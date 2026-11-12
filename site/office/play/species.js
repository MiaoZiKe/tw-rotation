// 物種圖鑑：每個物種＝一份資料（尺寸、移動方式、配色表、配件位置）＋一個組裝函式＋待機小動作＋招牌動作
// 全部原創；個體差異由 spec = { species, pal, hue, acc:[...] } 決定（見 resolveSpec）
import * as THREE from 'three';
import { softMat, blobGeo, ball, sstep, clamp } from './soft.js';
import { lathe, rbox } from './world.js';

const V3 = THREE.Vector3, _v = new V3();
const M = (c, o) => softMat(o, c.sh);
const put = (c, geo, mat, x = 0, y = 0, z = 0, sx = 1, sy = sx, sz = sx, parent = null) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.scale.set(sx, sy, sz); (parent || c.deform).add(m); return m; };
const piv = (c, x, y, z, o = {}) => { const g = new THREE.Group(); g.position.set(x, y, z); c.deform.add(g); c.apps.push({ piv: g, side: 0, k: 150, c: 9, g: 0.02, gy: 0, rest: [0, 0], droop: 0, ...o }); return g; };
const rnd = (a, b) => a + Math.random() * (b - a);
const every = (c, key, sec, dt) => { c.tm ??= {}; c.tm[key] = (c.tm[key] ?? Math.random() * sec) - dt; if (c.tm[key] <= 0) { c.tm[key] = sec * rnd(0.7, 1.3); return true; } return false; };
const calm = (c) => c.mode === 'normal' && c.grounded && !c.act;

// 共用預設值（單位公尺；原點在腳底、面朝 +z）
const DEF = {
  R: 0.33, walk: 1.5, run: 3.6, jumpV: 5.8, stride: [0.46, 1.0], lat: 0.12, footFwd: 0.03, footSize: [0.085, 0.06, 0.11], handR: 0.06, hand: [0.33, 0.3, 0.05],
  front: 0.33, cheek: [0.22, 0.45, 0.3], waddle: 0.06, bob: 0.03, wob: 1, mouth: [0, 0.4, 0.33], top: 0.8, move: 'walk', hopH: 0.12, floatH: 0, tintK: 1, anc: {},
};
const FACE = { ex: 88, ey: 262, rx: 34, ry: 44, my: 320, mw: 16, line: 7, eye: '#3a2622', eye2: '#6e4638', blush: '255,132,140' };

