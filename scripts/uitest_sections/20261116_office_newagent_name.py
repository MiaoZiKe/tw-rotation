# 驗收段落「辦公室新專案 Agent 名牌」（2026-11-16）
# 擁有者問題：收件服務收到新專案的 Agent（member-api、points-engine、qa-tester）時，名牌只顯示被截短的英文類型名「member⋯」，
#   但收件服務其實已帶來派工說明（例如「會員註冊登入 API」）。改成：名牌主名＝派工說明前 8 字中文（沒有說明才用類型名縮短），第二行保留類型名；
#   既有已有中文暱稱的角色（例如 inspector）不變；先用類型名報到、之後才拿到說明的，補改一次。
#   另外：對話框裡指令完成後，回覆泡泡旁小字「已完成」，進行中小字「處理中」（不出現「已取走」「排隊中」「由 CEO 轉交」）。
# 用「真的收件端」devserver，事件／指令都真的送進去；RS_SHOTS 指到資料夾時存截圖。
# flake8: noqa

import json as _json
import os as _os
import re as _re
import shutil as _sh
import socket as _sock
import subprocess as _sp
import tempfile as _tf
import time as _tm
import urllib.request as _ur
from urllib.parse import urlparse as _rup

_NN_TOK = "owner-token-" + "0123456789abcdef"           # devserver 的假會員服務認得的「擁有者」登入權杖（假值）
_NN_OLD, _NN_NEW, _NN_OTHER = "a1" * 8, "b1" * 8, "d1" * 8
_NN_CL1, _NN_CL2 = "c1" * 8, "c2" * 8
try:
    _NN_HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:                                   # 小跑者用 exec 載入、沒有 __file__
    _NN_HERE = _os.path.join(_os.getcwd(), "scripts", "uitest_sections")
_NN_DEV = next((p for p in (_os.environ.get("AIO_DEVSERVER", ""), _os.path.abspath(_os.path.join(_NN_HERE, "..", "..", "workers", "ai-office-bridge", "test", "devserver.mjs")), "/home/user/tw-rotation/workers/ai-office-bridge/test/devserver.mjs") if p and _os.path.exists(p)), "")
_NN_NOPROXY = _ur.build_opener(_ur.ProxyHandler({}))


def _nn_shot(pg, name):
    d = _os.environ.get("RS_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _NnSrv:
    """起一個本機真收件端；origin＝測試網站的來源（收件端的 CORS 白名單）"""

    def __init__(self, origin):
        s = _sock.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.url = "http://127.0.0.1:%d" % self.port
        self.tmp = _tf.mkdtemp()
        cf = _os.path.join(self.tmp, "code.txt")
        self.p = _sp.Popen(["node", _NN_DEV, "--port", str(self.port), "--origin", origin, "--code-file", cf], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        for _ in range(100):
            try:
                _NN_NOPROXY.open(self.url + "/health", timeout=1).read()
                break
            except Exception:
                _tm.sleep(0.1)
        self.code = open(cf).read().strip()

    def post(self, path, body, bearer=True):
        req = _ur.Request(self.url + path, method="POST", data=_json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.code})
        return _json.loads(_NN_NOPROXY.open(req, timeout=5).read().decode())

    def events(self, evs):
        for i in range(0, len(evs), 20):
            self.post("/v1/events", {"events": evs[i:i + 20]})

    def stop(self):
        self.p.terminate()
        _sh.rmtree(self.tmp, ignore_errors=True)


def _nn_ev(event, sid, ph, name, **k):
    d = {"event": event, "session_id": sid, "project_hash": ph, "project_name": name, "ts": int(_tm.time() * 1000), "cloud": True}
    d.update(k)
    return d


def _nn_seed(srv):
    ev = _nn_ev
    srv.events([
        ev("SessionStart", "s-o1", _NN_OLD, "tw-rotation"), ev("SessionStart", "s-o2", _NN_OLD, "tw-rotation"),            # 舊的路徑雜湊（2 個進行中）
        ev("SessionStart", "s-n1", _NN_NEW, "tw-rotation", agent_files=["inspector", "my-bot", "code-reviewer"]),           # 新的儲存庫雜湊（1 個進行中）
        ev("SubagentStart", "s-n1", _NN_NEW, "tw-rotation", agent_id="ag-1", agent_type="Explore"),
        ev("SessionStart", "s-x1", _NN_OTHER, "other-repo", agent_files=["deployer", "zz-agent-b"]),
        ev("SessionStart", "c1", _NN_CL1, "user"), ev("SessionStart", "c2", _NN_CL1, "user"), ev("SessionStart", "c3", _NN_CL2, "root"),
        ev("SubagentStart", "c1", _NN_CL1, "user", agent_id="cag-1", agent_type="general-purpose"),
    ])


def _nn_ctx(b, srv, w=1280, h=800, creds=True):
    c = b.new_context(viewport={"width": w, "height": h})
    if creds:
        cfg = _json.dumps({"url": srv.url, "login": True})
        user = _json.dumps({"email": "a@example.com", "name": "站長", "admin": True})
        c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('tw.acct.tok','" + _NN_TOK + "');localStorage.setItem('tw.acct.user'," + _json.dumps(user) + ");localStorage.setItem('aiOffice.live.v1'," + _json.dumps(cfg) + ")}catch(e){}")
        c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://tw-account.test' };", headers={"Content-Type": "application/javascript"}))
    else:
        c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    return c


