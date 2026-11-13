// 物種圖鑑：每個物種＝一份資料（尺寸、移動方式、配色表、配件位置）＋一個組裝函式＋待機小動作＋招牌動作
// 全部原創；個體差異由 spec = { species, pal, hue, acc:[...] } 決定（見 resolveSpec）
import * as THREE from 'three';
import { softMat, blobGeo, ball, sstep, clamp, DETAIL, bumpS } from './soft.js';
import { lathe, rbox } from './world.js';
import { taperGeo, tubeGeo } from './limb.js';

const V3 = THREE.Vector3, _v = new V3();
const M = (c, o) => { if (o.face && !c.bodyO) c.bodyO = { color: o.color, top: o.top ?? o.color, y0: o.y0 ?? -0.3, y1: o.y1 ?? 0.3 }; return softMat(o, c.sh); };
const MR = (c, o) => softMat({ ...o, root: c.bodyO, rootSpan: c.cfg.rootSpan ?? 0.34 }, c.sh);   // 會與身體表面融合的材質（附屬物根部）
const put = (c, geo, mat, x = 0, y = 0, z = 0, sx = 1, sy = sx, sz = sx, parent = null) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.scale.set(sx, sy, sz); (parent || c.deform).add(m); return m; };
const piv = (c, x, y, z, o = {}) => { const g = new THREE.Group(); g.position.set(x, y, z); c.deform.add(g); c.apps.push({ piv: g, side: 0, k: 150, c: 9, g: 0.02, gy: 0, rest: [0, 0], droop: 0, ...o }); return g; };
// 從 a 到 b 的錐形肢體（根在 a、埋進身體；用會與身體融合的材質）
const UP = new V3(0, 1, 0);
const limbTo = (c, mat, a, b, r, o = {}, parent = null) => { const A = new V3(...a), d = new V3(...b).sub(A), L = d.length(), m = put(c, taperGeo({ q: 0.6, p: 1.8, cap: 0.3, ...o }), mat, A.x, A.y, A.z, r, L * 1.08, o.rz ?? r, parent); m.quaternion.setFromUnitVectors(UP, d.normalize()); return m; };
const rnd = (a, b) => a + Math.random() * (b - a);
const every = (c, key, sec, dt) => { c.tm ??= {}; c.tm[key] = (c.tm[key] ?? Math.random() * sec) - dt; if (c.tm[key] <= 0) { c.tm[key] = sec * rnd(0.7, 1.3); return true; } return false; };
const calm = (c) => c.mode === 'normal' && c.grounded && !c.act;
// 專屬待機小動作排程：站著沒事時每隔 period 秒演一次、長 dur 秒；fn(u, 結束?, 開始?)，u＝0~1
const tic = (c, key, period, dur, dt, fn) => {
  c.tc ??= {}; const s = c.tc[key] ??= { w: rnd(0.2, 0.8) * period, u: -1 };
  if (s.u < 0) { if (calm(c) && (s.w -= dt) <= 0) { s.u = 0; s.w = period * rnd(0.75, 1.3); fn(0, false, true); } }
  else { s.u += dt / dur; if (s.u >= 1 || !calm(c)) { s.u = -1; fn(1, true, false); } else fn(s.u, false, false); }
};
const rod = (c, mat, a, b, r, parent = null) => { const A = new V3(...a), B = new V3(...b), d = B.clone().sub(A), L = d.length(), m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, L, 14), mat); m.position.copy(A).addScaledVector(d, 0.5); m.quaternion.setFromUnitVectors(new V3(0, 1, 0), d.normalize()); (parent || c.deform).add(m); return m; };

// 共用預設值（單位公尺；原點在腳底、面朝 +z）
const DEF = {
  R: 0.33, walk: 1.5, run: 3.6, jumpV: 5.8, stride: [0.46, 1.0], lat: 0.12, footFwd: 0.03, footSize: [0.085, 0.06, 0.11], handR: 0.06, hand: [0.33, 0.3, 0.05],
  front: 0.33, cheek: [0.22, 0.45, 0.3], waddle: 0.06, bob: 0.03, wob: 1, mouth: [0, 0.4, 0.33], top: 0.8, move: 'walk', hopH: 0.12, floatH: 0, tintK: 1, anc: {},
};
const FACE = { ex: 88, ey: 262, rx: 34, ry: 44, my: 320, mw: 16, line: 7, eye: '#3a2622', eye2: '#6e4638', blush: '255,132,140' };