export const SPECIES = {
  // ───────── 1 糰糰：麻糬糰子（頭就是身體，圓耳朵、短尾巴）
  mochi: {
    name: '糰糰', sub: '麻糬糰子', moveZh: '小碎步', sigZh: '彈彈跳', why: '頭就是身體，臉最大、擠壓伸展最誇張',
    R: 0.36, walk: 1.5, run: 3.5, jumpV: 5.7, stride: [0.42, 0.9], lat: 0.15, footFwd: 0.2, footSize: [0.082, 0.062, 0.1], handR: 0.062,
    stick: [0.475, 0.37, 0.445, 0.335], hand: [0.45, 0.2, 0.17], front: 0.4, cheek: [0.26, 0.3, 0.36], waddle: 0.085, wob: 1.25, mouth: [0, 0.24, 0.42], top: 0.72, faceUp: 0.14,
    face: { ...FACE, ex: 92, rx: 36, ry: 47, my: 322, mw: 17, wmouth: true },
    pals: [{ n: '奶油桃', body: 0xffc9ad, top: 0xfff1e2, acc: 0xffbfa6, sss: 0xff8f6e }, { n: '草莓牛奶', body: 0xffb4c6, top: 0xffe8ef, acc: 0xff9db6, sss: 0xff6f9a }, { n: '抹茶', body: 0xc3e0ad, top: 0xeff8de, acc: 0xa5d291, sss: 0x8fd070 }, { n: '芋頭', body: 0xcdb9f0, top: 0xf2ebff, acc: 0xb7a0ea, sss: 0x9a7bff }],
    anc: { hat: [0, 0.7, 0.02, 1], bow: [0.2, 0.66, 0.12], chest: [0, 0.1, 0.43], glasses: 1 },
    build(c, p) {
      const m = M(c, { color: p.body, top: p.top, y0: -0.36, y1: 0.25, sss: p.sss, sssAmt: 0.27, face: c.face, headC: [0, 0, 0], span: [2.2, 2.2] });
      c.main = put(c, blobGeo(v => { const y = v.y, b = 1 + 0.15 * sstep(0.4, -0.7, y); v.set(v.x * 0.455 * b, y * (y > 0 ? 0.385 : 0.345), v.z * 0.425 * b); }), m, 0, 0.335, 0);
      const em = M(c, { color: p.acc, top: p.top, y0: -0.4, y1: 0.9, sss: p.sss });
      for (const s of [-1, 1]) { const g = piv(c, s * 0.25, 0.62, -0.02, { side: s, g: 0.016, gy: 0.012, rest: [0, s * -0.22], droop: 0.75 }); put(c, ball(), em, 0, 0.065, 0, 0.105, 0.1, 0.07, g); }
      const t = piv(c, 0.06, 0.2, -0.4, { k: 220, c: 10, g: 0.03, wag: true }); put(c, ball(), em, 0, 0, -0.04, 0.075, 0.075, 0.075, t);
      c.limbMat = M(c, { color: p.acc, top: p.top, y0: 0, y1: 1.6, sss: p.sss });
    },
    idle(c, dt, t) { if (calm(c) && every(c, 'ear', 3.2, dt)) for (const a of c.apps) if (a.side) a.vz += a.side * 5; },
    sig: { dur: 1.9, fn(c, u, a, P) { const b = Math.abs(Math.sin(a.t * 9)); P.yOff = b * 0.16 * (1 - u * 0.3); P.sq = 0.16 * b - 0.14 * (1 - b); P.expr = 'laugh'; P.wig = 0.5; if (c.every('sg', 0.35)) c.fx.sfx('boing'); } },
  },
  // ───────── 2 豆芽：豆子小人（有手有腳，頭頂一大一小兩片葉子）
  bean: {
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
    },
    idle(c, dt, t) { c.sprout.scale.setScalar(c.sprout.scale.x + ((c.sproutBig ? 2.1 : 1.3) - c.sprout.scale.x) * Math.min(1, dt * 8)); c.sproutBig = false; },
    sig: { dur: 2.0, fn(c, u, a, P) { c.sproutBig = u > 0.2 && u < 0.85; P.sq = u < 0.2 ? -0.2 * u / 0.2 : 0.1 * (1 - u); P.expr = u < 0.2 ? 'effort' : 'happy'; P.hands = [1.25, 0.25]; if (u > 0.2 && !a.f) { a.f = 1; c.fx.sfx('boing'); c.fx.burst('spark', c.headTop(new V3()).add(_v.set(0, 0.2, 0)), 6, { speed: 0.9, up: 0.6, life: 0.5, size: 0.12 }); } } },
  },
  // ───────── 3 啵啵：圓頭小機器人（發光的臉、彈簧天線、浮空的手）
  robo: {
    name: '啵啵', sub: '圓頭機器人', moveZh: '踩步走', sigZh: '掃描', why: '發光的臉表情最清楚，像辦公室小助理',
    R: 0.33, stride: [0.46, 1.0], lat: 0.115, handR: 0.066, hand: [0.31, 0.25, 0.05], front: 0.34, cheek: [0.24, 0.5, 0.33], wob: 0.6, mouth: [0, 0.44, 0.36], top: 0.95,
    face: { kind: 'screen', ex: 78, ey: 262, rx: 27, ry: 34, my: 312, mw: 15, line: 6, glow: '#9ff4ff', blush: '255,140,190', blushAmt: 0.9, visor: { w: 392, h: 236, y: 152, r: 108, c0: '#1d2444', c1: '#303a6b' } },
    pals: [{ n: '薰衣草', acc: 0x9db2ff, acc2: 0xc3d0ff, tip: 0xffb3c8, glow: '#9ff4ff' }, { n: '蜜桃', acc: 0xffa9b8, acc2: 0xffd0d8, tip: 0xffe08a, glow: '#ffd9a8' }, { n: '薄荷', acc: 0x8fdcc4, acc2: 0xc0f0e0, tip: 0xffb3c8, glow: '#a8ffd8' }, { n: '奶油黃', acc: 0xffd27a, acc2: 0xffe8b0, tip: 0x9db2ff, glow: '#fff3a8' }],
    anc: { hat: [0.12, 0.84, 0.05, 0.8], bow: [0.22, 0.84, 0.08], chest: [0, 0.27, 0.19], neck: [0.31, 0.18, 0.17], glasses: 0 },
    build(c, p) {
      c.face.st.glow = p.glow;
      const white = { color: 0xe6e6fb, top: 0xfdfcff, sss: 0xa9b6ff, sssAmt: 0.22, rim: 0xffffff, rough: 0.42 };
      const m = M(c, { ...white, y0: -0.3, y1: 0.25, face: c.face, headC: [0, -0.02, 0], span: [2.35, 2.35], glow: 0.8 });
      c.main = put(c, blobGeo(v => { const rh = Math.hypot(v.x, v.z) || 1e-6, k = Math.pow(rh, 0.86) / rh; v.set(v.x * k * 0.385, v.y * 0.315, v.z * k * 0.355); }), m, 0, 0.58, 0);
      const bm = M(c, { ...white, y0: -0.2, y1: 0.2 });
      put(c, blobGeo(v => { const b = 1 + 0.12 * sstep(0.3, -0.8, v.y); v.set(v.x * 0.215 * b, v.y * 0.19, v.z * 0.195 * b); }, 48, 36), bm, 0, 0.2, 0);
      const am = M(c, { color: p.acc, top: p.acc2, y0: -1, y1: 1, sss: p.acc, sssAmt: 0.3, rough: 0.45 });
      for (const s of [-1, 1]) put(c, ball(), am, s * 0.375, 0.58, 0, 0.05, 0.105, 0.105);
      c.belt = put(c, ball(), am, 0, 0.23, 0.185, 0.05, 0.05, 0.025);
      const g = piv(c, 0, 0.88, 0, { k: 95, c: 5, g: 0.035 });
      put(c, new THREE.CylinderGeometry(0.012, 0.016, 0.15, 12), bm, 0, 0.07, 0, 1, 1, 1, g);
      c.tipMat = M(c, { color: p.tip, top: 0xffffff, y0: -1, y1: 2.5, sss: p.tip, sssAmt: 0.6, rough: 0.35 }); put(c, ball(), c.tipMat, 0, 0.17, 0, 0.052, 0.052, 0.052, g);
      c.limbMat = am;
    },
    idle(c, dt, t) { c.tipMat.userData.U.uSssAmt.value = 0.5 + 0.5 * Math.pow(Math.max(0, Math.sin(t * 2.2)), 6) + (c.scan ? 1.2 : 0); c.scan = false; },
    sig: { dur: 2.2, fn(c, u, a, P) { c.scan = true; P.yaw = Math.sin(u * Math.PI * 2) * 0.9; P.expr = 'look'; P.sq = 0.06; P.hands = [1.2, 0.1]; if (c.every('sg', 0.3)) c.fx.sfx('ui'); if (u > 0.9 && !a.f) { a.f = 1; c.say('掃描完成！', 1.4); c.emote('happy', 1.4); } } },
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
    name: '刺刺', sub: '盆栽仙人掌', moveZh: '連盆跳', sigZh: '開花', why: '最高的直立剪影，一高一低的手臂很好認',
    R: 0.3, move: 'hop', hopH: 0.09, footSize: null, handR: 0, top: 1.0, wob: 0.75, mouth: [0, 0.56, 0.22], front: 0.24, tintK: 0.45, faceUp: 0.06, walk: 1.3, run: 3.1,
    face: { ...FACE, ex: 62, ey: 262, rx: 26, ry: 34, my: 308, mw: 13, line: 6, eye: '#27352b', eye2: '#47604c', blush: '255,140,150' },
    pals: [{ n: '陶盆', body: 0x86cf96, top: 0xbdecb4, pot: 0xee9f7c, pot2: 0xf9c4a4, fl: 0xff9fb5, sss: 0x50c070 }, { n: '白盆', body: 0x7fd0b8, top: 0xbff0dc, pot: 0xf2ece4, pot2: 0xffffff, fl: 0xffd27a, sss: 0x40c0a0 }, { n: '粉盆', body: 0xa8d880, top: 0xd8f2b0, pot: 0xffb7c5, pot2: 0xffdbe2, fl: 0xffffff, sss: 0x80c040 }, { n: '藍盆', body: 0x8fc8a8, top: 0xc8ecd0, pot: 0x9db8f0, pot2: 0xc6d6ff, fl: 0xffb38a, sss: 0x50b080 }],
    anc: { hat: [-0.07, 0.9, 0.02, 0.75], bow: [-0.12, 0.88, 0.1], neck: [0.34, 0.24, 0.23], glasses: 1 },
    build(c, p) {
      put(c, lathe([[0, 0], [0.17, 0], [0.19, 0.02], [0.235, 0.2], [0.255, 0.235], [0.255, 0.275], [0.2, 0.28], [0, 0.27]], 48), M(c, { color: p.pot, top: p.pot2, y0: 0, y1: 0.3, sss: p.pot, sssAmt: 0.2, rough: 0.8 }));
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.3 };
      c.main = put(c, blobGeo(v => { const y = v.y, rh = Math.hypot(v.x, v.z) || 1e-6, k = Math.pow(rh, 0.72) / rh, th = Math.atan2(v.z, v.x), rib = 1 + 0.035 * Math.cos(th * 9) * (1 - Math.abs(y)); v.set(v.x * k * 0.205 * rib, y * 0.36, v.z * k * 0.195 * rib); }), M(c, { ...o, y0: -0.3, y1: 0.36, face: c.face, headC: [0, 0.05, 0], span: [3.0, 3.0] }), 0, 0.6, 0);
      const am = M(c, { ...o, y0: -1, y1: 1.2 });
      for (const [s, y, sc] of [[-1, 0.5, 1], [1, 0.64, 0.8]]) { const g = piv(c, s * 0.17, y, 0, { side: s, k: 190, c: 9, g: 0.012, gy: 0.006, rest: [0, 0], droop: 0.35 }); put(c, ball(), am, s * 0.09 * sc, 0, 0, 0.1 * sc, 0.068 * sc, 0.068 * sc, g); put(c, ball(), am, s * 0.15 * sc, 0.1 * sc, 0, 0.066 * sc, 0.13 * sc, 0.066 * sc, g); }
      const f = piv(c, 0.08, 0.94, 0, { k: 160, c: 7, g: 0.02 }); c.flower = f; const fm = M(c, { color: p.fl, top: 0xffffff, y0: -1, y1: 2, sss: p.fl, sssAmt: 0.4 });
      for (let i = 0; i < 5; i++) { const a = i * 1.2566; put(c, ball(), fm, Math.cos(a) * 0.045, 0.02, Math.sin(a) * 0.045, 0.04, 0.022, 0.04, f); }
      put(c, ball(), M(c, { color: 0xffd86a, sss: 0xffa020 }), 0, 0.03, 0, 0.03, 0.025, 0.03, f);
      const sm = M(c, { color: 0xfffdf2, sss: 0xffffff, sssAmt: 0.5 });
      for (let i = 0; i < 16; i++) { const a = i * 2.39996 + 0.6, y = -0.75 + (i / 15) * 1.5, r = Math.sqrt(Math.max(0, 1 - y * y * 0.8)); if (Math.cos(a - Math.PI / 2) > 0.45 && Math.abs(y) < 0.5) continue; put(c, ball(), sm, Math.cos(a) * 0.205 * Math.pow(r, 0.72), 0.6 + y * 0.34, Math.sin(a) * 0.195 * Math.pow(r, 0.72), 0.017); }
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
    name: '飄飄', sub: '小幽靈', moveZh: '飄浮', sigZh: '嚇你一跳', why: '波浪裙擺的剪影，飄的時候裙擺會甩',
    R: 0.31, move: 'float', floatH: 0.17, footSize: null, handR: 0.052, hand: [0.31, 0.3, 0.12], stick: [0.33, 0.4, 0.31, 0.32], top: 0.74, wob: 1.6, mouth: [0, 0.3, 0.31], front: 0.31, cheek: [0.2, 0.36, 0.28], faceUp: 0.1, walk: 1.5, run: 3.5,
    face: { ...FACE, ex: 78, ey: 260, rx: 31, ry: 42, my: 316, mw: 14, eye: '#353058', eye2: '#5c5490', blush: '255,150,190' },
    pals: [{ n: '牛奶白', body: 0xd2cdfc, top: 0xffffff, sss: 0xb0a0ff }, { n: '薄荷', body: 0xbdeadb, top: 0xfbfffd, sss: 0x70d8b0 }, { n: '蜜桃', body: 0xffcabd, top: 0xfff6f0, sss: 0xff9080 }, { n: '夜藍', body: 0x8f9ae6, top: 0xd9defc, sss: 0x6070ff }],
    anc: { hat: [0, 0.7, 0.02, 0.95], bow: [0.17, 0.68, 0.1], neck: [0.2, 0.345, 0.325], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.3, rim: 0xffffff, rimAmt: 0.42 };
      c.main = put(c, blobGeo(v => { const y = v.y, th = Math.atan2(v.z, v.x), hem = sstep(-0.1, -0.72, y), r = 0.3 * (1 + 0.16 * hem) * (1 + 0.2 * Math.sin(th * 5 + 0.6) * hem * hem), yy = Math.max(y, -0.74), rh = Math.hypot(v.x, v.z) || 1e-6, kk = y < -0.74 ? Math.sqrt(1 - 0.74 * 0.74) / rh * (rh / Math.sqrt(1 - 0.74 * 0.74)) : 1; v.set(v.x * r * kk, yy * (yy > 0 ? 0.4 : 0.37), v.z * r * 0.95 * kk); }, 96, 64), M(c, { ...o, y0: -0.28, y1: 0.2, face: c.face, headC: [0, 0.04, 0], span: [2.15, 2.15] }), 0, 0.33, 0);
      const t = piv(c, 0.05, 0.12, -0.27, { k: 70, c: 4, g: 0.05, wag: true }); put(c, ball(), M(c, { ...o, y0: -1, y1: 1 }), 0, -0.02, -0.05, 0.07, 0.06, 0.09, t);
      const tf = piv(c, 0.04, 0.72, -0.02, { k: 90, c: 4.5, g: 0.04, rest: [0, -0.5] }); put(c, blobGeo(v => { const u = (v.y + 1) / 2; v.set(v.x * 0.045 * (1 - 0.6 * u) + 0.05 * u * u, v.y * 0.07 + 0.05, v.z * 0.04 * (1 - 0.6 * u)); }, 24, 20), M(c, { ...o, y0: -0.1, y1: 0.1 }), 0, 0, 0, 1, 1, 1, tf);
      c.limbMat = M(c, { ...o, y0: -1, y1: 0.5 });
    },
    idle(c, dt, t) { c.wobV.x += Math.sin(t * 1.9) * 0.9 * dt; },
    sig: { dur: 1.9, fn(c, u, a, P) { if (u < 0.45) { P.sq = -0.42 * sstep(0, 0.3, u); P.yOff = -c.cfg.floatH * sstep(0, 0.3, u); P.expr = 'smug'; P.hands = [0.6, -0.1]; } else { P.sq = 0.3 * (1 - sstep(0.5, 1, u)); P.yOff = 0.2 * (1 - sstep(0.5, 1, u)); P.expr = 'laugh'; P.hands = [1.4, 0.3]; if (!a.f) { a.f = 1; c.say('哇！', 1.1); c.fx.sfx('boing'); c.sqV += 6; } } } },
  },
  // ───────── 9 啾啾：圓鳥（蛋形身體、小尖嘴、頭頂三根毛、左右搖擺走）
  bird: {
    name: '啾啾', sub: '圓滾小鳥', moveZh: '左右搖擺', sigZh: '拍翅膀', why: '有立體的小尖嘴與翅膀，搖擺走路最逗',
    R: 0.31, walk: 1.35, run: 3.3, stride: [0.3, 0.72], lat: 0.1, footFwd: 0.07, footSize: [0.085, 0.036, 0.1], handR: 0.05, handScale: [0.04, 0.13, 0.1], hand: [0.315, 0.36, -0.02], front: 0.3, cheek: [0.2, 0.44, 0.28], waddle: 0.17, bob: 0.03, wob: 0.8, mouth: [0, 0.4, 0.4], top: 0.86, faceUp: 0.1,
    face: { ...FACE, ex: 80, ey: 240, rx: 31, ry: 40, my: 300, mw: 0, noMouth: true, eye: '#2a2a36', eye2: '#4a4a66', belly: 1 },
    pals: [{ n: '天空藍', body: 0x9ecbff, top: 0xd4eaff, belly: '#ffffff', beak: 0xffb45a, sss: 0x60a0ff }, { n: '小雞黃', body: 0xffdf7a, top: 0xfff4c0, belly: '#fffbe8', beak: 0xff9a50, sss: 0xffb020 }, { n: '櫻花粉', body: 0xffb0c4, top: 0xffe2ea, belly: '#fff6f0', beak: 0xffc060, sss: 0xff6f9a }, { n: '企鵝灰', body: 0x8c9cb8, top: 0xb8c6dc, belly: '#ffffff', beak: 0xffb45a, sss: 0x6070a0 }],
    anc: { hat: [0, 0.8, 0.03, 0.85], bow: [0.17, 0.78, 0.1], chest: [0, 0.24, 0.3], neck: [0.3, 0.34, 0.32], glasses: 1 },
    build(c, p) {
      c.face.st.bellyCol = p.belly;
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.26 };
      c.main = put(c, blobGeo(v => { const y = v.y, b = 1 + 0.12 * sstep(0.5, -0.6, y); v.set(v.x * 0.31 * b, y * (y > 0 ? 0.42 : 0.37), v.z * 0.295 * b); }), M(c, { ...o, y0: -0.3, y1: 0.3, face: c.face, headC: [0, 0.03, 0], span: [2.3, 2.3] }), 0, 0.42, 0);
      const bk = M(c, { color: p.beak, top: 0xffd890, y0: -0.05, y1: 0.05, sss: 0xff7020, sssAmt: 0.35, rough: 0.4 });
      c.beak = put(c, blobGeo(v => { const t = (v.z + 1) / 2, r = 0.062 * (1 - 0.72 * t * t); v.set(v.x * r * 1.25, v.y * r * 0.85, v.z * 0.06); }, 32, 24), bk, 0, 0.415, 0.325);
      const g = piv(c, 0, 0.82, -0.02, { k: 120, c: 6, g: 0.03 }); const tm = M(c, { ...o, y0: -1, y1: 1 });
      for (const [x, r, s] of [[-0.045, 0.5, 0.8], [0, 0, 1], [0.045, -0.5, 0.8]]) { const f = put(c, ball(), tm, x, 0.045 * s, -0.01, 0.022, 0.07 * s, 0.03, g); f.rotation.z = r; }
      const t = piv(c, 0, 0.3, -0.3, { k: 200, c: 9, g: 0.03, wag: true }); put(c, ball(), tm, 0, 0, -0.03, 0.09, 0.035, 0.09, t).rotation.x = -0.5;
      c.limbMat = tm; c.footMat = bk;
    },
    idle(c, dt, t) { c.beak.scale.y = 1 + Math.min(1, Math.max(0, c.face.cur.mOpen + c.face.talk)) * 0.55; if (calm(c) && every(c, 'tilt', 3.6, dt)) { c.tiltT = 0.9; c.tiltS = Math.random() < 0.5 ? -1 : 1; if (Math.random() < 0.5) { c.fx.sfx('squeak'); c.fx.spawn('note', c.headTop(new V3()).add(_v.set(0.2, 0, 0.1)), { v: new V3(0.2, 0.5, 0), life: 0.9, size: 0.14, sway: 0.5 }); } } if (c.tiltT > 0) { c.tiltT -= dt; c.rollAdd = c.tiltS * 0.26 * sstep(0, 0.15, 0.9 - c.tiltT) * sstep(0, 0.15, c.tiltT); } },
    sig: { dur: 2.0, fn(c, u, a, P) { const b = sstep(0, 0.2, u) * (1 - sstep(0.8, 1, u)), f = Math.sin(a.t * 34); P.yOff = 0.3 * b + f * 0.012; P.expr = 'effort'; P.hands = [1.25 + 0.15 * f, 0.1 + 0.16 * f]; P.handK = 600; P.sq = 0.06 * b; if (c.every('sg', 0.2)) { c.fx.sfx('step', 3); c.fx.spawn('dust', _v.set(c.pos.x + rnd(-0.3, 0.3), c.pos.y + 0.05, c.pos.z).clone(), { v: new V3(rnd(-0.6, 0.6), 0.2, rnd(-0.3, 0.3)), life: 0.4, size: 0.14, grow: 2 }); } } },
  },
  // ───────── 10 八寶：小章魚（大圓頭＋一圈短觸手，貼地滑行）
  octo: {
    name: '八寶', sub: '小章魚', moveZh: '貼地滑行', sigZh: '噴墨', why: '頭大腳多，觸手各自晃動，停下來還在動',
    R: 0.34, move: 'slide', footSize: null, handR: 0, top: 0.82, wob: 1.25, mouth: [0, 0.38, 0.37], front: 0.37, faceUp: 0.12, walk: 1.4, run: 3.4,
    face: { ...FACE, ex: 84, ey: 268, rx: 32, ry: 42, my: 322, mw: 12, mouthO: 1, eye: '#33264e', eye2: '#5c4690' },
    pals: [{ n: '葡萄', body: 0xc3a2f0, top: 0xeadcff, tip: 0xf0e4ff, sss: 0xa070ff }, { n: '蜜桃', body: 0xffab9c, top: 0xffe0d6, tip: 0xffece4, sss: 0xff7060 }, { n: '海藍', body: 0x8fc6f5, top: 0xd6ecff, tip: 0xe6f4ff, sss: 0x5090ff }, { n: '檸檬', body: 0xffdc78, top: 0xfff4c4, tip: 0xfff8dc, sss: 0xffb020 }],
    anc: { hat: [0, 0.79, 0.02, 1.05], bow: [0.2, 0.76, 0.12], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.3 };
      c.main = put(c, blobGeo(v => { const y = v.y, b = 1 + 0.09 * sstep(-0.6, 0.5, y); v.set(v.x * 0.345 * b, y * (y > 0 ? 0.37 : 0.31), v.z * 0.33 * b); }), M(c, { ...o, y0: -0.3, y1: 0.3, face: c.face, headC: [0, -0.03, 0], span: [2.2, 2.2] }), 0, 0.45, 0);
      const tm = M(c, { ...o, color: p.body, top: p.top, y0: -1.5, y1: 1.5 }), tp = M(c, { color: p.tip, top: p.tip, sss: p.sss, sssAmt: 0.2 });
      for (let i = 0; i < 7; i++) { const a = (i + 0.5) / 7 * Math.PI * 2 + Math.PI / 2, cx = Math.cos(a), sz = Math.sin(a); const g = piv(c, cx * 0.2, 0.2, sz * 0.2, { side: cx > 0.2 ? 1 : cx < -0.2 ? -1 : 0, k: 80 + i * 6, c: 4.5, g: 0.035, gy: 0.01, wig: i * 0.9 }); put(c, ball(), tm, cx * 0.07, -0.07, sz * 0.07, 0.095, 0.1, 0.095, g); put(c, ball(), tm, cx * 0.17, -0.14, sz * 0.17, 0.075, 0.06, 0.075, g); put(c, ball(), tp, cx * 0.25, -0.165, sz * 0.25, 0.055, 0.035, 0.055, g); }
      const sp = M(c, { color: p.top, top: p.top, sss: p.sss, sssAmt: 0.2 }); for (const [x, y, z, r] of [[-0.2, 0.72, 0.1, 0.06], [-0.27, 0.62, 0.02, 0.035], [0.22, 0.7, -0.08, 0.045]]) put(c, ball(), sp, x, y, z, r, r * 0.5, r);
    },
    idle(c, dt, t) { for (const a of c.apps) if (a.wig != null) { a.vx += Math.sin(t * 2.3 + a.wig) * 2.5 * dt; a.vz += Math.cos(t * 1.9 + a.wig * 1.7) * 2.5 * dt; } },
    sig: { dur: 2.4, fn(c, u, a, P) { if (u < 0.3) { P.sq = -0.2 * sstep(0, 0.3, u); P.expr = 'effort'; } else { P.sq = 0.12 * (1 - sstep(0.3, 0.6, u)); P.expr = u < 0.5 ? 'surprised' : 'shy'; if (u > 0.5) { P.tint = [1, 0.6, 0.68]; P.tintA = 0.3; } if (!a.f) { a.f = 1; c.fx.sfx('skid'); c.sqV += 5; for (let i = 0; i < 12; i++) c.fx.spawn('dust', _v.set(c.pos.x - Math.sin(c.yaw) * 0.3, c.pos.y + 0.2, c.pos.z - Math.cos(c.yaw) * 0.3).clone(), { v: new V3(-Math.sin(c.yaw) * rnd(0.6, 1.8) + rnd(-0.4, 0.4), rnd(0, 0.7), -Math.cos(c.yaw) * rnd(0.6, 1.8) + rnd(-0.4, 0.4)), life: 1.3, size: 0.22, grow: 1.6, drag: 2.2, color: 0x4a3c6a }); } } } },
  },
  // ───────── 11 閃閃：小星星（鼓鼓的五角星，站在兩個下尖角上，會側翻）
  star: {
    name: '閃閃', sub: '小星星', moveZh: '蹦蹦跳', sigZh: '側翻', why: '唯一有五個尖角（都磨圓）的剪影，側翻很搶眼',
    R: 0.3, move: 'hop', hopH: 0.13, lat: 0.13, footFwd: 0.02, footSize: [0.075, 0.05, 0.095], handR: 0, top: 0.76, wob: 0.9, mouth: [0, 0.34, 0.17], front: 0.18, tintK: 0.5, faceUp: 0.0, faceShift: 0.5, walk: 1.5, run: 3.6,
    face: { ...FACE, ex: 72, ey: 254, rx: 34, ry: 44, my: 312, mw: 15, line: 7, eye: '#4a3418', eye2: '#7a5a30', blush: '255,130,110' },
    pals: [{ n: '星星黃', body: 0xffd04a, top: 0xfff2a0, shoe: 0xff9f6a, sss: 0xffa020 }, { n: '櫻粉', body: 0xff9fbe, top: 0xffe0ea, shoe: 0xffffff, sss: 0xff6090 }, { n: '薄荷', body: 0x8fe0c0, top: 0xd8fbe8, shoe: 0xffffff, sss: 0x40d0a0 }, { n: '天藍', body: 0x8fc2ff, top: 0xd8ecff, shoe: 0xffe08a, sss: 0x5090ff }],
    anc: { hat: [0, 0.72, 0, 0.55], bow: [0.13, 0.52, 0.14], chest: [0, 0.18, 0.165], glasses: 1 },
    build(c, p) {
      c.main = put(c, blobGeo(v => { const ph = Math.atan2(v.x, v.y), k = Math.cos(5 * ph), rr = 0.285 * (1 + 0.3 * k + 0.05 * k * k); v.set(v.x * rr, v.y * rr, v.z * (0.175 - 0.03 * k)); }, 120, 60), M(c, { color: p.body, top: p.top, y0: -0.3, y1: 0.36, sss: p.sss, sssAmt: 0.45, rim: 0xffffff, rimAmt: 0.4, face: c.face, headC: [0, -0.02, -0.1], span: [2.0, 2.0] }), 0, 0.385, 0);
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
    name: '滾滾', sub: '小海豹', moveZh: '一伸一縮', sigZh: '翻肚肚', why: '唯一橫躺的長條剪影；會翻肚子拍手',
    R: 0.29, move: 'slide', footSize: null, handR: 0.05, handScale: [0.105, 0.028, 0.075], hand: [0.3, 0.09, 0.14], top: 0.52, wob: 1.1, mouth: [0, 0.2, 0.5], front: 0.47, cheek: [0.18, 0.24, 0.42], faceUp: 0.2, walk: 1.2, run: 3.0, stride: [0.5, 0.9],
    face: { ...FACE, ex: 80, ey: 246, rx: 30, ry: 38, my: 316, mw: 15, line: 6, wmouth: true, nose: 1, whisk: 1, eye: '#2a2e3a', eye2: '#4a5268', blush: '255,150,160' },
    pals: [{ n: '雪白', body: 0xd7e2ee, top: 0xffffff, fin: 0xb9c8da, sss: 0xa9c0e0 }, { n: '灰藍', body: 0x9fb2c8, top: 0xd6e0ec, fin: 0x8094ae, sss: 0x7090c0 }, { n: '奶茶', body: 0xe6cdb0, top: 0xfff4e4, fin: 0xcfae8a, sss: 0xd09060 }, { n: '櫻粉', body: 0xffc4d0, top: 0xfff0f3, fin: 0xf5a4b6, sss: 0xff80a0 }],
    anc: { hat: [0, 0.5, 0.2, 0.8], bow: [0.14, 0.48, 0.24], glasses: 1 },
    build(c, p) {
      const o = { color: p.body, top: p.top, sss: p.sss, sssAmt: 0.26 };
      c.main = put(c, blobGeo(v => { const z = v.z, k = 1 + 0.17 * z, tl = 1 - 0.5 * sstep(-0.25, -1, z); v.set(v.x * 0.3 * k * tl, v.y * 0.255 * k * tl - 0.02 * (1 - tl) + 0.03 * sstep(0.2, 1, z), v.z * 0.47); }, 80, 60), M(c, { ...o, y0: -0.22, y1: 0.1, face: c.face, headC: [0, 0.02, 0.17], span: [2.0, 2.0] }), 0, 0.26, 0);
      const fm = M(c, { color: p.fin, top: p.body, y0: -1, y1: 1, sss: p.sss }); c.limbMat = fm;
      const t = piv(c, 0, 0.2, -0.4, { k: 130, c: 6, g: 0.03, wag: true }); for (const s of [-1, 1]) { const f = put(c, ball(), fm, s * 0.085, 0.13, -0.07, 0.085, 0.13, 0.03, t); f.rotation.set(-0.5, 0, -s * 0.5); }
    },
    idle(c, dt, t) { },
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
    idle(c, dt, t) { const e = c.emo && c.emo.name, tg = c.flash ? 1.7 : c.mode === 'sleep' ? 0.12 : e === 'sad' || e === 'sleepy' ? 0.22 : e === 'happy' || e === 'laugh' ? 0.95 : 0.55; c.glowU.value += (tg + Math.sin(t * 3) * 0.03 - c.glowU.value) * Math.min(1, dt * (c.flash ? 30 : 5)); c.flash = false; },
    sig: { dur: 2.0, fn(c, u, a, P) { if (u < 0.4) { P.expr = 'sleepy'; P.pitch = 0.1; P.hands = [0.5, 0.3]; } else { c.flash = u < 0.75; P.expr = 'surprised'; P.sq = 0.14 * (1 - sstep(0.4, 1, u)); P.yOff = 0.1 * Math.sin(sstep(0.4, 0.7, u) * Math.PI); P.hands = [1.3, 0.3]; if (!a.f) { a.f = 1; c.say('有了！', 1.3); c.fx.sfx('heart'); c.sqV += 5; c.fx.burst('spark', c.headTop(new V3()), 9, { speed: 1.3, up: 0.6, life: 0.5, size: 0.13 }); } } } },
  },
};
export const SPECIES_IDS = Object.keys(SPECIES);
for (const id of SPECIES_IDS) SPECIES[id] = { id, ...DEF, ...SPECIES[id] };

