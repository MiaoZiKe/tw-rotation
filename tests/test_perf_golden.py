"""效能重構的護欄：改快可以，改掉答案不行。

2026-09-18 量出部署那 866 秒幾乎全在 `build_payload` 的個股那一圈
（`mtf.build` 一檔 180ms＝全市場 419 秒、`compute_all`／`technical`／`scoring` 各約 100 秒）。
要動它們就一定要有辦法證明「算出來的東西沒有變」。

固定輸入在 `tests/fixtures/perf_bars.json`，現況輸出在 `perf_golden.json`，
兩個都由 `scripts/_make_perf_fixture.py` 產生。**純粹改快的重構不准重跑那支**，
重跑等於把護欄拆了；真的要改演算法才重跑，並在 commit 訊息講清楚哪裡變了。

浮點數比對用相對誤差 1e-9：重構常常會換掉加總順序，最後一個 bit 不一樣是正常的，
但只要差到第 9 位以上，那就是演算法真的變了。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parent / "fixtures"
BARS = FIX / "perf_bars.json"
GOLD = FIX / "perf_golden.json"

pytestmark = pytest.mark.skipif(not (BARS.exists() and GOLD.exists()),
                                reason="還沒產生 fixture：先跑 python scripts/_make_perf_fixture.py")


def _diff(a, b, path=""):
    """回傳第一個對不上的地方（沒有就回 None）。"""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return f"{path}: 鍵不一樣 少了{sorted(set(b) - set(a))} 多了{sorted(set(a) - set(b))}"
        for k in a:
            d = _diff(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: 長度 {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = _diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if isinstance(a, bool) or isinstance(b, bool):
        return None if a == b else f"{path}: {a!r} != {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return None
        scale = max(abs(a), abs(b), 1.0)
        return None if abs(a - b) / scale < 1e-9 else f"{path}: {a!r} != {b!r}"
    return None if a == b else f"{path}: {a!r} != {b!r}"


def test_個股頁那一圈的輸出沒有變():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts._make_perf_fixture import outputs
    bars = json.loads(BARS.read_text(encoding="utf-8"))
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    got = json.loads(json.dumps(outputs(bars), ensure_ascii=False, default=str, sort_keys=True))
    d = _diff(got, gold, "")
    assert d is None, f"重構把結果改掉了 → {d}"
