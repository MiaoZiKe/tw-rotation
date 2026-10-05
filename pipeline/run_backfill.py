"""歷史回補。

這是整個專案最有時效性的一件事：開放資料只有當日快照，每晚一天開始存檔，
就永久少一天歷史。FinMind 免費層是目前唯一能一次補回十年的免費途徑。

設計成可以重複執行：
- 已經補過的股票會被跳過（依資料湖裡既有的最早日期判斷）
- 額度用盡就停下並寫進度檔，下一輪從沒補到的地方接續
- 中途被 CI timeout 砍掉，已寫入的部分不會丟失
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from . import config
from .groups import loader
from .sources import finmind
from .util import http, roc, store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backfill")

PROGRESS = config.STATE / "backfill_progress.json"

# 各資料集鍵（--datasets 用的名字）；summary 與 main() 的合計都照這張表
DATA_KEYS = ("price", "inst", "per", "revenue", "financial", "balance",
             "dividend", "divresult", "margin", "holding", "daytrade", "sbl")

# ETF / 指數型商品沒有財報、月營收、本益比、股利公告可抓（ETF 其實有配息，先不抓），
# 逐檔去問只是在燒額度；融資券與股權分散 ETF 有，要抓
FINANCIAL_KEYS = {"per", "revenue", "financial", "balance", "dividend", "divresult"}

# 逐檔 done 鍵的值（2026-09-28）：True＝抓到資料寫進資料湖；NO_DATA＝額度還在、上游明確回空，
# 「確認這檔沒有這種資料」（新掛牌、從沒配過股利…）。兩者對「要不要再問」的判斷一樣（都是真值、
# 都跳過），但對「補到多少」的統計不一樣 —— 以前一律寫 True，done 區的鍵數看起來全都是
# 「補到了」，無從分辨哪些其實是空的。舊進度檔裡既有的 True 無法回溯區分，只從這版開始分。
NO_DATA = "no_data"

# 回補資料集鍵 → FinMind 的 dataset 名稱（2026-10-03，DECISIONS #311）。
# 封印理由要拿「**這個**資料集自己」最近一次的錯誤（http.finmind_last_error(dataset)），
# 不能拿全域最後一次 —— 那可能是上一個資料集撞到的 402，會把封印理由寫錯。
FINMIND_DATASET = {
    "price": "TaiwanStockPrice", "inst": "TaiwanStockInstitutionalInvestorsBuySell",
    "per": "TaiwanStockPER", "revenue": "TaiwanStockMonthRevenue",
    "financial": "TaiwanStockFinancialStatements", "balance": "TaiwanStockBalanceSheet",
    "dividend": "TaiwanStockDividend", "divresult": "TaiwanStockDividendResult",
    "margin": "TaiwanStockMarginPurchaseShortSale", "holding": "TaiwanStockHoldingSharesPer",
    "daytrade": "TaiwanStockDayTrading", "sbl": "TaiwanDailyShortSaleBalances",
}

# 排程用的預設回補計畫：依序執行，某一步額度用盡就停下，下一小時從那一步接續。
# scope=universe → target_codes(limit)（**會吃 --limit**：手動觸發預設 500 時只剩成交值前 500 檔）；
# scope=market   → market_codes()：全市場上市＋上櫃普通股，**刻意不吃 --limit**（見 market_codes 說明）；
# scope=groups   → 只補 groups.yaml 的成分股。
PLAN_DEFAULT = [
    {"datasets": "revenue+financial+balance", "start": "2016-01-01", "scope": "universe"},
    {"datasets": "dividend+divresult",        "start": "2016-01-01", "scope": "universe"},
    {"datasets": "margin+holding",            "start": "2021-01-01", "scope": "universe"},
    {"datasets": "price",                     "start": "2000-01-01", "scope": "groups"},
    # ★ 2026-09-27（個股頁數據普查）：三大法人**從來不在計畫裡**。每日管線只補成交值前 500 檔
    #   （run_daily.fetch_institutional，UNIVERSE_SIZE），更早的一次性回補也只跑到 401 檔 ——
    #   實測 1,980 檔普通股裡 1,626 檔的 inst_daily 一列都沒有，個股頁「三大法人」整張不出現。
    #   一檔一次請求（FinMind TaiwanStockInstitutionalInvestorsBuySell，免費層可用）。
    #   補完之後的每日更新見 refresh_stale_inst()。
    # ★ 2026-09-28（CEO 查證）：這三步原本寫 scope=universe，而那幾輪是手動觸發（limit 預設 500），
    #   target_codes(500) 只給成交值前 500 檔 —— 三步都標成 done，資料湖實測卻只有
    #   inst_daily 781 檔、daytrade_daily 498 檔，前 500 名以外的個股頁照樣空白。
    #   改成 scope=market（全市場普通股、不吃 limit），完成旗標換成新鍵
    #   「inst@market」等（datasets_key_of 的 scope 參數），舊的 universe 旗標擋不住新步驟；
    #   逐檔的 done 鍵（inst:2330、daytrade@2025-01-01:2330…）跟以前**同一個格式**，
    #   所以前 500 檔已補過的不會重抓一次。
    {"datasets": "inst",                      "start": "2016-01-01", "scope": "market"},
    # ★ 2026-09-27：當沖與借券賣出（籌碼分頁照 Andy 的券商 App 截圖補）。只補到 2025 年起 ——
    #   籌碼分頁最長看 1 年（約 250 個交易日），更早的用不到；一檔一次請求 × 兩個資料集。
    {"datasets": "daytrade+sbl",              "start": "2025-01-01", "scope": "market"},
    # ★ 2026-09-27（Andy：「除權息時間軸往前拉到 2009」）：股利公告與除權息結果再往前補 2009～2015。
    #   done 鍵是「dividend@2009-01-01:<代號>」，build_payload.dividend_cover_years 看這個鍵決定年度圖從哪年畫起。
    {"datasets": "dividend+divresult",        "start": "2009-01-01", "scope": "market"},
    # ★ 2026-10-04（Andy 截圖：自選頁 4561 健椿 2018 年上櫃，K 線只有 15 根）：價量是唯一還沒有
    #   全市場版的資料集。上面那一步 price@2000-01-01 是 scope=groups，只涵蓋族群成分股（約 445 檔）；
    #   其餘約 1,760 檔的 price_daily 只有每日管線（openapi）累積的最近十幾個交易日，
    #   個股頁因此掉成「簡版頁」。逐檔 done 鍵與 groups 那一步**同一個格式**（price@2000-01-01:<代號>），
    #   所以已補過完整歷史的那幾百檔直接跳過，不會重抓。一檔一次請求（TaiwanStockPrice 一次回整段歷史）。
    #   放在最後：前面幾步都已補齊（2026-10-04 進度檔實測），不跟它們搶額度。
    #   build_payload 不必改：個股頁的名單是「日線 ≥ MIN_PAGE_BARS」就升成完整頁，
    #   還原價（adjust_prices）吃整張 price_daily，更舊的部分自動寫進 data/hist 分頁 —— 補進來就吃得到。
    {"datasets": "price",                     "start": "2000-01-01", "scope": "market"},
    # ★ 2026-10-05（ETF 專區）：上面每一步的名單都濾成「普通股」（is_common_stock 排除 00 開頭），
    #   所以 ETF 從來沒有配息紀錄、價量也只有族群步驟碰巧涵蓋的 37 檔有長歷史（實測 2026-10-05：
    #   dividend_events 裡 ETF 0 列、price_daily 240 檔 ETF 只有 37 檔超過 200 根）。
    #   ETF 專區的配息行事曆、殖利率、3/5/10 年報酬全部要靠這兩步。
    #   ⚠ 已知疑點：2016 那一步（universe）曾把 dividend:0050、dividend:0056 標成 done，湖裡卻 0 列。
    #   可能是 FinMind 當時對 ETF 回空、或那幾輪資料集被封印。這裡用新的逐檔鍵（@2009-01-01）重問一次；
    #   若仍回空，前端照樣標「配息資料尚未取得」，不會拿 0 冒充（compute/etf.div_done 只認湖裡真的有列）。
    #   ETF 約 270 檔 × 3 次請求 ≈ 810 次 ≈ 2 輪。逐檔 done 鍵與既有步驟同格式，族群步驟補過的不重抓。
    {"datasets": "dividend+divresult",        "start": "2009-01-01", "scope": "etf"},
    {"datasets": "price",                     "start": "2000-01-01", "scope": "etf"},
]
# 請求數估算（2026-09-28 以資料湖實測：market_codes() 1,980 檔，扣掉已有逐檔 done 鍵／已補到起始日的；
# FinMind 一檔一資料集一次請求，每小時可用約 510 次）：
#   inst               1,314 次
#   daytrade+sbl       1,507 × 2 ＝ 3,014 次
#   dividend+divresult 1,507 × 2 ＝ 3,014 次
#   合計 ≈ 7,340 次 ÷ 510 ≈ 15 輪。排程每天 22 輪（避開每日管線那兩小時），約 15～18 小時補完。
#   補完之前每一輪都會撞到額度上限而停在這幾步，refresh_stale_inst 的每日續補要等補完才開始跑。
# 2026-10-04 全市場日線（price@2000-01-01@market）：market_codes() 1,980 檔，扣掉已有 done 鍵的
#   實測剩 1,513 檔 × 1 次 ≈ 1,513 次 ÷ 每輪約 450～500 次（扣健檢與每日續補）≈ 4 輪，約 4～5 小時。
PLANS = {"default": PLAN_DEFAULT}
TAIPEI = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- 資料集封印
# 2026-09-19 的事故：revenue / financial / balance 連續好幾輪整組回空，
# 判定「資料集不開放」的邏輯只活在那一輪的記憶體裡、沒有寫進進度檔，
# 於是**每一輪都重問全部 506 檔**、每一輪都把額度燒光，
# 計畫永遠停在第 1 步，後面幾千檔個股的價量與法人永遠輪不到。
#
# 修法是「封印 ＋ 定期探測」：判定不開放就寫進進度檔並記時間戳，
# 之後每天最多重問一次，而且重問只拿少量樣本去探，探到通了才恢復全量。
# 刻意不做成「永遠不再問」—— 資料集有可能之後就開放了（或只是上游暫時壞掉），
# 那樣會永遠補不到。
UNAVAILABLE_RETRY_HOURS = 24   # 封印後至少隔這麼久才准再探一次
PROBE_CODES = 5                # 解封探測一輪最多問幾檔（夠過「3 檔以上」的判定門檻）
EMPTY_STREAK_LIMIT = 20        # 同一個資料集在一輪內連續回空幾檔就先收手

# ★ 2026-10-03 誤封印事故（daytrade／sbl，DECISIONS #304）：
#   「這一輪問到的每一檔都回空」不等於「資料集不開放」—— 要看問的是哪些股票。
#   每日續補挑的是「落後最久」的股票，而落後最久的正好是**早就沒有當沖／借券資料**的那幾十檔
#   （不能當沖的處置股、借券標的被拿掉的…，最後一筆停在 2025 年），於是 20 檔全空 → 封印；
#   之後每 24 小時的探測又拿名單最前面那 5 檔（還是同一批）去問 → 永遠探不通。
#   修法：封印前先拿 CANARY_CODE（台積電）問同一個區間當反證 —— 台積電有資料就代表資料集是通的，
#   那些回空的是真的沒資料；而且區間內根本沒有交易日（連假）時一律不判定。
#   已經用「整組回空」理由封印的，每 SEAL_CANARY_RETRY_HOURS 小時也拿台積電驗一次，驗通就當場解封。
SEAL_CANARY_RETRY_HOURS = 24

# 健檢用的標的：台積電最近幾天的日線 —— FinMind 免費層一定有的東西。
# 連它都拿不到就不是「某個資料集不開放」，是整把 token／帳號的問題。
CANARY_CODE = "2330"
CANARY_DAYS = 10


def _progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except ValueError:
            pass
    return {"done": {}, "updated_at": None}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value) -> datetime | None:
    try:
        ts = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def dataset_mode(prog: dict, key: str, now: datetime | None = None) -> str:
    """這一輪要怎麼對待這個資料集。

    full   —— 正常全量跑（沒有被封印，或剛剛探測成功）
    probe  —— 封印超過 UNAVAILABLE_RETRY_HOURS，這一輪只拿 PROBE_CODES 檔去探
    sealed —— 還在封印期內，這一輪一次請求都不發（額度留給補得動的步驟）
    """
    rec = (prog.get("unavailable") or {}).get(key)
    if not isinstance(rec, dict):
        return "full"
    ts = _parse_ts(rec.get("last_probe") or rec.get("since"))
    if ts is None:
        return "probe"
    hours = ((now or _now()) - ts).total_seconds() / 3600
    return "probe" if hours >= UNAVAILABLE_RETRY_HOURS else "sealed"


def seal_dataset(prog: dict, key: str, reason: str = "") -> bool:
    """把資料集記成「不開放」。回傳 True 代表這是第一次判定（先前沒有紀錄）。"""
    book = prog.setdefault("unavailable", {})
    rec = book.get(key)
    first = not isinstance(rec, dict)
    now = _now().isoformat()
    if first:
        rec = {"since": now, "probes": 0}
    rec["last_probe"] = now
    rec["probes"] = int(rec.get("probes") or 0) + 1
    if reason:
        rec["last_reason"] = reason[:200]
    book[key] = rec
    return first


def unseal_dataset(prog: dict, key: str) -> None:
    """探測拿到資料了 —— 解除封印，下一輪恢復全量。"""
    book = prog.get("unavailable") or {}
    if key in book:
        book.pop(key, None)
        log.info("%s 又拿得到資料了 —— 解除封印，恢復全量回補", key)


def no_trading_day_since(start: str) -> bool:
    """price_daily 裡完全沒有 >= start 的交易日 → True（這段區間問什麼都會是空的，不能拿來判定封印）。

    用資料湖裡的日期判斷，不用執行當下的日期（連假、颱風假都自然涵蓋）。
    price_daily 是空的（測試沙盒、剛建湖）→ 不知道 → False，交給其他判準。"""
    if "price_daily" not in _cov_cache:
        _cov_cache["price_daily"] = store.read("price_daily")
    px = _cov_cache["price_daily"]
    if px is None or px.empty or "date" not in px.columns:
        return False
    return str(px["date"].astype(str).max()) < str(start)[:10]


def _save_progress(p: dict) -> None:
    p["updated_at"] = datetime.now(timezone.utc).isoformat()
    PROGRESS.write_text(json.dumps(p, ensure_ascii=False, indent=2))


def target_codes(limit: int | None) -> list[str]:
    """回補優先順序：先是 groups.yaml 裡的族群成分股（這些一定要有歷史），
    再依近期成交值補其他流動性好的標的。"""
    picks: list[str] = []

    m = loader.membership()
    if not m.empty:
        picks.extend(dict.fromkeys(m["code"].tolist()))

    price = store.read("price_daily")
    if not price.empty:
        latest = price["date"].max()
        recent = price[price["date"] == latest]
        by_turnover = (recent.groupby("code")["turnover"].sum()
                             .sort_values(ascending=False).index.tolist())
        for c in by_turnover:
            if c not in picks:
                picks.append(c)
    else:
        # 資料湖全空（第一次跑）就用 FinMind 的股票總覽當來源
        info = finmind.stock_info()
        if not info.empty:
            for c in info["code"]:
                if c not in picks:
                    picks.append(c)

    return picks[:limit] if limit else picks


MARKET_RECENT_DAYS = 30   # 全市場名單只收最近 30 天內還有成交紀錄的股票（下市股不再花額度）
MARKET_OK = {"TWSE", "TPEX"}   # company_info 的市場別；興櫃（EMERGING）沒有法人／當沖／除權息可補


def market_codes() -> list[str]:
    """全市場上市＋上櫃普通股（2026-09-28，scope="market"）。

    範圍以「個股頁會出現的股票」為準：build_payload 的個股頁名單取自 price_daily，
    所以這裡也從 price_daily 取，再濾成普通股（roc.is_common_stock：4 位數字、不以 0 開頭 ——
    排除 ETF、權證、特別股 2881A、存託憑證 91xxxx）。company_info 有市場別時只收上市／上櫃。
    只收最近 MARKET_RECENT_DAYS 天內有成交的（用資料裡的日期，不用執行當下的日期）。
    順序：最新交易日成交值由大到小，其餘（當天停牌）接在後面 —— 額度中途用完時先補到的是熱門股。

    ★ 刻意**不吃 --limit**：limit 是給手動觸發試跑用的，這一步的目的就是「全市場」，
      被 limit 砍掉就是 2026-09-28 那個 bug 本身。真正的節流閥是 FinMind 額度（402 即停、下一輪接續）。
    資料湖全空（第一次跑）時退回 FinMind 股票總覽。"""
    from .util.roc import is_common_stock

    info = store.read("company_info")
    market_of: dict[str, str] = {}
    if not info.empty and {"code", "market"} <= set(info.columns):
        mk = info.dropna(subset=["market"]).assign(code=lambda d: d["code"].astype(str))
        market_of = mk.drop_duplicates("code", keep="last").set_index("code")["market"].astype(str).to_dict()

    def ok(c: str) -> bool:
        return is_common_stock(c) and market_of.get(c, "TWSE") in MARKET_OK

    price = store.read("price_daily")
    if price.empty:
        fm = finmind.stock_info()
        if fm.empty:
            return []
        return list(dict.fromkeys(c for c in fm["code"].astype(str) if ok(c)))
    px = price.assign(code=price["code"].astype(str), date=price["date"].astype(str))
    latest = px["date"].max()
    since = (pd.Timestamp(latest) - pd.Timedelta(days=MARKET_RECENT_DAYS)).date().isoformat()
    recent = px[px["date"] >= since]
    day = recent[recent["date"] == latest]
    tv = day["turnover"] if "turnover" in day.columns else pd.Series(0.0, index=day.index)
    by_turnover = (day.assign(_tv=pd.to_numeric(tv, errors="coerce").fillna(0.0))
                      .groupby("code")["_tv"].sum().sort_values(ascending=False).index.tolist())
    out = [c for c in by_turnover if ok(c)]
    seen = set(out)
    out += sorted(c for c in recent["code"].unique() if c not in seen and ok(c))
    return out


_cov_cache: dict[str, pd.DataFrame] = {}


def etf_codes() -> list[str]:
    """上市＋上櫃 ETF（2026-10-05，scope="etf"，ETF 專區用）。

    判準跟 compute/etf.etf_universe 同一套：company_info 的產業別是 ETF，或代號 00 開頭、
    不是普通股（00 開頭的只有 ETF／ETN 與受益證券）。只收最近 MARKET_RECENT_DAYS 天有成交的，
    成交值大的排前面 —— 額度中途用完時先補到的是熱門 ETF。同樣不吃 --limit。"""
    from .compute.etf import is_etf_code

    info = store.read("company_info")
    etf_ind: set[str] = set()
    if not info.empty and {"code", "industry"} <= set(info.columns):
        etf_ind = set(info.loc[info["industry"].astype(str) == "ETF", "code"].astype(str))
    price = store.read("price_daily")
    if price.empty:
        return sorted(etf_ind)
    px = price.assign(code=price["code"].astype(str), date=price["date"].astype(str))
    latest = px["date"].max()
    since = (pd.Timestamp(latest) - pd.Timedelta(days=MARKET_RECENT_DAYS)).date().isoformat()
    recent = px[px["date"] >= since]
    ok = lambda c: c in etf_ind or is_etf_code(c)  # noqa: E731
    day = recent[recent["date"] == latest]
    tv = pd.to_numeric(day.get("turnover", pd.Series(0.0, index=day.index)), errors="coerce").fillna(0.0)
    by_tv = day.assign(_tv=tv).groupby("code")["_tv"].sum().sort_values(ascending=False).index.tolist()
    out = [c for c in by_tv if ok(c)]
    seen = set(out)
    out += sorted(c for c in recent["code"].unique() if c not in seen and ok(c))
    return out


def already_covered(table: str, code: str, start: str, respect_time: bool = True) -> bool:
    """該檔在這張表裡是否已經補到指定起始日之前。

    整張表只讀一次（price_daily 有六十幾萬列，逐檔重讀會讓一輪回補多花好幾分鐘）；
    這一輪新補進去的股票會被 progress 檔記住，不靠這個快取判斷。

    respect_time=False 時一律回 False（只看 progress 檔的 done_key）——
    每月重抓股利公告的步驟用：dividend_events 沒有時間欄位，否則「有資料就算補過」
    會讓月更新永遠被跳掉。"""
    if not respect_time:
        return False
    if table not in _cov_cache:
        _cov_cache[table] = store.read(table)
    df = _cov_cache[table]
    if df.empty or "code" not in df.columns:
        return False
    sub = df[df["code"] == code]
    if sub.empty:
        return False
    # 各表的時間欄位不同：日表 date、月表 ym、季表 period_end、股利公告 announce_date。
    # ★ 2026-09-26（Andy：「除權息為什麼只有一筆」）：dividend_events 以前被當成「沒有時間維度的表，
    #   有資料就算補過」。但每日管線（twse.dividend_events，證交所 OpenAPI 只給當年度公告）比回補先跑，
    #   先寫進一筆今年的公告 → 回補看到「有資料」就跳過 2016 起的歷史，而且**不寫 done 鍵**，
    #   所以永遠不會再補。實測 683 檔（除權息結果有 ≥4 年、公告卻 ≤2 年）裡 662 檔是這樣被跳掉的，
    #   3026 禾伸堂只剩 114 年一筆。改用公告日判斷「最早補到哪」，跟其他表同一套規則。
    col = next((c for c in ("date", "ym", "period_end", "announce_date") if c in sub.columns), None)
    if col is None:
        return True          # 沒有時間維度的表，有資料就算補過
    vals = sub[col].dropna().astype(str)
    vals = vals[vals.str.len() > 0]
    if vals.empty:
        return False
    earliest = str(vals.min())
    return earliest <= start[:len(earliest)]


def done_key_of(key: str, code: str, start: str, tag: str | None = None) -> str:
    """progress 檔裡的完成鍵。

    起始日等於 config.BACKFILL_START 時維持舊格式 "price:2330"（相容既有進度檔），
    其他起始日帶上日期 "price@2000-01-01:2330"；月更新步驟改帶 tag "dividend@m2026-09:2330"，
    每個月的鍵都不同，所以每月會重抓一次。"""
    if tag:
        return f"{key}@{tag}:{code}"
    if start == config.BACKFILL_START:
        return f"{key}:{code}"
    return f"{key}@{start}:{code}"


def datasets_key_of(datasets: str, start: str, tag: str | None = None,
                    scope: str | None = None) -> str:
    """prog["complete"] 的鍵；規則與 done_key_of 一致（舊格式 "revenue" 不變）。

    scope="market" 時尾巴多一段 "@market"（2026-09-28）：同一組資料集從「前 500 檔」擴成
    全市場，必須是**不同的完成旗標**，不然舊的 universe 旗標（已標 done）會讓工作流守門
    以為計畫早就補齊、整輪跳過。逐檔的 done 鍵不帶 scope，已補過的股票照樣跳過不重抓。"""
    base = "+".join(sorted(datasets.replace("+", ",").split(",")))
    if tag:
        key = f"{base}@{tag}"
    elif start == config.BACKFILL_START:
        key = base
    else:
        key = f"{base}@{start}"
    return f"{key}@{scope}" if scope in ("market", "etf") else key


def run(datasets: str, limit: int | None, start: str, *,
        codes: list[str] | None = None, datasets_key: str | None = None,
        tag: str | None = None, respect_time: bool = True) -> dict:
    """跑一輪回補。

    codes：覆寫目標清單（計畫步驟用，例如只補族群成分股）；預設 target_codes(limit)。
    datasets_key：prog["complete"] 用的鍵；預設依 datasets / start / tag 產生。
    tag / respect_time：月更新步驟用，見 done_key_of 與 already_covered。"""
    wanted = set(datasets.replace("+", ",").split(","))
    unknown = wanted - set(DATA_KEYS)
    if unknown:
        log.warning("不認識的資料集，略過：%s", sorted(unknown))
    codes = list(codes) if codes is not None else target_codes(limit)
    log.info("回補目標：%d 檔，資料集 %s，起始 %s%s", len(codes), sorted(wanted), start,
             f"，標記 {tag}" if tag else "")

    prog = _progress()
    prog.setdefault("done", {})
    prog.setdefault("complete", {})
    datasets_key = datasets_key or datasets_key_of(datasets, start, tag)
    summary = {k: 0 for k in DATA_KEYS}
    summary.update({"skipped": 0, "failed": 0, "no_data": 0, "exhausted": False})

    jobs = [
        ("price", "price_daily", lambda c: finmind.price_history(c, start, wait=False)),
        ("inst", "inst_daily", lambda c: finmind.institutional(c, start, wait=False)),
        ("per", "valuation_daily", lambda c: finmind.per_history(c, start, wait=False)),
        ("revenue", "revenue_monthly", lambda c: finmind.month_revenue(c, start, wait=False)),
        ("financial", "financial_q", lambda c: finmind.financial_statements(c, start, wait=False)),
        ("balance", "balance_q", lambda c: finmind.balance_sheet(c, start, wait=False)),
        ("dividend", "dividend_events", lambda c: finmind.dividend_events(c, start, wait=False)),
        ("divresult", "dividend_results", lambda c: finmind.dividend_results(c, start, wait=False)),
        ("margin", "margin_daily", lambda c: finmind.margin_history(c, start, wait=False)),
        ("holding", "shareholding_weekly", lambda c: finmind.holding_history(c, start, wait=False)),
        ("daytrade", "daytrade_daily", lambda c: finmind.day_trading(c, start, wait=False)),
        ("sbl", "sbl_daily", lambda c: finmind.short_sale_balances(c, start, wait=False)),
    ]

    # key -> 這一輪回空的 done_key 清單；key -> 這一輪至少拿到過一次資料
    pending_no_data: dict[str, list[str]] = {}
    got_data: set[str] = set()

    # 被封印的資料集這一輪怎麼處理（見 dataset_mode 的說明）
    modes = {k: dataset_mode(prog, k) for k in wanted}
    asked: dict[str, int] = {k: 0 for k in wanted}
    empty_streak: dict[str, int] = {k: 0 for k in wanted}
    halted: set[str] = set()          # 這一輪已經收手的資料集（連續回空太多）

    fetchers = {k: (t, f) for k, t, f in jobs}
    canary_seen: dict[str, bool | None] = {}

    def canary_has_data(key: str) -> bool | None:
        """封印前的反證（見 SEAL_CANARY_RETRY_HOURS 上方的事故說明）：拿 CANARY_CODE 問同一個區間。

        True＝台積電有資料 → 資料集是通的；False＝台積電也空 → 真的可能不開放；
        None＝不知道（額度用完、抓取例外）→ 這一輪什麼都不判定。每個資料集一輪最多問一次。
        拿到的資料照樣寫進資料湖（store.append 冪等），這 1 次額度不浪費。"""
        if key in canary_seen:
            return canary_seen[key]
        verdict: bool | None = None
        if http.finmind_budget_left() > 1:
            table, fetch = fetchers[key]
            try:
                df = fetch(CANARY_CODE)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s 封印前反證（%s）抓取失敗：%s", key, CANARY_CODE, exc)
                summary["failed"] += 1              # 沒判定成，這一步不算完成，下一輪再來
            else:
                if http.finmind_budget_left() <= 1:
                    summary["exhausted"] = True     # 撞到限流才空的，不能當證據
                elif df is not None and not df.empty:
                    summary[key] += store.append(table, df)
                    verdict = True
                else:
                    verdict = False
        canary_seen[key] = verdict
        log.info("%s 封印前反證：%s 從 %s 起 → %s", key, CANARY_CODE, start,
                 {True: "有資料（資料集是通的，回空的是那幾檔自己沒資料）",
                  False: "也是空的", None: "無法判定"}[verdict])
        return verdict

    def mark_available(key: str) -> None:
        got_data.add(key)
        empty_streak[key] = 0
        if modes[key] != "full":
            unseal_dataset(prog, key)
            modes[key] = "full"

    # 先前以「整組回空」（上游沒回任何錯誤訊息）封印的資料集：這種理由最可能是誤判，
    # 每 SEAL_CANARY_RETRY_HOURS 小時拿台積電驗一次，驗通就當場解封、這一輪恢復全量。
    # HTTP 400「等級不足」那種有明確原因的不走這條（照舊 24 小時拿 5 檔探）。
    for k in sorted(wanted):
        rec = (prog.get("unavailable") or {}).get(k)
        if modes.get(k) == "full" or not isinstance(rec, dict) or k not in fetchers:
            continue
        if str(rec.get("last_reason") or "") != "整組回空":
            continue
        last_c = _parse_ts(rec.get("canary_at"))
        if last_c and (_now() - last_c).total_seconds() < SEAL_CANARY_RETRY_HOURS * 3600:
            continue
        if canary_has_data(k):
            log.warning("%s 先前以「整組回空」封印，但 %s 拿得到資料 —— 判定是誤封印，解除並恢復全量",
                        k, CANARY_CODE)
            mark_available(k)
        else:
            rec["canary_at"] = _now().isoformat()
    for k, mode in sorted(modes.items()):
        if mode == "sealed":
            rec = (prog.get("unavailable") or {}).get(k, {})
            log.info("%s 先前判定為不開放（%s 起，已探 %s 次），封印中，這一輪不花額度",
                     k, str(rec.get("since"))[:19], rec.get("probes"))
        elif mode == "probe":
            log.info("%s 封印超過 %d 小時 —— 這一輪拿 %d 檔去探，探到就恢復全量",
                     k, UNAVAILABLE_RETRY_HOURS, PROBE_CODES)

    for i, code in enumerate(codes, 1):
        if http.finmind_budget_left() <= 1:
            log.warning("FinMind 額度用盡，本輪停在第 %d/%d 檔（%s）", i, len(codes), code)
            summary["exhausted"] = True
            break

        for key, table, fetch in jobs:
            if key not in wanted:
                continue
            if modes[key] == "sealed" or key in halted:
                continue
            if modes[key] == "probe" and asked[key] >= PROBE_CODES:
                continue
            done_key = done_key_of(key, code, start, tag)
            if prog["done"].get(done_key) or already_covered(table, code, start, respect_time):
                summary["skipped"] += 1
                continue
            if key in FINANCIAL_KEYS and roc.is_etf(code):
                prog["done"][done_key] = True
                summary["skipped"] += 1
                continue
            if http.finmind_budget_left() <= 1:
                summary["exhausted"] = True
                break

            asked[key] += 1
            try:
                df = fetch(code)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s %s 抓取失敗：%s", key, code, exc)
                summary["failed"] += 1
                continue

            if http.finmind_budget_left() <= 1:
                # 這一筆是撞到伺服器端限流才空的，不能當作「沒資料」
                summary["exhausted"] = True
                break

            if df is None or df.empty:
                # 額度還在卻拿不到東西 → **通常**是這檔真的沒有這種資料
                #（新掛牌、KY 股缺財報…），記成做過，下一輪不要再問。
                # ★ 但「整組資料集每一檔都回空」是完全不同的一件事：那代表這個資料集
                #   在免費層根本沒開，不是這 N 檔沒有資料。2026-09-12 那輪就是這樣 ——
                #   holding（集保股權分散）500 檔全回空、500 個 done 鍵全被寫死，
                #   於是「大戶 4 週變化」在全站永遠顯示「—」，而且再也不會有人去重抓。
                #   所以先記在暫存區，等整輪跑完再決定要不要真的寫進 progress（見下方）。
                summary["no_data"] += 1
                pending_no_data.setdefault(key, []).append(done_key)
                empty_streak[key] += 1
                # ★ 第一次遇到「整個資料集掛掉」也不該把額度燒完：連續 N 檔回空、
                #   而且這一輪一次都沒成功過 → 先收手，剩下的額度留給補得動的步驟。
                #   2026-09-19 少了這道閘，光是必定失敗的請求就吃掉 506 次額度。
                if empty_streak[key] >= EMPTY_STREAK_LIMIT and key not in got_data:
                    # ★ 收手前先反證（2026-10-03）：名單前面剛好全是「本來就沒資料」的股票時，
                    #   台積電照樣拿得到 → 資料集是通的，繼續往下問，不收手。
                    if canary_has_data(key):
                        mark_available(key)
                        continue
                    halted.add(key)
                    log.warning("%s 連續 %d 檔回空且一次都沒成功 —— 本輪先停問這個資料集，"
                                "把額度留給其他步驟", key, empty_streak[key])
                continue
            n = store.append(table, df)
            summary[key] += n
            got_data.add(key)
            empty_streak[key] = 0
            if modes[key] != "full":
                # 探測成功：解除封印，這一輪剩下的檔照全量跑
                unseal_dataset(prog, key)
                modes[key] = "full"
            prog["done"][done_key] = True

        if i % 25 == 0:
            _save_progress(prog)
            log.info("進度 %d/%d（額度剩 %d）：已寫入 %s",
                     i, len(codes), http.finmind_budget_left(),
                     {k: summary[k] for k in DATA_KEYS if k in wanted})
            time.sleep(0.2)

        if summary["exhausted"]:
            break

    # ★ 結算「回空」的那些鍵：某個 key 這一輪只要成功拿到過一次資料，
    #   其餘回空的就是真的沒資料，照舊記 done；一次都沒拿到（而且問了 3 檔以上）的，
    #   判定是這個資料集本身不開放，**不寫 done**，下一輪重問。
    #   門檻訂 3 是為了不要因為一輪只跑到兩檔就誤判。
    newly_unavailable: list[str] = []
    for key, keys in pending_no_data.items():
        if key not in got_data and len(keys) >= 3:
            # ★ 2026-10-03：判定「不開放」之前的兩道反證（見 SEAL_CANARY_RETRY_HOURS 上方）
            if no_trading_day_since(start):
                log.info("%s 本輪 %d 檔回空，但資料湖裡 %s 之後沒有任何交易日（連假）—— 不判定、不寫 done，下一輪重問",
                         key, len(keys), start)
                continue
            verdict = canary_has_data(key)
            if verdict is None:
                log.info("%s 本輪 %d 檔回空，反證無法判定 —— 不判定、不寫 done，下一輪重問", key, len(keys))
                continue
            if verdict:
                mark_available(key)
        if key in got_data or len(keys) < 3:
            for dk in keys:
                prog["done"][dk] = NO_DATA        # 確認無資料，不是「補到了」
            log.info("%s 本輪 %d 檔上游回空（額度還在）→ 記成確認無資料，下一輪不再問：%s",
                     key, len(keys), "、".join(dk.rsplit(":", 1)[-1] for dk in keys[:30])
                     + ("…" if len(keys) > 30 else ""))
        else:
            # ★ 只看這個資料集自己的錯誤（#311）：全域的「最後一次錯誤」可能是別的資料集撞到的 402
            err = http.finmind_last_error(FINMIND_DATASET.get(key, key)) or {}
            reason = f"HTTP {err.get('status')}：{err.get('msg')}" if err else "整組回空"
            first = seal_dataset(prog, key, reason)
            log.warning("%s 這一輪 %d 檔全部回空 —— 判定為該資料集不開放（而不是這些股票沒資料），"
                        "不寫入 done；已寫進進度檔封印，%d 小時後只拿 %d 檔重探。上游回應：%s",
                        key, len(keys), UNAVAILABLE_RETRY_HOURS, PROBE_CODES, reason)
            summary["unavailable"] = sorted(set(summary.get("unavailable", [])) | {key})
            if first:
                newly_unavailable.append(key)
    if newly_unavailable:
        summary["newly_unavailable"] = sorted(newly_unavailable)
    sealed_now = sorted(k for k in wanted if k in (prog.get("unavailable") or {}))
    if sealed_now:
        summary["sealed"] = sealed_now

    # 這一組資料集什麼情況下才算「補齊」（排程的 guard 看這個旗標決定要不要整輪跳過）：
    #   1) 沒有撞到 FinMind 限流（exhausted=False）——還沒問完，當然不算完成
    #   2) 沒有抓取例外（failed=0）
    #   3) 沒有**這一輪第一次**被判定為不開放的資料集 —— 那個狀態還不確定
    #      （可能只是上游暫時壞掉），留一輪讓下一次重問，不要太早宣告完成
    # ★ 已經封印過的資料集**不算**未完成。這一條是 2026-09-19 事故的正解：
    #   原本寫成「只要有 unavailable 就永遠不算完成」，結果一個確定不開放的資料集
    #   把整個計畫鎖死在第 1 步，後面幾千檔個股的價量與法人永遠輪不到。
    #   不開放的資料集不會因為我們一直等就開放；它該被封印＋每天探一次，
    #   而不是拿整個計畫去陪葬。
    finished_all = (not summary["exhausted"] and summary["failed"] == 0
                    and not newly_unavailable)
    summary["finished"] = finished_all

    # ★ 2026-09-28：把「這一步還剩幾檔沒補、幾檔確認無資料」寫進完成旗標與 log。
    #   那天 dividend+divresult@2009-01-01@market 連續十幾輪 done=False，被誤判成「卡住、永遠不會完成」，
    #   實際上每一輪都有前進（2009 鍵 500→1,928），只是每輪都撞到額度上限才停；
    #   而看得到的只有 done 區的鍵數 —— 那裡 `dividend:<代號>` 是 2016 那一步的鍵，跟 2009 這一步無關，
    #   `dividend@2009-01-01:<代號>` 才是。旗標上直接寫「剩幾檔」，就不必再從鍵名去猜。
    tables = {k: t for k, t, _ in jobs}
    remaining: dict[str, int] = {}
    no_data_n: dict[str, int] = {}
    for key in sorted(k for k in wanted if k in tables):
        left = nd = 0
        for code in codes:
            v = prog["done"].get(done_key_of(key, code, start, tag))
            if v == NO_DATA:
                nd += 1
            if v:
                continue
            if key in FINANCIAL_KEYS and roc.is_etf(code):
                continue
            if already_covered(tables[key], code, start, respect_time):
                continue
            left += 1
        remaining[key] = left
        no_data_n[key] = nd
    summary["remaining"] = remaining
    prog["complete"][datasets_key] = {
        "done": finished_all,
        "at": datetime.now(timezone.utc).isoformat(),
        "codes": len(codes),
        "remaining": remaining,
        "no_data": no_data_n,
    }
    _save_progress(prog)
    if any(remaining.values()):
        why = ("FinMind 額度用盡，下一輪從這裡接續" if summary["exhausted"]
               else "有抓取失敗或資料集封印中" if not finished_all
               else "封印中的資料集不計入完成判定")
        log.info("%s 還剩 %s 檔沒補（約 %d 次請求；%s）；確認無資料 %s 檔",
                 datasets_key, remaining, sum(remaining.values()), why, no_data_n)
    else:
        log.info("%s 名單 %d 檔全部處理過；確認無資料 %s 檔", datasets_key, len(codes), no_data_n)
    log.info("回補結束：%s", summary)
    return summary


# ------------------------------------------------------------------ 回補計畫

def monthly_step(today: date | None = None) -> dict:
    """每月重抓一次族群成分股的股利公告（今年以來）。

    tag 帶年月，所以每個月的 done_key 都是新的；一個月約 260 次請求。"""
    today = today or datetime.now(TAIPEI).date()
    return {"datasets": "dividend+divresult", "start": f"{today.year}-01-01",
            "scope": "groups", "tag": f"m{today:%Y-%m}"}


INDEX_START = "2000-01-01"
INST_FRESH_DAYS = 14      # 法人每日續補往回抓幾天（涵蓋連假；一檔仍只算一次請求）
FRESH_MAX_LOOKBACK = 90   # 落後很久的股票最多往回補幾天（歷史回補吃掉額度那幾天留下的缺口）
# 每日續補的表：(回補資料集鍵, 資料湖表, 每天最多幾檔)。順序＝額度不夠時的優先序（法人最重要）。
#
# ★ 2026-09-28 改成全市場後的每日請求量估算：
#   全市場普通股約 1,975 檔，每日管線（run_daily.fetch_institutional）已經顧好成交值前 500 檔，
#   所以每張表每天落後的大約是 1,475 檔。三張表全部每天補 ≈ 4,400 次，
#   以每小時約 510 次可用額度算要吃掉將近 9 小時 —— 會把歷史回補與其他步驟擠光。
#   所以每張表設「每天最多幾檔」，挑**落後最久的先補**（一次請求就把缺口整段抓回來，
#   不必天天問）：inst 750 ＋ daytrade 375 ＋ sbl 375 ＝ 每天最多 1,500 次 ≈ 3 輪的額度。
#   代價：前 500 名以外的股票，法人約每 2 個交易日更新一次、當沖／借券約每 4 個交易日一次；
#   窗口 INST_FRESH_DAYS=14 天（約 10 個交易日）大於這個週期，所以不會留缺口。
#
# ★ 2026-10-03（DECISIONS #304）兩處調整：
#   1. 加 margin（融資融券）：上市的每天由 run_daily 從證交所 MI_MARGN 全量抓，**上櫃沒有任何每日來源** ——
#      上櫃的融資券只靠計畫裡 holding+margin@2021-01-01 那一步一次性補到 09-23，之後就停了
#      （margin_daily 每日檔數 1,828 → 1,298，掉的 530 檔正好是上櫃）。走 FinMind 逐檔、跟歷史步驟同一支函式、同一口徑。
#   2. 基本上限仍是每天 1,500 次（inst 600 ＋ margin 300 ＋ daytrade 300 ＋ sbl 300）；
#      **計畫（PLAN_DEFAULT）本月已補齊時乘以 FRESH_BOOST** —— 那時候已經沒有歷史步驟需要讓額度，
#      原本「其餘留給歷史回補」的理由不成立，額度閒著不用只會讓續補多拖幾天。
#
# ★ 2026-10-03 晚（DECISIONS #311）順序與分配再改：
#   證據：GitHub 的排程大量延遲／丟棄（backfill.yml 寫每小時，實際 10-01～10-02 一天只跑 4 輪、間隔 4～6 小時；
#   同一個 repo 的盤中巡檢 01:17 的排程 07:03 才跑），每輪約 505 次額度 → 一天實際只有約 2,000 次，
#   而每個交易日的續補需求是 法人 ~1,475 ＋ 當沖 ~1,750 ＋ 借券 ~1,900 ＋ 上櫃融資券 ~530 ≈ 5,650 次。
#   舊順序（法人第一、上限 ×2＝1,200）讓法人每輪把額度吃光：#304 合併後第一輪（run 172）
#   法人寫了 499 檔就用盡，當沖續補一次都沒輪到，資料湖 09-25 之後還是只有 2330（反證寫的那 4 天）。
#   1. **順序改成 當沖 → 借券 → 上櫃融資券 → 法人**：當沖／借券沒有任何每日來源（全靠這裡），
#      法人前 500 名已經由每日管線顧好、上市融資券由 MI_MARGN 顧好，缺的時候傷害比較小。
#   2. **每輪先給上櫃融資券、法人各一份保底（FRESH_SHARE），剩下的照順序補**（refresh_stale_inst）：
#      純粹照順序的話，平日需求是供給的 2.5 倍，排後面的會一整週一檔都輪不到；
#      法人保底 15% 讓前 500 名以外的平日也約 4～5 個交易日更新一次、上櫃融資券 10%
#      （一次請求把缺口整段補回，不會有洞）。其餘 75% 照順序：當沖先做完、再借券。
#   3. 基本上限仍是每天 1,500 次（測試釘住）；計畫本月補齊時 ×FRESH_BOOST＝4 ——
#      一天的上限要蓋得住全市場的需求，不然當天那一輪名單做完就被守門判定「今天補齊」，
#      剩下的排程整天空跑、額度閒著（上限只決定「今天最多問幾檔」，真正的節流閥是 FinMind 額度）。
FRESH_TABLES = (("daytrade", "daytrade_daily", 400), ("sbl", "sbl_daily", 400),
                ("margin", "margin_daily", 300), ("inst", "inst_daily", 400))
FRESH_BOOST = 4
# 每輪額度的保底（佔這一輪額度的比例）。沒列的（當沖、借券）不設保底，直接吃第二段的剩餘額度、照順序排第一第二 ——
# 它們沒有任何每日來源，缺口最大；保底只是確保排後面的兩張表每輪都有前進。
FRESH_SHARE = {"margin": 0.10, "inst": 0.15}


def stale_inst_codes(inst: pd.DataFrame, price: pd.DataFrame, universe: list[str],
                     cap: int | None = None) -> tuple[str | None, list[str]]:
    """哪些股票的三大法人落後了：回傳 (最新交易日, 代號清單)。

    判準（刻意保守，避免把額度燒在「本來就不會有資料」的股票上）：
    - 最新交易日＝price_daily 的最大日期（**用資料裡的日期，不用執行當下的日期**）；
    - 那天有成交（停牌股不問）；
    - inst_daily 裡**已經有**這一檔（一列都沒有的交給計畫的歷史步驟，回空會記 done，不會每天重問）；
    - 而且它最後一天 < 最新交易日。
    每日管線補的前 500 檔自然已經是最新的，不會被選進來。
    cap：最多回幾檔。有 cap 時**落後最久的排前面**（同樣落後的維持 universe 的順序），
    這樣每天只補一部分也不會讓某幾檔一直輪不到。
    """
    if price is None or price.empty or inst is None or inst.empty:
        return None, []
    latest = str(price["date"].astype(str).max())
    traded = set(price.loc[price["date"].astype(str) == latest, "code"].astype(str))
    last = inst.assign(code=inst["code"].astype(str), date=inst["date"].astype(str)).groupby("code")["date"].max()
    out = [c for c in universe if c in traded and c in last.index and last[c] < latest]
    if cap is not None:
        # ★ 2026-10-03（DECISIONS #304）：「落後最久的先補」要排除**早就停止有資料**的股票，
        #   否則名單最前面永遠是那幾十檔（當沖表裡最後一筆停在 2025-04 的處置股之類），
        #   每天的上限先被它們吃掉，而且整組回空會被誤判成資料集不開放（09-28 就是這樣封印的）。
        #   判準用**這張表自己的最新日期**往回 INST_FRESH_DAYS 天（不是 price 的最新日）：
        #   整張表一起落後（例如上游停了一週）時，大家都還算「活著」，不會整批被降級。
        #   被降級的不是剔除，只是排到最後 —— 復牌、恢復當沖的股票額度有剩時照樣會補到。
        tbl_latest = str(last.max())
        cut = (pd.Timestamp(tbl_latest) - pd.Timedelta(days=INST_FRESH_DAYS)).date().isoformat()
        out = sorted(out, key=lambda c: (last[c] < cut, last[c]))[:cap]     # sorted 是穩定排序
    return latest, out


def fresh_start(latest: str, last_dates: list[str]) -> str:
    """續補的起始日：平常往回 INST_FRESH_DAYS 天；有股票落後更久就往前拉到它的最後一天，
    但最多 FRESH_MAX_LOOKBACK 天（一檔一次請求，拉長區間不多花額度）。"""
    base = (pd.Timestamp(latest) - pd.Timedelta(days=INST_FRESH_DAYS)).date().isoformat()
    floor = (pd.Timestamp(latest) - pd.Timedelta(days=FRESH_MAX_LOOKBACK)).date().isoformat()
    oldest = min(last_dates) if last_dates else base
    return max(floor, min(base, oldest))


def refresh_stale_inst(prog: dict, today: date | None = None, limit: int | None = None) -> bool:
    """三大法人（＋當沖、借券）的每日續補：每日管線只顧前 500 檔，其餘股票在這裡補（2026-09-27）。

    為什麼不塞進 PLAN_DEFAULT：計畫的完成旗標以「月」為單位（plan_is_done），
    每天都要做的事放進去會讓計畫永遠不算完成；照 backfill_indices 的做法另外記
    `complete["inst_fresh"] = {done, date}`，工作流的守門也看這個旗標（當天沒做完就放行一輪）。

    ★ 2026-09-28：範圍從 target_codes(limit)（手動觸發時只剩前 500 檔）改成 market_codes() 全市場，
      並依 FRESH_TABLES 的每日上限節流（估算見 FRESH_TABLES 上方）。limit 參數保留但不再使用。
    額度用完就停，下一輪接續（當天的 done 鍵會跳過已補的）。
    """
    today = today or datetime.now(TAIPEI).date()
    flag = (prog.get("complete") or {}).get("inst_fresh")
    if isinstance(flag, dict) and flag.get("done") and flag.get("date") == today.isoformat():
        return True
    if http.finmind_budget_left() <= 1:
        return False
    price = store.read("price_daily")
    universe = market_codes()
    ok, latest, n_codes = True, None, {}
    plan = (prog.get("complete") or {}).get("plan:default")
    boost = FRESH_BOOST if (isinstance(plan, dict) and plan.get("done")
                            and plan.get("month") == f"{today:%Y-%m}") else 1
    if boost > 1:
        log.info("計畫本月已補齊 —— 每日續補上限 ×%d", boost)
    # 當沖、借券賣出（2026-09-27）同一套：歷史步驟補過的股票，之後每天在這裡續補
    lists: list[tuple[str, list[str], str, str]] = []     # (key, 名單, 起始日, 最新交易日)
    for key, table, cap in FRESH_TABLES:
        cap = cap * boost
        tbl = store.read(table)
        lt, codes = stale_inst_codes(tbl, price, universe, cap=cap)
        latest = latest or lt
        n_codes[key] = len(codes)
        if not codes:
            continue
        last = tbl.assign(code=tbl["code"].astype(str), date=tbl["date"].astype(str)).groupby("code")["date"].max()
        start = fresh_start(lt, [last[c] for c in codes])
        log.info("%s 每日續補：%d 檔落後於 %s（每日上限 %d，從 %s 起抓）", key, len(codes), lt, cap, start)
        lists.append((key, codes, start, lt))

    def _run(key: str, codes: list[str], start: str, lt: str) -> dict:
        return run(key, None, start, codes=codes, datasets_key=f"{key}@fresh{lt}",
                   tag=f"fresh{lt}", respect_time=False)

    # ★ 2026-10-03（#311）第一段：這一輪的額度不夠把所有名單做完時，先給有保底的表（上櫃融資券、法人）
    #   各做名單最前面（落後最久）的一份。這樣不管排程一天跑幾輪，排後面的表每輪都有前進，
    #   不會出現「排第一的那張每輪吃光額度、後面的整天輪不到」（run 172／173 的法人就是這樣把當沖擠掉）。
    budget = http.finmind_budget_left()
    need = sum(len(c) for _, c, _, _ in lists)
    if lists and need > budget > 1:
        log.info("續補名單共 %d 檔、這一輪額度約 %d —— 先做保底份額：%s，其餘照順序", need, budget,
                 {k: int(budget * FRESH_SHARE[k]) for k, _, _, _ in lists if k in FRESH_SHARE})
        for key, codes, start, lt in lists:
            share = int(budget * FRESH_SHARE.get(key, 0))
            if share <= 0:
                continue                       # 沒有保底的（當沖、借券）在第二段照順序吃剩餘額度
            if http.finmind_budget_left() <= 1:
                break
            # 名單比份額短也在這裡整份做完 —— 留到第二段的話會排在當沖、借券後面被吃光
            if _run(key, codes[:share], start, lt).get("exhausted"):
                break
    # 第二段：剩下的額度照 FRESH_TABLES 的順序把**整份名單**做完（第一段做過的有 done 鍵，不會重問）。
    #   額度已經用完時仍然每張表走一次：run() 會立刻停在第 1 檔，但會把「這張表還剩幾檔」寫進完成旗標，
    #   進度檔才看得出每張表各自補到哪（不然只會留下第一段那一小段的數字）。
    for key, codes, start, lt in lists:
        s = _run(key, codes, start, lt)
        ok = ok and bool(s.get("finished"))
    prog = _progress()
    # 續補的 done 鍵一天一組（<key>@fresh<日期>:<代號>），舊的留著只會讓進度檔每天多 1,500 個鍵
    prog["done"] = {k: v for k, v in (prog.get("done") or {}).items()
                    if "@fresh" not in k or f"@fresh{latest}:" in k}
    prog.setdefault("complete", {})["inst_fresh"] = {
        "done": ok, "date": today.isoformat(), "latest": latest, "codes": n_codes,
        "at": datetime.now(timezone.utc).isoformat()}
    _save_progress(prog)
    return ok


def backfill_indices(prog: dict, start: str = INDEX_START) -> bool:
    """把加權指數、櫃買指數、台指期的日 K 一次補到 2000 年。

    為什麼要另外寫一支，而不是塞進 PLAN_DEFAULT（2026-09-19）
    --------------------------------------------------------
    計畫的每一步都是「逐檔跑 codes」，但指數不是個股 —— 三個 symbol 一共只要 3 次請求。

    為什麼非補不可（Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」）
    ------------------------------------------------------------------
    `run_daily` 抓指數時寫死 `since = now - 40 天`，而回補計畫裡**沒有這張表** ——
    所以資料湖永遠只有 40 天：實測 32 個交易日 → 週 K 7 根、**月 K 2 根、季 K 1 根**。
    `market3.js` 卻給了日／週／月／季四顆按鈕，使用者按「季 K」看到一根棒子。
    這不是「還沒補完」，是**設計上永遠不會變多**，所以當時回報「已修好」是不對的。

    順帶解掉季節性的基準問題：`seasonality_v3.json` 的 note 寫著「指數只有 12 個月，不夠比」，
    所謂「超額報酬」其實退回成全市場等權平均、不是大盤。指數有歷史之後才比得了。

    補過就不再補（進度檔記 `complete["index_ohlc"]`），每日管線照樣用 40 天的增量。
    """
    flag = (prog.get("complete") or {}).get("index_ohlc")
    if isinstance(flag, dict) and flag.get("done") and flag.get("start") == start:
        log.info("指數歷史已補過（%s 起），跳過", start)
        return True
    if http.finmind_budget_left() <= 3:
        log.warning("額度不足 3 次，指數歷史這一輪先不補")
        return False

    total = 0
    # 每個來源要求哪些 symbol 都齊了才算數：index_ohlc 是一支函式抓兩個指數，
    # 只回到加權、櫃買失敗時它仍然是「非空」的 —— 那樣標成 done 會讓櫃買永遠只有 40 天。
    for label, fn, need, ds in (("指數", finmind.index_ohlc, {"TSE", "OTC"}, "TaiwanStockPrice"),
                                ("台指期", finmind.futures_ohlc, {"FUT"}, "TaiwanFuturesDaily")):
        try:
            df = fn(start, wait=False)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s 歷史抓取失敗：%s", label, exc)
            return False
        if df is None or df.empty:
            err = http.finmind_last_error(ds) or {}
            log.warning("%s 歷史回空 —— 不標 done，下一輪重試（上游最近一次錯誤：%s）",
                        label, f"HTTP {err.get('status')} {err.get('msg')}" if err else "無")
            return False
        missing = need - set(df.get("symbol", pd.Series(dtype=str)).astype(str))
        if missing:
            log.warning("%s 歷史只拿到部分代號，缺 %s —— 先寫進湖裡但不標 done，下一輪重試",
                        label, sorted(missing))
            store.append("index_ohlc", df)
            return False
        total += store.append("index_ohlc", df)

    prog.setdefault("complete", {})["index_ohlc"] = {
        "done": True, "start": start,
        "at": datetime.now(timezone.utc).isoformat(), "rows": total,
    }
    _save_progress(prog)
    log.info("指數歷史補完：寫入 %d 列（%s 起）", total, start)
    return True


FUT_TICK_DAYS = 60     # 台指期逐筆往回補幾個交易日（一天 1 次額度；60 天 ≈ 1H 300 根）


def backfill_index_intraday(prog: dict, days: int = FUT_TICK_DAYS) -> bool:
    """大盤三張圖 1H／4H 的一次性回補（2026-09-25）。

    ① 加權／櫃買：Yahoo 60 分補滿 730 天、15 分補滿 60 天（不吃 FinMind 額度）。
       每日管線湖空時也會自己補滿，這裡是讓回補那輪就先長出來。
    ② 台指期：FinMind TaiwanFuturesTick 逐日抓最近 `days` 個交易日（交易日取自 index_ohlc 的 FUT，
       不用執行當天推算），聚合成 60 分入湖。一天 1 次額度，額度剩 ≤ 5 就停，下一輪接續；
       已在湖裡的日子跳過，所以中斷重跑不會重花額度。
    全部補完記 `complete["index_intraday"]`。資料集沒權限（回空且有錯誤訊息）就記 `unavailable` 不再重試。
    """
    from .compute.intraday_bars import ticks_to_60m
    from .sources import yahoo

    from .compute.intraday_bars import kbar_to_60m

    flag = (prog.get("complete") or {}).get("index_intraday") or {}
    if flag.get("yahoo_v") != 3:
        # 2026-09-25 櫃買加了 Yahoo 候選代號（^TWOTCI）；舊進度的 yahoo=true 是只有加權抓到時記的，重開 Yahoo 一次。
        # ★ 2026-09-28（v3）：櫃買的 Yahoo 代號實測是 IX0043.TWO（^TWOII／^TWOTCI 都回空），而且
        #   index_intraday_since 改成每個指數各算各的缺口 —— 重開一次，讓櫃買一口氣補回 730 天 60 分＋60 天 15 分。
        flag.pop("yahoo", None)
        flag.pop("done", None)
        flag["yahoo_v"] = 3
    if flag.get("tse1m_v") != 1:
        # 2026-09-28：加權真實 1 分 K（FinMind 每 5 秒指數＋成交統計）回補，見 _backfill_tse_minute。
        flag.pop("done", None)
        flag["tse1m_v"] = 1
    if flag.get("kbar_v") != 1:
        # 2026-09-25 加了 FinMind 分 K 路線（櫃買 TaiwanStockKBar、台指期 TaiwanFuturesKBar）：
        # 舊進度可能因為「逐筆不可用」就記成 done，這裡重開一次讓分 K 那兩條有機會補；Yahoo 那段不重跑。
        flag.pop("done", None)
        flag.pop("fut_unavailable", None)
        flag["kbar_v"] = 1
    if flag.get("done"):
        return True
    have = store.read("index_intraday")
    if not flag.get("yahoo"):
        n = 0
        for iv in ("60m", "15m"):
            n += store.append("index_intraday", yahoo.index_intraday_since(have, iv))
        log.info("指數分 K（Yahoo）回補寫入 %d 列", n)
        flag["yahoo"] = n > 0 or not have.empty
        have = store.read("index_intraday")

    if not flag.get("fut_unavailable"):
        dates = store.read("index_ohlc")
        dates = (sorted(dates.loc[dates["symbol"].astype(str) == "FUT", "date"].astype(str).unique())
                 if not dates.empty else [])[-days:]
        got = set()
        if not have.empty:
            fut = have[have["symbol"].astype(str) == "FUT"]
            got = set(fut["ts"].astype(str).str.slice(0, 10))
        todo = [d for d in dates if d not in got]
        for d in reversed(todo):          # 新的先補：最近的 1H 最有用
            if http.finmind_budget_left() <= 5:
                log.warning("額度剩不多，台指期逐筆回補停在 %s，下一輪接續", d)
                break
            bars = pd.DataFrame()
            if not flag.get("tick_unavailable"):
                bars = ticks_to_60m(finmind.futures_ticks(d))
                if bars.empty and _dataset_denied("TaiwanFuturesTick"):
                    flag["tick_unavailable"] = _err_text("TaiwanFuturesTick")
            if bars.empty:
                # 逐筆沒權限就試期貨分 K（2026-09 FinMind 新增的 TaiwanFuturesKBar）
                bars = kbar_to_60m(finmind.futures_kbar(d), futures=True)
                if bars.empty and _dataset_denied("TaiwanFuturesKBar"):
                    log.warning("台指期逐筆與分 K 都不可用（%s），記下來不再重試", _err_text("TaiwanFuturesKBar"))
                    flag["fut_unavailable"] = _err_text("TaiwanFuturesKBar")
                    break
            if bars.empty:
                continue
            store.append("index_intraday", bars)
            todo = [x for x in todo if x != d]
        flag["fut_left"] = len(todo)
        fut_ok = not todo or bool(flag.get("fut_unavailable"))
    else:
        fut_ok = True

    otc_ok = _backfill_otc_kbar(flag, have, days)
    tse_ok = _backfill_tse_minute(flag, store.read("index_intraday"))
    flag["done"] = bool(flag.get("yahoo")) and fut_ok and otc_ok and tse_ok
    flag["at"] = datetime.now(timezone.utc).isoformat()
    prog.setdefault("complete", {})["index_intraday"] = flag
    _save_progress(prog)
    return flag["done"]


TSE_MINUTE_DAYS = 730        # 加權真實 1 分 K 往回補幾個日曆日（跟 Yahoo 60 分 K 的保留期一樣長，1H 整段都有真實量）
TSE_MINUTE_PER_RUN = 120     # 每一輪最多補幾個交易日（一天 2 次額度 → 240 次；每小時額度 510，留給法人續補等其他步驟）


def _backfill_tse_minute(flag: dict, have: pd.DataFrame) -> bool:
    """加權真實 1 分 K（2026-09-28，Andy：「加權指數的成交量 15min 30min 1H 都沒有確切成交量」）。回傳這段算不算完成。

    來源：FinMind TaiwanVariousIndicators5Seconds（加權每 5 秒）＋ TaiwanStockStatisticsOfOrderBookAndTrade
    （每 5 秒累計成交金額），兩個都是免費資料集（Actions 實測 register 等級拿得到、兩年前也拿得到）。
    交易日取自 index_ohlc 的 TSE（回應裡的日期，不用執行當天推算）；湖裡已有 finmind 那天的跳過；新的先補
    （最近的 15／30／60 分最常看）；額度剩 ≤ 20 或這一輪補滿 TSE_MINUTE_PER_RUN 天就停，下一小時接續。
    兩個資料集回「沒權限」（400 且不是額度）就記 `tse1m_unavailable`，之後不再重試。
    """
    from .run_daily import tse_minute_todo

    if flag.get("tse1m_unavailable"):
        return True
    ohlc = store.read("index_ohlc")
    if ohlc is not None and not ohlc.empty:
        cut = (datetime.now(TAIPEI) - timedelta(days=TSE_MINUTE_DAYS)).strftime("%Y-%m-%d")
        ohlc = ohlc[ohlc["date"].astype(str).str[:10] >= cut]
    # 同一天連續 3 輪都回空（FinMind 那天真的缺資料）就不再試 —— 不然每小時都為它燒 2 次額度、done 永遠不成立
    empt = flag.setdefault("tse1m_empty", {})
    todo = [d for d in tse_minute_todo(have, ohlc, 100_000) if empt.get(d, 0) < 3]
    n = 0
    for d in list(todo):
        if n >= TSE_MINUTE_PER_RUN:
            break
        if http.finmind_budget_left() <= 20:
            log.warning("額度剩不多，加權 1 分 K 回補停在 %s，下一輪接續", d)
            break
        bars = finmind.tse_minute_bars(d)
        n += 1
        if bars.empty:
            if _dataset_denied(finmind.TSE_5S_PRICE) or _dataset_denied(finmind.TSE_5S_TRADE):
                ds = finmind.TSE_5S_PRICE if _dataset_denied(finmind.TSE_5S_PRICE) else finmind.TSE_5S_TRADE
                log.warning("加權 5 秒資料不可用（%s），記下來不再重試", _err_text(ds))
                flag["tse1m_unavailable"] = _err_text(ds)
                return True
            empt[d] = empt.get(d, 0) + 1
            continue
        store.append("index_intraday", bars)
        todo.remove(d)
    flag["tse1m_left"] = len(todo)
    log.info("加權 1 分 K 回補：這一輪試了 %d 天，還剩 %d 天", n, len(todo))
    return not todo


def _dataset_denied(dataset: str) -> bool:
    """這個資料集最近一次是不是「沒權限／不存在」（402/429 是額度，不算）。
    以資料集為範圍（#311）：這個資料集之後成功過一次，舊的拒絕就不算數。"""
    err = http.finmind_last_error(dataset) or {}
    return err.get("dataset") == dataset and err.get("status") not in (None, 402, 429)


