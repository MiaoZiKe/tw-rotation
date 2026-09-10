"""族群對照表的讀取與健康檢查。"""
from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import yaml

log = logging.getLogger(__name__)

YAML_PATH = Path(__file__).resolve().parent / "groups.yaml"
STALE_DAYS = 100          # 超過約一季沒人工檢視就示警


def load(path: Path | None = None) -> dict:
    p = path or YAML_PATH
    with p.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def membership(cfg: dict | None = None) -> pd.DataFrame:
    """展開成一列一個 (code, group) 的長格式。一檔股票可以屬於多個族群。"""
    cfg = cfg or load()
    rows = []
    for gid, g in (cfg.get("groups") or {}).items():
        for code in g.get("codes") or []:
            rows.append({
                "code": str(code).strip(),
                "group_id": gid,
                "group_name": g.get("name", gid),
                "tier": g.get("tier", "standalone"),
                "chain": g.get("chain", "other"),
            })
    return pd.DataFrame(rows)


def benchmarks(cfg: dict | None = None) -> dict[str, str]:
    return (cfg or load()).get("benchmarks") or {}


def chains(cfg: dict | None = None) -> dict:
    return (cfg or load()).get("chains") or {}


def health(cfg: dict | None = None) -> dict:
    """對照表的體檢報告，會顯示在 dashboard 上，避免它默默過期。"""
    cfg = cfg or load()
    meta = cfg.get("meta") or {}
    m = membership(cfg)

    reviewed_raw = meta.get("reviewed")
    days_since = None
    if reviewed_raw:
        try:
            reviewed = datetime.strptime(str(reviewed_raw), "%Y-%m-%d").date()
            days_since = (date.today() - reviewed).days
        except ValueError:
            log.warning("groups.yaml 的 reviewed 日期格式不正確：%s", reviewed_raw)

    dupes = (m.groupby("code").size().loc[lambda s: s > 1]
             .sort_values(ascending=False).to_dict())

    return {
        "reviewed": reviewed_raw,
        "days_since_review": days_since,
        "is_stale": bool(days_since is not None and days_since > STALE_DAYS),
        "group_count": len(cfg.get("groups") or {}),
        "code_count": int(m["code"].nunique()) if not m.empty else 0,
        "multi_group_codes": dupes,
        "empty_groups": [gid for gid, g in (cfg.get("groups") or {}).items()
                         if not (g.get("codes") or [])],
    }
