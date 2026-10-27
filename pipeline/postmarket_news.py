"""盤後消息（精選文章「盤後消息」分頁的資料）。

2026-10-27 Andy：「還需要新增盤後消息，在盤前旁邊」。格式、清理規則、同日覆蓋、只留最近 KEEP 天
全部與盤前消息（pipeline/premarket_news.py）相同，所以直接沿用它的 clean_day()，不重寫一份
（兩邊的欄位檢查若各寫各的，日後改一邊就會悄悄不一致）。差別只有落點：site/articles/postmarket.json。
之後社群盤後貼文流程挑完幾則後呼叫 add_day()（或 CLI），這次先不接。

單日格式與盤前相同：
  {"date": "2026-10-27", "items": [{"cat": "總經|事件|科技|新聞", "title": "...", "url": "https://...", "source": "鉅亨", "time": "...", "desc": "..."}]}
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from pipeline.premarket_news import CATS, KEEP, MAX_ITEMS, clean_day  # noqa: F401  (CATS 等一併轉出，方便呼叫端)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "site" / "articles" / "postmarket.json"


def add_day(day: dict, path: Path = DEFAULT_PATH, today: str | None = None) -> bool:
    """把一天寫進 postmarket.json（同日覆蓋、新到舊、只留 KEEP 天）。成功回 True。"""
    d = clean_day(day)
    if d is None:
        return False
    try:
        cur = json.loads(Path(path).read_text(encoding="utf-8"))
        days = [x for x in cur.get("days", []) if isinstance(x, dict) and x.get("date") != d["date"]]
    except (OSError, ValueError):
        days = []
    days.append(d)
    days.sort(key=lambda x: x["date"], reverse=True)
    out = {"updated": today or dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d"), "days": days[:KEEP]}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("用法：python -m pipeline.postmarket_news <單日.json>")
    ok = add_day(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    sys.exit(0 if ok else "單日資料不合格（日期或分類或標題有誤），沒有寫入")
