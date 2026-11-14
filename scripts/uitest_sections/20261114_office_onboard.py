# 驗收段落「辦公室接入引導」：AI Office 3D 辦公室（site/office/world.html）頂列「連接我的 Claude」→ 一個畫面、兩個動作的引導
#   ① 複製提示詞（不含接入碼）貼到 Claude　② Claude 跳出表單時貼接入碼（沒有就自動產生、一律遮罩）　底下一行狀態，收到第一筆事件顯示「已接上」
#   驗：沒有步驟條與下一步／上一步、兩張並排卡（手機上下排）、提示詞預設收起、兩個複製鈕真的寫進剪貼簿、接入碼自動產生且遮罩、
#       提示詞不含 aio_、換一組真的換碼、模擬第一筆事件 → 已接上＋自動關閉＋切即時、尚未接上的醒目小點、
#       非站長／沒登入 → ②卡「目前只開放站長使用」且無按鈕、手機 390 不重疊不溢出字不小於 11px、禁用字、無主控台錯誤。
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


def _ob_inter(a, b):
    return not (a[2] <= b[0] + 0.5 or b[2] <= a[0] + 0.5 or a[3] <= b[1] + 0.5 or b[3] <= a[1] + 0.5)


# ───────────────────────── ① 擁有者：一個畫面、兩個動作 ─────────────────────────
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
        ok("引導：點標章打開引導面板（對話框）、標題「連接我的 Claude」", _ob_shown(pg, "#aioGuide") and pg.get_attribute("#aioGuide .aio-gp", "role") == "dialog" and pg.inner_text("#aioGt") == "連接我的 Claude")
        ok("引導：一個畫面——沒有步驟條、沒有下一步／上一步", pg.locator("#aioGs, .aio-steps, [data-a=gnext], [data-a=gprev], [data-a=gstep]").count() == 0)
        ok("引導：只有兩張卡（① 複製這段，貼到 Claude／② Claude 跳出表單時，貼這個）", pg.evaluate("() => [...document.querySelectorAll('#aioGb .aio-card h4')].map(e => e.textContent)") == ["① 複製這段，貼到 Claude", "② Claude 跳出表單時，貼這個"])
        r = pg.evaluate("() => { const a = document.getElementById('aioC1').getBoundingClientRect(), b = document.getElementById('aioC2').getBoundingClientRect(); return [a.right, b.left, a.top, b.top, a.width, b.width]; }")
        ok("引導：桌機兩張卡並排（左右、同高度）", r[0] <= r[1] + 1 and abs(r[2] - r[3]) < 2, r)
        ok("引導：狀態一行「等待你的 Claude 回報…」", "等待你的 Claude 回報…" in pg.inner_text("#aioStat"))
        ok("引導：提示詞預設收起", pg.locator("#aioPrompt").count() == 0)
        ok("引導：每張卡一個操作圖片版位（沒圖片時只留一行小字、不佔灰框）", pg.locator("#aioGb [data-shot]").count() == 2 and pg.locator("#aioGb .aio-shot, #aioGb figure, #aioGb img").count() == 0)
        ok("引導：「打開 Claude」連結＝claude.ai/code、新分頁", pg.evaluate("() => { const a = [...document.querySelectorAll('#aioC1 a')].find(x => x.textContent.trim() === '打開 Claude'); return !!a && a.href === 'https://claude.ai/code' && a.target === '_blank' && /noopener/.test(a.rel); }"))
        ok("引導：「遇到問題？」預設收起", pg.evaluate("() => !document.getElementById('aioHelp').open"))
        # ── ① 提示詞
        pg.click("#aioC1 [data-a=viewp]")
        pr = pg.inner_text("#aioPrompt")
        ok("① ：點「看內容」展開提示詞全文（可捲動）", len(pr) > 300 and pg.evaluate("() => getComputedStyle(document.getElementById('aioPrompt')).overflowY") in ("auto", "scroll"), len(pr))
        ok("① ：提示詞不含 aio_（接入碼不進聊天室）", "aio_" not in pr and "aio_" not in pg.evaluate("() => document.getElementById('aioPrompt').textContent"))
        ok("① ：提示詞帶入收件端主機、寫清楚安全表單／標頭／前綴／名稱", "aio.test" in pr and "{HOST}" not in pr and all(k in pr for k in ["安全表單", "Authorization", "Bearer", "AI 辦公室接入碼", "不要請我把接入碼貼在聊天室"]), pr[:120])
        ok("① ：提示詞引用公開儲存庫安裝腳本、先逐行跑過、送測試事件、繁體中文", all(k in pr for k in ["github.com/MiaoZiKe/tw-rotation", "install_hooks.py", "設定腳本", "測試事件", "繁體中文"]))
        pg.click("#aioC1 [data-a=viewp]")
        ok("① ：再點一次「收起內容」收起", pg.locator("#aioPrompt").count() == 0)
        pg.click("#aioC1 [data-a=cpprompt]")
        ok("① ：按「複製提示詞」→ 提示詞真的寫進剪貼簿（不含 aio_）", wait_until(pg, "() => navigator.clipboard.readText().then(t => t.length > 300 && t.includes('aio.test') && !t.includes('aio_') && t.includes('第 3 步')).catch(() => false)", 5000))
        ok("① ：複製後顯示「已複製」", "已複製" in pg.inner_text("#aioC1"))
        # ── ② 接入碼：自動產生、一律遮罩
        ok("② ：還沒產生時沒有接入碼、也沒有另外的「產生」鈕", pg.locator("#aioCodeMask").count() == 0 and pg.locator("[data-a=claim]").count() == 0 and not f.claims)
        _ob_shot(pg, "d1_桌機_複製前.png")
        pg.click("#aioC2 [data-a=cpcode]")
        ok("② ：按「複製接入碼」→ 自動向收件端領碼（不是換碼）", wait_until(pg, "() => !!document.getElementById('aioCodeMask')", 10000) and len(f.claims) == 1 and not f.claims[0].get("rotate"), f.claims)
        code1 = f.codes[-1]
        ok("② ：接入碼遮罩，只露前 7 碼「aio_Pp1…（已隱藏）」、畫面上沒有完整碼", pg.inner_text("#aioCodeMask") == "aio_Pp1…（已隱藏）" and code1 not in pg.inner_text("#aioGuide"), pg.inner_text("#aioCodeMask"))
        ok("② ：領到的碼真的寫進剪貼簿", wait_until(pg, "() => navigator.clipboard.readText().then(t => t === %s).catch(() => false)" % _json.dumps(code1), 5000))
        ok("② ：碼存進這台裝置、辦公室切到即時（等回報）", wait_until(pg, "() => __world.live.mode === 'live' && __world.live.status === 'nodata'", 15000) and pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.live.v1') || '{}').code") == code1)
        ok("② ：「不小心外流？換一組」小字連結在畫面上", _ob_shown(pg, "#aioC2 [data-a=rotate]") and "不小心外流？換一組" in pg.inner_text("#aioC2"))
        _ob_shot(pg, "d2_桌機_接入碼已遮罩.png")
        pg.click("#aioC2 [data-a=rotate]")
        ok("② ：按「換一組」→ 產生新碼（rotate）、舊的失效、仍是遮罩", wait_until(pg, "() => JSON.parse(localStorage.getItem('aiOffice.live.v1') || '{}').code !== %s" % _json.dumps(code1), 10000) and f.claims[-1].get("rotate") is True and len(f.codes) == 2 and pg.inner_text("#aioCodeMask") == "aio_Pp1…（已隱藏）", f.claims)
        code2 = f.codes[-1]
        pg.click("#aioC2 [data-a=cpcode]")
        ok("② ：已有碼時再按「複製接入碼」只複製、不再領碼", wait_until(pg, "() => navigator.clipboard.readText().then(t => t === %s).catch(() => false)" % _json.dumps(code2), 5000) and len(f.claims) == 2, f.claims)
        # ── 遇到問題？
        pg.click("#aioHelp summary")
        ok("「遇到問題？」展開：排除清單至少 4 項、有進階網址與接入碼輸入", pg.locator("#aioFix li").count() >= 4 and "新的" in pg.inner_text("#aioFix") and _ob_shown(pg, "#aioUrl") and _ob_shown(pg, "#aioIn"))
        ok("尚未收到回報：標章還有醒目小點、引導沒自動關", pg.evaluate("() => document.getElementById('aioBadge').classList.contains('hint')") and _ob_shown(pg, "#aioGuide"))
        f.add(event="SessionStart", session_id="aio-test")
        ok("收到第一筆事件 → 狀態變「已接上 ✓，你的辦公室正在即時更新」", wait_until(pg, "() => document.getElementById('aioStat') && document.getElementById('aioStat').innerText.includes('已接上 ✓，你的辦公室正在即時更新')", 15000))
        _ob_shot(pg, "d3_桌機_已接上.png")
        ok("已接上後自動關閉引導", wait_until(pg, "() => document.getElementById('aioGuide').hidden", 8000))
        ok("已接上：即時模式、標章「即時・最後更新 HH:MM」、醒目小點消失", pg.evaluate("() => __world.live.mode") == "live" and bool(_re.fullmatch(r"即時・最後更新 \d\d:\d\d", pg.evaluate("() => document.getElementById('aioTxt').textContent"))) and not pg.evaluate("() => document.getElementById('aioBadge').classList.contains('hint')"))
        pg.click("#aioBadge")
        ok("已接上：再點標章是原本的即時說明框（不再跳引導）", _ob_shown(pg, "#aioPop") and not _ob_shown(pg, "#aioGuide"))
        allt = pg.inner_text("#aioPop")
        ok("引導：沒有禁用字", not _OB_BAD_RE.search(allt), _OB_BAD_RE.findall(allt))
        # 換碼瞬間可能有一個舊碼的讀取還在路上，收件端回 401 是預期的（畫面會自己重讀），瀏覽器會記一行資源錯誤，這裡不算
        errs = [e for e in pg.errs if "401" not in e]
        ok("引導：沒有主控台錯誤（換碼瞬間的 401 除外）", not errs, errs[:3])
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
            ok("非站長（%s）：②卡顯示「目前只開放站長使用」" % label, wait_until(pg, "() => document.getElementById('aioC2').innerText.includes('目前只開放站長使用')", 8000), pg.inner_text("#aioC2")[:100])
            ok("非站長（%s）：②卡沒有任何按鈕、沒有領碼請求" % label, pg.locator("#aioC2 button").count() == 0 and not f.claims, f.claims)
            pg.click("#aioC1 [data-a=viewp]")
            ok("非站長（%s）：①卡提示詞仍看得到、不含接入碼" % label, len(pg.inner_text("#aioPrompt")) > 300 and "aio_" not in pg.inner_text("#aioPrompt"))
            _ob_shot(pg, "d4_非站長_%s.png" % label)
            ok("非站長（%s）：沒有主控台錯誤" % label, not pg.errs, pg.errs[:3])
        finally:
            c.close()
    # 查不到身分時的保底：按「複製接入碼」被收件端擋下（403 not_owner）→ ②卡改顯示只開放站長、按鈕消失
    f = _ObFake(admin=False)
    c, pg, got = _ob_open(b, base, f)
    try:
        if got:
            pg.evaluate("() => { window.TW_ACCOUNT = { api: '' }; }")
            pg.click("#aioBadge")
            if pg.locator("#aioC2 [data-a=cpcode]").count():
                pg.click("#aioC2 [data-a=cpcode]")
            ok("非站長：被收件端擋下（403）→ ②卡改顯示「目前只開放站長使用」、沒有按鈕", wait_until(pg, "() => document.getElementById('aioC2').innerText.includes('目前只開放站長使用') && !document.querySelector('#aioC2 button')", 8000))
    finally:
        c.close()


# ───────────────────────── ③ 手機 390：全螢幕、卡片上下排、不重疊、字夠大 ─────────────────────────
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
        r = pg.evaluate("() => { const a = document.getElementById('aioC1').getBoundingClientRect(), b = document.getElementById('aioC2').getBoundingClientRect(); return [a.bottom, b.top, a.left, b.left]; }")
        ok("手機：兩張卡上下排", r[0] <= r[1] + 1 and abs(r[2] - r[3]) < 2, r)
        ok("手機：第一屏就看得到兩顆複製鈕與狀態（不用捲）", pg.evaluate("() => ['#aioC1 [data-a=cpprompt]', '#aioC2 [data-a=cpcode]', '#aioStat'].every(s => { const r = document.querySelector(s).getBoundingClientRect(); return r.bottom <= innerHeight && r.top >= 0; })"))
        pg.tap("#aioC2 [data-a=cpcode]")
        wait_until(pg, "() => !!document.getElementById('aioCodeMask')", 8000)
        pg.tap("#aioC1 [data-a=viewp]")
        pg.tap("#aioHelp summary")
        pg.wait_for_timeout(300)
        _ob_shot(pg, "m1_手機_展開全部.png")
        pg.tap("#aioC1 [data-a=viewp]")
        pg.tap("#aioHelp summary")
        pg.wait_for_timeout(300)
        _ob_shot(pg, "m2_手機_預設.png")
        res = pg.evaluate("""() => {
          const g = document.querySelector('#aioGuide .aio-gp'), gb = document.getElementById('aioGb'), out = { small: [], over: [], hs: document.documentElement.scrollWidth > innerWidth || gb.scrollWidth > gb.clientWidth + 1 };
          const walker = document.createTreeWalker(g, NodeFilter.SHOW_TEXT);
          while (walker.nextNode()) { const t = walker.currentNode; if (!t.textContent.trim()) continue; const el = t.parentElement; const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue; if (parseFloat(cs.fontSize) < 11) out.small.push(el.tagName + ':' + t.textContent.trim().slice(0, 12)); }
          const R = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
          out.blocks = [...gb.children].filter(e => e.getBoundingClientRect().width > 0).map(e => [e.id || e.className || e.tagName, R(e)]);
          out.inner = [];
          for (const card of document.querySelectorAll('.aio-card')) { const k = [...card.children].filter(e => e.getBoundingClientRect().width > 0).map(e => [e.tagName + '.' + (e.className || ''), R(e)]); out.inner.push(k); }
          out.over = [...g.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.left < -0.5 || r.right > innerWidth + 0.5); }).map(e => e.tagName + '.' + e.className).slice(0, 4);
          return out; }""")
        ok("手機：沒有橫向捲軸、內容沒超出螢幕", not res["hs"] and not res["over"], res["over"])
        ok("手機：所有文字 ≥ 11px", not res["small"], res["small"][:4])
        bl = res["blocks"]
        bad = [(bl[i][0], bl[j][0]) for i in range(len(bl)) for j in range(i + 1, len(bl)) if _ob_inter(bl[i][1], bl[j][1])]
        for k in res["inner"]:
            bad += [(k[i][0], k[j][0]) for i in range(len(k)) for j in range(i + 1, len(k)) if _ob_inter(k[i][1], k[j][1])]
        ok("手機：卡片、狀態、摺疊區兩兩不重疊（卡內元素也不重疊）", not bad, bad[:3])
        tall = pg.evaluate("() => [...document.querySelectorAll('#aioGuide .btn')].filter(e => e.getBoundingClientRect().width > 0).map(e => [e.textContent.trim().slice(0, 8), Math.round(e.getBoundingClientRect().height)]).filter(x => x[1] < 36)")
        ok("手機：按鈕夠大好按（高 ≥ 36）", not tall, tall)
        f.add(event="SessionStart", session_id="aio-test")
        ok("手機：收到第一筆事件 → 顯示已接上並自動關閉", wait_until(pg, "() => document.getElementById('aioGuide').hidden", 14000))
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
