"""恐慌指數：臺指選擇權隱含波動率指數（本站自算，非期交所官方臺指VIX）。

為什麼自己算：期交所官方「臺指選擇權波動率指數」網站條款要事前書面同意、開放資料平台沒有、
FinMind 的 TaiwanOptionVix 要付費等級；但 TXO 逐履約價的每日行情（FinMind TaiwanOptionDaily，
與期交所 OpenAPI DailyMarketReportOpt 同一份開放資料）可以合法取得，公式又是公開的
（CBOE VIX 白皮書，期交所臺指VIX也是照這套）。名稱刻意不用「VIX」（Cboe 商標）。

公式（CBOE VIX 白皮書，逐項）：
  每一個到期月份 j（近月、次近月）：
    T_j  ＝ 剩餘時間（年）＝（到期日 08:45 − 資料日 13:45）的分鐘數 ÷ 525,600
    F_j  ＝ K* ＋ e^{R·T}·(C(K*) − P(K*))，K* ＝ 買權賣權價差絕對值最小的履約價
    K0   ＝ ≤ F 的最大履約價
    Q(K) ＝ K < K0 用賣權價、K > K0 用買權價、K0 用兩者平均（只取價外）
    由 K0 往外走，連續兩個履約價價格為 0／缺 → 停（CBOE「兩個零 bid 就停」的對應做法）
    ΔK_i ＝ (K_{i+1} − K_{i−1}) / 2，兩端用單邊差
    σ²_j ＝ (2/T)·Σ ΔK/K²·e^{RT}·Q(K) − (1/T)·(F/K0 − 1)²
  30 天期插補（N 為分鐘）：
    σ²_30 ＝ [T1σ1²·(N2−N30)/(N2−N1) ＋ T2σ2²·(N30−N1)/(N2−N1)] × N365/N30
    指數 ＝ 100 × √σ²_30

本站的取捨（寫清楚，跟官方值對不上時從這裡找原因）：
  · 價格用「結算價」（settlement_price）：期交所每天對每一個履約價都算結算價，沒成交的也有；
    收盤價（close）只有有成交的履約價才有，深價外常常是空的，用它會讓 Σ 少掉尾巴、指數偏低。
    結算價 ≤ 0 或缺 → 退用收盤價；都沒有 → 當作 0（觸發「連續兩個 0 就停」）。
    官方用的是買賣報價中價，我們拿不到，所以這是跟官方最主要的差距來源。
  · 只用「月契約」（contract_date 6 碼 YYYYMM）：週選（W／F 結尾）到期日規則多、筆數少，
    混進來會讓近月在每週跳一次；官方也是用月契約。
  · 到期日＝當月第三個星期三（期交所 TXO 月契約最後交易日）。遇到國定假日順延的少數月份
    會差 1～2 天，影響 T 的估計，但只在那幾天有感。
  · 近月剩不到 config.IVX_MIN_DAYS（3）個日曆天（≈最後 2 個交易日）→ 改用次近月＋第三近月（期交所臺指VIX 的換月規則）；
    這時 30 天在兩個期限之外（外插），公式照用（權重會 >1／<0，CBOE 舊版同樣處理）。
  · 利率 config.IVX_RATE 固定 1.5%（理由寫在 config）。
  · 一邊（買權或賣權）價外履約價不到 3 個 → 該月份不算（σ² 給 NaN），整天就不出值；不硬湊。
"""
from __future__ import annotations

import calendar
import logging
import math
import re
from datetime import date, datetime

import numpy as np
import pandas as pd

from .. import config

log = logging.getLogger(__name__)

MIN_YEAR = 525_600.0          # 一年的分鐘數（365 天，CBOE 口徑）
CP = {"call": "C", "put": "P", "c": "C", "p": "P", "買權": "C", "賣權": "P"}
AFTER = {"after_market", "盤後", "1", "afterhours"}
_MONTHLY = re.compile(r"^\d{6}$")


