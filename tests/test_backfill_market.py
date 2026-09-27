"""回補計畫的「全市場」範圍（2026-09-28）。

事故：三大法人、當沖＋借券、2009 起股利三步寫 scope=universe，那幾輪是手動觸發（limit 預設 500），
target_codes(500) 只給成交值前 500 檔 —— 三步都標成 done，資料湖卻只有 inst_daily 781 檔、
daytrade_daily 498 檔，前 500 名以外的個股頁照樣空白。

這裡守三件事：
  1. scope=market 取的是全市場上市＋上櫃普通股（不吃 limit、濾掉 ETF／權證／特別股／興櫃）；
  2. 新的完成鍵（…@market）不會被舊的 universe done 旗標擋住，已補過的個股也不會重抓；
  3. backfill.yml 的排程守門真的把新鍵納入（實際執行那段 Python，不是比對字串）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import config, run_backfill  # noqa: E402
from pipeline.util import http, store  # noqa: E402


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "state")
    (tmp_path / "data").mkdir()
    (tmp_path / "state").mkdir()
    monkeypatch.setattr(http, "_QUOTA_FILE", tmp_path / "state" / "finmind_quota.json")
    monkeypatch.setattr(run_backfill, "PROGRESS", tmp_path / "state" / "backfill_progress.json")
    run_backfill._cov_cache.clear()
    return tmp_path


def _price(rows):
    return pd.DataFrame([{"date": d, "code": c, "close": 1.0, "turnover": tv} for d, c, tv in rows])


# ------------------------------------------------------------------ 1. market scope 取碼

def test_market_scope_取全市場普通股_不吃limit_濾掉非普通股(sandbox, monkeypatch):
    store.append("price_daily", _price([
        ("2026-09-24", "2330", 900.0), ("2026-09-24", "0050", 800.0),    # ETF
        ("2026-09-24", "6488", 50.0), ("2026-09-24", "2881A", 40.0),     # 上櫃普通股／特別股
        ("2026-09-24", "030001", 30.0), ("2026-09-24", "1101", 100.0),   # 權證
        ("2026-09-24", "7777", 20.0),                                    # 興櫃（company_info 標 EMERGING）
        ("2026-09-15", "8888", 5.0),                                     # 最新一天停牌，但 30 天內有成交
        ("2026-06-01", "9999", 5.0),                                     # 早就沒成交（下市）→ 不花額度
    ]))
    store.append("company_info", pd.DataFrame({
        "code": ["2330", "6488", "1101", "7777", "8888"],
        "name": ["台積電", "環球晶", "台泥", "某興櫃", "停牌股"],
        "market": ["TWSE", "TPEX", "TWSE", "EMERGING", "TWSE"]}))
    # target_codes 的 limit 會把名單砍成 1 檔；market 不能受影響
    monkeypatch.setattr(run_backfill.loader, "membership", lambda cfg=None: pd.DataFrame(columns=["code"]))
    assert run_backfill._codes_for_scope("universe", 1) == ["2330"]
    codes = run_backfill._codes_for_scope("market", 1)
    assert codes == ["2330", "1101", "6488", "8888"], "成交值排序、停牌股接在後面、非普通股與興櫃都不收"


def test_計畫的法人_當沖借券_2009股利三步都是全市場():
    by = {(s["datasets"], s["start"]): s.get("scope") for s in run_backfill.PLAN_DEFAULT}
    assert by[("inst", "2016-01-01")] == "market"
    assert by[("daytrade+sbl", "2025-01-01")] == "market"
    assert by[("dividend+divresult", "2009-01-01")] == "market"


def test_market的完成鍵是新鍵_逐檔done鍵維持舊格式():
    k = run_backfill.datasets_key_of
    assert k("inst", "2016-01-01", scope="market") == "inst@market"
    assert k("daytrade+sbl", "2025-01-01", scope="market") == "daytrade+sbl@2025-01-01@market"
    assert k("dividend+divresult", "2009-01-01", scope="market") == "dividend+divresult@2009-01-01@market"
    assert k("inst", "2016-01-01", scope="universe") == "inst", "universe 步驟的鍵不能變（相容既有進度檔）"
    # 逐檔鍵不帶 scope：前 500 檔已補過的 inst:2330 在全市場那一步照樣命中、不重抓
    assert run_backfill.done_key_of("inst", "2330", "2016-01-01") == "inst:2330"


# ------------------------------------------------------------------ 2. 新鍵不被舊 done 擋

def test_舊的universe_done不擋全市場步驟_已補過的不重抓(sandbox, monkeypatch):
    store.append("price_daily", _price([("2026-09-24", c, tv) for c, tv in
                                        (("2330", 9.0), ("2454", 8.0), ("6488", 7.0), ("0050", 6.0))]))
    # 前 500 檔那一版：2330 已補過、旗標也標成 done
    run_backfill._save_progress({"done": {"inst:2330": True},
                                 "complete": {"inst": {"done": True, "codes": 500}}})
    # 只留全市場那一步（不接月更新步驟，那一步帶 tag、本來就會重抓）
    monkeypatch.setattr(run_backfill, "plan_steps", lambda name, today=None: [
        {"datasets": "inst", "start": "2016-01-01", "scope": "market"}])
    monkeypatch.setattr(run_backfill, "finmind_reachable", lambda prog: True)
    monkeypatch.setattr(run_backfill, "backfill_indices", lambda prog, *a, **k: True)
    monkeypatch.setattr(run_backfill, "backfill_index_intraday", lambda prog, *a, **k: True)
    monkeypatch.setattr(run_backfill, "refresh_stale_inst", lambda *a, **k: True)
    asked = []

    def fake(code, start, end=None, wait=False):
        asked.append((code, start))
        return pd.DataFrame({"date": ["2016-01-04"], "code": [code], "foreign": [1.0], "foreign_dealer": [0.0],
                             "foreign_total": [1.0], "trust": [0.0], "dealer_self": [0.0], "dealer_hedge": [0.0],
                             "dealer": [0.0], "inst_total": [1.0]})
    monkeypatch.setattr(run_backfill.finmind, "institutional", fake)

    run_backfill.run_plan("default", 500, today=date(2026, 9, 28))
    assert [c for c, _ in asked] == ["2454", "6488"], (
        "舊的 universe 旗標擋不住新步驟；已有逐檔 done 鍵的 2330 不重抓；ETF 不在全市場名單")
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["complete"]["inst@market"]["done"] is True
    assert prog["complete"]["plan:default"]["steps"]["inst@market"] is True


# ------------------------------------------------------------------ 3. 每日續補：全市場＋每日上限

def test_每日續補改全市場且依上限挑落後最久的(sandbox, monkeypatch):
    store.append("price_daily", _price([("2026-09-24", c, tv) for c, tv in
                                        (("2330", 9.0), ("2454", 8.0), ("6488", 7.0), ("1101", 6.0))]))
    store.append("inst_daily", pd.DataFrame({
        "date": ["2026-09-24", "2026-09-22", "2026-09-10", "2026-09-18"],
        "code": ["2330", "2454", "6488", "1101"], "foreign": [1.0] * 4}))
    monkeypatch.setattr(run_backfill, "FRESH_TABLES", (("inst", "inst_daily", 2),))
    # 舊實作走 target_codes(limit)；新實作不能再用它（手動觸發 limit=500 時只剩前 500 檔）
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: pytest.fail("續補不該再用 target_codes"))
    asked = []

    def fake(code, start, end=None, wait=False):
        asked.append((code, start))
        return pd.DataFrame({"date": ["2026-09-24"], "code": [code], "foreign": [5.0], "foreign_dealer": [0.0],
                             "foreign_total": [5.0], "trust": [0.0], "dealer_self": [0.0], "dealer_hedge": [0.0],
                             "dealer": [0.0], "inst_total": [5.0]})
    monkeypatch.setattr(run_backfill.finmind, "institutional", fake)
    assert run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 9, 25), limit=1) is True
    # 上限 2 檔：落後最久的 6488（09-10）、1101（09-18）先補；2454 明天再輪
    assert [c for c, _ in asked] == ["6488", "1101"]
    assert {s for _, s in asked} == {"2026-09-10"}, "起始日往前拉到落後最久那檔的最後一天"


def test_續補起始日有上下限():
    assert run_backfill.fresh_start("2026-09-24", ["2026-09-22"]) == "2026-09-10", "平常往回 14 天"
    assert run_backfill.fresh_start("2026-09-24", ["2026-08-01"]) == "2026-08-01"
    assert run_backfill.fresh_start("2026-09-24", ["2025-01-01"]) == "2026-06-26", "最多往回 90 天"


def test_每日續補上限總量控制在額度內():
    total = sum(cap for _, _, cap in run_backfill.FRESH_TABLES)
    assert total <= 1500, "每小時約 510 次，續補一天最多吃 3 輪，其餘留給歷史回補"
    assert [k for k, _, _ in run_backfill.FRESH_TABLES][0] == "inst", "法人最優先"


# ------------------------------------------------------------------ 4. backfill.yml 守門納入新鍵

def _guard_script() -> str:
    text = (ROOT / ".github" / "workflows" / "backfill.yml").read_text(encoding="utf-8")
    m = re.search(r"id: guard\n\s+run: \|\n\s+python3 - <<'PY'[^\n]*\n(.*?)\n\s+PY\n", text, re.S)
    assert m, "backfill.yml 找不到守門那段 Python"
    return textwrap.dedent(m.group(1))


def _run_guard(tmp_path: Path, complete: dict) -> dict:
    st = tmp_path / "data" / "_state"
    st.mkdir(parents=True, exist_ok=True)
    (st / "backfill_progress.json").write_text(json.dumps({"done": {}, "complete": complete}))
    # Logo 補齊而且還沒到期，守門才會真的回「跳過」
    (st / "logo_progress.json").write_text(json.dumps({"done": True, "next_due": "2999-01-01"}))
    env = {**os.environ, "DATASETS": "plan", "GITHUB_EVENT_NAME": "schedule"}
    out = subprocess.run([sys.executable, "-c", _guard_script()], cwd=tmp_path, env=env,
                         capture_output=True, text=True, check=True).stdout
    return dict(line.split("=", 1) for line in out.strip().splitlines())


def _all_done_complete() -> dict:
    tp = datetime.now(timezone(timedelta(hours=8)))
    cp = {"plan:default": {"done": True, "month": tp.strftime("%Y-%m")},
          "index_intraday": {"done": True},
          "inst_fresh": {"done": True, "date": tp.strftime("%Y-%m-%d")},
          # 舊的 universe 旗標（前 500 檔那一版）
          "inst": {"done": True}, "daytrade+sbl@2025-01-01": {"done": True},
          "dividend+divresult@2009-01-01": {"done": True}}
    for s in run_backfill.PLAN_DEFAULT:
        if s.get("scope") == "market":
            cp[run_backfill.datasets_key_of(s["datasets"], s["start"], s.get("tag"), "market")] = {"done": True}
    return cp


def test_守門_全部補齊才跳過(tmp_path):
    assert _run_guard(tmp_path, _all_done_complete())["skip"] == "true"


@pytest.mark.parametrize("step", [s for s in run_backfill.PLAN_DEFAULT if s.get("scope") == "market"],
                         ids=lambda s: s["datasets"] + "@" + s["start"])
def test_守門_全市場步驟沒補完就放行(tmp_path, step):
    """每一個 scope=market 步驟的新鍵都要被守門看到；只有舊的 universe 旗標是 done 不能算補齊。"""
    cp = _all_done_complete()
    cp.pop(run_backfill.datasets_key_of(step["datasets"], step["start"], step.get("tag"), "market"))
    assert _run_guard(tmp_path, cp)["skip"] == "false"
