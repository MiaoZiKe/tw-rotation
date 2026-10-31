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
START = "2012-01-01"         # 第二版：資料起點拉到 2012（複核指出原版丟掉 8 年）
HOLD_END = "2019-12-31"      # 2012～2019＝保留樣本（規則不是用它定的，只用來看「沒看過的資料」效果還在不在）
TRAIN_START = "2020-01-01"   # 2020～2023＝訓練期（只看方向、挑綜合 B 的因子）
TRAIN_END = "2023-12-31"
TEST_START = "2024-01-01"    # 2024 起＝樣本外（判定只看這段）
HORIZONS = (5, 10, 20, 60)
REBAL = 1                    # 第二版：每天都排名（複核：每 5 日抽一天會受起點運氣影響），NW 滯後＝持有天數
FIRST_ROW = 130              # 因子暖機（52 週高點最少要 120 日）
FWD_LOG_MIN_PERIODS = 50     # 前瞻紀錄累積幾期才下結論（約一年，每 5 個交易日算一期）
PRIOR_TESTS = 24             # 同系列先前研究（20261030_daily_signals：8 規則 × 3 持有天數）也算進多重比較的假設數
COMP_A = ["MOM60", "MOM20", "REV5", "H52", "VOLR", "SHARE", "INST10", "TRUST10", "MARGIN20", "SHORTR", "REVYOY", "REVACC"]
TOP_Q = 0.2                  # 取排名最前 20% 當「入選組」
COST_PCT = 0.47
LIQ_MIN = 1e8
MIN_NAMES = 8                # 一天有效標的少於此數就不算那一天
BOOT_REPS = 1000
RAND_REPS = 300
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
    {"id": "FOREIGN10", "name": "外資單獨 10 日淨買超占成交量", "sign": +1, "levels": ("group", "stock"),
     "mech": "拆開看「力量是不是主要來自外資」（Seasholes et al. 2014；台大論文：外資買超有持續性）。第二版補測。",
     "data": "inst_daily", "since": "2012", "v2": True},
    {"id": "DEALER10", "name": "自營商單獨 10 日淨買超占成交量", "sign": +1, "levels": ("group", "stock"),
     "mech": "自營商含避險部位、資訊含量文獻弱，預期無效；列入是為了完整檢驗三大法人各自的角色。第二版補測。",
     "data": "inst_daily", "since": "2012", "v2": True},
    {"id": "SUE", "name": "季盈餘驚喜 SUE（季節性隨機漫步）", "sign": +1, "levels": ("group", "stock"),
     "mech": "盈餘後漂移：單季 EPS 比去年同季多出的部分，除以過去 8 季差額的標準差；市場對盈餘驚喜反應不足（Bernard & Thomas 1989，原始版本就用去年同季 EPS 當預期，不需要分析師）。法定公告日才可用。",
     "data": "financial_q", "since": "2012", "v2": True},
    {"id": "SUR", "name": "標準化未預期營收（年增率相對自己過去 12 個月）", "sign": +1, "levels": ("group", "stock"),
     "mech": "「年增率高」不等於「超出預期」；用自己過去 12 個月年增率的平均與波動標準化，才是月營收版的驚喜。法定公布日才可用。",
     "data": "revenue_monthly", "since": "2012", "v2": True},
    {"id": "REVHIGH", "name": "月營收創 12 個月新高程度（本月 ÷ 過去 12 個月最高）", "sign": +1, "levels": ("group", "stock"),
     "mech": "營收創新高代表需求仍在擴張，常見的基本面動能指標。法定公布日才可用。",
     "data": "revenue_monthly", "since": "2012", "v2": True},
    {"id": "BREADTH", "name": "族群廣度（成員站上 20 日線的比例）", "sign": +1, "levels": ("group",),
     "mech": "族群內多數成員一起上攻，與只有一檔帶動意義不同，是輪動確認指標。第二版補測。",
     "data": "price_daily", "since": "2012", "v2": True},
    {"id": "TRUSTQE", "name": "投信季底作帳（季末月 3/6/9/12 月的投信 10 日淨買超）", "sign": +1, "levels": ("group", "stock"),
     "mech": "投信季底有作帳（推升持股）動機（台大論文：投信可能年底作帳）；只在季末月排名。第二版補測。",
     "data": "inst_daily", "since": "2012", "v2": True},
    {"id": "CSMOM", "name": "下游客戶 20 日報酬（供應鏈傳導）", "sign": +1, "levels": ("stock",),
     "mech": "客戶的消息要慢慢傳到供應商，客戶報酬可預測供應商報酬（Cohen & Frazzini 2008）。母體僅 supply_chain.yaml 有台股客戶的公司。",
     "data": "supply_chain.yaml + price_daily", "since": "2020"},
]
FACTOR_BY_ID = {f["id"]: f for f in FACTORS}
# 因子「記憶長度」（交易日）：因子值本身變化很慢（滾動窗、月營收、季財報只在公布日才更新），
# 相鄰排名日的 IC 相關可達這麼多天。第二版自查（REVHIGH 個股）：NW 滯後只取持有天數 10 時 t=5.98，
# 取 21 變 5.19、取 42 變 4.74、每 21 日只抽一天變 3.22 → 慢因子的 t 被高估。所以 NW 滯後與區塊長度改為 max(持有天數, 記憶長度)，
# 較嚴格，且對所有因子一體適用（不是只針對看起來太漂亮的那幾個）。綜合分數含 60 日窗因子，一律 60。
FACTOR_MEMORY = {"MOM60": 60, "MOM20": 20, "REV5": 5, "H52": 60, "VOLR": 60, "SHARE": 20, "INST10": 10, "TRUST10": 10,
                 "FOREIGN10": 10, "DEALER10": 10, "TRUSTQE": 10, "MARGIN20": 20, "SHORTR": 20, "SBL20": 20, "CSMOM": 20,
                 "BREADTH": 20, "REVYOY": 21, "REVACC": 21, "SUR": 21, "REVHIGH": 21, "SUE": 63}
