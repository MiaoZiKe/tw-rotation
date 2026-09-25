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


# ------------------------------------------------------------------ 累計 → 單季
# 證交所 t187ap14_L 給的是「年度累計數」（Q2 = 上半年合計），FinMind 給的是「單季數」，
# 兩者混在同一張 financial_q 表裡。以前 ttm() 直接把最近四列相加，
# 於是走證交所那條路的股票 TTM EPS 被灌水、自算本益比系統性偏低約 20%
# （用證交所自己公布的官方 PE 對帳，比值中位數 0.80，FinMind 那批是 1.00）。
# 這裡在算 TTM 之前先把累計數還原成單季：同一 code 同一年度，Qn 減掉 Q(n-1) 的累計。
CUM_COLS = ("eps", "revenue", "operating_income", "non_operating", "net_income", "gross_profit")


def _is_cumulative(df: pd.DataFrame) -> pd.Series:
    """哪些列是累計數。證交所那條路沒有 announce_date、但有 industry，用這個判。

    之後 sources/twse.py 若補上 is_cumulative 欄位，這裡會優先採用它。
    """
    if "is_cumulative" in df.columns:
        flag = df["is_cumulative"].fillna(False).astype(bool)
        if flag.any():
            return flag
    has_ann = df["announce_date"].notna() if "announce_date" in df.columns else pd.Series(False, index=df.index)
    return ~has_ann


def _decumulate(df: pd.DataFrame) -> pd.DataFrame:
    """把累計列還原成單季列。

    同一年度從 Q1 往後走，邊走邊記「到上一季為止的單季合計」：
      累計列 → 單季 = 累計值 − 到上一季的合計
      單季列 → 原值不動
    兩種來源會混在同一年（例如 Q1 來自 FinMind 的單季、Q2 來自證交所的累計），
    所以不能只在「前後都是累計」時才相減 —— 那正是第一版漏掉 2412 的原因。
    季別一旦不連續（缺 Q2 直接跳 Q3）就停止還原，寧可不減也不要減出一個兩季合計。
    """
    if df.empty:
        return df
    cum = _is_cumulative(df)
    if not cum.any():
        return df
    out = df.copy()
    cols = [c for c in CUM_COLS if c in out.columns]
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    orig = out[cols].copy()
    for _, g in out.groupby(["code", "year"], sort=False):
        g = g.sort_values("quarter")
        run = {c: 0.0 for c in cols}      # 到上一季為止的單季合計
        ok = True                          # 季別到目前為止是不是連續的
        expect = 1
        for idx in g.index:
            q = int(out.at[idx, "quarter"])
            if q != expect:
                ok = False
            expect = q + 1
            is_cum = bool(cum.get(idx, False))
            for c in cols:
                v = orig.at[idx, c]
                if pd.isna(v):
                    continue
                single = float(v)
                if is_cum and q > 1:
                    if not ok:
                        continue           # 季別不連續，不敢減
                    single = float(v) - run[c]
                    out.at[idx, c] = single
                run[c] += single
    return out


