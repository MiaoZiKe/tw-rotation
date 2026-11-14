// 跟隨視角的「遮擋閃避」（驗收員 11-15：跟隨鏡頭被路燈整根擋住角色）。
// 做法：跟隨角色時，每 0.35 秒從鏡頭往角色頭部射一條線，若中間先撞到家具或遊民區的靜態物件（路燈、長椅、拱門…）
// 就把鏡頭繞著角色平順轉開一個角度（依 ±0.35、±0.7、±1.05、±1.4 弧度挑第一個「看得到頭」的位置）；都擋住就不動。
// 為什麼不用把遮擋物淡化：家具與遊民區都是合併成一個網格的，無法只淡化其中一根路燈。
// 只在使用者沒有拖曳鏡頭的 1.5 秒之後才動，不跟手動運鏡搶；轉開之後 1.2 秒內不再重算，避免來回抖。
import * as THREE from 'three';

export function createCamClear(W, X) {
  const { camera, controls, view } = X, C = { moves: 0 }, ray = new THREE.Raycaster(), a = new THREE.Vector3(), d = new THREE.Vector3(), head = new THREE.Vector3(), off = new THREE.Vector3(), cand = new THREE.Vector3();
  let acc = 0, quiet = 0, goal = null, list = [], listT = 0;
  const blockers = () => { if (W.time - listT > 2 || !list.length) { listT = W.time; list = []; if (W.outside && W.outside.mesh) list.push(W.outside.mesh); for (const i of W.furn.values()) if (i.mesh && i.mesh.visible && i.obj.visible) list.push(i.mesh); } return list; };
  const blockedFrom = (from, to) => { d.copy(to).sub(from); const L = d.length(); if (L < 0.5) return false; ray.set(from, d.normalize()); ray.far = L - 0.6; ray.near = 0.2; return ray.intersectObjects(blockers(), false).length > 0; };
  C.tick = dt => {
    const c = view.char;
    if (view.mode !== 'char' || !c || view.tween || (W.pov && W.pov.on())) { goal = null; return; }
    if (goal) {                                                         // 平順移到新位置（保留與角色的距離與高度，只轉方位）
      const k = Math.min(1, dt * 5); camera.position.lerp(goal, k); if (camera.position.distanceToSquared(goal) < 0.0025) goal = null; return;
    }
    if (performance.now() / 1000 - view.lastUser < 1.5) return;
    acc += dt; quiet -= dt; if (acc < 0.35 || quiet > 0) return; acc = 0;
    const p = c.object3D.position, hy = 0.9 * (c.scale || 1); head.set(p.x, hy, p.z);
    if (!blockedFrom(camera.position, head)) return;
    off.copy(camera.position).sub(head); const r = Math.hypot(off.x, off.z), base = Math.atan2(off.x, off.z);
    for (const da of [0.35, -0.35, 0.7, -0.7, 1.05, -1.05, 1.4, -1.4]) {
      cand.set(head.x + Math.sin(base + da) * r, camera.position.y, head.z + Math.cos(base + da) * r);
      if (cand.x < 0.5 || cand.x > W.layout.size.w + 14 || cand.z < 0.5 || cand.z > W.layout.size.d + 14) continue;
      if (!blockedFrom(cand, head)) { goal = cand.clone(); quiet = 1.2; C.moves++; return; }
    }
  };
  const pf = X.pilot.frame; X.pilot.frame = (dt, t) => { pf(dt, t); C.tick(dt); };
  return C;
}