COMP_MEMORY = 60


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
    {"id": "DAYTRADE", "name": "當沖比過熱", "why": "daytrade_daily 只從 2025 起，短樣本，先累積。"},
    {"id": "GM", "name": "毛利率／營益率季改善", "why": "financial_q 有資料，本版尚未補測（列入下一輪）；營收與 SUE 已涵蓋基本面成長。"},
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


def _avail_wide(r: pd.DataFrame, cols: list, dates: list, codes: list, limit: int, clip=(-1, 5)) -> dict:
    """r 需有 code、avail（可用日字串）與各因子欄。可用日順延到「當天或之後第一個交易日」，當天收盤後才用，
    再向後填到下一次公布（最多 limit 個交易日，過期視為缺值）。"""
    dts = np.array(dates)
    r = r.copy()
    r["pos"] = np.searchsorted(dts, r["avail"].to_numpy(dtype=str), side="left")
    r = r[(r["pos"] < len(dts)) & r["code"].isin(set(codes))]
    out = {}
    for name in cols:
        x = r.dropna(subset=[name]).sort_values(["code", "pos"]).drop_duplicates(["pos", "code"], keep="last")
        w = pd.DataFrame(np.nan, index=range(len(dts)), columns=codes)
        piv = x.pivot(index="pos", columns="code", values=name)
        w.loc[piv.index, piv.columns] = piv.to_numpy()
        w = w.ffill(limit=limit)
        w.index = dates
        out[name] = w.clip(*clip[name] if isinstance(clip, dict) else clip)
    return out


def revenue_factors(rev: pd.DataFrame, dates: list, codes: list) -> dict:
    """月營收因子：yoy（年增率）、acc（年增加速）、sur（標準化未預期營收）、high（創 12 個月新高程度）。
    ★ 可用日＝法定公布日（announce_date，次月 10 日）順延到當天或之後第一個交易日，當天收盤後才能用
    （隔天開盤進場），所以不會偷看。YoY 自己用同一檔「去年同月」營收算，不依賴缺值多的 yoy_pct 欄。"""
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
    g = r.groupby("code")
    r["acc"] = r["yoy"] - g["yoy"].shift(3)
    # SUR：本月年增率相對「前 12 個月」年增率的平均與波動（不含本月，至少 8 個月）
    hist = g["yoy"].shift(1)
    mu = hist.groupby(r["code"]).rolling(12, min_periods=8).mean().reset_index(level=0, drop=True)
    sd = hist.groupby(r["code"]).rolling(12, min_periods=8).std().reset_index(level=0, drop=True)
    r["sur"] = (r["yoy"] - mu) / sd.clip(lower=0.05)
    # 創新高程度：本月 ÷ 前 12 個月最高（不含本月）
    mx = g["revenue"].shift(1).groupby(r["code"]).rolling(12, min_periods=8).max().reset_index(level=0, drop=True)
    r["high"] = (r["revenue"] / mx).where(mx > 0)
    # 公布日缺值（舊資料）→ 用「次月 10 日」法定日補；寧晚勿早
    ann = pd.to_datetime(r["announce_date"], errors="coerce")
    legal = (r["p"] + 1).dt.to_timestamp() + pd.Timedelta(days=9)
    r["avail"] = ann.fillna(legal).dt.strftime("%Y-%m-%d")
    out = _avail_wide(r, ["yoy", "acc", "sur", "high"], dates, codes, 45,
                      clip={"yoy": (-1, 5), "acc": (-1, 5), "sur": (-6, 6), "high": (0, 3)})
    return out


def _legal_deadline(year: int, quarter: int) -> str:
    """財報法定公告日（config.FINANCIAL_DEADLINES 同口徑）：Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31。"""
    return {1: f"{year}-05-15", 2: f"{year}-08-14", 3: f"{year}-11-14", 4: f"{year + 1}-03-31"}[int(quarter)]


