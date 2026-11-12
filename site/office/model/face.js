// 臉部貼圖：用 Canvas 畫眼睛、眉毛、腮紅、嘴巴，貼在模型臉上（位置用模型座標，單位同模型）
// meta.face = { eyeL:[x,y], eyeR:[x,y], eyeR_: 半徑, mouth:[x,y], brow: 眉毛高出眼睛中心多少 }
export const EXPRESSIONS = { neutral: '微笑', happy: '開心', angry: '生氣', surprised: '驚訝', sad: '難過', dizzy: '暈眩', focus: '專注' };

export class FaceDecal {
  constructor(f) {
    this.f = Object.assign({ eyeL: [0.085, 1.56], eyeR: [-0.125, 1.56], r: 0.062, mouth: [-0.02, 1.455], brow: 0.105 }, f);
    const cx = (this.f.eyeL[0] + this.f.eyeR[0]) / 2, w = 0.62, h = 0.62, cy = this.f.eyeL[1] - 0.04;
    this.rect = { x: cx - w / 2, y: cy - h / 2, w, h };
    this.canvas = document.createElement('canvas'); this.canvas.width = this.canvas.height = 1024;
    this.ctx = this.canvas.getContext('2d'); this.key = '';
  }
  px(p) { const r = this.rect, S = this.canvas.width; return [(p[0] - r.x) / r.w * S, (1 - (p[1] - r.y) / r.h) * S]; }
  draw({ expr = 'neutral', blink = 0, mouth = 0, look = [0, 0] } = {}) {
    const key = [expr, blink.toFixed(2), mouth.toFixed(2), look[0].toFixed(2), look[1].toFixed(2)].join('|');
    if (key === this.key) return false; this.key = key;
    const c = this.ctx, S = this.canvas.width, u = S / this.rect.w, f = this.f, R = f.r * u;
    c.clearRect(0, 0, S, S);
    if (expr === 'grid') { // 除錯：每 0.05 單位一條線，方便對位
      c.font = '16px sans-serif'; c.lineWidth = 2;
      for (let gx = Math.ceil(this.rect.x / 0.05) * 0.05; gx < this.rect.x + this.rect.w; gx += 0.05) { const [x] = this.px([gx, 0]); c.strokeStyle = Math.abs(gx) < 0.01 ? '#f00' : 'rgba(0,90,255,0.7)'; c.beginPath(); c.moveTo(x, 0); c.lineTo(x, S); c.stroke(); c.fillStyle = '#00f'; c.fillText(gx.toFixed(2), x + 2, S * 0.5); }
      for (let gy = Math.ceil(this.rect.y / 0.05) * 0.05; gy < this.rect.y + this.rect.h; gy += 0.05) { const [, y] = this.px([0, gy]); c.strokeStyle = 'rgba(0,160,60,0.7)'; c.beginPath(); c.moveTo(0, y); c.lineTo(S, y); c.stroke(); c.fillStyle = '#060'; c.fillText(gy.toFixed(2), S * 0.5, y - 2); }
      return true; }
    const eyes = [[f.eyeL, 1], [f.eyeR, -1]];
    // 腮紅
    for (const [e, s] of eyes) {
      const [x, y] = this.px([e[0] + s * f.r * 0.75, e[1] - f.r * 1.45]);
      const g = c.createRadialGradient(x, y, 0, x, y, R * 1.05); g.addColorStop(0, 'rgba(255,120,120,0.50)'); g.addColorStop(1, 'rgba(255,120,120,0)');
      c.fillStyle = g; c.beginPath(); c.ellipse(x, y, R * 1.05, R * 0.7, 0, 0, 7); c.fill();
    }
    const closed = expr === 'happy' ? 1 : blink;
    for (const [e, s] of eyes) {
      const [x, y] = this.px(e);
      c.save(); c.translate(x, y);
      if (expr === 'dizzy') { // 叉叉眼
        c.strokeStyle = '#3a2a2a'; c.lineWidth = R * 0.22; c.lineCap = 'round';
        c.beginPath(); c.moveTo(-R * 0.6, -R * 0.6); c.lineTo(R * 0.6, R * 0.6); c.moveTo(R * 0.6, -R * 0.6); c.lineTo(-R * 0.6, R * 0.6); c.stroke();
        c.restore(); continue;
      }
      if (closed > 0.85) { // 閉眼弧線（開心是往上彎）
        c.strokeStyle = '#3a2424'; c.lineWidth = R * 0.2; c.lineCap = 'round'; c.beginPath();
        if (expr === 'happy') c.arc(0, R * 0.35, R * 0.8, Math.PI * 1.15, Math.PI * 1.85); else c.arc(0, -R * 0.35, R * 0.8, Math.PI * 0.15, Math.PI * 0.85);
        c.stroke(); c.restore(); continue;
      }
      const open = (1 - closed) * (expr === 'surprised' ? 1.08 : expr === 'angry' || expr === 'focus' ? 0.86 : expr === 'sad' ? 0.9 : 1);
      const rx = R * 0.9, ry = R * 1.08 * open;
      // 眼白
      c.beginPath(); c.ellipse(0, 0, rx, ry, 0, 0, 7); c.fillStyle = '#ffffff'; c.fill(); c.save(); c.clip();
      // 虹膜（大而水亮）
      const k = expr === 'surprised' ? 0.62 : 0.84, ix = look[0] * R * 0.18, iy = -look[1] * R * 0.18 + R * 0.06;
      const g = c.createRadialGradient(ix, iy + R * 0.3, R * 0.1, ix, iy, R * k);
      g.addColorStop(0, '#9a5a34'); g.addColorStop(0.55, '#5a2f1c'); g.addColorStop(1, '#2a1510');
      c.fillStyle = g; c.beginPath(); c.ellipse(ix, iy, R * k * 0.95, R * k * 1.08, 0, 0, 7); c.fill();
      c.fillStyle = '#140a08'; c.beginPath(); c.ellipse(ix, iy, R * k * 0.42, R * k * 0.5, 0, 0, 7); c.fill();
      c.fillStyle = 'rgba(255,255,255,0.96)'; c.beginPath(); c.ellipse(ix - s * 0 - R * 0.28, iy - R * 0.36, R * 0.24, R * 0.28, 0, 0, 7); c.fill();
      c.fillStyle = 'rgba(255,255,255,0.8)'; c.beginPath(); c.arc(ix + R * 0.3, iy + R * 0.36, R * 0.11, 0, 7); c.fill();
      // 上眼皮陰影
      c.fillStyle = 'rgba(40,20,20,0.22)'; c.beginPath(); c.ellipse(0, -ry * 1.05, rx * 1.3, ry * 0.55, 0, 0, 7); c.fill();
      c.restore();
      // 上睫毛線
      c.strokeStyle = '#2e1c1c'; c.lineWidth = R * 0.17; c.lineCap = 'round';
      c.beginPath(); c.ellipse(0, 0, rx, ry, 0, Math.PI * 1.06, Math.PI * 1.94); c.stroke();
      c.lineWidth = R * 0.12; c.beginPath(); c.moveTo(s * rx * 0.93, -ry * 0.25); c.lineTo(s * rx * 1.2, -ry * 0.55); c.stroke();
      c.strokeStyle = 'rgba(90,50,40,0.45)'; c.lineWidth = R * 0.06; c.beginPath(); c.ellipse(0, 0, rx, ry, 0, Math.PI * 0.1, Math.PI * 0.9); c.stroke();
      if (expr === 'angry' || expr === 'focus') { // 斜的上眼皮
        c.fillStyle = '#ffd6bd'; c.beginPath(); c.moveTo(-s * rx * 1.3, -ry * 1.4); c.lineTo(s * rx * 1.3, -ry * 1.4); c.lineTo(s * rx * 1.3, -ry * (expr === 'angry' ? 0.75 : 0.9)); c.lineTo(-s * rx * 1.3, -ry * (expr === 'angry' ? 0.1 : 0.55)); c.fill();
        c.strokeStyle = '#2e1c1c'; c.lineWidth = R * 0.15; c.beginPath(); c.moveTo(s * rx * 1.05, -ry * (expr === 'angry' ? 0.75 : 0.9)); c.lineTo(-s * rx * 1.0, -ry * (expr === 'angry' ? 0.1 : 0.55)); c.stroke();
      }
      c.restore();
    }
    // 眉毛
    for (const [e, s] of eyes) {
      const [x, y] = this.px([e[0], e[1] + f.brow]);
      const tilt = { angry: 0.42, sad: -0.36, surprised: 0, focus: 0.2 }[expr] || 0, lift = { surprised: -R * 0.3, angry: R * 0.42, focus: R * 0.25, sad: -R * 0.05 }[expr] || 0;
      c.save(); c.translate(x, y + lift); c.rotate(-s * tilt);
      c.strokeStyle = '#2b2636'; c.lineWidth = R * 0.2; c.lineCap = 'round';
      c.beginPath(); c.moveTo(-s * R * 0.75, R * 0.05); c.quadraticCurveTo(0, -R * 0.26, s * R * 0.8, R * 0.12); c.stroke(); c.restore();
    }
    // 嘴巴
    { const [x, y] = this.px(f.mouth); const w = R * 0.62; c.save(); c.translate(x, y); c.lineCap = 'round'; c.lineJoin = 'round';
      const m = Math.max(mouth, expr === 'surprised' ? 0.75 : expr === 'happy' ? 0.7 : 0);
      if (m > 0.08) {
        const hh = R * (0.12 + 0.5 * m), ww = expr === 'surprised' ? w * 0.5 : w * (0.75 + 0.2 * m);
        c.beginPath();
        if (expr === 'angry' || expr === 'sad') c.ellipse(0, 0, ww * 0.8, hh * 0.8, 0, 0, 7);
        else if (expr === 'surprised') c.ellipse(0, 0, ww, hh, 0, 0, 7);
        else { c.moveTo(-ww, -hh * 0.3); c.quadraticCurveTo(0, -hh * 0.05, ww, -hh * 0.3); c.quadraticCurveTo(ww * 0.7, hh * 1.3, 0, hh * 1.3); c.quadraticCurveTo(-ww * 0.7, hh * 1.3, -ww, -hh * 0.3); }
        c.fillStyle = '#7a2b2b'; c.fill(); c.save(); c.clip(); c.fillStyle = '#ff8f8f'; c.beginPath(); c.ellipse(0, hh * 1.25, ww * 0.6, hh * 0.6, 0, 0, 7); c.fill(); c.restore();
        c.strokeStyle = '#5a1f1f'; c.lineWidth = R * 0.07; c.stroke();
      } else {
        c.strokeStyle = '#8a3a34'; c.lineWidth = R * 0.12; c.beginPath();
        if (expr === 'angry') { c.moveTo(-w * 0.8, R * 0.12); c.quadraticCurveTo(0, -R * 0.22, w * 0.8, R * 0.12); }
        else if (expr === 'sad') { c.moveTo(-w * 0.7, R * 0.1); c.quadraticCurveTo(0, -R * 0.12, w * 0.7, R * 0.1); }
        else if (expr === 'dizzy') { c.moveTo(-w, 0); c.quadraticCurveTo(-w * 0.5, -R * 0.2, 0, 0); c.quadraticCurveTo(w * 0.5, R * 0.2, w, 0); }
        else if (expr === 'focus') { c.moveTo(-w * 0.5, 0); c.lineTo(w * 0.5, 0); }
        else { c.moveTo(-w, -R * 0.1); c.quadraticCurveTo(0, R * 0.42, w, -R * 0.1); }
        c.stroke();
      }
      c.restore(); }
    return true;
  }
}
