# 驗收段落「糰糰第四階段」（AI Office 角色升級第四階段）：抓起與拋出、睡覺、情緒動作、檢查模式、場地面板、資源釋放。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until() 直接可用。
# 兩類驗收：A 真的操作（滑鼠按住身體拖曳、按鈕、面板）並驗畫面／狀態真的改變；B 頁面內固定時間步量測（CH.qa，不依賴軟體繪圖幀率）。
# 注意：這裡只驗「機器量得到的」。可愛度、重量感、轉場自然度要人眼看，見 docs/ai_office/upgrade_plan.md「第四階段結果」的人工美術驗收表。
# flake8: noqa

import hashlib as _hl
import math as _m


def _root(base):
    return base.split("/index.html")[0].rstrip("/")


def _open(b, base, qs="?shot&play=1", vp=None, mobile=False, skip=True):
    kw = dict(viewport=vp or {"width": 1280, "height": 800})
    if mobile:
        kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    c = b.new_context(**kw)
    pg = c.new_page()
    pg.set_default_timeout(120000)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(_root(base) + "/office/char.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => document.documentElement.dataset.ready === '1' && (%s)" % ("!!CH.cc" if "play" in qs else "true"), 90000)
    if got and skip:   # 軟體繪圖一幀要好幾百毫秒：不繪圖，只跑模擬與互動（需要看畫面的段落自己重新繪圖）
        pg.evaluate("() => { CH.S.skipRender = true; }")
    return c, pg, errs, got


def _screen(pg, x, y, z):
    return pg.evaluate("""([x, y, z]) => { const v = new CH.THREE.Vector3(x, y, z).project(CH.camera), r = CH.renderer.domElement.getBoundingClientRect();
      return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height]; }""", [x, y, z])


def _canvas_hash(pg):
    """用 CH.shotPNG（先重新繪圖再取 PNG）取畫面雜湊"""
    return _hl.md5(pg.evaluate("() => CH.shotPNG()").encode()).hexdigest()


def t_s4_panel(b, base):
    # ── A3 場地模式的控制面板：預設收成一條動作列，角色與場地看得到大半，文字不被切
    for nm, vp, mob in (("1280x800", {"width": 1280, "height": 800}, False), ("390x844", {"width": 390, "height": 844}, True)):
        c, pg, errs, got = _open(b, base, "?shot", vp, mob, skip=False)
        try:
            ok("場地面板 %s：頁面載入" % nm, got)
            if not got:
                continue
            if mob:
                pg.click("#btnPanel")   # 手機預設收起面板，先打開
            full = pg.evaluate("() => document.getElementById('panel').getBoundingClientRect().height")
            pg.click("#btnPlay")
            wait_until(pg, "() => !!CH.cc && document.body.classList.contains('play')", 60000)
            pg.wait_for_timeout(600)
            r = pg.evaluate("""() => { const p = document.getElementById('panel').getBoundingClientRect(), W = innerWidth, H = innerHeight;
              const vis = [...document.querySelectorAll('#panel button, #panel select')].filter(b => b.offsetParent);
              const cut = vis.filter(b => { const r = b.getBoundingClientRect(); return r.right > W + 0.5 || r.left < -0.5 || r.bottom > H + 0.5 || b.scrollWidth > b.clientWidth + 1; }).map(b => b.textContent);
              const groups = [...document.querySelectorAll('#panel > .grp')].filter(g => g.offsetParent).map(g => g.id || g.textContent.slice(0, 4));
              const ch = CH.cc.ch.root.position.clone().add(new CH.THREE.Vector3(0, 0.3, 0)).project(CH.camera), cy = (1 - ch.y) / 2 * H;
              return { top: p.top, h: p.height, bottom: p.bottom, H, W, n: vis.length, cut, groups, charY: cy, hint: getComputedStyle(document.getElementById('playHint')).display }; }""")
            ok("★ 場地面板 %s：預設只剩場地動作列（不再是整面板）" % nm, r["groups"] == ["grpPlay"] and r["hint"] == "none" and r["h"] < full * 0.6, [r, full])
            ok("★ 場地面板 %s：高度 < 螢幕 22%%，角色中心在面板上方（沒被擋住）" % nm, r["h"] < r["H"] * 0.22 and r["charY"] < r["top"] - 20, r)
            ok("★ 場地面板 %s：所有按鈕文字完整在畫面內、沒被切" % nm, r["cut"] == [] and r["n"] >= 10 and r["bottom"] <= r["H"] + 0.5, r)
            # 「更多選項」展開後，視角／表情／材質等群組才出現；再按一次收回
            pg.click("#btnMore")
            r2 = pg.evaluate("() => ({ groups: [...document.querySelectorAll('#panel > .grp')].filter(g => g.offsetParent).length, h: document.getElementById('panel').getBoundingClientRect().height, maxH: innerHeight * 0.46 + 2, hint: getComputedStyle(document.getElementById('playHint')).display })")
            ok("更多選項：展開後群組變多、仍在螢幕內（捲動不切字）、說明列出現", r2["groups"] >= 5 and r2["h"] <= r2["maxH"] and r2["hint"] != "none", r2)
            pg.click("#btnMore")
            ok("更多選項：再按一次收回精簡列", pg.evaluate("() => [...document.querySelectorAll('#panel > .grp')].filter(g => g.offsetParent).length") == 1)
            ok("場地面板 %s：無頁面例外" % nm, not errs, errs[:3])
        finally:
            c.close()


