"""多頻道自動發文入口（2026-11-09）。

Andy 原話（2026-11-09）：「talk_01010909 已經好了 幫忙協助其他頻道 一起建立 Tech_01010909 Shrimp_01010909 caffaine.ai
以上三個都只差在 Github」。說明：docs/marketing/channels/auto_post_all.md

頻道清單：docs/marketing/channels/channels.json（代碼、權杖前綴、佇列、state、開關檔、時段、每日上限）。
發文邏輯跟頻道④完全同一份（scripts/healing_post.py：取下一則、防重發、驗證模式、缺權杖空跑、短效換長效、刪文），
這支只負責「選頻道」：
  python scripts/channel_post.py --channel tech [--dry-run] [--mode post|verify|delete|test_delete] [--prepare]
  python scripts/channel_post.py --plan --schedule "17 4 * * *"   # 工作流用：這個排程是哪幾個頻道的時段 → JSON
  python scripts/channel_post.py --plan --channel all             # 手動觸發：all＝channel_post.yml 管的全部頻道
  python scripts/channel_post.py --plan --comments                 # 留言私訊：dm_config enabled=true 的頻道

每個頻道只讀自己前綴的權杖（例如 TECH_IG_ACCESS_TOKEN），工作流也只把那個頻道的 Secrets 帶進那個 job。
頻道④（healing）仍由 .github/workflows/healing_post.yml 排程；channel_post.yml 只管 workflow 欄位寫 channel_post.yml 的頻道。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import healing_post as HP  # noqa: E402

WORKFLOW = "channel_post.yml"


def plan(schedule: str = "", want: str = "all", path: Path = HP.CHANNELS_FILE) -> list[dict]:
    """回傳這一輪要跑的頻道 [{channel, prefix}]（給 GitHub matrix 用）。
    排程觸發：只挑 cron 清單裡有這個排程字串的頻道；手動觸發：want＝all 或某個代碼。"""
    out = []
    for code, c in HP.load_channels(path).items():
        if c.get("workflow") != WORKFLOW:
            continue
        if c.get("handed_over"):   # 頻道② 改用 tc_post.yml，2026-11-10 頻道④交接：不排、不手動跑，避免重複發文
            continue
        if schedule:
            if schedule.strip() not in [x.strip() for x in c.get("cron") or []]:
                continue
        elif want not in ("all", code):
            continue
        out.append({"channel": code, "prefix": c["prefix"]})
    return out


def plan_comments(want: str = "all", path: Path = HP.CHANNELS_FILE) -> list[dict]:
    """留言私訊（channel_comments.yml）：只挑 dm_config.json 的 enabled=true 的頻道；關著的連 job 都不開。"""
    out = []
    for code, c in HP.load_channels(path).items():
        if c.get("comments_workflow") != "channel_comments.yml" or want not in ("all", code):
            continue
        if c.get("handed_over"):   # 頻道② 留言／私訊改由 tc_post.yml 處理（2026-11-10 頻道④交接）
            continue
        cfg = HP.load_json(HP.ROOT / c.get("dm_config", ""), {}) if c.get("dm_config") else {}
        if cfg.get("enabled") is True:
            out.append({"channel": code, "prefix": c["prefix"]})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="多頻道自動發文", add_help=True)
    ap.add_argument("--plan", action="store_true", help="只印出這一輪要跑哪些頻道（JSON），給工作流用")
    ap.add_argument("--schedule", default="", help="--plan：github.event.schedule（排程字串）")
    ap.add_argument("--comments", action="store_true", help="--plan：改列留言私訊要跑的頻道（dm_config enabled=true）")
    a, rest = ap.parse_known_args(argv)
    if a.plan:
        ch = "all"
        if "--channel" in rest:
            ch = rest[rest.index("--channel") + 1]
        m = plan_comments(ch) if a.comments else plan(a.schedule, ch)
        print(json.dumps(m, ensure_ascii=False))
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write("matrix=" + json.dumps(m, ensure_ascii=False) + "\n")
                f.write("count=" + str(len(m)) + "\n")
        return 0
    if "--channel" not in rest:
        ap.error("要給 --channel（例如 --channel tech）")
    return HP.main(rest)


if __name__ == "__main__":
    sys.exit(main())
