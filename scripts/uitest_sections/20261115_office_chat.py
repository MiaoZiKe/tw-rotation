# 驗收段落「辦公室下指令」：AI Office 3D 辦公室（site/office/world.html）頂列「下指令」→ 對話框（規格 docs/ai_office/chat_command_spec.md 第六節）
#   ① 沒打開對話框前不打收件服務；打開後有收件對象下拉（第一項「交給 CEO 分派」、其餘是在職同事）、輸入框字數、送出
#   ② 超過 2000 字送出鈕灰掉；選同事、用鍵盤打字、Ctrl+Enter 送出 → 列表出現「排隊中」、送出的內容與收件對象正確、輸入框清空、那位同事頭上出現待辦小圖示
#   ③ 排隊中可以撤回 → 「已撤回」（收件服務真的收到撤回）
#   ④ 假收件服務把狀態推進：已取走 → 執行中（同事真的進入派工、走去座位工作）→ 完成並顯示回覆（網址可點）；完成後同事頭上有小慶祝、頂列徽章數字回 0
#   ⑤ 從同事的資訊卡按「對他下指令」→ 對話框開啟且收件對象已帶入
#   ⑥ 沒登入：白話說明＋送出鈕不能按、完全沒打收件服務；收件服務沒開收件匣（404）：白話說明、沒有主控台錯誤
#   ⑦ 接入碼：頁面任何地方（對話框、localStorage）都沒有；live.js 的「連接我的 Claude」領碼後，關掉視窗碼就清掉、觀看改用登入身分
#   ⑧ 手機 390×844：全螢幕對話框可用、沒有橫向溢出、字不小於 11px、按鈕夠大；畫面沒有禁用字
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
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "401" not in m.text else None)
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


