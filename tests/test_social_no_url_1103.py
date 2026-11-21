"""2026-11-03 Andy：「首先 網頁都不公開先，人數沒有起來，沒有建立信任關係，我覺得不妥」
→ 自動發文（Threads 主文／串文／留言、IG 文案）一律不放網站網址與「完整盤勢見網站」這類導流字；留言只留免責那句。
lint 出現網址即失敗；發文程式送出前自動移除（舊 manifest、補發、手寫佇列檔都一樣）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import threads_lint as L  # noqa: E402
import threads_v2 as V  # noqa: E402

FX = ROOT / "tests" / "fixtures" / "threads_v2"
OLD_REPLY = ("完整盤勢見網站（其餘新聞、盤面細項等）\n👉 法人、融資融券完整排行都在網站，個股一檔一檔查得到：\n"
             "https://liguligu-puipui.com/?u=th-cl-20261103#market/inst")


def test_開關預設關閉():
    import social_snap as ss
    import social_news as sn
    assert L.PROMOTE_SITE is False and ss.PROMOTE_SITE is False and sn.PROMOTE_SITE is False
    assert ss.link_lines("close", "20261104") == []


def test_strip_urls_拿掉網址與導流句():
    assert L.strip_urls(OLD_REPLY) == ""
    t = L.strip_urls("以上為公開資料整理，非投資建議\n" + OLD_REPLY)
    assert t == L.DEFAULT_LEGAL
    assert L.strip_urls("・領先 PCB → https://liguligu-puipui.com/?utm_source=threads#industry/pcb") == "・領先 PCB"
    assert "miaozike" not in L.strip_urls("備援 miaozike.github.io/tw-rotation 也有") and L.strip_urls("備援 miaozike.github.io/tw-rotation 也有").startswith("備援")
    assert not L.has_url("・外資賣超 1,073.1 億，已連 4 日賣超")          # 一般內容不動
    # 手寫檔（site_only）：只拿本站網域，其他網址留著
    assert L.strip_urls("出處 https://news.cnyes.com/x\nhttps://liguligu-puipui.com/", site_only=True) == "出處 https://news.cnyes.com/x"
    assert L.has_url("liguligu-puipui.com") and L.has_url("https://tw-rotation.pages.dev/")


def test_lint_出現網址即失敗():
    d = dict(hook_type="冷知識", emotion="吐槽", main_post="冷知識：今天八十三個族群只有八個是紅的，比我這個月的存款餘額還少見！\n#台股大跌",
             thread_posts=[], reply_post=OLD_REPLY, image_count=1, tag="台股大跌")
    e = L.lint(d)[0]
    assert any("留言出現網址" in x for x in e), e
    assert L.scrub_post(d) >= 1 and d["reply_post"] == L.DEFAULT_LEGAL and not L.lint(d)[0]


def test_盤後主貼文_留言只剩免責():
    m = json.loads((FX / "close.json").read_text(encoding="utf-8"))
    th = m["threads"]
    d = V.build("close", th["text"], th.get("reply", ""), th["images"], today="2026-11-04")
    assert d["reply_post"] == "以上為公開資料整理，非投資建議"
    for t in [d["main_post"], *d["thread_posts"], d["reply_post"]]:
        assert "http" not in t and "liguligu" not in t and "網站" not in t and "👉" not in t
    assert d["checklist_passed"], L.lint(d)


def test_social_publish_舊manifest帶網址_送出前自動移除(tmp_path, monkeypatch):
    from scripts import social_publish as sp
    flag = tmp_path / "LIVE"; flag.write_text("")
    monkeypatch.setattr(sp, "LIVE_FLAG", flag); monkeypatch.setattr(sp, "_sleep", lambda s: None)
    m = json.loads((FX / "close.json").read_text(encoding="utf-8"))
    m["kind"] = "close"
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    V.convert_manifest(p, None, None)
    mm = json.loads(p.read_text(encoding="utf-8"))
    mm["threads"]["reply_post"] = OLD_REPLY                 # 模擬 11-03 以前產的 manifest（補發）
    mm["threads"]["text"] += "\nhttps://liguligu-puipui.com/"
    p.write_text(json.dumps(mm, ensure_ascii=False), encoding="utf-8")
    calls, n = [], [0]

    def fake(method, url, **kw):
        calls.append((method, url, kw))
        if "refresh_access_token" in url:
            return {"access_token": kw["params"]["access_token"], "expires_in": 1}
        if method == "GET":
            return {"permalink": "https://l/x"} if kw["params"]["fields"] == "permalink" else {kw["params"]["fields"]: "FINISHED"}
        n[0] += 1
        return {"id": f"id{n[0]}"}
    monkeypatch.setattr(sp, "http", fake)
    monkeypatch.setattr(sp.post_quota, "live_allowed", lambda *a, **k: True)
    env = {"THREADS_USER_ID": "1", "THREADS_ACCESS_TOKEN": "TOKEN_XYZ_123", "IG_USER_ID": "", "IG_ACCESS_TOKEN": ""}
    sp.run(p, "https://x", env=env)
    sent = [c[2]["data"]["text"] for c in calls if c[0] == "POST" and "text" in c[2].get("data", {})]
    assert sent and all("liguligu" not in t and "網站" not in t and "👉" not in t for t in sent), sent
    assert sent[-1] == L.DEFAULT_LEGAL


def test_threads_post_與_ig_post_佇列檔送出前移除():
    import threads_post as tp
    posts = ["主文內容沒有網址，講外資賣超 1,073 億的事情", "以上為公開資料整理，非投資建議\n👉 更多詳細資料可以點擊以下連結：\nhttps://liguligu-puipui.com/?u=th-x"]
    out = tp.scrub_posts(posts, "2026-11-04_news-close-1.md")
    assert out == [posts[0], L.DEFAULT_LEGAL]
    out = tp.scrub_posts(["手寫：出處 https://news.cnyes.com/a", "https://liguligu-puipui.com/"], "2026-11-04_manual.md")
    assert out == ["手寫：出處 https://news.cnyes.com/a", L.DEFAULT_LEGAL]


def test_主題文章_常備文庫不帶網址():
    import social_news as S
    e = S.load_evergreen()[0]
    d = S.compose_evergreen(e, "wk1", 1, "2026-11-07")
    assert "http" not in d["caption_ig"] and "👉" not in d["caption_ig"]
    assert all("http" not in t and "👉" not in t for t in d["caption_threads"])
