"""每日三關稽核的測試（scripts/daily_audit.py）。

全部用假事實（fixture）跑純函式，不打 GitHub、不打線上網站、不讀資料湖。
涵蓋 Andy 2026-11-09 指定的情境：全綠、執行失敗（price／full 輪）、內容過期、已執行但沒發布、
非交易日不檢查、分段截止（價量 16:15、法人 17:15、其餘 18:40）、畫面資料日落後、補救追蹤與每日上限 3 次。
"""
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("daily_audit", ROOT / "scripts" / "daily_audit.py")
da = importlib.util.module_from_spec(_spec)
sys.modules["daily_audit"] = da
_spec.loader.exec_module(da)

TPE = timezone(timedelta(hours=8))
TODAY = "2026-11-09"  # 週一，交易日
HOL: set[str] = set()


def at(s: str) -> datetime:
    """無時區字串一律當台北時間（容器是 UTC，不能用 astimezone 猜）。"""
    return datetime.fromisoformat(s).replace(tzinfo=TPE)


def run(conclusion="success", created="2026-11-09T16:00:00+08:00", status="completed"):
    return {"conclusion": conclusion, "status": status, "created_at": created,
            "html_url": "https://github.com/x/runs/1", "id": 1}


def rr(conclusion, created, steps=None, title=None, status="completed", url="https://github.com/x/runs/2"):
    """帶步驟與標題的 daily.yml 執行（對應 jobs API 整理後的 _steps）。"""
    r = run(conclusion=conclusion, created=created, status=status)
    r["html_url"] = url
    if steps is not None:
        r["_steps"] = steps
    if title is not None:
        r["display_title"] = title
    return r


PRICE_STEPS_FAIL = [{"name": "跑指標庫測試", "conclusion": "success"},
                    {"name": "抓取與計算", "conclusion": "failure"}]
INST_STEPS = [{"name": "跑指標庫測試", "conclusion": "skipped"},
              {"name": "抓取與計算", "conclusion": "success"}]


def prev_month_end(s: str) -> str:
    """應有日的上一個月月底（月資料 date 欄位是月底）。"""
    d = datetime.fromisoformat(s).replace(day=1) - timedelta(days=1)
    return d.date().isoformat()


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
        "source_health": {"twse": {"consecutive_fail": 0},
                          "etf_pcf.holdings": {"consecutive_fail": 0, "last_ok_date": expected},
                          "etf.exright_notice": {"consecutive_fail": 0, "last_ok_date": expected}},
        "lake": {"price_daily": expected, "inst_daily": expected, "margin_total": expected,
                 "etf_holdings": expected, "etf_holdings_monthly": prev_month_end(expected)},
        "screen": {k: {"data_date": expected, "inst_date": expected, "inst_market_latest": expected,
                       "error": None, "etf_asof": expected, "etf_hold_asof": expected, "etf_error": None}
                   for k in ("liguligu", "gh_pages")},
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


def test_price_round_failure_is_red_before_deadline():
    # 11-09 事故：15:38 的 price 輪失敗，不等 16:15 截止，立刻紅，附失敗網址與失敗步驟名稱
    f = green_facts()
    f["runs"]["daily.yml"] = [rr("failure", "2026-11-09T15:38:00+08:00", PRICE_STEPS_FAIL,
                                 title="每日盤後管線 (price)")]
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T15:50:00")))
    assert items["data"]["status"] == "fail"
    g = items["data"]["gates"]["run"]
    assert g["ok"] is False and g["hard"] is True
    assert "抓取與計算" in g["why"]
    assert g["evidence"] == ["https://github.com/x/runs/2"]


def test_price_round_failure_then_success_is_green():
    f = green_facts()
    f["runs"]["daily.yml"] = [
        rr("failure", "2026-11-09T15:38:00+08:00", PRICE_STEPS_FAIL, title="每日盤後管線 (price)"),
        rr("success", "2026-11-09T16:05:00+08:00", title="每日盤後管線 (price)"),
    ]
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T16:20:00")))
    assert items["data"]["gates"]["run"]["ok"] is True
    assert items["data"]["status"] == "ok"


