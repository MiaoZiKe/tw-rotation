"""上市、上櫃公司「非擔任主管職務之全時員工薪資」年度表（每年 6/30 公布上一年度）。

來源（都是白名單內的政府開放資料，不碰 www.twse.com.tw/rwd）：
- 上市：openapi.twse.com.tw 的「上市公司企業ESG資訊揭露彙總資料-人力發展」
        （data.gov.tw 資料集 155869；欄位含非擔任主管職務之全時員工薪資平均數、中位數）
- 上櫃：www.tpex.org.tw/openapi 的「上櫃公司企業ESG資訊揭露彙總資料-人力發展」
        （data.gov.tw 資料集 156379）

為什麼用「探索」而不是寫死路徑：2026-11-11 開發時容器連不出去，沒有拿到實測 fixture，
而專案規矩是猜欄位名的下場是上線整欄空白。所以這裡：
  1. 先讀 swagger.json，找摘要含「人力發展」「非擔任主管」的路徑，再加上一組已知候選路徑；
  2. 每個候選都實際打一次，只收「欄位裡同時有『非擔任主管』與『平均』」的那個；
  3. 欄位用關鍵字比對，不寫死全名（上游改名是常態）；
  4. 解析失敗把實際表頭與前 200 字印進 log。
單位維持官方的「仟元/人」，換算成萬元是輸出層的事。
"""
from __future__ import annotations

import logging
import re

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, to_float, to_int

log = logging.getLogger(__name__)

# 已知候選（ESG 彙總系列 t187ap46_*；實際哪一支是人力發展由欄位判定，不靠編號）
TWSE_CANDIDATES = [f"/opendata/t187ap46_L_{i}" for i in range(1, 20)]
# 上櫃：先走證交所 OpenAPI 同主機的 _O 系列（config 的上櫃公司資料也是這樣取的，櫃買官網對雲端 IP 回 HTML 擋掉），
# 實測 2026-11-11 www.tpex.org.tw/openapi 對 Actions 回 HTML，所以只當最後備案。
TPEX_VIA_TWSE = [f"/opendata/t187ap46_O_{i}" for i in range(1, 20)]
TPEX_CANDIDATES = ([f"/t187ap46_O_{i}" for i in range(1, 20)]
                   + [f"/mopsfin_t187ap46_O_{i}" for i in range(1, 20)])
SWAGGER_KEYWORDS = ("人力發展", "非擔任主管")

COLUMNS = ["year", "market", "code", "name", "avg_k", "median_k", "headcount",
           "total_k", "source"]


def _find(cols: list[str], must: tuple[str, ...], bad: tuple[str, ...] = ()) -> str | None:
    """欄位名同時含 must 全部關鍵字、且不含 bad 任一個。"""
    for c in cols:
        n = re.sub(r"\s+", "", str(c))
        if all(k in n for k in must) and not any(b in n for b in bad):
            return c
    return None


_CHANGE = ("變動", "增減", "%", "成長")


def resolve_columns(cols: list[str]) -> dict | None:
    """回欄位對照；沒有「非擔任主管 + 平均」就回 None（代表這不是我們要的表）。"""
    avg = _find(cols, ("非擔任主管", "平均"), _CHANGE)
    if avg is None:
        return None
    return {
        "code": _find(cols, ("公司代號",)) or _find(cols, ("代號",)),
        "name": _find(cols, ("公司名稱",)) or _find(cols, ("公司簡稱",)) or _find(cols, ("名稱",)),
        "year": _find(cols, ("年度",), ("出表",)),
        "avg": avg,
        "median": _find(cols, ("非擔任主管", "中位數"), _CHANGE),
        "headcount": _find(cols, ("非擔任主管", "人數")) or _find(cols, ("全時員工", "人數")),
        "total": _find(cols, ("非擔任主管", "總額")) or _find(cols, ("全時員工", "薪資總額")),
    }


