# 驗收段落「糰糰控制器」（AI Office 角色升級第三階段）：site/office/char.html 的走動小場地、動畫控制器、物理。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until() 直接可用。
# 兩類驗收：A 真的操作（點地面、按鈕、摸頭）並驗畫面／狀態真的改變；B 頁面內固定時間步量測（CH.qa，不依賴軟體繪圖幀率）。
# flake8: noqa

import math as _m


def _root(base):
    return base.split("/index.html")[0].rstrip("/")


def _open(b, base, qs="?shot&play=1"):
    c = b.new_context(viewport={"width": 800, "height": 600})
    pg = c.new_page()
    pg.set_default_timeout(120000)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(_root(base) + "/office/char.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => document.documentElement.dataset.ready === '1' && !!CH.cc", 90000)
    pg.add_style_tag(content="#stat{display:none !important}")
    if got:   # 軟體繪圖很慢：陰影貼圖縮小，讓點擊與等待不被繪圖拖住（不影響控制器行為）
        pg.evaluate("() => { CH.S.skipRender = true; }")
    return c, pg, errs, got


def _btn(pg, sel):
    """面板收起後按鈕不可見：直接送出 DOM click（與使用者按下同一個 click 事件處理）"""
    pg.evaluate("(s) => document.querySelector(s).click()", sel)


def _screen(pg, x, y, z):
    return pg.evaluate("""([x, y, z]) => { const v = new CH.THREE.Vector3(x, y, z).project(CH.camera), r = CH.renderer.domElement.getBoundingClientRect();
      return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height]; }""", [x, y, z])


def t_ctl(b, base):
    c, pg, errs, got = _open(b, base)
    try:
        ok("糰糰控制器：?play=1 載入完成、控制器就緒", got)
        if not got:
            return
        ok("開發面板預設收起", pg.evaluate("() => document.getElementById('dev').hidden"))
        pg.click("#btnDev")
        ok("開發面板可展開並顯示狀態文字", wait_until(pg, "() => !document.getElementById('dev').hidden && document.getElementById('devTxt').textContent.includes('狀態')", 8000))
        pg.click("#btnDev")
        pg.click("#btnPanel")   # 收起面板，讓畫面中央露出場地
        # ── A1 點地面走過去：位置真的變、到了停下回 Idle
        pg.evaluate("() => { CH.cc.reset(0, 1.2, 0); }")
        x0 = pg.evaluate("() => [CH.cc.body.x, CH.cc.body.z]")
        sx, sy = _screen(pg, -0.9, 0, 0.8)
        pg.mouse.click(sx, sy)
        walked = wait_until(pg, "() => CH.cc.state === 'walk' || CH.cc.state === 'run'", 15000)
        ok("點地面：角色進入走路狀態", walked, pg.evaluate("() => CH.cc.info()"))
        arrived = wait_until(pg, "() => CH.cc.state === 'idle' && Math.hypot(CH.cc.body.x + 0.9, CH.cc.body.z - 0.8) < 0.15", 40000)
        x1 = pg.evaluate("() => [CH.cc.body.x, CH.cc.body.z]")
        ok("點地面：位置真的變了、停在目標附近並回到 Idle", arrived and _m.hypot(x1[0] - x0[0], x1[1] - x0[1]) > 0.8, [x0, x1])
        # ── A2 跳：離地後回到地面
        _btn(pg, "#btnJump")
        up = wait_until(pg, "() => !CH.cc.body.grounded", 6000, 40)
        ok("按跳：離開地面", up)
        back = wait_until(pg, "() => CH.cc.body.grounded && CH.cc.body.y < 0.001 && CH.cc.state !== 'air'", 15000)
        ok("跳躍後回到地面（高度 0、著地）", back, pg.evaluate("() => CH.cc.info()"))
        wait_until(pg, "() => CH.cc.state === 'idle'", 15000)
        # ── A3 坐下／起身
        _btn(pg, "#btnSit")
        seated = wait_until(pg, "() => CH.cc.state === 'sit' && CH.cc.sit && CH.cc.sit.sub === 'seated'", 90000, 300)
        ok("按坐下：走到凳子前、轉身、跳上去，最後狀態為 Sit（seated）", seated, pg.evaluate("() => CH.cc.info()"))
        gap = pg.evaluate("() => { const c = CH.cc; return c.lowestBody(false) - c.world.box('stool').y1; }")
        ok("坐著時臀部（身體最低點）與凳面距離 < 1 cm", seated and abs(gap) < 0.01, gap)
        _btn(pg, "#btnSit")
        rose = wait_until(pg, "() => CH.cc.state === 'idle' && CH.cc.body.y < 0.001", 40000, 300)
        ok("再按一次：起身並回到 Idle、站回地面", rose, pg.evaluate("() => CH.cc.info()"))
        # ── A4 摸頭：按住頭頂 → 表情改變；放開 → 表情恢復
        pg.evaluate("() => { CH.cc.reset(0, 0.4, 0); CH.cc.life = false; }")
        pg.wait_for_timeout(600)
        hx, hy = _screen(pg, 0, 0.66, 0.0)
        e0 = pg.evaluate("() => CH.cc.expr")
        pg.mouse.move(hx, hy)
        pg.mouse.down()
        petted = wait_until(pg, "() => CH.cc.pet.on && CH.cc.expr === 'bliss'", 15000)
        ok("按住頭頂：進入摸頭、表情改成 bliss（瞇眼開心）", petted, [e0, pg.evaluate("() => CH.cc.info()")])
        pg.mouse.up()
        back = wait_until(pg, "() => !CH.cc.pet.want && CH.cc.expr === 'neutral' && Math.abs(CH.cc.pet.p) < 0.02", 20000)
        ok("放開後表情與姿態恢復", back, pg.evaluate("() => CH.cc.info()"))
        # ── A5 原功能不壞：關掉場地模式後，揮手示範與新舊並排仍可用
        _btn(pg, "#btnPlay")
        ok("場地模式可關閉", wait_until(pg, "() => !CH.S.play", 5000))
        pg.click("#btnPanel")
        _btn(pg, "[data-a=wave]")
        ok("關閉場地後原本的揮手示範仍會動", wait_until(pg, "() => CH.S.act && CH.S.act.name === 'wave'", 5000))
        ok("頁面無例外", not errs, errs[:3])
    finally:
        c.close()


