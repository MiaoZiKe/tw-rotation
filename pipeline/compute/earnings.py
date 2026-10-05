"""財報日曆（#earnings，site/earnings.js）—— Andy 2026-10-05 16:00：
「總覽下方新增"財報日曆"……向行事曆那樣標示出台股大公司的開財報日期，以及 FED 公布重大數據也需要標示出來，
並且需要在旁邊有點及該個股後，出現對於這次財報的分析及展望（包含 FED 消息）」。

產出 site/data/earnings.json（build_payload 呼叫 build()）；本機也可以
`python -m pipeline.compute.earnings <輸出路徑>` 只產這一檔（預覽分支的種子檔 site/earnings_seed.json 就是這樣做的）。

口徑（每一條都寫在畫面上，不要只寫在這裡）
------------------------------------------
大公司：市值前 50（收盤 × 最新一季資產負債表的股數，上市＋上櫃，只算 4 碼普通股，排除 ETF）。
  沒有 0050／0051 成分股的資料源（資料湖沒有這張表），所以用市值排名；股數是季底的，季底後的增資配股沒反映。

公司事件 —— 只有兩種來源，畫面上分開標：
  ① **已公告**：公開資訊觀測站重大訊息（證交所 OpenAPI t187ap04，資料湖 material_news，2026-09-19 起才有）。
     主旨含「法人說明會／法說會」＝法說會（公司自己辦的標「法說會」、受邀參加券商論壇的標「受邀法說」）；
     主旨含「財務報告／財報」＋「董事會」＋「預計／召開日期」＝財報董事會日期；「董事會通過…財務報告」＝已公布。
     日期：主旨裡寫了「115年10月15日」就用它，否則用「事實發生日」。主旨有「更正／取消／延期」的不採用（不猜改到哪天）。
  ② **預估**：這一季還沒有任何公告的公司，標在「預估日」並寫「預估」——
     有過去幾季實際公布日（同一張重大訊息表）就用「平均早於法定期限幾天」推，沒有就直接標法定期限
     （Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31，DECISIONS #14）。財報資料湖的 announce_date 本身就是法定期限、
     不是實際公布日，所以不能拿來當「過去實際公布日」。

FED 與美國重大數據：FOMC（決議＋紀要）來自 pipeline/calendar/macro_events.yaml；CPI／非農／GDP／PCE 公布日
  以 FRED fred/release/dates（資料湖 macro_calendar）為準，抓不到才用 YAML 的退回日程（畫面標出處）。
  「上次數值」只用 FRED 觀測值（資料湖 macro）；沒有就寫「FRED 資料尚未取得」，不拿別的地方的數字湊。

分析與展望：**全部是規則＋資料湖數字組出來的句子，沒有任何語言模型**（同一份資料永遠產出同一段文字）。
  文字一律描述式（「目前…」「較去年同期…」），不寫買賣建議（證券投資信託及顧問法）。
  每段附出處與資料日期；頁面另有「純資料整理，不構成投資建議」。
"""
from __future__ import annotations

import logging
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .. import config

log = logging.getLogger(__name__)

UNIVERSE_N = 50
WINDOW_BACK = 75        # 日曆往回帶幾天的事件（看得到上個月）
WINDOW_AHEAD = 150      # 往後帶幾天（看得到下一季的法定期限）
NEWS_DAYS = 30
NEWS_N = 5
MOPS_N = 3
YAML_PATH = config.ROOT / "pipeline" / "calendar" / "macro_events.yaml"

