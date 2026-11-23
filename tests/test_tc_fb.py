"""頻道② 科技透明圈：FB 粉專 Reels 同步（scripts/tc_fb.py＋tc_post.py 整合）。全部假 API，不連外。

涵蓋：開關關閉完全不呼叫 FB；開關打開三段式順序正確（start → 上傳 → finish → 查狀態）、寫回 ids_fb／urls_fb；
FB 失敗不影響 IG／Threads；不重發；--fb-only 補發；只讀檢查不印權杖。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tc_fb as FB  # noqa: E402
import tc_post as tc  # noqa: E402
from test_tc_autopost import ENV, VNOW, VideoAPI, mkvideo  # noqa: E402

FBTOK, PAGE = "EAAPAGE_TOKEN_zzzzzzzzzzzzzzzz", "1467703339757220"
FENV = dict(ENV, TC_FB_PAGE_TOKEN=FBTOK, TC_FB_PAGE_ID=PAGE)
CFG = {"enabled": True, "threads": True, "ig": True, "per_day": 1, "min_gap_hours": 20}


class FakeFB:
    def __init__(self, fail=None, status=None):
        self.calls, self.fail = [], fail
        self.status = status or {"video_status": "ready", "publishing_phase": {"status": "complete"}}

    def __call__(self, method, url, token, params=None, headers=None, body=None):
        assert token == FBTOK
        p = dict(params or {})
        self.calls.append((method, url, p, dict(headers or {}), body))
        step = p.get("upload_phase") or ("upload" if "rupload" in url else p.get("fields", "") or url.rsplit("/", 1)[-1])
        if self.fail and self.fail == step:
            raise FB.FBError(f"HTTP 400 {url}：boom")
        if p.get("upload_phase") == "start":
            return {"video_id": "777", "upload_url": "https://rupload.facebook.com/video-upload/v25.0/777"}
        if "rupload" in url or p.get("upload_phase") == "finish":
            return {"success": True}
        if p.get("fields") == "status":
            return {"status": self.status}
        if p.get("fields") == "permalink_url":
            return {"permalink_url": "/reel/777"}
        raise AssertionError(url)

    def steps(self):
        return [c[2].get("upload_phase") or ("upload" if "rupload" in c[1] else c[2].get("fields")) for c in self.calls]


@pytest.fixture(autouse=True)
def _setup(monkeypatch, tmp_path):
    tc._SECRETS.clear()
    FB._SECRETS.clear()
    monkeypatch.setattr(tc, "SLEEP", lambda s: None)
    monkeypatch.setattr(FB, "SLEEP", lambda s: None)
    monkeypatch.setattr(FB, "probe", lambda p: {"w": 1080, "h": 1920, "fps": 30.0, "dur": 60.0})
    monkeypatch.setattr(tc, "check_public", lambda u: None)


def run(monkeypatch, tmp_path, fb_on, api=None, fb=None, env=FENV):
    (tmp_path / "fb.json").write_text(json.dumps({"enabled": fb_on}))
    monkeypatch.setattr(FB, "CONFIG", tmp_path / "fb.json")
    api, fb = api or VideoAPI(seq=("FINISHED",)), fb or FakeFB()
    monkeypatch.setattr(tc, "api", api)
    monkeypatch.setattr(FB, "http", fb)
    rc, res = tc.run(dict(env), VNOW, False, queue=tmp_path / "q", state_dir=tmp_path / "state", cfg=CFG)
    return rc, res, api, fb


def test_正式設定檔已開啟_Andy確認後():
    """2026-11-23 Andy 試發 800v 後回「看得到」，正式開啟。"""
    assert FB.load_config() == {"enabled": True}
    assert json.loads((Path(tc.ROOT) / "social" / "tc" / "fb.json").read_text())["enabled"] is True


def test_設定檔壞掉視為關閉(tmp_path):
    (tmp_path / "x.json").write_text("{壞")
    assert FB.load_config(tmp_path / "x.json") == {"enabled": False}
    (tmp_path / "y.json").write_text('{"enabled": "true"}')
    assert FB.load_config(tmp_path / "y.json") == {"enabled": False}


def test_開關關閉完全不呼叫FB(monkeypatch, tmp_path):
    a = mkvideo(tmp_path / "q")
    rc, res, api, fb = run(monkeypatch, tmp_path, False)
    assert rc == 0 and res["posted"] == ["20261115_v"] and fb.calls == []
    head = (a / "post.md").read_text()
    assert "ids_fb" not in head and "fb_error" not in head and not res["fb_alert"]


def test_開關打開_IG與Threads之後才發FB_三段式順序正確(monkeypatch, tmp_path, capsys):
    order = []
    a = mkvideo(tmp_path / "q")
    api = VideoAPI(seq=("FINISHED",))
    orig_api = api.__call__
    fb = FakeFB()

    def api2(*x, **k):
        order.append("meta")
        return orig_api(*x, **k)

    def fb2(*x, **k):
        order.append("fb")
        return fb(*x, **k)
    rc, res, _, _ = run(monkeypatch, tmp_path, True, api=api2, fb=fb2)
    assert rc == 0 and res["posted"] == ["20261115_v"] and not res["fb_alert"]
    assert "fb" not in order[:order.index("fb")] and "meta" not in order[order.index("fb"):]   # FB 全在最後
    assert len(api.posts("ig")) == 1 and len(api.posts("threads")) == 2
    assert fb.steps() == ["start", "upload", "finish", "status", "permalink_url"]
    start, up, fin = fb.calls[0], fb.calls[1], fb.calls[2]
    assert start[1] == f"https://graph.facebook.com/v25.0/{PAGE}/video_reels"
    assert up[1] == "https://rupload.facebook.com/video-upload/v25.0/777"
    assert up[3]["offset"] == "0" and up[3]["file_size"] == str(len(up[4])) and up[4] == (a / "ep.mp4").read_bytes()
    assert fin[2] == {"upload_phase": "finish", "video_id": "777", "video_state": "PUBLISHED",
                      "description": "IG 影片說明 #科技透明圈"}
    assert all(FBTOK not in json.dumps(c[2], ensure_ascii=False) and FBTOK not in c[1] for c in fb.calls)  # 權杖不進網址／參數
    head = (a / "post.md").read_text()
    assert "ids_fb: 777" in head and "urls_fb: https://www.facebook.com/reel/777" in head and "status: posted" in head
    st = json.loads((tmp_path / "state" / "posted.json").read_text())["posts"][0]
    assert st["ids_fb"] == "777" and st["fb"] == "https://www.facebook.com/reel/777"
    assert st["ids_ig"] and st["ids_threads"]
    assert FBTOK not in capsys.readouterr().out.replace("::add-mask::" + FBTOK, "")


@pytest.mark.parametrize("step", ["start", "upload", "finish"])
def test_FB失敗不影響IG與Threads(monkeypatch, tmp_path, step, capsys):
    a = mkvideo(tmp_path / "q")
    rc, res, api, fb = run(monkeypatch, tmp_path, True, fb=FakeFB(fail=step))
    assert rc == 0 and res["posted"] == ["20261115_v"]
    assert len(api.posts("ig")) == 1 and len(api.posts("threads")) == 2
    head = (a / "post.md").read_text()
    assert "status: posted" in head and "done: ig, threads" in head and "ids_fb" not in head
    assert "fb_error: HTTP 400" in head and res["fb_alert"] and not res["alert"]
    assert "FB Reels 發文失敗（不影響 IG／Threads）" in capsys.readouterr().out
    if step == "finish":
        assert fb.steps() == ["start", "upload", "finish"]


def test_FB處理狀態error也只記錄(monkeypatch, tmp_path):
    a = mkvideo(tmp_path / "q")
    rc, res, api, fb = run(monkeypatch, tmp_path, True, fb=FakeFB(status={"video_status": "error"}))
    assert rc == 0 and "status: posted" in (a / "post.md").read_text() and res["fb_alert"]


def test_IG失敗時FB照常不拋例外_IG照舊標error(monkeypatch, tmp_path):
    a = mkvideo(tmp_path / "q")
    rc, res, api, fb = run(monkeypatch, tmp_path, True, api=VideoAPI(seq=("ERROR",)))
    head = (a / "post.md").read_text()
    assert rc == 1 and "status: error" in head and "IG 影片容器處理失敗" in res["errors"][0]


def test_圖片稿與沒有權杖不發FB(monkeypatch, tmp_path):
    from test_tc_autopost import mkpost
    from datetime import datetime
    mkpost(tmp_path / "q")
    (tmp_path / "fb.json").write_text('{"enabled": true}')
    monkeypatch.setattr(FB, "CONFIG", tmp_path / "fb.json")
    fb = FakeFB()
    monkeypatch.setattr(FB, "http", fb)
    monkeypatch.setattr(tc, "api", VideoAPI(seq=("FINISHED",), ig_type="CAROUSEL_ALBUM", th_type="CAROUSEL_ALBUM"))
    tc.run(dict(FENV), datetime.fromisoformat("2026-11-10T21:00+08:00"), False, queue=tmp_path / "q",
           state_dir=tmp_path / "s", cfg=CFG)
    assert fb.calls == []
    a = mkvideo(tmp_path / "q2")
    rc, res = tc.run(dict(ENV), VNOW, False, queue=tmp_path / "q2", state_dir=tmp_path / "s2", cfg=CFG)
    assert rc == 0 and fb.calls == [] and "fb_error: 沒有 TECH_FB_PAGE_TOKEN" in (a / "post.md").read_text()


def test_規格不合不上傳(monkeypatch, tmp_path):
    monkeypatch.setattr(FB, "probe", lambda p: {"w": 1920, "h": 1080, "fps": 30.0, "dur": 120.0})
    a = mkvideo(tmp_path / "q")
    rc, res, api, fb = run(monkeypatch, tmp_path, True)
    assert rc == 0 and fb.calls == []
    head = (a / "post.md").read_text()
    assert "不是 9:16" in head and "不在 3～90 秒" in head


def test_fb_only補發已發影片_不改status_不重發(monkeypatch, tmp_path):
    a = mkvideo(tmp_path / "q", "20261122_800v")
    tc.IG.rewrite_meta(a / "post.md", {"status": "posted", "done": "ig, threads", "ids_ig": "1"})
    (tmp_path / "fb.json").write_text('{"enabled": false}')                # 開關關著也能手動補發
    monkeypatch.setattr(FB, "CONFIG", tmp_path / "fb.json")
    meta = VideoAPI()
    monkeypatch.setattr(tc, "api", meta)
    fb = FakeFB()
    monkeypatch.setattr(FB, "http", fb)
    # dry-run：不呼叫 FB、不寫檔
    before = (a / "post.md").read_text()
    rc, res = tc.fb_only(dict(FENV), VNOW, "20261122_800v", True, queue=tmp_path / "q", state_dir=tmp_path / "s")
    assert rc == 0 and fb.calls == [] and (a / "post.md").read_text() == before
    rc, res = tc.fb_only(dict(FENV), VNOW, "20261122_800v", False, queue=tmp_path / "q", state_dir=tmp_path / "s")
    head = (a / "post.md").read_text()
    assert rc == 0 and "ids_fb: 777" in head and "status: posted" in head and meta.calls == []
    n = len(fb.calls)
    rc, res = tc.fb_only(dict(FENV), VNOW, "20261122_800v", False, queue=tmp_path / "q", state_dir=tmp_path / "s")
    assert rc == 0 and len(fb.calls) == n                                   # 已發過不重發
    rc, res = tc.fb_only(dict(FENV), VNOW, "沒有這篇", False, queue=tmp_path / "q", state_dir=tmp_path / "s")
    assert rc == 1


def test_只讀檢查不印權杖(monkeypatch, capsys):
    def fake(method, url, token, params=None, headers=None, body=None):
        assert method == "GET"
        if url.endswith("/debug_token"):
            return {"data": {"type": "PAGE", "is_valid": True, "profile_id": PAGE, "expires_at": 0,
                             "scopes": ["publish_video", "pages_manage_posts", "pages_read_engagement", "pages_show_list"]}}
        return {"id": PAGE, "name": "科技透明圈"}
    monkeypatch.setattr(FB, "http", fake)
    assert FB.check({"TC_FB_PAGE_TOKEN": FBTOK, "TC_FB_PAGE_ID": PAGE}) == 0
    out = capsys.readouterr().out
    assert "科技透明圈" in out and "類型 PAGE" in out and "到期 永不" in out and "結果：成功" in out
    assert FBTOK not in out
    assert FB.check({"TC_FB_PAGE_TOKEN": "", "TC_FB_PAGE_ID": PAGE}) == 1
    assert "缺少 Secret：TECH_FB_PAGE_TOKEN" in capsys.readouterr().out


def test_工作流有fb選項且權杖只從Secret帶():
    y = (Path(tc.ROOT) / ".github" / "workflows" / "tc_post.yml").read_text()
    assert "fb_check:" in y and "fb_only:" in y and "scripts/tc_fb.py --check" in y
    assert "secrets.TECH_FB_PAGE_TOKEN" in y and "secrets.TECH_FB_PAGE_ID" in y
