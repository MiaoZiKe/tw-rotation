# 驗收段落「辦公室操控」：AI Office 3D 辦公室（site/office/world.html）的
#   ① 點選角色＝選取（光環、名牌提亮、資訊卡照舊）② 鍵盤操控（方向鍵／WASD、連按兩次跑步、Space 跳、碰撞不穿牆）
#   ③ 靠近同事「按 E 溝通」、F 揮手 ④ Esc 結束後角色自己走回座位 ⑤ 手機虛擬搖桿
#   ⑥ 資訊卡三個狀態格可點篩選、任務列可展開 ⑦ 佈告欄點開面板 ⑧ 任何視角都能用滑鼠旋轉／平移／縮放／雙擊地面移動。
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用；全部是真的操作（滑鼠、鍵盤、觸控事件），並驗「畫面／狀態真的改變」。
# 軟體繪圖（swiftshader）很慢，所以量測一律用場景的模擬時間（__world.time），不用牆鐘時間。
# 環境變數 PILOT_SHOTS 指到資料夾時，順便把驗收畫面存成截圖（交件用）。
# flake8: noqa

import math as _m
import os as _os


def _root(base):
    return base.split("/index.html")[0].rstrip("/")


def _open(b, base, w=1280, h=760, touch=False, qs="?ambient=0&q=low"):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    pg.wait_for_timeout(800)
    return c, pg, got


