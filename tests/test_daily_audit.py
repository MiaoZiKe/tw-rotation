"""每日三關稽核的測試（scripts/daily_audit.py）。

全部用假事實（fixture）跑純函式，不打 GitHub、不讀資料湖。
涵蓋 Andy 2026-11-09 指定的情境：全綠、執行失敗、內容過期、已執行但沒發布、非交易日不檢查、補救一天只一次。
"""
import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("daily_audit", ROOT / "scripts" / "daily_audit.py")
da = importlib.util.module_from_spec(_spec)
sys.modules["daily_audit"] = da
_spec.loader.exec_module(da)

TPE = timezone(timedelta(hours=8))
TODAY = "2026-11-09"
NOW = at("2026-11-09T10:26:00") if False else None  # 下面補上  # 週一，交易日
HOL: set[str] = set()


def at(s: str) -> datetime:
    """無時區字串一律當台北時間（容器是 UTC，不能用 astimezone 猜）。"""
    return datetime.fromisoformat(s).replace(tzinfo=TPE)


def run(conclusion="success", created="2026-11-09T16:00:00+08:00", status="completed"):
    return {"conclusion": conclusion, "status": status, "created_at": created,
            "html_url": "https://github.com/x/runs/1"}


def green_facts(today=TODAY, expected=TODAY):
    ok_runs = [run()]
    return {
        "today": today,
        "expected_price": expected,
        "runs": {"social-live.yml": ok_runs, "daily.yml": ok_runs, "article-jobs.yml": ok_runs,
                 "tc_post.yml": ok_runs, "healing_post.yml": ok_runs, "pages.yml": ok_runs,
                 "meta_token_refresh.yml": ok_runs},
        "premarket": {"updated": today, "days": [{"date": today, "items": [
            {"title": "盤前一", "url": "https://news.example/1"}]}]},
        "postmarket": {"updated": today, "days": [{"date": today, "items": [
            {"title": "盤後一", "url": "https://news.example/2"}]}]},
        "last_run": {"errors": []},
        "source_health": {"twse": {"consecutive_fail": 0}},
        "lake": {"price_daily": expected, "inst_daily": expected, "margin_total": expected},
        "snaps_posted": {f"close-{today}": {"threads": {"id": "1", "link": "https://threads.com/p/1"},
                                            "story": []}},
        "quota": {"live": {"close": {"threads": True}}, "tc": {"enabled": True}},
        "healing_quota": {"live": True, "per_day": 1},
        "healing_queue": [{"slug": "20261108_intro", "status": "approved", "platforms": ["ig", "threads"],
                           "publish_at": None}],
        "healing_posted": {"20261108_intro": {"ig": {"link": "https://ig.example/1"},
                                              "threads": {"link": "https://threads.example/1"}}},
        "tc_queue": [],
        "tc_posted": {},
        "meta": {"updated_at": f"{today}T03:00:00+00:00",
                 "platforms": {"threads": {"ok": True, "days_left": 60}, "ig": {"ok": True, "days_left": 60}}},
    }


SITE_OK = da.gate(True, "兩站都包含最新資料")


NOW = at("2026-11-09T10:26:00")


def by_id(items):
    return {it["id"]: it for it in items}


def test_all_green():
    now = at("2026-11-09T19:00:00")
    items = by_id(da.evaluate(green_facts(), HOL, {"site": SITE_OK}, now))
    assert all(it["status"] == "ok" for it in items.values()), {k: v["status"] for k, v in items.items()}
    assert da.summarize(list(items.values()))["fail"] == 0


def test_run_failure_is_red_after_deadline():
    f = green_facts()
    f["runs"]["daily.yml"] = [run(conclusion="failure")]
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
    assert items["data"]["status"] == "fail"
    assert items["data"]["gates"]["run"]["ok"] is False
    assert items["data"]["remedy"]["workflow"] == "daily.yml"


def test_stale_content_is_red():
    # 08:45 盤前：截止 08:40 已過，檔案還是昨天的 → 內容過期，紅燈
    f = green_facts()
    f["premarket"]["days"][0]["date"] = "2026-11-06"
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T08:45:00")))
    assert items["premarket"]["status"] == "fail"
    assert items["premarket"]["gates"]["content"]["ok"] is False
    assert items["premarket"]["remedy"]["inputs"]["kind"] == "premarket"


