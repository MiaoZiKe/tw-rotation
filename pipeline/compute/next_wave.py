"""提前找下一波上漲族群／個股：多假說、多因子、樣本外驗證（流向驗證頁「找下一波」區）。

★ 為什麼有這一支（Andy 2026-11-01：「不管是日內、日、周線級別，是否有方法能歸納出一個訊號，提前找到原因佈局，
  這找的方法都需要有科學根據，有數據、籌碼量、供需、族群輪動、財報……並且需要幫我找多個標的回測，驗證是否有效」）。
  先前（docs/research/20261030_daily_signals.md）8 條「事件型」規則樣本外都沒站住。這裡換一種問法，也是學術上
  驗證「預測力」的標準做法：每週把族群（或個股）依某個因子排名，看「排名高的那一群」之後 5／10／20／60 日
  有沒有比同母體平均多賺（Rank IC＋Newey-West t＋多重比較校正）。結果不好就照寫，不調參數。

紅線（本支遵守的）
  · 訊號收盤後產生、隔日開盤進場：未來報酬沿用 daily_signals.forward_excess（t+1 開盤進、t+h 收盤出）。
  · 假說、因子公式、方向（預期正或負）、參數都在 FACTORS／常數裡**事先寫死**；訓練期（≤2023）只用來看方向是否一致與
    「訓練選因子」的綜合分數，判定有效只看樣本外（2024-01 起）。
  · 月營收用「法定公布日」當可用日（announce_date，次月 10 日），再順延到當天或之後第一個交易日；寧晚勿早。
  · 法人／融資券是 T 日盤後才公布的資料，因子在 T 日收盤後才可用，進場仍是 T+1 開盤，沒有偷看。
  · 成本 0.47%／趟；流動性門檻＝20 日均成交值 > 1 億（個股）／占比 ≥ 0.3% 且成員 ≥ 3（族群）。
  · 只讀資料湖，不寫 data/*.parquet。

資料限制（直接影響能測什麼，寫進輸出 meta.untestable）
  · 集保大戶持股（shareholding_weekly）與本益比淨值比（valuation_daily）資料湖只從 2026-09 開始 → 無法回測。
  · 借券（sbl_daily）從 2025-01 開始 → 只有約 1.5 年，標「短樣本」。
  · tape_5m 只有 2026-10-30 起 → 日內只能用 60 分 K（2023-09 起）。
"""
from __future__ import annotations

import json
import logging
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import daily_signals as ds

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- 事先寫死的參數
START = "2020-01-01"
TRAIN_END = "2023-12-31"
TEST_START = "2024-01-01"
HORIZONS = (5, 10, 20, 60)
REBAL = 5                    # 每 5 個交易日（約每週）重新排名一次
TOP_Q = 0.2                  # 取排名最前 20% 當「入選組」
COST_PCT = 0.47
LIQ_MIN = 1e8
MIN_NAMES = 8                # 一天有效標的少於此數就不算那一天
BOOT_REPS = 1000
RAND_REPS = 1000
SEED = 20261101
CAND_GROUPS = 8
CAND_STOCKS = 20
CASE_COOLDOWN = 10

# 每個因子：id／名稱／白話機制／文獻／方向（+ 越大越看好；- 越小越看好）／需要的資料／可用起點
# 方向是**依文獻事先決定**，不是看資料挑的。level 欄位：哪些層級要測。
FACTORS = [
    {"id": "MOM60", "name": "產業／個股動能（60 日，跳過最近 5 日）", "sign": +1, "levels": ("group", "stock"),
     "mech": "投資人對產業消息反應不足，動能延續（Moskowitz & Grinblatt 1999；Jegadeesh & Titman 1993）。",
     "data": "price_daily", "since": "2020"},
    {"id": "MOM20", "name": "20 日相對強度", "sign": {"group": +1, "stock": -1}, "levels": ("group", "stock"),
     "mech": "族群層動能最強出現在 1 個月內（Moskowitz & Grinblatt 1999）；個股層 1 個月是反轉（Jegadeesh 1990）。",
     "data": "price_daily", "since": "2020"},
    {"id": "REV5", "name": "近 5 日報酬（短期反轉）", "sign": -1, "levels": ("group", "stock"),
     "mech": "一週內的過度反應通常回吐（Lehmann 1990）。", "data": "price_daily", "since": "2020"},
    {"id": "H52", "name": "接近 52 週高點", "sign": +1, "levels": ("group", "stock"),
     "mech": "投資人以 52 週高點當錨，接近高點時利多反應不足（George & Hwang 2004）。",
     "data": "price_daily", "since": "2020"},
    {"id": "VOLR", "name": "成交值異常放大（5 日均 ÷ 60 日均）", "sign": +1, "levels": ("group", "stock"),
     "mech": "異常成交量代表資訊到來、注意力上升，隨後有溢價（Gervais, Kaniel & Mingelgrin 2001）。",
     "data": "price_daily", "since": "2020"},
    {"id": "SHARE", "name": "資金占比輪動（5 日均占比 ÷ 20 日均占比）", "sign": +1, "levels": ("group", "stock"),
     "mech": "資金持續流入某族群＝需求端增加；先前研究顯示與價格同步，這裡檢驗是否有領先。",
     "data": "price_daily", "since": "2020"},
    {"id": "INST10", "name": "三大法人（外資＋投信）10 日淨買超占成交量", "sign": +1, "levels": ("group", "stock"),
     "mech": "機構資訊優勢＋追蹤誤差建倉期長，連續買超後價格續漲（外資：Seasholes et al. 2014；台股投信作帳）。",
     "data": "inst_daily", "since": "2020"},
    {"id": "TRUST10", "name": "投信 10 日淨買超占成交量", "sign": +1, "levels": ("group", "stock"),
     "mech": "投信買超黏著、持股集中，季底作帳有推升效果（台股實務，學術證據較弱）。",
     "data": "inst_daily", "since": "2020"},
    {"id": "MARGIN20", "name": "融資餘額 20 日增幅（散戶過熱）", "sign": -1, "levels": ("group", "stock"),
     "mech": "散戶融資暴增代表籌碼轉到弱手，是過熱反指標（台股融資餘額研究；Barber & Odean 散戶偏誤）。",
     "data": "margin_daily", "since": "2021"},
    {"id": "SHORTR", "name": "券資比（融券餘額 ÷ 融資餘額）", "sign": -1, "levels": ("group", "stock"),
     "mech": "放空比重高＝知情者看壞（Asquith, Pathak & Ritter 2005；Desai et al. 2002）；台股另有軋空反向說法，故兩邊都照實報。",
     "data": "margin_daily", "since": "2021"},
    {"id": "SBL20", "name": "借券賣出餘額 20 日增幅", "sign": -1, "levels": ("stock",),
     "mech": "借券放空增加＝法人看空（Boehmer, Jones & Zhang 2008 的賣空資訊含量）。短樣本（2025 起）。",
     "data": "sbl_daily", "since": "2025", "short_sample": True},
    {"id": "REVYOY", "name": "最新月營收年增率（法定公布日起可用）", "sign": +1, "levels": ("group", "stock"),
     "mech": "營收是最即時的基本面訊號，市場對成長反應不足（Bernard & Thomas 1989 盈餘後漂移；台股月營收公布效應）。",
     "data": "revenue_monthly", "since": "2020"},
    {"id": "REVACC", "name": "月營收年增率加速度（本月 YoY − 3 個月前 YoY）", "sign": +1, "levels": ("group", "stock"),
     "mech": "成長「加速」比「高成長」更新鮮，驚喜成分更高（盈餘驚喜後漂移的月營收版）。",
     "data": "revenue_monthly", "since": "2020"},
    {"id": "CSMOM", "name": "下游客戶 20 日報酬（供應鏈傳導）", "sign": +1, "levels": ("stock",),
     "mech": "客戶的消息要慢慢傳到供應商，客戶報酬可預測供應商報酬（Cohen & Frazzini 2008）。母體僅 supply_chain.yaml 有台股客戶的公司。",
     "data": "supply_chain.yaml + price_daily", "since": "2020"},
]
FACTOR_BY_ID = {f["id"]: f for f in FACTORS}


