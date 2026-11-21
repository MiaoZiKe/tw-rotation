"""臺灣期貨交易所「每日期貨每筆成交資料」→ 臺指期（TX）近月 1 分 K（日盤 FUT／夜盤 FUT_N）。

為什麼有這一支（2026-09-26）
----------------------------
總覽「大盤三張圖」的台指期多日分 K（15 分／1H／4H）原本只能從 09-26 起每天自己存 mis 分時檔慢慢長，
而且 mis 那個檔**只有日盤**。Andy 問「目前沒有免費管道嗎」，查到期交所自己公開的逐筆成交：
  · 政府資料開放平臺 資料集 20668「每日期貨每筆成交資料」，授權＝**政府資料開放授權條款－第 1 版**
    （提供機關：金管會證期局，免費、每日更新）。
  · 期交所「前 30 個交易日期貨每筆成交資料（不含鉅額）」下載頁，*.rpt／*.csv 兩種格式。
查證紀錄與限制寫在 `docs/source_whitelist_taifex_tpex.md`（為什麼可用、出處怎麼標、哪些沒查到）。
一次可以拿回過去約 30 個交易日（含夜盤、含真實口數），之後每天接著存。

檔案格式（依期交所欄位名稱與社群文件描述，**不是實抓**；容器連不到外網）
----------------------------------------------------------------------
  成交日期, 商品代號, 到期月份(週別), 成交時間, 成交價格, 成交數量(B+S), 近月價格, 遠月價格, 開盤集合競價
  · 每個欄位右側可能補空白（`TX     `），時間是 HHMMSS（前導 0 可能被吃掉，`84500`）。
  · 到期月份帶 `/` 的是價差單（`202610/202611`），**丟掉**；帶 `W` 的是週契約，近月不選它
    （週契約每週換，接起來的序列會每週跳一次）。
  · 成交數量(B+S) 是買賣雙邊合計，口數＝÷2。這個除數**執行時再跟 FinMind 日 K 對一次**（vol_divisor），
    對不上就記 log，不靠記憶。
解析一律找表頭欄名；表頭認不得、而且第一欄也不像日期時，整檔不收並把**回應前 200 字**寫進 log。

夜盤歸屬（期交所規定，高信心）與這個檔「成交日期」欄位的寫法（中信心）
----------------------------------------------------------------------
期交所：盤後交易時段（15:00～次日 05:00）的交易**歸屬次一一般交易時段**；
查詢頁也寫明「標示交易日期 2017/7/4 之 TX 盤後資料，為 2017/7/3 15:00 至 2017/7/4 05:00」。
但這個逐筆檔的「成交日期」到底寫**歸屬日**還是**日曆日**，沒有查到第一手說明。所以不猜，看資料本身：
  · 同一個檔裡，夜盤晚上那段（≥15:00）與凌晨那段（≤05:00）的成交日期**相同** → 寫的是歸屬日（attr）。
    這時晚上那段真正的日曆日＝歸屬日的**前一個交易日**（週五夜盤歸屬週一，晚上那段是週五），
    凌晨那段＝那天的隔一個日曆日。前一個交易日要從資料裡找得到（日盤列＋資料湖的日 K 日期），
    找不到就**不收那幾筆**（寫錯的時間進只增不改的資料湖就洗不掉了）。
  · 凌晨那段剛好比晚上那段晚一個日曆日 → 寫的是日曆日（cal），直接用。
  · 只有一段、判斷不出來 → 跟同一批其他檔的判斷走；整批都判斷不出來就照期交所公告的口徑當歸屬日。
存進資料湖的 `ts` 一律是**真正的台北牆鐘時間**，夜盤的「這一盤是哪天開的」由 intraday_bars.session_key()
照牆鐘時間自己算（夜盤 4H 歸在開盤那天，跟前端 sessKey() 一致）。

1 分 K 的口徑
-------------
  · 近月＝**那一盤**（日盤、或某一晚的夜盤）裡成交口數最多的單一月份（跟 finmind 日 K、ticks_to_60m 同一個規則），
    換月那幾天自然換過去，不會同一盤混兩個月份。
  · 時間戳＝那一分鐘的**開始**（08:45:00～08:45:59 → 08:45），跟 Yahoo／15 分聚合同一個慣例。
  · 開高低收＝那一分鐘逐筆的第一筆／最高／最低／最後一筆（真的盤中極值，比 mis 由分鐘收盤合成的準）。
  · 量＝口數。src="taifex"。
"""
from __future__ import annotations

