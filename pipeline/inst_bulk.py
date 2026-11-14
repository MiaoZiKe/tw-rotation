"""個股三大法人的「整天全市場」補抓（見 finmind.institutional_day）。

逐檔補一天要 ~1,975 次請求，每小時只有 600 次額度，最新交易日常只到幾百檔（2026-10-19 只有 148～249 檔）。
這裡先用 1 次請求試著把整天拉回來；拿不到（會員等級不夠）就回空，呼叫端照舊逐檔。
寫入一律走 store.append（只增不改），日期用回應裡的 date。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from .groups import loader
from .sources import finmind, inst_official
from .util import http, store
from .util.freshness import HISTORY_DAYS, MIN_RATIO
from .util.roc import is_tradable_security

log = logging.getLogger(__name__)


def site_codes() -> list[str]:
    """網站用到的個股（族群成分）。逐檔補抓時要排在最前面，頁面才不會缺。"""
    try:
        m = loader.membership(include_overlay=True)
        return sorted(set(m["code"].astype(str))) if not m.empty else []
    except Exception as exc:  # noqa: BLE001
        log.warning("讀族群成分失敗：%s", exc)
        return []


def with_site_codes(codes: list[str]) -> list[str]:
    """成交值前 N 檔 ＋ 網站用到的全部個股（去重、保序）。"""
    seen, out = set(), []
    for c in list(codes) + site_codes():
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def thin_dates(price_counts: pd.Series, inst_counts: pd.Series, max_days: int = 5,
               ratio: float = MIN_RATIO) -> list[str]:
    """最近 max_days 個價量日裡，法人筆數不足近期中位數 ratio 倍的日期（新到舊）。"""
    out = []
    dates = [str(d) for d in sorted(price_counts.index)][-max_days:]
    for d in reversed(dates):
        if int(price_counts.get(d, 0)) < 500:      # 價量本身沒到齊（休市／只有補一半）不問
            continue
        prev = inst_counts[[x for x in inst_counts.index if str(x) < d]].tail(HISTORY_DAYS)
        med = float(prev.median()) if len(prev) else 0.0
        if int(inst_counts.get(d, 0)) < ratio * max(med, 1.0):
            out.append(d)
    return out


def _tag(df: pd.DataFrame, reasons: list[str]) -> pd.DataFrame:
    """回空時把「為什麼空」掛在 attrs 上。

    2026-11-12 13:18 那輪：官方只回櫃買 893 檔（證交所 T86 回 HTML、欄位對不上），FinMind 整天額度又用盡，
    source_health 只看得到「回空（0 筆）」，分不出是哪一關壞。原因寫進 attrs["error"]，step() 會原樣記進
    last_run 與 source_health。只有 rows==0 才掛：有資料時不該頂著錯誤字樣。
    判定（進 empty、亮不亮燈）完全不變，這裡只補「為什麼」。"""
    if reasons and df.empty:
        df.attrs["error"] = "；".join(reasons)[:300]
    return df


def fill_inst_bulk(max_days: int = 5) -> pd.DataFrame:
    """先用官方開放資料（證交所＋櫃買，各 1 次請求、不吃額度）拿最新一日全市場法人；
    官方沒給或不夠的日子，再對筆數偏少的最近交易日各用 1 次 FinMind 請求拉整天。額度沒了就停；沒權限回空。"""
    reasons: list[str] = []
    official = inst_official.fetch_all()
    if official.empty:
        reasons.append("官方（證交所＋櫃買）整天全市場回空")
    off_counts = official["date"].value_counts() if not official.empty else pd.Series(dtype="int64")
    try:
        yrs = [datetime.now(timezone.utc).year, datetime.now(timezone.utc).year - 1]
        px = store.read("price_daily", years=yrs)      # 只需要最近幾天，不必讀整張 950 萬列
        inst = store.read("inst_daily", years=yrs)
        if px.empty:
            reasons.append("價量湖為空，無法判斷法人缺口")
            return _tag(official, reasons)
        pc = px["date"].astype(str).value_counts()
        ic = inst["date"].astype(str).value_counts() if not inst.empty else pd.Series(dtype="int64")
        for d, n in off_counts.items():      # 官方這一輪拿到的算進去，避免再花 FinMind 額度補同一天
            ic[str(d)] = max(int(ic.get(str(d), 0)), int(n))
        todo = thin_dates(pc, ic, max_days)
    except Exception as exc:  # noqa: BLE001
        log.warning("整天法人補抓：判斷缺口失敗 %s", exc)
        reasons.append(f"判斷缺口失敗：{exc}")
        return _tag(official, reasons)
    frames = [official] if not official.empty else []
    for d in todo:
        if http.finmind_budget_left() <= 1:
            log.warning("整天法人補抓：額度用盡，%s 之後的留給逐檔／下一輪", d)
            reasons.append(f"FinMind 額度用盡（{d} 起未補）")
            break
        df = finmind.institutional_day(d, wait=False)
        if df.empty:
            # 拿不到整天 → 後面的日期同一個原因，不再白燒額度
            reasons.append(f"FinMind 整天回空（{d}）")
            break
        df = df[df["date"].astype(str) == d]          # 只收回應裡就是那一天的
        df = df[df["code"].map(is_tradable_security)]
        log.info("整天法人補抓 %s：%d 檔（原本 %d 檔）", d, len(df), int(ic.get(d, 0)))
        frames.append(df)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return _tag(out, reasons)