def ttm(financial_q: pd.DataFrame, shares: dict | None = None, asof: str | None = None) -> pd.DataFrame:
    """每檔股票的近四季合計（EPS、淨利、營收）與最新一季毛利率。

    要求四季連續；缺任何一季就不給 TTM（給 NaN），而不是拿三季湊。

    shares（`share_table(corporate_actions(...))`）有給時，每一季 EPS 換算到 asof 當天的股本：
      eps_adj ＝ eps ÷ eps_divisor(...)（規則見 eps_divisor）。
    淨利、營收是金額，不受股數影響，不調。原始 EPS 合計留在 ttm_eps_raw 方便對帳。
    """
    if financial_q is None or financial_q.empty:
        return pd.DataFrame()
    df = financial_q.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["quarter"] = pd.to_numeric(df["quarter"], errors="coerce")
    df = df.dropna(subset=["year", "quarter", "code"])
    df["qidx"] = df["year"].astype(int) * 4 + df["quarter"].astype(int)
    df = df.sort_values(["code", "qidx"]).drop_duplicates(["code", "qidx"], keep="last")
    df = _decumulate(df)

    rows = []
    for code, g in df.groupby("code"):
        # 除數要在完整序列上算（第一季也需要「上一季」的隱含股數），再切最後四季
        div_all = (eps_divisors(g, shares, code, asof) if shares and str(code) in shares
                   else [1.0] * len(g))
        g = g.tail(4)
        div = np.asarray(div_all[-len(g):], dtype=float)
        if len(g) < 4 or (g["qidx"].max() - g["qidx"].min()) != 3:
            complete = False
        else:
            complete = True
        last = g.iloc[-1]
        eps_raw = pd.to_numeric(g["eps"], errors="coerce")
        eps = eps_raw
        if shares and str(code) in shares:
            eps = eps_raw / div
        rev = pd.to_numeric(g["revenue"], errors="coerce")
        ni = pd.to_numeric(g["net_income"], errors="coerce")
        gp = pd.to_numeric(last.get("gross_profit"), errors="coerce")
        rv = pd.to_numeric(last.get("revenue"), errors="coerce")
        rows.append({
            "code": code,
            "ttm_eps": float(eps.sum()) if complete and eps.notna().all() else np.nan,
            "ttm_eps_raw": float(eps_raw.sum()) if complete and eps_raw.notna().all() else np.nan,
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


def latest_balance(balance_q: pd.DataFrame, shares: dict | None = None,
                   asof: str | None = None) -> pd.DataFrame:
    """最新一季資產負債：股數、母公司權益、BPS。

    shares 有給時，股數 × share_growth(季底, asof]、BPS ÷ 同一個倍數
    （6669 Q2 股本是除權前的 1.87 億股，不調的話市值只剩 1/3、PB 算成 2.9，實際約 8.6）。
    用**季底**不用公布日：資產負債表上的股數就是季底那天的股數，季底之後的配股一律沒反映。
    """
    if balance_q is None or balance_q.empty:
        return pd.DataFrame()
    df = balance_q.copy()
    df["qidx"] = (pd.to_numeric(df["year"], errors="coerce") * 4 +
                  pd.to_numeric(df["quarter"], errors="coerce"))
    df = df.dropna(subset=["qidx"]).sort_values(["code", "qidx"])
    last = df.groupby("code").tail(1).copy()
    if shares:
        pe_ = last["period_end"] if "period_end" in last.columns else pd.Series([None] * len(last), index=last.index)
        g = [share_growth(shares, c, (e if not _blank(e) else quarter_end(int(y), int(q))), asof)
             for c, e, y, q in zip(last["code"], pe_, pd.to_numeric(last["year"]), pd.to_numeric(last["quarter"]))]
        g = np.asarray(g, dtype=float)
        last["shares"] = pd.to_numeric(last["shares"], errors="coerce") * g
        last["bps"] = pd.to_numeric(last["bps"], errors="coerce") / g
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
    # ★ 2026-09-21：自動桶（`ind_<法定產業別>`）也要能指定估值口徑。
    #
    #   為什麼需要這個：族群改成 tide 的 110 個板塊之後，「銀行金融」只收銀行股，
    #   **壽險型金控（2881 富邦金、2882 國泰金）、證券、產險、票券全部落到自動桶
    #   `ind_金融保險`**。自動桶以前一律用本益比 —— 而保險公司的 EPS 會被
    #   金融資產的評價損益扭曲，用 PE 跟同業比會得到完全錯誤的結論。
    #   這不是換個 id 的問題，是**金控股的估值口徑真的壞掉了**（pytest 的
    #   test_fundamental_payload_end_to_end 就是撞到這一條）。
    #
    #   做法：`groups.yaml` 的 `meta.ind_display` 登記每個自動桶的顯示名稱，
    #   需要非預設口徑的再加 `valuation_metric`。口徑仍然只寫在 YAML 裡、
    #   不在程式碼硬編碼（本檔開頭第 9 行那條規則沒有被打破）。
    for _ind, _cfg in ((cfg.get("meta") or {}).get("ind_display") or {}).items():
        if isinstance(_cfg, dict) and _cfg.get("valuation_metric"):
            metrics["ind_" + str(_ind)] = _cfg["valuation_metric"]
    m = loader.membership(cfg)

    joined = val.merge(m, on="code", how="left")

    # 沒有題材族群的用法定產業別當族群，口徑一律 pe
    if company is not None and not company.empty and "industry" in company.columns:
        joined = joined.merge(company[["code", "industry"]], on="code", how="left")
        fb = joined["group_id"].isna() & joined["industry"].notna()
        joined.loc[fb, "group_id"] = "ind_" + joined.loc[fb, "industry"].astype(str)
        _indmap = loader.ind_names()          # 先拿字典，不要逐列呼叫 ind_name（會重讀 YAML）
        _ind = joined.loc[fb, "industry"].astype(str)
        joined.loc[fb, "group_name"] = _ind.map(_indmap).fillna(_ind)
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
                # ★ 2026-09-19：原本這裡回的是**比值**（v / median），但前端兩處都當成
                #   「相對中位的百分比差」在用 —— site/app.js 的「只看低於族群中位」判 < 0，
                #   site/industry.js 個股頁印「高於／低於中位 N%」。本益比恆正，所以比值永遠 > 0：
                #   那個勾選框從掛上去的第一天就永遠篩出 0 筆（畫面寫「沒有符合條件的股票」，
                #   看起來像今天剛好沒便宜股），而個股頁對每一檔都印「高於中位」。
                #   口徑統一成百分比差：-30 ＝ 比族群中位便宜 30%。
                "vs_median": ((v / median - 1) * 100
                              if (n >= MIN_ANY_N and pd.notna(v) and median) else np.nan),
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


# ------------------------------------------------------------------ 除權息還原（payload 端計算，不回寫資料湖）
#
# ★ 2026-09-25 審查員 R5：6669 緯穎 9/2 除權（每股配 1.98 股，面額 10 元配 19.83 元），
#   股價 7800 → 2615。資料湖存的是「當天真的成交價」（這是對的，不能改），但下游全部拿它直接算：
#   K 線 -66% 斷崖、MA 失真、判讀目標價錯；EPS 還是除權前股本 → 本益比 6.7（應約 20）；
#   現金股利還是舊股本 → 殖利率 10.33%（應約 3.4%）；同業分位掉到 0%。
#
#   修法分兩條線，**刻意分開**：
#   1. 價格還原（K 線、均線、技術判讀）：官方參考價 ÷ 除權息前收盤＝還原因子，往回連乘。
#      這是「總報酬還原」（現金＋股票都還原），跟看盤軟體的「還原權值」同一個口徑。
#   2. 股數還原（EPS、BPS、股本、現金股利）：只看**股數**變化（配股、分割、變更面額、減資），
#      現金股利不動股數。本益比＝收盤 ÷ 近四季 EPS 合計 這條紅線不變，
#      只是把「除權前公布的那幾季 EPS」換算到今天的股本上（除以配股後股數倍數）。
#      理由見 DECISIONS #258。
#
#   配股率一律**從官方參考價反推**，不用「股票股利元 ÷ 10」：
#   5314 世紀* 面額 0.5 元，每股配 1.58 元股票股利＝每千股配 3,157 股，÷10 會算成 0.158（差 20 倍）。
#   參考價 14.75 反推 (61.3 − 0) ÷ 14.75 − 1 ＝ 3.156，與公司公告的 3,157.03 股／千股一致（MoneyDJ 2026-08）。

CLIFF_RET = 0.35            # 還原後單日 |報酬| 超過這個 → 一定還有沒還原到的股本事件
NEW_LISTING_DAYS = 5        # 上市（櫃）前 5 個交易日無漲跌幅限制
LIMIT_BAND = 0.10           # 一般股票漲跌幅 ±10%：推估參考價時的可行區間
# 分割／變更面額常見倍數（10→1 元＝10、10→0.5 元＝20…），反分割取倒數
_NICE_SPLITS = (2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0, 15.0, 20.0, 25.0, 40.0, 50.0, 100.0)
_NICE_RATIOS = _NICE_SPLITS + tuple(1.0 / x for x in _NICE_SPLITS)
_OHLC = ("open", "high", "low", "close")


def clean_price(price: pd.DataFrame) -> pd.DataFrame:
    """把「沒成交存成 0」的 K 棒拿掉，局部 0 的開高低用收盤補。

    資料湖有 1.5 萬列收盤＝0（沒成交日上游給 0，不是真的跌到 0），6949 還有 5 根 OHLC 全 0。
    這些列若留著：K 線畫出掉到 0 的針、報酬率算出 -100%、均線被拉歪。
    收盤 ≤ 0 或缺值 → 整列丟掉（這一天對價格而言等於不存在，下一天的報酬對上一個有效收盤）。
    收盤有值、但開／高／低是 0 或缺 → 用收盤補，再把高低夾回包住開收。
    """
    if price is None or price.empty or "close" not in price.columns:
        return price
    c = pd.to_numeric(price["close"], errors="coerce")
    df = price[c > 0].copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    for col in ("open", "high", "low"):
        if col in df.columns:
            v = pd.to_numeric(df[col], errors="coerce")
            df[col] = v.where(v > 0, df["close"])
    if {"open", "high", "low"} <= set(df.columns):
        df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
        df["low"] = df[["open", "high", "low", "close"]].min(axis=1)
    return df


def _infer_reference(prev: float, close: float, change) -> tuple[float, str]:
    """沒有官方除權息結果時，推估斷崖那天的參考價。回傳 (參考價, 推估方式)。

    1. `change`（漲跌，官方是對參考價算的）不是 0：參考價＝收盤 − 漲跌，而且它確實跟前收差很多才採用。
       0052 分割（245.3 → 35.35，漲跌 +0.31 → 參考價 35.04 ＝ 245.3 ÷ 7）、5904 面額 10→1 都靠這條。
    2. 漲跌是 0（FinMind 在參考價重設那天常給 0）：一般股票當天只能在參考價 ±10% 內成交，
       所以參考價落在 [收盤/1.1, 收盤/0.9]。常見分割倍數裡**恰好一個**落在這個區間就用它
       （6949 1490 → 67.1：區間 [61.0, 74.6]，只有 ÷20＝74.5 落在裡面）。
    3. 都不成立（例如減資，比例任意）：假設當天平盤（參考價＝收盤）。
       誤差上限就是那一天的漲跌幅（≤10%），但不會再有 -66% 的假斷崖。
    """
    try:
        ch = float(change)
    except (TypeError, ValueError):
        ch = float("nan")
    if np.isfinite(ch) and ch != 0:
        ref = close - ch
        if ref > 0 and abs(ref / prev - 1) > 0.30:
            return ref, "inferred_change"
    lo, hi = close / (1 + LIMIT_BAND), close / (1 - LIMIT_BAND)
    hits = [n for n in _NICE_RATIOS if lo <= prev / n <= hi]
    if len(hits) == 1:
        return prev / hits[0], "inferred_ratio"
    return close, "inferred_flat"


def corporate_actions(price: pd.DataFrame | None, dividend_results: pd.DataFrame | None = None,
                      dividend_events: pd.DataFrame | None = None) -> pd.DataFrame:
    """每一個會讓價格不連續的股本事件：code, date, price_factor, share_ratio, source。

    - price_factor：事件日「之前」的價格要乘的倍數（參考價 ÷ 前收盤；< 1 為除權息／分割、> 1 為減資／反分割）。
    - share_ratio：每 1 股變成 (1 + share_ratio) 股。純除息＝0；6669 ＝ 1.98；減資為負。
    - source：dividend_results（官方參考價）／inferred_change／inferred_ratio／inferred_flat。

    兩段：
    1. 官方：dividend_results 的每一筆。含「權」字的才有股數變化，
       配股率 ＝ (前收盤 − 同日現金股利) ÷ 參考價 − 1（同日現金股利取自 dividend_events）。
    2. 補漏：官方沒有、但套完官方因子後單日 |報酬| 仍 > 35% 的那天（分割、變更面額、減資、
       dividend_results 還沒回補到的股票），用 `_infer_reference` 推估，事件視為純股數變化。
       上市前 5 個交易日沒有漲跌幅限制，真的會單日 +200%，那幾天**不當成**股本事件。
    例外：參考價缺值／≤ 0／高於前收盤 → 當資料錯誤略過（不猜）。
    """
    cols = ["code", "date", "price_factor", "share_ratio", "source"]
    rows: list[dict] = []
    known: set[tuple[str, str]] = set()

    cash_by: dict[tuple[str, str], float] = {}
    if (dividend_events is not None and not dividend_events.empty
            and {"kind", "ex_date", "amount"} <= set(dividend_events.columns)):
        c = dividend_events[dividend_events["kind"] == "cash"]
        for code, d, amt in zip(c["code"].astype(str), c["ex_date"].astype(str),
                                pd.to_numeric(c["amount"], errors="coerce")):
            if pd.notna(amt):
                cash_by[(code, d)] = cash_by.get((code, d), 0.0) + float(amt)

    if dividend_results is not None and not dividend_results.empty:
        r = dividend_results.copy()
        r["code"] = r["code"].astype(str)
        r["date"] = r["date"].astype(str)
        r = r.drop_duplicates(["code", "date"], keep="last")
        kinds = r["kind"] if "kind" in r.columns else pd.Series([None] * len(r), index=r.index)
        for code, d, kind, before, ref in zip(r["code"], r["date"], kinds,
                                              pd.to_numeric(r["before_price"], errors="coerce"),
                                              pd.to_numeric(r["reference_price"], errors="coerce")):
            if not (pd.notna(before) and pd.notna(ref) and before > 0 and ref > 0):
                continue
            pf = float(ref) / float(before)
            if not (0.01 <= pf <= 1.0001):
                continue
            sr = 0.0
            if kind is not None and "權" in str(kind):
                cash = cash_by.get((code, d), 0.0)
                sr = (float(before) - cash) / float(ref) - 1
                if sr < 0.0005:             # 參考價四捨五入的雜訊
                    sr = 0.0
            rows.append({"code": code, "date": d, "price_factor": pf, "share_ratio": sr,
                         "source": "dividend_results"})
            known.add((code, d))

    acts = pd.DataFrame(rows, columns=cols)

    # ---- 補漏：套完官方因子後仍然斷崖的那天
    if price is not None and not price.empty:
        keep = ["code", "date", "close"] + (["change"] if "change" in price.columns else [])
        px = price[keep].copy()
        px["code"] = px["code"].astype(str)
        px["date"] = px["date"].astype(str)
        px["close"] = pd.to_numeric(px["close"], errors="coerce")
        px = (px[px["close"] > 0].sort_values(["code", "date"])
                .drop_duplicates(["code", "date"], keep="last").reset_index(drop=True))
        adj = adjust_prices(px[["code", "date", "close"]], acts, mode="total")
        prev_adj = adj.groupby("code")["close"].shift(1)
        prev_raw = px.groupby("code")["close"].shift(1)
        nth = px.groupby("code").cumcount()
        ret = adj["close"] / prev_adj - 1
        cand = px[(ret.abs() > CLIFF_RET) & (nth >= NEW_LISTING_DAYS) & (prev_raw > 0)]
        extra = []
        for i in cand.index:
            code, d = px.at[i, "code"], px.at[i, "date"]
            if (code, d) in known:
                continue
            p0, c0 = float(prev_raw.at[i]), float(px.at[i, "close"])
            ref, src = _infer_reference(p0, c0, px.at[i, "change"] if "change" in px.columns else None)
            pf = ref / p0
            extra.append({"code": code, "date": d, "price_factor": pf,
                          "share_ratio": 1.0 / pf - 1.0, "source": src})
        if extra:
            acts = pd.concat([acts, pd.DataFrame(extra, columns=cols)], ignore_index=True)
    return acts.sort_values(["code", "date"]).reset_index(drop=True)


def adjust_prices(price: pd.DataFrame, actions: pd.DataFrame | None, mode: str = "total") -> pd.DataFrame:
    """回傳還原後的價格表（欄位不變；開高低收／漲跌乘上因子、成交量換算到今天的股數）。

    mode="total"：價格乘 price_factor（現金＋股票都還原）→ K 線、均線、技術判讀用。
    mode="share"：價格只乘 1 ÷ (1 + share_ratio)（只還原股數）→ 季節性用：
                  季節性的基準是同一份價格算出的全市場等權報酬，現金股利兩邊都有，
                  只修股數斷崖就好，不動既有口徑。
    最新一天因子恆為 1：還原是「往回」調，今天的收盤永遠等於真的收盤（報價顯示不受影響）。
    某一列的因子 ＝ 所有「日期 > 該列」的事件因子連乘（事件當天本身已是新基準，不乘）。
    """
    if price is None or price.empty or actions is None or actions.empty:
        return price.copy() if price is not None else price
    a = actions.copy()
    a["code"] = a["code"].astype(str)
    a["date"] = a["date"].astype(str)
    share_pf = 1.0 / (1.0 + pd.to_numeric(a["share_ratio"], errors="coerce").fillna(0.0))
    a["pf"] = pd.to_numeric(a["price_factor"], errors="coerce") if mode == "total" else share_pf
    a["sf"] = share_pf
    a = a.dropna(subset=["pf"])
    a = a.groupby(["code", "date"], as_index=False)[["pf", "sf"]].prod()
    a = a.sort_values(["code", "date"], ascending=[True, False])
    a["cum_pf"] = a.groupby("code")["pf"].cumprod()     # 日期 ≥ 該事件的所有因子連乘
    a["cum_sf"] = a.groupby("code")["sf"].cumprod()
    a["_d"] = pd.to_datetime(a["date"], errors="coerce")
    a = a.dropna(subset=["_d"]).sort_values("_d")

    df = price.copy()
    pos = np.arange(len(df))
    left = pd.DataFrame({"_i": pos, "_code": df["code"].astype(str).to_numpy(),
                         "_d": pd.to_datetime(df["date"].astype(str), errors="coerce").to_numpy()})
    left = left.dropna(subset=["_d"]).sort_values("_d")
    m = pd.merge_asof(left, a[["code", "_d", "cum_pf", "cum_sf"]].rename(columns={"code": "_code"}),
                      on="_d", by="_code", direction="forward", allow_exact_matches=False)
    f = np.ones(len(df))
    sfac = np.ones(len(df))
    f[m["_i"].to_numpy()] = m["cum_pf"].fillna(1.0).to_numpy()
    sfac[m["_i"].to_numpy()] = m["cum_sf"].fillna(1.0).to_numpy()
    for col in _OHLC + ("change",):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").to_numpy() * f
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").to_numpy() / sfac
    return df


def share_table(actions: pd.DataFrame | None) -> dict:
    """每檔的股數事件表：code → (日期 list, 前綴連乘 array)。給 share_growth 查表用。"""
    out: dict = {}
    if actions is None or actions.empty:
        return out
    sr = pd.to_numeric(actions["share_ratio"], errors="coerce").fillna(0.0)
    a = actions[sr != 0]
    for code, g in a.groupby(a["code"].astype(str)):
        g = g.sort_values("date")
        mult = (1.0 + pd.to_numeric(g["share_ratio"], errors="coerce").fillna(0.0)).to_numpy()
        out[code] = (g["date"].astype(str).tolist(), np.concatenate([[1.0], np.cumprod(mult)]))
    return out


def _blank(x) -> bool:
    return x is None or (isinstance(x, float) and np.isnan(x)) or str(x) in ("", "None", "NaT", "nan")


def share_growth(tbl: dict, code: str, after, upto, *, include_after: bool = False) -> float:
    """(after, upto] 期間股數變成幾倍（include_after=True 時為 [after, upto]）。

    EPS 在 a 日公布 → 用 (a, upto]：a 日之後才除權，那一季的 EPS 是舊股本，要除以這個倍數；
      公布日當天或之前就已除權，依 IAS 33 公布的 EPS 已經是新股本，不再調。
    現金股利在 e 日除息 → 用 [e, upto]：同一天既除息又除權（權息），現金是按舊股數配的。
    after 缺值 → 1（不調；寧可少調也不要亂調）。
    """
    import bisect
    ent = tbl.get(str(code))
    if ent is None or _blank(after):
        return 1.0
    dates, pref = ent
    s_upto = "9999-12-31" if _blank(upto) else str(upto)
    i0 = (bisect.bisect_left if include_after else bisect.bisect_right)(dates, str(after))
    i1 = bisect.bisect_right(dates, s_upto)
    if i1 <= i0:
        return 1.0
    return float(pref[i1] / pref[i0])


QUARTER_DEADLINE = {1: "05-15", 2: "08-14", 3: "11-14"}


def statutory_available(year: int, quarter: int) -> str:
    """財報法定公布期限：Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31。announce_date 缺值時的保守替代。"""
    if int(quarter) == 4:
        return f"{int(year) + 1}-03-31"
    return f"{int(year)}-{QUARTER_DEADLINE[int(quarter)]}"



def quarter_end(year: int, quarter: int) -> str:
    return f"{int(year)}-" + {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[int(quarter)]


def _prev_day(d: str) -> str:
    return (pd.Timestamp(d) - pd.Timedelta(days=1)).date().isoformat()


def eps_divisor(tbl: dict, code: str, period_end: str, avail: str, upto: str | None,
                impl_ratio: float | None = None) -> float:
    """單季 EPS 要除以多少，才會換算成 upto 當天股本下的 EPS。

    股數事件分兩段看：
    - 季底之前除權：那一季的加權股數早就含了，不必調。
    - 季底之後 ~ 財報公布之間除權（「模糊區」）：依 IAS 33，財報核准發布前發生的配股要追溯調整，
      公布的 EPS **可能已經**是新股本（5386 7/20 除權、8/14 才公布 Q2，Q2 EPS 已經按新股本算）。
      判斷法：這一季的隱含股數（淨利 ÷ EPS）比上一季變成幾倍（impl_ratio）；
      在對數尺度上比較接近模糊區的配股倍數 → 已反映，不再調；比較接近 1 → 未反映，要調。
      沒有 impl_ratio（缺淨利、EPS 為 0、少上一季）→ 退回日期規則：公布日「之前」除權視為已反映，
      公布日當天或之後視為未反映（FinMind 的 announce_date 其實是法定期限，實際公布通常更早，
      當天除權的財報幾乎一定是除權前就核准的）。
    - 公布之後才除權：一定是舊股本，要調（6669：8/14 公布 Q2、9/2 除權）。
    """
    if not tbl or str(code) not in tbl:
        return 1.0
    total = share_growth(tbl, code, period_end, upto)
    if total == 1.0:
        return 1.0
    amb = share_growth(tbl, code, period_end, avail)            # (季底, 公布日]
    if amb == 1.0:
        return total
    if impl_ratio is not None and np.isfinite(impl_ratio) and impl_ratio > 0:
        reflected = abs(np.log(impl_ratio) - np.log(amb)) < abs(np.log(impl_ratio))
        return total / amb if reflected else total
    return total / share_growth(tbl, code, period_end, _prev_day(avail))


def eps_basis_info(g: pd.DataFrame) -> list[tuple[str, str, float | None]]:
    """每一季的 (季底, 公布日, impl_ratio)，順序同 g 依 year、quarter 排序後。

    g 需有 year、quarter、eps，選配 net_income、announce_date、period_end。
    公布日缺值用法定期限、季底缺值用曆法季底。
    impl_ratio ＝ (本季淨利 ÷ 本季 EPS) ÷ (上季淨利 ÷ 上季 EPS)，上一季必須剛好是前一季、兩者皆 > 0。
    """
    g = g.sort_values(["year", "quarter"])
    eps = pd.to_numeric(g["eps"], errors="coerce").to_numpy()
    ni = (pd.to_numeric(g["net_income"], errors="coerce").to_numpy()
          if "net_income" in g.columns else np.full(len(g), np.nan))
    ys, qs = g["year"].astype(int).to_numpy(), g["quarter"].astype(int).to_numpy()
    ann = g["announce_date"].to_numpy() if "announce_date" in g.columns else [None] * len(g)
    pend = g["period_end"].to_numpy() if "period_end" in g.columns else [None] * len(g)
    with np.errstate(divide="ignore", invalid="ignore"):
        implied = np.where((eps != 0) & np.isfinite(eps) & np.isfinite(ni), ni / eps, np.nan)
    out = []
    for i in range(len(g)):
        pe_ = str(pend[i]) if not _blank(pend[i]) else quarter_end(ys[i], qs[i])
        av = str(ann[i])[:10] if not _blank(ann[i]) else statutory_available(ys[i], qs[i])
        ratio = None
        if i > 0 and ys[i] * 4 + qs[i] - (ys[i - 1] * 4 + qs[i - 1]) == 1:
            a, b = implied[i], implied[i - 1]
            if np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0:
                ratio = float(a / b)
        out.append((pe_, av, ratio))
    return out


def eps_divisors(g: pd.DataFrame, tbl: dict, code: str, upto: str | None) -> list[float]:
    """一檔多季的 eps_divisor（換算到 upto 當天股本），順序同 g 依 year、quarter 排序後。"""
    return [eps_divisor(tbl, code, pe_, av, upto, r) for pe_, av, r in eps_basis_info(g)]
