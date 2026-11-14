#!/usr/bin/env python3
"""把 AI Office 掛鉤寫進一份 Claude Code 設定檔（不用外掛系統時用；雲端環境的設定腳本也用這支）。

用法
  python3 install_hooks.py --settings ~/.claude/settings.json            安裝（重跑不會重複加）
  python3 install_hooks.py --settings ~/.claude/settings.json --remove   移除（只拿掉這支加的，其他設定原封不動）
  python3 install_hooks.py --settings x.json --dry-run                   只印出結果，不寫檔

做法：讀 hooks/hooks.json，把 ${CLAUDE_PLUGIN_ROOT} 換成 bridge.py 的絕對路徑，合併進 settings 的 "hooks"。
認得自己加過的條目（指令裡有 ai-office-bridge 的 bridge.py），所以重跑只會更新，不會疊兩份。
設定檔壞掉（不是 JSON）就不動它、直接結束並回傳 1，絕不覆寫使用者的設定。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARK = "ai-office-bridge"


def ours(entry):
    return any(MARK in str(h.get("command", "")) and "bridge.py" in str(h.get("command", "")) for h in entry.get("hooks", []) if isinstance(h, dict))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", required=True)
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
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
        script = os.path.join(HERE, "bridge.py")
        for ev, entries in mine.items():
            for e in entries:
                e = json.loads(json.dumps(e).replace("${CLAUDE_PLUGIN_ROOT}/scripts/bridge.py", script.replace("\\", "/")))
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