def third_wednesday(ym: str) -> date:
    """'202611' → 2026-11-18（當月第三個星期三＝TXO 月契約最後交易日）。"""
    y, m = int(ym[:4]), int(ym[4:6])
    first = date(y, m, 1)
    off = (calendar.WEDNESDAY - first.weekday()) % 7
    return date(y, m, 1 + off + 14)


def minutes_to_expiry(d: date, exp: date) -> float:
    """資料日 13:45（收盤）到到期日 08:45（結算價以開盤時段決定）的分鐘數。"""
    return ((exp - d).days * 1440.0) - 300.0


def normalize(rows) -> pd.DataFrame:
    """FinMind TaiwanOptionDaily 逐契約 → (date, ym, K, cp, price)。

    只留一般交易時段、月契約；價格先結算價、沒有才收盤價。認不得欄位回空（不猜）。"""
    if rows is None:
        return pd.DataFrame()
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    need = {"date", "contract_date", "strike_price", "call_put"}
    if df.empty or not need <= set(df.columns):
        if not df.empty:
            log.warning("opt_ivx 欄位認不得（缺 %s）", sorted(need - set(df.columns)))
        return pd.DataFrame()
    df = df.copy()
    if "trading_session" in df.columns:
        df = df[~df["trading_session"].astype(str).str.strip().str.lower().isin(AFTER)]
    df["ym"] = df["contract_date"].astype(str).str.strip()
    df = df[df["ym"].str.match(_MONTHLY)]
    df["cp"] = df["call_put"].astype(str).str.strip().str.lower().map(CP)
    df["K"] = pd.to_numeric(df["strike_price"], errors="coerce")
    st = pd.to_numeric(df["settlement_price"], errors="coerce") if "settlement_price" in df.columns else pd.Series(np.nan, index=df.index)
    cl = pd.to_numeric(df["close"], errors="coerce") if "close" in df.columns else pd.Series(np.nan, index=df.index)
    df["price"] = st.where(st > 0, cl.where(cl > 0, 0.0)).fillna(0.0)
    df["date"] = df["date"].astype(str).str[:10]
    df = df.dropna(subset=["cp", "K"])
    df = df[df["K"] > 0]
    # 同一天同一契約同一履約價重複（重抓、兩個來源）→ 取價格較大那筆（0 多半是缺值）
    return (df.sort_values("price").drop_duplicates(["date", "ym", "K", "cp"], keep="last")
              [["date", "ym", "K", "cp", "price"]].reset_index(drop=True))


def term_variance(chain: pd.DataFrame, T: float, R: float) -> dict | None:
    """單一到期月份的 σ²（CBOE 公式）。chain：該月份的 (K, cp, price)。資料不夠回 None。"""
    if T <= 0 or chain is None or chain.empty:
        return None
    pv = chain.pivot_table(index="K", columns="cp", values="price", aggfunc="max").sort_index()
    for c in ("C", "P"):
        if c not in pv.columns:
            return None
    pv = pv.fillna(0.0)
    both = pv[(pv["C"] > 0) & (pv["P"] > 0)]
    if both.empty:
        return None
    diff = (both["C"] - both["P"]).abs()
    ks = float(diff.idxmin())
    er = math.exp(R * T)
    F = ks + er * float(both.loc[ks, "C"] - both.loc[ks, "P"])
    strikes = pv.index.to_numpy(dtype=float)
    below = strikes[strikes <= F]
    if not len(below):
        return None
    K0 = float(below.max())

    picked: list[tuple[float, float]] = []      # (K, Q)
    # 價外賣權：K0 往下
    zeros = 0; puts = []
    for K in sorted([k for k in strikes if k < K0], reverse=True):
        p = float(pv.loc[K, "P"])
        if p <= 0:
            zeros += 1
            if zeros >= 2:
                break
            continue
        zeros = 0; puts.append((K, p))
    zeros = 0; calls = []
    for K in sorted([k for k in strikes if k > K0]):
        c = float(pv.loc[K, "C"])
        if c <= 0:
            zeros += 1
            if zeros >= 2:
                break
            continue
        zeros = 0; calls.append((K, c))
    if len(puts) < 3 or len(calls) < 3:
        return None
    c0, p0 = float(pv.loc[K0, "C"]), float(pv.loc[K0, "P"])
    q0 = (c0 + p0) / 2 if c0 > 0 and p0 > 0 else max(c0, p0)
    picked = sorted(puts + [(K0, q0)] + calls)
    Ks = np.array([k for k, _ in picked]); Qs = np.array([q for _, q in picked])
    dK = np.empty_like(Ks)
    dK[1:-1] = (Ks[2:] - Ks[:-2]) / 2
    dK[0] = Ks[1] - Ks[0]
    dK[-1] = Ks[-1] - Ks[-2]
    s = float(np.sum(dK / Ks ** 2 * er * Qs))
    var = (2.0 / T) * s - (1.0 / T) * (F / K0 - 1.0) ** 2
    return {"var": var, "F": F, "K0": K0, "n": int(len(Ks))}