def _err_text(dataset: str | None = None) -> str:
    err = http.finmind_last_error(dataset) or {}
    return f"{err.get('dataset')} {err.get('status')} {err.get('msg')}"[:200]


def _backfill_otc_kbar(flag: dict, have: pd.DataFrame, days: int) -> bool:
    """櫃買 60 分 K：Yahoo 沒有，改逐日抓 FinMind TaiwanStockKBar 聚合（2026-09-25）。回傳這段算不算完成。

    交易日取自 index_ohlc 的 OTC（回應裡的日期，不用執行當天推算）；湖裡已有的日子跳過；
    額度剩 ≤ 5 就停；所有候選代號都回「沒權限」就記 `otc_unavailable`，之後不再重試。
    """
    from .compute.intraday_bars import kbar_to_60m

    if flag.get("otc_unavailable"):
        return True
    dates = store.read("index_ohlc")
    dates = (sorted(dates.loc[dates["symbol"].astype(str) == "OTC", "date"].astype(str).unique())
             if not dates.empty else [])[-days:]
    got = set()
    if have is not None and not have.empty:
        otc = have[have["symbol"].astype(str) == "OTC"]
        got = set(otc["ts"].astype(str).str.slice(0, 10))
    todo = [d for d in dates if d not in got]
    ids = list(finmind.OTC_KBAR_IDS)
    empties = 0
    for d in reversed(todo):
        if http.finmind_budget_left() <= 5:
            log.warning("額度剩不多，櫃買分 K 回補停在 %s，下一輪接續", d)
            break
        bars = pd.DataFrame()
        denied = 0
        for data_id in ids:
            bars = kbar_to_60m(finmind.index_kbar(d, data_id), symbol="OTC")
            if not bars.empty:
                ids = [data_id]          # 找到能用的代號就只用它，後面的日子不再浪費額度
                break
            denied += _dataset_denied("TaiwanStockKBar")
        if bars.empty:
            if denied == len(ids):
                log.warning("櫃買分 K 不可用（%s），記下來不再重試", _err_text("TaiwanStockKBar"))
                flag["otc_unavailable"] = _err_text("TaiwanStockKBar")
                return True
            empties += 1
            if empties >= 3 and not got and len(ids) > 1:
                # 代號不對時 FinMind 可能回 200 空陣列、沒有錯誤碼 —— 不設這道閘就會每小時燒一輪額度
                log.warning("櫃買分 K 連續 %d 個交易日所有代號都回空，視為不可用", empties)
                flag["otc_unavailable"] = f"連續 {empties} 個交易日回空（{_err_text('TaiwanStockKBar')}）"
                return True
            continue
        store.append("index_intraday", bars)
        todo = [x for x in todo if x != d]
    flag["otc_left"] = len(todo)
    return not todo


