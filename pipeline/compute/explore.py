"""選股探索頁（#explore）的預先計算欄位 —— site/data/explore.json。

為什麼要另外一份檔：探索頁的六個問題裡有四個需要「歷史」才能回答，而既有的全市場檔
（fundamental.json／stocks.json）只有「今天」：
  · 「相對便宜」要比的是**它自己過去五年的本益比**（DECISIONS #13：不跨族群比 PE），
    那份歷史只在個股頁 JSON（pe_history）裡，前端不可能一次載 2,000 檔個股頁。
  · 「走得穩」要 60 日波動度與均線位置（日 K 歷史）。
  · 「配息穩定」要逐年股利（dividends.by_year）。
  · 「法人在買」既有的 inst_streak.json 只列前 60 名，探索頁要的是全市場每一檔的連買天數。
所以在 build_payload 逐檔寫個股頁的那個迴圈裡，順手把這幾個數字抽出來（**只讀已經算好的東西，不多抓任何資料**）。

輸出刻意做成「欄位表＋列陣列」（cols／rows），不是每列一個 dict：2,000 檔 × 10 欄，
dict 形式的鍵名會吃掉一半以上的體積（實測 dict 約 380KB，列陣列約 140KB；上限 300KB）。
"""
from __future__ import annotations

import math

import pandas as pd

# 欄位順序 ＝ 前端 explore.js 的 COLS（兩邊一起改）
COLS = ["code", "vol60", "above20", "above60", "ret60", "pe_pct", "pe_n",
        "dy", "div_years", "buy_days", "net10", "tv20",
        # ★ 2026-10-05 第四版（四大面向）新增：籌碼面兩張、消息面兩張卡要的欄位
        "big_pct", "big_wchg", "mg_chg5", "ret5", "news7", "news_base", "mops7", "conf"]

# 籌碼沉澱與消息熱度的回看窗：都用「最近 N 個有資料的點」而不是日曆天，避免連假讓分母忽大忽小
MG_N = 5            # 融資餘額 5 個交易日變化
NEWS_DAYS = 7       # 近 7 日新聞則數
NEWS_BASE_DAYS = 28  # 基準：之前 28 天的平均每 7 日則數
CONF_AHEAD = 30     # 法說會：已公告、會議日在今天前 7 天～後 30 天內

# 本益比歷史位置至少要幾季才算數：少於 8 季（兩年）的位置，一兩季的高低就會讓百分位亂跳
PE_MIN_Q = 8


def _r(v, nd=2):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, nd)


def volatility(close: pd.Series, n: int = 60) -> float | None:
    """近 n 日日報酬的年化標準差（%）。×√252 是業界慣例，讓 25% 這種數字跟一般說法對得上。
    少於 n+1 根就不算（新股的前幾週波動本來就大，算出來會被當成「不穩」，其實是資料不夠）。"""
    c = pd.to_numeric(close, errors="coerce").dropna()
    if len(c) < n + 1:
        return None
    r = c.tail(n + 1).pct_change().dropna()
    if r.empty:
        return None
    return _r(float(r.std(ddof=1)) * math.sqrt(252) * 100, 1)


def pe_position(pe_now, pe_hist: list | None) -> tuple[float | None, int]:
    """目前本益比落在「自己過去各季本益比」的第幾百分位（0＝歷史最便宜、100＝歷史最貴）。
    虧損（pe 為空或 ≤0）不給位置 —— 虧損公司沒有本益比，硬算會把它排成「最便宜」。
    回傳 (百分位, 用了幾季)。"""
    vals = [float(x["pe"]) for x in (pe_hist or []) if isinstance(x, dict) and x.get("pe") not in (None, "")
            and _r(x.get("pe")) is not None and float(x["pe"]) > 0]
    now = _r(pe_now)
    if now is None or now <= 0 or len(vals) < PE_MIN_Q:
        return None, len(vals)
    below = sum(1 for v in vals if v < now)
    same = sum(1 for v in vals if v == now)
    return _r((below + 0.5 * same) / len(vals) * 100, 0), len(vals)


def dividend_streak(by_year: list | None, this_year: int) -> int:
    """連續有配現金股利的年數：從「去年」往回數，遇到沒配（cash ≤ 0）或資料不明（unknown 佔滿）就停。
    今年不算 —— 今年還沒過完，很多公司下半年才配，算進來會讓「連續」在年中突然斷掉。"""
    if not by_year:
        return 0
    yr = {}
    for x in by_year:
        if isinstance(x, dict) and x.get("year") is not None:
            yr[int(x["year"])] = x
    n = 0
    y = this_year - 1
    while y in yr:
        x = yr[y]
        cash = _r(x.get("cash")) or 0
        if cash <= 0:
            break
        n += 1
        y -= 1
    return n


def buy_streak(inst: pd.DataFrame | None) -> tuple[int, float | None]:
    """三大法人合計（inst_total）連續淨買超幾天（從最新一天往回數）＋近 10 日淨買超（張）。
    最新一天是賣超時回 0 —— 「連買」就是到今天為止還在買。"""
    if inst is None or not isinstance(inst, pd.DataFrame) or inst.empty or "inst_total" not in inst:
        return 0, None
    s = inst.sort_values("date")["inst_total"]
    s = pd.to_numeric(s, errors="coerce").fillna(0)
    n = 0
    for v in reversed(s.tolist()):
        if v > 0:
            n += 1
        else:
            break
    return n, _r(float(s.tail(10).sum()) / 1000, 0)