def sign_of(fid: str, level: str) -> int:
    s = FACTOR_BY_ID[fid]["sign"]
    return s[level] if isinstance(s, dict) else s


# 日內（60 分 K）因子：訊號在某根 K 棒收盤後產生、下一根開盤進場
INTRADAY = [
    {"id": "I1", "name": "第一小時相對強度 → 當日剩餘時段", "sign": +1,
     "mech": "開盤第一小時消化隔夜資訊，強勢者延續（Gao et al. 2018「日內動能」：首半小時預測末半小時）。", "target": "same"},
    {"id": "I2", "name": "第一小時成交量放大 → 當日剩餘時段", "sign": +1,
     "mech": "開盤量異常大＝資訊事件，注意力吸引後續買盤。", "target": "same"},
    {"id": "I3", "name": "尾盤（12:00 後）強度 → 隔日開盤到收盤", "sign": +1,
     "mech": "尾盤的知情交易延續到隔日（Heston, Korajczyk & Sadka 2010 日內動能）。", "target": "next"},
    {"id": "I4", "name": "收盤位於當日區間位置 → 隔日開盤到收盤", "sign": +1,
     "mech": "收在高檔代表買盤強於賣盤（類 Williams %R／收盤位置因子）。", "target": "next"},
]

NOT_TESTABLE = [
    {"id": "HOLD", "name": "集保大戶持股比例變化", "why": "資料湖只從 2026-09-04 開始（約 8 週），無法回測；已建議持續累積，約 2 年後可驗。"},
    {"id": "VAL", "name": "估值均值回歸（本益比／淨值比）", "why": "valuation_daily 只從 2026-09-09 開始，無法回測；以「接近 52 週高點」「動能」兩個價格因子代測。"},
    {"id": "NEWS", "name": "新聞情緒", "why": "news 表只從 2026-09-10 開始（約 7 週），文字情緒模型也尚未建立，無法回測。"},
    {"id": "TAPE", "name": "5 分 tape 級別日內資金流", "why": "tape_5m 只有 2026-10-30 起（約 1 個交易日），n 太小；日內級別改用 60 分 K（2023-09 起）。"},
    {"id": "FUT", "name": "期貨／選擇權籌碼（外資期貨未平倉、P/C）", "why": "屬大盤層級的時機訊號，不能用來挑族群；opt_pc 資料還停在 2025-06。"},
    {"id": "EPS", "name": "財報 EPS 驚喜後漂移", "why": "資料湖沒有分析師預期值，無法算「驚喜」；以月營收年增率與加速度（更即時、法定可用日明確）代測。"},
]


# ================================================================== 小工具
def rank_z(df: pd.DataFrame) -> pd.DataFrame:
    """逐日橫斷面排名 → z 分數（以名次計，免疫極端值）。缺值維持缺值。"""
    r = df.rank(axis=1)
    n = df.notna().sum(axis=1)
    mu = (n + 1) / 2
    sd = np.sqrt((n ** 2 - 1) / 12)
    return r.sub(mu, axis=0).div(sd.replace(0, np.nan), axis=0)


def nw_t(y: np.ndarray, lag: int) -> tuple[float, float]:
    """平均數的 Newey-West t 值（Bartlett 權重）與單尾 p（H1：平均 > 0）。"""
    from scipy import stats
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 5:
        return float("nan"), float("nan")
    m = y.mean()
    e = y - m
    v = (e * e).sum() / n
    for k in range(1, min(lag, n - 1) + 1):
        w = 1 - k / (lag + 1)
        v += 2 * w * (e[k:] * e[:-k]).sum() / n
    se = math.sqrt(max(v, 1e-18) / n)
    t = m / se
    return float(t), float(stats.t.sf(t, n - 1))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def boot_ci(y: np.ndarray, block: int, rng, reps: int = BOOT_REPS) -> tuple[float, float]:
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    D = len(y)
    if D < 5:
        return (float("nan"), float("nan"))
    k = int(np.ceil(D / block))
    st = rng.integers(0, D, size=(reps, k))
    idx = ((st[:, :, None] + np.arange(block)[None, None, :]) % D).reshape(reps, -1)[:, :D]
    m = y[idx].mean(axis=1)
    return (float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)))


# ================================================================== 因子面板（全部只看 t 日及以前）
def _wide(df: pd.DataFrame, col: str, dates, codes) -> pd.DataFrame:
    d = df[["date", "code", col]].copy()
    d["date"] = d["date"].astype(str)
    d["code"] = d["code"].astype(str)
    d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.drop_duplicates(["date", "code"], keep="last")
    return d.pivot(index="date", columns="code", values=col).reindex(index=dates, columns=codes)


def revenue_factors(rev: pd.DataFrame, dates: list, codes: list) -> dict:
    """月營收年增率與加速度。★ 可用日＝法定公布日（announce_date，次月 10 日）順延到當天或之後第一個交易日，
    當天收盤後才能用（隔天開盤進場），所以不會偷看。YoY 自己用同一檔「去年同月」營收算，不依賴缺值多的 yoy_pct 欄。"""
    r = rev[["ym", "code", "revenue", "announce_date"]].copy()
    r["code"] = r["code"].astype(str)
    r["revenue"] = pd.to_numeric(r["revenue"], errors="coerce")
    r = r.dropna(subset=["revenue"]).drop_duplicates(["ym", "code"], keep="last")
    r["p"] = pd.PeriodIndex(r["ym"], freq="M")
    prev = r[["code", "p", "revenue"]].copy()
    prev["p"] = prev["p"] + 12
    r = r.merge(prev.rename(columns={"revenue": "rev_ly"}), on=["code", "p"], how="left")
    r["yoy"] = (r["revenue"] / r["rev_ly"] - 1).where(r["rev_ly"] > 0)
    r = r.sort_values(["code", "p"])
    r["yoy_3m"] = r.groupby("code")["yoy"].shift(3)
    r["acc"] = r["yoy"] - r["yoy_3m"]
    # 公布日缺值（舊資料）→ 用「次月 10 日」法定日補；寧晚勿早
    ann = pd.to_datetime(r["announce_date"], errors="coerce")
    legal = (r["p"] + 1).dt.to_timestamp() + pd.Timedelta(days=9)
    r["avail"] = ann.fillna(legal).dt.strftime("%Y-%m-%d")
    dts = np.array(dates)
    pos = np.searchsorted(dts, r["avail"].to_numpy(dtype=str), side="left")   # 當天或之後第一個交易日
    r["pos"] = pos
    r = r[(r["pos"] < len(dts)) & r["code"].isin(set(codes))]
    out = {}
    for name in ("yoy", "acc"):
        x = r.dropna(subset=[name]).sort_values(["code", "pos"]).drop_duplicates(["pos", "code"], keep="last")
        w = pd.DataFrame(np.nan, index=range(len(dts)), columns=codes)
        piv = x.pivot(index="pos", columns="code", values=name)
        w.loc[piv.index, piv.columns] = piv.to_numpy()
        w = w.ffill(limit=45)                       # 45 個交易日後視為過期（缺新資料）
        w.index = dates
        out[name] = w.clip(-1, 5)                   # 極端值截尾，避免基期效應主導
    return out


