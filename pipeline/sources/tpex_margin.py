"""上櫃整體市場融資融券（融資張數、融資金額、融券張數）——櫃買中心 OpenAPI（2026-11-06，Andy：信用交易頁「上市＋上櫃」）。

為什麼要這一張表：
  上市的「融資維持率（估算）」分母是整體市場融資金額（FinMind TaiwanStockTotalMarginPurchaseShortSale，只含上市）。
  上櫃要用同一個口徑，就需要「上櫃整體融資金額」；FinMind 免費版沒有上櫃總表，
  上櫃個股融資餘額張數已經在 margin_daily（FinMind 逐檔續補，market=TPEX），缺的只有分母。
  櫃買 OpenAPI（www.tpex.org.tw/openapi，政府資料開放授權條款第 1 版，白名單見 docs/source_whitelist_taifex_tpex.md）
  有「上櫃信用交易餘額概況表」那一類的彙總端點，裡面有融資金額（仟元）。
  ⚠ 絕不碰 www.tpex.org.tw/www/zh-tw/... 那類網頁介面或 tpex-api（條款禁止自動擷取，DECISIONS #265）。

端點名稱與欄位名「沒有實測 fixture」（容器連不到外網），所以照 inst_official.py 的做法：
  * 先讀 swagger.json，把摘要／路徑含「信用交易、融資融券＋概況／彙總／總表、margin」的都列成候選，再加幾個猜的名字；
  * 欄位用關鍵字寬鬆對應（中文／英文都收），長表（一列一個項目）與寬表（一列一天）兩種形狀都認；
  * 回應超過 MAX_ROWS 列視為「個股明細」不是總表，不收（個股表沒有金額，硬加會把張數當金額）；
  * 融資金額換算成「元」後必須落在 [MONEY_MIN, MONEY_MAX]，否則整份不收 —— 資料湖只增不改，寧可缺不可錯；
  * 每一支端點的網址、HTTP 狀態、前 200 字、欄位名都進 DIAG，run_daily 寫進 last_run.json，下一個人照著修。
資料日期只用回應裡的日期欄；沒有日期欄就不收（不拿執行當下日期當交易日）。
OpenAPI 只給「最新一天」，所以這張表從第一次抓到起逐日累積，沒有官方開放的歷史可回補（已知限制）。
"""
from __future__ import annotations

import logging
import re

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import roc_to_iso, to_float

log = logging.getLogger(__name__)

ROOT = "https://www.tpex.org.tw/openapi"
SWAGGER = ROOT + "/swagger.json"
CANDIDATES = ["/v1/tpex_mainboard_margin_summary", "/v1/tpex_margin_summary", "/v1/tpex_mainboard_margin_trading_summary"]
_DISCOVER = re.compile(r"信用交易|融資融券.*(概況|彙總|總表|統計)|margin.*(summ|total|stat|overview)", re.I)
_HEADERS = {"Referer": "https://www.tpex.org.tw/", "Accept": "application/json, text/plain, */*"}
MAX_ROWS = 50                     # 總表只有幾列；超過就是個股明細
MONEY_MIN, MONEY_MAX = 5e9, 3e12  # 上櫃融資金額合理範圍（元）：50 億～3 兆；2026-11 實際約 1,500～2,000 億
COLS = ["date", "margin_lots", "margin_lots_prev", "margin_money", "margin_money_prev", "short_lots", "short_lots_prev"]

DIAG: list[dict] = []

_PREV = re.compile(r"前日|前資|昨日|previous|yesterday|^yes|prior", re.I)
_TODAY = re.compile(r"今日|本日|當日|餘額|balance|today", re.I)
_FLOW = re.compile(r"買進|賣出|現償|現券|限額|使用率|增減|purchase(?!money)|sale|sell|buy|redemp|repay|limit|rate|change", re.I)
_MONEY = re.compile(r"金額|amount|money|仟元|千元|value", re.I)
_MARGIN = re.compile(r"融資|資餘|margin", re.I)
_SHORT = re.compile(r"融券|券餘|short", re.I)
_K = re.compile(r"仟元|千元|thousand", re.I)


def _norm(s) -> str:
    return re.sub(r"[\s_()（）\-]", "", str(s))


def _item(ctx: str) -> str | None:
    """一段文字（項目名＋欄名）→ margin_money／margin_lots／short_lots／None。"""
    if _SHORT.search(ctx) and not re.search(r"融資", ctx):
        return None if _MONEY.search(ctx) else "short_lots"
    if _MARGIN.search(ctx):
        return "margin_money" if _MONEY.search(ctx) else "margin_lots"
    return None


def _when(key: str) -> str | None:
    """欄名 → 'today'／'prev'／None（買進、賣出、限額這類流量欄不收）。"""
    k = _norm(key)
    if _PREV.search(k):
        return "prev"
    # 「融資買進」的 purchase、「融券賣出」的 sale 會撞到 MarginPurchase／ShortSale 這種項目名；先把項目名縮短再找流量字眼，但「MarginPurchaseMoney」「融資餘額」這種要留著
    flow = _FLOW.search(re.sub(r"marginpurchase", "margin", re.sub(r"shortsale", "short", k, flags=re.I), flags=re.I))
    if flow:
        return None
    return "today" if _TODAY.search(k) else None