def test_executed_but_not_published_is_red():
    # 社群有發文紀錄但沒有發布網址 → 關卡三不過
    f = green_facts()
    f["snaps_posted"] = {f"close-{TODAY}": {"threads": {"id": "1"}, "story": []}}
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T20:42:00")))      # 11-09 起截止 20:35
    assert items["close_post"]["gates"]["content"]["ok"] is True
    assert items["close_post"]["gates"]["publish"]["ok"] is False
    assert items["close_post"]["status"] == "fail"


def test_site_not_deployed_is_red():
    bad_site = da.gate(False, "Cloudflare 主站還沒包含最新資料")
    items = by_id(da.evaluate(green_facts(), HOL, {"site": bad_site}, at("2026-11-09T19:00:00")))
    assert items["website"]["status"] == "fail"
    assert items["premarket"]["gates"]["publish"]["ok"] is False


def test_non_trading_day_is_skipped():
    # 2026-11-07 週六：盤前、盤後、盤後主貼文都不檢查
    f = green_facts(today="2026-11-07", expected="2026-11-06")
    f["premarket"]["days"][0]["date"] = "2026-11-06"  # 故意過期，也不該紅
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-07T10:00:00")))
    assert items["premarket"]["status"] == "skip"
    assert items["postmarket"]["status"] == "skip"
    assert items["close_post"]["status"] == "skip"
    assert items["data"]["status"] in ("ok", "fail")  # 每天都要檢查


def test_holiday_is_not_trading_day():
    hol = {"2026-11-10"}
    assert da.is_trading_day(datetime(2026, 11, 10).date(), hol) is False
    assert da.expected_price_date(at("2026-11-10T18:00:00"), hol).isoformat() == "2026-11-09"
    assert da.expected_price_date(at("2026-11-09T15:30:00"), hol).isoformat() == "2026-11-09"
    assert da.expected_price_date(at("2026-11-09T15:29:00"), hol).isoformat() == "2026-11-06"


def test_before_deadline_is_pending_not_red():
    f = green_facts()
    f["snaps_posted"] = {}  # 還沒發
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T17:00:00")))
    assert items["close_post"]["status"] == "pending"


def test_disabled_is_not_failure():
    f = green_facts()
    f["healing_quota"] = {"live": False}  # 整個停發
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
    assert items["healing"]["status"] == "disabled"


def test_healing_approved_due_but_not_posted_is_red():
    # 20:27 的時段已到、核准稿沒發（只有 ig 有紀錄，threads 缺）→ 21:40 紅燈
    f = green_facts()
    f["healing_queue"].append({"slug": "20261109_second", "status": "approved", "platforms": ["ig", "threads"],
                               "publish_at": None})
    f["healing_posted"]["20261109_second"] = {"ig": {"link": "https://ig.example/2"}}
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T21:40:00")))
    assert items["healing"]["status"] == "fail"
    assert "20261109_second" in items["healing"]["gates"]["publish"]["why"]
    assert items["healing"]["remedy"]["inputs"] == {"mode": "post", "dry_run": "false"}


def test_healing_future_publish_at_is_not_due():
    f = green_facts()
    f["healing_queue"] = [{"slug": "20261110_x", "status": "approved", "platforms": ["ig"],
                           "publish_at": "2026-11-10T20:27+08:00"}]
    f["healing_posted"] = {}
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T21:40:00")))
    assert items["healing"]["status"] == "ok"


def test_tc_draft_is_not_red_but_approved_due_is():
    f = green_facts()
    f["tc_queue"] = [{"slug": "20261110_quanta", "status": "draft", "scheduled_at": "2026-11-10T20:30+08:00",
                      "file": "x"}]
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T21:40:00")))
    assert items["tc"]["status"] == "ok"
    f["tc_queue"] = [{"slug": "20261108_x", "status": "approved", "scheduled_at": "2026-11-08T20:30+08:00",
                      "file": "x"}]
    f["tc_posted"] = None  # 紀錄檔不存在＝查不到
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T21:40:00")))
    assert items["tc"]["status"] == "fail"


