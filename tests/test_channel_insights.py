"""多頻道每日成效收集（scripts/channel_insights.py）的測試。全部用假的 HTTP，不連網。

重點驗：權限不足不會讓整輪失敗（記下缺哪個權限）、沒權杖就不呼叫任何端點、
只讀自己頻道的權杖、同一天重跑不重複列、檔案裡不會出現權杖或完整帳號編號、工作流的 Secrets 只帶自己前綴。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import channel_insights as CI  # noqa: E402
import healing_post as HP  # noqa: E402

TAIPEI = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 9, 23, 23, tzinfo=TAIPEI)
IG_TOKEN = "EAAFAKE_IG_TOKEN_0123456789"
TH_TOKEN = "THFAKE_THREADS_TOKEN_abc"
UID = "17841400123456789"   # 17 位帳號編號：檔案裡不准出現


def _state(tmp_path: Path, posted: dict) -> Path:
    st = tmp_path / "state"
    st.mkdir(parents=True, exist_ok=True)
    (st / "posted.json").write_text(json.dumps(posted, ensure_ascii=False), encoding="utf-8")
    return st


@pytest.fixture
def chan(tmp_path, monkeypatch):
    """假的頻道設定：TECH_ 前綴、兩則已發貼文（IG 與 Threads 各一）。"""
    st = _state(tmp_path, {
        "20261108_a": {"ig": {"id": "ig111", "at": "2026-11-08T12:17+08:00", "link": "x"},
                       "threads": {"id": "th111", "at": "2026-11-08T12:17+08:00"}},
    })
    cfg = {"code": "tech", "prefix": "TECH_", "account": "Tech_01010909", "state": st,
           "queue": tmp_path / "queue", "quota": tmp_path / "q.json", "per_day": 1}
    monkeypatch.setattr(HP, "channel", lambda code, path=None: cfg)
    monkeypatch.setattr(HP, "resolve_uid", lambda p, env_id, token, prefix=None, prefer_via="": UID)
    return cfg


def _ok(data):
    return True, data


def _err(code, msg):
    return False, {"code": code, "message": msg}


def _insight(name, value):
    return {"name": name, "values": [{"value": value}]}


def make_get(routes):
    """routes：[(判斷函式(url, params), 回應)]；沒有命中的一律回「不支援」，並記下每一次呼叫。"""
    calls = []

    def get(url, params):
        calls.append((url, dict(params)))
        for pred, resp in routes:
            if pred(url, params):
                return resp(params) if callable(resp) else resp
        return _err(100, "Unsupported get request")

    return get, calls


def _ig_routes(insights_resp):
    return [
        (lambda u, p: u.endswith(f"/{UID}") and "followers_count" in p.get("fields", ""), _ok({"followers_count": 321})),
        (lambda u, p: u.endswith(f"/{UID}/insights"), insights_resp),
        (lambda u, p: u.endswith("/ig111") and "like_count" in p.get("fields", ""),
         _ok({"like_count": 7, "comments_count": 2})),
        (lambda u, p: u.endswith("/ig111/insights"), _err(10, "(#10) Application does not have permission")),
    ]


def _env():
    return {"TECH_IG_ACCESS_TOKEN_AUTO": IG_TOKEN, "TECH_THREADS_ACCESS_TOKEN": TH_TOKEN}


# ---------- 錯誤分類與指標拿取 ----------
@pytest.mark.parametrize("err,kind", [
    ({"code": 190, "message": "Session has expired"}, "token_invalid"),
    ({"code": 10, "message": "(#10) Application does not have permission"}, "permission"),
    ({"code": 200, "message": "requires instagram_manage_insights"}, "permission"),
    ({"code": 100, "message": "Unsupported get request"}, "unsupported"),
    ({"code": 4, "message": "Application request limit reached"}, "rate_limit"),
    ({"code": 1, "message": "something else"}, "error"),
])
def test_classify(err, kind):
    assert CI.classify(err) == kind


def test_fetch_insights_falls_back_per_metric_and_records_permission_gap():
    def insights_one_by_one(params):
        m = params["metric"]
        return _ok({"data": [_insight(m, 11)]}) if m == "views" else _err(10, "no permission")

    get, calls = make_get([
        (lambda u, p: "," in p["metric"], _err(10, "combined failed")),
        (lambda u, p: True, insights_one_by_one),
    ])
    got, miss = CI.fetch_insights(get, "https://x/1/insights", "t", ["views", "reach"])
    assert got == {"views": 11}
    assert miss == {"reach": {"kind": "permission", "message": "no permission"}}
    assert len(calls) == 3   # 1 次合併＋2 次逐一


def test_vals_uses_total_value_and_last_series_point():
    d = {"data": [{"name": "reach", "total_value": {"value": 5}},
                  {"name": "views", "values": [{"value": 1}, {"value": 9}]}]}
    assert CI.vals(d) == {"reach": 5, "views": 9}


# ---------- 一個頻道的整輪 ----------
def test_ig_permission_gap_is_partial_not_error(chan):
    get, _ = make_get(_ig_routes(_err(10, "(#10) Application does not have permission")))
    rep = CI.run_channel("tech", _env(), NOW, get=get)
    ig = rep["platforms"]["ig"]
    assert ig["status"] == "partial"
    assert ig["need_permission"] == "instagram_manage_insights"
    assert ig["account_values"]["followers"] == 321
    assert ig["posts_total"] == 1 and ig["posts_with_data"] == 1   # like_count 拿到了
    assert "views" in ig["missing"]
    assert ig.get("last_success")


def test_no_token_means_no_network_calls(chan):
    get, calls = make_get([])
    rep = CI.run_channel("tech", {}, NOW, get=get)
    assert calls == []
    assert rep["platforms"]["ig"]["status"] == "no_token"
    assert rep["platforms"]["threads"]["status"] == "no_token"


def test_channel_reads_only_its_own_prefix(chan):
    get, calls = make_get([])
    env = {"HEALING_IG_ACCESS_TOKEN_AUTO": "EAAOTHER_HEALING_TOKEN_999"}
    rep = CI.run_channel("tech", env, NOW, get=get)
    assert calls == []
    assert rep["platforms"]["ig"]["status"] == "no_token"


def test_threads_full_ok_and_files_contain_no_secrets(chan):
    routes = [
        (lambda u, p: u.endswith("/me/threads_insights") and p.get("metric") == "followers_count",
         _ok({"data": [_insight("followers_count", 88)]})),
        (lambda u, p: u.endswith("/me/threads_insights"),
         _ok({"data": [{"name": "views", "values": [{"value": 40}]}, {"name": "likes", "values": [{"value": 3}]}]})),
        (lambda u, p: u.endswith("/th111/insights"),
         _ok({"data": [_insight("views", 12), _insight("likes", 1), _insight("replies", 0),
                       _insight("reposts", 0), _insight("quotes", 0), _insight("shares", 0)]})),
        (lambda u, p: u.endswith("/ig111/insights") or u.endswith(f"/{UID}") or u.endswith(f"/{UID}/insights"),
         _err(10, "no")),
    ]
    get, _ = make_get(routes)
    rep = CI.run_channel("tech", _env(), NOW, get=get)
    th = rep["platforms"]["threads"]
    assert th["status"] == "ok"
    assert th["account_values"]["followers"] == 88
    assert th["posts_with_data"] == 1
    out = Path(chan["state"]) / "insights"
    text = "".join(p.read_text(encoding="utf-8") for p in out.iterdir() if p.is_file())
    assert IG_TOKEN not in text and TH_TOKEN not in text and UID not in text
    assert "th111" in (out / "posts_daily.csv").read_text(encoding="utf-8")


def test_same_day_rerun_replaces_row_and_new_day_appends(chan):
    get, _ = make_get(_ig_routes(_err(10, "no permission")))
    CI.run_channel("tech", _env(), NOW, get=get)
    CI.run_channel("tech", _env(), NOW, get=get)
    f = Path(chan["state"]) / "insights" / "account_daily.csv"
    rows = f.read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 1 + 2   # 表頭＋IG 一列＋Threads 一列（兩個平台都有權杖）
    CI.run_channel("tech", _env(), NOW + timedelta(days=1), get=get)
    assert len(f.read_text(encoding="utf-8").strip().splitlines()) == 1 + 4


def test_last_run_json_keeps_last_success_when_today_fails(chan):
    ok_get, _ = make_get(_ig_routes(_ok({"data": [_insight("views", 1)]})))
    CI.run_channel("tech", _env(), NOW, get=ok_get)
    first = json.loads((Path(chan["state"]) / "insights" / "last_run.json").read_text(encoding="utf-8"))
    bad_get, _ = make_get([(lambda u, p: True, _err(190, "Session has expired"))])
    rep = CI.run_channel("tech", _env(), NOW + timedelta(days=1), get=bad_get)
    ig = rep["platforms"]["ig"]
    assert ig["status"] in ("token_invalid", "error")
    assert ig["last_success"] == first["platforms"]["ig"]["last_success"]


def test_clean_redacts_token_and_long_numbers():
    HP.mask(IG_TOKEN)
    s = CI._clean(f"bad token {IG_TOKEN} for object 17841400123456789")
    assert IG_TOKEN not in s and "17841400123456789" not in s


def test_render_is_traditional_table_without_secrets(chan):
    get, _ = make_get(_ig_routes(_err(10, "no")))
    rep = CI.run_channel("tech", _env(), NOW, get=get)
    md = CI.render(rep)
    assert "instagram_manage_insights" in md
    assert IG_TOKEN not in md and UID not in md


# ---------- 工作流 ----------
def test_workflow_schedule_and_secret_scoping():
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "channel_insights.yml").read_text(encoding="utf-8"))
    # PyYAML 把 key "on" 讀成布林 True
    trig = wf.get(True) or wf.get("on")
    cron = trig["schedule"][0]["cron"]
    minute, hour = cron.split()[:2]
    assert hour == "15" and minute not in ("0", "00")           # 台北 23:xx（UTC 15:xx），不在整點
    assert wf["jobs"]["insights"]["strategy"]["matrix"]["channel"] == ["healing", "tech", "caffaine"]
    env = wf["jobs"]["insights"]["env"]
    for key, val in env.items():
        prefix = key.split("_")[0]
        if key.startswith(("HEALING_", "TECH_", "CAFFAINE_")):
            want = {"HEALING": "healing", "TECH": "tech", "CAFFAINE": "caffaine"}[prefix]
            assert f"matrix.channel == '{want}'" in val, key
    text = (ROOT / ".github" / "workflows" / "channel_insights.yml").read_text(encoding="utf-8")
    assert "secrets.IG_ACCESS_TOKEN" not in text and "secrets.THREADS_ACCESS_TOKEN" not in text   # 不碰頻道①
    assert "concurrency" in wf["jobs"]["insights"]
