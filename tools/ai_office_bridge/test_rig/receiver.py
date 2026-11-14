#!/usr/bin/env python3
"""假收件端（只聽 127.0.0.1）。
POST /event        記下內容回 200
POST /slow         睡 20 秒才回（測逾時）
POST /err          回 500
POST /stopdecide   記下內容；收件匣有訊息就回 {"decision":"block","reason":...}（測 HTTP 掛鉤能否直接讓 Claude 繼續）
POST /inbox/push   放一則待處理訊息  {"text": "..."}
GET  /inbox        取出一則待處理訊息（取完即刪）
POST /reply        記下 Claude 的回覆
"""
import json, sys, time, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
LOGDIR = os.environ.get("AIO_LOGDIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs"))
INBOX, LOCK = [], threading.Lock()
def log(name, obj):
    with LOCK, open(os.path.join(LOGDIR, name), "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n).decode("utf-8", "replace")
        try: return json.loads(raw)
        except Exception: return {"_raw": raw}
    def do_GET(self):
        if self.path.startswith("/inbox"):
            with LOCK: m = INBOX.pop(0) if INBOX else None
            return self._send(200, {"message": m} if m else {})
        self._send(404, {})
    def do_POST(self):
        body = self._body(); path = self.path.split("?")[0]
        rec = {"ts": round(time.time(), 3), "path": self.path, "headers": {k: v for k, v in self.headers.items()}, "body": body}
        if path == "/slow":
            log("http_events.jsonl", rec); time.sleep(20); return self._send(200, {})
        if path == "/err":
            log("http_events.jsonl", rec); return self._send(500, {"error": "boom"})
        if path == "/inbox/push":
            with LOCK: INBOX.append(body.get("text", ""))
            return self._send(200, {"queued": len(INBOX)})
        if path == "/reply":
            log("replies.jsonl", rec); return self._send(200, {})
        if path == "/stopdecide":
            log("http_events.jsonl", rec)
            with LOCK: m = INBOX.pop(0) if INBOX else None
            return self._send(200, {"decision": "block", "reason": "【AI Office 網站訊息】" + m} if m else {})
        log("http_events.jsonl", rec); self._send(200, {})
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
