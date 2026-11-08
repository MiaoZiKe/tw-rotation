"""頻道④ IG 留言自動私訊（scripts/healing_comments.py）：用假的 HTTP 回應模擬 Meta。"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import healing_comments as HC  # noqa: E402
import social_publish as SP  # noqa: E402

NOW = datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc)
TOKEN = "IGAAfaketoken1234567890"
REAL_CFG = Path(__file__).resolve().parents[1] / "docs" / "marketing" / "channels" / "healing" / "dm_config.json"


def ts(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%S+0000")


class Fake:
    """依網址回假資料；follow 對照表 igsid → True/False/None（None＝API 錯誤）。"""

    def __init__(self, comments, follow, dm_error=None):
        self.comments = comments
        self.follow = follow
        self.dm_error = dm_error
        self.sent = []
        self.calls = []

    def __call__(self, method, url, params=None, json=None, **kw):
        self.calls.append((method, url))
        if url.endswith("/me"):
            return {"user_id": "17841400000000001", "username": "tanqing"}
        if url.endswith("/media"):
            return {"data": [{"id": "M1", "timestamp": ts(5)}, {"id": "OLD", "timestamp": ts(24 * 10)}]}
        if url.endswith("/comments"):
            mid = url.rsplit("/", 2)[-2]
            return {"data": self.comments.get(mid, [])}
        if url.endswith("/messages"):
            if self.dm_error:
                raise RuntimeError(self.dm_error)
            self.sent.append((json["recipient"]["comment_id"], json["message"]["text"]))
            return {"recipient_id": "x", "message_id": "m"}
        igsid = url.rsplit("/", 1)[-1]
        v = self.follow.get(igsid)
        if v is None:
            raise RuntimeError("HTTP 400 {\"message\": \"User consent is required\"}")
        return {"is_user_follow_business": v, "id": igsid}


def c(cid, uid, text, hours=1, name="someone"):
    return {"id": cid, "text": text, "timestamp": ts(hours), "from": {"id": uid, "username": name}}


@pytest.fixture
def paths(tmp_path, monkeypatch):
    monkeypatch.setattr(SP, "_sleep", lambda s: None)
    monkeypatch.setattr(SP, "_SECRETS", [])
    cfg = json.loads(REAL_CFG.read_text(encoding="utf-8"))
    p = {"cfg": tmp_path / "dm_config.json", "state": tmp_path / "state" / "comments_dm.json",
         "posted": tmp_path / "state" / "posted.json"}
    p["cfg"].write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    def set_cfg(**kw):
        cfg.update(kw)
        p["cfg"].write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    p["set_cfg"] = set_cfg
    return p


def go(paths, fake, monkeypatch, dry=False, env=None):
    monkeypatch.setattr(SP, "http", fake)
    return HC.run(env={"HEALING_IG_ACCESS_TOKEN": TOKEN} if env is None else env, dry_run=dry, now=NOW,
                  cfg_path=paths["cfg"], state_path=paths["state"], posted_path=paths["posted"])


def test_無權杖空跑成功(paths, monkeypatch):
    fake = Fake({}, {})
    code, res = go(paths, fake, monkeypatch, env={})
    assert code == 0 and "等待權杖" in res["summary"]
    assert fake.calls == [] and not paths["state"].exists()


def test_只私訊追蹤者_沒追蹤與無法確認不送(paths, monkeypatch):
    fake = Fake({"M1": [c("C1", "U1", "好喜歡"), c("C2", "U2", "路過"), c("C3", "U3", "推")]},
                {"U1": True, "U2": False})          # U3 → API 錯誤＝無法確認
    code, res = go(paths, fake, monkeypatch)
    assert code == 0
    assert [x[0] for x in fake.sent] == ["C1"]
    assert fake.sent[0][1].startswith("謝謝留下今天的晴")
    assert res["counts"] == {"dm": 1, "skip_not_follower": 1, "skip_unknown_follow": 1}
    st = json.loads(paths["state"].read_text(encoding="utf-8"))
    assert "本週「無法確認追蹤」未私訊 1 則" in res["summary"]
    raw = paths["state"].read_text(encoding="utf-8")
    for leak in ("C1", "U1", "好喜歡", "someone", TOKEN):      # 不存留言全文、名稱、編號、權杖
        assert leak not in raw
    assert len(st["seen"]) == 3


def test_去重_第二輪不重送(paths, monkeypatch):
    fake = Fake({"M1": [c("C1", "U1", "好喜歡")]}, {"U1": True})
    go(paths, fake, monkeypatch)
    code, res = go(paths, fake, monkeypatch)
    assert len(fake.sent) == 1 and res["counts"] == {}


def test_略過自己帳號與超過七天(paths, monkeypatch):
    fake = Fake({"M1": [c("C1", "17841400000000001", "謝謝大家", name="tanqing"),
                        c("C2", "U2", "舊留言", hours=24 * 8)]}, {"U2": True})
    _, res = go(paths, fake, monkeypatch)
    assert fake.sent == [] and res["counts"] == {"own": 1, "expired": 1}


def test_自傷關鍵字走關懷訊息_不看追蹤(paths, monkeypatch):
    fake = Fake({"M1": [c("C1", "U1", "真的不想活了"), c("C2", "U2", "笑死 太可愛")]}, {"U1": False, "U2": True})
    _, res = go(paths, fake, monkeypatch)
    sent = dict(fake.sent)
    assert "1925" in sent["C1"] and "119" in sent["C1"] and "謝謝留下今天的晴" not in sent["C1"]
    assert sent["C2"].startswith("謝謝留下今天的晴")       # 「笑死」被排除，不誤判
    assert res["alerts"] == 1 and res["counts"]["care"] == 1
    st = json.loads(paths["state"].read_text(encoding="utf-8"))
    assert sum(1 for v in st["seen"].values() if v.get("self_harm")) == 1
    assert "自傷訊號 1 則" in HC.summary_md(res)


def test_每輪上限_其餘下一輪(paths, monkeypatch):
    paths["set_cfg"](max_per_run=2)
    fake = Fake({"M1": [c(f"C{i}", f"U{i}", "嗨") for i in range(5)]}, {f"U{i}": True for i in range(5)})
    _, res = go(paths, fake, monkeypatch)
    assert len(fake.sent) == 2 and "每輪上限 2" in res["summary"]
    go(paths, fake, monkeypatch)
    go(paths, fake, monkeypatch)
    assert sorted(x[0] for x in fake.sent) == [f"C{i}" for i in range(5)]


def test_無法確認改成照樣送(paths, monkeypatch):
    paths["set_cfg"](unknown_follow="send")
    fake = Fake({"M1": [c("C1", "U1", "嗨")]}, {})
    _, res = go(paths, fake, monkeypatch)
    assert [x[0] for x in fake.sent] == ["C1"] and res["counts"] == {"dm_unknown_follow": 1}


def test_空跑不送不寫(paths, monkeypatch):
    fake = Fake({"M1": [c("C1", "U1", "嗨")]}, {"U1": True})
    _, res = go(paths, fake, monkeypatch, dry=True)
    assert fake.sent == [] and res["counts"] == {"dry_dm": 1} and not paths["state"].exists()


def test_私訊失敗會重試_權杖不進訊息(paths, monkeypatch):
    fake = Fake({"M1": [c("C1", "U1", "嗨")]}, {"U1": True}, dm_error=f"HTTP 500 boom {TOKEN}")
    code, res = go(paths, fake, monkeypatch)
    assert res["counts"] == {"send_failed": 1}
    assert all(TOKEN not in e for e in res["errors"])
    st = json.loads(paths["state"].read_text(encoding="utf-8"))
    assert list(st["seen"].values())[0]["tries"] == 1
    fake.dm_error = None
    go(paths, fake, monkeypatch)
    assert [x[0] for x in fake.sent] == ["C1"]


def test_停用開關(paths, monkeypatch):
    paths["set_cfg"](enabled=False)
    fake = Fake({"M1": [c("C1", "U1", "嗨")]}, {"U1": True})
    code, res = go(paths, fake, monkeypatch)
    assert code == 0 and fake.sent == [] and "enabled=false" in res["summary"]


def test_posted_json_的貼文也會讀(paths, monkeypatch):
    paths["posted"].parent.mkdir(parents=True, exist_ok=True)
    paths["posted"].write_text(json.dumps({"20261107_x": {"ig": {"id": "P9", "at": "2026-11-07T20:27:00+08:00"},
                                                          "at": "2026-11-07T20:27:00+08:00"}}), encoding="utf-8")
    fake = Fake({"P9": [c("C1", "U1", "嗨")]}, {"U1": True})
    go(paths, fake, monkeypatch)
    assert [x[0] for x in fake.sent] == ["C1"]


def test_預設文案合規():
    cfg = json.loads(REAL_CFG.read_text(encoding="utf-8"))
    m = cfg["message"]
    for bad in ("我", "我們", "投資", "股", "諮商", "治療", "醫"):
        assert bad not in m
    assert cfg["only_followers"] is True and cfg["unknown_follow"] == "skip"
    assert "1925" in cfg["care_message"] and "119" in cfg["care_message"] and "110" in cfg["care_message"]


def test_沒有新留言不寫檔(paths, monkeypatch):
    fake = Fake({"M1": []}, {})
    _, res = go(paths, fake, monkeypatch)
    assert not paths["state"].exists() and "沒有新留言" in res["summary"]
    fake.comments = {"M1": [c("C1", "U1", "嗨")]}
    fake.follow = {"U1": True}
    go(paths, fake, monkeypatch)
    t1 = paths["state"].read_text(encoding="utf-8")
    go(paths, fake, monkeypatch)
    assert paths["state"].read_text(encoding="utf-8") == t1      # 第二輪沒變動 → 檔案不動、不會產生空 commit