# ------------------------------------------------------------------ 公司 Logo（2026-09-26）

COMPANY_WEBSITE_REFRESH_DAYS = 30   # 上櫃／興櫃網址清單多久重抓一次（公司很少換網址）


def backfill_logos(prog: dict, limit: int | None = None, today: date | None = None) -> dict:
    """公司 Logo 的增量抓取（細節見 sources/logos.py 與 docs/logo_sources.md）。

    為什麼放在回補、而不是每日管線：
    - Logo 很少換，一天抓三次毫無意義；回補每小時一輪，剛好適合「每輪 300 家、慢慢補齊」。
    - 不吃 FinMind 額度，所以放在 FinMind 健檢**之前**跑 —— token 掛掉不該連 Logo 都停。
    - 補齊之後 `logo_progress.json` 會記下一次到期日，`backfill.yml` 的排程守門看它決定要不要放行，
      所以不會因為 plan:default 補齊了就永遠輪不到（2026-09-25 index_intraday 踩過一樣的坑）。
    失敗一律吞掉、記 log，不影響後面的回補步驟。
    """
    from .groups import loader as _loader
    from .sources import logos

    if not config.LOGOS_ENABLED:
        log.info("LOGOS_ENABLED 關閉，跳過 Logo")
        return logos.run(0)

    # ① 上櫃／興櫃網址（company_info 只有上市的網址）：30 天重抓一次，存進 company_website
    today = today or datetime.now(TAIPEI).date()
    flag = (prog.get("complete") or {}).get("company_website") or {}
    last = _parse_ts(flag.get("at"))
    if last is None or (today - last.astimezone(TAIPEI).date()).days >= COMPANY_WEBSITE_REFRESH_DAYS:
        try:
            df = logos.company_websites()
            n = store.append("company_website", df) if not df.empty else 0
            prog.setdefault("complete", {})["company_website"] = {
                "done": not df.empty, "at": _now().isoformat(), "rows": int(len(df)), "new": int(n),
                # 抓不到也記時間：不然櫃買擋雲端 IP 的日子，每一輪都會重打一次
            }
            _save_progress(prog)
        except Exception as exc:  # noqa: BLE001
            log.warning("上櫃／興櫃網址抓取失敗（Logo 只能先用上市的網址）：%s", exc)

    # ② Logo 本身（族群成分股優先）
    try:
        m = _loader.membership()
        prio = list(dict.fromkeys(m["code"].astype(str).tolist())) if not m.empty else []
    except Exception:  # noqa: BLE001
        prio = []
    return logos.run(limit, today=today, priority=prio)


