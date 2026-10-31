"""Threads v2（2026-11-01 Andy「Threads 發文規則」，docs/marketing/social_unit/threads_rules.md）：
lint、鉤子模板庫與輪替、主貼文改寫不漏數據、發文串接、舊格式自動改寫、數字卡不重疊。fixtures 是 10/30 正式發出的 manifest。"""
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import threads_lint as L  # noqa: E402
import threads_v2 as V  # noqa: E402

FX = ROOT / "tests" / "fixtures" / "threads_v2"


def man(kind):
    return json.loads((FX / f"{kind}.json").read_text(encoding="utf-8"))


GOOD = dict(hook_type="冷知識", emotion="吐槽", main_post="冷知識：今天八十三個族群只有八個是紅的，比我這個月的存款餘額還少見！\n#台股大跌",
            thread_posts=["🔥 熱力圖：\n・漲最多 貨櫃航運 +2.9%、資安防護 +1.8%；\n・跌最多 電源供應器 -8.8%"],
            reply_post="👉 完整圖表都在網站：\nhttps://liguligu-puipui.com/", image_count=2, tag="台股大跌")


# ---------------- lint ----------------
def test_lint_good_passes():
    assert L.lint(GOOD)[0] == []


@pytest.mark.parametrize("patch,needle", [
    (dict(main_post="短短的\n#台股大跌"), "主文"),
    (dict(main_post=GOOD["main_post"].replace("！", "，歡迎留言告訴我！")), "禁用字詞"),
    (dict(main_post="冷知識：今天八十三個族群只有八個是紅的 https://x.com 比存款還少見！\n#台股大跌"), "網址"),
    (dict(main_post="冷知識：今天八十三個族群只有八個是紅的，比我這個月的存款餘額還少見！\n#台股 #大跌"), "標籤"),
    (dict(main_post=GOOD["main_post"].replace("#台股大跌", "#投資"), tag="投資"), "泛用"),
    (dict(image_count=1), "配圖"),
    (dict(hook_type="新聞"), "開頭類型"),
    (dict(emotion="平鋪"), "情緒"),
    (dict(thread_posts=["甲" * 160]), "超過"),
    (dict(thread_posts=["甲" * 100] * 7), "最多 6 則"),
    (dict(thread_posts=["#標籤 " + "甲" * 40]), "標籤"),
    (dict(reply_post="沒有網址的留言"), "網址"),
    (dict(main_post="冷知識：今天八十三個族群只有八個是紅的，比我這個月的存款餘額還少見。\n#台股大跌"), "句號"),
    (dict(main_post="冷知識：今天八十三個族群只有八個是紅的，大家覺得接下來會怎麼樣呢？\n#台股大跌"), "空泛"),
    (dict(thread_posts=["外資今天買進台積電、加碼聯發科，分析師推薦的標的也跟著漲了一大段"]), "禁用字詞"),
])
def test_lint_catches(patch, needle):
    e = L.lint(dict(GOOD, **patch))[0]
    assert any(needle in x for x in e), e


# ---------------- 模板庫 ----------------
def test_template_library_size_and_mix():
    for t in V.HOOKS:
        assert t[2] in L.HOOK_TYPES and t[3] in L.EMOTIONS
    for ty in L.HOOK_TYPES:
        hs = [h for h in V.HOOKS if h[2] == ty]
        assert len(hs) >= 15, ty
        assert {h[3] for h in hs} == {"好笑", "吐槽"}, ty
    assert len({h[0] for h in V.HOOKS}) == len(V.HOOKS)
    for t in V.HOOKS:      # 模板本身不准有禁用字詞、網址、#
        assert not any(w in t[4] for w in L.BANNED) and "#" not in t[4] and "http" not in t[4]


# ---------------- 主貼文改寫 ----------------
@pytest.mark.parametrize("kind", ["intraday", "close", "premarket"])
def test_build_main_post_keeps_all_data(kind):
    m = man(kind)
    th = m["threads"]
    d = V.build(kind, th["text"], th.get("reply", ""), th["images"], today="2026-10-30")
    assert d["checklist_passed"], L.lint(d)
    assert d["image_count"] == 2 and len(d["images"]) == 2 and set(d["images"]) <= set(th["images"])
    assert "http" not in d["main_post"] and d["reply_post"].count("https://") == 1
    joined = "\n".join(d["thread_posts"])
    # 原本每一條數據（・開頭的行）都要在串文裡（喊單字改寫除外）
    for line in (th["text"] + "\n" + th.get("reply", "")).splitlines():
        line = line.strip()
        if line.startswith("・"):
            assert V._rewrite(line) in joined, line
    assert all(clen <= 150 for clen in map(L.clen, d["thread_posts"]))
    assert len(d["thread_posts"]) <= 6            # 2026-11-01 CEO：主文＋≤6 串文＋1 則留言
    assert d["tag"] not in L.GENERIC_TAGS


