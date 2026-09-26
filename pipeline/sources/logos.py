"""公司 Logo（搜尋結果與個股頁名稱旁的小圖示）。Andy 2026-09-26 的需求。

來源、條款查證、商標風險與關閉方式寫在 `docs/logo_sources.md`，這裡只寫「為什麼程式長這樣」。

來源（第二版，2026-09-26：全部候選都評分，取「最大」的那一張）
----------------------------------------------------------------
第一版「依序試、第一張合格就停」的結果：試 300 家，台積電、聯電、瑞昱、聯詠、廣達、緯穎這些權值股
全被判「太小」（官網只宣告 16px favicon），欣興、旺宏、南亞電路板被判「找不到」。第二版改成：

1. **公司自己的官網**（主來源）。首頁 HTML 裡找這幾種，全部當候選：
   - `<link rel="icon"|"apple-touch-icon"|"mask-icon" sizes=…>` **全部**（不只第一個）
   - `<link rel="manifest">` 指向的 web app manifest 裡的 icons（取最大的兩個）
   - `<meta property="og:image">`：只在它看起來是 Logo 時才用（路徑含 logo，或長寬比 1:1～4:1 且不是照片）
   - 頁首的 `<img>`：自己的 src／class／alt／id 含 logo，或包在 class／id 含 logo 的元素裡；
     頁尾、合作夥伴、認證、社群按鈕不收
   - 慣例路徑 `/apple-touch-icon.png`、`/favicon.ico`
   SVG 用 cairosvg 依原比例畫成點陣圖（沒有 cairosvg／libcairo 就跳過 SVG）。
   每一張都縮進 64×64 方框評「有效尺寸」（短邊，超過 64 不加分），取最大；一樣大時官方圖示優先。
   找到 ≥64px 的正方形官方圖示就提早停，每家最多下載 `config.LOGO_MAX_TRIES` 張。
   首頁轉址自己一跳一跳跟：只跟同一家公司的網域（www ↔ 非 www、.com.tw ↔ .com），每跳都先過 robots；
   首頁 404 或連不上就換 https／http、再換 www／非 www 的另一種。
2. **Google 的 favicon 服務**（備援）：`https://www.google.com/s2/favicons?domain=<網域>&sz=128`。
   官網什麼都沒有、或最好的也只有 32～47px 時才問它；它對只有小圖的網站仍回 16px，照樣判太小。
   ⚠ 它是非官方、無文件、無 SLA 的服務；找不到時回 404 附一張 16px 地球圖示 ——
   404 一律判「沒有」，16px 也會被「過小」擋掉，同一張圖出現在 ≥3 個網域也會被判成預設圖。
   沒選 DuckDuckGo（icons.duckduckgo.com/ip3）：它只回 16／32px 的 ICO、而且不看 <link rel=icon>，
   能拿到的東西是官網那條路的子集。

判定「沒有」的情況（寧可退回字母頭像，也不存假 Logo）
----------------------------------------------------
- `too_small`：原圖長邊 < `config.LOGO_MIN_PX`（16px 放大到 64px 只是一團糊），
  或長寬比超過 `config.LOGO_MAX_ASPECT`（橫條字標縮進 64×64 只剩一條線）
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
策略升級（`config.LOGO_STRATEGY` 加一）後，舊策略判「太小／找不到」的最先重試；
其次是沒抓過的（族群成分股優先，使用者最常看的先有圖），再來是抓到超過 90 天的、
沒抓到超過 30 天的。已經抓到的好圖不因為策略升級而重抓。每輪最多 `config.LOGOS_PER_RUN` 家、最多 `config.LOGO_TIME_BUDGET_SEC` 秒。
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


# ------------------------------------------------------------------ 網域：同一家公司的判斷

# 二層公共後綴的第一段（com.tw、co.jp、org.uk…）：registrable() 看到「兩碼國碼前面是這些」就多取一段
_SLD = {"com", "net", "org", "edu", "gov", "idv", "co", "ac", "or", "ne", "go", "mil"}


def registrable(host: str | None) -> str:
    """可註冊網域：www.tsmc.com → tsmc.com、ir.acc.com.tw → acc.com.tw、www.avc.co → avc.co。

    只處理台灣上市櫃公司官網實際會出現的形狀（.com／.com.tw／.tw／.co／.com.cn…），
    不引入完整的公共後綴清單 —— 判錯的代價只是「少跟一次轉址」，不值得多一個相依。
    """
    parts = (host or "").lower().strip(".").split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in _SLD:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_company(a: str | None, b: str | None) -> bool:
    """兩個主機是不是同一家公司的網域：可註冊網域相同，或品牌那一段相同（aoet.com.tw ↔ aoet.com）。

    首頁轉址只跟「同一家公司」的：www ↔ 非 www、.com.tw ↔ .com、子網域。
    轉到別的品牌（集團母公司、架站商、停放頁）就不跟 —— 那裡的圖示不是這家公司的 Logo。
    """
    if not a or not b:
        return False
    ra, rb = registrable(a), registrable(b)
    if ra == rb:
        return True
    la, lb = ra.split(".")[0], rb.split(".")[0]
    return len(la) >= 3 and la == lb


def homepage_candidates(website, host: str) -> list[str]:
    """首頁網址候選：原本的主機先試（原本寫 http 的先試 https，再退回 http），最後試 www／非 www 的另一個。

    第二版（2026-09-26）加最後那一個：第一輪「找不到」裡有好幾家只是申報的網址多了或少了 www，
    首頁 404 或連不上時換另一種常常就通。只在主機本身是 www.<網域> 或 <網域> 時才換，
    ir.xxx.com.tw 這種子網域不亂加 www。
    """
    raw = str(website or "").strip()
    first = "https" if not raw.lower().startswith("http://") else "http"
    other = "http" if first == "https" else "https"
    out = [f"{first}://{host}/", f"{other}://{host}/"]
    if host.startswith("www."):
        out.append(f"https://{host[4:]}/")
    elif host == registrable(host):
        out.append(f"https://www.{host}/")
    return out


def _origin(url: str) -> str:
    return "{0.scheme}://{0.netloc}/".format(urlparse(url))


# ------------------------------------------------------------------ HTML 裡的候選：圖示、manifest、og:image、頁首 logo 圖

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
         "source", "track", "wbr"}
# 頁面上「名字有 logo 但不是這家公司 Logo」的常見圖：合作夥伴、客戶、認證、社群按鈕、QR code、App 商店
_NOT_OWN_LOGO = re.compile(
    r"partner|client|customer|sponsor|award|certif|\biso\b|facebook|\bfb\b|\bline\b|youtube|linkedin|"
    r"instagram|twitter|wechat|weibo|\bqr|footer|app-?store|google-?play|member", re.I)
_SVG_URL = re.compile(r"\.svgz?(\?|#|$)", re.I)
_SVG_PX = 256        # SVG 依原比例畫成長邊 256px 再縮到 64（向量檔沒有「原始尺寸」，畫多大由我們決定）


def _is_svg_url(url: str) -> bool:
    return bool(_SVG_URL.search(url or ""))


def _abs(base: str, href: str | None) -> str | None:
    href = (href or "").strip()
    if not href or href.lower().startswith(("data:", "javascript:", "about:", "#")):
        return None
    try:
        url = urljoin(base, href)
    except ValueError:
        return None
    return url if url.lower().startswith(("http://", "https://")) else None


def _largest_srcset(srcset: str) -> str | None:
    """srcset="a.png 1x, a@2x.png 2x" 或 "s.png 120w, l.png 480w" → 描述值最大的那個網址。"""
    best, best_v = None, -1.0
    for part in (srcset or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        v = 1.0
        if len(bits) > 1:
            m = re.match(r"^([\d.]+)[wx]$", bits[1].lower())
            v = float(m.group(1)) if m else 1.0
        if v > best_v:
            best, best_v = bits[0], v
    return best


class _PageScan(HTMLParser):
    """一次掃過首頁：圖示類 <link>、manifest、og:image、「看起來是自家 Logo」的 <img>。

    頁首判斷用一個寬鬆的標籤堆疊：<header>、或 class／id 含 header／navbar／masthead 的元素算「頁首」，
    <footer> 或 class／id 含 footer 的算「頁尾」（頁尾的 logo 多半是合作夥伴、認證標章，一律不收）。
    壞掉、沒關的 HTML 很常見：結束標籤只往上找 64 層，找不到就當沒看到，堆疊最多 2000 層。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self.base: str | None = None
        self.manifest: str | None = None
        self.meta: dict[str, str] = {}
        self.imgs: list[dict] = []
        self._stack: list[tuple[str, frozenset]] = []

    def _zones(self) -> set:
        z: set = set()
        for _t, zs in self._stack:
            z |= zs
        return z

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "base":
            if a.get("href") and self.base is None:
                self.base = a["href"]
            return
        if tag == "link":
            return self._link(a)
        if tag == "meta":
            return self._meta(a)
        if tag == "img":
            return self._img(a)
        if tag in _VOID or len(self._stack) >= 2000:
            return
        cid = f"{a.get('class', '')} {a.get('id', '')}".lower()
        zs = set()
        if tag == "header" or re.search(r"header|masthead|navbar|topbar|top-bar", cid):
            zs.add("header")
        if tag == "footer" or "footer" in cid:
            zs.add("footer")
        if "logo" in cid or ("brand" in cid and ("header" in zs or "header" in self._zones())):
            zs.add("logo")
        self._stack.append((tag, frozenset(zs)))

    def handle_endtag(self, tag):
        lo = max(0, len(self._stack) - 64)
        for i in range(len(self._stack) - 1, lo - 1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                return

    def _link(self, a):
        rel = a.get("rel", "").lower().split()
        href = a.get("href", "").strip()
        if not href or not rel:
            return
        if "manifest" in rel:
            self.manifest = self.manifest or href
            return
        if "apple-touch-icon" in rel or "apple-touch-icon-precomposed" in rel:
            kind = "apple-touch-icon"
        elif "mask-icon" in rel:
            kind = "mask-icon"
        elif "icon" in rel:
            kind = "icon"
        else:
            return
        self.links.append({"href": href, "kind": kind, "sizes": a.get("sizes", ""),
                           "type": a.get("type", "").lower()})

    def _meta(self, a):
        key = (a.get("property") or a.get("name") or "").strip().lower()
        val = (a.get("content") or "").strip()
        if not val:
            return
        if key in ("og:image", "og:image:url", "og:image:secure_url"):
            self.meta.setdefault("og:image", val)
        elif key in ("og:image:width", "og:image:height"):
            self.meta.setdefault(key, val)

    def _img(self, a):
        if len(self.imgs) >= 30:
            return
        src = ""
        for k in ("src", "data-src", "data-original", "data-lazy-src", "data-lazy"):
            v = a.get(k, "").strip()
            if v and not v.lower().startswith("data:"):
                src = v
                break
        big = _largest_srcset(a.get("srcset") or a.get("data-srcset") or "")
        if big and not big.lower().startswith("data:"):
            src = big
        if not src:
            return
        zones = self._zones()
        if "footer" in zones:
            return
        own = " ".join(a.get(k, "") for k in ("src", "data-src", "class", "alt", "id")).lower()
        own_logo = "logo" in own
        if not (own_logo or "logo" in zones):
            return
        if _NOT_OWN_LOGO.search(own):
            return
        self.imgs.append({"href": src, "header": "header" in zones, "own": own_logo,
                          "order": len(self.imgs)})


def _declared_px(sizes: str) -> int:
    best = 0
    for m in re.finditer(r"(\d+)\s*[xX×]\s*(\d+)", sizes or ""):
        best = max(best, min(int(m.group(1)), int(m.group(2))))
    return best


def _int(v) -> int | None:
    try:
        n = int(float(str(v).strip()))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def scan_page(html: str, base_url: str) -> dict:
    """解析首頁，回 {icons, manifest, og, imgs}。每個候選是 {url, kind, px, svg}。

    - icons：`<link rel="icon"|"apple-touch-icon"|"mask-icon">` **全部**（第一版只取第一個能用的）。
      px 是宣告的 sizes；apple-touch-icon 沒寫 sizes 時照慣例當 180；SVG 寫 sizes="any" 當 512。
    - manifest：`<link rel="manifest">` 的網址（圖示要另外下載 manifest 才知道）。
    - og：`<meta property="og:image">` 與宣告的寬高；**要不要用由 og_candidate() 判斷**。
    - imgs：頁首「自家 Logo」的 <img>，頁首裡的、自己名字就有 logo 的排前面，最多 2 個。
    """
    p = _PageScan()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001 —— 壞掉的 HTML 能解多少算多少
        pass
    base = _abs(base_url, p.base) if p.base else base_url
    base = base or base_url
    icons, seen = [], set()
    for ln in p.links:
        url = _abs(base, ln["href"])
        if not url or url in seen:
            continue
        seen.add(url)
        svg = ln["kind"] == "mask-icon" or ln["type"] == "image/svg+xml" or _is_svg_url(url)
        px = _declared_px(ln["sizes"])
        if not px and svg and "any" in ln["sizes"].lower():
            px = 512
        if not px and ln["kind"] == "apple-touch-icon":
            px = 180
        icons.append({"url": url, "kind": ln["kind"], "px": px, "svg": svg})
    og = None
    if p.meta.get("og:image"):
        url = _abs(base, p.meta["og:image"])
        if url:
            og = {"url": url, "w": _int(p.meta.get("og:image:width")),
                  "h": _int(p.meta.get("og:image:height"))}
    imgs = []
    for im in sorted(p.imgs, key=lambda d: (not d["header"], not d["own"], d["order"])):
        url = _abs(base, im["href"])
        if url and url not in seen and len(imgs) < 2:
            seen.add(url)
            imgs.append({"url": url, "kind": "header-img", "px": 0, "svg": _is_svg_url(url)})
    return {"icons": icons, "manifest": _abs(base, p.manifest) if p.manifest else None,
            "og": og, "imgs": imgs}


def parse_icon_links(html: str, base_url: str) -> list[dict]:
    """（第一版留下的介面）只要點陣圖示連結：apple-touch-icon 優先 → 宣告尺寸大的 → 其他。

    略過 SVG、mask-icon 與 data: URI。第二版的完整候選請用 scan_page() ＋ plan_candidates()。
    """
    out = [c for c in scan_page(html, base_url)["icons"]
           if not c["svg"] and c["kind"] in ("apple-touch-icon", "icon")]
    out.sort(key=lambda d: (d["kind"] != "apple-touch-icon", -d["px"]))
    return out


def parse_manifest_icons(raw: bytes, manifest_url: str) -> list[dict]:
    """web app manifest（JSON）裡的 icons → 候選，大的先，最多 2 個。壞掉的 JSON 回空。

    purpose 只有 monochrome 的跳過（那是單色剪影，給系統上色用的，不是 Logo 本體）。
    """
    try:
        d = json.loads(raw.decode("utf-8-sig", errors="replace"))
    except (ValueError, AttributeError):
        return []
    icons = d.get("icons") if isinstance(d, dict) else None
    out = []
    for ic in icons if isinstance(icons, list) else []:
        if not isinstance(ic, dict):
            continue
        purpose = str(ic.get("purpose", "")).lower().split()
        if purpose and "monochrome" in purpose and "any" not in purpose and "maskable" not in purpose:
            continue
        url = _abs(manifest_url, ic.get("src"))
        if not url:
            continue
        svg = str(ic.get("type", "")).lower() == "image/svg+xml" or _is_svg_url(url)
        sizes = str(ic.get("sizes", ""))
        px = _declared_px(sizes) or (512 if svg and "any" in sizes.lower() else 0)
        out.append({"url": url, "kind": "manifest", "px": px, "svg": svg})
    out.sort(key=lambda c: -c["px"])
    return out[:2]


OG_ASPECT = (0.9, 4.0)     # 「接近 1:1～4:1」：寬／高；0.9 是給 1:1 圖量測誤差的容忍


def og_candidate(og: dict | None) -> dict | None:
    """og:image 只在「看起來是 Logo」時才當候選。

    - 檔名／路徑含 logo → 收（下載後仍會擋照片）。
    - 否則要長寬比接近 1:1～4:1（宣告了寬高就先看宣告，不合就連下載都省了），
      下載後再看一次實際長寬比，而且不能是照片（色彩數太多）—— 分享用的活動照、廠房照不是 Logo。
    """
    if not og or not og.get("url"):
        return None
    url = og["url"]
    logo_named = "logo" in urlparse(url).path.lower()
    w, h = og.get("w"), og.get("h")
    if not logo_named and w and h and not (OG_ASPECT[0] <= w / h <= OG_ASPECT[1]):
        return None
    return {"url": url, "kind": "og-image", "px": 0, "svg": _is_svg_url(url), "logo_named": logo_named}



def plan_candidates(scan: dict, origin: str, manifest_icons=()) -> list[dict]:
    """把所有候選排成「下載順序」。會全部評分取最大，順序只影響「提早停」與每家的下載上限。

    1. 宣告 ≥ 64px 的點陣圖示（apple-touch-icon、manifest、icon），大的先
    2. SVG 圖示（向量檔，畫多大都清楚）
    3. 慣例路徑 /apple-touch-icon.png（沒宣告但常常在）
    4. 頁首 logo 圖、og:image（通常就是商標本體，但多半是橫長字標，縮進方框後比圖示小）
    5. 宣告 < 64px 或沒寫尺寸的圖示、慣例路徑 /favicon.ico
    6. mask-icon（Safari 的單色剪影，最後的最後）
    """
    groups: list[list[dict]] = [[] for _ in range(6)]
    for c in list(scan.get("icons") or []) + list(manifest_icons or []):
        if c["kind"] == "mask-icon":
            groups[5].append(c)
        elif c["svg"]:
            groups[1].append(c)
        elif c["px"] >= 64 or (c["kind"] == "manifest" and not c["px"]):
            groups[0].append(c)
        else:
            groups[4].append(c)
    groups[0].sort(key=lambda c: (-c["px"], _KIND_RANK.get(c["kind"], 9)))
    groups[4].sort(key=lambda c: -(c["px"] or 40))     # 沒寫尺寸的，排在 48 與 32 之間
    groups[2].append({"url": urljoin(origin, "apple-touch-icon.png"), "kind": "conventional",
                      "px": 0, "svg": False})
    groups[3].extend(scan.get("imgs") or [])
    og = og_candidate(scan.get("og"))
    if og:
        groups[3].append(og)
    groups[4].append({"url": urljoin(origin, "favicon.ico"), "kind": "conventional", "px": 0, "svg": False})
    out, seen = [], set()
    for g in groups:
        for c in g:
            if c["url"] not in seen:
                seen.add(c["url"])
                out.append(c)
    return out


# ------------------------------------------------------------------ 圖檔 → 64×64 PNG

class LogoReject(Exception):
    """這張圖不能當 Logo。reason：too_small / too_wide / blank / not_logo / bad_image /
    svg_unsupported / none / error / no_pillow。"""

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


def svg_supported() -> bool:
    """cairosvg 裝了、而且系統有 libcairo（沒有的話匯入時會拋 OSError）才畫 SVG。"""
    try:
        import cairosvg  # noqa: F401,WPS433
        return True
    except Exception:  # noqa: BLE001
        return False


def _svg_image(data: bytes):
    """SVG → 點陣圖：依原比例畫成長邊 256px。

    為什麼可以畫 SVG（第一版不畫）：把向量檔依它自己的比例「算繪」成點陣圖，就是瀏覽器顯示它的方式，
    不改形狀、不改色、不裁切，跟縮放點陣圖是同一件事。第一版寫「縮放 SVG 等於重畫」太保守，
    結果大公司頁首的 SVG Logo 全部拿不到。
    安全：cairosvg ≥ 2.7 在 unsafe=False（預設）時不讀外部檔案、不解析 XML 實體；再加大小上限。
    """
    Image = _pil()
    if len(data) > config.LOGO_SVG_MAX_BYTES:
        raise LogoReject("bad_image", f"SVG 太大（{len(data)} bytes）")
    try:
        import cairosvg  # noqa: WPS433
    except Exception as exc:  # noqa: BLE001 —— ImportError，或沒有 libcairo 的 OSError
        raise LogoReject("svg_unsupported", f"沒有 cairosvg／libcairo：{str(exc)[:60]}") from exc
    try:
        img = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=data, output_width=_SVG_PX, unsafe=False)))
        img.load()
        if img.height > img.width:
            img = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=data, output_height=_SVG_PX,
                                                         unsafe=False)))
            img.load()
    except Exception as exc:  # noqa: BLE001
        raise LogoReject("bad_image", f"SVG 畫不出來：{str(exc)[:80]}") from exc
    return img


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