def _shot(pg, name):
    d = _os.environ.get("PILOT_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _pos(pg, cid):
    return pg.evaluate("(id) => { const c = __world.chars.get(id), p = c.object3D.position; return [p.x, p.z, p.y, __world.time]; }", cid)


def _scr(pg, cid, dy=30):
    r = pg.evaluate("(a) => { const c = __world.chars.get(a[0]); return [c._sx, c._sy + a[1]]; }", [cid, dy])
    return r


def _cam(pg):
    return pg.evaluate("""() => { const W = __world, c = W.camera, t = W.controls.target;
      return { az: Math.atan2(c.position.x - t.x, c.position.z - t.z), dist: c.position.distanceTo(t), tx: t.x, tz: t.z, tween: !!W.view.tween }; }""")


def _tween_done(pg, t=8000):
    return wait_until(pg, "() => !__world.view.tween", t)


def _rect(pg, sel):
    return pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e || e.hidden) return null; const r = e.getBoundingClientRect(); if (!r.width) return null;
      const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return null; return [r.left, r.top, r.right, r.bottom]; }""", sel)


def _overlap(a, b, pad=1):
    return a and b and not (a[2] <= b[0] + pad or b[2] <= a[0] + pad or a[3] <= b[1] + pad or b[3] <= a[1] + pad)


def _no_overlap(pg, sels):
    rs = [(s, _rect(pg, s)) for s in sels]
    bad = [(a[0], b[0]) for i, a in enumerate(rs) for b in rs[i + 1:] if _overlap(a[1], b[1])]
    return bad


def _hold(pg, key, ms):
    pg.keyboard.down(key)
    pg.wait_for_timeout(ms)
    pg.keyboard.up(key)


def _sim_speed(pg, cid, key, ms=1500):
    """按住 key ms 毫秒，回傳模擬時間內的平均速度（公尺／模擬秒）與位移向量"""
    p0 = _pos(pg, cid)
    pg.keyboard.down(key)
    pg.wait_for_timeout(ms)
    p1 = _pos(pg, cid)
    pg.keyboard.up(key)
    dt = max(1e-6, p1[3] - p0[3])
    return _m.hypot(p1[0] - p0[0], p1[1] - p0[1]) / dt, (p1[0] - p0[0], p1[1] - p0[1])


def _near_spot(pg, oid):
    return pg.evaluate("""(id) => { const W = __world, o = W.chars.get(id), p = o.object3D.position;
      for (const [dx, dz] of [[0.9, 0.9], [-0.9, 0.9], [0.9, -0.9], [-0.9, -0.9], [1.2, 0], [0, 1.2], [-1.2, 0], [0, -1.2]]) { const q = W.nav.nearestFree(p.x + dx, p.z + dz, 6); if (q && Math.hypot(q.x - p.x, q.z - p.z) > 0.85 && Math.hypot(q.x - p.x, q.z - p.z) < 1.6) return [q.x, q.z]; }
      return null; }""", oid)


def t_desktop(b, base):
    c, pg, got = _open(b, base)
    try:
        ok("辦公室操控：world.html 載入完成", got)
        if not got:
            return
        W = "__world"
        # ───────── 點選 → 選取效果 ─────────
        x, y = _scr(pg, "ceo")
        pg.mouse.click(x, y)
        ok("點角色：選取成立（pilot.sel）", wait_until(pg, "() => __world.pilot.sel && __world.pilot.sel.spec.id === 'ceo'", 6000))
        pg.wait_for_timeout(900)
        ok("選取效果：腳下光環出現", pg.evaluate("() => __world.pilot.halo.visible"))
        ok("選取效果：名牌提亮（.tag.sel）", pg.evaluate("() => !!document.querySelector('#labels .tag.sel')"))
        ok("既有資訊卡照舊出現（#card 顯示、有角色名）", pg.evaluate("() => !document.getElementById('card').hidden && document.querySelector('#card .hd b').textContent.includes('CEO')"))
        ok("提示卡出現，並寫明「按方向鍵開始操控」", pg.evaluate("() => { const t = document.querySelector('.pt-tips'); return !t.hidden && t.textContent.includes('按方向鍵開始操控'); }"))
        tips = pg.evaluate("() => document.querySelector('.pt-tips').textContent")
        ok("提示卡列出全部操作（方向鍵／WASD、連按兩次、Space、E、F、Esc）", all(k in tips for k in ["方向鍵", "WASD", "連按兩次", "Space", "E", "F", "Esc"]), tips)
        ok("選取但還沒按鍵時不接管（不改排程）", not pg.evaluate("() => __world.pilot.engaged"))
        pg.wait_for_timeout(300)
        _shot(pg, "選取效果.png")
        _shot(pg, "操作提示卡.png")
        ov = _no_overlap(pg, ["#card", ".pt-tips", ".cm-hint", "#bar", "#log"])
        ok("版面：資訊卡、提示卡、鏡頭小提示、工具列兩兩不重疊", not ov, ov)
        tag = pg.evaluate("() => { const e = document.querySelector('#labels .tag.sel'); const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }")
        ov2 = [s for s in ["#card", ".pt-tips", ".cm-hint", "#bar"] if _overlap(tag, _rect(pg, s))]
        ok("版面：選取名牌不與資訊卡／提示卡／工具列重疊", not ov2, ov2)

        # ───────── 提示卡收起、記住（localStorage） ─────────
        pg.click(".pt-min")
        ok("提示卡可收起（清單隱藏）", pg.evaluate("() => document.querySelector('.pt-tips').classList.contains('min') && getComputedStyle(document.querySelector('.pt-list')).display === 'none'"))
        ok("收起狀態記進 localStorage", pg.evaluate("() => localStorage.getItem('aiOffice.pilot.tips') === '0'"))
        pg.click(".pt-min")
        ok("再按一次可展開", pg.evaluate("() => !document.querySelector('.pt-tips').classList.contains('min')"))

        # ───────── 資訊卡：三個狀態格可點篩選 ─────────
        n = pg.evaluate("() => [...document.querySelectorAll('#cardKpi [data-k]')].map(b => +b.querySelector('b').textContent)")
        total = pg.evaluate("() => document.querySelectorAll('#cardList .row').length")
        ok("狀態格：預設顯示全部任務（筆數＝三格相加）", total == sum(n) and total > 0, (n, total))
        pg.click("#cardKpi [data-k='2']")
        rows = pg.evaluate("() => [...document.querySelectorAll('#cardList .row')].map(r => r.querySelector('.st').textContent)")
        ok("點「進行中」格：清單筆數等於格子數字、每列都是進行中", len(rows) == n[1] and all(s == "進行中" for s in rows), (n, rows))
        ok("被點的格子標成選取（aria-pressed、.on）", pg.evaluate("() => { const b = document.querySelector('#cardKpi [data-k=\"2\"]'); return b.getAttribute('aria-pressed') === 'true' && b.classList.contains('on'); }"))
        pg.click("#cardList .row")
        ok("點一列：細節展開（含狀態、時間、負責人）", pg.evaluate("() => { const d = document.querySelector('#cardList .det'); return !!d && d.textContent.includes('狀態') && d.textContent.includes('負責人') && d.textContent.includes('預估完成'); }"))
        ok("細節不出現空白列（每個 dd 都有字）", pg.evaluate("() => [...document.querySelectorAll('#cardList .det dd')].every(d => d.textContent.trim().length > 0)"))
        pg.click("#cardList .row")
        ok("再點同一列：細節收合", pg.evaluate("() => !document.querySelector('#cardList .det')"))
        for k, nm in ((1, "未完成"), (3, "已完成")):
            pg.click(f"#cardKpi [data-k='{k}']")
            rows = pg.evaluate("() => [...document.querySelectorAll('#cardList .row')].map(r => r.querySelector('.st').textContent)")
            ok(f"點「{nm}」格：筆數等於數字且每列都是{nm}", len(rows) == n[k - 1] and all(s == nm for s in rows), (n, rows))
        _shot(pg, "狀態格點開.png")
        pg.click("#cardKpi [data-k='3']")
        ok("再點同一格取消篩選：筆數回到全部", pg.evaluate("() => document.querySelectorAll('#cardList .row').length") == total)
        pg.focus("#cardKpi [data-k='2']")
        pg.keyboard.press("Enter")
        ok("鍵盤操作：Tab 到狀態格按 Enter 也能篩選", pg.evaluate("() => document.querySelector('#cardKpi [data-k=\"2\"]').classList.contains('on')"))
        pg.keyboard.press("Enter")
        pg.evaluate("() => document.activeElement.blur()")
        # 空狀態：找一個某狀態是 0 的角色
        zero = pg.evaluate("""() => { const W = __world; for (const [id, c] of W.chars) { const p = W.ui.progress(c.spec); const k = p.nTodo === 0 ? 1 : (p.nDoing === 0 ? 2 : (p.nDone === 0 ? 3 : 0)); if (k) return [id, k]; } return null; }""")
        if zero:
            pg.evaluate("(z) => { const W = __world; W.ui.showCard(W.chars.get(z[0])); }", zero)
            pg.click(f"#cardKpi [data-k='{zero[1]}']")
            ok("該狀態沒有任務時顯示「這個狀態目前沒有任務」", pg.evaluate("() => document.querySelector('#cardList .empty') && document.querySelector('#cardList .empty').textContent.includes('這個狀態目前沒有任務')"))
            pg.evaluate("() => { const W = __world; W.ui.showCard(W.pilot.sel); }")

        # ───────── 鍵盤：移動方向以鏡頭為準、走路速度 ─────────
        pg.evaluate("() => { document.activeElement && document.activeElement.blur(); }")
        pg.keyboard.down("ArrowUp")
        pg.wait_for_timeout(1800)
        ok("按方向鍵：接管（engaged）", pg.evaluate("() => __world.pilot.engaged"))
        pg.keyboard.up("ArrowUp")
        wait_until(pg, "() => !__world.pilot.engaging", 8000)
        pg.wait_for_timeout(500)
        # 穩定量測：先站定，再量 ArrowUp
        sp_walk, d = _sim_speed(pg, "ceo", "ArrowUp", 1600)
        fdir = pg.evaluate("() => { const W = __world, c = W.camera, t = W.controls.target; const x = t.x - c.position.x, z = t.z - c.position.z, l = Math.hypot(x, z); return [x / l, z / l]; }")
        mv = _m.hypot(*d)
        dot = (d[0] * fdir[0] + d[1] * fdir[1]) / mv if mv > 1e-6 else -1
        ok("↑：往遠離鏡頭的方向移動（位移與鏡頭前方夾角 < 15 度）", dot > 0.966, (dot, d))
        yaw = pg.evaluate("() => __world.chars.get('ceo').inner.yaw")
        want = _m.atan2(d[0], d[1])
        diff = abs((yaw - want + _m.pi) % (2 * _m.pi) - _m.pi)
        ok("角色朝向跟移動方向一致（誤差 < 0.35 弧度）", diff < 0.35, (yaw, want, diff))
        cfgwalk = pg.evaluate("() => __world.chars.get('ceo').inner.cfg.walk * (__world.chars.get('ceo').scale || 1)")
        ok("走路速度符合角色走路速度（±25%）", 0.75 * cfgwalk < sp_walk < 1.25 * cfgwalk, (sp_walk, cfgwalk))
        pg.wait_for_timeout(400)
        _, dd = _sim_speed(pg, "ceo", "KeyD", 1200)
        rdir = (-fdir[1], fdir[0])
        md = _m.hypot(*dd)
        ok("WASD 也能移動：D 往鏡頭右方", md > 0.3 and (dd[0] * rdir[0] + dd[1] * rdir[1]) / md > 0.9, (dd, rdir))
        _, dd = _sim_speed(pg, "ceo", "KeyW", 800)
        ok("WASD：W 往遠離鏡頭的方向", _m.hypot(*dd) > 0.2 and (dd[0] * fdir[0] + dd[1] * fdir[1]) / _m.hypot(*dd) > 0.9, dd)
        # 走路連拍（至少 6 格）
        _frames(pg, "走路連拍.png", "ArrowDown", 6, 420)

        # ───────── 跑步：連按兩次 ─────────
        pg.wait_for_timeout(400)
        pg.keyboard.down("ArrowRight"); pg.wait_for_timeout(60); pg.keyboard.up("ArrowRight"); pg.wait_for_timeout(90)
        p0 = _pos(pg, "ceo")
        pg.keyboard.down("ArrowRight"); pg.wait_for_timeout(1500)
        p1 = _pos(pg, "ceo")
        run_now = pg.evaluate("() => __world.pilot.run")
        pg.keyboard.up("ArrowRight")
        sp_run = _m.hypot(p1[0] - p0[0], p1[1] - p0[1]) / max(1e-6, p1[3] - p0[3])
        ok("同一方向 300 毫秒內連按兩次：進入跑步（pilot.run）", run_now)
        ok("跑步速度明顯高於走路（≥ 1.8 倍）", sp_run >= 1.8 * sp_walk, (sp_run, sp_walk))
        pg.wait_for_timeout(250)
        ok("放開方向鍵後回到走路（run 解除）", not pg.evaluate("() => __world.pilot.run"))
        sp2, _ = _sim_speed(pg, "ceo", "ArrowLeft", 1300)
        ok("再單按一次是走路速度（不殘留跑步）", sp2 < 1.4 * sp_walk, (sp2, sp_walk))
        _frames(pg, "跑步連拍.png", "ArrowUp", 6, 330, run=True)

        # ───────── 跳躍 ─────────
        pg.wait_for_timeout(500)
        pg.evaluate("() => { window.__ys = []; const f = () => { const c = __world.chars.get('ceo'); __ys.push([c.inner.pos.y, c.inner.sq, __world.time]); if (__ys.length < 600) requestAnimationFrame(f); }; f(); }")
        pg.keyboard.press("Space")
        pg.wait_for_timeout(300)
        _shot(pg, "_jump_mid.png")
        pg.wait_for_timeout(2500)
        ys = pg.evaluate("() => __ys")
        ymax = max(v[0] for v in ys)
        ipeak = [v[0] for v in ys].index(ymax)
        ok("Space：高度先升（最高 ≥ 0.3 公尺）", ymax >= 0.3, ymax)
        ok("Space：之後回到地面（最後 ≈ 0）", ys[-1][0] < 0.02, ys[-1])
        ok("起跳前先上升、最高點之後下降（有重力）", ys[ipeak - 1][0] < ymax and ys[min(len(ys) - 1, ipeak + 3)][0] < ymax)
        sqmin = min(v[1] for v in ys[ipeak:])
        ok("落地有壓縮回彈（squash 小於 -0.1 後回升）", sqmin < -0.1 and ys[-1][1] > sqmin + 0.05, (sqmin, ys[-1][1]))
        _jump_strip(pg)

        # ───────── 碰撞：不穿牆、不穿家具、不出辦公室 ─────────
        pg.evaluate("() => { __world.speed = 4; window.__hit = { solid: 0, out: 0, n: 0, minx: 99, minz: 99, maxx: -99, maxz: -99 }; const f = () => { const W = __world, c = W.chars.get('ceo'), p = c.object3D.position; const h = __hit; h.n++; if (W.nav.isSolid(p.x, p.z)) h.solid++; if (p.x < 0.3 || p.x > W.layout.size.w - 0.3 || p.z < 0.3 || p.z > W.layout.size.d - 0.3) h.out++; h.minx = Math.min(h.minx, p.x); h.minz = Math.min(h.minz, p.z); h.maxx = Math.max(h.maxx, p.x); h.maxz = Math.max(h.maxz, p.z); requestAnimationFrame(f); }; f(); }")
        for key, ms in (("ArrowUp", 5000), ("ArrowLeft", 5000), ("ArrowDown", 6000), ("ArrowRight", 6000), ("ArrowUp", 4000), ("ArrowLeft", 4000)):
            pg.keyboard.down(key); pg.wait_for_timeout(60); pg.keyboard.up(key); pg.wait_for_timeout(80)    # 連按兩次 → 跑著撞牆，最容易穿牆
            pg.keyboard.down(key); pg.wait_for_timeout(ms); pg.keyboard.up(key)
        h = pg.evaluate("() => __hit")
        ok("朝四面牆一直跑：全程沒有任何一格站進牆或家具本體", h["solid"] == 0, h)
        ok("朝四面牆一直跑：沒有走出辦公室範圍", h["out"] == 0 and h["minx"] > 0.3 and h["minz"] > 0.3 and h["maxx"] < 39.7 and h["maxz"] < 29.7, h)
        pg.evaluate("() => { __world.speed = 1; }")
        ok("全程跑過多個方向後角色仍在辦公室內且可操控", pg.evaluate("() => __world.pilot.engaged"))

        # ───────── 與旁邊的同事溝通 ─────────
        oid = "data-steward"
        spot = _near_spot(pg, oid)
        ok("找得到同事旁邊的空位（測試前置）", bool(spot))
        pg.evaluate("(a) => { const W = __world, c = W.chars.get('ceo'); c.standAt(a[0], a[1], 0); }", spot)
        pg.wait_for_timeout(700)
        ok("靠近同事：對方頭上出現「按 E 溝通」", wait_until(pg, "() => { const h = document.querySelector('.pt-hint'); return !h.hidden && h.textContent.includes('按 E 溝通'); }", 6000))
        _shot(pg, "靠近提示_按E溝通.png")
        ov = _no_overlap(pg, [".pt-hint", ".pt-tips", ".cm-hint", "#bar", "#card"])
        ok("版面：「按 E 溝通」不與提示卡／工具列／資訊卡重疊", not ov, ov)
        pg.keyboard.press("KeyE")
        ok("按 E：操控的角色說話（出現泡泡）", wait_until(pg, "() => __world.chars.get('ceo').speech && __world.chars.get('ceo').speech.text.length > 0", 5000))
        ok("按 E：兩人面對面（我朝向對方）", pg.evaluate("""(id) => { const W = __world, a = W.chars.get('ceo'), o = W.chars.get(id), pa = a.object3D.position, po = o.object3D.position;
          const want = Math.atan2(po.x - pa.x, po.z - pa.z); return Math.abs(((a.heading - want + Math.PI) % (2 * Math.PI)) - Math.PI) < 0.5; }""", oid))
        ok("按 E：對方的資訊卡打開（顯示對方名字）", pg.evaluate("(id) => { const W = __world, o = W.chars.get(id); return !document.getElementById('card').hidden && document.querySelector('#card .hd b').textContent.includes(o.spec.nick); }", oid))
        ok("按 E：對方停下原本動作並回話（對方也出現泡泡）", wait_until(pg, "(id) => { const o = __world.chars.get(id); return o.speech && o.speech.text.length > 0; }".replace("(id)", "()").replace("get(id)", f"get('{oid}')"), 9000))
        pg.wait_for_timeout(300)
        _shot(pg, "溝通對話.png")
        bub = pg.evaluate("() => [...document.querySelectorAll('#labels .bub')].filter(b => b.style.transform.indexOf('-999') < 0).length")
        ok("對話泡泡顯示在畫面上（≥ 1 個）", bub >= 1, bub)
        ov = _no_overlap(pg, ["#card", ".pt-tips", ".cm-hint", "#bar"])
        ok("版面：資訊卡、提示卡、鏡頭提示、工具列不重疊（溝通中）", not ov, ov)
        bubs = pg.evaluate("() => [...document.querySelectorAll('#labels .bub')].filter(b => b.style.transform.indexOf('-999') < 0).map(b => { const r = b.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })")
        okb = all(not _overlap(a, c2) for i, a in enumerate(bubs) for c2 in bubs[i + 1:])
        ok("兩個對話泡泡彼此不重疊", okb, bubs)
        pc = [_rect(pg, s) for s in (".pt-tips", "#card")]
        ok("對話泡泡不蓋到提示卡與資訊卡", all(not _overlap(bb, r) for bb in bubs for r in pc if r), (bubs, pc))
        ok("演出結束後對方回到原本行為（坐回座位工作、不忙）", wait_until(pg, "() => { const o = __world.chars.get('data-steward'); return !o.busy && o.state === 'sit' && o.atDesk; }", 20000))
        ok("演出結束後我可繼續操控（沒被鎖住）", pg.evaluate("() => !__world.pilot.talking && __world.pilot.engaged"))
        # F 揮手
        pg.keyboard.press("KeyF")
        ok("按 F：我揮手（action = wave）", wait_until(pg, "() => __world.chars.get('ceo').action === 'wave'", 3000))
        ok("按 F：旁邊的同事也回揮", wait_until(pg, "() => __world.chars.get('data-steward').action === 'wave'", 6000))
        # 離開後提示消失
        pg.evaluate("() => { const W = __world; W.chars.get('ceo').standAt(20, 21.5, 0); }")
        ok("走遠後「按 E 溝通」消失", wait_until(pg, "() => document.querySelector('.pt-hint').hidden", 5000))
        pg.keyboard.press("KeyE")
        ok("沒人在旁邊按 E：提示「附近沒有可以溝通的同事」", wait_until(pg, "() => !document.getElementById('toast').hidden && document.getElementById('toast').textContent.includes('附近沒有')", 4000))

        # ───────── 面板開著時不移動（佈告欄） ─────────
        # 見下方佈告欄段落

        # ───────── Esc：解除選取，角色自己走回座位（不瞬移） ─────────
        pg.evaluate("() => { window.__jumps = 0; window.__last = null; window.__mx = 0; const f = () => { const p = __world.chars.get('ceo').object3D.position; if (__last) { const d = Math.hypot(p.x - __last[0], p.z - __last[1]); __mx = Math.max(__mx, d); } __last = [p.x, p.z]; requestAnimationFrame(f); }; f(); }")
        pg.keyboard.press("Escape")
        ok("Esc：選取解除（sel 為空）", pg.evaluate("() => __world.pilot.sel === null"))
        ok("Esc：光環、提示卡消失", pg.evaluate("() => !__world.pilot.halo.visible && document.querySelector('.pt-tips').hidden && !document.querySelector('#labels .tag.sel')"))
        ok("Esc：角色恢復自動行為（開始自己走回座位）", wait_until(pg, "() => __world.chars.get('ceo').state === 'walk' || (__world.chars.get('ceo').state === 'sit')", 8000))
        pg.evaluate("() => { __world.speed = 4; }")
        ok("Esc：走回座位並坐下、恢復工作", wait_until(pg, "() => { const c = __world.chars.get('ceo'); return c.state === 'sit' && c.atDesk && !c.busy; }", 60000))
        pg.evaluate("() => { __world.speed = 1; }")
        mx = pg.evaluate("() => __mx")
        ok("Esc 之後沒有瞬移（單幀位移 < 1.5 公尺）", mx < 1.5, mx)

        # ───────── 點空白處取消選取 ─────────
        x, y = _scr(pg, "ceo")
        pg.mouse.click(x, y)
        wait_until(pg, "() => __world.pilot.sel", 5000)
        pg.mouse.click(1100, 250)
        ok("點空白處：取消選取（0.3 秒後）", wait_until(pg, "() => __world.pilot.sel === null", 3000))

        # ───────── 全程錯誤 ─────────
        ok("辦公室操控：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _frames(pg, name, key, n, gap, run=False):
    """按住方向鍵，每隔 gap 毫秒截一格（只截角色附近），拼成一張連拍圖"""
    d = _os.environ.get("PILOT_SHOTS")
    if not d:
        return
    from PIL import Image
    import io
    if run:
        pg.keyboard.down(key); pg.wait_for_timeout(60); pg.keyboard.up(key); pg.wait_for_timeout(80)
    pg.keyboard.down(key)
    ims = []
    for i in range(n):
        pg.wait_for_timeout(gap)
        x, y = _scr(pg, "ceo", 70)
        x = max(150, min(1130, x)); y = max(150, min(610, y))
        ims.append(Image.open(io.BytesIO(pg.screenshot(clip={"x": x - 150, "y": y - 150, "width": 300, "height": 300}))))
    pg.keyboard.up(key)
    W = Image.new("RGB", (300 * 3, 300 * ((n + 2) // 3)), "white")
    for i, im in enumerate(ims):
        W.paste(im, ((i % 3) * 300, (i // 3) * 300))
    _os.makedirs(d, exist_ok=True)
    W.save(_os.path.join(d, name))


def _jump_strip(pg):
    d = _os.environ.get("PILOT_SHOTS")
    if not d:
        return
    from PIL import Image
    import io
    pg.wait_for_timeout(400)
    pg.evaluate("() => { __world.speed = 0.25; }")
    pg.keyboard.press("Space")
    ims = []
    for i in range(6):
        pg.wait_for_timeout(260)
        x, y = _scr(pg, "ceo", 70)
        x = max(150, min(1130, x)); y = max(150, min(610, y))
        ims.append(Image.open(io.BytesIO(pg.screenshot(clip={"x": x - 150, "y": y - 150, "width": 300, "height": 300}))))
    pg.evaluate("() => { __world.speed = 1; }")
    W = Image.new("RGB", (300 * 3, 600), "white")
    for i, im in enumerate(ims):
        W.paste(im, ((i % 3) * 300, (i // 3) * 300))
    W.save(_os.path.join(d, "跳躍連拍.png"))
    pg.wait_for_timeout(1500)


def t_board(b, base):
    c, pg, got = _open(b, base)
    try:
        ok("佈告欄：頁面載入", got)
        if not got:
            return
        # 先選取並接管 CEO，驗證「操控中點佈告欄仍可開面板、面板開著方向鍵不移動」
        x, y = _scr(pg, "ceo")
        pg.mouse.click(x, y)
        wait_until(pg, "() => __world.pilot.sel", 5000)
        pg.keyboard.down("ArrowUp"); pg.wait_for_timeout(900); pg.keyboard.up("ArrowUp")
        ok("（前置）已接管 CEO", pg.evaluate("() => __world.pilot.engaged"))
        pg.evaluate("() => __world.jumpTo('legal')")
        _tween_done(pg, 12000)
        pg.wait_for_timeout(600)
        pt = pg.evaluate("""() => { const W = __world, THREE = W.THREE; const m = W.boardsMesh.find(m => m.userData.board === 'legal'); const b = new THREE.Box3().setFromObject(m), v = b.getCenter(new THREE.Vector3()).project(W.camera);
          const r = document.getElementById('cv').getBoundingClientRect(); return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height]; }""")
        pg.mouse.move(pt[0] - 40, pt[1] + 90)
        pg.mouse.move(pt[0], pt[1])
        pg.wait_for_timeout(400)
        ok("滑鼠停在佈告欄上：游標變手指", pg.evaluate("() => document.getElementById('cv').style.cursor === 'pointer'"))
        ok("滑鼠停在佈告欄上：板子微微提亮（外框顯示）", pg.evaluate("() => __world.boardHover.visible"))
        pg.mouse.move(pt[0] + 300, pt[1] + 200)
        pg.wait_for_timeout(300)
        ok("滑鼠移開後游標與提亮都還原", pg.evaluate("() => document.getElementById('cv').style.cursor === '' && !__world.boardHover.visible"))
        pg.mouse.move(pt[0], pt[1])
        pg.wait_for_timeout(300)
        pg.mouse.click(pt[0], pt[1])
        ok("點佈告欄：面板出現", wait_until(pg, "() => !document.getElementById('board').hidden", 5000))
        txt = pg.evaluate("() => document.getElementById('board').textContent")
        ok("面板含部門名稱（法遵與資安部）", "法遵" in txt, txt[:80])
        ok("面板含人數與主管", "人數" in txt and "主管" in txt, txt[:120])
        nrows = pg.evaluate("() => document.querySelectorAll('#boardList .row').length")
        ok("面板含至少一筆事項（便利貼公告對應的成員事項）", nrows >= 1, nrows)
        ok("面板含便利貼公告", pg.evaluate("() => document.querySelectorAll('#board .note').length") >= 1)
        ok("操控中點佈告欄：仍在操控（沒被取消選取）", pg.evaluate("() => __world.pilot.sel && __world.pilot.engaged"))
        pg.click("#boardKpi [data-bk='3']")
        rows = pg.evaluate("() => [...document.querySelectorAll('#boardList .row')].map(r => r.querySelector('.st').textContent)")
        n3 = pg.evaluate("() => +document.querySelector('#boardKpi [data-bk=\"3\"] b').textContent")
        ok("面板事項彙總：點「已完成」→ 筆數等於格子數字、每列都是已完成", len(rows) == n3 and all(s == "已完成" for s in rows), (n3, rows))
        pg.click("#boardList .row")
        ok("面板：點一列展開細節", pg.evaluate("() => !!document.querySelector('#boardList .det')"))
        _shot(pg, "佈告欄面板.png")
        ov = _no_overlap(pg, ["#board", ".pt-tips", ".cm-hint", "#bar", "#card"])
        ok("版面：佈告欄面板、提示卡、鏡頭提示、工具列兩兩不重疊", not ov, ov)
        p0 = _pos(pg, "ceo")
        pg.keyboard.down("ArrowUp"); pg.wait_for_timeout(900); pg.keyboard.up("ArrowUp")
        p1 = _pos(pg, "ceo")
        ok("面板開著時按方向鍵不移動角色", _m.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 0.05, (p0, p1))
        pg.keyboard.press("Escape")
        ok("Esc：關閉佈告欄面板", pg.evaluate("() => document.getElementById('board').hidden"))
        ok("Esc 只關面板，操控仍在（再按 Esc 才結束）", pg.evaluate("() => !!__world.pilot.sel"))
        pg.keyboard.down("ArrowDown"); pg.wait_for_timeout(900); pg.keyboard.up("ArrowDown")
        p2 = _pos(pg, "ceo")
        ok("關掉面板後方向鍵恢復可操控", _m.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 0.2, (p1, p2))
        pg.mouse.click(pt[0], pt[1])
        ok("再點佈告欄可重新打開；× 鈕可關閉", pg.evaluate("() => !document.getElementById('board').hidden"))
        pg.click("#board .x")
        ok("面板關閉鈕有效", pg.evaluate("() => document.getElementById('board').hidden"))
        # 總佈告欄（CEO）
        pg.evaluate("() => __world.ui.showBoard('ceo')")
        ok("CEO 總佈告欄面板：含 CEO 與事項", pg.evaluate("() => document.getElementById('board').textContent.includes('CEO') && document.querySelectorAll('#boardList .row').length >= 1"))
        pg.keyboard.press("Escape")
        ok("佈告欄段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_camera(b, base):
    c, pg, got = _open(b, base)
    try:
        ok("鏡頭：頁面載入", got)
        if not got:
            return
        pg.click("#viewSeg [data-v='god']")
        _tween_done(pg)
        pg.click("#viewSeg [data-v='ceo']")
        ok("按「CEO 視角」：運鏡開始後會結束（控制權交還）", _tween_done(pg, 12000))
        pg.wait_for_timeout(500)
        c0 = _cam(pg)
        pg.mouse.move(640, 380); pg.mouse.down()
        for i in range(1, 9):
            pg.mouse.move(640 + i * 45, 380)
            pg.wait_for_timeout(40)
        pg.mouse.up()
        pg.wait_for_timeout(500)
        c1 = _cam(pg)
        da = abs((c1["az"] - c0["az"] + _m.pi) % (2 * _m.pi) - _m.pi)
        ok("CEO 視角下左鍵拖曳：方位角真的改變（> 0.2 弧度）", da > 0.2, da)
        pg.wait_for_timeout(2500)
        c2 = _cam(pg)
        d2 = abs((c2["az"] - c1["az"] + _m.pi) % (2 * _m.pi) - _m.pi)
        ok("兩秒後鏡頭沒有被拉回（方位角不變 ±0.03）", d2 < 0.03, d2)
        ok("拖曳旋轉不暫停跟隨（只有平移才會）", not pg.evaluate("() => __world.view.detached"))
        pg.mouse.move(640, 380); pg.mouse.wheel(0, 400)
        pg.wait_for_timeout(700)
        c3 = _cam(pg)
        ok("滾輪：距離改變", abs(c3["dist"] - c2["dist"]) > 0.3, (c2["dist"], c3["dist"]))
        pg.mouse.move(640, 380); pg.mouse.wheel(0, -4000)
        pg.wait_for_timeout(800)
        ok("縮放有下限（不縮進牆裡，距離 ≥ 3）", _cam(pg)["dist"] >= 2.99, _cam(pg)["dist"])
        pg.mouse.wheel(0, 40000)
        pg.wait_for_timeout(800)
        ok("縮放有上限（不飛出辦公室太遠，距離 ≤ 110）", _cam(pg)["dist"] <= 110.5, _cam(pg)["dist"])
        pg.mouse.wheel(0, -30000)
        pg.wait_for_timeout(800)
        c4 = _cam(pg)
        pg.mouse.move(640, 380); pg.mouse.down(button="right")
        for i in range(1, 9):
            pg.mouse.move(640 + i * 25, 380 + i * 12)
            pg.wait_for_timeout(40)
        pg.mouse.up(button="right")
        pg.wait_for_timeout(500)
        c5 = _cam(pg)
        ok("右鍵拖曳：注視點改變（平移 > 0.5 公尺）", _m.hypot(c5["tx"] - c4["tx"], c5["tz"] - c4["tz"]) > 0.5, (c4, c5))
        ok("手動平移之後暫停跟隨，並出現「回到角色」鈕", pg.evaluate("() => __world.view.detached && !document.querySelector('.cm-back').hidden"))
        pg.wait_for_timeout(2200)
        c6 = _cam(pg)
        ok("平移後兩秒鏡頭沒有被拉回", _m.hypot(c6["tx"] - c5["tx"], c6["tz"] - c5["tz"]) < 0.1, (c5, c6))
        pg.keyboard.down("Shift")
        pg.mouse.move(640, 380); pg.mouse.down()
        for i in range(1, 7):
            pg.mouse.move(640 - i * 30, 380)
            pg.wait_for_timeout(40)
        pg.mouse.up(); pg.keyboard.up("Shift")
        pg.wait_for_timeout(400)
        c7 = _cam(pg)
        ok("Shift＋左鍵拖曳也能平移", _m.hypot(c7["tx"] - c6["tx"], c7["tz"] - c6["tz"]) > 0.4, (c6, c7))
        # 平移範圍有限
        for i in range(10):
            pg.mouse.move(900, 400); pg.mouse.down(button="right"); pg.mouse.move(100, 400, steps=6); pg.mouse.up(button="right")
        pg.wait_for_timeout(500)
        c8 = _cam(pg)
        ok("平移有範圍（注視點不會離開辦公室太遠）", -6.1 <= c8["tx"] <= 46.1 and -6.1 <= c8["tz"] <= 40.1, c8)
        # 雙擊地面
        pg.click("#viewSeg [data-v='god']")
        _tween_done(pg)
        pg.wait_for_timeout(400)
        t0 = _cam(pg)
        # 找一個地面點：畫面上偏右下、不是角色與佈告欄的位置
        gx, gy = 900, 520
        exp = pg.evaluate("""(a) => { const W = __world, T = W.THREE, r = document.getElementById('cv').getBoundingClientRect(), ray = new T.Raycaster(), n = new T.Vector2((a[0] - r.left) / r.width * 2 - 1, -(a[1] - r.top) / r.height * 2 + 1);
          ray.setFromCamera(n, W.camera); const p = new T.Vector3(); ray.ray.intersectPlane(new T.Plane(new T.Vector3(0, 1, 0), 0), p); return [p.x, p.z]; }""", [gx, gy])
        pg.mouse.dblclick(gx, gy)
        _tween_done(pg, 8000)
        pg.wait_for_timeout(500)
        t1 = _cam(pg)
        ok("雙擊地面：注視點移到該處附近（< 1.5 公尺）", _m.hypot(t1["tx"] - exp[0], t1["tz"] - exp[1]) < 1.5, (exp, t1))
        ok("雙擊地面：注視點確實改變", _m.hypot(t1["tx"] - t0["tx"], t1["tz"] - t0["tz"]) > 1.0, (t0, t1))
        # 跟隨角色 → 平移 → 回到角色
        x, y = _scr(pg, "ceo")
        pg.click("#viewSeg [data-v='ceo']")
        _tween_done(pg, 12000)
        pg.wait_for_timeout(400)
        pg.mouse.move(640, 380); pg.mouse.down(button="right"); pg.mouse.move(900, 500, steps=6); pg.mouse.up(button="right")
        pg.wait_for_timeout(400)
        ok("（前置）平移後進入暫停跟隨狀態", pg.evaluate("() => __world.view.detached"))
        a0 = _cam(pg)
        pg.click(".cm-back")
        pg.wait_for_timeout(2500)
        a1 = _cam(pg)
        ceo = _pos(pg, "ceo")
        ok("按「回到角色」：恢復跟隨並平順拉回角色（注視點靠近 CEO）", (not pg.evaluate("() => __world.view.detached")) and _m.hypot(a1["tx"] - ceo[0], a1["tz"] - ceo[1]) < 3.5, (a1, ceo))
        ok("按「回到角色」之後鏡頭按鈕隱藏", pg.evaluate("() => document.querySelector('.cm-back').hidden"))
        # 操控角色：跟隨 + 手動平移暫停 + 角色再次移動就接回
        x, y = _scr(pg, "ceo")
        pg.mouse.click(x, y)
        wait_until(pg, "() => __world.pilot.sel", 5000)
        _tween_done(pg, 12000)
        pg.keyboard.down("ArrowUp"); pg.wait_for_timeout(1500); pg.keyboard.up("ArrowUp")
        pg.mouse.move(640, 380); pg.mouse.down(button="right"); pg.mouse.move(800, 450, steps=6); pg.mouse.up(button="right")
        pg.wait_for_timeout(300)
        ok("操控中手動平移：暫停自動跟隨", pg.evaluate("() => __world.view.detached"))
        pg.keyboard.down("ArrowDown"); pg.wait_for_timeout(1500); pg.keyboard.up("ArrowDown")
        ok("角色再次移動：自動接回跟隨", wait_until(pg, "() => !__world.view.detached", 4000))
        az0 = _cam(pg)["az"]
        pg.mouse.move(640, 380); pg.mouse.down(); pg.mouse.move(800, 380, steps=8); pg.mouse.up()
        pg.wait_for_timeout(400)
        ok("操控中仍可左鍵旋轉", abs((_cam(pg)["az"] - az0 + _m.pi) % (2 * _m.pi) - _m.pi) > 0.1)
        # 鏡頭小提示
        ok("鏡頭操作小提示出現並寫明四種操作", pg.evaluate("() => { const t = document.querySelector('.cm-hint').textContent; return ['左鍵拖曳旋轉', '右鍵拖曳平移', '滾輪縮放', '雙擊地面移動'].every(k => t.includes(k)); }"))
        pg.click(".cm-x")
        ok("鏡頭小提示可收起並記住", pg.evaluate("() => !!document.querySelector('.cm-q') && localStorage.getItem('aiOffice.camhint') === '0'"))
        pg.click(".cm-q")
        pg.keyboard.press("Escape")
        # 雙擊地面時不誤取消選取
        x, y = _scr(pg, "ceo")
        pg.mouse.click(x, y)
        wait_until(pg, "() => __world.pilot.sel", 5000)
        pg.mouse.dblclick(900, 560)
        pg.wait_for_timeout(900)
        ok("操控中雙擊地面：鏡頭移動但不取消選取", pg.evaluate("() => !!__world.pilot.sel"))
        pg.keyboard.press("Escape")
        # 截圖：CEO 視角下用滑鼠移動後
        pg.click("#viewSeg [data-v='ceo']")
        _tween_done(pg, 12000)
        pg.mouse.move(640, 380); pg.mouse.down()
        for i in range(1, 9):
            pg.mouse.move(640 + i * 30, 380 - i * 4)
            pg.wait_for_timeout(40)
        pg.mouse.up()
        pg.mouse.move(640, 380); pg.mouse.down(button="right"); pg.mouse.move(520, 330, steps=6); pg.mouse.up(button="right")
        pg.mouse.wheel(0, 300)
        pg.wait_for_timeout(1200)
        _shot(pg, "CEO視角_滑鼠移動後.png")
        ov = _no_overlap(pg, [".cm-hint", "#bar", "#card", ".pt-tips"])
        ok("版面：鏡頭小提示與工具列、面板不重疊", not ov, ov)
        ok("鏡頭段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_mobile(b, base):
    c, pg, got = _open(b, base, 390, 844, touch=True, qs="?ambient=0")
    try:
        ok("手機：頁面載入", got)
        if not got:
            return
        ok("手機：沒有選取時看不到虛擬搖桿", pg.evaluate("() => document.querySelector('.pt-pad').hidden"))
        x, y = _scr(pg, "ceo")
        pg.touchscreen.tap(x, y)
        ok("手機：點角色選取", wait_until(pg, "() => __world.pilot.sel", 6000))
        pg.wait_for_timeout(900)
        ok("手機：出現虛擬搖桿與跳／溝通／揮手鈕", pg.evaluate("() => !document.querySelector('.pt-pad').hidden && !!document.querySelector('.pt-joy') && document.querySelectorAll('.pt-b').length === 3 && getComputedStyle(document.querySelector('.pt-joy')).display !== 'none'"))
        sizes = pg.evaluate("() => [...document.querySelectorAll('.pt-b, .pt-th button')].map(b => { const r = b.getBoundingClientRect(); return [b.textContent.trim(), Math.round(r.width), Math.round(r.height)]; })")
        ok("手機：所有按鈕至少 44px", all(w >= 44 and h >= 44 for _, w, h in sizes), sizes)
        ok("手機：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
        joy = _rect(pg, ".pt-joy")
        btns = _rect(pg, ".pt-btns")
        ok("手機：搖桿在左下、按鈕在右下（固定位置）", joy[0] < 60 and joy[3] > 600 and btns[2] > 330 and btns[3] > 600, (joy, btns))
        ov = _no_overlap(pg, [".pt-joy", ".pt-btns", ".pt-tips", "#card", "#bar", ".cm-hint"])
        ok("手機：搖桿、按鈕、提示卡、資訊卡、工具列、鏡頭提示兩兩不重疊", not ov, ov)
        ok("手機：資訊卡不超出螢幕", pg.evaluate("() => { const r = document.getElementById('card').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight + 1 && r.top >= 0; }"))
        _shot(pg, "手機_虛擬搖桿.png")
        # 拖動搖桿（觸控指標事件）
        p0 = _pos(pg, "ceo")
        cx, cy = (joy[0] + joy[2]) / 2, (joy[1] + joy[3]) / 2
        pg.evaluate("""(a) => { const j = document.querySelector('.pt-joy'); const ev = (t, x, y) => j.dispatchEvent(new PointerEvent(t, { pointerId: 7, pointerType: 'touch', clientX: x, clientY: y, bubbles: true, isPrimary: true })); window.__ev = ev; ev('pointerdown', a[0], a[1]); ev('pointermove', a[0], a[1] - 30); }""", [cx, cy])
        pg.wait_for_timeout(400)
        ok("手機：拖動搖桿，旋鈕真的跟著移動", pg.evaluate("() => document.querySelector('.pt-knob').style.transform.includes('translate')"))
        pg.wait_for_timeout(1800)
        p1 = _pos(pg, "ceo")
        ok("手機：搖桿推動後角色真的移動", _m.hypot(p1[0] - p0[0], p1[1] - p0[1]) > 0.3, (p0, p1))
        ok("手機：搖桿接管了角色", pg.evaluate("() => __world.pilot.engaged"))
        pg.evaluate("(a) => { __ev('pointermove', a[0], a[1] - 60); }", [cx, cy])
        pg.wait_for_timeout(300)
        ok("手機：推到底＝跑步（旋鈕變紅、pilot.run）", pg.evaluate("() => __world.pilot.run && document.querySelector('.pt-joy').classList.contains('run')"))
        pg.evaluate("(a) => { __ev('pointerup', a[0], a[1]); }", [cx, cy])
        pg.wait_for_timeout(300)
        ok("手機：放開搖桿後旋鈕回中、角色停下", pg.evaluate("() => document.querySelector('.pt-knob').style.transform === '' && !__world.pilot.run"))
        # 跳躍鈕
        pg.evaluate("() => { window.__ym = 0; const f = () => { __ym = Math.max(__ym, __world.chars.get('ceo').inner.pos.y); requestAnimationFrame(f); }; f(); }")
        jr = _rect(pg, ".pt-jump")
        pg.touchscreen.tap((jr[0] + jr[2]) / 2, (jr[1] + jr[3]) / 2)
        pg.wait_for_timeout(1500)
        ok("手機：跳鈕讓角色跳起來", pg.evaluate("() => __ym") > 0.25, pg.evaluate("() => __ym"))
        # 溝通鈕
        pg.evaluate("() => { __world.chars.get('ceo').speech = null; }")
        spot = _near_spot(pg, "data-steward")
        pg.evaluate("(a) => { __world.chars.get('ceo').standAt(a[0], a[1], 0); }", spot)
        pg.wait_for_timeout(800)
        ok("手機：靠近同事時溝通鈕亮起、提示改成「點溝通鈕」", pg.evaluate("() => document.querySelector('.pt-talk').classList.contains('ready') && document.querySelector('.pt-hint').textContent.includes('溝通')"))
        tr = _rect(pg, ".pt-talk")
        pg.touchscreen.tap((tr[0] + tr[2]) / 2, (tr[1] + tr[3]) / 2)
        ok("手機：點溝通鈕開始對話（出現泡泡）", wait_until(pg, "() => __world.chars.get('ceo').speech", 5000))
        wait_until(pg, "() => __world.chars.get('data-steward').speech", 6000)
        pg.wait_for_timeout(300)
        ok("手機：溝通時對方資訊卡不遮住搖桿與按鈕", not _no_overlap(pg, [".pt-joy", ".pt-btns", "#card"]), _no_overlap(pg, [".pt-joy", ".pt-btns", "#card"]))
        ok("手機：資訊卡仍在螢幕內", pg.evaluate("() => { const r = document.getElementById('card').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0; }"))
        ok("手機：沒有橫向捲軸（溝通中）", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
        # 提示卡：預設收起（手機）、字不小於 11px
        ok("手機：提示卡預設收起", pg.evaluate("() => document.querySelector('.pt-tips').classList.contains('min')"))
        fs = pg.evaluate("() => [...document.querySelectorAll('.pt-tips *, .cm-hint *, .pt-b')].filter(e => e.children.length === 0 && e.textContent.trim() && e.offsetParent).map(e => parseFloat(getComputedStyle(e).fontSize))")
        ok("手機：操控介面文字都 ≥ 11px", all(f >= 11 for f in fs), fs)
        # 手機點佈告欄
        pg.evaluate("() => __world.jumpTo('legal')")
        _tween_done(pg, 12000)
        pg.wait_for_timeout(600)
        pt = pg.evaluate("""() => { const W = __world, THREE = W.THREE; const m = W.boardsMesh.find(m => m.userData.board === 'legal'); const v = new THREE.Box3().setFromObject(m).getCenter(new THREE.Vector3()).project(W.camera);
          const r = document.getElementById('cv').getBoundingClientRect(); return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height]; }""")
        pg.touchscreen.tap(pt[0], pt[1])
        ok("手機：點佈告欄開面板", wait_until(pg, "() => !document.getElementById('board').hidden", 5000))
        ok("手機：佈告欄面板不超出螢幕", pg.evaluate("() => { const r = document.getElementById('board').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight + 1; }"))
        ok("手機：佈告欄面板有關閉鈕且可關", (pg.click("#board .x") or True) and pg.evaluate("() => document.getElementById('board').hidden"))
        ok("手機段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_all(b, base):
    t_desktop(b, base)
    t_board(b, base)
    t_camera(b, base)
    t_mobile(b, base)


register("辦公室操控", lambda pg, b, base, code: t_all(b, base))
