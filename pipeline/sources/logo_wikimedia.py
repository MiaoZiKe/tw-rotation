"""公司 Logo 的第二來源：Wikidata 的「標誌圖片」（P154）＋ Wikimedia Commons 的圖檔（第四版，2026-09-28）。

為什麼加這個來源（DECISIONS #276、docs/logo_sources.md §1.3）
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

# 收的授權（DECISIONS #276）：公有領域、CC0、CC BY、CC BY-SA。任何帶 NC（非商業）、ND（禁止改作）的都不收 ——
# 我們要縮放成 64px（算改作）而且網站是公開的；GFDL 單授權要求附整份授權全文，也不收。
# ⚠ CC BY／BY-SA 另外要 config.LOGO_WIKIMEDIA_ALLOW_BY 打開才收（預設關）：署名要做在網站畫面上，前端還沒有出處連結。
ALLOWED = ("PD", "CC0", "Apache", "CC BY", "CC BY-SA")
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
    if code.startswith("apache") or s.startswith("apache"):
        return "Apache", short or "Apache License 2.0"
    for pat, txt in ((_CC_CODE, code), (_CC_SHORT, s)):
        m = pat.match(txt)
        if m:
            return ("CC BY-SA" if m.group(1) else "CC BY"), short or code
    return None, f"授權不在白名單：{short or code or '（沒有授權資料）'}"


def _api(params: dict):
    # 不帶 maxlag（理由同 _wd_api：10-28 回補日誌 Commons 也對 runner 回 503）；503／429 退避重試兩次
    url = config.LOGO_COMMONS_API + "?" + urlencode({**params, "format": "json", "formatversion": "2"})
    status = body = None
    for wait in (0, 5, 15):
        if wait:
            time.sleep(wait)
        res = http.get_bytes(url, headers=_headers(), timeout=20, max_bytes=5_000_000)
        if res is None:
            return None
        status, body, _ct, _final = res
        if status not in (429, 503):
            break
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
        if kind == "Apache":
            # Apache 2.0 只開給科技透明圈（fetch_by_website，Andy 2026-10-28「放寬 Apache 2.0」）；個股頁沒有出處連結，不收。
            out[code] = {"status": "none", "domain": dom[code], "detail": f"{short} 只開給科技透明圈（{f}）"[:200]}
            continue
        if kind in ("CC BY", "CC BY-SA") and not config.LOGO_WIKIMEDIA_ALLOW_BY:
            # 署名義務要在「顯示圖的地方」做到（CC BY 4.0 §3(a)：合理方式，例如連到載明出處的頁面）。
            # 網站目前只在 repo 的 data/logos/ATTRIBUTION.md 列出處、畫面上沒有連結 —— 前端補上署名連結之前不收。
            out[code] = {"status": "none", "domain": dom[code],
                         "detail": f"{short} 需要在網站上署名，前端還沒有出處連結，暫不收（{f}）"[:200]}
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


# ------------------------------------------------------------------ 依「官網網域」找 Logo（科技透明圈外商，2026-10-27）
# 外商沒有台股代號，Wikidata 的台灣條目查詢（上面）幫不上忙。改用公司英文名搜尋 Wikidata，
# 再用條目的「官方網站」（P856）比對我們手上的網域 —— 網域對得上才收，名字像不算
# （同名公司很多：Apple 水果、Meta 前綴詞、Merck 美國 MSD 與德國 Merck KGaA；寧缺勿濫，掛錯別家 Logo 比沒有更糟）。

def _wd_api(params: dict):
    """Wikidata 的 wbsearchentities／wbgetentities。429／503／maxlag 丟 Throttled，其餘壞掉回 None。"""
    # 不帶 maxlag：10-28 回補日誌顯示帶 maxlag=5 時 Wikidata 複寫延遲一高就整批回 503，
    # 42 個網域全部「沒回應」；唯讀查詢本來就不必帶（maxlag 是給大量寫入的機器人用的）。
    url = config.LOGO_WIKIDATA_API + "?" + urlencode({**params, "format": "json"})
    status = body = None
    for wait in (0, 5, 15):        # 503／429 先退避重試兩次，仍不行才收手，避免一次抖動就放棄整批
        if wait:
            time.sleep(wait)
        res = http.get_bytes(url, headers=_headers(), timeout=20, max_bytes=5_000_000)
        if res is None:
            return None
        status, body, _ct, _final = res
        if status not in (429, 503):
            break
    if status in (429, 503):
        raise Throttled(f"Wikidata API 回 HTTP {status}")
    try:
        d = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        log.warning("Wikidata API 回應解析失敗（HTTP %s，回應前 200 字）：%s", status,
                    body[:200].decode("utf-8", errors="replace"))
        return None
    if isinstance(d, dict) and (d.get("error") or {}).get("code") == "maxlag":
        raise Throttled("Wikidata API maxlag")
    return d


def _claim_values(claims: dict, prop: str) -> list[str]:
    out = []
    for c in (claims or {}).get(prop) or []:
        if c.get("rank") == "deprecated":
            continue
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v, str) and v:
            out.append(v)
    return out


def logo_by_website(name_en: str, domain: str) -> dict | None:
    """英文名 → Wikidata 候選條目 → 官方網站網域對得上、且有 P154 標誌圖的那一個。回 {file, item, match} 或 None。

    候選最多看 5 個。對得上的條目若有兩個以上不同圖檔就放棄（不猜）。
    """
    from . import logos as lg

    d = _wd_api({"action": "wbsearchentities", "search": name_en, "language": "en", "type": "item", "limit": "5"})
    ids = [h.get("id") for h in ((d or {}).get("search") or []) if h.get("id")]
    if not ids:
        return None
    time.sleep(config.LOGO_WIKIMEDIA_PAUSE_SEC)
    e = _wd_api({"action": "wbgetentities", "ids": "|".join(ids), "props": "claims"})
    hits = []
    for qid in ids:
        claims = (((e or {}).get("entities") or {}).get(qid) or {}).get("claims") or {}
        logos_ = _claim_values(claims, "P154")
        if not logos_:
            continue
        for url in _claim_values(claims, "P856"):
            host = (re.sub(r"^[a-z]+://", "", url.strip().lower()).split("/")[0]).split(":")[0]
            if lg.same_company(host, domain):
                hits.append((logos_[0], qid))
                break
    files = sorted({h[0] for h in hits})
    if len(files) != 1:
        if len(files) > 1:
            log.info("Wikidata：%s（%s）官網對得上的條目有 %d 個不同圖檔，不猜", name_en, domain, len(files))
        return None
    f = files[0]
    return {"file": f if f.startswith("File:") else "File:" + f, "item": hits[0][1], "match": "website"}


def logos_by_domains_sparql(domains: list[str]) -> dict[str, dict]:
    """備援：wbsearchentities（www.wikidata.org/w/api.php）被 GitHub runner 的 IP 擋成 503 時，
    改走 SPARQL（query.wikidata.org，每週查台灣條目已證實連得上）一次問完：官方網站 P856 含該網域、且有標誌圖 P154。
    回 {網域: {file, item, match}}；同一網域對到兩個以上不同圖檔就不收（不猜）。連線失敗回 {}。"""
    from . import logos as lg

    doms = sorted({d.lower() for d in domains if d and re.fullmatch(r"[a-z0-9.-]+", d.lower())})
    if len(doms) > 10:          # 一次問太多容易逾時：約 10 個一批
        out: dict[str, dict] = {}
        for i in range(0, len(doms), 10):
            if i:
                time.sleep(config.LOGO_WIKIMEDIA_PAUSE_SEC)
            out.update(logos_by_domains_sparql(doms[i:i + 10]))
        return out
    if not doms:
        return {}
    cond = " || ".join(f'CONTAINS(LCASE(STR(?site)), "{d}")' for d in doms)
    q = f"SELECT DISTINCT ?item ?site ?logo WHERE {{ ?item wdt:P154 ?logo . ?item wdt:P856 ?site . FILTER({cond}) }}"
    res = http.get_bytes(config.LOGO_WIKIDATA_SPARQL + "?" + urlencode({"query": q, "format": "json"}),
                         headers={**_headers(), "Accept": "application/sparql-results+json"}, timeout=70, max_bytes=5_000_000)
    if res is None or res[0] != 200:
        log.warning("Wikidata SPARQL 備援失敗（HTTP %s）", res[0] if res else "連線失敗")
        return {}
    try:
        rows = json.loads(res[1].decode("utf-8"))["results"]["bindings"]
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        log.warning("Wikidata SPARQL 備援回應解析失敗（回應前 200 字）：%s", res[1][:200].decode("utf-8", errors="replace"))
        return {}
    found: dict[str, set] = {}
    for b in rows:
        try:
            host = (re.sub(r"^[a-z]+://", "", b["site"]["value"].strip().lower()).split("/")[0]).split(":")[0]
            f = file_title(b["logo"]["value"])
            q_id = b["item"]["value"].rsplit("/", 1)[-1]
        except (KeyError, TypeError):
            continue
        for d in doms:
            if f and lg.same_company(host, d):
                found.setdefault(d, set()).add((f, q_id))
    out = {}
    for d, v in found.items():
        if len({x[0] for x in v}) == 1:
            f, q_id = sorted(v)[0]
            out[d] = {"file": f if f.startswith("File:") else "File:" + f, "item": q_id, "match": "website-sparql"}
    return out


def fetch_by_website(rows: list[dict], reject=frozenset(), deadline: float | None = None) -> dict[str, dict]:
    """rows＝[{domain, en}] → {網域: 結果}（格式同 fetch_many，多半 status＝ok／none）。絕不拋例外；被限流就整段收手。"""
    from . import logos as lg

    out: dict[str, dict] = {}
    sp: dict | None = None      # 非 None＝API 被擋，改用 SPARQL 備援的結果
    try:
        for r in rows:
            dom, name, manual = r["domain"], r.get("en"), r.get("commons_file")
            if not name and not manual:
                continue
            if deadline and time.time() >= deadline:
                break
            try:
                if manual:      # 人工查證過的 Commons 檔名：不依賴 Wikidata，授權照 license_of 檢查
                    hit = {"file": manual if manual.startswith("File:") else "File:" + manual,
                           "item": None, "match": "manual"}
                elif sp is None:
                    try:
                        hit = logo_by_website(name, dom)
                    except Throttled as exc:
                        log.warning("Wikimedia（依網域）：%s，改走 SPARQL 備援", exc)
                        sp = logos_by_domains_sparql([x["domain"] for x in rows if x.get("en") and not x.get("commons_file")])
                        if not sp:
                            raise
                        hit = sp.get(dom)
                else:
                    hit = sp.get(dom)
                time.sleep(config.LOGO_WIKIMEDIA_PAUSE_SEC)
                if not hit:
                    out[dom] = {"status": "none", "domain": dom, "detail": f"Wikidata 查不到官網是 {dom} 的 {name}／沒有標誌圖"}
                    continue
                infos = commons_info([hit["file"]])
                info = infos.get(hit["file"])
                if not info:
                    out[dom] = {"status": "none", "domain": dom, "detail": f"Commons 查不到 {hit['file']}"}
                    continue
                kind, short = license_of(info["ext"])
                if not kind:
                    out[dom] = {"status": "none", "domain": dom, "detail": f"{short}（{hit['file']}）"[:200]}
                    continue
                if kind in ("CC BY", "CC BY-SA") and not config.LOGO_WIKIMEDIA_ALLOW_BY:
                    out[dom] = {"status": "none", "domain": dom,
                                "detail": f"{short} 需要署名，前端還沒有出處連結，暫不收（{hit['file']}）"[:200]}
                    continue
                time.sleep(config.LOGO_WIKIMEDIA_PAUSE_SEC)
                res = _download(lg, info)
                if isinstance(res, Throttled):
                    raise res
                if isinstance(res, lg.LogoReject):
                    out[dom] = {"status": "none", "domain": dom, "detail": f"Commons {res.reason} {res.detail}"[:200]}
                    continue
                png, orig = res
                if lg.sha1(png) in reject:
                    out[dom] = {"status": "generic", "domain": dom, "detail": f"預設圖 {hit['file']}"}
                    continue
                out[dom] = {"status": "ok", "domain": dom, "src": "wikimedia", "url": info.get("page") or hit["file"],
                            "png": png, "orig": list(orig),
                            "attribution": attribution(hit["file"], info, kind, short, hit)}
            except Throttled as exc:
                log.warning("Wikimedia（依網域）：%s，這輪收手", exc)
                break
            except Exception as exc:  # noqa: BLE001 —— 一家壞掉不影響下一家
                out[dom] = {"status": "error", "domain": dom, "detail": str(exc)[:200]}
    except Exception as exc:  # noqa: BLE001
        log.warning("Wikimedia（依網域）失敗（不影響官網那條路）：%s", exc)
    return out
