#!/usr/bin/env python3
"""AI Office 接入元件（雛形）——單一掛鉤腳本，所有事件共用。

設計原則
1. 絕不卡住使用者：任何錯誤一律安靜結束（exit 0）；連線逾時預設 2 秒。
2. 預設不送內容：提示詞、程式碼、工具輸入輸出、完整路徑都不送；只送事件種類、
   代號、專案顯示名與雜湊、子 Agent 類型、說明（截短）、Token 合計。
3. 金鑰不進 repo：從環境變數或使用者家目錄的設定檔讀。

設定（環境變數優先，其次設定檔 ~/.ai-office/config.json，可用 AIO_CONFIG 改路徑）
  AIO_URL      收件端網址（沒有就什麼都不做）
  AIO_TOKEN    接入碼（放在 Authorization: Bearer）
  AIO_CHAT     "1"＝開啟網站對話：Stop 時送出最後一則回覆，並查收件匣，有訊息就讓 Claude 繼續
  AIO_RAW_LOG  （只給測試用）把收到的原始 JSON 寫到這個檔案
"""
import sys, json, os, time, hashlib, urllib.request

EVENT = sys.argv[1] if len(sys.argv) > 1 else ""
TIMEOUT = 2.0


def load_cfg():
    cfg = {}
    path = os.environ.get("AIO_CONFIG") or os.path.join(os.path.expanduser("~"), ".ai-office", "config.json")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        pass
    for k in ("AIO_URL", "AIO_TOKEN", "AIO_CHAT", "AIO_RAW_LOG"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def http(cfg, method, path, obj=None):
    data = json.dumps(obj, ensure_ascii=False).encode() if obj is not None else None
    hdr = {"Content-Type": "application/json", "User-Agent": "ai-office-bridge/0.0.1"}
    if cfg.get("AIO_TOKEN"):
        hdr["Authorization"] = "Bearer " + cfg["AIO_TOKEN"]
    req = urllib.request.Request(cfg["AIO_URL"].rstrip("/") + path, data=data, method=method, headers=hdr)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # 會沿用環境的 HTTPS_PROXY／no_proxy
        return json.loads(r.read().decode() or "{}")


def short(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + "…"


def usage_total(path):
    """把對話紀錄檔裡每一則助理訊息的 usage 加總（同一個 requestId 只算最後一筆）。"""
    per = {}
    try:
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                u = (o.get("message") or {}).get("usage") if o.get("type") == "assistant" else None
                if u:
                    per[o.get("requestId") or i] = u
    except Exception:
        return None
    tot = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "requests": len(per)}
    for u in per.values():
        tot["input"] += u.get("input_tokens") or 0
        tot["output"] += u.get("output_tokens") or 0
        tot["cache_read"] += u.get("cache_read_input_tokens") or 0
        tot["cache_write"] += u.get("cache_creation_input_tokens") or 0
    return tot


def sanitize(p):
    """只留白名單欄位。完整路徑改成「資料夾名＋雜湊」。"""
    cwd = p.get("cwd") or ""
    ev = {
        "event": p.get("hook_event_name") or EVENT,
        "ts": round(time.time(), 3),  # 掛鉤資料本身沒有時間欄位，由腳本補
        "session_id": p.get("session_id"),
        "prompt_id": p.get("prompt_id"),
        "project_name": os.path.basename(cwd.rstrip("/")) or None,
        "project_hash": hashlib.sha256(cwd.encode()).hexdigest()[:16] if cwd else None,
        "cloud": os.environ.get("CLAUDE_CODE_REMOTE") == "true",
    }
    for k in ("agent_id", "agent_type", "source", "reason", "permission_mode", "stop_hook_active", "tool_use_id", "duration_ms"):
        if p.get(k) is not None:
            ev[k] = p[k]
    if p.get("tool_name"):
        ev["tool_name"] = p["tool_name"]
        ti = p.get("tool_input") or {}
        if p["tool_name"] in ("Agent", "Task"):  # 派工：只留類型與短說明，不送派工提示詞
            ev["subagent_type"] = ti.get("subagent_type")
            ev["description"] = short(ti.get("description"), 80)
            tr = p.get("tool_response")
            if isinstance(tr, dict):
                ev["spawned_agent_id"] = tr.get("agentId")
                ev["spawn_status"] = tr.get("status")  # completed＝前景跑完；async_launched＝背景執行（此時還沒有 Token 數）
                for k in ("totalTokens", "totalDurationMs", "totalToolUseCount", "resolvedModel"):
                    if tr.get(k) is not None:
                        ev[k] = tr[k]
    if ev["event"] == "UserPromptSubmit":
        pr = p.get("prompt") or ""
        ev["prompt_chars"] = len(pr)
        ev["prompt_is_system"] = pr.lstrip().startswith("<")  # 例如背景子 Agent 完成通知，不是真人輸入
    if ev["event"] == "Notification":
        ev["notification_type"] = p.get("notification_type")
    if ev["event"] == "SubagentStop":
        ev["usage"] = usage_total(p.get("agent_transcript_path") or "")
    if ev["event"] in ("Stop", "SessionEnd"):
        tp = p.get("transcript_path") or ""
        ev["usage_main"] = usage_total(tp)
        # 子 Agent 的紀錄檔在「<主紀錄檔去掉 .jsonl>/subagents/agent-<代號>.jsonl」；
        # SubagentStop 當下最後一則還沒寫進檔案（實測會少算），所以在回合結束時再整批重算一次
        sub = os.path.join(tp[:-6], "subagents") if tp.endswith(".jsonl") else ""
        if sub and os.path.isdir(sub):
            ev["usage_subagents"] = {f[6:-6]: usage_total(os.path.join(sub, f))
                                     for f in sorted(os.listdir(sub)) if f.startswith("agent-") and f.endswith(".jsonl")}
    if isinstance(p.get("background_tasks"), list):
        ev["background_running"] = sum(1 for t in p["background_tasks"] if t.get("status") == "running")
    return ev


def main():
    raw = sys.stdin.read()
    cfg = load_cfg()
    try:
        p = json.loads(raw or "{}")
    except Exception:
        p = {}
    if cfg.get("AIO_RAW_LOG"):
        try:
            with open(cfg["AIO_RAW_LOG"], "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": round(time.time(), 3), "tag": "plugin:" + EVENT,
                                    "plugin_root": os.environ.get("CLAUDE_PLUGIN_ROOT"), "payload": p}, ensure_ascii=False) + "\n")
        except Exception:
            pass
    if not cfg.get("AIO_URL"):
        return
    try:
        http(cfg, "POST", "/event", sanitize(p))
    except Exception:
        pass
    if EVENT == "Stop" and cfg.get("AIO_CHAT") == "1":
        try:
            # 只有開啟對話功能才送回覆文字（擁有者自己看的對話），截短 8000 字
            http(cfg, "POST", "/reply", {"session_id": p.get("session_id"), "text": short(p.get("last_assistant_message"), 8000)})
            m = http(cfg, "GET", "/inbox?session=" + str(p.get("session_id"))).get("message")
            if m:
                print(json.dumps({"decision": "block",
                                  "reason": "【AI Office 網站上，擁有者本人傳來的新訊息。請把它當成使用者的下一句話來處理並回覆】\n" + short(m, 8000)},
                                 ensure_ascii=False))
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
