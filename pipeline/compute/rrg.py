"""資金流向 v3 的三張圖的資料：相對輪動圖（RRG）、資金桑基圖、族群佔比河流圖。

RRG（Relative Rotation Graph）是看「輪動」最直觀的圖：
  x 軸 = 相對強度（族群指數 / 大盤指數，相對自己近 20 日均值的偏離，中心 100）
  y 軸 = 相對強度的動能（x 軸值相對自己近 5 日均值的偏離，中心 100）
  四象限：右上領先、右下轉弱、左下落後、左上改善；族群通常順時針繞圈。
JdK 原版公式未公開，這裡用常見的均值標準化近似，趨勢與象限判讀一致。

大盤指數用全市場成交值加權漲跌幅累乘還原，跟族群指數同一套算法，避免兩邊口徑不同。
"""
from __future__ import annotations

from .names import latest_names, name_or_code
import logging

import numpy as np
import pandas as pd

from ..groups import loader
from ..util.roc import is_tradable_security

log = logging.getLogger(__name__)


def _v(x, nd=2):
    try:
        f = float(x)
        return round(f, nd) if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def market_index(price: pd.DataFrame, days: int = 160) -> pd.Series:
    """全市場成交值加權日報酬累乘成指數（index=date 字串）。"""
    cutoff = (pd.Timestamp(price["date"].max()) - pd.Timedelta(days=days * 1.6)).date().isoformat()
    px = price[price["date"].astype(str) >= cutoff][["date", "code", "close", "change", "turnover"]].copy()
    px = px[px["code"].map(is_tradable_security)]
    px["turnover"] = pd.to_numeric(px["turnover"], errors="coerce").fillna(0)
    prev = px["close"] - px["change"].fillna(0)
    px["chg"] = np.where(prev > 0, px["change"] / prev, np.nan)
    px = px.dropna(subset=["chg"])
    w = px.groupby("date").apply(lambda g: float((g["chg"] * g["turnover"]).sum() / g["turnover"].sum())
                                 if g["turnover"].sum() > 0 else 0.0)
    return (1 + w).cumprod()


def rrg(group_hist: pd.DataFrame, price: pd.DataFrame, trail: int = 30,
        min_share: float = 0.3) -> dict:
    """trail 是「存下來的軌跡長度」，不是前端一定要畫滿的長度。
    前端的拉Bar 能拉到幾天，這裡就要存到幾天 —— 存得比前端短的話，
    拉到最大值等於沒反應，使用者會以為壞了。

    2026-09-19（Andy N4「時間週期拉到 30 天」）：20 → 30。"""
    if group_hist is None or group_hist.empty:
        return {"points": [], "date": None}
    g = group_hist.sort_values("date").copy()
    g["date"] = g["date"].astype(str)
    g["factor"] = 1 + g["chg_pct"].fillna(0) / 100
    g["gi"] = g.groupby("group_id")["factor"].cumprod()
    bench = market_index(price)
    bench.index = bench.index.astype(str)
    g["bi"] = g["date"].map(bench)
    g = g.dropna(subset=["bi"])
    g["rs"] = 100 * g["gi"] / g["bi"]
    gg = g.groupby("group_id")
    g["rs_ratio"] = 100 + 100 * (g["rs"] / gg["rs"].transform(lambda s: s.rolling(20, min_periods=10).mean()) - 1)
    g["rs_mom"] = 100 + 100 * (g["rs_ratio"] / g.groupby("group_id")["rs_ratio"]
                               .transform(lambda s: s.rolling(5, min_periods=3).mean()) - 1)
    latest = g["date"].max()
    today = g[g["date"] == latest]
    # 只畫今天成交值佔比 ≥ min_share% 的族群，太小的族群在圖上只是雜訊
    keep = set(today[today["turnover_share"] >= min_share]["group_id"])
    points = []
    for gid, sub in g[g["group_id"].isin(keep)].groupby("group_id"):
        sub = sub.dropna(subset=["rs_ratio", "rs_mom"]).tail(trail)
        if sub.empty:
            continue
        last = sub.iloc[-1]
        x, y = float(last["rs_ratio"]), float(last["rs_mom"])
        quadrant = ("leading" if x >= 100 and y >= 100 else "weakening" if x >= 100 else
                    "improving" if y >= 100 else "lagging")
        points.append({
            "group_id": gid, "group_name": last["group_name"], "chain": last.get("chain"),
            "x": _v(x), "y": _v(y), "quadrant": quadrant,
            "share": _v(last["turnover_share"]), "turnover": _v(last["turnover"], 0),
            "trail": [[str(d), _v(a), _v(b)] for d, a, b in zip(sub["date"], sub["rs_ratio"], sub["rs_mom"])],
        })
    points.sort(key=lambda p: -(p["turnover"] or 0))
    return {"date": latest, "points": points, "trail_days": trail,
            "note": "x＝相對強度（族群指數/大盤，相對近 20 日均值，中心 100）；y＝相對強度動能（相對近 5 日均值）。近似 JdK RS-Ratio / RS-Momentum。"}


