// 角色：三個原創候選共用同一套骨架 —— 彈性身體（彈簧擠壓＋果凍晃動）、種在地上的腳、彈簧手與附屬物、Canvas 臉
import * as THREE from 'three';
import { Face } from './face.js';
import { G, BOUNDS } from './world.js';

const V3 = THREE.Vector3, clamp = (x, a, b) => Math.max(a, Math.min(b, x)), lerp = (a, b, t) => a + (b - a) * t;
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const angDiff = (a, b) => { let d = (a - b) % (Math.PI * 2); if (d > Math.PI) d -= Math.PI * 2; if (d < -Math.PI) d += Math.PI * 2; return d; };
const _a = new V3(), _b = new V3(), _c = new V3(), _d = new V3(), _q = new THREE.Quaternion(), _UP = new V3(0, 1, 0);

// ── 軟質材質：上下漸層、邊緣光、假的次表面散射、戳下去的凹陷、接地壓扁、臉部貼圖
export function softMat(o, sh) {
  const m = new THREE.MeshStandardMaterial({ color: o.color, roughness: o.rough ?? 0.62, metalness: 0 });
  const U = {
    uTop: { value: new THREE.Color(o.top ?? o.color) }, uY: { value: new THREE.Vector2(o.y0 ?? -0.3, o.y1 ?? 0.3) },
    uSss: { value: new THREE.Color(o.sss ?? 0xff8a70) }, uSssAmt: { value: o.sssAmt ?? 0.3 }, uRim: { value: new THREE.Color(o.rim ?? 0xfff6ea) }, uRimAmt: { value: o.rimAmt ?? 0.32 },
    uTint: sh.uTint, uTintAmt: sh.uTintAmt, uGround: sh.uGround, uDent: { value: new THREE.Vector4(0, 1, 0, 0) }, uDentR: { value: 0.17 },
  };
  if (o.face) Object.assign(U, { uFace: { value: o.face.tex }, uHeadC: { value: new V3(...o.headC) }, uFaceSpan: { value: new THREE.Vector2(...o.span) }, uFaceOff: { value: new THREE.Vector2() }, uFaceGlow: { value: o.glow ?? 0 }, uFaceGloss: { value: o.gloss ?? 0.7 } });
  m.userData.U = U; if (o.face) m.defines = { USE_FACE: '' };
  m.onBeforeCompile = (s) => {
    Object.assign(s.uniforms, U);
    s.vertexShader = s.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vObjP; uniform vec4 uDent; uniform float uDentR; uniform float uGround;')
      .replace('#include <beginnormal_vertex>', '#include <beginnormal_vertex>\n vec3 dP = position - uDent.xyz; float dW = exp(-dot(dP,dP)/(uDentR*uDentR)); objectNormal = normalize(objectNormal - uDent.w*dW*2.0*dP/(uDentR*uDentR));')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\n vObjP = position; transformed -= normal * uDent.w * dW;')
      .replace('#include <project_vertex>', 'vec4 wPos = modelMatrix * vec4(transformed,1.0); float gd = uGround - wPos.y; if (gd > 0.0) wPos.y = uGround - gd*0.06;\n vec4 mvPosition = viewMatrix * wPos; gl_Position = projectionMatrix * mvPosition;');
    s.fragmentShader = s.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vObjP; uniform vec3 uTop; uniform vec2 uY; uniform vec3 uSss; uniform float uSssAmt; uniform vec3 uRim; uniform float uRimAmt; uniform vec3 uTint; uniform float uTintAmt;\n#ifdef USE_FACE\nuniform sampler2D uFace; uniform vec3 uHeadC; uniform vec2 uFaceSpan; uniform vec2 uFaceOff; uniform float uFaceGlow; uniform float uFaceGloss;\n#endif')
      .replace('#include <color_fragment>', '#include <color_fragment>\n diffuseColor.rgb = mix(diffuseColor.rgb, uTop, smoothstep(uY.x, uY.y, vObjP.y)); diffuseColor.rgb = mix(diffuseColor.rgb, uTint, uTintAmt);')
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
        float fr = pow(1.0 - saturate(dot(normal, normalize(vViewPosition))), 2.4);
        #ifdef USE_FACE
          vec3 fd = normalize(vObjP - uHeadC);
          vec2 fuv = vec2(atan(fd.x, fd.z) - uFaceOff.x, asin(clamp(fd.y,-1.0,1.0)) - uFaceOff.y) / uFaceSpan + 0.5;
          vec4 fc = texture2D(uFace, fuv);
          float fm = step(0.0,fuv.x)*step(fuv.x,1.0)*step(0.0,fuv.y)*step(fuv.y,1.0)*step(-0.15, fd.z);
          fc *= fm;
          vec3 fcol = pow(fc.rgb / max(fc.a, 1e-3), vec3(2.2));
          diffuseColor.rgb = mix(diffuseColor.rgb, fcol * (1.0 - 0.7*step(0.5,uFaceGlow)), fc.a);
          float dark = fc.a * (1.0 - dot(fcol, vec3(0.333)));
          roughnessFactor = mix(roughnessFactor, 0.14, clamp(dark*uFaceGloss + fc.a*step(0.5,uFaceGlow)*0.8, 0.0, 1.0));
          totalEmissiveRadiance += fcol * fc.a * uFaceGlow;
          fr *= 1.0 - fc.a*0.85;
          float faceA = fc.a;
        #else
          float faceA = 0.0;
        #endif
        totalEmissiveRadiance += (diffuseColor.rgb * uSss * uSssAmt * (0.3 + 0.7*fr) + uRim * uRimAmt * fr) * (1.0 - faceA);`);
  };
  m.customProgramCacheKey = () => (o.face ? 'softface' : 'soft');
  return m;
}

// 用單位球變形成任意圓潤造型；法線用數值微分算，沒有接縫
export function blobGeo(fn, ws = 80, hs = 60) {
  const g = new THREE.SphereGeometry(1, ws, hs), p = g.attributes.position, n = g.attributes.normal;
  const d = new V3(), t1 = new V3(), t2 = new V3(), p0 = new V3(), p1 = new V3(), p2 = new V3(), e = 2e-3;
  for (let i = 0; i < p.count; i++) {
    d.fromBufferAttribute(p, i).normalize();
    t1.crossVectors(Math.abs(d.y) > 0.9 ? _a.set(1, 0, 0) : _a.set(0, 1, 0), d).normalize(); t2.crossVectors(d, t1);
    fn(p0.copy(d)); fn(p1.copy(d).addScaledVector(t1, e).normalize()); fn(p2.copy(d).addScaledVector(t2, e).normalize());
    p1.sub(p0); p2.sub(p0); t1.crossVectors(p1, p2).normalize(); if (t1.dot(d) < 0) t1.negate();
    p.setXYZ(i, p0.x, p0.y, p0.z); n.setXYZ(i, t1.x, t1.y, t1.z);
  }
  return g;
}
const ball = (() => { let g; return () => g || (g = new THREE.SphereGeometry(1, 40, 28)); })();
const foot = (() => { let g; return () => g || (g = blobGeo(v => { v.y = v.y * (v.y < 0 ? 0.55 : 1) + 0.55; v.z += 0.12 * (1 - Math.abs(v.y - 0.5)); }, 36, 24)); })();

// ══ 三個原創候選 ══
export const CHARS = [
  {
    id: 'mochi', name: '糰糰', sub: '麻糬糰子', why: '一顆會彈的糰子：頭就是身體，最大的臉、最誇張的擠壓伸展',
    R: 0.36, walk: 1.5, run: 3.5, jumpV: 5.7, stride: [0.42, 0.9], lat: 0.15, footFwd: 0.2, footSize: [0.082, 0.062, 0.1], handR: 0.062,
    stick: [0.475, 0.37, 0.445, 0.335], hand: [0.45, 0.2, 0.17], front: 0.4, cheek: [0.26, 0.3, 0.36], waddle: 0.085, bob: 0.03, wob: 1.25, mouth: [0, 0.24, 0.42], top: 0.72,
    faceUp: 0.14, face: { ex: 92, ey: 262, rx: 36, ry: 47, my: 322, mw: 17, line: 7, wmouth: true, eye: '#3a2622', eye2: '#6e4638', blush: '255,132,140' },
    build(c) {
      const col = 0xffe9d6, acc = 0xffbfa6;
      const m = softMat({ color: 0xffc9ad, top: 0xfff1e2, y0: -0.36, y1: 0.25, sss: 0xff8f6e, sssAmt: 0.27, face: c.face, headC: [0, 0.0, 0], span: [2.2, 2.2] }, c.sh);
      const body = new THREE.Mesh(blobGeo(v => { const y = v.y, b = 1 + 0.15 * sstep(0.4, -0.7, y); v.set(v.x * 0.455 * b, y * (y > 0 ? 0.385 : 0.345), v.z * 0.425 * b); }), m);
      body.position.y = 0.335; c.main = body; c.deform.add(body);
      const em = softMat({ color: acc, top: col, y0: -0.4, y1: 0.9, sss: 0xff8f6e }, c.sh);
      for (const s of [-1, 1]) {
        const piv = new THREE.Group(); piv.position.set(s * 0.25, 0.335 + 0.285, -0.02); c.deform.add(piv);
        const e = new THREE.Mesh(ball(), em); e.scale.set(0.105, 0.1, 0.07); e.position.y = 0.065; piv.add(e);
        c.apps.push({ piv, side: s, k: 150, c: 9, g: 0.016, gy: 0.012, rest: [0, s * -0.22], droop: 0.75 });
      }
      const tp = new THREE.Group(); tp.position.set(0.06, 0.2, -0.4); c.deform.add(tp);
      const tl = new THREE.Mesh(ball(), em); tl.scale.setScalar(0.075); tl.position.z = -0.04; tp.add(tl);
      c.apps.push({ piv: tp, side: 0, k: 220, c: 10, g: 0.03, gy: 0, rest: [0, 0], droop: 0, wag: true });
      c.limbMat = softMat({ color: acc, top: 0xffd2bd, y0: 0, y1: 1.2, sss: 0xff8f6e }, c.sh);
    },
  },
  {
    id: 'bean', name: '豆芽', sub: '豆子小人', why: '豆子身體＋真的會踩步的小腳：走路、跑步、急停最有戲',
    R: 0.3, walk: 1.6, run: 3.9, jumpV: 5.9, stride: [0.5, 1.15], lat: 0.105, footFwd: 0.02, footSize: [0.075, 0.058, 0.105], handR: 0.058,
    hand: [0.35, 0.33, 0.04], front: 0.31, cheek: [0.21, 0.5, 0.28], waddle: 0.05, bob: 0.035, wob: 0.8, mouth: [0, 0.44, 0.31], top: 0.9, legs: true, tintK: 0.5,
    faceUp: 0.1, face: { ex: 88, ey: 262, rx: 35, ry: 45, my: 320, mw: 16, line: 7, eye: '#2f2a26', eye2: '#5a4a3c', blush: '255,140,150' },
    build(c) {
      const m = softMat({ color: 0xbfe6c4, top: 0xe6f8e2, y0: -0.4, y1: 0.35, sss: 0x6fcf9a, sssAmt: 0.3, rim: 0xf6fff0, face: c.face, headC: [0, 0.07, 0], span: [2.1, 2.1] }, c.sh);
      const body = new THREE.Mesh(blobGeo(v => { const y = v.y, rh = Math.hypot(v.x, v.z) || 1e-6, k = Math.pow(rh, 0.7) / rh, w = 1 + 0.1 * y - 0.05 * Math.exp(-Math.pow((y + 0.1) / 0.3, 2)); v.set(v.x * k * 0.335 * w, Math.sign(y) * Math.pow(Math.abs(y), 0.92) * 0.375, v.z * k * 0.305 * w); }), m);
      body.position.y = 0.375 + 0.085; c.main = body; c.deform.add(body);
      const lm = softMat({ color: 0x6fca82, top: 0xa6e6a0, y0: -1, y1: 1, sss: 0x9be070, sssAmt: 0.4 }, c.sh);
      const piv = new THREE.Group(); piv.position.set(0, 0.46 + 0.36, 0); piv.scale.setScalar(1.3); c.deform.add(piv);
      const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.013, 0.02, 0.15, 14), lm); stem.position.y = 0.06; piv.add(stem);
      for (const [s, sc] of [[1, 1], [-1, 0.72]]) { const l = new THREE.Mesh(ball(), lm); l.scale.set(0.105 * sc, 0.022, 0.06 * sc); l.position.set(s * 0.085 * sc, 0.135 + 0.02 * sc, 0); l.rotation.z = s * 0.5; piv.add(l); }
      c.apps.push({ piv, side: 0, k: 110, c: 6.5, g: 0.03, gy: 0, rest: [0, 0], droop: 0, bend: 0.5 });
      c.limbMat = softMat({ color: 0xfff3da, top: 0xfffaf0, y0: 0, y1: 1.2, sss: 0xffb070 }, c.sh);
      c.legMat = softMat({ color: 0xa9dcb2, top: 0xbfe6c4, y0: -1, y1: 1, sss: 0x6fcf9a }, c.sh);
      c.hip = [0.1, 0.17, 0]; c.shoulder = [0.28, 0.4, 0.02];
    },
  },
  {
    id: 'robo', name: '啵啵', sub: '圓頭小機器人', why: '發光的臉＋彈簧天線：表情最清楚，辦公室助理的感覺',
    R: 0.33, walk: 1.5, run: 3.6, jumpV: 5.8, stride: [0.46, 1.0], lat: 0.115, footFwd: 0.03, footSize: [0.085, 0.06, 0.11], handR: 0.066,
    hand: [0.31, 0.25, 0.05], front: 0.34, cheek: [0.24, 0.5, 0.33], waddle: 0.06, bob: 0.03, wob: 0.6, mouth: [0, 0.44, 0.36], top: 0.95,
    face: { kind: 'screen', ex: 78, ey: 262, rx: 27, ry: 34, my: 312, mw: 15, glow: '#9ff4ff', blush: '255,140,190', blushAmt: 0.9, visor: { w: 392, h: 236, y: 152, r: 108, c0: '#1d2444', c1: '#303a6b' } },
    build(c) {
      const white = { color: 0xe6e6fb, top: 0xfdfcff, sss: 0xa9b6ff, sssAmt: 0.22, rim: 0xffffff, rough: 0.42 };
      const m = softMat({ ...white, y0: -0.3, y1: 0.25, face: c.face, headC: [0, -0.02, 0], span: [2.35, 2.35], glow: 0.8 }, c.sh);
      const head = new THREE.Mesh(blobGeo(v => { const rh = Math.hypot(v.x, v.z) || 1e-6, k = Math.pow(rh, 0.86) / rh; v.set(v.x * k * 0.385, v.y * 0.315, v.z * k * 0.355); }), m);
      head.position.y = 0.58; c.main = head; c.deform.add(head);
      const bm = softMat({ ...white, y0: -0.2, y1: 0.2 }, c.sh);
      const torso = new THREE.Mesh(blobGeo(v => { const b = 1 + 0.12 * sstep(0.3, -0.8, v.y); v.set(v.x * 0.215 * b, v.y * 0.19, v.z * 0.195 * b); }, 48, 36), bm);
      torso.position.y = 0.2; c.deform.add(torso); c.extra.push(torso);
      const am = softMat({ color: 0x9db2ff, top: 0xc3d0ff, y0: -1, y1: 1, sss: 0x8a7bff, sssAmt: 0.3, rough: 0.45 }, c.sh);
      for (const s of [-1, 1]) { const e = new THREE.Mesh(ball(), am); e.scale.set(0.05, 0.105, 0.105); e.position.set(s * 0.375, 0.58, 0); c.deform.add(e); c.extra.push(e); }
      const belt = new THREE.Mesh(ball(), am); belt.scale.set(0.05, 0.05, 0.025); belt.position.set(0, 0.23, 0.185); c.deform.add(belt);
      const piv = new THREE.Group(); piv.position.set(0, 0.58 + 0.3, 0); c.deform.add(piv);
      const st = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.016, 0.15, 12), bm); st.position.y = 0.07; piv.add(st);
      const tipM = softMat({ color: 0xffb3c8, top: 0xffd6e0, y0: -1, y1: 1, sss: 0xff6f9a, sssAmt: 0.6, rough: 0.35 }, c.sh);
      const tip = new THREE.Mesh(ball(), tipM); tip.scale.setScalar(0.052); tip.position.y = 0.17; piv.add(tip); c.tipMat = tipM;
      c.apps.push({ piv, side: 0, k: 95, c: 5, g: 0.035, gy: 0, rest: [0, 0], droop: 0, bend: 0.7 });
      c.limbMat = am;
    },
  },
];

const ACT = {
  wave: { dur: 2.0, lock: true, cam: true }, bow: { dur: 1.7, lock: true, cam: true }, dance: { dur: 4.4, lock: true, cam: true }, spin: { dur: 0.9, lock: true },
  eat: { dur: 2.9, lock: true, cam: true }, catch: { dur: 2.6, lock: true }, yawn: { dur: 2.2, lock: false }, talk: { dur: 1.8, lock: false, cam: true },
  shake: { dur: 0.6, lock: true }, stomp: { dur: 1.6, lock: true },
};
const EMO_DUR = 3.2;

export class Character {
  constructor(cfg, scene, world, fx) {
    this.cfg = cfg; this.scene = scene; this.world = world; this.fx = fx; this.R = cfg.R;
    this.sh = { uTint: { value: new THREE.Color(1, 1, 1) }, uTintAmt: { value: 0 }, uGround: { value: 0 } };
    this.face = new Face(cfg.face);
    this.root = new THREE.Group(); this.tilt = new THREE.Group(); this.tumble = new THREE.Group(); this.deform = new THREE.Group();
    this.root.add(this.tilt); this.tilt.add(this.tumble); this.tumble.add(this.deform);
    this.tumble.position.y = cfg.R; this.deform.position.y = -cfg.R; this.deform.matrixAutoUpdate = false;
    this.apps = []; this.extra = []; this.parts = [];
    cfg.build(this);
    scene.add(this.root);
    this.root.traverse(o => { if (o.isMesh) { o.castShadow = true; o.userData.char = this; } });
    this.pickList = []; this.root.traverse(o => { if (o.isMesh) this.pickList.push(o); });
    // 腳、手（放在世界座標，腳會「種」在地上）
    const fs = cfg.footSize;
    this.feet = [-1, 1].map(s => { const m = new THREE.Mesh(foot(), this.limbMat); m.scale.set(fs[0], fs[1], fs[2]); m.castShadow = true; m.userData.char = this; scene.add(m); this.pickList.push(m); return { s, m, p: new V3(), v: new V3(), from: new V3(), planted: true, sw: 1, yaw: 0, lift: 0, timed: 0 }; });
    this.hands = [-1, 1].map(s => { const m = new THREE.Mesh(ball(), this.limbMat); m.scale.setScalar(cfg.handR); m.castShadow = true; m.userData.char = this; scene.add(m); this.pickList.push(m); return { s, m, p: new V3(), v: new V3() }; });
    this.limbs = [];
    if (cfg.legs) {
      const lg = new THREE.CylinderGeometry(1, 1, 1, 14); lg.translate(0, 0.5, 0);
      for (let i = 0; i < 4; i++) { const m = new THREE.Mesh(lg, this.legMat); m.castShadow = true; scene.add(m); this.limbs.push(m); }
    }
    this.shadow = world.mkShadow(cfg.R * 1.15);
    // 狀態
    this.pos = new V3(0, 0, 0.9); this.vel = new V3(); this.yaw = 0; this.yawRate = 0; this.grounded = true; this.groundS = null; this.airT = 0;
    this.mode = 'normal'; this.modeT = 0; this.act = null; this.goal = null; this.jumpPrep = 0; this.jumpBuf = 0; this.skid = false; this.pushing = 0; this.hop = null;
    this.sq = 0; this.sqV = 0; this.sqT = 0; this.wob = new V3(); this.wobV = new V3(); this.acc = new V3(); this.accS = new V3();
    this.pitch = 0; this.roll = 0; this.phase = 0; this.bobY = 0; this.yOff = 0;
    this.emo = null; this.idleT = 0; this.petting = false; this.pokeN = 0; this.pokeT = 9; this.dent = 0; this.dentV = 0; this.dentT = 0;
    this.gaze = new V3(0, 0.5, 5); this.gx = 0; this.gy = 0; this.lookT = 0; this.lookP = new V3(); this.speech = null; this.zT = 0; this.heartT = 0; this.stepSnd = 0;
    this.w = new V3(); this.tq = new THREE.Quaternion(); this.holdT = new V3(); this.camPos = new V3(4, 3, 6);
    this.stat = { slip: 0, slipN: 0, maxPen: 0 };
    this.feet.forEach(f => { this.footHome(f, f.p); f.yaw = this.yaw; });
    this.hands.forEach(h => { h.p.set(this.pos.x + h.s * cfg.hand[0], cfg.hand[1], this.pos.z); });
    this.t = 0; this.syncGroups(); this.root.updateMatrixWorld(true);
  }
  dispose() {
    const S = this.scene; S.remove(this.root, this.shadow, ...this.feet.map(f => f.m), ...this.hands.map(h => h.m), ...this.limbs);
    this.face.tex.dispose();
  }
  get center() { return _d.set(this.pos.x, this.pos.y + this.R, this.pos.z); }
  headTop(out) { return out.set(this.pos.x, this.pos.y + this.cfg.top * (1 + this.sq) + this.yOff, this.pos.z); }
  mouthWorld(out) { return this.deform.localToWorld(out.set(...this.cfg.mouth)); }
  footHome(f, out, fwd = 0, side = 1) { const c = this.cfg, cy = Math.cos(this.yaw), sy = Math.sin(this.yaw), lx = f.s * c.lat * side, lz = c.footFwd + fwd; return out.set(this.pos.x + lx * cy + lz * sy, this.pos.y, this.pos.z - lx * sy + lz * cy); }
  busy() { return this.mode !== 'normal' || (this.act && ACT[this.act.name].lock); }

  // ── 對外指令
  wake() { this.idleT = 0; if (this.mode === 'sleep' || this.mode === 'sit') { const was = this.mode; this.mode = 'normal'; this.modeT = 0; if (was === 'sleep') { this.sqV += 3; this.emote('surprised', 0.7); } return true; } return false; }
  setGoal(x, z, run, use = null) { if (this.mode === 'held' || this.mode === 'tumble' || this.mode === 'recover' || this.mode === 'dizzy') return; this.wake(); if (this.act && ACT[this.act.name].lock) return; this.act = null; this.goal = { x: clamp(x, BOUNDS.x0 + 0.3, BOUNDS.x1 - 0.3), z: clamp(z, BOUNDS.z0 + 0.3, BOUNDS.z1 - 0.3), run, use, t: 0, stuck: 0 }; }
  useThing(u) { if (u.type === 'sleep') this.setGoal(u.seat.x, u.seat.z, false, u); else this.setGoal(u.from.x, u.from.z, false, u); }
  jump() { this.jumpBuf = 0.16; }
  emote(name, dur = EMO_DUR) { this.emo = { name, t: dur }; this.idleT = 0; if (name === 'surprised' && this.grounded && this.mode === 'normal') this.sqV += 4; if (name === 'angry') this.fx.sfx('angry'); if (name === 'laugh') this.fx.sfx('laugh'); }
  say(text, dur = 1.8) { this.speech = { text, t: dur, talk: Math.min(dur, 0.25 + text.length * 0.16) }; }
  doAct(name, data) {
    if (this.mode === 'sleep' || this.mode === 'sit') this.wake();
    if (this.mode !== 'normal') return false; if (this.act && ACT[this.act.name].lock && name !== 'catch') return false;
    this.goal = null; this.act = { name, t: 0, dur: ACT[name].dur, data, f: 0 }; this.idleT = 0;
    if (name === 'wave') this.say('嗨～'); if (name === 'talk') this.say(data || '今天也要加油！', 1.9); if (name === 'yawn') this.fx.sfx('yawn');
    return true;
  }
  sit() { if (this.mode !== 'normal' || !this.grounded) return; this.goal = null; this.act = null; this.mode = 'sit'; this.modeT = 0; this.vel.set(0, 0, 0); this.sqV -= 2; }
  sleep() { if (this.mode === 'sleep') return; if (this.mode !== 'normal' && this.mode !== 'sit') return; this.goal = null; this.act = null; this.mode = 'sleep'; this.modeT = 0; this.vel.set(0, 0, 0); }
  poke(hit, dir) {
    this.idleT = 0; const woke = this.wake();
    this.pokeN = this.pokeT < 2.4 ? this.pokeN + 1 : 1; this.pokeT = 0;
    // 凹陷位置（主體的物件座標）＋果凍晃動
    const U = this.main.material.userData.U; this.main.worldToLocal(_a.copy(hit)); U.uDent.value.set(_a.x, _a.y, _a.z, 0); this.dent = 0.075; this.dentV = 0;
    this.wobV.x += dir.x * 2.6 * this.cfg.wob; this.wobV.z += dir.z * 2.6 * this.cfg.wob; this.sqV -= 1.6;
    this.fx.sfx(this.pokeN % 2 ? 'poke' : 'squeak');
    if (woke) { this.say('嗯…？', 1.2); return; }
    if (this.mode === 'dizzy' || this.mode === 'tumble' || this.mode === 'held') return;
    if (this.pokeN <= 2) this.emote('surprised', 0.7);
    else if (this.pokeN <= 5) { this.emote('laugh', 1.5); if (this.pokeN === 3) this.say('好癢！', 1.2); }
    else { this.emote('angry', 2.8); if (this.pokeN === 6 || this.pokeN % 4 === 0) { this.say('不要戳啦！', 1.6); if (this.mode === 'normal' && !this.busy()) this.doAct('stomp'); } }
  }
  petStart(hit) { this.wake(); this.petting = true; this.heartT = 0; this.goal = null; this.petHit = hit ? this.main.worldToLocal(hit.clone()) : new V3(0, 0.3, 0.1); }
  petEnd() { if (!this.petting) return; this.petting = false; this.emote('happy', 1.6); }
  grab() { this.wake(); this.mode = 'held'; this.modeT = 0; this.goal = null; this.act = null; this.petting = false; this.grounded = false; this.hop = null; this.holdT.copy(this.center); this.fx.sfx('squeak'); this.feet.forEach(f => f.planted = false); }
  dragTo(p) { this.holdT.set(clamp(p.x, BOUNDS.x0 + 0.3, BOUNDS.x1 - 0.3), clamp(p.y, this.R + 0.05, 2.9), clamp(p.z, BOUNDS.z0 + 0.3, BOUNDS.z1 - 0.3)); }
  release() {
    if (this.mode !== 'held') return; const sp = this.vel.length(); if (sp > 10) this.vel.multiplyScalar(10 / sp);
    if (sp > 2.4) { this.mode = 'tumble'; this.modeT = 0; this.rest = 0; this.w.set(this.vel.z, 0, -this.vel.x).multiplyScalar(1.3 / this.R).add(_a.set(Math.random() - .5, Math.random() - .5, Math.random() - .5).multiplyScalar(4)); this.fx.sfx('whee'); }
    else { this.mode = 'normal'; this.modeT = 0; this.grounded = false; this.airT = 1; }
  }
  onKick() { if (this.mode === 'normal' && !this.emo) this.emote('happy', 0.8); }
  onBallHit(o, rel, nx, ny, nz) {
    if (this.act && this.act.name === 'catch' && this.act.data === o && !this.act.miss) return;
    if (this.mode === 'held' || this.mode === 'tumble') return;
    this.wake(); this.wobV.x -= nx * rel * 0.5 * this.cfg.wob; this.wobV.z -= nz * rel * 0.5 * this.cfg.wob; this.sqV -= 2;
    this.fx.sfx('bonk'); this.fx.burst('star', _a.copy(o.p), 4, { speed: 1.6, up: 1.5, g: 5, life: 0.6, size: 0.16, spin: 5 });
    if (rel > 6.5 && this.mode === 'normal') { this.act = null; this.goal = null; this.mode = 'tumble'; this.modeT = 0; this.rest = 0; this.grounded = false; this.vel.set(-nx * rel * 0.4, 2.8, -nz * rel * 0.4); this.w.set(this.vel.z, 0, -this.vel.x).multiplyScalar(2.5 / this.R); return; }
    if (this.mode === 'normal' || this.mode === 'sit') { this.emote(rel > 4 ? 'angry' : 'ouch', rel > 4 ? 2 : 1); if (rel > 4) this.say('好痛！', 1.2); }
  }
  startCatch(ballObj, ok) { if (!this.doAct('catch', ballObj)) return false; this.act.miss = !ok; return true; }

  // ── 物理子步
  step(h, ctl) {
    const p = this.pos, v = this.vel, W = this.world, c = this.cfg; const vx0 = v.x, vy0 = v.y, vz0 = v.z;
    this.modeT += h; if (this.pushing > 0) this.pushing -= h;
    if (ctl.jump) { this.jumpBuf = 0.16; ctl.jump = false; }
    if (this.jumpBuf > 0) this.jumpBuf -= h;
    const inp = Math.hypot(ctl.mx, ctl.mz) > 0.05;
    if (this.mode === 'normal') this.stepNormal(h, ctl);
    else if (this.mode === 'held') {
      _a.copy(this.holdT).sub(this.center); v.x += (_a.x * 150 - v.x * 17) * h; v.y += (_a.y * 150 - v.y * 17) * h; v.z += (_a.z * 150 - v.z * 17) * h;
      p.addScaledVector(v, h); p.y = Math.max(p.y, W.groundAt(p.x, p.z, p.y + 0.3).h);
      this.tumble.quaternion.slerp(_q.identity(), 1 - Math.exp(-h * 8));
    } else if (this.mode === 'tumble') this.stepTumble(h);
    else {
      v.set(0, 0, 0);
      if ((this.mode === 'sit' || this.mode === 'sleep') && (inp || this.jumpBuf > 0)) { this.wake(); }
    }
    // 慣性 → 果凍晃動與附屬物
    const A = this.acc.set(clamp((v.x - vx0) / h, -70, 70), clamp((v.y - vy0) / h, -90, 90), clamp((v.z - vz0) / h, -70, 70));
    this.accS.lerp(A, 1 - Math.exp(-h * 14));
    const wk = 125, wc = 8.5, g = 0.75 * c.wob;
    this.wobV.x += (-wk * this.wob.x - wc * this.wobV.x - A.x * g) * h; this.wobV.z += (-wk * this.wob.z - wc * this.wobV.z - A.z * g) * h;
    this.wob.x = clamp(this.wob.x + this.wobV.x * h, -0.5, 0.5); this.wob.z = clamp(this.wob.z + this.wobV.z * h, -0.5, 0.5);
    // 擠壓伸展彈簧（體積守恆在 syncGroups 做）
    let tgt = this.sqT;
    if (this.jumpPrep > 0) { tgt = -0.34; this.sqV -= 22 * h; } else if (!this.grounded && this.mode !== 'held') tgt = clamp(Math.abs(v.y) * 0.032, 0, 0.28); else if (this.mode === 'held') tgt = 0.1;
    this.sqV += (-190 * (this.sq - tgt) - 13.5 * this.sqV) * h; this.sq = clamp(this.sq + this.sqV * h, -0.55, 0.6);
    this.dentV += (-320 * this.dent - 11 * this.dentV) * h; this.dent += this.dentV * h;
    // 附屬物彈簧
    const cy = Math.cos(this.yaw), sy = Math.sin(this.yaw), ax = A.x * cy - A.z * sy, az = A.x * sy + A.z * cy;
    for (const a of this.apps) {
      a.x ??= 0; a.z ??= 0; a.vx ??= 0; a.vz ??= 0; a.tx ??= 0; a.tz ??= 0;
      a.vx += (-a.k * (a.x - a.tx) - a.c * a.vx - az * a.g * a.k) * h; a.vz += (-a.k * (a.z - a.tz) - a.c * a.vz + ax * a.g * a.k - a.side * A.y * a.gy * a.k) * h;
      a.x = clamp(a.x + a.vx * h, -1.3, 1.3); a.z = clamp(a.z + a.vz * h, -1.3, 1.3);
    }
  }
  stepNormal(h, ctl) {
    const p = this.pos, v = this.vel, W = this.world, c = this.cfg;
    let mx = ctl.mx, mz = ctl.mz, mag = Math.hypot(mx, mz), run = ctl.run;
    const lock = this.act && ACT[this.act.name].lock;
    if (mag > 0.05) { if (mag > 1) { mx /= mag; mz /= mag; mag = 1; } this.goal = null; this.idleT = 0; this.hop && (this.hop.auto = 0); }
    else if (this.goal && !this.hop) {
      const g = this.goal, dx = g.x - p.x, dz = g.z - p.z, d = Math.hypot(dx, dz); g.t += h;
      if (Math.hypot(v.x, v.z) < 0.2 && g.t > 0.4) g.stuck += h; else g.stuck = 0;
      if (d < 0.09 || g.t > 9 || g.stuck > 0.8) { this.goal = null; mag = 0; if (g.use && (d < 0.5 || g.use.type !== 'sleep')) this.startUse(g.use); }
      else { mx = dx / d; mz = dz / d; mag = Math.min(1, 0.3 + d / 0.5); run = g.run && d > 0.9; }
    } else mag = 0;
    if (lock || this.petting) mag = 0;
    const top = (run ? c.run : c.walk) * (this.pushing > 0 ? 0.5 : 1) * (this.emo && this.emo.name === 'sad' ? 0.6 : 1) * (this.emo && this.emo.name === 'sleepy' ? 0.7 : 1);
    const sp = Math.hypot(v.x, v.z), dvx = mx * mag * top, dvz = mz * mag * top;
    if (!this.hop) {
      let a;
      if (this.grounded) {
        if (mag < 0.05) { if (sp > c.walk * 1.35) this.skid = true; else if (sp < 0.35) this.skid = false; a = this.skid ? 6.5 : 15; }
        else { const dot = sp > 0.01 ? (v.x * mx + v.z * mz) / sp : 1; if (sp > 2.1 && dot < -0.25) this.skid = true; else if (sp < 0.6 || dot > 0.2) this.skid = false; a = this.skid ? 10 : (run ? 13 : 11); }
      } else { a = 5; this.skid = false; }
      const ex = dvx - v.x, ez = dvz - v.z, el = Math.hypot(ex, ez), st = a * h;
      if (el <= st) { v.x = dvx; v.z = dvz; } else { v.x += ex / el * st; v.z += ez / el * st; }
      if (this.skid && this.grounded && sp > 1) { this.skidFx = (this.skidFx || 0) - h; if (this.skidFx <= 0) { this.skidFx = 0.07; this.fx.spawn('dust', _a.set(p.x, p.y + 0.06, p.z), { v: _b.set(-v.x * 0.15, 0.5, -v.z * 0.15), life: 0.5, size: 0.22, grow: 2.5, drag: 2 }); if (!this.skidS) { this.fx.sfx('skid'); this.skidS = 1; } } } else this.skidS = 0;
    }
    // 轉向：面向移動方向；轉彎速度留給身體側傾用
    let ty = this.yaw; const act = this.act;
    if (mag > 0.05 && !this.skid) ty = Math.atan2(mx, mz);
    else if (this.faceYaw != null) ty = this.faceYaw;
    const dy = angDiff(ty, this.yaw), r = clamp(dy * 13, -15, 15); this.yawRate = lerp(this.yawRate, r, 1 - Math.exp(-h * 20)); this.yaw += this.yawRate * h;
    // 跳：先下蹲（預備動作）再起跳
    if (this.grounded) this.airT = 0; else this.airT += h;
    if (this.jumpBuf > 0 && this.jumpPrep <= 0 && (this.grounded || this.airT < 0.1) && !lock && !this.hop) { this.jumpPrep = 0.12; this.jumpBuf = 0; this.idleT = 0; }
    if (this.jumpPrep > 0) {
      this.jumpPrep -= h;
      if (this.jumpPrep <= 0) {
        const ph = this.pendHop; this.pendHop = null;
        if (ph) { v.x = ph.vx; v.z = ph.vz; v.y = ph.vy; this.hop = ph; } else v.y = c.jumpV;
        this.grounded = false; this.airT = 0.2; this.sqV += 5.5; this.fx.sfx('jump'); this.feet.forEach(f => f.planted = false);
        this.fx.burst('dust', _a.set(p.x, p.y + 0.05, p.z), 4, { speed: 0.7, up: 0.3, life: 0.4, size: 0.18, grow: 2, drag: 3 });
      }
    }
    v.y -= G * h; const y0 = p.y; p.addScaledVector(v, h);
    const gr = W.groundAt(p.x, p.z, Math.max(y0, p.y));
    if (p.y <= gr.h && v.y <= 0) {
      const imp = -v.y; p.y = gr.h; v.y = 0;
      if (!this.grounded) this.onLand(imp, gr.s); else this.groundS = gr.s;
    } else if (this.grounded && p.y > gr.h + 0.03) { this.grounded = false; }
    else if (this.grounded) { p.y = gr.h; v.y = 0; this.groundS = gr.s; }
    if (this.grounded) W.pushBox(this);
    const hit = W.resolve(p, this.R * 0.8, p.y, v, 0, this.hop ? this.hop.use.solid : null);
    if (hit && hit.tag === 'plant') W.plantShake = Math.min(1.5, W.plantShake + 0.04);
    this.stat.maxPen = Math.max(this.stat.maxPen, gr.h - p.y);
  }
  startUse(u) {
    const p = this.pos, dx = u.seat.x - p.x, dz = u.seat.z - p.z, dy = u.seat.y - p.y;
    if (u.type === 'sleep') { this.faceYaw = null; this.yawTo = u.yaw; this.sleep(); return; }
    const H = Math.max(dy, 0) + 0.42, vy = Math.sqrt(2 * G * H), T = vy / G + Math.sqrt(2 * (H - dy) / G);
    this.pendHop = { use: u, vx: dx / T, vz: dz / T, vy, auto: u.type === 'hop' ? 4 : 0 }; this.yaw = Math.atan2(dx, dz); this.jumpPrep = 0.13;
  }
  onLand(imp, s) {
    const p = this.pos, v = this.vel; this.grounded = true; this.groundS = s;
    const hop = this.hop;
    if (s && s.bounce) {
      const boost = this.jumpBuf > 0 || (hop && hop.auto > 0); let out = boost ? Math.min(imp * 0.62 + 4.6, 9.3) : imp * 0.7;
      if (hop) { hop.auto--; v.x = (s.x - p.x) * 1.2; v.z = (s.z - p.z) * 1.2; if (hop.auto <= 0) { this.hop = null; } }
      if (out > 2.3) { v.y = out; this.grounded = false; this.sqV -= imp * 0.35; this.jumpBuf = 0; this.world.bounceTramp(imp); if (out > 7.5 && !this.emo) this.emote('whee', 0.9); return; }
    }
    this.hop = null;
    this.sq = Math.min(this.sq, 0.03); this.sqV = -Math.min(imp, 13) * (s && s.soft ? 0.85 : 0.72);
    if (imp > 2.2) { this.fx.sfx('land', imp / 8); this.fx.burst('dust', _a.set(p.x, p.y + 0.05, p.z), imp > 5 ? 7 : 4, { speed: 0.5 + imp * 0.12, up: 0.25, life: 0.45, size: 0.2, grow: 2.2, drag: 3 }); }
    this.feet.forEach(f => { this.footHome(f, f.p); f.planted = true; f.sw = 1; f.yaw = this.yaw; });
    if (hop && s === hop.use.solid && hop.use.type === 'sit') { v.x = v.z = 0; p.x = hop.use.seat.x; p.z = hop.use.seat.z; this.yawTo = hop.use.yaw; this.mode = 'sit'; this.modeT = 0; }
  }
  stepTumble(h) {
    const p = this.pos, v = this.vel, W = this.world, R = this.R, w = this.w;
    v.y -= G * h; const y0 = p.y; p.addScaledVector(v, h);
    const wl = w.length(); if (wl > 1e-4) { _q.setFromAxisAngle(_a.copy(w).divideScalar(wl), wl * h); this.tumble.quaternion.premultiply(_q); }
    const gr = W.groundAt(p.x, p.z, Math.max(y0, p.y), 0.05); let rest = false;
    if (p.y <= gr.h) {
      p.y = gr.h;
      if (v.y < 0) {
        const imp = -v.y;
        if (gr.s && gr.s.bounce && imp > 1.5) { v.y = imp * 0.8; W.bounceTramp(imp); }
        else if (imp > 1.5) { v.y = imp * (gr.s && gr.s.soft ? 0.25 : 0.46); v.x *= 0.82; v.z *= 0.82; this.fx.sfx('land', imp / 7); this.fx.burst('dust', _a.set(p.x, p.y + 0.05, p.z), 5, { speed: 0.9, up: 0.3, life: 0.45, size: 0.2, grow: 2, drag: 3 }); }
        else { v.y = 0; rest = true; }
        if (imp > 1.5) { this.sqV -= Math.min(imp, 10) * 0.32; w.lerp(_a.set(v.z / R, 0, -v.x / R), 0.7); }
      } else rest = v.y === 0;
    }
    if (rest) { const k = Math.exp(-2.4 * h); v.x *= k; v.z *= k; const sp = Math.hypot(v.x, v.z), d = Math.max(0, sp - 1.2 * h) / (sp || 1); v.x *= d; v.z *= d; w.lerp(_a.set(v.z / R, 0, -v.x / R), 1 - Math.exp(-12 * h)); }
    const vb = _b.copy(v), hit = W.resolve(p, R * 0.9, p.y, v, 0.45);
    if (hit && vb.sub(v).length() > 1.5) { w.multiplyScalar(-0.5); this.fx.sfx('bonk'); this.sqV -= 2; }
    if (p.y > 2.7 && v.y > 0) v.y *= -0.3;
    if (rest && Math.hypot(v.x, v.z) < 0.3) this.rest += h; else this.rest = 0;
    if (this.rest > 0.12 || this.modeT > 7) { v.set(0, 0, 0); w.set(0, 0, 0); this.mode = 'recover'; this.modeT = 0; this.tq.copy(this.tumble.quaternion); this.grounded = true; this.groundS = gr.s; }
  }

  // ── 每幀：表情、姿態、手腳、臉
  animate(dt, env) {
    this.t += dt; const t = this.t, c = this.cfg, p = this.pos, v = this.vel, fx = this.fx; this.camPos.copy(env.cam);
    const sp = Math.hypot(v.x, v.z), runF = sstep(c.walk * 1.05, c.run * 0.9, sp);
    this.pokeT += dt; if (this.emo && (this.emo.t -= dt) <= 0) this.emo = null;
    if (this.speech && (this.speech.t -= dt) <= 0) this.speech = null;
    const camYaw = Math.atan2(env.cam.x - p.x, env.cam.z - p.z);
    this.faceYaw = null; this.sqT = 0;
    let expr = 'neutral', pitchT = 0, rollT = 0, yOff = 0, yawAdd = 0, tint = null, tintA = 0, appDroop = 0, appWig = 0;
    const HP = [new V3(), new V3()]; let hk = 230, hc = 20;   // 手的目標（相對腳底的區域座標）
    const hx = c.hand[0], hy = c.hand[1], hz = c.hand[2];
    const setH = (i, x, y, z) => HP[i].set(x, y, z);
    const both = (x, y, z) => { setH(0, -x, y, z); setH(1, x, y, z); };
    const breath = Math.sin(t * 2.1) * 0.012;
    both(hx, hy + breath * 0.6, hz);
    const emo = this.emo ? this.emo.name : null;
    // ── 模式
    if (this.mode === 'recover') {
      const u = clamp(this.modeT / 0.55, 0, 1), e = u * u * (3 - 2 * u); this.tumble.quaternion.copy(this.tq).slerp(_q.identity(), e); yOff = Math.sin(u * Math.PI) * 0.12; expr = 'dizzy';
      if (u >= 1) { this.mode = 'dizzy'; this.modeT = 0; this.fx.sfx('dizzy'); this.say(['頭好暈…', '嗚哇…', '轉圈圈…'][Math.floor(Math.random() * 3)], 1.3); this.feet.forEach(f => { this.footHome(f, f.p); f.planted = true; f.sw = 1; }); for (let i = 0; i < 3; i++) fx.spawn('star', new V3(c.R * 0.75, c.top + 0.12, 0), { follow: p, orbit: 5, life: 1.6, size: 0.15, spin: 3 }).userData.ph = i * 2.094; }
    } else if (this.mode === 'dizzy') {
      expr = 'dizzy'; rollT = Math.sin(t * 5) * 0.16; pitchT = Math.cos(t * 3.7) * 0.08; both(hx * 1.15, hy + 0.05 + Math.sin(t * 6) * 0.04, hz);
      if (this.modeT > 1.6) { this.mode = 'normal'; this.modeT = 0; this.act = { name: 'shake', t: 0, dur: ACT.shake.dur }; }
    } else if (this.mode === 'held') {
      expr = this.modeT < 0.5 ? 'surprised' : 'effort'; hk = 120; hc = 9;
      both(hx * 1.2, hy + 0.2 + Math.sin(t * 17) * 0.05 * (this.modeT > 0.5 ? 1 : 0), hz);
    } else if (this.mode === 'tumble') { expr = v.length() > 3 ? 'whee' : 'ouch'; hk = 90; hc = 7; both(hx * 1.3, hy + 0.12, 0); }
    else if (this.mode === 'sit') {
      this.sqT = -0.1; expr = emo || 'neutral'; both(hx * 0.7, hy - 0.08, c.front * 0.7);
      if (this.yawTo != null) this.faceYaw = this.yawTo;
    } else if (this.mode === 'sleep') {
      this.sqT = -0.2 + Math.sin(t * 1.5) * 0.035; expr = 'sleep'; rollT = 0.13; pitchT = 0.08; both(hx * 0.85, hy - 0.14, c.front * 0.5); appDroop = 1;
      if (this.yawTo != null) this.faceYaw = this.yawTo;
      if ((this.zT -= dt) <= 0) { this.zT = 1.15; fx.spawn('zzz', this.headTop(new V3()).add(_a.set(0.15, 0.02, 0.1)), { v: new V3(0.16, 0.3, 0), life: 2.2, size: 0.13, grow: 0.55, sway: 0.5, fadeIn: 0.3 }); }
    }
    if (this.mode !== 'sit' && this.mode !== 'sleep') this.yawTo = null;
    // ── 一般狀態：走跑跳的姿態
    const moving = this.mode === 'normal' && this.grounded && sp > 0.2;
    if (this.mode === 'normal') {
      const cy = Math.cos(this.yaw), sy = Math.sin(this.yaw), af = this.accS.x * sy + this.accS.z * cy;
      if (this.grounded) {
        pitchT = clamp(af * 0.02, -0.3, 0.3) + runF * 0.2 + (this.skid ? -0.36 : 0);
        rollT = clamp(-this.yawRate * sp * 0.035, -0.32, 0.32);
        if (this.pushing > 0) { pitchT += 0.2; both(hx * 0.55, hy + 0.02, c.front + 0.1); expr = 'effort'; }
        else if (this.skid) { both(hx * 1.25, hy + 0.12, hz + 0.1); expr = 'surprised'; }
      } else {
        expr = v.y < -6.5 ? 'whee' : (this.airT > 0.05 ? 'look' : expr); pitchT = clamp(sp * 0.03, 0, 0.14);
        const up = v.y > 0 ? 1 : 0; both(hx * (1.15 + 0.1 * (1 - up)), hy + (up ? 0.02 : 0.24), hz);
      }
      if (this.jumpPrep > 0) both(hx * 1.1, hy - 0.1, hz - 0.06);
      // 情緒 → 身體姿態
      const idle = this.grounded && !moving && !this.act && this.jumpPrep <= 0;
      if (emo) {
        expr = emo;
        if (idle) switch (emo) {
          case 'happy': yOff = Math.abs(Math.sin(t * 7)) * 0.07; this.sqT = -0.05 + 0.1 * Math.abs(Math.sin(t * 7)); both(hx * 1.2, hy + 0.26, hz); appWig = 0.3; break;
          case 'laugh': this.sqT = Math.sin(t * 22) * 0.05 - 0.03; pitchT = -0.16; both(hx * 0.62, hy - 0.03, c.front * 0.92); yOff = Math.abs(Math.sin(t * 11)) * 0.03; appWig = 0.2; break;
          case 'surprised': this.sqT = 0.12; pitchT = -0.1; both(hx * 1.4, hy + 0.2, hz); appDroop = -0.5; break;
          case 'angry': this.sqT = 0.03; pitchT = 0.14; tint = [1, 0.45, 0.42]; tintA = 0.45; both(hx * 1.12 + Math.sin(t * 30) * 0.012, hy - 0.08, hz - 0.03); appDroop = -0.3; rollT = Math.sin(t * 26) * 0.03; break;
          case 'sad': this.sqT = -0.11; pitchT = 0.17; both(hx * 0.7, hy - 0.13, c.front * 0.75); appDroop = 1; rollT = Math.sin(t * 1.3) * 0.04; tint = [0.72, 0.8, 1.0]; tintA = 0.3; break;
          case 'sleepy': this.sqT = -0.07 + Math.sin(t * 1.4) * 0.03; rollT = Math.sin(t * 0.9) * 0.12; pitchT = 0.1 + Math.sin(t * 0.7) * 0.06; setH(0, -hx * 0.95, hy - 0.08, hz); setH(1, c.cheek[0] * 0.9, c.cheek[1] + 0.06 + Math.sin(t * 5) * 0.015, c.cheek[2] + 0.05); appDroop = 0.6; break;
          case 'shy': this.sqT = -0.05; yawAdd = Math.sin(t * 3.2) * 0.22; pitchT = 0.12; tint = [1, 0.6, 0.68]; tintA = 0.3; both(c.cheek[0], c.cheek[1] - 0.03, c.cheek[2] + 0.04); appDroop = 0.35; break;
          case 'smug': this.sqT = 0.05; pitchT = -0.2; both(hx * 0.98, hy - 0.06, hz + 0.06); rollT = 0.05; break;
        }
        else if (emo === 'angry') { tint = [1, 0.45, 0.42]; tintA = 0.45; } else if (emo === 'sad') appDroop = 1;
      } else if (moving && expr === 'neutral') expr = runF > 0.5 ? 'whee' : 'look';
      // 腳步循環（相位由走過的距離推進 → 腳不滑）
      if (moving && !this.skid) {
        const stride = lerp(c.stride[0], c.stride[1], runF); this.phase = (this.phase + sp * dt / stride) % 1;
        const amp = Math.min(1, sp / c.walk);
        yOff += (c.bob + runF * 0.035) * amp * (0.5 - 0.5 * Math.cos(this.phase * 4 * Math.PI)) - c.bob * 0.4 * amp;
        rollT += Math.sin(this.phase * 2 * Math.PI) * c.waddle * amp * (1 - runF * 0.4);
        const sw = Math.sin(this.phase * 2 * Math.PI) * (0.1 + runF * 0.12) * amp;
        if (!(this.pushing > 0)) { setH(0, -hx * (1 + runF * 0.12), hy + runF * 0.03, hz + sw - runF * 0.1); setH(1, hx * (1 + runF * 0.12), hy + runF * 0.03, hz - sw - runF * 0.1); }
      }
      // 動作
      const a = this.act;
      if (a) {
        a.t += dt; const u = a.t / a.dur; if (ACT[a.name].cam) this.faceYaw = camYaw;
        const bell = sstep(0, 0.25, u) * (1 - sstep(0.75, 1, u));
        switch (a.name) {
          case 'wave': expr = 'happy'; setH(1, hx * 1.15 + Math.sin(t * 13) * 0.085 * bell, hy + 0.36 * bell, hz + 0.05); rollT -= 0.1 * bell; yOff += Math.abs(Math.sin(t * 6.5)) * 0.03 * bell; appWig = 0.3; break;
          case 'bow': { const b = sstep(0.08, 0.38, u) * (1 - sstep(0.7, 0.95, u)); pitchT = 0.85 * b - 0.1 * sstep(0, 0.08, u) * (1 - sstep(0.08, 0.2, u)); this.sqT = -0.06 * b; expr = b > 0.4 ? 'bliss' : 'neutral'; both(hx * 0.6, hy - 0.05, c.front * 0.8 * b + hz); if (u > 0.95 && !a.f) { a.f = 1; this.emote('happy', 1.2); } break; }
          case 'dance': {
            const bt = a.t * 2.3 * Math.PI * 2, beat = Math.sin(bt), half = Math.sin(bt / 2); expr = u > 0.8 ? 'laugh' : 'happy';
            this.sqT = -0.13 * Math.max(0, beat); rollT = 0.2 * half; yOff += Math.max(0, -beat) * 0.07; yawAdd = u > 0.72 ? sstep(0.72, 0.95, u) * Math.PI * 2 : 0.25 * Math.sin(bt / 4);
            setH(0, -hx * 1.2, hy + 0.2 + 0.16 * half, hz); setH(1, hx * 1.2, hy + 0.2 - 0.16 * half, hz); appWig = 0.6;
            const bi = Math.floor(a.t * 2.3); if (bi !== a.f) { a.f = bi; fx.sfx('note', bi); fx.spawn('note', this.headTop(new V3()).add(_a.set((Math.random() - .5) * 0.6, 0.05, 0.1)), { v: new V3((Math.random() - .5) * 0.5, 0.7, 0), life: 1.1, size: 0.17, sway: 0.8, drag: 0.6 }); }
            break;
          }
          case 'spin': yawAdd = sstep(0, 1, u) * Math.PI * 2; this.sqT = 0.08; both(hx * 1.3, hy + 0.1, 0); expr = 'happy'; break;
          case 'shake': yawAdd = Math.sin(u * Math.PI * 6) * 0.45 * (1 - u); expr = 'effort'; break;
          case 'stomp': { expr = 'angry'; tint = [1, 0.45, 0.42]; tintA = 0.5; const st = Math.sin(a.t * 20); yOff += Math.abs(st) * 0.035; this.sqT = -0.06 * Math.max(0, st); both(hx * 1.15, hy - 0.1 + Math.abs(st) * 0.03, hz - 0.03); a.stomp = st; if ((a.f | 0) !== Math.floor(a.t * 6.4)) { a.f = Math.floor(a.t * 6.4); fx.sfx('step', 3); fx.spawn('dust', this.headTop(new V3()).add(_a.set((Math.random() - .5) * 0.4, -0.05, 0)), { v: new V3((Math.random() - .5) * 0.4, 0.9, 0), life: 0.6, size: 0.16, grow: 2.5 }); } break; }
          case 'yawn': { const b = sstep(0.1, 0.35, u) * (1 - sstep(0.7, 0.95, u)); if (b > 0.3) expr = 'yawn'; else expr = 'sleepy'; pitchT = -0.14 * b; this.sqT = 0.1 * b; setH(1, c.cheek[0] * 0.35, c.mouth[1] + 0.0, c.front + 0.07); HP[1].lerp(_a.set(hx, hy, hz), 1 - b); setH(0, -hx * (1 + 0.3 * b), hy + 0.22 * b, hz - 0.05); break; }
          case 'talk': expr = emo || 'happy'; setH(1, hx * 1.1, hy + 0.12 + Math.sin(t * 9) * 0.03, hz + 0.1); yOff += Math.abs(Math.sin(t * 8)) * 0.012; break;
          case 'eat': {
            const arrive = 0.62 / a.dur;
            if (u < arrive) { expr = 'eatOpen'; pitchT = -0.08; this.sqT = 0.08; both(hx * 0.8, hy + 0.1, c.front * 0.9); }
            else if (u < 0.78) { expr = 'chew'; const ch = Math.sin((a.t - 0.62) * 15); this.sqT = -0.07 * Math.max(0, ch) + 0.02; this.face.extraOpen = 0; both(c.cheek[0] * 0.8, c.cheek[1] - 0.06, c.cheek[2] + 0.03); if (!a.f) { a.f = 1; fx.sfx('eat'); fx.burst('crumb', this.mouthWorld(new V3()), 6, { speed: 0.8, up: 0.8, g: 6, life: 0.5, size: 0.05 }); } }
            else { expr = 'happy'; yOff += Math.abs(Math.sin(t * 8)) * 0.05; both(hx * 1.2, hy + 0.24, hz); if (a.f < 2) { a.f = 2; this.say(['好吃！', '還要！', '謝謝～'][Math.floor(Math.random() * 3)], 1.3); fx.sfx('heart'); fx.burst('heart', this.headTop(new V3()), 3, { speed: 0.35, up: 0.7, life: 1.1, size: 0.17, sway: 0.4 }); } }
            break;
          }
          case 'catch': {
            const o = a.data; this.faceYaw = Math.atan2(o.p.x - p.x, o.p.z - p.z); expr = a.got ? 'happy' : (a.miss ? 'surprised' : 'look');
            const chest = _c.set(p.x + Math.sin(this.yaw) * (c.front + o.r * 0.6), p.y + hy + 0.1, p.z + Math.cos(this.yaw) * (c.front + o.r * 0.6));
            if (!a.got) {
              both(hx * 0.75, hy + (a.miss ? 0.34 : 0.14), c.front + 0.06);
              if (!a.miss && o.p.distanceTo(chest) < o.r + 0.3 && a.t > 0.2) { a.got = a.t; o.held = true; o.caught = true; o.v.set(0, 0, 0); this.sqV -= 2.5; this.wobV.x -= Math.sin(this.yaw) * 1.5; this.wobV.z -= Math.cos(this.yaw) * 1.5; fx.sfx('kick'); fx.burst('spark', chest, 4, { speed: 0.8, up: 0.5, life: 0.4, size: 0.12 }); this.say('接到了！', 1.1); }
              if (a.t > 1.7 && !a.got) a.t = a.dur;
            } else {
              const g = a.t - a.got; both(o.r * 0.9 + 0.03, hy + 0.12, c.front + o.r * 0.5); o.p.lerp(chest, 0.5); yOff += Math.abs(Math.sin(g * 9)) * 0.05;
              if (g > 0.95) { o.held = false; o.p.y = p.y + c.top + o.r + 0.12; o.v.set(Math.sin(camYaw) * 2.0, 5.2, Math.cos(camYaw) * 2.0); setTimeout(() => { o.caught = false; }, 450); a.t = a.dur; this.emote('happy', 1.2); fx.sfx('jump'); }
            }
            break;
          }
        }
        if (a.t >= a.dur) { if (a.name === 'catch' && a.data.held) { a.data.held = false; a.data.caught = false; } this.act = null; }
      }
      // 摸頭
      if (this.petting) {
        expr = 'bliss'; this.sqT = -0.1 + Math.sin(t * 5) * 0.025; rollT += Math.sin(t * 4) * 0.05; both(hx * 1.02, hy + 0.05, hz + 0.05); appDroop = 0.5; appWig = 0.25;
        const U = this.main.material.userData.U; U.uDent.value.set(this.petHit.x, this.petHit.y, this.petHit.z, 0); this.dent = lerp(this.dent, 0.05, 0.2); this.dentV = 0;
        if ((this.heartT -= dt) <= 0) { this.heartT = 0.3; fx.spawn('heart', this.headTop(new V3()).add(_a.set((Math.random() - .5) * 0.5, -0.05, 0.15)), { v: new V3((Math.random() - .5) * 0.3, 0.75, 0), life: 1.2, size: 0.15 + Math.random() * 0.07, sway: 0.5, drag: 0.5 }); if (Math.random() < 0.45) fx.sfx('heart'); }
      }
      // 發呆：東張西望 → 打哈欠 → 坐下 → 睡著
      if (idle && !emo && !this.petting && !this.goal) {
        this.idleT += dt * (env.idleScale || 1); const it = this.idleT;
        if (it > 13 && !this.yawned) { this.yawned = true; this.doAct('yawn'); }
        if (it > 22) { this.sit(); this.idleSit = true; }
      } else if (!idle) { if (this.idleT < 1) this.yawned = false; }
    }
    if (this.mode === 'sit' && this.idleSit) { this.idleT += dt * (env.idleScale || 1); if (this.idleT > 26 && this.idleT < 34) expr = 'sleepy'; if (this.idleT > 34) { this.sleep(); } }
    if (this.mode === 'normal') this.idleSit = false;
    // ── 視線
    let look = env.look;
    if (this.act && this.act.name === 'eat' && env.food) look = env.food;
    if (!look || this.mode === 'sleep') {
      if ((this.lookT -= dt) <= 0) { this.lookT = 1.2 + Math.random() * 2.4; const a = this.yaw + (Math.random() - .5) * 2.2; this.lookP.set(p.x + Math.sin(a) * 3, 0.2 + Math.random() * 1.3, p.z + Math.cos(a) * 3); if (Math.random() < 0.4) this.lookP.copy(env.cam); }
      look = this.lookP;
    }
    const hw = this.main.getWorldPosition(_a), ldx = look.x - hw.x, ldy = look.y - hw.y, ldz = look.z - hw.z, lh = Math.hypot(ldx, ldz);
    const yawNow = this.yaw + yawAdd; let gyaw = angDiff(Math.atan2(ldx, ldz), yawNow), gp = Math.atan2(ldy, lh);
    const gxT = this.mode === 'tumble' || this.mode === 'dizzy' || this.mode === 'recover' ? 0 : clamp(gyaw / 1.0, -1, 1) * (Math.abs(gyaw) > 2.4 ? 0.3 : 1), gyT = clamp(gp / 0.8, -1, 1);
    const gk = 1 - Math.exp(-dt * 9); this.gx += (gxT - this.gx) * gk; this.gy += (gyT - this.gy) * gk;
    // 發呆時，看的東西在背後就慢慢轉過去
    if (this.mode === 'normal' && this.grounded && !moving && !this.act && this.jumpPrep <= 0 && env.look && Math.abs(gyaw) > 0.85 && this.faceYaw == null && !this.petting) { this.turnT = (this.turnT || 0) + dt; if (this.turnT > 0.5) this.faceYaw = this.yaw + gyaw * 0.8; } else this.turnT = 0;
    if (this.faceYaw != null && this.mode !== 'normal') { const d = angDiff(this.faceYaw, this.yaw); this.yaw += d * (1 - Math.exp(-dt * 8)); }
    // ── 身體傾斜平滑
    const tk = 1 - Math.exp(-dt * 11); this.pitch += (pitchT - this.pitch) * tk; this.roll += (rollT - this.roll) * tk; this.yOff += (yOff - this.yOff) * (1 - Math.exp(-dt * 30));
    this.yawAdd = yawAdd;
    const sh = this.sh; if (tint) sh.uTint.value.setRGB(...tint); sh.uTintAmt.value += ((tint ? tintA * (c.tintK ?? 1) : 0) - sh.uTintAmt.value) * (1 - Math.exp(-dt * 6));
    sh.uGround.value = this.mode === 'held' ? -50 : (this.grounded || this.mode === 'tumble' || this.mode === 'recover' ? p.y : this.world.groundAt(p.x, p.z, p.y + 0.1).h);
    // 附屬物的靜止角度（難過會垂下來、開心會擺）
    for (const a of this.apps) {
      const wig = appWig ? Math.sin(t * 11 + a.side) * appWig : 0;
      a.tx = a.rest[0] + (a.wag ? 0 : 0) + (a.side === 0 && !a.wag ? appDroop * 0.5 : 0); a.tz = a.rest[1] - a.side * a.droop * appDroop + wig * (a.side || 1);
      if (a.wag) a.tz = Math.sin(t * (appWig ? 16 : 3)) * (appWig ? 0.5 : 0.08);
      a.piv.rotation.set(a.x, 0, a.z);
    }
    this.face.set(expr);
    this.face.gx = this.gx; this.face.gy = -this.gy;
    const sp2 = this.speech; this.face.talk = sp2 && sp2.talk > 0 ? (sp2.talk -= dt, 0.12 + 0.45 * Math.abs(Math.sin(t * 15)) * (0.6 + 0.4 * Math.sin(t * 6.3))) : 0;
    this.face.update(dt, expr === 'dizzy' || expr === 'surprised' ? 22 : 12);
    const U = this.main.material.userData.U; U.uFaceOff.value.set(this.gx * 0.2, this.gy * 0.1 + (c.faceUp || 0)); U.uDent.value.w = this.dent;
    this.syncGroups(); this.root.updateMatrixWorld(true);
    this.updateFeet(dt, moving, sp, runF);
    this.updateHands(dt, HP, hk, hc);
    // 接觸陰影
    const gh = this.world.groundAt(p.x, p.z, p.y + 0.05).h, hg = p.y + this.yOff - gh;
    this.shadow.position.set(p.x, gh + 0.015, p.z); this.shadow.material.opacity = 0.6 * Math.max(0.2, 1 - hg * 0.45); this.shadow.scale.setScalar(c.R * 3.0 * (1 + hg * 0.35) * (1 - this.sq * 0.3));
  }
  syncGroups() {
    const sy = 1 + this.sq, sx = 1 / Math.sqrt(sy);
    this.root.position.set(this.pos.x, this.pos.y + (this.yOff || 0), this.pos.z); this.root.rotation.y = this.yaw + (this.yawAdd || 0);
    this.tilt.rotation.set(this.pitch, 0, this.roll);
    // 果凍晃動：頂端相對底部的慣性延遲 → 剪切
    const cy = Math.cos(this.root.rotation.y), sn = Math.sin(this.root.rotation.y), kx = (this.wob.x * cy - this.wob.z * sn) * 1.6, kz = (this.wob.x * sn + this.wob.z * cy) * 1.6;
    const R = this.R; this.deform.matrix.set(sx, kx, 0, 0, 0, sy, 0, -R, 0, kz, sx, 0, 0, 0, 0, 1);
    this.deform.matrixWorldNeedsUpdate = true;
  }
  updateFeet(dt, moving, sp, runF) {
    const c = this.cfg, p = this.pos, v = this.vel, fs = c.footSize;
    const stride = lerp(c.stride[0], c.stride[1], runF), duty = lerp(0.62, 0.4, runF), dirx = sp > 0.01 ? v.x / sp : 0, dirz = sp > 0.01 ? v.z / sp : 0;
    const fixed = (this.mode === 'normal' || this.mode === 'sit' || this.mode === 'sleep' || this.mode === 'dizzy') && this.grounded;
    const stompA = this.act && this.act.name === 'stomp' ? this.act.stomp : 0;
    this.feet.forEach((f, i) => {
      let pitch = 0; f.lift = 0;
      if (!fixed) {
        // 空中、被拎著、翻滾：腳用彈簧跟著身體
        const kick = this.mode === 'held' && this.modeT > 0.5 ? Math.sin(this.t * 17 + i * Math.PI) * 0.09 : 0;
        const tuck = this.mode === 'normal' ? clamp(v.y * 0.012, -0.05, 0.06) : 0;
        this.tumble.localToWorld(_a.set(f.s * c.lat * 1.1, -this.R + 0.02 - tuck + (this.mode === 'held' ? -0.05 : 0), c.footFwd + kick + (this.mode === 'normal' ? i * 0.05 - 0.02 : 0)));
        const k = 420, d = 26; f.v.x += ((_a.x - f.p.x) * k - f.v.x * d) * dt; f.v.y += ((_a.y - f.p.y) * k - f.v.y * d) * dt; f.v.z += ((_a.z - f.p.z) * k - f.v.z * d) * dt; f.p.addScaledVector(f.v, dt);
        if (this.mode !== 'held') f.p.y = Math.max(f.p.y, this.sh.uGround.value);
        f.planted = false; f.yaw = this.yaw; pitch = this.mode === 'normal' ? clamp(-v.y * 0.06, -0.5, 0.6) : 0;
        f.m.quaternion.copy(this.tumble.getWorldQuaternion(_q)); f.m.rotateX(pitch);
      } else {
        if (this.mode === 'sit' || this.mode === 'sleep') {
          this.footHome(f, _a, this.mode === 'sit' ? c.front * 0.55 + 0.1 - c.footFwd : 0.12, this.mode === 'sit' ? 1.15 : 1.4); f.p.lerp(_a, 1 - Math.exp(-dt * 12)); f.p.y = p.y; f.planted = true; f.sw = 1; f.yaw = this.yaw + f.s * 0.35; pitch = this.mode === 'sit' ? -0.5 : 0;
        } else if (this.skid) {
          this.footHome(f, _a, 0.1 + i * 0.07, 1.25); f.p.lerp(_a, 1 - Math.exp(-dt * 25)); f.p.y = p.y; f.planted = true; f.sw = 1; f.yaw = this.yaw; pitch = -0.35;
        } else if (moving) {
          const fp = (this.phase + i * 0.5) % 1, swing = fp >= duty;
          if (swing) {
            if (f.planted) { f.planted = false; f.from.copy(f.p); }
            const u = (fp - duty) / (1 - duty), rem = (1 - u) * (1 - duty) * stride / Math.max(sp, 0.2);
            this.footHome(f, _a); _a.x += dirx * (stride * duty * 0.5) + v.x * rem; _a.z += dirz * (stride * duty * 0.5) + v.z * rem;
            const e = u * u * (3 - 2 * u); f.p.lerpVectors(f.from, _a, e); f.lift = Math.sin(u * Math.PI) * (0.045 + runF * 0.07 + fs[1] * 0.3); f.p.y = p.y + f.lift; f.sw = u;
            f.yaw += angDiff(this.yaw, f.yaw) * Math.min(1, dt * 14); pitch = Math.sin(u * Math.PI * 2) * 0.5 * (0.5 + runF * 0.5);
          } else {
            if (!f.planted) { f.planted = true; f.sw = 1; if ((this.stepSnd -= 1) <= 0) { this.stepSnd = 0; this.fx.sfx('step', 0.6 + runF); } if (runF > 0.6) this.fx.spawn('dust', _b.copy(f.p).setY(p.y + 0.04), { v: _c.set(-dirx * 0.3, 0.3, -dirz * 0.3), life: 0.35, size: 0.12, grow: 2.5, drag: 3 }); f.lock = _b.copy(f.p).clone(); }
            f.p.y = p.y;
            if (f.lock) { this.stat.slip += Math.hypot(f.p.x - f.lock.x, f.p.z - f.lock.z); this.stat.slipN++; }
          }
        } else {
          // 站定：腳離家太遠就補一小步
          this.footHome(f, _a); const d = Math.hypot(_a.x - f.p.x, _a.z - f.p.z), other = this.feet[1 - i];
          const st = stompA && (i ? stompA > 0 : stompA < 0) ? Math.abs(stompA) * 0.07 : 0;
          if (f.timed > 0) { f.timed -= dt; const u = clamp(1 - f.timed / 0.15, 0, 1); f.p.lerpVectors(f.from, _a, u * u * (3 - 2 * u)); f.lift = Math.sin(u * Math.PI) * 0.04; f.p.y = p.y + f.lift; f.yaw += angDiff(this.yaw, f.yaw) * u; if (f.timed <= 0) { f.planted = true; f.p.copy(_a); } }
          else if ((!f.planted || d > 0.06 || Math.abs(angDiff(this.yaw, f.yaw)) > 0.5) && !(other.timed > 0)) { f.timed = 0.15; f.from.copy(f.p); f.planted = false; }
          else { f.p.y = p.y + st; f.lift = st; }
          f.lock = null;
        }
        f.m.rotation.set(0, 0, 0); f.m.rotation.order = 'YXZ'; f.m.rotation.y = f.yaw; f.m.rotation.x = pitch;
      }
      f.m.position.copy(f.p);
    });
  }
  updateHands(dt, HP, k, d) {
    const R = this.R, c = this.cfg;
    this.hands.forEach((h, i) => {
      // 目標：身體座標（含傾斜、翻滾與擠壓的一部分）→ 世界
      const tp = HP[i]; if (c.stick) { const k = c.stick, dx = tp.x / k[0], dy = (tp.y - k[3]) / k[1], dz = tp.z / k[2], L = Math.hypot(dx, dy, dz) || 1; tp.set(tp.x / L, k[3] + (tp.y - k[3]) / L, tp.z / L); }
      _a.set(tp.x * (1 + (1 / Math.sqrt(1 + this.sq) - 1) * 0.8), (tp.y) * (1 + this.sq * 0.8) - R, tp.z); this.tumble.localToWorld(_a);
      const n = Math.max(1, Math.ceil(dt / 0.012)), hh = dt / n;
      for (let j = 0; j < n; j++) { h.v.x += ((_a.x - h.p.x) * k - h.v.x * d) * hh; h.v.y += ((_a.y - h.p.y) * k - h.v.y * d) * hh; h.v.z += ((_a.z - h.p.z) * k - h.v.z * d) * hh; h.p.addScaledVector(h.v, hh); }
      // 手不要離身體太遠（被丟的時候）
      const cx = this.pos.x, cyy = this.pos.y + R, cz = this.pos.z, dd = Math.hypot(h.p.x - cx, h.p.y - cyy, h.p.z - cz), mx = R * 2.1; if (dd > mx) { h.p.set(cx + (h.p.x - cx) * mx / dd, cyy + (h.p.y - cyy) * mx / dd, cz + (h.p.z - cz) * mx / dd); }
      h.m.position.copy(h.p);
    });
    // 豆芽的手臂與腿：連接身體與手腳的小圓柱
    if (this.limbs.length) {
      const put = (m, ax, ay, az, to, r) => { this.deform.localToWorld(_a.set(ax, ay, az)); _b.copy(to).sub(_a); const L = _b.length(); m.position.copy(_a); m.quaternion.setFromUnitVectors(_UP, _b.divideScalar(L || 1)); m.scale.set(r, L, r); };
      this.feet.forEach((f, i) => put(this.limbs[i], f.s * this.hip[0], this.hip[1], this.hip[2], _c.copy(f.p).setY(f.p.y + c.footSize[1] * 0.9), 0.034));
      this.hands.forEach((h, i) => put(this.limbs[2 + i], h.s * this.shoulder[0], this.shoulder[1], this.shoulder[2], h.p, 0.03));
    }
  }
}
