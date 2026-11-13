// 角色視角（擁有者 11-13：「需要再新增該角色視角」）：鏡頭放到選取角色的眼睛，從他看出去的樣子看辦公室。
//
// 入口：資訊卡「角色視角」鈕、視角切換列在有選取時多出的「角色視角」格、鍵盤 V（手機：操控列「視角」鈕）。
// 離開：Esc、再按一次 V／同一顆鈕、點別人、切到別的視角、取消選取（自動退出）。
//
// 做法（為什麼不用 OrbitControls）：角色視角的鏡頭「綁在頭上」，每幀由角色的眼睛位置與朝向決定，OrbitControls 的環繞模型不適用，
//   所以進入時暫時關掉它（連滑鼠按鍵設定也清空，避免它在背景累積位移，離開時鏡頭突然跳掉），離開時用 modeControls 恢復。
//   進出各有約 0.5 秒的平順過渡（位置、朝向、視野都插值）；快到頭上時才把自己的身體藏起來（放到第 1 層，主鏡頭只畫第 0 層，
//   不動 visible，所以碰撞、「按 E 溝通」的對象判斷、導演排程都不受影響）。
// 視線：
//   頭的轉動（左鍵拖曳／觸控單指）＝相對身體的偏移，左右 ±150 度、上下 −60～+52 度；拖曳的方向跟「旋轉」模式一致（抓著畫面拖）。
//   放開後的規則（刻意的）：上下視角停 2.5 秒就慢慢回到平視；左右視角在「站著不動」時維持你轉過去的方向，
//   一旦身體開始往前走就慢慢回正（走路時人會看著前進的方向）。
//   操控中：↑ ↓ ＝往前、往後（相對身體前方）、← → ＝身體轉向（視角跟著轉），所以「前進＝角色前方」。
// 鏡頭保護：不進入別人的身體（把鏡頭推出去）、不超出辦公室範圍、站的格子是空的才做家具退讓；眼睛高度依身高、坐姿、漂浮算出。
import * as THREE from 'three';

const V3 = THREE.Vector3, FOV = 68, NEAR = 0.05, DUR = 0.5;
const YAW_LIM = 2.6, PIT_MIN = -1.05, PIT_MAX = 0.9;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const ease = k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const angDiff = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b));

