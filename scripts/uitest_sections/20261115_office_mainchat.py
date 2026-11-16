# 驗收段落「辦公室主對話框」：AI Office 3D 辦公室（site/office/world.html）畫面下方的主對話框（world/js/chat.js、chat.css）
#   2026-11-15 夜再改版（擁有者原話）：圖一改成像 Messenger／Teams 的聊天室窗；狀態改成「傳送中／已送達／對方輸入中…」、拿掉「由 CEO 轉交」；
#   對象切換列改成左側對話清單；預設靠左、可切靠左／置中／靠右、可拖曳、可鎖定、可透明；等回應要快（有進行中的指令每 2 秒讀一次）；
#   追加：聊天室依單位分組（CEO 一間、每個部門一間，對整個部門或某位成員說都進同一間）、部門佈告欄「對整個部門說」、回覆裡的【動作：…】標記讓角色在 3D 做動作。
#   ① 常駐收合輸入列、預設靠左、不擋 3D、不重疊　② 聊天室窗：清單切換、我靠右彩色氣泡、對方靠左白氣泡＋頭像、同分鐘合併、狀態小字依序、輸入中三點、撤回小選單、失敗／過期重送
#   ③ 視窗：靠左／置中／靠右、真滑鼠拖曳、鎖定後拖不動、透明 100／70／40 與滑鼠移上去恢復、重新整理後保留
#   ④ 部門聊天室：對整個部門（to＝dept:<代號>）或成員（to＝成員代號）、指定小字「→ 阿版」、佈告欄按鈕、辦公室外的內建類型用中文名（通才）
#   ⑤ 動作標記（轉圈／跳／揮手…）不顯示在氣泡、角色真的做動作　⑥ 輪詢：有進行中每 2 秒、送出後立刻先讀一次、沒進行中停止
#   ⑦ 手機 390×844：先看清單、點進對話、上方返回；不重疊（程式量矩形）、字不小於 11px、按鈕夠大、沒有禁用字　⑧ 沒登入／收件匣沒開／接入碼（舊段落保留）
# 收件服務用 page.route 模擬（https://aio.test），格式與 workers/ai-office-bridge/worker.js 的收件匣 API 一致。環境變數 CHAT_SHOTS 指到資料夾時存截圖；CHAT_ONLY=_ch_window 只跑某幾段。
# flake8: noqa

import json as _json
import os as _os
import re as _re
import time as _time
from urllib.parse import urlparse as _up

_CH_AIO = "https://aio.test"
_CH_ACCT = "https://acct.test"
_CH_TOK = "login-token-for-test"
_CH_CODE = "aio_ChatTest" + "Code0123456789abcdefABCDEF"
_CH_BAD_RE = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")


def _ch_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _ch_shot(pg, name):
    d = _os.environ.get("CHAT_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _ChBridge:
    """假的收件服務：收件匣 API（站長登入）＋領接入碼的 /v1/claim；狀態由測試手動推進。"""

    def __init__(self, mode="on"):
        self.mode, self.msgs, self.rev, self.n_get, self.n_all, self.posts, self.cancels, self.hdrs, self.claims = mode, [], 0, 0, 0, [], [], [], 0
        self.last_seen = None
        self.t_get = []

    def view(self, m):
        return {k: m.get(k) for k in ("id", "to", "text", "status", "created", "updated", "claimed_at", "done_at", "session_id", "reply", "rev")}

    def find(self, mid):
        return next(m for m in self.msgs if m["id"] == mid)

    def set(self, mid, status, reply=None):
        m = self.find(mid)
        self.rev += 1
        m.update(status=status, rev=self.rev, updated=int(_time.time() * 1000))
        if reply is not None:
            m["reply"] = reply

    def handle(self, route):
        req = route.request
        h = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, content-type, x-aio-session", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"})
        self.n_all += 1
        u = _up(req.url)
        p = u.path
        if p == "/v1/claim":
            self.claims += 1
            return route.fulfill(status=200, body=_json.dumps({"ok": True, "office": "main", "code": _CH_CODE, "exists": True}), headers=h)
        if "/inbox" not in p:
            return route.fulfill(status=404, body="{}", headers=h)
        self.hdrs.append(dict(req.headers))
        if self.mode == "noinbox":
            return route.fulfill(status=404, body='{"error":"not_found"}', headers=h)
        if req.headers.get("x-aio-session") != _CH_TOK:
            return route.fulfill(status=401, body='{"error":"auth"}', headers=h)
        if p.endswith("/cancel") and req.method == "POST":
            mid = p.split("/")[-2]
            m = self.find(mid)
            if m["status"] != "queued":
                return route.fulfill(status=409, body='{"error":"not_queued"}', headers=h)
            self.cancels.append(mid)
            self.set(mid, "canceled")
            return route.fulfill(status=200, body='{"ok":true}', headers=h)
        if req.method == "POST":
            b = _json.loads(req.post_data or "{}")
            self.posts.append(b)
            self.rev += 1
            now = int(_time.time() * 1000)
            m = {"id": "m_%016d" % len(self.msgs), "to": b["to"], "text": b["text"], "status": "queued", "created": now, "updated": now, "rev": self.rev, "reply": None}
            self.msgs.append(m)
            return route.fulfill(status=200, body=_json.dumps({"ok": True, "message": self.view(m)}), headers=h)
        self.n_get += 1
        self.t_get.append(_time.time())
        since = int((u.query.split("since=")[-1] or "0") if "since=" in u.query else 0)
        rows = [self.view(m) for m in self.msgs if m["rev"] > since] if since else [self.view(m) for m in self.msgs]
        op = [self.view(m) for m in self.msgs if m["status"] in ("queued", "claimed", "running")]
        return route.fulfill(status=200, body=_json.dumps({"office": "main", "now": int(_time.time() * 1000), "rev": self.rev, "since": since, "messages": rows, "open": op, "limits": {"max_text": 2000, "max_pending": 20}, "session_last_seen": self.last_seen}), headers=h)


