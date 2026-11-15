"""頻道③ CaffAIne 每天兩支 Reels（2026-11-15 Andy：「我決定每天兩隻 Reels」）：
一天兩個時段（12:15、21:00）每個時段最多 1 則、整天最多 2 則；影片放 GitHub Release（不進 main）；
@reels-test 驗證；channel_media 的 sync／clean／stage／testclip；頻道④／輪播行為不變。"""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts import channel_media as cm
from scripts import channel_post as cp
from scripts import healing_post as hp

ROOT = Path(__file__).resolve().parents[1]
TPE = timezone(timedelta(hours=8))
SLOTS = [{"slot": "12:15", "backup": "13:43"}, {"slot": "21:00", "backup": "22:27"}]
ENV = {"CAFFAINE_IG_ACCESS_TOKEN": "IGAA_CAFF_REELS_SECRET_aaaa", "CAFFAINE_THREADS_ACCESS_TOKEN": "THAA_CAFF_bbbb",
       "CAFFAINE_IG_USER_ID": "8001", "CAFFAINE_THREADS_USER_ID": "8002"}
REL = "https://github.com/MiaoZiKe/tw-rotation/releases/download/channel-media/"


def at(h, m, day=16):
    return datetime(2026, 11, day, h, m, tzinfo=TPE)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    hp.SP._SECRETS.clear()
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)


