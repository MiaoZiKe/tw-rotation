"""ETF 成分股與權重：各發行投信官網每日公告的「申購買回清單（PCF）／持股明細」。

為什麼是這裡、不是別處（查證過程與實測紀錄在 docs/etf_holdings_source.md）：
- 投信依《ETF 發行人應行注意事項》每個營業日都要公告 PCF，內容就是基金持有的每一檔股票與股數，
  這是「為了讓投資人取用」而公開的一手資訊；投信官網的頁面背後都是自家的 JSON API，
  這裡打的就是那幾支（2026-10-07 在 GitHub Actions 上實測過，`.github/workflows/probe-etf-pcf.yml`）。
- 證交所官網（www.twse.com.tw 的 ETF e 添富、rwd）照 CLAUDE.md 絕對不做 1 不碰；
  openapi.twse.com.tw 的 swagger 實測沒有任何 ETF 成分端點；第三方彙整站（口袋、CMoney）不當來源。

設計：
- 每一家投信一支函式，失敗回空 DataFrame 並記 log，不讓一家壞掉拖垮其他家。
- 解析失敗一律把**實際回應前 200 字**印進 log —— 投信改版是常態，下一個人才修得了。
- 資料日期一律用回應裡的日期（淨值日／持股基準日），不用執行當下的日期。
- 欄位：date（持股基準日）、etf、code、name、weight（占基金淨值 %，投信沒給就留空，
  由 build_payload 用股數×收盤價推算）、shares（基金持有總股數，可為空）、issuer、src（來源網址）。
"""
from __future__ import annotations

import datetime as dt
import html as _html
import json
import logging
import re
import time
from typing import Any, Callable

import pandas as pd

from ..util import http

log = logging.getLogger(__name__)

COLS = ["date", "etf", "code", "name", "weight", "shares", "issuer", "src"]
TIMEOUT = 30

# 非股票型（債券／槓桿反向／期貨／匯率／商品）在這裡就跳過：沒有個股成分，抓了也是白抓。
_SKIP_SUFFIX = re.compile(r"[BLRUKD]$")


def _skip_code(code: str) -> bool:
    return bool(_SKIP_SUFFIX.search(str(code).strip()))


def _snip(text: Any) -> str:
    try:
        s = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        s = repr(text)
    return s[:200].replace("\n", " ").replace("\r", " ")


def _num(x) -> float | None:
    if x is None:
        return None
    s = str(x).replace(",", "").replace("%", "").strip()
    if not s or s in ("-", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _iso(s: Any) -> str | None:
    """各家日期格式（2026/10/06、2026-10-06T00:00:00、20261006、115/10/06）→ ISO。"""
    if s is None:
        return None
    t = str(s).strip()
    m = re.match(r"^/Date\((\d+)", t)                      # .NET JSON 日期（毫秒）→ 台北日期
    if m:
        return (dt.datetime.fromtimestamp(int(m.group(1)) / 1000, dt.timezone.utc) + dt.timedelta(hours=8)).date().isoformat()
    m = re.match(r"^(\d{2,3})/(\d{1,2})/(\d{1,2})", t)          # 民國
    if m and int(m.group(1)) < 1911:
        return f"{int(m.group(1)) + 1911:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"^(\d{4})[-/]?(\d{1,2})[-/]?(\d{1,2})", t)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def _req(method: str, url: str, *, json_body: Any = None, params: dict | None = None,
         expect: str = "json", retries: int = 2) -> Any | None:
    """投信 API 共用的請求：POST 也要支援（util.http.get 只有 GET），失敗回 None 並記前 200 字。"""
    last = ""
    for _ in range(retries):
        try:
            s = http.session()
            r = (s.post(url, json=json_body, params=params, timeout=TIMEOUT) if method == "POST"
                 else s.get(url, params=params, timeout=TIMEOUT))
            if r.status_code != 200:
                last = f"HTTP {r.status_code}：{_snip(r.text)}"
                if r.status_code in (401, 403, 404, 405):
                    break
                continue
            if expect == "text":
                r.encoding = r.encoding or "utf-8"
                return r.text
            try:
                return r.json()
            except ValueError:
                last = f"不是 JSON：{_snip(r.text)}"
                break
        except Exception as exc:  # noqa: BLE001 —— 任何連線錯誤都只記錄
            last = str(exc)[:200]
    log.warning("ETF PCF %s %s 失敗：%s", method, url, last)
    return None


def _frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=COLS)
    df = pd.DataFrame(rows)
    for c in COLS:
        if c not in df.columns:
            df[c] = None
    df = df[COLS]
    df["code"] = df["code"].astype(str).str.strip()
    df = df[df["code"].ne("") & df["date"].notna()]
    return df.drop_duplicates(["date", "etf", "code"], keep="last").reset_index(drop=True)


# ───────────────────────────────────────────── 群益（capitalfund.com.tw）
CAPITAL_LIST = "https://www.capitalfund.com.tw/CFWeb/api/etf/list"
CAPITAL_PCF = "https://www.capitalfund.com.tw/CFWeb/api/etf/buyback"


def parse_capital(etf: str, payload: dict) -> list[dict]:
    """POST buyback 的回應：data.pcf.date2＝淨值日（持股基準日），data.stocks[]＝持股（weight 是占淨值 %）。"""
    data = (payload or {}).get("data") or {}
    pcf = data.get("pcf") or {}
    day = _iso(pcf.get("date2")) or _iso(pcf.get("date1"))
    out = []
    for s in data.get("stocks") or []:
        out.append({"date": day, "etf": etf, "code": str(s.get("stocNo") or "").strip(),
                    "name": (s.get("stocName") or "").strip(), "weight": _num(s.get("weight")),
                    "shares": _num(s.get("share")), "issuer": "群益", "src": CAPITAL_PCF})
    return out


def capital() -> pd.DataFrame:
    lst = _req("POST", CAPITAL_LIST, json_body=None)
    funds = (((lst or {}).get("data") or {}).get("funds")) or []
    if not funds:
        log.warning("群益 ETF 清單解析失敗（前 200 字）：%s", _snip(lst))
        return pd.DataFrame(columns=COLS)
    rows: list[dict] = []
    for f in funds:
        code, fid = str(f.get("stockNo") or "").strip(), str(f.get("fundNo") or "").strip()
        if not code or not fid or _skip_code(code):
            continue
        p = _req("POST", CAPITAL_PCF, json_body={"fundId": fid, "date": None})
        got = parse_capital(code, p) if p else []
        if p and not got and ((p.get("data") or {}).get("stocks") is None):
            log.info("群益 %s 沒有股票清單（前 200 字）：%s", code, _snip(p))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 野村（nomurafunds.com.tw）