def customer_pairs(sc: dict, codes: list) -> list[tuple[str, str]]:
    """供應鏈 supplies 邊中，雙方都是台股的 (供應商代號, 客戶代號)。"""
    ids = {c["id"]: str(c.get("ticker") or "") for c in sc.get("companies", [])}
    cs = set(codes)
    out = set()
    for e in sc.get("edges", []):
        if e.get("rel") != "supplies":
            continue
        a, b = ids.get(e["from"], ""), ids.get(e["to"], "")
        if re.fullmatch(r"\d{4}", a) and re.fullmatch(r"\d{4}", b) and a in cs and b in cs and a != b:
            out.add((a, b))
    return sorted(out)


def stock_factors(panel: dict, volume: pd.DataFrame, trust: pd.DataFrame, rev: dict | None,
                  margin: pd.DataFrame | None, short: pd.DataFrame | None, sbl: pd.DataFrame | None,
                  pairs: list | None) -> dict:
    """個股層所有因子（日期 × 代號）。每個 rolling／shift 都是往過去看，t 日的值只依賴 t 日及以前。"""
    cc, tv, net = panel["cc"], panel["tv"], panel["net"]
    lv = ds._level(cc)
    F = {}
    F["MOM60"] = lv.shift(5) / lv.shift(65) - 1
    F["MOM20"] = lv / lv.shift(20) - 1
    F["REV5"] = lv / lv.shift(5) - 1
    F["H52"] = lv / lv.rolling(250, min_periods=120).max()
    F["VOLR"] = tv.rolling(5).mean() / tv.rolling(60, min_periods=40).mean()
    sh = tv.div(tv.sum(axis=1).where(lambda s: s > 0), axis=0)
    F["SHARE"] = sh.rolling(5).mean() / sh.rolling(20, min_periods=15).mean()
    vsum = volume.rolling(10, min_periods=8).sum()
    F["INST10"] = (net.rolling(10, min_periods=8).sum() / vsum).where(vsum > 0)
    F["TRUST10"] = (trust.rolling(10, min_periods=8).sum() / vsum).where(vsum > 0)
    if margin is not None:
        F["MARGIN20"] = (margin / margin.shift(20) - 1).where(margin.shift(20) > 0)
        if short is not None:
            F["SHORTR"] = (short / margin).where(margin > 100)
    if sbl is not None:
        F["SBL20"] = (sbl / sbl.shift(20) - 1).where(sbl.shift(20) > 0)
    if rev is not None:
        F["REVYOY"], F["REVACC"] = rev["yoy"], rev["acc"]
    if pairs:
        ci = {c: i for i, c in enumerate(cc.columns)}
        A = np.zeros((len(cc.columns), len(cc.columns)))      # A[客戶, 供應商]
        for s, c in pairs:
            A[ci[c], ci[s]] = 1
        has = A.sum(axis=0) > 0
        r20 = np.nan_to_num((lv / lv.shift(20) - 1).to_numpy(dtype=float))
        cust = (r20 @ A) / np.where(A.sum(axis=0) > 0, A.sum(axis=0), 1)
        cm = pd.DataFrame(cust, index=cc.index, columns=cc.columns)
        F["CSMOM"] = cm.where(pd.Series(has, index=cc.columns).reindex(cc.columns).to_numpy()[None, :] & lv.notna().to_numpy())
    return F


def group_factors(panel: dict, es: dict, SF: dict) -> dict:
    """族群層因子：報酬／成交值類直接用族群序列；基本面／籌碼類＝成員「橫斷面名次 z」的平均（避免大股獨大）。"""
    M = panel["M"]
    gids = list(panel["groups"].index)
    g_cc, g_tv = es["g_cc"], es["g_tv"]
    glv = ds._level(g_cc)
    F = {}
    F["MOM60"] = glv.shift(5) / glv.shift(65) - 1
    F["MOM20"] = glv / glv.shift(20) - 1
    F["REV5"] = glv / glv.shift(5) - 1
    F["H52"] = glv / glv.rolling(250, min_periods=120).max()
    F["VOLR"] = g_tv.rolling(5).mean() / g_tv.rolling(60, min_periods=40).mean()
    gs = es["g_share"]
    F["SHARE"] = gs.rolling(5).mean() / gs.rolling(20, min_periods=15).mean()
    B = (M > 0).astype(float)
    for fid in ("INST10", "TRUST10", "MARGIN20", "SHORTR", "REVYOY", "REVACC"):
        if fid not in SF:
            continue
        z = rank_z(SF[fid])
        ok = z.notna().to_numpy().astype(float)
        num = np.nan_to_num(z.to_numpy(dtype=float)) @ B
        den = ok @ B
        F[fid] = pd.DataFrame(np.where(den >= 3, num / np.where(den > 0, den, 1), np.nan), index=z.index, columns=gids)
    return F


def group_raw(panel: dict, SF: dict) -> dict:
    """族群層「顯示用」原始數值：成員原始因子值的平均（INST10、REVYOY…），只給案例與候選的白話說明用，不進統計。"""
    B = (panel["M"] > 0).astype(float)
    gids = list(panel["groups"].index)
    out = {}
    for fid in ("INST10", "TRUST10", "MARGIN20", "REVYOY", "REVACC"):
        if fid not in SF:
            continue
        v = SF[fid].to_numpy(dtype=float)
        lo_, hi_ = np.nanpercentile(v, [1, 99])
        x = SF[fid].clip(lo_, hi_)
        ok = x.notna().to_numpy().astype(float)
        den = ok @ B
        num = np.nan_to_num(x.to_numpy(dtype=float)) @ B
        out[fid] = pd.DataFrame(np.where(den >= 3, num / np.where(den > 0, den, 1), np.nan), index=x.index, columns=gids)
    return out


def eligibility(panel: dict, es: dict) -> dict:
    tv = panel["tv"]
    liq = tv.rolling(20, min_periods=15).mean() > ds.LIQ_MIN
    four = pd.Series([bool(re.fullmatch(r"\d{4}", c)) for c in tv.columns], index=tv.columns)
    stock = liq & four.to_numpy()[None, :] & tv.notna()
    group = (es["g_share"] >= ds.GROUP_MIN_SHARE) & (es["g_cnt"] >= ds.GROUP_MIN_MEMBERS)
    return {"stock": stock, "group": group}


