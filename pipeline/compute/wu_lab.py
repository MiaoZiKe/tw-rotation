"""「吳小弟策略」（老吳 @stockwu888 台指期均線策略）回測。規格：scratchpad/wu_spec.md（由公開貼文歸納、推論，非原始設定）。

骨架
  * 只用 K 棒＋均線；全部在「收棒」判斷，訊號收盤後產生、**下一根開盤成交**（不用當根收盤進場，避免前視）。
  * 模組 A（上揚均線＋長紅棒低點拉回做多）為核心；B（糾結後長紅突破）、C（空排表態失敗）、E（平台試單）可疊加；
    D（5 分 K 碰 20T 反壓）需要 5 分 K，資料湖沒有（見 README 資料節），**未實作**。
  * 出場：初始停損＝長紅棒低點與上揚均線取較近者，**收盤確認**（收盤跌破 -> 下一根開盤出）；移動停利＝收盤跌破 60/5
    （日K 版就是日K 的 5MA）。移動停利須先「收盤站上過 5MA」才啟動（我的推論：否則在 MA10/MA20 附近進場的單，
    下一根收盤就會因為還在 5MA 之下而被立刻停利出場）。
  * 停損後可反手（B 版）：停損當根收盤若符合空方條件，下一根開盤直接反向進場；停損後 cool 根內禁止同向再進。
  * 資料（兩條路線，因為資料湖沒有台指期 60 分 K）：
      ① 日K 版：index_ohlc 的 symbol=FUT（真實台指期日盤日K，2000 起）。**週期與原策略不同**（原策略主週期 60 分 K）。
      ② 60 分 K 代理版：index_intraday 的加權指數 60 分 K（2023-09 起）。沒有夜盤、有基差、樣本只有約 3 年。
      ③ 真期貨 60 分 K（期交所逐筆合成，日盤＋夜盤）：index_intraday 的 FUT／FUT_N 1 分 K 只有 2026-08 起，約 58 個日曆日（含夜盤歸屬日），僅做參考。
  * 參數只能用 2015～2020 優化；2021 起是保留期，只跑一次（final_holdout 寫鎖檔，再呼叫直接拒絕）。
"""
from __future__ import annotations

import glob
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import futures_lab as F  # noqa: E402

OUT = ROOT / "docs" / "futures_lab" / "wu"
MULT = 200.0
FEE_PTS = F.FEE_NTD / MULT          # 單邊手續費折點數
TAX = F.TAX
SLIP = F.SLIP_PTS
CASH_D = F.CASH_Y / F.PPY
SEARCH = ("2015-01-01", "2021-01-01")
HOLDOUT = "2021-01-01"
WARM = "2013-01-01"

DEFAULT_P = dict(m=1.5, N=15, k=3, delta=0.3, X=8, theta=0.5, cool=5, Np=20, theta_r=4.0, trail=5)
GRID_P = dict(m=[1.2, 1.5, 2.0, 2.5], N=[10, 15, 25], k=[1, 3, 5], delta=[0.2, 0.3, 0.5], X=[5, 8, 12], cool=[3, 5, 8], trail=[5, 10])


# ------------------------------------------------------------------ 資料
def _rd(table):
    fs = glob.glob(str(ROOT / "data" / table / "**" / "*.parquet"), recursive=True)
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)


class Bars:
    """一組 K 棒與其均線、ATR、市況標籤。date：每根所屬交易日；regime：週K 40 週均線狀態（延後一週，無前視）。"""

    def __init__(self, ts, o, h, l, c, regime=None, name=""):
        self.ts = pd.DatetimeIndex(ts)
        self.o, self.h, self.l, self.c = (np.asarray(x, float) for x in (o, h, l, c))
        self.date = self.ts.normalize().tz_localize(None) if self.ts.tz is not None else self.ts.normalize()
        self.n = len(self.c)
        self.ma = {k: pd.Series(self.c).rolling(k).mean().to_numpy() for k in (5, 10, 20, 60, 240)}
        self.atr = F.atr_wilder(self.h, self.l, self.c)
        self.regime = np.zeros(self.n, int) if regime is None else regime
        self.name = name
        self.fc = {}

    def feats(self, p):
        key = (p["m"], p["N"], p["k"], p["X"], p["theta"], p["Np"], p["theta_r"])
        if key in self.fc:
            return self.fc[key]
        c, o, h, l, ma, atr = self.c, self.o, self.h, self.l, self.ma, self.atr
        body = np.abs(c - o)
        avgb = pd.Series(body).rolling(p["N"]).mean().shift(1).to_numpy()
        lred = (c > o) & (body >= p["m"] * avgb)
        lblk = (c < o) & (body >= p["m"] * avgb)
        last_red = np.full(self.n, -1); last_blk = np.full(self.n, -1)
        a = b = -1
        for i in range(self.n):                      # 嚴格「這一根以前」最近的長紅／長黑
            last_red[i] = a; last_blk[i] = b
            if lred[i]:
                a = i
            if lblk[i]:
                b = i
        k = p["k"]
        sh = lambda x: np.r_[np.full(k, np.nan), x[:-k]]
        rise = {n: ma[n] > sh(ma[n]) for n in (10, 20, 60)}
        fall = {n: ma[n] < sh(ma[n]) for n in (10, 20, 60)}
        bull = (ma[5] > ma[10]) & (ma[10] > ma[20]) & (ma[20] > ma[60]) & rise[20] & rise[60]
        bear = (ma[5] < ma[10]) & (ma[10] < ma[20]) & (ma[20] < ma[60]) & fall[20] & fall[60]
        top3 = np.fmax(np.fmax(ma[5], ma[10]), ma[20]); bot3 = np.fmin(np.fmin(ma[5], ma[10]), ma[20])
        tangle = (top3 - bot3) / np.where(atr > 0, atr, np.nan) < p["theta"]
        hh = pd.Series(h).rolling(p["Np"]).max().to_numpy(); ll = pd.Series(l).rolling(p["Np"]).min().to_numpy()
        flat = (hh - ll) / np.where(atr > 0, atr, np.nan) < p["theta_r"]
        res = dict(lred=lred, lblk=lblk, last_red=last_red, last_blk=last_blk, rise=rise, fall=fall, bull=bull, bear=bear,
                   top3=top3, bot3=bot3, tangle=tangle, hh=hh, ll=ll, flat=flat)
        self.fc[key] = res
        return res


def make_daily() -> Bars:
    lab = F.Lab()
    tx = lab.tx
    reg = lab.X["reg"][40]
    return Bars(tx.index, tx.open, tx.high, tx.low, tx.close, regime=reg, name="日K版（台指期日盤日K）")


def make_60m_spot(lab_regime=None) -> Bars:
    d = _rd("index_intraday")
    x = d[(d.symbol == "TSE") & (d.interval == "60m")].drop_duplicates("ts").sort_values("ts")
    ts = pd.to_datetime(x.ts)
    b = Bars(ts, x.open, x.high, x.low, x.close, name="60分K代理版（加權指數現貨）")
    if lab_regime is not None:
        s = pd.Series(lab_regime[0], index=lab_regime[1])
        b.regime = s.reindex(b.date, method="ffill").fillna(0).to_numpy().astype(int)
    return b


