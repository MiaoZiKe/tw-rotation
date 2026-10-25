"""台股盤前社群貼文（Threads 輪播＋IG 限動）：美股收盤、台積電 ADR、台指期夜盤、大事件與科技新聞、一句話總結。

Andy 2026-10-26 原話：「需要在新增盤前，只有開盤，當天還需要新增盤前內容，裡面包含 昨日 或上週美股狀況，是否有大事件，
科技新聞大事，以及台指夜盤 台積電ADR 狀況 那斯達克 費半 標普 等狀況，這些也需要以貼文形式呈現 需要截圖給我」。

跟 scripts/social_snap.py 的差別
--------------------------------
盤中／盤後那幾篇是「截網站的圖」；盤前要的東西網站上沒有一張現成的卡（美股五大指數＋ADR 換算＋夜盤＋新聞），
所以這支直接讀資料湖（data/*.parquet，Actions checkout 下來就有），用同一套版型（品牌列＝LOGO＋標題、圓角細框卡片、
FRAME 配色、紅漲綠跌）在瀏覽器裡排版、截圖。共用 social_snap 的配色、LOGO、網址與深連結函式，**不改 social_snap.py**。

五張（Threads 輪播順序＝限動順序）
------------------------------------
1. us-close   美股收盤：那斯達克、費半、標普500、道瓊、VIX；收盤、漲跌點、漲跌%、近 20 日小走勢
2. tsm-adr    台積電 ADR：收盤、漲跌%、換算台股價（1 ADR＝5 股，× TWD=X 匯率 ÷ 5）、對台積電前一日收盤的溢價／折價
3. tx-night   台指期夜盤：最近一個「在目標開盤前已結束」的夜盤；收盤、較日盤收盤、分時走勢；台股休市期間註明「休市 N 天」
4. news       大事件與科技新聞：美股收盤後～台股開盤前的新聞挑 3～5 則（只列標題＋來源＋時間）＋本週已排定的美國重大日程
5. summary    一句話總結（只用上面四張的數字）＋免責

誠實規則
--------
· 資料湖沒有的數字一律不填：例如 TSM／^DJI 還沒進湖 → 該格寫「查證中」並在下方註明「已加進每日管線，下一輪起自動帶入」。
· 新聞只列標題、來源、時間，不摘要、不判讀；挑選規則是固定的關鍵字權重（EVENT_KW／TECH_KW）＋排除清單（SKIP_RE），可重現。
· 總結句只用數字事實，不給買賣建議。
· 版面元素（[data-box]）兩兩不得相交、不得超出畫布、文字不得被截斷 → 有一筆就結束碼 3，不發。

用法
----
    python scripts/social_premarket.py --date 2026-10-27 --out /tmp/premarket --force
    python scripts/social_premarket.py --out snaps/premarket-$(TZ=Asia/Taipei date +%Y%m%d-%H%M)   # 預設＝下一個台股開盤日

結束碼：0＝有產出；10＝刻意不發（目標日不是台股交易日、美股資料太舊、這一篇已發過）；2＝資料完全讀不到；3＝版面重疊／截斷。
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from datetime import date, datetime, timedelta
from datetime import time as dtime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import social_snap as ss

TPE = ZoneInfo("Asia/Taipei")
NY = ZoneInfo("America/New_York")
OPEN_TPE = dtime(8, 45)          # 台指期日盤開盤（盤前貼文的時間上限）
KIND = "premarket"
WEEK = "一二三四五六日"

US_ROWS = [("^IXIC", "那斯達克"), ("^SOX", "費城半導體"), ("^GSPC", "標普500"), ("^DJI", "道瓊工業"), ("^VIX", "VIX 波動率")]
ADR_SYM, FX_SYM, TSMC = "TSM", "TWD=X", "2330"
ADR_RATIO = 5                     # 1 股 ADR＝5 股台積電普通股
SPARK_N = 20
PENDING = "查證中"
PENDING_NOTE = "尚未進資料庫，已加進每日管線，下一輪起自動帶入"
SRC_NAME = {"cnyes": "鉅亨", "udn": "聯合新聞網", "technews": "科技新報"}
DISCLAIMER = "資料：Yahoo Finance、期交所公開資料、新聞媒體整理，僅供參考，不構成投資建議"
HASHTAGS = "#台股 #盤前 #美股 #台指期 #台積電ADR"

# 新聞挑選：固定權重（可重現）。大事件＝總經／地緣／政策；科技＝半導體／AI／大型科技
EVENT_KW = {"聯準會": 3, "Fed": 3, "FOMC": 3, "央行": 3, "利率": 2, "關稅": 3, "伊朗": 3, "中東": 2, "油價": 3, "停火": 2,
            "戰爭": 1, "三大指數": 3, "美股": 1, "殖利率": 2, "衰退": 2, "通膨": 2, "CPI": 3, "非農": 3, "制裁": 2, "選舉": 1}
TECH_KW = {"台積電": 3, "輝達": 3, "Nvidia": 3, "NVIDIA": 3, "半導體": 2, "晶片": 2, "記憶體": 2, "HBM": 2, "CoWoS": 2, "CPO": 2,
           "美光": 2, "AI": 1, "蘋果": 1, "亞馬遜": 1, "AWS": 1, "英特爾": 1, "三星": 1, "財報": 1, "載板": 1, "伺服器": 1}
SKIP_RE = re.compile(r"杜金龍|擂台|購\d|報名|優惠|喊進|潛力股|作帳|目標價|抄底|進場|閉眼|私房|網友|妙招|怎麼放|旅展|豪宅|戰隊|"
                     r"定期定額|論壇|成交前十|掛牌|股價.*周漲|熱門股|〈|大代誌|搶先看|本周大事|操盤筆記")
RELEASE_NAME = {"cpi": "美國 CPI", "nfp": "美國非農就業", "gdp": "美國 GDP", "pce": "美國 PCE"}


# ============================================================================ 小工具
def fmt_num(v: float, nd: int = 2) -> str:
    return f"{v:,.{nd}f}"


def fmt_signed(v: float, nd: int = 2, suffix: str = "") -> str:
    """+1.23／−1.23（減號用全形減號 U+2212，跟網站一致）。"""
    s = f"{abs(v):,.{nd}f}{suffix}"
    return ("+" if v > 0 else "−" if v < 0 else "±") + s


def md(d: date | str) -> str:
    d = pd.Timestamp(d).date() if not isinstance(d, date) else d
    return f"{d.month}/{d.day}"


def mdw(d: date) -> str:
    return f"{md(d)}（{WEEK[d.weekday()]}）"


def tone(v: float | None) -> str:
    return "rise" if (v or 0) > 0 else "fall" if (v or 0) < 0 else "ink3"


def load_holidays() -> set[str]:
    try:
        import yaml
        d = yaml.safe_load((ROOT / "pipeline" / "calendar" / "tw_holidays.yaml").read_text("utf-8")) or {}
        return set(str(k) for k in (d.get("days") or {}))
    except Exception:  # noqa: BLE001
        return set()


def is_tw_trading_day(d: date, holidays: set[str]) -> bool:
    """開盤前沒有當天的資料可看，只能用行事曆：平日且不在 tw_holidays.yaml。颱風假這種臨時休市看不到（照實寫在 docs）。"""
    return d.weekday() < 5 and d.isoformat() not in holidays


def next_trading_day(now: datetime, holidays: set[str]) -> date:
    d = now.date()
    if now.time() >= OPEN_TPE:
        d += timedelta(days=1)
    while not is_tw_trading_day(d, holidays):
        d += timedelta(days=1)
    return d


def parse_pub(s) -> pd.Timestamp | None:
    """news.published_at 兩種格式：ISO（鉅亨）與 RFC 2822（聯合、科技新報）。回台北時間。"""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    try:
        t = pd.Timestamp(str(s))
        if t.tzinfo is None:
            t = t.tz_localize(TPE)
        return t.tz_convert(TPE)
    except Exception:  # noqa: BLE001
        try:
            return pd.Timestamp(parsedate_to_datetime(str(s))).tz_convert(TPE)
        except Exception:  # noqa: BLE001
            return None


# ============================================================================ 資料整理（純函式，測試不連網）
def us_close(intl: pd.DataFrame, target: date) -> dict:
    """目標開盤日之前最後一個美股交易日（以 ^IXIC 有收盤的日期為準）的五大指數。缺的那檔 missing=True，不補數字。"""
    out = {"date": None, "rows": []}
    if intl is None or intl.empty:
        return out
    df = intl.copy()
    df["date"] = df["date"].astype(str).str[:10]
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    base = df[(df["symbol"] == "^IXIC") & (df["date"] < target.isoformat())].dropna(subset=["close"])
    if base.empty:
        return out
    usd = base["date"].max()
    out["date"] = usd
    for sym, label in US_ROWS:
        s = df[(df["symbol"] == sym) & (df["date"] <= usd)].dropna(subset=["close"]).sort_values("date")
        if s.empty or s["date"].iloc[-1] != usd or len(s) < 2:
            out["rows"].append({"sym": sym, "label": label, "missing": True})
            continue
        c, p = float(s["close"].iloc[-1]), float(s["close"].iloc[-2])
        out["rows"].append({"sym": sym, "label": label, "missing": False, "close": c, "chg": c - p,
                            "pct": (c / p - 1) * 100 if p else 0.0, "prev_date": s["date"].iloc[-2],
                            "spark": [float(x) for x in s["close"].tail(SPARK_N)]})
    return out


def adr_info(intl: pd.DataFrame, price: pd.DataFrame, us_date: str | None, target: date) -> dict:
    """台積電 ADR：收盤、漲跌%、換算台股價＝ADR × 匯率 ÷ 5、對台積電前一日收盤的溢價／折價%。"""
    r: dict = {"missing": True, "date": us_date}
    if intl is not None and not intl.empty and us_date:
        df = intl.copy()
        df["date"] = df["date"].astype(str).str[:10]
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        fx = df[(df["symbol"] == FX_SYM) & (df["date"] <= us_date)].dropna(subset=["close"]).sort_values("date")
        if not fx.empty:
            r["fx"], r["fx_date"] = float(fx["close"].iloc[-1]), fx["date"].iloc[-1]
        a = df[(df["symbol"] == ADR_SYM) & (df["date"] <= us_date)].dropna(subset=["close"]).sort_values("date")
        if len(a) >= 2 and a["date"].iloc[-1] == us_date:
            c, p = float(a["close"].iloc[-1]), float(a["close"].iloc[-2])
            r.update(missing=False, close=c, chg=c - p, pct=(c / p - 1) * 100 if p else 0.0,
                     spark=[float(x) for x in a["close"].tail(SPARK_N)])
    if price is not None and not price.empty:
        t = price[(price["code"].astype(str) == TSMC) & (price["date"].astype(str).str[:10] < target.isoformat())]
        t = t.dropna(subset=["close"]).sort_values("date")
        if not t.empty:
            r["tw_close"], r["tw_date"] = float(t["close"].iloc[-1]), str(t["date"].iloc[-1])[:10]
    if not r["missing"] and r.get("fx"):
        r["conv"] = r["close"] * r["fx"] / ADR_RATIO
        if r.get("tw_close"):
            r["prem"] = (r["conv"] / r["tw_close"] - 1) * 100
    return r


def night_session(intra: pd.DataFrame, ohlc: pd.DataFrame, target: date) -> dict:
    """最近一個在目標日 08:45 前已結束的台指期夜盤（FUT_N，15:00～次日 05:00）。

    session＝夜盤開始那天（台北）。日盤收盤取 index_ohlc 的 FUT（同一天）；期交所漲跌取 index_ohlc 的 FUT_N
    （期交所把夜盤記在次一營業日，所以取 session 之後第一筆、而且收盤要對得上才用）。"""
    r: dict = {"missing": True}
    if intra is None or intra.empty:
        return r
    x = intra[intra["symbol"].astype(str) == "FUT_N"].copy()
    if x.empty:
        return r
    x["t"] = pd.to_datetime(x["ts"].astype(str), utc=True).dt.tz_convert(TPE)
    x["close"] = pd.to_numeric(x["close"], errors="coerce")
    x = x.dropna(subset=["close"]).sort_values("t")
    hr = x["t"].dt.hour
    x["session"] = (x["t"] - pd.to_timedelta((hr < 15).astype(int), unit="D")).dt.date
    limit = datetime.combine(target, OPEN_TPE, tzinfo=TPE)
    x = x[x["t"] < limit]
    if x.empty:
        return r
    sess = x["session"].max()
    bars = x[x["session"] == sess]
    close = float(bars["close"].iloc[-1])
    r.update(missing=False, session=sess.isoformat(), close=close, start=bars["t"].iloc[0].isoformat(),
             end=bars["t"].iloc[-1].isoformat(),
             partial=bool(bars["t"].iloc[-1] < datetime.combine(sess + timedelta(days=1), dtime(4, 30), tzinfo=TPE)), bars=[[b.isoformat(), float(c)] for b, c in zip(bars["t"], bars["close"])])
    if ohlc is not None and not ohlc.empty:
        o = ohlc.copy()
        o["date"] = o["date"].astype(str).str[:10]
        day = o[(o["symbol"].astype(str) == "FUT") & (o["date"] == sess.isoformat())]
        if not day.empty:
            r["day_close"] = float(day["close"].iloc[-1])
        n = o[(o["symbol"].astype(str) == "FUT_N") & (o["date"] > sess.isoformat())].sort_values("date")
        if not n.empty and abs(float(n["close"].iloc[0]) - close) < 0.5 and pd.notna(n["change"].iloc[0]):
            r["official_chg"] = float(n["change"].iloc[0])
    if "day_close" not in r:   # 退回：同一天日盤 1 分 K 的最後一根
        d = intra[(intra["symbol"].astype(str) == "FUT") & intra["ts"].astype(str).str.startswith(sess.isoformat())]
        if not d.empty:
            r["day_close"] = float(pd.to_numeric(d.sort_values("ts")["close"], errors="coerce").dropna().iloc[-1])
    if r.get("day_close"):
        r["diff"] = close - r["day_close"]
        r["diff_pct"] = (close / r["day_close"] - 1) * 100
    return r


def closure_note(last_td: str | None, target: date) -> dict | None:
    """上一個台股交易日到目標日之間有平日沒開盤 → 「台股 10/23–10/26 休市 4 天」。週末本來就休，不寫。"""
    if not last_td:
        return None
    d0 = pd.Timestamp(last_td).date()
    gap = [d0 + timedelta(days=i) for i in range(1, (target - d0).days)]
    weekdays = [d for d in gap if d.weekday() < 5]
    if not weekdays:
        return None
    first, last = weekdays[0], gap[-1]      # 從第一個沒開盤的平日算到目標日前一天（含中間的週末）
    n = (last - first).days + 1
    return {"first": first.isoformat(), "last": last.isoformat(), "days": n,
            "text": f"台股 {md(first)}–{md(last)} 休市 {n} 天，{md(target)} 復市"}


def us_close_tpe(us_date: str) -> datetime:
    """美股收盤（美東 16:00）換成台北時間；夏令時間台北 04:00、冬令 05:00。"""
    d = pd.Timestamp(us_date).date()
    return datetime.combine(d, dtime(16, 0), tzinfo=NY).astimezone(TPE)


def _score(title: str, kw: dict) -> tuple[int, str]:
    best, topic = 0, ""
    for k, w in kw.items():
        if k in title:
            best += w
            if not topic or w > kw.get(topic, 0):
                topic = k
    return best, topic


def pick_news(news: pd.DataFrame, start: datetime, end: datetime, n_event: int = 2, n_tech: int = 3) -> list[dict]:
    """美股收盤後～台股開盤前的新聞：大事件 n_event 則＋科技 n_tech 則（同一主題只留分數最高的一則）。
    只回標題、來源、時間；不改寫標題。"""
    if news is None or news.empty:
        return []
    df = news.copy()
    df["t"] = df["published_at"].map(parse_pub)
    df = df[df["t"].notna()]
    df = df[(df["t"] >= pd.Timestamp(start)) & (df["t"] < pd.Timestamp(end))]
    df = df[~df["title"].astype(str).str.contains(SKIP_RE)]
    df = df.drop_duplicates("title")
    picked, topics = [], set()
    for kind, kw, n, cats in (("大事件", EVENT_KW, n_event, {"總經", "科技", "台股"}), ("科技", TECH_KW, n_tech, {"科技", "台股"})):
        rows = []
        for r in df.itertuples():
            if str(getattr(r, "category", "")) not in cats:
                continue
            s, tp = _score(str(r.title), kw)
            if s >= 2:
                rows.append((s, r.t, tp, r))
        rows.sort(key=lambda z: (-z[0], -z[1].value))
        got = 0
        for s, t, tp, r in rows:
            if got >= n:
                break
            if tp in topics or any(p["title"] == r.title for p in picked):
                continue
            topics.add(tp)
            picked.append({"kind": kind, "title": str(r.title).strip(), "source": SRC_NAME.get(str(r.source), str(r.source)),
                           "time": t.isoformat(), "topic": tp, "score": s})
            got += 1
    return picked


def upcoming_events(target: date, cal: pd.DataFrame | None, days: int = 5) -> list[dict]:
    """目標日起 days 天內已排定的美國重大日程：FOMC 決議（macro_events.yaml）＋ CPI／非農／GDP／PCE（FRED 日程，沒有就用 YAML 退回值）。
    美東時間換台北時間。"""
    try:
        import yaml
        y = yaml.safe_load((ROOT / "pipeline" / "calendar" / "macro_events.yaml").read_text("utf-8")) or {}
    except Exception:  # noqa: BLE001
        y = {}
    lo, hi = datetime.combine(target, dtime(0, 0), tzinfo=TPE), datetime.combine(target + timedelta(days=days), dtime(0, 0), tzinfo=TPE)
    ev = []
    for m in ((y.get("fomc") or {}).get("meetings") or []):
        t = datetime.combine(pd.Timestamp(m["end"]).date(), dtime(14, 0), tzinfo=NY).astimezone(TPE)
        if lo <= t < hi:
            ev.append({"t": t, "name": "FOMC 利率決議"})
    rel: dict[str, set] = {}
    if cal is not None and not cal.empty:
        for r in cal.itertuples():
            rel.setdefault(str(r.release), set()).add(str(r.date)[:10])
    else:
        for k, v in ((y.get("releases") or {}).items()):
            rel[k] = {str(d["date"]) for d in (v.get("dates") or [])}
    for k, ds in rel.items():
        for d in ds:
            t = datetime.combine(pd.Timestamp(d).date(), dtime(8, 30), tzinfo=NY).astimezone(TPE)
            if lo <= t < hi and k in RELEASE_NAME:
                ev.append({"t": t, "name": RELEASE_NAME[k]})
    ev.sort(key=lambda e: (e["t"], e["name"]))
    merged: list[dict] = []          # 同一時間的併成一行（GDP、PCE 同時公布）
    for e in ev:
        if merged and merged[-1]["t"] == e["t"]:
            merged[-1]["name"] += "、" + e["name"].replace("美國 ", "")
        else:
            merged.append(dict(e))
    return [{"time": e["t"].isoformat(), "name": e["name"],
             "label": f"{mdw(e['t'].date())} {e['t']:%H:%M}"} for e in merged]


def summary_line(us: dict, adr: dict, night: dict, closure: dict | None) -> str:
    """一句話總結：只用數字事實，不給方向判斷、不給買賣建議。"""
    parts = []
    if us.get("date"):
        got = [f"{r['label'].replace('費城半導體', '費半')} {fmt_signed(r['pct'], 2, '%')}" for r in us["rows"]
               if not r["missing"] and r["sym"] in ("^IXIC", "^SOX", "^GSPC")]
        if got:
            parts.append(f"美股 {md(us['date'])} " + "、".join(got))
    if not adr.get("missing"):
        s = f"台積電 ADR {fmt_signed(adr['pct'], 2, '%')}"
        if adr.get("prem") is not None:
            s += f"、換算{'溢價' if adr['prem'] >= 0 else '折價'} {abs(adr['prem']):.2f}%"
        parts.append(s)
    if not night.get("missing") and night.get("diff") is not None:
        parts.append(f"台指期 {md(night['session'])} 夜盤較日盤 {fmt_signed(night['diff'], 0)} 點")
    s = "；".join(parts) + "。" if parts else "盤前資料待更新。"
    if closure:
        s += closure["text"] + "。"
    return s


def collect(target: date, intl, price, intra, ohlc, news, cal) -> dict:
    us = us_close(intl, target)
    adr = adr_info(intl, price, us["date"], target)
    night = night_session(intra, ohlc, target)
    last_td = None
    if ohlc is not None and not ohlc.empty:
        t = ohlc[(ohlc["symbol"].astype(str) == "TSE") & (ohlc["date"].astype(str).str[:10] < target.isoformat())]
        if not t.empty:
            last_td = str(t["date"].astype(str).str[:10].max())
    closure = closure_note(last_td, target)
    start = us_close_tpe(us["date"]) if us["date"] else datetime.combine(target - timedelta(days=1), dtime(5, 0), tzinfo=TPE)
    end = datetime.combine(target, OPEN_TPE, tzinfo=TPE)
    return {"target": target.isoformat(), "us": us, "adr": adr, "night": night, "last_td": last_td, "closure": closure,
            "news_window": [start.isoformat(), end.isoformat()], "news": pick_news(news, start, end),
            "events": upcoming_events(target, cal), "summary": summary_line(us, adr, night, closure)}


def load_lake(target: date) -> tuple:
    from pipeline.util import store
    ys = sorted({target.year, (target - timedelta(days=40)).year})
    yms = sorted({int(f"{d.year}{d.month:02d}") for d in (target, target - timedelta(days=10))})
    intl = store.read("intl_daily")
    price = store.read("price_daily", years=ys)
    if not price.empty:
        price = price[price["code"].astype(str) == TSMC]
    intra = store.read("index_intraday", years=yms)
    ohlc = store.read("index_ohlc", years=ys)
    news = store.read("news")
    cal = store.read("macro_calendar")
    return intl, price, intra, ohlc, news, cal


# ============================================================================ 圖（SVG，量好實際框再畫，不拉伸）
def spark_svg(vals: list[float], w: int, h: int, color: str, pad: int = 0) -> str:
    if len(vals) < 2:
        return ""
    pad = pad or int(max(4, h / 22) + 4)    # 留邊＞終點圓點半徑，圓點不被切
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = [(pad + i * (w - 2 * pad) / (len(vals) - 1), pad + (hi - v) / rng * (h - 2 * pad)) for i, v in enumerate(vals)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pts[0][0]:.1f},{h - pad} " + d + f" {pts[-1][0]:.1f},{h - pad}"
    lx, ly = pts[-1]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polygon points="{area}" fill="{color}" fill-opacity="0.10"/>'
            f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{max(2.5, h / 40):.1f}" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{max(4, h / 22):.1f}" fill="{color}"/></svg>')


def night_svg(bars: list, ref: float | None, w: int, h: int, c: dict, fs: int) -> str:
    """夜盤分時走勢：實線＝夜盤 1 分 K 收盤；虛線＝日盤收盤。軸字放在左與下的留邊內，不壓到線。"""
    if len(bars) < 2:
        return ""
    ts = [pd.Timestamp(t) for t, _ in bars]
    vs = [v for _, v in bars]
    lo, hi = min(vs + ([ref] if ref else [])), max(vs + ([ref] if ref else []))
    span = (hi - lo) or 1
    lo, hi = lo - span * 0.06, hi + span * 0.06
    L, R, T, B = int(fs * 4.2), 12, int(fs * 0.8), int(fs * 1.9)
    t0 = ts[0].normalize() + pd.Timedelta(hours=15)
    t1 = t0 + pd.Timedelta(hours=14)
    X = lambda t: L + (t - t0) / (t1 - t0) * (w - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (h - T - B)
    col = c["rise"] if (ref and vs[-1] > ref) else c["fall"] if ref and vs[-1] < ref else c["cyan"]
    d = " ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in zip(ts, vs))
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Noto Sans CJK TC,Noto Sans TC,WenQuanYi Zen Hei,sans-serif">']
    for k in range(5):      # 水平格線＋左側刻度
        v = lo + (hi - lo) * k / 4
        y = Y(v)
        g.append(f'<line x1="{L}" y1="{y:.1f}" x2="{w - R}" y2="{y:.1f}" stroke="{c["line"]}" stroke-width="1.5"/>')
        g.append(f'<text x="{L - 10}" y="{y + fs * 0.35:.1f}" font-size="{fs}" fill="{c["ink3"]}" text-anchor="end">{v:,.0f}</text>')
    for hh, lab in ((0, "15:00"), (5, "20:00"), (9, "00:00"), (14, "05:00")):
        x = X(t0 + pd.Timedelta(hours=hh))
        anchor = "start" if hh == 0 else "end" if hh == 14 else "middle"
        g.append(f'<text x="{x:.1f}" y="{h - fs * 0.45:.1f}" font-size="{fs}" fill="{c["ink3"]}" text-anchor="{anchor}">{lab}</text>')
    if ref:
        g.append(f'<line x1="{L}" y1="{Y(ref):.1f}" x2="{w - R}" y2="{Y(ref):.1f}" stroke="{c["ink3"]}" stroke-width="2.5" stroke-dasharray="10 8"/>')
    g.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="3.5" stroke-linejoin="round"/>')
    g.append(f'<circle cx="{X(ts[-1]):.1f}" cy="{Y(vs[-1]):.1f}" r="7" fill="{col}"/></svg>')
    return "".join(g)


def svg_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


# ============================================================================ 版型
def _e(t) -> str:
    return ss._esc(str(t))


def page_css(mode: str, theme: str) -> str:
    c = ss.FRAME[theme]
    story = mode == "story"
    H = 1920 if story else 1350
    S = (lambda a, b: b if story else a)
    return (":root{" + "".join(f"--{k}:{v};" for k, v in c.items()) + "}" + f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:{H}px;overflow:hidden}}
body{{background:var(--bg);color:var(--ink);font-family:'Noto Sans CJK TC','Noto Sans TC','PingFang TC','Microsoft JhengHei','WenQuanYi Zen Hei',sans-serif;
  display:flex;flex-direction:column;padding:{S('16px 20px 16px', '24px 24px 20px')};font-variant-numeric:tabular-nums}}
.brand{{display:flex;align-items:center;gap:12px;height:{S(64, 72)}px;flex:none}}
.brand img{{width:{S(54, 60)}px;height:{S(54, 60)}px;border-radius:13px;display:block}}
.brand .nm{{font-size:{S(40, 44)}px;font-weight:800;line-height:1.5;white-space:nowrap}}
.card{{flex:1;min-height:0;display:flex;flex-direction:column;margin-top:8px;background:var(--panel);border:1.5px solid var(--line2);border-radius:24px;padding:{S('14px 18px 14px', '18px 20px 18px')}}}
.sub{{flex:none;font-size:{S(24, 30)}px;line-height:1.5;color:var(--ink3);white-space:nowrap;margin:0 4px {S(8, 12)}px}}
.body{{flex:1;min-height:0;display:flex;flex-direction:column;gap:{S(10, 14)}px}}
.rise{{color:var(--rise)}}.fall{{color:var(--fall)}}.ink3{{color:var(--ink3)}}
.row{{flex:1;min-height:0;display:grid;grid-template-columns:{S('300px 1fr 300px', '1fr 1fr')};grid-template-rows:{S('1fr', 'auto 1fr')};align-items:center;column-gap:16px;
  border:1.5px solid var(--line);border-radius:16px;padding:{S('6px 16px', '12px 20px')};background:var(--panel2)}}
.row .nm{{font-size:{S(34, 42)}px;font-weight:800;line-height:1.5;white-space:nowrap}}
.row .px{{font-size:{S(30, 38)}px;line-height:1.5;color:var(--ink2);white-space:nowrap}}
.row .pct{{font-size:{S(46, 56)}px;font-weight:800;line-height:1.4;white-space:nowrap;text-align:{S('right', 'right')}}}
.row .pts{{font-size:{S(28, 34)}px;line-height:1.5;white-space:nowrap;text-align:right}}
.row .na{{font-size:{S(30, 36)}px;line-height:1.5;color:var(--ink3);white-space:nowrap;text-align:right}}
.row .sp{{align-self:stretch;min-height:0;position:relative;{S('', 'grid-column:1 / span 2;')}}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:{S(12, 16)}px}}
.tiles{{flex:1;min-height:0}}
.tile{{min-width:0;min-height:0;border:1.5px solid var(--line);border-radius:16px;background:var(--panel2);padding:{S('14px 20px', '20px 24px')};display:flex;flex-direction:column;justify-content:center}}
.tile .k{{font-size:{S(28, 34)}px;line-height:1.5;color:var(--ink3);white-space:nowrap}}
.tile .v{{font-size:{S(60, 72)}px;font-weight:800;line-height:1.3;white-space:nowrap}}
.tile .v small{{font-size:.5em;font-weight:700;margin-left:6px}}
.tile .d{{font-size:{S(28, 34)}px;line-height:1.5;white-space:nowrap;color:var(--ink2)}}
.tile .d.rise,.row .rise{{color:var(--rise)}}.tile .d.fall,.row .fall{{color:var(--fall)}}
.row.kv{{grid-template-columns:1fr auto;grid-template-rows:1fr}}.row.kv.wsp{{grid-template-columns:{S('1fr auto 300px', '1fr auto')};grid-template-rows:{S('1fr', 'auto 1fr')}}}
.row.kv .pct{{font-size:{S(64, 76)}px}}
.note{{flex:none;font-size:{S(26, 32)}px;line-height:1.5;color:var(--ink2)}}
.note.warn{{color:var(--amber);font-weight:700}}
.chartbox{{flex:1;min-height:0;position:relative}}
.chartbox img{{position:absolute;left:0;top:0;display:block}}
.legend{{flex:none;display:flex;gap:28px;font-size:{S(24, 30)}px;line-height:1.5;color:var(--ink3);white-space:nowrap}}
.news{{flex:1;min-height:0;display:flex;flex-direction:column;justify-content:space-between;gap:{S(8, 12)}px}}
.it{{border-left:6px solid var(--c);padding:{S('4px 0 4px 16px', '6px 0 6px 18px')};flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center}}
.it .tg{{font-size:{S(24, 30)}px;line-height:1.5;font-weight:800;color:var(--c);white-space:nowrap}}
.it .tt{{font-size:{S(32, 40)}px;line-height:1.45;font-weight:700;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:{S(2, 3)};overflow:hidden}}
.it .ms{{font-size:{S(24, 30)}px;line-height:1.5;color:var(--ink3);white-space:nowrap}}
.cal{{flex:none;border:1.5px solid var(--line);border-radius:16px;background:var(--panel2);padding:{S('10px 18px', '14px 20px')}}}
.cal b{{display:block;font-size:{S(26, 32)}px;line-height:1.5;color:var(--cyan)}}
.cal div{{font-size:{S(28, 34)}px;line-height:1.5;white-space:nowrap}}
.bigbox{{flex:none;display:flex;align-items:center;border:1.5px solid var(--line);border-radius:16px;background:var(--panel2);padding:{S('16px 28px', '24px 32px')}}}
.big{{font-size:{S(50, 60)}px;line-height:1.6;font-weight:700}}
.sumt .v{{font-size:{S(92, 110)}px}}.sumt .k{{font-size:{S(34, 42)}px}}
.disc{{flex:none;font-size:{S(24, 30)}px;line-height:1.5;color:var(--ink3)}}
""")


