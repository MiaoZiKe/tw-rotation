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


def _open(b, base, w=1280, h=760, touch=False, qs="?ambient=0&q=low&view=ceo"):   # 預設進場是俯視；這些操控流程要從 CEO 視角開始，所以帶 view=ceo（預設視角另有 t_view 驗）
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    # 軟體繪圖下每幀的模擬時間很短（實測模擬時間只有牆鐘的 1/8），播放速度調成 8 倍讓模擬時間約等於牆鐘；
    # 物理子步仍固定 ≤ 0.034 秒，所以行為與 1 倍速一致，只是不用空等。
    if got:
        pg.evaluate("() => { __world.speed = 8; }")
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


def _settle(pg, tries=30):
    """等阻尼的餘動停下來（軟體繪圖幀率很低，OrbitControls 的阻尼是「每幀」衰減，要很多秒才停；真實 60 幀約 0.3 秒就停）"""
    last = _cam(pg)
    for _ in range(tries):
        pg.wait_for_timeout(700)
        cur = _cam(pg)
        if abs(cur["az"] - last["az"]) < 0.002 and abs(cur["dist"] - last["dist"]) < 0.01 and _m.hypot(cur["tx"] - last["tx"], cur["tz"] - last["tz"]) < 0.005:
            return cur
        last = cur
    return last


def _free_pt(pg):
    """畫面上離所有角色最遠、又不在面板上的一點：拖曳要從空地開始，從角色身上開始會變成「拎起來」而不是轉鏡頭（有選取時角色常在畫面中央附近，固定座標會偶爾壓到）"""
    return pg.evaluate("""() => { const W = __world; let best = [700, 300], bd = -1; for (const x of [420, 520, 620, 720, 820, 920]) for (const y of [200, 280, 360, 440, 520, 600]) { let d = 1e9; for (const c of [...W.chars.values(), ...(W.pets || [])]) if (c._sx > -900) d = Math.min(d, Math.hypot(c._sx - x, c._sy + 20 - y)); if (d > bd) { bd = d; best = [x, y]; } } return best; }""")


def _mode(pg, m):
    """切換「拖曳：移動｜旋轉」（真的點畫面上的鈕）。新規則（擁有者 11-13）：左鍵拖曳預設是平移，切到旋轉才是旋轉"""
    pg.click(".cm-seg [data-c='%s']" % ("ro" if m == "rotate" else "mv"))


def _tween_done(pg, t=8000):
    return wait_until(pg, "() => !__world.view.tween", t)


