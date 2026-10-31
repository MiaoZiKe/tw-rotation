"""IG 主題文章晚間監工（2026-11-01 Andy「OK」：IG 主題文章改晚上 20:00／20:50／21:40 發；CEO：「監工排程增加 22:10 檢查 IG 主題文章是否發出」）。

看 social/ig/queue/<今天>_news-*.md：
  · 該有的段落（交易日 pre／intra／post、休市日 wk1／wk2）沒有檔 → 缺稿
  · status: approved 且 publish_at 已過 10 分鐘還沒 posted → 逾時（工作流會先叫 ig_post 補發再查一次）
  · status: error → 發文失敗
用法：python scripts/ig_news_check.py [--date YYYY-MM-DD] [--json]
結束碼：全部 posted → 0；有缺稿／逾時／失敗 → 1（印出每篇狀態與 urls）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPE = timezone(timedelta(hours=8))


def meta_of(p: Path) -> dict:
    m = re.match(r"\A---\s*\n(.*?)\n---", p.read_text(encoding="utf-8"), re.S)
    return {a.strip(): b.strip() for a, _, b in (l.partition(":") for l in (m.group(1).splitlines() if m else [])) if _}


def expected_slots(day: str) -> tuple[str, ...]:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from social_news import is_trading
        return ("pre", "intra", "post") if is_trading(day) else ("wk1", "wk2")
    except Exception:  # noqa: BLE001
        return ()


def check(day: str, now: datetime, root: Path = ROOT) -> dict:
    q = root / "social" / "ig" / "queue"
    rows, bad = [], []
    have = set()
    for f in sorted(q.glob(f"{day}_news-*.md")):
        mt = meta_of(f)
        slot = re.match(rf"{day}_news-([a-z0-9]+)-\d+", f.stem)
        have.add(slot.group(1) if slot else "")
        st = mt.get("status", "")
        try:
            due = datetime.fromisoformat(mt.get("publish_at", ""))
        except ValueError:
            due = None
        state = "已發" if st == "posted" else ("發文失敗" if st == "error" else
                 ("逾時未發" if st == "approved" and due and now - due > timedelta(minutes=10) else
                  ("草稿（未核准）" if st == "draft" else "等待中")))
        rows.append(dict(file=f.name, status=st, publish_at=mt.get("publish_at"), state=state, urls=mt.get("urls", "")))
        if state in ("發文失敗", "逾時未發"):
            bad.append(f"{f.name}：{state}")
    for s in expected_slots(day):
        if s not in have:
            bad.append(f"{s} 段沒有 IG 主題文章檔")
    return dict(date=day, checked_at=now.isoformat(timespec="minutes"), posts=rows, problems=bad)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    now = datetime.now(TPE)
    r = check(a.date or now.strftime("%Y-%m-%d"), now)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        for x in r["posts"]:
            print(f"{x['file']}｜{x['state']}｜{x['publish_at']}｜{x['urls']}")
        for p in r["problems"]:
            print("⚠ " + p)
    return 1 if r["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
