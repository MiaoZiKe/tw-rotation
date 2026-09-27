"""個股頁深度資料（v3）：營收、獲利、除權息、資券、大戶散戶、法人、基本資料、本益比歷史。

全部是「把資料湖整理成前端可直接畫的序列」，不做任何預測。
每個函式都容忍該表為空 —— 回補還沒跑到的股票就是會缺，缺就回空清單，前端顯示「尚無資料」。

金融專家的口徑：
- 累計 EPS 用「同一年內各季相加」，跨年歸零；財報是單季值（FinMind 與證交所 t187ap14 都是）。
- 本益比歷史 = 每季財報「可用日」之後的收盤 / 當時可得的近四季 EPS，不偷看未來季報。
- 「大戶」＝集保 1,000 張以上（level 15）；「中實戶」＝400–1,000 張（level 12–14）；
  「散戶」＝10 張以下（level 1–3）。這三個口徑跟坊間籌碼軟體一致。
- 填息天數 = 除息日起，第一個收盤價 ≥ 除息前一日收盤價的交易日數；超過 250 天視為未填息。
"""
from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

BIG_LEVEL = 15                 # ≥ 1,000 張
MID_LEVELS = (12, 13, 14)      # 400–1,000 張
RETAIL_LEVELS = (1, 2, 3)      # ≤ 10 張
TOTAL_LEVEL = 17
DIV_YEAR_DAYS = 320            # 殖利率：最後一次除息往回幾天內算「同一個配息年度」
# ★ 2026-09-26（Andy：「籌碼這邊的時間週期都需要 4 週最少，然後都呈現每日狀況」）：
#   籌碼分頁四張圖改成共用一條逐交易日的日期軸，上方切「4 週｜3 個月｜6 個月｜1 年」。
#   「1 年」要畫得滿，法人與融資券就得各給約一年的交易日（台股一年約 245 天，留 15 天餘裕）。
#   以前法人 120 天、融資券 250 天各給各的，四張圖的起訖日因此對不起來。
CHIP_DAYS = 260
# ★ 2026-09-26（Andy：「除權息為什麼只有一筆……沒有配就顯示空值，但需要標示年份」）：
#   年度股利圖至少畫近 DIV_YEARS 年、每年一根；但不早於資料湖的回補起點
#   （PLAN_DEFAULT 的股利與除權息結果都從 2016-01-01 補起 —— 更早的年份是「不知道」，不是「沒配」），
#   也不早於這一檔有價量的第一年（上市前的年份不是「沒配」，是還不存在）。
DIV_YEARS = 10
DIV_COVER_YEAR = 2016
EVENTS_MAX = 120               # 股利公告最多給幾筆（季配息 10 年 × 現金／股票 ≈ 80）
RESULTS_MAX = 80               # 除權息紀錄最多給幾筆（2016 起季配息約 44 筆）


