"""盤後保底＋法人補充貼文＋inst 輪加速（2026-10-29 事故：上市個股法人到 18:25 還沒出，盤後主貼文整段沒發）。不連網。"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_close_state as cs  # noqa: E402
import social_gate as g  # noqa: E402
import social_snap as ss  # noqa: E402

from pipeline.run_daily import inst_rebuild_flags  # noqa: E402
from scripts import social_publish as sp  # noqa: E402

H = g.load_holidays()
CLOSE = ["fut-oi", "retail-ratio", "inst-today", "streak-foreign", "streak-trust"]
D = "2026-10-29"
CD = {"fut-oi": D, "retail-ratio": D, "inst-today": "2026-10-28", "streak-foreign": "2026-10-28", "streak-trust": "2026-10-28"}


def T(s):
    return datetime.fromisoformat(s).replace(tzinfo=g.TPE)


def test_保底_19點前照舊等_19點後拿掉過期卡其他照發():
    assert g.close_fallback(D, CD, H, D, True, T("2026-10-29T18:50"))[0] is False
    ok, why, drop = g.close_fallback(D, CD, H, D, True, T("2026-10-29T19:05"))
    assert ok and set(drop) == {"inst-today", "streak-foreign", "streak-trust"} and "fut-oi" in why
    # 保底時間可設定
    assert g.close_fallback(D, CD, H, D, True, T("2026-10-29T18:40"), "18:30")[0] is True


def test_保底_全部都不是今天或休市日或臨時休市就不走():
    old = {k: "2026-10-28" for k in CLOSE}
    assert g.close_fallback(D, old, H, D, True, T("2026-10-29T19:30"))[0] is False
    assert g.close_fallback("2026-10-25", {k: "2026-10-25" for k in CLOSE}, {**H, "2026-10-25": "測試休市"}, None, False, T("2026-10-25T19:30"))[0] is False
    # 即時成交日停在前一天＝臨時休市
    assert g.close_fallback(D, CD, H, "2026-10-28", True, T("2026-10-29T19:30"))[0] is False


def test_保底文案_不引用舊法人_標明稍後補(monkeypatch):
    monkeypatch.setattr(ss, "PARTIAL", ["inst-today", "streak-foreign", "streak-trust"])
    shots = [{"name": "fut-oi", "ok": True, "read": "外資 -87,297 投信 +83,601 自營商 +3,260"},
             {"name": "retail-ratio", "ok": True, "read": [{"prod": "小台", "pct": "+12.3%"}]}]
    txt = ss.build_text("close", "10/29 19:05", shots, D, "20261029")
    assert "法人個股明細晚到，稍後補" in txt and "三大法人買賣超" not in txt and txt.splitlines()[0] == "🌙 盤後3分鐘"
    assert len(txt) <= 480 and txt.count("https://") == 1


def test_補充貼文_標題與鍵不同於主貼文(monkeypatch):
    monkeypatch.setattr(ss, "SUPPLEMENT", True)
    shots = [{"name": "inst-today", "ok": True, "read": [["外資", "−815.8億"], ["投信", "+94.9億"]]}]
    txt = ss.build_text("close", "10/29 20:10", shots, D, "20261029")
    assert txt.splitlines()[0] == "🌙 盤後3分鐘｜法人補充" and "三大法人買賣超" in txt
    assert ss.slot_key_for("close", D, "2026-10-29T20:10:00+08:00", True) == f"close-inst-{D}"
    assert ss.slot_key_for("close", D, "2026-10-29T20:10:00+08:00") == f"close-{D}"
    assert sp.slot_key({"kind": "close", "data_date": D, "supplement": True, "taken_at": "2026-10-29T20:10:00+08:00"}) == f"close-inst-{D}"
    assert sp.slot_key({"kind": "close", "data_date": D, "taken_at": "2026-10-29T20:10:00+08:00"}) == f"close-{D}"


def test_發布紀錄記下_partial_讓下一輪知道要補發(tmp_path, monkeypatch):
    on = tmp_path / "LIVE_ENABLED"
    on.write_text("", encoding="utf-8")
    monkeypatch.setattr(sp, "LIVE_FLAG", on)
    monkeypatch.setattr(sp, "_sleep", lambda s: None)
    n = {"i": 0}

    def fake(method, url, **kw):
        if "refresh_access_token" in url:
            return {"access_token": kw["params"]["access_token"], "expires_in": 5183944}
        if method == "GET":
            f = kw["params"]["fields"]
            return {"permalink": "https://link/x"} if f == "permalink" else {f: "FINISHED"}
        n["i"] += 1
        return {"id": f"id{n['i']}"}
    monkeypatch.setattr(sp, "http", fake)
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"kind": "close", "taken_at": "2026-10-29T19:05:00+08:00", "data_date": D, "partial": ["inst-today"],
                             "threads": {"text": "盤後", "images": ["a.png"]}, "story": ["s.png"]}), encoding="utf-8")
    env = {"THREADS_USER_ID": "11", "THREADS_ACCESS_TOKEN": "T", "IG_USER_ID": "22", "IG_ACCESS_TOKEN": "I"}
    assert sp.run(m, "https://x.test", env=env) == 0
    posted = json.loads((tmp_path / "posted.json").read_text("utf-8"))
    assert posted[f"close-{D}"]["partial"] == ["inst-today"]
    assert cs.state(posted, D) == "supplement"
    posted[f"close-inst-{D}"] = {"threads": {"id": "x"}}
    assert cs.state(posted, D) == "skip"
    assert cs.state({f"close-{D}": {"threads": {"id": "y"}}}, D) == "skip"
    assert cs.state({}, D) == ""


def test_inst輪_沒新增今天法人就不重算不部署():
    assert inst_rebuild_flags(878, 878, 0) == {"rebuild": False, "post": False}
    assert inst_rebuild_flags(878, 878, 12) == {"rebuild": False, "post": True}      # 只有期貨新列：派盤後貼文，不重算
    assert inst_rebuild_flags(878, 2100, 0) == {"rebuild": True, "post": True}
    assert inst_rebuild_flags(-1, 878, 0)["rebuild"] is True                          # 讀不到列數：保守照舊重算


def test_daily_workflow_重算與部署看_rebuild():
    import yaml
    wf = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/daily.yml").read_text("utf-8"))
    steps = {s.get("name"): s for s in wf["jobs"]["collect"]["steps"]}
    assert "rebuild" in steps["整站重算（inst 輪延後的那一步）"]["if"]
    assert "rebuild" in steps["上傳網站"]["if"]
    assert "rebuild" in wf["jobs"]["deploy"]["if"]
    assert wf["jobs"]["collect"]["outputs"]["rebuild"] == "${{ steps.fetch.outputs.rebuild }}"