def make_60m_fut(lab_regime=None):
    """期交所逐筆合成的台指期 1 分 K（日盤 FUT＋夜盤 FUT_N）-> 60 分 K。樣本只有約 46 個交易日。"""
    d = _rd("index_intraday")
    x = d[(d.symbol.isin(["FUT", "FUT_N"])) & (d.interval == "1m")].drop_duplicates(["ts", "symbol"]).copy()
    x["t"] = pd.to_datetime(x.ts)
    x = x.sort_values("t")
    g = x.groupby(x["t"].dt.floor("60min"))
    bars = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()}).dropna()
    b = Bars(bars.index, bars.open, bars.high, bars.low, bars.close, name="真期貨60分K（日夜盤，約46個交易日）")
    if lab_regime is not None:
        s = pd.Series(lab_regime[0], index=lab_regime[1])
        b.regime = s.reindex(b.date, method="ffill").fillna(0).to_numpy().astype(int)
    return b


# ------------------------------------------------------------------ 設定
def cfg_of(**kw):
    c = dict(entry="A", mods=("A",), exit="formal", align=False, reverse=False, addreduce=False, shorts=False,
             maxstop_atr=3.0, maxstop_pts=None, tp=87.0, hold=30, risk=None, risk_cap=3.0)
    c.update(kw)
    return c


# ------------------------------------------------------------------ 進場訊號（全部用 i 與 i 以前的資料，收盤後判斷）
def _near(a, b, tol):
    return abs(a - b) <= tol


def signal(b, f, i, d, cfg, p):
    """回傳 (module, stop, addtrig, units) 或 None。d=+1 做多、-1 放空（對稱鏡像）。"""
    c, o, h, l, ma, atr = b.c, b.o, b.h, b.l, b.ma, b.atr
    a = atr[i]
    if not a > 0:
        return None
    tol = p["delta"] * a
    cl = c[i]
    lim = cfg["maxstop_pts"] if cfg["maxstop_pts"] else cfg["maxstop_atr"] * a
    for mod in cfg["mods"]:
        if mod == "A":
            j = f["last_red"][i] if d == 1 else f["last_blk"][i]
            kpart = mpart = False
            stop = np.nan; addtrig = np.nan
            if j >= 0 and i - j <= p["X"]:
                if d == 1:
                    L = l[j]; kpart = _near(l[i], L, tol) and cl > L
                    stop_k = L; addtrig = h[j]
                else:
                    Hh = h[j]; kpart = _near(h[i], Hh, tol) and cl < Hh
                    stop_k = Hh; addtrig = l[j]
            ref = np.nan
            for n in (10, 20):
                trend_ok = f["rise"][n][i] if d == 1 else f["fall"][n][i]
                px = l[i] if d == 1 else h[i]
                if trend_ok and _near(px, ma[n][i], tol) and ((cl > ma[n][i]) if d == 1 else (cl < ma[n][i])):
                    mpart = True; ref = ma[n][i]; break
            if cfg["entry"] == "K":
                ok = kpart; st = stop_k if kpart else np.nan
            elif cfg["entry"] == "M":
                ok = mpart; st = ref if mpart else np.nan
            else:
                ok = kpart and mpart
                st = (max(stop_k, ref) if d == 1 else min(stop_k, ref)) if ok else np.nan
            if ok:
                if cfg["align"] and not (f["bull"][i] if d == 1 else f["bear"][i]):
                    continue
                risk = (cl - st) if d == 1 else (st - cl)
                if risk <= 0 or risk > lim:
                    continue
                return ("A", st, addtrig, 1.0)
        elif mod == "B":
            tg = f["tangle"]
            if i >= 2 and tg[i - 1] and tg[i - 2]:
                if d == 1 and f["lred"][i] and cl > f["top3"][i]:
                    st = l[i]; risk = cl - st
                elif d == -1 and f["lblk"][i] and cl < f["bot3"][i]:
                    st = h[i]; risk = st - cl
                else:
                    continue
                if 0 < risk <= lim:
                    return ("B", st, h[i] if d == 1 else l[i], 1.0)
        elif mod == "C":
            if i >= 6:
                w = slice(i - 3, i + 1)
                if d == 1 and f["bear"][i - 4] and l[w].min() <= f["ll"][i] + 1e-9 and cl > ma[5][i] and c[i - 1] <= ma[5][i - 1]:
                    st = l[w].min(); risk = cl - st
                elif d == -1 and f["bull"][i - 4] and h[w].max() >= f["hh"][i] - 1e-9 and cl < ma[5][i] and c[i - 1] >= ma[5][i - 1]:
                    st = h[w].max(); risk = st - cl
                else:
                    continue
                if 0 < risk <= lim:
                    return ("C", st, np.nan, 1.0)
        elif mod == "E" and d == 1:
            if f["flat"][i] and not np.isnan(f["ll"][i]) and l[i] <= f["ll"][i] + tol and cl > f["ll"][i]:
                w = slice(i - p["Np"] + 1, i + 1)
                tested = int((l[w] <= f["ll"][i] + 0.25 * a).sum())
                if tested >= 2:
                    st = f["ll"][i]; risk = cl - st
                    if 0 < risk <= lim:
                        return ("E", st, f["hh"][i], 0.5)             # 試單 0.5 單位；突破平台高點再補到 1
    return None


