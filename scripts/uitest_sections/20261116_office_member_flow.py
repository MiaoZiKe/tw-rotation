# 驗收段落「一般會員的辦公室整條流程」（2026-11-16）
# 流程：一般會員登入 → 建自己的辦公室 → 辦公室頁打開「連接我的 Claude」→ 產生自己的接入碼（不是站長的 main）→ 拿到提示詞
#       → 會員自己的 Claude 用這組碼送事件 → 畫面上自己的員工開始工作 → 對話框送出成功、指令只進自己的收件匣。
# 另驗：會員看不到站長辦公室的事件（隔離）；站長畫面照舊連 main、引導沒有被擋、事件照常顯示。
# 用「真的收件端」devserver（假會員服務：member-token-… 是一般會員、owner-token-… 是站長）。RS_SHOTS 指到資料夾時存截圖。
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

_MF_MEM = "member-token-" + "0123456789abcdef"
_MF_OWN = "owner-token-" + "0123456789abcdef"
_MF_BAN = ("價格", "NT$", "付費", "升級", "訂閱", "方案", "Plus", "Pro", "免費", "右鍵")
try:
    _MF_HERE = _os.path.dirname(_os.path.abspath(__file__))
except NameError:
    _MF_HERE = _os.path.join(_os.getcwd(), "scripts", "uitest_sections")
_MF_DEV = next((p for p in (_os.environ.get("AIO_DEVSERVER", ""), _os.path.abspath(_os.path.join(_MF_HERE, "..", "..", "workers", "ai-office-bridge", "test", "devserver.mjs")), "/home/user/tw-rotation/workers/ai-office-bridge/test/devserver.mjs") if p and _os.path.exists(p)), "")
_MF_NP = _ur.build_opener(_ur.ProxyHandler({}))


