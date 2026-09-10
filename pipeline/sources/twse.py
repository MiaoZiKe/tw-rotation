"""證交所 OpenAPI（openapi.twse.com.tw）—— 每日增量的主力來源。

重要特性（2026-09-10 實測）：
- 免 API key、無流量限制、屬政府開放資料，不受 TWSE 官網禁爬條款限制
- 每個端點都只有「最新一期快照」，加 ?date= 無效 → 歷史只能靠每天存
- 落後官網一個交易日（T-1）
- 日期是民國格式、金額多為千元、所有欄位都是字串
- MI_MARGN 沒有日期欄位，需由同批次的行情日期補上
"""
from __future__ import annotations

import logging

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, roc_to_iso, roc_ym_to_iso, to_float, to_int

log = logging.getLogger(__name__)

# 證交所產業別代碼（t187ap03_L 用代碼制，t187ap05_L / t187ap14_L 用名稱制）
INDUSTRY_CODES = {
    "01": "水泥工業", "02": "食品工業", "03": "塑膠工業", "04": "紡織纖維",
    "05": "電機機械", "06": "電器電纜", "08": "玻璃陶瓷", "09": "造紙工業",
    "10": "鋼鐵工業", "11": "橡膠工業", "12": "汽車工業", "14": "建材營造",
    "15": "航運業", "16": "觀光餐旅", "17": "金融保險", "18": "貿易百貨",
    "19": "綜合", "20": "其他", "21": "化學工業", "22": "生技醫療業",
    "23": "油電燃氣業", "24": "半導體業", "25": "電腦及週邊設備業",
    "26": "光電業", "27": "通信網路業", "28": "電子零組件業",
    "29": "電子通路業", "30": "資訊服務業", "31": "其他電子業",
    "32": "文化創意業", "33": "農業科技業", "34": "電子商務",
    "35": "綠能環保", "36": "數位雲端", "37": "運動休閒", "38": "居家生活",
}


def _fetch(key: str) -> list[dict] | None:
    url = config.TWSE_OPENAPI + config.TWSE_ENDPOINTS[key]
    data = http.get(url)
    if not isinstance(data, list) or not data:
        log.warning("TWSE %s 回應空白或格式非預期", key)
        return None
    return data


def _pick(row: dict, *names: str) -> str | None:
    """依候選名稱找欄位。端點欄位名偶有微調，這層讓抓取不會因為改名而整個掛掉。"""
    for n in names:
        if n in row:
            return row[n]
    # 退而求其次：去空白後比對
    norm = {str(k).strip(): v for k, v in row.items()}
    for n in names:
        if n in norm:
            return norm[n]
    return None


# ------------------------------------------------------------------ 個股日行情

def price_daily() -> pd.DataFrame:
    """全市場上市個股日行情。一支請求拿 1,000+ 檔，是整條管線最划算的來源。"""
    raw = _fetch("price_daily")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(_pick(r, "Code", "證券代號"))
        d = roc_to_iso(_pick(r, "Date", "日期"))
        if not code or not d:
            continue
        rows.append({
            "date": d,
            "code": code,
            "name": _pick(r, "Name", "證券名稱"),
            "market": "TWSE",
            "open": to_float(_pick(r, "OpeningPrice")),
            "high": to_float(_pick(r, "HighestPrice")),
            "low": to_float(_pick(r, "LowestPrice")),
            "close": to_float(_pick(r, "ClosingPrice")),
            "change": to_float(_pick(r, "Change")),
            "volume": to_int(_pick(r, "TradeVolume")),        # 股
            "turnover": to_float(_pick(r, "TradeValue")),     # 元
            "transactions": to_int(_pick(r, "Transaction")),
        })
    df = pd.DataFrame(rows)
    log.info("TWSE 日行情：%d 檔，日期 %s", len(df), df["date"].iloc[0] if len(df) else "—")
    return df


# ------------------------------------------------------------------ 評價指標

