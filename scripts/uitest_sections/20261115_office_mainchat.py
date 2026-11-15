# 驗收段落「辦公室主對話框」：AI Office 3D 辦公室（site/office/world.html）畫面下方常駐的主對話框（world/js/chat.js、chat.css）
#   規格：docs/ai_office/plan.md 最後一節「主對話框」、docs/ai_office/chat_command_spec.md 第六節。擁有者原話：不管對哪個 Agent 說，其實都是對 CEO 說，只是附上指定給誰。
#   ① 常駐：一載入就有輸入列（不用先按任何鈕）、收合時只有一行；還沒碰它之前不打收件服務；沒選人＝「對 CEO 說」
#   ② 不擋 3D：外框不吃滑鼠，真滑鼠點 3D 角色照樣選到人；輸入框打字（wasd／E／F／V／空白）不會操控角色或觸發場景快捷鍵
#   ③ 鍵盤：Enter 送出、Shift+Enter 換行、注音選字中的 Enter 不送出、Esc 在輸入框內收合
#   ④ 切對象：真滑鼠點 3D 的人 → 對象切成他（頭像、名字、提示字）；資訊卡「對他說」→ 對象帶入並展開；「回到 CEO」一鍵切回；對話串切換列
#   ⑤ 每位 Agent 一串、CEO 一串：依收件匣資料的 to 分組；訊息下方標「由 CEO 轉交給 ○○」；技術上收件服務收到的 to＝指定的人
#   ⑥ 狀態與回覆：排隊中→已取走→執行中→完成；回覆用那位 Agent 的頭像與名字顯示在他的串；3D 頭上冒泡泡（回覆第一句）；撤回
#   ⑦ 不重疊：用程式量對話框與版本標記、運動場鈕、資訊卡、操控提示、整修列、客服鈕（測試裡放一顆同位置同大小的假客服鈕）的矩形（1440／1000／800／390 四種寬度）
#   ⑧ 手機 390×844：輸入列固定底部、點開全螢幕對話串；資訊卡「對他說」可用；沒有橫向溢出、字不小於 11px、按鈕夠大；沒有禁用字
#   ⑨ 沒登入／收件匣沒開：白話說明、不打收件服務；接入碼不長期存放（舊段落保留）
# 收件服務用 page.route 模擬（https://aio.test），格式與 workers/ai-office-bridge/worker.js 的收件匣 API 一致（這就是「假資料模式」：前端走的是真的 fetch 路徑）。
# 環境變數 CHAT_SHOTS 指到資料夾時，順便存截圖。函式名一律加 _ch 前綴，自成一格。
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
        since = int((u.query.split("since=")[-1] or "0") if "since=" in u.query else 0)
        rows = [self.view(m) for m in self.msgs if m["rev"] > since] if since else [self.view(m) for m in self.msgs]
        op = [self.view(m) for m in self.msgs if m["status"] in ("queued", "claimed", "running")]
        return route.fulfill(status=200, body=_json.dumps({"office": "main", "now": int(_time.time() * 1000), "rev": self.rev, "since": since, "messages": rows, "open": op, "limits": {"max_text": 2000, "max_pending": 20}, "session_last_seen": self.last_seen}), headers=h)


