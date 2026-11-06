"""恐慌指數（臺指選擇權隱含波動率・本站自算）的原料抓取：FinMind TaiwanOptionDaily（data_id＝TXO）。

跟 sources/optpc.py 同一個資料集、同一支 http.finmind_get（同一套每小時額度管理）。
差別：optpc 只把成交量／未平倉加總；這裡逐天把月契約的價外買權、賣權結算價丟進 compute/ivx.py 算指數，
湖裡只存「每天一列」的結果（opt_ivx），不存幾千列的逐契約原始資料 —— 原始資料隔天就沒人要讀了。

兩條路：
  · daily_update()：每日管線用；從湖裡最後一天的隔天抓到今天（最多回看 10 天），1 次額度。
  · backfill()：回補用；按月游標（backfill_progress.json 的 complete.opt_ivx），每輪最多 48 個月（一輪補完），
    起點 config.IVX_BACKFILL_FLOOR。連兩個月都空就停（多半是額度或資料集暫時不給），下一輪再試，不把游標推過去。
⚠ 容器連不到 FinMind，欄位名照 FinMind 文件（date, option_id, contract_date, strike_price, call_put, open, max, min,
  close, volume, settlement_price, open_interest, trading_session）；認不得就回空並記 log，不寫壞資料進湖。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from .. import config
from ..compute import ivx
from .optpc import month_range

log = logging.getLogger(__name__)
MONTHS_PER_RUN = 48          # 一次請求一個月（約 7 萬列）；額度只算請求數（每小時 510 次），一輪約 47 次就把 2023-01 起全部補完


def _fetch(a: str, b: str):
    from ..util import http
    return http.finmind_get("TaiwanOptionDaily", data_id="TXO", start_date=a, end_date=b)


def daily_update(today: date | None = None, fetch=None, last: str | None = None) -> pd.DataFrame:
    """從湖裡最後一天的隔天抓到今天。回傳要 append 的列（可能是空的）。"""
    from ..util import store
    today = today or date.today()
    if last is None:
        cur = store.read("opt_ivx", years=[today.year - 1, today.year])
        last = str(cur["date"].max())[:10] if not cur.empty and "date" in cur.columns else None
    start = today - timedelta(days=10)
    if last:
        start = max(start, date.fromisoformat(last) + timedelta(days=1))
    if start > today:
        return pd.DataFrame()
    # 來源規矩：失敗回空、不拋例外（拋了會被 run_daily 記成錯誤、整輪變紅）；原因掛在 attrs["error"]
    try:
        rows = (fetch or _fetch)(start.isoformat(), today.isoformat())
        out = ivx.compute(rows)
    except Exception as exc:  # noqa: BLE001
        log.warning("opt_ivx 每日增量失敗：%s", exc)
        out = pd.DataFrame()
        out.attrs["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        return out
    if out.empty and rows is None:
        out.attrs["error"] = "FinMind 沒回應或額度用完"
    return out


def backfill(prog: dict, save_progress, today: date | None = None, months: int = MONTHS_PER_RUN, fetch=None) -> int:
    """每輪補 months 個月；游標在 prog['complete']['opt_ivx']['next']。回傳新增列數。"""
    from ..util import store
    if "opt_ivx" not in config.TABLES:
        return 0
    today = today or date.today()
    flag = prog.setdefault("complete", {}).setdefault("opt_ivx", {})
    if flag.get("done"):                       # 補到本月就交給 daily_update，不再每小時重抓本月
        return 0
    nxt = date.fromisoformat(flag.get("next") or config.IVX_BACKFILL_FLOOR)
    if nxt > today:
        return 0
    fetch = fetch or _fetch
    added = 0; empties = 0
    for k, (a, b) in enumerate(month_range(nxt, today)):
        if k >= months:
            break
        rows = fetch(a.isoformat(), (b - timedelta(days=1)).isoformat())
        if rows is None:                       # 額度用完：游標不動，下一輪再來
            log.info("opt_ivx %s：FinMind 額度用完，下一輪再補", a)
            break
        df = ivx.compute(rows)
        if df.empty:
            empties += 1
            log.info("opt_ivx %s 沒有算出任何一天（連續空 %d 個月，原始 %d 列）", a, empties, len(rows or []))
            if empties >= 2:
                break
            flag["next"] = b.isoformat() if a.year * 12 + a.month < today.year * 12 + today.month else a.isoformat()
        else:
            added += store.append("opt_ivx", df)
            empties = 0
            # 本月還沒過完：游標停在本月，下一輪再抓一次（之後每天由 daily_update 接手，重抓依 date 去重無害）
            flag["next"] = b.isoformat() if b <= today else a.isoformat()
        flag["at"] = str(today)
        # 完成＝本月真的算出資料了（本月是空的不算完成：可能 FinMind 還沒更新，下一輪再試）
        flag["done"] = (not df.empty) and a == date(today.year, today.month, 1)
        save_progress(prog)
        if flag["done"]:
            break
    return added
