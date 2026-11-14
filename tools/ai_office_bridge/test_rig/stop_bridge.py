#!/usr/bin/env python3
"""Stop 掛鉤：①把對話紀錄檔最後一則助理文字送回收件端 ②查收件匣，有訊息就阻止停止並把訊息交給 Claude。
任何錯誤都安靜結束（exit 0），連線逾時 2 秒，絕不卡住工作階段。"""
import sys, json, os, urllib.request
BASE = os.environ.get("AIO_URL", "http://127.0.0.1:8765")
def http(method, path, obj=None):
    data = json.dumps(obj).encode() if obj is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=2) as r:
        return json.loads(r.read().decode() or "{}")
def last_assistant_text(path):
    text = ""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try: o = json.loads(line)
                except Exception: continue
                if o.get("type") == "assistant" and not o.get("isSidechain"):
                    t = "".join(c.get("text", "") for c in (o.get("message", {}).get("content") or []) if isinstance(c, dict) and c.get("type") == "text")
                    if t.strip(): text = t
    except Exception: pass
    return text
try:
    p = json.loads(sys.stdin.read() or "{}")
    reply = p.get("last_assistant_message") or last_assistant_text(p.get("transcript_path", ""))
    http("POST", "/reply", {"session_id": p.get("session_id"), "text": reply[:4000], "from": "last_assistant_message" if p.get("last_assistant_message") else "transcript", "stop_hook_active": p.get("stop_hook_active")})
    m = http("GET", "/inbox?session=" + str(p.get("session_id"))).get("message")
    if m:
        print(json.dumps({"decision": "block", "reason": "【AI Office 網站上擁有者傳來的新訊息，請當成使用者的下一句話來處理】\n" + m}, ensure_ascii=False))
except Exception:
    pass
sys.exit(0)
