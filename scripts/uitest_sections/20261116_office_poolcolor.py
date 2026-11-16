# 驗收段落「辦公室泳池洗色」（2026-11-16 擁有者回報：「被燒到後放到泳池內會熄火，身上顏色會被洗掉」）
#   預期：泳池只洗掉「燒焦的黑」，角色原本的膚色、漸層、腮紅、配件顏色必須完整恢復。
#   做法：新角色、舊角色各一位，真滑鼠把「燒著的員工」拎起丟進泳池 → 熄火 → 出水；
#         逐材質比對燒前與恢復後的 color／emissive／emissiveIntensity／opacity／map／頂點色旗標、以及材質上的顏色型著色器參數
#         （漸層 uTop、區塊色 uZoneCol／uZone2Col、次表面 uSss、邊緣光 uRim），每一項差 < 0.02；
#         焦黑疊色（uScorch／uEmber）要在水裡 6 秒內歸零；燒前／燒焦／出水後各截一張圖。
#   另測：自然熄火（沒進泳池）的恢復路徑、冒煙愣著的人走進泳池會被洗乾淨（washed）、再燒一次也能正常恢復。
#   截圖放 TW_SHOT_DIR（預設系統暫存區 office_poolcolor）。
#   由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa
import math as _m
import os as _os
import io as _io
import tempfile as _tf
from PIL import Image as _Im

_PC_URL = "/office/world.html?ambient=0&q=low&pr=0.5"
_PC_NAT = (18.0, 40.5)   # 離營火與泳池都遠的地方（自然熄火與「冒煙愣著」用）
_PC_SHOTS = _os.environ.get("TW_SHOT_DIR") or _os.path.join(_tf.gettempdir(), "office_poolcolor")

_PC_SNAP = """(id) => { const c = __world.chars.get(id), out = {}; let n = 0;
  const rgb = v => v && v.isColor ? v.toArray().map(x => +x.toFixed(4)) : null;
  c.object3D.traverse(o => { if (!o.isMesh || !o.material) return; for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
    const r = { nm: (o.name || o.type) + '|' + (o.userData && o.userData.prop || '') + '|' + o.visible, col: rgb(m.color), em: rgb(m.emissive), ei: m.emissiveIntensity == null ? null : +m.emissiveIntensity, op: +m.opacity, map: m.map ? m.map.uuid : null, vc: !!m.vertexColors, patched: !!(m.userData && m.userData._scOwner), U: {} };
    const U = m.userData && m.userData.U; if (U) for (const q in U) { const v = U[q] && U[q].value; if (v && v.isColor && q !== 'uTint') r.U[q] = rgb(v); }   // uTint 要跟 uTintAmt（情緒色調，會自己淡出）一起看，下面另外比 uTintAmt
    r.tint = U && U.uTintAmt ? +U.uTintAmt.value.toFixed(3) : null;
    const q = m.uuid; if (!out[q]) out[q] = r; n++; } });
  return out; }"""