# ------------------------------------------------------------------ 回測引擎
def backtest(b: Bars, cfg: dict, p: dict | None = None):
    p = dict(DEFAULT_P, **(p or {}))
    f = b.feats(p)
    o, h, l, c, ma = b.o, b.h, b.l, b.c, b.ma
    n = b.n
    ret = np.zeros(n)
    trades = []
    pos = 0; units = 0.0; e = 1.0; stop = np.nan; armed = False; reduced = False; added = False; addtrig = np.nan
    avg = 0.0; pnl_pts = 0.0; ent_i = 0; mod = ""; hold = 0; mae = 0.0; mfe = 0.0; r_tr = 0.0; pk_units = 0.0
    pend = None
    cool_until = {1: -1, -1: -1}
    base_e = 0.5 if cfg["addreduce"] else 1.0
    trail_n = p["trail"]

    def close_trade(i, px, reason):
        nonlocal pos, units, pnl_pts, r_tr
        trades.append(dict(entry_i=ent_i, exit_i=i, dir=pos, module=mod, entry_px=avg0[0], exit_px=px, reason=reason,
                           pnl_pts=pnl_pts, mae=mae, mfe=mfe, ret=r_tr, hold=i - ent_i, units=pk_units, regime=int(b.regime[ent_i]),
                           stop=stop, atr=b.atr[ent_i], exit_close_i=i))
        pos = 0; units = 0.0
    avg0 = [0.0]

    for i in range(1, n):
        prev = c[i - 1]
        r = 0.0
        if pos != 0:
            r += pos * units * e * (o[i] - prev) / prev
        ev, pend = pend, None
        exited = False
        r_off = 0.0
        if ev:
            if pos != 0 and ev.get("exit"):
                px = o[i] - pos * SLIP
                cost = FEE_PTS + TAX * px
                r -= units * e * (SLIP + cost) / prev
                pnl_pts += pos * units * (px - avg) - units * cost
                r_tr += r - r_off
                if ev["exit"] == "stop":
                    cool_until[ev["was"]] = i + p["cool"]
                close_trade(i, px, ev["exit"])
                exited = True
            elif pos != 0 and ev.get("reduce"):
                u_out = units / 2.0
                px = o[i] - pos * SLIP
                cost = FEE_PTS + TAX * px
                r -= u_out * e * (SLIP + cost) / prev
                pnl_pts += pos * u_out * (px - avg) - u_out * cost
                units -= u_out
            elif pos != 0 and ev.get("add"):
                px = o[i] + pos * SLIP
                cost = FEE_PTS + TAX * px
                r -= 1.0 * e * (SLIP + cost) / prev
                pnl_pts -= 1.0 * cost
                avg = (avg * units + px) / (units + 1.0)
                units += 1.0; pk_units = max(pk_units, units)
            if pos == 0 and ev.get("enter"):
                d, mname, st, at, u0, risk_pts = ev["enter"]
                px = o[i] + d * SLIP
                ok = (px > st) if d == 1 else (px < st)
                if ok:
                    pos = d; units = u0; mod = mname; stop = st; addtrig = at
                    avg = px; avg0[0] = px; ent_i = i; armed = False; reduced = False; added = False; hold = 0
                    mae = 0.0; mfe = 0.0; r_tr = 0.0; pnl_pts = 0.0; pk_units = u0; r_off = r
                    e = base_e
                    if cfg["risk"] and risk_pts > 0:
                        e = min(cfg["risk_cap"], cfg["risk"] * px / risk_pts)
                    cost = FEE_PTS + TAX * px
                    r -= units * e * (SLIP + cost) / prev
                    pnl_pts -= units * cost
        # 盤中
        if pos != 0:
            hold += 1
            adv = (avg - l[i]) if pos == 1 else (h[i] - avg)
            fav = (h[i] - avg) if pos == 1 else (avg - l[i])
            mae = max(mae, adv); mfe = max(mfe, fav)
            if cfg["exit"] == "fixed87":
                tp_px = avg + pos * cfg["tp"]; sl_px = avg - pos * cfg["tp"]
                hit_sl = (l[i] <= sl_px) if pos == 1 else (h[i] >= sl_px)
                hit_tp = (h[i] >= tp_px) if pos == 1 else (l[i] <= tp_px)
                if hit_sl or hit_tp:
                    if hit_sl:                                        # 同根兩邊都碰：保守算停損先
                        px = (min(o[i], sl_px) if pos == 1 else max(o[i], sl_px)) - pos * SLIP
                        why = "固定停損"
                    else:
                        px = (max(o[i], tp_px) if pos == 1 else min(o[i], tp_px)) - pos * SLIP
                        why = "固定停利"
                    r += pos * units * e * (px - o[i]) / prev
                    cost = FEE_PTS + TAX * px
                    r -= units * e * cost / prev
                    pnl_pts += pos * units * (px - avg) - units * cost
                    r_tr += r - r_off
                    close_trade(i, px, why)
                    ret[i] = r
                    continue
        if pos != 0:
            r += pos * units * e * (c[i] - o[i]) / prev
            r_tr += r - r_off
        ret[i] = r
        # ---- 收盤後決策（下一根開盤執行）
        if pos != 0:
            if cfg["exit"] == "fixed87":
                if hold >= cfg["hold"]:
                    pend = dict(exit="逾時")
            else:
                broke = (c[i] < stop) if pos == 1 else (c[i] > stop)
                mt = ma[trail_n][i]
                if broke:
                    pend = dict(exit="stop", was=pos)
                    if cfg["reverse"] and cfg["shorts"]:
                        opp = signal_any(b, f, i, -pos, cfg, p, cool_until)
                        if opp is not None:
                            pend["enter"] = opp
                else:
                    if (c[i] > mt) if pos == 1 else (c[i] < mt):
                        armed = True
                    out = (c[i] < mt) if pos == 1 else (c[i] > mt)
                    if armed and out:
                        if cfg["addreduce"] and not reduced:
                            reduced = True
                            pend = dict(reduce=True)
                        elif not cfg["addreduce"]:
                            pend = dict(exit="trail")
                    if cfg["addreduce"] and reduced and not pend:
                        m10 = ma[10][i]
                        if (c[i] < m10) if pos == 1 else (c[i] > m10):
                            pend = dict(exit="trail")
                    if not pend and not added and not reduced and not np.isnan(addtrig) and pk_units < 2.0 and (
                            cfg["addreduce"] or mod == "E"):
                        if (c[i] > addtrig) if pos == 1 else (c[i] < addtrig):
                            added = True
                            pend = dict(add=True)
        else:
            sig = signal_any(b, f, i, None, cfg, p, cool_until)
            if sig is not None:
                pend = dict(enter=sig)
    if pos != 0:
        close_trade(n - 1, c[n - 1], "資料尾")
    tdf = pd.DataFrame(trades)
    return pd.Series(ret, index=b.ts), tdf


def signal_any(b, f, i, d, cfg, p, cool_until):
    dirs = [d] if d is not None else ([1, -1] if cfg["shorts"] else [1])
    for dd in dirs:
        if i <= cool_until.get(dd, -1):
            continue
        s = signal(b, f, i, dd, cfg, p)
        if s is not None:
            mname, st, at, u0 = s
            risk = abs(b.c[i] - st)
            return (dd, mname, st, at, u0, risk)
    return None


# ------------------------------------------------------------------ 績效
def daily_returns(b: Bars, ret: pd.Series) -> pd.Series:
    """bar 報酬 -> 交易日報酬（同日複利），再加閒置資金年息 1%（與前幾輪同口徑）。"""
    r = (1 + ret).groupby(b.date).prod() - 1
    return r + CASH_D


def perf(b, ret, trades, a, z=None, lab=None):
    """a～z 區間：年化、最大回撤、夏普、交易統計。交易以進場日落在區間內為準。"""
    dr = daily_returns(b, ret)
    x = dr[(dr.index >= pd.Timestamp(a)) & ((dr.index < pd.Timestamp(z)) if z else True)]
    s = F.stats(x)
    t = trades
    if len(t):
        ed = b.date[t.entry_i.to_numpy().astype(int)]
        m = (ed >= pd.Timestamp(a)) & ((ed < pd.Timestamp(z)) if z else True)
        t = t[m]
    n = len(t)
    if n:
        w = t[t.pnl_pts > 0]; lo = t[t.pnl_pts <= 0]
        payoff = (w.pnl_pts.mean() / abs(lo.pnl_pts.mean())) if len(w) and len(lo) and lo.pnl_pts.mean() != 0 else np.nan
        s.update(n=n, win=len(w) / n, payoff=payoff, maxloss_pts=t.pnl_pts.min(), maxloss_ret=t.ret.min(),
                 hold=t.hold.mean(), pf=(w.pnl_pts.sum() / abs(lo.pnl_pts.sum())) if len(lo) and lo.pnl_pts.sum() != 0 else np.nan)
    else:
        s.update(n=0, win=np.nan, payoff=np.nan, maxloss_pts=np.nan, maxloss_ret=np.nan, hold=np.nan, pf=np.nan)
    return s


def bench(lab, a, z=None):
    return F.stats(lab.bh_0050(a, z))


