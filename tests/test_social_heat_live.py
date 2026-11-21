"""2026-10-28 盤中熱力圖被略過（data-snap-live=err）事故的回歸測試。
Andy 原話：「後續盤中 盤後也不能發生這樣的事情」。"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import social_snap as ss  # noqa: E402


def test_err不再一看到就放棄_等到期限才失敗():
    assert ss.live_state_step("err", 5) == "wait"          # 以前一看到 err 就不發
    assert ss.live_state_step("pending", 60) == "wait"
    assert ss.live_state_step("err", ss.LIVE_STATE_WAIT_S) == "fail"
    assert ss.live_state_step("pending", ss.LIVE_STATE_WAIT_S + 1) == "fail"
    for st in ("live", "close", ""):                       # 沒有旗標的卡片沿用舊行為，不白等
        assert ss.live_state_step(st, 0) == "ok"
    assert ss.LIVE_STATE_WAIT_S > 150                      # 要比前端的熱力圖逾時（HL_PEND_MAX 150 秒）長


def test_熱力圖兩半都標了可退回收盤():
    heat = next(t for t in ss.TARGETS if t["name"] == "heat")
    assert heat["kind"] == "intraday" and all(p.get("close_fallback") for p in heat["parts"])
    others = [t for t in ss.TARGETS if t["kind"] == "intraday" and t["name"] != "heat"]
    assert not any(t.get("close_fallback") for t in others)      # 輪盤／分流樹／排行不退回收盤（不冒充）


def test_close_label():
    assert ss.close_label("2026-10-27") == "10/27 收盤"
    assert ss.close_label("") == "上一個交易日收盤"
    assert "setCard('heat', false)" in ss.CLOSE_FALLBACK_JS      # 退回＝關掉熱力圖即時，前端原地換回盤後


def test_退回收盤_標題列寫收盤日不寫12點():
    import inspect
    src = inspect.getsource(ss.compose)
    assert src.index('rec.get("close_label")') < src.index('12:00')


def _shots(close_label=None):
    h = {"name": "heat", "ok": True, "heat": [["軟板", 3.0], ["玻纖布", 2.0], ["被動元件", -1.0]]}
    if close_label:
        h["close_label"] = close_label
    return [
        {"name": "rotation", "ok": True, "lines": [["領先", ["軟板", "玻纖布"]], ["落後", ["晶圓代工", "ETF"]]]},
        {"name": "sankey", "ok": True, "notes": [["流入前五", ["軟板", "被動元件"]], ["流出前五", ["ETF", "晶圓代工"]]]},
        h,
    ]


def test_熱力圖即時正常_文案照舊():
    L = ss.build_text("intraday", "10/29 12:00", _shots(), "2026-10-29", "20261029").splitlines()
    assert "🔥 熱力圖：" in L and any(x.startswith("・族群") for x in L)


def test_熱力圖退回收盤_文案標日期且盤面分析不引用昨天():
    L = ss.build_text("intraday", "10/29 12:00", _shots("10/28 收盤"), "2026-10-29", "20261029").splitlines()
    assert "🔥 熱力圖（10/28 收盤）：" in L
    assert not any("族群平均" in x or "漲幅居前" in x or "族群走低" in x for x in L)
    assert ss.intraday_reads({s["name"]: s for s in _shots("10/28 收盤")}) == []


def test_前端_熱力圖即時只在看得到時計時_且送出即算問過():
    js = (ROOT / "site" / "app.js").read_text("utf-8")
    m = re.search(r"function hlState\(\) \{(.*?)\n  \}", js, re.S)
    body = m.group(1)
    assert "if (!hlShown()) { HL.pendSince = 0; return 'pending'; }" in body          # 單頁換頁不帶著舊計時進熱力圖頁
    assert body.index("hlShown()") < body.index("HL.err")
    assert re.search(r"const HL_PEND_MAX = (\d+)", js) and int(re.search(r"const HL_PEND_MAX = (\d+)", js).group(1)) >= 120000
    assert "Object.keys(d.fill || {}).forEach(k => (d.fill[k] || []).forEach(c => { if (HL.uniSet && HL.uniSet.has(c)) HL.asked.add(c); }))" in js   # mis 沒回的代號也算問過
    assert "!d.ok && hlShown() && HL.pendSince" in js