import csv
import io
import json
import logging
import zipfile
from datetime import datetime, timedelta, timezone

import pandas as pd

from .. import config
from ..util import http

log = logging.getLogger(__name__)

TZ = "Asia/Taipei"
SRC = "taifex"

# 時段（HHMMSS 整數）。日盤 08:45～13:45；夜盤 15:00～翌日 05:00。時段外的列丟掉並計數。
DAY_FROM, DAY_TO = 84500, 134559
NIGHT_FROM, NIGHT_TO = 150000, 50059

# 表頭關鍵字 → 內部欄名（找「欄名含這個字」的第一欄；期交所改過欄名時只要關鍵字還在就接得住）
HEAD_KEYS = [("date", "成交日期"), ("product", "商品代號"), ("month", "到期月份"),
             ("time", "成交時間"), ("price", "成交價格"), ("qty", "成交數量")]


def _head(x) -> str:
    """回應前 200 字（上游改格式時，下一個人靠這一段才修得動）。"""
    if isinstance(x, bytes):
        x = x[:400].decode("cp950", errors="replace")
    return str(x)[:200].replace("\n", "⏎").replace("\r", "")


def _decode(raw: bytes) -> str:
    """期交所的檔多半是 Big5（cp950），偶爾是 UTF-8（帶 BOM）。先試 UTF-8 嚴格解碼，失敗再 cp950。"""
    for enc in ("utf-8-sig", "cp950", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp950", errors="replace")


def _unzip(raw: bytes) -> str | None:
    """zip 位元組 → 第一個 csv／rpt 檔的文字。不是 zip 就當成文字本身。"""
    if raw[:2] != b"PK":
        return _decode(raw)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = [n for n in z.namelist() if n.lower().endswith((".csv", ".rpt", ".txt"))]
            if not names:
                log.warning("期交所逐筆 zip 裡沒有 csv／rpt：%s", z.namelist()[:5])
                return None
            return _decode(z.read(names[0]))
    except zipfile.BadZipFile as exc:
        log.warning("期交所逐筆 zip 壞掉：%s（前 200 字）：%s", exc, _head(raw))
        return None


def _to_int_time(s: str) -> int | None:
    s = str(s).strip()
    if not s:
        return None
    s = s.split(".")[0]                       # 有些版本帶小數秒
    if not s.isdigit() or len(s) > 6:
        return None
    t = int(s)
    hh, mm, ss = t // 10000, (t // 100) % 100, t % 100
    if hh > 23 or mm > 59 or ss > 59:
        return None
    return t


def parse_ticks(raw, product: str = "TX", file_id: str | None = None) -> pd.DataFrame:
    """一個逐筆檔（zip 位元組、或已解開的文字）→ 只留 `product` 的逐筆長表。

    回傳欄位：date（YYYYMMDD 字串，檔案裡寫的）, time（HHMMSS 整數）, month（到期月份字串）,
             price（float）, qty（float，檔案原值＝B+S 雙邊）, seq（檔內順序，同一秒多筆時保持先後）, file。
    失敗（不是 zip／表頭認不得／一筆都解析不出來）回空 DataFrame 並記 log（含前 200 字）。
    """
    empty = pd.DataFrame()
    try:
        text = _unzip(raw) if isinstance(raw, (bytes, bytearray)) else str(raw)
    except Exception as exc:  # noqa: BLE001 —— 單一檔壞掉不能讓整條管線死
        log.warning("期交所逐筆 %s 解開失敗：%s（前 200 字）：%s", file_id, exc, _head(raw))
        return empty
    if not text:
        return empty
    text = text.lstrip("﻿")
    rows = csv.reader(io.StringIO(text))
    idx: dict[str, int] | None = None
    out, bad, total = [], 0, 0
    want = product.strip().upper()
    for i, rec in enumerate(rows):
        # 檔案裡是全部期貨商品（一天上百萬列），先只看商品代號那一欄，不是要的就跳過，不逐欄 strip
        if idx is not None:
            j = idx["product"]
            if len(rec) <= j or rec[j].strip().upper() != want:
                continue
        cells = [c.strip() for c in rec]
        if not any(cells):
            continue
        if idx is None:
            # 第一個非空列：先當表頭找欄名；找不到但第一欄像日期（8 碼數字）就照期交所公告的欄位順序
            found = {}
            for key, kw in HEAD_KEYS:
                for j, c in enumerate(cells):
                    if kw in c:
                        found[key] = j
                        break
            if len(found) == len(HEAD_KEYS):
                idx = found
                continue
            if cells[0].isdigit() and len(cells[0]) == 8 and len(cells) >= 6:
                idx = {k: j for j, (k, _) in enumerate(HEAD_KEYS)}
                log.warning("期交所逐筆 %s 沒有認得的表頭，照公告欄位順序解析（前 200 字）：%s",
                            file_id, _head(text))
            else:
                log.warning("期交所逐筆 %s 表頭認不得、整檔不收（前 200 字）：%s", file_id, _head(text))
                return empty
        total += 1
        if len(cells) <= max(idx.values()):
            bad += 1
            continue
        d = cells[idx["date"]]
        t = _to_int_time(cells[idx["time"]])
        try:
            px = float(cells[idx["price"]].replace(",", ""))
            q = float(cells[idx["qty"]].replace(",", ""))
        except ValueError:
            bad += 1
            continue
        if not (len(d) == 8 and d.isdigit()) or t is None or px <= 0 or q <= 0:
            bad += 1
            continue
        out.append((d, t, cells[idx["month"]], px, q, i))
    if idx is None:
        log.warning("期交所逐筆 %s 是空檔（前 200 字）：%s", file_id, _head(text))
        return empty
    if total and bad > total * 0.05:
        log.warning("期交所逐筆 %s：%s %d 筆裡 %d 筆解析不出來，判定格式變了、整檔不收（前 200 字）：%s",
                    file_id, want, total, bad, _head(text))
        return empty
    if not out:
        log.warning("期交所逐筆 %s 找不到任何 %s 的成交（前 200 字）：%s", file_id, want, _head(text))
        return empty
    if bad:
        log.info("期交所逐筆 %s：丟掉 %d 筆壞值", file_id, bad)
    df = pd.DataFrame(out, columns=["date", "time", "month", "price", "qty", "seq"])
    df["file"] = file_id or ""
    return df


# ------------------------------------------------------------------ 夜盤：成交日期 → 真正的牆鐘時間

def _session_of(t: int) -> str | None:
    if DAY_FROM <= t <= DAY_TO:
        return "day"
    if t >= NIGHT_FROM or t <= NIGHT_TO:
        return "night"
    return None


def _next_cal(d: str) -> str:
    return (pd.Timestamp(d) + pd.Timedelta(days=1)).strftime("%Y%m%d")


def detect_convention(night: pd.DataFrame) -> str | None:
    """一個檔的夜盤列 → 'attr'（成交日期寫歸屬日）／'cal'（寫日曆日）／None（判斷不出來）。"""
    if night.empty:
        return None
    eve = set(night.loc[night["time"] >= NIGHT_FROM, "date"])
    morn = set(night.loc[night["time"] <= NIGHT_TO, "date"])
    if not eve or not morn:
        return None
    if eve == morn:
        return "attr"
    if morn == {_next_cal(e) for e in eve}:
        return "cal"
    return None


def attach_wall_time(ticks: pd.DataFrame, known_days=None) -> pd.DataFrame:
    """逐筆長表 → 加上 session（day／night）、wall（台北牆鐘 naive Timestamp）、open_day（這一盤開盤那天）。

    known_days：已知的交易日（'YYYYMMDD' 或 'YYYY-MM-DD'），用來在「成交日期寫歸屬日」時找前一個交易日。
    日盤列本身的日期也會自動加進去。時段外、或找不到前一個交易日的夜盤列丟掉並記 log。
    """
    if ticks is None or ticks.empty:
        return pd.DataFrame()
    df = ticks.copy()
    df["session"] = df["time"].map(_session_of)
    n_out = int(df["session"].isna().sum())
    df = df[df["session"].notna()].copy()
    if n_out:
        log.info("期交所逐筆：%d 筆落在交易時段外，丟掉", n_out)
    days = {str(d).replace("-", "") for d in (known_days or [])}
    days |= set(df.loc[df["session"] == "day", "date"])
    days_sorted = sorted(days)

    night = df[df["session"] == "night"]
    if "file" not in df.columns:
        df["file"] = ""
    conv = {f: detect_convention(g) for f, g in night.groupby("file")}
    decided = [c for c in conv.values() if c]
    fallback = max(set(decided), key=decided.count) if decided else "attr"
    for f, c in conv.items():
        if c is None:
            log.info("期交所逐筆 %s：夜盤只有一段、判斷不出成交日期的寫法，照 %s", f or "(未命名)", fallback)
    df["conv"] = df["file"].map(lambda f: conv.get(f) or fallback)

    def _prev_day(a: str) -> str | None:
        import bisect
        i = bisect.bisect_left(days_sorted, a)
        return days_sorted[i - 1] if i > 0 else None

    # 一天幾十萬筆，逐列建 Timestamp 太慢：同一個（日期, 時段, 寫法, 晚上/凌晨）的基準日都一樣，
    # 先對「組合」算一次，再整欄拼字串交給 to_datetime。
    df["eve"] = df["time"] >= NIGHT_FROM
    combo: dict = {}
    for d, s, c, eve in df[["date", "session", "conv", "eve"]].drop_duplicates().itertuples(index=False):
        if s == "day":
            combo[(d, s, c, eve)] = (d, d)
        elif c == "cal":
            od = d if eve else (pd.Timestamp(d) - pd.Timedelta(days=1)).strftime("%Y%m%d")
            combo[(d, s, c, eve)] = (d, od)
        else:
            e = _prev_day(d)
            combo[(d, s, c, eve)] = (None, None) if e is None else ((e if eve else _next_cal(e)), e)
    keys = list(zip(df["date"], df["session"], df["conv"], df["eve"]))
    base = pd.Series([combo[k][0] for k in keys], index=df.index)
    df["open_day"] = [combo[k][1] for k in keys]
    txt = base + " " + df["time"].astype(int).astype(str).str.zfill(6)
    df["wall"] = pd.to_datetime(txt.where(base.notna()), format="%Y%m%d %H%M%S", errors="coerce")
    df = df.drop(columns=["eve"])
    lost = int(df["wall"].isna().sum())
    if lost:
        log.warning("期交所逐筆：%d 筆夜盤找不到前一個交易日（成交日期寫歸屬日、資料裡沒有更早的日盤），不收", lost)
    return df[df["wall"].notna()].drop(columns=["conv"]).reset_index(drop=True)


# ------------------------------------------------------------------ 口數：B+S 要不要 ÷2

def vol_divisor(raw_day: dict, official: dict) -> float:
    """每天日盤近月的「成交數量(B+S)」加總 vs FinMind 日 K（index_ohlc FUT）的量 → 除數。

    B+S 字面是買賣雙邊合計，口數＝÷2（預設）。但這是依欄名推的，所以只要湖裡有同一天的官方日 K 就再對一次：
    比值落在 2 附近 → 2；落在 1 附近 → 1（代表檔案其實已經是單邊）；都不像 → 還是 2，但記 warning。
    """
    ratios = []
    for d, raw in raw_day.items():
        off = official.get(d)
        if off and off > 0 and raw > 0:
            ratios.append(raw / off)
    if not ratios:
        return 2.0
    r = float(pd.Series(ratios).median())
    if 1.7 <= r <= 2.3:
        return 2.0
    if 0.85 <= r <= 1.15:
        log.warning("期交所逐筆：B+S 加總 ≈ 官方日 K 量（比值 %.2f），判定檔案已是單邊口數，不除 2", r)
        return 1.0
    log.warning("期交所逐筆：B+S 加總 ÷ 官方日 K 量 = %.2f（%d 天），不像 2 也不像 1，照預設 ÷2；請人工查", r, len(ratios))
    return 2.0


# ------------------------------------------------------------------ 逐筆 → 1 分 K

def _near_month(g: pd.DataFrame) -> str | None:
    """一盤裡成交口數最多的單一月份（價差單帶 `/` 丟掉；週契約帶 W 不選，除非只剩週契約）。"""
    m = g["month"].astype(str)
    ok = g[~m.str.contains("/", na=False)]
    mono = ok[~ok["month"].astype(str).str.upper().str.contains("W", na=False)]
    pick = mono if not mono.empty else ok
    if pick.empty:
        return None
    return pick.groupby("month")["qty"].sum().idxmax()


def ticks_to_1m(df: pd.DataFrame, divisor: float = 2.0) -> pd.DataFrame:
    """attach_wall_time() 的結果 → 1 分 K（`index_intraday` 的形狀）。

    欄位：ts（台北 ISO，帶 +08:00；那一分鐘的開始）, symbol（FUT 日盤／FUT_N 夜盤）, interval="1m",
         open, high, low, close, volume（口數）, src="taifex"。
    """
    if df is None or df.empty or "wall" not in df.columns:
        return pd.DataFrame()
    rows = []
    for (sess, od), g in df.groupby(["session", "open_day"], sort=True):
        near = _near_month(g)
        if near is None:
            continue
        g = g[g["month"] == near].sort_values(["wall", "seq"], kind="stable")
        g = g.assign(minute=g["wall"].dt.floor("min"))
        sym = "FUT_N" if sess == "night" else "FUT"
        agg = g.groupby("minute", sort=True).agg(open=("price", "first"), high=("price", "max"),
                                                 low=("price", "min"), close=("price", "last"),
                                                 qty=("qty", "sum"))
        for mnt, r in zip(agg.index, agg.itertuples(index=False)):
            rows.append({"ts": mnt.tz_localize(TZ).isoformat(), "symbol": sym, "interval": "1m",
                         "open": float(r.open), "high": float(r.high), "low": float(r.low),
                         "close": float(r.close), "volume": float(r.qty) / divisor, "src": SRC})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 下載與增量

def _state_path():
    return config.STATE / "taifex_ticks.json"


def load_state() -> dict:
    try:
        s = json.loads(_state_path().read_text(encoding="utf-8"))
        if isinstance(s, dict):
            s.setdefault("done", {})
            s.setdefault("absent", {})
            return s
    except (OSError, ValueError):
        pass
    return {"done": {}, "absent": {}}


def save_state(s: dict) -> None:
    try:
        _state_path().parent.mkdir(parents=True, exist_ok=True)
        _state_path().write_text(json.dumps(s, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        log.warning("寫入 %s 失敗：%s", _state_path(), exc)


def candidate_dates(now: datetime | None = None, lookback: int | None = None) -> list[str]:
    """要試著下載的檔名日期（YYYY-MM-DD，週一～五），由新到舊。

    ⚠ 這裡用「現在」只是為了**列出候選檔名**（檔名就是日期，沒有索引頁可讀）；
    交易日一律取檔案內容的成交日期，拿到 404 的日子（假日）記進 absent 之後不再試。
    """
    lookback = config.TAIFEX_TICK_LOOKBACK_DAYS if lookback is None else lookback
    now = now or datetime.now(timezone.utc)
    today = pd.Timestamp(now).tz_convert(TZ).normalize().tz_localize(None)
    out = []
    for k in range(lookback + 1):
        d = today - pd.Timedelta(days=k)
        if d.weekday() < 5:
            out.append(d.strftime("%Y-%m-%d"))
    return out


def fetch_day(day: str) -> tuple[int, bytes | None]:
    """下載一天的逐筆 zip。回 (狀態碼, 位元組或 None)；連線失敗回 (0, None)。"""
    y, m, d = day.split("-")
    url = config.TAIFEX_TICKS_CSV.format(y=y, m=m, d=d)
    res = http.get_bytes(url, headers={"Referer": config.TAIFEX_TICKS_PAGE}, timeout=120,
                         max_bytes=config.TAIFEX_TICK_MAX_BYTES, retries=2)
    if res is None:
        return 0, None
    status, body, ctype, _ = res
    if status != 200:
        return status, None
    if body[:2] != b"PK":
        # 期交所對不存在的日期有時回 200 + 一張 HTML 錯誤頁；那不是資料，照 404 看待
        log.info("期交所逐筆 %s 回 200 但不是 zip（%s；前 200 字）：%s", day, ctype, _head(body))
        return 404, None
    return 200, body


def minute_bars(known_days=None, official_vol: dict | None = None, now: datetime | None = None,
                max_files: int | None = None) -> pd.DataFrame:
    """下載還沒處理過的逐筆檔 → TX 近月 1 分 K。任何一步失敗都只記 log，回空或回拿得到的部分。

    known_days：資料湖已知的交易日（找「歸屬日的前一個交易日」用）。
    official_vol：{'YYYYMMDD': FinMind 日盤近月量（口）}，拿來核對 B+S 的除數。
    進度寫在 data/_state/taifex_ticks.json：done＝已收的檔、absent＝404 的日子（假日），都不再下載。
    """
    max_files = config.TAIFEX_TICK_MAX_FILES if max_files is None else max_files
    st = load_state()
    now = now or datetime.now(timezone.utc)
    today = pd.Timestamp(now).tz_convert(TZ).strftime("%Y-%m-%d")
    cands = candidate_dates(now)
    keep = set(cands)
    # 窗外的舊紀錄清掉（期交所只留 30 個交易日，窗外的檔本來就抓不到）
    st["done"] = {k: v for k, v in st["done"].items() if k in keep}
    st["absent"] = {k: v for k, v in st["absent"].items() if k in keep}
    todo = [d for d in cands if d not in st["done"] and d not in st["absent"]][:max_files]
    if not todo:
        log.info("期交所逐筆：窗內 %d 個候選日都處理過了", len(cands))
        save_state(st)
        return pd.DataFrame()

    frames = []
    for day in todo:
        status, body = fetch_day(day)
        if status == 404:
            # 今天、昨天的檔可能只是還沒出；再早的 404 就是假日，記下來不再試。
            # 403／5xx 不記（可能是暫時擋雲端 IP 或主機出狀況），下一輪照試。
            if (pd.Timestamp(today) - pd.Timestamp(day)).days >= 2:
                st["absent"][day] = now.isoformat(timespec="seconds")
            log.info("期交所逐筆 %s：HTTP %s（假日或還沒出）", day, status)
            continue
        if body is None:
            log.warning("期交所逐筆 %s：下載失敗（HTTP %s），下一輪再試", day, status)
            continue
        t = parse_ticks(body, product=config.TAIFEX_TICK_PRODUCT, file_id=day)
        if t.empty:
            continue                          # 格式問題已記 log（含前 200 字）；不記 done，下一輪再試
        file_days = sorted(set(t.loc[t["time"].between(DAY_FROM, DAY_TO), "date"]))
        if file_days and file_days != [day.replace("-", "")]:
            log.warning("期交所逐筆 %s：檔內日盤的成交日期是 %s，跟檔名不同；照檔內日期", day, file_days)
        frames.append(t)
    if not frames:
        save_state(st)
        return pd.DataFrame()

    ticks = pd.concat(frames, ignore_index=True)
    walled = attach_wall_time(ticks, known_days)
    raw_day = {}
    if not walled.empty:
        dd = walled[walled["session"] == "day"]
        for od, g in dd.groupby("open_day"):
            near = _near_month(g)
            if near is not None:
                raw_day[od] = float(g.loc[g["month"] == near, "qty"].sum())
    div = vol_divisor(raw_day, official_vol or {})
    bars = ticks_to_1m(walled, divisor=div)
    stamp = now.isoformat(timespec="seconds")
    for f, g in ticks.groupby("file"):
        st["done"][f] = {"ticks": int(len(g)), "at": stamp}
    save_state(st)
    if not bars.empty:
        by = bars.groupby("symbol")["ts"].agg(lambda s: f"{str(s.min())[:10]}～{str(s.max())[:10]}")
        log.info("期交所逐筆 → 1 分 K：%d 根（%s；÷%g）", len(bars), "、".join(f"{k} {v}" for k, v in by.items()), div)
    return bars
