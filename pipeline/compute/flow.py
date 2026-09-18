"""M1 資金面：族群資金彙總、輪動雷達、集中度、相對強弱。

核心概念：個股層級的成交值加總到族群，再看「佔比」而不是絕對金額 ——
大盤整體量能起伏很大，只看金額會被大盤帶著走，看不出輪動。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..groups import loader
from ..util.roc import norm_industry

log = logging.getLogger(__name__)


def _attach_groups(price: pd.DataFrame, company: pd.DataFrame) -> pd.DataFrame:
    """把每檔股票掛上題材族群；沒有題材的用法定產業別當族群，確保全市場都有歸屬。

    一檔股票可以同時屬於多個族群（鴻海既是 AI 伺服器也是手機供應鏈）。
    這時它的成交值會被平均分配到各族群（weight = 1/族群數），而不是每個
    族群都算一次完整金額 —— 否則多族群股會把市場總量灌水，「資金佔比」
    這個指標就失去意義了。
    """
    m = loader.membership()
    df = price.merge(m, on="code", how="left")

    if not company.empty and "industry" in company.columns:
        ind = company[["code", "industry"]].copy()
        # 上市與上櫃的產業別寫法不同，統一過才不會產出兩個同義族群（見 util/roc.norm_industry）
        ind["industry"] = ind["industry"].map(norm_industry)
        df = df.merge(ind, on="code", how="left")
        fallback = df["group_id"].isna() & df["industry"].notna()
        df.loc[fallback, "group_id"] = "ind_" + df.loc[fallback, "industry"].astype(str)
        df.loc[fallback, "group_name"] = df.loc[fallback, "industry"]
        df.loc[fallback, "tier"] = "standalone"
        df.loc[fallback, "chain"] = "industry"

    df = df[df["group_id"].notna()].copy()
    if df.empty:
        return df

    # 同一天同一檔股票被掛到幾個族群，就把它的量能拆成幾份
    n_groups = df.groupby(["date", "code"])["group_id"].transform("nunique")
    df["weight"] = 1.0 / n_groups.clip(lower=1)
    return df


def group_daily(price: pd.DataFrame, company: pd.DataFrame,
                inst: pd.DataFrame | None = None,
                margin: pd.DataFrame | None = None) -> pd.DataFrame:
    """每日 × 每族群的資金彙總。這張表是 M1 所有圖表的共同來源。"""
    if price.empty:
        return pd.DataFrame()

    df = _attach_groups(price, company)
    if df.empty:
        log.warning("沒有任何個股對得上族群，請檢查 groups.yaml 與 company_info")
        return pd.DataFrame()

    df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce").fillna(0)
    df["prev_close"] = df["close"] - df["change"].fillna(0)
    df["chg_pct"] = np.where(df["prev_close"] > 0,
                             df["change"] / df["prev_close"] * 100, np.nan)

    if inst is not None and not inst.empty:
        df = df.merge(inst[["date", "code", "foreign_total", "trust", "dealer"]],
                      on=["date", "code"], how="left")
    for col in ("foreign_total", "trust", "dealer"):
        if col not in df.columns:
            df[col] = np.nan

    if margin is not None and not margin.empty:
        df = df.merge(margin[["date", "code", "margin_change", "margin_balance"]],
                      on=["date", "code"], how="left")
    for col in ("margin_change", "margin_balance"):
        if col not in df.columns:
            df[col] = np.nan

    # ★★ 這一段是整條部署管線最貴的地方，改動前務必先讀這段註解。
    #   2026-09-18 在 build() 加上分段計時之後量到：整個 build() 559.7 秒，
    #   **這一個函式就佔 393.1 秒（70%）** —— 比全市場 2,334 檔個股頁那一圈（146.5 秒）還貴兩倍半。
    #
    #   原本的寫法是 `groupby([...]).apply(_agg)`，`_agg` 是一個 Python 函式。
    #   groupby 的組數 ＝ 交易日數 × 族群數 ＝ **236,641 組**，
    #   所以那一行等於在 Python 裡跑二十三萬次迴圈，每一次還要建一個九個元素的 Series 物件。
    #
    #   改成向量化：先把每一項要加總的東西算成一個欄位，再讓 groupby 一次把整批加完。
    #   兩個一定要顧到、不然數字會變的地方：
    #   1. **min_count=1**：外資／投信／自營／融資這四項，一整組全是 NaN 時要維持 NaN
    #   （代表「那天法人資料還沒到」），不可以變成 0（那代表「法人剛好買賣相抵」）。
    #   `groupby.sum()` 預設會把全 NaN 變 0，所以這四項要另外用 `.sum(min_count=1)` 算。
    #   2. **欄位型別**：舊版把 int 與 float 混在同一個 `pd.Series({...})` 裡，
    #   pandas 會把整個 Series 轉成 float64 —— 所以 advancers／decliners／constituents
    #   在舊版**是浮點數**，JSON 寫出來是 `5.0` 不是 `5`。這裡刻意 astype(float) 對齊，
    #   不然前端拿到的字面值會變（`tests/` 與逐檔比對都釘住這件事）。
    keys = ["date", "group_id", "group_name", "tier", "chain"]
    w = df["weight"]
    tv = df["turnover"] * w
    # 漲跌幅用成交值加權，否則會被冷門小型股主導；沒有漲跌幅的那幾檔權重算 0
    ww = tv.where(df["chg_pct"].notna(), 0)
    tmp = pd.DataFrame({
        "_tv": tv, "_ww": ww, "_chgw": df["chg_pct"].fillna(0) * ww,
        "_adv": (df["chg_pct"] > 0).astype("int64"),
        "_dec": (df["chg_pct"] < 0).astype("int64"),
        "code": df["code"],
        "foreign_net": df["foreign_total"] * w, "trust_net": df["trust"] * w,
        "dealer_net": df["dealer"] * w, "margin_change": df["margin_change"] * w,
    })
    for k in keys:
        tmp[k] = df[k]
    gb = tmp.groupby(keys, dropna=False, sort=True)
    out = gb.agg(turnover=("_tv", "sum"), _wsum=("_ww", "sum"), _chgw=("_chgw", "sum"),
                 advancers=("_adv", "sum"), decliners=("_dec", "sum"),
                 constituents=("code", "nunique"))
    # 法人與融資：全 NaN 要留成 NaN（見上面第 1 點），所以不能併進上面那個 agg
    nets = gb[["foreign_net", "trust_net", "dealer_net", "margin_change"]].sum(min_count=1)
    out = out.join(nets)
    out["chg_pct"] = np.where(out["_wsum"] > 0, out["_chgw"] / out["_wsum"], np.nan)
    for c in ("advancers", "decliners", "constituents"):
        out[c] = out[c].astype(float)      # 對齊舊版（見上面第 2 點）
    out = (out.drop(columns=["_wsum", "_chgw"])
              .reindex(columns=["turnover", "chg_pct", "advancers", "decliners", "constituents",
                                "foreign_net", "trust_net", "dealer_net", "margin_change"])
              .reset_index())

    total = out.groupby("date")["turnover"].transform("sum")
    out["turnover_share"] = np.where(total > 0, out["turnover"] / total * 100, np.nan)
    return out.sort_values(["date", "turnover"], ascending=[True, False])


def rotation_radar(group_hist: pd.DataFrame, short: int = 5,
                   long: int = 20) -> pd.DataFrame:
    """輪動雷達：成交值佔比的 5 日均 減 20 日均。

    正值＝資金正在往這個族群集中；負值＝正在流出。
    用佔比的移動平均差值而不是單日數字，是為了濾掉單日的假訊號。
    """
    if group_hist.empty:
        return pd.DataFrame()

    g = group_hist.sort_values("date").copy()
    g["share_short"] = (g.groupby("group_id")["turnover_share"]
                         .transform(lambda s: s.rolling(short, min_periods=2).mean()))
    g["share_long"] = (g.groupby("group_id")["turnover_share"]
                        .transform(lambda s: s.rolling(long, min_periods=5).mean()))
    g["rotation"] = g["share_short"] - g["share_long"]

    latest = g["date"].max()
    out = g[g["date"] == latest].copy()
    return out.sort_values("rotation", ascending=False)


def concentration(group_hist: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """資金集中度：前 N 大族群吃掉多少成交值。

    上升＝行情縮圈到少數族群（通常是主流股獨強）
    下降＝資金擴散（通常是輪動或補漲階段）

    前 5 大與前 10 大同時算：前 5 看「主流有多獨」，前 10 看「主流圈子有多大」，
    兩條分開才看得出「換主流」和「資金整體擴散」的差別。
    """
    if group_hist.empty:
        return pd.DataFrame()
    rows = []
    for d, g in group_hist.groupby("date"):
        s = g.sort_values("turnover", ascending=False)["turnover_share"]
        rows.append({"date": d, "top_share": float(s.head(top_n).sum()),
                     "top10_share": float(s.head(10).sum())})
    out = pd.DataFrame(rows).sort_values("date")
    out["top_share_ma20"] = out["top_share"].rolling(20, min_periods=5).mean()
    out["top10_share_ma20"] = out["top10_share"].rolling(20, min_periods=5).mean()
    return out


def relative_strength(group_hist: pd.DataFrame, market: pd.DataFrame,
                      window: int = 20) -> pd.DataFrame:
    """族群相對強弱：族群 N 日報酬 減 大盤 N 日報酬。"""
    if group_hist.empty:
        return pd.DataFrame()

    g = group_hist.sort_values("date").copy()
    # 用族群成交值加權漲跌幅累乘還原出族群指數
    g["factor"] = 1 + g["chg_pct"].fillna(0) / 100
    g["group_index"] = g.groupby("group_id")["factor"].cumprod()
    g["ret"] = (g.groupby("group_id")["group_index"]
                 .transform(lambda s: s / s.shift(window) - 1) * 100)

    market_ret = _market_return(market, window)

    latest = g["date"].max()
    out = g[g["date"] == latest][
        ["date", "group_id", "group_name", "tier", "chain", "ret"]].copy()
    out["market_ret"] = market_ret
    out["rs"] = out["ret"] - market_ret
    return out.sort_values("rs", ascending=False)


def _market_return(market: pd.DataFrame | None, window: int) -> float:
    """大盤 N 日報酬。

    證交所的 FMTQIK 只回傳「當月至今」，所以每個月初只有幾個交易日可用，
    根本算不出 20 日報酬 —— 這會讓整張相對強弱圖變成空白。
    拿不到就改用 yfinance 的 ^TWII（intl_daily 裡有一年份）。
    """
    from ..util import store

    def _ret(series: pd.Series) -> float:
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) <= window:
            return np.nan
        return float((s.iloc[-1] / s.iloc[-1 - window] - 1) * 100)

    if market is not None and not market.empty and "taiex" in market.columns:
        r = _ret(market.sort_values("date")["taiex"])
        if not np.isnan(r):
            return r

    try:
        intl = store.read("intl_daily")
    except Exception:  # noqa: BLE001
        return np.nan
    if intl.empty or "symbol" not in intl.columns:
        log.warning("拿不到大盤報酬，相對強弱會是空的")
        return np.nan

    twii = intl[intl["symbol"] == "^TWII"].sort_values("date")
    if twii.empty:
        log.warning("intl_daily 裡沒有 ^TWII，相對強弱會是空的")
        return np.nan
    r = _ret(twii["close"])
    if np.isnan(r):
        log.warning("^TWII 資料不足 %d 天，相對強弱會是空的", window)
    return r


#: 法人別 → inst_daily 的欄位。`total` 是三大法人合計。
INST_COLS = {"trust": "trust", "foreign": "foreign_total", "total": None}


def trust_streak(inst_hist: pd.DataFrame, min_days: int = 2,
                 who: str = "trust") -> pd.DataFrame:
    """法人連續買超天數排行。

    台股中期最有效的籌碼訊號之一：法人持續買代表真的在建倉，而不是當沖或避險部位。

    `who`：`trust` 投信、`foreign` 外資、`total` 三大法人合計
    （Andy 2026-09-15：「還能切換買超週期 不限只有3天，還要加上外資買超，以及綜合」）。
    `min_days` 放寬到 2 —— 門檻由前端自己篩，這裡給得多一點前端才有得選。
    """
    if inst_hist.empty:
        return pd.DataFrame()

    df = inst_hist.sort_values(["code", "date"]).copy()
    if who == "total":
        cols = [c for c in ("foreign_total", "trust", "dealer") if c in df.columns]
        if not cols:
            return pd.DataFrame()
        df["_net"] = df[cols].fillna(0).sum(axis=1)
    else:
        col = INST_COLS.get(who, "trust")
        if col not in df.columns:
            return pd.DataFrame()
        df["_net"] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    rows = []
    for code, g in df.groupby("code"):
        g = g.sort_values("date")
        streak = 0
        total = 0.0
        for net in reversed(g["_net"].tolist()):
            if not (net > 0):
                break
            streak += 1
            total += float(net or 0)
        if streak >= min_days:
            rows.append({"code": code, "streak_days": streak,
                         "accumulated": total, "who": who,
                         "date": g["date"].iloc[-1]})
    out = pd.DataFrame(rows)
    return out.sort_values("streak_days", ascending=False) if not out.empty else out


# ---------------------------------------------------------------- 期間資金流向
# Andy 的原話：「需要有趨勢 好比說上週 上上週 上個月等等 可以查到不同時期 資金走向為何」。
# 所以這裡不是只給「今天」，而是把資金流向切成人講得出口的幾個期間，
# 每個期間都回答同一組問題：這段時間錢在誰身上、比上一段多還少、名次跑到哪裡去了。

PERIOD_KEYS = ("w0", "w1", "w2", "m0", "m1", "q")
PERIOD_LABEL = {"w0": "本週", "w1": "上週", "w2": "上上週",
                "m0": "本月", "m1": "上月", "q": "近三月"}
BUMP_WEEKS = 8          # 名次趨勢圖往回看幾週
BUMP_MONTHS = 8         # 名次趨勢圖往回看幾個月（切到月／季期間時用）
BUMP_TOP = 10           # 名次趨勢圖畫幾個族群（照最新一週的名次取）；再多線就糊成一團
BUMP_UNIT_LABEL = {"week": "近 8 週", "month": "近 8 個月"}


def _week_blocks(dates: list[str], n: int) -> list[list[str]]:
    """把交易日切成一週一塊（最新的在前），週一為一週之始。"""
    if not dates:
        return []
    ts = pd.to_datetime(pd.Series(dates))
    key = (ts - pd.to_timedelta(ts.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    blocks: dict[str, list[str]] = {}
    for d, k in zip(dates, key):
        blocks.setdefault(k, []).append(d)
    return [blocks[k] for k in sorted(blocks, reverse=True)[:n]]


def _month_blocks(dates: list[str], n: int) -> list[list[str]]:
    blocks: dict[str, list[str]] = {}
    for d in dates:
        blocks.setdefault(d[:7], []).append(d)
    return [blocks[k] for k in sorted(blocks, reverse=True)[:n]]


def _agg_block(g: pd.DataFrame, days: list[str]) -> pd.DataFrame:
    """一個期間內，每個族群的成交值、佔比、期間報酬、法人合計。"""
    sub = g[g["date"].isin(days)]
    if sub.empty:
        return pd.DataFrame()
    rows = []
    for gid, one in sub.groupby("group_id"):
        one = one.sort_values("date")
        tv = float(one["turnover"].sum())
        # 期間報酬＝每日族群漲跌幅複利，跟看 K 線同一個口徑
        ret = float((1 + one["chg_pct"].fillna(0) / 100).prod() - 1) * 100
        rows.append({
            "group_id": gid,
            "group_name": one["group_name"].iloc[-1],
            "chain": one["chain"].iloc[-1] if "chain" in one else None,
            "turnover": tv,
            "ret": round(ret, 2),
            "foreign": _sum_or_none(one, "foreign_net"),
            "trust": _sum_or_none(one, "trust_net"),
            "dealer": _sum_or_none(one, "dealer_net"),
            "days": int(one["date"].nunique()),
        })
    out = pd.DataFrame(rows)
    total = out["turnover"].sum()
    out["share"] = out["turnover"] / total * 100 if total > 0 else np.nan
    out = out.sort_values("share", ascending=False).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    return out


def _sum_or_none(df: pd.DataFrame, col: str):
    if col not in df or df[col].isna().all():
        return None
    return float(df[col].sum())


def period_flows(group_hist: pd.DataFrame) -> dict:
    """各期間的資金流向，外加近幾週的名次序列（給名次趨勢圖）。"""
    if group_hist is None or group_hist.empty:
        empty = {"weeks": [], "series": [], "unit": "week", "label": BUMP_UNIT_LABEL["week"]}
        return {"periods": [], "bump": empty,
                "bumps": {"week": empty, "month": dict(empty, unit="month", label=BUMP_UNIT_LABEL["month"])}}

    g = group_hist.copy()
    g["date"] = g["date"].astype(str)
    dates = sorted(g["date"].unique())
    weeks = _week_blocks(dates, max(BUMP_WEEKS, 4))
    months = _month_blocks(dates, 3)

    # 期間 → （這一段的交易日, 用來比較的上一段交易日）
    spec: dict[str, tuple[list[str], list[str]]] = {}
    for i, key in enumerate(("w0", "w1", "w2")):
        if len(weeks) > i:
            spec[key] = (weeks[i], weeks[i + 1] if len(weeks) > i + 1 else [])
    for i, key in enumerate(("m0", "m1")):
        if len(months) > i:
            spec[key] = (months[i], months[i + 1] if len(months) > i + 1 else [])
    q_now = dates[-63:]
    spec["q"] = (q_now, dates[-126:-63])

    periods = []
    for key in PERIOD_KEYS:
        if key not in spec:
            continue
        days, prev_days = spec[key]
        cur = _agg_block(g, days)
        if cur.empty:
            continue
        prev = _agg_block(g, prev_days) if prev_days else pd.DataFrame()
        pmap = prev.set_index("group_id") if not prev.empty else None
        rows = []
        for _, r in cur.iterrows():
            p = pmap.loc[r["group_id"]] if pmap is not None and r["group_id"] in pmap.index else None
            share_prev = float(p["share"]) if p is not None and pd.notna(p["share"]) else None
            rank_prev = int(p["rank"]) if p is not None else None
            rows.append({
                "group_id": r["group_id"], "group_name": r["group_name"], "chain": r["chain"],
                "turnover": round(float(r["turnover"]), 0),
                "share": round(float(r["share"]), 3) if pd.notna(r["share"]) else None,
                "share_prev": round(share_prev, 3) if share_prev is not None else None,
                "share_chg": round(float(r["share"]) - share_prev, 3) if share_prev is not None and pd.notna(r["share"]) else None,
                "ret": r["ret"], "rank": int(r["rank"]), "rank_prev": rank_prev,
                "rank_chg": (rank_prev - int(r["rank"])) if rank_prev is not None else None,
                "foreign": r["foreign"], "trust": r["trust"], "dealer": r["dealer"],
            })
        periods.append({
            "key": key, "label": PERIOD_LABEL[key],
            "from": days[0], "to": days[-1], "days": len(days),
            "prev_from": prev_days[0] if prev_days else None,
            "prev_to": prev_days[-1] if prev_days else None,
            "groups": rows,
        })

    # 名次趨勢：週與月各做一份。Andy 切到「上月／近三月」時名次圖也要跟著換刻度，
    # 不然整張圖固定是近 8 週，看起來就是「排名不會變」。
    week_bump = _bump(g, list(reversed(weeks[:BUMP_WEEKS])), "week")
    month_bump = _bump(g, list(reversed(_month_blocks(dates, BUMP_MONTHS))), "month")

    return {"periods": periods,
            "bump": week_bump,                       # 舊欄位保留：前端舊版還在讀
            "bumps": {"week": week_bump, "month": month_bump}}


def inst_daily_series(group_hist: pd.DataFrame, days: int = 30) -> dict:
    """族群 × 法人的**逐日**序列（最近 `days` 個交易日）。

    為什麼要這個（Andy 2026-09-18：「族群 × 法人需要新增時間週期也是拉 Bar 式，0-30 天」）：
    原本只有 `period_flows()` 給的**期間**彙總（本週／上週／本月／近三月），
    那是固定的幾個區間，拉不出「最近 N 天」。逐日給出來之後，
    前端要幾天就自己加幾天 —— 拖拉的當下就重算，不用再回頭問後端。

    只給最近 30 天：拉 Bar 的上限就是 30，多給的是白給
    （26 個族群 × 30 天 × 3 種法人 ≈ 2,340 個數字，很小）。
    """
    if group_hist is None or group_hist.empty or "date" not in group_hist.columns:
        return {"dates": [], "groups": []}
    cols = [c for c in ("foreign_net", "trust_net", "dealer_net") if c in group_hist.columns]
    if not cols:
        return {"dates": [], "groups": []}
    dates = sorted({str(d) for d in group_hist["date"]})[-int(days):]
    if not dates:
        return {"dates": [], "groups": []}
    g = group_hist[group_hist["date"].astype(str).isin(dates)]
    out = []
    for gid, sub in g.groupby("group_id"):
        sub = sub.set_index(sub["date"].astype(str))
        row = {"group_id": str(gid),
               "group_name": str(sub["group_name"].iloc[-1]) if "group_name" in sub else str(gid)}
        for c, key in (("foreign_net", "foreign"), ("trust_net", "trust"), ("dealer_net", "dealer")):
            if c in sub.columns:
                s = sub[c].reindex(dates)
                row[key] = [None if pd.isna(v) else float(v) for v in s]
        out.append(row)
    return {"dates": dates, "groups": out}


def share_daily(group_hist: pd.DataFrame, days: int = 60) -> dict:
    """族群成交值**佔比**的逐日序列（最近 `days` 個交易日）。

    為什麼要這個（Andy 2026-09-18 圖四：「資金流向排行需要跟資金輪動一樣以拉Bar 形式呈現，
    也是可以選時間週期拉Bar 1-30 天」）：
    原本排行只吃 `period_flows()` 給的**固定期間**（本週／上週／本月／近三月），
    拉不出「最近 N 天」。逐日給出來之後，前端要幾天就自己算幾天 ——
    拖拉的當下就重算，不用回頭問後端（同 `inst_daily_series()` 的做法，DECISIONS #163）。

    給 60 天而不是 30：拉 Bar 上限是 30 天，但**比較基準**要往前再取 30 天
    （「最近 30 天 vs 前 30 天」），所以至少要 60 天才夠算滿。

    每個族群三條：
      share    當天成交值佔全市場的百分比（這是排行的主角）
      turnover 當天成交值（給 tooltip 用絕對金額）
      chg      當天漲跌百分比（給前端算區間複利報酬）
    """
    if group_hist is None or group_hist.empty or "date" not in group_hist.columns:
        return {"dates": [], "groups": []}
    dates = sorted({str(d) for d in group_hist["date"]})[-int(days):]
    if not dates:
        return {"dates": [], "groups": []}
    g = group_hist[group_hist["date"].astype(str).isin(dates)]
    out = []
    for gid, sub in g.groupby("group_id"):
        sub = sub.set_index(sub["date"].astype(str))
        last = sub.iloc[-1]
        row = {"group_id": str(gid),
               "group_name": str(last["group_name"]) if "group_name" in sub.columns else str(gid),
               "chain": (None if "chain" not in sub.columns or pd.isna(last["chain"]) else str(last["chain"]))}
        for col, key in (("turnover_share", "share"), ("turnover", "turnover"), ("chg_pct", "chg")):
            if col in sub.columns:
                # reindex 到同一組日期：某族群那天沒有資料就是 None，不可以自己補 0
                # （補 0 會讓前端把「沒資料」畫成「佔比掉到 0」）
                s = sub[col].reindex(dates)
                row[key] = [None if pd.isna(v) else float(v) for v in s]
            else:
                row[key] = [None] * len(dates)
        out.append(row)
    # 以最後一天的佔比由大到小，前端不必再排一次
    out.sort(key=lambda r: -((r.get("share") or [None])[-1] or 0))
    return {"dates": dates, "groups": out}


def _bump(g: pd.DataFrame, blocks_days: list[list[str]], unit: str) -> dict:
    """一段一段（週或月）算佔比名次，畫名次趨勢圖用。blocks_days 由舊到新。"""
    blocks = [_agg_block(g, days) for days in blocks_days]
    keep = [(d, b) for d, b in zip(blocks_days, blocks) if not b.empty]
    if not keep:
        return {"weeks": [], "series": [], "unit": unit, "label": BUMP_UNIT_LABEL[unit]}
    blocks_days = [d for d, _ in keep]
    blocks = [b for _, b in keep]
    if unit == "month":
        labels = [days[0][:7].replace("-", "/") for days in blocks_days]
    else:
        labels = [days[0][5:].replace("-", "/") for days in blocks_days]
    latest = blocks[-1]
    top_ids = list(latest.nsmallest(BUMP_TOP, "rank")["group_id"])
    series = []
    for gid in top_ids:
        ranks, shares = [], []
        for blk in blocks:
            if gid in set(blk["group_id"]):
                row = blk[blk["group_id"] == gid].iloc[0]
                ranks.append(int(row["rank"])); shares.append(round(float(row["share"]), 2))
            else:
                ranks.append(None); shares.append(None)
        name = latest[latest["group_id"] == gid]["group_name"].iloc[0]
        series.append({"group_id": gid, "group_name": name, "ranks": ranks, "shares": shares})
    return {"weeks": labels, "series": series, "unit": unit, "label": BUMP_UNIT_LABEL[unit]}
