"""台股盤前社群貼文（Threads 輪播＋IG 限動）：美股日 K、台指期日 K、台積電 ADR 日 K、今日焦點消息、一句話總結。

Andy 2026-10-26 原話：「需要在新增盤前，只有開盤，當天還需要新增盤前內容，裡面包含 昨日 或上週美股狀況，是否有大事件，
科技新聞大事，以及台指夜盤 台積電ADR 狀況 那斯達克 費半 標普 等狀況，這些也需要以貼文形式呈現 需要截圖給我」。

第 2 版（Andy 看完 10/27 範例的改版要求，CEO 轉述）
------------------------------------------------------
· 美股：除了 VIX，那斯達克、費半、標普、道瓊都改成「日 K」蠟燭圖（近 25 日）。
· 台指期與台積電 ADR：日 K＋MA5／MA20＋RSI(14)，附 2～3 行只依技術面數字的描述（位於／站上／跌破均線、RSI 區間、量價），不給買賣建議。
· 消息：只留標題；分「新聞／事件／科技／總經」四類，不指定主題、以「最多家媒體同時報導」當最受關注；分類色塊、大標題、無來源無時間。
· 圖上所有備註都拿掉（資料日小字、來源、查證中、休市、時段、本週日程、免責）；資料日只留在標題列「台股盤前｜10/27」。
· 查不到的數字不填：那一格整格不畫，或換成可得的指標（例：台積電 ADR 沒進資料庫 → 換成台積電 2330 日 K）。
· 文案放完整標題清單，最後一行「想看完整內容，留言『消息』」。
· manifest 多一個 premarket_news（分類、標題、連結、來源、時間），另存 premarket_news.json；格式見
  docs/marketing/social_unit/premarket_news_format.md（網站「每日精選 → 盤前消息」讀它）。

資料（只讀資料湖，Actions checkout 下來就有）
--------------------------------------------
intl_daily（yfinance：^IXIC ^SOX ^GSPC ^DJI ^VIX TSM TWD=X；2026-10-26 起多存 open／high／low）、
index_ohlc（台指期 FUT 日盤日 K）、index_intraday（FUT_N 夜盤 1 分 K）、price_daily（2330）、news。
沒有 open／high／low 的舊列：美股小圖退回收盤折線（可得的指標），不假造 K 棒。

版面：共用 social_snap 的配色、LOGO、深連結（不改 social_snap.py）；程式量 [data-box] 的框，兩兩不得相交、不得出界、
文字不得被截，有一筆就結束碼 3、不發。

用法
----
    python scripts/social_premarket.py --date 2026-10-27 --out /tmp/premarket --force
    python scripts/social_premarket.py --out snaps/premarket-$(TZ=Asia/Taipei date +%Y%m%d-%H%M) --posted-json state/posted.json

結束碼：0＝有產出；10＝刻意不發（目標日不是台股交易日、美股資料太舊、這一篇已發過）；2＝資料完全讀不到；3＝版面重疊／截斷。
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import re
import sys
from datetime import date, datetime, timedelta
from datetime import time as dtime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import social_snap as ss  # 只讀它的常數與小工具，不改它

from pipeline import indicators as ind  # RSI 用專案同一套 Wilder 口徑

TPE = ZoneInfo("Asia/Taipei")
NY = ZoneInfo("America/New_York")
OPEN_TPE = dtime(8, 45)          # 台指期日盤開盤（盤前貼文的時間上限）
KIND = "premarket"
WEEK = "一二三四五六日"

US_ROWS = [("^IXIC", "那斯達克"), ("^SOX", "費城半導體"), ("^GSPC", "標普500"), ("^DJI", "道瓊工業"), ("^VIX", "VIX 波動率")]
ADR_SYM, FX_SYM, TSMC = "TSM", "TWD=X", "2330"
ADR_RATIO = 5                     # 1 股 ADR＝5 股台積電普通股
K_N = 25                          # 美股那頁每列的日 K 根數（小圖）
K_LONG = 125                      # 台指期／ADR 主圖的日 K 根數（約半年交易日；Andy 10-26：「K 棒期間至少半年」）
MAS = [(5, "5日"), (10, "10日"), (20, "月線20"), (60, "季線60"), (120, "半年線120"), (240, "年線240")]
SRC_NAME = {"cnyes": "鉅亨", "udn": "聯合新聞網", "technews": "科技新報"}
DISCLAIMER = "資料：Yahoo Finance、期交所公開資料、新聞媒體整理，僅供參考，不構成投資建議"
HASHTAGS = "#台股 #盤前 #美股 #台指期 #台積電"
ASK_LINE = "想看完整內容，留言『消息』"
RELEASE_NAME = {"cpi": "美國 CPI", "nfp": "美國非農就業", "gdp": "美國 GDP", "pce": "美國 PCE"}

# 消息：排除喊盤、權證、促銷、個人理財問答這類（不是「消息」）
SKIP_RE = re.compile(r"杜金龍|擂台|購\d|報名|優惠|喊進|潛力股|作帳|目標價|抄底|進場|閉眼|私房|網友|妙招|怎麼放|旅展|豪宅|戰隊|"
                     r"定期定額|論壇|成交前十|掛牌|周漲|熱門股|〈|大代誌|搶先看|本周大事|操盤筆記|周冠軍|飆股的故事|股海自由行|就市論勢|支撐|鞏固")
# 不當成「主題」的泛用字（這些字幾乎每篇都有，拿來分群會把所有新聞黏在一起）
GENERIC = {"ai", "人工智慧", "ai 人工智慧", "美股", "台股", "優分析", "科技", "美國", "中國", "top", "投資", "財經", "市場動態", "國際金融",
           "國際貿易", "名人談", "經濟", "市場", "交易", "資本", "支出", "需求", "供給", "半導體", "晶片", "科技生活", "零組件", "材料",
           "能源", "產能", "財報", "股價", "etf", "台股etf", "營收", "獲利", "法人", "外資", "資金", "公司治理", "軟體、系統", "數位通訊",
           "材料、設備", "生物科技", "醫療科技", "金融政策", "能源科技"}
CAT_ORDER = ["新聞", "事件", "科技", "總經"]
MACRO_RE = re.compile(r"Fed|聯準會|央行|利率|降息|升息|殖利率|通膨|CPI|GDP|PCE|非農|就業|失業|衰退|油價|金價|黃金|美元指數|美元走|日元|日圓|匯率|美債|公債|景氣|PMI")
EVENT_RE = re.compile(r"戰爭|戰事|開戰|戰線|作戰|停火|談判|攻擊|制裁|關稅|選舉|期中|示威|抗議|颱風|地震|罷工|峰會|會談|川普|普丁|伊朗|以色列|烏克蘭|俄羅斯|北韓|金正恩|"
                      r"中東|胡塞|休市|政策|法案|禁令")
TECH_RE = re.compile(r"AI|晶片|半導體|台積電|輝達|NVIDIA|Nvidia|記憶體|HBM|蘋果|iPhone|伺服器|雲端|OpenAI|Anthropic|CoWoS|CPO|載板|PCB|"
                     r"英特爾|三星|美光|超微|AMD|博通|亞馬遜|AWS|微軟|谷歌|Google|特斯拉|SpaceX|機器人|資料中心|算力")
CAT_CAP = 2                       # 同一類最多幾則（四類盡量都有；Andy 10-26）
# 跟台股／市場／科技產業有關的字（相關度加分）與政治口水、八卦（降權）；Andy 10-26：「優先挑跟台股、市場、科技產業相關，降權政治八卦」
MARKET_RE = re.compile(r"台股|加權|大盤|股價|股市|美股|指數|期貨|外資|投信|自營|法人|營收|財報|獲利|EPS|毛利|法說|ETF|除息|配息|漲停|跌停|上市|上櫃|"
                       r"IPO|訂單|出貨|產能|擴產|資本支出|供應鏈|市值|殖利率|油價|關稅|出口管制|制裁|匯率|台幣|\d{4}")
STOCK_RE = re.compile(r"台股|加權|大盤|股價|股市|美股|指數|期貨|外資|投信|法人|營收|財報|EPS|法說|ETF")   # 口水標題裡有這些才不降權
GOSSIP_RE = re.compile(r"批評?|嗆|罵|酸|怒|轟|諷|嘲|槓上|互槓|口水|八卦|緋聞|離婚|婚|網紅|名嘴|爆料|私生活|澤倫斯基|罷免")


# ============================================================================ 小工具
def fmt_num(v: float, nd: int = 2) -> str:
    return f"{v:,.{nd}f}"


def fmt_signed(v: float, nd: int = 2, suffix: str = "") -> str:
    """+1.23／−1.23（減號用全形減號 U+2212，跟網站一致）。"""
    s = f"{abs(v):,.{nd}f}{suffix}"
    return ("+" if v > 0 else "−" if v < 0 else "±") + s


DATE_TXT = ""      # 標題列右側日期（main 設定），例 10/27 週二


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
        return {str(k) for k in (d.get("days") or {})}
    except Exception:  # noqa: BLE001
        return set()


def is_tw_trading_day(d: date, holidays: set[str]) -> bool:
    """開盤前沒有當天的資料可看，只能用行事曆：平日且不在 tw_holidays.yaml。颱風假這種臨時休市看不到。"""
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


# ============================================================================ 日 K 與技術面（純函式，測試不連網）
def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(np.nan, index=df.index)


def daily_frame(df: pd.DataFrame) -> pd.DataFrame:
    """統一成 date／open／high／low／close／volume，按日期排、去重（同一天留最後一筆）。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    out = pd.DataFrame({"date": df["date"].astype(str).str[:10], "open": _num(df, "open"), "high": _num(df, "high"),
                        "low": _num(df, "low"), "close": _num(df, "close"), "volume": _num(df, "volume")})
    return out.dropna(subset=["close"]).drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def _f(v):
    return None if pd.isna(v) else float(v)