# 不吃 FinMind 額度、放在健檢之前跑的資料集（`--datasets` 只給這幾個時，整輪不碰 FinMind）
EXTRA_DATASETS = {"logos", "intraday"}


def backfill_intraday_60m() -> dict | None:
    """個股 60 分 K 全市場回補一輪（2026-09-30，細節見 pipeline/intraday60.py）。

    為什麼放回補、不放每日管線：新增約 1,400 檔 × Yahoo 兩年，一次打完會被限流、也拖慢每日管線；
    回補每小時一輪、每輪最多 intraday60.BACKFILL_PER_RUN 檔，約 5 輪補完（2026-09-30：要補 1,719 檔）。進度寫 `complete["intraday_60m"]`
    （含 remaining），backfill.yml 的守門看它 —— 計畫補齊之後這一步還沒補完，照樣放行一輪。
    失敗一律吞掉、記 log，不影響後面的 FinMind 步驟。
    """
    from . import intraday60
    try:
        prog = _progress()
        return intraday60.backfill(prog, save=_save_progress)
    except Exception as exc:  # noqa: BLE001
        log.warning("個股 60 分 K 回補失敗（不影響其他步驟）：%s", exc)
        return None


def finmind_reachable(prog: dict) -> bool:
    """花 1 次額度確認「整把 token 還通不通」。

    為什麼要這一步（2026-09-19 的事故）
    ----------------------------------
    那天 revenue / financial / balance 連續好幾輪每一檔都回 400，
    日誌裡只寫「回 400，不重試」，所以沒有人分得出是
    ①「這三個資料集不開放」還是 ②「整把 token 失效／帳號等級被改」——
    而這兩種的修法完全不同（前者封印那三個資料集，後者要換金鑰）。
    於是每一輪都把 506 次額度燒在必定失敗的請求上，計畫永遠停在第 1 步。

    做法：先問一個最基本、免費層一定拿得到的東西（台積電最近 10 天的日線）。
    - 拿得到 → 是個別資料集的問題，照常跑，由封印機制處理。
    - 拿不到 → 不是資料集的問題，整輪直接停，把上游回應的原文寫進進度檔，
      讓下一個人（或 Andy）一眼看出要不要去 GitHub Secrets 換 token。
    """
    if http.finmind_budget_left() <= 1:
        return True          # 額度本來就沒了，健檢沒有意義，交給原本的限流流程
    since = (datetime.now(TAIPEI).date() - timedelta(days=CANARY_DAYS)).isoformat()
    try:
        df = finmind.price_history(CANARY_CODE, since, wait=False)
    except Exception as exc:  # noqa: BLE001
        df = None
        log.warning("FinMind 健檢拋出例外：%s", exc)
    ok = df is not None and not df.empty
    err = http.finmind_last_error("TaiwanStockPrice") or {}
    prog["finmind_health"] = {
        "ok": ok,
        "at": _now().isoformat(),
        "probe": f"TaiwanStockPrice/{CANARY_CODE} since {since}",
        "detail": "" if ok else f"HTTP {err.get('status')}：{err.get('msg')}",
    }
    if not ok:
        log.error("FinMind 健檢失敗 —— 連 %s 最近 %d 天的日線都拿不到。"
                  "這不是某個資料集不開放，是整把 token／帳號的問題，本輪不再發任何請求。"
                  "上游回應：%s", CANARY_CODE, CANARY_DAYS,
                  prog["finmind_health"]["detail"] or "（沒有留下錯誤內容）")
        log.error("要處理的話：到 FinMind 網站重新產一把 token，"
                  "更新 GitHub Secrets 的 FINMIND_TOKEN，再手動觸發一次「歷史回補」。")
    _save_progress(prog)
    return ok


