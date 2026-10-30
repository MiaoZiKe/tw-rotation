"""新聞貼文自動排程（scripts/social_news.py、news_legal.py、news_insights.py）的單元測試：不連外、不渲染。"""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import news_insights as NI  # noqa: E402
import news_legal as L  # noqa: E402
import social_news as S  # noqa: E402

TPE = timezone(timedelta(hours=8))


def test_legal_sanitize_and_block():
    assert L.sanitize("台股大漲939點、外資狂賣") == "台股上漲939點、外資賣超"
    ok = "台股上漲 939 點。\n以上為公開資料整理，非投資建議"
    assert L.check(ok) == []
    assert any("買賣建議" in x for x in L.check("建議逢低買進。以上為公開資料整理，非投資建議"))
    assert any("傳聞" in x for x in L.check("市場傳出搶單。以上為公開資料整理，非投資建議"))
    assert any("缺法遵句" in x for x in L.check("台股上漲"))
    assert L.is_promo("留言應援抽好禮")


def test_numbers_of_keeps_full_units():
    xs = S.numbers_of("博通籌資逾600億美元，第3季營收10.77億元，季增3%，毛利率51.5%")
    got = {x["label"]: (x["value"], x["unit"]) for x in xs}
    assert got["博通籌資"] == ("逾600", "億美元")
    assert got["第3季營收"] == ("10.77", "億元")
    assert got["毛利率"] == ("51.5", "%")
    assert any(k.endswith("季增") for k in got)


def test_lines_do_not_split_numbers():
    ls = S._lines("台股 上漲939.35點收47,035.58點 台積電收2,425元", 14)
    assert len(ls) <= 2 and all(len(x) <= 14 for x in ls)
    assert not any(x.endswith("2,4") for x in ls)


def test_pack_threads_limit_and_numbering():
    secs = ["甲" * 300, "乙" * 300, "丙" * 100]
    out = S.pack_threads(secs)
    assert len(out) >= 2 and out[-1].endswith(f"({len(out)}/{len(out)})")
    assert all(S._tlen(x) <= 480 for x in out)


def test_pick_reserves_exploration():
    base = datetime(2026, 10, 28, 9, tzinfo=TPE)
    cands = [dict(cat=c, ctype="公司動態", heat=10 - i) for i, c in enumerate(["財報", "財報", "財報", "台股", "台股", "科技", "美股", "總經"])]
    got = S.pick(cands, 5, random.Random(1), 0.2)
    assert len(got) == 5
    assert sum(c["explore"] for c in got) == 1
    assert sum(c["cat"] == "財報" for c in got if not c["explore"]) <= 2


def test_publish_base_plus_15_and_floor():
    now = datetime(2026, 10, 29, 8, 30, tzinfo=TPE)
    posted = {"premarket-2026-10-29": {"at": "2026-10-29T08:21:00+08:00"}}
    assert S.publish_base("pre", "2026-10-29", posted, now).strftime("%H:%M") == "08:36"
    assert S.publish_base("intra", "2026-10-29", posted, now) is None


def test_weights_shrink_and_clip():
    agg = {"topic_category": {"財報": dict(n=10, views=1000, interactions=80, eng_rate=0.08),
                              "總經": dict(n=10, views=1000, interactions=20, eng_rate=0.02),
                              "科技": dict(n=2, views=100, interactions=50, eng_rate=0.5)}}
    w = NI.weights(agg)
    assert w["explore"] == 0.2
    assert w["topic_category"]["財報"] > 1 > w["topic_category"]["總經"]
    assert w["topic_category"]["科技"] == 1.0           # 樣本 < 3 不調
    assert all(0.6 <= v <= 1.6 for v in w["topic_category"].values())


