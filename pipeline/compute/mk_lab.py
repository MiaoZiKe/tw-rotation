"""MK 策略（股癌 Gooaye 交易邏輯）重現與回測。

來源：Andy 上傳的 Excel（docs/strategy_lab/mk/mk_source.xlsx）：策略規則、台股交易明細、淨值曲線、節目逐集標籤。
原檔引擎（gooaye_backtest.js）沒有附上，所以規則以「策略規則」頁的文字重建，無法逐行對帳的地方在 README 列明原因。

引擎規則（v2 主策略，台股）
  股池     31 檔 AI 供應鏈個股（file31）＋節目題材熱度濾網（近 60 天直接點名，或近 45 天相關題材被提及 >= 3 集）
  進場     收盤 > 50 日線、近 3 個月（63 日）動能 > 0、依動能排名；近 20 日漲幅 > 30% 不追
  分批     首筆買目標部位 50%，下次週調整時「有賺才補滿」
  配置     最多 5 檔：龍頭（動能第一）30%，其餘各 15%，永遠保留 10% 現金；沒填滿的部位停泊在 0050
  停損     連 2 日收盤跌破 60 日線（每天檢查）；停利不設；仍在季線上且動能排名在前半就續抱，跌出前半＝汰弱留強
  大盤濾網 0050 收盤 < 100 日線：個股全出、0050 留 50%；若 0050 距一年高點回落 > 15%，0050 拉到 90%
  頻率     每週最後一個交易日收盤後檢查，隔日成交（原檔＝隔日收盤、我們另跑隔日開盤）
v1：4 檔（40/20/20/20）、停損＝連 5 天收盤下跌、無題材濾網、無 20 日追高限制、股池前 15 檔、跌破 100 日線全數轉 0050。
「純個股版」：0050 的角色全部改成現金（停泊與低水位皆為現金），符合「不持有 0050 或任何 ETF」。
研究用，非買賣建議、不下單。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import swing_lab5 as S  # noqa: E402
from pipeline.compute.strategy_lab import FEE, TAX, SLIP  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "mk"
XLSX = OUT / "mk_source.xlsx"
ETF_TAX = S.ETF_TAX

FILE31 = "2330 2454 2317 2382 3231 6669 2376 3017 3324 3661 3443 2308 2345 2303 3711 2379 2408 2344 2337 8299 2327 2357 4979 3081 3363 2383 3037 2368 1519 1503 2059".split()
FILE15 = FILE31[:15]
# 股票 -> 題材代碼：原檔只說「見逐集標籤頁」但該頁沒有對照表，以下為依公司主要業務的重建（非原檔）。
THEMES = {"2330": "AK", "2454": "A", "2317": "SA", "2382": "SA", "3231": "SA", "6669": "SA", "2376": "SA", "3017": "CS", "3324": "C",
          "3661": "AK", "3443": "AK", "2308": "PC", "2345": "SO", "2303": "A", "3711": "K", "2379": "A", "2408": "M", "2344": "M",
          "2337": "M", "8299": "M", "2327": "B", "2357": "SA", "4979": "O", "3081": "O", "3363": "O", "2383": "B", "3037": "BK",
          "2368": "B", "1519": "P", "1503": "P", "2059": "S"}
THEME_NAME = {"A": "AI", "M": "記憶體", "O": "光通訊", "C": "散熱", "K": "先進封裝", "S": "伺服器", "E": "電動車", "R": "機器人", "P": "電力能源", "B": "PCB材料"}
NAME2CODE = {v: k for k, v in THEME_NAME.items()}
MENTION_MAP = {"TSM": "2330"}          # 節目提到台積電 ADR 視為提到 2330

THEMES_B = dict(THEMES, **{"2317": "S", "2382": "S", "3231": "S", "6669": "S", "2376": "S", "2357": "S", "2379": "", "2303": "", "2454": "A", "3661": "A", "3443": "A", "2330": "AK"})
TMAPS = {"A": THEMES, "B": THEMES_B}

COST = {"file": dict(buy=0.000855, sell=0.003855, slip=0.0, etf_sell=0.003855), "ours": dict(buy=FEE, sell=FEE + TAX, slip=SLIP, etf_sell=FEE + ETF_TAX)}


# ------------------------------------------------------------------ 原檔資料
def load_episodes():
    t = pd.read_excel(XLSX, sheet_name="節目逐集標籤", header=3)
    t["上架日"] = pd.to_datetime(t["上架日"])
    t["codes"] = t["提到的公司（代號）"].fillna("").map(lambda s: [MENTION_MAP.get(x, x) for x in str(s).split()])
    t["themes"] = t["題材"].fillna("").map(lambda s: [NAME2CODE[x] for x in str(s).split("、") if x in NAME2CODE])
    return t[["集數", "上架日", "codes", "themes"]]


def theme_ok(eps, code, check_date, tmap=THEMES):
    """週檢查日 check_date（收盤後）能用的資訊：上架日 < check_date 的集數。"""
    e = eps[eps["上架日"] < check_date]
    if code in set(c for lst in e[e["上架日"] >= check_date - pd.Timedelta(days=60)]["codes"] for c in lst):
        return True
    e45 = e[e["上架日"] >= check_date - pd.Timedelta(days=45)]
    for th in tmap.get(code, ""):
        if sum(1 for lst in e45["themes"] if th in lst) >= 3:
            return True
    return False


def file_reference():
    d = pd.read_excel(XLSX, sheet_name="台股交易明細", header=2)
    d = d.dropna(subset=["代號"]); d["日期"] = pd.to_datetime(d["日期"]); d["代號"] = d["代號"].astype(str)
    nav = pd.read_excel(XLSX, sheet_name="淨值曲線", header=None, skiprows=4)
    nav = nav.iloc[:, 6:11].dropna(how="all"); nav.columns = ["日期", "v1", "v2", "v2無熱度", "0050"]
    nav["日期"] = pd.to_datetime(nav["日期"])
    return d, nav


# ------------------------------------------------------------------ 引擎
V2 = dict(ver="v2", slots=5, weights=(0.30, 0.15, 0.15, 0.15, 0.15), reserve=0.10, stop="ma60x2", mom=63, chase=0.30, ma_entry=50,
          mf_ma=100, low_etf=0.5, panic_etf=0.9, panic_dd=0.15, etf=True, theme=True, pool="file31", fill="close", costs="file")
V1 = dict(V2, ver="v1", slots=4, weights=(0.40, 0.20, 0.20, 0.20), reserve=0.0, stop="down5", chase=None, low_etf=1.0, panic_etf=None, theme=False, pool="file15")


def cfg(base, **kw):
    d = dict(base); d.update(kw); return d


def run_mk(P, spec, lo, hi, eps=None, trades=True):
    idx, cols, ci = P["idx"], P["cols"], P["ci"]
    O, Cf = P["O"], P["Cf"]
    c50, o50 = P["c50"].to_numpy(), P["o50"].to_numpy()
    cost = COST[spec["costs"]]
    T, N = Cf.shape
    lo_i = idx.searchsorted(pd.Timestamp(lo)); hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    cf = pd.DataFrame(Cf, index=idx)
    ma_e = cf.rolling(spec["ma_entry"]).mean().to_numpy()
    ma60 = cf.rolling(60).mean().to_numpy()
    mom = (cf / cf.shift(spec["mom"]) - 1).to_numpy()
    r20 = (cf / cf.shift(20) - 1).to_numpy()
    c50s = pd.Series(c50, index=idx)
    mfma = c50s.rolling(spec["mf_ma"]).mean().to_numpy()
    hi252 = c50s.rolling(252, min_periods=120).max().to_numpy()
    pool_mask = None
    if spec["pool"] in ("file31", "file15"):
        codes = FILE31 if spec["pool"] == "file31" else FILE15
        pool_mask = np.zeros(N, bool)
        for c in codes:
            if c in ci:
                pool_mask[ci[c]] = True
    pit = {"pit200": 200, "pit100": 100}.get(spec["pool"])
    wk = idx.to_period("W-FRI")
    is_week_end = np.array([t + 1 < T and wk[t + 1] != wk[t] for t in range(T)])
    atr = None
    if spec["stop"] == "atr":
        hh = pd.DataFrame(P["H"], index=idx); ll = pd.DataFrame(P["L"], index=idx)
        tr_ = pd.concat([hh - ll, (hh - cf.shift(1)).abs(), (ll - cf.shift(1)).abs()]).groupby(level=0).max()
        atr = tr_.rolling(14).mean().to_numpy()
    use_etf = spec["etf"]

    def fillpx(arr_open, arr_close, t, i, side):
        base = arr_open[t, i] if spec["fill"] == "open" else arr_close[t, i]
        return base * (1 + cost["slip"]) if side == "buy" else base * (1 - cost["slip"])

    cash, sh, etf_sh = 1.0, {}, 0.0
    st = {}                      # i -> dict(first_t, cost_basis, tranche, below_cnt, down_cnt, peak)
    eq = np.full(T, np.nan); expo = np.zeros(T)
    pend_sell, pend_buy, etf_tgt, pend_reason = {}, {}, ((1.0 - spec["reserve"]) if use_etf else None), {}
    log, tr = [], []

    def val(t):
        return cash + sum(sh[i] * Cf[t, i] for i in sh) + etf_sh * c50[t]

    for t in range(lo_i, hi_i + 1):
        # --- 成交（隔日開盤或隔日收盤）
        if pend_sell or pend_buy or etf_tgt is not None:
            for i in list(pend_sell):
                if i in sh and np.isfinite(Cf[t, i]) and np.isfinite(O[t, i]):
                    px = fillpx(O, Cf, t, i, "sell")
                    proceeds = sh[i] * px * (1 - cost["sell"])
                    cash += proceeds
                    s_ = st[i]
                    tr.append(dict(代號=cols[i], 進場日=idx[s_["first_t"]].date(), 進場均價=round(s_["cost_basis"] / s_["shares_bought"], 2), 出場日=idx[t].date(),
                                   出場價=round(px, 2), 報酬=proceeds / s_["cost_basis"] - 1, 持有天數=(idx[t] - idx[s_["first_t"]]).days,
                                   出場原因=pend_reason.get(i, ""), 批次=s_["tranche"]))
                    del sh[i], st[i]
            pend_sell = {}
            if etf_tgt is not None and use_etf and etf_tgt < 0:
                pass
            # ETF 先賣（為買股票與現金保留騰出資金）
            eq_now = val(t) if spec["fill"] == "close" else cash + sum(sh[i] * O[t, i] for i in sh) + etf_sh * o50[t]
            for i, w in list(pend_buy.items()):
                if not (np.isfinite(Cf[t, i]) and np.isfinite(O[t, i])):
                    continue
                amt = eq_now * w
                avail = cash - eq_now * spec["reserve"]
                if avail < amt and etf_sh > 0 and use_etf:
                    need = amt - avail
                    pxe = (o50[t] if spec["fill"] == "open" else c50[t]) * (1 - cost["slip"])
                    sell_sh = min(etf_sh, need / (pxe * (1 - cost["etf_sell"])))
                    cash += sell_sh * pxe * (1 - cost["etf_sell"]); etf_sh -= sell_sh
                    avail = cash - eq_now * spec["reserve"]
                amt = min(amt, max(avail, 0.0))
                if amt <= 0:
                    continue
                px = fillpx(O, Cf, t, i, "buy")
                n_sh = amt / (px * (1 + cost["buy"]))
                cash -= amt
                if i in sh:
                    sh[i] += n_sh; st[i]["cost_basis"] += amt; st[i]["shares_bought"] += n_sh; st[i]["tranche"] = 2
                    log.append(dict(日期=idx[t].date(), 代號=cols[i], 動作="買（補滿）", 價=round(px, 2), 金額=round(amt, 4)))
                else:
                    sh[i] = n_sh
                    st[i] = dict(first_t=t, cost_basis=amt, shares_bought=n_sh, tranche=1, below=0, down=0, peak=px)
                    log.append(dict(日期=idx[t].date(), 代號=cols[i], 動作="買（第1批）", 價=round(px, 2), 金額=round(amt, 4)))
            pend_buy = {}
            if etf_tgt is not None and use_etf:
                eq_now = val(t) if spec["fill"] == "close" else cash + sum(sh[i] * O[t, i] for i in sh) + etf_sh * o50[t]
                want = eq_now * etf_tgt
                cur = etf_sh * (o50[t] if spec["fill"] == "open" else c50[t])
                diff = want - cur
                pb = (o50[t] if spec["fill"] == "open" else c50[t])
                if diff > 0.02 * eq_now:
                    amt = min(diff, max(cash - eq_now * spec["reserve"], 0.0))
                    if amt > 0:
                        px = pb * (1 + cost["slip"]); etf_sh += amt / (px * (1 + cost["buy"])); cash -= amt
                elif -diff > 0.02 * eq_now or etf_tgt == 0 and etf_sh > 0:
                    sell_val = min(cur, -diff) if etf_tgt > 0 else cur
                    px = pb * (1 - cost["slip"]); n_ = min(etf_sh, sell_val / (px * (1 - cost["etf_sell"])))
                    cash += n_ * px * (1 - cost["etf_sell"]); etf_sh -= n_
            etf_tgt = None
        eq[t] = val(t)
        expo[t] = sum(sh[i] * Cf[t, i] for i in sh) / eq[t]
        if t == hi_i:
            break
        # --- 每日停損檢查
        for i in list(sh):
            if i in pend_sell or not np.isfinite(Cf[t, i]):
                continue
            s_ = st[i]
            if spec["stop"] == "ma60x2":
                s_["below"] = s_["below"] + 1 if Cf[t, i] < ma60[t, i] else 0
                if s_["below"] >= 2:
                    pend_sell[i] = 1; pend_reason[i] = "停損：連2日收盤跌破季線"
            elif spec["stop"] == "ma50x2":
                s_["below"] = s_["below"] + 1 if Cf[t, i] < ma_e[t, i] else 0
                if s_["below"] >= 2:
                    pend_sell[i] = 1; pend_reason[i] = "停損：連2日收盤跌破50日線"
            elif spec["stop"] == "down5":
                s_["down"] = s_["down"] + 1 if Cf[t, i] < Cf[t - 1, i] else 0
                if s_["down"] >= 5:
                    pend_sell[i] = 1; pend_reason[i] = "停損：連5天收盤下跌"
            elif spec["stop"] == "under5":
                s_["down"] = s_["down"] + 1 if (t >= 5 and Cf[t, i] < Cf[t - 5, i]) else 0
                if s_["down"] >= 5:
                    pend_sell[i] = 1; pend_reason[i] = "停損：連5天低於5日前收盤"
            elif spec["stop"] == "atr":
                s_["peak"] = max(s_["peak"], Cf[t, i])
                if Cf[t, i] < s_["peak"] - spec["atr_k"] * atr[t, i]:
                    pend_sell[i] = 1; pend_reason[i] = f"停損：自高點回落 {spec['atr_k']} 倍 ATR"
            if spec.get("trail") and i not in pend_sell:
                s_["peak"] = max(s_["peak"], Cf[t, i])
                if Cf[t, i] < s_["peak"] * (1 - spec["trail"]):
                    pend_sell[i] = 1; pend_reason[i] = f"移動停利：自高點回落 {int(spec['trail']*100)}%"
        # --- 每週調整（週最後一個交易日收盤後）
        if not is_week_end[t]:
            continue
        low = bool(np.isfinite(mfma[t]) and c50[t] < mfma[t])
        if low:
            for i in sh:
                if i not in pend_sell:
                    pend_sell[i] = 1; pend_reason[i] = f"大盤濾網：0050 跌破 {spec['mf_ma']} 日線，個股全出"
            panic = spec.get("panic_etf") and np.isfinite(hi252[t]) and c50[t] < (1 - spec["panic_dd"]) * hi252[t]
            etf_tgt = (spec["panic_etf"] if panic else spec["low_etf"]) if use_etf else 0.0
            continue
        # 正常模式：股池、題材濾網、動能排名
        if pool_mask is not None:
            valid = pool_mask.copy()
        else:
            valid = P["elig"][pit][t].copy()
        valid &= np.isfinite(mom[t]) & np.isfinite(ma_e[t]) & np.isfinite(O[min(t + 1, T - 1)])
        if spec["theme"] and eps is not None:
            cd = idx[t]
            for i in np.where(valid)[0]:
                if not theme_ok(eps, cols[i], cd, TMAPS[spec.get("tmap", "A")]):
                    valid[i] = False
        vi = np.where(valid)[0]
        if len(vi) == 0:
            rank_of = {}
        else:
            order = vi[np.argsort(-mom[t][vi])]
            rank_of = {int(i): r for r, i in enumerate(order)}
        half = max(len(vi) // 2, 1) if spec.get("half_mode", "half") == "half" else (spec["slots"] if spec["half_mode"] == "slots" else spec["slots"] + 2)
        for i in list(sh):
            if i in pend_sell:
                continue
            if spec.get("half_rule", spec["stop"] != "down5" and spec["stop"] != "under5"):
                if i not in rank_of or rank_of[i] >= half:
                    pend_sell[i] = 1; pend_reason[i] = "汰弱留強：動能跌出前半名單"
        held = [i for i in sh if i not in pend_sell]
        room = spec["slots"] - len(held)
        cand = [int(i) for i in vi if int(i) not in sh and Cf[t, i] > ma_e[t, i] and mom[t, i] > 0 and
                (spec["chase"] is None or r20[t, i] <= spec["chase"])]
        cand.sort(key=lambda i: -mom[t, i])
        new = cand[:max(room, 0)]
        final = sorted(held + new, key=lambda i: -mom[t, i])
        wmap = {i: spec["weights"][r] for r, i in enumerate(final[:len(spec["weights"])])}
        eq_t = eq[t]
        for i in final:
            tgt = wmap.get(i, spec["weights"][-1])
            if i in new:
                pend_buy[i] = tgt * 0.5
            else:
                s_ = st[i]
                cur_w = sh[i] * Cf[t, i] / eq_t
                gain = sh[i] * Cf[t, i] / s_["cost_basis"] - 1 > 0
                if s_["tranche"] == 1 and gain and tgt - cur_w > 0.01:
                    pend_buy[i] = tgt - cur_w
        if use_etf:
            stock_w = sum(sh[i] * Cf[t, i] for i in held) / eq_t + sum(pend_buy.values())
            etf_tgt = max(0.0, 1.0 - spec["reserve"] - stock_w)
    # 窗尾清倉（只為計算績效）
    end_adj = 0.0
    for i in list(sh):
        s_ = st[i]; px = Cf[hi_i, i] * (1 - cost["slip"])
        end_adj += sh[i] * px * cost["sell"]
        tr.append(dict(代號=cols[i], 進場日=idx[s_["first_t"]].date(), 進場均價=round(s_["cost_basis"] / s_["shares_bought"], 2), 出場日=idx[hi_i].date(),
                       出場價=round(px, 2), 報酬=sh[i] * px * (1 - cost["sell"]) / s_["cost_basis"] - 1,
                       持有天數=(idx[hi_i] - idx[s_["first_t"]]).days, 出場原因="回測結束（強制清倉，非策略訊號）", 批次=s_["tranche"]))
    end_adj += etf_sh * c50[hi_i] * (cost["etf_sell"])
    eq[hi_i] -= end_adj
    s = pd.Series(eq, index=idx).iloc[lo_i:hi_i + 1]
    return dict(eq=s, trades=pd.DataFrame(tr), log=pd.DataFrame(log), expo=float(expo[lo_i:hi_i + 1].mean()))


# ------------------------------------------------------------------ 績效、日誌、實驗
FILE_WIN = ("2023-10-26", "2026-10-22")          # 原檔回測 2023-10-26～2026-10-23；資料湖最後一天是 10-22
TRAIN, INNER, FINAL = ("2012-01-02", "2018-12-31"), ("2019-01-02", "2022-12-30"), ("2023-01-02", "2026-10-22")


def mstats(eq, P, lo, hi):
    s, b = S.eq_stats(eq), S.eq_stats(S.bench(P, lo, hi))
    y, by = S.yearly(eq), S.yearly(S.bench(P, lo, hi))
    return dict(total=float(eq.iloc[-1] - 1), cagr=s["cagr"], mdd=s["mdd"], sharpe=s["sharpe"], bh=b["cagr"], bh_mdd=b["mdd"], bh_total=float(S.bench(P, lo, hi).iloc[-1] - 1),
                excess=s["cagr"] - b["cagr"], yrs=json.dumps({int(k): round(float(v), 3) for k, v in y.items()}), y0050=json.dumps({int(k): round(float(v), 3) for k, v in by.items()}),
                ywin=int((y > by.reindex(y.index)).sum()), ynum=len(y))


def weights_for(slots, leader=0.30, reserve=0.10):
    rest = (1 - reserve - leader) / (slots - 1)
    return tuple([leader] + [rest] * (slots - 1))


REASON_NOTE = {
    "停損": "停損出場：限制單筆虧損；代價是洗出後該股可能反彈（MK 說不要死板執行停損，所以用季線這種慢指標）。",
    "汰弱留強": "動能排名跌出前半被換掉：屬於「強者恆強」的輪替；檢討重點是被換掉後原持股是否繼續漲（名單輪替太快會砍到贏家）。",
    "大盤濾網": "0050 跌破 100 日線，個股全出：保護性出場；若隨後快速反彈就是濾網錯殺成本。",
    "移動停利": "自高點回落觸發的停利：鎖住獲利；代價是趨勢尚未結束時被洗出。",
    "回測結束": "回測結束的強制清倉，只為計算績效，不是策略訊號。",
}


def critique(t, p50):
    note = next((v for k, v in REASON_NOTE.items() if k in t["出場原因"]), "")
    out = "賺" if t["報酬"] > 0.05 else ("小賺小賠" if t["報酬"] > -0.05 else ("虧損" if t["報酬"] > -0.2 else "大虧"))
    return f"{out}（{t['報酬']*100:+.1f}%），{'跑贏' if t['報酬'] > p50 else '輸給'}同期 0050（{p50*100:+.1f}%）。{note}"


def annotate(P, tr):
    if tr.empty:
        return tr
    c50, o50 = P["c50"], P["o50"]
    p = []
    for _, r in tr.iterrows():
        a, b = pd.Timestamp(r["進場日"]), pd.Timestamp(r["出場日"])
        p.append(c50.loc[b] / o50.loc[a] - 1 if a in o50.index and b in c50.index else np.nan)
    tr = tr.copy(); tr["同期0050報酬"] = p
    tr["檢討"] = [critique(r, r["同期0050報酬"]) for _, r in tr.iterrows()]
    return tr


def go(P, eps, spec, lo, hi, name, group, rows, store=None):
    r = run_mk(P, spec, lo, hi, eps)
    row = dict(名稱=name, 類別=group, 區間=f"{lo}~{hi}", 交易筆數=len(r["trades"]), 平均持股比例=r["expo"], **mstats(r["eq"], P, lo, hi))
    rows.append(row)
    if store is not None:
        store[name] = r
    return r


HOLDLOG = OUT / "holdout_log.csv"


def holdout_once(P, eps, spec, window, lo, hi, tag):
    """保留期只跑一次：同一個 (tag, window) 已有紀錄就只讀紀錄。"""
    log = pd.read_csv(HOLDLOG) if HOLDLOG.exists() else pd.DataFrame(columns=["tag", "window"])
    hit = log[(log["tag"] == tag) & (log["window"] == window)]
    if len(hit):
        return hit.iloc[0].to_dict()
    r = run_mk(P, spec, lo, hi, eps)
    row = dict(tag=tag, window=window, lo=lo, hi=hi, 交易筆數=len(r["trades"]), 平均持股比例=r["expo"], **mstats(r["eq"], P, lo, hi))
    pd.concat([log, pd.DataFrame([row])], ignore_index=True).to_csv(HOLDLOG, index=False, encoding="utf-8-sig")
    return row


def run_all():
    OUT.mkdir(parents=True, exist_ok=True)
    P = S.build_features(S.load5())
    eps = load_episodes()
    ref, nav = file_reference()
    ours = dict(fill="open", costs="ours")
    # ---------- 1. 重現（台股 v1、v2、v2 無熱度；原檔窗）
    rows = []; keep = {}
    for nm, base in (("v1", V1), ("v2", V2), ("v2 無熱度", cfg(V2, theme=False))):
        for fill, costs, lab in (("close", "file", "隔日收盤成交＋原檔成本"), ("open", "file", "隔日開盤成交＋原檔成本"), ("open", "ours", "隔日開盤成交＋我們的成本（含滑價）")):
            go(P, eps, cfg(base, fill=fill, costs=costs), *FILE_WIN, f"{nm}｜{lab}", "重現", rows, keep)
    pd.DataFrame(rows).to_csv(OUT / "1_reproduction.csv", index=False, encoding="utf-8-sig")
    # 規則解讀歧義的敏感度（逐一列出）
    g = []
    for tm in ("A", "B"):
        for hm in ("half", "slots", "slots+2"):
            go(P, eps, cfg(V2, tmap=tm, half_mode=hm), *FILE_WIN, f"v2｜題材對照{tm}｜汰弱門檻={hm}", "解讀敏感度", g)
    for hm in ("half", "slots", "slots+2"):
        go(P, eps, cfg(V2, theme=False, half_mode=hm), *FILE_WIN, f"v2 無熱度｜汰弱門檻={hm}", "解讀敏感度", g)
    for stp in ("down5", "under5"):
        for hr in (False, True):
            go(P, eps, cfg(V1, stop=stp, half_rule=hr), *FILE_WIN, f"v1｜停損={stp}｜加汰弱規則={hr}", "解讀敏感度", g)
    pd.DataFrame(g).to_csv(OUT / "1b_interpretation_sensitivity.csv", index=False, encoding="utf-8-sig")
    # ---------- 2. 偏誤：同規則換股池、純個股版（原檔窗，開盤成交＋我們的成本）
    b = []
    for pool in ("file31", "pit200", "pit100"):
        for etf in (True, False):
            go(P, eps, cfg(V2, theme=False, pool=pool, etf=etf, **ours), *FILE_WIN, f"v2 無熱度｜股池={pool}｜{'含 0050 停泊（原版）' if etf else '純個股（現金）'}", "偏誤", b, keep)
    go(P, eps, cfg(V2, theme=True, pool="file31", etf=False, **ours), *FILE_WIN, "v2 有熱度｜股池=file31｜純個股（現金）", "偏誤", b, keep)
    pd.DataFrame(b).to_csv(OUT / "2_bias.csv", index=False, encoding="utf-8-sig")
    # ---------- 3. 拉長：2012～今（pit 前 200／100、純個股、無題材濾網）
    L = []
    base = cfg(V2, theme=False, pool="pit200", etf=False, **ours)
    for nm, sp in (("v2 純個股 pit200", base), ("v2 純個股 pit100", cfg(base, pool="pit100")),
                   ("v1 純個股 pit200", cfg(V1, theme=False, pool="pit200", etf=False, **ours)),
                   ("v2 含 0050 停泊 pit200（僅供對照，不合規）", cfg(base, etf=True))):
        for w, (lo, hi) in (("訓練 2012-2018", TRAIN), ("內部保留 2019-2022", INNER), ("最終 2023-2026（已被看過）", FINAL), ("全期 2012-2026", ("2012-01-02", "2026-10-22"))):
            go(P, eps, sp, lo, hi, f"{nm}｜{w}", "長回測", L, keep)
    pd.DataFrame(L).to_csv(OUT / "3_long_backtest.csv", index=False, encoding="utf-8-sig")
    return P, eps, keep


def opt_variants(base):
    v = []
    for k in (3, 4):
        v.append(("停損", f"ATR 追蹤停損 {k} 倍", cfg(base, stop="atr", atr_k=k)))
    v.append(("停損", "連 2 日跌破 50 日線", cfg(base, stop="ma50x2")))
    for tr_ in (0.15, 0.25, 0.35):
        v.append(("移動停利", f"自高點回落 {int(tr_*100)}% 停利（疊加原停損）", cfg(base, trail=tr_)))
    for sl in (3, 8, 10):
        v.append(("持股數", f"{sl} 檔（龍頭 30%，其餘均分）", cfg(base, slots=sl, weights=weights_for(sl))))
    for m in (21, 126, 252):
        v.append(("動能週期", f"{m} 日動能", cfg(base, mom=m)))
    for c in (0.15, 0.50, None):
        v.append(("追高門檻", "不設限" if c is None else f"近 20 日漲幅 > {int(c*100)}% 不進", cfg(base, chase=c)))
    for ma in (50, 150, 200):
        v.append(("大盤濾網", f"0050 跌破 {ma} 日線", cfg(base, mf_ma=ma)))
    v.append(("大盤濾網", "不設大盤濾網（只靠個股停損）", cfg(base, mf_ma=1)))
    v.append(("汰弱規則", "取消『動能跌出前半』汰弱", cfg(base, half_rule=False)))
    v.append(("汰弱規則", "汰弱門檻放寬為前 7 名", cfg(base, half_mode="slots+2")))
    return v


def optimize(P, eps):
    base = cfg(V2, theme=False, pool="pit200", etf=False, fill="open", costs="ours")
    rows = []
    store = {}
    for pool in (200, 100):
        b = cfg(base, pool=f"pit{pool}")
        go(P, eps, b, *TRAIN, f"基準（原規則）｜pit{pool}", "基準", rows, store)
        for factor, label, sp in opt_variants(b):
            go(P, eps, sp, *TRAIN, f"{factor}：{label}｜pit{pool}", factor, rows, store)
    df = pd.DataFrame(rows)
    df["池"] = df["名稱"].str.extract(r"pit(\d+)")[0]
    b0 = df[df["類別"] == "基準"].set_index("池")
    df["相對基準年化變化"] = df.apply(lambda r: r["cagr"] - b0.loc[r["池"], "cagr"], axis=1)
    df["相對基準回撤變化"] = df.apply(lambda r: r["mdd"] - b0.loc[r["池"], "mdd"], axis=1)
    df.to_csv(OUT / "4_optimization_train.csv", index=False, encoding="utf-8-sig")
    return df, base


def pick_combined(df, base):
    """每個因子選「兩個池訓練期年化的最小改善量」最大且 >= +1 個百分點、回撤不惡化超過 5 個百分點者；否則維持原規則。"""
    chosen = {}
    for factor in df["類別"].unique():
        if factor == "基準":
            continue
        best, bs = None, 0.01
        for lab in df[df["類別"] == factor]["名稱"].str.replace(r"｜pit\d+", "", regex=True).unique():
            sub = df[df["名稱"].str.startswith(lab + "｜pit")]
            if len(sub) != 2:
                continue
            imp = sub["相對基準年化變化"].min(); dd = sub["相對基準回撤變化"].min()
            if imp > bs and dd > -0.05:
                best, bs = lab, imp
        if best:
            chosen[factor] = best
    return chosen


def explore_combos(P, eps, base):
    """單因子都沒有「兩池皆 >= +1pt」者，改做探索性組合（只用訓練期，供參考；訓練期沒贏 0050 就不開保留期）。"""
    rows = []
    for pool in (200, 100):
        b = cfg(base, pool=f"pit{pool}")
        combos = {
            "組合 X：連2日跌破50日線＋不設追高門檻": cfg(b, stop="ma50x2", chase=None),
            "組合 Y：X＋取消汰弱規則": cfg(b, stop="ma50x2", chase=None, half_rule=False),
            "組合 Z：Y＋8 檔": cfg(b, stop="ma50x2", chase=None, half_rule=False, slots=8, weights=weights_for(8)),
            "組合 W：Y＋大盤濾網改 200 日線": cfg(b, stop="ma50x2", chase=None, half_rule=False, mf_ma=200),
        }
        for nm, sp in combos.items():
            go(P, eps, sp, *TRAIN, f"{nm}｜pit{pool}", "探索性組合", rows)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "4b_exploratory_combos_train.csv", index=False, encoding="utf-8-sig")
    return df


def finish():
    """產生對帳表、逐筆交易（含檢討）、保留期紀錄。"""
    P = S.build_features(S.load5()); eps = load_episodes(); ref, nav = file_reference()
    # --- 對帳：原檔數字 vs 我們（隔日收盤成交＋原檔成本，最接近原檔設定）
    fileval = {"v1": dict(total=1.563, cagr=0.370, mdd=-0.393, sharpe=1.07, trades=79, yrs=[0.067, 0.301, 0.361, 0.357]),
               "v2": dict(total=1.590, cagr=0.374, mdd=-0.295, sharpe=1.13, trades=75, yrs=[0.059, 0.294, 0.491, 0.267]),
               "v2 無熱度": dict(total=2.315, cagr=0.493, mdd=-0.333, sharpe=1.27, trades=77, yrs=None),
               "0050": dict(total=2.763, cagr=0.557, mdd=-0.275, sharpe=None, trades=None, yrs=[0.113, 0.486, 0.369, 0.663])}
    rep = pd.read_csv(OUT / "1_reproduction.csv")
    rows = []
    for nm, fv in fileval.items():
        if nm == "0050":
            b = P["c50"][FILE_WIN[0]:FILE_WIN[1]]; e = b / b.iloc[0]
            s = S.eq_stats(e); ours = dict(total=float(e.iloc[-1] - 1), cagr=s["cagr"], mdd=s["mdd"], sharpe=s["sharpe"], trades=None, yrs=list(S.yearly(e).round(3)))
        else:
            r = rep[rep["名稱"] == f"{nm}｜隔日收盤成交＋原檔成本"].iloc[0]
            ours = dict(total=r["total"], cagr=r["cagr"], mdd=r["mdd"], sharpe=r["sharpe"], trades=int(r["交易筆數"]), yrs=list(json.loads(r["yrs"]).values()))
        rows.append(dict(策略=nm, 原檔總報酬=fv["total"], 我們總報酬=ours["total"], 原檔年化=fv["cagr"], 我們年化=ours["cagr"], 原檔MDD=fv["mdd"], 我們MDD=ours["mdd"],
                         原檔夏普=fv["sharpe"], 我們夏普=ours["sharpe"], 原檔交易筆數=fv["trades"], 我們交易筆數=ours["trades"],
                         原檔逐年=str(fv["yrs"]), 我們逐年=str(ours["yrs"])))
    pd.DataFrame(rows).to_csv(OUT / "1c_reconciliation.csv", index=False, encoding="utf-8-sig")
    # --- 首批進場對帳
    r = run_mk(P, cfg(V2, fill="close", costs="file"), *FILE_WIN, eps)
    ours_first = r["log"].head(12).assign(來源="我們")
    ref_first = ref[ref["買/賣"] == "買"].head(12).rename(columns={"日期": "日期", "代號": "代號", "成交價": "價", "原因": "動作"})[["日期", "代號", "價", "動作"]].assign(來源="原檔")
    pd.concat([ref_first, ours_first[["日期", "代號", "價", "動作", "來源"]]]).to_csv(OUT / "1d_first_trades_compare.csv", index=False, encoding="utf-8-sig")
    # --- 逐筆交易（含檢討）：重現 v2、純個股版長回測（內部保留與最終）
    annotate(P, r["trades"]).assign(版本="v2 重現（收盤成交＋原檔成本）").to_csv(OUT / "trades_v2_reproduction.csv", index=False, encoding="utf-8-sig")
    base = cfg(V2, theme=False, pool="pit200", etf=False, fill="open", costs="ours")
    out = []
    for w, (lo, hi) in (("訓練 2012-2018", TRAIN), ("內部保留 2019-2022", INNER), ("最終 2023-2026（已被看過）", FINAL)):
        rr = run_mk(P, base, lo, hi, eps)
        out.append(annotate(P, rr["trades"]).assign(版本="v2 純個股 pit200", 區間=w))
    pd.concat(out).to_csv(OUT / "trades_pure_pit200.csv", index=False, encoding="utf-8-sig")
    # --- 保留期紀錄（原規則、未經優化；各只跑一次）
    for w, (lo, hi) in (("內部保留 2019-2022", INNER), ("最終 2023-2026（已被看過）", FINAL)):
        for pool in ("pit200", "pit100"):
            holdout_once(P, eps, cfg(base, pool=pool), w, lo, hi, f"原規則 v2 純個股 {pool}")
    return P


if __name__ == "__main__":
    P, eps, keep = run_all()
    df, base = optimize(P, eps)
    explore_combos(P, eps, base)
    finish()
