"""alloc：台指期當「便宜槓桿工具」的趨勢濾網版（只做多、不放空）。
訊號：加權指數收盤 vs 200 日線（±2% 遲滯），收盤後產生、隔日開盤成交。
曝險 = lev 倍帳戶權益（期貨名目），其餘現金計 1% 年息。成本：單邊 2 點滑價+手續費+期交稅（折成名目比例），換月 0.3%/年×曝險。
未模擬追繳；這裡的 lev 只到 2 倍，保證金遠低於帳戶權益。"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, ".")
from pipeline.compute import lev_lab as L

w = L.World(with_tx=False, with_mom=False)
b = L.Bench(w)
idx = L._rd("index_ohlc", ["date", "symbol", "open", "close"])
idx["date"] = pd.to_datetime(idx["date"])
fut = idx[idx.symbol == "FUT"].drop_duplicates("date").set_index("date").sort_index()
fut = fut[(fut.open > 0) & (fut.close > 0)].reindex(w.cal).ffill()
o, c = fut.open.to_numpy(), fut.close.to_numpy()
on_r = np.r_[0, o[1:] / c[:-1] - 1]
id_r = c / o - 1
cost_unit = 0.0004  # 單邊約 4 點/1 萬點 + 手續費稅，粗估 0.04% 名目


def strat(lev, n=200, h=0.02, always=False):
    st = np.ones(len(w.cal)) if always else L.shift1(L.ma_state(w, n, h, 1))
    pos = st * lev
    prev = np.r_[0, pos[:-1]]
    r = prev * on_r + pos * id_r + (1 - pos) * (w.rf / 252) - np.abs(pos - prev) * cost_unit - pos * 0.003 / 252
    r[: w.start_i] = 0
    return r, int((np.abs(np.diff(pos)) > 0).sum())


segs = {"13~16": ("2013-01-01", "2016-12-31"), "17~20": ("2017-01-01", "2020-12-31"), "21~": ("2021-01-01", None),
        "13~全": ("2013-01-01", None), "03-07~12": ("2003-07-01", "2012-12-31")}
print("0050     ", {k: round(L.cagr(L.window(w, b.r, a, bb)) * 100, 1) for k, (a, bb) in segs.items()})
for lev, always in [(1.0, True), (1.0, False), (1.5, False), (2.0, False), (2.0, True)]:
    r, ntr = strat(lev, always=always)
    cg = {k: round(L.cagr(L.window(w, r, a, bb)) * 100, 1) for k, (a, bb) in segs.items()}
    s = L.stats(w, r, "2013-01-01")
    print(f"TX{lev}x {'永遠持有' if always else '200MA濾網'}", cg, f"2013起 MDD{s['mdd']*100:.1f}% 夏普{s['sharpe']:.2f} 切換{ntr}次")
