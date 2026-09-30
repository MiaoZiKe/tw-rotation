"""個股 60 分 K：名單、每日續補、歷史回補（2026-09-30 擴到全市場）。

為什麼有這支（Andy 2026-09-30：「有部分股票打開在小時間級別的周期裡面 1 小時 4 小時都會是找不到數據的狀況」）
------------------------------------------------------------------------------------------
以前的名單是「最新交易日成交值前 400 檔」（run_daily.INTRADAY_LIMIT），而且增量的起點是
「整張表的最後一根」。兩件事疊在一起的結果（2026-09-30 資料湖實測）：
  · 資料湖只有 567 檔、全市場普通股約 1,980 檔 → 約 1,400 檔的個股頁 1H／4H 永遠是空的；
  · 那 567 檔裡約 1/4 只有 2～15 根：某天擠進前 400 名，只拿到「全表最後一根之後」的那幾根，
    隔天掉出前 400 就停了 —— 歷史從來沒有補過。

新做法（DECISIONS #155：會重複用到的一律進湖、增量；#156：60 分 K 保留 730 天）：
  · 名單＝全市場上市＋上櫃普通股（跟回補的 run_backfill.market_codes() 同一份），
    再加上成交值前 400 名的可交易證券（ETF 擴大前就有分 K，不能因為擴大反而消失）。
  · 每日續補（run_daily）只跟 Yahoo 要最近幾天，逐檔只留「這一檔最後一根之後」的那一段。
  · 歷史（Yahoo 60 分最多約 730 天）交給回補（run_backfill，每小時一輪），每輪最多 BACKFILL_PER_RUN 檔，
    進度寫進 backfill_progress.json：逐檔 done 鍵 `intraday_60m:<代號>`，整體 `complete["intraday_60m"]`
    （含 remaining）。不在每日管線一次打爆 Yahoo。
  · Yahoo 回空的冷門股，連兩輪（而且同一輪 2330 拿得到，證明不是限流／斷線）才記成 `no_data`
    ＝「確認無資料」，個股頁會寫「此檔沒有盤中分 K 資料」而不是空白。

所有對外請求失敗都只記 log、回空，絕不讓整條管線掛掉。
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from . import config
from .util import store
from .util.roc import is_tradable_security

log = logging.getLogger(__name__)

TABLE = "intraday_60m"
DONE_PREFIX = "intraday_60m:"      # prog["done"] 的逐檔鍵：True＝補過完整歷史；"no_data"＝確認無資料
COMPLETE_KEY = "intraday_60m"      # prog["complete"] 的鍵（backfill.yml 守門與執行摘要看它）
TRIES_KEY = "intraday_60m_empty"   # prog 裡記「Yahoo 回空過幾輪」的表（還沒到 no_data 門檻的）
NO_DATA = "no_data"                # 跟 run_backfill.NO_DATA 同一個值（執行摘要靠它分開計數）

TOP_TRADABLE = 400      # 普通股全市場之外，另外保留成交值前 400 名的可交易證券（含 ETF）
BACKFILL_PER_RUN = 400  # 回補一輪最多補幾檔（10 批 × 40 檔）；新增約 1,400 檔 → 約 4 輪
BATCH = 40              # 一次跟 Yahoo 要幾檔（yfinance 一次下載多檔；沿用 yahoo.intraday 的預設）
NO_DATA_TRIES = 2       # 同一檔要連幾輪回空（而且那一輪 2330 拿得到）才記成確認無資料
DAILY_MIN_DAYS = 5      # 每日續補至少跟 Yahoo 要幾天（排程延遲、漏一兩輪也補得回來）
DAILY_MAX_DAYS = 30     # 每日續補最多要幾天 —— 更久的缺口是回補的事，不在每日管線一次打爆 Yahoo
COMPLETE_WINDOW_DAYS = 700   # 判斷「湖裡已經有完整歷史」看最近幾天（Yahoo 保留 730 天，留緩衝）
COMPLETE_RATIO = 0.9    # 最近 700 天的根數 ≥ 全湖最多那一檔的 90% 才算完整（新上市的會被 Yahoo 那輪補成 done）
CANARY = "2330"         # 整批回空時拿它探一下：它都拿不到就是限流或斷線，不是這批沒資料
TPE = timezone(timedelta(hours=8))


# ------------------------------------------------------------------ 名單

def _recent_parts(table: str, n: int) -> list[int]:
    """資料湖某張表最後 n 個分割的鍵（年或年月）。用目錄名，不用執行當下的日期去猜。"""
    d = config.DATA / table
    parts = sorted(p.parent.name.split("=", 1)[1] for p in d.glob("year=*/part.parquet"))
    return [int(x) for x in parts[-n:] if x.isdigit()]


def universe() -> tuple[list[str], dict[str, str]]:
    """要有 60 分 K 的代號（依成交值由大到小）與市場別（Yahoo 靠它決定 .TW／.TWO）。

    ① 成交值前 TOP_TRADABLE 名的可交易證券（普通股＋ETF）—— 擴大前的名單就是這一批，ETF 不能掉；
    ② 全市場上市＋上櫃普通股（run_backfill.market_codes()，跟法人／當沖／股利回補同一份）。
    市場別取 price_daily 最近一筆（上市轉上櫃這種換市場的，以最新的為準），沒有才看 company_info。
    """
    from .run_backfill import market_codes   # 延遲匯入：run_backfill 匯入時會設定 logging

    px = store.read("price_daily", years=_recent_parts("price_daily", 2))
    if px.empty:
        # 湖裡還沒有價量就不知道全市場有誰（market_codes 這時會退回問 FinMind，那是回補第一次跑的事，
        # 分 K 不必為了這個多打一個外部請求）
        return [], {}
    common = market_codes()
    markets: dict[str, str] = {}
    top: list[str] = []
    if not px.empty and {"date", "code"} <= set(px.columns):
        px = px.assign(code=px["code"].astype(str), date=px["date"].astype(str)).sort_values("date", kind="stable")
        if "market" in px.columns:
            mk = px.dropna(subset=["market"]).drop_duplicates("code", keep="last")
            markets = dict(zip(mk["code"], mk["market"].astype(str)))
        latest = px["date"].max()
        day = px[px["date"] == latest]
        if "turnover" in day.columns:
            day = day.assign(_tv=pd.to_numeric(day["turnover"], errors="coerce").fillna(0.0)) \
                     .sort_values("_tv", ascending=False, kind="stable")
        top = [c for c in dict.fromkeys(day["code"]) if is_tradable_security(c)][:TOP_TRADABLE]
    info = store.read("company_info")
    if not info.empty and {"code", "market"} <= set(info.columns):
        for c, m in zip(info["code"].astype(str), info["market"]):
            if c not in markets and isinstance(m, str) and m:
                markets[c] = m
    codes = list(dict.fromkeys(top + common))
    return codes, {c: markets.get(c, "") for c in codes}


def read_progress() -> dict:
    p = config.STATE / "backfill_progress.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except ValueError:
        return {}


def no_data_codes(prog: dict | None) -> set[str]:
    """回補確認過 Yahoo 沒有 60 分 K 的代號（done 值＝"no_data"）。"""
    done = (prog or {}).get("done") or {}
    return {k[len(DONE_PREFIX):] for k, v in done.items() if k.startswith(DONE_PREFIX) and v == NO_DATA}


def state_of(code: str, n_bars: int, prog: dict | None) -> str:
    """個股頁要怎麼講這一檔的 60 分 K：ok（有）／none（確認無資料）／pending（還在回補）。"""
    if n_bars >= 5:
        return "ok"
    v = ((prog or {}).get("done") or {}).get(DONE_PREFIX + str(code))
    return "none" if v == NO_DATA else "pending"


# ------------------------------------------------------------------ 每日續補

def daily_increment(now: datetime | None = None) -> tuple[pd.DataFrame, dict]:
    """每日管線用：全名單跟 Yahoo 要最近幾天，逐檔只留「這一檔湖裡最後一根之後」的部分。

    回傳 (要寫進湖的列, 給 last_run.json 的摘要)。
    · 只讀湖的最後兩個月分割就夠知道每一檔的最後一根（整張表兩年、幾百萬列，不必全讀）。
    · 跟 Yahoo 要的天數＝距離「湖裡最新一根」幾天，夾在 DAILY_MIN_DAYS～DAILY_MAX_DAYS。
      更久的缺口（新加入名單、Yahoo 那幾天掛掉）交給回補，不在這裡要兩年。
    · 回補確認無資料的冷門股不再問（每一輪省下它們的請求）。
    """
    from .sources import yahoo

    codes, markets = universe()
    if not codes:
        return pd.DataFrame(), {"codes": 0, "why": "還沒有價量資料，不知道要抓哪些代號"}
    nd = no_data_codes(read_progress())
    ask = [c for c in codes if c not in nd]

    recent = store.read(TABLE, years=_recent_parts(TABLE, 2))
    last_by: dict[str, str] = {}
    lake_last = None
    if not recent.empty and {"ts", "code"} <= set(recent.columns):
        ts = recent["ts"].astype(str)
        last_by = ts.groupby(recent["code"].astype(str)).max().to_dict()
        lake_last = ts.max()
    days = DAILY_MIN_DAYS
    if lake_last:
        try:
            start = pd.Timestamp(lake_last)
            start = start.tz_localize("Asia/Taipei") if start.tzinfo is None else start
            gap = (pd.Timestamp(now or datetime.now(TPE)) - start).days
            days = min(DAILY_MAX_DAYS, max(DAILY_MIN_DAYS, gap))
        except Exception:  # noqa: BLE001 —— 壞掉的時間字串當成沒有
            log.warning("60 分 K 每日續補：湖裡最後一根 %r 解不出來，照最少天數要", lake_last)
    period = yahoo.period_for(days, "60m")
    log.info("60 分 K 每日續補：%d 檔（略過確認無資料 %d 檔），跟 Yahoo 要 %s", len(ask), len(nd), period)
    df = yahoo.intraday(ask, markets, "60m", period, batch=BATCH)
    info = {"codes": len(ask), "skipped_no_data": len(nd), "period": period, "lake_last": lake_last,
            "got_codes": 0, "rows": 0}
    if df is None or df.empty:
        return pd.DataFrame(), info
    last = df["code"].astype(str).map(last_by).fillna("")
    out = df[df["ts"].astype(str) > last].reset_index(drop=True)
    info.update(got_codes=int(df["code"].nunique()), rows=int(len(out)))
    log.info("60 分 K 每日續補：Yahoo 回 %d 檔 %d 列，其中新的 %d 列", info["got_codes"], len(df), len(out))
    return out, info


# ------------------------------------------------------------------ 歷史回補

def _lake_summary(m60: pd.DataFrame) -> tuple[dict[str, tuple[str, str, int]], str | None, int]:
    """每檔 (第一根, 最後一根, 最近 COMPLETE_WINDOW_DAYS 天的根數)、全湖最新一根、最近窗口內最多的根數。"""
    if m60 is None or m60.empty or not {"ts", "code"} <= set(m60.columns):
        return {}, None, 0
    ts = m60["ts"].astype(str)
    code = m60["code"].astype(str)
    lake_last = ts.max()
    cut = (pd.Timestamp(lake_last) - pd.Timedelta(days=COMPLETE_WINDOW_DAYS)).isoformat()
    g = pd.DataFrame({"ts": ts, "code": code, "win": ts >= cut}).groupby("code")
    first, last, win = g["ts"].min(), g["ts"].max(), g["win"].sum()
    summ = {c: (first[c], last[c], int(win[c])) for c in first.index}
    return summ, lake_last, int(win.max()) if len(win) else 0


def _canary_ok() -> bool:
    from .sources import yahoo
    try:
        return not yahoo.intraday([CANARY], {CANARY: "TWSE"}, "60m", "5d", batch=1).empty
    except Exception:  # noqa: BLE001
        return False


def backfill(prog: dict, save=None, per_run: int = BACKFILL_PER_RUN, batch: int = BATCH) -> dict:
    """回補一輪：把名單裡還沒補過完整歷史的代號，每批 `batch` 檔跟 Yahoo 要 730 天，最多 `per_run` 檔。

    `save(prog)`：每批寫完湖就存一次進度（CI 中途被砍，已寫的不會重抓）。
    回傳並寫進 `prog["complete"]["intraday_60m"]`：done、remaining、這一輪補了幾檔、停在哪裡。

    判斷「已經補過」的順序：
      1. 逐檔 done 鍵（True 或 "no_data"）→ 跳過；
      2. 湖裡已經有完整歷史（第一根在 700 天前、最後一根跟全湖最新差不到 5 天、最近 700 天根數夠）
         → 直接記 done，不花請求（擴大前那約 300 檔完整的就是這樣處理）；
      3. 其餘依名單順序（成交值大的先）補。
    """
    from .sources import yahoo

    save = save or (lambda _p: None)
    codes, markets = universe()
    done = prog.setdefault("done", {})
    tries = prog.setdefault(TRIES_KEY, {})
    have = store.read(TABLE)
    summ, lake_last, best = _lake_summary(have)
    del have
    marked_lake = 0
    if lake_last:
        cut = (pd.Timestamp(lake_last) - pd.Timedelta(days=COMPLETE_WINDOW_DAYS)).isoformat()
        fresh = (pd.Timestamp(lake_last) - pd.Timedelta(days=5)).isoformat()
        for c in codes:
            s = summ.get(c)
            if done.get(DONE_PREFIX + c) or not s:
                continue
            if s[0] <= cut and s[1] >= fresh and s[2] >= COMPLETE_RATIO * best:
                done[DONE_PREFIX + c] = True
                marked_lake += 1
    todo = [c for c in codes if not done.get(DONE_PREFIX + c)]
    picks = todo[:max(0, int(per_run))]
    log.info("60 分 K 回補：名單 %d 檔，湖裡已完整直接記 done %d 檔，還沒補 %d 檔，這一輪補 %d 檔",
             len(codes), marked_lake, len(todo), len(picks))

    fetched = rows = new_nd = 0
    stopped = None
    for i in range(0, len(picks), max(1, int(batch))):
        if i:
            time.sleep(yahoo.BATCH_PAUSE)   # 批與批之間停一下（yahoo.intraday 只在它自己的批次之間停）
        chunk = picks[i:i + batch]
        try:
            df = yahoo.intraday(chunk, markets, "60m", "730d", batch=len(chunk))
        except Exception as exc:  # noqa: BLE001 —— Yahoo 隨時會掛，這層不能拋
            log.warning("60 分 K 回補第 %d 批失敗：%s", i // batch + 1, exc)
            df = pd.DataFrame()
        got = set(df["code"].astype(str)) if df is not None and not df.empty else set()
        if not got and not _canary_ok():
            # 整批回空、連 2330 都拿不到 → 限流或斷線，不是這批沒資料。不記任何 no_data，這一輪收手。
            stopped = f"第 {i // batch + 1} 批整批回空，而且 {CANARY} 也拿不到（多半是 Yahoo 限流或網路），這一輪先停"
            log.warning("60 分 K 回補：%s", stopped)
            break
        if got:
            rows += store.append(TABLE, df)
        for c in chunk:
            k = DONE_PREFIX + c
            if c in got:
                done[k] = True
                tries.pop(c, None)
                fetched += 1
            else:
                tries[c] = int(tries.get(c) or 0) + 1
                if tries[c] >= NO_DATA_TRIES:
                    done[k] = NO_DATA
                    tries.pop(c, None)
                    new_nd += 1
        save(prog)

    remaining = sum(1 for c in codes if not done.get(DONE_PREFIX + c))
    n_ok = sum(1 for c in codes if done.get(DONE_PREFIX + c) is True)
    n_nd = sum(1 for c in codes if done.get(DONE_PREFIX + c) == NO_DATA)
    rec = {
        "done": remaining == 0, "remaining": {TABLE: remaining},
        "codes": len(codes), "ok": n_ok, "no_data": n_nd, "per_run": int(per_run),
        "this_run": {"asked": len(picks), "got": fetched, "new_rows": int(rows),
                     "new_no_data": new_nd, "marked_from_lake": marked_lake},
        "stopped": stopped, "at": datetime.now(timezone.utc).isoformat(),
    }
    prog.setdefault("complete", {})[COMPLETE_KEY] = rec
    save(prog)
    log.info("60 分 K 回補結束：還剩 %d 檔（名單 %d、已補 %d、確認無資料 %d），這一輪拿到 %d 檔、新增 %d 列",
             remaining, len(codes), n_ok, n_nd, fetched, rows)
    return rec
