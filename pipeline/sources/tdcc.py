"""集保結算所股權分散表（每週五基準，次週初公布）。

這是全案取得最順的來源：純 CSV、免 key、無反爬。
持股分級 1–15 由小到大，15 為「1,000 張以上」的大戶級距 —— M1 的
「千張大戶週變化」就靠這一級。
"""
from __future__ import annotations

import csv
import io
import logging

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, roc_to_iso, to_float, to_int

log = logging.getLogger(__name__)

# 集保持股分級對照（單位：股）
LEVEL_LABELS = {
    1: "1-999", 2: "1,000-5,000", 3: "5,001-10,000", 4: "10,001-15,000",
    5: "15,001-20,000", 6: "20,001-30,000", 7: "30,001-40,000",
    8: "40,001-50,000", 9: "50,001-100,000", 10: "100,001-200,000",
    11: "200,001-400,000", 12: "400,001-600,000", 13: "600,001-800,000",
    14: "800,001-1,000,000", 15: "1,000,001以上", 16: "差異數調整",
    17: "合計",
}
BIG_HOLDER_LEVELS = (13, 14, 15)  # 600 張以上視為大戶
THOUSAND_LOT_LEVEL = 15           # 千張以上


def shareholding_weekly() -> pd.DataFrame:
    """抓最新一週的股權分散表。"""
    text = http.get(config.TDCC_URL, expect_json=False)
    if not text:
        log.warning("TDCC 抓取失敗")
        return pd.DataFrame()

    # 集保的 CSV 帶 UTF-8 BOM。不剝掉的話 DictReader 的第一個欄名會是
    # '﻿資料日期'，r.get("資料日期") 就永遠是 None，
    # 於是每一列都被下面的 skip 條件濾掉，整張表靜悄悄地變成空的。
    text = text.lstrip("﻿")

    try:
        reader = csv.DictReader(io.StringIO(text))
        raw = list(reader)
    except Exception as exc:
        log.error("TDCC CSV 解析失敗：%s", exc)
        return pd.DataFrame()

    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(r.get("證券代號"))
        d = roc_to_iso(r.get("資料日期"))
        lvl = to_int(r.get("持股分級"))
        if not code or not d or lvl is None:
            continue
        rows.append({
            "date": d,
            "code": code,
            "level": lvl,
            "level_label": LEVEL_LABELS.get(lvl, str(lvl)),
            "holders": to_int(r.get("人數")),
            "shares": to_float(r.get("股數")),
            "pct": to_float(r.get("占集保庫存數比例%")),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        log.info("TDCC 股權分散：%d 列，資料日期 %s", len(df), df["date"].iloc[0])
    return df


def big_holder_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """由分級明細算出每檔的大戶持股比例，這是實際要用的指標。"""
    if df.empty:
        return pd.DataFrame()
    big = df[df["level"].isin(BIG_HOLDER_LEVELS)]
    thousand = df[df["level"] == THOUSAND_LOT_LEVEL]

    g = (big.groupby(["date", "code"], as_index=False)["pct"].sum()
            .rename(columns={"pct": "big_holder_pct"}))
    t = (thousand.groupby(["date", "code"], as_index=False)["pct"].sum()
              .rename(columns={"pct": "thousand_lot_pct"}))
    return g.merge(t, on=["date", "code"], how="outer")
