// 泳池水面與落水物理（2026-11-15）。
//   · 水面：一個半透明網格（自訂著色器：池邊淺、中間深、淡淡的水紋、最多 6 個同時擴散的漣漪、夜晚池底自發光）。漣漪全在著色器裡算，不另外加繪製。
//   · 水花與滴水：一個粒子池（Points，240 顆），重力、落到水面或地面就消失；被丟進水裡濺大水花，走出水的人身上持續滴水一陣子。
//   · 角色：進入泳池範圍且高度低於水面（被丟進來、自己走進來都算）→ 濺水（W.emit 'splashed'）、浮起來（微微上下起伏）、
//     燒著的人立刻熄火（呼叫 fire.js 的 F.extinguish，事件 'extinguished' 附 cause:'pool'）、走出水之後身體濕一陣子（滴水）、
//     並且 15 秒內碰到火不會著火、只會冒白煙＋「滋」（c._fireImmuneUntil；fire.js 的 ignite 會檢查）；濕的期間頭上有水滴圖示、名牌顯示「濕答答」。
//   · 情緒由 mind.js 處理，這裡只送事件。時間全部用模擬時間（W.time）。
import { THREE } from './kit.js';
import { LAY } from './sports_build.js';

const clamp = (x, a, b) => Math.max(a, Math.min(b, x)), rnd = (a, b) => a + Math.random() * (b - a);
const reduce = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
export const WET_SEC = 15, IMMUNE_SEC = 15;      // 走出水後身體濕多久、多久內不會著火（模擬秒；11-16 擁有者：15 秒，兩個一致）