def test_v2_gate_rejects_long_title_and_empty_phrases():
    key = dict(value="4.31", unit="元")
    d = dict(card=dict(cover_title=["是方第3季財報", "EPS 4.31元"], hero="4.31元"),
             caption_ig="甲" * 520 + "以上為公開資料整理，非投資建議", caption_threads=["x"])
    assert S.quality_gate(d, key) == []
    d2 = dict(card=dict(cover_title=["Space為何要跟特斯拉合併", "EPS 4.31元"], hero="6.8元"),
              caption_ig="指數點數反映整體市值。共有2家媒體5則報導 #stock/2330 以上為公開資料整理，非投資建議", caption_threads=["x"])
    bad = "；".join(S.quality_gate(d2, key))
    for w in ("標題行長度", "封面大數字", "內文", "空泛句", "個股頁"):
        assert w in bad


def test_queue_default_draft(monkeypatch):
    import importlib
    monkeypatch.delenv("NEWS_AUTO_APPROVE", raising=False)
    assert importlib.reload(S).STATUS == "draft"
    monkeypatch.setenv("NEWS_AUTO_APPROVE", "1")
    assert importlib.reload(S).STATUS == "approved"
    monkeypatch.delenv("NEWS_AUTO_APPROVE")
    importlib.reload(S)


# ---------------- 主題文章每日自動（2026-10-29）：名額、週末、常備文庫 ----------------
def test_evergreen_library_all_pass_gates():
    lib = S.load_evergreen()
    assert len(lib) >= 8, "常備文庫至少 8 篇，才夠週末與備案輪替"
    ids = [e["id"] for e in lib]
    assert len(ids) == len(set(ids))
    for e in lib:
        d = S.compose_evergreen(e, "wk1", 1, "2026-10-31")     # 法遵、長度、落點閘不過會丟 Skip
        assert d["meta"]["has_ai_image"] == "false" and d["card"]["photo_cats"]       # 10-29：常備文庫也要有實景封面
        assert "#stock/" not in d["caption_ig"]
        assert "ig-newswk11-20261031" in d["caption_ig"]
        assert len(d["card"]["numbers"]) == 3
        assert all(len(x) <= S.TITLE_MAX + 2 for x in e["cover_title"])


def test_pick_evergreen_rotates_and_respects_cooldown(monkeypatch):
    lib = S.load_evergreen()
    monkeypatch.setattr(S, "evg_usage", lambda: {lib[0]["id"]: ["2026-10-25"]})
    got = S.pick_evergreen("2026-10-31", len(lib), set(), random.Random(1))
    assert got[-1]["id"] == lib[0]["id"]                      # 30 天內用過的排最後
    assert lib[1]["id"] not in {e["id"] for e in S.pick_evergreen("2026-10-31", 3, {lib[1]["id"]}, random.Random(1))}


def test_daily_quota_and_auto_slots(tmp_path, monkeypatch):
    assert S.SLOTS["pre"]["n"] + S.SLOTS["intra"]["n"] + S.SLOTS["post"]["n"] == 3       # 交易日主題文章 3 篇（10-29 盤中加 1 篇）
    assert S.SLOTS["post"]["floor"] >= 1 and S.SLOTS["wk1"]["floor"] >= 1 and S.SLOTS["wk2"]["floor"] >= 1
    monkeypatch.setattr(S, "IG_Q", tmp_path)
    at = lambda h: datetime.fromisoformat(f"2026-10-31T{h}+08:00")
    assert S.auto_slots("2026-10-31", at("09:00"), {}) == []                              # 週六 10:00 前不排
    assert S.auto_slots("2026-10-31", at("10:15"), {}) == ["wk1"]
    assert S.auto_slots("2026-10-31", at("19:00"), {}) == ["wk1", "wk2"]
    assert S.auto_slots("2026-11-01", at("10:15"), {}) == ["wk1"]                         # 週日
    posted = {"premarket-2026-10-29": {"at": "2026-10-29T08:20+08:00"}, "close-2026-10-29": {"at": "2026-10-29T17:20+08:00"}}
    now = datetime.fromisoformat("2026-10-29T17:40+08:00")
    assert S.auto_slots("2026-10-29", now, posted) == ["pre", "post"]                     # 交易日（盤中名額 0 不排）
    assert S.auto_slots("2026-10-29", datetime.fromisoformat("2026-10-29T21:05+08:00"), {}) == ["fb"]   # 主貼文都沒發 → 備案
    (tmp_path / "2026-10-29_news-post-1.md").write_text("x")
    assert "fb" not in S.auto_slots("2026-10-29", datetime.fromisoformat("2026-10-29T21:05+08:00"), posted)


