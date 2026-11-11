"""公司 LOGO 模式（2026-11-11）：company_photos.py --source logo → company_logos.py。全部離線，假 session 不連網。"""
import io, json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
L = pytest.importorskip("company_logos")

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100"><circle cx="50" cy="50" r="40" fill="#ff6600"/></svg>'


def _png(w, h, mode="RGBA", color=(0, 120, 255, 255)):
    from PIL import Image
    buf = io.BytesIO(); Image.new(mode, (w, h), color if mode == "RGBA" else color[:3]).save(buf, "PNG"); return buf.getvalue()


def _md(short, code="", cats=""):
    return {"LicenseShortName": {"value": short}, "License": {"value": code}, "Categories": {"value": cats},
            "Artist": {"value": "<a href='x'>MediaTek Inc.</a>"}, "LicenseUrl": {"value": ""}}


class Resp:
    def __init__(self, js=None, content=b""):
        self._js, self.content = js, content
    def raise_for_status(self): pass
    def json(self): return self._js


class Sess:
    """假的 requests.Session：files＝{Commons 檔名: (mime, extmetadata, 內容)}；沒有的回 missing。"""
    def __init__(self, files):
        self.files, self.calls = files, []
    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if params:
            t = params["titles"]
            if t not in self.files:
                return Resp({"query": {"pages": {"-1": {"title": t, "missing": ""}}}})
            mime, md, _ = self.files[t]
            return Resp({"query": {"pages": {"1": {"title": t, "imageinfo": [dict(
                url="https://upload.wikimedia.org/x/" + t[5:], descriptionurl="https://commons.wikimedia.org/wiki/" + t.replace(" ", "_"),
                mime=mime, width=400, height=100, extmetadata=md)]}}}})
        name = "File:" + url.rsplit("/", 1)[1]
        return Resp(content=self.files[name][2])


@pytest.mark.parametrize("short,code,cats,ok", [
    ("Public domain", "pd", "", True),
    ("Public domain", "pd", "PD textlogo|Logos of Taiwan", True),
    ("CC0", "cc0", "", True),
    ("CC BY 4.0", "cc-by-4.0", "", True),
    ("CC BY-SA 3.0", "cc-by-sa-3.0", "", True),
    ("CC BY-NC 4.0", "cc-by-nc-4.0", "", False),
    ("CC BY-ND 4.0", "cc-by-nd-4.0", "", False),
    ("Fair use", "", "", False),
    ("", "", "", False),
    ("GFDL", "gfdl", "", False),
])
def test_license_whitelist(short, code, cats, ok):
    assert L.logo_license(_md(short, code, cats))[0] is ok


def test_pd_textlogo_named():
    assert L.logo_license(_md("Public domain", "pd", "PD textlogo"))[1] == "PD-textlogo"


def _target(slug, logo):
    return dict(slug=slug, name_en=slug, zh=[slug], commons_logo=logo)


def test_svg_to_512_transparent_png(tmp_path):
    pytest.importorskip("cairosvg")
    from PIL import Image
    s = Sess({"File:A logo.svg": ("image/svg+xml", _md("Public domain", "pd", "PD textlogo"), SVG)})
    res = L.run_logos(s, tmp_path, [_target("acme", "File:A logo.svg")])
    assert res[0]["status"] == "ok" and res[0]["license"] == "PD-textlogo"
    im = Image.open(tmp_path / "acme" / "logo.png")
    assert im.height == 512 and im.width == 2048 and im.mode == "RGBA"     # 原比例 4:1
    assert im.getpixel((2000, 10))[3] == 0                                   # 背景透明
    assert im.getpixel((200, 256))[:3] == (255, 102, 0)                      # 原色
    logo = json.loads((tmp_path / "acme" / "pool.json").read_text(encoding="utf-8"))["logo"]
    assert logo["status"] == "ok" and logo["converted_from_svg"] is True
    assert logo["source_url"] == "https://commons.wikimedia.org/wiki/File:A_logo.svg"
    assert logo["author"] == "MediaTek Inc." and logo["license"] == "PD-textlogo"
    log = json.loads((tmp_path / "logo_log.json").read_text(encoding="utf-8"))
    assert log["ok"] == ["acme"]