# 照片判定的門檻（2026-09-26 用資料湖裡第一輪抓到的 214 張 Logo 校過：5 bit 色數最高 514，
# 只有 1 張（3289 宜特，JPEG 壓縮雜訊）到 1,566，但它前 8 種顏色仍佔 42%）
PHOTO_COLORS_STRICT = 600    # 嚴格：色數超過這個就算照片（沒有任何 logo 字樣的 og:image 用）
PHOTO_COLORS_LENIENT = 1200  # 寬鬆：色數超過這個「而且」前 8 種顏色佔不到 35% 才算照片
PHOTO_TOP8_SHARE = 0.35      # （路徑含 logo 的 og:image、頁首 logo 圖用 —— 已經有「它是 Logo」的強訊號）


def is_photo(img, strict: bool = False) -> bool:
    """og:image 與頁首圖用：是照片就不是 Logo。

    做法：貼到白底、NEAREST 取樣成 64×64（不取平均 —— 取平均會把照片的細節抹成一片灰），
    每個色版只留 5 bit，數有幾種顏色；再用 4 bit 看「前 8 種顏色佔多少格」。
    Logo 是幾塊平塗色加反鋸齒邊：色數有限、而且少數幾種顏色就佔掉大半；照片兩樣都相反。
    strict 只看色數（沒有 logo 字樣的 og:image 是最容易抓錯的來源，寧可不收）；
    寬鬆模式兩個條件都要成立，免得 JPEG 壓縮雜訊把真正的 Logo 誤判成照片。
    """
    Image = _pil()
    rgba = img.convert("RGBA")
    canvas = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    canvas.alpha_composite(rgba)
    small = canvas.convert("RGB").resize((64, 64), Image.NEAREST)
    n5 = len(small.point(lambda v: v & 0xF8).getcolors(maxcolors=64 * 64 + 1) or [])
    if strict:
        return n5 > PHOTO_COLORS_STRICT
    if n5 <= PHOTO_COLORS_LENIENT:
        return False
    c4 = sorted(small.point(lambda v: v & 0xF0).getcolors(maxcolors=64 * 64 + 1) or [], reverse=True)
    return sum(n for n, _ in c4[:8]) / (64 * 64) < PHOTO_TOP8_SHARE