def test_topic_status_switch_is_separate():
    # 週末／常備文庫用 TOPIC_AUTO_APPROVE，交易日新聞稿用 NEWS_AUTO_APPROVE
    assert S.TOPIC_STATUS in ("draft", "approved")


# ---------------- 主體辨識與數字標籤（2026-10-29 盤前 9 則全被判「找不到主體」後補） ----------------
NAMES = {"4966": "譜瑞", "2330": "台積電", "6669": "緯穎"}


def _subj(title, summary=""):
    return S.subject_of({"lead": {"title": title, "summary": summary}}, NAMES)


def test_subject_of_bracket_bank_foreign_emerging_commodity():
    assert _subj("〈譜瑞法說〉Q3每股賺7.69元 Q4營收估季減約2成毛利率可望回升") == ("譜瑞", "4966")
    assert _subj("泰國央行維持利率不變並調高經濟成長預測") == ("泰國央行", "")
    assert _subj("〈財報〉Q3營收暴增近1800%！摩爾線程搭上中國AI硬體需求潮")[0] == "摩爾線程"
    assert _subj("昆桐明日以每股參考價390元登興櫃 衛星與AI散熱雙引擎迎接高成長期")[0] == "昆桐"
    assert _subj("沙烏地能源樞紐遇襲 歐洲天然氣價格飆升至2022年以來新高")[0] == "歐洲天然氣"
    assert _subj("Anthropic IPO招股書15大關鍵！上半年淨虧807億美元")[0] == "Anthropic"
    assert _subj("伊朗戰爭推升油輪運價 沙烏地航運巨頭Q3獲利衝上10倍", "Bahri第3季淨利51億")[0] == "Bahri"
    assert _subj("歐洲央行按兵不動")[0] == "歐洲央行"
    assert _subj("〈財報〉本季營收創高") == ("", "")          # 只有「財報」標頭、沒有名字 → 仍找不到


def test_names_map_strips_ky_suffix(monkeypatch):
    import pandas as pd
    monkeypatch.setattr(pd, "read_parquet", lambda f: pd.DataFrame({"code": ["4966", "8436"], "name": ["譜瑞-KY", "大江*"]}))
    monkeypatch.setattr(S, "ROOT", Path(__file__).resolve().parent.parent)
    n = S.names_map()
    assert n.get("4966") == "譜瑞" and n.get("8436") == "大江"


def test_numbers_of_period_only_label_inherits_metric():
    xs = S.numbers_of("央行上修今年GDP成長率至2.4%、2027年2.1%；核心通膨估今年1.2%、明年1.3%")
    labs = [x["label"] for x in xs]
    assert "2027年GDP成長率" in labs and "今年核心通膨" in labs and "明年核心通膨" in labs
    assert not any(l.startswith("〈") for l in (x["label"] for x in S.numbers_of("〈財報〉Q3營收年增1,774%")))


def test_min_body_not_below_400():
    assert 400 <= S.MIN_BODY <= 500


# ---------------- 第二輪（2026-10-29）：「成」單位、商品報價、標題期間＋事件、之前的報導主體、接下來觀察 ----------------
def _cand(title, summary, codes="", ts="2026-10-28T18:00:00+08:00", source="cnyes"):
    n = dict(title=title, summary=summary, codes=codes, source=source, category="", news_id="x1", url="",
             ts=datetime.fromisoformat(ts))
    return S.score([n], {})


def _no_lake(monkeypatch, macro=None):
    monkeypatch.setattr(S, "_HIST", [])
    monkeypatch.setattr(S, "_macro_dates", lambda day: dict(macro or {"nfp": "2026-11-06", "cpi": "2026-11-10",
                                                                       "pce": "2026-10-29", "fomc": "2026-12-09"}))


