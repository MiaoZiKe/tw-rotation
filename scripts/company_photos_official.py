"""公司官方照片來源（official）：抓公司官方新聞室／媒體資源／官網「關於我們、廠區、產品」頁面上的照片。

依據：Andy 2026-10-30 拍板「改成接用 並標明出處 是可以的」（DECISIONS #373、photo_lib_review.md 第九節）。
- license 一律寫 `official-press`；卡上署名「圖：<公司名>官方」（targets.json 的 `official_credit` 依網域覆寫官方指定署名）。
- 只抓 targets.json 裡 `official_sites` 列的網域（種子頁＋同網域、網址或連結文字像「關於／廠區／產品／新聞室／媒體」的頁面，每家最多 MAX_PAGES 頁）。
- 檔名或 alt 像標誌、人像、主管、活動、獎項的圖不抓；寬 < 1000、直式（寬高比 < 1.25）、幾乎單色（插畫底圖）不抓。
- 新抓的 reviewed=false、origin=official，必須 art-director 逐張照 photo_lib_review.md 審過才可用（人物主角、媒體／新聞社拍的、標誌主視覺、AI 生圖一律退件）。
- 容器連不到外網，所以在 GitHub Actions 跑（company_photos.yml，source=official）。用 Playwright 真瀏覽器開頁，才抓得到 JS 載入與 lazy-load 的圖。
用法：python scripts/company_photos.py --source official [--only slug1,slug2]"""
from __future__ import annotations
import hashlib, io, json, os, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

MAX_PAGES = 30          # 每家最多開幾頁
MAX_NEW = 14            # 每家一次最多新增幾張候選（待審）
MIN_W, MIN_H, MIN_AR = 800, 420, 1.25     # 封面照片區 952×約 440；再小的網頁橫幅裁成封面會糊（審核時再看清晰度）
MAX_PDF = 3             # 官網找不到照片時，再從官方永續報告書／年報 PDF 裡取照片（每家最多開 3 份）
PDF_KW = re.compile(r"永續|ESG|CSR|sustainab|annual|年報|企業社會責任|報告書", re.I)
PREFIX_CAP = 3          # 同一路徑前綴（前兩層）最多開幾頁，避免被產品清單頁灌爆
# 連結優先序：廠區／據點／總部／圖庫 > 關於／媒體 > 產品 > 其他
LINK_PRI = [(re.compile(r"facilit|fab\b|fabs|plant|factory|campus|location|headquart|site-?tour|gallery|photo|image|multimedia|media-?(kit|library|asset)|廠|據點|園區|總部", re.I), 0),
            (re.compile(r"about|company|corporate|overview|press|newsroom|esg|csr|sustainab|report|關於|公司|簡介|新聞|媒體|永續|報告", re.I), 1),
            (re.compile(r"product|technolog|data-?center|infrastructure|產品|技術", re.I), 2)]
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126.0 Safari/537.36")
# 連結：像「關於／廠區／據點／產品／新聞室／媒體／圖庫」的頁面才跟進
LINK_OK = re.compile(r"about|company|corporate|overview|facilit|fab\b|fabs|plant|factory|campus|location|site|office|headquart|"
                     r"manufactur|operation|global|news|press|media|gallery|image|photo|multimedia|product|technolog|data-?center|"
                     r"infrastructure|cloud|esg|csr|sustainab|report|關於|公司|簡介|廠|據點|營運|新聞|媒體|產品|技術|全球|永續|報告", re.I)
LINK_BAD = re.compile(r"career|job|recruit|investor|ir\.|financial|login|signin|account|privacy|legal|terms|cookie|contact|"
                      r"\.pdf$|\.zip$|mailto:|javascript:|tel:|#|人才|招募|投資人|財務|隱私|條款|登入", re.I)
# 圖：網址或 alt 像這些字的不抓（標誌、人像、活動、獎項、圖示）
IMG_BAD = re.compile(r"logo|(?<![a-z])icons?(?![a-z])|favicon|sprite|avatar|headshot|portrait|people|person|team|leader|executive|ceo|cfo|founder|"
                     r"board-?of|boardroom|chairman|president|speaker|keynote|award|ceremony|signing|event|staff|employee|selfie|interview|"
                     r"(?<![a-z])qr|badge|flag|(?<![a-z])map(?![a-z])|chart|infographic|diagram|banner-text|placeholder|blank|loading|"
                     r"董事|總經理|執行長|人物|頒獎|典禮|活動|標誌", re.I)


