"""盤中 5 分鐘快照（tape）落地：把 Cloudflare Worker 的 `GET /tape` 存進資料湖 `tape_5m`。

為什麼要落地（2026-10-30，docs/research/20261030_flow_vs_price.md）：
  研究「盤中資金占比能否提前判斷族群強弱」發現 60 分 K 的 09:00–10:00 那根幾乎沒有成交量，
  盤中領先訊號需要更細的資料，而且至少要累積 60 個交易日 —— 但 Worker 的 KV 只留約 8 天
  （workers/quote-proxy/worker.js 的 TAPE_TTL），不落地就會一天天過期消失。

來源與白名單：
  Worker 盤中 Cron 每 5 分鐘從 mis（白名單，DECISIONS #108）抓約 455 檔族群成分股，這裡讀的是**我們自己的** Worker，
  不是新的第三方來源，也不碰 www.twse.com.tw/rwd。

/tape 格式（NDJSON，與 site/tape.js 的 parse() 同一份）：
  第一行 {"date":"2026-10-30","codes":[...],"y":[昨收...]}；之後每行 {"t":"09:05","p":[成交價...],"v":[累計張數...]}，
  順序同 codes，沒有就 null。`GET /tape?date=YYYYMMDD` 取指定日；沒有那天回 404。

怎麼避免漏抓（保底）：
  KV 的 TTL 是 8 天，所以不必擠在收盤後的某一個時間點 —— 每一輪 daily 管線（含隔天清晨、盤中的 news 輪）
  都回頭掃最近 8 天，湖裡還沒收齊（沒有 13:30 之後那一格）的交易日就補抓；收齊的不再打 Worker。
  另有 .github/workflows/tape-lake.yml 在 14:07 專門抓一次、可手動觸發。
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from .. import config
from ..util import http, store

log = logging.getLogger(__name__)

# 我們自己的 Worker（site/live.js 的 DEFAULT_PROXY 同一台）。可用環境變數換，測試／備援用。
DEFAULT_PROXY = "https://tw-quote.kcq01010909.workers.dev"
# Worker 對有帶 Origin 的請求會檢查白名單；帶自家網域最保險（沒帶 Origin 也放行）。
ORIGIN = "https://liguligu-puipui.com"
KV_DAYS = 8                       # Worker 的 TAPE_TTL（8 天）；往回掃的天數
COMPLETE_SLOT = "13:30"           # 湖裡某天有 ≥ 這一格就視為收齊（最後一格是 13:35，13:30 是收盤試撮）
READY_AFTER = (13, 40)            # 今天要 13:40 之後才抓：盤中抓會寫進半天，雖然之後會補齊，但白白多 commit

COLUMNS = ["ts", "code", "price", "cum_lots", "cum_value", "prev_close", "src", "val_src"]


def _proxy() -> str:
    return (os.environ.get("TAPE_PROXY_URL") or DEFAULT_PROXY).rstrip("/")


def _tpe_now() -> datetime:
    """台北當下時間（測試會換掉）。只用來決定「今天收盤了沒」，交易日一律取自 /tape 回應的 date。"""
    return datetime.now(timezone(timedelta(hours=8)))


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x else None          # NaN 視為沒有


def parse(text: str) -> pd.DataFrame:
    """把 /tape 的 NDJSON 轉成 tape_5m 的形狀。解析不了回空 DataFrame 並把前 200 字記進 log（上游改格式時才有得修）。

    成交值估算：tape 沒有成交值，逐格「新增張數 × 1000 × 該格成交價」累加（比「累計張數 × 最新價」準，
    後者會把早盤的量全部乘上尾盤的價）。缺格時那段新增量按下一格的價算，誤差小於一格的價差。
    """
    empty = pd.DataFrame(columns=COLUMNS)
    try:
        lines = [l for l in str(text or "").split("\n") if l.strip()]
        head = json.loads(lines[0])
        codes, date = head["codes"], str(head["date"])[:10]
        if len(date) != 10 or date[4] != "-":
            raise ValueError(f"date 格式不對：{head.get('date')!r}")
        ys = head.get("y") or []
        slots = []
        for l in lines[1:]:
            try:           # 壞行略過（寫到一半被讀走），與 site/tape.js 同一個容錯
                s = json.loads(l)
                if s.get("t") and s.get("p"):
                    slots.append(s)
            except ValueError:
                continue
    except Exception as exc:  # noqa: BLE001 —— 任何格式不符都回空，不讓單一來源拖垮管線
        log.warning("tape 解析失敗（%s），回應前 200 字：%r", exc, str(text)[:200])
        empty.attrs["error"] = f"parse:{exc}"[:200]
        return empty

    slots.sort(key=lambda s: s["t"])
    prev_lots = [0.0] * len(codes)
    cum_val = [0.0] * len(codes)
    rows = []
    for s in slots:
        ts = f"{date}T{s['t']}:00+08:00"
        ps, vs = s["p"], s.get("v") or []
        for i, code in enumerate(codes):
            price = _num(ps[i]) if i < len(ps) else None
            if price is None:
                continue
            lots = _num(vs[i]) if i < len(vs) else None
            if lots is not None:
                # 累計量只會增加；變小（mis 偶爾回舊值）當 0 新增，不倒扣
                cum_val[i] += max(lots - prev_lots[i], 0.0) * 1000 * price
                prev_lots[i] = max(lots, prev_lots[i])
            rows.append({
                "ts": ts, "code": str(code), "price": price,
                "cum_lots": lots,
                "cum_value": round(cum_val[i], 0) if lots is not None else None,
                "prev_close": _num(ys[i]) if i < len(ys) else None,
                "src": "tape", "val_src": "est",
            })
    return pd.DataFrame(rows, columns=COLUMNS) if rows else empty


def fetch_day(date8: str | None = None) -> pd.DataFrame:
    """向 Worker 要某一天的 /tape（YYYYMMDD；None＝Worker 的最新一天）。失敗（404／連不上／格式不符）回空 DataFrame。"""
    url = _proxy() + "/tape"
    params = {"date": date8} if date8 else None
    text = http.get(url, params=params, headers={"Origin": ORIGIN}, expect_json=False)
    if not text:
        out = pd.DataFrame(columns=COLUMNS)
        out.attrs["error"] = f"{date8 or 'latest'}: 無回應（404＝KV 沒有那天，或 Worker 連不上）"
        return out
    return parse(text)


def candidate_dates(now: datetime, complete: set[str]) -> list[str]:
    """最近 KV_DAYS 天裡該去補抓的平日（YYYYMMDD，新到舊）：略過湖裡已收齊的、略過還沒收盤的今天。"""
    out = []
    for back in range(KV_DAYS + 1):
        d = (now - timedelta(days=back)).date()
        if d.weekday() >= 5:
            continue
        d8 = d.strftime("%Y%m%d")
        if back == 0 and (now.hour, now.minute) < READY_AFTER:
            continue
        if d8 in complete:
            continue
        out.append(d8)
    return out


def complete_days(now: datetime) -> set[str]:
    """湖裡已收齊（有 ≥ COMPLETE_SLOT 那一格）的日期（YYYYMMDD）。只讀最近兩個月的分割。"""
    months = {int((now - timedelta(days=b)).strftime("%Y%m")) for b in (0, KV_DAYS + 1)}
    have = store.read("tape_5m", years=sorted(months))
    if have.empty or "ts" not in have.columns:
        return set()
    t = have["ts"].astype(str)
    return set(t[t.str[11:16] >= COMPLETE_SLOT].str[:10].str.replace("-", "", regex=False))


def collect(now: datetime | None = None) -> pd.DataFrame:
    """回頭補抓 KV 還留著、湖裡還沒收齊的交易日。沒有要補的、或全部失敗都回空 DataFrame（不拋例外）。

    ★ 交易日取自 /tape 回應裡的 date；休市日 Worker 不寫 KV，會回 404 → 空，天然略過。
    """
    now = now or _tpe_now()
    parts, miss = [], []
    try:
        todo = candidate_dates(now, complete_days(now))
    except Exception as exc:  # noqa: BLE001
        log.warning("tape 判斷待補日期失敗，改成全部掃：%s", exc)
        todo = candidate_dates(now, set())
    for d8 in todo:
        try:
            df = fetch_day(d8)
        except Exception as exc:  # noqa: BLE001
            log.warning("tape %s 抓取失敗：%s", d8, exc)
            continue
        if df.empty:
            miss.append(d8)
        else:
            log.info("tape %s：%d 列、%d 格", d8, len(df), df["ts"].nunique())
            parts.append(df)
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=COLUMNS)
    out.attrs["todo"], out.attrs["miss"] = todo, miss
    return out


def main() -> int:
    """獨立入口（.github/workflows/tape-lake.yml）：抓、寫進資料湖、寫 data/_state/tape_last.json。

    不走 run_daily：那條會覆寫 last_run.json，heal_daily.py 靠它判斷「今天價量 phase 補過沒」，不能被這支蓋掉。
    一律回 0：KV 還沒有／連不上是常態，不該讓工作流紅燈。
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df = collect()
    added = store.append("tape_5m", df) if not df.empty else 0
    info = {
        "at": datetime.now(timezone.utc).isoformat(),
        "todo": df.attrs.get("todo"), "miss": df.attrs.get("miss"),
        "rows": int(len(df)), "added": int(added),
        "days": sorted({str(t)[:10] for t in df["ts"]}) if not df.empty else [],
    }
    (config.STATE / "tape_last.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("tape 落地：%s", info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
