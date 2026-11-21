#!/usr/bin/env python3
"""背景等待收件匣（搭配掛鉤的 asyncRewake）。每秒查一次收件端，最多等 AIO_WAIT 秒（預設 60）。
有訊息：把訊息寫到標準錯誤並以 exit 2 結束 → Claude Code 會把閒置中的模型叫醒並把這段文字交給它。
沒訊息或任何錯誤：exit 0，什麼都不發生。"""
import sys, json, os, time, urllib.request
BASE = os.environ.get("AIO_URL", "http://127.0.0.1:8765")
try: sid = json.loads(sys.stdin.read() or "{}").get("session_id")
except Exception: sid = None
end = time.time() + float(os.environ.get("AIO_WAIT", "60"))
while time.time() < end:
    try:
        with urllib.request.urlopen(BASE + "/inbox?session=" + str(sid), timeout=2) as r:
            m = json.loads(r.read().decode() or "{}").get("message")
        if m:
            sys.stderr.write("【AI Office 網站上，擁有者本人傳來的新訊息。請把它當成使用者的下一句話來處理並回覆】\n" + m + "\n")
            sys.exit(2)
    except SystemExit: raise
    except Exception: pass
    time.sleep(1)
sys.exit(0)
