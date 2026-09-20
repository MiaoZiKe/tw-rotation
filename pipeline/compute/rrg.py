"""資金流向 v3 的三張圖的資料：相對輪動圖（RRG）、資金桑基圖、族群佔比河流圖。

RRG（Relative Rotation Graph）是看「輪動」最直觀的圖：
  x 軸 = 相對強度（族群指數 / 大盤指數，先做 EMA 平滑，再看相對自己近 40 日均值的偏離，中心 100）
  y 軸 = 相對強度的動能（x 軸值的 10 日變動率，中心 100）
  四象限：右上領先、右下轉弱、左下落後、左上改善；族群通常順時針繞圈。
JdK 原版公式未公開，這裡用常見的均值標準化近似，趨勢與象限判讀一致。

★ 2026-09-20（Andy A4 第 8 條：「明明是一天的差距，在圖上卻是各種歪曲，
  一天的走勢就一個點」）—— 這一段是那次量測的結論，改參數前先讀完。

  量的方法：把每個族群的 trail 相鄰兩天算成一個步長，再除以「時鐘盤面的半徑」
  （前端把兩軸各自除以當天最大偏離量之後畫成極座標，所以半徑 1 ＝ 偏離最大的族群）。
  量到的事實（36 個族群 × 30 天）：

    舊算法 20/5   一日步長中位數 = 盤面半徑的 **0.255**，最大 **1.852**，
                  30 天軌跡的直線度（淨位移 ÷ 路徑長）只有 **0.07**
                  —— 一天就能從圓心衝到盤緣，軌跡是一團原地抖動的毛線。

  根因**不是**「rs_mom 的 5 日窗口太短」。實測把 5 日拉到 10/20/30 日，
  一日步長完全沒有變（中位數 1.60 → 1.60，p99 8.22 → 9.05）。
  原因是 rs_ratio = 100 × rs ÷ SMA_n(rs)：SMA 一天幾乎不動，
  所以 **Δrs_ratio ≈ rs 的當日報酬**，跟 n 完全無關。
  而 rs 是「族群指數 ÷ 大盤指數」，族群 chg_pct 是成交值加權的，
  一天相對大盤差 2%（中位數）、尾端差 8~13% 都是常態 —— 那 11 點的跳動是真的，
  只是**沒有人先把它平滑掉就直接畫上去**。

  第二個根因：舊的 rs_mom 是「rs_ratio 相對自己 5 日均值」，
  這個量和 rs_ratio 本身的日變動相關係數高達 **+0.90**
  —— 兩個軸幾乎是同一個數字，點只會沿 45 度對角線來回彈，根本不會繞圈。

  所以改成標準 RRG 的兩層作法：
    1. **先把 rs 做 EMA 平滑**（RS_SMOOTH 日）再算 RS-Ratio ——
       直接把「一天的雜訊」壓下去，這才是步長變小的關鍵。
    2. **RS-Momentum 改用 RS-Ratio 的變動率**（ROC，MOM_ROC 日）而不是「相對自己的均值」。
       ROC 是 RS-Ratio 的一階導數，會領先它約 90 度，這才是 RRG 會順時針繞圈的來源。

  改後（EMA10 / SMA40 / ROC10，同一份資料）：
    一日步長中位數 **0.053**（降 4.8 倍）、最大 **0.280**（降 6.6 倍）、
    直線度 **0.38**（提升 5.4 倍）、順時針步數比例 0.65 → 0.71。

大盤指數用全市場成交值加權漲跌幅累乘還原，跟族群指數同一套算法，避免兩邊口徑不同。
"""
from __future__ import annotations

from .names import latest_names, name_or_code
import logging

import numpy as np
import pandas as pd

from ..groups import loader
from ..util.roc import is_tradable_security, norm_industry

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