def test_raster_scaled_keeps_ratio_and_small_not_upscaled(tmp_path):
    from PIL import Image
    s = Sess({"File:Big.png": ("image/png", _md("CC BY 4.0", "cc-by-4.0"), _png(2000, 1000)),
              "File:Small.png": ("image/png", _md("CC0", "cc0"), _png(200, 50))})
    L.run_logos(s, tmp_path, [_target("big", "File:Big.png"), _target("small", "File:Small.png")])
    assert Image.open(tmp_path / "big" / "logo.png").size == (1024, 512)
    assert Image.open(tmp_path / "small" / "logo.png").size == (200, 50)


def test_bad_license_skipped_with_reason_and_no_file(tmp_path):
    s = Sess({"File:NC.png": ("image/png", _md("CC BY-NC-SA 4.0", "cc-by-nc-sa-4.0"), _png(10, 10))})
    res = L.run_logos(s, tmp_path, [_target("nc", "File:NC.png")])
    assert res[0]["status"] == "skipped" and "NC" in res[0]["reason"]
    assert not (tmp_path / "nc" / "logo.png").exists()
    pool = json.loads((tmp_path / "nc" / "pool.json").read_text(encoding="utf-8"))
    assert pool["logo"]["status"] == "skipped" and pool["logo"]["reason"]
    assert not any("upload.wikimedia.org" in c for c in s.calls)            # 授權不合格不下載


def test_missing_empty_and_untargeted(tmp_path):
    s = Sess({})
    ts = [_target("gone", "File:Nope.svg"), _target("blank", ""), dict(slug="photo_only", name_en="x")]
    res = {r["slug"]: r for r in L.run_logos(s, tmp_path, ts)}
    assert res["gone"]["status"] == "missing" and res["blank"]["status"] == "empty"
    assert "photo_only" not in res                                           # 沒有 commons_logo 欄位的公司不跑
    log = json.loads((tmp_path / "logo_log.json").read_text(encoding="utf-8"))
    assert set(log["miss"]) == {"gone", "blank"}


def test_existing_photos_kept_and_same_title_not_refetched(tmp_path):
    d = tmp_path / "acme"; d.mkdir()
    (d / "pool.json").write_text(json.dumps(dict(slug="acme", photos=[dict(file="photo_1.jpg")], rejected=[])), encoding="utf-8")
    s = Sess({"File:A.png": ("image/png", _md("CC0", "cc0"), _png(100, 40))})
    assert L.run_logos(s, tmp_path, [_target("acme", "A.png")])[0]["status"] == "ok"   # 沒寫 File: 也補上
    pool = json.loads((d / "pool.json").read_text(encoding="utf-8"))
    assert pool["photos"] == [dict(file="photo_1.jpg")]                     # 照片池不動
    n = len(s.calls)
    assert L.run_logos(s, tmp_path, [_target("acme", "File:A.png")])[0]["status"] == "kept"
    assert len(s.calls) == n                                                 # 同檔名不再連 Commons


def test_targets_json_logo_fields():
    ts = json.loads((Path(__file__).resolve().parents[1] / "social" / "photo_lib" / "targets.json").read_text(encoding="utf-8"))
    by = {t["slug"]: t for t in ts}
    assert len(by) == len(ts)                                                # slug 不重複
    want = {"mediatek", "asmedia", "tsmc", "realtek", "airoha", "hon_precision", "novatek", "guc", "raydium", "fitipower",
            "aspeed", "igs", "ememory", "pixart", "phison", "genesys_logic"}
    assert want <= set(by)
    for s in want:
        v = by[s]["commons_logo"]
        assert v == "" or v.startswith("File:")


def test_main_logo_mode_dispatch(tmp_path, monkeypatch):
    P = pytest.importorskip("company_photos")
    lib = tmp_path / "lib"; lib.mkdir()
    (lib / "targets.json").write_text(json.dumps([_target("acme", "File:A.png")]), encoding="utf-8")
    monkeypatch.setattr(P, "LIB", lib)
    import requests
    fake = Sess({"File:A.png": ("image/png", _md("CC0", "cc0"), _png(100, 40))})
    monkeypatch.setattr(requests, "Session", lambda: type("S", (), {"headers": {}, "get": fake.get})())
    assert P.main(["--source", "logo"]) == 0
    assert (lib / "acme" / "logo.png").exists() and not (lib / "fetch_log.json").exists()   # 不跑照片流程
