# 驗收段落「辦公室視角與面向」：AI Office 3D 辦公室（site/office/world.html）的
#   ① 角色視角（擁有者 11-13：「需要再新增該角色視角」）：入口（資訊卡鈕、視角切換列多一格「角色視角」、鍵盤 V、手機操控列鈕）、
#      鏡頭在眼睛附近且朝角色面向、自己的身體／名牌／光環看不到、左鍵拖曳環顧（角色不動）、操控中前進＝角色前方且鏡頭跟著走、
#      轉身與跳躍時視角跟著、E／F 互動照常（提示、泡泡、資訊卡不重疊）、不穿進別人身體、Esc／再按 V／取消選取退出並回到先前視角附近、
#      高矮兩種體型眼睛高度不同、手機單指拖曳環顧
#   ② 點選角色時面向我（擁有者 11-13：「我點擊該角色，他會面向我」）：站著的人轉過來面向鏡頭（夾角 < 20 度）、坐著的人不離座只轉椅子、
#      走路中的人停下轉身且取消後繼續走、睡覺中不叫醒、取消選取後回原朝向、操控後朝向跟著移動方向
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用；全部是真的操作（滑鼠、鍵盤、觸控事件），並驗「畫面／狀態真的改變」。
# 環境變數 STATE_SHOTS 指到資料夾時，順便把驗收畫面存成截圖（交件用）。
# flake8: noqa

import math as _m
import os as _os
import re as _re

_PV_FORBID = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")


def _pv_open(b, base, w=1280, h=800, touch=False, qs="?ambient=0&q=low&pr=0.6", speed=8):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    pg = c.new_page(); pg.set_default_timeout(120000); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(base.split("/index.html")[0].rstrip("/") + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    if got:
        pg.evaluate("(s) => { __world.speed = s; }", speed)
    pg.wait_for_timeout(600)
    return c, pg, got


def _pv_shot(pg, name):
    d = _os.environ.get("STATE_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _pv_deg(a, b):
    """兩個角度（弧度）的最小夾角，單位度"""
    return abs(_m.degrees((a - b + _m.pi) % (2 * _m.pi) - _m.pi))


def _pv_sel(pg, cid, view=True):
    pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id); W.setView('char', c, true); W.ui.showCard(c); W.pilot.select(c); }""", cid)
    pg.wait_for_timeout(300)


def _pv_cam(pg):
    return pg.evaluate("""() => { const W = __world, d = new W.THREE.Vector3(); W.camera.getWorldDirection(d); const p = W.camera.position;
      return { x: p.x, y: p.y, z: p.z, yaw: Math.atan2(d.x, d.z), pitch: Math.asin(d.y), st: W.pov.st }; }""")


def _pv_ch(pg, cid):
    return pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id), p = c.object3D.position, e = new W.THREE.Vector3(); c.eye(e);
      return { x: p.x, z: p.z, y: p.y, yaw: c.inner.yaw, ex: e.x, ey: e.y, ez: e.z, h: c.height + (c.lift || 0), state: c.state, r: c.radius, face: c._seat ? c._seat.face : null }; }""", cid)


def _pv_toward(pg, cid):
    """角色 → 鏡頭 的水平方向（與角色朝向同一套角度）"""
    return pg.evaluate("(id) => { const W = __world, c = W.chars.get(id), p = c.object3D.position, q = W.camera.position; return Math.atan2(q.x - p.x, q.z - p.z); }", cid)


def _pv_vis(pg, cid):
    """這個角色身上還有幾個東西會被主鏡頭畫出來（角色視角開著時要是 0）"""
    return pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id); let n = 0; c.object3D.traverse(o => { if ((o.isMesh || o.isSprite) && o.visible && o.layers.test(W.camera.layers)) n++; }); return n; }""", cid)


def _pv_rect(pg, sel):
    return pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e || e.hidden) return null; const r = e.getBoundingClientRect(); if (!r.width) return null;
      const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return null; return [r.left, r.top, r.right, r.bottom]; }""", sel)


def _pv_hit(a, b, pad=1):
    return a and b and not (a[2] <= b[0] + pad or b[2] <= a[0] + pad or a[3] <= b[1] + pad or b[3] <= a[1] + pad)


def _pv_no_overlap(pg, sels):
    rs = [(s, _pv_rect(pg, s)) for s in sels]
    rs = [x for x in rs if x[1]]
    return [(a[0], b[0]) for i, a in enumerate(rs) for b in rs[i + 1:] if _pv_hit(a[1], b[1])], len(rs)


def _pv_bubbles(pg):
    """畫面上看得到的泡泡（不在 -999 螢幕外的）"""
    return pg.evaluate("""() => [...document.querySelectorAll('.bub')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > 0 && r.left < innerWidth && r.bottom > 0 && r.top < innerHeight; }).map(e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })""")


def _pv_free(pg, w=1280, h=800):
    """畫面上離所有角色最遠、又不在面板上的一點（拖曳要從空地開始，從角色身上開始會變成「拎起來」）"""
    return pg.evaluate("""([w, h]) => { const W = __world; let best = null, bd = -1; const xs = innerWidth > 700 ? [420, 520, 620, 720, 820, 920] : [80, 140, 200, 260], ys = innerWidth > 700 ? [200, 280, 360, 440, 520, 600] : [300, 360, 420, 480];
      for (const x of xs) for (const y of ys) { let d = 1e9; for (const c of [...W.chars.values(), ...(W.pets || [])]) if (c._sx > -900) d = Math.min(d, Math.hypot(c._sx - x, c._sy + 20 - y)); if (d > bd) { bd = d; best = [x, y]; } } return best; }""", [w, h])