# RRG 三個平滑參數集中在這裡，改一個就會動到象限歸屬，不要散在函式裡。
# 取值理由見模組 docstring 的量測表：EMA10/SMA40/ROC10 是「步長夠小、軌跡夠直、
# 又不會鈍到看不出輪動」的折衷；再拉長（EMA15/SMA60）直線度只多 0.13，
# 但 ROC 的落後會從 10 天變 15 天，對「什麼時候進場」這件事反而有害。
RS_SMOOTH = 10      # rs 的 EMA 平滑天數（把一天的雜訊壓掉）
RS_BASE = 40        # RS-Ratio 的基準均線天數（相對自己這條均線的偏離）
MOM_ROC = 10        # RS-Momentum＝RS-Ratio 的幾日變動率

# 個股 RRG：每個族群只取成交值前 N 檔。
# 為什麼是 10：① 圖上族群點最多 16 顆，個股再進來 10 顆＝26 顆，已經是
# 1440px 的盤面上標籤還排得開的上限（再多就只能靠隱藏標籤，那等於看不懂）；
# ② 成交值排序第 11 檔以後，佔族群成交值通常已經不到 2%，對「錢往哪跑」沒有解釋力；
# ③ 36 個族群 × 10 檔 × 31 天軌跡實測約 0.5MB，還在「下鑽時才抓」可以接受的範圍。
MEMBER_TOP_N = 10


def rrg_axes(g: pd.DataFrame, key: str) -> pd.DataFrame:
    """把 RS-Ratio／RS-Momentum 算出來。**族群與個股共用這一支。**

    需要的欄位：`key`（族群 id 或股票代號）、`gi`（自己的指數）、`bi`（大盤指數）。
    回傳同一張表加上 rs / rs_s / rs_ratio / rs_mom。

    ★ 為什麼一定要共用：兩邊若各寫一套（哪怕只差一個窗口長度），
      個股點和族群點畫在**同一張盤**上就會是兩種尺度 ——
      使用者會看到「個股全部貼在盤緣、族群全部縮在圓心」這種假象，
      而那不是市場的事實，是我們自己算出來的。

    三層的理由寫在模組 docstring（EMA 平滑 → 相對均線 → 一階導數），這裡不重複。
    """
    g = g.copy()
    g["rs"] = 100 * g["gi"] / g["bi"]
    gg = g.groupby(key)
    # ① 先把 rs 平滑掉 —— 步長之所以會小，靠的是這一行，不是底下的窗口長度（見模組 docstring）
    g["rs_s"] = gg["rs"].transform(lambda s: s.ewm(span=RS_SMOOTH, adjust=False).mean())
    # ② RS-Ratio：平滑後的 rs 相對自己 RS_BASE 日均線的偏離。
    #    min_periods 刻意用**滿窗**：窗口沒滿時均線只由少數幾天決定，算出來的偏離會非常誇張，
    #    那幾個點會把前端的正規化尺度整個撐開（所有族群被擠到圓心）。
    #    歷史不足 RS_BASE 天的族群／個股寧可不畫，也不要畫一個不能信的點
    #    —— 這一行同時就是「上市未滿 40+10 天的個股不輸出」的實作：
    #    窗口不滿 → rs_ratio 全 NaN → rs_mom 全 NaN → 後面 dropna 之後整檔消失，
    #    不會變成一個假的 0 或 NaN 點混在盤上。
    g["rs_ratio"] = 100 + 100 * (g["rs_s"] / g.groupby(key)["rs_s"]
                                 .transform(lambda s: s.rolling(RS_BASE, min_periods=RS_BASE).mean()) - 1)
    # ③ RS-Momentum：RS-Ratio 的 MOM_ROC 日變動率（一階導數），
    #    這才會領先 RS-Ratio 約 90 度、讓族群／個股在盤面上順時針繞圈。
    g["rs_mom"] = 100 + 100 * (g["rs_ratio"] / g.groupby(key)["rs_ratio"]
                               .transform(lambda s: s.shift(MOM_ROC)) - 1)
    return g


