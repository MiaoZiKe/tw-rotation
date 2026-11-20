"""頻道①哩股哩股 IG 留言關鍵字 → 私訊來源連結（scripts/ligu_comments.py）：用假的 Meta 回應。"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ig_login_dm as DM  # noqa: E402
import ligu_comments as LC  # noqa: E402
import social_publish as SP  # noqa: E402

NOW = datetime(2026, 11, 20, 4, 0, tzinfo=timezone.utc)
CFG = {"enabled": True, "keywords": ["來源", "連結"], "lookback_days": 7, "max_per_run": 20,
       "dm_template": "來源：{url}", "ack_text": "已經私訊你囉～", "fallback_template": "連結 {url}"}


def setup(tmp_path, comments, dm_fail=False):
    q = tmp_path / "queue"
    q.mkdir()
    (q / "a.md").write_text("---\nstatus: posted\nposted_at: 2026-11-19T12:19+08:00\ntitle: T\n"
                            "first_comment: 來源：https://liguligu-puipui.com/#article/x\n"
                            "urls: https://www.instagram.com/reel/ABC123/\n---\n內文\n", encoding="utf-8")
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps(CFG), encoding="utf-8")
    calls = []

    def http(method, url, **kw):
        calls.append((method, url))
        if url.endswith("/me"):
            return {"user_id": "99", "username": "ligu"}
        if url.endswith("/media"):
            return {"data": [{"id": "M1", "permalink": "https://www.instagram.com/reel/ABC123/"}]}
        if url.endswith("/comments"):
            return {"data": comments}
        raise AssertionError(url)

    posts = []

    def post(url, token, params=None, body=None):
        posts.append((url, params, body))
        if dm_fail and url.endswith("/messages"):
            raise RuntimeError("HTTP 400")
        return {}

    return q, cfg, calls, posts, http, post


def go(monkeypatch, tmp_path, comments, dry=False, dm_fail=False):
    q, cfg, calls, posts, http, post = setup(tmp_path, comments, dm_fail)
    monkeypatch.setattr(SP, "http", http)
    monkeypatch.setattr(DM, "_post", post)
    st = tmp_path / "state.json"
    code, res = LC.run(env={"IG_ACCESS_TOKEN": "IGAAtoken"}, dry_run=dry, now=NOW, cfg_path=tmp_path / "cfg.json",
                       state_path=st, queue=q)
    return code, res, posts, st


C1 = {"id": "c1", "text": "請問來源在哪", "timestamp": "2026-11-20T03:30:00+0000", "username": "fan"}


def test_符合關鍵字_先私訊再公開回已私訊(monkeypatch, tmp_path):
    code, res, posts, st = go(monkeypatch, tmp_path, [C1])
    assert code == 0 and res["sent"] == 1
    assert posts[0][0].endswith("/99/messages") and "liguligu-puipui.com" in posts[0][2]["message"]["text"]
    assert posts[1][0].endswith("/c1/replies") and posts[1][1]["message"] == "已經私訊你囉～"
    assert "dm_ok" in st.read_text()


def test_已處理過的留言不重送(monkeypatch, tmp_path):
    go(monkeypatch, tmp_path, [C1])
    q, cfg, calls, posts, http, post = setup(tmp_path / "x", [C1]) if (tmp_path / "x").mkdir() is None else None
    monkeypatch.setattr(SP, "http", http)
    monkeypatch.setattr(DM, "_post", post)
    code, res = LC.run(env={"IG_ACCESS_TOKEN": "IGAAtoken"}, now=NOW, cfg_path=cfg, state_path=tmp_path / "state.json", queue=q)
    assert posts == [] and res["matched"] == 1 and res["sent"] == 0


def test_私訊失敗退回公開貼連結(monkeypatch, tmp_path):
    code, res, posts, st = go(monkeypatch, tmp_path, [C1], dm_fail=True)
    assert code == 0 and posts[-1][0].endswith("/c1/replies") and "liguligu-puipui.com" in posts[-1][1]["message"]
    assert "fallback_public" in st.read_text()


def test_沒有關鍵字與自己的留言不回(monkeypatch, tmp_path):
    cs = [{"id": "c2", "text": "好看", "timestamp": "2026-11-20T03:30:00+0000", "username": "fan"},
          {"id": "c3", "text": "來源在上面", "timestamp": "2026-11-20T03:30:00+0000", "username": "ligu"}]
    code, res, posts, st = go(monkeypatch, tmp_path, cs)
    assert posts == [] and res["matched"] == 0


def test_空跑不送不寫紀錄(monkeypatch, tmp_path):
    code, res, posts, st = go(monkeypatch, tmp_path, [C1], dry=True)
    assert posts == [] and not st.exists() and res["matched"] == 1


def test_沒權杖或停用就安靜結束(tmp_path):
    q, cfg, *_ = setup(tmp_path, [])
    assert LC.run(env={}, cfg_path=cfg, state_path=tmp_path / "s.json", queue=q)[0] == 0