def sankey(today: pd.DataFrame, members: dict, top_groups: int = 12, top_members: int = 3) -> dict:
    """大盤 → 產業鏈 → 族群 → 代表個股 的成交值流向（今日）。"""
    if today is None or today.empty:
        return {"nodes": [], "links": []}
    chains = loader.chains()
    chain_name = {cid: c.get("name", cid) for cid, c in chains.items()}
    chain_name.setdefault("industry", "其他產業")
    chain_name.setdefault("other", "其他")
    t = today.copy()
    t["turnover"] = pd.to_numeric(t["turnover"], errors="coerce").fillna(0)
    t = t.sort_values("turnover", ascending=False)
    top = t.head(top_groups)
    rest = float(t["turnover"].iloc[top_groups:].sum())

    nodes, links = [{"name": "台股成交值", "depth": 0}], []
    seen = {"台股成交值"}

    def _node(name, depth, **extra):
        if name not in seen:
            nodes.append({"name": name, "depth": depth, **extra}); seen.add(name)

    for chain_id, sub in top.groupby(top["chain"].fillna("other")):
        cname = chain_name.get(chain_id, chain_id)
        _node(cname, 1)
        links.append({"source": "台股成交值", "target": cname, "value": float(sub["turnover"].sum())})
        for r in sub.itertuples():
            gname = r.group_name
            _node(gname, 2, group_id=r.group_id)
            links.append({"source": cname, "target": gname, "value": float(r.turnover)})
            for mmb in (members.get(r.group_id, {}).get("members") or [])[:top_members]:
                label = f"{mmb['name']} {mmb['code']}"
                _node(label, 3, code=mmb["code"])
                links.append({"source": gname, "target": label, "value": float(mmb.get("turnover") or 0)})
    if rest > 0:
        _node("其他族群", 1)
        links.append({"source": "台股成交值", "target": "其他族群", "value": rest})
    return {"nodes": nodes, "links": links}