def k_series(df: pd.DataFrame, n: int = K_N) -> dict:
    """最後 n 根日 K＋整段歷史算出的 MA5／10／20／60／120／240 與 RSI14（指標先用全歷史算再切，均線開頭才不會斷）。
    has_ohlc＝最後 n 根都有開高低 → 畫 K 棒；否則畫收盤折線（可得的指標，不假造 K 棒）。"""
    d = daily_frame(df)
    if d.empty:
        return {"bars": [], "has_ohlc": False}
    for p, _ in MAS:
        d[f"ma{p}"] = d["close"].rolling(p).mean()
    d["rsi"] = ind.rsi(d["close"], 14)
    d["vma5"] = d["volume"].rolling(5).mean().shift(1)    # 前 5 日均量（不含當天）
    tail = d.tail(n)
    has = bool(tail[["open", "high", "low"]].notna().all().all())
    bars = [{"date": r["date"], "o": _f(r["open"]), "h": _f(r["high"]), "l": _f(r["low"]), "c": float(r["close"]), "v": _f(r["volume"]),
             **{f"ma{p}": _f(r[f"ma{p}"]) for p, _ in MAS}, "rsi": _f(r["rsi"]), "vma5": _f(r["vma5"])} for _, r in tail.iterrows()]
    return {"bars": bars, "has_ohlc": has}


def ta_rows(ks: dict) -> list[tuple[str, str, str]]:
    """技術面表格（左欄項目｜中欄數值｜右欄狀態），三列：收盤、RSI(14)、量能。只講數字位置，不判多空、不給建議。
    收盤的狀態：今天真的穿過哪幾條均線（跟昨天在不同側）就寫「站上／跌破 5日、10日」；都沒穿過就寫跟月線、季線的相對位置。"""
    b = ks.get("bars") or []
    if len(b) < 2:
        return []
    t, y = b[-1], b[-2]
    nd = 2 if t["c"] < 1000 else 0
    rows = []
    up, dn, pos = [], [], []
    for p, name in MAS:
        k = f"ma{p}"
        if t.get(k) is None:
            continue
        above = t["c"] >= t[k]
        if y.get(k) is not None and above != (y["c"] >= y[k]):
            (up if above else dn).append(name)
    for p, name in ((20, "月線"), (60, "季線")):
        if t.get(f"ma{p}") is not None:
            pos.append(f"{name}{'之上' if t['c'] >= t[f'ma{p}'] else '之下'}")
    st = "、".join(x for x in (("站上 " + "、".join(up)) if up else "", ("跌破 " + "、".join(dn)) if dn else "") if x) or "、".join(pos)
    rows.append(("收盤", fmt_num(t["c"], nd), st))
    if t.get("rsi") is not None:
        r = t["rsi"]
        zone = "70 以上高檔區" if r >= 70 else "30 以下低檔區" if r <= 30 else ("30–70 區間・50 以上" if r >= 50 else "30–70 區間・50 以下")
        rows.append(("RSI(14)", f"{r:.1f}", zone))
    if t.get("v") and t.get("vma5"):
        vp = (t["v"] / t["vma5"] - 1) * 100
        pv = ("價漲" if t["c"] > y["c"] else "價跌" if t["c"] < y["c"] else "價平") + ("量增" if vp > 0 else "量縮")
        rows.append(("量能", fmt_signed(vp, 1, "%"), f"較前 5 日均量・{pv}"))
    return rows


def ma_values(ks: dict) -> list[tuple[str, float]]:
    """最後一根的各條均線值（data.json 用；算不出來的那條不列）。"""
    b = (ks.get("bars") or [{}])[-1]
    return [(name, b[f"ma{p}"]) for p, name in MAS if b.get(f"ma{p}") is not None]


