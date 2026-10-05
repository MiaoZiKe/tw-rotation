"""等「網站真的部署完成」才回報 —— 唯一可以拿來說「部署好了」的依據。

2026-10-06 事故（DECISIONS #323）：推 preview/style-guide 之後，CEO 盯的是 head_sha＝預覽分支那一輪
「部署網站」，那一輪只是轉呼叫（relay-preview，10 秒就 success），真正把預覽裝上網站的是 main 那一輪
（workflow_dispatch，要 10～15 分鐘），當時還在跑。CEO 卻回報「02:17 就部署好了」，Andy 打開看沒變化。

這支只看 GitHub「Deployments」（environment＝github-pages）——那是 Pages 真的換版的紀錄，不看 Actions run：
  · 找「建立時間 ≥ 你推送的時間」的第一筆 github-pages deployment
  · 正式站（--branch main）：還要求它的 sha 就是你推的那個 commit 或其後代
  · 預覽（--branch preview/<名稱>）：main 那一輪是在推送之後才開始，會把所有 preview/* 一起裝進去
  · 被後面的推送擠掉（cancelled／inactive／error）就繼續等下一筆
  · 等到 success 才印「部署完成」；failure 就印失敗；逾時就印「還沒好」——三種都不可以講成「好了」

用法：
  python scripts/deploy_wait.py --branch main [--sha <commit>] [--timeout 2400]
  python scripts/deploy_wait.py --branch preview/style-guide
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = "MiaoZiKe/tw-rotation"
TPE = timezone(timedelta(hours=8))


def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr.strip() or out.stdout.strip())
    return json.loads(out.stdout)


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def tpe(d):
    return d.astimezone(TPE).strftime("%m-%d %H:%M")


def is_ancestor(a, b):
    # a 是 b 的祖先（或相同）→ b 那一版包含 a
    r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b], capture_output=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", required=True, help="main 或 preview/<名稱>")
    ap.add_argument("--sha", help="推上去的 commit（預設取遠端該分支最新）")
    ap.add_argument("--timeout", type=int, default=2400)
    a = ap.parse_args()

    sha = a.sha or gh(f"repos/{REPO}/commits/{a.branch}")["sha"]
    pushed = ts(gh(f"repos/{REPO}/commits/{sha}")["commit"]["committer"]["date"])
    if a.branch != "main":
        # 預覽：commit 時間可能早於真正推送（先 commit、晚點才推）→ 改用該分支轉呼叫那一輪的建立時間＝推送時間
        runs = gh(f"repos/{REPO}/actions/workflows/pages.yml/runs?branch={a.branch}&per_page=5")["workflow_runs"]
        runs = [r for r in runs if r["head_sha"] == sha]
        if runs:
            pushed = max(pushed, ts(min(r["created_at"] for r in runs)))
    else:
        subprocess.run(["git", "fetch", "-q", "origin", "main"], capture_output=True)
    url = ("https://miaozike.github.io/tw-rotation/" if a.branch == "main"
           else f"https://miaozike.github.io/tw-rotation/preview/{a.branch.split('/', 1)[1].replace('/', '-')}/")
    print(f"等 {a.branch} {sha[:8]}（推送時間 台北 {tpe(pushed)}）真正部署到 Pages …", flush=True)

    t0 = time.time()
    seen_bad = set()
    while time.time() - t0 < a.timeout:
        deps = gh(f"repos/{REPO}/deployments?environment=github-pages&per_page=20")
        cands = sorted((d for d in deps if ts(d["created_at"]) >= pushed), key=lambda d: d["created_at"])
        for d in cands:
            if a.branch == "main" and not is_ancestor(sha, d["sha"]):
                continue
            if d["id"] in seen_bad:
                continue
            st = gh(f"repos/{REPO}/deployments/{d['id']}/statuses")
            state = st[0]["state"] if st else "pending"
            if state == "success":
                done = ts(st[0]["created_at"])
                print(f"✅ 部署完成：Pages deployment {d['id']}（main {d['sha'][:8]}）台北 {tpe(done)} success")
                print(f"   網址：{url}")
                print("   ⚠ 這是從 GitHub 部署紀錄確認的；容器打不開網站，請 Andy 重新整理看一眼。")
                return 0
            if state in ("failure", "error", "inactive"):
                print(f"   deployment {d['id']}（{d['sha'][:8]}）{state} —— 繼續等下一筆", flush=True)
                seen_bad.add(d["id"])
                continue
            break  # 這一筆還在跑（waiting／queued／in_progress），先等它
        time.sleep(20)
    print(f"⏳ 還沒部署完成（等了 {int(time.time() - t0)} 秒）—— 不可以回報「好了」。")
    return 2


if __name__ == "__main__":
    sys.exit(main())
