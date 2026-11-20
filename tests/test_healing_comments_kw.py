"""頻道④ 每篇專屬留言關鍵字（2026-11-16）：meta.json comment_keyword → 私訊完整資料／公開回覆保底／Threads 公開回覆。"""
import json
from datetime import timedelta
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import healing_comments as HC  # noqa: E402
import social_publish as SP  # noqa: E402
from test_healing_comments import NOW, TOKEN, Fake, c, go, paths, ts  # noqa: E402,F401

ROOT = Path(__file__).resolve().parents[1]
CH = ROOT / "docs" / "marketing" / "channels" / "healing"
URL = "https://liguligu-puipui.com/#article/2026-11-15-healing-marriage-video"


class KwFake(Fake):
    """多接住公開回覆 POST /{comment-id}/replies 與 EAA 的 debug_token。"""

    def __init__(self, *a, reply_error=None, **kw):
        super().__init__(*a, **kw)
        self.replies = []
        self.reply_error = reply_error

    def __call__(self, method, url, params=None, json=None, **kw):
        if url.endswith("/replies") and method == "POST":
            self.calls.append((method, url))
            if self.reply_error:
                raise RuntimeError(self.reply_error)
            self.replies.append((url.rsplit("/", 2)[-2], params["message"]))
            return {"id": "R"}
        return super().__call__(method, url, params=params, json=json, **kw)


@pytest.fixture
def kw(paths):
    """posted.json：資料夾 20261115v_marriage ↔ IG 貼文 M1；佇列 meta.json 設 comment_keyword=結婚。"""
    paths["posted"].parent.mkdir(parents=True, exist_ok=True)
    paths["posted"].write_text(json.dumps({"20261115v_marriage": {
        "ig": {"id": "M1", "at": "2026-11-08T12:00:00+08:00"},
        "threads": {"id": "T1", "at": "2026-11-08T12:00:00+08:00"}}}), encoding="utf-8")
    q = paths["posted"].parent.parent / "queue" / "20261115v_marriage"
    q.mkdir(parents=True)
    (q / "meta.json").write_text(json.dumps({"comment_keyword": "結婚"}, ensure_ascii=False), encoding="utf-8")
    return paths


def test_有追蹤_私訊完整資料(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "結婚")]}, {"U1": True})
    _, res = go(kw, fake, monkeypatch)
    assert res["counts"] == {"kw_dm": 1}
    assert [t for _, t in fake.replies] == ["已經將「10年，結婚登記少了近3成」完整資訊給你囉～"]   # 2026-11-20 私訊成功後公開補「已經將XXX完整資訊給你囉～」
    text = fake.sent[0][1]
    assert "147,861" in text and "104,376" in text and "內政部" in text and URL in text


def test_沒追蹤與查不到追蹤_公開回覆保底(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "想看 結婚 資料"), c("C2", "U2", "結婚！")]}, {"U1": False})
    _, res = go(kw, fake, monkeypatch)
    assert fake.sent == []                                     # 只私訊有追蹤者：照舊
    assert res["counts"] == {"kw_public_not_follower": 1, "kw_public_unknown_follow": 1}
    assert sorted(x[0] for x in fake.replies) == ["C1", "C2"]
    assert all(URL in t for _, t in fake.replies)


def test_沒關鍵字的留言照舊一般問候(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "好喜歡")]}, {"U1": True})
    _, res = go(kw, fake, monkeypatch)
    assert res["counts"] == {"dm": 1} and fake.sent[0][1].startswith("謝謝留下今天的晴")


def test_自傷關鍵字優先_不送資料(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "結婚什麼的 不想活了")]}, {"U1": True})
    _, res = go(kw, fake, monkeypatch)
    assert res["counts"] == {"needs_human": 1} and res["alerts"] == 1
    assert fake.replies == [] and fake.sent == []           # 不送資料、不送 1925、不公開回


