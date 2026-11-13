# 驗收段落「糰糰v2」（AI Office 角色升級第二階段）：site/office/char.html 的展示頁。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until() 直接可用，不要 import _uitest。
# 原則：每一項都驗「畫面真的因此改變了」——用截圖位元組比對、骨頭／形態鍵數值、相機位置，不只驗元素存在。
# flake8: noqa

import hashlib as _hl
import math as _m


def _root(base):
    return base.split("/index.html")[0].rstrip("/")


def _calm(pg, ms=15000):
    """鏡頭補間結束、表情混合到位（軟體繪圖很慢，不能用固定毫秒等）"""
    return wait_until(pg, "() => { const f = CH.ch.face; return !CH.S.tween && (!f || Object.keys(f.target).every(k => Math.abs(f.cur[k] - f.target[k]) < 0.03)); }", ms, 120)


def _shot(pg, clip=None):
    return _hl.md5(pg.screenshot(clip=clip)).hexdigest()


_FACE_CLIP = {"x": 0, "y": 0, "width": 0, "height": 0}

_LOWEST_Y = """() => { const ch = CH.ch, b = ch.body, g = b.geometry, p = g.attributes.position, T = new CH.camera.position.constructor(), M = g.morphAttributes.position, w = b.morphTargetInfluences;
  ch.model.updateMatrixWorld(true); b.skeleton.update(); let mn = 1e9;
  for (let i = 0; i < p.count; i += 1) { T.set(p.getX(i), p.getY(i), p.getZ(i)); for (let k = 0; k < M.length; k++) if (w[k]) T.x += M[k].getX(i) * w[k], T.y += M[k].getY(i) * w[k], T.z += M[k].getZ(i) * w[k];
    b.applyBoneTransform(i, T); T.applyMatrix4(b.matrixWorld); if (T.y < mn) mn = T.y; }
  return mn; }"""


def _open(b, base, vp=None, mobile=False, qs="?shot"):
    kw = dict(viewport=vp or {"width": 1100, "height": 760})
    if mobile:
        kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    c = b.new_context(**kw)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(_root(base) + "/office/char.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => document.documentElement.dataset.ready === '1'", 60000)
    pg.add_style_tag(content='#stat{display:none !important}')   # fps 字樣每秒變一次，會讓截圖比對誤判
    return c, pg, errs, got


