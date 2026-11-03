"""官方「非擔任主管職務之全時員工薪資」（證交所／櫃買中心 ESG 人力發展彙總，政府資料開放授權條款第 1 版）。

為什麼走 openapi.twse.com.tw：CLAUDE.md 白名單內的端點；櫃買的同類資料集（data.gov.tw #156379）
其 API 說明文件同樣指向證交所 swagger，上櫃端點在 TWSE swagger 以 _O 結尾（t187ap03_O 也是這樣用）。
端點代號沒有實測過（開發容器連不到外網），所以不寫死：先讀 swagger.json，挑摘要含「人力發展」的路徑，
欄位名也用關鍵字比對（含「非擔任主管」＋「平均」／「中位數」），改名也不會整個掛掉。
單位：原始是仟元／人，這裡換成「萬元／年」（÷10）。口徑是非主管全時員工，不可跟財報全體員工薪酬混用。
"""
from __future__ import annotations

import logging
import re

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, to_float

log = logging.getLogger(__name__)

SWAGGER = config.TWSE_OPENAPI + "/swagger.json"
KEYWORD = "人力發展"


def find_paths(swagger: dict) -> list[tuple[str, str]]:
    """回傳 [(路徑, 市場別 'TWSE'|'TPEX')]。摘要或描述含「人力發展」才收；_O 結尾視為上櫃。"""
    out = []
    for path, ops in (swagger.get("paths") or {}).items():
        txt = " ".join(str((ops.get("get") or {}).get(k, "")) for k in ("summary", "description"))
        if KEYWORD in txt:
            out.append((path, "TPEX" if re.search(r"_O(_\d+)?$", path) else "TWSE"))
    return out


def _col(row: dict, *must: str, exclude: tuple[str, ...] = ()) -> str | None:
    for k in row:
        s = str(k).replace(" ", "")
        if all(m in s for m in must) and not any(e in s for e in exclude):
            return k
    return None


def parse_rows(rows: list[dict], market: str) -> pd.DataFrame:
    """把一個端點的 JSON 轉成表。找不到「非擔任主管」平均數／中位數欄的列整列略過。"""
    recs = []
    for r in rows or []:
        kavg = _col(r, "非擔任主管", "平均", exclude=("變動", "調整"))
        kmed = _col(r, "非擔任主管", "中位數", exclude=("變動", "調整"))
        if not kavg and not kmed:
            continue
        kyr = _col(r, "年度")
        kcode = _col(r, "公司代號") or _col(r, "代號")
        kname = _col(r, "公司名稱")
        kn = _col(r, "非擔任主管", "人數") or _col(r, "全時員工", "人數")
        kya = _col(r, "非擔任主管", "平均", "變動") or _col(r, "非擔任主管", "平均", "調整")
        kym = _col(r, "非擔任主管", "中位數", "變動") or _col(r, "非擔任主管", "中位數", "調整")
        code = clean_code(r.get(kcode)) if kcode else None
        year = to_float(r.get(kyr)) if kyr else None
        if not code or year is None:
            continue
        y = int(year)
        avg = to_float(r.get(kavg)) if kavg else None
        med = to_float(r.get(kmed)) if kmed else None
        n = to_float(r.get(kn)) if kn else None
        recs.append({
            "year": y + 1911 if y < 1911 else y,        # 報告年度是民國年（114）
            "code": code,
            "name": str(r.get(kname, "") or "").strip() if kname else "",
            "market": market,
            "avg_wan": round(avg / 10, 1) if avg else None,       # 仟元 → 萬元
            "median_wan": round(med / 10, 1) if med else None,
            "n": int(n) if n else None,
            "yoy_avg_pct": to_float(r.get(kya)) if kya else None,
            "yoy_median_pct": to_float(r.get(kym)) if kym else None,
        })
    return pd.DataFrame(recs)


def fetch() -> pd.DataFrame:
    sw = http.get(SWAGGER)
    if not isinstance(sw, dict):
        log.warning("讀不到 TWSE swagger.json，官方薪資略過")
        return pd.DataFrame()
    paths = find_paths(sw)
    if not paths:
        log.warning("swagger 裡沒有摘要含「%s」的端點", KEYWORD)
        return pd.DataFrame()
    frames = []
    for path, mkt in paths:
        rows = http.get(config.TWSE_OPENAPI + path)
        if isinstance(rows, list) and rows:
            df = parse_rows(rows, mkt)
            log.info("官方薪資 %s（%s）：%d 列", path, mkt, len(df))
            if not df.empty:
                frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