def test_numbers_of_cheng_unit_range_and_spaced_eps():
    got = {x["label"]: x for x in S.numbers_of("Q4營收估季減約2成，全年營收有望年增五成，估營收季增1-3%，第3季EPS 4.55元，營收成長3成長")}
    assert got["Q4營收估季減"]["value"] == "約20" and got["Q4營收估季減"]["unit"] == "%" and got["Q4營收估季減"]["orig"] == "約2成"
    assert any(x["value"] == "50" and x["unit"] == "%" for x in got.values())          # 中文「五成」也認得
    assert got["估營收季增"]["value"] == "1～3" and got["估營收季增"].get("range")       # 不再讀成「-3%」
    assert got["第3季EPS"]["value"] == "4.55"                                             # 「EPS 4.55元」中間有空白也抓得到
    assert not any(x["unit"] == "成" for x in got.values())


def test_numbers_of_commodity_units():
    xs = {x["label"]: x for x in S.numbers_of("荷蘭 TTF 近月期貨漲1.2%至97.35歐元/MWh，英國 NBP 漲1.5%至241便士/therm，布蘭特原油每桶85.2美元")}
    assert xs["荷蘭 TTF 近月期貨"]["unit"] == "歐元/MWh" and xs["荷蘭 TTF 近月期貨"]["value"] == "97.35"
    assert xs["荷蘭 TTF 近月期貨漲"]["value"] == "1.2"                                  # 漲幅保留「漲」，不會變成「期貨 1.2%」
    assert xs["英國 NBP"]["unit"] == "便士/therm"
    assert xs["布蘭特原油"]["unit"] == "美元/桶"


def test_compose_commodity_price_passes(monkeypatch):
    _no_lake(monkeypatch)
    c = _cand("沙烏地能源樞紐遇襲 歐洲天然氣價格飆升至2022年以來新高",
              "胡塞組織以彈道飛彈與無人機襲擊沙烏地能源設施，歐洲批發天然氣價格周三漲至 2022 年以來新高。，"
              "荷蘭 TTF 近月期貨漲1.2%至97.35歐元/MWh，英國 NBP 漲1.5%至241便士/therm，連6日走高。，"
              "LNG航線受阻、歐盟地下儲氣僅74.6%，11月初歐洲將降溫，市場供應壓力加劇。")
    d = S.compose(c, "pre", 1, "2026-10-29", "口袋長文", NAMES)
    assert d["card"]["cover_title"] == ["歐洲天然氣價格", "97.35歐元/MWh"]
    assert "1,000 度電" in d["caption_ig"]                                              # 單位白話
    w = d["caption_ig"].split("接下來觀察")[1]
    assert "PCE" in w and "能源價格" in w and "非農" not in w                           # 寫清楚為什麼相關


def test_compose_cheng_unlocks_compare_section(monkeypatch):
    _no_lake(monkeypatch)
    c = _cand("〈譜瑞法說〉Q3每股賺7.69元 Q4營收估季減約2成毛利率可望回升",
              "譜瑞-KY第三季營收41.9億元、稅後純益5.9億元，EPS 7.69元，受PC供應鏈提前拉貨後庫存調節影響，年季雙減。，"
              "第四季營收季減約2成；毛利率可望回升至41%至45%，獲利結構自谷底改善。", codes="4966")
    d = S.compose(c, "post", 1, "2026-10-28", "口袋長文", NAMES)
    assert d["card"]["cover_title"] == ["譜瑞第3季財報", "EPS 7.69元"]
    cmp_ = d["caption_ig"].split("和前期比")[1].split("🔎")[0]
    assert "約20%" in cmp_ and "約2成" in cmp_


def test_title_period_event_match_key_number():
    key = dict(label="Google第2季雲端營收", metric="營收", value="250", unit="億美元")
    p, ev, seg = S.title_parts(key, "不只賣自家雲端！Google找上甲骨文 搶輝達AI晶片生意",
                               "Google調整雲端策略，透過甲骨文等外部夥伴擴大TPU銷售", "2026-10-29")
    assert (p, ev, seg) == ("第2季", "", "雲端")                                         # 不是「第2季財報」，帶出「雲端」
    key = dict(label="Q4毛利率持續站穩", metric="毛利率", value="30", unit="%")
    assert S.title_parts(key, "穩懋Q3 EPS 4.55元 Q4毛利率持續站穩30%", "", "2026-10-28")[:2] == ("第4季", "展望")
    key = dict(label="第3季稅後純益", metric="淨利", value="8,829", unit="萬元")
    assert S.title_parts(key, "昶昕財報／第3季稅後純益8,829萬元", "", "2026-10-28")[:2] == ("第3季", "財報")