def valuation_daily() -> pd.DataFrame:
    """本益比 / 殖利率 / 股價淨值比。M2 同業本益比分位的原料。"""
    raw = _fetch("valuation_daily")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(_pick(r, "Code", "證券代號"))
        d = roc_to_iso(_pick(r, "Date", "日期"))
        if not code or not d:
            continue
        rows.append({
            "date": d,
            "code": code,
            "pe": to_float(_pick(r, "PEratio", "本益比")),
            "dividend_yield": to_float(_pick(r, "DividendYield", "殖利率(%)")),
            "pb": to_float(_pick(r, "PBratio", "股價淨值比")),
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 融資融券

def margin_daily(trade_date: str | None = None) -> pd.DataFrame:
    """融資融券餘額。

    這支端點沒有日期欄位，必須由呼叫端把當批行情的日期傳進來 ——
    否則資料會無法對齊，而且去重會失效。
    """
    if not trade_date:
        log.error("margin_daily 需要 trade_date，否則無法建立主鍵，本次跳過")
        return pd.DataFrame()

    raw = _fetch("margin_daily")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(_pick(r, "股票代號", "Code"))
        if not code:
            continue
        prev_m = to_int(_pick(r, "融資前日餘額"))
        curr_m = to_int(_pick(r, "融資今日餘額"))
        prev_s = to_int(_pick(r, "融券前日餘額"))
        curr_s = to_int(_pick(r, "融券今日餘額"))
        rows.append({
            "date": trade_date,
            "code": code,
            "margin_balance": curr_m,
            "margin_change": (curr_m - prev_m) if (curr_m is not None and prev_m is not None) else None,
            "short_balance": curr_s,
            "short_change": (curr_s - prev_s) if (curr_s is not None and prev_s is not None) else None,
            "margin_buy": to_int(_pick(r, "融資買進")),
            "margin_sell": to_int(_pick(r, "融資賣出")),
            "short_sell": to_int(_pick(r, "融券賣出")),
            "short_cover": to_int(_pick(r, "融券買進")),
            "offset": to_int(_pick(r, "資券互抵")),
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 類股指數

def index_daily() -> pd.DataFrame:
    """各類股指數收盤。這是族群強弱最權威的官方基準。"""
    raw = _fetch("index_daily")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        name = _pick(r, "指數", "Index")
        d = roc_to_iso(_pick(r, "日期", "Date"))
        if not name or not d:
            continue
        rows.append({
            "date": d,
            "index": str(name).strip(),
            "close": to_float(_pick(r, "收盤指數")),
            "change_pct": to_float(_pick(r, "漲跌百分比")),
            "change_pts": to_float(_pick(r, "漲跌點數")),
        })
    return pd.DataFrame(rows)


def market_daily() -> pd.DataFrame:
    """大盤成交統計。FMTQIK 是少數會回傳當月至今的端點。"""
    raw = _fetch("market_daily")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        d = roc_to_iso(_pick(r, "Date", "日期"))
        if not d:
            continue
        rows.append({
            "date": d,
            "volume": to_int(_pick(r, "TradeVolume")),
            "turnover": to_float(_pick(r, "TradeValue")),
            "transactions": to_int(_pick(r, "Transaction")),
            "taiex": to_float(_pick(r, "TAIEX")),
            "change": to_float(_pick(r, "Change")),
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 基本面

def company_info() -> pd.DataFrame:
    """上市公司基本資料。產業別在這裡是代碼制，轉成名稱後與其他表對齊。"""
    raw = _fetch("company_info")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(_pick(r, "公司代號", "Code"))
        if not code:
            continue
        ind_raw = _pick(r, "產業別")
        ind = str(ind_raw).strip() if ind_raw else ""
        rows.append({
            "code": code,
            "name": _pick(r, "公司簡稱", "公司名稱"),
            "full_name": _pick(r, "公司名稱"),
            "market": "TWSE",
            "industry": INDUSTRY_CODES.get(ind.zfill(2), ind or None),
            "industry_code": ind or None,
            "listed_date": roc_to_iso(_pick(r, "上市日期")),
            "capital": to_float(_pick(r, "實收資本額")),
            "chairman": _pick(r, "董事長"),
            "website": _pick(r, "網址"),
        })
    return pd.DataFrame(rows)


def revenue_monthly() -> pd.DataFrame:
    """月營收。這支端點的產業別是名稱制，可直接用。"""
    raw = _fetch("revenue_monthly")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(_pick(r, "公司代號"))
        ym = roc_ym_to_iso(_pick(r, "資料年月"))
        if not code or not ym:
            continue
        rows.append({
            "ym": ym,
            "code": code,
            "name": _pick(r, "公司名稱"),
            "industry": _pick(r, "產業別"),
            # 營收欄位單位為千元，統一換算成元
            "revenue": to_float(_pick(r, "營業收入-當月營收"), thousand_scale=True),
            "revenue_prev_month": to_float(_pick(r, "營業收入-上月營收"), thousand_scale=True),
            "revenue_last_year": to_float(_pick(r, "營業收入-去年當月營收"), thousand_scale=True),
            "mom_pct": to_float(_pick(r, "上月比較增減(%)")),
            "yoy_pct": to_float(_pick(r, "去年同月增減(%)")),
            "cum_revenue": to_float(_pick(r, "累計營業收入-當月累計"), thousand_scale=True),
            "cum_last_year": to_float(_pick(r, "累計營業收入-去年累計"), thousand_scale=True),
            "cum_yoy_pct": to_float(_pick(r, "前期比較增減(%)")),
        })
    return pd.DataFrame(rows)


def financial_q() -> pd.DataFrame:
    """季報精簡表：EPS、營收、營益、稅後淨利，且自帶產業別。"""
    raw = _fetch("financial_q")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(_pick(r, "公司代號"))
        year = to_int(_pick(r, "年度"))
        quarter = to_int(_pick(r, "季別"))
        if not code or year is None or quarter is None:
            continue
        rows.append({
            "year": year + 1911 if year < 1911 else year,
            "quarter": quarter,
            "code": code,
            "name": _pick(r, "公司名稱"),
            "industry": _pick(r, "產業別"),
            "eps": to_float(_pick(r, "基本每股盈餘(元)", "基本每股盈餘（元）")),
            "revenue": to_float(_pick(r, "營業收入"), thousand_scale=True),
            "operating_income": to_float(_pick(r, "營業利益"), thousand_scale=True),
            "non_operating": to_float(_pick(r, "營業外收入及支出"), thousand_scale=True),
            "net_income": to_float(_pick(r, "稅後淨利"), thousand_scale=True),
        })
    return pd.DataFrame(rows)


def dividend() -> pd.DataFrame:
    """股利分派。欄位名稱在這支端點較不穩定，用寬鬆比對。"""
    raw = _fetch("dividend")
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(_pick(r, "公司代號", "Code"))
        year = to_int(_pick(r, "股利所屬年度", "年度"))
        if not code or year is None:
            continue
        rows.append({
            "code": code,
            "year": year + 1911 if year < 1911 else year,
            "cash_dividend": to_float(_pick(r, "現金股利", "股東配發-現金股利(元/股)")),
            "stock_dividend": to_float(_pick(r, "股票股利", "股東配發-股票股利(元/股)")),
            "ex_date": roc_to_iso(_pick(r, "除息交易日", "除權交易日")),
        })
    return pd.DataFrame(rows)