def t_s4_grab(b, base):
    c, pg, errs, got = _open(b, base)
    try:
        ok("抓起與拋出：載入完成", got)
        if not got:
            return
        pg.click("#btnPanel")
        pg.evaluate("() => { CH.cc.life = false; CH.cc.ch.face.autoBlink = false; CH.S.noFollow = true; CH.cc.reset(0, 0.9, 0); }")
        pg.wait_for_timeout(400)
        # ── 按住身體不動 → 不抓起（頭才是摸頭）
        bx, by = _screen(pg, 0.0, 0.25, 0.9)
        pg.mouse.move(bx, by)
        pg.mouse.down()
        pg.wait_for_timeout(250)
        st = pg.evaluate("() => CH.cc.state")
        pg.mouse.up()
        ok("按住身體不拖：不會抓起（狀態不是 held）", st != "held", st)
        # ── 按住身體拖曳 → 抓起：離地、抓點跟著指標、身體有懸吊擺盪
        wait_until(pg, "() => CH.cc.state === 'idle'", 5000)
        bx, by = _screen(pg, 0.0, 0.25, 0.9)
        y0 = pg.evaluate("() => CH.cc.body.y")
        pg.mouse.move(bx, by)
        pg.mouse.down()
        for i in range(1, 13):
            pg.mouse.move(bx, by - i * 14)
            pg.wait_for_timeout(25)
        held = wait_until(pg, "() => CH.cc.state === 'held'", 4000)
        ok("★ 按住身體拖曳：進入 held 狀態", held, pg.evaluate("() => CH.cc.info()"))
        wait_until(pg, "() => CH.cc.body.y > 0.3", 4000)
        y1 = pg.evaluate("() => CH.cc.body.y")
        ok("★ 拖曳：身體真的被拉離地面（高度 %.2f → %.2f）" % (y0, y1), y1 > y0 + 0.25, [y0, y1])
        pg.evaluate("() => { window.__hmax = 0; window.__hiv = setInterval(() => { window.__hmax = Math.max(window.__hmax, Math.abs(CH.cc.hang.x), Math.abs(CH.cc.hang.z)); }, 10); }")
        for i in range(0, 16):   # 左右甩動，讓擺產生振幅
            pg.mouse.move(bx + (110 if i % 2 == 0 else -110), by - 170)
            pg.wait_for_timeout(70)
        sw = pg.evaluate("() => { clearInterval(window.__hiv); return window.__hmax; }")
        ok("★ 左右甩動：身體懸吊擺盪（甩動期間最大擺角 > 0.1 rad）", sw > 0.1, sw)
        # ── 甩出去：放手時給初速度（有上限）
        for i in range(0, 8):
            pg.mouse.move(bx + 40 * i, by - 170 - 6 * i)
            pg.wait_for_timeout(8)
        pg.mouse.up()
        rel = pg.evaluate("() => CH.S.lastRelease")
        ok("★ 放手：依指標速度給初速度（> 0.5 m/s）且不超過上限 12 m/s", rel and 0.5 < rel["speed"] <= 12.001, rel)
        ok("放手後離開 held（tumble 或 air）", pg.evaluate("() => ['tumble','air'].includes(CH.cc.state)"), pg.evaluate("() => CH.cc.state"))
        # 飛行中每一幀都要有限、速度不失控、之後落地並自己回待機
        bad = pg.evaluate("""async () => { let bad = 0, vmax = 0; const t0 = performance.now(); while (performance.now() - t0 < 9000 && !(CH.cc.state === 'idle' && CH.cc.stateT > 0.3)) { const b = CH.cc.body; if (![b.x, b.y, b.z, b.vx, b.vy, b.vz].every(Number.isFinite)) bad++; vmax = Math.max(vmax, Math.hypot(b.vx, b.vy, b.vz)); await new Promise(r => setTimeout(r, 30)); } return { bad, vmax, state: CH.cc.state }; }""")
        ok("★ 拋出後：全程有限值、速度 ≤ 14 m/s、落地後自己回到待機", bad["bad"] == 0 and bad["vmax"] < 14 and bad["state"] == "idle", bad)
        ok("拋出後位置在場地內（沒穿出邊界）", pg.evaluate("() => Math.abs(CH.cc.body.x) <= 2.3 && Math.abs(CH.cc.body.z) <= 2.3 && CH.cc.body.y >= 0"))
        # ── 摸頭仍可用：按住頭頂不動
        pg.evaluate("() => CH.cc.reset(0, 0.9, 0)")
        pg.wait_for_timeout(300)
        hx, hy = _screen(pg, 0.0, 0.62, 0.9)
        pg.mouse.move(hx, hy)
        pg.mouse.down()
        petted = wait_until(pg, "() => CH.cc.pet.on", 3000)
        pg.mouse.up()
        ok("按住頭頂不動：仍是摸頭（pet.on）", petted)
        ok("頁面無例外", not errs, errs[:3])
    finally:
        c.close()


