# 驗收段落「辦公室多專案」：一個專案一間辦公室（docs/ai_office/plan.md 最後一節「實際接上後發現的問題」）
#   ① 入口：「你的專案」清單列出每個專案的名稱、最後活動、進行中工作階段數；名稱是 user 的顯示「雲端工作階段」；點「進入」才進辦公室，網址帶 office 與 project
#   ② 辦公室頁：只看到該專案的角色（別的專案的子 Agent 不會出現、只有該專案的分身）；CEO 名牌「tw-rotation CEO」、分身名牌「tw-rotation CEO（分身 2）」、
#      「CEO 辦公室」門牌改成「tw-rotation CEO 辦公室」；user 專案的名牌寫「雲端工作階段 CEO」
#   ③ 左上角「← 專案名 ▾」：← 回入口並自動打開專案清單；▾ 打開下拉、點另一個專案 → 換成那個專案的角色與名牌；「?」另外放、照樣能開
#   ④ 辦公室清單讀伺服器：建立（伺服器擋 3 間）、改名、綁定專案（進入時只列綁定的）、移除；伺服器連不上時退回暫存並寫明
#   ⑤ 手機 390×844：入口專案清單、辦公室左上角「← 專案名 ▾」沒有橫向溢出、按鈕不小於 40px、字不小於 11px、下拉在畫面內；畫面沒有禁用字
# 收件端用 page.route 模擬（https://aio.test），回應格式與 workers/ai-office-bridge/worker.js 一致（含 ?project= 過濾）。環境變數 PROJ_SHOTS 指到資料夾時順便存截圖。
# flake8: noqa

import json as _json
import os as _os
import re as _re
import time as _time
from urllib.parse import urlparse as _up, parse_qs as _pq

_PX_AIO = "https://aio.test"
_PX_T0 = int(_time.time() * 1000)
_PA, _PB, _PU = "aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb", "cccccccccccccccc"
_PX_BAD = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")
_PX_CORS = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}


