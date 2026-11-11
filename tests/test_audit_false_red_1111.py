"""每日稽核假紅修復（2026-11-11）。

五類假紅的共同病根：判定用了「不是真失敗」的訊號當失敗。
- optivx.daily：湖已到今天（窗內已處理）→ 來源回空但沒宣告 skipped → 被記成失敗 → 連續兩天紅。
- 主站 403：GitHub 執行環境讀不到 liguligu-puipui.com，但 CF 部署紀錄已含最新資料，判定不該只看這一個讀取。
- ETF：湖的基準日是真相，source_health 的日期鍵（trade_date）慢一個交易日，不能拿來當「最後成功日」的硬門檻。
- 權杖：未設定（missing）是未啟用、不是壞；即時驗證失敗（check-fail）即使剩 59 天也是真紅，但要講清楚原因。
"""
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.sources import optivx  # noqa: E402

_spec = importlib.util.spec_from_file_location("daily_audit", ROOT / "scripts" / "daily_audit.py")
da = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(da)

HOL = set()
EXP = "2026-11-10"


# ---------------------------------------------------------------- optivx
def test_optivx_already_up_to_date_is_skipped_not_failure():
    # 湖最後一天＝今天：start 會比 today 晚一天，不打 API；必須宣告 skipped，run_daily 才會記成 ok
    calls = []
    out = optivx.daily_update(today=date(2026, 11, 10), fetch=lambda s, e: calls.append(1) or [],
                              last="2026-11-10")
    assert out.empty and calls == []
    assert "skipped" in out.attrs and "已到" in out.attrs["skipped"]
    assert "error" not in out.attrs


# ---------------------------------------------------------------- 主站 403
def _screen(main_status=None, main_ok=True, back_ok=True):
    main = {"data_date": EXP, "inst_date": EXP, "inst_market_latest": EXP, "error": None,
            "http_status": None}
    if not main_ok:
        main = {"data_date": None, "inst_date": None, "inst_market_latest": None,
                "error": "HTTP Error 403: Forbidden", "http_status": main_status}
    back = {"data_date": EXP, "inst_date": EXP, "inst_market_latest": EXP, "error": None}
    if not back_ok:
        back["data_date"] = "2026-11-09"
    return {"liguligu": main, "gh_pages": back}


def test_main_403_passes_when_cf_deploy_has_latest_and_backup_matches():
    g = da.screen_gate(_screen(403, main_ok=False), EXP, cf_ok=True)
    assert g["ok"] is True and "Cloudflare" in g["why"]


def test_main_403_without_cf_proof_is_still_red():
    g = da.screen_gate(_screen(403, main_ok=False), EXP, cf_ok=False)
    assert g["ok"] is False


def test_main_403_but_backup_stale_is_red():
    g = da.screen_gate(_screen(403, main_ok=False, back_ok=False), EXP, cf_ok=True)
    assert g["ok"] is False and "備援" in g["why"]


def test_main_other_error_is_red_even_with_cf_proof():
    # 逾時、5xx 不是「讀不到權限」，不能用 CF 部署紀錄蓋掉
    s = _screen(500, main_ok=False)
    s["liguligu"]["http_status"] = 500
    assert da.screen_gate(s, EXP, cf_ok=True)["ok"] is False


def test_collect_screen_keeps_http_status_on_403():
    class E403(Exception):
        code = 403

    def fake(url):
        if "liguligu" in url:
            raise E403("HTTP Error 403: Forbidden")
        if url.endswith("meta.json"):
            return {"data_date": EXP, "inst_date": EXP}
        return {"latest": EXP}

    out = da.collect_screen(fake)
    assert out["liguligu"]["http_status"] == 403 and out["liguligu"]["error"]
    assert out["gh_pages"]["http_status"] is None and out["gh_pages"]["error"] is None


def test_etf_screen_main_403_uses_cf_proof():
    class E403(Exception):
        code = 403

    scr = {"liguligu": {"etf_asof": None, "etf_hold_asof": None, "etf_error": "403", "etf_http_status": 403},
           "gh_pages": {"etf_asof": EXP, "etf_hold_asof": EXP, "etf_error": None}}
    assert da.etf_screen_gate(scr, EXP, cf_ok=True)["ok"] is True
    assert da.etf_screen_gate(scr, EXP, cf_ok=False)["ok"] is False


# ---------------------------------------------------------------- ETF 口徑
def test_etf_notice_tolerates_one_trading_day_lag_of_day_key():
    h = {"etf.exright_notice": {"last_ok_date": "2026-11-09", "consecutive_fail": 0}}
    assert da.etf_notice_gate(h, EXP, prev_s="2026-11-09")["ok"] is True
    # 容忍的是「慢一個交易日」，不是放任兩天沒成功
    h["etf.exright_notice"]["last_ok_date"] = "2026-11-06"
    assert da.etf_notice_gate(h, EXP, prev_s="2026-11-09")["ok"] is False


def test_etf_notice_consecutive_fail_is_red_even_if_date_fresh():
    h = {"etf.exright_notice": {"last_ok_date": "2026-11-10", "consecutive_fail": da.SOURCE_FAIL_RED}}
    assert da.etf_notice_gate(h, EXP, prev_s="2026-11-09")["ok"] is False


# ---------------------------------------------------------------- 權杖（走真的 evaluate，不另抄一份判定）
_T = importlib.util.spec_from_file_location("tda", ROOT / "tests" / "test_daily_audit.py")
tda = importlib.util.module_from_spec(_T)
_T.loader.exec_module(tda)


def _meta_content(platforms):
    f = tda.green_facts()
    f["meta"] = {"updated_at": "2026-11-10T08:52:22+00:00", "platforms": platforms}
    items = {it["id"]: it for it in da.evaluate(f, tda.HOL, {"site": tda.SITE_OK}, tda.at("2026-11-09T19:00:00"))}
    return items["meta"]["gates"]["content"]


def test_meta_missing_secret_is_not_red():
    g = _meta_content({"tc_threads": {"ok": False, "status": "missing", "days_left": None},
                       "healing_ig": {"ok": True, "status": "fb-no-secret", "days_left": None}})
    assert g["ok"] is True and "tc_threads" in g["why"]


def test_meta_check_fail_is_red_and_says_live_check_failed():
    # 剩 59 天但即時驗證失敗＝真紅（發文會失敗），不是判定邏輯錯；原因要寫清楚
    g = _meta_content({"healing_threads": {"ok": False, "status": "check-fail", "days_left": 59.3}})
    assert g["ok"] is False and "即時驗證失敗" in g["why"]