# ================================================================== 橫斷面評估
def cs_stats(F: pd.DataFrame, X: pd.DataFrame, elig: pd.DataFrame, rows: np.ndarray, sign: int, q: float = TOP_Q) -> dict:
    """在指定的重新排名日（rows）逐日算：Rank IC、入選組平均超額、母體平均超額、入選組檔數。"""
    fv = (F.to_numpy(dtype=float) * sign)
    xv = X.to_numpy(dtype=float)
    ev = elig.to_numpy(dtype=bool)
    ic, top, uni, nn = [], [], [], []
    for i in rows:
        ok = ev[i] & np.isfinite(fv[i]) & np.isfinite(xv[i])
        n = int(ok.sum())
        if n < MIN_NAMES:
            ic.append(np.nan); top.append(np.nan); uni.append(np.nan); nn.append(0)
            continue
        f, x = fv[i][ok], xv[i][ok]
        rf = f.argsort().argsort().astype(float)
        rx = x.argsort().argsort().astype(float)
        ic.append(float(np.corrcoef(rf, rx)[0, 1]))
        k = max(int(round(n * q)), 3)
        sel = rf >= n - k
        top.append(float(x[sel].mean())); uni.append(float(x.mean())); nn.append(k)
    return {"ic": np.array(ic), "top": np.array(top), "uni": np.array(uni), "k": np.array(nn)}


def summarize(st: dict, h: int, rng, seg: np.ndarray) -> dict:
    """seg：布林，哪些重新排名日屬於這一段（訓練或樣本外）。"""
    ic, top, uni = st["ic"][seg], st["top"][seg], st["uni"][seg]
    ok = np.isfinite(ic) & np.isfinite(top)
    ic, top, uni = ic[ok], top[ok], uni[ok]
    n = int(ok.sum())
    if n < 5:
        return {"n_dates": n}
    lag = max(int(math.ceil(h / REBAL)), 1)
    t_ic, p_ic = nw_t(ic, lag)
    spread = top - uni
    t_sp, p_sp = nw_t(spread, lag)
    hit_k = int((spread > 0).sum())
    lo, hi = wilson(hit_k, n)
    # 有效獨立樣本：重疊持有期使相鄰日期不獨立 → 命中率區間以 n/lag 近似縮小樣本
    n_eff = max(int(n / lag), 1)
    lo2, hi2 = wilson(int(round(hit_k / n * n_eff)), n_eff)
    ci = boot_ci(spread, lag, rng)
    return {
        "n_dates": n, "n_eff": n_eff, "k_avg": round(float(np.mean(st["k"][seg][ok])), 1),
        "ic": round(float(ic.mean()), 4), "ic_t": round(t_ic, 2), "ic_p": round(p_ic, 4),
        "top": round(float(top.mean()), 3),                 # 入選組相對大盤的平均超額 %
        "uni": round(float(uni.mean()), 3),                 # 母體（等權）相對大盤的平均超額 %
        "spread": round(float(spread.mean()), 3),           # 比隨機多（入選 − 母體平均）%
        "spread_t": round(t_sp, 2), "spread_p": round(p_sp, 4),
        "spread_ci": [round(ci[0], 3), round(ci[1], 3)],
        "hit": round(hit_k / n, 3), "hit_ci": [round(lo2, 3), round(hi2, 3)],
        "net": round(float(spread.mean()) - COST_PCT, 3),   # 扣成本後比隨機多（每期換股一趟）
    }


def holm(ps: list[float]) -> list[float]:
    return ds._holm([1.0 if not np.isfinite(p) else p for p in ps])


def verdict(tr: dict, te: dict, p_holm: float, short_sample: bool = False) -> tuple[str, str]:
    """有效＝樣本外：Holm 校正後 IC p<0.05、比隨機多>0 且扣成本後>0、訓練期方向一致（IC 同號）、樣本日數≥20。"""
    if te.get("n_dates", 0) < 20:
        return "unproven", "樣本不足"
    if short_sample:
        return "short", "短樣本（< 2 年），只供參考"
    same_dir = tr.get("ic", 0) > 0
    if p_holm < 0.05 and te["spread"] > 0 and te["net"] > 0 and same_dir:
        return "pass", "樣本外有效（過多重比較校正、扣成本後仍為正）"
    if te["ic"] < 0 and te["ic_p"] > 0.95:
        return "reverse", "樣本外方向相反"
    if te["ic_p"] < 0.05 and p_holm >= 0.05:
        return "weak", "單看顯著、但沒過多重比較校正"
    return "unproven", "未證實（與隨機無顯著差異）"


def run_level(level: str, F: dict, elig: pd.DataFrame, cc, oc, mk_cc, mk_oc, dates: list, rng) -> dict:
    """某一層級（族群／個股）所有因子 × 持有天數的統計。"""
    T = len(dates)
    split = int(np.searchsorted(np.array(dates), TEST_START))
    X = {h: ds.forward_excess(cc, oc, mk_cc, mk_oc, h) for h in HORIZONS}
    all_rows = np.arange(60, T, REBAL)
    out = {}
    for fid, fr in F.items():
        s = sign_of(fid, level)
        for h in HORIZONS:
            st = cs_stats(fr, X[h], elig, all_rows, s)
            tr_seg = (all_rows < split - h)
            te_seg = (all_rows >= split) & (all_rows < T - h)
            out[(fid, h)] = {"train": summarize(st, h, rng, tr_seg), "test": summarize(st, h, rng, te_seg),
                             "_st": st, "_rows": all_rows}
    return out, X


# ================================================================== 綜合分數
def composite(F: dict, level: str, ids: list[str]) -> pd.DataFrame:
    """等權 z 分數：每個因子先橫斷面名次 z、乘上事先決定的方向、再平均（至少一半因子有值才算）。"""
    zs = [rank_z(F[i]) * sign_of(i, level) for i in ids if i in F]
    if not zs:
        return None
    arr = np.stack([z.to_numpy(dtype=float) for z in zs])
    cnt = np.isfinite(arr).sum(axis=0)
    m = np.nanmean(np.where(np.isfinite(arr), arr, np.nan), axis=0) if arr.size else None
    m = np.where(cnt >= max(len(zs) / 2, 1), m, np.nan)
    return pd.DataFrame(m, index=zs[0].index, columns=zs[0].columns)


def train_select(res: dict, level: str, h: int = 20, t_min: float = 1.5) -> list[str]:
    """訓練期（≤2023）挑因子：方向校正後 Rank IC 的 NW t > t_min。只用訓練期資料。"""
    ids = []
    for (fid, hh), v in res.items():
        if hh == h and v["train"].get("ic_t", 0) > t_min and v["train"].get("ic", 0) > 0:
            ids.append(fid)
    return sorted(ids)


# ================================================================== 日內（60 分 K）
def intraday_panel(df60: pd.DataFrame, codes: list) -> dict | None:
    """把 60 分 K 變成「日 × 代號」寬表，每根 K 棒一張：O0..O4／C0..C4／V0..V4。
    K 棒起點 09:00,10:00,11:00,12:00,13:00（最後一根含 13:30 收盤）。"""
    d = df60[df60["code"].isin(set(codes))].copy()
    if d.empty:
        return None
    ts = d["ts"].astype(str)
    d["day"] = ts.str.slice(0, 10)
    d["k"] = ts.str.slice(11, 13).astype(int) - 9
    d = d[(d["k"] >= 0) & (d["k"] <= 4)]
    out = {}
    for col, nm in (("open", "O"), ("close", "C"), ("high", "H"), ("low", "L"), ("volume", "V")):
        for k in range(5):
            s = d[d["k"] == k].drop_duplicates(["day", "code"], keep="last")
            out[f"{nm}{k}"] = s.pivot(index="day", columns="code", values=col)
    return out


