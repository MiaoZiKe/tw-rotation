"""自我補跑：GitHub 免費層的 schedule 會延遲、甚至整輪被丟掉（官方文件承認高負載時可能丟棄），
2026-10-20 台北 15:30 與三輪 inst 全沒觸發，Andy 看到「數據沒更新」。
backfill.yml 每小時排程實測穩定，所以由它的 heal job 呼叫這支：
今天（台北）該有的 phase 沒有成功紀錄，就用 workflow_dispatch 補派 daily.yml。

判斷依據是證據（last_run.json 的 phase／finished_at），不是「有沒有 run」：
run 成功不代表有抓到價量（phase=news／inst 的 run 也是 success）。
同一 phase 一天最多補一次：用 bot 自己派的 run 標題（run-name 帶 phase）去重。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
PRICE_READY = (15, 40)    # 台北 15:40 起該有價量
FULL_READY = (18, 40)     # 台北 18:40 起該有完整那輪
CUTOFF_HOUR = 22          # 22:00 後不補（隔天清晨有 news 輪，補了也只是空轉）


def decide(now_utc, last_run, runs):
    """回傳要補的 phase（'price'／'full'）或 None。

    runs：daily.yml 最近的 run（dict：status、event、created_at、display_title、actor_login）。
    """
    now = now_utc.astimezone(TPE)
    if now.weekday() >= 5:
        return None
    hm = (now.hour, now.minute)
    if hm < PRICE_READY or now.hour >= CUTOFF_HOUR:
        return None
    due = "full" if hm >= FULL_READY else "price"
    ok_phases = {"full"} if due == "full" else {"price", "full"}

    day_start = now.replace(hour=15, minute=30, second=0, microsecond=0).astimezone(timezone.utc)
    fin = (last_run or {}).get("finished_at")
    if fin and (last_run or {}).get("phase") in ok_phases:
        try:
            if datetime.fromisoformat(fin) >= day_start:
                return None            # 今天已經有該有的 phase
        except ValueError:
            pass
    for r in runs:
        created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        if created < day_start:
            continue
        if r["status"] != "completed":
            return None                # 已有一輪排隊或在跑，不疊
        title = r.get("display_title", "")
        if r.get("actor_login") == "github-actions[bot]" and f"({due})" in title:
            return None                # 這個 phase 今天已補過一次
    return due


def _gh_runs():
    out = subprocess.run(
        ["gh", "api", "repos/{}/actions/workflows/daily.yml/runs?per_page=30".format(os.environ["GITHUB_REPOSITORY"]),
         "--jq", "[.workflow_runs[]|{status,event,created_at,display_title,actor_login:.triggering_actor.login}]"],
        check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def main():
    try:
        last = json.load(open("data/_state/last_run.json", encoding="utf-8"))
    except Exception:
        last = {}
    phase = decide(datetime.now(timezone.utc), last, _gh_runs())
    print(f"補跑判斷：{phase or '不需要'}")
    if phase:
        subprocess.run(["gh", "workflow", "run", "daily.yml", "--ref", os.environ.get("GITHUB_REF_NAME", "main"),
                        "-f", f"phase={phase}"], check=True)
        print(f"已派 daily.yml phase={phase}")


if __name__ == "__main__":
    sys.exit(main())
