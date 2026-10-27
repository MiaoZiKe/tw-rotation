"""每日盤後訊號與紙上帳本（前向驗證）。

> 免責：研究用，不是買賣建議，不會下單。這裡只算「如果照規則做會怎樣」的假想帳本。

為什麼有這支：策略委員會（docs/strategy_lab/council/r3_final.md）選出兩套「穩健版」——
  * E2（個股＋ETF）：加權指數 200 日線 ±2% 切換正二（00631L）。線上 100% 正二；線下 30% 正二 + 70% 現金。
  * F2（台指期）：永遠持有名目 1.3 倍，每月第一個交易日檢查，曝險偏離超過 0.10 倍才調口數。
回測已經過門檻，但回測是在看過的資料上跑的。這支從 2026-10-27 起用「新資料」前向驗證：
每天盤後算訊號、隔日開盤價假想成交並扣成本、寫進 data/paper/（只增不改）。結果好壞都照實記，不調參數。

紅線（backtest 專家守則）：
  * 訊號只用 t 日收盤以前的資料；成交在 t+1 日開盤價。算 t 日列時絕對不讀 t 日之後的任何價格（tests 有驗）。
  * 成本全算：ETF 手續費 0.1425%（不打折）、賣出證交稅 0.1%、滑價（正二 0.10%、0050 0.05%）；
    期貨 調整成本 0.03% + 期交稅 0.002%、每次結算換月 4.5 點（滑價 4 + 手續費 0.5）。
  * 帳本只能 append：已經寫下的列永遠不改；每個方案只接在最後一天之後（不補洞、不回填）。

三個方案 + 一個基準，同一張帳本表（paper/ledger，key＝date, plan）：
  E2     正二 200 日線方案（門檻：同期含息 0050 x 1.5）
  F2     台指期 1.3 倍（門檻：同期含息 0050 x 1.0）
  SAT    個股衛星（凍結候選 x2=nh85）：營收動能 + 站上 20/60/120 日線 + 近 52 週新高 >= 85%，前 200 檔流動性池取 10 檔。
         這條帳戶本身是「衛星部位單獨的紀錄」；真正的資金配置在 E2SAT 裡占 20%。
         2026-10-27 起衛星改列真實配置：依據第八輪存活者偏誤壓力測試（分支 claude/elegant-fermi-scpgme 的
         docs/strategy_lab/round8/survivorship_stress.md，最壞情境三個窗仍贏 0050）。價格沒還原除息仍是已知限制。
  E2SAT  80% E2 + 20% 衛星（SAT），每年第一個交易日開盤再平衡回 80/20（門檻：同期含息 0050 x 1.4＝0.8x1.5+0.2x1.0）。
  BENCH  0050 含息（除息金額於除息日以收盤價再投入），同樣在第一個成交日開盤買進並扣成本。

假想本金 1,000 萬元（讓微型台指期口數取整有意義；報酬都用淨值比，與本金大小無關）。
現金利率用 1.6%/年（lev_lab RF_BY_YEAR 的 2025~2026 值，假設）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from pipeline import config
from pipeline.util import store

log = logging.getLogger(__name__)

DISCLAIMER = "研究用，不是買賣建議，不會下單。"
START = pd.Timestamp("2026-10-27")          # 帳本第一個訊號日（收盤後算訊號，次一交易日開盤成交）
CAPITAL = 10_000_000.0                      # 假想本金（元）
RF = 0.016                                  # 現金年利率（假設）

# --- E2
E2_MA = 200
E2_BAND = 0.02
E2_W_UP = 1.0                               # 線上：100% 正二
E2_W_DOWN = 0.30                            # 線下：30% 正二 + 70% 現金
# --- F2
F2_X = 1.3
F2_BAND = 0.10
BIG_PT = 200.0                              # 大台每點 200 元
MICRO_PT = 10.0                             # 微型台指每點 10 元
ROLL_PTS = 4.5
FUT_COST = 0.0001 + 0.0002 + 0.00002        # 手續費 + 滑價 + 期交稅（占名目）
M_MAINT = 0.08                              # 維持保證金率（占名目，futures_lab2 同值）
# --- ETF 成本（單邊）
FEE = 0.001425
TAX = 0.001
SLIP = {"00631L": 0.001, "0050": 0.0005}
# --- 衛星
SAT_N = 10
SAT_POOL = 200
SAT_NEAR_HIGH = 0.85
SAT_BUY = 0.001425 + 0.001
SAT_SELL = 0.001425 + 0.001 + 0.003

E2SAT_W_E2 = 0.80                           # E2SAT 的 E2 部位目標權重
E2SAT_W_SAT = 0.20                          # E2SAT 的衛星部位目標權重（每年第一個交易日開盤調回）
SAT_MA = (20, 60, 120)                      # 凍結規格 ma3：收盤要同時站上 20/60/120 日線
SAT_NH_MIN_OBS = 200                        # 凍結規格 nh：252 日滾動最高價至少要有 200 筆（min_periods=200）

PLANS = ("BENCH", "E2", "F2", "SAT", "E2SAT")   # BENCH 先算，其他方案要帶同期基準；E2SAT 自成一格不依賴別的方案
MULT = {"E2": 1.5, "F2": 1.0, "SAT": 1.0, "BENCH": 1.0, "E2SAT": E2SAT_W_E2 * 1.5 + E2SAT_W_SAT * 1.0}

T_LEDGER = "paper/ledger"
T_SAT = "paper/satellite"
T_E2SAT = "paper/e2sat_holdings"


# ------------------------------------------------------------------ 純函式：訊號
def e2_signal(close: pd.Series, n: int = E2_MA, band: float = E2_BAND) -> pd.DataFrame:
    """加權指數收盤、n 日簡單均線、上下帶、狀態（1＝線上、0＝線下）。
    遲滯：收盤 > 均線 x (1+band) 轉『線上』，收盤 < 均線 x (1-band) 轉『線下』，帶內維持原狀態；均線還沒有值時狀態＝0。
    第 i 列只用到第 i 列以前的收盤（rolling 與逐日狀態機都是因果的）。"""
    c = close.astype(float)
    ma = c.rolling(n).mean()
    up, dn = ma * (1 + band), ma * (1 - band)
    st = np.zeros(len(c), np.int8)
    cur = 0
    cv, uv, dv = c.to_numpy(), up.to_numpy(), dn.to_numpy()
    for i in range(len(c)):
        if not np.isnan(uv[i]):
            if cv[i] > uv[i]:
                cur = 1
            elif cv[i] < dv[i]:
                cur = 0
        st[i] = cur
    return pd.DataFrame({"close": c, "ma": ma, "upper": up, "lower": dn, "state": st}, index=c.index)


def settle_days(cal: pd.DatetimeIndex) -> np.ndarray:
    """每月第三個週三＝台指期結算日（遇休市順延到下一個交易日）。"""
    out = np.zeros(len(cal), bool)
    for y in range(cal[0].year, cal[-1].year + 1):
        for m in range(1, 13):
            d0 = pd.Timestamp(y, m, 1)
            w = d0 + pd.Timedelta(days=(2 - d0.weekday()) % 7 + 14)
            j = cal.searchsorted(w)
            if j < len(cal) and cal[j].month == m:
                out[j] = True
    return out


def third_wednesday(y: int, m: int) -> pd.Timestamp:
    d0 = pd.Timestamp(y, m, 1)
    return d0 + pd.Timedelta(days=(2 - d0.weekday()) % 7 + 14)


def next_weekday(d: pd.Timestamp) -> pd.Timestamp:
    n = d + pd.Timedelta(days=1)
    while n.weekday() >= 5:
        n += pd.Timedelta(days=1)
    return n


def futures_calendar(asof: pd.Timestamp) -> dict[str, Any]:
    """F2 的日曆資訊。未來的休市日資料湖不知道，一律用『週一到週五』近似（遇國定假日實際日期會順延）。"""
    nxt = next_weekday(asof)
    sd = third_wednesday(asof.year, asof.month)
    if sd <= asof:
        y, m = (asof.year + 1, 1) if asof.month == 12 else (asof.year, asof.month + 1)
        sd = third_wednesday(y, m)
    y, m = (asof.year + 1, 1) if asof.month == 12 else (asof.year, asof.month + 1)
    first = pd.Timestamp(y, m, 1)
    while first.weekday() >= 5:
        first += pd.Timedelta(days=1)
    return {"next_settle": sd, "roll_tomorrow": bool(nxt == sd), "next_check": first,
            "check_tomorrow": bool(nxt.month != asof.month)}


def f2_sizing(nav: float, index_level: float, x: float = F2_X) -> dict[str, float]:
    """目前淨值換算的 x 倍口數：大台（每點 200 元）取小數、微型台指（每點 10 元）取整。"""
    notional = nav * x
    return {"notional": notional, "big": notional / (index_level * BIG_PT), "micro": float(round(notional / (index_level * MICRO_PT)))}


def pick_satellite(close: pd.DataFrame, turnover: pd.DataFrame, rev_ratio: pd.Series, asof: pd.Timestamp) -> pd.DataFrame:
    """衛星清單（只用 asof 當日收盤以前的資料），規格 = round8 frozen_candidates.json 的「x2=nh85」：
    前 200 檔（近 60 日平均成交值）∩ 營收動能（近 3 月均營收 / 近 12 月均營收 > 1）∩ 收盤同時站上 20/60/120 日線（ma3）
    ∩ 收盤 >= 52 週高點 x 0.85（252 日滾動最高、至少 200 筆），依營收動能比值由大到小取 10 檔。
    與凍結規格的差異（以凍結規格為準）：原實作漏了 ma3 條件，2026-10-27 補上；
    仍存在的差異：研究端用還原價，這裡資料湖是未還原收盤（除權息日會讓 52 週高點與均線偏高，偏保守）。
    回傳欄位 rank, code, rev_ratio, near_high。"""
    c = close.loc[:asof]
    t = turnover.loc[:asof]
    last = c.iloc[-1]
    win = c.tail(252)
    hi = win.max().where(win.count() >= SAT_NH_MIN_OBS)
    near = (last / hi)
    ma_ok = pd.Series(True, index=c.columns)
    for n in SAT_MA:
        ma_ok &= (last > c.tail(n).mean()) & (c.tail(n).count() >= n)
    liq = t.tail(60).mean()
    pool = liq.dropna().nlargest(SAT_POOL).index
    s = rev_ratio.dropna()
    s = s[s.index.isin(pool) & (s > 1.0)]
    s = s[(near.reindex(s.index) >= SAT_NEAR_HIGH).fillna(False)]
    s = s[ma_ok.reindex(s.index).fillna(False).astype(bool)]
    top = s.sort_values(ascending=False).head(SAT_N)
    return pd.DataFrame({"rank": range(1, len(top) + 1), "code": top.index, "rev_ratio": top.values, "near_high": near.reindex(top.index).values})


# ------------------------------------------------------------------ 資料
def _years_from(y0: int) -> list[int]:
    return list(range(y0, datetime.now(timezone.utc).year + 1))


def load_market(asof: pd.Timestamp | None = None) -> dict[str, Any]:
    """讀資料湖。price_daily 一律逐檔 read 再 concat（store.read 就是這樣讀；2026 分區 schema 與前幾年不同，整個資料夾一次讀會炸）。"""
    px = store.read("price_daily", years=_years_from(2025))
    if px.empty:
        return {}
    px["date"] = pd.to_datetime(px["date"])
    if asof is not None:
        px = px[px["date"] <= asof]
    px = px.drop_duplicates(["date", "code"], keep="last")
    one = px[px.code.isin(["0050", "00631L"])]
    etf = {c: one[one.code == c].set_index("date").sort_index()[["open", "close"]].astype(float) for c in ("0050", "00631L")}
    stk = px[px.code.str.fullmatch(r"\d{4}")]
    piv = lambda col: stk.pivot_table(index="date", columns="code", values=col, aggfunc="last").sort_index()   # noqa: E731
    ix = store.read("index_ohlc")
    ix["date"] = pd.to_datetime(ix["date"])
    if asof is not None:
        ix = ix[ix["date"] <= asof]
    idx = {s: ix[ix.symbol == s].drop_duplicates("date").set_index("date").sort_index()[["open", "close"]].astype(float) for s in ("TSE", "FUT")}
    dv = pd.concat([store.read("etf_dividend_events"), store.read("dividend_events")], ignore_index=True)
    if not dv.empty:
        dv = dv[(dv.code == "0050") & (dv.kind == "cash") & dv.ex_date.notna()].copy()
        dv["ex_date"] = pd.to_datetime(dv["ex_date"])
        dv = dv.drop_duplicates("ex_date").set_index("ex_date")["amount"].astype(float)
    else:
        dv = pd.Series(dtype=float)
    rv = store.read("revenue_monthly", years=_years_from(2024))
    return {"etf": etf, "stk_open": piv("open"), "stk_close": piv("close"), "stk_turn": piv("turnover"), "idx": idx, "div": dv, "rev": rv}


def rev_ratio_asof(rev: pd.DataFrame, asof: pd.Timestamp) -> pd.Series:
    """asof 當天已經法定公布的月營收動能比（近 3 月均 / 近 12 月均）。
    營收的法定公布日是次月 10 日：ym 月份的營收要等到『次月 11 日』才可用（寧可晚用，不偷看）。"""
    if rev.empty:
        return pd.Series(dtype=float)
    R = rev.pivot_table(index="ym", columns="code", values="revenue", aggfunc="last").sort_index()
    ok = []
    for ym in R.index:
        y, m = map(int, str(ym).split("-"))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        if pd.Timestamp(y, m, 11) <= asof:
            ok.append(ym)
    R = R.loc[ok]
    if len(R) < 12:
        return pd.Series(dtype=float)
    return R.tail(3).mean() / R.tail(12).mean()


# ------------------------------------------------------------------ 帳本（只增不改）
def read_ledger() -> pd.DataFrame:
    df = store.read(T_LEDGER)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["plan", "date"]).reset_index(drop=True)


def append_only(table: str, df: pd.DataFrame, keys: list[str]) -> int:
    """只加新 key 的列；已存在的 key 一律不動（store.append 預設『後到覆蓋』，這裡先擋掉重複 key）。
    另外：每個 plan 只能接在已記錄的最後一天之後，不補洞、不回填（避免事後改寫歷史）。"""
    if df is None or df.empty:
        return 0
    old = store.read(table)
    new = df.copy()
    if not old.empty:
        old_k = old[keys].astype(str).agg("|".join, axis=1)
        new_k = new[keys].astype(str).agg("|".join, axis=1)
        new = new[~new_k.isin(set(old_k))]
        if "plan" in keys and "plan" in old.columns:
            last = pd.to_datetime(old["date"]).groupby(old["plan"]).max()
            keep = [pd.Timestamp(r["date"]) > last.get(r["plan"], pd.Timestamp.min) for _, r in new.iterrows()]
            new = new[keep]
    if new.empty:
        return 0
    return store.append(table, new)


def _row(date: pd.Timestamp, plan: str, **kw) -> dict[str, Any]:
    base = {"date": date.strftime("%Y-%m-%d"), "plan": plan, "nav": np.nan, "cash": np.nan, "units": 0.0, "notional": 0.0, "exposure": 0.0,
            "target": np.nan, "held": np.nan, "action": "", "fill_px": np.nan, "traded": 0.0, "cost": 0.0, "sig": "{}", "extra": "{}",
            "plan_cum": np.nan, "bench_cum": np.nan, "thresh_cum": np.nan, "disclaimer": DISCLAIMER}
    base.update(kw)
    return base


# ------------------------------------------------------------------ 逐日推進
def _split_mult(prev_close: float, open_: float) -> float:
    """ETF 拆股：開盤價相對昨收 < 0.6 視為拆股（k=round(1/ratio)）；> 3 視為反分割。回傳『把今天價格換算到昨天尺度』的乘數。"""
    r = open_ / prev_close
    if r < 0.6:
        return float(round(1 / r))
    if r > 3.0:
        return 1.0 / float(round(r))
    return 1.0


def step_etf(prev: dict | None, d: pd.Timestamp, opx: float, cpx: float, prev_close: float | None, code: str,
             target_next: float, rf: float = RF, cash_adj: float = 0.0) -> dict[str, Any]:
    """E2 帳戶一天（cash_adj≠0 是 E2SAT 年度再平衡：開盤前先和衛星部位劃撥現金，並強制調回目標權重）：隔夜現金利息 -> 開盤執行『昨天收盤決定的目標權重』-> 收盤估值 -> 設定明天的目標。"""
    cost = traded = 0.0
    fill = np.nan
    action = ""
    if prev is None:
        cash, units, held = CAPITAL, 0.0, np.nan
        pending = target_next                      # 起始日：只決定目標，次一交易日開盤才成交
    else:
        cash, units, held = float(prev["cash"]) * (1 + rf / 252), float(prev["units"]), prev["held"]
        pending = float(prev["target"])
        if prev_close is not None:
            units *= _split_mult(prev_close, opx)
        cash += cash_adj
        if np.isnan(held) or abs(pending - held) > 1e-9 or cash_adj != 0.0:
            e_open = cash + units * opx
            delta = pending * e_open - units * opx                 # 元；>0 買進
            slip = SLIP[code]
            rate = (FEE + slip) if delta > 0 else (FEE + TAX + slip)
            if delta > 0:
                delta = max(min(delta, cash / (1 + rate)), 0.0)    # 買進金額 + 成本不能超過手上現金（不借錢）
            cost = abs(delta) * rate
            cash -= delta + cost
            units += delta / opx
            traded, fill, held = delta, opx, pending
            action = f"開盤{'買進' if delta > 0 else '賣出'} {abs(delta):,.0f} 元（目標權重 {pending:.0%}）"
    nav = cash + units * cpx
    return dict(cash=cash, units=units, held=held, target=target_next, nav=nav, cost=cost, traded=traded, fill=fill, action=action,
                exposure=units * cpx / nav if nav else 0.0)


def step_fut(prev: dict | None, d: pd.Timestamp, fo: float, fc: float, prev_fc: float | None, tse_o: float, tse_c_prev: float | None,
             is_settle: bool, prev_was_settle: bool, check_day: bool, tse_c_prev_for_roll: float | None, rf: float = RF) -> dict[str, Any]:
    """F2 帳戶一天。權益全放現金計息，期貨損益併入現金；Nf＝期貨名目。
    結算隔日的連續序列有換月跳點，隔夜報酬改用加權指數現貨報酬（futures_lab5 同一個修正）。"""
    cost = traded = 0.0
    fill = np.nan
    action = ""
    if prev is None:
        return dict(cash=CAPITAL, nf=0.0, nav=CAPITAL, target=F2_X, cost=0.0, traded=0.0, fill=np.nan, action="", exposure=0.0)
    cash, nf = float(prev["cash"]) * (1 + rf / 252), float(prev["notional"])
    if prev_fc is not None:
        use_spot = prev_was_settle and tse_c_prev and tse_o and tse_o > 0
        r_on = (tse_o / tse_c_prev - 1) if use_spot else (fo / prev_fc - 1)
        cash += nf * r_on
        nf *= 1 + r_on
    if is_settle and tse_c_prev_for_roll:
        cash -= nf * ROLL_PTS / tse_c_prev_for_roll          # 結算前一日收盤轉倉：滑價 4 點 + 手續費 0.5 點
    e = cash
    do = (nf == 0.0 and F2_X > 0) or (check_day and e > 0 and abs(nf / e - F2_X) > F2_BAND)
    if do:
        tgt = F2_X * e
        dn = tgt - nf
        cost = abs(dn) * FUT_COST
        cash -= cost
        nf = tgt
        traded, fill = dn, fo
        action = f"開盤調整期貨名目至 {F2_X} 倍（{dn:+,.0f} 元）"
    r_id = fc / fo - 1
    cash += nf * r_id
    nf *= 1 + r_id
    return dict(cash=cash, nf=nf, nav=cash, target=F2_X, cost=cost, traded=traded, fill=fill, action=action, exposure=nf / cash if cash else 0.0)


def run(asof: pd.Timestamp | None = None, market: dict | None = None) -> dict[str, Any]:
    """推進帳本到資料湖最新的一天（或 asof）。重跑安全：已記錄的日子不會重算、不會被改寫。"""
    mk = market or load_market(asof)
    summary: dict[str, Any] = {"disclaimer": DISCLAIMER, "rows_added": 0}
    if not mk:
        summary["error"] = "price_daily 沒資料"
        return summary
    e0, e2, tse, fut = mk["etf"]["0050"], mk["etf"]["00631L"], mk["idx"]["TSE"], mk["idx"]["FUT"]
    cal = e0.index.intersection(e2.index).intersection(tse.index).intersection(fut.index).sort_values()
    cal = cal[cal <= asof] if asof is not None else cal
    summary["data_last"] = str(cal[-1].date()) if len(cal) else None
    if not len(cal) or cal[-1] < START:
        summary["status"] = f"資料還沒到起算日 {START.date()}（資料湖最新 {summary['data_last']}）"
        summary["signals"] = signals_snapshot(mk, cal[-1] if len(cal) else None, None)
        return summary
    led = read_ledger()
    sig_all = e2_signal(mk["idx"]["TSE"]["close"])
    settle = pd.Series(settle_days(tse.index), index=tse.index)
    todo = [d for d in cal if d >= START]
    last_done = {p: (led[led.plan == p].date.max() if not led.empty and (led.plan == p).any() else None) for p in PLANS}
    new_rows: list[dict] = []
    sat_rows: list[dict] = []
    hold_rows: list[dict] = []
    state: dict[str, dict | None] = {}
    for p in PLANS:
        sub = led[led.plan == p] if not led.empty else led
        state[p] = sub.iloc[-1].to_dict() if len(sub) else None
    for d in todo:
        i = cal.get_loc(d)
        prev_d = cal[i - 1] if i > 0 else None
        for p in PLANS:
            if last_done[p] is not None and d <= last_done[p]:
                continue
            row = _day_row(p, d, prev_d, state[p], mk, e0, e2, tse, fut, sig_all, settle, cal, state)
            if row is None:
                continue
            new_rows.append(row["row"])
            sat_rows += row.get("sat", [])
            hold_rows += row.get("hold", [])
            state[p] = row["row"]
            last_done[p] = d
    n = append_only(T_LEDGER, pd.DataFrame(new_rows), ["date", "plan"]) if new_rows else 0
    if sat_rows:
        append_only(T_SAT, pd.DataFrame(sat_rows), ["date", "rank"])
    if hold_rows:
        append_only(T_E2SAT, pd.DataFrame(hold_rows), ["date", "code"])
    summary["rows_added"] = n
    summary["signals"] = signals_snapshot(mk, cal[-1], state)
    summary["status"] = "ok"
    return summary


def _cum(nav: float) -> float:
    return nav / CAPITAL - 1


def _day_row(p, d, prev_d, prev, mk, e0, e2, tse, fut, sig_all, settle, cal, state):
    """算一個方案在 d 日的一列。只讀 d 日以前（含 d 日開高低收）的資料；d 日的訊號只用 d 日收盤以前。
    BENCH 必須先算（PLANS 的順序），其他方案才能帶同期基準報酬與門檻。"""
    if p == "BENCH":
        return {"row": _bench_row(prev, d, prev_d, mk, e0)}
    if p == "SAT":
        out = _sat_row(prev, d, prev_d, mk)
        _attach_bench(out["row"], state.get("BENCH"), p)
        return out
    if p == "E2SAT":
        out = _e2sat_row(prev, d, prev_d, mk, e2, sig_all)
        _attach_bench(out["row"], state.get("BENCH"), p)
        return out
    if p == "E2":
        s = sig_all.loc[d]
        tgt = E2_W_UP if int(s["state"]) == 1 else E2_W_DOWN
        r = step_etf(prev, d, float(e2.loc[d, "open"]), float(e2.loc[d, "close"]), float(e2.loc[prev_d, "close"]) if prev_d is not None else None, "00631L", tgt)
        sig = dict(tse_close=float(s["close"]), ma200=float(s["ma"]), upper=float(s["upper"]), lower=float(s["lower"]), state=int(s["state"]),
                   target_next=tgt, switch_tomorrow=bool(np.isnan(r["held"]) or abs(tgt - r["held"]) > 1e-9))
        row = _row(d, p, nav=r["nav"], cash=r["cash"], units=r["units"], exposure=r["exposure"], target=tgt, held=r["held"], action=r["action"],
                   fill_px=r["fill"], traded=r["traded"], cost=r["cost"], sig=json.dumps(sig, ensure_ascii=False), plan_cum=_cum(r["nav"]))
    else:  # F2
        is_settle = bool(settle.loc[d])
        # 結算隔日的連續序列有換月跳點 -> 隔夜報酬改用現貨；結算日當天扣轉倉成本（與 lev_lab 引擎相同）
        prev_was_settle = bool(prev_d is not None and settle.loc[prev_d])
        chk = bool(prev_d is not None and prev_d.month != d.month)
        r = step_fut(prev, d, float(fut.loc[d, "open"]), float(fut.loc[d, "close"]), float(fut.loc[prev_d, "close"]) if prev_d is not None else None,
                     float(tse.loc[d, "open"]), float(tse.loc[prev_d, "close"]) if prev_d is not None else None, is_settle, prev_was_settle, chk,
                     float(tse.loc[prev_d, "close"]) if prev_d is not None else None)
        info = futures_calendar(d)
        size = f2_sizing(r["nav"], float(fut.loc[d, "close"]))
        sig = dict(fut_close=float(fut.loc[d, "close"]), target_x=F2_X, contracts_big=round(size["big"], 3), contracts_micro=int(size["micro"]),
                   roll_tomorrow=info["roll_tomorrow"], next_settle=str(info["next_settle"].date()), next_check=str(info["next_check"].date()),
                   check_tomorrow=info["check_tomorrow"], margin_ratio=round(1.0 / (M_MAINT * r["exposure"]), 2) if r["exposure"] > 0 else None)
        row = _row(d, p, nav=r["nav"], cash=r["cash"], notional=r["nf"], exposure=r["exposure"], target=F2_X, action=r["action"], fill_px=r["fill"],
                   traded=r["traded"], cost=r["cost"], sig=json.dumps(sig, ensure_ascii=False), plan_cum=_cum(r["nav"]))
    _attach_bench(row, state.get("BENCH"), p)
    return {"row": row}


def _attach_bench(row: dict, bench_row: dict | None, plan: str) -> None:
    """帶上同期含息 0050 累積報酬與門檻（E2＝1.5 倍、F2＝1.0 倍）。"""
    if bench_row is not None and str(pd.Timestamp(bench_row.get("date")).date()) == row["date"]:
        row["bench_cum"] = float(bench_row["bench_cum"])
        row["thresh_cum"] = MULT[plan] * float(bench_row["bench_cum"])


def _bench_row(prev, d, prev_d, mk, e0):
    opx, cpx = float(e0.loc[d, "open"]), float(e0.loc[d, "close"])
    cost = traded = 0.0
    fill = np.nan
    action = ""
    if prev is None:
        cash, units = CAPITAL, 0.0
    else:
        cash, units = float(prev["cash"]) * (1 + RF / 252), float(prev["units"])
        units *= _split_mult(float(e0.loc[prev_d, "close"]), opx)
        if units == 0.0:                                         # 第一個成交日：開盤全部買進
            rate = FEE + SLIP["0050"]
            amt = cash / (1 + rate)
            cost = amt * rate
            units, cash, traded, fill = amt / opx, 0.0, amt, opx
            action = f"開盤買進 0050 {amt:,.0f} 元"
    dv = mk["div"]
    if units > 0 and d in dv.index:                              # 除息：股息於收盤價再投入（含息報酬口徑）
        units += units * float(dv.loc[d]) / cpx
    nav = cash + units * cpx
    return _row(d, "BENCH", nav=nav, cash=cash, units=units, exposure=units * cpx / nav if nav else 0.0, target=1.0, action=action, fill_px=fill,
                traded=traded, cost=cost, plan_cum=_cum(nav), bench_cum=_cum(nav), thresh_cum=_cum(nav))


def tomorrow_is_rebalance_day(d: pd.Timestamp) -> bool:
    """明天是不是『每月第一個 >= 11 日的交易日』（營收法定公布日是次月 10 日）。休市日以週一到週五近似。"""
    nxt = next_weekday(d)
    return bool(d.month == nxt.month and d.day < 11 <= nxt.day)


def _sat_row(prev, d, prev_d, mk):
    """衛星部位單獨紀錄（E2SAT 內占 20%）。每天等權持有清單，日報酬分隔夜／盤中兩段（與 lev_lab 衛星同口徑），
    換股日開盤成交；起算日收盤先決定第一份清單，次一交易日開盤買進。價格沒還原除息、|日報酬|>10.5% 視為公司行動設 0。"""
    so, sc, st = mk["stk_open"], mk["stk_close"], mk["stk_turn"]
    held: dict[str, float] = {}
    nav = CAPITAL
    cost = 0.0
    action = ""
    if prev is not None:
        ex = json.loads(prev["extra"])
        held, pend = ex.get("holdings") or {}, ex.get("pending")
        nav = float(prev["nav"])
        nav *= 1 + sum(w * _clip(so.loc[d, c] / sc.loc[prev_d, c] - 1) for c, w in held.items() if c in so.columns)
        if pend:
            diff = {c: pend.get(c, 0.0) - held.get(c, 0.0) for c in set(held) | set(pend)}
            buy = sum(max(v, 0) for v in diff.values())
            sell = sum(max(-v, 0) for v in diff.values())
            cost = nav * (buy * SAT_BUY + sell * SAT_SELL)
            nav -= cost
            held = pend
            action = f"開盤換股：買 {buy:.0%}／賣 {sell:.0%}（衛星部位）"
        nav *= 1 + sum(w * _clip(sc.loc[d, c] / so.loc[d, c] - 1) for c, w in held.items() if c in sc.columns)
    pending, sat_rows = None, []
    if prev is None or not held or tomorrow_is_rebalance_day(d):
        picks = pick_satellite(sc, st, rev_ratio_asof(mk["rev"], d), d)
        if len(picks):
            pending = {r.code: 1.0 / len(picks) for r in picks.itertuples()}
            sat_rows = [dict(date=d.strftime("%Y-%m-%d"), rank=int(r.rank), code=r.code, rev_ratio=float(r.rev_ratio), near_high=float(r.near_high),
                             weight_pct=E2SAT_W_SAT, disclaimer=DISCLAIMER) for r in picks.itertuples()]
    row = _row(d, "SAT", nav=nav, cash=0.0, exposure=sum(held.values()) if held else 0.0, target=E2SAT_W_SAT, action=action, cost=cost,
               sig=json.dumps({"picks": list(pending) if pending else [], "資金權重": "20%（E2SAT 內的衛星部位；本列為衛星單獨紀錄）"}, ensure_ascii=False),
               extra=json.dumps({"holdings": held, "pending": pending}, ensure_ascii=False), plan_cum=_cum(nav))
    return {"row": row, "sat": sat_rows}


def _clip(x: float) -> float:
    """|日報酬| > 10.5% 視為除權息／減資等公司行動（價格沒還原）設 0；缺值設 0。"""
    if x is None or not np.isfinite(x) or abs(x) > 0.105:
        return 0.0
    return float(x)


def is_year_rebalance_day(d: pd.Timestamp, prev_d: pd.Timestamp | None) -> bool:
    """E2SAT 年度再平衡日：資料湖裡每年第一個交易日（上一個交易日跨年）。起算日不算（那天才剛配 80/20）。"""
    return prev_d is not None and d.year != prev_d.year


def _e2sat_row(prev, d, prev_d, mk, e2, sig_all):
    """E2SAT：80% E2 + 20% 衛星，兩個子帳戶各自記帳（extra 存衛星子帳戶），每年第一個交易日開盤調回 80/20。
    順序與其他方案一致：d 日開盤執行『前一日收盤決定』的事（E2 目標權重、衛星換股、年度再平衡），d 日收盤估值，
    再用 d 日收盤以前的資料決定明天要做什麼。再平衡所需的成本（正二 手續費+稅+滑價、個股 手續費+稅+證交稅）全部扣。"""
    sc, so, st = mk["stk_close"], mk["stk_open"], mk["stk_turn"]
    s = sig_all.loc[d]
    tgt = E2_W_UP if int(s["state"]) == 1 else E2_W_DOWN
    opx, cpx = float(e2.loc[d, "open"]), float(e2.loc[d, "close"])
    sat_cost = 0.0
    action_parts: list[str] = []
    if prev is None:
        sat_nav, held, pend = CAPITAL * E2SAT_W_SAT, {}, None
        e2_adj = 0.0
        r = step_etf(None, d, opx, cpx, None, "00631L", tgt)
        r["cash"] = CAPITAL * E2SAT_W_E2                 # 起算日：先把本金切 80/20，E2 只拿 80%
        r["nav"] = r["cash"]
    else:
        ex = json.loads(prev["extra"])
        held, pend = ex.get("holdings") or {}, ex.get("pending")
        sat_nav = float(ex["sat_nav"])
        # 衛星子帳戶：隔夜到開盤的報酬（沒持股就只計現金利息）
        if held:
            sat_nav *= 1 + sum(w * _clip(so.loc[d, c] / sc.loc[prev_d, c] - 1) for c, w in held.items() if c in so.columns)
        else:
            sat_nav *= 1 + RF / 252
        e2_adj = 0.0
        if is_year_rebalance_day(d, prev_d):
            # 開盤時兩邊的市值（E2 用開盤價估，與 step_etf 的開盤估值同口徑）
            mult = _split_mult(float(e2.loc[prev_d, "close"]), opx)
            e2_open = float(prev["cash"]) * (1 + RF / 252) + float(prev["units"]) * mult * opx
            total = e2_open + sat_nav
            diff = total * E2SAT_W_SAT - sat_nav          # >0：衛星要加碼，錢從 E2 部位出
            w_before = sat_nav / total
            if diff > 0:
                fee = diff * SAT_BUY if held else 0.0
                sat_nav += diff - fee
                sat_cost += fee
                e2_adj = -diff
            elif diff < 0:
                fee = (-diff) * SAT_SELL if held else 0.0
                sat_nav += diff                           # 賣出 |diff|，成本從賣出款扣
                sat_cost += fee
                e2_adj = -diff - fee
            action_parts.append(f"年度再平衡：衛星 {w_before:.1%}→目標 {E2SAT_W_SAT:.0%}（劃撥 {diff:+,.0f} 元）")
        if pend:
            diffw = {c: pend.get(c, 0.0) - held.get(c, 0.0) for c in set(held) | set(pend)}
            buy = sum(max(v, 0) for v in diffw.values())
            sell = sum(max(-v, 0) for v in diffw.values())
            fee = sat_nav * (buy * SAT_BUY + sell * SAT_SELL)
            sat_nav -= fee
            sat_cost += fee
            held = pend
            action_parts.append(f"衛星開盤換股：買 {buy:.0%}／賣 {sell:.0%}")
        if held:
            sat_nav *= 1 + sum(w * _clip(sc.loc[d, c] / so.loc[d, c] - 1) for c, w in held.items() if c in sc.columns)
        e2_prev = dict(cash=prev["cash"], units=prev["units"], held=prev["held"], target=prev["target"], nav=prev["nav"])
        r = step_etf(e2_prev, d, opx, cpx, float(e2.loc[prev_d, "close"]), "00631L", tgt, cash_adj=e2_adj)
        if r["action"]:
            action_parts.append("E2 " + r["action"])
    nav = r["nav"] + sat_nav
    new_pend = None
    if prev is None or not held or tomorrow_is_rebalance_day(d):
        picks = pick_satellite(sc, st, rev_ratio_asof(mk["rev"], d), d)
        if len(picks):
            new_pend = {x.code: 1.0 / len(picks) for x in picks.itertuples()}
    eq = (r["units"] * cpx + sat_nav * sum(held.values())) / nav if nav else 0.0
    sig = dict(tse_close=float(s["close"]), ma200=float(s["ma"]), state=int(s["state"]), e2_target_next=tgt,
               e2_value=r["nav"], sat_value=sat_nav, sat_weight=sat_nav / nav if nav else 0.0,
               sat_picks_next=list(new_pend) if new_pend else [], 資金權重="80% E2 + 20% 衛星，每年第一個交易日再平衡")
    row = _row(d, "E2SAT", nav=nav, cash=r["cash"], units=r["units"], exposure=eq, target=tgt, held=r["held"], action="；".join(action_parts),
               fill_px=r["fill"], traded=r["traded"], cost=r["cost"] + sat_cost, sig=json.dumps(sig, ensure_ascii=False),
               extra=json.dumps({"holdings": held, "pending": new_pend, "sat_nav": sat_nav}, ensure_ascii=False), plan_cum=_cum(nav))
    hold = [dict(date=d.strftime("%Y-%m-%d"), code="00631L", sleeve="E2", weight=r["units"] * cpx / nav if nav else 0.0, disclaimer=DISCLAIMER)]
    hold += [dict(date=d.strftime("%Y-%m-%d"), code=c, sleeve="SAT", weight=w * sat_nav / nav if nav else 0.0, disclaimer=DISCLAIMER) for c, w in held.items()]
    hold.append(dict(date=d.strftime("%Y-%m-%d"), code="CASH", sleeve="E2", weight=r["cash"] / nav if nav else 0.0, disclaimer=DISCLAIMER))
    return {"row": row, "hold": hold}


def signals_snapshot(mk: dict, asof: pd.Timestamp | None, state: dict | None) -> dict[str, Any]:
    """給人看的最新訊號（也寫進 data/_state/live_signals.json）。state 為空時只算 E2 與 F2 日曆。"""
    out: dict[str, Any] = {"disclaimer": DISCLAIMER}
    if asof is None or "idx" not in mk:
        return out
    s = e2_signal(mk["idx"]["TSE"]["close"].loc[:asof]).iloc[-1]
    out["asof"] = str(asof.date())
    out["E2"] = dict(tse_close=float(s["close"]), ma200=float(s["ma"]), upper=float(s["upper"]), lower=float(s["lower"]), state="線上（持 100% 正二）" if s["state"] == 1 else "線下（30% 正二 + 70% 現金）")
    out["F2"] = {k: (str(v.date()) if isinstance(v, pd.Timestamp) else v) for k, v in futures_calendar(asof).items()}
    if state and state.get("E2SAT"):
        ex = json.loads(state["E2SAT"]["extra"])
        nxt = pd.Timestamp(asof.year + 1, 1, 1)
        while nxt.weekday() >= 5:
            nxt += pd.Timedelta(days=1)
        out["E2SAT"] = dict(持有衛星=sorted((ex.get("holdings") or {}).keys()), 明日換股清單=sorted((ex.get("pending") or {}).keys()),
                            下次年度再平衡約=str(nxt.date()), 目標權重="80% E2 + 20% 衛星")
    if state:
        for p in PLANS:
            if state.get(p):
                out[p + "_last"] = {k: state[p][k] for k in ("date", "nav", "plan_cum", "action") if k in state[p]}
    return out


def main() -> int:
    """進入點：失敗只記錄、不拋出（daily.yml 這一步也設了 continue-on-error，雙重保險不影響其他步驟）。"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        res = run()
    except Exception as exc:                                            # noqa: BLE001
        log.exception("live_signals 失敗")
        res = {"disclaimer": DISCLAIMER, "status": "error", "error": str(exc)[:300]}
    res["generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    try:
        config.STATE.mkdir(parents=True, exist_ok=True)
        (config.STATE / "live_signals.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    except Exception:                                                   # noqa: BLE001
        log.exception("寫 live_signals.json 失敗")
    log.info("live_signals：%s", {k: v for k, v in res.items() if k != "signals"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