def test_compose_google_title_not_earnings(monkeypatch):
    _no_lake(monkeypatch)
    c = _cand("不只賣自家雲端！Google找上甲骨文 搶輝達AI晶片生意",
              "Google調整雲端策略，透過甲骨文等外部夥伴擴大TPU銷售，挑戰輝達主導的AI晶片市場。，"
              "Google第2季雲端營收250億美元，第三季營收估年增約90%；TPU合約收入大多將於2027年認列。，"
              "TPU對外銷售料稀釋獲利率至約20%，但可降成本；Anthropic、OpenAI等也成TPU客戶。")
    d = S.compose(c, "pre", 1, "2026-10-29", "口袋長文", NAMES)
    t = "".join(d["card"]["cover_title"])
    assert "財報" not in t and "雲端" in t and "250億美元" in t


def test_history_clause_needs_subject():
    names = {"2330": "台積電", "4966": "譜瑞"}
    assert S.hist_clause("年增24.2％", "譜瑞", names) == ""                              # 看不出是誰 → 丟掉
    assert S.hist_clause("營收年增20%", "譜瑞", names) == "譜瑞營收年增20%"               # 財報指標開頭 → 補主體
    assert S.hist_clause("台積電營收年增30%", "譜瑞", names) == ""                         # 講的是別家
    assert S.hist_clause("Alphabet第3季營收年增15%", "Google", names).startswith("Alphabet")   # 別名也算有主體


def test_next_corp_event_from_news(monkeypatch):
    mk = lambda t, ts: dict(title=t, summary="", source="cnyes", ts=datetime.fromisoformat(ts))
    monkeypatch.setattr(S, "_HIST", [
        mk("本周SK海力士與谷歌、微軟等科技財報登場", "2026-10-27T09:00:00+08:00"),
        mk("閃迪周四將公布財報", "2026-10-28T09:00:00+08:00"),
        mk("台達電今天公布第3季財報", "2026-10-28T14:00:00+08:00"),
    ])
    before = datetime.fromisoformat("2026-10-28T21:00:00+08:00")
    assert "10/26～11/1 這一週公布財報" in S.next_corp_event("Google", "2026-10-29", before)
    assert "10/29 公布財報" in S.next_corp_event("閃迪", "2026-10-29", before)
    assert S.next_corp_event("台達電", "2026-10-28", before) == ""                        # 講的就是這則報導本身


def test_us_company_watch_prefers_earnings_then_related_macro(monkeypatch):
    _no_lake(monkeypatch)
    before = datetime.fromisoformat("2026-10-28T21:00:00+08:00")
    w = S.watch_point("2026-10-29", False, "財報數字", "Google", "Google 雲端 TPU", "", before)
    assert "CPI" in w and "利率" in w and "非農" not in w
    w = S.watch_point("2026-10-29", False, "總經數據", "泰國央行", "泰國央行維持利率不變", "", before)
    assert "FOMC" in w and "聯準會" in w
    monkeypatch.setattr(S, "_HIST", [dict(title="Alphabet將於10月29日公布財報", summary="", source="udn",
                                          ts=datetime.fromisoformat("2026-10-27T09:00:00+08:00"))])
    w = S.watch_point("2026-10-29", False, "財報數字", "Google", "Google 雲端", "", before)
    assert w.startswith("Google預計 10/29 公布財報")


def test_sanitize_fly_growth_vs_level():
    assert L.sanitize("AI 光通訊營收飆 44%") == "AI 光通訊營收成長 44%"
    assert L.sanitize("債券殖利率飆15%") == "債券殖利率升至15%"
    assert "升至至" not in L.sanitize("殖利率飆至15%")