def us_close(intl: pd.DataFrame, target: date) -> dict:
    """目標開盤日之前最後一個美股交易日（以 ^IXIC 有收盤的日期為準）的五大指數。缺的那檔 missing=True（圖上整格不畫）。"""
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
        s = daily_frame(df[(df["symbol"] == sym) & (df["date"] <= usd)])
        if s.empty or s["date"].iloc[-1] != usd or len(s) < 2:
            out["rows"].append({"sym": sym, "label": label, "missing": True})
            continue
        c, p = float(s["close"].iloc[-1]), float(s["close"].iloc[-2])
        out["rows"].append({"sym": sym, "label": label, "missing": False, "close": c, "chg": c - p,
                            "pct": (c / p - 1) * 100 if p else 0.0, "k": k_series(s)})
    return out


def adr_info(intl: pd.DataFrame, price: pd.DataFrame, us_date: str | None, target: date) -> dict:
    """台積電 ADR：收盤、漲跌%、換算台股價＝ADR × 匯率 ÷ 5、對台積電前一日收盤的溢價／折價%＋ADR 日 K。
    ADR 沒進資料庫時 missing=True，另外附台積電（2330）日 K 當替代（tw_k）。"""
    r: dict = {"missing": True, "date": us_date}
    if price is not None and not price.empty:
        t = daily_frame(price[(price["code"].astype(str) == TSMC) & (price["date"].astype(str).str[:10] < target.isoformat())])
        if not t.empty:
            r["tw_close"], r["tw_date"] = float(t["close"].iloc[-1]), t["date"].iloc[-1]
            if len(t) >= 2:
                r["tw_chg"] = r["tw_close"] - float(t["close"].iloc[-2])
                r["tw_pct"] = (r["tw_close"] / float(t["close"].iloc[-2]) - 1) * 100
            r["tw_k"] = k_series(t, K_LONG)
    if intl is not None and not intl.empty and us_date:
        df = intl.copy()
        df["date"] = df["date"].astype(str).str[:10]
        fx = daily_frame(df[(df["symbol"] == FX_SYM) & (df["date"] <= us_date)])
        if not fx.empty:
            r["fx"], r["fx_date"] = float(fx["close"].iloc[-1]), fx["date"].iloc[-1]
        a = daily_frame(df[(df["symbol"] == ADR_SYM) & (df["date"] <= us_date)])
        if len(a) >= 2 and a["date"].iloc[-1] == us_date:
            c, p = float(a["close"].iloc[-1]), float(a["close"].iloc[-2])
            r.update(missing=False, close=c, chg=c - p, pct=(c / p - 1) * 100 if p else 0.0, k=k_series(a, K_LONG))
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
             partial=bool(bars["t"].iloc[-1] < datetime.combine(sess + timedelta(days=1), dtime(4, 30), tzinfo=TPE)))
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


def tx_daily(ohlc: pd.DataFrame, target: date) -> dict:
    """台指期日盤（FUT）日 K＋指標；最後一根的日期、收盤、漲跌。"""
    if ohlc is None or ohlc.empty:
        return {"missing": True}
    d = daily_frame(ohlc[(ohlc["symbol"].astype(str) == "FUT") & (ohlc["date"].astype(str).str[:10] < target.isoformat())])
    if len(d) < 2:
        return {"missing": True}
    c, p = float(d["close"].iloc[-1]), float(d["close"].iloc[-2])
    return {"missing": False, "date": d["date"].iloc[-1], "close": c, "chg": c - p, "pct": (c / p - 1) * 100, "k": k_series(d, K_LONG)}


def closure_note(last_td: str | None, target: date) -> dict | None:
    """上一個台股交易日到目標日之間有平日沒開盤 → 「台股 10/23–10/26 休市 4 天」（只進文案與 data.json，不上圖）。"""
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


# ============================================================================ 消息（最多家媒體同時報導＝最受關注）
def news_category(title: str, cat: str = "") -> str:
    """四類，依序判斷：事件（戰爭、關稅、選舉、天災…）→ 總經（利率、通膨、油價、匯率…）→ 科技（AI、半導體、大型科技）→ 其他＝新聞。"""
    if EVENT_RE.search(title):
        return "事件"
    if MACRO_RE.search(title):
        return "總經"
    if TECH_RE.search(title) or cat == "科技":
        return "科技"
    return "新聞"


def _kw(s) -> set[str]:
    return {k.strip().lower() for k in str(s or "").split(",") if len(k.strip()) >= 2}


def _item(r, topic: str, cov: dict) -> dict:
    return {"category": news_category(str(r["title"]), str(r.get("category", ""))), "title": re.sub(r"[\s\u3000]+", " ", str(r["title"])).strip(),
            "url": str(r.get("url") or ""), "source": SRC_NAME.get(str(r["source"]), str(r["source"])),
            "published_at": r["t"].isoformat(), "topic": topic, "coverage": cov}