def _px_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _px_shot(pg, name):
    d = _os.environ.get("PROJ_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


class _PxFake:
    """假的收件端：專案清單、依 project 過濾的 state、辦公室清單（上限 3 間）。"""

    def __init__(self):
        self.offices, self.limit, self.down = [], 3, False
        self.state_urls, self.n = [], 0
        mk = lambda sid, ph, nm, dt: {"id": sid, "project_hash": ph, "project_name": nm, "cloud": True, "started": _PX_T0, "last": _PX_T0 + dt, "ended": None, "state": "working", "flag": None, "perm": None, "prompts": 1, "turns": 0, "summary": None, "tokens": None}
        self.sessions = [mk("sa1", _PA, "tw-rotation", 5000), mk("sa2", _PA, "tw-rotation", 4000), mk("sb1", _PB, "other-repo", 3000), mk("su1", _PU, "user", 2000)]
        ag = lambda aid, sid, ph, ty: {"agent_id": aid, "session_id": sid, "project_hash": ph, "agent_type": ty, "description": "做事", "started": _PX_T0, "last": _PX_T0 + 4000, "ended": None, "status": "running", "tool": "other"}
        self.agents = [ag("a1", "sa1", _PA, "general-purpose"), ag("b1", "sb1", _PB, "zz-agent-b"), ag("u1", "su1", _PU, "zz-agent-u")]
        self.events = [{"seq": i + 1, "rcv": _PX_T0 + i * 1000, "event": "SessionStart", "session_id": s["id"], "project_hash": s["project_hash"]} for i, s in enumerate(self.sessions)]

    def projects(self):
        names = {_PA: "tw-rotation", _PB: "other-repo", _PU: "user"}
        out = []
        for ph, nm in names.items():
            ss = [s for s in self.sessions if s["project_hash"] == ph]
            out.append({"hash": ph, "name": nm, "first": _PX_T0, "last": max(s["last"] for s in ss), "events": 3, "active": len([s for s in ss if not s["ended"]])})
        return out

    def state(self, q):
        pj = (q.get("project") or [None])[0]
        flt = lambda l, k: [x for x in l if not pj or x.get(k) == pj]
        since = int((q.get("since") or ["0"])[0])
        evs = [e for e in flt(self.events, "project_hash") if e["seq"] > since]
        ss, ag = flt(self.sessions, "project_hash"), flt(self.agents, "project_hash")
        return {"office": "main", "now": _PX_T0, "seq": len(self.events), "since": since, "initial": since == 0, "total_events": len(evs), "last_event_at": _PX_T0, "project": pj, "agents_capped": 0,
                "projects": self.projects(), "sessions": ss, "agents": ag, "types": [], "ceo": {"sessions": len(ss), "prompts": 1, "turns": 0}, "quota": None, "events": evs}

    def handle(self, route):
        req = route.request
        h = dict(_PX_CORS)
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={**h, "Access-Control-Allow-Headers": "authorization, content-type, x-aio-session", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"})
        u = _up(req.url)
        self.n += 1
        if self.down:
            return route.fulfill(status=503, body='{"error":"down"}', headers=h)
        if req.headers.get("x-aio-session") != "tok-test":
            return route.fulfill(status=401, body='{"error":"auth"}', headers=h)
        ok_ = lambda o, s=200: route.fulfill(status=s, body=_json.dumps(o), headers=h)
        p, body = u.path, {}
        try:
            body = _json.loads(req.post_data or "{}")
        except Exception:
            body = {}
        if p == "/v1/office/main/projects":
            return ok_({"office": "main", "now": _PX_T0, "projects": self.projects()})
        if p == "/v1/office/main/state":
            self.state_urls.append(req.url)
            return ok_(self.state(_pq(u.query)))
        if p == "/v1/offices" and req.method == "GET":
            return ok_({"offices": self.offices, "limits": {"max": self.limit, "agents": 5}, "admin": False})
        if p == "/v1/offices" and req.method == "POST":
            if len(self.offices) >= self.limit:
                return ok_({"error": "office_limit", "max": self.limit}, 409)
            if any(o["name"] == body.get("name") for o in self.offices):
                return ok_({"error": "name_taken"}, 409)
            o = {"id": "o_fake%02d" % (len(self.offices) + 1) + "abcd", "name": body.get("name"), "projects": body.get("projects") or [], "agent_cap": 5, "created": _PX_T0, "updated": _PX_T0}
            self.offices.append(o)
            return ok_({"ok": True, "office": o})
        m = _re.match(r"^/v1/offices/(o_\w+)(/delete)?$", p)
        if m:
            o = next((x for x in self.offices if x["id"] == m.group(1)), None)
            if not o:
                return ok_({"error": "not_found"}, 404)
            if m.group(2):
                self.offices.remove(o)
                return ok_({"ok": True})
            if "name" in body:
                o["name"] = body["name"]
            if "projects" in body:
                o["projects"] = body["projects"]
            return ok_({"ok": True, "office": o})
        return route.fulfill(status=404, body="{}", headers=h)


def _px_ctx(b, f, w=1280, h=800, touch=False):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    cfg = _json.dumps({"url": _PX_AIO, "login": True})
    user = _json.dumps({"email": "a@example.com", "name": "測試", "admin": False})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('tw.acct.tok','tok-test');localStorage.setItem('tw.acct.user'," + _json.dumps(user) + ");localStorage.setItem('aiOffice.live.v1'," + _json.dumps(cfg) + ")}catch(e){}")
    c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://tw-account.test' };", headers={"Content-Type": "application/javascript"}))
    c.route(_PX_AIO + "/**", f.handle)
    return c


def _px_page(c):
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    return pg


def _px_world_ready(pg):
    return wait_until(pg, "() => window.__world && window.__world.ready && window.__world.live && window.__world.live.data", 120000)


def _px_tags(pg):
    return pg.evaluate("""() => { const W = window.__world, o = {}; for (const [id, c] of W.chars) if (c._lab) o[id] = c._lab.tag.children[0].textContent; (W.extras || []).forEach(c => { if (c._lab) o[c.spec.id] = c._lab.tag.children[0].textContent; });
        return { ceo: o.ceo, clones: Object.entries(o).filter(([k]) => /^ceo-clone/.test(k)).map(([, v]) => v), ids: Object.keys(o) } }""")


def _px_sign(pg):
    return pg.evaluate("() => { let r = null; __world.scene.traverse(o => { if (o.userData && o.userData.roomText === 'CEO 辦公室') r = o.userData.signNow || o.userData.roomText; }); return r }")


# ───────────────────────── ① 入口專案清單 → ② 進辦公室只看到該專案 ─────────────────────────
def _px_flow(b, base):
    f = _PxFake()
    c = _px_ctx(b, f)
    try:
        pg = _px_page(c)
        pg.goto(_px_root(base) + "/office/index.html", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__officeEntry && !document.getElementById('projSec').hidden", 20000)
        ok("入口：伺服器有專案時，出現「你的專案」清單", got)
        if not got:
            return
        txt = pg.locator("#projList").inner_text()
        rows = pg.locator("#projList li")
        ok("入口：列出 3 個專案，各有「最後活動」與進行中工作階段數", rows.count() == 3 and txt.count("最後活動") == 3 and "2 個進行中" in txt and txt.count("1 個進行中") == 2, txt)
        ok("入口：名稱是 user 的顯示「雲端工作階段」，畫面上沒有「user」這個名字", "雲端工作階段" in txt and not _re.search(r"\buser\b", txt) and "tw-rotation" in txt and "other-repo" in txt, txt)
        ok("入口：伺服器辦公室清單是空的 → 「我的辦公室」區不顯示、空狀態大卡也收起（有專案可進）", not pg.locator("#mine").is_visible() and not pg.locator("#empty").is_visible())
        _px_shot(pg, "p1_入口專案清單.png")
        pg.locator("#projList li").first.get_by_role("link", name="進入").click()
        pg.wait_for_url(_re.compile(r"world\.html\?office=main&project=" + _PA))
        ok("入口：點「進入」才進辦公室，網址帶辦公室與專案雜湊", "project=" + _PA in pg.url and "office=main" in pg.url, pg.url)
        got = _px_world_ready(pg)
        ok("辦公室：載入完成、即時資料進來", got)
        if not got:
            return
        wait_until(pg, "() => (window.__world.live.clones || []).some(c => c.sid)", 30000)
        ok("辦公室：請求帶 project=（收件端依專案過濾）", any("project=" + _PA in u for u in f.state_urls), f.state_urls[:2])
        tg = _px_tags(pg)
        ok("名牌：CEO 寫「tw-rotation CEO」", tg["ceo"] == "tw-rotation CEO", tg)
        ok("名牌：同專案的第二個工作階段是「tw-rotation CEO（分身 2）」，而且只有這一位分身", tg["clones"] == ["tw-rotation CEO（分身 2）"], tg)
        ok("只看到該專案角色：自己專案的子 Agent 在、別的專案的（zz-agent-b、zz-agent-u）不在", "x-general-purpose" in tg["ids"] and not any(i.startswith("x-zz-") for i in tg["ids"]), tg["ids"])
        ok("門牌：「CEO 辦公室」改成「tw-rotation CEO 辦公室」", _px_sign(pg) == "tw-rotation CEO 辦公室", _px_sign(pg))
        pj = pg.locator(".aio-pjn")
        ok("左上角：看得出能按的「← 專案名 ▾」，旁邊的「?」另外放、仍可按", pj.is_visible() and "tw-rotation" in pj.inner_text() and "▾" in pj.inner_text() and pg.locator(".aio-pjn .pjb").inner_text().strip() == "←" and pg.locator("#helpBtn").is_visible() and not pg.locator(".ttl a[href='index.html']").is_visible())
        _px_shot(pg, "p2_辦公室左上角與名牌.png")
        pg.locator("#helpBtn").click()
        ok("左上角：「?」照樣打開操作說明（和專案按鈕互不干擾）", pg.locator("#helpPop").is_visible())
        pg.locator("#helpBtn").click()
        # ③ ▾ 下拉切換
        pg.locator(".aio-pjn .pjn").click()
        menu = pg.locator(".aio-pjm")
        ok("▾：打開下拉，列出 3 個專案，目前這個打勾", menu.is_visible() and menu.locator("button[data-h]").count() == 3 and "✓" in menu.locator("button.cur").inner_text(), menu.inner_text() if menu.count() else "")
        _px_shot(pg, "p3_下拉切換專案.png")
        pg.keyboard.press("Escape")
        ok("▾：按 Esc 關掉下拉", pg.locator(".aio-pjm").count() == 0)
        pg.locator(".aio-pjn .pjn").click()
        pg.locator(".aio-pjm button[data-h='%s']" % _PB).click()
        pg.wait_for_url(_re.compile("project=" + _PB))
        got = _px_world_ready(pg)
        wait_until(pg, "() => window.__world.live.projName", 30000)
        tg = _px_tags(pg)
        ok("切換：換成 other-repo，名牌「other-repo CEO」、沒有分身、只有該專案的子 Agent", tg["ceo"] == "other-repo CEO" and tg["clones"] == [] and "x-zz-agent-b" in tg["ids"] and "x-general-purpose" not in tg["ids"] and "x-zz-agent-u" not in tg["ids"], tg)
        ok("切換：門牌跟著換", _px_sign(pg) == "other-repo CEO 辦公室", _px_sign(pg))
        pg.locator(".aio-pjn .pjn").click()
        pg.locator(".aio-pjm button[data-h='%s']" % _PU).click()
        pg.wait_for_url(_re.compile("project=" + _PU))
        _px_world_ready(pg)
        wait_until(pg, "() => window.__world.live.projName", 30000)
        tg = _px_tags(pg)
        ok("沒意義的專案名（user）：名牌寫「雲端工作階段 CEO」、門牌「雲端工作階段 CEO 辦公室」", tg["ceo"] == "雲端工作階段 CEO" and _px_sign(pg) == "雲端工作階段 CEO 辦公室", (tg, _px_sign(pg)))
        # ← 回專案清單
        pg.locator(".aio-pjn .pjb").click()
        pg.wait_for_url(_re.compile(r"office/index\.html"))
        got = wait_until(pg, "() => !document.getElementById('dlg').hidden && document.querySelectorAll('#dlgBody .plist li').length === 3", 20000)
        ok("←：回到入口並自動打開專案清單（3 個專案）", got, pg.inner_text("#dlgBody") if pg.locator("#dlgBody").count() else "")
        ok("←：網址上的 #pick 清掉了（重新整理不會又彈出來）", "#pick" not in pg.url, pg.url)
        _px_shot(pg, "p4_回專案清單對話框.png")
        pg.locator("#dlgBody .plist li").nth(1).get_by_role("link", name="進入").click()
        pg.wait_for_url(_re.compile("project=" + _PB))
        ok("專案清單對話框：點「進入」進對應專案", True)
        ok("沒有頁面錯誤", not pg.errs, pg.errs[:2])
    finally:
        c.close()


# ───────────────────────── ④ 辦公室清單讀伺服器 ─────────────────────────
def _px_offices(b, base):
    f = _PxFake()
    c = _px_ctx(b, f)
    try:
        pg = _px_page(c)
        pg.goto(_px_root(base) + "/office/index.html", wait_until="domcontentloaded")
        wait_until(pg, "() => window.__officeEntry && window.__officeEntry.srv.loaded", 20000)
        ok("伺服器模式：辦公室清單讀伺服器（不是瀏覽器暫存）", pg.evaluate("() => window.__officeEntry.srv.mode") == "server" and not pg.locator("#srvNote").is_visible())
        for nm in ["甲辦公室", "乙辦公室", "丙辦公室"]:
            pg.locator("#newDoor").click()
            pg.fill("#offName", nm)
            pg.keyboard.press("Enter")
            wait_until(pg, "() => /連接你的 Claude/.test(document.getElementById('dlgT').textContent)", 10000)
            pg.locator("#dlg .x").click()
        ok("建立：3 間都建在伺服器上、清單出現、瀏覽器暫存沒有留", len(f.offices) == 3 and pg.locator("#mineList li").count() == 3 and pg.evaluate("() => window.__officeEntry.local().length") == 0, (len(f.offices), pg.locator("#mineList li").count()))
        ok("上限：第三張卡寫「已達 3 間上限」", "已達 3 間上限" in pg.locator("#newSub").inner_text())
        f.limit = 3
        pg.locator("#newDoor").click(force=True)
        ok("上限：點了出現說明、不能再建（伺服器端也擋）", "上限" in pg.locator("#dlgT").inner_text() and len(f.offices) == 3)
        pg.locator("#dlg .x").click()
        # 改名
        pg.locator("#mineList li").first.get_by_role("button", name="改名").click()
        pg.fill("#offName", "我的專案甲")
        pg.keyboard.press("Enter")
        wait_until(pg, "() => document.getElementById('dlg').hidden", 10000)
        ok("改名：清單與伺服器都換成新名字", "我的專案甲" in pg.locator("#mineList li").first.inner_text() and f.offices[0]["name"] == "我的專案甲", f.offices[0])
        # 綁專案：進入 → 專案清單 → 綁定
        pg.locator("#mineList li").first.get_by_role("link", name="進入").click()
        got = wait_until(pg, "() => !document.getElementById('dlg').hidden && document.querySelectorAll('#dlgBody .plist li').length === 3", 10000)
        ok("進入辦公室：先列專案清單（還沒綁專案＝列全部 3 個）", got)
        pg.locator("#dlgBody .plist li").first.get_by_role("button", name="綁定到這間").click()
        wait_until(pg, "() => document.querySelector('#dlgBody .plist button[data-bind]').textContent === '取消綁定'", 10000)
        ok("綁定：伺服器記下綁定的專案、按鈕變「取消綁定」", f.offices[0]["projects"] == [_PA], f.offices[0])
        pg.locator("#dlg .x").click()
        ok("綁定：清單上這間寫「1 個專案」", "1 個專案" in pg.locator("#mineList li").first.inner_text())
        pg.locator("#mineList li").first.get_by_role("link", name="進入").click()
        wait_until(pg, "() => !document.getElementById('dlg').hidden", 10000)
        ok("綁定後進入：只列綁定的專案，另有「顯示其他專案（2）」", pg.locator("#dlgBody .plist li").count() == 1 and "顯示其他專案（2）" in pg.locator("#dlgBody").inner_text())
        pg.get_by_role("button", name=_re.compile("顯示其他專案")).click()
        ok("顯示其他專案：展開成 3 個", pg.locator("#dlgBody .plist li").count() == 3)
        pg.locator("#dlgBody .plist li").first.get_by_role("link", name="進入").click()
        pg.wait_for_url(_re.compile("office=o_fake01abcd&project=" + _PA))
        ok("進入：網址帶伺服器辦公室代號與專案", True, pg.url)
        got = _px_world_ready(pg)
        ok("辦公室：帶伺服器辦公室代號時，請求帶 view=（伺服器套每間 5 位 Agent 的上限）", got and any("view=o_fake01abcd" in u for u in f.state_urls), f.state_urls[:2])
        # 移除
        pg.goto(_px_root(base) + "/office/index.html", wait_until="domcontentloaded")
        wait_until(pg, "() => window.__officeEntry && window.__officeEntry.srv.loaded && document.querySelectorAll('#mineList li').length === 3", 20000)
        b0 = pg.locator("#mineList li").last.get_by_role("button", name="移除")
        b0.click()
        pg.locator("#mineList li").last.get_by_role("button", name="確定移除？").click()
        wait_until(pg, "() => document.querySelectorAll('#mineList li').length === 2", 10000)
        ok("移除：兩段確認後伺服器也刪掉、第三張卡又能用", len(f.offices) == 2 and pg.locator("#newDoor").get_attribute("aria-disabled") == "false", len(f.offices))
        # 伺服器連不上：退回暫存並寫明
        f.down = True
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => window.__officeEntry && window.__officeEntry.srv.loaded", 20000)
        ok("伺服器連不上：退回瀏覽器暫存、頁面上寫明原因", pg.evaluate("() => window.__officeEntry.srv.mode") == "local" and "暫時連不上" in pg.locator("#srvNote").inner_text() and pg.locator("#srvNote").is_visible())
        ok("伺服器連不上：照樣能建立暫存辦公室、不會壞", True)
        pg.locator("#newDoor, #heroBtn").locator("visible=true").first.click()
        pg.fill("#offName", "暫存的")
        pg.keyboard.press("Enter")
        wait_until(pg, "() => /連接你的 Claude/.test(document.getElementById('dlgT').textContent)", 10000)
        ok("伺服器連不上：暫存建立成功（只在這個瀏覽器）", pg.evaluate("() => window.__officeEntry.local().length") == 1)
        pg.locator("#dlg .x").click()
        f.down = False
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => window.__officeEntry && window.__officeEntry.srv.loaded && window.__officeEntry.srv.mode === 'server'", 20000)
        wait_until(pg, "() => window.__officeEntry.local().length === 0", 10000)
        ok("伺服器恢復：暫存的辦公室自動搬上伺服器、暫存清空", any(o["name"] == "暫存的" for o in f.offices) and pg.evaluate("() => window.__officeEntry.local().length") == 0, [o["name"] for o in f.offices])
        ok("沒有頁面錯誤", not pg.errs, pg.errs[:2])
    finally:
        c.close()


# ───────────────────────── ⑤ 手機＋禁用字 ─────────────────────────
def _px_mobile(b, base):
    f = _PxFake()
    c = _px_ctx(b, f, 390, 844, True)
    try:
        pg = _px_page(c)
        pg.goto(_px_root(base) + "/office/index.html", wait_until="domcontentloaded")
        wait_until(pg, "() => window.__officeEntry && !document.getElementById('projSec').hidden", 20000)
        chk = lambda: pg.evaluate("""() => { const sw = document.documentElement.scrollWidth, small = []; const q = [...document.querySelectorAll('button,a.go2,a.big')].filter(e => { const r = e.getBoundingClientRect(); return r.height > 0 && r.width > 0 && !e.classList.contains('q') && !e.classList.contains('x') });
            q.forEach(e => { if (e.getBoundingClientRect().height < 40) small.push(e.textContent.trim()); });
            const fs = [...document.querySelectorAll('body *')].filter(e => e.children.length === 0 && e.textContent.trim() && e.getBoundingClientRect().height > 0).map(e => parseFloat(getComputedStyle(e).fontSize)).filter(x => x < 11);
            return { over: sw > innerWidth + 1, small, tiny: fs.length } }""")
        r = chk()
        ok("手機入口：專案清單沒有橫向溢出、按鈕不小於 40px、字不小於 11px", not r["over"] and not r["small"] and r["tiny"] == 0, r)
        _px_shot(pg, "p5_手機入口專案清單.png")
        ok("手機入口：專案清單第一屏就看得到第一個專案的「進入」", pg.evaluate("() => { const r = document.querySelector('#projList li .go2').getBoundingClientRect(); return r.bottom <= innerHeight && r.top >= 0 }"))
        txt = pg.evaluate("() => document.body.innerText")
        ok("入口畫面沒有禁用字", not _PX_BAD.search(txt), _PX_BAD.findall(txt))
        pg.locator("#projList li").first.get_by_role("link", name="進入").click()
        pg.wait_for_url(_re.compile("project=" + _PA))
        got = _px_world_ready(pg)
        wait_until(pg, "() => window.__world.live.projName", 30000)
        ok("手機辦公室：載入完成", got)
        m = pg.evaluate("""() => { const t = document.querySelector('.ttl').getBoundingClientRect(), b1 = document.querySelector('.aio-pjn .pjb').getBoundingClientRect(), b2 = document.querySelector('.aio-pjn .pjn').getBoundingClientRect(), q = document.getElementById('helpBtn').getBoundingClientRect();
            return { inView: t.left >= 0 && t.right <= innerWidth, h1: b1.height, w1: b1.width, h2: b2.height, qh: q.height, over: document.documentElement.scrollWidth > innerWidth + 1, fs: parseFloat(getComputedStyle(document.querySelector('.aio-pjn .pjn span')).fontSize) } }""")
        ok("手機辦公室：左上角「← 專案名 ▾」在畫面內、← 與專案名都不小於 40px 高、字不小於 11px、沒有橫向溢出", m["inView"] and m["h1"] >= 40 and m["w1"] >= 40 and m["h2"] >= 40 and m["fs"] >= 11 and not m["over"], m)
        ok("手機辦公室：「?」另外放、也好按（不小於 40px）", m["qh"] >= 40, m)
        _px_shot(pg, "p6_手機辦公室左上角.png")
        pg.locator(".aio-pjn .pjn").tap()
        mm = pg.evaluate("() => { const e = document.querySelector('.aio-pjm'); if (!e) return null; const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, b: r.bottom, n: e.querySelectorAll('button[data-h]').length, minh: Math.min(...[...e.querySelectorAll('button,a')].map(x => x.getBoundingClientRect().height)) } }")
        ok("手機下拉：在畫面內、每個選項不小於 40px", mm and mm["l"] >= 0 and mm["r"] <= 390 and mm["b"] <= 844 and mm["n"] == 3 and mm["minh"] >= 40, mm)
        _px_shot(pg, "p7_手機下拉.png")
        wtxt = pg.evaluate("() => document.getElementById('bar').innerText + ' ' + (document.querySelector('.aio-pjm') || {innerText: ''}).innerText")
        ok("辦公室頂列與下拉沒有禁用字", not _PX_BAD.search(wtxt), _PX_BAD.findall(wtxt))
        ok("沒有頁面錯誤", not pg.errs, pg.errs[:2])
    finally:
        c.close()


def _px_all(pg, b, base, code):
    _px_flow(b, base)
    _px_offices(b, base)
    _px_mobile(b, base)


register("辦公室多專案", _px_all)
