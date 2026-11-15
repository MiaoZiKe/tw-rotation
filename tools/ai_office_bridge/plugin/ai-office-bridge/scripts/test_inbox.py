#!/usr/bin/env python3
"""網站指令收件匣（Claude 端）測試：python3 test_inbox.py
起一個本機「真的收件端」（workers/ai-office-bridge/test/devserver.mjs，只聽 127.0.0.1），端到端驗：
預設關閉、Stop 掛鉤 decision block、UserPromptSubmit 附加內容、沒指令不輸出、連不上安靜結束、
待命被新指令叫醒、待命逾時自己結束、接入碼錯誤時待命結束並說明、ack 回報與回覆、安裝腳本認得新掛鉤。
不需要 Claude Code、不連外網；需要 node（22 以上，有 node:sqlite）。"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
DEV = os.path.join(REPO, "workers", "ai-office-bridge", "test", "devserver.mjs")
INBOX = os.path.join(HERE, "inbox.py")
ORIGIN = "http://127.0.0.1:8000"
OWNER = "owner-token-" + "0123456789abcdef"     # devserver 的假會員服務認得的「擁有者」網站登入權杖（假值，執行時拼接）
fails = []


def ok(name, cond, extra=""):
    print(("通過 " if cond else "失敗 ") + name + ("" if cond else "  " + str(extra)[:400]))
    if not cond:
        fails.append(name)


if not shutil.which("node") or not os.path.exists(DEV):
    print("略過：找不到 node 或 devserver.mjs")
    sys.exit(0)

s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
URL = "http://127.0.0.1:%d" % port
tmp = tempfile.mkdtemp()
code_file = os.path.join(tmp, "code.txt")
srv = subprocess.Popen(["node", DEV, "--port", str(port), "--origin", ORIGIN, "--code-file", code_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
for _ in range(100):
    try:
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(URL + "/health", timeout=1).read()
        break
    except Exception:
        time.sleep(0.1)
CODE = open(code_file).read().strip()
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def site(method, path, body=None):
    req = urllib.request.Request(URL + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Origin": ORIGIN, "X-AIO-Session": OWNER})
    try:
        with op.open(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def send(to, text):
    return site("POST", "/v1/office/main/inbox", {"to": to, "text": text})[1]["message"]["id"]


def msgs():
    return {m["id"]: m for m in site("GET", "/v1/office/main/inbox")[1]["messages"]}


home = os.path.join(tmp, "home")
os.makedirs(home)
ENV = {**os.environ, "HOME": home, "AIO_URL": URL, "AIO_TOKEN": CODE, "AIO_INBOX": "1", "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"}
for k in ("AIO_CONFIG", "AIO_STOP_MODE", "AIO_DISABLE"):
    ENV.pop(k, None)


def run(args, payload=None, env=None, timeout=20):
    t = time.time()
    p = subprocess.run([sys.executable, INBOX] + args, input=json.dumps(payload or {"session_id": "sess-1"}).encode(), env=env or ENV, capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode(), p.stderr.decode(), time.time() - t


try:
    # ── 預設關閉 ──
    m1 = send("ceo", "把首頁標題改成藍色")
    rc, out, _, _ = run(["hook", "Stop"], env={**ENV, "AIO_INBOX": ""})
    ok("沒開 AIO_INBOX：掛鉤不輸出、不取走", rc == 0 and out == "" and msgs()[m1]["status"] == "queued", (rc, out))

    # ── Stop 掛鉤 ──
    rc, out, _, dt = run(["hook", "Stop"], {"session_id": "sess-1", "stop_hook_active": False})
    j = json.loads(out or "{}")
    ok("Stop：回 decision block＋reason", rc == 0 and j.get("decision") == "block" and "把首頁標題改成藍色" in j.get("reason", ""), out)
    ok("Stop：標明來源是網站、附指令編號與回報指令、附安全規則",
       all(x in j.get("reason", "") for x in ["來源：AI Office 網站", "不是在這個對話裡直接打的字", m1, "inbox.py\" ack", "先在這個對話裡向擁有者確認"]), j.get("reason"))
    ok("Stop：取走後狀態變「已取走」、記下工作階段", msgs()[m1]["status"] == "claimed" and msgs()[m1]["session_id"] == "sess-1", msgs()[m1])
    ok("Stop：掛鉤很快結束（< 3 秒）", dt < 3, dt)
    rc, out, _, _ = run(["hook", "Stop"])
    ok("Stop：沒有新指令就不輸出（Claude 照常停下）", rc == 0 and out == "", out)

    m2 = send("frontend-ui", "手機版按鈕太小")
    rc, out, _, _ = run(["hook", "Stop"], env={**ENV, "AIO_STOP_MODE": "context"})
    j = json.loads(out or "{}")
    ok("Stop（context 模式）：改用 hookSpecificOutput.additionalContext", j.get("hookSpecificOutput", {}).get("hookEventName") == "Stop" and "手機版按鈕太小" in j["hookSpecificOutput"].get("additionalContext", "") and "decision" not in j, out)
    ok("指定 Agent：寫明要派給哪個 subagent_type", "subagent_type＝frontend-ui" in out, out)

    # ── UserPromptSubmit 掛鉤 ──
    m3 = send("ceo", "順便看一下今天的部署")
    rc, out, _, _ = run(["hook", "UserPromptSubmit"], {"session_id": "sess-1", "prompt": "別的事"})
    j = json.loads(out or "{}")
    ok("UserPromptSubmit：以 additionalContext 附上", j.get("hookSpecificOutput", {}).get("hookEventName") == "UserPromptSubmit" and "順便看一下今天的部署" in j["hookSpecificOutput"].get("additionalContext", ""), out)

    # ── 連不上、壞輸入 ──
    rc, out, _, dt = run(["hook", "Stop"], env={**ENV, "AIO_URL": "http://127.0.0.1:9"})
    ok("連不上：安靜 exit 0、不輸出、很快結束", rc == 0 and out == "" and dt < 4, (rc, out, dt))
    p = subprocess.run([sys.executable, INBOX, "hook", "Stop"], input=b"not json", env=ENV, capture_output=True, timeout=10)
    ok("壞掉的輸入：照樣 exit 0", p.returncode == 0)

    # ── ack ──
    rc, out, _, _ = run(["ack", m1, "running"])
    ok("ack running：成功、網站看到「執行中」", rc == 0 and msgs()[m1]["status"] == "running", (rc, out))
    rf = os.path.join(tmp, "reply.txt")
    open(rf, "w", encoding="utf-8").write("改好了\n預覽：https://liguligu-puipui.com/preview/blue/")
    rc, out, _, _ = run(["ack", m1, "done", "--reply-file", rf])
    mm = msgs()[m1]
    ok("ack done：網站看到「完成」與回覆（保留換行與網址）", rc == 0 and mm["status"] == "done" and mm["reply"] == "改好了\n預覽：https://liguligu-puipui.com/preview/blue/", mm)
    rc, _, err, _ = run(["ack", m1, "running"])
    ok("ack：已完成的不能再改（回傳 1 並說明）", rc == 1 and "not_active" in err, err)
    run(["ack", m2, "failed", "--reply", "找不到那個按鈕"])
    ok("ack failed：網站看到「失敗」", msgs()[m2]["status"] == "failed")

    # ── 待命模式 ──
    t0 = time.time()
    w = subprocess.Popen([sys.executable, INBOX, "wait", "--minutes", "1", "--poll", "5"], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1.5)
    ok("待命：沒指令時一直等著", w.poll() is None)
    m4 = send("reviewer", "待命時送來的")
    out, _ = w.communicate(timeout=15)
    out = out.decode()
    dt = time.time() - t0
    ok("待命：網站一送就結束並印出指令（背景指令結束＝喚醒工作階段）", w.returncode == 0 and "待命時送來的" in out and m4 in out and dt < 6, (dt, out))
    ok("待命：提醒處理完再開一次待命", "再用背景指令執行一次待命" in out, out)
    rc, out, _, dt = run(["wait", "--minutes", "0.05", "--poll", "1"])
    rc2, out2, _, dt2 = run(["wait", "--minutes", "0.06", "--poll", "0", "--interval", "1"])
    ok("待命（短輪詢模式）：時間到自己結束", rc2 == 0 and "待命結束" in out2 and dt2 < 8, (dt2, out2))
    ok("待命：時間到沒指令就自己結束並說明", rc == 0 and "待命結束" in out and 2 < dt < 8, (dt, out))
    rc, out, _, _ = run(["wait", "--minutes", "0.2"], env={**ENV, "AIO_TOKEN": "aio_" + "wrong" * 6})
    ok("待命：接入碼錯誤就結束並說明（不空轉）", rc == 0 and "收件端拒絕" in out, out)
    rc, out, _, _ = run(["wait"], env={**ENV, "AIO_INBOX": ""})
    ok("待命：沒開 AIO_INBOX 就說明並結束", rc == 0 and "沒有啟動" in out, out)

    # ── 安裝腳本 ──
    st = os.path.join(home, ".claude", "settings.json")
    os.makedirs(os.path.dirname(st))
    inst = [sys.executable, os.path.join(HERE, "install_hooks.py"), "--settings", st]
    subprocess.run(inst, check=True, capture_output=True)
    subprocess.run(inst, check=True, capture_output=True)
    c = json.load(open(st))
    cmds = [h["command"] for e in c["hooks"]["Stop"] for h in e["hooks"]]
    ok("安裝：Stop 有 bridge.py 與 inbox.py 各一支、重跑不重複", sum("inbox.py" in x for x in cmds) == 1 and sum("bridge.py" in x for x in cmds) == 1, cmds)
    ok("安裝：inbox.py 指到絕對路徑、不是背景執行", HERE.replace("\\", "/") + "/inbox.py" in json.dumps(c) and not any(h.get("async") for e in c["hooks"]["Stop"] for h in e["hooks"] if "inbox.py" in h["command"]), c["hooks"]["Stop"])
    subprocess.run(inst + ["--remove"], check=True, capture_output=True)
    ok("移除：連 inbox.py 一起拿掉", "hooks" not in json.load(open(st)))
finally:
    srv.terminate()
    shutil.rmtree(tmp, ignore_errors=True)

print("\n共 %d 項失敗" % len(fails) if fails else "\n全部通過")
sys.exit(1 if fails else 0)
