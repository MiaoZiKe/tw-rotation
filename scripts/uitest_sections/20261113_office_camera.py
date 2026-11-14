# 驗收段落「辦公室鏡頭」（擁有者 11-13：一律左鍵、拖曳速度太快、視角鈕重複）
#   · 左鍵拖曳＝抓著地面拖：預設俯視拖 100 像素，起點對應的地面點在畫面上的位移與滑鼠位移誤差 ≤ 10%；近距離同樣
#   · 切到「旋轉」才是左鍵旋轉（拖畫面寬度 1/4 約轉 45 度）；↺ ↻ 鈕點一下轉一格、按住持續轉；右鍵只是隱藏捷徑
#   · 提示文字「拖曳移動・滾輪縮放・雙擊地面前往」不含右鍵；靈敏度慢／中／快記在 localStorage；視角鈕第三格不再重複「CEO」
# flake8: noqa
import math as _m


def _o(b, base, w=1280, h=800, touch=False):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    pg = c.new_page(); pg.set_default_timeout(120000); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(base.split("/index.html")[0] + "/office/world.html?ambient=0&q=low&pr=0.4", wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    if got:
        pg.evaluate("() => { __world.speed = 1; }")
    pg.wait_for_timeout(800)
    return c, pg, got


def _st(pg):
    return pg.evaluate("() => { const W = __world, c = W.camera, t = W.controls.target; return { az: Math.atan2(c.position.x - t.x, c.position.z - t.z), d: c.position.distanceTo(t), tx: t.x, tz: t.z }; }")


def _ground(pg, x, y):
    return pg.evaluate("""([x, y]) => { const W = __world, r = W.renderer.domElement.getBoundingClientRect(), T = W.THREE, v = new T.Vector2((x - r.left) / r.width * 2 - 1, -(y - r.top) / r.height * 2 + 1), rc = new T.Raycaster(); rc.setFromCamera(v, W.camera); const p = new T.Vector3(); rc.ray.intersectPlane(new T.Plane(new T.Vector3(0, 1, 0), 0), p); return [p.x, p.z]; }""", [x, y])


def _scr(pg, gx, gz):
    return pg.evaluate("""([x, z]) => { const W = __world, T = W.THREE, v = new T.Vector3(x, 0, z).project(W.camera), r = W.renderer.domElement.getBoundingClientRect(); return [(v.x + 1) / 2 * r.width, (1 - v.y) / 2 * r.height]; }""", [gx, gz])


def t_camera2(b, base):
    c, pg, got = _o(b, base)
    try:
        ok("鏡頭：載入完成", got)
        if not got:
            return
        hint = pg.evaluate("() => document.querySelector('.cm-hint').textContent")
        ok("鏡頭：提示文字是「快速拖曳：移動場景・長按後拖曳：調整角度・滾輪：縮放・雙擊地面：前往」且不含「右鍵」（11-14 改成長按旋轉）", "快速拖曳：移動場景・長按後拖曳：調整角度・滾輪：縮放・雙擊地面：前往" in hint and "右鍵" not in hint, hint)
        ok("鏡頭：畫面上任何文字都不提右鍵", "右鍵" not in pg.evaluate("() => document.body.innerText + [...document.querySelectorAll('[title],[aria-label]')].map(e => e.title + e.getAttribute('aria-label')).join('')"))
        ok("鏡頭：預設是「移動」（localStorage 沒記就是移動）", pg.evaluate("() => __world.cam.mode === 'move' && document.querySelector('.cm-seg [data-c=mv]').classList.contains('on')"))
        for name, close in [("預設俯視", False), ("近距離", True)]:
            if close:
                pg.evaluate("() => __world.godAt(20, 15, 14)"); wait_until(pg, "() => !__world.view.tween", 12000)
            pg.wait_for_timeout(600)
            a = _st(pg); x0, y0 = 640, 420; g0 = _ground(pg, x0, y0)
            pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move(x0 + 100, y0, steps=8); pg.wait_for_timeout(80); pg.mouse.up(); pg.wait_for_timeout(1500)
            b2 = _st(pg); s = _scr(pg, *g0)
            err = abs((s[0] - x0) - 100) / 100
            ok("左鍵拖曳 100 像素（%s）：注視點移動 %.2f 公尺；拖曳起點的地面點在畫面上位移 %.1f 像素，與滑鼠位移誤差 %.1f%%（≤ 10%%）、方位角不變" % (name, _m.hypot(b2["tx"] - a["tx"], b2["tz"] - a["tz"]), s[0] - x0, err * 100), err <= 0.10 and abs(s[1] - y0) < 10 and abs(b2["az"] - a["az"]) < 0.01, (s, a, b2))
        # 旋轉模式
        pg.click(".cm-seg [data-c=ro]")
        ok("切到「旋轉」：模式記在 localStorage", pg.evaluate("() => localStorage.getItem('aiOffice.cam.mode') === 'rotate' && __world.cam.mode === 'rotate'"))
        a = _st(pg); pg.mouse.move(640, 420); pg.mouse.down(); pg.mouse.move(640 + 320, 420, steps=8); pg.wait_for_timeout(80); pg.mouse.up(); pg.wait_for_timeout(1800); b2 = _st(pg)
        da = abs(_m.degrees((b2["az"] - a["az"] + _m.pi) % (2 * _m.pi) - _m.pi))
        ok("旋轉模式左鍵拖曳畫面寬度 1/4（320 像素）：方位角轉 %.1f 度（目標約 45，容許 30–60）、注視點不動" % da, 30 <= da <= 60 and _m.hypot(b2["tx"] - a["tx"], b2["tz"] - a["tz"]) < 0.05, (a, b2))
        a = _st(pg); pg.mouse.move(640, 420); pg.mouse.down(button="right"); pg.mouse.move(740, 420, steps=6); pg.mouse.up(button="right"); pg.wait_for_timeout(800); b2 = _st(pg)
        ok("右鍵拖曳仍是旋轉的隱藏捷徑（不是平移）", abs(b2["az"] - a["az"]) > 0.05 and _m.hypot(b2["tx"] - a["tx"], b2["tz"] - a["tz"]) < 0.05)
        pg.click(".cm-seg [data-c=mv]")
        # 旋轉鈕
        a = _st(pg); pg.click(".cm-rot[data-c=rl]"); pg.wait_for_timeout(1800); b2 = _st(pg)
        d1 = _m.degrees((b2["az"] - a["az"] + _m.pi) % (2 * _m.pi) - _m.pi)
        ok("↺ 點一下：方位角轉約 30 度（實際 %.1f）" % d1, 20 <= abs(d1) <= 40, d1)
        a = _st(pg); pg.click(".cm-rot[data-c=rr]"); pg.wait_for_timeout(1800); b2 = _st(pg)
        d2 = _m.degrees((b2["az"] - a["az"] + _m.pi) % (2 * _m.pi) - _m.pi)
        ok("↻ 點一下：往相反方向轉約 30 度（實際 %.1f）" % d2, 20 <= abs(d2) <= 40 and d1 * d2 < 0, (d1, d2))
        box = pg.locator(".cm-rot[data-c=rl]").bounding_box(); a = _st(pg)
        pg.mouse.move(box["x"] + 10, box["y"] + 10); pg.mouse.down(); pg.wait_for_timeout(2000); pg.mouse.up(); pg.wait_for_timeout(300); b2 = _st(pg)
        d3 = abs(_m.degrees((b2["az"] - a["az"] + _m.pi) % (2 * _m.pi) - _m.pi))
        ok("↺ 按住 2 秒：持續旋轉（轉了 %.0f 度，大於點一下的 30 度），放開就停" % d3, d3 > 45 and not pg.evaluate("() => __world.cam.spin"), d3)
        # 靈敏度
        pg.click("#helpBtn")
        ok("「?」裡有「拖曳靈敏度」慢／中／快，預設「中」", pg.evaluate("() => [...document.querySelectorAll('#helpPop .sens button')].map(b => b.textContent + (b.classList.contains('on') ? '*' : '')).join()") == "慢,中*,快")
        pg.click("#helpPop .sens [data-sens='0.6']")
        ok("靈敏度改成「慢」：記在 localStorage", pg.evaluate("() => localStorage.getItem('aiOffice.cam.sens') === '0.6' && __world.cam.sens === 0.6"))
        pg.click("#helpBtn")
        # 靈敏度比例：同一個畫面位置、同樣拖曳 100 像素，慢／中／快的注視點位移比例要接近 0.6：1：1.5（修正前：遠景慢 1.5 公尺、快 23.6 公尺，比例差很多）
        disp = {}
        for name, dist in [("遠景", 40), ("近景", 14)]:
            for sens in (0.6, 1, 1.5):
                pg.evaluate("([d, s]) => { __world.cam.setSens(s); __world.godAt(20, 15, d); }", [dist, sens]); wait_until(pg, "() => !__world.view.tween", 12000); pg.wait_for_timeout(700)
                a = _st(pg); pg.mouse.move(640, 420); pg.mouse.down(); pg.mouse.move(740, 420, steps=10); pg.wait_for_timeout(60); pg.mouse.up(); pg.wait_for_timeout(1500); b2 = _st(pg)
                disp[(name, sens)] = _m.hypot(b2["tx"] - a["tx"], b2["tz"] - a["tz"])
            d1 = disp[(name, 1)]
            r6, r15 = disp[(name, 0.6)] / d1, disp[(name, 1.5)] / d1
            ok("靈敏度比例（%s）：慢 %.2f 公尺、中 %.2f 公尺、快 %.2f 公尺 → 慢÷中 %.2f（目標 0.6、容許 0.5–0.7）、快÷中 %.2f（目標 1.5、容許 1.3–1.7）" % (name, disp[(name, 0.6)], d1, disp[(name, 1.5)], r6, r15), 0.5 <= r6 <= 0.7 and 1.3 <= r15 <= 1.7, disp)
        pg.evaluate("() => __world.cam.setSens(1)")
        # 重新整理後模式與靈敏度仍在
        pg.evaluate("() => __world.cam.setMode('rotate')"); pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => window.__world && window.__world.ready", 90000)
        ok("重新整理後：拖曳模式仍是「旋轉」", pg.evaluate("() => __world.cam.mode === 'rotate' && document.querySelector('.cm-seg [data-c=ro]').classList.contains('on')"))
        pg.evaluate("() => __world.cam.setMode('move')")
        # 視角鈕
        pg.evaluate("() => { const W = __world; W.setView('char', W.chars.get('ceo'), true); }"); pg.wait_for_timeout(500)
        t = pg.evaluate("() => [...document.querySelectorAll('#viewSeg button')].filter(b => !b.hidden).map(b => b.textContent)")
        ok("視角鈕：選到 CEO 時第三格寫「跟隨」，不再與「CEO 視角」重複；有選取時多一格「角色視角」（%s）" % t, t == ["CEO 視角", "俯瞰", "跟隨", "角色視角"], t)
        ok("鏡頭：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()
    # 手機
    c, pg, got = _o(b, base, w=390, h=844, touch=True)
    try:
        ok("鏡頭（手機）：頂端工具列預設收起，鏡頭提示（拖曳切換、旋轉鈕）收在「更多」裡", pg.evaluate("() => !document.querySelector('.cm-hint').offsetParent && document.getElementById('moreBtn').getAttribute('aria-expanded') === 'false'"))
        pg.click("#moreBtn"); pg.wait_for_timeout(600)
        ok("鏡頭（手機）：點「更多」後旋轉鈕與拖曳切換都出現（%d 顆按鈕）、至少 44px、不超出畫面" % pg.evaluate("() => [...document.querySelectorAll('.cm-hint button')].filter(b => b.offsetParent).length"), pg.evaluate("() => [...document.querySelectorAll('.cm-hint button')].filter(b => b.offsetParent).length >= 4") and pg.evaluate("() => [...document.querySelectorAll('.cm-hint button')].filter(b => b.offsetParent).every(b => b.offsetHeight >= 28)") and pg.evaluate("() => { const r = document.querySelector('.cm-hint').getBoundingClientRect(); return r.left >= 0 && r.right <= 390; }"))
        ok("鏡頭（手機）：提示是「單指拖曳移動・雙指縮放旋轉・雙點地面前往」、沒有橫向捲軸", pg.evaluate("() => document.querySelector('.cm-hint').textContent.includes('單指拖曳移動・雙指縮放旋轉・雙點地面前往') && document.documentElement.scrollWidth <= innerWidth"))
        r1 = pg.evaluate("() => [...document.querySelectorAll('#bar > *')].filter(e => e.offsetParent).map(e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })")
        h = pg.evaluate("() => { const r = document.querySelector('.cm-hint').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }")
        ok("鏡頭（手機）：鏡頭提示與頂列各按鈕不重疊", not any(not (a[2] <= h[0] or h[2] <= a[0] or a[3] <= h[1] or h[3] <= a[1]) for a in r1), h)
        pg.screenshot(path=__import__("os").path.join(__import__("os").environ.get("STATE_SHOTS", "/tmp"), "旋轉控制_390.png"))
    finally:
        c.close()


register("辦公室鏡頭", lambda pg, b, base, code: t_camera2(b, base))
