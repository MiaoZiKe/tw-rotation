#!/usr/bin/env python3
"""產生測試專案的 .claude/settings.json。用法：gen_settings.py <專案資料夾> <模式>
模式 all＝所有事件掛記錄腳本；http＝幾個事件直接用 HTTP 掛鉤（含壞掉與很慢的收件端）；stopcmd＝Stop 用腳本橋接；stophttp＝Stop 用 HTTP 掛鉤直接回 decision；ctx＝UserPromptSubmit／SessionStart 附加內容"""
import sys, json, os
proj, mode = sys.argv[1], sys.argv[2]
rig = os.path.dirname(os.path.abspath(__file__))
EVENTS = ["PreToolUse","PostToolUse","PostToolUseFailure","PostToolBatch","Notification","UserPromptSubmit","UserPromptExpansion","SessionStart","SessionEnd","Stop","StopFailure","SubagentStart","SubagentStop","PreCompact","PostCompact","PreModelSwitch","PostModelSwitch","PermissionRequest","PermissionDenied","Setup","TeammateIdle","TaskCreated","TaskCompleted","Elicitation","ElicitationResult","ConfigChange","WorktreeCreate","WorktreeRemove","InstructionsLoaded","CwdChanged","FileChanged","DirectoryAdded","MessageDisplay"]
SKIP = {"WorktreeCreate"}  # 這個事件的掛鉤會取代建立工作樹的行為，不掛
cmd = lambda tag: {"type": "command", "command": f"python3 {rig}/log_event.py {tag}", "timeout": 5}
hooks = {}
if mode == "all":
    for e in EVENTS:
        if e not in SKIP: hooks[e] = [{"hooks": [cmd("proj:" + e)]}]
elif mode == "http":
    U = "http://127.0.0.1:8765"
    for e in ["SessionStart", "UserPromptSubmit", "SubagentStart", "SubagentStop", "Stop", "SessionEnd"]:
        hooks[e] = [{"hooks": [{"type": "http", "url": f"{U}/event?e={e}", "timeout": 2, "headers": {"X-AIO-Token": "$AIO_TOKEN"}, "allowedEnvVars": ["AIO_TOKEN"]}, cmd("proj:" + e)]}]
    hooks["PreToolUse"] = [{"hooks": [
        {"type": "http", "url": f"{U}/slow", "timeout": 2},
        {"type": "http", "url": "http://127.0.0.1:9/dead", "timeout": 2},
        {"type": "http", "url": f"{U}/err", "timeout": 2},
        cmd("proj:PreToolUse")]}]
elif mode == "stopcmd":
    hooks["Stop"] = [{"hooks": [cmd("proj:Stop"), {"type": "command", "command": f"python3 {rig}/stop_bridge.py", "timeout": 5}]}]
elif mode == "stophttp":
    hooks["Stop"] = [{"hooks": [cmd("proj:Stop"), {"type": "http", "url": "http://127.0.0.1:8765/stopdecide", "timeout": 3}]}]
elif mode == "ctx":
    hooks["UserPromptSubmit"] = [{"hooks": [{"type": "command", "command": f"python3 {rig}/ctx_hook.py UserPromptSubmit"}]}]
    hooks["SessionStart"] = [{"hooks": [{"type": "command", "command": f"python3 {rig}/ctx_hook.py SessionStart"}]}]
os.makedirs(os.path.join(proj, ".claude"), exist_ok=True)
json.dump({"hooks": hooks}, open(os.path.join(proj, ".claude", "settings.json"), "w"), indent=1)
print("已寫入", os.path.join(proj, ".claude", "settings.json"), "模式", mode)
