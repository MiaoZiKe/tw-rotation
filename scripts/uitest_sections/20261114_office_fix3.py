# 驗收段落「辦公室第三輪修正」：AI Office 3D 辦公室（site/office/world.html）擁有者 11-14 試用後回報的四件事。
#   F1 拖曳一律平移：從角色身上、桌子上、佈告欄上、空地按下拖曳，鏡頭注視點都會移動，而且沒有選取、沒有拎起；
#      短按角色＝選取；按住角色不動約 0.4 秒再拖＝拎起（鏡頭不動）；旋轉模式、整修模式維持原樣；慢慢點（0.45 秒）招牌也算點擊
#   F2 績效總表：頂端鈕（桌機／手機直接露出）、入口打卡機、部門招牌三個入口都打得開；排序、切週、只看需要加強、展開部門、
#      點列飛過去、關閉，每一項都驗畫面真的改變；預設網址與 ?body=v2、直接複製的站台副本（沒有 data／preview）都要能用
#   F3 無業遊民區：預設俯視看得到一部分、沒露出中心時有邊緣標示（點了飛過去）、「區域」選單可飛到、木牌寫「目前沒有人待業」、
#      開除鈕在資訊卡上半部（手機也不用捲動）、開除後木牌改寫人數
#   F4 預設就是新角色；?body=v1 才是舊的
#   另：畫面文字不含禁用字、1280／390 元素不重疊、無主控台錯誤
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用；全部是真的操作（滑鼠按下／移動／放開、點按鈕）。
# 環境變數 F3_SHOTS 指到資料夾時，順便存交件截圖。
# flake8: noqa

import os as _os
import re as _re
import json as _json

_F3_FORBID = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")
_F3_QS = "?ambient=0&q=low&pr=0.6&sim=1"
_F3_PROJ = """([x, y, z]) => { const W = __world, v = new W.THREE.Vector3(x, y, z).project(W.camera), r = document.getElementById('cv').getBoundingClientRect(); return [(v.x + 1) / 2 * r.width + r.left, (1 - v.y) / 2 * r.height + r.top]; }"""


