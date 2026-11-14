#!/usr/bin/env python3
"""AI Office 接入元件（第一版）——單一掛鉤腳本，所有事件共用。

做的事：把 Claude Code 的掛鉤事件「去識別」之後送到 AI Office 收件端（workers/ai-office-bridge）。

絕對守的規矩
1. 不卡住使用者：讀完標準輸入就把送出交給背景子程序，自己立刻結束（exit 0）；連線逾時 2 秒；任何錯誤一律吞掉。
   收件端連不上或回錯：記一個「暫停」旗標，暫停期間的事件直接丟掉，不會每個事件都等 2 秒。
2. 不送內容：提示詞全文、派工全文、指令、檔名、完整路徑、工具輸入輸出、程式碼一律不送。
   只送：事件種類、隨機代號、專案資料夾名＋路徑雜湊、子 Agent 類型、工具「類別」、派工短說明與回覆摘要（遮掉路徑／網址／信箱／檔名後截短）。
3. 金鑰不進 repo：接入碼從環境變數或家目錄設定檔讀；雲端版建議完全不設，由雲端環境的「網路金鑰」在代理端注入標頭（腳本不持有金鑰）。

設定（環境變數優先，其次 ~/.ai-office/config.json；可用 AIO_CONFIG 指定設定檔路徑）
  AIO_URL       收件端網址，例如 https://tw-ai-office-bridge.<你的子網域>.workers.dev（沒有就什麼都不做）
  AIO_TOKEN     接入碼（放在 Authorization: Bearer）。雲端由代理注入時不要設
  AIO_SUMMARY   "0"＝連派工短說明與回覆摘要都不送（只送類別與代號）；預設 "1"
  AIO_DISABLE   "1"＝完全停用
  AIO_RAW_LOG   （只給測試）把收到的原始 JSON 寫到這個檔案
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

VERSION = "0.1.0"
EVENT = sys.argv[1] if len(sys.argv) > 1 else ""
TIMEOUT = 2.0
HOME = os.path.join(os.path.expanduser("~"), ".ai-office")

READ = {"Read", "Glob", "Grep", "LS", "NotebookRead"}
WRITE = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SEARCH = {"WebSearch", "WebFetch"}
DISPATCH = {"Agent", "Task"}
ASK = {"AskUserQuestion"}
TEST_RE = re.compile(r"\b(pytest|unittest|node\s+--test|npm\s+(run\s+)?test|yarn\s+test|pnpm\s+test|jest|vitest|mocha|go\s+test|cargo\s+test|_uitest|_preview|playwright\s+test)\b")
DEPLOY_RE = re.compile(r"\b(git\s+push|wrangler\s+(deploy|publish)|deploy\b|gh\s+workflow\s+run|vercel|netlify\s+deploy|firebase\s+deploy)")
WAIT_RE = re.compile(r"\b(deploy_wait|gh\s+run\s+watch|sleep\s+\d)")
FILE_RE = re.compile(r"[\w.-]+\.(?:m?js|cjs|tsx?|jsx|py|json|ya?ml|toml|md|html?|css|sh|bat|ps1|go|rs|java|kt|swift|rb|php|sql|csv|txt|png|jpe?g|gif|svg|pdf|parquet|lock|env|ini|cfg|xml|vue|c|h|cpp|ipynb)\b", re.I | re.A)


def load_cfg():
    cfg = {}
    path = os.environ.get("AIO_CONFIG") or os.path.join(HOME, "config.json")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f) or {}
    except Exception:
        cfg = {}
    for k in ("AIO_URL", "AIO_TOKEN", "AIO_SUMMARY", "AIO_DISABLE", "AIO_RAW_LOG"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def scrub(s, n):
    """去識別：去控制字元、遮網址／信箱／路徑／檔名／疑似金鑰，再截短。收件端會再做一次。"""
    if not isinstance(s, str):
        return None
    s = re.sub(r"[\x00-\x1f\x7f]+", " ", s)
    s = re.sub(r"https?://\S+", "〔網址〕", s, flags=re.I)
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "〔信箱〕", s, flags=re.A)
    s = re.sub(r"(?:[A-Za-z]:\\|~/|/)(?:[^\s/\\]+[/\\])+[^\s/\\]*", "〔路徑〕", s)
    s = re.sub(r"(?:[\w.-]*[A-Za-z][\w.-]*/)+[\w.-]+", "〔路徑〕", s, flags=re.A)
    s = FILE_RE.sub("〔檔名〕", s)
    s = re.sub(r"\b[A-Za-z0-9_\-]{28,}\b", "〔遮蔽〕", s, flags=re.A)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None
    return s if len(s) <= n else s[: n - 1] + "…"


def first_line(s):
    if not isinstance(s, str):
        return None
    for line in s.splitlines():
        line = line.strip(" #*>-`")
        if line:
            return line
    return None


def tool_category(name, tool_input):
    """工具名稱 → 類別。指令內容只在本機拿來判斷類別，不會送出去。"""
    if name in DISPATCH:
        return "dispatch"
    if name in ASK:
        return "ask"
    if name in READ:
        return "read"
    if name in WRITE:
        return "write"
    if name in SEARCH:
        return "search"
    if name == "Bash":
        cmd = str((tool_input or {}).get("command") or "")
        if WAIT_RE.search(cmd):
            return "wait"
        if TEST_RE.search(cmd):
            return "test"
        if DEPLOY_RE.search(cmd):
            return "deploy"
    return "other"


def perm_category(name):
    if name == "Bash":
        return "command"
    if name in WRITE:
        return "edit"
    if name in SEARCH:
        return "web"
    return "other"


def usage_total(path):
    """把對話紀錄檔裡每一則助理訊息的 usage 加總（同一個 requestId 只算最後一筆）。只回數字，不讀內容。"""
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


def tokens(u):
    return None if not u else u["input"] + u["output"] + u["cache_write"]


def sanitize(p, cfg):
    """只留白名單欄位。完整路徑改成「資料夾名＋雜湊」。回傳 None＝這筆不送。"""
    name = p.get("hook_event_name") or EVENT
    cwd = p.get("cwd") or ""
    summ = cfg.get("AIO_SUMMARY", "1") != "0"
    ev = {
        "event": name,
        "ts": int(time.time() * 1000),        # 掛鉤資料本身沒有時間欄位，由腳本補
        "session_id": p.get("session_id"),
        "project_name": scrub(os.path.basename(cwd.rstrip("/\\")), 60) if cwd else None,
        "project_hash": hashlib.sha256(cwd.encode()).hexdigest()[:16] if cwd else None,
        "cloud": os.environ.get("CLAUDE_CODE_REMOTE") == "true",
    }
    for k in ("agent_id", "agent_type", "source", "reason", "permission_mode"):
        if isinstance(p.get(k), str):
            ev[k] = p[k]
    tool = p.get("tool_name")
    ti = p.get("tool_input") if isinstance(p.get("tool_input"), dict) else {}
    if name in ("PreToolUse", "PostToolUse"):
        cat = tool_category(tool, ti)
        if name == "PostToolUse":
            if cat == "ask":
                cat = "answered"
            elif cat != "dispatch":
                return None                   # 其他工具的「用完了」不送（量太大、對演出沒有用）
        ev["tool_category"] = cat
        if cat == "dispatch":                 # 派工：只留類型與短說明，不送派工全文
            ev["subagent_type"] = ti.get("subagent_type") or "general-purpose"
            if summ:
                ev["description"] = scrub(ti.get("description"), 80)
            tr = p.get("tool_response")
            if isinstance(tr, dict):
                ev["spawned_agent_id"] = tr.get("agentId")
                ev["spawn_status"] = tr.get("status")
                for k in ("totalTokens", "totalDurationMs", "totalToolUseCount"):
                    if isinstance(tr.get(k), (int, float)):
                        ev[k] = tr[k]
    if name == "PermissionRequest":
        ev["perm_category"] = perm_category(tool)
    if name == "UserPromptSubmit":
        pr = p.get("prompt") or ""
        ev["prompt_chars"] = len(pr)
        ev["prompt_is_system"] = pr.lstrip().startswith("<")  # 例如背景子 Agent 完成通知，不是真人輸入
    if name == "Notification":
        ev["notification_type"] = p.get("notification_type")
    if name == "StopFailure":
        err = p.get("error") if isinstance(p.get("error"), dict) else {}
        et = p.get("error_type") or err.get("type") or p.get("reason")
        if isinstance(et, str):
            ev["error_type"] = re.sub(r"[^A-Za-z0-9_.:-]", "_", et)[:40]
    if name in ("SubagentStop", "Stop") and summ:
        ev["summary"] = scrub(first_line(p.get("last_assistant_message")), 120)
    if name == "SubagentStop":
        u = usage_total(p.get("agent_transcript_path") or "")
        if u:
            ev["usage"] = u
    if name in ("Stop", "SessionEnd"):
        tp = p.get("transcript_path") or ""
        ev["usage_main"] = tokens(usage_total(tp))
        # 子 Agent 的紀錄檔在「<主紀錄檔去掉 .jsonl>/subagents/agent-<代號>.jsonl」；
        # SubagentStop 當下最後一則還沒寫進檔案（實測會少算），所以回合結束時再整批重算一次
        sub = os.path.join(tp[:-6], "subagents") if tp.endswith(".jsonl") else ""
        if sub and os.path.isdir(sub):
            m = {}
            for f in sorted(os.listdir(sub))[:50]:
                if f.startswith("agent-") and f.endswith(".jsonl"):
                    t = tokens(usage_total(os.path.join(sub, f)))
                    if t is not None:
                        m[f[6:-6]] = t
            if m:
                ev["usage_subagents"] = m
    if isinstance(p.get("background_tasks"), list):
        ev["background_running"] = sum(1 for t in p["background_tasks"] if isinstance(t, dict) and t.get("status") == "running")
    rl = read_rate_limits()
    if rl:
        ev["rate_limits"] = rl
    return {k: v for k, v in ev.items() if v is not None}


def read_rate_limits():
    """選用：若使用者自己的狀態列腳本把 rate_limits 存到 ~/.ai-office/rate_limits.json（15 分鐘內），順便帶上。沒有就不送。"""
    try:
        path = os.path.join(HOME, "rate_limits.json")
        if time.time() - os.path.getmtime(path) > 900:
            return None
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        return r if isinstance(r, dict) else None
    except Exception:
        return None


# ── 節流：同一個工作階段／子 Agent 的工具類別沒變，20 秒內不重送 ──
def throttled(ev):
    if ev.get("event") != "PreToolUse" or ev.get("tool_category") in ("dispatch", "ask"):
        return False
    try:
        d = os.path.join(HOME, "state")
        os.makedirs(d, exist_ok=True)
        key = re.sub(r"[^A-Za-z0-9_-]", "_", str(ev.get("session_id")))[:80]
        path = os.path.join(d, key + ".json")
        try:
            with open(path, encoding="utf-8") as f:
                st = json.load(f)
        except Exception:
            st = {}
        who = ev.get("agent_id") or "main"
        last = st.get(who) or [None, 0]
        now = time.time()
        if last[0] == ev["tool_category"] and now - last[1] < 20:
            return True
        st[who] = [ev["tool_category"], now]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except Exception:
        return False
    return False


# ── 暫停旗標：收件端連不上就暫停一陣子，避免每個事件都等逾時 ──
def paused():
    try:
        with open(os.path.join(HOME, "pause_until"), encoding="utf-8") as f:
            return time.time() < float(f.read().strip() or 0)
    except Exception:
        return False


def pause(sec):
    try:
        os.makedirs(HOME, exist_ok=True)
        with open(os.path.join(HOME, "pause_until"), "w", encoding="utf-8") as f:
            f.write(str(time.time() + sec))
    except Exception:
        pass


def send(cfg, ev):
    data = json.dumps(ev, ensure_ascii=False).encode()
    hdr = {"Content-Type": "application/json", "User-Agent": "ai-office-bridge/" + VERSION}
    if cfg.get("AIO_TOKEN"):
        hdr["Authorization"] = "Bearer " + cfg["AIO_TOKEN"]
    req = urllib.request.Request(cfg["AIO_URL"].rstrip("/") + "/v1/events", data=data, method="POST", headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # 沿用環境的 HTTPS_PROXY（雲端由代理注入接入碼）
            r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            pause(1800)      # 接入碼不對：30 分鐘內不再送（換碼後刪掉 ~/.ai-office/pause_until 即可立刻恢復）
        elif e.code == 429:
            pause(60)
        elif e.code >= 500:
            pause(120)
    except Exception:
        pause(120)           # 連不上、逾時


def background(fn):
    """交給背景子程序做，父程序立刻結束，不讓 Claude Code 等。沒有 fork（Windows）就直接做（仍有 2 秒逾時）。"""
    if not hasattr(os, "fork"):
        fn()
        return
    try:
        pid = os.fork()
    except Exception:
        fn()
        return
    if pid > 0:
        return
    try:
        os.setsid()
        dn = os.open(os.devnull, os.O_RDWR)
        for fd in (0, 1, 2):
            os.dup2(dn, fd)
        fn()
    except Exception:
        pass
    finally:
        os._exit(0)


def main():
    raw = sys.stdin.read()
    cfg = load_cfg()
    if cfg.get("AIO_DISABLE") == "1":
        return
    try:
        p = json.loads(raw or "{}")
    except Exception:
        p = {}
    if not isinstance(p, dict):
        return
    if cfg.get("AIO_RAW_LOG"):
        try:
            with open(cfg["AIO_RAW_LOG"], "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": round(time.time(), 3), "tag": "plugin:" + EVENT, "payload": p}, ensure_ascii=False) + "\n")
        except Exception:
            pass
    if not cfg.get("AIO_URL") or paused():
        return
    ev = sanitize(p, cfg)
    if not ev or throttled(ev):
        return
    background(lambda: send(cfg, ev))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
