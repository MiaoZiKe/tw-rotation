// 天竺鼠寵物：白色毛球（多層殼毛）＋立體亮眼睛
import { THREE, softMat, dirSurface, ellipsoid, latheGeo, canvasTex, Spring, sstep, C } from './core.js';
import { makeSymbol } from './fx.js';
import { irisTex } from './face.js';
const mesh = (g, m, cast = true) => { const o = new THREE.Mesh(g, m); o.castShadow = cast; o.receiveShadow = true; return o; };
const grp = (parent, x = 0, y = 0, z = 0) => { const g = new THREE.Group(); g.position.set(x, y, z); parent && parent.add(g); return g; };
// ───────── 天竺鼠寵物：白色毛球（多層殼毛） ─────────
function furTex() {
  return canvasTex(256, 256, (c) => {
    c.fillStyle = '#000'; c.fillRect(0, 0, 256, 256);
    let s = 7; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < 9000; i++) { const x = rnd() * 256, y = rnd() * 256, v = Math.floor(110 + rnd() * 145), r = 1.3 + rnd() * 1.2; c.fillStyle = `rgb(${v},${v},${v})`; for (const ox of [-256, 0, 256]) for (const oy of [-256, 0, 256]) { c.beginPath(); c.arc(x + ox, y + oy, r, 0, 7); c.fill(); } }
  });
}
export function buildPet(sp) {
  const ch = { id: 'pet', spec: sp, springs: [], n: {}, props: {}, sym: {}, pet: true, HIP: 0 };
  const root = ch.root = new THREE.Group(); const rig = ch.rig = grp(root); const n = ch.n;
  const hips = n.hips = grp(rig, 0, 0.165, 0); const spine = n.spine = grp(hips);
  const shape = (d, p) => { const f = sstep(-0.2, 1, d.z); p.set(d.x * 0.185 * (1 - 0.1 * f), d.y * 0.158 * (1 + 0.04 * f) + 0.012 * f, d.z * 0.27); };
  const g = dirSurface(shape, { w: 72, h: 48, color: (d, p, c) => c.set('#ffffff').lerp(C('#efe6e2'), sstep(0.1, -0.9, d.y) * 0.8) });
  const furK = new Float32Array(g.attributes.position.count); const tmp = new THREE.Vector3();
  for (let i = 0; i < furK.length; i++) { tmp.fromBufferAttribute(g.attributes.position, i); const d = tmp.clone().set(tmp.x / 0.185, tmp.y / 0.158, tmp.z / 0.255).normalize(); const eyeD = Math.min(Math.hypot(d.x - 0.4, d.y - 0.19), Math.hypot(d.x + 0.4, d.y - 0.19)); furK[i] = (d.z > 0 ? 0.25 + 0.75 * sstep(0.12, 0.4, eyeD) : 1) * (1 - 0.72 * sstep(0.55, 0.95, d.z)) * (1 - 0.5 * sstep(-0.5, -1, d.y)) * (1 + 0.5 * sstep(0.5, 1, d.y) * sstep(0.2, 0.7, d.z)); }
  g.setAttribute('furK', new THREE.BufferAttribute(furK, 1));
  spine.add(mesh(g, softMat(0xffffff, { vc: true })));
  const ft = furTex(); ft.wrapS = ft.wrapT = THREE.RepeatWrapping;
  const N = 22;
  for (let i = 1; i <= N; i++) {
    const m = softMat(0xffffff, { vc: true, rimStr: 0.25 }); const sh = i / N; const base = m.onBeforeCompile;
    m.onBeforeCompile = (s) => {
      base(s); s.uniforms.uFur = { value: ft }; s.uniforms.uSh = { value: sh };
      s.vertexShader = s.vertexShader.replace('#include <common>', '#include <common>\nattribute float furK; uniform float uSh; varying vec3 vOP; varying vec3 vON;')
        .replace('#include <begin_vertex>', 'vec3 transformed = position + normal * uSh * 0.05 * furK; transformed.y -= uSh * uSh * 0.012; vOP = position; vON = normal;');
      s.fragmentShader = s.fragmentShader.replace('#include <common>', '#include <common>\nuniform sampler2D uFur; uniform float uSh; varying vec3 vOP; varying vec3 vON;')
        .replace('#include <color_fragment>', `#include <color_fragment>
          vec3 w = pow(abs(normalize(vON)), vec3(6.0)); w /= (w.x + w.y + w.z);
          float fn = texture2D(uFur, vOP.yz * 5.5).r * w.x + texture2D(uFur, vOP.xz * 5.5).r * w.y + texture2D(uFur, vOP.xy * 5.5).r * w.z;
          if (fn < 0.3 + uSh * 0.7) discard;
          diffuseColor.rgb *= 0.86 + 0.14 * uSh;`);
    };
    m.customProgramCacheKey = () => 'fur';
    const sm = new THREE.Mesh(g, m); sm.castShadow = false; spine.add(sm);
  }
  const at = (x, y, z, out = 0) => { const d = new THREE.Vector3(x, y, z).normalize(), p = new THREE.Vector3(); shape(d, p); return p.addScaledVector(d, out); };
  // 眼睛（黑亮珠子＋高光）、鼻、嘴、腮紅
  for (const s of [-1, 1]) {
    const p = at(s * 0.42, 0.2, 0.9, 0.02); const e = mesh(ellipsoid(0.027, 0.03, 0.022, { w: 24, h: 18 }), softMat('#2d2530', { rough: 0.25, rimStr: 0.1 }), false); e.position.copy(p); spine.add(e); (n.eyes ||= []).push(e);
    const h = new THREE.Mesh(ellipsoid(0.009, 0.009, 0.005, { w: 12, h: 8 }), new THREE.MeshBasicMaterial({ color: 0xffffff })); h.position.set(-0.008, 0.011, 0.02); e.add(h);
    const h2 = new THREE.Mesh(ellipsoid(0.004, 0.004, 0.003, { w: 10, h: 6 }), new THREE.MeshBasicMaterial({ color: 0xffffff })); h2.position.set(0.008, -0.009, 0.021); e.add(h2);
    const b = new THREE.Mesh(new THREE.CircleGeometry(0.04, 24), new THREE.MeshBasicMaterial({ map: blushTex(), transparent: true, depthWrite: false, opacity: 0.8 })); b.position.copy(at(s * 0.6, -0.12, 0.8, 0.009)); b.lookAt(b.position.clone().multiplyScalar(3)); b.renderOrder = 3; spine.add(b);
    const ear = n['ear' + (s > 0 ? 'L' : 'R')] = grp(spine); ear.position.copy(at(s * 0.7, 0.58, 0.5, 0.012)); ear.rotation.set(0.35, s * 0.5, -s * 1.3);
    ear.add(mesh(dirSurface((d, p) => p.set(d.x * 0.036, d.y * 0.03 + 0.024, d.z * 0.018 + 0.01 * d.x * d.x * 4), { w: 24, h: 18 }), softMat('#ffc2c9')));
    ch.springs.push(new Spring(ear, 0.07, { k: 150, c: 8, acc: 2.4 }));
  }
  const nose = n.nose = mesh(ellipsoid(0.02, 0.014, 0.012, { w: 18, h: 12 }), softMat('#ff9fb0'), false); nose.position.copy(at(0, 0.02, 1, 0.012)); spine.add(nose);
  const mo = n.mouth = mesh(ellipsoid(0.012, 0.01, 0.006, { w: 14, h: 10 }), softMat('#8a3a48'), false); mo.position.copy(at(0, -0.14, 1, 0.014)); spine.add(mo);
  // 頭頂一撮翹毛
  const tuft = grp(spine); tuft.position.copy(at(0, 0.8, 0.55, 0.02)); tuft.rotation.set(0.4, 0, 0.2);
  tuft.add(mesh(dirSurface((d, p) => { const t = d.y * 0.5 + 0.5; p.set(d.x * 0.034 * (1 - 0.5 * t) + 0.02 * t * t, d.y * 0.03 + 0.012, d.z * 0.03 * (1 - 0.5 * t)); }, { w: 18, h: 16 }), softMat('#ffffff')));
  ch.springs.push(new Spring(tuft, 0.07, { k: 120, c: 6, acc: 3 }));
  // 四隻小腳
  n.feet = [];
  for (const [x, z] of [[0.09, 0.14], [-0.09, 0.14], [0.1, -0.12], [-0.1, -0.12]]) { const f = grp(rig, x, 0.022, z); f.add(mesh(ellipsoid(0.03, 0.02, 0.04, { w: 20, h: 12 }), softMat('#ffc2c9'))); f.userData.z = z; n.feet.push(f); }
  // 紅蘿蔔（坐下時啃）
  const car = ch.props.carrot = grp(spine, 0.01, -0.075, 0.3); car.visible = false; car.rotation.set(1.25, 0, 2.6);
  car.add(mesh(latheGeo([[0, -0.09], [0.012, -0.08], [0.03, 0.0], [0.034, 0.05], [0.02, 0.066], [0, 0.068]], { rows: 28, seg: 24 }), softMat('#ffa24d')));
  for (const r of [-0.4, 0, 0.4]) { const lf = mesh(ellipsoid(0.012, 0.035, 0.008, { w: 12, h: 10 }), softMat('#8fd69a')); lf.position.set(Math.sin(r) * 0.02, 0.09, 0); lf.rotation.z = -r; car.add(lf); }
  const symA = ch.symAnchor = grp(spine, 0, 0.3, 0.1);
  for (const k of ['anger', 'q', 'ex', 'spark', 'bulb', 'drop', 'heart', 'note']) { const s = ch.sym[k] = makeSymbol(k, 0.14); symA.add(s); }
  ch.puffs = []; ch.dizzy = [0, 1, 2].map(() => { const s = makeSymbol('star', 0.08); symA.add(s); return s; }); ch.bubble = null; ch.bdots = [];
  root.traverse((o) => { o.frustumCulled = false; });
  return ch;
}
let _bl; const blushTex = () => _bl || (_bl = canvasTex(64, 64, (c) => { const g = c.createRadialGradient(32, 32, 0, 32, 32, 32); g.addColorStop(0, 'rgba(255,150,170,1)'); g.addColorStop(0.5, 'rgba(255,150,170,0.8)'); g.addColorStop(1, 'rgba(255,150,170,0)'); c.fillStyle = g; c.fillRect(0, 0, 64, 64); }));
