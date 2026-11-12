// 角色建模：全部原創、全部程式生成的平滑曲面（二頭身、大頭、梨形身體、短手短腳、圓球手）
import { THREE, softMat, dirSurface, ellipsoid, gradY, limbGeo, latheGeo, fixSeam, roundedSlab, canvasTex, Spring, sstep, lerp, clamp, C } from './core.js';
import { Face, FACE_AZ, FACE_EL, FACE_TOP, makeSymbol } from './face.js';

const D2R = Math.PI / 180;
const mesh = (g, m, cast = true) => { const o = new THREE.Mesh(g, m); o.castShadow = cast; o.receiveShadow = true; return o; };
const grp = (parent, x = 0, y = 0, z = 0) => { const g = new THREE.Group(); g.position.set(x, y, z); parent && parent.add(g); return g; };
const mixHex = (a, b, t) => '#' + C(a).lerp(C(b), t).getHexString();

// ───────── 角色設定（原創角色與名字） ─────────
export const SPECS = {
  human: {
    name: '小禾', kind: '人類', role: '前端工程師',
    skin: '#ffe6d4', skinDark: '#fbd0bb', hair: '#8a5a44', hairHi: '#b98566',
    outfit: { kind: 'shirt', top: '#fdfaf4', topDark: '#e9e4f2', tie: '#ff9a8b', tieDark: '#f07c74', pants: '#8fa6cf', collar: '#ffffff' },
    sleeve: '#fbf7f0', sleeveDark: '#e6e0ee', pants: '#8fa6cf', shoe: '#7a6a8e', sole: '#fff6ea', badge: '#7fd1c1',
    face: { ink: '#4a3230', iris: '#b06c4c', blush: '#ff9d9d', eyeX: 19.5, eyeY: -10, eyeRx: 8.2, eyeRy: 10.8, mouthY: -29.5, browC: '#a9745c', humanNose: true },
    head: (d, p) => { const s = sstep(0.35, -0.5, d.y); p.set(d.x * 0.36 * (1.1 + 0.1 * s), d.y * 0.36 * 0.93, d.z * 0.36 * (1.0 + 0.05 * s)); },
  },
  cat: {
    name: '麻糬', kind: '貓', role: '資料分析師',
    skin: '#ffcf8f', skinDark: '#f6b672', hair: '#f2a65a',
    outfit: { kind: 'sweater', top: '#cdbcf5', topDark: '#b3a0e6', accent: '#fff3c9', pants: '#8c86b5', collar: '#ffffff', tie: '#ffb3c7' },
    sleeve: '#cdbcf5', sleeveDark: '#b3a0e6', pants: '#8c86b5', shoe: '#fff1dc', sole: '#ffd9d0', badge: '#ffb86b', paw: '#fff1dc',
    face: { ink: '#4a3632', iris: '#7fb069', blush: '#ff9a9a', eyeX: 20, eyeY: -9, eyeRx: 7.8, eyeRy: 9.4, mouthY: -24.5, catMouth: true, brow: false, browC: '#b06a2c' },
    head: (d, p) => { const s = sstep(0.4, -0.5, d.y); p.set(d.x * 0.36 * (1.14 + 0.14 * s), d.y * 0.36 * 0.9, d.z * 0.36 * (1.0 + 0.05 * s)); },
  },
  alien: {
    name: '啾比', kind: '外星人', role: '量化研究員',
    skin: '#bdf3de', skinDark: '#8fe0c6', hair: '#7fd6bd',
    outfit: { kind: 'shirt', top: '#bfe0ff', topDark: '#9cc6f2', tie: '#ffd66b', tieDark: '#f5bd45', pants: '#7d8fc4', collar: '#eaf5ff' },
    sleeve: '#bfe0ff', sleeveDark: '#9cc6f2', pants: '#7d8fc4', shoe: '#b79cff', sole: '#f1ebff', badge: '#ff9ac1',
    face: { ink: '#2b3a55', iris: '#5ad1c8', blush: '#ff9fc6', blushA: 0.55, eyeX: 21.5, eyeY: -7, eyeRx: 9.2, eyeRy: 12.4, mouthY: -29, lash: false, brow: false, browC: '#4f9c8a' },
    head: (d, p) => { const s = sstep(-0.5, 0.6, d.y); p.set(d.x * 0.35 * (1.0 + 0.16 * s), d.y * 0.35 * 1.0, d.z * 0.35 * (0.98 + 0.08 * s)); },
  },
  ghost: {
    name: '飄飄', kind: '幽靈', role: '夜班維運',
    skin: '#f4f6ff', skinDark: '#b9c4f2', hair: '#ffffff', ghost: true,
    outfit: { kind: 'ghost', top: '#ffffff', topDark: '#d6defc', tie: '#ff8fa3', tieDark: '#f06f88' },
    sleeve: '#ffffff', sleeveDark: '#dfe6ff', badge: '#9ad0ff',
    face: { ink: '#3d3a5c', iris: '#8f8ad6', blush: '#ffa3b8', blushA: 0.7, eyeX: 18, eyeY: -8, eyeRx: 6.8, eyeRy: 10.4, mouthY: -27, lash: false, brow: false, browC: '#8f95c4' },
    head: (d, p) => { const s = sstep(0.3, -0.6, d.y); p.set(d.x * 0.37 * (1.06 + 0.06 * s), d.y * 0.37 * 0.96, d.z * 0.37); },
  },
  pet: { name: '雪球', kind: '天竺鼠', role: '辦公室寵物', pet: true },
};

