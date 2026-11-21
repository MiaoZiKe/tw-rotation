"""盤後消息：從資料湖挑「今天收盤（13:30）之後」的重點消息 5 則，寫進 site/articles/postmarket.json（精選文章「盤後消息」分頁）。

2026-10-27 Andy：「還需要新增盤後消息 在盤前旁邊」→ 分頁已上線；這支每天盤後管線抓完新聞後跑（daily.yml），同日覆蓋，
傍晚那輪（full）會用更多新聞再挑一次。挑法與盤前完全相同（scripts/social_premarket.pick_news），只差時間窗。
非交易日、沒有新聞就不寫（回 0，不讓管線紅）。
"""
from __future__ import annotations

import sys
from datetime import datetime, time as dtime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

import social_premarket as sp  # noqa: E402
from pipeline import postmarket_news as PM  # noqa: E402
from pipeline.util import store  # noqa: E402


def main() -> int:
    now = datetime.now(sp.TPE)
    today = now.date()
    if not sp.is_tw_trading_day(today, sp.load_holidays()):
        print(f"[postmarket] {today} 不是台股交易日 → 不寫")
        return 0
    start = datetime.combine(today, dtime(13, 30), tzinfo=sp.TPE)
    if now <= start:
        print("[postmarket] 還沒收盤 → 不寫")
        return 0
    items = sp.pick_news(store.read("news"), start, now, n=5)
    if not items:
        print(f"[postmarket] {start:%H:%M}～{now:%H:%M} 沒有可用的消息 → 不寫")
        return 0
    ok = PM.add_day({"date": today.isoformat(), "items": [{"cat": i["category"], "title": i["title"], "url": i["url"], "source": i["source"],
                                                           "time": i["published_at"], "desc": i.get("summary", "")} for i in items]})
    print(f"[postmarket] 盤後消息 {len(items)} 則寫入 site/articles/postmarket.json：{'成功' if ok else '格式不合，未寫'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