def page_html(mode: str, theme: str, title: str, sub: str, inner: str) -> str:
    logo = ss._logo_uri()
    body = (f'<div class=brand>{"<img data-box=logo src=" + chr(34) + logo + chr(34) + ">" if logo else ""}'
            f'<div class=nm data-box=title>{_e(title)}</div></div>'
            f'<div class=card><div class=sub data-box=sub>{_e(sub)}</div><div class=body>{inner}</div></div>')
    return f"<!doctype html><html><head><meta charset=utf-8><style>{page_css(mode, theme)}</style></head><body>{body}</body></html>"


def build_pages(D: dict, mode: str) -> list[dict]:
    """每張回 {name, title, sub, inner, charts:{key: 畫圖函式(w,h,c)}}。"""
    story = mode == "story"
    tgt = pd.Timestamp(D["target"]).date()
    head = f"台股盤前｜{md(tgt)}"
    us, adr, night = D["us"], D["adr"], D["night"]
    pages = []

    # 1 美股收盤
    rows, charts = [], {}
    for r in us["rows"]:
        if r["missing"]:
            rows.append(f'<div class=row><div><div class=nm data-box=nm-{r["sym"]}>{_e(r["label"])}</div></div>'
                        f'<div class=na data-box=na-{r["sym"]}>{PENDING}</div>{"" if story else "<div></div>"}</div>')
            continue
        tn = tone(r["chg"]) if r["sym"] != "^VIX" else "ink3"
        key = "sp" + re.sub(r"\W", "", r["sym"])
        nd = 2
        rows.append(f'<div class=row><div><div class=nm data-box=nm-{key}>{_e(r["label"])}</div>'
                    f'<div class=px data-box=px-{key}>{fmt_num(r["close"], nd)}</div></div>'
                    f'<div><div class="pct {tn}" data-box=pct-{key}>{fmt_signed(r["pct"], 2, "%")}</div>'
                    f'<div class="pts {tn}" data-box=pts-{key}>{fmt_signed(r["chg"], nd)} 點</div></div>'
                    f'<div class=sp><div class=chartbox data-box={key} data-chart={key} style="position:absolute;inset:0"></div></div></div>')
        charts[key] = (lambda vals, t: (lambda w, h, c: spark_svg(vals, w, h, c[t] if t in c else c["cyan"])))(r["spark"], tn if tn != "ink3" else "cyan")
    miss = [r["label"] for r in us["rows"] if r["missing"]]
    inner = "".join(rows) + (f'<div class="note ink3" data-box=note-miss>{_e("、".join(miss))}{PENDING_NOTE}</div>' if miss else "")
    pages.append(dict(name="us-close", title=f"{head}｜美股收盤", sub=f"資料日：美股 {mdw(pd.Timestamp(us['date']).date()) if us['date'] else '—'} 美東收盤・小圖＝近 {SPARK_N} 日",
                      inner=inner, charts=charts))

    # 2 台積電 ADR（四列：ADR 收盤＋近 20 日小圖、換算台股價、台積電前收、溢價／折價）
    def kv(i, k, d, v, cls="", spark=None):
        sp = '<div class=sp><div class=chartbox data-box=adrsp data-chart=adrsp style="position:absolute;inset:0"></div></div>' if spark else ""
        return (f'<div class="row kv{" wsp" if spark else ""}"><div><div class=nm data-box=k{i}>{_e(k)}</div>'
                + (f'<div class=px data-box=d{i}>{d}</div>' if d else "") + f'</div><div class="pct {cls}" data-box=v{i}>{v}</div>{sp}</div>')
    charts = {}
    tw = fmt_num(adr["tw_close"], 0) if adr.get("tw_close") else "—"
    twd = f'{md(adr["tw_date"])} 收盤' if adr.get("tw_date") else ""
    if adr["missing"]:
        rows = [kv(1, "ADR 收盤（美元）", "TSM・美東收盤", PENDING, "ink3"),
                kv(2, "換算台股價（元）", f"ADR × 匯率 ÷ {ADR_RATIO}", PENDING, "ink3"),
                kv(3, "台積電前一日收盤（元）", twd, tw),
                kv(4, "溢價／折價", "換算價 vs 台積電前收", PENDING, "ink3")]
    else:
        tn = tone(adr["chg"])
        p = adr.get("prem")
        rows = [kv(1, "ADR 收盤（美元）", f'<span class={tn}>{fmt_signed(adr["chg"])}（{fmt_signed(adr["pct"], 2, "%")}）</span>',
                   fmt_num(adr["close"]), "", spark=True),
                kv(2, "換算台股價（元）", f'ADR × {adr.get("fx", 0):.3f} ÷ {ADR_RATIO}', fmt_num(adr.get("conv", 0), 1) if adr.get("conv") else "—"),
                kv(3, "台積電前一日收盤（元）", twd, tw),
                kv(4, f'{"溢價" if (p or 0) >= 0 else "折價"}（對台積電前收）', "換算價 vs 台積電前收", fmt_signed(p, 2, "%") if p is not None else "—", tone(p))]
        charts["adrsp"] = (lambda vals, t: (lambda w, h, c: spark_svg(vals, w, h, c[t])))(adr.get("spark") or [], tn if tn != "ink3" else "cyan")
    notes = [f'<div class=note data-box=n1>換算台股價＝ADR × 美元兌台幣 ÷ {ADR_RATIO}（1 股 ADR＝{ADR_RATIO} 股普通股）'
             + (f'；匯率 {adr["fx"]:.3f}（{md(adr["fx_date"])}，Yahoo Finance TWD=X）' if adr.get("fx") else "") + '</div>']
    if adr["missing"]:
        notes.append(f'<div class="note warn" data-box=n3>台積電 ADR（TSM）{PENDING_NOTE}</div>')
    pages.append(dict(name="tsm-adr", title=f"{head}｜台積電 ADR",
                      sub=f"資料日：ADR {mdw(pd.Timestamp(adr['date']).date()) if adr.get('date') else '—'} 美東收盤・台積電 {md(adr['tw_date']) if adr.get('tw_date') else '—'}",
                      inner="".join(rows) + "".join(notes), charts=charts))

    # 3 台指期夜盤
    charts = {}
    if night["missing"]:
        inner = f'<div class="note warn" data-box=nm>台指期夜盤{PENDING_NOTE}</div>'
        nsub = "資料日：—"
    else:
        sess = pd.Timestamp(night["session"]).date()
        dc = night.get("day_close")
        tn = tone(night.get("diff"))
        tiles = (f'<div class=tile><div class=k data-box=k1>夜盤收盤</div><div class=v data-box=v1>{fmt_num(night["close"], 0)}</div>'
                 + (f'<div class="d {tone(night["official_chg"])}" data-box=d1>漲跌 {fmt_signed(night["official_chg"], 0)} 點（期交所）</div>' if night.get("official_chg") is not None else "")
                 + '</div>'
                 f'<div class=tile><div class=k data-box=k2>較日盤收盤 {fmt_num(dc, 0) if dc else "—"}</div>'
                 f'<div class="v {tn}" data-box=v2>{fmt_signed(night["diff"], 0) if dc else "—"}<small>點</small></div>'
                 f'<div class="d {tn}" data-box=d2>{fmt_signed(night["diff_pct"], 2, "%") if dc else ""}</div></div>')
        inner = (f'<div class=grid2 style="flex:none">{tiles}</div>'
                 f'<div class=legend><span data-box=lg1>━ 夜盤走勢（1 分 K）</span><span data-box=lg2>┅ 日盤收盤</span></div>'
                 f'<div class=chartbox data-box=chart data-chart=night></div>')
        bars, ref = night["bars"], dc
        charts["night"] = lambda w, h, c: night_svg(bars, ref, w, h, c, 30 if story else 24)
        e = pd.Timestamp(night["end"])
        inner += f'<div class=note data-box=n1>時段：{md(sess)} 15:00～{md(e.date())} {"05:00" if not night.get("partial") else e.strftime("%H:%M") + "（資料到這裡為止）"}（對應美股 {md(sess)} 交易時段）</div>'
        if D.get("closure"):
            inner += f'<div class="note warn" data-box=n2>{_e(D["closure"]["text"])}</div>'
        nsub = f"資料日：{mdw(sess)} 夜盤・最近一個已收盤的夜盤"
    pages.append(dict(name="tx-night", title=f"{head}｜台指期夜盤", sub=nsub, inner=inner, charts=charts))

    # 4 大事件與科技新聞
    items = []
    for i, n in enumerate(D["news"]):
        t = pd.Timestamp(n["time"])
        col = "amber" if n["kind"] == "大事件" else "cyan"
        items.append(f'<div class=it style="--c:var(--{col})"><div class=tg data-box=tg{i}>{n["kind"]}</div>'
                     f'<div class=tt data-box=tt{i}>{_e(n["title"])}</div>'
                     f'<div class=ms data-box=ms{i}>{_e(n["source"])}・{mdw(t.date())} {t:%H:%M}</div></div>')
    if not items:
        items.append('<div class="note ink3" data-box=none>這段時間沒有符合條件的重大新聞</div>')
    cal = ""
    if D["events"]:
        lines = "".join(f'<div data-box=ev{i}>{_e(e["label"])}　{_e(e["name"])}</div>' for i, e in enumerate(D["events"][:3]))
        cal = f'<div class=cal><b data-box=calh>本週已排定（台北時間）</b>{lines}</div>'
    w0, w1 = pd.Timestamp(D["news_window"][0]), pd.Timestamp(D["news_window"][1])
    pages.append(dict(name="news", title=f"{head}｜大事件與科技新聞", sub=f"美股收盤後 {md(w0.date())} {w0:%H:%M}～{md(w1.date())} {w1:%H:%M}・只列標題",
                      inner=f'<div class=news>{"".join(items)}</div>{cal}', charts={}))

    # 5 一句話總結
    tiles = []
    for r in us["rows"]:
        if r["sym"] in ("^IXIC", "^SOX") and not r["missing"]:
            tiles.append((r["label"].replace("費城半導體", "費半"), fmt_signed(r["pct"], 2, "%"), tone(r["pct"])))
    tiles.append(("台積電 ADR", fmt_signed(adr["pct"], 2, "%") if not adr["missing"] else PENDING, tone(adr.get("pct")) if not adr["missing"] else "ink3"))
    if not night["missing"] and night.get("diff") is not None:
        tiles.append(("夜盤較日盤", fmt_signed(night["diff"], 0) + " 點", tone(night["diff"])))
    th = "".join(f'<div class=tile><div class=k data-box=sk{i}>{_e(k)}</div><div class="v {t}" data-box=sv{i}>{_e(v)}</div></div>'
                 for i, (k, v, t) in enumerate(tiles[:4]))
    pages.append(dict(name="summary", title=f"{head}｜一句話總結",
                      sub=f"資料日：美股 {md(us['date']) if us['date'] else '—'}・夜盤 {md(night['session']) if not night['missing'] else '—'}・台北 {md(tgt)} 開盤前",
                      inner=(f'<div class="grid2 tiles sumt" style="grid-template-rows:1fr 1fr">{th}</div>'
                             f'<div class=bigbox><div class=big data-box=sum>{_e(D["summary"])}</div></div><div class=disc data-box=disc>{DISCLAIMER}</div>'), charts={}))
    return pages