def t_s4_qa(b, base):
    c, pg, errs, got = _open(b, base, "?shot&play=1&qa=1")
    try:
        ok("檢查模式：?qa=1 載入、面板展開", got and pg.evaluate("() => !CH.qaPanel.hidden"))
        if not got:
            return
        pg.evaluate("() => { CH.cc.life = false; CH.cc.ch.face.autoBlink = false; CH.S.noFollow = true; CH.cc.reset(0, 0.9, 0); }")
        pg.click("#btnPanel")
        # 鏡頭：正面／側面／背面／45 度（相機方位真的改變）
        az = {}
        for k, nm in (("front", "正面"), ("side", "側面"), ("back", "背面"), ("q45", "45 度")):
            pg.click("#qv_" + k)
            wait_until(pg, "() => !CH.S.tween", 20000, 100)
            az[k] = pg.evaluate("() => { const p = CH.camera.position, t = CH.ctl.target; return Math.atan2(p.x - t.x, p.z - t.z); }")
        ok("★ 檢查模式四個鏡頭：方位角真的不同（正面≈0、側面≈90°、背面≈180°、45°）", abs(az["front"]) < 0.1 and abs(az["side"] - _m.pi / 2) < 0.1 and abs(abs(az["back"]) - _m.pi) < 0.1 and abs(az["q45"] - _m.pi / 4) < 0.1, az)
        pg.click("#qv_front")
        wait_until(pg, "() => !CH.S.tween", 20000, 100)
        pg.evaluate("() => { CH.S.paused = true; CH.cc.reset(0, 0.9, 0); CH.cc.update(0.2); }")
        pg.wait_for_timeout(300)
        h0 = _canvas_hash(pg)
        # 碰撞形狀：畫面真的多了線條；再按一次消失
        pg.click("#qCollide")
        ok("碰撞形狀：QAView 顯示且畫面改變", pg.evaluate("() => CH.qav && CH.qav.group.visible && CH.qav.collide") and (pg.evaluate("() => CH.qav.update(CH.cc)") or True) and _canvas_hash(pg) != h0)
        pg.click("#qContacts")
        pg.evaluate("() => CH.qav.update(CH.cc)")
        info = pg.evaluate("() => ({ feet: CH.qav.feetDots.map(d => d.visible), low: CH.qav.low.position.y, ring: CH.qav.ring.visible })")
        ok("接觸點與接地：兩個腳點、最低點、接地圈都存在，最低點貼地", all(info["feet"]) and abs(info["low"]) < 0.02 and info["ring"], info)
        pg.click("#qCollide")
        pg.click("#qContacts")
        ok("再按一次：疊加物全部隱藏、畫面回到原樣", (not pg.evaluate("() => CH.qav.group.visible")) and _canvas_hash(pg) == h0)
        # 法線／線框：覆蓋材質真的換掉，畫面改變；再按還原
        pg.click("#qNorm")
        ok("法線檢視：覆蓋材質為 MeshNormalMaterial、畫面改變", pg.evaluate("() => CH.scene.overrideMaterial && CH.scene.overrideMaterial.type") == "MeshNormalMaterial" and _canvas_hash(pg) != h0)
        pg.click("#qWire")
        ok("線框：覆蓋材質為 wireframe（與法線互斥）", pg.evaluate("() => CH.scene.overrideMaterial && CH.scene.overrideMaterial.wireframe === true && !CH.S.norm"))
        pg.click("#qWire")
        ok("關掉線框：回到原畫面", pg.evaluate("() => !CH.scene.overrideMaterial") and _canvas_hash(pg) == h0)
        # 狀態與速度、接地偵測：跳起來時文字「空中」、落地後「接地」
        pg.click("#qInfo")
        pg.evaluate("() => { CH.S.paused = false; }")
        pg.evaluate("() => CH.cc.jump()")
        air = wait_until(pg, "() => !CH.cc.body.grounded && document.getElementById('qTxt').textContent.includes('空中')", 8000, 60)
        ok("★ 接地偵測顯示：跳起來時文字出現「否（空中）」", air, pg.evaluate("() => document.getElementById('qTxt').textContent"))
        gnd = wait_until(pg, "() => CH.cc.body.grounded && document.getElementById('qTxt').textContent.includes('是（接地）')", 10000, 80)
        ok("落地後文字回到「是（接地）」並顯示狀態與速度", gnd and "速度" in pg.evaluate("() => document.getElementById('qTxt').textContent"))
        # 播放速度、暫停、逐格：量模擬時間 / 牆鐘時間
        wait_until(pg, "() => CH.cc.state === 'idle'", 8000)
        def sim_rate(ms):
            t0 = pg.evaluate("() => CH.cc.time"); pg.wait_for_timeout(ms); t1 = pg.evaluate("() => CH.cc.time"); return (t1 - t0) / (ms / 1000)
        r1 = sim_rate(1500)
        pg.click("#qs_0.25")
        r025 = sim_rate(1500)
        pg.click("#qs_0.5")
        r05 = sim_rate(1500)
        ok("★ 播放速度：1× / 0.5× / 0.25× 的模擬進度比約為 1 : 0.5 : 0.25", 0.8 < r1 < 1.2 and 0.38 < r05 / r1 < 0.62 and 0.17 < r025 / r1 < 0.33, [r1, r05, r025])
        pg.click("#qs_1")
        pg.click("#qPause")
        t0 = pg.evaluate("() => CH.cc.time")
        pg.wait_for_timeout(800)
        t1 = pg.evaluate("() => CH.cc.time")
        ok("★ 暫停：模擬時間完全停住", t1 == t0 and pg.evaluate("() => CH.S.paused"), [t0, t1])
        for _ in range(6):
            pg.click("#qStep")
        pg.wait_for_timeout(500)
        t2 = pg.evaluate("() => CH.cc.time")
        ok("★ 逐格 ×6：模擬時間前進約 6/60 秒（0.10 ± 0.01）且仍是暫停", abs((t2 - t1) - 0.1) < 0.011 and pg.evaluate("() => CH.S.paused"), [t1, t2])
        pg.click("#qPause")
        ok("繼續：模擬時間再度前進", wait_until(pg, "() => CH.cc.time > %f" % (t2 + 0.2), 5000))
        # 各動作單獨播放：每顆鈕真的讓角色進入對應狀態
        want = {"walk": ("walk", "run"), "run": ("run", "walk"), "jump": ("jumpPrep", "air"), "sit": ("sit",), "sleep": ("sleep",), "grab": ("held",), "throw": ("tumble", "air")}
        for k, states in want.items():
            pg.click("#qa_" + k)
            okk = wait_until(pg, "() => %s.includes(CH.cc.state)" % list(states), 6000, 40)
            ok("各動作單獨播放：「%s」鈕 → 狀態進入 %s" % (k, "/".join(states)), okk, pg.evaluate("() => CH.cc.state"))
        for k in ("hit", "happy", "angry", "sad"):
            pg.click("#qa_" + k)
            okk = wait_until(pg, "() => !!CH.cc.overlay && CH.cc.overlay.name === '%s'" % k, 6000, 40)
            ok("各動作單獨播放：「%s」鈕 → 覆蓋動作開始" % k, okk, pg.evaluate("() => CH.cc.info()"))
        # 截圖輸出：真的是 PNG，兩個不同狀態的畫面不同
        a = pg.evaluate("() => CH.shotPNG()")
        pg.click("#qa_sleep")
        wait_until(pg, "() => CH.cc.state === 'sleep' && CH.cc.stateT > 1.5", 8000, 60)
        b2 = pg.evaluate("() => CH.shotPNG()")
        ok("★ 截圖輸出：PNG 資料有效、不同狀態的截圖不同", a.startswith("data:image/png;base64,") and len(a) > 5000 and a != b2, [len(a), len(b2)])
        # 新舊對照：離開場地模式並開啟並排
        pg.click("#qCmp")
        ok("新舊對照：進入並排（S.cmp）並離開場地模式", wait_until(pg, "() => CH.S.cmp === true && CH.S.play === false", 8000))
        ok("頁面無例外", not errs, errs[:3])
    finally:
        c.close()


