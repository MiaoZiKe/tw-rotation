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

第三版（2026-09-26 深夜，`LOGO_STRATEGY`＝3）：Andy 截圖問聯電、南亞科、欣興、長榮航為什麼還是字母頭像
--------------------------------------------------------------------------------------------------
- **小圖當後備**：官網找不到 ≥48px 的圖時，官網最大的那張只要 ≥16px 就收（索引 `status: ok`＋`lowres: true`）。
  前端只顯示 20～32px，16px 官方 favicon 在那個尺寸幾乎是原生大小，比字母頭像好認。
  **照原尺寸存**（16×16 就是 16×16，只補透明邊成正方形），不放大重採樣 —— 理由見 normalize_image()。
  Google s2 的小圖不收（第三方來源仍要 ≥32px）。長寬比超過 5:1 的橫長字標照樣判太小。
- **預設圖拒收後繼續往下找**：第二版是整輪抓完才發現「這張跟 14 個網域同一張」、刪檔判 generic，那家就沒圖；
  而且那張 64px 預設 favicon 會讓「提早停」與「不必問 s2」成立，後面的頁首圖、s2 根本沒試。
  第三版把已知預設圖的雜湊傳進 fetch_logo()，抓到就跳過、不提早停，繼續試頁首圖／manifest／og:image／s2。
  已知雜湊記進索引 `generic_sha1`，那幾家換成真 Logo 之後也不會忘記那張是預設圖。
- **找不到（none）沒有第二備援**：評估過 DuckDuckGo `icons.duckduckgo.com/ip3` 等公開 favicon 快取，不採用
  （無公開條款、DuckDuckGo 一般條款據摘要限制自動化使用、而且等於透過第三方繞過官網對我們的阻擋；
  細節見 docs/logo_sources.md §1.2 與 DECISIONS #267）。robots 不准的公司照舊不走任何備援。
- 「太小／找不到／預設圖」三種在策略升級後最先重試；好圖不重抓、不覆寫。

第四版（2026-09-28，`LOGO_STRATEGY`＝4，DECISIONS #276）：Andy「有個股還是沒有公司 Logo」（例：8038 長園科）
--------------------------------------------------------------------------------------------------------
- **robots.txt 照 RFC 9309 判**：回 4xx（含 401、403）＝「不可取得」，可以抓（§2.3.1.3）；5xx／連不上＝暫時全站禁止（§2.3.1.4），
  這輪不抓、記 error；429 也是這輪不抓。第三版以前照 robotparser 把 401／403 當全站禁止（比標準嚴），5xx 當沒限制（比標準鬆）。
  **寫了 Disallow 的照舊尊重**，官網一個檔都不碰、也不問 Google s2。見 robots_rules()。
- **第二來源 Wikidata／Wikimedia Commons**（logo_wikimedia.py）：官網拿不到圖、或只有低解析小圖時，
  用證券代號／公司全名找 Wikidata 條目的標誌圖片（P154），只收 PD／CC0（CC BY／BY-SA 要等網站畫面有出處連結才開 `LOGO_WIKIMEDIA_ALLOW_BY`），
  出處記進索引 `attribution`，
  署名清單寫在 `data/logos/ATTRIBUTION.md`。它是公開授權的圖庫、不是去爬公司官網，所以 robots 不准的公司也可以用。
- **人工指定**（data/logos/manual/<代號>.png ＋ manual.json）：最優先，回補永遠不覆寫。見 apply_manual()。
- **不做**：用程式去 Google 圖片搜尋抓圖（Google 服務條款禁止自動化查詢；搜尋結果的圖來源與授權不明，可能抓到別家公司或未授權的圖）。
- robots／none／too_small／generic／blank／error 與低解析 ok 在策略升級後最先重試。

第四版・官網那條路再往下挖（2026-09-29 收尾）：第三版的 none 168 家裡，約 77 家是「首頁打得開、卻一個候選都沒有」
（詳細紀錄的第一個失敗是 /apple-touch-icon.png 404），這種站多半是下面幾種長相，第三版一律看不到：
- **入口頁**：首頁只有 `<meta http-equiv=refresh>`、`<frameset><frame src>`、`location.href='…'`，
  或只有「繁體中文／English」兩顆按鈕（`hreflang`、href 含 /tw/、zh-tw、cht…）。首頁候選太弱時，
  **最多再開 2 頁**（同一家公司的網域，每一頁照樣過 robots）把候選併進來。見 follow_links()。
- **頁首 Logo 不叫 logo**：`<a href="/">` 首頁連結包著的第一張圖（台灣老網站常見 `<a href="index.html" title="回首頁"><img src="images/top_01.png">`）、
  schema.org 的 `"logo"`（JSON-LD）與 `itemprop="logo"`、頁首 inline `<svg>`、CSS `background-image` 寫在 logo 元素上的圖、
  `msapplication-TileImage`（Windows 磚圖示，通常 144px）與 browserconfig.xml。
- **申報的網址帶路徑**（例 `https://www.nanyapcb.com.tw/nypcb/Chinese/index`）：先開申報的那一頁，不只開網域根目錄。
- **同集團母公司官網**：申報的官網轉址到別的網域（集團共用官網）時，**那一頁提到這家公司的名稱**才跟過去取圖；
  沒提到就不跟（可能是停放頁、被併購後的新東家，掛上去會是別家的 Logo）。
- robots.txt 與首頁**都**回 401／403（對方擋雲端存取）時，不再請 Google s2 代抓 —— 那跟 #267 不用 DuckDuckGo 是同一個理由。

判定「沒有」的情況（寧可退回字母頭像，也不存假 Logo）
----------------------------------------------------
- `too_small`：原圖長邊 < `config.LOGO_LOWRES_MIN_PX`（16，官網圖）／`config.LOGO_MIN_PX`（32，Google s2），
  或長寬比超過 `config.LOGO_MAX_ASPECT`（橫條字標縮進 64×64 只剩一條線）
- `blank`：全透明，或在白底與黑底上看都是單一顏色（空白佔位圖）
- `generic`：同一張圖（雜湊相同）出現在 ≥ `config.LOGO_GENERIC_DOMAINS` 個**不同網域** ——
  那是 Google 的地球、架站商的預設圖示，不是那家公司的 Logo
- `robots`：官網 robots.txt 的 **Disallow 規則**不允許一般爬蟲抓首頁 —— 尊重它，**連 Google 備援也不用**
  （用 Google 繞過去等於繞 robots，那是紅線）。第四版起 robots.txt 回 4xx 不算（RFC 9309），
  而 Wikimedia Commons 的自由授權圖仍可用（不是去爬那個官網，DECISIONS #276）
- `none`：兩個來源都沒有可用的圖
- `error`：連線失敗、逾時、圖檔壞掉

存放（DECISIONS #155：會重複用到的一律進資料湖，不准每次重抓）
------------------------------------------------------------
- `data/logos/<code>.png`：64×64 PNG（等比縮放、置中、透明補邊 —— 不裁切、不拉伸、不改色）；
  低解析（原圖長邊 < 48）照原尺寸存成正方形 PNG（例 16×16），不放大
- `data/logos/_index.json`：代號 → 狀態、來源、網域、抓取日、雜湊、原圖尺寸
- `data/_state/logo_progress.json`：每輪摘要、這輪的失敗清單、還有幾家待抓、下一次到期日
  （`backfill.yml` 的排程守門看這份決定要不要放行）
PNG 不是 Parquet：90 天重抓時如果圖真的變了會換掉舊檔（雜湊一樣就不寫，git 不會多一個版本）。
被判成 generic 的會刪掉檔案 —— 那本來就不該存在。

增量
----
策略升級（`config.LOGO_STRATEGY` 加一）後，舊策略判「太小／找不到／預設圖」的最先重試；
其次是沒抓過的（族群成分股優先，使用者最常看的先有圖），再來是抓到超過 90 天的、
沒抓到（或只有低解析圖）超過 30 天的。已經抓到的好圖不因為策略升級而重抓。每輪最多 `config.LOGOS_PER_RUN` 家、最多 `config.LOGO_TIME_BUDGET_SEC` 秒。
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
    # 第四版：申報的網址帶路徑（/tw/、/nypcb/Chinese/index）→ 先開那一頁。網域根目錄常常只是入口頁或 404，
    # 公司自己申報的那一頁才是它的「官網首頁」。那一頁 404 就照舊退回根目錄。
    path = declared_path(raw, host)
    if path:
        out.insert(0, f"{first}://{host}{path}")
    return out


