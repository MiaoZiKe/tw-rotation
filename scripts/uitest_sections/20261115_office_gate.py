# 驗收段落「辦公室功能閘門」：AI 辦公室頁（site/office/world.html）的功能鍵＋各方案每日次數＋閘門（site/office/world/js/gate.js）
# 這支由 _uitest.py 用 exec 載入，也能用 /tmp 小跑者單跑；只用 ok()／wait_until()／register()，不要 import _uitest。函式名一律加 _og_ 前綴。
#   ① 註冊會員（每日 下指令 2 次）：送滿 2 則 → 第 3 次被鎖：說明寫在對話框裡（白話、沒有禁用字）、送出鈕灰掉、真的沒有送出、計數（tw.quota＋伺服器）都是 2
#   ② 重新整理後仍被鎖（今天的次數存在 tw.quota、也跟伺服器對帳），不是只擋在記憶體
#   ③ 體驗額度：每日用完後說明改寫「你還有體驗次數 N 次」、送出鈕可按；送出真的打 /v1/grants/hit、收件服務真的收到；體驗用完才被鎖
#   ④ 站主（owner）：後台把次數設 0 也照常送、不計次、不打 /v1/quota/hit
#   ⑤ 訪客（會員系統開、沒登入）：三個鍵都是「要先登入」；連接我的 Claude：每日 1 次，用完不再產生接入碼（收件端只領一次）；
#      開除與重新聘用：每日 1 次，用完確認框寫白話說明、開除鈕灰掉，資訊卡的「重新聘用」不動作並浮出說明
#   ⑥ 預覽／本機 ?demo_tier=free：讀 plan_presets.js 的數字（下指令 5）；會員系統沒開＝全放行（舊行為不變）
#   ⑦ 手機 390×844：被鎖的畫面沒有橫向溢出、字不小於 11px、沒有禁用字
#   ⑧ 主站：「權限」#admin/perm 有「AI 辦公室」分類與三個開關＋次數、「編輯：新會員體驗」#admin/grants 清單列得到三個鍵（需要主站驗收環境，單跑小跑者會略過）
# 帳號服務、收件服務都用 page.route 模擬（https://acct.test、https://aio.test），格式與 workers/account-api、workers/ai-office-bridge 一致。
# 環境變數 GATE_SHOTS 指到資料夾時順便存截圖。
# flake8: noqa

import json as _json
import os as _os
import re as _re
import time as _time
from urllib.parse import urlparse as _up

_OG_AIO = "https://aio.test"
_OG_ACCT = "https://acct.test"
_OG_TOK = "login-token-for-test"
_OG_CODE = "aio_GateTest" + "Code0123456789abcdefABCDEF"
_OG_BAD = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")
_OG_H = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS"}


def _og_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _og_shot(pg, name):
    d = _os.environ.get("GATE_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _OgAcct:
    """假的會員伺服器：/v1/perm/me、/v1/me、/v1/grants/me、/v1/grants/hit、/v1/quota/hit（跟 workers/account-api 同格式）。"""

    def __init__(self, lims=None, owner=False, grants=0, who="member", feats=None):
        self.lims, self.owner, self.who, self.feats = lims or {}, owner, who, feats or {}
        self.grant_left, self.grant_hits, self.quota = grants, [], {}
        self.log = []

    def handle(self, route):
        req = route.request
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=_OG_H)
        p = _up(req.url).path
        b = _json.loads(req.post_data or "{}")
        self.log.append((p, b))
        out, code = {}, 200
        if p == "/v1/perm/me":
            out = {"who": self.who, "plan": "free" if self.who == "member" else "guest", "planName": "註冊會員", "feats": self.feats, "lims": self.lims, "dq": None}
        elif p == "/v1/me":
            out = {"user": {"email": "boss@example.com", "name": "站長", "admin": True, "owner": self.owner}}
        elif p == "/v1/grants/me":
            now = int(_time.time() * 1000)
            gr = []
            if self.grant_left > 0 or self.grant_hits:
                gr = [{"gid": "welcome", "name": "新會員體驗", "kind": "welcome", "start": now - 1000, "end": now + 14 * 86400000,
                       "feats": {"office.cmd": {"max": 2, "used": 2 - self.grant_left, "left": self.grant_left}}}]
            out = {"now": now, "today": {}, "grants": gr}
        elif p == "/v1/grants/hit":
            if self.grant_left <= 0:
                out = {"over": True, "left": 0}
            else:
                self.grant_left -= 1
                self.grant_hits.append(b.get("k"))
                out = {"ok": True, "gid": "welcome", "left": self.grant_left}
        elif p == "/v1/quota/hit":
            k, key = b.get("k"), b.get("key")
            ks = self.quota.setdefault(k, [])
            lim = self.lims.get(k)
            if key and key not in ks:
                if not self.owner and isinstance(lim, int) and len(ks) >= lim:
                    return route.fulfill(status=200, body=_json.dumps({"k": k, "keys": ks, "over": True, "limit": lim}), headers=_OG_H)
                ks.append(key)
            out = {"day": "x", "k": k, "n": len(ks), "keys": list(ks)}
        else:
            out, code = {"error": "not_found"}, 404
        return route.fulfill(status=code, body=_json.dumps(out), headers=_OG_H)

    def n(self, path, k=None):
        return len([1 for (p, b) in self.log if p == path and (k is None or b.get("k") == k)])