export function createPOV(W, X) {
  const { camera, controls, cv, view } = X;
  // st: 'off' 沒開｜'in' 進入過渡｜'on' 在角色視角｜'out' 離開過渡
  const P = { c: null, st: 'off', yaw: 0, pitch: 0, t: 0, saved: null, lastDrag: -10, still: 0, eye: new V3(), cur: new V3(), curSet: false };
  const q0 = new THREE.Quaternion(), q1 = new THREE.Quaternion(), qa = new THREE.Quaternion(), e1 = new THREE.Euler(0, 0, 0, 'YXZ'), m4 = new THREE.Matrix4(), up = new V3(0, 1, 0), v1 = new V3(), v2 = new V3();
  const sel = () => W.pilot && W.pilot.sel;

  P.on = () => P.st !== 'off';                 // 角色視角開著（含進出過渡）
  P.active = () => P.st === 'in' || P.st === 'on';   // 操控以角色身體方向為準（pilot.js 用）
  P.driving = () => P.st !== 'off';            // 鏡頭由這裡接手（主迴圈用）
  P.hides = c => P.st !== 'off' && P.c === c;  // 這個角色的名牌不顯示（主迴圈用）

  const quatLook = (p, t, out) => { m4.lookAt(p, t, up); return out.setFromRotationMatrix(m4); };
  function eyeQuat(out) { e1.set(P.pitch, P.c.inner.yaw + P.yaw + Math.PI, 0, 'YXZ'); return out.setFromEuler(e1); }

  P.enter = c => {
    c = c || sel(); if (c && sel() !== c && W.pilot && !c.jobless && !c.away && !c.spec.pet) W.pilot.select(c);     // 資訊卡上別人的「角色視角」：先選取他
    if (!c || c.jobless || c.away || c.spec.pet || P.st === 'in' || P.st === 'on') return false;
    if (P.st === 'out') finish(true);
    P.c = c; P.yaw = 0; P.pitch = 0; P.t = 0; P.st = 'in'; P.curSet = false; P.lastDrag = -10;
    P.saved = { off: camera.position.clone().sub(controls.target), fov: camera.fov, near: camera.near, p: camera.position.clone(), q: camera.quaternion.clone(), mode: view.mode };
    controls.enabled = false; controls.enableRotate = controls.enablePan = controls.enableZoom = false; controls.mouseButtons = { LEFT: -1, MIDDLE: -1, RIGHT: -1 }; controls.touches = {};
    view.tween = null; camera.near = NEAR; camera.updateProjectionMatrix();
    X.ui.setPovUI(true, c);        // 操作說明在鏡頭提示（右上）與操作提示卡，不再跳 toast（會蓋到名牌）
    return true;
  };
  // 離開。instant＝立刻回到原鏡頭（要切去別的視角時用）；否則 0.5 秒平順飛回原本的視角
  P.exit = instant => {
    if (P.st === 'off') return;
    const c = P.c; if (c) c.hideFromCam(false);
    if (instant) { finish(true); return; }
    if (P.st === 'out') return;
    P.st = 'out'; X.ui.setPovUI(false, c);        // P.t 維持目前進度（在切入途中離開，就從那一格倒回去，不會跳一下）
  };
  P.toggle = c => { if (P.on() && P.st !== 'out') P.exit(); else P.enter(c); };
  function restorePose() {
    const c = P.c, t = X.charTarget(c, new V3()), p = t.clone().add(P.saved.off); if (p.y < 0.8) p.y = 0.8; return { t, p };
  }
  function finish(instant) {
    const c = P.c, S = P.saved; if (!S) { P.st = 'off'; P.c = null; return; }
    if (c) c.hideFromCam(false);
    const r = c ? restorePose() : null;
    camera.near = S.near; camera.fov = S.fov; camera.updateProjectionMatrix();
    if (r) { camera.position.copy(r.p); controls.target.copy(r.t); }
    else { controls.target.copy(camera.position).add(v1.set(0, 0, -10).applyQuaternion(S.q)); camera.position.copy(S.p); }
    X.restoreControls(); controls.enabled = true; controls.update();
    view.tween = null; view.detached = false; view.pull = 0; view.last = null;
    P.st = 'off'; P.c = null; P.saved = null; X.ui.setPovUI(false, null);
    if (c && sel() === c) { view.mode = 'char'; view.char = c; X.ui.setViewUI('char', c); }
  }

  // ── 視線：左鍵（觸控單指）拖曳 ──
  let drag = null;
  cv.addEventListener('pointerdown', e => {
    if (P.st !== 'on' || e.button !== 0 || X.isGrabbing() || X.downChar()) return;
    if (e.pointerType === 'touch' && !e.isPrimary) return;
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY };
  });
  cv.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id || P.st !== 'on' || X.isGrabbing()) return;
    const k = X.cam.sens, dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
    P.yaw = clamp(P.yaw + dx / Math.max(1, cv.clientWidth) * Math.PI * k, -YAW_LIM, YAW_LIM);        // 全寬拖曳 ＝ 180 度；右拖 ＝ 往左看（抓著畫面拖）
    P.pitch = clamp(P.pitch + dy / Math.max(1, cv.clientHeight) * Math.PI * 0.8 * k, PIT_MIN, PIT_MAX);
    P.lastDrag = performance.now() / 1000;
  });
  const dragEnd = e => { if (drag && e.pointerId === drag.id) drag = null; };
  addEventListener('pointerup', dragEnd); addEventListener('pointercancel', dragEnd);
  P.dragging = () => !!drag;

  // ── 每幀：由主迴圈在 updateCamera 的位置呼叫（角色視角開著時取代 OrbitControls） ──
  P.cam = dt => {
    const c = P.c;
    // 自動退出：取消選取、角色被開除／離開、被換了身體（改造型）
    if (!c || W.chars.get(c.spec.id) !== c || c.jobless || c.away) { finish(true); return; }
    if (P.st !== 'out' && sel() !== c) { P.exit(); }
    // 放開後的回正規則
    const now = performance.now() / 1000, still = now - P.lastDrag > 1.2 && !drag, sp = Math.hypot(c.inner.vel.x, c.inner.vel.z);
    if (P.st === 'on' && !drag) {
      if (now - P.lastDrag > 2.5) P.pitch += (0 - P.pitch) * Math.min(1, dt * 1.6);
      if (still && sp > 0.35) P.yaw += (0 - P.yaw) * Math.min(1, dt * 1.8);
    }
    c.hideFromCam(P.st === 'on' || (P.st === 'in' && P.t > 0.8));     // 快到頭上時才藏身體；離開時（上面 exit）一開始就顯示
    if (P.st === 'out') c.hideFromCam(false);
    c.eye(v1);
    // 眼睛位置輕微低通，走路的上下晃動不會讓人暈
    if (!P.curSet) { P.cur.copy(v1); P.curSet = true; } else { const k = 1 - Math.exp(-dt * 26); P.cur.lerp(v1, k); P.cur.x = v1.x; P.cur.z = v1.z; }
    P.eye.copy(P.cur); guard(P.eye, c);
    eyeQuat(q1);
    let k = 1;
    if (P.st === 'in') { P.t = Math.min(1, P.t + dt / DUR); k = ease(P.t); if (P.t >= 1) P.st = 'on'; }
    else if (P.st === 'out') { P.t = Math.max(0, P.t - dt / DUR); k = ease(P.t); }
    if (P.st === 'in' || P.st === 'out') {
      const S = P.saved;
      if (P.st === 'in') { camera.position.lerpVectors(S.p, P.eye, k); camera.quaternion.slerpQuaternions(S.q, q1, k); camera.fov = S.fov + (FOV - S.fov) * k; }
      else { const r = restorePose(); quatLook(r.p, r.t, qa); camera.position.lerpVectors(r.p, P.eye, k); camera.quaternion.slerpQuaternions(qa, q1, k); camera.fov = S.fov + (FOV - S.fov) * k; }
      camera.updateProjectionMatrix();
      if (P.st === 'out' && P.t <= 0) finish(true);
      return;
    }
    camera.position.copy(P.eye); camera.quaternion.copy(q1); if (camera.fov !== FOV) { camera.fov = FOV; camera.updateProjectionMatrix(); }
  };

  // 不穿牆、不穿別人：把鏡頭推到合理的位置
  function guard(p, c) {
    const B = W.layout.size; p.x = clamp(p.x, 0.3, B.w - 0.3); p.z = clamp(p.z, 0.3, B.d + 9);
    const bp = c.object3D.position;
    if (W.nav && W.nav.isFree(bp.x, bp.z) && !W.nav.isFree(p.x, p.z)) {      // 身體站的格子是空的、鏡頭前方卻是家具：往身體中心退到空的地方
      for (let i = 1; i <= 5; i++) { v2.set(p.x + (bp.x - p.x) * i / 5, 0, p.z + (bp.z - p.z) * i / 5); if (W.nav.isFree(v2.x, v2.z)) { p.x = v2.x; p.z = v2.z; break; } }
    }
    for (const o of X.everyone()) {
      if (o === c || !o.object3D.visible || o.away) continue;
      const q = o.object3D.position, dx = p.x - q.x, dz = p.z - q.z, d = Math.hypot(dx, dz), r = (o.radius || 0.35) + 0.1;
      if (d < r && p.y < (o.height || 1) + (o.lift || 0) + 0.2 && d > 1e-4) { p.x = q.x + dx / d * r; p.z = q.z + dz / d * r; }
    }
  }
  return P;
}