def index_for_day(day_chain: pd.DataFrame, d: str, R: float | None = None,
                  target_days: int | None = None, min_days: int | None = None) -> dict | None:
    """單一天：挑近月／次近月 → 兩個 σ² → 30 天期插補。資料不夠回 None。"""
    R = config.IVX_RATE if R is None else R
    target_days = target_days or config.IVX_TARGET_DAYS
    min_days = config.IVX_MIN_DAYS if min_days is None else min_days
    if day_chain is None or day_chain.empty:
        return None
    dd = date.fromisoformat(d)
    terms = []
    for ym in sorted(day_chain["ym"].unique()):
        exp = third_wednesday(ym)
        N = minutes_to_expiry(dd, exp)
        if N <= 0:
            continue
        terms.append((ym, exp, N))
    terms = [t for t in terms if (t[1] - dd).days >= min_days]
    out = None
    # 近月（或它算不出來時）往後找下一組相鄰兩個月：一個月份資料壞掉不讓整天開天窗，但每一次都只用相鄰兩個月
    for i in range(len(terms) - 1):
        (y1, e1, N1), (y2, e2, N2) = terms[i], terms[i + 1]
        t1 = term_variance(day_chain[day_chain["ym"] == y1], N1 / MIN_YEAR, R)
        t2 = term_variance(day_chain[day_chain["ym"] == y2], N2 / MIN_YEAR, R)
        if not t1 or not t2:
            continue
        N30 = target_days * 1440.0
        T1, T2 = N1 / MIN_YEAR, N2 / MIN_YEAR
        v = (T1 * t1["var"] * (N2 - N30) / (N2 - N1) + T2 * t2["var"] * (N30 - N1) / (N2 - N1)) * MIN_YEAR / N30
        if not (v > 0) or not math.isfinite(v):
            continue
        out = {"date": d, "ivx": round(100 * math.sqrt(v), 4),
               "near_ym": y1, "near_exp": e1.isoformat(), "near_days": round(N1 / 1440, 3), "near_var": t1["var"],
               "near_fwd": round(t1["F"], 2), "near_k0": t1["K0"], "near_n": t1["n"],
               "next_ym": y2, "next_exp": e2.isoformat(), "next_days": round(N2 / 1440, 3), "next_var": t2["var"],
               "next_fwd": round(t2["F"], 2), "next_k0": t2["K0"], "next_n": t2["n"],
               "rate": R, "price_src": "settlement"}
        break
    return out


def compute(rows) -> pd.DataFrame:
    """逐契約原始資料（可多天）→ 每天一列 opt_ivx。算不出來的那天不出列（不寫 NaN 進只增不改的湖）。"""
    ch = normalize(rows)
    if ch.empty:
        return pd.DataFrame()
    out = []
    for d, g in ch.groupby("date"):
        r = index_for_day(g, d)
        if r:
            out.append(r)
        else:
            log.info("opt_ivx %s 算不出來（月契約價外履約價不足或缺買／賣權）", d)
    return pd.DataFrame(out)