export const SPECIES = {
  // ───────── 1 糰糰：麻糬糰子（頭就是身體，圓耳朵、短尾巴）
  mochi: {
    pat: ['spots','belly','patch'],
    name: '糰糰', sub: '麻糬糰子', moveZh: '小碎步', sigZh: '彈彈跳', why: '頭就是身體，臉最大、擠壓伸展最誇張',
    R: 0.36, walk: 1.5, run: 3.5, jumpV: 5.7, stride: [0.42, 0.9], lat: 0.15, footFwd: 0.2, footSize: [0.082, 0.062, 0.1], handR: 0.062,
    stick: [0.575, 0.455, 0.53, 0.335], hand: [0.45, 0.2, 0.17], shoulder: [0.3, 0.27, 0.12], front: 0.4, cheek: [0.26, 0.3, 0.36], waddle: 0.085, wob: 1.25, mouth: [0, 0.24, 0.42], top: 0.72, faceUp: 0.14,
    face: { ...FACE, ex: 92, rx: 36, ry: 47, my: 322, mw: 17, wmouth: true },
    pals: [{ n: '奶油桃', body: 0xffc9ad, top: 0xfff1e2, acc: 0xffbfa6, sss: 0xff8f6e }, { n: '草莓牛奶', body: 0xffb4c6, top: 0xffe8ef, acc: 0xff9db6, sss: 0xff6f9a }, { n: '抹茶', body: 0xc3e0ad, top: 0xeff8de, acc: 0xa5d291, sss: 0x8fd070 }, { n: '芋頭', body: 0xcdb9f0, top: 0xf2ebff, acc: 0xb7a0ea, sss: 0x9a7bff }],
    anc: { hat: [0, 0.7, 0.02, 1], bow: [0.2, 0.66, 0.12], chest: [0, 0.1, 0.43], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.36, y1: 0.25, sss: p.sss, sssAmt: 0.27, face: c.face, headC: [0, 0, 0], span: [2.2, 2.2] });
      c.main = put(c, blobGeo(v => { const y = v.y, b = 1 + 0.15 * sstep(0.4, -0.7, y); v.set(v.x * 0.455 * b, y * (y > 0 ? 0.385 : 0.345), v.z * 0.425 * b); }), m, 0, 0.335, 0);
      const em = MR(c, { color: p.acc, top: p.acc, y0: -0.4, y1: 0.9, sss: p.sss });
      for (const s of [-1, 1]) { const g = piv(c, s * 0.25, 0.62, -0.02, { side: s, g: 0.016, gy: 0.012, rest: [0, s * -0.22], droop: 0.75 }); put(c, taperGeo({ q: 0.8, p: 2.6, cap: 0.55, bulge: 0.12 }), em, 0, -0.05, 0, 0.115, 0.2, 0.08, g); }
      const t = piv(c, 0.06, 0.2, -0.4, { k: 220, c: 10, g: 0.03, wag: true }); put(c, ball(), em, 0, 0, -0.03, 0.08, 0.08, 0.08, t);
      c.limbMat = M(c, { color: p.acc, top: p.top, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { if (calm(c) && every(c, 'ear', 3.2, dt)) for (const a of c.apps) if (a.side) a.vz += a.side * 5; },
    sig: { dur: 1.9, fn(c, u, a, P) { const b = Math.abs(Math.sin(a.t * 9)); P.yOff = b * 0.16 * (1 - u * 0.3); P.sq = 0.16 * b - 0.14 * (1 - b); P.expr = 'laugh'; P.wig = 0.5; if (c.every('sg', 0.35)) c.fx.sfx('boing'); } },
  },
  // ───────── 2 豆芽：豆子小人（有手有腳，頭頂一大一小兩片葉子）
  bean: {
    pat: ['spots','stripes','belly'],
    name: '豆芽', sub: '豆子小人', moveZh: '踩步走', sigZh: '長葉子', why: '真的會踩步的小短腿，走跑急停最有戲',
    R: 0.3, walk: 1.6, run: 3.9, jumpV: 5.9, stride: [0.5, 1.15], lat: 0.105, footFwd: 0.02, footSize: [0.075, 0.058, 0.105], handR: 0.058,
    hand: [0.35, 0.33, 0.04], front: 0.31, cheek: [0.21, 0.5, 0.28], waddle: 0.05, bob: 0.035, wob: 0.8, mouth: [0, 0.44, 0.31], top: 0.9, legs: true, tintK: 0.5, faceUp: 0.1,
    face: { ...FACE, rx: 35, ry: 45, eye: '#2f2a26', eye2: '#5a4a3c', blush: '255,140,150' },
    pals: [{ n: '薄荷', body: 0xbfe6c4, top: 0xe6f8e2, leaf: 0x6fca82, leaf2: 0xa6e6a0, shoe: 0xfff3da, leg: 0xa9dcb2, sss: 0x6fcf9a }, { n: '檸檬', body: 0xffe79a, top: 0xfff8d8, leaf: 0x86cf78, leaf2: 0xb4e8a0, shoe: 0xffffff, leg: 0xf5d67a, sss: 0xffc040 }, { n: '蜜桃', body: 0xffc4b0, top: 0xffece0, leaf: 0x86cf78, leaf2: 0xb4e8a0, shoe: 0xfff3da, leg: 0xf7ad98, sss: 0xff8060 }, { n: '晴空', body: 0xb9dcff, top: 0xe6f4ff, leaf: 0x7fd4b0, leaf2: 0xb0ecd0, shoe: 0xfff3da, leg: 0xa0c8f2, sss: 0x70a8ff }],
    anc: { hat: [-0.1, 0.83, 0.02, 0.8], bow: [0.18, 0.8, 0.1], chest: [0, 0.24, 0.3], neck: [0.3, 0.33, 0.3], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.4, y1: 0.35, sss: p.sss, sssAmt: 0.3, rim: 0xffffff, face: c.face, headC: [0, 0.07, 0], span: [2.1, 2.1] });
      c.main = put(c, blobGeo(v => { const y = v.y, rh = Math.hypot(v.x, v.z) || 1e-6, k = Math.pow(rh, 0.7) / rh, w = 1 + 0.1 * y - 0.05 * Math.exp(-Math.pow((y + 0.1) / 0.3, 2)); v.set(v.x * k * 0.335 * w, Math.sign(y) * Math.pow(Math.abs(y), 0.92) * 0.375, v.z * k * 0.305 * w); }), m, 0, 0.46, 0);
      const lm = M(c, { color: p.leaf, top: p.leaf2, y0: -1, y1: 1, sss: 0x9be070, sssAmt: 0.4 });
      const g = piv(c, 0, 0.82, 0, { k: 110, c: 6.5, g: 0.03 }); g.scale.setScalar(1.3); c.sprout = g;
      put(c, new THREE.CylinderGeometry(0.013, 0.02, 0.15, 14), lm, 0, 0.06, 0, 1, 1, 1, g);
      for (const [s, sc] of [[1, 1], [-1, 0.72]]) { const l = put(c, ball(), lm, s * 0.085 * sc, 0.135 + 0.02 * sc, 0, 0.105 * sc, 0.022, 0.06 * sc, g); l.rotation.z = s * 0.5; }
      c.limbMat = M(c, { color: p.shoe, top: 0xffffff, y0: 0, y1: 1.6, sss: 0xffb070 }); c.legMat = M(c, { color: p.leg, top: p.body, y0: -1, y1: 1, sss: p.sss });
      c.hip = [0.1, 0.17, 0]; c.shoulder = [0.28, 0.4, 0.02];
      put(c, ball(), M(c, { color: p.top, top: 0xffffff, y0: -1, y1: 2, sss: p.sss, sssAmt: 0.2 }), 0, 0.235, 0.268, 0.13, 0.1, 0.03);
      for (const y of [0.275, 0.215]) put(c, ball(), lm, 0, y, 0.298 + (y - 0.215) * 0.1, 0.02, 0.02, 0.012);
    },
    idle(c, dt, t) { tic(c, 'grow', 6, 1.6, dt, (u, end) => { c.sproutBig = !end && u > 0.15 && u < 0.8; }); c.sprout.scale.setScalar(c.sprout.scale.x + ((c.sproutBig ? 2.1 : 1.3) - c.sprout.scale.x) * Math.min(1, dt * 8)); c.sproutBig = false; },
    sig: { dur: 2.0, fn(c, u, a, P) { c.sproutBig = u > 0.2 && u < 0.85; P.sq = u < 0.2 ? -0.2 * u / 0.2 : 0.1 * (1 - u); P.expr = u < 0.2 ? 'effort' : 'happy'; P.hands = [1.25, 0.25]; if (u > 0.2 && !a.f) { a.f = 1; c.fx.sfx('boing'); c.fx.burst('spark', c.headTop(new V3()).add(_v.set(0, 0.2, 0)), 6, { speed: 0.9, up: 0.6, life: 0.5, size: 0.12 }); } } },
  },
  // ───────── 3 啵啵：圓頭小機器人（發光的臉、彈簧天線、浮空的手）
  robo: {
    name: '啵啵', sub: '映像管小機器人', moveZh: '滾輪滑行', sigZh: '掃描', why: '橫向圓角的映像管頭、側邊問號天線、波紋管脖子與手臂；螢幕眼睛是暖色橫槓，不是白球機器人', memo: '橫長圓角頭＋側邊問號天線',
    R: 0.33, move: 'slide', footSize: null, walk: 1.4, run: 3.3, lat: 0.115, handR: 0.062, hand: [0.37, 0.27, 0.05], shoulder: [0.2, 0.34, 0.03], armRip: 0.2, wrist: 0.7, armFlare: 1.5, armLf: 0.7,
    handGeo: () => { const g = new THREE.TorusGeometry(1, 0.36, 10, 24, 4.75); g.rotateZ(-0.82); return g; },
    front: 0.34, cheek: [0.24, 0.45, 0.3], wob: 0.6, mouth: [0, 0.68, 0.3], top: 1.0,
    face: { kind: 'screen', ex: 92, ey: 262, rx: 30, ry: 21, my: 318, mw: 14, line: 6, glow: '#ffd66b', blush: '255,143,107', blushAmt: 0.8, visor: { w: 440, h: 252, y: 146, r: 96, c0: '#3a4466', c1: '#4c5890' } },
    pals: [{ n: '薄荷青', body: 0x7fd6c4, top: 0xc9f2e8, joint: 0xf4f1ea, tip: 0xff8f6b, glow: '#ffd66b' }, { n: '奶油黃', body: 0xffd166, top: 0xffefb8, joint: 0xf4f1ea, tip: 0xff8f6b, glow: '#ffe8a0' }, { n: '莓粉', body: 0xf58aa8, top: 0xffd0dc, joint: 0xf4f1ea, tip: 0xffd166, glow: '#ffe2a0' }, { n: '薰衣草', body: 0xa99cf0, top: 0xddd6ff, joint: 0xf4f1ea, tip: 0xffd166, glow: '#ffe8a0' }],
    anc: { hat: [0.1, 0.95, 0.04, 0.8], bow: [-0.25, 0.9, 0.1], chest: [0, 0.27, 0.22], neck: [0.2, 0.42, 0.13], glasses: 0 },
    build(c, p) {
      c.face.st.glow = p.glow;
      const sh = { color: p.body, top: p.top, sss: p.body, sssAmt: 0.2, rim: 0xffffff, rimAmt: 0.25, rough: 0.42 };
      // 頭：橫向圓角方（映像管電視），寬高比約 1.3
      const nn = 3.6, sq = (v, hx, hy, hz) => { const f = 1 / Math.pow(Math.pow(Math.abs(v.x), nn) + Math.pow(Math.abs(v.y), nn) + Math.pow(Math.abs(v.z), nn), 1 / nn); v.set(v.x * f * hx, v.y * f * hy, v.z * f * hz); };
      c.main = put(c, blobGeo(v => sq(v, 0.37, 0.27, 0.29), 72, 56), M(c, { ...sh, y0: -0.3, y1: 0.28, face: c.face, headC: [0, 0, 0], span: [2.5, 2.4], glow: 0.7 }), 0, 0.71, 0);
      // 身體：上窄下寬的小鐘形
      put(c, lathe([[0, 0.07], [0.21, 0.075], [0.28, 0.13], [0.255, 0.27], [0.17, 0.37], [0.11, 0.395], [0, 0.395]], 40, 40), M(c, { ...sh, y0: 0.05, y1: 0.4 }), 0, 0, 0);
      const jm = M(c, { color: p.joint, top: 0xffffff, y0: 0.2, y1: 0.5, sss: 0xbfd0ff, sssAmt: 0.12, rough: 0.55 });
      // 脖子：波紋管 3 節（直徑約頭寬 22%）
      { const pts = []; for (let i = 0; i <= 30; i++) { const y = 0.37 + i / 30 * 0.12; pts.push(new THREE.Vector2(0.075 + 0.016 * Math.cos(i / 30 * 3 * 6.2832 + Math.PI) , y)); } put(c, new THREE.LatheGeometry(pts, Math.max(16, Math.round(26 * DETAIL.k))), jm, 0, 0, 0); put(c, new THREE.CylinderGeometry(0.07, 0.07, 0.1, 14), jm, 0, 0.43, 0); }
      // 輪罩：兩個半球嵌在身體底部（不露腿，靠滾輪滑行）
      for (const sd of [-1, 1]) { put(c, ball(), jm, sd * 0.18, 0.075, 0.015, 0.115, 0.08, 0.145); put(c, ball(), M(c, { color: 0x4a4f66, top: 0x5a607a, y0: -1, y1: 1, rough: 0.7 }), sd * 0.18, 0.072, 0.105, 0.05, 0.05, 0.03); }
      // 耳朵：左邊旋鈕、右邊喇叭網孔
      const tp = M(c, { color: p.tip, top: 0xffffff, y0: -1, y1: 2.5, sss: p.tip, sssAmt: 0.35, rough: 0.4 }); c.tipMat = tp;
      { const k = put(c, new THREE.CylinderGeometry(0.075, 0.085, 0.07, 22), jm, -0.37, 0.71, 0, 1, 1, 1); k.rotation.z = Math.PI / 2; const kk = put(c, new THREE.CylinderGeometry(0.05, 0.05, 0.03, 18), tp, -0.41, 0.71, 0, 1, 1, 1); kk.rotation.z = Math.PI / 2; put(c, ball(), jm, -0.425, 0.74, 0, 0.012);
        const sp = put(c, new THREE.CylinderGeometry(0.085, 0.09, 0.06, 22), jm, 0.37, 0.71, 0); sp.rotation.z = Math.PI / 2; const dk = M(c, { color: 0x4a4f66, top: 0x4a4f66, y0: -1, y1: 1, rough: 0.7 });
        for (const [y, z] of [[0, 0], [0.035, 0], [-0.035, 0], [0, 0.035], [0, -0.035]]) put(c, ball(), dk, 0.402, 0.71 + y, z, 0.011, 0.011, 0.011); }
      // 天線：側邊彎成問號形，尖端小球
      const g = piv(c, 0.2, 0.955, 0, { k: 95, c: 5, g: 0.035 }); c.ant = c.apps[c.apps.length - 1];
      put(c, tubeGeo({ key: 'roboant', path: (u) => { if (u < 0.5) return [0, 0.15 * u / 0.5, 0]; const ph = (u - 0.5) / 0.5 * Math.PI * 1.2; return [-0.05 * Math.sin(ph) * 1.0, 0.15 + 0.05 * (1 - Math.cos(ph)), 0]; }, rad: () => 0.013, flare: 1.7, fl: 0.12, cap: 0.05, N: 24, S: 10 }), jm, 0, 0, 0, 1, 1, 1, g);
      put(c, ball(), tp, -0.012, 0.21, 0, 0.034, 0.034, 0.034, g);
      c.limbMat = jm;
    },
    idle(c, dt, t) { c.tipMat.userData.U.uSssAmt.value = 0.35 + 0.35 * Math.pow(Math.max(0, Math.sin(t * 2.2)), 6) + (c.scan ? 0.9 : 0); c.scan = false; if (c.face.scan >= 0 && !c.scanOn) { c.face.scan = -1; c.face.dirty = true; } c.scanOn = false; },
    sig: { dur: 2.2, fn(c, u, a, P) { c.scan = true; c.scanOn = true; c.face.scan = u < 0.92 ? (u * 2.2) % 1 : -1; if (u >= 0.92) c.face.dirty = true; c.ant.vz += Math.sin(a.t * 18) * 0.5; P.yaw = Math.sin(u * Math.PI * 2) * 0.9; P.expr = 'look'; P.sq = 0.06; P.hands = [1.2, 0.1]; if (c.every('sg', 0.3)) c.fx.sfx('ui'); if (u > 0.9 && !a.f) { a.f = 1; c.say('掃描完成！', 1.4); c.emote('happy', 1.4); } } },
  },
  // ───────── 4 綿綿：雲朵（好幾顆圓球堆成一團，飄在半空，會下小雨）
  cloud: {
    name: '綿綿', sub: '小雲朵', moveZh: '飄浮', sigZh: '下小雨', why: '不對稱的蓬蓬輪廓，飄來飄去、難過會下雨',
    R: 0.34, move: 'float', floatH: 0.24, footSize: null, handR: 0, top: 0.82, wob: 1.3, mouth: [0, 0.27, 0.34], front: 0.34, faceUp: 0.05, walk: 1.4, run: 3.3,
    face: { ...FACE, ex: 84, ey: 258, rx: 31, ry: 40, my: 312, mw: 15, eye: '#34405e', eye2: '#5a6a92', blush: '255,150,170' },
    pals: [{ n: '棉花白', body: 0xcfe0fb, top: 0xffffff, sss: 0x9fc0ff }, { n: '夕陽粉', body: 0xffc8cf, top: 0xfff3ee, sss: 0xff90a0 }, { n: '薄荷', body: 0xc4ecdc, top: 0xfafffb, sss: 0x80d8b0 }, { n: '雨雲灰', body: 0xb9c0d6, top: 0xeef0f8, sss: 0x8090c0 }],
    anc: { hat: [0.13, 0.78, -0.02, 0.85], bow: [-0.24, 0.62, 0.1], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.24, rim: 0xffffff, rimAmt: 0.4, rough: 0.8 };
      c.main = put(c, blobGeo(v => v.set(v.x * 0.43, v.y * 0.265, v.z * 0.33)), M(c, { ...o, y0: -0.25, y1: 0.15, face: c.face, headC: [0, 0, 0], span: [2.0, 2.2] }), 0, 0.3, 0);
      const pm = M(c, { ...o, y0: -1, y1: 0.4 });
      for (const [x, y, z, r] of [[-0.21, 0.47, -0.03, 0.2], [0.13, 0.55, -0.05, 0.25], [0.37, 0.35, -0.03, 0.17], [-0.41, 0.31, -0.01, 0.15], [0.02, 0.36, -0.2, 0.27], [-0.1, 0.2, -0.12, 0.2], [0.24, 0.21, -0.08, 0.17]]) put(c, ball(), pm, x, y, z, r);
    },
    idle(c, dt, t) {
      const sad = c.emo && c.emo.name === 'sad', n = c.rain ? 0.05 : sad ? 0.12 : 2.6; c.rain = false;
      if (c.mode !== 'held' && c.mode !== 'tumble' && every(c, 'rain', n, dt)) c.fx.spawn('drop', _v.set(c.pos.x + rnd(-0.3, 0.3), c.pos.y + c.yOff + 0.1, c.pos.z + rnd(-0.15, 0.2)).clone(), { v: new V3(0, -0.4, 0), g: 6, life: Math.max(0.15, Math.sqrt(2 * (c.yOff + 0.1) / 6)), size: 0.07, fadeIn: 0.03 });
    },
    sig: { dur: 2.2, fn(c, u, a, P) { c.rain = u > 0.15; P.tint = [0.62, 0.68, 0.82]; P.tintA = 0.55; P.sq = -0.08 + Math.sin(a.t * 30) * 0.03; P.yOff = 0.12; P.expr = u < 0.8 ? 'effort' : 'happy'; if (c.every('sg', 0.5)) c.fx.sfx('skid'); } },
  },
  // ───────── 5 小燭：火苗（水滴形、尖端歪一邊，一直在晃，會冒火星）
  flame: {
    name: '小燭', sub: '小火苗', moveZh: '彈跳', sigZh: '燒旺', why: '歪歪的尖頂、會發光、一直在搖曳',
    R: 0.3, move: 'hop', hopH: 0.15, footSize: null, handR: 0.05, hand: [0.3, 0.2, 0.1], stick: [0.33, 0.3, 0.31, 0.26], top: 0.86, wob: 1.7, mouth: [0, 0.2, 0.33], front: 0.33, cheek: [0.2, 0.26, 0.3], tintK: 0.4, faceUp: 0.12,
    face: { ...FACE, ex: 84, ey: 256, rx: 33, ry: 43, my: 314, mw: 15, eye: '#5a2414', eye2: '#8a4020', blush: '255,110,90' },
    pals: [{ n: '橘焰', body: 0xff8a4a, top: 0xffe680, sss: 0xffa030 }, { n: '藍焰', body: 0x6fa8ff, top: 0xd8f2ff, sss: 0x60a0ff }, { n: '櫻焰', body: 0xff8fb0, top: 0xffe0d0, sss: 0xff70a0 }, { n: '青焰', body: 0x5fd0c0, top: 0xe0fff0, sss: 0x40d0b0 }],
    anc: { bow: [-0.16, 0.5, 0.14], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.2, y1: 0.42, sss: p.sss, sssAmt: 0.7, rim: p.top, rimAmt: 0.45, rough: 0.5, face: c.face, headC: [0, -0.04, 0], span: [2.1, 2.1] }); c.glowU = m.userData.U.uSssAmt;
      c.main = put(c, blobGeo(v => { const y = v.y, t = sstep(-0.15, 1, y), r = 0.34 * (1 - 0.82 * t * t) * (1 + 0.1 * sstep(0.2, -0.8, y)); v.set(v.x * r + 0.13 * t * t * t, y < 0 ? y * 0.3 : y * 0.56, v.z * r * 0.93); }), m, 0, 0.3, 0);
      c.limbMat = M(c, { color: p.body, top: p.top, y0: -1, y1: 1.5, sss: p.sss, sssAmt: 0.7 });
    },
    idle(c, dt, t) {
      c.wobV.x += (Math.sin(t * 7.3) + Math.sin(t * 11.7)) * 2.2 * dt; c.wobV.z += Math.sin(t * 9.1) * 1.6 * dt;
      const e = c.emo && c.emo.name; c.glowU.value += (((c.flare ? 1.3 : e === 'sad' || c.mode === 'sleep' ? 0.3 : 0.7) + Math.sin(t * 13) * 0.06) - c.glowU.value) * Math.min(1, dt * 6); c.flare = false;
      if (c.mode !== 'sleep' && every(c, 'spk', 0.7, dt)) c.fx.spawn('spark', c.headTop(new V3()).add(_v.set(rnd(-0.1, 0.15), -0.05, 0)), { v: new V3(rnd(-0.2, 0.2), 0.6, 0), life: 0.7, size: 0.07, sway: 0.5 });
    },
    sig: { dur: 1.8, fn(c, u, a, P) { const b = sstep(0, 0.25, u) * (1 - sstep(0.75, 1, u)); c.flare = true; P.sq = 0.34 * b - 0.2 * sstep(0, 0.12, u) * (1 - sstep(0.12, 0.25, u)); P.expr = 'effort'; P.hands = [1.2, 0.28]; if (c.every('sg', 0.08)) c.fx.spawn('spark', c.headTop(new V3()), { v: new V3(rnd(-0.8, 0.8), rnd(0.8, 1.8), rnd(-0.5, 0.5)), g: 2, life: 0.6, size: 0.1 }); if (!a.f) { a.f = 1; c.fx.sfx('whee'); } } },
  },
  // ───────── 6 刺刺：盆栽仙人掌（一高一低兩隻手臂、頭頂偏一邊的小花，連盆一起跳）
  cactus: {
    pat: ['spots'],
    name: '刺刺', sub: '圓球仙人掌盆栽', moveZh: '連盆跳', sigZh: '開花', why: '圓球身體＋一大一小兩顆側芽＋頭頂小花，整盆一起跳',
    R: 0.3, move: 'hop', hopH: 0.09, footSize: null, handR: 0, top: 0.9, wob: 0.75, mouth: [0, 0.5, 0.27], front: 0.28, tintK: 0.45, faceUp: 0.06, walk: 1.3, run: 3.1,
    face: { ...FACE, ex: 62, ey: 262, rx: 26, ry: 34, my: 308, mw: 13, line: 6, eye: '#27352b', eye2: '#47604c', blush: '255,140,150' },
    pals: [{ n: '陶盆', body: 0x86cf96, top: 0xbdecb4, pot: 0xee9f7c, pot2: 0xf9c4a4, fl: 0xff9fb5, sss: 0x50c070 }, { n: '白盆', body: 0x7fd0b8, top: 0xbff0dc, pot: 0xf2ece4, pot2: 0xffffff, fl: 0xffd27a, sss: 0x40c0a0 }, { n: '粉盆', body: 0xa8d880, top: 0xd8f2b0, pot: 0xffb7c5, pot2: 0xffdbe2, fl: 0xffffff, sss: 0x80c040 }, { n: '藍盆', body: 0x8fc8a8, top: 0xc8ecd0, pot: 0x9db8f0, pot2: 0xc6d6ff, fl: 0xffb38a, sss: 0x50b080 }],
    anc: { hat: [-0.09, 0.8, 0.02, 0.8], bow: [-0.15, 0.76, 0.12], neck: [0.31, 0.27, 0.26], glasses: 1 },
    build(c, p) {
      put(c, lathe([[0, 0], [0.17, 0], [0.19, 0.02], [0.235, 0.2], [0.255, 0.235], [0.255, 0.275], [0.2, 0.28], [0, 0.27]], 48), M(c, { color: p.pot, top: p.pot2, y0: 0, y1: 0.3, sss: p.pot, sssAmt: 0.2, rough: 0.8 }));
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.3 };
      c.main = put(c, blobGeo(v => { const y = v.y, th = Math.atan2(v.z, v.x), rib = 1 + 0.04 * Math.cos(th * 10) * (1 - y * y); v.set(v.x * 0.27 * rib, y * (y > 0 ? 0.29 : 0.25), v.z * 0.26 * rib); }), M(c, { ...o, y0: -0.25, y1: 0.29, face: c.face, headC: [0, 0.02, 0], span: [2.4, 2.4] }), 0, 0.53, 0);
      const am = M(c, { ...o, y0: -1, y1: 1.2 });
      for (const [s, y, sc] of [[-1, 0.5, 1], [1, 0.68, 0.72]]) { const g = piv(c, s * 0.22, y, 0, { side: s, k: 190, c: 9, g: 0.012, gy: 0.006, rest: [0, 0], droop: 0.35 }); put(c, ball(), am, s * 0.07 * sc, 0.02, 0, 0.115 * sc, 0.105 * sc, 0.105 * sc, g); put(c, ball(), M(c, { color: p.fl, top: 0xffffff, sss: p.fl, sssAmt: 0.4 }), s * 0.1 * sc, 0.12 * sc, 0.02, 0.03 * sc, 0.022 * sc, 0.03 * sc, g); }
      const f = piv(c, 0.07, 0.83, 0, { k: 160, c: 7, g: 0.02 }); c.flower = f; const fm = M(c, { color: p.fl, top: 0xffffff, y0: -1, y1: 2, sss: p.fl, sssAmt: 0.4 });
      for (let i = 0; i < 5; i++) { const a = i * 1.2566; put(c, ball(), fm, Math.cos(a) * 0.05, 0.02, Math.sin(a) * 0.05, 0.046, 0.024, 0.046, f); }
      put(c, ball(), M(c, { color: 0xffd86a, sss: 0xffa020 }), 0, 0.032, 0, 0.032, 0.026, 0.032, f);
      const sm = M(c, { color: 0xfffdf2, sss: 0xffffff, sssAmt: 0.5 });
      for (let i = 0; i < 14; i++) { const a = i * 2.39996 + 0.6, y = -0.7 + (i / 13) * 1.4, r = Math.sqrt(Math.max(0, 1 - y * y)); if (Math.cos(a - Math.PI / 2) > 0.4 && Math.abs(y) < 0.55) continue; put(c, ball(), sm, Math.cos(a) * 0.272 * r, 0.53 + y * (y > 0 ? 0.29 : 0.25), Math.sin(a) * 0.262 * r, 0.018); }
    },
    idle(c, dt, t) { if (calm(c) && every(c, 'shv', 4.5, dt)) c.shv = 0.45; if (c.shv > 0) { c.shv -= dt; c.wobV.x += Math.sin(t * 60) * 9 * dt; } const s = c.flower.scale.x + ((c.bloom ? 2.4 : 1) - c.flower.scale.x) * Math.min(1, dt * 9); c.flower.scale.setScalar(s); c.bloom = false; },
    sig: { dur: 2.2, fn(c, u, a, P) { c.bloom = u > 0.25 && u < 0.9; P.sq = u < 0.25 ? -0.18 * (u / 0.25) : 0.08 * (1 - u); P.expr = u < 0.25 ? 'effort' : 'happy'; if (u > 0.25 && !a.f) { a.f = 1; c.fx.sfx('heart'); c.fx.burst('spark', c.headTop(new V3()), 7, { speed: 0.8, up: 0.5, life: 0.6, size: 0.11 }); } } },
  },
  // ───────── 7 拿鐵：咖啡杯（單邊把手、杯裡的咖啡會晃、會冒蒸氣）
  mug: {
    name: '拿鐵', sub: '咖啡杯', moveZh: '搖擺走', sigZh: '乾杯', why: '辦公室味最重；單邊把手讓輪廓不對稱',
    R: 0.31, stride: [0.36, 0.8], lat: 0.12, footFwd: 0.02, footSize: [0.08, 0.055, 0.1], handR: 0.055, hand: [0.34, 0.24, 0.07], front: 0.3, cheek: [0.2, 0.33, 0.28], waddle: 0.11, wob: 0.45, mouth: [0, 0.27, 0.3], top: 0.64, walk: 1.4, run: 3.3,
    face: { ...FACE, ex: 80, ey: 258, rx: 31, ry: 40, my: 312, mw: 15, eye: '#4a3024', eye2: '#7a5040' },
    pals: [{ n: '奶白', body: 0xfff0e2, top: 0xffffff, cof: 0xb9855a, acc: 0xffb7a0, sss: 0xffb080 }, { n: '櫻粉', body: 0xffbccb, top: 0xffe6ec, cof: 0xc99a70, acc: 0xffffff, sss: 0xff7fa0 }, { n: '晴藍', body: 0xb4d4ff, top: 0xe4f1ff, cof: 0xb9855a, acc: 0xffffff, sss: 0x70a0ff }, { n: '奶黃', body: 0xffe08a, top: 0xfff4c8, cof: 0x9a6a48, acc: 0xffffff, sss: 0xffb030 }],
    anc: { bow: [-0.2, 0.6, 0.14], chest: [0, 0.13, 0.275], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.22, rough: 0.35 };
      c.main = put(c, lathe([[0, 0.06], [0.2, 0.06], [0.262, 0.105], [0.285, 0.25], [0.292, 0.52], [0.283, 0.56], [0.258, 0.56], [0.25, 0.52], [0, 0.515]], 72, 64), M(c, { ...o, y0: 0.05, y1: 0.55, face: c.face, headC: [0, 0.31, 0], span: [2.15, 2.15] }));
      const hd = put(c, new THREE.TorusGeometry(0.105, 0.036, 18, 40, Math.PI * 1.16), M(c, { ...o, y0: -0.1, y1: 0.1 }), 0.275, 0.31, 0); hd.rotation.z = -Math.PI * 0.58;
      const g = piv(c, 0, 0.525, 0, { k: 60, c: 3.2, g: 0.02 }); c.slosh = g;
      put(c, new THREE.CylinderGeometry(0.25, 0.25, 0.012, 48), M(c, { color: p.cof, top: p.cof, sss: 0x703010, sssAmt: 0.3, rough: 0.25 }), 0, 0, 0, 1, 1, 1, g);
      const fm = M(c, { color: 0xfff3e0, sss: 0xffd0a0, rough: 0.5 }); for (const s of [-1, 1]) put(c, ball(), fm, s * 0.04, 0.008, -0.02, 0.06, 0.008, 0.075, g).rotation.y = s * 0.5;
      c.limbMat = M(c, { color: p.acc, top: 0xffffff, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { if (c.mode !== 'held' && c.mode !== 'tumble' && every(c, 'stm', c.cheer ? 0.12 : 0.55, dt)) c.fx.spawn(c.cheer ? 'heart' : 'dust', c.headTop(new V3()).add(_v.set(rnd(-0.1, 0.1), -0.02, 0)), { v: new V3(rnd(-0.05, 0.05), 0.35, 0), life: 1.3, size: c.cheer ? 0.12 : 0.1, grow: 0.9, sway: 0.35 }); c.cheer = false; },
    sig: { dur: 1.9, fn(c, u, a, P) { const b = sstep(0, 0.2, u) * (1 - sstep(0.8, 1, u)); c.cheer = b > 0.5; P.yOff = Math.abs(Math.sin(a.t * 6)) * 0.1 * b; P.pitch = -0.22 * b; P.expr = 'happy'; P.hands = [1.15, 0.32 * b]; if (!a.f) { a.f = 1; c.say('乾杯！', 1.4); c.fx.sfx('heart'); } } },
  },
  // ───────── 8 飄飄：小幽靈（圓頂＋波浪裙擺，飄在半空）
  ghost: {
    pat: ['spots','stripes'],
    name: '飄飄', sub: '小幽靈', moveZh: '飄浮', sigZh: '嚇你一跳', why: '波浪裙擺的剪影，飄的時候裙擺會甩',
    R: 0.31, move: 'float', floatH: 0.17, footSize: null, handR: 0.062, hand: [0.33, 0.3, 0.12], stick: [0.33, 0.4, 0.31, 0.32], top: 0.74, wob: 1.6, mouth: [0, 0.3, 0.31], front: 0.31, cheek: [0.2, 0.36, 0.28], faceUp: 0.1, walk: 1.5, run: 3.5,
    face: { ...FACE, ex: 78, ey: 260, rx: 31, ry: 42, my: 316, mw: 14, eye: '#353058', eye2: '#5c5490', blush: '255,150,190' },
    pals: [{ n: '牛奶白', body: 0xd2cdfc, top: 0xffffff, sss: 0xb0a0ff }, { n: '薄荷', body: 0xbdeadb, top: 0xfbfffd, sss: 0x70d8b0 }, { n: '蜜桃', body: 0xffcabd, top: 0xfff6f0, sss: 0xff9080 }, { n: '夜藍', body: 0x8f9ae6, top: 0xd9defc, sss: 0x6070ff }],
    anc: { hat: [0, 0.7, 0.02, 0.95], bow: [0.17, 0.68, 0.1], neck: [0.2, 0.345, 0.325], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.3, rim: 0xffffff, rimAmt: 0.42 };
      c.main = put(c, blobGeo(v => { const y = v.y, th = Math.atan2(v.z, v.x), hem = sstep(-0.05, -0.7, y), wv = Math.sin(th * 6 + 0.5), r = 0.3 * (1 + 0.24 * hem) * (1 + 0.16 * wv * hem * hem), yy = Math.max(y, -0.74 + 0.16 * (0.5 + 0.5 * wv)), rh = Math.hypot(v.x, v.z) || 1e-6, kk = y < -0.74 ? Math.sqrt(1 - 0.74 * 0.74) / rh * (rh / Math.sqrt(1 - 0.74 * 0.74)) : 1; v.set(v.x * r * kk, yy * (yy > 0 ? 0.4 : 0.37), v.z * r * 0.95 * kk); }, 96, 64), M(c, { ...o, y0: -0.28, y1: 0.2, face: c.face, headC: [0, 0.04, 0], span: [2.15, 2.15] }), 0, 0.33, 0);
      const t = piv(c, 0.05, 0.12, -0.27, { k: 70, c: 4, g: 0.05, wag: true }); put(c, ball(), M(c, { ...o, y0: -1, y1: 1 }), 0, -0.02, -0.05, 0.07, 0.06, 0.09, t);
      const tf = piv(c, 0.04, 0.72, -0.02, { k: 90, c: 4.5, g: 0.04, rest: [0, -0.5] }); put(c, blobGeo(v => { const u = (v.y + 1) / 2; v.set(v.x * 0.045 * (1 - 0.6 * u) + 0.05 * u * u, v.y * 0.07 + 0.05, v.z * 0.04 * (1 - 0.6 * u)); }, 24, 20), M(c, { ...o, y0: -0.1, y1: 0.1 }), 0, 0, 0, 1, 1, 1, tf);
      c.limbMat = M(c, { ...o, y0: -1, y1: 0.5 });
    },
    idle(c, dt, t) { c.wobV.x += Math.sin(t * 1.9) * 0.9 * dt; tic(c, 'twirl', 9, 2.2, dt, (u, end, st) => { c.idleYaw = end ? 0 : sstep(0.1, 0.9, u) * Math.PI * 2; c.idleY = end ? 0 : Math.sin(u * Math.PI) * 0.12; if (!end) c.wobV.z += Math.sin(u * 20) * 0.4 * dt * 10; }); },
    sig: { dur: 1.9, fn(c, u, a, P) { if (u < 0.45) { P.sq = -0.42 * sstep(0, 0.3, u); P.yOff = -c.cfg.floatH * sstep(0, 0.3, u); P.expr = 'smug'; P.hands = [0.6, -0.1]; } else { P.sq = 0.3 * (1 - sstep(0.5, 1, u)); P.yOff = 0.2 * (1 - sstep(0.5, 1, u)); P.expr = 'laugh'; P.hands = [1.4, 0.3]; if (!a.f) { a.f = 1; c.say('哇！', 1.1); c.fx.sfx('boing'); c.sqV += 6; } } } },
  },
  // ───────── 9 啾啾：圓鳥（蛋形身體、小尖嘴、頭頂三根毛、左右搖擺走）
  bird: {
    pat: ['spots','belly','stripes'],
    name: '啾啾', sub: '水滴小鳥', moveZh: '左右搖擺', sigZh: '拍翅膀', why: '側面是橫放上翹的水滴，往後甩的三片冠羽、扇形尾羽、三趾腳掌', memo: '冠羽＋扇形尾羽',
    R: 0.31, walk: 1.35, run: 3.3, stride: [0.3, 0.72], lat: 0.1, footFwd: 0.07, footSize: [0.075, 0.032, 0.105], footGeo: 'web', hip: [0.1, 0.17, 0.02], handR: 0.05, handScale: [0.05, 0.17, 0.115], hand: [0.36, 0.4, -0.07], shoulder: [0.27, 0.46, 0.02], front: 0.3, cheek: [0.2, 0.44, 0.28], waddle: 0.17, bob: 0.03, wob: 0.8, mouth: [0, 0.4, 0.4], top: 0.86, faceUp: 0.1,
    face: { ...FACE, ex: 80, ey: 244, rx: 35, ry: 45, my: 300, mw: 0, noMouth: true, eye: '#2a2a36', eye2: '#4a4a66', belly: 1, heart: 1 },
    pals: [{ n: '青綠', body: 0x4fc3b0, top: 0x9fe8d8, belly: '#fff6e0', beak: 0xff9a4d, crest: 0xffd35a, sss: 0x20b098 }, { n: '天空藍', body: 0x6fb1ff, top: 0xb4d6ff, belly: '#fff6e0', beak: 0xff9a4d, crest: 0xffd35a, sss: 0x4a90ff }, { n: '櫻花粉', body: 0xffb0c4, top: 0xffe2ea, belly: '#fff6f0', beak: 0xffc060, sss: 0xff6f9a }, { n: '企鵝灰', body: 0x8c9cb8, top: 0xb8c6dc, belly: '#ffffff', beak: 0xffb45a, sss: 0x6070a0 }],
    anc: { hat: [0, 0.8, 0.03, 0.85], bow: [0.17, 0.78, 0.1], chest: [0, 0.24, 0.3], neck: [0.3, 0.34, 0.32], glasses: 1 },
    build(c, p) {
      c.face.st.bellyCol = p.belly; const cr = p.crest ?? 0xffd35a;
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.26 };
      // 側面是橫放、後端上翹的水滴：胸口往前鼓，屁股往後上方收
      const BB = [[0, -0.3, 1, 0.05, 0.6], [0, -0.7, 0.5, 0.025, 0.5], [0.8, -0.35, 0.3, 0.025, 0.4], [-0.8, -0.35, 0.3, 0.025, 0.4]];
      c.main = put(c, blobGeo(v => { const bs = bumpS(v, BB), dx = v.x, dy = v.y, dz = v.z, y = dy, b = 1 + 0.14 * sstep(0.5, -0.6, y); v.set(dx * 0.35 * b, y * (y > 0 ? 0.42 : 0.37) + 0.075 * sstep(0.1, -1, dz) * sstep(-0.6, 0.5, dy), dz * 0.295 * b - 0.02 * sstep(0, -1, dz)); v.x += dx * bs; v.y += dy * bs; v.z += dz * bs; }, 88, 64), M(c, { ...o, y0: -0.3, y1: 0.3, face: c.face, headC: [0, 0.03, 0], span: [2.3, 2.3] }), 0, 0.42, 0);
      // 嘴：寬扁的圓角三角（位置在兩眼連線下方）
      const bk = M(c, { color: p.beak, top: 0xffd890, y0: -0.05, y1: 0.05, sss: 0xff7020, sssAmt: 0.35, rough: 0.4 });
      c.beak = put(c, blobGeo(v => { const t = (v.z + 1) / 2; v.set(v.x * 0.085 * (1 - 0.55 * t * t), v.y * 0.04 * (1 - 0.3 * t), v.z * 0.065); }, 32, 24), bk, 0, 0.395, 0.325);
      // 冠羽：往後甩的大中小三片
      const cm = softMat({ color: cr, top: cr, sss: cr, sssAmt: 0.3, rough: 0.5, y0: -1, y1: 1 }, c.sh), tm = MR(c, { ...o, y0: -1, y1: 1 });
      const tm2 = softMat({ ...o, color: p.body, top: p.body, y0: -1, y1: 1, rough: 0.55 }, c.sh), g = piv(c, 0, 0.84, -0.04, { k: 120, c: 6, g: 0.03 });
      [[0, 0.27, 0.065, -0.6, 0], [0.065, 0.2, 0.056, -1.0, 0.6], [-0.065, 0.15, 0.05, -0.9, -0.6]].forEach(([x, L, r0, rx, rz]) => { const f = put(c, taperGeo({ q: 0.4, p: 1.1, cap: 0.4, flare: 1.4, fl: 0.2 }), cm, x, -0.02, -0.01, r0, L, r0 * 0.4, g); f.rotation.set(rx, 0, rz); });
      // 尾羽：三片扇形上翹，從屁股兩側都看得到
      const t = piv(c, 0, 0.44, -0.25, { k: 200, c: 9, g: 0.03, wag: true }); c.tailG = t;
      [[0, -0.9, 0.3], [-0.6, -0.8, 0.25], [0.6, -0.8, 0.25]].forEach(([rz, rx, L]) => { const f = put(c, taperGeo({ q: 0.55, p: 1.1, cap: 0.35, flare: 1.35, fl: 0.2 }), tm2, 0, 0, -0.03, 0.065, L, 0.022, t); f.rotation.set(rx - 0.0, 0, rz); });
      c.limbMat = tm; c.footMat = bk;
    },
    idle(c, dt, t) { c.beak.scale.y = 1 + Math.min(1, Math.max(0, c.face.cur.mOpen + c.face.talk)) * 0.55; if (calm(c) && every(c, 'tilt', 3.6, dt)) { c.tiltT = 0.9; c.tiltS = Math.random() < 0.5 ? -1 : 1; if (Math.random() < 0.5) { c.fx.sfx('squeak'); c.fx.spawn('note', c.headTop(new V3()).add(_v.set(0.2, 0, 0.1)), { v: new V3(0.2, 0.5, 0), life: 0.9, size: 0.14, sway: 0.5 }); } } if (c.tiltT > 0) { c.tiltT -= dt; c.rollAdd = c.tiltS * 0.26 * sstep(0, 0.15, 0.9 - c.tiltT) * sstep(0, 0.15, c.tiltT); } },
    sig: { dur: 2.0, fn(c, u, a, P) { const b = sstep(0, 0.2, u) * (1 - sstep(0.8, 1, u)), f = Math.sin(a.t * 34); P.yOff = 0.3 * b + f * 0.012; P.expr = 'effort'; P.hands = [1.25 + 0.15 * f, 0.1 + 0.16 * f]; P.handK = 600; P.sq = 0.06 * b; if (c.every('sg', 0.2)) { c.fx.sfx('step', 3); c.fx.spawn('dust', _v.set(c.pos.x + rnd(-0.3, 0.3), c.pos.y + 0.05, c.pos.z).clone(), { v: new V3(rnd(-0.6, 0.6), 0.2, rnd(-0.3, 0.3)), life: 0.4, size: 0.14, grow: 2 }); } } },
  },
  // ───────── 10 八寶：小章魚（大圓頭＋一圈短觸手，貼地滑行）
  octo: {
    pat: ['spots','stripes'],
    name: '八寶', sub: '小章魚', moveZh: '貼地滑行', sigZh: '噴墨', why: '頭大腳多，觸手各自晃動，停下來還在動',
    R: 0.34, rootSpan: 0.1, move: 'slide', footSize: null, handR: 0, top: 0.82, wob: 1.25, mouth: [0, 0.38, 0.37], front: 0.37, faceUp: 0.12, walk: 1.4, run: 3.4,
    face: { ...FACE, ex: 86, ey: 268, rx: 38, ry: 49, my: 326, mw: 12, mouthO: 1, eye: '#33264e', eye2: '#5c4690' },
    pals: [{ n: '葡萄', body: 0xa77de8, top: 0xdcc8ff, tip: 0xffd9e6, sss: 0x9060f0 }, { n: '蜜桃', body: 0xffab9c, top: 0xffe0d6, tip: 0xffece4, sss: 0xff7060 }, { n: '海藍', body: 0x8fc6f5, top: 0xd6ecff, tip: 0xe6f4ff, sss: 0x5090ff }, { n: '檸檬', body: 0xffdc78, top: 0xfff4c4, tip: 0xfff8dc, sss: 0xffb020 }],
    anc: { hat: [0, 0.79, 0.02, 1.05], bow: [0.2, 0.76, 0.12], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.3 };
      // 頭＝蒜頭形（最寬處約在頭高 60%，底部收到 ~80%）
      c.main = put(c, blobGeo(v => { const y = v.y, b = 1 + 0.1 * sstep(-0.35, 0.3, y) - 0.14 * sstep(0.1, -0.9, y); v.set(v.x * 0.345 * b, y * (y > 0 ? 0.37 : 0.31), v.z * 0.33 * b); }), M(c, { ...o, y0: -0.3, y1: 0.3, face: c.face, headC: [0, -0.03, 0], span: [2.2, 2.2] }), 0, 0.45, 0);
      const tm = MR(c, { ...o, color: p.body, top: p.body, y0: -1.5, y1: 1.5 }), sk = M(c, { ...o, color: p.body, top: p.body, y0: -1.5, y1: 1.5 });
      // 裙邊：從頭底外張到約 1.15 倍頭寬再往下收，下緣 6 個波；觸手從裙邊下緣長出來
      { const prof = [[0.2, 0.2], [0.27, 0.15], [0.3, 0.125], [0.33, 0.1], [0.375, 0.1], [0.4, 0.13], [0.395, 0.17], [0.37, 0.215], [0.3, 0.26], [0.2, 0.3]].map(q => new THREE.Vector2(q[0], q[1]));
        const g = new THREE.LatheGeometry(prof, Math.max(36, Math.round(60 * DETAIL.k)), 0, Math.PI * 2), P = g.attributes.position;
        for (let i = 0; i < P.count; i++) { const y = P.getY(i), x = P.getX(i), z = P.getZ(i), w = sstep(0.2, 0.08, y) * 0.03 * Math.cos(Math.atan2(z, x) * 6); P.setY(i, y - w); } g.computeVertexNormals(); put(c, g, sk); }
      const tp = M(c, { color: p.tip, top: p.tip, sss: p.sss, sssAmt: 0.2, y0: -1, y1: 1 }), RC = 0.062;
      for (let i = 0; i < 6; i++) {
        const a = (i + 0.5) / 6 * Math.PI * 2 + Math.PI / 2, cx = Math.cos(a), sz = Math.sin(a), SC = 0.62;
        // 觸手路徑（相對根）：先往外下垂、再往上捲成 0.6 圈的小圈；R＝徑向，Y＝向上，T＝切向（捲圈略偏出平面避免自交）
        const pth = (u) => { const t = Math.min(1, u / SC); let r, y, q = 0; if (u <= SC) { r = 0.05 + 0.3 * t; y = 0.03 - 0.2 * Math.sin(t * Math.PI / 2) + 0.03 * (1 - t); } else { const ph = (u - SC) / (1 - SC) * Math.PI * 1.25; const r0 = 0.35, y0 = -0.17; r = r0 + RC * Math.sin(ph); y = y0 + RC * (1 - Math.cos(ph)); q = 0.022 * (ph / 4); } return [cx * r - sz * q, y, sz * r + cx * q]; };
        const g = piv(c, cx * 0.1, 0.145, sz * 0.1, { side: cx > 0.2 ? 1 : cx < -0.2 ? -1 : 0, k: 80 + i * 6, c: 4.5, g: 0.035, gy: 0.01, wig: i * 0.9 });
        put(c, tubeGeo({ key: 'octo6_' + i, path: pth, rad: (u) => 0.031 + 0.056 * Math.pow(1 - u, 1.25), flare: 1.45, fl: 0.14, cap: 0.1, N: 34, S: 14 }), tm, 0, 0, 0, 1, 1, 1, g);
        for (const u of [0.74, 0.84, 0.94]) { const P = pth(u), P2 = pth(u + 0.01), cx2 = cx * (0.27 + 0), r = 0.031 + 0.056 * Math.pow(1 - u, 1.25); // 吸盤：捲圈內側（朝圈心）
          const ph = (u - SC) / (1 - SC) * Math.PI * 1.25, inx = -Math.sin(ph) * cx, iny = Math.cos(ph) - 0, inz = -Math.sin(ph) * sz; const L = Math.hypot(inx, iny, inz) || 1;
          put(c, ball(), tp, P[0] + inx / L * r * 0.8, P[1] + iny / L * r * 0.8, P[2] + inz / L * r * 0.8, 0.017, 0.017, 0.017, g); void P2; void cx2; }
      }
      const sp = M(c, { color: p.top, top: p.top, sss: p.sss, sssAmt: 0.2 }); for (const [x, y, z, r] of [[-0.2, 0.72, 0.1, 0.06], [-0.27, 0.62, 0.02, 0.035], [0.22, 0.7, -0.08, 0.045]]) put(c, ball(), sp, x, y, z, r, r * 0.5, r);
    },
    idle(c, dt, t) { const sp = Math.hypot(c.vel.x, c.vel.z); for (const a of c.apps) if (a.wig != null) { a.vx += Math.sin(t * 2.3 + a.wig) * 2.5 * dt; a.vz += Math.cos(t * 1.9 + a.wig * 1.7) * 2.5 * dt; if (sp > 0.2) { a.vz += Math.sin(t * 9 - a.wig * 1.1) * (6 + sp * 5) * dt * 3; a.vx += Math.cos(t * 9 - a.wig * 1.1) * 3 * dt * 3; } } },
    sig: { dur: 2.4, fn(c, u, a, P) { if (u < 0.3) { P.sq = -0.2 * sstep(0, 0.3, u); P.expr = 'effort'; } else { P.sq = 0.12 * (1 - sstep(0.3, 0.6, u)); P.expr = u < 0.5 ? 'surprised' : 'shy'; if (u > 0.5) { P.tint = [1, 0.6, 0.68]; P.tintA = 0.3; } if (!a.f) { a.f = 1; c.fx.sfx('skid'); c.sqV += 5; for (let i = 0; i < 12; i++) c.fx.spawn('dust', _v.set(c.pos.x - Math.sin(c.yaw) * 0.3, c.pos.y + 0.2, c.pos.z - Math.cos(c.yaw) * 0.3).clone(), { v: new V3(-Math.sin(c.yaw) * rnd(0.6, 1.8) + rnd(-0.4, 0.4), rnd(0, 0.7), -Math.cos(c.yaw) * rnd(0.6, 1.8) + rnd(-0.4, 0.4)), life: 1.3, size: 0.22, grow: 1.6, drag: 2.2, color: 0x4a3c6a }); } } } },
  },
  // ───────── 11 閃閃：小星星（鼓鼓的五角星，站在兩個下尖角上，會側翻）
  star: {
    pat: ['spots'],
    name: '閃閃', sub: '小星星', moveZh: '蹦蹦跳', sigZh: '側翻', why: '唯一有五個尖角（都磨圓）的剪影，側翻很搶眼',
    R: 0.3, move: 'hop', hopH: 0.13, lat: 0.13, footFwd: 0.02, footSize: [0.075, 0.05, 0.095], handR: 0, top: 0.76, wob: 0.9, mouth: [0, 0.34, 0.23], front: 0.24, tintK: 0.5, faceUp: 0.0, faceShift: 0.3, walk: 1.5, run: 3.6,
    face: { ...FACE, ex: 72, ey: 254, rx: 34, ry: 44, my: 312, mw: 15, line: 7, eye: '#4a3418', eye2: '#7a5a30', blush: '255,130,110' },
    pals: [{ n: '星星黃', body: 0xffd04a, top: 0xfff2a0, shoe: 0xff9f6a, sss: 0xffa020 }, { n: '櫻粉', body: 0xff9fbe, top: 0xffe0ea, shoe: 0xffffff, sss: 0xff6090 }, { n: '薄荷', body: 0x8fe0c0, top: 0xd8fbe8, shoe: 0xffffff, sss: 0x40d0a0 }, { n: '天藍', body: 0x8fc2ff, top: 0xd8ecff, shoe: 0xffe08a, sss: 0x5090ff }],
    anc: { hat: [0, 0.71, 0, 0.55], bow: [0.13, 0.55, 0.17], chest: [0, 0.17, 0.215], glasses: 1 },
    build(c, p) {
      c.main = put(c, blobGeo(v => { const ph = Math.atan2(v.x, v.y), k = Math.cos(5 * ph), rho = Math.hypot(v.x, v.y), rr = 0.3 * (1 + 0.21 * k * Math.pow(rho, 1.6)); v.set(v.x * rr, v.y * rr, v.z * 0.275 * (1 - 0.1 * rho * rho - 0.12 * Math.max(0, k) * rho)); }, 120, 60), M(c, { color: p.body, top: p.top, y0: -0.3, y1: 0.36, sss: p.sss, sssAmt: 0.45, rim: 0xffffff, rimAmt: 0.4, face: c.face, headC: [0, -0.02, -0.05], span: [1.95, 1.95] }), 0, 0.385, 0);
      const ck = M(c, { color: p.top, top: 0xffffff, sss: p.sss, sssAmt: 0.5 }); for (const q of [-1, 1]) put(c, ball(), ck, q * 0.2, 0.52, 0.1, 0.03, 0.03, 0.02);
      c.limbMat = M(c, { color: p.shoe, top: 0xffffff, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { if (c.mode !== 'sleep' && every(c, 'tw', 0.9, dt)) { const a = Math.floor(Math.random() * 5) * 1.2566, cy = Math.cos(c.yaw), sy = Math.sin(c.yaw), lx = Math.sin(a) * 0.36; c.fx.spawn('spark', new V3(c.pos.x + lx * cy, c.pos.y + c.yOff + 0.385 + Math.cos(a) * 0.36, c.pos.z - lx * sy), { life: 0.5, size: 0.11, spin: 3 }); } },
    sig: { dur: 1.5, fn(c, u, a, P) { const e = sstep(0.1, 0.9, u); P.spinZ = -e * Math.PI * 2; P.yOff = Math.sin(e * Math.PI) * 0.3; P.side = Math.sin(e * Math.PI) * 1.4; P.expr = 'whee'; P.sq = u < 0.1 ? -0.2 * u / 0.1 : 0.05; if (c.every('sg', 0.07)) c.fx.spawn('spark', c.headTop(new V3()).add(_v.set(rnd(-0.3, 0.3), rnd(-0.4, 0), 0)), { life: 0.5, size: 0.1 }); if (!a.f) { a.f = 1; c.fx.sfx('whee'); } } },
  },
  // ───────── 12 算算：計算機（方方的身體、液晶臉、九顆彩色按鍵）
  calc: {
    name: '算算', sub: '小計算機', moveZh: '硬邦邦地走', sigZh: '算一算', why: '唯一方形的剪影；液晶螢幕就是臉，按鍵會亮',
    R: 0.31, stride: [0.4, 0.9], lat: 0.14, footFwd: 0.02, footSize: [0.085, 0.055, 0.11], handR: 0.055, hand: [0.33, 0.3, 0.03], front: 0.16, cheek: [0.19, 0.56, 0.14], waddle: 0.1, wob: 0.35, mouth: [0, 0.52, 0.14], top: 0.78, tintK: 0.5, faceShift: 0.25,
    face: { kind: 'lcd', ex: 84, ey: 250, rx: 26, ry: 33, my: 300, mw: 15, line: 7, eye: '#30453a', eye2: '#30453a', blush: '255,150,150', blushAmt: 0.8, mouthIn: '#30453a', tongue: '#5a7a68', visor: { w: 410, h: 200, y: 156, r: 44, c0: '#d6eedc', c1: '#bfe2cc', dark: 1 } },
    pals: [{ n: '奶黃', body: 0xffe08f, top: 0xfff3c6, shoe: 0xffffff, sss: 0xffb030, keys: [0xff9fb5, 0x9fc4ff, 0x8fe3c4] }, { n: '薄荷', body: 0xaee6cf, top: 0xdff8ec, shoe: 0xffffff, sss: 0x40c0a0, keys: [0xffd27a, 0xff9fb5, 0x9fc4ff] }, { n: '櫻粉', body: 0xffb9c8, top: 0xffe4ea, shoe: 0xffffff, sss: 0xff6f9a, keys: [0xfff0b0, 0x9fc4ff, 0x8fe3c4] }, { n: '晴藍', body: 0xb0d0ff, top: 0xe2efff, shoe: 0xffe08a, sss: 0x6090ff, keys: [0xffd27a, 0xff9fb5, 0xffffff] }],
    anc: { hat: [-0.12, 0.74, 0, 0.8], bow: [0.17, 0.76, 0.06], glasses: 0 },
    build(c, p) {
      c.main = put(c, rbox(0.52, 0.64, 0.24, 0.085, 6), M(c, { color: p.body, top: p.top, y0: -0.32, y1: 0.32, sss: p.sss, sssAmt: 0.24, face: c.face, headC: [0, 0.145, -0.35], span: [1.16, 1.16] }), 0, 0.43, 0);
      c.keys = []; const kg = rbox(0.105, 0.075, 0.05, 0.022, 3);
      for (let r = 0; r < 3; r++) for (let k = 0; k < 3; k++) { const col = p.keys[(r + k) % 3], m = put(c, kg, M(c, { color: col, top: 0xffffff, y0: -0.04, y1: 0.12, sss: col, sssAmt: 0.25 }), (k - 1) * 0.14, 0.4 - r * 0.095, 0.115); c.keys.push(m); }
      c.limbMat = M(c, { color: p.shoe, top: 0xffffff, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { if (every(c, 'key', c.calc ? 0.11 : 1.4, dt)) { c.kI = c.calc ? ((c.kI ?? 0) + 1) % 9 : Math.floor(Math.random() * 9); c.kT = 0.22; if (c.calc) c.fx.sfx('ui'); } c.calc = false; c.kT = (c.kT ?? 0) - dt; c.keys.forEach((k, i) => { const on = i === c.kI && c.kT > 0; k.position.z = 0.115 - (on ? 0.02 : 0); k.material.userData.U.uSssAmt.value = on ? 1.1 : 0.25; }); },
    sig: { dur: 2.4, fn(c, u, a, P) { c.calc = u < 0.7; P.expr = u < 0.7 ? 'look' : 'happy'; P.sq = u < 0.7 ? -0.04 + Math.sin(a.t * 20) * 0.015 : 0.08; if (u > 0.7 && !a.f) { a.f = 1; c.say('答案是 100 分！', 1.6); c.fx.sfx('heart'); c.emote('smug', 1.6); } } },
  },
  // ───────── 13 布布：布丁（平頂的梯形、焦糖流下來、頂著櫻桃，抖得最厲害）
  pudding: {
    name: '布布', sub: '雞蛋布丁', moveZh: '抖著跳', sigZh: '抖抖舞', why: '平頂梯形＋櫻桃；全身晃動幅度最大',
    R: 0.33, move: 'hop', hopH: 0.07, footSize: null, handR: 0, top: 0.66, wob: 2.3, mouth: [0, 0.2, 0.32], front: 0.32, tintK: 0.5, faceUp: 0.12, walk: 1.3, run: 3.0, stride: [0.36, 0.7],
    face: { ...FACE, ex: 82, ey: 262, rx: 31, ry: 41, my: 316, mw: 15, wmouth: true, eye: '#4a2c18', eye2: '#7a4c28', blush: '255,130,120' },
    pals: [{ n: '雞蛋', body: 0xffd870, top: 0xfff0b4, cap: 0xb06c36, cap2: 0xdc9a58, ch: 0xff5f6e, sss: 0xffb030 }, { n: '草莓', body: 0xffb4c4, top: 0xffe4ea, cap: 0xf05f78, cap2: 0xff9aa8, ch: 0xffffff, sss: 0xff6f9a }, { n: '抹茶', body: 0xc2dc98, top: 0xe8f4cc, cap: 0x7a4a3a, cap2: 0xa8705a, ch: 0xfff3e0, sss: 0x90c040 }, { n: '可可', body: 0xc79a78, top: 0xe8c8a8, cap: 0xfff3e0, cap2: 0xffffff, ch: 0xff5f6e, sss: 0xa06030 }],
    anc: { bow: [0.17, 0.52, 0.1], chest: [0, 0.09, 0.345], glasses: 1 },
    build(c, p) {
      c.main = put(c, lathe([[0, 0], [0.3, 0], [0.348, 0.04], [0.335, 0.15], [0.275, 0.4], [0.24, 0.452], [0, 0.455]], 72, 64), M(c, { color: p.body, top: p.top, y0: 0, y1: 0.45, sss: p.sss, sssAmt: 0.34, rough: 0.45, face: c.face, headC: [0, 0.22, 0], span: [2.25, 2.25] }));
      put(c, blobGeo(v => { const th = Math.atan2(v.z, v.x), y = v.y; v.set(v.x * 0.283, y > 0 ? y * 0.05 : y * (0.085 + 0.065 * Math.sin(th * 5 + 1)), v.z * 0.283); }, 80, 40), M(c, { color: p.cap, top: p.cap2, y0: -0.12, y1: 0.05, sss: p.cap, sssAmt: 0.35, rough: 0.22 }), 0, 0.452, 0);
      const g = piv(c, 0.03, 0.49, 0, { k: 80, c: 4, g: 0.04 });
      put(c, ball(), M(c, { color: 0xfff6ea, sss: 0xffd0a0 }), 0, 0.02, 0, 0.1, 0.045, 0.1, g);
      put(c, ball(), M(c, { color: p.ch, top: 0xffffff, y0: -1, y1: 3, sss: p.ch, sssAmt: 0.5, rough: 0.2 }), 0, 0.085, 0, 0.058, 0.058, 0.058, g);
      const st = put(c, new THREE.CylinderGeometry(0.006, 0.006, 0.08, 8), M(c, { color: 0x7a9a50, sss: 0x7a9a50 }), 0.02, 0.16, 0, 1, 1, 1, g); st.rotation.z = -0.35;
    },
    idle(c, dt, t) { if (calm(c) && every(c, 'jig', 2.8, dt)) { c.wobV.x += rnd(-2.5, 2.5); c.sqV += 2.5; } if (c.jig) { c.wobV.x += Math.sin(t * 24) * 26 * dt; c.jig = false; } },
    sig: { dur: 2.2, fn(c, u, a, P) { c.jig = true; P.sq = Math.sin(a.t * 18) * 0.1; P.expr = 'laugh'; P.yaw = Math.sin(a.t * 6) * 0.3; if (c.every('sg', 0.26)) c.fx.sfx('boing'); } },
  },
  // ───────── 14 滾滾：小海豹（橫躺的長條身體、前鰭、尾鰭，一伸一縮往前蠕動）
  seal: {
    pat: ['spots','belly'],
    name: '滾滾', sub: '小海豹', moveZh: '一伸一縮', sigZh: '翻肚肚', why: '唯一橫躺的長條剪影；會翻肚子拍手',
    R: 0.29, move: 'slide', footSize: null, handR: 0.05, handScale: [0.12, 0.032, 0.085], hand: [0.34, 0.08, 0.16], top: 0.56, wob: 1.1, mouth: [0, 0.27, 0.5], front: 0.47, cheek: [0.18, 0.3, 0.42], faceUp: 0.2, walk: 1.2, run: 3.0, stride: [0.5, 0.9],
    face: { ...FACE, ex: 80, ey: 246, rx: 30, ry: 38, my: 316, mw: 15, line: 6, wmouth: true, nose: 1, whisk: 1, eye: '#2a2e3a', eye2: '#4a5268', blush: '255,150,160' },
    pals: [{ n: '雪白', body: 0xd7e2ee, top: 0xffffff, fin: 0xb9c8da, sss: 0xa9c0e0 }, { n: '灰藍', body: 0x9fb2c8, top: 0xd6e0ec, fin: 0x8094ae, sss: 0x7090c0 }, { n: '奶茶', body: 0xe6cdb0, top: 0xfff4e4, fin: 0xcfae8a, sss: 0xd09060 }, { n: '櫻粉', body: 0xffc4d0, top: 0xfff0f3, fin: 0xf5a4b6, sss: 0xff80a0 }],
    anc: { hat: [0, 0.56, 0.2, 0.8], bow: [0.14, 0.54, 0.24], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.26 };
      c.main = put(c, blobGeo(v => { const z = v.z, k = 1 + 0.17 * z, tl = 1 - 0.5 * sstep(-0.25, -1, z); v.set(v.x * 0.3 * k * tl, v.y * 0.255 * k * tl - 0.03 * (1 - tl) + 0.085 * sstep(0.0, 1, z), v.z * 0.47); }, 80, 60), M(c, { ...o, y0: -0.22, y1: 0.1, face: c.face, headC: [0, 0.02, 0.17], span: [2.0, 2.0] }), 0, 0.26, 0);
      const fm = M(c, { color: p.fin, top: p.body, y0: -1, y1: 1, sss: p.sss }); c.limbMat = fm;
      const t = piv(c, 0, 0.24, -0.4, { k: 130, c: 6, g: 0.03, wag: true }); for (const s of [-1, 1]) { const f = put(c, ball(), fm, s * 0.11, 0.2, -0.06, 0.1, 0.17, 0.034, t); f.rotation.set(-0.35, 0, -s * 0.62); }
      const sc2 = new THREE.Color(p.fin).multiplyScalar(0.68).getHex(), sp = M(c, { color: sc2, top: sc2, y0: -1, y1: 1, sss: p.sss, sssAmt: 0.05 }); for (const [x, y, z, r] of [[0.1, 0.475, -0.06, 0.05], [-0.07, 0.462, -0.2, 0.038], [-0.12, 0.49, 0.06, 0.03], [0.05, 0.43, -0.28, 0.026]]) put(c, ball(), sp, x, y, z, r * 1.25, r * 0.42, r * 1.25);
    },
    idle(c, dt, t) { tic(c, 'flap', 4.5, 1.4, dt, (u, end, st) => { const tl = c.apps.find(a => a.wag); if (tl && !end) tl.vz += Math.sin(u * 34) * 1.4; c.rollAdd = end ? 0 : Math.sin(u * Math.PI * 4) * 0.18 * (1 - u); if (st) c.sqV += 2.5; }); },
    sig: { dur: 2.4, fn(c, u, a, P) { const e = sstep(0.05, 0.4, u) - sstep(0.75, 1, u); P.spinZ = e * Math.PI; P.yOff = 0.24 * e; P.expr = 'happy'; const f = Math.sin(a.t * 16); P.hands = [0.5 + 0.35 * Math.max(0, f) * e, 0.2 * e]; if (e > 0.9 && c.every('sg', 0.39)) { c.fx.sfx('kick'); } } },
  },
  // ───────── 15 亮亮：燈泡（上圓下窄、螺旋金屬座，心情好會變亮）
  bulb: {
    name: '亮亮', sub: '小燈泡', moveZh: '踮腳走', sigZh: '靈光一閃', why: '倒梨形＋螺紋底座；亮度跟著心情變',
    R: 0.3, stride: [0.36, 0.85], lat: 0.085, footFwd: 0.02, footSize: [0.07, 0.05, 0.095], handR: 0.05, hand: [0.25, 0.27, 0.06], front: 0.3, cheek: [0.2, 0.6, 0.27], waddle: 0.08, wob: 0.75, mouth: [0, 0.52, 0.3], top: 0.9, tintK: 0.35, faceUp: 0.08,
    face: { ...FACE, ex: 76, ey: 262, rx: 30, ry: 39, my: 314, mw: 14, eye: '#4a3a1a', eye2: '#7a6030', blush: '255,140,110' },
    pals: [{ n: '暖黃', body: 0xffe690, top: 0xfffbe0, base: 0xc6c4dc, sss: 0xffd040 }, { n: '冷白', body: 0xcfe6ff, top: 0xffffff, base: 0xc6c4dc, sss: 0x80c0ff }, { n: '櫻粉', body: 0xffc6d4, top: 0xfff2f5, base: 0xe0c8d0, sss: 0xff80a0 }, { n: '薄荷', body: 0xbff0d8, top: 0xf6fffa, base: 0xc8d8d0, sss: 0x50e0a0 }],
    anc: { hat: [0, 0.86, 0, 0.85], bow: [0.17, 0.84, 0.08], neck: [0.33, 0.185, 0.185], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.3, y1: 0.3, sss: p.sss, sssAmt: 0.55, rim: 0xffffff, rimAmt: 0.5, rough: 0.28, face: c.face, headC: [0, 0.04, 0], span: [2.2, 2.2] }); c.glowU = m.userData.U.uSssAmt;
      c.main = put(c, blobGeo(v => { const y = v.y, n = sstep(-0.2, -0.95, y), r = 0.305 * (1 - 0.52 * n); v.set(v.x * r, y * (y > 0 ? 0.31 : 0.37), v.z * r); }), m, 0, 0.57, 0);
      put(c, lathe([[0, 0.09], [0.1, 0.09], [0.14, 0.115], [0.166, 0.145], [0.148, 0.175], [0.168, 0.205], [0.15, 0.235], [0.17, 0.265], [0.155, 0.3], [0, 0.3]], 48, 80), M(c, { color: p.base, top: 0xffffff, y0: 0.05, y1: 0.5, sss: 0x9090c0, sssAmt: 0.2, rough: 0.3 }));
      c.limbMat = M(c, { color: p.base, top: 0xffffff, y0: 0, y1: 1.6, sss: 0x9090c0 });
    },
    idle(c, dt, t) { const e = c.emo && c.emo.name, tg = c.flash ? 1.7 : c.mode === 'sleep' ? 0.12 : e === 'sad' || e === 'sleepy' ? 0.22 : e === 'happy' || e === 'laugh' ? 0.95 : 0.55; let fl = 1; tic(c, 'flick', 6, 0.9, dt, (u, end) => { fl = end ? 1 : (Math.sin(u * 60) > 0.2 ? 1 : 0.2) * (u < 0.7 ? 1 : 1); }); c.glowU.value += (tg * fl + Math.sin(t * 3) * 0.03 - c.glowU.value) * Math.min(1, dt * (c.flash ? 30 : 14)); c.flash = false; },
    sig: { dur: 2.0, fn(c, u, a, P) { if (u < 0.4) { P.expr = 'sleepy'; P.pitch = 0.1; P.hands = [0.5, 0.3]; } else { c.flash = u < 0.75; P.expr = 'surprised'; P.sq = 0.14 * (1 - sstep(0.4, 1, u)); P.yOff = 0.1 * Math.sin(sstep(0.4, 0.7, u) * Math.PI); P.hands = [1.3, 0.3]; if (!a.f) { a.f = 1; c.say('有了！', 1.3); c.fx.sfx('heart'); c.sqV += 5; c.fx.burst('spark', c.headTop(new V3()), 9, { speed: 1.3, up: 0.6, life: 0.5, size: 0.13 }); } } } },
  },
  // ───────── 16 貼貼：便利貼（方方一張、右上角翹起來、身上有兩行字）
  note: {
    name: '貼貼', sub: '便利貼', moveZh: '啪嗒啪嗒走', sigZh: '貼上去', why: '薄薄一張方形紙，右上角翹起來；走路會像紙一樣飄',
    R: 0.3, stride: [0.4, 0.9], lat: 0.13, footFwd: 0.02, footSize: [0.08, 0.055, 0.105], handR: 0.055, hand: [0.34, 0.3, 0.03], front: 0.1, cheek: [0.19, 0.5, 0.1], waddle: 0.12, wob: 1.5, mouth: [0, 0.42, 0.09], top: 0.72, tintK: 0.5, faceShift: 0.25,
    face: { ...FACE, ex: 78, ey: 250, rx: 30, ry: 39, my: 306, mw: 15, eye: '#4a3a1a', eye2: '#7a6030', blush: '255,140,120' },
    pals: [{ n: '檸檬黃', body: 0xffe37a, top: 0xfff6c0, ink: 0xe0b84a, shoe: 0xffffff, sss: 0xffb830 }, { n: '櫻花粉', body: 0xffb3c8, top: 0xffe2ea, ink: 0xe88aa6, shoe: 0xffffff, sss: 0xff6f9a }, { n: '天空藍', body: 0xa9d2ff, top: 0xe0f0ff, ink: 0x7aaae6, shoe: 0xfff0b0, sss: 0x6090ff }, { n: '薄荷綠', body: 0xa8e6c4, top: 0xdcf8ea, ink: 0x74c49a, shoe: 0xffffff, sss: 0x40c090 }],
    anc: { hat: [-0.13, 0.69, 0, 0.75], bow: [-0.2, 0.7, 0.07], chest: [0.02, 0.1, 0.066], glasses: 1 },
    build(c, p) {
      const g = rbox(0.56, 0.56, 0.11, 0.045, 6), P = g.attributes.position;
      for (let i = 0; i < P.count; i++) { const x = P.getX(i), y = P.getY(i), k = sstep(0.3, 0.56, x + y); if (k > 0) { P.setZ(i, P.getZ(i) + k * k * 0.2); P.setY(i, y - k * k * 0.08); P.setX(i, x - k * k * 0.05); } }
      c.main = put(c, g, M(c, { color: p.body, top: p.top, y0: -0.28, y1: 0.3, sss: p.sss, sssAmt: 0.26, face: c.face, headC: [0, 0.07, -0.36], span: [1.2, 1.2] }), 0, 0.4, 0);
      const im = M(c, { color: p.ink, sss: p.ink, sssAmt: 0.2 }); put(c, rbox(0.3, 0.026, 0.02, 0.01, 2), im, -0.06, 0.25, 0.058); put(c, rbox(0.2, 0.026, 0.02, 0.01, 2), im, -0.11, 0.2, 0.058);
      put(c, rbox(0.56, 0.07, 0.03, 0.012, 2), M(c, { color: p.ink, top: p.body, y0: -0.05, y1: 0.05, sss: p.sss, sssAmt: 0.2 }), 0, 0.64, -0.052);
      c.limbMat = M(c, { color: p.shoe, top: 0xffffff, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { if (calm(c) && every(c, 'flap', 3.4, dt)) { c.wobV.x += rnd(-3, 3); c.wobV.z += rnd(1.5, 3); } },
    sig: { dur: 1.8, fn(c, u, a, P) { if (u < 0.35) { P.sq = 0.22 * sstep(0, 0.35, u); P.yOff = 0.3 * sstep(0, 0.35, u); P.expr = 'whee'; P.hands = [1.3, 0.3]; } else { const k = 1 - sstep(0.35, 0.5, u); P.yOff = 0.3 * k; P.sq = -0.3 * (1 - k) * (1 - sstep(0.6, 1, u)); P.expr = 'happy'; P.hands = [1.2, 0.1]; if (!a.f && u > 0.5) { a.f = 1; c.say('貼好了！', 1.2); c.fx.sfx('land', 1); c.fx.burst('spark', c.headTop(new V3()), 6, { speed: 1, up: 0.5, life: 0.5, size: 0.12 }); } } } },
  },
  // ───────── 17 夾夾：資料夾（橫的牛皮紙夾、左上有標籤耳、裡面的文件探出頭）
  folder: {
    name: '夾夾', sub: '資料夾', moveZh: '抱著文件走', sigZh: '翻文件', why: '比高還寬的橫長方形＋標籤耳，文件從上面探出來會晃',
    R: 0.32, stride: [0.42, 0.9], lat: 0.15, footFwd: 0.02, footSize: [0.085, 0.055, 0.11], handR: 0.056, hand: [0.38, 0.27, 0.04], front: 0.13, cheek: [0.2, 0.42, 0.12], waddle: 0.09, wob: 0.6, mouth: [0, 0.33, 0.1], top: 0.72, tintK: 0.5, faceShift: 0.25,
    face: { ...FACE, ex: 84, ey: 252, rx: 30, ry: 39, my: 306, mw: 15, eye: '#4a3418', eye2: '#7a5a30', blush: '255,140,120' },
    pals: [{ n: '牛皮紙', body: 0xf2c98a, top: 0xffe8be, paper: 0xfffdf6, paper2: 0xa9d2ff, shoe: 0xffffff, sss: 0xe09040 }, { n: '海軍藍', body: 0x9db8f0, top: 0xd4e2ff, paper: 0xfffdf6, paper2: 0xffe37a, shoe: 0xffffff, sss: 0x6080e0 }, { n: '草綠', body: 0xa6dc9c, top: 0xdaf4d0, paper: 0xfffdf6, paper2: 0xffb3c8, shoe: 0xffffff, sss: 0x50b060 }, { n: '莓果', body: 0xf5a6b8, top: 0xffdbe4, paper: 0xfffdf6, paper2: 0xa8e6c4, shoe: 0xffffff, sss: 0xff6080 }],
    anc: { hat: [0.14, 0.66, 0, 0.75], bow: [0.24, 0.6, 0.08], chest: [0, 0.07, 0.078], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.24 };
      c.main = put(c, rbox(0.66, 0.46, 0.14, 0.06, 6), M(c, { ...o, y0: -0.23, y1: 0.25, face: c.face, headC: [0, 0.05, -0.36], span: [1.25, 1.25] }), 0, 0.33, 0);
      put(c, rbox(0.24, 0.13, 0.13, 0.045, 3), M(c, { ...o, y0: -0.1, y1: 0.1 }), -0.19, 0.575, -0.005);
      const g = piv(c, 0.06, 0.54, -0.02, { k: 120, c: 6, g: 0.03 }); c.papers = g;
      put(c, rbox(0.5, 0.16, 0.035, 0.016, 2), M(c, { color: p.paper, sss: 0xffd0a0, sssAmt: 0.2 }), 0, 0.04, 0, 1, 1, 1, g).rotation.z = 0.05;
      put(c, rbox(0.42, 0.16, 0.03, 0.014, 2), M(c, { color: p.paper2, top: 0xffffff, y0: -0.1, y1: 0.3, sss: p.paper2, sssAmt: 0.2 }), 0.06, 0.075, -0.035, 1, 1, 1, g).rotation.z = -0.08;
      put(c, rbox(0.2, 0.07, 0.02, 0.012, 2), M(c, { color: 0xfffdf6, sss: 0xffd0a0, sssAmt: 0.2 }), 0.17, 0.2, 0.066);
      c.limbMat = M(c, { color: p.shoe, top: 0xffffff, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { tic(c, 'peek', 5.5, 1.2, dt, (u, end) => { c.flip = !end && u > 0.1 && u < 0.85; if (!end) c.papers.rotation.z = Math.sin(u * 14) * 0.08; }); const s = c.papers.scale.y + ((c.flip ? 1.9 : 1) - c.papers.scale.y) * Math.min(1, dt * 10); c.papers.scale.y = s; c.flip = false; },
    sig: { dur: 2.0, fn(c, u, a, P) { c.flip = u > 0.2 && u < 0.85 && Math.sin(a.t * 14) > -0.3; P.expr = u < 0.85 ? 'look' : 'happy'; P.sq = u < 0.2 ? -0.12 * u / 0.2 : 0.05; P.hands = [1.1, 0.25]; P.wig = 0.4; if (c.every('sg', 0.3)) c.fx.sfx('ui'); if (u > 0.85 && !a.f) { a.f = 1; c.say('找到了！', 1.3); } } },
  },
  // ───────── 18 筆筆：鉛筆（最高最瘦、頭頂是削尖的筆尖、腳邊是橡皮擦）
  pencil: {
    name: '筆筆', sub: '鉛筆', moveZh: '直挺挺地走', sigZh: '畫一圈', why: '最高最瘦的直條，筆尖像一頂尖帽子（尖端磨圓）',
    R: 0.26, stride: [0.38, 0.85], lat: 0.09, footFwd: 0.02, footSize: [0.07, 0.05, 0.095], handR: 0.05, hand: [0.27, 0.33, 0.04], front: 0.21, cheek: [0.15, 0.5, 0.19], waddle: 0.07, wob: 0.55, mouth: [0, 0.42, 0.21], top: 1.0, tintK: 0.5, faceUp: 0.04,
    face: { ...FACE, ex: 60, ey: 258, rx: 25, ry: 33, my: 304, mw: 12, line: 6, eye: '#3a2a16', eye2: '#6a4a28', blush: '255,130,110' },
    pals: [{ n: '經典黃', body: 0xffd35a, top: 0xffeea0, wood: 0xf6ddb4, tip: 0x6b6470, er: 0xff9fb5, sss: 0xffa820 }, { n: '珊瑚紅', body: 0xff9a8a, top: 0xffd0c4, wood: 0xf6ddb4, tip: 0x6b6470, er: 0xfff0b0, sss: 0xff6050 }, { n: '天藍', body: 0x8fc2ff, top: 0xd0e6ff, wood: 0xf6ddb4, tip: 0x5a6078, er: 0xffb3c8, sss: 0x5090ff }, { n: '抹茶', body: 0xa8d890, top: 0xdcf2c8, wood: 0xf6ddb4, tip: 0x6b6470, er: 0xffc9a0, sss: 0x60b040 }],
    anc: { bow: [0.13, 0.7, 0.1], chest: [0, 0.2, 0.205], neck: [0.3, 0.215, 0.215], glasses: 1 },
    build(c, p) {
      c.main = put(c, lathe([[0, 0.13], [0.17, 0.13], [0.205, 0.16], [0.21, 0.4], [0.205, 0.64], [0.17, 0.675], [0, 0.68]], 56, 48), M(c, { color: p.body, top: p.top, y0: 0.13, y1: 0.7, sss: p.sss, sssAmt: 0.28, face: c.face, headC: [0, 0.44, 0], span: [2.9, 2.9] }));
      put(c, lathe([[0, 0.64], [0.18, 0.645], [0.19, 0.67], [0.13, 0.79], [0.07, 0.885], [0, 0.89]], 48, 40), M(c, { color: p.wood, top: 0xfff6e4, y0: 0.64, y1: 0.9, sss: 0xe0a060, sssAmt: 0.3 }));
      const tp = piv(c, 0, 0.87, 0, { k: 200, c: 9, g: 0.012 }); put(c, lathe([[0, 0], [0.068, 0.0], [0.05, 0.06], [0.022, 0.1], [0, 0.11]], 32, 24), M(c, { color: p.tip, top: 0x9a94a0, y0: 0, y1: 0.12, sss: 0x404050, sssAmt: 0.2, rough: 0.35 }), 0, 0, 0, 1, 1, 1, tp);
      put(c, lathe([[0, 0.085], [0.2, 0.085], [0.214, 0.1], [0.2, 0.115], [0.214, 0.13], [0.2, 0.15], [0, 0.15]], 48, 40), M(c, { color: 0xd4d2e2, top: 0xffffff, y0: 0.08, y1: 0.16, sss: 0x9090c0, sssAmt: 0.2, rough: 0.3 }));
      put(c, lathe([[0, 0.01], [0.15, 0.012], [0.195, 0.04], [0.195, 0.09], [0, 0.095]], 48, 32), M(c, { color: p.er, top: 0xffffff, y0: 0, y1: 0.2, sss: p.er, sssAmt: 0.35 }));
      c.limbMat = M(c, { color: p.er, top: 0xffffff, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { tic(c, 'spin', 8, 1.3, dt, (u, end, st) => { const e = sstep(0.18, 0.9, u); c.idleYaw = end ? 0 : e * Math.PI * 2; c.idleY = end ? 0 : Math.sin(e * Math.PI) * 0.08; if (st) c.sqV -= 2.5; if (!end && u > 0.9 && !c.pdone) { c.pdone = 1; c.sqV += 3; } if (end) c.pdone = 0; }); },
    sig: { dur: 1.7, fn(c, u, a, P) { const e = sstep(0.1, 0.85, u); P.yaw = e * Math.PI * 2; P.sq = u < 0.1 ? -0.14 * u / 0.1 : 0.07 * (1 - u); P.yOff = Math.sin(e * Math.PI) * 0.1; P.expr = u > 0.85 ? 'happy' : 'effort'; P.hands = [1.3, 0.2]; if (c.every('sg', 0.06) && u < 0.85) { const an = c.yaw + e * Math.PI * 2; c.fx.spawn('spark', new V3(c.pos.x + Math.sin(an) * 0.45, c.pos.y + 0.05, c.pos.z + Math.cos(an) * 0.45), { life: 0.7, size: 0.1 }); } if (u > 0.85 && !a.f) { a.f = 1; c.say('畫好了！', 1.2); c.fx.sfx('heart'); } } },
  },
  // ───────── 19 印印：印章（圓圓的握把頭、細脖子、寬寬的章座，走路就是一下一下蓋章）
  stamp: {
    name: '印印', sub: '印章', moveZh: '一下一下蓋', sigZh: '核可', why: '上圓下寬的葫蘆剪影；每跳一步都像蓋一次章',
    R: 0.3, move: 'hop', hopH: 0.11, footSize: null, handR: 0.055, hand: [0.34, 0.36, 0.08], stick: [0.36, 0.42, 0.34, 0.4], top: 0.86, wob: 0.7, mouth: [0, 0.5, 0.25], front: 0.27, cheek: [0.18, 0.58, 0.22], tintK: 0.45, faceUp: 0.06, walk: 1.35, run: 3.1, stride: [0.4, 0.75],
    face: { ...FACE, ex: 76, ey: 262, rx: 30, ry: 39, my: 314, mw: 14, eye: '#3a2618', eye2: '#6a4630', blush: '255,130,120' },
    pals: [{ n: '原木', body: 0xf0c48e, top: 0xffe6c0, base: 0xd89a62, ink: 0xf2605a, sss: 0xe08840 }, { n: '櫻桃木', body: 0xf5a99a, top: 0xffd8cc, base: 0xd87a6a, ink: 0x6a8fe8, sss: 0xff6050 }, { n: '薄荷', body: 0xb4e4d0, top: 0xe4f8ee, base: 0x7cc4a8, ink: 0xf2605a, sss: 0x40c0a0 }, { n: '藍莓', body: 0xb6c6f6, top: 0xe2e8ff, base: 0x8a9ee0, ink: 0xffb040, sss: 0x6070ff }],
    anc: { hat: [0, 0.82, 0, 0.9], bow: [0.17, 0.8, 0.08], neck: [0.345, 0.15, 0.15], chest: [0, 0.07, 0.29], glasses: 1 },
    build(c, p) {
      c.main = put(c, blobGeo(v => { v.set(v.x * 0.265, v.y * (v.y > 0 ? 0.255 : 0.235), v.z * 0.255); }), M(c, { color: p.body, top: p.top, y0: -0.24, y1: 0.26, sss: p.sss, sssAmt: 0.3, face: c.face, headC: [0, 0.03, 0], span: [2.2, 2.2] }), 0, 0.6, 0);
      put(c, lathe([[0, 0.04], [0.27, 0.04], [0.3, 0.07], [0.3, 0.18], [0.26, 0.225], [0.15, 0.26], [0.115, 0.32], [0.125, 0.4], [0, 0.4]], 56, 64), M(c, { color: p.base, top: p.body, y0: 0.04, y1: 0.4, sss: p.sss, sssAmt: 0.25 }));
      put(c, lathe([[0, 0], [0.26, 0], [0.292, 0.02], [0.292, 0.05], [0, 0.055]], 56, 24), M(c, { color: p.ink, top: 0xffffff, y0: -0.1, y1: 0.4, sss: p.ink, sssAmt: 0.4, rough: 0.4 }));
      c.limbMat = M(c, { color: p.base, top: p.body, y0: -1, y1: 1.2, sss: p.sss });
    },
    idle(c, dt, t) { tic(c, 'stamp', 7, 1.2, dt, (u, end, st) => { const k = u < 0.5 ? Math.sin(u / 0.5 * Math.PI * 0.5) : 1 - sstep(0.5, 0.6, u); c.idleY = end ? 0 : 0.3 * k; if (!end && u >= 0.5 && !c.sdone) { c.sdone = 1; c.sqV -= 5; c.fx.burst('dust', new V3(c.pos.x, c.pos.y + 0.05, c.pos.z), 4, { speed: 0.8, up: 0.2, life: 0.4, size: 0.14, grow: 2, drag: 3 }); } if (end) c.sdone = 0; }); },
    sig: { dur: 1.9, fn(c, u, a, P) { if (u < 0.4) { const k = sstep(0, 0.4, u); P.yOff = 0.42 * Math.sin(k * Math.PI * 0.5); P.sq = 0.16 * k; P.expr = 'effort'; P.hands = [1.2, 0.35]; } else { const k = sstep(0.4, 0.5, u); P.yOff = 0.42 * (1 - k); P.sq = -0.38 * k * (1 - sstep(0.62, 1, u)); P.expr = u > 0.55 ? 'smug' : 'effort'; P.hands = [1.25, 0.05]; if (k >= 1 && !a.f) { a.f = 1; c.say('核可！', 1.3); c.fx.sfx('land', 1.4); c.fx.burst('dust', new V3(c.pos.x, c.pos.y + 0.05, c.pos.z), 8, { speed: 1.2, up: 0.3, life: 0.5, size: 0.2, grow: 2.2, drag: 3 }); c.fx.burst('star', c.headTop(new V3()), 4, { speed: 1.2, up: 1.4, g: 5, life: 0.7, size: 0.15, spin: 5 }); } } } },
  },

  // ───────── 20 彎彎：檯燈（圓盤底座＋彎成 C 形的長脖子＋大圓燈罩，點頭時燈罩會晃）
  lamp: {
    name: '彎彎', sub: '彎脖子檯燈', moveZh: '蹦著走', sigZh: '打亮', why: '全場唯一有彎曲長脖子的剪影：細脖子撐著大燈罩，點頭時整顆頭會晃', memo: '長彎脖子＋大圓燈罩',
    R: 0.3, move: 'hop', hopH: 0.1, footSize: null, handR: 0.05, hand: [0.3, 0.3, 0.1], top: 0.78, wob: 1.0, mouth: [0, 0.55, 0.3], front: 0.3, cheek: [0.22, 0.6, 0.3], tintK: 0.4, faceUp: 0.2, walk: 1.3, run: 3.0, faceShift: 0.6,
    face: { ...FACE, ex: 80, ey: 258, rx: 30, ry: 39, my: 316, mw: 14, eye: '#4a3a1a', eye2: '#7a6030', blush: '255,140,110' },
    pals: [{ n: '檸檬燈', body: 0xffd96a, top: 0xfff0b0, arm: 0xdcd6ea, glow: 0xfff2a8, sss: 0xffb020 }, { n: '天空藍', body: 0x9ccaff, top: 0xe2f0ff, arm: 0xdcd6ea, glow: 0xe8f6ff, sss: 0x5a9aff }, { n: '櫻桃粉', body: 0xffa9bd, top: 0xffe2ea, arm: 0xe8d6dc, glow: 0xfff0e8, sss: 0xff6a90 }, { n: '薄荷', body: 0x9fe0c4, top: 0xe0fbee, arm: 0xd2e2dc, glow: 0xf0fff6, sss: 0x40c898 }],
    anc: { hat: [-0.01, 0.78, 0.07, 0.8], bow: [0.2, 0.55, 0.2], glasses: 1 },
    build(c, p) {
      const am = M(c, { color: p.arm, top: 0xffffff, y0: 0, y1: 0.7, sss: 0x9090c0, sssAmt: 0.2, rough: 0.3 });
      put(c, lathe([[0, 0], [0.2, 0], [0.245, 0.02], [0.245, 0.05], [0.14, 0.085], [0, 0.09]], 56, 40), M(c, { color: p.arm, top: 0xffffff, y0: 0, y1: 0.1, sss: 0x9090c0, sssAmt: 0.2, rough: 0.3 }));
      const pts = [[0, 0.08, 0], [-0.1, 0.2, -0.04], [-0.17, 0.34, -0.06], [-0.13, 0.46, -0.03]]; c.armPts = pts;
      for (let i = 0; i < 3; i++) { rod(c, am, pts[i], pts[i + 1], 0.032); put(c, ball(), am, ...pts[i + 1], 0.042); }
      put(c, ball(), am, 0, 0.09, 0, 0.04);
      const h = piv(c, -0.13, 0.46, -0.03, { k: 70, c: 4.6, g: 0.03, rest: [0.1, 0] }); c.headG = h; c.headApp = c.apps[c.apps.length - 1];
      const sm = M(c, { color: p.body, top: p.top, y0: 0.0, y1: 0.28, sss: p.sss, sssAmt: 0.3, rim: 0xffffff, rimAmt: 0.35, rough: 0.5, face: c.face, headC: [0, 0.12, 0], span: [2.0, 2.0] });
      c.main = put(c, lathe([[0, 0.002], [0.28, 0.002], [0.315, 0.025], [0.3, 0.07], [0.255, 0.15], [0.19, 0.23], [0.1, 0.285], [0, 0.3]], 64, 56), sm, 0.12, 0, 0.08, 1, 1, 1, h);
      const gm = M(c, { color: p.glow, top: 0xffffff, y0: -1, y1: 1, sss: p.glow, sssAmt: 1.1, rim: p.glow, rimAmt: 0.5, rough: 0.3 }); c.glowU = gm.userData.U.uSssAmt;
      const rim = put(c, new THREE.TorusGeometry(0.295, 0.022, 14, 56), gm, 0.12, 0.012, 0.08, 1, 1, 1, h); rim.rotation.x = Math.PI / 2;
      put(c, ball(), gm, 0.12, -0.02, 0.08, 0.09, 0.07, 0.09, h);
      put(c, rbox(0.06, 0.04, 0.06, 0.016, 3), am, 0.12, 0.3, 0.08, 1, 1, 1, h);
      c.limbMat = am;
    },
    idle(c, dt, t) {
      const e = c.emo && c.emo.name, tg = c.flash ? 1.8 : c.mode === 'sleep' ? 0.15 : e === 'sad' || e === 'sleepy' ? 0.3 : e === 'happy' || e === 'laugh' ? 1.1 : 0.75; let fl = 1;
      tic(c, 'nod', 5, 1.4, dt, (u, end, st) => { if (st) c.headApp.vx += 4.5; fl = end ? 1 : (u > 0.45 && u < 0.7 ? 0.25 + 0.75 * (Math.sin(u * 90) > 0 ? 1 : 0) : 1); });
      c.glowU.value += (tg * fl - c.glowU.value) * Math.min(1, dt * (c.flash ? 30 : 12)); c.flash = false;
    },
    sig: { dur: 1.9, fn(c, u, a, P) { c.flash = u > 0.35 && u < 0.85; P.pitch = u < 0.3 ? 0.2 * u / 0.3 : -0.1; P.sq = u < 0.3 ? -0.1 : 0.08 * (1 - u); P.expr = u < 0.35 ? 'effort' : 'happy'; P.hands = [1.1, 0.3]; if (u > 0.35 && !a.f) { a.f = 1; c.say('打亮啦！', 1.3); c.fx.sfx('heart'); c.fx.burst('spark', c.headTop(new V3()), 8, { speed: 1.2, up: 0.6, life: 0.5, size: 0.12 }); } } },
  },
  // ───────── 21 慢慢：蝸牛（橫長的身體、背上一個有螺旋的殼、兩根會轉的眼柄）
  snail: {
    name: '慢慢', sub: '小蝸牛', moveZh: '貼地慢慢滑', sigZh: '縮進殼裡', why: '橫躺的身體背著一圈圈螺旋殼，兩根眼柄各動各的', memo: '螺旋殼＋兩根眼柄',
    pat: ['spots'], R: 0.3, move: 'slide', footSize: null, handR: 0, top: 0.66, wob: 1.0, mouth: [0, 0.2, 0.48], front: 0.5, cheek: [0.16, 0.22, 0.44], faceUp: 0.14, walk: 1.0, run: 2.3, stride: [0.5, 0.9],
    face: { ...FACE, ex: 70, ey: 250, rx: 28, ry: 37, my: 312, mw: 14, line: 6, eye: '#2d3340', eye2: '#566074', blush: '255,150,150' },
    pals: [{ n: '蜜桃', body: 0xffd9b8, top: 0xfff0e2, body: 0xb7a6f0, shell2: 0xe0d6ff, ridge: 0x8f7be0, sss: 0xff9070 }, { n: '薄荷', body: 0xd6f0c8, top: 0xf4fcec, body: 0xffcf7a, shell2: 0xffeab8, ridge: 0xe09a30, sss: 0x80d070 }, { n: '奶藍', body: 0xdbe6f6, top: 0xf6f9ff, body: 0xff9fb5, shell2: 0xffd6df, ridge: 0xe0708f, sss: 0x80a0e0 }, { n: '焦糖', body: 0xf0d2a8, top: 0xfff0d4, body: 0x8fd0c0, shell2: 0xc8f0e4, ridge: 0x50a898, sss: 0xd09050 }],
    anc: { hat: [0, 0.5, 0.3, 0.6], bow: [0.15, 0.44, 0.38], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.26 };
      c.main = put(c, blobGeo(v => { const z = v.z, k = 1 + 0.1 * z, tl = 1 - 0.58 * sstep(-0.15, -1, z); v.set(v.x * 0.215 * k * tl, v.y * 0.17 * k * tl - 0.04 * (1 - tl) + 0.14 * sstep(0.1, 1, z), v.z * 0.5); }, 80, 60), M(c, { ...o, y0: -0.2, y1: 0.12, face: c.face, headC: [0, 0.1, 0.2], span: [2.1, 2.1] }), 0, 0.19, 0);
      const sg = piv(c, 0, 0.36, -0.1, { k: 120, c: 6, g: 0.025, rest: [0, 0] }); c.shellG = sg;
      const sm = M(c, { color: p.shell, top: p.shell2, y0: -0.2, y1: 0.25, sss: p.shell, sssAmt: 0.28, rim: 0xffffff, rimAmt: 0.4, rough: 0.4 });
      put(c, blobGeo(v => v.set(v.x * 0.14, v.y * 0.255, v.z * 0.255), 64, 48), sm, 0, 0, 0, 1, 1, 1, sg);
      const rm = M(c, { color: p.ridge, top: p.ridge, y0: -1, y1: 1, sss: p.ridge, sssAmt: 0.2, rough: 0.5 });
      for (const sd of [-1, 1]) {
        const pts = []; for (let i = 0; i <= 46; i++) { const th = i / 46 * Math.PI * 4.2 + 0.3, r = 0.02 + 0.215 * (i / 46), y = Math.cos(th * sd) * r, z = Math.sin(th * sd) * r, q = 1 - (y / 0.255) ** 2 - (z / 0.255) ** 2; pts.push(new V3(sd * (0.14 * Math.sqrt(Math.max(0, q)) + 0.004), y, z)); }
        const tg = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 70, 0.0105, 7, false); put(c, tg, rm, 0, 0, 0, 1, 1, 1, sg);
      }
      const em = M(c, { color: p.body, top: p.top, y0: -1, y1: 1, sss: p.sss, sssAmt: 0.3 }), tm = M(c, { color: p.ridge, top: p.shell2, y0: -1, y1: 1, sss: p.shell, sssAmt: 0.5, rough: 0.35 });
      c.stalks = [];
      for (const s of [-1, 1]) { const g = piv(c, s * 0.075, 0.37, 0.3, { side: s, k: 85, c: 5, g: 0.03, rest: [0.12, s * 0.28], droop: 0.45 }); c.stalks.push(c.apps[c.apps.length - 1]); rod(c, em, [0, 0, 0], [0, 0.16, 0], 0.014, g); put(c, ball(), tm, 0, 0.18, 0, 0.034, 0.034, 0.034, g); }
      c.limbMat = em;
    },
    idle(c, dt, t) {
      tic(c, 'look', 4.2, 1.8, dt, (u, end, st) => { if (st) { c.stalks[0].vx += 6; c.stalks[1].vx -= 2; c.stalks[0].vz -= 4; c.stalks[1].vz += 5; } if (!end && c.shellG) c.apps.find(a => a.piv === c.shellG).vz += Math.sin(u * 14) * 0.3 * dt * 20; });
    },
    sig: { dur: 2.2, fn(c, u, a, P) { const e = sstep(0, 0.25, u) * (1 - sstep(0.75, 1, u)); P.sq = -0.34 * e; P.pitch = 0.5 * e; P.expr = e > 0.5 ? 'shy' : 'neutral'; P.tint = [0.9, 0.85, 1]; P.tintA = 0.2 * e; if (e > 0.9 && !a.f) { a.f = 1; c.say('（躲起來）', 1.2); c.fx.sfx('skid'); } } },
  },
  // ───────── 22 啃啃：小恐龍（粗尾巴會甩、背上一排圓背板、鼻頭微凸）
  dino: {
    name: '啃啃', sub: '小恐龍', moveZh: '大步走', sigZh: '嗷！', why: '前傾的梨形身體、往側後方甩出的粗尾巴、頭頂高過頭的大背板；甩尾巴時整隻跟著晃', memo: '側甩上翹的粗尾巴＋三片大中小背板',
    pat: ['spots', 'stripes', 'belly'], R: 0.33, stride: [0.46, 0.95], lat: 0.14, footFwd: 0.04, footSize: [0.1, 0.07, 0.13], hip: [0.13, 0.1, 0.02], shoulder: [0.2, 0.47, 0.17], handR: 0.046, hand: [0.27, 0.36, 0.2], front: 0.33, cheek: [0.22, 0.4, 0.33], waddle: 0.08, bob: 0.03, wob: 0.9, mouth: [0, 0.38, 0.34], top: 0.9, faceUp: 0.06, tintK: 0.5,
    face: { ...FACE, ex: 84, ey: 266, rx: 36, ry: 47, my: 330, mw: 15, nostril: 1, eye: '#3a2420', eye2: '#6a4036', blush: '255,150,130' },
    pals: [{ n: '珊瑚龍', body: 0xf08a6c, top: 0xffc9b0, plate: 0xffd35a, tail: 0xe87a5e, sss: 0xff7a50 }, { n: '薄荷龍', body: 0x6cc98a, top: 0xc8f0d4, plate: 0xffb86b, tail: 0x5ab878, sss: 0x30b060 }, { n: '天藍龍', body: 0x7fb0ff, top: 0xd2e6ff, plate: 0xff9fb5, tail: 0x6aa0f4, sss: 0x4a80ff }, { n: '芋紫龍', body: 0xb59af0, top: 0xe6dcff, plate: 0xffd27a, tail: 0xa388e6, sss: 0x8a6bff }],
    anc: { hat: [0, 0.86, 0.04, 0.85], bow: [0.18, 0.8, 0.13], chest: [0, 0.26, 0.31], neck: [0.46, 0.25, 0.24], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.4, y1: 0.45, sss: p.sss, sssAmt: 0.22, rim: 0xffffff, rimAmt: 0.22, face: c.face, headC: [0, 0.03, 0.02], span: [2.1, 2.1] });
      // 身體＝前傾梨形；鼻吻、肩丘、大腿根、尾根、背板底座都是同一張曲面上的高斯鼓包
      const S2 = 0.7071, PD = [[0, 0.85, -0.53], [0, 0.45, -0.89], [0, 0.02, -1]];
      const DB = [[0, 0.1, 1, 0.045, 0.5], [0.8, 0.05, 0.55, 0.035, 0.42], [-0.8, 0.05, 0.55, 0.035, 0.42], [0, -0.38, -0.92, 0.075, 0.55], [0.55, -0.85, 0.05, 0.05, 0.45], [-0.55, -0.85, 0.05, 0.05, 0.45], ...PD.map(d => [d[0], d[1], d[2], 0.022, 0.32])];
      const dsh = (v) => { const bs = bumpS(v, DB), dx = v.x, dy = v.y, dz = v.z, w = 1 + 0.38 * sstep(0.5, -0.7, dy); v.set(dx * 0.27 * w, dy * (dy > 0 ? 0.44 : 0.385), dz * 0.25 * w + 0.11 * sstep(-0.1, 1, dy)); v.x += dx * bs; v.y += dy * bs; v.z += dz * bs; };
      c.main = put(c, blobGeo(dsh, 96, 72), m, 0, 0.46, 0);
      // 背板：大中小三片，底座埋進身體；最大那片從頭頂後方冒出
      const pm = softMat({ color: p.plate, top: p.plate, y0: -0.1, y1: 0.3, sss: p.plate, sssAmt: 0.25, rough: 0.5 }, c.sh);
      [[0, 0.24, 0.095, 0.28], [1, 0.17, 0.08, 0.7], [2, 0.12, 0.066, 1.1]].forEach(([i, L, rb, tl]) => {
        const d = new V3(...PD[i]).normalize(), B = new V3(d.x, d.y, d.z); dsh(B); B.y += 0.46;
        const g = put(c, taperGeo({ q: 0.45, p: 1.2, cap: 0.45, flare: 1.4, fl: 0.25 }), pm, B.x, B.y - 0.03, B.z + 0.012, rb, L, rb * 0.55); g.rotation.x = -tl;
      });
      // 尾巴：根部和身體同粗，往右後方甩出再上翹（正面看得到尾尖），全長前三分之一粗細幾乎不變
      const tl = new V3(0, 0.2, -0.2); c.tail = null;
      const t = piv(c, tl.x, tl.y, tl.z, { k: 120, c: 5.5, g: 0.04, wag: true }); c.tail = c.apps[c.apps.length - 1];
      const tg = tubeGeo({ key: 'dinotail', path: (u) => [0.5 * Math.pow(u, 1.7), 0.02 + 0.2 * Math.pow(u, 2.2), -0.04 - 0.3 * u], rad: (u) => 0.175 * (1 - 0.9 * sstep(0.2, 1, u)) + 0.012, flare: 1.35, fl: 0.18, cap: 0.14, N: 30, S: 18 });
      put(c, tg, MR(c, { color: p.tail, top: p.top, y0: -0.2, y1: 0.3, sss: p.sss, sssAmt: 0.22 }), 0, 0, 0, 1, 1, 1, t);
      c.limbMat = M(c, { color: p.body, top: p.body, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { tic(c, 'whip', 4.5, 1.3, dt, (u, end, st) => { if (st) { c.tail.vz += 9; c.wobV.x += 1.2; } c.idleYaw = end ? 0 : -0.26 * Math.sin(Math.min(1, u * 7) * Math.PI / 2) * (1 - sstep(0.1, 0.3, u)); if (!end && u < 0.5) c.tail.vz += Math.sin(u * 40) * 0.5; }); },
    sig: { dur: 2.0, fn(c, u, a, P) { const e = sstep(0.1, 0.35, u) * (1 - sstep(0.75, 1, u)); P.pitch = -0.22 * e; P.sq = 0.16 * e - 0.1 * (u < 0.1 ? u / 0.1 : 0); P.expr = e > 0.3 ? 'laugh' : 'effort'; P.hands = [1.2, 0.3]; P.wig = 0.4; if (e > 0.3 && !a.f) { a.f = 1; c.say('嗷！', 1.3); c.fx.sfx('boing'); c.tail.vz += 10; c.fx.burst('dust', new V3(c.pos.x, c.pos.y + 0.06, c.pos.z), 6, { speed: 1, up: 0.3, life: 0.45, size: 0.18, grow: 2, drag: 3 }); } } },
  },
  // ───────── 23 圈圈：甜甜圈（立著的環，中間有洞可以看穿，上半是糖霜與彩色糖粒）
  donut: {
    name: '圈圈', sub: '甜甜圈', moveZh: '滾著小跳', sigZh: '滾一圈', why: '全場唯一「中間是空的」：站在後面看得到穿過洞的景色；糖霜與彩色糖粒', memo: '中間有洞的環',
    R: 0.34, move: 'hop', hopH: 0.1, footSize: null, handR: 0.055, hand: [0.4, 0.34, 0.06], top: 0.72, wob: 1.2, mouth: [0, 0.2, 0.15], front: 0.15, cheek: [0.24, 0.22, 0.14], faceShift: 0.35, tintK: 0.5, walk: 1.3, run: 3.0,
    face: { ...FACE, ex: 78, ey: 258, rx: 30, ry: 40, my: 322, mw: 14, line: 6, freck: 0, eye: '#4a2c1c', eye2: '#7a4a30', blush: '255,130,120' },
    pals: [{ n: '草莓糖霜', body: 0xf2c58e, top: 0xff9fbd, spr: [0xffffff, 0xffe35a, 0x7fd6ff, 0x9be37a], sss: 0xe09040 }, { n: '巧克力', body: 0xf0c08a, top: 0x9a6246, spr: [0xffffff, 0xff9fb5, 0xffe35a, 0x7fd6ff], sss: 0xd08040 }, { n: '抹茶', body: 0xf2c88e, top: 0xb6dc8e, spr: [0xffffff, 0xff9fb5, 0xffe35a, 0xc8b0ff], sss: 0xe09040 }, { n: '檸檬', body: 0xf3cb92, top: 0xffe27a, spr: [0xffffff, 0xff9fb5, 0x7fd6ff, 0x9be37a], sss: 0xe09840 }],
    anc: { hat: [0, 0.72, 0, 0.95], bow: [0.22, 0.64, 0.1], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.015, y1: 0.03, sss: p.sss, sssAmt: 0.3, rough: 0.55, rim: 0xffffff, rimAmt: 0.3, face: c.face, headC: [0, -0.22, 0], span: [3.3, 3.3] });
      c.main = put(c, new THREE.TorusGeometry(0.22, 0.125, Math.max(16, Math.round(30 * DETAIL.k)), Math.max(28, Math.round(64 * DETAIL.k))), m, 0, 0.36, 0);
      const sg = new THREE.CapsuleGeometry(0.009, 0.04, 3, 6); let k = 0;
      for (const [ph, th] of [[0.5, 1.0], [0.85, 1.25], [1.2, 0.85], [1.55, 1.2], [1.95, 0.95], [2.3, 1.2], [2.65, 0.9], [0.68, 1.55], [2.05, 1.5]]) {
        const R = 0.22 + 0.125 * Math.cos(th) * 0.92, x = R * Math.cos(ph), y = R * Math.sin(ph), z = 0.125 * Math.sin(th) * 0.98;
        const sp = put(c, sg, M(c, { color: p.spr[k++ % p.spr.length], top: 0xffffff, y0: -1, y1: 1, sss: 0xffffff, sssAmt: 0.12, rough: 0.35 }), x, 0.36 + y, z, 1, 1, 1); sp.rotation.set(0.6 + k * 1.3, k * 2.1, k * 0.9);
      }
      c.limbMat = M(c, { color: p.body, top: p.body, y0: 0, y1: 1, sss: p.sss });
    },
    idle(c, dt, t) { tic(c, 'coin', 6, 1.8, dt, (u, end, st) => { c.rollAdd = end ? 0 : Math.sin(u * Math.PI * 5) * 0.34 * (1 - u); if (st) c.sqV -= 1.5; }); },
    sig: { dur: 2.0, fn(c, u, a, P) { const e = sstep(0.1, 0.85, u); P.spinZ = -e * Math.PI * 2; P.yOff = Math.sin(e * Math.PI) * 0.12; P.expr = 'whee'; P.sq = u < 0.1 ? -0.16 * u / 0.1 : 0.04; if (!a.f) { a.f = 1; c.fx.sfx('whee'); } if (c.every('sg', 0.1)) c.fx.spawn('spark', c.headTop(new V3()).add(_v.set(rnd(-0.3, 0.3), rnd(-0.5, 0), 0)), { life: 0.5, size: 0.09 }); } },
  },
  // ───────── 24 蠕蠕：毛毛蟲（好幾節疊成一串、大腦袋、兩根觸角，身體會依序擺動）
  worm: {
    name: '蠕蠕', sub: '站著的毛毛蟲', moveZh: '一節一節走', sigZh: '蠕動波浪', why: '全場唯一由好幾節圓球疊成的剪影，節與節之間會依序擺動', memo: '多節疊起來的身體',
    pat: ['stripes', 'spots'], R: 0.28, stride: [0.4, 0.9], lat: 0.09, footFwd: 0.02, footSize: [0.07, 0.05, 0.095], handR: 0.05, hand: [0.27, 0.48, 0.06], front: 0.28, cheek: [0.2, 0.84, 0.27], waddle: 0.09, bob: 0.03, wob: 0.6, mouth: [0, 0.74, 0.28], top: 1.06, tintK: 0.5, faceUp: 0.04,
    face: { ...FACE, ex: 76, ey: 258, rx: 30, ry: 40, my: 320, mw: 14, eye: '#26382c', eye2: '#4a6a52', blush: '255,140,130' },
    pals: [{ n: '青蘋果', body: 0xb9e48c, top: 0xf0fcd8, seg: 0x96d070, tip: 0xff9fb5, sss: 0x70c040 }, { n: '蜜柑', body: 0xffcf86, top: 0xfff0cc, seg: 0xffb458, tip: 0x9db8ff, sss: 0xffa030 }, { n: '莓果', body: 0xffb3c8, top: 0xffe6ee, seg: 0xf58fae, tip: 0xffe08a, sss: 0xff6a98 }, { n: '薰衣草', body: 0xcdb9f2, top: 0xf2ebff, seg: 0xb09ae6, tip: 0xa8f0d0, sss: 0x9a7bff }],
    anc: { hat: [0, 1.03, 0.02, 0.85], bow: [0.2, 0.96, 0.1], chest: [0, 0.52, 0.2], neck: [0.64, 0.24, 0.22], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.28, y1: 0.28, sss: p.sss, sssAmt: 0.3, rim: 0xffffff, face: c.face, headC: [0, 0.02, 0], span: [2.15, 2.15] });
      c.main = put(c, blobGeo(v => v.set(v.x * 0.285, v.y * 0.27, v.z * 0.265)), m, 0, 0.8, 0); c.wseg = [c.main];
      c.wbase = [0];
      [[0.52, 0.205, 0], [0.34, 0.195, 1], [0.18, 0.17, 0], [0.075, 0.13, 1]].forEach(([y, r, alt], i) => { const sm = M(c, { color: alt ? p.seg : p.body, top: alt ? p.body : p.top, y0: -0.2, y1: 0.2, sss: p.sss, sssAmt: 0.28, rough: 0.6 }); const g = put(c, blobGeo(v => v.set(v.x * r, v.y * r * 0.92, v.z * r * 0.95), 48, 36), sm, 0, y, 0); c.wseg.push(g); c.wbase.push(0); });
      const tm = M(c, { color: p.tip, top: 0xffffff, y0: -1, y1: 1, sss: p.tip, sssAmt: 0.4, rough: 0.35 }), am = M(c, { color: p.seg, top: p.body, y0: -1, y1: 1, sss: p.sss });
      for (const s of [-1, 1]) { const g = piv(c, s * 0.1, 1.03, 0, { side: s, k: 85, c: 4.6, g: 0.03, rest: [0.05, s * 0.4], droop: 0.5 }); c.wseg.push(g); c.wbase.push(null); rod(c, am, [0, 0, 0], [0, 0.15, 0], 0.012, g); put(c, ball(), tm, 0, 0.17, 0, 0.04, 0.04, 0.04, g); }
      c.limbMat = M(c, { color: p.seg, top: p.body, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) {
      let amp = 0.01, sp = 2.2; tic(c, 'wave', 5.5, 2.0, dt, (u, end) => { c.wA = end ? 0 : Math.sin(u * Math.PI); });
      c.wA = c.wA || 0; amp += 0.05 * c.wA; sp += 5 * c.wA;
      for (let i = 0; i < 5; i++) { const s = c.wseg[i]; s.position.x = amp * Math.sin(t * sp - i * 0.9); if (c.wA > 0.02) s.position.y += 0; }
    },
    sig: { dur: 2.0, fn(c, u, a, P) { c.wA = Math.sin(u * Math.PI); P.sq = 0.1 * Math.sin(u * Math.PI * 4); P.expr = 'happy'; P.hands = [1.2, 0.3]; P.wig = 0.5; if (c.every('sg', 0.4)) c.fx.sfx('boing'); } },
  },
  // ───────── 25 垂垂：長耳兔（一隻耳朵站直、一隻從中間折下來垂著，圓尾巴、前面露出兩隻大腳）
  bunny: {
    name: '垂垂', sub: '一高一垂的長耳兔', moveZh: '蹦蹦跳', sigZh: '耳朵轉圈', why: '兩隻長耳朵一隻站、一隻折下來垂著（不對稱），耳朵會各自彈；白球尾巴＋前面兩隻大腳', memo: '一站一垂的長耳朵',
    pat: ['patch', 'spots', 'belly'], R: 0.3, move: 'hop', hopH: 0.17, footSize: null, handR: 0.05, hand: [0.31, 0.3, 0.14], front: 0.3, cheek: [0.21, 0.4, 0.3], wob: 1.3, mouth: [0, 0.34, 0.31], top: 1.0, faceUp: 0.08, tintK: 0.5, walk: 1.5, run: 3.5,
    face: { ...FACE, ex: 82, ey: 266, rx: 32, ry: 42, my: 326, mw: 16, wmouth: true, eye: '#3a2630', eye2: '#6e4658', blush: '255,130,150' },
    pals: [{ n: '奶油兔', body: 0xffe8d6, top: 0xfffaf2, ear: 0xffbfc8, sss: 0xffa088 }, { n: '灰藍兔', body: 0xc9d4ea, top: 0xf2f5ff, ear: 0xffc0d0, sss: 0x90a8e0 }, { n: '焦糖兔', body: 0xeab98a, top: 0xffe6c8, ear: 0xffd0c0, sss: 0xd08850 }, { n: '櫻花兔', body: 0xffc8d8, top: 0xfff0f4, ear: 0xffe6a8, sss: 0xff80a0 }],
    anc: { hat: [0, 0.74, 0.03, 0.75], bow: [-0.2, 0.62, 0.14], chest: [0, 0.2, 0.3], neck: [0.3, 0.26, 0.25], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.3, y1: 0.34, sss: p.sss, sssAmt: 0.28, rim: 0xffffff, face: c.face, headC: [0, 0.08, 0], span: [2.15, 2.15] });
      c.main = put(c, blobGeo(v => { const y = v.y, w = 1 + 0.14 * sstep(0.3, -0.8, y); v.set(v.x * 0.315 * w, y * (y > 0 ? 0.35 : 0.3), v.z * 0.3 * w); }, 88, 64), m, 0, 0.42, 0);
      const em = MR(c, { color: p.body, top: p.top, y0: 0, y1: 0.4, sss: p.sss, sssAmt: 0.3 }), im = M(c, { color: p.ear, top: 0xffffff, y0: 0, y1: 0.4, sss: p.ear, sssAmt: 0.3 });
      const g1 = piv(c, -0.115, 0.74, -0.02, { side: -1, k: 140, c: 7, g: 0.018, rest: [0, 0.14], droop: 0.35 }); c.earL = c.apps[c.apps.length - 1];
      put(c, taperGeo({ q: 0.5, p: 1.5, cap: 0.4 }), em, 0, -0.05, 0, 0.088, 0.48, 0.055, g1); put(c, ball(), im, 0, 0.2, 0.02, 0.043, 0.17, 0.02, g1);
      const g2 = piv(c, 0.115, 0.74, -0.02, { side: 1, k: 110, c: 6, g: 0.02, rest: [0, -0.1], droop: 0.35 }); c.earR = c.apps[c.apps.length - 1];
      put(c, taperGeo({ q: 0.6, p: 1.5, cap: 0.5 }), em, 0, -0.05, 0, 0.088, 0.27, 0.055, g2); put(c, ball(), im, 0, 0.1, 0.02, 0.043, 0.085, 0.02, g2);
      const f = new THREE.Group(); f.position.set(0, 0.2, 0); f.rotation.z = -1.5; g2.add(f); put(c, ball(), em, 0, 0.12, 0, 0.07, 0.15, 0.042, f); put(c, ball(), im, 0, 0.12, 0.02, 0.04, 0.1, 0.02, f);
      const t = piv(c, 0, 0.2, -0.3, { k: 160, c: 8, g: 0.03, wag: true }); put(c, ball(), MR(c, { color: 0xffffff, top: 0xffffff, sss: 0xffd0d8, sssAmt: 0.2, rough: 0.9 }), 0, 0.01, -0.05, 0.095, 0.095, 0.095, t);
      for (const s of [-1, 1]) { put(c, blobGeo(v => { v.y = v.y * (v.y < 0 ? 0.5 : 1) + 0.5; v.z += 0.1 * (1 - Math.abs(v.y - 0.5)); }, 36, 24), em, s * 0.14, 0.015, 0.16, 0.075, 0.08, 0.125).rotation.y = s * 0.15; limbTo(c, em, [s * 0.12, 0.25, 0.06], [s * 0.14, 0.07, 0.15], 0.085, { q: 0.75, p: 1.4 }); }
      c.limbMat = em;
    },
    idle(c, dt, t) { tic(c, 'ear', 3.4, 1.0, dt, (u, end, st) => { if (st) { c.earL.vz += (Math.random() < 0.5 ? 1 : -1) * 6; c.earR.vz += 3; c.earR.vx -= 4; } if (!end && u > 0.4 && u < 0.45) c.earL.vz += 3; }); },
    sig: { dur: 1.9, fn(c, u, a, P) { const b = Math.abs(Math.sin(a.t * 8)); P.yOff = b * 0.22; P.sq = 0.18 * b - 0.1 * (1 - b); P.expr = 'whee'; P.wig = 0.6; c.earL.vz += Math.sin(a.t * 20) * 0.6; if (c.every('sg', 0.4)) c.fx.sfx('boing'); } },
  },
};
export const SPECIES_IDS = Object.keys(SPECIES);
for (const id of SPECIES_IDS) SPECIES[id] = { id, ...DEF, ...SPECIES[id] };

export const ACCESSORIES = [['glasses', '眼鏡'], ['hat', '帽子'], ['bow', '蝴蝶結'], ['tie', '領帶'], ['scarf', '圍巾'], ['badge', '識別證'], ['crown', '小皇冠']];
const ACC_COL = [0xff8f9f, 0x7fb0ff, 0xffc85a, 0x7fd6b0, 0xb49af0, 0xff9f6a];

// 個體規格 → 完整設定。spec：{ species, pal(配色編號或名稱), hue(-0.08~0.08 色相微調), acc:['glasses','tie'…], accColor(編號) }
export function resolveSpec(spec) {
  if (typeof spec === 'string') spec = { species: spec };
  const cfg = SPECIES[spec.species] || SPECIES.mochi;
  let pi = typeof spec.pal === 'string' ? cfg.pals.findIndex(p => p.n === spec.pal) : (spec.pal | 0); if (pi < 0) pi = 0;
  const pal = { ...cfg.pals[pi % cfg.pals.length] };
  if (spec.hue) { const c = new THREE.Color(), h = {}; for (const k in pal) if (typeof pal[k] === 'number') { c.setHex(pal[k]); c.getHSL(h); c.setHSL((h.h + spec.hue + 1) % 1, h.s, h.l); pal[k] = c.getHex(); } }
  return { cfg, pal, palIndex: pi % cfg.pals.length, acc: (spec.acc || []).filter(a => canWear(cfg, a)), v: traitsOf(spec.seed, cfg), accColor: typeof spec.accColor === 'string' ? new THREE.Color(spec.accColor).getHex() : ACC_COL[(spec.accColor | 0) % ACC_COL.length], spec };
}
// ── 個體差異：由 spec.seed（辦公室用成員 id 的雜湊）決定，固定不變；沒有 seed 就是「標準款」
const mulberry = (a) => () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const IRIS = ['#5b8cff', '#2fae9a', '#9a6bff', '#c0702a', '#e0508a', '#3a9b5c'];
const PAT_K = { spots: 0, stripes: 2, patch: 3, belly: 4 };
const NEUTRAL = { sx: 1, sy: 1, pat: null, brow: 0, tooth: 0, freck: 0, eyeK: 1, iris: null, buttons: 0, patS: 5, patA: 0.7, patSeed: 0, patHue: 0, patL: 0 };
export function traitsOf(seed, cfg) {
  if (!seed) return NEUTRAL;
  const r = mulberry(seed), f = (a, b) => a + (b - a) * r(), pl = cfg.pat || [];
  const pat = pl.length && r() < 0.66 ? pl[Math.floor(r() * pl.length)] : (r(), null);
  return { sx: f(0.93, 1.07), sy: f(0.92, 1.09), pat, patS: f(5, 7.5), patA: f(0.8, 1), patSeed: r() * 20, patHue: f(-0.05, 0.05), patL: (r() < 0.5 ? -1 : 1) * f(0.13, 0.22), brow: r() < 0.55 ? f(0.5, 0.85) : (r(), 0), tooth: r() < 0.2 ? 1 : 0, freck: r() < 0.3 ? 1 : 0, eyeK: f(0.92, 1.1), iris: r() < 0.6 ? IRIS[Math.floor(r() * IRIS.length)] : (r(), null), buttons: r() < 0.28 ? 1 : 0 };
}
const lighten = (hex, k) => '#' + new THREE.Color(hex).lerp(new THREE.Color(0xffffff), k).getHexString();
// 臉的樣式：標準款加上個體差異（眼睛大小、虹膜色、眉毛、虎牙、雀斑）
export function faceStyleFor(st, v) {
  const o = { ...st, iris: st.iris ?? v.iris ?? lighten(st.eye2 || '#6e4638', 0.18), restBrow: v.brow, tooth: v.tooth, freck: v.freck };
  if (v.eyeK !== 1 && !st.visor) { o.rx = st.rx * v.eyeK; o.ry = st.ry * v.eyeK; }
  return o;
}
// 建完身體後套上個體特徵：花紋（斑點／條紋／縫線補丁／肚皮）、鈕扣
export function applyTraits(c, rs) {
  const v = rs.v, cfg = rs.cfg, U = c.main && c.main.material.userData.U; if (!v || !U) return;
  if (v.pat) {
    c.main.geometry.computeBoundingBox(); const bb = c.main.geometry.boundingBox, w = bb.max.x - bb.min.x, h = bb.max.y - bb.min.y, k = PAT_K[v.pat];
    const base = new THREE.Color(rs.pal.body ?? rs.pal.acc ?? 0xffffff), hsl = {}; base.getHSL(hsl);
    const col = k === 4 ? new THREE.Color(0xfff4e4).lerp(base, 0.12) : k === 3 ? new THREE.Color().setHSL((hsl.h + 0.33 + v.patHue) % 1, Math.min(0.55, hsl.s), 0.8) : new THREE.Color().setHSL((hsl.h + v.patHue + 1) % 1, Math.min(1, hsl.s * 1.08), Math.max(0.3, Math.min(0.95, hsl.l + v.patL)));
    U.uPat.value.set(k, v.patA, v.patS, v.patSeed); U.uPatCol.value.copy(col);
    if (k === 3) { U.uPatC.value.set(bb.min.x * 0.42, bb.min.y + h * 0.3, 0); U.uPatR.value = 0.19 * w; }
    else if (k === 4) { U.uPatC.value.set(0, bb.min.y + h * 0.3, 0); U.uPatR.value = 0.3 * w; }
  }
  const ch = cfg.anc.chest;
  if (v.buttons && ch && !rs.acc.includes('tie') && !rs.acc.includes('badge') && !v.pat) {
    const bm = M(c, { color: 0xfff6e6, top: 0xffffff, y0: -1, y1: 1, sss: 0xffd0a0, sssAmt: 0.15, rough: 0.35 }), dm = M(c, { color: 0x6a5a55, sss: 0x6a5a55, sssAmt: 0.05 });
    const bt = [], hl = []; for (const dy of [0.05, -0.04]) { bt.push([_lb(), ch[0], ch[1] + dy, ch[2], 0.026, 0.026, 0.012]); for (const dx of [-0.007, 0.007]) hl.push([_lb(), ch[0] + dx, ch[1] + dy + 0.007, ch[2] + 0.009, 0.004, 0.004, 0.003]); }
    mrg(c, bm, bt); mrg(c, dm, hl);
  }
}
export function canWear(cfg, a) { const n = cfg.anc; return a === 'glasses' ? !!n.glasses : a === 'hat' || a === 'crown' ? !!n.hat : a === 'bow' ? !!n.bow : a === 'tie' || a === 'badge' ? !!n.chest : a === 'scarf' ? !!n.neck : false; }

// 把同一種材質的小零件合併成一個網格（辦公室幾十隻同場，繪製呼叫數要省）
// items：[幾何, x,y,z, sx,sy,sz, rx,ry,rz]
const _m4 = new THREE.Matrix4(), _q = new THREE.Quaternion(), _e = new THREE.Euler(), _p = new V3(), _s = new V3(), _n3 = new THREE.Matrix3();
function mrg(c, mat, items, parent = null) {
  const pos = [], nor = [], idx = []; let off = 0;
  for (const [g, x = 0, y = 0, z = 0, sx = 1, sy = sx, sz = sx, rx = 0, ry = 0, rz = 0] of items) {
    _m4.compose(_p.set(x, y, z), _q.setFromEuler(_e.set(rx, ry, rz)), _s.set(sx, sy, sz)); _n3.getNormalMatrix(_m4);
    const P = g.attributes.position, N = g.attributes.normal, v = new V3();
    for (let i = 0; i < P.count; i++) { v.fromBufferAttribute(P, i).applyMatrix4(_m4); pos.push(v.x, v.y, v.z); v.fromBufferAttribute(N, i).applyMatrix3(_n3).normalize(); nor.push(v.x, v.y, v.z); }
    if (g.index) for (let i = 0; i < g.index.count; i++) idx.push(g.index.getX(i) + off); else for (let i = 0; i < P.count; i++) idx.push(i + off);
    off += P.count;
  }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); geo.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3)); geo.setIndex(idx);
  const m = new THREE.Mesh(geo, mat); (parent || c.deform).add(m); return m;
}
const _box = (() => { let g; return () => g || (g = new THREE.BoxGeometry(1, 1, 1)); })();
const _lb = (() => { let g; return () => g || (g = new THREE.SphereGeometry(1, 10, 7)); })();
const _tor = (() => { let g; return () => g || (g = new THREE.TorusGeometry(1, 0.24, 12, 40)); })();

// 配件：位置由各物種的 anc 決定，掛在會跟著身體擠壓的那一層
// 做工：布料（帽、蝴蝶結、圍巾）霧面、邊緣光很弱；領帶偏絲質；識別證、皇冠偏塑膠／金屬；加縫線、飾帶、標籤、流蘇、條紋等小細節
export function addAccessories(c, list, col) {
  const n = c.cfg.anc, o = { color: col, top: 0xffffff, y0: -1, y1: 4, sss: col, sssAmt: 0.25 };
  const cloth = M(c, { ...o, rough: 0.95, rimAmt: 0.16, sssAmt: 0.14 }), silk = M(c, { ...o, rough: 0.4, rimAmt: 0.4 }), m = M(c, o), wm = M(c, { color: 0xfffaf2, sss: 0xffd0a0, rough: 0.92, rimAmt: 0.15 });
  const dk = M(c, { color: 0x6a5a55, sss: 0x6a5a55, sssAmt: 0.05, rough: 0.5 });
  for (const a of list) {
    if (a === 'glasses') { c.face.st.glasses = '#' + new THREE.Color(col).multiplyScalar(0.55).getHexString(); c.face.dirty = true; }
    else if (a === 'hat') {
      const [x, y, z, s] = n.hat, g = piv(c, x, y, z, { k: 260, c: 14, g: 0.008 }); g.scale.setScalar(s);
      mrg(c, cloth, [[blobGeo(v => v.set(v.x * 0.15, Math.max(v.y, -0.25) * 0.105, v.z * 0.15), 40, 28), 0, 0.02, 0], [ball(), 0, 0.005, 0.13, 0.11, 0.014, 0.085]], g);
      const st = []; for (let i = 0; i < 5; i++) { const an = -0.7 + i * 0.35; st.push([_box(), Math.sin(an) * 0.148, 0.0, Math.cos(an) * 0.148, 0.02, 0.004, 0.004, 0, an, 0]); }
      mrg(c, wm, [[_lb(), 0, 0.125, 0, 0.03, 0.024, 0.03], [_tor(), 0, 0.006, 0, 0.146, 0.05, 0.146, Math.PI / 2, 0, 0], [_box(), -0.152, -0.015, 0.03, 0.034, 0.042, 0.008, 0, 1.2, 0], ...st], g);
      g.rotation.x = -0.12; c.apps[c.apps.length - 1].rest = [-0.12, 0.1];
    }
    else if (a === 'crown') { if (list.includes('hat')) continue; const [x, y, z, s] = n.hat, g = piv(c, x, y, z, { k: 260, c: 14, g: 0.008 }); g.scale.setScalar(s * 0.9); const gm = M(c, { color: 0xffd04a, top: 0xfff2a0, y0: -1, y1: 4, sss: 0xffa020, sssAmt: 0.4, rough: 0.32 }); put(c, new THREE.TorusGeometry(0.1, 0.03, 14, 40), gm, 0, 0.03, 0, 1, 1, 1.25, g).rotation.x = Math.PI / 2; for (let i = 0; i < 5; i++) { const an = i * 1.2566 + Math.PI / 2; put(c, ball(), gm, Math.cos(an) * 0.1, 0.085, Math.sin(an) * 0.1, 0.034, 0.06, 0.034, g); put(c, ball(), i % 2 ? wm : M(c, { color: 0xff7f9c, sss: 0xff4070, rough: 0.2 }), Math.cos(an) * 0.1, 0.15, Math.sin(an) * 0.1, 0.02, 0.02, 0.02, g); } g.rotation.x = -0.1; c.apps[c.apps.length - 1].rest = [-0.1, 0.08]; }
    else if (a === 'bow') {
      const [x, y, z] = n.bow, g = piv(c, x, y, z, { k: 240, c: 12, g: 0.01, rest: [0, -0.3] });
      mrg(c, cloth, [[ball(), -0.05, 0, 0, 0.055, 0.042, 0.026, 0, 0, -0.3], [ball(), 0.05, 0, 0, 0.055, 0.042, 0.026, 0, 0, 0.3], [_lb(), -0.022, -0.05, -0.004, 0.02, 0.05, 0.014, 0, 0, 0.3], [_lb(), 0.022, -0.05, -0.004, 0.02, 0.05, 0.014, 0, 0, -0.3]], g);
      mrg(c, silk, [[_lb(), 0, 0, 0.012, 0.028, 0.03, 0.028]], g);
      mrg(c, wm, [-1, 1].flatMap(sd => [-0.01, 0.012].map(dx => [_box(), sd * (0.05 + dx), 0.008, 0.022, 0.011, 0.003, 0.003, 0, 0, sd * 0.3])), g);
    }
    else if (a === 'tie') {
      const [x, y, z] = n.chest, g = piv(c, x, y + 0.07, z, { k: 120, c: 6, g: 0.03 });
      mrg(c, silk, [[_lb(), 0, 0, 0.012, 0.03, 0.026, 0.02], [blobGeo(v => { const w = 0.6 + 0.4 * (1 - Math.abs(v.y + 0.3)); v.set(v.x * 0.04 * w, v.y * 0.075, v.z * 0.014); }, 24, 16), 0, -0.085, 0.016]], g);
      mrg(c, wm, [-0.05, -0.085, -0.12].map(yy => [_box(), 0, yy, 0.03, 0.062, 0.007, 0.004, 0, 0, 0.45]), g);
    }
    else if (a === 'badge') {
      const [x, y, z] = n.chest, g = piv(c, x + 0.1, y + 0.04, z - 0.01, { k: 140, c: 7, g: 0.02 });
      put(c, rbox(0.085, 0.105, 0.014, 0.006, 2), wm, 0, -0.03, 0.012, 1, 1, 1, g); put(c, rbox(0.085, 0.03, 0.016, 0.006, 2), m, 0, 0.005, 0.013, 1, 1, 1, g);
      mrg(c, dk, [[_lb(), 0, -0.004, 0.022, 0.017, 0.017, 0.004], [_box(), 0, 0.03, 0.016, 0.034, 0.014, 0.012], [_box(), 0.004, -0.062, 0.021, 0.05, 0.006, 0.003], [_box(), -0.006, -0.076, 0.021, 0.036, 0.006, 0.003]], g);
      put(c, _lb(), M(c, { color: 0xf2c9a4, sss: 0xff9070, sssAmt: 0.15 }), 0, -0.03, 0.022, 0.022, 0.024, 0.004, g);
    }
    else if (a === 'scarf') {
      const [y, rx, rz, tk = 0.06] = n.neck, g = piv(c, rx * 0.5, y - 0.03, rz * 0.82, { k: 90, c: 5, g: 0.04 });
      mrg(c, cloth, [[_tor(), 0, y, 0, rx * 0.84, rz * 0.84, tk / 0.24 * 1.25, Math.PI / 2, 0, 0]]);
      mrg(c, cloth, [[_lb(), 0, -0.07, 0.03, 0.045, 0.09, 0.025]], g);
      mrg(c, wm, [[_box(), 0, -0.05, 0.052, 0.088, 0.012, 0.004], [_box(), 0, -0.09, 0.052, 0.088, 0.012, 0.004], ...[-0.03, 0, 0.03].map(fx => [_box(), fx, -0.17, 0.03, 0.01, 0.036, 0.01]), [_box(), 0.062, -0.1, 0.03, 0.024, 0.03, 0.006, 0, 0, 0.15]], g);
    }
  }
}
