#!/usr/bin/env python3
"""UserPromptSubmit／SessionStart 掛鉤：用 hookSpecificOutput.additionalContext 附加內容。"""
import sys, json
ev = sys.argv[1]; sys.stdin.read()
code = "暗號-藍鯨-7391" if ev == "UserPromptSubmit" else "暗號-山貓-2468"
print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "additionalContext": f"（AI Office 橋接測試）{ev} 掛鉤附加的內容：{code}"}}, ensure_ascii=False))