def _to_year(v) -> int | None:
    """年度可能是民國（114）或西元（2025）。"""
    n = to_int(v)
    if n is None:
        return None
    return n + 1911 if n < 1911 else n


def swagger_paths(base: str) -> list[str]:
    """從 swagger 找摘要／說明含關鍵字的路徑。失敗回空 list（不影響已知候選）。"""
    root = base.rsplit("/v1", 1)[0]
    sw = None
    for u in (root + "/v1/swagger.json", root + "/swagger.json", root + "/v1/swagger"):
        sw = http.get(u)
        if isinstance(sw, dict) and isinstance(sw.get("paths"), dict):
            break
    if not isinstance(sw, dict) or not isinstance(sw.get("paths"), dict):
        log.warning("swagger 取不到或格式非預期：%s", base)
        return []
    out = []
    for path, spec in sw["paths"].items():
        text = str(spec)
        if any(k in text for k in SWAGGER_KEYWORDS):
            out.append(path)
    return out


def parse(rows: list[dict], market: str, source: str) -> pd.DataFrame:
    """把一個端點的回應轉成固定欄位。不是目標表就回空。"""
    if not rows or not isinstance(rows[0], dict):
        return pd.DataFrame(columns=COLUMNS)
    cols = [str(k).strip().lstrip("﻿") for k in rows[0].keys()]
    m = resolve_columns(cols)
    if m is None or not m["code"]:
        return pd.DataFrame(columns=COLUMNS)
    out = []
    for r in rows:
        r = {str(k).strip().lstrip("﻿"): v for k, v in r.items()}
        code = clean_code(r.get(m["code"]))
        year = _to_year(r.get(m["year"])) if m["year"] else None
        avg = to_float(r.get(m["avg"]))
        if not code or year is None or avg is None:
            continue
        out.append({
            "year": year, "market": market, "code": code,
            "name": (r.get(m["name"]) or "").strip() if m["name"] else "",
            "avg_k": avg,
            "median_k": to_float(r.get(m["median"])) if m["median"] else None,
            "headcount": to_int(r.get(m["headcount"])) if m["headcount"] else None,
            "total_k": to_float(r.get(m["total"])) if m["total"] else None,
            "source": source,
        })
    return pd.DataFrame(out, columns=COLUMNS)


def _scan(base: str, candidates: list[str], market: str) -> pd.DataFrame:
    return _scan_paths(base, list(dict.fromkeys(swagger_paths(base) + candidates)), market)


def _scan_paths(base: str, paths: list[str], market: str) -> pd.DataFrame:
    frames = []
    for p in paths:
        url = base + p
        data = http.get(url)
        if not isinstance(data, list) or not data:
            continue
        df = parse(data, market, url)
        if df.empty:
            if isinstance(data[0], dict):
                log.info("%s 不是非主管薪資表，表頭：%s", url, list(data[0].keys())[:8])
            continue
        log.info("%s：命中 %s 列（年度 %s）", url, len(df), sorted(df["year"].unique()))
        frames.append(df)
    if not frames:
        log.warning("%s 市場找不到非主管薪資表（已試 %s 個路徑）", market, len(paths))
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(frames, ignore_index=True)


def nonmgr_salary_twse() -> pd.DataFrame:
    try:
        return _scan(config.TWSE_OPENAPI, TWSE_CANDIDATES, "上市")
    except Exception as exc:  # noqa: BLE001 —— 單一來源不能拖垮管線
        log.error("上市非主管薪資抓取失敗：%s", exc)
        return pd.DataFrame(columns=COLUMNS)


def nonmgr_salary_tpex() -> pd.DataFrame:
    try:
        df = _scan_paths(config.TWSE_OPENAPI, TPEX_VIA_TWSE, "上櫃")
        if not df.empty:
            return df
        return _scan(config.TPEX_OPENAPI, TPEX_CANDIDATES, "上櫃")
    except Exception as exc:  # noqa: BLE001
        log.error("上櫃非主管薪資抓取失敗：%s", exc)
        return pd.DataFrame(columns=COLUMNS)