def credit_for(t: dict, url: str) -> str:
    host = urlparse(url).netloc.lower()
    for dom, cr in (t.get("official_credit") or {}).items():
        if host.endswith(dom.lower()):
            return cr
    return f"圖：{t.get('credit_name') or (t.get('zh') or [t['name_en']])[0]}官方"


def _root(host: str) -> str:
    """註冊網域：nanyapcb.com.tw → nanyapcb.com.tw（不是 com.tw）；www.arm.com → arm.com。"""
    p = host.lower().split(".")
    n = 3 if len(p) >= 3 and len(p[-1]) == 2 and p[-2] in ("com", "co", "org", "net", "gov", "edu", "ac") else 2
    return ".".join(p[-n:])


def _domain_ok(url: str, sites: list[str]) -> bool:
    host = urlparse(url).netloc.lower()
    roots = {_root(urlparse(s).netloc) for s in sites}
    return any(host == r or host.endswith("." + r) for r in roots)


def _collect(page) -> dict:
    """回傳頁面上的圖（網址、alt、顯示寬）與連結。"""
    for _ in range(8):                      # 捲動觸發 lazy-load
        page.mouse.wheel(0, 2400); page.wait_for_timeout(400)
    return page.evaluate("""() => {
      const big = s => { if (!s) return null; let best=null, bw=0;
        for (const p of s.split(',')) { const [u, w] = p.trim().split(/\\s+/); const n = parseInt(w) || 1; if (n >= bw) { bw = n; best = u; } } return best; };
      const imgs = [];
      for (const im of document.images) imgs.push({src: big(im.getAttribute('srcset') || im.getAttribute('data-srcset')) || im.currentSrc || im.src || im.getAttribute('data-src'),
                                                   alt: (im.alt || '') + ' ' + (im.title || ''), w: im.naturalWidth || 0});
      for (const s of document.querySelectorAll('picture source')) imgs.push({src: big(s.srcset), alt: '', w: 0});
      for (const el of document.querySelectorAll('[style*="background"]')) { const m = /url\\(["']?([^"')]+)/.exec(el.getAttribute('style') || ''); if (m) imgs.push({src: m[1], alt: el.getAttribute('aria-label') || '', w: 0}); }
      const og = document.querySelector('meta[property="og:image"]'); if (og) imgs.push({src: og.content, alt: 'og', w: 0});
      const links = [...document.querySelectorAll('a[href]')].map(a => ({href: a.href, text: (a.innerText || '').trim().slice(0, 60)}));
      return {imgs, links, title: document.title};
    }""")


def _kind_of(page_url: str, alt: str) -> str:
    s = f"{page_url} {alt}".lower()
    if re.search(r"product|solution|technolog|gpu|memory|dram|chip|substrate|laminate|pcb|產品|技術", s): return "產品"
    return "總部/廠房"


def _flat(im) -> bool:
    """幾乎單色或色數極少（插畫底圖、純色橫幅）→ True。"""
    from PIL import ImageStat
    sm = im.convert("L").resize((64, 32))
    return ImageStat.Stat(sm).stddev[0] < 18 or len(set(im.convert("RGB").resize((48, 24)).getdata())) < 120


def _pri(href: str, text: str) -> int:
    for rx, p in LINK_PRI:
        if rx.search(href) or rx.search(text or ""): return p
    return 3


def _prefix(url: str) -> str:
    u = urlparse(url); return u.netloc + "/".join(u.path.split("/")[:3])


def _download(dl, sess, src: str, referer: str) -> bytes:
    """先用瀏覽器分頁開圖（帶 cookie、真瀏覽器指紋，擋爬蟲的 CDN 也開得了）；失敗再用 requests。"""
    try:
        if re.search(r"\.pdf(\?|$)", src, re.I):      # 瀏覽器開 PDF 會回內建閱讀器的 HTML，改用同一個瀏覽器環境的 API 請求（帶 cookie）
            r = dl.context.request.get(src, timeout=120000, headers={"Referer": referer})
            if r.ok and r.body()[:4] == b"%PDF": return r.body()
        else:
            r = dl.goto(src, timeout=45000, referer=referer)
            if r and r.ok:
                b = r.body()
                if b: return b
    except Exception:
        pass
    r = sess.get(src, timeout=60, headers={"User-Agent": BROWSER_UA, "Referer": referer}); r.raise_for_status()
    return r.content


