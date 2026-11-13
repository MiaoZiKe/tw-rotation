// 天色：依「台北時間」連續變化（清晨淡粉橘 → 白天淡藍 → 黃昏暖橘金 → 夜晚深藍有星月），不是硬切。
// 一起變的有：天空漸層、霧色、太陽／月亮的位置與方向光（陰影跟著走）、光色與強度、環境光（半球光）、雲色、
// 窗玻璃與地上的窗光、夜間室內的暖光（桌面與立燈的光暈，用一個加法混色的點雲，不加任何會投影的燈）。
// 效能：只新增 4 次繪製（星星點雲、太陽、月亮、室內暖光點雲）；顏色約每 2 秒更新一次，不是每幀；
//       方向光轉動超過 0.4 度才重烘一次陰影（陰影是靜態烘的）。
// 介面：左上角一個小字「時段・台北 HH:MM」，點開可切「跟隨現在時間／早晨／白天／黃昏／夜晚」，選擇記在 localStorage。
import * as THREE from 'three';

const KEY = 'aiOffice.daytime';
const $ = id => document.getElementById(id);
const C = h => new THREE.Color(h);

// 關鍵時刻（小時，台北時間）→ 各項參數；兩個關鍵時刻之間線性漸變。顏色維持柔和的淺色美術風格，夜晚也不過暗。
const K = [
  // t     天頂       天中       地平       霧        半球天      半球地      半球強度 光色       光強  雲色       窗色       窗不透明 窗光斑色   斑強  暖光  星
  [0,    '#0d1538', '#1c2c62', '#34447e', '#2a3870', '#bcc9f2', '#7e7ab4', 1.12, '#aebfff', 0.58, '#56608e', '#ffd48a', 0.78, '#ffcf80', 0.34, 1.0, 1.0],
  [5,    '#1c2552', '#3d4c88', '#7c6c9c', '#6c6c9c', '#c6cef2', '#8c88b8', 1.18, '#b4c0f4', 0.58, '#6a6a98', '#ffd48a', 0.74, '#ffcf80', 0.30, 0.9, 0.9],
  [6.3,  '#9db8e8', '#f6c8b8', '#ffe2c0', '#f9d9c4', '#ffeadf', '#ebc8b4', 1.36, '#ffc9a0', 1.05, '#ffdcd0', '#ffe0c8', 0.48, '#ffd0b0', 0.16, 0.25, 0.0],
  [7.8,  '#a9ddf8', '#d7f0fc', '#f1fbff', '#e3f4fc', '#fffaf3', '#f3d5b4', 1.50, '#fff3e0', 1.55, '#ffffff', '#cfefff', 0.38, '#ffffff', 0.10, 0.0, 0.0],
  [12,   '#8fd0f6', '#cdeefc', '#f1fbff', '#e3f4fc', '#fffaf3', '#f3d5b4', 1.55, '#fff6e6', 1.65, '#ffffff', '#cfefff', 0.38, '#ffffff', 0.10, 0.0, 0.0],
  [16.5, '#a9ddf8', '#d7f0fc', '#f1fbff', '#e3f4fc', '#fffaf3', '#f3d5b4', 1.50, '#fff3e0', 1.55, '#ffffff', '#cfefff', 0.38, '#ffffff', 0.10, 0.0, 0.0],
  [17.8, '#a6b9e8', '#ffd2a0', '#ffe9c2', '#ffdcb0', '#ffe3c4', '#f0c49a', 1.32, '#ffb878', 1.30, '#ffd9b0', '#ffc58a', 0.55, '#ffb070', 0.22, 0.35, 0.0],
  [18.8, '#4e5496', '#da8a76', '#ffb87a', '#cf9078', '#eec6c8', '#a88cac', 1.05, '#ff9a70', 0.70, '#e0a090', '#ffc880', 0.66, '#ffb060', 0.28, 0.8, 0.45],
  [20.2, '#0d1538', '#1c2c62', '#34447e', '#2a3870', '#bcc9f2', '#7e7ab4', 1.12, '#aebfff', 0.58, '#56608e', '#ffd48a', 0.78, '#ffcf80', 0.34, 1.0, 1.0],
  [24,   '#0d1538', '#1c2c62', '#34447e', '#2a3870', '#bcc9f2', '#7e7ab4', 1.12, '#aebfff', 0.58, '#56608e', '#ffd48a', 0.78, '#ffcf80', 0.34, 1.0, 1.0],
];
const KC = [1, 2, 3, 4, 5, 6, 8, 10, 11, 13];   // 哪些欄位是顏色
const MODES = { auto: null, morning: 6.3, day: 12, dusk: 18, night: 22 };   // 預覽用：強制時刻（清晨／白天／黃昏／夜晚）
const LABEL = { auto: '跟隨現在時間', morning: '早晨', day: '白天', dusk: '黃昏', night: '夜晚' };