def effective_px(w: int, h: int) -> float:
    """縮進 64×64 方框之後「看得到的大小」：短邊 × 解析度（超過 64 不加分）。

    這就是「取最大」的「大」：正方形 180px 圖示 ＝ 64、32px favicon ＝ 32、300×100 橫長字標 ＝ 21。
    前端顯示 20～32px，正方形圖示比橫長字標清楚得多，所以不能只比原始像素。
    """
    if not w or not h:
        return 0.0
    return min(max(w, h), config.LOGO_PX) * min(w, h) / max(w, h)


def normalize_image(data: bytes, *, photo_check: bool | str = False,
                    aspect: tuple[float, float] | None = None) -> tuple[bytes, tuple[int, int]]:
    """任何 Pillow 讀得懂的圖（ICO／PNG／JPEG／GIF／WebP／BMP）或 SVG → 64×64 透明底 PNG。

    ICO 內含多種尺寸時 Pillow 預設開最大的那張。等比縮到 64 以內再置中貼到透明畫布，
    不裁切、不拉伸、不改色 —— 只縮放，這是「指稱性使用、不修改圖形」的技術面保證。
    非正方形（橫長字標）就上下補透明邊；長寬比超過 LOGO_MAX_ASPECT 的判太小（縮完只剩一條線）。
    photo_check：是照片就擋（True＝寬鬆、"strict"＝嚴格，見 is_photo）；aspect：限定寬／高範圍（沒寫 logo 的 og:image 用）。
    """
    Image = _pil()
    head = data[:1024].lstrip().lower()
    if head[:1] == b"<":
        if b"<svg" not in data[:8192].lower():
            raise LogoReject("none", "回的是 HTML 不是圖")
        img = _svg_image(data)
        vector = True
    else:
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception as exc:  # noqa: BLE001
            raise LogoReject("bad_image", str(exc)[:120]) from exc
        vector = False
    try:
        img.seek(0)          # 動態 GIF 取第一格
    except Exception:  # noqa: BLE001
        pass
    w, h = img.size
    if not vector and max(w, h) < config.LOGO_MIN_PX:
        raise LogoReject("too_small", f"{w}x{h}")
    if min(w, h) <= 0 or max(w, h) / min(w, h) > config.LOGO_MAX_ASPECT:
        raise LogoReject("too_wide", f"{w}x{h}")
    if aspect and not (aspect[0] <= w / h <= aspect[1]):
        raise LogoReject("not_logo", f"長寬比不像 Logo {w}x{h}")
    rgba = img.convert("RGBA")
    if is_blank(rgba):
        raise LogoReject("blank", f"{w}x{h}")
    if photo_check and is_photo(rgba, strict=photo_check == "strict"):
        raise LogoReject("not_logo", f"看起來是照片 {w}x{h}")
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


