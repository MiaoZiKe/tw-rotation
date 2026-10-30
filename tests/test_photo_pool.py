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
    # 2026-10-29 Andy：「封面沒圖片需要添加」→ 不在名單也不再回 None，最後退到總類通用圖池（這個測試庫只有半導體池）
    assert R.photo_pick("不在名單")[2:] == ("D-實景(通用)", "_category/半導體/photo_1.jpg")
    assert R.photo_pick("不在名單", topic="總經")[2] == "D-實景(通用)"


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


def test_central_bank_pool_matches_bank(R):
    """央行圖池是 Fed／ECB／日銀的建築：只配給講那一家的新聞；其他國家央行不配圖（10-29 泰國央行配到 Fed 大樓）。"""
    d = R.PHOTO_LIB / "_category" / "總經_央行"; d.mkdir(parents=True)
    ph = [dict(file="photo_1.jpg", kind="類別", reviewed=True, query="Federal Reserve Building"),
          dict(file="photo_5.jpg", kind="類別", reviewed=True, query="European Central Bank Frankfurt")]
    for m in ph:
        (d / m["file"]).write_bytes(b"x")
    (d / "pool.json").write_text(json.dumps(dict(photos=ph)), encoding="utf-8")
    assert R.photo_pick("歐洲央行", topic="總經", text="歐洲央行維持利率")[3] == "_category/總經_央行/photo_5.jpg"
    assert R.photo_pick("聯準會", topic="總經", text="聯準會降息")[3] == "_category/總經_央行/photo_1.jpg"
    r = R.photo_pick("泰國央行", topic="總經", text="泰國央行維持利率不變")
    assert r is None or not r[3].startswith("_category/總經_央行/")        # 不配 Fed／ECB 大樓（10-29 起改退通用圖池，這個測試庫沒有通用池 → None）
    assert "總經_匯率" not in R.topic_cats("摩爾線程 淨利4,930萬人民幣", "財報")      # 非總經新聞的幣別不配鈔票圖


# ---- 2026-10-30 Andy：「相這種跟公司有關的 優先附上公司圖片」（緊急加發「Alphabet 跌 12.6%」配到 Intel 處理器照片）----
@pytest.fixture
def RC(tmp_path, monkeypatch):
    R = pytest.importorskip("render_news_cards")
    lib = tmp_path / "lib"
    def pool(d, photos):
        d.mkdir(parents=True)
        for m in photos:
            (d / m["file"]).write_bytes(b"x")
        (d / "pool.json").write_text(json.dumps(dict(photos=photos)), encoding="utf-8")
    pool(lib / "alphabet", [dict(file="photo_1.jpg", kind="相關場景", reviewed=True),
                            dict(file="photo_2.jpg", kind="總部/廠房", reviewed=True)])
    pool(lib / "intel", [dict(file="photo_1.jpg", kind="產品", reviewed=True)])
    pool(lib / "tsmc", [dict(file="photo_1.jpg", kind="總部/廠房", reviewed=True)])
    pool(lib / "sk_hynix", [dict(file="photo_1.jpg", kind="產品", reviewed=False)])
    for cat in ("半導體", "記憶體", "總經_景氣", "金融", "總經"):
        pool(lib / "_category" / cat, [dict(file="photo_1.jpg", kind="類別", reviewed=True)])
    (lib / "aliases.json").write_text(json.dumps({"Alphabet": "alphabet", "Google": "alphabet", "Intel": "intel", "英特爾": "intel",
                                                  "台積電": "tsmc", "SK hynix": "sk_hynix", "SK海力士": "sk_hynix"}), encoding="utf-8")
    (lib / "targets.json").write_text(json.dumps([dict(slug="alphabet", category="半導體"), dict(slug="intel", category="半導體"),
                                                  dict(slug="tsmc", category="半導體"), dict(slug="sk_hynix", category="記憶體")]), encoding="utf-8")
    monkeypatch.setattr(R, "PHOTO_LIB", lib)
    return R


def test_alphabet_subject_gets_google_photo_not_intel(RC):
    text = "Alphabet 單日跌 12.6% Intel 盤後再跌近兩成 晶片 半導體"
    for subj in ("Alphabet", "Google", "Google（Alphabet）", "Alphabet Inc."):
        key = RC.photo_pick(subj, topic="美股", text=text, today="2026-10-30")[3]
        assert key.startswith("alphabet/"), (subj, key)
    # 公司自己的總部照排在「相關場景」通用畫面前面
    assert RC.photo_pick("Alphabet", today="2026-10-30")[3] == "alphabet/photo_2.jpg"


def test_company_photo_beats_prefer_and_category(RC):
    # 常備文庫／台股大盤指定的類別圖池不能蓋過主體公司圖
    r = RC.photo_pick("台積電", topic="台股", text="台積電 法說 晶圓", prefer=[("金融", None)], tw=True, today="2026-10-30")
    assert r[3] == "tsmc/photo_1.jpg" and r[2] == "D-實景(公司)"
    assert RC.photo_pick("台積電ADR", topic="美股", today="2026-10-30")[3] == "tsmc/photo_1.jpg"


def test_no_company_photo_falls_back_to_category_not_other_company(RC):
    # SK 海力士圖池沒有已審圖 → 退記憶體類別池；文字裡提到 Intel 也不准拿 Intel 的圖
    key = RC.photo_pick("SK海力士", topic="美股", text="SK海力士 HBM 供貨 Intel", today="2026-10-30")[3]
    assert key == "_category/記憶體/photo_1.jpg"
    assert RC.company_pick("SK海力士") is None
    assert RC.company_slug("Harmony") == "" and RC.company_slug("英特爾") == "intel"


def test_card_auto_uses_subject_company(RC, monkeypatch):
    monkeypatch.setattr(RC, "card_photo", lambda d, i, t, ph, slot, pending=False: str(ph[0]))
    d = dict(card=dict(title="Alphabet 單日跌 12.6%", subject="Alphabet", category="美股", cover_title=["美股科技股收黑", "Alphabet 跌 12.6%"],
                       photo_cats=[dict(cat="半導體")]), meta={})
    html, lay, pick = RC.card_auto(d, 1, 1, today="2026-10-30")
    assert pick["key"].startswith("alphabet/")