// ───────── 衣服貼圖（Canvas 2D）：襯衫領、領帶、毛衣織紋與羅紋、褲頭 ─────────
const BY0 = -0.07, BY1 = 0.44;
function outfitTex(o) {
  return canvasTex(1024, 512, (c, W, H) => {
    const Y = (y) => (1 - (y - BY0) / (BY1 - BY0)) * H, X = W / 2;
    let g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, o.top); g.addColorStop(0.55, o.top); g.addColorStop(1, o.topDark);
    c.fillStyle = g; c.fillRect(0, 0, W, H);
    c.lineCap = 'round'; c.lineJoin = 'round';
    if (o.kind === 'ghost') {
      g = c.createLinearGradient(0, Y(0.3), 0, H); g.addColorStop(0, '#fbfcff'); g.addColorStop(1, '#b4c1f5'); c.fillStyle = g; c.fillRect(0, Y(0.3), W, H);
      // 小領結
      c.fillStyle = o.tie; for (const s of [-1, 1]) { c.beginPath(); c.moveTo(X, Y(0.275)); c.bezierCurveTo(X + s * 30, Y(0.33), X + s * 74, Y(0.325), X + s * 70, Y(0.275)); c.bezierCurveTo(X + s * 74, Y(0.225), X + s * 30, Y(0.22), X, Y(0.275)); c.fill(); }
      c.fillStyle = o.tieDark; c.beginPath(); c.ellipse(X, Y(0.275), 15, 17, 0, 0, 7); c.fill();
      return;
    }
    if (o.kind === 'sweater') {
      // 細織紋
      c.globalAlpha = 0.16; c.strokeStyle = o.topDark; c.lineWidth = 2;
      for (let x = 0; x < W; x += 12) { c.beginPath(); c.moveTo(x, Y(0.4)); c.lineTo(x, Y(0.06)); c.stroke(); }
      c.globalAlpha = 1;
      // 胸前北歐風花紋帶
      c.strokeStyle = o.accent; c.lineWidth = 5; c.beginPath();
      for (let x = 0; x <= W; x += 16) { const y = Y(0.2) + ((x / 16) % 2 ? -9 : 9); x ? c.lineTo(x, y) : c.moveTo(x, y); } c.stroke();
      c.fillStyle = o.accent; for (let x = 16; x < W; x += 32) { c.beginPath(); c.arc(x, Y(0.2) + 26, 4, 0, 7); c.fill(); c.beginPath(); c.arc(x + 16, Y(0.2) - 26, 4, 0, 7); c.fill(); }
      // 下襬羅紋
      c.fillStyle = o.topDark; c.fillRect(0, Y(0.07), W, Y(0.015) - Y(0.07));
      c.strokeStyle = o.top; c.globalAlpha = 0.55; c.lineWidth = 3; for (let x = 0; x < W; x += 14) { c.beginPath(); c.moveTo(x, Y(0.066)); c.lineTo(x, Y(0.02)); c.stroke(); } c.globalAlpha = 1;
      // V 領＋裡面的襯衫領與小領帶
      c.fillStyle = o.collar; c.beginPath(); c.moveTo(X - 120, Y(0.44)); c.lineTo(X + 120, Y(0.44)); c.lineTo(X, Y(0.24)); c.closePath(); c.fill();
      c.strokeStyle = o.topDark; c.lineWidth = 9; c.beginPath(); c.moveTo(X - 122, Y(0.44)); c.lineTo(X, Y(0.236)); c.lineTo(X + 122, Y(0.44)); c.stroke();
      c.fillStyle = o.tie; c.beginPath(); c.moveTo(X - 15, Y(0.345)); c.lineTo(X + 15, Y(0.345)); c.lineTo(X + 10, Y(0.31)); c.lineTo(X + 17, Y(0.27)); c.lineTo(X, Y(0.25)); c.lineTo(X - 17, Y(0.27)); c.lineTo(X - 10, Y(0.31)); c.closePath(); c.fill();
    } else {
      // 襯衫：門襟、口袋、領帶
      c.strokeStyle = o.topDark; c.lineWidth = 3; c.beginPath(); c.moveTo(X - 13, Y(0.36)); c.lineTo(X - 13, Y(0.02)); c.moveTo(X + 13, Y(0.36)); c.lineTo(X + 13, Y(0.02)); c.stroke();
      c.lineWidth = 3.5; c.beginPath(); c.roundRect(X + 70, Y(0.235), 62, 52, 9); c.stroke();
      c.fillStyle = o.tie; c.beginPath(); c.moveTo(X - 19, Y(0.345)); c.lineTo(X + 19, Y(0.345)); c.lineTo(X + 13, Y(0.305)); c.lineTo(X + 22, Y(0.14)); c.lineTo(X, Y(0.085)); c.lineTo(X - 22, Y(0.14)); c.lineTo(X - 13, Y(0.305)); c.closePath(); c.fill();
      c.fillStyle = o.tieDark; c.beginPath(); c.moveTo(X - 19, Y(0.345)); c.lineTo(X + 19, Y(0.345)); c.lineTo(X + 13, Y(0.305)); c.lineTo(X - 13, Y(0.305)); c.closePath(); c.fill();
      c.strokeStyle = o.tieDark; c.lineWidth = 4; c.globalAlpha = 0.5; for (const y of [0.26, 0.2, 0.14]) { c.beginPath(); c.moveTo(X - 14, Y(y)); c.lineTo(X + 14, Y(y + 0.03)); c.stroke(); } c.globalAlpha = 1;
    }
    // 襯衫領片（下巴正下方看得到的位置）
    if (o.kind === 'shirt') {
      c.fillStyle = o.collar; c.strokeStyle = o.topDark; c.lineWidth = 3;
      for (const s of [-1, 1]) { c.beginPath(); c.moveTo(X, Y(0.35)); c.lineTo(X + s * 30, Y(0.265)); c.quadraticCurveTo(X + s * 84, Y(0.3), X + s * 118, Y(0.44)); c.lineTo(X, Y(0.44)); c.closePath(); c.fill(); c.stroke(); }
    }
    // 褲子＋腰帶
    c.fillStyle = o.pants; c.fillRect(0, Y(0.017), W, H);
    c.fillStyle = mixHex(o.pants, '#3a3350', 0.25); c.fillRect(0, Y(0.017), W, 7);
  });
}

