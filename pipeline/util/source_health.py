"""來源健康紀錄 data/_state/source_health.json（2026-11-06 稽核 B）。

為什麼要跨執行累積：單看「這一輪 ok／false」看不出某來源已經連續壞三天。
這裡每個來源記：最後一次真的有資料的交易日（last_ok_date）、連續失敗幾天（consecutive_fail）、最後的錯誤原因。

計數以「天」為單位，不是以「執行次數」：一天跑三輪（15:30／18:30／21:30）都失敗，只算一天。
同一天多次寫入是冪等的（last_fail_date 去重）。
"""
from __future__ import annotations

import json
from pathlib import Path

ERR_EMPTY = "回空（0 筆）"


def update(health: dict, steps: dict, day: str, *, now_iso: str | None = None) -> dict:
    """依本輪 RESULT["steps"] 更新健康紀錄（純函式，不碰檔案）。

    只看帶 "ok" 欄位的步驟（那是來源層級）；只有 stored／stored 計數的表格列不算來源。
    day：本輪的交易日（YYYY-MM-DD）；拿不到時呼叫端傳台北今天。
    """
    out = {k: dict(v) for k, v in (health or {}).items()}
    for name, info in (steps or {}).items():
        if not isinstance(info, dict) or "ok" not in info:
            continue
        e = out.get(name, {"last_ok_date": None, "consecutive_fail": 0, "last_fail_date": None,
                           "last_error": None, "last_seen": None})
        e["last_seen"] = now_iso or e.get("last_seen")
        if info.get("ok"):
            e["last_ok_date"] = day
            e["consecutive_fail"] = 0
            e["last_error"] = None
        elif e.get("last_fail_date") != day:          # 同一天只計一次
            e["consecutive_fail"] = int(e.get("consecutive_fail") or 0) + 1
            e["last_fail_date"] = day
            e["last_error"] = str(info.get("error") or ERR_EMPTY)[:300]
        out[name] = e
    return out


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(path: Path, health: dict) -> None:
    path.write_text(json.dumps(health, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def failing(health: dict, min_days: int = 2) -> list[dict]:
    """連續失敗達 min_days 天的來源（給資料狀態列用）。門檻 2 天：單日回空可能是端點偶發，兩天才講。"""
    out = []
    for name, e in sorted(health.items()):
        n = int(e.get("consecutive_fail") or 0)
        if n >= min_days:
            out.append({"source": name, "days": n, "last_ok_date": e.get("last_ok_date"),
                        "last_error": e.get("last_error")})
    return out