# ---------------- 2026-10-29 Andy：「封面沒圖片需要添加」→ 每一篇主題文章封面都要有實景照片 ----------------
def _R():
    # 2026-10-29 事故：render_news_cards 會載入 Playwright；每日盤後管線（daily.yml）只裝 requirements.txt、沒有 Playwright，
    # 這三個測試因 ModuleNotFoundError 紅 → 「跑指標庫測試」失敗 → price／full 輪整段沒抓資料（價量、法人、指數全停在 10-28）。
    # 沒裝 Playwright 的環境就跳過（社群工作流有裝，照樣會驗）。
    import pytest
    pytest.importorskip("playwright")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "docs" / "marketing" / "posts"))
    import render_news_cards as R
    return R


def _cover_photo(d):
    R = _R(); c = d["card"]
    text = " ".join([c.get("title", "")] + list(c.get("cover_title") or []) + [x.get("name", "") for x in d.get("sources", [])])
    prefer = [(x["cat"], x.get("query")) for x in (c.get("photo_cats") or [])]
    return R.photo_pick(c.get("subject"), d["meta"].get("topic_category"), None, "2026-10-29", text=text, prefer=prefer)


def test_every_evergreen_cover_has_reviewed_photo():
    for e in S.load_evergreen():
        d = S.compose_evergreen(e, "pre", 1, "2026-10-29")
        ph = _cover_photo(d)
        assert ph, f"{e['id']} 封面沒有照片"
        assert ph[1].get("reviewed"), f"{e['id']} 用到未審照片"
        assert ph[3].split("/")[1] == e["photo_cats"][0]["cat"], f"{e['id']} 沒用到指定圖池：{ph[3]}"


def test_every_news_cover_has_photo_even_without_company_pool(monkeypatch):
    _no_lake(monkeypatch)
    cases = [("泰國央行維持利率不變並調高經濟成長預測", "泰國央行MPC以6票贊成維持基準利率1%不變，央行上修今年GDP成長率至2.4%、2027年2.1%；核心通膨估今年1.2%、明年1.3%。"),
             ("〈財報〉Q3營收暴增近1800%！摩爾線程搭上中國AI硬體需求潮", "第三季營收年增1,774%至人民幣16億元，獲利4,930萬元，創上市以來最快增速。"),
             ("某小型外商公布第3季財報 營收年增12%", "某小型外商第3季營收12.5億美元，年增12%，毛利率40%。")]
    R = _R()
    for title, summ in cases:
        c = _cand(title, summ)
        try:
            d = S.compose(c, "pre", 1, "2026-10-29", "口袋長文", NAMES)
        except S.Skip:
            subj = S.subject_of(c, NAMES)[0]
            d = dict(card=dict(subject=subj, title=title, cover_title=[subj, ""]), meta=dict(topic_category=c["cat"]), sources=[])
        ph = _cover_photo(d)
        assert ph and ph[1].get("reviewed"), f"{title} 封面沒有照片"
        assert "Federal Reserve" not in (ph[1].get("query") or "") or "泰國" not in title       # 泰國央行不配 Fed 大樓
        assert not (("泰國" in title or "外商" in title) and ph[3].startswith("_category/總經/")), "外國題材不配台北街景"
    assert R.photo_pick("完全不在名單的主體", topic="科技", text="") is not None                  # 最後保底一定有圖


def test_tw_market_cover_uses_taiwan_generic_photo():
    R = _R()
    d = dict(card=dict(subject="台股", title="台股收盤 加權47,035.58點", cover_title=["台股收盤", "加權47,035.58點"], photo_hint="tw_market",
                       photo_text="華邦電、力積電獲加碼，記憶體族群走強", numbers=[], category="台股"), meta=dict(topic_category="台股"), sources=[])
    c = d["card"]
    prefer = R.GENERIC_TW
    ph = R.photo_pick(c["subject"], "台股", None, "2026-10-29", text=c["photo_text"], prefer=prefer)
    assert ph and ph[3].split("/")[1] in ("總經", "金融")          # 不因內文提到記憶體就配記憶體晶片


