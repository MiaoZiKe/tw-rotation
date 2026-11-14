// 辦公室物理互動層（2026-11-14 擁有者：「丟人物，桌椅會被打翻；燒起來、焦黑，過一陣子都會主動復原」）。
//
// 做了什麼
//   1. 可被撞翻的「輕東西」：椅子、盆栽、立燈、懶骨頭、桌上的杯子／書／球。
//      · 獨立家具（盆栽、立燈、懶骨頭）本來就是一個群組，直接讓它動。
//      · 椅子、桌上小物原本併在桌子的合併網格裡：被撞到的那一刻，把它的頂點「拆」出來變成獨立網格
//        （合併網格裡那段頂點縮成一點；歸位時再貼回去）。平常 0 個額外繪製，被撞開的才多 1 個／件。
//   2. 剛體：位置、速度、重力、地面摩擦、與牆／重家具碰撞；高的東西用「繞底邊翻倒」的倒單擺（有翻倒門檻能量）；
//      倒下後會彈一下、滾動（盆栽、立燈）、停住。角色（被丟、被操控跑步）撞上去依相對速度動量交換，雙方都有反作用。
//   3. 重家具（桌、牆、書櫃）不動，但飛行中的角色撞上會反彈並引起小震動（鏡頭微晃＋桌上小物跳起來）。
//   4. 自動復原：翻倒／被撞離的東西等 20～40 秒（模擬時間），由附近閒著的同事走去扶起、推回原位；沒人就自己彈回去。
//   5. 事件：W.on(型態, 函數) / W.emit(型態, id, 附加欄位)。本檔送出
//        knocked（角色被撞／撞牆）、toppled（東西翻倒）、righted（東西復原）、bump（重物碰撞）。
//      火焰那邊（fire.js）送 burned、recovered、extinguished。表情與個性由情緒系統訂閱這些事件決定。
//
// 時間：全部用模擬時間（W.speed 加速時一起加速）；每個模擬步由主迴圈呼叫 P.tick(h)。
import { THREE, MAT } from './kit.js';
import { footToWorld, localToWorld } from './nav.js';

const V3 = THREE.Vector3, Qn = THREE.Quaternion, UP = new V3(0, 1, 0);
const G = 9.8, rnd = (a, b) => a + Math.random() * (b - a), clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const easeOutBack = u => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2); };
const easeIO = u => u * u * (3 - 2 * u);
const angDiff = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b));

// ── 事件匯流排（若別的模組已經提供就沿用）──
export function ensureBus(W) {
  if (W.emit && W.on) return;
  const L = new Map(); W.eventLog = W.eventLog || [];
  W.on = (type, fn) => { if (!L.has(type)) L.set(type, []); L.get(type).push(fn); return () => { const a = L.get(type); const i = a.indexOf(fn); if (i >= 0) a.splice(i, 1); }; };
  W.emit = (type, id, extra) => {
    const ev = { type, id, t: W.time, ...(extra || {}) }; W.eventLog.push(ev); if (W.eventLog.length > 300) W.eventLog.shift();
    for (const k of [type, '*']) for (const fn of (L.get(k) || []).slice()) { try { fn(ev); } catch (e) { console.error('事件處理例外', type, e); } }
    return ev;
  };
}

// ── 各種輕東西的物理參數（單位：公尺、公斤；rb＝底面半徑、hcg＝重心高、hhit＝受撞的平均高度、restTh＝倒下後的傾角）──
const KIND = {
  chair:     { zh: '椅子', r: 0.3, h: 0.85, m: 4.5, rb: 0.24, hcg: 0.42, hhit: 0.45, restTh: 1.36, lift: 0.14, mu: 0.55, e: 0.35, tip: true, roll: false },
  plant:     { zh: '盆栽', r: 0.24, h: 0.9, m: 3.2, rb: 0.19, hcg: 0.36, hhit: 0.4, restTh: 1.5708, lift: 0.07, mu: 0.7, e: 0.3, tip: true, roll: true },
  plant_big: { zh: '大盆栽', r: 0.32, h: 2.0, m: 9, rb: 0.26, hcg: 0.85, hhit: 0.8, restTh: 1.5708, lift: 0.08, mu: 0.8, e: 0.25, tip: true, roll: true },
  lamp:      { zh: '立燈', r: 0.2, h: 1.6, m: 3.4, rb: 0.2, hcg: 0.78, hhit: 0.9, restTh: 1.5708, lift: 0.1, mu: 0.5, e: 0.3, tip: true, roll: true },
  beanbag:   { zh: '懶骨頭', r: 0.5, h: 0.55, m: 7, rb: 0.5, hcg: 0.2, hhit: 0.3, restTh: 0, lift: 0, mu: 1.5, e: 0.2, tip: false, roll: false },
  mug:       { zh: '杯子', r: 0.06, h: 0.1, m: 0.25, rb: 0.05, hcg: 0.05, hhit: 0.05, restTh: 1.5708, lift: 0.0, mu: 0.5, e: 0.45, tip: false, roll: true, item: true },
  book:      { zh: '書', r: 0.14, h: 0.05, m: 0.4, rb: 0.14, hcg: 0.02, hhit: 0.02, restTh: 0, lift: 0, mu: 0.6, e: 0.3, tip: false, roll: false, item: true },
  ball:      { zh: '小球', r: 0.06, h: 0.12, m: 0.2, rb: 0.06, hcg: 0.06, hhit: 0.06, restTh: 0, lift: 0, mu: 0.15, e: 0.6, tip: false, roll: true, item: true },
};
const FURN_KIND = { plant: 'plant', plant_big: 'plant_big', lamp: 'lamp', beanbag: 'beanbag' };
// 重家具高度（角色飛得比它高就能飛過去）
const STATIC_H = { workstation: 0.78, ceo_desk: 0.78, meeting_table: 0.72, bookshelf: 1.7, cabinet: 1.2, sofa: 0.85, armchair: 0.85, reserve_seat: 0.85, counter: 1.1, dining: 0.75, snack: 1.4, arcade: 1.7, fridge: 1.7, water: 1.1, pingpong: 0.8, coffee_table: 0.45, side_table: 0.5, bench: 0.5, kiosk: 1.3, board: 1.6, whiteboard: 1.6, rug: 0, doormat: 0, door: 0, deptsign: 0, roomsign: 0 };
// 桌面高度（小物件從上方落下時停在這個高度）
const TOP = { workstation: 0.67, ceo_desk: 0.7, meeting_table: 0.69, coffee_table: 0.41, side_table: 0.56, dining: 0.72, counter: 1.0, bench: 0.5, sofa: 0.5, armchair: 0.5 };
const MAX_ITEMS = 5, MAX_CHAIRS = 6;   // 同時最多拆出來的零件數（每件多 1 次繪製）：桌上小物 5、椅子 6