export const ACCESSORIES = [['glasses', '眼鏡'], ['hat', '帽子'], ['bow', '蝴蝶結'], ['tie', '領帶'], ['scarf', '圍巾'], ['badge', '識別證']];
const ACC_COL = [0xff8f9f, 0x7fb0ff, 0xffc85a, 0x7fd6b0, 0xb49af0, 0xff9f6a];

// 個體規格 → 完整設定。spec：{ species, pal(配色編號或名稱), hue(-0.08~0.08 色相微調), acc:['glasses','tie'…], accColor(編號) }
export function resolveSpec(spec) {
  if (typeof spec === 'string') spec = { species: spec };
  const cfg = SPECIES[spec.species] || SPECIES.mochi;
  let pi = typeof spec.pal === 'string' ? cfg.pals.findIndex(p => p.n === spec.pal) : (spec.pal | 0); if (pi < 0) pi = 0;
  const pal = { ...cfg.pals[pi % cfg.pals.length] };
  if (spec.hue) { const c = new THREE.Color(), h = {}; for (const k in pal) if (typeof pal[k] === 'number') { c.setHex(pal[k]); c.getHSL(h); c.setHSL((h.h + spec.hue + 1) % 1, h.s, h.l); pal[k] = c.getHex(); } }
  return { cfg, pal, palIndex: pi % cfg.pals.length, acc: (spec.acc || []).filter(a => canWear(cfg, a)), accColor: ACC_COL[(spec.accColor | 0) % ACC_COL.length], spec };
}
export function canWear(cfg, a) { const n = cfg.anc; return a === 'glasses' ? !!n.glasses : a === 'hat' ? !!n.hat : a === 'bow' ? !!n.bow : a === 'tie' || a === 'badge' ? !!n.chest : a === 'scarf' ? !!n.neck : false; }

