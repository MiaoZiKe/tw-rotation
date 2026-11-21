"""台指期 60 分 K 合成（pipeline/compute/lab.py tx_60）：用手算得出來的 1 分 K，驗每天 5 根、以 :45 為界、開高低收量的合成口徑。"""
import pandas as pd

from pipeline.compute.lab import pack_60, tx_60


def _day(date: str, base: float) -> list[dict]:
    """08:45～13:44 每分鐘一根；收盤價＝base＋第幾分鐘，高＝收＋1、低＝收−1、開＝收−0.5，量固定 2。"""
    rows = []
    for k in range(300):
        t = pd.Timestamp(f"{date} 08:45:00+08:00") + pd.Timedelta(minutes=k)
        c = base + k
        rows.append({"ts": t.isoformat(), "symbol": "FUT", "interval": "1m", "open": c - 0.5, "high": c + 1, "low": c - 1, "close": c, "volume": 2.0})
    return rows


def test_tx_60_每天五根且口徑正確():
    ii = pd.DataFrame(_day("2026-08-17", 20000) + _day("2026-08-18", 21000) + _day("2026-08-19", 22000) + _day("2026-08-20", 23000) + [{"ts": "2026-08-17T20:00:00+08:00", "symbol": "FUT_N", "interval": "1m", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}])
    g = tx_60(ii)
    assert g is not None and len(g) == 20                     # 四天各 5 根，夜盤 FUT_N 不納入
    first = g.iloc[0]
    assert first["open"] == 19999.5 and first["close"] == 20059 and first["high"] == 20060 and first["low"] == 19999
    assert first["volume"] == 120                              # 60 分鐘 × 每分鐘 2 口
    assert g.iloc[4]["close"] == 20299                          # 第 5 根收在當天最後一分（12:45～13:44）
    assert g.iloc[5]["open"] == 20999.5                         # 第二天從 08:45 重新開始
    pk = pack_60(g, vdiv=1.0)
    assert pk is not None and pk["v"][0] == 120 and len(pk["c"]) == 20


def test_tx_60_資料太少回None():
    assert tx_60(pd.DataFrame(_day("2026-08-17", 20000)[:50])) is None
