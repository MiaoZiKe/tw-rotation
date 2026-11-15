// 指向外框（擁有者 11-16：「游標移動到員工身上，他周圍會有一層明顯的線條，我才知道有沒有指向到他」）
// 做法：只對「被指向的那一位」，替他身上每個網格各蓋一層「反面放大殼」（反面渲染、沿平滑法線在視空間推出去 N 公尺），
// 露在輪廓邊緣的那圈就是外框；移開就把殼拆掉。不用後處理，所以沒指向任何人時完全零成本，指向時只多十來個繪製呼叫。
// 粗細依鏡頭距離換算成「約 3 像素」：遠看也清楚、近看不會粗得蓋住臉。新舊角色（SkinnedMesh／一般網格）都支援。
import * as THREE from 'three';

const PX = 3.6;                    // 外框粗細（螢幕像素）
const smoothCache = new WeakMap(); // 原幾何 → 殼用幾何（共用同一份頂點緩衝，只換一組平滑法線）

// 同一個位置的頂點（方塊的角、被切開的接縫）法線取平均，外推時才不會裂開
function hullGeometry(g) {
  let h = smoothCache.get(g); if (h) return h;
  const pos = g.attributes.position, nor = g.attributes.normal; if (!pos || !nor) { smoothCache.set(g, null); return null; }
  const n = pos.count, acc = new Map(), key = i => Math.round(pos.getX(i) * 2000) + ',' + Math.round(pos.getY(i) * 2000) + ',' + Math.round(pos.getZ(i) * 2000), ks = new Array(n);
  for (let i = 0; i < n; i++) { const k = ks[i] = key(i); let a = acc.get(k); if (!a) acc.set(k, a = [0, 0, 0]); a[0] += nor.getX(i); a[1] += nor.getY(i); a[2] += nor.getZ(i); }
  const sm = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { const a = acc.get(ks[i]), l = Math.hypot(a[0], a[1], a[2]) || 1; sm[i * 3] = a[0] / l; sm[i * 3 + 1] = a[1] / l; sm[i * 3 + 2] = a[2] / l; }
  h = new THREE.BufferGeometry();
  for (const k in g.attributes) if (k !== 'normal') h.setAttribute(k, g.attributes[k]);
  h.setAttribute('normal', new THREE.BufferAttribute(sm, 3));
  if (g.index) h.setIndex(g.index);
  if (g.morphAttributes && Object.keys(g.morphAttributes).length) { h.morphAttributes = g.morphAttributes; h.morphTargetsRelative = g.morphTargetsRelative; }   // 身體形態鍵（胖瘦、壓扁）：殼要跟本體同形，不然縮在身體裡面看不到
  h.groups = g.groups; h.boundingSphere = g.boundingSphere; h.boundingBox = g.boundingBox;
  smoothCache.set(g, h); return h;
}

export function createOutline(W, { camera, cv }) {
  const uThk = { value: 0.03 };
  const mat = new THREE.MeshBasicMaterial({ color: '#ff8a1f', side: THREE.BackSide, fog: false, toneMapped: false, depthWrite: true });
  mat.onBeforeCompile = sh => {
    sh.uniforms.uThk = uThk;
    sh.vertexShader = 'uniform float uThk;\n' + sh.vertexShader.replace('#include <project_vertex>',
      `#include <project_vertex>
      #if defined( USE_SKINNING )
        vec3 olN = normalize( transformedNormal );
      #else
        vec3 olN = normalize( normalMatrix * normal );
      #endif
      mvPosition.xyz += olN * uThk;
      gl_Position = projectionMatrix * mvPosition;`);
  };
  mat.customProgramCacheKey = () => 'dh-outline-v1';
  const O = { target: null, hulls: [], mat, count: 0, shown: 0 };
  const tmpV = new THREE.Vector3();

  function eligible(m) {
    if (!m.isMesh || m.userData.dhOutline || m.isInstancedMesh) return false;
    if (m.name && /decal|shadow|blob/i.test(m.name)) return false;
    const mm = Array.isArray(m.material) ? m.material[0] : m.material; if (!mm || mm.transparent || mm.visible === false) return false;
    return !!(m.geometry && m.geometry.attributes.normal);
  }
  function clear() {
    for (const h of O.hulls) { if (h.parent) h.parent.remove(h); }
    O.hulls.length = 0; O.target = null;
  }
  O.set = c => {
    if (c === O.target) return; clear(); if (!c) return;
    O.target = c; const src = [];
    c.object3D.traverse(m => { if (eligible(m)) src.push(m); });
    for (const m of src) {
      const g = hullGeometry(m.geometry); if (!g) continue; let h;
      if (m.isSkinnedMesh) { h = new THREE.SkinnedMesh(g, mat); h.bind(m.skeleton, m.bindMatrix); h.position.copy(m.position); h.quaternion.copy(m.quaternion); h.scale.copy(m.scale); (m.parent || c.object3D).add(h); }
      else { h = new THREE.Mesh(g, mat); m.add(h); }
      if (m.morphTargetInfluences) { h.morphTargetInfluences = m.morphTargetInfluences; h.morphTargetDictionary = m.morphTargetDictionary; }   // 共用同一個陣列，本體形態怎麼動殼就怎麼動
      h.userData.dhOutline = true; h.userData.src = m; h.frustumCulled = false; h.castShadow = false; h.receiveShadow = false; h.renderOrder = 4; h.raycast = () => { };
      O.hulls.push(h);
    }
    O.count++; O.shown = O.hulls.length; O.frame();
  };
  // 每格：粗細換成世界公尺（距離越遠越粗，維持約 PX 像素）、殼的可見跟著原網格
  O.frame = () => {
    const c = O.target; if (!c) return;
    const d = camera.position.distanceTo(c.object3D.getWorldPosition(tmpV)), pxPerM = cv.clientHeight / (2 * Math.tan(camera.fov * Math.PI / 360) * Math.max(0.5, d));
    uThk.value = Math.min(0.4, Math.max(0.012, PX / pxPerM));
    for (const h of O.hulls) h.visible = h.userData.src.visible;
  };
  O.clear = clear;
  return O;
}