CHECK_JS = """() => {   // 每個 [data-box] 的框：兩兩不得相交、不得超出畫布、文字不得被截（橫向 nowrap 溢出或縱向 line-clamp 截掉）
  const els = [...document.querySelectorAll('[data-box]')];
  const R = els.map(e => { const r = e.getBoundingClientRect(); let b = { x: r.x, y: r.y, w: r.width, h: r.height };
    if (e.tagName !== 'IMG' && !e.dataset.chart) { const rg = document.createRange(); rg.selectNodeContents(e); const t = rg.getBoundingClientRect(); if (t.width) b = { x: t.x, y: t.y, w: t.width, h: t.height }; }
    return { n: e.dataset.box, ...b, cut: e.tagName !== 'IMG' && !e.dataset.chart && (e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 2) }; });
  const hits = [];
  for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++) { const a = R[i], b = R[j];
    if (a.x < b.x + b.w - 0.5 && b.x < a.x + a.w - 0.5 && a.y < b.y + b.h - 0.5 && b.y < a.y + a.h - 0.5) hits.push(a.n + '×' + b.n); }
  const W = document.documentElement.clientWidth, H = document.documentElement.clientHeight;
  const out = R.filter(b => b.x < -0.5 || b.y < -0.5 || b.x + b.w > W + 0.5 || b.y + b.h > H + 0.5).map(b => b.n);
  const card = document.querySelector('.card').getBoundingClientRect();
  return { hits, out, cut: R.filter(r => r.cut).map(r => r.n), n: R.length, content_ratio: (card.bottom - document.querySelector('.brand').getBoundingClientRect().top) / H };
}"""


