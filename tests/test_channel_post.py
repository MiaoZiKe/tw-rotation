"""多頻道自動發文（scripts/channel_post.py＋healing_post.py 的 prefix）：設定讀取、權杖前綴隔離、各頻道不重發、
shrimp live=false 略過、缺權杖空跑、排程與 channels.json 一致、留言私訊多頻道、續期多頻道與短效換長效。"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts import channel_post as cp
from scripts import healing_comments as hc
from scripts import healing_post as hp
from scripts import meta_token_refresh as mtr

ROOT = Path(__file__).resolve().parents[1]
TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 12, 12, 20, tzinfo=TPE)
CODES = {"healing": "HEALING_", "tech": "TECH_", "shrimp": "SHRIMP_", "caffaine": "CAFFAINE_"}
ALL_ENV = {}
for _c, _p in CODES.items():
    ALL_ENV[f"{_p}IG_ACCESS_TOKEN"] = f"IGTOK_{_c}_xxxxxxxxxxxx"
    ALL_ENV[f"{_p}THREADS_ACCESS_TOKEN"] = f"THTOK_{_c}_xxxxxxxxxxxx"
    ALL_ENV[f"{_p}IG_USER_ID"] = f"77{len(_c)}1"
    ALL_ENV[f"{_p}THREADS_USER_ID"] = f"77{len(_c)}2"
ALL_ENV.update(IG_ACCESS_TOKEN="CH1_IG_TOKEN_zzzzzz", THREADS_ACCESS_TOKEN="CH1_TH_TOKEN_zzzzzz",
               TC_IG_ACCESS_TOKEN="TC_IG_zzzzzz", TC_THREADS_ACCESS_TOKEN="TC_TH_zzzzzz")


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    hp.SP._SECRETS.clear()
    mtr._SECRETS.clear()
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)


# ---------- 設定 ----------
def test_channels_json四個頻道與資料夾開關():
    chs = hp.load_channels()
    assert {k: v["prefix"] for k, v in chs.items()} == CODES
    for code, c in chs.items():
        assert c["queue"].is_dir() and c["state"].is_dir() and c["quota"].is_file(), code
        assert c["per_day"] == 1
        assert c["queue"] == ROOT / f"docs/marketing/channels/{code}/queue"
    q = {k: json.loads(v["quota"].read_text(encoding="utf-8")) for k, v in chs.items()}
    assert q["tech"]["live"] is True and q["caffaine"]["live"] is True
    assert q["shrimp"]["live"] is False, "水下蝦米還在用 Buffer，切換前不准開"
    assert all(x["per_day"] == 1 for x in q.values())
    # 頻道④首篇仍在佇列
    assert (chs["healing"]["queue"] / "20261108_intro" / "1.png").exists()


def _utc_cron(hhmm: str) -> str:
    h, m = map(int, hhmm.split(":"))
    return f"{m} {(h - 8) % 24} * * *"


def test_時段_cron與工作流一致且避開整點():
    chs = hp.load_channels()
    wf = {}
    for f in ("healing_post.yml", "channel_post.yml"):
        d = yaml.safe_load((ROOT / ".github/workflows" / f).read_text(encoding="utf-8"))
        wf[f] = {x["cron"] for x in d[True]["schedule"]}        # yaml 把 on 讀成 True
    mine = {"healing_post.yml": set(), "channel_post.yml": set()}
    slots = []
    for code, c in chs.items():
        assert c["cron"] == [_utc_cron(c["slot"]), _utc_cron(c["backup"])], code
        assert not c["slot"].endswith(":00") and not c["slot"].endswith(":30")
        mine[c["workflow"]] |= set(c["cron"])
        slots.append(c["slot"])
    assert mine == wf
    assert len(set(slots)) == 4


def test_plan排程只挑那個頻道_手動all不含healing():
    assert cp.plan("17 4 * * *") == [{"channel": "tech", "prefix": "TECH_"}]
    assert cp.plan("43 0 * * *") == [{"channel": "shrimp", "prefix": "SHRIMP_"}]
    assert cp.plan("13 11 * * *") == [{"channel": "caffaine", "prefix": "CAFFAINE_"}]
    assert cp.plan("27 12 * * *") == []                       # healing 的時段歸 healing_post.yml
    assert [x["channel"] for x in cp.plan("", "all")] == ["tech", "shrimp", "caffaine"]
    assert cp.plan("", "healing") == []


# ---------- 權杖前綴隔離 ----------
@pytest.mark.parametrize("code,prefix", list(CODES.items()))
def test_每個頻道只讀自己前綴的權杖(code, prefix):
    t = hp.tokens(ALL_ENV, prefix)
    assert t == {"ig": f"IGTOK_{code}_xxxxxxxxxxxx", "threads": f"THTOK_{code}_xxxxxxxxxxxx"}
    other = {k: v for k, v in ALL_ENV.items() if not k.startswith(prefix)}
    assert hp.tokens(other, prefix) == {"ig": "", "threads": ""}      # 別頻道、頻道①、TC_ 都不會被拿來用
    assert hc.get_token(other, prefix) == ""
    assert hc.get_token(ALL_ENV, prefix) == f"IGTOK_{code}_xxxxxxxxxxxx"


def test_空前綴或亂寫前綴直接拒絕():
    for bad in ("", "tech_", "TECH", "TC-"):
        with pytest.raises(ValueError):
            hp.tokens(ALL_ENV, bad)
        with pytest.raises(ValueError):
            hc.get_token(ALL_ENV, bad)


def test_工作流每個頻道只帶自己的Secrets():
    for f, n in (("channel_post.yml", 6), ("channel_comments.yml", 3)):
        txt = (ROOT / ".github/workflows" / f).read_text(encoding="utf-8")
        lines = re.findall(r"^\s+([A-Z_]+): \$\{\{ matrix\.channel == '(\w+)' && secrets\.([A-Z_]+) \|\| '' \}\}", txt, re.M)
        assert len(lines) == 3 * n, f
        for env_name, ch, sec in lines:
            assert env_name == sec and sec.startswith(CODES[ch]), (f, env_name, ch)
        assert "HEALING_" not in txt.split("jobs:")[1]
        for ch1 in ("secrets.IG_ACCESS_TOKEN", "secrets.THREADS_ACCESS_TOKEN", "secrets.TC_"):
            assert ch1 not in txt, (f, ch1)


# ---------- 發文 ----------
def mk_item(q, name, n=2):
    d = q / name
    d.mkdir(parents=True)
    for i in range(1, n + 1):
        (d / f"{i}.png").write_bytes(b"x")
        (d / f"{i}.jpg").write_bytes(b"x")
    (d / "caption.txt").write_text("測試內文", encoding="utf-8")
    (d / "meta.json").write_text(json.dumps({"platforms": ["ig", "threads"], "status": "approved",
                                             "publish_at": None}), encoding="utf-8")


@pytest.fixture
def chans(tmp_path, monkeypatch):
    monkeypatch.setattr(hp, "ROOT", tmp_path)
    monkeypatch.setattr(hp.SP, "http", lambda m, url, **kw: {"access_token": kw["params"]["access_token"]})
    calls = []

    def pubs(code):
        return {"ig": lambda uid, tok, urls, cap: calls.append((code, "ig", uid, tok)) or {"id": f"ig-{code}"},
                "threads": lambda uid, tok, text, urls: calls.append((code, "threads", uid, tok)) or {"id": f"th-{code}"}}

    def vers(code):
        return {p: (lambda p: lambda uid, tok, urls, text: calls.append((code, "verify-" + p, uid, tok)) or "c")(p)
                for p in ("ig", "threads")}

    def go(code, env=ALL_ENV, live=True, dry=False, per_day_max=1):
        base = tmp_path / code
        (base / "queue").mkdir(parents=True, exist_ok=True)
        qp = base / "post_quota.json"
        if not qp.exists():
            qp.write_text(json.dumps({"live": live, "per_day": 5}), encoding="utf-8")
        return hp.run(dict(env), NOW, dry, queue=base / "queue", state=base / "state", quota_path=qp,
                      publishers=pubs(code), check=lambda u, w: None, saver=lambda *a: True,
                      verifiers=vers(code), prefix=CODES[code], per_day_max=per_day_max)
    return {"root": tmp_path, "calls": calls, "go": go}


def test_各頻道用自己的權杖發_先驗證_不重發(chans):
    for code in ("tech", "caffaine"):
        mk_item(chans["root"] / code / "queue", "20261112_a")
        mk_item(chans["root"] / code / "queue", "20261113_b")
    for code in ("tech", "caffaine"):
        rc, res = chans["go"](code)
        assert rc == 0 and set(res["posted"]) == {"ig", "threads"}, res
    for code, kind, uid, tok in chans["calls"]:
        assert tok.endswith(f"_{code}_xxxxxxxxxxxx") and uid == ALL_ENV[f"{CODES[code]}{kind.split('-')[-1].upper()}_USER_ID"]
    kinds = [(c, k) for c, k, _, _ in chans["calls"]]
    assert kinds.index(("tech", "verify-ig")) < kinds.index(("tech", "ig"))     # 權杖第一次出現：先驗證
    n = len(chans["calls"])
    rc, res = chans["go"]("tech")                                    # 同一天第二輪：per_day 上限 1 → 不發下一則
    assert rc == 0 and "下一則留到明天" in res["summary"] and len(chans["calls"]) == n
    posted = json.loads((chans["root"] / "tech/state/posted.json").read_text(encoding="utf-8"))
    assert list(posted) == ["20261112_a"]
    assert json.loads((chans["root"] / "tech/queue/20261112_a/meta.json").read_text())["status"] == "posted"
    # 頻道④的 state 完全沒被碰
    assert not (chans["root"] / "healing").exists()


def test_per_day取channels_json與開關檔較小者(chans):
    mk_item(chans["root"] / "tech" / "queue", "20261112_a")
    mk_item(chans["root"] / "tech" / "queue", "20261113_b")
    chans["go"]("tech", per_day_max=2)
    rc, res = chans["go"]("tech", per_day_max=2)
    assert set(res["posted"]) == {"ig", "threads"}                  # 開關檔 5、上限 2 → 第二則也發
    rc, res = chans["go"]("tech", per_day_max=2)
    assert "佇列已空" in res["summary"]


def test_shrimp_live_false略過不連Meta(chans, monkeypatch):
    mk_item(chans["root"] / "shrimp" / "queue", "20261112_a")
    monkeypatch.setattr(hp.SP, "http", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不准連 Meta")))
    rc, res = chans["go"]("shrimp", live=False)
    assert rc == 0 and "live=false" in res["summary"] and not chans["calls"]
    assert not (chans["root"] / "shrimp/state/posted.json").exists()


def test_缺權杖空跑_摘要寫前綴(chans, monkeypatch):
    mk_item(chans["root"] / "caffaine" / "queue", "20261112_a")
    monkeypatch.setattr(hp.SP, "http", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不准連 Meta")))
    env = {k: v for k, v in ALL_ENV.items() if not k.startswith("CAFFAINE_")}
    rc, res = chans["go"]("caffaine", env=env)
    assert rc == 0 and not chans["calls"]
    assert "等待 Andy 設定權杖：CAFFAINE_IG_ACCESS_TOKEN、CAFFAINE_THREADS_ACCESS_TOKEN" in res["summary"]


def test_佇列空_摘要寫佇列已空(chans):
    rc, res = chans["go"]("tech")
    assert rc == 0 and "佇列已空" in res["summary"] and not chans["calls"]
    env = {k: v for k, v in ALL_ENV.items() if not k.startswith("TECH_")}
    rc, res = chans["go"]("tech", env=env)
    assert "佇列已空" in res["summary"] and "等待 Andy 設定權杖：TECH_" in res["summary"]


def test_短效換長效寫回自己頻道的AUTO(monkeypatch):
    saved = []
    seq = iter([RuntimeError("expired"), {"access_token": "LONG_TECH_TOKEN_yyyyyyyy", "expires_in": 5184000}])

    def http(m, url, **kw):
        x = next(seq)
        if isinstance(x, Exception):
            raise x
        return x
    monkeypatch.setattr(hp.SP, "http", http)
    env = {"THREADS_APP_SECRET": "APPSEC_zzzzzzzz", "META_SECRETS_PAT": "PAT_zzzzzzzz"}
    new = hp.threads_token_check("SHORT", env, [], saver=lambda n, v, r, p: saved.append(n) or True, prefix="TECH_")
    assert new == "LONG_TECH_TOKEN_yyyyyyyy" and saved == ["TECH_THREADS_ACCESS_TOKEN_AUTO"]


def test_channel_post入口真的切換頻道路徑(monkeypatch):
    seen = {}

    def fake_run(env, now, dry, **kw):
        seen.update(kw, dry=dry)
        return 0, {"mode": "dry-run", "summary": "ok", "posted": {}, "notes": []}
    monkeypatch.setattr(hp, "run", fake_run)
    monkeypatch.setattr(cp.HP, "run", fake_run)          # channel_post 用 sys.path 匯入，是另一個模組物件
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert cp.main(["--channel", "caffaine", "--dry-run"]) == 0
    assert seen["prefix"] == "CAFFAINE_" and seen["queue"] == ROOT / "docs/marketing/channels/caffaine/queue"
    assert seen["quota_path"].name == "post_quota.json" and seen["dry"] is True
    assert hp.main(["--dry-run"]) == 0 and seen["prefix"] == "HEALING_"           # 不給 --channel＝頻道④
    assert seen["state"] == ROOT / "docs/marketing/channels/healing/state"


# ---------- 留言私訊 ----------
def test_新頻道私訊預設關閉_關著不讀權杖不連Meta(monkeypatch):
    monkeypatch.setattr(hc.SP, "http", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不准連 Meta")))
    for code in ("tech", "shrimp", "caffaine"):
        c = hc.channel_paths(code)
        assert json.loads(c["cfg"].read_text(encoding="utf-8"))["enabled"] is False
        rc, res = hc.run(env=ALL_ENV, cfg_path=c["cfg"], state_path=c["state"], posted_path=c["posted"],
                         prefix=c["prefix"])
        assert rc == 0 and "enabled=false" in res["summary"]
    assert cp.plan_comments() == []


def test_私訊開了但文字空白就不送(tmp_path, monkeypatch):
    monkeypatch.setattr(hc.SP, "http", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不准連 Meta")))
    cfg = tmp_path / "dm.json"
    cfg.write_text('{"enabled": true, "message": ""}', encoding="utf-8")
    rc, res = hc.run(env=ALL_ENV, cfg_path=cfg, state_path=tmp_path / "s.json", posted_path=tmp_path / "p.json",
                     prefix="TECH_")
    assert rc == 1 and "message 空白" in res["summary"]


# ---------- 續期 ----------
def test_續期包含三個新頻道_沒設是missing不告警(monkeypatch, tmp_path):
    for k in ("tech", "shrimp", "caffaine"):
        assert mtr.PLATFORMS[f"{k}_threads"]["env"] == f"{k.upper()}_THREADS_ACCESS_TOKEN"
        assert mtr.PLATFORMS[f"{k}_ig"]["env"] == f"{k.upper()}_IG_ACCESS_TOKEN"
    monkeypatch.setattr(mtr, "http_get", lambda url, params: {"access_token": params["access_token"], "expires_in": 5184000})
    rc, st = mtr.run({"THREADS_ACCESS_TOKEN": "T1_xxxxxxxx", "IG_ACCESS_TOKEN": "I1_xxxxxxxx"},
                     datetime(2026, 11, 15, 2, 23, tzinfo=timezone.utc), False, state_path=tmp_path / "m.json",
                     saver=lambda *a: True, pat_checker=lambda p, r: {"ok": True})
    assert rc == 0 and not st["alert"]
    for k in ("tech_threads", "tech_ig", "shrimp_threads", "shrimp_ig", "caffaine_threads", "caffaine_ig"):
        assert st["platforms"][k]["status"] == "missing"


def test_續期失敗有APP_SECRET就換長效寫回TECH_AUTO(monkeypatch, tmp_path):
    def http_get(url, params):
        if "refresh_access_token" in url:
            raise RuntimeError("HTTP 400 Session has expired")
        if url == mtr.THREADS_EXCHANGE:
            assert params["client_secret"] == "APPSEC_zzzzzzzz"
            return {"access_token": "LONG_NEW_TECH_wwwwwwww", "expires_in": 5184000}
        return {"id": "1"}
    monkeypatch.setattr(mtr, "http_get", http_get)
    saved = []
    rc, st = mtr.run({"TECH_THREADS_ACCESS_TOKEN": "SHORT_TECH_vvvvvvvv", "THREADS_APP_SECRET": "APPSEC_zzzzzzzz",
                      "META_SECRETS_PAT": "PAT_zzzzzzzz"},
                     datetime(2026, 11, 15, 2, 23, tzinfo=timezone.utc), False, state_path=tmp_path / "m.json",
                     saver=lambda n, v, r, p: saved.append((n, v)) or True, pat_checker=lambda p, r: {"ok": True})
    assert saved == [("TECH_THREADS_ACCESS_TOKEN_AUTO", "LONG_NEW_TECH_wwwwwwww")]
    assert st["platforms"]["tech_threads"]["ok"] and st["platforms"]["tech_threads"]["exchanged"]
    disk = (tmp_path / "m.json").read_text()
    assert "LONG_NEW_TECH" not in disk and "APPSEC" not in disk and "SHORT_TECH" not in disk


def test_只缺一個平台_摘要只列缺的那個(chans):
    env = {k: v for k, v in ALL_ENV.items() if k != "TECH_THREADS_ACCESS_TOKEN"}
    rc, res = chans["go"]("tech", env=env)
    assert "佇列已空" in res["summary"] and res["summary"].endswith("等待 Andy 設定權杖：TECH_THREADS_ACCESS_TOKEN")


def test_新頻道佇列空_驗證模式借頻道4的圖_不發布(tmp_path, monkeypatch):
    q4 = tmp_path / "h" / "queue"
    mk_item(q4, "20261108_intro")
    monkeypatch.setattr(hp, "QUEUE", q4)
    monkeypatch.setattr(hp, "ROOT", tmp_path)
    monkeypatch.setattr(hp.SP, "resolve_user_id", lambda p, uid, tok: "123")
    seen = []
    env = {"TECH_IG_ACCESS_TOKEN": "IGTOK_tech_xxxxxxxxxxxx"}
    (tmp_path / "t" / "queue").mkdir(parents=True)
    rc, res = hp.run_verify(env, NOW, queue=tmp_path / "t" / "queue", state=tmp_path / "t" / "state",
                            check=lambda u, w: None, verifiers={"ig": lambda uid, tok, urls, cap: seen.append(tok) or "c1"},
                            prefix="TECH_")
    assert rc == 0 and seen == ["IGTOK_tech_xxxxxxxxxxxx"] and res["item"] == "20261108_intro"
    v = json.loads((tmp_path / "t/state/verify.json").read_text())
    assert v["ig"]["verified"] and "threads" not in v
    assert not (tmp_path / "h" / "state").exists()          # 頻道④的 state 沒被寫