def _nn_page(c):
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    return pg


def _nn_ready(pg):
    return wait_until(pg, "() => window.__world && window.__world.ready && window.__world.live && window.__world.live.data", 120000)


_NN_VIS = "() => [...window.__world.chars.values()].filter(c => !c.away && c.object3D.visible && !c.spec.isCeo && !c.spec.pet).map(c => c.spec.id).sort()"


_NN_PH = "e1" * 8


def _nn_world(base, ph):
    return base.split("/index.html")[0].rstrip("/") + "/office/world.html?office=main&project=" + ph + "&live_poll=800&ambient=0&q=low&pr=0.6&chat_poll=500&chat_bg_poll=700"


def _nn_site_post(srv, path, body):
    req = _ur.Request(srv.url + path, method="POST", data=_json.dumps(body).encode(), headers={"Content-Type": "application/json", "X-AIO-Session": _NN_TOK})
    return _json.loads(_NN_NOPROXY.open(req, timeout=5).read().decode())


def _nn_info(pg, ids):
    return pg.evaluate("""(ids) => { const W = window.__world, o = {}; for (const id of ids) { const c = W.chars.get(id); if (!c) { o[id] = null; continue; }
        const k = c._lab.tag.children; o[id] = { nick: c.spec.nick, zh: c.spec.zh, member: (W.members.get(id) || {}).nick, tag1: k[0].textContent, tag2: k[1].textContent, sit: c.state === 'sit' }; } return o; }""", ids)