def declared_path(website, host: str) -> str | None:
    """申報網址裡、主機是 host 的那一個所帶的路徑（含查詢字串）；沒有路徑或只有 / 回 None。"""
    for part in re.split(r"[\s;,、，；]+", str(website or "").strip()):
        if not part:
            continue
        url = part if re.match(r"^[a-z][a-z0-9+.-]*://", part, re.I) else "http://" + part
        try:
            u = urlparse(url)
        except ValueError:
            continue
        if (u.hostname or "").lower().strip(".") != host:
            continue
        path = u.path or ""
        if not path.strip("/"):
            return None
        return path + (f"?{u.query}" if u.query else "")
    return None


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
    """一次掃過首頁：圖示類 <link>、manifest、og:image、「看起來是自家 Logo」的 <img>，
    以及第四版加的：入口頁要跟的下一頁、首頁連結包著的圖、JSON-LD／itemprop 的 logo、頁首 inline SVG、
    logo 元素上的 CSS 背景圖、msapplication 磚圖示。

    頁首判斷用一個寬鬆的標籤堆疊：<header>、或 class／id 含 header／navbar／masthead 的元素算「頁首」，
    <footer> 或 class／id 含 footer 的算「頁尾」（頁尾的 logo 多半是合作夥伴、認證標章，一律不收）。
    `<a href="/">`（指回首頁的連結）算「home」區 —— 網站 Logo 幾乎都包在回首頁的連結裡，
    台灣老網站的 Logo 圖檔名常常是 top_01.png、header.gif，名字裡沒有 logo，第三版全部漏掉。
    壞掉、沒關的 HTML 很常見：結束標籤只往上找 64 層，找不到就當沒看到，堆疊最多 2000 層。
    """

    def __init__(self, raw: str = "", base_url: str = ""):
        super().__init__(convert_charrefs=True)
        self.raw = raw
        self.base_url = base_url
        self.links: list[dict] = []
        self.base: str | None = None
        self.manifest: str | None = None
        self.meta: dict[str, str] = {}
        self.imgs: list[dict] = []
        self._stack: list[tuple[str, frozenset]] = []
        # 第四版
        self.refresh: str | None = None
        self.frames: list[str] = []
        self.alternates: list[str] = []     # <link rel=alternate hreflang=zh-TW>、<a hreflang=zh-TW>
        self.lang_links: list[str] = []     # href 看起來是繁中版首頁的 <a>
        self.itemprop: list[str] = []
        self.jsonld_raw: list[str] = []
        self.css_urls: list[str] = []
        self.style_raw: list[str] = []
        self.svgs: list[str] = []
        self.tiles: list[dict] = []
        self.browserconfig: str | None = None
        self.home_imgs: list[str] = []
        self._img_seen = 0
        self._svg_depth = 0
        self._svg_start: int | None = None
        self._svg_keep = False
        self._text_tag: str | None = None   # 正在收內容的 <script type=ld+json> 或 <style>
        self._text_buf: list[str] = []
        self._line_starts: list[int] | None = None

    # ---- 位置：getpos() 是（行, 欄），切 inline SVG 原文要換成字元位移
    def _offset(self) -> int:
        if self._line_starts is None:
            starts, pos = [0], 0
            for line in self.raw.splitlines(keepends=True):
                pos += len(line)
                starts.append(pos)
            self._line_starts = starts
        line, col = self.getpos()
        return self._line_starts[min(line - 1, len(self._line_starts) - 1)] + col

    def _zones(self) -> set:
        z: set = set()
        for _t, zs in self._stack:
            z |= zs
        return z

    def _is_home(self, href: str) -> bool:
        """這個連結是不是指回網站首頁：/、./、index.*／default.*／home.*，或絕對網址的路徑是根目錄或就是這一頁。"""
        h = (href or "").strip()
        if not h or h.startswith(("#", "javascript:", "mailto:", "tel:")):
            return False
        if re.match(r"^(\./|/)?((index|default|home)\.(html?|php|aspx?|jsp))?(\?[^#]*)?$", h, re.I):
            return True
        if not self.base_url:
            return False
        try:
            u, b = urlparse(urljoin(self.base_url, h)), urlparse(self.base_url)
        except ValueError:
            return False
        if u.netloc.lower() != b.netloc.lower():
            return False
        return u.path in ("", "/") or u.path.rstrip("/") == b.path.rstrip("/")

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "base":
            if a.get("href") and self.base is None:
                self.base = a["href"]
            return
        if a.get("itemprop", "").lower() == "logo":
            v = a.get("content") or a.get("src") or a.get("href")
            if v and len(self.itemprop) < 3:
                self.itemprop.append(v)
        if tag == "link":
            return self._link(a)
        if tag == "meta":
            return self._meta(a)
        cid = f"{a.get('class', '')} {a.get('id', '')}".lower()
        zones_now = self._zones()
        if a.get("style") and ("logo" in cid or "logo" in zones_now) and "footer" not in zones_now:
            for m in _CSS_URL.finditer(a["style"]):
                if len(self.css_urls) < 3:
                    self.css_urls.append(m.group(2))
        if tag == "img":
            return self._img(a)
        if tag in ("frame", "iframe"):
            if a.get("src") and len(self.frames) < 3 and (tag == "frame" or "footer" not in zones_now):
                self.frames.append(a["src"])
            if tag == "frame":
                return
        if tag in ("script", "style") and self._text_tag is None:
            if tag == "style" or "ld+json" in a.get("type", "").lower():
                self._text_tag, self._text_buf = tag, []
        if tag == "svg":
            if self._svg_depth == 0:
                own = " ".join(a.get(k, "") for k in ("class", "id", "aria-label", "role")).lower()
                self._svg_keep = ("footer" not in zones_now and not _NOT_OWN_LOGO.search(own)
                                  and ("logo" in own or "logo" in zones_now
                                       or ("home" in zones_now and "header" in zones_now)))
                self._svg_start = self._offset() if self._svg_keep and len(self.svgs) < 2 else None
            self._svg_depth += 1
        if tag == "a":
            hl = a.get("hreflang", "").lower().replace("_", "-")
            href = a.get("href", "")
            if href and hl in _ZH_TW_LANGS and len(self.alternates) < 3:
                self.alternates.append(href)
            elif href and _LANG_HREF.search(href) and len(self.lang_links) < 3:
                self.lang_links.append(href)
        if tag in _VOID or len(self._stack) >= 2000:
            return
        zs = set()
        if tag == "header" or re.search(r"header|masthead|navbar|topbar|top-bar", cid):
            zs.add("header")
        if tag == "footer" or "footer" in cid:
            zs.add("footer")
        if "logo" in cid or ("brand" in cid and ("header" in zs or "header" in zones_now)):
            zs.add("logo")
        if tag == "a" and self._is_home(a.get("href", "")):
            zs.add("home")
        self._stack.append((tag, frozenset(zs)))

    def handle_endtag(self, tag):
        if tag == self._text_tag:
            text = "".join(self._text_buf)[:200_000]
            (self.style_raw if tag == "style" else self.jsonld_raw).append(text)
            self._text_tag, self._text_buf = None, []
        if tag == "svg" and self._svg_depth > 0:
            self._svg_depth -= 1
            if self._svg_depth == 0 and self._svg_start is not None:
                end = self.raw.find(">", self._offset())
                if end > self._svg_start:
                    frag = self.raw[self._svg_start:end + 1]
                    if len(frag) <= config.LOGO_SVG_MAX_BYTES:
                        self.svgs.append(frag)
                self._svg_start = None
        lo = max(0, len(self._stack) - 64)
        for i in range(len(self._stack) - 1, lo - 1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        if self._text_tag is not None and sum(map(len, self._text_buf)) < 200_000:
            self._text_buf.append(data)

    def _link(self, a):
        rel = a.get("rel", "").lower().split()
        href = a.get("href", "").strip()
        if not href or not rel:
            return
        if "manifest" in rel:
            self.manifest = self.manifest or href
            return
        if "alternate" in rel:
            if a.get("hreflang", "").lower().replace("_", "-") in _ZH_TW_LANGS and len(self.alternates) < 3:
                self.alternates.append(href)
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
        if a.get("http-equiv", "").strip().lower() == "refresh" and val and self.refresh is None:
            m = re.search(r"url\s*=\s*['\"]?([^'\";]+)", val, re.I)
            if m:
                self.refresh = m.group(1).strip()
            return
        if not val:
            return
        if key in ("og:image", "og:image:url", "og:image:secure_url"):
            self.meta.setdefault("og:image", val)
        elif key in ("og:image:width", "og:image:height"):
            self.meta.setdefault(key, val)
        elif key in _MS_TILES:
            self.tiles.append({"href": val, "px": _MS_TILES[key]})
        elif key == "msapplication-config" and val.lower() != "none":
            self.browserconfig = self.browserconfig or val

    def _img(self, a):
        self._img_seen += 1
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
            # 第四版：回首頁連結包著的圖（頁首裡的，或整頁前 6 張圖以內的），只收第一張；
            # 檔名像按鈕、小圖示的（home.png、icon_*、arrow、flag）不收 —— 那是「回首頁」的房子圖示，不是 Logo
            if ("home" in zones and not self.home_imgs and ("header" in zones or self._img_seen <= 6)
                    and not _NOT_HOME_LOGO.search(urlparse(src).path.rsplit("/", 1)[-1])
                    and not _NOT_OWN_LOGO.search(own)):
                self.home_imgs.append(src)
            return
        if _NOT_OWN_LOGO.search(own):
            return
        self.imgs.append({"href": src, "header": "header" in zones, "own": own_logo,
                          "order": len(self.imgs)})


# 第四版的解析常數
_ZH_TW_LANGS = {"zh-tw", "zh-hant", "zh-hant-tw", "zh"}
# 入口頁上「繁體中文版」的連結：/tw/、/zh-tw/、/cht/、/big5/、/ch/、?lang=zh-tw、index_tw.html …
_LANG_HREF = re.compile(r"(^|[/_?=&.-])(zh[-_]?tw|zh[-_]?hant|tw|cht|big5|ch|tc|chinese)([/_.?&#-]|$)", re.I)
_CSS_URL = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", re.I)
# <style> 裡「選擇器含 logo」的那條規則的背景圖：.logo{background:url(images/logo.png)}、#header .brand-logo a{…}
_CSS_LOGO_RULE = re.compile(r"([^{}]*logo[^{}]*)\{([^{}]*)\}", re.I)
_MS_TILES = {"msapplication-tileimage": 144, "msapplication-square150x150logo": 150,
             "msapplication-square310x310logo": 310, "msapplication-square70x70logo": 70}
_NOT_HOME_LOGO = re.compile(r"home|house|icon|arrow|btn|button|search|menu|lang|flag|spacer|blank|pixel|close", re.I)
_JS_REDIRECT = re.compile(
    r"""(?:(?:window|document|top|self|parent)\.)?location(?:\.href)?\s*=\s*['"]([^'"\s]{1,300})['"]"""
    r"""|location\.(?:replace|assign)\(\s*['"]([^'"\s]{1,300})['"]""")


def jsonld_logos(texts) -> list[str]:
    """JSON-LD（schema.org）裡的 "logo"：字串、{"url"|"contentUrl": …} 或它們的陣列。壞掉的 JSON 略過。

    Organization／Corporation 的 logo 就是那家公司自己宣告的 Logo（Yoast 等外掛會自動輸出），
    訊號跟 apple-touch-icon 一樣強，只是常常是橫長字標。publisher.logo 也收：公司官網的 publisher 就是自己。
    """
    out: list[str] = []

    def val(v):
        if isinstance(v, dict):
            v = v.get("url") or v.get("contentUrl")
        return v if isinstance(v, str) and v.strip() else None

    def walk(node, depth=0):
        if depth > 12 or len(out) >= 3:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "logo":
                    for item in (v if isinstance(v, list) else [v]):
                        u = val(item)
                        if u and u not in out and not u.startswith("#") and len(out) < 3:
                            out.append(u)
                else:
                    walk(v, depth + 1)
        elif isinstance(node, list):
            for v in node:
                walk(v, depth + 1)

    for t in texts or []:
        try:
            body = re.sub(r"^\s*<!--|-->\s*$", "", t or "").strip()
            walk(json.loads(body or "null"))
        except (ValueError, TypeError, RecursionError):
            continue
    return out


def css_logo_urls(style_texts, inline_urls=()) -> list[str]:
    """logo 元素的 CSS 背景圖：style 屬性（掃描時已收）＋ <style> 區塊裡選擇器含 logo 的規則。

    只看頁面裡的 <style>，不另外下載外部 .css（一家多幾個請求換來的命中率不值得，而且外部 CSS 常常幾百 KB）。
    """
    out = [u for u in inline_urls if u]
    for t in style_texts or []:
        for m in _CSS_LOGO_RULE.finditer(t[:200_000]):
            sel = m.group(1).rsplit("}", 1)[-1]
            if "footer" in sel.lower() or _NOT_OWN_LOGO.search(sel):
                continue
            for u in _CSS_URL.finditer(m.group(2)):
                if len(out) < 4:
                    out.append(u.group(2))
    seen, uniq = set(), []
    for u in out:
        u = u.strip()
        if u and not u.lower().startswith("data:") and u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq[:3]


def js_redirects(html: str) -> list[str]:
    """`location.href='…'`、`location.replace('…')` 這種入口頁轉址。只看前 100 KB、最多 2 個。"""
    out = []
    for m in _JS_REDIRECT.finditer(html[:100_000]):
        u = m.group(1) or m.group(2)
        if u and u not in out and not u.lower().startswith(("javascript:", "#", "mailto:")):
            out.append(u)
        if len(out) >= 2:
            break
    return out


def _svg_fix(frag: str) -> bytes:
    """inline <svg> 切出來單獨畫：補 xmlns（HTML 裡可以省略，獨立的 SVG 檔不行）；有用 xlink: 就補 xlink 的宣告。"""
    head_end = frag.find(">")
    head = frag[:head_end]
    add = ""
    if "xmlns=" not in head:
        add += ' xmlns="http://www.w3.org/2000/svg"'
    if "xlink:" in frag and "xmlns:xlink" not in head:
        add += ' xmlns:xlink="http://www.w3.org/1999/xlink"'
    if add:
        frag = frag[:4] + add + frag[4:]
    return frag.encode("utf-8")


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
    """解析首頁，回 {icons, manifest, og, imgs, logos, svgs, next, browserconfig}。每個候選是 {url, kind, px, svg}。

    - icons：`<link rel="icon"|"apple-touch-icon"|"mask-icon">` **全部**（第一版只取第一個能用的）。
      px 是宣告的 sizes；apple-touch-icon 沒寫 sizes 時照慣例當 180；SVG 寫 sizes="any" 當 512。
      第四版加 `msapplication-TileImage`／`square150x150logo`… 磚圖示（kind＝ms-tile，px 照名稱）。
    - manifest：`<link rel="manifest">` 的網址（圖示要另外下載 manifest 才知道）。
    - og：`<meta property="og:image">` 與宣告的寬高；**要不要用由 og_candidate() 判斷**。
    - imgs：頁首「自家 Logo」的 <img>，頁首裡的、自己名字就有 logo 的排前面，最多 2 個。
    - logos（第四版）：JSON-LD／itemprop 的 logo（kind＝schema-logo）、回首頁連結包著的第一張圖（home-img）、
      logo 元素的 CSS 背景圖（css-logo）。
    - svgs（第四版）：頁首 inline `<svg>` 的原文（kind＝inline-svg，候選帶 data 不帶網址）。
    - next（第四版）：入口頁要跟的下一頁，依序是 meta refresh、frame、JS 轉址、hreflang＝zh-TW、繁中版連結。
      要不要跟由 follow_links() 決定（首頁候選太弱才跟）。
    - browserconfig（第四版）：`msapplication-config` 指的 browserconfig.xml（磚圖示）。
    """
    p = _PageScan(html or "", base_url)
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
    for t in p.tiles:
        url = _abs(base, t["href"])
        if url and url not in seen:
            seen.add(url)
            icons.append({"url": url, "kind": "ms-tile", "px": t["px"], "svg": _is_svg_url(url)})
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
    logos = []
    for kind, hrefs in (("schema-logo", p.itemprop + jsonld_logos(p.jsonld_raw)),
                        ("home-img", p.home_imgs),
                        ("css-logo", css_logo_urls(p.style_raw, p.css_urls))):
        n = 0
        for href in hrefs:
            url = _abs(base, href)
            if url and url not in seen and n < 2:
                seen.add(url)
                n += 1
                logos.append({"url": url, "kind": kind, "px": 0, "svg": _is_svg_url(url)})
    svgs = [{"url": f"{base_url}#inline-svg-{i + 1}", "kind": "inline-svg", "px": 0, "svg": True,
             "data": _svg_fix(frag)} for i, frag in enumerate(p.svgs)]
    nxt, nseen = [], {base_url.rstrip("/")}
    for href in ([p.refresh] if p.refresh else []) + p.frames + js_redirects(html or "") + p.alternates + p.lang_links:
        url = _abs(base, href)
        if url and url.split("#")[0].rstrip("/") not in nseen:
            nseen.add(url.split("#")[0].rstrip("/"))
            nxt.append(url)
    return {"icons": icons, "manifest": _abs(base, p.manifest) if p.manifest else None,
            "og": og, "imgs": imgs, "logos": logos, "svgs": svgs, "next": nxt[:5],
            "browserconfig": _abs(base, p.browserconfig) if p.browserconfig else None}


def weak_scan(scan: dict) -> bool:
    """首頁候選「太弱」＝ 沒有 ≥48px 的圖示、沒有 SVG 圖示、沒有 manifest、也沒有任何「看起來是 Logo」的圖。

    這種首頁多半是入口頁（只有 meta refresh／frameset／語言選擇）—— 第三版的 none 裡最大的一群。
    只有這時才去開下一頁，正常的首頁不多花一個請求。
    """
    if scan.get("manifest") or scan.get("imgs") or scan.get("logos") or scan.get("svgs"):
        return False
    return not any(c.get("svg") or (c.get("px") or 0) >= 48 for c in scan.get("icons") or [])


def merge_scans(a: dict, b: dict) -> dict:
    """把下一頁的候選併進首頁的：清單相接（網址重複的去掉），manifest／og／browserconfig 首頁沒有才用下一頁的。"""
    out = dict(a)
    for k in ("icons", "imgs", "logos", "svgs"):
        seen = {c["url"] for c in a.get(k) or []}
        out[k] = list(a.get(k) or []) + [c for c in b.get(k) or [] if c["url"] not in seen]
    for k in ("manifest", "og", "browserconfig"):
        out[k] = a.get(k) or b.get(k)
    out["next"] = []
    return out


def parse_browserconfig(raw: bytes, url: str) -> list[dict]:
    """browserconfig.xml 的 <square150x150logo src=…>／<square310x310logo>／<TileImage> → 候選（大的先）。壞掉回空。"""
    try:
        text = raw.decode("utf-8-sig", errors="replace")
    except AttributeError:
        return []
    out = []
    for m in re.finditer(r"<\s*(square(\d+)x\d+logo|tileimage)\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]", text, re.I):
        u = _abs(url, m.group(3))
        if u and all(c["url"] != u for c in out):
            out.append({"url": u, "kind": "ms-tile", "px": int(m.group(2) or 144), "svg": _is_svg_url(u)})
    out.sort(key=lambda c: -c["px"])
    return out[:2]


def decode_html(body: bytes, ctype: str = "") -> str:
    """首頁 HTML → 文字。照 Content-Type 或 <meta charset> 宣告的編碼解；台灣老網站很多是 Big5（用 cp950 解，它是 Big5 的超集）。

    第三版一律 utf-8 解（標籤與屬性是 ASCII，找圖示夠用）；第四版要比對「頁面有沒有提到這家公司的名稱」，中文要解對。
    """
    body = body or b""
    m = re.search(rb"charset\s*=\s*['\"]?([A-Za-z0-9_-]+)", (ctype or "").encode("ascii", "ignore")) or \
        re.search(rb"<meta[^>]+charset\s*=\s*['\"]?([A-Za-z0-9_-]+)", body[:4096], re.I)
    enc = m.group(1).decode("ascii").lower() if m else "utf-8"
    if enc in ("big5", "big5-hkscs", "x-x-big5"):
        enc = "cp950"
    try:
        return body.decode(enc, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def mentions_company(html: str, names) -> bool:
    """頁面文字有沒有提到這家公司（簡稱或去掉「股份有限公司」的全名，至少 2 個字）。「臺」「台」視為同一字。"""
    text = re.sub(r"\s+", "", (html or "")[:500_000]).replace("臺", "台")
    for n in names or ():
        n = re.sub(r"\s+", "", str(n or "")).replace("臺", "台")
        n = re.sub(r"(股份有限公司|有限公司)$", "", n)
        if len(n) >= 2 and n in text:
            return True
    return False


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
    第四版：ms-tile（磚圖示）跟一般圖示一起依宣告尺寸排；schema-logo／inline-svg／home-img／css-logo 排在第 4 層。
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
    # 第四版：schema.org logo、inline SVG、回首頁連結的圖、CSS 背景圖 —— 跟頁首 logo 圖同一層（都是商標本體）
    groups[3].extend(c for c in scan.get("logos") or [] if c["kind"] == "schema-logo")
    groups[3].extend(scan.get("svgs") or [])
    groups[3].extend(c for c in scan.get("logos") or [] if c["kind"] != "schema-logo")
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
                    aspect: tuple[float, float] | None = None,
                    allow_lowres: bool = False) -> tuple[bytes, tuple[int, int]]:
    """任何 Pillow 讀得懂的圖（ICO／PNG／JPEG／GIF／WebP／BMP）或 SVG → 透明底 PNG（通常 64×64）。

    ICO 內含多種尺寸時 Pillow 預設開最大的那張。等比縮到 64 以內再置中貼到透明畫布，
    不裁切、不拉伸、不改色 —— 只縮放，這是「指稱性使用、不修改圖形」的技術面保證。
    非正方形（橫長字標）就上下補透明邊；長寬比超過 LOGO_MAX_ASPECT 的判太小（縮完只剩一條線）。
    photo_check：是照片就擋（True＝寬鬆、"strict"＝嚴格，見 is_photo）；aspect：限定寬／高範圍（沒寫 logo 的 og:image 用）。

    低解析（第三版）：原圖長邊 < LOGO_LOWRES_BELOW（48）的點陣圖**照原尺寸**存，只補透明邊成正方形
    （16×16 就存 16×16、24×25 存 25×25），不放大重採樣 —— 放大只會做出「看起來是 64px、其實是 16px」的假解析度。
    為什麼不是「置中貼到 64×64 畫布」：前端 `.slogo img` 用 width/height:100%＋object-fit:contain，
    整張 PNG 會被縮放到 20～32px 的框裡；16px 圖示貼在 64 畫布中間，顯示出來只剩框的四分之一（約 5px），
    比字母頭像還難認。照原尺寸存，放大交給瀏覽器顯示時做（跟分頁上的 favicon 一樣），湖裡存的就是原圖。
    allow_lowres：長邊 16～31px 的圖要不要收（只有官網自己的圖可以；Google s2 等第三方仍要 ≥ LOGO_MIN_PX）。
    """
    Image = _pil()
    head = data[:1024].lstrip(b"\xef\xbb\xbf \t\r\n").lower()     # 有的 SVG 前面帶 UTF-8 BOM
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
    if not vector and max(w, h) < (config.LOGO_LOWRES_MIN_PX if allow_lowres else config.LOGO_MIN_PX):
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
    if not vector and max(w, h) < config.LOGO_LOWRES_BELOW:
        px, resized = max(w, h), rgba          # 低解析：原尺寸，只補邊（見上方說明）
        nw, nh = w, h
    else:
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

    第四版（2026-09-28，DECISIONS #276）照 RFC 9309 §2.3.1 的四種狀態判：
    - 200：照 Disallow／Allow 規則判（一律以一般爬蟲 * 的規則）。**寫了 Disallow 的照舊尊重。**
    - 4xx（含 401、403、404、410）＝「不可取得（unavailable）」：RFC 9309 §2.3.1.3 明定爬蟲**可以存取任何資源**。
      Google 的 robots.txt 規格也把 4xx（429 除外）當「沒有 robots.txt」。
      第三版以前照 Python robotparser 的慣例把 401／403 當全站禁止 —— 比標準還嚴，89 家 robots 裡至少 22 家是這樣被擋掉的。
      ⚠ robots.txt 回 403 常常是 WAF 擋雲端 IP，那種站首頁多半也是 403；首頁 403 就判「找不到」，
      一樣**不換網址重試、不走任何繞道**（_fetch_logo 的「403／5xx 不換網址」規則照舊）。
    - 429（請求太頻繁）：對方在叫我們慢下來。這輪不抓（`.defer`），記成 error，下一次照規則再試。
      RFC 把它歸在 4xx，但 Google 規格特別把 429 排除在「沒有 robots.txt」之外，我們採較保守的那一邊。
    - 5xx＝「無法連線（unreachable）」：RFC 9309 §2.3.1.4 要求**視為全站禁止**（第三版以前反而當成沒有限制，比標準鬆）。
      這是暫時狀態，所以不記 robots（永久不准），而是這輪不抓、記成 error，下一次照規則再試。
    - 連不上（DNS 失敗、逾時）：同 5xx，這輪不抓。
    首頁與每一個圖示網址都要過這一關（有的站只擋 /images/ 之類的目錄）。
    """
    def allow_all(url):
        return True
    allow_all.why = ""
    res = _get(urljoin(root, "/robots.txt"), timeout=6, max_bytes=200_000)
    if res is None:
        def unreachable(url):
            return True
        unreachable.why = ""
        # 連 robots.txt 都連不上（DNS 失敗、逾時）：首頁幾乎一定也連不上。標起來讓 _open_home 直接跳過，
        # 第二版多了 www／非 www 備援，死掉的網域每多試一個主機就要多等一次逾時，這樣每家可省 10 秒以上。
        unreachable.unreachable = True
        return unreachable
    status, body, _ctype, _final = res
    if status == 429 or status >= 500:
        def defer(url):
            return False
        defer.why = ""
        defer.defer = (f"robots.txt 回 HTTP {status}（" +
                       ("請求太頻繁，這輪先不抓" if status == 429 else
                        "RFC 9309 §2.3.1.4：伺服器錯誤視為暫時全站禁止，這輪不抓") + f"）{root}")
        return defer
    if 400 <= status < 500:
        def unavailable(url):
            return True
        unavailable.why = ""
        unavailable.unavailable = status      # RFC 9309 §2.3.1.3：不可取得 ＝ 可以存取任何資源
        return unavailable
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
              "ms-tile": 1, "header-img": 2, "schema-logo": 2, "inline-svg": 2, "home-img": 2,
              "css-logo": 3, "og-image": 3, "mask-icon": 4}


# 可以收「低解析」（16～31px）的候選：官網自己的圖。第三方快取（google_s2）不收 —— 它對找不到的網站
# 會回 16px 預設地球，小圖從第三方來的可信度太低；而且它回的 16px 本來就是官網那張的複本，官網那條路已經試過了。
# 要放寬見 config.LOGO_LOWRES_ALLOW_S2（預設關）。
_LOWRES_KINDS = {"apple-touch-icon", "manifest", "icon", "conventional", "header-img", "og-image", "mask-icon",
                 "ms-tile", "schema-logo", "inline-svg", "home-img", "css-logo"}
# 要做照片判定的候選（寬鬆模式）：不是「宣告成圖示」的圖，可能抓到橫幅照片
_PHOTO_KINDS = {"og-image", "header-img", "schema-logo", "home-img", "css-logo"}


def _try_image(url: str, kind: str = "icon", logo_named: bool = True,
               data: bytes | None = None) -> tuple[bytes, tuple[int, int]] | LogoReject:
    """下載一個候選並正規化。data 有值（inline SVG）就不下載，直接畫頁面裡切出來的那段。"""
    if data is not None:
        body = data
    else:
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
                               photo_check="strict" if bare_og else kind in _PHOTO_KINDS,
                               aspect=OG_ASPECT if bare_og else None,
                               allow_lowres=kind in _LOWRES_KINDS
                               or (kind == "google_s2" and config.LOGO_LOWRES_ALLOW_S2))
    except LogoReject as rej:
        rej.detail = f"{rej.detail} {url}".strip()
        return rej


# 失敗原因的「嚴重度」：多個候選都失敗時，回報最有資訊量的那一個
_REASON_RANK = {"too_small": 6, "too_wide": 6, "generic": 5, "blank": 5, "not_logo": 4, "bad_image": 3,
                "svg_unsupported": 3, "none": 2, "error": 1}


def fetch_logo(website, host: str | None = None, reject: set | frozenset | None = None,
               names=None) -> dict:
    """抓一家公司的 Logo。回 {status, src, png, orig, detail, domain[, site][, lowres][, via]}；status＝ok 時 png 有值。

    site：首頁轉址到同公司的另一個網域時，記下實際取圖的主機（例如 www.aoet.com.tw → www.aoet.com）。
    lowres：官網找不到 ≥48px 的圖、收下的是 16～47px 的小圖（照原尺寸存，見 normalize_image）。
    reject：已知預設圖的雜湊（第三版）。候選正規化後的雜湊在裡面 ＝ 那是預設圖，**跳過它繼續往下找**
    （頁首圖、manifest、s2 …），不是直接判失敗 —— 第二版是整輪抓完才發現、刪檔判 generic，那家就沒圖了。
    names：這家公司的簡稱／全名（第四版）。申報的官網轉址到別的網域（集團共用官網）時，
    那一頁要提到其中一個名字才跟過去取圖（via＝group）；沒給 names 就照第三版一律不跟。
    絕不拋例外：任何意外都變成 status=error，一家壞掉不能拖垮一整輪。
    """
    host = host or extract_domain(website)
    if not host:
        return {"status": "no_website", "domain": None}
    try:
        return _fetch_logo(website, host, frozenset(reject or ()), tuple(n for n in (names or ()) if n))
    except LogoReject as rej:
        return {"status": "error", "domain": host, "detail": f"{rej.reason} {rej.detail}"[:200]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "domain": host, "detail": str(exc)[:200]}


def _open_home(url: str, host: str, rules) -> tuple:
    """打開首頁，**自己一跳一跳地跟轉址**：每一跳先確認是同一家公司的網域、再過那個網域的 robots.txt。

    回 ("page", 狀態碼, 內容, 最終網址, Content-Type) / ("robots", 網域根, 原因) / ("foreign", 轉到哪) / ("down", 說明)。
    """
    cur = url
    for _hop in range(6):
        origin = _origin(cur)
        allowed = rules(origin)
        if getattr(allowed, "unreachable", False):
            return ("down", f"連不上 {origin}（robots.txt 就連不上，首頁不再試）")
        if getattr(allowed, "defer", None):
            return ("down", allowed.defer)      # robots.txt 回 429／5xx：這輪不抓（不是永久的 robots）
        if not allowed(cur):
            return ("robots", origin, getattr(allowed, "why", "") or "robots.txt 不允許")
        res = _get(cur, timeout=10, max_bytes=2_000_000, allow_redirects=False)
        if res is None:
            return ("down", f"首頁連線失敗 {cur}")
        status, body, ctype, nxt = res
        if 300 <= status < 400:
            if not nxt or nxt == cur:
                return ("down", f"首頁 HTTP {status} 沒有可跟的 Location {cur}")
            nh = urlparse(nxt).hostname
            if not same_company(host, nh):
                return ("foreign", nxt)
            cur = nxt
            continue
        return ("page", status, body, cur, ctype or "")
    return ("down", f"首頁轉址超過 5 次 {url}")


FOLLOW_MAX_PAGES = 2     # 入口頁最多再開幾頁（第四版）


def follow_links(scan: dict, host: str, rules, names=(), own_hosts: set | None = None) -> tuple[dict, list]:
    """首頁候選太弱（weak_scan）時，照 scan["next"] 的順序最多再開 FOLLOW_MAX_PAGES 頁，把候選併進來。

    - 同一家公司的網域才跟；別家網域只有「那一頁提到這家公司名稱」才收（集團共用官網），否則丟掉。
    - 每一頁都走 _open_home（逐跳過 robots、只跟同公司轉址）；robots 不准的那一頁就不開，不影響已經拿到的候選。
    - 收到候選夠強（weak_scan 為假）就停，不多開。
    回 (併好的 scan, 這一步記下的失敗說明)。own_hosts 會加進真的開過的主機（候選的 robots 檢查要用）。
    """
    notes: list = []
    opened = 0
    for url in list(scan.get("next") or []):
        if opened >= FOLLOW_MAX_PAGES or not weak_scan(scan):
            break
        uh = urlparse(url).hostname or ""
        same = same_company(host, uh) or any(same_company(h, uh) for h in (own_hosts or ()))
        if not same and not names:
            notes.append(f"下一頁在別家網域 {url}，不跟")
            continue
        got = _open_home(url, uh if not same else host, rules)
        if got[0] != "page" or got[1] != 200 or not got[2]:
            notes.append(f"下一頁打不開（{got[0]}）{url}")
            continue
        text = decode_html(got[2], got[4])
        if not same and not mentions_company(text, names):
            notes.append(f"下一頁在別家網域、而且沒提到公司名稱 {url}，不跟")
            continue
        opened += 1
        if own_hosts is not None:
            own_hosts.add(urlparse(got[3]).hostname or uh)
        scan = merge_scans(scan, scan_page(text, got[3]))
    return scan, notes


def _fetch_logo(website, host: str, reject: frozenset = frozenset(), names: tuple = ()) -> dict:
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

    # ① 官網首頁（申報的那一頁 → 根目錄；404 或連不上就換 scheme、換 www／非 www；轉址只跟同一家公司的網域）
    page, reachable, deferred, foreign = None, None, False, None
    for home in homepage_candidates(website, host):
        got = _open_home(home, host, rules)
        if got[0] == "robots":
            return {"status": "robots", "domain": host,
                    "detail": f"{got[1]} {got[2]} —— 尊重它，也不走 Google 備援"[:200]}
        if got[0] == "down":
            keep(LogoReject("error", got[1]))
            if got[1].startswith("robots.txt 回 HTTP"):
                deferred = True     # 429／5xx：對方暫時不准，這輪連 Google 備援都不問（等同 robots 不准）
                break
            continue
        if got[0] == "foreign":
            foreign = foreign or got[1]
            keep(LogoReject("none", f"首頁轉到別家網域 {got[1]}，不跟"))
            continue
        _, status, body, final, ctype = got
        reachable = reachable or final
        if status == 200 and body:
            page = (body, final, ctype)
            break
        keep(LogoReject("none", f"首頁 HTTP {status} {final}"))
        if status in (401, 403) and getattr(rules(_origin(final)), "unavailable", None) in (401, 403):
            # 第四版：robots.txt 與首頁都回 401／403 ＝ 對方在擋我們（多半是擋雲端 IP 的防火牆）。
            # RFC 9309 說 robots.txt 4xx 可以抓，但首頁也不給，就是不給 —— 不請 Google 代抓（同 #267 不用 DuckDuckGo 的理由）
            return {"status": "none", "domain": host,
                    "detail": f"robots.txt 與首頁都回 HTTP {status}（對方擋雲端存取），圖檔與 Google 備援都不抓 {final}"[:200]}
        if status not in (404, 410):
            break          # 403／5xx 換網址也一樣，別浪費對方的資源

    extra: dict = {}
    # ①-b 同集團母公司官網（第四版）：申報的官網整個轉到別的網域，那一頁提到這家公司才跟
    if page is None and reachable is None and foreign and names and not deferred:
        fh = urlparse(foreign).hostname or ""
        got = _open_home(foreign, fh, rules)
        if got[0] == "robots":
            return {"status": "robots", "domain": host, "site": fh,
                    "detail": f"官網轉到 {fh}，{got[1]} {got[2]} —— 尊重它，也不走 Google 備援"[:200]}
        if got[0] == "page" and got[1] == 200 and got[2]:
            if mentions_company(decode_html(got[2], got[4]), names):
                page, reachable = (got[2], got[3], got[4]), got[3]
                extra["via"] = "group"
            else:
                keep(LogoReject("none", f"首頁轉到別家網域 {foreign}，那一頁沒提到公司名稱，不跟"))

    site_ok = reachable is not None
    cands: list[dict] = []
    final_host = None
    if site_ok:
        base_url = page[1] if page else reachable
        final_host = urlparse(base_url).hostname
        origin = _origin(base_url)
        own_hosts = {host, final_host}
        scan = (scan_page(decode_html(page[0], page[2]), page[1]) if page
                else {"icons": [], "manifest": None, "og": None, "imgs": [], "logos": [], "svgs": [], "next": []})
        # 第四版：入口頁（meta refresh／frameset／語言選擇）→ 最多再開兩頁
        if page and weak_scan(scan) and scan.get("next"):
            scan, notes = follow_links(scan, host, rules, names, own_hosts)
            for n in notes:
                keep(LogoReject("none", n))

        def allowed(url: str) -> bool:
            """同一家公司（或這輪真的開過的主機）的網址要過它自己網域的 robots；CDN 上的圖檔照第一版的做法直接抓。"""
            uh = urlparse(url).hostname or ""
            if not any(same_company(h, uh) or h == uh for h in own_hosts if h):
                return True
            return rules(_origin(url))(url)

        man_icons: list[dict] = []
        mu = scan.get("manifest")
        if mu and allowed(mu):
            res = _get(mu, timeout=6, max_bytes=200_000)
            if res and res[0] == 200 and res[1]:
                man_icons = parse_manifest_icons(res[1], res[3] or mu)
        bc = scan.get("browserconfig")
        if bc and allowed(bc):
            res = _get(bc, timeout=6, max_bytes=100_000)
            if res and res[0] == 200 and res[1]:
                man_icons = man_icons + parse_browserconfig(res[1], res[3] or bc)
        cands = plan_candidates(scan, origin, man_icons)
        # 同網域的圖檔要過 robots（有的站只擋 /images/）；inline SVG 是首頁本身的內容，不必再問
        cands = [c for c in cands if c.get("data") is not None or allowed(c["url"])]

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
        got = _try_image(c["url"], c["kind"], c.get("logo_named", True), c.get("data"))
        if isinstance(got, LogoReject):
            keep(got)
            continue
        png, orig = got
        if sha1(png) in reject:
            # 已知的預設圖（例：同一張 favicon.ico 出現在南亞科、中租、東和鋼鐵等 14 家不相干公司）：
            # 不收，也**不提早停**，繼續試頁首圖、og:image、其他圖示，最後還有 s2
            keep(LogoReject("generic", f"預設圖（跟其他網域同一張）{c['url']}"))
            continue
        cand = {**c, "png": png, "orig": orig, "eff": effective_px(*orig)}
        if best is None or _score(cand) > _score(best):
            best = cand
        if cand["eff"] >= config.LOGO_PX and _KIND_RANK.get(c["kind"], 9) <= 1:
            break          # 已經有 ≥64px 的正方形官方圖示，不必再下載其他候選

    # ② Google 備援：官網沒有，或官網最好的也只有 32～47px 時，問 Google 有沒有更大的。
    # 集團官網那條（via＝group）不問 —— s2 問的是申報網域，拿到的會是停放頁或舊站的圖示，跟集團那頁對不上
    if not deferred and "via" not in extra and (best is None or best["eff"] < 48):
        s2 = config.LOGO_GOOGLE_S2.format(domain=host)
        got = _try_image(s2, "google_s2")
        if isinstance(got, LogoReject):
            keep(got)
        elif sha1(got[0]) in reject:
            keep(LogoReject("generic", f"預設圖（跟其他網域同一張）{s2}"))
        else:
            png, orig = got
            cand = {"url": s2, "kind": "google_s2", "png": png, "orig": orig, "eff": effective_px(*orig)}
            if best is None or _score(cand) > _score(best):
                best = cand

    if final_host and final_host != host:
        extra["site"] = final_host      # 連 www ↔ 非 www 也記：下一個人查「為什麼圖是從這裡來的」才對得上
    if best is not None:
        src = "google_s2" if best["kind"] == "google_s2" else f"site:{best['kind']}"
        if max(best["orig"]) < config.LOGO_LOWRES_BELOW and not best.get("svg"):
            extra["lowres"] = True      # 找不到 ≥48px 的，收的是小圖（照原尺寸存）；30 天後再找找看有沒有更大的
        return {"status": "ok", "domain": host, "src": src, "url": best["url"],
                "png": best["png"], "orig": list(best["orig"]), **extra}
    extra.pop("via", None)
    reason = worst.reason if worst else "none"
    if reason == "too_wide":
        reason = "too_small"
    status = reason if reason in ("too_small", "blank", "error", "generic") else "none"
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
    第四版：有 `site`（實際取圖的主機）就用它 —— 三家子公司各自申報的網域都轉到同一個集團官網、拿到同一張集團 Logo，
    那是同一個網站，不是「三個不相干的網域同一張預設圖」。
    Commons 來源（src＝wikimedia）不參與：金控與子公司共用同一個 Commons 檔是正常的，那張圖是 Wikidata 標註過的標誌、不是架站商預設圖。
    """
    n = config.LOGO_GENERIC_DOMAINS if min_domains is None else min_domains
    by_hash: dict[str, set[str]] = {}
    for rec in items.values():
        if rec.get("src") in ("manual", "wikimedia"):
            continue          # 人工指定的是人挑過的圖、Commons 的是 Wikidata 標註過的標誌，不參與「預設圖」判定
        if rec.get("status") in ("ok", "generic") and rec.get("sha1"):
            by_hash.setdefault(rec["sha1"], set()).add(base_domain(rec.get("site") or rec.get("domain")))
    return {h for h, doms in by_hash.items() if len(doms) >= n}


def known_generic(idx: dict) -> set[str]:
    """已知預設圖的雜湊：這一輪從索引算出來的 ∪ 以前記下來的（`idx["generic_sha1"]`）。

    第三版為什麼要另外記：判 generic 的那幾家重抓之後換成真正的 Logo，紀錄裡的舊雜湊就沒了；
    只靠 generic_hashes() 現算，那張預設圖會「失憶」，下一家架在同一個架站商的公司又會把它收進來。
    """
    return generic_hashes(idx.get("items", {})) | {str(h) for h in idx.get("generic_sha1") or []}


def usable_codes(idx: dict) -> dict[str, str]:
    """{代號: 檔名}：狀態 ok、檔案真的在、而且不是預設圖。build_payload 只輸出這些。"""
    items = idx.get("items", {})
    bad = known_generic(idx)
    out = {}
    for code, rec in items.items():
        if rec.get("status") != "ok":
            continue
        if rec.get("sha1") in bad and rec.get("src") != "manual":   # 人工指定的一律信任
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


# 取圖策略升級時要「立刻重試」的失敗狀態：這幾種是「方法不夠好」造成的。
# 第三版加 generic：第二版拒收預設圖後就直接判失敗，沒有往下找頁首圖、s2 —— 那是方法的問題，不是圖的問題。
# 第四版（DECISIONS #276）再加三種：
# - robots：robots.txt 回 4xx 的改照 RFC 9309 視為沒有規則；而且 55 家是第一版判的、當時沒記原因，
#   分不出是 403 還是 Disallow，只能重讀一次 robots.txt 才知道。讀 robots.txt 本身永遠是允許的；
#   真的寫了 Disallow 的，重讀之後照樣判 robots、照樣不碰官網 —— 但會試 Wikimedia Commons（不是爬官網，見 logo_wikimedia.py）。
# - blank、error：官網那條路沒變，但多了 Wikimedia 這個新來源，值得再試一次。
RETRY_ON_UPGRADE = ("too_small", "none", "generic", "robots", "blank", "error")


def retry_on_upgrade(rec: dict) -> bool:
    """這筆是用比 config.LOGO_STRATEGY 舊的策略判成「太小／找不到／預設圖」的 → 下一輪立刻重試。

    沒記 strategy 的舊紀錄一律當第 1 版。重試完會記上新版號，之後回到一般的 30 天規則，
    不會每輪都重抓。抓到的好圖（ok）不在這裡 —— 策略升級不去動已經有的圖，只補沒有的；
    唯一例外是「低解析」的 ok（第三版起才有）：它本來就是「先頂著用」，之後策略再升級時也一起重試。
    重試失敗時 run() 會保留舊圖，不會把低解析的圖弄丟。
    """
    lowres_ok = rec.get("status") == "ok" and rec.get("lowres")
    if not lowres_ok and rec.get("status") not in RETRY_ON_UPGRADE:
        return False
    try:
        ver = int(rec.get("strategy") or 1)
    except (TypeError, ValueError):
        ver = 1
    return ver < config.LOGO_STRATEGY


def _days(rec: dict) -> int:
    """好圖 90 天重抓；沒抓到的、以及「低解析」的 ok 30 天再找一次（官網改版常常就有大圖了）。"""
    if rec.get("status") == "ok" and not rec.get("lowres"):
        return config.LOGO_REFRESH_DAYS
    return config.LOGO_RETRY_DAYS


def _due(rec: dict, today: date) -> bool:
    try:
        last = date.fromisoformat(str(rec.get("fetched"))[:10])
    except ValueError:
        return True
    return (today - last).days >= _days(rec)


def next_due(rec: dict) -> str | None:
    try:
        last = date.fromisoformat(str(rec.get("fetched"))[:10])
    except ValueError:
        return None
    return (last + timedelta(days=_days(rec))).isoformat()


def select_todo(sites: pd.DataFrame, idx: dict, today: date, limit: int,
                priority: list[str] | None = None) -> list[dict]:
    """這一輪要抓哪些：策略升級要重試的 → 沒抓過的 → 網域換了的 → 到期重抓的（最舊的先）。

    第三版：策略升級要重試的包含「太小／找不到／預設圖」三種（見 RETRY_ON_UPGRADE）。

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
        elif rec.get("src") == "manual":
            continue          # 人工指定的 Logo（第四版）：優先於自動抓的，永遠不重抓、不覆寫
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
        priority: list[str] | None = None, wikimedia=None) -> dict:
    """抓一輪 Logo。回摘要 dict，並寫進 data/_state/logo_progress.json。絕不拋例外。

    wikimedia：第二來源（第四版）。None ＝ 走真的官網抓取（fetcher 沒換）時才用真的 Wikimedia，
    測試換了 fetcher 就不碰網路；要測 Wikimedia 那段就傳一個 (rows, reject, deadline) → {代號: 結果} 的函式。
    False ＝ 這輪不用。
    """
    summary: dict = {"enabled": config.LOGOS_ENABLED, "at": datetime.now(timezone.utc).isoformat()}
    if not config.LOGOS_ENABLED:
        log.info("LOGOS_ENABLED 關閉，Logo 步驟不抓")
        summary.update(done=True, skipped="disabled")
        _write_state(summary)
        return summary
    try:
        return _run(summary, limit, today, time_budget, fetcher, priority, wikimedia)
    except Exception as exc:  # noqa: BLE001
        log.warning("Logo 步驟失敗（不影響其他步驟）：%s", exc)
        summary.update(done=False, error=str(exc)[:200])
        _write_state(summary)
        return summary


def _run(summary, limit, today, time_budget, fetcher, priority, wikimedia=None) -> dict:
    today = today or _today()
    limit = config.LOGOS_PER_RUN if limit is None else limit
    budget = config.LOGO_TIME_BUDGET_SEC if time_budget is None else time_budget
    real = fetcher is None or fetcher is fetch_logo
    fetcher = fetcher or fetch_logo
    if wikimedia is None:
        wikimedia = _wikimedia_real if real and config.LOGO_WIKIMEDIA_ENABLED else None
    sites = websites()
    idx = read_index()
    items = idx.setdefault("items", {})
    # 人工指定的 Logo 最先套用（第四版）：優先於任何自動來源，之後的抓取一律不覆寫
    summary["manual"] = apply_manual(items, today)
    # 開抓前先記下已知的預設圖：判 generic 的那幾家這輪重抓成功後，舊紀錄的雜湊就沒了，結尾要併回去
    reject = frozenset(known_generic(idx))
    if real:
        _pil()   # 沒有 Pillow 就整輪不跑（直接進 except 記進狀態檔），不要抓了幾百張卻存不了
    todo = select_todo(sites, idx, today, limit, priority)
    logo_dir().mkdir(parents=True, exist_ok=True)
    log.info("Logo：有網址 %d 家、已有紀錄 %d 家，這輪抓 %d 家（上限 %d、%d 秒）",
             len(sites), len(items), len(todo), limit, budget)

    t0 = time.time()
    deadline = t0 + budget

    # 公司名稱（第四版）：集團官網轉址時，要確認那一頁提到這家公司才跟。同網域共用結果，所以按網域收名字
    cnames = company_names()
    names_by_host: dict[str, list] = {}
    for r in todo:
        names_by_host.setdefault(r["domain"], []).extend(cnames.get(r["code"], ()))

    def bound(rej):
        # 已知的預設圖交給每一家：抓到它就跳過、繼續往下找（第三版），不是抓完才刪檔判失敗
        if not real:
            return fetcher
        return lambda website, host: fetch_logo(website, host, reject=rej, names=names_by_host.get(host))

    results, deadline_hit = _fetch_rows(todo, bound(reject), deadline)
    if wikimedia:
        summary["wikimedia"] = _wikimedia_pass(results, sites, reject, deadline, wikimedia)

    counts: dict[str, int] = {}
    failures: list[dict] = []
    stamp = today.isoformat()
    for code, res in results.items():
        _record(items, code, res, stamp, counts, failures)

    # 預設圖：同一張圖出現在太多網域 → 刪檔、標 generic；雜湊記進索引，之後抓到一律跳過（見 known_generic）
    n_generic, bad, fresh_generic = 0, set(reject), []
    for _pass in range(2):
        bad |= known_generic(idx)
        fresh_generic = []
        for code, rec in items.items():
            if rec.get("status") == "ok" and rec.get("sha1") in bad and rec.get("src") != "manual":
                rec["status"] = "generic"
                (logo_dir() / f"{code}.png").unlink(missing_ok=True)
                n_generic += 1
                if code in results:
                    fresh_generic.append(code)
        # 第二遍（第三版）：這輪才被判成預設圖的，用更新過的預設圖清單**當場再抓一次**，讓它往下找頁首圖、s2。
        # 會發生在兩種情況：這輪才第一次湊滿 3 個網域的新預設圖；或舊紀錄的雜湊是舊版正規化算的
        # （例：32px 預設圖第二版放大到 64 存，第三版照原尺寸存，雜湊不同，開抓前的清單認不出來）。
        # 只做一次、只在時間還夠時做；沒做到的留給下一輪（狀態 generic、版號是新的 → 30 天後）。
        if _pass or not real or not fresh_generic or time.time() >= deadline:
            break
        rows = [{"code": c, "website": _site_of(sites, c), "domain": items[c].get("domain")}
                for c in fresh_generic]
        rows = [r for r in rows if r["website"] is not None]
        log.info("Logo：%d 家這輪才判成預設圖，用新的預設圖清單再抓一次", len(rows))
        again, hit2 = _fetch_rows(rows, bound(frozenset(bad)), deadline)
        deadline_hit = deadline_hit or hit2
        for code, res in again.items():
            counts["ok"] = counts.get("ok", 0) - (1 if results.get(code, {}).get("status") == "ok" else 0)
            _record(items, code, res, stamp, counts, failures)
            results[code] = res
            n_generic -= 1
    idx["generic_sha1"] = sorted(bad)
    counts = {k: v for k, v in counts.items() if v > 0}
    if n_generic:
        log.info("Logo：%d 家的圖跟其他網域完全一樣（預設圖），已刪檔改標 generic", n_generic)

    write_index(idx)
    write_attribution(items)
    left = select_todo(sites, idx, today, 10 ** 9, priority)
    dues = [d for d in (next_due(r) for r in items.values() if r.get("status") != "removed") if d]
    summary.update(
        done=not left, pending=len(left), attempted=len(results),
        counts=counts, generic=n_generic, sites=len(sites),
        have=sum(1 for r in items.values() if r.get("status") == "ok"),
        next_due=min(dues) if dues else None,
        seconds=round(time.time() - t0, 1), deadline_hit=deadline_hit,
        strategy=config.LOGO_STRATEGY, svg=svg_supported(),   # svg=false ＝ 這輪沒有 libcairo，SVG 候選全被跳過
        failures=failures[:200],
    )
    _write_state(summary)
    log.info("Logo：這輪 %s，現在有圖 %d 家，還有 %d 家待抓（下一次到期 %s）",
             counts, summary["have"], len(left), summary["next_due"])
    return summary


# ------------------------------------------------------------------ 第二來源：Wikidata／Wikimedia Commons（第四版）

def _wikimedia_real(rows, reject, deadline):
    from . import logo_wikimedia
    return logo_wikimedia.fetch_many(rows, reject, deadline)


def company_names() -> dict[str, tuple]:
    """{代號: (簡稱, 全名)}（第四版）：比對「集團官網那一頁有沒有提到這家公司」用。讀不到回空（那就一律不跟別家網域）。

    上櫃公司在 company_info 只有簡稱（沒有全名），簡稱至少 2 個字才用（mentions_company 也會再擋一次）。
    """
    try:
        info = store.read("company_info")
    except Exception:  # noqa: BLE001
        return {}
    if info.empty or "code" not in info.columns:
        return {}
    x = info.drop_duplicates("code", keep="last")
    out = {}
    for r in x.itertuples(index=False):
        code = clean_code(getattr(r, "code", None))
        names = tuple(str(v).strip() for v in (getattr(r, "name", None), getattr(r, "full_name", None))
                      if isinstance(v, str) and len(str(v).strip()) >= 2)
        if code and names:
            out[code] = names
    return out


def _full_names() -> dict[str, str]:
    """{代號: 公司全名}：Wikidata 用名稱比對時要（只有上市公司有全名）。讀不到回空，只剩代號比對。"""
    try:
        info = store.read("company_info")
    except Exception:  # noqa: BLE001
        return {}
    if info.empty or "full_name" not in info.columns:
        return {}
    x = info.dropna(subset=["full_name"]).drop_duplicates("code", keep="last")
    return {clean_code(c): str(n) for c, n in zip(x["code"], x["full_name"]) if clean_code(c) and str(n).strip()}


def _wikimedia_pass(results: dict, sites: pd.DataFrame, reject, deadline: float, wikimedia) -> dict:
    """官網那條路沒拿到圖（或只拿到低解析小圖）的，問 Wikimedia Commons 有沒有自由授權的 Logo。

    - 官網失敗（none／too_small／robots／blank／generic／error）→ Commons 有就用 Commons 的。
      **robots 也問**：Commons 是公開授權的圖庫，不是去爬那家公司的官網（DECISIONS #276）。Google s2 仍然不問。
    - 官網只有低解析（16～47px）→ Commons 的有效尺寸比較大才換。
    - 官網拿到正常大小的圖 → 不問（官網自己的圖最準、最新）。
    換掉時把官網那邊的失敗原因記在 `site_fail`，下一個人查「為什麼這家的圖是從 Commons 來的」對得上。
    """
    need = [c for c, r in results.items()
            if r.get("status") not in ("ok", "no_website") or r.get("lowres")]
    stat = {"asked": len(need), "ok": 0, "replaced_lowres": 0}
    if not need or time.time() >= deadline:
        return stat
    names = _full_names()
    rows = [{"code": c, "domain": results[c].get("domain"), "full_name": names.get(c)} for c in sorted(need)]
    try:
        got = wikimedia(rows, reject, deadline) or {}
    except Exception as exc:  # noqa: BLE001
        log.warning("Wikimedia 來源失敗（不影響官網那條路）：%s", exc)
        return stat
    stat["matched"] = len(got)
    for code, w in got.items():
        old = results.get(code)
        if old is None or w.get("status") != "ok":
            continue
        if old.get("status") == "ok":            # 官網只有低解析：Commons 的比較大才換
            if effective_px(*w["orig"]) <= effective_px(*old["orig"]):
                continue
            stat["replaced_lowres"] += 1
            fail = f"官網只有低解析 {old.get('orig')} {old.get('url', '')}".strip()
        else:
            fail = f"{old.get('status')} {old.get('detail', '')}".strip()
        new = {**w, "domain": old.get("domain") or w.get("domain"), "site_fail": fail[:200]}
        if old.get("site"):
            new["site"] = old["site"]
        results[code] = new
        stat["ok"] += 1
    return stat


def write_attribution(items: dict) -> None:
    """data/logos/ATTRIBUTION.md：Commons 來源的 Logo 逐張列出檔名、作者、授權、出處（CC BY／BY-SA 的署名義務）。

    repo 是 public，圖檔跟著 repo 散布，署名清單就放在圖檔旁邊。內容沒變就不重寫（沒有時間戳，版本庫不會多一個版本）。
    """
    rows = []
    for code, rec in sorted(items.items()):
        a = rec.get("attribution")
        if rec.get("status") != "ok" or rec.get("src") != "wikimedia" or not a:
            continue
        lic = a.get("license", "") + (f" <{a['license_url']}>" if a.get("license_url") else "")
        rows.append(f"| {code} | [{a.get('file', '')}]({a.get('page', '')}) | {a.get('artist') or '—'} | {lic} |")
    f = logo_dir() / "ATTRIBUTION.md"
    if not rows:
        if f.exists():
            f.unlink()
        return
    text = ("# 公司 Logo 出處（來自 Wikimedia Commons 的圖）\n\n"
            "以下 Logo 取自 Wikimedia Commons，只收公有領域、CC0、CC BY、CC BY-SA 授權的檔案；"
            "本站僅做等比縮放（CC BY-SA 的改作依同一授權釋出）。著作權授權不代表商標授權：各 Logo 之商標權屬各該公司所有，"
            "本站僅用於識別，不代表任何合作或背書關係。本檔由 `pipeline/sources/logos.py` 自動產生，請勿手改。\n\n"
            "| 代號 | Commons 檔案 | 作者 | 授權 |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
    if not f.exists() or f.read_text(encoding="utf-8") != text:
        f.write_text(text, encoding="utf-8")


# ------------------------------------------------------------------ 人工指定的 Logo（第四版）

def manual_dir() -> Path:
    return logo_dir() / config.LOGO_MANUAL_SUBDIR


def read_manual_meta() -> dict:
    """manual.json：{代號: {source_url, date, note}}。鍵不是代號的（例如「_說明」）略過；壞掉回空並記 log。"""
    p = manual_dir() / config.LOGO_MANUAL_META
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError) as exc:
        log.warning("人工 Logo 的 manual.json 讀不進來（%s）；圖照樣套用，但沒有來源紀錄", exc)
        return {}
    if isinstance(d, dict) and isinstance(d.get("items"), dict):
        d = d["items"]
    return {clean_code(k): v for k, v in (d.items() if isinstance(d, dict) else [])
            if clean_code(k) and isinstance(v, dict)}


def manual_files() -> dict[str, Path]:
    """{代號: 檔案}：data/logos/manual/<代號>.png（也收 jpg／webp／gif／svg，同代號多個檔時 png 優先）。"""
    d = manual_dir()
    out: dict[str, Path] = {}
    if not d.is_dir():
        return out
    by_ext: dict[str, list[Path]] = {}
    for f in sorted(d.iterdir()):
        if f.is_file():
            by_ext.setdefault(f.suffix.lower(), []).append(f)
    for ext in config.LOGO_MANUAL_EXTS:          # 依偏好順序：先看到的留下
        for f in by_ext.get(ext, []):
            code = clean_code(f.stem)
            if code and code not in out:
                out[code] = f
    return out


def apply_manual(items: dict, today: date) -> dict:
    """把 data/logos/manual/ 的人工 Logo 套進索引與 data/logos/<代號>.png。回摘要。

    - 人工檔**優先**：不管那家原本有沒有自動抓到的圖，一律換成人工的；之後 select_todo 永遠跳過它、_record 也不覆寫。
    - 一樣走 normalize_image（等比縮放、透明補邊，不裁不拉不改色），跟自動來源同一套「不修改圖形」保證；
      16px 以上都收（人挑過的圖不用再擋低解析）。長寬比超過 5:1 仍然不收 ——
      縮進 20px 的框只剩一條線，請裁成接近正方形再放（docs/logo_manual.md）。
    - 原始檔的雜湊記在 `manual_sha1`：人工檔沒換就不重做；換了圖就重做。
    - 人工檔被刪掉：索引改回 none、版號歸零，下一輪由自動來源重抓。
    - manual.json 沒寫來源網址的照樣套用，但記進摘要的 `missing_meta`（CEO 要補）。
    """
    files = manual_files()
    meta = read_manual_meta()
    stat: dict = {"files": len(files), "applied": [], "errors": [], "missing_meta": [], "removed": []}
    stamp = today.isoformat()
    for code, f in sorted(files.items()):
        try:
            raw = f.read_bytes()
        except OSError as exc:
            stat["errors"].append({"code": code, "detail": f"讀不到 {f.name}：{exc}"[:200]})
            continue
        m = meta.get(code) or {}
        if not str(m.get("source_url") or "").strip():
            stat["missing_meta"].append(code)
        old = items.get(code) or {}
        rsha = sha1(raw)
        if (old.get("src") == "manual" and old.get("manual_sha1") == rsha
                and (logo_dir() / f"{code}.png").exists()):
            # 圖沒換：只同步 manual.json 的來源欄位（CEO 可能事後才補來源）
            _manual_meta_fields(old, m)
            continue
        try:
            png, orig = normalize_image(raw, allow_lowres=True)
        except LogoReject as rej:
            stat["errors"].append({"code": code, "detail": f"{f.name} 不能用：{rej.reason} {rej.detail}"[:200]})
            log.warning("人工 Logo %s 不能用（%s %s），沿用原本的紀錄", f.name, rej.reason, rej.detail)
            continue
        rec = {"status": "ok", "src": "manual", "domain": old.get("domain"), "fetched": stamp,
               "strategy": config.LOGO_STRATEGY, "orig": list(orig), "manual_sha1": rsha,
               "manual_file": f"{config.LOGO_MANUAL_SUBDIR}/{f.name}",
               "sha1": _save_png(code, png, old.get("sha1") if old.get("src") == "manual" else None)}
        _manual_meta_fields(rec, m)
        if old and old.get("src") != "manual":
            rec["replaced"] = {k: old.get(k) for k in ("status", "src", "url") if old.get(k)}
        items[code] = rec
        stat["applied"].append(code)
    for code, rec in list(items.items()):
        if rec.get("src") == "manual" and code not in files:
            (logo_dir() / f"{code}.png").unlink(missing_ok=True)
            items[code] = {"status": "none", "domain": rec.get("domain"), "fetched": stamp, "strategy": 0,
                           "detail": "人工 Logo 已移除，下一輪由自動來源重抓"}
            stat["removed"].append(code)
    if stat["applied"] or stat["removed"] or stat["errors"]:
        log.info("人工 Logo：套用 %s、移除 %s、不能用 %s、缺來源紀錄 %s",
                 stat["applied"], stat["removed"], [e["code"] for e in stat["errors"]], stat["missing_meta"])
    return stat


def _manual_meta_fields(rec: dict, m: dict) -> None:
    if m.get("source_url"):
        rec["source_url"] = str(m["source_url"])
    if m.get("date"):
        rec["manual_date"] = str(m["date"])
    if m.get("note"):
        rec["manual_note"] = str(m["note"])[:200]


def manual_pending(idx: dict | None = None) -> list[str]:
    """還沒套進索引（或已換圖、已刪除）的人工 Logo 代號。backfill.yml 的排程守門用它決定要不要放行一輪。"""
    idx = idx if idx is not None else read_index()
    items = idx.get("items", {})
    out = []
    files = manual_files()
    for code, f in files.items():
        rec = items.get(code) or {}
        try:
            if rec.get("src") != "manual" or rec.get("manual_sha1") != sha1(f.read_bytes()):
                out.append(code)
        except OSError:
            continue
    out += [c for c, r in items.items() if r.get("src") == "manual" and c not in files]
    return sorted(out)


def _site_of(sites: pd.DataFrame, code: str):
    hit = sites[sites["code"].map(clean_code) == code]
    return None if hit.empty else hit.iloc[0]["website"]


def _fetch_rows(todo: list[dict], fetcher, deadline: float) -> tuple[dict, bool]:
    """並行抓一批（每個網域只抓一次，同網域的其他代號沿用結果）。回 ({代號: 結果}, 是否撞到時間上限)。"""
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
        futs = [ex.submit(one, row) for row in firsts]
        for fu in as_completed(futs):
            if fu.cancelled():
                continue
            try:
                row, res, _ = fu.result()
            except Exception as exc:  # noqa: BLE001 —— 一家出事不能讓整輪的結果都沒寫
                log.warning("Logo：抓取執行緒拋出例外：%s", exc)
                continue
            results[row["code"]] = res
            if time.time() > deadline and not deadline_hit:
                deadline_hit = True
                log.warning("Logo：這輪時間到，剩下的下一輪接續")
                for f in futs:
                    f.cancel()
    for row in rest:
        d = base_domain(row["domain"])
        if d in by_domain:
            results[row["code"]] = dict(by_domain[d])
    return results, deadline_hit


def _record(items: dict, code: str, res: dict, stamp: str, counts: dict, failures: list) -> None:
    """把一家的抓取結果寫進索引（PNG 也在這裡存）。之前有圖、這次沒抓到的保留舊圖。"""
    st = res.get("status", "error")
    if st == "no_website":
        return
    old = items.get(code) or {}
    if old.get("src") == "manual":
        # 人工指定的 Logo 優先（第四版）：select_todo 已經跳過它，這裡是第二道保險 —— 同網域共用結果時也可能走到這裡
        counts["manual_kept"] = counts.get("manual_kept", 0) + 1
        return
    rec = {"status": st, "domain": res.get("domain"), "fetched": stamp,
           "strategy": config.LOGO_STRATEGY}
    if res.get("site"):
        rec["site"] = res["site"]      # 首頁轉到同公司的另一個網域：記下來，網域變了要看得到
    if st == "ok":
        rec.update(src=res.get("src"), url=res.get("url"), orig=res.get("orig"),
                   sha1=_save_png(code, res["png"], old.get("sha1")))
        if res.get("lowres"):
            rec["lowres"] = True       # 前端不看這欄；給下一個人查「為什麼這家的圖糊」、給 30 天重找用
        if res.get("attribution"):
            rec["attribution"] = res["attribution"]   # Wikimedia 來源：檔名、授權、作者、出處頁（CC BY／BY-SA 必記）
        if res.get("site_fail"):
            rec["site_fail"] = res["site_fail"]       # 官網那條路為什麼沒用（robots、找不到、只有低解析…）
        if res.get("via"):
            rec["via"] = res["via"]                   # group＝圖取自申報官網轉過去的集團官網（那一頁提到這家公司）
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
