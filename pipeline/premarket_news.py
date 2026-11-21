"""盤前消息（精選文章「盤前消息」分頁的資料）。

為什麼單一檔：資料量極小（每天 5 則），而且要「網站直接讀、可往回看前幾天」。
落點是 site/articles/premarket.json（跟 articles/index.json 同一個資料夾：進版控、Pages 直接送出，
不必等 build_payload 重算）。社群盤前貼文流程挑完 5 則後呼叫 add_day()（或 CLI），
同一天重跑會覆蓋那一天（冪等），不會重複堆疊；只保留最近 KEEP 天，檔案不會無限長大。

單日格式（見 docs/marketing/social_unit/premarket_news_format.md）：
  {"date": "2026-10-27", "items": [{"cat": "總經|事件|科技|新聞", "title": "...", "url": "https://...", "source": "鉅亨", "time": "2026-10-24T08:50:02+08:00"}]}
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

CATS = ("新聞", "事件", "科技", "總經")
KEEP = 60
MAX_ITEMS = 8
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "site" / "articles" / "premarket.json"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _desc(v) -> str:
    """新聞摘要 → 一句簡短敘述：解 HTML 實體（&#10; &#8230;）、換行改「；」、去掉「[…]」，最多 80 字。"""
    import html
    t = html.unescape(str(v or ""))
    t = re.sub(r"\s*\[(…|\.\.\.)\]\s*$", "", t)
    t = re.sub(r"\s*[\r\n]+\s*", "；", t.strip())
    t = re.sub(r"[ \t\u3000]+", " ", t).replace("。；", "；").strip("；").strip()
    return t[:80] + ("…" if len(t) > 80 else "")


def clean_day(day: dict) -> dict | None:
    """檢查並清理單日資料；日期不合或一則都沒有就回 None（寧可不寫，也不要寫壞檔讓網頁壞掉）。"""
    if not isinstance(day, dict) or not _DATE.match(str(day.get("date", ""))):
        return None
    try:
        dt.date.fromisoformat(day["date"])
    except ValueError:
        return None
    items = []
    for it in day.get("items") or []:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or "").strip()
        cat = str(it.get("cat") or "").strip()
        if not title or cat not in CATS:
            continue
        url = str(it.get("url") or "").strip()
        if not re.match(r"^https?://", url, re.I):
            url = ""    # 只收 http(s)，擋掉 javascript: 之類
        items.append({"cat": cat, "title": title[:160], "url": url[:500],
                      "source": str(it.get("source") or "").strip()[:20], "time": str(it.get("time") or "").strip()[:30],
                      # 簡短敘述（2026-10-27 Andy：「盤前消息後面五個標題需要有簡短敘述」）：取新聞摘要前 80 字，沒有就空字串
                      "desc": _desc(it.get("desc"))})
    if not items:
        return None
    return {"date": day["date"], "items": items[:MAX_ITEMS]}


def add_day(day: dict, path: Path = DEFAULT_PATH, today: str | None = None) -> bool:
    """把一天寫進 premarket.json（同日覆蓋、新到舊、只留 KEEP 天）。成功回 True。"""
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
        sys.exit("用法：python -m pipeline.premarket_news <單日.json>")
    ok = add_day(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    sys.exit(0 if ok else "單日資料不合格（日期或分類或標題有誤），沒有寫入")