// 筆電螢幕：會動的內容（程式碼逐行出現、游標閃爍、小圖表）
export function makeScreen() {
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 160; const c = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const cols = ['#ffb3c7', '#9ad0ff', '#b9f0c9', '#ffe08a', '#d9c2ff'];
  const draw = (t) => {
    c.fillStyle = '#fbf7ff'; c.fillRect(0, 0, 256, 160); c.fillStyle = '#cdbcf5'; c.fillRect(0, 0, 256, 20);
    c.fillStyle = '#fff'; for (let i = 0; i < 3; i++) { c.beginPath(); c.arc(12 + i * 14, 10, 4, 0, 7); c.fill(); }
    const n = Math.floor(t * 7), row = Math.floor(n / 9), sc = Math.max(0, row - 6);
    for (let r = sc; r <= row; r++) {
      const y = 32 + (r - sc) * 15; let x = 12 + ((r * 7) % 3) * 12; const words = r === row ? (n % 9) + 1 : 3 + ((r * 5) % 6);
      for (let w = 0; w < Math.min(words, 3 + ((r * 5) % 6)); w++) { const len = 14 + ((r * 13 + w * 29) % 34); c.fillStyle = cols[(r + w * 2) % 5]; c.beginPath(); c.roundRect(x, y, len, 8, 4); c.fill(); x += len + 6; }
      if (r === row && Math.floor(t * 4) % 2) { c.fillStyle = '#6b5a8e'; c.fillRect(x, y - 1, 3, 10); }
    }
    for (let i = 0; i < 5; i++) { const h = 12 + 16 * (0.5 + 0.5 * Math.sin(t * 2 + i * 1.3)); c.fillStyle = cols[i]; c.beginPath(); c.roundRect(186 + i * 13, 150 - h, 9, h, 3); c.fill(); }
    tex.needsUpdate = true;
  };
  draw(0); return { tex, draw };
}

