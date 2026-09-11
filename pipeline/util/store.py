"""Parquet 資料湖：append-only 寫入、依 key 去重、依年份分割。

為什麼要這樣設計：
- 開放資料只有「最新一天快照」，歷史完全靠我們自己每天存下來。
  一旦寫壞或覆蓋，那天的資料就永遠回不來了 —— 所以永遠 append + 去重，
  絕不整檔覆寫。
- 非交易日 API 會靜默回傳前一個交易日的資料，且不標示。
  去重機制讓這種重複自動被吃掉，不會污染資料。
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .. import config

log = logging.getLogger(__name__)


def _table_dir(table: str) -> Path:
    d = config.DATA / table
    d.mkdir(parents=True, exist_ok=True)
    return d


def _partition_key(df: pd.DataFrame, table: str) -> pd.Series:
    """決定每一列落在哪個年度分割檔。"""
    if "date" in df.columns:
        return pd.to_datetime(df["date"], errors="coerce").dt.year.astype("Int64")
    if "ym" in df.columns:
        return df["ym"].astype(str).str.slice(0, 4).astype("Int64")
    if "year" in df.columns:
        return pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    # 無時間維度的表（company_info）用單一分割
    return pd.Series([0] * len(df), index=df.index, dtype="Int64")


def read(table: str, *, years: list[int] | None = None) -> pd.DataFrame:
    """讀出整張表（或指定年份）。表不存在回空 DataFrame。"""
    d = config.DATA / table
    if not d.exists():
        return pd.DataFrame()
    files = sorted(d.glob("year=*/part.parquet"))
    if years is not None:
        keep = {f"year={y}" for y in years}
        files = [f for f in files if f.parent.name in keep]
    if not files:
        return pd.DataFrame()
    frames = []
    for f in files:
        try:
            frames.append(pd.read_parquet(f))
        except Exception as exc:  # 單一分割壞掉不該讓整條管線死
            log.error("讀取 %s 失敗：%s", f, exc)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def append(table: str, df: pd.DataFrame) -> int:
    """寫入新資料並依 key 去重。回傳實際新增的列數。"""
    if df is None or df.empty:
        log.info("%s：沒有新資料", table)
        return 0
    if table not in config.TABLES:
        raise KeyError(f"未定義的資料表：{table}")

    keys = config.TABLES[table]
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise ValueError(f"{table} 缺少 key 欄位：{missing}")

    df = df.copy()
    df = df.dropna(subset=keys)
    if df.empty:
        return 0

    df["__part"] = _partition_key(df, table)
    total_new = 0

    for part, chunk in df.groupby("__part", dropna=False):
        chunk = chunk.drop(columns="__part")
        part_val = 0 if pd.isna(part) else int(part)
        pdir = _table_dir(table) / f"year={part_val}"
        pdir.mkdir(parents=True, exist_ok=True)
        target = pdir / "part.parquet"

        if target.exists():
            try:
                old = pd.read_parquet(target)
            except Exception as exc:
                log.error("讀取既有分割 %s 失敗，為避免覆蓋資料，本次跳過：%s", target, exc)
                continue
            before = len(old)
            merged = pd.concat([old, chunk], ignore_index=True)
            # 後到的資料視為更正版本，保留最後一筆
            merged = merged.drop_duplicates(subset=keys, keep="last")
            added = len(merged) - before
        else:
            merged = chunk.drop_duplicates(subset=keys, keep="last")
            added = len(merged)

        merged = _sort(merged, keys)
        merged.to_parquet(target, index=False, compression="zstd")
        total_new += max(0, added)

    log.info("%s：寫入 %d 列，新增 %d 列", table, len(df), total_new)
    return total_new


def _sort(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    cols = [k for k in keys if k in df.columns]
    return df.sort_values(cols, kind="stable").reset_index(drop=True) if cols else df


def latest_date(table: str) -> str | None:
    """該表目前最新的日期，用來判斷今天是不是已經抓過了。"""
    df = read(table)
    if df.empty:
        return None
    col = "date" if "date" in df.columns else ("ym" if "ym" in df.columns else None)
    if col is None:
        return None
    vals = df[col].dropna().astype(str)
    return vals.max() if len(vals) else None


def table_summary() -> pd.DataFrame:
    """所有資料表的列數與最新日期，給健康檢查用。"""
    rows = []
    for t in config.TABLES:
        df = read(t)
        rows.append({
            "table": t,
            "rows": len(df),
            "latest": latest_date(t) or "—",
        })
    return pd.DataFrame(rows)


def purge(table: str, keep: "callable", column: str = "code") -> int:
    """就地清掉不該存在的列，回傳刪除筆數。

    這是唯一允許改寫既有分割檔的操作，只在明確的資料清理情境下使用
    （例如早期版本誤把上萬檔權證寫進 price_daily）。
    """
    d = config.DATA / table
    if not d.exists():
        return 0
    removed = 0
    for f in sorted(d.glob("year=*/part.parquet")):
        try:
            df = pd.read_parquet(f)
        except Exception as exc:
            log.error("讀取 %s 失敗，跳過清理：%s", f, exc)
            continue
        if column not in df.columns or df.empty:
            continue
        mask = df[column].map(keep).fillna(False).astype(bool)
        if mask.all():
            continue
        removed += int((~mask).sum())
        df[mask].reset_index(drop=True).to_parquet(f, index=False, compression="zstd")
    if removed:
        log.info("%s：清掉 %d 列不符合條件的資料", table, removed)
    return removed
