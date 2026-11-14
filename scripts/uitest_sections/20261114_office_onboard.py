# 驗收段落「辦公室接入引導」：AI Office 3D 辦公室（site/office/world.html）頂列「連接我的 Claude」→ 三步驟引導面板
#   擁有者站在使用者角度的流程：① 複製提示詞（不含接入碼）貼到 Claude → ② Claude 跳出安全表單卡片時貼上接入碼 → ③ 收到第一筆事件顯示「已接上」
#   驗：三步驟與步驟條、提示詞全文與複製（真的寫進剪貼簿）、提示詞不含 aio_、接入碼預設遮罩（眼睛暫時顯示）、複製接入碼、
#       「我不小心外流了，換一組」真的換碼、模擬第一筆事件 → 已接上＋自動關閉＋切即時、尚未接上的醒目小點（接上後消失）、
#       非站長／沒登入 → 「目前只開放站長使用」、手機 390 全螢幕不重疊不溢出字不小於 11px、禁用字、無主控台錯誤。
# 收件端、會員 API 都用 page.route 模擬（https://aio.test、https://acct.test）。
# 環境變數 ONBOARD_SHOTS 指到資料夾時，順便存截圖。自成一格（函式名都加 _ob 前綴，不依賴別的段落）。
# flake8: noqa

import json as _json
import os as _os
import re as _re
import time as _time
from urllib.parse import urlparse as _up, parse_qs as _pq

_OB_AIO = "https://aio.test"
_OB_ACCT = "https://acct.test"
_OB_T0 = int(_time.time() * 1000)
_OB_BAD = ["價格", "NT$", "付費", "升級", "訂閱", "方案", "Plus", "免費", "右鍵"]
_OB_BAD_RE = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")


def _ob_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _ob_shot(pg, name):
    d = _os.environ.get("ONBOARD_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _ObFake:
    """假的收件端＋會員 API：接入碼可以被換掉；事件由測試手動加。"""

    def __init__(self, admin=True):
        self.admin, self.events, self.codes, self.claims = admin, [], [], []
        self.n_state = 0

    def add(self, **e):
        e.setdefault("seq", len(self.events) + 1)
        e.setdefault("rcv", _OB_T0 + e["seq"] * 1000)
        self.events.append(e)

    def new_code(self):
        c = "aio_Pp1" + "QrStUvWx%02d" % len(self.codes) + "0123456789abcdef"
        self.codes.append(c)
        return c

    def body(self, since):
        evs = [e for e in self.events if e["seq"] > since] if since else self.events[-60:]
        return {"office": "main", "now": _OB_T0, "seq": len(self.events), "since": since, "initial": since == 0, "total_events": len(self.events),
                "last_event_at": self.events[-1]["rcv"] if self.events else None, "projects": [], "sessions": [], "agents": [], "types": [],
                "ceo": {"sessions": 0, "prompts": 0, "turns": 0}, "quota": None, "events": evs}

    def handle(self, route):
        req = route.request
        h = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, content-type, x-aio-session", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"})
        u = _up(req.url)
        if u.path.endswith("/v1/me"):
            return route.fulfill(status=200, body=_json.dumps({"user": {"admin": self.admin}}), headers=h)
        if u.path.endswith("/v1/claim"):
            b = _json.loads(req.post_data or "{}")
            self.claims.append(b)
            if not self.admin:
                return route.fulfill(status=403, body='{"error":"not_owner"}', headers=h)
            return route.fulfill(status=200, body=_json.dumps({"ok": True, "office": "main", "code": self.new_code(), "created": _OB_T0, "rotated": bool(b.get("rotate"))}), headers=h)
        if u.path.endswith("/state"):
            self.n_state += 1
            auth = req.headers.get("authorization", "")
            if not self.codes or auth != "Bearer " + self.codes[-1]:
                return route.fulfill(status=401, body='{"error":"auth"}', headers=h)
            since = int((_pq(u.query).get("since") or ["0"])[0])
            return route.fulfill(status=200, body=_json.dumps(self.body(since)), headers=h)
        return route.fulfill(status=404, body="{}", headers=h)


