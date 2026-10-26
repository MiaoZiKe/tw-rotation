"""第五輪紅線測試：隔日開盤成交、只持個股（不持 ETF）、大盤濾網關閉時空手、0050 基準含成本。"""
import numpy as np
import pandas as pd

from pipeline.compute import swing_lab5 as S


def _P(T=420, seed=0, mkt=True):
    idx = pd.bdate_range("2019-01-01", periods=T)
    cols = ["0050", "1101", "1102", "1103"]
    rng = np.random.default_rng(seed)
    C = 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, (T, 4)), axis=0)
    O = C * (1 + rng.normal(0, 0.002, (T, 4)))
    mom = np.zeros((T, 4)); mom[:, 2] = 1.0; mom[:, 1] = 0.5            # 1102 動能最高
    f = {"mom252": mom, "mom189": mom, "mom126": mom, "nh": np.ones((T, 4)), "ma200": C * 0.9}
    elig = np.ones((T, 4), bool); elig[:, 0] = False                      # 0050 不可交易
    P = dict(idx=idx, cols=cols, ci={c: i for i, c in enumerate(cols)}, O=O, H=O, L=O, C=C, V=np.ones((T, 4)), rawC=C,
             Cf=C, f=f, elig={200: elig, 100: elig}, mf={"ma200": np.full(T, mkt)}, mkt_on=np.full(T, mkt),
             br={200: np.ones(T), 100: np.ones(T)}, mkt_12m=np.ones(T), is_etf=np.array([True, False, False, False]),
             c50=pd.Series(C[:, 0], index=idx), o50=pd.Series(O[:, 0], index=idx))
    return P


def test_隔日開盤買進且不持有ETF():
    P = _P()
    spec = dict(fam="mom", L=252, N=1, rebal="M", mkt=True)
    r = S.run_periodic(P, spec, 200, "2020-01-02", "2020-08-31", trades=True)
    t = r["trades"]
    assert len(t) >= 1 and set(t["code"]) == {"1102"}              # 只買動能最高的個股，從不買 0050
    first = t.iloc[0]
    lo_i = P["idx"].searchsorted(pd.Timestamp("2020-01-02"))
    assert first["entry"] == P["idx"][lo_i]                         # 窗首訊號用前一日收盤，當天開盤成交
    assert np.isclose(first["entry_px"], P["O"][lo_i, 2] * (1 + S.SLIP))


def test_大盤濾網關閉就空手():
    P = _P(mkt=False)
    spec = dict(fam="mom", L=252, N=3, rebal="M", mkt=True)
    r = S.run_periodic(P, spec, 200, "2020-01-02", "2020-08-31", trades=True)
    assert r["trades"].empty and abs(r["eq"].iloc[-1] - 1.0) < 1e-9 and r["expo"] == 0.0


def test_0050基準有扣成本():
    P = _P()
    b = S.bench(P, "2020-01-02", "2020-08-31")
    i0 = P["idx"].searchsorted(pd.Timestamp("2020-01-02")); i1 = P["idx"].searchsorted(pd.Timestamp("2020-08-31"), side="right") - 1
    raw = P["C"][i1, 0] / P["O"][i0, 0]
    assert b.iloc[-1] < raw - 0.004


def test_週K狀態不使用當週未完成資料():
    P = _P()
    P["Cf"] = P["C"]
    up = S.weekly_state(P, 3, 6)
    P2 = dict(P); C2 = P["C"].copy(); C2[-1] *= 0.1                    # 竄改最後一天
    P2["Cf"] = C2
    up2 = S.weekly_state(P2, 3, 6)
    assert pd.DataFrame(up[:-6]).equals(pd.DataFrame(up2[:-6]))   # 更早的日子完全不受影響
