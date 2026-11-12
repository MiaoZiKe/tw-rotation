// 臉：Canvas 即時畫的貼圖。所有表情都是同一組參數，參數之間平滑內插。
import * as THREE from 'three';

// open 眼睛張開量；arc 閉眼時的弧（+1 笑眼 ∩、-1 睡眼 ∪）；lidT/lidB 上下眼皮；lidA 眼皮斜度（+生氣、-難過）
// eyeS 眼睛大小；brow/browA/browY 眉毛；mCurve 嘴角（+笑 -垮）；mOpen 張嘴；mW 嘴寬；mRound 圓嘴；smirk 歪嘴
const B = { open: 1, arc: 0, lidT: 0, lidA: 0, lidB: 0, eyeS: 1, hl: 1, brow: 0, browA: 0, browY: 0, mCurve: 0.55, mOpen: 0, mW: 1, mRound: 0, smirk: 0, blush: 0.6, hatch: 0, tear: 0, dizzy: 0, sparkle: 0, cheek: 0 };
const E = (o) => ({ ...B, ...o });
export const EXPR = {
  neutral: E({}),
  happy: E({ open: 0, arc: 1, mCurve: 1, mOpen: 0.45, mW: 1.15, blush: 0.9, lidB: 0 }),
  laugh: E({ open: 0, arc: 1, mCurve: 1, mOpen: 1, mW: 1.5, blush: 1, eyeS: 1.05 }),
  surprised: E({ eyeS: 1.22, hl: 1.25, brow: 1, browY: 16, mCurve: 0, mOpen: 0.75, mW: 0.62, mRound: 1, blush: 0.35 }),
  angry: E({ lidT: 0.34, lidA: 1, brow: 1, browA: 1, browY: -6, mCurve: -0.9, mOpen: 0.28, mW: 1.0, blush: 0.9, eyeS: 0.96 }),
  sad: E({ lidT: 0.22, lidA: -1, brow: 1, browA: -1, browY: 6, mCurve: -1, mOpen: 0, mW: 0.85, blush: 0.3, tear: 1, hl: 1.25 }),
  sleepy: E({ lidT: 0.56, lidB: 0.1, mCurve: 0.1, mOpen: 0.12, mW: 0.6, mRound: 0.8, blush: 0.5, hl: 0.6 }),
  shy: E({ lidT: 0.18, lidB: 0.3, mCurve: 0.5, mW: 0.6, blush: 1.5, hatch: 1, hl: 1.2, brow: 0.6, browA: -0.6, browY: 4 }),
  smug: E({ lidT: 0.42, lidB: 0.16, brow: 1, browA: 0.45, browY: 2, mCurve: 0.9, smirk: 1, mW: 1.05, blush: 0.6 }),
  // 以下是動作用的表情
  bliss: E({ open: 0, arc: 1, mCurve: 0.9, mW: 0.8, blush: 1.3 }),
  dizzy: E({ dizzy: 1, mCurve: -0.2, mOpen: 0.5, mW: 0.7, mRound: 0.9, blush: 0.4 }),
  yawn: E({ open: 0, arc: -0.3, mOpen: 1.25, mW: 0.85, mRound: 1, mCurve: 0, blush: 0.5, tear: 0.35 }),
  sleep: E({ open: 0, arc: -1, mCurve: 0.2, mOpen: 0.1, mW: 0.5, mRound: 1, blush: 0.7 }),
  eatOpen: E({ eyeS: 1.08, sparkle: 1, mOpen: 1.3, mW: 1.1, mRound: 0.85, mCurve: 0.3, blush: 0.9, hl: 1.3 }),
  chew: E({ open: 0, arc: 1, mCurve: 0.6, mW: 0.75, blush: 1.2, cheek: 1 }),
  effort: E({ open: 0, arc: -0.6, lidA: 1, brow: 1, browA: 0.8, mCurve: -0.3, mW: 0.9, blush: 1.0 }),
  whee: E({ eyeS: 1.12, hl: 1.2, mCurve: 0.8, mOpen: 0.9, mW: 1.1, blush: 0.8 }),
  ouch: E({ open: 0, arc: -0.2, lidA: 1, brow: 1, browA: -0.7, browY: 4, mCurve: -0.6, mOpen: 0.4, mW: 0.9, blush: 0.5, tear: 0.5 }),
  look: E({ eyeS: 1.04, mCurve: 0.35, mW: 0.8 }),
};
const KEYS = Object.keys(B);

