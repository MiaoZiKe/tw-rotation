# 驗收段落「辦公室對話框開放一般會員」（2026-11-16）
# 擁有者要求：任何建立了自己辦公室的一般使用者，登入後都能在對話框跟自己辦公室的 CEO／Agent 對話；費用由他自己的 Claude 負擔（網站不呼叫 Claude）。
# 驗：① 一般會員還沒建辦公室 → 對話框引導「先建立你自己的辦公室」；建好後按「再試一次」→ 可以送出；
#     ② 指令只進他自己的收件匣：站長的接入碼取不到、他自己的接入碼取得到；回覆回到他的對話框；
#     ③ 沒登入 → 對話框顯示登入引導（有「去登入」連結、送出鈕寫「請先登入」）；④ 畫面沒有禁用字。
# 用「真的收件端」devserver（假會員服務：member-token-… 是一般會員）。RS_SHOTS 指到資料夾時存截圖。
# flake8: noqa

import json as _json
import os as _os
import shutil as _sh
import socket as _sock
import subprocess as _sp
import tempfile as _tf
import time as _tm
import urllib.request as _ur
from urllib.parse import urlparse as _rup

_CM_TOK = "member-token-" + "0123456789abcdef"          # devserver 假會員服務的「一般會員」權杖（假值）
_CM_BAN = ("價格", "付費", "升級", "訂閱", "方案", "Plus", "Pro", "免費", "右鍵")
try:
    _CM_HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _CM_HERE = _os.path.join(_os.getcwd(), "scripts", "uitest_sections")
_CM_DEV = next((p for p in (_os.environ.get("AIO_DEVSERVER", ""), _os.path.abspath(_os.path.join(_CM_HERE, "..", "..", "workers", "ai-office-bridge", "test", "devserver.mjs")), "/home/user/tw-rotation/workers/ai-office-bridge/test/devserver.mjs") if p and _os.path.exists(p)), "")
_CM_NOPROXY = _ur.build_opener(_ur.ProxyHandler({}))


def _cm_shot(pg, name):
    d = _os.environ.get("RS_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _CmSrv:
    def __init__(self, origin):
        s = _sock.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.origin = origin
        self.url = "http://127.0.0.1:%d" % self.port
        self.tmp = _tf.mkdtemp()
        cf = _os.path.join(self.tmp, "code.txt")
        self.p = _sp.Popen(["node", _CM_DEV, "--port", str(self.port), "--origin", origin, "--code-file", cf], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        for _ in range(100):
            try:
                _CM_NOPROXY.open(self.url + "/health", timeout=1).read()
                break
            except Exception:
                _tm.sleep(0.1)
        self.code = open(cf).read().strip()           # 站長的接入碼

    def req(self, path, body, hdr):
        r = _ur.Request(self.url + path, method="POST", data=_json.dumps(body).encode(), headers={"Content-Type": "application/json", **hdr})
        try:
            return _json.loads(_CM_NOPROXY.open(r, timeout=5).read().decode())
        except Exception as e:
            return {"err": str(e)}

    def stop(self):
        self.p.terminate()
        _sh.rmtree(self.tmp, ignore_errors=True)


def _cm_ctx(b, srv, tok):
    c = b.new_context(viewport={"width": 1280, "height": 800})
    cfg = _json.dumps({"url": srv.url, "login": True})
    if tok:
        user = _json.dumps({"email": "m@example.com", "name": "一般會員", "admin": False})
        c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('tw.acct.tok','" + tok + "');localStorage.setItem('tw.acct.user'," + _json.dumps(user) + ");localStorage.setItem('aiOffice.live.v1'," + _json.dumps(cfg) + ")}catch(e){}")
    else:
        c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('aiOffice.live.v1'," + _json.dumps(cfg) + ")}catch(e){}")
    c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://tw-account.test' };", headers={"Content-Type": "application/javascript"}))
    return c


def _cm_open(c, base):
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.goto(base.split("/index.html")[0].rstrip("/") + "/office/world.html?office=main&live_poll=800&ambient=0&q=low&pr=0.6&chat_poll=500&chat_bg_poll=700", wait_until="domcontentloaded")
    return pg, wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat", 120000)


