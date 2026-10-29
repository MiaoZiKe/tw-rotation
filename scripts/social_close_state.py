"""盤後發布狀態（social-live.yml 的「盤後已經發過了就不重複」那一步用，2026-10-29）。

用法：python scripts/social_close_state.py <posted.json> <YYYY-MM-DD>
印出：
  skip        今天的盤後主貼文已發，而且不需要補發（或補發也已發）
  supplement  主貼文是走保底發的（紀錄有 partial：法人卡晚到被拿掉），法人補充貼文 close-inst-<日期> 還沒發
  （空字串）  今天還沒發主貼文 → 照常做
讀不到檔案一律當成「還沒發」（寧可多跑一輪，由 social_snap.py 的 --posted-json 再把關一次）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def state(posted: dict, day: str) -> str:
    main = posted.get(f"close-{day}")
    if not main:
        return ""
    if isinstance(main, dict) and main.get("partial") and f"close-inst-{day}" not in posted:
        return "supplement"
    return "skip"


def main(argv: list[str]) -> int:
    try:
        posted = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        posted = {}
    print(state(posted if isinstance(posted, dict) else {}, argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
