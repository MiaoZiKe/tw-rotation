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

    text = text.lstrip("﻿")
    if text.lstrip()[:1] == "<":
        # 反爬／維護頁會用 200 回 HTML；記下前 200 字，下次看 log 就知道發生什麼事
        log.warning("TDCC 回的是 HTML 不是 CSV（前 200 字）：%s", text[:200].replace("\n", " "))
        return pd.DataFrame()

    try:
        reader = csv.DictReader(io.StringIO(text))
        raw = list(reader)
    except Exception as exc:
        log.error("TDCC CSV 解析失敗：%s", exc)
        return pd.DataFrame()

    if not raw:
        log.warning("TDCC CSV 沒有資料列（前 200 字）：%s", text[:200].replace("\n", " "))
        return pd.DataFrame()

    # 表頭偶有 BOM／空白／全形百分比之類的差異，用「包含關鍵字」找欄位
    header = [str(k).strip().lstrip("﻿") for k in raw[0].keys() if k is not None]
    col = _resolve_columns(header)
    if col is None:
        log.warning("TDCC 表頭對不上，實際表頭：%s", header)
        return pd.DataFrame()

    rows = []
    for r in raw:
        r = {str(k).strip().lstrip("﻿"): v for k, v in r.items() if k is not None}
        code = clean_code(r.get(col["code"]))
        d = roc_to_iso(r.get(col["date"]))
        lvl = to_int(r.get(col["level"]))
        if not code or not d or lvl is None:
            continue
        rows.append({
            "date": d,
            "code": code,
            "level": lvl,
            "level_label": LEVEL_LABELS.get(lvl, str(lvl)),
            "holders": to_int(r.get(col["holders"])),
            "shares": to_float(r.get(col["shares"])),
            "pct": to_float(r.get(col["pct"])),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        log.warning("TDCC 有 %d 列但一列都解析不出來，表頭 %s，第一列 %s", len(raw), header, raw[0])
    else:
        log.info("TDCC 股權分散：%d 列，資料日期 %s", len(df), df["date"].iloc[0])
    return df


_COLUMN_HINTS = {
    "date": ("資料日期", "日期"),
    "code": ("證券代號", "代號"),
    "level": ("持股分級", "分級"),
    "holders": ("人數",),
    "shares": ("股數",),
    "pct": ("比例", "占集保庫存數"),
}


def _resolve_columns(header: list[str]) -> dict[str, str] | None:
    """把實際表頭對應到我們要的六個欄位；缺任何一個就回 None。"""
    out: dict[str, str] = {}
    for key, hints in _COLUMN_HINTS.items():
        match = next((h for h in header if any(h == x for x in hints)), None) \
            or next((h for h in header if any(x in h for x in hints)), None)
        if match is None:
            return None
        out[key] = match
    return out


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
