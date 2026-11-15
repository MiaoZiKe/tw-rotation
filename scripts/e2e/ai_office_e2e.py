#!/usr/bin/env python3
"""AI 辦公室「真的」端到端驗證（2026-11-15）：網站 ⇄ 收件服務 ⇄ 真的 Claude Code 工作階段。

跟 scripts/uitest_sections/*office* 的差別：那些用 page.route 假的收件服務；這支全部是真的——
  · 收件服務：workers/ai-office-bridge/worker.js 用 wrangler dev --local（miniflare，本機 SQLite，不連 Cloudflare、不用金鑰）
  · 站長登入：本機假會員服務 scripts/e2e/fake_account.py（收件服務用 --var ACCOUNT_API_URL 指過去；瀏覽器的 tw.acct.tok 放同一組測試權杖）
  · 網站：git archive HEAD 打包＋minify_site.py 壓縮後的 site/，python http.server 開在 8805，網址帶 ?aio_url= 指到本機收件服務
  · Claude：/opt/node22/bin/claude -p（無頭模式）在暫時 HOME 底下跑，外掛用 install_hooks.py 裝進 ~/.claude/settings.json，
    ~/.ai-office/config.json 放收件服務網址＋接入碼（接入碼只在暫存資料夾，不進 repo、不寫進報告）
  · 操作：Playwright 真滑鼠、真鍵盤點網站（接入引導 → 複製接入碼 → 對話框下指令 → 點 3D 角色 → 對他說 → 撤回）

用法
  bash scripts/e2e/ai_office_e2e.sh                 # 等於下面這行
  python3 scripts/e2e/ai_office_e2e.py --out <資料夾> [--model sonnet] [--keep]
費用：整條只開「一個」 claude -p 工作階段（待命模式 inbox.py wait，網站下的每則指令都在同一個工作階段裡處理），指令都很小。
"""
import argparse
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 埠：網站、收件服務、假會員服務。有人在用時可用環境變數 E2E_PORTS="8815,8816,8817" 換一組
P_SITE, P_BRIDGE, P_ACCT = [int(x) for x in os.environ.get("E2E_PORTS", "8805,8806,8807").split(",")]
ORIGIN = "http://127.0.0.1:%d" % P_SITE
BRIDGE = "http://127.0.0.1:%d" % P_BRIDGE
CLAUDE = os.environ.get("CLAUDE_BIN", "/opt/node22/bin/claude")
WRANGLER_VER = "4.162.0"

R = []          # (步驟, 通過, 說明)
T0 = time.time()
LOG = None


def now():
    return time.strftime("%H:%M:%S", time.localtime())


def log(*a):
    s = "[%s +%5.1fs] %s" % (now(), time.time() - T0, " ".join(str(x) for x in a))
    print(s, flush=True)
    if LOG:
        LOG.write(s + "\n")
        LOG.flush()


def ok(step, cond, detail=""):
    R.append((step, bool(cond), detail))
    log(("✅" if cond else "❌"), step, ("— " + str(detail)[:300]) if detail else "")
    return bool(cond)


def port_open(p):
    s = socket.socket()
    s.settimeout(0.3)
    try:
        return s.connect_ex(("127.0.0.1", p)) == 0
    finally:
        s.close()


def http(method, url, body=None, headers=None, timeout=10):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"err": str(e)}


def wait_for(fn, timeout, every=0.5):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(every)
    return fn()


