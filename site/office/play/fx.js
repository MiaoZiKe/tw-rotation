// 粒子與音效：愛心、星星、灰塵、Zzz、音符、蒸氣、碎屑；全部用 Canvas 畫成柔邊貼圖
import * as THREE from 'three';

function tex(draw, s = 128) {
  const c = document.createElement('canvas'); c.width = c.height = s;
  const g = c.getContext('2d'); g.translate(s / 2, s / 2); draw(g, s / 2);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const T = {};
function initTex() {
  T.heart = tex((g, r) => {
    const k = r * 0.78;
    g.beginPath(); g.moveTo(0, k * 0.78);
    g.bezierCurveTo(-k * 1.25, -k * 0.05, -k * 0.62, -k * 0.98, 0, -k * 0.38);
    g.bezierCurveTo(k * 0.62, -k * 0.98, k * 1.25, -k * 0.05, 0, k * 0.78);
    const gr = g.createRadialGradient(-k * 0.3, -k * 0.4, k * 0.05, 0, 0, k * 1.1);
    gr.addColorStop(0, '#ffc2cf'); gr.addColorStop(0.5, '#ff7f9c'); gr.addColorStop(1, '#f2557c');
    g.shadowColor = 'rgba(255,120,150,.55)'; g.shadowBlur = r * 0.18; g.fillStyle = gr; g.fill();
    g.shadowBlur = 0; g.fillStyle = 'rgba(255,255,255,.75)';
    g.beginPath(); g.ellipse(-k * 0.38, -k * 0.38, k * 0.16, k * 0.1, -0.7, 0, 7); g.fill();
  });
  T.star = tex((g, r) => {
    const R = r * 0.74, q = R * 0.5;
    g.beginPath();
    for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? q : R; g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); }
    g.closePath(); g.lineJoin = 'round'; g.lineWidth = r * 0.2; g.strokeStyle = '#ffd04a';
    g.shadowColor = 'rgba(255,200,60,.6)'; g.shadowBlur = r * 0.2; g.stroke(); g.fillStyle = '#ffe27a'; g.fill();
    g.shadowBlur = 0; g.fillStyle = 'rgba(255,255,255,.7)'; g.beginPath(); g.arc(-R * 0.2, -R * 0.2, R * 0.14, 0, 7); g.fill();
  });
  T.dust = tex((g, r) => {
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, r * 0.95);
    gr.addColorStop(0, 'rgba(255,250,242,.95)'); gr.addColorStop(0.55, 'rgba(255,246,236,.55)'); gr.addColorStop(1, 'rgba(255,244,232,0)');
    g.fillStyle = gr; g.beginPath(); g.arc(0, 0, r, 0, 7); g.fill();
  });
  T.zzz = tex((g, r) => {
    g.font = `900 ${r * 1.5}px "Arial Rounded MT Bold","Nunito","Noto Sans TC",sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.lineJoin = 'round'; g.lineWidth = r * 0.26; g.strokeStyle = '#ffffff'; g.strokeText('Z', 0, r * 0.05);
    g.fillStyle = '#8fa8ff'; g.fillText('Z', 0, r * 0.05);
  });
  T.note = tex((g, r) => {
    g.fillStyle = '#ff9fbd'; g.strokeStyle = '#ff9fbd'; g.lineWidth = r * 0.13; g.lineCap = 'round';
    g.shadowColor = 'rgba(255,255,255,.9)'; g.shadowBlur = r * 0.15;
    g.beginPath(); g.ellipse(-r * 0.2, r * 0.42, r * 0.27, r * 0.2, -0.4, 0, 7); g.fill();
    g.beginPath(); g.moveTo(r * 0.03, r * 0.38); g.lineTo(r * 0.03, -r * 0.55); g.quadraticCurveTo(r * 0.3, -r * 0.5, r * 0.42, -r * 0.2); g.stroke();
  });
  T.drop = tex((g, r) => {
    const k = r * 0.62;
    g.beginPath(); g.moveTo(0, -k * 1.15); g.bezierCurveTo(k * 0.95, -k * 0.1, k * 0.8, k * 0.95, 0, k * 0.95);
    g.bezierCurveTo(-k * 0.8, k * 0.95, -k * 0.95, -k * 0.1, 0, -k * 1.15);
    const gr = g.createLinearGradient(0, -k, 0, k); gr.addColorStop(0, '#d9f2ff'); gr.addColorStop(1, '#8fd0ff');
    g.fillStyle = gr; g.fill();
  });
  T.spark = tex((g, r) => {
    const R = r * 0.85;
    g.beginPath();
    for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4, rr = i % 2 ? R * 0.22 : R; g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); }
    g.closePath(); g.shadowColor = '#fff'; g.shadowBlur = r * 0.25; g.fillStyle = '#fffbe0'; g.fill();
  });
  T.crumb = tex((g, r) => {
    const gr = g.createRadialGradient(-r * .2, -r * .2, 0, 0, 0, r * 0.7);
    gr.addColorStop(0, '#f6d9a8'); gr.addColorStop(1, '#d9a866'); g.fillStyle = gr; g.beginPath(); g.arc(0, 0, r * 0.6, 0, 7); g.fill();
  });
  T.ring = tex((g, r) => {
    g.strokeStyle = 'rgba(255,255,255,.95)'; g.lineWidth = r * 0.12; g.shadowColor = '#ffd9a0'; g.shadowBlur = r * 0.2;
    g.beginPath(); g.arc(0, 0, r * 0.72, 0, 7); g.stroke();
  }, 256);
  T.shadow = tex((g, r) => {
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, r);
    gr.addColorStop(0, 'rgba(70,40,30,.62)'); gr.addColorStop(0.45, 'rgba(70,40,30,.36)'); gr.addColorStop(1, 'rgba(70,40,30,0)');
    g.fillStyle = gr; g.beginPath(); g.arc(0, 0, r, 0, 7); g.fill();
  });
}

export class FX {
  constructor(scene) {
    initTex(); this.T = T; this.scene = scene; this.pool = []; this.live = [];
    this.muted = false; this.ac = null;
  }
  spawn(type, p, o = {}) {
    let s = this.pool.pop();
    if (!s) { s = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false })); this.scene.add(s); }
    s.material.map = T[type]; s.material.opacity = 1; s.material.rotation = o.rot || 0; s.material.depthTest = o.depthTest !== false;
    s.visible = true; s.position.copy(p); s.renderOrder = 20;
    const d = s.userData;
    d.v = o.v ? o.v.clone() : new THREE.Vector3(); d.life = d.max = o.life || 1; d.size = o.size || 0.2; d.grow = o.grow || 0;
    d.g = o.g || 0; d.drag = o.drag || 0; d.spin = o.spin || 0; d.sway = o.sway || 0; d.ph = Math.random() * 6.28; d.fadeIn = o.fadeIn || 0.08;
    d.follow = o.follow || null; d.off = o.follow ? p.clone() : null; d.orbit = o.orbit || 0;
    s.scale.setScalar(d.size); this.live.push(s); return s;
  }
  burst(type, p, n, o = {}) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, sp = (o.speed || 1) * (0.5 + Math.random() * 0.7);
      const v = new THREE.Vector3(Math.cos(a) * sp, (o.up || 0) + Math.random() * (o.upR || 0), Math.sin(a) * sp);
      const q = p.clone(); if (o.spread) { q.x += (Math.random() - .5) * o.spread; q.z += (Math.random() - .5) * o.spread; q.y += (Math.random() - .5) * o.spread * (o.spreadY ?? 1); }
      this.spawn(type, q, { ...o, v, size: (o.size || 0.2) * (0.75 + Math.random() * 0.5), life: (o.life || 1) * (0.8 + Math.random() * 0.4), rot: o.rotR ? (Math.random() - .5) * o.rotR : 0 });
    }
  }
  update(dt, t) {
    for (let i = this.live.length - 1; i >= 0; i--) {
      const s = this.live[i], d = s.userData;
      d.life -= dt;
      if (d.life <= 0) { s.visible = false; this.live.splice(i, 1); this.pool.push(s); continue; }
      const age = d.max - d.life;
      if (d.follow) {
        if (d.orbit) { const a = d.ph + t * d.orbit; s.position.set(d.follow.x + Math.cos(a) * d.off.x, d.follow.y + d.off.y + Math.sin(a * 2) * 0.02, d.follow.z + Math.sin(a) * d.off.x); }
      } else {
        d.v.y -= d.g * dt; if (d.drag) d.v.multiplyScalar(Math.exp(-d.drag * dt));
        s.position.addScaledVector(d.v, dt);
        if (d.sway) s.position.x += Math.sin(t * 3 + d.ph) * d.sway * dt;
      }
      const k = d.life / d.max;
      s.material.opacity = Math.min(1, age / d.fadeIn) * Math.min(1, k * 3);
      s.scale.setScalar(d.size * (1 + d.grow * age) * (0.6 + 0.4 * Math.min(1, age / 0.12)));
      if (d.spin) s.material.rotation += d.spin * dt;
    }
  }
  // ── 音效（全部即時合成，不載檔）
  _ac() {
    if (this.muted) return null;
    if (!this.ac) { try { this.ac = new (window.AudioContext || window.webkitAudioContext)(); this.master = this.ac.createGain(); this.master.gain.value = 0.35; this.master.connect(this.ac.destination); } catch (e) { return null; } }
    if (this.ac.state === 'suspended') this.ac.resume().catch(() => { });
    return this.ac;
  }
  tone(f0, f1, dur, type = 'sine', vol = 0.5, delay = 0) {
    const ac = this._ac(); if (!ac) return;
    const t = ac.currentTime + delay, o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.012); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(this.master); o.start(t); o.stop(t + dur + 0.02);
  }
  noise(dur, freq = 800, vol = 0.3, delay = 0) {
    const ac = this._ac(); if (!ac) return;
    const n = Math.floor(ac.sampleRate * dur), b = ac.createBuffer(1, n, ac.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const s = ac.createBufferSource(); s.buffer = b; const f = ac.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = freq;
    const g = ac.createGain(); g.gain.value = vol; s.connect(f); f.connect(g); g.connect(this.master); s.start(ac.currentTime + delay);
  }
  sfx(n, a = 1) {
    switch (n) {
      case 'jump': this.tone(280, 620, 0.16, 'sine', 0.4); break;
      case 'land': this.noise(0.09, 500, 0.35 * Math.min(1, a)); this.tone(150, 70, 0.1, 'sine', 0.3 * Math.min(1, a)); break;
      case 'boing': this.tone(180, 520, 0.28, 'triangle', 0.45); this.tone(360, 900, 0.22, 'sine', 0.2, 0.03); break;
      case 'poke': this.tone(700 + Math.random() * 200, 420, 0.09, 'sine', 0.4); break;
      case 'squeak': this.tone(900, 1500, 0.1, 'sine', 0.3); this.tone(1500, 1000, 0.1, 'sine', 0.25, 0.09); break;
      case 'heart': this.tone(660, 660, 0.1, 'sine', 0.3); this.tone(880, 880, 0.14, 'sine', 0.3, 0.09); break;
      case 'kick': this.noise(0.05, 1200, 0.3); this.tone(240, 120, 0.08, 'sine', 0.35); break;
      case 'bonk': this.tone(320, 110, 0.18, 'triangle', 0.5); break;
      case 'eat': this.noise(0.06, 2400, 0.3); this.noise(0.06, 2000, 0.25, 0.22); this.noise(0.06, 2200, 0.25, 0.44); break;
      case 'skid': this.noise(0.22, 3000, 0.12); break;
      case 'angry': this.tone(200, 150, 0.25, 'sawtooth', 0.18); break;
      case 'laugh': for (let i = 0; i < 4; i++) this.tone(620 + i * 30, 520, 0.08, 'sine', 0.28, i * 0.11); break;
      case 'yawn': this.tone(420, 200, 0.7, 'sine', 0.18); break;
      case 'whee': this.tone(500, 1100, 0.35, 'sine', 0.3); break;
      case 'dizzy': this.tone(700, 500, 0.5, 'triangle', 0.15); this.tone(900, 640, 0.5, 'triangle', 0.12, 0.15); break;
      case 'note': this.tone([523, 659, 784, 659][Math.floor(a) % 4], [523, 659, 784, 659][Math.floor(a) % 4], 0.16, 'triangle', 0.25); break;
      case 'step': this.noise(0.03, 700, 0.06 * a); break;
      case 'ui': this.tone(880, 1100, 0.06, 'sine', 0.2); break;
    }
  }
}
