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


# ------------------------------------------------------------------ 產業關聯圖

CHAIN_PATH = Path(__file__).resolve().parent / "supply_chain.yaml"
SHARE_STALE_DAYS = 180


def supply_chain(path: Path | None = None) -> dict:
    """讀 supply_chain.yaml 並整理成前端可直接畫圖的結構。

    每個市占數字帶 stale 標記（超過 180 天），前端會變灰提示。
    公司節點會附上它在 groups.yaml 的族群，方便跳轉到個股頁。
    """
    p = path or CHAIN_PATH
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    today = date.today()

    def _stale(as_of) -> bool:
        if not as_of:
            return True
        s = str(as_of)
        try:
            if "Q" in s:                      # 2026-Q2 → 季末
                y, q = s.split("-Q"); d = date(int(y), int(q) * 3, 28)
            elif "H" in s:
                y, h = s.split("-H"); d = date(int(y), 6 if h == "1" else 12, 28)
            elif s.endswith("F"):
                return False                  # 預估值不算過期
            elif len(s) == 4:
                d = date(int(s), 6, 30)
            elif len(s) == 7:
                d = date(int(s[:4]), int(s[5:7]), 28)
            else:
                d = datetime.strptime(s, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return True
        return (today - d).days > SHARE_STALE_DAYS

    m = membership()
    group_lookup = (m.groupby("code")["group_name"].agg(lambda x: list(dict.fromkeys(x))).to_dict()
                    if not m.empty else {})

    seg_layer = {s["id"]: s.get("layer", 0) for s in raw.get("segments", [])}
    companies = []
    for c in raw.get("companies", []):
        shares = []
        for sh in c.get("share", []) or []:
            sh = dict(sh)
            sh["stale"] = _stale(sh.get("as_of"))
            shares.append(sh)
        ticker = str(c.get("ticker") or "")
        companies.append({
            "id": c["id"], "name": c.get("name"), "ticker": ticker or None,
            "tw_code": ticker if (ticker.isdigit() and len(ticker) == 4) else None,
            "segment": c.get("segment"), "layer": seg_layer.get(c.get("segment"), 0),
            "foreign": bool(c.get("foreign")), "tech": c.get("tech", []),
            "share": shares, "growth": c.get("growth"), "risks": c.get("risks", []),
            "note": c.get("note"), "groups": group_lookup.get(ticker, []),
        })

    products = []
    for pr in raw.get("products", []) or []:
        pr = dict(pr)
        for pen in pr.get("penetration", []) or []:
            pen["stale"] = _stale(pen.get("as_of"))
        products.append(pr)

    return {
        "meta": raw.get("meta", {}),
        "segments": sorted(raw.get("segments", []), key=lambda s: s.get("layer", 0)),
        "products": products,
        "companies": companies,
        "edges": raw.get("edges", []),
    }
