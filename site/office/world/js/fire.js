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
import { footToWorld } from './nav.js';
import { WET_SEC } from './sports_water.js';

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
  const F = { cfg: { range: 1.45, recoverMin: 30, recoverMax: 60, burnMin: 8, burnMax: 12, smoke: 9, fade: 7, maxBurning: 4, maxFurn: 6, furnRecMin: 20, furnRecMax: 40, contact: 0.85 }, states: new Map(), stats: { ignited: 0, recovered: 0, patched: 0, particles: 0 }, on: true };
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
  const PA = mkPool(560, true), PS = mkPool(300, false);   // PA：火星、火舌（加法）；PS：灰煙、黑煙（一般）
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
        case 5: { r = 1; g = 0.55; b = 0.2; a = (u < 0.25 ? u / 0.25 : 1 - u) * 0.14; break; }                                                                 // 家具著火的光暈（大而淡的橘光）
        case 4: { r = g = b = 0.96; a = (u < 0.12 ? u / 0.12 : 1 - u) * 0.5; break; }                                                                       // 水蒸氣（被水澆熄的瞬間，白白的一團）
        default: { r = 0.12; g = 0.1; b = 0.11; a = (u < 0.12 ? u / 0.12 : 1 - u) * 0.62; }                                                                  // 黑煙
      }
      pool.size[i] = s; pool.col[i * 4] = r; pool.col[i * 4 + 1] = g; pool.col[i * 4 + 2] = b; pool.col[i * 4 + 3] = a;
    }
    pool.live = live;
  }
  function upload(pool) { pool.g.attributes.position.needsUpdate = true; pool.g.attributes.aSize.needsUpdate = true; pool.g.attributes.aCol.needsUpdate = true; }
  F.emit = { spark: (x, y, z, o) => spawn(PA, x, y, z, rnd(-0.25, 0.25), rnd(0.8, 1.7), rnd(-0.25, 0.25), rnd(0.9, 2.0), 0.07, 0.02, 0, { drag: 1.2 }),
    // 情緒層用的小特效（2026-11-16）：汗滴（白點往下掉）、白色蒸氣（熄火喘氣）、黑色小煙（咳嗽吐煙）
    drop: (x, y, z) => spawn(PS, x, y, z, rnd(-0.5, 0.5), rnd(0.5, 1.1), rnd(-0.5, 0.5), rnd(0.45, 0.7), 0.05, 0.04, 4, { drag: 0.6, g: -5 }),
    steam: (x, y, z) => spawn(PS, x, y, z, rnd(-0.2, 0.2), rnd(0.5, 1.0), rnd(-0.2, 0.2), rnd(1.0, 1.7), 0.12, 0.5, 4, { drag: 1.5 }),
    soot: (x, y, z) => spawn(PS, x, y, z, rnd(-0.15, 0.15), rnd(0.35, 0.7), rnd(-0.15, 0.15), rnd(1.0, 1.6), 0.08, 0.38, 3, { drag: 1.2 }) };

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
  // 濕的人（剛出泳池、被水桶或飲水機澆過）15 秒內碰到火：冒一陣白煙、「滋」一聲，不會著火；乾了以後照常會燒（11-16 擁有者）
  const isWet = c => (c._fireImmuneUntil || 0) > W.time || !!(W.sports && W.sports.water && W.sports.water.inWater && W.sports.water.inWater(c));
  F.isWet = isWet;
  F.sfx = { on: (() => { try { return localStorage.getItem('aiOffice.sfx') !== '0'; } catch (e) { return true; } })(), played: 0, ctx: null,
    sizzle() {   // 短促白噪音（高頻帶通、約 0.35 秒淡出）；系統設定「減少動態效果」或音效關閉時不響；瀏覽器還沒允許播放聲音時也不響
      if (!F.sfx.on || reduce) return false;
      try {
        const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return false; const x = F.sfx.ctx || (F.sfx.ctx = new AC()); if (x.state !== 'running') return false;
        const len = Math.floor(x.sampleRate * 0.35), buf = x.createBuffer(1, len, x.sampleRate), d = buf.getChannelData(0); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
        const src = x.createBufferSource(); src.buffer = buf; const f = x.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 5200; f.Q.value = 0.8; const g = x.createGain(); g.gain.value = 0.08;
        src.connect(f); f.connect(g); g.connect(x.destination); src.start(); F.sfx.played++; return true;
      } catch (e) { return false; }
    } };
  function sizzle(c) {
    if (W.time - (c._sizT || -9) < 1.6) return; c._sizT = W.time; F.stats.sizzled = (F.stats.sizzled || 0) + 1;
    const p = posOf(c); for (let i = 0; i < 12; i++) spawn(PS, p.x + rnd(-0.25, 0.25), (c.lift || 0) + (c.height || 0.8) * rnd(0.1, 0.8), p.z + rnd(-0.25, 0.25), rnd(-0.3, 0.3), rnd(0.8, 1.5), rnd(-0.3, 0.3), rnd(0.9, 1.5), 0.14 * (c.scale || 1), 0.6 * (c.scale || 1), 4, { drag: 1.6 });
    F.sfx.sizzle(); c.emote && c.emote('steam', 1.2);
    W.emit && W.emit('sizzled', c.spec.id, { x: p.x, z: p.z });
  }
  const burningCount = () => { let n = 0; for (const o of F.states.values()) if (o.state === 'burning') n++; return n; };
  function ignite(c, why, from) {
    if (!F.on || imm(c)) return false; const s = st(c);
    if (s && s.state === 'burning') return false;
    if (isWet(c)) { sizzle(c); return false; }
    if (why === 'contact' && burningCount() >= F.cfg.maxBurning) return false;   // 同時著火的角色上限（傳火才受限）
    ensureScorch(c);
    const o = s || { state: 'none', scorch: 0 }; F.states.set(c.spec.id, o);
    const wasRec = o.state === 'recovering';
    Object.assign(o, { state: 'burning', t: 0, dur: rnd(F.cfg.burnMin, F.cfg.burnMax), c, hop: 0, tok: (o.tok || 0) + 1, start: { x: posOf(c).x, z: posOf(c).z }, fled: 0, heldFor: 0, why, wash: false, quick: false, done: false, fading: false });
    F.stats.ignited++;
    // 接管這個角色：取消正在做的事、放開操控、不讓別的流程把他叫走
    const Dr = D(); c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.atDesk = false; if (c.stop) c.stop(false);
    if (W.pilot && W.pilot.releaseIf) { try { W.pilot.releaseIf(c); } catch (e) { /* 沒被操控就算了 */ } }
    if (c.spot && c.spot.taken === c.spec.id && c.state !== 'sit') { /* 座位保留給他，之後走回去 */ }
    if (wasRec) o.scorch = c._sootU.value;
    W.emit && W.emit('burned', c.spec.id, { x: posOf(c).x, z: posOf(c).z, why: why || 'campfire', from: from || null });
    if (F.helperFor) F.helperFor({ kind: 'char', c });
    return true;
  }
  F.ignite = ignite;
  // 熄火介面（2026-11-15，泳池）：燒著的人被水澆熄 → 立刻停止燃燒（不用等燒夠時間）、冒一團白色水蒸氣、事件 'extinguished' 附 cause。
  // cause 'pool'：身體泡過水，焦黑很快就洗掉（約 3 秒後自己走去休息區拍拍身體），不用等 30～60 秒。回傳是否真的熄了火。
  F.extinguish = (c, cause = 'pool', by) => {
    const o = st(c); if (!o || o.state !== 'burning') return false;
    o.state = 'smoldering'; o.t = 0; o.recoverAt = cause === 'pool' ? 0 : rnd(F.cfg.recoverMin, F.cfg.recoverMax); o.why = cause; o.wash = cause === 'pool'; c.drive && c.drive(null);
    if (cause === 'water' || cause === 'bucket') { c._wetUntil = W.time + WET_SEC; c._fireImmuneUntil = W.time + WET_SEC; }   // 被飲水機的水或水桶澆熄：身上濕 15 秒（同泳池）
    c._sootU.value = Math.max(c._sootU.value, 0.35); c._emberU.value = 0;
    const p = posOf(c); for (let i = 0; i < 16; i++) spawn(PS, p.x + rnd(-0.2, 0.2), (c.lift || 0) + (c.height || 0.8) * rnd(0.2, 0.9), p.z + rnd(-0.2, 0.2), rnd(-0.25, 0.25), rnd(0.7, 1.4), rnd(-0.25, 0.25), rnd(0.9, 1.6), 0.15 * (c.scale || 1), 0.55 * (c.scale || 1), 4, { drag: 1.6 });
    F.stats.extinguished = (F.stats.extinguished || 0) + 1;
    W.emit && W.emit('extinguished', c.spec.id, { cause, x: p.x, z: p.z, by: by || null });
    return true;
  };
  // 洗淨介面（2026-11-16，泳池）：身上有焦黑（冒煙愣著、走去休息區的路上、正在褪色）的人泡進水裡 → 焦黑在水裡約 2 秒內洗掉。
  //   洗掉的只有「焦黑疊色」這一層（著色器的 uScorch / uEmber 兩個數值）；材質本身的顏色、漸層、貼圖、腮紅、配件顏色都沒碰過，洗完照原樣。
  //   燒著的人走 F.extinguish（先熄火，再洗）。回傳是否有東西要洗。
  F.wash = c => {
    const o = st(c); if (!o || o.state === 'none' || !c._sootU) return false;
    if (o.state === 'burning') return F.extinguish(c, 'pool');
    if (c._sootU.value <= 0.002 && !o.wash) return false;
    if (!o.wash) { o.wash = true; o.s0 = c._sootU.value; F.stats.washed = (F.stats.washed || 0) + 1; W.emit && W.emit('washed', c.spec.id, { x: posOf(c).x, z: posOf(c).z }); }
    return true;
  };
  function fleeDir(c, o, s) {
    const p = posOf(c); let dx = p.x - fx, dz = p.z - fz, d = Math.hypot(dx, dz); if (d < 0.05) { const a = Math.random() * 6.28; dx = Math.cos(a); dz = Math.sin(a); d = 1; }
    dx /= d; dz /= d;
    for (const da of [0, 0.6, -0.6, 1.2, -1.2, 1.9, -1.9]) {   // 前面被擋就轉一個角度
      const cs = Math.cos(da), sn = Math.sin(da), vx = dx * cs - dz * sn, vz = dx * sn + dz * cs;
      if (W.nav.isFree(p.x + vx * 0.5, p.z + vz * 0.5)) return { x: vx, z: vz };
    }
    return { x: dx, z: dz };
  }
  function grounded(c) { if (c._held || c.state === 'held') return false; if (c.newModel) { const ctl = c.inner.ctl; return ctl.body.grounded && ctl.state !== 'tumble' && ctl.state !== 'air'; } const ch = c.inner; return ch.grounded && ch.mode === 'normal'; }
  function jumpHop(c) { if (c.newModel) { try { c.inner.ctl.jump(); } catch (e) { /* 跳不起來就算了 */ } } else if (c.inner && c.inner.jumpBuf !== undefined) c.inner.jumpBuf = 0.15; }
  const sampleBody = (c, out) => { const p = posOf(c), a = Math.random() * 6.28, r = (c.radius || 0.3) * rnd(0.2, 0.8); return out.set(p.x + Math.cos(a) * r, (c.lift || 0) + rnd(0.15, 0.85) * (c.height || 0.8), p.z + Math.sin(a) * r); };
  const tmp = new V3();

  function tickChar(o, h) {
    const c = o.c, id = c.spec.id, p = posOf(c); o.t += h;
    if (o.wash && o.state !== 'burning') {   // 泡過水：焦黑與餘燼用約 2 秒洗掉（只動疊色數值，不碰材質）
      c._sootU.value = Math.max(0, c._sootU.value - h * 0.5); c._emberU.value = 0;
      if (o.state === 'smoldering' && c._sootU.value <= 0.002 && !c._held && c.state !== 'held' && !c.away) { c._sootU.value = 0; o.state = 'recovering'; o.t = 0; o.s0 = 0; o.quick = true; recoverJob(o); }
      else if (o.state === 'smoldering' && c._sootU.value <= 0.002) c._sootU.value = 0;
    }
    if (o.state === 'burning') {
      // 阻止別的流程把他叫走（落地後導演的「被丟之後」流程會自己開始走路）
      if (c._path) { c.stop(false); c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; }
      const dist = Math.hypot(p.x - fx, p.z - fz);
      if ((c._held || c.state === 'held') && (o.heldFor = (o.heldFor || 0) + h) < 14) o.t -= h;   // 被拎著時燃燒時間不倒數（放下後繼續跑去滅火；最多凍結 14 秒）
      // 驚慌跑開（落地才能跑）：離火 ≥ 2.6 公尺、而且燒夠了才停；中途小跳
      if (grounded(c)) {
        const sty = F.steer && F.steer(c, o, h, dist);   // 情緒層（mind_feel.js）接管走法：亂跑繞圈、原地跳腳、拍打、蹲下、跑向泳池（傳回 null 就走預設的直線逃開）
        if (sty) { c.drive(sty.vx, sty.vz, sty.fx, sty.fz); if (sty.hop) jumpHop(c); }
        else { const run = fleeDir(c, o); o.hop -= h; if (o.hop <= 0 && dist < 3) { o.hop = rnd(0.55, 1.0); jumpHop(c); }
          const sp = 3.3 * (c.scale || 1); c.drive(run.x * sp, run.z * sp, run.x, run.z); }
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
      if (o.fading) { const u = clamp(o.fadeT / F.cfg.fade, 0, 1); o.fadeT += h; const v = o.s0 * (1 - u * u * (3 - 2 * u)); c._sootU.value = o.wash ? Math.min(c._sootU.value, v) : v; if ((u >= 1 || (o.wash && c._sootU.value <= 0.002)) && !o.done) { o.done = true; c._sootU.value = 0; } }
      else if (o.wash && c._sootU.value <= 0.002) { c._sootU.value = 0; }
      else if (o.t > 3 && o.t % 1 < h) { /* 還在走去休息區 */ }
    }
  }
  async function recoverJob(o) {
    const c = o.c, tok = o.tok, Dr = D(), id = c.spec.id, alive = () => o.tok === tok && o.state === 'recovering';
    try {
      c.busy = true; c.script = (c.script || 0) + 1; const stk = c.script;
      // 走去休息區（沙發、懶骨頭）坐下；找不到就原地
      const spot = !o.quick && W.spot && (W.spot('sofa', posOf(c), id) || W.spot('bean', posOf(c), id));   // 泳池洗乾淨的（quick）不用再走去休息區
      if (spot && Dr) { c.setAction('idle'); const ok = await Dr.goTo(c, spot, { speed: 1.8 }); if (!alive() || c.script !== stk) return; if (!ok) { /* 沒走到：就地拍拍身體 */ } }
      if (!alive()) return;
      c.setAction(o.quick ? 'idle' : 'clap'); await W.sleep(o.quick ? 0.4 : 0.9); if (!alive()) return;   // 拍拍身體：把灰拍掉（舊新兩種角色都有的「拍手」姿勢）
      o.fading = true; o.fadeT = o.quick ? F.cfg.fade : 0; c.setAction(o.quick ? 'idle' : 'clap'); await W.sleep(o.quick ? 0.3 : 1.4); if (!alive()) return; c.setAction('idle');
      while (alive() && !o.done) await W.sleep(0.2);
      if (!alive()) return;
      o.state = 'none'; o.scorch = 0; o.wash = false; o.quick = false; c._sootU.value = 0; c._emberU.value = 0; F.stats.recovered++;
      W.emit && W.emit('recovered', id, {});
      if (Dr) { await Dr.goHome(c); } if (c.script === stk) c.busy = false;
    } catch (e) { console.error('燒焦恢復流程例外', e); c.busy = false; }
  }


  // ───────────────────────── 人傳火、人點燃家具、同事拿水桶去滅（11-16 擁有者追加）─────────────────────────
  // 規則：只有「燒著的人 → 別人」「燒著的人 → 可燃家具」；家具不傳給人、家具不傳給家具（避免連鎖失控）。
  // 家具上限同時 F.cfg.maxFurn 個著火；火焰、煙、光暈全部共用上面兩個粒子池；焦黑是一層深色半透明疊在家具外觀上（共用同一份幾何，不複製模型）。
  const COMB = { workstation: [20, 25], ceo_desk: [20, 25], meeting_table: [20, 25], dining: [18, 24], coffee_table: [16, 22], side_table: [16, 22], bookshelf: [20, 25], cabinet: [18, 24], sofa: [18, 23], armchair: [16, 21], beanbag: [15, 19], bench: [16, 21], board: [15, 18], plant: [15, 17], plant_big: [15, 18] };
  F.combustible = type => !!COMB[type];
  F.furn = new Map();
  const furnBox = new THREE.Box3();
  const sootMat = new THREE.MeshBasicMaterial({ color: 0x1b1512, transparent: true, opacity: 0, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, fog: false });
  function furnOverlay(inst) {
    const mat = sootMat.clone(), ov = new THREE.Mesh(inst.mesh.geometry, mat); ov.raycast = () => { }; ov.renderOrder = 3; ov.frustumCulled = false; inst.mesh.add(ov); return ov;
  }
  F.igniteFurn = (inst, why = 'char') => {
    if (!F.on || !inst || !COMB[inst.f.type]) return false; const id = inst.f.id, cur = F.furn.get(id);
    if (cur && cur.state === 'burning') return false;
    let n = 0; for (const o of F.furn.values()) if (o.state === 'burning') n++; if (n >= F.cfg.maxFurn) return false;   // 家具同時著火上限
    const [a, b] = COMB[inst.f.type]; furnBox.setFromObject(inst.obj); const top = Math.max(0.7, furnBox.max.y - (furnBox.min.y > 0 ? 0 : 0));
    const o = cur || { inst, ov: null, scorch: 0 }; Object.assign(o, { state: 'burning', t: 0, dur: rnd(a, b), top, emitA: 0, emitS: 0, emitG: 0, tok: (o.tok || 0) + 1, helper: null, why });
    if (!o.ov || !o.ov.parent) o.ov = furnOverlay(inst); F.furn.set(id, o); F.stats.furnIgnited = (F.stats.furnIgnited || 0) + 1;
    W.emit && W.emit('furn_burned', id, { type: inst.f.type, x: inst.f.x, z: inst.f.z });
    F.helperFor({ kind: 'furn', id }); return true;
  };
  F.extinguishFurn = (id, cause = 'bucket') => {
    const o = F.furn.get(id); if (!o || o.state !== 'burning') return false;
    o.scorch = Math.max(o.scorch, Math.min(0.85, 0.35 + 0.5 * o.t / o.dur)); o.state = 'scorched'; o.t = 0; o.recoverAt = rnd(F.cfg.furnRecMin, F.cfg.furnRecMax);
    const f = o.inst.f; for (let i = 0; i < 14; i++) spawn(PS, f.x + rnd(-0.5, 0.5), rnd(0.3, o.top), f.z + rnd(-0.5, 0.5), rnd(-0.2, 0.2), rnd(0.7, 1.3), rnd(-0.2, 0.2), rnd(1.0, 1.7), 0.14, 0.6, 4, { drag: 1.5 });
    F.stats.furnExtinguished = (F.stats.furnExtinguished || 0) + 1; W.emit && W.emit('furn_extinguished', id, { cause, type: f.type }); return true;
  };
  const furnShapes = inst => footToWorld(inst.f, inst.spec.foot || []);
  const inShape = (sh, x, z, m) => sh.r != null ? Math.hypot(x - sh.x, z - sh.z) < sh.r + m : Math.abs(x - sh.x) < sh.w / 2 + m && Math.abs(z - sh.z) < sh.d / 2 + m;
  function tickFurn(h) {
    for (const [id, o] of F.furn) {
      const f = o.inst.f;
      if (o.state === 'burning') {
        o.t += h; const sh = furnShapes(o.inst)[0] || { x: f.x, z: f.z, w: 0.8, d: 0.8 }, w = sh.r != null ? sh.r * 2 : sh.w, d = sh.r != null ? sh.r * 2 : sh.d, big = Math.max(w, d);
        const pt = () => [sh.x + rnd(-0.45, 0.45) * w, sh.z + rnd(-0.45, 0.45) * d];
        o.emitA += h * (14 + 6 * Math.min(2, big)); while (o.emitA >= 1) { o.emitA--; const [x, z] = pt(); spawn(PA, x, rnd(0.35, o.top * 0.9), z, rnd(-0.15, 0.15), rnd(0.7, 1.4), rnd(-0.15, 0.15), rnd(0.35, 0.65), rnd(0.18, 0.3), 0.04, 1, { drag: 3 }); }
        o.emitS += h * 6; while (o.emitS >= 1) { o.emitS--; const [x, z] = pt(); spawn(PS, x, o.top * rnd(0.8, 1.05), z, rnd(-0.1, 0.1), rnd(0.5, 0.9), rnd(-0.1, 0.1), rnd(1.6, 2.6), 0.16, 0.7, 3, { drag: 1.2 }); }
        o.emitG += h * 3; while (o.emitG >= 1) { o.emitG--; const [x, z] = pt(); spawn(PA, x, o.top * 0.6, z, 0, 0.05, 0, rnd(0.7, 1.1), Math.max(0.9, big * 0.9), Math.max(1.1, big * 1.1), 5, { drag: 2 }); }
        o.scorch = Math.max(o.scorch, Math.min(0.85, 0.2 + 0.65 * o.t / o.dur)); o.ov.material.opacity = o.scorch * 0.8;
        if (o.t >= o.dur) { o.state = 'scorched'; o.t = 0; o.recoverAt = rnd(F.cfg.furnRecMin, F.cfg.furnRecMax); F.stats.furnExtinguished = (F.stats.furnExtinguished || 0) + 1; W.emit && W.emit('furn_extinguished', id, { cause: 'burnt-out', type: f.type }); }
      } else if (o.state === 'scorched') {
        o.t += h; o.ov.material.opacity = o.scorch * 0.8;
        o.emitS += h * 1.2; while (o.emitS >= 1) { o.emitS--; spawn(PS, f.x + rnd(-0.3, 0.3), o.top * rnd(0.8, 1), f.z + rnd(-0.3, 0.3), 0, rnd(0.4, 0.6), 0, rnd(1.6, 2.4), 0.1, 0.45, 3, { drag: 1 }); }
        if (o.t >= o.recoverAt) { o.state = 'recovering'; o.t = 0; o.s0 = o.scorch; }
      } else if (o.state === 'recovering') {
        o.t += h; const u = clamp(o.t / F.cfg.fade, 0, 1); o.scorch = o.s0 * (1 - u * u * (3 - 2 * u)); o.ov.material.opacity = o.scorch * 0.8;
        if (u >= 1) { o.state = 'none'; o.scorch = 0; o.ov.removeFromParent(); o.ov.material.dispose(); o.ov = null; F.furn.delete(id); F.stats.furnRecovered = (F.stats.furnRecovered || 0) + 1; W.emit && W.emit('furn_recovered', id, { type: f.type }); }
      }
    }
  }
  // 燒著的人 → 別人（傳火）與 → 可燃家具（點燃）
  function spreadTick() {
    let any = false; for (const o of F.states.values()) if (o.state === 'burning') { any = true; break; } if (!any) return;
    const cs = allChars(), combs = [...W.furn.values()].filter(i => COMB[i.f.type] && i.obj && i.obj.visible);
    for (const o of [...F.states.values()]) {
      if (o.state !== 'burning') continue; const c = o.c, p = posOf(c); if (c._held || c.state === 'held') continue;
      for (const q of cs) {
        if (q === c || imm(q) || !q.object3D.visible || q.away || q.state === 'sit' || q.state === 'held' || q._held) continue; const s = st(q); if (s && s.state !== 'none') continue;
        const pq = posOf(q); if (Math.abs((c.lift || 0) - (q.lift || 0)) > 1) continue; if (Math.hypot(pq.x - p.x, pq.z - p.z) < F.cfg.contact) { ignite(q, 'contact', c.spec.id); F.stats.contact = (F.stats.contact || 0) + 1; }
      }
      if ((c.lift || 0) < 1.2) for (const inst of combs) { const cur = F.furn.get(inst.f.id); if (cur && cur.state !== 'none') continue; if (furnShapes(inst).some(sh => inShape(sh, p.x, p.z, 0.3))) F.igniteFurn(inst, 'char'); }
    }
  }
  // 同事拿水桶（桶子是個小小的藍色水桶，拿在胸前）去滅火；不羞辱：喊話、關心。每個火點最多一位，每位 12 秒內沒到就算了。
  F.helpers = { runs: 0, active: new Set() };
  const bucketMesh = () => { const g = new THREE.Group(), m1 = new THREE.MeshStandardMaterial({ color: 0x5aa9e6, roughness: 0.6 }), m2 = new THREE.MeshStandardMaterial({ color: 0xbfe6ff, roughness: 0.3 }); const b = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.08, 0.17, 12), m1); const w = new THREE.Mesh(new THREE.CylinderGeometry(0.095, 0.095, 0.01, 12), m2); w.position.y = 0.075; const h = new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.008, 6, 12, Math.PI), new THREE.MeshStandardMaterial({ color: 0x555a66 })); h.position.y = 0.085; g.add(b, w, h); g.name = 'bucket'; return g; };
  const helperOk = (c, avoid) => c && !c.spec.pet && c !== avoid && c.object3D.visible && !c.away && !c.jobless && !c.sleeping && !c.piloted && !c.hrBusy && !c._held && c.state !== 'held' && !c.busy && !imm(c) && (!st(c) || st(c).state === 'none') && !F.helpers.active.has(c.spec.id);
  F.helperFor = tgt => {
    if (!F.on || F.noHelpers) return null; const where = tgt.kind === 'char' ? posOf(tgt.c) : F.furn.get(tgt.id).inst.f, avoid = tgt.kind === 'char' ? tgt.c : null;
    let best = null, bd = 16; for (const q of W.chars.values()) { if (!helperOk(q, avoid)) continue; const pq = posOf(q), d = Math.hypot(pq.x - where.x, pq.z - where.z); if (d < bd) { bd = d; best = q; } }
    if (best) bucketRun(best, tgt); return best;
  };
  async function bucketRun(c, tgt) {
    const D0 = D(); if (!D0) return; const id = c.spec.id; F.helpers.active.add(id); F.helpers.runs++; const tok = c.script = (c.script || 0) + 1; c.busy = true; c.stop && c.stop(false);
    const bk = bucketMesh(), sc = c.object3D.scale.x || 1; bk.scale.setScalar(1 / sc); bk.position.set(0, (c.height || 0.8) * 0.5 / sc, 0.32 / sc); c.object3D.add(bk); c._bucket = bk;
    const alive = () => c.script === tok && !c._held && c.state !== 'held';
    const tpos = () => tgt.kind === 'char' ? posOf(tgt.c) : F.furn.get(tgt.id).inst.f, still = () => tgt.kind === 'char' ? (st(tgt.c) && st(tgt.c).state === 'burning') : (F.furn.get(tgt.id) && F.furn.get(tgt.id).state === 'burning');
    try {
      await W.sleep(rnd(0.8, 1.6)); if (!alive()) return; c.emote('exclaim', 1.2); c.say(tgt.kind === 'char' ? '我拿水來了！撐住！' : '著火了！我去滅火！', 2); c.setAction('idle');
      const t0 = W.time;
      for (let k = 0; k < 8 && alive() && still() && W.time - t0 < 14; k++) {
        const t = tpos(), a = posOf(c), d = Math.hypot(t.x - a.x, t.z - a.z); if (d < 1.7) break;
        const g = 1.35, L = d || 1, f = W.nav.nearestFree(t.x + (a.x - t.x) / L * g, t.z + (a.z - t.z) / L * g, 3); if (!f) break;
        await D0.goTo(c, { x: f.x, z: f.z, face: 0 }, { speed: 3.8 });
      }
      if (!alive() || !still()) return;
      const t = tpos(); c.faceTo(t.x, t.z); c.setAction('pour'); c.say(tgt.kind === 'char' ? '嘩——！' : '嘩啦——！', 1.4); await W.sleep(0.7); if (!alive()) return;
      const a = posOf(c); for (let i = 0; i < 10; i++) spawn(PS, (a.x + t.x) / 2 + rnd(-0.2, 0.2), 0.7 + rnd(0, 0.3), (a.z + t.z) / 2 + rnd(-0.2, 0.2), (t.x - a.x) * 0.6, rnd(-0.3, 0.2), (t.z - a.z) * 0.6, rnd(0.4, 0.7), 0.07, 0.05, 4, { drag: 1.0, g: -4 });
      if (tgt.kind === 'char') { if (st(tgt.c) && st(tgt.c).state === 'burning') F.extinguish(tgt.c, 'bucket', id); } else F.extinguishFurn(tgt.id, 'bucket');
      F.stats.bucketed = (F.stats.bucketed || 0) + 1; W.emit && W.emit('bucketed', id, { kind: tgt.kind, target: tgt.kind === 'char' ? tgt.c.spec.id : tgt.id });
      await W.sleep(0.9); if (c.script !== tok) return; c.say(tgt.kind === 'char' ? '沒事了，火滅了' : '火滅了，沒事了', 1.8); c.emote('check', 1.2); c.setAction('idle');
      await W.sleep(1.2);
    } catch (e) { console.error('滅火流程例外', e); }
    finally { F.helpers.active.delete(id); if (bk.parent) bk.removeFromParent(); c._bucket = null; if (c.script === tok) { c.busy = false; try { const Dr = D(); if (Dr && Dr.goHome) await Dr.goHome(c, { speed: 2.4 }); } catch (e) { /* 走不回去就算了 */ } } }
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
      // 「上一步位置」每一步都先更新（不管後面會不會 continue）：燒焦、坐著、隱藏、被瞬移期間不更新的話，恢復那一刻線段會從舊位置拉到現在，穿過火心而誤燒
      const p = posOf(c), pv = c._fp || (c._fp = { x: p.x, z: p.z }); let ox = pv.x, oz = pv.z; pv.x = p.x; pv.z = p.z;
      if (Math.hypot(p.x - ox, p.z - oz) > 2.5) { ox = p.x; oz = p.z; }   // 一步跳超過 2.5 公尺＝瞬移（重新聘用、整修歸位、被放到別處），不當成飛過去
      if (imm(c) || !c.object3D.visible || c.away) continue; const s = st(c);
      if (s && s.state !== 'none') continue;   // 剛燒完（愣著冒煙）的不再重燒
      if (c._seat && c.state === 'sit') continue;
      const lift = c.lift || 0;
      // 這一步走過的線段離火心多近（被甩得很快的角色一步會飛 0.3 公尺以上，只看終點會漏接）
      const sx = p.x - ox, sz = p.z - oz, sl = sx * sx + sz * sz, u = sl > 1e-9 ? clamp(((fx - ox) * sx + (fz - oz) * sz) / sl, 0, 1) : 1, d = Math.hypot(ox + sx * u - fx, oz + sz * u - fz);
      // 腳離地低於火焰高度（約 1.3 公尺）就碰得到；被拎著的角色（高度約 1）在火焰正上方 0.9 公尺內也算
      const held = c.state === 'held' || (c.newModel ? c.inner.ctl.state === 'held' : c.inner.mode === 'held');
      const rng = (c.piloted || lift > 0.05 || held) ? F.cfg.range : F.cfg.range - 0.3;   // 操控中、飛行中的角色用完整範圍；自己走路經過的只在幾乎貼到石圈時才算（避免路過的同事常常著火）
      if ((d < rng && lift < 1.3) || (held && d < 0.9 && lift < 2)) ignite(c, 'campfire');
    }
    for (const o of F.states.values()) { if (o.state !== 'none') tickChar(o, h); }
    spreadTick(); tickFurn(h);
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
  F.reset = () => { for (const [id, o] of F.furn) { if (o.ov) { o.ov.removeFromParent(); o.ov.material.dispose(); } } F.furn.clear(); F.helpers.active.clear(); for (const o of F.states.values()) { o.state = 'none'; o.wash = false; o.quick = false; o.tok++; if (o.c && o.c._sootU) o.c._sootU.value = 0; o.c && o.c.drive && o.c.drive(null); if (o.c) o.c.busy = false; } for (const pl of [PA, PS]) pl.p.length = 0; };
  return F;
}