def _f3_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _f3_open(b, base, w=1280, h=800, qs=_F3_QS):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=w < 700, is_mobile=w < 700)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    # 404 只放過站台副本本來就沒有的圖示／資料檔；其他的主控台錯誤一律算
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(_f3_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    if got:
        pg.evaluate("() => { __world.speed = 8; }")
    pg.wait_for_timeout(500)
    return c, pg, got


def _f3_shot(pg, name):
    d = _os.environ.get("F3_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _f3_target(pg):
    return pg.evaluate("() => __world.controls.target.toArray()")


def _f3_dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _f3_drag(pg, x, y, dx=-130, dy=-60, steps=12, hold=0):
    """真的按下、慢慢移動、放開（走瀏覽器真正的輸入管線 Input.dispatchMouseEvent）。
    事件時間用 timestamp 明確指定：這個測試環境是軟體繪圖，每個動作的來回要好幾百毫秒，若用實際等待時間，
    「按下到第一次移動」會被拉長到超過 0.4 秒，變成每次都是長按。hold＝按下後先停多久（毫秒，事件時間，測長按用）"""
    import time as _t
    cdp = getattr(pg, "_f3cdp", None)
    if cdp is None:
        cdp = pg.context.new_cdp_session(pg)
        pg._f3cdp = cdp
    T = _t.time()
    send = lambda t, px, py, b, ts: cdp.send("Input.dispatchMouseEvent", {"type": t, "x": px, "y": py, "button": "left" if b else "none", "buttons": 1 if b else 0, "clickCount": 1 if t != "mouseMoved" else 0, "timestamp": ts})
    send("mouseMoved", x, y, False, T)
    send("mousePressed", x, y, True, T + 0.001)
    T0 = T + 0.002 + hold / 1000.0
    for i in range(1, steps + 1):
        send("mouseMoved", x + dx * i / steps, y + dy * i / steps, True, T0 + 0.016 * i)
    send("mouseReleased", x + dx, y + dy, True, T0 + 0.016 * (steps + 1))
    pg.wait_for_timeout(150)


def _f3_free_char(pg, mx=200):
    """一位站在畫面中間、點下去確實會落在畫布上（不被面板擋）的角色；回傳 [id, x, y]"""
    return pg.evaluate("""(mx) => { const W = __world, cv = document.getElementById('cv'), r = cv.getBoundingClientRect(); let best = null;
      for (const c of W.chars.values()) { if (c.spec.pet || c.away || c.jobless || c.state === 'held') continue;
        const v = new W.THREE.Vector3(c.object3D.position.x, 0.45 * (c.scale || 1), c.object3D.position.z).project(W.camera), x = (v.x + 1) / 2 * r.width + r.left, y = (1 - v.y) / 2 * r.height + r.top;
        if (x < mx || x > innerWidth - mx || y < 150 || y > innerHeight - 160) continue; const el = document.elementFromPoint(x, y); if (!el || el !== cv) continue;
        const d = Math.hypot(x - innerWidth / 2, y - innerHeight / 2); if (!best || d < best.d) best = { id: c.spec.id, x, y, d }; }
      return best && [best.id, best.x, best.y]; }""", mx)


def _f3_overlaps(pg, sels):
    rs = pg.evaluate("""(sels) => { const out = []; for (const s of sels) document.querySelectorAll(s).forEach((e, i) => { if (e.hidden) return; const r = e.getBoundingClientRect(), cs = getComputedStyle(e); if (!r.width || cs.display === 'none' || cs.visibility === 'hidden') return; out.push([s + i, r.left, r.top, r.right, r.bottom]); }); return out; }""", sels)
    bad = []
    for i, a in enumerate(rs):
        for c in rs[i + 1:]:
            if not (a[3] <= c[1] + 1 or c[3] <= a[1] + 1 or a[4] <= c[2] + 1 or c[4] <= a[2] + 1):
                bad.append((a[0], c[0]))
    return bad, len(rs)


def t_f3_pan(b, base):
    c, pg, got = _f3_open(b, base)
    ok("修正3：辦公室頁載入完成", got)
    if not got:
        return
    try:
        pg.evaluate("() => { __world.cam.setMode('move'); __world.setView('god', null, true); }")
        pg.wait_for_timeout(900)
        # ── 從角色身上拖曳＝平移 ──
        ch = _f3_free_char(pg)
        ok("拖曳：畫面上找得到一位站得出來的角色", bool(ch), ch)
        cid, x, y = ch
        t0 = _f3_target(pg)
        _f3_shot(pg, "從角色上拖曳平移_前.png")
        _f3_drag(pg, x, y, dx=-150, dy=-50)
        t1 = _f3_target(pg)
        st = pg.evaluate("(id) => { const c = __world.chars.get(id); return [c.state, !!document.querySelector('#card:not([hidden])'), __world.pilot.sel ? __world.pilot.sel.spec.id : null]; }", cid)
        ok("從角色身上按住拖曳：鏡頭注視點移動了 %.1f 公尺" % _f3_dist(t0, t1), _f3_dist(t0, t1) > 1.5, (t0, t1))
        ok("從角色身上拖曳：沒有拎起他（狀態 %s）、沒有選取他（資訊卡未開、操控未選取）" % st[0], st[0] != "held" and not st[1] and st[2] is None, st)
        _f3_shot(pg, "從角色上拖曳平移_後.png")
        # 往回拖一次，鏡頭也跟著回來（一比一抓著地面）
        pg.evaluate("() => __world.setView('god', null, true)")
        pg.wait_for_timeout(700)
        # ── 從桌子上、佈告欄上拖曳 ──
        desk = pg.evaluate("() => { const i = [...__world.furn.values()].find(q => q.f.type === 'workstation'); return [i.f.x, i.f.z]; }")
        dx_, dy_ = pg.evaluate(_F3_PROJ, [desk[0], 0.8, desk[1]])
        t0 = _f3_target(pg)
        _f3_drag(pg, dx_, dy_, dx=120, dy=40)
        t1 = _f3_target(pg)
        ok("從桌子上按住拖曳：鏡頭注視點移動了 %.1f 公尺" % _f3_dist(t0, t1), _f3_dist(t0, t1) > 1.5, (t0, t1))
        pg.evaluate("() => __world.setView('god', null, true)")
        pg.wait_for_timeout(700)
        bd = pg.evaluate("() => { const m = __world.boardsMesh[0], T = __world.THREE, b = new T.Box3().setFromObject(m), v = new T.Vector3(); b.getCenter(v); return [v.x, v.y, v.z]; }")
        bx, by = pg.evaluate(_F3_PROJ, bd)
        t0 = _f3_target(pg)
        _f3_drag(pg, bx, by, dx=-110, dy=30)
        t1 = _f3_target(pg)
        ok("從佈告欄上按住拖曳：鏡頭注視點移動了 %.1f 公尺，佈告欄面板沒有被打開" % _f3_dist(t0, t1), _f3_dist(t0, t1) > 1.5 and pg.evaluate("() => document.getElementById('board').hidden"), (t0, t1))
        # ── 短按角色＝選取（鏡頭不抖）──
        pg.evaluate("() => __world.setView('god', null, true)")
        pg.wait_for_timeout(700)
        ch = _f3_free_char(pg)
        cid, x, y = ch
        t0 = _f3_target(pg)
        pg.mouse.click(x, y)
        pg.wait_for_timeout(500)
        sel = pg.evaluate("() => __world.pilot.sel ? __world.pilot.sel.spec.id : null")
        ok("短按角色：選取他（%s）、資訊卡打開" % cid, sel == cid and pg.evaluate("() => !document.getElementById('card').hidden"), sel)
        # 選取後鏡頭會飛去跟隨他，所以這裡不比鏡頭，只確認「沒有被當成拖曳而平移到別處」＝模式變成跟隨該角色
        ok("短按角色：視角切成跟隨他", pg.evaluate("(id) => __world.view.char && __world.view.char.spec.id === id", cid))
        # ── 長按再拖＝拎起（鏡頭不動）──
        pg.keyboard.press("Escape")
        pg.evaluate("() => { __world.pilot.deselect(); __world.ui.closePops(); __world.setView('god', null, true); }")
        pg.wait_for_timeout(900)
        ch = _f3_free_char(pg)
        cid, x, y = ch
        t0 = _f3_target(pg)
        # 長按：事件時間上按下後 0.65 秒才開始移動；拎在半空時拍一張，再放開
        import time as _t
        cdp = getattr(pg, "_f3cdp", None) or pg.context.new_cdp_session(pg)
        pg._f3cdp = cdp
        T = _t.time()
        send = lambda t, px, py, b, ts: cdp.send("Input.dispatchMouseEvent", {"type": t, "x": px, "y": py, "button": "left" if b else "none", "buttons": 1 if b else 0, "clickCount": 1 if t != "mouseMoved" else 0, "timestamp": ts})
        send("mouseMoved", x, y, False, T)
        send("mousePressed", x, y, True, T + 0.001)
        for i in range(1, 9):
            send("mouseMoved", x - 12 * i, y - 6 * i, True, T + 0.65 + 0.016 * i)
        pg.wait_for_timeout(200)
        held = pg.evaluate("(id) => __world.chars.get(id).state", cid)
        t1 = _f3_target(pg)
        _f3_shot(pg, "長按拎起角色.png")
        send("mouseReleased", x - 96, y - 48, True, T + 0.9)
        pg.wait_for_timeout(300)
        ok("按住角色不動約半秒再拖：把他拎起來（狀態 %s），鏡頭沒有平移（%.2f 公尺）" % (held, _f3_dist(t0, t1)), held == "held" and _f3_dist(t0, t1) < 0.3, (held, t0, t1))
        ok("放開後他不再是被拎著的狀態", pg.evaluate("(id) => __world.chars.get(id).state", cid) != "held")
        # ── 旋轉模式：從角色身上拖曳仍然是旋轉，不是拎起 ──
        pg.wait_for_timeout(2500)
        pg.evaluate("() => { __world.pilot.deselect(); __world.cam.setMode('rotate'); __world.setView('god', null, true); }")
        pg.wait_for_timeout(900)
        ch = _f3_free_char(pg)
        cid, x, y = ch
        az0 = pg.evaluate("() => Math.atan2(__world.camera.position.x - __world.controls.target.x, __world.camera.position.z - __world.controls.target.z)")
        _f3_drag(pg, x, y, dx=-200, dy=0)
        az1 = pg.evaluate("() => Math.atan2(__world.camera.position.x - __world.controls.target.x, __world.camera.position.z - __world.controls.target.z)")
        ok("旋轉模式：從角色身上拖曳＝旋轉鏡頭（方位變了 %.2f 弧度），沒有拎起他" % abs(az1 - az0), abs(az1 - az0) > 0.2 and pg.evaluate("(id) => __world.chars.get(id).state", cid) != "held", (az0, az1))
        pg.evaluate("() => { __world.cam.setMode('move'); __world.setView('god', null, true); }")
        pg.wait_for_timeout(700)
        # ── 慢慢點（按住 0.45 秒不動）部門招牌／打卡機也算點擊 ──
        kiosk = pg.evaluate("() => { const i = [...__world.furn.values()].find(q => q.f.type === 'kiosk'); return [i.f.x, i.f.z]; }")
        kx, ky = pg.evaluate(_F3_PROJ, [kiosk[0], 1.0, kiosk[1]])
        pg.mouse.move(kx, ky)
        pg.mouse.down()
        pg.wait_for_timeout(330)
        pg.mouse.up()
        ok("慢慢點（按住 0.33 秒，以前超過 0.25 秒就不算點）入口打卡機：績效總表打得開", wait_until(pg, "() => !document.getElementById('ledger').hidden", 3000), (kx, ky))
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        # ── 整修模式：拖家具照舊（移動家具、鏡頭不動）──
        pg.evaluate("() => __world.setView('god', null, true)")
        pg.wait_for_timeout(700)
        pg.click("#editBtn")
        pg.wait_for_timeout(600)
        t0 = _f3_target(pg)
        desk = pg.evaluate("() => { const i = [...__world.furn.values()].find(q => q.f.type === 'workstation'); return [i.f.x, i.f.z, i.f.id]; }")
        ex, ey = pg.evaluate(_F3_PROJ, [desk[0], 0.7, desk[1]])
        _f3_drag(pg, ex, ey, dx=90, dy=0)
        moved = pg.evaluate("(id) => { const i = __world.furn.get(id); return [i.f.x, i.f.z]; }", desk[2])
        t1 = _f3_target(pg)
        ok("整修模式：拖曳桌子＝移動桌子（%.2f → %.2f），鏡頭沒有跟著平移" % (desk[0], moved[0]), abs(moved[0] - desk[0]) > 0.5 and _f3_dist(t0, t1) < 0.3, (desk, moved, t0, t1))
        pg.click('[data-e="reset"]')
        pg.click('[data-e="done"]')
        pg.wait_for_timeout(300)
        # ── 沒有透明的 HTML 元素擋住畫布：在畫面上取樣，每個點最上層不是畫布就必須是有內容或有底色的介面 ──
        blockers = pg.evaluate("""() => { const cv = document.getElementById('cv'), bad = []; for (let gx = 40; gx < innerWidth; gx += 90) for (let gy = 40; gy < innerHeight; gy += 70) { const el = document.elementFromPoint(gx, gy); if (!el || el === cv) continue; let e = el, solid = false; while (e && e !== document.body) { const cs = getComputedStyle(e); if ((e.textContent || '').trim() || e.tagName === 'BUTTON' || e.tagName === 'INPUT' || e.tagName === 'SELECT' || (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)')) { solid = true; break; } e = e.parentElement; } if (!solid) bad.push([gx, gy, el.id || el.className || el.tagName]); } return bad; }""")
        ok("畫面上沒有「透明但擋住滑鼠」的元素（取樣 %d 點）" % ((1280 // 90 + 1) * (800 // 70 + 1)), not blockers, blockers[:5])
        ok("拖曳：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_f3_pan_touch(b, base):
    c, pg, got = _f3_open(b, base, w=390, h=844)
    ok("修正3（手機）：載入完成", got)
    if not got:
        return
    try:
        ok("手機：「績效總表」鈕直接露在頂列（不用先開「更多」）", pg.evaluate("() => { const r = document.getElementById('rwBtn').getBoundingClientRect(); return r.width >= 60 && r.height >= 36 && r.top >= 0 && r.bottom <= 130 && !document.body.classList.contains('m-more'); }"))
        pg.evaluate("() => { __world.setView('god', null, true); }")
        pg.wait_for_timeout(900)
        # 觸控單指拖曳：用 CDP 派真正的觸控事件
        ch = _f3_free_char(pg, 30)
        cdp = c.new_cdp_session(pg)
        if ch:
            cid, x, y = ch
            t0 = _f3_target(pg)
            import time as _t

            def tdrag(hold):
                T = _t.time()
                cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y, "id": 1}], "timestamp": T})
                for i in range(1, 11):
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x - 8 * i, "y": y - 5 * i, "id": 1}], "timestamp": T + hold + 0.016 * i})
                held = pg.evaluate("(id) => __world.chars.get(id).state", cid)
                cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": [], "timestamp": T + hold + 0.3})
                pg.wait_for_timeout(250)
                return held
            held = tdrag(0)
            t1 = _f3_target(pg)
            ok("手機：單指從角色身上拖曳＝平移（移動 %.1f 公尺），沒有拎起（狀態 %s）" % (_f3_dist(t0, t1), held), _f3_dist(t0, t1) > 1.0 and held != "held", (t0, t1, held))
            pg.evaluate("() => { __world.setView('god', null, true); }")
            pg.wait_for_timeout(2500)
            ch = _f3_free_char(pg, 30)
            if ch:
                cid, x, y = ch
                t0 = _f3_target(pg)
                held = tdrag(0.65)
                t1 = _f3_target(pg)
                ok("手機：單指按住角色不動約半秒再拖＝拎起（狀態 %s），鏡頭沒有平移（%.2f 公尺）" % (held, _f3_dist(t0, t1)), held == "held" and _f3_dist(t0, t1) < 0.3, (held, t0, t1))
        else:
            ok("手機：畫面上找得到角色", False)
        ok("手機：拖曳沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _f3_ledger_flow(pg, mobile, tag):
    """打開後把每個操作都點過一遍，每項驗畫面真的改變"""
    ok("績效總表（%s）：打開了、有 12 個單位（CEO＋11 部門）" % tag, pg.evaluate("() => !document.getElementById('ledger').hidden && document.querySelectorAll('#ledger [data-lvl=top]').length") == 12)
    _f3_shot(pg, "績效總表_開啟_%s.png" % tag)
    order0 = pg.evaluate("() => [...document.querySelectorAll('#ledger [data-lvl=top]')].map(e => e.dataset.u)")
    if mobile:
        pg.select_option("#lgSort", "name")
    else:
        pg.click('#ledger [data-sort="name"]')
    pg.wait_for_timeout(300)
    order1 = pg.evaluate("() => [...document.querySelectorAll('#ledger [data-lvl=top]')].map(e => e.dataset.u)")
    ok("績效總表（%s）：改用名稱排序，列的順序真的變了" % tag, order0 != order1, (order0[:3], order1[:3]))
    # 切週
    wk0 = pg.evaluate("() => document.getElementById('lgSub').textContent")
    if mobile:
        pg.select_option("#lgWeek", index=1)
    else:
        pg.click('#ledger [data-wk="1"]')
    pg.wait_for_timeout(300)
    wk1 = pg.evaluate("() => document.getElementById('lgSub').textContent")
    ok("績效總表（%s）：切到上一週，副標題週次改變（%s → %s）" % (tag, wk0[:12], wk1[:12]), wk0 != wk1)
    if mobile:
        pg.select_option("#lgWeek", index=0)
    else:
        pg.click('#ledger [data-wk="0"]')
    pg.wait_for_timeout(200)
    # 只看需要加強
    n0 = pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=top]').length")
    pg.click('#ledger [data-act="need"]')
    pg.wait_for_timeout(300)
    n1 = pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=top]').length")
    ok("績效總表（%s）：「只看需要加強」列數從 %d 變成 %d" % (tag, n0, n1), n1 < n0 and n1 >= 1)
    pg.click('#ledger [data-act="need"]')
    pg.wait_for_timeout(200)
    # 展開部門
    sel = '#ledger [data-u="dept:data"] [data-act="%s"]' % ("card" if mobile else "tog")
    pg.click(sel)
    pg.wait_for_timeout(300)
    sub = pg.evaluate("() => document.querySelectorAll('#ledger [data-u^=\"agent:\"]').length")
    ok("績效總表（%s）：展開「資料部」後出現成員列（%d 位）" % (tag, sub), sub >= 2)
    # 點列飛過去
    t0 = _f3_target(pg)
    pg.click('#ledger [data-u="dept:data"] [data-act="go"]')
    ok("績效總表（%s）：點部門那一列 → 總表關閉、鏡頭飛到資料部" % tag, wait_until(pg, "() => document.getElementById('ledger').hidden && (() => { const r = __world.layout.rooms.find(q => q.id === 'data'), t = __world.controls.target; return t.x > r.x - 1 && t.x < r.x + r.w + 1 && t.z > r.z - 3 && t.z < r.z + r.d + 3; })()", 6000), _f3_target(pg))
    # 再開、用 Esc／×關閉
    pg.click("#rwBtn")
    ok("績效總表（%s）：再按一次頂端鈕又打開" % tag, wait_until(pg, "() => !document.getElementById('ledger').hidden", 3000))
    txt = pg.evaluate("() => document.getElementById('ledger').innerText")
    ok("績效總表（%s）：畫面文字不含禁用字" % tag, not _F3_FORBID.search(txt), _F3_FORBID.search(txt))
    pg.click('#ledger [data-act="close"]')
    ok("績效總表（%s）：按 × 關閉" % tag, wait_until(pg, "() => document.getElementById('ledger').hidden", 2000))