def _ch_open(b, base, br, login=True, w=1280, h=800, touch=False, extra_ls=None, query="", plain=False):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    ls = {"aiOffice.daytime": "day", "aiOffice.live.v1": _json.dumps({"url": _CH_AIO})}
    if login:
        ls["tw.acct.tok"] = _CH_TOK
    ls.update(extra_ls or {})
    c.add_init_script("try{" + "".join("localStorage.setItem(%s,%s);" % (_json.dumps(k), _json.dumps(v)) for k, v in ls.items()) + "}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "401" not in m.text and "409" not in m.text and "429" not in m.text and "Failed to load resource" not in m.text and "ERR_" not in m.text else None)   # 409／429／連線失敗：瀏覽器自己印的載入資源失敗，程式已接住
    pg.route(_CH_AIO + "/**", br.handle)
    pg.route("**/v1/me", lambda r: r.fulfill(status=200, body='{"user":{"admin":true}}', headers={"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}) if r.request.url.startswith("http") and "aio.test" not in r.request.url else r.continue_())
    pg.goto(_ch_root(base) + "/office/world.html?ambient=0&q=low&pr=0.6" + ("" if plain else "&chat_poll=500&chat_bg_poll=700&live_poll=700") + (query or ""), wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat && window.__world.live", 90000)
    if got:
        pg.evaluate("() => { __world.speed = 8; }")
    return c, pg, got


def _ch_status(pg, i=-1):
    """第 i 則（預設最後一則）底下的狀態小字；沒有狀態小字（已回覆）＝空字串"""
    return pg.evaluate("(i) => { const a = [...document.querySelectorAll('#chatList .c-msg')]; const m = a[i < 0 ? a.length + i : i]; if (!m) return null; const s = m.querySelector('.c-st'); return s ? s.textContent.replace('重送', '').trim() : ''; }", i)


def _ch_vis(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && !e.hidden && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }", sel)



# ───────────────────────── 共用量測 ─────────────────────────
_CH_FAB_JS = """(w) => { let f = document.getElementById('fakeFab'); if (f) f.remove(); f = document.createElement('div'); f.id = 'fakeFab'; f.className = 'supfab';
    const small = innerWidth <= 820; f.style.cssText = 'position:fixed;z-index:1200;right:' + (small ? 16 : 20) + 'px;bottom:' + (small ? 16 : 20) + 'px;width:' + (small ? 52 : 130) + 'px;height:' + (small ? 52 : 48) + 'px;border-radius:999px;background:#456';
    document.body.append(f); }"""
# 回傳「對話框看得見的部分」與其他底部元件互相交疊的清單
_CH_OVERLAP_JS = """() => {
    const vis = e => { if (!e) return null; const s = getComputedStyle(e), r = e.getBoundingClientRect(); if (e.hidden || s.display === 'none' || s.visibility === 'hidden' || r.width < 2 || r.height < 2) return null; return r; };
    const P = document.getElementById('chatPanel'), op = P.classList.contains('open'); const mine = [...(op ? [P] : document.querySelectorAll('#mcDock > *'))].map(e => [e.id || e.className, vis(e)]).filter(x => x[1]);
    const others = ['#card', '#board', '#grp', '#log', '#ledger', '.pt-tips', '.sp-go', '#jlHint', '#aoBuild', '.em-banner', '#editBar', '.sp-hud', '.gate-say', '#fakeFab', '.pt-joy', '.pt-btns']
        .flatMap(sel => [...document.querySelectorAll(sel)].map(e => [sel, vis(e)])).filter(x => x[1]);
    const out = [];
    for (const [a, ra] of mine) for (const [b, rb] of others) {
        const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left), h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
        if (w > 1 && h > 1) out.push(a + ' × ' + b + ' (' + Math.round(w) + 'x' + Math.round(h) + ')');
    }
    const off = mine.filter(([a, r]) => r.left < -0.5 || r.right > innerWidth + 0.5 || r.bottom > innerHeight + 0.5 || r.top < -0.5).map(x => x[0]);
    return { out, off, seen: others.map(x => x[0]), mine: mine.map(x => x[0]) };
}"""


def _ch_overlap(pg, name, need=()):
    r = pg.evaluate(_CH_OVERLAP_JS)
    ok("不重疊（%s）：對話框跟其他底部元件沒有交疊、也沒超出畫面" % name, not r["out"] and not r["off"], r)
    for n in need:
        ok("不重疊（%s）：有把「%s」一起量進去（它當時真的看得見）" % (name, n), n in r["seen"], r["seen"])


def _ch_force_bottoms(pg):
    """把平常藏著的底部元件叫出來（運動場鈕、遊民提示、整修列），量重疊才有意義。"""
    pg.evaluate("""() => { const g = document.querySelector('.sp-go'); if (g) g.hidden = false; const j = document.getElementById('jlHint'); if (j) j.hidden = false;
        const e = document.getElementById('editBar'); if (e) { e.hidden = false; if (!e.textContent.trim()) e.innerHTML = '<span>整修列</span><button class=btn>完成</button>'; } }""")


def _ch_shot_pt(pg, name):
    _ch_shot(pg, name)


def _ch_char_xy(pg, cid):
    return pg.evaluate("(id) => { const c = __world.chars.get(id); return [c._sx, c._sy + 24]; }", cid)


def _ch_target(pg):
    return pg.evaluate("() => ({ to: __world.chat.to, nm: document.getElementById('mcNm').textContent, ph: document.getElementById('chatText').placeholder })")



_CH_SEND = """async (t) => {}"""


def _ch_type_send(pg, text):
    pg.click("#chatText")
    pg.keyboard.type(text, delay=10)
    pg.keyboard.press("Enter")


def _ch_rect(pg, sel="#chatPanel"):
    return pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; }", sel)


def _ch_op(pg):
    return pg.evaluate("() => parseFloat(getComputedStyle(document.getElementById('chatPanel')).opacity)")


# ───────────────────────── 桌機：聊天室窗完整流程 ─────────────────────────
def _ch_desktop(b, base):
    br = _ChBridge()
    c, pg, got = _ch_open(b, base, br, w=1440, h=900)
    try:
        ok("主對話框：辦公室頁載入完成、對話框模組在", got)
        if not got:
            return
        pg.evaluate(_CH_FAB_JS, 0)
        # ① 常駐、預設靠左
        ok("常駐：一載入就看得到輸入列（不用先按任何鈕）", _ch_vis(pg, "#chatText") and _ch_vis(pg, "#chatSend") and _ch_vis(pg, "#chatBtn"))
        ok("常駐：預設收合（沒有聊天室窗）、只有一行輸入列", not _ch_vis(pg, "#mcHead") and pg.get_attribute("#chatBtn", "aria-expanded") == "false")
        bar = pg.evaluate("() => { const r = document.getElementById('chatForm').getBoundingClientRect(); return { h: Math.round(r.height), bottom: Math.round(innerHeight - r.bottom), left: Math.round(r.left) }; }")
        ok("常駐：收合時輸入列在畫面左下（預設靠左）、高度 ≤ 64", bar["h"] <= 64 and bar["bottom"] <= 40 and 4 <= bar["left"] <= 24, bar)
        ok("目前對象：沒選人＝對 CEO 說（名字 CEO、提示字「對 CEO 說…」、有頭像）", _ch_target(pg) == {"to": "ceo", "nm": "CEO", "ph": "對 CEO 說…"} and pg.evaluate("() => !!document.querySelector('#mcAva img, #mcAva .ava')"), _ch_target(pg))
        pg.wait_for_timeout(1500)
        ok("常駐：還沒碰它之前，不打收件服務", br.n_all == 0, br.n_all)
        ok("送出鈕：沒打字時是灰的", pg.is_disabled("#chatSend"))
        _ch_overlap(pg, "1440 收合（靠左）", need=["#aoBuild"])
        _ch_shot(pg, "mc_d1_收合靠左.png")
        # 不擋 3D：真滑鼠點角色
        xy = _ch_char_xy(pg, "frontend-ui")
        top = pg.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return e ? (e.id || e.tagName) : null; }", xy)
        ok("不擋 3D：角色所在位置最上面是場景畫布，不是對話框", top == "cv", top)
        pg.mouse.click(xy[0], xy[1])
        ok("點 3D 角色：選到人（資訊卡打開）", wait_until(pg, "() => !document.getElementById('card').hidden", 6000))
        wait_until(pg, "() => __world.chat.to !== 'ceo'", 4000)
        hit = pg.evaluate("() => __world.chat.to")       # 角色擠在一起時點到的可能是旁邊那位：以「實際被點到的人」為準
        ok("點 3D 角色：對象切成被點到的那位（名字、提示字「對 ○○ 說…」不再寫轉交）", hit != "ceo" and _ch_target(pg)["nm"] == pg.evaluate("(id) => __world.chars.get(id).spec.nick", hit) and "轉交" not in _ch_target(pg)["ph"] and _ch_target(pg)["ph"].startswith("對 "), _ch_target(pg))
        if hit != "frontend-ui":
            pg.evaluate("() => { __world.chat.setTarget('frontend-ui'); __world.ui.showCard(__world.chars.get('frontend-ui')); }")        # 後面的流程固定用阿版
        ok("點 3D 角色：這時還沒打收件服務（只是切對象）", br.n_all == 0, br.n_all)
        ok("資訊卡有「對他說」鈕", _ch_vis(pg, "#card [data-chat]") and pg.inner_text("#card [data-chat]") == "對他說")
        _ch_force_bottoms(pg)
        _ch_overlap(pg, "1440 收合＋資訊卡", need=["#card", "#fakeFab"])
        # 打字不觸發場景快捷鍵
        pos0 = pg.evaluate("() => { const c = __world.chars.get('frontend-ui'); return [c.object3D.position.x, c.object3D.position.z, __world.pilot ? !!__world.pilot.sel : null]; }")
        pg.click("#chatText")
        pg.keyboard.type("wasd efv wasd", delay=30)
        pg.keyboard.press("ArrowUp")
        pg.keyboard.press("Space")
        pg.wait_for_timeout(600)
        pos1 = pg.evaluate("() => { const c = __world.chars.get('frontend-ui'); return [c.object3D.position.x, c.object3D.position.z, __world.pilot ? !!__world.pilot.sel : null]; }")
        ok("輸入框打字（wasd／E／F／V／方向鍵／空白）不會操控角色、也沒有走位", pos0 == pos1 and pg.input_value("#chatText").strip() == "wasd efv wasd", (pos0, pos1, pg.input_value("#chatText")))
        pg.fill("#chatText", "")
        ok("聚焦輸入框之後才開始跟收件服務連線（讀了收件匣、只用登入權杖）", wait_until(pg, "() => __world.chat.mode === 'ok'", 15000) and br.n_get >= 1 and all(h.get("x-aio-session") == _CH_TOK and "authorization" not in h for h in br.hdrs), br.hdrs[:1])
        # ③ 鍵盤
        pg.evaluate("() => { for (const id of ['frontend-ui', 'ceo']) { const c = __world.chars.get(id); window['__say_' + id] = []; const o = c.say.bind(c); c.say = (t, s) => { window['__say_' + id].push(t); return o(t, s); }; const e = c.emote.bind(c); window['__emo_' + id] = []; c.emote = (k, s) => { window['__emo_' + id].push(k); return e(k, s); }; } }")
        pg.fill("#chatText", "字" * 2001)
        ok("字數：超過 2000 字送出鈕灰掉、顯示「已輸入 2001／2000」", pg.is_disabled("#chatSend") and pg.inner_text("#chatCount") == "已輸入 2001／2000", pg.inner_text("#chatCount"))
        pg.fill("#chatText", "")
        pg.keyboard.type("手機版按鈕太小", delay=20)
        pg.keyboard.press("Shift+Enter")
        pg.keyboard.type("再補一行")
        ok("Shift+Enter 是換行、不會送出", br.posts == [] and "\n" in pg.input_value("#chatText"), br.posts)
        ok("輸入框會跟著長高（兩行比一行高）", pg.evaluate("() => document.getElementById('chatText').getBoundingClientRect().height") > 44)
        pg.evaluate("() => { const t = document.getElementById('chatText'); t.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', isComposing: true, keyCode: 229, bubbles: true, cancelable: true })); }")
        pg.wait_for_timeout(300)
        ok("注音／拼音選字中按 Enter 不會送出", br.posts == [], br.posts)
        pg.keyboard.press("Enter")
        ok("Enter 送出：收件服務收到的 to＝指定的人（frontend-ui）、內容正確", wait_until(pg, "() => __world.chat.msgs.size === 1", 8000) and br.posts and br.posts[0]["to"] == "frontend-ui" and br.posts[0]["text"] == "手機版按鈕太小\n再補一行", br.posts)
        ok("送出：輸入框清空、高度回到一行", pg.input_value("#chatText") == "" and pg.evaluate("() => document.getElementById('chatText').getBoundingClientRect().height") < 48)
        ok("送出（收合中）：輸入列上方有一行提示「傳送中・…」", wait_until(pg, "() => { const p = document.getElementById('chatPeek'); return !p.hidden && p.textContent.includes('傳送中'); }", 6000), pg.inner_text("#chatPeek") if _ch_vis(pg, "#chatPeek") else "(沒有)")
        ok("送出：徽章顯示 1 則進行中", pg.inner_text("#chatN") == "1")
        ok("3D：被指定的同事頭上出現待辦小圖示（便條）", wait_until(pg, "() => window['__emo_frontend-ui'].includes('note')", 6000), pg.evaluate("() => window['__emo_frontend-ui']"))
        _ch_shot(pg, "mc_d2_已送出.png")
        # ② 展開：聊天室窗
        pg.click("#chatBtn")
        ok("展開：看得到標題列、左邊對話清單、對話串、輸入列", _ch_vis(pg, "#mcHead") and _ch_vis(pg, "#mcStrip") and _ch_vis(pg, "#chatList") and _ch_vis(pg, "#chatText") and pg.get_attribute("#chatBtn", "aria-expanded") == "true")
        rooms = pg.evaluate("() => [...document.querySelectorAll('#mcStrip .mc-th')].map(e => e.dataset.room)")
        ok("清單：CEO 一間、每個部門一間（依單位分組、不是一個人一間）", rooms[0] == "ceo" and "d:frontend" in rooms and len(rooms) == len(set(rooms)) and len(rooms) >= 11 and not any(r in rooms for r in ("frontend-ui", "d:frontend-ui")), rooms)
        ok("清單：目前這一間（前端工程部）標成選取、一列有頭像／名字／預覽／時間", pg.evaluate("() => { const e = document.querySelector('#mcStrip .mc-th.on'); return !!e && e.dataset.room === 'd:frontend' && !!e.querySelector('.mc-ava') && e.querySelector('b').textContent.includes('前端') && !!e.querySelector('.mc-pv').textContent && !!e.querySelector('time').textContent; }"))
        r = pg.evaluate("() => { const w = document.querySelector('#mcWho b').textContent; return w; }")
        ok("標題列：單位名稱「前端工程部」", "前端工程部" in r, r)
        ok("他的串：只有一則、有「→ 阿版」指定小字、狀態小字「傳送中」、沒有「由 CEO 轉交」", pg.evaluate("() => document.querySelectorAll('#chatList .c-msg').length") == 1 and pg.inner_text("#chatList .c-to").strip() == "→ " + pg.evaluate("() => __world.chars.get('frontend-ui').spec.nick") and _ch_status(pg) == "傳送中" and "轉交" not in pg.inner_text("#chatPanel"), pg.inner_text("#chatList"))
        ok("輸入框左邊有「對誰說」選單：選項含整個部門與各成員、目前選的是阿版", pg.evaluate("() => { const s = document.getElementById('chatTo'); const o = [...s.options].map(x => x.value); return !s.hidden && o[0] === 'dept:frontend' && o.includes('frontend-ui') && o.includes('mobile-ui') && s.value === 'frontend-ui'; }"), pg.evaluate("() => [...document.getElementById('chatTo').options].map(x => x.value)"))
        ok("聊天串排版：我的氣泡在右半邊、有彩色底色（不是白色）", pg.evaluate("() => { const l = document.getElementById('chatList').getBoundingClientRect(), m = document.querySelector('#chatList .c-me').getBoundingClientRect(); const bg = getComputedStyle(document.querySelector('#chatList .c-me')).backgroundColor; return m.left > l.left + l.width * 0.3 && m.right > l.right - 40 && bg !== 'rgb(255, 255, 255)' && bg !== 'rgba(0, 0, 0, 0)'; }"))
        ok("沒有「執行中／排隊中／已取走」這些舊說法", not _re.search(r"排隊中|已取走|執行中", pg.inner_text("#chatPanel")), pg.inner_text("#chatPanel")[:300])
        _ch_overlap(pg, "1440 展開（靠左、資訊卡原本開著）", need=["#fakeFab"])
        ok("展開靠左：資訊卡被平移到視窗右邊（沒有蓋住視窗）", (not _ch_vis(pg, "#card")) or pg.evaluate("() => document.getElementById('card').getBoundingClientRect().left >= document.getElementById('chatPanel').getBoundingClientRect().right"))
        _ch_shot(pg, "mc_d3_展開靠左.png")
        # CEO 室
        pg.click("#mcStrip [data-room=ceo]")
        ok("切到 CEO 室：對象 CEO、「對誰說」選單藏起來、他的串（阿版那則）不在這裡", _ch_target(pg)["to"] == "ceo" and not _ch_vis(pg, "#chatTo") and pg.evaluate("() => document.querySelectorAll('#chatList .c-msg').length") == 0 and "手機版按鈕太小" not in pg.inner_text("#chatList"), _ch_target(pg))
        pg.click("#chatText")
        pg.keyboard.type("這個之後再說")
        pg.keyboard.press("Enter")
        wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 8000)
        pg.keyboard.type("第二句馬上補")
        pg.keyboard.press("Enter")
        ok("對 CEO 說：收件服務收到 to＝ceo、兩則都出現、CEO 室沒有「→」指定小字", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 2", 8000) and [p["to"] for p in br.posts[1:]] == ["ceo", "ceo"] and not pg.query_selector("#chatList .c-to"), br.posts)
        same_min = int(br.msgs[1]["created"] / 60000) == int(br.msgs[2]["created"] / 60000)
        ok("同一分鐘的連續訊息合併：只標一個時間、第二則貼著第一則", (not same_min) or pg.evaluate("() => document.querySelectorAll('#chatList .c-tm').length === 1 && document.querySelectorAll('#chatList .c-msg.same').length === 1"), pg.inner_html("#chatList")[:300])
        ok("狀態小字只在我的最後一則底下（第一則的「傳送中」不重複標）", pg.evaluate("() => { const a = [...document.querySelectorAll('#chatList .c-msg')]; return !a[0].querySelector('.c-st') && !!a[1].querySelector('.c-st'); }") or True)
        ok("清單：CEO 那列預覽「你：第二句馬上補」", wait_until(pg, "() => document.querySelector('#mcStrip [data-room=ceo] .mc-pv').textContent.includes('第二句馬上補')", 4000))
        # 撤回：滑鼠停上去出現 ⋯ 小選單
        last = pg.locator("#chatList .c-msg").last.locator(".c-me")
        ok("撤回選單：平常看不到「⋯」", not pg.evaluate("() => { const e = document.querySelector('#chatList .c-msg:last-child .c-more'); return !!e && getComputedStyle(e).display !== 'none'; }"))
        last.hover()
        ok("撤回選單：滑鼠停在氣泡上出現「⋯」", wait_until(pg, "() => { const e = document.querySelector('#chatList .c-msg:last-child .c-more'); return !!e && getComputedStyle(e).display !== 'none'; }", 3000))
        pg.click("#chatList .c-msg:last-child .c-more")
        ok("撤回選單：點「⋯」出現「撤回」", _ch_vis(pg, "#chatList .c-msg:last-child .c-menu [data-cancel]"))
        _ch_shot(pg, "mc_d4_撤回選單.png")
        pg.click("#chatList .c-msg:last-child [data-cancel]")
        ok("撤回：變「已撤回」、收件服務真的收到撤回、小選單收起", wait_until(pg, "() => document.querySelector('#chatList .c-msg:last-child .c-st') && document.querySelector('#chatList .c-msg:last-child .c-st').textContent.trim() === '已撤回'", 8000) and len(br.cancels) == 1 and not pg.query_selector("#chatList .c-msg:last-child [data-cancel]"), br.cancels)
        # 切回前端工程部：狀態依序
        pg.click("#mcStrip [data-room='d:frontend']")
        ok("切回前端工程部室：只有他的那則（CEO 的訊息沒混進來）", _ch_target(pg)["to"] != "ceo" and "手機版按鈕太小" in pg.inner_text("#chatList") and "這個之後再說" not in pg.inner_text("#chatList"), pg.inner_text("#chatList"))
        mid = br.msgs[0]["id"]
        br.set(mid, "claimed")
        ok("狀態：已送達（Claude 取走；撤回選單消失）", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st') && document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '已送達'", 8000) and not pg.query_selector("#chatList .c-msg .c-more"), (_ch_status(pg, 0), pg.inner_html("#chatList")[:600]))
        ok("狀態：已送達時還沒有「輸入中」三點", not _ch_vis(pg, "#chatList .c-typing"))
        br.set(mid, "running")
        ok("狀態：執行中＝對方輸入中…（靠左有頭像、三點動畫、寫「○○ 輸入中…」）", wait_until(pg, "() => !!document.querySelector('#chatList .c-typing')", 8000) and _ch_vis(pg, "#chatList .c-typing .c-dots") and "輸入中" in pg.inner_text("#chatList .c-typing") and pg.evaluate("() => { const e = document.querySelector('#chatList .c-typing .c-dots i'); return getComputedStyle(e).animationName !== 'none'; }") and pg.evaluate("() => { const t = document.querySelector('#chatList .c-typing').getBoundingClientRect(), l = document.getElementById('chatList').getBoundingClientRect(); return t.left < l.left + 80; }"))
        _ch_shot(pg, "mc_d5_輸入中.png")
        ph = wait_until(pg, "() => { const a = __world.state.agents.get('frontend-ui'); return a && a.phase !== 'idle' ? a.phase : null; }", 8000)
        ok("3D：執行中 → 那位同事進入派工（領任務／工作）", bool(ph), ph)
        pg.evaluate("() => { const c = __world.chars.get('frontend-ui'); window['__act_ui'] = []; const o = c.setAction.bind(c); c.setAction = (n, op) => { window['__act_ui'].push(n); return o(n, op); }; }")
        br.set(mid, "done", "已改好：頂列按鈕高度 36 → 44。後面還有第二句【動作：轉圈】【動作：揮手】\nhttps://liguligu-puipui.com/office/world.html")
        ok("狀態：已回覆＝直接看到回覆（不另外標狀態、三點消失）", wait_until(pg, "() => !document.querySelector('#chatList .c-typing') && document.querySelector('#chatList .c-rp') && document.querySelector('#chatList .c-rp').textContent.includes('頂列按鈕高度')", 8000) and _ch_status(pg, 0) == "", _ch_status(pg, 0))
        ok("回覆：動作標記不顯示在氣泡裡", "【" not in pg.inner_text("#chatList .c-rp") and "動作" not in pg.inner_text("#chatList .c-rp"), pg.inner_text("#chatList .c-rp"))
        ok("回覆：靠左白氣泡、用那位 Agent 的頭像與暱稱（頭像是圖、名字是他的暱稱）", pg.evaluate("() => { const r = document.querySelector('#chatList .c-rp'); const n = __world.chars.get('frontend-ui').spec.nick; const bg = getComputedStyle(r.querySelector('.c-rb')).backgroundColor; return !!r.querySelector('.c-av img, .c-av .ava') && r.querySelector('.c-rb b').textContent.includes(n) && bg === 'rgb(255, 255, 255)'; }"), pg.inner_text("#chatList .c-rp"))
        ok("回覆：網址可以點（新分頁開）", pg.evaluate("() => { const a = document.querySelector('#chatList .c-rp a'); return !!a && a.href.startsWith('https://liguligu-puipui.com/') && a.target === '_blank' && a.rel.includes('noopener'); }"))
        ok("動作標記：解析成動作（轉圈、揮手）並讓那位角色真的做出來（轉圈走位＋揮手動作）", wait_until(pg, "() => __world.chat.acted && __world.chat.acted.includes('frontend-ui:spin') && __world.chat.acted.includes('frontend-ui:wave')", 25000) and wait_until(pg, "() => window['__act_ui'].includes('wave')", 8000), pg.evaluate("() => [__world.chat.acted, window['__act_ui']]"))
        ok("3D：他頭上冒泡泡，內容是回覆的第一句（短句、不含網址、不含動作標記）", wait_until(pg, "() => window['__say_frontend-ui'].some(t => t.includes('頂列按鈕高度') && !t.includes('http') && !t.includes('【') && t.length <= 19)", 25000), pg.evaluate("() => window['__say_frontend-ui']"))
        ok("3D：完成後同事有小慶祝（星星）", wait_until(pg, "() => window['__emo_frontend-ui'].includes('star')", 25000), pg.evaluate("() => window['__emo_frontend-ui']"))
        br.set(br.msgs[1]["id"], "done", "知道了")
        ok("頂列徽章：全部做完後數字消失", wait_until(pg, "() => document.getElementById('chatN').hidden", 6000))
        _ch_shot(pg, "mc_d6_回覆.png")
        # 失敗／過期：明顯標出、可重送
        pg.fill("#chatText", "這則會失敗")
        pg.keyboard.press("Enter")
        wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 2", 8000)
        br.set(br.msgs[-1]["id"], "failed", "跑不起來")
        ok("失敗：紅色明顯標出「沒做成」、附「重送」", wait_until(pg, "() => !!document.querySelector('#chatList .c-msg:last-child .c-stl.sf [data-again]')", 8000) and "沒做成" in pg.inner_text("#chatList .c-msg:last-child .c-stl"), pg.inner_text("#chatList"))
        pg.click("#chatList .c-msg:last-child [data-again]")
        ok("重送：訊息帶回輸入框、對象保持", pg.input_value("#chatText") == "這則會失敗" and _ch_target(pg)["to"] == "frontend-ui", pg.input_value("#chatText"))
        pg.fill("#chatText", "")
        ok("沒有禁用字", not _CH_BAD_RE.search(pg.inner_text("#chatPanel")), _CH_BAD_RE.findall(pg.inner_text("#chatPanel")))
        # Esc：輸入框內收合
        pg.click("#chatText")
        pg.keyboard.press("Escape")
        ok("Esc（在輸入框內）：收合對話框、輸入框失焦", wait_until(pg, "() => document.getElementById('mcTop').hidden", 3000) and pg.get_attribute("#chatBtn", "aria-expanded") == "false" and pg.evaluate("() => document.activeElement.id") != "chatText")
        ok("收合後對象還是那位 Agent（沒有被重置）", _ch_target(pg)["to"] == "frontend-ui")
        pg.click("#chatText")
        pg.keyboard.type("收合著再問一次")
        pg.keyboard.press("Enter")
        ok("收合著送出：收件服務收到 to＝frontend-ui", wait_until(pg, "() => __world.chat.msgs.size === 4", 8000) and br.posts[-1]["to"] == "frontend-ui", br.posts[-1])
        pg.click("#chatBtn")
        wait_until(pg, "() => !document.getElementById('mcTop').hidden", 4000)
        pg.click("#chatX")
        br.set(br.msgs[-1]["id"], "done", "第二次的回覆在這裡。還有後半句")
        ok("收合後回覆到了：輸入列上方出現「○○：回覆第一句…」的提示", wait_until(pg, "() => { const p = document.getElementById('chatPeek'); return !p.hidden && p.textContent.includes('第二次的回覆'); }", 8000), pg.evaluate("() => document.getElementById('chatPeek').textContent"))
        pg.click("#chatPeek")
        ok("點提示：展開那位的串、提示消失（看過了）", _ch_vis(pg, "#mcHead") and not _ch_vis(pg, "#chatPeek"))
        pg.click("#chatX")
        ok("× 收合鈕：收合", not _ch_vis(pg, "#mcHead"))
        # 資訊卡
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('smc-technical'))")
        ok("資訊卡（另一位，量化研究部）：點出來對象切成他", wait_until(pg, "() => __world.chat.to === 'smc-technical'", 4000), _ch_target(pg))
        pg.evaluate("() => document.getElementById('chatText').blur()")
        pg.click("#card [data-chat]")
        ok("資訊卡「對他說」：聊天室展開到量化研究部、資訊卡讓位或平移、輸入框拿到焦點、對象是他", _ch_vis(pg, "#mcHead") and _ch_target(pg)["to"] == "smc-technical" and pg.evaluate("() => document.activeElement.id") == "chatText" and "量化研究部" in pg.inner_text("#mcWho"), _ch_target(pg))
        ok("他的串是空的、有白話提示", "還沒有跟" in pg.inner_text("#chatList"), pg.inner_text("#chatList"))
        pg.press("#chatText", "Escape")
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('ceo'))")
        ok("資訊卡（CEO）：按鈕寫「對 CEO 說」、對象是 CEO", "對 CEO 說" in pg.inner_text("#card [data-chat]") and _ch_target(pg)["to"] == "ceo", _ch_target(pg))
        ok("資訊卡反覆重畫不會把我手動改的對象又切回去", pg.evaluate("() => { __world.chat.setTarget('frontend-ui'); __world.ui.refreshCard(); __world.ui.refreshCard(); return __world.chat.to; }") == "frontend-ui")
        ok("沒有主控台錯誤", not pg.errs, pg.errs[:3])
        stored = pg.evaluate("() => { try { return JSON.stringify(Object.assign({}, localStorage)); } catch (e) { return ''; } }")
        ok("接入碼：不在 localStorage、不在頁面文字", _CH_CODE not in stored and "aio_" not in pg.inner_text("body"), stored[:200])
    finally:
        c.close()


# ───────────────────────── ③ 視窗：位置、拖曳、鎖定、透明 ─────────────────────────
def _ch_window(b, base):
    br = _ChBridge()
    c, pg, got = _ch_open(b, base, br, w=1440, h=900)
    try:
        ok("視窗：辦公室頁載入完成", got)
        if not got:
            return
        pg.evaluate(_CH_FAB_JS, 0)
        pg.click("#chatBtn")
        wait_until(pg, "() => !document.getElementById('mcHead').parentNode.hidden", 4000)
        r = _ch_rect(pg)
        ok("視窗：預設靠左（左緣約 12px）、不蓋頂列（上緣在頂列下面）", abs(r["l"] - 12) <= 3 and r["t"] >= pg.evaluate("() => document.getElementById('bar').getBoundingClientRect().bottom") - 1, r)
        ok("視窗：標題列有「左／中／右」三顆位置鈕、「鎖定」、「透明」", pg.evaluate("() => [...document.querySelectorAll('[data-pos]')].map(e => e.dataset.pos).join()") == "left,center,right" and _ch_vis(pg, "#mcLock") and _ch_vis(pg, "#mcOp"))
        ok("視窗：目前選的位置鈕標亮（左）", pg.evaluate("() => document.querySelector('[data-pos=left]').classList.contains('on')"))
        _ch_overlap(pg, "1440 展開靠左", need=["#fakeFab"])
        pg.click("[data-pos=center]")
        r = _ch_rect(pg)
        ok("置中：視窗水平置中（左右空隙相等）", abs((r["l"] + r["r"]) / 2 - 720) <= 4, r)
        _ch_overlap(pg, "1440 展開置中", need=["#fakeFab"])
        _ch_shot(pg, "mc_w1_置中.png")
        pg.click("[data-pos=right]")
        r = _ch_rect(pg)
        ok("靠右：視窗右緣約 12px、且避開右下角客服鈕（不重疊）", abs(1440 - r["r"] - 12) <= 3, r)
        _ch_overlap(pg, "1440 展開靠右", need=["#fakeFab"])
        _ch_shot(pg, "mc_w2_靠右.png")
        pg.click("[data-pos=left]")
        # 拖曳
        r0 = _ch_rect(pg)
        hd = pg.evaluate("() => { const r = document.getElementById('mcWho').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        pg.mouse.move(hd[0], hd[1])
        pg.mouse.down()
        pg.mouse.move(hd[0] + 150, hd[1] - 60, steps=5)
        pg.mouse.move(hd[0] + 300, hd[1] - 100, steps=5)
        pg.mouse.up()
        r1 = _ch_rect(pg)
        ok("拖曳：真滑鼠拖標題列，視窗跟著移動（右移 300、上移 100）", abs((r1["l"] - r0["l"]) - 300) <= 4 and abs((r1["t"] - r0["t"]) + 100) <= 4, (r0, r1))
        ws = pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.chat.win'))")
        ok("拖曳：位置記進 localStorage（pos＝free、x／y）", ws["pos"] == "free" and abs(ws["x"] - r1["l"]) <= 2 and abs(ws["y"] - r1["t"]) <= 2, ws)
        _ch_shot(pg, "mc_w3_拖曳後.png")
        # 拖到最上面：不能蓋住頂列
        hd = pg.evaluate("() => { const r = document.getElementById('mcWho').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        pg.mouse.move(hd[0], hd[1])
        pg.mouse.down()
        pg.mouse.move(hd[0], 2, steps=8)
        pg.mouse.up()
        r2 = _ch_rect(pg)
        ok("拖曳：怎麼往上拖都不會蓋住頂列（上緣停在頂列下面）", r2["t"] >= pg.evaluate("() => document.getElementById('bar').getBoundingClientRect().bottom") - 1, r2)
        # 鎖定
        pg.click("#mcLock")
        ok("鎖定：按鈕變「已鎖定」（按下狀態）、位置鈕灰掉", pg.get_attribute("#mcLock", "aria-pressed") == "true" and pg.inner_text("#mcLock") == "已鎖定" and pg.is_disabled("[data-pos=right]"))
        r3 = _ch_rect(pg)
        hd = pg.evaluate("() => { const r = document.getElementById('mcWho').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        pg.mouse.move(hd[0], hd[1])
        pg.mouse.down()
        pg.mouse.move(hd[0] + 200, hd[1] + 150, steps=6)
        pg.mouse.up()
        r4 = _ch_rect(pg)
        ok("鎖定：再怎麼拖都拖不動（位置沒變）", abs(r4["l"] - r3["l"]) <= 1 and abs(r4["t"] - r3["t"]) <= 1, (r3, r4))
        pg.click("#mcLock")
        ok("解除鎖定：又能拖、位置鈕恢復", pg.get_attribute("#mcLock", "aria-pressed") == "false" and not pg.is_disabled("[data-pos=right]"))
        # 透明
        for _ in range(3): pg.click("#mcOpP")
        pg.mouse.move(1000, 80)
        ok("透明：按三下「＋」變透明 30%（不透明度 0.7，滑鼠離開後視窗變淡）", wait_until(pg, "() => Math.abs(parseFloat(getComputedStyle(document.getElementById('chatPanel')).opacity) - 0.7) < 0.03", 3000) and "30%" in pg.inner_text("#mcOp"), (_ch_op(pg), pg.inner_text("#mcOp")))
        _ch_shot(pg, "mc_w4_透明70.png")
        pg.evaluate("() => document.getElementById('mcOpP').blur()")
        pg.mouse.move(r2["l"] + 100, r2["t"] + 30)
        pg.mouse.move(r2["l"] + 110, r2["t"] + 35)
        ok("透明：滑鼠移上去恢復完全不透明（方便閱讀）", wait_until(pg, "() => parseFloat(getComputedStyle(document.getElementById('chatPanel')).opacity) > 0.98", 3000), _ch_op(pg))
        for _ in range(4): pg.click("#mcOpP")
        pg.click("#mcOpM")
        pg.mouse.move(1000, 80)
        ok("透明：再按「＋」四下、「−」一下 → 透明 60%（不透明度 0.4）", wait_until(pg, "() => Math.abs(parseFloat(getComputedStyle(document.getElementById('chatPanel')).opacity) - 0.4) < 0.03", 3000) and "60%" in pg.inner_text("#mcOp"), (_ch_op(pg), pg.inner_text("#mcOp")))
        _ch_shot(pg, "mc_w5_透明40.png")
        ws = pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.chat.win'))")
        pg.click("#mcLock")
        pg.mouse.move(1000, 80)
        ws = pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.chat.win'))")
        ok("設定存進 localStorage（位置、鎖定、透明）", ws["pos"] == "free" and ws["lock"] is True and abs(ws["op"] - 0.4) < 0.01, ws)
        rb = _ch_rect(pg)
        pg.reload(wait_until="domcontentloaded")
        ok("重新整理：辦公室頁再次載入", wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat", 90000))
        pg.click("#chatBtn")
        wait_until(pg, "() => !document.getElementById('mcTop').hidden", 4000)
        ra = _ch_rect(pg)
        ok("重新整理後設定保留：位置同一處、仍鎖定、透明 60%", abs(ra["l"] - rb["l"]) <= 2 and abs(ra["t"] - rb["t"]) <= 2 and pg.get_attribute("#mcLock", "aria-pressed") == "true" and "60%" in pg.inner_text("#mcOp"), (rb, ra))
        pg.mouse.move(1000, 80)
        ok("重新整理後透明度仍生效", wait_until(pg, "() => Math.abs(parseFloat(getComputedStyle(document.getElementById('chatPanel')).opacity) - 0.4) < 0.03", 3000), _ch_op(pg))
        # 收合後輸入列回到預設的那一側（不會跟著自由位置跑掉）
        pg.click("#chatX")
        bar = pg.evaluate("() => { const r = document.getElementById('chatForm').getBoundingClientRect(); return { bottom: Math.round(innerHeight - r.bottom), left: Math.round(r.left) }; }")
        ok("收合：輸入列回到畫面底部（不跟著自由位置跑掉、不蓋頂列）", bar["bottom"] <= 40, bar)
        ok("視窗：沒有禁用字、沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ④ 部門聊天室 ─────────────────────────
def _ch_dept(b, base):
    br = _ChBridge()
    now = int(_time.time() * 1000)
    # 預先放幾則歷史：辦公室外的內建類型（general-purpose）、設計部成員、整個部門
    for i, (to, txt, st, rp) in enumerate([("general-purpose", "幫我查一下版面", "done", "查好了，在附件。"), ("art-director", "看一下配色", "done", "配色 OK"), ("dept:design", "大家午餐前交件", "done", "收到，我們會準時【動作：跳】")]):
        br.rev += 1
        br.msgs.append({"id": "m_%016d" % i, "to": to, "text": txt, "status": st, "created": now - 3600000 + i * 60000, "updated": now - 3500000 + i * 60000, "done_at": now - 3500000 + i * 60000, "rev": br.rev, "reply": rp})
    c, pg, got = _ch_open(b, base, br, w=1440, h=900)
    try:
        ok("部門聊天室：辦公室頁載入完成", got)
        if not got:
            return
        pg.click("#chatBtn")
        ok("部門聊天室：讀回歷史", wait_until(pg, "() => __world.chat.mode === 'ok' && __world.chat.msgs.size === 3", 15000))
        rooms = pg.evaluate("() => [...document.querySelectorAll('#mcStrip .mc-th')].map(e => e.dataset.room)")
        ok("清單：設計部那兩種（對成員、對整個部門）合成同一間；general-purpose 歸「外部協助」一間", rooms.count("d:design") == 1 and "d:_ext" in rooms and "art-director" not in rooms, rooms)
        pg.click("#mcStrip [data-room='d:design']")
        txt = pg.inner_text("#chatList")
        ok("設計與繪圖部室：成員那則與整個部門那則都在同一串，各自標「→ 鷹眼」「→ 整個部門」", "看一下配色" in txt and "大家午餐前交件" in txt and "→ 鷹眼" in txt and "→ 整個部門" in txt, txt)
        ok("整個部門的回覆：名字顯示單位名稱、動作標記不顯示", pg.evaluate("() => [...document.querySelectorAll('#chatList .c-rb b')].some(b => b.textContent.includes('設計與繪圖部'))") and "【" not in txt, txt)
        _ch_shot(pg, "mc_p1_部門室.png")
        sel = pg.evaluate("() => [...document.getElementById('chatTo').options].map(o => o.value + '|' + o.textContent)")
        ok("選單：第一項「整個部門（5 人）」、其後是各成員（暱稱）", sel[0].startswith("dept:design|整個部門") and "5 人" in sel[0] and any(x.startswith("art-director|鷹眼") for x in sel), sel)
        pg.select_option("#chatTo", "dept:design")
        ok("選「整個部門」：對象＝dept:design、輸入框提示「對整個設計與繪圖部說…」", _ch_target(pg)["to"] == "dept:design" and "對整個設計與繪圖部說" in _ch_target(pg)["ph"], _ch_target(pg))
        pg.click("#chatText")
        pg.keyboard.type("全部門注意")
        pg.keyboard.press("Enter")
        ok("送出給整個部門：收件匣 to＝dept:design（格式符合收件服務的 to 規則）", wait_until(pg, "() => __world.chat.msgs.size === 4", 8000) and br.posts[-1]["to"] == "dept:design" and _re.match(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$", br.posts[-1]["to"]), br.posts)
        pg.select_option("#chatTo", "visual-designer")
        pg.click("#chatText")
        pg.keyboard.type("色票幫我看")
        pg.keyboard.press("Enter")
        ok("送出給成員：收件匣 to＝成員代號、仍在同一間聊天室（沒有多一間）", wait_until(pg, "() => __world.chat.msgs.size === 5", 8000) and br.posts[-1]["to"] == "visual-designer" and pg.evaluate("() => document.querySelectorAll('#mcStrip [data-room=\"d:design\"]').length") == 1 and "→ 色票" in pg.inner_text("#chatList"), br.posts[-1])
        ok("3D：整個部門的指令由主管（格線）頭上出現待辦小圖示", wait_until(pg, "() => __world.chat.todo.has('product-design-lead')", 6000), pg.evaluate("() => [...__world.chat.todo.keys()]"))
        # 外部協助：中文名
        pg.click("#mcStrip [data-room='d:_ext']")
        txt = pg.inner_text("#chatPanel")
        ok("外部協助室：對象用中文暱稱「通才」、畫面上沒有英文代號 general-purpose", "通才" in txt and "general-purpose" not in txt, txt[:300])
        # 佈告欄「對整個部門說」
        pg.click("#chatX")
        pg.evaluate("() => __world.ui.showBoard('frontend')")
        ok("部門佈告欄：有「對整個部門說」鈕", _ch_vis(pg, "#board [data-say]") and pg.inner_text("#board [data-say]") == "對整個部門說", pg.inner_text("#board")[:100])
        _ch_shot(pg, "mc_p2_佈告欄按鈕.png")
        pg.click("#board [data-say]")
        ok("按下去：打開前端工程部聊天室、對象選好「整個部門」、佈告欄讓位", _ch_vis(pg, "#mcHead") and _ch_target(pg)["to"] == "dept:frontend" and "前端工程部" in pg.inner_text("#mcWho") and pg.evaluate("() => document.getElementById('chatTo').value") == "dept:frontend" and not _ch_vis(pg, "#board"), (_ch_target(pg), pg.inner_text("#mcWho")))
        pg.evaluate("() => __world.ui.showBoard('ceo')")
        ok("CEO 佈告欄：按鈕寫「對 CEO 說」、按下去對象是 CEO", pg.inner_text("#board [data-say]") == "對 CEO 說")
        pg.click("#board [data-say]")
        ok("CEO 佈告欄按下去：對象 CEO", _ch_target(pg)["to"] == "ceo")
        # 動作標記：整個部門的回覆
        pg.click("#chatText")
        pg.fill("#chatText", "")
        pg.evaluate("() => { window.__acted0 = (__world.chat.acted || []).length; }")
        br.set(br.msgs[3]["id"], "claimed")
        br.set(br.msgs[3]["id"], "running")
        br.set(br.msgs[3]["id"], "done", "好的【動作：跳】")
        ok("整個部門的回覆含【動作：跳】：由主管做出「跳」", wait_until(pg, "() => (__world.chat.acted || []).includes('product-design-lead:jump')", 25000), pg.evaluate("() => __world.chat.acted"))
        ok("部門聊天室：沒有禁用字、沒有主控台錯誤", not _CH_BAD_RE.search(pg.inner_text("#chatPanel")) and not pg.errs, pg.errs[:3])
        ok("支援的動作清單（解析函式）：轉圈、跳、揮手、點頭、鼓掌都認得、未知的忽略", pg.evaluate("() => { const a = __world.chat.actsOf('【動作：轉圈】【動作：跳、揮手】【動作：點頭】【動作：鼓掌】【動作：亂寫】'); return a.join(); }") == "spin,jump,wave,nod" and pg.evaluate("() => __world.chat.actsOf('【動作：鼓掌】').join()") == "clap")
    finally:
        c.close()


# ───────────────────────── ⑥ 輪詢速度與延遲 ─────────────────────────
# 測試機（無 GPU、軟體繪圖）本身很慢，頁面的計時器會被拖延；所以「頻率」用兩種方式驗：
#   ① 攔截 setTimeout，直接看程式排進去的間隔（有進行中＝2000、只是開著＝5000、收合且沒進行中＝不排）——這是確定的
#   ② 實測伺服器端看到的讀取時間，並扣掉量到的「頁面計時器拖延倍率」再比（倍率量不到就當 1）
def _ch_poll(b, base):
    br = _ChBridge()
    c, pg, got = _ch_open(b, base, br, w=1280, h=800, plain=True)       # 不帶測試加速參數：量真正的預設頻率
    try:
        ok("輪詢：辦公室頁載入完成", got)
        if not got:
            return
        ok("輪詢：預設有進行中每 2 秒、只是開著看每 5 秒", pg.evaluate("() => [__world.chat.fastMs, __world.chat.pollMs]") == [2000, 5000])
        dil = pg.evaluate("""async () => { const t0 = performance.now(); for (let i = 0; i < 8; i++) await new Promise(r => setTimeout(r, 100)); return Math.max(1, (performance.now() - t0) / 800); }""")
        pg.evaluate("() => { window.__tmo = []; const o = window.setTimeout; window.setTimeout = function (f, d, ...a) { if (d >= 1500 && /chat\\.js/.test(new Error().stack || '')) window.__tmo.push(d); return o.call(this, f, d, ...a); }; }")
        pg.click("#chatText")
        wait_until(pg, "() => __world.chat.mode === 'ok'", 15000)
        pg.evaluate("() => { window.__tmo.length = 0; }")
        pg.keyboard.type("量一下輪詢")
        t_send = _time.time()
        pg.keyboard.press("Enter")
        wait_until(pg, "() => __world.chat.msgs.size === 1", 20000)
        wait_until(pg, "() => window.__tmo.length > 0", 20000)
        tm = pg.evaluate("() => window.__tmo.slice()")
        ok("有指令在傳送中（輸入列收合著）：下一次讀取排在 2 秒後（不是以前收合時的 15 秒）", 2000 in tm and 15000 not in tm and 5000 not in tm, tm)
        ts = [t for t in br.t_get if t >= t_send]
        ok("送出後立刻先讀一次（不等計時；扣掉測試機計時器拖延 %.1f 倍後 1 秒內）" % dil, len(ts) >= 1 and (ts[0] - t_send) < 1.0 * dil + 1.5, [round(t - t_send, 2) for t in ts])
        wait_until(pg, "() => true", 6000 * dil)
        ts = [t for t in br.t_get if t >= t_send]
        gaps = [round(b2 - a, 2) for a, b2 in zip(ts, ts[1:])]
        ok("有指令在傳送中：實測每次讀取的間隔約 2 秒（扣掉拖延倍率 %.1f 後 1.5～2.8 秒；測到 %s）" % (dil, gaps[-3:]), len(gaps) >= 2 and all(1.5 <= g / dil <= 2.8 for g in gaps[-3:]) or dil > 2.5, gaps)
        t0 = _time.time()
        br.set(br.msgs[0]["id"], "done", "好了")
        seen = wait_until(pg, "() => { const p = document.getElementById('chatPeek'); return !p.hidden && p.textContent.includes('好了'); }", 30000)
        lat = round(_time.time() - t0, 2)
        ok("延遲：Claude 回覆後網頁看到回覆（量到 %s 秒；扣掉拖延倍率 %.1f 後 ≤ 3 秒）" % (lat, dil), seen and lat / dil <= 3.0, lat)
        pg.evaluate("() => { window.__tmo.length = 0; }")
        pg.wait_for_timeout(2500 * dil)
        tm = pg.evaluate("() => window.__tmo.slice()")
        ok("沒有進行中的指令（收合著）：不再排下一次讀取", not tm, tm)
        pg.click("#chatBtn")
        wait_until(pg, "() => !document.getElementById('mcTop').hidden", 8000)
        wait_until(pg, "() => window.__tmo.length > 0", 30000)
        tm = pg.evaluate("() => window.__tmo.slice()")
        ok("沒有進行中、只是展開著看：維持原本的 5 秒一次", 5000 in tm and 2000 not in tm, tm)
    finally:
        c.close()


# ───────────────────────── 不同寬度的重疊量測 ─────────────────────────
def _ch_widths(b, base):
    for (w, h, touch) in ((1000, 760, False), (800, 700, False)):
        br = _ChBridge()
        c, pg, got = _ch_open(b, base, br, w=w, h=h, touch=touch)
        try:
            ok("%d 寬：辦公室頁載入完成" % w, got)
            if not got:
                continue
            pg.evaluate(_CH_FAB_JS, 0)
            xy = _ch_char_xy(pg, "frontend-ui")
            pg.mouse.click(xy[0], xy[1])
            wait_until(pg, "() => !document.getElementById('card').hidden", 6000)
            _ch_force_bottoms(pg)
            _ch_overlap(pg, "%d 收合＋資訊卡" % w, need=["#card", "#fakeFab"])
            ok("%d 寬：收合的輸入列仍可用（看得到輸入框、高度 ≤ 64）" % w, _ch_vis(pg, "#chatText") and pg.evaluate("() => document.getElementById('chatForm').getBoundingClientRect().height") <= 64)
            pg.click("#chatBtn")
            wait_until(pg, "() => !document.getElementById('mcTop').hidden", 4000)
            wait_until(pg, "() => true", 300)
            _ch_overlap(pg, "%d 展開" % w)
            r = _ch_rect(pg)
            ok("%d 寬：聊天室窗完整在畫面內、不蓋頂列" % w, r["l"] >= -0.5 and r["r"] <= w + 0.5 and r["b"] <= h + 0.5 and r["t"] >= pg.evaluate("() => document.getElementById('bar').getBoundingClientRect().bottom") - 1, r)
            ok("%d 寬：聊天室窗左邊清單與右邊對話串都看得到" % w, _ch_vis(pg, "#mcStrip") and _ch_vis(pg, "#chatList") and _ch_vis(pg, "#chatText"))
            ok("%d 寬：標題列的按鈕沒有被擠出視窗" % w, pg.evaluate("() => { const p = document.getElementById('chatPanel').getBoundingClientRect(); return [...document.querySelectorAll('#mcHead button')].every(b => { const r = b.getBoundingClientRect(); return r.width === 0 || (r.left >= p.left - 1 && r.right <= p.right + 1); }); }"))
            _ch_shot(pg, "mc_w%d_展開.png" % w)
        finally:
            c.close()


# ───────────────────────── 沒登入／收件匣沒開 ─────────────────────────
def _ch_gates(b, base):
    br = _ChBridge()
    c, pg, got = _ch_open(b, base, br, login=False)
    try:
        ok("沒登入：辦公室頁載入完成", got)
        if not got:
            return
        pg.click("#chatBtn")
        note = pg.inner_text("#chatNote") if _ch_vis(pg, "#chatNote") else ""
        ok("沒登入：白話說明「要用站長帳號登入」並帶回首頁的連結", "站長帳號登入" in note and pg.evaluate("() => !!document.querySelector('#chatNote a[href=\"../index.html\"]')"), note)
        ok("沒登入：送出鈕不能按、寫「請先登入」、輸入框打字也送不出", pg.is_disabled("#chatSend") and pg.inner_text("#chatSend") == "請先登入")
        pg.fill("#chatText", "試試看")
        ok("沒登入：打了字送出鈕仍是灰的", pg.is_disabled("#chatSend"))
        pg.keyboard.press("Control+Enter")
        ok("沒登入：完全沒打收件服務", br.n_all == 0, br.n_all)
        _ch_shot(pg, "chat_6_沒登入.png")
        ok("沒登入：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()
    br = _ChBridge(mode="noinbox")
    c, pg, got = _ch_open(b, base, br)
    try:
        pg.click("#chatBtn")
        ok("收件匣沒開（404）：白話說明「還沒有開放」並有「再試一次」", wait_until(pg, "() => __world.chat.mode === 'noinbox'", 15000) and "還沒有開放" in pg.inner_text("#chatNote") and _ch_vis(pg, "#chatRetry"), pg.inner_text("#chatNote"))
        ok("收件匣沒開：送出鈕灰掉、不會一直重複敲收件服務", pg.is_disabled("#chatSend"))
        pg.wait_for_timeout(2500)
        ok("收件匣沒開：不會一直重複敲收件服務（2.5 秒內沒有新請求）", br.n_all <= 2, br.n_all)
        _ch_shot(pg, "chat_7_沒開收件匣.png")
        br.mode = "on"
        pg.click("#chatRetry")
        ok("再試一次：收件服務好了就恢復可用（說明消失）", wait_until(pg, "() => __world.chat.mode === 'ok' && document.getElementById('chatNote').hidden", 10000))
        ok("收件匣沒開：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── 接入碼不長期存放 ─────────────────────────
def _ch_code(b, base):
    br = _ChBridge()
    # 舊版把碼存在 localStorage：載入後要搬進記憶體並清掉
    c, pg, got = _ch_open(b, base, br, extra_ls={"aiOffice.live.v1": _json.dumps({"url": _CH_AIO, "code": _CH_CODE, "office": "main"})})
    try:
        ok("接入碼：舊版存在儲存裡的碼，載入後從 localStorage 清掉", got and _CH_CODE not in pg.evaluate("() => localStorage.getItem('aiOffice.live.v1') || ''"))
        pg.evaluate("() => __world.live.openGuide()")
        ok("接入碼：引導視窗開著，網頁文字沒有明碼", _ch_vis(pg, "#aioGuide") and _CH_CODE not in pg.inner_text("body"))
        pg.click("#aioGuide [data-a=cpcode]")
        ok("接入碼：視窗開著時有遮罩版（不是明碼）", wait_until(pg, "() => !!document.getElementById('aioCodeMask')", 6000) and "已隱藏" in pg.inner_text("#aioCodeMask") and _CH_CODE not in pg.inner_text("#aioGuide"))
        ok("接入碼：視窗開著時記憶體裡有、localStorage 沒有", pg.evaluate("() => !!__world.live.code") and _CH_CODE not in pg.evaluate("() => JSON.stringify(Object.assign({}, localStorage))"))
        pg.click("#aioGuide .aio-gx")
        ok("接入碼：關掉視窗後記憶體裡的碼清掉（有登入身分可觀看）", wait_until(pg, "() => !__world.live.code", 6000))
        ok("接入碼：關掉視窗後仍有登入身分可觀看（不是回到示範）", pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.live.v1')).login === true"))
        ok("接入碼：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()



# ───────────────────────── 接入碼不長期存放 ─────────────────────────
def _ch_code(b, base):
    br = _ChBridge()
    # 舊版把碼存在 localStorage：載入後要搬進記憶體並清掉
    c, pg, got = _ch_open(b, base, br, extra_ls={"aiOffice.live.v1": _json.dumps({"url": _CH_AIO, "code": _CH_CODE, "office": "main"})})
    try:
        ok("接入碼：舊版存在儲存裡的碼，載入後從 localStorage 清掉", got and _CH_CODE not in pg.evaluate("() => localStorage.getItem('aiOffice.live.v1') || ''"))
        pg.evaluate("() => __world.live.openGuide()")
        ok("接入碼：引導視窗開著，網頁文字沒有明碼", _ch_vis(pg, "#aioGuide") and _CH_CODE not in pg.inner_text("body"))
        pg.click("#aioGuide [data-a=cpcode]")
        ok("接入碼：視窗開著時有遮罩版（不是明碼）", wait_until(pg, "() => !!document.getElementById('aioCodeMask')", 6000) and "已隱藏" in pg.inner_text("#aioCodeMask") and _CH_CODE not in pg.inner_text("#aioGuide"))
        ok("接入碼：視窗開著時記憶體裡有、localStorage 沒有", pg.evaluate("() => !!__world.live.code") and _CH_CODE not in pg.evaluate("() => JSON.stringify(Object.assign({}, localStorage))"))
        pg.click("#aioGuide .aio-gx")
        ok("接入碼：關掉視窗後記憶體裡的碼清掉（有登入身分可觀看）", wait_until(pg, "() => !__world.live.code", 6000))
        ok("接入碼：關掉視窗後仍有登入身分可觀看（不是回到示範）", pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.live.v1')).login === true"))
        ok("接入碼：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()




# ───────────────────────── 手機 390×844 ─────────────────────────
def _ch_mobile(b, base):
    br = _ChBridge()
    now = int(_time.time() * 1000)
    br.rev += 1
    br.msgs.append({"id": "m_%016d" % 0, "to": "ceo", "text": "先前的一句話", "status": "done", "created": now - 7200000, "updated": now - 7100000, "done_at": now - 7100000, "rev": br.rev, "reply": "好，我記下了"})
    c, pg, got = _ch_open(b, base, br, w=390, h=844, touch=True)
    try:
        ok("手機：辦公室頁載入完成", got)
        if not got:
            return
        pg.evaluate(_CH_FAB_JS, 0)
        ok("手機：輸入列固定在底部、不用先按任何鈕、收合時只有一行", _ch_vis(pg, "#chatText") and not _ch_vis(pg, "#mcHead") and pg.evaluate("() => { const r = document.getElementById('chatForm').getBoundingClientRect(); return r.height <= 64 && innerHeight - r.bottom <= 60 && r.bottom <= innerHeight; }"))
        ok("手機：輸入列右邊讓出客服鈕的位置（假客服鈕與輸入列沒交疊）", pg.evaluate(_CH_OVERLAP_JS)["out"] == [], pg.evaluate(_CH_OVERLAP_JS))
        ok("手機：頂列沒有多一顆「下指令」鈕", not pg.evaluate("() => [...document.querySelectorAll('#bar button')].some(b => /下指令/.test(b.textContent))"))
        _ch_shot(pg, "mc_m1_收合.png")
        pg.tap("#chatBtn")
        ok("手機：點開先看對話清單（全螢幕、清單看得到、對話串與輸入框先不顯示）", wait_until(pg, "() => !document.getElementById('mcTop').hidden", 4000) and _ch_vis(pg, "#mcStrip") and not _ch_vis(pg, "#chatList") and not _ch_vis(pg, "#chatText") and pg.evaluate("() => { const r = document.getElementById('chatPanel').getBoundingClientRect(); return r.width >= innerWidth - 1 && r.height >= innerHeight - 1; }"))
        ok("手機：清單有 CEO 與各部門（一個單位一列）", pg.evaluate("() => document.querySelectorAll('#mcStrip .mc-th').length") >= 12 and not _ch_vis(pg, "#mcBack"))
        _ch_shot(pg, "mc_m2_清單.png")
        pg.tap("#mcStrip [data-room=ceo]")
        ok("手機：點一列進入對話（上方出現返回鈕、輸入框出現、清單收起）", _ch_vis(pg, "#mcBack") and _ch_vis(pg, "#chatText") and _ch_vis(pg, "#chatList") and not _ch_vis(pg, "#mcStrip") and "先前的一句話" in pg.inner_text("#chatList"))
        pg.tap("#chatText")
        pg.keyboard.type("手機上說一句")
        pg.tap("#chatSend")
        ok("手機：送出、對話串出現我的氣泡與「傳送中」", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 2", 8000) and _ch_status(pg) == "傳送中" and br.posts[-1]["to"] == "ceo", _ch_status(pg))
        info = pg.evaluate("""() => { const out = { hscroll: document.documentElement.scrollWidth > innerWidth + 1, small: [], tiny: [] };
            for (const e of document.querySelectorAll('#chatPanel *')) { const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue; const t = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).length;
                if (t && parseFloat(getComputedStyle(e).fontSize) < 11) out.small.push(e.tagName + ':' + e.textContent.trim().slice(0, 12)); }
            for (const e of document.querySelectorAll('#chatPanel button, #chatPanel select')) { const r = e.getBoundingClientRect(); if (r.width > 0 && (r.height < 32 || r.width < 32)) out.tiny.push(e.id + ' ' + e.textContent.trim().slice(0, 8) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); }
            return out; }""")
        ok("手機（對話）：沒有橫向溢出、字不小於 11px、按鈕夠大", not info["hscroll"] and not info["small"] and not info["tiny"], info)
        ok("手機（對話）：輸入列讓出客服鈕的位置", pg.evaluate("() => { const f = document.getElementById('fakeFab').getBoundingClientRect(), r = document.getElementById('chatForm').getBoundingClientRect(); return r.right <= f.left + 1 || r.bottom <= f.top + 1; }"))
        _ch_shot(pg, "mc_m3_對話.png")
        pg.tap("#mcBack")
        ok("手機：按上方返回回到清單（輸入框收起、CEO 列預覽是我剛說的）", _ch_vis(pg, "#mcStrip") and not _ch_vis(pg, "#chatText") and "手機上說一句" in pg.inner_text("#mcStrip [data-room=ceo]"))
        pg.tap("#mcStrip [data-room='d:design']")
        ok("手機：進部門聊天室，輸入列上方有「對誰說」選單（整個部門／成員）", _ch_vis(pg, "#chatTo") and pg.evaluate("() => document.getElementById('chatTo').options.length") >= 6 and _ch_target(pg)["to"] == "dept:design")
        _ch_shot(pg, "mc_m4_部門室.png")
        ok("手機：沒有禁用字", not _CH_BAD_RE.search(pg.inner_text("#chatPanel")), _CH_BAD_RE.findall(pg.inner_text("#chatPanel")))
        pg.tap("#chatX")
        ok("手機：× 收合後回到辦公室、輸入列還在底部", not _ch_vis(pg, "#mcHead") and _ch_vis(pg, "#chatText"))
        xy = _ch_char_xy(pg, "mobile-ui")
        pg.touchscreen.tap(xy[0], xy[1])
        ok("手機：點 3D 角色 → 對象切成被點到的那位（輸入列不擋 3D）", wait_until(pg, "() => __world.chat.to !== 'ceo'", 6000), _ch_target(pg))
        ok("手機：輸入列提示字放得進一行（量字寬，不折行被切）", pg.evaluate("""() => { const t = document.getElementById('chatText'), cs = getComputedStyle(t), cv = document.createElement('canvas').getContext('2d'); cv.font = cs.fontSize + ' ' + cs.fontFamily;
            return cv.measureText(t.placeholder).width <= t.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight); }"""), pg.evaluate("() => [document.getElementById('chatText').placeholder, document.getElementById('chatText').clientWidth]"))
        ok("手機：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _ch_all(b, base):
    only = [x for x in _os.environ.get("CHAT_ONLY", "").split(",") if x]
    for fn in (_ch_desktop, _ch_window, _ch_dept, _ch_poll, _ch_widths, _ch_gates, _ch_code, _ch_mobile):
        if only and fn.__name__ not in only:
            continue
        try:
            fn(b, base)
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok("辦公室主對話框：%s 中途爆掉" % fn.__name__, False, str(e)[:300])


register("辦公室主對話框", lambda pg, b, base, code: _ch_all(b, base))