// 配件：位置由各物種的 anc 決定，掛在會跟著身體擠壓的那一層
export function addAccessories(c, list, col) {
  const n = c.cfg.anc, o = { color: col, top: 0xffffff, y0: -1, y1: 4, sss: col, sssAmt: 0.25 }, m = M(c, o), wm = M(c, { color: 0xfffaf2, sss: 0xffd0a0 });
  for (const a of list) {
    if (a === 'glasses') { c.face.st.glasses = '#' + new THREE.Color(col).multiplyScalar(0.55).getHexString(); c.face.dirty = true; }
    else if (a === 'hat') { const [x, y, z, s] = n.hat, g = piv(c, x, y, z, { k: 260, c: 14, g: 0.008 }); g.scale.setScalar(s); put(c, blobGeo(v => v.set(v.x * 0.15, Math.max(v.y, -0.25) * 0.105, v.z * 0.15), 40, 28), m, 0, 0.02, 0, 1, 1, 1, g); put(c, ball(), m, 0, 0.005, 0.13, 0.11, 0.014, 0.085, g); put(c, ball(), wm, 0, 0.125, 0, 0.026, 0.02, 0.026, g); g.rotation.x = -0.12; c.apps[c.apps.length - 1].rest = [-0.12, 0.1]; }
    else if (a === 'bow') { const [x, y, z] = n.bow, g = piv(c, x, y, z, { k: 240, c: 12, g: 0.01, rest: [0, -0.3] }); for (const s of [-1, 1]) put(c, ball(), m, s * 0.05, 0, 0, 0.055, 0.042, 0.026, g).rotation.z = s * 0.3; put(c, ball(), m, 0, 0, 0.012, 0.026, 0.028, 0.026, g); }
    else if (a === 'tie') { const [x, y, z] = n.chest, g = piv(c, x, y + 0.07, z, { k: 120, c: 6, g: 0.03 }); put(c, ball(), m, 0, 0, 0.012, 0.03, 0.026, 0.02, g); put(c, blobGeo(v => { const w = 0.6 + 0.4 * (1 - Math.abs(v.y + 0.3)); v.set(v.x * 0.04 * w, v.y * 0.075, v.z * 0.014); }, 24, 16), m, 0, -0.085, 0.016, 1, 1, 1, g); }
    else if (a === 'badge') { const [x, y, z] = n.chest, g = piv(c, x + 0.1, y + 0.04, z - 0.01, { k: 140, c: 7, g: 0.02 }); put(c, rbox(0.085, 0.105, 0.014, 0.006, 2), wm, 0, -0.03, 0.012, 1, 1, 1, g); put(c, rbox(0.085, 0.03, 0.016, 0.006, 2), m, 0, 0.005, 0.013, 1, 1, 1, g); put(c, ball(), M(c, { color: 0x6a5a55, sss: 0x6a5a55, sssAmt: 0.1 }), 0, -0.04, 0.021, 0.017, 0.017, 0.004, g); }
    else if (a === 'scarf') { const [y, rx, rz, tk = 0.06] = n.neck, t = put(c, new THREE.TorusGeometry(1, 0.24, 14, 48), m, 0, y, 0, rx * 0.84, rz * 0.84, tk / 0.24 * 1.25); t.rotation.x = Math.PI / 2; const g = piv(c, rx * 0.5, y - 0.03, rz * 0.82, { k: 90, c: 5, g: 0.04 }); put(c, ball(), m, 0, -0.07, 0.03, 0.045, 0.09, 0.025, g); }
  }
}
