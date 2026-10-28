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
        assert d["meta"]["has_ai_image"] == "false" and d["card"]["no_photo"] is True
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
    assert S.SLOTS["pre"]["n"] + S.SLOTS["intra"]["n"] + S.SLOTS["post"]["n"] == 2       # 交易日主題文章 2 篇
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
