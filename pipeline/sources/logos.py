"""公司 Logo（搜尋結果與個股頁名稱旁的小圖示）。Andy 2026-09-26 的需求。

來源、條款查證、商標風險與關閉方式寫在 `docs/logo_sources.md`，這裡只寫「為什麼程式長這樣」。

來源（依序試，第一個拿到合格圖就停）
------------------------------------
1. **公司自己的官網**（主來源）：首頁 HTML 裡的 `<link rel="apple-touch-icon">`、`<link rel="icon">`，
   再退到慣例路徑 `/apple-touch-icon.png`、`/favicon.ico`。
   理由：這是公司自己公開給瀏覽器顯示的圖示，抓法跟一般瀏覽器開首頁一模一樣；
   apple-touch-icon 通常是 180px，縮到 64px 最清楚；而且不依賴任何第三方的非官方服務。
2. **Google 的 favicon 服務**（備援）：`https://www.google.com/s2/favicons?domain=<網域>&sz=64`。
   官網首頁是 JS 渲染、或擋雲端 IP 的時候，Google 可能已經有快取。
   ⚠ 它是非官方、無文件、無 SLA 的服務；找不到時回 404 附一張 16px 地球圖示 ——
   404 一律判「沒有」，16px 也會被「過小」擋掉，同一張圖出現在 ≥3 個網域也會被判成預設圖。
   沒選 DuckDuckGo（icons.duckduckgo.com/ip3）：它只回 16／32px 的 ICO、而且不看 <link rel=icon>，
   能拿到的東西是官網那條路的子集。

判定「沒有」的情況（寧可退回字母頭像，也不存假 Logo）
----------------------------------------------------
- `too_small`：原圖長邊 < `config.LOGO_MIN_PX`（16px 放大到 64px 只是一團糊）
- `blank`：全透明，或在白底與黑底上看都是單一顏色（空白佔位圖）
- `generic`：同一張圖（雜湊相同）出現在 ≥ `config.LOGO_GENERIC_DOMAINS` 個**不同網域** ——
  那是 Google 的地球、架站商的預設圖示，不是那家公司的 Logo
- `robots`：官網 robots.txt 不允許一般爬蟲抓首頁 —— 尊重它，**連 Google 備援也不用**
  （用 Google 繞過去等於繞 robots，那是紅線）
- `none`：兩個來源都沒有可用的圖
- `error`：連線失敗、逾時、圖檔壞掉

存放（DECISIONS #155：會重複用到的一律進資料湖，不准每次重抓）
------------------------------------------------------------
- `data/logos/<code>.png`：統一 64×64 PNG（等比縮放、置中、透明補邊 —— 不裁切、不拉伸、不改色）
- `data/logos/_index.json`：代號 → 狀態、來源、網域、抓取日、雜湊、原圖尺寸
- `data/_state/logo_progress.json`：每輪摘要、這輪的失敗清單、還有幾家待抓、下一次到期日
  （`backfill.yml` 的排程守門看這份決定要不要放行）
PNG 不是 Parquet：90 天重抓時如果圖真的變了會換掉舊檔（雜湊一樣就不寫，git 不會多一個版本）。
被判成 generic 的會刪掉檔案 —— 那本來就不該存在。

增量
----
沒抓過的先抓（族群成分股優先，使用者最常看的先有圖），其次是抓到超過 90 天的、
沒抓到超過 30 天的。每輪最多 `config.LOGOS_PER_RUN` 家、最多 `config.LOGO_TIME_BUDGET_SEC` 秒。
同一個網域一輪只抓一次（金控與子公司常共用官網）。
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests

from .. import config
from ..util import http, store
from ..util.roc import clean_code

log = logging.getLogger(__name__)

TAIPEI = timezone(timedelta(hours=8))
INDEX_VERSION = 1

# 網址欄常見的「沒有網址」寫法
_NO_SITE = {"", "-", "—", "無", "none", "n/a", "na", "null", "nan", "暫無", "無網站"}
_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


# ------------------------------------------------------------------ 路徑（每次呼叫才算，測試可以換 config.DATA）

def logo_dir() -> Path:
    return config.DATA / config.LOGOS_SUBDIR


def index_path() -> Path:
    return logo_dir() / config.LOGOS_INDEX_NAME


def state_path() -> Path:
    return config.STATE / config.LOGOS_STATE_NAME


def _today() -> date:
    return datetime.now(TAIPEI).date()


# ------------------------------------------------------------------ 網址 → 網域

def extract_domain(website) -> str | None:
    """從 company_info 的「網址」欄抽出主機名稱（小寫、去掉 port）。抽不出來回 None。

    實際資料長這樣（2026-09-26 資料湖抽樣）：`https://www.tsmc.com`、`www.acc.com.tw`（沒有 scheme）、
    `WWW.FOPCO.COM.TW`（全大寫）、`http://www.aten.com/tw/zh/`（帶路徑）；
    也可能是空值、「無」、或兩個網址用分號／空白隔開（取第一個看起來像網址的）。
    """
    if website is None:
        return None
    try:
        if pd.isna(website):
            return None
    except (TypeError, ValueError):
        pass
    text = str(website).strip()
    if text.lower() in _NO_SITE:
        return None
    for part in re.split(r"[\s;,、，；]+", text):
        part = part.strip().strip("/")
        if not part or part.lower() in _NO_SITE:
            continue
        if "@" in part and "://" not in part:   # 電子郵件被填進網址欄
            continue
        url = part if re.match(r"^[a-z][a-z0-9+.-]*://", part, re.I) else "http://" + part
        try:
            host = (urlparse(url).hostname or "").strip(".").lower()
        except ValueError:
            continue
        if host and _HOST_RE.match(host) and not re.match(r"^\d+(\.\d+){3}$", host):
            return host
    return None


def base_domain(host: str | None) -> str:
    """判定「預設圖」時用的網域：去掉 www. —— www.a.com 與 a.com 算同一個網站。"""
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def homepage_candidates(website, host: str) -> list[str]:
    """首頁網址候選。原本寫 http 的先試 https（多數官網已強制 https），再退回 http。"""
    raw = str(website or "").strip()
    first = "https" if not raw.lower().startswith("http://") else "http"
    other = "http" if first == "https" else "https"
    return [f"{first}://{host}/", f"{other}://{host}/"]


# ------------------------------------------------------------------ HTML 裡的圖示連結

class _IconLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self.base: str | None = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "base" and a.get("href") and self.base is None:
            self.base = a["href"]
        if tag != "link":
            return
        rel = a.get("rel", "").lower().split()
        href = a.get("href", "").strip()
        if not href or not rel:
            return
        if "apple-touch-icon" in rel or "apple-touch-icon-precomposed" in rel:
            kind = "apple-touch-icon"
        elif "icon" in rel:
            kind = "icon"
        else:
            return
        self.links.append({"href": href, "kind": kind, "sizes": a.get("sizes", ""),
                           "type": a.get("type", "").lower()})


def _declared_px(sizes: str) -> int:
    best = 0
    for m in re.finditer(r"(\d+)\s*[xX×]\s*(\d+)", sizes or ""):
        best = max(best, min(int(m.group(1)), int(m.group(2))))
    return best


def parse_icon_links(html: str, base_url: str) -> list[dict]:
    """解析首頁的圖示連結，回 [{url, kind, px}]，依「最可能清楚」排好。

    排序：apple-touch-icon（慣例 180px）優先 → 宣告尺寸大的 → 其他。
    略過 SVG（Pillow 畫不了向量檔，而且縮放 SVG 等於自己重畫一次，不是「不修改圖形」）
    與 data: URI（內嵌圖多半是 1px 佔位）。
    """
    p = _IconLinks()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001 —— 壞掉的 HTML 能解多少算多少
        pass
    base = urljoin(base_url, p.base) if p.base else base_url
    out, seen = [], set()
    for ln in p.links:
        href = ln["href"]
        if href.lower().startswith("data:"):
            continue
        if ln["type"] == "image/svg+xml" or re.search(r"\.svgz?(\?|#|$)", href, re.I):
            continue
        url = urljoin(base, href)
        if not url.lower().startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "kind": ln["kind"], "px": _declared_px(ln["sizes"])})
    out.sort(key=lambda d: (d["kind"] != "apple-touch-icon", -d["px"]))
    return out


# ------------------------------------------------------------------ 圖檔 → 64×64 PNG

class LogoReject(Exception):
    """這張圖不能當 Logo（reason = too_small / blank / bad_image / no_pillow）。"""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _pil():
    """Pillow 延後載入：build_payload 與其他步驟不需要它，沒裝的話只有 Logo 步驟停擺。"""
    try:
        from PIL import Image  # noqa: WPS433
        return Image
    except ImportError as exc:  # pragma: no cover —— requirements 有列，Actions 一定有
        raise LogoReject("no_pillow", str(exc)) from exc


def is_blank(img) -> bool:
    """全透明，或在白底、黑底上都幾乎只有一種顏色 ＝ 空白佔位圖。

    分白底、黑底兩次看：白色 Logo 配透明背景在白底上會「消失」，但在黑底上看得到，那不是空白。
    """
    Image = _pil()
    rgba = img.convert("RGBA")
    alpha_hi = rgba.getchannel("A").getextrema()[1]
    if alpha_hi < 16:
        return True
    spans = []
    for bg in ((255, 255, 255, 255), (0, 0, 0, 255)):
        canvas = Image.new("RGBA", rgba.size, bg)
        canvas.alpha_composite(rgba)
        lo, hi = canvas.convert("L").getextrema()
        spans.append(hi - lo)
    return max(spans) < 10


def normalize_image(data: bytes) -> tuple[bytes, tuple[int, int]]:
    """任何 Pillow 讀得懂的圖（ICO／PNG／JPEG／GIF／WebP／BMP）→ 64×64 透明底 PNG。

    ICO 內含多種尺寸時 Pillow 預設開最大的那張。等比縮到 64 以內再置中貼到透明畫布，
    不裁切、不拉伸、不改色 —— 只縮放，這是「指稱性使用、不修改圖形」的技術面保證。
    """
    Image = _pil()
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001
        raise LogoReject("bad_image", str(exc)[:120]) from exc
    try:
        img.seek(0)          # 動態 GIF 取第一格
    except Exception:  # noqa: BLE001
        pass
    w, h = img.size
    if max(w, h) < config.LOGO_MIN_PX:
        raise LogoReject("too_small", f"{w}x{h}")
    rgba = img.convert("RGBA")
    if is_blank(rgba):
        raise LogoReject("blank", f"{w}x{h}")
    px = config.LOGO_PX
    scale = px / max(w, h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    resized = rgba.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    canvas.paste(resized, ((px - nw) // 2, (px - nh) // 2), resized)
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), (w, h)


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


# ------------------------------------------------------------------ 抓單一家

_tls = threading.local()


def _sess() -> requests.Session:
    s = getattr(_tls, "sess", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": config.USER_AGENT,
                          "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"})
        _tls.sess = s
    return s


def _get(url: str, **kw):
    return http.get_bytes(url, sess=_sess(), **kw)


def robots_allows(root: str, page: str) -> bool:
    """官網的 robots.txt 允不允許一般爬蟲（*）抓首頁。

    robots.txt 抓不到（404／連線失敗）＝ 沒有限制；401／403 依 robotparser 的慣例視為全站禁止。
    """
    res = _get(urljoin(root, "/robots.txt"), timeout=6, max_bytes=200_000)
    if res is None:
        return True
    status, body, _ctype, _final = res
    rp = RobotFileParser()
    if status in (401, 403):
        return False
    if status != 200:
        return True
    try:
        rp.parse(body.decode("utf-8", errors="replace").splitlines())
    except Exception:  # noqa: BLE001
        return True
    return rp.can_fetch("*", page)


def _try_image(url: str) -> tuple[bytes, tuple[int, int]] | LogoReject:
    res = _get(url, timeout=8, max_bytes=1_000_000)
    if res is None:
        return LogoReject("error", f"連線失敗 {url}")
    status, body, _ctype, _final = res
    if status != 200 or not body:
        return LogoReject("none", f"HTTP {status} {url}")
    head = body[:300].lstrip().lower()
    if head[:1] == b"<":
        # 以「內容」判斷，不信 Content-Type（有的站圖檔也標 text/html）：
        # 很多站對不存在的 /favicon.ico 回 200 ＋ 首頁 HTML（軟 404）；SVG 也是 < 開頭，一樣不處理
        what = "SVG 不處理" if b"<svg" in head else "回的是 HTML 不是圖"
        return LogoReject("none", f"{what} {url}")
    try:
        return normalize_image(body)
    except LogoReject as rej:
        rej.detail = f"{rej.detail} {url}".strip()
        return rej


# 失敗原因的「嚴重度」：多個候選都失敗時，回報最有資訊量的那一個
_REASON_RANK = {"too_small": 5, "blank": 4, "bad_image": 3, "none": 2, "error": 1}


def fetch_logo(website, host: str | None = None) -> dict:
    """抓一家公司的 Logo。回 {status, src, png, orig, detail, domain}；status＝ok 時 png 有值。

    絕不拋例外：任何意外都變成 status=error，一家壞掉不能拖垮一整輪。
    """
    host = host or extract_domain(website)
    if not host:
        return {"status": "no_website", "domain": None}
    try:
        return _fetch_logo(website, host)
    except LogoReject as rej:
        return {"status": "error", "domain": host, "detail": f"{rej.reason} {rej.detail}"[:200]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "domain": host, "detail": str(exc)[:200]}


def _fetch_logo(website, host: str) -> dict:
    worst: LogoReject | None = None

    def keep(rej: LogoReject):
        nonlocal worst
        if worst is None or _REASON_RANK.get(rej.reason, 0) > _REASON_RANK.get(worst.reason, 0):
            worst = rej

    # ① 官網
    site_ok = False
    for home in homepage_candidates(website, host):
        root = home
        if not robots_allows(root, home):
            return {"status": "robots", "domain": host,
                    "detail": f"{root}robots.txt 不允許抓首頁 —— 尊重它，也不走 Google 備援"}
        res = _get(home, timeout=10, max_bytes=2_000_000)
        if res is None:
            keep(LogoReject("error", f"首頁連線失敗 {home}"))
            continue
        status, body, ctype, final = res
        site_ok = True
        cands: list[dict] = []
        if status == 200 and body:
            cands = parse_icon_links(body.decode("utf-8", errors="replace"), final or home)
        origin = "{0.scheme}://{0.netloc}/".format(urlparse(final or home))
        for path in ("apple-touch-icon.png", "favicon.ico"):
            u = urljoin(origin, path)
            if all(c["url"] != u for c in cands):
                cands.append({"url": u, "kind": "conventional", "px": 0})
        for c in cands[:5]:
            got = _try_image(c["url"])
            if isinstance(got, LogoReject):
                keep(got)
                continue
            png, orig = got
            return {"status": "ok", "domain": host, "src": f"site:{c['kind']}",
                    "url": c["url"], "png": png, "orig": list(orig)}
        break      # 首頁連得上就不必再換 scheme 重來一次

    # ② Google 備援
    s2 = config.LOGO_GOOGLE_S2.format(domain=host)
    got = _try_image(s2)
    if not isinstance(got, LogoReject):
        png, orig = got
        return {"status": "ok", "domain": host, "src": "google_s2", "url": s2,
                "png": png, "orig": list(orig)}
    keep(got)
    reason = worst.reason if worst else "none"
    status = reason if reason in ("too_small", "blank", "error") else "none"
    if status == "error" and site_ok:
        status = "none"
    return {"status": status, "domain": host, "detail": (worst.detail if worst else "")[:200]}


# ------------------------------------------------------------------ 索引

def read_index() -> dict:
    p = index_path()
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("items"), dict):
                return d
        except (ValueError, OSError) as exc:
            log.warning("Logo 索引讀不進來（%s），當成空的重建 —— 已有的 PNG 會在重抓時補回索引", exc)
    return {"version": INDEX_VERSION, "items": {}}


def write_index(idx: dict) -> None:
    logo_dir().mkdir(parents=True, exist_ok=True)
    idx["version"] = INDEX_VERSION
    idx["updated_at"] = datetime.now(timezone.utc).isoformat()
    idx["items"] = dict(sorted(idx.get("items", {}).items()))
    index_path().write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


def generic_hashes(items: dict, min_domains: int | None = None) -> set[str]:
    """出現在 ≥ min_domains 個**不同網域**的圖雜湊 ＝ 預設圖（地球、架站商圖示）。

    算網域不算代號：金控與子公司共用同一個官網、同一個 Logo 是正常的，不能誤判。
    """
    n = config.LOGO_GENERIC_DOMAINS if min_domains is None else min_domains
    by_hash: dict[str, set[str]] = {}
    for rec in items.values():
        if rec.get("status") in ("ok", "generic") and rec.get("sha1"):
            by_hash.setdefault(rec["sha1"], set()).add(base_domain(rec.get("domain")))
    return {h for h, doms in by_hash.items() if len(doms) >= n}


def usable_codes(idx: dict) -> dict[str, str]:
    """{代號: 檔名}：狀態 ok、檔案真的在、而且不是預設圖。build_payload 只輸出這些。"""
    items = idx.get("items", {})
    bad = generic_hashes(items)
    out = {}
    for code, rec in items.items():
        if rec.get("status") != "ok" or rec.get("sha1") in bad:
            continue
        f = logo_dir() / f"{code}.png"
        if f.exists():
            out[code] = f.name
    return out


# ------------------------------------------------------------------ 誰要抓

def websites() -> pd.DataFrame:
    """[code, website, market]：上市用 company_info 的「網址」，上櫃／興櫃用 company_website 補。

    ETF 沒有公司官網（也沒有 Logo 可抓），直接排除。
    """
    frames = []
    info = store.read("company_info")
    if not info.empty and "website" in info.columns:
        x = info.copy()
        if "industry" in x.columns:
            x = x[x["industry"].astype(str) != "ETF"]
        x = x.drop_duplicates("code", keep="last")
        frames.append(x.reindex(columns=["code", "website", "market"]))
    extra = store.read("company_website")
    if not extra.empty and "website" in extra.columns:
        frames.append(extra.drop_duplicates("code", keep="last")
                      .reindex(columns=["code", "website", "market"]))
    if not frames:
        return pd.DataFrame(columns=["code", "website", "market"])
    df = pd.concat(frames, ignore_index=True)
    df = df[df["website"].map(lambda v: extract_domain(v) is not None)]
    # company_info 的網址優先（它是上市公司自己申報的那份）；company_website 只補沒有的
    return df.drop_duplicates("code", keep="first").reset_index(drop=True)


def _due(rec: dict, today: date) -> bool:
    try:
        last = date.fromisoformat(str(rec.get("fetched"))[:10])
    except ValueError:
        return True
    days = config.LOGO_REFRESH_DAYS if rec.get("status") == "ok" else config.LOGO_RETRY_DAYS
    return (today - last).days >= days


def next_due(rec: dict) -> str | None:
    try:
        last = date.fromisoformat(str(rec.get("fetched"))[:10])
    except ValueError:
        return None
    days = config.LOGO_REFRESH_DAYS if rec.get("status") == "ok" else config.LOGO_RETRY_DAYS
    return (last + timedelta(days=days)).isoformat()


def select_todo(sites: pd.DataFrame, idx: dict, today: date, limit: int,
                priority: list[str] | None = None) -> list[dict]:
    """這一輪要抓哪些：沒抓過的 → 網域換了的 → 到期重抓的（最舊的先）。

    沒抓過的裡面，`priority`（族群成分股）排前面 —— 使用者最常點的股票先有圖。
    """
    items = idx.get("items", {})
    prio = {c: i for i, c in enumerate(priority or [])}
    fresh, changed, due = [], [], []
    for r in sites.itertuples(index=False):
        code = clean_code(r.code)
        if not code:
            continue
        host = extract_domain(r.website)
        rec = items.get(code)
        row = {"code": code, "website": r.website, "domain": host}
        if rec is None:
            fresh.append(row)
        elif base_domain(rec.get("domain")) != base_domain(host):
            changed.append(row)
        elif _due(rec, today):
            due.append((str(rec.get("fetched") or ""), row))
    fresh.sort(key=lambda d: (prio.get(d["code"], len(prio)), d["code"]))
    due.sort(key=lambda t: t[0])
    return (fresh + changed + [r for _, r in due])[:max(0, limit)]


# ------------------------------------------------------------------ 一輪

def _save_png(code: str, png: bytes, old_sha: str | None) -> str:
    h = sha1(png)
    f = logo_dir() / f"{code}.png"
    if h != old_sha or not f.exists():
        f.write_bytes(png)
    return h


def run(limit: int | None = None, *, today: date | None = None,
        time_budget: float | None = None, fetcher=None,
        priority: list[str] | None = None) -> dict:
    """抓一輪 Logo。回摘要 dict，並寫進 data/_state/logo_progress.json。絕不拋例外。"""
    summary: dict = {"enabled": config.LOGOS_ENABLED, "at": datetime.now(timezone.utc).isoformat()}
    if not config.LOGOS_ENABLED:
        log.info("LOGOS_ENABLED 關閉，Logo 步驟不抓")
        summary.update(done=True, skipped="disabled")
        _write_state(summary)
        return summary
    try:
        return _run(summary, limit, today, time_budget, fetcher, priority)
    except Exception as exc:  # noqa: BLE001
        log.warning("Logo 步驟失敗（不影響其他步驟）：%s", exc)
        summary.update(done=False, error=str(exc)[:200])
        _write_state(summary)
        return summary


def _run(summary, limit, today, time_budget, fetcher, priority) -> dict:
    today = today or _today()
    limit = config.LOGOS_PER_RUN if limit is None else limit
    budget = config.LOGO_TIME_BUDGET_SEC if time_budget is None else time_budget
    fetcher = fetcher or fetch_logo
    if fetcher is fetch_logo:
        _pil()   # 沒有 Pillow 就整輪不跑（直接進 except 記進狀態檔），不要抓了幾百張卻存不了

    sites = websites()
    idx = read_index()
    items = idx.setdefault("items", {})
    todo = select_todo(sites, idx, today, limit, priority)
    logo_dir().mkdir(parents=True, exist_ok=True)
    log.info("Logo：有網址 %d 家、已有紀錄 %d 家，這輪抓 %d 家（上限 %d、%d 秒）",
             len(sites), len(items), len(todo), limit, budget)

    t0 = time.time()
    by_domain: dict[str, dict] = {}
    results: dict[str, dict] = {}
    lock = threading.Lock()
    deadline_hit = False

    def one(row):
        dom = base_domain(row["domain"])
        with lock:
            if dom in by_domain:
                return row, by_domain[dom], True
        res = fetcher(row["website"], row["domain"])
        with lock:
            by_domain.setdefault(dom, res)
        return row, res, False

    # 同一網域的代號擺在一起會在不同執行緒同時抓；先抓每個網域的第一家，其餘等結果
    firsts, rest, seen = [], [], set()
    for row in todo:
        d = base_domain(row["domain"])
        (rest if d in seen else firsts).append(row)
        seen.add(d)

    with ThreadPoolExecutor(max_workers=max(1, config.LOGO_WORKERS)) as ex:
        futs = []
        for row in firsts:
            futs.append(ex.submit(one, row))
        for fu in as_completed(futs):
            if fu.cancelled():
                continue
            try:
                row, res, _ = fu.result()
            except Exception as exc:  # noqa: BLE001 —— 一家出事不能讓整輪的結果都沒寫
                log.warning("Logo：抓取執行緒拋出例外：%s", exc)
                continue
            results[row["code"]] = res
            if time.time() - t0 > budget and not deadline_hit:
                deadline_hit = True
                log.warning("Logo：這輪已經 %.0f 秒，時間到，剩下的下一輪接續", time.time() - t0)
                for f in futs:
                    f.cancel()
    for row in rest:
        d = base_domain(row["domain"])
        if d in by_domain:
            results[row["code"]] = dict(by_domain[d])

    counts: dict[str, int] = {}
    failures = []
    stamp = today.isoformat()
    for code, res in results.items():
        st = res.get("status", "error")
        if st == "no_website":
            continue
        old = items.get(code) or {}
        rec = {"status": st, "domain": res.get("domain"), "fetched": stamp}
        if st == "ok":
            rec.update(src=res.get("src"), url=res.get("url"), orig=res.get("orig"),
                       sha1=_save_png(code, res["png"], old.get("sha1")))
        else:
            rec["detail"] = res.get("detail", "")
            failures.append({"code": code, "status": st, "domain": res.get("domain"),
                             "detail": res.get("detail", "")})
            if old.get("status") == "ok" and (logo_dir() / f"{code}.png").exists():
                # 之前抓到過、這次沒抓到（官網暫時掛掉）：保留舊圖，只延後下一次重抓
                rec = {**old, "fetched": stamp, "last_fail": st}
                st = "kept"
        items[code] = rec
        counts[st] = counts.get(st, 0) + 1

    # 預設圖：同一張圖出現在太多網域 → 刪檔、標 generic
    bad = generic_hashes(items)
    n_generic = 0
    for code, rec in items.items():
        if rec.get("status") == "ok" and rec.get("sha1") in bad:
            rec["status"] = "generic"
            (logo_dir() / f"{code}.png").unlink(missing_ok=True)
            n_generic += 1
    if n_generic:
        log.info("Logo：%d 家的圖跟其他網域完全一樣（預設圖），已刪檔改標 generic", n_generic)

    write_index(idx)
    left = select_todo(sites, idx, today, 10 ** 9, priority)
    dues = [d for d in (next_due(r) for r in items.values()) if d]
    summary.update(
        done=not left, pending=len(left), attempted=len(results),
        counts=counts, generic=n_generic, sites=len(sites),
        have=sum(1 for r in items.values() if r.get("status") == "ok"),
        next_due=min(dues) if dues else None,
        seconds=round(time.time() - t0, 1), deadline_hit=deadline_hit,
        failures=failures[:200],
    )
    _write_state(summary)
    log.info("Logo：這輪 %s，現在有圖 %d 家，還有 %d 家待抓（下一次到期 %s）",
             counts, summary["have"], len(left), summary["next_due"])
    return summary


def _write_state(summary: dict) -> None:
    try:
        state_path().parent.mkdir(parents=True, exist_ok=True)
        state_path().write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        log.warning("Logo 狀態檔寫不進去：%s", exc)


# ------------------------------------------------------------------ 上櫃／興櫃的官網網址

_CODE_KEYS = ("公司代號", "SecuritiesCompanyCode", "CompanyCode", "Code", "code")
_SITE_KEYS = ("網址", "WebAddress", "Website", "WebSite", "CompanyWebsite", "URL", "Url", "website")
_DATE_KEYS = ("出表日期", "Date", "date")


def _pick(row: dict, keys) -> str | None:
    norm = {str(k).strip(): v for k, v in row.items()}
    for k in keys:
        if k in norm and norm[k] not in (None, ""):
            return norm[k]
    # 欄位改名是常態：退而求其次找名字裡有「網址／web／url」的欄位
    if keys is _SITE_KEYS:
        for k, v in norm.items():
            kl = k.lower()
            if ("網址" in k or "web" in kl or kl.endswith("url")) and v:
                return v
    return None


def parse_company_websites(raw, market: str, src: str, fetched: str) -> pd.DataFrame:
    """把「公司基本資料」端點的回應解析成 [code, website, market, src, asof]。

    asof 用回應裡的「出表日期」（民國轉西元）；端點沒給才用抓取日，而且欄名叫 asof 不叫 date ——
    這不是交易日，只是「這份網址清單是哪天的」。
    """
    from ..util.roc import roc_to_iso

    if not isinstance(raw, list) or not raw:
        return pd.DataFrame()
    rows = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        code = clean_code(_pick(r, _CODE_KEYS))
        site = _pick(r, _SITE_KEYS)
        if not code or extract_domain(site) is None:
            continue
        d = _pick(r, _DATE_KEYS)
        asof = roc_to_iso(d) if d else None
        rows.append({"code": code, "website": str(site).strip(), "market": market,
                     "src": src, "asof": asof or fetched})
    return pd.DataFrame(rows)


def company_websites() -> pd.DataFrame:
    """上櫃／興櫃公司的官網網址（company_info 只有上市的網址）。失敗回空 DataFrame 並記 log。"""
    fetched = _today().isoformat()
    frames, got_markets = [], set()
    for market, url in config.COMPANY_WEBSITE_ENDPOINTS:
        if market in got_markets:
            continue
        headers = None
        if "tpex.org.tw" in url:
            headers = {"Referer": "https://www.tpex.org.tw/", "Origin": "https://www.tpex.org.tw"}
        try:
            raw = http.get(url, headers=headers, retries=2)
        except Exception as exc:  # noqa: BLE001
            log.warning("公司網址 %s 抓取失敗：%s", url, exc)
            continue
        df = parse_company_websites(raw, market, urlparse(url).netloc, fetched)
        if df.empty:
            head = json.dumps(raw, ensure_ascii=False)[:200] if raw is not None else "（沒有回應）"
            log.warning("公司網址 %s 解析不出任何一筆（回應前 200 字）：%s", url, head)
            continue
        log.info("公司網址 %s：%d 家（%s）", url, len(df), market)
        frames.append(df)
        got_markets.add(market)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates("code", keep="first")