def test_私訊失敗_改公開回覆(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "結婚")]}, {"U1": True}, dm_error="HTTP 400 boom")
    _, res = go(kw, fake, monkeypatch)
    assert res["counts"] == {"kw_public_dm_failed": 1} and [x[0] for x in fake.replies] == ["C1"]


def test_EAA_看不到粉絲專頁_不查追蹤直接公開回覆(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "結婚")]}, {"U1": True})
    eaa = "EAAfaketoken1234567890"
    monkeypatch.setattr(HC, "me", lambda t, p=None: (HC._PAGE.__setitem__(t, {"page_id": "", "page_token": ""}),
                                                     {"id": "17841400000000001", "username": "tanqing"})[1])
    _, res = go(kw, fake, monkeypatch, env={"HEALING_IG_ACCESS_TOKEN": eaa})
    assert res["counts"] == {"kw_public_no_dm": 1} and fake.sent == []
    assert not any("is_user_follow" in u or u.endswith("/U1") for _, u in fake.calls)    # 接不通就不浪費查追蹤
    assert [x[0] for x in fake.replies] == ["C1"]


def test_每人每篇一次_去重不洗版(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "結婚"), c("C2", "U1", "結婚 again")]}, {})
    _, res = go(kw, fake, monkeypatch)
    assert len(fake.replies) == 1 and res["counts"].get("kw_dup") == 1
    go(kw, fake, monkeypatch)
    assert len(fake.replies) == 1


def test_公開回覆上限_其餘下一輪(kw, monkeypatch):
    kw["set_cfg"](public_max_per_run=2)
    fake = KwFake({"M1": [c(f"C{i}", f"U{i}", "結婚") for i in range(5)]}, {})
    _, res = go(kw, fake, monkeypatch)
    assert len(fake.replies) == 2 and "其餘下一輪" in res["summary"]
    go(kw, fake, monkeypatch)
    go(kw, fake, monkeypatch)
    assert sorted(x[0] for x in fake.replies) == [f"C{i}" for i in range(5)]


def test_每篇每小時上限(kw, monkeypatch):
    kw["set_cfg"](public_max_per_post_hour=3)
    fake = KwFake({"M1": [c(f"C{i}", f"U{i}", "結婚") for i in range(5)]}, {})
    go(kw, fake, monkeypatch)
    go(kw, fake, monkeypatch)
    assert len(fake.replies) == 3
    raw = kw["state"].read_text(encoding="utf-8")
    for leak in ("C1", "U1", "M1", "結婚", TOKEN):          # 紀錄只有雜湊
        assert leak not in raw


def test_公開回覆失敗_下一輪重試(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "結婚")]}, {}, reply_error="HTTP 500 x")
    _, res = go(kw, fake, monkeypatch)
    assert res["counts"] == {"send_failed": 1}
    fake.reply_error = None
    go(kw, fake, monkeypatch)
    assert [x[0] for x in fake.replies] == ["C1"]


def test_空跑不回不寫_附能力檢查(kw, monkeypatch):
    fake = KwFake({"M1": [c("C1", "U1", "結婚")]}, {})
    _, res = go(kw, fake, monkeypatch, dry=True)
    assert fake.replies == [] and res["counts"] == {"dry_kw_public_unknown_follow": 1}
    assert res["probe"]["dm_available"] is True and not kw["state"].exists()
    assert "能力檢查" in HC.summary_md(res)


def test_待填內容不送半成品(kw, monkeypatch):
    kw["set_cfg"](keyword_replies={"結婚": {"dm": "待填", "public": ["待填網址"]}})
    fake = KwFake({"M1": [c("C1", "U1", "結婚")]}, {"U1": True})
    _, res = go(kw, fake, monkeypatch)
    assert fake.sent == [] and fake.replies[0][1] == "已經將這篇的完整資訊給你囉～內容在主站文章頁，貼文說明欄也有重點。"


def test_輪流挑句_固定可重現():
    v = ["a", "b", "c"]
    assert HC.rotate(v, "X1") == HC.rotate(v, "X1")
    assert {HC.rotate(v, f"id{i}") for i in range(30)} == set(v)


