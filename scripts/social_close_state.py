"""盤後發布狀態（social-live.yml 的「盤後已經發過了就不重複」那一步用，2026-10-29）。

用法：python scripts/social_close_state.py <posted.json> <YYYY-MM-DD>
印出：
  skip        今天的盤後主貼文已發，而且不需要補發（或補發也已發）
  supplement  主貼文是走保底發的（紀錄有 partial：法人卡晚到被拿掉），法人補充貼文 close-inst-<日期> 還沒發
  （空字串）  今天還沒發主貼文 → 照常做
讀不到檔案一律當成「還沒發」（寧可多跑一輪，由 social_snap.py 的 --posted-json 再把關一次）。

★ 2026-11-09（事故：11-06 降量模式下多發一則 close-inst-2026-11-06）：
  1. 補充貼文是「另一則貼文」，要看 post_quota.json 的 live.close_inst（沒寫＝關）；關著 → skip，被停的不補發。
  2. 只有被拿掉的是法人卡（inst-today／streak-foreign／streak-trust）才需要補充；
     11-06 主貼文只拿掉 retail-ratio（散戶多空比），法人三張早就在主貼文裡，補充貼文等於把同樣三張重發一次。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import post_quota  # noqa: E402  只用標準函式庫

INST_CARDS = ("inst-today", "streak-foreign", "streak-trust")      # 同 social_gate.INST_CARDS（這支不 import 它，保持零依賴）


def state(posted: dict, day: str, q: dict | None = None) -> str:
    main = posted.get(f"close-{day}")
    if not main:
        return ""
    if isinstance(main, dict) and f"close-inst-{day}" not in posted \
            and any(n in INST_CARDS for n in (main.get("partial") or [])):
        if not post_quota.any_on("close_inst", q if q is not None else post_quota.load()):
            print(f"{post_quota.SKIP_MSG}：法人補充貼文 close-inst-{day}（post_quota.json live.close_inst 關）→ 不補發", file=sys.stderr)
            return "skip"
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