def t_f3_ledger_desktop(b, base):
    for qs, tag in ((_F3_QS, "桌機"), (_F3_QS + "&body=v2", "桌機 body=v2")):
        c, pg, got = _f3_open(b, base, qs=qs)
        ok("績效總表（%s）：載入完成且獎勵層啟用" % tag, got and pg.evaluate("() => __world.rewards && __world.rewards.on"))
        if not got:
            continue
        try:
            ok("績效總表（%s）：頂端鈕看得到、沒被別的元素蓋住" % tag, pg.evaluate("() => { const b = document.getElementById('rwBtn'), r = b.getBoundingClientRect(), e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return r.width > 0 && (e === b || b.contains(e)); }"))
            pg.mouse.click(*pg.evaluate("() => { const r = document.getElementById('rwBtn').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }"))
            wait_until(pg, "() => !document.getElementById('ledger').hidden", 3000)
            _f3_flow = _f3_ledger_flow
            _f3_flow(pg, False, tag)
            if tag == "桌機":
                # 入口打卡機、部門招牌（真的在 3D 畫面上點）
                pg.evaluate("() => __world.setView('god', null, true)")
                pg.wait_for_timeout(900)
                kiosk = pg.evaluate("() => { const i = [...__world.furn.values()].find(q => q.f.type === 'kiosk'); return [i.f.x, i.f.z]; }")
                kx, ky = pg.evaluate(_F3_PROJ, [kiosk[0], 1.0, kiosk[1]])
                pg.mouse.click(kx, ky)
                ok("績效總表（桌機）：點入口打卡機打得開", wait_until(pg, "() => !document.getElementById('ledger').hidden", 3000), (kx, ky))
                pg.keyboard.press("Escape")
                pos = pg.evaluate("() => { for (const i of __world.furn.values()) if (i.spec.deptsign === 'social') return [i.f.x, i.f.z]; }")
                pg.evaluate("([x, z]) => __world.godAt(x, z + 3, 12)", pos)
                wait_until(pg, "() => !__world.view.tween", 15000)
                pg.wait_for_timeout(400)
                sx, sy = pg.evaluate(_F3_PROJ, [pos[0] - 0.3, 1.2, pos[1]])
                pg.mouse.click(sx, sy)
                ok("績效總表（桌機）：點部門招牌打得開並展開該部門", wait_until(pg, "() => !document.getElementById('ledger').hidden && document.querySelector('[data-u^=\"agent:\"]')", 3000), (sx, sy))
                _f3_shot(pg, "績效總表_點招牌_桌機.png")
                pg.keyboard.press("Escape")
            ok("績效總表（%s）：沒有主控台錯誤" % tag, not pg.errs, pg.errs[:3])
        finally:
            c.close()