# ------------------------------------------------------------------ 前端 JSON
def _state(pct: float | None) -> str | None:
    if pct is None:
        return None
    if pct >= config.IVX_PCT_PANIC:
        return "panic"
    if pct >= config.IVX_PCT_CALM:
        return "alert"
    return "calm"


def percentile_series(s: pd.Series, window: int = 750) -> tuple[pd.Series, pd.Series]:
    """每一天：當天值在「到當天為止」最近 window 天裡的分位（中位秩：小於的比例＋一半等於的比例）與樣本數。

    只用過去＋當天，不偷看未來 —— 畫在圖上的歷史狀態，就是那一天當下真的算得出來的狀態。"""
    v = s.to_numpy(dtype=float)
    pct = np.full(len(v), np.nan); n = np.zeros(len(v), dtype=int)
    for i in range(len(v)):
        h = v[max(0, i - window + 1): i + 1]
        h = h[np.isfinite(h)]
        n[i] = len(h)
        if len(h) and np.isfinite(v[i]):
            # 中位秩（< 的比例＋一半的 = 的比例）：同值很多時不會一律被算成最高分位
            pct[i] = float(np.mean(h < v[i]) + 0.5 * np.mean(h == v[i]))
    return pd.Series(pct, index=s.index), pd.Series(n, index=s.index)


