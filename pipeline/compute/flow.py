"""M1 資金面：族群資金彙總、輪動雷達、集中度、相對強弱。

核心概念：個股層級的成交值加總到族群，再看「佔比」而不是絕對金額 ——
大盤整體量能起伏很大，只看金額會被大盤帶著走，看不出輪動。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..groups import loader

log = logging.getLogger(__name__)


def _attach_groups(price: pd.DataFrame, company: pd.DataFrame) -> pd.DataFrame:
    """把每檔股票掛上題材族群；沒有題材的用法定產業別當族群，確保全市場都有歸屬。

    一檔股票可以同時屬於多個族群（鴻海既是 AI 伺服器也是手機供應鏈）。
    這時它的成交值會被平均分配到各族群（weight = 1/族群數），而不是每個
    族群都算一次完整金額 —— 否則多族群股會把市場總量灌水，「資金佔比」
    這個指標就失去意義了。
    """
    m = loader.membership()
    df = price.merge(m, on="code", how="left")

    if not company.empty and "industry" in company.columns:
        df = df.merge(company[["code", "industry"]], on="code", how="left")
        fallback = df["group_id"].isna() & df["industry"].notna()
        df.loc[fallback, "group_id"] = "ind_" + df.loc[fallback, "industry"].astype(str)
        df.loc[fallback, "group_name"] = df.loc[fallback, "industry"]
        df.loc[fallback, "tier"] = "standalone"
        df.loc[fallback, "chain"] = "industry"

    df = df[df["group_id"].notna()].copy()
    if df.empty:
        return df

    # 同一天同一檔股票被掛到幾個族群，就把它的量能拆成幾份
    n_groups = df.groupby(["date", "code"])["group_id"].transform("nunique")
    df["weight"] = 1.0 / n_groups.clip(lower=1)
    return df


def group_daily(price: pd.DataFrame, company: pd.DataFrame,
                inst: pd.DataFrame | None = None,
                margin: pd.DataFrame | None = None) -> pd.DataFrame:
    """每日 × 每族群的資金彙總。這張表是 M1 所有圖表的共同來源。"""
    if price.empty:
        return pd.DataFrame()

    df = _attach_groups(price, company)
    if df.empty:
        log.warning("沒有任何個股對得上族群，請檢查 groups.yaml 與 company_info")
        return pd.DataFrame()

    df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce").fillna(0)
    df["prev_close"] = df["close"] - df["change"].fillna(0)
    df["chg_pct"] = np.where(df["prev_close"] > 0,
                             df["change"] / df["prev_close"] * 100, np.nan)

    if inst is not None and not inst.empty:
        df = df.merge(inst[["date", "code", "foreign_total", "trust", "dealer"]],
                      on=["date", "code"], how="left")
    for col in ("foreign_total", "trust", "dealer"):
        if col not in df.columns:
            df[col] = np.nan

    if margin is not None and not margin.empty:
        df = df.merge(margin[["date", "code", "margin_change", "margin_balance"]],
                      on=["date", "code"], how="left")
    for col in ("margin_change", "margin_balance"):
        if col not in df.columns:
            df[col] = np.nan

    def _agg(g: pd.DataFrame) -> pd.Series:
        w = g["weight"]
        tv = float((g["turnover"] * w).sum())
        # 漲跌幅用成交值加權，否則會被冷門小型股主導
        ww = (g["turnover"] * w).where(g["chg_pct"].notna(), 0)
        wsum = ww.sum()
        chg = float((g["chg_pct"].fillna(0) * ww).sum() / wsum) if wsum > 0 else np.nan
        return pd.Series({
            "turnover": tv,
            "chg_pct": chg,
            "advancers": int((g["chg_pct"] > 0).sum()),
            "decliners": int((g["chg_pct"] < 0).sum()),
            "constituents": int(g["code"].nunique()),
            "foreign_net": (g["foreign_total"] * w).sum(min_count=1),
            "trust_net": (g["trust"] * w).sum(min_count=1),
            "dealer_net": (g["dealer"] * w).sum(min_count=1),
            "margin_change": (g["margin_change"] * w).sum(min_count=1),
        })

    out = (df.groupby(["date", "group_id", "group_name", "tier", "chain"],
                      dropna=False)
             .apply(_agg, include_groups=False)
             .reset_index())

    total = out.groupby("date")["turnover"].transform("sum")
    out["turnover_share"] = np.where(total > 0, out["turnover"] / total * 100, np.nan)
    return out.sort_values(["date", "turnover"], ascending=[True, False])


def rotation_radar(group_hist: pd.DataFrame, short: int = 5,
                   long: int = 20) -> pd.DataFrame:
    """輪動雷達：成交值佔比的 5 日均 減 20 日均。

    正值＝資金正在往這個族群集中；負值＝正在流出。
    用佔比的移動平均差值而不是單日數字，是為了濾掉單日的假訊號。
    """
    if group_hist.empty:
        return pd.DataFrame()

    g = group_hist.sort_values("date").copy()
    g["share_short"] = (g.groupby("group_id")["turnover_share"]
                         .transform(lambda s: s.rolling(short, min_periods=2).mean()))
    g["share_long"] = (g.groupby("group_id")["turnover_share"]
                        .transform(lambda s: s.rolling(long, min_periods=5).mean()))
    g["rotation"] = g["share_short"] - g["share_long"]

    latest = g["date"].max()
    out = g[g["date"] == latest].copy()
    return out.sort_values("rotation", ascending=False)


def concentration(group_hist: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """資金集中度：前 N 大族群吃掉多少成交值。

    上升＝行情縮圈到少數族群（通常是主流股獨強）
    下降＝資金擴散（通常是輪動或補漲階段）
    """
    if group_hist.empty:
        return pd.DataFrame()
    rows = []
    for d, g in group_hist.groupby("date"):
        top = g.nlargest(top_n, "turnover")["turnover_share"].sum()
        rows.append({"date": d, "top_share": top})
    out = pd.DataFrame(rows).sort_values("date")
    out["top_share_ma20"] = out["top_share"].rolling(20, min_periods=5).mean()
    return out


def relative_strength(group_hist: pd.DataFrame, market: pd.DataFrame,
                      window: int = 20) -> pd.DataFrame:
    """族群相對強弱：族群 N 日報酬 減 大盤 N 日報酬。"""
    if group_hist.empty:
        return pd.DataFrame()

    g = group_hist.sort_values("date").copy()
    # 用族群成交值加權漲跌幅累乘還原出族群指數
    g["factor"] = 1 + g["chg_pct"].fillna(0) / 100
    g["group_index"] = g.groupby("group_id")["factor"].cumprod()
    g["ret"] = (g.groupby("group_id")["group_index"]
                 .transform(lambda s: s / s.shift(window) - 1) * 100)

    market_ret = np.nan
    if market is not None and not market.empty and "taiex" in market.columns:
        mk = market.sort_values("date")
        taiex = pd.to_numeric(mk["taiex"], errors="coerce").dropna()
        if len(taiex) > window:
            market_ret = (taiex.iloc[-1] / taiex.iloc[-1 - window] - 1) * 100

    latest = g["date"].max()
    out = g[g["date"] == latest][
        ["date", "group_id", "group_name", "tier", "chain", "ret"]].copy()
    out["market_ret"] = market_ret
    out["rs"] = out["ret"] - market_ret
    return out.sort_values("rs", ascending=False)


def trust_streak(inst_hist: pd.DataFrame, min_days: int = 3) -> pd.DataFrame:
    """投信連續買超天數排行。

    台股中期最有效的籌碼訊號之一：投信持續買代表法人真的在建倉，
    而不是當沖或避險部位。
    """
    if inst_hist.empty or "trust" not in inst_hist.columns:
        return pd.DataFrame()

    df = inst_hist.sort_values(["code", "date"]).copy()
    df["buying"] = df["trust"] > 0
    # 每檔股票各自從最新一天往回數連續買超
    rows = []
    for code, g in df.groupby("code"):
        g = g.sort_values("date")
        streak = 0
        total = 0.0
        for buying, net in zip(reversed(g["buying"].tolist()),
                               reversed(g["trust"].tolist())):
            if not buying:
                break
            streak += 1
            total += float(net or 0)
        if streak >= min_days:
            rows.append({"code": code, "streak_days": streak,
                         "accumulated": total,
                         "date": g["date"].iloc[-1]})
    out = pd.DataFrame(rows)
    return out.sort_values("streak_days", ascending=False) if not out.empty else out
