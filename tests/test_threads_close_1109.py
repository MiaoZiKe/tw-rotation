"""2026-11-09 Andy：「同意，四項改動全部照改」（docs/marketing/traffic_plan_1109.md 第二節第 2～7 條、diagnosis_1109.md）。

盤後自動主貼文（Threads）：
  ① 拿掉「🌙 盤後3分鐘｜盤面分析」欄目標頭；第一句＝用當天最反差的數字寫的吊胃口問句；結尾一題好回答的二選一
  ② 主文 ≤150 字（標籤不算），其餘數據放串文第一則回覆（≤500）
  ③ 發文時段 19:30～20:30：資料齊了也等到 19:30；稽核截止 20:35，18:40 那輪不紅
  ④ IG 自動純圖文全關（post_quota.json），Threads 盤後 1 則照舊開
fixtures 用 11-03、11-04 盤後正式產出的舊版文案（tests/fixtures/threads_auto_1104/）。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import post_quota  # noqa: E402
import social_gate as G  # noqa: E402
import threads_lint as L  # noqa: E402
import threads_v2 as V  # noqa: E402

FX = ROOT / "tests" / "fixtures" / "threads_auto_1104"

# 11-06 盤後正式文案（social-snaps close-20261106-1944 的 threads_v1，前幾段）＋一行加權指數（測反差模板 c_x1）
TEXT_1106 = """🌙 盤後3分鐘
🧭 盤面分析：
・加權指數跌 82 點（-0.30%）；上市櫃（含 ETF）上漲 512 家、下跌 1,201 家
・外資賣超 911.9 億，已連 7 日賣超，累計 7,056.6 億
・投信買超 266.6 億，已連 19 日買超，累計 3,573.8 億
📊 台指期法人淨未平倉：
・外資 -99,930 口、投信 +90,437 口；
・自營商 +1,680 口
🏦 三大法人買賣超：
・外資 -911.9億、投信 +266.6億；
・自營 -494.8億、合計 -1,140.1億
🌏 外資：
・買超 南亞科、大立光、聯亞、頎邦、環球晶；
・賣超 台積電、聯發科、日月光投控、欣興、台達電
#台股 #法人買賣超 #外資 #投信 #台指期"""


def fx(day):
    return json.loads((FX / f"close_{day}.json").read_text(encoding="utf-8"))


def _check_close(d):
    body, tags = L.split_tag(d["main_post"])
    hook, rest = L.hook_of(body)
    assert d["checklist_passed"], L.lint(d)
    assert d["rule"] == "auto_1109" and d["profile"] == "auto"
    assert L.clen(body) <= 150, (L.clen(body), body)                         # ② 主文 ≤150
    assert "盤後3分鐘" not in d["main_post"] and "盤面分析" not in d["main_post"]     # ① 欄目標頭拿掉
    assert hook.endswith("？") and any(c.isdigit() for c in hook)              # ① 第一句＝帶數字的問句
    last = body.split("\n\n")[-1]
    assert last.endswith("？") and "還是" in last and last != hook             # ① 結尾二選一
    assert len(d["thread_posts"]) == 1 and L.tlen(d["thread_posts"][0]) <= 500   # ② 數據放串文第一則
    assert "http" not in d["main_post"] + "".join(d["thread_posts"])          # 不放網址
    assert not L.stock_in(hook)                                               # 開頭不點名個股
    assert d["reply_post"] == L.DEFAULT_LEGAL and len(tags) == 1
    return hook, rest


def test_andy_example_contrast_hook_and_binary_ending():
    d = V.build("close", TEXT_1106, "", ["a/threads_streak-foreign.png"], today="2026-11-06")
    hook, rest = _check_close(d)
    assert hook == "外資賣超 912 億，指數卻只跌 0.30%，錢去哪了？"            # Andy 給的例句（用當天最反差的數字）
    assert rest.endswith("你覺得是換手還是出貨？")
    assert "盤面分析" in d["thread_posts"][0] and "買超 南亞科" in d["thread_posts"][0]
    assert d["images"] == ["a/threads_streak-foreign.png"]                    # 圖照舊 1 張


def test_real_1103_1104_new_format():
    for day in ("20261103", "20261104"):
        th = fx(day)
        d = V.build("close", th["text"], th["reply"], th["images"], today=f"{day[:4]}-{day[4:6]}-{day[6:]}")
        _check_close(d)


def test_lint_rejects_long_main_and_missing_binary():
    d = V.build("close", TEXT_1106, "", [], today="2026-11-06")
    long_ = dict(d, main_post=d["main_post"].replace("你覺得是換手還是出貨？", "甲" * 120 + "你覺得是換手還是出貨？"))
    assert any("盤後主文" in e and "≤150" in e for e in L.lint(long_)[0])
    no_q = dict(d, main_post=d["main_post"].replace("你覺得是換手還是出貨？", "法人動向整理如下"))
    assert any("二選一" in e for e in L.lint(no_q)[0])
    two = dict(d, thread_posts=d["thread_posts"] * 2)
    assert any("最多 1 則" in e for e in L.lint(two)[0])
    # 盤後新版串文單則可到 500（不套一般 150）；其他時段照舊 0 則
    assert not [e for e in L.lint(d)[0] if "串文" in e]
    other = dict(d, rule="auto_1104")
    assert any("最多 0 則" in e for e in L.lint(other)[0])


def test_never_empty_without_data():
    d = V.build("close", "", "", [], today="2026-11-09")       # 沒有任何數據也發得出一篇（保底模板＋保底二選一）
    body = L.split_tag(d["main_post"])[0]
    assert d["main_post"] and L.clen(body) <= 150 and "還是" in body.split("\n\n")[-1]


