"""交易練習室（#lab）的靜態資料：每檔標的一個 JSON，前端按需載入（不在前端打任何外部 API）。

輸出到 site/data/lab/：
  index.json         可搜尋的標的清單（代號、名稱、種類、日 K 起訖、有沒有 60 分 K）
  s/<代號>.json      日 K（欄位式、整數、差分編碼，見 pack_daily）
  s/<代號>.60.json   60 分 K（只有 2023-09 之後；資料湖沒有就不產生）
  events.json        事件表（events_history.yaml），給事件分析用

為什麼用「整數＋差分」：全市場兩千檔、十幾年日 K，直接寫小數 JSON 會吃掉 Pages 的容量與部署時間。
價格 × 100 轉整數，開高低改存「與收盤的差」，日期存「與前一根相差的日曆日數」，每檔約 40～60 KB。
價格一律用總報酬還原價（price_adj，K 線／技術判讀同一份口徑）——回測不能被除權息的跳空騙到。
訊號用到的所有指標在前端算（site/lab/engine.js），這裡只出原料。
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import shutil
from pathlib import Path

import pandas as pd

from .. import config
from ..util import store

log = logging.getLogger(__name__)

EPOCH = dt.date(1970, 1, 1)
CODE_RE = re.compile(r"^\d{4,6}[A-Z]?$")
DAILY_FROM = "2016-01-01"       # 個股日 K 從這天起（Pages 容量有限；2016 起涵蓋疫情、升息、AI 行情等多個循環）
TOP60 = 500                     # 60 分 K 只給近期成交值前 500 名（其餘標的 60 分鈕反灰），省下約八成容量
INDEX_FROM = "2000-01-01"       # 加權／櫃買／台指期有全歷史
# 預覽分支吃的是正式站的資料、正式站還沒有 lab/ 目錄，所以另外 commit 一份小樣本到 site/lab/sample/
SAMPLE_CODES = ["2330", "2317", "2454", "2303", "2881", "2603", "0050", "3037", "2382", "3711"]


def _days(s: pd.Series) -> list[int]:
    d = pd.to_datetime(s.astype(str)).dt.date
    return [(x - EPOCH).days for x in d]


def pack_daily(df: pd.DataFrame, vol_div: float = 1000.0) -> dict:
    """df 欄位：date, open, high, low, close, volume（已按日期排序、無重複）。

    t：第一根的「日數（自 1970-01-01）」；dt：其後每根與前一根相差的日曆日數
    c：收盤×100 的差分（第一個是絕對值）；o／h／l：與當根收盤×100 的差；v：成交量（股數/1000 → 張）
    """
    df = df.dropna(subset=["close"]).copy()
    for col in ("open", "high", "low"):
        df[col] = df[col].where(df[col] > 0, df["close"])
    c = [int(round(x * 100)) for x in df["close"]]
    d = _days(df["date"])
    return {
        "t": d[0], "dt": [d[i] - d[i - 1] for i in range(1, len(d))],
        "c": [c[0]] + [c[i] - c[i - 1] for i in range(1, len(c))],
        "o": [int(round(a * 100)) - b for a, b in zip(df["open"], c)],
        "h": [int(round(a * 100)) - b for a, b in zip(df["high"], c)],
        "l": [int(round(a * 100)) - b for a, b in zip(df["low"], c)],
        "v": [int(round(x / vol_div)) for x in df["volume"].fillna(0)],
    }


def pack_60(g: pd.DataFrame, vdiv: float = 1000.0) -> dict | None:
    """60 分 K：ts 轉「自 1970 的分鐘數」差分；其餘同 pack_daily。價格不還原（60 分 K 只有近三年）。"""
    g = g.dropna(subset=["close"]).sort_values("ts").drop_duplicates("ts")
    if len(g) < 20:
        return None
    # 不用 astype("int64")：pandas 3 的時間單位可能是 us 而非 ns，直接轉整數會差一千倍
    ts = (pd.to_datetime(g["ts"], utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(minutes=1)
    t = [int(x) for x in ts]
    c = [int(round(x * 100)) for x in g["close"]]
    return {
        "t": t[0], "dt": [t[i] - t[i - 1] for i in range(1, len(t))],
        "c": [c[0]] + [c[i] - c[i - 1] for i in range(1, len(c))],
        "o": [int(round(a * 100)) - b for a, b in zip(g["open"], c)],
        "h": [int(round(a * 100)) - b for a, b in zip(g["high"], c)],
        "l": [int(round(a * 100)) - b for a, b in zip(g["low"], c)],
        "v": [int(round(x / vdiv)) for x in g["volume"].fillna(0)],
    }


def tx_60(ii: pd.DataFrame) -> pd.DataFrame | None:
    """台指期 60 分 K：資料湖只有近月連續的「1 分 K」（index_intraday，symbol=FUT，日盤 08:45～13:45），而且只從 2026-08 才開始存。
    合成成每小時一根（以 :45 為界，每天 5 根：08:45、09:45、10:45、11:45、12:45），開＝第一分、高低＝極值、收＝最後一分、量＝加總。
    不納入夜盤（FUT_N）。回傳含 ts／open／high／low／close／volume 欄的表；資料不夠回 None。"""
    f = ii[(ii["symbol"] == "FUT") & (ii["interval"] == "1m")].dropna(subset=["close"]).copy()
    if len(f) < 100:
        return None
    f["t"] = pd.to_datetime(f["ts"], utc=True).dt.tz_convert("Asia/Taipei")
    f = f.sort_values("t").drop_duplicates("t").set_index("t")
    g = f.resample("60min", origin="start_day", offset="45min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    g = g.dropna(subset=["close"]).reset_index().rename(columns={"t": "ts"})
    return g if len(g) >= 20 else None


def _dump(path: Path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    path.write_text(s, encoding="utf-8")
    return len(s)


def export_lab(price_adj: pd.DataFrame, names: dict, markets: dict, out_dir: Path | None = None,
               m60: pd.DataFrame | None = None, only: list[str] | None = None) -> dict:
    out = Path(out_dir or (config.SITE_DATA / "lab"))
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    total = 0

    # ---- 指數與台指期（全歷史）。volume 欄：指數放成交金額（元→百萬）、台指期放口數
    idx = store.read("index_ohlc")
    idx = idx[idx["date"].astype(str) >= INDEX_FROM]
    spec = [("TAIEX", "TSE", "加權指數", "index", 1e6, "成交金額（百萬）"),
            ("OTC", "OTC", "櫃買指數", "index", 1e6, "成交金額（百萬）"),
            ("TX", "FUT", "台指期（近月連續）", "fut", 1.0, "口數")]
    for code, sym, nm, kind, vdiv, vu in spec:
        g = idx[idx["symbol"] == sym].sort_values("date").drop_duplicates("date")
        vcol = "turnover" if kind == "index" else "volume"
        g = g.assign(volume=pd.to_numeric(g[vcol], errors="coerce"))
        if len(g) < 100:
            continue
        o = {"c": code, "n": nm, "k": kind, "vu": vu, "d": pack_daily(g, vdiv)}
        total += _dump(out / "s" / f"{code}.json", o)
        items.append({"c": code, "n": nm, "k": kind, "a": str(g["date"].iloc[0]), "b": str(g["date"].iloc[-1]), "h60": False})

    # ---- 台指期 60 分 K（只有 2026-08 起，前端會標示「僅自 xx 起」）
    try:
        tx = tx_60(store.read("index_intraday"))
        k60 = pack_60(tx, vdiv=1.0) if tx is not None else None
        if k60:
            total += _dump(out / "s" / "TX.60.json", {"c": "TX", "d": k60})
            for it in items:
                if it["c"] == "TX":
                    it["h60"] = True
                    it["a60"] = str(pd.to_datetime(tx["ts"].iloc[0]).date())
    except Exception as exc:  # noqa: BLE001 —— 台指期分 K 壞了只影響 60 分鈕
        log.warning("交易練習室台指期 60 分 K 產出失敗：%s", exc)

    # ---- 個股／ETF
    p = price_adj[price_adj["date"].astype(str) >= DAILY_FROM]
    latest = str(p["date"].max())
    cut = (pd.to_datetime(latest) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    m60g: dict = {}
    if m60 is not None and not m60.empty:
        m60g = {str(c): g for c, g in m60.groupby(m60["code"].astype(str))}
    recent = p[p["date"].astype(str) >= (pd.to_datetime(latest) - pd.Timedelta(days=60)).strftime("%Y-%m-%d")]
    top60 = set(recent.groupby(recent["code"].astype(str))["turnover"].sum().nlargest(TOP60).index)
    topchip = set(recent.groupby(recent["code"].astype(str))["turnover"].sum().nlargest(CHIP_N).index)
    for code, g in p.groupby(p["code"].astype(str)):
        if not CODE_RE.match(code) or (only and code not in only):
            continue
        g = g.sort_values("date").drop_duplicates("date")
        g = g[g["close"] > 0]
        if len(g) < 60 or str(g["date"].iloc[-1]) < cut:
            continue
        nm = names.get(code)
        if not nm:
            nm = g["name"].dropna().iloc[-1] if g["name"].notna().any() else code
        kind = "etf" if code.startswith("00") else "stock"
        o = {"c": code, "n": nm, "k": kind, "vu": "張", "d": pack_daily(g)}
        total += _dump(out / "s" / f"{code}.json", o)
        h60 = False
        if code in m60g and (code in top60 or only):
            k60 = pack_60(m60g[code])
            if k60:
                total += _dump(out / "s" / f"{code}.60.json", {"c": code, "d": k60})
                h60 = True
        items.append({"c": code, "n": nm, "k": kind, "m": markets.get(code, ""), "a": str(g["date"].iloc[0]),
                      "b": str(g["date"].iloc[-1]), "h60": h60})
    total += export_us(out)
    try:
        total += export_chips(p, items, out, topchip, only)
    except Exception as exc:  # noqa: BLE001 —— 籌碼壞了只影響籌碼策略，K 線與回測照常
        log.warning("交易練習室籌碼資料產出失敗：%s", exc)
    _dump(out / "index.json", {"updated": latest, "items": items})
    log.info("交易練習室：%d 檔、合計 %.1f MB → %s", len(items), total / 1e6, out)
    return {"n": len(items), "bytes": total}


CHIP_N = 1000                   # 籌碼檔只給近期成交值前 1000 名（含 ETF 後約 850 檔個股，每檔約 30 KB，合計約 26 MB）
# 欄位 → (來源表, 來源欄, 單位換算)。三大法人是買賣超股數、融資融券是餘額股數、當沖是成交股數；一律換成「張」。
CHIP_FIELDS = {"fn": ("inst_daily", "_fn"), "tr": ("inst_daily", "trust"), "dl": ("inst_daily", "_dl"),
               "mb": ("margin_daily", "margin_balance"), "sb": ("margin_daily", "short_balance"),
               "dt": ("daytrade_daily", "daytrade_volume")}


def _rev_series(rev: pd.DataFrame, dates: list[str]) -> dict[str, pd.Series] | None:
    """月營收三條序列，全部對齊到每個交易日（標準策略「營收動能」「營收年增＋公布後短窗」用）：
      rv＝近 3 月均營收 ÷ 近 12 月均營收 × 100（%）
      ry＝最新一期月營收年增率（%）＝ 本月 ÷ 去年同月 − 1
      ra＝最新一期營收「公布後第幾個交易日」（公布日當天＝0，沒資料或超過 99 一律 99）
    可用日一律用法定期限：某月營收最晚次月 10 日公布（config.REVENUE_DEADLINE_DAY），所以「次月 10 日起」的第一根 K 才用得到；
    不用公司實際公告日（早報的日子不能當成全市場都知道）。月份用連續日曆月補齊（缺月是 NaN，不會把不相鄰的月份當成相鄰）。
    訊號在該日收盤後產生、下一根開盤成交，所以 10 日當天收盤看到、11 日開盤進場（和淘汰賽報告 docs/strategy_lab/tournament 同口徑）。"""
    r = rev.dropna(subset=["revenue"]).drop_duplicates("ym", keep="last")
    if len(r) < 13:
        return None
    r = r.assign(ym=r["ym"].astype(str)).set_index("ym").sort_index()
    full = pd.period_range(r.index.min(), r.index.max(), freq="M").astype(str)
    v = pd.to_numeric(r["revenue"], errors="coerce").reindex(full)
    m3, m12 = v.rolling(3).mean(), v.rolling(12).mean()
    day = config.REVENUE_DEADLINE_DAY
    avail = pd.Index([(pd.Period(ym, "M") + 1).strftime("%Y-%m") + f"-{day:02d}" for ym in full])
    idx = pd.Index(dates)

    def daily(x: pd.Series) -> pd.Series:
        s_ = pd.Series(x.to_numpy(), index=avail)
        s_ = s_[~s_.index.duplicated(keep="last")]
        return s_.reindex(s_.index.union(idx)).ffill().reindex(idx)

    # 公布後第幾個交易日：每個「可用日」落在哪一根（該日或之後第一根）
    first_day = str(idx[0]) if len(idx) else ""
    pos = idx.searchsorted([a_ for a_ in avail if a_ >= first_day])      # 比資料第一天還早公布的期別數不到「第幾個交易日」，不算
    pos = sorted({int(q) for q in pos if q < len(idx)})
    age, last, ps = [], None, set(pos)
    for i in range(len(idx)):
        if i in ps:
            last = i
        age.append(99 if last is None else min(99, i - last))
    return {"rv": daily(m3 / m12 * 100), "ry": daily((v / v.shift(12) - 1) * 100), "ra": pd.Series(age, index=idx)}


def export_us(out: Path) -> int:
    """美股前一晚漲跌：{sox, ixic, tsm: {d:[日數], r:[漲跌 %]}}。日數＝自 1970 的日曆日數。
    前端對每根台股 K 棒只取「日期嚴格早於這一天」的最近一筆（T-1，不含同一個日曆日），所以台股盤中決策用不到當天夜裡的美股。"""
    try:
        ig = store.read("intl_daily")
    except Exception as exc:  # noqa: BLE001
        log.warning("交易練習室美股資料讀取失敗：%s", exc)
        return 0
    obj = {}
    for key, sym in (("sox", "^SOX"), ("ixic", "^IXIC"), ("tsm", "TSM")):
        g = ig[ig["symbol"] == sym].drop_duplicates("date").sort_values("date")
        c = pd.to_numeric(g["close"], errors="coerce").to_numpy()
        d = [(dt.date.fromisoformat(str(x)[:10]) - EPOCH).days for x in g["date"]]
        r = [(i, round(float(c[i] / c[i - 1] - 1) * 100, 2)) for i in range(1, len(c)) if c[i] == c[i] and c[i - 1] == c[i - 1] and c[i - 1] > 0]
        obj[key] = {"d": [d[i] for i, _ in r], "r": [x for _, x in r]}
    return _dump(out / "us.json", obj)


def export_chips(p: pd.DataFrame, items: list, out: Path, rank_set=None, only=None) -> int:
    """每檔一個 c/<代號>.json：{s:{欄位:起點列號}, fn:[…], tr:[…], …}，各序列對齊該檔日 K 的列（同樣的日期篩選與去重）。
    為什麼用「起點列號＋連續陣列」：融資從 2021、當沖從 2025 才有，用 null 補會變很肥；起點之前就是沒有資料，前端補 NaN。
    資料當天沒紀錄的法人買賣超補 0（沒成交＝沒買賣超），餘額類沿用前一日。集保大戶只有 2026-09 起、不足以回測，故意不出。
    """
    cand = [it["c"] for it in items if it["k"] == "stock" and ((only and it["c"] in only) or (not only and it["c"] in (rank_set or ())))]
    if not cand:
        return 0
    cs = set(cand)
    frames = {}
    for t in ("inst_daily", "margin_daily", "daytrade_daily"):
        df = store.read(t)
        df = df[(df["date"].astype(str) >= DAILY_FROM) & df["code"].astype(str).isin(cs)]
        df = df.assign(code=df["code"].astype(str), date=df["date"].astype(str))
        if t == "inst_daily":
            # 2018 以前資料湖的 foreign_total／dealer 欄位幾乎是空的：外資改用「外陸資 foreign」補、自營商改用「自買＋避險」補
            # （外資自營商那一小塊早年缺，口徑略有差異；和淘汰賽報告 docs/strategy_lab/tournament 的處理一致）
            df = df.assign(_fn=pd.to_numeric(df["foreign_total"], errors="coerce").fillna(pd.to_numeric(df["foreign"], errors="coerce")),
                           _dl=pd.to_numeric(df["dealer"], errors="coerce").fillna(pd.to_numeric(df["dealer_self"], errors="coerce").fillna(0) + pd.to_numeric(df["dealer_hedge"], errors="coerce").fillna(0)))
        frames[t] = {c: g.drop_duplicates("date", keep="last").set_index("date") for c, g in df.groupby("code")}
    try:
        rv_all = store.read("revenue_monthly")
        rv_all = rv_all[rv_all["code"].astype(str).isin(cs)].assign(code=lambda d: d["code"].astype(str))
        rv_by = {c: g for c, g in rv_all.groupby("code")}
    except Exception as exc:  # noqa: BLE001 —— 月營收壞了只影響「營收動能」條件
        log.warning("交易練習室月營收讀取失敗：%s", exc)
        rv_by = {}
    total = 0
    for code in cand:
        g = p[p["code"].astype(str) == code].sort_values("date").drop_duplicates("date")
        g = g[g["close"] > 0]
        dates = g["date"].astype(str).tolist()
        o: dict = {"c": code, "s": {}}
        for f, (t, col) in CHIP_FIELDS.items():
            src = frames[t].get(code)
            if src is None or col not in src.columns or src.empty:
                continue
            ser = pd.to_numeric(src[col], errors="coerce").reindex(dates)
            first = ser.first_valid_index()
            if first is None:
                continue
            i0 = dates.index(first)
            ser = ser.iloc[i0:]
            ser = ser.fillna(0) if t == "inst_daily" else ser.ffill().fillna(0)
            o["s"][f] = i0
            o[f] = [int(round(x / 1000)) for x in ser.tolist()]
        if code in rv_by:
            rs = _rev_series(rv_by[code], dates)
            first = rs["rv"].first_valid_index() if rs is not None else None
            if first is not None:
                i0 = dates.index(first)
                for k, nd in (("rv", 0), ("ry", 1), ("ra", 0)):
                    x = rs[k].iloc[i0:]
                    o["s"][k] = i0
                    # rv 單位：%（118＝近 3 月均是近 12 月均的 1.18 倍）；ry 單位：%（1 位小數）；ra：公布後第幾個交易日（99＝沒資料或太久）
                    o[k] = [(round(float(v_), nd) if nd else int(round(v_))) if v_ == v_ and abs(v_) != float("inf") else (0 if k != "ry" else 0.0) for v_ in x.tolist()]      # NaN／無限大（去年同月營收 0）一律當沒有資料
        if o["s"]:
            total += _dump(out / "c" / f"{code}.json", o)
            for it in items:
                if it["c"] == code:
                    it["ch"] = True
    log.info("交易練習室籌碼：%d 檔、%.1f MB", len(cand), total / 1e6)
    return total


def export_events(out_dir: Path | None = None) -> int:
    """事件表：events_history.yaml（人工維護、每筆附出處）。"""
    import yaml
    out = Path(out_dir or (config.SITE_DATA / "lab"))
    src = Path(__file__).resolve().parents[1] / "groups" / "events_history.yaml"
    doc = yaml.safe_load(src.read_text(encoding="utf-8")) if src.exists() else {}
    doc = doc or {}
    _dump(out / "events.json", {"types": doc.get("types", {}), "events": doc.get("events", [])})
    return len(doc.get("events", []))


def build(price_adj, names, markets, m60=None):
    try:
        if m60 is None:
            m60 = store.read("intraday_60m")      # 全部月份（2023-09 起）；只在這裡讀一次
        r = export_lab(price_adj, names, markets, m60=m60)
        export_events()
        return r
    except Exception as exc:  # noqa: BLE001 —— 練習室資料壞了不能拖垮整份 payload
        log.warning("交易練習室資料產出失敗：%s", exc)
        return None


def main(argv=None):
    """單獨產生交易練習室資料（不必重算整份 payload）：
    python -m pipeline.compute.lab                 → site/data/lab/（全部標的）
    python -m pipeline.compute.lab --sample        → site/lab/sample/（預覽分支用的小樣本，會 commit）
    """
    import argparse

    from . import fundamental
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s | %(message)s")
    price = fundamental.clean_price(store.read("price_daily"))
    actions = fundamental.corporate_actions(price, store.read("dividend_results"), store.read("dividend_events"))
    price_adj = fundamental.adjust_prices(price, actions, mode="total")
    company = store.read("company_info")
    names = company.dropna(subset=["name"]).drop_duplicates("code", keep="last").set_index("code")["name"].to_dict()
    markets = company.dropna(subset=["market"]).drop_duplicates("code", keep="last").set_index("code")["market"].to_dict()
    m60 = store.read("intraday_60m")
    if a.sample:
        out = Path(__file__).resolve().parents[2] / "site" / "lab" / "sample"
        only = SAMPLE_CODES
    else:
        out, only = None, None
    export_lab(price_adj, names, markets, out_dir=out, m60=m60, only=only)
    export_events(out)


if __name__ == "__main__":
    main()