def robots_rules(root: str):
    """讀官網的 robots.txt，回一個「這個網址能不能抓」的判斷函式（`.why` 記禁止的原因，寫進 log 用）。

    robots.txt 抓不到（404／連線失敗／內容不是規則）＝ 沒有限制；
    401／403 依 robotparser 的慣例視為全站禁止。一律以一般爬蟲（*）的規則判斷。
    首頁與每一個圖示網址都要過這一關（有的站只擋 /images/ 之類的目錄）。
    """
    def allow_all(url):
        return True
    allow_all.why = ""
    res = _get(urljoin(root, "/robots.txt"), timeout=6, max_bytes=200_000)
    if res is None:
        return allow_all
    status, body, _ctype, _final = res
    if status in (401, 403):
        def deny(url):
            return False
        deny.why = f"robots.txt 回 HTTP {status}（依 robotparser 慣例視為全站禁止）"
        return deny
    if status != 200:
        return allow_all
    rp = RobotFileParser()
    try:
        rp.parse(body.decode("utf-8", errors="replace").splitlines())
    except Exception:  # noqa: BLE001
        return allow_all

    def by_rules(url):
        return rp.can_fetch("*", url)
    by_rules.why = "robots.txt 的 Disallow 規則不允許"
    return by_rules


def robots_allows(root: str, page: str) -> bool:
    return robots_rules(root)(page)


