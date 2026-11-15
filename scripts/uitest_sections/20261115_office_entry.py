# 驗收段落「辦公室入口與建立」：site/office/index.html 的「建立新辦公室」流程（site/office/entry.js）
# 擁有者原話：「這邊需要有建立新專案的示範，當我沒有任何專案的情況，這邊會需要有建立新辦公室，且有連接步驟」。
#   ① 沒有辦公室：最上方空狀態「你還沒有辦公室」＋大按鈕「建立第一間辦公室」＋三步驟示意（不是假截圖）；「先看示範」連到示範辦公室
#   ② 真滑鼠真鍵盤走完：建立 → 取名字（空白擋下、同名擋下）→ 連接你的 Claude（三步說明、接入碼不在畫面也不在 localStorage）→ 先跳過 → 完成 → 進辦公室連結；
#      清單出現、空狀態消失、第三張卡計數 1／3
#   ③ 「開始連接」真的點下去：進 world.html 後接入引導自動打開（connect_link.js 接力）、分頁標題換成辦公室名稱、接入碼仍不在 localStorage
#   ④ 未登入（會員系統有開、沒有權杖）：建立 → 只出現「先登入再建立辦公室」＋到網站首頁登入的連結，不進取名字；先看示範照常
#   ⑤ 已達上限：非站長用介面建到 3 間 → 第三張卡寫已達上限、點了出現說明、不能再建；移除一間（兩段確認）後又能建立；站長不受 3 間限制
#   ⑥ 手機 390×844：空狀態、流程、清單都沒有橫向溢出、可見文字不小於 11px、按鈕不小於 40px、對話框在畫面內
#   ⑦ 全部畫面都沒有禁用字（價格、NT$、付費、升級、訂閱、方案、Plus、Pro、免費、右鍵）
# 只用 ok()／wait_until()／register()；函式名一律 _oe_ 前綴。環境變數 ENTRY_SHOTS 指到資料夾時順便存截圖。
# flake8: noqa

import json as _json
import os as _os
import re as _re

_OE_BAD = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")
_OE_CODE = _re.compile(r"aio_[A-Za-z0-9_-]{6,}")