def _date(row: dict) -> str | None:
    """回應裡的資料日（民國 1151105／115/11/05 或西元 2026-11-05、2026/11/05 都收）。"""
    for k, v in row.items():
        if re.search(r"date|日期|資料日", str(k), re.I):
            s = str(v).strip()
            d = roc_to_iso(s) or roc_to_iso(s.replace("/", "-"))
            if d:
                return d
    return None


def parse_summary(raw) -> pd.DataFrame:
    """櫃買 OpenAPI 信用交易彙總表的 list[dict] → 一天一列（COLS）。認不得回空。

    兩種形狀都收：
      長表：每列一個項目（「融資(交易單位)」「融資金額(仟元)」「融券(交易單位)」），欄是前日餘額／買進／…／今日餘額；
      寬表：每列一天，欄名本身帶項目（「融資金額今日餘額」「MarginPurchaseMoneyTodayBalance」）。
    融資金額一律換成「元」：項目名或欄名有「仟元／千元」就 ×1000；都沒寫而數值 < MONEY_MIN 也視為仟元 ×1000
    （上櫃融資金額以元計至少數百億，以仟元計才會落在一億上下），換算後不在合理範圍就整份不收。
    """
    if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict) or len(raw) > MAX_ROWS:
        return pd.DataFrame()
    out: dict[str, dict] = {}
    for row in raw:
        d = _date(row)
        if not d:
            continue
        label = " ".join(str(v) for v in row.values() if isinstance(v, str) and (_MARGIN.search(v) or _SHORT.search(v))
                         and to_float(v) is None)
        rec = out.setdefault(d, {})
        for k, v in row.items():
            if re.search(r"date|日期", str(k), re.I):
                continue
            val = to_float(v)
            if val is None:
                continue
            ctx = _norm(label + str(k))
            it = _item(ctx)
            w = _when(str(k))
            if not it or not w:
                continue
            if it == "margin_money" and (_K.search(ctx) or val < MONEY_MIN):
                val *= 1000
            rec.setdefault(it + ("" if w == "today" else "_prev"), val)
    rows = []
    for d, rec in out.items():
        m = rec.get("margin_money")
        if m is None or not (MONEY_MIN <= m <= MONEY_MAX):
            if rec:
                log.warning("上櫃信用彙總 %s 融資金額不在合理範圍或找不到（%s），不收", d, m)
            continue
        rows.append({c: (d if c == "date" else rec.get(c)) for c in COLS})
    return pd.DataFrame(rows, columns=COLS) if rows else pd.DataFrame()


def _get(url: str):
    try:
        r = http.session().get(url, headers=_HEADERS, timeout=config.HTTP_TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        DIAG.append({"url": url, "err": str(exc)[:120]})
        return None, None
    head = r.text[:200].replace("\n", " ")
    DIAG.append({"url": url, "http": r.status_code, "head": head})
    log.info("上櫃信用彙總探測 %s -> HTTP %s：%s", url, r.status_code, head)
    if r.status_code != 200:
        return r.status_code, None
    try:
        return 200, r.json()
    except ValueError:
        return 200, None


def discover(sw: dict | None) -> list[str]:
    """swagger.json → 候選路徑（摘要或路徑命中 _DISCOVER）。回傳 /v1 開頭的路徑。"""
    found = []
    for p, spec in ((sw or {}).get("paths") or {}).items():
        summ = " ".join(str((op or {}).get("summary", "")) for op in (spec or {}).values() if isinstance(op, dict))
        if _DISCOVER.search(summ) or _DISCOVER.search(p):
            pp = p if p.startswith("/v1") else "/v1" + p
            found.append(pp)
            DIAG.append({"swagger_path": pp, "summary": summ[:80]})
    return found


def fetch() -> pd.DataFrame:
    """抓上櫃信用交易彙總（只有最新一天）；失敗或認不得回空 DataFrame。"""
    DIAG.clear()
    _, sw = _get(SWAGGER)
    cands = discover(sw if isinstance(sw, dict) else None)
    for p in CANDIDATES:
        if p not in cands:
            cands.append(p)
    for p in cands:
        st, js = _get(ROOT + p)
        if st != 200 or js is None:
            continue
        if isinstance(js, list) and js and isinstance(js[0], dict):
            DIAG.append({"url": ROOT + p, "n": len(js), "cols": list(js[0].keys())[:20]})
        df = parse_summary(js)
        if not df.empty:
            log.info("上櫃信用彙總：%s 取得 %d 天", p, len(df))
            DIAG.append({"picked": p, "rows": int(len(df))})
            return df
    log.warning("上櫃信用彙總：所有候選端點都認不得（見 DIAG）")
    return pd.DataFrame()
