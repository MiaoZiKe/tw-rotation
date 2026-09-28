"""公司 Logo 的第二來源：Wikidata 的「標誌圖片」（P154）＋ Wikimedia Commons 的圖檔（第四版，2026-09-28）。

為什麼加這個來源（DECISIONS #271、docs/logo_sources.md §1.3）
------------------------------------------------------------
Andy 2026-09-28：「我發現有個股還是沒有公司 Logo」（例：8038 長園科）。第三版之後還缺 315 家：
none 168、robots 89、too_small 51、blank 6、generic 1；另有 109 家只有 16～47px 的低解析 favicon。
官網那條路能做的都做了，缺的要從**別的合規來源**補。Commons 是公開授權的圖庫：

- 圖是志願者上傳、逐張標了授權的，**授權資訊是機器可讀的**（imageinfo 的 extmetadata）。
- 我們只收**授權明確可再利用**的：公有領域（PD，Logo 最常見的是 PD-textlogo —— 只有字與簡單幾何形狀，
  未達著作權的原創性門檻）、CC0、CC BY、CC BY-SA。其他（GFDL 單授權、FAL、沒寫授權的……）一律不收。
  CC BY／BY-SA 要署名：檔名、作者、授權、出處頁全部記進索引的 `attribution`，並產出 `data/logos/ATTRIBUTION.md`。
- **它不是去爬公司官網**，所以不受官網 robots.txt 影響：robots.txt 管的是「對那個網站的自動存取」，
  我們沒有碰那個網站；Commons 自己的 API 規範（User-Agent、流量）我們照守。
  這跟第三版不採用 DuckDuckGo／Google 替我們去抓官網的圖**性質不同** —— 那是請第三方代替我們去存取對方的網站
  （等於繞過對方的存取控制）；Commons 的圖是人工上傳、帶授權的獨立副本。
- ⚠ 著作權自由 ≠ 商標自由。Commons 的 Logo 多半同時掛 {{trademarked}}：著作權上可以用，但仍是各公司的商標。
  我們的用法跟官網來源一樣是「指示性使用」（docs/logo_sources.md §3），這一點沒有因為換來源而改變。

怎麼找到那家公司的條目
----------------------
1. **證券代號**：條目的「證券交易所」（P414）陳述帶「股票代號」（P249）修飾，交易所在台灣（P17＝Q865）。
   排除 deprecated 等級、以及有「結束時間」（P582）修飾的陳述 —— 下市後代號可能被別家重用。
2. **公司全名**：條目的國家是台灣，中文標籤（zh-tw → zh-hant → zh）去掉「股份有限公司」後跟 company_info 的全名一樣。
   只有上市公司有全名（上櫃的 company_info 沒有），所以上櫃只能靠代號。
   同一個代號／名字對到**兩個不同的圖檔**就放棄（寧可沒有，也不要掛錯公司的 Logo）。
一次 SPARQL 查回「台灣、有 P154 的條目」全部，存進 `data/_state/logo_wikidata.json`，7 天重查一次（DECISIONS #155）。

規範（2026-09-28 WebSearch 查證，原文點不進去，見 docs/logo_sources.md §1.3）
--------------------------------------------------------------------------
- Wikimedia User-Agent 政策：要能辨識、附聯絡方式 → `config.LOGO_WIKIMEDIA_UA`（repo 網址；不放個人 email）。
- Wikidata Query Service：每個「UA＋IP」每 60 秒 60 秒的查詢時間、每 IP 5 個並行、超過回 429＋Retry-After。
  我們一輪只查一次（有快取時零次）。
- Wikimedia API：匿名每 IP 每小時約 500 次；GitHub Actions 的 IP 是共用的，所以每輪最多下載
  `config.LOGO_WIKIMEDIA_MAX_PER_RUN` 張、序列抓、每次間隔 `LOGO_WIKIMEDIA_PAUSE_SEC` 秒；帶 `maxlag=5`。
  收到 429／503 就**整段收手**，下一輪再來。
- Commons 縮圖只接受標準寬度（…120、250、330、500…），用 250。SVG 由 Commons 自己算繪成 PNG，不需要 cairosvg。

每一個函式都「失敗就回空並記 log」，不讓 Wikimedia 掛掉拖垮一整輪 Logo。
"""
from __future__ import annotations

import html
import json
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import unquote, urlencode

from .. import config
from ..util import http
from ..util.roc import clean_code