def t_s4_sim(b, base):
    c, pg, errs, got = _open(b, base)
    try:
        ok("第四階段量測：頁面載入", got)
        if not got:
            return
        ev = lambda e: pg.evaluate("async () => { const qa = CH.qa; return await (" + e + "); }")
        # ── 靜止不穿地
        r = ev("(() => { const c = qa.prepare({x: 0.4, z: 0.7}); let mn = 1e9, drift = 0; qa.run(c, 60, 10, null, () => { mn = Math.min(mn, c.lowestBody(true) - c.body.supportY); drift = Math.max(drift, Math.abs(c.body.y)); }); return { mn, drift, finite: qa.finite(c) }; })()")
        ok("★ 靜止 10 秒：身體最低點不低於地面 5 mm、高度不漂移", r["mn"] > -0.005 and r["drift"] < 1e-6 and r["finite"], r)
        # ── 跳後正常落地
        r = ev("(() => { const c = qa.prepare({x: 0, z: 0.5}); c.jump(); const seq = []; let peakSq = 0, apex = 0; qa.run(c, 60, 3, null, () => { if (seq[seq.length - 1] !== c.state) seq.push(c.state); apex = Math.max(apex, c.body.y); peakSq = Math.max(peakSq, c.ch.wm.land || 0); }); qa.run(c, 60, 3); return { seq, apex, peakSq, y: c.body.y, state: c.state, rd: qa.restDiff(c) }; })()")
        ok("★ 跳後落地：狀態依序 jumpPrep→air→land→idle、頂點約 0.62 m、落地壓縮 > 0.1、最後貼地回待機", r["seq"][:4] == ["jumpPrep", "air", "land", "idle"] and abs(r["apex"] - 0.62) < 0.03 and r["peakSq"] > 0.1 and r["y"] == 0 and r["rd"]["worstQ"] < 1e-3 and r["rd"]["worstM"] < 1e-3, r)
        # ── 每個動作結束回到正確姿勢
        for n in ("hit", "happy", "angry", "sad"):
            r = ev("qa.emoSegs('%s')" % n)
            ok("★ %s：五段（起始、預備、主動作、緩衝、回待機）定義齊全、實際依序經過，結束後骨頭與形態鍵回靜止" % n,
               r["defined"][0] == "start" and r["defined"][1] == "pre" and r["defined"][-2:] == ["settle", "out"] and "main" in r["defined"]
               and r["seen"][0] == "pre" and r["seen"][-2:] == ["settle", "out"] and "main" in r["seen"] and r["state"] == "idle" and not r["overlay"]
               and r["worstQ"] < 1e-3 and r["worstM"] < 1e-3 and r["finite"], r)
            ok("%s：個性「慢半拍」——%s" % (n, "受擊是反射（延遲 < 0.15 s）" if n == "hit" else "先歪頭好奇再反應（延遲 0.2～0.6 s）"),
               (r["delay"] < 0.15) if n == "hit" else (0.2 < r["delay"] < 0.6), r["delay"])
        r = ev("qa.sleepInfo(60)")
        ok("★ 睡覺：躺下（squash ≥ 0.4）、睡眼表情、呼吸比待機慢 1.5 倍以上", r["squash"] >= 0.4 and r["face"] == "sleep" and r["ratio"] > 1.5, r)
        ok("★ 睡覺：Zzz 冒出來（≥1 個），叫醒後起身回待機、Zzz 全部消失、骨頭回靜止", r["zmax"] >= 1 and r["zAfter"] == 0 and r["wakeState"] == "idle" and r["worstQ"] < 1e-3 and r["worstM"] < 1e-3, r)
        # ── 坐下符合接觸點（回歸）
        r = ev("qa.sitContact(60)")
        ok("★ 坐下：臀部與凳面距離 < 1 cm、接觸點在座面內、朝向正確", abs(r["gapBody"]) < 0.01 and r["lowestInSeat"] and r["yawErr"] < 0.05 and r["sub"] == "seated", r)
        # ── 拋擲：多組隨機初速度
        for seed, fps in ((11, 60), (23, 30), (5, 144)):
            r = ev("qa.throwStorm(40, %d, %d)" % (seed, fps))
            ok("★ 隨機拋擲 40 組（種子 %d、%d fps）：無非有限值、速度 ≤ 14 m/s、彈跳 ≤ 8 次、都在 10 秒內停下回待機" % (seed, fps),
               r["nonFinite"] == 0 and r["maxSpeed"] <= 14 and r["maxBounces"] <= 8 and r["notIdle"] == 0 and r["maxSettle"] < 10 and r["conflicts"] == 0, r)
            ok("拋擲（種子 %d、%d fps）：蒙皮後最低點不低於地面 5 mm、不嵌進箱子／凳子 3 cm 以上、含 NaN 速度的組合也安全" % (seed, fps),
               r["minBelow"] > -0.005 and r["maxPen"] < 0.03 and r["nanCases"] >= 1 and r["endStates"].get("idle") == r["n"], r)
        r = ev("qa.heldDrift(60, 0.6)")
        ok("★ 抓起懸吊：擺盪振幅 > 0.3 rad，抓點在擺盪中漂移 < 6 cm（含頭部傾斜的姿勢偏移），放手回待機", r["maxSwing"] > 0.3 and r["spread"] < 0.06 and r["released"] and r["endState"] == "idle" and r["finite"], r)
        r = ev("qa.switchSeq(60)")
        ok("★ 動作連續切換 20 次：位置只被物理推動（單幀位移超出速度預算 < 5 cm）、無通道衝突、回到待機", r["maxJumpOver"] < 0.05 and r["conflicts"] == 0 and r["state"] == "idle" and r["finite"], r)
        ok("頁面無例外", not errs, errs[:3])
    finally:
        c.close()