# ---------- Threads ----------
class ThFake:
    def __init__(self, rows):
        self.rows, self.posts, self.calls = rows, [], []

    def __call__(self, method, url, params=None, data=None, **kw):
        self.calls.append((method, url))
        if url.endswith("/me"):
            return {"id": "TU", "username": "talk_01010909"}
        if url.endswith("/replies"):
            return {"data": self.rows.get(url.rsplit("/", 2)[-2], [])}
        if url.endswith("/threads"):
            self.posts.append((data["reply_to_id"], data["text"]))
            return {"id": "CR"}
        if url.endswith("/threads_publish"):
            return {"id": "P"}
        raise AssertionError(url)


def th(kw, fake, monkeypatch, dry=False, env=None):
    monkeypatch.setattr(SP, "http", fake)
    return HC.threads_run(env={"HEALING_THREADS_ACCESS_TOKEN": "THfake1234567890"} if env is None else env,
                          dry_run=dry, now=NOW, cfg_path=kw["cfg"], posted_path=kw["posted"])


def r(rid, who, text):
    return {"id": rid, "username": who, "text": text, "timestamp": ts(1)}


def test_Threads_關鍵字公開回覆_每人每篇一次(kw, monkeypatch):
    fake = ThFake({"T1": [r("R1", "amy", "結婚"), r("R2", "amy", "結婚+1"), r("R3", "bob", "好看"),
                          r("R4", "talk_01010909", "結婚")]})
    code, res = th(kw, fake, monkeypatch)
    assert code == 0 and [x[0] for x in fake.posts] == ["R1"] and URL in fake.posts[0][1]
    th(kw, fake, monkeypatch)
    assert len(fake.posts) == 1
    raw = (kw["posted"].parent / "threads_replied.json").read_text(encoding="utf-8")
    assert "amy" not in raw and "R1" not in raw


def test_Threads_自傷不自動回_提醒(kw, monkeypatch):
    fake = ThFake({"T1": [r("R1", "amy", "結婚 好想消失"), r("R2", "bob", "撐不下去了")]})   # 沒關鍵字的也標
    _, res = th(kw, fake, monkeypatch)
    assert fake.posts == [] and res["alerts"] == 2 and res["counts"] == {"needs_human": 2}
    sp = kw["posted"].parent / "threads_replied.json"
    raw = sp.read_text(encoding="utf-8")
    assert "amy" not in raw and "R1" not in raw and "消失" not in raw
    assert {v["post"] for v in json.loads(raw)["needs_human"].values()} == {"T1"}
    _, res = th(kw, fake, monkeypatch)                     # 第二輪不重複計
    assert res["alerts"] == 0
    n = HC.needs_human_count(NOW - timedelta(days=1), state_path=kw["state"], threads_path=sp)
    assert n["threads"] == 2 and n["posts"] == ["T1"]


def test_Threads_沒設關鍵字的貼文不讀(paths, monkeypatch):
    fake = ThFake({})
    _, res = th(paths, fake, monkeypatch)
    assert fake.calls == [] and "沒有設 comment_keyword" in res["summary"]


def test_Threads_空跑與無權杖(kw, monkeypatch):
    fake = ThFake({"T1": [r("R1", "amy", "結婚")]})
    _, res = th(kw, fake, monkeypatch, dry=True)
    assert fake.posts == [] and res["counts"] == {"dry_threads_public": 1}
    _, res = th(kw, ThFake({}), monkeypatch, env={})
    assert "等待權杖" in res["summary"]