def _f(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _r(x, nd=2):
    v = _f(x)
    return round(v, nd) if v is not None else None


# ------------------------------------------------------------------ 營收

def revenue_series(rev: pd.DataFrame, code: str, months: int = 72) -> dict:
    """月營收序列：每月營收、YoY、MoM、累計營收、累計 YoY；另附年度合計方便畫「年度走勢」。"""
    if rev is None or rev.empty:
        return {"monthly": [], "yearly": []}
    g = rev[rev["code"] == code][["ym", "revenue"]].copy()
    if g.empty:
        return {"monthly": [], "yearly": []}
    g["revenue"] = pd.to_numeric(g["revenue"], errors="coerce")
    g = g.dropna(subset=["revenue"]).drop_duplicates("ym", keep="last").sort_values("ym")
    g["year"] = g["ym"].str[:4].astype(int)
    g["month"] = g["ym"].str[5:7].astype(int)
    # 用 (year, month) 對齊去年同月，而不是 shift(12)：缺月時 shift 會對錯
    prev = g.set_index(["year", "month"])["revenue"]
    g["yoy"] = [
        (r / prev.get((y - 1, m)) * 100 - 100) if prev.get((y - 1, m)) else None
        for r, y, m in zip(g["revenue"], g["year"], g["month"])
    ]
    g["rev_ly"] = [prev.get((y - 1, m)) for y, m in zip(g["year"], g["month"])]
    # MoM 也要對到「上一個日曆月」，不是上一列：缺月時 pct_change 會拿兩個月前的來比
    g["mom"] = [(r / prev.get((y - (m == 1), 12 if m == 1 else m - 1)) * 100 - 100)
                if prev.get((y - (m == 1), 12 if m == 1 else m - 1)) else None
                for r, y, m in zip(g["revenue"], g["year"], g["month"])]
    g["cum"] = g.groupby("year")["revenue"].cumsum()
    # 累計營收要從 1 月一路都有才算數：缺月時「累計」少了一個月，累計 YoY 會系統性偏低
    g["cum"] = g["cum"].where(g.groupby("year").cumcount() + 1 == g["month"])
    cum_prev = g.set_index(["year", "month"])["cum"]
    g["cum_yoy"] = [
        (c / cum_prev.get((y - 1, m)) * 100 - 100) if (pd.notna(c) and pd.notna(cum_prev.get((y - 1, m), np.nan))
                                                         and cum_prev.get((y - 1, m))) else None
        for c, y, m in zip(g["cum"], g["year"], g["month"])
    ]
    tail = g.tail(months)
    # ★ 2026-09-27：列尾多一欄「去年同月營收」（Andy 的券商 App：月走勢是當月＋去年同期兩組柱並排）
    monthly = [[r.ym, _r(r.revenue, 0), _r(r.yoy, 1), _r(r.mom, 1), _r(r.cum, 0), _r(r.cum_yoy, 1), _r(r.rev_ly, 0)]
               for r in tail.itertuples()]
    yearly = []
    for y, gg in g.groupby("year"):
        yearly.append({"year": int(y), "months": int(len(gg)),
                       "revenue": _r(gg["revenue"].sum(), 0),
                       "by_month": {int(m): _r(v, 0) for m, v in zip(gg["month"], gg["revenue"])}})
    return {"monthly": monthly, "yearly": yearly[-7:],
            "columns": ["ym", "revenue", "yoy", "mom", "cum", "cum_yoy", "revenue_last_year"]}


# ------------------------------------------------------------------ 獲利

def _single_quarter_frame(fin: pd.DataFrame, code: str) -> pd.DataFrame:
    """這一檔的季損益，**一律先還原成單季**，依 (year, quarter) 排序、去重。

    ★ 2026-09-27（個股頁數據普查）：資料湖的 financial_q 混了兩種口徑 ——
      FinMind 給單季；每日管線的證交所 t187ap14 給「年度累計」（Q2＝上半年、Q3＝前三季、Q4＝全年）。
      ttm() 早就先過 fundamental._decumulate()（DECISIONS #88），個股頁的季損益與本益比歷史卻直接吃原表：
      2026-09-26 實測 1,040 檔的 2026Q2 是證交所累計列，2618 長榮航季報寫「2026Q2 EPS 2.24、營收 1,283 億」，
      其實是上半年合計（單季 0.71 元、678 億）；本益比歷史的最後一段 TTM 也因此灌水。
      Q4 若來自證交所（全年累計），同一套還原就是「年報 − 前三季」；FinMind 的 Q4 本來就是單季。
    ⚠ _decumulate 不是冪等的（它用「沒有 announce_date」判斷累計列，還原後旗標不變），
      所以只能在這裡做一次，呼叫端一律傳原表進來。
    """
    from .fundamental import _decumulate
    if fin is None or fin.empty or "code" not in fin.columns:
        return pd.DataFrame()
    g = fin[fin["code"] == code].copy()
    if g.empty:
        return g
    for c in ("year", "quarter"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    g = g.dropna(subset=["year", "quarter"])
    g = g[g["quarter"].isin([1, 2, 3, 4])]
    if g.empty:
        return g
    g["year"] = g["year"].astype(int); g["quarter"] = g["quarter"].astype(int)
    g = g.sort_values(["year", "quarter"]).drop_duplicates(["year", "quarter"], keep="last")
    g = _decumulate(g.reset_index(drop=True))
    for c in ("revenue", "gross_profit", "operating_income", "net_income", "eps"):
        g[c] = pd.to_numeric(g[c], errors="coerce") if c in g.columns else np.nan
    return g.sort_values(["year", "quarter"]).reset_index(drop=True)


PROFIT_QUARTERS = 40     # 季損益給幾季：資料湖 2016Q1 起約 42 季，全部給（以前只給 24 季）
PROFIT_YEARS = 10        # 年度損益給幾年


def profit_series(fin: pd.DataFrame, code: str, quarters: int = PROFIT_QUARTERS,
                  asof: str | None = None) -> dict:
    """季損益 ＋ 年度損益。

    quarters（每季一列）：[期別, 營收, 毛利率, 營益率, 淨利率, EPS, 年度累計 EPS, EPS 年增（元）, 淨利]
    - 單季值：證交所累計列先還原（見 _single_quarter_frame）。
    - **季標籤連續**：第一季到最後一季之間缺的季補一列空值（除了期別全是 None），
      圖的 x 軸不會把 2019Q2 直接接到 2019Q4 而看不出斷層；缺的期別另列在 `gaps`。
    - 毛利率＝毛利 ÷ 營收、營益率＝營業利益 ÷ 營收、淨利率＝淨利 ÷ 營收（%）；營收 0 或缺 → None。
    - 年度累計 EPS＝同一年 Q1 起逐季相加，**中間缺任何一季就從那季起給 None**（不拿缺季湊累計）。
    - EPS 年增＝本季 EPS − 去年同季 EPS（元，不是 %，EPS 可能跨零）。

    yearly（每年一列，dict）：year, quarters（有幾季）, eps（四季加總）, revenue, net_income, gm/om/nm, partial
    - 年 EPS ＝ 四季單季 EPS 相加（跟「年報 EPS」差在加權股數，差距通常 < 1%，口徑與 TTM 一致）。
    - 三率用金額相加後再除（Σ毛利 ÷ Σ營收），不是四季比率的平均。
    - 四季不齊的年份：今年（還沒過完）給前 n 季合計並標 partial＝True、前端要寫「前 n 季」；
      過去年份缺季 → eps 等欄位給 None（不給三季當全年）。

    asof（資料日）有給時多一個 `timing`：法定期限下這一天「至少應該有」到哪一季（expected）、
    「最多可能有」到哪一季（max_possible＝季底已過）、實際最新（latest）與判定：
      ok ＝ expected ≤ latest ≤ max_possible；missing ＝ 已過法定期限卻還沒有；future ＝ 季底都還沒到卻有資料（資料錯）。
    """
    from .fundamental import quarter_timing
    out = {"quarters": [], "yearly": [], "gaps": [],
           "columns": ["period", "revenue", "gross_margin", "op_margin", "net_margin",
                       "eps", "eps_cum", "eps_yoy_diff", "net_income"]}
    g = _single_quarter_frame(fin, code)
    if g.empty:
        if asof:
            out["timing"] = quarter_timing(asof, None)
        return out
    g["qidx"] = g["year"] * 4 + g["quarter"] - 1
    full = pd.DataFrame({"qidx": np.arange(int(g["qidx"].min()), int(g["qidx"].max()) + 1)})
    full["year"] = full["qidx"] // 4
    full["quarter"] = full["qidx"] % 4 + 1
    g = full.merge(g.drop(columns=["year", "quarter"]), on="qidx", how="left")
    g["have"] = g["eps"].notna() | g["revenue"].notna()
    rv = g["revenue"].where(g["revenue"] != 0)
    g["gm"] = g["gross_profit"] / rv * 100
    g["om"] = g["operating_income"] / rv * 100
    g["nm"] = g["net_income"] / rv * 100
    # 年度累計：Q1 起一路都有 EPS 才累計，斷掉之後同一年全部 None
    cum, run_y, run_v, ok = [], None, 0.0, True
    for y, q, e in zip(g["year"], g["quarter"], g["eps"]):
        if y != run_y:
            run_y, run_v, ok = y, 0.0, True
        if q == 1:
            ok = True
        if ok and pd.notna(e):
            run_v += float(e)
            cum.append(run_v)
        else:
            ok = False
            cum.append(None)
    g["eps_cum"] = cum
    prev = dict(zip(g["qidx"], g["eps"]))
    g["eps_yoy"] = [(e - prev[i - 4]) if (pd.notna(e) and pd.notna(prev.get(i - 4, np.nan))) else None
                    for i, e in zip(g["qidx"], g["eps"])]
    out["gaps"] = [f"{y}Q{q}" for y, q, h in zip(g["year"], g["quarter"], g["have"]) if not h]
    tail = g.tail(quarters)
    # 三率給 2 位小數（Andy 給的券商 App 對照：2344 2026Q2 毛利率 66.25%、淨利率 40.44%，1 位會被讀成對不上）
    out["quarters"] = [[f"{r.year}Q{r.quarter}", _r(r.revenue, 0), _r(r.gm, 2), _r(r.om, 2), _r(r.nm, 2),
                        _r(r.eps, 2), _r(r.eps_cum, 2), _r(r.eps_yoy, 2), _r(r.net_income, 0)]
                       for r in tail.itertuples()]
    last_have = g[g["have"]].iloc[-1]
    latest = f"{int(last_have['year'])}Q{int(last_have['quarter'])}"
    cur_year = int(str(asof)[:4]) if asof else int(last_have["year"])
    yearly = []
    for y, gy in g.groupby("year"):
        gy = gy[gy["have"]]
        n = int(len(gy))
        qs = sorted(gy["quarter"].tolist())
        partial = n < 4
        # 今年還沒過完：前 n 季（必須從 Q1 起連續）照樣給合計，標 partial；過去年份缺季就不給數字
        usable = (not partial) or (int(y) >= cur_year and qs == list(range(1, n + 1)))
        def ssum(col):
            v = pd.to_numeric(gy[col], errors="coerce")
            return float(v.sum()) if usable and n and v.notna().all() else None
        rev, gp, oi, ni, eps = (ssum(c) for c in ("revenue", "gross_profit", "operating_income", "net_income", "eps"))
        yearly.append({"year": int(y), "quarters": n, "partial": bool(partial),
                       "eps": _r(eps, 2), "revenue": _r(rev, 0), "net_income": _r(ni, 0),
                       "gm": _r(gp / rev * 100, 2) if gp is not None and rev else None,
                       "om": _r(oi / rev * 100, 2) if oi is not None and rev else None,
                       "nm": _r(ni / rev * 100, 2) if ni is not None and rev else None})
    out["yearly"] = yearly[-PROFIT_YEARS:]
    if asof:
        out["timing"] = quarter_timing(asof, latest)
    return out


# ------------------------------------------------------------------ 指標標籤

TAG_RULES = [
    ("rev_yoy3_20", "連三月營收年增>20%"),
    ("rev_high_m", "月營收創新高"),
    ("rev_high_q", "近一季營收創新高"),
    ("q_rev_yoy_3of4_20", "近四季有三季營收年增>20%"),
    ("q_om_3of4_10", "近四季有三季營益率>10%"),
    ("q_gm_3of4_30", "近四季有三季毛利率>30%"),
    ("rev_streak", "連續 N 個月營收年增"),
    ("eps_pos4", "近四季 EPS 皆為正"),
]


def stock_tags(rev: pd.DataFrame | None, fin: pd.DataFrame | None, code: str) -> dict:
    """「指標」分頁的條件標籤（2026-09-27，Andy 給的券商 App「符合 65 項指標」截圖）。

    **只陳述事實條件，不做推介**：每一條都寫出判斷用的數字（detail）與比較範圍，符合／不符合都回傳，
    前端把符合的列在上面、不符合的收在下面，不挑好看的講。資料不夠判斷 → hit＝None、detail 寫原因。

    規則（月營收用資料湖全部月份、季資料用還原成單季的季損益）：
    - 連三月營收年增>20%：最近三個**連續**月份的 YoY 都 > 20%（YoY 用同月對同月）。
    - 月營收創新高：最新一個月 > 資料湖內這一檔所有更早月份（比較範圍寫在 detail，例如「2016-01 起 128 個月」）。
    - 近一季營收創新高：最新一季單季營收 > 所有更早的季（同上，寫比較範圍）。
    - 近四季有三季營收年增>20%／營益率>10%／毛利率>30%：最近四個**連續**季，至少三季達標；缺季 → 不判斷。
    - 連續 N 個月營收年增：從最新月往回數 YoY > 0 的連續月數，N ≥ 3 才算符合（N 寫在標籤裡）。
    - 近四季 EPS 皆為正：最近四個連續季 EPS 都 > 0。
    「台灣 50／MSCI 成分股」「集團」沒有白名單內的合規來源，不做（見 DECISIONS）。
    """
    items: dict[str, dict] = {k: {"id": k, "kind": "指標", "label": lab, "hit": None, "detail": "資料不足"}
                              for k, lab in TAG_RULES}
    if rev is not None and not rev.empty:
        g = rev[rev["code"] == code][["ym", "revenue"]].copy()
        g["revenue"] = pd.to_numeric(g["revenue"], errors="coerce")
        g = g.dropna().drop_duplicates("ym", keep="last").sort_values("ym")
        if len(g):
            g["y"] = g["ym"].str[:4].astype(int); g["m"] = g["ym"].str[5:7].astype(int)
            g["mi"] = g["y"] * 12 + g["m"]
            val = dict(zip(g["mi"], g["revenue"]))
            g["yoy"] = [(v / val[i - 12] * 100 - 100) if val.get(i - 12) else np.nan for i, v in zip(g["mi"], g["revenue"])]
            t3 = g.tail(3)
            if len(t3) == 3 and t3["mi"].iloc[-1] - t3["mi"].iloc[0] == 2 and t3["yoy"].notna().all():
                items["rev_yoy3_20"].update(hit=bool((t3["yoy"] > 20).all()),
                                            detail="、".join(f"{a[2:]} {b:+.1f}%" for a, b in zip(t3["ym"], t3["yoy"])))
            if len(g) >= 13:
                last, prior = g.iloc[-1], g.iloc[:-1]
                # 嚴格大於：跟前高打平不算「創新高」（跟近一季創新高同一個判準）
                items["rev_high_m"].update(hit=bool(last["revenue"] > prior["revenue"].max()),
                                           detail=f"{last['ym']} {last['revenue'] / 1e8:,.2f} 億；比較 {prior['ym'].iloc[0]} 起 {len(prior)} 個月"
                                                  f"（前高 {prior['revenue'].max() / 1e8:,.2f} 億）")
            n = 0
            for i, y_ in zip(reversed(g["mi"].tolist()), reversed(g["yoy"].tolist())):
                if pd.notna(y_) and y_ > 0 and (n == 0 or i == prev_i - 1):
                    n += 1; prev_i = i
                else:
                    break
            if g["yoy"].notna().any():
                items["rev_streak"].update(label=f"連續 {n} 個月營收年增" if n >= 3 else "連續 N 個月營收年增",
                                           hit=n >= 3, detail=f"截至 {g['ym'].iloc[-1]} 連續 {n} 個月 YoY > 0")
    q = _single_quarter_frame(fin, code) if fin is not None else pd.DataFrame()
    if not q.empty:
        q = q.copy()
        q["qi"] = q["year"] * 4 + q["quarter"] - 1
        rv = dict(zip(q["qi"], q["revenue"]))
        q["ryoy"] = [(v / rv[i - 4] * 100 - 100) if (pd.notna(v) and rv.get(i - 4)) else np.nan
                     for i, v in zip(q["qi"], q["revenue"])]
        with np.errstate(divide="ignore", invalid="ignore"):
            q["gm"] = np.where(q["revenue"] > 0, q["gross_profit"] / q["revenue"] * 100, np.nan)
            q["om"] = np.where(q["revenue"] > 0, q["operating_income"] / q["revenue"] * 100, np.nan)
        lab = lambda r: f"{int(r.year)}Q{int(r.quarter)}"  # noqa: E731
        qq = q.dropna(subset=["revenue"])
        if len(qq) >= 5:
            last, prior = qq.iloc[-1], qq.iloc[:-1]
            items["rev_high_q"].update(hit=bool(last["revenue"] > prior["revenue"].max()),
                                       detail=f"{lab(last)} 單季 {last['revenue'] / 1e8:,.2f} 億；比較 {lab(prior.iloc[0])} 起 {len(prior)} 季"
                                              f"（前高 {prior['revenue'].max() / 1e8:,.2f} 億）")
        t4 = q.tail(4)
        if len(t4) == 4 and t4["qi"].iloc[-1] - t4["qi"].iloc[0] == 3:
            for key, col, thr in (("q_rev_yoy_3of4_20", "ryoy", 20), ("q_om_3of4_10", "om", 10), ("q_gm_3of4_30", "gm", 30)):
                v = t4[col]
                if v.notna().all():
                    items[key].update(hit=bool((v > thr).sum() >= 3),
                                      detail="、".join(f"{lab(r)} {getattr(r, col):.1f}%" for r in t4.itertuples()))
            e = t4["eps"]
            if e.notna().all():
                items["eps_pos4"].update(hit=bool((e > 0).all()),
                                         detail="、".join(f"{lab(r)} {r.eps:.2f}" for r in t4.itertuples()))
        else:
            for key in ("q_rev_yoy_3of4_20", "q_om_3of4_10", "q_gm_3of4_30", "eps_pos4"):
                items[key]["detail"] = "最近四季不連續（有缺季），不判斷"
    out = list(items.values())
    return {"items": out, "n_hit": sum(1 for x in out if x["hit"])}


# ------------------------------------------------------------------ 本益比歷史

def pe_daily(price: pd.DataFrame, fin: pd.DataFrame, code: str,
             shares: dict | None = None, quarters: int | None = None) -> pd.DataFrame:
    """逐日本益比：[date, close, ttm_eps, pe, period, from]。price 必須是**原始**（未還原）收盤。

    公式：PE_d ＝ 原始收盤_d ÷ TTM_d，
          TTM_d ＝ Σ(近四季 eps_q ÷ eps_divisor(..., d))  —— 每季 EPS 換算到 d 當天的股本。
    所以除權當天收盤掉到 1/2.98、TTM 也同步除以 2.98，本益比連續（R5：6669 從 20 掉到 6.7 就是少了這步）。
    - 只用公布日（缺值用法定期限）之後的價格，不偷看未來季報。
    - 四季不連續或任一季缺 EPS → 那一段不給；TTM ≤ 0 → pe 為 NaN（不給負數）。
    - quarters：只算最後幾季（個股頁只要 5 年，全算會多花好幾倍時間）。
    效能：TTM 只會在「新季報」或「股數事件」那天變，所以區段再依事件日切開、每一小段向量化，
    不逐日呼叫查表（逐日版本全市場要多 10 分鐘以上）。
    """
    from .fundamental import eps_divisor, eps_basis_info
    cols = ["date", "close", "ttm_eps", "pe", "period", "from"]
    if fin is None or fin.empty or price is None or price.empty:
        return pd.DataFrame(columns=cols)
    # ★ 2026-09-27：先還原成單季（證交所累計列，見 _single_quarter_frame）—— 以前 2026Q2 那一段的 TTM
    #   把「上半年合計」當成單季，1,040 檔的本益比歷史最後一段被系統性壓低。
    g = _single_quarter_frame(fin, code)
    if g.empty:
        return pd.DataFrame(columns=cols)
    g["qidx"] = g["year"] * 4 + g["quarter"]
    g = g.sort_values("qidx").drop_duplicates("qidx", keep="last").reset_index(drop=True)
    g["eps"] = pd.to_numeric(g["eps"], errors="coerce")
    info = eps_basis_info(g)                    # 在完整序列上算（隱含股數要上一季）
    pend = [x[0] for x in info]; avail = [x[1] for x in info]; impl = [x[2] for x in info]
    px = price[price["code"] == code][["date", "close"]]
    dates = px["date"].astype(str).to_numpy()
    closes = pd.to_numeric(px["close"], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(closes) & (closes > 0)
    dates, closes = dates[ok], closes[ok]
    order = np.argsort(dates, kind="stable")
    dates, closes = dates[order], closes[order]
    if len(dates) == 0:
        return pd.DataFrame(columns=cols)
    ent = (shares or {}).get(str(code))
    ev_dates = ent[0] if ent is not None else []
    qidx = g["qidx"].to_numpy(); eps = g["eps"].to_numpy(dtype=float)
    first_i = 3 if quarters is None else max(3, len(g) - int(quarters))
    parts = []
    for i in range(first_i, len(g)):
        if qidx[i] - qidx[i - 3] != 3 or np.isnan(eps[i - 3: i + 1]).any():
            continue
        start = avail[i]
        end = avail[i + 1] if i + 1 < len(g) else "9999-12-31"
        lo, hi = np.searchsorted(dates, start, "left"), np.searchsorted(dates, end, "left")
        if hi <= lo:
            continue
        sd, sc = dates[lo:hi], closes[lo:hi]
        # 區段內的股數事件日把這段再切開；每一小段 TTM 是常數
        cuts = [0] + [int(np.searchsorted(sd, e, "left")) for e in ev_dates if sd[0] < e <= sd[-1]] + [len(sd)]
        t = np.empty(len(sd))
        for a_, b_ in zip(cuts[:-1], cuts[1:]):
            if b_ <= a_:
                continue
            d0 = sd[a_]
            t[a_:b_] = sum(eps[k] / (eps_divisor(shares, code, pend[k], avail[k], d0, impl[k]) if ent is not None else 1.0)
                           for k in range(i - 3, i + 1))
        # ★ 2026-09-26（小數點普查）：四季 EPS 相加有浮點殘差（0.1＋(-0.3)＋0.2＝5.5e-17），
        #   不先捨入就會被當成「正的 TTM」，本益比算成 5.3e+18（3504 2026Q2、6226 2022Q3 實際發生）。
        #   捨到 1e-6 只抹掉殘差（EPS 本身只有 2 位），「TTM ≤ 0 不給本益比」的口徑不變。
        t = np.round(t, 6)
        with np.errstate(divide="ignore", invalid="ignore"):
            pe = np.where(t > 0, sc / t, np.nan)
        parts.append(pd.DataFrame({"date": sd, "close": sc, "ttm_eps": t, "pe": pe,
                                   "period": f"{g.at[i, 'year']}Q{g.at[i, 'quarter']}", "from": sd[0]}))
    if not parts:
        return pd.DataFrame(columns=cols)
    return pd.concat(parts, ignore_index=True)[cols]


def pe_history(price: pd.DataFrame, fin: pd.DataFrame, code: str, years: int = 5,
               shares: dict | None = None, adj_price: pd.DataFrame | None = None) -> list:
    """每季一個點：季報可用日之後的第一個收盤 / 當時近四季 EPS，外加該季區間的最高與最低本益比。

    price 是**原始**收盤（本益比用的是當天真的價格 ÷ 當天股本下的 EPS，見 pe_daily）。
    ttm_eps 欄位要給前端「本益比河流圖」拿去跟**還原 K 線**相除，所以換算到還原價的基準：
      ttm_eps_輸出 ＝ 區段最後一天的 收盤_還原 ÷ PE
    這樣河流圖的 收盤_還原 ÷ ttm_eps 在區段最後一天會精確等於真的本益比；
    區段內若有除息，前面幾天的偏差不超過那次的現金殖利率（除權的股數部分則完全抵銷）。
    沒給 adj_price 時 ttm_eps 就是當天股本下的 TTM（舊行為）。虧損（TTM ≤ 0）的季度給 None。
    """
    d = pe_daily(price, fin, code, shares, quarters=years * 4 + 1)
    if d.empty:
        return []
    adj_map = None
    if adj_price is not None and not adj_price.empty:
        a = adj_price[adj_price["code"] == code]
        adj_map = pd.Series(pd.to_numeric(a["close"], errors="coerce").to_numpy(),
                            index=a["date"].astype(str).to_numpy())
        adj_map = adj_map[~adj_map.index.duplicated(keep="last")]
    rows = []
    per = d["period"].to_numpy()
    brk = np.flatnonzero(per[1:] != per[:-1]) + 1
    for a_, b_ in zip(np.r_[0, brk], np.r_[brk, len(d)]):
        seg = d.iloc[a_:b_]
        last = seg.iloc[-1]
        ttm_raw = float(last["ttm_eps"])
        if ttm_raw <= 0:
            rows.append({"period": last["period"], "ttm_eps": round(ttm_raw, 2),
                         "pe": None, "pe_high": None, "pe_low": None, "from": seg["from"].iloc[0]})
            continue
        ttm_out = ttm_raw
        if adj_map is not None:
            ac = adj_map.get(last["date"])
            if ac is not None and pd.notna(ac) and ac > 0 and pd.notna(last["pe"]) and last["pe"] > 0:
                ttm_out = float(ac) / float(last["pe"])
        pes = seg["pe"].dropna()
        rows.append({"period": last["period"], "ttm_eps": round(ttm_out, 2),
                     "pe": _r(seg["pe"].iloc[0], 1),
                     "pe_high": _r(pes.max(), 1) if len(pes) else None,
                     "pe_low": _r(pes.min(), 1) if len(pes) else None,
                     "from": seg["from"].iloc[0]})
    return rows[-years * 4:]


# ------------------------------------------------------------------ 除權息

def _is_date(s) -> bool:
    """YYYY-MM-DD 才算有日期（公告的除權息日可能是 None／NaN／空字串／'NaT'）。"""
    s = str(s or "")[:10]
    return len(s) == 10 and s[4] == "-" and s[7] == "-" and s[:4].isdigit()


_HALF = {"後半年度": "H2", "下半年": "H2", "下半年度": "H2", "前半年度": "H1", "上半年": "H1", "上半年度": "H1"}


def period_label(period, fiscal_year=None) -> str | None:
    """股利所屬期間的顯示標籤（2026-09-27，Andy 的券商 App 表格用「2025H2、2025H1」）。

    FinMind／證交所的 period 是民國字串：「114年」→「2025」、「114年後半年度」「114年下半年」→「2025H2」、
    「114年前半年度」「114年上半年」→「2025H1」、「114年第3季」→「2025Q3」。
    其他寫法（「113年度及114年上半年」這種合併分派、資本公積）→ 用 fiscal_year 加原字串尾巴，不硬套。
    同一期兩家來源寫法不同（「下半年」vs「後半年度」）在這裡收成同一個標籤，upcoming 才去得了重。
    """
    s_ = str(period or "").strip()
    m = re.match(r"^(\d{2,3})年(.*)$", s_)
    if not m:
        return (str(int(fiscal_year)) if fiscal_year is not None and pd.notna(fiscal_year) else None) if not s_ else s_
    y = int(m.group(1)) + 1911
    rest = m.group(2).strip()
    if rest in ("", "度", "年度"):
        return str(y)
    if rest in _HALF:
        return f"{y}{_HALF[rest]}"
    q = re.match(r"^第([1-4])季$", rest)
    if q:
        return f"{y}Q{q.group(1)}"
    return f"{y} {rest}"


def div_year_bars(events: pd.DataFrame, results: pd.DataFrame, price: pd.DataFrame | None,
                  code: str, asof: str | None, cover_from: int | None = None) -> tuple[list, list]:
    """年度股利長條（每年一根）＋已公告、尚未除權息的清單。回傳 (bars, upcoming)。

    口徑（金融專家 2026-09-26，DECISIONS #266）：
    - **年度＝除權息日所在的西元年**（實際配發那一年，坊間「股利發放年度」同一口徑），
      不是股利所屬年度。理由：①官方除權息結果（dividend_results）2016 年起每一檔都補齊了，
      股利公告（dividend_events）卻有 600 多檔的歷史被回補跳過（見 run_backfill.already_covered），
      用除權息日才有一份每檔都完整的日期；②跟「除權息紀錄」表的年份一一對得上；
      ③季配息股同一個所屬年度的四次會跨兩個西元年發放，用所屬年度要等隔年最後一季公告才完整。
    - 同一年多次除權息（季配、半年配）加總；`items` 逐次列出（前端提示框用）。
    - 現金、股票分開：金額取自同一除權息日的股利公告（元／股，**當時公告的每股金額**，不換算成今天股數 ——
      這張圖回答「那一年配了多少」，不是殖利率；殖利率另有換算，見 dividends()）。
      對不到公告時：純「息」用官方結果的股利（除息價差本身就是現金股利）；
      含「權」又對不到公告 → 那一次的金額留空不猜、`unknown` +1
      （參考價反推只拿得到「配股率 × 價格」的混合值，拆不出現金與股票各多少）。
    - 沒有任何除權息的年份照樣給一根：cash = stock = 0、n = 0（前端 0 高度、x 軸照樣標年份）。
    - 年份範圍：end ＝ asof 的年份（沒給 asof 用資料最後一年）；
      start ＝ max(min(資料最早年, end − DIV_YEARS + 1), DIV_COVER_YEAR, 這一檔價量第一年)。
      —— 2016 之前是「資料湖沒補」，上市之前是「還不存在」，兩者都不是「沒配」，所以不畫。
      end 那一年若還沒過完，標 `partial`（今年還沒結束，別拿去跟整年比）。
    - 除權息日在 asof 之後、或還沒訂的公告不進長條，另列 `upcoming`。
    """
    asof_s = str(asof)[:10] if asof else None
    paid: dict[str, dict[str, float]] = {}
    period_of: dict[str, str] = {}
    upcoming: list[dict] = []
    if events is not None and not events.empty and "ex_date" in events.columns:
        e = events[events["code"] == code] if "code" in events.columns else events
        # ★ 2026-09-27：同一期同一種股利，證交所（每日管線）寫「114年下半年」、沒有除息日；
        #   FinMind（回補）寫「114年後半年度」、有除息日 —— 以前沒有日期那筆被當成「已公告、尚未除息」，
        #   2344 的 2025H2 現金 0.5 元早在 2026-03-27 除息了，卻一直掛在「即將除權息」。
        dated = {(period_label(r.get("period"), r.get("fiscal_year")), str(r.get("kind") or ""))
                 for _, r in e.iterrows() if _is_date(r.get("ex_date"))}
        for _, r in e.iterrows():
            amt = _f(r.get("amount"))
            if amt is None:
                continue
            d = str(r.get("ex_date") or "")[:10]
            kind = str(r.get("kind") or "")
            if not _is_date(d) and (period_label(r.get("period"), r.get("fiscal_year")), kind) in dated:
                continue
            if not _is_date(d) or (asof_s and d > asof_s):
                upcoming.append({"period": r.get("period"), "kind": kind or None, "amount": _r(amt, 4),
                                 "announce_date": r.get("announce_date") if _is_date(r.get("announce_date")) else None,
                                 "ex_date": d if _is_date(d) else None})
                continue
            paid.setdefault(d, {}).setdefault(kind, 0.0)
            paid[d][kind] += amt
            period_of.setdefault(d, str(r.get("period") or ""))

    items: dict[str, dict] = {}
    if results is not None and not results.empty:
        rs = results[results["code"] == code] if "code" in results.columns else results
        for _, r in rs.iterrows():
            d = str(r.get("date"))[:10]
            if not _is_date(d) or (asof_s and d > asof_s):
                continue
            kind = str(r.get("kind") or "")
            got = paid.get(d, {})
            if "權" in kind:
                cash = got.get("cash", None if "息" in kind else 0.0)
                stock = got.get("stock")
            else:
                cash = got.get("cash", _f(r.get("dividend")))
                stock = got.get("stock", 0.0)
            bp = _f(r.get("before_price"))
            items[d] = {"date": d, "kind": kind or None, "cash": cash, "stock": stock,
                        "period": period_of.get(d) or None,
                        # 現金殖利率（這一次）＝現金股利 ÷ 除息前一日收盤（官方結果的 before_price）
                        "cash_yield": (cash / bp * 100) if (cash and bp and bp > 0) else (0.0 if cash == 0 else None)}
    # 有公告、官方結果卻還沒進湖的除權息日（結果表偶爾晚幾天）：用公告補上，不讓那一次憑空消失
    for d, got in paid.items():
        if d not in items:
            kind = ("權" if got.get("stock") else "") + ("息" if got.get("cash") else "")
            items[d] = {"date": d, "kind": kind or None, "cash": got.get("cash", 0.0),
                        "stock": got.get("stock", 0.0), "period": period_of.get(d) or None,
                        "cash_yield": None}      # 沒有官方結果就沒有除息前收盤，不自己拿別天的價格湊
    upcoming.sort(key=lambda x: (x.get("ex_date") or "9999-99-99", str(x.get("announce_date") or "")))

    years_have = sorted({int(d[:4]) for d in items})
    end = int(asof_s[:4]) if asof_s else (years_have[-1] if years_have else None)
    if end is None:
        return [], upcoming
    # ★ 2026-09-27（Andy：「時間軸往前拉到 2009，資料湖有多少就畫多少」）：不再只畫近 10 年。
    #   start ＝ max(這一檔的回補起點 cover_from, 這一檔「存在」的第一年)；
    #   存在的第一年＝min(價量第一年, 最早一次除權息年) —— 價量只從 2016 補起的股票，2009 年有配息就代表那年已經上市。
    #   cover_from 由 build_payload 依回補進度給（2009 那一步補過的是 2009，否則 2016）：
    #   沒補過的年份是「不知道」不是「沒配」，不能畫成 0。
    cover = int(cover_from) if cover_from else DIV_COVER_YEAR
    exist = years_have[0] if years_have else end
    if price is not None and not price.empty and "date" in price.columns:
        px = price[price["code"] == code] if "code" in price.columns else price
        if not px.empty:
            exist = min(exist, int(str(px["date"].astype(str).min())[:4]))
    start = min(max(cover, exist), end)
    by: dict[int, list] = {}
    for d, it in items.items():
        by.setdefault(int(d[:4]), []).append(it)
    bars = []
    for y in range(start, end + 1):
        its = sorted(by.get(y, []), key=lambda x: x["date"])
        cash = sum(x["cash"] for x in its if x["cash"] is not None)
        stock = sum(x["stock"] for x in its if x["stock"] is not None)
        unknown = sum(1 for x in its if x["cash"] is None or x["stock"] is None)
        # 年度現金殖利率＝Σ(每次現金股利 ÷ 該次除息前一日收盤)。任何一次有現金卻算不出殖利率 → 整年給 None（不拿部分次數湊）
        ys = [x.get("cash_yield") for x in its if x["cash"]]
        if any(x["cash"] is None for x in its):
            yld = None                       # 有一次現金金額不知道 → 年度殖利率也不知道
        elif ys:
            yld = sum(ys) if all(v is not None for v in ys) else None
        else:
            yld = 0.0                        # 這一年沒有現金股利
        bars.append({"year": y, "cash": _r(cash, 4), "stock": _r(stock, 4), "n": len(its), "unknown": unknown,
                     "cash_yield": _r(yld, 2),
                     "partial": bool(asof_s and y == end and asof_s[5:10] < "12-31"),
                     "items": [{**x, "cash": _r(x["cash"], 4), "stock": _r(x["stock"], 4),
                                "cash_yield": _r(x.get("cash_yield"), 2)} for x in its]})
    return bars, upcoming


def dividend_periods(e_all: pd.DataFrame, r_all: pd.DataFrame, asof: str | None = None) -> list:
    """股利**所屬期間**表（2026-09-27，Andy 的券商 App：年度欄是「2025H2、2025H1」）。

    一列＝一個所屬期間（period_label：2025、2025H2、2025Q3），欄位：
      cash／stock（元，當時公告值）、cash_ex_date（除息日）、stock_ex_date（除權日）、payment_date（現金發放日）、
      cash_yield（%，＝現金股利 ÷ 除息前一日收盤，收盤取官方除權息結果 before_price；對不到結果給 None）、
      status：paid（除權息日已過）／upcoming（日期在 asof 之後）／pending（還沒訂日期）。
    跟 by_year（除權息日所在西元年）並存：by_year 回答「那一年實際拿到多少」，這張回答「那一期（哪一段盈餘）配多少」。
    季配息的 2025Q4 會在 2026 年發，所以同一筆錢在兩張表的「年」不一樣，這是口徑不同，不是錯。
    """
    if e_all is None or e_all.empty:
        return []
    bp = {}
    if r_all is not None and not r_all.empty and "before_price" in r_all.columns:
        bp = {str(d)[:10]: _f(v) for d, v in zip(r_all["date"], r_all["before_price"])}
    asof_s = str(asof)[:10] if asof else None
    rows: dict[tuple, dict] = {}
    for _, r in e_all.iterrows():
        lab = period_label(r.get("period"), r.get("fiscal_year"))
        if not lab:
            continue
        fy = r.get("fiscal_year")
        key = (lab,)
        it = rows.setdefault(key, {"period": lab, "fiscal_year": int(fy) if pd.notna(fy) else None,
                                   "raw_period": r.get("period"), "cash": None, "stock": None,
                                   "cash_ex_date": None, "stock_ex_date": None, "payment_date": None,
                                   "announce_date": None})
        kind = str(r.get("kind") or "")
        amt = _f(r.get("amount"))
        exd = str(r.get("ex_date"))[:10] if _is_date(r.get("ex_date")) else None
        if kind in ("cash", "stock") and amt is not None:
            # 同一期兩家來源各寫一筆（下半年／後半年度）：有除權息日的那筆為準，不重複加
            have_date = it[f"{kind}_ex_date"]
            if it[kind] is None or (exd and not have_date):
                it[kind] = amt
            if exd:
                it[f"{kind}_ex_date"] = exd
        if kind == "cash" and _is_date(r.get("payment_date")):
            it["payment_date"] = str(r.get("payment_date"))[:10]
        if _is_date(r.get("announce_date")):
            a = str(r.get("announce_date"))[:10]
            it["announce_date"] = max(it["announce_date"] or a, a)
    out = []
    for it in rows.values():
        dates = [d for d in (it["cash_ex_date"], it["stock_ex_date"]) if d]
        if not dates:
            it["status"] = "pending"
        elif asof_s and max(dates) > asof_s:
            it["status"] = "upcoming"
        else:
            it["status"] = "paid"
        b = bp.get(it["cash_ex_date"]) if it["cash_ex_date"] else None
        it["cash_yield"] = _r(it["cash"] / b * 100, 2) if (it["cash"] and b and b > 0) else None
        it["cash"] = _r(it["cash"], 4); it["stock"] = _r(it["stock"], 4)
        out.append(it)
    # 由新到舊：先年度，同年度再 H2 > H1、Q4 > Q1 > 年度（年度字串最短）
    rank = lambda p: (int(p[:4]) if p[:4].isdigit() else 0, p[4:])  # noqa: E731
    out.sort(key=lambda x: rank(x["period"]), reverse=True)
    return out[:EVENTS_MAX]


def dividends(events: pd.DataFrame, results: pd.DataFrame, price: pd.DataFrame,
              code: str, close: float | None, shares: dict | None = None,
              asof: str | None = None, cover_from: int | None = None) -> dict:
    """股利公告 + 除權息結果（含填息天數）+ 近一年現金股利合計的殖利率 + 年度股利長條。

    price 必須是**原始**收盤（填息是拿除權息前的真實收盤比）。
    - 殖利率 ＝ 最近一個配息年度的現金股利（換算到今天的股數）÷ 收盤；
      配息年度＝最後一次除息往回 DIV_YEAR_DAYS（320）天內的各次除息。
      每筆現金 ÷ share_growth([除息日, asof])：6669 6/22 配 144.39 元，9/2 每股變 2.98 股，
      換算後每股 48.4 元 → 殖利率約 3.4%（R5 回報沒換算時是 10.33%）。
    - 除權息紀錄的「股利」只放股利：現金＋股票股利（元），取自 dividend_events 同一除權息日；
      以前放的是 dividend_results 的「前收盤 − 參考價」價差（6669 寫成 5,185）。
      對不到公告時：純除息用價差（除息價差就是現金股利），含權的留空（不猜）。
    - ★ 2026-09-26：`by_year`／`upcoming` 見 div_year_bars。`events`／`results` 以前只給最近 24／12 筆 ——
      季配息股 12 筆只有 3 年，「除權息紀錄」跟年度圖的年份對不起來；現在給資料湖裡全部
      （上限 EVENTS_MAX／RESULTS_MAX）。`coverage` 寫明兩張表各自最早到哪天、各幾筆，
      前端據此講清楚「股利公告只有幾筆」是資料湖的限制，不是這一檔只配過一次。
    """
    out = {"events": [], "results": [], "cash_ttm": None, "yield_ttm": None,
           "by_year": [], "by_period": [], "upcoming": [], "coverage": {}}
    e_all = events[events["code"] == code].copy() if events is not None and not events.empty else pd.DataFrame()
    r_all = results[results["code"] == code].copy() if results is not None and not results.empty else pd.DataFrame()
    if not r_all.empty:
        r_all = r_all.drop_duplicates("date", keep="last")
    if not e_all.empty:
        e = e_all.copy()
        # 同一個所屬年度裡先照期間（第4季 > 第1季、後半年 > 前半年）由新到舊，同期間的現金／股票再照除權息日（沒有就公告日）排
        key = e["ex_date"].where(e["ex_date"].map(_is_date), e.get("announce_date")) if "ex_date" in e.columns else ""
        e["_k"] = pd.Series(key, index=e.index).astype(str)
        e = e.sort_values(["fiscal_year", "period", "_k"], ascending=[False, False, False]) \
            if "fiscal_year" in e.columns else e
        out["events"] = [{
            "period": r.get("period"), "kind": r.get("kind"), "amount": _r(r.get("amount"), 4),
            "announce_date": r.get("announce_date"), "ex_date": r.get("ex_date"),
            "payment_date": r.get("payment_date"),
            "fiscal_year": int(r["fiscal_year"]) if pd.notna(r.get("fiscal_year")) else None,
        } for _, r in e.head(EVENTS_MAX).iterrows()]
        cash = e[e["kind"] == "cash"].copy()
        cash["ex_date"] = cash["ex_date"].astype(str)
        cash = cash[cash["ex_date"].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)].sort_values("ex_date")
        if asof:
            cash = cash[cash["ex_date"] <= str(asof)]      # 還沒除息的不算進「近一年已配」
        if not cash.empty:
            # 「最近一個配息年度」＝最後一次除息往回 320 天內（不是 365 天）：
            # 年配息股每年除息日會前後漂移幾天，用 365 天會把去年那一筆也算進來
            # （6669：2025-06-24 與 2026-06-22 只差 363 天，殖利率被多算一整年）。
            # 季配息四次橫跨約 9 個月（≈275 天）、半年配兩次約 6 個月，都在 320 天內。
            cutoff = (pd.Timestamp(cash["ex_date"].iloc[-1]) - pd.Timedelta(days=DIV_YEAR_DAYS)).date().isoformat()
            recent = cash[cash["ex_date"] > cutoff]
            amt = pd.to_numeric(recent["amount"], errors="coerce")
            if shares:
                from .fundamental import share_growth
                amt = amt / np.asarray([share_growth(shares, code, d, asof, include_after=True)
                                        for d in recent["ex_date"]], dtype=float)
            ttm_cash = float(amt.sum())
            out["cash_ttm"] = round(ttm_cash, 4)
            if close:
                out["yield_ttm"] = round(ttm_cash / close * 100, 2)
    if not r_all.empty:
        paid: dict[str, dict[str, float]] = {}
        if not e_all.empty and "ex_date" in e_all.columns:
            for k, d, amt in zip(e_all["kind"], e_all["ex_date"].astype(str),
                                 pd.to_numeric(e_all["amount"], errors="coerce")):
                if pd.notna(amt):
                    paid.setdefault(d, {}).setdefault(k, 0.0)
                    paid[d][k] += float(amt)
        px = price[price["code"] == code][["date", "close"]].copy() \
            if price is not None and not price.empty else pd.DataFrame()
        if not px.empty:
            px["date"] = px["date"].astype(str)
            px = px.sort_values("date")
        rows = []
        for _, r in r_all.sort_values("date", ascending=False).head(RESULTS_MAX).iterrows():
            d = str(r.get("date"))
            before = _f(r.get("before_price"))
            fill_days = None
            if not px.empty and before:
                after = px[px["date"] >= d]
                closes = pd.to_numeric(after["close"], errors="coerce")
                hit = np.where(closes.values >= before)[0]
                if len(hit):
                    fill_days = int(hit[0]) + 1
                elif len(after) >= 250:
                    fill_days = -1        # 一年內沒填
            pd_ = paid.get(d)
            if pd_:
                cash_d, stock_d = pd_.get("cash"), pd_.get("stock")
                div = (cash_d or 0.0) + (stock_d or 0.0)
            elif "權" not in str(r.get("kind") or ""):
                cash_d, stock_d, div = _f(r.get("dividend")), None, _f(r.get("dividend"))
            else:
                cash_d = stock_d = div = None
            gap = (before - _f(r.get("reference_price"))) if before and _f(r.get("reference_price")) else None
            rows.append({"date": d, "kind": r.get("kind"), "dividend": _r(div, 4),
                         "cash_dividend": _r(cash_d, 4), "stock_dividend": _r(stock_d, 4),
                         "cash_yield": _r(cash_d / before * 100, 2) if (cash_d and before) else None,
                         "price_gap": _r(gap, 2),
                         "before_price": before, "reference_price": _f(r.get("reference_price")),
                         "fill_days": fill_days})
        out["results"] = rows
    if not e_all.empty or not r_all.empty:
        out["by_year"], out["upcoming"] = div_year_bars(e_all, r_all, price, code, asof, cover_from)
        out["by_period"] = dividend_periods(e_all, r_all, asof)
        ann = (e_all["announce_date"].map(lambda v: str(v)[:10] if _is_date(v) else None).dropna()
               if not e_all.empty and "announce_date" in e_all.columns else pd.Series(dtype=object))
        out["coverage"] = {
            "events_n": int(len(e_all)),
            "events_first": ann.min() if len(ann) else None,
            "events_years": int(e_all["fiscal_year"].dropna().nunique())
            if not e_all.empty and "fiscal_year" in e_all.columns else 0,
            "results_n": int(len(r_all)),
            "results_first": str(r_all["date"].astype(str).min())[:10] if not r_all.empty else None,
            "cover_from": int(cover_from) if cover_from else DIV_COVER_YEAR,
        }
    return out


# ------------------------------------------------------------------ 資券

MARGIN_COLUMNS = ["date", "margin_balance", "short_balance", "margin_change", "short_change",
                  "daytrade_lots", "daytrade_ratio", "sbl_sell_lots", "sbl_balance_lots"]


def margin_series(margin: pd.DataFrame, code: str, days: int = CHIP_DAYS,
                  daytrade: pd.DataFrame | None = None, sbl: pd.DataFrame | None = None,
                  price: pd.DataFrame | None = None) -> list:
    """資券每日列（欄位見 MARGIN_COLUMNS）：

    - 前五欄（沿用）：融資餘額、融券餘額、融資增減、融券增減，單位**張**（證交所 MI_MARGN／FinMind 同口徑）。
    - ★ 2026-09-27 往後加四欄（Andy 的券商 App 截圖「融資｜當沖｜融券｜借券賣」）：
      daytrade_lots  ＝ 當日沖銷成交股數 ÷ 1000（張；FinMind TaiwanStockDayTrading.Volume）
      daytrade_ratio ＝ 當沖成交股數 ÷ 當日成交股數 × 100（%；分母用 price_daily.volume，**原始股數**，沒成交或缺量給 None）
      sbl_sell_lots  ＝ 當日借券賣出股數 ÷ 1000（張；TaiwanDailyShortSaleBalances.SBLShortSalesShortSales）
      sbl_balance_lots ＝ 借券賣出餘額 ÷ 1000（張）
      來源沒資料（帳號等級不夠被封印、或還沒回補）→ 這幾欄是 None，前端照實寫「資料源未提供／回補中」。
    - 日期＝三個來源的聯集取最後 days 天，任何一邊缺的那天那幾欄是 None（不補 0）。
    """
    frames = []
    if margin is not None and not margin.empty:
        g = margin[margin["code"] == code].drop_duplicates("date", keep="last")
        if not g.empty:
            frames.append(g.assign(date=g["date"].astype(str)).set_index("date")[
                [c for c in ("margin_balance", "short_balance", "margin_change", "short_change") if c in g.columns]])
    if daytrade is not None and not daytrade.empty and "daytrade_volume" in daytrade.columns:
        d = daytrade[daytrade["code"] == code].drop_duplicates("date", keep="last")
        if not d.empty:
            dd = d.assign(date=d["date"].astype(str)).set_index("date")
            dt = pd.DataFrame({"dt_vol": pd.to_numeric(dd["daytrade_volume"], errors="coerce")})
            if price is not None and not price.empty and "volume" in price.columns:
                px = price[price["code"] == code].drop_duplicates("date", keep="last")
                vol = pd.to_numeric(px["volume"], errors="coerce").to_numpy()
                vol_s = pd.Series(vol, index=px["date"].astype(str).to_numpy())
                dt["vol"] = vol_s.reindex(dt.index).to_numpy()
            frames.append(dt)
    if sbl is not None and not sbl.empty and "sbl_balance" in sbl.columns:
        b = sbl[sbl["code"] == code].drop_duplicates("date", keep="last")
        if not b.empty:
            bb = b.assign(date=b["date"].astype(str)).set_index("date")
            frames.append(pd.DataFrame({"sbl_sell": pd.to_numeric(bb["sbl_sell"], errors="coerce"),
                                        "sbl_bal": pd.to_numeric(bb["sbl_balance"], errors="coerce")}))
    if not frames:
        return []
    m = pd.concat(frames, axis=1).sort_index().tail(days)
    col = lambda c: m[c] if c in m.columns else pd.Series(np.nan, index=m.index)  # noqa: E731
    vol = col("vol")
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where((vol > 0) & col("dt_vol").notna(), col("dt_vol") / vol * 100, np.nan)
    out = []
    for i, d in enumerate(m.index):
        out.append([str(d), _r(col("margin_balance").iloc[i], 0), _r(col("short_balance").iloc[i], 0),
                    _r(col("margin_change").iloc[i], 0), _r(col("short_change").iloc[i], 0),
                    _r(col("dt_vol").iloc[i] / 1000, 0) if pd.notna(col("dt_vol").iloc[i]) else None,
                    _r(ratio[i], 2),
                    _r(col("sbl_sell").iloc[i] / 1000, 0) if pd.notna(col("sbl_sell").iloc[i]) else None,
                    _r(col("sbl_bal").iloc[i] / 1000, 0) if pd.notna(col("sbl_bal").iloc[i]) else None])
    return out


# ------------------------------------------------------------------ 大戶散戶

def holder_series(sh: pd.DataFrame, code: str, weeks: int = 104) -> list:
    """[date, 千張大戶%, 400-1000張%, 10張以下散戶%, 總股東人數]"""
    if sh is None or sh.empty:
        return []
    g = sh[sh["code"] == code]
    if g.empty:
        return []
    rows = []
    for d, gg in g.groupby("date"):
        lv = gg.drop_duplicates("level", keep="last").set_index("level")
        pct = pd.to_numeric(lv["pct"], errors="coerce")
        # ★ 2026-09-26（Andy：「大戶／散戶持股資訊為何這麼少」）：集保原檔的 pct 只到小數兩位，
        #   400–1000 張三級加起來常常連續幾週都是同一個數（2330：09-04 與 09-11 都是 2.75%），
        #   前端怎麼放大 Y 軸都只看到一條水平線。原檔同時給了每級的**股數**與合計股數，
        #   用股數自己除回來可以多拿一位有效數字（2.766% → 2.764%，真的有在變）。
        #   沒有股數（舊資料、測試資料）才退回原檔的 pct，口徑不變、只是精度變高。
        sh = pd.to_numeric(lv["shares"], errors="coerce") if "shares" in lv else None
        tot_sh = sh.get(TOTAL_LEVEL) if sh is not None else None
        if tot_sh is not None and pd.notna(tot_sh) and tot_sh > 0:
            pct = pct.where(sh.isna(), sh / tot_sh * 100)
        nd = 3
        big = pct.get(BIG_LEVEL)
        mid = pct.reindex(list(MID_LEVELS)).sum(min_count=1)
        retail = pct.reindex(list(RETAIL_LEVELS)).sum(min_count=1)
        total = lv["holders"].get(TOTAL_LEVEL) if "holders" in lv else None
        rows.append([str(d), _r(big, nd), _r(mid, nd), _r(retail, nd),
                     int(total) if total is not None and pd.notna(total) else None])
    rows.sort(key=lambda x: x[0])
    return rows[-weeks:]


MAIN_PROXY_WINDOWS = (5, 20)


def main_proxy_series(inst: pd.DataFrame | None, price: pd.DataFrame | None, code: str,
                      days: int = CHIP_DAYS) -> dict:
    """「主力」分頁的**替代口徑**（2026-09-27）：券商分點（主力買賣超、家數差）依 CLAUDE.md 第 7 條不爬，
    改用三大法人合計當「主力」的代理，集中度照券商 App 的定義換成法人版本。

    每日列：[date, 法人合計買賣超（股）, 成交股數, 5 日集中度 %, 20 日集中度 %]
      N 日集中度 ＝ Σ(近 N 個交易日 法人合計買賣超) ÷ Σ(近 N 個交易日 成交股數) × 100
      - 「近 N 個交易日」照 price_daily 的交易日算；其中任何一天缺法人資料或缺量 → 那天的集中度給 None
        （不拿 N−1 天湊，也不把缺值當 0）。
      - 分母 0（N 天都沒成交）→ None。
      - 成交股數用**原始**價量表（還原不動量，但口徑跟當沖率同一份）。
    這不是主力：法人只是市場參與者的一部分（外資、投信、自營商），券商分點裡的大戶、中實戶都不在裡面。
    頁面標題一律寫「主力（替代口徑：三大法人）」。
    """
    cols = ["date", "inst_net", "volume", "conc5", "conc20"]
    out = {"daily": [], "columns": cols, "proxy": "三大法人合計（外資＋投信＋自營商）"}
    if inst is None or inst.empty or price is None or price.empty:
        return out
    gi = inst[inst["code"].astype(str) == str(code)].drop_duplicates("date", keep="last")
    gp = price[price["code"].astype(str) == str(code)].drop_duplicates("date", keep="last")
    if gi.empty or gp.empty or "volume" not in gp.columns:
        return out
    # 三欄全缺才算缺；只缺一欄（例如那天投信沒進出、來源給空）當 0 —— 跟 inst_series 的「合計」同口徑
    three = pd.concat([pd.to_numeric(gi[c], errors="coerce") if c in gi.columns else pd.Series(np.nan, index=gi.index)
                       for c in ("foreign_total", "trust", "dealer")], axis=1)
    net_s = pd.Series(np.where(three.isna().all(axis=1), np.nan, three.fillna(0).sum(axis=1)),
                      index=gi["date"].astype(str).to_numpy())
    # 日期軸＝這一檔的交易日（價量表），不是法人表的日期：法人表缺一天，集中度那幾天就要是 None
    vol_s = pd.Series(pd.to_numeric(gp["volume"], errors="coerce").to_numpy(), index=gp["date"].astype(str).to_numpy())
    d = pd.DataFrame({"vol": vol_s}).sort_index()
    d["net"] = net_s.reindex(d.index)
    d = d[d.index >= net_s.index.min()]
    if d.empty:
        return out
    for n in MAIN_PROXY_WINDOWS:
        ok = d["net"].notna() & d["vol"].notna()
        s_net = d["net"].rolling(n, min_periods=n).sum()
        s_vol = d["vol"].rolling(n, min_periods=n).sum()
        full = ok.astype(int).rolling(n, min_periods=n).sum() == n
        with np.errstate(divide="ignore", invalid="ignore"):
            d[f"c{n}"] = np.where(full & (s_vol > 0), s_net / s_vol * 100, np.nan)
    t = d.tail(days)
    out["daily"] = [[str(i), _r(r.net, 0), _r(r.vol, 0), _r(r.c5, 2), _r(r.c20, 2)] for i, r in zip(t.index, t.itertuples())]
    return out


INSIDER_BASE_MAX_DAYS = 45    # 分母（集保總股數）那一週離月底超過幾天就不拿來除


def insider_series(ih: pd.DataFrame | None, sh: pd.DataFrame | None, code: str, months: int = 24) -> dict:
    """董監持股（每月一列），給「大戶」卡的董監持股比例（2026-09-27）。

    公式：董監持股比例 ＝ 董監「目前持股」合計 ÷ 集保總股數（level 17）× 100。
      - 分子：sources/mops.parse_insider 彙總好的 director_shares（職稱含董事／監察人、同名只算一次）。
      - 分母：集保股權分散表 level 17 的股數，取**離該月月底最近**的那一週；相差超過 INSIDER_BASE_MAX_DAYS 天
        → 不給比例（股本可能已經變了，不拿遠處的股數硬除）。集保資料湖 2026-09-04 起才有，所以更早的月份多半沒有比例，
        只給股數。
      - 設質比例 ＝ 董監設質股數 ÷ 董監目前持股（董監持股 0 → None）。
      - 比例 > 100% 一定是分子重複計算或分母錯，給 None 並標 flag＝"over100"，不把錯的數字畫上去。
    回傳 {"monthly": [{ym, director_pct, insider_pct, director_shares, pledge_pct, n_directors, base_date}],
          "latest": 最後一列或 None, "source": 說明字串}；沒有資料 → monthly 空清單。
    """
    out = {"monthly": [], "latest": None,
           "source": "證交所 OpenAPI t187ap11_L／櫃買 mopsfin_t187ap11_O（董監事持股餘額明細，每月）"}
    if ih is None or ih.empty or "code" not in ih.columns:
        return out
    g = ih[ih["code"].astype(str) == str(code)].drop_duplicates("ym", keep="last").sort_values("ym").tail(months)
    if g.empty:
        return out
    base = pd.Series(dtype=float)
    if sh is not None and not sh.empty and "level" in sh.columns:
        t = sh[(sh["code"].astype(str) == str(code)) & (pd.to_numeric(sh["level"], errors="coerce") == TOTAL_LEVEL)]
        if not t.empty and "shares" in t.columns:
            base = pd.Series(pd.to_numeric(t["shares"], errors="coerce").to_numpy(),
                             index=pd.to_datetime(t["date"].astype(str), errors="coerce")).dropna()
            base = base[base > 0].sort_index()
    rows = []
    for r in g.itertuples():
        me = pd.Timestamp(f"{r.ym}-01") + pd.offsets.MonthEnd(0)
        den, bdate = None, None
        if len(base):
            i = int(np.argmin(np.abs((base.index - me).days)))
            if abs((base.index[i] - me).days) <= INSIDER_BASE_MAX_DAYS:
                den, bdate = float(base.iloc[i]), base.index[i].strftime("%Y-%m-%d")
        ds, ins = _f(getattr(r, "director_shares", None)), _f(getattr(r, "insider_shares", None))
        pl = _f(getattr(r, "director_pledged", None))
        dp = ds / den * 100 if (ds is not None and den) else None
        ip = ins / den * 100 if (ins is not None and den) else None
        flag = None
        if (dp is not None and dp > 100) or (ip is not None and ip > 100):
            dp = ip = None
            flag = "over100"
        rows.append({"ym": r.ym, "director_pct": _r(dp, 2), "insider_pct": _r(ip, 2),
                     "director_shares": _r(ds, 0), "pledge_pct": _r(pl / ds * 100, 2) if (pl is not None and ds) else None,
                     "n_directors": int(getattr(r, "n_directors", 0) or 0), "base_date": bdate, "flag": flag})
    out["monthly"] = rows
    out["latest"] = rows[-1] if rows else None
    return out


# ------------------------------------------------------------------ 法人

def inst_series(inst: pd.DataFrame, code: str, days: int = CHIP_DAYS) -> dict:
    if inst is None or inst.empty:
        return {"daily": [], "sum20": None, "sum60": None}
    g = inst[inst["code"] == code].drop_duplicates("date", keep="last").sort_values("date")
    if g.empty:
        return {"daily": [], "sum20": None, "sum60": None}
    for c in ("foreign_total", "trust", "dealer", "dealer_self", "dealer_hedge"):
        g[c] = pd.to_numeric(g[c], errors="coerce") if c in g.columns else np.nan
    tail = g.tail(days).copy()
    tail["cum"] = (tail["foreign_total"].fillna(0) + tail["trust"].fillna(0) + tail["dealer"].fillna(0)).cumsum()
    # ★ 2026-09-27（Andy 的券商 App 截圖：法人分頁「外資｜投信｜自營商｜合計」四段切換＋每日表）：
    #   列尾多兩欄＝自營商拆成「自行買賣」與「避險」（FinMind Dealer_self／Dealer_Hedging，單位股）。
    #   只往後加欄、不動前五欄的位置，舊前端照索引讀不會讀錯。
    #   ⚠ 2014-12 之前 FinMind 只有合併的「Dealer」，那段 dealer_hedge 是 0（不是「沒有避險」，是當時沒拆）。
    daily = [[str(r.date), _r(r.foreign_total, 0), _r(r.trust, 0), _r(r.dealer, 0), _r(r.cum, 0),
              _r(r.dealer_self, 0), _r(r.dealer_hedge, 0)]
             for r in tail.itertuples()]
    tot = g["foreign_total"].fillna(0) + g["trust"].fillna(0) + g["dealer"].fillna(0)
    return {"daily": daily, "columns": ["date", "foreign", "trust", "dealer", "cum", "dealer_self", "dealer_hedge"],
            "sum20": _r(tot.tail(20).sum(), 0), "sum60": _r(tot.tail(60).sum(), 0),
            "foreign20": _r(g["foreign_total"].tail(20).sum(), 0),
            "trust20": _r(g["trust"].tail(20).sum(), 0)}


# ------------------------------------------------------------------ 基本資料

def monthly_seasonality(price: pd.DataFrame, code: str, years: int = 15) -> dict:
    """個股的 1–12 月平均漲幅（C5，Andy 2026-09-18 拍板要做）。

    原話：「統計過往 15 年 1-12 月的平均漲幅，並且可以切時間週期 1、3、5 年（可自行填寫）」。
    沒有 15 年的就**從它有資料的那一年開始算**，並且把實際年數講出來 ——
    上市三年的公司硬湊 15 年只會變成假數字。

    回傳每一年每一個月的報酬（`by_year`），前端就能自己切 1／3／5／自填年數，
    不用為了換一個年數回頭問後端。月報酬＝該月最後一個交易日收盤 / 前一月最後一個交易日收盤 − 1。

    ★ 只用**已經收完的月份**：當月還沒走完，把它算進「平均漲幅」會讓最近一個月
      永遠是半個月的數字，平均被拉歪。
    """
    empty = {"years": 0, "from": None, "to": None, "by_year": {}, "months": []}
    if price is None or price.empty or "code" not in price.columns:
        return empty
    g = price[price["code"].astype(str) == str(code)]
    if g.empty or "date" not in g.columns or "close" not in g.columns:
        return empty
    g = g.dropna(subset=["close"]).copy()
    g["date"] = g["date"].astype(str)
    g = g.sort_values("date")
    g["ym"] = g["date"].str.slice(0, 7)
    # 每個月的最後一個交易日收盤
    last = g.groupby("ym")["close"].last().astype(float)
    if len(last) < 2:
        return empty
    # 當月還沒收完就丟掉（見上面的理由）
    newest_day = g["date"].iloc[-1]
    if newest_day[:7] == last.index[-1]:
        import datetime as _d
        y, m = int(newest_day[:4]), int(newest_day[5:7])
        nxt = _d.date(y + (m == 12), 1 if m == 12 else m + 1, 1)
        if (nxt - _d.date(y, m, int(newest_day[8:10]))).days > 1:
            last = last.iloc[:-1]
    if len(last) < 2:
        return empty
    ret = (last / last.shift(1) - 1) * 100
    ret = ret.iloc[1:]
    by_year: dict[str, dict[str, float]] = {}
    for ym, v in ret.items():
        if pd.isna(v):
            continue
        by_year.setdefault(ym[:4], {})[str(int(ym[5:7]))] = round(float(v), 2)
    ys = sorted(by_year)[-int(years):]
    by_year = {y: by_year[y] for y in ys}
    return {"years": len(ys), "from": ys[0] if ys else None, "to": ys[-1] if ys else None,
            "by_year": by_year, "months": list(range(1, 13))}


def basics(company: pd.DataFrame, code: str) -> dict:
    if company is None or company.empty:
        return {}
    g = company[company["code"] == code]
    if g.empty:
        return {}
    r = g.iloc[-1]
    cap = _f(r.get("capital"))
    return {
        "name": r.get("name"), "full_name": r.get("full_name"), "market": r.get("market"),
        "industry": r.get("industry"), "industry_finmind": r.get("industry_finmind"),
        "listed_date": r.get("listed_date"),
        "capital": cap, "capital_billion": round(cap / 1e8, 2) if cap else None,
        "chairman": r.get("chairman"), "website": r.get("website"),
    }


# ------------------------------------------------------------------ 歷史無限回溯（③）

HIST_CHUNK = 1000        # 一段幾根日 K


def history_chunks(bars: list, chunk: int = HIST_CHUNK) -> list[dict]:
    """把「個股頁那一段之前」的更舊日 K 切成一段一段，最新的那一段排 p0。

    為什麼要切段：個股頁本來就給 1,250～1,500 根（5～6 年），再往前資料湖最多還有
    5,100 根（2000-01-04 起）。一次全部塞給瀏覽器＝一檔多下載 200KB 而且九成用不到；
    切成一段一段，使用者往左拖一次才要一段（約 40KB）。

    為什麼每一段自己帶 `prev` 而不是另外做一份目錄檔：
    前端要的判斷只有一個 ——「還有沒有更舊的」。`prev` 是 None 就代表這是資料湖裡
    最早的一段，前端看到就收手，不會繼續往下打請求（也就不會出現「拖到底還一直轉」）。
    多一份目錄檔等於多一次來回，而且多一個會對不起來的地方。

    bars 由舊到新，形狀是 [日期, 開, 高, 低, 收, 量]。
    """
    if not bars:
        return []
    segs: list[list] = []
    i = len(bars)
    while i > 0:
        j = max(0, i - chunk)
        segs.append(bars[j:i])
        i = j
    out = []
    for n, seg in enumerate(segs):
        out.append({
            "page": n,
            "prev": None if n == len(segs) - 1 else f"p{n + 1}",
            "from": str(seg[0][0]),
            "to": str(seg[-1][0]),
            "bars": seg,
        })
    return out
