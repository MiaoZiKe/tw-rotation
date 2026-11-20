"""頻道④影片貼文（2026-11-15，plan_202611_影片為主.md T5～T7）：IG Reels／Threads 影片、輪詢、網址候選換條、驗證只建容器、
--target 只驗一則、--prepare 同步到 site/media、文章存檔、輪播向下相容。"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts import healing_post as hp

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 16, 20, 30, tzinfo=TPE)
TOK_I, TOK_T = "IGAA_HEALING_VIDEO_SECRET_aaaa", "THAA_HEALING_VIDEO_SECRET_bbbb"
ENV = {"HEALING_IG_ACCESS_TOKEN": TOK_I, "HEALING_THREADS_ACCESS_TOKEN": TOK_T,
       "HEALING_IG_USER_ID": "9001", "HEALING_THREADS_USER_ID": "9002"}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    hp.SP._SECRETS.clear()
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)


def mk_video(q, name, status="approved", cover=True, publish_at=None, caption="一年工作 2,027 小時"):
    d = q / name
    d.mkdir(parents=True)
    (d / "video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"v" * 100)
    if cover:
        (d / "cover.jpg").write_bytes(b"jpg")
    (d / "caption.txt").write_text(caption, encoding="utf-8")
    (d / "meta.json").write_text(json.dumps({"format": "video", "platforms": ["ig", "threads"], "status": status,
                                             "publish_at": publish_at}), encoding="utf-8")
    return d


def mk_carousel(q, name, status="approved"):
    d = q / name
    d.mkdir(parents=True)
    for i in (1, 2, 3):
        (d / f"{i}.png").write_bytes(b"x")
        (d / f"{i}.jpg").write_bytes(b"x")
    (d / "caption.txt").write_text("輪播", encoding="utf-8")
    (d / "meta.json").write_text(json.dumps({"platforms": ["ig", "threads"], "status": status, "publish_at": None}),
                                 encoding="utf-8")
    return d


@pytest.fixture
def box(tmp_path, monkeypatch):
    root = tmp_path
    q = root / "docs/marketing/channels/healing/queue"
    st = root / "docs/marketing/channels/healing/state"
    q.mkdir(parents=True)
    quota = root / "post_quota.json"
    quota.write_text('{"live": true, "per_day": 1}', encoding="utf-8")
    monkeypatch.setattr(hp, "ROOT", root)
    monkeypatch.setattr(hp.SP, "http", lambda m, url, **kw: {"access_token": kw["params"]["access_token"],
                                                            "expires_in": 5184000})
    calls = []

    def vpub(p):
        def f(uid, token, url, text, cover=""):
            calls.append(("pub-" + p, url, cover, text))
            return {"id": p + "-v1", "link": f"https://example.com/{p}/v1"}
        return f

    def vver(p):
        def f(uid, token, url, text, cover=""):
            calls.append(("ver-" + p, url, cover, text))
            return "c-" + p
        return f

    def carousel_fail(*a, **k):
        raise AssertionError("影片貼文不該走輪播函式")

    def go(env=ENV, dry=False, check=lambda u, w: None, vpubs=None, vvers=None):
        return hp.run(dict(env), NOW, dry, queue=q, state=st, quota_path=quota,
                      publishers={"ig": carousel_fail, "threads": carousel_fail}, check=check, saver=lambda *a: True,
                      verifiers={"ig": carousel_fail, "threads": carousel_fail},
                      video_publishers=vpubs or {"ig": vpub("ig"), "threads": vpub("threads")},
                      video_verifiers=vvers or {"ig": vver("ig"), "threads": vver("threads")})
    return {"root": root, "q": q, "st": st, "calls": calls, "go": go, "vver": vver, "vpub": vpub}


def test_validate_影片不需要圖_缺影片報錯(box):
    d = mk_video(box["q"], "20261116v_a")
    it = hp.read_item(d)
    assert it["is_video"] and hp.validate(it) == []
    (d / "video.mp4").unlink()
    assert any("video.mp4" in e for e in hp.validate(hp.read_item(d)))
    m = json.loads((d / "meta.json").read_text())
    m["format"] = "gif"
    (d / "meta.json").write_text(json.dumps(m))
    assert any("format" in e for e in hp.validate(hp.read_item(d)))


def test_輪播預設不變(box):
    it = hp.read_item(mk_carousel(box["q"], "20261116_c"))
    assert it["format"] == "carousel" and not it["is_video"] and hp.validate(it) == []


def test_網址候選順序_正式站同步後優先(box):
    d = mk_video(box["q"], "20261116v_a")
    it = hp.read_item(d)
    assert [x[0] for x in hp.video_sources(it)] == ["raw"]
    assert hp.prepare(box["q"])            # 同步到 site/media/healing/<資料夾>/
    site = box["root"] / "site/media/healing/20261116v_a/video.mp4"
    assert site.read_bytes() == (d / "video.mp4").read_bytes()
    assert (box["root"] / "site/media/healing/20261116v_a/cover.jpg").exists()
    assert hp.prepare(box["q"]) == []      # 內容一樣不重寫
    src = hp.video_sources(it)
    assert [x[0] for x in src] == ["site", "raw"]
    assert src[0][1] == "https://liguligu-puipui.com/media/healing/20261116v_a/video.mp4" and src[0][2] == "video/mp4"
    assert src[1][1].startswith(hp.RAW) and src[1][2] == ""
    assert [x[0] for x in hp.video_sources(it, prefer="raw")] == ["raw", "site"]


def test_發影片_IG_Reels與Threads_紀錄(box):
    mk_video(box["q"], "20261116v_a")
    rc, res = box["go"]()
    kinds = [c[0] for c in box["calls"]]
    assert rc == 0 and kinds == ["ver-ig", "pub-ig", "ver-threads", "pub-threads"]
    ig = [c for c in box["calls"] if c[0] == "pub-ig"][0]
    assert ig[1].endswith("/20261116v_a/video.mp4") and ig[2].endswith("/cover.jpg")
    th = [c for c in box["calls"] if c[0] == "pub-threads"][0]
    assert th[2] == ""                      # Threads 不帶封面
    p = json.loads((box["st"] / "posted.json").read_text())["20261116v_a"]
    assert p["ig"]["format"] == "video" and p["ig"]["video_via"] == "raw" and p["threads"]["id"] == "threads-v1"
    m = json.loads((box["q"] / "20261116v_a/meta.json").read_text())
    assert m["status"] == "posted" and m["urls"]["ig"] == "https://example.com/ig/v1"
    v = json.loads((box["st"] / "verify.json").read_text())
    assert v["video"]["ig"]["url_via"] == "raw" and v["ig"]["verified"]


def test_第一條網址失敗換下一條(box):
    mk_video(box["q"], "20261116v_a")
    hp.prepare(box["q"])
    tried = []

    def ig(uid, token, url, text, cover=""):
        tried.append(url)
        if "liguligu" in url:
            raise RuntimeError("ig 影片處理失敗：ERROR 2207026")
        return {"id": "ig-v", "link": ""}
    rc, res = box["go"](vpubs={"ig": ig, "threads": box["vpub"]("threads")})
    assert rc == 0 and len(tried) == 2 and "liguligu" in tried[0] and tried[1].startswith(hp.RAW)
    assert json.loads((box["st"] / "posted.json").read_text())["20261116v_a"]["ig"]["video_via"] == "raw"
    assert any("site" in n for n in res["notes"])


def test_網址抓不到也換下一條_全失敗紅燈不外洩權杖(box):
    mk_video(box["q"], "20261116v_a")
    hp.prepare(box["q"])

    def check(u, want):
        if want == "video/mp4":
            raise RuntimeError("HTTP 404")

    def bad(uid, token, url, text, cover=""):
        raise RuntimeError("HTTP 400 抓不到影片 " + token)
    rc, res = box["go"](check=check, vpubs={"ig": bad, "threads": bad})
    assert rc == 1 and "影片所有網址都失敗" in res["errors"]["ig"]
    assert "site 網址抓不到" in res["errors"]["ig"] and TOK_I not in json.dumps(res, ensure_ascii=False)
    assert not (box["st"] / "posted.json").exists() or "20261116v_a" not in json.loads(
        (box["st"] / "posted.json").read_text())


def test_封面抓不到就不帶封面_不擋發文(box):
    mk_video(box["q"], "20261116v_a")

    def check(u, want):
        if u.endswith("cover.jpg"):
            raise RuntimeError("HTTP 404")
    rc, res = box["go"](check=check)
    assert rc == 0 and [c for c in box["calls"] if c[0] == "pub-ig"][0][2] == ""
    assert any("封面" in n for n in res["notes"])


def test_空跑列出影片網址(box, capsys):
    mk_video(box["q"], "20261116v_a")
    rc, res = box["go"](dry=True)
    out = capsys.readouterr().out
    assert rc == 0 and not box["calls"] and "會發影片" in out and "video.mp4" in out


def test_驗證模式_target只驗指定影片_draft也可以_不動排程輪播(box):
    mk_carousel(box["q"], "20261116_marriage")                 # 排程中的輪播（approved）
    mk_video(box["q"], "20261116v_worktime", status="draft")
    seen = []
    vv = {p: (lambda p: lambda uid, t, url, x, c="": seen.append((p, url)) or "vc-" + p)(p) for p in ("ig", "threads")}
    no_carousel = {p: (lambda *a: (_ for _ in ()).throw(AssertionError("不該驗輪播"))) for p in ("ig", "threads")}
    rc, res = hp.run_verify(dict(ENV), NOW, queue=box["q"], state=box["st"], check=lambda u, w: None,
                            saver=lambda *a: True, verifiers=no_carousel, video_verifiers=vv,
                            target="20261116v_worktime")
    assert rc == 0, res
    assert [s[0] for s in seen] == ["ig", "threads"] and all("20261116v_worktime/video.mp4" in s[1] for s in seen)
    assert res["containers"]["ig"]["id"] == "vc-ig" and res["containers"]["threads"]["status"] == "FINISHED"
    assert res["containers"]["ig"]["urls"] == {"raw": "FINISHED 容器 vc-ig"}
    v = json.loads((box["st"] / "verify.json").read_text())
    assert v["video"]["ig"]["item"] == "20261116v_worktime" and "ig" not in v      # 不動原本輪播驗證紀錄
    assert not (box["st"] / "posted.json").exists()
    assert json.loads((box["q"] / "20261116v_worktime/meta.json").read_text())["status"] == "draft"
    assert json.loads((box["q"] / "20261116_marriage/meta.json").read_text())["status"] == "approved"
    last = json.loads((box["st"] / "last_run.json").read_text())
    assert last["containers"]["ig"]["id"] == "vc-ig"
    # 空跑：不呼叫
    seen.clear()
    rc, res = hp.run_verify(dict(ENV), NOW, True, queue=box["q"], state=box["st"], video_verifiers=vv,
                            target="20261116v_worktime")
    assert rc == 0 and not seen and "影片" in res["summary"]
    # 不存在／怪字元的 target
    assert hp.run_verify(dict(ENV), NOW, queue=box["q"], state=box["st"], target="../x")[0] == 1
    assert hp.run_verify(dict(ENV), NOW, queue=box["q"], state=box["st"], target="nope")[0] == 1


def test_驗證模式_影片失敗紅燈(box):
    mk_video(box["q"], "20261116v_a", status="draft")

    def bad(uid, t, url, x, c=""):
        raise RuntimeError("ig 影片處理失敗：ERROR")
    rc, res = hp.run_verify(dict(ENV), NOW, queue=box["q"], state=box["st"], check=lambda u, w: None,
                            saver=lambda *a: True, video_verifiers={"ig": bad, "threads": bad},
                            target="20261116v_a")
    assert rc == 1 and "影片所有網址都失敗" in res["errors"]["ig"]
    assert not (box["st"] / "verify.json").exists()


def test_EAA權杖_驗證影片走graph_facebook(box, monkeypatch):
    mk_video(box["q"], "20261116v_a", status="draft")
    eaa = "EAA_FB_LOGIN_TOKEN_xxxxxxxxxxxx"
    monkeypatch.setattr(hp, "fb_diag", lambda tok, acc, via: {"lines": ["ok"], "missing": [], "problems": [],
                                                               "cands": [{"id": "1784", "username": "talk", "via": "me_edge"}],
                                                               "ids": ["1784"]})
    posts = []

    def http(m, url, **kw):
        if m == "POST":
            posts.append((url, dict(kw["data"])))
            return {"id": "777"}
        if "refresh_access_token" in url:
            return {"access_token": kw["params"]["access_token"]}
        return {"status_code": "FINISHED", "status": "FINISHED"} if "graph.facebook" in url else {"status": "FINISHED"}
    monkeypatch.setattr(hp.SP, "http", http)
    env = {"HEALING_IG_ACCESS_TOKEN": eaa, "HEALING_THREADS_ACCESS_TOKEN": TOK_T, "HEALING_THREADS_USER_ID": "9002"}
    rc, res = hp.run_verify(env, NOW, queue=box["q"], state=box["st"], check=lambda u, w: None,
                            saver=lambda *a: True, target="20261116v_a")
    assert rc == 0, res
    ig = [p for p in posts if "graph.facebook.com" in p[0]]
    assert ig and ig[0][0].endswith("/1784/media") and ig[0][1]["media_type"] == "REELS"
    assert ig[0][1]["share_to_feed"] == "false" and ig[0][1]["cover_url"].endswith("cover.jpg")
    th = [p for p in posts if "graph.threads.net" in p[0]]
    assert th and th[0][1]["media_type"] == "VIDEO" and th[0][1]["video_url"].endswith("video.mp4")
    assert not any("publish" in p[0] for p in posts)                 # 驗證不發布
    v = json.loads((box["st"] / "verify.json").read_text())
    assert v["video"]["ig"]["via"] == "me_edge" and eaa not in json.dumps(v)


def test_IGAA權杖走graph_instagram_發布與輪詢(monkeypatch):
    seq = iter([{"status_code": "IN_PROGRESS"}, {"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}])
    log = []

    def http(m, url, **kw):
        log.append((m, url, kw.get("data") or kw.get("params")))
        if m == "POST" and url.endswith("/media"):
            return {"id": "c1"}
        if m == "POST" and url.endswith("/media_publish"):
            return {"id": "p1"}
        if "permalink" in str(kw.get("params")):
            return {"permalink": "https://www.instagram.com/reel/X/"}
        return next(seq)
    monkeypatch.setattr(hp.SP, "http", http)
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)
    r = hp.publish_ig_video("9001", "IGAA_tok", "https://v/x.mp4", "cap", "https://v/c.jpg")
    assert r == {"id": "p1", "link": "https://www.instagram.com/reel/X/"}
    assert all(u.startswith("https://graph.instagram.com/") for _, u, _ in log)
    polls = [x for x in log if x[0] == "GET" and "status_code" in str(x[2])]
    assert len(polls) == 3


def test_輪詢_ERROR帶原因_逾時(monkeypatch):
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)
    monkeypatch.setattr(hp.SP, "http", lambda m, u, **kw: {"status_code": "ERROR", "status": "Error: 2207026 格式不支援"})
    with pytest.raises(RuntimeError, match="2207026"):
        hp.wait_video("https://graph.instagram.com/v24.0", "t", "c1", "ig 影片", "status_code")
    monkeypatch.setattr(hp.SP, "http", lambda m, u, **kw: {"status": "IN_PROGRESS"})
    with pytest.raises(RuntimeError, match="逾時"):
        hp.wait_video(hp.SP.THREADS_HOST, "t", "c1", "threads 影片", "status", timeout=30)
    # 剛建立查不到（2207006）不算失敗
    seq = iter([RuntimeError("HTTP 400 2207006"), {"status": "FINISHED"}])

    def http(m, u, **kw):
        x = next(seq)
        if isinstance(x, Exception):
            raise x
        return x
    monkeypatch.setattr(hp.SP, "http", http)
    hp.wait_video(hp.SP.THREADS_HOST, "t", "c1", "threads 影片", "status")


def test_Threads影片發布流程(monkeypatch):
    log = []

    def http(m, url, **kw):
        log.append((m, url, dict(kw.get("data") or {})))
        if m == "POST" and url.endswith("/threads"):
            return {"id": "tc"}
        if url.endswith("/threads_publish"):
            return {"id": "tp"}
        if "permalink" in str(kw.get("params")):
            return {"permalink": "https://www.threads.com/@talk/post/Y"}
        return {"status": "FINISHED"}
    monkeypatch.setattr(hp.SP, "http", http)
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)
    r = hp.publish_threads_video("9002", "TH_tok", "https://v/x.mp4", "文字")
    assert r["id"] == "tp" and r["link"].endswith("/Y")
    c = [x for x in log if x[1].endswith("/9002/threads")][0][2]
    assert c["media_type"] == "VIDEO" and c["video_url"] == "https://v/x.mp4" and "image_url" not in c


def test_輪播佇列有video檔但沒設format_照舊走輪播(box):
    d = mk_carousel(box["q"], "20261116_marriage")
    (d / "video.mp4").write_bytes(b"v")
    it = hp.read_item(d)
    assert not it["is_video"] and hp.validate(it) == []
    assert hp.prepare(box["q"]) == [] or not (box["root"] / "site/media").exists()


def test_實際佇列_影片資料夾格式正確():
    q = hp.QUEUE / "20261116v_worktime"
    if not q.exists():
        pytest.skip("影片佇列資料夾還沒建")
    it = hp.read_item(q)
    assert it["is_video"] and hp.validate(it) == [] and it["meta"]["status"] in ("draft", "approved", "posted")
    assert (q / "video.mp4").stat().st_size <= hp.VIDEO_MAX_BYTES


def test_文章存檔_影片貼文放封面連結與文案(tmp_path, monkeypatch):
    from scripts import healing_article as ha
    ch = tmp_path / "healing"
    d = mk_video(ch / "queue", "20261116v_worktime", status="draft",
                 caption="一年工作 2,027 小時\n\n第一段。\n\n資料來源：\n・勞動部\n\n#談晴說礙 #工時")
    monkeypatch.setattr(ha, "CH", ch)
    monkeypatch.setattr(ha, "IMG", tmp_path / "img")
    monkeypatch.setattr(ha, "ROOT", tmp_path)
    (tmp_path / "img").mkdir()
    ha.posted = {}
    cfg = {"slug": "worktime", "date": "2026-11-16", "summary": "s", "alts": ["封面"], "sources": [], "confidence": "中"}
    post = ha.build("20261116v_worktime", cfg)
    ts = [b["t"] for b in post["blocks"]]
    assert ts[:3] == ["h", "img", "links"] and post["title"] == "一年工作 2,027 小時"
    assert post["blocks"][1]["items"][0]["src"] == "articles/healing/img/2026-11-16-healing-worktime-cover.jpg"
    assert (tmp_path / "img/2026-11-16-healing-worktime-cover.jpg").exists()
    assert post["blocks"][2]["items"][0]["url"].endswith("/20261116v_worktime/video.mp4")
    assert {"t": "p", "text": "第一段。"} in post["blocks"] and post["social"]["format"] == "video"
    assert post["tags"] == ["談晴說礙", "工時"]
    # 沒有封面：至少有影片連結與文案
    (d / "cover.jpg").unlink()
    post = ha.build("20261116v_worktime", cfg)
    assert [b["t"] for b in post["blocks"]][:2] == ["h", "links"]
    # 已發出：補上網址
    ha.posted = {"20261116v_worktime": {"at": "2026-11-16T20:30:00+08:00", "ig": {"link": "https://ig/r"},
                                         "threads": {"link": "https://th/p"}}}
    post = ha.build("20261116v_worktime", cfg)
    assert post["social"]["ig"] == "https://ig/r" and any(b["t"] == "links" and b.get("title") == "公開網址"
                                                         for b in post["blocks"])


def test_驗證模式_每條網址都試_記錄結果_正式站優先(box):
    mk_video(box["q"], "20261116v_a", status="draft")
    hp.prepare(box["q"])
    seen = []

    def ig(uid, t, url, x, c=""):
        seen.append(url)
        if url.startswith(hp.RAW):
            raise RuntimeError("ig 影片處理失敗：ERROR 2207026 不支援的格式")
        return "site-c"
    th = lambda uid, t, url, x, c="": seen.append(url) or "th-c"   # noqa: E731
    rc, res = hp.run_verify(dict(ENV), NOW, queue=box["q"], state=box["st"], check=lambda u, w: None,
                            saver=lambda *a: True, video_verifiers={"ig": ig, "threads": th}, target="20261116v_a")
    assert rc == 0 and len(seen) == 4                    # 兩個平台 × 兩條網址
    v = json.loads((box["st"] / "verify.json").read_text())["video"]
    assert v["ig"]["url_via"] == "site" and "2207026" in v["ig"]["urls"]["raw"]
    assert v["threads"]["urls"] == {"site": "FINISHED 容器 th-c", "raw": "FINISHED 容器 th-c"}
    assert hp.video_via(box["st"], "ig") == "site"