def eps_factors(fq: pd.DataFrame, dates: list, codes: list) -> dict:
    """SUE（季節性隨機漫步）：(EPS_q − EPS_{q−4}) ÷ 過去 8 季同樣差額的標準差（不含本季，至少 6 季）。
    ★ 可用日用 announce_date，但不早於法定公告日（資料若標得比法定早，以法定為準；寧晚勿早），
    順延到當天或之後第一個交易日。單季 EPS 為單季值（financial_q 註明）。"""
    f = fq[["year", "quarter", "code", "announce_date", "eps"]].copy()
    f["code"] = f["code"].astype(str)
    f["year"] = pd.to_numeric(f["year"], errors="coerce")
    f["quarter"] = pd.to_numeric(f["quarter"], errors="coerce")
    f["eps"] = pd.to_numeric(f["eps"], errors="coerce")
    f = f.dropna(subset=["year", "quarter", "eps"]).drop_duplicates(["year", "quarter", "code"], keep="last")
    f["k"] = (f["year"] * 4 + f["quarter"] - 1).astype(int)
    prev = f[["code", "k", "eps"]].copy()
    prev["k"] = prev["k"] + 4
    f = f.merge(prev.rename(columns={"eps": "eps_ly"}), on=["code", "k"], how="left").sort_values(["code", "k"])
    f["diff"] = f["eps"] - f["eps_ly"]
    h = f.groupby("code")["diff"].shift(1)
    sd = h.groupby(f["code"]).rolling(8, min_periods=6).std().reset_index(level=0, drop=True)
    f["sue"] = f["diff"] / sd.clip(lower=0.1)
    legal = [_legal_deadline(int(y), int(q)) for y, q in zip(f["year"], f["quarter"])]
    ann = pd.to_datetime(f["announce_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("9999-12-31")
    f["avail"] = [max(a_, l_) for a_, l_ in zip(ann.tolist(), legal)]   # 字串日期可直接比大小
    return _avail_wide(f, ["sue"], dates, codes, 70, clip=(-6, 6))


def _group_agg(z: pd.DataFrame, B: np.ndarray, gids: list, min_n: int = 3) -> pd.DataFrame:
    """成員橫斷面名次 z 的族群平均（至少 min_n 個成員有值）。研究與前瞻紀錄共用，口徑一致。"""
    ok = z.notna().to_numpy().astype(float)
    num = np.nan_to_num(z.to_numpy(dtype=float)) @ B
    den = ok @ B
    return pd.DataFrame(np.where(den >= min_n, num / np.where(den > 0, den, 1), np.nan), index=z.index, columns=gids)


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
                  pairs: list | None, foreign: pd.DataFrame | None = None, dealer: pd.DataFrame | None = None,
                  sue: pd.DataFrame | None = None) -> dict:
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
    if foreign is not None:
        F["FOREIGN10"] = (foreign.rolling(10, min_periods=8).sum() / vsum).where(vsum > 0)
    if dealer is not None:
        F["DEALER10"] = (dealer.rolling(10, min_periods=8).sum() / vsum).where(vsum > 0)
    months = np.array([int(d[5:7]) for d in cc.index])
    qe = np.isin(months, (3, 6, 9, 12))
    F["TRUSTQE"] = F["TRUST10"].where(pd.DataFrame(np.broadcast_to(qe[:, None], cc.shape), index=cc.index, columns=cc.columns))          # 只在季末月有值
    F["BREADTH"] = (lv > lv.rolling(20, min_periods=15).mean()).astype(float).where(lv.notna())
    if sue is not None:
        F["SUE"] = sue
    if margin is not None:
        F["MARGIN20"] = (margin / margin.shift(20) - 1).where(margin.shift(20) > 0)
        if short is not None:
            F["SHORTR"] = (short / margin).where(margin > 100)
    if sbl is not None:
        F["SBL20"] = (sbl / sbl.shift(20) - 1).where(sbl.shift(20) > 0)
    if rev is not None:
        F["REVYOY"], F["REVACC"] = rev["yoy"], rev["acc"]
        F["SUR"], F["REVHIGH"] = rev["sur"], rev["high"]
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
    for fid in ("INST10", "TRUST10", "MARGIN20", "SHORTR", "REVYOY", "REVACC",
                "FOREIGN10", "DEALER10", "SUE", "SUR", "REVHIGH", "TRUSTQE"):
        if fid not in SF:
            continue
        F[fid] = _group_agg(rank_z(SF[fid]), B, gids)
    if "BREADTH" in SF:                      # 廣度：成員「站上 20 日線」的比例（原始比例，不用名次）
        b = SF["BREADTH"]
        ok = b.notna().to_numpy().astype(float)
        den = ok @ B
        F["BREADTH"] = pd.DataFrame(np.where(den >= 3, (np.nan_to_num(b.to_numpy(dtype=float)) @ B) / np.where(den > 0, den, 1), np.nan),
                                    index=b.index, columns=gids)
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
def cs_multi(F: pd.DataFrame, Xs: dict, elig: pd.DataFrame, rows: np.ndarray, sign: int, q: float = TOP_Q) -> dict:
    """在指定排名日（rows）逐日算：Rank IC、入選組平均超額、母體平均超額、入選檔數；一次處理多個持有天數（名次只排一次）。
    回傳 {h: {"ic","top","uni","k"}}。"""
    fv = F.to_numpy(dtype=float) * sign
    ev = elig.to_numpy(dtype=bool)
    xv = {h: X.to_numpy(dtype=float) for h, X in Xs.items()}
    out = {h: {"ic": [], "top": [], "uni": [], "k": []} for h in Xs}
    for i in rows:
        base = ev[i] & np.isfinite(fv[i])
        if base.sum() < MIN_NAMES:
            for h in Xs:
                for k in out[h]:
                    out[h][k].append(np.nan if k != "k" else 0)
            continue
        for h in Xs:
            ok = base & np.isfinite(xv[h][i])
            n = int(ok.sum())
            if n < MIN_NAMES:
                for k in out[h]:
                    out[h][k].append(np.nan if k != "k" else 0)
                continue
            f, x = fv[i][ok], xv[h][i][ok]
            rf = f.argsort().argsort().astype(float)
            rx = x.argsort().argsort().astype(float)
            out[h]["ic"].append(float(np.corrcoef(rf, rx)[0, 1]))
            k = max(int(round(n * q)), 3)
            out[h]["top"].append(float(x[rf >= n - k].mean()))
            out[h]["uni"].append(float(x.mean()))
            out[h]["k"].append(k)
    return {h: {k: np.array(v) for k, v in d.items()} for h, d in out.items()}


def cs_stats(F: pd.DataFrame, X: pd.DataFrame, elig: pd.DataFrame, rows: np.ndarray, sign: int, q: float = TOP_Q) -> dict:
    """單一持有天數的版本（日內與穩健性用）。"""
    return cs_multi(F, {0: X}, elig, rows, sign, q)[0]


def summarize(st: dict, h: int, rng, seg: np.ndarray, memory: int = 0) -> dict:
    """seg：布林，哪些排名日屬於這一段。每天排名、持有期重疊 → NW 滯後＝持有天數、有效樣本＝日數 ÷ 持有天數。"""
    ic, top, uni = st["ic"][seg], st["top"][seg], st["uni"][seg]
    ok = np.isfinite(ic) & np.isfinite(top)
    ic, top, uni = ic[ok], top[ok], uni[ok]
    n = int(ok.sum())
    if n < 5:
        return {"n_dates": n}
    lag = max(int(h), int(memory), 1)
    t_ic, p_ic = nw_t(ic, lag)
    spread = top - uni
    t_sp, p_sp = nw_t(spread, lag)
    hit_k = int((spread > 0).sum())
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
        "net": round(float(spread.mean()) - COST_PCT, 3),   # 扣成本後比隨機多（每期換股一趟，保守）
    }


def holm(ps: list[float]) -> list[float]:
    return ds._holm([1.0 if not np.isfinite(p) else p for p in ps])


