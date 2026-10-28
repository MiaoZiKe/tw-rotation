"""公司實景照片素材庫 v2「圖池」（Andy 2026-10-28：「為何有部分沒有圖片，若是沒有圖片可以改用相關產品圖片，並且圖片可以多樣，相關的也可以」）。
只從 Wikimedia Commons 取 CC0／CC BY／CC BY-SA／公有領域的照片，記下作者、授權、原始網址。
不抓新聞媒體、Google 圖片、公司官網照片；不放 LOGO 為主角的圖。容器連不到外網，所以在 GitHub Actions 跑
（.github/workflows/company_photos.yml）。

每家一個圖池：social/photo_lib/<slug>/photo_1..N.jpg ＋ pool.json（photos 每張一筆 meta，含 kind：
總部/廠房、產品、相關場景；rejected＝退件過的檔名，不再抓）。目標每家 3～5 張：
  總部/廠房 ≤2（queries，需含公司名＋建築字）、產品 ≤2（product_queries）、相關場景 ≤1（related_queries）。
類別通用圖池：social/photo_lib/_category/<類別>/（categories.json 的查詢字，每類 ≤8 張），找不到公司圖時用。
新抓的 reviewed 一律 false，須 art-director 審過改 true 才可用。已有的照片不覆蓋，只補到上限。
用法：python scripts/company_photos.py [--only slug1,slug2] [--no-category] [--only-category]"""
from __future__ import annotations
import io, json, re, sys, time, html as _html
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "social" / "photo_lib"
CAT_DIR = LIB / "_category"
API = "https://commons.wikimedia.org/w/api.php"
UA = "tw-rotation-photo-lib/2.0 (https://github.com/MiaoZiKe/tw-rotation; social news cards)"
OK_LIC = re.compile(r"^(cc0|cc[- ]by(-sa)?[- ]\d(\.\d)?.*|cc[- ]by(-sa)?|public domain|pd.*)$", re.I)
BAD_WORD = re.compile(r"logo|icon|map|chart|graph|diagram|screenshot|portrait|ceo|award|signature|svg|banner|flag|seal|card\b|"
                      r"stock certificate|protest|fire|accident|crash|wreck|selfie|interview|speech|keynote", re.I)
PLACE = re.compile(r"headquarter|\bhq\b|building|campus|office|fab\b|fab\d|factory|plant|tower|park|center|centre|plex|spheres|"
                   r"gigafactory|refinery|works|ship|vessel|site|facility|總部|大樓|廠|園區", re.I)
QUOTA = {"總部/廠房": 2, "產品": 2, "相關場景": 1}
CAT_MAX = 8
STOP = {"the", "and", "of", "in", "at", "for", "with", "taiwan", "data", "center", "close", "up"}


def lic_ok(short: str) -> bool:
    s = (short or "").strip()
    return bool(OK_LIC.match(s)) and "nc" not in s.lower() and "nd" not in s.lower().replace("and", "")


def strip_html(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def search(sess, q: str, limit: int = 25) -> list[dict]:
    r = sess.get(API, params=dict(action="query", format="json", generator="search", gsrsearch=f"{q} filetype:bitmap",
                                  gsrnamespace=6, gsrlimit=limit, prop="imageinfo", iiprop="url|size|mime|extmetadata",
                                  iiurlwidth=1920), timeout=60)
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages") or {}
    return sorted(pages.values(), key=lambda p: p.get("index", 99))


def tokens(q: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) >= 3 and w not in STOP]


def candidates(pages: list[dict], kind: str, name_en: str, q: str, seen: set[str], key: str = ""):
    """依 kind 篩：總部/廠房＝含公司名（targets 的 key，沒填取英文名第一個字）＋建築字；產品／相關場景／類別＝含查詢字裡至少一個實詞。"""
    key = (key or name_en.split()[0]).lower().replace("-", "")
    qt = tokens(q)
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata") or {}
        title = p.get("title", ""); desc = strip_html((md.get("ImageDescription") or {}).get("value", ""))
        lic = strip_html((md.get("LicenseShortName") or {}).get("value", ""))
        if title in seen: continue
        if ii.get("mime") != "image/jpeg" or not lic_ok(lic): continue
        if (ii.get("width") or 0) < 1200 or (ii.get("height") or 0) < 600: continue
        if (ii.get("width") or 1) / (ii.get("height") or 1) < 0.9: continue      # 直式圖裁成橫幅會失真，跳過
        if BAD_WORD.search(title): continue
        text = f"{title} {desc}".lower().replace("-", "")
        if kind == "總部/廠房":
            if key not in text or not PLACE.search(text): continue
        elif qt and not any(w in text for w in qt):
            continue
        yield dict(title=title, ii=ii, md=md, lic=lic, desc=desc)