def _mf_shot(pg, name):
    d = _os.environ.get("RS_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _MfSrv:
    def __init__(self, origin):
        s = _sock.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.origin = origin
        self.url = "http://127.0.0.1:%d" % self.port
        self.tmp = _tf.mkdtemp()
        cf = _os.path.join(self.tmp, "code.txt")
        self.p = _sp.Popen(["node", _MF_DEV, "--port", str(self.port), "--origin", origin, "--code-file", cf], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        for _ in range(100):
            try:
                _MF_NP.open(self.url + "/health", timeout=1).read()
                break
            except Exception:
                _tm.sleep(0.1)
        self.code = open(cf).read().strip()           # 站長（main）的接入碼

    def req(self, path, body, hdr):
        r = _ur.Request(self.url + path, method="POST", data=_json.dumps(body).encode(), headers={"Content-Type": "application/json", **hdr})
        try:
            return _json.loads(_MF_NP.open(r, timeout=5).read().decode())
        except Exception as e:
            return {"err": str(e)}

    def events(self, code, evs):
        return self.req("/v1/events", {"events": evs}, {"Authorization": "Bearer " + code})

    def stop(self):
        self.p.terminate()
        _sh.rmtree(self.tmp, ignore_errors=True)


def _mf_ev(event, sid, name, **k):
    d = {"event": event, "session_id": sid, "project_hash": "ab12cd34ef567890", "project_name": name, "ts": int(_tm.time() * 1000), "cloud": True}
    d.update(k)
    return d


def _mf_ctx(b, srv, tok, admin):
    c = b.new_context(viewport={"width": 1280, "height": 800})
    cfg = _json.dumps({"url": srv.url, "login": True})
    user = _json.dumps({"email": "x@example.com", "name": "站長" if admin else "一般會員", "admin": admin})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('tw.acct.tok','" + tok + "');localStorage.setItem('tw.acct.user'," + _json.dumps(user) + ");localStorage.setItem('aiOffice.live.v1'," + _json.dumps(cfg) + ")}catch(e){}")
    c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://tw-account.test' };", headers={"Content-Type": "application/javascript"}))
    return c


def _mf_open(c, base):
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.goto(base.split("/index.html")[0].rstrip("/") + "/office/world.html?office=main&live_poll=800&ambient=0&q=low&pr=0.6&chat_poll=500&chat_bg_poll=700", wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.live && window.__world.chat", 120000)
    wait_until(pg, "() => window.__world.growth && window.__world.growth.ready", 15000)
    pg.evaluate("() => { if (window.__world.growth) window.__world.growth.cfg.settleHour = 99; }")   # 台北 18:00 後的「今日結算」卡會擋住點擊
    return pg, got


def _mf_main(b, base):
    if not _sh.which("node") or not _os.path.exists(_MF_DEV):
        ok("會員整條流程：略過（這台沒有 node 或找不到 devserver.mjs）", True)
        return
    o = _rup(base)
    srv = _MfSrv("%s://%s" % (o.scheme, o.netloc))
    try:
        # 站長辦公室（main）先放一筆事件，之後驗會員看不到它
        srv.events(srv.code, [_mf_ev("SessionStart", "s-own", "站長專案"), _mf_ev("SubagentStart", "s-own", "站長專案", agent_id="own-1", agent_type="Explore")])
        # ───── ① 一般會員還沒建辦公室：引導指向入口頁、不產生碼 ─────
        c = _mf_ctx(b, srv, _MF_MEM, False)
        pg, got = _mf_open(c, base)
        ok("會員：辦公室頁載入完成", got)
        if not got:
            return
        pg.evaluate("() => window.__world.live.openGuide()")
        got = wait_until(pg, "() => !document.getElementById('aioGuide').hidden && document.querySelector('#aioC2 [data-a=cpcode]')", 20000)
        ok("會員：「連接我的 Claude」打開，有「複製提示詞」「複製接入碼」", got)
        pg.click("#aioC2 [data-a=cpcode]")
        got = wait_until(pg, "() => /先建立你自己的辦公室/.test(document.getElementById('aioGuide').innerText)", 20000)
        ok("會員還沒建辦公室：引導寫「先建立你自己的辦公室」、沒有產生接入碼", got and pg.evaluate("() => !window.__world.live.code"), pg.inner_text("#aioGuide")[:160])
        _mf_shot(pg, "mf0_先建辦公室.png")
        # ───── ② 建好辦公室 → 產生自己的接入碼 ─────
        r = srv.req("/v1/offices", {"name": "我的辦公室"}, {"Origin": srv.origin, "X-AIO-Session": _MF_MEM})
        ok("會員建立自己的辦公室成功", r.get("ok"), r)
        pg.evaluate("() => window.__world.live.closeGuide(); window.__world.live.openGuide()")
        wait_until(pg, "() => document.querySelector('#aioC2 [data-a=cpcode]')", 20000)
        gt = pg.inner_text("#aioGuide")
        ok("會員建好辦公室後：引導沒有擋牆", "只開放站長" not in gt and "請先登入" not in gt and "先建立你自己的辦公室" not in gt, gt[:200])
        pg.click("#aioC2 [data-a=cpcode]")
        got = wait_until(pg, "() => !!window.__world.live.code", 20000)
        cfg = pg.evaluate("() => ({ office: window.__world.live.cfg.office, code: window.__world.live.code, guideOwner: window.__world.live.guide.owner })")
        ok("會員：按「複製接入碼」自動產生自己的接入碼（綁自己的代號 u_…，不是 main）", got and cfg["office"].startswith("u_") and cfg["guideOwner"] == "owner", {k: v for k, v in cfg.items() if k != "code"})
        mcode = cfg["code"]
        pg.click("#aioC1 [data-a=viewp]")
        pr = pg.inner_text("#aioPrompt") if pg.query_selector("#aioPrompt") else ""
        ok("會員：提示詞顯示出來，主機是收件端、不含接入碼", "127.0.0.1" in pr and mcode not in pr and "{HOST}" not in pr, pr[:120])
        bad = [w for w in _MF_BAN if w in pg.inner_text("#aioGuide")]
        ok("會員引導：沒有禁用字", not bad, bad)
        _mf_shot(pg, "mf1_會員連接我的Claude.png")
        # ───── ③ 會員自己的 Claude 送事件 → 畫面自己的員工開始工作 ─────
        r = srv.events(mcode, [_mf_ev("SessionStart", "s-mem", "我的專案"), _mf_ev("SubagentStart", "s-mem", "我的專案", agent_id="mem-1", agent_type="general-purpose")])
        ok("會員的 Claude 用自己的接入碼送事件成功", r.get("ok"), r)
        got = wait_until(pg, "() => window.__world.live.status === 'ok' && window.__world.chars.has('general-purpose') && ['sit', 'walk'].includes(window.__world.chars.get('general-purpose').state) && !window.__world.chars.get('general-purpose').away", 60000)   # 走去座位（walk）或已坐下（sit）都算開始工作；慢機器上走路要很久
        st = pg.evaluate("() => ({ st: window.__world.live.status, total: window.__world.live.data && window.__world.live.data.total_events, gp: window.__world.chars.has('general-purpose') ? window.__world.chars.get('general-purpose').state : null, ex: window.__world.chars.has('Explore') && !window.__world.chars.get('Explore').away && window.__world.chars.get('Explore').object3D.visible })")
        ok("會員：畫面讀自己的辦公室，自己的員工（general-purpose）開始工作、狀態「即時」", got and st["st"] == "ok" and st["gp"] in ("sit", "walk"), st)
        ok("會員：看不到站長辦公室的員工與事件（隔離）", not st["ex"] and st["total"] == 2, st)
        # 會員畫面走區塊模式：只有 CEO＋自己實際有的 Agent，沒有站長的部門與示範同事
        dn = pg.evaluate("() => (window.__world.org.departments || []).map(d => d.name)")
        vis = pg.evaluate("() => [...window.__world.chars.values()].filter(c => !c.away && c.object3D.visible && !c.spec.pet).map(c => c.spec.id).sort()")
        ok("會員畫面：區塊模式（blocks）、網址帶專案", pg.evaluate("() => !!window.__world.blocks") and "project=" in pg.url, pg.url)
        ok("會員畫面：只有 CEO＋自己的 general-purpose（沒有站長的示範同事）", vis == ["ceo", "general-purpose"], vis)
        ok("會員畫面：場景裡沒有站長的部門名稱", len(dn) >= 5 and not [d for d in dn if d in pg.inner_text("body")], dn)
        _mf_shot(pg, "mf2_會員員工工作中.png")
        # ───── ④ 對話框送出 ─────
        pg.evaluate("() => { window.__world.live.closeGuide && window.__world.live.closeGuide(); }")
        pg.evaluate("() => window.__world.chat.openTo && window.__world.chat.openTo('ceo')")
        pg.click("#chatText")
        got = wait_until(pg, "() => window.__world.chat.mode === 'ok'", 30000)
        ok("會員：對話框可以用（mode=ok）", got, pg.evaluate("() => window.__world.chat.mode"))
        lst = pg.evaluate("() => [...document.querySelectorAll('.mc-th')].map(e => e.innerText.replace(/\\s+/g, ' ').trim())")
        ok("會員對話框：部門清單只有 CEO 與自己的成員，沒有站長的部門", len(lst) >= 1 and not [d for d in dn if any(d in t for t in lst)], lst)
        pg.keyboard.type("幫我整理今天的待辦", delay=10)
        pg.keyboard.press("Enter")
        got = wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length >= 1", 20000)
        ok("會員：對話框送出成功，訊息出現在對話框", got and "幫我整理今天的待辦" in pg.inner_text("#chatList"), pg.inner_text("#chatList")[:200])
        pm = srv.req("/v1/inbox/pull", {"session_id": "s-mem", "wait": 0}, {"Authorization": "Bearer " + mcode})
        msgs = pm.get("messages") or []
        ok("會員自己的 Claude 取得到這則指令", len(msgs) == 1 and msgs[0].get("text") == "幫我整理今天的待辦", pm)
        po = srv.req("/v1/inbox/pull", {"session_id": "s-own", "wait": 0}, {"Authorization": "Bearer " + srv.code})
        ok("站長的 Claude 取不到會員的指令", po.get("ok") and not po.get("messages"), po)
        if msgs:
            srv.req("/v1/inbox/ack", {"id": msgs[0]["id"], "status": "done", "reply": "今天有三件待辦。", "session_id": "s-mem"}, {"Authorization": "Bearer " + mcode})
            got = wait_until(pg, "() => document.querySelector('#chatList').innerText.includes('今天有三件待辦')", 20000)
            ok("回覆回到會員自己的對話框", got, pg.inner_text("#chatList")[:300])
        _mf_shot(pg, "mf3_會員對話.png")
        ok("會員：沒有頁面錯誤", not pg.errs, pg.errs[:3])
        c.close()

        # ───── ⑥ 站長畫面不受影響 ─────
        c = _mf_ctx(b, srv, _MF_OWN, True)
        pg, got = _mf_open(c, base)
        ok("站長：辦公室頁載入完成", got)
        if got:
            got = wait_until(pg, "() => window.__world.live.status === 'ok' && window.__world.live.data && window.__world.live.data.total_events === 2", 60000)
            cfg = pg.evaluate("() => ({ office: window.__world.live.cfg.office || 'main', total: window.__world.live.data && window.__world.live.data.total_events, ex: window.__world.chars.has('Explore') })")
            ok("站長：照舊讀 main（站長自己的事件 2 筆、看不到會員的）", got and cfg["office"] == "main" and cfg["ex"], cfg)
            pg.evaluate("() => window.__world.live.openGuide()")
            wait_until(pg, "() => document.querySelector('#aioC2 [data-a=cpcode]')", 20000)
            wait_until(pg, "() => window.__world.live.guide.owner === 'owner'", 20000)
            gt = pg.inner_text("#aioGuide")
            ok("站長：連接引導照常（沒被擋、沒有登入牆）", "請先登入" not in gt and "先建立你自己的辦公室" not in gt, gt[:160])
            bad = [w for w in _MF_BAN if w in gt]
            ok("站長引導：沒有禁用字", not bad, bad)
            _mf_shot(pg, "mf4_站長引導.png")
            ok("站長：沒有頁面錯誤", not pg.errs, pg.errs[:3])
        c.close()
    finally:
        srv.stop()


register("辦公室會員整條流程", lambda pg, b, base, code: _mf_main(b, base))