def _rect(pg, sel):
    return pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e || e.hidden) return null; const r = e.getBoundingClientRect(); if (!r.width) return null;
      const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return null; return [r.left, r.top, r.right, r.bottom]; }""", sel)


def _overlap(a, b, pad=1):
    return a and b and not (a[2] <= b[0] + pad or b[2] <= a[0] + pad or a[3] <= b[1] + pad or b[3] <= a[1] + pad)


_BAR = ("#bar .ttl", "#viewSeg", "#areaBtn", "#demoBtn", "#speedSeg", "#editBtn")   # 工具列本身是整排寬的容器，要比的是裡面的按鈕


def _no_overlap(pg, sels):
    rs = [(s, _rect(pg, s)) for s in sels]
    bad = [(a[0], b[0]) for i, a in enumerate(rs) for b in rs[i + 1:] if _overlap(a[1], b[1])]
    return bad


def _hold(pg, key, ms):
    pg.keyboard.down(key)
    pg.wait_for_timeout(ms)
    pg.keyboard.up(key)


def _sim_speed(pg, cid, key, sim=1.2):
    """按住 key，穩定後量 sim 個模擬秒內的平均速度（公尺／模擬秒）與位移向量。播放速度暫時降到 3 倍，
    讓軟體繪圖下每幀的模擬量小一點（8 倍時每幀跑 0.8 秒，會一口氣衝過空地撞牆）。"""
    pg.evaluate("() => { __world.speed = 3; }")
    pg.keyboard.down(key)
    wait_until(pg, "() => __world.pilot.speedNow > 0.2", 15000)     # 等按鍵真的被這一幀處理到、角色起步
    p0 = _pos(pg, cid)
    wait_until(pg, f"() => __world.time - {p0[3]} >= {sim}", 30000)
    p1 = _pos(pg, cid)
    pg.keyboard.up(key)
    pg.evaluate("() => { __world.speed = 8; }")
    dt = max(1e-6, p1[3] - p0[3])
    return _m.hypot(p1[0] - p0[0], p1[1] - p0[1]) / dt, (p1[0] - p0[0], p1[1] - p0[1])


def _rec_start(pg, cid="ceo"):
    pg.evaluate("(id) => { window.__rec = []; window.__recOn = true; const f = () => { if (!window.__recOn) return; const c = __world.chars.get(id), p = c.object3D.position; __rec.push([__world.time, p.x, p.z, __world.pilot.run]); requestAnimationFrame(f); }; f(); }", cid)


def _rec_speeds(pg):
    """每一幀的實際速度（公尺／模擬秒）：用相鄰兩幀的位移與模擬時間差算，不受按鍵延遲與撞牆停下的影響"""
    r = pg.evaluate("() => { __recOn = false; return __rec; }")
    out = []
    for a, b2 in zip(r, r[1:]):
        dt = b2[0] - a[0]
        if dt > 1e-6:
            out.append((_m.hypot(b2[1] - a[1], b2[2] - a[2]) / dt, b2[3]))
    return out


def _near_spot(pg, oid):
    return pg.evaluate("""(id) => { const W = __world, o = W.chars.get(id), p = o.object3D.position;
      for (const [dx, dz] of [[0.9, 0.9], [-0.9, 0.9], [0.9, -0.9], [-0.9, -0.9], [1.2, 0], [0, 1.2], [-1.2, 0], [0, -1.2]]) { const q = W.nav.nearestFree(p.x + dx, p.z + dz, 6); if (q && Math.hypot(q.x - p.x, q.z - p.z) > 0.85 && Math.hypot(q.x - p.x, q.z - p.z) < 1.6) return [q.x, q.z]; }
      return null; }""", oid)


def _open_area(pg, kind="f", reach=3.6):
    """找一個起點，沿鏡頭的 f 前／b 後／r 右／l 左 方向有 reach 公尺的空地（走道寬 1 公尺，靠近辦公室中央優先）——量速度才不會撞到家具或牆"""
    return pg.evaluate("""([kind, reach]) => { const W = __world, c = W.camera, t = W.controls.target; let fx = t.x - c.position.x, fz = t.z - c.position.z; const l = Math.hypot(fx, fz); fx /= l; fz /= l; const rx = -fz, rz = fx;
      const [dx, dz] = { f: [fx, fz], b: [-fx, -fz], r: [rx, rz], l: [-rx, -rz] }[kind], px = -dz, pz = dx;
      const clear = (x, z, R) => { for (let s = 0; s <= R; s += 0.25) for (const o of [-0.5, 0, 0.5]) { if (!W.nav.isFree(x + dx * s + px * o, z + dz * s + pz * o)) return false; } return true; };
      for (const R of [reach, reach - 0.6, reach - 1.2]) { let best = null, bm = -1e9;
        for (let x = 2.5; x <= 37.5; x += 0.5) for (let z = 2.5; z <= 27.5; z += 0.5) { if (!clear(x, z, R)) continue; const m = -Math.hypot(x - 20, z - 15); if (m > bm) { bm = m; best = [x, z]; } }
        if (best) return best; }
      return null; }""", [kind, reach])


def _tap_twice(pg, code, gap):
    """連按同一個方向鍵兩次，第二次按下後維持按住。gap ≤ 300：在同一個 JS 工作裡連送 keydown→keyup→keydown（兩次相隔不到 1 毫秒；
    軟體繪圖很慢時，頁面計時器會被一幀拖到幾百毫秒，外部逐筆送鍵的間隔不可靠）。gap > 300：兩次分開送，中間真的等 gap 毫秒。"""
    ev = "(code) => { const k = (t) => window.dispatchEvent(new KeyboardEvent(t, { code, key: code, bubbles: true, cancelable: true }));"
    if gap <= 300:
        pg.evaluate(ev + " k('keydown'); k('keyup'); k('keydown'); }", code)
    else:
        pg.evaluate(ev + " k('keydown'); k('keyup'); }", code)
        pg.wait_for_timeout(gap)
        pg.evaluate(ev + " k('keydown'); }", code)


def _release(pg, code):
    pg.evaluate("(code) => window.dispatchEvent(new KeyboardEvent('keyup', { code, key: code, bubbles: true, cancelable: true }))", code)


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
        ov = _no_overlap(pg, ["#card", ".pt-tips", ".cm-hint", *_BAR, "#log"])
        ok("版面：資訊卡、提示卡、鏡頭小提示、工具列兩兩不重疊", not ov, ov)
        tag = pg.evaluate("() => { const e = document.querySelector('#labels .tag.sel'); const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }")
        ov2 = [s for s in ["#card", ".pt-tips", ".cm-hint", *_BAR] if _overlap(tag, _rect(pg, s))]
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
        oas = {k: _open_area(pg, k) for k in "fbrl"}
        ok("（前置）鏡頭前後左右四個方向都找得到可以走 3 公尺以上的空地", all(oas.values()), oas)

        def reset(kind="f"):
            a = _open_area(pg, kind) or oas[kind]       # 每次都依「現在的鏡頭」重找（鏡頭方位可能已經變了）
            pg.evaluate("(a) => { __world.chars.get('ceo').standAt(a[0], a[1], 0); }", a)
            pg.wait_for_timeout(700)
        reset("f")
        # 穩定量測：先站定，再量 ArrowUp
        _rec_start(pg)
        sp_walk, d = _sim_speed(pg, "ceo", "ArrowUp", 1.2)
        walk_frames = [v for v, _ in _rec_speeds(pg)]
        sp_walk_peak = max(walk_frames)
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
        reset("r")
        _, dd = _sim_speed(pg, "ceo", "KeyD", 1.0)
        rdir = (-fdir[1], fdir[0])
        md = _m.hypot(*dd)
        ok("WASD 也能移動：D 往鏡頭右方", md > 0.3 and (dd[0] * rdir[0] + dd[1] * rdir[1]) / md > 0.9, (dd, rdir))
        reset("f")
        _, dd = _sim_speed(pg, "ceo", "KeyW", 0.8)
        ok("WASD：W 往遠離鏡頭的方向", _m.hypot(*dd) > 0.2 and (dd[0] * fdir[0] + dd[1] * fdir[1]) / _m.hypot(*dd) > 0.9, dd)
        # 走路連拍（至少 6 格）
        reset("b")
        _frames(pg, "走路連拍.png", "ArrowDown", 6, 420)

        # ───────── 跑步：連按兩次 ─────────
        reset("r")
        pg.evaluate("() => { __world.speed = 3; }")
        _rec_start(pg)
        t_start = _pos(pg, "ceo")[3]
        _tap_twice(pg, "ArrowRight", 120)
        wait_until(pg, f"() => __world.time - {t_start} >= 1.0", 40000)
        run_now = pg.evaluate("() => __world.pilot.run")
        _release(pg, "ArrowRight")
        pg.evaluate("() => { __world.speed = 8; }")
        rec_dbg = pg.evaluate("""() => { const c = __world.chars.get('ceo'), P = __world.pilot; return { rec: __rec.slice(-3), speedNow: P.speedNow, run: P.run, state: c.state, drive: !!c._drive && [c._drive.vx, c._drive.vz], hop: !!c._hop, path: !!c._path, engaging: !!P.engaging, talking: P.talking, vel: c.inner.vel.length(), mode: c.inner.mode, held: c._held }; }""")
        run_frames = [v for v, r in _rec_speeds(pg) if r]
        sp_run = max(run_frames) if run_frames else 0
        ok("同一方向 300 毫秒內連按兩次：進入跑步（pilot.run）", run_now)
        ok("跑步速度明顯高於走路（逐幀最高速 ≥ 1.8 倍）", sp_run >= 1.8 * sp_walk_peak, (sp_run, sp_walk_peak, rec_dbg))
        pg.wait_for_timeout(250)
        ok("放開方向鍵後回到走路（run 解除）", not pg.evaluate("() => __world.pilot.run"))
        reset("l")
        sp2, _ = _sim_speed(pg, "ceo", "ArrowLeft", 1.2)
        ok("再單按一次是走路速度（不殘留跑步）", sp2 < 1.4 * sp_walk, (sp2, sp_walk))
        reset("r")
        _tap_twice(pg, "ArrowRight", 600)
        pg.wait_for_timeout(600)
        ok("兩次按下間隔 600 毫秒（超過 300）：不算連按，不跑步", not pg.evaluate("() => __world.pilot.run"))
        _release(pg, "ArrowRight")
        reset("f")
        reset("f")
        _frames(pg, "跑步連拍.png", "ArrowUp", 6, 330, run=True)

        # ───────── 站著不動很久（角色的待機行為會想坐下），之後仍要能操控 ─────────
        reset("f")
        t_idle = _pos(pg, "ceo")[3]
        wait_until(pg, f"() => __world.time - {t_idle} >= 30", 120000)
        ok("操控中站著不動 30 模擬秒：不會自己坐下發呆（仍是 normal 模式）", pg.evaluate("() => __world.chars.get('ceo').inner.mode") == "normal", pg.evaluate("() => __world.chars.get('ceo').inner.mode"))
        sp_after, d_after = _sim_speed(pg, "ceo", "ArrowUp", 0.6)
        ok("站很久之後按方向鍵仍會移動", _m.hypot(*d_after) > 0.5, d_after)

        # ───────── 跳躍 ─────────
        reset("f")
        pg.evaluate("() => { __world.speed = 1; }")      # 一次跳躍只有約 0.6 模擬秒，8 倍速時整段都落在同一幀裡，逐幀取樣看不到高度
        pg.evaluate("() => { const ch = __world.chars.get('ceo').inner, o = ch.onLand.bind(ch); window.__land = null; ch.onLand = (imp, sf) => { o(imp, sf); window.__land = { imp, sqV: ch.sqV }; }; }")
        pg.evaluate("() => { window.__ys = []; const f = () => { const c = __world.chars.get('ceo'); __ys.push([c.inner.pos.y, c.inner.sq, __world.time]); if (__ys.length < 600) requestAnimationFrame(f); }; f(); }")
        pg.keyboard.press("Space")
        pg.wait_for_timeout(300)
        wait_until(pg, "() => __land || __ys.length >= 599", 90000)
        pg.wait_for_timeout(1500)
        pg.evaluate("() => { __world.speed = 8; }")
        ys = pg.evaluate("() => __ys")
        ymax = max(v[0] for v in ys)
        ipeak = [v[0] for v in ys].index(ymax)
        ok("Space：高度先升（最高 ≥ 0.3 公尺）", ymax >= 0.3, ymax)
        ok("Space：之後回到地面（最後 ≈ 0）", ys[-1][0] < 0.02, ys[-1])
        ok("起跳前先上升、最高點之後下降（有重力）", ys[ipeak - 1][0] < ymax and ys[min(len(ys) - 1, ipeak + 3)][0] < ymax)
        land = pg.evaluate("() => __land")
        ok("落地有壓縮（落地衝擊 ≥ 3、壓縮初速 ≤ -2）並回彈到原樣（最後 squash ≈ 0）", bool(land) and land["imp"] >= 3 and land["sqV"] <= -2 and abs(ys[-1][1]) < 0.1, (land, ys[-1]))
        _jump_strip(pg)

        # ───────── 碰撞：不穿牆、不穿家具、不出辦公室 ─────────
        pg.evaluate("() => { __world.speed = 8; window.__hit = { solid: 0, out: 0, n: 0, minx: 99, minz: 99, maxx: -99, maxz: -99 }; const f = () => { const W = __world, c = W.chars.get('ceo'), p = c.object3D.position; const h = __hit; h.n++; if (W.nav.isSolid(p.x, p.z)) { h.solid++; h.at = h.at || [p.x, p.z, W.time]; } if (p.x < 0.3 || p.x > W.layout.size.w - 0.3 || p.z < 0.3 || p.z > W.layout.size.d - 0.3) h.out++; h.minx = Math.min(h.minx, p.x); h.minz = Math.min(h.minz, p.z); h.maxx = Math.max(h.maxx, p.x); h.maxz = Math.max(h.maxz, p.z); requestAnimationFrame(f); }; f(); }")
        for key, ms in (("ArrowUp", 5000), ("ArrowLeft", 5000), ("ArrowDown", 6000), ("ArrowRight", 6000), ("ArrowUp", 4000), ("ArrowLeft", 4000)):
            pg.keyboard.down(key); pg.wait_for_timeout(60); pg.keyboard.up(key); pg.wait_for_timeout(80)    # 連按兩次 → 跑著撞牆，最容易穿牆
            pg.keyboard.down(key); pg.wait_for_timeout(ms); pg.keyboard.up(key)
        h = pg.evaluate("() => __hit")
        ok("朝四面牆一直跑：全程沒有任何一格站進牆或家具本體", h["solid"] == 0, h)
        ok("朝四面牆一直跑：沒有走出辦公室範圍", h["out"] == 0 and h["minx"] > 0.3 and h["minz"] > 0.3 and h["maxx"] < 39.7 and h["maxz"] < 29.7, h)
        pg.evaluate("() => { __world.speed = 8; }")
        ok("全程跑過多個方向後角色仍在辦公室內且可操控", pg.evaluate("() => __world.pilot.engaged"))

        # ───────── 與旁邊的同事溝通 ─────────
        oid = "data-steward"
        spot = _near_spot(pg, oid)
        ok("找得到同事旁邊的空位（測試前置）", bool(spot))
        pg.evaluate("(a) => { const W = __world, c = W.chars.get('ceo'); c.standAt(a[0], a[1], 0); }", spot)
        pg.wait_for_timeout(700)
        ok("靠近同事：對方頭上出現「按 E 溝通」", wait_until(pg, "() => { const h = document.querySelector('.pt-hint'); return !h.hidden && h.textContent.includes('按 E 溝通'); }", 6000))
        _shot(pg, "靠近提示_按E溝通.png")
        ov = _no_overlap(pg, [".pt-hint", ".pt-tips", ".cm-hint", *_BAR, "#card"])
        ok("版面：「按 E 溝通」不與提示卡／工具列／資訊卡重疊", not ov, ov)
        pg.evaluate("() => { __world.speed = 1; }")     # 泡泡只有 2～3 模擬秒，放慢才抓得到畫面
        pg.keyboard.press("KeyE")
        ok("按 E：操控的角色說話（出現泡泡）", wait_until(pg, "() => __world.chars.get('ceo').speech && __world.chars.get('ceo').speech.text.length > 0", 5000))
        ok("按 E：兩人面對面（我朝向對方）", pg.evaluate("""(id) => { const W = __world, a = W.chars.get('ceo'), o = W.chars.get(id), pa = a.object3D.position, po = o.object3D.position;
          const want = Math.atan2(po.x - pa.x, po.z - pa.z); return Math.abs(((a.heading - want + Math.PI) % (2 * Math.PI)) - Math.PI) < 0.5; }""", oid))
        ok("按 E：對方的資訊卡打開（顯示對方名字）", pg.evaluate("(id) => { const W = __world, o = W.chars.get(id); return !document.getElementById('card').hidden && document.querySelector('#card .hd b').textContent.includes(o.spec.nick); }", oid))
        ok("按 E：對方停下原本動作並回話（對方也出現泡泡）", wait_until(pg, f"() => {{ const o = __world.chars.get('{oid}'); return o.speech && o.speech.text.length > 0; }}", 90000))
        bub = pg.evaluate("() => [...document.querySelectorAll('#labels .bub')].filter(b => b.getBoundingClientRect().left > -500).length")
        bubs = pg.evaluate("() => [...document.querySelectorAll('#labels .bub')].filter(b => b.getBoundingClientRect().left > -500).map(b => { const r = b.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })")
        ovb = _no_overlap(pg, ["#card", ".pt-tips", ".cm-hint", *_BAR])
        _shot(pg, "溝通對話.png")
        ok("對方回話的當下，兩個人的對話泡泡同時顯示在畫面上（= 2 個）", bub == 2, bub)
        ok("版面：資訊卡、提示卡、鏡頭提示、工具列不重疊（溝通中）", not ovb, ovb)
        okb = all(not _overlap(a, c2) for i, a in enumerate(bubs) for c2 in bubs[i + 1:])
        ok("兩個對話泡泡彼此不重疊", okb, bubs)
        pc = [_rect(pg, s) for s in (".pt-tips", "#card")]
        ok("對話泡泡不蓋到提示卡與資訊卡", all(not _overlap(bb, r) for bb in bubs for r in pc if r), (bubs, pc))
        pg.evaluate("() => { __world.speed = 8; }")
        ok("演出結束後對方回到原本行為（坐回座位工作、不忙）", wait_until(pg, "() => { const o = __world.chars.get('data-steward'); return !o.busy && o.state === 'sit' && o.atDesk; }", 20000))
        ok("演出結束後我可繼續操控（沒被鎖住）", pg.evaluate("() => !__world.pilot.talking && __world.pilot.engaged"))
        # F 揮手
        pg.evaluate("() => { __world.speed = 2; }")     # 揮手只有 1.4 模擬秒，放慢才抓得到
        pg.keyboard.press("KeyF")
        ok("按 F：我揮手（action = wave）", wait_until(pg, "() => __world.chars.get('ceo').action === 'wave'", 3000))
        ok("按 F：旁邊的同事也回揮", wait_until(pg, "() => __world.chars.get('data-steward').action === 'wave'", 12000))
        pg.evaluate("() => { __world.speed = 8; }")
        # 離開後提示消失
        pg.evaluate("() => { const W = __world; W.chars.get('ceo').standAt(20, 21.5, 0); }")
        ok("走遠後「按 E 溝通」消失", wait_until(pg, "() => document.querySelector('.pt-hint').hidden", 5000))
        pg.keyboard.press("KeyE")
        ok("沒人在旁邊按 E：提示「附近沒有可以溝通的同事」", wait_until(pg, "() => !document.getElementById('toast').hidden && document.getElementById('toast').textContent.includes('附近沒有')", 4000))

        # ───────── 面板開著時不移動（佈告欄） ─────────
        # 見下方佈告欄段落

        # ───────── Esc：解除選取，角色自己走回座位（不瞬移） ─────────
        pg.evaluate("() => { window.__jumps = 0; window.__last = null; window.__mx = 0; const f = () => { const p = __world.chars.get('ceo').object3D.position, t = __world.time; if (__last && t - __last[2] > 1e-6) { const d = Math.hypot(p.x - __last[0], p.z - __last[1]); __mx = Math.max(__mx, d / (t - __last[2])); } __last = [p.x, p.z, t]; requestAnimationFrame(f); }; f(); }")
        pg.keyboard.press("Escape")
        ok("Esc：選取解除（sel 為空）", pg.evaluate("() => __world.pilot.sel === null"))
        ok("Esc：光環、提示卡消失", pg.evaluate("() => !__world.pilot.halo.visible && document.querySelector('.pt-tips').hidden && !document.querySelector('#labels .tag.sel')"))
        ok("Esc：角色恢復自動行為（開始自己走回座位）", wait_until(pg, "() => __world.chars.get('ceo').state === 'walk' || (__world.chars.get('ceo').state === 'sit')", 8000))
        pg.evaluate("() => { __world.speed = 8; }")
        ok("Esc：走回座位並坐下、恢復工作", wait_until(pg, "() => { const c = __world.chars.get('ceo'); return c.state === 'sit' && c.atDesk && !c.busy; }", 60000))
        pg.evaluate("() => { __world.speed = 8; }")
        mx = pg.evaluate("() => __mx")
        ok("Esc 之後沒有瞬移（逐幀速度最高 < 5 公尺／秒；走路約 2.2、瞬移會是幾十以上）", mx < 5, mx)

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
        _tap_twice(pg, key, 120)
    else:
        pg.keyboard.down(key)
    ims = []
    for i in range(n):
        pg.wait_for_timeout(gap)
        x, y = _scr(pg, "ceo", 70)
        x = max(150, min(1130, x)); y = max(150, min(610, y))
        ims.append(Image.open(io.BytesIO(pg.screenshot(clip={"x": x - 150, "y": y - 150, "width": 300, "height": 300}))))
    if run:
        _release(pg, key)
    else:
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
    pg.evaluate("() => { __world.speed = 2; }")
    pg.keyboard.press("Space")
    ims = []
    for i in range(6):
        pg.wait_for_timeout(260)
        x, y = _scr(pg, "ceo", 70)
        x = max(150, min(1130, x)); y = max(150, min(610, y))
        ims.append(Image.open(io.BytesIO(pg.screenshot(clip={"x": x - 150, "y": y - 150, "width": 300, "height": 300}))))
    pg.evaluate("() => { __world.speed = 8; }")
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
        ov = _no_overlap(pg, ["#board", ".pt-tips", ".cm-hint", *_BAR, "#card"])
        ok("版面：佈告欄面板、提示卡、鏡頭提示、工具列兩兩不重疊", not ov, ov)
        oa_b = _open_area(pg, "b") or _open_area(pg, "f")
        pg.evaluate("(a) => { __world.chars.get('ceo').standAt(a[0], a[1], 0); }", oa_b)    # 站到空曠處，之後「能不能動」才不會被家具擋住而誤判
        pg.wait_for_timeout(700)
        p0 = _pos(pg, "ceo")
        pg.keyboard.down("ArrowUp"); pg.wait_for_timeout(900); pg.keyboard.up("ArrowUp")
        p1 = _pos(pg, "ceo")
        ok("面板開著時按方向鍵不移動角色", _m.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 0.05, (p0, p1))
        pg.keyboard.press("Escape")
        ok("Esc：關閉佈告欄面板", pg.evaluate("() => document.getElementById('board').hidden"))
        ok("Esc 只關面板，操控仍在（再按 Esc 才結束）", pg.evaluate("() => !!__world.pilot.sel"))
        pg.keyboard.down("ArrowDown")
        wait_until(pg, "() => __world.pilot.speedNow > 0.2", 15000)
        pg.wait_for_timeout(1500)
        p2 = _pos(pg, "ceo")
        pg.keyboard.up("ArrowDown")
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
        c1 = _settle(pg)
        ok("CEO 視角下左鍵拖曳（預設「移動」）：注視點改變、方位角不變", _m.hypot(c1["tx"] - c0["tx"], c1["tz"] - c0["tz"]) > 0.5 and abs(c1["az"] - c0["az"]) < 0.02, (c0, c1))
        pg.evaluate("() => { __world.view.detached = false; }")
        _mode(pg, "rotate")
        c0 = _cam(pg)
        pg.mouse.move(640, 380); pg.mouse.down()
        for i in range(1, 9):
            pg.mouse.move(640 + i * 45, 380)
            pg.wait_for_timeout(40)
        pg.mouse.up()
        c1 = _settle(pg)
        _mode(pg, "move")
        da = abs((c1["az"] - c0["az"] + _m.pi) % (2 * _m.pi) - _m.pi)
        ok("切到「旋轉」後左鍵拖曳：方位角真的改變（> 0.2 弧度）", da > 0.2, da)
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
        pg.mouse.move(640, 380); pg.mouse.down()
        for i in range(1, 9):
            pg.mouse.move(640 + i * 25, 380 + i * 12)
            pg.wait_for_timeout(40)
        pg.mouse.up()
        c5 = _settle(pg)
        ok("左鍵拖曳：注視點改變（平移 > 0.5 公尺）", _m.hypot(c5["tx"] - c4["tx"], c5["tz"] - c4["tz"]) > 0.5, (c4, c5))
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
            pg.mouse.move(900, 400); pg.mouse.down(); pg.mouse.move(100, 400, steps=6); pg.mouse.up()
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
        pg.mouse.move(640, 380); pg.mouse.down(); pg.mouse.move(900, 500, steps=6); pg.mouse.up()
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
        pg.mouse.move(640, 380); pg.mouse.down(); pg.mouse.move(800, 450, steps=6); pg.mouse.up()
        pg.wait_for_timeout(300)
        ok("操控中手動平移：暫停自動跟隨", pg.evaluate("() => __world.view.detached"))
        pg.keyboard.down("ArrowDown"); pg.wait_for_timeout(1500); pg.keyboard.up("ArrowDown")
        ok("角色再次移動：自動接回跟隨", wait_until(pg, "() => !__world.view.detached", 4000))
        az0 = _cam(pg)["az"]
        _mode(pg, "rotate")
        fx, fy = _free_pt(pg)
        pg.mouse.move(fx, fy); pg.mouse.down(); pg.mouse.move(fx + 160, fy, steps=8); pg.mouse.up()
        pg.wait_for_timeout(400)
        _mode(pg, "move")
        ok("操控中切到「旋轉」後左鍵拖曳仍可旋轉", abs((_cam(pg)["az"] - az0 + _m.pi) % (2 * _m.pi) - _m.pi) > 0.1)
        # 鏡頭小提示
        ok("鏡頭操作小提示：寫明「快速拖曳：移動場景・長按後拖曳：調整角度・滾輪：縮放・雙擊地面：前往」、不提右鍵，並有「移動｜旋轉」切換與 ↺ ↻ 鈕", pg.evaluate("() => { const t = document.querySelector('.cm-hint').textContent; return t.includes('快速拖曳：移動場景・長按後拖曳：調整角度・滾輪：縮放・雙擊地面：前往') && !t.includes('右鍵') && !!document.querySelector('.cm-seg [data-c=ro]') && !!document.querySelector('.cm-rot[data-c=rl]') && !!document.querySelector('.cm-rot[data-c=rr]'); }"))
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
        pg.mouse.move(640, 380); pg.mouse.down(); pg.mouse.move(520, 330, steps=6); pg.mouse.up()
        pg.mouse.wheel(0, 300)
        pg.wait_for_timeout(1200)
        _shot(pg, "CEO視角_滑鼠移動後.png")
        ov = _no_overlap(pg, [".cm-hint", *_BAR, "#card", ".pt-tips"])
        ok("版面：鏡頭小提示與工具列、面板不重疊", not ov, ov)
        ok("鏡頭段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_mobile(b, base):
    c, pg, got = _open(b, base, 390, 844, touch=True, qs="?ambient=0&view=ceo")
    try:
        ok("手機：頁面載入", got)
        if not got:
            return
        ok("手機：沒有選取時看不到虛擬搖桿", pg.evaluate("() => document.querySelector('.pt-pad').hidden"))
        x, y = _scr(pg, "ceo")
        pg.touchscreen.tap(x, y)
        ok("手機：點角色選取", wait_until(pg, "() => __world.pilot.sel", 6000))
        pg.wait_for_timeout(900)
        ok("手機：出現虛擬搖桿與跳／溝通／揮手／視角鈕", pg.evaluate("() => !document.querySelector('.pt-pad').hidden && !!document.querySelector('.pt-joy') && document.querySelectorAll('.pt-b').length === 4 && getComputedStyle(document.querySelector('.pt-joy')).display !== 'none'"))
        sizes = pg.evaluate("() => [...document.querySelectorAll('.pt-b, .pt-th button')].map(b => { const r = b.getBoundingClientRect(); return [b.textContent.trim(), Math.round(r.width), Math.round(r.height)]; })")
        ok("手機：所有按鈕至少 44px", all(w >= 44 and h >= 44 for _, w, h in sizes), sizes)
        ok("手機：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
        joy = _rect(pg, ".pt-joy")
        btns = _rect(pg, ".pt-btns")
        ok("手機：搖桿在左下、按鈕在右下（固定位置）", joy[0] < 60 and joy[3] > 600 and btns[2] > 330 and btns[3] > 600, (joy, btns))
        ov = _no_overlap(pg, [".pt-joy", ".pt-btns", ".pt-tips", "#card", *_BAR, ".cm-hint"])
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
        pg.evaluate("() => { window.__ym = 0; const P = __world.pilot, t0 = P.tick; P.tick = h => { t0(h); __ym = Math.max(__ym, __world.chars.get('ceo').inner.pos.y); }; }")   # 在每個模擬步裡取最高點（軟體繪圖幀很慢，一幀可能整段跳躍都跑完，用 rAF 取樣會漏掉）
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
        pt = pg.evaluate("""() => { const W = __world, T = W.THREE; const m = W.boardsMesh.find(m => m.userData.board === 'legal');
          const r = document.getElementById('cv').getBoundingClientRect(), rc = new T.Raycaster(), box = new T.Box3().setFromObject(m);
          // 佈告欄在手機上可能被上方工具列蓋住一部分：在它投影出來的範圍裡找一個「真的點得到它、沒被別的元素蓋住」的位置
          const cs = [[box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z], [box.min.x, box.max.y, box.min.z], [box.max.x, box.min.y, box.max.z]].map(a => new T.Vector3(...a).project(W.camera));
          const x0 = Math.min(...cs.map(v => v.x)), x1 = Math.max(...cs.map(v => v.x)), y0 = Math.min(...cs.map(v => v.y)), y1 = Math.max(...cs.map(v => v.y));
          for (let i = 0; i <= 12; i++) for (let k = 0; k <= 12; k++) {
            const nx = x0 + (x1 - x0) * i / 12, ny = y0 + (y1 - y0) * k / 12, x = r.left + (nx + 1) / 2 * r.width, y = r.top + (1 - ny) / 2 * r.height;
            if (x < 2 || y < 2 || x > innerWidth - 2 || y > innerHeight - 2) continue; if ([[0, 0], [16, 0], [-16, 0], [0, 16], [0, -16]].some(d => { const e = document.elementFromPoint(x + d[0], y + d[1]); return !e || e.id !== 'cv'; })) continue;   // 四周 16px 內都沒有別的元素（手機瀏覽器會把觸控吸附到附近的按鈕）
            rc.setFromCamera(new T.Vector2(nx, ny), W.camera); const h = rc.intersectObjects(W.boardsMesh, false)[0]; if (h && h.object === m) return [x, y];
          } return null; }""")
        ok("手機：佈告欄在畫面上有一塊沒被工具列或面板蓋住、可以點到", pt is not None, pt)
        pg.touchscreen.tap(pt[0], pt[1])
        ok("手機：點佈告欄開面板", wait_until(pg, "() => !document.getElementById('board').hidden", 5000))
        ok("手機：佈告欄面板不超出螢幕", pg.evaluate("() => { const r = document.getElementById('board').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight + 1; }"))
        ok("手機：佈告欄面板有關閉鈕且可關", (pg.click("#board .x") or True) and pg.evaluate("() => document.getElementById('board').hidden"))
        ok("手機段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_daytime(b, base):
    """天色依台北時間連續變化：四個時段、夜晚室內可見度、跟隨現在時間、選單與記憶"""
    import datetime as _dt
    import io
    from zoneinfo import ZoneInfo
    from PIL import Image
    # 故意把瀏覽器時區設成洛杉磯：顯示的必須是台北時間，不是瀏覽器所在時區
    c = b.new_context(viewport={"width": 1280, "height": 760}, timezone_id="America/Los_Angeles")
    pg = c.new_page()
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    try:
        pg.goto(_root(base) + "/office/world.html?ambient=0&q=low&view=ceo", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
        ok("天色：頁面載入", got)
        if not got:
            return
        pg.evaluate("() => { __world.speed = 8; }")
        pg.wait_for_timeout(800)
        tp = _dt.datetime.now(ZoneInfo("Asia/Taipei"))
        txt = pg.evaluate("() => document.querySelector('.dt-chip').textContent")
        ok("預設跟隨現在時間：左上小字顯示時段與台北時間（與台北時間誤差 ≤ 1 分鐘，即使瀏覽器時區是洛杉磯）",
           "台北" in txt and abs((int(txt.split("台北 ")[1][:2]) * 60 + int(txt.split("台北 ")[1][3:5])) - (tp.hour * 60 + tp.minute)) <= 1 and "預覽" not in txt, (txt, tp.strftime("%H:%M")))
        ok("預設模式是跟隨現在時間（auto）", pg.evaluate("() => __world.daytime.mode") == "auto")
        pg.click(".dt-b")
        ok("點小字：展開「時間」選單（跟隨現在時間／早晨／白天／黃昏／夜晚）", pg.evaluate("() => { const p = document.querySelector('.dt-pop'); return !p.hidden && ['跟隨現在時間', '早晨', '白天', '黃昏', '夜晚'].every(k => p.textContent.includes(k)); }"))
        ov = _no_overlap(pg, [".dt-chip", ".dt-pop", ".cm-hint", *_BAR])
        ok("版面：時間小字／選單與鏡頭提示、工具列不重疊", not ov, ov)
        pg.click(".dt-b")
        shots = {}
        info = {}
        for key, nm in (("morning", "早晨"), ("day", "白天"), ("dusk", "黃昏"), ("night", "夜晚")):
            pg.click(".dt-b")
            pg.click(f".dt-pop [data-m='{key}']")
            pg.wait_for_timeout(1300)
            info[key] = pg.evaluate("""() => { const W = __world, cv = W.skyTex.image, d = cv.getContext('2d').getImageData(0, 140, 1, 1).data, sc = W.sun.color, hc = W.hemi.color;
              return { sky: [d[0] / 255, d[1] / 255, d[2] / 255], sun: [sc.r, sc.g, sc.b], int: W.sun.intensity, hemi: W.hemi.intensity, hc: [hc.r, hc.g, hc.b], stars: __world.daytime.stars.material.opacity,
                       sunVis: __world.daytime.sunS.visible, moonVis: __world.daytime.moonS.visible, dir: __world.daytime.dir ? __world.daytime.dir.toArray() : null, chip: document.querySelector('.dt-chip').textContent, glow: document.querySelector('.dt-chip') && 0 }; }""")
            im = Image.open(io.BytesIO(pg.screenshot()))
            shots[key] = im
            # 臉部區域（CEO 嘴巴附近 36×36 像素）平均亮度
            pt = pg.evaluate("""() => { const W = __world, c = W.chars.get('ceo'), T = W.THREE, i = c.inner, s = c.scale || 1, p = c.object3D.position;
              const v = new T.Vector3(p.x, i.cfg.mouth[1] * s + 0.02, p.z).project(W.camera), r = document.getElementById('cv').getBoundingClientRect(); return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height]; }""")
            face = Image.open(io.BytesIO(pg.screenshot(clip={"x": pt[0] - 18, "y": pt[1] - 22, "width": 36, "height": 36}))).convert("RGB")
            px = list(face.getdata())
            info[key]["face"] = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in px) / len(px) / 255
        ok("強制四個時段：小字顯示「預覽・時段」", all(("預覽" in info[k]["chip"]) and nm in info[k]["chip"] for k, nm in (("morning", "清晨"), ("day", "白天"), ("dusk", "黃昏"), ("night", "夜晚"))), {k: v["chip"] for k, v in info.items()})

        def dist(a, b2):
            return _m.sqrt(sum((x - y) ** 2 for x, y in zip(a, b2)))
        ks = list(info)
        pairs = [(a, b2) for i, a in enumerate(ks) for b2 in ks[i + 1:]]
        sky_d = {f"{a}-{b2}": round(dist(info[a]["sky"], info[b2]["sky"]), 3) for a, b2 in pairs}
        sun_d = {f"{a}-{b2}": round(dist(info[a]["sun"], info[b2]["sun"]), 3) for a, b2 in pairs}
        ok("四個時段的天空顏色兩兩明顯不同（RGB 距離 ≥ 0.10）", min(sky_d.values()) >= 0.10, sky_d)
        ok("四個時段的方向光顏色兩兩明顯不同（RGB 距離 ≥ 0.10）", min(sun_d.values()) >= 0.10, sun_d)
        ok("方向光角度隨時段改變（陰影方向跟著太陽走：早晨與黃昏的光向量不同）", dist(info["morning"]["dir"], info["dusk"]["dir"]) > 0.4, (info["morning"]["dir"], info["dusk"]["dir"]))
        ok("夜晚有星星、有月亮；白天沒有星星、有太陽", info["night"]["stars"] > 0.9 and info["night"]["moonVis"] and info["day"]["stars"] < 0.05 and info["day"]["sunVis"] and not info["day"]["moonVis"], {k: (v["stars"], v["sunVis"], v["moonVis"]) for k, v in info.items()})
        FACE_MIN = 0.30      # 臉部區域平均亮度（0～1）門檻：任何時段都不得低於它（實測夜晚約 0.39）
        ok(f"任何時段角色臉部區域平均亮度 ≥ {FACE_MIN}（夜晚也看得清楚）", all(v["face"] >= FACE_MIN for v in info.values()), {k: round(v["face"], 3) for k, v in info.items()})
        print("  量測：臉部亮度", {k: round(v["face"], 3) for k, v in info.items()}, "天空距離", sky_d, "方向光顏色距離", sun_d, flush=True)
        ok("夜晚室內有暖光：窗戶透出暖光（窗色偏黃）", pg.evaluate("() => { const c = __world.glassMat.color; return c.r > c.b + 0.15 && __world.glassMat.opacity > 0.6; }"))
        ok("夜晚的畫面確實比白天暗（但不過暗）", sum(shots["night"].convert("L").getdata()) < sum(shots["day"].convert("L").getdata()))
        # 並排截圖
        d = _os.environ.get("PILOT_SHOTS")
        if d:
            W2 = Image.new("RGB", (1280, 760), "white")
            for i, k in enumerate(("morning", "day", "dusk", "night")):
                W2.paste(shots[k].convert("RGB").resize((640, 380)), ((i % 2) * 640, (i // 2) * 380))
            _os.makedirs(d, exist_ok=True)
            W2.save(_os.path.join(d, "四個時段並排.png"))
        # 記住選擇
        ok("選擇記進 localStorage", pg.evaluate("() => localStorage.getItem('aiOffice.daytime')") == "night")
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => window.__world && window.__world.ready", 90000)
        pg.wait_for_timeout(800)
        ok("重新整理後仍是上次選的「夜晚」", "夜晚" in pg.evaluate("() => document.querySelector('.dt-chip').textContent") and "預覽" in pg.evaluate("() => document.querySelector('.dt-chip').textContent"))
        pg.click(".dt-b")
        pg.click(".dt-pop [data-m='auto']")
        pg.wait_for_timeout(800)
        tp = _dt.datetime.now(ZoneInfo("Asia/Taipei"))
        txt = pg.evaluate("() => document.querySelector('.dt-chip').textContent")
        ok("切回「跟隨現在時間」：顯示的時間與台北時間一致（±1 分鐘）、不再標「預覽」", "預覽" not in txt and abs((int(txt.split("台北 ")[1][:2]) * 60 + int(txt.split("台北 ")[1][3:5])) - (tp.hour * 60 + tp.minute)) <= 1, (txt, tp.strftime("%H:%M")))
        ok("跟隨現在時間的時段與台北時間相符", pg.evaluate("() => __world.daytime.phaseOf(__world.daytime.now().t)") in txt)
        ok("天色：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_view(b, base):
    """預設視角是俯視；選了角色之後在背景拖曳仍可移動鏡頭（拖曳與點一下要分清）"""
    # 不帶任何 view 參數 ＝ 使用者直接打開辦公室頁
    c, pg, got = _open(b, base, qs="?ambient=0&q=low")
    try:
        ok("預設視角：頁面載入", got)
        if not got:
            return
        wait_until(pg, "() => !__world.view.tween", 15000)
        pg.wait_for_timeout(600)
        v = pg.evaluate("""() => { const W = __world, c = W.camera, t = W.controls.target, d = c.position.distanceTo(t), T = W.THREE, r = document.getElementById('cv').getBoundingClientRect();
          const polar = Math.acos((c.position.y - t.y) / d);
          const corners = [[0, 0], [40, 0], [40, 30], [0, 30]].map(q => { const p = new T.Vector3(q[0], 0, q[1]).project(c); return [(p.x + 1) / 2 * r.width, (1 - p.y) / 2 * r.height]; });
          return { mode: W.view.mode, y: c.position.y, polar, d, corners, on: document.querySelector('#viewSeg .on').dataset.v, w: r.width, h: r.height }; }""")
        print("  量測：預設視角", {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items() if k in ("mode", "y", "polar", "d")}, flush=True)
        ok("預設是俯視模式（view.mode = god、「俯瞰」鈕亮著）", v["mode"] == "god" and v["on"] == "god", v)
        ok("俯視判定：鏡頭高度 ≥ 25 公尺、與垂直的夾角（polar）≤ 0.8 弧度（約 46 度）", v["y"] >= 25 and v["polar"] <= 0.8, (round(v["y"], 1), round(v["polar"], 3)))
        ok("整間辦公室（四個角）都在畫面內", all(-5 <= x <= v["w"] + 5 and -5 <= y <= v["h"] + 5 for x, y in v["corners"]), v["corners"])
        _shot(pg, "預設俯視.png")
        ok("「回 CEO 視角」鈕保留且可用", pg.evaluate("() => !!document.querySelector('#viewSeg [data-v=\"ceo\"]')"))
        pg.click("#viewSeg [data-v='ceo']")
        ok("按「CEO 視角」仍會運鏡到 CEO", wait_until(pg, "() => __world.view.mode === 'ceo' && !__world.view.tween", 15000))
        ok("預設視角：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()
    # ── 選了角色之後，在背景拖曳 ──
    c, pg, got = _open(b, base)
    try:
        x, y = _scr(pg, "ceo")
        pg.mouse.click(x, y)
        wait_until(pg, "() => __world.pilot.sel", 6000)
        _tween_done(pg, 12000)
        _settle(pg)
        ok("（前置）選了角色、資訊卡開著", pg.evaluate("() => !document.getElementById('card').hidden && __world.pilot.sel.spec.id === 'ceo'"))
        hit = pg.evaluate("""() => { const rs = ['card', 'board', 'log'].map(i => document.getElementById(i)).concat([document.querySelector('.pt-tips')]).filter(e => e && !e.hidden).map(e => e.getBoundingClientRect());
          const inR = (x, y) => rs.some(r => x >= r.left - 4 && x <= r.right + 4 && y >= r.top - 4 && y <= r.bottom + 4);
          const pts = [[900, 250], [1100, 300], [700, 120], [1000, 600], [640, 700], [300, 400], [500, 650]].filter(p => !inR(p[0], p[1]));
          return { n: pts.length, hit: pts.map(p => { const e = document.elementFromPoint(p[0], p[1]); return e ? (e.id || e.className || e.tagName) : null; }), rects: rs.map(r => [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]) }; }""")
        ok("資訊卡與面板只擋自己的範圍：面板範圍以外的位置，滑鼠事件都打在畫布上", hit["n"] >= 4 and all(h == "cv" for h in hit["hit"]), hit)
        c0 = _cam(pg)
        pg.mouse.move(900, 250); pg.mouse.down()
        for i in range(1, 9):
            pg.mouse.move(900 + i * 30, 250)
            pg.wait_for_timeout(40)
        pg.mouse.up()
        c1 = _settle(pg)
        ok("選了角色後在背景按住拖曳（預設「移動」）：鏡頭平移、方位不變", _m.hypot(c1["tx"] - c0["tx"], c1["tz"] - c0["tz"]) > 0.3 and abs(c1["az"] - c0["az"]) < 0.02, (c0, c1))
        _mode(pg, "rotate"); c0 = _cam(pg)
        pg.mouse.move(900, 250); pg.mouse.down()
        for i in range(1, 9):
            pg.mouse.move(900 + i * 30, 250)
            pg.wait_for_timeout(40)
        pg.mouse.up()
        c1 = _settle(pg); _mode(pg, "move")
        da = abs((c1["az"] - c0["az"] + _m.pi) % (2 * _m.pi) - _m.pi)
        ok("選了角色後切到「旋轉」再拖曳：鏡頭方位真的改變（> 0.2 弧度）", da > 0.2, da)
        ok("拖曳後選取仍在、資訊卡仍開著、提示卡仍在", pg.evaluate("() => !!__world.pilot.sel && !document.getElementById('card').hidden && !document.querySelector('.pt-tips').hidden"))
        _shot(pg, "選角後拖曳背景.png")
        pg.mouse.move(900, 250); pg.mouse.wheel(0, 500)
        pg.wait_for_timeout(600)
        c2 = _settle(pg)
        ok("選了角色後滾輪仍能縮放", abs(c2["dist"] - c1["dist"]) > 0.3, (c1["dist"], c2["dist"]))
        pg.mouse.move(900, 250); pg.mouse.down(); pg.mouse.move(800, 300, steps=6); pg.mouse.up()
        c3 = _settle(pg)
        ok("選了角色後左鍵拖曳仍能平移（注視點改變）", _m.hypot(c3["tx"] - c2["tx"], c3["tz"] - c2["tz"]) > 0.3, (c2, c3))
        ok("拖曳平移後仍保持選取", pg.evaluate("() => !!__world.pilot.sel && !document.getElementById('card').hidden"))
        # 按住不動超過 250 毫秒再放開 ＝ 不是點一下 → 不取消選取
        pg.mouse.move(900, 250); pg.mouse.down(); pg.wait_for_timeout(450); pg.mouse.up()
        pg.wait_for_timeout(600)
        ok("在背景按住超過 250 毫秒再放開：不算「點一下」，不取消選取", pg.evaluate("() => !!__world.pilot.sel"))
        # 位移超過 5 像素的小拖曳也不算點
        pg.mouse.move(900, 250); pg.mouse.down(); pg.mouse.move(912, 252, steps=3); pg.mouse.up()
        pg.wait_for_timeout(600)
        ok("位移超過 5 像素的小拖曳：不取消選取", pg.evaluate("() => !!__world.pilot.sel"))
        # 真正的點一下空白 ＝ 取消選取
        pg.mouse.click(900, 250)
        ok("快速點一下空白處：取消選取", wait_until(pg, "() => __world.pilot.sel === null", 3000))
        ok("選角拖曳段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_views(b, base):
    """其他視角也能用滑鼠：俯瞰、區域跳轉後、會議演出後；運鏡中使用者一動就中止"""
    c, pg, got = _open(b, base, qs="?ambient=0&q=low")
    try:
        ok("多視角：頁面載入", got)
        if not got:
            return
        wait_until(pg, "() => !__world.view.tween", 15000)

        def spot():
            """找一個畫面上沒有角色、沒有面板的空地當拖曳起點（按在角色上會變成「拎起來」，不是轉鏡頭）"""
            return pg.evaluate("""() => { const W = __world; let best = null, bd = -1;
              for (let x = 120; x < innerWidth - 120; x += 40) for (let y = 120; y < innerHeight - 60; y += 40) {
                const e = document.elementFromPoint(x, y); if (!e || e.id !== 'cv') continue;
                let d = 1e9; for (const c of W.chars.values()) if (c._sx > -900) d = Math.min(d, Math.hypot(c._sx - x, c._sy - y));
                if (d > bd) { bd = d; best = [x, y]; } }
              return best; }""")

        def drag(dx, dy=0, btn="left", at=None):
            at = at or spot()
            pg.mouse.move(*at); pg.mouse.down(button=btn)
            for i in range(1, 9):
                pg.mouse.move(at[0] + dx * i / 8, at[1] + dy * i / 8)
                pg.wait_for_timeout(40)
            pg.mouse.up(button=btn)

        def three(tag):
            a0 = _cam(pg)
            _mode(pg, "rotate"); drag(300)
            a1 = _settle(pg); _mode(pg, "move")
            da = abs((a1["az"] - a0["az"] + _m.pi) % (2 * _m.pi) - _m.pi)
            ok(tag + "：切到旋轉後左鍵拖曳（方位角改變 > 0.2）", da > 0.2, da)
            pg.mouse.move(*spot()); pg.mouse.wheel(0, 500); pg.wait_for_timeout(600)
            a2 = _settle(pg)
            ok(tag + "：滾輪縮放（距離改變 > 0.3）", abs(a2["dist"] - a1["dist"]) > 0.3, (a1["dist"], a2["dist"]))
            drag(-120, 60)
            a3 = _settle(pg)
            ok(tag + "：左鍵拖曳平移（注視點改變 > 0.3 公尺）", _m.hypot(a3["tx"] - a2["tx"], a3["tz"] - a2["tz"]) > 0.3, (a2, a3))
            pg.wait_for_timeout(2200)
            a4 = _cam(pg)
            ok(tag + "：兩秒後鏡頭沒有被拉回", abs(a4["tx"] - a3["tx"]) < 0.05 and abs(a4["tz"] - a3["tz"]) < 0.05 and abs(a4["dist"] - a3["dist"]) < 0.05, (a3, a4))

        three("預設俯視")
        # 區域跳轉（運鏡到某個部門）之後
        pg.evaluate("() => __world.jumpTo('legal')")
        ok("區域跳轉：運鏡結束", _tween_done(pg, 15000))
        three("區域跳轉後")
        # 運鏡中使用者一動就中止：運鏡開始後立刻按下滑鼠
        pg.evaluate("() => __world.setView('ceo')")
        ok("（前置）運鏡進行中", pg.evaluate("() => !!__world.view.tween"))
        sp = spot(); pg.mouse.move(*sp); pg.mouse.down(); pg.mouse.move(sp[0] + 60, sp[1], steps=3)
        ok("運鏡中使用者一按住拖曳：運鏡立刻中止", pg.evaluate("() => !__world.view.tween"))
        pg.mouse.up(); _settle(pg)
        # 會議演出播完之後
        pg.evaluate("() => { __world.speed = 8; }")
        pg.click("#demoBtn"); pg.click("#demoPop [data-demo='meeting']")
        ok("會議示範開始（導演進入會議）", wait_until(pg, "() => { const d = __world.director; return !!d && (d.running || !!d.meeting); }", 20000))
        wait_until(pg, "() => { const d = __world.director; return d && !d.running && !d.meeting; }", 300000, 1000)
        ok("會議示範結束", pg.evaluate("() => { const d = __world.director; return !!d && !d.running && !d.meeting; }"))
        pg.wait_for_timeout(500)
        three("會議演出後")
        ok("多視角段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_all(b, base):
    t_desktop(b, base)
    t_board(b, base)
    t_camera(b, base)
    t_view(b, base)
    t_views(b, base)
    t_daytime(b, base)
    t_mobile(b, base)


register("辦公室操控", lambda pg, b, base, code: t_all(b, base))