def save(sess, d: Path, n: int, c: dict, kind: str, q: str, slug: str, name_en: str) -> dict:
    from PIL import Image
    url = c["ii"].get("thumburl") or c["ii"]["url"]
    r = sess.get(url, timeout=120); r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    if im.width > 1920: im = im.resize((1920, int(im.height * 1920 / im.width)), Image.LANCZOS)
    d.mkdir(parents=True, exist_ok=True)
    fn = f"photo_{n}.jpg"
    im.save(d / fn, quality=86, optimize=True)      # 原色，只縮放；不調色
    md = c["md"]
    return dict(file=fn, kind=kind, slug=slug, name_en=name_en, query=q, file_title=c["title"],
                source_url=c["ii"].get("descriptionurl"), image_url=c["ii"]["url"],
                license=c["lic"], license_url=strip_html((md.get("LicenseUrl") or {}).get("value", "")),
                author=strip_html((md.get("Artist") or {}).get("value", ""))[:120] or "不詳",
                credit=strip_html((md.get("Credit") or {}).get("value", ""))[:160],
                description=c["desc"][:300], width=im.width, height=im.height,
                fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                reviewed=False, reviewer="", review_note="")


def load_pool(d: Path, slug: str) -> dict:
    try:
        return json.loads((d / "pool.json").read_text(encoding="utf-8"))
    except Exception:
        return dict(slug=slug, photos=[], rejected=[])


def fill(sess, d: Path, slug: str, name_en: str, plan: list[tuple[str, list[str], int]], gseen: set[str], key: str = "") -> dict:
    """plan＝[(kind, 查詢字, 上限)]；補到上限為止，已在池裡／退件過／別家用過的檔名跳過。"""
    pool = load_pool(d, slug)
    seen = gseen | {x.get("file_title") for x in pool["photos"]} | {x.get("file_title") for x in pool.get("rejected", [])}
    used_n = {int(m.group(1)) for x in pool["photos"] if (m := re.match(r"photo_(\d+)\.jpg", x.get("file", "")))}
    added = 0
    for kind, qs, cap in plan:
        have = sum(1 for x in pool["photos"] if x.get("kind") == kind and not x.get("reject_reason"))   # 複審退件的不佔名額
        for q in qs:
            if have >= cap: break
            try:
                cs = list(candidates(search(sess, q), kind, name_en, q, seen, key))
            except Exception as ex:      # 單一查詢失敗不影響其他
                print(slug, q, "查詢失敗", ex); cs = []
            time.sleep(1)
            for c in cs[:max(0, cap - have)]:
                n = 1
                while n in used_n: n += 1
                try:
                    pool["photos"].append(save(sess, d, n, c, kind, q, slug, name_en))
                except Exception as ex:
                    print(slug, c["title"], "下載失敗", ex); continue
                used_n.add(n); seen.add(c["title"]); have += 1; added += 1
                if have >= cap: break
    d.mkdir(parents=True, exist_ok=True)
    (d / "pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8")
    gseen.update(x["file_title"] for x in pool["photos"])
    return dict(slug=slug, ok=bool(pool["photos"]), total=len(pool["photos"]), added=added,
                reviewed=sum(1 for x in pool["photos"] if x.get("reviewed")))


def main(argv=None) -> int:
    import requests
    argv = argv or sys.argv[1:]
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv and argv[argv.index("--only") + 1:] else None
    targets = json.loads((LIB / "targets.json").read_text(encoding="utf-8"))
    sess = requests.Session(); sess.headers["User-Agent"] = UA
    gseen: set[str] = set()
    log = []
    if "--only-category" not in argv:
        for t in targets:
            if only and t["slug"] not in only: continue
            plan = [("總部/廠房", t["queries"] + [t["name_en"]], QUOTA["總部/廠房"]),
                    ("產品", t.get("product_queries", []), QUOTA["產品"]),
                    ("相關場景", t.get("related_queries", []), QUOTA["相關場景"])]
            res = fill(sess, LIB / t["slug"], t["slug"], t["name_en"], plan, gseen, t.get("key", "")); print(res); log.append(res)
    cats = []
    if "--no-category" not in argv:
        for cat, qs in json.loads((LIB / "categories.json").read_text(encoding="utf-8")).items():
            if only and "--only-category" in argv and cat not in only: continue      # --only 也可指定類別名（例如 總經_央行）
            plan = [("類別", [q], min(CAT_MAX, (i + 1) * 2)) for i, q in enumerate(qs)] + [("類別", qs, CAT_MAX)]   # 每個查詢字約 2 張，查詢字之間多樣
            res = fill(sess, CAT_DIR / cat, cat, cat, plan, gseen)
            print(res); cats.append(res)
    if only:
        try:      # 類別也只抓一部分時，保留其他類別的紀錄
            pc = {x["slug"]: x for x in json.loads((LIB / "fetch_log.json").read_text(encoding="utf-8")).get("categories", [])}
            pc.update({x["slug"]: x for x in cats}); cats = list(pc.values())
        except Exception:
            pass
    if only:      # 只抓部分時，與上一次完整紀錄合併，保留其他家的狀態
        try:
            prev = {x["slug"]: x for x in json.loads((LIB / "fetch_log.json").read_text(encoding="utf-8"))["items"]}
            prev.update({x["slug"]: x for x in log}); log = list(prev.values())
        except Exception:
            pass
    got = [x for x in log if x["ok"]]
    (LIB / "fetch_log.json").write_text(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ok=len(got), miss=[x["slug"] for x in log if not x["ok"]], items=log, categories=cats), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"公司圖池 {len(got)} 家有圖，無圖 {len(log) - len(got)} 家；類別池 {sum(x['total'] for x in cats)} 張")
    return 0


if __name__ == "__main__":
    sys.exit(main())
