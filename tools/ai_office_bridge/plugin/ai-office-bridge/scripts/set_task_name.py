#!/usr/bin/env python3
"""設定這個工作階段在 AI 辦公室顯示的「任務簡稱」（6～12 個字，例如「AI 辦公室接入」）。

用法（由 Claude 在開工、或任務明顯換題時自己執行）：
  python3 /opt/ai-office-bridge/scripts/set_task_name.py "任務簡稱"

寫到 ~/.ai-office/task_names/<工作階段代號>.txt，之後每一筆事件都會帶上 task_name。
工作階段代號取環境變數 CLAUDE_CODE_SESSION_ID（雲端與新版 Claude Code 都有）；沒有就什麼都不做。
只存簡稱本身，不存提示詞原文。
"""
import os
import re
import sys

HOME = os.path.join(os.path.expanduser("~"), ".ai-office")


def main():
    name = " ".join(sys.argv[1:]).strip()
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    if not name or not re.fullmatch(r"[\w-]{1,80}", sid, flags=re.A):
        print("略過：沒有簡稱或沒有工作階段代號", file=sys.stderr)
        return 0
    name = re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]+", " ", name))[:24]
    d = os.path.join(HOME, "task_names")
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, sid + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(name)
    os.replace(tmp, os.path.join(d, sid + ".txt"))
    print("AI 辦公室任務簡稱：" + name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
