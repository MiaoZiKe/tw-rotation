"""圖池選圖（Andy 2026-10-28 v2）：公司已審圖池（14 天輪替）→ 類別圖池 → 灰框。"""
import json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs" / "marketing" / "posts"))


@pytest.fixture
def R(tmp_path, monkeypatch):
    R = pytest.importorskip("render_news_cards")
    lib = tmp_path / "lib"
    def pool(d, photos):
        d.mkdir(parents=True)
        for m in photos:
            (d / m["file"]).write_bytes(b"x")
        (d / "pool.json").write_text(json.dumps(dict(photos=photos)), encoding="utf-8")
    pool(lib / "acme", [dict(file="photo_1.jpg", kind="總部/廠房", reviewed=True),
                        dict(file="photo_2.jpg", kind="產品", reviewed=True),
                        dict(file="photo_3.jpg", kind="產品", reviewed=False)])
    pool(lib / "nopic", [dict(file="photo_1.jpg", kind="總部/廠房", reviewed=False)])
    pool(lib / "_category" / "半導體", [dict(file="photo_1.jpg", kind="類別", reviewed=True)])
    (lib / "aliases.json").write_text(json.dumps({"艾克": "acme", "無圖": "nopic"}), encoding="utf-8")
    (lib / "targets.json").write_text(json.dumps([dict(slug="acme", category="半導體"), dict(slug="nopic", category="半導體")]), encoding="utf-8")
    monkeypatch.setattr(R, "PHOTO_LIB", lib)
    return R


def test_company_pool_rotates_and_skips_unreviewed(R):
    p, m, lay, key = R.photo_pick("艾克", today="2026-10-28")
    assert key == "acme/photo_1.jpg" and lay == "D-實景(公司)"
    used = {key: ["2026-10-27"]}
    p, m, lay, key = R.photo_pick("艾克", used=used, today="2026-10-28")
    assert key == "acme/photo_2.jpg" and lay == "D-實景(產品)"
    used["acme/photo_2.jpg"] = ["2026-10-28"]           # 兩張都在 14 天內 → 挑最久沒用的
    assert R.photo_pick("艾克", used=used, today="2026-10-28")[3] == "acme/photo_1.jpg"
    used = {"acme/photo_1.jpg": ["2026-10-01"], "acme/photo_2.jpg": ["2026-10-20"]}   # 超過 14 天 → 可再用
    assert R.photo_pick("艾克", used=used, today="2026-10-28")[3] == "acme/photo_1.jpg"


def test_fallback_to_category_then_none(R):
    assert R.photo_pick("無圖")[2:] == ("D-實景(類別)", "_category/半導體/photo_1.jpg")
    assert R.photo_pick("不在名單") is None
    assert R.photo_pick("不在名單", topic="總經") is None      # 總經池沒有圖 → 灰框
