"""盤中 5 分快照（tape_5m）缺口的替代來源回補：用 Yahoo 5 分 K ＋ 證交所日收重建。

為什麼有這支（2026-11-06，Andy：「找不到的要再安排維修人員去修復」）：
  tape_5m 的原始來源是 Worker KV（TTL 8 天），10-28、10-29 兩個交易日落地失敗、KV 已過期，原來源補不回來。
  2026-11-06 Actions 實測（probe/tape-gap）：
    · Yahoo 5 分 K：10-28、10-29 兩天各 53 根（09:00～13:20），單檔 2330／6488 都拿得到；保留約 60 天。
    · FinMind TaiwanStockKBar／TaiwanStockPriceTick：帳號等級 register（Free），回 400「Your level is register」→ 不能用。
    · 證交所／櫃買 openapi：只有日收盤與統計，沒有個股盤中分鐘資料（swagger 的 MI_5MINS 是指數統計、不是個股）。
    · 資料湖 intraday_60m 只有 60 分一層，聚不出 5 分。
  → 唯一可用的是 Yahoo 5 分 K（已是管線既有來源，yahoo.py）。

口徑與原本 tape 不同的地方（全部在資料狀態說明、src 欄標 rebuild:yahoo5m）：
  1. 價格：tape 的 09:05 格是「09:05 當下最後成交價」，Yahoo 的 09:00 那根收盤價 ≈ 09:05 的價 → 格＝棒起點 + 5 分，取該棒收盤。
     實測兩者逐格價格完全一致的比例約 4～6 成（取樣時刻差幾秒），其餘差一兩檔位，不影響走勢形狀。
  2. 09:00 那格：tape 是試撮／開盤前價、累計量 0；這裡用第一根的開盤價、量 0。
  3. 量：Yahoo 的 5 分量偏低且不穩（2330 10-28 全日只有證交所日量的 62%，11-04 卻 106%），不能直接用。
     做法：用 Yahoo 累計量的「形狀」（各格占全日的比例），乘上證交所 price_daily 的當日成交量。
     尾端：tape 實測 13:25 的累計量約占最終值 94.5%（10-30～11-04 中位數），最終值約是證交所日量的 98%
     （mis 不含盤後定價等），所以 13:25 這格＝日量 × 0.98 × 0.945，13:30、13:35＝日量 × 0.98，收盤價取證交所收盤。
  4. 成交值：同 tape 的估算方式，逐格新增張數 × 1000 × 該格價累加，val_src 標 est。
  5. 昨收取前一個交易日的證交所收盤。
  → 這些列是「形狀正確、數量級對得上」的重建值，不是逐筆原始值；研究若要嚴格比較，請用 src 欄排除。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd

from ..util import store
from . import yahoo
from .tape import COLUMNS, GAP_SINCE

log = logging.getLogger(__name__)

SRC = "rebuild:yahoo5m"
YAHOO_5M_DAYS = 55                 # Yahoo 5 分 K 保留約 60 天，留 5 天緩衝
VOL_FINAL = 0.98                   # tape 最終累計量 ÷ 證交所日量（10-30～11-04 中位數 0.977～0.983）
VOL_AT_1325 = 0.945                # tape 13:25 累計量 ÷ 最終累計量（中位數 0.941～0.958）
FIRST_SLOT, LAST_BAR = "09:00", "13:20"


def _add5(hm: str) -> str:
    h, m = int(hm[:2]), int(hm[3:5])
    t = h * 60 + m + 5
    return f"{t // 60:02d}:{t % 60:02d}"


def build_day(date: str, bars: pd.DataFrame, official: pd.DataFrame, prev_close: dict[str, float]) -> pd.DataFrame:
    """純函式：某天的 Yahoo 5 分 K ＋ 當日證交所日收 → tape_5m 形狀。

    bars：yahoo.intraday 的長格式（ts, code, open, close, volume；volume 單位＝股）。
    official：price_daily 該日的列（code, close, volume；volume 單位＝股），是量與收盤價的錨。
    沒有 Yahoo 資料的代號、沒有官方日量的代號都略過（寧缺勿造）。
    """
    if bars is None or bars.empty or official is None or official.empty:
        return pd.DataFrame(columns=COLUMNS)
    b = bars[bars["ts"].astype(str).str[:10] == date].copy()
    off = official.set_index("code")
    rows = []
    for code, g in b.groupby("code"):
        code = str(code)
        if code not in off.index:
            continue
        o = off.loc[code]
        vol_all = float(o["volume"]) if pd.notna(o["volume"]) else 0.0
        if vol_all <= 0:
            continue
        g = g.sort_values("ts")
        g = g[(g["ts"].astype(str).str[11:16] <= LAST_BAR)]
        if g.empty:
            continue
        y_tot = float(pd.to_numeric(g["volume"], errors="coerce").fillna(0).sum())
        if y_tot <= 0:
            continue
        pc = prev_close.get(code)
        close_final = float(o["close"]) if pd.notna(o["close"]) else float(g["close"].iloc[-1])
        lots_final = vol_all / 1000.0 * VOL_FINAL
        cum = pd.to_numeric(g["volume"], errors="coerce").fillna(0).cumsum() / y_tot
        slots = [(FIRST_SLOT, float(g["open"].iloc[0]), 0.0)]
        for (ts, px), frac in zip(zip(g["ts"].astype(str), g["close"]), cum):
            if pd.isna(px):
                continue
            slots.append((_add5(ts[11:16]), float(px), lots_final * VOL_AT_1325 * float(frac)))
        slots += [("13:30", close_final, lots_final), ("13:35", close_final, lots_final)]
        last_lots, cum_val = 0.0, 0.0
        for hm, price, lots in slots:
            lots = round(max(lots, last_lots), 3)         # 累計量只增不減
            cum_val += (lots - last_lots) * 1000 * price
            last_lots = lots
            rows.append({"ts": f"{date}T{hm}:00+08:00", "code": code, "price": price,
                         "cum_lots": lots, "cum_value": round(cum_val, 0),
                         "prev_close": pc, "src": SRC, "val_src": "est"})
    return pd.DataFrame(rows, columns=COLUMNS) if rows else pd.DataFrame(columns=COLUMNS)


def _official(date: str) -> tuple[pd.DataFrame, dict[str, float], dict[str, str]]:
    """(該日 price_daily 的 code/close/volume, 前一交易日收盤, 代號→市場別)。"""
    d = datetime.strptime(date, "%Y-%m-%d")
    px = store.read("price_daily", years=sorted({d.year, (d - timedelta(days=14)).year}))
    if px.empty:
        return pd.DataFrame(), {}, {}
    px = px.copy()
    px["_d"] = px["date"].astype(str).str[:10]
    today = px[px["_d"] == date]
    earlier = sorted(x for x in px["_d"].unique() if x < date)
    prev = px[px["_d"] == earlier[-1]] if earlier else px.iloc[0:0]
    prev_close = {str(c): float(v) for c, v in zip(prev["code"], prev["close"]) if pd.notna(v)}
    mk = {str(c): str(m) for c, m in zip(today["code"], today["market"])} if "market" in today else {}
    return today[["code", "close", "volume"]].assign(code=lambda x: x["code"].astype(str)), prev_close, mk


def rebuild_day(date8: str, codes: list[str]) -> pd.DataFrame:
    """某一天（YYYYMMDD）整日重建。Yahoo 掛了／該日休市／超過 Yahoo 保留期都回空 DataFrame 並記 log。"""
    date = f"{date8[:4]}-{date8[4:6]}-{date8[6:]}"
    try:
        if date8 < GAP_SINCE:
            return pd.DataFrame(columns=COLUMNS)
        if (datetime.now() - datetime.strptime(date8, "%Y%m%d")).days > YAHOO_5M_DAYS:
            log.warning("tape 重建 %s：超過 Yahoo 5 分 K 保留期（%d 天），無法重建", date, YAHOO_5M_DAYS)
            return pd.DataFrame(columns=COLUMNS)
        off, prev_close, mk = _official(date)
        if off.empty:
            log.warning("tape 重建 %s：price_daily 沒有那天（休市或日收還沒進湖），不重建", date)
            return pd.DataFrame(columns=COLUMNS)
        end = (datetime.strptime(date8, "%Y%m%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        bars = yahoo.intraday(codes, mk, "5m", "60d", start=date, end=end)
        if bars.empty:
            log.warning("tape 重建 %s：Yahoo 5 分 K 一筆都沒拿到", date)
            return pd.DataFrame(columns=COLUMNS)
        out = build_day(date, bars, off, prev_close)
        log.info("tape 重建 %s：%d 列／%d 檔／%d 格（Yahoo %d 列，名單 %d 檔）", date, len(out),
                 out["code"].nunique() if not out.empty else 0, out["ts"].nunique() if not out.empty else 0,
                 len(bars), len(codes))
        return out
    except Exception:  # noqa: BLE001 —— 替代來源也不能拖垮管線
        log.exception("tape 重建 %s 失敗", date)
        return pd.DataFrame(columns=COLUMNS)


def universe() -> list[str]:
    """重建用的代號名單＝湖裡最近一個 tape 日的代號（Worker 用的 tape_codes.json 那份，約 455 檔）。"""
    have = store.read("tape_5m")
    if have.empty:
        return []
    t = have["ts"].astype(str).str[:10]
    return sorted(set(have.loc[t == t.max(), "code"].astype(str)))


def main(argv: list[str] | None = None) -> int:
    """一次性手動回補：python -m pipeline.sources.tape_rebuild 20261028 20261029（走 store.append，只增不改）。"""
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    dates = [a for a in (argv if argv is not None else sys.argv[1:]) if a.isdigit() and len(a) == 8]
    codes = universe()
    total = 0
    for d8 in dates:
        have = store.read("tape_5m")
        if not have.empty and ((have["ts"].astype(str).str[:10] == f"{d8[:4]}-{d8[4:6]}-{d8[6:]}")
                               & (have["ts"].astype(str).str[11:16] >= "13:30")).any():
            log.info("tape 重建 %s：湖裡已收齊，略過（不覆寫原始資料）", d8)
            continue
        df = rebuild_day(d8, codes)
        total += store.append("tape_5m", df) if not df.empty else 0
    log.info("tape 重建完成：新增 %d 列", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