def test_failure_after_success_is_red():
    # 15:45 成功、18:37 的 full 輪失敗，之後沒有成功 → 紅
    f = green_facts()
    f["runs"]["daily.yml"] = [
        rr("success", "2026-11-09T15:45:00+08:00", title="每日盤後管線 (price)"),
        rr("failure", "2026-11-09T18:37:00+08:00", PRICE_STEPS_FAIL, title="每日盤後管線 (full)"),
    ]
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
    assert items["data"]["gates"]["run"]["hard"] is True
    assert items["data"]["status"] == "fail"


def test_inst_round_failure_does_not_count_as_price_round():
    # 法人輪（測試步驟被跳過）失敗，不算價量輪的失敗：不能是 hard 紅
    f = green_facts()
    f["runs"]["daily.yml"] = [rr("failure", "2026-11-09T16:15:00+08:00",
                                 [{"name": "跑指標庫測試", "conclusion": "skipped"},
                                  {"name": "抓取與計算", "conclusion": "failure"}])]
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T16:10:00")))
    assert items["data"]["status"] == "pending"  # 價量截止前，沒有價量輪＝還沒到
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T16:30:00")))
    assert items["data"]["gates"]["run"]["hard"] is False
    assert items["data"]["status"] == "fail"  # 截止後沒有價量輪＝沒跑，才紅


def test_pending_before_price_deadline_when_no_round_yet():
    f = green_facts()
    f["runs"]["daily.yml"] = []
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T15:50:00")))
    assert items["data"]["status"] == "pending"
    assert items["data"]["gates"]["run"]["ok"] is False


def test_running_round_is_busy_not_red():
    f = green_facts()
    f["runs"]["daily.yml"] = [rr("failure", "2026-11-09T15:38:00+08:00", PRICE_STEPS_FAIL,
                                 title="每日盤後管線 (price)"),
                              rr(None, "2026-11-09T16:12:00+08:00", title="每日盤後管線 (price)",
                                 status="in_progress")]
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T16:13:00")))
    assert items["data"]["gates"]["run"]["busy"] is True
    assert items["data"]["status"] == "pending"


def test_news_and_weekend_runs_are_not_price_rounds():
    assert da.is_round(run(created="2026-11-07T20:07:00+08:00"), HOL) is False  # 週六的新聞輪
    assert da.is_round(rr("success", "2026-11-09T09:07:00+08:00", title="每日盤後管線 (news)"), HOL) is False
    assert da.is_round(rr("success", "2026-11-09T16:00:00+08:00", title="每日盤後管線 (price)"), HOL) is True


def test_inst_deadline_is_1715_not_1615():
    f = green_facts()
    f["lake"]["inst_daily"] = "2026-11-06"  # 法人還沒進湖
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T17:00:00")))
    assert items["data"]["status"] == "pending"
    assert items["data"]["gates"]["inst"]["ok"] is False
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T17:20:00")))
    assert items["data"]["status"] == "fail"
    assert items["data"]["gates"]["inst"]["ok"] is False


def test_screen_behind_is_red_after_deadline():
    # 備援站的總覽還停在前一天：截止前還沒到，18:40 後紅，且說明寫出兩站各自的日期
    f = green_facts()
    f["screen"]["gh_pages"]["inst_market_latest"] = "2026-11-06"
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T18:00:00")))
    assert items["data"]["status"] == "pending"
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T18:50:00")))
    assert items["data"]["status"] == "fail"
    why = items["data"]["gates"]["screen"]["why"]
    assert "備援" in why and "2026-11-06" in why and "主站" in why