def plan_steps(name: str, today: date | None = None) -> list[dict]:
    if name not in PLANS:
        raise KeyError(f"沒有這個回補計畫：{name}（可用：{sorted(PLANS)}）")
    m = monthly_step(today)
    # ETF 的配息每月也要重抓（月配 ETF 每個月都有新公告；族群月更新那一步不含 ETF）
    return [dict(s) for s in PLANS[name]] + [m, {**m, "scope": "etf"}]


def _codes_for_scope(scope: str, limit: int | None) -> list[str]:
    if scope == "groups":
        m = loader.membership()
        if m.empty:
            log.warning("groups.yaml 沒有任何成分股，這一步沒有目標")
            return []
        return list(dict.fromkeys(m["code"].tolist()))
    if scope == "market":
        return market_codes()          # 刻意不吃 limit（見 market_codes）
    if scope == "etf":
        return etf_codes()
    return target_codes(limit)


def plan_is_done(prog: dict, name: str = "default", today: date | None = None) -> bool:
    """進度檔裡的計畫是否已補齊且仍在同一個月（月更新步驟的 tag 換了就算未完成）。"""
    flag = (prog.get("complete") or {}).get(f"plan:{name}")
    if not isinstance(flag, dict) or not flag.get("done"):
        return False
    return flag.get("month") == monthly_step(today)["tag"][1:]