def render(pages: list[dict], mode: str, theme: str, out: Path, browser, report: list) -> list[str]:
    files = []
    H = 1920 if mode == "story" else 1350
    c = ss.FRAME[theme]
    for p in pages:
        pg = browser.new_page(viewport={"width": 1080, "height": H}, device_scale_factor=1)
        pg.set_content(page_html(mode, theme, p["title"], p["sub"], p["inner"]), wait_until="load")
        pg.wait_for_timeout(250)
        for key, fn in p["charts"].items():
            w, h = pg.evaluate("(k) => { const r = document.querySelector('[data-chart=\"' + k + '\"]').getBoundingClientRect(); return [Math.floor(r.width), Math.floor(r.height)]; }", key)
            svg = fn(max(w, 40), max(h, 30), c) if w > 0 and h > 0 else ""
            if svg:
                pg.evaluate("([k, src, w, h]) => { const b = document.querySelector('[data-chart=\"' + k + '\"]'); b.innerHTML = '<img width=' + w + ' height=' + h + ' src=\"' + src + '\">'; }",
                            [key, svg_uri(svg), w, h])
        pg.wait_for_timeout(250)
        res = pg.evaluate(CHECK_JS)
        name = f"{'story' if mode == 'story' else 'threads'}_{p['name']}.png"
        res.update(file=name, w=1080, h=H)
        report.append(res)
        pg.screenshot(path=str(out / name), full_page=False)
        pg.close()
        files.append(name)
    return files


