# 辦公室：遠距離點得到員工、指向外框、拎著拖曳跟地面投影＋邊緣平移、佈告欄照回報進度格式（2026-11-16 擁有者四則回饋）
#   1.「我這樣距離抓不到員工」→ 點選判定改成每次自己把「腳底→頭頂」投影成螢幕線段，最小命中圓 22 像素（觸控 30），不再依賴名牌（名牌在 17 公尺外會隱藏）
#   2.「游標移動到員工身上，他周圍會有一層明顯的線條」→ outline.js：只對被指向的那一位蓋橘色反面放大殼，移開就拆掉
#   3.「拖著員工移動時，竟會依據我滑鼠在螢幕的方向進行移動」→ 拎起時暫停鏡頭跟隨（根因：跟隨鏡頭＋游標投影點互相追）；
#      游標靠邊 40 像素鏡頭自動平移；拎著滾輪仍可縮放
#   4.「佈告欄應該 Follow 回報進度格式顯示」→ ✅🔄🛠️⚠️⬜、花多久／完成時間／做到哪／預估還要／預計開始／卡在誰
#   這一段用真滑鼠與真觸控（Playwright 的 mouse／touchscreen），量：外框殼物件數與畫面橘色像素變化、拎著時員工位置與游標投影點的差、鏡頭平移量。
#   由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

import io as _io
from PIL import Image as _Im


def _pk_orange(png):
    im = _Im.open(_io.BytesIO(png)).convert("RGB")
    d = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
    return sum(1 for r, g, b in d if r > 225 and 95 < g < 185 and b < 95 and r - b > 150)


_PK_JS = """() => { if (window.__pk) return 1; const W = __world, cv = document.getElementById('cv'); const P = window.__pk = {};
  P.ctr = id => { const c = W.chars.get(id), r = cv.getBoundingClientRect(), p = c.object3D.position, v = new W.THREE.Vector3(p.x, p.y + (c.lift || 0) + c.height * 0.5, p.z).project(W.camera); return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height, c.height]; };
  P.dist = d => { W.setView('god', null, true); const t = W.controls.target, off = W.camera.position.clone().sub(t).normalize(); W.camera.position.copy(t).addScaledVector(off, d); W.camera.lookAt(t); W.controls.update(); W.camera.updateMatrixWorld(); return W.camera.position.distanceTo(t); };
  P.plane = (cx, cy, y) => { const r = cv.getBoundingClientRect(), ray = new W.THREE.Raycaster(), ndc = new W.THREE.Vector2((cx - r.left) / r.width * 2 - 1, -(cy - r.top) / r.height * 2 + 1); ray.setFromCamera(ndc, W.camera); const hp = new W.THREE.Vector3(); return ray.ray.intersectPlane(new W.THREE.Plane(new W.THREE.Vector3(0, 1, 0), -y), hp) ? [hp.x, hp.z] : null; };
  P.pos = id => { const p = W.chars.get(id).object3D.position; return [p.x, p.z]; };
  P.tgt = () => { const t = W.controls.target; return [t.x, t.z]; };
  P.freeze = () => { W.speed = 0.001; };
  P.pick = () => { const o = W.outline; return { n: o.hulls.length, who: o.target && o.target.spec.id }; };
  return 1; }"""


