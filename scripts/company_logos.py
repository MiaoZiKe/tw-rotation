"""公司 LOGO（2026-11-11，科技透明圈年薪排名圖用）：`company_photos.py --source logo` 呼叫這支。
法遵：LOGO 只從 Wikimedia Commons 取，且只依 targets.json 每家的 `commons_logo`（指定 Commons 檔名）抓，不搜尋、不猜。
授權白名單：公有領域（含 PD-textlogo）、CC0、CC BY／CC BY-SA（不含 NC／ND）；不在白名單就跳過並記原因。
存檔：social/photo_lib/<slug>/logo.png；SVG 用 cairosvg（沒有就 rsvg-convert）轉成高 512px 透明背景 PNG，
點陣圖只等比縮到高 512（比原圖小就不放大），不調色、不裁切、不改比例。
授權、作者、原始頁面網址寫進 pool.json 的 `logo` 欄位；每家結果另寫 social/photo_lib/logo_log.json。"""
from __future__ import annotations
import io, json, re, shutil, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
LOGO_H = 512
LOGO_FILE = "logo.png"
# LicenseShortName 白名單（Commons extmetadata 的寫法，例如 "Public domain"、"CC0"、"CC BY 4.0"、"CC BY-SA 3.0"）
LOGO_LIC = re.compile(r"^(public domain|pd([- ].*)?|cc0( 1\.0)?|cc[- ]by( \d(\.\d)?)?|cc[- ]by-sa( \d(\.\d)?)?)$", re.I)


def _s(md: dict, k: str) -> str:
    v = (md.get(k) or {}).get("value", "")
    return _html_strip(v if isinstance(v, str) else str(v))


def _html_strip(s: str) -> str:
    import html as _h
    return _h.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def logo_license(md: dict) -> tuple[bool, str, str]:
    """回 (是否在白名單, 授權名, 原因)。PD-textlogo 由 Commons 分類辨認（extmetadata Categories 含 "PD textlogo"）。"""
    short = _s(md, "LicenseShortName")
    code = _s(md, "License").lower()
    cats = _s(md, "Categories")
    if re.search(r"(^|\|)PD[ _]textlogo", cats, re.I):
        name = "PD-textlogo"
    else:
        name = short
    low = f"{short} {code}".lower()
    if not short and not code:
        return False, "", "Commons 沒有授權資訊"
    if re.search(r"\bnc\b|-nc|non[- ]?commercial", low):
        return False, short, f"授權含 NC（非商用）：{short}"
    if re.search(r"\bnd\b|-nd|no ?deriv", low):
        return False, short, f"授權含 ND（禁止改作）：{short}"
    if re.search(r"fair use|non[- ]?free", low):
        return False, short, f"非自由授權：{short}"
    if name == "PD-textlogo" or LOGO_LIC.match(short.strip()) or re.match(r"^(pd|cc0|cc-by(-sa)?-\d(\.\d)?)$", code):
        return True, name, ""
    return False, short, f"授權不在白名單：{short or code}"


def query_file(sess, title: str) -> dict | None:
    r = sess.get(API, params=dict(action="query", format="json", titles=title, redirects=1, prop="imageinfo",
                                  iiprop="url|size|mime|extmetadata", iiextmetadatafilter=
                                  "LicenseShortName|License|LicenseUrl|Artist|Credit|ImageDescription|Categories|Restrictions|UsageTerms|AttributionRequired"),
                 timeout=60)
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages") or {}
    for pg in pages.values():
        if "missing" in pg or not pg.get("imageinfo"):
            return None
        return pg
    return None


def svg_to_png(data: bytes, height: int = LOGO_H) -> bytes:
    """SVG → 高 height 的透明背景 PNG（寬依原比例）。先 cairosvg，沒裝再用 rsvg-convert。"""
    try:
        import cairosvg
        return cairosvg.svg2png(bytestring=data, output_height=height)
    except ImportError:
        pass
    exe = shutil.which("rsvg-convert")
    if not exe:
        raise RuntimeError("沒有 cairosvg 也沒有 rsvg-convert，無法轉 SVG")
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "in.svg"; src.write_bytes(data)
        return subprocess.run([exe, "-h", str(height), "-b", "none", str(src)], check=True, capture_output=True).stdout