def _oe_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _oe_shot(pg, name):
    d = _os.environ.get("ENTRY_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _oe_new(b, w=1280, h=800, touch=False, login=None, owner=False):
    """login=None：會員系統沒開；login=False：有開但沒登入；login=True：有開且已登入。"""
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    if login is not None:
        c.route("**/account_config.js", lambda r: r.fulfill(status=200, body="window.TW_ACCOUNT = { api: 'https://acct.test' };", headers={"Content-Type": "application/javascript"}))
    if login:
        u = _json.dumps({"email": "a@example.com", "name": "測試", "admin": owner, "owner": owner})
        c.add_init_script("try{localStorage.setItem('tw.acct.tok','tok-test');localStorage.setItem('tw.acct.user'," + _json.dumps(u) + ")}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(30000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    return c, pg


def _oe_open(pg, base):
    pg.goto(_oe_root(base) + "/office/index.html", wait_until="domcontentloaded")
    wait_until(pg, "() => window.__officeEntry", 20000)


def _oe_text(pg):
    return pg.evaluate("() => document.body.innerText")


def _oe_ls_has_code(pg):
    return pg.evaluate("() => { const o = {}; for (let i = 0; i < localStorage.length; i++) o[localStorage.key(i)] = localStorage.getItem(localStorage.key(i)); return JSON.stringify(o) }")


def _oe_make(pg, name, finish=True):
    """從入口點「建立」到完成（先跳過連接）。回傳辦公室 id。"""
    pg.locator("#newDoor, #heroBtn").locator("visible=true").first.click()
    pg.locator("#offName").click()
    pg.keyboard.type(name)
    pg.keyboard.press("Enter")
    pg.locator("#dlg").get_by_role("button", name="先跳過").click()
    pg.locator("#dlg").get_by_role("button", name="回入口").click()
    return pg.evaluate("() => window.__officeEntry.list().slice(-1)[0].id")


def _oe_flow(b, base):
    c, pg = _oe_new(b)
    try:
        _oe_open(pg, base)
        # ① 空狀態
        ok("空狀態：最上方寫「你還沒有辦公室」、有大按鈕「建立第一間辦公室」", pg.locator("#empty").is_visible() and "你還沒有辦公室" in _oe_text(pg) and pg.get_by_role("button", name="建立第一間辦公室").is_visible())
        ok("空狀態：三步驟示意（取名字／連接你的 Claude／進辦公室）", pg.locator(".steps3 li").count() == 3 and all(t in pg.locator(".steps3").inner_text() for t in ["取名字", "連接你的 Claude", "進辦公室"]))
        ok("空狀態：「我的辦公室」清單先不顯示、示範辦公室與圖鑑兩張卡仍在，第三張卡「建立新辦公室」在", (not pg.locator("#mine").is_visible()) and pg.locator("a.door").count() == 2 and pg.locator("#newDoor").is_visible())
        ok("空狀態：「先看示範」連到示範辦公室 world.html", pg.locator("#doorDemo").get_attribute("href") == "world.html" and "先看示範" in pg.locator("#doorDemo").inner_text())
        ok("空狀態：沒有禁用字", not _OE_BAD.search(_oe_text(pg)), _OE_BAD.findall(_oe_text(pg)))
        _oe_shot(pg, "entry_empty.png")
        # ② 建立流程
        pg.get_by_role("button", name="建立第一間辦公室").click()
        ok("步驟 1：對話框開啟、標題「幫辦公室取個名字」、輸入框有焦點", pg.locator("#dlg").is_visible() and "取個名字" in pg.locator("#dlgT").inner_text() and pg.evaluate("() => document.activeElement && document.activeElement.id") == "offName")
        pg.keyboard.press("Enter")
        ok("步驟 1：名稱空白按 Enter → 擋下、寫「請先輸入名稱」、沒有進下一步", "請先輸入名稱" in pg.locator("#offErr").inner_text() and pg.evaluate("() => window.__officeEntry.list().length") == 0)
        _oe_shot(pg, "entry_step1.png")
        pg.keyboard.type("我的新專案")
        pg.keyboard.press("Enter")
        ok("步驟 2：進到「連接你的 Claude」、寫出三個動作、有「開始連接」「先跳過」", "連接你的 Claude" in pg.locator("#dlgT").inner_text() and pg.locator(".how li").count() == 3 and pg.locator("#dlg").get_by_role("link", name="開始連接").is_visible() and pg.locator("#dlg").get_by_role("button", name="先跳過").is_visible())
        ok("步驟 2：辦公室已記下（清單 1 間、尚未連接）", pg.evaluate("() => { const l = window.__officeEntry.list(); return l.length === 1 && l[0].name === '我的新專案' && !l[0].connected }"))
        ok("步驟 2：畫面與 localStorage 都沒有接入碼", not _OE_CODE.search(_oe_text(pg)) and not _OE_CODE.search(_oe_ls_has_code(pg)))
        ok("步驟 2：沒有禁用字", not _OE_BAD.search(_oe_text(pg)), _OE_BAD.findall(_oe_text(pg)))
        _oe_shot(pg, "entry_step2.png")
        pg.locator("#dlg").get_by_role("button", name="先跳過").click()
        ok("步驟 3：寫「辦公室建好了」、有「進辦公室」連結指到這間", "建好了" in pg.locator("#dlgT").inner_text() and "world.html?office=" in (pg.locator("#dlg").get_by_role("link", name="進辦公室").get_attribute("href") or ""))
        _oe_shot(pg, "entry_step3.png")
        pg.locator("#dlg").get_by_role("button", name="回入口").click()
        ok("回到入口：空狀態收掉、「我的辦公室」出現這一間（尚未連接）、第三張卡寫已建 1／3 間", (not pg.locator("#empty").is_visible()) and pg.locator("#mineList li").count() == 1 and "尚未連接" in pg.locator("#mineList").inner_text() and "已建 1／3 間" in pg.locator("#newSub").inner_text())
        _oe_shot(pg, "entry_list.png")
        # 同名擋下
        pg.locator("#newDoor").click()
        pg.keyboard.type("我的新專案")
        pg.keyboard.press("Enter")
        ok("同名辦公室：擋下並寫「已經有同名」", "同名" in pg.locator("#offErr").inner_text() and pg.evaluate("() => window.__officeEntry.list().length") == 1)
        pg.keyboard.press("Escape")
        ok("Esc 關閉對話框", not pg.locator("#dlg").is_visible())
        # 重新整理仍在（本機暫存）
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => window.__officeEntry", 20000)
        ok("重新整理後辦公室還在", pg.locator("#mineList li").count() == 1)
        ok("沒有頁面錯誤", not pg.errs, pg.errs[:2])
        # ③ 繼續連接 → 開始連接 → 進 world 引導自動打開
        pg.get_by_role("button", name="繼續連接").click()
        pg.locator("#dlg").get_by_role("link", name="開始連接").click()
        pg.wait_for_url("**/world.html*", timeout=30000)
        got = wait_until(pg, "() => { const g = document.getElementById('aioGuide'); return g && !g.hidden }", 120000)
        ok("按「開始連接」：進到辦公室、接入引導自動打開", bool(got))
        ok("接入引導打開時，分頁標題換成辦公室名稱", "我的新專案" in pg.title(), pg.title())
        ok("接入引導打開時，localStorage 沒有接入碼", not _OE_CODE.search(_oe_ls_has_code(pg)))
        _oe_shot(pg, "entry_world_guide.png")
    finally:
        c.close()


def _oe_login(b, base):
    c, pg = _oe_new(b, login=False)
    try:
        _oe_open(pg, base)
        ok("未登入：空狀態寫「要先登入」", "先登入" in pg.locator("#heroNote").inner_text())
        pg.get_by_role("button", name="建立第一間辦公室").click()
        ok("未登入：點建立 → 出現「先登入再建立辦公室」、有到網站首頁登入的連結、不進取名字", "先登入" in pg.locator("#dlgT").inner_text() and pg.locator("#offName").count() == 0 and (pg.locator("#dlg").get_by_role("link", name="到網站首頁登入").get_attribute("href") or "").endswith("index.html"))
        ok("未登入：沒有禁用字", not _OE_BAD.search(_oe_text(pg)), _OE_BAD.findall(_oe_text(pg)))
        _oe_shot(pg, "entry_login.png")
        pg.keyboard.press("Escape")
        ok("未登入：先看示範照常可點（連到 world.html）", pg.locator("#doorDemo").get_attribute("href") == "world.html")
        ok("未登入：沒有寫入任何辦公室", pg.evaluate("() => window.__officeEntry.list().length") == 0)
    finally:
        c.close()
    # 已登入 → 直接進取名字
    c, pg = _oe_new(b, login=True)
    try:
        _oe_open(pg, base)
        pg.get_by_role("button", name="建立第一間辦公室").click()
        ok("已登入：點建立直接進「取名字」", pg.locator("#offName").is_visible())
    finally:
        c.close()


def _oe_limit(b, base):
    c, pg = _oe_new(b, login=True, owner=False)
    try:
        _oe_open(pg, base)
        for n in ("甲", "乙", "丙"):
            _oe_make(pg, "辦公室" + n)
        ok("上限：建到 3 間，第三張卡寫「已達 3 間上限」", pg.locator("#mineList li").count() == 3 and "已達 3 間上限" in pg.locator("#newSub").inner_text() and pg.locator("#newDoor").get_attribute("aria-disabled") == "true")
        pg.locator("#newDoor").click()
        ok("上限：點第三張卡 → 說明「已達辦公室上限」、沒有取名字輸入框、沒有多建", "上限" in pg.locator("#dlgT").inner_text() and pg.locator("#offName").count() == 0 and pg.evaluate("() => window.__officeEntry.list().length") == 3)
        ok("上限：說明沒有禁用字", not _OE_BAD.search(_oe_text(pg)), _OE_BAD.findall(_oe_text(pg)))
        _oe_shot(pg, "entry_limit.png")
        pg.get_by_role("button", name="知道了").click()
        # 移除（兩段確認）
        first = pg.locator("#mineList li").first.get_by_role("button", name="移除")
        first.click()
        ok("移除：第一下變成「確定移除？」、還沒刪", "確定移除" in first.inner_text() and pg.locator("#mineList li").count() == 3)
        pg.locator("#mineList li").first.get_by_role("button", name="確定移除？").click()
        ok("移除：第二下才真的刪、剩 2 間、第三張卡又能用", pg.locator("#mineList li").count() == 2 and pg.locator("#newDoor").get_attribute("aria-disabled") == "false")
        pg.locator("#newDoor").click()
        ok("移除後又能建立（出現取名字）", pg.locator("#offName").is_visible())
    finally:
        c.close()
    # 站長不受 3 間限制
    c, pg = _oe_new(b, login=True, owner=True)
    try:
        _oe_open(pg, base)
        for n in ("一", "二", "三", "四"):
            _oe_make(pg, "站長辦公室" + n)
        ok("站長：建到 4 間也沒被擋、第三張卡沒有上限字樣", pg.locator("#mineList li").count() == 4 and "上限" not in pg.locator("#newSub").inner_text() and pg.locator("#newDoor").get_attribute("aria-disabled") == "false")
    finally:
        c.close()


def _oe_mobile(b, base):
    c, pg = _oe_new(b, 390, 844, touch=True)
    try:
        _oe_open(pg, base)

        def chk(tag):
            r = pg.evaluate("""() => {
                const bad = []; const w = innerWidth;
                for (const e of document.querySelectorAll('body *')) {
                    const cs = getComputedStyle(e), r = e.getBoundingClientRect();
                    if (cs.display === 'none' || cs.visibility === 'hidden' || r.width === 0 || r.height === 0) continue;
                    if ([...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && parseFloat(cs.fontSize) < 11) bad.push('字 ' + e.tagName + ' ' + cs.fontSize);
                    if (e.closest('#dlg') ? false : false) {}
                }
                const btns = [...document.querySelectorAll('button,a.big,a.go2')].filter(e => e.getBoundingClientRect().height > 0 && !e.classList.contains('q') && !e.classList.contains('x')).filter(e => e.getBoundingClientRect().height < 40).map(e => e.textContent.trim());
                const dlg = document.querySelector('#dlg:not([hidden]) .box'), db = dlg ? dlg.getBoundingClientRect() : null;
                return { over: document.documentElement.scrollWidth > w, small: bad.slice(0, 3), btns, dlgOut: db ? (db.bottom > innerHeight + 1 || db.right > w + 1 || db.left < -1) : false };
            }""")
            ok(f"手機 {tag}：沒有橫向溢出", not r["over"])
            ok(f"手機 {tag}：可見文字不小於 11px", not r["small"], r["small"])
            ok(f"手機 {tag}：按鈕不小於 40px 高", not r["btns"], r["btns"])
            ok(f"手機 {tag}：對話框在畫面內", not r["dlgOut"])

        chk("空狀態")
        ok("手機：空狀態第一屏看得到「建立第一間辦公室」", pg.evaluate("() => { const r = document.getElementById('heroBtn').getBoundingClientRect(); return r.bottom <= innerHeight && r.top >= 0 }"))
        _oe_shot(pg, "entry_m_empty.png")
        pg.locator("#heroBtn").tap()
        chk("取名字")
        pg.locator("#offName").tap()
        pg.keyboard.type("手機辦公室")
        pg.keyboard.press("Enter")
        chk("連接步驟")
        _oe_shot(pg, "entry_m_step2.png")
        pg.locator("#dlg").get_by_role("button", name="先跳過").tap()
        chk("完成")
        pg.locator("#dlg").get_by_role("button", name="回入口").tap()
        ok("手機：建立完成後清單出現", pg.locator("#mineList li").count() == 1)
        chk("清單")
        _oe_shot(pg, "entry_m_list.png")
        ok("手機：沒有禁用字", not _OE_BAD.search(_oe_text(pg)), _OE_BAD.findall(_oe_text(pg)))
    finally:
        c.close()


def _oe_all(pg, b, base, code):
    _oe_flow(b, base)
    _oe_login(b, base)
    _oe_limit(b, base)
    _oe_mobile(b, base)


register("辦公室入口與建立", _oe_all)