def run_plan(name: str, limit: int | None, today: date | None = None) -> dict:
    """依序執行計畫的每一步；某一步額度用盡就停下，後面的步驟下一小時再來。

    每一步都會寫自己的 prog["complete"][datasets_key]；全部 done 才把
    prog["complete"]["plan:<name>"] 標成 done，並記下月更新的年月。"""
    steps = plan_steps(name, today)
    month = monthly_step(today)["tag"][1:]
    prog0 = _progress()

    # ★ 第一件事是健檢：整把 token 不通的話，後面每一個請求都是白燒額度。
    #   2026-09-19 就是少了這一步，三輪各燒掉 506 次額度、一列都沒寫進來。
    if not finmind_reachable(prog0):
        return {"done": False, "steps": {}, "stopped_at": None, "exhausted": False,
                "finmind_down": True, **{k: 0 for k in DATA_KEYS}}

    # 指數歷史只要 3 次請求，放最前面：它一補完，總覽的月 K／季 K 與季節性的
    # 大盤基準就都有東西了，不必等後面幾千檔個股跑完。
    idx_ok = backfill_indices(prog0)
    # 大盤 1H／4H 的分 K（Yahoo 不吃額度；台指期逐筆一天 1 次）。失敗不擋後面的個股回補。
    try:
        backfill_index_intraday(_progress())
    except Exception as exc:  # noqa: BLE001
        log.warning("指數分 K 回補失敗（不影響其他步驟）：%s", exc)
    results: dict[str, bool] = {}
    stopped_at: str | None = None
    totals = {k: 0 for k in DATA_KEYS}

    for n, step in enumerate(steps, 1):
        tag = step.get("tag")
        key = datasets_key_of(step["datasets"], step["start"], tag, step.get("scope"))
        log.info("計畫 %s 第 %d/%d 步：%s（起始 %s，範圍 %s）",
                 name, n, len(steps), key, step["start"], step.get("scope", "universe"))
        codes = _codes_for_scope(step.get("scope", "universe"), limit)
        summary = run(step["datasets"], limit, step["start"], codes=codes,
                      datasets_key=key, tag=tag, respect_time=not tag)
        for k in DATA_KEYS:
            totals[k] += summary.get(k, 0)
        # 用 run() 算好的同一個判準，不要在這裡再寫一次（兩邊不一致過一次就夠了）
        results[key] = bool(summary.get("finished"))
        if summary["exhausted"]:
            stopped_at = key
            log.warning("計畫 %s 在第 %d 步（%s）額度用盡，這一步還剩 %s 檔，其餘步驟下一輪接續",
                        name, n, key, summary.get("remaining"))
            break

    all_done = len(results) == len(steps) and all(results.values())
    # 法人每日續補：計畫的歷史步驟之外、每天一次（見 refresh_stale_inst）。不影響計畫的完成旗標。
    if stopped_at is None:
        try:
            refresh_stale_inst(_progress(), today, limit)
        except Exception as exc:  # noqa: BLE001
            log.warning("法人每日續補失敗（不影響其他步驟）：%s", exc)
    prog = _progress()
    prog.setdefault("complete", {})
    prog["complete"][f"plan:{name}"] = {
        "done": all_done,
        "at": datetime.now(timezone.utc).isoformat(),
        "month": month,
        "steps": results,
        "stopped_at": stopped_at,
    }
    _save_progress(prog)
    log.info("計畫 %s 結束：done=%s，各步 %s，寫入 %s", name, all_done, results,
             {k: v for k, v in totals.items() if v})
    return {"done": all_done and idx_ok, "steps": {**results, "index_ohlc": idx_ok},
            "stopped_at": stopped_at,
            "exhausted": stopped_at is not None, **totals}