def t_office_pick(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    errs = []
    out = {}

    def mk(vw, vh, touch=False):
        c = b.new_context(viewport={"width": vw, "height": vh}, has_touch=touch, is_mobile=touch)
        c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.removeItem('aiOffice.hr.v1')}catch(e){}")
        pg = c.new_page()
        pg.set_default_timeout(120000)
        pg.on("pageerror", lambda e: errs.append("pageerror:" + str(e)[:200]))
        pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
        return c, pg

    def load(pg):
        pg.goto(root + "/office/world.html?ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
        okk = wait_until(pg, "() => window.__world && window.__world.ready", 120000)
        if okk:
            pg.wait_for_timeout(600)
            pg.evaluate(_PK_JS)
        return okk

    c1, pg = mk(1280, 800)
    try:
        ok("指向與拖曳：場景載入", load(pg))
        ids = pg.evaluate("() => { const W = __world, a = [...W.chars.values()].filter(c => !c.spec.isCeo && !c.spec.pet && !c.away); const nw = a.find(c => c.newModel), od = a.find(c => !c.newModel); return { nw: nw && nw.spec.id, od: od && od.spec.id }; }")
        ok("指向與拖曳：新舊兩種角色都有 %s" % ids, ids["nw"] and ids["od"], ids)
        pg.evaluate("() => __pk.freeze()")

        # ───── 1) 遠距離也點得到：俯視整棟（約 90 公尺）與跟隨視角拉遠（40 公尺，名牌已隱藏）─────
        for label, setup in (("俯視整棟 90 公尺", "() => __pk.dist(90)"), ("跟隨視角 40 公尺（名牌已隱藏）", "() => { const W = __world; W.setView('char', W.chars.get('%s'), true); const t = W.controls.target, off = W.camera.position.clone().sub(t).normalize(); W.camera.position.copy(t).addScaledVector(off, 40); W.controls.update(); W.camera.updateMatrixWorld(); return W.camera.position.distanceTo(t); }" % ids["od"])):
            d = pg.evaluate(setup)
            pg.wait_for_timeout(500)
            pg.evaluate("() => { __world.camera.updateMatrixWorld(); }")
            for kind in ("nw", "od"):
                cid = ids[kind]
                x, y, h = pg.evaluate("(id) => __pk.ctr(id)", cid)
                vis = 0 < x < 1280 and 60 < y < 780
                if not vis:
                    ok("指向：%s %s角色在畫面外，略過" % (label, kind), True)
                    continue
                pg.mouse.move(x - 8, y - 8)
                pg.mouse.move(x + 1, y + 1)   # 兩次移動：確保 pointermove 到達
                pg.wait_for_timeout(260)
                got = pg.evaluate("() => __pk.pick()")
                ok("指向：%s（鏡頭距離 %.0f m、角色螢幕高度約 %d px）游標在身上 → 指到他（外框 %d 片）" % (label, d, 0, got["n"]), got["who"] == cid and got["n"] > 0, (got, cid))
                # 偏 14 像素仍在最小命中圓（22）內
                pg.mouse.move(x + 14, y + 1)
                pg.wait_for_timeout(260)
                near = pg.evaluate("() => __pk.pick()")
                ok("指向：%s %s 偏 14 像素仍指得到" % (label, kind), near["who"] == cid, near)
                pg.mouse.move(x + 90, y + 1)
                pg.wait_for_timeout(260)
                far = pg.evaluate("() => __pk.pick()")
                ok("指向：%s %s 離 90 像素不會誤指到他（外框消失）" % (label, kind), far["who"] != cid, far)

        # ───── 2) 外框：像素變化（遠距離與近距離，新舊角色）─────
        for label, dd in (("遠 45 公尺", 45), ("近 8 公尺", 8)):
            for kind in ("nw", "od"):
                cid = ids[kind]
                pg.evaluate("(d) => { const W = __world; W.setView('god', null, true); }", dd)
                pg.evaluate("([id, d]) => { const W = __world, c = W.chars.get(id), p = c.object3D.position; W.view.mode = 'god'; W.controls.target.set(p.x, 0.6, p.z); W.camera.position.set(p.x + 0.01, 0.6 + d * 0.8, p.z + d * 0.6); W.camera.lookAt(W.controls.target); W.controls.update(); W.camera.updateMatrixWorld(); }", [cid, dd])
                pg.wait_for_timeout(500)
                x, y, h = pg.evaluate("(id) => __pk.ctr(id)", cid)
                clip = {"x": max(0, x - 60), "y": max(0, y - 60), "width": 120, "height": 120}
                pg.mouse.move(8, 400)
                pg.wait_for_timeout(260)
                n0 = pg.evaluate("() => __pk.pick().n")
                a = _pk_orange(pg.screenshot(clip=clip))
                pg.mouse.move(x - 5, y - 3)
                pg.mouse.move(x, y)
                pg.wait_for_timeout(300)
                got = pg.evaluate("() => __pk.pick()")
                png = pg.screenshot(clip=clip)
                bb = _pk_orange(png)
                if label.startswith("遠") and kind == "nw":
                    open("/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad/s3/pk_far_hover.png", "wb").write(pg.screenshot())
                if label.startswith("近") and kind == "od":
                    open("/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad/s3/pk_near_hover.png", "wb").write(pg.screenshot())
                pg.mouse.move(8, 400)
                pg.wait_for_timeout(300)
                gone = pg.evaluate("() => __pk.pick()")
                cc = _pk_orange(pg.screenshot(clip=clip))
                ok("外框：%s・%s 沒指向時無外框殼（%d 片）" % (label, kind, n0), n0 == 0)
                ok("外框：%s・%s 指向 → 外框殼 %d 片、橘色像素 %d → %d" % (label, kind, got["n"], a, bb), got["who"] == cid and got["n"] > 0 and bb - a >= 25, (got, a, bb))
                ok("外框：%s・%s 移開 → 殼拆掉、橘色像素回到 %d（≤ 原本 +5）" % (label, kind, cc), gone["n"] == 0 and cc <= a + 5, (gone, a, cc))

        # ───── 3) 拎著拖曳：跟地面投影點、不跟螢幕方向；游標靠邊鏡頭平移；滾輪縮放 ─────
        pg.evaluate("() => { const W = __world; W.speed = 1; }")
        cid = ids["nw"]
        pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c.busy = true; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.stop(false); c._drive = null; c.standAt(18, 20, 0); W.advance(0.4); W.speed = 0.001; }", cid)
        # 跟隨視角、距離 14 公尺（以前就是這種情況：點員工 → 鏡頭跟隨他 → 一拎起來就漂）
        pg.evaluate("(id) => { const W = __world; W.setView('char', W.chars.get(id), true); const t = W.controls.target, off = W.camera.position.clone().sub(t).normalize(); W.camera.position.copy(t).addScaledVector(off, 14); W.controls.update(); W.camera.updateMatrixWorld(); W.speed = 1; }", cid)
        pg.wait_for_timeout(900)
        x, y, h = pg.evaluate("(id) => __pk.ctr(id)", cid)
        pg.mouse.move(x, y)
        pg.mouse.down()
        pg.wait_for_timeout(700)
        pg.mouse.move(x + 20, y - 40, steps=3)     # 偏離螢幕中心的位置（以前會朝這個方向一直跑）
        pg.wait_for_timeout(300)
        held = pg.evaluate("(id) => ({ g: !!__world.grabbing(), st: __world.chars.get(id).state })", cid)
        ok("拎著：長按後拖曳 → 拎起來了 %s" % held, held["g"] and held["st"] == "held", held)
        cx, cy = x + 20, y - 40
        p0 = pg.evaluate("(id) => __pk.pos(id)", cid)
        t0 = pg.evaluate("() => __pk.tgt()")
        pg.wait_for_timeout(1500)       # 游標完全不動 1.5 秒：以前人會一直跑掉
        p1 = pg.evaluate("(id) => __pk.pos(id)", cid)
        t1 = pg.evaluate("() => __pk.tgt()")
        drift = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5
        cdrift = ((t1[0] - t0[0]) ** 2 + (t1[1] - t0[1]) ** 2) ** 0.5
        ok("拎著：游標不動 1.5 秒，員工漂移 %.2f m、鏡頭注視點漂移 %.2f m（都 < 0.3）" % (drift, cdrift), drift < 0.3 and cdrift < 0.3, (p0, p1, t0, t1))
        # 游標拖到畫面內另一個點 → 員工位置 = 游標在拎起高度水平面上的投影點（也量對地面的差）
        for tx, ty in ((640, 300), (420, 520), (860, 420)):
            pg.mouse.move(tx, ty, steps=8)
            pg.wait_for_timeout(900)
            exp = pg.evaluate("([a, b]) => __pk.plane(a, b, 1.05)", [tx, ty])
            gnd = pg.evaluate("([a, b]) => __pk.plane(a, b, 0)", [tx, ty])
            pp = pg.evaluate("(id) => __pk.pos(id)", cid)
            e1 = ((pp[0] - exp[0]) ** 2 + (pp[1] - exp[1]) ** 2) ** 0.5
            e2 = ((pp[0] - gnd[0]) ** 2 + (pp[1] - gnd[1]) ** 2) ** 0.5
            ok("拎著：游標在 (%d,%d)，員工離游標投影點 %.2f m（拎起高度水平面）／%.2f m（地面）— 水平面 < 0.5" % (tx, ty, e1, e2), e1 < 0.5, (pp, exp, gnd))
        # 滾輪縮放
        d0 = pg.evaluate("() => __world.camera.position.distanceTo(__world.controls.target)")
        pg.mouse.wheel(0, -300)
        pg.wait_for_timeout(500)
        d1 = pg.evaluate("() => __world.camera.position.distanceTo(__world.controls.target)")
        ok("拎著：滾輪仍可縮放（鏡頭距離 %.1f → %.1f）" % (d0, d1), d1 < d0 - 1 and pg.evaluate("() => !!__world.grabbing()"))
        pg.mouse.move(640, 300, steps=4)
        pg.wait_for_timeout(600)
        # 邊緣平移：游標靠左邊緣 → 鏡頭往左平移，員工跟著走、還在畫面內
        pg.evaluate("() => { const W = __world; const t = W.controls.target, off = W.camera.position.clone().sub(t).normalize(); W.camera.position.copy(t).addScaledVector(off, 22 - W.camera.position.distanceTo(t)); W.camera.updateMatrixWorld(); }")
        pg.wait_for_timeout(300)
        pa = pg.evaluate("(id) => __pk.pos(id)", cid)
        ta = pg.evaluate("() => __pk.tgt()")
        right = pg.evaluate("() => { const W = __world, d = new W.THREE.Vector3(); W.camera.getWorldDirection(d); return [-d.z, d.x]; }")
        n = (right[0] ** 2 + right[1] ** 2) ** 0.5 or 1
        pg.mouse.move(10, 400, steps=6)
        pg.wait_for_timeout(1400)
        pb = pg.evaluate("(id) => __pk.pos(id)", cid)
        tb = pg.evaluate("() => __pk.tgt()")
        pan = ((tb[0] - ta[0]) * right[0] + (tb[1] - ta[1]) * right[1]) / n
        mv = ((pb[0] - pa[0]) * right[0] + (pb[1] - pa[1]) * right[1]) / n
        sx, sy, _ = pg.evaluate("(id) => __pk.ctr(id)", cid)
        stat = pg.evaluate("() => __world.grabStat")
        ok("邊緣平移：游標貼左邊 → 鏡頭往左平移 %.1f m、員工往左 %.1f m、仍被拎著、仍在畫面內 (%d,%d)" % (-pan, -mv, sx, sy), pan < -3 and mv < -3 and pg.evaluate("() => !!__world.grabbing()") and 0 < sx < 1280, (pan, mv, stat, sx, sy))
        pg.screenshot(path="/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad/s3/pk_dragging.png")
        pg.mouse.move(640, 400, steps=4)
        pg.wait_for_timeout(300)
        pg.mouse.up()
        pg.wait_for_timeout(500)
        rel = pg.evaluate("(id) => ({ g: !!__world.grabbing(), st: __world.chars.get(id).state, n: __world.outline.hulls.length })", cid)
        ok("拎著：放開後不再拎著、外框拆掉 %s" % rel, (not rel["g"]) and rel["st"] != "held" and rel["n"] == 0, rel)

        # ───── 4) 佈告欄：回報進度格式 ─────
        dept = pg.evaluate("() => __world.org.departments[0].id")
        pg.evaluate("(d) => __world.ui.showBoard(d)", dept)
        pg.wait_for_timeout(300)
        bd = pg.evaluate("""() => { const b = document.getElementById('board'), t = b.innerText, r = b.getBoundingClientRect(), rows = [...b.querySelectorAll('.row.bt')];
          const sy = {}; rows.forEach(x => { const s = x.querySelector('.sy').textContent; sy[s] = (sy[s] || 0) + 1; });
          return { t, hidden: b.hidden, rect: [r.left, r.top, r.right, r.bottom], sw: b.scrollWidth, cw: b.clientWidth, rows: rows.length, sy, hasAct: !!b.querySelector('.acts [data-hr=firedept]') }; }""")
        ok("佈告欄：開得起來，有 %d 件事項，符號分佈 %s" % (bd["rows"], bd["sy"]), (not bd["hidden"]) and bd["rows"] >= 3, bd)
        for s in ("✅", "🔄", "🛠️", "⚠️"):
            ok("佈告欄：出現符號 %s" % s, s in bd["t"])
        ok("佈告欄：有「花」＋完成時間欄、進行中有「預估還要」「預估完成」、未完成有「預計」「卡在／沒有卡關」", all(k in bd["t"] for k in ("完成 ", "預估", "預計")) and ("卡在" in bd["t"] or "沒有卡關" in bd["t"]), bd["t"][:400])
        ok("佈告欄：底部「開除整個部門」按鈕還在", bd["hasAct"])
        # 逐種狀態切過去、各展開一列
        seen = {}
        for k in (1, 2, 3):
            pg.evaluate("(k) => document.querySelector('#board [data-bk=\"' + k + '\"]').click()", k)
            pg.wait_for_timeout(150)
            r = pg.evaluate("() => { const b = document.getElementById('board'), row = b.querySelector('.row.bt'); if (!row) return null; row.click(); const dl = b.querySelector('.det'); return { head: b.querySelector('.row.bt .bm').innerText, det: dl ? dl.innerText : '' }; }")
            seen[k] = r
        ok("佈告欄：三種狀態的列都有時間欄位 %s" % {k: (v and v["head"][:40]) for k, v in seen.items()}, all(v and ("完成" in v["head"] or "開始" in v["head"] or "排定" in v["head"]) for v in seen.values()), seen)
        pg.evaluate("() => { document.querySelector('#board [data-bk=\"2\"]').click(); }")
        pg.wait_for_timeout(200)
        pg.screenshot(path="/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad/s3/pk_board_desktop.png")
        # 效能：pickChar 一次的成本
        t = pg.evaluate("() => { const W = __world, e = { clientX: 640, clientY: 400, pointerType: 'mouse' }, t0 = performance.now(); for (let i = 0; i < 400; i++) W.pickChar(e); return (performance.now() - t0) / 400; }")
        out["pick_ms"] = t
        ok("效能：pickChar 一次 %.3f 毫秒（%d 位角色）" % (t, pg.evaluate("() => __world.chars.size")), t < 1.0)
    finally:
        c1.close()

    # ───── 手機 390×844：佈告欄完整看得到；觸控點選與拎起 ─────
    c2, pm = mk(390, 844, True)
    try:
        ok("手機：場景載入", load(pm))
        dept = pm.evaluate("() => __world.org.departments[0].id")
        pm.evaluate("(d) => __world.ui.showBoard(d)", dept)
        pm.wait_for_timeout(400)
        bd = pm.evaluate("""() => { const b = document.getElementById('board'), r = b.getBoundingClientRect(), sc = document.getElementById('boardScroll'); return { rect: [r.left, r.top, r.right, r.bottom], sw: b.scrollWidth, cw: b.clientWidth, scw: sc.scrollWidth, sccw: sc.clientWidth, sh: sc.scrollHeight, ch: sc.clientHeight, vw: innerWidth, vh: innerHeight, act: (() => { const a = b.querySelector('.acts'); if (!a) return null; const q = a.getBoundingClientRect(); return [q.top, q.bottom]; })(), t: b.innerText.slice(0, 120) }; }""")
        ok("手機：佈告欄在畫面內且沒有橫向溢出 %s" % bd["rect"], bd["rect"][0] >= 0 and bd["rect"][2] <= bd["vw"] + 1 and bd["rect"][3] <= bd["vh"] + 1 and bd["scw"] <= bd["sccw"] + 1 and bd["sw"] <= bd["cw"] + 1, bd)
        ok("手機：佈告欄底部按鈕列看得到、內容可捲動看完（內容 %d／可視 %d）" % (bd["sh"], bd["ch"]), bd["act"] is not None and bd["act"][1] <= bd["vh"] + 1 and bd["ch"] >= 120, bd)
        pm.screenshot(path="/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad/s3/pk_board_mobile.png")
        pm.evaluate("() => { document.getElementById('board').hidden = true; }")
        pm.evaluate("() => __pk.freeze()")
        pm.evaluate("() => __pk.dist(90)")
        pm.wait_for_timeout(500)
        nm = pm.evaluate("() => [...__world.chars.values()].find(c => !c.spec.isCeo && !c.spec.pet && !c.away).spec.id")
        x, y, h = pm.evaluate("(id) => __pk.ctr(id)", nm)
        ok("手機：觸控命中圓 30 像素（遠距離 90 公尺、點偏 24 像素仍選得到人）", pm.evaluate("([x, y]) => !!__world.pickChar({ clientX: x + 24, clientY: y + 2, pointerType: 'touch' })", [x, y]))
    finally:
        c2.close()
    ok("指向與拖曳：整段沒有主控台錯誤", not errs, errs[:3])


register("辦公室指向與拖曳", lambda pg, b, base, code: t_office_pick(b, base))