NOMURA_PCF = "https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets"


def parse_nomura(etf: str, payload: dict) -> list[dict]:
    """GetFundAssets：Entries.Data.FundAsset.NavDate，Table[TableTitle=股票].Rows＝[代號, 名稱, 股數, 權重%]。"""
    data = (((payload or {}).get("Entries") or {}).get("Data")) or {}
    day = _iso((data.get("FundAsset") or {}).get("NavDate"))
    out = []
    for tb in data.get("Table") or []:
        if "股票" not in str(tb.get("TableTitle") or ""):
            continue
        cols = [str(c.get("Name") or "") for c in tb.get("Columns") or []]
        ix = {k: next((i for i, c in enumerate(cols) if k in c), None) for k in ("代號", "名稱", "股數", "權重")}
        if ix["代號"] is None or ix["權重"] is None:
            log.warning("野村 %s 欄位對不上：%s", etf, cols)
            continue
        for r in tb.get("Rows") or []:
            g = lambda k: r[ix[k]] if ix[k] is not None and ix[k] < len(r) else None  # noqa: E731
            out.append({"date": day, "etf": etf, "code": str(g("代號") or "").strip(), "name": str(g("名稱") or "").strip(),
                        "weight": _num(g("權重")), "shares": _num(g("股數")), "issuer": "野村", "src": NOMURA_PCF})
    return out


