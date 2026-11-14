// 跟隨視角的「遮擋閃避」（驗收員 11-15：跟隨鏡頭被路燈整根擋住角色）。
// 做法：跟隨角色時，每 0.35 秒從鏡頭往角色頭部射一條線，若中間先撞到家具或遊民區的靜態物件（路燈、長椅、拱門…）
// 就把鏡頭繞著角色平順轉開一個角度（依 ±0.35、±0.7、±1.05、±1.4 弧度挑第一個「看得到頭」的位置）；都擋住就不動。
// 為什麼不用把遮擋物淡化：家具與遊民區都是合併成一個網格的，無法只淡化其中一根路燈。
// 只在使用者沒有拖曳鏡頭的 1.5 秒之後才動，不跟手動運鏡搶；轉開之後 1.2 秒內不再重算，避免來回抖。
import * as THREE from 'three';

export function createCamClear(W, X) {
  const { camera, controls, view } = X, C = { moves: 0 }, ray = new THREE.Raycaster(), a = new THREE.Vector3(), d = new THREE.Vector3(), head = new THREE.Vector3(), off = new THREE.Vector3(), cand = new THREE.Vector3();
  let acc = 0, quiet = 0, goal = null, list = [], listT = 0, outMesh = null;
  const blockers = () => { if (performance.now() / 1000 - listT > 1 || !list.length) { listT = performance.now() / 1000;   /* 用真實時間：畫面很卡時模擬時間走得慢，清單會太久才更新 */ list = []; outMesh = W.outside && W.outside.mesh || null; if (outMesh) list.push(outMesh); for (const i of W.furn.values()) if (i.mesh && i.mesh.visible && i.obj.visible) list.push(i.mesh); } return list; };
  // 遊民區的靜態物件（路燈離角色只有 0.2～0.3 公尺）：射線一路算到頭部前 8 公分；以前一律排除頭部前 0.6 公尺，剛好把路燈排除、鏡頭被擋 15 秒都不動。
  // 辦公室家具維持排除頭部前 0.6 公尺（坐著的人自己的桌椅就在身邊，算進去會一直被判成擋住）。
  const hit = (objs, from, to, tail) => { d.copy(to).sub(from); const L = d.length(); if (L < 0.5) return false; ray.set(from, d.normalize()); ray.far = L - tail; ray.near = 0.2; return ray.intersectObjects(objs, false).length > 0; };
  const one = (from, to) => (outMesh && hit([outMesh], from, to, 0.08)) || hit(list.filter(o => o !== outMesh), from, to, 0.6);
  const side = new THREE.Vector3(), tl = new THREE.Vector3(), tr = new THREE.Vector3();
  // 頭部中心與身體左右兩側（各 0.3 公尺）共 3 條線，任一被擋就算擋住：路燈可能只蓋住半邊身體
  const blockedFrom = (from, to) => { blockers(); side.set(to.z - from.z, 0, from.x - to.x); if (side.lengthSq() < 1e-6) return one(from, to); side.normalize().multiplyScalar(0.3); tl.copy(to).add(side); tr.copy(to).sub(side); return one(from, to) || one(from, tl) || one(from, tr); };
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