def test_tag_event_types():
    f = V.facts("close", man("close")["threads"]["text"])
    assert V.pick_tag("close", man("close")["threads"]["text"], f) == "台股大跌"         # 10/30 跌 1,156 點
    assert V.pick_tag("intraday", "Fed 主席鮑爾談話", {}) == "Fed利率決策"
    assert V.pick_tag("intraday", "・聯發科第三季 EPS 達 17.5 元", {}) == "聯發科財報"
    assert V.pick_tag("premarket", "沒有事件", {}) == "台積電ADR"
    assert V.pick_tag("intraday", "什麼都沒有", {}) not in L.GENERIC_TAGS


def test_rotation_type_never_repeats_and_14_day_cooldown():
    st = {"history": []}
    th = man("intraday")["threads"]
    used = []
    for i in range(20):
        day = (date(2026, 11, 2) + timedelta(days=i)).isoformat()
        d = V.build("intraday", th["text"], th["reply"], th["images"], state=st, today=day)
        assert d["checklist_passed"]
        if st["history"]:
            if d["level"] in ("全部規則", "放寬14天"):
                assert d["hook_type"] != st["history"][-1]["type"]
        if d["level"] == "全部規則":
            assert d["template"] not in [u for u in used[-13:]]
        V.record(st, d, "intraday", day)
        used.append(d["template"])
    assert len(set(used)) >= 10          # 20 天至少 10 種開頭，不千篇一律


def test_never_blocks_even_with_empty_text():
    d = V.build("intraday", "", "", [], today="2026-11-02")
    assert d["main_post"] and d["reply_post"] and d["image_count"] == 0


def test_one_image_becomes_zero():
    th = man("intraday")["threads"]
    d = V.build("intraday", th["text"], th["reply"], th["images"][:1], today="2026-11-02")
    assert d["image_count"] == 0


def test_convert_manifest_writes_state(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(man("intraday"), ensure_ascii=False), encoding="utf-8")
    V.convert_manifest(p, None, str(tmp_path / "h.json"))
    m = json.loads(p.read_text(encoding="utf-8"))
    assert m["threads"]["v2"]["checklist_passed"] and m["threads_v1"]["text"].startswith("🕛")
    assert m["threads"]["thread_posts"] and "https://" in m["threads"]["reply_post"]
    h = json.loads((tmp_path / "h.json").read_text(encoding="utf-8"))["history"]
    assert h[0]["key"] == "intraday-2026-10-30"
    V.convert_manifest(p, None, None)       # 已是 v2 不重複改
    assert json.loads(p.read_text(encoding="utf-8"))["threads"]["v2"] == m["threads"]["v2"]


# ---------------- 發文：主文 → 串文鏈 → 留言連結 ----------------
def test_publish_chain(tmp_path, monkeypatch):
    from scripts import social_publish as sp
    flag = tmp_path / "LIVE"; flag.write_text("")
    monkeypatch.setattr(sp, "LIVE_FLAG", flag); monkeypatch.setattr(sp, "_sleep", lambda s: None)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(man("intraday"), ensure_ascii=False), encoding="utf-8")
    V.convert_manifest(p, None, None)
    th = json.loads(p.read_text(encoding="utf-8"))["threads"]
    calls, n = [], [0]

    def fake(method, url, **kw):
        calls.append((method, url, kw))
        if "refresh_access_token" in url:
            return {"access_token": kw["params"]["access_token"], "expires_in": 1}
        if method == "GET":
            return {"permalink": "https://l/x"} if kw["params"]["fields"] == "permalink" else {kw["params"]["fields"]: "FINISHED"}
        n[0] += 1
        if kw.get("data", {}).get("text") == th["thread_posts"][2]:
            raise RuntimeError("HTTP 500")         # 中間某一則一直失敗（重試也不過）→ 照樣往下發
        return {"id": f"id{n[0]}"}
    monkeypatch.setattr(sp, "http", fake)
    env = {"THREADS_USER_ID": "1", "THREADS_ACCESS_TOKEN": "TOKEN_XYZ_123", "IG_USER_ID": "", "IG_ACCESS_TOKEN": ""}
    rc = sp.run(p, "https://x", env=env)
    replies = [c for c in calls if c[0] == "POST" and "reply_to_id" in c[2].get("data", {})]
    texts = [c[2]["data"]["text"] for c in replies]
    want = th["thread_posts"] + [th["reply_post"]]
    assert texts[-1] == th["reply_post"] and rc == 1           # 有一則失敗 → 標紅，但最後的連結仍發出
    assert set(texts) == set(want)
    main = [c for c in calls if c[0] == "POST" and c[2].get("data", {}).get("media_type") == "CAROUSEL"]
    assert len(main) == 1 and main[0][2]["data"]["text"] == th["text"]
    posted = json.loads((tmp_path / "posted.json").read_text(encoding="utf-8"))
    assert len(posted["intraday-2026-10-30"]["threads_chain"]) == len(want) - 1