log = logging.getLogger(__name__)

TAIPEI = timezone(timedelta(hours=8))

# 台灣＝Q865；台灣證券交易所＝Q548621（WebSearch 摘要，另以「交易所的國家是台灣」兜底，任一成立即可）
SPARQL = """
SELECT DISTINCT ?item ?logo ?ticker ?label WHERE {
  ?item wdt:P154 ?logo .
  {
    ?item p:P414 ?st .
    ?st ps:P414 ?ex ; pq:P249 ?ticker ; wikibase:rank ?rk .
    FILTER(?rk != wikibase:DeprecatedRank)
    FILTER NOT EXISTS { ?st pq:P582 ?end }
    { ?ex wdt:P17 wd:Q865 } UNION { VALUES ?ex { wd:Q548621 } }
  } UNION {
    ?item wdt:P17 wd:Q865 .
    ?item rdfs:label ?label .
    FILTER(LANG(?label) IN ("zh-tw", "zh-hant", "zh"))
  }
}
"""

# 收的授權（DECISIONS #271）：公有領域、CC0、CC BY、CC BY-SA。任何帶 NC（非商業）、ND（禁止改作）的都不收 ——
# 我們要縮放成 64px（算改作）而且網站是公開的；GFDL 單授權要求附整份授權全文，也不收。
ALLOWED = ("PD", "CC0", "CC BY", "CC BY-SA")
_CC_CODE = re.compile(r"^cc-by(-sa)?-\d(\.\d)?(-[a-z]{2,})?$")
_CC_SHORT = re.compile(r"^cc by(-sa)? \d(\.\d)?( [a-z]{2,})?$")
_TICKER = re.compile(r"(?<!\d)(\d{4,6}[A-Z]?)(?![\d])")
_SUFFIX = re.compile(r"(股份有限公司|有限公司|公司)$")


class Throttled(Exception):
    """Wikimedia 回 429／503（maxlag）：這輪整段收手。"""


def _headers() -> dict:
    return {"User-Agent": config.LOGO_WIKIMEDIA_UA, "Accept": "application/json"}


def cache_path():
    return config.STATE / config.LOGO_WIKIDATA_CACHE


def _today() -> date:
    return datetime.now(TAIPEI).date()


# ------------------------------------------------------------------ 名稱與檔名

def norm_name(s) -> str:
    """公司名比對用：去空白、全形括號轉半形、臺→台、去掉「股份有限公司／有限公司／公司」結尾。"""
    t = re.sub(r"\s+", "", str(s or "")).replace("（", "(").replace("）", ")").replace("臺", "台")
    return _SUFFIX.sub("", t).lower()


def file_title(url_or_name: str) -> str | None:
    """P154 的值（http://commons.wikimedia.org/wiki/Special:FilePath/Foo%20bar.svg）→ 「File:Foo bar.svg」。"""
    name = unquote(str(url_or_name or "").rsplit("/", 1)[-1]).replace("_", " ").strip()
    if name.lower().startswith("file:"):
        name = name[5:].strip()
    return f"File:{name}" if name else None


def ticker_code(raw) -> str | None:
    """P249 的值常見 `2330`、`2330.TW`、`TPE:2330`、`8038.TWO` → 代號；抽不出來回 None。"""
    m = _TICKER.search(str(raw or "").upper())
    return clean_code(m.group(1)) if m else None


# ------------------------------------------------------------------ Wikidata：代號／名稱 → Commons 檔名

def parse_sparql(raw) -> dict:
    """SPARQL JSON → {"by_code": {代號: [[檔名, Q號], …]}, "by_label": {正規化名稱: [[檔名, Q號], …]}}。壞掉回空。"""
    by_code: dict[str, set] = {}
    by_label: dict[str, set] = {}
    try:
        rows = raw["results"]["bindings"]
    except (KeyError, TypeError):
        return {}
    for b in rows if isinstance(rows, list) else []:
        try:
            f = file_title(b["logo"]["value"])
            q = str(b["item"]["value"]).rsplit("/", 1)[-1]
        except (KeyError, TypeError):
            continue
        if not f:
            continue
        if "ticker" in b:
            c = ticker_code(b["ticker"].get("value"))
            if c:
                by_code.setdefault(c, set()).add((f, q))
        if "label" in b:
            k = norm_name(b["label"].get("value"))
            if len(k) >= 2:
                by_label.setdefault(k, set()).add((f, q))
    return {"by_code": {k: sorted(map(list, v)) for k, v in by_code.items()},
            "by_label": {k: sorted(map(list, v)) for k, v in by_label.items()}}


