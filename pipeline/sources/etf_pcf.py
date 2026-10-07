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


def kgi_fund_ids(page_html: str) -> dict[str, str]:
    """申購買回清單頁的基金下拉選單：<option value="J024">009816 凱基台灣TOP50</option> → {009816: J024}。"""
    out = {}
    for m in re.finditer(r'<option[^>]*value="([A-Za-z]\d+)"[^>]*>([^<]*)</option>', page_html or ""):
        c = re.search(r"\b(\d{4,6}[A-Z]?)\b", _html.unescape(m.group(2)))
        if c:
            out[c.group(1)] = m.group(1)
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


def kgi() -> pd.DataFrame:
    page = _req("GET", KGI_PAGE, expect="text")
    ids = kgi_fund_ids(page or "")
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
    """{ETF 代號: fundCode}。清單 API 分頁（41 檔／5 頁），分頁參數名以實測為準；拿不到的頁就算了，記 log。"""
    out: dict[str, str] = {}
    for params in ({},) + tuple({"pageIndex": i, "pageSize": 100} for i in (1,)) + tuple({"page": i} for i in range(2, 7)):
        lst = _req("GET", CATHAY_LIST, params=params or None, retries=1)
        for r in (lst or {}).get("result") or []:
            c, f = str(r.get("stockCode") or "").strip(), str(r.get("fundCode") or "").strip()
            if c and f:
                out[c] = f
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
    """元大 PCF 頁：PCF.trandate（淨值日）、osunit／baseunit、InKind.FundComposition[{stkcd,name,qty}]。

    元大只給「每一實物申購基數（baseunit 單位）要交付的股數」，沒有權重：
    - shares＝qty × 已發行單位數 ÷ 基數單位數（換算成整檔基金的持股）
    - weight 留空，由 build_payload 用股數×收盤價推算（頁面標註「依股數×收盤價推算」）。"""
    body, env = _nuxt_env(page)
    m = re.search(r"\.PCF=\{", body)          # 另有一個 .PCF=[...]（欄位說明），只認物件那個
    pcf = _JS(body[m.end() - 1:], env).val() if m else {}
    comp = _nuxt_pick(body, "FundComposition", env) or []
    day = _iso(pcf.get("trandate")) or _iso(pcf.get("upddate"))
    os_, base = _num(pcf.get("osunit")), _num(pcf.get("baseunit"))
    mult = os_ / base if os_ and base else None
    out = []
    for s in comp:
        if not isinstance(s, dict):
            continue
        q = _num(s.get("qty"))
        out.append({"date": day, "etf": etf, "code": str(s.get("stkcd") or "").strip(), "name": str(s.get("name") or "").strip(),
                    "weight": None, "shares": (q * mult if q is not None and mult else None),
                    "issuer": "元大", "src": YUANTA_PCF.format(code=etf)})
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


# ───────────────────────────────────────────── 總入口
ISSUER_PREFIX = {  # 從 ETF 簡稱判斷發行投信（給「哪些已接上／哪些沒接上」用）
    "元大": "元大", "國泰": "國泰", "群益": "群益", "富邦": "富邦", "統一": "統一", "凱基": "凱基", "大華": "大華銀",
    "復華": "復華", "中信": "中國信託", "野村": "野村", "兆豐": "兆豐", "第一金": "第一金", "新光": "新光", "台新": "台新",
    "永豐": "永豐", "聯博": "聯博", "摩根": "摩根", "街口": "街口", "富蘭克林": "富蘭克林", "安聯": "安聯", "玉山": "玉山",
    "華南永昌": "華南永昌", "貝萊德": "貝萊德", "宏利": "宏利", "路博邁": "路博邁", "富達": "富達", "柏瑞": "柏瑞", "保德信": "保德信",
    "台灣": None,
}
CONNECTED = {"群益", "野村", "復華", "統一", "元大", "凱基", "國泰"}


def issuer_of(name: str) -> str | None:
    n = re.sub(r"^主動", "", str(name or ""))
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
        ("群益", capital), ("復華", fuhhwa), ("統一", uni), ("凱基", kgi), ("國泰", cathay),
        ("野村", lambda: nomura(sorted(by.get("野村", [])))),
        ("元大", lambda: yuanta(sorted(by.get("元大", [])))),
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
    names = dict(zip(ci.loc[ci["industry"].eq("ETF"), "code"], ci.loc[ci["industry"].eq("ETF"), "name"])) if len(ci) else {}
    only = sys.argv[1:]
    if only:
        names = {c: n for c, n in names.items() if issuer_of(n) in only or c in only}
    df = fetch_all(names)
    print("合計", len(df), "列，", df["etf"].nunique() if len(df) else 0, "檔")
    for etf, g in df.groupby("etf"):
        print(f"  {etf} {g['issuer'].iloc[0]} {g['date'].iloc[0]} {len(g)} 檔 權重合計 {g['weight'].sum():.1f} 前三：",
              g.sort_values('weight', ascending=False).head(3)[['code', 'name', 'weight', 'shares']].values.tolist())
