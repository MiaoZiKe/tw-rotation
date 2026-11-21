#!/usr/bin/env python3
"""極簡 MCP 伺服器（stdio）：提供「讀取 AI Office 待處理訊息」與「回覆」兩個工具。只為驗證可行性。
收件端網址讀環境變數 AIO_URL（預設 http://127.0.0.1:8765）。"""
import sys, json, os, urllib.request
BASE = os.environ.get("AIO_URL", "http://127.0.0.1:8765")
def http(method, path, obj=None):
    data = json.dumps(obj, ensure_ascii=False).encode() if obj is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as r:
        return json.loads(r.read().decode() or "{}")
TOOLS = [
    {"name": "get_pending_messages", "description": "讀取擁有者在 AI Office 網站上留給這個工作階段的待處理訊息（取出後即刪）。",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "send_reply", "description": "把回覆送回 AI Office 網站的對話窗。",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
]
def handle(m):
    mid, meth, params = m.get("id"), m.get("method"), m.get("params") or {}
    if meth == "initialize":
        return {"protocolVersion": params.get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}},
                "serverInfo": {"name": "ai-office-inbox", "version": "0.0.1"}}
    if meth == "tools/list":
        return {"tools": TOOLS}
    if meth == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        try:
            if name == "get_pending_messages":
                msg = http("GET", "/inbox").get("message")
                text = json.dumps({"messages": [msg] if msg else []}, ensure_ascii=False)
            elif name == "send_reply":
                http("POST", "/reply", {"text": args.get("text", ""), "from": "mcp"}); text = "已送出"
            else:
                return {"content": [{"type": "text", "text": "未知的工具"}], "isError": True}
            return {"content": [{"type": "text", "text": text}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": "收件端連線失敗：" + str(e)}], "isError": True}
    if meth == "ping":
        return {}
    return None
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: m = json.loads(line)
    except Exception: continue
    if "id" not in m: continue  # 通知不用回
    res = handle(m)
    out = {"jsonrpc": "2.0", "id": m["id"]}
    if res is None: out["error"] = {"code": -32601, "message": "method not found"}
    else: out["result"] = res
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n"); sys.stdout.flush()