export function createWater(W) {
  const A = { stats: { splashes: 0, entered: 0, extinguished: 0, drips: 0 }, rip: [], inside: new Map() };
  const L = LAY.pool, top = L.top, cxm = (L.x0 + L.x1) / 2, czm = (L.z0 + L.z1) / 2;
  // ── 水面
  const uRip = Array.from({ length: 6 }, () => new THREE.Vector4(0, 0, -1, 0));
  const mat = new THREE.ShaderMaterial({
    uniforms: { uT: { value: 0 }, uNight: { value: 0 }, uRip: { value: uRip }, uBox: { value: new THREE.Vector4(L.x0, L.z0, L.x1, L.z1) } },
    transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false,
    vertexShader: 'varying vec2 vXZ; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vXZ = w.xz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: `uniform float uT, uNight; uniform vec4 uRip[6]; uniform vec4 uBox; varying vec2 vXZ;
      void main(){
        vec2 q = vXZ; float edge = min(min(q.x - uBox.x, uBox.z - q.x), min(q.y - uBox.y, uBox.w - q.y));
        vec3 col = mix(vec3(0.56, 0.87, 0.95), vec3(0.30, 0.66, 0.87), smoothstep(0.0, 0.9, edge));
        float w = sin(q.x * 2.6 + uT * 0.5) * sin(q.y * 2.2 - uT * 0.4) * 0.5 + 0.5; col += (w - 0.5) * 0.07;
        float rr = 0.0;
        for (int i = 0; i < 6; i++) { float age = uRip[i].z; if (age < 0.0) continue; float d = length(q - uRip[i].xy); float ring = exp(-pow((d - age * 1.4) / 0.13, 2.0)); rr += ring * uRip[i].w * exp(-age * 1.0); }
        col += vec3(0.55, 0.65, 0.65) * rr * 0.5;
        col = col * (1.0 - 0.42 * uNight) + vec3(0.05, 0.22, 0.28) * uNight;
        gl_FragColor = vec4(col, 0.64 + 0.12 * rr);
      }`
  });
  const geo = new THREE.PlaneGeometry(L.x1 - L.x0, L.z1 - L.z0); geo.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geo, mat); mesh.position.set(cxm, top, czm); mesh.renderOrder = 4; mesh.frustumCulled = false; W.scene.add(mesh); A.mesh = mesh;
  A.ripple = (x, z, amp = 1) => { let k = A.rip.findIndex(r => r.age > 3.2); if (k < 0) k = A.rip.length < 6 ? A.rip.length : A.rip.reduce((b, r, i, a) => (r.age > a[b].age ? i : b), 0); A.rip[k] = { x, z, age: 0, amp }; };
  // ── 水花粒子
  const N = 240, pos = new Float32Array(N * 3), size = new Float32Array(N), col = new Float32Array(N * 4), ps = new Array(N).fill(null); let head = 0;
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage)); g.setAttribute('aSize', new THREE.BufferAttribute(size, 1).setUsage(THREE.DynamicDrawUsage)); g.setAttribute('aCol', new THREE.BufferAttribute(col, 4).setUsage(THREE.DynamicDrawUsage));
  const uScale = { value: 800 };
  const pm = new THREE.ShaderMaterial({
    uniforms: { uScale }, transparent: true, depthWrite: false, fog: false,
    vertexShader: 'attribute float aSize; attribute vec4 aCol; uniform float uScale; varying vec4 vC; void main(){ vC = aCol; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_PointSize = clamp(aSize * uScale / max(0.1, -mv.z), 0.0, 40.0); gl_Position = projectionMatrix * mv; }',
    fragmentShader: 'varying vec4 vC; void main(){ float d = length(gl_PointCoord - 0.5) * 2.0; float a = 1.0 - smoothstep(0.45, 1.0, d); gl_FragColor = vec4(vC.rgb, vC.a * a); }'
  });
  const pts = new THREE.Points(g, pm); pts.frustumCulled = false; pts.renderOrder = 7; W.scene.add(pts); A.points = pts;
  function drop(x, y, z, vx, vy, vz, life, s) { const i = head; head = (head + 1) % N; ps[i] = { x, y, z, vx, vy, vz, age: 0, life, s }; }
  A.splash = (x, z, speed = 3, y = top) => {
    A.stats.splashes++; const n = Math.round(clamp(10 + speed * 5, 10, 46));
    for (let i = 0; i < n; i++) { const a = Math.random() * 6.283, r = Math.random() * 0.3, v = rnd(0.4, 1.3) * (0.6 + speed * 0.12); drop(x + Math.cos(a) * r * 0.5, y + 0.05, z + Math.sin(a) * r * 0.5, Math.cos(a) * v * 0.7, rnd(1.5, 2.6) + speed * 0.25, Math.sin(a) * v * 0.7, rnd(0.6, 1.1), rnd(0.06, 0.1)); }
    A.ripple(x, z, clamp(0.5 + speed * 0.15, 0.5, 1.6)); if (speed > 3.5) { setTimeout(() => A.ripple(x, z, 0.8), 160); }
  };
  A.drip = (x, y, z) => { A.stats.drips++; drop(x, y, z, rnd(-0.1, 0.1), rnd(-0.2, 0.2), rnd(-0.1, 0.1), rnd(0.5, 0.8), 0.045); };
  function stepParts(h) {
    for (let i = 0; i < N; i++) {
      const p = ps[i]; if (!p) { size[i] = 0; col[i * 4 + 3] = 0; continue; }
      p.age += h; p.vy -= 9.8 * h; p.x += p.vx * h; p.y += p.vy * h; p.z += p.vz * h;
      const inPool = p.x > L.x0 && p.x < L.x1 && p.z > L.z0 && p.z < L.z1, floor = inPool ? top : 0.05;
      if (p.age >= p.life || (p.vy < 0 && p.y < floor)) { if (inPool && p.age < p.life && Math.random() < 0.18) A.ripple(p.x, p.z, 0.25); ps[i] = null; size[i] = 0; col[i * 4 + 3] = 0; continue; }
      const u = p.age / p.life; pos[i * 3] = p.x; pos[i * 3 + 1] = p.y; pos[i * 3 + 2] = p.z; size[i] = p.s;
      col[i * 4] = 0.72; col[i * 4 + 1] = 0.9; col[i * 4 + 2] = 1.0; col[i * 4 + 3] = (1 - u * u) * 0.9;
    }
  }
  // ── 角色與水
  const allChars = () => [...W.chars.values(), ...(W.pets || []), ...(W.extras || [])];
  const velOf = c => { const v = c.inner && c.inner.vel; const k = c.newModel ? 1 : (c.scale || 1); return v ? { x: v.x * k, y: v.y * k, z: v.z * k } : { x: 0, y: 0, z: 0 }; };
  const inRect = (x, z, m = 0.08) => x > L.x0 + m && x < L.x1 - m && z > L.z0 + m && z < L.z1 - m;
  // 真的被拎在手上（c._held 在被丟出去、飛行中也是 true，那不算拎著）
  const isHeld = c => (c.newModel ? (c.inner.ctl && c.inner.ctl.state === 'held') : (c.inner && c.inner.mode === 'held'));
  A.inWater = c => A.inside.has(c);
  A.isWet = c => (c._wetUntil || 0) > W.time || A.inside.has(c);
  let dripT = 0, stepN = 0;
  A.tick = h => {
    stepN++; for (const r of A.rip) r.age += h;
    stepParts(h);
    dripT += h;
    for (const c of allChars()) {
      if (!c.object3D.visible || c.away) { if (A.inside.has(c)) A.inside.delete(c); continue; }
      const p = c.object3D.position, held = isHeld(c), lift = c.lift || 0;
      if (lift > 0.08 || held) { const vy = velOf(c).y; c._airT = W.time; c._fallV = Math.max(c._fallV || 0, -vy); } else if (W.time - (c._airT || -9) > 0.8) c._fallV = 0;   // 飛行中記下最大下墜速度（濺水大小）
      let st = A.inside.get(c);
      if (!st) {
        if (held || !inRect(p.x, p.z) || lift > top + 0.14) { /* 不在水裡 */ }
        else {
          const v = velOf(c), fall = Math.max(c._fallV || 0, -v.y), speed = Math.hypot(fall, Math.hypot(v.x, v.z) * 0.6), thrown = W.time - (c._airT || -9) < 0.6 && fall > 0.8;
          st = { t: 0, ph: Math.random() * 6.28, rippleT: 0, thrown }; A.inside.set(c, st); A.stats.entered++;
          const quiet = (c._noSplashUntil || 0) > W.time;   // 自己跳水（sports.js）已經濺過了
          if (!quiet) A.splash(p.x, p.z, thrown ? Math.max(2.5, speed) : 1.2);
          const F = W.fire, burning = !!(F && F.states.get(c.spec.id) && F.states.get(c.spec.id).state === 'burning');
          if (!quiet) W.emit && W.emit('splashed', c.spec.id, { x: p.x, z: p.z, speed: +speed.toFixed(2), thrown, burning, from: thrown ? 'thrown' : 'walk' });
          if (burning && F.extinguish && F.extinguish(c, 'pool')) A.stats.extinguished++;
        }
      }
      if (st) {
        if (held || !inRect(p.x, p.z, -0.02)) {        // 被拎起來、或走出泳池：身體濕一陣子（滴水），一段時間內不著火
          A.inside.delete(c); c._wetUntil = W.time + WET_SEC; c._fireImmuneUntil = W.time + IMMUNE_SEC; c._floatY = 0; if (!held) c.object3D.position.y = 0;
          W.emit && W.emit('left_pool', c.spec.id, { x: p.x, z: p.z });
        } else {
          st.t += h; c._floatY = (0.13 + (reduce ? 0 : 0.03 * Math.sin(W.time * 2.4 + st.ph))) * Math.min(1, st.t / 0.5);   // 浮起來的高度（模擬時間算；畫面更新時才加到位置上）
          c._wetUntil = W.time + WET_SEC; c._fireImmuneUntil = W.time + IMMUNE_SEC;
          const F = W.fire, fs = F && F.states.get(c.spec.id); if (fs && fs.state === 'burning' && F.extinguish && F.extinguish(c, 'pool')) A.stats.extinguished++;   // 水裡不會燒（含剛好在水裡被點燃）
          if (F && F.wash && fs && fs.state !== 'none' && !fs.wash) F.wash(c);   // 身上還有焦黑（愣著冒煙、褪色途中）：泡在水裡洗掉
          const sp = Math.hypot(velOf(c).x, velOf(c).z); st.rippleT -= h; if (st.rippleT <= 0 && sp > 0.35) { st.rippleT = 0.45; A.ripple(p.x, p.z, 0.4); }
        }
      } else if ((c._wetUntil || 0) > W.time && dripT >= 0.2) {   // 身體濕：偶爾滴一滴水（落到腳邊）；頭上掛著水滴圖示（沒有別的圖示佔著時才掛）
        if (!c.emoteSym && !reduce) c.emote('sweat', 2.6);
        if (Math.random() < 0.7 && !held) A.drip(p.x + rnd(-0.15, 0.15), lift + (c.height || 0.8) * rnd(0.15, 0.55), p.z + rnd(-0.15, 0.15));
      }
    }
    if (dripT >= 0.2) dripT = 0;
  };
  // 每一畫面：水紋時間、夜晚亮度、粒子上傳、浮起來的上下起伏（在所有角色更新完之後、繪圖之前加上去）
  A.frame = () => {
    const now = performance.now() / 1000; mat.uniforms.uT.value = reduce ? 0 : now;
    mat.uniforms.uNight.value = W.daytime && W.daytime.outL ? W.daytime.outL.k : 0;
    for (let i = 0; i < 6; i++) { const r = A.rip[i]; if (r && r.age < 3.2) uRip[i].set(r.x, r.z, r.age, r.amp); else uRip[i].set(0, 0, -1, 0); }
    const cam = W.camera, rend = W.renderer; uScale.value = rend.domElement.height / (2 * Math.tan(cam.fov * Math.PI / 360));
    g.attributes.position.needsUpdate = true; g.attributes.aSize.needsUpdate = true; g.attributes.aCol.needsUpdate = true;
    for (const [c] of A.inside) { if (!isHeld(c) && c.state !== 'sit') c.object3D.position.y = c._floatY || 0; }
  };
  return A;
}