def t_office_char(b, base):
    c, pg, errs, got = _open(b, base)
    try:
        ok("糰糰v2：展示頁載入完成（GLB＋骨架＋臉）", got)
        if not got:
            return
        info = pg.evaluate("""() => { const c = CH.ch, b = c.body; return { bones: b.skeleton.bones.length, morphs: Object.keys(b.morphTargetDictionary), tris: b.geometry.index.count / 3 + c.decal.geometry.index.count / 3,
          skinned: b.isSkinnedMesh && c.decal.isSkinnedMesh, hasFace: !!c.face, eyes: c.face ? c.face.eyes.length : 0, ao: !!b.geometry.attributes.color }; }""")
        ok("★ 糰糰v2：是 SkinnedMesh，骨頭 18 根、形態鍵 7 個、頂點色 AO", info["skinned"] and info["bones"] == 18 and len(info["morphs"]) == 7 and info["ao"], info)
        ok("糰糰v2：LOD0 網格（本體＋臉貼片）≤ 9000 三角面", info["tris"] <= 9000, info["tris"])
        geo = pg.evaluate("""() => { const c = CH.ch, W = (n) => c.boneWorld(n), e = c.meta.anchors['eye.L'].p, eR = c.meta.anchors['eye.R'].p;
          const col = c.body.geometry.attributes.color; const bb = c.body.geometry.boundingBox || (c.body.geometry.computeBoundingBox(), c.body.geometry.boundingBox);
          return { hand: W('hand.L').x, footY: W('foot.L').z, height: bb.max.y - bb.min.y, width: bb.max.x - bb.min.x, eyeGap: Math.abs(e[0] - eR[0]), eyeLow: e[1], colorN: col ? col.itemSize : 0 }; }""")
        ok("★ 四肢讀得出來：手骨末端在身體側面外凸（x ≥ 0.45）、腳往身體前下方凸出（z 方向 ≥ 0.2）", geo["hand"] >= 0.45 and geo["footY"] >= 0.2, geo)
        ok("頂點色已合成 RGB（局部顏色×AO，itemSize 3）", geo["colorN"] == 3, geo)
        ok("眼睛低位（高度在身高 45% 以下）且間距寬（兩眼中心距 ≥ 0.28 m）", geo["eyeLow"] < geo["height"] * 0.45 and geo["eyeGap"] >= 0.28, geo)
        ok("糰糰v2：有兩顆立體眼球", info["eyes"] == 2)

        # ── 靜止／動態開關：切了之後畫面真的停下來／動起來
        pg.evaluate("() => { CH.S.ch.face.autoBlink = false; }")
        pg.click("#btnMotion")
        wait_until(pg, "() => CH.S.paused === true", 3000)
        t0 = pg.evaluate("() => CH.S.time"); h0 = _shot(pg); pg.wait_for_timeout(900); h1 = _shot(pg); t1 = pg.evaluate("() => CH.S.time")
        ok("★ 切「靜止」：畫面完全不變、時間不前進", h0 == h1 and abs(t1 - t0) < 1e-6, [h0 == h1, t0, t1])
        ok("靜止鈕：文字變「靜止」、aria-pressed=false", pg.inner_text("#btnMotion").strip() == "靜止" and pg.get_attribute("#btnMotion", "aria-pressed") == "false")
        pg.click("#btnMotion")
        wait_until(pg, "() => CH.S.paused === false", 3000)
        pg.wait_for_timeout(700); h2 = _shot(pg); pg.wait_for_timeout(500); h3 = _shot(pg)
        ok("★ 切回「動態」：呼吸待機讓畫面隨時間改變", h2 != h3 or pg.evaluate("() => CH.S.time") > t1 + 0.5, [h2 != h3])
        # 頁面切走：rAF 停掉
        pg.evaluate("() => { Object.defineProperty(document, 'hidden', { value: true, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); }")
        pg.wait_for_timeout(300); f0 = pg.evaluate("() => CH.S.frames"); pg.wait_for_timeout(600); f1 = pg.evaluate("() => CH.S.frames")
        ok("★ 分頁切走：動畫迴圈停掉（幀數不增加）", f1 == f0, [f0, f1])
        pg.evaluate("() => { Object.defineProperty(document, 'hidden', { value: false, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); }")
        got2 = wait_until(pg, f"() => CH.S.frames >= {f1 + 3}", 10000, 100); f2 = pg.evaluate("() => CH.S.frames")
        ok("分頁切回：動畫迴圈重新開始（軟體繪圖很慢，等到多 3 幀為止）", bool(got2), [f1, f2])

        # ── 視角鈕：相機真的轉到對的方位
        want = {"正面": 0, "側面": 90, "背面": 180, "45 度": 45}
        for label, deg in want.items():
            pg.click(f"#gView button:has-text('{label}')")
            wait_until(pg, "() => !CH.S.tween", 20000, 100); pg.wait_for_timeout(250)
            az = pg.evaluate("() => { const p = CH.camera.position; return Math.atan2(p.x, p.z) * 180 / Math.PI; }")
            d = abs(((az - deg + 180) % 360) - 180)
            ok(f"視角鈕「{label}」：相機方位 {deg}°（實際 {az:.0f}°）", d < 8, az)
        pg.click("#gView button:has-text('正面')"); wait_until(pg, "() => !CH.S.tween", 20000, 100)

        # ── 表情：8 顆按鈕，每個都讓臉的畫面不一樣
        pg.click("#btnMotion"); wait_until(pg, "() => CH.S.paused === true", 3000)   # 靜止模式下表情仍要會變（按鈕要有反應）
        pg.evaluate("() => { CH.camera.position.set(0, 0.42, 1.55); CH.ctl.target.set(0, 0.3, 0); CH.ctl.update(); CH.S.tween = null; }")
        hs = {}
        for key, zh in (("neutral", "正常睜眼"), ("happy", "開心閉眼"), ("confused", "疑惑"), ("sad", "難過"), ("angry", "生氣"), ("surprised", "驚訝"), ("sleep", "睡覺"), ("smile", "嘴角微笑")):
            pg.click(f"#gExpr button:has-text('{zh}')"); _calm(pg)
            nm = pg.evaluate("() => CH.ch.face.name")
            hs[key] = _shot(pg)
            ok(f"表情鈕「{zh}」：face.name＝{key}", nm == key, nm)
        ok("★ 八種表情畫面兩兩不同（臉真的改變）", len(set(hs.values())) == 8, {k: v[:6] for k, v in hs.items()})
        # 睡覺＝兩顆眼都閉；開心＝笑眼弧出現；難過＝有淚
        pg.click("#gExpr button:has-text('睡覺')"); _calm(pg)
        st = pg.evaluate("() => ({ lidOpen: CH.ch.face.eyes.map(e => e.lid.visible), up: CH.ch.face.eyes.map(e => e.arcUp.visible), dn: CH.ch.face.eyes.map(e => e.arcDn.visible), tear: CH.ch.face.cur.tear })")
        ok("睡覺：眼皮閉上、∪ 形睡眼弧出現", all(st["lidOpen"]) and all(st["dn"]), st)
        pg.evaluate("() => { const f = CH.ch.face; f.set('neutral'); f.snap(); f.blinkV = 0; f.blink = 0.5; f.update(0.001, 12, true); }")
        st = pg.evaluate("() => ({ rim: CH.ch.face.eyes.map(e => e.rim.visible), lash: CH.ch.face.eyes.map(e => e.lash.visible) })")
        ok("★ 眨眼中間格：眼皮邊緣的睫毛線出現、全閉睫毛弧還沒出現（不是空白面具）", all(st["rim"]) and not any(st["lash"]), st)
        pg.evaluate("() => { const f = CH.ch.face; f.blink = 1; f.update(0.001, 12, true); }")
        st = pg.evaluate("() => ({ rim: CH.ch.face.eyes.map(e => e.rim.visible), lash: CH.ch.face.eyes.map(e => e.lash.visible), same: CH.ch.face.eyes[0].lid.material !== CH.ch.face.eyes[1].lid.material })")
        ok("★ 眨眼閉合：睫毛弧出現、眼皮邊緣線收掉；左右眼皮各有自己的表面法線材質", all(st["lash"]) and not any(st["rim"]) and st["same"], st)
        pg.evaluate("() => { const f = CH.ch.face; f.blink = 0; f.update(0.001, 12, true); }")
        pg.click("#gExpr button:has-text('開心閉眼')"); _calm(pg)
        st = pg.evaluate("() => ({ lid: CH.ch.face.eyes.map(e => e.lid.visible), up: CH.ch.face.eyes.map(e => e.arcUp.visible) })")
        ok("開心閉眼：眼皮閉上、∩ 形笑眼弧出現", all(st["lid"]) and all(st["up"]), st)
        pg.click("#gExpr button:has-text('難過')"); _calm(pg)
        ok("難過：眼淚貼花出現（tear>0.5）", pg.evaluate("() => CH.ch.face.cur.tear") > 0.5)
        pg.click("#gExpr button:has-text('正常睜眼')"); _calm(pg)
        # 自然眨眼：排程到了眼皮會閉上再打開
        pg.click("#btnMotion"); wait_until(pg, "() => CH.S.paused === false", 3000)
        pg.evaluate("() => { CH.ch.face.autoBlink = true; CH.ch.face.blinkT = 0.05; }")
        seen = pg.evaluate("""() => new Promise(res => { let n = 0, t0 = performance.now(), closed = false; const f = () => { if (CH.ch.face.blink > 0.6) closed = true; if (performance.now() - t0 > 1500) return res(closed); requestAnimationFrame(f); }; f(); })""")
        ok("★ 自然眨眼：排程觸發後眼皮真的閉上（blink>0.6）", seen)
        pg.evaluate("() => { CH.ch.face.autoBlink = false; }"); pg.wait_for_timeout(300)
        pg.click("#btnMotion"); wait_until(pg, "() => CH.S.paused === true", 3000)

        # ── 視線追蹤：瞳孔（眼球）在動，不是整張臉平移
        pg.click("#gExpr button:has-text('正常睜眼')"); pg.click("#btnMotion"); wait_until(pg, "() => CH.S.paused === false", 3000)
        pg.click("#btnTrack"); pg.evaluate("() => { CH.ch.face.autoBlink = false; }")
        box = pg.evaluate("() => { const r = CH.renderer.domElement.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
        res = {}
        for tag, fx, fy in (("L", 0.12, 0.5), ("R", 0.88, 0.5), ("U", 0.5, 0.08), ("D", 0.5, 0.62)):
            pg.mouse.move(box[0] + box[2] * fx, box[1] + box[3] * fy, steps=4)
            pg.wait_for_timeout(900)
            res[tag] = pg.evaluate("() => ({ y: CH.ch.face.eyes[0].ball.rotation.y, x: CH.ch.face.eyes[0].ball.rotation.x, decal: CH.ch.decal.position.toArray(), eyeGrp: CH.ch.face.eyes[0].grp.position.toArray() })")
        ok("★ 視線追蹤：游標在左／右，眼球左右轉向相反", res["L"]["y"] * res["R"]["y"] < 0 and abs(res["L"]["y"]) > 0.08 and abs(res["R"]["y"]) > 0.08, [res["L"]["y"], res["R"]["y"]])
        ok("視線追蹤：游標在上／下，眼球上下轉向相反", res["U"]["x"] * res["D"]["x"] < 0, [res["U"]["x"], res["D"]["x"]])
        ok("★ 視線追蹤：眼球座標與臉貼片沒有平移（動的是瞳孔，不是整張臉）", all(abs(res[k]["eyeGrp"][i] - res["L"]["eyeGrp"][i]) < 0.004 for k in res for i in range(3)) and res["L"]["decal"] == res["R"]["decal"], [res["L"]["eyeGrp"], res["R"]["eyeGrp"]])
        pg.click("#btnTrack"); pg.wait_for_timeout(700)
        ok("關閉視線追蹤：眼球回正（|yaw|<0.06）", abs(pg.evaluate("() => CH.ch.face.eyes[0].ball.rotation.y")) < 0.06)

        # ── 動作示範：真的動骨頭與形態鍵，結束後回到靜止姿勢
        pg.evaluate("() => CH.S.ch.resetPose()")
        pg.click("#gAct button:has-text('揮手')")
        wait_until(pg, "() => CH.S.act && CH.S.act.t > 0.8", 20000, 100)
        ang = pg.evaluate("() => { const b = CH.ch.bones['arm.L'], r = CH.ch.rest['arm.L']; return b.quaternion.angleTo(r.q); }")
        ok("★ 揮手：arm.L 骨頭離開靜止姿勢超過 0.6 弧度", ang > 0.6, ang)
        wait_until(pg, "() => CH.S.act === null", 30000, 150); pg.wait_for_timeout(200)
        ang2 = pg.evaluate("() => { const b = CH.ch.bones['arm.L'], r = CH.ch.rest['arm.L']; return b.quaternion.angleTo(r.q); }")
        ok("★ 揮手結束：骨頭回到靜止姿勢（<0.02）、沒有殘留動作", ang2 < 0.02 and pg.evaluate("() => CH.S.act") is None, ang2)
        pg.click("#gAct button:has-text('被壓扁回彈')")
        wait_until(pg, "() => CH.S.act && CH.S.act.t > 0.34", 20000, 60)
        land = pg.evaluate("() => CH.ch.wm.land || 0")
        ok("★ 被壓扁：land 形態鍵權重 > 0.4（身體真的變扁）", land > 0.4, land)
        low = pg.evaluate(_LOWEST_Y)
        ok("★ 壓扁到最扁：身體最低點沒有穿地（y ≥ −0.012）", low >= -0.012, low)
        wait_until(pg, "() => CH.S.act === null", 30000, 150); pg.wait_for_timeout(200)
        ok("被壓扁結束：land 形態鍵回 0", (pg.evaluate("() => CH.ch.wm.land || 0")) < 0.02)
        pg.click("#gAct button:has-text('小跳')")
        wait_until(pg, "() => CH.S.act && CH.S.act.t > 0.4", 20000, 40)
        y = pg.evaluate("() => CH.ch.boneWorld('root').y")
        ok("小跳：root 骨頭離地（y>0.2），接觸陰影變淡", y > 0.2 and pg.evaluate("() => CH.stage.shadows[0].body.material.opacity") < 0.2, [y])
        wait_until(pg, "() => CH.S.act === null", 30000, 100); pg.wait_for_timeout(200)
        ok("小跳結束：root 回到地面（y<0.01）", pg.evaluate("() => CH.ch.boneWorld('root').y") < 0.01)
        rest_low = pg.evaluate(_LOWEST_Y)
        ok("靜止姿勢：身體最低點貼地（|y| < 0.012）", abs(rest_low) < 0.012, rest_low)
        fin = pg.evaluate("() => { let bad = 0; CH.ch.model.traverse(n => { if (n.isBone) for (const v of n.matrixWorld.elements) if (!isFinite(v)) bad++; }); return bad; }")
        ok("所有動作後骨頭矩陣沒有 NaN／無限大", fin == 0, fin)

        # ── 線框、剪影、新舊並排、材質
        pg.click("#gAct button:has-text('轉頭')"); pg.wait_for_timeout(100)
        pg.evaluate("() => CH.endAct()"); pg.click("#btnMotion"); wait_until(pg, "() => CH.S.paused === true", 3000)
        pg.evaluate("() => { CH.S.ch.resetPose(); CH.S.ch.update(0); }"); _calm(pg); pg.wait_for_timeout(300)
        CL = {"x": 0, "y": 50, "width": 1100, "height": 440}   # 只比 3D 畫面（面板按鈕的 hover 狀態會讓整頁截圖不同）
        a0 = _shot(pg, CL)
        pg.click("#btnWire"); pg.wait_for_timeout(300); a1 = _shot(pg, CL)
        ok("★ 線框鈕：畫面改變，覆蓋材質為 wireframe", a1 != a0 and pg.evaluate("() => !!CH.scene.overrideMaterial && CH.scene.overrideMaterial.wireframe"), [a0 != a1])
        pg.click("#btnWire"); pg.wait_for_timeout(500)
        ok("線框再按一次：還原（畫面與原圖相同）", _shot(pg, CL) == a0)
        pg.click("#btnSil"); pg.wait_for_timeout(300)
        sil = pg.evaluate("() => !!CH.scene.overrideMaterial && CH.scene.overrideMaterial.color.getHex() === 0x111111")
        ok("★ 黑色剪影鈕：整個場景改成純黑剪影", sil and _shot(pg, CL) != a0)
        pg.click("#btnSil"); pg.wait_for_timeout(300)
        pg.click("#btnCmp"); pg.wait_for_timeout(1200)
        ok("★ 新舊並排：舊版（球體拼接）被建立、標籤出現", pg.evaluate("() => !!CH.S.old && CH.S.cmp") and pg.evaluate("() => document.getElementById('tag').classList.contains('on')"))
        w = pg.evaluate("() => innerWidth")
        left = _shot(pg, {"x": 0, "y": 80, "width": w // 2, "height": 380}); right = _shot(pg, {"x": w // 2, "y": 80, "width": w // 2, "height": 380})
        ok("新舊並排：左右兩半是不同的角色畫面", left != right)
        px = pg.evaluate("""() => { const r = CH.renderer.domElement, g = document.createElement('canvas'); g.width = r.width; g.height = r.height; const x = g.getContext('2d'); x.drawImage(r, 0, 0);
          const half = (x0) => { const d = x.getImageData(x0, Math.floor(r.height * 0.2), Math.floor(r.width / 2) - 2, Math.floor(r.height * 0.5)).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 243) + Math.abs(d[i + 1] - 230) + Math.abs(d[i + 2] - 216) > 60) n++; return n; };
          return [half(0), half(Math.floor(r.width / 2) + 2)]; }""")
        ok("★ 新舊並排：左（新）右（舊）都真的有畫出角色（非背景像素 > 3000）", px[0] > 3000 and px[1] > 3000, px)
        pg.click("#btnCmp"); pg.wait_for_timeout(600)
        sm = pg.query_selector("#selMat")
        before = _shot(pg)
        sm.select_option("ceramic"); pg.wait_for_timeout(500)
        ok("★ 材質預設「陶瓷」：材質參數與畫面都改變（roughness 0.28、clearcoat 0.6）", pg.evaluate("() => { const m = CH.ch.body.material; return m.userData.preset === 'ceramic' && Math.abs(m.roughness - 0.28) < 1e-6 && m.clearcoat > 0.5; }") and _shot(pg) != before)
        pg.evaluate("() => { const o = [...CH.ch.body.material.userData.P ? [CH.ch.body.material.userData.P] : []]; }")
        sm.select_option("fur"); pg.wait_for_timeout(400)
        pr = pg.evaluate("() => { const m = CH.ch.body.material; return { r: m.roughness, e: m.emissive.getHex(), env: m.envMapIntensity, sheen: m.sheen, coat: m.clearcoat }; }")
        ok("★ 材質通則（軟綿絨毛）：roughness≥0.45、不發光（emissive=0）、envMapIntensity≤0.5、clearcoat≤0.2", pr["r"] >= 0.45 and pr["e"] == 0 and pr["env"] <= 0.5 and pr["coat"] <= 0.2, pr)
        ok("糰糰v2 桌機：沒有網頁錯誤", not errs, errs[:3])
    finally:
        c.close()

    # ── LOD2：沒有臉貼片、面數少，頁面不出錯
    c, pg, errs, got = _open(b, base, qs="?shot&lod=2")
    try:
        ok("糰糰v2 LOD2：載入、沒有臉貼片、≤ 1100 三角面（含併入本體的兩顆深色眼睛）、沒有網頁錯誤", got and pg.evaluate("() => !CH.ch.face && CH.ch.body.geometry.index.count / 3 <= 1100") and not errs, errs[:3])
    finally:
        c.close()

    # ── 手機寬度 390
    c, pg, errs, got = _open(b, base, vp={"width": 390, "height": 844}, mobile=True)
    try:
        if got:
            m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth, panel: getComputedStyle(document.getElementById('panel')).display, hasBtn: !!document.getElementById('btnPanel') })")
            ok("★ 手機 390：沒有橫向捲軸、預設收起控制面板、有「控制面板」鈕", m["sw"] <= m["iw"] and m["panel"] == "none" and m["hasBtn"], m)
            c0 = _shot(pg)
            pg.click("#btnPanel"); pg.wait_for_timeout(500)
            m2 = pg.evaluate("""() => ({ panel: getComputedStyle(document.getElementById('panel')).display, sw: document.documentElement.scrollWidth, iw: innerWidth,
              minH: Math.min(...[...document.querySelectorAll('#panel button')].map(b => b.getBoundingClientRect().height)), minF: Math.min(...[...document.querySelectorAll('#panel button, #panel b, #panel select')].map(b => parseFloat(getComputedStyle(b).fontSize))),
              out: [...document.querySelectorAll('#panel button')].filter(b => { const r = b.getBoundingClientRect(); return r.right > innerWidth + 1 || r.left < -1; }).length })""")
            ok("★ 手機 390 展開面板：按鈕 ≥ 32px 高、字 ≥ 12px、沒有按鈕超出畫面、沒有橫向捲軸", m2["panel"] != "none" and m2["minH"] >= 31.5 and m2["minF"] >= 12 and m2["out"] == 0 and m2["sw"] <= m2["iw"], m2)
            ok("手機 390：展開面板後畫面真的改變（角色往上讓位）", _shot(pg) != c0)
            pg.click("#gExpr button:has-text('驚訝')"); pg.wait_for_timeout(700)
            ok("手機 390：點表情鈕有反應（face.name＝surprised）", pg.evaluate("() => CH.ch.face.name") == "surprised")
        ok("糰糰v2 手機：載入且沒有網頁錯誤", got and not errs, errs[:3])
    finally:
        c.close()

    # ── 47 隻同場壓力頁：繪製呼叫、三角面、JS 時間都在預算內
    c = b.new_context(viewport={"width": 1000, "height": 650})
    pg = c.new_page()
    perr = []
    pg.on("pageerror", lambda e: perr.append(str(e)))
    try:
        pg.goto(_root(base) + "/office/char/stress.html?n=47&lod=mix", wait_until="domcontentloaded")
        got = wait_until(pg, "() => document.documentElement.dataset.ready === '1'", 90000)
        pg.wait_for_timeout(1500)
        s = pg.evaluate("() => window.STRESS") if got else None
        ok("★ 47 隻同場（距離分級）：繪製呼叫 ≤ 330、三角面 ≤ 400k、JS 更新 ≤ 6 ms/幀", bool(s) and s["calls"] <= 330 and s["tris"] <= 400000 and s["updMs"] <= 6.0, s)
        ok("47 隻同場：沒有網頁錯誤", not perr, perr[:3])
    finally:
        c.close()


register("糰糰v2", lambda pg, b, base, code: t_office_char(b, base))
