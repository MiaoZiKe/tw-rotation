"""P-1107-06 個股「除息／財報公布前後的歷史走勢」（事件研究）。

Andy 2026-11-09：「02 05 03 04 06」（五項全做）。法遵審查 docs/feature_proposals/p1107_06_legal_review.md（R1～R15 是硬性驗收條件）。
這支是純函式（不打網路），只讀資料湖已經有的表：
  · 價格：build_payload 的 price_adj（總報酬還原＝還原權值、含息；fundamental.adjust_prices mode="total"）
  · 基準：index_ohlc 的 TSE（發行量加權股價指數，**不含息**；報酬指數在湖裡只有 2026-09 起，不夠長）
  · 除息事件：dividend_results（證交所除權息結果，kind 含「息」的那幾筆；日期就是除息交易日）
  · 財報事件：material_news 重大訊息「董事會通過財報」（earnings.mops_events 的 report），日期＝公告那天。
    ⚠ financial_q 的 announce_date 是**法定截止日**不是實際公告日（fundamental.py 註解），R7 禁止用它代替：
      沒有實際公告日的季度一律不納入，數量寫進 excl（畫面顯示「排除 k 次」）。

口徑（畫面與「?」寫同一套字）：
  · 第 0 天＝事件日當天（不是交易日就順延到下一個交易日）；交易日曆用加權指數有收盤的日子。
  · 報酬＝第 −X 天收盤 → 第 +Y 天收盤；原始＝個股（還原、含息）；超額＝個股 − 同期加權指數。
  · 視窗沒走完（第 +Y 天還沒到）、或兩端那天個股沒有收盤（停牌、尚未上市）→ 不納入（不是「排除」，是還不能算）。
  · 樣本 N < 5（MIN_N）：不給中位數與上漲比例，只列每一次的原始數字（R5）。
  · 不輸出任何未來日期（R8）：事件日一律 ≤ 資料日，而且視窗已走完。
  · 只產單檔 JSON，不產跨股彙總、不排序（R9）；期貨／選擇權／權證／槓桿反向期貨型 ETF 不納入（R13）。
"""
from __future__ import annotations

import json
import re
from bisect import bisect_left
from statistics import median

import pandas as pd

WINDOWS = ((5, 5), (20, 20))     # 事件前 X 日 → 後 Y 日（交易日）
MIN_N = 5                        # 樣本少於這個數：不給中位數、上漲比例
STOCK_RE = re.compile(r"^\d{4}$")                  # 普通股（4 碼數字；特別股 2881A、權證 6 碼、TDR 91xxxx 都不進）
ETF_RE = re.compile(r"^00\d{2,4}[A-KM-QSTV-Z]?$")   # ETF；L（槓桿）、R（反向）、U（期貨型商品）排除——底層是期貨（R13）
BASIS = {"stock": "股價已還原除權息、含息（總報酬）", "bench": "發行量加權股價指數（不含息）"}
SRC = "證交所／櫃買中心公開資料（除權息結果、重大訊息）"


def eligible(code: str) -> bool:
    c = str(code)
    return bool(STOCK_RE.match(c) or ETF_RE.match(c))


def dividend_dates(div_results: pd.DataFrame | None) -> dict[str, list[str]]:
    """每檔的除息交易日（kind 含「息」：息、除息、權息、除權息）。同一天多筆算一次。"""
    out: dict[str, set] = {}
    if div_results is None or div_results.empty:
        return {}
    d = div_results[div_results["kind"].astype(str).str.contains("息", na=False)]
    for c, day in zip(d["code"].astype(str), d["date"].astype(str).str[:10]):
        if eligible(c) and len(day) == 10:
            out.setdefault(c, set()).add(day)
    return {c: sorted(v) for c, v in out.items()}


def _quarter_before(day: str) -> str:
    """公告日之前最近一個已結束的季（主旨沒寫第幾季時用，例如「前三季合併財務報告」）。"""
    y, m = int(day[:4]), int(day[5:7])
    q = (m - 1) // 3          # 這一季之前那一季
    return f"{y - 1}Q4" if q == 0 else f"{y}Q{q}"


def earnings_dates(report_events: list[dict]) -> dict[str, dict[str, str]]:
    """{代號: {季: 實際公告日}}；同一季公告多次取最早那天（第一次讓市場知道的那天）。"""
    out: dict[str, dict[str, str]] = {}
    for e in report_events or []:
        if e.get("k") != "report" or not e.get("code") or len(str(e.get("d") or "")) != 10:
            continue
        c, d = str(e["code"]), str(e["d"])
        if not eligible(c):
            continue
        q = e.get("q") or _quarter_before(d)
        cur = out.setdefault(c, {})
        if q not in cur or d < cur[q]:
            cur[q] = d
    return out


def event_returns(dates: list[str], cal: list[str], px: dict[str, float], idx: dict[str, float],
                  windows=WINDOWS) -> dict:
    """每個事件、每個視窗的 [原始, 超額]（小數）。視窗沒走完或兩端沒有收盤的事件該視窗為 None。

    cal：交易日曆（遞增）；px：個股 日期→還原收盤；idx：日期→加權指數收盤。
    回傳 {"events": [{"d": 事件日, "d0": 第0天, "r": {"5": [raw, ex] 或 None, "20": ...}}], "pending": 視窗都還沒走完的事件數}
    """
    evs, pending = [], 0
    last = len(cal) - 1
    for d in dates:
        i0 = bisect_left(cal, d)
        if i0 > last:
            pending += 1
            continue
        r, any_ok, any_wait = {}, False, False
        for x, y in windows:
            s, e = i0 - x, i0 + y
            key = str(y) if x == y else f"{x}_{y}"
            if e > last:
                r[key] = None; any_wait = True; continue
            if s < 0:
                r[key] = None; continue
            ds, de = cal[s], cal[e]
            a, b, ia, ib = px.get(ds), px.get(de), idx.get(ds), idx.get(de)
            if not a or not b or not ia or not ib:
                r[key] = None; continue
            raw = b / a - 1
            ex = raw - (ib / ia - 1)
            r[key] = [round(raw, 5), round(ex, 5)]
            any_ok = True
        if any_ok:
            evs.append({"d": d, "d0": cal[i0], "r": r})
        elif any_wait:
            pending += 1
    return {"events": evs, "pending": pending}