# ---------------- 舊格式檔自動改寫（手動加發） ----------------
def test_threads_post_legacy_conversion(tmp_path):
    import threads_post as tp
    body = ("#美股 Alphabet 單日跌 12.6%\n#科技股 #財報\n\n美國時間 10/29 美股四大指數全部收黑，Alphabet 公布第三季財報後股價單日跌 12.64%。\n\n"
            "📊 #四大指數\n・道瓊：52,342.56 點，跌 0.25%\n・那斯達克：26,184.72 點，跌 1.38%\n-----\n以上為公開資料整理，非投資建議\n"
            "👉 更多詳細資料可以點擊以下連結：\nhttps://liguligu-puipui.com/?u=th-newsurgent-20261030")
    meta, posts = tp.parse(f"---\nstatus: approved\npublish_at: 2026-11-02T08:00+08:00\ntitle: t\nimages: a.jpg, b.jpg\n---\n{body}\n")
    out, imgs = tp.legacy_v2(meta, posts, tp.images_of(meta), datetime(2026, 11, 2, 8, tzinfo=timezone(timedelta(hours=8))))
    assert "http" not in out[0] and out[-1].count("https://") == 1 and len(imgs) == 2
    assert any("52,342.56" in x for x in out[1:-1])
    meta["format"] = "threads_v2"
    assert tp.legacy_v2(meta, posts, ["a"], datetime.now())[0] == posts


# ---------------- 主題文章：舊串文解析、數字卡 ----------------
def test_sections_from_article_posts():
    posts = ["#光寶科 EPS 8.08元\n#財報 和前期比，差多少？\n\n10/30，經濟日報報導：光寶科公布營運成果。\n\n📊 #重點數字\n▪ EPS年增 64%\n(1/2)",
             "以上為公開資料整理，非投資建議\n👉 更多詳細資料可以點擊以下連結：\nhttps://liguligu-puipui.com/?u=th-newspost1-20261030\n(2/2)"]
    title, secs, url = V.sections_from_posts(posts)
    assert title.startswith("光寶科 EPS 8.08元") and url.endswith("20261030")
    assert ("📊 #重點數字", ["▪ EPS年增 64%"]) in secs
    d = V.build("article", "\n".join(posts), images=["a", "b"], url=url, today="2026-11-02", sections=secs, title=title,
                extra=dict(subj="光寶科", hero="8.08元", num1="EPS 8.08元", cat="財報"), legal="以上為公開資料整理，非投資建議",
                item_max=V.THREAD_TARGET, tag_text=title)
    assert d["checklist_passed"] and d["tag"] == "光寶科財報" and "非投資建議" in d["reply_post"]


def test_numcard_no_overlap(tmp_path):
    import social_numcard as NC
    try:
        NC.font_path()
    except FileNotFoundError:
        pytest.skip("沒有中文字型")
    rows = [dict(label="外資賣超", value="1124.67", unit="億"), dict(label="加權指數跌", value="1156.5", unit="點"),
            dict(label="那指跌", value="1.38", unit="%")]
    for lay in NC.LAYOUTS:
        r = NC.render(tmp_path / f"{lay}.jpg", "「這新聞看標題就好了吧？」不行，台股的外資賣超藏在後面，只看標題會錯過重點！", rows,
                      label="財報｜台股", date_md="10/30", layout=lay)
        assert r["bad"] == [] and Path(r["path"]).exists()
    assert len({NC.layout_for(f"2026-11-{d:02d}", "post0") for d in range(1, 10)}) == 3     # 三套版型都會輪到


def test_long_content_trimmed_to_six_posts_and_points_to_site():
    """數據很多（新聞 10 條、盤面細項很長）→ 同類合併＋精簡次要數據，壓到 6 則，留言寫「完整盤勢見網站」。"""
    th = man("close")["threads"]
    news = "📰 新聞焦點：\n" + "\n".join(f"・第{i}則新聞的短標題：這是一段很長很長的描述，用來把串文撐爆，看看會不會被精簡到網站連結那則去{i}" for i in range(10))
    d = V.build("close", th["text"], th["reply"] + "\n" + news, th["images"], today="2026-11-02")
    assert len(d["thread_posts"]) <= 6 and d["checklist_passed"], L.lint(d)
    assert "完整盤勢見網站" in d["reply_post"]
    joined = "\n".join(d["thread_posts"])
    for must in ("外資 -1,124.7億", "買超 大立光", "加權指數跌 1,156 點"):     # 主要數據（盤勢、法人）一定留著
        assert must in joined


def test_fit_keeps_everything_when_it_fits():
    posts, cut = V.fit([("🔥 熱力圖：", ["・漲最多 貨櫃航運 +2.9%、資安防護 +1.8%；", "・跌最多 電源供應器 -8.8%"])], "🕛 盤中3分鐘", 145)
    assert cut == [] and len(posts) == 1