def test_earliest_1930_gate():
    T = lambda s: datetime.fromisoformat(s).replace(tzinfo=G.TPE)    # noqa: E731
    assert G.CLOSE_EARLIEST_AT == "19:30" and G.CLOSE_FALLBACK_AT == "20:00"
    assert G.close_wait(T("2026-11-09T17:30")) > G.CLOSE_WAIT_MAX_S          # 17:30 資料齊了 → 這輪不發（結束碼 10）
    assert 0 < G.close_wait(T("2026-11-09T19:20")) <= G.CLOSE_WAIT_MAX_S     # 19:20 → 就地等到 19:30
    assert G.close_wait(T("2026-11-09T19:30")) <= 0 and G.close_wait(T("2026-11-09T20:20")) <= 0
    assert G.close_wait(T("2026-11-09T18:00"), "17:00") <= 0                 # 環境變數 CLOSE_EARLIEST_AT 可改


def test_social_live_backup_schedule_is_close():
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "social-live.yml").read_text(encoding="utf-8"))
    on = wf.get("on") or wf.get(True)
    assert [c["cron"] for c in on["schedule"]] == ["41 11 * * 1-5", "11 12 * * 1-5"]     # 台北 19:41、20:11
    kind_expr = wf["jobs"]["snap-and-post"]["strategy"]["matrix"]["kind"]
    assert "github.event_name == 'schedule'" in kind_expr and "'[\"close\"]'" in kind_expr
    au = yaml.safe_load((ROOT / ".github" / "workflows" / "daily_audit.yml").read_text(encoding="utf-8"))
    crons = [c["cron"] for c in (au.get("on") or au.get(True))["schedule"]]
    assert "42 12 * * 1-5" in crons                                           # 台北 20:42 盤後主貼文稽核


def test_ig_auto_image_posts_all_off_threads_close_on():
    q = post_quota.load(post_quota.QUOTA_FILE)      # conftest 會把 POST_QUOTA_FILE 指到測試用的全開檔 → 這裡讀正式檔
    assert "2026-11-09" in q.get("_note", "") and "同意，四項改動全部照改" in q["_note"]
    for kind in ("premarket", "intraday", "close", "credit", "close_inst"):
        assert post_quota.live_allowed(kind, "ig_story", q) is False, kind
    assert post_quota.queue_allowed("ig", "2026-11-09_news-close-1.md", q) is False
    assert post_quota.live_allowed("close", "threads", q) is True


# ---- 2026-11-09 CEO 追加：① 標籤不准含個股名 ② 備用文案（v2 失敗時發的）也要新格式 ----
def test_close_tag_has_no_stock_name():
    for day in ("20261103", "20261104"):
        th = fx(day)
        d = V.build("close", th["text"], th["reply"], th["images"], today="2026-11-05")
        assert not L.stock_in(d["tag"]) and d["tag"] not in L.GENERIC_TAGS, d["tag"]
    d = V.build("close", TEXT_1106, "", [], today="2026-11-06")
    assert d["tag"] == "外資連賣" and d["main_post"].endswith("#外資連賣")
    bad = dict(d, main_post=d["main_post"].replace("#外資連賣", "#台積電外資賣超"), tag="台積電外資賣超")
    assert any("含個股名「台積電」" in e for e in L.lint(bad)[0])


def test_snap_fallback_caption_is_new_format():
    import social_snap as S
    for day in ("20261103", "20261104"):
        th = fx(day)
        main, reply = S.close_v1(th["text"], th["reply"])
        body, tags = L.split_tag(main)
        hook = body.split("\n\n")[0]
        last = body.split("\n\n")[-1]
        assert "盤後3分鐘" not in main and "盤面分析" not in main
        assert L.clen(body) <= 150 and hook.endswith("？") and last.endswith("？") and "還是" in last
        assert len(tags) == 1 and not L.stock_in(tags[0]) and not L.stock_in(hook)
        assert "http" not in main + reply and L.tlen(reply) <= 500 and reply.endswith(L.DEFAULT_LEGAL)
        assert "盤後3分鐘" not in reply and "・" in reply
        # 過得了 auto_1109 的 lint（當成 v2 貼文檢查）
        p = dict(kind="close", profile="auto", rule="auto_1109", hook_type="問句", emotion="專業", main_post=main,
                 thread_posts=[], reply_post=L.DEFAULT_LEGAL, image_count=1, tag=tags[0])
        assert not L.lint(p)[0], L.lint(p)
    m, r = S.close_v1("", "")
    assert "還是" in m and r == L.DEFAULT_LEGAL                      # 沒資料也發得出一篇


def test_v2_rewrites_from_v1_raw():
    import social_snap as S
    import tempfile
    th = fx("20261104")
    main, reply = S.close_v1(th["text"], th["reply"])
    m = {"kind": "close", "taken_at": "2026-11-04T19:35:00+08:00", "data_date": "2026-11-04",
         "threads": {"text": main, "reply": reply, "images": th["images"], "v1_raw": {"text": th["text"], "reply": th["reply"]}}}
    with tempfile.TemporaryDirectory() as td:
        mp = Path(td) / "manifest.json"
        mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        out = V.convert_manifest(mp, None, None)
    v2 = out["threads"]["v2"]
    assert v2["rule"] == "auto_1109" and v2["checklist_passed"] and "盤面分析" in out["threads"]["thread_posts"][0]
