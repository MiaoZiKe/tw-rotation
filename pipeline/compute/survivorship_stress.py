"""存活者偏誤壓力測試（第八輪首選候選：月營收動能 + 近 52 週高 85%，pit 前 200 池）。

只做壓力測試，不改任何候選參數。做法：
  1. 把 FinMind 下市名單（backfill_progress 的 delisted_px:<代號> 鍵，201 檔）對照資料湖，
     找出「湖裡完全沒有價量」與「只有零星幾列」的代號。
  2. 用湖裡真的已停止交易、且有足夠歷史的股票（有資料的下市批）量出：進前 200 池的比例、
     被策略選中的比例、最後 60 個交易日的平均跌幅。
  3. 把「缺資料批」依估計的選中率注入逐筆交易：樂觀（現狀）／中度（缺資料批吃有資料批平均末 60 日跌幅）／
     最壞（被選中的缺資料股一律 -100%）。
注入方式（近似，文件有寫）：每筆交易占權益約 1/N；對每筆交易以機率 q 把報酬換成 L，
於該筆出場日把權益乘上 (1 - w*q*(ret-L))，再由調整後權益重算年化與回撤。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import factor_lab as FL
from . import rev_lab8 as R8
from . import swing_lab5 as S

OUT = R8.OUT
WINDOWS = {"2013~2016": R8.NEW, "2019~2022": FL.INNER, "2023+": FL.FINAL}
DEAD_BEFORE = "2026-09-01"     # 最後一筆未還原價早於此日 = 已停止交易
MIN_ROWS = 250                  # 至少一年價量才算「有資料」


def specs():
    return {"S2 原版": R8.make_spec(), "S2-R（產業上限 2）": R8.make_spec(cap=2), "候選 營收動能+近52週高85%": R8.make_spec(x2="nh85")}


def fm_codes():
    d = json.load(open(R8.ROOT / "data" / "_state" / "backfill_progress.json", encoding="utf-8"))["done"]
    return sorted(k.split(":")[1] for k in d if k.startswith("delisted_px:"))


def life_table(P):
    """每檔的首末筆『真實』價量日（P['C'] 沒有前向填補；Cf 有，不能用）。"""
    idx, C = P["idx"], P["C"]
    fin = np.isfinite(C)
    first = [idx[fin[:, j].argmax()] if fin[:, j].any() else pd.NaT for j in range(C.shape[1])]
    last = [idx[len(idx) - 1 - fin[::-1, j].argmax()] if fin[:, j].any() else pd.NaT for j in range(C.shape[1])]
    return pd.DataFrame(dict(code=P["cols"], first=first, last=last, n=fin.sum(0)))


def dead_stats(P, life):
    """有資料的已停止交易股：進池天數占比、末 60 日報酬、死前 120 日是否在前 200 池。"""
    idx, Cf, el = P["idx"], P["Cf"], P["elig"][200]
    rows = []
    for _, r in life[(life["last"] < pd.Timestamp(DEAD_BEFORE)) & (life["n"] >= MIN_ROWS)].iterrows():
        j = P["ci"][r["code"]]; li = idx.get_loc(r["last"])
        a = max(li - 60, 0)
        rows.append(dict(code=r["code"], last=r["last"], n=int(r["n"]), pool_days=int(el[:, j].sum()),
                         in_pool_before_death=bool(el[max(li - 120, 0):li + 1, j].any()),
                         ret60=float(Cf[li, j] / Cf[a, j] - 1) if np.isfinite(Cf[a, j]) and Cf[a, j] > 0 else np.nan))
    return pd.DataFrame(rows)


def adjust_equity(eq: pd.Series, trades: pd.DataFrame, q: float, loss: float, n_pos: int = 10) -> pd.Series:
    """於每筆交易出場日把權益乘上 (1 - w*q*(ret-L))。
    w = 1/n_pos（每筆約占權益 1/N）；q = 該筆其實是『缺資料下市股』的機率；L = 該股實際報酬。"""
    if trades is None or len(trades) == 0 or q <= 0:
        return eq
    t = trades.copy(); t["exit"] = pd.to_datetime(t["exit"])
    hit = (1.0 / n_pos) * q * (t["ret"] - loss)
    step = (1 - hit.groupby(t["exit"]).sum()).reindex(eq.index).fillna(1.0)
    return eq * step.cumprod()


def rates(ds: pd.DataFrame):
    """有資料的下市批：進池率 p_pool = 生前曾進過前 200 池（pool_days>0）的代號占比；回傳 (進池率, 末 60 日平均報酬)。"""
    return float((ds["pool_days"] > 0).mean()), float(ds["ret60"].mean())


def clopper_upper(k: int, n: int, conf: float = 0.95) -> float:
    """二項比例的單尾 Clopper-Pearson 上界（k=0 時退化為 1-(1-conf)^(1/n)）。"""
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


def stress_table(res: dict, ds: pd.DataFrame, rho: float = 1.0, s_rate: float | None = None, extreme=(2.0, None)):
    """res[(策略, 窗)] = dict(eq, trades, bench)；ds = 有資料下市批。
    缺資料批代號數 = rho × 該窗內有資料下市批代號數（假設湖外還有同等比例的下市股）。
    期望被選中部位數 k = 缺資料代號數 × p_pool × s；q = k / 該窗交易筆數。"""
    dead_codes = set(ds["code"])
    p_pool, ret60 = rates(ds)
    # 實測選中率：下市批中，生前進過前 200 池的代號，被任一策略任一窗選中過的比例
    # 實測 k=0~1 太少，點估計用 Jeffreys (k+0.5)/(n+1)，避免「0 次 = 風險為 0」的假安心
    pooled = ds[ds["pool_days"] > 0]
    hit = {c for r in res.values() for c in r["trades"]["code"].unique() if c in dead_codes}
    k_hit, n_pool = len(hit & set(pooled["code"])), len(pooled)
    s0 = (k_hit + 0.5) / (n_pool + 1)
    s_up = clopper_upper(k_hit, n_pool)
    s = s0 if s_rate is None else s_rate
    rows = []
    for (sn, wn), r in res.items():
        lo, hi = WINDOWS[wn]
        n_dead_w = int(((ds["last"] >= pd.Timestamp(lo)) & (ds["last"] <= pd.Timestamp(hi))).sum())
        ntr = max(len(r["trades"]), 1)
        b = S.eq_stats(r["bench"])["cagr"]
        scen = {"樂觀（現狀）": (0.0, 0.0), "中度（缺資料批吃末60日平均跌幅）": (None, ret60), "最壞（被選中者 -100%）": (None, -1.0),
                "極端（2倍缺資料、選中率取95%上界、-100%）": ("x", -1.0)}
        for nm, (_, L) in scen.items():
            if nm.startswith("樂觀"):
                k = 0.0
            elif nm.startswith("極端"):
                k = extreme[0] * n_dead_w * p_pool * s_up
            else:
                k = rho * n_dead_w * p_pool * s
            q = min(k / ntr, 1.0)
            e = adjust_equity(r["eq"], r["trades"], q, L)
            st = S.eq_stats(e)
            rows.append(dict(策略=sn, 窗=wn, 情境=nm, 缺資料期望被選中部位數=round(k, 2), q=q, 年化=st["cagr"], 最大回撤=st["mdd"], 同期0050含息=b,
                             超額=st["cagr"] - b, 贏0050=bool(st["cagr"] > b), 交易筆數=len(r["trades"])))
    meta = dict(p_pool=p_pool, ret60=ret60, s_hit=s0, k_hit=k_hit, n_pool=n_pool, s_upper95=s_up, n_dead=len(ds))
    return pd.DataFrame(rows), meta


def main(cache: str | None = None):
    import pickle
    if cache:
        d = pickle.load(open(cache, "rb")); ds, res, fm = d["ds"], d["res"], d["fm"]
    else:
        P = R8.add_features8(FL.load_all()); life = life_table(P); ds = dead_stats(P, life)
        L = fm_codes(); lt = life.set_index("code")
        fm = pd.DataFrame(dict(code=L)); fm["n"] = fm["code"].map(lt["n"]).fillna(0).astype(int)
        res = {}
        for sn, sp in specs().items():
            for wn, (lo, hi) in WINDOWS.items():
                r = R8.run8(P, sp, 200, lo, hi, trades=True)
                res[(sn, wn)] = dict(eq=r["eq"], trades=r["trades"], bench=S.bench(P, lo, hi))
    tab, meta = stress_table(res, ds)
    tab.to_csv(OUT / "survivorship_stress.csv", index=False, encoding="utf-8-sig")
    fm.assign(分類=np.where(fm["n"] == 0, "湖內完全沒有價量", np.where(fm["n"] < MIN_ROWS, "只有零星價量(<250日)", "有完整歷史"))).to_csv(
        OUT / "survivorship_delisted_coverage.csv", index=False, encoding="utf-8-sig")
    json.dump(meta, open(OUT / "survivorship_stress_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return tab, meta, ds, fm


if __name__ == "__main__":
    main()