def sankey_daily(group_hist: pd.DataFrame, price: pd.DataFrame,
                 membership: "pd.DataFrame | None",
                 days: int = 60, top_groups: int = 12, top_members: int = 3) -> dict:
    """資金去向的**逐日**版本（Andy 2026-09-18 圖六：「一樣都具備相資金輪動的拉Bar
    可以觀察並搭配播放功能」）。

    原本的 `sankey()` 只有今天一天，所以那張圖拉不動也播不了。
    這裡給最近 `days` 天，前端就能像輪動時鐘一樣往回拉、一天一天播。

    ★ 這份要**寫成獨立的 JSON 檔**，不要塞進 flow_v3 ——
      flow_v3 已經是這個網站最大的一份，再加 60 天 × 12 族群 × 3 檔會讓
      每一頁（包含只想看總覽的人）都得先下載它。

    回傳 {dates: [...], groups: [{gid, name, chain, tv: [...]}], leaves: {date: [{gid, code, name, tv}]}}
    """
    if group_hist is None or group_hist.empty:
        return {"dates": [], "groups": [], "leaves": {}}
    g = group_hist.copy()
    g["date"] = g["date"].astype(str)
    dates = sorted(g["date"].unique())[-int(days):]
    if not dates:
        return {"dates": [], "groups": [], "leaves": {}}
    g = g[g["date"].isin(dates)]
    latest = dates[-1]
    order = (g[g["date"] == latest].sort_values("turnover", ascending=False)["group_id"]
             .head(top_groups).tolist())
    meta = g.drop_duplicates("group_id").set_index("group_id")
    groups = []
    for gid in order:
        sub = g[g["group_id"] == gid].set_index("date")["turnover"].reindex(dates)
        groups.append({
            "gid": str(gid),
            "name": str(meta.loc[gid]["group_name"]) if gid in meta.index else str(gid),
            "chain": (None if gid not in meta.index or pd.isna(meta.loc[gid].get("chain"))
                      else str(meta.loc[gid]["chain"])),
            "tv": [_v(x, 0) for x in sub.tolist()],
        })
    # 每一天、每個族群的前幾檔（給前端展開用）
    leaves: dict[str, list] = {}
    if price is not None and not price.empty and "turnover" in price.columns:
        # membership 是 loader.membership() 的長格式 DataFrame（一列一個 code×group_id）
        code2g: dict[str, list[str]] = {}
        keep = {str(x) for x in order}
        if membership is not None and len(membership):
            for r in membership.itertuples():
                if str(r.group_id) in keep:
                    code2g.setdefault(str(r.code), []).append(str(r.group_id))
        if code2g:
            px = price.copy()
            px["date"] = px["date"].astype(str)
            px = px[px["date"].isin(dates)]
            # ★ 2026-09-20：代表股那一欄整排顯示 "nan" 的根因就在這一行。
            #   `price_daily` 的 `name` 欄是後來才加的，只有 2026-09-09 之後的列有值，
            #   更早的列是 NaN。原本寫 `px.drop_duplicates("code")` 取的是**最早**那一列
            #   （px 已經切到最近 60 天，起點在三個月前），於是每一檔抓到的都是 NaN，
            #   再被 `str()` 變成字串 "nan" 送進 JSON —— 前端拿到的就是「nan 2330」。
            #   改成先丟掉沒有名字的列、再取**最後**一筆（改名的話以最新為準）。
            name_of = latest_names(px)
            for d, day in px.groupby("date"):
                buckets: dict[str, list] = {}
                for r in day.itertuples():
                    for gid in code2g.get(str(r.code), ()):
                        buckets.setdefault(gid, []).append((str(r.code), float(r.turnover or 0)))
                rows = []
                for gid, lst in buckets.items():
                    lst.sort(key=lambda t: -t[1])
                    for c, tv in lst[:top_members]:
                        # 查不到名字就退回代號本身 —— 寧可顯示「2330」也不要顯示「nan」
                        rows.append({"gid": gid, "code": c, "name": name_or_code(name_of, c), "tv": tv})
                leaves[str(d)] = rows
    return {"dates": dates, "groups": groups, "leaves": leaves}


def share_series(group_hist: pd.DataFrame, days: int = 250, top: int = 12) -> dict:
    """族群成交值佔比逐日序列（河流圖用）；前 top 個族群 + 其他。

    2026-09-18（Andy 圖七「也需要播放功能、拉Bar + &  -」）：60 → 250 天。
    原本只給 60 天，前端的拉 Bar 只能「從尾端往前切幾天」；
    要做「把截止日往前挪、一天一天回放」就得有更長的歷史，不然回放兩下就沒資料了。
    250 個交易日約一年，回放一整年綽綽有餘。
    """
    if group_hist is None or group_hist.empty:
        return {"dates": [], "series": []}
    g = group_hist.copy()
    g["date"] = g["date"].astype(str)
    dates = sorted(g["date"].unique())[-days:]
    g = g[g["date"].isin(dates)]
    latest = dates[-1]
    order = (g[g["date"] == latest].sort_values("turnover", ascending=False)["group_id"].tolist())
    keep, others = order[:top], set(order[top:])
    piv = g.pivot_table(index="date", columns="group_id", values="turnover_share", aggfunc="sum").reindex(dates).fillna(0)
    names = g.drop_duplicates("group_id").set_index("group_id")["group_name"].to_dict()
    series = [{"group_id": gid, "name": names.get(gid, gid),
               "values": [_v(x) for x in piv[gid].tolist()]} for gid in keep if gid in piv]
    if others:
        cols = [c for c in others if c in piv]
        series.append({"group_id": "_others", "name": "其他",
                       "values": [_v(x) for x in piv[cols].sum(axis=1).tolist()]})
    return {"dates": dates, "series": series}