# ───────────────────────── 桌機：完整流程 ─────────────────────────
def _ch_desktop(b, base):
    br = _ChBridge()
    c, pg, got = _ch_open(b, base, br)
    try:
        ok("下指令：辦公室頁載入完成、對話框模組在", got)
        if not got:
            return
        ok("下指令：頂列有「下指令」鈕", _ch_vis(pg, "#chatBtn") and "下指令" in pg.inner_text("#chatBtn"))
        pg.wait_for_timeout(1500)
        ok("下指令：沒打開對話框之前，不打收件服務", br.n_all == 0, br.n_all)
        pg.click("#chatBtn")
        ok("下指令：點鈕打開對話框", _ch_vis(pg, "#chatPanel") and pg.get_attribute("#chatBtn", "aria-expanded") == "true")
        ok("下指令：打開後讀了收件匣、而且只用登入權杖（沒有接入碼標頭）", wait_until(pg, "() => __world.chat.mode === 'ok'", 15000) and br.n_get >= 1 and all(h.get("x-aio-session") == _CH_TOK and "authorization" not in h for h in br.hdrs), br.hdrs[:1])
        opts = pg.evaluate("() => [...document.querySelectorAll('#chatTo option')].map(o => [o.value, o.textContent])")
        ok("收件對象：第一項是「交給 CEO 分派」（值 ceo）", opts and opts[0] == ["ceo", "交給 CEO 分派"], opts[:2])
        ok("收件對象：其後列出在職同事（含 frontend-ui），不含寵物", len(opts) >= 8 and any(o[0] == "frontend-ui" for o in opts) and not any(o[0] == "ceo" for o in opts[1:]), len(opts))
        ok("你的 Claude 在不在：沒有工作階段時寫「目前沒開、會排隊、最多保留 24 小時」", "目前沒開" in pg.inner_text("#chatLive") and "24 小時" in pg.inner_text("#chatLive"), pg.inner_text("#chatLive"))
        br.last_seen = int(_time.time() * 1000) - 20000
        ok("你的 Claude 在不在：5 分鐘內有工作階段 → 「你的 Claude 在線上」", wait_until(pg, "() => document.getElementById('chatLive').textContent.includes('在線上')", 8000), pg.inner_text("#chatLive"))
        ok("送出鈕：沒打字時是灰的", pg.is_disabled("#chatSend"))
        _ch_shot(pg, "chat_1_打開.png")
        pg.evaluate("() => { const c = __world.chars.get('frontend-ui'); window.__emo = []; const o = c.emote.bind(c); c.emote = (s, t) => { window.__emo.push(s); return o(s, t); }; }")
        # 超過 2000 字
        pg.fill("#chatText", "字" * 2001)
        ok("字數：顯示「已輸入 2001／2000」、超過就不能送", pg.inner_text("#chatCount") == "已輸入 2001／2000" and pg.is_disabled("#chatSend") and "over" in (pg.get_attribute("#chatCount", "class") or ""), pg.inner_text("#chatCount"))
        pg.fill("#chatText", "")
        # 選同事、用鍵盤打字、Ctrl+Enter 送出
        pg.select_option("#chatTo", "frontend-ui")
        pg.click("#chatText")
        pg.keyboard.type("手機版按鈕太小", delay=20)
        ok("字數：隨輸入更新（7 字）、送出鈕可按", pg.inner_text("#chatCount") == "已輸入 7／2000" and not pg.is_disabled("#chatSend"), pg.inner_text("#chatCount"))
        pg.keyboard.press("Enter")
        pg.keyboard.type("再補一行")
        ok("Enter 是換行、不會送出", br.posts == [] and "\n" in pg.input_value("#chatText"), br.posts)
        pg.keyboard.press("Control+Enter")
        ok("送出：收件服務收到正確的對象與內容", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 8000) and br.posts and br.posts[0]["to"] == "frontend-ui" and br.posts[0]["text"] == "手機版按鈕太小\n再補一行", br.posts)
        ok("送出：列表出現「排隊中」、對象名稱與內容都在、輸入框清空", _ch_status(pg) == "排隊中" and "手機版按鈕太小" in pg.inner_text("#chatList") and pg.input_value("#chatText") == "", _ch_status(pg))
        ok("送出：頂列徽章顯示 1 則進行中", pg.inner_text("#chatN") == "1")
        em = wait_until(pg, "() => window.__emo.includes('note')", 6000)
        ok("3D：被指定的同事頭上出現待辦小圖示（便條）", em, pg.evaluate("() => window.__emo"))
        _ch_shot(pg, "chat_2_排隊中.png")
        # 撤回
        pg.select_option("#chatTo", "ceo")
        pg.fill("#chatText", "晚點再說的事")
        pg.click("#chatSend")
        ok("送出給 CEO：第二則排隊中", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 2", 8000) and br.posts[1]["to"] == "ceo")
        pg.click("#chatList .c-msg:nth-child(2) [data-cancel]")
        ok("撤回：變「已撤回」、收件服務真的收到撤回、撤回鈕消失", wait_until(pg, "() => document.querySelector('#chatList .c-msg:nth-child(2) .c-st').textContent.trim() === '已撤回'", 8000) and len(br.cancels) == 1 and not pg.query_selector("#chatList .c-msg:nth-child(2) [data-cancel]"), br.cancels)
        # 狀態推進
        mid = br.msgs[0]["id"]
        br.set(mid, "claimed")
        ok("狀態：已取走", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '已取走'", 8000), _ch_status(pg, 0))
        ok("已取走：撤回鈕消失（不能再撤回）", not pg.query_selector("#chatList .c-msg:first-child [data-cancel]"))
        br.set(mid, "running")
        ok("狀態：執行中（有轉圈）", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '執行中' && !!document.querySelector('#chatList .c-msg .c-st .spin')", 8000), _ch_status(pg, 0))
        ph = wait_until(pg, "() => { const a = __world.state.agents.get('frontend-ui'); return a && a.phase !== 'idle' ? a.phase : null; }", 8000)
        ok("3D：執行中 → 那位同事進入派工（領任務／工作）", bool(ph), ph)
        ok("3D：名牌狀態字不是空的（領任務中／工作中）", bool(pg.evaluate("() => __world.statusOf(__world.chars.get('frontend-ui'))")))
        _ch_shot(pg, "chat_3_執行中.png")
        br.set(mid, "done", "已改好：頂列按鈕高度 36 → 44\nhttps://liguligu-puipui.com/office/world.html")
        ok("狀態：完成、顯示回覆", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '完成'", 8000) and "頂列按鈕高度" in pg.inner_text("#chatList .c-rp"), _ch_status(pg, 0))
        ok("回覆：網址可以點（新分頁開）", pg.evaluate("() => { const a = document.querySelector('#chatList .c-rp a'); return !!a && a.href.startsWith('https://liguligu-puipui.com/') && a.target === '_blank' && a.rel.includes('noopener'); }"))
        ok("頂列徽章：全部做完後數字消失", wait_until(pg, "() => document.getElementById('chatN').hidden", 6000))
        ok("3D：完成後同事有小慶祝（星星）", wait_until(pg, "() => window.__emo.includes('star')", 25000), pg.evaluate("() => window.__emo"))
        ok("3D：交件後同事回到閒置", wait_until(pg, "() => { const a = __world.state.agents.get('frontend-ui'); return !a || a.phase === 'idle'; }", 40000), pg.evaluate("() => __world.state.agents.get('frontend-ui')"))
        _ch_shot(pg, "chat_4_完成.png")
        ok("對話框：沒有禁用字", not _CH_BAD_RE.search(pg.inner_text("#chatPanel")) and not _CH_BAD_RE.search(pg.inner_text("#chatBtn")), _CH_BAD_RE.findall(pg.inner_text("#chatPanel")))
        # 失敗與重新整理後仍在
        br.set(br.msgs[1]["id"], "canceled")
        pg.click("#chatX")
        ok("關閉：× 鈕關掉對話框", not _ch_vis(pg, "#chatPanel"))
        # ⑤ 資訊卡帶入
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('smc-technical'))")
        ok("資訊卡：有「對他下指令」鈕", _ch_vis(pg, "#card [data-chat]") and "對他下指令" in pg.inner_text("#card [data-chat]"))
        _ch_shot(pg, "chat_5_資訊卡.png")
        pg.click("#card [data-chat]")
        ok("資訊卡：按下去對話框打開、資訊卡讓位、收件對象已是那位同事", _ch_vis(pg, "#chatPanel") and not _ch_vis(pg, "#card") and pg.input_value("#chatTo") == "smc-technical", pg.input_value("#chatTo"))
        pg.press("#chatText", "Escape")
        ok("Esc 可以關掉對話框", not _ch_vis(pg, "#chatPanel"))
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('ceo'))")
        ok("資訊卡（CEO）：「對 CEO 下指令」", "對 CEO 下指令" in pg.inner_text("#card [data-chat]"))
        pg.click("#card [data-chat]")
        ok("資訊卡（CEO）：收件對象帶入 CEO 分派", pg.input_value("#chatTo") == "ceo")
        ok("沒有主控台錯誤", not pg.errs, pg.errs[:3])
        # ⑦ 接入碼：頁面上與儲存裡都沒有
        stored = pg.evaluate("() => { try { return JSON.stringify(Object.assign({}, localStorage)); } catch (e) { return ''; } }")
        ok("接入碼：不在 localStorage、不在頁面文字", _CH_CODE not in stored and "aio_" not in pg.inner_text("body"), stored[:200])
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
        ok("手機：頂列預設收起時不佔位（跟區域、示範、整修一樣收在「更多」）", not _ch_vis(pg, "#chatBtn"))
        pg.tap("#moreBtn")
        ok("手機：按「更多」後「下指令」鈕看得到、夠大（高 ≥ 36）", _ch_vis(pg, "#chatBtn") and pg.evaluate("() => document.getElementById('chatBtn').getBoundingClientRect().height") >= 36)
        _ch_shot(pg, "chat_m0_頂列.png")
        pg.tap("#chatBtn")
        ok("手機：對話框全螢幕", _ch_vis(pg, "#chatPanel") and pg.evaluate("() => { const r = document.getElementById('chatPanel').getBoundingClientRect(); return r.width >= innerWidth - 1 && r.height >= innerHeight - 1; }"))
        wait_until(pg, "() => __world.chat.mode === 'ok'", 15000)
        pg.select_option("#chatTo", "mobile-ui")
        pg.tap("#chatText")
        pg.keyboard.type("手機版測試", delay=15)
        pg.tap("#chatSend")
        ok("手機：送出後列表出現「排隊中」", wait_until(pg, "() => document.querySelectorAll('#chatList .c-msg').length === 1", 8000) and _ch_status(pg) == "排隊中")
        _ch_shot(pg, "chat_m1_排隊中.png")
        br.set(br.msgs[0]["id"], "done", "手機測試回覆\nhttps://liguligu-puipui.com/")
        ok("手機：完成並顯示回覆", wait_until(pg, "() => document.querySelector('#chatList .c-msg .c-st').textContent.trim() === '完成'", 8000))
        _ch_shot(pg, "chat_m2_完成.png")
        info = pg.evaluate("""() => {
            const out = { hscroll: document.documentElement.scrollWidth > innerWidth + 1, small: [], tiny: [], over: [] };
            const P = document.getElementById('chatPanel'), pr = P.getBoundingClientRect();
            for (const e of P.querySelectorAll('*')) {
                const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
                const t = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).length;
                if (t && parseFloat(getComputedStyle(e).fontSize) < 11) out.small.push(e.tagName + ':' + e.textContent.trim().slice(0, 12));
                if (r.right > pr.right + 1 || r.left < pr.left - 1) out.over.push(e.tagName + '.' + e.className);
            }
            for (const e of P.querySelectorAll('button')) { const r = e.getBoundingClientRect(); if (r.width > 0 && (r.height < 30 || r.width < 30)) out.tiny.push(e.textContent.trim().slice(0, 8) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); }
            return out;
        }""")
        ok("手機：沒有橫向溢出、沒有東西超出對話框", not info["hscroll"] and not info["over"], info)
        ok("手機：字不小於 11px", not info["small"], info["small"][:3])
        ok("手機：按鈕夠大好按", not info["tiny"], info["tiny"])
        ok("手機：沒有禁用字", not _CH_BAD_RE.search(pg.inner_text("#chatPanel")))
        pg.tap("#chatX")
        ok("手機：× 關掉後回到辦公室", not _ch_vis(pg, "#chatPanel"))
        ok("手機：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _ch_all(b, base):
    for fn in (_ch_desktop, _ch_gates, _ch_code, _ch_mobile):
        try:
            fn(b, base)
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok("辦公室下指令：%s 中途爆掉" % fn.__name__, False, str(e)[:300])


register("辦公室下指令", lambda pg, b, base, code: _ch_all(b, base))