export class Face {
  constructor(style) {
    this.st = Object.assign({ kind: 'soft', ex: 78, ey: 276, rx: 27, ry: 35, my: 322, mw: 17, eye: '#3b2723', eye2: '#6a4438', mouthIn: '#8a3344', tongue: '#ff8fa0', blush: '255,128,140', line: 6, wmouth: false, glow: null, visor: null }, style);
    const c = this.cv = document.createElement('canvas'); c.width = c.height = 512;
    this.g = c.getContext('2d');
    const t = this.tex = new THREE.CanvasTexture(c);
    t.premultiplyAlpha = true; t.colorSpace = THREE.NoColorSpace; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.anisotropy = 4;
    this.cur = { ...EXPR.neutral }; this.target = EXPR.neutral;
    this.blinkT = 2; this.blink = 0; this.blinkV = 0; this.gx = 0; this.gy = 0; this.talk = 0; this.time = 0; this.extraOpen = 0;
    this.draw();
  }
  set(name) { this.target = EXPR[name] || EXPR.neutral; this.name = name; }
  update(dt, speed = 12) {
    this.time += dt;
    const k = 1 - Math.exp(-dt * speed), c = this.cur, t = this.target;
    for (const key of KEYS) c[key] += (t[key] - c[key]) * k;
    // 眨眼：隨機間隔，偶爾連眨兩下
    this.blinkT -= dt;
    if (this.blinkT <= 0) { this.blinkV = 1; this.blinkT = Math.random() < 0.2 ? 0.28 : 1.8 + Math.random() * 3.6; }
    if (this.blinkV > 0) { this.blink += dt / 0.055; if (this.blink >= 1) { this.blink = 1; this.blinkV = -1; } }
    else if (this.blinkV < 0) { this.blink -= dt / 0.09; if (this.blink <= 0) { this.blink = 0; this.blinkV = 0; } }
    this.draw();
  }
  draw() {
    const g = this.g, s = this.st, c = this.cur, T = this.time;
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, 512, 512);
    const cx = 256 + this.gx * 9, gy = this.gy * 7;
    const glow = s.glow;
    if (s.visor) {
      const v = s.visor; g.save();
      const gr = g.createLinearGradient(0, v.y, 0, v.y + v.h); gr.addColorStop(0, v.c0); gr.addColorStop(1, v.c1);
      g.fillStyle = gr; g.beginPath(); g.roundRect(256 - v.w / 2, v.y, v.w, v.h, v.r); g.fill();
      g.globalAlpha = 0.1; g.fillStyle = '#fff'; g.beginPath(); g.ellipse(256 - v.w * 0.2, v.y + v.h * 0.2, v.w * 0.24, v.h * 0.1, -0.25, 0, 7); g.fill();
      g.restore();
    }
    const open = Math.max(0, c.open * (1 - this.blink));
    // 腮紅
    const bl = c.blush * (s.blushAmt ?? 1);
    if (bl > 0.02) for (const sd of [-1, 1]) {
      const bx = cx + sd * (s.ex + s.rx * 1.25), by = s.ey + s.ry * 0.95 + gy * 0.6 - c.cheek * 4;
      const rw = s.rx * 1.25 * (1 + c.cheek * 0.25), rh = s.rx * 0.72 * (1 + c.cheek * 0.3);
      g.save(); g.translate(bx, by); g.scale(1, rh / rw);
      const gr = g.createRadialGradient(0, 0, 0, 0, 0, rw);
      const a = Math.min(0.85, 0.5 * bl);
      gr.addColorStop(0, `rgba(${s.blush},${a})`); gr.addColorStop(0.6, `rgba(${s.blush},${a * 0.55})`); gr.addColorStop(1, `rgba(${s.blush},0)`);
      g.fillStyle = gr; g.beginPath(); g.arc(0, 0, rw, 0, 7); g.fill(); g.restore();
      if (c.hatch > 0.05) {
        g.save(); g.globalAlpha = Math.min(1, c.hatch) * 0.75; g.strokeStyle = `rgb(${s.blush})`; g.lineWidth = 3.4; g.lineCap = 'round';
        for (let i = -1; i <= 1; i++) { g.beginPath(); g.moveTo(bx + i * 9 + 3, by - 6); g.lineTo(bx + i * 9 - 3, by + 6); g.stroke(); }
        g.restore();
      }
    }
    // 眼睛
    const col = glow || s.eye;
    for (const sd of [-1, 1]) {
      const ex = cx + sd * s.ex, ey = s.ey + gy;
      const rx = s.rx * c.eyeS, ry = s.ry * c.eyeS;
      g.save(); g.translate(ex, ey);
      if (glow) { g.shadowColor = glow; g.shadowBlur = 16; }
      if (c.dizzy > 0.5) {
        g.strokeStyle = col; g.lineWidth = s.line; g.lineCap = 'round'; g.beginPath();
        for (let i = 0; i <= 40; i++) { const a = i / 40 * Math.PI * 4.2 + T * 7 * sd, r = i / 40 * rx * 1.02; const X = Math.cos(a) * r, Y = Math.sin(a) * r; i ? g.lineTo(X, Y) : g.moveTo(X, Y); }
        g.stroke(); g.restore(); continue;
      }
      if (open > 0.1) {
        const oy = ry * Math.min(1, open);
        g.save();
        // 眼皮：用裁切區做上、下眼皮
        const top = -ry - 4 + c.lidT * 2 * ry, sl = c.lidA * ry * 0.42 * -sd, bot = ry + 4 - c.lidB * ry * 1.1;
        g.beginPath(); g.moveTo(-rx - 8, top - sl); g.lineTo(rx + 8, top + sl); g.lineTo(rx + 8, bot);
        g.quadraticCurveTo(0, bot - c.lidB * ry * 0.8, -rx - 8, bot); g.closePath(); g.clip();
        g.beginPath(); g.ellipse(0, 0, rx, oy, 0, 0, 7);
        if (glow) g.fillStyle = glow;
        else { const gr = g.createLinearGradient(0, -oy, 0, oy); gr.addColorStop(0, s.eye); gr.addColorStop(0.55, s.eye); gr.addColorStop(1, s.eye2); g.fillStyle = gr; }
        g.fill();
        if (!glow) {
          const ha = Math.min(1, (open - 0.1) / 0.5);
          g.shadowBlur = 0; g.globalAlpha = ha; g.fillStyle = '#fff';
          const hs = c.hl, hx = -rx * 0.3 - this.gx * 2.5, hy = -oy * 0.36 - this.gy * 2;
          g.beginPath(); g.ellipse(hx, hy, rx * 0.36 * hs, rx * 0.36 * hs * Math.min(1, open * 1.2), 0, 0, 7); g.fill();
          g.globalAlpha = ha * 0.85; g.beginPath(); g.arc(rx * 0.36, oy * 0.42, rx * 0.15 * hs, 0, 7); g.fill();
          if (c.sparkle > 0.05) { g.globalAlpha = c.sparkle * (0.6 + 0.4 * Math.sin(T * 9)); g.beginPath(); g.arc(rx * 0.05, oy * 0.55, rx * 0.11, 0, 7); g.fill(); g.beginPath(); g.arc(-rx * 0.45, oy * 0.3, rx * 0.08, 0, 7); g.fill(); }
        } else {
          g.shadowBlur = 0; g.globalAlpha = 0.55 * Math.min(1, (open - 0.1) / 0.5); g.fillStyle = '#fff';
          g.beginPath(); g.ellipse(-rx * 0.28, -oy * 0.36, rx * 0.3, rx * 0.3 * Math.min(1, open * 1.2), 0, 0, 7); g.fill();
        }
        g.restore();
      }
      if (open < 0.3) {
        g.globalAlpha = 1 - open / 0.3; g.strokeStyle = col; g.lineWidth = s.line + 1; g.lineCap = 'round';
        const w = rx * 1.08, h = c.arc * rx * 1.0;
        g.beginPath(); g.moveTo(-w, h * 0.42); g.quadraticCurveTo(0, -h * 1.15, w, h * 0.42); g.stroke();
      }
      g.restore();
      // 眉毛
      if (c.brow > 0.04) {
        g.save(); g.globalAlpha = Math.min(1, c.brow); g.strokeStyle = col; g.lineWidth = s.line; g.lineCap = 'round';
        if (glow) { g.shadowColor = glow; g.shadowBlur = 12; }
        g.translate(ex, ey - ry - 13 - c.browY + c.lidT * ry * 0.5); g.rotate(-c.browA * 0.38 * sd);
        g.beginPath(); g.moveTo(-rx * 0.62, 0); g.quadraticCurveTo(0, -3, rx * 0.62, 0); g.stroke(); g.restore();
      }
      // 眼淚
      if (c.tear > 0.04) {
        g.save(); g.globalAlpha = Math.min(1, c.tear) * 0.92;
        const ty = ey + ry * 0.85 + 4 + Math.sin(T * 3 + sd) * 2.5, tx = ex + sd * rx * 0.55, k = 8 + c.tear * 3;
        g.translate(tx, ty); g.beginPath(); g.moveTo(0, -k * 1.2); g.bezierCurveTo(k, -k * 0.1, k * 0.85, k, 0, k); g.bezierCurveTo(-k * 0.85, k, -k, -k * 0.1, 0, -k * 1.2);
        g.fillStyle = glow ? '#bfeaff' : '#9fd8ff'; g.fill(); g.globalAlpha *= 0.8; g.fillStyle = '#fff'; g.beginPath(); g.arc(-k * 0.25, k * 0.1, k * 0.22, 0, 7); g.fill();
        g.restore();
      }
    }
    // 嘴
    const mo = Math.max(0, c.mOpen + this.talk);
    const mx = cx + this.gx * -1.5 + c.smirk * 7, my = s.my + gy * 0.8;
    const w = s.mw * c.mW * (1 - 0.35 * Math.min(1, c.mRound) * Math.min(1, mo * 2));
    g.save(); g.translate(mx, my); g.rotate(-c.smirk * 0.2);
    g.strokeStyle = col; g.lineCap = 'round'; g.lineJoin = 'round'; g.lineWidth = s.line;
    if (glow) { g.shadowColor = glow; g.shadowBlur = 12; }
    if (mo > 0.06) {
      const H = mo * s.mw * 1.55, cc = (c.mCurve + 1) / 2, r = Math.min(1, c.mRound);
      const tY = -H * ((1 - cc) * (1 - r) + 0.5 * r), bY = H * (cc * (1 - r) + 0.5 * r);
      g.beginPath(); g.moveTo(-w, 0); g.bezierCurveTo(-w, tY * 1.33, w, tY * 1.33, w, 0); g.bezierCurveTo(w, bY * 1.33, -w, bY * 1.33, -w, 0); g.closePath();
      if (glow) { g.fillStyle = glow; g.globalAlpha = 0.9; g.fill(); }
      else {
        g.fillStyle = s.mouthIn; g.fill(); g.save(); g.clip();
        g.fillStyle = s.tongue; g.beginPath(); g.ellipse(0, bY + w * 0.25, w * 0.75, Math.max(3, H * 0.55), 0, 0, 7); g.fill(); g.restore();
        g.lineWidth = s.line * 0.8; g.stroke();
      }
    } else {
      const d = c.mCurve * w * 0.75;
      g.beginPath();
      if (s.wmouth && c.mCurve > 0 && c.smirk < 0.3) {
        const k = Math.min(1, c.mCurve * 1.6);
        g.moveTo(-w, -d * 0.2); g.quadraticCurveTo(-w * 0.5, d * (0.55 + 0.5 * k), 0, -d * 0.1 * k); g.quadraticCurveTo(w * 0.5, d * (0.55 + 0.5 * k), w, -d * 0.2);
      } else { g.moveTo(-w, -d * 0.3); g.quadraticCurveTo(0, d * 1.25, w, -d * 0.3 - c.smirk * 5); }
      g.stroke();
    }
    g.restore();
    this.tex.needsUpdate = true;
  }
}