export function createPhysics(W, opts = {}) {
  ensureBus(W);
  const P = { props: [], stats: { maxStep: 0, hits: 0, topples: 0, restores: 0, helped: 0, selfReturn: 0, charHits: 0, wallHits: 0 }, delay: [20, 40], on: true, shake: 0, cfg: { restMin: 20, restMax: 40 } };
  W.phys = P;
  const D = () => W.director, allChars = () => [...W.chars.values(), ...(W.pets || []), ...(W.extras || [])];
  const q1 = new Qn(), q2 = new Qn(), q3 = new Qn(), tv = new V3(), tv2 = new V3(), axis = new V3();
  const reduce = matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ───────────────────────── 建立可動物件 ─────────────────────────
  function mkProp(o) {
    const K = KIND[o.kind]; return Object.assign({
      id: '', kind: o.kind, K, inst: null, obj: null, mesh: null, mode: 'home', x: 0, z: 0, y: 0, vx: 0, vz: 0, vy: 0, th: 0, om: 0, dx: 0, dz: 1, dyaw: 0, rho: 0, sq: 0, wyaw: 0,
      r: K.r, h: K.h, m: K.m, rb: K.rb, hcg: K.hcg, hhit: K.hhit, restTh: K.restTh, restAt: 0, restT: 0, wait: 0, helper: null, hwait: 0, urgent: false, detached: false,
      baseY: 0, ret: null, spin: new Qn(), spinW: new V3(), restQ: null, since: 0, locked: false, spot: null
    }, o);
  }
  P.rebuild = () => {
    for (const p of P.props) if (p.mode !== 'home') toHome(p, true);
    for (const p of P.props) if (p.mesh) { p.mesh.removeFromParent(); p.mesh.geometry.dispose(); p.mesh = null; }
    P.props = [];
    for (const inst of W.furn.values()) {
      const t = inst.f.type;
      if (FURN_KIND[t]) { P.props.push(mkProp({ id: inst.f.id, kind: FURN_KIND[t], inst, obj: inst.obj, src: 'furn', wait: 0, lampOn: t === 'lamp' })); }
      (inst.marks || []).forEach((m, mi) => {
        const kind = m.kind === 'chair' ? 'chair' : (m.what || 'mug');
        const p = mkProp({ id: inst.f.id + '/' + (m.kind === 'chair' ? 'chair' : m.what) + mi, kind, inst, src: 'part', mi, mark: m });
        if (m.kind === 'chair') {
          if (m.big) { p.r *= 1.12; p.m *= 1.3; p.hcg *= 1.2; p.h *= 1.15; }
          const seats = inst.spec.seats || []; const si = seats.findIndex(s => Math.abs(s.x - m.x) < 0.06 && Math.abs(s.z - m.z) < 0.06); if (si >= 0) p.spotUid = inst.f.id + '#s' + si;
        } else { p.r = m.r || p.r; p.h = m.h || p.h; p.baseY = m.y; p.isItem = true; }
        P.props.push(p);
      });
    }
    P.glowChanged();
  };
  P.onRestyle = inst => { for (const p of P.props) if (p.inst === inst && p.src === 'part') { p.mark = inst.marks[p.mi]; if (p.detached) collapse(p); } };
  // 立燈光暈的點位（daytime.js 重建光暈後通知）
  P.glowChanged = () => { for (const p of P.props) if (p.kind === 'lamp') { p.gi = W.glowIdx ? W.glowIdx.get(p.inst.f.id) : undefined; } };

  // ───────────────────────── 切出／貼回合併網格的那段頂點 ─────────────────────────
  function base(p) {   // 這件東西「底面中心」目前的位置（家具座標 → 世界）與朝向
    const f = p.inst.f;
    if (p.src === 'furn') return { x: f.x, z: f.z, yaw: f.rot * Math.PI / 2 };
    const w = localToWorld(f, p.mark.x, p.mark.z); return { x: w.x, z: w.z, yaw: f.rot * Math.PI / 2 };
  }
  function detach(p) {
    if (p.src !== 'part' || p.detached) return;
    const m = p.mark, g = p.inst.mesh.geometry, pos = g.attributes.position, nor = g.attributes.normal, col = g.attributes.color, n = m.v1 - m.v0;
    const ox = m.x, oy = m.kind === 'chair' ? 0 : m.y, oz = m.z, a = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { a[i * 3] = pos.array[(m.v0 + i) * 3] - ox; a[i * 3 + 1] = pos.array[(m.v0 + i) * 3 + 1] - oy; a[i * 3 + 2] = pos.array[(m.v0 + i) * 3 + 2] - oz; }
    const ng = new THREE.BufferGeometry(); ng.setAttribute('position', new THREE.BufferAttribute(a, 3));
    ng.setAttribute('normal', new THREE.BufferAttribute(nor.array.slice(m.v0 * 3, m.v1 * 3), 3)); ng.setAttribute('color', new THREE.BufferAttribute(col.array.slice(m.v0 * 3, m.v1 * 3), 3));
    ng.computeBoundingSphere();
    p.backup = pos.array.slice(m.v0 * 3, m.v1 * 3); p.bo = { x: ox, y: oy, z: oz };
    const mesh = new THREE.Mesh(ng, MAT.solid); mesh.castShadow = true; mesh.receiveShadow = true; mesh.userData.prop = p.id; mesh.frustumCulled = false;
    W.scene.add(mesh); p.mesh = mesh; p.obj = mesh; collapse(p); p.detached = true; W.shadowDirty();
  }
  function collapse(p) {
    const m = p.mark, g = p.inst.mesh.geometry, pos = g.attributes.position, o = p.bo;
    for (let v = m.v0; v < m.v1; v++) { pos.array[v * 3] = o.x; pos.array[v * 3 + 1] = o.y; pos.array[v * 3 + 2] = o.z; } pos.needsUpdate = true;
  }
  function attach(p) {
    if (p.src !== 'part' || !p.detached) return;
    const m = p.mark, g = p.inst.mesh.geometry, pos = g.attributes.position; pos.array.set(p.backup, m.v0 * 3); pos.needsUpdate = true;
    p.mesh.removeFromParent(); p.mesh.geometry.dispose(); p.mesh = null; p.obj = null; p.detached = false; p.backup = null; W.shadowDirty();
  }

  // ───────────────────────── 姿勢 → 物件 ─────────────────────────
  function poseOf(p, out) {
    const b = base(p); if (!p.obj) return;
    const yaw = b.yaw + p.dyaw;
    q1.setFromAxisAngle(UP, yaw);
    let px = p.x, pz = p.z, py = p.y;
    if (p.th !== 0) {
      axis.set(p.dz, 0, -p.dx); q2.setFromAxisAngle(axis, p.th); q1.premultiply(q2);
      tv.set(-p.dx * p.rb, 0, -p.dz * p.rb).applyQuaternion(q2);   // 繞底邊：底面中心離開原位
      px += p.dx * p.rb + tv.x; pz += p.dz * p.rb + tv.z; py += p.rb * 0 + tv.y + p.K.lift * Math.sin(Math.min(p.th, 1.5708));
    }
    if (p.rho) { axis.set(p.dx, 0, p.dz); q3.setFromAxisAngle(axis, p.rho); q1.premultiply(q3); }
    if (p.isItem && p.spinOn) { q1.premultiply(p.spin); }
    p.obj.position.set(px, py, pz); p.obj.quaternion.copy(q1);
    if (p.kind === 'beanbag') p.obj.scale.set(1 + p.sq * 0.25, 1 - p.sq * 0.4, 1 + p.sq * 0.25); else if (p.obj.scale.x !== 1) p.obj.scale.set(1, 1, 1);
    p.obj.updateMatrixWorld(true);
  }
  function toHome(p, instant) {
    p.mode = 'home'; p.th = 0; p.om = 0; p.vx = p.vz = p.vy = 0; p.dyaw = 0; p.rho = 0; p.sq = 0; p.y = p.isItem ? p.baseY : 0; p.spinOn = false; p.ret = null; p.helper = null; p.urgent = false; p.air = false; p.toppled = false; p.settled = false; p.hw0 = 0; p.restQ = null; p.spin.identity(); p.carry = null; p.lift = null;
    if (p.src === 'furn') { p.obj.rotation.set(0, 0, 0); p.obj.quaternion.identity(); W.place(p.inst); p.obj.scale.set(1, 1, 1); p.obj.visible = true; }
    else attach(p);
    if (p.spot) p.spot.blocked = false; if (p.kind === 'lamp') lampSet(p);
    W.shadowDirty();
  }
  function startMove(p) {
    if (p.mode !== 'home') return;
    const b = base(p); p.x = b.x; p.z = b.z; p.y = p.isItem ? p.baseY : 0; p.th = 0; p.om = 0; p.rho = 0; p.dyaw = 0; p.vx = p.vz = p.vy = 0;
    if (p.src === 'part') detach(p); else { p.obj.updateMatrixWorld(true); }
    p.mode = 'move'; p.restT = 0; p.since = W.time; p.wait = rnd(P.cfg.restMin, P.cfg.restMax); p.hwait = 0; p.urgent = false; p.helper = null;
    const sp = p.spotUid && W.spots.find(s => s.uid === p.spotUid); p.spot = sp || null; if (sp) sp.blocked = true;
    if (p.src === 'furn' && p.kind !== 'beanbag') { /* 影子是靜態烘的：動起來時不投影，用腳下的接觸陰影 */ }
    W.shadowDirty();
  }

  // ───────────────────────── 受力 ─────────────────────────
  // 把一個衝擊施加到物件上：n＝從來源指向物件的單位向量，vn＝來源逼近物件的速度分量，mSrc＝來源質量
  function impart(p, nx, nz, vn, mSrc, vyUp = 0) {
    if (vn <= 0.05 || p.locked) return 0;
    if (p.src === 'part' && !p.detached) { let ni = 0, nc = 0; for (const q of P.props) if (q.detached) { if (q.isItem) ni++; else nc++; } if (p.isItem ? ni >= MAX_ITEMS : nc >= MAX_CHAIRS) return 0; }   // 同時被拆出來的零件上限（每個多 1 次繪製）：桌上小物 5、椅子 6
    if (p.mode === 'carry' || p.mode === 'lift' || p.mode === 'lifted') return 0;
    startMove(p); if (p.mode === 'ret' || p.mode === 'wait' || p.mode === 'lifted') { p.mode = 'move'; p.ret = null; p.helper = null; }
    const e = p.K.e, j = (1 + e) * vn / (1 / mSrc + 1 / p.m), dv = Math.min(j / p.m, p.isItem ? 2.8 : 5.5), Ieff = 1.1 * p.hcg * p.hcg + p.rb * p.rb;
    let tipped = false;
    if (p.K.tip) {
      const om0 = dv * p.hhit / Ieff * 0.9, barrier = G * (Math.hypot(p.rb, p.hcg) - p.hcg), need = 0.5 * Ieff * om0 * om0;
      if (p.th < 0.05) { p.dx = nx; p.dz = nz; p.om += om0; } else p.om += om0 * 0.4 * Math.max(0, p.dx * nx + p.dz * nz);
      tipped = need > barrier * 0.95 || p.th > 0.3;
      if (tipped && !p.toppled) { p.toppled = true; P.stats.topples++; W.emit('toppled', p.id, { kind: p.kind, zh: p.K.zh, x: p.x, z: p.z }); }
    }
    const k = tipped ? 0.45 : 1; p.vx += nx * dv * k; p.vz += nz * dv * k;
    if (p.isItem) p.vy += Math.max(vyUp, 1.1 + dv * 0.5), p.air = true;
    p.restT = 0; p.since = W.time; p.wait = rnd(P.cfg.restMin, P.cfg.restMax); p.hwait = 0;
    if (p.kind === 'beanbag') p.sq = Math.min(1, p.sq + dv * 0.3);
    if (p.kind === 'lamp') { p.flick = 0.5; }
    return j;   // 來源受到反向衝量 -j
  }

  // ───────────────────────── 角色轉接（新舊兩種角色共用）─────────────────────────
  function cinfo(c) {
    if (!c.object3D.visible || c.away || c._seat || c._hop || c._rising) return null;   // 坐著、正要跳上／跳下座位的不算（他們本來就在家具裡面）   // 注意：被丟出去後 c._held 要到落地才解除，所以不能用 c.state==='held' 排除（拎著的由下面的物理狀態判斷）
    const s = c.scale || 1, p = c.object3D.position, inner = c.inner;
    if (c.newModel) {
      const ctl = inner && inner.ctl, b = ctl && ctl.body, st = ctl && ctl.state; if (!b) return null;
      if (st === 'sit' || st === 'sleep' || st === 'held' || ctl.sit) return null;
      const vx = b.vx * s, vz = b.vz * s, fly = st === 'tumble' || st === 'air' || !b.grounded;
      return { c, s, x: p.x, z: p.z, vx, vz, fly, sp: Math.hypot(vx, vz), y0: c.lift || 0, newM: true, b, ctl, vy: b.vy * s };
    }
    const ch = inner; if (!ch || !ch.vel || !ch.pos || ch.mode === 'held' || ch.mode === 'sit' || ch.mode === 'sleep') return null;   // 沒有物理本體的佔位角色（?char=./character.js 除錯用）不參與
    const vx = ch.vel.x * s, vz = ch.vel.z * s, fly = ch.mode === 'tumble' || !ch.grounded;
    return { c, s, x: p.x, z: p.z, vx, vz, fly, sp: Math.hypot(vx, vz), y0: c.lift || 0, newM: false, ch, vy: ch.vel.y * s };
  }
  function setV(ci, vx, vz) { if (ci.newM) { ci.b.vx = vx / ci.s; ci.b.vz = vz / ci.s; } else { ci.ch.vel.x = vx / ci.s; ci.ch.vel.z = vz / ci.s; } ci.vx = vx; ci.vz = vz; ci.sp = Math.hypot(vx, vz); }
  function moveBy(ci, dx, dz) { if (ci.newM) { ci.b.x += dx / ci.s; ci.b.z += dz / ci.s; } else { ci.ch.pos.x += dx / ci.s; ci.ch.pos.z += dz / ci.s; } ci.c.object3D.position.x += dx; ci.c.object3D.position.z += dz; ci.x += dx; ci.z += dz; }
  const cmass = ci => 5.5 * ci.s * ci.s * (ci.c.spec && ci.c.spec.pet ? 1 : 1);
  // 把角色撞倒（跑步撞上去、被重物撞）：新角色走控制器的拋擲，舊角色走自己的翻滾
  function knockDown(ci, vx, vy, vz) {
    const c = ci.c; if (c._knockT && W.time - c._knockT < 1.5) return; c._knockT = W.time;
    c.stop && c.stop(false); c._drive = null;
    if (ci.newM) { ci.ctl.throwAt(vx / ci.s, vy / ci.s, vz / ci.s); c._held = true; c._released = true; }
    else { const ch = ci.ch; ch.act = null; ch.goal = null; ch.mode = 'tumble'; ch.modeT = 0; ch.rest = 0; ch.grounded = false; ch.vel.set(vx / ci.s, vy / ci.s, vz / ci.s); ch.w.set(ch.vel.z, 0, -ch.vel.x).multiplyScalar(2.5 / ch.R); c._held = true; c._released = true; }
  }
  // 丟人（給測試與其他模組用）：新舊角色同一個介面。速度單位：世界公尺／秒
  P.throwChar = (c, vx, vy, vz) => {
    const s = c.scale || 1; c.grab();
    if (c.newModel) { c.inner.ctl.release(vx / s, vy / s, vz / s); c._released = true; }
    else { c.inner.vel.set(vx / s, vy / s, vz / s); c.release(); }
  };

  // ───────────────────────── 重家具與牆（飛行中的角色會撞到）─────────────────────────
  let statics = [];
  P.rebuildStatics = () => {
    statics = [];
    for (const inst of W.furn.values()) {
      const t = inst.f.type, h = STATIC_H[t]; if (h === 0 || FURN_KIND[t]) continue;
      for (const sh of footToWorld(inst.f, inst.spec.foot || [])) {
        // 椅子的腳印（桌子自帶的那顆小圓）不當重物：它是會被撞開的輕東西
        if (sh.r != null && sh.r <= 0.3 && (t === 'workstation' || t === 'ceo_desk' || t === 'meeting_table')) continue;
        statics.push({ ...sh, h: h == null ? 0.9 : h, fid: inst.f.id, inst, type: t });
      }
    }
    for (const w of W.layout.walls) { const T = 0.125, x0 = Math.min(w.x1, w.x2) - T, x1 = Math.max(w.x1, w.x2) + T, z0 = Math.min(w.z1, w.z2) - T, z1 = Math.max(w.z1, w.z2) + T; statics.push({ x: (x0 + x1) / 2, z: (z0 + z1) / 2, w: x1 - x0, d: z1 - z0, h: w.h || 2.4, wall: true }); }
    P.statics = statics;
  };
  // 圓（x,z,r）與靜態物的最近距離與法向量（指向圓心）；回傳 null＝沒碰到
  function circVs(s, x, z, r) {
    let nx, nz, dist, pen;
    if (s.r != null) { const dx = x - s.x, dz = z - s.z, d = Math.hypot(dx, dz); if (d >= r + s.r) return null; nx = d > 1e-6 ? dx / d : 1; nz = d > 1e-6 ? dz / d : 0; pen = r + s.r - d; }
    else {
      const hx = s.w / 2, hz = s.d / 2, qx = clamp(x, s.x - hx, s.x + hx), qz = clamp(z, s.z - hz, s.z + hz), dx = x - qx, dz = z - qz, d = Math.hypot(dx, dz);
      if (d >= r) return null;
      if (d < 1e-6) { const ex = hx - Math.abs(x - s.x), ez = hz - Math.abs(z - s.z); if (ex < ez) { nx = Math.sign(x - s.x) || 1; nz = 0; pen = ex + r; } else { nz = Math.sign(z - s.z) || 1; nx = 0; pen = ez + r; } }
      else { nx = dx / d; nz = dz / d; pen = r - d; }
    }
    return { nx, nz, pen };
  }
  // 「碰」的小震動：鏡頭微晃（離鏡頭遠的不晃）＋被撞的家具抖一下＋桌上的小物跳起來
  const shakes = [];
  function bumpFx(x, z, sp, st) {
    P.stats.hits++; if (reduce) return;
    const cam = W.camera, d = Math.hypot(cam.position.x - x, cam.position.z - z); P.shake = Math.max(P.shake, clamp(sp * 0.012, 0, 0.09) * clamp(1.3 - d / 40, 0.2, 1));
    if (st && st.inst && !st.wall) { const o = shakes.find(q => q.inst === st.inst); if (o) { o.t = 0; o.amp = Math.min(0.05, sp * 0.008); } else shakes.push({ inst: st.inst, t: 0, amp: Math.min(0.05, sp * 0.008) }); }
    if (st && st.inst && sp > 2) for (const p of P.props) if (p.inst === st.inst && p.isItem && p.mode === 'home') { const a = Math.random() * 6.28; impart(p, Math.cos(a), Math.sin(a), 0.6 + sp * 0.25, 1.2, 1.5 + sp * 0.12); }
    W.emit('bump', st && st.fid, { speed: sp, x, z });
  }

  // ───────────────────────── 角色 × 物件 ─────────────────────────
  function charVsProps(ci, h) {
    const r = (ci.c.radius || 0.3) * 0.85;
    for (const p of P.props) {
      if (p.locked || p.mode === 'carry' || p.mode === 'lift' || p.mode === 'lifted') continue;
      let px, pz; if (p.mode === 'home') { const b = base(p); px = b.x; pz = b.z; if (p.isItem) continue; } else { px = p.x; pz = p.z; }
      const dx = px - ci.x, dz = pz - ci.z, rr = r + p.r; if (dx * dx + dz * dz > rr * rr) continue;
      const top = (p.mode === 'home' ? 0 : p.y) + p.h, bot = p.mode === 'home' ? 0 : p.y;
      if (ci.y0 > top - 0.02 || ci.y0 + (ci.c.height || 0.7) < bot + 0.05) continue;
      const d = Math.hypot(dx, dz) || 1e-6, nx = dx / d, nz = dz / d;                        // 從角色指向物件
      const pvx = p.mode === 'home' ? 0 : p.vx, pvz = p.mode === 'home' ? 0 : p.vz;
      const vn = (ci.vx - pvx) * nx + (ci.vz - pvz) * nz;                                // 角色逼近物件的速度
      if (vn < 0.2) { // 緩慢貼著：只把角色推開一點點，不傷物件
        if (p.mode !== 'home') { const k = (rr - d) * 0.5; p.x += nx * k; p.z += nz * k; moveBy(ci, -nx * k, -nz * k); } continue;
      }
      const mc = cmass(ci), j = impart(p, nx, nz, vn, mc, 0);
      if (j > 0) {
        P.stats.charHits++; const nvx = ci.vx - nx * j / mc, nvz = ci.vz - nz * j / mc; setV(ci, nvx, nvz);
        const pen = rr - d; if (pen > 0) moveBy(ci, -nx * pen * 0.6, -nz * pen * 0.6);
        if (vn > 3.2 && (p.K.m > 3 || ci.fly)) { reactHit(ci, p.K.zh, vn, nx, nz); }
        if (vn > 2.4) bumpFx(px, pz, vn * 0.6, null);
      }
    }
  }
  function reactHit(ci, what, vn, nx, nz) {
    const c = ci.c, id = c.spec.id; W.emit('knocked', id, { by: what, speed: vn });
    // 跑步撞上去又很快：整個人彈開翻一圈（被丟的本來就在翻）
    if (!ci.fly && vn > 4.3 && (!c._knockT || W.time - c._knockT > 1.5)) knockDown(ci, -nx * vn * 0.45, 2.4, -nz * vn * 0.45);
  }
  function charVsStatics(ci, h) {
    const r = (ci.c.radius || 0.3) * 0.9;
    for (const s of statics) {
      if (ci.y0 > s.h - 0.03) continue;
      const hit = circVs(s, ci.x, ci.z, r); if (!hit) continue;
      const vn = -(ci.vx * hit.nx + ci.vz * hit.nz);   // 朝牆的速度分量（正＝撞向它）
      const push = Math.min(hit.pen, Math.max(0.002, 3.5 * h + (vn > 0 ? hit.pen : 0)));
      moveBy(ci, hit.nx * push, hit.nz * push);
      if (vn > 0) {
        const e = ci.fly ? 0.45 : 0.1, tx = ci.vx + hit.nx * vn, tz = ci.vz + hit.nz * vn;     // 切線分量
        setV(ci, tx * 0.9 + hit.nx * vn * e, tz * 0.9 + hit.nz * vn * e);
        if (vn > 1.5) {
          if (!ci._wallT || W.time - ci._wallT > 0.25) { ci._wallT = W.time; P.stats.wallHits++; bumpFx(ci.x, ci.z, vn, s);
            if (vn > 2.6) W.emit('knocked', ci.c.spec.id, { by: s.wall ? '牆' : '家具', speed: vn }); }
        }
      }
    }
  }

  // ───────────────────────── 物件自身的運動 ─────────────────────────
  function groundY(p, y0) {
    if (!p.isItem) return 0; if (y0 == null) y0 = p.y; const f = p.inst.f; let g = 0;
    for (const sh of footToWorld(f, p.inst.spec.foot || [])) { const inside = sh.r != null ? Math.hypot(p.x - sh.x, p.z - sh.z) < sh.r : Math.abs(p.x - sh.x) < sh.w / 2 && Math.abs(p.z - sh.z) < sh.d / 2; if (inside && y0 >= p.baseY - 0.03) g = Math.max(g, p.baseY); }   // 原本那張桌子：要從桌面上方落下才停得住（從桌子側邊下面滑回來是撞到桌腳，不是爬上桌）
    // 飛過別的桌子上方、落下來會停在那張桌面上（不是穿進桌子裡）
    // y0：這一步開始前的高度（一步會掉 0.1 公尺，用落下後的高度判斷會漏接）
    for (const q of statics) { if (q.wall || q.inst === p.inst) continue; const top = TOP[q.type]; if (top == null || y0 < top - 0.03) continue; if (circVs(q, p.x, p.z, 0.02)) g = Math.max(g, top); }
    return g;
  }
  function stepMove(p, h) {
    const K = p.K, yPrev = p.y;
    // 倒單擺（繞底邊）
    if (K.tip) {
      const Ie = 1.1 * p.hcg * p.hcg + p.rb * p.rb, a = G * (p.hcg * Math.sin(p.th) - p.rb * Math.cos(p.th)) / Ie;
      if (p.th > 0 || p.om !== 0) {
        p.om += a * h; p.om *= 1 - 0.9 * h; p.th += p.om * h;
        if (p.th < 0) { p.th = 0; p.om = Math.abs(p.om) > 0.4 ? -p.om * 0.25 : 0; }
        if (p.th > p.restTh) { const imp = p.om; p.th = p.restTh; if (imp > 1.2) { p.om = -imp * 0.3; p.landT = W.time; bumpFx(p.x, p.z, imp * 0.8, null); } else p.om = 0; }
      }
    }
    // 重力（桌上小物）
    if (p.isItem) {
      const gy = groundY(p, yPrev);
      if (p.air || p.y > gy + 1e-3) {
        p.vy -= G * h; p.y += p.vy * h; p.spinOn = true; tv.copy(p.spinW); const w = tv.length(); if (w > 1e-4) { q2.setFromAxisAngle(tv.multiplyScalar(1 / w), w * h); p.spin.premultiply(q2); }
        if (p.y <= gy) { p.y = gy; if (p.vy < -0.8) { p.vy = -p.vy * K.e; p.vx *= 0.8; p.vz *= 0.8; p.spinW.multiplyScalar(0.6); if (-p.vy > 1.2) bumpFx(p.x, p.z, 1, null); } else { p.vy = 0; p.air = false; } }
      }
      if (!p.air && p.spinOn) { // 落地後轉到「平放」的朝向（杯子側躺、書本平放）
        if (!p.restQ) { p.restQ = new Qn(); const lie = p.kind === 'mug' ? 1.5708 : 0; p.restQ.setFromEuler(new THREE.Euler(lie, Math.random() * 6.28, 0, 'YXZ')); }
        p.spin.slerp(p.restQ, 1 - Math.exp(-8 * h));
      }
    }
    // 水平滑動（庫侖摩擦）；倒下的圓柱（盆栽、立燈）可以滾，摩擦小
    const sp = Math.hypot(p.vx, p.vz), lying = p.th > 1.0 || (p.isItem && !p.air);
    if (sp > 1e-4 && (!p.isItem || !p.air)) { const mu = lying && K.roll ? 0.18 : K.mu * (p.th > 0.25 ? 0.7 : 1), dec = mu * G * h, ns = Math.max(0, sp - dec); p.vx *= ns / sp; p.vz *= ns / sp; }
    if (K.roll && lying && sp > 0.02 && !p.isItem) p.rho += -(p.vx * p.dz - p.vz * p.dx) / Math.max(p.r, 0.12) * h;
    if (K.roll && p.isItem && !p.air && sp > 0.02) p.rho += -(p.vx * p.dz - p.vz * p.dx) / Math.max(p.r, 0.04) * h;
    p.x += p.vx * h; p.z += p.vz * h; p.dyaw += p.wyaw * h; p.wyaw *= 1 - 3 * h;
    if (p.kind === 'beanbag') p.sq *= 1 - 7 * h;
    // 與重家具、牆、房間邊界
    const rr = p.r + (lying && !p.isItem ? 0.12 : 0);
    if (!p.isItem || p.y > 0.02 || true) for (const s of statics) {
      if (s.fid === p.inst.f.id && p.src === 'part') continue;                 // 椅子可以滑進自己那張桌子下面
      const hh = p.isItem && TOP[s.type] != null ? TOP[s.type] : s.h;   // 小物件在桌面上時不算撞到桌子
      if (yPrev > hh - 0.03 || (p.isItem && s.inst === p.inst && yPrev >= p.baseY - 0.01)) continue;
      const hit = circVs(s, p.x, p.z, rr); if (!hit) continue;
      const vn = -(p.vx * hit.nx + p.vz * hit.nz), push = Math.min(hit.pen, 0.05 + (vn > 0 ? vn * h : 0)); p.x += hit.nx * push; p.z += hit.nz * push;   // 嵌進去太深時慢慢推出來（不瞬移）
      if (vn > 0) { p.vx += hit.nx * vn * (1 + 0.3); p.vz += hit.nz * vn * (1 + 0.3); if (vn > 1.2 && !p.isItem) { p.wyaw += (Math.random() - 0.5) * vn; bumpFx(p.x, p.z, vn * 0.5, s); } }
    }
    const L = W.layout.size; const mx = 0.3 + p.r * 0.2;
    if (p.x < mx) { p.x = mx; p.vx = Math.abs(p.vx) * 0.3; } if (p.x > L.w - mx) { p.x = L.w - mx; p.vx = -Math.abs(p.vx) * 0.3; } if (p.z < mx) { p.z = mx; p.vz = Math.abs(p.vz) * 0.3; } if (p.z > L.d - mx) { p.z = L.d - mx; p.vz = -Math.abs(p.vz) * 0.3; }
    // 與別的輕東西碰撞（只算會動的對上全部）
    for (const o of P.props) {
      if (o === p || o.locked || o.mode === 'carry' || o.mode === 'lift' || o.isItem !== p.isItem) continue;
      const ox = o.mode === 'home' ? base(o).x : o.x, oz = o.mode === 'home' ? base(o).z : o.z, dx = ox - p.x, dz = oz - p.z, rr2 = p.r + o.r; if (dx * dx + dz * dz > rr2 * rr2) continue;
      const d = Math.hypot(dx, dz) || 1e-6, nx = dx / d, nz = dz / d, vn = (p.vx - (o.mode === 'home' ? 0 : o.vx)) * nx + (p.vz - (o.mode === 'home' ? 0 : o.vz)) * nz;
      if (vn > 0.3) { const j = impart(o, nx, nz, vn, p.m * (p.th > 0.5 ? 0.6 : 1)); if (j) { p.vx -= nx * j / p.m; p.vz -= nz * j / p.m; } }
      if (o.mode !== 'home') { const k = (rr2 - d) * 0.5; p.x -= nx * k; p.z -= nz * k; o.x += nx * k; o.z += nz * k; } else if (d < rr2) { p.x -= nx * (rr2 - d); p.z -= nz * (rr2 - d); }
    }
    // 靜止判定
    const rest = Math.hypot(p.vx, p.vz) < 0.04 && Math.abs(p.om) < 0.05 && (!p.isItem || (!p.air && Math.abs(p.vy) < 0.05)) && (p.th < 0.02 || p.th >= p.restTh - 0.02 || p.th > 0.25 && Math.abs(p.om) < 0.02);
    if (rest) { p.restT += h; p.vx = p.vz = 0; if (p.restT > 0.25 && p.mode === 'move' && !p.settled) { p.settled = true; p.obj && (p.obj.castShadow = false); W.shadowDirty(); } } else { p.restT = 0; p.settled = false; }
    // 還沒倒下去、也沒離家太遠：站穩了就算原位（微小滑動直接緩慢歸位，不通報）
    const b = base(p), off = Math.hypot(p.x - b.x, p.z - b.z);
    if (rest && p.th < 0.02 && off < 0.012 && Math.abs(p.dyaw) < 0.02 && !(p.isItem && Math.abs(p.y - p.baseY) > 0.01)) { toHome(p, true); return; }
    if (rest && p.restT > 0.4 && W.time - p.since >= p.wait) beginRestore(p);
  }

  // ───────────────────────── 復原：同事扶起／自己彈回 ─────────────────────────
  function helperOk(c) { return c && !c.busy && !c.away && !c.jobless && !c.sleeping && !c.spec.isCeo && !c.spec.pet && c.state === 'sit' && c.atDesk && c.object3D.visible; }
  function pickHelper(p) {
    let best = null, bd = 9.5; for (const c of W.chars.values()) { if (!helperOk(c)) continue; const d = Math.hypot(c.object3D.position.x - p.x, c.object3D.position.z - p.z); if (d < bd) { bd = d; best = c; } } return best;
  }
  function beginRestore(p) {
    if (p.mode !== 'move' || p.edging) return;
    if (!p.urgent && !p.noHelp && (p.toppled || p.isItem || Math.hypot(p.x - base(p).x, p.z - base(p).z) > 1.0)) {
      const c = pickHelper(p); if (c) { p.mode = 'wait'; helperJob(p, c); return; }
      p.hwait += 0; if (!p.hw0) p.hw0 = W.time; if (W.time - p.hw0 < 6) return;   // 先等幾秒看有沒有人閒下來
    }
    selfReturn(p, p.urgent ? 0.7 : 1.5);
  }
  function selfReturn(p, T) {
    const b = base(p); P.stats.selfReturn++; p.hw0 = 0;
    p.ret = { t: 0, T: Math.max(T, Math.hypot(p.x - b.x, p.z - b.z) / 1.1 + 0.6), x0: p.x, z0: p.z, th0: p.th, dy0: p.dyaw, y0: p.y, hop: p.isItem ? 0.35 : 0.1, rho0: p.rho };
    p.mode = 'ret'; p.vx = p.vz = p.vy = 0; p.om = 0; p.air = false; p.settled = false;
  }
  function stepRet(p, h) {
    const r = p.ret, b = base(p); r.t += h; const u = clamp(r.t / r.T, 0, 1), e = easeOutBack(u), ep = easeIO(u);
    p.x = r.x0 + (b.x - r.x0) * ep; p.z = r.z0 + (b.z - r.z0) * ep;
    p.th = r.th0 * (1 - e); if (u >= 1) p.th = 0;
    p.dyaw = r.dy0 * (1 - ep); p.rho = r.rho0 * (1 - ep); const homeY = p.isItem ? p.baseY : 0;
    p.y = r.y0 + (homeY - r.y0) * ep + Math.sin(Math.PI * u) * r.hop; p.spinOn = p.isItem && u < 1; if (p.spinOn) p.spin.slerp(new Qn(), ep);
    if (u >= 1) { P.stats.restores++; W.emit('righted', p.id, { kind: p.kind, zh: p.K.zh, by: p.helperName || null }); toHome(p, true); }
  }
  async function helperJob(p, c) {
    const Dr = D(); if (!Dr) { selfReturn(p, 1.5); return; }
    const tok = c.script = (c.script || 0) + 1; c.busy = true; p.helper = c; p.helperName = c.spec.id; P.stats.helped++;
    const fail = () => { if (p.helper === c) p.helper = null; p.mode = 'move'; p.hw0 = 0; p.since = W.time - p.wait + 3; if (c.script === tok) { c.busy = false; Dr.goHome(c).then(() => { }); } };
    try {
      const b = base(p), from = { x: c.object3D.position.x, z: c.object3D.position.z };
      // 站在物件「靠近自己這一側」0.7 公尺處
      let ux = from.x - p.x, uz = from.z - p.z, ul = Math.hypot(ux, uz) || 1; ux /= ul; uz /= ul;
      let ap = W.nav.nearestFree(p.x + ux * 0.75, p.z + uz * 0.75, 6) || { x: p.x + ux * 0.9, z: p.z + uz * 0.9 };
      c.say && c.say(['我來扶', '東西倒了，我來', '我來收拾'][Math.floor(Math.random() * 3)], 1.6);
      P.trace && P.trace.push('goTo ' + c.spec.id);
      const ok = await Dr.goTo(c, { x: ap.x, z: ap.z, face: Math.atan2(p.x - ap.x, p.z - ap.z) }, { speed: 2.2 });
      P.trace && P.trace.push('arrived ' + ok + ' script ' + (c.script === tok) + ' mode ' + p.mode);
      if (!ok || c.script !== tok || p.mode !== 'wait') { if (p.mode === 'wait') fail(); return; }
      c.faceTo && c.faceTo(p.x, p.z); c.setAction('reach'); await W.sleep(0.45); if (c.script !== tok || p.mode !== 'wait') { if (p.mode === 'wait') fail(); return; }
      // 扶起來：傾角在 1.1 秒內回到 0（物件原地站直，手扶著）
      p.mode = 'lift'; p.lift = { t: 0, T: 1.1, th0: p.th, y0: p.y, rho0: p.rho, dy0: p.dyaw }; p.vx = p.vz = p.vy = 0; p.om = 0; p.air = false;
      while (p.mode === 'lift') { await W.sleep(0.1); if (c.script !== tok) { p.mode = 'move'; p.since = W.time - p.wait + 3; p.hw0 = 0; return; } }
      if (p.mode !== 'lifted') { fail(); return; }
      // 推回原位：站到「家那邊」往原位走，物件在身前被推著走
      const hx = b.x, hz = b.z; let wx = c.object3D.position.x - hx, wz = c.object3D.position.z - hz, wl = Math.hypot(wx, wz) || 1; wx /= wl; wz /= wl;
      const stand = W.nav.nearestFree(hx + wx * 0.8, hz + wz * 0.8, 6) || { x: hx + wx * 0.9, z: hz + wz * 0.9 };
      p.mode = 'carry'; p.carry = { c, u: 0 };
      const ok2 = await Dr.goTo(c, { x: stand.x, z: stand.z, face: Math.atan2(hx - stand.x, hz - stand.z) }, { speed: 1.5 });
      if (c.script !== tok || !ok2) { if (p.mode === 'carry') { p.mode = 'move'; p.since = W.time - p.wait + 3; p.hw0 = 0; p.carry = null; } if (c.script !== tok) return; }
      if (p.mode === 'carry') { p.carry = null; selfReturn(p, 0.55); p.helperName = c.spec.id; }
      c.setAction('nod'); await W.sleep(0.9);
      if (c.script === tok) { await Dr.goHome(c); if (c.script === tok) c.busy = false; }
    } catch (e) { console.error('同事扶東西的流程例外', e); if (c.script === tok) c.busy = false; }
  }
  function stepLift(p, h) {
    const l = p.lift; l.t += h; const u = clamp(l.t / l.T, 0, 1), e = easeIO(u); p.th = l.th0 * (1 - e); p.rho = l.rho0 * (1 - e); p.dyaw = l.dy0 * (1 - e); p.y = l.y0 + (p.isItem ? 0.5 * e : 0);
    if (u >= 1) { p.th = 0; p.rho = 0; p.dyaw = 0; p.mode = 'lifted'; }
  }

  // ───────────────────────── 主要每步 ─────────────────────────
  const gl = new V3();
  function lampSet(p) {
    // 立燈的光暈（夜間室內暖光點雲裡的一個點）：跟著燈罩移動；倒下時貼近地面；剛撞到時閃一下
    if (p.gi == null || !W.glowGeo) return;
    let x, y, z;
    if (p.mode === 'home' || !p.obj) { const f = p.inst.f; x = f.x; y = 1.35; z = f.z; }
    else { gl.set(0, 1.32, 0); gl.applyMatrix4(p.obj.matrixWorld); x = gl.x; y = Math.max(0.12, gl.y); z = gl.z; }
    const off = p.flick > 0 && Math.sin(W.time * 80) > 0.2;   // 撞到後燈閃爍（短暫熄滅）
    const yy = off ? -20 : y, a = W.glowGeo.attributes.position, L = p.glow;
    if (L && L.x === x && L.y === yy && L.z === z) { p.glow.real = { x, y, z }; return; }
    a.setXYZ(p.gi, x, yy, z); a.needsUpdate = true; p.glow = { x, y: yy, z, real: { x, y, z } };
  }
  P.lampGlow = id => { const p = P.props.find(q => q.inst && q.inst.f.id === id && q.kind === 'lamp'); return p && p.glow ? p.glow.real : null; };
  // 立燈的地面光斑：一個加法混色的網格（每盞燈一個四邊形），夜晚才看得到；燈倒下時光斑跟著燈罩移動、變小，剛撞到時閃爍
  let lpool = null;
  function lampPoolBuild() {
    const lamps = P.props.filter(p => p.kind === 'lamp'); if (!lamps.length) return;
    const n = lamps.length, pos = new Float32Array(n * 18), uv = new Float32Array(n * 12), col = new Float32Array(n * 18);
    for (let i = 0; i < n; i++) { const q = [[0, 0], [1, 0], [1, 1], [0, 0], [1, 1], [0, 1]]; for (let k = 0; k < 6; k++) { uv[i * 12 + k * 2] = q[k][0]; uv[i * 12 + k * 2 + 1] = q[k][1]; } }
    const cv = document.createElement('canvas'); cv.width = cv.height = 64; const c = cv.getContext('2d'), g = c.createRadialGradient(32, 32, 1, 32, 32, 31); g.addColorStop(0, 'rgba(255,224,170,0.85)'); g.addColorStop(0.5, 'rgba(255,205,140,0.32)'); g.addColorStop(1, 'rgba(255,190,120,0)'); c.fillStyle = g; c.fillRect(0, 0, 64, 64);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage)); geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); geo.setAttribute('color', new THREE.BufferAttribute(col, 3).setUsage(THREE.DynamicDrawUsage));
    const mat = new THREE.MeshBasicMaterial({ map: tex, vertexColors: true, color: '#ffffff', transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, fog: false });
    const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = 3; mesh.visible = false; W.scene.add(mesh); lpool = { mesh, geo, mat, lamps, pos, col, shown: [] };
  }
  P.lampPool = () => lpool;
  function lampPoolTick() {
    if (!lpool) return; const k = W.daytime && W.daytime.outL ? W.daytime.outL.k : 0; lpool.mesh.visible = k > 0.01; if (k <= 0.01) return; lpool.mat.opacity = k * 0.62;
    lpool.lamps.forEach((p, i) => {
      let cx, cz, r, br = 1; const f = p.inst.f;
      if (p.mode === 'home' || !p.obj) { cx = f.x; cz = f.z; r = 1.3; } else { gl.set(0, 1.32, 0).applyMatrix4(p.obj.matrixWorld); const hs = Math.max(0.1, gl.y); cx = gl.x; cz = gl.z; r = 0.38 + 0.92 * Math.min(1, hs / 1.35); br = 0.55 + 0.45 * Math.min(1, hs / 1.0); }
      if (p.flick > 0) br *= Math.sin(W.time * 80) > 0.2 ? 0.05 : 1;
      const y = 0.125, o = i * 18, v = [[-r, -r], [r, -r], [r, r], [-r, -r], [r, r], [-r, r]];
      for (let q = 0; q < 6; q++) { lpool.pos[o + q * 3] = cx + v[q][0]; lpool.pos[o + q * 3 + 1] = y; lpool.pos[o + q * 3 + 2] = cz + v[q][1]; lpool.col[o + q * 3] = lpool.col[o + q * 3 + 1] = lpool.col[o + q * 3 + 2] = br; }
      lpool.shown[i] = { x: cx, z: cz, r, br };
    });
    lpool.geo.attributes.position.needsUpdate = true; lpool.geo.attributes.color.needsUpdate = true;
  }
  P.lampSpots = () => lpool ? lpool.shown.slice() : [];

  let acc = 0, urgentT = 0;
  P.tick = h => {
    if (!P.on) return; if (!P.props.length && W.furn.size) { P.rebuild(); P.rebuildStatics(); }
    // 整修模式：先把所有東西瞬間歸位（手動擺放的位置就是新的原位）
    if (W.edit && W.edit.on) { if (P.props.some(p => p.mode !== 'home')) P.restoreAll(true); return; }
    // 角色 → 物件、角色 → 重家具
    for (const c of allChars()) {
      const ci = cinfo(c); if (!ci) continue;
      if (ci.fly || ci.sp > 2.4) { charVsProps(ci, h); }
      if (ci.fly && ci.sp > 0.3) charVsStatics(ci, h);
    }
    // 椅子的座位主人在椅子上（或快走到）→ 不讓它被撞；椅子還倒著而主人要坐了 → 立刻快速彈回
    urgentT -= h; const chk = urgentT <= 0; if (chk) urgentT = 0.2;
    for (const p of P.props) {
      if (p.kind === 'chair') {
        const sp = p.spotUid && (p.spot || W.spots.find(s => s.uid === p.spotUid)); const o = sp && sp.taken ? W.chars.get(sp.taken) : null;
        if (p.mode === 'home') p.locked = !!(o && (o.state === 'sit' || o._seat));
        else if (chk && o && (p.mode === 'move' || p.mode === 'wait') && Math.hypot(o.object3D.position.x - p.x, o.object3D.position.z - p.z) < 3.2) { p.urgent = true; if (p.mode === 'move') selfReturn(p, 0.7); }
        if (sp) sp.blocked = p.mode !== 'home';
      }
    }
    // 物件自己的運動
    const blobs = [];
    for (const p of P.props) {
      if (p.mode === 'home') continue;
      const ox = p.x, oz = p.z, oy = p.y, oth = p.th;
      if (p.mode === 'move') stepMove(p, h);
      else if (p.mode === 'ret') stepRet(p, h);
      else if (p.mode === 'lift') stepLift(p, h);
      else if (p.mode === 'carry') stepCarry(p, h);

      if (p.mode !== 'home') { if (p.obj) poseOf(p); const step = Math.hypot(p.x - ox, p.z - oz, p.y - oy); if (step > P.stats.maxStep && !(p.isItem && p.air)) { P.stats.maxStep = step; P.stats.maxStepId = p.id + ':' + p.mode; } if (p.mode !== 'home') blobs.push({ x: p.x, z: p.z, s: Math.max(0.7, p.r * 2.4) }); }
    }
    W.extraBlobs = blobs;
    for (const p of P.props) if (p.kind === 'lamp') { if (p.flick > 0) p.flick = Math.max(0, p.flick - h); lampSet(p); }
    lampPoolTick();
    // 被撞的家具抖一下
    for (let i = shakes.length - 1; i >= 0; i--) { const s = shakes[i]; s.t += h; const f = s.inst.f, k = Math.exp(-s.t * 9), o = s.inst.obj; if (s.t > 0.6) { shakes.splice(i, 1); W.place(s.inst); continue; } o.position.set(f.x + Math.sin(s.t * 70) * s.amp * k, 0, f.z + Math.cos(s.t * 63) * s.amp * k * 0.6); o.updateMatrixWorld(true); }
  };
  function stepCarry(p, h) {
    const c = p.carry && p.carry.c; if (!c) { p.mode = 'move'; return; }
    const cp = c.object3D.position, hd = c.heading || 0, tx = cp.x + Math.sin(hd) * 0.62, tz = cp.z + Math.cos(hd) * 0.62, dx = tx - p.x, dz = tz - p.z, d = Math.hypot(dx, dz), mv = Math.min(d, Math.max(d * (1 - Math.exp(-9 * h)), 0), 2.4 * h);   // 跟著同事走，但追趕速度有上限（不瞬移）
    if (d > 1e-6) { p.x += dx / d * mv; p.z += dz / d * mv; } p.th = 0; p.rho = 0; p.y += ((p.isItem ? 0.5 : 0) - p.y) * Math.min(1, 6 * h); p.vx = p.vz = 0;
  }
  // ───────────────────────── 對外 ─────────────────────────
  P.restoreAll = instant => { for (const p of P.props) { if (p.mode !== 'home') toHome(p, true); } W.extraBlobs = []; };
  P.displaced = () => P.props.filter(p => p.mode !== 'home');
  P.find = id => P.props.find(p => p.id === id);
  P.nearest = (kind, x, z, free = true) => { let b = null, bd = 1e9; for (const p of P.props) { if (p.kind !== kind || (free && p.locked)) continue; const q = base(p), d = Math.hypot(q.x - x, q.z - z); if (d < bd) { bd = d; b = p; } } return b; };
  P.homePos = p => base(p);
  // 手動撞一下（測試、其他模組用）：從 (fromX,fromZ) 以 speed 的速度撞向物件
  P.knock = (p, fromX, fromZ, speed, mass = 5.5) => { const b = base(p), dx = b.x - fromX, dz = b.z - fromZ, d = Math.hypot(dx, dz) || 1; return impart(p, dx / d, dz / d, speed, mass); };
  // 每幀畫面前後：鏡頭微晃（只在渲染那一刻加上偏移，渲染完立刻扣掉，不會累積漂移）
  let sx = 0, sy = 0, sz = 0;
  P.preRender = (dt) => { if (P.shake > 0.0015) { const a = P.shake; sx = (Math.random() - 0.5) * 2 * a; sy = (Math.random() - 0.5) * 2 * a; sz = (Math.random() - 0.5) * 2 * a; W.camera.position.x += sx; W.camera.position.y += sy; W.camera.position.z += sz; P.shake *= Math.exp(-9 * dt); } else { P.shake = 0; sx = sy = sz = 0; } };
  P.postRender = () => { if (sx || sy || sz) { W.camera.position.x -= sx; W.camera.position.y -= sy; W.camera.position.z -= sz; sx = sy = sz = 0; } };
  P.summary = () => P.props.filter(p => p.mode !== 'home').map(p => ({ id: p.id, kind: p.kind, mode: p.mode, x: +p.x.toFixed(2), z: +p.z.toFixed(2), th: +p.th.toFixed(2) }));

  P.rebuild(); P.rebuildStatics(); lampPoolBuild();
  W.respotHooks = (W.respotHooks || []); W.respotHooks.push(() => P.rebuildStatics());
  return P;
}