// ───────── 兩足角色 ─────────
export function buildChar(id) {
  const sp = SPECS[id];
  if (sp.pet) return buildPet(sp);
  const ch = { id, spec: sp, springs: [], n: {}, props: {}, sym: {} };
  const root = ch.root = new THREE.Group(); const rig = ch.rig = grp(root); const n = ch.n;
  const HIP = ch.HIP = sp.ghost ? 0.46 : 0.245;
  const hips = n.hips = grp(rig, 0, HIP, 0); const spine = n.spine = grp(hips);
  const skinM = softMat(sp.skin, { vc: true }), M = (c, o) => softMat(c, o);

  // 身體（梨形旋轉體＋衣服貼圖）
  const prof = sp.ghost
    ? [[0, -0.4], [0.028, -0.385], [0.07, -0.3], [0.125, -0.19], [0.18, -0.07], [0.21, 0.05], [0.2, 0.17], [0.165, 0.27], [0.13, 0.35], [0.085, 0.42], [0, 0.44]]
    : [[0, -0.07], [0.12, -0.055], [0.19, -0.005], [0.218, 0.075], [0.203, 0.17], [0.168, 0.27], [0.132, 0.35], [0.085, 0.42], [0, 0.44]];
  const bodyR = (y) => { for (let i = 1; i < prof.length; i++) if (y <= prof[i][1]) { const a = prof[i - 1], b = prof[i]; return lerp(a[0], b[0], (y - a[1]) / (b[1] - a[1])); } return 0; };
  const bodyG = latheGeo(prof, { rows: 44, seg: 64 });
  if (sp.ghost) { const uv = bodyG.attributes.uv, pos = bodyG.attributes.position; for (let i = 0; i < pos.count; i++) { uv.setY(i, clamp((pos.getY(i) - BY0) / (BY1 - BY0))); const y = Math.min(0, pos.getY(i) + 0.02), k = y * y; pos.setZ(i, pos.getZ(i) - k * 2.0); pos.setY(i, pos.getY(i) + k * k * 9); } fixSeam(bodyG); }
  const body = n.body = mesh(bodyG, softMat(0xffffff, { map: outfitTex(sp.outfit), rimStr: sp.ghost ? 0.2 : 0.38 })); spine.add(body);

  // 識別證（3D、掛在胸前口袋夾上、會晃）
  {
    const u = 0.5 + 0.098, phi = Math.PI + u * Math.PI * 2, y = sp.outfit.kind === 'sweater' ? 0.15 : 0.2, r = bodyR(y) + 0.006;
    const piv = grp(spine, r * Math.sin(phi), y, r * Math.cos(phi)); piv.rotation.set(0.13, phi - Math.PI * 2, 0, 'YXZ');
    const clip = mesh(ellipsoid(0.014, 0.014, 0.008), M('#8d93a8')); piv.add(clip);
    const sw = grp(piv); const card = mesh(roundedSlab(0.07, 0.088, 0.014, 0.006, 0.003), M('#ffffff')); card.position.set(0, -0.058, 0.006); sw.add(card);
    const tex = canvasTex(128, 160, (c) => { c.fillStyle = '#fff'; c.fillRect(0, 0, 128, 160); c.fillStyle = sp.badge; c.fillRect(0, 0, 128, 46); c.fillStyle = sp.skin === '#ffffff' ? '#e8ecff' : sp.skin; c.beginPath(); c.arc(64, 74, 26, 0, 7); c.fill(); c.fillStyle = sp.face.ink; c.beginPath(); c.arc(55, 72, 3.4, 0, 7); c.arc(73, 72, 3.4, 0, 7); c.fill(); c.fillStyle = '#d5d8e4'; c.beginPath(); c.roundRect(24, 112, 80, 9, 4); c.fill(); c.beginPath(); c.roundRect(36, 130, 56, 8, 4); c.fill(); c.fillStyle = '#fff'; c.beginPath(); c.roundRect(48, 14, 32, 8, 4); c.fill(); });
    const fr = new THREE.Mesh(new THREE.PlaneGeometry(0.066, 0.084), softMat(0xffffff, { map: tex })); fr.position.set(0, -0.058, 0.0125); sw.add(fr);
    ch.springs.push(new Spring(sw, 0.09, { axis: new THREE.Vector3(0, -1, 0), k: 70, c: 5, acc: 2.5, g: 6 }));
  }

  // 手臂：上臂、前臂（袖子）、圓球手＋小拇指球
  const sleeveG = () => gradY(limbGeo(0.053, 0.1), sp.sleeve, sp.sleeveDark, -0.15, 0.05);
  const foreG = () => { const g = limbGeo(0.052, 0.07, 0.056); const pos = g.attributes.position, col = new Float32Array(pos.count * 3), a = C(sp.sleeve), b = C(sp.sleeveDark), cuff = C(sp.outfit.kind === 'sweater' ? sp.sleeveDark : '#ffffff'), cc = new THREE.Color();
    for (let i = 0; i < pos.count; i++) { const y = pos.getY(i); cc.copy(a).lerp(b, sstep(0.05, -0.12, y)); if (y < -0.05) cc.copy(cuff); col[i * 3] = cc.r; col[i * 3 + 1] = cc.g; col[i * 3 + 2] = cc.b; } g.setAttribute('color', new THREE.BufferAttribute(col, 3)); return g; };
  const clothM = softMat(0xffffff, { vc: true, rimStr: sp.ghost ? 0.2 : 0.38 });
  const handC = sp.paw ?? sp.skin;
  for (const [s, k] of [[1, 'L'], [-1, 'R']]) {
    const arm = n['arm' + k] = grp(spine, s * 0.142, 0.318, 0); arm.rotation.order = 'ZXY'; arm.add(mesh(sleeveG(), clothM));
    const elb = n['elb' + k] = grp(arm, 0, -0.1, 0); elb.add(mesh(foreG(), clothM));
    const hand = n['hand' + k] = grp(elb, 0, -0.122, 0);
    const hm = softMat(handC, { rimStr: sp.ghost ? 0.2 : 0.38 });
    hand.add(mesh(ellipsoid(0.07, 0.072, 0.068, { w: 32, h: 24 }), hm));
    const th = mesh(ellipsoid(0.026, 0.03, 0.026, { w: 20, h: 14 }), hm); th.position.set(-s * 0.03, 0.0, 0.05); hand.add(th);
    if (sp.paw) for (const dx of [-0.026, 0, 0.026]) { const t = mesh(ellipsoid(0.012, 0.012, 0.008, { w: 14, h: 10 }), M('#ffb7c0'), false); t.position.set(dx, -0.055 + Math.abs(dx) * 0.3, 0.04); hand.add(t); }
    n['grip' + k] = grp(hand, 0, -0.02, 0.045);
  }

  // 腿與腳（幽靈沒有腿，改成會飄的尾巴）
  if (!sp.ghost) {
    const pantM = softMat(0xffffff, { vc: true });
    for (const [s, k] of [[1, 'L'], [-1, 'R']]) {
      const leg = n['leg' + k] = grp(hips, s * 0.088, -0.015, 0); leg.add(mesh(gradY(limbGeo(0.07, 0.08), sp.pants, mixHex(sp.pants, '#4a4470', 0.18), -0.2, 0.05), pantM));
      const knee = n['knee' + k] = grp(leg, 0, -0.08, 0); knee.add(mesh(gradY(limbGeo(0.07, 0.07, 0.066), mixHex(sp.pants, '#4a4470', 0.1), mixHex(sp.pants, '#4a4470', 0.22), -0.14, 0), pantM));
      const foot = n['foot' + k] = grp(knee, 0, -0.07, 0);
      const shoe = mesh(dirSurface((d, p) => { const up = sstep(-0.2, 0.9, d.y); p.set(d.x * 0.082 * (1 - 0.1 * up), d.y * 0.058 * (1 + 0.1 * sstep(0, -1, d.z) * up), d.z * 0.112 * (1 - 0.08 * up)); }, { w: 36, h: 26 }), M(sp.shoe)); shoe.position.set(0, -0.02, 0.034); foot.add(shoe);
      const sole = mesh(ellipsoid(0.085, 0.022, 0.116, { w: 36, h: 14 }), M(sp.sole)); sole.position.set(0, -0.064, 0.034); foot.add(sole);
      if (sp.paw) for (const dx of [-0.034, 0, 0.034]) { const t = mesh(ellipsoid(0.016, 0.012, 0.012, { w: 14, h: 10 }), M('#ffb7c0'), false); t.position.set(dx, -0.03, 0.14 - Math.abs(dx) * 0.35); foot.add(t); }
    }
  }

  // 頭
  const head = n.head = grp(spine, 0, 0.4, 0); const skull = n.skull = grp(head, 0, 0.285, 0);
  const sk = C(sp.skin), skD = C(sp.skinDark);
  const headCol = (d, p, c) => { c.copy(skD).lerp(sk, sstep(-0.75, 0.25, d.z * 0.6 + d.y * 0.7)); if (id === 'cat') { const m = sstep(0.25, 0.75, d.z) * sstep(0.15, -0.35, d.y); c.lerp(C('#fff3df'), m * 0.95); } };
  skull.add(mesh(dirSurface(sp.head, { w: 96, h: 64, color: headCol }), softMat(0xffffff, { vc: true, rimStr: sp.ghost ? 0.2 : 0.38 })));
  // 臉貼片
  const fs = { ...sp.face };
  if (id === 'cat') {
    fs.pre = (c, f) => { // 額頭與臉頰的虎斑
      c.strokeStyle = '#e8913f'; c.lineCap = 'round';
      for (const [x, w, l] of [[-11, 4.6, 13], [0, 5.4, 17], [11, 4.6, 13]]) { c.lineWidth = w; c.beginPath(); c.moveTo(x * 1.15, 57); c.quadraticCurveTo(x, 50, x * 0.8, 57 - l - 16); c.stroke(); }
      for (const s of [-1, 1]) for (const [y, l] of [[-3, 9], [-11, 7]]) { c.lineWidth = 3.6; c.beginPath(); c.moveTo(s * 58, y + 2); c.quadraticCurveTo(s * 52, y, s * (56 - l), y - 1.5); c.stroke(); }
    };
    fs.nose = (c, f) => { c.fillStyle = '#ff8fa0'; c.beginPath(); c.moveTo(-3.4, -18.6); c.quadraticCurveTo(0, -17.4, 3.4, -18.6); c.quadraticCurveTo(3.2, -21, 0, -23.6); c.quadraticCurveTo(-3.2, -21, -3.4, -18.6); c.fill();
      c.strokeStyle = '#c9a98f'; c.lineWidth = 0.9; for (const s of [-1, 1]) for (const [dy, a] of [[0, 2.5], [-4.5, -1]]) { c.beginPath(); c.moveTo(s * 13, -22 + dy); c.lineTo(s * 30, -21 + dy + a); c.stroke(); } };
  }
  if (id === 'human') fs.nose = (c) => { c.strokeStyle = '#eba58c'; c.lineWidth = 1.5; c.beginPath(); c.moveTo(-1.3, -20.6); c.quadraticCurveTo(0, -22.2, 1.3, -20.6); c.stroke(); };
  if (id === 'alien') fs.pre = (c) => { c.fillStyle = '#c9f7e6'; c.globalAlpha = 0.8; for (const [x, y, r] of [[-14, 46, 4.2], [-3, 54, 2.6], [12, 49, 3.4], [22, 40, 2]]) { c.beginPath(); c.ellipse(x, y, r, r * 0.92, 0, 0, 7); c.fill(); } c.globalAlpha = 1; };
  const face = ch.face = new Face(fs);
  const fp = mesh(dirSurface((d, p) => { sp.head(d, p); p.multiplyScalar(1.004); }, { w: 56, h: 56, phiStart: Math.PI / 2 - FACE_AZ * D2R / 2, phiLen: FACE_AZ * D2R, thetaStart: (90 - FACE_TOP) * D2R, thetaLen: FACE_EL * D2R }), softMat(0xffffff, { map: face.tex, transparent: true }), false);
  fp.renderOrder = 2; skull.add(fp);

  const earSpring = (node, len, o) => ch.springs.push(new Spring(node, len, o));
  if (id === 'human') {
    // 頭髮：包住頭的平滑髮殼（瀏海有波浪）、兩側鬢角、頭頂丸子與呆毛
    const hair = (d, p) => {
      sp.head(d, p); const az = Math.atan2(d.x, d.z), a = Math.abs(az);
      const front = 0.4 + 0.075 * Math.cos(az * 5.2) - 0.1 * sstep(0.45, 0.95, a);
      const L = lerp(front, -0.5, sstep(0.7, 1.45, a));
      const m = sstep(L - 0.07, L + 0.16, d.y);
      const th = 0.075 + 0.05 * sstep(0.2, -0.9, d.z) + 0.02 * sstep(0.3, 1, d.y) + 0.035 * sstep(-0.1, -0.5, d.y) * sstep(0.9, 1.4, a);
      p.multiplyScalar(1 + m * th - (1 - m) * 0.03);
    };
    const hc = C(sp.hair), hh = C(sp.hairHi);
    const hm = softMat(0xffffff, { vc: true, rimStr: 0.5 });
    skull.add(mesh(dirSurface(hair, { w: 220, h: 140, color: (d, p, c) => { const band = Math.exp(-Math.pow((d.y - 0.62) / 0.11, 2)) * (0.55 + 0.45 * Math.cos(Math.atan2(d.x, d.z) * 9)); c.copy(hc).lerp(hh, clamp(0.25 * sstep(-0.6, 0.9, d.y) + 0.6 * band + 0.035 * Math.sin(Math.atan2(d.x, d.z) * 46) * sstep(0.95, 0.3, d.y))); } }), hm));
    const bun = grp(skull, 0, 0.36, -0.06); bun.add(mesh(gradY(ellipsoid(0.125, 0.11, 0.12), sp.hairHi, sp.hair), hm));
    const tie = mesh(new THREE.TorusGeometry(0.075, 0.018, 14, 40), M('#ff9a8b')); tie.rotation.x = Math.PI / 2; tie.position.set(0, 0.292, -0.06); skull.add(tie);
    const aho = grp(skull, 0.02, 0.335, 0.12); aho.rotation.set(0.5, 0, -0.3);
    const ag = dirSurface((d, p) => { const t = d.y * 0.5 + 0.5; p.set(d.x * 0.022 * (1 - 0.6 * t) + 0.05 * t * t, d.y * 0.06 + 0.05, d.z * 0.016 * (1 - 0.5 * t)); }, { w: 20, h: 20 });
    aho.add(mesh(ag, M(sp.hair))); earSpring(aho, 0.1, { k: 120, c: 7, acc: 2.4 });
  }
  if (id === 'cat') {
    const earG = dirSurface((d, p) => { const t = sstep(-0.6, 1, d.y); p.set(d.x * 0.125 * (1 - 0.62 * t), d.y * 0.13 + 0.08, d.z * 0.05 * (1 - 0.3 * t)); }, { w: 36, h: 28, color: (d, p, c) => c.copy(C('#f2a65a')).lerp(C('#ffcf8f'), sstep(1, -0.5, d.y)) });
    const inG = dirSurface((d, p) => { const t = sstep(-0.6, 1, d.y); p.set(d.x * 0.078 * (1 - 0.62 * t), d.y * 0.088 + 0.078, d.z * 0.02 + 0.036); }, { w: 28, h: 20 });
    for (const s of [-1, 1]) {
      const e = n['ear' + (s > 0 ? 'L' : 'R')] = grp(skull, s * 0.235, 0.215, 0.0); e.rotation.set(-0.08, 0, -s * 0.42);
      e.add(mesh(earG, softMat(0xffffff, { vc: true }))); e.add(mesh(inG, M('#ffb7c0'), false));
      earSpring(e, 0.2, { k: 140, c: 8, acc: 2.2 });
    }
    // 尾巴：五節彈簧鏈，尾端奶油色
    let par = grp(hips, 0, 0.0, -0.17); par.rotation.x = -0.95; n.tail = par;
    for (let i = 0; i < 5; i++) {
      const seg = grp(par, 0, i ? 0.075 : 0, 0); if (i) seg.rotation.x = 0.3;
      const g = limbGeo(0.04 - i * 0.002, 0.075); g.rotateX(Math.PI);
      seg.add(mesh(g, M(i === 4 ? '#fff1dc' : i % 2 ? '#f2a65a' : '#ffc27a')));
      if (i === 4) { const tip = mesh(ellipsoid(0.045, 0.05, 0.045), M('#fff1dc')); tip.position.y = 0.085; seg.add(tip); }
      ch.springs.push(new Spring(seg, 0.075, { k: 60 + i * 6, c: 5.5, acc: 2.6 })); par = seg;
    }
  }
  if (id === 'alien') {
    for (const s of [-1, 1]) {
      const a = n['ant' + (s > 0 ? 'L' : 'R')] = grp(skull, s * 0.13, 0.31, 0.02); a.rotation.set(0.05, 0, -s * 0.38);
      const curve = new THREE.QuadraticBezierCurve3(new THREE.Vector3(0, -0.03, 0), new THREE.Vector3(0, 0.12, 0), new THREE.Vector3(s * 0.05, 0.2, 0));
      a.add(mesh(new THREE.TubeGeometry(curve, 24, 0.014, 14), M('#7fd6bd')));
      const ball = mesh(ellipsoid(0.05, 0.05, 0.05, { w: 28, h: 20 }), softMat('#ffe58a', { emissive: 0xffc94d, emissiveIntensity: 0.55 })); ball.position.set(s * 0.05, 0.2, 0); a.add(ball);
      earSpring(a, 0.2, { k: 55, c: 3.6, acc: 3.2 });
    }
  }
  if (id === 'ghost') {
    const w = grp(skull, 0, 0.33, 0); w.rotation.set(-0.2, 0, -0.25);
    w.add(mesh(dirSurface((d, p) => { const t = d.y * 0.5 + 0.5; p.set(d.x * 0.07 * (1 - 0.72 * t * t) + 0.07 * t * t, d.y * 0.1 + 0.07, d.z * 0.06 * (1 - 0.72 * t * t)); }, { w: 28, h: 28 }), softMat('#f4f6ff', { rimStr: 0.2 })));
    earSpring(w, 0.16, { k: 60, c: 4, acc: 3 });
  }

  // 頭上情緒符號
  const symA = ch.symAnchor = grp(skull, 0, 0.4, 0);
  for (const k of ['anger', 'q', 'ex', 'spark', 'bulb', 'drop', 'heart', 'note']) { const s = ch.sym[k] = makeSymbol(k, 0.2); symA.add(s); }
  ch.puffs = [0, 1, 2].map(() => { const s = makeSymbol('puff', 0.16); symA.add(s); return s; });
  ch.dizzy = [0, 1, 2].map(() => { const s = makeSymbol('star', 0.12); symA.add(s); return s; });
  ch.bubble = makeSymbol('dots', 0.3); symA.add(ch.bubble);
  ch.bdots = [0, 1, 2].map(() => { const d = new THREE.Sprite(new THREE.SpriteMaterial({ color: 0xb79cff, depthTest: false, map: dotTex() })); d.renderOrder = 21; d.scale.setScalar(0.04); symA.add(d); return d; });

  buildProps(ch);
  root.traverse((o) => { o.frustumCulled = false; });
  return ch;
}
let _dot; const dotTex = () => _dot || (_dot = canvasTex(64, 64, (c) => { c.fillStyle = '#fff'; c.beginPath(); c.arc(32, 32, 28, 0, 7); c.fill(); }));