# ---------- 正式設定與佇列（交件檢查）----------
def test_正式設定_結婚私訊文字齊全且合規():
    cfg = json.loads((CH / "dm_config.json").read_text(encoding="utf-8"))
    rep = cfg["keyword_replies"]["結婚"]
    texts = [rep["dm"]] + rep["public"] + [cfg["keyword_default_public"]]
    for t in texts:
        assert HC.PLACEHOLDER not in t
        assert not re.search(r"我|我們", t)                       # 觀察者口吻
        for bad in ("往右滑", "傳給朋友", "標記", "告訴我們", "投資", "保證", "史上"):
            assert bad not in t
        assert len(t) <= 500                                      # Threads 單則上限
    for t in [rep["dm"]] + rep["public"]:
        assert URL in t and "內政部" in t                          # 數字一定附出處
    for n in ("147,861", "104,376", "3,305", "33.4", "31.4", "0.695", "29.4%"):
        assert n in rep["dm"]
    assert cfg["only_followers"] is True                          # 只私訊有追蹤者：照舊


def test_佇列文案寫了留言關鍵字_就一定有設定():
    """caption.txt 有「留言「X」」→ meta.json comment_keyword 要含 X、dm_config 要有 X 的回覆內容（否則承諾兌現不了）。"""
    cfg = json.loads((CH / "dm_config.json").read_text(encoding="utf-8"))
    bad = []
    for d in sorted((CH / "queue").iterdir()):
        cap = d / "caption.txt"
        if not cap.is_file():
            continue
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").is_file() else {}
        if meta.get("status") not in ("approved", "draft", "ready"):
            continue
        for k in HC.cta_keywords(cap.read_text(encoding="utf-8")):
            if k not in HC.post_keywords(d.name, CH / "queue") or not HC.ready((cfg.get("keyword_replies") or {}).get(k, {}).get("public")):
                bad.append(f"{d.name}：{k}")
    assert bad == [], "文案寫了留言關鍵字但沒設定：" + "、".join(bad)


def test_結婚影片已設關鍵字():
    assert HC.post_keywords("20261115v_marriage", CH / "queue") == ["結婚"]


def test_能力檢查_debug_token被拒改問permissions(monkeypatch):
    eaa = "EAAprobe1234567890"
    HC._PAGE[eaa] = {"page_id": "", "page_token": ""}

    def fake(method, url, params=None, **kw):
        if url.endswith("/debug_token"):
            raise RuntimeError("HTTP 400 (#100) You must provide an app access token")
        if url.endswith("/me/permissions"):
            return {"data": [{"permission": "instagram_manage_comments", "status": "granted"},
                             {"permission": "instagram_manage_messages", "status": "declined"}]}
        raise AssertionError(url)
    monkeypatch.setattr(SP, "http", fake)
    out = HC.probe(eaa)
    assert out["dm_available"] is False and out["scopes"] == ["instagram_manage_comments"]
    assert out["can_public_reply"] is True


def test_CaffAIne_佇列文案的留言關鍵字都有設定():
    """頻道③：caption 寫了「留言「X」」→ meta.json comment_keyword 含 X、dm_config 有 X 的私訊＋公開回覆，且連結是站內文章。"""
    ch = HC.ROOT / "docs" / "marketing" / "channels" / "caffaine"
    cfg = json.loads((ch / "dm_config.json").read_text(encoding="utf-8"))
    assert cfg["enabled"] is True and cfg["generic_dm"] is False
    bad = []
    for d in sorted((ch / "queue").iterdir()):
        cap = d / "caption.txt"
        if not cap.is_file():
            continue
        for k in HC.cta_keywords(cap.read_text(encoding="utf-8")):
            rep = (cfg.get("keyword_replies") or {}).get(k, {})
            if k not in HC.post_keywords(d.name, ch / "queue") or not HC.ready(rep.get("public")) or not HC.ready(rep.get("dm")):
                bad.append(f"{d.name}：{k}")
    assert bad == [], "文案寫了留言關鍵字但沒設定：" + "、".join(bad)


def _caff_cfg(paths):
    cfg = json.loads((HC.ROOT / "docs/marketing/channels/caffaine/dm_config.json").read_text(encoding="utf-8"))
    paths["cfg"].write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    meta = paths["posted"].parent.parent / "queue" / "20261115v_marriage" / "meta.json"
    meta.write_text(json.dumps({"comment_keyword": "動畫"}, ensure_ascii=False), encoding="utf-8")
    return cfg


