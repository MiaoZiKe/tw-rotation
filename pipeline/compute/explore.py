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
        "dy", "div_years", "buy_days", "net10", "tv20"]

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


def stock_row(code: str, *, close: pd.Series, ma20, ma60, turnover: pd.Series,
              pe_now, pe_hist, dividends: dict | None, inst: pd.DataFrame | None,
              this_year: int) -> list:
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
    return [code, volatility(c), a20, a60, ret60, pct, n, dy, dyears, bd, net10, tv20]


def payload(rows: list[list], asof: str) -> dict:
    return {"v": 1, "asof": asof, "cols": COLS, "rows": rows}