def quadrant_of(x: float, y: float) -> str:
    """四象限歸屬。族群與個股共用，免得兩邊的邊界條件（>= 還是 >）悄悄變得不一致。"""
    return ("leading" if x >= 100 and y >= 100 else "weakening" if x >= 100 else
            "improving" if y >= 100 else "lagging")



def rrg(group_hist: pd.DataFrame, price: pd.DataFrame, trail: int = 31,
        min_share: float = 0.3) -> dict:
    """trail 是「存下來的軌跡長度」，不是前端一定要畫滿的長度。
    前端的拉Bar 能拉到幾天，這裡就要存到幾天 —— 存得比前端短的話，
    拉到最大值等於沒反應，使用者會以為壞了。

    2026-09-19（Andy N4「時間週期拉到 30 天」）：20 → 30。
    2026-09-20（Andy A4 第 3、7 條「時間範圍前一天～前三十天」「大圈要落在那一天」）：
    30 → **31**。前端把拉Bar 改成時間軸刷動之後，「第 30 天前」要取的是
    `trail[len-1-30]`；只存 30 筆的話那個索引是 -1，JavaScript 會回 undefined，
    拉到最大值時大圈會默默停在「今天」—— 看起來就像拉Bar 壞了。多存一天就補起來。"""
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
    g = rrg_axes(g, "group_id")
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
        quadrant = quadrant_of(x, y)
        points.append({
            "group_id": gid, "group_name": last["group_name"], "chain": last.get("chain"),
            "x": _v(x), "y": _v(y), "quadrant": quadrant,
            "share": _v(last["turnover_share"]), "turnover": _v(last["turnover"], 0),
            "trail": [[str(d), _v(a), _v(b)] for d, a, b in zip(sub["date"], sub["rs_ratio"], sub["rs_mom"])],
        })
    points.sort(key=lambda p: -(p["turnover"] or 0))
    return {"date": latest, "points": points, "trail_days": trail,
            "note": f"x＝相對強度（族群指數/大盤，EMA{RS_SMOOTH} 平滑後相對近 {RS_BASE} 日均值，中心 100）；"
                    f"y＝相對強度的 {MOM_ROC} 日變動率（中心 100）。近似 JdK RS-Ratio / RS-Momentum。"}