def _ch_open(b, base, br, login=True, w=1280, h=800, touch=False, extra_ls=None):
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
    pg.goto(_ch_root(base) + "/office/world.html?ambient=0&q=low&pr=0.6&chat_poll=500&chat_bg_poll=700&live_poll=700", wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat && window.__world.live", 90000)
    if got:
        pg.evaluate("() => { __world.speed = 8; }")
    return c, pg, got


def _ch_status(pg, i=-1):
    return pg.evaluate("(i) => { const a = [...document.querySelectorAll('#chatList .c-msg')]; const m = a[i < 0 ? a.length + i : i]; return m ? m.querySelector('.c-st').textContent.trim() : null; }", i)


def _ch_vis(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && !e.hidden && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }", sel)



# ───────────────────────── 共用量測 ─────────────────────────
_CH_FAB_JS = """(w) => { let f = document.getElementById('fakeFab'); if (f) f.remove(); f = document.createElement('div'); f.id = 'fakeFab'; f.className = 'supfab';
    const small = innerWidth <= 820; f.style.cssText = 'position:fixed;z-index:1200;right:' + (small ? 16 : 20) + 'px;bottom:' + (small ? 16 : 20) + 'px;width:' + (small ? 52 : 130) + 'px;height:' + (small ? 52 : 48) + 'px;border-radius:999px;background:#456';
    document.body.append(f); }"""
# 回傳「對話框看得見的部分」與其他底部元件互相交疊的清單
_CH_OVERLAP_JS = """() => {
    const vis = e => { if (!e) return null; const s = getComputedStyle(e), r = e.getBoundingClientRect(); if (e.hidden || s.display === 'none' || s.visibility === 'hidden' || r.width < 2 || r.height < 2) return null; return r; };
    const mine = [...document.querySelectorAll('#mcTop, #mcDock > *')].map(e => [e.id || e.className, vis(e)]).filter(x => x[1]);
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


# ───────────────────────── 桌機：完整流程 ─────────────────────────
def _ch_desktop(b, base):
    br = _ChBridge()
    c, pg, got = _ch_open(b, base, br, w=1440, h=900)
    try:
        ok("主對話框：辦公室頁載入完成、對話框模組在", got)
        if not got:
            return
        pg.evaluate(_CH_FAB_JS, 0)
        # ① 常駐
        ok("常駐：一載入就看得到輸入列（不用先按任何鈕）", _ch_vis(pg, "#chatText") and _ch_vis(pg, "#chatSend") and _ch_vis(pg, "#chatBtn"))
        ok("常駐：預設收合（沒有對話串卡片）、只有一行輸入列", not _ch_vis(pg, "#mcTop") and pg.get_attribute("#chatBtn", "aria-expanded") == "false")
        bar = pg.evaluate("() => { const r = document.getElementById('chatForm').getBoundingClientRect(); return { h: Math.round(r.height), bottom: Math.round(innerHeight - r.bottom), cx: Math.round((r.left + r.right) / 2) }; }")
        ok("常駐：收合時輸入列在畫面底部、高度 ≤ 64、水平置中", bar["h"] <= 64 and bar["bottom"] <= 40 and abs(bar["cx"] - 720) <= 6, bar)
        ok("目前對象：沒選人＝對 CEO 說（名字 CEO、提示字「對 CEO 說…」、有頭像）", _ch_target(pg) == {"to": "ceo", "nm": "CEO", "ph": "對 CEO 說…"} and pg.evaluate("() => !!document.querySelector('#mcAva img, #mcAva .ava')"), _ch_target(pg))
        pg.wait_for_timeout(1500)
        ok("常駐：還沒碰它之前，不打收件服務", br.n_all == 0, br.n_all)
        ok("送出鈕：沒打字時是灰的", pg.is_disabled("#chatSend"))
        ok("說明：Enter 送出、Shift＋Enter 換行（展開時看得到）", "Enter 送出" in pg.evaluate("() => document.getElementById('chatHint').textContent") and "Shift＋Enter 換行" in pg.evaluate("() => document.getElementById('chatHint').textContent"))
        _ch_overlap(pg, "1440 收合")
        _ch_shot(pg, "mc_d1_收合.png")
        # ② 不擋 3D：真滑鼠點角色
        xy = _ch_char_xy(pg, "frontend-ui")
        top = pg.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return e ? (e.id || e.tagName) : null; }", xy)
        ok("不擋 3D：角色所在位置最上面是場景畫布，不是對話框", top == "cv", top)
        pg.mouse.click(xy[0], xy[1])
        ok("點 3D 角色：選到人（資訊卡打開）", wait_until(pg, "() => !document.getElementById('card').hidden", 6000))
        ok("點 3D 角色：對象切成他（對話框顯示他的名字、提示字、頭像）", wait_until(pg, "() => __world.chat.to === 'frontend-ui'", 4000) and _ch_target(pg)["nm"] == pg.evaluate("() => __world.chars.get('frontend-ui').spec.nick") and "由 CEO 轉交" in _ch_target(pg)["ph"], _ch_target(pg))
        ok("點 3D 角色：這時還沒打收件服務（只是切對象）", br.n_all == 0, br.n_all)
        ok("資訊卡有「對他說」鈕", _ch_vis(pg, "#card [data-chat]") and pg.inner_text("#card [data-chat]") == "對他說")
        _ch_force_bottoms(pg)
        _ch_overlap(pg, "1440 資訊卡開著", need=["#card", "#aoBuild", "#fakeFab"])
        _ch_shot(pg, "mc_d2_點角色.png")
        # 打字不觸發場景快捷鍵（角色還被選著）
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
        ok("送出（收合中）：輸入列上方有一行提示「排隊中・…」", wait_until(pg, "() => { const p = document.getElementById('chatPeek'); return !p.hidden && p.textContent.includes('排隊中'); }", 6000), pg.inner_text("#chatPeek") if _ch_vis(pg, "#chatPeek") else "(沒有)")
        ok("送出：徽章顯示 1 則進行中", pg.inner_text("#chatN") == "1")
        ok("3D：被指定的同事頭上出現待辦小圖示（便條）", wait_until(pg, "() => window['__emo_frontend-ui'].includes('note')", 6000), pg.evaluate("() => window['__emo_frontend-ui']"))
        _ch_shot(pg, "mc_d3_已送出.png")
        # 展開：他的對話串
        pg.click("#chatBtn")
        ok("展開：看得到對話串、頭像與名字、「回到 CEO」鈕", _ch_vis(pg, "#mcTop") and _ch_vis(pg, "#mcWho .mc-ava") and _ch_vis(pg, "#chatCeo") and pg.get_attribute("#chatBtn", "aria-expanded") == "true")
        ok("他的串：只有給他的那一則、狀態「排隊中」、下方標「由 CEO 轉交給 ○○」", pg.evaluate("() => document.querySelectorAll('#chatList .c-msg').length") == 1 and _ch_status(pg) == "排隊中" and "由 CEO 轉交給" in pg.inner_text("#chatList .c-relay"), pg.inner_text("#chatList"))
        ok("展開時沒有 CEO 的那一串訊息混進來（CEO 串還是空的）", pg.evaluate("() => { const K = __world.chat; return [...K.msgs.values()].filter(m => (m.to || 'ceo') === 'ceo').length; }") == 0)
        _ch_overlap(pg, "1440 展開（資訊卡仍開著）", need=["#card"])
        _ch_shot(pg, "mc_d4_展開他的串.png")
        # 對 CEO 說：一鍵回 CEO
        pg.click("#chatCeo")
        ok("回到 CEO：一鍵切回（名字 CEO、「回到 CEO」鈕消失、他的訊息不在 CEO 串裡）", _ch_target(pg)["to"] == "ceo" and not _ch_vis(pg, "#chatCeo") and pg.evaluate("() => document.querySelectorAll('#chatList .c-msg').length") == 0 and pg.evaluate("() => document.activeElement.id") == "chatText", _ch_target(pg))
        pg.keyboard.type("這個之後再說")
        pg.keyboard.press("Enter")
        ok("對 CEO 說：收件服務收到 to＝ceo、CEO 的串出現這一則、標「送給 CEO」", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 8000) and br.posts[1]["to"] == "ceo" and "送給 CEO" in pg.inner_text("#chatList .c-relay") and "轉交" not in pg.inner_text("#chatList .c-relay"), br.posts)
        ok("對話串切換列：出現 CEO 與那位 Agent 兩串", wait_until(pg, "() => document.querySelectorAll('#mcStrip .mc-th').length === 2", 4000), pg.evaluate("() => document.getElementById('mcStrip').innerText"))
        # 撤回 CEO 這則
        pg.click("#chatList .c-msg [data-cancel]")
        ok("撤回：變「已撤回」、收件服務真的收到撤回、撤回鈕消失", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '已撤回'", 8000) and len(br.cancels) == 1 and not pg.query_selector("#chatList .c-msg [data-cancel]"), br.cancels)
        # 切到 Agent 的串
        pg.click("#mcStrip [data-th=frontend-ui]")
        ok("切換列：點那位 Agent → 切到他的串（只有他的訊息）", _ch_target(pg)["to"] == "frontend-ui" and "手機版按鈕太小" in pg.inner_text("#chatList") and "這個之後再說" not in pg.inner_text("#chatList"), pg.inner_text("#chatList"))
        # 狀態推進
        mid = br.msgs[0]["id"]
        br.set(mid, "claimed")
        ok("狀態：已取走（撤回鈕消失）", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '已取走'", 8000) and not pg.query_selector("#chatList .c-msg [data-cancel]"), _ch_status(pg, 0))
        br.set(mid, "running")
        ok("狀態：執行中（有轉圈）", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '執行中' && !!document.querySelector('#chatList .c-msg .c-st .spin')", 8000), _ch_status(pg, 0))
        ph = wait_until(pg, "() => { const a = __world.state.agents.get('frontend-ui'); return a && a.phase !== 'idle' ? a.phase : null; }", 8000)
        ok("3D：執行中 → 那位同事進入派工（領任務／工作）", bool(ph), ph)
        br.set(mid, "done", "已改好：頂列按鈕高度 36 → 44。後面還有第二句\nhttps://liguligu-puipui.com/office/world.html")
        ok("狀態：完成、他的串裡出現回覆", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '完成'", 8000) and "頂列按鈕高度" in pg.inner_text("#chatList .c-rp"), _ch_status(pg, 0))
        ok("回覆：用那位 Agent 的頭像與名字（頭像是圖、名字是他的暱稱）", pg.evaluate("() => { const r = document.querySelector('#chatList .c-rp'); const n = __world.chars.get('frontend-ui').spec.nick; return !!r.querySelector('.c-av img, .c-av .ava') && r.querySelector('.c-rb b').textContent.trim() === n; }"), pg.inner_text("#chatList .c-rp"))
        ok("回覆：網址可以點（新分頁開）", pg.evaluate("() => { const a = document.querySelector('#chatList .c-rp a'); return !!a && a.href.startsWith('https://liguligu-puipui.com/') && a.target === '_blank' && a.rel.includes('noopener'); }"))
        ok("3D：他頭上冒泡泡，內容是回覆的第一句（短句、不含網址）", wait_until(pg, "() => window['__say_frontend-ui'].some(t => t.includes('頂列按鈕高度') && !t.includes('http') && t.length <= 19)", 25000), pg.evaluate("() => window['__say_frontend-ui']"))
        ok("3D：完成後同事有小慶祝（星星）", wait_until(pg, "() => window['__emo_frontend-ui'].includes('star')", 25000), pg.evaluate("() => window['__emo_frontend-ui']"))
        ok("頂列徽章：全部做完後數字消失", wait_until(pg, "() => document.getElementById('chatN').hidden", 6000))
        _ch_shot(pg, "mc_d5_回覆.png")
        ok("沒有禁用字", not _CH_BAD_RE.search(pg.inner_text("#chatPanel")), _CH_BAD_RE.findall(pg.inner_text("#chatPanel")))
        # Esc：輸入框內收合
        pg.click("#chatText")
        pg.keyboard.press("Escape")
        ok("Esc（在輸入框內）：收合對話框、輸入框失焦", wait_until(pg, "() => document.getElementById('mcTop').hidden", 3000) and pg.get_attribute("#chatBtn", "aria-expanded") == "false" and pg.evaluate("() => document.activeElement.id") != "chatText")
        ok("收合後對象還是那位 Agent（沒有被重置）", _ch_target(pg)["to"] == "frontend-ui")
        pg.click("#chatText")
        pg.keyboard.type("收合著再問一次")
        pg.keyboard.press("Enter")
        ok("收合著送出第二則：收件服務收到 to＝frontend-ui", wait_until(pg, "() => __world.chat.msgs.size === 3", 8000) and br.posts[-1]["to"] == "frontend-ui", br.posts)
        pg.click("#chatBtn")
        wait_until(pg, "() => !document.getElementById('mcTop').hidden", 4000)
        pg.click("#chatX")
        br.set(br.msgs[-1]["id"], "done", "第二次的回覆在這裡。還有後半句")      # 先展開看過「排隊中」再收合，之後才完成：仍要跳出「有新回覆」
        ok("收合後回覆到了：輸入列上方出現「○○：回覆第一句…」的提示（還沒看過的新回覆）", wait_until(pg, "() => { const p = document.getElementById('chatPeek'); return !p.hidden && p.textContent.includes('第二次的回覆'); }", 8000), pg.evaluate("() => document.getElementById('chatPeek').textContent"))
        pg.click("#chatPeek")
        ok("點提示：展開那位的串、提示消失（看過了）", _ch_vis(pg, "#mcTop") and _ch_target(pg)["to"] == "frontend-ui" and not _ch_vis(pg, "#chatPeek"))
        pg.click("#chatX")
        ok("× 收合鈕：收合", not _ch_vis(pg, "#mcTop"))
        # 資訊卡「對他說」
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('smc-technical'))")
        ok("資訊卡（另一位）：點出來對象切成他", wait_until(pg, "() => __world.chat.to === 'smc-technical'", 4000), _ch_target(pg))
        pg.evaluate("() => document.getElementById('chatText').blur()")
        pg.click("#card [data-chat]")
        ok("資訊卡「對他說」：對話框展開、資訊卡讓位、輸入框拿到焦點、對象是他", _ch_vis(pg, "#mcTop") and not _ch_vis(pg, "#card") and _ch_target(pg)["to"] == "smc-technical" and pg.evaluate("() => document.activeElement.id") == "chatText", _ch_target(pg))
        ok("他的串是空的、有白話提示（說明會先交給 CEO 再轉交）", "還沒有跟" in pg.inner_text("#chatList") and "CEO" in pg.inner_text("#chatList"), pg.inner_text("#chatList"))
        pg.press("#chatText", "Escape")
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('ceo'))")
        ok("資訊卡（CEO）：按鈕寫「對 CEO 說」、對象是 CEO", "對 CEO 說" in pg.inner_text("#card [data-chat]") and _ch_target(pg)["to"] == "ceo", _ch_target(pg))
        ok("資訊卡反覆重畫（refreshCard）不會把我手動改的對象又切回去", pg.evaluate("() => { __world.chat.setTarget('frontend-ui'); __world.ui.refreshCard(); __world.ui.refreshCard(); return __world.chat.to; }") == "frontend-ui")
        ok("沒有主控台錯誤", not pg.errs, pg.errs[:3])
        stored = pg.evaluate("() => { try { return JSON.stringify(Object.assign({}, localStorage)); } catch (e) { return ''; } }")
        ok("接入碼：不在 localStorage、不在頁面文字", _CH_CODE not in stored and "aio_" not in pg.inner_text("body"), stored[:200])
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
            _ch_overlap(pg, "%d 收合＋資訊卡" % w, need=["#card", "#aoBuild", "#fakeFab"])
            ok("%d 寬：收合的輸入列仍可用（看得到輸入框、高度 ≤ 64）" % w, _ch_vis(pg, "#chatText") and pg.evaluate("() => document.getElementById('chatForm').getBoundingClientRect().height") <= 64)
            pg.click("#chatBtn")
            wait_until(pg, "() => !document.getElementById('mcTop').hidden", 4000)
            _ch_overlap(pg, "%d 展開" % w)
            ok("%d 寬：展開時窄螢幕讓資訊卡讓位（不疊在對話串上）" % w, not _ch_vis(pg, "#card"))
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



# ───────────────────────── 手機 390×844 ─────────────────────────
def _ch_mobile(b, base):
    br = _ChBridge()
    c, pg, got = _ch_open(b, base, br, w=390, h=844, touch=True)
    try:
        ok("手機：辦公室頁載入完成", got)
        if not got:
            return
        pg.evaluate(_CH_FAB_JS, 0)
        ok("手機：輸入列固定在底部、不用先按任何鈕、收合時只有一行", _ch_vis(pg, "#chatText") and not _ch_vis(pg, "#mcTop") and pg.evaluate("() => { const r = document.getElementById('chatForm').getBoundingClientRect(); return r.height <= 64 && innerHeight - r.bottom <= 60 && r.bottom <= innerHeight; }"))
        ok("手機：輸入列右邊讓出客服鈕的位置（假客服鈕與輸入列沒交疊）", pg.evaluate(_CH_OVERLAP_JS)["out"] == [], pg.evaluate(_CH_OVERLAP_JS))
        ok("手機：頂列沒有多一顆「下指令」鈕（「更多」裡也沒有）", not pg.evaluate("() => [...document.querySelectorAll('#bar button')].some(b => /下指令/.test(b.textContent))"))
        info = pg.evaluate("""() => { const out = { hscroll: document.documentElement.scrollWidth > innerWidth + 1, small: [], tiny: [] };
            for (const e of document.querySelectorAll('#chatPanel *')) { const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue; const t = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).length;
                if (t && parseFloat(getComputedStyle(e).fontSize) < 11) out.small.push(e.tagName + ':' + e.textContent.trim().slice(0, 12)); }
            for (const e of document.querySelectorAll('#chatPanel button')) { const r = e.getBoundingClientRect(); if (r.width > 0 && (r.height < 32 || r.width < 32)) out.tiny.push(e.id + ' ' + e.textContent.trim().slice(0, 8) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); }
            return out; }""")
        ok("手機（收合）：沒有橫向溢出、字不小於 11px、按鈕夠大", not info["hscroll"] and not info["small"] and not info["tiny"], info)
        _ch_shot(pg, "mc_m1_收合.png")
        # 真手指點角色 → 對象切換、資訊卡「對他說」
        xy = _ch_char_xy(pg, "mobile-ui")
        pg.touchscreen.tap(xy[0], xy[1])
        # 手機上角色擠在一起，手指點到的可能是旁邊那位；只要「點到的人」＝對象就算對（後面一律用實際被點到的人驗）
        ok("手機：點 3D 角色 → 對象切成被點到的那位（輸入列不擋 3D）", wait_until(pg, "() => __world.chat.to !== 'ceo'", 6000), _ch_target(pg))
        tid = pg.evaluate("() => __world.chat.to")
        ok("手機：資訊卡有「對他說」鈕、夠大", _ch_vis(pg, "#card [data-chat]") and pg.evaluate("() => document.querySelector('#card [data-chat]').getBoundingClientRect().height") >= 34)
        _ch_overlap(pg, "390 資訊卡開著", need=["#card", "#aoBuild", "#fakeFab"])
        _ch_shot(pg, "mc_m2_資訊卡.png")
        pg.tap("#card [data-chat]")
        ok("手機：「對他說」→ 全螢幕對話串、對象是他", wait_until(pg, "() => !document.getElementById('mcTop').hidden", 4000) and pg.evaluate("() => { const r = document.getElementById('chatPanel').getBoundingClientRect(); return r.width >= innerWidth - 1 && r.height >= innerHeight - 1; }") and _ch_target(pg)["to"] == tid, _ch_target(pg))
        wait_until(pg, "() => __world.chat.mode === 'ok'", 15000)
        pg.tap("#chatText")
        pg.keyboard.type("手機版測試", delay=15)
        pg.tap("#chatSend")
        ok("手機：送出後列表出現「排隊中」、收件對象是他", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 8000) and _ch_status(pg) == "排隊中" and br.posts[0]["to"] == tid, br.posts)
        br.set(br.msgs[0]["id"], "done", "手機測試回覆\nhttps://liguligu-puipui.com/")
        ok("手機：完成並顯示回覆（他的頭像）", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '完成'", 8000) and _ch_vis(pg, "#chatList .c-av"))
        _ch_shot(pg, "mc_m3_全螢幕.png")
        info = pg.evaluate("""() => { const out = { hscroll: document.documentElement.scrollWidth > innerWidth + 1, small: [], tiny: [], over: [] };
            const P = document.getElementById('chatPanel'), pr = P.getBoundingClientRect();
            for (const e of P.querySelectorAll('*')) { const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue; const t = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).length;
                if (t && parseFloat(getComputedStyle(e).fontSize) < 11) out.small.push(e.tagName + ':' + e.textContent.trim().slice(0, 12));
                if (r.right > pr.right + 1 || r.left < pr.left - 1) out.over.push(e.tagName + '.' + e.className); }
            for (const e of P.querySelectorAll('button')) { const r = e.getBoundingClientRect(); if (r.width > 0 && (r.height < 32 || r.width < 32)) out.tiny.push(e.id + ' ' + e.textContent.trim().slice(0, 8) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); }
            return out; }""")
        ok("手機（全螢幕）：沒有橫向溢出、沒有東西超出對話框、字不小於 11px、按鈕夠大", not info["hscroll"] and not info["over"] and not info["small"] and not info["tiny"], info)
        ok("手機（全螢幕）：輸入列與假客服鈕沒有交疊、版本標記被蓋住的不算（整頁蓋住）", pg.evaluate(_CH_OVERLAP_JS)["out"] == [], pg.evaluate(_CH_OVERLAP_JS))
        ok("手機：沒有禁用字", not _CH_BAD_RE.search(pg.inner_text("#chatPanel")))
        pg.tap("#chatX")
        ok("手機：× 收合後回到辦公室、輸入列還在底部", not _ch_vis(pg, "#mcTop") and _ch_vis(pg, "#chatText"))
        ok("手機：輸入列提示字放得進一行（量字寬，不折行被切）", pg.evaluate("""() => { const t = document.getElementById('chatText'), cs = getComputedStyle(t), cv = document.createElement('canvas').getContext('2d'); cv.font = cs.fontSize + ' ' + cs.fontFamily;
            return cv.measureText(t.placeholder).width <= t.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight); }"""), pg.evaluate("() => [document.getElementById('chatText').placeholder, document.getElementById('chatText').clientWidth]"))
        ok("手機：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _ch_all(b, base):
    only = [x for x in _os.environ.get("CHAT_ONLY", "").split(",") if x]      # 開發時只跑某幾段：CHAT_ONLY=_ch_mobile
    for fn in (_ch_desktop, _ch_widths, _ch_gates, _ch_code, _ch_mobile):
        if only and fn.__name__ not in only:
            continue
        try:
            fn(b, base)
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok("辦公室主對話框：%s 中途爆掉" % fn.__name__, False, str(e)[:300])


register("辦公室主對話框", lambda pg, b, base, code: _ch_all(b, base))