def nomura(codes: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for c in codes:
        if _skip_code(c):
            continue
        p = _req("POST", NOMURA_PCF, json_body={"FundID": c, "SearchDate": None})
        got = parse_nomura(c, p) if p else []
        if p and not got:
            log.info("野村 %s 沒有股票表（前 200 字）：%s", c, _snip(p))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 復華（fhtrust.com.tw）
FH_LIST = "https://www.fhtrust.com.tw/api/fundList"
FH_ASSETS = "https://www.fhtrust.com.tw/api/assets"


def parse_fuhhwa(payload: dict) -> list[dict]:
    """/api/assets?fundID=ETFxx&qDate=YYYY/MM/DD：result[0].dDate、etf002（代號）、detail[]（ftype=股票）。"""
    out = []
    for blk in (payload or {}).get("result") or []:
        etf = str(blk.get("etf002") or "").strip()
        day = _iso(blk.get("dDate"))
        for d in blk.get("detail") or []:
            if str(d.get("ftype") or "") != "股票":
                continue
            out.append({"date": day, "etf": etf, "code": str(d.get("stockid") or "").strip(),
                        "name": str(d.get("stockname") or "").strip(), "weight": _num(d.get("prate_addaccint")),
                        "shares": _num(d.get("qshare")), "issuer": "復華", "src": FH_ASSETS})
    return out


def fuhhwa(today: dt.date | None = None) -> pd.DataFrame:
    lst = _req("GET", FH_LIST)
    funds = [(str(f.get("fundID") or ""), str(f.get("etf002") or "").strip()) for f in ((lst or {}).get("result") or [])]
    funds = [(fid, c) for fid, c in funds if fid.startswith("ETF") and re.match(r"^\d{4,6}[A-Z]?$", c) and not _skip_code(c)]
    if not funds:
        log.warning("復華 ETF 清單解析失敗（前 200 字）：%s", _snip(lst))
        return pd.DataFrame(columns=COLS)
    today = today or dt.date.today()
    rows: list[dict] = []
    for fid, code in funds:
        # qDate 要給「有資料的那一天」：從今天往前找，最多 7 天（假日、颱風假）。日期以回應的 dDate 為準。
        for back in range(0, 8):
            q = (today - dt.timedelta(days=back)).strftime("%Y/%m/%d")
            p = _req("GET", FH_ASSETS, params={"fundID": fid, "qDate": q}, retries=1)
            got = parse_fuhhwa(p) if isinstance(p, dict) else []
            if got:
                rows += got
                break
    return _frame(rows)


# ───────────────────────────────────────────── 統一（ezmoney.com.tw）
UNI_PAGE = "https://www.ezmoney.com.tw/ETF/Transaction/PCF"
UNI_PCF = "https://www.ezmoney.com.tw/ETF/Transaction/GetPCF"


def parse_uni(etf: str, payload: dict) -> list[dict]:
    """GetPCF：asset[]＝各資產類別 {AssetCode, AssetName, Details[]}；股票類（AssetName 含「股票」）的
    Details 每列 {DetailCode 代號, DetailName 名稱, NavRate 權重%, Share 股數, TranDate 淨值日}。
    （2026-10-07 實測：assetDetailSchema 把 NavRate 標成「持股權重」、Share 標成股數／口數。）"""
    if not isinstance(payload, dict):
        return []
    day = None
    for p in payload.get("pcf") or []:
        day = _iso(p.get("TranDate")) or day
        if day:
            break
    out = []
    for a in payload.get("asset") or []:
        if not isinstance(a, dict) or "股" not in str(a.get("AssetName") or ""):
            continue
        for d in a.get("Details") or []:
            code = str(d.get("DetailCode") or "").strip()
            if not code:
                continue
            out.append({"date": _iso(d.get("TranDate")) or day, "etf": etf, "code": code,
                        "name": str(d.get("DetailName") or "").strip(), "weight": _num(d.get("NavRate")),
                        "shares": _num(d.get("Share")), "issuer": "統一", "src": UNI_PCF})
    return out


def uni_fund_codes(page_html: str) -> dict[str, str]:
    """PCF 頁裡內嵌的基金清單（HTML 轉義過的 JSON）：sFundCode ↔ sStockNo。"""
    t = _html.unescape(page_html or "")
    out = {}
    for m in re.finditer(r'"sFundCode":"(\w+)".{0,400}?"sStockNo":"(\w+)\s*"', t):
        out[m.group(2).strip()] = m.group(1)
    return out


def uni(today: dt.date | None = None) -> pd.DataFrame:
    page = _req("GET", UNI_PAGE, expect="text")
    codes = uni_fund_codes(page or "")
    if not codes:
        log.warning("統一 PCF 頁找不到基金代碼（前 200 字）：%s", _snip(page))
        return pd.DataFrame(columns=COLS)
    today = today or dt.date.today()
    roc = f"{today.year - 1911}/{today.month:02d}/{today.day:02d}"
    rows: list[dict] = []
    for etf, fc in codes.items():
        if _skip_code(etf):
            continue
        p = _req("POST", UNI_PCF, json_body={"fundCode": fc, "date": roc, "specificDate": False})
        got = parse_uni(etf, p) if p else []
        if p and not got:
            log.info("統一 %s 回應裡找不到持股，asset 前 400 字：%s", etf,
                     (json.dumps(p.get("asset") if isinstance(p, dict) else p, ensure_ascii=False)[:400] + " ／ schema " + json.dumps(p.get("assetDetailSchema") if isinstance(p, dict) else None, ensure_ascii=False)[:400]))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 凱基（kgifund.com.tw）
KGI_PAGE = "https://www.kgifund.com.tw/Fund/RedemptionList"
KGI_PCF = "https://www.kgifund.com.tw/Fund/RedemptionVC"


def _norm(n: str) -> str:
    return re.sub(r"\s+", "", str(n or "")).upper()


def kgi_fund_ids(page_html: str, names: dict[str, str]) -> dict[str, str]:
    """申購買回清單頁的隱藏欄位 AllFundName＝[{label: 簡稱, fundID: J024}]（沒有 ETF 代號），
    用 company_info 的 ETF 簡稱對回代號；對不到的記 log。"""
    t = _html.unescape(page_html or "")
    m = re.search(r'id="AllFundName"[^>]*value="(\[.*?\])"', t, re.S) or re.search(r'value="(\[\{"label".*?\])"', t, re.S)
    try:
        lst = json.loads(m.group(1)) if m else []
    except ValueError:
        lst = []
    by_name = {_norm(n): c for c, n in names.items()}
    out = {}
    for x in lst:
        lab, fid = x.get("label"), x.get("fundID")
        c = by_name.get(_norm(lab))
        if c and fid:
            out[c] = fid
        elif fid:
            log.info("凱基 %s（%s）對不到 ETF 代號", lab, fid)
    return out


def parse_kgi(etf: str, frag: str) -> list[dict]:
    """RedemptionVC 回的 HTML 片段：股票表 <tr name="content"><td>代號<td>名稱<td>股數<td>權重(%)；資料日期取片段裡第一個日期。"""
    t = _html.unescape(frag or "")
    dm = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", t) or re.search(r"(\d{3})/(\d{1,2})/(\d{1,2})", t)
    day = _iso("/".join(dm.groups())) if dm else None
    out = []
    for tr in re.findall(r'<tr name="content"[^>]*>(.*?)</tr>', t, re.S):
        tds = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(tds) >= 4 and re.match(r"^\d{4,6}[A-Z]?$", tds[0]):
            out.append({"date": day, "etf": etf, "code": tds[0], "name": tds[1], "weight": _num(tds[3]),
                        "shares": _num(tds[2]), "issuer": "凱基", "src": KGI_PCF})
    return out


def kgi(names: dict[str, str]) -> pd.DataFrame:
    page = _req("GET", KGI_PAGE, expect="text")
    ids = kgi_fund_ids(page or "", {c: n for c, n in names.items() if "凱基" in str(n)})
    if not ids:
        log.warning("凱基申購買回清單頁找不到基金選單（前 200 字）：%s", _snip(page))
        return pd.DataFrame(columns=COLS)
    rows: list[dict] = []
    for etf, fid in ids.items():
        if _skip_code(etf):
            continue
        try:
            r = http.session().post(KGI_PCF, data={"fundID": fid, "queryDate": ""}, timeout=TIMEOUT)
            frag = r.text if r.status_code == 200 else ""
        except Exception as exc:  # noqa: BLE001
            log.warning("凱基 %s 失敗：%s", etf, exc)
            continue
        got = parse_kgi(etf, frag)
        if not got:
            log.info("凱基 %s 沒有股票表（前 200 字）：%s", etf, _snip(frag))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 國泰（cathaysite.com.tw；官網 www 對雲端 IP 回 403，資料 API 在 cwapi）
CATHAY_LIST = "https://cwapi.cathaysite.com.tw/api/ETF/GetETFList"
CATHAY_ASSETS = "https://cwapi.cathaysite.com.tw/api/ETF/GetETFAssets"
CATHAY_STOCKS = "https://cwapi.cathaysite.com.tw/api/ETF/GetETFDetailStockList"


def parse_cathay(etf: str, day: str | None, payload: dict) -> list[dict]:
    """GetETFDetailStockList?FundCode=&SearchDate=：result[] {stockCode, stockName, volumn（股數）, weights（%）}。
    日期不在這支回應裡，由 GetETFAssets 的 preDate（淨值日）提供。"""
    out = []
    for r in (payload or {}).get("result") or []:
        out.append({"date": day, "etf": etf, "code": str(r.get("stockCode") or "").strip(),
                    "name": re.sub(r"\s+", "", str(r.get("stockName") or "")), "weight": _num(r.get("weights")),
                    "shares": _num(r.get("volumn")), "issuer": "國泰", "src": CATHAY_STOCKS})
    return out


def cathay_funds() -> dict[str, str]:
    """{ETF 代號: fundCode}。清單 API 分頁，參數名照官網前端（CurrentPage／PerPageCount，2026-10-07 讀 main.js 確認）。"""
    out: dict[str, str] = {}
    for page in range(1, 6):
        lst = _req("GET", CATHAY_LIST, params={"FundType": "", "Keyword": "", "CurrentPage": page, "PerPageCount": 100}, retries=1)
        res = (lst or {}).get("result") or []
        for r in res:
            c, f = str(r.get("stockCode") or "").strip(), str(r.get("fundCode") or "").strip()
            if c and f:
                out[c] = f
        if len(out) >= int((lst or {}).get("totalCount") or 0) or not res:
            break
    return out


def cathay(today: dt.date | None = None) -> pd.DataFrame:
    funds = cathay_funds()
    if not funds:
        log.warning("國泰 ETF 清單抓不到")
        return pd.DataFrame(columns=COLS)
    rows: list[dict] = []
    for etf, fc in funds.items():
        if _skip_code(etf):
            continue
        a = _req("GET", CATHAY_ASSETS, params={"FundCode": fc}, retries=1)
        day = _iso(((a or {}).get("result") or {}).get("preDate"))
        if not day:
            log.info("國泰 %s 沒有淨值日（前 200 字）：%s", etf, _snip(a))
            continue
        p = _req("GET", CATHAY_STOCKS, params={"FundCode": fc, "SearchDate": day.replace("-", "/")}, retries=1)
        got = parse_cathay(etf, day, p)
        if not got:
            log.info("國泰 %s 沒有股票清單（前 200 字）：%s", etf, _snip(p))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 中國信託（ctbcinvestments.com；API 在 .com.tw）
CTBC_API = "https://www.ctbcinvestments.com.tw/API/"
CTBC_SITE = "www.ctbcinvestments.com"


def parse_ctbc(etf: str, payload: dict) -> list[dict]:
    """etf/ETFHoldingWeight：Data.FundAssets[0].資料日期；Data.FundAssetsDetail[Code=STOCK].Data[] {code_, name_, qty_, weights_}。"""
    data = (payload or {}).get("Data") or {}
    fa = (data.get("FundAssets") or [{}])[0] or {}
    day = _iso(fa.get("資料日期")) or _iso(fa.get("NAV_DT"))
    out = []
    for blk in data.get("FundAssetsDetail") or []:
        if str(blk.get("Code") or "").upper() != "STOCK":
            continue
        for r in blk.get("Data") or []:
            out.append({"date": day, "etf": etf, "code": str(r.get("code_") or "").strip(), "name": str(r.get("name_") or "").strip(),
                        "weight": _num(r.get("weights_")), "shares": _num(r.get("qty_")), "issuer": "中國信託",
                        "src": CTBC_API + "etf/ETFHoldingWeight"})
    return out


def ctbc() -> pd.DataFrame:
    """照官網前端的流程：home/AuthToken 拿 token → etf/ETFList 拿 {ETF_ID, FID} → 逐檔 etf/ETFHoldingWeight。"""
    def call(path: str, body: dict, token: str = CTBC_SITE):
        return _req("POST", CTBC_API + path, params={"token": token}, json_body={"token": token, **body}, retries=1)

    lst = call("etf/ETFList", {"IsWithETF": "Y"})
    funds = [(str(x.get("ETF_ID") or "").strip(), str(x.get("FID") or "").strip())
             for x in (((lst or {}).get("Data") or {}).get("Data") or [])]
    funds = [(c, f) for c, f in funds if c and f and not _skip_code(c)]
    if not funds:
        log.warning("中信 ETF 清單解析失敗（前 200 字）：%s", _snip(lst))
        return pd.DataFrame(columns=COLS)
    tok = ((((call("home/AuthToken", {}) or {}).get("Data")) or {}).get("token")) or CTBC_SITE
    rows: list[dict] = []
    for etf, fid in funds:
        start = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        p = call("etf/ETFHoldingWeight", {"FID": fid, "StartDate": start}, tok)
        got = parse_ctbc(etf, p)
        if not got:
            log.info("中信 %s 沒有股票持股（前 200 字）：%s", etf, _snip(p))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 元大（yuantaetfs.com）
YUANTA_PCF = "https://www.yuantaetfs.com/tradeInfo/pcf/{code}"


class _JS:
    """極小的 JS 字面值解析器 —— 只為了讀 Nuxt SSR 的 window.__NUXT__。

    元大 PCF 頁是 Nuxt 伺服器端渲染，資料不走 XHR，而是包在
    `window.__NUXT__=(function(a,b,...){return {...}}(值1,值2,...))` 裡；重複出現的值被抽成參數。
    這裡只認：字串、數字、true/false/null/void 0、Array(n)、陣列、物件（鍵可不加引號）、識別字（查參數表）。
    其他語法（函式呼叫、運算式）一律丟例外，由呼叫端記 log 後放棄這一檔。"""

    def __init__(self, s: str, env: dict | None = None):
        self.s, self.i, self.env = s, 0, env or {}

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self.i += 1

    def val(self):
        self.ws()
        c = self.s[self.i]
        if c == '"' or c == "'":
            return self.string()
        if c == "[":
            return self.arr()
        if c == "{":
            return self.obj()
        m = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?").match(self.s, self.i)
        if m:
            self.i = m.end()
            t = m.group(0)
            return float(t) if any(x in t for x in ".eE") else int(t)
        m = re.compile(r"[A-Za-z_$][\w$]*").match(self.s, self.i)
        if m:
            w = m.group(0)
            self.i = m.end()
            if w == "true":
                return True
            if w == "false":
                return False
            if w == "null":
                return None
            if w == "void":
                self.ws()
                self.val()
                return None
            if w == "Array" and self.s[self.i] == "(":
                j = self.s.index(")", self.i)
                n = int(self.s[self.i + 1:j] or 0)
                self.i = j + 1
                return [None] * n
            return self.env.get(w)
        raise ValueError(f"看不懂的 JS 在 {self.i}：{self.s[self.i:self.i + 40]!r}")

    def string(self):
        q = self.s[self.i]
        j = self.i + 1
        buf = []
        esc = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
        while self.s[j] != q:
            if self.s[j] == "\\":
                n = self.s[j + 1]
                if n == "u":
                    buf.append(chr(int(self.s[j + 2:j + 6], 16)))
                    j += 6
                    continue
                if n == "x":
                    buf.append(chr(int(self.s[j + 2:j + 4], 16)))
                    j += 4
                    continue
                buf.append(esc.get(n, n))
                j += 2
            else:
                buf.append(self.s[j])
                j += 1
        self.i = j + 1
        return "".join(buf)

    def arr(self):
        self.i += 1
        out = []
        while True:
            self.ws()
            if self.s[self.i] == "]":
                self.i += 1
                return out
            out.append(self.val())
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1

    def obj(self):
        self.i += 1
        out = {}
        while True:
            self.ws()
            if self.s[self.i] == "}":
                self.i += 1
                return out
            if self.s[self.i] in "\"'":
                k = self.string()
            else:
                m = re.compile(r"[\w$]+").match(self.s, self.i)
                k = m.group(0)
                self.i = m.end()
            self.ws()
            self.i += 1  # ':'
            out[k] = self.val()
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1


def _nuxt_env(page: str) -> tuple[str, dict]:
    """回 (函式本體, 參數表)。"""
    k = page.index("window.__NUXT__=")
    end = page.index("</script>", k)
    s = page[k:end]
    p0 = s.index("(function(") + len("(function(")
    p1 = s.index(")", p0)
    params = [x.strip() for x in s[p0:p1].split(",") if x.strip()]
    tail = s.rstrip().rstrip(";")
    assert tail.endswith("))"), "結尾不是 }(…))"
    a0 = tail.rindex("}(") + 2
    args = _JS("[" + tail[a0:-2] + "]").val()
    return s[p1:a0], dict(zip(params, args))


def _nuxt_pick(body: str, key: str, env: dict):
    k = body.find(key + ":")
    if k < 0:
        return None
    return _JS(body[k + len(key) + 1:], env).val()


def parse_yuanta(etf: str, page: str) -> list[dict]:
    """元大 PCF 頁（Nuxt SSR）：
    - 優先讀 `.FundWeights={Summary, StockWeights:[{code, name, weights（%）, qty（基金持有總股數）}]}`
      —— 2026-10-07 實測 00713（現金申贖型）有這段；
    - 沒有的話退回 `.InKind={FundComposition:[{stkcd, name, qty（每一申購基數的股數）}]}`（實物申贖型，0050 等），
      shares＝qty × 已發行單位數 ÷ 基數單位數，weight 留空由 build_payload 用股數×收盤價推算。
    日期一律用 `.PCF.trandate`（淨值日）。"""
    body, env = _nuxt_env(page)
    m = re.search(r"\.PCF=\{", body)          # 另有一個 .PCF=[...]（欄位說明），只認物件那個
    pcf = _JS(body[m.end() - 1:], env).val() if m else {}
    day = _iso(pcf.get("trandate")) or _iso(pcf.get("upddate"))
    src = YUANTA_PCF.format(code=etf)
    out = []
    m = re.search(r"\.FundWeights=\{", body)
    fw = _JS(body[m.end() - 1:], env).val() if m else {}
    for s in (fw or {}).get("StockWeights") or []:
        if isinstance(s, dict) and s.get("code"):
            out.append({"date": day, "etf": etf, "code": str(s.get("code")).strip(), "name": str(s.get("name") or "").strip(),
                        "weight": _num(s.get("weights")), "shares": _num(s.get("qty")), "issuer": "元大", "src": src})
    if out:
        return out
    comp = _nuxt_pick(body, "FundComposition", env) or []
    os_, base = _num(pcf.get("osunit")), _num(pcf.get("baseunit"))
    mult = os_ / base if os_ and base else None
    for s in comp if isinstance(comp, list) else []:
        if not isinstance(s, dict):
            continue
        q = _num(s.get("qty"))
        out.append({"date": day, "etf": etf, "code": str(s.get("stkcd") or "").strip(), "name": str(s.get("name") or "").strip(),
                    "weight": None, "shares": (q * mult if q is not None and mult else None), "issuer": "元大", "src": src})
    return out


def yuanta(codes: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for c in codes:
        if _skip_code(c):
            continue
        page = _req("GET", YUANTA_PCF.format(code=c), expect="text")
        if not page:
            continue
        try:
            got = parse_yuanta(c, page)
        except Exception as exc:  # noqa: BLE001 —— 版型一改就會進來，記下來讓人修
            k = page.find("FundComposition")
            log.warning("元大 %s 解析失敗：%s；FundComposition 附近前 200 字：%s", c, exc, _snip(page[max(0, k):]))
            continue
        if not got:
            k = page.find("InKind")
            k2 = page.find("stkcd")
            log.info("元大 %s 沒有實物申購清單（現金申贖型？）InKind 附近：%s ／ stkcd 附近：%s", c,
                     page[max(0, k - 50):k + 300].replace("\n", " ") if k >= 0 else "無",
                     page[max(0, k2 - 300):k2 + 300].replace("\n", " ") if k2 >= 0 else "無")
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 第一金（fsitc.com.tw）
# 2026-10-07 Actions 真瀏覽器實測：基金頁 FundDetail.aspx?ID=xxx 載入後 POST WebAPI.aspx/Get_hd {pStrFundID, pStrDate:''}，
# 回 {"d": "<JSON 字串>"}，每列 {fundid, sdate（持股日）, group, A 代號, B 名稱, C 權重%, D 股數}；group=1 是股票。
# 債券型（00834B、00981B）這支只給「債券 96.56%」這種類別彙總，沒有逐檔債券，所以只收股票型。
# 官網沒有「ETF 代號 → 內部 ID」的 API（ETFList／FundList 頁只有名稱連結），對照表手寫；
# 依據：首頁淨值表的連結文字（例「第一金臺灣工業菁英30 ETF基金 → ID=D90」）與首頁橫幅「【00408A】… → ID=183」。
FSITC_HD = "https://www.fsitc.com.tw/WebAPI.aspx/Get_hd"
FSITC_IDS = {"00728": "D90", "00408A": "183", "00994A": "182", "00910": "167"}


def parse_fsitc(etf: str, payload: Any) -> list[dict]:
    try:
        rows = json.loads((payload or {}).get("d") or "[]")
    except (ValueError, AttributeError):
        return []
    out = []
    for r in rows if isinstance(rows, list) else []:
        if str(r.get("group")) != "1":
            continue
        code = str(r.get("A") or "").strip()
        if not code:
            continue
        out.append({"date": _iso(r.get("sdate")), "etf": etf, "code": code, "name": str(r.get("B") or "").strip(),
                    "weight": _num(r.get("C")), "shares": _num(r.get("D")), "issuer": "第一金", "src": FSITC_HD})
    return out


def fsitc() -> pd.DataFrame:
    rows: list[dict] = []
    for etf, fid in FSITC_IDS.items():
        p = _req("POST", FSITC_HD, json_body={"pStrFundID": fid, "pStrDate": ""})
        got = parse_fsitc(etf, p) if p else []
        if p and not got:
            log.warning("第一金 %s（ID=%s）解析不到股票（前 200 字）：%s", etf, fid, _snip(p))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 聯博（abfunds.com.tw → webapi.alliancebernstein.com）
# 2026-10-07 實測：申購買回清單頁 pcf.<ISIN>.html 背後打 GET webapi.alliancebernstein.com/v2/funds/tw/zh-tw/investor/<ISIN>/holdings，
# 回 domesticHoldings[{asOfDate "MM/DD/YYYY", holdingCategory, holdings[{holding 名稱, holdingCode, holdingPerc %, holdingShares}]}]。
# 股票型（00404A）holdingCode 就是台股代號；債券型（00980D、00984D）是債券 ISIN —— 照 Andy 的要求一樣收（前端顯示名稱＋權重）。
# 期貨／現金類別不收（那是避險部位，不是成分）。
AB_HOLD = "https://webapi.alliancebernstein.com/v2/funds/tw/zh-tw/investor/{isin}/holdings"


def tw_isin(code: str) -> str:
    """台灣證券 ISIN：TW + 9 碼（000 + 代號，右補 0 到 6 碼）+ 檢查碼（ISO 6166，字母轉數字後 Luhn）。
    例：0050 → TW0000050004、00404A → TW00000404A5（聯博官網網址實際用的就是這個）。"""
    body = "TW" + ("000" + str(code).strip().upper().ljust(6, "0"))[:9]
    digits = "".join(str(int(ch, 36)) for ch in body)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            d = d - 9 if d > 9 else d
        total += d
    return body + str((10 - total % 10) % 10)


def _tw_code_from_isin(s: str) -> str:
    s = str(s or "").strip()
    if re.fullmatch(r"TW000[0-9A-Z]{6}\d", s):
        core = s[5:11]
        return core[:4] if core[4:] == "00" else core
    return s


def parse_ab(etf: str, payload: Any) -> list[dict]:
    out = []
    for sec in (payload or {}).get("domesticHoldings") or [] if isinstance(payload, dict) else []:
        cat = str(sec.get("holdingCategory") or "")
        if any(k in cat for k in ("futures", "cash", "forward", "swap", "option")):
            continue
        day = _iso(re.sub(r"^(\d\d)/(\d\d)/(\d{4})$", r"\3-\1-\2", str(sec.get("asOfDate") or "")))
        for h in sec.get("holdings") or []:
            code = _tw_code_from_isin(h.get("holdingCode"))
            if not code:
                continue
            out.append({"date": day, "etf": etf, "code": code, "name": str(h.get("holding") or "").strip(),
                        "weight": _num(h.get("holdingPerc")), "shares": _num(h.get("holdingShares")),
                        "issuer": "聯博", "src": AB_HOLD.format(isin=tw_isin(etf))})
    return out


def ab(codes: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for c in codes:
        p = _req("GET", AB_HOLD.format(isin=tw_isin(c)))
        got = parse_ab(c, p) if p else []
        if p and not got:
            log.warning("聯博 %s 解析不到持股（前 200 字）：%s", c, _snip(p))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 華南永昌（hnfunds.com.tw；舊網域 hnitc.com.tw 憑證已過期、會轉到這裡）
# 2026-10-07 實測：申購買回清單頁（Nuxt）先 POST WEB_API/HN_OW_PROD/Auth/SysLogin（無內容，回公開用 access_token），
# 再 POST ETF/FundList 拿自家 ETF、POST ETF/BuyBack {"ETFID":"009808","DataDate":""}；
# 回 Data.DataDate（申購買回清單適用日）＋ 成分 [{StockNo, StockName, Share, Weight（小數，0.4019＝40.19%）}]。
HN_API = "https://www.hnfunds.com.tw/WEB_API/HN_OW_PROD/"


def _find_rows(obj: Any, key: str) -> list[dict]:
    """在巢狀 JSON 裡找「元素帶 key 的 list」—— 投信常改外層包裝，但成分列的欄位名比較穩。"""
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj) and any(key in x for x in obj):
            return obj
        for x in obj:
            r = _find_rows(x, key)
            if r:
                return r
    elif isinstance(obj, dict):
        for v in obj.values():
            r = _find_rows(v, key)
            if r:
                return r
    return []


def parse_hn(etf: str, payload: Any) -> list[dict]:
    data = (payload or {}).get("Data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return []
    day = _iso(str(data.get("NavDate") or data.get("DataDate") or "")[:10])
    out = []
    for r in _find_rows(data, "StockNo"):
        code = str(r.get("StockNo") or "").strip()
        w = _num(r.get("Weight"))
        if not code:
            continue
        out.append({"date": day, "etf": etf, "code": code, "name": str(r.get("StockName") or "").strip(),
                    "weight": None if w is None else round(w * 100, 4), "shares": _num(r.get("Share")),
                    "issuer": "華南永昌", "src": HN_API + "ETF/BuyBack"})
    return out


def hn(codes: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    try:
        s = http.session()
        # client_id 放在標頭（官網前端寫死的公開用戶端 WFPAPIPublicClient，2026-10-07 真瀏覽器記下的請求標頭）；
        # 少了它會回 200 但 access_token=null、Message="Wrong client id!"。
        tok = s.post(HN_API + "Auth/SysLogin", headers={"client_id": "WFPAPIPublicClient"}, timeout=TIMEOUT)
        token = tok.json().get("access_token") if tok.status_code == 200 else None
        if not token:
            log.warning("華南永昌 SysLogin 拿不到 token：HTTP %s %s", tok.status_code, _snip(tok.text))
            return _frame([])
        hdr = {"Authorization": f"Bearer {token}"}
        for c in codes:
            r = s.post(HN_API + "ETF/BuyBack", json={"ETFID": c, "DataDate": ""}, headers=hdr, timeout=TIMEOUT)
            try:
                p = r.json()
            except ValueError:
                log.warning("華南永昌 %s 不是 JSON：HTTP %s %s", c, r.status_code, _snip(r.text))
                continue
            got = parse_hn(c, p)
            if not got:
                log.warning("華南永昌 %s 解析不到成分（前 200 字）：%s", c, _snip(p))
            rows += got
    except Exception as exc:  # noqa: BLE001
        log.warning("華南永昌 失敗：%s", str(exc)[:200])
    return _frame(rows)


# ───────────────────────────────────────────── 富邦（websys.fsit.com.tw）
# 10-07 早上以為「Pcf.aspx 的 HTML 與 XHR 都找不到成分股」—— 其實 PCF 頁只有申購基數與總價金，
# 成分在同頁「基金資產」按鈕連過去的 Trade/Assets.aspx?stkId=<代號>&lan=TW（伺服器端渲染，不用 API）：
# 「資料日期：2026/10/06」＋ 每個資產類別一個 <h6>股票|債券|期貨|附買回債券</h6> 加一張表，
# 列＝[代碼, 名稱, 股數／面額／口數, 金額, 權重(%)]。股票、債券都收（債券照 Andy 的要求顯示名稱＋權重），期貨與附買回不算成分。
FUBON_ASSETS = "https://websys.fsit.com.tw/FubonETF/Trade/Assets.aspx"
_FUBON_KEEP = ("股票", "債券")


def _cells(tr: str) -> list[str]:
    return [_html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]


def parse_fubon(etf: str, page: str) -> list[dict]:
    if not isinstance(page, str):
        return []
    # 不認得的 stkId（已下市的 0058／0059、或 00625K 這種期貨型）官網不報錯，而是回「預設的那一檔」——
    # 2026-10-07 實測 0058、0059、00625K、00717 拿到同一份 231 列。所以頁首 <h6 class="top…">代號 名稱</h6> 必須等於要的代號。
    t = re.search(r'<h6[^>]*class="top[^"]*"[^>]*>\s*([0-9A-Z]+)\s', page)
    if t and t.group(1) != etf:
        log.info("富邦 %s 官網回的是 %s 的頁面（代號不認得），略過", etf, t.group(1))
        return []
    m = re.search(r"資料日期[：:]\s*(\d{4}/\d{1,2}/\d{1,2})", page)
    day = _iso(m.group(1)) if m else None
    out = []
    parts = re.split(r"<h6[^>]*>\s*([^<]+?)\s*</h6>", page)
    for i in range(1, len(parts) - 1, 2):
        kind, body = parts[i], parts[i + 1]
        if kind not in _FUBON_KEEP:            # 期貨、附買回債券、現金…
            continue
        tb = re.search(r"<table.*?</table>", body, re.S)
        if not tb:
            continue
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tb.group(0), re.S)[1:]:   # 第一列是表頭
            c = _cells(tr)
            if len(c) < 5 or not c[0] or "合計" in c[0] or not c[1]:     # 表尾「股票合計」列不是成分
                continue
            out.append({"date": day, "etf": etf, "code": c[0], "name": c[1], "weight": _num(c[4]), "shares": _num(c[2]),
                        "issuer": "富邦", "src": f"{FUBON_ASSETS}?stkId={etf}&lan=TW"})
    return out


def fubon(codes: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for c in codes:
        if re.search(r"[LR]$", c):              # 槓桿／反向：資產是期貨，沒有成分可列
            continue
        page = _req("GET", FUBON_ASSETS, params={"stkId": c, "lan": "TW"}, expect="text")
        got = parse_fubon(c, page) if page else []
        if page and not got and "期貨" not in page:
            log.warning("富邦 %s 解析不到股票／債券表（前 200 字）：%s", c, _snip(page))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 台新（tsit.com.tw；含併入的原新光投信 ETF）
# 2026-10-07 實測：申購買回清單頁的下拉選單在 Pcf.js 裡是 location.href = "/ETF/Home/Pcf/<代號>?FundType=ALL&DataDate="，
# 伺服器端渲染：「日期：<input id=PUB_DATE value=2026-10-08>」＋ 每個資產類別一張卡片
# <div class="card-header">…股票|債券|期貨</div> 後面一張表，表頭決定欄位（股票：代號「2330 TT」／名稱／股數／持股權重「39.1444%」；
# 債券：代號／名稱／面額／市值／權重(%)）。股票、債券都收；期貨不算成分。
TSIT_PCF = "https://www.tsit.com.tw/ETF/Home/Pcf/{code}"


def parse_tsit(etf: str, page: str) -> list[dict]:
    if not isinstance(page, str):
        return []
    m = re.search(r'id="PUB_DATE"[^>]*value="([0-9-]{8,10})"', page)
    day = _iso(m.group(1)) if m else None
    t = re.search(r"<h4>[^<]*\((\w+)\)\s*</h4>", page)
    if t and t.group(1) != etf:
        log.info("台新 %s 官網回的是 %s 的頁面，略過", etf, t.group(1))
        return []
    out = []
    for hdr, rest in re.findall(r'<div class="card-header[^"]*">(.*?)</div>(.*?)(?=<div class="card-header|$)', page, re.S):
        kind = re.sub(r"<[^>]+>", "", hdr).strip()
        if kind not in ("股票", "債券"):
            continue
        tb = re.search(r"<table.*?</table>", rest, re.S)
        if not tb:
            continue
        head = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", tb.group(0), re.S)]
        ix = {k: next((i for i, h in enumerate(head) if any(w in h for w in ws)), None)
              for k, ws in (("code", ("代號",)), ("name", ("名稱",)), ("qty", ("股數", "面額")), ("w", ("權重",)))}
        if ix["code"] is None or ix["w"] is None:
            log.warning("台新 %s %s 表頭對不上：%s", etf, kind, head)
            continue
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tb.group(0), re.S):
            c = _cells(tr)
            if len(c) <= max(v for v in ix.values() if v is not None):
                continue
            code = re.sub(r"\s+TT$", "", c[ix["code"]])          # 台股寫成「2330 TT」
            if not code:
                continue
            out.append({"date": day, "etf": etf, "code": code, "name": c[ix["name"]] if ix["name"] is not None else "",
                        "weight": _num(c[ix["w"]]), "shares": _num(c[ix["qty"]]) if ix["qty"] is not None else None,
                        "issuer": "台新", "src": TSIT_PCF.format(code=etf)})
    return out


def tsit(codes: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for c in codes:
        if re.search(r"[LR]$", c):
            continue
        # 2026-10-07 實測：連打二十幾頁後官網會間歇回一張「<title>Error</title>」的錯誤頁（00936、00775B 單獨打是好的），
        # 所以每頁之間停 1 秒、遇到錯誤頁停 5 秒再試一次 —— 整輪多花半分鐘，換掉一半的漏抓。
        page = None
        for wait in (1, 5):
            time.sleep(wait)
            page = _req("GET", TSIT_PCF.format(code=c), params={"FundType": "ALL", "DataDate": ""}, expect="text")
            if not (isinstance(page, str) and "<title>Error</title>" in page):
                break
        got = parse_tsit(c, page) if page else []
        if page and not got:
            log.warning("台新 %s 解析不到股票／債券表（前 200 字）：%s", c, _snip(page))
        rows += got
    return _frame(rows)


# ───────────────────────────────────────────── 總入口
ISSUER_PREFIX = {  # 從 ETF 簡稱判斷發行投信（給「哪些已接上／哪些沒接上」用）
    "元大": "元大", "國泰": "國泰", "群益": "群益", "富邦": "富邦", "統一": "統一", "凱基": "凱基", "大華": "大華銀",
    "復華": "復華", "中信": "中國信託", "野村": "野村", "兆豐": "兆豐", "第一金": "第一金", "新光": "新光", "台新": "台新",
    "永豐": "永豐", "聯博": "聯博", "摩根": "摩根", "街口": "街口", "富蘭克林": "富蘭克林", "安聯": "安聯", "玉山": "玉山",
    "華南永昌": "華南永昌", "貝萊德": "貝萊德", "宏利": "宏利", "路博邁": "路博邁", "富達": "富達", "柏瑞": "柏瑞", "保德信": "保德信",
    "FT": "富蘭克林華美", "聯邦": "聯邦",   # FT＝富蘭克林華美（00899 全名「富蘭克林華美全球潔淨能源ETF」）
    "台灣": None,
}
CONNECTED = {"群益", "野村", "復華", "統一", "元大", "凱基", "國泰", "中國信託", "第一金", "聯博", "華南永昌", "富邦", "台新"}
# 還沒接上的投信 → 給讀者看的原因（前端成分股分頁照抄）。查證過程、關鍵字與來源在 docs/etf_holdings_coverage.md。
# 寫「為什麼抓不到」而不是「尚未接上」：Andy 2026-10-07 問「為何有 ETF 沒有成分股」，答案要在畫面上。
NOT_CONNECTED_WHY = {
    "兆豐": "兆豐投信官網擋雲端主機的連線（2026-10-07 實測回 403 Access Denied），自動排程抓不到，只能人工整理。",
    "大華銀": "大華銀投信官網的 HTTPS 憑證鏈不完整（伺服器沒附中繼憑證），程式驗證憑證會失敗；在補上憑證前不關掉驗證硬抓。",
    "永豐": "永豐投信官網的 ETF 持股公告頁還沒找到可以穩定取用的位置（2026-10-07 查過官網首頁與 ETF 路徑都沒有）。",
    "玉山": "玉山投信（2026 年由保德信投信更名）新官網的申購買回清單位置還沒查到。",
    "貝萊德": "貝萊德官網在自動排程的主機上開頁逾時，持股頁還沒接上。",
    "安聯": "安聯投信官網找得到，但 ETF 申購買回清單的資料位置還沒查到。",
    "摩根": "摩根投信官網 ETF 區還沒查到每日持股的資料位置。",
    "富蘭克林華美": "富蘭克林華美投信官網在自動排程的主機上開頁逾時，持股頁還沒接上。",
    "聯邦": "聯邦投信官網在自動排程的主機上開頁逾時，持股頁還沒接上。",
    "街口": "街口投信的 ETF 都是期貨型，持有的是期貨契約，沒有股票成分。",
}


def issuer_of(name: str) -> str | None:
    n = re.sub(r"^(主動|平衡|期)", "", str(name or ""))   # 主動式／平衡型（00980T）／期貨信託（期元大…）前綴
    for k, v in ISSUER_PREFIX.items():
        if v and n.startswith(k):
            return v
    return None


def fetch_all(etf_names: dict[str, str]) -> pd.DataFrame:
    """抓所有已接上的投信。etf_names＝{代號: 簡稱}（company_info 裡 industry=ETF 的那些），
    元大／野村沒有「列出自家 ETF」的公開 API，用簡稱判斷發行商後逐檔打。"""
    by = {}
    for c, n in etf_names.items():
        by.setdefault(issuer_of(n), []).append(c)
    jobs: list[tuple[str, Callable[[], pd.DataFrame]]] = [
        ("群益", capital), ("復華", fuhhwa), ("統一", uni), ("凱基", lambda: kgi(etf_names)), ("國泰", cathay), ("中國信託", ctbc),
        ("野村", lambda: nomura(sorted(by.get("野村", [])))),
        ("元大", lambda: yuanta(sorted(by.get("元大", [])))),
        ("第一金", fsitc), ("聯博", lambda: ab(sorted(by.get("聯博", [])))),
        ("華南永昌", lambda: hn(sorted(by.get("華南永昌", [])))),
        ("富邦", lambda: fubon(sorted(by.get("富邦", [])))),
        ("台新", lambda: tsit(sorted(by.get("台新", []) + by.get("新光", [])))),
    ]
    frames = []
    for name, fn in jobs:
        try:
            df = fn()
        except Exception as exc:  # noqa: BLE001 —— 一家掛掉不影響其他家
            log.exception("ETF PCF %s 失敗：%s", name, exc)
            df = pd.DataFrame(columns=COLS)
        log.info("ETF PCF %s：%d 檔、%d 列", name, df["etf"].nunique() if len(df) else 0, len(df))
        frames.append(df)
    out = pd.concat([f for f in frames if len(f)], ignore_index=True) if any(len(f) for f in frames) else pd.DataFrame(columns=COLS)
    return out


if __name__ == "__main__":  # 在 Actions 上手動自我測試：python -m pipeline.sources.etf_pcf
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from ..util import store

    ci = store.read("company_info")
    m = ci["industry"].isin(["ETF", "上櫃ETF"]) if len(ci) else None
    names = dict(zip(ci.loc[m, "code"], ci.loc[m, "name"])) if len(ci) else {}
    only = sys.argv[1:]
    if only:
        names = {c: n for c, n in names.items() if issuer_of(n) in only or c in only}
    df = fetch_all(names)
    print("合計", len(df), "列，", df["etf"].nunique() if len(df) else 0, "檔")
    for etf, g in df.groupby("etf"):
        print(f"  {etf} {g['issuer'].iloc[0]} {g['date'].iloc[0]} {len(g)} 檔 權重合計 {g['weight'].sum():.1f} 前三：",
              g.sort_values('weight', ascending=False).head(3)[['code', 'name', 'weight', 'shares']].values.tolist())