def stats(vals: list[float]) -> dict:
    """一組報酬（小數）的摘要。N < MIN_N：只給 n、few，其他是 None（R5）。"""
    v = [x for x in vals if x is not None]
    n = len(v)
    if n < MIN_N:
        return {"n": n, "few": True, "up": None, "med": None, "best": None, "worst": None}
    return {"n": n, "few": False, "up": sum(1 for x in v if x > 0), "med": round(median(v), 5),
            "best": round(max(v), 5), "worst": round(min(v), 5)}


def summarize(evs: list[dict], windows=WINDOWS) -> dict:
    """{視窗: {"raw": stats, "ex": stats, "from": 最早事件日, "to": 最晚事件日}}"""
    out = {}
    for x, y in windows:
        key = str(y) if x == y else f"{x}_{y}"
        rows = [e for e in evs if e["r"].get(key)]
        out[key] = {"raw": stats([e["r"][key][0] for e in rows]), "ex": stats([e["r"][key][1] for e in rows]),
                    "from": rows[0]["d"] if rows else None, "to": rows[-1]["d"] if rows else None}
    return out


def stock_payload(code: str, asof: str, cal: list[str], px: dict[str, float], idx: dict[str, float],
                  div_days: list[str], earn_q: dict[str, str], fin_quarters: list[str]) -> dict | None:
    """一檔的 JSON。兩類事件都沒有可算的 → None（不寫檔）。"""
    div_days = [d for d in div_days if d <= asof]
    dv = event_returns(div_days, cal, px, idx)
    eq = {q: d for q, d in earn_q.items() if d <= asof}
    er = event_returns(sorted(eq.values()), cal, px, idx)
    by_d = {d: q for q, d in eq.items()}
    for e in er["events"]:
        e["q"] = by_d.get(e["d"])
    # 排除＝財報季有在湖裡（financial_q）、但沒有實際公告日的季（R7）
    excl = sorted(set(fin_quarters) - set(eq))
    if not dv["events"] and not er["events"] and not excl:
        return None
    return {
        "v": 1, "code": code, "asof": asof, "windows": [list(w) for w in WINDOWS], "min_n": MIN_N, "basis": BASIS, "src": SRC,
        "div": {"events": dv["events"], "pending": dv["pending"], "sum": summarize(dv["events"])},
        "earn": {"events": er["events"], "pending": er["pending"], "excl": len(excl),
                 "excl_from": excl[0] if excl else None, "excl_to": excl[-1] if excl else None, "sum": summarize(er["events"])},
    }


def export(site_data, price_adj: pd.DataFrame, index_ohlc: pd.DataFrame, div_results: pd.DataFrame | None,
           report_events: list[dict], financial_q: pd.DataFrame | None, asof: str) -> dict:
    """寫 site/data/eventstudy/<代號>.json（有事件的才寫）＋ _index.json（有檔的代號清單，前端先讀它，避免 404）。"""
    out = site_data / "eventstudy"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.json"):
        f.unlink()
    ix = index_ohlc[index_ohlc["symbol"].astype(str) == "TSE"][["date", "close"]].dropna()
    ix = ix[(ix["close"] > 0) & (ix["date"].astype(str) <= asof)]
    idx = dict(zip(ix["date"].astype(str).str[:10], ix["close"].astype(float)))
    cal = sorted(idx)
    divs = dividend_dates(div_results)
    earns = earnings_dates(report_events)
    finq: dict[str, list[str]] = {}
    if financial_q is not None and not financial_q.empty:
        fq = financial_q[["code", "year", "quarter"]].dropna().drop_duplicates()
        for c, y, q in zip(fq["code"].astype(str), fq["year"].astype(int), fq["quarter"].astype(int)):
            if eligible(c):
                finq.setdefault(c, []).append(f"{y}Q{q}")
    codes = sorted((set(divs) | set(earns) | set(finq)))
    p = price_adj[price_adj["code"].astype(str).isin(codes)][["code", "date", "close"]]
    p = p[p["date"].astype(str) <= asof]
    written = []
    for code, g in p.groupby(p["code"].astype(str)):
        px = dict(zip(g["date"].astype(str).str[:10], g["close"].astype(float)))
        # 財報季只算「有價格那段期間之後」的季（上市前的財報季談不上前後走勢）
        first = min(px) if px else asof
        fq = [q for q in finq.get(code, []) if f"{q[:4]}-{int(q[-1]) * 3:02d}-28" >= first]
        pl = stock_payload(code, asof, cal, px, idx, divs.get(code, []), earns.get(code, {}), fq)
        if pl is None:
            continue
        (out / f"{code}.json").write_text(json.dumps(pl, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        written.append(code)
    (out / "_index.json").write_text(json.dumps({"updated": asof, "codes": written}, ensure_ascii=False), encoding="utf-8")
    return {"codes": len(written), "asof": asof, "earn_codes": len(earns)}
