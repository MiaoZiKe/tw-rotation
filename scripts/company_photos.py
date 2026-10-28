"""公司實景照片素材庫（Andy 2026-10-28：新聞卡上方改放對應公司的實景圖）。
只從 Wikimedia Commons 取 CC0／CC BY／CC BY-SA／公有領域的照片，記下作者、授權、原始網址。
不抓新聞媒體、Google 圖片、公司官網照片；不放 LOGO。容器連不到外網，所以在 GitHub Actions 跑
（.github/workflows/company_photos.yml）。
用法：python scripts/company_photos.py [--only slug1,slug2] [--refresh]
輸出：social/photo_lib/<slug>/{photo.jpg,meta.json}；meta.reviewed 一律 false，須 art-director 審過改 true 才可用。
已存在的 slug 預設跳過（不覆蓋已審核的圖）；--refresh 只重抓 reviewed=false 的。"""
from __future__ import annotations
import io, json, re, sys, time, html as _html
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "social" / "photo_lib"
API = "https://commons.wikimedia.org/w/api.php"
UA = "tw-rotation-photo-lib/1.0 (https://github.com/MiaoZiKe/tw-rotation; social news cards)"
OK_LIC = re.compile(r"^(cc0|cc[- ]by(-sa)?[- ]\d(\.\d)?.*|cc[- ]by(-sa)?|public domain|pd.*)$", re.I)
BAD_WORD = re.compile(r"logo|icon|map|chart|graph|diagram|screenshot|portrait|ceo|award|signature|svg|banner|flag|seal|card|stock certificate", re.I)
PLACE = re.compile(r"headquarter|\bhq\b|building|campus|office|fab\b|fab\d|factory|plant|tower|park|center|centre|plex|spheres|"
                   r"gigafactory|refinery|works|ship|vessel|site|facility|總部|大樓|廠|園區", re.I)


def lic_ok(short: str) -> bool:
    s = (short or "").strip()
    return bool(OK_LIC.match(s)) and "nc" not in s.lower() and "nd" not in s.lower().replace("and", "")


def strip_html(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def search(sess, q: str, limit: int = 20) -> list[dict]:
    r = sess.get(API, params=dict(action="query", format="json", generator="search", gsrsearch=f"{q} filetype:bitmap",
                                  gsrnamespace=6, gsrlimit=limit, prop="imageinfo", iiprop="url|size|mime|extmetadata",
                                  iiurlwidth=1920), timeout=60)
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages") or {}
    return sorted(pages.values(), key=lambda p: p.get("index", 99))


def choose(pages: list[dict], name_en: str) -> dict | None:
    key = name_en.split()[0].lower().replace("-", "")
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata") or {}
        title = p.get("title", ""); desc = strip_html((md.get("ImageDescription") or {}).get("value", ""))
        lic = strip_html((md.get("LicenseShortName") or {}).get("value", ""))
        if ii.get("mime") != "image/jpeg" or not lic_ok(lic): continue
        if (ii.get("width") or 0) < 1200 or (ii.get("height") or 0) < 600: continue
        if (ii.get("width") or 1) / (ii.get("height") or 1) < 0.9: continue      # 直式圖裁成橫幅會失真，跳過
        if BAD_WORD.search(title): continue
        text = f"{title} {desc}"
        if key not in text.lower().replace("-", "") or not PLACE.search(text): continue
        return dict(title=title, ii=ii, md=md, lic=lic, desc=desc)
    return None


def fetch_one(sess, slug: str, name_en: str, queries: list[str]) -> dict:
    from PIL import Image
    for q in queries + [name_en]:
        try:
            c = choose(search(sess, q), name_en)
        except Exception as ex:      # 單一查詢失敗不影響其他
            print(slug, q, "查詢失敗", ex); c = None
        time.sleep(1)
        if not c: continue
        url = c["ii"].get("thumburl") or c["ii"]["url"]
        r = sess.get(url, timeout=120); r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        if im.width > 1920: im = im.resize((1920, int(im.height * 1920 / im.width)), Image.LANCZOS)
        d = LIB / slug; d.mkdir(parents=True, exist_ok=True)
        im.save(d / "photo.jpg", quality=86, optimize=True)      # 原色，只縮放；不調色
        md = c["md"]
        meta = dict(slug=slug, name_en=name_en, query=q, file_title=c["title"],
                    source_url=c["ii"].get("descriptionurl"), image_url=c["ii"]["url"],
                    license=c["lic"], license_url=strip_html((md.get("LicenseUrl") or {}).get("value", "")),
                    author=strip_html((md.get("Artist") or {}).get("value", ""))[:120] or "不詳",
                    credit=strip_html((md.get("Credit") or {}).get("value", ""))[:160],
                    description=c["desc"][:300], width=im.width, height=im.height,
                    fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    reviewed=False, reviewer="", review_note="")
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        return dict(slug=slug, ok=True, license=meta["license"], file=c["title"])
    return dict(slug=slug, ok=False)


def main(argv=None) -> int:
    import requests
    argv = argv or sys.argv[1:]
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    refresh = "--refresh" in argv
    targets = json.loads((LIB / "targets.json").read_text(encoding="utf-8"))
    sess = requests.Session(); sess.headers["User-Agent"] = UA
    log = []
    for slug, name_en, _zh, queries in targets:
        if only and slug not in only: continue
        mp = LIB / slug / "meta.json"
        if mp.exists():
            m = json.loads(mp.read_text(encoding="utf-8"))
            if m.get("reviewed") or not refresh:
                log.append(dict(slug=slug, ok=True, skipped=True, license=m.get("license"))); continue
        res = fetch_one(sess, slug, name_en, queries); print(res); log.append(res)
    if only:      # 只抓部分時，與上一次完整紀錄合併，保留其他家的狀態
        try:
            prev = {x["slug"]: x for x in json.loads((LIB / "fetch_log.json").read_text(encoding="utf-8"))["items"]}
            prev.update({x["slug"]: x for x in log}); log = list(prev.values())
        except Exception:
            pass
    got = [x for x in log if x["ok"]]
    (LIB / "fetch_log.json").write_text(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ok=len(got), miss=[x["slug"] for x in log if not x["ok"]], items=log), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"抓到 {len(got)} 家，無圖 {len(log) - len(got)} 家")
    return 0


if __name__ == "__main__":
    sys.exit(main())
