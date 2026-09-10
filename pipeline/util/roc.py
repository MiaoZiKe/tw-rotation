"""民國日期與證交所數值格式的轉換。

證交所 OpenAPI 有三個一致的坑，這裡集中處理：
1. 日期是民國格式，而且有兩種寫法：`1150909` 與 `115年09月10日`
2. 所有欄位（含數字）都是字串，且千分位有逗號、空值是 "--" 或 "" 或 "N/A"
3. 金額單位多為新台幣「千元」
"""
from __future__ import annotations

import re
from datetime import date

_ROC_COMPACT = re.compile(r"^(\d{3})(\d{2})(\d{2})$")
_ROC_CJK = re.compile(r"^(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日$")
_ROC_SLASH = re.compile(r"^(\d{2,3})/(\d{1,2})/(\d{1,2})$")
_AD_DASH = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_AD_COMPACT = re.compile(r"^(\d{4})(\d{2})(\d{2})$")

# 空值的各種寫法，實測都出現過
_NULLS = {"", "--", "-", "N/A", "n/a", "null", "None", "不適用", "無", "---"}


def roc_to_date(value: str | None) -> date | None:
    """把證交所各種日期寫法轉成 datetime.date；無法解析回 None。"""
    if value is None:
        return None
    s = str(value).strip().replace(" ", "")
    if s in _NULLS:
        return None

    for pat, roc in ((_ROC_COMPACT, True), (_ROC_CJK, True), (_ROC_SLASH, True),
                     (_AD_DASH, False), (_AD_COMPACT, False)):
        m = pat.match(s)
        if not m:
            continue
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if roc:
            # 民國年一定小於 1911；若已經是西元（例如 TDCC 的 20260904）就不加
            y += 1911
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def roc_to_iso(value: str | None) -> str | None:
    d = roc_to_date(value)
    return d.isoformat() if d else None


def roc_ym_to_iso(value: str | None) -> str | None:
    """民國年月 `11507` -> `2026-07`。"""
    if value is None:
        return None
    s = str(value).strip()
    if s in _NULLS or not s.isdigit() or len(s) not in (5, 6):
        return None
    y, m = int(s[:-2]) + 1911, int(s[-2:])
    if not 1 <= m <= 12:
        return None
    return f"{y:04d}-{m:02d}"


def to_float(value, *, thousand_scale: bool = False) -> float | None:
    """證交所數字字串 -> float。

    thousand_scale=True 時把「千元」換算成「元」。
    """
    if value is None:
        return None
    s = str(value).strip().replace(",", "").replace("%", "")
    if s in _NULLS:
        return None
    # 有些欄位用全形加減號，或用括號表示負數
    s = s.replace("＋", "+").replace("－", "-").replace("−", "-")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    if s in ("+", "-", "X", "x"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v * 1000.0 if thousand_scale else v


def to_int(value) -> int | None:
    v = to_float(value)
    return int(v) if v is not None else None


def clean_code(value) -> str | None:
    """股票代號正規化：去空白、去 BOM、保留原始零開頭（如 0050）。"""
    if value is None:
        return None
    s = str(value).strip().strip("﻿").strip('"')
    return s or None


def is_common_stock(code: str | None) -> bool:
    """判斷是否為一般上市櫃普通股（4 位數字），排除權證、ETF、特別股、存託憑證。"""
    if not code:
        return False
    return len(code) == 4 and code.isdigit() and not code.startswith("0")


def is_etf(code: str | None) -> bool:
    """台股 ETF 代號一律以 00 開頭，長度 4–6：0050、00878、00631L（正2）、00981A（主動式）。"""
    if not code:
        return False
    return code.startswith("00") and 4 <= len(code) <= 6