# ============================================================================ 文案
def caption(D: dict, ymd: str, max_len: int = ss.THREADS_MAX) -> str:
    tgt = pd.Timestamp(D["target"]).date()
    us, adr, night = D["us"], D["adr"], D["night"]
    link = lambda route: ss.deep_link(route, KIND, ymd)
    L1 = f"台股盤前｜{md(tgt)}"
    seg = []
    if us["date"]:
        xs = [f"{r['label'].replace('費城半導體', '費半').replace('道瓊工業', '道瓊').replace('VIX 波動率', 'VIX')} "
              + (PENDING if r["missing"] else (fmt_num(r["close"], 2) if r["sym"] == "^VIX" else fmt_signed(r["pct"], 2, "%")))
              for r in us["rows"]]
        seg.append(f"美股 {md(us['date'])}：" + "、".join(xs))
    if adr["missing"]:
        seg.append(f"台積電 ADR：{PENDING}" + (f"（台積電前收 {fmt_num(adr['tw_close'], 0)}，{md(adr['tw_date'])}）" if adr.get("tw_close") else ""))
    else:
        s = f"台積電 ADR：{fmt_num(adr['close'])} 美元（{fmt_signed(adr['pct'], 2, '%')}）"
        if adr.get("conv"):
            s += f"，換算 {fmt_num(adr['conv'], 1)} 元"
        if adr.get("prem") is not None:
            s += f"，{'溢價' if adr['prem'] >= 0 else '折價'} {abs(adr['prem']):.2f}%"
        seg.append(s)
    if not night["missing"]:
        s = f"台指期夜盤（{md(night['session'])}）：收 {fmt_num(night['close'], 0)}"
        if night.get("diff") is not None:
            s += f"，較日盤收盤 {fmt_signed(night['diff'], 0)} 點（{fmt_signed(night['diff_pct'], 2, '%')}）"
        seg.append(s)
    if D.get("closure"):
        seg.append(D["closure"]["text"])
    ev = [n for n in D["news"] if n["kind"] == "大事件"]
    te = [n for n in D["news"] if n["kind"] == "科技"]
    cal = "；".join(f"{e['name']} {e['label']}" for e in D["events"][:2])
    tail = [f"看更多 {link('overview')}", DISCLAIMER, HASHTAGS]
    for ne, nt, use_cal in ((len(ev), len(te), True), (1, 2, True), (1, 1, True), (1, 1, False), (1, 0, False), (0, 0, False)):
        lines = [L1] + seg
        if ne and ev:
            lines.append("大事件：" + "／".join(f"{n['title']}（{n['source']}）" for n in ev[:ne]))
        if nt and te:
            lines.append("科技：" + "／".join(f"{n['title']}（{n['source']}）" for n in te[:nt]))
        if use_cal and cal:
            lines.append("本週：" + cal)
        txt = "\n".join(lines + tail)
        if len(txt) <= max_len:
            return txt
    return txt


