// 頭上的情緒符號與特效看板（Canvas 貼圖）
import { THREE } from './core.js';
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