# ------------------------------------------------------------------ 六步流程
def steps_for(shorts: bool, hold: int, maxstop_pts=None):
    base = dict(shorts=shorts, hold=hold, maxstop_pts=maxstop_pts)
    return [
        ("1 只有K棒（長紅低點拉回）＋固定87點", "還沒有任何均線，先看紅棒低點這個進場點本身有沒有優勢", cfg_of(entry="K", exit="fixed87", **base)),
        ("2 只有均線（上揚MA10/20附近）＋固定87點", "對照：只有均線、不看紅棒低點", cfg_of(entry="M", exit="fixed87", **base)),
        ("3 兩者疊加＝模組A＋固定87點", "兩個條件同時成立，看勝率／期望值有沒有比單獨好", cfg_of(entry="A", exit="fixed87", **base)),
        ("4 正式出場：技術停損＋60/5移動停利", "固定87點是教學用基準；老吳實際是『收盤跌破紅棒低點』停損、『收盤跌破5MA』停利", cfg_of(entry="A", exit="formal", **base)),
        ("5a ＋趨勢濾網（多排／空排）", "老吳：順勢、不接刀；只在均線多排（空排）時進場", cfg_of(entry="A", exit="formal", align=True, **base)),
        ("5b ＋停損反手", "老吳：停損後順勢反手、不在同方向一直摸（僅 B 版有空單）", cfg_of(entry="A", exit="formal", align=True, reverse=True, **base)),
        ("5c ＋加減碼", "突破長紅高點加碼、跌破5MA先減半、跌破10MA全出（基礎部位 0.5 倍，最多 1 倍）", cfg_of(entry="A", exit="formal", align=True, reverse=True, addreduce=True, **base)),
        ("5d ＋模組B（糾結突破）", "老吳：均線糾結後長紅帶動多排", cfg_of(entry="A", mods=("A", "B"), exit="formal", align=True, reverse=True, addreduce=True, **base)),
        ("5e ＋模組C（空排表態失敗）", "限動：空排表態失敗站回 60/5", cfg_of(entry="A", mods=("A", "B", "C"), exit="formal", align=True, reverse=True, addreduce=True, **base)),
        ("5f ＋模組E（平台試單）", "老吳：平台低點試單、突破補正式部位", cfg_of(entry="A", mods=("A", "B", "C", "E"), exit="formal", align=True, reverse=True, addreduce=True, **base)),
    ]


def run_steps(b, lab, shorts, a, z, maxstop_pts=None, hold=30, p=None, registry=None, tag=""):
    bb = bench(lab, a, z)
    rows = []
    prev = None
    kept = None
    for nm, why, cfg in steps_for(shorts, hold, maxstop_pts):
        ret, t = backtest(b, cfg, p)
        s = perf(b, ret, t, a, z)
        if registry is not None:
            registry.append(dict(版本=tag, 步驟=nm, 年化=s["cagr"], 回撤=s["mdd"], 交易數=s["n"]))
        calmar = s["cagr"] / max(abs(s["mdd"]), 1e-6) if s["n"] else -9
        keep = None
        if nm.startswith(("5", "4")) and nm[:2] != "4 ":
            pass
        rows.append(dict(步驟=nm, 加了什麼為什麼=why, 年化=s["cagr"], 回撤=s["mdd"], 夏普=s["sharpe"], 勝率=s["win"], 盈虧比=s["payoff"],
                         最大單筆虧損點=s["maxloss_pts"], 交易數=s["n"], 平均持有根數=s["hold"], 同窗0050=bb["cagr"],
                         差距=s["cagr"] - bb["cagr"], _cfg=cfg, _calmar=calmar))
    return pd.DataFrame(rows), bb


def pick_final(df, shorts):
    """Andy 指定的策略不套用我們自己加的限制：主結果＝規格書原則全開（A 長紅低點拉回＋趨勢濾網＋停損反手＋加減碼＋模組 B/C/E 試單；
    B 版多空都做）。六步表仍逐步列出每個原則的邊際效果，但不再用 Calmar 規則挑選保留哪些。"""
    last = df.iloc[-1]
    return last._cfg, ["規格書原則全開（" + last.步驟 + "）"]


def regime_table(b, trades, a, z):
    names = {1: "多頭", -1: "空頭", 0: "盤整"}
    ed = b.date[trades.entry_i.to_numpy().astype(int)] if len(trades) else []
    rows = []
    for code, nm in names.items():
        t = trades[(trades.regime == code) & (ed >= pd.Timestamp(a)) & ((ed < pd.Timestamp(z)) if z else True)] if len(trades) else trades
        if len(t):
            w = t[t.pnl_pts > 0]
            rows.append(dict(行情=nm, 交易數=len(t), 勝率=len(w) / len(t), 平均每筆點數=t.pnl_pts.mean(), 合計點數=t.pnl_pts.sum(),
                             最大單筆虧損點=t.pnl_pts.min()))
        else:
            rows.append(dict(行情=nm, 交易數=0, 勝率=np.nan, 平均每筆點數=np.nan, 合計點數=0.0, 最大單筆虧損點=np.nan))
    return pd.DataFrame(rows)


def yearly(b, ret, lab, a, z=None):
    dr = daily_returns(b, ret)
    out = []
    for y in range(pd.Timestamp(a).year, (pd.Timestamp(z).year if z else dr.index.max().year + 1)):
        x = dr[(dr.index >= f"{y}-01-01") & (dr.index < f"{y + 1}-01-01")]
        if len(x) < 20:
            continue
        b0 = lab.bh_0050(f"{y}-01-01", f"{y + 1}-01-01")
        out.append(dict(年=y, 策略=(1 + x).prod() - 1, **{"0050": (1 + b0).prod() - 1}))
    return pd.DataFrame(out)


# ------------------------------------------------------------------ 優化（只用 2015～2020）
def optimize(b, lab, cfg, a=SEARCH[0], z=SEARCH[1], min_trades=15):
    bb = bench(lab, a, z)
    keys = list(GRID_P)
    best, bs, n = None, -9, 0
    for vals in itertools.product(*[GRID_P[k] for k in keys]):
        p = dict(DEFAULT_P, **dict(zip(keys, vals)))
        ret, t = backtest(b, cfg, p)
        s = perf(b, ret, t, a, z)
        n += 1
        if s["n"] < min_trades:
            continue
        sc = s["cagr"]
        if sc > bs:
            best, bs = p, sc
    return best, bs, n


