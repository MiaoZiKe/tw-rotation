# 驗收段落「辦公室物理互動」（2026-11-14 擁有者：丟人物桌椅會被打翻；碰到火會燒起來、燒焦，過一陣子主動復原）
#   · 丟角色撞椅子：椅子位置與傾角改變（翻倒）、角色減速；等一陣子後椅子回到原位（誤差 < 5 公分、角度 < 5 度），
#     過程有同事走過來扶起、沒人時自己彈回，每個模擬步的位移有上限（不瞬移）；舊做法與新做法的角色都測
#   · 盆栽、立燈、桌上杯子：撞到會倒／滾／飛，之後復原；立燈倒下時光暈與地面光斑跟著移動，扶起後恢復
#   · 角色撞牆：反彈、送出 knocked／bump 事件、鏡頭微晃
#   · 營火：火焰多舌、白天看得到、光斑與火苗同一個時間函數（跟著跳）、有火星與煙
#   · 丟進營火：burned 事件、焦黑 > 0、離開火源、extinguished、30～60 秒後 recovered 且焦黑回到 0；小燭（火焰角色）不會燒
#   · 焦黑在畫面上真的變暗（截圖亮度），新舊兩種角色都驗
#   · 整修模式：翻倒的東西立刻歸位；手動擺放的位置是新的原位
#   · 真人操作：滑鼠按住角色 → 拖 → 放開 → 角色被拎起再被丟出；1280 與 390 寬度都測
#   · 繪製次數增量 ≤ +10（對照 ?nophys=1）；無主控台錯誤
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

import io as _io
from PIL import Image as _Im


def _ph_lum(png, box):
    im = _Im.open(_io.BytesIO(png)).convert("L").crop(box)
    d = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
    return sum(d) / max(1, len(d))


_PH_HELPERS = """() => {
  const W = __world, P = W.phys, F = W.fire; const T = window.__T = {};
  T.ev = []; const oe = W.emit; W.emit = function (a, b, d) { T.ev.push({ t: +W.time.toFixed(2), type: a, id: b, d: d || null }); return oe ? oe.apply(W, arguments) : undefined; };
  T.evs = (type, id) => T.ev.filter(e => e.type === type && (id == null || e.id === id));
  T.spd = c => { if (c.newModel) { const b = c.inner.ctl.body; return Math.hypot(b.vx, b.vz) * c.scale; } return Math.hypot(c.inner.vel.x, c.inner.vel.z) * c.scale; };
  T.vel = c => { if (c.newModel) { const b = c.inner.ctl.body; return [b.vx * c.scale, b.vz * c.scale]; } return [c.inner.vel.x * c.scale, c.inner.vel.z * c.scale]; };
  T.oldChar = () => [...W.chars.values()].find(c => !c.newModel && !c.spec.isCeo && c.look.species === 'bird');
  T.newChar = () => [...W.chars.values()].find(c => c.newModel && !c.spec.isCeo);
  T.flameChar = () => [...W.chars.values()].find(c => c.look.species === 'flame');
  T.place = (c, x, z, face) => { c.busy = true; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.stop(false); c._drive = null; c.standAt(x, z, face || 0); W.advance(0.3); };   // script／job 加一：把導演「被丟之後走回座位」的流程作廢，不要跟測試搶角色
  T.throwTo = (c, tx, tz, v, vy) => { const p = c.object3D.position, dx = tx - p.x, dz = tz - p.z, d = Math.hypot(dx, dz); P.throwChar(c, dx / d * v, vy, dz / d * v); };
  T.step = async (sec) => { await W.advanceAsync(sec, 1 / 30); };
  T.settle = async c => { await T.until(() => !c._held && (c.newModel ? !['tumble', 'air', 'held', 'recover', 'land'].includes(c.inner.ctl.state) : c.inner.mode === 'normal'), 20); await T.step(0.6); };   // 等被丟的角色落地站穩
  T.freeChair = () => P.props.filter(p => p.kind === 'chair' && !p.locked && p.id.startsWith('meeting_table') && p.mode === 'home').sort((a, b) => P.homePos(b).z - P.homePos(a).z)[0];   // 最靠南的那張（正對大門缺口，丟得進去）
  T.angErr = p => Math.abs(Math.atan2(Math.sin(p.dyaw), Math.cos(p.dyaw)));
  T.calls = async () => { await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r)))); return W.stats.calls; };
  T.until = async (fn, maxSec) => { for (let t = 0; t < maxSec; t += 1 / 30) { if (fn()) return t; await W.advanceAsync(1 / 30, 1 / 30); } return -1; };
  return 1;
}"""

