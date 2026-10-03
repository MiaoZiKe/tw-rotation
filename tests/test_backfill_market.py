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
    # 2026-10-03（DECISIONS #311）：順序改成當沖 → 借券 → 上櫃融資券 → 法人。
    #   當沖／借券沒有任何每日來源；法人前 500 名由每日管線顧好。法人的保底份額見 FRESH_SHARE。
    assert [k for k, _, _ in run_backfill.FRESH_TABLES][:2] == ["daytrade", "sbl"], "當沖、借券最優先"


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
    from pipeline import config as cfg
    (st / "logo_progress.json").write_text(json.dumps({"done": True, "next_due": "2999-01-01",
                                                       "strategy": cfg.LOGO_STRATEGY}))
    env = {**os.environ, "DATASETS": "plan", "GITHUB_EVENT_NAME": "schedule"}
    out = subprocess.run([sys.executable, "-c", _guard_script()], cwd=tmp_path, env=env,
                         capture_output=True, text=True, check=True).stdout
    return dict(line.split("=", 1) for line in out.strip().splitlines())


def _all_done_complete() -> dict:
    tp = datetime.now(timezone(timedelta(hours=8)))
    cp = {"plan:default": {"done": True, "month": tp.strftime("%Y-%m")},
          # 2026-09-28：大盤分 K 多了櫃買 IX0043.TWO（yahoo_v 3）與加權真實 1 分 K（tse1m_v 1）兩個版本鍵
          "index_intraday": {"done": True, "yahoo_v": 3, "tse1m_v": 1},
          "inst_fresh": {"done": True, "date": tp.strftime("%Y-%m-%d")},
          # 舊的 universe 旗標（前 500 檔那一版）
          "inst": {"done": True}, "daytrade+sbl@2025-01-01": {"done": True},
          "dividend+divresult@2009-01-01": {"done": True},
          # 2026-09-30：個股 60 分 K 全市場回補（Yahoo，不在 PLAN_DEFAULT 裡，守門另外看）
          "intraday_60m": {"done": True, "remaining": {"intraday_60m": 0}}}
    for s in run_backfill.PLAN_DEFAULT:
        if s.get("scope") == "market":
            cp[run_backfill.datasets_key_of(s["datasets"], s["start"], s.get("tag"), "market")] = {"done": True}
    return cp


def test_守門_全部補齊才跳過(tmp_path):
    assert _run_guard(tmp_path, _all_done_complete())["skip"] == "true"


def test_守門_大盤分K舊版進度要放行(tmp_path):
    """舊進度的 index_intraday done 不涵蓋 IX0043.TWO 與加權真實 1 分 K —— 版本對不上就放行一輪。"""
    cp = _all_done_complete()
    cp["index_intraday"] = {"done": True, "yahoo_v": 2}
    assert _run_guard(tmp_path, cp)["skip"] == "false"


@pytest.mark.parametrize("step", [s for s in run_backfill.PLAN_DEFAULT if s.get("scope") == "market"],
                         ids=lambda s: s["datasets"] + "@" + s["start"])
def test_守門_全市場步驟沒補完就放行(tmp_path, step):
    """每一個 scope=market 步驟的新鍵都要被守門看到；只有舊的 universe 旗標是 done 不能算補齊。"""
    cp = _all_done_complete()
    cp.pop(run_backfill.datasets_key_of(step["datasets"], step["start"], step.get("tag"), "market"))
    assert _run_guard(tmp_path, cp)["skip"] == "false"


def test_守門_個股60分K沒補完要放行且只跑intraday(tmp_path):
    """計畫補齊之後才加的 60 分 K 全市場回補：complete.intraday_60m 不是 done → 放行一輪，只跑 `--datasets intraday`
    （不碰 FinMind）；補完才跳過。沒有這個鍵（第一次上線）也要放行。"""
    cp = _all_done_complete()
    cp["intraday_60m"] = {"done": False, "remaining": {"intraday_60m": 1413}}
    got = _run_guard(tmp_path, cp)
    assert got["skip"] == "false" and got["intraday_only"] == "true" and got["logos_only"] == "false"
    cp.pop("intraday_60m")
    assert _run_guard(tmp_path, cp)["intraday_only"] == "true"
    cp["intraday_60m"] = {"done": True}
    got = _run_guard(tmp_path, cp)
    assert got["skip"] == "true" and got["intraday_only"] == "false"


def test_守門_計畫沒補齊時不另外標intraday_only(tmp_path):
    """計畫還在跑（--plan default 那一輪本來就會先補 60 分 K），不必另外切成只跑 intraday。"""
    cp = _all_done_complete()
    cp["plan:default"]["done"] = False
    cp["intraday_60m"] = {"done": False}
    got = _run_guard(tmp_path, cp)
    assert got["skip"] == "false" and got["intraday_only"] == "false"