def verdict(tr: dict, te: dict, p_holm: float, short_sample: bool = False) -> tuple[str, str]:
    """第二版判定（複核後降級）：本研究**不再輸出「有效（pass）」**。
    experimental＝樣本外：Holm 校正（含整個系列的假設數）後 IC p<0.05、入選組比母體多>0 且扣成本後>0、訓練期 IC 同方向、樣本日數≥20；
    僅代表「值得做前瞻紀錄」，不代表可以交易。"""
    if te.get("n_dates", 0) < 20:
        return "unproven", "樣本不足"
    if short_sample:
        return "short", "短樣本（< 2 年），只供參考"
    same_dir = tr.get("ic", 0) > 0
    if p_holm < 0.05 and te["spread"] > 0 and te["net"] > 0 and same_dir:
        return "experimental", "實驗訊號：樣本外過多重比較校正，但幅度薄、依賴多頭，需前瞻紀錄驗證"
    if te["ic"] < 0 and te["ic_p"] > 0.95:
        return "reverse", "樣本外方向相反"
    if te["ic_p"] < 0.05 and p_holm >= 0.05:
        return "weak", "單看顯著、但沒過多重比較校正"
    return "unproven", "未證實（與隨機無顯著差異）"


def seg_masks(dates: list, rows: np.ndarray, h: int) -> dict:
    """三段（保留／訓練／樣本外）的排名日遮罩；各段的持有期不跨進下一段（避免標籤洩漏）。"""
    d = np.array(dates)
    i_train = int(np.searchsorted(d, TRAIN_START))
    i_test = int(np.searchsorted(d, TEST_START))
    T = len(dates)
    return {"hold": rows < i_train - h,
            "train": (rows >= i_train) & (rows < i_test - h),
            "test": (rows >= i_test) & (rows < T - h)}


def run_level(level: str, F: dict, elig: pd.DataFrame, cc, oc, mk_cc, mk_oc, dates: list, rng) -> dict:
    """某一層級（族群／個股）所有因子 × 持有天數的統計（每天排名）。"""
    T = len(dates)
    X = {h: ds.forward_excess(cc, oc, mk_cc, mk_oc, h) for h in HORIZONS}
    rows = np.arange(FIRST_ROW, T)
    out = {}
    for fid, fr in F.items():
        stm = cs_multi(fr, X, elig, rows, sign_of(fid, level))
        for h in HORIZONS:
            st = stm[h]
            m = seg_masks(dates, rows, h)
            mem = FACTOR_MEMORY.get(fid, 21)
            out[(fid, h)] = {"hold": summarize(st, h, rng, m["hold"], mem), "train": summarize(st, h, rng, m["train"], mem),
                             "test": summarize(st, h, rng, m["test"], mem), "_st": st, "_rows": rows}
    return out, X


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
FWD_METHOD = "INST10_G"
FWD_RULE = "族群層、外資＋投信 10 日淨買超占成交量（成員名次 z 平均）、排名前 20%、每個交易日排名、隔日開盤進場（規則 v1，寫死不調）"
FWD_RETIRE = f"前瞻紀錄累積 {FWD_LOG_MIN_PERIODS} 期（每 5 個交易日算一期）後，10 日平均「入選比母體多」≤ 0 就改標「已失效」，不調參數救它"


def forward_candidates(price, inst, company, names=None, tail_days: int = 120) -> pd.DataFrame:
    """前瞻紀錄：只用最近 tail_days 個交易日（名次只看當天橫斷面，滾動窗最多 10 日），算最新一天的 INST10 族群入選名單。
    與 build() 的 INST10 族群因子同一套函式（_group_agg／rank_z／eligibility），口徑一致；每天寫進資料湖
    `next_wave_forward`（store.append，只增不改），之後才有「不受回填與多重比較影響」的真實驗證。"""
    cols = ["date", "method", "group_id", "name", "rank", "score", "k", "n_universe", "rule"]
    dl = sorted(set(price["date"].astype(str)))[-tail_days:]
    if len(dl) < 30:
        return pd.DataFrame(columns=cols)
    start = dl[0]
    pr = price[price["date"].astype(str) >= start]
    ins = inst[inst["date"].astype(str) >= start]
    panel = ds.build_panel(pr, ins, company, start=start)
    es = ds.entity_series(panel)
    dates, codes = panel["dates"], panel["codes"]
    volume = _wide(pr[["date", "code", "volume"]], "volume", dates, codes)
    vsum = volume.rolling(10, min_periods=8).sum()
    inst10 = (panel["net"].rolling(10, min_periods=8).sum() / vsum).where(vsum > 0)
    gids = list(panel["groups"].index)
    G = _group_agg(rank_z(inst10), (panel["M"] > 0).astype(float), gids)
    E = eligibility(panel, es)["group"]
    last = len(dates) - 1
    ok = E.to_numpy(dtype=bool)[last] & np.isfinite(G.to_numpy(dtype=float)[last])
    n = int(ok.sum())
    if n < MIN_NAMES:
        return pd.DataFrame(columns=cols)
    sv = G.to_numpy(dtype=float)[last]
    idx = np.flatnonzero(ok)
    k = max(int(round(n * TOP_Q)), 3)
    top = idx[np.argsort(-sv[idx])[:k]]
    gname = panel["groups"]["group_name"].to_dict()
    rows = [{"date": dates[last], "method": FWD_METHOD, "group_id": gids[j], "name": gname.get(gids[j], gids[j]),
             "rank": r + 1, "score": round(float(sv[j]), 4), "k": k, "n_universe": n, "rule": FWD_RULE}
            for r, j in enumerate(top)]
    return pd.DataFrame(rows, columns=cols)


