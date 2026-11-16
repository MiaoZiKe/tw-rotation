"""2026-11-04 Andy「要，盤後也改成專業語氣」：自動主貼文（盤後；之後重開的盤前／盤中／融資融券）開頭＝專業吊胃口問句。
fixtures 是 11-03、11-04 盤後正式產出的舊版文案（social-snaps snaps/close-20261103-1734、close-20261104-1708 的 threads_v1）。"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import threads_lint as L  # noqa: E402
import threads_v2 as V  # noqa: E402

FX = ROOT / "tests" / "fixtures" / "threads_auto_1104"
POSTED_1104 = "朋友問：「外資今天在幹嘛？」我說賣超1,499.0億，他問那台積電呢，我只能默默拍拍他…"


def fx(day):
    return json.loads((FX / f"close_{day}.json").read_text(encoding="utf-8"))


def _auto(hook, **kw):
    d = dict(profile="auto", hook_type="問句", emotion="專業", main_post=f"{hook}\n\n🌙 盤後3分鐘\n・加權指數跌 359 點\n#台積電外資賣超",
             thread_posts=[], reply_post=L.DEFAULT_LEGAL, image_count=1, tag="台積電外資賣超")
    d.update(kw)
    return d


def test_auto_lint_rejects_1104_casual_hook():
    e = "；".join(L.lint(_auto(POSTED_1104))[0])
    assert "要 1 句問句" in e and "默默" in e and "拍拍" in e and "朋友" in e


def test_auto_lint_passes_professional_question():
    assert L.lint(_auto("外資連 5 日賣超、累計 5,120 億，這一波和前幾次有什麼不同？"))[0] == []
    assert L.lint(_auto("加權指數跌 359 點，但漲停 49 家、跌停只有 4 家，盤面透露什麼訊號？"))[0] == []


def test_auto_lint_requires_question_type_and_tone():
    e = "；".join(L.lint(_auto("外資連 5 日賣超、累計 5,120 億，這一波和前幾次有什麼不同？", hook_type="對話", emotion="好笑"))[0])
    assert "問句" in e and "專業" in e
    e = "；".join(L.lint(_auto("外資連 5 日賣超、累計 5,120 億，這一波和前幾次有什麼不同？",
                               main_post="外資連 5 日賣超、累計 5,120 億，這一波和前幾次有什麼不同？\n\n・跌停只有 4 家啦\n#台積電外資賣超"))[0])
    assert "主文口語" in e


def test_old_profile_unchanged_for_manual_queue():
    e = L.lint(_auto(POSTED_1104, profile=None))[0]           # 手寫佇列檔（沒有 rule）照舊規則，不被自動模式影響
    assert not any("自動貼文" in x for x in e)


def test_real_1103_1104_professional_and_complete():
    for day in ("20261103", "20261104"):
        th = fx(day)
        d = V.build("close", th["text"], th["reply"], th["images"], today=f"{day[:4]}-{day[4:6]}-{day[6:]}")
        hook, rest = L.hook_of(L.split_tag(d["main_post"])[0])
        assert d["checklist_passed"], L.lint(d)
        assert d["profile"] == "auto" and d["hook_type"] == "問句" and d["emotion"] == "專業"
        assert hook.endswith("？") and not L.casual_words(d["main_post"], hook=False) and not L.casual_words(hook, hook=True)
        assert any(c.isdigit() for c in hook)                  # 用當天數據帶入
        assert L.tlen(d["main_post"]) <= 500 and "http" not in d["main_post"] and d["reply_post"] == L.DEFAULT_LEGAL
        assert "比比" not in d["main_post"] and "盤面分析" in d["thread_posts"][0]    # 11-09 起條列移到串文第一則


def test_andy_examples_are_candidates_on_1104():
    th = fx("20261104")
    f = V.facts("close", th["text"], th["reply"])
    txt = [t for _, t in V.candidates("close", f)]
    assert "外資連 5 日賣超、累計 5,120 億，這一波和前幾次有什麼不同？" in txt
    assert "加權指數跌 359 點，但漲停 49 家、跌停只有 4 家，盤面透露什麼訊號？" in txt
    assert len(txt) >= 10


def test_14_day_no_repeat_on_real_data():
    st = {"history": []}
    used = []
    for i in range(14):
        th = fx("20261103" if i % 2 else "20261104")
        day = (date(2026, 11, 5) + timedelta(days=i)).isoformat()
        d = V.build("close", th["text"], th["reply"], th["images"], state=st, today=day)
        assert d["checklist_passed"], L.lint(d)
        if d["level"] == "全部規則":
            assert d["template"] not in used[-13:]
        V.record(st, d, "close", day)
        used.append(d["template"])
    # 11-09 起盤後先挑「反差」模板（同模板 3 天內不重複）→ 不再要求 14 天 10 種；但不准連兩天同一個模板
    assert len(set(used)) >= 3 and all(a != b for a, b in zip(used, used[1:])), used


# ---- 2026-11-05 CEO 法遵退件：開頭不點名個股、不問時機 ----
def test_auto_lint_rejects_stock_name_and_timing():
    e = "；".join(L.lint(_auto("外資賣超 1,499 億的盤面裡，買超第一名是旺矽，資金為什麼選它？"))[0])
    assert "點名個股「旺矽」" in e
    e = "；".join(L.lint(_auto("外資賣超以台積電最多、達 488.2 億，占當日賣超 33%，權值股比重正在調整嗎？"))[0])
    assert "點名個股「台積電」" in e
    e = "；".join(L.lint(_auto("投信連 17 日買超、累計 3,082 億，和外資方向相反的布局能撐多久？"))[0])
    assert "時機" in e


def test_stock_mask_no_false_positive():
    assert L.stock_in("族群平均 -3.80%，貨櫃航運卻逆勢 +2.9%，它和大盤走勢分開的原因在哪裡？") == []
    assert L.stock_in("加權指數跌 359 點、幅度 0.83%，今天盤後最值得留意的是哪一個數字？") == []


def test_no_template_names_a_stock_or_timing_on_real_data():
    for day in ("20261103", "20261104"):
        th = fx(day)
        f = V.facts("close", th["text"], th["reply"])
        for h, t in V.candidates("close", f):
            assert not L.stock_in(t) and not any(w in t for w in L.AUTO_TIMING), (h[0], t)
    for h in V.HOOKS:
        assert "{fbuy1}" not in h[4] and "{fsell1}" not in h[4] and "{fx_top}" not in h[4] and "{adr}" not in h[4], h[0]


def test_casual_news_line_dropped_from_body():
    th = fx("20261104")
    d = V.build("close", th["text"], th["reply"] + "\n・投資人傻眼：台股又跌了啦", th["images"], today="2026-11-05")
    assert "傻眼" not in d["main_post"] and d["checklist_passed"], L.lint(d)


def test_fallback_still_professional():
    d = V.build("close", "", "", [], today="2026-11-05")
    hook = L.hook_of(L.split_tag(d["main_post"])[0])[0]
    assert hook.endswith("？") and d["hook_type"] == "問句" and d["main_post"]