def test_守門_Logo策略升級或人工Logo要放行(tmp_path):
    """Logo 第四版（DECISIONS #276）：狀態檔寫著補齊，但 LOGO_STRATEGY 跟狀態檔的版號不同 → 放行一輪 logos；
    版號相同就照舊跳過；data/logos/manual/ 多一張索引沒記的人工 Logo → 也放行。"""
    from pipeline import config as cfg
    (tmp_path / "pipeline").mkdir()
    (tmp_path / "pipeline" / "config.py").write_text(f"LOGO_STRATEGY = {cfg.LOGO_STRATEGY}\n", encoding="utf-8")
    assert _run_guard(tmp_path, _all_done_complete())["skip"] == "true"   # 版號對上、沒有人工檔 → 跳過
    lp = tmp_path / "data" / "_state" / "logo_progress.json"
    env = {**os.environ, "DATASETS": "plan", "GITHUB_EVENT_NAME": "schedule"}

    def guard():
        out = subprocess.run([sys.executable, "-c", _guard_script()], cwd=tmp_path, env=env,
                             capture_output=True, text=True, check=True).stdout
        return dict(line.split("=", 1) for line in out.strip().splitlines())
    lp.write_text(json.dumps({"done": True, "next_due": "2999-01-01", "strategy": cfg.LOGO_STRATEGY - 1}))
    got = guard()                                                     # 狀態檔是舊版策略寫的 → 放行
    assert got["skip"] == "false" and got["logos_only"] == "true"
    lp.write_text(json.dumps({"done": True, "next_due": "2999-01-01", "strategy": cfg.LOGO_STRATEGY}))
    assert guard()["skip"] == "true"
    md = tmp_path / "data" / "logos" / "manual"
    md.mkdir(parents=True)
    (md / "8038.png").write_bytes(b"fake")
    got = guard()
    assert got["skip"] == "false" and got["logos_only"] == "true"


# ------------------------------------------------------------------ 5. 2009 股利全市場步驟的完成判定（2026-09-28）
# 誤判事件：dividend+divresult@2009-01-01@market 連續十幾輪 done=False、stopped_at 一直停在這一步，
# 被當成「卡住、永遠不會完成」。實際上 2009 那一步的逐檔鍵是 `dividend@2009-01-01:<代號>`
# （00:49 的 500 → 15:34 的 1,928，每輪約 +250），`dividend:<代號>` 是 2016 那一步的鍵（2,338 個，
# 跟這一步無關）；每一輪都在前進，只是都撞到 FinMind 伺服器端額度上限才停。這一組守三件事：
#   ① 2016 那一步的鍵不會被當成 2009 這一步補過；
#   ② 額度用盡時 done=False，但旗標寫出「還剩幾檔」；下一輪從沒補的接續、不重抓；
#   ③ 額度還在、上游回空 → 記成「確認無資料」（NO_DATA，仍是真值會跳過），
#      名單全部處理過才 done=True；確認無資料的檔也算「股利補到 2009」。

def _div_events(code):
    return pd.DataFrame({"code": [code], "period": ["2009"], "kind": ["cash"],
                         "announce_date": ["2009-06-01"], "cash": [1.0]})


def _div_results(code):
    return pd.DataFrame({"code": [code], "date": ["2009-07-01"], "cash": [1.0]})


def _div_sandbox(monkeypatch, codes):
    store.append("price_daily", _price([("2026-09-24", c, float(100 - i)) for i, c in enumerate(codes)]))
    monkeypatch.setattr(run_backfill, "plan_steps", lambda name, today=None: [
        {"datasets": "dividend+divresult", "start": "2009-01-01", "scope": "market"}])
    monkeypatch.setattr(run_backfill, "finmind_reachable", lambda prog: True)
    monkeypatch.setattr(run_backfill, "backfill_indices", lambda prog, *a, **k: True)
    monkeypatch.setattr(run_backfill, "backfill_index_intraday", lambda prog, *a, **k: True)
    monkeypatch.setattr(run_backfill, "refresh_stale_inst", lambda *a, **k: True)