def _cm_main(b, base):
    if not _sh.which("node") or not _os.path.exists(_CM_DEV):
        ok("會員對話框：略過（這台沒有 node 或找不到 devserver.mjs）", True)
        return
    o = _rup(base)
    srv = _CmSrv("%s://%s" % (o.scheme, o.netloc))
    try:
        # ───── ① 一般會員、還沒建辦公室 ─────
        c = _cm_ctx(b, srv, _CM_TOK)
        pg, got = _cm_open(c, base)
        ok("會員：辦公室載入完成", got)
        if not got:
            return
        pg.click("#chatText")
        got = wait_until(pg, "() => window.__world.chat.mode === 'nooffice'", 30000)
        note = pg.inner_text("#chatNote") if pg.is_visible("#chatNote") else ""
        ok("會員沒建辦公室：對話框引導「先建立你自己的辦公室」", got and "先建立你自己的辦公室" in note, (pg.evaluate("() => window.__world.chat.mode"), note))
        _cm_shot(pg, "cm1_先建辦公室.png")
        # 建辦公室（網站的辦公室清單 API，同一個帳號）→ 按「建好了，再試一次」
        r = srv.req("/v1/offices", {"name": "我的辦公室"}, {"Origin": srv.origin, "X-AIO-Session": _CM_TOK})
        ok("會員建立辦公室成功", r.get("ok"), r)
        pg.click("#chatRetry")
        got = wait_until(pg, "() => window.__world.chat.mode === 'ok'", 30000)
        ok("建好之後按「再試一次」→ 對話框可以用（mode=ok）", got, pg.evaluate("() => window.__world.chat.mode"))
        pg.evaluate("() => window.__world.chat.openTo && window.__world.chat.openTo('ceo')")
        pg.click("#chatText")
        pg.keyboard.type("幫我整理今天的待辦", delay=10)
        pg.keyboard.press("Enter")
        got = wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length >= 1", 20000)
        ok("會員送出：訊息出現在對話框", got and "幫我整理今天的待辦" in pg.inner_text("#chatList"), pg.inner_text("#chatList")[:200])
        # ───── ② 只進自己的收件匣 ─────
        po = srv.req("/v1/inbox/pull", {"session_id": "s-owner", "wait": 0}, {"Authorization": "Bearer " + srv.code})
        ok("站長的 Claude 取不到會員的指令", po.get("ok") and not po.get("messages"), po)
        cl = srv.req("/v1/claim", {"t": _CM_TOK}, {"Origin": srv.origin})
        ok("會員可以產生自己的接入碼（綁自己的辦公室，不是 main）", cl.get("code") and cl.get("office") != "main", {k: v for k, v in cl.items() if k != "code"})
        pm = srv.req("/v1/inbox/pull", {"session_id": "s-mem", "wait": 0}, {"Authorization": "Bearer " + (cl.get("code") or "x")})
        msgs = pm.get("messages") or []
        ok("會員自己的 Claude 取得到這則指令", len(msgs) == 1 and msgs[0].get("text") == "幫我整理今天的待辦", pm)
        if msgs:
            srv.req("/v1/inbox/ack", {"id": msgs[0]["id"], "status": "done", "reply": "今天有三件待辦，已整理好。", "session_id": "s-mem"}, {"Authorization": "Bearer " + cl["code"]})
            got = wait_until(pg, "() => document.querySelector('#chatList').innerText.includes('今天有三件待辦')", 20000)
            ok("回覆回到會員自己的對話框", got, pg.inner_text("#chatList")[:300])
        _cm_shot(pg, "cm2_會員對話.png")
        txt = pg.inner_text("#chatPanel") if pg.query_selector("#chatPanel") else pg.inner_text("body")
        bad = [w for w in _CM_BAN if w in txt]
        ok("會員對話框：沒有禁用字", not bad, bad)
        ok("會員：沒有頁面錯誤", not pg.errs, pg.errs[:3])
        c.close()

        # ───── ③ 沒登入 ─────
        c = _cm_ctx(b, srv, None)
        pg, got = _cm_open(c, base)
        ok("訪客：辦公室載入完成", got)
        if got:
            pg.click("#chatText")
            got = wait_until(pg, "() => window.__world.chat.mode === 'nologin'", 20000)
            note = pg.inner_text("#chatNote") if pg.is_visible("#chatNote") else ""
            ok("沒登入：對話框顯示登入引導（有「去登入」）", got and "登入後就能跟你的 CEO 說話" in note and pg.query_selector("#chatLogin") is not None, note)
            ok("沒登入：送出鈕寫「請先登入」", pg.inner_text("#chatSend").strip() == "請先登入", pg.inner_text("#chatSend"))
            ok("沒登入：引導文字沒有禁用字也不提站長帳號", not [w for w in _CM_BAN if w in note] and "站長帳號" not in note, note)
            _cm_shot(pg, "cm3_訪客登入引導.png")
        c.close()
    finally:
        srv.stop()


register("辦公室對話框開放一般會員", lambda pg, b, base, code: _cm_main(b, base))