def pick_news(news: pd.DataFrame, start: datetime, end: datetime, n: int = 5) -> list[dict]:
    """美股收盤後～台股開盤前的新聞，先看跟台股／市場／科技產業的相關度，再看「主題被幾家媒體、幾篇報導」，取前 n 則；四類盡量都有。
    主題＝新聞附的關鍵字（鉅亨、科技新報有附）＋出現在標題裡的同一個詞（聯合新聞網沒附關鍵字，用標題比對）。
    不改寫標題；同一類最多 CAT_CAP 則；主題不夠時用最新的補滿。"""
    if news is None or news.empty:
        return []
    df = news.copy()
    if "keywords" not in df.columns:
        df["keywords"] = ""
    df["t"] = df["published_at"].map(parse_pub)
    df = df[df["t"].notna()]
    df = df[(df["t"] >= pd.Timestamp(start)) & (df["t"] < pd.Timestamp(end))]
    df = df[~df["title"].astype(str).str.contains(SKIP_RE)].drop_duplicates("title").reset_index(drop=True)
    if df.empty:
        return []
    raw: dict[str, int] = {}
    for kws in df["keywords"]:
        for k in _kw(kws):
            raw[k] = raw.get(k, 0) + 1
    vocab = {k for k, c in raw.items() if c >= 2 and k not in GENERIC}
    stat: dict[str, tuple[set, list]] = {}
    toks: dict[int, set] = {}
    for i, r in df.iterrows():
        tl = str(r["title"]).lower()
        toks[i] = (_kw(r["keywords"]) | {v for v in vocab if v in tl}) - GENERIC
        for k in toks[i]:
            s = stat.setdefault(k, (set(), []))
            s[0].add(str(r["source"]))
            s[1].append(i)
    # 每個主題選代表標題：先挑跟市場最相關的那篇，再挑跟同主題其他篇共用關鍵字最多（最居中的角度），同分取標題較完整的 → 候選清單
    cands = []
    for k in sorted(stat, key=lambda k: (-len(stat[k][0]), -len(stat[k][1]), k)):
        ids = stat[k][1]
        if len(ids) < 2:
            continue
        best = max(ids, key=lambda i: (-relevance_tier(str(df.at[i, "title"]), news_category(str(df.at[i, "title"]), str(df.at[i, "category"]))),
                                       sum(len(toks[i] & toks[j]) for j in ids if j != i), len(str(df.at[i, "title"])), df.at[i, "t"].value))
        cands.append((_item(df.loc[best], k, {"sources": len(stat[k][0]), "articles": len(ids)}), set(ids), best))
    for i in df.sort_values("t", ascending=False).index:      # 單篇也當候選（排在多家報導的主題後面），補類別或補數量用
        cands.append((_item(df.loc[i], "", {"sources": 1, "articles": 1}), {i}, i))
    cands.sort(key=lambda c: (relevance_tier(c[0]["title"], c[0]["category"]), -c[0]["coverage"]["sources"], -c[0]["coverage"]["articles"]))
    used: set[int] = set()
    picked: list[dict] = []
    per_cat: dict[str, int] = {}

    def take(it, ids):
        used.update(ids)
        per_cat[it["category"]] = per_cat.get(it["category"], 0) + 1
        picked.append(it)
    # 第一輪：四類各挑最相關、最多家報導的一則（政治口水那一級不參加）
    for cat in CAT_ORDER:
        for it, ids, rep in cands:
            if it["category"] == cat and rep not in used and relevance_tier(it["title"], cat) < 2:
                take(it, ids)
                break
    # 第二輪：照相關度＋報導家數補滿；同類最多 CAT_CAP 則；真的不夠才放寬類別上限、最後才用口水那一級
    for relax in (0, 1, 2):
        for it, ids, rep in cands:
            if len(picked) >= n:
                break
            if rep in used or (relax < 2 and relevance_tier(it["title"], it["category"]) >= 2):
                continue
            if relax == 0 and per_cat.get(it["category"], 0) >= CAT_CAP:
                continue
            take(it, ids)
    picked.sort(key=lambda it: (relevance_tier(it["title"], it["category"]), -it["coverage"]["sources"], -it["coverage"]["articles"]))
    return picked[:n]


def relevance_tier(title: str, cat: str) -> int:
    """0＝跟台股／市場／科技產業直接相關（科技、總經、新聞類，或事件但有市場字眼）；1＝其他事件（地緣政治）；2＝政治口水、八卦。"""
    if GOSSIP_RE.search(title) and not (TECH_RE.search(title) or STOCK_RE.search(title)):
        return 2
    if cat != "事件" or MARKET_RE.search(title):
        return 0
    return 1


def upcoming_events(target: date, cal: pd.DataFrame | None, days: int = 5) -> list[dict]:
    """目標日起 days 天內已排定的美國重大日程（只進 data.json，圖上不放）。"""
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
    merged: list[dict] = []
    for e in ev:
        if merged and merged[-1]["t"] == e["t"]:
            merged[-1]["name"] += "、" + e["name"].replace("美國 ", "")
        else:
            merged.append(dict(e))
    return [{"time": e["t"].isoformat(), "name": e["name"], "label": f"{mdw(e['t'].date())} {e['t']:%H:%M}"} for e in merged]


def summary_line(us: dict, adr: dict, tx: dict, night: dict) -> str:
    """一句話總結：只用數字事實，不給方向判斷、不給買賣建議（休市說明不上圖，只進文案）。"""
    parts = []
    if us.get("date"):
        got = [f"{r['label'].replace('費城半導體', '費半').replace('道瓊工業', '道瓊')} {fmt_signed(r['pct'], 2, '%')}" for r in us["rows"]
               if not r["missing"] and r["sym"] in ("^IXIC", "^SOX", "^GSPC", "^DJI")]
        if got:
            parts.append("美股" + "、".join(got))
    if not adr.get("missing"):
        s = f"台積電 ADR {fmt_signed(adr['pct'], 2, '%')}"
        if adr.get("prem") is not None:
            s += f"、換算{'溢價' if adr['prem'] >= 0 else '折價'} {abs(adr['prem']):.2f}%"
        parts.append(s)
    if not night.get("missing") and night.get("diff") is not None and not night.get("partial"):
        parts.append(f"台指期夜盤較日盤 {fmt_signed(night['diff'], 0)} 點")
    elif not tx.get("missing"):
        parts.append(f"台指期 {fmt_signed(tx['chg'], 0)} 點")
    return "；".join(parts) + "。" if parts else ""


def collect(target: date, intl, price, intra, ohlc, news, cal) -> dict:
    us = us_close(intl, target)
    adr = adr_info(intl, price, us["date"], target)
    night = night_session(intra, ohlc, target)
    tx = tx_daily(ohlc, target)
    last_td = None
    if ohlc is not None and not ohlc.empty:
        t = ohlc[(ohlc["symbol"].astype(str) == "TSE") & (ohlc["date"].astype(str).str[:10] < target.isoformat())]
        if not t.empty:
            last_td = str(t["date"].astype(str).str[:10].max())
    start = us_close_tpe(us["date"]) if us["date"] else datetime.combine(target - timedelta(days=1), dtime(5, 0), tzinfo=TPE)
    end = datetime.combine(target, OPEN_TPE, tzinfo=TPE)
    return {"target": target.isoformat(), "us": us, "adr": adr, "tx": tx, "night": night, "last_td": last_td,
            "closure": closure_note(last_td, target), "news_window": [start.isoformat(), end.isoformat()],
            "news": pick_news(news, start, end), "events": upcoming_events(target, cal),
            "summary": summary_line(us, adr, tx, night),
            "ta": {k: {"rows": ta_rows(v["k"]), "ma": ma_values(v["k"])} for k, v in (("tx", tx), ("adr", adr)) if not v.get("missing")}}


def load_lake(target: date) -> tuple:
    from pipeline.util import store
    ys = sorted({d.year for d in (target, target - timedelta(days=270), target - timedelta(days=560))})   # MA240＋半年 K 棒約需 365 個交易日
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
FONT = "Noto Sans CJK TC,Noto Sans TC,WenQuanYi Zen Hei,sans-serif"
# 均線六色＋RSI：避開紅綠（K 棒用），由短到長從暖到冷再到深灰
MA_COL = {"light": {**{f"ma{n}": c for n, c in zip((5, 10, 20, 60, 120, 240), ss.TH.MA_COLORS)}, "rsi": "#0A6A86"},   # 亮色 HUD 六色（social_theme.MA_COLORS）
          "dark": {"ma5": "#ffb454", "ma10": "#f2dc5d", "ma20": "#b49bff", "ma60": "#6aa8ff", "ma120": "#d0a07a", "ma240": "#c8cdd8", "rsi": "#3ee0ff"}}


