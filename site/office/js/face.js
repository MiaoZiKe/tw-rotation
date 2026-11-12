// 臉：用 Canvas 2D 動態畫成貼圖（不是 SVG），貼在頭部前方的球面貼片上
// 座標單位是「度」：x＝左右方位角、y＝仰角（往上為正），所以畫出來貼到球面不會歪
import { THREE, clamp, lerp } from './core.js';

export const FACE_AZ = 126, FACE_EL = 135, FACE_TOP = 72; // 貼片涵蓋角度
const W = 768, H = 768;

export class Face {
  constructor(spec) {
    this.spec = spec;
    this.cv = document.createElement('canvas'); this.cv.width = W; this.cv.height = H;
    this.ctx = this.cv.getContext('2d');
    this.tex = new THREE.CanvasTexture(this.cv); this.tex.colorSpace = THREE.SRGBColorSpace; this.tex.anisotropy = 8;
    this.s = { blink: 0, mouth: 0, expr: 'neutral', lx: 0, ly: 0, t: 0 };
    this.key = ''; this.update();
  }
  update() {
    const s = this.s, anim = (s.expr === 'dizzy' || s.expr === 'sad' || s.expr === 'angry') ? Math.round(s.t * 12) : 0;
    const key = [Math.round(s.blink * 8), Math.round(s.mouth * 10), s.expr, Math.round(s.lx * 4), Math.round(s.ly * 4), anim].join('|');
    if (key === this.key) return; this.key = key; this.draw(); this.tex.needsUpdate = true;
  }
  draw() {
    const c = this.ctx, sp = this.spec, s = this.s, e = s.expr;
    c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, W, H);
    c.setTransform(W / FACE_AZ, 0, 0, -H / FACE_EL, W / 2, H * FACE_TOP / FACE_EL);
    c.lineCap = 'round'; c.lineJoin = 'round';
    const ey = sp.eyeY ?? -9, ex = sp.eyeX ?? 19, rx = sp.eyeRx ?? 7.2, ry = sp.eyeRy ?? 9.6;
    if (sp.pre) sp.pre(c, this);
    // 腮紅
    const bl = sp.blush ?? '#ff9aa8', ba = (sp.blushA ?? 0.6) * (e === 'happy' || e === 'smug' ? 1.25 : e === 'angry' ? 1.3 : 1);
    for (const sx of [-1, 1]) this.glow(sx * (ex + 9.5), ey - 11.5, 8.5, 5.2, e === 'angry' ? '#ff6f6f' : bl, clamp(ba));
    // 眼睛
    for (const sx of [-1, 1]) this.eye(sx * ex + s.lx * 1.6, ey + s.ly * 1.2, rx, ry, sx);
    // 眉毛
    this.brows(ex, ey + ry, rx);
    // 鼻、嘴
    if (sp.nose) sp.nose(c, this);
    this.mouth(sp.mouthY ?? -27);
    // 生氣時臉上的斜線陰影／難過的淚
    if (e === 'sad') this.tears(ex, ey - ry);
    if (e === 'dizzy' || e === 'awk') this.sweat(ex + 13, ey + 15);
  }
  ell(x, y, rx, ry, rot = 0) { const c = this.ctx; c.beginPath(); c.ellipse(x, y, Math.max(0.01, rx), Math.max(0.01, ry), rot, 0, Math.PI * 2); }
  glow(x, y, rx, ry, color, a) {
    const c = this.ctx; c.save(); c.translate(x, y); c.scale(rx, ry);
    const g = c.createRadialGradient(0, 0, 0, 0, 0, 1); g.addColorStop(0, color); g.addColorStop(0.55, color); g.addColorStop(1, color + '00');
    c.globalAlpha = a; c.fillStyle = g; c.beginPath(); c.arc(0, 0, 1, 0, 7); c.fill(); c.restore();
  }
  eye(cx, cy, rx, ry, sx) {
    const c = this.ctx, sp = this.spec, s = this.s, e = s.expr, ink = sp.ink ?? '#3b2a2a';
    c.strokeStyle = ink; c.fillStyle = ink;
    if (e === 'happy') { // 笑瞇瞇 ∩
      c.lineWidth = 2.7; c.beginPath(); c.moveTo(cx - rx * 0.95, cy - 2.5); c.quadraticCurveTo(cx, cy + ry * 1.05, cx + rx * 0.95, cy - 2.5); c.stroke(); return;
    }
    if (e === 'dizzy') { // 暈眩螺旋
      c.lineWidth = 1.5; c.beginPath(); const ph = s.t * 6 * sx;
      for (let a = 0; a < 15; a += 0.2) { const r = a * 0.5, x = cx + Math.cos(a + ph) * r, y = cy + Math.sin(a + ph) * r; a ? c.lineTo(x, y) : c.moveTo(x, y); } c.stroke(); return;
    }
    let open = 1 - s.blink, k = 1;
    if (e === 'surprised') k = 1.13; if (e === 'think') open *= 0.92; if (e === 'smug') open *= 0.62; if (e === 'angry') open *= 0.86;
    if (open < 0.16) { c.lineWidth = 2.4; c.beginPath(); c.moveTo(cx - rx, cy - 1); c.quadraticCurveTo(cx, cy - 4.2, cx + rx, cy - 1); c.stroke(); return; }
    const RX = rx * k, RY = ry * k * open;
    c.save();
    // 上眼瞼切線：生氣內側壓低、難過外側壓低、得意整條壓平
    c.beginPath();
    const top = cy + RY + 2, lid = e === 'angry' ? [cy + RY * 0.05, cy + RY * 0.95] : e === 'sad' ? [cy + RY * 0.95, cy + RY * 0.25] : e === 'smug' ? [cy + RY * 0.55, cy + RY * 0.55] : [top, top];
    const xin = cx - sx * (RX + 2), xout = cx + sx * (RX + 2);
    c.moveTo(xin, lid[0]); c.lineTo(xout, lid[1]); c.lineTo(xout, cy - RY - 3); c.lineTo(xin, cy - RY - 3); c.closePath(); c.clip();
    this.ell(cx, cy, RX, RY); c.fillStyle = ink; c.fill(); c.clip();
    // 虹膜下半部的顏色漸層
    const g = c.createLinearGradient(0, cy + RY * 0.2, 0, cy - RY); g.addColorStop(0, (sp.iris ?? '#8a5a44') + '00'); g.addColorStop(1, sp.iris ?? '#8a5a44');
    c.fillStyle = g; this.ell(cx, cy - RY * 0.15, RX * 0.86, RY * 0.86); c.fill();
    if (e === 'surprised') { c.fillStyle = ink; this.ell(cx, cy, RX * 0.42, RY * 0.42); c.fill(); }
    // 高光：左上大、右下小
    const lookX = (e === 'think' ? 1.6 : 0), lookY = (e === 'think' ? 1.8 : 0);
    c.fillStyle = '#ffffff'; this.ell(cx - RX * 0.32 + lookX, cy + RY * 0.38 + lookY * open, RX * 0.36, RY * 0.3); c.fill();
    c.globalAlpha = 0.9; this.ell(cx + RX * 0.36 + lookX, cy - RY * 0.42, RX * 0.17, RY * 0.14); c.fill();
    c.restore();
    // 上睫毛弧線＋眼尾小翹
    if (sp.lash !== false && (e === 'neutral' || e === 'surprised' || e === 'think')) {
      c.lineWidth = 1.5; c.beginPath(); c.ellipse(cx, cy, RX + 0.3, RY + 0.3, 0, Math.PI * 0.12, Math.PI * 0.88); c.stroke();
      c.lineWidth = 1.3; c.beginPath(); c.moveTo(cx + sx * RX * 0.86, cy + RY * 0.55); c.lineTo(cx + sx * (RX + 2.3), cy + RY * 0.85); c.stroke();
    }
    if (e === 'smug' || e === 'angry' || e === 'sad') { c.lineWidth = 2.1; c.beginPath(); c.moveTo(xin + sx * 1.5, lid[0]); c.lineTo(xout - sx * 1.5, lid[1]); c.stroke(); }
  }
  brows(ex, top, rx) {
    const c = this.ctx, e = this.s.expr, sp = this.spec; if (sp.brow === false && (e === 'neutral' || e === 'happy')) return;
    c.strokeStyle = sp.browC ?? sp.ink ?? '#5a4038'; c.lineWidth = e === 'angry' ? 2.6 : e === 'neutral' || e === 'happy' ? 1.5 : 1.9;
    for (const sx of [-1, 1]) {
      let yi = 5.5, yo = 5, lift = 1.8; // 內側、外側高度
      if (e === 'angry') { yi = -0.5; yo = 6; lift = 0; } else if (e === 'sad') { yi = 7; yo = 2.5; lift = 0; } else if (e === 'surprised') { yi = yo = 8.5; lift = 2; }
      else if (e === 'think') { yi = sx > 0 ? 8 : 3.5; yo = sx > 0 ? 8.5 : 3; } else if (e === 'smug') { yi = 4; yo = sx > 0 ? 8 : 5; } else if (e === 'happy') { yi = yo = 6.5; }
      const sh = e === 'neutral' || e === 'happy' ? 0.5 : 0.78, x0 = sx * (ex - rx * sh), x1 = sx * (ex + rx * (sh + 0.05));
      c.beginPath(); c.moveTo(x0, top + yi); c.quadraticCurveTo((x0 + x1) / 2, top + (yi + yo) / 2 + lift, x1, top + yo); c.stroke();
    }
  }
  mouth(my) {
    const c = this.ctx, s = this.s, e = s.expr, sp = this.spec, ink = sp.ink ?? '#3b2a2a', m = s.mouth, cat = sp.catMouth;
    const inner = '#7c2f3c', tongue = '#ff8f9f';
    c.strokeStyle = ink; c.lineWidth = 1.8;
    const openShape = (w, hgt, yoff = 0, flatTop = false) => {
      c.save(); c.beginPath();
      if (flatTop) { c.moveTo(-w, my + yoff); c.quadraticCurveTo(0, my + yoff + 0.8, w, my + yoff); c.bezierCurveTo(w * 0.95, my + yoff - hgt * 1.25, -w * 0.95, my + yoff - hgt * 1.25, -w, my + yoff); }
      else c.ellipse(0, my + yoff - hgt * 0.5, w, hgt * 0.5 + 0.4, 0, 0, 7);
      c.fillStyle = inner; c.fill(); c.clip(); c.fillStyle = tongue; this.ell(0, my + yoff - hgt * (flatTop ? 0.95 : 0.9), w * 0.7, hgt * 0.42); c.fill(); c.restore();
      c.stroke();
    };
    if (cat) { // 貓嘴 ω
      c.beginPath(); c.moveTo(-4.6, my + 0.6); c.quadraticCurveTo(-2.6, my - 2.6, 0, my + 0.4); c.quadraticCurveTo(2.6, my - 2.6, 4.6, my + 0.6);
      if (e === 'sad' || e === 'angry') { c.beginPath(); c.moveTo(-4.2, my - 2.2); c.quadraticCurveTo(-2.2, my + 1.2, 0, my - 0.6); c.quadraticCurveTo(2.2, my + 1.2, 4.2, my - 2.2); }
      c.stroke();
      const mm = e === 'happy' ? Math.max(m, 0.55) : e === 'surprised' ? Math.max(m, 0.45) : e === 'angry' ? Math.max(m, 0.3) : m;
      if (mm > 0.06) openShape(2.2 + mm * 1.2, 1 + mm * 5, -1.6);
      return;
    }
    if (e === 'happy' || (e === 'smug' && m > 0.2)) return openShape(5.2 + m, 4.6 + m * 2.6, 1.2, true);
    if (e === 'surprised') return openShape(2.3 + m * 0.6, 5 + m * 2, 1.5);
    if (e === 'dizzy') { c.beginPath(); for (let i = 0; i <= 12; i++) { const x = -5 + i * 10 / 12, y = my - 1 + Math.sin(i * 1.57) * 1.2; i ? c.lineTo(x, y) : c.moveTo(x, y); } c.stroke(); return; }
    if (e === 'angry') { // 咬牙：開口方形露牙，講話時張更大
      if (m > 0.12) { c.save(); c.beginPath(); c.moveTo(-5, my + 1); c.lineTo(5, my + 1); c.quadraticCurveTo(5.4, my - 3.5 - m * 4, 0, my - 3.2 - m * 4.2); c.quadraticCurveTo(-5.4, my - 3.5 - m * 4, -5, my + 1); c.closePath(); c.fillStyle = inner; c.fill(); c.clip(); c.fillStyle = '#fff'; c.fillRect(-5, my - 0.6, 10, 1.8); c.restore(); c.stroke(); return; }
      c.lineWidth = 2; c.beginPath(); c.moveTo(-4.6, my - 2.6); c.quadraticCurveTo(0, my + 1.6, 4.6, my - 2.6); c.stroke(); return;
    }
    if (e === 'sad') { if (m > 0.15) return openShape(2.6, 2 + m * 3, 0); c.beginPath(); c.moveTo(-4, my - 2.4); c.quadraticCurveTo(-1.5, my + 0.8, 0, my - 0.2); c.quadraticCurveTo(1.5, my + 0.8, 4, my - 2.4); c.stroke(); return; }
    if (e === 'smug') { c.lineWidth = 2; c.beginPath(); c.moveTo(-4.5, my - 1); c.quadraticCurveTo(0, my - 3.6, 5.2, my + 1.8); c.stroke(); return; }
    if (e === 'think') { if (m > 0.15) return openShape(2.2, 1.5 + m * 3, 0); c.beginPath(); c.moveTo(-1, my - 1.2); c.quadraticCurveTo(1.6, my - 2.2, 4.4, my - 0.4); c.stroke(); return; }
    if (m > 0.08) return openShape(3 + m * 1.4, 1.2 + m * 5.4, 1);
    c.beginPath(); c.moveTo(-4, my); c.quadraticCurveTo(0, my - 3.4, 4, my); c.stroke();
  }
  tears(ex, y) {
    const c = this.ctx, t = this.s.t;
    for (const sx of [-1, 1]) {
      const w = 0.5 + 0.5 * Math.sin(t * 5 + sx);
      c.fillStyle = '#8fd4ff'; c.globalAlpha = 0.92;
      c.beginPath(); const x = sx * (ex + 2.5), yy = y - 1.5 - w * 1.2;
      c.moveTo(x, yy + 3.2); c.bezierCurveTo(x + 3.2, yy - 1.4, x + 2.2, yy - 4.6, x, yy - 4.6); c.bezierCurveTo(x - 2.2, yy - 4.6, x - 3.2, yy - 1.4, x, yy + 3.2); c.fill();
      c.fillStyle = '#fff'; c.globalAlpha = 0.8; this.ell(x - 0.8, yy - 2.6, 0.7, 1); c.fill(); c.globalAlpha = 1;
    }
  }
  sweat(x, y) {
    const c = this.ctx; c.fillStyle = '#9fdcff';
    c.beginPath(); c.moveTo(x, y + 4.5); c.bezierCurveTo(x + 3.6, y - 0.6, x + 2.6, y - 4.2, x, y - 4.2); c.bezierCurveTo(x - 2.6, y - 4.2, x - 3.6, y - 0.6, x, y + 4.5); c.fill();
    c.fillStyle = '#fff'; this.ell(x - 0.9, y - 1.8, 0.7, 1.1); c.fill();
  }
}