// 台北時間（不管瀏覽器在哪個時區）
const fmt = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Taipei', hourCycle: 'h23', hour: '2-digit', minute: '2-digit', second: '2-digit' });
export function taipeiNow() { const p = {}; for (const x of fmt.formatToParts(new Date())) p[x.type] = x.value; const h = +p.hour, m = +p.minute, s = +p.second; return { h, m, s, t: h + m / 60 + s / 3600, text: `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}` }; }
export const phaseOf = t => (t >= 5 && t < 7 ? '清晨' : t >= 7 && t < 17 ? '白天' : t >= 17 && t < 19 ? '黃昏' : '夜晚');

function frame(t) {                                                // 在關鍵時刻之間內插
  let i = 0; while (i < K.length - 2 && t >= K[i + 1][0]) i++;
  const a = K[i], b = K[i + 1], u = Math.max(0, Math.min(1, (t - a[0]) / (b[0] - a[0]))), e = u * u * (3 - 2 * u), out = [];
  for (let j = 1; j < a.length; j++) out[j] = KC.includes(j) ? C(a[j]).lerp(C(b[j]), e) : a[j] + (b[j] - a[j]) * e;
  return out;
}

export function createDaytime(W, X) {
  const { scene, sun, hemi, camera } = W, D = { mode: 'auto', t: 12, cur: null };
  try { const m = localStorage.getItem(KEY); if (m && m in MODES) D.mode = m; } catch (e) { /* 沒有儲存空間就用預設（跟隨現在時間） */ }

  // ── 天空物件：跟著鏡頭走（等於無限遠）：星星點雲、太陽、月亮 ──
  const sky = new THREE.Group(); sky.renderOrder = -1; scene.add(sky);
  const stars = (() => {
    const n = 420, pos = new Float32Array(n * 3); let s = 11; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < n; i++) { const a = r() * Math.PI * 2, el = 0.12 + r() * 1.35, R = 200; pos[i * 3] = Math.cos(a) * Math.cos(el) * R; pos[i * 3 + 1] = Math.sin(el) * R; pos[i * 3 + 2] = Math.sin(a) * Math.cos(el) * R; }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const tex = glowTex(32, c => { c.fillStyle = '#fff'; c.beginPath(); c.arc(16, 16, 5, 0, 7); c.fill(); });
    const m = new THREE.Points(g, new THREE.PointsMaterial({ map: tex, size: 3.2, sizeAttenuation: false, color: '#fffbe8', transparent: true, opacity: 0, depthWrite: false, fog: false })); m.frustumCulled = false; m.renderOrder = 0; return m;
  })();
  const sunS = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(128, c => { const g = c.createRadialGradient(64, 64, 4, 64, 64, 62); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.22, 'rgba(255,244,210,1)'); g.addColorStop(0.3, 'rgba(255,230,170,.55)'); g.addColorStop(1, 'rgba(255,220,160,0)'); c.fillStyle = g; c.fillRect(0, 0, 128, 128); }), color: '#ffffff', transparent: true, depthWrite: false, depthTest: false, fog: false }));
  sunS.scale.set(46, 46, 1); sunS.renderOrder = 1;
  const moonS = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(128, c => {
    const g = c.createRadialGradient(64, 64, 10, 64, 64, 62); g.addColorStop(0, 'rgba(210,225,255,.55)'); g.addColorStop(1, 'rgba(210,225,255,0)'); c.fillStyle = g; c.fillRect(0, 0, 128, 128);
    c.fillStyle = '#fff8dc'; c.beginPath(); c.arc(64, 64, 24, 0, 7); c.fill();                       // 月亮本體（有一點月牙的陰影）
    c.globalCompositeOperation = 'destination-out'; c.beginPath(); c.arc(76, 58, 20, 0, 7); c.fill(); c.globalCompositeOperation = 'source-over';
    c.fillStyle = 'rgba(255,248,220,.35)'; c.beginPath(); c.arc(64, 64, 24, 0, 7); c.fill();
  }), color: '#ffffff', transparent: true, depthWrite: false, depthTest: false, fog: false }));
  moonS.scale.set(30, 30, 1); moonS.renderOrder = 1;
  sky.add(stars, sunS, moonS);
  function glowTex(n, draw) { const cv = document.createElement('canvas'); cv.width = cv.height = n; draw(cv.getContext('2d')); const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t; }

  // ── 夜間室內的暖光：每張辦公桌與立燈一個光暈（一個加法混色的點雲，不投影、不增加光源）──
  let glow = null;
  W.glowRebuild = () => {
    if (glow) { scene.remove(glow); glow.geometry.dispose(); glow = null; }
    const pts = []; for (const inst of W.furn.values()) { const f = inst.f; if (f.type === 'lamp') pts.push(f.x, 1.35, f.z); else if (f.type === 'workstation' || f.type === 'ceo_desk') pts.push(f.x, 1.0, f.z); }
    if (!pts.length) return;
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    const tex = glowTex(64, c => { const r = c.createRadialGradient(32, 32, 1, 32, 32, 31); r.addColorStop(0, 'rgba(255,236,180,.95)'); r.addColorStop(0.35, 'rgba(255,214,140,.38)'); r.addColorStop(1, 'rgba(255,200,120,0)'); c.fillStyle = r; c.fillRect(0, 0, 64, 64); });
    glow = new THREE.Points(g, new THREE.PointsMaterial({ map: tex, size: 1.9, sizeAttenuation: true, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, fog: false })); glow.frustumCulled = false; glow.renderOrder = 5; scene.add(glow);
  };
  W.glowRebuild();

  // ── 套用某一時刻的天色 ──
  const cv = W.skyTex && W.skyTex.image, g2 = cv && cv.getContext('2d'), center = new THREE.Vector3(20, 0, 15), dir = new THREE.Vector3(), sd = new THREE.Vector3(), md = new THREE.Vector3(), lastDir = new THREE.Vector3(0, 1, 0);
  function bodyDir(h, riseH, out) {                                // 太陽（或月亮）在天空的方向：東邊升起、南邊偏高、西邊落下
    const a = ((h - riseH + 24) % 24) / 12 * Math.PI; return out.set(Math.cos(a) * 0.9, Math.sin(a), 0.38).normalize();
  }
  function apply(t) {
    const f = frame(t); D.cur = f;
    if (g2) { const gr = g2.createLinearGradient(0, 0, 0, cv.height); gr.addColorStop(0, '#' + f[1].getHexString()); gr.addColorStop(0.55, '#' + f[2].getHexString()); gr.addColorStop(1, '#' + f[3].getHexString()); g2.fillStyle = gr; g2.fillRect(0, 0, cv.width, cv.height); W.skyTex.needsUpdate = true; }
    scene.fog.color.copy(f[4]); hemi.color.copy(f[5]); hemi.groundColor.copy(f[6]); hemi.intensity = f[7];
    sun.color.copy(f[8]); sun.intensity = f[9];
    if (W.clouds) W.clouds.material.color.copy(f[10]);
    if (W.glassMat) { W.glassMat.color.copy(f[11]); W.glassMat.opacity = f[12]; }
    if (W.patchMat) { W.patchMat.color.copy(f[13]); W.patchMat.opacity = f[14]; }
    if (glow) glow.material.opacity = f[15] * 0.75; stars.material.opacity = f[16];
    // 太陽 6～18 點在天上；月亮 18～6 點。方向光：白天用太陽，夜晚用月亮，兩者交接的 1 小時內方向平順轉過去
    bodyDir(t, 6, sd); bodyDir(t, 18, md);
    const isDay = t >= 5.5 && t < 18.5, w = isDay ? Math.min(1, Math.min(t - 5.5, 18.5 - t) / 1.0) : 0;
    dir.copy(md).lerp(sd, w).normalize(); if (dir.y < 0.22) { dir.y = 0.22; dir.normalize(); }            // 光不低於地平線太多（陰影才不會拉到無限長）
    sun.position.copy(center).addScaledVector(dir, 44.6);
    if (dir.angleTo(lastDir) > 0.007) { lastDir.copy(dir); W.shadowDirty(); }
    sunS.material.color.copy(f[8]).lerp(new THREE.Color('#ffffff'), 0.3); sunS.visible = sd.y > -0.05 && t >= 5 && t < 19.2; sunS.position.copy(sd).multiplyScalar(170); sunS.material.opacity = Math.max(0, Math.min(1, (sd.y + 0.05) * 6));
    moonS.visible = md.y > -0.05 && (t >= 17.8 || t < 6.2); moonS.position.copy(md).multiplyScalar(170); moonS.material.opacity = Math.max(0, Math.min(1, (md.y + 0.05) * 6));
    D.dir = dir.clone(); D.shown = t;
  }

  // ── 介面：左上小字＋時間選單 ──
  const chip = document.createElement('div'); chip.className = 'dt-chip'; $('app').append(chip);
  const pop = document.createElement('div'); pop.className = 'dt-pop'; pop.hidden = true; $('app').append(pop);
  function now() { const n = taipeiNow(); return D.mode === 'auto' ? n : { ...n, t: MODES[D.mode], text: n.text }; }
  function renderChip() {
    const n = taipeiNow(), t = D.mode === 'auto' ? n.t : MODES[D.mode];
    chip.innerHTML = `<button class="dt-b" aria-haspopup="true" aria-expanded="${!pop.hidden}" aria-label="時間：${phaseOf(t)}，台北 ${n.text}，點一下切換預覽">${D.mode === 'auto' ? '' : '預覽・'}${phaseOf(t)}・台北 ${n.text}</button>`;
    pop.innerHTML = `<div class="dt-h">時間（預覽用）</div>` + Object.keys(MODES).map(k => `<button class="dt-it${k === D.mode ? ' on' : ''}" data-m="${k}">${LABEL[k]}</button>`).join('');
  }
  chip.addEventListener('click', e => { if (e.target.closest('.dt-b')) { pop.hidden = !pop.hidden; renderChip(); place(); } });
  pop.addEventListener('click', e => { const b = e.target.closest('[data-m]'); if (!b) return; D.set(b.dataset.m); pop.hidden = true; renderChip(); });
  document.addEventListener('pointerdown', e => { if (!pop.hidden && !e.target.closest('.dt-chip') && !e.target.closest('.dt-pop')) { pop.hidden = true; renderChip(); } });
  function place() {
    const bar = $('bar').getBoundingClientRect(), hint = document.querySelector('.cm-hint'), hr = hint && hint.offsetParent ? hint.getBoundingClientRect() : null;
    const narrow = innerWidth < 1180 || matchMedia('(pointer:coarse)').matches;
    // 寬螢幕：左上、工具列下方；窄螢幕與手機：鏡頭小提示下方（兩者都在工具列下方，不重疊）
    const top = narrow && hr ? hr.bottom + 6 : bar.bottom + 8;
    chip.style.top = Math.round(top) + 'px'; chip.style.left = '12px';
    pop.style.top = Math.round(top + 36) + 'px'; pop.style.left = '12px';
  }
  addEventListener('resize', place);

  D.set = m => { if (!(m in MODES)) return; D.mode = m; try { localStorage.setItem(KEY, m); } catch (e) { /* 只在這次有效 */ } D.update(true); renderChip(); };
  let lastAt = -1e9, lastTxt = '';
  D.update = force => {
    const tt = performance.now();
    if (!force && tt - lastAt < 2000) { return; } lastAt = tt;
    const n = taipeiNow(), t = D.mode === 'auto' ? n.t : MODES[D.mode]; D.t = t; apply(t);
    if (n.text !== lastTxt || force) { lastTxt = n.text; renderChip(); }
    place();
  };
  D.tick = () => { sky.position.copy(camera.position); D.update(false); };
  D.now = () => ({ ...taipeiNow(), t: D.t }); D.mode0 = () => D.mode; D.phaseOf = phaseOf; D.MODES = MODES; D.chip = chip; D.pop = pop; D.stars = stars; D.sunS = sunS; D.moonS = moonS;
  D.update(true); place();
  return D;
}