def t_f3_ledger_mobile(b, base):
    for qs, tag in ((_F3_QS, "手機"), (_F3_QS + "&body=v2", "手機 body=v2")):
        c, pg, got = _f3_open(b, base, w=390, h=844, qs=qs)
        ok("績效總表（%s）：載入完成且獎勵層啟用" % tag, got and pg.evaluate("() => __world.rewards && __world.rewards.on"))
        if not got:
            continue
        try:
            ok("績效總表（%s）：頂端鈕直接看得到" % tag, pg.evaluate("() => { const b = document.getElementById('rwBtn'), r = b.getBoundingClientRect(), e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return r.width > 0 && (e === b || b.contains(e)); }"))
            _f3_shot(pg, "手機_頂列有績效總表鈕.png" if tag == "手機" else "手機_v2.png")
            pg.mouse.click(*pg.evaluate("() => { const r = document.getElementById('rwBtn').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }"))
            wait_until(pg, "() => !document.getElementById('ledger').hidden", 3000)
            _f3_ledger_flow(pg, True, tag)
            ok("績效總表（%s）：沒有主控台錯誤" % tag, not pg.errs, pg.errs[:3])
        finally:
            c.close()


def t_f3_jobless(b, base):
    c, pg, got = _f3_open(b, base)
    ok("遊民區：載入完成", got)
    if not got:
        return
    try:
        pg.evaluate("() => __world.setView('god', null, true)")
        pg.wait_for_timeout(1200)
        z = pg.evaluate("() => { const z = __world.outside.zone; return [z.x0, z.x1, z.z0, z.z1]; }")
        p1 = pg.evaluate(_F3_PROJ, [z[0] + 4, 0.1, z[2] + 1.2])
        ok("預設俯視：遊民區的一角（入口小路旁）露在畫面裡（%.0f, %.0f，畫面高 800）" % tuple(p1), 0 <= p1[0] <= 1280 and 0 <= p1[1] <= 780, p1)
        sg = pg.evaluate(_F3_PROJ, [24.0, 2.25, 32.8])
        ok("預設俯視：遊民區的木牌也看得到（%.0f, %.0f）" % tuple(sg), 0 <= sg[0] <= 1280 and 0 <= sg[1] <= 790, sg)
        _f3_shot(pg, "預設俯視_看得到遊民區.png")
        hint = pg.evaluate("() => { const h = document.getElementById('jlHint'); const r = h.getBoundingClientRect(); return [!h.hidden, h.textContent, r.right <= innerWidth, r.bottom <= innerHeight]; }")
        ok("預設俯視：遊民區中心不在畫面時，右下角有「▼ 無業遊民區」邊緣標示（%s）" % hint[1], hint[0] and hint[2] and hint[3], hint)
        # 點邊緣標示 → 飛過去
        pg.click("#jlHint")
        ok("點邊緣標示：鏡頭飛到遊民區，標示自己消失", wait_until(pg, "() => { const t = __world.controls.target, z = __world.outside.center; return Math.hypot(t.x - z.x, t.z - z.z) < 3 && document.getElementById('jlHint').hidden; }", 6000), _f3_target(pg))
        # 區域選單
        pg.evaluate("() => __world.setView('god', null, true)")
        pg.wait_for_timeout(900)
        pg.click("#areaBtn")
        ok("區域選單：有「無業遊民區」", pg.evaluate("() => !!document.querySelector('#areaPop [data-room=jobless]')"))
        _f3_shot(pg, "區域選單_遊民區.png")
        pg.click("#areaPop [data-room=jobless]")
        ok("區域選單 → 無業遊民區：鏡頭飛到遊民區（注視點落在區內）", wait_until(pg, "() => { const t = __world.controls.target, z = __world.outside.zone; return t.x > z.x0 && t.x < z.x1 && t.z > z.z0 - 1 && t.z < z.z1; }", 6000), _f3_target(pg))
        pg.wait_for_timeout(1200)
        sg = pg.evaluate(_F3_PROJ, [24.0, 2.25, 32.8])
        ok("飛到遊民區後：木牌、營火都在畫面裡", 0 <= sg[0] <= 1280 and 0 <= sg[1] <= 800 and pg.evaluate(_F3_PROJ, [30.2, 0.3, 36.6])[1] < 800, sg)
        ok("遊民區木牌：沒有人被開除時寫「目前沒有人待業」", pg.evaluate("() => __world.outside.signN") == 0)
        _f3_shot(pg, "遊民區_目前沒有人待業.png")
        # 開除鈕在資訊卡上半部，不用捲動
        pg.evaluate("() => { const c = [...__world.chars.values()].find(q => !q.spec.isCeo && !q.spec.pet && !q.away); window.__f3c = c.spec.id; __world.ui.showCard(c); }")
        pg.wait_for_timeout(400)
        pos = pg.evaluate("() => { const b = document.querySelector('#card [data-i=fire]'), r = b.getBoundingClientRect(), k = document.getElementById('card').getBoundingClientRect(); return [r.top, r.bottom, innerHeight, k.top, document.querySelectorAll('#card [data-i=fire]').length]; }")
        ok("資訊卡：「開除」鈕只有一顆、在動作格裡（不用捲動就看得到：%.0f～%.0f，畫面高 %d）" % (pos[0], pos[1], pos[2]), pos[4] == 1 and pos[1] <= pos[2] and pos[0] >= pos[3])
        _f3_shot(pg, "開除鈕位置.png")
        pg.click("#card [data-i=fire]")
        pg.wait_for_timeout(500)
        ok("按「開除」：先跳確認框，還沒有真的開除", pg.evaluate("() => !!document.getElementById('fireDlg') && __world.hr.fired.size === 0"))
        # 兩段式確認：第一次按「開除」只會變成「確定開除」，第二次才真的執行
        pg.click("#fireGo")
        pg.wait_for_timeout(200)
        btn = [pg.evaluate("() => document.getElementById('fireGo').textContent")]
        ok("確認框第一次按「開除」只是變成「確定開除」，還沒開除", btn[0] == "確定開除" and pg.evaluate("() => __world.hr.fired.size") == 0, btn)
        pg.click("#fireGo")
        wait_until(pg, "() => __world.hr.fired.size === 1", 4000)
        ok("第二次確認後同事被開除", pg.evaluate("() => __world.hr.fired.size") == 1)
        pg.wait_for_timeout(600)
        ok("開除後遊民區木牌改寫「目前 1 位待業中」", pg.evaluate("() => __world.outside.signN") == 1)
        pg.evaluate("() => { __world.hr.fired.size && __world.hr.rehire(window.__f3c); }")
        pg.wait_for_timeout(300)
        ok("遊民區：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_f3_jobless_mobile(b, base):
    c, pg, got = _f3_open(b, base, w=390, h=844)
    ok("遊民區（手機）：載入完成", got)
    if not got:
        return
    try:
        pg.evaluate("() => __world.setView('god', null, true)")
        pg.wait_for_timeout(1200)
        z = pg.evaluate("() => { const z = __world.outside.zone; return [z.x0, z.x1, z.z0, z.z1]; }")
        p1 = pg.evaluate(_F3_PROJ, [z[0] + 6, 0.1, z[2] + 1.5])
        ok("預設俯視（手機）：遊民區露出一部分（%.0f, %.0f）" % tuple(p1), 0 <= p1[0] <= 390 and 0 <= p1[1] <= 844, p1)
        hint = pg.evaluate("() => { const h = document.getElementById('jlHint'), r = h.getBoundingClientRect(); return [!h.hidden, r.left >= 0, r.right <= innerWidth, r.bottom <= innerHeight, r.height]; }")
        ok("預設俯視（手機）：有邊緣標示、在畫面內、高 ≥ 36", hint[0] and hint[1] and hint[2] and hint[3] and hint[4] >= 36, hint)
        _f3_shot(pg, "手機_預設俯視_看得到遊民區.png")
        pg.click("#moreBtn")
        pg.wait_for_timeout(300)
        pg.click("#areaBtn")
        pg.wait_for_timeout(300)
        pg.click("#areaPop [data-room=jobless]")
        ok("區域選單（手機）→ 無業遊民區：飛過去", wait_until(pg, "() => { const t = __world.controls.target, z = __world.outside.zone; return t.x > z.x0 && t.x < z.x1 && t.z > z.z0 - 2 && t.z < z.z1 + 2; }", 6000))
        pg.evaluate("() => { const c = [...__world.chars.values()].find(q => !q.spec.isCeo && !q.spec.pet && !q.away); __world.ui.showCard(c); }")
        pg.wait_for_timeout(400)
        pos = pg.evaluate("() => { const b = document.querySelector('#card [data-i=fire]').getBoundingClientRect(); return [b.top, b.bottom, innerHeight, b.height]; }")
        ok("資訊卡（手機）：「開除」鈕不用捲動就看得到（%.0f～%.0f，畫面高 %d），高 ≥ 40" % (pos[0], pos[1], pos[2]), pos[1] <= pos[2] and pos[3] >= 40, pos)
        _f3_shot(pg, "手機_開除鈕位置.png")
        ok("遊民區（手機）：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_f3_model(b, base):
    r = {}
    for tag, qs in (("預設", _F3_QS), ("body=v1", _F3_QS + "&body=v1"), ("body=v2", _F3_QS + "&body=v2")):
        c, pg, got = _f3_open(b, base, qs=qs)
        ok("角色模型（%s）：載入完成" % tag, got)
        if not got:
            continue
        try:
            r[tag] = pg.evaluate("() => { let n = 0, t = 0; for (const c of __world.chars.values()) { if (c.spec.pet) continue; t++; if (c.newModel) n++; } return [n, t]; }")
            if tag == "預設":
                pg.evaluate("() => __world.setView('ceo', null, true)")
                pg.wait_for_timeout(1500)
                _f3_shot(pg, "預設新角色.png")
            ok("角色模型（%s）：沒有主控台錯誤" % tag, not pg.errs, pg.errs[:3])
        finally:
            c.close()
    if "預設" in r and "body=v1" in r:
        ok("預設網址載入的是新模型（%d／%d 位是新模型：糰糰、垂垂、布布三個物種，其餘物種仍是舊系統），?body=v1 是舊的（%d 位新模型）" % (r["預設"][0], r["預設"][1], r["body=v1"][0]), r["預設"][0] >= 3 and r["body=v1"][0] == 0, r)
    if "預設" in r and "body=v2" in r:
        ok("?body=v2 與預設一樣是新模型", r["body=v2"][0] == r["預設"][0], r)


def t_f3_layout(b, base):
    for w, h, tag in ((1280, 800, "1280"), (390, 844, "390")):
        c, pg, got = _f3_open(b, base, w=w, h=h)
        ok("版面（%s）：載入完成" % tag, got)
        if not got:
            continue
        try:
            pg.evaluate("() => __world.setView('god', null, true)")
            pg.wait_for_timeout(1000)
            bad, n = _f3_overlaps(pg, ["#bar .ttl", "#viewSeg", "#moreBtn", "#areaBtn", "#demoBtn", "#speedSeg", "#editBtn", "#rwBtn", "#pwBtn", ".cm-hint", ".dt-chip", "#jlHint"])
            ok("版面（%s）：頂列、提示列、邊緣標示兩兩不重疊（量了 %d 個元素）" % (tag, n), not bad, bad)
            ok("版面（%s）：沒有橫向捲軸" % tag, pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
            txt = pg.evaluate("() => document.body.innerText")
            ok("版面（%s）：畫面文字不含禁用字" % tag, not _F3_FORBID.search(txt), _F3_FORBID.search(txt))
            ok("版面（%s）：最小字 ≥ 11px（邊緣標示 %s）" % (tag, pg.evaluate("() => getComputedStyle(document.getElementById('jlHint')).fontSize")), pg.evaluate("() => parseFloat(getComputedStyle(document.getElementById('jlHint')).fontSize)") >= 11)
            ok("版面（%s）：沒有主控台錯誤" % tag, not pg.errs, pg.errs[:3])
        finally:
            c.close()


register("辦公室第三輪修正-拖曳平移", lambda pg, b, base, code: t_f3_pan(b, base))
register("辦公室第三輪修正-手機觸控", lambda pg, b, base, code: t_f3_pan_touch(b, base))
register("辦公室第三輪修正-績效總表桌機", lambda pg, b, base, code: t_f3_ledger_desktop(b, base))
register("辦公室第三輪修正-績效總表手機", lambda pg, b, base, code: t_f3_ledger_mobile(b, base))
register("辦公室第三輪修正-遊民區", lambda pg, b, base, code: t_f3_jobless(b, base))
register("辦公室第三輪修正-遊民區手機", lambda pg, b, base, code: t_f3_jobless_mobile(b, base))
register("辦公室第三輪修正-新角色預設", lambda pg, b, base, code: t_f3_model(b, base))
register("辦公室第三輪修正-版面", lambda pg, b, base, code: t_f3_layout(b, base))