// 頭上的情緒符號（Canvas 貼圖做成的看板）：怒氣、問號、驚嘆號、亮晶晶、燈泡、汗滴、星星、蒸氣
const SYM = {};
export function symbolTex(kind) {
  if (SYM[kind]) return SYM[kind];
  const cv = document.createElement('canvas'); cv.width = cv.height = 192; const c = cv.getContext('2d');
  c.translate(96, 96); c.lineCap = 'round'; c.lineJoin = 'round';
  const out = (fill, stroke = '#fff', lw = 12) => { c.strokeStyle = stroke; c.lineWidth = lw; c.stroke(); c.fillStyle = fill; c.fill(); };
  if (kind === 'anger') { // 怒氣符號（四段弧線）
    for (const pass of [0, 1]) { c.strokeStyle = pass ? '#ff5468' : '#fff'; c.lineWidth = pass ? 15 : 27;
      for (let i = 0; i < 4; i++) { c.save(); c.rotate(i * Math.PI / 2); c.beginPath(); c.moveTo(14, 60); c.quadraticCurveTo(14, 14, 60, 14); c.stroke(); c.restore(); } }
  } else if (kind === 'q' || kind === 'ex') {
    c.font = '900 150px "Arial Rounded MT Bold","Nunito","Noto Sans TC",Arial,sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle';
    const ch = kind === 'q' ? '?' : '!'; c.lineWidth = 22; c.strokeStyle = '#fff'; c.strokeText(ch, 0, 8); c.fillStyle = kind === 'q' ? '#6aa8ff' : '#ff8a4c'; c.fillText(ch, 0, 8);
  } else if (kind === 'star' || kind === 'spark') {
    const n = kind === 'star' ? 5 : 4, r0 = 78, r1 = kind === 'star' ? 40 : 22; c.beginPath();
    for (let i = 0; i < n * 2; i++) { const a = -Math.PI / 2 + i * Math.PI / n, r = i % 2 ? r1 : r0; i ? c.lineTo(Math.cos(a) * r, Math.sin(a) * r) : c.moveTo(Math.cos(a) * r, Math.sin(a) * r); }
    c.closePath(); out(kind === 'star' ? '#ffd24d' : '#fff3a8', kind === 'star' ? '#fff' : '#ffc93c', kind === 'star' ? 14 : 8);
  } else if (kind === 'bulb') {
    c.beginPath(); c.arc(0, -14, 52, Math.PI * 0.75, Math.PI * 0.25); c.lineTo(22, 50); c.lineTo(-22, 50); c.closePath(); out('#ffe066');
    c.fillStyle = '#9aa3b5'; c.beginPath(); c.roundRect(-22, 50, 44, 26, 8); c.fill(); c.fillStyle = '#fff'; c.globalAlpha = 0.7; c.beginPath(); c.ellipse(-20, -30, 10, 16, 0.5, 0, 7); c.fill();
  } else if (kind === 'drop') {
    c.beginPath(); c.moveTo(0, -78); c.bezierCurveTo(60, 0, 46, 70, 0, 70); c.bezierCurveTo(-46, 70, -60, 0, 0, -78); out('#8fd4ff'); c.fillStyle = '#fff'; c.beginPath(); c.ellipse(-16, 30, 9, 16, 0.3, 0, 7); c.fill();
  } else if (kind === 'puff') {
    const g = c.createRadialGradient(0, 0, 10, 0, 0, 90); g.addColorStop(0, 'rgba(255,255,255,0.95)'); g.addColorStop(0.6, 'rgba(255,255,255,0.75)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    c.fillStyle = g; for (const [x, y, r] of [[0, 0, 60], [-34, 18, 40], [34, 14, 44], [6, -34, 42]]) { c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); }
  } else if (kind === 'dots') {
    c.beginPath(); c.roundRect(-84, -62, 168, 104, 44); c.moveTo(-40, 40); c.lineTo(-58, 78); c.lineTo(-8, 42); c.fillStyle = '#fff'; c.fill();
  } else if (kind === 'heart') {
    c.beginPath(); c.moveTo(0, 62); c.bezierCurveTo(-90, 0, -50, -70, 0, -28); c.bezierCurveTo(50, -70, 90, 0, 0, 62); out('#ff8fa8');
  } else if (kind === 'note') { c.fillStyle = '#b79cff'; c.beginPath(); c.ellipse(-22, 44, 26, 19, -0.4, 0, 7); c.fill(); c.fillRect(-2, -62, 12, 106); c.beginPath(); c.moveTo(-2, -62); c.quadraticCurveTo(50, -50, 56, -8); c.quadraticCurveTo(34, -32, 8, -34); c.fill(); }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; SYM[kind] = t; return t;
}
export function makeSymbol(kind, size = 0.2) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: symbolTex(kind), transparent: true, depthWrite: false, depthTest: false }));
  s.scale.setScalar(size); s.renderOrder = 20; s.visible = false; return s;
}