// ───────── 道具：椅子＋桌子＋筆電、站立桌、平板、放大鏡、筆記本、筆 ─────────
function buildProps(ch) {
  const P = ch.props, M = softMat, root = ch.root, n = ch.n;
  // 辦公椅＋桌＋筆電
  const desk = P.desk = grp(root); desk.visible = false;
  const seatY = ch.spec.ghost ? 0.3 : 0.3;
  const chair = grp(desk, 0, 0, -0.02); chair.visible = !ch.spec.ghost;
  const seat = mesh(latheGeo([[0, -0.035], [0.17, -0.035], [0.215, -0.012], [0.215, 0.012], [0.17, 0.035], [0, 0.035]], { rows: 30, tension: 0.2 }), M('#ffc9b8')); seat.position.y = seatY - 0.035; chair.add(seat);
  const back = mesh(dirSurface((d, p) => p.set(d.x * 0.19, d.y * 0.15, d.z * 0.035 - 0.035 * d.x * d.x), { w: 40, h: 28 }), M('#ffc9b8')); back.position.set(0, seatY + 0.2, -0.215); back.rotation.x = -0.12; chair.add(back);
  const bp = mesh(limbGeo(0.018, 0.2), M('#b9b4c9')); bp.position.set(0, seatY + 0.12, -0.225); chair.add(bp);
  const pole = mesh(limbGeo(0.026, seatY - 0.09), M('#b9b4c9')); pole.position.y = seatY - 0.05; chair.add(pole);
  for (let i = 0; i < 5; i++) { const a = i / 5 * Math.PI * 2, leg = mesh(limbGeo(0.02, 0.17), M('#b9b4c9')); leg.position.y = 0.05; leg.rotation.set(Math.PI / 2 - 0.12, a, 0, 'YXZ'); chair.add(leg); const wh = mesh(ellipsoid(0.03, 0.03, 0.03, { w: 16, h: 12 }), M('#8d88a3')); wh.position.set(Math.sin(a) * 0.18, 0.03, Math.cos(a) * 0.18); chair.add(wh); }
  const dz = 0.52, top = mesh(roundedSlab(0.92, 0.46, 0.06, 0.03, 0.012), M('#ffe9c9')); top.rotation.x = -Math.PI / 2; top.position.set(0, 0.5, dz); desk.add(top);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const l = mesh(limbGeo(0.024, 0.44), M('#f5cfa0')); l.position.set(sx * 0.38, 0.49, dz + sz * 0.16); desk.add(l); }
  const lap = P.laptop = grp(desk, 0, 0.527, dz - 0.07);
  const lb = mesh(roundedSlab(0.34, 0.2, 0.025, 0.012, 0.004), M('#f1eefa')); lb.rotation.x = -Math.PI / 2; lap.add(lb);
  const kb = new THREE.Mesh(new THREE.PlaneGeometry(0.29, 0.12), softMat(0xffffff, { map: canvasTex(256, 112, (c) => { c.fillStyle = '#f1eefa'; c.fillRect(0, 0, 256, 112); c.fillStyle = '#cfc8e6'; for (let r = 0; r < 4; r++) for (let k = 0; k < 11; k++) { c.beginPath(); c.roundRect(6 + k * 22.4 + (r % 2) * 5, 6 + r * 26, 18, 20, 5); c.fill(); } }) })); kb.rotation.x = -Math.PI / 2; kb.position.set(0, 0.0115, -0.025); lap.add(kb);
  const lid = grp(lap, 0, 0.008, 0.1); lid.rotation.x = 0.3;
  const ls = mesh(roundedSlab(0.34, 0.21, 0.025, 0.01, 0.004), M('#e4dcf7')); ls.position.y = 0.105; lid.add(ls);
  const scr = ch.screen = makeScreen(); const sm = new THREE.Mesh(new THREE.PlaneGeometry(0.31, 0.185), new THREE.MeshBasicMaterial({ map: scr.tex })); sm.position.set(0, 0.105, -0.0096); sm.rotation.y = Math.PI; lid.add(sm);
  const logo = mesh(ellipsoid(0.03, 0.03, 0.004, { w: 24, h: 12 }), M('#ffffff')); logo.position.set(0, 0.11, 0.0095); lid.add(logo);
  const mug = grp(desk, 0.33, 0.515, dz + 0.02); mug.add(mesh(latheGeo([[0, 0], [0.036, 0], [0.04, 0.012], [0.04, 0.07], [0.034, 0.074], [0.03, 0.066], [0.03, 0.02], [0, 0.018]], { rows: 40, tension: 0.15 }), M('#ffb3c7')));
  const hd = mesh(new THREE.TorusGeometry(0.022, 0.007, 10, 24), M('#ffb3c7')); hd.position.set(0.045, 0.04, 0); mug.add(hd);
  const plant = grp(desk, -0.35, 0.515, dz + 0.04); plant.add(mesh(latheGeo([[0, 0], [0.034, 0], [0.045, 0.06], [0.04, 0.064], [0, 0.06]], { rows: 24, tension: 0.2 }), M('#fff6ea')));
  for (const [x, z, r, s] of [[0, 0, 0, 1.15], [0.03, 0.01, 0.5, 0.85], [-0.03, 0, -0.5, 0.9], [0, -0.02, 0.2, 0.7]]) { const lf = mesh(ellipsoid(0.026 * s, 0.06 * s, 0.014 * s, { w: 18, h: 14 }), M('#9fe0b0')); lf.position.set(x, 0.1 * s + 0.01, z); lf.rotation.z = -r; plant.add(lf); }

  // 爭執用的小圓桌
  const tb = P.table = grp(root, 0, 0, 0.56); tb.visible = false;
  const tt = mesh(latheGeo([[0, -0.02], [0.27, -0.02], [0.3, 0], [0.27, 0.02], [0, 0.02]], { rows: 28, tension: 0.2 }), M('#ffe9c9')); tt.position.y = 0.385; tb.add(tt);
  const tl = mesh(limbGeo(0.035, 0.33), M('#f5cfa0')); tl.position.y = 0.37; tb.add(tl);
  const tf = mesh(latheGeo([[0, 0], [0.16, 0], [0.17, 0.012], [0.05, 0.035], [0, 0.035]], { rows: 24, tension: 0.2 }), M('#f5cfa0')); tb.add(tf);
  const paper = P.paper = grp(tb, 0.06, 0.407, -0.02); const pm = mesh(roundedSlab(0.15, 0.2, 0.012, 0.004, 0.001), M('#ffffff')); pm.rotation.set(-Math.PI / 2, 0, 0.3); paper.add(pm);
  const tmug = P.tmug = grp(tb, -0.14, 0.405, 0.06); tmug.add(mesh(latheGeo([[0, 0], [0.036, 0], [0.04, 0.012], [0.04, 0.07], [0.034, 0.074], [0.03, 0.066], [0.03, 0.02], [0, 0.018]], { rows: 40, tension: 0.15 }), M('#9ad0ff')));

  // 平板（左手）＋放大鏡（右手）
  const tab = P.tablet = grp(n.gripL); tab.visible = false; tab.rotation.set(0.15, 0, 0); tab.position.set(-0.085, 0.0, 0.05);
  tab.add(mesh(roundedSlab(0.27, 0.19, 0.024, 0.012, 0.004), M('#8fdcc8')));
  { const lg = mesh(ellipsoid(0.034, 0.034, 0.004, { w: 24, h: 10 }), M('#ffffff'), false); lg.position.z = -0.011; tab.add(lg); }
  const ts = new THREE.Mesh(new THREE.PlaneGeometry(0.245, 0.165), new THREE.MeshBasicMaterial({ map: canvasTex(256, 172, (c) => { c.fillStyle = '#f4fbff'; c.fillRect(0, 0, 256, 172); c.strokeStyle = '#ff9a8b'; c.lineWidth = 5; c.lineJoin = 'round'; c.beginPath(); [[14, 120], [50, 96], [86, 110], [122, 66], [158, 80], [194, 40], [240, 52]].forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.stroke(); c.fillStyle = '#b9e3ff'; for (let i = 0; i < 7; i++) { c.beginPath(); c.roundRect(16 + i * 33, 150 - (10 + (i * 37) % 22), 20, 10 + (i * 37) % 22, 4); c.fill(); } c.fillStyle = '#cdbcf5'; c.beginPath(); c.roundRect(14, 12, 110, 14, 7); c.fill(); }) })); ts.position.z = 0.0106; tab.add(ts);
  const mg = P.glass = grp(n.gripR); mg.visible = false; mg.rotation.set(2.45, 0, -0.35); mg.position.set(0, 0.0, 0.0); mg.userData.s0 = 1.25;
  const ring = mesh(new THREE.TorusGeometry(0.07, 0.013, 16, 48), M('#ffb86b')); ring.position.y = 0.14; mg.add(ring);
  const lens = new THREE.Mesh(new THREE.CircleGeometry(0.066, 40), new THREE.MeshBasicMaterial({ color: 0xd9f1ff, transparent: true, opacity: 0.42, side: THREE.DoubleSide, depthWrite: false })); lens.position.y = 0.14; mg.add(lens);
  const hl = mesh(limbGeo(0.014, 0.075), M('#c98a5a')); hl.position.y = 0.065; mg.add(hl);

  // 筆記本（左手）＋鉛筆（右手）
  const nb = P.book = grp(n.gripL); nb.visible = false; nb.rotation.set(0.2, 0, 0); nb.position.set(-0.08, 0.0, 0.035);
  nb.add(mesh(roundedSlab(0.2, 0.25, 0.015, 0.016, 0.004), M('#ff9ac1')));
  const pg = ch.noteTex = makeNotes(); const pgm = new THREE.Mesh(new THREE.PlaneGeometry(0.18, 0.23), softMat(0xffffff, { map: pg.tex })); pgm.position.z = 0.0125; nb.add(pgm);
  for (let i = 0; i < 6; i++) { const r = mesh(new THREE.TorusGeometry(0.011, 0.0035, 8, 16), M('#b9b4c9'), false); r.position.set(-0.07 + i * 0.028, 0.125, 0.004); r.rotation.y = Math.PI / 2; nb.add(r); }
  const pen = P.pen = grp(n.gripR); pen.visible = false; pen.rotation.set(0.88, 0, 0.5); pen.position.set(0, -0.01, 0.01); pen.userData.s0 = 1.5;
  pen.add(mesh(latheGeo([[0, -0.085], [0.004, -0.082], [0.011, -0.055], [0.011, 0.06], [0.012, 0.062], [0.012, 0.08], [0.008, 0.088], [0, 0.089]], { rows: 40, seg: 20, tension: 0.1 }), softMat(0xffffff, { map: canvasTex(8, 64, (c) => { c.fillStyle = '#ffd24d'; c.fillRect(0, 0, 8, 64); c.fillStyle = '#ffb7c0'; c.fillRect(0, 0, 8, 9); c.fillStyle = '#c9ccd8'; c.fillRect(0, 9, 8, 3); c.fillStyle = '#f5d9b5'; c.fillRect(0, 53, 8, 8); c.fillStyle = '#5a4a4a'; c.fillRect(0, 61, 8, 3); }) })));
}
// 筆記本頁面：字跡逐漸寫出來
export function makeNotes() {
  const cv = document.createElement('canvas'); cv.width = 144; cv.height = 184; const c = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; let last = -1;
  const draw = (t) => {
    const n = Math.floor(t * 9) % 70; if (n === last) return; last = n;
    c.fillStyle = '#fffdf6'; c.fillRect(0, 0, 144, 184); c.strokeStyle = '#d6e6fb'; c.lineWidth = 1.5;
    for (let y = 30; y < 180; y += 22) { c.beginPath(); c.moveTo(10, y); c.lineTo(134, y); c.stroke(); }
    c.strokeStyle = '#6b6f9c'; c.lineWidth = 2.6; c.lineCap = 'round'; c.lineJoin = 'round';
    for (let i = 0; i < n; i++) { const row = Math.floor(i / 10), k = i % 10, x = 14 + k * 12, y = 26 + row * 22; c.beginPath(); c.moveTo(x, y); c.lineTo(x + 3, y - 6 - ((i * 7) % 5)); c.lineTo(x + 6, y - ((i * 3) % 4)); c.lineTo(x + 9, y - 5); c.stroke(); }
    tex.needsUpdate = true;
  };
  draw(0); return { tex, draw };
}

// ───────── 天竺鼠寵物：白色毛球（多層殼毛） ─────────
function furTex() {
  return canvasTex(256, 256, (c) => {
    c.fillStyle = '#000'; c.fillRect(0, 0, 256, 256);
    let s = 7; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < 9000; i++) { const x = rnd() * 256, y = rnd() * 256, v = Math.floor(110 + rnd() * 145), r = 1.3 + rnd() * 1.2; c.fillStyle = `rgb(${v},${v},${v})`; for (const ox of [-256, 0, 256]) for (const oy of [-256, 0, 256]) { c.beginPath(); c.arc(x + ox, y + oy, r, 0, 7); c.fill(); } }
  });
}
function buildPet(sp) {
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