def test_CaffAIne_IGAA_有追蹤_私訊後公開補一句(kw, monkeypatch):
    _caff_cfg(kw)
    fake = KwFake({"M1": [c("C1", "U1", "動畫"), c("C2", "U2", "好喜歡")]}, {"U1": True, "U2": True})
    _, res = go(kw, fake, monkeypatch)
    # 沒設專屬關鍵字的留言（好喜歡）不回；關鍵字留言：私訊 1 則＋公開補「已經將XXX完整資訊給你囉～」
    assert res["counts"].get("kw_dm") == 1 and "dm" not in res["counts"] and "skip_generic" in res["counts"]
    assert [t for _, t in fake.replies] == ["已經將「這支影片的動畫，是我叫 AI 做的」完整資訊給你囉～"]


def test_CaffAIne_EAA_私訊接不通_只公開回覆連結(kw, monkeypatch):
    _caff_cfg(kw)
    fake = KwFake({"M1": [c("C1", "U1", "動畫")]}, {"U1": True})
    eaa = "EAAfaketoken1234567890"
    monkeypatch.setattr(HC, "me", lambda t, p=None: (HC._PAGE.__setitem__(t, {"page_id": "", "page_token": ""}),
                                                     {"id": "17841400000000001", "username": "caffaine.ai"})[1])
    _, res = go(kw, fake, monkeypatch, env={"HEALING_IG_ACCESS_TOKEN": eaa})
    assert fake.sent == [] and res["counts"] == {"kw_public_no_dm": 1}
    assert len(fake.replies) == 1 and "已經私訊" not in fake.replies[0][1]


# ---------- CaffAIne Threads（2026-11-19）：同 IG 一套，公開回覆＋主站連結 ----------
CAFF = ROOT / "docs" / "marketing" / "channels" / "caffaine"


def test_CaffAIne_Threads_已開啟且關鍵字連結指向主站():
    cfg = json.loads((CAFF / "dm_config.json").read_text(encoding="utf-8"))
    assert cfg["enabled"] and cfg["threads_reply"]["enabled"] is True
    for kw_, rep in cfg["keyword_replies"].items():
        assert all("https://liguligu-puipui.com/#article/" in t for t in rep["public"]), kw_


def test_CaffAIne_Threads_公開回覆含連結_每人每篇一次(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    posted = state / "posted.json"
    posted.write_text(json.dumps({"20261118_same-look": {
        "ig": {"id": "I1", "at": "2026-11-18T21:07:06+08:00"},
        "threads": {"id": "T1", "at": "2026-11-18T21:07:06+08:00"}}}), encoding="utf-8")
    q = tmp_path / "queue" / "20261118_same-look"
    q.mkdir(parents=True)
    (q / "meta.json").write_text(json.dumps({"comment_keyword": "網頁"}, ensure_ascii=False), encoding="utf-8")
    cfg = tmp_path / "dm_config.json"
    cfg.write_text((CAFF / "dm_config.json").read_text(encoding="utf-8"), encoding="utf-8")
    fake = ThFake({"T1": [r("R1", "amy", "想要 網頁 提示詞"), r("R2", "amy", "網頁"), r("R3", "bob", "好看"),
                          r("R4", "talk_01010909", "網頁")]})
    monkeypatch.setattr(SP, "http", fake)
    env = {"CAFFAINE_THREADS_ACCESS_TOKEN": "THfake1234567890"}
    for _ in range(2):
        code, res = HC.threads_run(env=env, now=NOW, cfg_path=cfg, posted_path=posted, prefix="CAFFAINE_")
    assert code == 0 and [x[0] for x in fake.posts] == ["R1"]
    assert "https://liguligu-puipui.com/#article/2026-11-18-same-look" in fake.posts[0][1]
    raw = (state / "threads_replied.json").read_text(encoding="utf-8")
    assert "amy" not in raw and "R1" not in raw