def mk_video(q, name, publish_at=None, local=False, cover=True, status="approved"):
    d = q / name
    d.mkdir(parents=True)
    if local:
        (d / "video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"v" * 50)
    if cover:
        (d / "cover.jpg").write_bytes(b"jpg")
    (d / "caption.txt").write_text(f"{name} 內文", encoding="utf-8")
    m = {"format": "video", "platforms": ["ig", "threads"], "status": status, "publish_at": publish_at}
    if not local:
        m["video_src"] = f"media/caffaine/{name}"
    (d / "meta.json").write_text(json.dumps(m), encoding="utf-8")
    return d


@pytest.fixture
def box(tmp_path, monkeypatch):
    root = tmp_path
    q = root / "docs/marketing/channels/caffaine/queue"
    st = root / "docs/marketing/channels/caffaine/state"
    q.mkdir(parents=True)
    st.mkdir(parents=True)
    quota = root / "docs/marketing/channels/caffaine/post_quota.json"
    quota.write_text('{"live": true, "per_day": 2}', encoding="utf-8")
    monkeypatch.setattr(hp, "ROOT", root)
    monkeypatch.setitem(hp.MEDIA, q, st)
    monkeypatch.setattr(hp.SP, "http", lambda m, url, **kw: {"access_token": kw["params"]["access_token"],
                                                            "expires_in": 5184000})
    # 已驗證過（略過首次驗證模式），影片網址 release
    (st / "verify.json").write_text(json.dumps({p: {"verified": True} for p in ("ig", "threads")}), encoding="utf-8")
    calls = []

    def vpub(p):
        def f(uid, token, url, text, cover=""):
            calls.append((p, url, cover))
            return {"id": f"{p}-{len(calls)}", "link": f"https://example.com/{p}/{len(calls)}"}
        return f

    def no(*a, **k):
        raise AssertionError("不該走輪播／驗證函式")

    def media(name):
        m = json.loads((st / "media.json").read_text()) if (st / "media.json").exists() else {}
        n = name.lstrip("@")
        m[name] = {"video": REL + f"caffaine__{n}.mp4", "cover": REL + f"caffaine__{n}__cover.jpg",
                   "at": "2026-11-16T10:00:00+08:00"}
        (st / "media.json").write_text(json.dumps(m), encoding="utf-8")

    def go(now, slots=SLOTS, dry=False, env=ENV):
        return hp.run(dict(env), now, dry, queue=q, state=st, quota_path=quota, publishers={"ig": no, "threads": no},
                      check=lambda u, w: None, saver=lambda *a: True, verifiers={"ig": no, "threads": no},
                      prefix="CAFFAINE_", per_day_max=2, video_publishers={"ig": vpub("ig"), "threads": vpub("threads")},
                      video_verifiers={"ig": no, "threads": no}, slots=slots)
    return {"root": root, "q": q, "st": st, "calls": calls, "go": go, "media": media}


# ---------- 時段 ----------
def test_slot_key_屬於最近一個已到的主時段():
    assert hp.slot_key(at(12, 15), SLOTS) == "2026-11-16 12:15"
    assert hp.slot_key(at(13, 43), SLOTS) == "2026-11-16 12:15"      # 保底補跑＝同一個時段
    assert hp.slot_key(at(20, 59), SLOTS) == "2026-11-16 12:15"      # GitHub 延遲也還是第一個時段
    assert hp.slot_key(at(21, 0), SLOTS) == "2026-11-16 21:00"
    assert hp.slot_key(at(22, 27), SLOTS) == "2026-11-16 21:00"
    assert hp.slot_key(at(0, 40, 17), SLOTS) == "2026-11-16 21:00"   # 半夜延遲：算前一天晚上那個時段
    assert hp.slot_key(at(9, 0, 17), SLOTS) == "2026-11-16 21:00"
    assert hp.slot_key(datetime(2026, 11, 16, 4, 16, tzinfo=timezone.utc), SLOTS) == "2026-11-16 12:15"   # UTC 也對


def test_兩個時段各發一則_同時段保底不重發_整天最多兩則(box):
    for n in ("20261116_a", "20261116_b", "20261116_c"):
        mk_video(box["q"], n)
        box["media"](n)
    rc, res = box["go"](at(12, 16))
    assert rc == 0 and set(res["posted"]) == {"ig", "threads"} and res["item"] == "20261116_a", res
    rc, res = box["go"](at(13, 44))                                   # 第一個時段保底：已發 → 不發第二則
    assert rc == 0 and "這個時段（2026-11-16 12:15）已發 20261116_a" in res["summary"] and not res["posted"]
    rc, res = box["go"](at(21, 1))
    assert rc == 0 and res["item"] == "20261116_b" and set(res["posted"]) == {"ig", "threads"}
    rc, res = box["go"](at(22, 28))                                   # 第二個時段保底：整天 2 則已滿
    assert "今天已發 2 則（per_day=2）" in res["summary"] and not res["posted"]
    posted = json.loads((box["st"] / "posted.json").read_text())
    assert posted["20261116_a"]["slot"] == "2026-11-16 12:15" and posted["20261116_b"]["slot"] == "2026-11-16 21:00"
    assert len(box["calls"]) == 4
    rc, res = box["go"](at(12, 16, 17))                               # 隔天中午發第三則
    assert res["item"] == "20261116_c" and set(res["posted"]) == {"ig", "threads"}


def test_晚上時段保底_就算整天還有額度也不在同時段發第二則(box):
    for n in ("20261116_a", "20261116_b"):
        mk_video(box["q"], n)
        box["media"](n)
    box["go"](at(21, 1))
    rc, res = box["go"](at(22, 28))
    assert "這個時段（2026-11-16 21:00）已發 20261116_a" in res["summary"] and not res["posted"]


def test_整天上限2_手動觸發也擋(box):
    for n in ("20261116_a", "20261116_b", "20261116_c"):
        mk_video(box["q"], n)
        box["media"](n)
    box["go"](at(12, 16))
    box["go"](at(21, 1))
    rc, res = box["go"](at(23, 50), slots=SLOTS + [{"slot": "23:45", "backup": "23:55"}])
    assert "今天已發 2 則（per_day=2）" in res["summary"] and not res["posted"]


def test_一個平台失敗_保底只補那個平台_不算新的一則(box):
    mk_video(box["q"], "20261116_a")
    mk_video(box["q"], "20261116_b")
    for n in ("20261116_a", "20261116_b"):
        box["media"](n)
    fail = {"n": 0}

    def bad(uid, token, url, text, cover=""):
        fail["n"] += 1
        raise RuntimeError("HTTP 500")
    rc, res = hp.run(dict(ENV), at(12, 16), False, queue=box["q"], state=box["st"],
                     quota_path=box["root"] / "docs/marketing/channels/caffaine/post_quota.json",
                     check=lambda u, w: None, saver=lambda *a: True, prefix="CAFFAINE_", per_day_max=2,
                     video_publishers={"ig": lambda *a, **k: {"id": "ig1", "link": "L"}, "threads": bad}, slots=SLOTS)
    assert rc == 1 and set(res["posted"]) == {"ig"}
    rc, res = box["go"](at(13, 44))                                   # 保底：同一則補 Threads
    assert res["item"] == "20261116_a" and set(res["posted"]) == {"threads"}


def test_publish_at指定晚上時段_中午不會先發(box):
    mk_video(box["q"], "20261116_a", publish_at="2026-11-16T21:00+08:00")
    box["media"]("20261116_a")
    rc, res = box["go"](at(12, 16))
    assert "佇列已空" in res["summary"] and not box["calls"]
    rc, res = box["go"](at(21, 1))
    assert res["item"] == "20261116_a" and set(res["posted"]) == {"ig", "threads"}


def test_沒有slots的頻道行為不變(box):
    for n in ("20261116_a", "20261116_b"):
        mk_video(box["q"], n)
        box["media"](n)
    box["go"](at(12, 16), slots=None)
    rc, res = box["go"](at(12, 20), slots=None)                       # 沒有時段限制：per_day 2 → 同一時段可再發
    assert set(res["posted"]) == {"ig", "threads"}
    assert "slot" not in json.loads((box["st"] / "posted.json").read_text())["20261116_a"]


# ---------- 影片放 Release ----------
def test_影片在Release_不用放進main_網址第一條是release(box):
    d = mk_video(box["q"], "20261116_a")
    it = hp.read_item(d)
    assert it["release"] and hp.validate(it) == []                    # meta.video_src 指 media 分支 → 不缺檔
    assert hp.video_sources(it) == []                                 # 還沒 sync：沒有可用網址
    box["media"]("20261116_a")
    it = hp.read_item(d)
    assert hp.video_sources(it) == [("release", REL + "caffaine__20261116_a.mp4", "*")]
    assert hp.cover_src(it) == (hp.RAW + "docs/marketing/channels/caffaine/queue/20261116_a/cover.jpg", "image/jpeg")
    (d / "cover.jpg").unlink()
    assert hp.cover_src(hp.read_item(d)) == (REL + "caffaine__20261116_a__cover.jpg", "*")
    rc, res = box["go"](at(12, 16))
    assert {c[1] for c in box["calls"]} == {REL + "caffaine__20261116_a.mp4"}
    assert [c[2] for c in box["calls"] if c[0] == "ig"] == [REL + "caffaine__20261116_a__cover.jpg"]
    posted = json.loads((box["st"] / "posted.json").read_text())["20261116_a"]
    assert posted["ig"]["video_via"] == "release" and posted["threads"]["format"] == "video"


def test_影片也放在佇列_release失敗退回raw(box):
    d = mk_video(box["q"], "20261116_a", local=True)
    box["media"]("20261116_a")
    it = hp.read_item(d)
    assert [x[0] for x in hp.video_sources(it)] == ["release", "raw"]
    tried = []

    def pub(uid, token, url, text, cover=""):
        tried.append(url)
        if url.startswith(REL):
            raise RuntimeError("2207026 影片抓不到")
        return {"id": "x", "link": "L"}
    rc, res = hp.run(dict(ENV), at(12, 16), False, queue=box["q"], state=box["st"],
                     quota_path=box["root"] / "docs/marketing/channels/caffaine/post_quota.json",
                     check=lambda u, w: None, saver=lambda *a: True, prefix="CAFFAINE_", per_day_max=2,
                     video_publishers={"ig": pub, "threads": pub}, slots=SLOTS)
    assert rc == 0 and set(res["posted"]) == {"ig", "threads"}
    assert res["posted"]["ig"]["video_via"] == "raw"


def test_release頻道_沒有影片也沒有video_src_報錯(box):
    d = mk_video(box["q"], "20261116_a", local=True)
    (d / "video.mp4").unlink()
    assert any("video.mp4" in e for e in hp.validate(hp.read_item(d)))


def test_沒註冊release的頻道_影片規則不變(tmp_path, monkeypatch):
    monkeypatch.setattr(hp, "ROOT", tmp_path)
    q = tmp_path / "docs/marketing/channels/healing/queue"
    d = mk_video(q, "20261116v_a", local=True)
    it = hp.read_item(d)
    assert "release" not in it and [x[0] for x in hp.video_sources(it)] == ["raw"]
    assert hp.cover_src(it)[1] == "image/jpeg"
    d2 = mk_video(q, "20261116v_b")                                   # 頻道④寫 video_src 沒用：還是要有 video.mp4
    assert any("video.mp4" in e for e in hp.validate(hp.read_item(d2)))


def test_verify_reels_test_用Release測試片_不發布不寫posted(box):
    rc, res = hp.run_verify(dict(ENV), at(12, 0), True, queue=box["q"], state=box["st"], prefix="CAFFAINE_",
                            target="@reels-test")                     # 空跑：還沒有測試片也綠燈，說明會做什麼
    assert rc == 0 and "3 秒測試片" in res["summary"]
    box["media"]("@reels-test")
    seen = []

    def ver(p):
        return lambda uid, token, url, text, cover="": seen.append((p, url, cover)) or f"c-{p}"
    rc, res = hp.run_verify(dict(ENV), at(12, 0), queue=box["q"], state=box["st"], check=lambda u, w: None,
                            prefix="CAFFAINE_", target="@reels-test",
                            video_verifiers={"ig": ver("ig"), "threads": ver("threads")})
    assert rc == 0, res
    assert seen == [("ig", REL + "caffaine__reels-test.mp4", REL + "caffaine__reels-test__cover.jpg"),
                    ("threads", REL + "caffaine__reels-test.mp4", "")]
    v = json.loads((box["st"] / "verify.json").read_text())["video"]
    assert v["ig"]["url_via"] == "release" and v["threads"]["item"] == "@reels-test"
    assert not (box["st"] / "posted.json").exists()
    rc, res = hp.run_verify(dict(ENV), at(12, 0), queue=box["q"], state=box["st"], target="@nope", prefix="CAFFAINE_")
    assert rc == 1 and "@nope" in res["summary"]


def test_check_public_星號用GET(monkeypatch):
    import requests
    seen = []

    class R:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(requests, "get", lambda url, **kw: seen.append((url, kw["stream"])) or R())
    monkeypatch.setattr(requests, "head", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不用 HEAD")))
    hp.check_public(REL + "x.mp4", "*")
    assert seen == [(REL + "x.mp4", True)]


# ---------- channel_media ----------
class FakeGH:
    def __init__(self):
        self.assets_, self.uploads, self.deleted, self.branches = {}, [], [], []
        self.rel = None

    def release(self):
        self.rel = self.rel or {"id": 7}
        return self.rel

    def assets(self, rel):
        return dict(self.assets_)

    def delete_asset(self, aid):
        self.deleted.append(aid)
        self.assets_ = {k: v for k, v in self.assets_.items() if v["id"] != aid}

    def upload(self, rel, name, data, ctype):
        self.uploads.append((name, len(data), ctype))
        self.assets_[name] = {"id": len(self.uploads), "name": name}
        return self.assets_[name]

    def delete_branch(self, br):
        self.branches.append(br)
        return True


@pytest.fixture
def mbox(box, monkeypatch):
    chs = {"caffaine": {"code": "caffaine", "name": "③", "queue": box["q"], "state": box["st"], "video_host": "release"}}
    monkeypatch.setattr(cm.HP, "channel", lambda code: chs[code])
    return box


def test_sync_從media分支或佇列上傳_一樣就跳過_發完的不傳(mbox):
    q, st = mbox["q"], mbox["st"]
    mk_video(q, "20261116_a")                                         # 影片在 media 分支
    mk_video(q, "20261116_b", local=True)                             # 影片在佇列
    mk_video(q, "20261116_d", status="draft")                         # draft 也先傳（給驗證用）
    mk_video(q, "20261115_old")
    (st / "posted.json").write_text(json.dumps({"20261115_old": {"ig": {"at": "x"}, "threads": {"at": "x"}}}))
    fetched = []

    def fetch(br, fname):
        fetched.append((br, fname))
        return b"MP4" * 10 if fname == "video.mp4" else None
    gh = FakeGH()
    log = cm.sync("caffaine", gh=gh, fetch=fetch, now=at(10, 0))
    names = [u[0] for u in gh.uploads]
    assert names == ["caffaine__20261116_a.mp4", "caffaine__20261116_a__cover.jpg",
                     "caffaine__20261116_b.mp4", "caffaine__20261116_b__cover.jpg",
                     "caffaine__20261116_d.mp4", "caffaine__20261116_d__cover.jpg"], log
    assert ("media/caffaine/20261115_old", "video.mp4") not in fetched
    assert all(u[2] == ("video/mp4" if u[0].endswith(".mp4") else "image/jpeg") for u in gh.uploads)
    m = json.loads((st / "media.json").read_text())
    assert m["20261116_a"]["video"] == REL + "caffaine__20261116_a.mp4" and m["20261116_a"]["src"] == "media/caffaine/20261116_a"
    assert m["20261116_b"]["src"] == "queue"
    n = len(gh.uploads)
    log = cm.sync("caffaine", gh=gh, fetch=fetch, now=at(10, 5))
    assert len(gh.uploads) == n and all("跳過" in x for x in log)
    # 換了影片 → 先刪舊資產再上傳
    (q / "20261116_b" / "video.mp4").write_bytes(b"NEW")
    cm.sync("caffaine", gh=gh, fetch=fetch, now=at(10, 6))
    assert gh.uploads[-2][0] == "caffaine__20261116_b.mp4" and gh.deleted


def test_sync_找不到影片_只記下來不擋其他(mbox):
    mk_video(mbox["q"], "20261116_a")
    mk_video(mbox["q"], "20261116_b", local=True)
    gh = FakeGH()
    log = cm.sync("caffaine", gh=gh, fetch=lambda br, f: None, now=at(10, 0))
    assert any("20261116_a：找不到影片" in x for x in log)
    assert [u[0] for u in gh.uploads][0] == "caffaine__20261116_b.mp4"


def test_sync_佇列空不連GitHub也不寫檔(mbox):
    assert cm.sync("caffaine", gh=None, fetch=lambda *a: None) == []
    assert not (mbox["st"] / "media.json").exists()


def test_clean_發完超過3天才刪資產與分支_測試片1天(mbox):
    q, st = mbox["q"], mbox["st"]
    mk_video(q, "20261110_a")
    mk_video(q, "20261115_b")
    mk_video(q, "20261116_c")
    for n in ("20261110_a", "20261115_b", "20261116_c", "@reels-test"):
        mbox["media"](n)
    m = json.loads((st / "media.json").read_text())
    m["@reels-test"]["at"] = "2026-11-14T10:00:00+08:00"
    (st / "media.json").write_text(json.dumps(m))
    (st / "posted.json").write_text(json.dumps({
        "20261110_a": {"ig": {"at": "2026-11-10T12:16:00+08:00"}, "threads": {"at": "2026-11-10T12:17:00+08:00"}},
        "20261115_b": {"ig": {"at": "2026-11-15T21:01:00+08:00"}, "threads": {"at": "2026-11-15T21:01:00+08:00"}},
        "20261116_c": {"ig": {"at": "2026-11-10T12:16:00+08:00"}}}))          # 只發一半 → 不刪
    gh = FakeGH()
    for n in ("20261110_a", "20261115_b", "20261116_c", "@reels-test"):
        gh.upload(None, cm.asset_name("caffaine", n), b"x", "video/mp4")
        gh.upload(None, cm.asset_name("caffaine", n, "cover"), b"x", "image/jpeg")
    log = cm.clean("caffaine", keep_days=3, gh=gh, now=at(12, 0))
    assert gh.branches == ["media/caffaine/20261110_a"]
    assert set(gh.assets_) == {cm.asset_name("caffaine", n, k) for n in ("20261115_b", "20261116_c")
                               for k in ("video", "cover")}
    assert set(json.loads((st / "media.json").read_text())) == {"20261115_b", "20261116_c"}
    assert cm.clean("caffaine", gh=FakeGH(), now=at(12, 5)) == ["沒有要清的影片"]


def test_testclip_寫reels_test(mbox):
    gh = FakeGH()
    url = cm.testclip("caffaine", gh=gh, maker=lambda d: (b"MP4", b"JPG"), now=at(11, 0))
    assert url == REL + "caffaine__reels-test.mp4"
    m = json.loads((mbox["st"] / "media.json").read_text())["@reels-test"]
    assert m["cover"] == REL + "caffaine__reels-test__cover.jpg" and m["src"] == "ffmpeg"


def test_make_clip_真的產出3秒直式影片(tmp_path):
    import shutil
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("沒有 ffmpeg")
    v, c = cm.make_clip(tmp_path)
    (tmp_path / "o.mp4").write_bytes(v)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height:format=duration",
                          "-of", "json", str(tmp_path / "o.mp4")], capture_output=True, text=True).stdout
    d = json.loads(out)
    vs = [s for s in d["streams"] if s.get("width")][0]
    assert (vs["codec_name"], vs["width"], vs["height"]) == ("h264", 1080, 1920)
    assert any(s["codec_name"] == "aac" for s in d["streams"])
    assert 2.9 <= float(d["format"]["duration"]) <= 3.2 and c[:2] == b"\xff\xd8"