# ============================================================================ 主程式
def main() -> int:
    ap = argparse.ArgumentParser(description="台股盤前社群貼文（Threads 輪播＋IG 限動）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--date", default="", help="盤前的目標開盤日 YYYY-MM-DD（預設＝下一個台股開盤日）")
    ap.add_argument("--frame", default="light", choices=list(ss.FRAME))
    ap.add_argument("--force", action="store_true", help="非交易日／資料舊／已發過也照產（示範用，不可用在發布）")
    ap.add_argument("--posted-json", default="", help="social-snaps 的 state/posted.json；premarket-<目標日> 已在裡面就不產（結束碼 10）")
    ap.add_argument("--max-stale-days", type=int, default=5, help="美股收盤日距目標日超過幾天就不發")
    args = ap.parse_args()

    hol = load_holidays()
    now = datetime.now(TPE)
    target = pd.Timestamp(args.date).date() if args.date else next_trading_day(now, hol)
    if not is_tw_trading_day(target, hol) and not args.force:
        print(f"[premarket] {target} 不是台股交易日 → 不發")
        return 10
    key = f"{KIND}-{target.isoformat()}"
    if args.posted_json and not args.force:
        try:
            if key in json.loads(Path(args.posted_json).read_text("utf-8")):
                print(f"[premarket] {key} 已發過 → 不重複")
                return 10
        except Exception:  # noqa: BLE001
            pass

    D = collect(target, *load_lake(target))
    if not D["us"]["date"]:
        print("[premarket] 資料庫讀不到美股收盤")
        return 2
    stale = (target - pd.Timestamp(D["us"]["date"]).date()).days
    if stale > args.max_stale_days and not args.force:
        print(f"[premarket] 美股最新收盤 {D['us']['date']} 距 {target} 已 {stale} 天 → 不發")
        return 10

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(json.dumps({k: v for k, v in D.items()}, ensure_ascii=False, indent=1, default=str), "utf-8")
    from playwright.sync_api import sync_playwright
    report: list = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=ss.CHROMIUM) if ss.CHROMIUM else p.chromium.launch()
        threads = render(build_pages(D, "threads"), "threads", args.frame, out, browser, report)
        stories = render(build_pages(D, "story"), "story", args.frame, out, browser, report)
        browser.close()
    (out / "layout_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    bad = [r for r in report if r["hits"] or r["out"] or r["cut"]]
    print(f"[premarket] 重疊檢查：程式 {len(report)} 張、{sum(r['n'] for r in report)} 個框、{len(bad)} 筆問題")
    for r in report:
        print(f"  {r['file']}: 框 {r['n']}、填滿 {r['content_ratio']:.0%}" + (f"  ✗ {r['hits']} {r['out']} {r['cut']}" if r in bad else ""))
    if bad:
        return 3
    ymd = target.strftime("%Y%m%d")
    text = caption(D, ymd)
    manifest = {"kind": KIND, "taken_at": now.isoformat(timespec="seconds"), "data_date": target.isoformat(), "slot_key": key,
                "threads": {"text": text, "images": threads}, "story": stories}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    (out / "caption.txt").write_text(text + "\n", "utf-8")
    print(f"[premarket] manifest：{out / 'manifest.json'}；文案 {len(text)} 字")
    return 0


if __name__ == "__main__":
    sys.exit(main())