def _nn_main(b, base):
    if not _sh.which("node") or not _os.path.exists(_NN_DEV):
        ok("新專案名牌：略過（這台沒有 node 或找不到 devserver.mjs）", True)
        return
    o = _rup(base)
    srv = _NnSrv("%s://%s" % (o.scheme, o.netloc))
    c = _nn_ctx(b, srv)
    try:
        ev = _nn_ev
        srv.events([
            ev("SessionStart", "s-e1", _NN_PH, "member-project", agent_files=["member-api", "points-engine", "qa-tester", "inspector"]),
            ev("SubagentStart", "s-e1", _NN_PH, "member-project", agent_id="ag-m", agent_type="member-api", description="會員註冊登入 API 開發"),
            ev("SubagentStart", "s-e1", _NN_PH, "member-project", agent_id="ag-p", agent_type="points-engine", description="點數計算引擎，含過期規則"),
            ev("SubagentStart", "s-e1", _NN_PH, "member-project", agent_id="ag-i", agent_type="inspector", description="審這批改動有沒有漏"),
        ])
        pg = _nn_page(c)
        pg.goto(_nn_world(base, _NN_PH), wait_until="domcontentloaded")
        got = _nn_ready(pg)
        ok("新專案：辦公室載入完成", got)
        if not got:
            return
        ids = ["member-api", "points-engine", "qa-tester", "inspector"]
        wait_until(pg, "() => ['member-api', 'points-engine', 'qa-tester', 'inspector'].every(k => window.__world.chars.has(k))", 60000)
        wait_until(pg, "() => ['member-api','points-engine','qa-tester'].every(k => window.__world.chars.get(k).state === 'sit')", 90000)
        d = _nn_info(pg, ids)
        ok("名牌主名：member-api 用派工說明「會員註冊登入」（中文、不是「member⋯」）", d["member-api"]["nick"] == "會員註冊登入" and d["member-api"]["tag1"] == "會員註冊登入" and d["member-api"]["member"] == "會員註冊登入", d["member-api"])
        ok("名牌主名：points-engine 用說明第一段前 8 字「點數計算引擎」（逗號後的不收）", d["points-engine"]["nick"] == "點數計算引擎" and d["points-engine"]["tag1"] == "點數計算引擎", d["points-engine"])
        ok("第二行保留類型名：頭頂名牌第二行含 member-api／points-engine", "member-api" in d["member-api"]["tag2"] and "points-engine" in d["points-engine"]["tag2"] and d["member-api"]["zh"] == "member-api", (d["member-api"]["tag2"], d["points-engine"]["tag2"]))
        ok("沒有派工說明的 qa-tester：主名用類型名縮短（沒有任何中文）、第二行仍是類型名", d["qa-tester"]["nick"].startswith("qa") and not _re.search(r"[\u4e00-\u9fff]", d["qa-tester"]["nick"]) and "qa-tester" in d["qa-tester"]["tag2"], d["qa-tester"])
        ok("既有已有中文暱稱的角色不變：inspector 不被他的派工說明蓋掉", d["inspector"]["nick"] == d["inspector"]["member"] and "審這批" not in d["inspector"]["nick"] and _re.search(r"[\u4e00-\u9fff]", d["inspector"]["nick"]), d["inspector"])
        plate = pg.evaluate("() => { const W = window.__world, c = W.chars.get('member-api'); const i = W.furn.get(c.homeSpot.fid); const p = i && i.spec.extras && i.spec.extras[0]; return { vis: !!(p && p.visible), tex: !!(p && p.userData && p.userData.tex) }; }")
        ok("桌上名牌：member-api 的桌子名牌亮著（已換成他）", plate["vis"] and plate["tex"], plate)
        _nn_shot(pg, "na1_新名牌.png")

        # 之後才拿到說明：補改一次
        srv.events([ev("SubagentStart", "s-e1", _NN_PH, "member-project", agent_id="ag-q", agent_type="qa-tester", description="測試會員流程與點數")])
        got = wait_until(pg, "() => window.__world.chars.get('qa-tester').spec.nick === '測試會員流程與點'", 30000)
        d2 = _nn_info(pg, ["qa-tester", "member-api"])
        ok("先用類型名報到、後來才拿到說明：補改成任務簡稱（頭頂名牌、成員表同步），第二行仍是類型名", got and d2["qa-tester"]["tag1"] == "測試會員流程與點" and d2["qa-tester"]["member"] == "測試會員流程與點" and "qa-tester" in d2["qa-tester"]["tag2"], d2["qa-tester"])
        ok("已經有簡稱的不會跳來跳去（新說明來了 member-api 名牌不變）", d2["member-api"]["nick"] == "會員註冊登入")
        srv.events([ev("SubagentStart", "s-e1", _NN_PH, "member-project", agent_id="ag-m2", agent_type="member-api", description="改寫密碼重設信")])
        pg.wait_for_timeout(2500)
        ok("同一類型換新任務：名牌仍是原本簡稱", _nn_info(pg, ["member-api"])["member-api"]["nick"] == "會員註冊登入")
        _nn_shot(pg, "na2_補改簡稱.png")

        # ───── 對話框：處理中／已完成 ─────
        pg.evaluate("() => window.__world.chat.openTo('member-api')")
        wait_until(pg, "() => window.__world.chat.mode === 'ok' || window.__world.chat.mode === 'noinbox'", 30000)
        pg.click("#chatText")
        pg.keyboard.type("請把註冊流程補上手機驗證", delay=10)
        pg.keyboard.press("Enter")
        wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length >= 1", 20000)
        pulled = srv.post("/v1/inbox/pull", {"session_id": "sess-na", "wait": 0, "project_hash": _NN_PH})
        msgs = pulled.get("messages") or pulled.get("items") or []
        mid = (msgs[0] if msgs else {}).get("id")
        ok("指令真的送進收件匣、Claude 端取得到", bool(mid), pulled)
        if mid:
            srv.post("/v1/inbox/ack", {"id": mid, "status": "running", "session_id": "sess-na"})
            got = wait_until(pg, "() => !!document.querySelector('#chatList .c-rp .c-rs[data-rs=doing]')", 20000)
            txt = pg.inner_text("#chatList")
            ok("進行中：回覆泡泡旁小字「處理中」", got and pg.inner_text("#chatList .c-rs[data-rs=doing]").strip() == "處理中", txt)
            ok("進行中：沒有「已取走」「排隊中」「由 CEO 轉交」這些字", not any(w in txt for w in ("已取走", "排隊中", "由 CEO 轉交")), txt)
            _nn_shot(pg, "na3_處理中.png")
            srv.post("/v1/inbox/ack", {"id": mid, "status": "done", "reply": "已補上手機驗證步驟。", "session_id": "sess-na"})
            got = wait_until(pg, "() => !!document.querySelector('#chatList .c-rp .c-rs[data-rs=done]')", 20000)
            txt = pg.inner_text("#chatList")
            ok("完成：回覆泡泡旁小字「已完成」、處理中消失", got and pg.inner_text("#chatList .c-rs[data-rs=done]").strip() == "已完成" and not pg.query_selector("#chatList .c-rs[data-rs=doing]"), txt)
            ok("完成：小字在回覆泡泡旁（同一列、不蓋住回覆文字）", pg.evaluate("() => { const r = document.querySelector('#chatList .c-rp'), b = r.querySelector('.c-rb').getBoundingClientRect(), s = r.querySelector('.c-rs').getBoundingClientRect(); return s.left >= b.right - 1 && Math.abs((s.bottom) - b.bottom) < 24; }"))
            ok("完成：沒有「已取走」「排隊中」「由 CEO 轉交」", not any(w in txt for w in ("已取走", "排隊中", "由 CEO 轉交")), txt)
            _nn_shot(pg, "na4_已完成.png")
        ok("沒有頁面錯誤", not pg.errs, pg.errs[:2])
    finally:
        c.close()
        srv.stop()


register("辦公室新專案名牌", lambda pg, b, base, code: _nn_main(b, base))