def forward_status(log: pd.DataFrame | None, dates: list, es: dict, E_group: pd.DataFrame) -> dict:
    """前瞻紀錄的成績單與下架判定。每 5 個「紀錄日」算一期；期數不足 FWD_LOG_MIN_PERIODS 一律「收集中」。"""
    base = {"method": FWD_METHOD, "rule": FWD_RULE, "retire_rule": FWD_RETIRE, "min_periods": FWD_LOG_MIN_PERIODS,
            "n_logged_days": 0, "n_periods": 0, "mean_spread_5": None, "mean_spread_10": None, "hit_10": None,
            "status": "collecting", "status_text": "收集中（前瞻紀錄剛開始，還不能下結論）"}
    if log is None or len(log) == 0:
        return base
    lg = log[log["method"] == FWD_METHOD].copy()
    lg["date"] = lg["date"].astype(str)
    days = sorted(set(lg["date"]) & set(dates))
    base["n_logged_days"] = len(days)
    if not days:
        return base
    base["first_date"], base["last_date"] = days[0], days[-1]
    sel = days[::5]
    X = {h: ds.forward_excess(es["g_cc"], es["g_oc"], es["mk_cc"], es["mk_oc"], h) for h in (5, 10)}
    pos = {d: i for i, d in enumerate(dates)}
    sp = {5: [], 10: []}
    for d in sel:
        i = pos[d]
        chosen = set(lg.loc[lg["date"] == d, "group_id"])
        for h in (5, 10):
            row = X[h].iloc[i]
            uni = row[E_group.iloc[i].to_numpy(dtype=bool)].dropna()
            top = row[[g for g in row.index if g in chosen]].dropna()
            if len(top) and len(uni):
                sp[h].append(float(top.mean() - uni.mean()))
    n = len(sp[10])
    base["n_periods"] = n
    if sp[5]:
        base["mean_spread_5"] = round(float(np.mean(sp[5])), 3)
    if sp[10]:
        base["mean_spread_10"] = round(float(np.mean(sp[10])), 3)
        base["hit_10"] = round(float(np.mean(np.array(sp[10]) > 0)), 3)
    if n >= FWD_LOG_MIN_PERIODS:
        if base["mean_spread_10"] <= 0:
            base["status"], base["status_text"] = "retired", "已失效（前瞻紀錄滿期、平均沒有比母體多，依事先寫死的條件下架）"
        else:
            base["status"], base["status_text"] = "alive", "前瞻紀錄滿期且平均為正（仍是實驗訊號，不是買賣建議）"
    else:
        base["status_text"] = f"收集中（已 {n} 期／需 {FWD_LOG_MIN_PERIODS} 期）"
    return base


def _yr(dates, rows):
    return np.array([dates[i][:4] for i in rows])