def _pv_snap(pg, cid):
    """角色與鏡頭在「同一個瞬間」的樣子（播放速度快時，分兩次取值會差很遠）"""
    return pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id), p = c.object3D.position, d = new W.THREE.Vector3(), cp = W.camera.position; W.camera.getWorldDirection(d);
      return { cx: p.x, cz: p.z, cyaw: c.inner.yaw, cam: [cp.x, cp.y, cp.z], camyaw: Math.atan2(d.x, d.z) }; }""", cid)


def _pv_drag(pg, x0, y0, dx, dy, steps=8):
    pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move(x0 + dx, y0 + dy, steps=steps); pg.wait_for_timeout(80); pg.mouse.up(); pg.wait_for_timeout(500)


def _pv_engaged(pg):
    return wait_until(pg, "() => __world.pilot.engaged && !__world.pilot.engaging", 40000, 200)


def _pv_pick_extremes(pg):
    return pg.evaluate("""() => { const W = __world; const a = [...W.chars.values()].filter(c => !c.away && !c.jobless && !c.spec.isCeo);
      a.sort((p, q) => p.height - q.height); const f = a.find(c => c.inner.cfg.floatH) || null;
      return { small: a[0].spec.id, smallH: a[0].height, big: a[a.length - 1].spec.id, bigH: a[a.length - 1].height, floaty: f && f.spec.id, ceoH: W.chars.get('ceo').height }; }""")


def t_pov_desktop(b, base):
    c, pg, got = _pv_open(b, base)
    try:
        ok("角色視角：辦公室頁載入完成", got)
        if not got:
            return
        pg.click("#helpBtn"); pg.wait_for_timeout(300)
        ok("角色視角：說明收在「?」裡（寫了「角色視角」「面向你」「更多」）", pg.evaluate("() => { const t = document.getElementById('helpPop').textContent; return !document.getElementById('helpPop').hidden && /角色視角/.test(t) && /面向你/.test(t) && /更多/.test(t); }"))
        pg.click("#helpBtn")
        # ── 入口 ──
        ok("角色視角：沒選任何角色時，視角切換列沒有「角色視角」格", pg.evaluate("() => document.getElementById('viewPov').hidden"))
        pg.evaluate("() => __world.setView('god', null, true)"); pg.wait_for_timeout(500)
        pg.keyboard.press("v"); pg.wait_for_timeout(400)
        ok("角色視角：沒選角色時按 V 沒反應", pg.evaluate("() => __world.pov.st") == "off")
        # 真的點角色（CEO 視角下他在畫面上），再看入口
        pg.evaluate("() => { const W = __world; W.setView('ceo', null, true); }"); pg.wait_for_timeout(900)
        pt = pg.evaluate("() => { const c = __world.chars.get('ceo'); const k = c.scale || 1, px = __world.renderer.domElement.clientHeight / (2 * Math.tan(__world.camera.fov * Math.PI / 360) * c._sd); return [c._sx, c._sy + px * 0.45 * k]; }")
        pg.mouse.click(pt[0], pt[1]); pg.wait_for_timeout(1500)
        ok("角色視角：點 CEO 後選取（pilot.sel）", pg.evaluate("() => !!__world.pilot.sel && __world.pilot.sel.spec.id === 'ceo'"))
        segs = pg.evaluate("() => [...document.querySelectorAll('#viewSeg button')].filter(b => !b.hidden).map(b => b.textContent)")
        ok("角色視角：視角切換列有選取時多一格「角色視角」，四格字面互不重複（%s）" % segs, segs == ["CEO 視角", "俯瞰", "跟隨", "角色視角"] and len(set(segs)) == 4, segs)
        ok("角色視角：資訊卡有「角色視角」鈕", pg.evaluate("() => !!document.querySelector('#card [data-i=pov]') && document.querySelector('#card [data-i=pov]').textContent.trim() === '角色視角'"))
        ok("角色視角：操作提示卡寫了「V」與用途", pg.evaluate("() => [...document.querySelectorAll('.pt-tips kbd')].some(k => k.textContent === 'V') && /角色視角/.test(document.querySelector('.pt-tips').textContent)"))
        cam0 = _pv_cam(pg)
        ok("角色視角：進入前不在角色視角、自己的身體看得到（%d 件）" % _pv_vis(pg, "ceo"), pg.evaluate("() => __world.pov.st") == "off" and _pv_vis(pg, "ceo") > 5)
        # ── 進入（資訊卡的鈕）──
        pg.click("#card [data-i=pov]")
        mid = wait_until(pg, "() => __world.pov.st === 'in'", 3000, 30)
        ok("角色視角：按鈕後有約 0.5 秒的切入過渡（先進入「in」再到「on」）", mid or pg.evaluate("() => __world.pov.st") == "on")
        ok("角色視角：切入完成（on）", wait_until(pg, "() => __world.pov.st === 'on'", 6000, 100))
        pg.wait_for_timeout(500)
        ch = _pv_ch(pg, "ceo"); cm = _pv_cam(pg)
        d = _m.dist((cm["x"], cm["y"], cm["z"]), (ch["ex"], ch["ey"], ch["ez"]))
        ok("角色視角：鏡頭在眼睛附近（距離 %.2f 公尺，門檻 ≤ 0.35）、高度 %.2f 在「身高＋坐墊高」%.2f 的 40%%～100%%" % (d, cm["y"], ch["h"]), d <= 0.35 and 0.4 * ch["h"] <= cm["y"] <= ch["h"] + 0.05, (cm, ch))
        ang = _pv_deg(cm["yaw"], ch["yaw"])
        ok("角色視角：鏡頭朝向與角色面向夾角 %.1f 度（門檻 ≤ 12）" % ang, ang <= 12, (cm, ch))
        ok("角色視角：自己的身體、配件、道具從主鏡頭看不到（可繪製物件 %d 件，要 0）" % _pv_vis(pg, "ceo"), _pv_vis(pg, "ceo") == 0)
        ok("角色視角：自己的名牌、選取光環不顯示", pg.evaluate("() => { const W = __world, c = W.chars.get('ceo'); return !c._lab.on && !W.pilot.halo.visible; }"))
        ok("角色視角：入口鈕同步亮起（資訊卡、視角切換列「角色視角」）", pg.evaluate("() => document.querySelector('#card [data-i=pov]').classList.contains('on') && document.getElementById('viewPov').classList.contains('on') && !document.querySelector('#viewSeg [data-v=ceo]').classList.contains('on')"))
        ok("角色視角：鏡頭提示改成「拖曳環顧・按 V 或 Esc 回原視角」", pg.evaluate("() => /拖曳環顧/.test(document.querySelector('.cm-hint').textContent)"))
        _pv_shot(pg, "角色視角_CEO.png")
        # ── 左鍵拖曳環顧：角色不動 ──
        before = _pv_cam(pg); c0 = _pv_ch(pg, "ceo")
        fx, fy = _pv_free(pg)
        _pv_drag(pg, fx, fy, 240, 0)
        after = _pv_cam(pg); c1 = _pv_ch(pg, "ceo")
        dyaw = _pv_deg(after["yaw"], before["yaw"])
        ok("角色視角：左鍵拖曳 240 像素 → 視線方位改變 %.1f 度（要 ≥ 20）、角色本身位置與朝向不變" % dyaw, dyaw >= 20 and _m.hypot(c1["x"] - c0["x"], c1["z"] - c0["z"]) < 0.02 and _pv_deg(c1["yaw"], c0["yaw"]) < 3, (before, after, c0, c1))
        _pv_drag(pg, fx, fy, 0, -120)
        c2 = _pv_cam(pg)
        ok("角色視角：往上拖 → 視線上下改變（仰角 %.0f → %.0f 度）" % (_m.degrees(after["pitch"]), _m.degrees(c2["pitch"])), abs(c2["pitch"] - after["pitch"]) > 0.15, (after, c2))
        # 放開後的回正規則：站著不動時左右維持，上下 2.5 秒後回平視
        pg.wait_for_timeout(300)
        yawA = _pv_cam(pg)["yaw"]; pg.wait_for_timeout(1500); yawB = _pv_cam(pg)["yaw"]
        ok("角色視角：放開後，站著不動時左右視角維持你轉過去的方向（相差 %.1f 度）" % _pv_deg(yawA, yawB), _pv_deg(yawA, yawB) < 5)
        lvl = wait_until(pg, "() => { const d = new __world.THREE.Vector3(); __world.camera.getWorldDirection(d); return Math.abs(Math.asin(d.y)) < 0.12; }", 20000, 300)
        ok("角色視角：放開後上下視角慢慢回到平視（仰角 %.0f 度 → %.0f 度）" % (_m.degrees(c2["pitch"]), _m.degrees(_pv_cam(pg)["pitch"])), bool(lvl))
        # ── 操控：前進＝角色前方、鏡頭跟著 ──
        pg.evaluate("() => { __world.pov.yaw = 0; }")
        pg.keyboard.down("ArrowUp")
        ok("角色視角：按 ↑ 後接管（從椅子上起身）", _pv_engaged(pg))
        pg.evaluate("() => { __world.speed = 2; }")
        p0 = _pv_snap(pg, "ceo")
        pg.wait_for_timeout(1500)
        p1 = _pv_snap(pg, "ceo")
        pg.keyboard.up("ArrowUp"); pg.wait_for_timeout(400)
        mv = _m.hypot(p1["cx"] - p0["cx"], p1["cz"] - p0["cz"]); cmv = _m.hypot(p1["cam"][0] - p0["cam"][0], p1["cam"][2] - p0["cam"][2])
        dirm = _m.atan2(p1["cx"] - p0["cx"], p1["cz"] - p0["cz"])
        ok("角色視角：往前走 %.2f 公尺，方向與「身體前方」夾角 %.0f 度（要 ≤ 25）" % (mv, _pv_deg(dirm, (p0["cyaw"] + p1["cyaw"]) / 2)), mv > 0.3 and _pv_deg(dirm, (p0["cyaw"] + p1["cyaw"]) / 2) <= 25, (p0, p1))
        ok("角色視角：前進時鏡頭跟著移動 %.2f 公尺（角色 %.2f 公尺，要 ≥ 75%%；貼牆時鏡頭會被往回推一點，不穿牆）；鏡頭方位與面向夾角 %.0f 度" % (cmv, mv, _pv_deg(p1["camyaw"], p1["cyaw"])), cmv >= mv * 0.75 and _pv_deg(p1["camyaw"], p1["cyaw"]) <= 12, (p0, p1))
        ch = _pv_ch(pg, "ceo"); cm = _pv_cam(pg)
        ok("角色視角：走動後鏡頭仍在眼睛附近（%.2f 公尺）、朝向與面向夾角 %.0f 度" % (_m.dist((cm["x"], cm["y"], cm["z"]), (ch["ex"], ch["ey"], ch["ez"])), _pv_deg(cm["yaw"], ch["yaw"])), _m.dist((cm["x"], cm["y"], cm["z"]), (ch["ex"], ch["ey"], ch["ez"])) <= 0.4 and _pv_deg(cm["yaw"], ch["yaw"]) <= 25, (cm, ch))
        cmw = _pv_cam(pg); B = pg.evaluate("() => __world.layout.size")
        ok("角色視角：貼著牆走時鏡頭不穿牆（鏡頭 x=%.2f z=%.2f 都在辦公室內側 0.3 公尺以上）" % (cmw["x"], cmw["z"]), 0.3 - 1e-6 <= cmw["x"] <= B["w"] - 0.3 + 1e-6 and 0.3 - 1e-6 <= cmw["z"] <= B["d"] + 9 + 1e-6, (cmw, B))
        # 轉身：← 轉身，視角跟著
        a0 = _pv_ch(pg, "ceo")["yaw"]; k0 = _pv_cam(pg)["yaw"]
        pg.keyboard.down("ArrowLeft"); pg.wait_for_timeout(700); pg.keyboard.up("ArrowLeft"); pg.wait_for_timeout(500)
        a1 = _pv_ch(pg, "ceo")["yaw"]; k1 = _pv_cam(pg)["yaw"]
        ok("角色視角：按 ← 身體轉向（轉了 %.0f 度）、視角跟著轉（視角轉了 %.0f 度）" % (_pv_deg(a1, a0), _pv_deg(k1, k0)), _pv_deg(a1, a0) > 15 and abs(_pv_deg(k1, k0) - _pv_deg(a1, a0)) < 20 and _pv_deg(k1, a1) < 15, (a0, a1, k0, k1))
        # 跳躍：視角跟著升高
        pg.evaluate("() => { __world.speed = 1; window.__ymax = -1; window.__ystop = 0; (function f() { window.__ymax = Math.max(window.__ymax, __world.camera.position.y); if (!window.__ystop) requestAnimationFrame(f); })(); }")
        pg.wait_for_timeout(500)
        y0 = _pv_cam(pg)["y"]; pg.evaluate("() => { window.__ymax = -1; }")
        pg.keyboard.press("Space"); pg.wait_for_timeout(2500)
        ymax = pg.evaluate("() => { window.__ystop = 1; return window.__ymax; }")
        ok("角色視角：按 Space 跳躍，視角高度升高 %.2f 公尺（要 ≥ 0.08；站著 %.2f → 最高 %.2f）" % (ymax - y0, y0, ymax), ymax - y0 >= 0.08, (y0, ymax))
        pg.evaluate("() => { __world.speed = 8; }")
        pg.wait_for_timeout(1200)
        # ── E／F 互動照常，不重疊、不穿進別人 ──
        pg.evaluate("""() => { const W = __world, me = W.chars.get('ceo'), o = W.chars.get('animation-director') || [...W.chars.values()].find(c => c !== me && !c.spec.pet), p = me.object3D.position, h = me.inner.yaw;
          const q = W.nav.nearestFree(p.x + Math.sin(h) * 1.2, p.z + Math.cos(h) * 1.2, 6) || { x: p.x + 1.2, z: p.z }; o.script = (o.script || 0) + 1; o.job = (o.job || 0) + 1; o.busy = true; o.stop(false); o.standAt(q.x, q.z, h + Math.PI); window.__other = o.spec.id; }""")
        pg.wait_for_timeout(1000)
        oid = pg.evaluate("() => window.__other")
        near = wait_until(pg, "() => { const h = document.querySelector('.pt-hint'); return h && !h.hidden && /按 E 溝通/.test(h.textContent); }", 15000, 200)
        ok("角色視角：走到同事旁邊，頭上出現「按 E 溝通」提示（對方 %s）" % oid, near)
        hr = _pv_rect(pg, ".pt-hint")
        ok("角色視角：「按 E 溝通」提示在畫面內看得到（位置 %s；上緣 ≥ 100 像素，不被頂列擋住）" % (hr,), bool(hr) and hr[0] >= 0 and hr[2] <= 1280 and hr[1] >= 100 and hr[3] <= 800, hr)
        o = _pv_ch(pg, oid); cm = _pv_cam(pg)
        ok("角色視角：鏡頭沒有穿進對方身體（水平距離 %.2f，對方半徑 %.2f）" % (_m.hypot(cm["x"] - o["x"], cm["z"] - o["z"]), o["r"]), _m.hypot(cm["x"] - o["x"], cm["z"] - o["z"]) >= o["r"] * 0.9, (cm, o))
        _pv_shot(pg, "角色視角_靠近同事.png")
        pg.keyboard.press("e")
        ok("角色視角：按 E 溝通，對方資訊卡打開、泡泡出現", wait_until(pg, "() => __world.pilot.talking && !document.getElementById('card').hidden", 15000, 150) and wait_until(pg, "() => [...document.querySelectorAll('.bub')].some(e => { const r = e.getBoundingClientRect(); return r.width && r.right > 0 && r.top > 0; })", 15000, 150))
        pg.wait_for_timeout(400)
        bad, n = _pv_no_overlap(pg, ["#card", ".pt-tips", ".pt-hint", "#bar .ttl", "#viewSeg", "#areaBtn", "#demoBtn", "#speedSeg", "#editBtn", ".cm-hint"])
        ok("角色視角：溝通中，資訊卡、提示卡、頂列、鏡頭提示互不重疊（比對 %d 個）%s" % (n, bad), not bad, bad)
        bubs = _pv_bubbles(pg)
        pair = [(i, j) for i in range(len(bubs)) for j in range(i + 1, len(bubs)) if _pv_hit(bubs[i], bubs[j])]
        ok("角色視角：溝通中畫面上 %d 個泡泡互不重疊" % len(bubs), not pair, bubs)
        cardr = _pv_rect(pg, "#card")
        ok("角色視角：泡泡不蓋到資訊卡與頂列", not any(_pv_hit(bb, cardr) for bb in bubs) and not any(bb[1] < 52 for bb in bubs), (bubs, cardr))
        wait_until(pg, "() => !__world.pilot.talking", 30000, 300)
        pg.evaluate("() => { __world.speed = 1; const c = __world.chars.get('ceo'); window.__acts = []; const o = c.setAction; c.setAction = (n, a) => { window.__acts.push(n); return o.call(c, n, a); }; }")
        pg.keyboard.press("f"); pg.wait_for_timeout(500)
        ok("角色視角：按 F 揮手照常（動作 wave、說「嗨～」）", pg.evaluate("() => window.__acts.includes('wave')") and pg.evaluate("() => { const c = __world.chars.get('ceo'); return !!c.speech && /嗨/.test(c.speech.text); }"))
        pg.evaluate("() => { __world.speed = 8; }")
        # ── 退出：Esc 回原視角，選取還在 ──
        pg.keyboard.press("Escape")
        ok("角色視角：Esc 回到原視角（pov 關閉）", wait_until(pg, "() => __world.pov.st === 'off'", 8000, 100))
        ok("角色視角：Esc 只退出角色視角，角色還在選取中", pg.evaluate("() => !!__world.pilot.sel && __world.pilot.sel.spec.id === 'ceo'"))
        ok("角色視角：退出後身體又看得到、名牌回來、控制恢復", pg.evaluate("() => { const W = __world; return W.camera.near > 0.2 && W.controls.enabled && W.camera.fov < 60; }") and _pv_vis(pg, "ceo") > 5)
        ok("角色視角：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
        pg.keyboard.press("Escape"); pg.wait_for_timeout(600)
        ok("角色視角：再按一次 Esc 才結束選取", pg.evaluate("() => !__world.pilot.sel"))
    finally:
        c.close()


def t_pov_exit(b, base):
    """進出、回到原視角、取消選取自動退出、別人的資訊卡、換視角、體型"""
    c, pg, got = _pv_open(b, base, speed=3)
    try:
        ok("角色視角（進出）：頁面載入完成", got)
        if not got:
            return
        _pv_sel(pg, "data-scraper"); pg.wait_for_timeout(2200)
        before = _pv_cam(pg)
        pg.keyboard.press("v")
        ok("角色視角（進出）：按 V 進入", wait_until(pg, "() => __world.pov.st === 'on'", 8000, 100))
        pg.keyboard.press("v")
        ok("角色視角（進出）：再按一次 V 離開", wait_until(pg, "() => __world.pov.st === 'off'", 8000, 100))
        pg.wait_for_timeout(300)
        after = _pv_cam(pg)
        d = _m.dist((before["x"], before["y"], before["z"]), (after["x"], after["y"], after["z"]))
        ok("角色視角（進出）：離開後鏡頭回到先前視角附近（相距 %.2f 公尺，門檻 ≤ 1.5；方位差 %.0f 度）" % (d, _pv_deg(before["yaw"], after["yaw"])), d <= 1.5 and _pv_deg(before["yaw"], after["yaw"]) <= 20, (before, after))
        # 進入過渡是平順的：沒有一幀就跳到頭上
        pg.evaluate("() => { window.__pp = []; window.__stT = {}; const W = __world; (function f() { const p = W.camera.position, t = performance.now(); window.__pp.push([p.x, p.y, p.z, t]); const st = W.pov.st; if (!(st in window.__stT)) window.__stT[st] = t; if (!window.__ppStop) requestAnimationFrame(f); })(); }")
        pg.keyboard.press("v"); wait_until(pg, "() => __world.pov.st === 'on'", 8000, 100); pg.wait_for_timeout(300)
        pg.evaluate("() => { window.__ppStop = 1; }")
        pp = pg.evaluate("() => window.__pp"); stT = pg.evaluate("() => window.__stT")
        steps = [_m.dist(pp[i][:3], pp[i + 1][:3]) for i in range(len(pp) - 1)]
        tot = _m.dist(pp[0][:3], pp[-1][:3]); dur = (stT.get("on", 0) - stT.get("in", 0)) / 1000
        ok("角色視角（進出）：切入過渡約 0.5 秒（量到 %.2f 秒，容許 0.35–1.5；軟體繪圖下畫面更新慢，所以放寬）" % dur, 0.35 <= dur <= 1.5, stT)
        ok("角色視角（進出）：切入是漸進的不是瞬跳（%d 個畫面、單格最大位移佔總位移 %.0f%%，要 ≤ 85%%）" % (len(pp), 100 * max(steps) / max(tot, 1e-6)), len(pp) >= 4 and max(steps) <= 0.85 * tot, (steps, tot))
        # 取消選取自動退出
        pg.evaluate("() => __world.pilot.deselect()")
        ok("角色視角（進出）：取消選取後自動退出", wait_until(pg, "() => __world.pov.st === 'off'", 8000, 100))
        # 點資訊卡上別人的「角色視角」會先選取他
        _pv_sel(pg, "data-scraper"); pg.wait_for_timeout(300)
        oth = pg.evaluate("() => { const W = __world; const o = W.chars.get('ceo'); W.ui.showCard(o); return o.spec.id; }")
        pg.click("#card [data-i=pov]")
        ok("角色視角（進出）：資訊卡是別人時，按「角色視角」會選取並進入他的視角", wait_until(pg, "() => __world.pov.st === 'on' && __world.pov.c.spec.id === 'ceo' && __world.pilot.sel && __world.pilot.sel.spec.id === 'ceo'", 8000, 100))
        # 切到別的視角：立刻離開
        pg.click("#viewSeg [data-v=god]")
        ok("角色視角（進出）：切到「俯瞰」立刻退出角色視角、鏡頭恢復一般控制", wait_until(pg, "() => __world.pov.st === 'off' && __world.controls.enabled && __world.camera.near > 0.2", 6000, 100))
        # 點別人也會換掉
        pg.evaluate("() => __world.pilot.deselect()")
        # ── 體型：矮的與高的 ──
        ex = pg.evaluate("""() => { const W = __world; const a = [...W.chars.values()].filter(c => !c.away && !c.jobless && !c.spec.isCeo); a.sort((p, q) => p.height - q.height);
          const f = a.find(c => c.inner.cfg.floatH) || null; return { small: a[0].spec.id, smallH: a[0].height, big: a[a.length - 1].spec.id, bigH: a[a.length - 1].height, floaty: f && f.spec.id }; }""")
        res = {}
        for tag, cid in [("矮小", ex["small"]), ("高大", ex["big"]), ("漂浮", ex["floaty"])]:
            if not cid:
                continue
            _pv_sel(pg, cid); pg.wait_for_timeout(1800)
            pg.keyboard.press("v"); wait_until(pg, "() => __world.pov.st === 'on'", 8000, 100); pg.wait_for_timeout(500)
            ch = _pv_ch(pg, cid); cm = _pv_cam(pg)
            d = _m.dist((cm["x"], cm["y"], cm["z"]), (ch["ex"], ch["ey"], ch["ez"]))
            res[tag] = (cm["y"], ch["h"])
            ok("角色視角（體型）：%s（%s，身高 %.2f）眼睛高度 %.2f 公尺在身高的 35%%～105%%、鏡頭距眼睛 %.2f 公尺" % (tag, cid, ch["h"], cm["y"], d), 0.35 * ch["h"] <= cm["y"] <= 1.05 * ch["h"] + 0.1 and d <= 0.35, (cm, ch))
            if tag == "矮小":
                _pv_shot(pg, "角色視角_小體型.png")
            pg.keyboard.press("Escape"); wait_until(pg, "() => __world.pov.st === 'off'", 8000, 100); pg.evaluate("() => __world.pilot.deselect()"); pg.wait_for_timeout(300)
        if "矮小" in res and "高大" in res:
            ok("角色視角（體型）：矮小的眼睛（%.2f）比高大的（%.2f）低，依身高推算" % (res["矮小"][0], res["高大"][0]), res["矮小"][0] < res["高大"][0], res)
        ok("角色視角（進出）：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_face(b, base):
    """點選角色時面向鏡頭"""
    c, pg, got = _pv_open(b, base, speed=1)
    try:
        ok("面向鏡頭：頁面載入完成", got)
        if not got:
            return
        # ── 站著、背對鏡頭的人 ──
        pg.evaluate("""() => { const W = __world, c = W.chars.get('data-scraper'); W.setView('god', null, true); }""")
        pg.wait_for_timeout(1200)
        pg.evaluate("""() => { const W = __world, c = W.chars.get('data-scraper'), q = W.nav.nearestFree(20, 27, 8), cp = W.camera.position;
          c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.stop(false); c.standAt(q.x, q.z, Math.atan2(cp.x - q.x, cp.z - q.z) + Math.PI); }""")
        pg.wait_for_timeout(1500)
        y0 = _pv_ch(pg, "data-scraper")["yaw"]; t0 = _pv_toward(pg, "data-scraper")
        ok("面向鏡頭：測試前他背對鏡頭（朝向與「角色→鏡頭」夾角 %.0f 度，要 ≥ 140）" % _pv_deg(y0, t0), _pv_deg(y0, t0) >= 140)
        _pv_shot(pg, "_face_before.png")
        pt = pg.evaluate("() => { const W = __world, c = W.chars.get('data-scraper'), k = c.scale || 1, px = W.renderer.domElement.clientHeight / (2 * Math.tan(W.camera.fov * Math.PI / 360) * c._sd); return [c._sx, c._sy + px * 0.45 * k]; }")
        pg.evaluate("() => { window.__yy = []; const W = __world, c = W.chars.get('data-scraper'); (function f() { window.__yy.push(c.inner.yaw); if (!window.__yyStop) requestAnimationFrame(f); })(); }")
        pg.mouse.click(pt[0], pt[1])
        ok("面向鏡頭：真的點他 → 選取成功", wait_until(pg, "() => __world.pilot.sel && __world.pilot.sel.spec.id === 'data-scraper'", 6000, 100))
        pg.wait_for_timeout(3800)
        pg.evaluate("() => { window.__yyStop = 1; }")
        yy = pg.evaluate("() => window.__yy")
        y1 = _pv_ch(pg, "data-scraper")["yaw"]; t1 = _pv_toward(pg, "data-scraper")
        ang = _pv_deg(y1, t1)
        ok("面向鏡頭：點選後他的面向與「角色→鏡頭」水平方向夾角 %.1f 度（門檻 < 20）" % ang, ang < 20, (y1, t1))
        jumps = [_pv_deg(yy[i + 1], yy[i]) for i in range(len(yy) - 1)]
        ok("面向鏡頭：轉身是平順的（%d 個畫面，單格最大轉動 %.0f 度，要 < 120；總共轉了 %.0f 度）" % (len(yy), max(jumps) if jumps else 0, _pv_deg(y1, y0)), len(yy) >= 6 and max(jumps) < 120 and _pv_deg(y1, y0) > 100, jumps)
        ok("面向鏡頭：「被注意到」的反應有觸發（精神一振、只做一次）", pg.evaluate("() => __world.attn.reacts >= 1"))
        ok("面向鏡頭：面向鏡頭的狀態持續中（眼睛與頭一直看向鏡頭）", pg.evaluate("() => __world.attn.current() === __world.chars.get('data-scraper')"))
        _pv_shot(pg, "點選後面向鏡頭_前後.png")
        # 鏡頭大幅移動後仍然面向：拖曳鏡頭繞一圈
        pg.evaluate("() => __world.cam.setMode('rotate')")
        pg.mouse.move(640, 300); pg.mouse.down(); pg.mouse.move(640 + 500, 300, steps=10); pg.mouse.up(); pg.wait_for_timeout(2500)
        y2 = _pv_ch(pg, "data-scraper")["yaw"]; t2 = _pv_toward(pg, "data-scraper")
        ok("面向鏡頭：鏡頭繞到別的方位後，他的面向持續跟著（夾角 %.1f 度 < 25）" % _pv_deg(y2, t2), _pv_deg(y2, t2) < 25)
        pg.evaluate("() => __world.cam.setMode('move')")
        # 取消選取：回原朝向
        pg.evaluate("() => __world.pilot.deselect()")
        pg.wait_for_timeout(3000)
        y3 = _pv_ch(pg, "data-scraper")["yaw"]
        ok("面向鏡頭：取消選取後轉回原本的朝向（夾角 %.0f 度 < 15）、沒有瞬移" % _pv_deg(y3, y0), _pv_deg(y3, y0) < 15)
        ok("面向鏡頭：取消選取後不再追著鏡頭（attn 釋放）", pg.evaluate("() => !__world.attn.current()"))
        # 操控後朝向跟著移動方向
        _pv_sel(pg, "data-scraper"); pg.wait_for_timeout(2500)
        pg.keyboard.down("ArrowLeft")
        ok("面向鏡頭：按方向鍵接管後，面向鏡頭的狀態解除", _pv_engaged(pg) and pg.evaluate("() => !__world.attn.current()"))
        p0 = _pv_ch(pg, "data-scraper"); pg.wait_for_timeout(1800)
        p1 = _pv_ch(pg, "data-scraper"); pg.keyboard.up("ArrowLeft"); pg.wait_for_timeout(500)
        mvdir = _m.atan2(p1["x"] - p0["x"], p1["z"] - p0["z"]); mv = _m.hypot(p1["x"] - p0["x"], p1["z"] - p0["z"])
        ok("面向鏡頭：操控中朝向跟著移動方向（移動 %.2f 公尺，方向與朝向夾角 %.0f 度 ≤ 30）" % (mv, _pv_deg(mvdir, _pv_ch(pg, "data-scraper")["yaw"])), mv > 0.3 and _pv_deg(mvdir, _pv_ch(pg, "data-scraper")["yaw"]) <= 30)
        pg.evaluate("() => __world.pilot.release({ noHome: true, silent: true })")
        # ── 不同體型：矮小、高大、漂浮的人也都自然地轉過來 ──
        ex = _pv_pick_extremes(pg)
        for i, (tag, cid) in enumerate([("矮小", ex["small"]), ("高大", ex["big"]), ("漂浮", ex["floaty"])]):
            if not cid:
                continue
            pg.evaluate("() => { __world.pilot.deselect(); __world.setView('god', null, true); }"); pg.wait_for_timeout(500)
            pg.evaluate("""([id, x]) => { const W = __world, c = W.chars.get(id), q = W.nav.nearestFree(x, 27, 8), cp = W.camera.position; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.stop(false); c.standAt(q.x, q.z, Math.atan2(cp.x - q.x, cp.z - q.z) + Math.PI); }""", [cid, 14 + i * 6])
            pg.wait_for_timeout(1200)
            _pv_sel(pg, cid); pg.wait_for_timeout(3200)
            e = _pv_deg(_pv_ch(pg, cid)["yaw"], _pv_toward(pg, cid))
            ok("面向鏡頭（體型）：%s（%s）點選後轉過來面向鏡頭，夾角 %.1f 度（< 20）" % (tag, cid, e), e < 20)
            if tag == "漂浮":
                _pv_shot(pg, "_face_float.png")
        pg.evaluate("() => __world.pilot.deselect()"); pg.wait_for_timeout(500)
        # ── 坐著：CEO ──
        pg.evaluate("() => { const W = __world; W.setView('god', null, true); }"); pg.wait_for_timeout(800)
        s0 = _pv_ch(pg, "ceo")
        _pv_sel(pg, "ceo"); pg.wait_for_timeout(3500)
        s1 = _pv_ch(pg, "ceo"); tt = _pv_toward(pg, "ceo")
        rel = (tt - s0["face"] + _m.pi) % (2 * _m.pi) - _m.pi
        ideal = s0["face"] + max(-1.75, min(1.75, rel))
        ok("面向鏡頭（坐著）：不離座、位置不動（移動 %.3f 公尺）、仍是坐姿" % _m.hypot(s1["x"] - s0["x"], s1["z"] - s0["z"]), _m.hypot(s1["x"] - s0["x"], s1["z"] - s0["z"]) < 0.03 and s1["state"] == "sit")
        ok("面向鏡頭（坐著）：轉椅子朝向鏡頭，最多轉 100 度（目標 %.0f 度、實際相差 %.0f 度 < 20；與鏡頭方向夾角 %.0f 度）" % (_m.degrees(ideal), _pv_deg(s1["yaw"], ideal), _pv_deg(s1["yaw"], tt)), _pv_deg(s1["yaw"], ideal) < 20 and _pv_deg(s1["yaw"], s0["face"]) > 20, (s0, s1, tt))
        _pv_shot(pg, "_face_seated.png")
        pg.evaluate("() => __world.pilot.deselect()"); pg.wait_for_timeout(2500)
        s2 = _pv_ch(pg, "ceo")
        ok("面向鏡頭（坐著）：取消選取後椅子轉回原朝向（夾角 %.0f 度 < 15）、仍坐在原位" % _pv_deg(s2["yaw"], s0["face"]), _pv_deg(s2["yaw"], s0["face"]) < 15 and _m.hypot(s2["x"] - s0["x"], s2["z"] - s0["z"]) < 0.03 and s2["state"] == "sit")
        # ── 走路中：停下轉身，取消後繼續走 ──
        pg.evaluate("() => { __world.speed = 6; __world.director.routine('data-scraper', 'coffee'); }")
        ok("面向鏡頭（走路）：先讓他走起來", wait_until(pg, "() => { const c = __world.chars.get('data-scraper'); return c.state === 'walk' && !c._hop; }", 30000, 200))
        pg.wait_for_timeout(800)
        pg.evaluate("() => { __world.speed = 1; }")
        _pv_sel(pg, "data-scraper"); pg.wait_for_timeout(1500)
        w0 = _pv_ch(pg, "data-scraper"); pg.wait_for_timeout(1500); w1 = _pv_ch(pg, "data-scraper")
        ok("面向鏡頭（走路）：選取後停下腳步（1.5 秒只動 %.2f 公尺）、仍是「走路中」的狀態（取消後繼續走）" % _m.hypot(w1["x"] - w0["x"], w1["z"] - w0["z"]), _m.hypot(w1["x"] - w0["x"], w1["z"] - w0["z"]) < 0.12 and w1["state"] == "walk")
        ok("面向鏡頭（走路）：停下來面向鏡頭（夾角 %.0f 度 < 25）" % _pv_deg(w1["yaw"], _pv_toward(pg, "data-scraper")), _pv_deg(w1["yaw"], _pv_toward(pg, "data-scraper")) < 25)
        pg.evaluate("() => { __world.pilot.deselect(); __world.speed = 3; }"); pg.wait_for_timeout(2500)
        w2 = _pv_ch(pg, "data-scraper")
        ok("面向鏡頭（走路）：取消選取後繼續走原路（又走了 %.2f 公尺）" % _m.hypot(w2["x"] - w1["x"], w2["z"] - w1["z"]), _m.hypot(w2["x"] - w1["x"], w2["z"] - w1["z"]) > 0.4)
        # ── 睡覺中：不叫醒 ──
        pg.evaluate("() => { __world.speed = 1; const c = __world.chars.get('animation-director'); c.setAction('sleep'); c.sleeping = true; }")
        pg.wait_for_timeout(1200)
        _pv_sel(pg, "animation-director"); pg.wait_for_timeout(1500)
        ok("面向鏡頭（睡覺）：不叫醒、不轉身（仍在睡、位置朝向不變）", pg.evaluate("() => { const c = __world.chars.get('animation-director'); return c.action === 'sleep' && c.inner.mode === 'sleep' && c.state === 'sit'; }"))
        pg.evaluate("() => { __world.pilot.deselect(); const c = __world.chars.get('animation-director'); c.sleeping = false; c.setAction('type'); }")
        ok("面向鏡頭：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_pov_mobile(b, base):
    c, pg, got = _pv_open(b, base, w=390, h=844, touch=True, speed=3)
    try:
        ok("手機（角色視角）：頁面載入完成", got)
        if not got:
            return
        # ── 頂端工具列重排：只佔一小塊，其餘收進「更多」 ──
        bar = pg.evaluate("() => { const e = [...document.querySelectorAll('#bar > *')].filter(x => x.offsetParent); return { n: e.length, bottom: Math.max(...e.map(x => x.getBoundingClientRect().bottom)), ids: e.map(x => x.id || x.className) }; }")
        ok("手機：頂端工具列收起時最下緣在 %d 像素（畫面高 844 的 %.0f%%，要 ≤ 12%%）、可見項目 %s" % (bar["bottom"], bar["bottom"] / 8.44, bar["ids"]), bar["bottom"] <= 0.12 * 844, bar)
        ok("手機：收起時第一排只有標題、視角、「更多」；電力膠囊保留在看得到的位置", pg.evaluate("() => ['areaBtn', 'demoBtn', 'speedSeg', 'editBtn'].every(i => !document.getElementById(i).offsetParent) && !!document.getElementById('moreBtn').offsetParent && !!document.getElementById('pwBtn').offsetParent && !document.querySelector('.cm-hint').offsetParent && !document.querySelector('.dt-chip').offsetParent"))
        ok("手機：「更多」預設收起（aria-expanded=false）", pg.evaluate("() => document.getElementById('moreBtn').getAttribute('aria-expanded') === 'false'"))
        _pv_shot(pg, "手機工具列_後.png")
        pg.click("#moreBtn"); pg.wait_for_timeout(600)
        ok("手機：點「更多」展開 → 區域、示範、速度、整修、拖曳切換、時間都出現", pg.evaluate("() => ['areaBtn', 'demoBtn', 'speedSeg', 'editBtn'].every(i => !!document.getElementById(i).offsetParent) && !!document.querySelector('.cm-hint').offsetParent && !!document.querySelector('.dt-chip').offsetParent"))
        bad, n = _pv_no_overlap(pg, ["#bar .ttl", "#viewSeg", "#moreBtn", "#areaBtn", "#demoBtn", "#speedSeg", "#pwBtn", "#editBtn", ".cm-hint", ".dt-chip"])
        ok("手機：展開後各項目互不重疊（比對 %d 個）%s" % (n, bad), not bad, bad)
        ok("手機：展開後沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
        _pv_shot(pg, "手機工具列_展開.png")
        pg.click("#areaBtn"); pg.wait_for_timeout(300)
        ok("手機：展開後「區域」真的能點開選單", pg.evaluate("() => !document.getElementById('areaPop').hidden"))
        pg.click("#areaBtn"); pg.click("#moreBtn"); pg.wait_for_timeout(300)
        ok("手機：再點「更多」收回去", pg.evaluate("() => !document.getElementById('areaBtn').offsetParent && document.getElementById('moreBtn').getAttribute('aria-expanded') === 'false'"))
        # ── 角色視角 ──
        pg.evaluate("() => { __world.speed = 3; }")
        _pv_sel(pg, "ceo"); pg.wait_for_timeout(1800)
        pg.evaluate("() => { __world.view.detached = true; __world.view.dpos = null; }"); pg.wait_for_timeout(900)
        r = _pv_rect(pg, ".cm-hint .cm-back")
        ok("手機：手動平移後，「回到角色」鈕在收起的工具列下直接看得到（%s），其他鏡頭鈕仍收著" % (r,), bool(r) and not pg.evaluate("() => !!document.querySelector('.cm-hint .cm-seg').offsetParent"), r)
        if r:
            pg.click(".cm-hint .cm-back"); pg.wait_for_timeout(500)
        ok("手機：點「回到角色」後恢復跟隨、鈕消失", pg.evaluate("() => !__world.view.detached") and not _pv_rect(pg, ".cm-hint .cm-back"))
        ok("手機（角色視角）：資訊卡有「角色視角」鈕、操控列有「視角」鈕", pg.evaluate("() => !!document.querySelector('#card [data-i=pov]') && !!document.querySelector('.pt-pov')"))
        ok("手機（角色視角）：視角切換列第一排放不下，不顯示「角色視角」格（入口在資訊卡與操控列）", pg.evaluate("() => !document.getElementById('viewPov').offsetParent"))
        sels = [".pt-joy", ".pt-jump", ".pt-talk", ".pt-wave", ".pt-pov", ".pt-tips", "#card", "#bar .ttl", "#viewSeg", "#moreBtn", "#pwBtn"]
        bad, n = _pv_no_overlap(pg, sels)
        ok("手機（角色視角）：選取後操控列、搖桿、提示卡、資訊卡、頂列互不重疊（比對 %d 個）%s" % (n, bad), not bad, bad)
        szs = pg.evaluate("() => [...document.querySelectorAll('.pt-b')].map(e => [e.className, Math.round(e.offsetWidth), Math.round(e.offsetHeight)])")
        ok("手機（角色視角）：操控列每顆鈕至少 44×44 像素（%s）" % szs, all(w >= 44 and h >= 44 for _, w, h in szs), szs)
        pg.tap(".pt-pov")
        ok("手機（角色視角）：點「視角」鈕進入角色視角", wait_until(pg, "() => __world.pov.st === 'on'", 10000, 100))
        pg.wait_for_timeout(500)
        ch = _pv_ch(pg, "ceo"); cm = _pv_cam(pg)
        ok("手機（角色視角）：鏡頭在眼睛附近（%.2f 公尺）、朝向與面向夾角 %.0f 度" % (_m.dist((cm["x"], cm["y"], cm["z"]), (ch["ex"], ch["ey"], ch["ez"])), _pv_deg(cm["yaw"], ch["yaw"])), _m.dist((cm["x"], cm["y"], cm["z"]), (ch["ex"], ch["ey"], ch["ez"])) <= 0.4 and _pv_deg(cm["yaw"], ch["yaw"]) <= 15)
        ok("手機（角色視角）：「視角」鈕亮起、鏡頭提示寫「單指拖曳環顧」", pg.evaluate("() => document.querySelector('.pt-pov').classList.contains('on') && /單指拖曳環顧/.test(document.querySelector('.cm-hint') ? document.querySelector('.cm-hint').textContent : '單指拖曳環顧')"))
        # 單指拖曳環顧（合成觸控指標事件）
        before = _pv_cam(pg); fx, fy = _pv_free(pg)
        pg.evaluate("""([x0, y0]) => { const cv = __world.renderer.domElement, mk = (t, x, y) => new PointerEvent(t, { pointerId: 7, pointerType: 'touch', isPrimary: true, button: 0, buttons: t === 'pointerup' ? 0 : 1, clientX: x, clientY: y, bubbles: true });
          cv.dispatchEvent(mk('pointerdown', x0, y0)); for (let i = 1; i <= 8; i++) cv.dispatchEvent(mk('pointermove', x0 + i * 20, y0)); cv.dispatchEvent(mk('pointerup', x0 + 160, y0)); }""", [fx, fy])
        pg.wait_for_timeout(500)
        after = _pv_cam(pg)
        ok("手機（角色視角）：單指拖曳 160 像素 → 視線轉了 %.0f 度（要 ≥ 15）、角色不動" % _pv_deg(after["yaw"], before["yaw"]), _pv_deg(after["yaw"], before["yaw"]) >= 15 and _pv_deg(_pv_ch(pg, "ceo")["yaw"], ch["yaw"]) < 3, (before, after))
        _pv_shot(pg, "手機_角色視角.png")
        bad, n = _pv_no_overlap(pg, [".pt-joy", ".pt-jump", ".pt-talk", ".pt-wave", ".pt-pov", ".pt-tips", "#card", "#bar .ttl", "#viewSeg", "#moreBtn", "#pwBtn"])
        ok("手機（角色視角）：角色視角中畫面元素互不重疊（比對 %d 個）%s" % (n, bad), not bad, bad)
        ok("手機（角色視角）：沒有橫向捲軸、字不小於 11px", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth && [...document.querySelectorAll('.pt-tips *, .pt-b, #bar *')].filter(e => e.children.length === 0 && e.textContent.trim() && e.offsetParent).every(e => parseFloat(getComputedStyle(e).fontSize) >= 11)"))
        pg.tap(".pt-pov")
        ok("手機（角色視角）：再點一次「視角」鈕回到原視角", wait_until(pg, "() => __world.pov.st === 'off'", 10000, 100))
        txt = pg.evaluate("() => document.body.innerText")
        ok("手機（角色視角）：畫面文字不含價格／付費／升級／方案／Plus／Pro／免費／右鍵", not _PV_FORBID.search(txt), _PV_FORBID.findall(txt))
        ok("手機（角色視角）：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_pov_copy(b, base):
    """預覽部署會略過名為 data、preview 的資料夾：照那個規則複製 site 再起伺服器，跑角色視角與面向的核心流程，並檢查主控台錯誤與禁用字"""
    import functools, http.server, shutil, socketserver, tempfile, threading
    src = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "site"))
    dst = _os.path.join(tempfile.mkdtemp(prefix="office_pov_preview_"), "site")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("data", "preview"))

    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Q, directory=dst))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        ok("預覽部署重建（視角）：複製後沒有 data／preview 資料夾、視角與面向用到的檔案都在", not _os.path.exists(_os.path.join(dst, "data")) and not _os.path.exists(_os.path.join(dst, "preview")) and all(_os.path.exists(_os.path.join(dst, "office", "world", "js", f)) for f in ["pov.js", "attention.js", "pilot.js", "main.js"]))
        c, pg, got = _pv_open(b, "http://127.0.0.1:%d/index.html" % srv.server_address[1], speed=3)
        try:
            ok("預覽部署重建（視角）：office/world.html 載入完成", got)
            if not got:
                return
            _pv_sel(pg, "ceo"); pg.wait_for_timeout(1500)
            att = pg.evaluate("() => __world.attn.current() && __world.attn.current().spec.id")
            ok("預覽部署重建（視角）：點選後面向鏡頭啟動（%s）" % att, att == "ceo")
            pg.keyboard.press("v")
            ok("預覽部署重建（視角）：按 V 進入角色視角", wait_until(pg, "() => __world.pov.st === 'on'", 10000, 100))
            txt = pg.evaluate("() => document.body.innerText")
            ok("預覽部署重建（視角）：畫面文字不含價格／NT$／付費／升級／訂閱／方案／Plus／Pro／免費／右鍵", not _PV_FORBID.search(txt), _PV_FORBID.findall(txt))
            pg.keyboard.press("Escape")
            ok("預覽部署重建（視角）：Esc 回原視角", wait_until(pg, "() => __world.pov.st === 'off'", 10000, 100))
            ok("預覽部署重建（視角）：沒有主控台錯誤", not pg.errs, pg.errs[:3])
        finally:
            c.close()
    finally:
        srv.shutdown()
        shutil.rmtree(_os.path.dirname(dst), ignore_errors=True)


def t_pov_all(b, base):
    t_pov_desktop(b, base)
    t_pov_exit(b, base)
    t_face(b, base)
    t_pov_mobile(b, base)
    t_pov_copy(b, base)


register("辦公室視角與面向", lambda pg, b, base, code: t_pov_all(b, base))