def main() -> int:
    ap = argparse.ArgumentParser(description="FinMind 歷史回補")
    ap.add_argument("--limit", default="400",
                    help="本輪最多處理幾檔；留空或 0 表示不限")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--datasets", default=None,
                      help="price / inst / per / revenue / financial / balance / "
                           "dividend / divresult / margin / holding，可用 + 串接（預設 price+inst）；"
                           "logos ＝ 只抓公司 Logo；intraday ＝ 只補個股 60 分 K（Yahoo，全市場分批）")
    mode.add_argument("--plan", default=None, choices=sorted(PLANS),
                      help="改跑預設回補計畫（依序多步驟，忽略 --start；與 --datasets 二擇一）")
    ap.add_argument("--start", default=config.BACKFILL_START)
    args = ap.parse_args()

    if not config.FINMIND_TOKEN:
        log.warning("未設定 FINMIND_TOKEN，額度只有 300/hr，回補會很慢")

    limit_raw = (args.limit or "").strip()
    limit = int(limit_raw) if limit_raw.isdigit() and int(limit_raw) > 0 else None

    # 公司 Logo 與個股 60 分 K：都不吃 FinMind 額度，放在 FinMind 健檢之前，token 掛掉也照樣補。
    # `--datasets logos`／`intraday`／`logos+intraday` ＝ 只跑這幾步（計畫補齊後守門放行、或手動觸發用）；
    # `--limit` 在這裡不套用（兩者各有自己的每輪上限）。
    extras = set((args.datasets or "").split("+")) if args.datasets else set()
    only_extras = bool(extras) and extras <= EXTRA_DATASETS
    if args.plan or "logos" in extras:
        try:
            backfill_logos(_progress())
        except Exception as exc:  # noqa: BLE001
            log.warning("Logo 步驟失敗（不影響其他步驟）：%s", exc)
    if args.plan or "intraday" in extras:
        backfill_intraday_60m()
    if only_extras:
        return 0

    if args.plan:
        summary = run_plan(args.plan, limit)
    else:
        # 手動指定資料集也要先健檢：token 掛掉的話，逐檔跑只是在燒額度
        prog = _progress()
        if not finmind_reachable(prog):
            log.error("FinMind 不通，本輪不跑（原因見上一行與 backfill_progress.json 的 finmind_health）")
            return 0
        summary = run(args.datasets or "price+inst", limit, args.start)
    total = sum(summary[k] for k in DATA_KEYS)
    log.info("本輪共寫入 %d 列", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
