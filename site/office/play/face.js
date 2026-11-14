// 臉：Canvas 即時畫的貼圖。所有表情都是同一組參數，參數之間平滑內插。
import * as THREE from 'three';

// open 眼睛張開量；arc 閉眼時的弧（+1 笑眼 ∩、-1 睡眼 ∪）；lidT/lidB 上下眼皮；lidA 眼皮斜度（+生氣、-難過）
// eyeS 眼睛大小；brow/browA/browY 眉毛；mCurve 嘴角（+笑 -垮）；mOpen 張嘴；mW 嘴寬；mRound 圓嘴；smirk 歪嘴
const B = { open: 1, arc: 0, lidT: 0, lidA: 0, lidB: 0, eyeS: 1, hl: 1, brow: 0, browA: 0, browY: 0, mCurve: 0.55, mOpen: 0, mW: 1, mRound: 0, smirk: 0, blush: 0.6, hatch: 0, tear: 0, dizzy: 0, sparkle: 0, cheek: 0 };
const E = (o) => ({ ...B, ...o });
export const EXPR = {
  neutral: E({}),
  happy: E({ open: 0, arc: 1, mCurve: 1, mOpen: 0.72, mW: 1.2, blush: 0.9, lidB: 0 }),
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
  // ── 情緒層（world/js/mind.js）用的細緻表情：新舊兩種角色共用這張表（新做法的臉在 char/facerig.js 會複製這張表）
  smile: E({ mCurve: 0.78, mW: 1.05, blush: 0.8 }),
  confused: E({ brow: 1, browA: -0.5, browY: 7, mCurve: 0, mOpen: 0.2, mW: 0.55, mRound: 1, blush: 0.45 }),
  pout: E({ lidT: 0.14, lidA: -0.5, brow: 1, browA: -0.55, browY: 4, mCurve: -0.7, mOpen: 0, mW: 0.55, mRound: 0.35, blush: 0.8, tear: 0.35, hl: 1.15 }),          // 委屈嘟嘴：嘴角下垂、眼眶微濕
  worried: E({ lidT: 0.06, lidA: -0.6, brow: 1, browA: -1, browY: 8, mCurve: -0.35, mW: 0.75, blush: 0.35, eyeS: 1.04, hl: 1.15 }),                                 // 擔心：八字眉
  wary: E({ lidT: 0.3, lidB: 0.12, lidA: 0.4, brow: 1, browA: 0.55, browY: -2, mCurve: -0.15, mW: 0.7, smirk: 0.2, blush: 0.25, eyeS: 0.94, hl: 0.8 }),              // 戒備：半瞇眼、眉頭微壓
  relieved: E({ lidT: 0.32, lidB: 0.05, brow: 0.6, browA: -0.4, browY: 6, mCurve: 0.65, mOpen: 0.35, mW: 0.8, mRound: 0.8, blush: 0.8 }),                           // 鬆一口氣
  blank: E({ eyeS: 0.86, hl: 0.45, lidT: 0.2, mCurve: 0, mOpen: 0, mW: 0.55, blush: 0.15 }),                                                                         // 呆滯
  cry: E({ lidT: 0.2, lidA: -1, brow: 1, browA: -1, browY: 7, mCurve: -1, mOpen: 0.55, mW: 1.0, blush: 0.5, tear: 1.6, hl: 1.3, eyeS: 1.05 }),                      // 大聲哭（很少用）
  grateful: E({ eyeS: 1.12, hl: 1.45, brow: 0.7, browA: -0.5, browY: 9, mCurve: 1, mOpen: 0.45, mW: 1.05, blush: 1.1, tear: 0.9, sparkle: 1 }),                      // 驚喜感激（眼眶含淚笑）
  fistpump: E({ lidT: 0.18, brow: 1, browA: 0.5, browY: -3, mCurve: 0.9, mOpen: 0.6, mW: 1.1, blush: 0.9, eyeS: 1.04 }),                                           // 握拳：好勝的開心
  sulkf: E({ lidT: 0.3, lidA: 0.9, brow: 1, browA: 0.7, browY: -5, mCurve: -0.6, mOpen: 0, mW: 0.6, mRound: 0.3, smirk: 0.3, blush: 1 }),                            // 賭氣
  scared: E({ eyeS: 1.3, hl: 1.4, brow: 1, browA: -0.5, browY: 20, mCurve: -0.4, mOpen: 1.0, mW: 0.85, mRound: 0.6, blush: 0.1 }),                                   // 驚叫
  cough: E({ open: 0.25, arc: -0.4, lidA: 0.5, brow: 1, browA: -0.3, mCurve: -0.2, mOpen: 0.85, mW: 0.6, mRound: 1, blush: 0.8, tear: 0.2 }),                       // 咳一下
  giggle: E({ lidT: 0.12, brow: 0.5, browA: 0.3, mCurve: 0.9, mOpen: 0.2, mW: 0.7, smirk: 0.4, blush: 1, cheek: 0.6 }),                                             // 小小偷笑
};
const KEYS = Object.keys(B);
const hexA = (h, a) => { const n = parseInt(h.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };

export class Face {
  constructor(style, size = 512) {
    this.size = size;
    this.st = Object.assign({ kind: 'soft', ex: 78, ey: 276, rx: 27, ry: 35, my: 322, mw: 17, eye: '#3b2723', eye2: '#6a4438', mouthIn: '#8a3344', tongue: '#ff8fa0', blush: '255,128,140', line: 6, wmouth: false, glow: null, visor: null }, style);
    const c = this.cv = document.createElement('canvas'); c.width = c.height = size;
    this.g = c.getContext('2d');
    const t = this.tex = new THREE.CanvasTexture(c);
    t.premultiplyAlpha = true; t.colorSpace = THREE.NoColorSpace; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.anisotropy = 4;
    this.cur = { ...EXPR.neutral }; this.target = EXPR.neutral;
    this.blinkT = 2; this.blink = 0; this.blinkV = 0; this.gx = 0; this.gy = 0; this.talk = 0; this.time = 0; this.extraOpen = 0;
    this.draw();
  }
  // 沒變就不重畫（辦公室一次有幾十隻，逐幀重畫＋上傳貼圖太貴）
  changed() {
    if (this.scan >= 0) { this._sig = ''; return true; }
    const c = this.cur; if (this.dirty || c.dizzy > 0.05 || c.tear > 0.04 || c.sparkle > 0.05) { this.dirty = false; this._sig = ''; return true; }
    let s = Math.round(this.blink * 16) + '|' + Math.round(this.gx * 24) + '|' + Math.round(this.gy * 24) + '|' + Math.round(this.talk * 24);
    for (const k of KEYS) s += '|' + Math.round(c[k] * 40);
    if (s === this._sig) return false; this._sig = s; return true;
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
    if (this.changed()) this.draw();
  }
  draw() {
    const g = this.g, s = this.st, c = this.cur, T = this.time;
    const K = this.size / 512; g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, this.size, this.size); g.setTransform(K, 0, 0, K, 0, 0);
    const cx = 256 + this.gx * 9, gy = this.gy * 7;
    const glow = s.glow;
    if (s.belly) { g.fillStyle = s.bellyCol || '#fff6e6'; g.beginPath(); if (s.flameInner) { const gr = g.createRadialGradient(256, 340, 10, 256, 340, 190); gr.addColorStop(0, '#fffbe0'); gr.addColorStop(0.6, s.bellyCol || '#ffe07a'); gr.addColorStop(1, s.bellyCol || '#ffe07a'); g.fillStyle = gr; g.moveTo(256, 150); g.bezierCurveTo(290, 215, 372, 270, 372, 365); g.bezierCurveTo(372, 440, 320, 492, 256, 492); g.bezierCurveTo(192, 492, 140, 440, 140, 365); g.bezierCurveTo(140, 270, 222, 215, 256, 150); } else if (s.heart) { g.moveTo(256, 308); g.bezierCurveTo(256, 262, 156, 262, 156, 332); g.bezierCurveTo(156, 404, 236, 452, 256, 510); g.bezierCurveTo(276, 452, 356, 404, 356, 332); g.bezierCurveTo(356, 262, 256, 262, 256, 308); } else g.ellipse(256, 440, 104, 140, 0, 0, 7); g.fill(); }
    if (s.visor) {
      const v = s.visor; g.save();
      const gr = g.createLinearGradient(0, v.y, 0, v.y + v.h); gr.addColorStop(0, v.c0); gr.addColorStop(1, v.c1);
      g.fillStyle = gr; g.beginPath(); g.roundRect(256 - v.w / 2, v.y, v.w, v.h, v.r); g.fill();
      if (v.border) { g.strokeStyle = v.border; g.lineWidth = 16; g.beginPath(); g.roundRect(256 - v.w / 2 + 8, v.y + 8, v.w - 16, v.h - 16, Math.max(4, v.r - 6)); g.stroke(); }
      g.globalAlpha = 0.1; g.fillStyle = '#fff'; g.beginPath(); g.ellipse(256 - v.w * 0.2, v.y + v.h * 0.2, v.w * 0.24, v.h * 0.1, -0.25, 0, 7); g.fill();
      if (this.scan >= 0) { g.beginPath(); g.roundRect(256 - v.w / 2, v.y, v.w, v.h, v.r); g.clip(); const sx = 256 - v.w / 2 + this.scan * v.w, sg = g.createLinearGradient(sx - 46, 0, sx + 4, 0); sg.addColorStop(0, 'rgba(255,214,107,0)'); sg.addColorStop(1, 'rgba(255,214,107,0.55)'); g.fillStyle = sg; g.fillRect(sx - 46, v.y, 50, v.h); g.fillStyle = 'rgba(255,238,170,0.95)'; g.fillRect(sx, v.y, 5, v.h); }
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
      const a = Math.min(0.9, 0.62 * bl);
      gr.addColorStop(0, `rgba(${s.blush},${a})`); gr.addColorStop(0.6, `rgba(${s.blush},${a * 0.55})`); gr.addColorStop(1, `rgba(${s.blush},0)`);
      g.fillStyle = gr; g.beginPath(); g.arc(0, 0, rw, 0, 7); g.fill(); g.restore();
      if (c.hatch > 0.05) {
        g.save(); g.globalAlpha = Math.min(1, c.hatch) * 0.75; g.strokeStyle = `rgb(${s.blush})`; g.lineWidth = 3.4; g.lineCap = 'round';
        for (let i = -1; i <= 1; i++) { g.beginPath(); g.moveTo(bx + i * 9 + 3, by - 6); g.lineTo(bx + i * 9 - 3, by + 6); g.stroke(); }
        g.restore();
      }
    }
    if (s.freck && bl > 0.02) { g.save(); g.fillStyle = `rgba(${s.blush},0.75)`; for (const sd of [-1, 1]) for (const [fx, fy, fr] of [[-9, -4, 3.2], [3, -9, 2.8], [10, 1, 3], [-2, 5, 2.6], [-12, 9, 2.4]]) { g.beginPath(); g.arc(cx + sd * (s.ex + s.rx * 1.25) + fx * sd, s.ey + s.ry * 0.95 + gy * 0.6 + fy, fr, 0, 7); g.fill(); } g.restore(); }
    // 眼睛
    const col = glow || s.eye;
    for (const sd of [-1, 1]) {
      const ex = cx + sd * s.ex, ey = s.ey + gy;
      const rx = Math.abs(s.rx * c.eyeS), ry = Math.abs(s.ry * c.eyeS);
      g.save(); g.translate(ex, ey);
      if (glow) { g.shadowColor = glow; g.shadowBlur = 16; }
      if (c.dizzy > 0.5) {
        g.strokeStyle = col; g.lineWidth = s.line; g.lineCap = 'round'; g.beginPath();
        for (let i = 0; i <= 40; i++) { const a = i / 40 * Math.PI * 4.2 + T * 7 * sd, r = i / 40 * rx * 1.02; const X = Math.cos(a) * r, Y = Math.sin(a) * r; i ? g.lineTo(X, Y) : g.moveTo(X, Y); }
        g.stroke(); g.restore(); continue;
      }
      if (open > 0.1) {
        const oy = Math.max(0.01, ry * Math.min(1, open));
        g.save();
        // 眼皮：用裁切區做上、下眼皮
        const top = -ry - 4 + c.lidT * 2 * ry, sl = c.lidA * ry * 0.42 * -sd, bot = ry + 4 - c.lidB * ry * 1.1;
        g.beginPath(); g.moveTo(-rx - 8, top - sl); g.lineTo(rx + 8, top + sl); g.lineTo(rx + 8, bot);
        g.quadraticCurveTo(0, bot - c.lidB * ry * 0.8, -rx - 8, bot); g.closePath(); g.clip();
        g.beginPath(); g.ellipse(0, 0, rx, oy, 0, 0, 7);
        if (glow) g.fillStyle = glow;
        else { const gr = g.createLinearGradient(0, -oy, 0, oy); gr.addColorStop(0, s.eye); gr.addColorStop(0.55, s.eye); gr.addColorStop(1, s.eye2); g.fillStyle = gr; }
        g.fill();
        if (s.iris && !glow && s.kind !== 'lcd') {
          g.save(); g.beginPath(); g.ellipse(0, 0, rx, oy, 0, 0, 7); g.clip();
          const ig = g.createRadialGradient(0, oy * 0.42, 0, 0, oy * 0.42, rx * 1.05); ig.addColorStop(0, hexA(s.iris, 0.95)); ig.addColorStop(0.6, hexA(s.iris, 0.5)); ig.addColorStop(1, hexA(s.iris, 0));
          g.fillStyle = ig; g.fillRect(-rx, -oy, rx * 2, oy * 2);
          g.strokeStyle = hexA(s.eye, 0.55); g.lineWidth = Math.max(3, rx * 0.12); g.beginPath(); g.ellipse(0, 0, rx - 1.5, oy - 1.5, 0, 0, 7); g.stroke();
          g.restore();
        }
        if (s.kind === 'lcd') { }
        else if (!glow) {
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
      const bA = Math.max(c.brow, (s.restBrow || 0) * (1 - c.arc * 0.0));
      if (bA > 0.04) {
        g.save(); g.globalAlpha = Math.min(1, bA) * (c.brow > 0.04 ? 1 : 0.8); g.strokeStyle = col; g.lineWidth = s.line * (s.restBrow && c.brow < 0.04 ? 0.85 : 1); g.lineCap = 'round';
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
    if (s.glasses) {
      g.save(); g.strokeStyle = s.glasses; g.lineWidth = 6; const R = s.ry * 1.22, ey = s.ey + gy * 0.4;
      for (const sd of [-1, 1]) { g.fillStyle = 'rgba(255,255,255,.16)'; g.beginPath(); g.arc(cx + sd * s.ex, ey, R, 0, 7); g.fill(); g.stroke(); }
      g.save(); g.strokeStyle = 'rgba(255,255,255,.6)'; g.lineWidth = 4; for (const sd of [-1, 1]) { g.beginPath(); g.arc(cx + sd * s.ex, ey, R * 0.7, Math.PI * 1.15, Math.PI * 1.45); g.stroke(); } g.restore();
      g.beginPath(); g.moveTo(cx - s.ex + R, ey - 4); g.quadraticCurveTo(cx, ey - 14, cx + s.ex - R, ey - 4); g.stroke(); g.restore();
    }
    // 擁有者硬性規則：不畫鼻子（鼻點、鼻孔點一律不畫）
    if (s.whisk) { g.fillStyle = s.eye; g.globalAlpha = 0.55; for (const sd of [-1, 1]) for (const [x, y] of [[30, -4], [42, 6], [30, 14]]) { g.beginPath(); g.arc(cx + sd * x, s.my + y + gy * 0.8, 2.6, 0, 7); g.fill(); } g.globalAlpha = 1; }
    if (s.noMouth) { this.tex.needsUpdate = true; return; }
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
        if (s.tooth) { g.fillStyle = '#fffaf0'; g.beginPath(); g.roundRect(-w * 0.16, tY * 0.8 - 2, w * 0.32, H * 0.34 + 2, 3); g.fill(); }
        g.fillStyle = s.tongue; g.beginPath(); g.ellipse(0, bY + H * 0.3, w * 0.62, H * 0.62, 0, 0, 7); g.fill(); g.restore();
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
