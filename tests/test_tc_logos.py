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


def test_sub64_everywhere_is_rejected_not_stored(sandbox):
    dom = [{"domain": "d.com", "names": ["丁"], "en": ""}]
    s2 = lambda d, r: {"status": "ok", "domain": d, "src": "google_s2", "url": "u", "png": _png((48, 48)), "orig": [48, 48]}
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