def intraday_eval(P: dict, panel: dict, elig_stock: pd.DataFrame, rng, M: np.ndarray, gids: list, g_elig: pd.DataFrame | None = None) -> dict:
    """日內因子的橫斷面檢驗。樣本日數少（約 3 年）且 60 分 K 粗糙 → 一律標短樣本，不作投資結論。"""
    days = list(P["C0"].index)
    codes = list(P["C0"].columns)
    ev = elig_stock.reindex(index=days, columns=codes).fillna(False)
    O = {k: P[f"O{k}"].reindex(index=days, columns=codes) for k in range(5)}
    C = {k: P[f"C{k}"].reindex(index=days, columns=codes) for k in range(5)}
    V = {k: P[f"V{k}"].reindex(index=days, columns=codes) for k in range(5)}
    H = pd.concat([P[f"H{k}"].reindex(index=days, columns=codes) for k in range(5)]).groupby(level=0).max()
    L = pd.concat([P[f"L{k}"].reindex(index=days, columns=codes) for k in range(5)]).groupby(level=0).min()
    day_close = C[4]
    f = {}
    f["I1"] = C[0] / O[0] - 1
    base = V[0].rolling(20, min_periods=10).mean().shift(1)           # 過去 20 日同一根量（不含當天）
    f["I2"] = (V[0] / base).where(base > 0)
    f["I3"] = C[4] / O[3] - 1                                          # 最後兩根（12:00 起）
    rng_ = (H - L).where((H - L) > 0)
    f["I4"] = (day_close - L) / rng_
    tgt_same = (C[4] / O[1] - 1) * 100                                 # 10:00 開盤進、收盤出
    nxt = (C[4] / O[0] - 1) * 100
    tgt_next = nxt.shift(-1)                                            # 隔日 09:00 開盤進、收盤出
    out = {}
    split = int(np.searchsorted(np.array(days), TEST_START))
    rows = np.arange(20, len(days) - 1)
    for spec in INTRADAY:
        fid = spec["id"]
        X = tgt_same if spec["target"] == "same" else tgt_next
        for level in ("stock", "group"):
            if level == "stock":
                Fr, Xr, E = f[fid], X, ev
            else:
                Bm = pd.DataFrame(M, index=panel["codes"], columns=gids).reindex(codes).fillna(0).to_numpy() > 0
                Bf = Bm.astype(float)

                def agg(df):
                    a = np.nan_to_num(df.to_numpy(dtype=float))
                    ok = df.notna().to_numpy().astype(float)
                    den = ok @ Bf
                    return pd.DataFrame(np.where(den >= 3, (a * ok) @ Bf / np.where(den > 0, den, 1), np.nan), index=df.index, columns=gids)
                Fr, Xr = agg(f[fid]), agg(X)
                E = (ev.to_numpy().astype(float) @ Bf >= 3)
                E = pd.DataFrame(E, index=days, columns=gids)
            st = cs_stats(Fr, Xr, E, rows, spec["sign"])
            tr = rows < split
            te = rows >= split
            lag = 2
            res = {}
            for nm, seg in (("train", tr), ("test", te)):
                ic, top, uni = st["ic"][seg], st["top"][seg], st["uni"][seg]
                ok = np.isfinite(ic) & np.isfinite(top)
                if ok.sum() < 5:
                    res[nm] = {"n_dates": int(ok.sum())}
                    continue
                sp = (top - uni)[ok]
                t_ic, p_ic = nw_t(ic[ok], lag)
                t_sp, p_sp = nw_t(sp, lag)
                ci = boot_ci(sp, lag, rng)
                hit = int((sp > 0).sum())
                lo, hi = wilson(hit, int(ok.sum()))
                res[nm] = {"n_dates": int(ok.sum()), "ic": round(float(ic[ok].mean()), 4), "ic_t": round(t_ic, 2),
                           "ic_p": round(p_ic, 4), "spread": round(float(sp.mean()), 3), "spread_t": round(t_sp, 2),
                           "spread_p": round(p_sp, 4), "spread_ci": [round(ci[0], 3), round(ci[1], 3)],
                           "hit": round(hit / int(ok.sum()), 3), "hit_ci": [round(lo, 3), round(hi, 3)],
                           "net": round(float(sp.mean()) - COST_PCT, 3)}
            out[(fid, level)] = res
    return out


# ================================================================== 案例
def cases_for(score: pd.DataFrame, elig: pd.DataFrame, X: dict, F: dict, level: str, names: dict, gname: dict,
              mk_ret20: pd.Series, dates: list, top_n: int, rows: np.ndarray) -> list[dict]:
    """綜合分數「新進入入選組」的歷次觸發（去重：同標的 10 個交易日內不重算）。"""
    sv = score.to_numpy(dtype=float)
    ev = elig.to_numpy(dtype=bool)
    prev_in = set()
    last_hit: dict = {}
    out = []
    for i in rows:
        ok = ev[i] & np.isfinite(sv[i])
        if ok.sum() < MIN_NAMES:
            continue
        idx = np.flatnonzero(ok)
        top = idx[np.argsort(-sv[i][idx])[:top_n]]
        cur = set(top.tolist())
        for j in cur - prev_in:
            if i - last_hit.get(j, -999) <= CASE_COOLDOWN * 2:
                continue
            last_hit[j] = i
            key = score.columns[j]
            row = {"date": dates[i], "level": level, "code": key,
                   "name": gname.get(key, key) if level == "group" else names.get(key, key),
                   "score": round(float(sv[i][j]), 2),
                   "why": {fid: (None if not np.isfinite(F[fid].iat[i, j]) else round(float(F[fid].iat[i, j]), 3))
                           for fid in F if fid in ("MOM60", "H52", "INST10", "REVYOY", "REVACC", "VOLR", "MARGIN20")},
                   "mkt20": None if not np.isfinite(mk_ret20.iat[i]) else round(float(mk_ret20.iat[i]) * 100, 1),
                   "fwd": {str(h): (None if not np.isfinite(X[h].iat[i, j]) else round(float(X[h].iat[i, j]), 2)) for h in (5, 20, 60)}}
            out.append(row)
        prev_in = cur
    return out


def explain(c: dict) -> str:
    """把一筆案例自動翻成白話原因（成功或失敗都給）。"""
    w = c["why"]
    bits = []
    if w.get("REVYOY") is not None and w["REVYOY"] > 0.2:
        bits.append(f"月營收年增 {w['REVYOY']*100:.0f}%")
    if w.get("REVACC") is not None and w["REVACC"] > 0.15:
        bits.append(f"年增加速 {w['REVACC']*100:.0f} 個百分點")
    if w.get("MOM60") is not None:
        bits.append(f"過去約 3 個月漲 {w['MOM60']*100:.0f}%")
    if w.get("INST10") is not None and w["INST10"] > 0.02:
        bits.append(f"法人 10 日淨買占成交量 {w['INST10']*100:.1f}%")
    if w.get("VOLR") is not None and w["VOLR"] > 1.3:
        bits.append(f"成交值放大 {w['VOLR']:.1f} 倍")
    if w.get("MARGIN20") is not None and w["MARGIN20"] > 0.15:
        bits.append(f"融資 20 日增 {w['MARGIN20']*100:.0f}%（偏熱）")
    f20 = c["fwd"].get("20")
    tail = ""
    if f20 is not None:
        if f20 < -3 and c.get("mkt20") is not None and c["mkt20"] < -3:
            tail = "；大盤同期走弱，順勢資金一起撤"
        elif f20 < -3 and w.get("MOM60") is not None and w["MOM60"] > 0.4:
            tail = "；進場前已大漲，屬追高被回檔"
        elif f20 < -3:
            tail = "；沒有明顯單一原因，屬訊號失靈"
        elif f20 > 3:
            tail = "；基本面與資金同向，續航"
    return "、".join(bits) + tail if bits else "多項因子名次同步靠前" + tail