# 每種候選的「可信度」：有效尺寸一樣大時，官方圖示優先於頁首圖，頁首圖優先於 og:image
_KIND_RANK = {"apple-touch-icon": 0, "manifest": 0, "icon": 1, "conventional": 1, "google_s2": 1,
              "header-img": 2, "og-image": 3, "mask-icon": 4}


def _try_image(url: str, kind: str = "icon", logo_named: bool = True) -> tuple[bytes, tuple[int, int]] | LogoReject:
    res = _get(url, timeout=8, max_bytes=2_000_000 if kind == "og-image" else 1_000_000)
    if res is None:
        return LogoReject("error", f"連線失敗 {url}")
    status, body, _ctype, _final = res
    if status != 200 or not body:
        return LogoReject("none", f"HTTP {status} {url}")
    # 以「內容」判斷，不信 Content-Type（有的站圖檔也標 text/html）：
    # 很多站對不存在的 /favicon.ico 回 200 ＋ 首頁 HTML（軟 404）；SVG 也是 < 開頭，由 normalize_image 分辨
    try:
        bare_og = kind == "og-image" and not logo_named     # 沒有任何 logo 字樣的 og:image：最嚴
        return normalize_image(body,
                               photo_check="strict" if bare_og else kind in ("og-image", "header-img"),
                               aspect=OG_ASPECT if bare_og else None)
    except LogoReject as rej:
        rej.detail = f"{rej.detail} {url}".strip()
        return rej


