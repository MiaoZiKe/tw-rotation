"""M2 基本面：TTM EPS、自算本益比、分族群估值分位、月營收動能。

金融專家定下的規則，寫在這裡當作程式的契約：
1. PE 一律自算 = 收盤 / 近四季 EPS 合計。單季 ×4 在半導體這種季節性產業是錯的。
2. 虧損股（TTM EPS ≤ 0）的 PE 記 NaN —— 不是負數、不是 0、不排序。
3. 族群統計量用中位數，不用平均。PE 落在 [3, 200] 之外視為離群不納入統計。
4. 分位是「同族群」內的分位。樣本 < 5 退回法定產業別；< 3 一律留白，且永遠顯示 n。
5. 不同族群看不同的估值口徑：金融看 PB + ROE、未獲利生技看 PS、其餘 PE。
   由 groups.yaml 的 valuation_metric 決定，不在程式裡硬編碼。
6. 絕不跨族群比 PE 絕對值。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..groups import loader

log = logging.getLogger(__name__)

PE_MIN, PE_MAX = 3.0, 200.0
MIN_GROUP_N = 5          # 族群樣本低於此退回產業別
MIN_ANY_N = 3            # 再低就留白


# ------------------------------------------------------------------ 財報

def ttm(financial_q: pd.DataFrame) -> pd.DataFrame:
    """每檔股票的近四季合計（EPS、淨利、營收）與最新一季毛利率。

    要求四季連續；缺任何一季就不給 TTM（給 NaN），而不是拿三季湊。
    """
    if financial_q is None or financial_q.empty:
        return pd.DataFrame()
    df = financial_q.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce")
    df = df.dropna(subset=["year", "quarter", "code"])
    df["qidx"] = df["year"].astype(int) * 4 + df["quarter"].astype(int)
    df = df.sort_values(["code", "qidx"]).drop_duplicates(["code", "qidx"], keep="last")

    rows = []
    for code, g in df.groupby("code"):
        g = g.tail(4)
        if len(g) < 4 or (g["qidx"].max() - g["qidx"].min()) != 3:
            complete = False
        else:
            complete = True
        last = g.iloc[-1]
        eps = pd.to_numeric(g["eps"], errors="coerce")
        rev = pd.to_numeric(g["revenue"], errors="coerce")
        ni = pd.to_numeric(g["net_income"], errors="coerce")
        gp = pd.to_numeric(last.get("gross_profit"), errors="coerce")
        rv = pd.to_numeric(last.get("revenue"), errors="coerce")
        rows.append({
            "code": code,
            "ttm_eps": float(eps.sum()) if complete and eps.notna().all() else np.nan,
            "ttm_revenue": float(rev.sum()) if complete and rev.notna().all() else np.nan,
            "ttm_net_income": float(ni.sum()) if complete and ni.notna().all() else np.nan,
            "latest_eps_q": float(eps.iloc[-1]) if pd.notna(eps.iloc[-1]) else np.nan,
            "gross_margin": float(gp / rv * 100) if pd.notna(gp) and pd.notna(rv) and rv else np.nan,
            "latest_period": f"{int(last['year'])}Q{int(last['quarter'])}",
            "announce_date": last.get("announce_date"),
            "quarters": int(len(g)),
            "ttm_complete": complete,
        })
    return pd.DataFrame(rows)


def latest_balance(balance_q: pd.DataFrame) -> pd.DataFrame:
    if balance_q is None or balance_q.empty:
        return pd.DataFrame()
    df = balance_q.copy()
    df["qidx"] = (pd.to_numeric(df["year"], errors="coerce") * 4 +
                  pd.to_numeric(df["quarter"], errors="coerce"))
    df = df.dropna(subset=["qidx"]).sort_values(["code", "qidx"])
    last = df.groupby("code").tail(1)
    return last[["code", "shares", "equity_parent", "bps", "total_assets"]].reset_index(drop=True)


# ------------------------------------------------------------------ 估值

def valuation(price_latest: pd.DataFrame, ttm_df: pd.DataFrame,
              balance: pd.DataFrame | None = None) -> pd.DataFrame:
    """每檔股票的 PE / PB / PS / ROE / 市值。價格用傳進來那一天的收盤。"""
    if price_latest is None or price_latest.empty:
        return pd.DataFrame()
    v = price_latest[["code", "close"]].drop_duplicates("code").copy()
    v["close"] = pd.to_numeric(v["close"], errors="coerce")
    if ttm_df is not None and not ttm_df.empty:
        v = v.merge(ttm_df, on="code", how="left")
    else:
        for c in ("ttm_eps", "ttm_revenue", "ttm_net_income", "gross_margin", "latest_period"):
            v[c] = np.nan
    if balance is not None and not balance.empty:
        v = v.merge(balance, on="code", how="left")
    else:
        for c in ("shares", "equity_parent", "bps", "total_assets"):
            v[c] = np.nan

    eps = pd.to_numeric(v["ttm_eps"], errors="coerce")
    v["pe"] = np.where(eps > 0, v["close"] / eps, np.nan)           # 規則 2
    v["pb"] = np.where(pd.to_numeric(v["bps"], errors="coerce") > 0,
                       v["close"] / pd.to_numeric(v["bps"], errors="coerce"), np.nan)
    v["market_cap"] = v["close"] * pd.to_numeric(v["shares"], errors="coerce")
    rev = pd.to_numeric(v["ttm_revenue"], errors="coerce")
    v["ps"] = np.where(rev > 0, v["market_cap"] / rev, np.nan)
    eq = pd.to_numeric(v["equity_parent"], errors="coerce")
    ni = pd.to_numeric(v["ttm_net_income"], errors="coerce")
    v["roe"] = np.where(eq > 0, ni / eq * 100, np.nan)
    v["is_loss"] = eps.notna() & (eps <= 0)
    return v


def _pct_within(series: pd.Series, value: float) -> float:
    s = series.dropna()
    if len(s) == 0 or pd.isna(value):
        return np.nan
    return float((s < value).mean() * 100)


def group_valuation(val: pd.DataFrame, company: pd.DataFrame | None = None) -> pd.DataFrame:
    """分族群的估值分位。回傳每檔：所屬族群、該族群的口徑、族群中位數、樣本數、分位。

    一檔屬多個族群時，每個族群各算一列（前端顯示時取它的主族群）。
    """
    if val is None or val.empty:
        return pd.DataFrame()
    cfg = loader.load()
    metrics = {gid: (g.get("valuation_metric") or "pe")
               for gid, g in (cfg.get("groups") or {}).items()}
    m = loader.membership(cfg)

    joined = val.merge(m, on="code", how="left")

    # 沒有題材族群的用法定產業別當族群，口徑一律 pe
    if company is not None and not company.empty and "industry" in company.columns:
        joined = joined.merge(company[["code", "industry"]], on="code", how="left")
        fb = joined["group_id"].isna() & joined["industry"].notna()
        joined.loc[fb, "group_id"] = "ind_" + joined.loc[fb, "industry"].astype(str)
        joined.loc[fb, "group_name"] = joined.loc[fb, "industry"]
    joined = joined[joined["group_id"].notna()].copy()
    if joined.empty:
        return pd.DataFrame()

    # 每個族群的統計：先把離群 PE 拿掉
    joined["pe_clean"] = joined["pe"].where((joined["pe"] >= PE_MIN) & (joined["pe"] <= PE_MAX))

    out = []
    for gid, g in joined.groupby("group_id"):
        metric = metrics.get(gid, "pe")
        col = {"pe": "pe_clean", "pb_roe": "pb", "ps": "ps"}.get(metric, "pe_clean")
        valid = g[col].dropna()
        n = int(len(valid))
        loss_ratio = float(g["is_loss"].fillna(False).mean() * 100) if "is_loss" in g else np.nan
        median = float(valid.median()) if n >= MIN_ANY_N else np.nan
        for _, r in g.iterrows():
            v = r[col]
            out.append({
                "code": r["code"],
                "group_id": gid,
                "group_name": r.get("group_name"),
                "metric": metric,
                "metric_value": v,
                "group_median": median,
                "group_n": n,
                "percentile": _pct_within(valid, v) if n >= MIN_ANY_N else np.nan,
                "vs_median": (v / median) if (n >= MIN_ANY_N and pd.notna(v) and median) else np.nan,
                "thin_sample": n < MIN_GROUP_N,
                "group_loss_ratio": loss_ratio,
            })
    res = pd.DataFrame(out)

    # 族群樣本 < 5 但 ≥ 3：標示 thin；< 3：分位已是 NaN。
    # 退回產業別：若該檔在題材族群裡樣本不足、但產業別族群夠，用產業別的分位
    if company is not None and not company.empty and "industry" in company.columns:
        ind = res[res["group_id"].str.startswith("ind_")].set_index("code")
        need = res[(res["thin_sample"]) & (~res["group_id"].str.startswith("ind_"))]
        for i, r in need.iterrows():
            alt = ind.loc[r["code"]] if r["code"] in ind.index else None
            if alt is not None and isinstance(alt, pd.Series) and not alt.get("thin_sample", True):
                res.loc[i, ["percentile", "group_median", "group_n", "vs_median"]] = \
                    [alt["percentile"], alt["group_median"], alt["group_n"], alt["vs_median"]]
                res.loc[i, "fallback"] = "industry"
    if "fallback" not in res.columns:
        res["fallback"] = None
    return res


# ------------------------------------------------------------------ 月營收動能

def revenue_momentum(revenue_monthly: pd.DataFrame) -> pd.DataFrame:
    """每檔的月營收動能，含金融專家列的幾個陷阱處理：
    - 1、2 月合併看（農曆年落點不同會讓單月 YoY 失真）
    - MoM 對照該檔近 5 年同月的 MoM 中位數，不看絕對值（淡旺季）
    - YoY > 100% 標警示（併購 / 一次性），不自動當利多
    - 另給近 3 個月合計 YoY 當平滑版
    """
    if revenue_monthly is None or revenue_monthly.empty:
        return pd.DataFrame()
    df = revenue_monthly[["ym", "code", "revenue"]].copy()
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    df = df.dropna(subset=["ym", "code"]).drop_duplicates(["code", "ym"], keep="last")
    df["year"] = df["ym"].str[:4].astype(int)
    df["month"] = df["ym"].str[5:7].astype(int)

    rows = []
    for code, g in df.groupby("code"):
        g = g.sort_values("ym").reset_index(drop=True)
        if len(g) < 2:
            continue
        g["yoy"] = g["revenue"] / g.groupby("month")["revenue"].shift(1) * 100 - 100
        g["mom"] = g["revenue"].pct_change() * 100
        # 1+2 月合併的 YoY
        jf = g[g["month"].isin([1, 2])].groupby("year")["revenue"].sum()
        jf_yoy = (jf / jf.shift(1) * 100 - 100)
        last = g.iloc[-1]
        ym, month, year = last["ym"], int(last["month"]), int(last["year"])

        yoy = float(last["yoy"]) if pd.notna(last["yoy"]) else np.nan
        if month in (1, 2) and year in jf_yoy.index and pd.notna(jf_yoy.get(year)):
            yoy_adj = float(jf_yoy[year]); yoy_note = "1-2 月合併"
        else:
            yoy_adj = yoy; yoy_note = None

        # MoM 對照同月歷史中位數
        same_month = g[(g["month"] == month) & (g["year"] < year)].tail(5)["mom"].dropna()
        mom = float(last["mom"]) if pd.notna(last["mom"]) else np.nan
        mom_typical = float(same_month.median()) if len(same_month) >= 3 else np.nan

        # 近 3 個月合計 YoY
        r3 = g["revenue"].tail(3).sum()
        prev3 = g[g["ym"].isin(
            [f"{y}-{m:02d}" for y, m in
             [((int(x[:4]) - 1), int(x[5:7])) for x in g["ym"].tail(3)]])]["revenue"].sum()
        yoy_3m = float(r3 / prev3 * 100 - 100) if prev3 else np.nan

        # 連續 YoY 成長月數
        streak = 0
        for v in reversed(g["yoy"].tolist()):
            if pd.notna(v) and v > 0:
                streak += 1
            else:
                break

        # 年初至今累計 YoY
        ytd = g[g["year"] == year]["revenue"].sum()
        ytd_prev = g[(g["year"] == year - 1) & (g["month"] <= month)]["revenue"].sum()
        ytd_yoy = float(ytd / ytd_prev * 100 - 100) if ytd_prev else np.nan

        rows.append({
            "code": code, "ym": ym, "revenue": float(last["revenue"]),
            "yoy": yoy, "yoy_adj": yoy_adj, "yoy_note": yoy_note,
            "mom": mom, "mom_typical": mom_typical,
            "mom_vs_typical": (mom - mom_typical) if pd.notna(mom) and pd.notna(mom_typical) else np.nan,
            "yoy_3m": yoy_3m, "ytd_yoy": ytd_yoy,
            "growth_streak": streak,
            "months": int(len(g)),
            "flag_spike": bool(pd.notna(yoy) and yoy > 100),
            "is_record_high": bool(last["revenue"] >= g["revenue"].max()),
        })
    return pd.DataFrame(rows)


def momentum_score(rev: pd.Series) -> float:
    """營收動能 0–100。起始權重，待 walk-forward 檢驗。"""
    s = 50.0
    y = rev.get("yoy_adj")
    if pd.notna(y):
        s += float(np.clip(y, -40, 60)) * 0.5
    st = rev.get("growth_streak") or 0
    s += min(st, 12) * 1.5
    if rev.get("is_record_high"):
        s += 6
    mv = rev.get("mom_vs_typical")
    if pd.notna(mv):
        s += float(np.clip(mv, -20, 20)) * 0.3
    if rev.get("flag_spike"):
        s -= 8            # 併購 / 一次性認列，先扣分等人工確認
    return float(np.clip(s, 0, 100))
