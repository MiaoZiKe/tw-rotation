// 火焰與燒焦（2026-11-14 擁有者：「火焰、燈光、動作行為都要更符合物理世界……碰到火焰會燒起來、燒焦，然後過一陣子主動復原」）。
//
// 做了什麼
//   1. 營火火苗：舊的「兩個錐體」換成一個合併網格的多舌火焰（外焰橘紅 3～4 條、中焰橘黃、內焰白黃，底下一圈餘燼），
//      頂點著色器讓每條火舌有各自的相位：高度上下跳、尖端左右擺、根部穩定；高度與亮度用同一個時間函數 W.fireFlick(毫秒)，
//      daytime.js 的營火光斑（地面光暈）也讀它，所以「火苗長高時光斑變亮」。白天火苗照樣看得到（不透明漸層），光斑本來就只在傍晚後出現。
//   2. 火星與煙：兩個點雲（加法混色的火星／火舌，一般混色的灰煙與黑煙）共用一個粒子池，火星往上飄、受微風左右飄、漸漸變暗熄滅；
//      營火上方有淡淡的灰煙。小燭（火焰角色）頭上也有火星。
//   3. 碰到火：角色（被丟、被操控跑到邊上、走路經過）進入營火範圍 → 身上冒出火舌與煙、驚慌跑開（有小跳）、
//      約 3～5 秒後火熄滅（extinguished）；身體表面用材質疊一層焦黑斑紋（著色器，不改模型、不改貼圖）逐漸變黑、
//      焦邊微微發紅橘；頭頂冒一縷黑煙。之後 30～60 秒（模擬時間）角色主動走去休息區坐下、拍拍身體，焦黑慢慢褪回原色（recovered）。
//      小燭（火焰角色）不會被燒。卡通可愛：只有黑炭臉、頭頂冒煙，沒有任何受傷的表現。
//   4. 事件：burned、extinguished、recovered（W.emit(型態, 角色代號, 附加欄位)），表情由情緒系統（mind.js）決定。
//
// 效能：新增繪製 = 火焰網格 1（取代舊的 1）＋ 粒子 2（火星、煙）；焦黑不增加繪製（只換著色器）。
import { THREE } from './kit.js';

const V3 = THREE.Vector3, clamp = (x, a, b) => Math.max(a, Math.min(b, x)), rnd = (a, b) => a + Math.random() * (b - a);
const reduce = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

// 火焰的亮度／高度：毫秒的純函數（daytime.js 的營火光斑也用它），範圍約 0.15～0.95
export const fireFlick = tt => 0.55 + 0.2 * Math.sin(tt * 0.011) + 0.12 * Math.sin(tt * 0.023 + 1.3) + 0.08 * Math.sin(tt * 0.047);

const SOOT_GLSL = `
float scH(vec3 p){ p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float scN(vec3 x){ vec3 i = floor(x), f = fract(x); f = f*f*(3.0-2.0*f);
  return mix(mix(mix(scH(i+vec3(0,0,0)),scH(i+vec3(1,0,0)),f.x), mix(scH(i+vec3(0,1,0)),scH(i+vec3(1,1,0)),f.x), f.y),
             mix(mix(scH(i+vec3(0,0,1)),scH(i+vec3(1,0,1)),f.x), mix(scH(i+vec3(0,1,1)),scH(i+vec3(1,1,1)),f.x), f.y), f.z); }
`;
const SOOT_FRAG = `
if (uScorch > 0.002) {
  float scn = scN(vScP * 9.0) * 0.55 + scN(vScP * 21.0) * 0.30 + scN(vScP * 47.0) * 0.15;
  float scm = smoothstep(1.0 - uScorch * 1.18, 1.0 - uScorch * 1.18 + 0.2, scn + clamp(vScP.y * 0.5, 0.0, 1.0) * 0.12 + uScorch * 0.22);
  vec3 sootC = vec3(0.075, 0.065, 0.07) * (0.75 + 0.5 * scn);
  outgoingLight = mix(outgoingLight, sootC, scm * 0.93);
  float scEdge = smoothstep(0.0, 0.12, scm) * (1.0 - smoothstep(0.35, 0.7, scm));
  outgoingLight += vec3(1.0, 0.38, 0.08) * scEdge * uEmber * 0.8;
}
`;

