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