def line_svg(vals: list[float], w: int, h: int, color: str) -> str:
    """收盤折線（沒有開高低時用；也給 VIX 用）。"""
    if len(vals) < 2:
        return ""
    pad = int(max(4, h / 22) + 4)
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


def candle_svg(ks: dict, w: int, h: int, c: dict, theme: str, *, fs: int = 0, ma: bool = False, rsi: bool = False) -> str:
    """日 K：K 棒收≥開＝紅、收＜開＝綠（台股紅漲綠跌慣例）。
    fs>0 才畫軸字（左側價格、下方日期）；ma＝畫六條均線；rsi＝下方 RSI(14) 副圖（30／70 虛線）。沒有開高低時改畫收盤折線。"""
    b = ks.get("bars") or []
    if len(b) < 2:
        return ""
    if not ks.get("has_ohlc"):
        return line_svg([x["c"] for x in b], w, h, c["cyan"])
    mc = MA_COL[theme]
    L = int(fs * 4.0) if fs else 4
    R, T = 6, (int(fs * 0.6) if fs else 4)
    B = int(fs * 1.8) if fs else 4
    gap = int(fs * 0.5) if rsi else 0
    ph = (h - T - B - gap) * (0.78 if rsi else 1.0)        # 價格區高
    rh = (h - T - B - gap) - ph if rsi else 0
    # 縱軸：K 棒＋5～60 日均線全包；半年線、年線離太遠時最多再放寬 15%，超出的部分裁掉（不然 K 棒會被壓扁）
    short = [x[f"ma{p}"] for x in b for p in (5, 10, 20, 60) if ma and x.get(f"ma{p}") is not None]
    long_ = [x[f"ma{p}"] for x in b for p in (120, 240) if ma and x.get(f"ma{p}") is not None]
    lo, hi = min([x["l"] for x in b] + short), max([x["h"] for x in b] + short)
    sp = (hi - lo) or 1
    if long_:
        lo = max(min([lo] + long_), lo - sp * 0.15)
        hi = min(max([hi] + long_), hi + sp * 0.15)
        sp = hi - lo
    lo, hi = lo - sp * 0.04, hi + sp * 0.04
    n = len(b)
    step = (w - L - R) / n

    def X(i):
        return L + step * (i + 0.5)

    def Y(v):
        return T + (hi - v) / (hi - lo) * ph
    g = [(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">'
          f'<defs><clipPath id="pc"><rect x="{L}" y="{T}" width="{w - L - R}" height="{ph:.1f}"/></clipPath></defs>')]
    if fs:
        raw = (hi - lo) / 5                                  # 整數刻度（約 4～5 條）：1／2／2.5／5 × 10^n
        mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
        stp = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
        for v in [k * stp for k in range(math.ceil(lo / stp), math.floor(hi / stp) + 1)]:
            y = Y(v)
            g.append(f'<line x1="{L}" y1="{y:.1f}" x2="{w - R}" y2="{y:.1f}" stroke="{c["line"]}" stroke-width="1.5"/>')
            g.append(f'<text x="{L - 8}" y="{y + fs * 0.35:.1f}" font-size="{fs}" fill="{c["ink3"]}" text-anchor="end">{v:,.{0 if stp >= 1 else 1}f}</text>')
        for i, anchor in ((0, "start"), (n // 3, "middle"), (2 * n // 3, "middle"), (n - 1, "end")):
            x = X(i) - step / 2 if anchor == "start" else X(i) + step / 2 if anchor == "end" else X(i)
            g.append(f'<text x="{x:.1f}" y="{h - fs * 0.35:.1f}" font-size="{fs}" fill="{c["ink3"]}" text-anchor="{anchor}">{md(b[i]["date"])}</text>')
    bw = max(2.0, step * 0.62)
    for i, x in enumerate(b):
        col = c["rise"] if x["c"] >= x["o"] else c["fall"]
        top, bot = Y(max(x["o"], x["c"])), Y(min(x["o"], x["c"]))
        g.append(f'<line x1="{X(i):.1f}" y1="{Y(x["h"]):.1f}" x2="{X(i):.1f}" y2="{Y(x["l"]):.1f}" stroke="{col}" stroke-width="{max(1.5, bw / 6):.1f}"/>')
        g.append(f'<rect x="{X(i) - bw / 2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(1.5, bot - top):.1f}" fill="{col}"/>')
    if ma:
        for p, _ in reversed(MAS):          # 長均線先畫、短的疊在上面
            k = f"ma{p}"
            pts = [f"{X(i):.1f},{Y(x[k]):.1f}" for i, x in enumerate(b) if x.get(k) is not None]
            if len(pts) >= 2:
                g.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{mc[k]}" stroke-width="2.5" stroke-linejoin="round" clip-path="url(#pc)"/>')
    if rsi:
        y0 = T + ph + gap

        def RY(v):
            return y0 + (100 - v) / 100 * rh
        g.append(f'<rect x="{L}" y="{y0:.1f}" width="{w - L - R}" height="{rh:.1f}" fill="none" stroke="{c["line"]}" stroke-width="1.5"/>')
        for lv in (30, 70):
            g.append(f'<line x1="{L}" y1="{RY(lv):.1f}" x2="{w - R}" y2="{RY(lv):.1f}" stroke="{c["ink3"]}" stroke-width="1.5" stroke-dasharray="8 6"/>')
            if fs:
                g.append(f'<text x="{L - 8}" y="{RY(lv) + fs * 0.35:.1f}" font-size="{fs}" fill="{c["ink3"]}" text-anchor="end">{lv}</text>')
        pts = [f"{X(i):.1f},{RY(x['rsi']):.1f}" for i, x in enumerate(b) if x["rsi"] is not None]
        if len(pts) >= 2:
            g.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{mc["rsi"]}" stroke-width="3" stroke-linejoin="round"/>')
    g.append("</svg>")
    return "".join(g)


def svg_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


# ============================================================================ 版型
CAT_COL = {"light": dict(ss.TH.CATEGORY),
           "dark": {"新聞": "#3ee0ff", "事件": "#ffb454", "科技": "#b49bff", "總經": "#7ddc8f"}}


def _e(t) -> str:
    return ss._esc(str(t))


def page_css(mode: str, theme: str) -> str:
    c = ss.FRAME[theme]
    story = mode == "story"
    H = 1920 if story else 1350

    def S(a, b):
        return b if story else a
    mc = MA_COL[theme]
    cats = "".join(f".cat-{k}{{--c:{v}}}" for k, v in CAT_COL[theme].items())
    tg_ink = "#fff" if theme == "light" else "#070b16"
    return (ss.TH.base_css(mode).replace("body{width:1080px;", f"html,body{{height:{H}px;overflow:hidden}}\nbody{{width:1080px;height:{H}px;", 1)
            + ":root{" + "".join(f"--{k}:{v};" for k, v in mc.items()) + "}" + cats + f"""
body{{font-variant-numeric:tabular-nums}}
.card{{flex:1;min-height:0;display:flex;flex-direction:column;gap:{S(10, 14)}px;padding:{S('14px 18px', '18px 20px')}}}
.rise{{color:var(--rise)}}.fall{{color:var(--fall)}}.ink3{{color:var(--ink3)}}
.row{{flex:1;min-height:0;display:grid;grid-template-columns:{S('290px 1fr 380px', '1fr 1fr')};grid-template-rows:{S('1fr', 'auto 1fr')};align-items:center;column-gap:16px;
  border:1.5px solid var(--line);border-radius:10px;padding:{S('8px 16px', '12px 20px')};background:var(--panel2)}}
.row .nm{{font-size:{S(34, 42)}px;font-weight:800;line-height:1.5;white-space:nowrap}}
.row .px{{font-size:{S(30, 38)}px;line-height:1.5;color:var(--ink2);white-space:nowrap}}
.row .pct{{font-size:{S(46, 56)}px;font-weight:800;line-height:1.4;white-space:nowrap;text-align:right}}
.row .pts{{font-size:{S(28, 34)}px;line-height:1.5;white-space:nowrap;text-align:right}}
.row .sp{{align-self:stretch;min-height:0;position:relative;{S('', 'grid-column:1 / span 2;margin-top:8px;')}}}
.grid{{flex:none;display:grid;gap:{S(12, 14)}px}}
.tile{{min-width:0;border:1.5px solid var(--line);border-radius:10px;background:var(--panel2);padding:{S('10px 18px', '14px 20px')}}}
.tile .k{{font-size:{S(26, 32)}px;line-height:1.5;color:var(--ink3);white-space:nowrap}}
.tile .v{{font-size:{S(50, 58)}px;font-weight:800;line-height:1.3;white-space:nowrap}}
.tile .d{{font-size:{S(26, 32)}px;line-height:1.5;white-space:nowrap}}
.legend{{flex:none;display:flex;flex-wrap:wrap;column-gap:{S(18, 22)}px;row-gap:2px;font-size:{S(23, 24)}px;line-height:1.4;color:var(--ink2);white-space:nowrap}}
.legend i{{display:inline-block;width:{S(24, 30)}px;height:5px;border-radius:3px;vertical-align:middle;margin-right:6px;background:var(--lc)}}
.sec{{flex:1;min-height:0;display:flex;flex-direction:column;gap:{S(8, 12)}px}}
.sec + .sec{{border-top:1.5px solid var(--line);padding-top:{S(10, 14)}px}}
.sec .grid .tile{{padding:{S('6px 14px', '6px 16px')}}}
.sec .tile .k{{font-size:{S(22, 25)}px}}.sec .tile .v{{font-size:{S(38, 40)}px}}.sec .tile .d{{font-size:{S(22, 25)}px}}
.sec .tile.nmt{{display:flex;align-items:center;background:none;border:none;padding-left:0}}
.sec .tile.nmt .v{{font-size:{S(34, 36)}px}}
.tat{{flex:none;display:grid;grid-template-columns:auto auto 1fr;column-gap:{S(28, 32)}px;border:1.5px solid var(--line);border-radius:10px;background:var(--panel2);padding:{S('4px 18px', '8px 20px')}}}
.tat > div{{font-size:{S(25, 27)}px;line-height:1.45;white-space:nowrap;padding:{S('2px 0', '2px 0')}}}
.tat .tk{{color:var(--ink3)}}.tat .tv{{text-align:right;font-weight:700;font-variant-numeric:tabular-nums;font-family:'Roboto Mono','DejaVu Sans Mono',monospace}}
.tat .ts{{color:var(--ink2)}}
.tat > div:nth-child(n+4){{border-top:1px dashed var(--line)}}
.chartbox{{flex:1;min-height:0;position:relative}}
.chartbox img{{position:absolute;left:0;top:0;display:block}}
.ta{{flex:none;border:1.5px solid var(--line);border-radius:10px;background:var(--panel2);padding:{S('10px 18px', '14px 20px')}}}
.ta div{{font-size:{S(30, 34)}px;line-height:1.55}}
.news{{flex:1;min-height:0;display:flex;flex-direction:column;gap:{S(12, 16)}px}}
.it{{flex:1;min-height:0;display:flex;align-items:center;gap:{S(18, 20)}px;border-radius:10px;padding:{S('8px 20px 8px 16px', '12px 22px 12px 18px')};
  background:var(--panel2);border:1.5px solid var(--line);border-left:8px solid var(--c)}}
.it .tg{{flex:none;background:var(--c);color:{tg_ink};font-size:{S(28, 34)}px;font-weight:800;line-height:1.4;border-radius:12px;padding:{S('8px 14px', '10px 16px')};white-space:nowrap}}
.it .tt{{flex:1;min-width:0;font-size:{S(44, 48)}px;line-height:1.4;font-weight:800;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:{S(3, 4)};overflow:hidden}}
.sumt{{flex:1;min-height:0;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr}}
.sumt .tile{{display:flex;flex-direction:column;justify-content:center}}
.sumt .v{{font-size:{S(84, 100)}px}}.sumt .k{{font-size:{S(34, 42)}px}}
.bigbox{{flex:none;border:1.5px solid var(--line);border-radius:10px;background:var(--panel2);padding:{S('16px 28px', '24px 32px')}}}
.big{{font-size:{S(46, 56)}px;line-height:1.6;font-weight:700}}
""")


def page_html(mode: str, theme: str, title: str, inner: str, date: str = "") -> str:
    """標題列走 social_theme（LOGO｜時段膠囊｜標題｜靠右日期），日期只在標題列。"""
    body = f'{ss.TH.header_html("premarket", _e(title), _e(date))}<div class=card>{inner}</div>'
    return f"<!doctype html><html><head><meta charset=utf-8><style>{page_css(mode, theme)}</style></head><body>{body}</body></html>"


def _tile(i: int, k: str, v: str, cls: str = "", d: str = "", dcls: str = "") -> str:
    dd = f'<div class="d {dcls}" data-box=d{i}>{d}</div>' if d else ""
    return f'<div class=tile><div class=k data-box=k{i}>{_e(k)}</div><div class="v {cls}" data-box=v{i}>{v}</div>{dd}</div>'


def ma_legend() -> str:
    """圖例：中文均線名稱＋RSI(14)；一張圖只放一次（兩段共用同一套顏色）。"""
    items = "".join(f'<span data-box=lg{p}><i style="--lc:var(--ma{p})"></i>{name}</span>' for p, name in MAS)
    return f'<div class=legend>{items}<span data-box=lgrsi><i style="--lc:var(--rsi)"></i>RSI(14)</span></div>'


def _ksec(key: str, name: str, tiles: list[str], ks: dict, story: bool, theme: str) -> tuple[str, dict, list]:
    """一段日 K：名稱＋數字卡一列 → 圖（K 棒＋六條均線＋RSI 副圖）→ 技術面表格（項目｜數值｜狀態）。"""
    rows = ta_rows(ks)
    tat = ('<div class=tat>' + "".join(f'<div class=tk data-box={key}-tk{i}>{_e(a)}</div><div class=tv data-box={key}-tv{i}>{_e(b)}</div>'
                                       f'<div class=ts data-box={key}-ts{i}>{_e(c)}</div>' for i, (a, b, c) in enumerate(rows)) + '</div>') if rows else ""
    nm = f'<div class="tile nmt"><div class=v data-box={key}-nm>{_e(name)}</div></div>'
    cols = "auto " + " ".join(["1fr"] * len(tiles))
    grid = f'<div class=grid style="grid-template-columns:{cols}">{nm}{"".join(tiles)}</div>'

    def draw(w, h, c):
        return candle_svg(ks, w, h, c, theme, fs=26 if story else 21, ma=True, rsi=True)
    html = f'<div class=sec>{grid}<div class=chartbox data-box={key}-chart data-chart={key}></div>{tat}</div>'
    return html, {key: draw}, rows


def build_pages(D: dict, mode: str, theme: str = "light") -> list[dict]:
    """每張回 {name, title, inner, charts:{key: 畫圖函式(w,h,c)}}。圖上不放任何備註（資料日只在標題列）。"""
    story = mode == "story"
    head = ""   # 日期與「盤前」改放標題列的日期／膠囊（render 傳 date），標題只留頁名
    us, adr, tx, night = D["us"], D["adr"], D["tx"], D["night"]
    night_ok = not night["missing"] and night.get("diff") is not None and not night.get("partial")
    pages = []

    # 1 美股：有資料的才畫（缺的整列不畫）；VIX 用折線，其他用日 K
    rows, charts = [], {}
    for r in us["rows"]:
        if r["missing"]:
            continue
        tn = tone(r["chg"]) if r["sym"] != "^VIX" else "ink3"
        key = "k" + re.sub(r"\W", "", r["sym"])
        rows.append(f'<div class=row><div><div class=nm data-box=nm-{key}>{_e(r["label"])}</div>'
                    f'<div class=px data-box=px-{key}>{fmt_num(r["close"])}</div></div>'
                    f'<div><div class="pct {tn}" data-box=pct-{key}>{fmt_signed(r["pct"], 2, "%")}</div>'
                    f'<div class="pts {tn}" data-box=pts-{key}>{fmt_signed(r["chg"])} 點</div></div>'
                    f'<div class=sp><div class=chartbox data-box={key} data-chart={key} style="position:absolute;inset:0"></div></div></div>')
        if r["sym"] == "^VIX":
            charts[key] = (lambda vals: (lambda w, h, c: line_svg(vals, w, h, c["cyan"])))([b["c"] for b in r["k"]["bars"]])
        else:
            charts[key] = (lambda ks: (lambda w, h, c: candle_svg(ks, w, h, c, theme)))(r["k"])
    if rows:
        pages.append({"name": "us-close", "title": "美股", "inner": "".join(rows), "charts": charts})

    # 2 台指期（上）＋台積電 ADR（下）同一頁；ADR 沒進資料庫 → 下段不畫（Andy 10-26：台積電現貨那頁改回 ADR）
    secs, charts, ta = [], {}, {}
    if not tx["missing"]:
        tiles = [_tile(1, "日盤收盤", fmt_num(tx["close"], 0), "", f'{fmt_signed(tx["chg"], 0)} 點（{fmt_signed(tx["pct"], 2, "%")}）', tone(tx["chg"]))]
        if night_ok:
            tiles.append(_tile(2, "夜盤收盤", fmt_num(night["close"], 0), "",
                               f'較日盤 {fmt_signed(night["diff"], 0)} 點（{fmt_signed(night["diff_pct"], 2, "%")}）', tone(night["diff"])))
        h, ch, rows = _ksec("ktx", "台指期", tiles, tx["k"], story, theme)
        secs.append(h); charts.update(ch); ta["tx"] = rows
    if not adr["missing"]:
        tiles = [_tile(3, "ADR（美元）", fmt_num(adr["close"]), "", fmt_signed(adr["pct"], 2, "%"), tone(adr["chg"]))]
        if adr.get("conv"):
            tiles.append(_tile(4, "換算台股價", fmt_num(adr["conv"], 1)))
        if adr.get("prem") is not None:
            tiles.append(_tile(5, "溢價" if adr["prem"] >= 0 else "折價", fmt_signed(adr["prem"], 2, "%"), tone(adr["prem"])))
        h, ch, rows = _ksec("kadr", "台積電 ADR", tiles, adr["k"], story, theme)
        secs.append(h); charts.update(ch); ta["adr"] = rows
    if secs:
        sub = "台指期・台積電 ADR" if len(secs) == 2 else ("台指期" if not tx["missing"] else "台積電 ADR")
        pages.append({"name": "tx", "title": sub, "inner": ma_legend() + "".join(secs), "charts": charts, "ta": ta})

    # 4 今日焦點：分類色塊＋大標題，無來源無時間
    if D["news"]:
        items = "".join(f'<div class="it cat-{n["category"]}"><div class=tg data-box=tg{i}>{n["category"]}</div>'
                        f'<div class=tt data-box=tt{i}>{_e(n["title"])}</div></div>' for i, n in enumerate(D["news"]))
        pages.append({"name": "news", "title": "今日焦點", "inner": f'<div class=news>{items}</div>', "charts": {}})

    # 5 一句話總結：四格數字＋一句話（缺的格子換成可得的：標普、VIX）
    tiles = []
    for r in us["rows"]:
        if r["sym"] in ("^IXIC", "^SOX") and not r["missing"]:
            tiles.append((r["label"].replace("費城半導體", "費半"), fmt_signed(r["pct"], 2, "%"), tone(r["pct"])))
    if night_ok:
        tiles.append(("夜盤較日盤", fmt_signed(night["diff"], 0) + " 點", tone(night["diff"])))
    if not adr["missing"]:
        tiles.append(("台積電 ADR", fmt_signed(adr["pct"], 2, "%"), tone(adr["pct"])))
    for r in us["rows"]:
        if len(tiles) >= 4:
            break
        if not r["missing"] and r["sym"] in ("^GSPC", "^VIX"):
            tiles.append((r["label"].replace("VIX 波動率", "VIX"), fmt_num(r["close"]) if r["sym"] == "^VIX" else fmt_signed(r["pct"], 2, "%"),
                          "ink3" if r["sym"] == "^VIX" else tone(r["pct"])))
    th = "".join(f'<div class=tile><div class=k data-box=sk{i}>{_e(k)}</div><div class="v {t}" data-box=sv{i}>{_e(v)}</div></div>'
                 for i, (k, v, t) in enumerate(tiles[:4]))
    if th:
        big = f'<div class=bigbox><div class=big data-box=sum>{_e(D["summary"])}</div></div>' if D["summary"] else ""
        pages.append({"name": "summary", "title": "一句話總結", "inner": f'<div class="grid sumt">{th}</div>{big}', "charts": {}})
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
  return { hits, out, cut: R.filter(r => r.cut).map(r => r.n), n: R.length, content_ratio: (card.bottom - document.querySelector('.hd').getBoundingClientRect().top) / H };
}"""


def render(pages: list[dict], mode: str, theme: str, out: Path, browser, report: list) -> list[str]:
    files = []
    H = 1920 if mode == "story" else 1350
    c = ss.FRAME[theme]
    for p in pages:
        pg = browser.new_page(viewport={"width": 1080, "height": H}, device_scale_factor=1)
        pg.set_content(page_html(mode, theme, p["title"], p["inner"], DATE_TXT), wait_until="load")
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


# ============================================================================ 文案與 premarket_news
def premarket_news(D: dict) -> dict:
    """給網站「每日精選 → 盤前消息」讀的結構（格式見 docs/marketing/social_unit/premarket_news_format.md）。"""
    return {"version": 1, "target_date": D["target"], "window": {"start": D["news_window"][0], "end": D["news_window"][1]},
            "categories": CAT_ORDER,
            "items": [{"category": n["category"], "title": n["title"], "url": n["url"], "source": n["source"],
                       "published_at": n["published_at"], "coverage": n.get("coverage", {})} for n in D["news"]]}


def caption(D: dict, ymd: str, max_len: int = ss.THREADS_MAX) -> str:
    """第 1 行標題；美股／台指期／台積電各一行；完整消息標題清單；網址；免責；hashtag；最後一行留言關鍵字。超長先縮數字行。"""
    tgt = pd.Timestamp(D["target"]).date()
    us, adr, tx, night = D["us"], D["adr"], D["tx"], D["night"]
    num = []
    if us["date"]:
        xs = [f"{r['label'].replace('費城半導體', '費半').replace('道瓊工業', '道瓊').replace('VIX 波動率', 'VIX')} "
              + (fmt_num(r["close"]) if r["sym"] == "^VIX" else fmt_signed(r["pct"], 2, "%")) for r in us["rows"] if not r["missing"]]
        num.append(f"美股 {md(us['date'])}：" + "、".join(xs))
    if not tx["missing"]:
        s = f"台指期 {md(tx['date'])} 收 {fmt_num(tx['close'], 0)}（{fmt_signed(tx['chg'], 0)}）"
        if not night["missing"] and night.get("diff") is not None and not night.get("partial"):
            s += f"，夜盤 {fmt_num(night['close'], 0)}（較日盤 {fmt_signed(night['diff'], 0)}）"
        num.append(s)
    if not adr["missing"]:
        s = f"台積電 ADR {fmt_num(adr['close'])} 美元（{fmt_signed(adr['pct'], 2, '%')}）"
        if adr.get("prem") is not None:
            s += f"，換算{'溢價' if adr['prem'] >= 0 else '折價'} {abs(adr['prem']):.2f}%"
        num.append(s)
    elif adr.get("tw_close"):
        num.append(f"台積電 {md(adr['tw_date'])} 收 {fmt_num(adr['tw_close'], 0)}（{fmt_signed(adr.get('tw_pct', 0), 2, '%')}）")
    if D.get("closure"):
        num.append(D["closure"]["text"])
    news = [f"【{n['category']}】{n['title']}" for n in D["news"]]
    tail = [f"看更多 {ss.deep_link('overview', KIND, ymd)}", DISCLAIMER, HASHTAGS, ASK_LINE]
    txt = ""
    for keep_num, keep_news, keep_disc in ((len(num), len(news), True), (3, len(news), True), (2, len(news), True), (1, len(news), True),
                                           (1, len(news), False), (0, len(news), False), (0, 4, False), (0, 3, False)):
        t = tail if keep_disc else [x for x in tail if x != DISCLAIMER]
        txt = "\n".join([f"台股盤前｜{md(tgt)}"] + num[:keep_num] + news[:keep_news] + t)
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
            done = json.loads(Path(args.posted_json).read_text("utf-8"))
        except Exception as exc:  # noqa: BLE001 —— 沒有紀錄檔＝還沒發過
            print(f"[premarket] 讀不到發布紀錄（{exc}），當作還沒發過")
            done = {}
        if key in done:
            print(f"[premarket] {key} 已發過 → 不重複")
            return 10

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
    (out / "data.json").write_text(json.dumps(D, ensure_ascii=False, indent=1, default=str), "utf-8")
    global DATE_TXT
    _t = pd.Timestamp(D['target']).date()
    DATE_TXT = f"{md(_t)} 週{WEEK[_t.weekday()]}"
    pn = premarket_news(D)
    (out / "premarket_news.json").write_text(json.dumps(pn, ensure_ascii=False, indent=1), "utf-8")
    from playwright.sync_api import sync_playwright
    report: list = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=ss.CHROMIUM) if ss.CHROMIUM else p.chromium.launch()
        threads = render(build_pages(D, "threads", args.frame), "threads", args.frame, out, browser, report)
        stories = render(build_pages(D, "story", args.frame), "story", args.frame, out, browser, report)
        browser.close()
    (out / "layout_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    bad = [r for r in report if r["hits"] or r["out"] or r["cut"]]
    print(f"[premarket] 重疊檢查：程式 {len(report)} 張、{sum(r['n'] for r in report)} 個框、{len(bad)} 筆問題")
    for r in report:
        print(f"  {r['file']}: 框 {r['n']}、填滿 {r['content_ratio']:.0%}" + (f"  ✗ {r['hits']} {r['out']} {r['cut']}" if r in bad else ""))
    if bad:
        return 3
    text = caption(D, target.strftime("%Y%m%d"))
    manifest = {"kind": KIND, "taken_at": now.isoformat(timespec="seconds"), "data_date": target.isoformat(), "slot_key": key,
                "threads": {"text": text, "images": threads}, "story": stories, "premarket_news": pn}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    (out / "caption.txt").write_text(text + "\n", "utf-8")
    print(f"[premarket] manifest：{out / 'manifest.json'}；文案 {len(text)} 字；消息 {len(pn['items'])} 則")
    return 0


if __name__ == "__main__":
    sys.exit(main())