def t_s4_res(b, base):
    c, pg, errs, got = _open(b, base)
    try:
        ok("資源釋放：頁面載入", got)
        if not got:
            return
        r = pg.evaluate("async () => await CH.qa.reloadCycle(9)")
        rows = r["rows"]
        key = lambda x: (x["geo"], x["tex"], x["programs"], x["meshes"], x["lights"])
        ok("★ 連續重建角色 9 次（輪流切 LOD0／1／2）：同一細緻度第 2、3 輪的 幾何／貼圖／著色器／場景物件數 不再增加",
           key(rows[3]) == key(rows[6]) and key(rows[4]) == key(rows[7]) and key(rows[5]) == key(rows[8]), [(x["lod"], key(x)) for x in rows])
        ok("★ 重建後：舊角色已從場景移除、控制器指向新角色、動畫狀態乾淨（idle、無覆蓋動作、無待反應、無抓取）",
           r["detached"] and r["ctlOk"] and r["state"] == "idle" and not r["overlay"] and not r["pend"] and not r["held"] and r["intent"] == 0, r)
        # 用介面切細緻度（下拉選單）也一樣
        pg.click("#btnMore")   # 場地模式下細緻度選單收在「更多選項」裡
        pg.select_option("#selLod", "1")
        wait_until(pg, "() => CH.S.lod === 1 && CH.cc && CH.cc.ch === CH.S.ch", 20000)
        a = pg.evaluate("() => CH.qa.resources()")
        pg.select_option("#selLod", "0")
        wait_until(pg, "() => CH.S.lod === 0 && CH.cc && CH.cc.ch === CH.S.ch", 20000)
        pg.select_option("#selLod", "1")
        wait_until(pg, "() => CH.S.lod === 1 && CH.cc && CH.cc.ch === CH.S.ch", 20000)
        a2 = pg.evaluate("() => CH.qa.resources()")
        pg.click("#btnMore")
        ok("用下拉選單切細緻度 1→0→1：資源數量回到原值", (a["geo"], a["tex"], a["meshes"]) == (a2["geo"], a2["tex"], a2["meshes"]), [a, a2])
        # 檢查模式疊加物反覆開關：不累積資源
        pg.evaluate("() => { CH.ensureQav().setCollide(true); CH.ensureQav().setContacts(true); CH.qav.update(CH.cc); }")
        b1 = pg.evaluate("() => CH.qa.resources()")
        for _ in range(5):
            pg.evaluate("() => { CH.qav.setCollide(false); CH.qav.setContacts(false); CH.qav.setCollide(true); CH.qav.setContacts(true); CH.qav.update(CH.cc); }")
        b2 = pg.evaluate("() => CH.qa.resources()")
        ok("檢查模式疊加物開關 5 次：資源數量不變", (b1["geo"], b1["tex"], b1["meshes"]) == (b2["geo"], b2["tex"], b2["meshes"]), [b1, b2])
        ok("頁面無例外", not errs, errs[:3])
    finally:
        c.close()


register("糰糰第四階段-面板", lambda pg, b, base, code: t_s4_panel(b, base))
register("糰糰第四階段-抓起拋出", lambda pg, b, base, code: t_s4_grab(b, base))
register("糰糰第四階段-檢查模式", lambda pg, b, base, code: t_s4_qa(b, base))
register("糰糰第四階段-量測", lambda pg, b, base, code: t_s4_sim(b, base))
register("糰糰第四階段-資源", lambda pg, b, base, code: t_s4_res(b, base))
