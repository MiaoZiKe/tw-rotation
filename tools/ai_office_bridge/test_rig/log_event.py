#!/usr/bin/env python3
"""把掛鉤從標準輸入收到的 JSON 原樣寫進記錄檔（一行一筆）。用法：log_event.py <標籤>"""
import sys, json, os, time
tag = sys.argv[1] if len(sys.argv) > 1 else ""
raw = sys.stdin.read()
try:
    p = json.loads(raw)
except Exception:
    p = {"_raw": raw}
keys = ("CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DATA", "CLAUDE_ENV_FILE", "CLAUDE_CODE_REMOTE")
env = {k: os.environ[k] for k in keys if os.environ.get(k)}
log = os.environ.get("AIO_LOG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "events.jsonl")
with open(log, "a", encoding="utf-8") as f:
    f.write(json.dumps({"ts": round(time.time(), 3), "tag": tag, "env": env, "payload": p}, ensure_ascii=False) + "\n")