def _query_wikidata() -> dict:
    url = config.LOGO_WIKIDATA_SPARQL + "?" + urlencode({"query": SPARQL, "format": "json"})
    res = http.get_bytes(url, headers={**_headers(), "Accept": "application/sparql-results+json"},
                         timeout=70, max_bytes=30_000_000)
    if res is None:
        log.warning("Wikidata 查詢連線失敗，這輪不用 Wikimedia 來源")
        return {}
    status, body, _ct, _final = res
    if status == 429 or status >= 500:
        log.warning("Wikidata 查詢回 HTTP %s（限流或伺服器忙），這輪不用 Wikimedia 來源", status)
        return {}
    try:
        raw = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        log.warning("Wikidata 查詢回應解析失敗（HTTP %s，回應前 200 字）：%s", status,
                    body[:200].decode("utf-8", errors="replace"))
        return {}
    m = parse_sparql(raw)
    if not m:
        log.warning("Wikidata 查詢回應沒有 results.bindings（回應前 200 字）：%s",
                    body[:200].decode("utf-8", errors="replace"))
    return m


def load_map(today: date | None = None, *, refresh: bool | None = None) -> dict:
    """讀快取；超過 7 天（或沒有）才重查一次。重查失敗就用舊的（再舊也比沒有好），都沒有回 {}。"""
    today = today or _today()
    p = cache_path()
    cached: dict = {}
    if p.exists():
        try:
            cached = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            cached = {}
    try:
        age = (today - date.fromisoformat(str(cached.get("fetched"))[:10])).days
    except ValueError:
        age = 10 ** 6
    if refresh is None:
        refresh = age >= config.LOGO_WIKIDATA_REFRESH_DAYS
    if not refresh and cached.get("by_code") is not None:
        return cached
    m = _query_wikidata()
    if not m:
        return cached if cached.get("by_code") is not None else {}
    m["fetched"] = today.isoformat()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(m, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        log.warning("Wikidata 對照快取寫不進去：%s", exc)
    log.info("Wikidata：有 Logo 的台灣條目，代號對照 %d 筆、名稱對照 %d 筆",
             len(m["by_code"]), len(m["by_label"]))
    return m


def lookup(m: dict, code: str, full_name=None) -> dict | None:
    """找一家公司的 Commons 檔名：代號優先，其次公司全名。同一把鑰匙對到兩個不同圖檔就放棄。"""
    tries = [("ticker", (m.get("by_code") or {}).get(code))]
    if full_name and isinstance(full_name, str):
        tries.append(("name", (m.get("by_label") or {}).get(norm_name(full_name))))
    for how, hits in tries:
        if not hits:
            continue
        files = sorted({h[0] for h in hits})
        if len(files) != 1:
            log.info("Wikidata：%s 用%s對到 %d 個不同圖檔（%s），不猜", code,
                     "代號" if how == "ticker" else "名稱", len(files), "、".join(files[:3]))
            return None
        qs = sorted({h[1] for h in hits})
        return {"file": files[0], "item": qs[0], "match": how}
    return None


# ------------------------------------------------------------------ Commons：授權與縮圖

def _v(ext: dict, key: str) -> str:
    val = (ext or {}).get(key)
    if isinstance(val, dict):
        val = val.get("value")
    return str(val or "").strip()


def strip_html(s) -> str:
    """extmetadata 的 Artist／Credit 常是 HTML（<a href=…>User:X</a>）→ 純文字，最多 200 字。"""
    t = re.sub(r"<[^>]+>", " ", str(s or ""))
    return re.sub(r"\s+", " ", html.unescape(t)).strip()[:200]


def license_of(ext: dict) -> tuple[str | None, str]:
    """授權白名單判定。回 (類別, 授權簡稱)；不收時類別是 None，第二欄是原因。

    看兩個欄位：`License`（機器碼，例 cc-by-sa-4.0、pd、cc0）與 `LicenseShortName`（例 CC BY-SA 4.0、Public domain）。
    兩個都對不上白名單就不收 —— 包含「沒有授權資料」「GFDL」「Attribution（自訂署名）」「CC BY-NC」這些。
    """
    code = _v(ext, "License").lower()
    short = strip_html(_v(ext, "LicenseShortName"))
    s = short.lower()
    if re.search(r"(^|[-\s])(nc|nd)([-\s]|$)", f"{code} {s}"):
        return None, f"授權含非商業／禁止改作：{short or code}"
    if code == "pd" or code.startswith("pd-") or s.startswith("public domain"):
        return "PD", short or "Public domain"
    if code == "cc0" or s.startswith("cc0"):
        return "CC0", short or "CC0"
    for pat, txt in ((_CC_CODE, code), (_CC_SHORT, s)):
        m = pat.match(txt)
        if m:
            return ("CC BY-SA" if m.group(1) else "CC BY"), short or code
    return None, f"授權不在白名單：{short or code or '（沒有授權資料）'}"


def _api(params: dict):
    url = config.LOGO_COMMONS_API + "?" + urlencode({**params, "format": "json", "formatversion": "2",
                                                     "maxlag": "5"})
    res = http.get_bytes(url, headers=_headers(), timeout=20, max_bytes=5_000_000)
    if res is None:
        return None
    status, body, _ct, _final = res
    if status == 429 or status == 503:
        raise Throttled(f"Commons API 回 HTTP {status}")
    try:
        d = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        log.warning("Commons API 回應解析失敗（HTTP %s，回應前 200 字）：%s", status,
                    body[:200].decode("utf-8", errors="replace"))
        return None
    if isinstance(d, dict) and (d.get("error") or {}).get("code") == "maxlag":
        raise Throttled("Commons API maxlag")
    return d


def commons_info(titles: list[str]) -> dict[str, dict]:
    """{File:檔名: {thumb, url, page, mime, w, h, ext}}，50 個一批（API 上限）。拿不到的不列。"""
    out: dict[str, dict] = {}
    titles = sorted(set(t for t in titles if t))
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        if i:
            time.sleep(config.LOGO_WIKIMEDIA_PAUSE_SEC)
        d = _api({"action": "query", "prop": "imageinfo", "redirects": "1",
                  "iiprop": "url|mime|size|extmetadata", "iiurlwidth": str(config.LOGO_COMMONS_THUMB_PX),
                  "iiextmetadatafilter": "License|LicenseShortName|LicenseUrl|Artist|Credit|"
                                         "AttributionRequired|UsageTerms|Restrictions|Copyrighted",
                  "titles": "|".join(batch)})
        q = (d or {}).get("query") or {}
        alias = {}
        for key in ("normalized", "redirects"):
            for n in q.get(key) or []:
                alias[n.get("to")] = n.get("from")
        for pg in q.get("pages") or []:
            ii = (pg.get("imageinfo") or [None])[0]
            if not ii or pg.get("missing"):
                continue
            t = pg.get("title")
            req = t
            while req in alias:          # 正規化／重新導向可能連兩層：接回我們原本問的那個名字
                req = alias[req]
            out[req] = {"thumb": ii.get("thumburl") or ii.get("url"), "url": ii.get("url"),
                        "page": ii.get("descriptionurl"), "mime": ii.get("mime"),
                        "w": ii.get("width"), "h": ii.get("height"),
                        "ext": ii.get("extmetadata") or {}, "title": t}
    return out


def attribution(file: str, info: dict, kind: str, short: str, hit: dict) -> dict:
    """要寫進索引的出處：CC BY／BY-SA 依授權條款必須署名（作者、授權、出處）；PD／CC0 也記，方便查證。"""
    ext = info.get("ext") or {}
    a = {"file": info.get("title") or file, "page": info.get("page"), "license": short, "license_kind": kind,
         "license_url": _v(ext, "LicenseUrl") or None, "artist": strip_html(_v(ext, "Artist")) or None,
         "credit": strip_html(_v(ext, "Credit")) or None, "wikidata": hit.get("item"), "match": hit.get("match")}
    restr = _v(ext, "Restrictions")
    if restr:
        a["restrictions"] = restr        # 例 trademarked：著作權自由，但仍是商標（見檔頭）
    return {k: v for k, v in a.items() if v}


# ------------------------------------------------------------------ 一批公司

def fetch_many(rows: list[dict], reject=frozenset(), deadline: float | None = None,
               today: date | None = None, max_downloads: int | None = None) -> dict[str, dict]:
    """rows＝[{code, domain, full_name}] → {代號: 結果}；只回「查到條目」的代號。絕不拋例外。

    結果 status＝ok 時跟 logos.fetch_logo 同格式（png、orig、src＝"wikimedia"、attribution）；
    不收時 status＝"none"、detail 寫原因（授權不在白名單、太小、太寬……），呼叫端只拿來記 log。
    """
    try:
        return _fetch_many(rows, frozenset(reject or ()), deadline, today, max_downloads)
    except Exception as exc:  # noqa: BLE001
        log.warning("Wikimedia 來源失敗（不影響官網那條路）：%s", exc)
        return {}


def _fetch_many(rows, reject, deadline, today, max_downloads) -> dict[str, dict]:
    from . import logos as lg     # 延後載入：logos 也會 import 這支

    if not rows:
        return {}
    m = load_map(today)
    if not m:
        return {}
    hits = {}
    for r in rows:
        h = lookup(m, r["code"], r.get("full_name"))
        if h:
            hits[r["code"]] = h
    if not hits:
        log.info("Wikimedia：這輪 %d 家缺 Logo，Wikidata 都沒有對得上的條目", len(rows))
        return {}
    try:
        infos = commons_info([h["file"] for h in hits.values()])
    except Throttled as exc:
        log.warning("Wikimedia：%s，這輪收手", exc)
        return {}
    limit = config.LOGO_WIKIMEDIA_MAX_PER_RUN if max_downloads is None else max_downloads
    dom = {r["code"]: r.get("domain") for r in rows}
    out: dict[str, dict] = {}
    got: dict[str, object] = {}      # 同一個檔名只下載一次（金控與子公司常共用一張）
    for code, h in sorted(hits.items()):
        f = h["file"]
        info = infos.get(f)
        if not info:
            out[code] = {"status": "none", "domain": dom[code], "detail": f"Commons 查不到 {f}"}
            continue
        kind, short = license_of(info["ext"])
        if not kind:
            out[code] = {"status": "none", "domain": dom[code], "detail": f"{short}（{f}）"[:200]}
            continue
        if f not in got:
            if len(got) >= limit or (deadline and time.time() >= deadline):
                break
            if got:
                time.sleep(config.LOGO_WIKIMEDIA_PAUSE_SEC)
            got[f] = _download(lg, info)
            if isinstance(got[f], Throttled):
                log.warning("Wikimedia：%s，這輪收手", got[f])
                break
        res = got[f]
        if isinstance(res, lg.LogoReject):
            out[code] = {"status": res.reason if res.reason in ("too_small", "blank") else "none",
                         "domain": dom[code], "detail": f"Commons {res.reason} {res.detail} {f}".strip()[:200]}
            continue
        png, orig = res
        if lg.sha1(png) in reject:
            out[code] = {"status": "generic", "domain": dom[code], "detail": f"預設圖 {f}"}
            continue
        out[code] = {"status": "ok", "domain": dom[code], "src": "wikimedia", "url": info.get("page") or f,
                     "png": png, "orig": list(orig), "attribution": attribution(f, info, kind, short, h)}
    n_ok = sum(1 for r in out.values() if r["status"] == "ok")
    log.info("Wikimedia：缺 Logo %d 家、Wikidata 對到 %d 家、收下 %d 家（下載 %d 張）",
             len(rows), len(hits), n_ok, len(got))
    return out


def _download(lg, info: dict):
    """下載 Commons 縮圖（SVG 由 Commons 算繪成 PNG）→ logos.normalize_image。回 (png, 原圖尺寸) 或 LogoReject。"""
    url = info.get("thumb")
    if not url:
        return lg.LogoReject("none", "沒有圖檔網址")
    res = http.get_bytes(url, headers={"User-Agent": config.LOGO_WIKIMEDIA_UA}, timeout=15, max_bytes=3_000_000)
    if res is None:
        return lg.LogoReject("error", f"連線失敗 {url}")
    status, body, _ct, _final = res
    if status in (429, 503):
        return Throttled(f"Commons 縮圖回 HTTP {status}")
    if status != 200 or not body:
        return lg.LogoReject("none", f"HTTP {status} {url}")
    try:
        # 不做照片判定：P154 本來就是「標誌圖片」屬性，而且縮圖是 Commons 依原比例算的。
        # 只收 ≥32px（第三方來源的標準，跟 Google s2 一樣），長寬比超過 5:1 的橫長字標照樣判太小。
        return lg.normalize_image(body, allow_lowres=False)
    except lg.LogoReject as rej:
        return rej