class _OgBridge:
    """假的收件服務（收件匣＋領接入碼）。"""

    def __init__(self):
        self.posts, self.claims, self.msgs = [], 0, []

    def handle(self, route):
        req = route.request
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=_OG_H)
        p = _up(req.url).path
        if p == "/v1/claim":
            self.claims += 1
            return route.fulfill(status=200, body=_json.dumps({"ok": True, "office": "main", "code": _OG_CODE + str(self.claims), "exists": True}), headers=_OG_H)
        if "/inbox" not in p:
            return route.fulfill(status=404, body="{}", headers=_OG_H)
        if req.method == "POST":
            b = _json.loads(req.post_data or "{}")
            self.posts.append(b)
            now = int(_time.time() * 1000)
            m = {"id": "m_%016d" % len(self.msgs), "to": b["to"], "text": b["text"], "status": "queued", "created": now, "updated": now, "rev": len(self.msgs) + 1, "reply": None}
            self.msgs.append(m)
            return route.fulfill(status=200, body=_json.dumps({"ok": True, "message": m}), headers=_OG_H)
        return route.fulfill(status=200, body=_json.dumps({"office": "main", "now": int(_time.time() * 1000), "rev": len(self.msgs), "since": 0, "messages": list(self.msgs),
                                                           "open": [m for m in self.msgs if m["status"] == "queued"], "limits": {"max_text": 2000, "max_pending": 20}, "session_last_seen": None}), headers=_OG_H)