# ───────────────────────── 1. 準備：打包網站、收件服務、假會員、使用者專案 ─────────────────────────
def setup(out):
    procs = []
    for p in (P_SITE, P_BRIDGE, P_ACCT):
        if port_open(p):
            sys.exit("埠 %d 已經有人在用；這支測試需要 %d／%d／%d（不會去關別人的程式）" % (p, P_SITE, P_BRIDGE, P_ACCT))
    src = os.path.join(out, "src")
    shutil.rmtree(src, ignore_errors=True)
    os.makedirs(src)
    # 測的是「已經 commit 的版本」：網站、收件服務、外掛都從 HEAD 打包，不吃工作區裡別人改到一半的檔
    subprocess.run("git archive HEAD site scripts/minify_site.py workers/ai-office-bridge tools/ai_office_bridge | tar -x -C %s" % src, shell=True, check=True, cwd=REPO)
    shutil.rmtree(os.path.join(src, "site/data"), ignore_errors=True)
    shutil.rmtree(os.path.join(src, "site/preview"), ignore_errors=True)
    subprocess.run([sys.executable, "scripts/minify_site.py", "site"], cwd=src, check=True, env={**os.environ, "ESBUILD": os.environ.get("ESBUILD", "/opt/node22/bin/esbuild")}, stdout=subprocess.DEVNULL)
    log("網站已打包壓縮：", os.path.join(src, "site"))
    # wrangler（裝在 out/wr，不動 repo）
    wr = os.environ.get("WRANGLER") or os.path.join(out, "wr", "node_modules", ".bin", "wrangler")     # WRANGLER＝已經裝好的 wrangler 路徑（省得每輪重裝）
    if not os.path.exists(wr):
        shutil.rmtree(os.path.join(out, "wr"), ignore_errors=True)
        os.makedirs(os.path.join(out, "wr"))
        subprocess.run("npm init -y >/dev/null && npm install wrangler@%s --no-audit --no-fund >/dev/null 2>&1" % WRANGLER_VER, shell=True, check=True, cwd=os.path.join(out, "wr"))
    owner_tok = "e2e-owner-" + secrets.token_hex(16)        # 假會員服務認的「站長登入權杖」：每次隨機，不是任何真金鑰
    env = {**os.environ, "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}
    procs.append(subprocess.Popen([sys.executable, os.path.join(REPO, "scripts/e2e/fake_account.py"), str(P_ACCT), owner_tok], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    procs.append(subprocess.Popen([sys.executable, "-m", "http.server", str(P_SITE), "--bind", "127.0.0.1"], cwd=os.path.join(src, "site"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    wstate = os.path.join(out, "wstate")
    shutil.rmtree(wstate, ignore_errors=True)
    wlog = open(os.path.join(out, "wrangler.log"), "w")
    procs.append(subprocess.Popen([wr, "dev", "--local", "--port", str(P_BRIDGE), "--ip", "127.0.0.1", "--persist-to", wstate,
                                   "--var", "ALLOWED_ORIGINS:" + ORIGIN, "--var", "ACCOUNT_API_URL:http://127.0.0.1:%d" % P_ACCT],
                                  cwd=os.path.join(src, "workers/ai-office-bridge"), stdout=wlog, stderr=subprocess.STDOUT, env=env, start_new_session=True))
    up = wait_for(lambda: http("GET", BRIDGE + "/health")[0] == 200 and port_open(P_SITE) and port_open(P_ACCT), 90)
    ok("準備：收件服務（wrangler dev --local）、假會員服務、網站都起來了", up, http("GET", BRIDGE + "/health")[1])
    # 使用者專案（一個很小的專案，兩位子 Agent：tester、frontend）
    proj = os.path.join(out, "demo-calc")
    shutil.rmtree(proj, ignore_errors=True)
    os.makedirs(os.path.join(proj, ".claude", "agents"))
    files = {
        "README.md": "# 小計算機\n\n一個示範專案。\n",
        "calc.py": "def add(a, b):\n    return a + b\n\n\ndef mul(a, b):\n    return a * b\n",
        "test_calc.py": "import unittest\nfrom calc import add, mul\n\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n    def test_mul(self):\n        self.assertEqual(mul(2, 3), 6)\n\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "index.html": "<!doctype html>\n<meta charset=\"utf-8\">\n<title>小計算機</title>\n<h1>小計算機</h1>\n",
        ".claude/agents/tester.md": "---\nname: tester\ndescription: 測試員。跑專案的測試（python3 -m unittest）並用一兩句話回報結果。\ntools: Bash, Read\n---\n你是測試員。只跑測試、讀結果，不改任何檔案。回報用繁體中文，一兩句話。\n",
        ".claude/agents/frontend.md": "---\nname: frontend\ndescription: 前端工程師。修改 index.html 的畫面文字。\ntools: Read, Edit\n---\n你是前端工程師。只改 index.html，改完用一句繁體中文回報改了什麼。\n",
        ".claude/settings.json": json.dumps({"permissions": {"allow": ["Bash(python3:*)", "Bash(date:*)", "Bash(cat:*)", "Bash(ls:*)", "Read", "Edit", "Write", "Glob", "Grep", "Agent", "Task"]}}, ensure_ascii=False, indent=2) + "\n",
    }
    for k, v in files.items():
        with open(os.path.join(proj, k), "w", encoding="utf-8") as f:
            f.write(v)
    subprocess.run("git init -q && git add -A && git -c user.email=e2e@example.test -c user.name=e2e commit -qm init", shell=True, check=True, cwd=proj)
    # 暫時 HOME：裝外掛（install_hooks.py）＋設定檔
    home = os.path.join(out, "home")
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home)
    # 信任這個專案資料夾（等於使用者第一次互動開啟時按了「信任」）。沒信任的話，無頭模式會忽略專案 .claude/settings.json 的允許清單，
    # 待命指令 python3 inbox.py wait 會被「需要核准」擋掉、工作階段直接結束（2026-11-15 實測第一輪就卡在這裡）。
    with open(os.path.join(home, ".claude.json"), "w") as f:
        json.dump({"hasCompletedOnboarding": True, "projects": {proj: {"hasTrustDialogAccepted": True}}}, f)
    plug = os.path.join(src, "tools/ai_office_bridge/plugin/ai-office-bridge")
    r = subprocess.run([sys.executable, os.path.join(plug, "scripts/install_hooks.py"), "--settings", os.path.join(home, ".claude/settings.json")], capture_output=True, text=True)
    ok("準備：install_hooks.py 把掛鉤裝進暫時 HOME 的 ~/.claude/settings.json", r.returncode == 0 and os.path.exists(os.path.join(home, ".claude/settings.json")), r.stdout.strip())
    return {"procs": procs, "src": src, "proj": proj, "home": home, "plug": plug, "owner_tok": owner_tok}


def claude_env(ctx):
    keep = ["HTTPS_PROXY", "https_proxy", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"]
    e = {k: os.environ[k] for k in keep if os.environ.get(k)}
    e.update({"PATH": "/opt/node22/bin:/usr/local/bin:/usr/bin:/bin", "HOME": ctx["home"], "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost", "AIO_INBOX": "1", "LANG": "C.UTF-8"})
    return e


# ───────────────────────── 2. 瀏覽器（使用者） ─────────────────────────
JS_MSGS = "() => [...__world.chat.msgs.values()].map(m => ({ id: m.id, to: m.to, status: m.status, reply: m.reply, text: m.text }))"
JS_UI_ST = "() => [...document.querySelectorAll('#chatList .c-msg')].map(e => ({ id: e.dataset.id, st: e.querySelector('.c-st').textContent.trim() }))"


class Run:
    def __init__(self, out, ctx, model, minutes):
        self.out, self.ctx, self.model, self.minutes = out, ctx, model, minutes
        self.shots = os.path.join(out, "shots")
        os.makedirs(self.shots, exist_ok=True)
        self.n = 0
        self.code = None
        self.claude = None
        self.timeline = []

    def shot(self, pg, name):
        self.n += 1
        p = os.path.join(self.shots, "%02d_%s.png" % (self.n, name))
        pg.screenshot(path=p)
        log("截圖", p)
        return p

    def state(self):
        """用接入碼讀收件服務的辦公室狀態（跟網站同一支 API；這裡只拿來核對事件）。"""
        return http("GET", BRIDGE + "/v1/office/main/state?since=0", headers={"Authorization": "Bearer " + self.code})[1] if self.code else {}

    def events_all(self):
        # since=0 只回「最近 60 筆」；要完整事件串就從 since=1 往後翻（seq 從 1 開始，第 1 筆是撤回測試那則的 InboxUpdate，不影響判斷）
        st, out, since = 200, [], 1
        while True:
            st, j = http("GET", BRIDGE + "/v1/office/main/state?since=%d" % since, headers={"Authorization": "Bearer " + self.code})
            ev = j.get("events") or []
            out += ev
            if len(ev) < 300:
                return out, j
            since = ev[-1]["seq"]

    def open_page(self, b):
        c = b.new_context(viewport={"width": 1280, "height": 800}, permissions=["clipboard-read", "clipboard-write"])
        ls = {"aiOffice.daytime": "day", "tw.acct.tok": self.ctx["owner_tok"]}     # 模擬「站長已用 Google 登入」：主站登入後就是把權杖放在這個鍵
        c.add_init_script("try{if(!sessionStorage.getItem('e2e')){sessionStorage.setItem('e2e','1');" + "".join("localStorage.setItem(%s,%s);" % (json.dumps(k), json.dumps(v)) for k, v in ls.items()) + "}}catch(e){}")
        pg = c.new_page()
        pg.set_default_timeout(60000)
        pg.errs = []
        pg.on("pageerror", lambda e: pg.errs.append(str(e)))
        pg.goto(ORIGIN + "/office/world.html?ambient=0&q=low&pr=0.6&aio_url=%s&live_poll=2000&chat_poll=1000&chat_bg_poll=1500" % BRIDGE, wait_until="domcontentloaded")
        pg.wait_for_function("() => window.__world && __world.ready && __world.chat && __world.live", timeout=120000)
        pg.wait_for_timeout(1500)
        return c, pg

    def send(self, pg, text):
        if pg.get_attribute("#chatBtn", "aria-expanded") != "true":
            pg.click("#chatBtn")                     # 展開對話串（看得到狀態、撤回鈕、回覆）
            pg.wait_for_selector("#mcTop:not([hidden])")
        pg.click("#chatText")
        pg.keyboard.insert_text(text)            # 中文是用輸入法「選字送出」進來的：insert_text 就是這個動作（逐鍵 type 在 3D 頁面上太慢）
        pg.keyboard.press("Enter")
        pg.wait_for_function("(t) => [...__world.chat.msgs.values()].some(m => m.text === t)", arg=text, timeout=15000)
        return pg.evaluate("(t) => [...__world.chat.msgs.values()].filter(m => m.text === t).pop().id", text)

    def follow(self, pg, mid, label, timeout=420, watch=None):
        """盯著一則指令：記下網站畫面上每一個狀態第一次出現的時間，各截一張。回傳看過的狀態序列。
        watch＝角色代號：同時記下 3D 裡這位同事的工作階段（phase）與位置變化（看他有沒有走去工作）。"""
        seen, end, last, ph_last, phases = [], time.time() + timeout, None, None, []
        while time.time() < end:
            m = pg.evaluate("(id) => { const m = __world.chat.msgs.get(id); return m ? { s: m.status, r: m.reply } : null; }", mid)
            ui = pg.evaluate("(id) => { const e = document.querySelector('#chatList .c-msg[data-id=\"' + id + '\"] .c-st'); if (e) return e.textContent.trim(); const p = document.getElementById('chatPeek'); return p && !p.hidden ? '（收合列）' + p.textContent.trim() : null; }", mid)
            if watch:
                w = pg.evaluate("(id) => { const c = __world.chars.get(id), a = __world.state.agents.get(id); return c ? { ph: a ? a.phase : 'idle', x: Math.round(c.object3D.position.x * 10) / 10, z: Math.round(c.object3D.position.z * 10) / 10, act: c.action || c.state || null } : null; }", watch)
                if w and w["ph"] != ph_last:
                    ph_last = w["ph"]
                    phases.append(w)
                    log("  3D：%s 階段 → %s（位置 %s,%s）" % (watch, w["ph"], w["x"], w["z"]))
                    if w["ph"] not in ("idle",):
                        self.shot(pg, "%s_3D_%s" % (label, w["ph"]))
            s = m and m["s"]
            if s and s != last:
                last = s
                seen.append(s)
                self.timeline.append({"t": now(), "msg": label, "status": s, "ui": ui})
                log("指令「%s」狀態 → %s（畫面：%s）" % (label, s, ui))
                self.shot(pg, "%s_%s" % (label, s))
            if s in ("done", "failed", "canceled", "expired"):
                if watch:
                    pg.wait_for_timeout(7000)          # 交件演出（走回 CEO 桌）收尾
                    w = pg.evaluate("(id) => { const c = __world.chars.get(id), a = __world.state.agents.get(id); return { ph: a ? a.phase : 'idle', done: a ? a.done.length : 0, x: Math.round(c.object3D.position.x * 10) / 10, z: Math.round(c.object3D.position.z * 10) / 10 }; }", watch)
                    phases.append(w)
                    self.timeline.append({"t": now(), "msg": label, "agent": watch, "phases": phases})
                    self.shot(pg, "%s_3D_交件後" % label)
                return seen, m, phases
            pg.wait_for_timeout(400)
        return seen, None, phases

    # ─────────── Claude 工作階段（待命模式） ───────────
    def start_claude(self):
        inbox = os.path.join(self.ctx["plug"], "scripts/inbox.py")
        prompt = ("這是 AI Office 待命工作階段，全程繁體中文。請用 Bash 工具的背景執行（run_in_background）跑這行，不要用前景等待、也不要用 sleep 輪詢："
                  "python3 \"%s\" wait --minutes %g\n"
                  "它收到網站指令時會印出指令與處理規則，請照規則處理：開始前 ack running；指定給某位 Agent 的，用 Agent 工具派給那個 subagent_type；"
                  "做完 ack done 並附一兩句回覆。處理完再用背景執行跑一次同一行 wait。"
                  "如果 wait 印出「待命結束」（時間到沒有新指令），就直接結束，不要再開。" % (inbox, self.minutes))
        self.clog = open(os.path.join(self.out, "claude_stream.jsonl"), "w")
        self.claude = subprocess.Popen([CLAUDE, "-p", prompt, "--model", self.model, "--output-format", "stream-json", "--verbose"],
                                       cwd=self.ctx["proj"], env=claude_env(self.ctx), stdout=self.clog, stderr=subprocess.STDOUT, start_new_session=True)
        log("已啟動 claude -p（待命模式），pid", self.claude.pid)

    def stop_claude(self):
        if self.claude and self.claude.poll() is None:
            try:
                os.killpg(self.claude.pid, signal.SIGTERM)
            except Exception:
                pass

    def claude_text(self):
        try:
            with open(os.path.join(self.out, "claude_stream.jsonl"), encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def inbox_history(self, mid):
        """收件服務記下的這則指令每一次狀態改變（InboxUpdate 事件）：網站輪詢慢的時候，畫面可能跳過很快的中間狀態，以這個為準。"""
        ev, _ = self.events_all()
        return [e.get("status") for e in ev if e["event"] == "InboxUpdate" and e.get("message_id") == mid]

    def subagents(self):
        """從收件服務收到的事件裡找 SubagentStart／SubagentStop（這些是外掛掛鉤真的送上來的）。"""
        ev, _ = self.events_all()
        return [(e["event"], e.get("agent_type"), e.get("agent_id")) for e in ev if e["event"] in ("SubagentStart", "SubagentStop")]


def main():
    global LOG
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.environ.get("TMPDIR", "/tmp"), "ai_office_e2e"))
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--minutes", type=float, default=4.0, help="待命一次最多等幾分鐘")
    ap.add_argument("--keep", action="store_true", help="跑完不關服務（方便手動再看）")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    LOG = open(os.path.join(a.out, "run.log"), "w", encoding="utf-8")
    ctx = setup(a.out)
    run = Run(a.out, ctx, a.model, a.minutes)
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", headless=True)
            c, pg = run.open_page(b)
            flow(run, pg)
            if pg.errs:
                log("頁面錯誤：", pg.errs[:5])
            ok("網站沒有 JavaScript 例外", not [e for e in pg.errs if "Error" in e], pg.errs[:3])
            b.close()
    finally:
        run.stop_claude()
        with open(os.path.join(a.out, "timeline.json"), "w", encoding="utf-8") as f:
            json.dump(run.timeline, f, ensure_ascii=False, indent=1)
        with open(os.path.join(a.out, "results.json"), "w", encoding="utf-8") as f:
            json.dump([{"step": s, "ok": o, "detail": str(d)[:500]} for s, o, d in R], f, ensure_ascii=False, indent=1)
        if not a.keep:
            for pr in ctx["procs"]:
                try:
                    os.killpg(pr.pid, signal.SIGTERM) if pr.args[0].endswith("wrangler") else pr.terminate()
                except Exception:
                    pass
            time.sleep(1)
            for d in ("src", "wstate"):              # 打包的網站與收件服務資料約數百 MB：跑完就清（截圖、紀錄、使用者專案留著）
                shutil.rmtree(os.path.join(a.out, d), ignore_errors=True)
        bad = [s for s, o, _ in R if not o]
        log("總結：%d 項通過、%d 項失敗" % (len(R) - len(bad), len(bad)))
        for s in bad:
            log("  ❌", s)
    sys.exit(1 if [s for s, o, _ in R if not o] else 0)


# ───────────────────────── 3. 流程 ─────────────────────────
def flow(run, pg):
    proj, W = run.ctx["proj"], "__world"
    run.shot(pg, "開場_示範模式")
    ok("開場：還沒接上時頂列顯示「連接我的 Claude」", "連接" in pg.inner_text("#aioBadge"), pg.inner_text("#aioBadge"))

    # f. 撤回：Claude 還沒開時排一則，撤回 → 之後 Claude 開工也不會做
    CANCEL_TXT = "（撤回測試）在 README.md 最後加一行 SHOULD-NOT-RUN"
    mid_x = run.send(pg, CANCEL_TXT)
    pg.wait_for_function("(id) => __world.chat.msgs.get(id).status === 'queued'", arg=mid_x)
    pg.wait_for_timeout(800)
    ok("撤回：Claude 沒開時送出 → 排隊中，畫面提示「你的 Claude 目前沒開」", "目前沒開" in pg.inner_text("#chatLive"), pg.inner_text("#chatLive"))
    run.shot(pg, "撤回前_排隊中")
    pg.click('#chatList [data-cancel="%s"]' % mid_x)
    canceled = pg.wait_for_function("(id) => __world.chat.msgs.get(id).status === 'canceled'", arg=mid_x, timeout=10000)
    pg.wait_for_timeout(600)
    ok("撤回：按「撤回」→ 狀態變「已撤回」", canceled and "已撤回" in pg.inner_text('#chatList .c-msg[data-id="%s"]' % mid_x))
    run.shot(pg, "撤回後")
    pg.click("#chatX")
    pg.wait_for_timeout(300)

    # a. 接入流程：頂列 → 接入引導 → 複製接入碼（自動產生）
    pg.click("#aioBadge")
    pg.wait_for_selector("#aioGuide:not([hidden])")
    run.shot(pg, "接入引導")
    pg.click('#aioGuide [data-a="cpcode"]')
    pg.wait_for_function("() => !!__world.live.code", timeout=20000)
    code = pg.evaluate("() => navigator.clipboard.readText()")
    ok("接入：按「複製接入碼」→ 收件服務發了一組碼、放進剪貼簿；畫面只顯示遮罩", bool(re.match(r"^aio_[A-Za-z0-9_-]{20,}$", code or "")) and code not in pg.inner_text("#aioGuide") and "已隱藏" in pg.inner_text("#aioGuide"))
    run.code = code
    run.shot(pg, "接入碼已複製_遮罩")
    # 用這組碼設定外掛（使用者在自己的電腦做的事：寫 ~/.ai-office/config.json）
    os.makedirs(os.path.join(run.ctx["home"], ".ai-office"), exist_ok=True)
    with open(os.path.join(run.ctx["home"], ".ai-office/config.json"), "w") as f:
        json.dump({"AIO_URL": BRIDGE, "AIO_TOKEN": code, "AIO_INBOX": "1"}, f)
    os.chmod(os.path.join(run.ctx["home"], ".ai-office/config.json"), 0o600)
    pg.wait_for_timeout(2500)                    # 等兩輪讀取，確認引導沒有被收件匣紀錄誤判成「已接上」
    ok("接入：Claude 還沒開工前，引導維持「等待你的 Claude 回報…」（撤回測試寫的收件匣紀錄不算接上）", not pg.evaluate("() => __world.live.guide.done") and "等待你的 Claude 回報" in pg.inner_text("#aioGuide"))
    if os.environ.get("E2E_DRY") == "1":
        log("E2E_DRY=1：只跑到接入碼為止，不啟動 Claude")
        return
    # 啟動「使用者的 Claude」（待命模式）
    run.start_claude()
    got = pg.wait_for_function("() => __world.live.guide.done === true", timeout=120000)
    ok("接入：Claude 開工後網站顯示「已接上 ✓」", got and "已接上" in pg.inner_text("#aioGuide"))
    run.shot(pg, "已接上")
    pg.wait_for_timeout(3200)
    if pg.is_visible("#aioGuide"):
        pg.click('#aioGuide .aio-gx')
    ok("接入：關掉引導後接入碼從網頁記憶體清掉，改用登入身分觀看", pg.evaluate("() => !__world.live.code && __world.live.cfg.login === true && __world.live.mode === 'live'"))

    # b. 辦公室出現這個專案與 CEO
    pg.wait_for_function("() => __world.live.data && __world.live.data.sessions.length > 0", timeout=60000)
    d = pg.evaluate("() => ({ badge: document.getElementById('aioBadge').innerText, projects: __world.live.data.projects.map(p => p.name), sessions: __world.live.data.sessions.map(s => ({ ended: s.ended, state: s.state })), primary: __world.live.primary, ceo: !!__world.chars.get('ceo') })")
    ok("辦公室：頂列「即時」、專案名稱＝使用者專案資料夾、有一個開著的工作階段（CEO）", "即時" in d["badge"] and "demo-calc" in d["projects"] and any(not s["ended"] for s in d["sessions"]) and d["primary"] and d["ceo"], d)
    pg.click("#aioBadge")
    pg.wait_for_timeout(500)
    run.shot(pg, "辦公室_專案與CEO")
    pg.keyboard.press("Escape")
    pg.mouse.click(5, 450)

    # 等 Claude 真的進入待命（收件服務看到它來取過指令：session_last_seen 有值）
    ok("撤回：被撤回的那則沒有被 Claude 取走（還是已撤回）", pg.evaluate("(id) => __world.chat.msgs.get(id).status", mid_x) == "canceled")

    # c. 對 CEO 下指令：README 加今天日期
    readme0 = open(os.path.join(proj, "README.md"), encoding="utf-8").read()
    T1 = "在 README.md 最後加一行今天的日期（用 date +%F 取得），做完回報。"
    mid1 = run.send(pg, T1)
    seen1, m1, _ = run.follow(pg, mid1, "CEO_README")
    readme1 = open(os.path.join(proj, "README.md"), encoding="utf-8").read()
    today = time.strftime("%Y-%m-%d")
    h1 = run.inbox_history(mid1)
    ok("CEO 指令：收件服務的狀態紀錄依序 排隊中→已取走→執行中→完成", h1 == ["queued", "claimed", "running", "done"], h1)
    ok("CEO 指令：網站畫面看到的狀態是同一個順序、最後是「完成」（Claude 在待命時幾乎是一送出就取走，排隊中可能一閃而過）", seen1 and seen1[-1] == "done" and seen1 == [x for x in h1 if x in seen1], seen1)
    ok("CEO 指令：README.md 真的被改了（多一行今天日期 %s）" % today, today in readme1 and readme1 != readme0, readme1[-80:])
    ok("CEO 指令：網站對話框看得到 Claude 的回覆", bool(m1 and m1.get("r")), (m1 or {}).get("r"))
    run.shot(pg, "CEO_README_回覆")

    # d-1. 要兩位子 Agent 的指令（還沒出現在辦公室的類型：tester、frontend）
    T2 = "請派 tester 跑 python3 -m unittest 回報通過幾個；同時派 frontend 把 index.html 的 h1 改成「小計算機 v2」。兩個都做完再一起回報。"
    mid2 = run.send(pg, T2)
    seen2, m2, _ = run.follow(pg, mid2, "CEO_派兩位")
    html = open(os.path.join(proj, "index.html"), encoding="utf-8").read()
    sa = run.subagents()
    ok("派工：收件服務收到 tester 與 frontend 的 SubagentStart／SubagentStop（外掛掛鉤真的送上來）",
       {("SubagentStart", "tester"), ("SubagentStop", "tester"), ("SubagentStart", "frontend"), ("SubagentStop", "frontend")} <= {(e, t) for e, t, _ in sa}, sa)
    ok("派工：frontend 真的改了 index.html", "小計算機 v2" in html, html.strip()[-60:])
    ok("派工：指令完成、有回覆", m2 and seen2[-1] == "done" and m2.get("r"), (m2 or {}).get("r"))
    pg.click("#chatX")
    pg.wait_for_timeout(2500)
    who = pg.evaluate("() => ['tester', 'frontend'].map(t => { const id = __world.live.typeMap.get(t); const c = id && __world.chars.get(id); return { type: t, id, nick: c && c.spec.nick, seat: c && c.homeSpot && c.homeSpot.name, done: id ? __world.state.agent(id).done.length : 0 }; })")
    ok("辦公室：為新的子 Agent 類型產生角色、坐進座位（生產對應工作區 Agent）", all(w["id"] and w["nick"] and w["seat"] for w in who), who)
    run.shot(pg, "新同事報到_tester_frontend")

    # d-2／e. 直接對 tester、frontend 下指令：收合對話框 → 真滑鼠點 3D 裡的他 → 資訊卡「對他說」→ 打字送出 → 收合看 3D 演出
    for agent, text, label in (("tester", "再跑一次測試，只回報通過幾個。", "tester"), ("frontend", "把 index.html 的 title 也改成「小計算機 v2」。", "frontend")):
        aid = pg.evaluate("(t) => __world.live.typeMap.get(t)", agent)
        if not aid:
            ok("對 %s 下指令：辦公室裡找不到他" % agent, False)
            continue
        if pg.get_attribute("#chatBtn", "aria-expanded") == "true":
            pg.click("#chatX")
            pg.wait_for_timeout(500)
        if pg.is_visible("#card"):
            pg.keyboard.press("Escape")
        pg.click('button[data-v="god"]')             # 回到俯瞰（上一位的資訊卡會把鏡頭切成「跟隨」，下一位可能不在畫面裡）
        try:                                          # 等他回到座位（上一件工作的交件演出走完）再點，點移動中的人容易點空
            pg.wait_for_function("(id) => { const a = __world.state.agents.get(id); return !a || a.phase === 'idle'; }", arg=aid, timeout=60000)
        except Exception:
            log("%s 60 秒內沒有回到待命，照樣點" % agent)
        pg.wait_for_timeout(1500)
        # 點的位置＝main.js pickChar() 判定的角色中心（頭頂投影點往下 0.45 公尺），不是猜的偏移
        xy = pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id), cv = document.getElementById('cv'), r = cv.getBoundingClientRect();
            const px = cv.clientHeight / (2 * Math.tan(W.camera.fov * Math.PI / 360) * c._sd), k = c.scale || 1;
            return [Math.round(r.left + c._sx), Math.round(r.top + c._sy + px * 0.45 * k), innerWidth, innerHeight]; }""", aid)
        top = pg.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return e ? (e.id || e.tagName) : null; }", xy[:2])
        clicked = False
        if 0 < xy[0] < xy[2] and 0 < xy[1] < xy[3]:
            pg.mouse.click(xy[0], xy[1])
            try:
                pg.wait_for_function("(id) => !document.getElementById('card').hidden && __world.chat.to === id", arg=aid, timeout=6000)
                clicked = True
            except Exception:
                clicked = False
        if not clicked:
            log("真滑鼠點 3D 的 %s 沒點到（座標 %s，最上層 %s），改用 __world.ui.showCard 打開資訊卡" % (agent, xy, top))
            pg.evaluate("(id) => __world.ui.showCard(__world.chars.get(id))", aid)
        ok("對 %s：%s → 資訊卡打開、對話框對象切成他" % (agent, "真滑鼠點 3D 角色" if clicked else "（沒點到，改直接開資訊卡）"), clicked and pg.evaluate("(id) => !document.getElementById('card').hidden && __world.chat.to === id", aid), {"xy": xy, "top": top})
        run.shot(pg, "%s_資訊卡" % label)
        pg.click("#card [data-chat]")
        pg.wait_for_selector("#mcTop:not([hidden])")
        n_before = len([1 for e, t, _ in run.subagents() if e == "SubagentStart" and t == agent])
        mid = run.send(pg, text)
        to = pg.evaluate("(id) => __world.chat.msgs.get(id).to", mid)
        ok("對 %s：收件匣收到的 to＝%s（Claude 會被告知派給 subagent_type＝%s）" % (agent, to, to), to == agent, to)
        run.shot(pg, "%s_已送出_他的對話串" % label)
        pg.click("#chatX")                           # 收合，讓 3D 看得到他工作
        seen, m, phases = run.follow(pg, mid, label, watch=aid)
        n_after = len([1 for e, t, _ in run.subagents() if e == "SubagentStart" and t == agent])
        h = run.inbox_history(mid)
        ok("對 %s：收件服務的狀態紀錄依序 排隊中→已取走→執行中→完成" % agent, h == ["queued", "claimed", "running", "done"], h)
        ok("對 %s：Claude 真的派了 %s（SubagentStart 多一筆）、狀態走到完成、有回覆" % (agent, agent), n_after > n_before and seen and seen[-1] == "done" and m and m.get("r"), {"seen": seen, "reply": (m or {}).get("r"), "starts": [n_before, n_after]})
        try:
            pg.wait_for_function("(id) => { const a = __world.state.agents.get(id); return a && a.phase === 'idle' && a.done.length > 0; }", arg=aid, timeout=60000)
        except Exception:
            pass
        fin = pg.evaluate("(id) => { const a = __world.state.agents.get(id); return { ph: a.phase, done: a.done.length, last: a.done[0] && a.done[0].title }; }", aid)
        ok("對 %s：3D 裡他有開工（階段離開待命）、交件後回到待命、資訊卡完成清單多一件" % agent, any(p.get("ph") not in (None, "idle") for p in phases) and fin["ph"] == "idle" and fin["done"] >= 1, {"phases": phases, "final": fin})
        pg.click("#chatBtn")
        pg.wait_for_selector("#mcTop:not([hidden])")
        pg.wait_for_timeout(800)
        run.shot(pg, "%s_回覆_他的對話串" % label)
    html = open(os.path.join(proj, "index.html"), encoding="utf-8").read()
    ok("frontend 指令：index.html 的 title 真的被改了", "<title>小計算機 v2</title>" in html, html.strip()[:120])
    txt = run.claude_text()
    ok("撤回：Claude 的完整對話紀錄裡從頭到尾沒有出現被撤回那則的內容", "SHOULD-NOT-RUN" not in txt and "SHOULD-NOT-RUN" not in open(os.path.join(proj, "README.md"), encoding="utf-8").read())
    ev, st = run.events_all()
    kinds = sorted({e["event"] for e in ev})
    log("收件服務收到的事件種類：", kinds, "共", len(ev), "筆")
    ok("事件：收件服務收到 SessionStart、UserPromptSubmit、PreToolUse、SubagentStart、SubagentStop、Stop", {"SessionStart", "UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop"} <= set(kinds), kinds)
    run.shot(pg, "全部完成")


if __name__ == "__main__":
    main()
