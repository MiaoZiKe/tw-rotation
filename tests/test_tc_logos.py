"""科技透明圈外商 Logo（以網域為鍵，DECISIONS #364）：離線假資料，不打真網路。"""
from __future__ import annotations

import io
import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build_payload, config  # noqa: E402
from pipeline.sources import logo_wikimedia as wm  # noqa: E402
from pipeline.sources import logos as lg  # noqa: E402
from pipeline.sources import tc_logos as tc  # noqa: E402
from pipeline.util import http  # noqa: E402

TODAY = date(2026, 10, 27)


def _png(size=(180, 180), fg=(200, 30, 30, 255)) -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    w, h = size
    ImageDraw.Draw(img).rectangle([w // 4, h // 4, w * 3 // 4, h * 3 // 4], fill=fg)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "data" / "_state")
    monkeypatch.setattr(config, "SITE_DATA", tmp_path / "site" / "data")
    monkeypatch.setattr(config, "LOGOS_ENABLED", True)
    monkeypatch.setattr(wm.time, "sleep", lambda s: None)
    return tmp_path


def _ok(orig=(180, 180), color=(200, 30, 30, 255), src="site:apple-touch-icon"):
    def f(website, host, reject=None, names=None):
        return {"status": "ok", "domain": host, "src": src, "url": website + "/icon.png",
                "png": lg.normalize_image(_png(orig, color))[0], "orig": list(orig)}
    return f


def _fail(status="none", detail="沒有"):
    def f(website, host, reject=None, names=None):
        return {"status": status, "domain": host, "detail": detail}
    return f


def test_domain_list_is_valid_and_has_english_names():
    ds = tc.load_domains()
    assert len(ds) >= 40
    assert len({d["domain"] for d in ds}) == len(ds)
    assert all(d["names"] for d in ds)
    assert next(d for d in ds if d["domain"] == "nvidia.com")["en"]


def test_site_logo_is_saved_at_128px_and_px_restored(sandbox):
    dom = [{"domain": "nvidia.com", "names": ["NVIDIA"], "en": "Nvidia"}]
    s = tc.run(domains=dom, today=TODAY, site_fetcher=_ok(), wiki_fetcher=lambda *a: {}, s2_fetcher=lambda *a: {"status": "none"})
    assert s["have"] == 1 and s["coverage"] == 1.0
    from PIL import Image
    img = Image.open(tc.tc_dir() / "nvidia.com.png")
    assert img.size == (128, 128)
    assert config.LOGO_PX == 64
    rec = tc.read_index()["items"]["nvidia.com"]
    assert rec["status"] == "ok" and rec["names"] == ["NVIDIA"]


def test_small_site_icon_falls_to_wikimedia_then_google(sandbox):
    # 官網只有 32px → 不收；Wikimedia 有 → 用它；google 不該被問
    asked = []
    dom = [{"domain": "a.com", "names": ["甲"], "en": "A Co"}]
    wiki = lambda rows, reject, deadline: {"a.com": {"status": "ok", "domain": "a.com", "src": "wikimedia", "url": "u",
                                                     "png": _png((128, 128)), "orig": [250, 250],
                                                     "attribution": {"file": "File:A.svg", "license": "PD"}}}
    s2 = lambda d, r: asked.append(d) or {"status": "none"}
    s = tc.run(domains=dom, today=TODAY, site_fetcher=_ok((32, 32)), wiki_fetcher=wiki, s2_fetcher=s2)
    rec = tc.read_index()["items"]["a.com"]
    assert rec["src"] == "wikimedia" and s["have"] == 1 and asked == []
    assert "ok" in rec["tried"]["site"] and "wikimedia" in rec["tried"]
    assert (tc.tc_dir() / "ATTRIBUTION.md").exists()


def test_google_256_used_when_site_and_wiki_fail(sandbox):
    dom = [{"domain": "b.com", "names": ["乙"], "en": ""}]
    s2 = lambda d, r: {"status": "ok", "domain": d, "src": "google_s2", "url": "u", "png": _png((128, 128)), "orig": [256, 256]}
    s = tc.run(domains=dom, today=TODAY, site_fetcher=_fail(), wiki_fetcher=lambda *a: {}, s2_fetcher=s2)
    assert tc.read_index()["items"]["b.com"]["src"] == "google_s2" and s["have"] == 1


def test_robots_blocks_google_and_marks_failure(sandbox):
    asked = []
    dom = [{"domain": "c.com", "names": ["丙"], "en": ""}]
    s = tc.run(domains=dom, today=TODAY, site_fetcher=_fail("robots", "Disallow 尊重它"), wiki_fetcher=lambda *a: {},
               s2_fetcher=lambda d, r: asked.append(d) or {"status": "ok"})
    rec = tc.read_index()["items"]["c.com"]
    assert asked == [] and rec["status"] == "robots" and s["have"] == 0
    assert not (tc.tc_dir() / "c.com.png").exists()


def test_sub48_everywhere_is_rejected_not_stored(sandbox):
    dom = [{"domain": "d.com", "names": ["丁"], "en": ""}]
    s2 = lambda d, r: {"status": "ok", "domain": d, "src": "google_s2", "url": "u", "png": _png((40, 40)), "orig": [40, 40]}
    s = tc.run(domains=dom, today=TODAY, site_fetcher=_ok((40, 40)), wiki_fetcher=lambda *a: {}, s2_fetcher=s2)
    assert s["have"] == 0 and tc.read_index()["items"]["d.com"]["status"] == "too_small"
    assert not (tc.tc_dir() / "d.com.png").exists()


def test_incremental_ok_not_refetched_and_old_png_kept_on_failure(sandbox):
    dom = [{"domain": "e.com", "names": ["戊"], "en": ""}]
    tc.run(domains=dom, today=TODAY, site_fetcher=_ok(), wiki_fetcher=lambda *a: {}, s2_fetcher=lambda *a: {"status": "none"})
    calls = []
    boom = lambda *a, **k: calls.append(1) or {"status": "error"}
    s = tc.run(domains=dom, today=date(2026, 11, 20), site_fetcher=boom, wiki_fetcher=lambda *a: {})
    assert calls == [] and s["attempted"] == 0 and s["done"]            # 90 天內不重抓
    before = (tc.tc_dir() / "e.com.png").read_bytes()
    s = tc.run(domains=dom, today=date(2027, 2, 1), site_fetcher=_fail("error", "連線失敗"), wiki_fetcher=lambda *a: {},
               s2_fetcher=lambda *a: {"status": "none"})
    rec = tc.read_index()["items"]["e.com"]
    assert rec["status"] == "ok" and rec["last_fail"] == "error" and (tc.tc_dir() / "e.com.png").read_bytes() == before


def test_never_raises_and_disabled(sandbox, monkeypatch):
    def bad(*a, **k):
        raise RuntimeError("壞了")
    s = tc.run(domains=[{"domain": "f.com", "names": [], "en": ""}], today=TODAY, site_fetcher=bad,
               wiki_fetcher=lambda *a: {}, s2_fetcher=lambda *a: {"status": "none"})
    assert s["have"] == 0
    monkeypatch.setattr(config, "LOGOS_ENABLED", False)
    assert tc.run(today=TODAY)["skipped"] == "disabled"


def test_export_tc_logos_json_format(sandbox):
    dom = [{"domain": "asml.com", "names": ["ASML"], "en": ""}]
    tc.run(domains=dom, today=TODAY, site_fetcher=_ok(), wiki_fetcher=lambda *a: {}, s2_fetcher=lambda *a: {"status": "none"})
    m = build_payload.export_tc_logos()
    assert m == {"asml.com": "data/tc_logos/asml.com.png"}
    assert json.loads((config.SITE_DATA / "tc_logos.json").read_text(encoding="utf-8")) == m
    assert (config.SITE_DATA / "tc_logos" / "asml.com.png").exists()


def test_export_tc_logos_empty_when_no_logos(sandbox):
    assert build_payload.export_tc_logos() == {}
    assert json.loads((config.SITE_DATA / "tc_logos.json").read_text(encoding="utf-8")) == {}


# ---- Wikidata 依官網網域比對（掛錯別家 Logo 比沒有更糟）

def _wd_fake(entities, search_ids):
    def fake(url, **kw):
        if "wbsearchentities" in url:
            return 200, json.dumps({"search": [{"id": i} for i in search_ids]}).encode(), "application/json", url
        if "wbgetentities" in url:
            return 200, json.dumps({"entities": entities}).encode(), "application/json", url
        return 404, b"", "", url
    return fake


def _claims(site, logo):
    c = {}
    if site:
        c["P856"] = [{"rank": "normal", "mainsnak": {"datavalue": {"value": site}}}]
    if logo:
        c["P154"] = [{"rank": "normal", "mainsnak": {"datavalue": {"value": logo}}}]
    return {"claims": c}


def test_wikidata_requires_official_website_match(sandbox, monkeypatch):
    ents = {"Q1": _claims("https://www.apple.com/", "Apple_logo.svg"),        # 對得上
            "Q2": _claims("https://fruit.example.org/", "Apple_fruit.svg")}   # 同名但網域不同
    monkeypatch.setattr(http, "get_bytes", _wd_fake(ents, ["Q2", "Q1"]))
    hit = wm.logo_by_website("Apple Inc.", "apple.com")
    assert hit == {"file": "File:Apple_logo.svg", "item": "Q1", "match": "website"}


def test_wikidata_no_match_or_ambiguous_returns_none(sandbox, monkeypatch):
    ents = {"Q1": _claims("https://www.apple.com/", "A.svg"), "Q2": _claims("https://apple.com", "B.svg")}
    monkeypatch.setattr(http, "get_bytes", _wd_fake(ents, ["Q1", "Q2"]))
    assert wm.logo_by_website("Apple", "apple.com") is None               # 兩個不同圖檔 → 不猜
    monkeypatch.setattr(http, "get_bytes", _wd_fake({"Q3": _claims("https://other.com", "C.svg")}, ["Q3"]))
    assert wm.logo_by_website("Apple", "apple.com") is None


def test_wikidata_throttle_stops_quietly(sandbox, monkeypatch):
    monkeypatch.setattr(http, "get_bytes", lambda url, **kw: (429, b"", "", url))
    out = wm.fetch_by_website([{"domain": "apple.com", "en": "Apple"}, {"domain": "amd.com", "en": "AMD"}])
    assert out == {}


# ------------------------------------------------------------------ 品質關卡（DECISIONS #365）

def _banner_png(size=(1200, 674)) -> bytes:
    """假的橫幅照片：整張不透明、很多顏色。"""
    from PIL import Image
    img = Image.new("RGB", size)
    img.putdata([((x * 7) % 256, (x * y) % 256, (y * 5) % 256) for y in range(size[1]) for x in range(size[0])]) if False else None
    px = img.load()
    for y in range(0, size[1], 3):
        for x in range(0, size[0], 3):
            px[x, y] = ((x * 7) % 256, (x + y) % 256, (y * 5) % 256)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _res(png_bytes, src, orig, url="https://x.com/a.png", dom="x.com"):
    png, o = lg.normalize_image(png_bytes, allow_lowres=True)
    return {"status": "ok", "domain": dom, "src": src, "url": url, "png": png, "orig": list(orig or o)}


def test_quality_og_image_never_accepted():
    assert "og-image" in tc.quality(_res(_png(), "site:og-image", (180, 180)))


def test_quality_banner_photo_rejected_even_as_header_img():
    r = _res(_banner_png(), "site:header-img", (1200, 674))
    assert tc.quality(r) is not None          # 整張不透明長方形（NVIDIA／AMD 那種）


def test_quality_header_img_wider_than_3_to_1_rejected():
    r = _res(_png((400, 80)), "site:header-img", (256, 59))
    assert "3:1" in tc.quality(r)
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([20, 20, 380, 180], fill=(200, 30, 30, 255))      # 2:1、透明底、非長方形的標誌：收
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    assert tc.quality(_res(buf.getvalue(), "site:header-img", (400, 200))) is None


def test_quality_bad_url_and_deny_and_tiny_mark():
    assert tc.quality(_res(_png(), "site:header-img", (180, 180), url="https://w.com/share-icons/share-icon.png"))
    assert tc.quality(_res(_png(), "site:manifest", (512, 512), url="https://q.com/etc.clientlibs/clientlib-react/logo512.png"))
    assert "人工排除" in tc.quality(_res(_png(), "site:header-img", (180, 180), dom="carmax.com.tw"), "carmax.com.tw")
    from PIL import Image
    tiny = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    tiny.paste(Image.new("RGBA", (30, 30), (200, 0, 0, 255)), (75, 75))
    buf = io.BytesIO()
    tiny.save(buf, format="PNG")
    assert "一小角" in tc.quality(_res(buf.getvalue(), "site:icon", (180, 180)))


def test_quality_wikimedia_exempt_and_normal_icon_passes():
    assert tc.quality({"src": "wikimedia", "png": b"", "orig": [250, 72]}) is None
    assert tc.quality(_res(_png(), "site:apple-touch-icon", (180, 180))) is None


def test_resolve_rejected_site_image_falls_back_to_wikimedia(sandbox):
    """官網只有 og-image → 不合格 → 換 Wikimedia。"""
    def wiki(rows, reject, deadline):
        return {r["domain"]: {"status": "ok", "domain": r["domain"], "src": "wikimedia", "url": "https://commons/x",
                              "png": lg.normalize_image(_png((250, 250)))[0], "orig": [250, 250]} for r in rows}
    out = tc.resolve([{"domain": "nv.com", "names": ["N"], "en": "Nv"}], frozenset(), 9e18,
                     site_fetcher=_ok(src="site:og-image"), wiki_fetcher=wiki, s2_fetcher=lambda d, r: {"status": "none"})
    assert out["nv.com"]["status"] == "ok" and out["nv.com"]["src"] == "wikimedia"
    assert "og-image" in out["nv.com"]["tried"]["quality"]


def test_resolve_wiki_first_domain_skips_site(sandbox):
    calls = []
    def site(website, host, reject=None, names=None):
        calls.append(host)
        return {"status": "none", "domain": host}
    def wiki(rows, reject, deadline):
        return {r["domain"]: {"status": "ok", "domain": r["domain"], "src": "wikimedia", "url": "u",
                              "png": lg.normalize_image(_png((250, 250)))[0], "orig": [250, 250]} for r in rows}
    out = tc.resolve([{"domain": "nvidia.com", "names": [], "en": "NVIDIA"}], frozenset(), 9e18,
                     site_fetcher=site, wiki_fetcher=wiki, s2_fetcher=lambda d, r: {"status": "none"})
    assert out["nvidia.com"]["src"] == "wikimedia" and calls == []


def test_resolve_s2_deny_and_all_fail_gives_not_logo(sandbox):
    s2_called = []
    def s2(dom, reject):
        s2_called.append(dom)
        return {"status": "ok", "domain": dom, "src": "google_s2", "url": "u", "png": lg.normalize_image(_png())[0], "orig": [128, 128]}
    out = tc.resolve([{"domain": "uicpaymentsinc.com", "names": [], "en": ""}], frozenset(), 9e18,
                     site_fetcher=_ok(src="site:og-image"), wiki_fetcher=lambda *a, **k: {}, s2_fetcher=s2)
    assert s2_called == [] and out["uicpaymentsinc.com"]["status"] == "not_logo"


def test_revalidate_marks_old_bad_and_run_removes_unrecoverable(sandbox):
    d = tc.tc_dir()
    d.mkdir(parents=True)
    (d / "nvidia.com.png").write_bytes(lg.normalize_image(_png())[0])
    (d / "good.com.png").write_bytes(lg.normalize_image(_png())[0])
    tc.write_index({"items": {
        "nvidia.com": {"status": "ok", "src": "site:og-image", "url": "https://n/og-image.jpg", "orig": [1200, 674], "fetched": "2026-10-20"},
        "good.com": {"status": "ok", "src": "site:icon", "url": "https://g/i.png", "orig": [180, 180], "fetched": "2026-10-20"}}})
    doms = [{"domain": "nvidia.com", "names": ["NVIDIA"], "en": "NVIDIA"}, {"domain": "good.com", "names": ["G"], "en": ""}]
    s = tc.run(today=TODAY, domains=doms, site_fetcher=_fail(), wiki_fetcher=lambda r, rj, dl: {}, s2_fetcher=lambda d, r: {"status": "none"})
    idx = tc.read_index()["items"]
    assert idx["nvidia.com"]["status"] != "ok" and not (d / "nvidia.com.png").exists()     # 錯圖不留
    assert idx["good.com"]["status"] == "ok" and (d / "good.com.png").exists()             # 好圖不動
    assert "nvidia.com" not in tc.usable()


def test_new_ok_record_is_stamped_with_quality_version(sandbox):
    tc.run(today=TODAY, domains=[{"domain": "a.com", "names": ["A"], "en": ""}], site_fetcher=_ok(),
           wiki_fetcher=lambda r, rj, dl: {}, s2_fetcher=lambda d, r: {"status": "none"})
    assert tc.read_index()["items"]["a.com"]["qv"] == tc.QV


def test_code_supplement_merged_into_domain_list():
    ds = {d["domain"]: d for d in tc.load_domains()}
    assert ds["umc.com"]["supp"] and ds["umc.com"]["en"]          # 2303 聯電（16px）
    sup = json.loads(tc.CODE_DOMAINS_FILE.read_text(encoding="utf-8"))["codes"]
    assert {"2303", "3017", "2385"} <= {r["code"] for r in sup}
    assert all(r["domain"] in ds for r in sup)


def test_shared_hash_default_icon_is_marked_bad_and_rejected(sandbox):
    d = tc.tc_dir()
    d.mkdir(parents=True)
    same = lg.normalize_image(_png())[0]
    other = lg.normalize_image(_png(fg=(10, 120, 200, 255)))[0]
    for k, b in (("a.com", same), ("b.com", same), ("c.com", other)):
        (d / f"{k}.png").write_bytes(b)
    it = {k: {"status": "ok", "src": "site:conventional", "url": "u", "orig": [64, 64], "qv": 2, "sha1": lg.sha1(b), "fetched": "2026-10-20"}
          for k, b in (("a.com", same), ("b.com", same), ("c.com", other))}
    doms = [{"domain": k, "names": [k], "en": ""} for k in it]
    assert tc.shared_hashes(it) == {lg.sha1(same)}
    assert set(tc.revalidate(it, doms)) == {"a.com", "b.com"}


def test_min_px_is_48(sandbox):
    assert config.TC_LOGO_MIN_PX == 48
    assert tc.big_enough({"status": "ok", "png": b"x", "orig": [48, 48]})
    assert not tc.big_enough({"status": "ok", "png": b"x", "orig": [32, 32]})
