"""流向驗證分頁（預覽版 preview/verify-panel）的資料：挑歷史任一天，回放那天的資金流向與盤中走勢，並回測盤中訊號。

★ 為什麼要有這一支（Andy 2026-10-30：要能挑**歷史任一天**，比對那天的強弱輪動／資金輪盤／資金分流樹
  與族群、成分股走勢是否吻合，並回測盤中訊號）。預覽版讀正式站資料，所以 JSON 由 main 的 build_payload 產出；
  這支**只新增** site/data/flowcheck/ 底下的檔案，不改任何既有輸出的欄位。
  檔案結構對齊設計規格 docs/design/20261030_flow_verify_page.md 第七節；欄位說明（前端以它為準）在
  docs/research/20261030_flowcheck_data.md。

輸出（site/data/flowcheck/）：
  index.json            可選日期、每天有哪些層、族群名單、大盤日報酬、吻合度常態、參數
  day/<日期>.json        近 FC_DAYS 個交易日：族群日線、成分股日線、背離、訊號、新聞、60 分 K 族群序列
  m60/<日期>.json        有 60 分 K 的那幾天：全部成分股 60 分序列（價、漲跌、新增成交值）
  m5/<日期>.json         有 tape_5m 的日子（10-30 起，之後每天累積）：族群＋全部成分股 5 分鐘序列
  series/<族群>.json     近 SERIES_DAYS 個交易日的族群日線（走勢大圖日線模式），只做人工族群
  backtest.json         盤中訊號回測（依粒度分開），含事件表

口徑（每一條都寫理由）：
  · 日漲跌＝flow.group_daily 的 chg_pct（前一日成交值加權，2026-10-30 新口徑），**直接沿用不重算**。
  · ★ 大盤＝**加權指數（TAIEX）**（2026-10-30 使用者測試後改；DECISIONS #378）：日線 index_ohlc TSE，
    盤中 index_intraday TSE 1 分 K（沒有就 60 分）。相對大盤＝族群 − 加權指數，急跌日＝加權指數 < −1.5%。
    原本用的 rrg.market_index（全市場前一日成交值加權）漲跌約是加權指數兩倍（10-28 +4.28% vs +2.04%），
    這一頁是給人跟加權指數比，所以換；主站強弱輪動的口徑另存 mkt_site／rs_*_site 供對照，主站本身不動。
  · 強弱輪動 rs_x/rs_y＝rrg.rrg_axes；資金輪盤 m_x/m_y＝money_wheel.money_axes（CEO 10-30 指定沿用，不另做一套）。
    兩支只用當天以前的資料（rolling／EMA adjust=False／shift），第 D 天的座標不含 D 之後的資訊。
  · dshare＝今日占比 − 前一交易日占比（pp）；rot＝占比 5 日均 − 20 日均（pp，同 flow.rotation_radar）。
  · 背離（規格第三節）：f＝dshare。A＝f 在人工族群前 30% 且 rel < −0.3pp；B＝rel > +0.3pp 且 f 在後 30%。
  · 盤中（5m／60m 同一套）：
      族群漲跌＝成分股相對昨收漲跌，以**前一日成交值**加權（與 group_daily 同口徑，規格 7.3 要求）；
      成分股掛多個人工族群時權重 ×1/族群數（同 group_daily）。大盤＝加權指數盤中（taiex_slots）。
      ⚠ 預覽版 app.js 即時卡目前是「等權」，回放與即時卡數字會不同 —— 研究文件已請前端對齊這裡。
      累計成交值占比＝族群成分股累計成交值 ÷ 名單內全部個股累計成交值（占比不拆分，同預覽版）。
      殘缺格：該格有報價檔數 < 當天最多那一格的 95% → **整格剔除**（缺一批股票時分母突然變小，畫出來是假跳動）。
      成分股有報價 < 3 檔的族群不算。
  · 5 分鐘（tape_5m）：成交值用 cum_value（逐格新增張數×成交價累加），**不用**「現價×累計張數」——
      後者把早盤成交量用現價重估，價一漲占比就跟著漲，等於把價格訊號灌進資金訊號。
  · 60 分（intraday_60m，Yahoo）：格子時間＝K 棒收盤時刻（09:00 那根→10:00，13:00 那根→13:30），
      最前面補 09:00＝第一根開盤價。09:00 那根的量 Yahoo 約六成是 0 → **整根量一律視為缺**，
      累計占比從 10:00 那根開始（第一個有值的格子是 11:00），檔案標 gap_0900。
  · 盤中訊號（照預覽版 tvSignals 的門檻；W＝「30 分鐘」對應格數：5m＝6、60m＝1）：
      flow_lead 資金先行：最近 W 格新增成交值占比 > 累計占比 × 1.5，且相對大盤 ≤ 0
      breadth   擴散　　：上漲家數比例 W 格內 +20pp 以上
      open_low_recover 開低回升：第一格相對大盤 < −1%、回升過半，且占比高於第一個有值的格子
      第 W 格起才判斷；每條每族群只記第一次；在最後一格觸發的不計回測（沒有之後可看）。
      rel_to_close＝收盤格相對大盤 − 觸發格相對大盤；rel_next_day＝下一交易日族群日線相對大盤（結果標籤，只評分用）。
      ⚠ 5m 與 60m 的格數、門檻意義不同，回測**分粒度各自計算，絕不混算**。
  · 族群歸屬用當前的 groups.yaml（存活者偏差），研究文件有寫。
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .. import config
from .money_wheel import money_axes
from .rrg import market_index, quadrant_of, rrg_axes

log = logging.getLogger(__name__)

SCHEMA = 1
FC_DAYS = 60            # day/ 檔：近幾個交易日
SERIES_DAYS = 750       # series/ 與 index.market：近幾個交易日（約 3 年）
BACKTEST_DAYS = 750     # 回測：近幾個交易日（60 分 K 起點 2023-09-19，實際以資料為準）
RESIDUAL_MIN = 0.95     # 殘缺格門檻：該格檔數 ÷ 當天最多那一格
MIN_MEMBERS = 3         # 族群至少幾檔有報價才算（同預覽版）
SIG_WIN_MIN = 30        # 訊號的「30 分鐘」
R1_MULT = 1.5
R2_PP = 20.0
R3_OPEN = -1.0
R3_RECOVER = 0.5
DIV_PCT = 0.30          # 背離：資金方向前／後 30%
DIV_REL = 0.30          # 背離：相對大盤門檻 pp
CRASH = -1.5            # 大盤急跌日門檻 %
COST = 0.47             # 回測扣成本（%，規格 7.5）
TOP_MEMBERS = 6
NEWS_PER_GROUP = 8
SIG_TYPE = {"r1": "flow_lead", "r2": "breadth", "r3": "open_low_recover"}
SIG_LABEL = {"flow_lead": "資金先行", "breadth": "擴散", "open_low_recover": "開低回升"}
GRAN_MIN = {"5m": 5, "60m": 60}


def _r(x, nd=2):
    """四捨五入；NaN／inf／None → None。"""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return round(f, nd) if math.isfinite(f) else None


def _ok(*v) -> bool:
    return all(x is not None and isinstance(x, (int, float, np.floating)) and math.isfinite(x) for x in v)


def sig_window(gran: str) -> int:
    """「30 分鐘」對應幾格。5m＝6 格；60m 一格就超過 30 分鐘，取 1 格。"""
    return max(1, SIG_WIN_MIN // GRAN_MIN[gran])


def _quad(x, y):
    return quadrant_of(x, y) if x is not None and y is not None else None


def wilson(k: int, n: int, z: float = 1.96):
    """命中率 95% 信賴區間（Wilson，%）。n=0 → (None, None)。不用常態近似：n 小、比例靠邊時會跑出 0 以下。"""
    if n <= 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round((c - h) * 100, 1), round((c + h) * 100, 1)


# ------------------------------------------------------------------ 日線
def market_daily(price: pd.DataFrame, n_days: int) -> pd.Series:
    """大盤日報酬（%），index＝日期字串。rrg.market_index 的逐日還原（Π(1+r) → r）。"""
    bench = market_index(price, days=n_days + 10)
    bench.index = bench.index.astype(str)
    r = bench.pct_change() * 100
    if len(bench):
        r.iloc[0] = (bench.iloc[0] - 1) * 100
    return r


def taiex_daily(taiex_ohlc: pd.DataFrame | None, taiex_intra: pd.DataFrame | None = None) -> pd.DataFrame:
    """加權指數日報酬（%）：index＝日期字串，欄位 chg／close／prev／src。

    主來源 index_ohlc symbol=TSE（證交所加權指數日收，2000 起）：chg＝change ÷ (close − change)。
    index_ohlc 當天還沒進湖時（盤後第一輪先抓價量），用 index_intraday 的 TSE 1 分 K 最後一根收盤（mis 來源）
    對前一天官方收盤算暫定值，src 標 "intraday"；兩者都沒有就不給（該天 rel 為 null，不拿別的基準頂替）。"""
    rows = {}
    if taiex_ohlc is not None and not taiex_ohlc.empty:
        t = taiex_ohlc.copy()
        t["date"] = t["date"].astype(str)
        t = t.sort_values("date").drop_duplicates("date", keep="last")
        prev = t["close"] - t["change"]
        for d, c, pv in zip(t["date"], t["close"], prev):
            if pv > 0:
                rows[d] = {"close": float(c), "prev": float(pv), "chg": (c / pv - 1) * 100, "src": "index_ohlc"}
    if taiex_intra is not None and not taiex_intra.empty and rows:
        m1 = taiex_intra[taiex_intra["interval"] == "1m"]
        last = sorted(rows)[-1]
        for d, sub in m1.groupby(m1["ts"].astype(str).str[:10]):
            if d > last:
                c = float(sub.sort_values("ts")["close"].iloc[-1])
                pv = rows[sorted(k for k in rows if k < d)[-1]]["close"]
                rows[d] = {"close": c, "prev": pv, "chg": (c / pv - 1) * 100, "src": "intraday"}
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


def daily_table(group_hist: pd.DataFrame, price: pd.DataFrame, n_days: int = SERIES_DAYS + 60,
                taiex: pd.DataFrame | None = None) -> pd.DataFrame:
    """每日 × 每族群：相對大盤、dshare、rot、強弱輪動、資金輪盤。只用當天以前的資料
    （rel_next／date_next 除外：那是評分用的結果標籤，欄名明寫 next）。

    ★ 2026-10-30（使用者測試）：「大盤」改成**加權指數**（taiex，見 taiex_daily）。原本用主站強弱輪動的
      rrg.market_index（全市場前一日成交值加權），它的漲跌約是加權指數的兩倍（10-28 +4.28% vs 加權 +2.04%），
      這一頁是給人跟加權指數比的，基準要是大家看得到的那一個。主站口徑另外留一組（mkt_site／rs_*_site），
      讓回放的強弱輪動可以和主站那張圖對得上。沒給 taiex 時（單元測試）退回主站口徑。"""
    if group_hist is None or group_hist.empty:
        return pd.DataFrame()
    g = group_hist.sort_values("date").copy()
    g["date"] = g["date"].astype(str)
    keep_dates = sorted(g["date"].unique())[-n_days:]
    msite = market_daily(price, len(keep_dates))
    mret = taiex["chg"] if taiex is not None and not taiex.empty else msite
    g = g[g["date"].isin(keep_dates)].copy()
    g["mkt_chg"] = g["date"].map(mret)
    g["mkt_site"] = g["date"].map(msite)
    g["rel"] = g["chg_pct"] - g["mkt_chg"]
    gs = g.groupby("group_id")["turnover_share"]
    g["dshare"] = g["turnover_share"] - gs.shift(1)
    g["rot"] = (gs.transform(lambda s: s.rolling(5, min_periods=2).mean())
                - gs.transform(lambda s: s.rolling(20, min_periods=5).mean()))
    g["factor"] = 1 + g["chg_pct"].fillna(0) / 100
    g["gi"] = g.groupby("group_id")["factor"].cumprod()
    # 指數只在 keep_dates 上累乘（缺的那天記 0 報酬＝持平，同 market_index 的處理）
    kd = pd.Index(keep_dates)
    for col, src in (("rs", mret), ("rs_site", msite)):
        bench = (1 + src.reindex(kd).fillna(0) / 100).cumprod()
        gg = g[["date", "group_id", "gi"]].copy()
        gg["bi"] = gg["date"].map(bench)
        r = rrg_axes(gg.dropna(subset=["bi"]), "group_id")[["date", "group_id", "rs_ratio", "rs_mom"]]
        sfx = "" if col == "rs" else "_site"
        g = g.merge(r.rename(columns={"rs_ratio": "rs_ratio" + sfx, "rs_mom": "rs_mom" + sfx}),
                    on=["date", "group_id"], how="left")
    m = money_axes(g[["date", "group_id", "turnover_share"]].copy())[["date", "group_id", "x", "y"]]
    g = g.merge(m.rename(columns={"x": "m_x", "y": "m_y"}), on=["date", "group_id"], how="left")
    g = g.sort_values(["group_id", "date"])
    g["rel_next"] = g.groupby("group_id")["rel"].shift(-1)
    g["date_next"] = g.groupby("group_id")["date"].shift(-1)
    return g.sort_values(["date", "turnover"], ascending=[True, False]).reset_index(drop=True)


def divergence(day: pd.DataFrame, manual: set) -> dict:
    """背離 A／B（規格第三節）。只在人工族群裡排 dshare 百分位；樣本 < 5 不判斷（回空）。"""
    d = day[day["group_id"].isin(manual) & day["dshare"].notna() & day["rel"].notna()]
    if len(d) < 5:
        return {}
    pct = d["dshare"].rank(pct=True)
    return {gid: ("A" if p > 1 - DIV_PCT and rel < -DIV_REL else "B" if rel > DIV_REL and p <= DIV_PCT else None)
            for gid, p, rel in zip(d["group_id"], pct, d["rel"])}


def agree_stats(day: pd.DataFrame, manual: set) -> dict:
    """當天吻合度：人工族群 dshare 與 rel 同號的比率（%）、橫斷面 Spearman IC。任一為 0 的不計。樣本 < 5 給 null。"""
    d = day[day["group_id"].isin(manual)][["dshare", "rel"]].dropna()
    d = d[(d["dshare"] != 0) & (d["rel"] != 0)]
    if len(d) < 5:
        return {"agree": None, "ic": None, "n": int(len(d))}
    same = (np.sign(d["dshare"]) == np.sign(d["rel"])).mean() * 100
    ic = d["dshare"].rank().corr(d["rel"].rank())
    return {"agree": _r(same, 1), "ic": _r(ic, 3), "n": int(len(d))}


def baseline(D: pd.DataFrame, manual: set, dates: list[str]) -> dict:
    """近 N 日吻合度常態：全部／上漲日／下跌日／急跌日（大盤 < −1.5%）分開，附天數。"""
    rows = []
    for _, day in D[D["date"].isin(dates)].groupby("date"):
        s = agree_stats(day, manual)
        if s["agree"] is not None:
            mk = day["mkt_chg"].dropna()
            rows.append((s["agree"], s["ic"], float(mk.iloc[0]) if len(mk) else np.nan))
    if not rows:
        return {}
    a = pd.DataFrame(rows, columns=["agree", "ic", "mkt"])

    def _s(x):
        return {"agree": _r(x["agree"].mean(), 1), "ic": _r(x["ic"].mean(), 3), "n_days": int(len(x))}
    return {"all": _s(a), "up": _s(a[a["mkt"] >= 0]), "down": _s(a[a["mkt"] < 0]),
            "crash": _s(a[a["mkt"] < CRASH]), "period": [min(dates), max(dates)]}


def tv_prev_table(price: pd.DataFrame) -> pd.DataFrame:
    """每檔每天：前一筆交易紀錄成交值（同 group_daily 的 tv_prev）、昨收、漲跌%。"""
    px = price[[c for c in ("date", "code", "open", "close", "change", "turnover") if c in price.columns]].copy()
    if "open" not in px.columns:
        px["open"] = np.nan                     # 沒有開盤價 → 60 分 K 不做還原權值校正（比例當 1）
    px["date"] = px["date"].astype(str)
    px["turnover"] = pd.to_numeric(px["turnover"], errors="coerce").fillna(0)
    px = px.sort_values(["code", "date"])
    px["tv_prev"] = px.groupby("code", sort=False)["turnover"].shift(1)
    px["prev_close"] = px["close"] - px["change"].fillna(0)
    px["chg"] = np.where(px["prev_close"] > 0, px["change"] / px["prev_close"] * 100, np.nan)
    return px


# ------------------------------------------------------------------ 盤中：兩種來源整理成同一格式
def frames_from_tape(tape_day: pd.DataFrame) -> dict | None:
    """tape_5m 一天 → {price, chg, cum}（列＝格子 HH:MM、欄＝代號）。"""
    if tape_day is None or tape_day.empty:
        return None
    t = tape_day.copy()
    t["tm"] = t["ts"].astype(str).str[11:16]
    t = t.drop_duplicates(["tm", "code"], keep="last")
    price = t.pivot(index="tm", columns="code", values="price").sort_index()
    prev = t.pivot(index="tm", columns="code", values="prev_close").reindex(price.index)
    cum = t.pivot(index="tm", columns="code", values="cum_value").reindex(price.index)
    chg = (price / prev.where(prev > 0) - 1) * 100
    return {"gran": "5m", "price": price, "chg": chg, "cum": cum, "gap_0900": False}


def frames_from_60m(bars_day: pd.DataFrame, prev_close: pd.Series,
                    day_close: pd.Series | None = None, day_open: pd.Series | None = None) -> dict | None:
    """intraday_60m 一天 → 同格式。格子時間＝K 棒收盤時刻；最前面補 09:00＝第一根開盤價。
    09:00 那根的量整根視為缺，累計成交值從 10:00 那根開始。昨收取 price_daily（close − change）。
    ★ Yahoo 的歷史分 K 是**還原權值**的價（之後的除權息會回頭把整天的價格縮小），昨收卻是 price_daily 的原始價，
      直接相除會讓整天的漲跌偏一個除息幅度（實測 2024-01 有 17% 的股票 09:00 開盤價和官方開盤差 > 0.5%，
      分位 1%～99% 是 0.60～1.69 倍）。修法：用 day_open（price_daily 當天官方開盤）÷ Yahoo 第一根開盤當比例，
      **把整天的 Yahoo 價格乘回原始價**。比例只用到 09:00 就知道的開盤價，不偷看收盤；比例落在 0.5～2 倍以外
      （對不上的壞資料）→ 那檔整天剔除。
    day_close（price_daily 當天收盤）有給時，13:30 那格的價改用它：Yahoo 13:00 那根的收盤是 13:25 前最後一筆，
      不含 13:30 收盤集合競價；13:30 這格本來就是收盤時刻，用官方收盤不算偷看。"""
    if bars_day is None or bars_day.empty:
        return None
    b = bars_day.copy()
    b["h"] = b["ts"].astype(str).str[11:16]
    b = b.drop_duplicates(["h", "code"], keep="last")
    hours = sorted(b["h"].unique())
    end_of = {h: ("13:30" if h >= "13:00" else f"{int(h[:2]) + 1:02d}:00") for h in hours}
    close = b.pivot(index="h", columns="code", values="close").reindex(hours)
    vol = b.pivot(index="h", columns="code", values="volume").reindex(hours)
    first = hours[0]
    opn = b[b["h"] == first].set_index("code")["open"].reindex(close.columns)
    nv = (vol * close).astype(float)
    gap = first == "09:00"
    if gap:
        nv.loc["09:00"] = np.nan
    idx = [end_of[h] for h in hours]
    close.index = idx
    price = pd.concat([pd.DataFrame([opn.values], index=[first], columns=close.columns), close])
    if day_open is not None:
        do = day_open.reindex(price.columns)
        f = (do / opn.where(opn > 0)).where(do > 0, 1.0).fillna(1.0)
        f = f.where((f >= 0.5) & (f <= 2.0))            # 對不上 → NaN → 整檔剔除
        price = price * f
        nv = nv * f                                      # 成交值也要用原始價
    cum = nv.cumsum(skipna=True).where(nv.notna().cumsum() > 0)
    cum.index = idx
    cum = pd.concat([pd.DataFrame([[np.nan] * len(close.columns)], index=[first], columns=close.columns), cum])
    if day_close is not None and price.index[-1] == "13:30":
        dc = day_close.reindex(price.columns)
        last = price.iloc[-1]
        price.iloc[-1] = dc.where((dc > 0) & last.notna(), last).values   # 被剔除的那檔維持 NaN
    pc = prev_close.reindex(price.columns)
    chg = (price / pc.where(pc > 0) - 1) * 100
    return {"gran": "60m", "price": price, "chg": chg, "cum": cum, "gap_0900": gap}


def taiex_slots(times: list[str], intra_day: pd.DataFrame | None, prev_close: float | None,
                day_close: float | None) -> pd.Series:
    """盤中每一格的加權指數相對昨收（%）。

    格子 HH:MM 取「標籤早於 HH:MM 的最後一根 K 棒」的收盤（K 棒標籤是開始時間：09:14 那根收在 09:15）；
    有 1 分 K 用 1 分（mis，2023-12 起），沒有就用 60 分（Yahoo，2023-09 起）；
    09:00（還沒有任何一根收盤）→ 第一根的開盤；13:30 以後 → 官方收盤（index_ohlc），有給才換。
    只用格子時間以前的 K 棒，不偷看。昨收缺 → 全部 NaN（不拿成分股加權頂替，免得口徑混在一起）。"""
    out = pd.Series(np.nan, index=times, dtype=float)
    if not prev_close or prev_close <= 0 or intra_day is None or intra_day.empty:
        return out
    iv = "1m" if (intra_day["interval"] == "1m").any() else "60m"
    b = intra_day[intra_day["interval"] == iv].copy()
    b["hm"] = b["ts"].astype(str).str[11:16]
    b = b.sort_values("hm").drop_duplicates("hm", keep="last")
    hms, closes = b["hm"].tolist(), b["close"].tolist()
    if not hms:
        return out
    for t in times:
        if t >= "13:30" and day_close:
            v = day_close
        else:
            k = int(np.searchsorted(hms, t, side="left"))     # 標籤 < t 的根數
            v = float(b["open"].iloc[0]) if k == 0 else closes[k - 1]
        out[t] = (v / prev_close - 1) * 100
    out.attrs["interval"] = iv
    return out


def _wavg(chg: pd.DataFrame, w: pd.Series) -> pd.Series:
    """逐格加權平均：權重缺／0 或漲跌缺的那檔不算；整格沒權重 → NaN。"""
    wv = w.reindex(chg.columns).fillna(0).clip(lower=0).values
    ww = pd.DataFrame(np.where(chg.notna(), wv, 0.0), index=chg.index, columns=chg.columns)
    s = ww.sum(axis=1)
    return (chg.fillna(0) * ww).sum(axis=1) / s.where(s > 0)


def group_intraday(fr: dict, members: dict[str, list[str]], universe: list[str],
                   w: pd.Series, nmem: pd.Series, mkt_override: pd.Series | None = None) -> dict:
    """族群盤中序列。w＝前一日成交值（代號→元）；nmem＝代號掛幾個人工族群（族群漲跌權重 ×1/n，同 group_daily）。

    用「格子 × 代號」矩陣乘「代號 × 族群」0/1 成員矩陣一次算完全部族群：回測要跑 750 天，
    逐族群 pandas 迴圈一天 0.6 秒、整段 7 分多鐘，矩陣乘法把它壓到一天幾毫秒（數字完全相同，只是換算法）。"""
    cols = [c for c in universe if c in fr["price"].columns]
    price, chg, cum = fr["price"][cols], fr["chg"][cols], fr["cum"][cols]
    cnt = price.notna().sum(axis=1)
    mx = cnt.max() if len(cnt) else 0
    keep = list(cnt[cnt >= RESIDUAL_MIN * mx].index) if mx > 0 else []
    price, chg, cum = price.loc[keep], chg.loc[keep], cum.loc[keep]
    # 大盤：有加權指數盤中序列就用它（mkt_override，2026-10-30 起的口徑）；沒有才用名單內個股前一日成交值加權
    mkt = mkt_override.reindex(keep) if mkt_override is not None else _wavg(chg, w)
    tot = cum.sum(axis=1, min_count=1)
    out = {"times": keep, "mkt": mkt.tolist(), "tot": tot.tolist(), "G": {}, "price": price,
           "chg": chg, "cum": cum, "gran": fr["gran"], "gap_0900": fr["gap_0900"]}
    if not keep:
        return out
    pos = {c: i for i, c in enumerate(cols)}
    gids = [g for g, cs in members.items() if any(c in pos for c in cs)]
    Mg = np.zeros((len(cols), len(gids)))
    for j, g in enumerate(gids):
        for c in members[g]:
            if c in pos:
                Mg[pos[c], j] = 1.0
    present = price.notna().any(axis=0).values.astype(float) @ Mg
    wg = (w.reindex(cols).fillna(0).clip(lower=0) / nmem.reindex(cols).fillna(1).clip(lower=1)).values
    C = chg.values
    nn = ~np.isnan(C)
    num = (np.where(nn, C, 0) * wg) @ Mg
    den = (nn * wg) @ Mg
    with np.errstate(invalid="ignore", divide="ignore"):
        gchg = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
    Vv = cum.values
    vn = ~np.isnan(Vv)
    val = np.where(vn, Vv, 0) @ Mg
    val = np.where((vn.astype(float) @ Mg) > 0, val, np.nan)
    totv = tot.values
    with np.errstate(invalid="ignore", divide="ignore"):
        share = np.where(totv[:, None] > 0, val / np.where(totv > 0, totv, 1)[:, None] * 100, np.nan)
    adv = (np.where(nn, C, 0) > 0).astype(float) @ Mg
    dec = (np.where(nn, C, 0) < 0).astype(float) @ Mg
    n = nn.astype(float) @ Mg
    with np.errstate(invalid="ignore", divide="ignore"):
        br = np.where(n > 0, adv / np.where(n > 0, n, 1) * 100, np.nan)
    mk = mkt.values
    for j, g in enumerate(gids):
        if present[j] < MIN_MEMBERS:
            continue
        out["G"][g] = {"codes": [c for c in members[g] if c in pos], "chg": gchg[:, j].tolist(),
                       "rel": (gchg[:, j] - mk).tolist(), "share": share[:, j].tolist(),
                       "adv": [int(v) for v in adv[:, j]], "dec": [int(v) for v in dec[:, j]],
                       "br": br[:, j].tolist(), "val": val[:, j].tolist()}
    return out


def scan_signals(M: dict) -> list[dict]:
    """三條規則掃全部族群。第 t 格的判斷只用 ≤ t 的資料（rel_to_close 是結果標籤，另算）。"""
    W = sig_window(M["gran"])
    times, tot = M["times"], M["tot"]
    last = len(times) - 1
    out = []
    if last < W:
        return out
    for gid, g in M["G"].items():
        rel, share, br, val = g["rel"], g["share"], g["br"], g["val"]
        if not _ok(rel[0]):
            continue
        s0 = next((s for s in share if _ok(s)), None)
        hit = {}
        for t in range(W, last + 1):
            if len(hit) == 3:
                break
            if not _ok(rel[t]) or not _ok(share[t]):
                continue
            if "r1" not in hit and _ok(val[t], val[t - W], tot[t], tot[t - W]):
                dt = tot[t] - tot[t - W]
                win = (val[t] - val[t - W]) / dt * 100 if dt > 0 else None
                avg = share[t]
                if win is not None and avg > 0 and win > R1_MULT * avg and rel[t] <= 0:
                    hit["r1"] = (t, {"win": _r(win, 3), "avg": _r(avg, 3), "x": _r(win / avg)})
            if "r2" not in hit and _ok(br[t], br[t - W]) and br[t] - br[t - W] >= R2_PP:
                hit["r2"] = (t, {"br0": _r(br[t - W], 1), "br1": _r(br[t], 1)})
            if ("r3" not in hit and rel[0] < R3_OPEN and s0 is not None
                    and (rel[t] - rel[0]) / -rel[0] > R3_RECOVER and share[t] > s0):
                hit["r3"] = (t, {"rel0": _r(rel[0]), "rec": _r((rel[t] - rel[0]) / -rel[0] * 100, 0),
                                 "s0": _r(s0, 3), "s": _r(share[t], 3)})
        for rule, (t, num) in hit.items():
            fresh = t == last
            perf = None if fresh or not _ok(rel[last]) else _r(rel[last] - rel[t])
            out.append({"gid": gid, "type": SIG_TYPE[rule], "t": times[t], "ti": t,
                        "rel_at_trigger": _r(rel[t]), "rel_to_close": perf, "fresh": fresh, "num": num})
    out.sort(key=lambda x: (x["ti"], x["gid"], x["type"]))
    return out


def stock_series(M: dict) -> dict:
    """成分股盤中：p 價、c 相對昨收 %、v 該格新增成交值（萬元；負值夾 0，累計值偶有回補誤差）。"""
    out = {}
    for c in sorted({c for g in M["G"].values() for c in g["codes"]}):
        if M["price"][c].notna().sum() < 1:
            continue
        cum = M["cum"][c]
        nv = cum.diff()
        if len(cum):
            nv.iloc[0] = cum.iloc[0]
        out[c] = {"p": [_r(v) for v in M["price"][c]], "c": [_r(v) for v in M["chg"][c]],
                  "v": [_r(v / 1e4, 0) for v in nv.clip(lower=0)]}
    return out


def group_series_json(M: dict) -> dict:
    return {gid: {"idx_rel": [_r(v) for v in g["rel"]], "chg": [_r(v) for v in g["chg"]],
                  "share": [_r(v, 3) for v in g["share"]], "adv": g["adv"], "dec": g["dec"],
                  "br": [_r(v, 1) for v in g["br"]]} for gid, g in M["G"].items()}


# ------------------------------------------------------------------ 新聞
def day_news(news_day, mat_day, members: dict[str, list[str]], names: dict[str, str],
             gnames: dict[str, str]) -> list[dict]:
    """當天新聞＋重大訊息，比對到族群：新聞代號欄含成分股、標題含成分股名稱（≥2 字）、標題含族群名稱。
    每族群最多 NEWS_PER_GROUP 則（依比中檔數、再依時間新到舊）；同一則只出一次，gids 列出它屬於哪些族群。
    ⚠ 名稱比對是字面的，名稱是常用詞時會誤配，研究文件有寫。"""
    items = []
    if news_day is not None and not news_day.empty:
        for r in news_day.itertuples():
            try:
                ts = pd.Timestamp(str(r.published_at)).tz_convert("Asia/Taipei")
            except Exception:  # noqa: BLE001
                ts = None
            items.append({"id": str(r.news_id), "t": ts.strftime("%H:%M") if ts is not None else None,
                          "_k": ts.value if ts is not None else 0, "title": str(r.title or ""),
                          "url": str(r.url or "") or None, "source": str(r.source or ""), "kind": "news",
                          "_codes": {c.strip() for c in str(r.codes or "").split(",") if c.strip()}})
    if mat_day is not None and not mat_day.empty:
        for r in mat_day.itertuples():
            tm = str(getattr(r, "time", "") or "")
            items.append({"id": str(r.news_id), "t": tm[:5] if len(tm) >= 5 else None, "_k": 0,
                          "title": f"{r.name}：{r.subject}", "url": None, "source": "公開資訊觀測站",
                          "kind": "material", "_codes": {str(r.code)}})
    out = {}
    for gid, cs in members.items():
        gname = gnames.get(gid, "")
        picks = []
        for i, it in enumerate(items):
            hit = [c for c in cs if c in it["_codes"] or (len(names.get(c, "")) >= 2 and names[c] in it["title"])]
            if hit or (len(gname) >= 2 and gname in it["title"]):
                picks.append((len(hit), it["_k"], i, hit))
        picks.sort(key=lambda x: (-x[0], -x[1]))
        for _, _, i, hit in picks[:NEWS_PER_GROUP]:
            o = out.setdefault(i, {**{k: v for k, v in items[i].items() if not k.startswith("_")},
                                   "codes": [], "gids": []})
            o["gids"].append(gid)
            o["codes"] = sorted(set(o["codes"]) | set(hit))
    return sorted(out.values(), key=lambda x: (x["t"] or ""), reverse=True)


# ------------------------------------------------------------------ 組裝
def _members(membership: pd.DataFrame) -> dict[str, list[str]]:
    return {str(gid): [str(c) for c in sub["code"]] for gid, sub in membership.groupby("group_id")
            if not str(gid).startswith("ind_")}


def _by(df, key_series):
    return {d: s for d, s in df.groupby(key_series)} if df is not None and not df.empty else {}


def market_meta(TX: pd.DataFrame, sd: list[str], mser: pd.Series) -> dict:
    """index.json 的 market：日報酬序列＋來源與起訖（規格要求標註來源）。"""
    if TX.empty:
        return {"dates": sd, "chg": [_r(v) for v in mser], "src": "weighted_universe",
                "note": "沒有加權指數資料，退回全市場前一日成交值加權（主站強弱輪動口徑）"}
    srcs = [str(TX.at[d, "src"]) if d in TX.index else None for d in sd]
    have = [d for d in sd if d in TX.index]
    return {"dates": sd, "chg": [_r(v) for v in mser], "src_by_day": srcs,
            "src": "TAIEX", "range": [have[0], have[-1]] if have else None,
            "proxy_0050": None,
            "note": ("加權指數（證交所發行量加權股價指數 TAIEX）日報酬：index_ohlc symbol=TSE（2000 起），"
                     "當天還沒進湖時用 index_intraday TSE 1 分 K 最後一根（src_by_day=intraday，暫定值）。"
                     "盤中用 index_intraday TSE 1 分 K（2023-12 起），之前用 60 分 K。750 日都有加權指數，未用 0050 代理。")}


def calendar_gaps(TX: pd.DataFrame, sd: list[str], all_dates: list[str], layers: dict) -> dict:
    """休市日與缺資料日分開列，前端才能分別顯示「休市」與「資料缺」。

    closed_days：區間內的週一～五，加權指數沒有那天（＝證交所沒開盤：國定假日、補假、颱風休市）。
    missing_days：加權指數有開盤、但價量資料湖（group_hist）沒有那天 → 真的缺資料，應回補。
    missing_intraday：有日線、但沒有 60 分／5 分盤中資料的交易日。
    沒有加權指數資料時無從判斷，三個都給空陣列。"""
    if TX.empty or not sd:
        return {"closed_days": [], "missing_days": [], "missing_intraday": []}
    cal = set(TX.index)
    have = set(all_dates)
    wk = pd.bdate_range(sd[0], sd[-1]).strftime("%Y-%m-%d")
    return {"closed_days": [d for d in wk if d not in cal and d not in have],
            "missing_days": [d for d in wk if d in cal and d not in have],
            "missing_intraday": [d for d in sd if not ({"m60", "m5"} & set(layers.get(d, [])))]}


def build(group_hist: pd.DataFrame, price: pd.DataFrame, membership: pd.DataFrame,
          tape: pd.DataFrame | None, bars60: pd.DataFrame | None, news: pd.DataFrame | None,
          names: dict[str, str], material: pd.DataFrame | None = None, inst: pd.DataFrame | None = None,
          taiex_ohlc: pd.DataFrame | None = None, taiex_intra: pd.DataFrame | None = None,
          days: int = FC_DAYS, series_days: int = SERIES_DAYS, backtest_days: int = BACKTEST_DAYS) -> dict:
    """回傳 {"index","day","m60","m5","series","backtest"}；寫檔另由 write()（測試不必碰硬碟）。

    taiex_ohlc：index_ohlc 的 TSE 列（date/open/close/change）；taiex_intra：index_intraday 的 TSE 列
    （ts/interval/open/close）。兩者都沒給 → 大盤退回主站口徑（只在單元測試發生），index.market.src 會寫明。"""
    TX = taiex_daily(taiex_ohlc, taiex_intra)
    D = daily_table(group_hist, price, max(series_days, backtest_days) + 60, taiex=TX if not TX.empty else None)
    if D.empty:
        return {"index": {"schema": SCHEMA, "dates": [], "layers": {}}, "day": {}, "m60": {}, "m5": {},
                "series": {}, "backtest": backtest([], None)}
    all_dates = sorted(D["date"].unique())
    dates = all_dates[-days:]
    bt_dates = all_dates[-backtest_days:]
    sd = all_dates[-series_days:]
    members = _members(membership)
    manual = set(members)
    meta = membership.drop_duplicates("group_id").set_index("group_id")
    gnames = meta["group_name"].astype(str).to_dict()
    nmem = membership[membership["group_id"].astype(str).isin(manual)].groupby("code")["group_id"].nunique()
    first = min(sd[0], bt_dates[0])
    PX = tv_prev_table(price[price["date"].astype(str) >= first])
    need = set(bt_dates) | set(dates)
    PXd = {d: s.set_index("code") for d, s in PX[PX["date"].isin(need)].groupby("date")}
    if tape is not None and not tape.empty:
        tdate = tape["ts"].astype(str).str[:10]
        universe = sorted(set(tape[tdate == tdate.max()]["code"].astype(str)))
        tape_by = _by(tape, tdate)
    else:
        universe = sorted({c for cs in members.values() for c in cs})
        tape_by = {}
    bars_by = _by(bars60, bars60["ts"].astype(str).str[:10]) if bars60 is not None and not bars60.empty else {}
    news_by = _by(news, news["date"].astype(str)) if news is not None and not news.empty else {}
    mat_by = _by(material, material["date"].astype(str)) if material is not None and not material.empty else {}
    inst_d = {}
    if inst is not None and not inst.empty:
        ii = inst[inst["date"].astype(str).isin(set(dates))]
        inst_d = {d: s.set_index("code") for d, s in ii.groupby(ii["date"].astype(str))}
    nxt = D.set_index(["date", "group_id"])[["rel_next", "date_next"]]

    def _next(d, gid):
        try:
            rn, dn = nxt.loc[(d, gid)]
        except KeyError:
            return None, None
        return (None, None) if dn is None or pd.isna(dn) else (_r(rn), str(dn))

    tx_by = (_by(taiex_intra, taiex_intra["ts"].astype(str).str[:10])
             if taiex_intra is not None and not taiex_intra.empty else {})

    def _intraday(d):
        p = PXd.get(d)
        if p is None:
            return None
        if d in tape_by:
            fr = frames_from_tape(tape_by[d])
        elif d in bars_by:
            fr = frames_from_60m(bars_by[d], p["prev_close"], p["close"], p["open"])
        else:
            return None
        if fr is None:
            return None
        mo, src = None, "weighted_universe"
        if not TX.empty:
            tx = TX.loc[d] if d in TX.index else None
            mo = taiex_slots(list(fr["price"].index), tx_by.get(d),
                             None if tx is None else tx["prev"], None if tx is None else tx["close"])
            src = ("taiex_" + mo.attrs.get("interval", "none")) if mo.notna().any() else "none"
        M = group_intraday(fr, members, universe, p["tv_prev"], nmem, mkt_override=mo)
        M["mkt_src"] = src
        return M if len(M["times"]) >= 2 and M["G"] else None

    # ---- 回測先跑：day 檔的訊號直接取自同一份事件表，回測與頁面口徑只有一份
    events, Ms = [], {}
    for d in sorted(set(bt_dates) | set(tape_by)):
        M = _intraday(d)
        if M is None:
            continue
        if d in dates or d in tape_by:
            Ms[d] = M
        for s in scan_signals(M):
            s["rel_next_day"], s["next_date"] = _next(d, s["gid"])
            s["granularity"] = M["gran"]
            events.append({**s, "date": d})
    ev_by = {}
    for e in events:
        ev_by.setdefault(e["date"], []).append({k: v for k, v in e.items() if k != "date"})

    out = {"day": {}, "m60": {}, "m5": {}, "series": {}}
    for d in dates:
        day = D[D["date"] == d]
        div = divergence(day, manual)
        p = PXd.get(d)
        mkt = day["mkt_chg"].dropna()
        mk = float(mkt.iloc[0]) if len(mkt) else None
        groups = {}
        for r in day.itertuples():
            gid = str(r.group_id)
            rx, ry, mx, my = _r(r.rs_ratio), _r(r.rs_mom), _r(r.m_x), _r(r.m_y)
            groups[gid] = {"share": _r(r.turnover_share, 3), "dshare": _r(r.dshare, 3), "rot": _r(r.rot, 3),
                           "chg": _r(r.chg_pct), "rel": _r(r.rel), "adv": _r(r.advancers, 0),
                           "dec": _r(r.decliners, 0), "tv": _r(r.turnover / 1e8, 2),
                           "rs_x": rx, "rs_y": ry, "quadrant": _quad(rx, ry),
                           # 主站強弱輪動口徑（大盤＝全市場前一日成交值加權），回放要和主站那張圖對照時用
                           "rs_x_site": _r(r.rs_ratio_site), "rs_y_site": _r(r.rs_mom_site),
                           "quadrant_site": _quad(_r(r.rs_ratio_site), _r(r.rs_mom_site)),
                           "m_x": mx, "m_y": my, "m_quadrant": _quad(mx, my),
                           "inst": [_r(r.foreign_net / 1000, 0), _r(r.trust_net / 1000, 0), _r(r.dealer_net / 1000, 0)],
                           "div": div.get(gid)}
        mem_out = {}
        if p is not None:
            ins = inst_d.get(d)
            for gid, cs in members.items():
                cs = [c for c in cs if c in p.index]
                if not cs:
                    continue
                sub = p.loc[cs]
                tvs = sub["turnover"].sum()
                wv = (sub["tv_prev"].fillna(0).clip(lower=0) / nmem.reindex(cs).fillna(1).values).where(sub["chg"].notna(), 0)
                ws = wv.sum()
                for c in cs:
                    ch = p.at[c, "chg"]
                    row = mem_out.get(c)
                    if row is None:
                        iv = None
                        if ins is not None and c in ins.index:
                            x = ins.loc[c]
                            iv = [_r(x["foreign_total"] / 1000, 0), _r(x["trust"] / 1000, 0), _r(x["dealer"] / 1000, 0)]
                        row = mem_out[c] = {"name": names.get(c, c), "gid": [], "close": _r(p.at[c, "close"]),
                                            "chg": _r(ch), "rel": _r(ch - mk) if mk is not None else None,
                                            "tv": _r(p.at[c, "turnover"] / 1e8, 3),
                                            "share_in_group": {}, "contrib": {}, "inst": iv}
                    row["gid"].append(gid)
                    row["share_in_group"][gid] = _r(p.at[c, "turnover"] / tvs * 100, 2) if tvs > 0 else None
                    row["contrib"][gid] = _r(wv[c] * ch / ws, 3) if ws > 0 and _ok(ch) else None
        ms = day["mkt_site"].dropna()
        payload = {"schema": SCHEMA, "date": d, "mkt_chg": _r(mk),
                   "mkt_src": (str(TX.at[d, "src"]) if d in TX.index else "none") if not TX.empty else "weighted_universe",
                   "mkt_site": _r(ms.iloc[0]) if len(ms) else None, "crash": bool(mk is not None and mk < CRASH),
                   "agree": agree_stats(day, manual), "div_params": {"pct": DIV_PCT, "rel": DIV_REL, "version": 1},
                   "granularity": None, "groups": groups, "members": mem_out,
                   "signals": ev_by.get(d, []), "news": day_news(news_by.get(d), mat_by.get(d), members, names, gnames),
                   "m60": None}
        M = Ms.get(d)
        if M is not None:
            payload["granularity"] = M["gran"]
            if M["gran"] == "60m":
                tvd = p["turnover"] if p is not None else pd.Series(dtype=float)
                tops = {gid: sorted(g["codes"], key=lambda c: -float(tvd.get(c, 0) or 0))[:TOP_MEMBERS]
                        for gid, g in M["G"].items()}
                st = stock_series(M)
                payload["m60"] = {"times": M["times"], "gap_0900": M["gap_0900"], "mkt": [_r(v) for v in M["mkt"]],
                                  "mkt_src": M["mkt_src"],
                                  "groups": group_series_json(M), "top": tops,
                                  "top_close": {c: st[c]["p"] for cs in tops.values() for c in cs if c in st}}
                out["m60"][d] = {"schema": SCHEMA, "date": d, "times": M["times"], "gap_0900": M["gap_0900"],
                                 "stocks": st}
        out["day"][d] = payload
    # m5：全部 tape 日（不只近 60 日；資料湖每天累積，這裡每次重產）
    for d in sorted(tape_by):
        M = Ms.get(d)
        if M is None or M["gran"] != "5m":
            continue
        out["m5"][d] = {"schema": SCHEMA, "date": d, "granularity": "5m", "times": M["times"],
                        "mkt": [_r(v) for v in M["mkt"]], "mkt_src": M["mkt_src"], "groups": group_series_json(M),
                        "share_base": None,
                        "share_base_note": "同時段過去 20 日基準需要 20 個 tape_5m 交易日，目前不足，給 null",
                        "signals": ev_by.get(d, []), "stocks": stock_series(M)}
    # series：人工族群近 series_days 日
    sdset = set(sd)
    close_w = PX[PX["date"].isin(sdset)].pivot(index="date", columns="code", values="close").reindex(sd)
    tv60 = PX[PX["date"].isin(set(all_dates[-60:]))].groupby("code")["turnover"].sum()
    mser = D.drop_duplicates("date").set_index("date")["mkt_chg"].reindex(sd)
    bi = (1 + mser.fillna(0) / 100).cumprod() * 100
    for gid, s in D[D["date"].isin(sdset) & D["group_id"].isin(manual)].groupby("group_id"):
        s = s.set_index("date").reindex(sd)
        gi = (1 + s["chg_pct"].fillna(0) / 100).cumprod() * 100
        top = list(tv60.reindex(members[gid]).dropna().sort_values(ascending=False).index[:TOP_MEMBERS])
        out["series"][gid] = {"schema": SCHEMA, "gid": gid, "name": gnames.get(gid, gid), "dates": sd,
                              "idx": [_r(v) for v in gi], "idx_rel": [_r(v) for v in gi / bi * 100],
                              "share": [_r(v, 3) for v in s["turnover_share"]],
                              "dshare": [_r(v, 3) for v in s["dshare"]],
                              "chg": [_r(v) for v in s["chg_pct"]], "rel": [_r(v) for v in s["rel"]],
                              "top": [{"code": c, "name": names.get(c, c),
                                       "close": [_r(v) for v in close_w[c]] if c in close_w else []} for c in top]}
    layers = {d: ["daily"] for d in sd}
    for d in sd:
        if d in tape_by:
            layers[d].append("m5")
        elif d in bars_by:
            layers[d].append("m60")
        if d in out["day"]:
            layers[d].append("day")
    groups_meta = [{"gid": g, "name": gnames.get(g, g), "chain": str(meta.at[g, "chain"]),
                    "tier": str(meta.at[g, "tier"]), "members": members[g], "is_bucket": False} for g in sorted(manual)]
    for r in D.drop_duplicates("group_id").itertuples():
        if str(r.group_id).startswith("ind_"):
            groups_meta.append({"gid": str(r.group_id), "name": str(r.group_name), "chain": str(r.chain),
                                "tier": str(r.tier), "members": [], "is_bucket": True})
    out["index"] = {
        "schema": SCHEMA, "latest": all_dates[-1],
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dates": dates, "layers": layers, "groups": groups_meta, "baseline": baseline(D, manual, sd),
        "market": market_meta(TX, sd, mser),
        **calendar_gaps(TX, sd, all_dates, layers),
        "params": {"fc_days": days, "series_days": series_days, "backtest_days": backtest_days,
                   "residual_min": RESIDUAL_MIN, "min_members": MIN_MEMBERS, "r1_mult": R1_MULT, "r2_pp": R2_PP,
                   "r3_open": R3_OPEN, "r3_recover": R3_RECOVER, "sig_window_min": SIG_WIN_MIN,
                   "div_pct": DIV_PCT, "div_rel": DIV_REL, "crash": CRASH, "cost": COST},
    }
    out["backtest"] = backtest(events, all_dates[-1])
    return out


def backtest(events: list[dict], as_of) -> dict:
    """訊號回測：**依粒度 × 訊號分開**（5m 與 60m 不混算）。命中＝觸發後到收盤相對大盤 > 0；最後一格觸發的不計。
    n < 30 標 low_n（前端整列灰字不下結論）；CI 含 50% 標 ci_has_50（無法區分於隨機）。
    passed_multiple_test 固定 False：研究 16 組未通過多重比較（docs/research/20261030_flow_vs_price.md），
    這裡不做任何能讓它變 True 的調參。ic／t_nw 目前給 null（理由見研究文件）。"""
    rows = []
    for gran, typ in sorted({(e["granularity"], e["type"]) for e in events}):
        ss = [e for e in events if e["granularity"] == gran and e["type"] == typ]
        cl = [e["rel_to_close"] for e in ss if e["rel_to_close"] is not None]
        nd = [e["rel_next_day"] for e in ss if e["rel_next_day"] is not None]
        k, kn = sum(v > 0 for v in cl), sum(v > 0 for v in nd)
        lo, hi = wilson(k, len(cl))
        rows.append({"granularity": gran, "type": typ, "label": SIG_LABEL[typ], "n_trig": len(ss),
                     "n": len(cl), "hit_rate": _r(k / len(cl) * 100, 1) if cl else None, "ci95": [lo, hi],
                     "avg_excess": _r(np.mean(cl), 3) if cl else None,
                     "avg_excess_net": _r(np.mean(cl) - COST, 3) if cl else None,
                     "n_next": len(nd), "hit_rate_next": _r(kn / len(nd) * 100, 1) if nd else None,
                     "ci95_next": list(wilson(kn, len(nd))), "avg_next": _r(np.mean(nd), 3) if nd else None,
                     "avg_next_net": _r(np.mean(nd) - COST, 3) if nd else None,
                     "low_n": len(cl) < 30, "ci_has_50": bool(lo is not None and lo <= 50 <= hi),
                     "ic": None, "t_nw": None,
                     "period": [min(e["date"] for e in ss), max(e["date"] for e in ss)],
                     "days": len({e["date"] for e in ss})})
    ev = [[e["date"], e["gid"], e["type"], e["granularity"], e["t"], e["rel_to_close"], e["rel_next_day"]]
          for e in events]
    return {"schema": SCHEMA, "as_of": as_of, "passed_multiple_test": False, "cost": COST, "summary": rows,
            "events_cols": ["date", "gid", "type", "granularity", "t", "rel_to_close", "rel_next_day"],
            "events": ev}


def write(result: dict, outdir: Path) -> dict:
    """寫檔。已滑出視窗的舊檔刪掉（site/data 是 gitignore 的產出，不是資料湖）。回傳檔數與各資料夾最大一檔（KB）。"""
    stats = {"files": 0, "bytes": 0, "max": {}}
    outdir.mkdir(parents=True, exist_ok=True)

    def _w(path: Path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
        n = path.stat().st_size
        stats["files"] += 1
        stats["bytes"] += n
        k = path.parent.name
        stats["max"][k] = max(stats["max"].get(k, 0), n)

    for sub in ("day", "m60", "m5", "series"):
        keep = {f"{k}.json" for k in result.get(sub, {})}
        d = outdir / sub
        if d.exists():
            for f in d.glob("*.json"):
                if f.name not in keep:
                    f.unlink()
        for k, obj in result.get(sub, {}).items():
            _w(d / f"{k}.json", obj)
    _w(outdir / "index.json", result["index"])
    _w(outdir / "backtest.json", result["backtest"])
    stats["max"] = {k: round(v / 1024, 1) for k, v in stats["max"].items()}
    stats["total_kb"] = round(stats.pop("bytes") / 1024, 1)
    return stats


def run(store, loader, group_hist: pd.DataFrame, price: pd.DataFrame, names: dict[str, str],
        outdir: Path) -> dict:
    """build_payload 的入口：只讀需要的月分割（intraday_60m 只取成分股與 tape 名單），算完寫檔。"""
    dates = sorted(group_hist["date"].astype(str).unique())[-max(BACKTEST_DAYS, FC_DAYS):]
    if not dates:
        return {}
    yms = {d[:7].replace("-", "") for d in dates}
    ys = sorted({int(d[:4]) for d in dates})
    mem = loader.membership()
    want = set(mem["code"].astype(str))

    def _read_monthly(table, codes=None):
        base = config.DATA / table
        frames = []
        for ym in sorted(yms):
            f = base / f"year={ym}" / "part.parquet"
            if f.exists():
                df = pd.read_parquet(f)
                frames.append(df[df["code"].astype(str).isin(codes)] if codes is not None and "code" in df.columns else df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    tape = _read_monthly("tape_5m")
    if not tape.empty:
        want |= set(tape["code"].astype(str))
    bars = _read_monthly("intraday_60m", want)
    inst = store.read("inst_daily", years=sorted({int(d[:4]) for d in dates[-FC_DAYS:]}))
    # 加權指數：日線 index_ohlc（年分割，只取 TSE）、盤中 index_intraday（月分割，只取 TSE 的 1m／60m）
    tx = store.read("index_ohlc", years=ys)
    tx = tx[tx["symbol"] == "TSE"] if not tx.empty and "symbol" in tx.columns else pd.DataFrame()
    txi = _read_monthly("index_intraday")
    if not txi.empty:
        txi = txi[(txi["symbol"] == "TSE") & (txi["interval"].isin(["1m", "60m"]))]
    res = build(group_hist, price, mem, tape, bars, store.read("news", years=ys), names,
                material=store.read("material_news", years=ys), inst=inst, taiex_ohlc=tx, taiex_intra=txi)
    return write(res, outdir)