# 失敗原因的「嚴重度」：多個候選都失敗時，回報最有資訊量的那一個
_REASON_RANK = {"too_small": 6, "too_wide": 6, "blank": 5, "not_logo": 4, "bad_image": 3,
                "svg_unsupported": 3, "none": 2, "error": 1}


def fetch_logo(website, host: str | None = None) -> dict:
    """抓一家公司的 Logo。回 {status, src, png, orig, detail, domain[, site]}；status＝ok 時 png 有值。

    site：首頁轉址到同公司的另一個網域時，記下實際取圖的主機（例如 www.aoet.com.tw → www.aoet.com）。
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


def _open_home(url: str, host: str, rules) -> tuple:
    """打開首頁，**自己一跳一跳地跟轉址**：每一跳先確認是同一家公司的網域、再過那個網域的 robots.txt。

    回 ("page", 狀態碼, 內容, 最終網址) / ("robots", 網域根, 原因) / ("foreign", 轉到哪) / ("down", 說明)。
    """
    cur = url
    for _hop in range(6):
        origin = _origin(cur)
        allowed = rules(origin)
        if not allowed(cur):
            return ("robots", origin, getattr(allowed, "why", "") or "robots.txt 不允許")
        res = _get(cur, timeout=10, max_bytes=2_000_000, allow_redirects=False)
        if res is None:
            return ("down", f"首頁連線失敗 {cur}")
        status, body, _ctype, nxt = res
        if 300 <= status < 400:
            if not nxt or nxt == cur:
                return ("down", f"首頁 HTTP {status} 沒有可跟的 Location {cur}")
            nh = urlparse(nxt).hostname
            if not same_company(host, nh):
                return ("foreign", nxt)
            cur = nxt
            continue
        return ("page", status, body, cur)
    return ("down", f"首頁轉址超過 5 次 {url}")


def _fetch_logo(website, host: str) -> dict:
    worst: LogoReject | None = None

    def keep(rej: LogoReject):
        nonlocal worst
        if worst is None or _REASON_RANK.get(rej.reason, 0) > _REASON_RANK.get(worst.reason, 0):
            worst = rej

    robots_cache: dict = {}

    def rules(origin: str):
        if origin not in robots_cache:
            robots_cache[origin] = robots_rules(origin)
        return robots_cache[origin]

    # ① 官網首頁（404 或連不上就換 scheme、換 www／非 www；轉址只跟同一家公司的網域）
    page, reachable = None, None
    for home in homepage_candidates(website, host):
        got = _open_home(home, host, rules)
        if got[0] == "robots":
            return {"status": "robots", "domain": host,
                    "detail": f"{got[1]} {got[2]} —— 尊重它，也不走 Google 備援"[:200]}
        if got[0] == "down":
            keep(LogoReject("error", got[1]))
            continue
        if got[0] == "foreign":
            keep(LogoReject("none", f"首頁轉到別家網域 {got[1]}，不跟"))
            continue
        _, status, body, final = got
        reachable = reachable or final
        if status == 200 and body:
            page = (body, final)
            break
        keep(LogoReject("none", f"首頁 HTTP {status} {final}"))
        if status not in (404, 410):
            break          # 403／5xx 換網址也一樣，別浪費對方的資源

    site_ok = reachable is not None
    cands: list[dict] = []
    final_host = None
    if site_ok:
        base_url = page[1] if page else reachable
        final_host = urlparse(base_url).hostname
        origin = _origin(base_url)
        allowed = rules(origin)
        scan = (scan_page(page[0].decode("utf-8", errors="replace"), page[1]) if page
                else {"icons": [], "manifest": None, "og": None, "imgs": []})
        man_icons: list[dict] = []
        mu = scan.get("manifest")
        if mu and (urlparse(mu).netloc != urlparse(origin).netloc or allowed(mu)):
            res = _get(mu, timeout=6, max_bytes=200_000)
            if res and res[0] == 200 and res[1]:
                man_icons = parse_manifest_icons(res[1], res[3] or mu)
        cands = plan_candidates(scan, origin, man_icons)
        # 同網域的圖檔要過 robots（有的站只擋 /images/）；CDN 上的圖檔照第一版的做法直接抓
        cands = [c for c in cands if urlparse(c["url"]).netloc != urlparse(origin).netloc or allowed(c["url"])]

    best: dict | None = None
    can_svg = None
    tries = 0
    for c in cands:
        if tries >= config.LOGO_MAX_TRIES:
            break
        if c["svg"]:
            if can_svg is None:
                can_svg = svg_supported()
            if not can_svg:
                keep(LogoReject("svg_unsupported", f"沒有 cairosvg／libcairo，跳過 SVG {c['url']}"))
                continue
        tries += 1
        got = _try_image(c["url"], c["kind"], c.get("logo_named", True))
        if isinstance(got, LogoReject):
            keep(got)
            continue
        png, orig = got
        cand = {**c, "png": png, "orig": orig, "eff": effective_px(*orig)}
        if best is None or _score(cand) > _score(best):
            best = cand
        if cand["eff"] >= config.LOGO_PX and _KIND_RANK.get(c["kind"], 9) <= 1:
            break          # 已經有 ≥64px 的正方形官方圖示，不必再下載其他候選

    # ② Google 備援：官網沒有，或官網最好的也只有 32～47px 時，問 Google 有沒有更大的
    if best is None or best["eff"] < 48:
        s2 = config.LOGO_GOOGLE_S2.format(domain=host)
        got = _try_image(s2, "google_s2")
        if isinstance(got, LogoReject):
            keep(got)
        else:
            png, orig = got
            cand = {"url": s2, "kind": "google_s2", "png": png, "orig": orig, "eff": effective_px(*orig)}
            if best is None or _score(cand) > _score(best):
                best = cand

    extra = {}
    if final_host and final_host != host:
        extra["site"] = final_host      # 連 www ↔ 非 www 也記：下一個人查「為什麼圖是從這裡來的」才對得上
    if best is not None:
        src = "google_s2" if best["kind"] == "google_s2" else f"site:{best['kind']}"
        return {"status": "ok", "domain": host, "src": src, "url": best["url"],
                "png": best["png"], "orig": list(best["orig"]), **extra}
    reason = worst.reason if worst else "none"
    if reason == "too_wide":
        reason = "too_small"
    status = reason if reason in ("too_small", "blank", "error") else "none"
    if status == "error" and site_ok:
        status = "none"
    return {"status": status, "domain": host, "detail": (worst.detail if worst else "")[:200], **extra}


def _score(c: dict) -> tuple:
    """「最大」的比較鍵：有效尺寸（取整，避免 63.9 跟 64 這種誤差翻盤）→ 候選可信度 → 原圖長邊。"""
    return (round(c["eff"]), -_KIND_RANK.get(c["kind"], 9), max(c["orig"]))


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


# 取圖策略升級時要「立刻重試」的失敗狀態：只有這兩種是「方法不夠好」造成的。
# robots（對方不准）、blank／generic（圖本身不能用）、error（連線問題）換了方法也一樣，照 30 天規則。
RETRY_ON_UPGRADE = ("too_small", "none")


def retry_on_upgrade(rec: dict) -> bool:
    """這筆是用比 config.LOGO_STRATEGY 舊的策略判成「太小／找不到」的 → 下一輪立刻重試。

    沒記 strategy 的舊紀錄一律當第 1 版。重試完會記上新版號，之後回到一般的 30 天規則，
    不會每輪都重抓。抓到的好圖（ok）不在這裡 —— 策略升級不去動已經有的圖，只補沒有的。
    """
    if rec.get("status") not in RETRY_ON_UPGRADE:
        return False
    try:
        ver = int(rec.get("strategy") or 1)
    except (TypeError, ValueError):
        ver = 1
    return ver < config.LOGO_STRATEGY


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
    """這一輪要抓哪些：策略升級要重試的 → 沒抓過的 → 網域換了的 → 到期重抓的（最舊的先）。

    沒抓過的裡面，`priority`（族群成分股）排前面 —— 使用者最常點的股票先有圖。
    策略升級要重試的（`retry_on_upgrade()`）排最前面：第一輪判「太小／找不到」的正是
    台積電、聯電、欣興這些大公司，Andy 最先看的就是它們，不能等 30 天、也不能排在 1,600 家新的後面。
    """
    items = idx.get("items", {})
    prio = {c: i for i, c in enumerate(priority or [])}
    retry, fresh, changed, due = [], [], [], []
    for r in sites.itertuples(index=False):
        code = clean_code(r.code)
        if not code:
            continue
        host = extract_domain(r.website)
        rec = items.get(code)
        row = {"code": code, "website": r.website, "domain": host}
        if rec is None:
            fresh.append(row)
        elif rec.get("status") == "removed":
            continue          # 人工下架的（見 docs/logo_sources.md「只移除某一家」），永遠不重抓
        elif base_domain(rec.get("domain")) != base_domain(host):
            changed.append(row)
        elif retry_on_upgrade(rec):
            retry.append(row)
        elif _due(rec, today):
            due.append((str(rec.get("fetched") or ""), row))
    fresh.sort(key=lambda d: (prio.get(d["code"], len(prio)), d["code"]))
    retry.sort(key=lambda d: (prio.get(d["code"], len(prio)), d["code"]))
    due.sort(key=lambda t: t[0])
    return (retry + fresh + changed + [r for _, r in due])[:max(0, limit)]


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
        rec = {"status": st, "domain": res.get("domain"), "fetched": stamp,
               "strategy": config.LOGO_STRATEGY}
        if res.get("site"):
            rec["site"] = res["site"]      # 首頁轉到同公司的另一個網域：記下來，網域變了要看得到
        if st == "ok":
            rec.update(src=res.get("src"), url=res.get("url"), orig=res.get("orig"),
                       sha1=_save_png(code, res["png"], old.get("sha1")))
        else:
            rec["detail"] = res.get("detail", "")
            failures.append({"code": code, "status": st, "domain": res.get("domain"),
                             "detail": res.get("detail", "")})
            if old.get("status") == "ok" and (logo_dir() / f"{code}.png").exists():
                # 之前抓到過、這次沒抓到（官網暫時掛掉）：保留舊圖，只延後下一次重抓
                rec = {**old, "fetched": stamp, "last_fail": st, "strategy": config.LOGO_STRATEGY}
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
    dues = [d for d in (next_due(r) for r in items.values() if r.get("status") != "removed") if d]
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