def test_screen_unreadable_is_not_green():
    f = green_facts()
    f["screen"]["liguligu"] = {"data_date": None, "inst_date": None, "inst_market_latest": None,
                               "error": "timeout"}
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
    assert items["data"]["gates"]["screen"]["ok"] is False
    assert "讀不到" in items["data"]["gates"]["screen"]["why"]
    assert items["data"]["status"] == "fail"


def test_collect_screen_records_per_site_errors():
    def fake(url):
        if "miaozike" in url:
            raise OSError("boom")
        if url.endswith("meta.json"):
            return {"data_date": TODAY, "inst_date": TODAY}
        return {"latest": TODAY}

    out = da.collect_screen(fake)
    assert out["liguligu"]["data_date"] == TODAY and out["liguligu"]["inst_market_latest"] == TODAY
    assert out["liguligu"]["error"] is None
    assert out["gh_pages"]["error"] and out["gh_pages"]["data_date"] is None


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
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
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


def test_deploy_in_progress_is_pending_even_after_deadline():
    # 08:45 盤前截止 08:40 已過，但部署中（一小時內）→ 還沒到，不是紅燈
    f = green_facts()
    site = da.gate(False, "pages.yml 正在部署中（還沒跑完）", busy=True)
    items = by_id(da.evaluate(f, HOL, {"site": site}, at("2026-11-09T10:26:00")))
    assert items["premarket"]["status"] == "pending"
    assert items["premarket"]["gates"]["content"]["ok"] is True


def test_site_gate_detects_stale_cloudflare():
    site = {"required": "aaa1111", "gh_pages": "bbb2222", "cf": "ccc3333", "pending": False}
    now = at("2026-11-09T19:00:00")

    def cmp(base, head):
        if (base, head) == ("aaa1111", "bbb2222"):
            return "ahead"
        if (base, head) == ("aaa1111", "ccc3333"):
            return "ahead"
        if (base, head) == ("bbb2222", "ccc3333"):
            return "ahead"  # cf 比 gh 新 → 不算落後
        return "behind"

    assert da.site_gate(site, cmp, now)["ok"] is True
    site_lag = dict(site, cf="ddd4444")
    assert da.site_gate(site_lag, lambda b, h: "behind", now)["ok"] is False


def test_site_gate_pending_and_unknown():
    now = at("2026-11-09T19:00:00")
    busy = da.site_gate({"required": "a", "pending": True, "pending_since": "2026-11-09T18:20:00+08:00"},
                        lambda b, h: "ahead", now)
    assert busy["ok"] is False and busy["busy"] is True
    stuck = da.site_gate({"required": "a", "pending": True, "pending_since": "2026-11-09T08:00:00+08:00"},
                         lambda b, h: "ahead", now)
    assert stuck["ok"] is False and stuck["busy"] is False and "卡住" in stuck["why"]
    unknown = da.site_gate({"required": None, "pending": False}, lambda b, h: "ahead", now)
    assert unknown["ok"] is False and unknown["why"].startswith("查不到")


