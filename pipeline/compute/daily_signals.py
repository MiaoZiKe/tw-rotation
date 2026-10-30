"""日線找訊號：用日級資料找「未來可能被資金關注」的族群與個股，並誠實回測（流向驗證頁「找訊號」區）。

★ 為什麼有這一支（Andy 2026-10-30：「這邊是負責找訊號的，找的訊號不只是當天，也可以拿日級別資訊去找未來潛在個股」）。
  先前研究（docs/research/20261030_flow_vs_price.md）：資金占比與當天走勢同向 62%，部分是機械性的；
  盤中領先訊號 16 組都沒通過多重比較。這裡改用日線，問的是：「訊號出現的『隔天開盤』買進，
  之後 5／10／20 日有沒有比大盤多賺？」—— 答案不好就照寫，不調門檻。

紅線（本支遵守的）
  · 訊號一律收盤後產生、隔天開盤成交：未來報酬 ＝ 第 t+1 日「開盤→收盤」×（t+2…t+h 的收盤報酬），
    t 日及以前的資訊只用來產生訊號。tests/test_daily_signals.py 驗「砍掉未來資料後，訊號不變」。
  · 規則與門檻**事先寫死**（見 RULES），不看結果調整。訓練期（TRAIN_END 以前）只用來看方向是否一致，
    判定「站得住」只看樣本外（TEST_START 起），且要過 Holm 多重比較校正。
  · 扣成本 0.47%／趟（買 0.1425%＋賣 0.1425%＋證交稅 0.3%，不打折，保守）。
  · 樣本數、信賴區間、隨機基準一律隨數字輸出。
  · 只讀資料湖，不寫 data/*.parquet。

口徑
  · 報酬用官方「漲跌／前收」（除權息日以參考價為基準，等於不含股利，但不會把除息當成下跌），
    開盤→收盤用 close/open−1（不受除權息影響）。
  · 族群報酬＝成員報酬以「前一日成交值 ÷ 該股所屬族群數」加權（與 flow.group_daily 同口徑，無前視）；
    大盤基準＝全市場個股以前一日成交值加權。
  · 超額報酬 ＝ 標的報酬 − 大盤報酬（同一段持有期）。族群報酬是加權籃子，扣成本時沿用同樣 0.47% 當近似。
  · 個股只看 20 日均成交值 > 1 億、四位數代號的普通股。
  · 事件去重：同一標的、同一規則，觸發後 10 個交易日內不重算（避免連續觸發灌水樣本）。

已知限制（也寫進輸出的 meta.limits）
  · 族群成分用「現在的」groups.yaml 套到歷史（族群成分不隨時間變）→ 有成分回填偏誤。
  · 下市股在資料湖裡只到最後一個交易日，未來報酬缺值被剔除 → 存活者偏差（低估踩雷損失）。
  · 隔天開盤若鎖漲停買不到，回測仍當成買得到 → 對「剛爆量的強勢股」略樂觀。
  · 事件在橫斷面上高度相關（同一天很多檔一起觸發），所以信賴區間用「以日期為單位的區塊自助法」，
    p 值用「同日期、同檔數的隨機抽樣基準」，不是把每筆當獨立樣本。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from . import flow
from .money_wheel import money_axes
from .rrg import quadrant_of, rrg_axes

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- 事先寫死的參數（不准看結果調）
START = "2020-01-01"          # 回測資料起點（含 2020 疫情、2022 空頭、2023-25 多頭）
TRAIN_END = "2023-12-31"      # 訓練期結束；之後為樣本外
TEST_START = "2024-01-01"
HORIZONS = (5, 10, 20)
COST_PCT = 0.47               # 每趟（買＋賣）成本，百分點
COOLDOWN = 10                 # 同標的同規則的去重天數
LIQ_MIN = 1e8                 # 個股 20 日均成交值門檻（元）
GROUP_MIN_SHARE = 0.3         # 族群當日成交值占全市場 % 的門檻（同資金輪盤）
GROUP_MIN_MEMBERS = 3
RAND_REPS = 2000
BOOT_REPS = 1000
SEED = 20261030
RECENT_DAYS = 60
STOCK_CAP_PER_RULE_DAY = 10   # 近 60 日清單每天每條規則最多列幾檔個股（回測統計不受此限）

S1_RISE_DAYS = 3              # 資金占比連續上升日數
S2_BUY_DAYS = 5               # 法人連買日數
S2_HIGH_WIN = 20              # 「未突破」的高點窗口
S3_RATIO = 1.5                # 5 日均成交值／20 日均成交值
S3_BAND = 3.0                 # 5 日漲跌幅絕對值上限（%）
REL_WIN = 5                   # 相對大盤累積漲幅窗口

RULES = [
    {"id": "G1", "level": "group", "name": "資金先行：占比連升、價格未表態",
     "text": "族群成交值占全市場的比重連續 3 日上升，且近 5 日漲幅不超過大盤（相對大盤 ≤ 0）。"},
    {"id": "S1", "level": "stock", "name": "資金先行：占比連升、價格未表態",
     "text": "個股成交值占全市場的比重連續 3 日上升，且近 5 日漲幅不超過大盤（相對大盤 ≤ 0）。"},
    {"id": "G2", "level": "group", "name": "法人連買、價格未突破",
     "text": "族群的外資＋投信合計買超連續 5 日為正，且族群指數仍未突破前 20 日高點。"},
    {"id": "S2", "level": "stock", "name": "法人連買、價格未突破",
     "text": "個股的外資＋投信合計買超連續 5 日為正，且股價仍未突破前 20 日高點。"},
    {"id": "G3", "level": "group", "name": "量增價穩",
     "text": "族群成交值 5 日均 ÷ 20 日均 > 1.5，且近 5 日漲跌幅在 ±3% 內。"},
    {"id": "S3", "level": "stock", "name": "量增價穩",
     "text": "個股成交值 5 日均 ÷ 20 日均 > 1.5，且近 5 日漲跌幅在 ±3% 內。"},
    {"id": "G4", "level": "group", "name": "資金輪盤：升溫 → 集中",
     "text": "資金輪盤（成交值占比版）的族群由「升溫（改善）」象限進入「集中（領先）」象限的那一天。"},
    {"id": "G5", "level": "group", "name": "強弱輪動：改善 → 領先（對照組）",
     "text": "強弱輪動（價格相對大盤）的族群由「改善」象限進入「領先」象限的那一天；用來對照資金版是否更有用。"},
]
RULE_BY_ID = {r["id"]: r for r in RULES}


# ================================================================== 資料面板
def _pairs(price: pd.DataFrame, company: pd.DataFrame) -> pd.DataFrame:
    """代號 → 所屬族群與權重（沿用 flow._attach_groups：題材族群＋產業別補底、一檔股票成交值平分給各族群）。"""
    one = price[["code"]].drop_duplicates().copy()
    one["date"] = "2000-01-01"
    d = flow._attach_groups(one, company)
    return d[["code", "group_id", "group_name", "chain", "weight"]].reset_index(drop=True)


def build_panel(price: pd.DataFrame, inst: pd.DataFrame, company: pd.DataFrame,
                start: str = START) -> dict:
    """寬表面板（日期 × 代號）。回傳 dict：dates、codes、cc、oc、tv、net、M（代號×族群權重）、groups。"""
    p = price[["date", "code", "open", "close", "change", "turnover"]].copy()
    p["date"] = p["date"].astype(str)
    p = p[p["date"] >= start]
    p["code"] = p["code"].astype(str)
    pairs = _pairs(p, company)
    p = p[p["code"].isin(set(pairs["code"]))]
    for c in ("open", "close", "change", "turnover"):
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p = p[p["close"] > 0].drop_duplicates(["date", "code"], keep="last")   # 收盤 0＝沒成交（同 fundamental.clean_price）

    def wide(col: str) -> pd.DataFrame:
        return p.pivot(index="date", columns="code", values=col).sort_index()

    close, opn, chg, tv = wide("close"), wide("open"), wide("change"), wide("turnover")
    pc = close - chg.fillna(0)
    cc = (chg / pc).where(pc > 0)
    cc = cc.where(cc.abs() < 0.5)                              # >50% 多半是資料錯誤或換股，剔除
    oc = (close / opn - 1).where(opn > 0)
    oc = oc.where(oc.abs() < 0.25)

    net = None
    if inst is not None and not inst.empty:
        i = inst[["date", "code", "foreign_total", "trust"]].copy()
        i["date"] = i["date"].astype(str)
        i = i[(i["date"] >= start)].drop_duplicates(["date", "code"], keep="last")
        i["code"] = i["code"].astype(str)
        i["net"] = pd.to_numeric(i["foreign_total"], errors="coerce").fillna(0) + pd.to_numeric(i["trust"], errors="coerce").fillna(0)
        net = i.pivot(index="date", columns="code", values="net").reindex(index=close.index, columns=close.columns)
    else:
        net = pd.DataFrame(np.nan, index=close.index, columns=close.columns)

    gids = list(dict.fromkeys(pairs["group_id"]))
    gi = {g: k for k, g in enumerate(gids)}
    ci = {c: k for k, c in enumerate(close.columns)}
    M = np.zeros((len(close.columns), len(gids)))
    for code, gid, w in zip(pairs["code"], pairs["group_id"], pairs["weight"]):
        if code in ci:
            M[ci[code], gi[gid]] = w
    gmeta = pairs.drop_duplicates("group_id").set_index("group_id")[["group_name", "chain"]].reindex(gids)
    return {"dates": list(close.index), "codes": list(close.columns), "cc": cc, "oc": oc,
            "tv": tv, "net": net, "M": M, "groups": gmeta, "pairs": pairs}


def _wavg(w: pd.DataFrame, r: pd.DataFrame, M: np.ndarray | None = None):
    """以 w 為權重的加權平均報酬。M 為 None → 全市場一條序列；否則 → 各族群一欄。r 缺值的列不進分母。"""
    ok = r.notna().to_numpy()
    wv = np.nan_to_num(w.to_numpy(dtype=float)) * ok
    rv = np.nan_to_num(r.to_numpy(dtype=float))
    if M is None:
        den = wv.sum(axis=1)
        return pd.Series(np.where(den > 0, (wv * rv).sum(axis=1) / np.where(den > 0, den, 1), np.nan), index=r.index)
    num, den = (wv * rv) @ M, wv @ M
    return pd.DataFrame(np.where(den > 0, num / np.where(den > 0, den, 1), np.nan), index=r.index)


def entity_series(panel: dict) -> dict:
    """算出大盤與族群的報酬／成交值／占比／法人淨買；個股直接用面板。"""
    cc, oc, tv, net, M = panel["cc"], panel["oc"], panel["tv"], panel["net"], panel["M"]
    w_prev = tv.shift(1)                       # 前一日成交值當權重：收盤前就已知，無前視
    mk_cc, mk_oc = _wavg(w_prev, cc), _wavg(w_prev, oc)
    g_cc = _wavg(w_prev, cc, M)
    g_oc = _wavg(w_prev, oc, M)
    gids = list(panel["groups"].index)
    for d in (g_cc, g_oc):
        d.columns = gids
    tvv = np.nan_to_num(tv.to_numpy(dtype=float))
    g_tv = pd.DataFrame(tvv @ M, index=tv.index, columns=gids)
    tot = g_tv.sum(axis=1)
    g_share = g_tv.div(tot.where(tot > 0), axis=0) * 100
    nv = net.to_numpy(dtype=float)
    has = (np.isfinite(nv).astype(float) @ (M > 0).astype(float)) > 0
    g_net = pd.DataFrame(np.where(has, np.nan_to_num(nv) @ M, np.nan), index=net.index, columns=gids)
    cnt = pd.DataFrame((tvv > 0).astype(float) @ (M > 0).astype(float), index=tv.index, columns=gids)
    s_share = tv.div(tv.sum(axis=1).where(lambda s: s > 0), axis=0) * 100
    return {"mk_cc": mk_cc, "mk_oc": mk_oc, "g_cc": g_cc, "g_oc": g_oc, "g_tv": g_tv,
            "g_share": g_share, "g_net": g_net, "g_cnt": cnt, "s_share": s_share}


# ================================================================== 訊號（只用 t 日及以前）
def _level(cc: pd.DataFrame) -> pd.DataFrame:
    return np.exp(np.log1p(cc.fillna(0)).cumsum())


def _ret(level: pd.DataFrame, n: int) -> pd.DataFrame:
    return level / level.shift(n) - 1


def flags_basic(cc: pd.DataFrame, tv: pd.DataFrame, net: pd.DataFrame, share: pd.DataFrame,
                mk_cc: pd.Series) -> dict:
    """三條共用規則（資金先行／法人連買／量增價穩）的布林表。族群與個股共用同一份實作，口徑不會兩套。

    所有運算都是「rolling／shift(正數)」，t 日的值只看 t 日及以前 —— 測試用截斷未來來驗。"""
    lv = _level(cc)
    mk = np.exp(np.log1p(mk_cc.fillna(0)).cumsum())
    ret5 = _ret(lv, REL_WIN)
    rel5 = ret5.sub(mk / mk.shift(REL_WIN) - 1, axis=0)
    # G1/S1：占比連續上升（每一天都比前一天高）且價格還沒跑贏大盤
    rising = (share.diff() > 0).astype(float).where(share.diff().notna())
    c1 = (rising.rolling(S1_RISE_DAYS, min_periods=S1_RISE_DAYS).min() == 1) & (rel5 <= 0)
    # G2/S2：外資＋投信連買，且今天收盤指數沒有高過「前 20 日」最高（不含今天）
    pos = (net > 0).astype(float).where(net.notna())
    prior_high = lv.shift(1).rolling(S2_HIGH_WIN, min_periods=S2_HIGH_WIN).max()
    c2 = (pos.rolling(S2_BUY_DAYS, min_periods=S2_BUY_DAYS).min() == 1) & (lv <= prior_high)
    # G3/S3：量增（5 日均/20 日均 > 1.5）而價穩（5 日漲跌 ±3% 內）
    t5 = tv.rolling(5, min_periods=5).mean()
    t20 = tv.rolling(20, min_periods=20).mean()
    ratio = t5 / t20
    c3 = (ratio > S3_RATIO) & (ret5.abs() <= S3_BAND / 100)
    strength = {"1": share / share.shift(S1_RISE_DAYS),
                "2": net.rolling(S2_BUY_DAYS, min_periods=S2_BUY_DAYS).sum(),
                "3": ratio}
    return {"1": c1.fillna(False), "2": c2.fillna(False), "3": c3.fillna(False), "strength": strength,
            "ret5": ret5, "rel5": rel5, "ratio": ratio}


def flags_quadrant(g_share: pd.DataFrame, g_cc: pd.DataFrame, mk_cc: pd.Series) -> dict:
    """G4（資金輪盤）與 G5（強弱輪動）：由「改善」象限進入「領先」象限的那一天。"""
    # 資金輪盤
    long = g_share.stack(future_stack=True).rename("turnover_share").reset_index()
    long.columns = ["date", "group_id", "turnover_share"]
    long = long.sort_values(["group_id", "date"])
    ax = money_axes(long)
    q4 = _quad_wide(ax, "x", "y", g_share)
    # 強弱輪動：族群指數 / 大盤指數
    gl = _level(g_cc)
    ml = np.exp(np.log1p(mk_cc.fillna(0)).cumsum())
    st = gl.stack(future_stack=True).rename("gi").reset_index()
    st.columns = ["date", "group_id", "gi"]
    st["bi"] = st["date"].map(ml)
    st = st.sort_values(["group_id", "date"])
    ax2 = rrg_axes(st, "group_id")
    q5 = _quad_wide(ax2, "rs_ratio", "rs_mom", g_share)

    def enter(q: pd.DataFrame) -> pd.DataFrame:
        return (q == "improving") .shift(1, fill_value=False) & (q == "leading")
    return {"4": enter(q4), "5": enter(q5), "q4": q4, "q5": q5}


def _quad_wide(ax: pd.DataFrame, xc: str, yc: str, like: pd.DataFrame) -> pd.DataFrame:
    ax = ax.dropna(subset=[xc, yc]).copy()
    ax["q"] = [quadrant_of(x, y) for x, y in zip(ax[xc], ax[yc])]
    w = ax.pivot(index="date", columns="group_id", values="q").reindex(index=like.index, columns=like.columns)
    return w.fillna("")


# ================================================================== 未來報酬（隔天開盤進場）
def forward_excess(cc: pd.DataFrame, oc: pd.DataFrame, mk_cc: pd.Series, mk_oc: pd.Series, h: int) -> pd.DataFrame:
    """第 t 日收盤後出訊號 → t+1 開盤進、t+h 收盤出的報酬，減去大盤同一段（單位：%）。

    報酬 ＝ (1 + 第 t+1 日開→收) × Π(1 + 第 t+2…t+h 日收盤報酬) − 1。
    出場日收盤沒有價（停牌／下市）→ 缺值，不補 0。"""
    def fwd(c: pd.DataFrame, o: pd.DataFrame) -> pd.DataFrame:
        L = np.log1p(c.fillna(0)).cumsum()
        r = (1 + o.shift(-1)) * np.exp(L.shift(-h) - L.shift(-1)) - 1
        return r.where(o.shift(-1).notna() & c.shift(-h).notna())
    fe = fwd(cc, oc)
    fm = fwd(mk_cc.to_frame("m"), mk_oc.to_frame("m"))["m"]
    return fe.sub(fm, axis=0) * 100


# ================================================================== 事件、統計
def cooldown_events(flag: pd.DataFrame, gap: int = COOLDOWN) -> pd.DataFrame:
    """同一標的觸發後 gap 個交易日內不重算。回傳與 flag 同形的布林表。"""
    a = flag.to_numpy(dtype=bool)
    out = np.zeros_like(a)
    for j in range(a.shape[1]):
        last = -10**9
        for i in np.flatnonzero(a[:, j]):
            if i - last > gap:
                out[i, j] = True
                last = i
    return pd.DataFrame(out, index=flag.index, columns=flag.columns)


def _holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = np.argsort(ps)
    adj = [0.0] * m
    run = 0.0
    for rank, k in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[k]))
        adj[k] = run
    return adj


def _block_boot_ci(S: np.ndarray, N: np.ndarray, H: np.ndarray, block: int, rng) -> dict:
    """以日期為單位的區塊自助法（區塊長＝持有天數，吸收重疊持有期的自相關）。S／N／H 為每個日期的超額總和／事件數／命中數。"""
    D = len(S)
    if D == 0 or N.sum() == 0:
        return {}
    k = int(np.ceil(D / block))
    starts = rng.integers(0, D, size=(BOOT_REPS, k))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % D
    idx = idx.reshape(BOOT_REPS, -1)
    n = N[idx].sum(axis=1)
    ok = n > 0
    mean = S[idx].sum(axis=1)[ok] / n[ok]
    hit = H[idx].sum(axis=1)[ok] / n[ok]
    return {"mean": (float(np.percentile(mean, 2.5)), float(np.percentile(mean, 97.5))),
            "hit": (float(np.percentile(hit, 2.5)), float(np.percentile(hit, 97.5)))}


def evaluate(ev: pd.DataFrame, ex: pd.DataFrame, elig: pd.DataFrame, h: int, split_idx: int,
             rng, with_rand: bool = True) -> dict:
    """一條規則 × 一個持有天數的統計。回傳 {'train':…, 'test':…}。

    ev 事件布林表；ex 超額報酬(%)；elig 隨機基準可抽的池（同日同母體）。
    訓練期事件要在 split 前 h 天截止（持有期不跨進樣本外，避免標籤洩漏）。"""
    T = ev.shape[0]
    exv = ex.to_numpy(dtype=float)
    evv = ev.to_numpy(dtype=bool) & np.isfinite(exv)
    out = {}
    for name, lo, hi in (("train", 0, max(split_idx - h, 0)), ("test", split_idx, T)):
        rows = np.arange(lo, hi)
        e = evv[lo:hi]
        x = np.where(e, exv[lo:hi], 0.0)
        N = e.sum(axis=1).astype(float)
        S = x.sum(axis=1)
        Hh = (e & (exv[lo:hi] > 0)).sum(axis=1).astype(float)
        n = int(N.sum())
        if n == 0:
            out[name] = {"n": 0, "n_dates": 0}
            continue
        vals = exv[lo:hi][e]
        mean = float(S.sum() / n)
        res = {"n": n, "n_dates": int((N > 0).sum()), "mean": round(mean, 3),
               "median": round(float(np.median(vals)), 3), "hit": round(float(Hh.sum() / n), 4),
               "net": round(mean - COST_PCT, 3)}
        ci = _block_boot_ci(S, N, Hh, h, rng)
        if ci:
            res["ci"] = [round(ci["mean"][0], 3), round(ci["mean"][1], 3)]
            res["hit_ci"] = [round(ci["hit"][0], 4), round(ci["hit"][1], 4)]
        if with_rand and name == "test":
            pool = elig.to_numpy(dtype=bool)[lo:hi] & np.isfinite(exv[lo:hi])
            base = np.zeros(RAND_REPS)
            tot = 0
            for i in np.flatnonzero(N > 0):
                cand = exv[lo:hi][i][pool[i]]
                if cand.size == 0:
                    continue
                k = int(N[i])
                base += cand[rng.integers(0, cand.size, size=(RAND_REPS, k))].sum(axis=1)
                tot += k
            if tot:
                base /= tot
                res["rand_mean"] = round(float(base.mean()), 3)
                res["vs_rand"] = round(mean - float(base.mean()), 3)   # 比「同日同檔數隨機挑」多賺多少（個股母體本身跑輸市值加權大盤，所以要看這欄）
                res["p"] = round(float((1 + (base >= mean).sum()) / (1 + RAND_REPS)), 4)
                res["p_low"] = round(float((1 + (base <= mean).sum()) / (1 + RAND_REPS)), 4)
        out[name] = res
    return out


# ================================================================== 組裝
def _pct(x, nd=2):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def compute(panel: dict, *, with_rand: bool = True, recent_days: int = RECENT_DAYS, names: dict | None = None) -> dict:
    """主流程：訊號 → 事件 → 統計 → 近 60 日清單與最新候選。回傳可直接寫 JSON 的 dict。"""
    names = names or {}
    rng = np.random.default_rng(SEED)
    dates = panel["dates"]
    cc, oc, tv, net = panel["cc"], panel["oc"], panel["tv"], panel["net"]
    es = entity_series(panel)
    mk_cc, mk_oc = es["mk_cc"], es["mk_oc"]
    T = len(dates)
    split_idx = int(np.searchsorted(np.array(dates), TEST_START))

    # ---- 個股母體：四位數普通股、20 日均成交值 > 1 億（用 t 日及以前）
    four = [c for c in panel["codes"] if len(c) == 4 and c.isdigit() and not c.startswith("0")]
    avg20 = tv.rolling(20, min_periods=20).mean()
    s_elig = (avg20 > LIQ_MIN)[panel["codes"]]
    s_elig = s_elig & pd.Series(s_elig.columns.isin(four), index=s_elig.columns)
    # ---- 族群母體
    g_elig = (es["g_share"] >= GROUP_MIN_SHARE) & (es["g_cnt"] >= GROUP_MIN_MEMBERS)

    fb_s = flags_basic(cc, tv, net, es["s_share"], mk_cc)
    fb_g = flags_basic(es["g_cc"], es["g_tv"], es["g_net"], es["g_share"], mk_cc)
    fq = flags_quadrant(es["g_share"], es["g_cc"], mk_cc)

    flag_map = {
        "G1": fb_g["1"], "G2": fb_g["2"], "G3": fb_g["3"], "G4": fq["4"], "G5": fq["5"],
        "S1": fb_s["1"], "S2": fb_s["2"], "S3": fb_s["3"],
    }
    elig_map = {r["id"]: (g_elig if r["level"] == "group" else s_elig) for r in RULES}
    cc_map = {"group": (es["g_cc"], es["g_oc"]), "stock": (cc, oc)}
    ex = {lvl: {h: forward_excess(a, b, mk_cc, mk_oc, h) for h in HORIZONS} for lvl, (a, b) in cc_map.items()}

    events, stats = {}, {}
    for r in RULES:
        rid = r["id"]
        ev = cooldown_events(flag_map[rid] & elig_map[rid])
        events[rid] = ev
        stats[rid] = {h: evaluate(ev, ex[r["level"]][h], elig_map[rid], h, split_idx, rng, with_rand) for h in HORIZONS}

    # ---- Holm 校正（所有 規則×持有天數 的樣本外單尾 p 一起校正）
    keys = [(rid, h) for rid in stats for h in HORIZONS if "p" in stats[rid][h].get("test", {})]
    adj = _holm([stats[rid][h]["test"]["p"] for rid, h in keys]) if keys else []
    for (rid, h), a in zip(keys, adj):
        stats[rid][h]["test"]["p_holm"] = round(a, 4)

    rules_out = []
    for r in RULES:
        rid = r["id"]
        passed, weak, reverse = [], [], []
        for h in HORIZONS:
            te, tr = stats[rid][h].get("test", {}), stats[rid][h].get("train", {})
            if "p" not in te:
                continue
            if te["p"] < 0.05 and te["n"] >= 100:
                weak.append(h)
            if te.get("p_holm", 1) < 0.05 and te["n"] >= 100 and te["net"] > 0 and tr.get("mean", 0) > 0:
                passed.append(h)
            if te["p_low"] < 0.05 and te["n"] >= 100:
                reverse.append(h)
        verdict = "pass" if passed else "reverse" if reverse and not weak else "weak" if weak else "unproven"
        label = {"pass": "樣本外站得住", "weak": "未過多重比較校正（實驗）",
                 "reverse": "樣本外方向相反（實驗）", "unproven": "未證實（實驗）"}[verdict]
        rules_out.append({**r, "verdict": verdict, "verdict_text": label, "passed_horizons": passed,
                          "stats": {str(h): stats[rid][h] for h in HORIZONS}})

    # ---- 近 N 日事件清單（含之後實際超額）與最新候選
    pairs = panel["pairs"]
    gname = panel["groups"]["group_name"].to_dict()
    code_groups = pairs.groupby("code")["group_name"].apply(list).to_dict()
    last = T - 1
    first_recent = max(0, T - recent_days)
    strength = {"G1": fb_g["strength"]["1"], "G2": fb_g["strength"]["2"], "G3": fb_g["strength"]["3"],
                "S1": fb_s["strength"]["1"], "S2": fb_s["strength"]["2"], "S3": fb_s["strength"]["3"]}
    rows = []
    for r in RULES:
        rid, lvl = r["id"], r["level"]
        ev = events[rid].to_numpy()
        sv = strength[rid].to_numpy(dtype=float) if rid in strength else None
        for i in range(first_recent, T):
            cols = np.flatnonzero(ev[i])
            if lvl == "stock" and cols.size > STOCK_CAP_PER_RULE_DAY and sv is not None:
                cols = cols[np.argsort(-np.nan_to_num(sv[i][cols], nan=-1e18))[:STOCK_CAP_PER_RULE_DAY]]
            for j in cols:
                key = events[rid].columns[j]
                row = {"date": dates[i], "level": lvl, "rule": rid, "code": key,
                       "name": gname.get(key, key) if lvl == "group" else names.get(key, key),
                       "groups": [gname.get(key, key)] if lvl == "group" else code_groups.get(key, [])[:3],
                       "trigger": _trigger(rid, i, j, fb_g if lvl == "group" else fb_s, es, fq, tv, lvl),
                       "fwd": {str(h): _pct(ex[lvl][h].iat[i, j]) for h in HORIZONS}}
                rows.append(row)
    rows.sort(key=lambda x: (x["date"], x["level"], x["rule"]), reverse=True)

    # 最新一天：不做去重的「目前仍成立」清單，標出是否為新觸發
    cands: dict[tuple, dict] = {}
    for r in RULES:
        rid, lvl = r["id"], r["level"]
        fl = (flag_map[rid] & elig_map[rid]).to_numpy()[last]
        newv = events[rid].to_numpy()[last]
        sv = strength[rid].to_numpy(dtype=float)[last] if rid in strength else None
        cols = np.flatnonzero(fl)
        for j in cols:
            key = flag_map[rid].columns[j]
            c = cands.setdefault((lvl, key), {
                "level": lvl, "code": key,
                "name": gname.get(key, key) if lvl == "group" else names.get(key, key),
                "groups": [gname.get(key, key)] if lvl == "group" else code_groups.get(key, [])[:3],
                "rules": [], "triggers": {}})
            c["rules"].append({"rule": rid, "new": bool(newv[j]),
                               "strength": _pct(sv[j], 3) if sv is not None else None,
                               "verdict": next(x["verdict"] for x in rules_out if x["id"] == rid)})
            c["triggers"][rid] = _trigger(rid, last, j, fb_g if lvl == "group" else fb_s, es, fq, tv, lvl)
    cand_list = list(cands.values())
    for c in cand_list:
        c["score"] = len(c["rules"])
        c["has_pass"] = any(x["verdict"] == "pass" for x in c["rules"])
        c["any_new"] = any(x["new"] for x in c["rules"])
    cand_list.sort(key=lambda c: (-int(c["has_pass"]), -c["score"], c["level"] != "group", -int(c["any_new"]), c["code"]))

    return {
        "meta": {
            "latest": dates[-1], "first": dates[0], "train_end": TRAIN_END, "test_start": TEST_START,
            "n_dates": T, "horizons": list(HORIZONS), "cost_pct": COST_PCT, "cooldown": COOLDOWN,
            "recent_days": recent_days, "stock_cap_per_rule_day": STOCK_CAP_PER_RULE_DAY,
            "rand_reps": RAND_REPS, "liq_min": LIQ_MIN,
            "entry": "訊號當天收盤後產生，隔日開盤進場；持有 h 日後以第 h 日收盤出場；超額＝減大盤（前一日成交值加權）",
            "verdict_rule": "樣本外（test）至少一個持有天數同時滿足：Holm 校正後 p<0.05、樣本≥100、扣成本後超額>0、訓練期平均超額>0",
            "disclaimer": "統計研究輔助，不是買賣建議；歷史表現不代表未來。",
            "limits": ["族群成分用現在的 groups.yaml 套到歷史（成分回填偏誤）",
                       "下市股未來報酬缺值被剔除（存活者偏差，低估踩雷）",
                       "隔日開盤鎖漲停買不到仍當成買得到（對強勢股略樂觀）",
                       "同日事件高度相關：信賴區間用以日期為單位的區塊自助法，p 值用同日同檔數隨機基準",
                       "族群為加權籃子，扣成本沿用個股 0.47%（近似）",
                       "報酬不含現金股利（用官方參考價，除息日不計為下跌）"],
        },
        "rules": rules_out,
        "recent": rows,
        "latest": {"date": dates[-1], "candidates": cand_list[:60], "n_candidates": len(cand_list)},
    }


def _trigger(rid: str, i: int, j: int, fb: dict, es: dict, fq: dict, tv: pd.DataFrame, lvl: str) -> dict:
    """觸發當下的關鍵數字（給前端顯示）。"""
    if rid in ("G1", "S1"):
        sh = (es["g_share"] if lvl == "group" else es["s_share"]).iat[i, j]
        return {"share": _pct(sh, 3), "rel5": _pct(fb["rel5"].iat[i, j] * 100)}
    if rid in ("G2", "S2"):
        return {"net5": _pct(fb["strength"]["2"].iat[i, j] / 1000, 0), "ret5": _pct(fb["ret5"].iat[i, j] * 100)}
    if rid in ("G3", "S3"):
        return {"ratio": _pct(fb["ratio"].iat[i, j]), "ret5": _pct(fb["ret5"].iat[i, j] * 100)}
    if rid == "G4":
        return {"quadrant": "領先", "from": "改善"}
    return {"quadrant": "領先", "from": "改善"}


# ================================================================== 進入點
def build(price: pd.DataFrame, inst: pd.DataFrame, company: pd.DataFrame,
          names: dict | None = None, *, with_rand: bool = True) -> dict:
    panel = build_panel(price, inst, company)
    if names is None and company is not None and not company.empty:
        names = company.dropna(subset=["name"]).drop_duplicates("code", keep="last").set_index("code")["name"].to_dict()
    return compute(panel, with_rand=with_rand, names=names)


def write(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:                      # pragma: no cover — 手動驗證用的獨立小入口
    import argparse
    from .. import config
    from ..util import store
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.SITE_DATA / "flowcheck" / "daily_signals.json"))
    a = ap.parse_args()
    yrs = list(range(int(START[:4]), 2100))
    price = store.read("price_daily", years=yrs)
    inst = store.read("inst_daily", years=yrs)
    company = store.read("company_info")
    # 與 build_payload 同口徑：只用「上市資料到齊」的最後一天以前
    from ..build_payload import last_complete_date
    latest = last_complete_date(price)
    price = price[price["date"].astype(str) <= latest]
    inst = inst[inst["date"].astype(str) <= latest]
    out = build(price, inst, company)
    write(out, Path(a.out))
    log.info("寫出 %s", a.out)


if __name__ == "__main__":             # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    main()
