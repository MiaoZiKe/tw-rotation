#!/usr/bin/env python3
"""外掛的自我測試（不需要網路、不需要 Claude Code）：python3 test_bridge.py
驗：去識別（不送提示詞、指令、檔名、路徑）、工具類別判斷、節流、背景送出不拖慢、收件端連不上時安靜結束並暫停、
install_hooks.py 重跑不重複、移除只拿掉自己的。"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import http.server

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bridge  # noqa: E402

fails = []


def ok(name, cond, extra=""):
    print(("通過 " if cond else "失敗 ") + name + ("" if cond else "  " + str(extra)[:300]))
    if not cond:
        fails.append(name)


SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "..", "samples", "hook_payloads.sanitized.json"), encoding="utf-8"))["事件"]

# ── 去識別 ──
up = bridge.sanitize(SAMPLE["UserPromptSubmit"], {})
ok("使用者指令：不送全文，只送字數", "prompt" not in up and up["prompt_chars"] > 10 and up["prompt_is_system"] is False, up)
ok("路徑：不送完整路徑，只送資料夾名與雜湊", "cwd" not in up and "transcript_path" not in up and len(up["project_hash"]) == 16, up)
dis = bridge.sanitize(SAMPLE["PreToolUse（Agent）"], {})
ok("派工：類別 dispatch、類型、短說明；沒有派工全文", dis["tool_category"] == "dispatch" and dis["subagent_type"] == "general-purpose" and dis["description"] == "列出檔案" and "prompt" not in json.dumps(dis), dis)
bash = bridge.sanitize(SAMPLE["PreToolUse（Bash，子 Agent 內）"], {})
ok("子 Agent 內的指令：只送類別，不送指令內容", bash["tool_category"] == "other" and "ls" not in json.dumps(bash, ensure_ascii=False).replace("false", "") and bash["agent_id"], bash)
stop = bridge.sanitize(SAMPLE["Stop"], {})
ok("回合結束：摘要只取第一行", stop["summary"].startswith("我已派出子 Agent"), stop)
sub = bridge.sanitize(SAMPLE["SubagentStop"], {})
ok("交件：摘要取第一行（不送全文）", sub["summary"] == "目前工作目錄只有一個檔案：", sub)
ok("交件：背景工作數", sub["background_running"] == 1, sub)
nos = bridge.sanitize(SAMPLE["SubagentStop"], {"AIO_SUMMARY": "0"})
ok("AIO_SUMMARY=0：連摘要都不送", "summary" not in nos, nos)
ok("其他工具的 PostToolUse 不送", bridge.sanitize(SAMPLE["PostToolUse（Bash，子 Agent 內）"], {}) is None)
sys_p = bridge.sanitize(SAMPLE["UserPromptSubmit（背景子 Agent 完成通知，不是真人輸入）"], {})
ok("背景完成通知標成系統訊息", sys_p["prompt_is_system"] is True, sys_p)
s = bridge.scrub("改 /home/andy/tw-rotation/site/app.js 跟 site/m4/x.css，看 https://a.b/c 問 a@b.com 金鑰 tokABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", 200)
ok("文字去識別：路徑、檔名、網址、信箱、金鑰都遮掉", not any(x in s for x in ["andy", "app.js", "x.css", "a.b/c", "a@b.com", "tokABCDEF"]), s)
ok("文字去識別：中文不被吃掉", bridge.scrub("修改app.js的按鈕", 80) == "修改〔檔名〕的按鈕", bridge.scrub("修改app.js的按鈕", 80))

# ── 專案名稱與雜湊（2026-11-15：一個專案一間辦公室） ──
_tmp = tempfile.mkdtemp()
_d1, _d2, _d3 = (os.path.join(_tmp, n) for n in ("copy-one", "copy-two", "plain"))
for _d in (_d1, _d2, _d3):
    os.makedirs(_d)
for _d, _url in ((_d1, "https://github.com/someone/tw-rotation.git"), (_d2, "http://local_proxy@127.0.0.1:41234/git/someone/tw-rotation")):
    subprocess.run(["git", "init", "-q", _d], check=True)
    subprocess.run(["git", "-C", _d, "remote", "add", "origin", _url], check=True)
_n1, _h1 = bridge.project_info(_d1)
_n2, _h2 = bridge.project_info(_d2)

# ── 專案名冊（2026-11-16）：SessionStart 附上專案 .claude/agents/*.md 的檔名（去副檔名），只送名稱 ──
_ag = os.path.join(_d1, ".claude", "agents")
os.makedirs(_ag)
for _f in ("inspector.md", "my-agent.md", "bad name.md", "x.txt", "老師.md", "z" * 70 + ".md"):
    open(os.path.join(_ag, _f), "w").write("---\nname: secret-body-text\n---\n機密內文不能出現\n")
_ss = bridge.sanitize({"hook_event_name": "SessionStart", "session_id": "s1", "cwd": _d1}, {})
ok("名冊：SessionStart 帶 agent_files，只有合格的檔名（去 .md、排序）", _ss["agent_files"] == ["inspector", "my-agent"], _ss.get("agent_files"))
ok("名冊：不送檔案內容與路徑", "機密內文" not in json.dumps(_ss, ensure_ascii=False) and "secret-body-text" not in json.dumps(_ss) and _ag not in json.dumps(_ss), _ss)
_sub = os.path.join(_d1, "deep", "er")
os.makedirs(_sub)
ok("名冊：在子資料夾開 Claude 也找得到專案根的名冊", bridge.sanitize({"hook_event_name": "SessionStart", "session_id": "s1", "cwd": _sub}, {})["agent_files"] == ["inspector", "my-agent"])
_e0 = bridge.sanitize({"hook_event_name": "SessionStart", "session_id": "s1", "cwd": _d3}, {})
ok("名冊：沒有 .claude/agents 也送空清單（收件端才清得掉舊名冊）", _e0["agent_files"] == [], _e0.get("agent_files"))
ok("名冊：其他事件不帶 agent_files", "agent_files" not in bridge.sanitize({"hook_event_name": "Stop", "session_id": "s1", "cwd": _d1}, {}))
for _i in range(60):
    open(os.path.join(_ag, "many-%02d.md" % _i), "w").write("x")
ok("名冊：最多 50 個", len(bridge.agent_files(_d1)) == 50, len(bridge.agent_files(_d1)))
_n3, _h3 = bridge.project_info(_d3)
ok("專案名：優先用 git 遠端的儲存庫名（不是資料夾名）", _n1 == "tw-rotation" and _n2 == "tw-rotation", (_n1, _n2))
ok("專案雜湊：同一個儲存庫的不同複本／不同資料夾是同一個專案", _h1 == _h2 and len(_h1) == 16, (_h1, _h2))
ok("專案名：沒有 git 就用資料夾名，雜湊不同於有遠端的", _n3 == "plain" and _h3 != _h1, (_n3, _h3))
ok("專案：不送遠端網址與帳密", "someone" not in json.dumps(bridge.sanitize({"hook_event_name": "Stop", "cwd": _d2, "session_id": "s"}, {})) and "local_proxy" not in json.dumps(bridge.sanitize({"hook_event_name": "Stop", "cwd": _d2, "session_id": "s"}, {})))
ok("專案：沒有 cwd 就沒有專案名與雜湊", bridge.project_info("") == (None, None) and bridge.project_info(None) == (None, None))
ok("sanitize 用 project_info（事件裡的雜湊與取指令用的一致）", bridge.sanitize({"hook_event_name": "Stop", "cwd": _d1, "session_id": "s"}, {})["project_hash"] == _h1)

# ── 工具類別 ──
cases = [("Read", {}, "read"), ("Grep", {}, "read"), ("Edit", {}, "write"), ("WebSearch", {}, "search"), ("Bash", {"command": "python -m pytest tests -q"}, "test"),
         ("Bash", {"command": "git push origin main"}, "deploy"), ("Bash", {"command": "python scripts/deploy_wait.py --branch main"}, "wait"), ("Bash", {"command": "ls"}, "other"),
         ("Agent", {}, "dispatch"), ("AskUserQuestion", {}, "ask"), ("mcp__x__y", {}, "other")]
ok("工具類別判斷", all(bridge.tool_category(n, i) == c for n, i, c in cases), [(n, bridge.tool_category(n, i)) for n, i, c in cases])

# ── 收件端（本機假的） ──
got = []


class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        got.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": json.loads(self.rfile.read(n) or b"{}")})
        if "slow" in os.environ.get("AIO_TEST_MODE", ""):
            time.sleep(5)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = "http://127.0.0.1:%d" % srv.server_address[1]

with tempfile.TemporaryDirectory() as home:
    env = {**os.environ, "HOME": home, "AIO_URL": url, "AIO_TOKEN": "aio_test_token", "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"}
    env.pop("AIO_CONFIG", None)

    def run(ev, payload, extra_env=None):
        t = time.time()
        subprocess.run([sys.executable, os.path.join(HERE, "bridge.py"), ev], input=json.dumps(payload).encode(), env={**env, **(extra_env or {})}, timeout=10)
        return time.time() - t

    dt = run("SubagentStart", SAMPLE["SubagentStart"])
    for _ in range(40):
        if got:
            break
        time.sleep(0.05)
    ok("送出：收件端收到、路徑 /v1/events、帶接入碼", got and got[0]["path"] == "/v1/events" and got[0]["auth"] == "Bearer aio_test_token", got[:1])
    ok("送出：內容是去識別後的", got and got[0]["body"].get("agent_type") == "general-purpose" and "cwd" not in got[0]["body"], got[:1])
    os.environ["AIO_TEST_MODE"] = "slow"
    dt = run("Stop", SAMPLE["Stop"])
    ok("背景送出：收件端很慢（5 秒）時，掛鉤本身 1 秒內結束", dt < 1.0, dt)
    os.environ["AIO_TEST_MODE"] = ""
    # 節流：同一個子 Agent 連兩次讀檔，只送一次
    n0 = len(got)
    rd = dict(SAMPLE["PreToolUse（Bash，子 Agent 內）"], tool_name="Read", tool_input={"file_path": "/x/y.py"})
    run("PreToolUse", rd)
    run("PreToolUse", rd)
    time.sleep(0.6)
    ok("節流：同類別 20 秒內只送一次", len(got) - n0 == 1, len(got) - n0)
    # 連不上：安靜結束、記暫停旗標，暫停期間不再嘗試
    dt = run("SessionStart", SAMPLE["SessionStart"], {"AIO_URL": "http://127.0.0.1:9"})
    time.sleep(0.5)
    ok("連不上：掛鉤 1 秒內結束", dt < 1.0, dt)
    ok("連不上：記下暫停旗標", os.path.exists(os.path.join(home, ".ai-office", "pause_until")))
    n1 = len(got)
    run("SessionStart", SAMPLE["SessionStart"])
    time.sleep(0.4)
    ok("暫停期間：不再送（不會每個事件都等逾時）", len(got) == n1)
    os.remove(os.path.join(home, ".ai-office", "pause_until"))
    # 壞掉的輸入
    p = subprocess.run([sys.executable, os.path.join(HERE, "bridge.py"), "Stop"], input=b"not json", env=env, timeout=10)
    ok("壞掉的輸入：照樣 exit 0", p.returncode == 0)
    p = subprocess.run([sys.executable, os.path.join(HERE, "bridge.py"), "Stop"], input=b"{}", env={**env, "AIO_URL": ""}, timeout=10)
    ok("沒設網址：什麼都不做、exit 0", p.returncode == 0)

    # 任務簡稱：set_task_name.py 寫檔 → 之後的事件帶 task_name
    sid = SAMPLE["SessionStart"].get("session_id") or "s-test"
    subprocess.run([sys.executable, os.path.join(HERE, "set_task_name.py"), "AI 辦公室接入"], env={**env, "CLAUDE_CODE_SESSION_ID": sid}, check=True, capture_output=True)
    ok("任務簡稱：寫進 task_names", open(os.path.join(home, ".ai-office", "task_names", sid + ".txt"), encoding="utf-8").read() == "AI 辦公室接入")
    time.sleep(2.5)                            # 等前面「收件端很慢」那筆逾時寫完暫停旗標，再清掉
    try:
        os.remove(os.path.join(home, ".ai-office", "pause_until"))
    except FileNotFoundError:
        pass
    n2 = len(got)
    run("SessionStart", dict(SAMPLE["SessionStart"], session_id=sid))
    starts = []
    for _ in range(60):
        starts = [g for g in got[n2:] if g["body"].get("event") == "SessionStart"]
        if starts:
            break
        time.sleep(0.05)
    ok("任務簡稱：事件帶 task_name", starts and starts[0]["body"].get("task_name") == "AI 辦公室接入", starts[:1])
    ok("任務簡稱：怪的工作階段代號不讀檔", bridge.task_name("../../etc/passwd") is None)

    # ── install_hooks.py ──
    st = os.path.join(home, ".claude", "settings.json")
    os.makedirs(os.path.dirname(st))
    json.dump({"model": "x", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}, open(st, "w"))
    inst = [sys.executable, os.path.join(HERE, "install_hooks.py"), "--settings", st]
    subprocess.run(inst, check=True, capture_output=True)
    subprocess.run(inst, check=True, capture_output=True)
    c = json.load(open(st))
    ok("安裝：別人的設定與掛鉤原封不動", c["model"] == "x" and any("echo mine" in json.dumps(e) for e in c["hooks"]["Stop"]), c)
    ok("安裝：重跑不重複（Stop 只有自己 1 筆＋原本 1 筆）", len(c["hooks"]["Stop"]) == 2, c["hooks"]["Stop"])
    ok("安裝：指到 bridge.py 的絕對路徑", HERE.replace("\\", "/") + "/bridge.py" in json.dumps(c), "")
    subprocess.run(inst + ["--remove"], check=True, capture_output=True)
    c = json.load(open(st))
    ok("移除：只拿掉自己的", c["hooks"] == {"Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}, c)
    open(st, "w").write("{broken")
    p = subprocess.run(inst, capture_output=True)
    ok("設定檔壞掉：不覆寫、回傳 1", p.returncode == 1 and open(st).read() == "{broken")

srv.shutdown()
print("\n共 %d 項失敗" % len(fails) if fails else "\n全部通過")
sys.exit(1 if fails else 0)
