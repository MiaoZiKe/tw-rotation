#!/usr/bin/env python3
"""把 AI Office 掛鉤寫進一份 Claude Code 設定檔（不用外掛系統時用；雲端環境的設定腳本也用這支）。

用法
  python3 install_hooks.py --settings ~/.claude/settings.json            安裝（重跑不會重複加）
  python3 install_hooks.py --settings ~/.claude/settings.json --remove   移除（只拿掉這支加的，其他設定原封不動）
  python3 install_hooks.py --settings x.json --dry-run                   只印出結果，不寫檔
  python3 install_hooks.py --settings ~/.claude/settings.json --instructions ~/.claude/CLAUDE.md
      另外在全域指示檔加一段「開工先取任務簡稱」（AI 辦公室名牌用）；重跑只更新那一段，--remove 一起拿掉

做法：讀 hooks/hooks.json，把 ${CLAUDE_PLUGIN_ROOT}/scripts/ 換成本資料夾的絕對路徑（bridge.py 事件上報、inbox.py 網站指令），合併進 settings 的 "hooks"。
認得自己加過的條目（指令裡有 ai-office-bridge 的 bridge.py 或 inbox.py），所以重跑只會更新，不會疊兩份。
設定檔壞掉（不是 JSON）就不動它、直接結束並回傳 1，絕不覆寫使用者的設定。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARK = "ai-office-bridge"
BEGIN = "<!-- ai-office-bridge:task-name:begin -->"
END = "<!-- ai-office-bridge:task-name:end -->"


def instructions_block():
    setter = os.path.join(HERE, "set_task_name.py").replace("\\", "/")
    return "\n".join([
        BEGIN,
        "## AI 辦公室：任務簡稱",
        "開工後、第一次回覆前，依使用者這次交代的任務取一個 6～12 字的繁體中文簡稱（像聊天室標題，例如「AI 辦公室接入」「台股儀表板修圖」），執行：",
        "`python3 " + setter + " \"簡稱\"`",
        "任務明顯換題時再執行一次。簡稱不放金鑰、網址、檔案路徑或個人資料。這一步不必跟使用者報告。",
        END,
    ])


def write_instructions(path, remove):
    path = os.path.expanduser(path)
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    i, j = old.find(BEGIN), old.find(END)
    if i != -1 and j != -1:
        old = (old[:i].rstrip("\n") + "\n" + old[j + len(END):].lstrip("\n")).strip("\n")
    new = old if remove else (old.rstrip("\n") + "\n\n" if old.strip() else "") + instructions_block()
    new = new.strip("\n") + "\n" if new.strip() else ""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".aio-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new)
    os.replace(tmp, path)
    print(("已移除" if remove else "已寫入") + " AI 辦公室任務簡稱指示：" + path)
SCRIPTS = ("bridge.py", "inbox.py")


def ours(entry):
    return any(MARK in str(h.get("command", "")) and any(x in str(h.get("command", "")) for x in SCRIPTS) for h in entry.get("hooks", []) if isinstance(h, dict))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--instructions", help="全域指示檔（例如 ~/.claude/CLAUDE.md），加一段「開工先取任務簡稱」")
    a = ap.parse_args()
    path = os.path.expanduser(a.settings)
    cfg = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except Exception:
            print("設定檔不是合法 JSON，為了不弄壞它，這次不動：" + path, file=sys.stderr)
            return 1
    if not isinstance(cfg, dict):
        print("設定檔格式不對（最外層不是物件），不動：" + path, file=sys.stderr)
        return 1
    with open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8") as f:
        mine = json.load(f)["hooks"]
    hooks = cfg.get("hooks") if isinstance(cfg.get("hooks"), dict) else {}
    for ev in list(hooks):
        if isinstance(hooks[ev], list):
            hooks[ev] = [e for e in hooks[ev] if not (isinstance(e, dict) and ours(e))]
            if not hooks[ev]:
                del hooks[ev]
    if not a.remove:
        for ev, entries in mine.items():
            for e in entries:
                e = json.loads(json.dumps(e).replace("${CLAUDE_PLUGIN_ROOT}/scripts/", HERE.replace("\\", "/") + "/"))
                hooks.setdefault(ev, []).append(e)
    if hooks:
        cfg["hooks"] = hooks
    else:
        cfg.pop("hooks", None)
    out = json.dumps(cfg, ensure_ascii=False, indent=2)
    if a.dry_run:
        print(out)
        return 0
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".aio-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out + "\n")
    os.replace(tmp, path)
    print(("已移除" if a.remove else "已安裝") + " AI Office 掛鉤：" + path)
    if a.instructions:
        write_instructions(a.instructions, a.remove)
    return 0


if __name__ == "__main__":
    sys.exit(main())