def _ob_open(b, base, fake, tok=True, w=1280, h=800, touch=False, cfg=None):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch, permissions=["clipboard-read", "clipboard-write"])
    live = dict(cfg or {})
    live.setdefault("url", _OB_AIO)
    init = ("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('aiOffice.live.v1',%s);%s}catch(e){}window.TW_ACCOUNT={api:'%s'};"
            % (_json.dumps(_json.dumps(live)), "localStorage.setItem('tw.acct.tok','" + "T" * 40 + "');" if tok else "localStorage.removeItem('tw.acct.tok');", _OB_ACCT))
    c.add_init_script(init)
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.route(_OB_AIO + "/**", fake.handle)
    pg.route(_OB_ACCT + "/**", fake.handle)
    pg.goto(_ob_root(base) + "/office/world.html?ambient=0&q=low&pr=0.3&live_poll=700", wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.live", 90000)
    return c, pg, got


def _ob_shown(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && !e.hidden && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; }", sel)


def _ob_step(pg):
    return pg.evaluate("() => { const e = document.querySelector('#aioGs [aria-current=step]'); return e ? e.dataset.n : null; }")


def _ob_inter(a, b):
    return not (a[2] <= b[0] + 0.5 or b[2] <= a[0] + 0.5 or a[3] <= b[1] + 0.5 or b[3] <= a[1] + 0.5)


# ───────────────────────── ① 擁有者：三步驟走完 ─────────────────────────
def _ob_owner(b, base):
    f = _ObFake(admin=True)
    c, pg, got = _ob_open(b, base, f)
    try:
        ok("引導：辦公室頁載入完成", got)
        if not got:
            return
        ok("引導：尚未接上，頂列標章寫「連接我的 Claude」並有醒目小點", pg.evaluate("() => document.getElementById('aioBadge').classList.contains('hint')") and pg.evaluate("() => document.getElementById('aioTxt').textContent") == "連接我的 Claude")
        ok("引導：沒按之前引導是關著的", not _ob_shown(pg, "#aioGuide"))
        pg.click("#aioBadge")
        ok("引導：點標章打開引導面板（對話框）", _ob_shown(pg, "#aioGuide") and pg.get_attribute("#aioGuide .aio-gp", "role") == "dialog")
        ok("引導：步驟條三格（複製提示詞／貼上接入碼／確認接上）", pg.evaluate("() => [...document.querySelectorAll('#aioGs button span')].map(e => e.textContent)") == ["複製提示詞", "貼上接入碼", "確認接上"])
        ok("引導：目前在第 1 步", _ob_step(pg) == "1", _ob_step(pg))
        r = pg.evaluate("() => { const r = document.querySelector('#aioGuide .aio-gp').getBoundingClientRect(); return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2), innerWidth, innerHeight]; }")
        ok("引導：桌機置中對話框", abs(r[0] - r[2] / 2) <= 4 and abs(r[1] - r[3] / 2) <= 40, r)
        # ── 第 1 步：提示詞
        pr = pg.inner_text("#aioPrompt")
        ok("第 1 步：顯示提示詞全文（可捲動的區塊）", len(pr) > 300 and pg.evaluate("() => getComputedStyle(document.getElementById('aioPrompt')).overflowY") in ("auto", "scroll"), len(pr))
        ok("第 1 步：提示詞不含 aio_（接入碼不進聊天室）", "aio_" not in pr and "aio_" not in pg.evaluate("() => document.getElementById('aioPrompt').textContent"))
        ok("第 1 步：提示詞帶入實際收件端主機", "aio.test" in pr and "{HOST}" not in pr, pr[:80])
        ok("第 1 步：提示詞寫清楚安全表單、標頭、前綴、名稱", all(k in pr for k in ["安全表單", "Authorization", "Bearer", "AI 辦公室接入碼", "不要請我把接入碼貼在聊天室"]), pr[:200])
        ok("第 1 步：提示詞引用公開儲存庫的安裝腳本、並要求先逐行跑過、送測試事件", all(k in pr for k in ["github.com/MiaoZiKe/tw-rotation", "install_hooks.py", "設定腳本", "測試事件", "繁體中文"]))
        ok("第 1 步：「打開 Claude」連結＝claude.ai/code、新分頁", pg.evaluate("() => { const a = [...document.querySelectorAll('#aioGb a')].find(x => x.textContent.trim() === '打開 Claude'); return !!a && a.href === 'https://claude.ai/code' && a.target === '_blank' && /noopener/.test(a.rel); }"))
        ok("第 1 步：操作圖片版位（沒有圖片時灰底框寫「操作圖片將於實測後補上」）", "操作圖片將於實測後補上" in pg.inner_text("#aioGb") and pg.evaluate("() => !!document.querySelector('#aioGb figure[data-shot=\"s1_copy.png\"]')"))
        pg.click("#aioGb [data-a=cpprompt]")
        ok("第 1 步：按「複製提示詞」→ 提示詞真的寫進剪貼簿", wait_until(pg, "() => navigator.clipboard.readText().then(t => t.length > 300 && t.includes('aio.test') && !t.includes('aio_')).catch(() => false)", 5000))
        ok("第 1 步：複製後顯示「已複製」", "已複製" in pg.inner_text("#aioGb"))
        _ob_shot(pg, "d1_第1步_複製提示詞.png")
        # ── 第 2 步：產生並遮罩接入碼
        pg.click("#aioGf [data-a=gnext]")
        ok("第 2 步：下一步 → 第 2 步", _ob_step(pg) == "2")
        ok("第 2 步：還沒產生時只有「產生接入碼」鈕，沒有接入碼", pg.locator("#aioGb [data-a=claim]").count() == 1 and pg.locator("#aioCodeMask").count() == 0)
        ok("第 2 步：說明卡片長相與要按的鈕（值那一格貼上、按儲存）", all(k in pg.inner_text("#aioGb") for k in ["安全表單", "值", "儲存"]))
        _ob_shot(pg, "d2a_第2步_產生前.png")
        pg.click("#aioGb [data-a=claim]")
        ok("第 2 步：按「產生接入碼」→ 呼叫收件端領碼", wait_until(pg, "() => !!document.getElementById('aioCodeMask')", 10000) and len(f.claims) == 1, f.claims)
        code1 = f.codes[-1]
        mask = pg.inner_text("#aioCodeMask")
        ok("第 2 步：接入碼預設遮罩，只露前 7 碼「aio_Pp1…（已隱藏）」", mask == "aio_Pp1…（已隱藏）" and code1 not in pg.inner_text("#aioGuide"), mask)
        ok("第 2 步：接入碼存進這台裝置（即時模式讀得到）", pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.live.v1') || '{}').code") == code1)
        pg.click("#aioGb [data-a=eye]")
        ok("第 2 步：按眼睛 → 暫時顯示完整接入碼", pg.inner_text("#aioCodeMask") == code1 and pg.get_attribute("#aioGb [data-a=eye]", "aria-pressed") == "true")
        pg.click("#aioGb [data-a=eye]")
        ok("第 2 步：再按一次 → 又遮起來", pg.inner_text("#aioCodeMask") == mask)
        pg.click("#aioGb [data-a=cpcode]")
        ok("第 2 步：按「複製接入碼」→ 真的寫進剪貼簿", wait_until(pg, "(c) => navigator.clipboard.readText().then(t => t === c).catch(() => false)", 5000) if False else pg.evaluate("(c) => navigator.clipboard.readText().then(t => t === c)", code1))
        ok("第 2 步：複製後畫面仍是遮罩", pg.inner_text("#aioCodeMask") == mask)
        ok("第 2 步：「我不小心外流了，換一組」鈕顯眼地在畫面上", _ob_shown(pg, "#aioGb [data-a=rotate]") and "我不小心外流了，換一組" in pg.inner_text("#aioGb"))
        _ob_shot(pg, "d2b_第2步_接入碼遮罩.png")
        pg.click("#aioGb [data-a=rotate]")
        ok("第 2 步：按「換一組」→ 產生新的接入碼（rotate）、舊的失效", wait_until(pg, "() => JSON.parse(localStorage.getItem('aiOffice.live.v1') || '{}').code !== %s" % _json.dumps(code1), 10000) and f.claims[-1].get("rotate") is True and len(f.codes) == 2, f.claims)
        code2 = f.codes[-1]
        ok("第 2 步：換碼後畫面仍是遮罩、新碼已存", pg.inner_text("#aioCodeMask") == "aio_Pp1…（已隱藏）" and pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.live.v1')).code") == code2)
        # ── 第 3 步：等第一筆回報
        pg.click("#aioGf [data-a=gnext]")
        ok("第 3 步：下一步 → 第 3 步，顯示「等待第一筆回報…」", _ob_step(pg) == "3" and "等待第一筆回報…" in pg.inner_text("#aioGb"))
        ok("第 3 步：已切到即時模式（讀得到收件端）、尚未收到回報", wait_until(pg, "() => __world.live.mode === 'live' && __world.live.status === 'nodata'", 15000), pg.evaluate("() => [__world.live.mode, __world.live.status]"))
        pg.click("#aioGb details summary")
        ok("第 3 步：「沒反應怎麼辦」排除清單至少 4 項", pg.locator("#aioFix li").count() >= 4 and "新的" in pg.inner_text("#aioFix"))
        ok("第 3 步：沒收到之前標章還有醒目小點、引導沒自動關", pg.evaluate("() => document.getElementById('aioBadge').classList.contains('hint')") and _ob_shown(pg, "#aioGuide"))
        _ob_shot(pg, "d3a_第3步_等待.png")
        f.add(event="SessionStart", session_id="aio-test")
        ok("第 3 步：收件端收到第一筆事件 → 顯示「已接上 ✓，你的辦公室正在即時更新」", wait_until(pg, "() => document.getElementById('aioGb').innerText.includes('已接上 ✓，你的辦公室正在即時更新')", 15000), pg.inner_text("#aioGb")[:80])
        ok("第 3 步：步驟條三格都打勾", pg.evaluate("() => document.querySelectorAll('#aioGs .ok').length === 3"))
        _ob_shot(pg, "d3b_第3步_已接上.png")
        ok("第 3 步：已接上後自動關閉引導", wait_until(pg, "() => document.getElementById('aioGuide').hidden", 8000))
        ok("已接上：辦公室是即時模式、標章「即時・最後更新 HH:MM」、醒目小點消失", pg.evaluate("() => __world.live.mode") == "live" and bool(_re.fullmatch(r"即時・最後更新 \d\d:\d\d", pg.evaluate("() => document.getElementById('aioTxt').textContent"))) and not pg.evaluate("() => document.getElementById('aioBadge').classList.contains('hint')"))
        pg.click("#aioBadge")
        ok("已接上：再點標章是原本的即時說明框（不再跳引導）", _ob_shown(pg, "#aioPop") and not _ob_shown(pg, "#aioGuide") and "我不小心外流了，換一組" in pg.inner_text("#aioPop"))
        allt = pg.inner_text("#aioPop")
        ok("引導：沒有禁用字", not _OB_BAD_RE.search(allt), _OB_BAD_RE.findall(allt))
        ok("引導：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ② 非站長／沒登入：只開放站長 ─────────────────────────
def _ob_notowner(b, base):
    for label, admin, tok in (("一般登入使用者", False, True), ("沒登入", True, False)):
        f = _ObFake(admin=admin)
        c, pg, got = _ob_open(b, base, f, tok=tok)
        try:
            ok("非站長（%s）：載入完成" % label, got)
            if not got:
                continue
            pg.click("#aioBadge")
            pg.click("#aioGf [data-a=gnext]")
            ok("非站長（%s）：第 2 步顯示「目前只開放站長使用，之後開放」" % label, wait_until(pg, "() => document.getElementById('aioGb').innerText.includes('目前只開放站長使用，之後開放')", 8000), pg.inner_text("#aioGb")[:100])
            ok("非站長（%s）：沒有「產生接入碼」鈕、沒有壞掉的按鈕" % label, pg.locator("#aioGb [data-a=claim]").count() == 0 and pg.locator("#aioGb [data-a=cpcode]").count() == 0 and not f.claims, f.claims)
            pg.click("#aioGf [data-a=gprev]")
            ok("非站長（%s）：第 1 步提示詞仍看得到、不含接入碼" % label, _ob_step(pg) == "1" and len(pg.inner_text("#aioPrompt")) > 300 and "aio_" not in pg.inner_text("#aioPrompt"))
            _ob_shot(pg, "d4_非站長_%s.png" % label)
            ok("非站長（%s）：沒有主控台錯誤" % label, not pg.errs, pg.errs[:3])
        finally:
            c.close()
    # 一般登入的人若手動按領碼被擋（查不到身分時的保底）：收件端回 403 not_owner → 也顯示只開放站長
    f = _ObFake(admin=False)
    c, pg, got = _ob_open(b, base, f)
    try:
        if got:
            pg.evaluate("() => { window.TW_ACCOUNT = { api: '' }; }")
            pg.click("#aioBadge")
            pg.click("#aioGf [data-a=gnext]")
            if pg.locator("#aioGb [data-a=claim]").count():
                pg.click("#aioGb [data-a=claim]")
            ok("非站長：被收件端擋下（403）→ 改顯示「目前只開放站長使用」", wait_until(pg, "() => document.getElementById('aioGb').innerText.includes('目前只開放站長使用，之後開放')", 8000))
    finally:
        c.close()


# ───────────────────────── ③ 手機 390：全螢幕、不重疊、字夠大 ─────────────────────────
def _ob_mobile(b, base):
    f = _ObFake(admin=True)
    c, pg, got = _ob_open(b, base, f, w=390, h=844, touch=True)
    try:
        ok("手機：載入完成", got)
        if not got:
            return
        ok("手機：頂列標章有醒目小點", pg.evaluate("() => document.getElementById('aioBadge').classList.contains('hint')"))
        pg.tap("#aioBadge")
        ok("手機：引導面板開啟", _ob_shown(pg, "#aioGuide"))
        r = pg.evaluate("() => { const r = document.querySelector('#aioGuide .aio-gp').getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; }")
        ok("手機：全螢幕抽屜（寬 390、高＝視窗）", r[0] == 0 and r[1] == 0 and r[2] == 390 and r[3] >= 840, r)
        for n in (1, 2, 3):
            if n == 2:
                pg.tap("#aioGf [data-a=gnext]")
                pg.tap("#aioGb [data-a=claim]")
                wait_until(pg, "() => !!document.getElementById('aioCodeMask')", 8000)
            if n == 3:
                pg.tap("#aioGf [data-a=gnext]")
                wait_until(pg, "() => document.getElementById('aioGb').innerText.includes('等待第一筆回報…')", 8000)
            pg.wait_for_timeout(250)
            _ob_shot(pg, "m%d_手機第%d步.png" % (n, n))
            res = pg.evaluate("""() => {
              const g = document.querySelector('#aioGuide .aio-gp'), gb = document.getElementById('aioGb'), out = { small: [], over: [], hs: document.documentElement.scrollWidth > innerWidth || gb.scrollWidth > gb.clientWidth + 1, pairs: [] };
              const walker = document.createTreeWalker(g, NodeFilter.SHOW_TEXT);
              while (walker.nextNode()) { const t = walker.currentNode; if (!t.textContent.trim()) continue; const el = t.parentElement; const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue; if (parseFloat(cs.fontSize) < 11) out.small.push(el.tagName + ':' + t.textContent.trim().slice(0, 12)); }
              const R = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
              const blocks = [...document.querySelectorAll('#aioGs li, #aioGb > *, #aioGf > *')].filter(e => e.getBoundingClientRect().width > 0 && e.tagName !== 'DETAILS').map(e => [e.className || e.tagName, R(e)]);
              const gbR = R(gb), gfR = R(document.getElementById('aioGf'));
              for (const [n, r] of blocks) { if (r[0] < -0.5 || r[2] > innerWidth + 0.5) out.over.push(n); }
              out.blocks = blocks; out.gb = gbR; out.gf = gfR; out.gs = R(document.getElementById('aioGs'));
              return out; }""")
            ok("手機第 %d 步：沒有橫向捲軸、內容沒超出螢幕" % n, not res["hs"] and not res["over"], res["over"])
            ok("手機第 %d 步：所有文字 ≥ 11px" % n, not res["small"], res["small"][:4])
            bl = res["blocks"]
            bad = [(bl[i][0], bl[j][0]) for i in range(len(bl)) for j in range(i + 1, len(bl)) if _ob_inter(bl[i][1], bl[j][1]) and not (bl[i][0].startswith("aio-mask") or bl[j][0].startswith("aio-mask"))]
            # 內容區（可捲動）與頁尾、步驟條不重疊
            bad += [("gb/gf", "")] if _ob_inter(res["gb"], res["gf"]) else []
            bad += [("gs/gb", "")] if _ob_inter(res["gs"], res["gb"]) else []
            ok("手機第 %d 步：步驟條／內容／按鈕列兩兩不重疊" % n, not bad, bad[:3])
            tall = pg.evaluate("() => [...document.querySelectorAll('#aioGuide button, #aioGuide a.btn')].filter(e => e.getBoundingClientRect().width > 0 && !e.classList.contains('aio-gx')).map(e => [e.textContent.trim().slice(0, 8), Math.round(e.getBoundingClientRect().height)]).filter(x => x[1] < 36)")
            ok("手機第 %d 步：按鈕夠大好按（高 ≥ 36）" % n, not tall, tall)
        f.add(event="SessionStart", session_id="aio-test")
        ok("手機：收到第一筆事件 → 顯示已接上並自動關閉", wait_until(pg, "() => document.getElementById('aioGuide').hidden", 14000))
        _ob_shot(pg, "m4_手機_已接上關閉後.png")
        ok("手機：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _ob_all(b, base):
    for fn in (_ob_owner, _ob_notowner, _ob_mobile):
        try:
            fn(b, base)
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok("辦公室接入引導：%s 中途爆掉" % fn.__name__, False, str(e)[:300])


register("辦公室接入引導", lambda pg, b, base, code: _ob_all(b, base))
