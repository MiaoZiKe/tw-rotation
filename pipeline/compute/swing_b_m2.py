"""波段系統 B-M2：每日名單、S1/S2 進場訊號與紙上帳戶的逐日推進（純函式，不碰檔案）。

> 免責：研究用，不是買賣建議，不會下單。這裡只算「如果照凍結規則做會怎樣」的假想帳本。

規格來源（凍結登記，不准改任何參數）：策略委員會第三、四回合（r3_registry.json／r4_registry.json）。
全新樣本 2012-12～2016-12 驗證：不降速 年化 18.8%／最大回撤 19.3%（同期 0050 10.8%／21.0%）。
**這是回測、不是承諾**；已看過的 2017～2026 資料裡不降速版本回撤 40%（0050 34%）。前向帳本從新資料開始，好壞照實記。

規則（B-M2）：
  名單  中型池（60 日成交值中位數排名 101～600、>=1,000 萬元、股價>=10）、營收動能（近 3 月均／近 12 月均，法定可用日＝次月 10 日）
        前 60% 且 52 週新高接近度前 20%、收盤>60 日線、相對加權指數強度>0；分數＝0.4 營收動能 + 0.4 新高 + 0.2 相對強度
        + 族群廣度前三分之一加 5；取前 30（同族群最多 5 檔）；剔除「延伸過度」（收盤 > 20 日線 + 3 ATR）。
  進場  名單內、流動性 20 日均成交值>=3,000 萬元，且
          S1 回檔到 20 日線（最低<=20 日線 x1.01、收紅、收>20 日線、20 日線向上、收>60 日線），或
          S2 突破 20 日高（收>前 20 日高、量>=1.2 倍 20 日均量、收>60 日線）。
        訊號在 t 日收盤後產生，t+1 日開盤價成交（絕不用 t 日收盤成交）。
  停損  近 5 日最低 − 0.3 ATR14；距離須在 max(3%, 1 ATR) 到 10% 之間（以訊號收盤與實際成交價各驗一次）。
  出場  收盤跌破 50 日均線 → 次日開盤出；停損觸價（跳空以開盤價）；最長持有 60 個交易日（第 60 日收盤）。
  部位  每筆風險 1%（SWING_BRAKE 另有降速）；單檔名目<=20%；總名目曝險<=100%；最多 6 檔；同族群最多 2 檔；
        同日多檔依營收動能由高到低。
  降速  （只有 SWING_BRAKE）距淨值高點回撤>=5% 風險x0.5、>=8% x0.25、>=12% 停新單（冷卻 20 個交易日後以 x0.25 復出）；
        連虧>=3 筆 x0.5、>=5 筆 x0.25（取較小者，不相乘）。
  成本  手續費 0.1425% 買賣各一次（不打折）、賣出證交稅 0.3%、滑價 0.1% 單邊。

還原價：dividend_results 的 reference_price／before_price（含現金與股票股利）當除權息係數，往前連乘；
再用「還原後單日變動超出 [0.62, 1.6] 倍」補未登記的股本變動（漲跌停限制下不可能是真實價格行為）。與回測引擎同一套寫法。

與回測引擎（engine/r3lib.py、risk.py、portfolio2.py）有意識的差異（已在 docs 與回報寫明）：
  1. 同族群最多 2 檔：引擎的 basic 模式沒有這條，這裡照任務規格加上。
  2. 降速用的回撤＝「每日淨值（含持倉浮盈虧、扣預估出場成本）距高點」，引擎是只在候選進場日取樣的毛 R 盯市淨值。
  3. 股數取整數、曝險用目前實現淨值當分母；引擎用比例（無整數股）。
  4. 被帳戶拒絕的訊號不會像引擎那樣「虛擬佔用」同檔位置到出場日（引擎先去重再進帳戶）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ 凍結參數（登記後不改）
WINDOW = 330                      # 算特徵用的交易日數（250 日高 + 緩衝）
POOL_LO, POOL_HI = 100, 600       # 成交值中位數排名 (100, 600]
POOL_MIN_MED_TURNOVER = 1e7
POOL_MIN_PRICE = 10.0
LIQ_MIN_AVG_TURNOVER = 3e7
LIST_N = 30
LIST_PER_GROUP = 5
PRM_MIN, PNH_MIN = 60.0, 80.0
EXT_ATR = 3.0
STOP_ATR = 0.3
MIN_DIST, MAX_DIST = 0.03, 0.10
LOCK_UP = 1.095                   # 開盤 >= 前收 x1.095 且高=低 視為漲停鎖死、買不到
MA_EXIT = 50
MAX_HOLD = 60
REF_R = 3.0                       # 參考目標價＝進場 + 3R（僅供參考，B-M2 的出場不看目標價）

BASE_RISK = 0.01
MAX_POS = 6
MAX_PER_GROUP = 2
MAX_NOTIONAL = 0.20
MAX_EXPOSURE = 1.0
DD_STEPS = ((0.05, 0.5), (0.08, 0.25))
DD_HALT = 0.12
HALT_COOLDOWN_DAYS = 20
STREAK_STEPS = ((3, 0.5), (5, 0.25))

FEE, TAX, SLIP = 0.001425, 0.003, 0.001

DISCLAIMER = "研究用，不是買賣建議，不會下單。"


@dataclass(frozen=True)
class AccountCfg:
    name: str
    throttle: bool


SWING = AccountCfg("SWING", False)
SWING_BRAKE = AccountCfg("SWING_BRAKE", True)


def buy_px(px: float) -> float:
    """買進實付單價（含滑價與手續費）。"""
    return px * (1 + SLIP) * (1 + FEE)


def sell_px(px: float) -> float:
    """賣出實收單價（含滑價、手續費、證交稅）。"""
    return px * (1 - SLIP) * (1 - FEE - TAX)


def risk_multiplier(streak: int, dd: float) -> float:
    """連虧與回撤兩個降速取較小者（不相乘，避免縮到回不來）。"""
    m = 1.0
    for n, k in STREAK_STEPS:
        if streak >= n:
            m = min(m, k)
    for d, k in DD_STEPS:
        if dd >= d:
            m = min(m, k)
    return m


# ------------------------------------------------------------------ 還原價
def _piv(df: pd.DataFrame, col: str, dates: pd.DatetimeIndex, codes: list[str]) -> pd.DataFrame:
    return df.pivot(index="date", columns="code", values=col).reindex(index=dates, columns=codes)


def adjust_prices(px: pd.DataFrame, dv: pd.DataFrame) -> dict[str, Any]:
    """px：長表（date, code, open, high, low, close, volume, turnover），date 為 Timestamp，已濾掉非四碼股、ETF、興櫃。
    dv：dividend_results（date, code, before_price, reference_price），只能含 <= 最後一個交易日的列。
    回傳還原後的 open/high/low/close、原始 Craw、量 V、成交值 T。最新一天的還原價＝原始價（沒有未來事件）。"""
    px = px.drop_duplicates(["date", "code"], keep="last")
    dates = pd.DatetimeIndex(sorted(px["date"].unique()))
    codes = sorted(px["code"].unique())
    f = dv[dv["code"].isin(codes)].copy() if len(dv) else dv.copy()
    if len(f):
        f["f"] = f["reference_price"] / f["before_price"]
        f = f[(f["f"] > 0.3) & (f["f"] < 1.0)]
        f["date"] = pd.to_datetime(f["date"])
        f = f[f["date"] > dates[0]]
    if len(f):
        f = f.groupby(["date", "code"])["f"].prod().reset_index()
        F = f.pivot(index="date", columns="code", values="f")
        F = F.reindex(dates.union(F.index)).fillna(1.0)          # 非交易日的除權息係數併入下一個交易日
        pos = dates.searchsorted(F.index)
        F2 = F.groupby(np.minimum(pos, len(dates) - 1)).prod()
        F2.index = dates[F2.index]
        F = F2.reindex(dates).fillna(1.0).reindex(columns=codes).fillna(1.0)
    else:
        F = pd.DataFrame(1.0, index=dates, columns=codes)
    M = (F[::-1].cumprod()[::-1]) / F                           # 該日之後所有事件係數的連乘
    Craw = _piv(px, "close", dates, codes)
    adj0 = Craw * M
    rr = adj0 / adj0.ffill().shift(1)
    ev = (rr < 0.62) | (rr > 1.6)                                # 未登記的股本變動（分割／減資）
    F3 = rr.where(ev).fillna(1.0)
    M3 = (F3[::-1].cumprod()[::-1]) / F3
    MM = M * M3
    out: dict[str, Any] = {"dates": dates, "codes": codes, "Craw": Craw}
    for k in ("open", "high", "low", "close"):
        out[k] = _piv(px, k, dates, codes) * MM
    out["V"] = _piv(px, "volume", dates, codes)
    out["T"] = _piv(px, "turnover", dates, codes)
    return out


def _atr(H: pd.DataFrame, L: pd.DataFrame, C: pd.DataFrame) -> pd.DataFrame:
    pc = C.shift(1)
    tr = np.fmax(np.fmax(H - L, (H - pc).abs()), (L - pc).abs())
    return tr.ewm(alpha=1 / 14, adjust=False).mean()


def revenue_momentum_asof(rev: pd.DataFrame, asof: pd.Timestamp, codes: list[str]) -> pd.Series:
    """營收動能 = 近 3 月均 / 近 12 月均（單月暴衝：最大月 > 其餘兩月合計 → 去掉該月重算）。
    可用日＝次月 10 日（config.FINANCIAL_DEADLINES 的月營收口徑）；寧可晚用，asof 之前還沒到可用日的月份一律不用。"""
    if rev is None or len(rev) == 0:
        return pd.Series(np.nan, index=codes)
    R = rev.drop_duplicates(["ym", "code"]).pivot(index="ym", columns="code", values="revenue").sort_index()
    m3, m12 = R.rolling(3).mean(), R.rolling(12).mean()
    mx = R.rolling(3).max()
    oth = R.rolling(3).sum() - mx
    dom = mx > oth
    rm = (m3 / m12).where(~dom, ((R.rolling(3).sum() - mx) / 2) / m12)
    avail = pd.to_datetime(rm.index + "-01") + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)
    rm.index = avail
    rm = rm[~rm.index.duplicated()]
    rm = rm[rm.index <= asof]
    if rm.empty:
        return pd.Series(np.nan, index=codes)
    return rm.ffill().iloc[-1].reindex(codes)


# ------------------------------------------------------------------ 每日名單與訊號
@dataclass
class DayView:
    asof: pd.Timestamp
    adj: dict[str, Any]
    watch: pd.DataFrame           # 當日名單（rank, code, score, group, ext, prm, pnh, rm_raw, nh_raw）
    cands: pd.DataFrame           # 當日收盤後的進場候選（明日開盤成交）


def build_view(px: pd.DataFrame, dv: pd.DataFrame, rev: pd.DataFrame, idx_close: pd.Series, group_of: pd.Series,
               asof: pd.Timestamp) -> DayView | None:
    """只用 <= asof 的資料算 asof 當日的名單與 S1/S2 候選。asof 當天沒有任何價格就回 None。
    不偷看的保證：所有輸入先被截到 asof；rolling／shift 都只往過去看；營收只用法定可用日 <= asof 的月份。"""
    px = px[px["date"] <= asof]
    if px.empty or px["date"].max() != asof:
        return None
    dates = pd.DatetimeIndex(sorted(px["date"].unique()))[-WINDOW:]
    px = px[px["date"].isin(dates)]
    dv = dv[pd.to_datetime(dv["date"]) <= asof] if len(dv) else dv
    adj = adjust_prices(px, dv)
    dates, codes = adj["dates"], adj["codes"]
    O, H, L, C, V, T, Craw = (adj[k] for k in ("open", "high", "low", "close", "V", "T", "Craw"))
    ic = idx_close[idx_close.index <= asof].reindex(dates.union(idx_close.index[idx_close.index <= asof])).ffill().reindex(dates)
    ATR = _atr(H, L, C)
    MA20, MA60 = C.rolling(20).mean(), C.rolling(60).mean()
    V20 = V.rolling(20).mean().shift(1)
    H250 = H.rolling(250).max()
    hh20 = H.rolling(20).max().shift(1)
    med60 = T.rolling(60, min_periods=40).median()
    last = lambda X: X.iloc[-1]  # noqa: E731
    craw, med = last(Craw), last(med60)
    rank = med.rank(ascending=False)
    pool = (rank > POOL_LO) & (rank <= POOL_HI) & (med >= POOL_MIN_MED_TURNOVER) & (craw >= POOL_MIN_PRICE)
    liq = (last(T.rolling(20).mean()) >= LIQ_MIN_AVG_TURNOVER) & (craw >= POOL_MIN_PRICE)
    RM = revenue_momentum_asof(rev, asof, codes)
    c_t, atr_t, ma20_t, ma60_t = last(C), last(ATR), last(MA20), last(MA60)
    NH = c_t / last(H250)
    r60, r20 = c_t / C.iloc[-61] - 1 if len(C) > 60 else np.nan, c_t / C.iloc[-21] - 1 if len(C) > 20 else np.nan
    i60 = ic.iloc[-1] / ic.iloc[-61] - 1 if len(ic) > 60 else np.nan
    i20 = ic.iloc[-1] / ic.iloc[-21] - 1 if len(ic) > 20 else np.nan
    RS = ((r60 - i60) + (r20 - i20)) / 2
    pct = lambda x: x.where(pool).rank(pct=True) * 100  # noqa: E731
    Prm, Pnh, Prs = pct(RM), pct(NH), pct(RS)
    grp = group_of.reindex(codes)
    hi = (pool & (Pnh >= PNH_MIN))
    cnt = pool.groupby(grp).transform("sum")
    hic = hi.groupby(grp).transform("sum")
    GB = ((hic - hi.astype(float)) / np.maximum(cnt - 1, 1)).where(cnt >= 5)
    gbtop = GB.where(pool).rank(pct=True) >= 2 / 3
    ext = c_t > ma20_t + EXT_ATR * atr_t
    elig = pool & (Prm >= PRM_MIN) & (Pnh >= PNH_MIN) & (c_t > ma60_t) & (RS > 0)
    score = 0.4 * Prm + 0.4 * Pnh + 0.2 * Prs + 5 * gbtop.astype(float)
    rows, cg = [], {}
    e = score[elig.fillna(False)].sort_values(ascending=False, kind="stable")
    for code, s in e.items():
        g = grp[code]
        if cg.get(g, 0) >= LIST_PER_GROUP:
            continue
        cg[g] = cg.get(g, 0) + 1
        rows.append(dict(rank=len(rows) + 1, code=code, score=float(s), group=g, ext=bool(ext[code]), prm=float(Prm[code]), pnh=float(Pnh[code]),
                         rm_raw=float(RM[code]) if pd.notna(RM[code]) else np.nan, nh_raw=float(NH[code])))
        if len(rows) >= LIST_N:
            break
    watch = pd.DataFrame(rows, columns=["rank", "code", "score", "group", "ext", "prm", "pnh", "rm_raw", "nh_raw"])
    watch.insert(0, "date", asof)
    # ---- S1 / S2（簡化進場），只看名單內且沒有延伸過度的
    o_t, l_t, v_t = last(O), last(L), last(V)
    pull = (l_t <= 1.01 * ma20_t) & (c_t > ma20_t) & (c_t > o_t) & (ma20_t > MA20.iloc[-6]) & (c_t > ma60_t)
    brk = (c_t > last(hh20)) & (v_t >= 1.2 * last(V20)) & (c_t > ma60_t)
    stop = L.rolling(5).min().iloc[-1] - STOP_ATR * atr_t
    cand_rows = []
    for r in watch.itertuples():
        if r.ext:
            continue
        code = r.code
        s1, s2 = bool(pull[code]), bool(brk[code])
        if not (s1 or s2) or not bool(liq[code]):
            continue
        e_ref, st, a = float(c_t[code]), float(stop[code]), float(atr_t[code])
        if not (np.isfinite(e_ref) and np.isfinite(st) and np.isfinite(a)) or st >= e_ref:
            continue
        dist, atr_pct = (e_ref - st) / e_ref, a / e_ref
        min_dist = max(MIN_DIST, atr_pct)
        if dist < min_dist or dist > MAX_DIST:
            continue
        cand_rows.append(dict(signal_date=asof, code=code, kind="S1+S2" if (s1 and s2) else ("S1" if s1 else "S2"), rank=int(r.rank), score=float(r.score),
                              group=r.group, rm_raw=float(r.rm_raw) if pd.notna(r.rm_raw) else 0.0, nh_raw=float(r.nh_raw), prm=float(r.prm), pnh=float(r.pnh),
                              e_ref=e_ref, stop=st, atr_pct=float(atr_pct), min_dist=float(min_dist), dist=float(dist)))
    cands = pd.DataFrame(cand_rows)
    return DayView(asof=asof, adj=adj, watch=watch, cands=cands)


def day_bars(adj: dict[str, Any], asof: pd.Timestamp, codes: set[str]) -> dict[str, dict[str, float]]:
    """asof 當日各檔的開高低收、50 日線與『除權息換基準係數 f』。
    f＝（今天的還原基準下）前一筆收盤 / 前一筆原始收盤；沒有除權息時為 1，有除權息時 <1。
    持倉的停損、成本、股數要跟著換基準，否則除息日會被當成跌破停損。ma50 與 f 都用該檔自己的成交日序列（停牌日不算）。"""
    out: dict[str, dict[str, float]] = {}
    for code in codes:
        if code not in adj["close"].columns:
            continue
        c = adj["close"][code].dropna()
        if c.empty or c.index[-1] != asof:
            continue
        raw = adj["Craw"][code].dropna()
        f = 1.0
        if len(c) > 1 and len(raw) > 1 and raw.iloc[-2] > 0:
            f = float(c.iloc[-2] / raw.iloc[-2])
        ma = float(c.rolling(MA_EXIT).mean().iloc[-1]) if len(c) >= MA_EXIT else float("nan")
        out[code] = dict(o=float(adj["open"][code].iloc[-1]), h=float(adj["high"][code].iloc[-1]), l=float(adj["low"][code].iloc[-1]),
                         c=float(c.iloc[-1]), ma50=ma, f=f)
    return out


# ------------------------------------------------------------------ 帳戶逐日推進
def new_state(capital: float) -> dict[str, Any]:
    return dict(eq=capital, unsettled=[], streak=0, halt_since=None, peak=capital, last_nav=capital, positions=[], pending=[], n_closed=0)


def _scale(p: dict, f: float) -> None:
    """除權息換基準：價位乘 f、股數除以 f（含息報酬口徑，R 與損益不變）。"""
    if abs(f - 1.0) < 1e-12:
        return
    for k in ("stop", "buy_px", "entry_b", "risk_px", "last_c", "target"):
        if k in p and p[k] is not None:
            p[k] *= f
    p["sh"] /= f


def _clean(x: Any) -> Any:
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def step_account(st: dict[str, Any], d: pd.Timestamp, bars: dict[str, dict[str, float]], cands: pd.DataFrame, cfg: AccountCfg,
                 names: dict[str, str] | None = None) -> tuple[dict[str, Any], dict[str, list[dict]]]:
    """推進一個帳戶一天。順序：除權息換基準 → 結算前一日已出場損益 → 降速狀態 → 開盤成交昨日候選 → 既有持倉的出場 → 收盤標價 → 產生明日候選。
    昨日候選用今天的開盤價成交；既有持倉「今天出場」仍占用名額與曝險直到明天（與引擎相同：出場日當天不釋放）。
    回傳 (新狀態, {'signals': [...], 'holdings': [...]})。"""
    names = names or {}
    ds = d.strftime("%Y-%m-%d")
    st = {**st, "unsettled": list(st["unsettled"]), "positions": [dict(p) for p in st["positions"]], "pending": [dict(c) for c in st["pending"]]}
    sig: list[dict] = []

    def ev(event: str, code: str, **kw):
        sig.append(dict(date=ds, plan=cfg.name, code=code, name=names.get(code, ""), event=event, **{k: _clean(v) for k, v in kw.items()}))

    # 0) 除權息換基準
    for p in st["positions"]:
        b = bars.get(p["code"])
        if b:
            _scale(p, b["f"])
    for c in st["pending"]:
        b = bars.get(c["code"])
        if b:
            c["stop"] *= b["f"]
            c["e_ref"] *= b["f"]
    # 1) 結算前一日（含）以前已出場的損益 → 可用於部位大小的實現淨值與連虧
    for x in sorted(st["unsettled"], key=lambda x: x["exit_date"]):
        st["eq"] += x["pnl"]
        st["streak"] = st["streak"] + 1 if x["R"] < 0 else 0
    st["unsettled"] = []
    eq_s = st["eq"]
    # 2) 降速狀態（只有 SWING_BRAKE）。回撤＝昨日收盤淨值距高點
    mult, halting = 1.0, False
    if cfg.throttle:
        dd = 1 - st["last_nav"] / st["peak"] if st["peak"] > 0 else 0.0
        mult = risk_multiplier(st["streak"], dd)
        if dd >= DD_HALT:
            st["halt_since"] = st["halt_since"] or ds
            if (d - pd.Timestamp(st["halt_since"])).days < HALT_COOLDOWN_DAYS * 7 / 5:
                halting = True
            mult = min(mult, 0.25)
        else:
            st["halt_since"] = None
    open_start = list(st["positions"])
    held_codes = {p["code"] for p in open_start}
    taken: list[dict] = []
    # 3) 開盤成交昨日候選（同日依營收動能高到低）
    for c in sorted(st["pending"], key=lambda c: (-(c.get("rm_raw") or 0.0), c["code"])):
        code = c["code"]
        if code in held_codes:
            continue                                                # 同檔持有中不重複進場（出場日當天也不行）
        b = bars.get(code)
        if b is None:
            ev("REJECT", code, kind=c["kind"], note="明日沒有成交（停牌或無資料），訊號作廢")
            continue
        o, stop0 = b["o"], c["stop"]
        base = dict(kind=c["kind"], group=c["group"], rank=c["rank"], rm_raw=c["rm_raw"])
        if o >= c["e_ref"] * LOCK_UP and b["h"] == b["l"]:
            ev("REJECT", code, price=o, note="開盤漲停鎖死，買不到", **base)
            continue
        if o <= stop0:
            ev("REJECT", code, price=o, stop=stop0, note="開盤價已低於停損，不進場", **base)
            continue
        rpx = o - stop0
        if rpx / o < c["min_dist"] or rpx / o > MAX_DIST:
            ev("REJECT", code, price=o, stop=stop0, note=f"開盤後停損距離 {rpx / o:.1%} 不在 {c['min_dist']:.1%}～{MAX_DIST:.0%}", **base)
            continue
        cur = open_start + taken
        why = None
        if cfg.throttle and halting:
            why = "回撤 >= 12% 停新單（冷卻中）"
        elif len(cur) >= MAX_POS:
            why = f"持倉已滿 {MAX_POS} 檔"
        elif sum(1 for p in cur if p["group"] == c["group"]) >= MAX_PER_GROUP:
            why = f"同族群已有 {MAX_PER_GROUP} 檔"
        risk = BASE_RISK * mult
        n_frac = risk / (rpx / o)
        if n_frac > MAX_NOTIONAL:
            risk *= MAX_NOTIONAL / n_frac
            n_frac = MAX_NOTIONAL
        if why is None and sum(p["sh"] * p["entry_b"] for p in cur) / eq_s + n_frac > MAX_EXPOSURE + 1e-9:
            why = f"總名目曝險將超過 {MAX_EXPOSURE:.0%}"
        shares = int(math.floor(eq_s * risk / rpx)) if why is None else 0
        if why is None and shares < 1:
            why = "部位不足 1 股"
        if why:
            ev("REJECT", code, price=o, stop=stop0, note=why, **base)
            continue
        reason = (f"{'回檔 20 日線' if c['kind'] == 'S1' else '突破 20 日高' if c['kind'] == 'S2' else '回檔 20 日線＋突破 20 日高'}（{c['kind']}）；"
                  f"名單第 {c['rank']} 名（營收動能 {c['rm_raw']:.2f}、離 52 週高 {1 - c['nh_raw']:.1%}、族群 {c['group']}）；"
                  f"停損＝近 5 日低 −0.3ATR（距離 {rpx / o:.1%}）；風險 {risk:.2%}" + (f"（降速 x{mult:g}）" if mult < 1 else ""))
        p = dict(code=code, group=c["group"], kind=c["kind"], signal_date=c["signal_date"], entry_date=ds, entry_px=o, buy_px=buy_px(o), entry_b=o,
                 stop=stop0, risk_px=rpx, sh=float(shares), shares=shares, risk_frac=shares * rpx / eq_s, n_frac=shares * o / eq_s, eq0=eq_s,
                 target=o + REF_R * rpx, hold=0, mae=0.0, last_c=o, exit_next=None, rank=c["rank"], rm_raw=c["rm_raw"], reason=reason, mult=mult)
        taken.append(p)
        ev("ENTRY", code, kind=c["kind"], group=c["group"], rank=c["rank"], rm_raw=c["rm_raw"], price=o, stop=stop0, target=o + REF_R * rpx, r_px=rpx,
           r_pct=rpx / o, shares=shares, risk_frac=p["risk_frac"], weight=p["n_frac"], reason=reason, note=f"{c['signal_date']} 收盤訊號，{ds} 開盤成交")
    # 4) 持倉出場 + 5) 收盤標價與明日出場訊號
    survivors: list[dict] = []
    closed_today: list[dict] = []
    new_ids = {id(p) for p in taken}
    traded = cost = 0.0
    for p in taken:                                                 # 買進：成交額與成本（滑價 + 手續費）
        traded += p["sh"] * p["entry_px"]
        cost += p["sh"] * (p["buy_px"] - p["entry_px"])

    def close_pos(p: dict, px: float, why: str, label: str) -> None:
        nonlocal traded, cost
        traded += p["sh"] * px
        cost += p["sh"] * (px - sell_px(px))
        pnl = p["sh"] * (sell_px(px) - p["buy_px"])
        R = (sell_px(px) - p["buy_px"]) / p["risk_px"]
        ret = sell_px(px) / p["buy_px"] - 1
        closed_today.append(dict(exit_date=ds, pnl=pnl, R=R))
        ev("EXIT", p["code"], kind=p["kind"], group=p["group"], price=px, stop=p["stop"], target=p["target"], r_px=p["risk_px"], shares=p["shares"],
           reason=why, result_r=R, result_ret=ret, hold_days=p["hold"], mae=p["mae"], entry_date=p["entry_date"], entry_px=p["entry_px"], note=label)

    for p in open_start + taken:
        b = bars.get(p["code"])
        if b is None:
            survivors.append(p)
            continue
        is_new = id(p) in new_ids
        p["hold"] += 1
        p["mae"] = min(p["mae"], b["l"] / p["entry_b"] - 1)
        p["last_c"] = b["c"]
        if not is_new and p["exit_next"]:
            close_pos(p, b["o"], "收盤跌破 50 日線，次日開盤出場", "MA50 出場")
            continue
        if b["l"] <= p["stop"]:
            px = p["stop"] if is_new else min(b["o"], p["stop"])
            close_pos(p, px, "停損觸價" + ("（跳空以開盤價）" if (not is_new and b["o"] < p["stop"]) else ""), "停損出場")
            continue
        if not math.isnan(b["ma50"]) and b["c"] < b["ma50"]:
            p["exit_next"] = "ma"
            ev("EXIT_SIGNAL", p["code"], kind=p["kind"], price=b["c"], stop=p["stop"], note=f"收盤 {b['c']:.2f} 跌破 50 日線 {b['ma50']:.2f}，明日開盤出場")
        elif p["hold"] >= MAX_HOLD:
            close_pos(p, b["c"], f"持有滿 {MAX_HOLD} 個交易日，收盤出場", "時間出場")
            continue
        survivors.append(p)
    st["positions"] = survivors
    st["unsettled"] = closed_today
    st["n_closed"] += len(closed_today)
    # 6) 收盤淨值（扣預估出場成本）
    unreal = sum(p["sh"] * (sell_px(p["last_c"]) - p["buy_px"]) for p in survivors)
    eq_all = st["eq"] + sum(x["pnl"] for x in closed_today)
    nav = eq_all + unreal
    st["peak"] = max(st["peak"], nav)
    st["last_nav"] = nav
    # 7) 明日候選（排除收盤仍持有的；明天要出場的也算持有中）
    held_close = {p["code"] for p in survivors}
    pend = []
    if cands is not None and len(cands):
        for r in cands.to_dict("records"):
            if r["code"] in held_close:
                continue
            r["signal_date"] = ds
            pend.append(r)
            tgt = r["e_ref"] + REF_R * (r["e_ref"] - r["stop"])
            ev("ENTRY_SIGNAL", r["code"], kind=r["kind"], group=r["group"], rank=r["rank"], rm_raw=r["rm_raw"], price=r["e_ref"], stop=r["stop"], target=tgt,
               r_px=r["e_ref"] - r["stop"], r_pct=r["dist"],
               reason=f"{r['kind']}；名單第 {r['rank']} 名；停損＝近 5 日低 −0.3ATR", note="收盤後產生，明日開盤價假想成交（價格為訊號日收盤，僅參考）")
    st["pending"] = pend
    hold_rows = []
    for p in survivors:
        mv = p["sh"] * p["last_c"]
        hold_rows.append(dict(date=ds, plan=cfg.name, code=p["code"], name=names.get(p["code"], ""), group=p["group"], kind=p["kind"], shares=p["shares"],
                              entry_date=p["entry_date"], entry_px=p["entry_px"], close=p["last_c"], mkt_value=mv, weight=mv / nav if nav else 0.0,
                              stop=p["stop"], target=p["target"], r_px=p["risk_px"], upl_pct=sell_px(p["last_c"]) / p["buy_px"] - 1,
                              upl_r=(sell_px(p["last_c"]) - p["buy_px"]) / p["risk_px"], hold_days=p["hold"], mae=p["mae"],
                              status="明日開盤出場（收盤跌破 50 日線）" if p["exit_next"] else "持有", reason=p["reason"]))
    return st, {"signals": sig, "holdings": hold_rows, "nav": nav, "eq_all": eq_all, "unreal": unreal,
                "cost_in": sum(p["sh"] * p["buy_px"] for p in survivors), "mkt": sum(p["sh"] * p["last_c"] for p in survivors), "mult": mult, "halting": halting,
                           "traded": traded, "cost": cost}