def _pc_page(b, base, vw=1280, vh=800):
    c = b.new_context(viewport={"width": vw, "height": vh})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.removeItem('aiOffice.hr.v1')}catch(e){}")
    pg = c.new_page(); pg.set_default_timeout(120000); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)[:200]))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(base.split("/index.html")[0].rstrip("/") + _PC_URL, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    return c, pg, got


def _pc_adv(pg, sec):
    pg.evaluate("async (s) => { await __world.advanceAsync(s) }", sec)


def _pc_god(pg, x, z, d):
    pg.evaluate("([x, z, d]) => __world.godAt(x, z, d)", [x, z, d]); pg.wait_for_timeout(2300)


def _pc_st(pg, who):
    return pg.evaluate("(id) => { const W = __world, c = W.chars.get(id), o = W.fire.stateOf(c); return { s: o.state, soot: c._sootU ? c._sootU.value : -1, ember: c._emberU ? c._emberU.value : -1, inw: W.sports.water.inWater(c) } }", who)


def _pc_diff(a, b):
    """逐材質比對；回傳（比了幾項, 超過 0.02 的清單）"""
    bad, n = [], 0
    for k, x in a.items():
        y = b.get(k)
        if y is None:
            bad.append((x.get("nm"), "材質不見了")); continue
        for f in ("col", "em"):
            if x[f] is None:
                continue
            n += 1
            if y[f] is None or max(abs(p - q) for p, q in zip(x[f], y[f])) >= 0.02:
                bad.append((k, f, x[f], y[f]))
        for f in ("ei", "op"):
            if x[f] is not None:
                n += 1
                if y[f] is None or abs(x[f] - y[f]) >= 0.02:
                    bad.append((k, f, x[f], y[f]))
        for f in ("map", "vc"):
            n += 1
            if x[f] != y[f]:
                bad.append((k, f, x[f], y[f]))
        if x.get("tint") is not None:
            n += 1
            if y.get("tint") is None or y["tint"] > 0.02:
                bad.append((k, "uTintAmt", x["tint"], y.get("tint")))
        for q, v in x["U"].items():
            n += 1
            w = y["U"].get(q)
            if w is None or max(abs(p - r) for p, r in zip(v, w)) >= 0.02:
                bad.append((k, "U." + q, v, w))
    return n, bad


def _pc_crop(pg):
    im = _Im.open(_io.BytesIO(pg.screenshot())).convert("RGB"); W, H = im.size
    return im.crop((W // 2 - 220, H // 2 - 200, W // 2 + 220, H // 2 + 200))


def _pc_mean(im):
    px = [p for p in (im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()) if not (abs(p[0] - 207) < 14 and abs(p[1] - 218) < 14 and abs(p[2] - 175) < 20)]
    px = px[len(px) // 6:]   # 上緣的名牌不算
    n = max(1, len(px))
    return [sum(p[i] for p in px) / n for i in range(3)]


def _pc_dark(im):
    """畫面中「焦黑」像素（三個通道都 < 115）的比例"""
    px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
    return sum(1 for p in px if max(p) < 115) / max(1, len(px))


def _pc_throw(pg, who, tries=3):
    """真滑鼠：把燒著的員工拎起來、丟進泳池。回傳是否進了水"""
    for t in range(tries):
        pg.evaluate("() => { const W = __world; W.fire.reset(); W.speed = 1; }")
        _pc_god(pg, 4.2, 37.2, 9)
        pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c._sootU && (c._sootU.value = 0); c.standAt(3.0, 39.4, Math.PI); c.busy = false; c.atDesk = false; c._fireImmuneUntil = 0; W.fire.ignite(c, 'poolcolor'); }", who)
        pg.evaluate("() => { __world.speed = 0.05 }"); pg.wait_for_timeout(700)
        xy = pg.evaluate("(id) => { const c = __world.chars.get(id); return c._sx > -900 ? [c._sx, c._sy] : null }", who)
        if not xy:
            continue
        k = pg.evaluate("(id) => { const W = __world, c = W.chars.get(id), cv = document.getElementById('cv'); return cv.clientHeight / (2 * Math.tan(W.camera.fov * Math.PI / 360) * c._sd) }", who)
        tgt = pg.evaluate("() => { const W = __world, v = new W.THREE.Vector3(5.2, 1.0, 35.0).project(W.camera); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight] }")
        sy = xy[1] + k * 0.45
        pg.mouse.move(xy[0], sy); pg.mouse.down(); pg.wait_for_timeout(800); pg.mouse.move(xy[0] + 8, sy - 8, steps=2); pg.wait_for_timeout(200)
        held = pg.evaluate("(id) => __world.chars.get(id).state", who) == "held"
        pg.mouse.move(tgt[0], tgt[1], steps=6); pg.wait_for_timeout(500); pg.mouse.up()
        pg.evaluate("() => { __world.speed = 1 }")
        if not held:
            continue
        for i in range(24):
            _pc_adv(pg, 0.25)
            if _pc_st(pg, who)["inw"]:
                return True
    return False


def _pc_pick(pg):
    """挑一位「焦黑真的疊得上去」的新角色與舊角色（有被補上焦黑著色器的材質）"""
    pg.evaluate("() => { const W = __world; for (const c of W.chars.values()) if (!c.spec.isCeo && !c.spec.pet && c.look.species !== 'flame') W.fire.ensureScorch(c); }")
    return pg.evaluate("""() => { const W = __world, res = { n: null, o: null };
      for (const c of W.chars.values()) { if (c.spec.isCeo || c.spec.pet || c.look.species === 'flame') continue; let k = 0; c.object3D.traverse(o => { if (!o.isMesh || !o.material) return; for (const m of Array.isArray(o.material) ? o.material : [o.material]) if (m.userData && m.userData._scOwner === c.spec.id) k++; });
        if (k < 4) continue; const key = c.newModel ? 'n' : 'o'; if (!res[key]) res[key] = c.spec.id; }
      return res; }""")


def t_office_poolcolor(b, base):
    _os.makedirs(_PC_SHOTS, exist_ok=True)
    c, pg, got = _pc_page(b, base)
    try:
        ok("泳池洗色：頁面載入", got)
        if not got:
            return
        pg.wait_for_timeout(600)
        pk = _pc_pick(pg)
        ok("泳池洗色：新、舊角色各挑到一位（材質有被補上焦黑著色器）", bool(pk["n"]) and bool(pk["o"]), pk)
        for kind, who in (("新角色", pk["n"]), ("舊角色", pk["o"])):
            if not who:
                continue
            tag = "new" if kind == "新角色" else "old"
            # ── 燒前
            pg.evaluate("() => { const W = __world; W.fire.reset(); W.speed = 1; }")
            pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c.standAt(3.0, 39.4, Math.PI); c.busy = false; c.atDesk = false; }", who); _pc_adv(pg, 1.5)
            pre = pg.evaluate(_PC_SNAP, who)
            _pc_god(pg, 3.0, 39.4, 3.5); im0 = _pc_crop(pg); im0.save(_os.path.join(_PC_SHOTS, f"{tag}_1_pre.png")); m0 = _pc_mean(im0)
            # ── 燒焦（在營火邊燒到焦黑、還沒進水）：截圖
            pg.evaluate("([id, x, z]) => { const W = __world, c = W.chars.get(id); c.standAt(x, z, Math.PI); c.busy = false; c._fireImmuneUntil = 0; W.fire.ignite(c, 'poolcolor'); }", [who, *_PC_NAT]); _pc_adv(pg, 4.6)
            _pc_god(pg, *pg.evaluate("(id) => { const p = __world.chars.get(id).object3D.position; return [p.x, p.z] }", who), 3.5)
            im1 = _pc_crop(pg); im1.save(_os.path.join(_PC_SHOTS, f"{tag}_2_burnt.png")); m1 = _pc_mean(im1)
            s1 = _pc_st(pg, who)
            ok(f"泳池洗色（{kind}）：燒焦後焦黑疊色 ≥ 0.8、畫面明顯變暗", s1["soot"] >= 0.8 and _pc_dark(im1) > _pc_dark(im0) + 0.08, (s1, round(_pc_dark(im0), 3), round(_pc_dark(im1), 3)))
            # ── 真滑鼠丟進泳池
            inw = _pc_throw(pg, who)
            ok(f"泳池洗色（{kind}）：用真滑鼠把燒著的員工拎起丟進泳池（進水）", inw, _pc_st(pg, who))
            if not inw:
                continue
            ev = pg.evaluate("(id) => { const W = __world; return { ex: W.fire.stats.extinguished || 0 } }", who)
            t_in = None; wash_t = None
            for i in range(60):
                _pc_adv(pg, 0.25)
                s = _pc_st(pg, who)
                if s["inw"] and t_in is None:
                    t_in = i
                if s["soot"] <= 0.02 and wash_t is None:
                    wash_t = (i - (t_in or 0)) * 0.25
                if s["s"] == "none" and wash_t is not None:
                    break
            ok(f"泳池洗色（{kind}）：焦黑在水裡洗掉（疊色 ≤ 0.02）、{wash_t} 秒內", wash_t is not None and wash_t <= 6, (wash_t, s))
            for i in range(80):
                if _pc_st(pg, who)["s"] == "none":
                    break
                _pc_adv(pg, 1)
            end = _pc_st(pg, who)
            ok(f"泳池洗色（{kind}）：恢復完成（狀態 none、疊色 0、餘燼 0）", end["s"] == "none" and end["soot"] == 0 and end["ember"] == 0, end)
            # ── 逐材質比對
            pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c.standAt(3.0, 39.4, Math.PI); c.busy = false; }", who); _pc_adv(pg, 1.5)
            post = pg.evaluate(_PC_SNAP, who)
            n, bad = _pc_diff(pre, post)
            ok(f"泳池洗色（{kind}）：出水恢復後逐材質顏色與燒前一致（{n} 項、差 < 0.02）", n > 20 and not bad, bad[:4])
            _pc_god(pg, 3.0, 39.4, 3.5); im2 = _pc_crop(pg); im2.save(_os.path.join(_PC_SHOTS, f"{tag}_3_after.png")); m2 = _pc_mean(im2)
            ok(f"泳池洗色（{kind}）：出水後畫面平均色與燒前接近（每通道差 < 20，姿勢不同的容許值）", max(abs(p - q) for p, q in zip(m0, m2)) < 20, ([round(x) for x in m0], [round(x) for x in m2]))
            # ── 自然熄火（不進泳池）
            pg.evaluate("() => { const W = __world; W.fire.reset(); W.speed = 1 }")
            pg.evaluate("([id, x, z]) => { const W = __world, c = W.chars.get(id); c.standAt(x, z, Math.PI); c.busy = false; c._fireImmuneUntil = 0; W.fire.ignite(c, 'poolcolor2'); }", [who, *_PC_NAT])
            for i in range(80):
                _pc_adv(pg, 2)
                if i > 3 and _pc_st(pg, who)["s"] == "none":
                    break
            nat = _pc_st(pg, who)
            pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c.standAt(3.0, 39.4, Math.PI); c.busy = false; }", who); _pc_adv(pg, 1.5)
            n2, bad2 = _pc_diff(pre, pg.evaluate(_PC_SNAP, who))
            ok(f"泳池洗色（{kind}）：自然熄火的恢復路徑也還原（狀態 none、{n2} 項材質顏色差 < 0.02）", nat["s"] == "none" and nat["soot"] == 0 and not bad2, (nat, bad2[:3]))
            # ── 冒煙愣著的人（已自然燒完）走進泳池 → 被洗乾淨
            pg.evaluate("() => { const W = __world; W.fire.reset(); W.speed = 1 }")
            pg.evaluate("([id, x, z]) => { const W = __world, c = W.chars.get(id); c.standAt(x, z, Math.PI); c.busy = false; c._fireImmuneUntil = 0; W.fire.ignite(c, 'poolcolor3'); }", [who, *_PC_NAT])
            for i in range(40):
                _pc_adv(pg, 0.5)
                if _pc_st(pg, who)["s"] == "smoldering":
                    break
            sm = _pc_st(pg, who)
            pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c.standAt(5.2, 35.0, 0); }", who)
            w3 = None
            for i in range(40):
                _pc_adv(pg, 0.25)
                if _pc_st(pg, who)["soot"] <= 0.02:
                    w3 = (i + 1) * 0.25; break
            ok(f"泳池洗色（{kind}）：燒完冒煙愣著的人走進泳池 → 被洗乾淨（{w3} 秒內疊色歸零、送出 washed）", sm["s"] == "smoldering" and sm["soot"] >= 0.8 and w3 is not None and w3 <= 5 and pg.evaluate("() => __world.fire.stats.washed || 0") >= 1, (sm, w3))
            for i in range(40):
                if _pc_st(pg, who)["s"] == "none":
                    break
                _pc_adv(pg, 1)
            pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c.standAt(3.0, 39.4, Math.PI); c.busy = false; }", who); _pc_adv(pg, 1.5)
            n3, bad3 = _pc_diff(pre, pg.evaluate(_PC_SNAP, who))
            ok(f"泳池洗色（{kind}）：洗乾淨之後材質顏色仍與燒前一致（{n3} 項）", not bad3 and _pc_st(pg, who)["s"] == "none", bad3[:3])
            # ── 洗過之後再燒一次：焦黑照樣疊得上去、照樣恢復（旗標沒有殘留）
            pg.evaluate("([id, x, z]) => { const W = __world, c = W.chars.get(id); c.standAt(x, z, Math.PI); c._fireImmuneUntil = 0; W.fire.ignite(c, 'poolcolor4'); }", [who, *_PC_NAT]); _pc_adv(pg, 4.6)
            again = _pc_st(pg, who)
            ok(f"泳池洗色（{kind}）：洗過之後再燒一次，焦黑照樣疊上去（≥ 0.8）", again["soot"] >= 0.8 and again["s"] in ("burning", "smoldering"), again)
            for i in range(80):
                _pc_adv(pg, 2)
                if _pc_st(pg, who)["s"] == "none":
                    break
            ok(f"泳池洗色（{kind}）：再燒一次後也恢復到 none、疊色 0", _pc_st(pg, who)["s"] == "none" and _pc_st(pg, who)["soot"] == 0, _pc_st(pg, who))
        ok("泳池洗色：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
        print("  截圖：", _PC_SHOTS)
    finally:
        c.close()


register("辦公室泳池洗色", lambda pg, b, base, code: t_office_poolcolor(b, base))