def _pdf_images(data: bytes):
    """官方 PDF 內嵌的點陣圖（照片），依頁序回傳 (PIL 影像, 頁碼)。需要 PyMuPDF（工作流程官方來源步驟有裝）。"""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    from PIL import Image
    doc = fitz.open(stream=data, filetype="pdf")
    for pno, page in enumerate(doc, 1):
        for x in page.get_images(full=True):
            try:
                pix = fitz.Pixmap(doc, x[0])
                if pix.n - pix.alpha >= 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width < MIN_W: continue
                yield Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"), pno
            except Exception:
                continue


def fetch_official(t: dict, d: Path, sess, gseen: set[str]) -> dict:
    from PIL import Image
    from playwright.sync_api import sync_playwright
    slug, sites = t["slug"], t.get("official_sites") or []
    pool = json.loads((d / "pool.json").read_text(encoding="utf-8")) if (d / "pool.json").exists() else dict(slug=slug, photos=[], rejected=[])
    seen = gseen | {x.get("image_url") for x in pool["photos"]} | {x.get("file_title") for x in pool.get("rejected", [])}
    hashes = {x.get("sha1") for x in pool["photos"] + pool.get("rejected", []) if x.get("sha1")}
    used_n = {int(m.group(1)) for x in pool["photos"] if (m := re.match(r"photo_(\d+)\.jpg", x.get("file", "")))}
    pages_log, added = [], 0
    today = (datetime.now(timezone.utc) + timedelta(hours=8)).date().isoformat()
    if not sites:
        return dict(slug=slug, source="official", added=0, pages=[], note="targets.json 沒有 official_sites")
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        ctx = br.new_context(user_agent=BROWSER_UA, viewport=dict(width=1600, height=1000), locale="zh-TW")
        pg = ctx.new_page(); dl = ctx.new_page()
        queue = [(-1, i, u) for i, u in enumerate(sites)]      # (優先序, 先後, 網址)；種子頁最優先
        visited, per_prefix, seq, pdfs = set(), {}, len(sites), [u for u in sites if re.search(r"\.pdf(\?|$)", u, re.I)]
        while queue and len(visited) < MAX_PAGES and added < MAX_NEW:
            queue.sort(); _, _, url = queue.pop(0); url = url.split("#")[0]
            if url in visited: continue
            px = _prefix(url)
            if per_prefix.get(px, 0) >= PREFIX_CAP and url not in sites: continue
            visited.add(url); per_prefix[px] = per_prefix.get(px, 0) + 1
            try:
                pg.goto(url, wait_until="domcontentloaded", timeout=45000); pg.wait_for_timeout(2500)
                info = _collect(pg)
            except Exception as ex:
                pages_log.append(dict(url=url, error=str(ex)[:160])); continue
            n_img, why = 0, {}
            def skip(k): why[k] = why.get(k, 0) + 1
            for im in info["imgs"]:
                src = im.get("src")
                if not src or src.startswith("data:"): skip("無網址"); continue
                src = urljoin(url, src)
                if src in seen: skip("看過"); continue
                if re.search(r"\.(svg|gif)(\?|$)", src, re.I): skip("svg/gif"); continue
                fname = unquote(urlparse(src).path.rsplit("/", 1)[-1])      # 只看檔名（網域「semiconductor」含 icon 字樣，不能整串比）
                if IMG_BAD.search(fname) or IMG_BAD.search(im.get("alt") or ""): skip("檔名像標誌/人像/活動"); continue
                seen.add(src)
                try:
                    img = Image.open(io.BytesIO(_download(dl, sess, src, url))); img.load()
                except Exception:
                    skip("下載失敗"); continue
                if img.width < MIN_W or img.height < MIN_H: skip("太小"); continue
                if img.width / max(1, img.height) < MIN_AR: skip("直式"); continue
                rgb = img.convert("RGB")
                if _flat(rgb): skip("單色/插畫底"); continue
                h = hashlib.sha1(rgb.resize((32, 16)).tobytes()).hexdigest()
                if h in hashes: skip("重複"); continue
                hashes.add(h)
                if rgb.width > 1920: rgb = rgb.resize((1920, int(rgb.height * 1920 / rgb.width)), Image.LANCZOS)
                n = 1
                while n in used_n: n += 1
                fn = f"photo_{n}.jpg"; d.mkdir(parents=True, exist_ok=True)
                rgb.save(d / fn, quality=86, optimize=True)
                used_n.add(n); added += 1; n_img += 1
                pool["photos"].append(dict(file=fn, kind=_kind_of(url, im.get("alt") or ""), slug=slug, name_en=t["name_en"], origin="official",
                                           query="official", file_title=src, source_page=url, source_url=url, image_url=src,
                                           license="official-press", license_url="", author=credit_for(t, url).removeprefix("圖："),
                                           credit=credit_for(t, url), description=(im.get("alt") or "").strip()[:200] or info.get("title", "")[:200],
                                           width=rgb.width, height=rgb.height, sha1=h, fetched_at=today, fetched_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                           reviewed=False, reviewer="", review_note=""))
                if added >= MAX_NEW: break
            pages_log.append(dict(url=url, title=info.get("title", "")[:80], imgs=len(info["imgs"]), saved=n_img, skipped=why))
            queued = {u for _, _, u in queue}
            for a in info["links"]:
                href = (a.get("href") or "").split("#")[0]
                if re.search(r"\.pdf(\?|$)", href, re.I) and _domain_ok(href, sites) and href not in pdfs \
                        and (PDF_KW.search(href) or PDF_KW.search(a.get("text") or "")):
                    pdfs.append(href); continue
                if not href.startswith("http") or href in visited or href in queued: continue
                if not _domain_ok(href, sites) or LINK_BAD.search(href): continue
                if LINK_OK.search(href) or LINK_OK.search(a.get("text") or ""):
                    seq += 1; queue.append((_pri(href, a.get("text")), seq, href)); queued.add(href)
            time.sleep(1)
        for pdf in pdfs[:MAX_PDF]:
            if added >= MAX_NEW: break
            n0 = added
            try:
                data = _download(dl, sess, pdf, pdf)
                if len(data) > 80_000_000: raise ValueError("PDF 超過 80MB")
                for img, pno in _pdf_images(data):
                    if added >= MAX_NEW: break
                    key = f"{pdf}#p{pno}-{img.width}x{img.height}"
                    if key in seen: continue
                    seen.add(key)
                    if img.width < MIN_W or img.height < MIN_H or img.width / max(1, img.height) < MIN_AR or _flat(img): continue
                    h = hashlib.sha1(img.resize((32, 16)).tobytes()).hexdigest()
                    if h in hashes: continue
                    hashes.add(h)
                    if img.width > 1920: img = img.resize((1920, int(img.height * 1920 / img.width)), Image.LANCZOS)
                    n = 1
                    while n in used_n: n += 1
                    fn = f"photo_{n}.jpg"; d.mkdir(parents=True, exist_ok=True)
                    img.save(d / fn, quality=86, optimize=True)
                    used_n.add(n); added += 1
                    pool["photos"].append(dict(file=fn, kind="總部/廠房", slug=slug, name_en=t["name_en"], origin="official", query="official-pdf",
                                               file_title=key, source_page=pdf, source_url=pdf, image_url=key, pdf_page=pno,
                                               license="official-press", license_url="", author=credit_for(t, pdf).removeprefix("圖："),
                                               credit=credit_for(t, pdf), description=f"官方報告書 PDF 第 {pno} 頁", width=img.width, height=img.height,
                                               sha1=h, fetched_at=today, fetched_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                               reviewed=False, reviewer="", review_note=""))
                pages_log.append(dict(url=pdf, pdf=True, saved=added - n0))
            except Exception as ex:
                pages_log.append(dict(url=pdf, pdf=True, error=str(ex)[:160]))
        br.close()
    d.mkdir(parents=True, exist_ok=True)
    (d / "pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8")
    return dict(slug=slug, source="official", added=added, pages=pages_log)