def test_stage_推到media分支_不動工作目錄_第二次接在後面(tmp_path, monkeypatch):
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    for k, v in (("user.name", "t"), ("user.email", "t@example.com")):
        subprocess.run(["git", "-C", str(work), "config", k, v], check=True)
    subprocess.run(["git", "-C", str(work), "remote", "add", "origin", str(remote)], check=True)
    q = work / "docs/marketing/channels/caffaine/queue"
    d = q / "20261116_a"
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"status": "draft"}), encoding="utf-8")
    monkeypatch.setattr(cm.HP, "channel", lambda code: {"code": code, "queue": q, "state": work / "st"})
    vid, cov = tmp_path / "v.mp4", tmp_path / "c.jpg"
    vid.write_bytes(b"VIDEO1")
    cov.write_bytes(b"COVER")
    br = cm.stage("caffaine", "20261116_a", vid, cov, cwd=work)
    assert br == "media/caffaine/20261116_a"
    ls = subprocess.run(["git", "--git-dir", str(remote), "ls-tree", "--name-only", br], capture_output=True,
                        text=True).stdout.split()
    assert ls == ["cover.jpg", "video.mp4"]
    assert json.loads((d / "meta.json").read_text()) == {"status": "draft", "format": "video", "video_src": br}
    assert subprocess.run(["git", "-C", str(work), "status", "--porcelain"], capture_output=True,
                          text=True).stdout.strip() == "?? docs/"             # 只有 meta.json 自己的變動，沒多出影片
    vid.write_bytes(b"VIDEO2")
    cm.stage("caffaine", "20261116_a", vid, None, cwd=work)
    log = subprocess.run(["git", "--git-dir", str(remote), "log", "--format=%s", br], capture_output=True,
                         text=True).stdout.strip().splitlines()
    assert len(log) == 2                                                  # 一般 push 接在後面，沒有 force
    assert subprocess.run(["git", "--git-dir", str(remote), "show", f"{br}:video.mp4"], capture_output=True
                          ).stdout == b"VIDEO2"