def test_source_consecutive_fail_is_red_only_when_repeated():
    f = green_facts()
    f["source_health"]["macro.fred"] = {"consecutive_fail": 1}  # 只更新這一個來源，ETF 鍵保留
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
    assert items["data"]["status"] == "ok"  # 只壞一天不紅
    f["source_health"]["macro.fred"] = {"consecutive_fail": 2}
    items = by_id(da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00")))
    assert items["data"]["status"] == "fail"


def test_load_holidays_parses_days_block(tmp_path):
    p = tmp_path / "h.yaml"
    p.write_text('# "2026-01-01" 只是註解\ndays:\n  "2026-10-10": {n: 國慶日}\n  "2026-02-16": {n: 春節}\n',
                 encoding="utf-8")
    assert da.load_holidays(p) == {"2026-10-10", "2026-02-16"}


# ---------------------------------------------------------------- 補救：每項每天最多 3 次，上一次還在跑就不重派

def _fail_items():
    return [{"id": "x", "status": "fail", "remedy": {"workflow": "pages.yml", "inputs": {}}}]


def test_remedy_in_flight_is_not_redispatched_and_cancelled_is_redispatched():
    T0 = at("2026-11-09T19:00:00")
    state: dict = {}
    calls = []

    def fake(wf, inputs):
        calls.append(wf)
        return True, "dispatched"

    # 第一輪：派出
    da.run_remedies(_fail_items(), state, TODAY, fake, runs={"pages.yml": []}, now=T0)
    assert calls == ["pages.yml"]
    # 第二輪：派出的 run 還在跑 → 不重派
    items = _fail_items()
    da.run_remedies(items, state, TODAY, fake,
                    runs={"pages.yml": [rr("", (T0 + timedelta(seconds=10)).isoformat(), status="in_progress")]},
                    now=T0 + timedelta(minutes=1))
    assert calls == ["pages.yml"]
    assert "執行中" in items[0]["remedy_note"]
    # 第三輪：被佇列取代（cancelled）→ 重派；attempt 記下 run 結論
    da.run_remedies(_fail_items(), state, TODAY, fake,
                    runs={"pages.yml": [rr("cancelled", (T0 + timedelta(seconds=10)).isoformat(), status="completed")]},
                    now=T0 + timedelta(minutes=3))
    assert calls == ["pages.yml", "pages.yml"]
    assert state["remedies"]["x"]["attempts"][0]["run_conclusion"] == "cancelled"
    # 第四輪：又失敗 → 第三次
    da.run_remedies(_fail_items(), state, TODAY, fake,
                    runs={"pages.yml": [rr("failure", (T0 + timedelta(minutes=3, seconds=10)).isoformat())]},
                    now=T0 + timedelta(minutes=5))
    assert len(calls) == 3
    # 第五輪：今天已經 3 次 → 不再派，寫明等人工
    items = _fail_items()
    da.run_remedies(items, state, TODAY, fake,
                    runs={"pages.yml": [rr("success", (T0 + timedelta(minutes=5, seconds=10)).isoformat())]},
                    now=T0 + timedelta(minutes=7))
    assert len(calls) == 3
    assert "3 次" in items[0]["remedy_note"]
    assert state["remedies"]["x"]["count"] == 3


def test_remedy_lost_run_is_redispatched_after_timeout_and_unknown_is_not():
    T0 = at("2026-11-09T19:00:00")
    state: dict = {}
    calls = []

    def fake(wf, inputs):
        calls.append(wf)
        return True, "ok"

    da.run_remedies(_fail_items(), state, TODAY, fake, runs={"pages.yml": []}, now=T0)
    # 查不到（API 失敗）→ 不准重派，避免重複派
    da.run_remedies(_fail_items(), state, TODAY, fake, runs={"pages.yml": None}, now=T0 + timedelta(minutes=20))
    assert len(calls) == 1
    # 派出 11 分鐘還找不到 run → 當作派丟了，重派
    da.run_remedies(_fail_items(), state, TODAY, fake, runs={"pages.yml": []}, now=T0 + timedelta(minutes=11))
    assert len(calls) == 2


def test_remedy_cap_is_per_item_per_day_and_resets_next_day():
    state = {"remedies": {"data": {"date": "2026-11-08", "count": 3, "attempts": []}}}
    assert da.remedy_allowed(state, "data", "2026-11-09") is True  # 跨日歸零
    assert da.remedy_allowed({"remedies": {"data": {"date": TODAY, "count": 3}}}, "data", TODAY) is False
    assert da.remedy_allowed({"remedies": {"data": {"date": TODAY, "count": 2}}}, "data", TODAY) is True


def test_daily_remedy_dispatch_is_recorded_with_time_and_inputs():
    f = green_facts()
    f["runs"]["daily.yml"] = [run(conclusion="failure")]
    now = at("2026-11-09T19:00:00")
    calls = []

    def fake(wf, inputs):
        calls.append((wf, inputs))
        return True, "dispatched"

    items = da.evaluate(f, HOL, {"site": SITE_OK}, now)
    state: dict = {}
    da.run_remedies(items, state, TODAY, fake, runs=f["runs"], now=now)
    assert ("daily.yml", {"phase": "full"}) in calls
    att = state["remedies"]["data"]["attempts"][0]
    assert att["workflow"] == "daily.yml" and att["at"].startswith("2026-11-09T19:00:00")


# ---------------------------------------------------------------- 排程與文件綁在一起

def test_cron_has_1617_and_1717_trading_days():
    text = (ROOT / ".github" / "workflows" / "daily_audit.yml").read_text(encoding="utf-8")
    assert '"17 8 * * 1-5"' in text and '"17 9 * * 1-5"' in text
    # 15 8／15 9 會撞 daily.yml 的法人輪，不准用
    assert '"15 8 * * 1-5"' not in text and '"15 9 * * 1-5"' not in text


def test_facts_json_round_trip_is_plain():
    # render／寫檔用的結果必須能 json 化（寫進 daily_audit.json）
    f = green_facts()
    items = da.evaluate(f, HOL, {"site": SITE_OK}, at("2026-11-09T19:00:00"))
    json.dumps(items, ensure_ascii=False, default=str)


# ---------------------------------------------------------------- ETF（2026-11-09 Andy：ETF 資訊是否都有更新）
# 事故：11-06 的 full 輪被 pytest 擋掉，etf_pcf.holdings／etf.exright_notice 停在 11-05，
# 每日稽核只看價量法人融資券，所以 ETF 落後了三天沒人知道。下面的測試就是要把這種情況變紅。

def data_item(f, now):
    return by_id(da.evaluate(f, HOL, {"site": SITE_OK}, now))["data"]


def stale_etf_facts():
    """11-09 的事實，但 ETF 停在 11-05（etf 湖與 source_health 都停在前一天）。"""
    f = green_facts()
    f["lake"]["etf_holdings"] = "2026-11-05"
    f["source_health"]["etf_pcf.holdings"]["last_ok_date"] = "2026-11-05"
    f["source_health"]["etf.exright_notice"]["last_ok_date"] = "2026-11-05"
    for k in ("liguligu", "gh_pages"):
        f["screen"][k]["etf_asof"] = "2026-11-05"
        f["screen"][k]["etf_hold_asof"] = "2026-11-05"
    return f


def test_etf_stale_is_pending_before_deadline_and_red_after_2140():
    # 21:00 還沒到 21:40 截止：是還沒到，不紅
    assert data_item(stale_etf_facts(), at("2026-11-09T21:00:00"))["status"] == "pending"
    # 21:45 已過截止：紅，而且是 ETF 那幾關不過，補救是 daily.yml full
    it = data_item(stale_etf_facts(), at("2026-11-09T21:45:00"))
    assert it["status"] == "fail"
    for g in ("etf_hold", "etf_notice", "etf_screen"):
        assert it["gates"][g]["ok"] is False, g
    assert it["gates"]["etf_month"]["ok"] is True  # 月資料只落後 0 個月（11-05 落在 10 月）
    assert it["remedy"] == {"action": "dispatch", "workflow": "daily.yml", "inputs": {"phase": "full"}}


def test_etf_holdings_lake_current_but_health_stale_is_not_green():
    # 湖裡有 11-09 但來源紀錄停在 11-05：不准只看湖就綠
    f = green_facts()
    f["lake"]["etf_holdings"] = "2026-11-09"
    f["source_health"]["etf_pcf.holdings"]["last_ok_date"] = "2026-11-05"
    g = data_item(f, at("2026-11-09T21:45:00"))["gates"]["etf_hold"]
    assert g["ok"] is False and "2026-11-05" in g["why"]


def test_etf_holdings_t_plus_0_basis_rule():
    # 成分股基準日＝當天（10-08 實測）→ 應有日＝價量應有日。週一 08:00 的應有日是上週五，不是今天。
    assert da.expected_price_date(at("2026-11-09T08:00:00"), HOL).isoformat() == "2026-11-06"
    assert da.expected_price_date(at("2026-11-09T22:00:00"), HOL).isoformat() == "2026-11-09"
    # 週六查：應有日是週五（11-06），湖裡有 11-06 就綠，不會因為今天是週六就要求週六的資料
    f = green_facts(today="2026-11-07", expected="2026-11-06")
    f["lake"]["etf_holdings"] = "2026-11-06"
    f["source_health"]["etf_pcf.holdings"]["last_ok_date"] = "2026-11-06"
    assert data_item(f, at("2026-11-07T22:00:00"))["gates"]["etf_hold"]["ok"] is True
    f["lake"]["etf_holdings"] = "2026-11-05"
    assert data_item(f, at("2026-11-07T22:00:00"))["gates"]["etf_hold"]["ok"] is False


def test_etf_monthly_tolerates_one_month_only_and_never_reds_daily():
    f = green_facts()
    # 11-09 應有的完整月是 10 月；湖裡最新是 9 月底＝落後 1 個月，容許
    f["lake"]["etf_holdings_monthly"] = "2026-09-30"
    assert data_item(f, at("2026-11-09T22:00:00"))["gates"]["etf_month"]["ok"] is True
    # 落後 2 個月：紅
    f["lake"]["etf_holdings_monthly"] = "2026-08-31"
    it = data_item(f, at("2026-11-09T22:00:00"))
    assert it["gates"]["etf_month"]["ok"] is False and it["status"] == "fail"
    # 11-01 是週日：應有完整月＝9 月，湖裡 9 月底就是零落後
    f2 = green_facts(today="2026-11-01", expected="2026-10-30")
    f2["lake"]["etf_holdings_monthly"] = "2026-09-30"
    assert da.etf_monthly_gate("2026-09-30", "2026-11-01")["ok"] is True


def test_etf_monthly_unknown_is_not_green():
    g = da.etf_monthly_gate(None, TODAY)
    assert g["ok"] is False and "查不到" in g["why"]


def test_etf_notice_only_looks_at_health():
    # 除權息預告不看湖：湖的日期是除息日，不代表抓到了
    h = {"etf.exright_notice": {"last_ok_date": "2026-11-09"}}
    assert da.etf_notice_gate(h, TODAY)["ok"] is True
    assert da.etf_notice_gate({"etf.exright_notice": {"last_ok_date": "2026-11-06"}}, TODAY)["ok"] is False
    assert da.etf_notice_gate({}, TODAY)["ok"] is False   # 沒有紀錄＝沒有驗證過，不准綠
    assert da.etf_notice_gate(None, TODAY)["ok"] is False  # 讀不到 source_health＝查不到，不准綠


def test_etf_screen_mismatch_and_read_error_are_not_green():
    f = green_facts()
    f["screen"]["liguligu"]["etf_asof"] = "2026-11-06"   # 主站 ETF 頁還停在前一天
    it = data_item(f, at("2026-11-09T21:45:00"))
    g = it["gates"]["etf_screen"]
    assert g["ok"] is False and "主站" in g["why"] and "2026-11-06" in g["why"]
    assert it["status"] == "fail"
    f = green_facts()
    f["screen"]["gh_pages"]["etf_error"] = "HTTP 503"    # 讀不到 ≠ 綠
    assert da.etf_screen_gate(f["screen"], TODAY)["ok"] is False
    assert da.etf_screen_gate(None, TODAY)["ok"] is False


def test_etf_gate_none_when_lake_missing_becomes_red_after_deadline():
    f = green_facts()
    f["lake"]["etf_holdings"] = None   # 資料湖讀失敗
    it = data_item(f, at("2026-11-09T21:45:00"))
    assert it["gates"]["etf_hold"]["ok"] is False and "查不到" in it["gates"]["etf_hold"]["why"]
    assert it["status"] == "fail"
