"""盤中收集器：整個交易時段輪詢 mis，把每檔的大單／小單買賣（推估）彙整成一天一列，寫進資料湖 bigsmall_daily。

為什麼要自己收：日 K 級別的「大單／小單淨買賣」沒有免費合規來源（docs/bigsmall_sources.md 第 2 節）——
  FinMind 逐筆（TaiwanStockPriceTick）、分 K（TaiwanStockKBar）、分點（TaiwanStockTradingDailyReport）2026-11-07 實測都回
  「Your level is register」；證交所 openapi 143 支、櫃買 openapi 225 支端點裡沒有個股逐筆或單量分級（只有日成交、鉅額、分價表）。
  所以從開始收集那天起逐日累積，**補不了過去**（回補要買 FinMind 贊助方案或證交所 Data E-Shop 的歷史逐筆，見文件第 5 節）。

在哪裡跑：.github/workflows/bigsmall-collect.yml，台北 08:50 起一個 job 跑到 13:36（GitHub 一個 job 上限 6 小時）。
來源與自我約束（DECISIONS #108 白名單內的 mis；不碰 www.twse.com.tw/rwd、不碰券商分點）：
  · 名單＝Worker 盤中快照（tape）同一份族群／題材成分股（約 455 檔），不是全市場。
  · 一個請求最多 BATCH 檔、請求之間至少隔 REQ_GAP 秒（社群經驗 mis 太密會鎖 IP 約一小時），所以每檔約每 10 秒取樣一次。
  · 連續失敗就退避（60 秒起、最長 5 分鐘），不硬打。
  · 中途每 SAVE_EVERY 秒把目前累計寫到 data/_state/bigsmall_live.json（只給除錯，不進湖），收盤後才寫湖。

用法：python -m pipeline.sources.bigsmall_collect            # 正常：等到 08:59:30 開始、13:36 結束、寫湖
      python -m pipeline.sources.bigsmall_collect --once     # 只打一輪（除錯）
"""
from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from .. import config
from ..compute import bigsmall
from ..util import http, store

log = logging.getLogger(__name__)

TABLE = "bigsmall_daily"
BATCH = 100                      # 一個請求幾檔（Worker 實測 120 檔 OK，留邊際）
REQ_GAP = 2.0                    # 兩個請求之間至少隔幾秒
START_AT = (8, 59, 30)           # 開始輪詢（台北）
STOP_AT = (13, 36, 0)            # 停止（收盤 13:30，多留幾分鐘等收盤那一筆落地）
SAVE_EVERY = 300
TAPE_CODES_URL = "https://liguligu-puipui.com/data/tape_codes.json"
STATE = config.DATA / "_state" / "bigsmall_last.json"
LIVE = config.DATA / "_state" / "bigsmall_live.json"
TPE = timezone(timedelta(hours=8))


def _now() -> datetime:
    return datetime.now(TPE)


def universe() -> list[tuple[str, str]]:
    """[(代號, 'tse'|'otc')]：先拿線上的 tape_codes.json（Worker 用的同一份），拿不到就用湖裡最近一天的 tape 代號＋price_daily 的市場別。"""
    j = http.get(TAPE_CODES_URL, headers={"Origin": "https://liguligu-puipui.com"})
    if isinstance(j, dict) and j.get("codes"):
        return [(str(c), str(m)) for c, m in j["codes"]]
    try:
        from .tape_rebuild import universe as tape_uni
        codes = tape_uni()
        px = store.read("price_daily", years=[_now().year])
        mk = {}
        if not px.empty and "market" in px.columns:
            mk = dict(zip(px["code"].astype(str), px["market"].astype(str)))
        return [(c, "otc" if str(mk.get(c, "")).upper() in ("TPEX", "OTC") else "tse") for c in codes]
    except Exception as exc:  # noqa: BLE001
        log.warning("大小單名單：tape 名單也拿不到（%s）", exc)
        return []


def thresholds(codes: list[str]) -> dict[str, float]:
    now = _now()
    px = store.read("price_daily", years=[now.year - 1, now.year])
    avg = bigsmall.avg_trade_amount(px)
    return {c: bigsmall.threshold(avg.get(c)) for c in codes}