def test_remedy_only_once_per_day():
    f = green_facts()
    f["runs"]["daily.yml"] = [run(conclusion="failure")]
    now = at("2026-11-09T19:00:00")
    state: dict = {}
    calls = []

    def fake(wf, inputs):
        calls.append(wf)
        return True, "dispatched"

    items = da.evaluate(f, HOL, {"site": SITE_OK}, now)
    da.run_remedies(items, state, TODAY, fake)
    assert calls.count("daily.yml") >= 1
    first = len(calls)

    items2 = da.evaluate(f, HOL, {"site": SITE_OK}, now)
    da.run_remedies(items2, state, TODAY, fake)
    assert len(calls) == first, "同一天同一項不准再補救第二次"
    assert "今天已補救過一次" in " ".join(str(i.get("remedy_note", "")) for i in items2)


def test_remedy_resets_next_day():
    state = {"remedies": {"data": {"date": "2026-11-08", "ok": True}}}
    assert da.remedy_allowed(state, "data", "2026-11-09") is True
    assert da.remedy_allowed({"remedies": {"data": {"date": TODAY}}}, "data", TODAY) is False


def test_site_gate_detects_stale_cloudflare():
    site = {"required": "aaa1111", "gh_pages": "bbb2222", "cf": "ccc3333", "pending": False}

    def cmp(base, head):
        # 主站（cf）落後備援（gh_pages）：gh_pages...cf 的 head 是 cf，比 base 新 → 這裡模擬 required→cf 為 ahead
        if (base, head) == ("aaa1111", "bbb2222"):
            return "ahead"
        if (base, head) == ("aaa1111", "ccc3333"):
            return "ahead"
        if (base, head) == ("bbb2222", "ccc3333"):
            return "ahead"  # cf 比 gh 新 → 不算落後
        return "behind"

    assert da.site_gate(site, cmp, NOW)["ok"] is True
    site_lag = dict(site, cf="ddd4444")
    assert da.site_gate(site_lag, lambda b, h: "behind", NOW)["ok"] is False


def test_deploy_in_progress_is_pending_even_after_deadline():
    # 08:45 盤前截止 08:40 已過，但部署中（一小時內）→ 還沒到，不是紅燈
    f = green_facts()
    f["premarket"]["days"][0]["date"] = TODAY
    site = da.gate(False, "pages.yml 正在部署中（還沒跑完）", busy=True)
    items = by_id(da.evaluate(f, HOL, {"site": site}, at("2026-11-09T10:26:00")))
    assert items["premarket"]["status"] == "pending"
    assert items["premarket"]["gates"]["content"]["ok"] is True


def test_site_gate_pending_and_unknown():
    busy = da.site_gate({"required": "a", "pending": True, "pending_since": "2026-11-09T10:20:00+08:00"},
                        lambda b, h: "ahead", NOW)
    assert busy["ok"] is False and busy["busy"] is True
    stuck = da.site_gate({"required": "a", "pending": True, "pending_since": "2026-11-09T08:00:00+08:00"},
                         lambda b, h: "ahead", NOW)
    assert stuck["ok"] is False and stuck["busy"] is False and "卡住" in stuck["why"]
    unknown = da.site_gate({"required": None, "pending": False}, lambda b, h: "ahead", NOW)
    assert unknown["ok"] is False and unknown["why"].startswith("查不到")


def test_source_consecutive_fail_is_red_only_when_repeated():
    f = green_facts()
    f["source_health"] = {"macro.fred": {"consecutive_fail": 1}}
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
    assert items["data"]["status"] == "ok"  # 只壞一天不紅
    f["source_health"] = {"macro.fred": {"consecutive_fail": 2}}
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
    assert items["data"]["status"] == "fail"


def test_load_holidays_parses_days_block(tmp_path):
    p = tmp_path / "h.yaml"
    p.write_text('# "2026-01-01" 只是註解\ndays:\n  "2026-10-10": {n: 國慶日}\n  "2026-02-16": {n: 春節}\n',
                 encoding="utf-8")
    assert da.load_holidays(p) == {"2026-10-10", "2026-02-16"}


def test_close_post_1840_not_red_before_2035():
    # 2026-11-09 Andy 同意：盤後主貼文改 19:30～20:30 發。18:40、20:30 那輪還沒發 → 進行中（不紅、不補發、不寄信）；20:42 還沒發才紅
    f = green_facts()
    f["snaps_posted"] = {}
    for t in ("2026-11-09T18:40:00", "2026-11-09T19:45:00", "2026-11-09T20:30:00"):
        it = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at(t)))["close_post"]
        assert it["status"] == "pending" and it["remedy"] is None, (t, it["status"])
    it = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T20:42:00")))["close_post"]
    assert it["status"] == "fail" and it["remedy"]["workflow"] == "social-live.yml"