# ---- 相關公司（10-29 Andy：「可以的話需要附上相關股票 公司做哪塊 簡單補充」「以後文章都是，但是跟這類有關才要」）
def test_related_evergreen_industry_has_section_macro_not():
    lib = {e["id"]: e for e in S.load_evergreen()}
    assert all("related" in e for e in lib.values())                                     # 11 篇都要明確標（空物件＝跟產業無關）
    abf = S.compose_evergreen(lib["abf"], "wk1", 1, "2026-10-31")
    sec = S.REL_RE.search(abf["caption_ig"]).group(0)
    for line in ("・欣興（3037）：IC 載板，做 ABF 載板", "・南電（8046）：IC 載板", "・景碩（3189）：IC 載板"):
        assert line in sec
    assert 3 <= sec.count("\n・") + sec.startswith("・") <= 6
    assert any(S.REL_HEAD in t for t in abf["caption_threads"])                           # Threads 也有
    hbm = S.compose_evergreen(lib["hbm"], "wk1", 1, "2026-10-31")
    assert "台股沒有直接的 HBM 供應商" in hbm["caption_ig"] and "力成（6239）" in hbm["caption_ig"]
    for k in ("fomc", "cpi_pce", "three_inst", "margin", "eps", "monthly_rev"):           # 總經、籌碼、財報名詞：整節省略
        assert S.REL_HEAD not in S.compose_evergreen(lib[k], "wk1", 1, "2026-10-31")["caption_ig"]


def test_related_every_evergreen_legal_and_length():
    for e in S.load_evergreen():
        d = S.compose_evergreen(e, "wk1", 1, "2026-10-31")
        sec = S.REL_RE.search(d["caption_ig"])
        if sec:
            assert L.check(sec.group(0) + "\n以上為公開資料整理，非投資建議") == []
            assert not __import__("re").search(r"推薦|受惠|看好|買進|建議", sec.group(0))
        assert len(d["caption_ig"]) <= 2000 and all(S._tlen(t) <= 480 for t in d["caption_threads"])


def test_related_news_tw_company_lists_same_segment(monkeypatch):
    _no_lake(monkeypatch)
    names = dict(NAMES, **{"3037": "欣興", "8046": "南電", "3189": "景碩"})
    c = _cand("欣興Q3再賺逾百億 前三季稅後賺282億元年增7.99倍EPS 17.85元",
              "欣興第三季稅後純益102億元，季增15%，EPS 6.5元；前三季稅後純益282億元，年增7.99倍，EPS 17.85元。", codes="3037")
    d = S.compose(c, "post", 1, "2026-10-29", "口袋長文", names)
    sec = S.REL_RE.search(d["caption_ig"]).group(0)
    assert "南電（8046）" in sec and "景碩（3189）" in sec and "欣興（3037）" not in sec   # 列同環節「其他」公司
    assert sec in d["caption_ig"].split("👀")[0]                                           # 放在「接下來觀察」之前


def test_related_news_macro_and_market_omitted(monkeypatch):
    _no_lake(monkeypatch)
    c = _cand("泰國央行維持利率不變並調高經濟成長預測",
              "泰國央行MPC以6票贊成維持基準利率1%不變，央行上修今年GDP成長率至2.4%、2027年2.1%；核心通膨估今年1.2%、明年1.3%。")
    assert S.rel_news(c, "泰國央行", "", NAMES) == ""
    c = _cand("沙烏地能源樞紐遇襲 歐洲天然氣價格飆升至2022年以來新高", "荷蘭 TTF 近月期貨漲1.2%至97.35歐元/MWh。")
    assert S.rel_news(c, "歐洲天然氣", "", NAMES) == ""
    d = S.compose(_cand("沙烏地能源樞紐遇襲 歐洲天然氣價格飆升至2022年以來新高",
                        "歐洲批發天然氣價格周三漲至 2022 年以來新高。，荷蘭 TTF 近月期貨漲1.2%至97.35歐元/MWh，英國 NBP 漲1.5%至241便士/therm，連6日走高。"),
                  "pre", 1, "2026-10-29", "口袋長文", NAMES)
    assert S.REL_HEAD not in d["caption_ig"]


