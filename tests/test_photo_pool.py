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


def test_foreign_and_macro_text_fallback(R, tmp_path):
    lib = R.PHOTO_LIB
    for cat in ("總經_央行", "總經", "能源"):
        d = lib / "_category" / cat; d.mkdir(parents=True)
        (d / "photo_1.jpg").write_bytes(b"x")
        (d / "pool.json").write_text(json.dumps(dict(photos=[dict(file="photo_1.jpg", kind="類別", reviewed=True)])), encoding="utf-8")
    # 外商不在名單：依文字對應產業池
    assert R.photo_pick("某外商", topic="美股", text="某外商 HBM 晶片出貨")[3] == "_category/半導體/photo_1.jpg"   # 記憶體池沒圖 → 半導體
    assert R.photo_pick("埃克森", topic="美股", text="油價大漲 煉油")[3] == "_category/能源/photo_1.jpg"
    # 總經：先子類，子類沒圖退總經
    assert R.photo_pick("", topic="總經", text="Fed 宣布降息 1 碼")[3] == "_category/總經_央行/photo_1.jpg"
    assert R.photo_pick("", topic="總經", text="美國 CPI 年增 3%")[3] == "_category/總經/photo_1.jpg"
    assert R.topic_cats("非農新增 25 萬", "總經")[0] == "總經_物價就業"
    assert R.topic_cats("景氣燈號轉紅", "總經")[0] == "總經_景氣"