def build_json(ivx: pd.DataFrame, intl: pd.DataFrame | None, spark: int = 60, ohlc: pd.DataFrame | None = None) -> dict:
    """opt_ivx ＋ intl_daily 的 ^VIX → site/data/fear.json。

    tw.state 只在歷史 ≥ config.IVX_MIN_HIST 天時給；樣本數 n_hist 一律帶出去讓前端顯示。"""
    out: dict = {"tw": None, "us": None,
                 "method": {"rate": config.IVX_RATE, "target_days": config.IVX_TARGET_DAYS, "min_days": config.IVX_MIN_DAYS,
                            "calm": config.IVX_PCT_CALM, "panic": config.IVX_PCT_PANIC, "min_hist": config.IVX_MIN_HIST,
                            "window": 750, "price": "結算價（沒有才收盤價）", "contracts": "月契約近月＋次近月"}}
    if ivx is not None and not ivx.empty and "ivx" in ivx.columns:
        t = ivx.dropna(subset=["ivx"]).copy()
        t["date"] = t["date"].astype(str).str[:10]
        t = t.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
        if len(t):
            pct, n = percentile_series(t["ivx"].astype(float))
            last = t.iloc[-1]; i = len(t) - 1
            nh = int(n.iloc[i]); p = float(pct.iloc[i]) if np.isfinite(pct.iloc[i]) else None
            hist = t["ivx"].astype(float).iloc[max(0, i - 749): i + 1]
            out["tw"] = {
                "name": "恐慌指數（台指選擇權隱含波動率・本站自算）",
                "date": last["date"], "value": round(float(last["ivx"]), 2),
                "chg": round(float(last["ivx"] - t["ivx"].iloc[-2]), 2) if len(t) > 1 else None,
                "prev_date": t["date"].iloc[-2] if len(t) > 1 else None,
                "pct": round(p, 4) if p is not None else None, "n_hist": nh,
                "state": _state(p) if nh >= config.IVX_MIN_HIST else None,
                "q50": round(float(hist.quantile(config.IVX_PCT_CALM)), 2) if nh else None,
                "q85": round(float(hist.quantile(config.IVX_PCT_PANIC)), 2) if nh else None,
                "near": {"exp": last.get("near_exp"), "days": _num(last.get("near_days"))},
                "next": {"exp": last.get("next_exp"), "days": _num(last.get("next_days"))},
                "series": [[d, round(float(v), 2)] for d, v in zip(t["date"], t["ivx"])],
                "spark": [[d, round(float(v), 2)] for d, v in zip(t["date"].iloc[-spark:], t["ivx"].iloc[-spark:])],
                "pct_series": [[d, (round(float(x), 3) if np.isfinite(x) else None)] for d, x in zip(t["date"], pct)],
            }
    if intl is not None and not intl.empty and {"symbol", "date", "close"} <= set(intl.columns):
        u = intl[intl["symbol"] == "^VIX"].dropna(subset=["close"]).copy()
        u["date"] = u["date"].astype(str).str[:10]
        u = u.sort_values("date").drop_duplicates("date", keep="last")
        if len(u):
            first = out["tw"]["series"][0][0] if out["tw"] else u["date"].iloc[max(0, len(u) - 750)]
            uu = u[u["date"] >= first]
            out["us"] = {"name": "美股恐慌指數 VIX（芝加哥期權交易所）",
                         "date": u["date"].iloc[-1], "value": round(float(u["close"].iloc[-1]), 2),
                         "chg": round(float(u["close"].iloc[-1] - u["close"].iloc[-2]), 2) if len(u) > 1 else None,
                         "series": [[d, round(float(v), 2)] for d, v in zip(uu["date"], uu["close"])],
                         "spark": [[d, round(float(v), 2)] for d, v in zip(u["date"].iloc[-spark:], u["close"].iloc[-spark:])]}
    # 走勢圖上格的對照指數（Andy 11-06：「台股VIX 就是加權 櫃買；美股 就是 那斯達克 費城 S&P 比較」）：只輸出日收盤，
    # 前端以「期間起點＝100」畫相對走勢。台股取資料湖 index_ohlc 的 TSE（加權）／OTC（櫃買）；美股取 intl_daily 的 ^IXIC／^SOX／^GSPC
    # （美東交易日，日期照原樣不挪；前端用同一條 X 軸、沒開盤的那天留空）。起點＝恐慌指數序列的第一天。
    first = out["tw"]["series"][0][0] if out["tw"] else None
    def _cl(df, sym, col_sym, name):
        if df is None or df.empty or not {col_sym, "date", "close"} <= set(df.columns):
            return None
        u = df[df[col_sym] == sym].dropna(subset=["close"]).copy()
        u["date"] = u["date"].astype(str).str[:10]
        u = u.sort_values("date").drop_duplicates("date", keep="last")
        if first:
            u = u[u["date"] >= first]
        if not len(u):
            return None
        return {"name": name, "date": u["date"].iloc[-1], "series": [[d, round(float(v), 2)] for d, v in zip(u["date"], u["close"])]}
    tw_idx = {k: v for k, v in (("TSE", _cl(ohlc, "TSE", "symbol", "加權指數")), ("OTC", _cl(ohlc, "OTC", "symbol", "櫃買指數"))) if v}
    us_idx = {k: v for k, v in (("IXIC", _cl(intl, "^IXIC", "symbol", "那斯達克")), ("SOX", _cl(intl, "^SOX", "symbol", "費城半導體")),
                                ("GSPC", _cl(intl, "^GSPC", "symbol", "標普 500"))) if v}
    out["idx"] = {"tw": tw_idx, "us": us_idx}
    return out


def _num(v):
    try:
        f = float(v)
        return round(f, 2) if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":     # 只重算這一張卡：python -m pipeline.compute.ivx
    import json
    from ..util import store
    logging.basicConfig(level=logging.INFO)
    j = build_json(store.read("opt_ivx"), store.read("intl_daily", years=[datetime.now().year - 3, datetime.now().year - 2,
                                                                         datetime.now().year - 1, datetime.now().year]),
                   ohlc=store.read("index_ohlc"))
    p = config.ROOT / "site" / "data" / "fear.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(j, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print("寫入", p, "台指", (j["tw"] or {}).get("value"), (j["tw"] or {}).get("date"), "美股", (j["us"] or {}).get("value"), (j["us"] or {}).get("date"))