export function createFire(W, opts = {}) {
  const F = { cfg: { range: 1.2, recoverMin: 30, recoverMax: 60, burnMin: 3.2, burnMax: 4.8, smoke: 9, fade: 7 }, states: new Map(), stats: { ignited: 0, recovered: 0, patched: 0, particles: 0 }, on: true };
  W.fire = F; W.fireFlick = fireFlick;
  const scene = W.scene, O = W.outside, D = () => W.director, allChars = () => [...W.chars.values(), ...(W.pets || []), ...(W.extras || [])];
  const fx = O ? O.fire.x : 30.2, fz = O ? O.fire.z : 36.6;
  F.center = { x: fx, z: fz };

  // ───────────────────────── 營火火焰網格 ─────────────────────────
  const flameMat = new THREE.ShaderMaterial({
    uniforms: { uT: { value: 0 }, uK: { value: 0.6 }, uNight: { value: 0 } },
    transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false, forceSinglePass: true,   // 雙面透明預設會畫兩次；火焰一次就夠（省 1 次繪製）
    vertexShader: `
      uniform float uT, uK; attribute float aH, aSeed, aLayer, aLen; attribute vec3 aLean; varying float vH, vL; varying vec2 vXZ;
      void main(){
        float h = aH, wob = 0.88 + 0.22 * uK + 0.10 * sin(uT * 9.0 + aSeed * 6.3) + 0.05 * sin(uT * 17.0 + aSeed * 3.1);
        vec3 p = position; float ring = pow(max(0.0, 1.0 - h), 0.75);
        p.xz *= ring;
        float sway = sin(uT * 4.6 + aSeed * 11.0 + h * 3.6) * 0.11 + sin(uT * 10.5 + aSeed * 7.0 + h * 6.2) * 0.045;
        p.xz += aLean.xz * h * h + vec2(sway, cos(uT * 3.9 + aSeed * 5.0 + h * 2.4) * 0.07) * h * h;
        p.y = h * aLen * wob;
        if (aLayer > 1.5) { p = position; p.y = 0.03; }
        vH = h; vL = aLayer; vXZ = position.xz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
      }`,
    fragmentShader: `
      uniform float uK, uNight; varying float vH, vL; varying vec2 vXZ;
      void main(){
        vec3 c; float a;
        if (vL > 1.5) { float d = length(vXZ) / 0.52; a = (1.0 - smoothstep(0.55, 1.0, d)) * (0.55 + 0.4 * uK); c = mix(vec3(1.0, 0.55, 0.16), vec3(0.9, 0.2, 0.06), d); }
        else if (vL > 0.66) { c = mix(vec3(1.0, 1.0, 0.9), vec3(1.0, 0.93, 0.55), vH); a = 0.97 - 0.5 * smoothstep(0.6, 1.0, vH); }
        else if (vL > 0.33) { c = mix(vec3(1.0, 0.88, 0.38), vec3(1.0, 0.6, 0.18), vH); a = 0.94 - 0.6 * smoothstep(0.5, 1.0, vH); }
        else { c = mix(vec3(1.0, 0.56, 0.14), vec3(0.93, 0.24, 0.07), vH); a = 0.93 - 0.7 * smoothstep(0.45, 1.0, vH); }
        c *= 0.9 + 0.2 * uK + 0.15 * uNight; gl_FragColor = vec4(c, a);
      }`
  });
  function buildFlameGeo() {
    const pos = [], aH = [], aSeed = [], aLayer = [], aLen = [], aLean = [], idx = []; const SEG = 10, RAD = 8; let seed = 0;
    const tongue = (layer, rad, len, lx, lz, ox, oz) => {
      const base = pos.length / 3; seed += 1.37;
      for (let j = 0; j <= SEG; j++) for (let i = 0; i < RAD; i++) {
        const a = i / RAD * Math.PI * 2, h = j / SEG;
        pos.push(ox + Math.cos(a) * rad, 0, oz + Math.sin(a) * rad); aH.push(h); aSeed.push(seed); aLayer.push(layer); aLen.push(len); aLean.push(lx, 0, lz);
      }
      for (let j = 0; j < SEG; j++) for (let i = 0; i < RAD; i++) { const a = base + j * RAD + i, b = base + j * RAD + (i + 1) % RAD, c = a + RAD, d = b + RAD; idx.push(a, b, c, b, d, c); }
    };
    // 外焰（橘紅，高而寬）、中焰（橘黃）、內焰（白黃，矮而窄）；每條有自己的傾斜方向與相位
    [[0.30, 0.78, 0.05, -0.02, 0.12, 0.05], [0.27, 1.02, -0.07, 0.04, -0.10, 0.08], [0.28, 0.86, 0.02, 0.08, 0.03, -0.13], [0.24, 0.7, 0.06, -0.06, -0.06, -0.1]].forEach(q => tongue(0.1, q[0], q[1], q[2], q[3], q[4], q[5]));
    [[0.2, 0.88, -0.03, 0.03, 0.04, 0.03], [0.19, 0.7, 0.04, -0.02, -0.05, 0.02], [0.18, 0.78, 0, 0.05, 0.02, -0.06]].forEach(q => tongue(0.5, q[0], q[1], q[2], q[3], q[4], q[5]));
    [[0.12, 0.56, 0.01, 0.01, 0, 0], [0.1, 0.46, -0.02, 0.0, 0.03, -0.02]].forEach(q => tongue(0.9, q[0], q[1], q[2], q[3], q[4], q[5]));
    // 底下一圈餘燼（貼地的圓盤）
    { const base = pos.length / 3; pos.push(0, 0, 0); aH.push(0); aSeed.push(0); aLayer.push(2); aLen.push(0); aLean.push(0, 0, 0);
      for (let i = 0; i <= 20; i++) { const a = i / 20 * Math.PI * 2; pos.push(Math.cos(a) * 0.52, 0, Math.sin(a) * 0.52); aH.push(0); aSeed.push(0); aLayer.push(2); aLen.push(0); aLean.push(0, 0, 0); if (i > 0) idx.push(base, base + i, base + i + 1); } }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('aH', new THREE.Float32BufferAttribute(aH, 1)); g.setAttribute('aSeed', new THREE.Float32BufferAttribute(aSeed, 1));
    g.setAttribute('aLayer', new THREE.Float32BufferAttribute(aLayer, 1)); g.setAttribute('aLen', new THREE.Float32BufferAttribute(aLen, 1)); g.setAttribute('aLean', new THREE.Float32BufferAttribute(aLean, 3)); g.setIndex(idx);
    g.boundingSphere = new THREE.Sphere(new V3(0, 0.6, 0), 1.6); return g;
  }
  let flame = null;
  if (O && O.flame) {
    O.flame.visible = false; O.flame.removeFromParent();   // 舊的兩個錐體
    flame = new THREE.Mesh(buildFlameGeo(), flameMat); flame.position.set(fx, 0.2, fz); flame.renderOrder = 2; flame.frustumCulled = false; scene.add(flame); O.flame = flame; F.flame = flame;
    O.frame = () => { };   // outside.js 每幀對舊火苗做縮放的程式不再需要；火焰的動態在頂點著色器裡
  }

  // ───────────────────────── 粒子池 ─────────────────────────
  const uScale = { value: 800 };
  const mkPool = (n, additive) => {
    const g = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), size = new Float32Array(n), col = new Float32Array(n * 4);
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage)); g.setAttribute('aSize', new THREE.BufferAttribute(size, 1).setUsage(THREE.DynamicDrawUsage)); g.setAttribute('aCol', new THREE.BufferAttribute(col, 4).setUsage(THREE.DynamicDrawUsage));
    const m = new THREE.ShaderMaterial({
      uniforms: { uScale }, transparent: true, depthWrite: false, fog: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
      vertexShader: 'attribute float aSize; attribute vec4 aCol; uniform float uScale; varying vec4 vC; void main(){ vC = aCol; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_PointSize = clamp(aSize * uScale / max(0.1, -mv.z), 0.0, 96.0); gl_Position = projectionMatrix * mv; }',
      fragmentShader: 'varying vec4 vC; void main(){ float d = length(gl_PointCoord - 0.5) * 2.0; float a = (1.0 - smoothstep(0.35, 1.0, d)); gl_FragColor = vec4(vC.rgb, vC.a * a); }'
    });
    const pts = new THREE.Points(g, m); pts.frustumCulled = false; pts.renderOrder = additive ? 6 : 4; scene.add(pts);
    return { n, pos, size, col, g, pts, p: [], head: 0, live: 0 };
  };
  const PA = mkPool(360, true), PS = mkPool(170, false);   // PA：火星、火舌（加法）；PS：灰煙、黑煙（一般）
  F.pools = { PA, PS };
  function spawn(pool, x, y, z, vx, vy, vz, life, s0, s1, type, o = {}) {
    const i = pool.head; pool.head = (pool.head + 1) % pool.n;
    pool.p[i] = { x, y, z, vx, vy, vz, age: 0, life, s0, s1, type, sw: Math.random() * 6.28, dr: o.drag ?? 1.2, g: o.g ?? 0, alive: true };
  }
  const sizeK = () => (W.camera ? 1 : 1);
  function stepPool(pool, h) {
    let live = 0;
    for (let i = 0; i < pool.n; i++) {
      const p = pool.p[i];
      if (!p || !p.alive) { pool.size[i] = 0; pool.col[i * 4 + 3] = 0; continue; }
      p.age += h; const u = p.age / p.life; if (u >= 1) { p.alive = false; pool.size[i] = 0; pool.col[i * 4 + 3] = 0; continue; }
      live++;
      const wind = Math.sin(p.age * 2.2 + p.sw) * 0.35;
      p.vx += (wind - p.vx) * Math.min(1, p.dr * h); p.vz += (Math.cos(p.age * 1.7 + p.sw) * 0.25 - p.vz) * Math.min(1, p.dr * h); p.vy += p.g * h;
      p.x += p.vx * h; p.y += p.vy * h; p.z += p.vz * h;
      pool.pos[i * 3] = p.x; pool.pos[i * 3 + 1] = p.y; pool.pos[i * 3 + 2] = p.z;
      let r, g, b, a, s = p.s0 + (p.s1 - p.s0) * u;
      switch (p.type) {
        case 0: { const k = 1 - u; r = 1; g = 0.45 + 0.5 * k * k; b = 0.12 + 0.35 * k * k * k; a = (u < 0.1 ? u / 0.1 : 1 - Math.pow(u, 1.5)) * (0.75 + 0.25 * Math.sin(p.age * 40 + p.sw)); break; }   // 火星：黃白 → 橘 → 暗紅
        case 1: { r = 1; g = 0.62 - 0.45 * u; b = 0.15 - 0.1 * u; a = (u < 0.15 ? u / 0.15 : 1 - u) * 0.85; break; }                                         // 火舌：橘 → 紅
        case 2: { const t = 0.62 + 0.1 * Math.sin(p.sw); r = g = b = t; a = (u < 0.2 ? u / 0.2 : 1 - u) * 0.2; break; }                                      // 灰煙
        default: { r = 0.12; g = 0.1; b = 0.11; a = (u < 0.12 ? u / 0.12 : 1 - u) * 0.62; }                                                                  // 黑煙
      }
      pool.size[i] = s; pool.col[i * 4] = r; pool.col[i * 4 + 1] = g; pool.col[i * 4 + 2] = b; pool.col[i * 4 + 3] = a;
    }
    pool.live = live;
  }
  function upload(pool) { pool.g.attributes.position.needsUpdate = true; pool.g.attributes.aSize.needsUpdate = true; pool.g.attributes.aCol.needsUpdate = true; }
  F.emit = { spark: (x, y, z, o) => spawn(PA, x, y, z, rnd(-0.25, 0.25), rnd(0.8, 1.7), rnd(-0.25, 0.25), rnd(0.9, 2.0), 0.07, 0.02, 0, { drag: 1.2 }), };

  // ───────────────────────── 材質：焦黑疊色（不改模型、不改貼圖）─────────────────────────
  // 材質有沒有被好幾位角色共用（共用的不能疊焦黑：不然一位燒焦、別人也跟著黑）
  let useMap = null, useN = -1;
  function usage() {
    const cs = allChars(); if (useMap && useN === cs.length) return useMap; useMap = new Map(); useN = cs.length;
    for (const c of cs) c.object3D.traverse(o => { if (!o.isMesh || !o.material) return; for (const m of Array.isArray(o.material) ? o.material : [o.material]) { let a = useMap.get(m); if (!a) useMap.set(m, a = new Set()); a.add(c); } });
    return useMap;
  }
  function ensureScorch(c) {
    if (c._scorchPatched) return; c._scorchPatched = true;
    const u = c._sootU = { value: 0 }, e = c._emberU = { value: 0 }, seen = new Set(), use = usage();
    c.object3D.traverse(o => {
      if (!o.isMesh || !o.material || o.userData.prop === 'cushion') return;
      for (const mat of Array.isArray(o.material) ? o.material : [o.material]) {
        if (seen.has(mat) || mat.userData._scOwner || !mat.isMeshStandardMaterial || (mat.transparent && mat.map) || /decal|lid/i.test(o.name || '') || (use.get(mat) && use.get(mat).size > 1)) continue; seen.add(mat); mat.userData._scOwner = c.spec.id;
        const prev = mat.onBeforeCompile, key = mat.customProgramCacheKey;
        mat.onBeforeCompile = (sh, r) => {
          if (prev) prev.call(mat, sh, r);
          sh.uniforms.uScorch = u; sh.uniforms.uEmber = e;
          sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vScP;').replace('#include <begin_vertex>', '#include <begin_vertex>\n vScP = position;');
          sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vScP; uniform float uScorch, uEmber;\n' + SOOT_GLSL).replace('#include <opaque_fragment>', SOOT_FRAG + '\n#include <opaque_fragment>');
        };
        mat.customProgramCacheKey = () => (key ? key.call(mat) : '') + '|scorch1'; mat.needsUpdate = true; F.stats.patched++;
      }
    });
  }
  F.ensureScorch = ensureScorch;

  // ───────────────────────── 角色燒起來 ─────────────────────────
  const imm = c => c.look && c.look.species === 'flame';   // 小燭本身就是火焰
  const st = c => F.states.get(c.spec.id);
  F.stateOf = c => st(c) || { state: 'none', scorch: 0 };
  F.scorch = c => (c._sootU ? c._sootU.value : 0);
  const posOf = c => c.object3D.position;
  function ignite(c, why) {
    if (!F.on || imm(c)) return false; const s = st(c);
    if (s && s.state === 'burning') return false;
    ensureScorch(c);
    const o = s || { state: 'none', scorch: 0 }; F.states.set(c.spec.id, o);
    const wasRec = o.state === 'recovering';
    Object.assign(o, { state: 'burning', t: 0, dur: rnd(F.cfg.burnMin, F.cfg.burnMax), c, hop: 0, tok: (o.tok || 0) + 1, start: { x: posOf(c).x, z: posOf(c).z }, fled: 0, why });
    F.stats.ignited++;
    // 接管這個角色：取消正在做的事、放開操控、不讓別的流程把他叫走
    const Dr = D(); c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.atDesk = false; if (c.stop) c.stop(false);
    if (W.pilot && W.pilot.releaseIf) { try { W.pilot.releaseIf(c); } catch (e) { /* 沒被操控就算了 */ } }
    if (c.spot && c.spot.taken === c.spec.id && c.state !== 'sit') { /* 座位保留給他，之後走回去 */ }
    if (wasRec) o.scorch = c._sootU.value;
    W.emit && W.emit('burned', c.spec.id, { x: posOf(c).x, z: posOf(c).z, why: why || 'campfire' });
    return true;
  }
  F.ignite = ignite;
  function fleeDir(c, o, s) {
    const p = posOf(c); let dx = p.x - fx, dz = p.z - fz, d = Math.hypot(dx, dz); if (d < 0.05) { const a = Math.random() * 6.28; dx = Math.cos(a); dz = Math.sin(a); d = 1; }
    dx /= d; dz /= d;
    for (const da of [0, 0.6, -0.6, 1.2, -1.2, 1.9, -1.9]) {   // 前面被擋就轉一個角度
      const cs = Math.cos(da), sn = Math.sin(da), vx = dx * cs - dz * sn, vz = dx * sn + dz * cs;
      if (W.nav.isFree(p.x + vx * 0.5, p.z + vz * 0.5)) return { x: vx, z: vz };
    }
    return { x: dx, z: dz };
  }
  function grounded(c) { if (c.newModel) { const ctl = c.inner.ctl; return ctl.body.grounded && ctl.state !== 'tumble' && ctl.state !== 'air'; } const ch = c.inner; return ch.grounded && ch.mode === 'normal'; }
  function jumpHop(c) { if (c.newModel) { try { c.inner.ctl.jump(); } catch (e) { /* 跳不起來就算了 */ } } else if (c.inner && c.inner.jumpBuf !== undefined) c.inner.jumpBuf = 0.15; }
  const sampleBody = (c, out) => { const p = posOf(c), a = Math.random() * 6.28, r = (c.radius || 0.3) * rnd(0.2, 0.8); return out.set(p.x + Math.cos(a) * r, (c.lift || 0) + rnd(0.15, 0.85) * (c.height || 0.8), p.z + Math.sin(a) * r); };
  const tmp = new V3();

  function tickChar(o, h) {
    const c = o.c, id = c.spec.id, p = posOf(c); o.t += h;
    if (o.state === 'burning') {
      // 阻止別的流程把他叫走（落地後導演的「被丟之後」流程會自己開始走路）
      if (c._path) { c.stop(false); c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; }
      const dist = Math.hypot(p.x - fx, p.z - fz);
      // 驚慌跑開（落地才能跑）：離火 ≥ 2.6 公尺、而且燒夠了才停；中途小跳
      if (grounded(c)) {
        const run = fleeDir(c, o); o.hop -= h; if (o.hop <= 0 && dist < 3) { o.hop = rnd(0.55, 1.0); jumpHop(c); }
        const sp = 3.3 * (c.scale || 1); c.drive(run.x * sp, run.z * sp, run.x, run.z);
      }
      // 身上的火舌與煙
      o.emit = (o.emit || 0) + h * 38; while (o.emit >= 1) { o.emit--; sampleBody(c, tmp); spawn(PA, tmp.x, tmp.y, tmp.z, rnd(-0.2, 0.2), rnd(0.8, 1.5), rnd(-0.2, 0.2), rnd(0.35, 0.6), rnd(0.2, 0.3) * (c.scale || 1), 0.04, 1, { drag: 3 }); }
      o.emitS = (o.emitS || 0) + h * 9; while (o.emitS >= 1) { o.emitS--; sampleBody(c, tmp); spawn(PS, tmp.x, tmp.y + 0.3, tmp.z, rnd(-0.1, 0.1), rnd(0.5, 0.9), rnd(-0.1, 0.1), rnd(1.4, 2.2), 0.14, 0.55, 3, { drag: 1.5 }); }
      if (Math.random() < h * 14) { sampleBody(c, tmp); spawn(PA, tmp.x, tmp.y + 0.1, tmp.z, rnd(-0.5, 0.5), rnd(1.2, 2.2), rnd(-0.5, 0.5), rnd(0.8, 1.5), 0.06, 0.02, 0, { drag: 1 }); }
      // 焦黑逐漸加深（燒夠 → 約 0.9）
      const target = clamp(0.5 + o.t / o.dur * 0.45, 0, 0.95); c._sootU.value = Math.max(c._sootU.value, Math.min(target, c._sootU.value + h * 0.35)); c._emberU.value = 1;
      if (o.t >= o.dur && (dist > 2.6 || o.t > o.dur + 3.5)) {
        o.state = 'smoldering'; o.t = 0; o.recoverAt = rnd(F.cfg.recoverMin, F.cfg.recoverMax); c.drive(null); c._sootU.value = Math.max(c._sootU.value, 0.9);
        W.emit && W.emit('extinguished', id, {});
      }
    } else if (o.state === 'smoldering') {
      // 剛燒完先愣在原地（臉黑黑、頭頂冒煙）：別的流程（被丟之後的「走回座位」）不准把他叫走，等時間到了才主動去休息區
      if (c._path && !c._held) { c.stop(false); c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; }
      // 火熄了：餘燼的紅光很快褪掉、頭頂冒一縷黑煙，焦黑留著
      c._emberU.value = Math.max(0, c._emberU.value - h * 0.6);
      o.emitS = (o.emitS || 0) + h * F.cfg.smoke * (o.t < 12 ? 1 : 0.35); while (o.emitS >= 1) { o.emitS--; spawn(PS, p.x + rnd(-0.04, 0.04), (c.lift || 0) + (c.height || 0.8) * 0.98, p.z + rnd(-0.04, 0.04), rnd(-0.05, 0.05), rnd(0.45, 0.7), rnd(-0.05, 0.05), rnd(2.0, 3.0), 0.09 * (c.scale || 1), 0.4 * (c.scale || 1), 3, { drag: 1.0 }); }
      if (o.t >= o.recoverAt && !c._held && c.state !== 'held' && !c.away) { o.state = 'recovering'; o.t = 0; o.s0 = c._sootU.value; recoverJob(o); }
    } else if (o.state === 'recovering') {
      if (o.fading) { const u = clamp(o.fadeT / F.cfg.fade, 0, 1); o.fadeT += h; c._sootU.value = o.s0 * (1 - u * u * (3 - 2 * u)); if (u >= 1 && !o.done) { o.done = true; c._sootU.value = 0; } }
      else if (o.t > 3 && o.t % 1 < h) { /* 還在走去休息區 */ }
    }
  }
  async function recoverJob(o) {
    const c = o.c, tok = o.tok, Dr = D(), id = c.spec.id, alive = () => o.tok === tok && o.state === 'recovering';
    try {
      c.busy = true; c.script = (c.script || 0) + 1; const stk = c.script;
      // 走去休息區（沙發、懶骨頭）坐下；找不到就原地
      const spot = W.spot && (W.spot('sofa', posOf(c), id) || W.spot('bean', posOf(c), id));
      if (spot && Dr) { c.setAction('idle'); const ok = await Dr.goTo(c, spot, { speed: 1.8 }); if (!alive() || c.script !== stk) return; if (!ok) { /* 沒走到：就地拍拍身體 */ } }
      if (!alive()) return;
      c.setAction('clap'); await W.sleep(0.9); if (!alive()) return;   // 拍拍身體：把灰拍掉（舊新兩種角色都有的「拍手」姿勢）
      o.fading = true; o.fadeT = 0; c.setAction('clap'); await W.sleep(1.4); if (!alive()) return; c.setAction('idle');
      while (alive() && !o.done) await W.sleep(0.2);
      if (!alive()) return;
      o.state = 'none'; o.scorch = 0; c._sootU.value = 0; c._emberU.value = 0; F.stats.recovered++;
      W.emit && W.emit('recovered', id, {});
      if (Dr) { await Dr.goHome(c); } if (c.script === stk) c.busy = false;
    } catch (e) { console.error('燒焦恢復流程例外', e); c.busy = false; }
  }

  // ───────────────────────── 每個模擬步 ─────────────────────────
  let simAcc = 0, patchT = 0, patchI = 0, candleT = 0, smokeT = 0, sparkT = 0;
  F.tick = h => {
    if (!F.on) return;
    // 營火：火星、淡淡的灰煙（火苗大時多一點）
    const k = fireFlick(performance.now());
    if (!reduce) {
      sparkT += h * (7 + 14 * k); while (sparkT >= 1) { sparkT--; const a = Math.random() * 6.28, r = Math.random() * 0.22; spawn(PA, fx + Math.cos(a) * r, 0.5 + Math.random() * 0.4, fz + Math.sin(a) * r, rnd(-0.25, 0.25), rnd(0.9, 1.9), rnd(-0.25, 0.25), rnd(1.0, 2.2), 0.075, 0.02, 0, { drag: 1.1 }); }
      smokeT += h * 2.2; while (smokeT >= 1) { smokeT--; spawn(PS, fx + rnd(-0.12, 0.12), 1.0 + Math.random() * 0.2, fz + rnd(-0.12, 0.12), rnd(-0.05, 0.05), rnd(0.35, 0.55), rnd(-0.05, 0.05), rnd(2.4, 3.6), 0.2, 0.75, 2, { drag: 0.8 }); }
    }
    // 小燭頭上的火星（火焰角色）
    candleT += h; if (candleT > 0.18 && !reduce) { candleT = 0; for (const c of allChars()) if (imm(c) && c.object3D.visible && !c.away && Math.random() < 0.55) { const p = posOf(c); spawn(PA, p.x + rnd(-0.06, 0.06), (c.lift || 0) + (c.height || 0.8) * 0.95, p.z + rnd(-0.06, 0.06), rnd(-0.15, 0.15), rnd(0.6, 1.2), rnd(-0.15, 0.15), rnd(0.7, 1.3), 0.05 * (c.scale || 1), 0.015, 0, { drag: 1.3 }); } }
    // 進入火範圍的角色：被丟的、被操控的、走路經過的
    for (const c of allChars()) {
      if (imm(c) || !c.object3D.visible || c.away) continue; const s = st(c);
      if (s && s.state === 'burning') continue;
      if (c._seat && c.state === 'sit') continue;
      const p = posOf(c), d = Math.hypot(p.x - fx, p.z - fz);
      if (d < F.cfg.range && (c.lift || 0) < 1.0) { if (!(s && s.cool && W.time < s.cool)) ignite(c, 'campfire'); }
    }
    for (const o of F.states.values()) { if (o.state !== 'none') tickChar(o, h); }
    // 背景把每個角色的材質先補好焦黑著色器（不在第一次燒的瞬間才編譯）
    patchT += h; if (patchT > 0.4) { patchT = 0; const cs = allChars(); for (let n = 0; n < cs.length && n < 40; n++) { const c = cs[(patchI + n) % cs.length]; if (!c._scorchPatched && c.object3D.parent) { ensureScorch(c); patchI = (patchI + n + 1) % cs.length; break; } } }
    stepPool(PA, h); stepPool(PS, h); simAcc += h;
  };
  // 每一畫面：上傳粒子、更新火焰的時間參數、粒子大小的換算係數
  F.frame = real => {
    const now = performance.now(), K = fireFlick(now), cam = W.camera, rend = W.renderer;
    flameMat.uniforms.uT.value = reduce ? 0 : now / 1000; flameMat.uniforms.uK.value = reduce ? 0.6 : clamp((K - 0.15) / 0.8, 0, 1) * 0.9 + 0.1;   // 系統設定「減少動態效果」時火焰靜止
    const nk = W.daytime && W.daytime.outL ? W.daytime.outL.k : 0; flameMat.uniforms.uNight.value = nk;
    uScale.value = (rend.domElement.height) / (2 * Math.tan(cam.fov * Math.PI / 360)) * 1.0;
    upload(PA); upload(PS); F.stats.particles = PA.live + PS.live;
  };
  F.reset = () => { for (const o of F.states.values()) { o.state = 'none'; o.tok++; if (o.c && o.c._sootU) o.c._sootU.value = 0; o.c && o.c.drive && o.c.drive(null); if (o.c) o.c.busy = false; } for (const pl of [PA, PS]) pl.p.length = 0; };
  return F;
}
