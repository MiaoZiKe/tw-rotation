"""社群刪文工具：dry-run 不送 DELETE、沒確認字串不刪、保留清單生效、權限錯誤立即停、權杖不外洩。全部用假的 HTTP 回應，不連外。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import social_delete as sd  # noqa: E402

TOKEN = "SECRET-TOKEN-should-never-print"

TH_POSTS = [
    {"id": "111", "media_type": "IMAGE", "text": "盤前快訊 一二三", "timestamp": "2026-10-30T00:20:00+0000", "permalink": "https://t/111"},
    {"id": "17877487434633706", "media_type": "TEXT", "text": "廣達電腦- 行情分享", "timestamp": "2026-10-22T21:29:17+0000", "permalink": "https://t/q"},
    {"id": "222", "media_type": "TEXT", "text": "盤後3分鐘", "timestamp": "2026-10-31T10:00:00+0000", "permalink": "https://t/222"},
]
TH_REPLIES = [
    {"id": "333", "text": "廣達串文第二則", "timestamp": "2026-10-22T21:30:00+0000", "root_post": {"id": "17877487434633706"}},
    {"id": "444", "text": "盤前串文第二則", "timestamp": "2026-10-30T00:21:00+0000", "root_post": {"id": "111"}},
]
IG_MEDIA = [
    {"id": "18099107264560696", "caption": "廣達電腦- 行情分享", "media_type": "CAROUSEL_ALBUM", "media_product_type": "FEED",
     "timestamp": "2026-10-22T21:30:36+0000", "permalink": "https://www.instagram.com/p/Dez8-d9Ey68/"},
    {"id": "1800", "caption": "盤中快訊", "media_type": "IMAGE", "media_product_type": "FEED",
     "timestamp": "2026-10-30T04:00:00+0000", "permalink": "https://www.instagram.com/p/X/"},
]


class FakeHttp:
    def __init__(self, delete_error=None, quota_error=None, replies_error=False):
        self.calls = []
        self.delete_error = delete_error
        self.quota_error = quota_error
        self.replies_error = replies_error

    def __call__(self, method, url, params):
        assert params.get("access_token") == TOKEN
        self.calls.append((method, url))
        path = url.split(".net/v1.0", 1)[-1].split("v24.0", 1)[-1]
        if method == "DELETE":
            if self.delete_error:
                return 400, {"error": self.delete_error}
            return 200, {"success": True, "deleted_id": path.strip("/")}
        if path == "/me/threads":
            return 200, {"data": TH_POSTS}
        if path == "/me/replies":
            if self.replies_error:
                return 400, {"error": {"code": 10, "message": "no threads_read_replies"}}
            return 200, {"data": TH_REPLIES}
        if path == "/me/threads_publishing_limit":
            if self.quota_error:
                return 400, {"error": self.quota_error}
            return 200, {"data": [{"delete_quota_usage": 3, "delete_config": {"quota_total": 100, "quota_duration": 86400}}]}
        if path.endswith("/insights"):
            return 200, {"data": [{"name": "views", "values": [{"value": 42}]}]}
        if path == "/me/media":
            return 200, {"data": IG_MEDIA}
        if path == "/me/stories":
            return 200, {"data": []}
        return 404, {"error": {"code": 100, "message": f"unknown {path}"}}

    @property
    def deletes(self):
        return [u for m, u in self.calls if m == "DELETE"]


ENV = {"THREADS_ACCESS_TOKEN": TOKEN, "IG_ACCESS_TOKEN": TOKEN}


def keep_file(tmp_path):
    p = tmp_path / "keep.json"
    p.write_text(json.dumps({"threads": ["17877487434633706"], "ig": ["18099107264560696"]}), encoding="utf-8")
    return str(p)


def test_dry_run_never_sends_delete(tmp_path, capsys):
    http = FakeHttp()
    out = tmp_path / "list.json"
    rc = sd.main(["--out", str(out), "--keep-file", keep_file(tmp_path)], transport=http, env=ENV, sleep=0)
    assert rc == 0
    assert http.deletes == []
    d = json.loads(out.read_text(encoding="utf-8"))
    ids = {r["id"]: r for r in d["threads"]}
    assert set(ids) == {"111", "17877487434633706", "222", "333", "444"}
    assert ids["111"]["time_tw"] == "2026-10-30 08:20" and ids["111"]["views"] == 42
    assert "有" in d["threads_delete_permission"]
    # 手動刪除清單與 ids 草稿也產出了，且保留的不在 ids 草稿裡
    txt = (tmp_path / "list_threads_ids.txt").read_text(encoding="utf-8")
    assert "17877487434633706" not in txt and "333" not in txt and "111" in txt
    md = (tmp_path / "list_ig_manual.md").read_text(encoding="utf-8")
    assert "保留，不要刪" in md and "https://www.instagram.com/p/X/" in md
    assert TOKEN not in capsys.readouterr().out + out.read_text(encoding="utf-8")


def test_execute_without_confirm_deletes_nothing(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("111\n222\n", encoding="utf-8")
    for confirm in ([], ["--confirm", "yes"], ["--confirm", "我確定"]):
        http = FakeHttp()
        rc = sd.main(["--execute", "--ids-file", str(ids), "--keep-file", keep_file(tmp_path), *confirm],
                     transport=http, env=ENV, sleep=0)
        assert rc == 2
        assert http.calls == []          # 連一個請求都沒送


def test_execute_without_ids_file_deletes_nothing(tmp_path):
    http = FakeHttp()
    rc = sd.main(["--execute", "--confirm", sd.CONFIRM], transport=http, env=ENV, sleep=0)
    assert rc == 2 and http.calls == []


def test_ig_execute_refused(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("1800\n", encoding="utf-8")
    http = FakeHttp()
    rc = sd.main(["--platform", "ig", "--execute", "--ids-file", str(ids), "--confirm", sd.CONFIRM],
                 transport=http, env=ENV, sleep=0)
    assert rc == 2 and http.calls == []


def test_keep_list_respected_and_unlisted_skipped(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("111\n17877487434633706  # 廣達\n333\n999\n", encoding="utf-8")
    res = tmp_path / "res.json"
    http = FakeHttp()
    rc = sd.main(["--execute", "--ids-file", str(ids), "--confirm", sd.CONFIRM, "--keep-file", keep_file(tmp_path),
                  "--result", str(res)], transport=http, env=ENV, sleep=0)
    assert rc == 0
    deleted = [u.rsplit("/", 1)[-1] for u in http.deletes]
    assert deleted == ["111"]            # 廣達主文、廣達串文回覆（333）保留；999 不屬於帳號清單 → 跳過
    r = {x["id"]: x["result"] for x in json.loads(res.read_text(encoding="utf-8"))}
    assert r["111"] == "成功" and r["17877487434633706"].startswith("保留") and r["333"].startswith("保留")
    assert r["999"].startswith("跳過")


def test_keep_id_flag_and_prefix(tmp_path):
    ids = tmp_path / "ids.json"
    ids.write_text(json.dumps(["th:111", "222"]), encoding="utf-8")
    http = FakeHttp()
    sd.main(["--execute", "--ids-file", str(ids), "--confirm", sd.CONFIRM, "--keep-file", "",
             "--keep-id", "222", "--result", str(tmp_path / "r.json")], transport=http, env=ENV, sleep=0)
    assert [u.rsplit("/", 1)[-1] for u in http.deletes] == ["111"]


def test_permission_error_stops_immediately(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("111\n222\n444\n", encoding="utf-8")
    res = tmp_path / "res.json"
    http = FakeHttp(delete_error={"code": 10, "message": "Application does not have permission"})
    rc = sd.main(["--execute", "--ids-file", str(ids), "--confirm", sd.CONFIRM, "--keep-file", "",
                  "--result", str(res)], transport=http, env=ENV, sleep=0)
    assert rc == 1
    assert len(http.deletes) == 1        # 第一則就權限錯誤 → 後面兩則不再送
    assert "立即停止" in res.read_text(encoding="utf-8")


def test_no_delete_permission_preflight_stops(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("111\n", encoding="utf-8")
    http = FakeHttp(quota_error={"code": 10, "message": "需要 threads_delete"})
    rc = sd.main(["--execute", "--ids-file", str(ids), "--confirm", sd.CONFIRM, "--keep-file", ""],
                 transport=http, env=ENV, sleep=0)
    assert rc == 3 and http.deletes == []


def test_max_cap_and_quota(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("111\n222\n444\n", encoding="utf-8")
    res = tmp_path / "res.json"
    http = FakeHttp()
    sd.main(["--execute", "--ids-file", str(ids), "--confirm", sd.CONFIRM, "--keep-file", "", "--max", "2",
             "--result", str(res)], transport=http, env=ENV, sleep=0)
    assert len(http.deletes) == 2
    assert "未處理" in res.read_text(encoding="utf-8")


def test_list_json_as_ids_file_excludes_keep(tmp_path):
    http = FakeHttp()
    out = tmp_path / "list.json"
    sd.main(["--platform", "threads", "--no-views", "--out", str(out), "--keep-file", keep_file(tmp_path)],
            transport=http, env=ENV, sleep=0)
    assert set(sd.read_ids(out)) == {"111", "222", "444"}


def test_token_masked_in_errors():
    c = sd.Client("https://x", TOKEN, lambda m, u, p: (400, {"error": {"code": 1, "message": f"bad access_token={TOKEN}"}}))
    try:
        c.req("GET", "/me")
    except sd.ApiError as e:
        assert TOKEN not in str(e)
    else:
        raise AssertionError("應該丟錯")