# ================================================================== 主流程
def build(price, inst, company, margin, revenue, sbl, df60, sc, intl, names=None, *, with_intraday=True) -> dict:
    rng = np.random.default_rng(SEED)
    panel = ds.build_panel(price, inst, company, start=START)
    es = ds.entity_series(panel)
    dates, codes = panel["dates"], panel["codes"]
    if names is None and company is not None and not company.empty:
        names = company.dropna(subset=["name"]).drop_duplicates("code", keep="last").set_index("code")["name"].to_dict()
    names = names or {}
    p = price[["date", "code", "volume"]]
    volume = _wide(p, "volume", dates, codes)
    trust = _wide(inst, "trust", dates, codes).fillna(0)
    mg = _wide(margin, "margin_balance", dates, codes) if margin is not None and len(margin) else None
    sh = _wide(margin, "short_balance", dates, codes) if margin is not None and len(margin) else None
    sb = _wide(sbl, "sbl_balance", dates, codes) if sbl is not None and len(sbl) else None
    rv = revenue_factors(revenue, dates, codes) if revenue is not None and len(revenue) else None
    pairs = customer_pairs(sc, codes) if sc else []
    SF = stock_factors(panel, volume, trust, rv, mg, sh, sb, pairs)
    GF = group_factors(panel, es, SF)
    E = eligibility(panel, es)
    GRAW = group_raw(panel, SF)
    gname = panel["groups"]["group_name"].to_dict()

    res = {}
    Xs = {}
    for level, F, cc, oc, elig in (("group", GF, es["g_cc"], es["g_oc"], E["group"]),
                                   ("stock", SF, panel["cc"], panel["oc"], E["stock"])):
        # CSMOM 只在有客戶資料的小母體裡比較
        Fl = {k: v for k, v in F.items() if level in FACTOR_BY_ID[k]["levels"]}
        r, X = run_level(level, Fl, elig, cc, oc, es["mk_cc"], es["mk_oc"], dates, rng)
        res[level] = (r, Fl)
        Xs[level] = X
    # CSMOM 母體要限縮到「有客戶」的那幾檔
    if "CSMOM" in SF:
        e2 = E["stock"] & SF["CSMOM"].notna()
        r2, _ = run_level("stock", {"CSMOM": SF["CSMOM"]}, e2, panel["cc"], panel["oc"], es["mk_cc"], es["mk_oc"], dates, rng)
        for k, v in r2.items():
            res["stock"][0][k] = v

    # ---- 綜合分數：A＝全部文獻方向等權；B＝訓練期挑（NW t>1.5）
    comp = {}
    split = int(np.searchsorted(np.array(dates), TEST_START))
    T = len(dates)
    rows_all = np.arange(60, T, REBAL)
    for level, elig in (("group", E["group"]), ("stock", E["stock"])):
        r, Fl = res[level]
        ids_all = [i for i in Fl if not FACTOR_BY_ID[i].get("short_sample") and i != "CSMOM"]
        ids_b = [i for i in train_select(r, level) if i in ids_all]
        for tag, ids in (("A", ids_all), ("B", ids_b)):
            if not ids:
                continue
            sc_ = composite(Fl, level, ids)
            cc, oc = (es["g_cc"], es["g_oc"]) if level == "group" else (panel["cc"], panel["oc"])
            for h in HORIZONS:
                st = cs_stats(sc_, Xs[level][h], elig, rows_all, +1)
                tr_seg = rows_all < split - h
                te_seg = (rows_all >= split) & (rows_all < T - h)
                comp[(level, tag, h)] = {"ids": ids, "train": summarize(st, h, rng, tr_seg), "test": summarize(st, h, rng, te_seg),
                                         "_st": st, "_score": sc_}
    # 隨機基準 p（綜合分數）：樣本外同日同檔數隨機抽 → 平均超額分布
    for key, v in comp.items():
        level, tag, h = key
        st = v["_st"]
        te_seg = (rows_all >= split) & (rows_all < T - h)
        ok = te_seg & np.isfinite(st["top"])
        if ok.sum() < 5:
            continue
        X = Xs[level][h].to_numpy(dtype=float)
        elig = (E["group"] if level == "group" else E["stock"]).to_numpy(dtype=bool)
        obs = float(np.nanmean(st["top"][ok]))
        sim = np.zeros(RAND_REPS)
        cnt = 0
        for ri in np.flatnonzero(ok):
            i = rows_all[ri]
            pool = X[i][elig[i] & np.isfinite(X[i])]
            k = int(st["k"][ri])
            if pool.size < k or k == 0:
                continue
            sim += pool[rng.integers(0, pool.size, size=(RAND_REPS, k))].mean(axis=1)
            cnt += 1
        if cnt:
            sim /= cnt
            v["test"]["rand_mean"] = round(float(sim.mean()), 3)
            v["test"]["rand_p"] = round(float((sim >= obs).mean()), 4)

    # ---- Holm：單因子 + 綜合（層級×因子×持有天數）
    keys, ps = [], []
    for level in ("group", "stock"):
        for (fid, h), v in res[level][0].items():
            keys.append(("f", level, fid, h)); ps.append(v["test"].get("ic_p", 1.0))
    for (level, tag, h), v in comp.items():
        keys.append(("c", level, tag, h)); ps.append(v["test"].get("ic_p", 1.0))
    adj = dict(zip(keys, holm(ps)))
    sp_ps = []
    for k in keys:
        v = res[k[1]][0][(k[2], k[3])] if k[0] == "f" else comp[(k[1], k[2], k[3])]
        sp_ps.append(v["test"].get("spread_p", 1.0))
    adj_sp = dict(zip(keys, holm(sp_ps)))

    # ---- 日內
    intraday_out = []
    if with_intraday and df60 is not None and len(df60):
        P = intraday_panel(df60, codes)
        if P is not None:
            ires = intraday_eval(P, panel, E["stock"], rng, panel["M"], list(panel["groups"].index))
            iks, ips = [], []
            for k, v in ires.items():
                iks.append(k); ips.append(v["test"].get("ic_p", 1.0))
            iadj = dict(zip(iks, holm(ips + [1.0] * 0)))
            for spec in INTRADAY:
                for level in ("group", "stock"):
                    v = ires[(spec["id"], level)]
                    pa = iadj[(spec["id"], level)]
                    vd, vt = verdict(v["train"], v["test"], pa, short_sample=False)
                    # 日內樣本天數 < 2 年且訓練段極短 → 一律不給「有效」
                    if vd == "pass":
                        vd, vt = "weak", "單看過校正，但日內樣本僅約 3 年、訓練段極短，只當線索"
                    intraday_out.append({"id": spec["id"], "level": level, "name": spec["name"], "mech": spec["mech"],
                                         "sign": spec["sign"], "train": v["train"], "test": v["test"],
                                         "p_holm": round(pa, 4), "verdict": vd, "verdict_text": vt})

    # ---- 輸出
    methods = []
    for level in ("group", "stock"):
        r, Fl = res[level]
        for fid in Fl:
            f = FACTOR_BY_ID[fid]
            stats, pas = {}, []
            for h in HORIZONS:
                v = r[(fid, h)]
                pa = adj[("f", level, fid, h)]
                vd, vt = verdict(v["train"], v["test"], pa, bool(f.get("short_sample")))
                v["test"]["p_holm"] = round(pa, 4)
                v["test"]["spread_p_holm"] = round(adj_sp[("f", level, fid, h)], 4)
                stats[str(h)] = {"train": v["train"], "test": v["test"], "verdict": vd}
                if vd == "pass":
                    pas.append(h)
            best = None
            # 整體判定：任一持有天數 pass → pass；否則取最強的
            order = ["pass", "weak", "short", "reverse", "unproven"]
            vds = [stats[str(h)]["verdict"] for h in HORIZONS]
            overall = next((o for o in order if o in vds), "unproven")
            text = {"pass": "樣本外有效", "weak": "單看顯著、未過多重比較校正", "short": "短樣本，只供參考",
                    "reverse": "樣本外方向相反", "unproven": "未證實"}[overall]
            methods.append({"id": fid, "level": level, "name": f["name"], "mech": f["mech"], "data": f["data"],
                            "since": f["since"], "sign": sign_of(fid, level), "verdict": overall, "verdict_text": text,
                            "passed_horizons": pas, "stats": stats})
    comps = []
    for (level, tag, h), v in sorted(comp.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        pa = adj[("c", level, tag, h)]
        v["test"]["p_holm"] = round(pa, 4)
        v["test"]["spread_p_holm"] = round(adj_sp[("c", level, tag, h)], 4)
        vd, vt = verdict(v["train"], v["test"], pa)
        comps.append({"level": level, "tag": tag, "h": h, "factors": v["ids"], "train": v["train"], "test": v["test"],
                      "verdict": vd, "verdict_text": vt})

    # ---- 重點方法：案例、穩健性、最新候選
    #   重點方法＝樣本外證據最強的三個（族群：法人買超、月營收年增率、綜合 A）＋個股綜合 A（對照）。
    #   綜合分數固定用 A（文獻方向等權，事先寫死），不挑樣本外最好的，避免事後選擇。
    mk_lv = np.exp(np.log1p(es["mk_cc"].fillna(0)).cumsum())
    mk20 = (mk_lv / mk_lv.shift(20) - 1)
    mk60 = (mk_lv / mk_lv.shift(60) - 1)
    focus = [("group", "INST10", "法人10日淨買超"), ("group", "REVYOY", "月營收年增率"),
             ("group", "A", "綜合分數A"), ("stock", "A", "綜合分數A")]
    cases, latest, robust, case_stats = [], [], [], []
    for level, fid, label in focus:
        Fl = res[level][1]
        if level == "group":
            Fl = {**Fl, **GRAW}           # 顯示用：原始數值（排名 z 對一般人沒有意義）
        elig = E[level]
        if fid == "A":
            if (level, "A", 20) not in comp:
                continue
            sc_ = comp[(level, "A", 20)]["_score"]
        else:
            sc_ = rank_z(Fl[fid]) * sign_of(fid, level)
        topn = CAND_GROUPS if level == "group" else CAND_STOCKS
        cs = cases_for(sc_, elig, Xs[level], Fl, level, names, gname, mk20, dates, topn, np.arange(60, T - 61, REBAL))
        mname = f"{level}-{fid}"
        cases += cs
        for c in cs:
            c["method"] = mname
            c["method_label"] = label
            c["period"] = "樣本外" if c["date"] >= TEST_START else "訓練期"
            c["explain"] = explain(c)
        for per in ("訓練期", "樣本外"):
            f20 = [c["fwd"]["20"] for c in cs if c["period"] == per and c["fwd"]["20"] is not None]
            f5 = [c["fwd"]["5"] for c in cs if c["period"] == per and c["fwd"]["5"] is not None]
            f60 = [c["fwd"]["60"] for c in cs if c["period"] == per and c["fwd"]["60"] is not None]
            if f20:
                lo, hi = wilson(int(sum(1 for x in f20 if x > 0)), len(f20))
                case_stats.append({"method": mname, "label": label, "period": per, "n": len(f20),
                                   "mean5": round(float(np.mean(f5)), 2) if f5 else None,
                                   "mean20": round(float(np.mean(f20)), 2), "median20": round(float(np.median(f20)), 2),
                                   "mean60": round(float(np.mean(f60)), 2) if f60 else None,
                                   "win20": round(sum(1 for x in f20 if x > 0) / len(f20), 3),
                                   "win20_ci": [round(lo, 3), round(hi, 3)]})
        # 穩健性：逐年、多空市況、TOP_Q 擾動（只用重新排名日；持有 20 日）
        rows20 = np.arange(60, T - 20, REBAL)
        yrs = np.array([dates[i][:4] for i in rows20])
        bull = np.array([bool(np.isfinite(mk60.iat[i]) and mk60.iat[i] >= 0) for i in rows20])
        st = cs_stats(sc_, Xs[level][20], elig, rows20, +1)
        by_year = []
        for y in sorted(set(yrs)):
            m = (yrs == y) & np.isfinite(st["top"])
            if m.sum() >= 5:
                by_year.append({"year": y, "n_dates": int(m.sum()), "ic": round(float(np.nanmean(st["ic"][m])), 4),
                                "spread": round(float(np.nanmean((st["top"] - st["uni"])[m])), 3)})
        regime = {}
        for nm, m0 in (("多頭(大盤60日≥0)", bull), ("空頭(大盤60日<0)", ~bull)):
            m = m0 & np.isfinite(st["top"])
            if m.sum() >= 5:
                regime[nm] = {"n_dates": int(m.sum()), "ic": round(float(np.nanmean(st["ic"][m])), 4),
                              "spread": round(float(np.nanmean((st["top"] - st["uni"])[m])), 3)}
        topq = {}
        for q in (0.1, 0.2, 0.3):
            stq = cs_stats(sc_, Xs[level][20], elig, rows20, +1, q=q)
            m = (rows20 >= split) & np.isfinite(stq["top"])
            if m.sum() >= 5:
                topq[str(q)] = {"n_dates": int(m.sum()), "spread": round(float(np.nanmean((stq["top"] - stq["uni"])[m])), 3)}
        robust.append({"method": mname, "label": label, "h": 20, "by_year": by_year, "regime": regime, "top_q_test": topq})
        # 最新候選
        last = T - 1
        sv = sc_.to_numpy(dtype=float)[last]
        okm = elig.to_numpy(dtype=bool)[last] & np.isfinite(sv)
        idx = np.flatnonzero(okm)
        top = idx[np.argsort(-sv[idx])[:topn]]
        for j in top:
            key = sc_.columns[j]
            latest.append({"level": level, "method": mname, "code": key,
                           "name": gname.get(key, key) if level == "group" else names.get(key, key),
                           "score": round(float(sv[j]), 2),
                           "factors": {k: (None if not np.isfinite(Fl[k].iat[last, j]) else round(float(Fl[k].iat[last, j]), 3))
                                       for k in Fl if k in ("MOM60", "H52", "INST10", "REVYOY", "REVACC", "VOLR", "MARGIN20", "SHARE")}})
    # JSON 體積控制：族群案例全留（樣本外），個股案例樣本外隨機抽 150、訓練期抽 60（統計用全部算，見 case_stats）
    keep = []
    rs = np.random.default_rng(SEED)
    by = {}
    for c in cases:
        by.setdefault((c["level"], c["method"], c["period"]), []).append(c)
    for (lvl, m, per), lst in by.items():
        cap = None if lvl == "group" and per == "樣本外" else (150 if per == "樣本外" else 60)
        if cap is not None and len(lst) > cap:
            idx = rs.choice(len(lst), cap, replace=False)
            lst = [lst[k] for k in sorted(idx)]
        keep += lst
    cases = keep

    # ---- 美股傳導（費半單日大漲 → 台股半導體族群）
    us = us_link(intl, panel, es, E, dates, rng)

    meta = {
        "latest": dates[-1], "first": dates[0], "train_end": TRAIN_END, "test_start": TEST_START,
        "horizons": list(HORIZONS), "rebalance_days": REBAL, "top_q": TOP_Q, "cost_pct": COST_PCT, "liq_min": LIQ_MIN,
        "entry": "訊號當天收盤後產生，隔日開盤進場；持有 h 日後以第 h 日收盤出場；超額＝減大盤（前一日成交值加權）",
        "verdict_rule": "樣本外：Holm 校正後 Rank IC p<0.05、入選組比母體平均多>0 且扣成本 0.47% 後仍>0、訓練期 IC 同方向、樣本日數≥20",
        "disclaimer": "統計研究輔助，不是買賣建議；歷史表現不代表未來。",
        "limits": ["族群成分用現在的 groups.yaml 套到歷史（成分回填偏誤，會使族群層結果偏樂觀）",
                   "下市股未來報酬缺值被剔除（存活者偏差）", "樣本約 6.8 年，其中 2024 起偏多頭，沒有完整的空頭樣本外",
                   "隔日開盤鎖漲停買不到仍當成買得到", "報酬不含現金股利",
                   "重疊持有期使相鄰日期相關：已用 Newey-West 與區塊自助法處理，但有效樣本比日期數少很多"],
        "untestable": NOT_TESTABLE,
        "n_tests": len(keys),
    }
    for c in comps:
        c.pop("_st", None)
    payload = {"meta": meta,
               "factors": [{"id": f["id"], "name": f["name"], "mech": f["mech"], "sign": f["sign"], "data": f["data"]} for f in FACTORS],
               "methods": methods, "composites": comps, "intraday": intraday_out, "us_link": us,
               "cases": cases, "case_stats": case_stats, "robust": robust, "latest": {"date": dates[-1], "candidates": latest}}
    return payload


def us_link(intl, panel, es, E, dates, rng) -> dict:
    """美股傳導：費半（^SOX）單日漲幅 ≥ +2% 之後，台股半導體鏈族群（5 日）是否比「所有日子」的同一籃子更好。
    兩種對齊都報：
      same ＝ 用美股日期 ≤ 台股訊號日 t 的收盤（美股 t 日收盤在台北 t+1 清晨，早於 t+1 開盤，可交易，但開盤跳空已吃掉大部分）；
      lag  ＝ 用美股日期 < t（更保守，等於晚一天才反應）。"""
    if intl is None or intl.empty:
        return {}
    s = intl[intl["symbol"] == "^SOX"][["date", "close"]].copy()
    s["date"] = s["date"].astype(str)
    s = s.drop_duplicates("date").set_index("date")["close"].astype(float).sort_index()
    r1 = s.pct_change()
    d = np.array(dates, dtype=str)
    chain = panel["groups"]["chain"]
    semi = [g for g in panel["groups"].index if str(chain.get(g, "")) == "semiconductor"]
    if not semi:
        return {}
    out = {"rule": "費半單日漲幅 ≥ +2% 後，隔日開盤買進台股半導體鏈族群（等權），持有 5 日；對照＝所有日子的同一籃子",
           "threshold_pct": 2.0, "semi_groups": len(semi)}
    X5 = ds.forward_excess(es["g_cc"][semi], es["g_oc"][semi], es["mk_cc"], es["mk_oc"], 5)
    basket = X5.where(E["group"][semi]).mean(axis=1)
    T = len(dates)
    split = int(np.searchsorted(np.array(dates), TEST_START))
    for variant, side in (("same", "right"), ("lag", "left")):
        pos = np.searchsorted(r1.index.to_numpy(dtype=str), d, side=side) - 1
        sig = pd.Series(np.where(pos >= 0, r1.to_numpy()[np.clip(pos, 0, None)], np.nan), index=dates)
        for nm, lo, hi in (("train", 0, split - 5), ("test", split, T - 5)):
            b = basket.iloc[lo:hi]
            sg = (sig.iloc[lo:hi] >= 0.02) & b.notna()
            key = f"{variant}_{nm}"
            if sg.sum() < 5:
                out[key] = {"n": int(sg.sum())}
                continue
            t, p = nw_t((b[sg] - b.mean()).to_numpy(), 5)
            out[key] = {"n": int(sg.sum()), "event_mean": round(float(b[sg].mean()), 3), "all_mean": round(float(b.mean()), 3),
                        "diff": round(float(b[sg].mean() - b.mean()), 3), "t": round(t, 2), "p": round(p, 4),
                        "hit": round(float((b[sg] > b.mean()).mean()), 3)}
    return out


def write(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def load_inputs():            # pragma: no cover — 手動驗證用
    import yaml
    from .. import config
    from ..util import store
    yrs = list(range(int(START[:4]), 2100))
    price = store.read("price_daily", years=yrs)
    inst = store.read("inst_daily", years=yrs)
    company = store.read("company_info")
    margin = store.read("margin_daily", years=yrs)
    revenue = store.read("revenue_monthly", years=list(range(2018, 2100)))
    sbl = store.read("sbl_daily")
    intl = store.read("intl_daily")
    from ..build_payload import last_complete_date
    latest = last_complete_date(price)
    price = price[price["date"].astype(str) <= latest]
    inst = inst[inst["date"].astype(str) <= latest]
    sc = yaml.safe_load((Path(config.ROOT) / "pipeline" / "groups" / "supply_chain.yaml").read_text(encoding="utf-8"))
    return price, inst, company, margin, revenue, sbl, intl, sc


def main() -> None:           # pragma: no cover
    import argparse
    from .. import config
    from ..util import store
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.SITE_DATA / "flowcheck" / "next_wave.json"))
    ap.add_argument("--no-intraday", action="store_true")
    a = ap.parse_args()
    price, inst, company, margin, revenue, sbl, intl, sc = load_inputs()
    df60 = None if a.no_intraday else store.read("intraday_60m")
    out = build(price, inst, company, margin, revenue, sbl, df60, sc, intl, with_intraday=not a.no_intraday)
    write(out, Path(a.out))
    log.info("寫出 %s", a.out)


if __name__ == "__main__":     # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    main()