def _og_open(b, base, br, ac, login=True, w=1280, h=800, touch=False, query="", cfg=True, ls_extra=None):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    ls = {"aiOffice.daytime": "day", "aiOffice.live.v1": _json.dumps({"url": _OG_AIO})}
    if login:
        ls["tw.acct.tok"] = _OG_TOK
    ls.update(ls_extra or {})
    c.add_init_script("try{" + "".join("localStorage.setItem(%s,%s);" % (_json.dumps(k), _json.dumps(v)) for k, v in ls.items()) + "}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "401" not in m.text and "Failed to load resource" not in m.text else None)
    pg.route(_OG_AIO + "/**", br.handle)
    if cfg:
        pg.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: '%s' };" % _OG_ACCT, headers={"Content-Type": "application/javascript"}))
        pg.route(_OG_ACCT + "/**", ac.handle)
    pg.goto(_og_root(base) + "/office/world.html?ambient=0&q=low&pr=0.6&chat_poll=500&chat_bg_poll=700&live_poll=700" + query, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat && window.__world.live && window.__world.gate", 90000)
    if got:
        pg.evaluate("() => { __world.speed = 8; }")
    return c, pg, got


def _og_vis(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && !e.hidden && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }", sel)


def _og_used(pg, k):
    return pg.evaluate("(k) => { try { const d = JSON.parse(localStorage.getItem('tw.quota') || '{}'); return ((d.k || {})[k] || []).length; } catch (e) { return -1; } }", k)


def _og_wused(pg, k, n, ms=30000):
    """今天的用量要到 n：機器忙（3D 場景加上別的驗收同時在跑）時動作完成得慢，所以用等的，不是讀一次。"""
    return bool(wait_until(pg, "() => { try { return (((JSON.parse(localStorage.getItem('tw.quota') || '{}')).k || {})['%s'] || []).length === %d; } catch (e) { return false; } }" % (k, n), ms))


def _og_js(pg, sel):
    """3D 場景把主執行緒吃滿時 Playwright 的「等元素穩定」會逾時；這幾顆按鈕只驗功能，用頁面內的 click() 直接按。"""
    pg.evaluate("(s) => { const e = document.querySelector(s); if (!e) throw new Error('找不到 ' + s); e.click(); }", sel)


def _og_srv(pg, ac, k, n):
    """伺服器對帳是動作做完後才非同步送出的：最多等 2 秒再看伺服器記了幾次。"""
    for _ in range(20):
        if len(ac.quota.get(k, [])) >= n:
            break
        pg.wait_for_timeout(100)
    return len(ac.quota.get(k, [])) == n


def _og_send(pg, text):
    pg.fill("#chatText", text)
    pg.keyboard.press("Control+Enter")


# ───────────────────────── ① ② 註冊會員：下指令用到上限 ─────────────────────────
def _og_member(b, base):
    br, ac = _OgBridge(), _OgAcct(lims={"office.cmd": 2, "office.connect": 1, "office.hr": 1})
    c, pg, got = _og_open(b, base, br, ac)
    try:
        ok("閘門：辦公室頁載入完成、閘門模組在", got)
        if not got:
            return
        pg.wait_for_timeout(1200)
        ok("閘門：沒打開對話框之前不打會員伺服器", ac.n("/v1/perm/me") == 0, ac.log[:3])
        pg.click("#chatBtn")
        ok("閘門：打開對話框後讀了這個人的權限（/v1/perm/me）與站長旗標（/v1/me）、狀態來源是伺服器", wait_until(pg, "() => __world.gate.state.src === 'server' && __world.chat.mode === 'ok'", 15000) and ac.n("/v1/perm/me") >= 1 and ac.n("/v1/me") >= 1)
        ok("閘門：註冊會員每日 2 次、今天還沒用、說明框是空的", pg.evaluate("() => { const p = __world.gate.peek('office.cmd'); return p.pass && p.limit === 2 && p.used === 0; }") and not _og_vis(pg, "#chatGate"))
        _og_send(pg, "第一則")
        ok("送出第 1 則：收件服務收到、計數 1（本機 tw.quota＋伺服器）", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 30000) and len(br.posts) == 1 and _og_used(pg, "office.cmd") == 1 and len(ac.quota.get("office.cmd", [])) == 1,
           (len(br.posts), _og_used(pg, "office.cmd"), ac.quota))
        ok("送出第 1 則：還沒到上限，不顯示被鎖說明", not _og_vis(pg, "#chatGate"))
        _og_send(pg, "第二則")
        ok("送出第 2 則：收件服務收到、計數 2", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 2", 30000) and len(br.posts) == 2 and _og_used(pg, "office.cmd") == 2)
        ok("用到上限：對話框裡出現白話說明「今天的下指令次數用完了（今天 2／2），明天會恢復。」", wait_until(pg, "() => !document.getElementById('chatGate').hidden", 4000) and "今天的下指令次數用完了（今天 2／2），明天會恢復" in pg.inner_text("#chatGate"), pg.inner_text("#chatGate"))
        pg.fill("#chatText", "第三則")
        ok("用到上限：送出鈕灰掉（打了字也不能按）", pg.is_disabled("#chatSend"))
        pg.keyboard.press("Control+Enter")
        pg.wait_for_timeout(600)
        ok("用到上限：Ctrl+Enter 也送不出去——收件服務沒有收到第 3 則、計數仍是 2", len(br.posts) == 2 and _og_used(pg, "office.cmd") == 2 and len(ac.quota.get("office.cmd", [])) == 2, (len(br.posts), _og_used(pg, "office.cmd")))
        ok("用到上限：說明沒有禁用字（價格／付費／升級／方案…）", not _OG_BAD.search(pg.inner_text("#chatPanel")), _OG_BAD.findall(pg.inner_text("#chatPanel")))
        ok("用到上限：說明沒有噴錯誤碼或英文例外", not _re.search(r"error|undefined|null|exception", pg.inner_text("#chatGate"), _re.I))
        _og_shot(pg, "gate_1_桌機_用完.png")
        pg.reload(wait_until="domcontentloaded")
        got2 = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat && window.__world.gate", 90000)
        ok("② 重新整理：頁面重新載入完成", got2)
        pg.click("#chatBtn")
        ok("② 重新整理後打開對話框：仍然被鎖（次數存在 tw.quota、跟伺服器對帳，不是只在記憶體）", wait_until(pg, "() => !document.getElementById('chatGate').hidden && __world.gate.peek('office.cmd').used === 2", 15000) , pg.evaluate("() => __world.gate.peek('office.cmd')"))
        pg.fill("#chatText", "重新整理後再試")
        ok("② 重新整理後：送出鈕仍灰", pg.is_disabled("#chatSend"))
        ok("閘門：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ③ 體驗額度 ─────────────────────────
def _og_grants(b, base):
    br, ac = _OgBridge(), _OgAcct(lims={"office.cmd": 1}, grants=2)
    c, pg, got = _og_open(b, base, br, ac)
    try:
        if not ok("體驗：辦公室頁載入完成", got):
            return
        pg.click("#chatBtn")
        wait_until(pg, "() => __world.gate.state.src === 'server' && __world.chat.mode === 'ok'", 15000)
        _og_send(pg, "每日第一則")
        ok("體驗：每日 1 次先用掉（不扣體驗）", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 30000) and ac.n("/v1/grants/hit") == 0 and _og_used(pg, "office.cmd") == 1)
        ok("體驗：每日用完後，說明改寫「你還有體驗次數 2 次，這一次會用掉 1 次」", wait_until(pg, "() => !document.getElementById('chatGate').hidden && document.getElementById('chatGate').textContent.includes('體驗次數 2 次')", 6000), pg.inner_text("#chatGate"))
        pg.fill("#chatText", "用體驗送的第一則")
        ok("體驗：送出鈕仍可按（體驗可以繼續）", not pg.is_disabled("#chatSend"))
        pg.keyboard.press("Control+Enter")
        ok("體驗：送出 → 真的打 /v1/grants/hit（功能鍵 office.cmd）、收件服務收到第 2 則", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 2", 30000) and ac.n("/v1/grants/hit", "office.cmd") == 1 and len(br.posts) == 2, (ac.grant_hits, len(br.posts)))
        ok("體驗：體驗剩 1 次、說明改寫「體驗次數 1 次」", wait_until(pg, "() => document.getElementById('chatGate').textContent.includes('體驗次數 1 次')", 6000), pg.inner_text("#chatGate"))
        ok("體驗：不重複扣每日（每日計數仍是 1）", _og_used(pg, "office.cmd") == 1)
        _og_shot(pg, "gate_2_桌機_體驗可繼續.png")
        _og_send(pg, "用體驗送的第二則")
        ok("體驗：第二次體驗也送得出去（共 3 則、體驗打了 2 次）", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 3", 30000) and ac.n("/v1/grants/hit", "office.cmd") == 2 and len(br.posts) == 3)
        ok("體驗用完：說明改寫「體驗次數也用完了…明天會恢復」或同義白話、送出鈕灰掉", wait_until(pg, "() => document.getElementById('chatSend').disabled && !document.getElementById('chatGate').hidden && document.getElementById('chatGate').textContent.includes('明天會恢復')", 6000), pg.inner_text("#chatGate"))
        pg.fill("#chatText", "第四則")
        pg.keyboard.press("Control+Enter")
        pg.wait_for_timeout(500)
        ok("體驗用完：第 4 則送不出去、不再打 /v1/grants/hit", len(br.posts) == 3 and ac.n("/v1/grants/hit") == 2)
        ok("體驗：說明沒有禁用字", not _OG_BAD.search(pg.inner_text("#chatPanel")), _OG_BAD.findall(pg.inner_text("#chatPanel")))
        ok("體驗：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ④ 站長不受限 ─────────────────────────
def _og_owner(b, base):
    br, ac = _OgBridge(), _OgAcct(lims={"office.cmd": 0, "office.connect": 0, "office.hr": 0}, owner=True, feats={"office.cmd": False})
    c, pg, got = _og_open(b, base, br, ac)
    try:
        if not ok("站長：辦公室頁載入完成", got):
            return
        pg.click("#chatBtn")
        wait_until(pg, "() => __world.gate.state.src === 'server' && __world.chat.mode === 'ok'", 15000)
        ok("站長：就算範本把下指令關掉、次數設 0，也判定放行（站長不受限）", pg.evaluate("() => __world.gate.state.owner === true && __world.gate.peek('office.cmd').pass === true") and not _og_vis(pg, "#chatGate"))
        for i in range(3):
            _og_send(pg, "站長第 %d 則" % (i + 1))
            wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === %d" % (i + 1), 8000)
        ok("站長：連送 3 則都收得到、沒有被鎖說明", len(br.posts) == 3 and not _og_vis(pg, "#chatGate"))
        ok("站長：不計次（tw.quota 沒有 office.cmd）、也不打 /v1/quota/hit", _og_used(pg, "office.cmd") == 0 and ac.n("/v1/quota/hit") == 0, (_og_used(pg, "office.cmd"), ac.n("/v1/quota/hit")))
        ok("站長：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ⑤ 訪客／連接我的 Claude／開除與重新聘用 ─────────────────────────
def _og_guest(b, base):
    br, ac = _OgBridge(), _OgAcct(who="guest", lims={"office.cmd": 0, "office.connect": 0, "office.hr": 0})
    c, pg, got = _og_open(b, base, br, ac, login=False)
    try:
        if not ok("訪客：辦公室頁載入完成", got):
            return
        info = pg.evaluate("async () => { await __world.gate.load(); return ['office.cmd', 'office.connect', 'office.hr'].map(k => { const p = __world.gate.peek(k); return [p.pass, p.kind, p.note]; }); }")
        ok("訪客：三個鍵都不開放、說明都寫「要先登入才能使用」", all((not x[0]) and x[1] == "login" and "先登入" in x[2] for x in info), info)
        ok("訪客：說明沒有禁用字", not any(_OG_BAD.search(x[2]) for x in info), info)
        pg.click("#chatBtn")
        ok("訪客：下指令對話框走原本的「請先登入」說明、沒有噴錯", wait_until(pg, "() => __world.chat.mode === 'nologin'", 8000) and pg.is_disabled("#chatSend"))
        ok("訪客：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _og_connect_hr(b, base):
    br, ac = _OgBridge(), _OgAcct(lims={"office.cmd": 5, "office.connect": 1, "office.hr": 1})
    c, pg, got = _og_open(b, base, br, ac)
    try:
        if not ok("連接與人事：辦公室頁載入完成", got):
            return
        # —— 連接我的 Claude：每日 1 次
        pg.evaluate("() => __world.live.openGuide()")
        ok("連接：引導視窗打開", _og_vis(pg, "#aioGuide"))
        _og_js(pg, "#aioGuide [data-a=cpcode]")
        ok("連接：第 1 次產生接入碼成功（遮罩版出現、收件端領了 1 次、計數 1、伺服器記 1）", wait_until(pg, "() => !!document.getElementById('aioCodeMask')", 30000) and br.claims == 1 and _og_wused(pg, "office.connect", 1) and _og_srv(pg, ac, "office.connect", 1),
           (br.claims, _og_used(pg, "office.connect")))
        _og_js(pg, "#aioGuide .aio-gx")
        wait_until(pg, "() => !__world.live.code", 20000)
        pg.evaluate("() => __world.live.openGuide()")
        _og_js(pg, "#aioGuide [data-a=cpcode]")
        ok("連接：第 2 次被鎖——視窗裡寫白話「今天的連接次數用完了（今天 1／1），明天會恢復」", wait_until(pg, "() => document.getElementById('aioGuide').textContent.includes('連接次數用完了')", 30000), pg.inner_text("#aioGuide"))
        ok("連接：被鎖時不再向收件端領接入碼（仍是 1 次）、沒有遮罩版", br.claims == 1 and not pg.query_selector("#aioCodeMask"))
        ok("連接：說明沒有禁用字", not _OG_BAD.search(pg.inner_text("#aioGuide")), _OG_BAD.findall(pg.inner_text("#aioGuide")))
        _og_shot(pg, "gate_3_桌機_連接被鎖.png")
        _og_js(pg, "#aioGuide .aio-gx")
        # —— 開除與重新聘用：每日 1 次
        pg.evaluate("() => __world.hr.ask(['frontend-ui'])")
        ok("開除：確認框打開、還沒用過所以沒有被鎖說明、開除鈕可按", _og_vis(pg, "#fireDlg") and not _og_vis(pg, "#fdGate") and not pg.is_disabled("#fireGo"))
        _og_js(pg, "#fireGo")
        _og_js(pg, "#fireGo")
        ok("開除：第二次按才執行、frontend-ui 被開除、計數 1", wait_until(pg, "() => !document.getElementById('fireDlg') && __world.hr.fired.has('frontend-ui')", 30000) and _og_wused(pg, "office.hr", 1) and _og_srv(pg, ac, "office.hr", 1))
        pg.evaluate("() => __world.hr.ask(['mobile-ui'])")
        ok("開除：今天的次數用完後再開確認框 → 框裡寫白話說明、開除鈕灰掉", wait_until(pg, "() => { const g = document.getElementById('fdGate'); return !!g && !g.hidden && g.textContent.includes('人事異動次數用完了') && document.getElementById('fireGo').disabled; }", 20000), pg.evaluate("() => (document.getElementById('fdGate') || {}).textContent"))
        ok("開除：確認框的說明沒有禁用字", not _OG_BAD.search(pg.inner_text("#fireDlg")), _OG_BAD.findall(pg.inner_text("#fireDlg")))
        _og_shot(pg, "gate_4_桌機_開除被鎖.png")
        _og_js(pg, "#fireCancel")
        ok("開除：取消後沒有人被多開除", pg.evaluate("() => !__world.hr.fired.has('mobile-ui') && __world.hr.fired.size === 1"))
        # 重新聘用（資訊卡的鈕）
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('frontend-ui'))")
        ok("重新聘用：被開除者的資訊卡有「重新聘用」鈕", _og_vis(pg, "#card [data-hr=hire]"))
        _og_js(pg, "#card [data-hr=hire]")
        ok("重新聘用：次數用完 → 沒有執行（仍在無業遊民區）、畫面下方浮出白話說明", wait_until(pg, "() => { const e = document.getElementById('gateSay'); return !!e && !e.hidden && e.textContent.includes('人事異動次數用完了'); }", 20000) and pg.evaluate("() => __world.hr.fired.has('frontend-ui')"), pg.evaluate("() => (document.getElementById('gateSay') || {}).textContent"))
        ok("重新聘用：說明沒有禁用字", not _OG_BAD.search(pg.inner_text("#gateSay")), pg.inner_text("#gateSay"))
        _og_shot(pg, "gate_5_桌機_重新聘用被鎖.png")
        ok("連接與人事：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ⑥ 預覽示範身分／會員系統沒開 ─────────────────────────
def _og_demo(b, base):
    br, ac = _OgBridge(), _OgAcct()
    c, pg, got = _og_open(b, base, br, ac, query="&demo_tier=free")
    try:
        if not ok("示範身分：辦公室頁載入完成", got):
            return
        r = pg.evaluate("async () => { await __world.gate.load(); const p = __world.gate.peek('office.cmd'); return { src: __world.gate.state.src, limit: p.limit, pass: p.pass, hr: __world.gate.peek('office.hr').limit, cn: __world.gate.peek('office.connect').limit }; }")
        ok("示範身分 ?demo_tier=free：讀 plan_presets.js——下指令 5、連接 3、人事 5，不打會員伺服器", r["src"] == "demo" and r["limit"] == 5 and r["cn"] == 3 and r["hr"] == 5 and ac.log == [], (r, ac.log[:2]))
    finally:
        c.close()
    c, pg, got = _og_open(b, base, br, ac, query="&demo_tier=guest")
    try:
        r = pg.evaluate("async () => { await __world.gate.load(); const p = __world.gate.peek('office.cmd'); return [p.pass, p.kind]; }")
        ok("示範身分 ?demo_tier=guest：下指令不開放（要先登入）", r == [False, "login"], r)
    finally:
        c.close()
    c, pg, got = _og_open(b, base, br, ac, cfg=False)
    try:
        r = pg.evaluate("async () => { await __world.gate.load(); return ['office.cmd', 'office.connect', 'office.hr'].map(k => __world.gate.peek(k).pass); }")
        ok("會員系統沒開（沒有 account_config 網址）：三個鍵一律放行（舊行為不變）", r == [True, True, True], r)
    finally:
        c.close()


# ───────────────────────── ⑦ 手機 390×844 ─────────────────────────
def _og_mobile(b, base):
    br, ac = _OgBridge(), _OgAcct(lims={"office.cmd": 1, "office.connect": 1, "office.hr": 1})
    c, pg, got = _og_open(b, base, br, ac, w=390, h=844, touch=True)
    try:
        if not ok("手機：辦公室頁載入完成", got):
            return
        pg.tap("#moreBtn")
        pg.tap("#chatBtn")
        wait_until(pg, "() => __world.chat.mode === 'ok' && __world.gate.state.src === 'server'", 15000)
        pg.tap("#mcStrip [data-room=ceo]")        # 手機改成先看對話清單、點進對話才有輸入框（2026-11-15 夜）
        pg.fill("#chatText", "手機第一則")
        pg.tap("#chatSend")
        ok("手機：送出第 1 則", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 30000))
        ok("手機：用到上限後說明出現、送出鈕灰掉", wait_until(pg, "() => !document.getElementById('chatGate').hidden", 6000) and pg.is_disabled("#chatSend"))
        _og_shot(pg, "gate_m1_手機_被鎖.png")
        info = pg.evaluate("""() => {
            const out = { hscroll: document.documentElement.scrollWidth > innerWidth + 1, small: [], over: [] };
            const P = document.getElementById('chatPanel'), pr = P.getBoundingClientRect();
            for (const e of P.querySelectorAll('*')) {
                const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
                const t = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).length;
                if (t && parseFloat(getComputedStyle(e).fontSize) < 11) out.small.push(e.tagName + ':' + e.textContent.trim().slice(0, 12));
                if (r.right > pr.right + 1 || r.left < pr.left - 1) out.over.push(e.tagName + '.' + e.className);
            }
            return out; }""")
        ok("手機：被鎖畫面沒有橫向溢出、沒有東西超出對話框", not info["hscroll"] and not info["over"], info)
        ok("手機：字不小於 11px", not info["small"], info["small"][:3])
        ok("手機：沒有禁用字", not _OG_BAD.search(pg.inner_text("#chatPanel")))
        pg.tap("#chatX")
        pg.evaluate("() => __world.hr.ask(['frontend-ui'])")
        pg.tap("#fireGo")
        pg.tap("#fireGo")
        wait_until(pg, "() => __world.hr.fired.has('frontend-ui')", 8000)
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('frontend-ui'))")
        pg.tap("#card [data-hr=hire]")
        ok("手機：重新聘用被鎖時浮出說明、在畫面內、字不小於 11px", wait_until(pg, "() => { const e = document.getElementById('gateSay'); if (!e || e.hidden) return false; const r = e.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && parseFloat(getComputedStyle(e).fontSize) >= 11; }", 6000))
        _og_shot(pg, "gate_m2_手機_說明浮層.png")
        ok("手機：沒有橫向溢出", not pg.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1"))
        ok("手機：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ⑨ 下指令介面補強：數字徽章、手機鍵盤彈出 ─────────────────────────
def _og_ui(b, base):
    br, ac = _OgBridge(), _OgAcct(lims={"office.cmd": 5})
    c, pg, got = _og_open(b, base, br, ac)
    try:
        if not ok("徽章：辦公室頁載入完成", got):
            return
        _og_js(pg, "#chatBtn")
        wait_until(pg, "() => __world.chat.mode === 'ok'", 30000)
        _og_send(pg, "徽章測試")
        wait_until(pg, "() => !document.getElementById('chatN').hidden", 30000)
        _og_js(pg, "#chatX")          # 徽章長在收合的輸入列上；聊天室窗展開時那顆鈕藏起來（2026-11-15 夜改版），所以收合後再量
        r = pg.evaluate("() => { const e = document.getElementById('chatN'), s = getComputedStyle(e), b = e.getBoundingClientRect(); return { bw: s.borderTopWidth, mt: s.marginTop, w: Math.round(b.width), h: Math.round(b.height), t: e.textContent }; }")
        ok("徽章：沒吃到下拉三角形樣式（無邊框、無上邊距）、是 18 高的圓、數字 1", r["bw"] == "0px" and r["mt"] == "0px" and r["h"] == 18 and r["w"] >= 18 and r["t"] == "1", r)
        _og_shot(pg, "gate_6_徽章.png")
    finally:
        c.close()
    br, ac = _OgBridge(), _OgAcct(lims={"office.cmd": 5})
    c, pg, got = _og_open(b, base, br, ac, w=390, h=480, touch=True)
    try:
        pg.evaluate("() => document.getElementById('moreBtn').click()")
        pg.evaluate("() => document.getElementById('chatBtn').click()")
        wait_until(pg, "() => __world.chat.mode === 'ok'", 30000)
        _og_js(pg, "#mcStrip [data-room=ceo]")        # 手機先看清單、點進對話才有輸入框
        pg.fill("#chatText", "鍵盤測試")
        _og_js(pg, "#chatSend")
        wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 30000)
        r = pg.evaluate("() => { const l = document.getElementById('chatList').getBoundingClientRect(), b = document.querySelector('#chatList .c-me').getBoundingClientRect(), p = document.getElementById('chatPanel').getBoundingClientRect(); return { lt: l.top, lb: l.bottom, bt: b.top, bb: b.bottom, ph: p.height, lh: l.height }; }")
        ok("手機鍵盤彈出（可視高 480）：訊息氣泡完整看得見（沒被切；撤回改成長按小選單）", r["bt"] >= r["lt"] - 1 and r["bb"] <= r["lb"] + 1 and r["lh"] >= 100, r)
        _og_shot(pg, "gate_m3_鍵盤480.png")
    finally:
        c.close()


def _og_all(b, base):
    for fn in (_og_member, _og_grants, _og_owner, _og_guest, _og_connect_hr, _og_demo, _og_mobile, _og_ui):
        try:
            fn(b, base)
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok("辦公室功能閘門：%s 中途爆掉" % fn.__name__, False, str(e)[:300])


register("辦公室功能閘門", lambda pg, b, base, code: _og_all(b, base))


# ───────────────────────── ⑧ 主站「權限」「體驗」編輯器看得到新鍵（只在 _uitest.py 主站環境跑；單跑小跑者略過） ─────────────────────────
def _og_admin(b, base):
    if "_free_port" not in globals() or "ROOT" not in globals():
        print("略過：這一段要在 _uitest.py 主站環境跑（需要本機 account-api）")
        return
    import json, re, subprocess, time, urllib.request
    T = "辦公室功能鍵權限頁"
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    errs = []
    try:
        up = False
        for _ in range(40):
            try:
                up = json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api 起得來", up):
            return
        c = b.new_context(viewport={"width": 1440, "height": 900})
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        ad = c.new_page()
        ad.on("pageerror", lambda e: errs.append(str(e)))
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('acctBtn')", 8000)
        ad.click("#acctBtn")
        with ad.expect_popup() as pi:
            ad.click("#acctGo")
        pop = pi.value
        pop.wait_for_selector("#as-andy", timeout=8000)
        pop.click("#as-andy")
        wait_until(ad, "() => !!(window.TwAccount && TwAccount.user())", 12000)
        ad.evaluate("() => { location.hash = '#admin/perm'; }")
        wait_until(ad, "() => location.hash === '#admin/perm' && document.querySelectorAll('#pmCats .pmcat').length > 0", 12000)
        ad.click("#ptTier button[data-tier='free']")
        if not ad.evaluate("() => !!document.querySelector(\"#pmCats input[data-f='office.cmd']\") || !!document.querySelector(\"#pmCats select[data-f='office.cmd']\")"):
            wait_until(ad, "() => !!document.querySelector(\"#pmCats .pmcat[data-cat='office']\")", 5000)
            ad.click("#pmCats .pmcat[data-cat='office'] .pmcathd")
        d = ad.evaluate("""() => { const c = document.querySelector("#pmCats .pmcat[data-cat='office']"); if (!c) return null;
            const ids = [...c.querySelectorAll('input[role=switch][data-f]')].map(i => [i.dataset.f, i.checked]);
            const sels = [...c.querySelectorAll('select[data-f]')].map(s => [s.dataset.f, s.value]);
            return { h: (c.querySelector('h3') || {}).textContent || '', ids, sels, last: [...document.querySelectorAll('#pmCats .pmcat')].map(x => x.dataset.cat).pop() }; }""")
        ok(f"{T}：#admin/perm（註冊會員範本）有「AI 辦公室」分類卡、四個開關都開（含 2026-11-16 新增的 office.overview 總覽與通知）", bool(d) and "AI 辦公室" in d["h"] and [x[0] for x in d["ids"]] == ["office.cmd", "office.connect", "office.hr", "office.overview"] and all(x[1] for x in d["ids"]), d)
        ok(f"{T}：#admin/perm 三個鍵各有「每日次數」下拉（註冊會員預設 5／3／5）", bool(d) and sorted(d["sels"]) == sorted([["office.cmd", "5"], ["office.connect", "3"], ["office.hr", "5"]]), d and d["sels"])
        ad.evaluate("() => { location.hash = '#admin/grants'; }")
        wait_until(ad, "() => document.querySelectorAll('#agrList button[data-edit]').length > 0", 10000)
        ad.click("#agrList button[data-edit=\"welcome\"]")
        wait_until(ad, "() => document.querySelectorAll('#agrFeats input[data-fk]').length > 10", 5000)
        keys = ad.evaluate("() => [...document.querySelectorAll('#agrFeats input[data-fk]')].map(i => i.dataset.fk)")
        ok(f"{T}：「編輯：新會員體驗」清單列得到三個鍵（不在法遵禁止清單）", all(k in keys for k in ("office.cmd", "office.connect", "office.hr")), [k for k in keys if k.startswith("office")])
        pre = ad.evaluate("""() => [...document.querySelectorAll('#agrFeats input[data-fk]')].filter(i => i.dataset.fk.startsWith('office.')).map(i => i.checked)""")
        ok(f"{T}：體驗額度不替站長預設（四個鍵預設都沒勾）", pre == [False, False, False, False], pre)
        ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])
        c.close()
    finally:
        dev.terminate()


register("辦公室功能鍵權限頁", lambda pg, b, base, code: _og_admin(b, base))