def build(price, inst, company, margin, revenue, sbl, df60, sc, intl, names=None, *, fq=None, fwd_log=None,
          with_intraday=True) -> dict:
    rng = np.random.default_rng(SEED)
    panel = ds.build_panel(price, inst, company, start=START)
    es = ds.entity_series(panel)
    dates, codes = panel["dates"], panel["codes"]
    T = len(dates)
    if names is None and company is not None and not company.empty:
        names = company.dropna(subset=["name"]).drop_duplicates("code", keep="last").set_index("code")["name"].to_dict()
    names = names or {}
    volume = _wide(price[["date", "code", "volume"]], "volume", dates, codes)
    trust = _wide(inst, "trust", dates, codes).fillna(0)
    foreign = _wide(inst, "foreign_total", dates, codes).fillna(0)
    dealer = _wide(inst, "dealer", dates, codes).fillna(0)
    mg = _wide(margin, "margin_balance", dates, codes) if margin is not None and len(margin) else None
    sh = _wide(margin, "short_balance", dates, codes) if margin is not None and len(margin) else None
    sb = _wide(sbl, "sbl_balance", dates, codes) if sbl is not None and len(sbl) else None
    rv = revenue_factors(revenue, dates, codes) if revenue is not None and len(revenue) else None
    sue = eps_factors(fq, dates, codes)["sue"] if fq is not None and len(fq) else None
    pairs = customer_pairs(sc, codes) if sc else []
    SF = stock_factors(panel, volume, trust, rv, mg, sh, sb, pairs, foreign, dealer, sue)
    del volume, trust, foreign, dealer, mg, sh, sb
    GF = group_factors(panel, es, SF)
    E = eligibility(panel, es)
    GRAW = group_raw(panel, SF)
    gname = panel["groups"]["group_name"].to_dict()

    res, Xs = {}, {}
    for level, F, cc, oc, elig in (("group", GF, es["g_cc"], es["g_oc"], E["group"]),
                                   ("stock", SF, panel["cc"], panel["oc"], E["stock"])):
        Fl = {k: v for k, v in F.items() if level in FACTOR_BY_ID[k]["levels"]}
        r, X = run_level(level, Fl, elig, cc, oc, es["mk_cc"], es["mk_oc"], dates, rng)
        res[level] = (r, Fl)
        Xs[level] = X
    if "CSMOM" in SF:                       # 客戶動能：母體限縮到「有客戶」的那幾檔
        e2 = E["stock"] & SF["CSMOM"].notna()
        r2, _ = run_level("stock", {"CSMOM": SF["CSMOM"]}, e2, panel["cc"], panel["oc"], es["mk_cc"], es["mk_oc"], dates, rng)
        res["stock"][0].update(r2)

    # ---- 綜合分數：A＝原 12 個因子文獻方向等權（固定名單，與第一版相同）；B＝訓練期（2020～2023）挑 NW t>1.5
    comp = {}
    rows_all = np.arange(FIRST_ROW, T)
    for level in ("group", "stock"):
        r, Fl = res[level]
        ids_a = [i for i in COMP_A if i in Fl]
        ids_b = [i for i in train_select(r, level) if i in ids_a]
        for tag, ids in (("A", ids_a), ("B", ids_b)):
            if not ids:
                continue
            sc_ = composite(Fl, level, ids)
            stm = cs_multi(sc_, Xs[level], E[level], rows_all, +1)
            for h in HORIZONS:
                m = seg_masks(dates, rows_all, h)
                comp[(level, tag, h)] = {"ids": ids, "hold": summarize(stm[h], h, rng, m["hold"], COMP_MEMORY),
                                         "train": summarize(stm[h], h, rng, m["train"], COMP_MEMORY),
                                         "test": summarize(stm[h], h, rng, m["test"], COMP_MEMORY), "_st": stm[h], "_score": sc_}
    # 隨機基準 p（綜合分數）：樣本外每 5 個排名日取一天，同日同檔數隨機抽 → 平均超額分布
    for (level, tag, h), v in comp.items():
        st = v["_st"]
        m = seg_masks(dates, rows_all, h)["test"] & np.isfinite(st["top"])
        sub = np.flatnonzero(m)[::5]
        if len(sub) < 5:
            continue
        X = Xs[level][h].to_numpy(dtype=float)
        el = E[level].to_numpy(dtype=bool)
        obs = float(np.nanmean(st["top"][sub]))
        sim, cnt = np.zeros(RAND_REPS), 0
        for ri in sub:
            i = rows_all[ri]
            pool = X[i][el[i] & np.isfinite(X[i])]
            k = int(st["k"][ri])
            if pool.size < k or k == 0:
                continue
            sim += pool[rng.integers(0, pool.size, size=(RAND_REPS, k))].mean(axis=1)
            cnt += 1
        if cnt:
            sim /= cnt
            v["test"]["rand_mean"] = round(float(sim.mean()), 3)
            v["test"]["rand_p"] = round(float((sim >= obs).mean()), 4)

    # ---- 日內與費半（併入同一個多重比較族）
    ires = {}
    if with_intraday and df60 is not None and len(df60):
        P = intraday_panel(df60, codes)
        if P is not None:
            ires = intraday_eval(P, panel, E["stock"], rng, panel["M"], list(panel["groups"].index))
    us = us_link(intl, panel, es, E, dates, rng)

    # ---- Holm：本研究所有假設放同一族（單因子＋綜合＋日內＋費半），另加先前系列研究的 PRIOR_TESTS 個（p 以 1 計，只抬高門檻）
    keys, ps, sps = [], [], []
    for level in ("group", "stock"):
        for (fid, h), v in res[level][0].items():
            keys.append(("f", level, fid, h)); ps.append(v["test"].get("ic_p", 1.0)); sps.append(v["test"].get("spread_p", 1.0))
    for (level, tag, h), v in comp.items():
        keys.append(("c", level, tag, h)); ps.append(v["test"].get("ic_p", 1.0)); sps.append(v["test"].get("spread_p", 1.0))
    for (fid, level), v in ires.items():
        keys.append(("i", fid, level)); ps.append(v["test"].get("ic_p", 1.0)); sps.append(v["test"].get("spread_p", 1.0))
    for var in ("same_test", "lag_test"):
        if isinstance(us.get(var), dict) and us[var].get("p") is not None:
            keys.append(("u", var)); ps.append(us[var]["p"]); sps.append(us[var]["p"])
    n_ours = len(keys)
    adj = dict(zip(keys, holm(ps + [1.0] * PRIOR_TESTS)[:n_ours]))
    adj_sp = dict(zip(keys, holm(sps + [1.0] * PRIOR_TESTS)[:n_ours]))

    intraday_out = []
    for spec in INTRADAY:
        for level in ("group", "stock"):
            v = ires.get((spec["id"], level))
            if not v:
                continue
            pa = adj[("i", spec["id"], level)]
            vd, vt = verdict(v["train"], v["test"], pa)
            if vd == "experimental":
                vd, vt = "weak", "單看過校正，但日內樣本僅約 3 年、訓練段極短，只當線索"
            intraday_out.append({"id": spec["id"], "level": level, "name": spec["name"], "mech": spec["mech"], "sign": spec["sign"],
                                 "train": v["train"], "test": v["test"], "p_holm": round(pa, 4), "verdict": vd, "verdict_text": vt})

    VTXT = {"experimental": "實驗訊號（過多重比較校正，但幅度薄、依賴多頭，需前瞻驗證）", "weak": "單看顯著、未過多重比較校正",
            "short": "短樣本，只供參考", "reverse": "樣本外方向相反", "unproven": "未證實"}
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
                stats[str(h)] = {"hold": v["hold"], "train": v["train"], "test": v["test"], "verdict": vd}
                if vd == "experimental":
                    pas.append(h)
            vds = [stats[str(h)]["verdict"] for h in HORIZONS]
            overall = next((o for o in ["experimental", "weak", "short", "reverse", "unproven"] if o in vds), "unproven")
            hold_ok = bool(pas) and all(stats[str(h)]["hold"].get("ic", -1) > 0 for h in pas)
            show = (level == "group" and fid == "INST10")      # 網站只放這一個（CEO 複核後的決定）；其餘一律不上網站
            methods.append({"id": fid, "level": level, "name": f["name"], "mech": f["mech"], "data": f["data"],
                            "since": f["since"], "v2": bool(f.get("v2")), "sign": sign_of(fid, level), "verdict": overall,
                            "verdict_text": VTXT[overall], "experimental_horizons": pas,
                            "hold_same_direction": hold_ok if pas else None, "show_on_site": show, "stats": stats})
    comps = []
    for (level, tag, h), v in sorted(comp.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        v["test"]["p_holm"] = round(adj[("c", level, tag, h)], 4)
        v["test"]["spread_p_holm"] = round(adj_sp[("c", level, tag, h)], 4)
        vd, vt = verdict(v["train"], v["test"], v["test"]["p_holm"])
        comps.append({"level": level, "tag": tag, "h": h, "factors": v["ids"], "hold": v["hold"], "train": v["train"],
                      "test": v["test"], "verdict": vd, "verdict_text": vt})

    # ---- 重點方法：案例、穩健性、最新候選（只輸出族群候選）
    mk_lv = np.exp(np.log1p(es["mk_cc"].fillna(0)).cumsum())
    mk20 = (mk_lv / mk_lv.shift(20) - 1)
    mk60 = (mk_lv / mk_lv.shift(60) - 1)
    focus = [("group", "INST10", "法人10日淨買超"), ("group", "REVYOY", "月營收年增率"),
             ("group", "A", "綜合分數A"), ("stock", "A", "綜合分數A")]
    i_test = int(np.searchsorted(np.array(dates), TEST_START))
    i_train = int(np.searchsorted(np.array(dates), TRAIN_START))

    def period_of(d):
        return "保留樣本" if d < TRAIN_START else ("訓練期" if d < TEST_START else "樣本外")
    cases, latest, robust, case_stats = [], [], [], []
    for level, fid, label in focus:
        Fl = res[level][1]
        if level == "group":
            Fl = {**Fl, **GRAW}
        elig = E[level]
        if fid == "A":
            if (level, "A", 20) not in comp:
                continue
            sc_ = comp[(level, "A", 20)]["_score"]
        else:
            sc_ = rank_z(res[level][1][fid]) * sign_of(fid, level)
        topn = CAND_GROUPS if level == "group" else CAND_STOCKS
        cs = cases_for(sc_, elig, Xs[level], Fl, level, names, gname, mk20, dates, topn, np.arange(FIRST_ROW, T - 61, 5))
        mname = f"{level}-{fid}"
        for c in cs:
            c["method"], c["method_label"], c["period"] = mname, label, period_of(c["date"])
            c["explain"] = explain(c)
        cases += cs
        for per in ("保留樣本", "訓練期", "樣本外"):
            g = [c for c in cs if c["period"] == per]
            f20 = [c["fwd"]["20"] for c in g if c["fwd"]["20"] is not None]
            f5 = [c["fwd"]["5"] for c in g if c["fwd"]["5"] is not None]
            f60 = [c["fwd"]["60"] for c in g if c["fwd"]["60"] is not None]
            if f20:
                lo, hi = wilson(int(sum(1 for x in f20 if x > 0)), len(f20))
                case_stats.append({"method": mname, "label": label, "period": per, "n": len(f20),
                                   "mean5": round(float(np.mean(f5)), 2) if f5 else None,
                                   "mean20": round(float(np.mean(f20)), 2), "median20": round(float(np.median(f20)), 2),
                                   "mean60": round(float(np.mean(f60)), 2) if f60 else None,
                                   "win20": round(sum(1 for x in f20 if x > 0) / len(f20), 3),
                                   "win20_ci": [round(lo, 3), round(hi, 3)]})
        # 穩健性（每天排名）：逐年、多空市況（全期與樣本外）、入選比例擾動
        rr = np.arange(FIRST_ROW, T - 20)
        yrs = _yr(dates, rr)
        bull = np.array([bool(np.isfinite(mk60.iat[i]) and mk60.iat[i] >= 0) for i in rr])
        stm = cs_multi(sc_, {h: Xs[level][h] for h in (5, 10, 20)}, elig, rr, +1)
        by_year, regime, regime_test = {}, {}, {}
        for h in (5, 10, 20):
            st = stm[h]
            ex = np.isfinite(st["top"])
            sp = st["top"] - st["uni"]
            by_year[str(h)] = [{"year": y, "n_dates": int(((yrs == y) & ex).sum()),
                                "ic": round(float(np.nanmean(st["ic"][(yrs == y) & ex])), 4),
                                "spread": round(float(np.nanmean(sp[(yrs == y) & ex])), 3)}
                               for y in sorted(set(yrs)) if ((yrs == y) & ex).sum() >= 20]
            for nm, m0 in (("多頭", bull), ("空頭", ~bull)):
                for dct, extra in ((regime, np.ones(len(rr), bool)), (regime_test, rr >= i_test)):
                    m = m0 & ex & extra
                    if m.sum() >= 20:
                        dct.setdefault(str(h), {})[nm] = {"n_dates": int(m.sum()), "ic": round(float(np.nanmean(st["ic"][m])), 4),
                                                          "spread": round(float(np.nanmean(sp[m])), 3)}
        topq = {}
        for q in (0.1, 0.2, 0.3):
            sq = cs_multi(sc_, {20: Xs[level][20]}, elig, rr, +1, q=q)[20]
            m = (rr >= i_test) & np.isfinite(sq["top"])
            if m.sum() >= 20:
                topq[str(q)] = {"n_dates": int(m.sum()), "spread": round(float(np.nanmean((sq["top"] - sq["uni"])[m])), 3)}
        robust.append({"method": mname, "label": label, "by_year": by_year, "regime_all": regime, "regime_test": regime_test,
                       "top_q_test_h20": topq})
        if level == "group":                      # 只輸出族群候選（個股層 INST10 不成立，不提供個股名單）
            last = T - 1
            sv = sc_.to_numpy(dtype=float)[last]
            idx = np.flatnonzero(elig.to_numpy(dtype=bool)[last] & np.isfinite(sv))
            for j in idx[np.argsort(-sv[idx])[:topn]]:
                key = sc_.columns[j]
                latest.append({"level": level, "method": mname, "show_on_site": mname == "group-INST10", "code": key, "name": gname.get(key, key),
                               "score": round(float(sv[j]), 2),
                               "factors": {k: (None if not np.isfinite(Fl[k].iat[last, j]) else round(float(Fl[k].iat[last, j]), 3))
                                           for k in Fl if k in ("MOM60", "H52", "INST10", "REVYOY", "REVACC", "VOLR", "MARGIN20", "SHARE")}})
    # JSON 體積控制：只輸出族群案例（族群樣本外全留，其餘各段抽樣）；個股案例只留統計（case_stats）
    rs = np.random.default_rng(SEED)
    by = {}
    for c in cases:
        if c["level"] == "group":
            by.setdefault((c["method"], c["period"]), []).append(c)
    cases = []
    for (m, per), lst in by.items():
        if per != "樣本外" and len(lst) > 60:
            lst = [lst[k] for k in sorted(rs.choice(len(lst), 60, replace=False))]
        cases += lst

    # ---- 白話警語（複核要求：旁邊固定四句，數字由資料算出）
    gm = next((m for m in methods if m["level"] == "group" and m["id"] == "INST10"), None)
    caveats, samples = [], {}
    if gm:
        s5, s10 = gm["stats"]["5"], gm["stats"]["10"]
        te5, te10, h5, h10 = s5["test"], s10["test"], s5["hold"], s10["hold"]
        rb = next((r_ for r_ in robust if r_["method"] == "group-INST10"), None)
        y26 = next((y for y in (rb["by_year"].get("10", []) if rb else []) if y["year"] == "2026"), None)
        bear = (rb["regime_test"].get("10", {}).get("空頭") if rb else None)
        caveats = [
            f"樣本外（2024-01 起）：持有 5 日平均比母體多 {te5.get('spread')}%、10 日多 {te10.get('spread')}%"
            f"（{te5.get('n_dates')} 個排名日，有效獨立期約 {te5.get('n_eff')}／{te10.get('n_eff')} 期）。",
            f"2012～2019 保留樣本同規則只多 {h5.get('spread')}%（5 日）／{h10.get('spread')}%（10 日），"
            f"扣成本後 {h5.get('net')}%／{h10.get('net')}%（為負，賺不到成本）。",
            (f"2026 年以來 10 日 Rank IC 只有 {y26['ic']}（接近 0），效果幾乎消失。" if y26 else "2026 年資料不足，無法判斷是否轉弱。"),
            (f"空頭無效：樣本外大盤 60 日報酬 < 0 的排名日，10 日比母體多 {bear['spread']}%（{bear['n_dates']} 個排名日）。" if bear
             else "空頭樣本不足，無法判斷。"),
        ]
        samples = {"hold": h5.get("n_dates"), "train": s5["train"].get("n_dates"), "test": te5.get("n_dates")}
    fwd = forward_status(fwd_log, dates, es, E["group"])

    meta = {
        "latest": dates[-1], "first": dates[0], "hold_end": HOLD_END, "train_start": TRAIN_START, "train_end": TRAIN_END,
        "test_start": TEST_START, "horizons": list(HORIZONS), "rebalance": "每個交易日排名（第二版）", "nw_lag_rule": "max(持有天數, 因子記憶長度)", "factor_memory": FACTOR_MEMORY, "comp_memory": COMP_MEMORY, "top_q": TOP_Q,
        "cost_pct": COST_PCT, "liq_min": LIQ_MIN, "version": 2,
        "entry": "訊號當天收盤後產生，隔日開盤進場；持有 h 日後以第 h 日收盤出場；超額＝減「全市場前一日成交值加權平均」（不是 TAIEX；比隨機多的數字與基準無關）",
        "verdict_rule": "樣本外 Holm 校正後 Rank IC p<0.05、入選組比母體多>0 且扣成本 0.47% 後仍>0、訓練期 IC 同方向、樣本日數≥20 → 只給「實驗訊號」，本研究不輸出「有效」",
        "status": "experimental", "caveats": caveats, "samples": samples,
        "disclaimer": "統計研究輔助，不是買賣建議；歷史表現不代表未來。只提供族群層名單，不提供個股名單。",
        "limits": ["族群成分用現在的 groups.yaml 套到歷史（成分回填偏誤，越早越嚴重，2012～2019 結果偏樂觀）",
                   "下市股未來報酬缺值被剔除（存活者偏差）",
                   "樣本外 2024 起以 AI 多頭為主，缺完整空頭樣本外；2026 年訊號轉弱",
                   "隔日開盤鎖漲停買不到仍當成買得到；成本只扣 0.47%，未含滑價",
                   "報酬用官方參考價口徑，除權息日以參考價為基準，等於已把現金股利算進報酬（實測 2412 兩年連乘報酬比價格高約 10 個百分點）",
                   "每天排名、持有期重疊且因子變動慢：Newey-West 滯後與區塊長度＝max(持有天數, 因子記憶長度)，有效獨立樣本＝日數÷該滯後（慢因子如月營收 t 值經此校正會明顯下降）",
                   "個股層法人買超不成立（訓練期反向），不可拿來選個股"],
        "untestable": NOT_TESTABLE, "n_tests": n_ours, "n_tests_series": n_ours + PRIOR_TESTS,
        "n_tests_note": f"本研究 {n_ours} 個假設（單因子＋綜合分數＋日內＋費半）放同一個 Holm 族；另加先前研究 20261030_daily_signals 的 {PRIOR_TESTS} 個，系列共 {n_ours + PRIOR_TESTS} 個。",
    }
    for c in comps:
        c.pop("_st", None)
    return {"meta": meta,
            "factors": [{"id": f["id"], "name": f["name"], "mech": f["mech"], "sign": f["sign"], "data": f["data"], "v2": bool(f.get("v2"))} for f in FACTORS],
            "methods": methods, "composites": comps, "intraday": intraday_out, "us_link": us,
            "cases": cases, "case_stats": case_stats, "robust": robust, "forward": fwd,
            "latest": {"date": dates[-1], "candidates": latest}}


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
    y0 = int(START[:4])
    yrs = list(range(y0, 2100))
    price = store.read("price_daily", years=yrs)
    inst = store.read("inst_daily", years=yrs)
    company = store.read("company_info")
    margin = store.read("margin_daily", years=yrs)
    revenue = store.read("revenue_monthly", years=list(range(y0 - 2, 2100)))   # YoY 與 SUR 需要起點前 1～2 年的歷史
    fq = store.read("financial_q", years=list(range(y0 - 3, 2100)))
    sbl = store.read("sbl_daily")
    intl = store.read("intl_daily")
    try:
        fwd = store.read("next_wave_forward")
    except Exception:  # noqa: BLE001 — 前瞻紀錄表還沒有資料
        fwd = None
    from ..build_payload import last_complete_date
    latest = last_complete_date(price)
    price = price[price["date"].astype(str) <= latest]
    inst = inst[inst["date"].astype(str) <= latest]
    sc = yaml.safe_load((Path(config.ROOT) / "pipeline" / "groups" / "supply_chain.yaml").read_text(encoding="utf-8"))
    return price, inst, company, margin, revenue, sbl, intl, sc, fq, fwd


def main() -> None:           # pragma: no cover
    import argparse
    from .. import config
    from ..util import store
    global START
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.SITE_DATA / "flowcheck" / "next_wave.json"))
    ap.add_argument("--no-intraday", action="store_true")
    ap.add_argument("--start", default=START, help="資料起點（預設 2012-01-01；2020-01-01 可重現第一版口徑，較快）")
    a = ap.parse_args()
    START = a.start
    price, inst, company, margin, revenue, sbl, intl, sc, fq, fwd = load_inputs()
    df60 = None if a.no_intraday else store.read("intraday_60m")
    out = build(price, inst, company, margin, revenue, sbl, df60, sc, intl, fq=fq, fwd_log=fwd, with_intraday=not a.no_intraday)
    write(out, Path(a.out))
    log.info("寫出 %s", a.out)


if __name__ == "__main__":     # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    main()