def t_ctl_qa(b, base):
    c, pg, errs, got = _open(b, base, "?play=1")
    try:
        if not got:
            ok("糰糰控制器量測：頁面載入", False)
            return
        ev = lambda e: pg.evaluate("() => { const qa = CH.qa; return " + e + "; }")
        ap = [ev("qa.jumpApex(%d)" % f) for f in (20, 30, 60, 144)]
        h = [a["maxPhys"] for a in ap]
        ok("★ 跳躍頂點高度在 20／30／60／144 fps 下差異 < 2%", (max(h) - min(h)) / max(h) < 0.02, h)
        ok("跳躍頂點接近設定高度（±3%）", all(abs(x - ap[0]["expected"]) / ap[0]["expected"] < 0.03 for x in h), [h, ap[0]["expected"]])
        for kind in ("walk", "run"):
            for fps in (30, 60, 144):
                r = ev("qa.footLock('%s', %d, 0)" % (kind, fps))
                ok("★ %s %dfps：腳著地期間世界位移 < 5 mm、腿長變化 < 1.15 倍" % (kind, fps), r["maxSlide"] < 0.005 and r["ratioMax"] < 1.15 and r["intervals"] > 15, r)
            r = ev("qa.footLock('%s', 60, 1)" % kind)
            ok("%s 弧線轉彎：腳不滑、腿長 < 1.15" % kind, r["maxSlide"] < 0.005 and r["ratioMax"] < 1.15, r)
            r = ev("qa.strideTest('%s', 30)" % kind)
            ok("★ %s：速度與 步頻×步幅 誤差 < 5%%（由實際落腳點量）" % kind, r["errMax"] < 0.05 and r["n"] > 10, r)
        for n in ("idle", "walk", "run", "jump", "runjump", "sit", "sleep", "pet", "overlays", "throw"):
            r = ev("qa.lowest('%s')" % n)
            ok("★ %s 全程最低點不低於地面（容許 5 mm）" % n, r["min"] > -0.005 and r["finite"] and r["badFrames"] == 0 and r["conflicts"] == 0, r)
        for n in ("walk", "run", "jumpPrep", "air", "land", "sit", "sleep", "held", "tumble", "recover", "hit", "happy", "angry", "sad", "pet"):
            r = ev("qa.interruptFrom('%s')" % n)
            ok("★ %s 打斷後回 Idle：骨頭與形態鍵回靜止（< 1e-3）、位置不瞬移" % n, r["state"] == "idle" and r["worstQ"] < 1e-3 and r["worstP"] < 1e-3 and r["worstM"] < 1e-3 and r["maxStep"] < 0.3 and r["conflicts"] == 0, r)
        for seed, fps in ((7, 60), (99, 30)):
            r = ev("qa.storm(500, %d, %d)" % (seed, fps))
            ok("★ 隨機切換 500 次（種子 %d、%d fps）：無 NaN、無通道衝突、無卡住，最後回到 Idle" % (seed, fps), r["bad"] == 0 and r["conflicts"] == 0 and r["endState"] == "idle" and r["maxStateT"] < 8 and r["worstQ"] < 1e-2, r)
        r = ev("qa.sitContact(60)")
        ok("★ 坐下：臀部接觸點與凳面距離 < 1 cm、接觸點在座面範圍內、朝向正確", abs(r["gapBody"]) < 0.01 and r["lowestInSeat"] and r["yawErr"] < 0.05 and r["sub"] == "seated", r)
        ok("坐下後可起身回 Idle", r["afterRise"] in ("idle", "land") and r["afterY"] < 0.001, r)
        ok("頁面無例外", not errs, errs[:3])
    finally:
        c.close()


register("糰糰控制器", lambda pg, b, base, code: t_ctl(b, base))
register("糰糰控制器量測", lambda pg, b, base, code: t_ctl_qa(b, base))