def neighbors_of(p):
    out = []
    for k, vals in GRID_P.items():
        i = vals.index(p[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                q = dict(p); q[k] = vals[j]; out.append(q)
    return out


def neigh_stats(b, lab, cfg, p, a=SEARCH[0], z=SEARCH[1]):
    bb = bench(lab, a, z)
    cs = []
    for q in neighbors_of(p):
        ret, t = backtest(b, cfg, q)
        cs.append(perf(b, ret, t, a, z)["cagr"])
    return float(np.median(cs)), float(np.mean([c >= bb["cagr"] for c in cs])), len(cs)


# ------------------------------------------------------------------ 保留期（只能跑一次）
def final_holdout(b, lab, runs: dict):
    """runs = {名稱: (cfg, p)}。2021-01-01 起；同一次算完，寫鎖檔，之後拒絕再跑。"""
    lock = OUT / "_holdout_done.json"
    if lock.exists():
        raise RuntimeError("保留期已經跑過一次，依規則不得再跑：" + lock.read_text(encoding="utf-8")[:200])
    bb = bench(lab, HOLDOUT)
    res = {"0050": bb, "策略": {}}
    for nm, (cfg, p) in runs.items():
        ret, t = backtest(b, cfg, p)
        s = perf(b, ret, t, HOLDOUT)
        ys = yearly(b, ret, lab, HOLDOUT)
        rg = regime_table(b, t, HOLDOUT, None)
        res["策略"][nm] = dict(s=s, 通過=bool(s["cagr"] > bb["cagr"]), 年度=ys.to_dict("records"), 行情=rg.to_dict("records"))
    OUT.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
    return res


# ------------------------------------------------------------------ 逐筆筆記
REG = {1: "多頭", -1: "空頭", 0: "盤整"}
MODN = {"A": "A 上揚均線＋長紅低點拉回", "B": "B 糾結後長紅突破", "C": "C 空排表態失敗", "E": "E 平台試單"}


def review(t, b):
    msg = []
    d = int(t["dir"]); hold = int(t["hold"]); atr = t["atr"]
    if t["pnl_pts"] > 0:
        give = (1 - t["pnl_pts"] / t["mfe"]) if t["mfe"] > 0 else np.nan
        if give == give and give > 0.5:
            msg.append(f"賺但吐回最大浮盈的 {give:.0%}：5MA 移動停利偏慢，可試 60/10 反向（更快）或浮盈後保本")
        else:
            msg.append("順勢賺到，沿 5MA 持有的效果符合預期")
    else:
        if t["reason"] == "stop":
            slip_beyond = ((t["stop"] - t["exit_px"]) if d == 1 else (t["exit_px"] - t["stop"]))
            if hold <= 3:
                msg.append(f"進場後 {hold} 根內就被收盤停損：疑似假拉回；可要求拉回棒縮量／下一根站回再進")
            if atr and slip_beyond > 0.5 * atr:
                msg.append(f"收盤確認停損吃到跳空：實際出場比停損價多損 {slip_beyond:.0f} 點（{slip_beyond / atr:.1f} ATR）")
        elif t["reason"] == "trail":
            msg.append("移動停利啟動後回落到 5MA 之下才出，仍虧：趨勢力道太弱，進場時 5MA 追不上")
        elif t["reason"] in ("固定停損", "固定停利", "逾時"):
            msg.append(f"教學用固定 87 點出場：{t['reason']}")
        else:
            msg.append("資料尾端強制平倉")
    if (d == 1 and t["regime"] == -1) or (d == -1 and t["regime"] == 1):
        msg.append(f"逆勢單（週K {REG[t['regime']]}進場做{'多' if d == 1 else '空'}）：老吳原則『不逆勢』")
    if t["module"] == "E":
        msg.append("平台試單")
    return "；".join(msg)


def notes_table(b, trades, a, z=None, tag=""):
    rows = []
    for _, t in trades.iterrows():
        ei, xi = int(t.entry_i), int(t.exit_i)
        ed = b.date[ei]
        if ed < pd.Timestamp(a) or (z and ed >= pd.Timestamp(z)):
            continue
        rows.append(dict(版本=tag, 進場時間=str(b.ts[ei])[:16], 方向="多" if t["dir"] == 1 else "空", 模組=MODN.get(t.module, t.module),
                         進場價=round(t.entry_px, 1), 出場時間=str(b.ts[xi])[:16], 出場價=round(t.exit_px, 1), 出場原因=t.reason,
                         損益點=round(t.pnl_pts, 1), 損益元每口=round(t.pnl_pts * MULT), 報酬率=round(t.ret, 4), 持有根數=int(t.hold),
                         最大不利偏移點=round(t.mae, 1), 最大有利偏移點=round(t.mfe, 1), 最大曝險單位=t.units, 當時行情=REG[int(t.regime)],
                         事後檢討=review(t, b)))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 文件
def write_docs(R, P, H):
    lab, bd = R["lab"], R["bd"]
    hb = H["0050"]; S = H["策略"]
    L = []
    L.append("# 吳小弟策略（老吳 @stockwu888 台指期均線策略）回測\n")
    L.append("> **免責**：歷史資料的研究回測，非買賣建議、不下單。策略細節是從老吳公開貼文**歸納與推論**的（他完整的進出場只在收費群組教），"
             "標『推論』的地方是我補的可調參數，不是他的原始設定。淘汰規則：年化輸同期含息、扣成本的 0050 -> 淘汰。\n")
    L.append("> **兩個重要但書**：(1) 原策略主週期是 **60 分 K**，資料湖沒有台指期 60 分 K，所以主結果是**日K 版（週期與原策略不同）**，"
             "60 分 K 只有現貨指數代理（約 3 年、無夜盤、有基差）；(2) 參數只用 2015～2020 優化，2021 起是保留期，**只跑了一次**（鎖檔 `_holdout_done.json`）。\n")
    # ---- 0
    rows = []
    for ver in ("A只多", "B多空"):
        v = R["ver"][ver]
        for kind, sd in (("預設參數", v["sd"]), ("優化參數", v["so"])):
            s = S[f"{ver} {kind}"]["s"]
            sb = v["bb"]
            rows.append({"版本": f"{ver} {kind}", "搜尋期年化(2015-20)": fp(sd["cagr"]), "搜尋期0050": fp(sb["cagr"]),
                         "保留期年化(2021起)": fp(s["cagr"]), "保留期0050": fp(hb["cagr"]), "差距": f"{(s['cagr'] - hb['cagr']) * 100:+.1f} 點",
                         "保留期回撤": fp(s["mdd"]), "0050回撤": fp(hb["mdd"]), "勝率": fp(s["win"], 0), "盈虧比": fn(s["payoff"]),
                         "最大單筆虧損(點)": fn(s["maxloss_pts"], 0), "交易數": int(s["n"]),
                         "判定": "通過" if S[f"{ver} {kind}"]["通過"] else "**淘汰**（年化輸 0050）"})
    L.append("## 〇、通過／淘汰清單（日K 版，1 倍名目曝險，保留期 2021-01 起只跑一次）\n")
    L.append(f"保留期 0050 含息扣成本：年化 {fp(hb['cagr'])}、最大回撤 {fp(hb['mdd'])}、夏普 {fn(hb['sharpe'])}。\n")
    L.append(md(pd.DataFrame(rows)))
    npass = sum(1 for k in S if "風險" not in k and S[k]["通過"])
    L.append(f"\n**結論：{npass} 個版本通過。**" + ("" if npass else "日K 版預設與優化、只做多與多空，全數輸 0050；吳小弟策略在這個資料與週期下沒有找到能贏過 0050 的設定。")
             + "（60 分 K 代理與真期貨短樣本見第七節，只是參考，沒有進保留期。）\n")
    # ---- 1 白話
    L.append("## 一、策略白話（照著做會做出一樣的單）\n")
    L.append("**哲學**：只看 K 棒與均線；順勢、不接刀；沒有目標價，用均線移動停利；停損放在『技術位』（長紅棒低點）而不是固定點數；只在收棒時決策。\n")
    L.append("**主結果＝規格書原則全開（試單、停損反手、加減碼、多空都做；B 版），A 版＝同樣原則但只做多（對照）。**\n\n**怎麼執行（日K 版；60 分 K 原版把『日』換成『60 分鐘』即可）**\n")
    L.append("1. 每天收盤後（原策略是每小時收棒後）檢查一次，**隔天開盤**下單，不用當天收盤價。\n"
             "2. **長紅棒**＝收紅、實體 >= 1.5 倍過去 15 根平均實體（推論值）。記下它的最低點 L 與最高點 H。\n"
             "3. **模組 A 做多**：近 8 根內有長紅棒；今天最低點回到 L 附近（距離 <= 0.3 ATR）**且**同時回到『上揚的 10MA 或 20MA』附近（均線比 3 根前高），"
             "今天收盤仍在 L 與該均線之上 -> 收盤後確認，隔天開盤進多 1 口。\n"
             "4. **停損**：停損價＝L 與該均線兩者中離現價較近（較高）的那個；**收盤**跌破停損價，隔天開盤出場（不是盤中觸價）。"
             "停損距離超過 3 ATR 的訊號直接放棄（老吳：停損距離要自己能接受才進場）。\n"
             "5. **移動停利**：價格收盤站上 5MA 之後，只要收盤跌破 5MA，隔天開盤出場（60/5）。**沒有目標價**。\n"
             "6. **停損後**：同方向 5 根內不再進場；B 版若當天同時符合反方向訊號，隔天開盤直接反手。\n"
             "7. **趨勢濾網（5a）**：只在均線多排（5>10>20>60 且 20、60 均線上揚）做多；空排才放空。\n"
             "8. **加減碼（5c）**：基礎部位 0.5 倍；收盤突破長紅高點 H 加到 1 倍；收盤跌破 5MA 先減半、跌破 10MA 全出。\n"
             "9. **模組 B**：均線糾結（5/10/20MA 的距離 < 0.5 ATR）連續兩根後，長紅棒收盤站上全部短均線 -> 進多，停損＝該長紅低點。"
             "**模組 C**：空排之後創低但收盤站回 5MA -> 試單進多。**模組 E**：平台（20 根區間 < 4 ATR、低點被測試 >= 2 次）低點附近試單 0.5 倍，突破平台高點補到 1 倍。"
             "**模組 D**（5 分 K 碰 20T 反壓放空）需要 5 分 K，資料湖沒有，**未實作**。\n")
    L.append("**部位**：主結果固定 1 倍名目曝險（一口對應帳戶權益）；附表另有『每筆風險 1.5%』口數版（口數＝權益 x 1.5% /（停損距離 x 200），名義曝險上限 3 倍）。\n")
    # ---- 2 資料
    L.append("## 二、資料：先處理的問題\n")
    L.append("| 路線 | 資料 | 涵蓋 | 限制 |\n|---|---|---|---|\n"
             "| ① 日K 版（主結果） | `index_ohlc` symbol=FUT，真實台指期日盤日K | 2000～2026 | **週期與原策略不同**（日K 取代 60 分 K；5MA／10MA／20MA／60MA／240MA 週期數字照原樣，但代表的時間長度長 5 倍以上）；沒有夜盤；固定 87 點在 2015 年（約 1 萬點）占 0.9%、在 2026 年（4 萬多點）只占 0.2% |\n"
             "| ② 60 分 K 代理版 | `index_intraday` 加權指數現貨 60 分 K | 2023-09～2026-10（約 742 個交易日、3,700 根） | 現貨不是期貨：**沒有夜盤、有基差**；樣本短；只能跑預設參數，無法做 2015～2020 優化與保留期 |\n"
             f"| ③ 真期貨 60 分 K | `index_intraday` FUT／FUT_N 1 分 K 合成（期交所逐筆，日盤＋夜盤） | 2026-08 起，{P['fut']['days'] if 'fut' in P else '-'} 個交易日、{P['fut']['n'] if 'fut' in P else '-'} 根 | 樣本太短，只列參考 |\n")
    L.append("**合規的台指期分 K 歷史來源查證**（關鍵字：FinMind TaiwanFuturesTick 分K；期交所 期貨每筆成交資料 歷史；台指期 1分K 歷史資料 免費 下載）：\n"
             "- 期交所網站只免費提供「近 30 個交易日」逐筆成交資料；更早的歷史要向期交所『交易歷史資料申請』（期貨智慧資訊商店 E-Data Shop）付費購買，且沒有 API。出處：[期交所 FAQ：是否有提供期貨交易歷史資料](https://www.taifex.com.tw/cht/9/tradersQAIS)、[前 30 個交易日期貨每筆成交資料](https://www.taifex.com.tw/cht/3/futPrevious30DaysSalesData)。\n"
             "- 專案的 `config.py` 已記載：FinMind 分 K 要付費等級，台指期沒有 Yahoo 代號；而政府資料開放平臺資料集 20668（期交所每日期貨每筆成交資料）已經由 `pipeline/sources/taifex.py` 每天進 `index_intraday`（FUT 日盤、FUT_N 夜盤 1 分 K，`src=taifex`），"
             "所以**不需要新寫抓取腳本**；從 2026-08-17 開始累積，約 2027 年 8 月才會有滿一年的真期貨 60 分 K。\n"
             "- 鐵人賽文章（[iT邦：由 Tick 轉分K](https://ithelp.ithome.com.tw/articles/10223693)）與券商 API（永豐 Shioaji kbars，[iT邦範例](https://ithelp.ithome.com.tw/articles/10276580)）可取得歷史分 K，但需券商帳號、可回溯年限未確認；未使用。\n"
             "- **要把策略用原週期回測 2015～2020 的唯一合規辦法**：向期交所申購『臺股期貨百分秒成交簡檔』等歷史資料（費用未查到，需 Andy 決定），或用券商 API 抓 1 分 K。\n")
    # ---- 3 六步
    L.append("## 三、六步流程（日K 版，搜尋期 2015～2020，預設參數；每步記錄加了什麼、為什麼、結果怎麼變）\n")
    for ver in ("A只多", "B多空"):
        v = R["ver"][ver]
        df = v["steps"].copy()
        prev = None
        out = []
        for _, r in df.iterrows():
            dlt = "-" if prev is None else f"{(r['年化'] - prev['年化']) * 100:+.1f} 點／回撤 {(r['回撤'] - prev['回撤']) * 100:+.1f} 點／勝率 {((r['勝率'] or 0) - (prev['勝率'] or 0)) * 100:+.1f} 點"
            out.append({"步驟": r.步驟, "加了什麼／為什麼": r.加了什麼為什麼, "年化": fp(r.年化), "回撤": fp(r.回撤), "勝率": fp(r.勝率, 0),
                        "盈虧比": fn(r.盈虧比), "最大單筆虧損(點)": fn(r.最大單筆虧損點, 0), "交易數": int(r.交易數),
                        "相對上一步": dlt})
            prev = r
        L.append(f"**{ver}**（同窗 0050 年化 {fp(v['bb']['cagr'])}、回撤 {fp(v['bb']['mdd'])}）\n\n" + md(pd.DataFrame(out)))
        L.append(f"主結果組態：{' -> '.join(v['kept'])}。\n")
    L.append("讀法：步驟 1～3 用固定 87 點出場（上下各 87 點、最多持有 30 根），只是在檢驗『進場點本身有沒有優勢』——勝率約 4 成、盈虧比 < 1，等於沒有優勢。"
             "優勢主要來自步驟 4 之後的正式出場（盈虧比拉到 2.5～3.5），但勝率只有約 3 成，總報酬仍很低，因為訊號很少（6 年 15～60 筆）、持倉時間短。\n")
    # ---- 4 行情
    L.append("## 四、多頭／空頭／盤整三種行情各看一次（搜尋期 2015～2020 的交易，依進場當天週K 40 週均線狀態分類）\n")
    for ver in ("A只多", "B多空"):
        v = R["ver"][ver]
        for nm, tb in (("步驟4 正式出場", v["rg4"]), ("最終保留組態", v["rgf"])):
            t = tb.copy()
            t["勝率"] = t["勝率"].map(lambda x: fp(x, 0)); t["平均每筆點數"] = t["平均每筆點數"].map(lambda x: fn(x, 0))
            t["合計點數"] = t["合計點數"].map(lambda x: fn(x, 0)); t["最大單筆虧損點"] = t["最大單筆虧損點"].map(lambda x: fn(x, 0))
            L.append(f"**{ver} - {nm}**\n\n" + md(t))
    L.append("（行情標籤是延後一週的 40 週均線狀態，無前視；標籤落後，所以急殺後的反彈日常被歸在『空頭』。）\n")
    # ---- 5 預設 vs 優化
    L.append("## 五、預設參數 vs 優化參數（並排）\n")
    prm = pd.DataFrame([dict(參數=k, 預設=str(DEFAULT_P[k]), A只多優化=str(R["ver"]["A只多"]["popt"][k]), B多空優化=str(R["ver"]["B多空"]["popt"][k])) for k in GRID_P])
    L.append(md(prm))
    cmp_rows = []
    for ver in ("A只多", "B多空"):
        v = R["ver"][ver]
        sd, so = v["sd"], v["so"]
        d, o = S[f"{ver} 預設參數"]["s"], S[f"{ver} 優化參數"]["s"]
        cmp_rows.append({"版本": ver, "搜尋期 預設年化": fp(sd["cagr"]), "搜尋期 優化年化": fp(so["cagr"]), "保留期 預設年化": fp(d["cagr"]),
                         "保留期 優化年化": fp(o["cagr"]), "優化在搜尋期多賺": f"{(so['cagr'] - sd['cagr']) * 100:+.1f} 點",
                         "優化在保留期多賺": f"{(o['cagr'] - d['cagr']) * 100:+.1f} 點", "優化版鄰域贏0050比例": fp(v["nb"][1], 0), "優化版鄰域中位年化": fp(v["nb"][0])})
    L.append(md(pd.DataFrame(cmp_rows)))
    L.append("優化目標：搜尋期年化最大、至少 15 筆交易（不另加回撤限制，因為這是 Andy 指定的策略，不套用我們自己加的限制）；網格 " + str(R["ver"]["A只多"]["ngrid"]) + " 組（每個版本）。"
             "『優化在搜尋期多賺』與『在保留期多賺』的落差，就是過擬合的程度。\n")
    # ---- 6 年度
    L.append("## 六、依年份拆開的績效（預設參數；2004～2020 為搜尋期與更早的未調參期間，2021 起為保留期）\n")
    ys = {}
    for ver in ("A只多", "B多空"):
        ret, t = backtest(bd, R["ver"][ver]["cfg"])
        ys[ver] = yearly(bd, ret, lab, "2004-01-01", HOLDOUT)
    y = ys["A只多"].rename(columns={"策略": "A只多 預設"})
    y["B多空 預設"] = ys["B多空"]["策略"].values
    y = y[["年", "A只多 預設", "B多空 預設", "0050"]]
    hy = {}
    for ver in ("A只多", "B多空"):
        hy[ver] = pd.DataFrame(S[f"{ver} 預設參數"]["年度"])
    hrow = hy["A只多"].rename(columns={"策略": "A只多 預設"})
    hrow["B多空 預設"] = hy["B多空"]["策略"].values
    allv = pd.concat([y, hrow[["年", "A只多 預設", "B多空 預設", "0050"]]])
    for c in ("A只多 預設", "B多空 預設", "0050"):
        allv[c] = allv[c].map(fp)
    L.append(md(allv))
    # ---- 7 代理
    L.append("## 七、60 分 K 代理版與真期貨短樣本（只用預設參數，無優化、無保留期；僅供參考）\n")
    if "spot" in P:
        sp = P["spot"]
        L.append(f"現貨加權指數 60 分 K（沒有夜盤、有基差），統計區間 {sp['a']} 起（前 75 天給 240 根均線暖機），固定停損上限 120 點（規格書值）、固定 87 點逾時 40 根；同窗 0050 年化 {fp(sp['A'][1]['cagr'])}。\n")
        for ver in ("A", "B"):
            df = sp[ver][0]
            out = pd.DataFrame([{"步驟": r.步驟, "年化": fp(r.年化), "回撤": fp(r.回撤), "勝率": fp(r.勝率, 0), "盈虧比": fn(r.盈虧比),
                                 "最大單筆虧損(點)": fn(r.最大單筆虧損點, 0), "交易數": int(r.交易數)} for _, r in df.iterrows()])
            L.append(f"**{ver} 版（60 分 K 代理）**\n\n" + md(out))
        L.append("樣本只有約 3 年、交易數 20～60 筆，統計上不能下結論；最大單筆虧損約 -600～-1,950 點，可能與隔夜大跌（例如 2024-08-05）有關，未逐筆確認。\n")
    if "fut" in P:
        L.append(f"真期貨 60 分 K（期交所逐筆合成，含夜盤）只有 {P['fut']['days']} 個交易日、{P['fut']['n']} 根，連 240 根均線都剛暖機完，**不跑統計**；約 2027 年 8 月累積滿一年後再做。\n")
    # ---- 8 風險口數
    L.append("## 八、附表：每筆風險 1.5% 口數版（保留期，預設參數）\n")
    rr = []
    for ver in ("A只多", "B多空"):
        s = S[f"{ver} 預設參數＋每筆風險1.5%口數"]["s"]; s1 = S[f"{ver} 預設參數"]["s"]
        rr.append({"版本": ver, "1 倍年化": fp(s1["cagr"]), "1 倍回撤": fp(s1["mdd"]), "風險口數年化": fp(s["cagr"]), "風險口數回撤": fp(s["mdd"]),
                   "風險口數最大單筆虧損(權益%)": fp(s["maxloss_ret"]), "交易數": int(s["n"]), "年化輸贏0050": f"{(s['cagr'] - hb['cagr']) * 100:+.1f} 點"})
    L.append(md(pd.DataFrame(rr)))
    L.append("口數＝權益 x 1.5% /（進場價到停損價的點數 x 200 元），名義曝險上限 3 倍；未模擬保證金追繳，僅供對照，不是主結果。\n")
    # ---- 9 筆記
    L.append("## 九、逐筆交易筆記與檢討\n")
    notes = []
    for ver in ("A只多", "B多空"):
        v = R["ver"][ver]
        for kind, p in (("預設參數", None), ("優化參數", v["popt"])):
            ret, t = backtest(bd, v["cfg"], p)
            for per, (a, z) in (("搜尋期2015-20", SEARCH), ("保留期2021起", (HOLDOUT, None))):
                notes.append(notes_table(bd, t, a, z, tag=f"{ver} {kind}／{per}"))
    nt = pd.concat(notes)
    nt.to_csv(OUT / "trades_wu.csv", index=False, encoding="utf-8-sig")
    N = ["# 吳小弟策略 逐筆交易筆記（日K 版）\n", "每筆含進場理由（模組、當時行情）、出場原因、損益、最大不利偏移（MAE）、事後檢討（規則式自動產生，彙整見 README 第十節）。\n"]
    for tag, g in nt.groupby("版本", sort=False):
        N.append(f"\n## {tag}（{len(g)} 筆）\n")
        for _, r in g.iterrows():
            N.append(f"- **{r['進場時間'][:10]} {r['方向']}** {r['模組']} 進 {r['進場價']} -> {r['出場時間'][:10]} 出 {r['出場價']}（{r['出場原因']}，持有 {r['持有根數']} 根）｜"
                     f"損益 {r['損益點']} 點（每口 {r['損益元每口']:,} 元，權益 {r['報酬率']:.2%}）｜MAE {r['最大不利偏移點']} 點、MFE {r['最大有利偏移點']} 點｜當時週K {r['當時行情']}｜**檢討**：{r['事後檢討']}")
    (OUT / "trades_notes_wu.md").write_text("\n".join(N), encoding="utf-8")
    base = nt[nt.版本.str.contains("預設參數")]
    worst = base.nsmallest(5, "損益點")[["版本", "進場時間", "方向", "模組", "出場原因", "損益點", "報酬率", "持有根數", "當時行情", "事後檢討"]]
    L.append(f"完整逐筆見 `trades_notes_wu.md`、`trades_wu.csv`（共 {len(nt)} 筆）。**預設參數最慘的五筆**：\n")
    L.append(md(worst))
    # ---- 10 建議
    L.append("## 十、優化建議（由逐筆檢討彙整）\n")
    tags = base.事後檢討.str.split("；").explode().str[:12].value_counts().head(6)
    L.append("事後檢討最常出現的類型：" + "；".join(f"{k}…（{v} 次）" for k, v in tags.items()) + "。\n")
    L.append(CONC(R, S, hb, base))
    L.append("## 十一、已知限制與缺陷\n")
    L.append("- 主結果是日K 版，**週期與原策略不同**：原策略靠 60 分 K 的高頻率機會與 5MA 緊貼停利，日K 版 6 年只有 15～60 筆交易，統計力很低；日K 版的失敗**不代表**原 60 分 K 策略失敗。\n"
             "- 規格書的『紅棒明顯』『均線附近』都是主觀判讀，我量化成 m 倍平均實體與 δ 倍 ATR；結果不好時規格書建議優先調這兩項，本輪已在網格內（m、δ）。\n"
             "- 『移動停利須先站上過 5MA 才啟動』『加減碼的 5MA 減半、10MA 全出』是我的推論，不是老吳原話。\n"
             "- 模組 D（5 分 K）未實作；模組 C 與 E 是逆勢／試單，規格書說小資金應關閉；依 Andy 指示『指定的策略照原則跑』，主結果全開（試單、停損反手、加碼、多空都做），六步表（第三節）列出各原則的邊際效果。\n"
             "- 保留期（2021 起）不是真正沒看過的資料：前兩輪研究已看過 2013～2026 台指期整體走勢；本輪沒有用它調整設計。\n"
             "- 成本：每口單邊手續費 50 元、期交稅十萬分之二、滑價 2 點，沿用前幾輪口徑；0050 為含息、扣手續費、ETF 稅與滑價。\n")
    L.append("## 十二、試了幾組\n")
    reg = pd.read_csv(OUT / "registry.csv")
    L.append(f"- 六步流程每版 10 組（共 20 組）；優化網格每版 {R['ver']['A只多']['ngrid']} 組（共 {2 * R['ver']['A只多']['ngrid']} 組）；鄰域檢查每版 {R['ver']['A只多']['nb'][2]} 組；60 分 K 代理 20 組。"
             "全部登記在 `registry.csv`。優化只在搜尋期 2015～2020 內做。\n")
    L.append("## 十三、重現\n\n`python -m pipeline.compute.wu_lab`（只跑搜尋期，約 2 分鐘）；`--holdout` 才會跑保留期（已跑過，鎖檔存在時直接讀鎖檔）。測試：`pytest tests/test_wu_lab.py -q`。\n")
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")


def CONC(R, S, hb, base):
    bs = [(k, S[k]["s"]) for k in S if "風險" not in k]
    best = max(bs, key=lambda kv: kv[1]["cagr"])
    lines = [f"- 保留期表現最好的是『{best[0]}』：年化 {fp(best[1]['cagr'])}、回撤 {fp(best[1]['mdd'])}，仍輸 0050（{fp(hb['cagr'])}／{fp(hb['mdd'])}）{abs(best[1]['cagr'] - hb['cagr']) * 100:.1f} 點。"
             "日K 版主結果（B 多空、規格書原則全開）持倉日只占約 27～32%，其餘空手只賺現金利息，保留期是 0050 年化 27.6% 的大多頭，無法跟上。",
             "- **出場有價值、進場沒有**：固定 87 點的進場測試勝率約 4 成、盈虧比 < 1（進場點本身沒優勢）；換成 60/5 移動停利後盈虧比升到 2.5 以上，這與老吳『沒有目標價、沿 5T 走』的說法一致——賺的是讓獲利奔跑，不是進場點神準。",
             "- **想貼近原策略就必須有 60 分 K**：日K 的 5MA 等於一週，停利太慢也太鈍；請 Andy 決定是否申購期交所『臺股期貨百分秒成交簡檔』（2015～2020）或接券商 API 1 分 K，才能用原週期正式驗證（資料與費用由 Andy 決定，我不代購）。",
             "- 若不補資料，可行的低成本方向：把日K 版當『0050 的避險腳』（空頭或空排時才做空單），而不是取代 0050；或等 2027-08 真期貨 60 分 K 滿一年。",
             "- 『停損後反手』在日K 版很少觸發：B 版原則全開時，搜尋期 5 次、保留期 2 次；單獨加進六步表（步驟 5b）時因為已有多排／空排濾網，結果完全沒變。『加減碼』提高盈虧比但最大單筆虧損變大（基礎部位減半抵銷不了跳空）。"]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ 主流程
def fp(x, d=1):
    return F.fmt(x, True, d)


def fn(x, d=2):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def md(df):
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def search_all():
    lab = F.Lab(); bd = make_daily()
    registry = []
    R = {"lab": lab, "bd": bd, "ver": {}}
    for ver, shorts in (("A只多", False), ("B多空", True)):
        df, bb = run_steps(bd, lab, shorts, *SEARCH, hold=30, registry=registry, tag=ver)
        cfg, kept = pick_final(df, shorts)
        ret4, t4 = backtest(bd, df[df.步驟.str.startswith("4 ")].iloc[0]._cfg)
        retf, tf = backtest(bd, cfg)
        rg4 = regime_table(bd, t4, *SEARCH); rgf = regime_table(bd, tf, *SEARCH)
        sd = perf(bd, retf, tf, *SEARCH)
        popt, sc, ngrid = optimize(bd, lab, cfg)
        reto, to = backtest(bd, cfg, popt)
        so = perf(bd, reto, to, *SEARCH)
        nb = neigh_stats(bd, lab, cfg, popt)
        registry.append(dict(版本=ver, 步驟="優化網格", 年化=so["cagr"], 回撤=so["mdd"], 交易數=ngrid))
        R["ver"][ver] = dict(steps=df, bb=bb, cfg=cfg, kept=kept, rg4=rg4, rgf=rgf, sd=sd, so=so, popt=popt, nb=nb, ngrid=ngrid, shorts=shorts)
    R["registry"] = registry
    return R


def proxy_runs(R):
    lab = R["lab"]
    reg = (lab.X["reg"][40], lab.idx)
    out = {}
    try:
        bs = make_60m_spot(reg)
        a = str((bs.date[0] + pd.Timedelta(days=75)).date())
        out["spot"] = dict(b=bs, a=a, A=run_steps(bs, lab, False, a, None, maxstop_pts=120.0, hold=40), B=run_steps(bs, lab, True, a, None, maxstop_pts=120.0, hold=40))
    except Exception as exc:                     # noqa: BLE001
        out["spot_err"] = str(exc)
    try:
        bf = make_60m_fut(reg)
        out["fut"] = dict(b=bf, n=bf.n, days=int(pd.Series(bf.date).nunique()))
    except Exception as exc:                     # noqa: BLE001
        out["fut_err"] = str(exc)
    return out


def main(do_holdout=False):
    OUT.mkdir(parents=True, exist_ok=True)
    R = search_all()
    lab, bd = R["lab"], R["bd"]
    for ver, v in R["ver"].items():
        print(ver, "保留規則選出:", v["kept"], "| 預設搜尋期", round(v["sd"]["cagr"], 4), "優化", round(v["so"]["cagr"], 4), v["popt"], "鄰域", v["nb"])
    pd.DataFrame(R["registry"]).to_csv(OUT / "registry.csv", index=False, encoding="utf-8-sig")
    P = proxy_runs(R)
    if not do_holdout:
        return R, P, None
    lock = OUT / "_holdout_done.json"
    if lock.exists():
        H = json.loads(lock.read_text(encoding="utf-8"))
    else:
        runs = {}
        for ver, v in R["ver"].items():
            runs[f"{ver} 預設參數"] = (v["cfg"], None)
            runs[f"{ver} 優化參數"] = (v["cfg"], v["popt"])
            runs[f"{ver} 預設參數＋每筆風險1.5%口數"] = (dict(v["cfg"], risk=0.015), None)
        H = final_holdout(bd, lab, runs)
        H["_params"] = {k: (v["popt"]) for k, v in R["ver"].items()}
    write_docs(R, P, H)
    return R, P, H


if __name__ == "__main__":
    main(do_holdout="--holdout" in sys.argv)