def holder_change(sh: pd.DataFrame | None) -> tuple[float | None, float | None]:
    """千張大戶（集保分級 15：1,000 張以上）持股比例，以及跟上一週相比的變化（百分點）。
    集保每週公布一次，少於兩週就只給比例、不給變化（不拿 0 冒充「沒變」）。"""
    if sh is None or not isinstance(sh, pd.DataFrame) or sh.empty or "level" not in sh:
        return None, None
    g = sh[pd.to_numeric(sh["level"], errors="coerce") == 15]
    g = g.assign(pct=pd.to_numeric(g["pct"], errors="coerce")).dropna(subset=["pct"])
    g = g.drop_duplicates("date", keep="last").sort_values("date")
    if g.empty:
        return None, None
    now = _r(g["pct"].iloc[-1])
    if len(g) < 2:
        return now, None
    return now, _r(float(g["pct"].iloc[-1]) - float(g["pct"].iloc[-2]))


def margin_change(mg: pd.DataFrame | None, n: int = MG_N) -> float | None:
    """融資餘額近 n 個有資料的交易日變化率（%）。融資餘額太小（< 100 張）不算 —— 分母小，一兩張就變動幾十 %。"""
    if mg is None or not isinstance(mg, pd.DataFrame) or mg.empty or "margin_balance" not in mg:
        return None
    s = pd.to_numeric(mg.drop_duplicates("date", keep="last").sort_values("date")["margin_balance"],
                      errors="coerce").dropna()
    if len(s) <= n or float(s.iloc[-1 - n]) < 100:
        return None
    return _r((float(s.iloc[-1]) / float(s.iloc[-1 - n]) - 1) * 100, 1)


def _days_ago(dates, latest: str) -> list[int]:
    t0 = pd.Timestamp(str(latest)[:10])
    d = pd.to_datetime(pd.Series(list(dates), dtype="object").astype(str).str[:10], errors="coerce").dropna()
    return [(t0 - x).days for x in d]


def news_counts(dates, latest: str) -> tuple[int, float]:
    """近 7 日（含今天）提到這檔的新聞則數，以及之前 28 天的「平均每 7 日則數」當基準。
    未來日期（時區造成的 +1 天）算進近 7 日。"""
    ago = _days_ago(dates, latest)
    n7 = sum(1 for a in ago if a < NEWS_DAYS)
    base = sum(1 for a in ago if NEWS_DAYS <= a < NEWS_DAYS + NEWS_BASE_DAYS)
    return n7, _r(base / (NEWS_BASE_DAYS / NEWS_DAYS), 2)


def mops_recent(rows: list[dict] | None, latest: str) -> tuple[int, str | None]:
    """近 7 日重大訊息則數，以及「近期法說會」的會議日（公告標題含『法人說明會』或『法說會』，
    會議日落在今天前 7 天到後 30 天內；有多場取最近一場）。"""
    rows = rows or []
    ago = _days_ago([r.get("date") for r in rows], latest)
    m7 = sum(1 for a in ago if a < NEWS_DAYS)
    t0 = pd.Timestamp(str(latest)[:10])
    best = None
    for r in rows:
        subj = str(r.get("subject") or "")
        if "法人說明會" not in subj and "法說會" not in subj:
            continue
        occ = pd.to_datetime(str(r.get("occurred") or "")[:10], errors="coerce")
        if pd.isna(occ):
            continue
        delta = (occ - t0).days
        if -7 <= delta <= CONF_AHEAD and (best is None or abs(delta) < abs((pd.Timestamp(best) - t0).days)):
            best = occ.strftime("%Y-%m-%d")
    return m7, best


def stock_row(code: str, *, close: pd.Series, ma20, ma60, turnover: pd.Series,
              pe_now, pe_hist, dividends: dict | None, inst: pd.DataFrame | None,
              this_year: int, shareholding: pd.DataFrame | None = None,
              margin: pd.DataFrame | None = None, news_dates=None, mops: list | None = None,
              latest: str | None = None) -> list:
    """一檔一列（順序照 COLS）。"""
    c = pd.to_numeric(close, errors="coerce").dropna()
    last = float(c.iloc[-1]) if len(c) else None
    ret60 = None
    if len(c) > 60 and c.iloc[-61]:
        ret60 = _r((last / float(c.iloc[-61]) - 1) * 100, 1)
    a20 = 1 if (last is not None and _r(ma20) is not None and last > float(ma20)) else 0
    a60 = 1 if (last is not None and _r(ma60) is not None and last > float(ma60)) else 0
    pct, n = pe_position(pe_now, pe_hist)
    dv = dividends or {}
    dy = _r(dv.get("yield_ttm"), 2)
    dyears = dividend_streak(dv.get("by_year"), this_year)
    bd, net10 = buy_streak(inst)
    tv = pd.to_numeric(turnover, errors="coerce").dropna().tail(20)
    tv20 = _r(float(tv.mean()) / 1e6, 1) if len(tv) else None      # 百萬元
    ret5 = None
    if len(c) > 5 and c.iloc[-6]:
        ret5 = _r((last / float(c.iloc[-6]) - 1) * 100, 1)
    big_pct, big_wchg = holder_change(shareholding)
    mg5 = margin_change(margin)
    day = latest or ""   # 沒給最新交易日就不算消息面（不拿執行當下日期當交易日，CLAUDE.md 第 3 條）
    n7, nbase = news_counts(news_dates or [], day) if day else (0, 0)
    m7, conf = mops_recent(mops, day) if day else (0, None)
    return [code, volatility(c), a20, a60, ret60, pct, n, dy, dyears, bd, net10, tv20,
            big_pct, big_wchg, mg5, ret5, n7, nbase, m7, conf]


def payload(rows: list[list], asof: str) -> dict:
    return {"v": 1, "asof": asof, "cols": COLS, "rows": rows}