def test_related_news_foreign_topic_by_keyword_not_incidental_mention():
    c = _cand("SK海力士Q3營收創新高 HBM出貨年增逾5成", "SK海力士第三季營收創新高，HBM 出貨年增逾5成。")
    sec = S.rel_news(c, "SK海力士", "", NAMES)
    assert "南亞科（2408）" in sec and "力成（6239）" in sec
    c = _cand("不只賣自家雲端！Google找上甲骨文 搶輝達AI晶片生意", "Google 擴大 TPU 銷售。")
    assert S.rel_news(c, "Google", "", NAMES) == ""                                         # 標題順帶提「輝達」不算
    assert S.rel_news(_cand("ABF載板缺貨 味之素漲價三成", "ABF 膜漲價。"), "味之素", "", NAMES).count("IC 載板") == 3


# ---- 主體判斷（10-29：新聞自帶代號清單的第一檔不一定是主體 →「外資大砍友達」被判成台積電，相關公司跟著列錯）
def _subj2(title, codes="", summary="", names=None):
    return S.subject_of({"lead": {"title": title, "summary": summary, "codes": codes}}, names or NAMES2)


NAMES2 = {"2330": "台積電", "2409": "友達", "3037": "欣興", "8069": "元太", "8039": "台虹", "8070": "長華",
          "2344": "華邦電", "6770": "力積電", "2337": "旺宏", "1337": "再生", "7865": "金聯成", "3105": "穩懋",
          "3025": "星通", "6669": "緯穎", "2850": "新產"}


def test_subject_title_beats_tagged_codes():
    assert _subj2("外資大砍友達9.6萬張最凶 倒貨3檔主動式ETF、連12賣調節0050", "2330,2409,0050") == ("友達", "2409")
    assert _subj2("欣興決議處分日本子公司全數股權 推估MEIKO可望接手", "2330,3037") == ("欣興", "3037")
    assert _subj2("台虹財報出爐 前三季稅後純益6.15億元年增79.93% EPS2.33元", "8069,8039,8070") == ("台虹", "8039")


def test_subject_flow_news_uses_traded_stock():
    assert _subj2("外資擴大買超159億元！華邦電、力積電獲加碼 旺宏卻遭砍近3萬張") == ("華邦電", "2344")
    assert _subj2("外資回補298億元 大買00406A 7.2萬張、友達6.9萬張") == ("友達", "2409")
    assert _subj2("外資上週賣超2356億元　大砍晶圓代工股")[0] == "外資"                        # 沒寫個股 → 仍是外資


def test_subject_rejects_common_word_aliases_and_keeps_single_code():
    assert _subj2("銘福集團攜大馬Naza集團合作車輛資源回收及再生 下一步延伸到菲國", "7865")[1] != "1337"   # 「再生」是一般詞
    assert _subj2("衛星通訊｜星艦首度送上V3衛星！每顆PA用量增4至5倍，穩懋(3105)商機看星艦發射節奏", "3105") == ("穩懋", "3105")
    assert _subj2("《價值型投資 最新產業研究報告》緯穎 (6669-TW) Meta與亞馬遜需求延續", "6669") == ("緯穎", "6669")
    assert _subj2("台股殺出雙11「折扣行情」！台積電？聯發科？誰有機會脫穎而出？", "2330,2454")[0] == "台股"


def test_clean_name_strips_star_and_suffix():
    assert S.clean_name("矽力*-KY") == "矽力" and S.clean_name("譜瑞-KY") == "譜瑞" and S.clean_name(" 台積電 ") == "台積電"
    assert _subj2("11+12月大軋空可期、矽力⊕、金像電⊕、國巨、華新科", "3035,6415,2368",
                  names=dict(NAMES2, **{"6415": S.clean_name("矽力*-KY"), "2368": "金像電", "3035": "智原"})) == ("矽力", "6415")
    assert "材料" not in S._alias({"4763": S.clean_name("材料*-KY")})                     # 拿掉星號後變一般詞，列入 GENERIC