def member_rrg(price: pd.DataFrame, gdetail: dict, points: list, trail: int = 31,
               top_n: int = MEMBER_TOP_N, bench: "pd.Series | None" = None) -> dict:
    """**個股層級**的 RRG（Andy 2026-09-21：「點擊族群後可以顯示對應個股，
    也可以點擊，並顯示在圖上」）。

    回傳 `{族群id: [{code, name, x, y, quadrant, turnover, share, trail}, ...]}`。

    ★ 三件刻意這樣做的事：

    1. **算法和族群共用 `rrg_axes()`**，一個參數都不另開。個股點要和族群點畫在
       同一張盤上，兩邊的 EMA／SMA／ROC 只要差一天，尺度就不一樣 ——
       使用者會以為市場長那樣，其實是我們算出來的。
    2. **只取每個族群成交值前 `top_n` 檔**（理由見 MEMBER_TOP_N 的註解）。
       這是控量，不是取樣偏好：全市場 1800 檔 × 31 天軌跡會是好幾 MB。
    3. **資料不足的個股直接不輸出**，不給 0 也不給 NaN。
       實作靠 `rrg_axes` 的滿窗 min_periods（上市未滿 RS_BASE+MOM_ROC 天的
       整檔會是 NaN），再加上「最後一筆必須就是最新交易日」這道 ——
       中途下市／長期停牌的股票最後一筆會停在幾個月前，畫上去等於騙人。

    `points` 用 `rrg()` 回傳的族群點，所以這裡算的族群集合和時鐘上看得到的完全一致；
    時鐘點不到的族群本來就下鑽不到，多算只是把檔案撐大。
    """
    if price is None or price.empty or not points:
        return {}
    want: dict[str, list] = {}
    for p in points:
        gid = str(p.get("group_id"))
        ms = ((gdetail or {}).get(gid) or {}).get("members") or []
        ms = sorted(ms, key=lambda m: -(m.get("turnover") or 0))[:top_n]
        if ms:
            want[gid] = ms
    if not want:
        return {}
    codes = {str(m["code"]) for ms in want.values() for m in ms}

    # 和大盤指數取同一段窗口：EMA 要暖機，窗口太短的話個股的 rs_s 會比族群的「新」，
    # 兩者的平滑程度不一致（就是上面第 1 點在講的事）。
    cutoff = (pd.Timestamp(price["date"].max()) - pd.Timedelta(days=160 * 1.6)).date().isoformat()
    px = price[(price["date"].astype(str) >= cutoff)].copy()
    px["code"] = px["code"].astype(str)
    px = px[px["code"].isin(codes)][["date", "code", "close", "change", "turnover"]]
    if px.empty:
        return {}
    px["date"] = px["date"].astype(str)
    px = px.sort_values(["code", "date"]).drop_duplicates(["code", "date"], keep="last")
    prev = px["close"] - px["change"].fillna(0)
    # 個股指數＝日報酬累乘，和族群指數（chg_pct 累乘）、大盤指數完全同一套。
    # 起點是窗口第一天（＝1），但 RS-Ratio 是「相對自己的均線」的比值，起點會被約掉，
    # 所以不需要從上市第一天開始累乘。
    px["chg"] = np.where(prev > 0, px["change"] / prev, np.nan)
    px["factor"] = 1 + px["chg"].fillna(0)
    px["gi"] = px.groupby("code")["factor"].cumprod()
    if bench is None:
        bench = market_index(price)
    bench = bench.copy()
    bench.index = bench.index.astype(str)
    px["bi"] = px["date"].map(bench)
    px = px.dropna(subset=["bi"])
    if px.empty:
        return {}
    px = rrg_axes(px, "code")
    latest = str(px["date"].max())

    by_code = {c: sub for c, sub in px.groupby("code")}
    out: dict[str, list] = {}
    for gid, ms in want.items():
        gtv = sum((m.get("turnover") or 0) for m in ms) or 0
        rows = []
        for m in ms:
            code = str(m["code"])
            sub = by_code.get(code)
            if sub is None:
                continue
            sub = sub.dropna(subset=["rs_ratio", "rs_mom"]).tail(trail)
            # 樣本不足（上市未滿 40+10 天）或已經不再交易 → 不輸出（不可以假裝有值）
            if sub.empty or str(sub["date"].iloc[-1]) != latest:
                continue
            last = sub.iloc[-1]
            x, y = float(last["rs_ratio"]), float(last["rs_mom"])
            tv = m.get("turnover") or 0
            rows.append({
                "code": code, "name": m.get("name") or code,
                "x": _v(x), "y": _v(y), "quadrant": quadrant_of(x, y),
                "turnover": _v(tv, 0),
                # 佔比的分母是**所屬族群**（沿用資金去向 D4 的口徑），不是全市場 ——
                # 個股對全市場的佔比常常是 0.1%，整排看起來都一樣，等於沒寫。
                "share": _v(tv / gtv * 100) if gtv else None,
                "has_page": bool(m.get("has_page")),
                "trail": [[str(d), _v(a), _v(b)]
                          for d, a, b in zip(sub["date"], sub["rs_ratio"], sub["rs_mom"])],
            })
        if rows:
            rows.sort(key=lambda r: -(r["turnover"] or 0))
            out[gid] = rows
    return out

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
                 days: int = 60, top_groups: int = 18, top_members: int = 3,
                 company: "pd.DataFrame | None" = None) -> dict:
    """資金去向的**逐日**版本（Andy 2026-09-18 圖六：「一樣都具備相資金輪動的拉Bar
    可以觀察並搭配播放功能」）。

    原本的 `sankey()` 只有今天一天，所以那張圖拉不動也播不了。
    這裡給最近 `days` 天，前端就能像輪動時鐘一樣往回拉、一天一天播。

    ★ 這份要**寫成獨立的 JSON 檔**，不要塞進 flow_v3 ——
      flow_v3 已經是這個網站最大的一份，再加 60 天 × 12 族群 × 3 檔會讓
      每一頁（包含只想看總覽的人）都得先下載它。

    回傳 {dates: [...], groups: [{gid, name, chain, chain_name, tv: [...]}],
          leaves: {date: [{gid, code, name, tv}]}}

    ★ 2026-09-20（Andy：「半導體產業涵蓋 IC 設計、代工、封測，不應該將他們拆開…
      一個節點是半導體產業，後面接續是 IC 設計、代工、封裝」）——
      這裡多送一個 `chain_name`，前端才畫得出「台股成交值 → 產業鏈 → 族群 → 代表股」四層。

      為什麼不是在後端直接把樹組好：前端要能依「被點到哪個族群」重排壓暗、
      依螢幕寬度決定畫幾層，樹的形狀是**畫面的事**；後端只負責把分類講清楚。

      `chain_name` 的來源是 `groups.yaml` 的 `chains:`（唯一人工維護的分類表），
      不在任何鏈裡的兩種各有名字：
        · `industry`＝法定產業別的收容桶（半導體業／電子零組件業／ETF…），
          它們是「不屬於任何人工族群的股票」的集合，和晶圓代工那種真族群不是同一層 ——
          擺在一起看就會像 Andy 說的「半導體被拆開了」，所以獨立成「其他產業別」。
        · `other`＝連產業別都沒有的（理論上不該出現，留一個名字免得畫面上出現 raw id）。

      top_groups 12 → 18（同一次改）：12 個只夠撐出半導體／AI 伺服器／其他產業別三條鏈，
      傳產與一般電子整條看不到，分類層等於只講了一半。18 個剛好把五條鏈都帶出來。
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
    cname = {cid: (c or {}).get("name", cid) for cid, c in (loader.chains() or {}).items()}
    cname.setdefault("industry", "其他產業別")
    cname.setdefault("other", "其他")
    groups = []
    for gid in order:
        sub = g[g["group_id"] == gid].set_index("date")["turnover"].reindex(dates)
        chain = (None if gid not in meta.index or pd.isna(meta.loc[gid].get("chain"))
                 else str(meta.loc[gid]["chain"]))
        groups.append({
            "gid": str(gid),
            "name": str(meta.loc[gid]["group_name"]) if gid in meta.index else str(gid),
            "chain": chain,
            "chain_name": cname.get(chain or "other", cname["other"]),
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
        # ★ 2026-09-20：法定產業別的收容桶（ind_*）不在 `loader.membership()` 裡 ——
        #   它們是 `flow._attach_groups()` 在跑的時候現掛的「沒有人工族群的股票」。
        #   所以以前那 5 個收容桶在圖上**一檔代表股都沒有**，四層之後整條
        #   「其他產業別」底下會是一整排空白格子（電子零組件業是全場第二大，
        #   卻連一檔公司都秀不出來，看起來就像壞了）。
        #   這裡照 `_attach_groups` 同一套規則補上：沒有人工族群的股票掛 ind_<正規化產業別>。
        if company is not None and len(company) and "industry" in company.columns:
            named = set(code2g)
            for c_, ind_ in zip(company["code"], company["industry"]):
                code = str(c_)
                if code in named or ind_ is None or (isinstance(ind_, float) and pd.isna(ind_)):
                    continue
                gid = "ind_" + str(norm_industry(ind_))
                if gid in keep:
                    code2g.setdefault(code, []).append(gid)
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
