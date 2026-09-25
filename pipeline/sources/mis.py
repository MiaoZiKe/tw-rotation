"""證交所「基本市況報導」即時報價（`mis.twse.com.tw`）。

為什麼要這一支
--------------
`openapi.twse.com.tw` 的 `STOCK_DAY_ALL` 落後一個交易日。2026-09-14（週一）實測：
收盤後一小時（14:32）它回的還是 **09-11**；到 15:09 也一樣。
而同一時間 `mis` 已經有 **當天（20260914）** 的資料。
這就是 Andy 講的「我盤後才看到，等到隔天才買」的根源。

所以台北 15:30 那一輪（`--phase price`）改成：openapi 先抓（拿得到就用官方的），
拿不到當天就用 mis 把當天補起來，網站當天下午就看得到今天。

端點特性（2026-09-14 實測）
---------------------------
- 一個請求最多可帶很多代號，實測 **120 檔、120ms** 一次回全；上市 `tse_` 與上櫃
  `otc_` 可以混在同一個請求；`tse_t00.tw` 是加權指數。
- 回應是 `{"rtcode":"0000","msgArray":[...]}`，每一列的欄位：
  `c` 代號、`n` 簡稱、`ex` tse/otc、`d` 資料日期（西元 YYYYMMDD）、`t` 最後成交時間、
  `o` 開、`h` 高、`l` 低、`z` 成交價、`y` 昨收、`v` 累計成交張數、`tv` 最後一筆張數、
  `u` 漲停、`w` 跌停、`a`/`b` 五檔委賣／委買。
- 沒有成交時 `z` 會是 `-`，要退到最佳買價再退到昨收。

★ 成交量的口徑差異（一定要知道）
--------------------------------
`v` 是 **盤中（09:00–13:30）累計成交張數，不含盤後定價交易與鉅額**。
2026-09-14 收盤後拿 mis 與 FinMind（官方口徑）逐檔比對：

| 代號 | mis `v`（張） | 官方（張） | 差 |
|---|---:|---:|---:|
| 1101 台泥 | 35,582 | 35,779 | −0.55% |
| 6488 環球晶 | 3,954 | 4,180 | −5.4% |
| 2330 台積電 | 18,172 | 21,449 | **−15.3%** |

**差幅逐檔不同**，所以不能當成一致的縮放。開高低收則是**完全吻合**
（2330 開 2385／高 2395／低 2380／收 2380 三個來源一字不差）。

因此這支的契約是：
- **開高低收可以直接採用**
- **成交量與成交值是暫定值**，列上會標 `px_source="mis"`，
  等 openapi 隔天給出官方值時由 `store.append()` 覆蓋掉（後到覆蓋）
- 成交值沒有現成欄位，用「張數 × 1000 × 典型價 (高+低+收)/3」估算。
  這個估算本身很準（1101 誤差 −0.3%），誤差幾乎都來自上面那個量的口徑差。
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, is_tradable_security, to_float, to_int

log = logging.getLogger(__name__)

# 一個請求帶幾檔。實測 120 檔沒問題，留一點邊際。
BATCH = 100

# 指數不是股票，不進 price_daily
INDEX_CODES = {"t00", "t001", "o00"}


def _ex_ch(code: str, market: str | None) -> str:
    """代號 → mis 的 ex_ch。市場別不明就當上市（回應裡沒有就是沒有，不會出錯）。"""
    prefix = "otc" if (market or "").upper() in ("TPEX", "OTC") else "tse"
    return f"{prefix}_{code}.tw"


def _price_of(row: dict) -> float | None:
    """成交價。沒成交時 `z` 是 '-'，退到最佳買價第一檔，再退到昨收。"""
    z = to_float(row.get("z"))
    if z is not None:
        return z
    bids = str(row.get("b") or "").split("_")
    b = to_float(bids[0]) if bids and bids[0] else None
    if b is not None:
        return b
    return to_float(row.get("y"))


def quotes(pairs: list[tuple[str, str | None]]) -> list[dict]:
    """抓一批報價。`pairs` 是 (代號, 市場別) 的清單，市場別可以是 None。

    分批送，任何一批失敗只記 log 並繼續 —— 少幾檔比整輪掛掉好。
    """
    out: list[dict] = []
    for i in range(0, len(pairs), BATCH):
        chunk = pairs[i:i + BATCH]
        ex = "|".join(_ex_ch(c, m) for c, m in chunk)
        data = http.get(config.MIS_QUOTE, params={"json": "1", "delay": "0", "ex_ch": ex})
        if not isinstance(data, dict):
            log.warning("mis 第 %d 批沒有回應（%d 檔）", i // BATCH + 1, len(chunk))
            continue
        if str(data.get("rtcode")) != "0000":
            log.warning("mis 第 %d 批 rtcode=%s（%s）", i // BATCH + 1,
                        data.get("rtcode"), str(data.get("rtmessage"))[:60])
            continue
        rows = data.get("msgArray") or []
        out.extend(rows)
        log.info("mis 第 %d 批：要 %d 檔、回 %d 檔", i // BATCH + 1, len(chunk), len(rows))
    return out


def price_snapshot(pairs: list[tuple[str, str | None]]) -> pd.DataFrame:
    """把 mis 的報價整理成 `price_daily` 的形狀。

    日期一律取自回應裡的 `d`，不用執行當下的日期 ——
    非交易日打這支會回上一個交易日的資料而且不標示。
    """
    if not pairs:
        return pd.DataFrame()
    raw = quotes(pairs)
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(r.get("c"))
        if not code or code in INDEX_CODES or not is_tradable_security(code):
            continue
        d = str(r.get("d") or "").strip()
        if len(d) != 8 or not d.isdigit():
            continue
        date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        close = _price_of(r)
        high, low = to_float(r.get("h")), to_float(r.get("l"))
        prev = to_float(r.get("y"))
        lots = to_int(r.get("v"))
        shares = lots * 1000 if lots is not None else None
        # 典型價 (高+低+收)/3；缺高低就退回收盤價
        ref = [x for x in (high, low, close) if x is not None]
        typical = sum(ref) / len(ref) if ref else None
        rows.append({
            "date": date,
            "code": code,
            "name": r.get("n"),
            "market": "TPEX" if str(r.get("ex")).lower() == "otc" else "TWSE",
            "open": to_float(r.get("o")),
            "high": high,
            "low": low,
            "close": close,
            "change": (close - prev) if (close is not None and prev is not None) else None,
            "volume": shares,                                   # 股（盤中累計，見模組說明）
            "turnover": (shares * typical) if (shares is not None and typical) else None,
            "transactions": None,                               # mis 沒有這個欄位
            # ★ 標記這一列是暫定值：量與值是盤中口徑，隔天會被 openapi 的官方值覆蓋
            "px_source": "mis",
        })

    df = pd.DataFrame(rows)
    if df.empty:
        log.warning("mis 有 %d 列但一列都整理不出來", len(raw))
    else:
        log.info("mis 快照：%d 檔，資料日期 %s（成交量是盤中口徑，暫定值）",
                 len(df), df["date"].iloc[0])
    return df


def market_snapshot() -> pd.DataFrame:
    """`market_daily` 的當天暫定值（加權指數、漲跌點數、成交金額、成交量）。

    為什麼要另外抓一支
    ------------------
    `price_daily` 用 mis 補上今天之後，網站頂端的「資料更新到」就會寫今天，
    但**加權指數那格還是昨天的數字** —— 因為它來自 `market_daily`（證交所 FMTQIK），
    而 FMTQIK 跟日收檔一樣落後一個交易日。兩個數字擺在同一個畫面上就是明顯的矛盾
    （2026-09-14 實測：橫幅寫 09-14、加權指數卻是 09-11 收的 46,184.85）。

    這支拿的是「基本市況報導」那張加權走勢圖自己在用的檔，`infoArray[0]` 直接給：
        z 成交指數、y 昨收、o/h/l 開高低、d 日期、v 成交金額（百萬元）、m 成交量（張）
    2026-09-14 17:30 實測：z=45862.52、y=46184.85、v=630917、m=8705759，
    與 `staticObj.tz`（630,917,830,610 元）、`staticObj.tv` 對得上。

    口徑注意：成交金額與成交量跟 `price_snapshot()` 一樣是**盤中累計**，
    不含盤後定價交易，所以偏低；隔天 FMTQIK 給出官方值時由 `store.append()` 覆蓋。
    """
    # 帶 Referer：getStockInfo.jsp 不帶也通，但這支是網頁自己在讀的靜態檔，
    # 帶著跟瀏覽器一樣的來源比較不會被當成爬蟲擋掉（Worker 那邊也是這樣送的）。
    data = http.get(config.MIS_CHART_TSE,
                    headers={"Referer": "https://mis.twse.com.tw/stock/index.jsp"})
    if not isinstance(data, dict):
        log.warning("mis 大盤分時沒有回應")
        return pd.DataFrame()
    info = (data.get("infoArray") or [{}])[0]
    d = str(info.get("d") or "").strip()
    if not (len(d) == 8 and d.isdigit()):
        log.warning("mis 大盤分時沒有可用的日期：%r", d)
        return pd.DataFrame()
    close, prev = to_float(info.get("z")), to_float(info.get("y"))
    if close is None:
        log.warning("mis 大盤分時沒有成交指數")
        return pd.DataFrame()
    turnover = to_float(info.get("v"))          # 百萬元
    volume = to_int(info.get("m"))              # 張
    row = {
        "date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
        "taiex": close,
        "change": None if prev is None else round(close - prev, 2),
        # market_daily 的 turnover 是「元」（FMTQIK 給的 TradeValue），這裡要換算回去
        "turnover": None if turnover is None else turnover * 1_000_000,
        # 同樣對齊 FMTQIK：volume 是「股」
        "volume": None if volume is None else volume * 1000,
        "transactions": None,
        "px_source": "mis",
    }
    log.info("mis 大盤：%s 加權 %.2f（昨收 %s）", row["date"], close, prev)
    return pd.DataFrame([row])


def latest_date(sample: tuple[str, str | None] = ("2330", "TWSE")) -> str | None:
    """只問一檔，拿 mis 現在手上是哪一個交易日。用來決定要不要補。"""
    raw = quotes([sample])
    if not raw:
        return None
    d = str(raw[0].get("d") or "").strip()
    return f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 and d.isdigit() else None


# ------------------------------------------------------------------ 大盤三張圖的 1 分 K（2026-09-26）
# Andy 2026-09-26：「加權 櫃買 台指期，這三個到底有沒有統一的來源，不是一個有一個沒有」。
# 當天的分時三張本來就同一個來源（這三個檔，DECISIONS #121）；多日分 K 卻只有加權有（Yahoo ^TWII），
# 櫃買 ^TWOII 回空、台指期沒有 Yahoo 代號、FinMind 分 K 要付費等級。
# 解法：每個交易日盤後把這三個檔存成 1 分 K 進資料湖，三個指數同一個來源、同一套邏輯自己累積。
# 代價：過去的補不回來 —— 櫃買、台指期的多日分 K 從第一個抓到的交易日開始長。
#
# 檔案格式（2026-09-14 17:30 實測，fixture：docs/fixtures/mis_ohlc_tse_20260914.json）：
#   TSE／OTC：ohlcArray 每分鐘一筆 {t: epoch 毫秒, ts: "090100", c: 指數, s: 該分鐘成交張數}，09:01～13:33
#   FUT     ：同上但**沒有 ts**，08:46～13:45，s 是口數；證交所這個檔**只有日盤**
#   infoArray[0]：d 日期（YYYYMMDD）、o/h/l/z 開高低收、y 昨收；staticObj.tv 累計張數
# 每筆只有「那一分鐘的收盤」，沒有分鐘的高低 —— 所以 1 分 K 是合成的：
#   開＝前一分鐘的收盤（第一根用 infoArray 的開盤），高低＝開收兩者的極值（跟前端 toBars 同一個口徑）。

CHART_TZ = "Asia/Taipei"
# 量的單位跟 index_ohlc 對齊：指數存「股」（張 × 1000），台指期存「口」。前端 volUnit() 同一個口徑。
CHART_VOL_UNIT = {"TSE": 1000, "OTC": 1000, "FUT": 1}
# 每個檔「合理的」時間窗（台北牆鐘分鐘數）。落在窗外的點丟掉；超過 5% 落在窗外就整檔不收 ——
# 那代表時間戳的語意變了（例如某天 t 改成台北時間的 epoch），寫進只增不改的資料湖就再也洗不掉。
CHART_WINDOW = {"TSE": (8 * 60 + 55, 13 * 60 + 40), "OTC": (8 * 60 + 55, 13 * 60 + 40),
                "FUT": (8 * 60 + 40, 13 * 60 + 50)}
CHART_BAD_RATIO = 0.05
CHART_REFERER = "https://mis.twse.com.tw/stock/index.jsp"


def _head(x) -> str:
    """回應前 200 字（上游改格式時，下一個人靠這一段才修得動）。"""
    try:
        t = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    except (TypeError, ValueError):
        t = str(x)
    return t[:200]


def parse_index_chart(symbol: str, payload) -> pd.DataFrame:
    """一個分時檔（原始文字或已解析的 dict）→ 1 分 K 長表。失敗回空並記 log（含回應前 200 字）。

    欄位：ts（台北時間 ISO，帶 +08:00）, symbol, interval="1m", open, high, low, close, volume, src="mis"。

    ★ 交易日取自檔案內容（每一筆的 epoch `t`），不是執行當下的日期。
      週末或隔天清晨打這支，拿到的是上一個交易日的殘留 —— 照 `t` 歸日，自然落在正確那天；
      重複抓同一天由 `store.append()` 依 (ts, symbol, interval) 去重，不會多一列。
    """
    empty = pd.DataFrame()
    unit = CHART_VOL_UNIT.get(symbol, 1)
    data = payload
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")
    if isinstance(data, str):
        try:
            data = json.loads(data.lstrip("﻿"))
        except ValueError:
            log.warning("mis 分時 %s 不是 JSON（回應前 200 字）：%s", symbol, _head(payload))
            return empty
    if not isinstance(data, dict):
        log.warning("mis 分時 %s 形狀不對（回應前 200 字）：%s", symbol, _head(payload))
        return empty
    rt = data.get("rtcode")
    if rt is not None and str(rt) != "0000":
        log.warning("mis 分時 %s rtcode=%s（回應前 200 字）：%s", symbol, rt, _head(data))
        return empty
    arr = data.get("ohlcArray")
    if not isinstance(arr, list):
        log.warning("mis 分時 %s 沒有 ohlcArray（回應前 200 字）：%s", symbol, _head(data))
        return empty
    infos = data.get("infoArray")
    info = infos[0] if isinstance(infos, list) and infos and isinstance(infos[0], dict) else {}

    lo, hi = CHART_WINDOW.get(symbol, (0, 24 * 60))
    pts, bad, out_win, label_miss = [], 0, 0, 0
    for o in arr:
        if not isinstance(o, dict):
            bad += 1
            continue
        try:
            ms = int(float(o.get("t")))
        except (TypeError, ValueError):
            bad += 1
            continue
        c = to_float(o.get("c"))
        if c is None or c <= 0:
            bad += 1
            continue
        s = to_float(o.get("s"))
        wall = pd.Timestamp(ms, unit="ms", tz="UTC").tz_convert(CHART_TZ).floor("min")
        # TSE／OTC 另外有 "090100" 這種時間標籤：跟 epoch 換算出來的對不上，就是時間戳語意變了
        lab = str(o.get("ts") or "").strip()
        if len(lab) >= 4 and lab[:4].isdigit() and lab[:4] != wall.strftime("%H%M"):
            label_miss += 1
            continue
        minute = wall.hour * 60 + wall.minute
        if not (lo <= minute <= hi):
            out_win += 1
            continue
        pts.append((wall, c, max(0.0, s) if s is not None else 0.0))
    n_all = len(arr)
    if n_all and (label_miss + out_win) > n_all * CHART_BAD_RATIO:
        log.warning("mis 分時 %s：%d 筆裡 %d 筆時間標籤對不上、%d 筆落在交易時段外，判定格式變了、整檔不收"
                    "（回應前 200 字）：%s", symbol, n_all, label_miss, out_win, _head(data))
        return empty
    if not pts:
        log.warning("mis 分時 %s 一筆都解析不出來（%d 筆；回應前 200 字）：%s", symbol, n_all, _head(data))
        return empty
    if bad or label_miss or out_win:
        log.info("mis 分時 %s：丟掉 %d 筆壞值、%d 筆標籤不符、%d 筆時段外", symbol, bad, label_miss, out_win)

    df = (pd.DataFrame(pts, columns=["wall", "close", "s"])
          .sort_values("wall", kind="stable").drop_duplicates("wall", keep="last"))
    df["date"] = df["wall"].dt.strftime("%Y%m%d")

    info_d = str(info.get("d") or "").strip()
    info_d = info_d if (len(info_d) == 8 and info_d.isdigit()) else ""
    days = sorted(df["date"].unique())
    if info_d and days != [info_d]:
        # 不擋：每一筆的 epoch 才是那一筆自己的時間（上面已用時間標籤與時段驗過）。只記下來備查。
        log.warning("mis 分時 %s：infoArray 日期 %s 與分時點的日期 %s 不一致，照分時點歸日", symbol, info_d, days)
    try:
        total = float(str((data.get("staticObj") or {}).get("tv") or "").replace(",", ""))
    except ValueError:
        total = None

    rows = []
    for day, g in df.groupby("date", sort=True):
        s = g["s"].astype(float).reset_index(drop=True)
        # 防呆：s 應該是「該分鐘」的量。萬一哪天變成累計量（單調不減、最後一筆≈全日總量、加總遠大於總量），
        # 照舊加總會把量放大上百倍 —— 改成差分並記 log。
        if (total and day == info_d and len(s) > 10 and s.is_monotonic_increasing
                and s.sum() > 1.5 * total and abs(s.iloc[-1] - total) <= 0.05 * total):
            log.warning("mis 分時 %s %s：s 看起來是累計量（最後 %s ≈ 總量 %s），改用差分",
                        symbol, day, s.iloc[-1], total)
            s = s.diff().fillna(s.iloc[0]).clip(lower=0)
        closes = g["close"].astype(float).tolist()
        # 第一根的開盤用 infoArray 的開盤（那是真的開盤價）；日期對不上或離譜（差 10% 以上）就用第一筆收盤
        first_open = to_float(info.get("o")) if day == info_d else None
        if first_open is None or first_open <= 0 or abs(first_open / closes[0] - 1) > 0.1:
            first_open = closes[0]
        prev = first_open
        for w, c, v in zip(g["wall"], closes, s):
            o = prev
            rows.append({"ts": w.isoformat(), "symbol": symbol, "interval": "1m",
                         "open": o, "high": max(o, c), "low": min(o, c), "close": c,
                         "volume": float(v) * unit, "src": "mis"})
            prev = c
    out = pd.DataFrame(rows)
    log.info("mis 分時 %s：%d 根 1 分 K，交易日 %s", symbol, len(out), "、".join(days))
    return out


def index_minute_bars(symbols: list[str] | None = None) -> pd.DataFrame:
    """抓加權／櫃買／台指期三個當日分時檔 → 1 分 K（進 `index_intraday`，interval="1m"）。

    一個檔失敗只記 log、其他照收；三個都失敗回空。不耗 FinMind 額度，一次三個小請求。
    """
    frames = []
    for sym, url in config.MIS_CHART_FILES.items():
        if symbols and sym not in symbols:
            continue
        try:
            text = http.get(url, headers={"Referer": CHART_REFERER}, expect_json=False)
        except Exception as exc:  # noqa: BLE001 —— 單一來源掛掉不能讓整條管線死
            log.warning("mis 分時 %s 抓取失敗：%s", sym, exc)
            continue
        if not text:
            log.warning("mis 分時 %s 沒有回應", sym)
            continue
        try:
            df = parse_index_chart(sym, text)
        except Exception as exc:  # noqa: BLE001
            log.warning("mis 分時 %s 解析失敗：%s（回應前 200 字）：%s", sym, exc, _head(text))
            continue
        if not df.empty:
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