# 丟角色撞椅子，直到椅子回到原位。回傳整個過程的量測
_PH_CHAIR = """async ([who, nobody]) => {
  const W = __world, P = W.phys, T = __T; P.restoreAll(true); const c = who === 'new' ? T.newChar() : T.oldChar(); await T.settle(c); const ch = T.freeChair(); const hp = P.homePos(ch);
  if (nobody) for (const o of W.chars.values()) if (o !== c) o.busy = true;
  T.place(c, hp.x, hp.z + 2.8, Math.PI); P.stats.maxStep = 0; const ev0 = T.ev.length, st0 = { ...P.stats };
  T.throwTo(c, hp.x, hp.z, 9.0, 1.0);
  let vBefore = 0, vAfter = 1e9, hitT = -1, maxTh = 0, left = false, charMin = 1e9, out = {};
  for (let i = 0; i < 150; i++) {
    const s0 = T.spd(c); await W.advanceAsync(1 / 30, 1 / 30);
    if (ch.mode !== 'home' && !left) { left = true; hitT = i; vBefore = Math.max(vBefore, s0); }
    if (left) { vAfter = Math.min(vAfter, T.spd(c)); maxTh = Math.max(maxTh, ch.th); }
    if (!left) vBefore = Math.max(vBefore, s0);
  }
  out.moved = Math.hypot(ch.x - hp.x, ch.z - hp.z); out.th = maxTh; out.vBefore = vBefore; out.vAfter = vAfter; out.hit = hitT; out.mode1 = ch.mode;
  out.toppled = T.evs('toppled', ch.id).length; out.spotBlocked = ch.spot ? ch.spot.blocked : null;
  // 等復原：記錄同事有沒有走近、最近距離
  let hmin = 1e9, hname = null, tRestore = -1, sawCarry = false;
  for (let i = 0; i < 30 * 90; i++) {
    await W.advanceAsync(1 / 30, 1 / 30);
    if (ch.helper) { hname = ch.helper.spec.id; const hpp = ch.helper.object3D.position; hmin = Math.min(hmin, Math.hypot(hpp.x - ch.x, hpp.z - ch.z)); }
    if (ch.mode === 'carry') sawCarry = true;
    if (ch.mode === 'home') { tRestore = i / 30; break; }
  }
  const b = P.homePos(ch); out.err = Math.hypot(ch.x - b.x, ch.z - b.z); out.angErr = T.angErr(ch); out.thEnd = ch.th; out.tRestore = tRestore; out.mode2 = ch.mode;
  out.helper = hname; out.hmin = hmin; out.maxStep = P.stats.maxStep; out.helped = P.stats.helped - st0.helped; out.selfRet = P.stats.selfReturn - st0.selfReturn;
  out.righted = T.evs('righted', ch.id).length; out.id = ch.id; out.blockedEnd = ch.spot ? ch.spot.blocked : null; out.pos = [ch.obj ? 1 : 0];
  await T.step(8);                                                          // 讓幫忙的同事走回座位再放開忙碌旗標
  for (const o of W.chars.values()) if (o !== c) o.busy = false;
  P.restoreAll(true);
  return out;
}"""