def to_logo_png(data: bytes, mime: str) -> tuple[bytes, int, int]:
    """回 (PNG bytes, 寬, 高)。只等比縮放，不調色、不裁切。"""
    from PIL import Image
    if mime == "image/svg+xml":
        im = Image.open(io.BytesIO(svg_to_png(data)))
        im = im.convert("RGBA")
    else:
        im = Image.open(io.BytesIO(data))
        alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        im = im.convert("RGBA" if alpha else "RGB")
        if im.height > LOGO_H:
            im = im.resize((max(1, round(im.width * LOGO_H / im.height)), LOGO_H), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
    return buf.getvalue(), im.width, im.height


def _load_pool(d: Path, slug: str) -> dict:
    try:
        return json.loads((d / "pool.json").read_text(encoding="utf-8"))
    except Exception:
        return dict(slug=slug, photos=[], rejected=[])


def _write_pool(d: Path, pool: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "pool.json").write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8")


def fetch_logo(sess, d: Path, t: dict) -> dict:
    """抓一家的 LOGO；回這家的結果（status＝ok／kept／skipped／missing／empty／error）。"""
    slug = t["slug"]; title = (t.get("commons_logo") or "").strip()
    base = dict(slug=slug, zh=(t.get("zh") or [""])[0], commons_logo=title)
    if not title:
        return {**base, "status": "empty", "reason": "targets.json 的 commons_logo 是空的（Commons 上沒查到可確認的檔名）"}
    if not title.startswith("File:"):
        title = "File:" + title
    pool = _load_pool(d, slug)
    old = pool.get("logo") or {}
    if old.get("status") == "ok" and old.get("commons_title") == title and (d / LOGO_FILE).exists():
        return {**base, "status": "kept", "license": old.get("license"), "reason": "已有，同一個檔名不重抓"}
    pg = query_file(sess, title)
    if pg is None:
        return {**base, "status": "missing", "reason": "Commons 上沒有這個檔名"}
    ii = pg["imageinfo"][0]; md = ii.get("extmetadata") or {}
    ok, lic, why = logo_license(md)
    meta = dict(commons_title=pg.get("title", title), source_url=ii.get("descriptionurl"), image_url=ii.get("url"),
                mime=ii.get("mime"), license=lic, license_short=_s(md, "LicenseShortName"), license_code=_s(md, "License"),
                license_url=_s(md, "LicenseUrl"), author=_s(md, "Artist")[:160] or "不詳", credit=_s(md, "Credit")[:200],
                restrictions=_s(md, "Restrictions"), attribution_required=_s(md, "AttributionRequired"),
                orig_width=ii.get("width"), orig_height=ii.get("height"),
                fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    if not ok:
        if old.get("status") != "ok":        # 已有合格的就不蓋掉，只回報這次為何沒換
            pool["logo"] = dict(status="skipped", reason=why, **meta); _write_pool(d, pool)
        return {**base, "status": "skipped", "license": lic, "reason": why, "source_url": meta["source_url"]}
    if ii.get("mime") not in ("image/svg+xml", "image/png", "image/jpeg", "image/gif", "image/webp"):
        return {**base, "status": "skipped", "license": lic, "reason": f"檔案格式不是圖片：{ii.get('mime')}"}
    r = sess.get(ii["url"], timeout=120); r.raise_for_status()
    png, w, h = to_logo_png(r.content, ii["mime"])
    d.mkdir(parents=True, exist_ok=True)
    (d / LOGO_FILE).write_bytes(png)
    pool["logo"] = dict(status="ok", file=LOGO_FILE, width=w, height=h, converted_from_svg=ii["mime"] == "image/svg+xml",
                        note="原色、原比例，只等比縮放；使用時不准改色、變形、加效果", **meta)
    _write_pool(d, pool)
    return {**base, "status": "ok", "license": lic, "width": w, "height": h, "source_url": meta["source_url"]}


def run_logos(sess, lib: Path, targets: list[dict], only: set[str] | None = None) -> list[dict]:
    """依 targets.json 跑有 `commons_logo` 欄位（空字串也算，會記成 empty）的公司；一家失敗不影響其他家。"""
    out = []
    for t in targets:
        if only and t["slug"] not in only: continue
        if "commons_logo" not in t: continue
        try:
            res = fetch_logo(sess, lib / t["slug"], t)
        except Exception as ex:
            res = dict(slug=t["slug"], commons_logo=t.get("commons_logo"), status="error", reason=str(ex)[:300])
        print(res["slug"], res["status"], res.get("license", ""), res.get("reason", "")); out.append(res)
    try:
        prev = {x["slug"]: x for x in json.loads((lib / "logo_log.json").read_text(encoding="utf-8")).get("items", [])}
    except Exception:
        prev = {}
    prev.update({x["slug"]: x for x in out})
    items = list(prev.values())
    (lib / "logo_log.json").write_text(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ok=[x["slug"] for x in items if x["status"] in ("ok", "kept")],
        miss=[x["slug"] for x in items if x["status"] not in ("ok", "kept")], items=items), ensure_ascii=False, indent=1), encoding="utf-8")
    return out