def test_2009股利步驟_額度用盡記剩幾檔_下一輪接續到done(sandbox, monkeypatch):
    codes = ["2330", "2454", "2317", "1101", "6488", "8888"]
    _div_sandbox(monkeypatch, codes)
    # 2016 那一步的鍵全部都有（就是誤判時看到的那 2,338 個）—— 不能讓 2009 這一步跳過
    run_backfill._save_progress({"done": {**{f"dividend:{c}": True for c in codes},
                                          **{f"divresult:{c}": True for c in codes}},
                                 "complete": {}})
    key = "dividend+divresult@2009-01-01@market"
    asked: list[tuple[str, str]] = []
    budget = {"n": 5}      # 第一輪只給 5 次請求就撞到伺服器端上限（前一個 run 吃掉了同一小時的額度）

    def gate(kind, make):
        def fetch(code, start, wait=False):
            asked.append((kind, code))
            budget["n"] -= 1
            if budget["n"] < 0:
                http.finmind_mark_exhausted()       # 伺服器回 402：這一筆不能當成沒資料
                return pd.DataFrame()
            if code == "8888":
                return pd.DataFrame()               # 從沒配過股利：額度還在卻回空
            return make(code)
        return fetch

    monkeypatch.setattr(run_backfill.finmind, "dividend_events", gate("dividend", _div_events))
    monkeypatch.setattr(run_backfill.finmind, "dividend_results", gate("divresult", _div_results))

    r1 = run_backfill.run_plan("default", 500, today=date(2026, 9, 28))
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert asked[0] == ("dividend", "2330"), "2016 那一步的 dividend:<代號> 不可以擋住 2009 這一步"
    assert r1["stopped_at"] == key and r1["done"] is False
    st = prog["complete"][key]
    assert st["done"] is False
    # 5 次請求：2330、2454 兩個資料集都補到，2317 的 dividend 補到、divresult 那一筆撞上限
    assert st["remaining"] == {"dividend": 3, "divresult": 4}, st
    assert "divresult@2009-01-01:2317" not in prog["done"], "撞到上限的那一筆不能記成做過"

    # 第二輪：新的 Actions run，額度重新給足
    run_backfill._save_progress(prog)
    http._save_quota({"window_start": 0.0, "used": 0})
    budget["n"] = 999
    asked.clear()
    run_backfill._cov_cache.clear()
    r2 = run_backfill.run_plan("default", 500, today=date(2026, 9, 28))
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert asked[0] == ("divresult", "2317"), "從上一輪停下的那一筆接續，補過的不重抓"
    assert ("dividend", "2330") not in asked and ("dividend", "2317") not in asked
    st = prog["complete"][key]
    assert st["done"] is True and r2["stopped_at"] is None, st
    assert st["remaining"] == {"dividend": 0, "divresult": 0}
    assert prog["complete"]["plan:default"]["done"] is True
    # 8888 是「確認無資料」，不是「補到了」；但仍是真值，下一輪不再問
    assert prog["done"]["dividend@2009-01-01:8888"] == run_backfill.NO_DATA
    assert prog["done"]["divresult@2009-01-01:8888"] == run_backfill.NO_DATA
    assert prog["done"]["dividend@2009-01-01:2330"] is True
    assert st["no_data"] == {"dividend": 1, "divresult": 1}

    # 第三輪：全部跳過、一次請求都不花、旗標維持 done
    asked.clear()
    run_backfill._cov_cache.clear()
    run_backfill.run_plan("default", 500, today=date(2026, 9, 28))
    assert asked == []
    assert json.loads(run_backfill.PROGRESS.read_text())["complete"][key]["done"] is True


def test_確認無資料的股票也算股利補到2009(sandbox):
    """年度股利圖依 divresult@2009-01-01:<代號> 決定從哪年畫起：回空＝查過、確認沒配，也算補到 2009。"""
    from pipeline import build_payload
    run_backfill._save_progress({"done": {"divresult@2009-01-01:2330": True,
                                          "divresult@2009-01-01:8888": run_backfill.NO_DATA,
                                          "divresult:1101": True}, "complete": {}})
    assert build_payload.dividend_cover_years() == {"2330": 2009, "8888": 2009}


def test_執行摘要分開列確認無資料與還剩幾檔(tmp_path):
    """backfill.yml「執行摘要」那段 Python 真的跑一次：前綴分開、no_data 另計、未補齊的步驟寫剩幾檔。"""
    text = (ROOT / ".github" / "workflows" / "backfill.yml").read_text(encoding="utf-8")
    m = re.search(r"name: 執行摘要\n.*?python3 - <<'PY'\n(.*?)\n\s+PY\n", text, re.S)
    assert m, "backfill.yml 找不到執行摘要那段 Python"
    st = tmp_path / "data" / "_state"
    st.mkdir(parents=True)
    (st / "backfill_progress.json").write_text(json.dumps({
        "done": {"dividend:2330": True, "dividend@2009-01-01:2330": True,
                 "dividend@2009-01-01:8888": "no_data"},
        "complete": {"dividend+divresult@2009-01-01@market": {
            "done": False, "remaining": {"dividend": 79, "divresult": 80}}}}))
    out = subprocess.run([sys.executable, "-c", textwrap.dedent(m.group(1))], cwd=tmp_path,
                         capture_output=True, text=True, check=True).stdout
    assert "dividend 1、dividend@2009-01-01 2（1）" in out, out
    assert "還剩 {'dividend': 79, 'divresult': 80}" in out, out