ROC_DATE = re.compile(r"(1\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
QTR_WORD = {"一": 1, "二": 2, "三": 3, "四": 4, "1": 1, "2": 2, "3": 3, "4": 4}
QTR_RE = re.compile(r"(1\d{2})\s*年(?:度)?\s*第\s*([一二三四1-4])\s*季")
CONF_RE = re.compile(r"法人說明會|法說|投資人說明會")
INVITE_RE = re.compile(r"受邀|邀請|參加|參與")
BOARD_RE = re.compile(r"財務報告|財報")
SKIP_RE = re.compile(r"更正|取消|延期|延後|補充公告|重編")

# 台股慣例：Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31（config.FINANCIAL_DEADLINES，DECISIONS #14）
def deadline(year: int, q: int) -> str:
    mm, dd = config.FINANCIAL_DEADLINES[q]
    return f"{year + 1 if q == 4 else year}-{mm}-{dd}"


def quarter_end(year: int, q: int) -> str:
    return {1: f"{year}-03-31", 2: f"{year}-06-30", 3: f"{year}-09-30", 4: f"{year}-12-31"}[q]


def quarter_of_deadline(d: str) -> tuple[int, int] | None:
    """法定期限日 → 是哪一季的期限（2026-11-14 → (2026, 3)）。"""
    y = int(d[:4])
    for q in (1, 2, 3):
        if deadline(y, q) == d:
            return y, q
    if deadline(y - 1, 4) == d:
        return y - 1, 4
    return None


def quarter_for(day: str) -> tuple[int, int]:
    """某一天之後「下一個要公布的季報」：落在 (上一季季底, 這一季期限] 之間的那一季。"""
    d = pd.Timestamp(day)
    for y in (d.year - 1, d.year):
        for q in (1, 2, 3, 4):
            if pd.Timestamp(quarter_end(y, q)) < d <= pd.Timestamp(deadline(y, q)):
                return y, q
    # 落在期限之後、下一季季底之前（例如 11/20）→ 下一季
    y, q = d.year, (d.month - 1) // 3 + 1
    return (y, q)


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _r(x, nd=1):
    v = _f(x)
    return None if v is None else round(v, nd)


def _pct(v, nd=1):
    v = _f(v)
    return "—" if v is None else f"{v:+.{nd}f}%"


def _yi(v):
    """元 → 億元（一位小數）；千位加逗號。"""
    v = _f(v)
    return "—" if v is None else f"{v / 1e8:,.1f} 億元"


def _zhang(v):
    """股 → 張（四捨五入到整數，加逗號）。"""
    v = _f(v)
    return "—" if v is None else f"{v / 1000:+,.0f} 張"


def roc_date(text: str) -> str | None:
    m = ROC_DATE.search(text or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


def subject_quarter(text: str) -> str | None:
    m = QTR_RE.search(text or "")
    return f"{int(m.group(1)) + 1911}Q{QTR_WORD[m.group(2)]}" if m else None


# ------------------------------------------------------------------ 大公司名單
def universe(val: pd.DataFrame, names: dict, n: int = UNIVERSE_N) -> list[dict]:
    """市值前 n 的普通股。val＝fundamental.valuation() 的輸出（code, close, market_cap）。"""
    if val is None or val.empty or "market_cap" not in val.columns:
        return []
    v = val[["code", "close", "market_cap"]].copy()
    v["code"] = v["code"].astype(str)
    v = v[v["code"].str.fullmatch(r"[1-9]\d{3}")]
    v["market_cap"] = pd.to_numeric(v["market_cap"], errors="coerce")
    v = v.dropna(subset=["market_cap"]).sort_values("market_cap", ascending=False).head(n)
    return [{"code": c, "name": names.get(c) or c, "rank": i + 1, "mcap": _r(m / 1e8, 0), "close": _r(px, 2)}
            for i, (c, m, px) in enumerate(zip(v["code"], v["market_cap"], v["close"]))]


# ------------------------------------------------------------------ 公司事件（重大訊息）
def conf_detail(detail: str) -> dict:
    """重大訊息第 12 款（召開法人說明會）的內文有固定欄位：日期／時間／地點／擇要訊息。
    只抽公司自己寫的字，抽不到就留空 —— 不補、不猜（Andy：法說會不做推估）。"""
    t = str(detail or "")
    def f(lab):
        m = re.search(lab + r"[^：:\n]*[：:]\s*([^\r\n]+)", t)
        return re.sub(r"\s+", " ", m.group(1)).strip()[:60] if m else ""
    out = {}
    ds = f("召開法人說明會之日期")
    d = roc_date(ds)
    m = None if d else re.search(r"(1\d{2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{1,2})", ds)
    if m:                                  # 內文多半寫 115/09/30（民國／斜線）
        try:
            d = date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            d = None
    if d:
        out["d"] = d
    tm = f("召開法人說明會之時間")
    m = re.search(r"(\d{1,2})\s*[時:：]\s*(\d{1,2})?", tm)
    if m:
        out["time"] = f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"
    for k, lab in (("place", "召開法人說明會之地點"), ("brief", "法人說明會擇要訊息")):
        v = f(lab)
        if v:
            out[k] = v
    return out


def mops_events(material_news: pd.DataFrame | None, codes: set[str], conf_all: bool = False) -> list[dict]:
    """從重大訊息挑出法說會／財報董事會／已公布財報。
    財報類只看名單內的公司；conf_all=True 時法說會收全部上市櫃公司（Andy 1005：「行事曆幫我多新增公司法說會」）。"""
    if material_news is None or material_news.empty:
        return []
    out = []
    cs = material_news["code"].astype(str)
    m = material_news[cs.isin(codes) | (conf_all & material_news["subject"].astype(str).str.contains(CONF_RE.pattern, regex=True, na=False))]
    for _, r in m.iterrows():
        subj = re.sub(r"\s+", "", str(r.get("subject") or ""))
        if not subj or SKIP_RE.search(subj):
            continue
        kind = None
        if CONF_RE.search(subj):
            kind = "invite" if INVITE_RE.search(subj) else "conf"
        elif BOARD_RE.search(subj) and "董事會" in subj:
            if re.search(r"預計|召開日期|日期", subj):
                kind = "board"
            elif re.search(r"通過|決議|承認", subj):
                kind = "report"
        if not kind:
            continue
        ann = str(r.get("date") or "")[:10]
        d = roc_date(subj) or str(r.get("occurred") or "")[:10] or ann
        if kind not in ("conf", "invite") and str(r["code"]) not in codes:
            continue
        extra = conf_detail(r.get("detail")) if kind in ("conf", "invite") else {}
        if extra.get("d"):
            d = extra.pop("d")            # 內文寫的召開日期比主旨／事實發生日準
        if kind == "report":
            d = ann                       # 「董事會通過財報」的公布日就是公告那天
        if len(d) != 10:
            continue
        ev = {"d": d, "k": kind, "code": str(r["code"]), "title": subj[:80], "status": "公告",
              "q": subject_quarter(subj), "ann": ann,
              "src": "公開資訊觀測站重大訊息（證交所）"}
        if r.get("name"):
            ev["name"] = str(r["name"])
        ev.update(extra)
        out.append(ev)
    out.sort(key=lambda e: (e["d"], e["code"], e["k"]))
    # 同一家同一天同一類只留一筆（同一場法說常發兩則：公告＋補充資料）
    seen, uniq = set(), []
    for e in out:
        key = (e["d"], e["code"], e["k"])
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq


def estimate_events(univ: list[dict], announced: list[dict], asof: str, end: str) -> list[dict]:
    """這一季（以及窗內下一季）還沒有任何公告的公司 → 預估日。

    預估規則：同一家公司過去「已公布（report）」或「自辦法說（conf）」的日期，各自換算成「早於當季法定期限幾天」，
    取中位數，從這一季的期限往前推；沒有任何紀錄 → 直接標法定期限（basis 寫明）。"""
    out = []
    y, q = quarter_for(asof)
    targets = []
    while True:
        dl = deadline(y, q)
        if dl > end:
            break
        if dl >= asof:
            targets.append((y, q, dl))
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    by_code: dict[str, list[dict]] = {}
    for e in announced:
        by_code.setdefault(e["code"], []).append(e)
    for y, q, dl in targets:
        qe = quarter_end(y, q)
        for u in univ:
            evs = by_code.get(u["code"], [])
            if any(e["k"] in ("conf", "board", "report") and qe < e["d"] <= dl for e in evs):
                continue           # 這一季已經有公告的日子，不再放預估
            offs = []
            for e in evs:
                if e["k"] not in ("conf", "report"):
                    continue
                pq = quarter_for(e["d"])
                pdl = deadline(*pq)
                if pdl != dl and pd.Timestamp(e["d"]) <= pd.Timestamp(pdl):
                    offs.append((pd.Timestamp(pdl) - pd.Timestamp(e["d"])).days)
            if offs:
                off = int(pd.Series(offs).median())
                d = (pd.Timestamp(dl) - pd.Timedelta(days=off)).strftime("%Y-%m-%d")
                basis = f"依過去 {len(offs)} 次實際公布日（中位數早於法定期限 {off} 天）推估"
            else:
                d = dl
                basis = "還沒有這家公司過去實際公布日的紀錄（重大訊息自 2026-09-19 起才進資料湖），先標法定期限"
            out.append({"d": d, "k": "est", "code": u["code"], "status": "預估", "q": f"{y}Q{q}",
                        "title": f"{y} 年第 {q} 季財報（預估，法定期限 {dl[5:].replace('-', '/')}）",
                        "basis": basis, "deadline": dl,
                        "src": "法定申報期限（證券交易法第 36 條）"})
    return out


def market_events(start: str, end: str) -> list[dict]:
    """台股全市場的固定期限：月營收（每月 10 日前公告上月）與季報法定期限。"""
    out = []
    d = pd.Timestamp(start).replace(day=1)
    while d <= pd.Timestamp(end):
        k = d.replace(day=config.REVENUE_DEADLINE_DAY).strftime("%Y-%m-%d")
        prev = (d - pd.Timedelta(days=1)).month
        if start <= k <= end:
            out.append({"d": k, "k": "rev", "status": "期限", "title": f"{prev} 月營收公布期限",
                        "note": "上市櫃公司須在每月 10 日前公告上個月營收（多數大公司更早）",
                        "src": "法定申報期限（證券交易法第 36 條）"})
        d = (d + pd.Timedelta(days=32)).replace(day=1)
    for y in range(int(start[:4]) - 1, int(end[:4]) + 1):
        for q in (1, 2, 3, 4):
            dl = deadline(y, q)
            if start <= dl <= end:
                out.append({"d": dl, "k": "qdl", "status": "期限", "title": f"{y} Q{q} 財報法定期限",
                            "note": "一般上市櫃公司季報（Q4 為年報）最晚公告日", "src": "法定申報期限"})
    return out


# ------------------------------------------------------------------ FED 與美國數據
FED_INFO = {
    "fomc": {"name": "FOMC 利率決議", "short": "FOMC", "org": "聯準會（Federal Reserve）", "et": "14:00",
             "desc": "聯邦公開市場委員會一年開 8 次會，第二天美東 14:00 公布利率決議、14:30 主席記者會；標「附點陣圖」的那 4 次另有經濟預測摘要（SEP）。",
             "focus": ["政策利率區間有沒有調整、幅度多少", "聲明對通膨與就業的措辭有沒有改變", "附點陣圖的會議：委員預期的利率路徑（還要降／升幾次）"],
             "rel": ["policy", "cpi_yoy", "core_pce_yoy", "unrate"]},
    "minutes": {"name": "FOMC 會議紀要", "short": "紀要", "org": "聯準會（Federal Reserve）", "et": "14:00",
                "desc": "上一次利率會議的完整討論紀錄，在會後三週公布。決議本身早就知道了，紀要看的是委員之間的分歧。",
                "focus": ["有多少委員主張更快／更慢調整利率", "對通膨風險與就業降溫的看法", "有沒有提到資產負債表（縮表）的調整"],
                "rel": ["policy"]},
    "cpi": {"name": "美國 CPI 消費者物價", "short": "CPI", "org": "美國勞工統計局（BLS）", "et": "08:30",
            "desc": "每月公布上個月的消費者物價指數。聯準會的通膨目標是 2%（以 PCE 衡量），CPI 比 PCE 早兩週公布，是市場最先看到的通膨數字。",
            "focus": ["整體 CPI 年增率是否往 2% 回落", "核心 CPI（排除食品與能源）的年增與月增", "數字高於預期 → 降息預期降溫；低於預期 → 降息預期升溫"],
            "rel": ["cpi_yoy", "core_cpi_yoy"]},
    "nfp": {"name": "美國非農就業", "short": "非農", "org": "美國勞工統計局（BLS）", "et": "08:30",
            "desc": "每月第一個週五公布上個月的就業報告（Employment Situation）：非農新增就業人數、失業率、平均時薪。就業是聯準會雙重目標的另一半。",
            "focus": ["新增就業人數比前幾個月多或少", "失業率有沒有上升（就業降溫）", "平均時薪年增（薪資通膨）"],
            "rel": ["nfp_change", "unrate"]},
    "pce": {"name": "美國 PCE 物價", "short": "PCE", "org": "美國經濟分析局（BEA）", "et": "08:30",
            "desc": "個人所得與支出報告裡的 PCE 物價指數，是聯準會 2% 通膨目標**正式採用**的指標；核心 PCE 排除食品與能源。",
            "focus": ["核心 PCE 年增率離 2% 還有多遠", "跟兩週前公布的 CPI 方向是否一致", "個人消費支出的成長（需求強弱）"],
            "rel": ["pce_yoy", "core_pce_yoy"]},
    "gdp": {"name": "美國 GDP", "short": "GDP", "org": "美國經濟分析局（BEA）", "et": "08:30",
            "desc": "每季的國內生產毛額，同一季會公布三次（初值、第二次、第三次估計）；數字是「季增年率」。",
            "focus": ["實質 GDP 季增年率比上一季高或低", "個人消費與企業投資的貢獻", "跟市場對景氣放緩的預期是否一致"],
            "rel": ["gdp"]},
}


def _et_offset(d: str) -> int:
    """美東時間 → 台灣時間要加幾小時：夏令（3 月第二個週日～11 月第一個週日）+12，其餘 +13。"""
    t = pd.Timestamp(d)
    y = t.year
    mar = pd.Timestamp(f"{y}-03-01")
    dst_start = mar + pd.Timedelta(days=(6 - mar.weekday()) % 7 + 7)
    nov = pd.Timestamp(f"{y}-11-01")
    dst_end = nov + pd.Timedelta(days=(6 - nov.weekday()) % 7)
    return 12 if dst_start <= t < dst_end else 13


def tw_time(d: str, et: str) -> str:
    """'2026-10-14', '08:30' → '10/14 20:30'；跨日（FOMC 14:00）→ '10/29 02:00'。"""
    hh, mm = (int(x) for x in et.split(":"))
    t = pd.Timestamp(d) + pd.Timedelta(hours=hh + _et_offset(d), minutes=mm)
    return t.strftime("%m/%d %H:%M")


def load_macro_yaml(path: Path = YAML_PATH) -> dict:
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        log.warning("讀不到 %s：%s", path, exc)
        return {}


def macro_events(cfg: dict, cal: pd.DataFrame | None, start: str, end: str) -> list[dict]:
    """FOMC（YAML）＋ CPI／非農／GDP／PCE（FRED 優先，YAML 退回）。"""
    out = []
    fomc = (cfg or {}).get("fomc") or {}
    src_f = f"聯準會會議日程（{fomc.get('source', '')}；查證 {cfg.get('verified', '')}）"
    for m in fomc.get("meetings") or []:
        e, mn = str(m.get("end")), str(m.get("minutes") or "")
        if start <= e <= end:
            out.append({"d": e, "k": "fomc", "status": "排程", "title": "FOMC 利率決議" + ("（附點陣圖）" if m.get("sep") else ""),
                        "meet": f"{str(m.get('start'))[5:].replace('-', '/')}–{e[5:].replace('-', '/')}", "sep": bool(m.get("sep")),
                        "tw": tw_time(e, "14:00"), "src": src_f})
        if mn and start <= mn <= end:
            out.append({"d": mn, "k": "minutes", "status": "排程", "title": f"FOMC 會議紀要（{e[5:].replace('-', '/')} 會議）",
                        "tw": tw_time(mn, "14:00"), "src": src_f})
    # FRED：只採用「最近一次抓取」裡出現的日期（舊抓取的列若被改期，不會留下幽靈日期）
    fred_keys: set[str] = set()
    if cal is not None and not cal.empty and {"date", "release"} <= set(cal.columns):
        c = cal.copy()
        c["date"] = c["date"].astype(str).str[:10]
        if "fetched" in c.columns:
            last = c.groupby("release")["fetched"].transform("max")
            c = c[c["fetched"] == last]
        for _, r in c.iterrows():
            k, d = str(r["release"]), r["date"]
            if k in FED_INFO and start <= d <= end:
                fred_keys.add(k)
                out.append({"d": d, "k": k, "status": "排程", "title": FED_INFO[k]["name"], "tw": tw_time(d, FED_INFO[k]["et"]),
                            "src": f"FRED 公布日程（fred/release/dates，release_id {int(r.get('release_id') or 0)}；抓取 {r.get('fetched', '')}）"})
    for k, spec in ((cfg or {}).get("releases") or {}).items():
        if k in fred_keys or k not in FED_INFO:
            continue
        for x in spec.get("dates") or []:
            d = str(x.get("date"))
            if start <= d <= end:
                out.append({"d": d, "k": k, "status": "排程", "title": FED_INFO[k]["name"], "ref": x.get("ref"),
                            "tw": tw_time(d, FED_INFO[k]["et"]),
                            "src": f"官方公布日程（{spec.get('source', '')}；FRED 日程未取得時的退回值，查證 {cfg.get('verified', '')}）"})
    return out


def _series(macro: pd.DataFrame, sid: str) -> pd.Series:
    if macro is None or macro.empty:
        return pd.Series(dtype=float)
    s = macro[macro["series"] == sid]
    if s.empty:
        return pd.Series(dtype=float)
    s = s.assign(date=s["date"].astype(str).str[:10]).drop_duplicates("date", keep="last").sort_values("date")
    return pd.Series(pd.to_numeric(s["value"], errors="coerce").to_numpy(), index=s["date"].to_numpy()).dropna()


def _yoy_pair(s: pd.Series) -> tuple:
    """月資料的年增率：(最新期, 年增, 前一期, 前一期年增)。index 是 YYYY-MM-DD（月初）。"""
    if len(s) < 14:
        return None, None, None, None
    def yoy(i):
        cur, d = s.iloc[i], s.index[i]
        base_d = f"{int(d[:4]) - 1}{d[4:]}"
        b = s.get(base_d)
        return None if b is None or not b else round((cur / b - 1) * 100, 1)
    return s.index[-1][:7], yoy(-1), s.index[-2][:7], yoy(-2)


def _yoy_series(s: pd.Series, n: int = 12) -> list:
    out = []
    for d in s.index[-n:]:
        b = s.get(f"{int(d[:4]) - 1}{d[4:]}")
        if b:
            out.append([d[:7], round((s[d] / b - 1) * 100, 2)])
    return out


def macro_snapshot(macro: pd.DataFrame | None) -> dict:
    """FED 面板的「上次數值」：全部來自 FRED 觀測值；缺就不給（前端寫「FRED 資料尚未取得」）。"""
    out: dict = {}
    lo, hi = _series(macro, "DFEDTARL"), _series(macro, "DFEDTARU")
    if len(lo) and len(hi):
        out["policy"] = {"label": "聯邦基金利率目標區間", "value": f"{lo.iloc[-1]:.2f}%–{hi.iloc[-1]:.2f}%", "date": hi.index[-1],
                         "prev": None, "src": "FRED DFEDTARL／DFEDTARU"}
        chg = hi[hi.diff().fillna(0) != 0]
        if len(chg):
            out["policy"]["prev"] = f"上次調整 {chg.index[-1]}（上限 {hi.loc[:chg.index[-1]].iloc[-2]:.2f}% → {chg.iloc[-1]:.2f}%）" if len(hi.loc[:chg.index[-1]]) > 1 else None
    else:
        ff = _series(macro, "FEDFUNDS")
        if len(ff):
            out["policy"] = {"label": "聯邦基金有效利率（月均）", "value": f"{ff.iloc[-1]:.2f}%", "date": ff.index[-1][:7],
                             "prev": f"前一期 {ff.iloc[-2]:.2f}%" if len(ff) > 1 else None, "src": "FRED FEDFUNDS"}
    for key, sid, lab in (("cpi_yoy", "CPIAUCSL", "CPI 年增率"), ("core_cpi_yoy", "CPILFESL", "核心 CPI 年增率"),
                          ("pce_yoy", "PCEPI", "PCE 物價年增率"), ("core_pce_yoy", "PCEPILFE", "核心 PCE 年增率")):
        p, v, pp, pv = _yoy_pair(_series(macro, sid))
        if v is not None:
            out[key] = {"label": lab, "value": f"{v:.1f}%", "date": p, "prev": f"前一期（{pp}）{pv:.1f}%" if pv is not None else None,
                        "src": f"FRED {sid}（年增率＝本期 ÷ 去年同期 − 1）", "v": v, "pv": pv, "series": _yoy_series(_series(macro, sid))}
    pay = _series(macro, "PAYEMS")
    if len(pay) >= 3:
        d1, d2 = pay.iloc[-1] - pay.iloc[-2], pay.iloc[-2] - pay.iloc[-3]
        out["nfp_change"] = {"label": "非農新增就業", "value": f"{d1:+,.0f} 千人", "date": pay.index[-1][:7],
                             "prev": f"前一期（{pay.index[-2][:7]}）{d2:+,.0f} 千人", "src": "FRED PAYEMS（本期 − 前期）",
                             "v": float(d1), "pv": float(d2), "series": [[pay.index[i][:7], float(pay.iloc[i] - pay.iloc[i - 1])] for i in range(max(1, len(pay) - 12), len(pay))]}
    for key, sid, lab, fmt in (("unrate", "UNRATE", "失業率", "{:.1f}%"), ("gdp", "A191RL1Q225SBEA", "實質 GDP 季增年率", "{:+.1f}%"),
                               ("ust10", "DGS10", "美國十年期公債殖利率", "{:.2f}%")):
        s = _series(macro, sid)
        if len(s):
            out[key] = {"label": lab, "value": fmt.format(s.iloc[-1]), "date": s.index[-1][:7] if sid != "DGS10" else s.index[-1],
                        "prev": f"前一期（{s.index[-2][:7] if sid != 'DGS10' else s.index[-2]}）{fmt.format(s.iloc[-2])}" if len(s) > 1 else None,
                        "src": f"FRED {sid}", "v": float(s.iloc[-1]), "pv": float(s.iloc[-2]) if len(s) > 1 else None,
                        "series": [[i[:7], float(v)] for i, v in s.tail(12 if sid != "DGS10" else 1).items()] if sid != "DGS10" else []}
    return out


def fed_info_merged(cfg: dict | None = None) -> dict:
    """FED_INFO（程式內建的名稱與關注點）＋ macro_events.yaml 的 info 區塊（是什麼／怎麼看／影響／星級／偏多偏空規則）。"""
    cfg = cfg if cfg is not None else load_macro_yaml()
    extra = (cfg or {}).get("info") or {}
    return {k: {**v, **(extra.get(k) or {})} for k, v in FED_INFO.items()}


# ------------------------------------------------------------------ 個股分析與展望（規則式）
def _cols(block: dict, key: str) -> list[dict]:
    if not block:
        return []
    cols = block.get("columns") or []
    return [dict(zip(cols, r)) for r in (block.get(key) or [])]


def section_focus(rev_rows: list[dict], prof_rows: list[dict], target: str) -> dict:
    """本次財報看點：目標季的月營收已經公布了幾個月、合計跟去年同期／上一季同期比。"""
    y, q = int(target[:4]), int(target[-1])
    months = [f"{y}-{m:02d}" for m in range(q * 3 - 2, q * 3 + 1)]
    pq_y, pq = (y - 1, 4) if q == 1 else (y, q - 1)
    prev_months = [f"{pq_y}-{m:02d}" for m in range(pq * 3 - 2, pq * 3 + 1)]
    by = {r["ym"]: r for r in rev_rows}
    have = [m for m in months if m in by and _f(by[m].get("revenue")) is not None]
    lines, tone = [], 0
    if have:
        cur = sum(_f(by[m]["revenue"]) for m in have)
        ly = [_f(by[m].get("revenue_last_year")) for m in have]
        pm = [_f((by.get(prev_months[months.index(m)]) or {}).get("revenue")) for m in have]
        mtxt = "、".join(str(int(m[5:])) for m in have)
        yoy = (cur / sum(ly) - 1) * 100 if all(x for x in ly) else None
        qoq = (cur / sum(pm) - 1) * 100 if all(x for x in pm) else None
        if len(have) == 3:
            lines.append(f"{target} 三個月營收已全部公布：合計 {_yi(cur)}，較去年同期 {_pct(yoy)}、較上一季 {_pct(qoq)}。"
                         "財報上的營收大致已知，看點在毛利率、營益率與業外。")
        else:
            lines.append(f"{target} 已公布 {mtxt} 月營收：合計 {_yi(cur)}，較去年同期 {_pct(yoy)}、較上一季同期（同樣 {len(have)} 個月）{_pct(qoq)}。")
        tone = 1 if (yoy or 0) > 0 else -1 if (yoy or 0) < 0 else 0
    else:
        lines.append(f"{target} 的月營收還沒有公布（第一個月營收在季後第 1 個月 10 日前公告）。")
    done = [r for r in prof_rows if _f(r.get("eps")) is not None]
    if done:
        last = done[-1]
        gm, om = _f(last.get("gross_margin")), _f(last.get("op_margin"))
        eps, dy = _f(last.get("eps")), _f(last.get("eps_yoy_diff"))
        t = f"上一份財報（{last['period']}）：EPS {eps:.2f} 元"
        if dy is not None:
            t += f"（較去年同季 {dy:+.2f} 元）"
        if gm is not None:
            t += f"、毛利率 {gm:.1f}%"
        if om is not None:
            t += f"、營益率 {om:.1f}%"
        lines.append(t + "；這次要比的基準就是這組數字。")
    return {"key": "focus", "t": "這次財報看什麼", "tone": tone, "lines": lines,
            "src": "月營收（證交所／FinMind）、季損益（證交所／FinMind）",
            "asof": have[-1] if have else (done[-1]["period"] if done else None)}


def section_revenue(rev_rows: list[dict]) -> dict | None:
    rows = [r for r in rev_rows if _f(r.get("revenue")) is not None]
    if len(rows) < 3:
        return None
    last6 = rows[-6:]
    yo = [_f(r.get("yoy")) for r in last6]
    lines = []
    tbl = [[r["ym"], _r(_f(r["revenue"]) / 1e8, 1), _r(r.get("yoy")), _r(r.get("mom"))] for r in last6]
    r0 = rows[-1]
    lines.append(f"最新月營收（{r0['ym']}）{_yi(r0['revenue'])}，年增 {_pct(r0.get('yoy'))}、月增 {_pct(r0.get('mom'))}；"
                 f"今年累計年增 {_pct(r0.get('cum_yoy'))}。")
    a3 = [x for x in yo[-3:] if x is not None]
    b3 = [x for x in yo[-6:-3] if x is not None]
    trend, tone = "資料不足", 0
    if len(a3) == 3 and len(b3) == 3:
        ma, mb = sum(a3) / 3, sum(b3) / 3
        if ma - mb >= 5:
            trend, tone = "加速", 1
        elif mb - ma >= 5:
            trend, tone = "放緩", -1
        else:
            trend = "持平"
        lines.append(f"近 3 個月平均年增 {ma:+.1f}%，前 3 個月 {mb:+.1f}% → 成長動能「{trend}」（差距 5 個百分點以內算持平）。")
    streak = 0
    for r in reversed(rows):
        v = _f(r.get("yoy"))
        if v is None or v <= 0:
            break
        streak += 1
    if streak >= 2:
        lines.append(f"已連續 {streak} 個月年增為正。")
    elif _f(r0.get("yoy")) is not None and _f(r0.get("yoy")) <= 0:
        lines.append("最新一個月年增為負。")
    ser = [[r["ym"], _r(_f(r["revenue"]) / 1e8, 1), _r(r.get("yoy"))] for r in rows[-12:]]
    return {"key": "rev", "t": "月營收趨勢", "tone": tone, "trend": trend, "lines": lines, "series": ser,
            "table": {"cols": ["月份", "營收（億）", "年增%", "月增%"], "rows": tbl},
            "src": "月營收（證交所／FinMind；年增用官方附的去年同月）", "asof": r0["ym"]}


def section_profit(prof_rows: list[dict]) -> dict | None:
    allrows = [r for r in prof_rows if _f(r.get("eps")) is not None]
    rows = allrows[-4:]
    if len(rows) < 2:
        return None
    ser = [[r["period"], _r(r.get("eps"), 2), _r(r.get("gross_margin"))] for r in allrows[-8:]]
    gm = [_f(r.get("gross_margin")) for r in rows]
    om = [_f(r.get("op_margin")) for r in rows]
    lines, tone = [], 0
    eps = [_f(r["eps"]) for r in rows]
    lines.append("近 {} 季 EPS：{}（元）。".format(len(rows), "、".join(f"{r['period']} {e:.2f}" for r, e in zip(rows, eps))))
    if all(x is not None for x in gm):
        d1 = gm[-1] - gm[-2]
        up = sum(1 for a, b in zip(gm, gm[1:]) if b > a)
        dn = sum(1 for a, b in zip(gm, gm[1:]) if b < a)
        word = "連續上升" if up == len(gm) - 1 else "連續下降" if dn == len(gm) - 1 else ("較前一季上升" if d1 > 0 else "較前一季下降" if d1 < 0 else "與前一季持平")
        lines.append(f"毛利率 {gm[0]:.1f}% → {gm[-1]:.1f}%（{word}，最近一季 {d1:+.1f} 個百分點）。")
        tone = 1 if d1 > 0 else -1 if d1 < 0 else 0
    if all(x is not None for x in om):
        lines.append(f"營益率 {om[0]:.1f}% → {om[-1]:.1f}%（最近一季 {om[-1] - om[-2]:+.1f} 個百分點）。")
    dy = _f(rows[-1].get("eps_yoy_diff"))
    if dy is not None:
        lines.append(f"最近一季 EPS 較去年同季 {dy:+.2f} 元。")
    tbl = [[r["period"], _r(r.get("eps"), 2), _r(r.get("gross_margin")), _r(r.get("op_margin"))] for r in rows]
    return {"key": "profit", "t": "獲利能力（近 4 季）", "tone": tone, "lines": lines, "series": ser,
            "table": {"cols": ["季別", "EPS", "毛利率%", "營益率%"], "rows": tbl},
            "src": "季損益（證交所／FinMind，累計值已還原成單季）", "asof": rows[-1]["period"]}


def section_valuation(pe_now, pe_hist: list | None, close, close_date: str) -> dict | None:
    pe = _f(pe_now)
    vals = [float(x["pe"]) for x in (pe_hist or []) if isinstance(x, dict) and _f(x.get("pe")) and float(x["pe"]) > 0]
    if pe is None or pe <= 0:
        return {"key": "val", "t": "估值位置", "tone": 0, "lines": ["近四季 EPS 合計不是正數（或季報不連續），不計算本益比。"],
                "src": "本益比＝收盤 ÷ 近四季 EPS 合計", "asof": close_date}
    lines = [f"收盤 {close:,.2f} 元，本益比 {pe:.1f} 倍（收盤 ÷ 近四季 EPS 合計）。"]
    tone, pos = 0, None
    if len(vals) >= 8:
        below = sum(1 for v in vals if v < pe) + 0.5 * sum(1 for v in vals if v == pe)
        pos = round(below / len(vals) * 100)
        word = "偏高" if pos >= 80 else "偏低" if pos <= 20 else "中間"
        lines.append(f"落在自己近 {len(vals)} 季本益比的第 {pos} 百分位（0＝最便宜、100＝最貴）→ 位置「{word}」；"
                     f"區間 {min(vals):.1f}～{max(vals):.1f} 倍。")
        tone = -1 if pos >= 80 else 1 if pos <= 20 else 0
    else:
        lines.append(f"自己的歷史本益比只有 {len(vals)} 季，少於 8 季不排位置。")
    return {"key": "val", "t": "估值位置", "tone": tone, "pos": pos, "lines": lines, "pe": round(pe, 1),
            "lo": round(min(vals), 1) if vals else None, "hi": round(max(vals), 1) if vals else None,
            "src": "本益比＝收盤 ÷ 近四季 EPS 合計；歷史＝每季公布後第一個收盤的本益比", "asof": close_date}


def section_inst(inst: pd.DataFrame | None, vol: pd.Series | None) -> dict | None:
    if inst is None or inst.empty:
        return None
    g = inst.sort_values("date").drop_duplicates("date", keep="last").tail(20)
    if g.empty:
        return None
    s20 = {k: pd.to_numeric(g[k], errors="coerce").sum() for k in ("foreign_total", "trust", "dealer", "inst_total") if k in g}
    s5 = {k: pd.to_numeric(g.tail(5)[k], errors="coerce").sum() for k in s20}
    fk = "foreign_total" if "foreign_total" in s20 else "foreign"
    lines = [f"近 5 日：外資 {_zhang(s5.get(fk))}、投信 {_zhang(s5.get('trust'))}、自營商 {_zhang(s5.get('dealer'))}。",
             f"近 20 日：外資 {_zhang(s20.get(fk))}、投信 {_zhang(s20.get('trust'))}、三大法人合計 {_zhang(s20.get('inst_total'))}。"]
    tone = 0
    if vol is not None and len(vol):
        v20 = pd.to_numeric(vol, errors="coerce").tail(20).sum()
        if v20:
            ratio = s20.get("inst_total", 0) / v20 * 100
            word = "買超" if ratio >= 3 else "賣超" if ratio <= -3 else "差距不大"
            tone = 1 if ratio >= 3 else -1 if ratio <= -3 else 0
            lines.append(f"三大法人 20 日合計佔同期成交量 {ratio:+.1f}% → {word}（±3% 以內算差距不大）。")
    ik = "inst_total" if "inst_total" in g else fk
    ser = [[str(d)[:10], None if pd.isna(v) else int(round(v))] for d, v in zip(g["date"], pd.to_numeric(g[ik], errors="coerce"))]
    return {"key": "inst", "t": "法人籌碼", "tone": tone, "lines": lines, "series": ser,
            "src": "三大法人買賣超（證交所／FinMind；單位：張）", "asof": str(g["date"].iloc[-1])[:10]}


def section_news(news_rows: list[dict], mops_rows: list[dict]) -> dict | None:
    if not news_rows and not mops_rows:
        return None
    items = [{"d": n["date"], "t": n["title"], "s": n.get("source") or "", "u": n.get("url") or ""} for n in news_rows]
    mitems = [{"d": m["date"], "t": m["subject"], "s": "重大訊息"} for m in mops_rows]
    return {"key": "news", "t": "近期消息", "tone": 0, "items": mitems + items,
            "lines": [f"近 {NEWS_DAYS} 天提到這家公司的新聞 {len(news_rows)} 則（只列標題，不判讀情緒）；重大訊息最新 {len(mops_rows)} 則。"],
            "src": "新聞（鉅亨／TechNews RSS，依標題比對代號與簡稱）、重大訊息（公開資訊觀測站）",
            "asof": max([x["d"] for x in mitems + items] or [None])}


def summary_tags(secs: list[dict]) -> list[dict]:
    tags = []
    for s in secs:
        if not s:
            continue
        if s["key"] == "rev" and s.get("trend") not in (None, "資料不足"):
            tags.append({"l": "營收動能", "v": s["trend"], "tone": s["tone"]})
        elif s["key"] == "profit":
            tags.append({"l": "毛利率", "v": {1: "上升", -1: "下降", 0: "持平"}[s["tone"]], "tone": s["tone"]})
        elif s["key"] == "val" and s.get("pos") is not None:
            tags.append({"l": "本益比位置", "v": f"第 {s['pos']} 百分位", "tone": 0})
        elif s["key"] == "inst":
            tags.append({"l": "法人 20 日", "v": {1: "買超", -1: "賣超", 0: "差距不大"}[s["tone"]], "tone": s["tone"]})
    return tags


def company_analysis(code: str, *, rev: dict, prof: dict, pe_now, pe_hist, close, close_date: str,
                     inst: pd.DataFrame | None, vol: pd.Series | None, news_rows: list, mops_rows: list,
                     target: str) -> dict:
    rev_rows = _cols(rev, "monthly")
    prof_rows = _cols(prof, "quarters")
    secs = [section_focus(rev_rows, prof_rows, target), section_revenue(rev_rows), section_profit(prof_rows),
            section_valuation(pe_now, pe_hist, _f(close) or 0, close_date), section_inst(inst, vol),
            section_news(news_rows, mops_rows)]
    secs = [s for s in secs if s]
    return {"target": target, "tags": summary_tags(secs), "secs": secs}


# ------------------------------------------------------------------ 組裝
def build(*, val: pd.DataFrame, names: dict, latest: str, price: pd.DataFrame, price_adj: pd.DataFrame | None,
          revenue: pd.DataFrame, financial: pd.DataFrame, inst: pd.DataFrame, news: pd.DataFrame | None,
          material_news: pd.DataFrame | None, macro: pd.DataFrame | None, macro_cal: pd.DataFrame | None,
          shares: dict | None = None, cfg: dict | None = None) -> dict:
    from . import stockpage   # 延後載入：stockpage 很大，只有真的要算時才需要

    start = (pd.Timestamp(latest) - pd.Timedelta(days=WINDOW_BACK)).strftime("%Y-%m-%d")
    end = (pd.Timestamp(latest) + pd.Timedelta(days=WINDOW_AHEAD)).strftime("%Y-%m-%d")
    univ = universe(val, names)
    codes = {u["code"] for u in univ}
    ann = mops_events(material_news, codes, conf_all=True)
    ann_in = [e for e in ann if start <= e["d"] <= end]
    # 2026-10-05（晚，Andy：「裡面不可以有推估數據」）：只放已公告／官方公布的日子。
    # estimate_events（預估財報日）與 market_events（營收／財報法定期限）函式保留給測試與日後參考，但不再進 events。
    events = ann_in + macro_events(cfg if cfg is not None else load_macro_yaml(), macro_cal, start, end)
    for e in events:
        if e.get("code"):
            e["name"] = names.get(e["code"]) or e.get("name") or e["code"]
    events.sort(key=lambda e: (e["d"], {"fomc": 0, "minutes": 1, "cpi": 2, "nfp": 3, "pce": 4, "gdp": 5}.get(e["k"], 9), e.get("code") or ""))

    # 每家公司的「這次」財報＝窗內第一個（今天以後）的公司事件；沒有就用下一季
    next_ev: dict[str, dict] = {}
    for e in events:
        if e.get("code") and e["k"] in ("conf", "board", "est", "report") and e["d"] >= latest and e["code"] not in next_ev:
            next_ev[e["code"]] = e
    y, q = quarter_for(latest)
    default_target = f"{y}Q{q}"

    # 2026-10-06（Andy：「法說會公司不在前 50 也要給分析」）：有事件的公司全部做分析，不限市值前 50
    ev_codes = {e["code"] for e in events if e.get("code")}
    extra = sorted(ev_codes - codes)
    codes = codes | set(extra)
    vmap = {}
    if val is not None and not val.empty:
        vv = val.assign(code=val["code"].astype(str))
        vmap = {r.code: r for r in vv[vv["code"].isin(extra)].itertuples()}
    for c in extra:
        r = vmap.get(c)
        mc = _f(getattr(r, "market_cap", None)) if r is not None else None
        univ.append({"code": c, "name": names.get(c) or c, "rank": None, "mcap": _r(mc / 1e8, 0) if mc else None,
                     "close": _r(getattr(r, "close", None), 2) if r is not None else None, "_extra": True})

    def by_code(df, col="code"):
        if df is None or df.empty:
            return {}
        d = df[df[col].astype(str).isin(codes)]
        return {str(k): g for k, g in d.groupby(d[col].astype(str))}
    rev_by, fin_by, inst_by = by_code(revenue), by_code(financial), by_code(inst)
    raw_by = by_code(price)
    adj_by = by_code(price_adj) if price_adj is not None else {}
    news_by: dict[str, list] = {}
    if news is not None and not news.empty:
        cut = (pd.Timestamp(latest) - pd.Timedelta(days=NEWS_DAYS)).strftime("%Y-%m-%d")
        nd = news[news["date"].astype(str) >= cut].copy()
        ts = pd.to_datetime(nd.get("published_at"), errors="coerce", utc=True, format="mixed") if "published_at" in nd else None
        nd["_ts"] = ts if ts is not None else pd.NaT
        nd = nd.sort_values(["_ts", "date"], ascending=False, na_position="last")
        for _, n in nd.iterrows():
            for c in str(n.get("codes") or "").split(","):
                if c in codes and len(news_by.setdefault(c, [])) < NEWS_N:
                    news_by[c].append({"date": str(n["date"])[:10], "title": str(n.get("title") or ""),
                                       "source": n.get("source"), "url": n.get("url")})
    mops_by: dict[str, list] = {}
    if material_news is not None and not material_news.empty:
        mm = material_news[material_news["code"].astype(str).isin(codes)].sort_values(["date", "time"], ascending=False)
        for _, m in mm.iterrows():
            c = str(m["code"])
            if len(mops_by.setdefault(c, [])) < MOPS_N:
                mops_by[c].append({"date": str(m["date"])[:10], "subject": re.sub(r"\s+", " ", str(m.get("subject") or ""))[:80]})
    pe_map = {}
    if val is not None and not val.empty and "pe" in val.columns:
        pe_map = dict(zip(val["code"].astype(str), val["pe"]))

    companies = {}
    for u in univ:
        c = u["code"]
        try:
            fin = fin_by.get(c, pd.DataFrame())
            rv = stockpage.revenue_series(rev_by.get(c, pd.DataFrame()), c) if c in rev_by else {}
            pf = stockpage.profit_series(fin, c, asof=latest) if not fin.empty else {}
            ph = stockpage.pe_history(raw_by[c], fin, c, shares=shares, adj_price=adj_by.get(c)) if c in raw_by and not fin.empty else []
            raw = raw_by.get(c)
            vol = raw.sort_values("date")["volume"] if raw is not None and "volume" in raw else None
            ne = next_ev.get(c)
            target = (ne.get("q") if ne and ne.get("q") else None) or default_target
            companies[c] = {"name": u["name"], "rank": u["rank"], "mcap": u["mcap"], "close": u["close"],
                            "next": {k: ne[k] for k in ("d", "k", "status", "title") if k in ne} if ne else None,
                            **company_analysis(c, rev=rv, prof=pf, pe_now=pe_map.get(c), pe_hist=ph, close=u["close"],
                                               close_date=latest, inst=inst_by.get(c), vol=vol, news_rows=news_by.get(c, []),
                                               mops_rows=mops_by.get(c, []), target=target)}
        except Exception as exc:  # noqa: BLE001 —— 一家算壞不能讓整頁沒有
            log.warning("財報日曆 %s 分析失敗：%s", c, exc)
            companies[c] = {"name": u["name"], "rank": u["rank"], "mcap": u["mcap"], "close": u["close"], "next": None,
                            "target": default_target, "tags": [], "secs": [], "err": "這家的資料整理失敗，請改看個股頁"}

    snap = macro_snapshot(macro)
    nxt = {}
    for e in events:
        if e["k"] in FED_INFO and e["d"] >= latest and e["k"] not in nxt:
            nxt[e["k"]] = {"d": e["d"], "tw": e.get("tw"), "title": e["title"]}
    return {
        "v": 2, "asof": latest, "window": [start, end],
        "universe": {"basis": f"市值前 {UNIVERSE_N}（收盤 × 最新一季財報股數；上市＋上櫃普通股，排除 ETF）",
                     "n": UNIVERSE_N if len(univ) >= UNIVERSE_N else len(univ), "asof": latest, "list": [u for u in univ if not u.get("_extra")]},
        "mops_since": str(material_news["date"].min())[:10] if material_news is not None and not material_news.empty else None,
        "events": events,
        "companies": companies,
        "fed": {"info": fed_info_merged(cfg), "snap": snap, "next": nxt,
                "macro_src": "FRED（聯準會聖路易分行經濟資料庫）" if snap else None},
    }


def build_from_lake(latest: str | None = None) -> dict:
    """本機只產這一檔用（預覽分支的種子檔）。跟 build_payload 同一套口徑：價格清理、股本事件、近四季 EPS、市值。"""
    from ..util import store
    from . import fundamental
    from ..build_payload import last_complete_date

    price = store.read("price_daily")
    company = store.read("company_info")
    names = (company.dropna(subset=["name"]).drop_duplicates("code", keep="last").set_index("code")["name"].to_dict()
             if not company.empty else {})
    latest = latest or last_complete_date(price)
    price = fundamental.clean_price(price[price["date"].astype(str) <= latest])
    actions = fundamental.corporate_actions(price, store.read("dividend_results"), store.read("dividend_events"))
    actions = actions[actions["date"].astype(str) <= latest] if not actions.empty else actions
    shares = fundamental.share_table(actions)
    financial = store.read("financial_q")
    day_px = price[price["date"] == latest][["code", "close"]]
    val = fundamental.valuation(day_px, fundamental.ttm(financial, shares, latest),
                                fundamental.latest_balance(store.read("balance_q"), shares, latest))
    mat = store.read("material_news")
    codes = {u["code"] for u in universe(val, names)} | {e["code"] for e in mops_events(mat, set(), conf_all=True)}
    sub = price[price["code"].astype(str).isin(codes)]
    adj = fundamental.adjust_prices(sub, actions[actions["code"].astype(str).isin(codes)] if not actions.empty else actions, mode="total")
    inst = store.read("inst_daily")
    inst = inst[inst["date"].astype(str) <= latest] if not inst.empty else inst
    return build(val=val, names=names, latest=latest, price=sub, price_adj=adj, revenue=store.read("revenue_monthly"),
                 financial=financial, inst=inst, news=store.read("news"), material_news=mat,
                 macro=store.read("macro"), macro_cal=store.read("macro_calendar"), shares=shares)


if __name__ == "__main__":   # python -m pipeline.compute.earnings site/earnings_seed.json
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from ..build_payload import _clean
    out = Path(sys.argv[1] if len(sys.argv) > 1 else config.SITE_DATA / "earnings.json")
    out.write_text(json.dumps(_clean(build_from_lake()), ensure_ascii=False), encoding="utf-8")
    log.info("寫出 %s（%.1f KB）", out, out.stat().st_size / 1024)
