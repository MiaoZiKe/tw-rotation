#!/usr/bin/env python3
"""本機假會員服務（只給 AI 辦公室端到端測試用；scripts/e2e/ai_office_e2e.py 會自己起）。

為什麼要它：收件服務（workers/ai-office-bridge）判斷「是不是站長」要問會員 Worker（tw-account）的 POST /v1/me。
本機沒有 Google 登入，也不能連線上的會員服務，所以用這支替代：
  · 收件服務用 wrangler dev 的 --var ACCOUNT_API_URL:http://127.0.0.1:<埠> 指過來（worker.js 既有的替代路徑，正式環境走服務綁定 ACCOUNT）。
  · 只認一組「站長測試權杖」（啟動參數給，測試腳本每次隨機產生，不是任何真金鑰）→ {"user":{"admin":true}}；其他權杖 → admin:false。
用法：python3 fake_account.py <埠> <站長測試權杖>
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8807
OWNER = sys.argv[2] if len(sys.argv) > 2 else ""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            b = json.loads(self.rfile.read(n).decode() or "{}")
        except Exception:
            b = {}
        if self.path.rstrip("/") == "/v1/me":
            ok = bool(OWNER) and b.get("t") == OWNER
            out = {"user": {"email": "owner@example.test", "admin": ok, "owner": ok}} if ok else {"user": {"admin": False}}
            data = json.dumps(out).encode()
            self.send_response(200)
        else:
            data = b'{"error":"not_found"}'
            self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