# ---------- 設定與工作流 ----------
def test_caffaine設定_兩時段_release_每天2則():
    c = hp.load_channels()["caffaine"]
    assert c["slots"] == SLOTS and c["video_host"] == "release" and c["per_day"] == 2
    q = json.loads(c["quota"].read_text(encoding="utf-8"))
    assert q["live"] is True and q["per_day"] == 2
    for code in ("healing", "tech"):                                   # 其他頻道不變
        o = hp.load_channels()[code]
        assert "slots" not in o and "video_host" not in o
    assert not list(c["queue"].iterdir()) or all(
        json.loads((d / "meta.json").read_text(encoding="utf-8")).get("status") != "approved"
        for d in c["queue"].iterdir() if d.is_dir())                  # 沒有 Andy 看過的內容不准排進佇列


def test_channel_post入口_caffaine帶slots_註冊release(monkeypatch):
    seen = {}

    def fake_run(env, now, dry, **kw):
        seen.clear()
        seen.update(kw)
        return 0, {"mode": "dry-run", "summary": "ok", "posted": {}, "notes": []}
    monkeypatch.setattr(cp.HP, "run", fake_run)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(cp.HP, "MEDIA", {})
    assert cp.main(["--channel", "caffaine", "--dry-run"]) == 0
    assert seen["slots"] == SLOTS and seen["per_day_max"] == 2
    assert cp.HP.MEDIA == {ROOT / "docs/marketing/channels/caffaine/queue": ROOT / "docs/marketing/channels/caffaine/state"}
    cp.HP.MEDIA.clear()
    assert cp.HP.main(["--dry-run"]) == 0 and "slots" not in seen and cp.HP.MEDIA == {}    # 頻道④不變


def test_工作流有Release步驟_testclip_清理_逾時夠等影片():
    txt = (ROOT / ".github/workflows/channel_post.yml").read_text(encoding="utf-8")
    d = yaml.safe_load(txt)
    steps = d["jobs"]["post"]["steps"]
    names = [s.get("name", "") for s in steps]
    i_sync = next(i for i, n in enumerate(names) if "Release" in n and "影片傳到" in n)
    i_post = next(i for i, n in enumerate(names) if n.startswith("發文（"))
    i_clean = next(i for i, n in enumerate(names) if n.startswith("清掉發完"))
    assert i_sync < i_post < i_clean
    assert "channel_media.py sync" in steps[i_sync]["run"] and "testclip" in steps[i_sync]["run"]
    assert steps[i_sync]["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert steps[i_clean]["continue-on-error"] is True
    assert d["jobs"]["post"]["timeout-minutes"] >= 50
    assert "@reels-test" in txt