def t_office_physics(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    errs = []

    def mk(vw, vh, touch=False):
        c = b.new_context(viewport={"width": vw, "height": vh}, has_touch=touch, is_mobile=touch)
        pg = c.new_page()
        pg.set_default_timeout(180000)
        pg.on("pageerror", lambda e: errs.append("pageerror:" + str(e)[:200]))
        pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
        return c, pg

    def load(pg, extra=""):
        pg.goto(root + "/office/world.html?ambient=0&q=low&pr=0.6&sim=1" + extra, wait_until="domcontentloaded")
        okk = wait_until(pg, "() => window.__world && window.__world.ready", 120000)
        if okk:
            pg.wait_for_timeout(500)
        return okk

    # ───── 對照組：關掉物理與火焰量繪製次數（白天、夜晚）─────
    c0, p0 = mk(1280, 800)
    base_calls = {}
    try:
        ok("物理段：對照頁（nophys=1）載入", load(p0, "&nophys=1"))
        for k in ("day", "night"):
            p0.evaluate("(k) => { __world.daytime.set(k); __world.speed = 0.001; }", k)
            p0.wait_for_timeout(500)
            base_calls[k] = p0.evaluate("""async () => { await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r)))); return __world.stats.calls; }""")
    finally:
        c0.close()

    c1, pg = mk(1280, 800)
    try:
        ok("物理段：場景載入", load(pg))
        pg.evaluate("() => { __world.speed = 0.001; __world.daytime.set('day'); }")
        pg.evaluate(_PH_HELPERS)
        info = pg.evaluate("""() => { const P = __world.phys, k = {}; P.props.forEach(p => k[p.kind] = (k[p.kind] || 0) + 1); return { k, n: P.props.length, statics: P.statics.length, bus: typeof __world.emit === 'function' && typeof __world.on === 'function' }; }""")
        ok("物理：可動物件就位（椅子 %d、盆栽 %d＋%d、立燈 %d、懶骨頭 %d、杯子 %d、書 %d、球 %d）" % (info["k"].get("chair", 0), info["k"].get("plant", 0), info["k"].get("plant_big", 0), info["k"].get("lamp", 0), info["k"].get("beanbag", 0), info["k"].get("mug", 0), info["k"].get("book", 0), info["k"].get("ball", 0)),
           info["k"].get("chair", 0) >= 40 and info["k"].get("plant", 0) >= 20 and info["k"].get("lamp", 0) >= 3 and info["k"].get("beanbag", 0) >= 3 and info["k"].get("mug", 0) >= 20, info)
        ok("物理：事件匯流排 W.emit／W.on 可用", info["bus"])
        calls_day = pg.evaluate("() => __T.calls()")
        pg.evaluate("() => { __world.daytime.set('night'); }")
        pg.wait_for_timeout(500)
        calls_night = pg.evaluate("() => __T.calls()")
        pg.evaluate("() => { __world.daytime.set('day'); }")

        # ───── 丟角色撞椅子（舊做法的角色：鳥）─────
        r = pg.evaluate(_PH_CHAIR, ["old", False])
        ok("丟人撞椅子（舊角色）：椅子被撞離原位（位移 %.2f 公尺）" % r["moved"], r["hit"] >= 0, r)
        ok("丟人撞椅子（舊角色）：椅子翻倒（傾角 %.2f 弧度 ≥ 0.8）" % r["th"], r["th"] >= 0.8, r)
        ok("丟人撞椅子（舊角色）：角色減速（%.1f → %.1f 公尺/秒，剩 ≤ 60%%）" % (r["vBefore"], r["vAfter"]), r["vBefore"] > 3 and r["vAfter"] <= r["vBefore"] * 0.6, r)
        ok("丟人撞椅子（舊角色）：送出 toppled 事件，座位標成不可用", r["toppled"] >= 1 and r["spotBlocked"] in (True, None), r)
        ok("丟人撞椅子（舊角色）：過一陣子椅子回到原位（誤差 %.3f 公尺 < 0.05、角度 %.1f 度 < 5，花 %.0f 秒）" % (r["err"], r["angErr"] * 57.3, r["tRestore"]),
           r["mode2"] == "home" and r["err"] < 0.05 and r["angErr"] < 0.0873 and abs(r["thEnd"]) < 0.0873 and 15 <= r["tRestore"] <= 75, r)
        ok("丟人撞椅子（舊角色）：同事走過來扶起（%s，最近 %.2f 公尺）" % (r["helper"], r["hmin"]), r["helper"] is not None and r["hmin"] < 1.3 and r["helped"] >= 1, r)
        ok("丟人撞椅子（舊角色）：復原過程沒有瞬移（每個模擬步位移最大 %.3f 公尺 ≤ 0.12）" % r["maxStep"], r["maxStep"] <= 0.12, r)
        ok("丟人撞椅子（舊角色）：送出 righted 事件、座位恢復可用", r["righted"] >= 1 and not r["blockedEnd"], r)

        # ───── 新做法的角色（糰糰等）：沒有同事能幫忙，椅子自己彈回去 ─────
        r2 = pg.evaluate(_PH_CHAIR, ["new", True])
        ok("丟人撞椅子（新角色）：椅子翻倒（傾角 %.2f、位移 %.2f）" % (r2["th"], r2["moved"]), r2["th"] >= 0.8 and r2["hit"] >= 0, r2)
        ok("丟人撞椅子（新角色）：角色減速（%.1f → %.1f）" % (r2["vBefore"], r2["vAfter"]), r2["vBefore"] > 3 and r2["vAfter"] <= r2["vBefore"] * 0.6, r2)
        ok("沒人幫忙時椅子自己彈回原位（誤差 %.3f 公尺、角度 %.1f 度，花 %.0f 秒、自己回去 %d 次）" % (r2["err"], r2["angErr"] * 57.3, r2["tRestore"], r2["selfRet"]),
           r2["mode2"] == "home" and r2["err"] < 0.05 and r2["angErr"] < 0.0873 and r2["selfRet"] >= 1 and r2["helper"] is None, r2)
        ok("自己彈回：沒有瞬移（每步最大位移 %.3f 公尺 ≤ 0.12）" % r2["maxStep"], r2["maxStep"] <= 0.12, r2)

        # ───── 盆栽、立燈、杯子 ─────
        r3 = pg.evaluate("""async () => {
          const W = __world, P = W.phys, T = __T, out = {};
          for (const o of W.chars.values()) o.busy = true;                     // 不要同事幫忙，等它自己復原（比較快、也驗自己彈回）
          // 盆栽
          const pl = P.nearest('plant', 20, 15), pb = P.homePos(pl); P.knock(pl, pb.x - 1, pb.z, 5.0, 5.5);
          await T.step(1.6); out.plant = { mode: pl.mode, th: pl.th, moved: Math.hypot(pl.x - pb.x, pl.z - pb.z), rho: pl.rho };
          const t1 = await T.until(() => pl.mode === 'home', 90); out.plantBack = { t: t1, err: Math.hypot(pl.x - pb.x, pl.z - pb.z), th: pl.th, y: pl.obj ? pl.obj.position.y : 0, rot: [pl.obj.rotation.x, pl.obj.rotation.z] };
          // 立燈（夜晚看光）
          __world.daytime.set('night'); await T.step(0.2); await new Promise(r => setTimeout(r, 600));
          const lp = P.props.find(p => p.kind === 'lamp'), lb = P.homePos(lp), g0 = P.lampGlow(lp.inst.f.id), s0 = P.lampSpots(), i0 = P.props.filter(p => p.kind === 'lamp').indexOf(lp);
          P.knock(lp, lb.x - 1, lb.z, 4.0, 5.5); await T.step(2.0);
          const g1 = P.lampGlow(lp.inst.f.id), s1 = P.lampSpots();
          out.lamp = { mode: lp.mode, th: lp.th, g0, g1, s0: s0[i0], s1: s1[i0], moved: Math.hypot(lp.x - lb.x, lp.z - lb.z) };
          const t2 = await T.until(() => lp.mode === 'home', 90); await T.step(0.4);
          const g2 = P.lampGlow(lp.inst.f.id), s2 = P.lampSpots();
          out.lampBack = { t: t2, g2, s2: s2[i0], err: Math.hypot(lp.x - lb.x, lp.z - lb.z), th: lp.th };
          __world.daytime.set('day');
          // 桌上杯子
          const mug = P.props.find(p => p.kind === 'mug' && p.mode === 'home'), mb = P.homePos(mug), y0 = mug.baseY; let ymax = 0, ymin = 9;
          P.knock(mug, mb.x - 0.4, mb.z, 3.0, 3.0);
          for (let i = 0; i < 60; i++) { await T.step(1 / 30); ymax = Math.max(ymax, mug.y); ymin = Math.min(ymin, mug.y); }
          out.mug = { y0, ymax, ymin, mode: mug.mode, moved: Math.hypot(mug.x - mb.x, mug.z - mb.z), det: mug.detached };
          const t3 = await T.until(() => mug.mode === 'home', 90);
          out.mugBack = { t: t3, err: Math.hypot(mug.x - mb.x, mug.z - mb.z), y: mug.y, det: mug.detached };
          // 懶骨頭：不會翻，只會滑
          const bb = P.props.find(p => p.kind === 'beanbag'), bh = P.homePos(bb); P.knock(bb, bh.x - 1, bh.z, 5.0, 5.5); await T.step(1.2);
          out.bean = { mode: bb.mode, th: bb.th, moved: Math.hypot(bb.x - bh.x, bb.z - bh.z) };
          const t4 = await T.until(() => bb.mode === 'home', 90); out.beanBack = { t: t4, err: Math.hypot(bb.x - bh.x, bb.z - bh.z) };
          for (const o of W.chars.values()) o.busy = false;
          out.maxStep = P.stats.maxStep;
          return out;
        }""")
        ok("盆栽：被撞後翻倒（傾角 %.2f、位移 %.2f 公尺）並滾動" % (r3["plant"]["th"], r3["plant"]["moved"]), r3["plant"]["th"] >= 1.2 and r3["plant"]["moved"] > 0.15, r3["plant"])
        ok("盆栽：復原回到原位（誤差 %.3f、站直、花 %.0f 秒）" % (r3["plantBack"]["err"], r3["plantBack"]["t"]), r3["plantBack"]["t"] > 0 and r3["plantBack"]["err"] < 0.05 and abs(r3["plantBack"]["rot"][0]) < 1e-3 and abs(r3["plantBack"]["rot"][1]) < 1e-3, r3["plantBack"])
        lamp = r3["lamp"]
        ok("立燈：被撞後倒下（傾角 %.2f）" % lamp["th"], lamp["th"] >= 1.2, lamp)
        ok("立燈倒下：光暈點跟著燈罩移動（高度 %.2f → %.2f、水平位移 %.2f 公尺）" % (lamp["g0"]["y"], lamp["g1"]["y"], ((lamp["g1"]["x"] - lamp["g0"]["x"]) ** 2 + (lamp["g1"]["z"] - lamp["g0"]["z"]) ** 2) ** 0.5),
           lamp["g1"]["y"] < lamp["g0"]["y"] - 0.7 and ((lamp["g1"]["x"] - lamp["g0"]["x"]) ** 2 + (lamp["g1"]["z"] - lamp["g0"]["z"]) ** 2) ** 0.5 > 0.4, lamp)
        ok("立燈倒下：地面光斑跟著移動並縮小（半徑 %.2f → %.2f，中心移動 %.2f 公尺）" % (lamp["s0"]["r"], lamp["s1"]["r"], ((lamp["s1"]["x"] - lamp["s0"]["x"]) ** 2 + (lamp["s1"]["z"] - lamp["s0"]["z"]) ** 2) ** 0.5),
           lamp["s1"]["r"] < lamp["s0"]["r"] * 0.75 and ((lamp["s1"]["x"] - lamp["s0"]["x"]) ** 2 + (lamp["s1"]["z"] - lamp["s0"]["z"]) ** 2) ** 0.5 > 0.3, lamp)
        lb2 = r3["lampBack"]
        ok("立燈扶起後：光暈與地面光斑回到原位（光暈高度 %.2f、光斑半徑 %.2f）" % (lb2["g2"]["y"], lb2["s2"]["r"]), lb2["t"] > 0 and abs(lb2["g2"]["y"] - 1.35) < 0.02 and abs(lb2["s2"]["r"] - lamp["s0"]["r"]) < 0.02 and abs(lb2["s2"]["x"] - lamp["s0"]["x"]) < 0.02 and lb2["err"] < 0.05, lb2)
        mug = r3["mug"]
        ok("桌上杯子：被撞後飛離桌面落地（高度 %.2f → 最高 %.2f → 最低 %.2f），被拆成獨立零件" % (mug["y0"], mug["ymax"], mug["ymin"]), mug["ymax"] > mug["y0"] + 0.05 and mug["ymin"] < 0.1 and mug["moved"] > 0.2, mug)
        ok("桌上杯子：復原回到桌面原位（誤差 %.3f、高度 %.2f，貼回合併網格）" % (r3["mugBack"]["err"], r3["mugBack"]["y"]), r3["mugBack"]["t"] > 0 and r3["mugBack"]["err"] < 0.03 and not r3["mugBack"]["det"], r3["mugBack"])
        ok("懶骨頭：被撞後滑動、不會翻（傾角 %.2f、位移 %.2f），之後滑回原位" % (r3["bean"]["th"], r3["bean"]["moved"]), r3["bean"]["th"] == 0 and r3["bean"]["moved"] > 0.1 and r3["beanBack"]["t"] > 0 and r3["beanBack"]["err"] < 0.05, r3)
        ok("盆栽、立燈、杯子、懶骨頭的復原都沒有瞬移（每步最大位移 %.3f ≤ 0.12）" % r3["maxStep"], r3["maxStep"] <= 0.12, r3["maxStep"])

        # ───── 撞牆：反彈、事件、鏡頭微晃 ─────
        r4 = pg.evaluate("""async () => {
          const W = __world, P = W.phys, T = __T, c = T.oldChar(); await T.settle(c); T.place(c, 10.0, 10.8, Math.PI); const w0 = P.stats.wallHits; const ev0 = T.ev.length;
          T.throwTo(c, 10.0, 8.0, 7.5, 0.6); let vzBefore = 0, vzAfter = 0, shake = 0, hit = false, zmin = 99;
          for (let i = 0; i < 40; i++) { const v0 = T.vel(c)[1]; await W.advanceAsync(1 / 30, 1 / 30); const v1 = T.vel(c)[1]; zmin = Math.min(zmin, c.object3D.position.z); if (!hit && v0 < -2 && v1 > v0 + 2) { hit = true; vzBefore = v0; vzAfter = v1; shake = P.shake; } }
          await T.settle(c);
          return { hit, vzBefore, vzAfter, shake, walls: P.stats.wallHits - w0, zmin, knocked: T.evs('knocked', c.spec.id).length, bump: T.ev.slice(ev0).filter(e => e.type === 'bump').length };
        }""")
        ok("角色撞牆：反彈（vz %.1f → %.1f）、沒有穿牆（最近 z %.2f）" % (r4["vzBefore"], r4["vzAfter"], r4["zmin"]), r4["hit"] and r4["vzAfter"] > 0 and r4["zmin"] > 9.0, r4)
        ok("角色撞牆：送出 knocked 與 bump 事件、鏡頭微晃（%.3f）" % r4["shake"], r4["knocked"] >= 1 and r4["bump"] >= 1 and r4["shake"] > 0.01, r4)

        # ───── 跑步撞椅子（新舊角色）─────
        for who, nm in (("old", "舊"), ("new", "新")):
            r5 = pg.evaluate("""async (who) => {
              const W = __world, P = W.phys, T = __T, c = who === 'new' ? T.newChar() : T.oldChar(); for (const o of W.chars.values()) if (o !== c) o.busy = true;
              P.restoreAll(true); await T.settle(c); const ch = T.freeChair(); const hp = P.homePos(ch); T.place(c, hp.x, hp.z + 3.6, Math.PI);
              let before = 0, after = 1e9, left = false, tumbled = false;
              for (let i = 0; i < 90; i++) { c.drive(0, -4.6, 0, -1); const s0 = T.spd(c); await W.advanceAsync(1 / 30, 1 / 30); if (!left) before = Math.max(before, s0); if (ch.mode !== 'home') { left = true; } if (left) after = Math.min(after, T.spd(c)); if (c.newModel ? c.inner.ctl.state === 'tumble' : c.inner.mode === 'tumble') tumbled = true; }
              c.drive(null); const out = { left, th: ch.th, before, after, tumbled, topple: T.evs('toppled', ch.id).length };
              P.restoreAll(true); for (const o of W.chars.values()) o.busy = false; c.stop(false); return out;
            }""", who)
            ok("跑步撞椅子（%s角色）：椅子被撞開、翻倒（傾角 %.2f），角色減速（%.1f → %.1f）、被撞得翻滾（%s）" % (nm, r5["th"], r5["before"], r5["after"], r5["tumbled"]), r5["left"] and r5["th"] >= 0.8 and r5["before"] > 2.4 and r5["after"] < r5["before"] * 0.75 and (r5["tumbled"] or who == "new"), r5)

        # ───── 營火：火焰、光斑對齊、火星與煙 ─────
        r6 = pg.evaluate("""async () => {
          const W = __world, F = W.fire, O = W.outside; __world.daytime.set('day'); await __T.step(2.5); await new Promise(r => setTimeout(r, 500));
          const ks = []; for (let i = 0; i < 6; i++) { await new Promise(r => setTimeout(r, 120)); ks.push(+F.flame.material.uniforms.uK.value.toFixed(3)); }
          const dtv = []; const oL = W.daytime.outL; oL.k = 1; for (const tt of [1000, 1400, 2100, 3300]) { W.daytime.flicker(tt); dtv.push([+oL.fire.material.opacity.toFixed(4), +W.fireFlick(tt).toFixed(4)]); } oL.k = 0;
          return { has: !!F.flame && F.flame.visible, oldGone: !F.flame.parent ? 'x' : 'ok', tris: F.flame.geometry.index.count / 3, ks, dtv, live: F.pools.PA.live + F.pools.PS.live, spark: F.pools.PA.live, smoke: F.pools.PS.live, glow: oL.fire ? oL.fire.visible : null, uniform: Object.keys(F.flame.material.uniforms) };
        }""")
        ok("營火：多舌火焰網格（%d 個三角面，一個合併網格）白天也看得到" % r6["tris"], r6["has"] and r6["tris"] > 300, r6)
        ok("營火：火苗高度／亮度隨時間跳動（取樣 %s）" % r6["ks"], len(set(r6["ks"])) >= 3, r6["ks"])
        ok("營火：光斑亮度與火苗用同一個時間函數（光斑／火苗比例一致）", all(abs(a - bb) < 1e-3 for a, bb in r6["dtv"]) and len({round(a, 3) for a, bb in r6["dtv"]}) >= 3, r6["dtv"])
        ok("營火：有火星與灰煙粒子往上飄（火星 %d、煙 %d）" % (r6["spark"], r6["smoke"]), r6["spark"] >= 5 and r6["smoke"] >= 2, r6)
        ok("營火：白天地面光斑不顯示（光斑弱）", r6["glow"] in (False, None), r6)

        # ───── 丟進營火：舊做法的鳥 ─────
        def fire_round(who):
            return pg.evaluate("""async (who) => {
              const W = __world, F = W.fire, T = __T; __world.daytime.set('dusk'); const c = who === 'new' ? T.newChar() : T.oldChar(); const id = c.spec.id;
              await T.settle(c); T.place(c, 30.2, 34.3, 0); const ev0 = T.ev.length; const cx = 30.2, cz = 36.6;
              T.throwTo(c, cx, cz, 4.5, 1.5); const o = {}; let dmax = 0, burnT = -1, sootMax = 0, dist0 = 9, live = 0;
              for (let i = 0; i < 30 * 140; i++) {
                await W.advanceAsync(1 / 30, 1 / 30); const s = F.stateOf(c), p = c.object3D.position, d = Math.hypot(p.x - cx, p.z - cz);
                if (s.state === 'burning') { if (burnT < 0) { burnT = W.time; dist0 = d; o.sootAtStart = F.scorch(c); } dmax = Math.max(dmax, d); live = Math.max(live, F.pools.PA.live); }
                sootMax = Math.max(sootMax, F.scorch(c)); if (s.state === 'none' && burnT > 0 && W.time > burnT + 5) break;
              }
              const E = n => T.ev.slice(ev0).filter(e => e.type === n && e.id === id);
              o.burned = E('burned').length; o.ext = E('extinguished').length; o.rec = E('recovered').length; o.tBurn = E('burned')[0] && E('burned')[0].t; o.tExt = E('extinguished')[0] && E('extinguished')[0].t; o.tRec = E('recovered')[0] && E('recovered')[0].t;
              o.sootMax = sootMax; o.dmax = dmax; o.sootEnd = F.scorch(c); o.state = F.stateOf(c).state; o.recoverAt = F.stateOf(c).recoverAt; o.patched = !!c._scorchPatched; o.live = live; o.id = id; o.dist0 = dist0;
              return o;
            }""", who)

        ok("焦黑著色器：新舊角色都先補好（背景補、不卡）", pg.evaluate("() => [__T.oldChar(), __T.newChar()].every(c => (__world.fire.ensureScorch(c), c._scorchPatched))"))
        r7 = fire_round("old")
        ok("丟進營火（舊角色）：發出 burned 事件、進入燃燒（t=%.1f）" % (r7["tBurn"] or -1), r7["burned"] == 1 and r7["tBurn"] is not None, r7)
        ok("丟進營火（舊角色）：身上有火舌粒子、離開火源（最遠 %.1f 公尺 ≥ 2.4）" % r7["dmax"], r7["live"] >= 8 and r7["dmax"] >= 2.4, r7)
        ok("丟進營火（舊角色）：身體焦黑 > 0（最大 %.2f ≥ 0.8）、火熄滅發出 extinguished（%.1f 秒後）" % (r7["sootMax"], (r7["tExt"] or 0) - (r7["tBurn"] or 0)), r7["sootMax"] >= 0.8 and r7["ext"] == 1 and 2.5 <= (r7["tExt"] or 0) - (r7["tBurn"] or 0) <= 9, r7)
        ok("丟進營火（舊角色）：熄火後 30～60 秒（%.0f）內開始恢復、焦黑回到 0、發出 recovered（熄火後 %.0f 秒）" % (r7["recoverAt"] or -1, (r7["tRec"] or 0) - (r7["tExt"] or 0)),
           r7["rec"] == 1 and r7["sootEnd"] == 0 and 30 <= (r7["recoverAt"] or 0) <= 60 and 30 <= (r7["tRec"] or 0) - (r7["tExt"] or 0) <= 85, r7)
        r8 = fire_round("new")
        ok("丟進營火（新角色）：burned → 焦黑 %.2f → extinguished → recovered，焦黑回到 %.2f，離火最遠 %.1f 公尺" % (r8["sootMax"], r8["sootEnd"], r8["dmax"]),
           r8["burned"] == 1 and r8["ext"] == 1 and r8["rec"] == 1 and r8["sootMax"] >= 0.8 and r8["sootEnd"] == 0 and r8["dmax"] >= 2.4, r8)
        r9 = pg.evaluate("""async () => {
          const W = __world, F = W.fire, T = __T, c = T.flameChar(); T.place(c, 30.2, 34.3, 0); const ev0 = T.ev.length; T.throwTo(c, 30.2, 36.6, 4.5, 1.5);
          for (let i = 0; i < 30 * 8; i++) await W.advanceAsync(1 / 30, 1 / 30);
          return { burned: T.ev.slice(ev0).filter(e => e.type === 'burned' && e.id === c.spec.id).length, state: F.stateOf(c).state, soot: F.scorch(c), id: c.spec.id };
        }""")
        ok("小燭（火焰角色）丟進營火：不會燃燒、沒有焦黑", r9["burned"] == 0 and r9["state"] == "none" and r9["soot"] == 0, r9)

        # ───── 焦黑在畫面上真的變暗（截圖亮度）─────
        for who, nm in (("old", "舊"), ("new", "新")):
            pg.evaluate("""(who) => { const W = __world, T = __T, c = who === 'new' ? T.newChar() : T.oldChar(); T.place(c, who === 'new' ? 15.2 : 13.0, who === 'new' ? 11.6 : 10.9, Math.PI); W.daytime.set('day'); W.fire.ensureScorch(c); window.__pc = c; W.advance(0.5);
              W.view.mode = 'god'; W.view.char = null; W.view.tween = null; const p = c.object3D.position; W.controls.target.set(p.x, 0.5, p.z); W.camera.position.set(p.x + 0.4, 1.6, p.z + 3.0); W.camera.fov = 30; W.camera.updateProjectionMatrix(); W.controls.update(); c._sootU.value = 0; }""", who)
            pg.wait_for_timeout(900)
            box = pg.evaluate("() => { const W = __world, c = window.__pc, b3 = new W.THREE.Box3().setFromObject(c.object3D), v = b3.getCenter(new W.THREE.Vector3()).project(W.camera); return [Math.round((v.x + 1) / 2 * innerWidth), Math.round((1 - v.y) / 2 * innerHeight)]; }")
            crop = (box[0] - 28, box[1] - 28, box[0] + 28, box[1] + 28)
            l0 = _ph_lum(pg.screenshot(), crop)
            pg.evaluate("() => { window.__pc._sootU.value = 0.9; }")
            pg.wait_for_timeout(700)
            l1 = _ph_lum(pg.screenshot(), crop)
            pg.evaluate("() => { window.__pc._sootU.value = 0; window.__pc.busy = false; }")
            ok("焦黑畫面（%s角色）：身體區域平均亮度 %.0f → %.0f（變暗 ≥ 25%%）" % (nm, l0, l1), l1 <= l0 * 0.75, (l0, l1, box))

        # ───── 整修模式：翻倒的東西立刻歸位、手動擺放的位置是新的原位 ─────
        r10 = pg.evaluate("""async () => {
          const W = __world, P = W.phys, T = __T; for (const o of W.chars.values()) o.busy = true;
          const ch = T.freeChair(), hp = P.homePos(ch); P.knock(ch, hp.x, hp.z + 1, 6.0, 5.5); await T.step(1.0); const before = ch.mode;
          W.toggleEdit(); await T.step(0.3); const during = ch.mode, th = ch.th; const pl = P.nearest('plant_big', 20, 15), inst = pl.inst;
          inst.f.x += 1.0; W.place(inst); W.respot(); const nb = P.homePos(pl); W.toggleEdit(); await T.step(0.2);       // 搬到新位置、離開整修模式
          P.knock(pl, nb.x - 1, nb.z, 6.0, 5.5); await T.step(0.6); const tipped = pl.th;
          const t = await T.until(() => pl.mode === 'home', 100);
          const out = { before, during, th, newHome: nb.x, err: Math.hypot(pl.x - nb.x, pl.z - nb.z), tipped, t, edit: W.edit.on };
          inst.f.x -= 1.0; W.place(inst); W.respot(); for (const o of W.chars.values()) o.busy = false; return out;
        }""")
        ok("整修模式：進入時翻倒的椅子立刻歸位（之前 %s → 之後 %s）" % (r10["before"], r10["during"]), r10["before"] != "home" and r10["during"] == "home" and r10["th"] == 0, r10)
        ok("整修模式：手動擺放的位置是新的原位（盆栽搬到 x=%.2f，撞翻後回到那裡，誤差 %.3f）" % (r10["newHome"], r10["err"]), r10["tipped"] > 0.5 and r10["t"] > 0 and r10["err"] < 0.05, r10)

        # ───── 繪製次數（對照 nophys=1；閒置的增量在剛載入、場景還沒動過時量；暫時性的增量用同一頁前後相減）─────
        pg.evaluate("() => { __world.fire.reset(); __world.phys.restoreAll(true); __world.daytime.set('night'); }")
        pg.wait_for_timeout(600)
        late_night = pg.evaluate("() => __T.calls()")
        worst = pg.evaluate("""async () => {
          const W = __world, P = W.phys, F = W.fire, T = __T; for (const o of W.chars.values()) o.busy = true;
          const ch = T.freeChair(); P.knock(ch, 0, 0, 6.0, 5.5); const mugs = P.props.filter(p => p.kind === 'mug' && p.mode === 'home').slice(0, 3); mugs.forEach(m => P.knock(m, 0, 0, 3, 3));
          const lp = P.props.find(p => p.kind === 'lamp'); P.knock(lp, 0, 0, 4, 5.5); const c = T.oldChar(); c.busy = true; F.ignite(c, 'test'); await T.step(1.5);
          const calls = await T.calls(); const det = P.props.filter(p => p.detached).length; for (const o of W.chars.values()) o.busy = false; F.reset(); P.restoreAll(true); return { calls, det };
        }""")
        d_day, d_night = calls_day - base_calls["day"], calls_night - base_calls["night"]
        d_worst = d_night + (worst["calls"] - late_night)
        ok("繪製次數：白天閒置增量 +%d（%d → %d）≤ +10" % (d_day, base_calls["day"], calls_day), d_day <= 10, (calls_day, base_calls))
        ok("繪製次數：夜晚閒置增量 +%d（%d → %d）≤ +10" % (d_night, base_calls["night"], calls_night), d_night <= 10, (calls_night, base_calls))
        ok("繪製次數：最壞情況（夜晚＋燃燒中＋拆出 %d 個零件＋立燈倒下）合計增量 +%d ≤ +10" % (worst["det"], d_worst), d_worst <= 10, (worst, late_night, d_night))

        # ───── 真人操作：滑鼠按住角色 → 拖 → 放開（1280）─────
        def real_drag(pg_, tag):
            pg_.evaluate("""() => { const W = __world, T = __T, c = T.oldChar(); T.place(c, 13.0, 11.0, Math.PI); W.daytime.set('day'); W.speed = 1; W.view.mode = 'god'; W.view.char = null; W.view.tween = null;
              W.controls.target.set(13, 0.4, 11); W.camera.position.set(13, 9, 17); W.camera.fov = 38; W.camera.updateProjectionMatrix(); W.controls.update(); window.__rc = c; c.busy = false; }""")
            pg_.wait_for_timeout(800)
            pt = pg_.evaluate("() => { const W = __world, c = window.__rc, v = new W.THREE.Vector3(c.object3D.position.x, 0.45, c.object3D.position.z).project(W.camera); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight]; }")
            pg_.mouse.move(pt[0], pt[1])
            pg_.mouse.down()
            pg_.wait_for_timeout(650)                      # 按住不動 0.4 秒以上才算「拎起」，接著一動才真的拎起來
            held = False
            for i in range(1, 9):
                pg_.mouse.move(pt[0] + i * 40, pt[1] - i * 5)
                pg_.wait_for_timeout(40)
                if not held:
                    held = bool(pg_.evaluate("() => window.__rc.state === 'held'"))
            pg_.mouse.up()
            moved = wait_until(pg_, "() => window.__rc.state !== 'held' && Math.hypot(window.__rc.object3D.position.x - 13, window.__rc.object3D.position.z - 11) > 0.5", 20000)
            pos = pg_.evaluate("() => [window.__rc.object3D.position.x, window.__rc.object3D.position.z, window.__rc.state]")
            pg_.evaluate("() => { __world.speed = 0.001; window.__rc.busy = true; }")
            return held, moved, pos

        held, moved, pos = real_drag(pg, "1280")
        ok("真人操作（1280）：滑鼠按住角色 0.4 秒後被拎起", held, held)
        ok("真人操作（1280）：拖動後放開，角色被丟出、離開原位（現在在 %.1f,%.1f）" % (pos[0], pos[1]), moved, pos)
        ok("物理段：1280 沒有主控台錯誤、主迴圈無例外（loopErr=%s）" % pg.evaluate("() => __world.loopErr || 0"), not errs and not pg.evaluate("() => __world.loopErr"), errs[:3])
    finally:
        c1.close()

    # ───── 手機 390 ─────
    c2, pm = mk(390, 844, True)
    try:
        ok("物理段（390）：場景載入", load(pm))
        pm.evaluate("() => { __world.speed = 0.001; __world.daytime.set('day'); }")
        pm.evaluate(_PH_HELPERS)
        rm = pm.evaluate(_PH_CHAIR, ["old", False])
        ok("丟人撞椅子（390）：椅子翻倒（%.2f）並在 %.0f 秒後回到原位（誤差 %.3f）" % (rm["th"], rm["tRestore"], rm["err"]), rm["th"] >= 0.8 and rm["mode2"] == "home" and rm["err"] < 0.05 and rm["angErr"] < 0.0873, rm)
        rf = pm.evaluate("""async () => {
          const W = __world, F = W.fire, T = __T, c = T.oldChar(); T.place(c, 30.2, 34.3, 0); T.throwTo(c, 30.2, 36.6, 4.5, 1.5); let soot = 0, burned = false;
          for (let i = 0; i < 30 * 8; i++) { await W.advanceAsync(1 / 30, 1 / 30); soot = Math.max(soot, F.scorch(c)); if (F.stateOf(c).state === 'burning') burned = true; }
          return { soot, burned, state: F.stateOf(c).state }; }""")
        ok("營火（390）：丟進去會燒起來、焦黑 %.2f" % rf["soot"], rf["burned"] and rf["soot"] > 0.5, rf)
        held, moved, pos = real_drag(pm, "390")
        ok("真人操作（390）：按住角色被拎起、放開後被丟出", held and moved, (held, moved, pos))
        ok("手機 390：頁面沒有橫向捲動、沒有主控台錯誤", pm.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1") and not errs, errs[:3])
    finally:
        c2.close()


register("辦公室物理互動", lambda pg, b, base, code: t_office_physics(b, base))