def _fetch(batch: list[tuple[str, str]]) -> list[dict] | None:
    ex = "|".join(f"{m}_{c}.tw" for c, m in batch)
    j = http.get(config.MIS_QUOTE, params={"json": "1", "delay": "0", "ex_ch": ex, "_": str(int(time.time() * 1000))},
                 headers={"Referer": "https://mis.twse.com.tw/stock/index.jsp"}, retries=1, timeout=10)
    if not isinstance(j, dict) or j.get("rtcode") not in (None, "0000"):
        return None
    return j.get("msgArray") or []


def _date_of(msgs: list[dict]) -> str | None:
    for m in msgs:
        d = str(m.get("d") or "")
        if len(d) == 8 and d.isdigit():
            return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return None


def already_have(date: str) -> bool:
    try:
        have = store.read(TABLE, years=[int(date[:4])])
    except Exception:  # noqa: BLE001
        return False
    return not have.empty and (have["date"].astype(str).str[:10] == date).any()


def rows_of(accs: dict[str, bigsmall.Acc], date: str) -> pd.DataFrame:
    rows = [a.row(date, c) for c, a in accs.items() if a.v is not None]
    return pd.DataFrame(rows, columns=bigsmall.COLUMNS) if rows else pd.DataFrame(columns=bigsmall.COLUMNS)


def _write_json(path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def run(once: bool = False) -> int:
    uni = universe()
    if not uni:
        log.error("大小單收集：沒有名單，結束")
        _write_json(STATE, {"at": _now().isoformat(), "ok": False, "why": "沒有名單"})
        return 1
    thr = thresholds([c for c, _ in uni])
    accs = {c: bigsmall.Acc(thr=thr.get(c, float(bigsmall.BIG_FLOOR))) for c, _ in uni}
    batches = [uni[i:i + BATCH] for i in range(0, len(uni), BATCH)]
    now = _now()
    start = now.replace(hour=START_AT[0], minute=START_AT[1], second=START_AT[2], microsecond=0)
    stop = now.replace(hour=STOP_AT[0], minute=STOP_AT[1], second=STOP_AT[2], microsecond=0)
    if not once and now >= stop:
        log.info("大小單收集：已過 %02d:%02d，今天不收", *STOP_AT[:2])
        return 0
    if not once and now < start:
        wait = (start - now).total_seconds()
        log.info("大小單收集：等 %.0f 秒到 %02d:%02d:%02d", wait, *START_AT)
        time.sleep(wait)
    date, fails, last_req, last_save, cycles, backoff, checked = None, 0, 0.0, time.time(), 0, 60, False
    started = _now().strftime("%H:%M:%S")
    while True:
        for b in batches:
            gap = REQ_GAP - (time.time() - last_req)
            if gap > 0:
                time.sleep(gap)
            last_req = time.time()
            msgs = _fetch(b)
            if msgs is None:
                fails += 1
                if fails >= 3:
                    log.warning("mis 連續失敗 %d 次，退避 %d 秒", fails, backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 300)
                continue
            fails, backoff = 0, 60
            date = date or _date_of(msgs)
            if date and not once and not checked:
                checked = True
                if already_have(date):
                    log.info("大小單收集：湖裡已有 %s，略過（排隊的第二個排程）", date)
                    return 0
            for m in msgs:
                c = str(m.get("c") or "")
                if c in accs:
                    accs[c].step(m)
        cycles += 1
        if once or _now() >= stop:
            break
        if time.time() - last_save >= SAVE_EVERY and date:
            last_save = time.time()
            _write_json(LIVE, {"date": date, "at": _now().isoformat(), "cycles": cycles,
                               "rows": rows_of(accs, date).head(20).to_dict("records")})
    if not date:
        log.warning("大小單收集：一筆都沒拿到")
        _write_json(STATE, {"at": _now().isoformat(), "ok": False, "why": "mis 一筆都沒回"})
        return 1
    df = rows_of(accs, date)
    n = 0 if once else store.append(TABLE, df)
    cov = pd.to_numeric(df["coverage"], errors="coerce")
    _write_json(STATE, {"at": _now().isoformat(), "ok": True, "date": date, "started": started, "codes": len(df), "cycles": cycles,
                        "new_rows": int(n), "coverage_median": None if cov.dropna().empty else round(float(cov.median()), 4),
                        "pre_lots_median": float(pd.to_numeric(df["pre"], errors="coerce").median() or 0)})
    log.info("大小單收集 %s：%d 檔、%d 輪、新增 %d 列", date, len(df), cycles, n)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = argv if argv is not None else sys.argv[1:]
    return run(once="--once" in args)


if __name__ == "__main__":
    raise SystemExit(main())
