// ════════════════════════════════════════════════════════════════════════
// 辦公室場景用的角色工廠：createCharacter(spec, env) —— 介面照 site/office/world/js/character.js 開頭那份約定，
// 另外多了：手上的道具、頭上的情緒圖示、起身／坐下的過渡、拎起來丟、摸頭／敲頭／餵食、遠近分級、縮放（寵物、CEO）。
//
// spec 除了場景原本的 { id, nick, zh, race, dept, color, isCeo, lead }，還可以指定外觀（都可省略）：
//   species   物種代號（見 species.js）    pal 配色編號或名稱    hue 色相微調（-0.08 ~ 0.08）
//   acc       配件陣列：glasses hat bow tie scarf badge crown    accColor 配件顏色（編號 0~5 或 '#rrggbb'）
//   scale     整體大小（預設 1；寵物 0.5 左右、CEO 1.15）
// 沒指定時依 id 的雜湊決定，所以同一個 id 每次長得一樣。
// 動作 setAction(name)：
//   持續型：idle type read tablet doc note listen think phone drink eat magnify carry present doze sulk sleep paddle
//   一次型：talk nod shake raise cheer clap angry wave stretch slam point pour reach
// 完整說明見 docs/ai_office/character_factory.md
// ════════════════════════════════════════════════════════════════════════
import * as THREE from 'three';
import { Character } from './character.js';
import { SPECIES, SPECIES_IDS, canWear } from './species.js';
import { stubFx } from './lite.js';
import { DETAIL, clamp, lerp, sstep } from './soft.js';
import { G as KG, Part, MAT } from '../world/js/kit.js';

const V3 = THREE.Vector3, _v = new V3(), _w = new V3();
const EXPR = { neutral: null, happy: 'happy', angry: 'angry', surprised: 'surprised', sad: 'sad', think: 'look', awkward: 'shy', proud: 'smug', sleepy: 'sleepy', laugh: 'laugh', ouch: 'ouch' };
const ONE_SHOT = { talk: 2.2, nod: 1.2, shake: 1.2, raise: 1.6, cheer: 1.8, clap: 1.6, angry: 1.8, wave: 1.4, stretch: 2.7, slam: 1.8, point: 1.6, pour: 1.6, reach: 1.4 };
// 動作 → 姿勢與手上的道具（A＝兩手之間、L＝左手、R＝右手）
const ACTS = {
  idle: {}, type: { pose: 'type' }, read: { pose: 'read', A: 'book' }, tablet: { pose: 'read', A: 'tablet' }, doc: { pose: 'read', A: 'doc' },
  note: { pose: 'note', L: 'notebook', R: 'pen' }, listen: { pose: 'listen' }, think: { pose: 'think' }, nod: { pose: 'nod' }, shake: { pose: 'no' },
  raise: { pose: 'raise' }, clap: { pose: 'clap' }, cheer: { pose: 'cheer' }, drink: { pose: 'drink', R: 'cup' }, phone: { pose: 'phone', R: 'phone' },
  talk: { pose: 'talkg' }, stretch: { pose: 'stretch' }, doze: { pose: 'doze' }, slam: { pose: 'slam' }, point: { pose: 'point' },
  carry: { pose: 'carry', A: 'doc' }, present: { pose: 'present', A: 'doc' }, eat: { pose: 'eat', R: 'donut' }, magnify: { pose: 'magnify', R: 'magnifier', L: 'doc' },
  box: { pose: 'carry', A: 'box' }, paddle: { pose: 'paddle', R: 'paddle' }, pour: { pose: 'pour', R: 'cup' }, reach: { pose: 'reach' }, sulk: { pose: 'sulk' }, angry: { pose: 'slam' }, wave: { pose: 'raise' }, sleep: {},
};
const hash = (s) => { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0; return h; };

const CFG = { faceSize: 256, lodNear: 14, lodFar: 30, fxDist: 26 };
// 建立任何角色之前呼叫：detail 幾何細緻度（1＝展示頁的品質）、faceSize 臉部貼圖大小
export function configure(o = {}) { if (o.detail) DETAIL.k = o.detail; Object.assign(CFG, o); }

export function lookFor(spec) {
  const h = hash(spec.id || spec.nick || 'x'), cfgId = spec.species && SPECIES[spec.species] ? spec.species : SPECIES_IDS[h % SPECIES_IDS.length];
  const cfg = SPECIES[cfgId], pool = ['glasses', 'bow', 'scarf', 'badge', 'hat'].filter(a => canWear(cfg, a));
  let acc = spec.acc; if (!acc) { acc = []; if (pool.length && (h >> 3) % 3) acc.push(pool[(h >> 5) % pool.length]); if (spec.lead || spec.isCeo) acc.push('tie'); if (spec.isCeo) acc.push('crown', 'badge'); }
  return { species: cfgId, pal: spec.pal ?? (h >> 9) % 4, hue: spec.hue ?? (((h >> 12) % 9) - 4) * 0.008, acc: [...new Set(acc)], accColor: spec.accColor ?? (h >> 16) % 6, seed: spec.seed ?? (h | 1) };
}

// ── 頭上的情緒圖示（畫布畫的柔邊貼圖，不是文字）
const ICON = {}; const ALIAS = { '!': 'exclaim', '?': 'question', '怒': 'anger', '♪': 'note', '…': 'dots', '汗': 'sweat', '☆': 'star', '♥': 'heart' };
function iconTex(name) {
  if (ICON[name]) return ICON[name];
  const S = 128, cv = document.createElement('canvas'); cv.width = cv.height = S; const g = cv.getContext('2d'); g.translate(S / 2, S / 2); const r = S / 2;
  g.lineJoin = g.lineCap = 'round';
  const halo = (path, fill, stroke = '#fff', lw = r * 0.2) => { g.save(); g.shadowColor = 'rgba(120,80,40,.35)'; g.shadowBlur = r * 0.12; g.shadowOffsetY = r * 0.04; g.lineWidth = lw; g.strokeStyle = stroke; path(); g.stroke(); g.restore(); g.fillStyle = fill; path(); g.fill(); };
  const P = {
    exclaim() { halo(() => { g.beginPath(); g.roundRect(-r * 0.15, -r * 0.72, r * 0.3, r * 0.82, r * 0.15); g.moveTo(r * 0.17, r * 0.5); g.arc(0, r * 0.5, r * 0.17, 0, 7); }, '#ff8a3c'); },
    question() { g.save(); g.shadowColor = 'rgba(120,80,40,.35)'; g.shadowBlur = r * 0.12; g.lineWidth = r * 0.46; g.strokeStyle = '#fff'; const q = () => { g.beginPath(); g.arc(0, -r * 0.32, r * 0.3, Math.PI * 0.95, Math.PI * 2.35); g.quadraticCurveTo(0, r * 0.02, 0, r * 0.18); }; q(); g.stroke(); g.restore(); g.lineWidth = r * 0.24; g.strokeStyle = '#5b9bf0'; q(); g.stroke(); halo(() => { g.beginPath(); g.arc(0, r * 0.55, r * 0.15, 0, 7); }, '#5b9bf0', '#fff', r * 0.14); },
    anger() { g.save(); g.shadowColor = 'rgba(160,40,30,.4)'; g.shadowBlur = r * 0.12; const q = () => { for (let i = 0; i < 4; i++) { g.save(); g.rotate(i * Math.PI / 2); g.beginPath(); g.moveTo(r * 0.16, -r * 0.62); g.quadraticCurveTo(r * 0.16, -r * 0.16, r * 0.62, -r * 0.16); g.stroke(); g.restore(); } }; g.lineWidth = r * 0.36; g.strokeStyle = '#fff'; q(); g.restore(); g.lineWidth = r * 0.2; g.strokeStyle = '#ff4d4d'; q(); },
    sweat() { halo(() => { const k = r * 0.5; g.beginPath(); g.moveTo(0, -k * 1.3); g.bezierCurveTo(k * 1.0, -k * 0.1, k * 0.85, k * 1.0, 0, k * 1.0); g.bezierCurveTo(-k * 0.85, k * 1.0, -k * 1.0, -k * 0.1, 0, -k * 1.3); }, '#7cc8ff'); g.fillStyle = 'rgba(255,255,255,.8)'; g.beginPath(); g.ellipse(-r * 0.14, r * 0.12, r * 0.07, r * 0.13, 0.3, 0, 7); g.fill(); },
    bulb() { g.strokeStyle = '#ffc93c'; g.lineWidth = r * 0.09; for (let i = 0; i < 7; i++) { const a = Math.PI + i * Math.PI / 6; g.beginPath(); g.moveTo(Math.cos(a) * r * 0.66, -r * 0.12 + Math.sin(a) * r * 0.66); g.lineTo(Math.cos(a) * r * 0.86, -r * 0.12 + Math.sin(a) * r * 0.86); g.stroke(); } halo(() => { g.beginPath(); g.arc(0, -r * 0.12, r * 0.42, 0, 7); }, '#ffe066'); halo(() => { g.beginPath(); g.roundRect(-r * 0.18, r * 0.26, r * 0.36, r * 0.3, r * 0.08); }, '#c9c4dc', '#fff', r * 0.12); g.fillStyle = 'rgba(255,255,255,.75)'; g.beginPath(); g.ellipse(-r * 0.16, -r * 0.26, r * 0.1, r * 0.14, -0.5, 0, 7); g.fill(); },
    star() { halo(() => { g.beginPath(); for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * 0.36 : r * 0.72; g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); } g.closePath(); }, '#ffd84a'); },
    heart() { halo(() => { const k = r * 0.7; g.beginPath(); g.moveTo(0, k * 0.78); g.bezierCurveTo(-k * 1.25, -k * 0.05, -k * 0.62, -k * 0.98, 0, -k * 0.38); g.bezierCurveTo(k * 0.62, -k * 0.98, k * 1.25, -k * 0.05, 0, k * 0.78); }, '#ff7f9c'); },
    note() { halo(() => { g.beginPath(); g.ellipse(-r * 0.2, r * 0.4, r * 0.27, r * 0.2, -0.4, 0, 7); g.roundRect(r * 0.0, -r * 0.6, r * 0.1, r * 1.0, r * 0.05); g.moveTo(r * 0.05, -r * 0.6); g.quadraticCurveTo(r * 0.45, -r * 0.5, r * 0.5, -r * 0.12); g.lineTo(r * 0.36, -r * 0.1); g.quadraticCurveTo(r * 0.3, -r * 0.34, r * 0.05, -r * 0.36); }, '#ff8fb5'); },
    dots() { halo(() => { g.beginPath(); g.roundRect(-r * 0.74, -r * 0.34, r * 1.48, r * 0.68, r * 0.34); }, '#ffffff', '#f0d9c0', r * 0.1); g.fillStyle = '#b09a8c'; for (const x of [-0.38, 0, 0.38]) { g.beginPath(); g.arc(x * r, 0, r * 0.11, 0, 7); g.fill(); } },
    zzz() { g.font = `900 ${r * 1.3}px "Arial Rounded MT Bold","Nunito",sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineWidth = r * 0.26; g.strokeStyle = '#fff'; g.strokeText('Z', 0, 0); g.fillStyle = '#8fa8ff'; g.fillText('Z', 0, 0); },
    steam() { const gr = g.createRadialGradient(0, 0, 0, 0, 0, r * 0.9); gr.addColorStop(0, 'rgba(255,255,255,.95)'); gr.addColorStop(0.6, 'rgba(255,236,230,.6)'); gr.addColorStop(1, 'rgba(255,220,210,0)'); g.fillStyle = gr; g.beginPath(); g.arc(0, 0, r, 0, 7); g.fill(); },
    // 額度用完：空電池（紅色一格）、等核准：盾牌加鎖、出了狀況：小烏雲（不羞辱：沒有閃電、沒有黑煙）
    battery() { const body = () => { g.beginPath(); g.roundRect(-r * 0.66, -r * 0.34, r * 1.2, r * 0.68, r * 0.16); }; halo(() => { g.beginPath(); g.roundRect(r * 0.54, -r * 0.14, r * 0.16, r * 0.28, r * 0.05); }, '#b9a99a', '#fff', r * 0.14); halo(body, '#fff6ea'); g.lineWidth = r * 0.08; g.strokeStyle = '#8a766a'; body(); g.stroke(); g.fillStyle = '#ff6a4d'; g.beginPath(); g.roundRect(-r * 0.54, -r * 0.2, r * 0.2, r * 0.4, r * 0.05); g.fill(); },
    shield() { const sh = () => { g.beginPath(); g.moveTo(0, -r * 0.74); g.bezierCurveTo(r * 0.3, -r * 0.55, r * 0.55, -r * 0.5, r * 0.62, -r * 0.5); g.bezierCurveTo(r * 0.62, r * 0.2, r * 0.32, r * 0.55, 0, r * 0.78); g.bezierCurveTo(-r * 0.32, r * 0.55, -r * 0.62, r * 0.2, -r * 0.62, -r * 0.5); g.bezierCurveTo(-r * 0.55, -r * 0.5, -r * 0.3, -r * 0.55, 0, -r * 0.74); g.closePath(); }; halo(sh, '#ffb300'); g.fillStyle = '#fff'; g.beginPath(); g.roundRect(-r * 0.2, -r * 0.08, r * 0.4, r * 0.32, r * 0.06); g.fill(); g.strokeStyle = '#fff'; g.lineWidth = r * 0.1; g.beginPath(); g.arc(0, -r * 0.1, r * 0.14, Math.PI, 0); g.stroke(); },
    cloud() { halo(() => { g.beginPath(); g.arc(-r * 0.28, r * 0.06, r * 0.26, 0, 7); g.arc(r * 0.02, -r * 0.14, r * 0.34, 0, 7); g.arc(r * 0.34, r * 0.08, r * 0.26, 0, 7); g.roundRect(-r * 0.54, r * 0.06, r * 1.12, r * 0.28, r * 0.14); }, '#a9b7cf'); g.fillStyle = '#7cc8ff'; for (const x of [-0.3, 0.05, 0.38]) { g.beginPath(); g.ellipse(x * r, r * 0.62, r * 0.05, r * 0.1, 0, 0, 7); g.fill(); } },
    check() { g.save(); g.shadowColor = 'rgba(40,120,60,.4)'; g.shadowBlur = r * 0.12; const q = () => { g.beginPath(); g.moveTo(-r * 0.5, 0); g.lineTo(-r * 0.12, r * 0.4); g.lineTo(r * 0.56, -r * 0.42); g.stroke(); }; g.lineWidth = r * 0.42; g.strokeStyle = '#fff'; q(); g.restore(); g.lineWidth = r * 0.22; g.strokeStyle = '#4cc27a'; q(); },
  };
  (P[name] || P.exclaim)();
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return (ICON[name] = t);
}
export const ICON_NAMES = ['exclaim', 'question', 'anger', 'sweat', 'bulb', 'star', 'heart', 'note', 'dots', 'zzz', 'check', 'battery', 'shield', 'cloud'];

// ── 道具（每種一份合併幾何，全部角色共用；造型已經是「拿在手上」的角度：+z 朝前、+y 朝上）
const PROP = {}; let inkMat = null, inkCtx = null, inkTex = null, inkT = 0, inkN = 0, tabMat = null, tabCtx = null, tabTex = null, tabN = 0, sharedT = -1;
function sharedTextures() {
  if (inkMat) return;
  const mk = (w, h) => { const cv = document.createElement('canvas'); cv.width = w; cv.height = h; const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return [cv.getContext('2d'), t]; };
  [inkCtx, inkTex] = mk(64, 48); inkCtx.fillStyle = '#fffdf6'; inkCtx.fillRect(0, 0, 64, 48); inkMat = new THREE.MeshBasicMaterial({ map: inkTex });
  [tabCtx, tabTex] = mk(48, 32); tabCtx.fillStyle = '#f4faff'; tabCtx.fillRect(0, 0, 48, 32); tabMat = new THREE.MeshBasicMaterial({ map: tabTex });
}
// 筆記本的字跡一筆一筆出現（寫滿就翻頁）；平板畫面往上捲。全部角色共用一張貼圖，每 0.16 秒更新一次。
function tickShared(t) {
  if (!inkMat || t - sharedT < 0.16) return; sharedT = t;
  const c = inkCtx, row = Math.floor(inkN / 7), col = inkN % 7; if (row >= 6) { inkN = 0; c.fillStyle = '#fffdf6'; c.fillRect(0, 0, 64, 48); } else { c.strokeStyle = ['#5b6fa8', '#5b6fa8', '#c2527a'][row % 3]; c.lineWidth = 1.6; c.lineCap = 'round'; c.beginPath(); const x = 6 + col * 7.6, y = 7 + row * 7; c.moveTo(x, y + Math.sin(inkN * 1.7) * 1.4); c.quadraticCurveTo(x + 3, y - 2 + Math.cos(inkN) * 2, x + 6, y + Math.sin(inkN * 2.3) * 1.4); c.stroke(); inkN += (row === 5 && col === 4) ? 99 : 1; if (inkN > 90) inkN = 42; }
  inkTex.needsUpdate = true;
  const d = tabCtx; d.drawImage(d.canvas, 0, -3); d.fillStyle = '#f4faff'; d.fillRect(0, 29, 48, 3); d.fillStyle = ['#8fb6f0', '#f3a6bd', '#8fd3a6', '#f6c177'][tabN % 4]; if (tabN % 5 === 3) d.fillRect(4, 29, 14, 3); else d.fillRect(4, 30, 8 + (tabN * 13) % 30, 1.6); tabN++; tabTex.needsUpdate = true;
}
function propMesh(type) {
  if (!PROP[type]) {
    const P = new Part(); let extra = null;
    // 斜板上的小方塊：a 傾斜角（遠端翹起、板面朝向拿的人）、l 離板面的高度、z 板面上的前後位置
    const T = (a, l, z) => [l * Math.cos(a) + z * Math.sin(a), -l * Math.sin(a) + z * Math.cos(a)];
    const tb = (col, w, h, d, a, l, z, x = 0, r = 0.004, rz = 0) => { const [y, zz] = T(a, l, z); P.box(col, w, h, d, x, y - h / 2, zz, r, 0, -a, rz); };
    const plane = (w, h, a, l, z, mat) => { const g = new THREE.PlaneGeometry(w, h); g.rotateZ(Math.PI); const [y, zz] = T(a, l, z); extra = { geo: g, mat, rx: -a - Math.PI / 2, y, z: zz }; };
    switch (type) {
      case 'book': { const a = 0.75; tb('#7fa8e8', 0.3, 0.02, 0.2, a, 0, 0, 0, 0.008); for (const q of [-1, 1]) { tb('#fffdf6', 0.135, 0.02, 0.18, a, 0.014, 0, q * 0.072, 0.008, q * -0.14); for (let i = 0; i < 4; i++) tb(i === 2 ? '#e6b9c8' : '#b9c6dc', 0.1 - (i % 2) * 0.02, 0.004, 0.012, a, 0.027 + 0.004, 0.055 - i * 0.034, q * 0.07, 0.001, q * -0.14); } break; }
      case 'box': P.box('#d8a56a', 0.3, 0.2, 0.24, 0, -0.1, 0.02, 0.02); P.box('#f2dfb5', 0.07, 0.012, 0.24, 0, 0.1, 0.02, 0.004); P.box('#c99256', 0.3, 0.012, 0.09, 0, 0.098, -0.095, 0.004, 0, -0.5); P.box('#c99256', 0.3, 0.012, 0.09, 0, 0.098, 0.135, 0.004, 0, 0.5); P.sph('#93d18b', 0.07, 0.07, 0.17, 0.02); P.cyl('#fffaf2', 0.035, 0.07, -0.08, 0.1, 0.02, 0.01); break;   // 收拾桌面的紙箱
      case 'tablet': tb('#6b7285', 0.24, 0.016, 0.17, 0.8, 0, 0, 0, 0.007); plane(0.21, 0.14, 0.8, 0.0095, 0, 'tab'); break;
      case 'notebook': { const a = 0.6; tb('#ffd27a', 0.2, 0.018, 0.16, a, 0, 0, 0, 0.007); tb('#fffdf6', 0.185, 0.012, 0.15, a, 0.012, 0, 0.004, 0.005); for (let i = 0; i < 5; i++) { const [y, z] = T(a, 0.016, (i - 2) * 0.028); P.add(KG.torus(0.012, 0.004, 8), '#9aa0aa', -0.096, y, z, Math.PI / 2, 0, 0); } plane(0.16, 0.125, a, 0.0195, 0, 'ink'); break; }
      case 'pen': P.cyl('#5b8def', 0.011, 0.11, 0, -0.02, 0, 0.004); P.cyl('#f6c177', 0.011, 0.02, 0, -0.04, 0, 0.004, 0.004); P.sph('#ff9f9f', 0.013, 0, 0.095, 0); break;
      case 'phone': P.box('#5c6378', 0.062, 0.115, 0.014, 0, -0.03, 0, 0.006); P.box('#bfe3ff', 0.05, 0.09, 0.004, 0, -0.018, 0.008, 0.002); break;
      case 'cup': P.cyl('#fffaf2', 0.045, 0.085, 0, -0.03, 0, 0.012, 0.052, 14); P.cyl('#8a5a3c', 0.042, 0.006, 0, 0.05, 0, 0.002, 0.042, 14); P.add(KG.torus(0.028, 0.009, 12), '#fffaf2', 0.056, 0.012, 0); break;
      case 'doc': { const a = 0.9; tb('#ffffff', 0.21, 0.008, 0.27, a, 0, 0); tb('#f6c177', 0.15, 0.004, 0.024, a, 0.006, 0.095, 0, 0.001); for (let i = 0; i < 5; i++) tb(i === 3 ? '#f3a6bd' : '#b9c6dc', 0.16 - (i % 2) * 0.04, 0.004, 0.012, a, 0.006, 0.05 - i * 0.034, -(i % 2) * 0.02, 0.001); break; }
      case 'donut': P.add(KG.torus(0.038, 0.02, 14), '#e8b06a', 0, 0, 0, 0, 0.4); P.add(KG.torus(0.038, 0.016, 14), '#ff9fbd', 0, 0.003, 0.008, 0, 0.4); break;
      case 'magnifier': P.add(KG.torus(0.05, 0.01, 16), '#8a6a5a', 0, 0.07, 0); P.add(KG.cyl(0.046, 0.004, 0.001, 16), '#cfefff', 0, 0.07, -0.002, 0, Math.PI / 2); P.cyl('#f6c177', 0.011, 0.075, 0, -0.06, 0, 0.004); break;
      case 'paddle': P.add(KG.cyl(0.07, 0.014, 0.005, 16), '#f2706a', 0, 0.08, -0.007, 0, Math.PI / 2); P.cyl('#e9c79c', 0.013, 0.08, 0, -0.07, 0, 0.004); break;
    }
    PROP[type] = { geo: P.geometry(), extra };
  }
  const d = PROP[type], m = new THREE.Mesh(d.geo, MAT.solid); m.userData.prop = type;
  if (d.extra) { sharedTextures(); const e = new THREE.Mesh(d.extra.geo, d.extra.mat === 'ink' ? inkMat : tabMat); e.rotation.x = d.extra.rx; e.position.set(0, d.extra.y, d.extra.z); m.add(e); }
  return m;
}

let serial = 0;
export function createCharacter(spec, env = {}) {
  const s = spec.scale || 1, root = new THREE.Group(), space = new THREE.Group(); root.add(space); space.matrixAutoUpdate = false; root.userData.character = true;
  const look = lookFor(spec), B = env.bounds || { x0: 0.6, x1: 39.4, z0: 0.6, z1: 33 };
  // 給底層角色用的世界：平地；被丟出去時不會飛出建築外
  const world = { plantShake: 0, groundAt: () => ({ h: 0, s: null }), pushBox() { }, bounceTramp() { }, mkShadow: () => { const m = new THREE.Mesh(); m.visible = false; m.material = new THREE.MeshBasicMaterial(); return m; },
    resolve(p, r, y, v) { let hit = null; const x0 = B.x0 / s, x1 = B.x1 / s, z0 = B.z0 / s, z1 = B.z1 / s; if (p.x < x0) { p.x = x0; if (v.x < 0) v.x *= -0.5; hit = { tag: 'wall' }; } else if (p.x > x1) { p.x = x1; if (v.x > 0) v.x *= -0.5; hit = { tag: 'wall' }; } if (p.z < z0) { p.z = z0; if (v.z < 0) v.z *= -0.5; hit = { tag: 'wall' }; } else if (p.z > z1) { p.z = z1; if (v.z > 0) v.z *= -0.5; hit = { tag: 'wall' }; } return hit; } };
  // 粒子：座標換回真實世界；離鏡頭遠就不放；只有被互動的那一下才出聲
  const F = env.fx, dummy = { userData: {} }; let loud = 0;
  const near = () => !env.camera || env.camera.position.distanceTo(root.position) < CFG.fxDist || loud > 0;
  const fx = F ? {
    T: F.T, update() { }, sfx(n, a) { if (loud > 0) F.sfx(n, a); },
    spawn(type, p, o = {}) { if (!near() || !root.visible) return dummy; if (s === 1) return F.spawn(type, p, o); if (o.follow) return dummy; return F.spawn(type, _w.copy(p).multiplyScalar(s), { ...o, v: o.v ? o.v.clone().multiplyScalar(s) : undefined, size: (o.size || 0.2) * s }); },
    burst(type, p, n, o = {}) { if (!near() || !root.visible) return; if (s === 1) F.burst(type, p, n, o); else F.burst(type, _w.copy(p).multiplyScalar(s), n, { ...o, speed: (o.speed || 1) * s, up: (o.up || 0) * s, size: (o.size || 0.2) * s }); },
  } : stubFx;
  const ch = new Character(look, null, world, fx, { space, faceSize: CFG.faceSize });
  ch.ext = { vx: 0, vz: 0, yaw: 0, y: 0 }; ch.pos.set(0, 0, 0); ch.bounds = { x0: B.x0 / s, x1: B.x1 / s, z0: B.z0 / s, z1: B.z1 / s };
  // 場景的影子是靜態烘的，角色不投影（腳下另有接觸陰影）
  const tiny = [], small = []; space.traverse(o => { if (!o.isMesh) return; o.castShadow = false; o.receiveShadow = false; if (o.userData.limb) { small.push(o); return; } if (o.userData.tiny) { tiny.push(o); return; } if (o !== ch.main && o.geometry) { o.geometry.boundingSphere || o.geometry.computeBoundingSphere(); const r = o.geometry.boundingSphere.radius * Math.max(o.scale.x, o.scale.y, o.scale.z); if (r < 0.045) tiny.push(o); else if (r < 0.1) small.push(o); } });
  const camP = new V3(0, 6, 10), aenv = { look: null, cam: camP, idleScale: 0 }, ctl = { mx: 0, mz: 0, run: false, jump: false };
  const slot = { A: null, L: null, R: null }, slotType = { A: '', L: '', R: '' }; let icon = null, iconT = 0, iconDur = 0, lod = 0, frame = (serial++) % 6, accDt = 0, react = null;
  const c = {
    object3D: root, spec, look, inner: ch, scale: s, radius: ch.R * 0.85 * s, height: (ch.cfg.top + (ch.cfg.floatH || 0) + 0.06) * s, speech: null, emoteSym: null, expression: 'neutral', action: 'idle', lift: 0,
    _base: 'idle', _until: 0, _t: 0, _path: null, _pi: 0, _speed: 1.6, _resolve: null, _stuck: 0, _ghost: 0, _seat: null, _hop: null, _held: false, heading: 0, onDrop: null,
    get state() { return c._held ? 'held' : (c._path || (c._hop && c._hop.off)) ? 'walk' : c._seat ? 'sit' : 'stand'; },
    get lod() { return lod; },
    update(dt, t) {
      c._t = t; dt = Math.min(dt, 0.05); if (loud > 0) loud -= dt;
      // 場景可能直接改 object3D.position（瞬移），以它為準
      if (!c._held && !c._hop && Math.abs(root.position.x - ch.pos.x * s) + Math.abs(root.position.z - ch.pos.z * s) > 0.5) place(root.position.x, root.position.z);
      if (c._until && t > c._until) { c._until = 0; apply(c._base); }
      if (c.speech && t > c.speech.until) c.speech = null; if (c.emoteSym && t > c.emoteSym.until) c.emoteSym = null;
      if (react && t > react.until) { const r = react; react = null; r.done && r.done(); }
      if (c._held) { ch.ext.vx = ch.ext.vz = 0; }
      else if (c._hop) { ch.ext.vx = ch.ext.vz = 0; }
      else if (c._path) { if (c._pause) { ch.ext.vx = ch.ext.vz = 0; } else step(dt); }   // 被點選時暫停走路（轉過來面向鏡頭），取消後從原地接著走原路
      else if (c._drive) { const d = c._drive; ch.ext.vx = d.vx / s; ch.ext.vz = d.vz / s; if (d.fx || d.fz) c.heading = Math.atan2(d.fx, d.fz); else if (d.vx || d.vz) c.heading = Math.atan2(d.vx, d.vz); }
      else { ch.ext.vx = ch.ext.vz = 0; }
      if (!c._held) ch.ext.yaw = c.heading;
      if (cushion) cushion.visible = !!c._seat && c._boost > 0 && !c._hop && lod < 2 && root.visible;
      const n = Math.max(1, Math.ceil(dt / (1 / 90))), h = dt / n; for (let i = 0; i < n; i++) ch.step(h, ctl);
      if (c._hop && !c._held) hopStep(dt);
      if (c._held && ch.mode === 'normal' && ch.grounded && !ch.extFall) dropped();
      root.position.set(ch.pos.x * s, 0, ch.pos.z * s); root.rotation.y = ch.yaw; c.lift = (ch.pos.y + ch.yOff) * s;
      // 遠近分級：遠的隔幾幀才更新一次姿態與表情
      let dist = 0; if (env.camera) { camP.copy(env.camera.position); dist = camP.distanceTo(root.position); camP.multiplyScalar(1 / s); }
      const want = c._held || react || env.followed === c ? 0 : dist > CFG.lodFar ? 2 : dist > CFG.lodNear ? 1 : 0; if (want !== lod) setLod(want);
      accDt += dt; frame++;
      if (lod === 0 || c._path || c._hop || frame % (lod + 1) === 0) {
        root.updateMatrix(); space.matrix.copy(root.matrix).invert(); if (s !== 1) space.matrix.scale(_v.set(s, s, s)); root.updateMatrixWorld(true);
        ch.animate(Math.min(accDt, 0.1), aenv); accDt = 0; props(t); tickShared(t);
      } else { root.updateMatrix(); space.matrix.copy(root.matrix).invert(); if (s !== 1) space.matrix.scale(_v.set(s, s, s)); root.updateMatrixWorld(true); }
      if (icon && icon.visible) {
        iconT += dt; const u = iconT / iconDur; if (u >= 1) icon.visible = false; else { const pop = u < 0.12 ? 1 + 0.5 * Math.sin(u / 0.12 * Math.PI) : 1, k = clamp(dist * 0.03, 0.34, 1.3) * pop * (u > 0.85 ? (1 - u) / 0.15 : Math.min(1, u / 0.06)); icon.scale.setScalar(k); icon.position.set(0, c.height + c.lift + 0.2 + dist * 0.04 + k * 0.5 + Math.sin(iconT * 5) * 0.02, 0); }   // 圖示放在名牌上方
      }
    },
    setAction(name, opts = {}) { if (!ACTS[name]) name = 'idle'; if (ONE_SHOT[name]) { c._until = c._t + (opts.duration || ONE_SHOT[name]); if (opts.then) c._base = opts.then; apply(name); } else { c._base = name; if (opts.duration) { c._until = c._t + opts.duration; c._base = opts.then || 'idle'; apply(name); } else if (!c._until) apply(name); } },
    setExpression(name, sec) { c.expression = name; const e = EXPR[name]; if (e) ch.emote(e, sec || 1e9); else ch.emo = null; },
    // 外部操控（pilot.js）：直接給世界速度（公尺／秒）與想面向的方向；傳 null 結束。走路／跑步的腳步由實際速度推進，不會滑行
    drive(vx, vz, fx, fz) { c._drive = vx == null ? null : { vx, vz, fx: fx || 0, fz: fz || 0 }; if (vx == null) { ch.ext.vx = ch.ext.vz = 0; } },
    walkTo(path, opts = {}) {
      c._drive = null; c.stop(false); if (!path || path.length < 2 || c._held) return Promise.resolve(!c._held);
      c._path = path; c._pi = 1; c._speed = opts.speed || 1.6; c._stuck = 0;
      if (ch.mode !== 'normal') { ch.mode = 'normal'; ch.modeT = 0; }
      if (c._seat) {         // 從椅子上跳下來，再開始走
        const p = path[1]; c._seat = null; c.heading = Math.atan2(p.x - ch.pos.x * s, p.z - ch.pos.z * s);
        hopTo(p.x, 0, p.z, { off: true, done() { c._pi = 2; if (c._pi >= c._path.length) c.stop(true); } });
      } else { ch.ext.y = 0; }
      return new Promise(res => { c._resolve = res; });
    },
    stop(ok = false) { if (c._path) { c._path = null; const r = c._resolve; c._resolve = null; ch.ext.vx = ch.ext.vz = 0; if (c._hop && c._hop.off) { c._hop = null; ch.ext.y = 0; } if (r) r(ok); } },
    // 坐到座位：人就在旁邊的話會跳上去，否則直接放上去（開場、整修後）
    sitAt(seat, opts = {}) {
      c.stop(false); if (c._held) return; const d = Math.hypot(seat.x - ch.pos.x * s, seat.z - ch.pos.z * s); c._seat = seat;
      const sy = seatY(seat);
      if (opts.instant || d > 2.4 || d < 0.05) { c._hop = null; place(seat.x, seat.z); ch.pos.y = sy / s; ch.ext.y = ch.pos.y; c.heading = ch.yaw = seat.face; seated(); return; }
      if (ch.mode !== 'normal') ch.mode = 'normal'; c.heading = Math.atan2(seat.x - ch.pos.x * s, seat.z - ch.pos.z * s);
      hopTo(seat.x, sy, seat.z, { done() { c.heading = seat.face; seated(); } });
    },
    standAt(x, z, face) { c.stop(false); if (c._held) return; c._seat = null; c._hop = null; ch.mode = 'normal'; place(x, z); ch.ext.y = 0; ch.pos.y = 0; if (face != null) { c.heading = face; ch.yaw = face; } },
    faceTo(x, z) { const dx = x - ch.pos.x * s, dz = z - ch.pos.z * s; if (dx * dx + dz * dz > 1e-4) { c.heading = Math.atan2(dx, dz); if (ch.mode === 'sit') ch.yawTo = c.heading; } },
    say(text, sec = 2.6) { c.speech = { text, until: c._t + sec }; ch.speech = { text, t: sec, talk: Math.min(sec, 0.25 + text.length * 0.16) }; },
    // 頭上圖示：exclaim question anger sweat bulb star heart note dots zzz check（舊的文字符號也認得）
    emote(sym, sec = 2) {
      const name = ALIAS[sym] || sym; c.emoteSym = { sym: name, until: c._t + sec };
      if (!icon) { icon = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false, depthTest: false })); icon.renderOrder = 30; root.add(icon); }
      icon.material.map = iconTex(name); icon.material.needsUpdate = true; icon.visible = true; iconT = 0; iconDur = sec;
    },
    // ── 互動
    pet(sec = 2.2) { loud = sec + 1; hold(sec + 0.6); ch.petStart(null, true); c.emote('heart', sec); react = { until: c._t + sec, done() { ch.petEnd(); } }; },
    bonk() {
      loud = 3; hold(3.2); ch.petting = false; ch.sqV -= 11; ch.wobV.x += 3 * (Math.random() - 0.5); ch.wobV.z += 2.5; fx.sfx('bonk');
      fx.burst('star', ch.headTop(new V3()).add(_v.set(0, 0.05, 0)), 6, { speed: 1.5, up: 1.6, g: 5, life: 0.8, size: 0.17, spin: 5 });
      ch.emote('ouch', 0.9); c.emote('sweat', 2.4); c.say(['嗚…', '好痛…', '我會改進的…'][Math.floor(Math.random() * 3)], 2);
      const base = c._base, until = c._until; c._until = 0; apply('sulk'); react = { until: c._t + 2.6, done() { c._until = until; apply(base); } };
      setTimeout(() => { if (react) ch.emote('sad', 1.9); }, 800);
    },
    feed() {
      loud = 4; hold(5); const base = c._base; c._until = 0; apply('eat'); c.emote('note', 1.2);
      react = { until: c._t + 3.2, done() { apply(base); ch.emote('happy', 1.6); c.emote('heart', 1.6); c.say(['好吃！', '謝謝～', '還要！'][Math.floor(Math.random() * 3)], 1.6); fx.sfx('heart'); fx.burst('heart', ch.headTop(new V3()), 4, { speed: 0.35, up: 0.7, life: 1.1, size: 0.17, sway: 0.4 }); } };
    },
    grab() { c.stop(false); c._hop = null; c._seat = null; c._held = true; c._until = 0; react = null; loud = 9; apply('idle'); ch.ext.y = 0; ch.petting = false; ch.grab(); },
    dragTo(x, y, z) { ch.dragTo(_v.set(x / s, y / s, z / s)); loud = 6; },
    release() { if (!c._held) return; ch.release(); if (ch.mode === 'normal') { ch.extFall = true; ch.vel.x = ch.vel.z = 0; } },
    setVisible(v) { root.visible = v; },
    // ── 鏡頭互動（world/js/attention.js、pov.js 使用）──
    // 視線：給世界座標就看向那裡（頭與眼睛轉過去），null 恢復自己亂看
    lookAt(v) { aenv.look = v ? (aenv.lookV || (aenv.lookV = new V3())).copy(v) : null; },
    pause(on) { c._pause = !!on; if (on && c._path) { ch.ext.vx = ch.ext.vz = 0; } },
    // 坐著時轉椅子：只轉身體朝向（位置不動）；給 null 轉回座位原本的朝向
    swivel(yaw) { if (ch.mode !== 'sit' || !c._seat) return false; ch.yawTo = yaw == null ? c._seat.face : yaw; return true; },
    // 被注意到：精神一振（身體微彈）＋開心的眼神，不打斷手上的動作
    perk(sec = 1.1) { ch.sqV += 3.2; if (!c.sleeping) ch.emote('happy', sec); },
    // 眼睛的世界座標（角色視角用）：嘴巴高度往上約三成頭高，再往前到臉的表面；身高、坐姿、漂浮、蹲下都會算進去
    eye(out) {
      const cf = ch.cfg, y = (ch.pos.y + ch.yOff + cf.mouth[1] + (cf.top - cf.mouth[1]) * 0.35) * s, f = cf.front * 0.7 * s;
      return out.set(root.position.x + Math.sin(ch.yaw) * f, y, root.position.z + Math.cos(ch.yaw) * f);
    },
    // 角色視角時，自己的身體從主鏡頭看不到（放到第 1 層，主鏡頭只畫第 0 層）；每次都重掃，因為手上的道具、頭上的圖示會中途加進來
    hideFromCam(on) { const L = on ? 1 : 0; root.traverse(o => { if (o.layers.mask !== (1 << L)) o.layers.set(L); }); c._hidCam = !!on; },
    dispose() { space.traverse(m => { if (m.isMesh && m.material && m.material.userData && m.material.userData.U) m.material.dispose(); }); ch.main.geometry.dispose(); ch.dispose(); if (icon) icon.material.dispose(); root.removeFromParent(); },
  };
  // 互動反應期間，場景排的「下一件桌上工作」往後延，反應才不會被蓋掉
  function hold(sec) { c.workAt = Math.max(c.workAt || 0, c._t + sec); }
  function place(x, z) { ch.pos.x = x / s; ch.pos.z = z / s; ch.vel.set(0, 0, 0); ch.grounded = true; ch.feet.forEach(f => { ch.footHome(f, f.p); f.planted = true; f.v.set(0, 0, 0); }); ch.hands.forEach(h => { h.p.set(ch.pos.x, ch.pos.y + 0.3, ch.pos.z); h.v.set(0, 0, 0); }); root.position.set(x, 0, z); }
  // 個子矮的坐在辦公椅上會被桌子擋住臉：椅子上多一塊加高坐墊，讓嘴巴高過桌面
  let cushion = null;
  function seatY(seat) {
    const base = Math.max(0, seat.y - 0.04), chair = seat.y > 0.405 && seat.y < 0.435; let boost = chair ? clamp(0.93 - (ch.cfg.mouth[1] * s + base), 0, 0.27) : 0; if (boost < 0.03) boost = 0;
    if (boost) { if (!cushion) { cushion = new THREE.Mesh(KG.cyl(0.21, 1, 0.03, 16), new THREE.MeshStandardMaterial({ color: new THREE.Color(spec.color || '#ffd9b0').lerp(new THREE.Color('#ffffff'), 0.35), roughness: 0.9 })); cushion.userData.prop = 'cushion'; space.add(cushion); } cushion.position.set(seat.x / s, (base - 0.01) / s, seat.z / s); cushion.scale.set(1 / s, (boost + 0.02) / s, 1 / s); }
    c._boost = boost; return base + boost;
  }
  function seated() { ch.vel.set(0, 0, 0); ch.grounded = true; ch.yaw = ch.yawTo = c.heading; ch.mode = c.action === 'sleep' ? 'sleep' : 'sit'; ch.modeT = 0; ch.idleSit = false; ch.sqV -= 2.5; }
  function dropped() { c._held = false; c._seat = null; ch.ext.y = 0; c.heading = ch.yaw; if (c.onDrop) c.onDrop(c); }
  // 跳上、跳下椅子：拋物線＋起跳下蹲、落地擠壓；從椅背那一側過來就跳高一點
  function hopTo(x, y, z, o = {}) {
    const x0 = ch.pos.x, y0 = ch.pos.y, z0 = ch.pos.z, d = Math.hypot(x / s - x0, z / s - z0); let hh = 0.24 + d * 0.18;
    const seat = o.off ? null : c._seat; if (seat) { const bx = -Math.sin(seat.face), bz = -Math.cos(seat.face), dot = ((x0 * s - seat.x) * bx + (z0 * s - seat.z) * bz) / (d * s || 1); if (dot > 0.55) hh = 0.7; }
    c._hop = { x0, y0, z0, x1: x / s, y1: y / s, z1: z / s, h: hh / s, t: -0.14, dur: 0.34 + d * 0.16 + (hh > 0.5 ? 0.1 : 0), ...o }; ch.sqV -= 3.2;
  }
  function hopStep(dt) {
    const h = c._hop; h.t += dt / h.dur; if (h.t < 0) return; const u = Math.min(1, h.t), e = u;
    ch.pos.x = lerp(h.x0, h.x1, e); ch.pos.z = lerp(h.z0, h.z1, e); ch.pos.y = ch.ext.y = lerp(h.y0, h.y1, e) + h.h * 4 * u * (1 - u);
    if (u >= 1) { c._hop = null; ch.pos.y = ch.ext.y = h.y1; ch.sqV -= 3; ch.feet.forEach(f => { ch.footHome(f, f.p); f.planted = true; }); h.done && h.done(); }
  }
  function apply(name) {
    c.action = name; const a = ACTS[name] || {}; ch.extPose = a.pose || null; ch.poseT = 0;
    setSlot('A', a.A); setSlot('L', a.L); setSlot('R', a.R);
    if (name === 'sleep') { if (ch.mode !== 'sleep' && !c._hop && !c._held) { ch.mode = 'sleep'; ch.modeT = 0; } return; }
    if (ch.mode === 'sleep') { ch.mode = c._seat ? 'sit' : 'normal'; ch.modeT = 0; }
    if (name === 'angry') ch.emote('angry', ONE_SHOT.angry);
    if (name === 'wave' && ch.mode === 'normal' && !c._hop) { ch.extPose = null; ch.doAct('wave'); ch.speech = null; }
  }
  function setSlot(k, type) {
    if (slotType[k] === (type || '')) return; slotType[k] = type || '';
    if (slot[k]) { slot[k].removeFromParent(); slot[k] = null; }
    if (type) { slot[k] = propMesh(type); slot[k].visible = lod < 2; space.add(slot[k]); }
  }
  // 道具跟著手；沒有手的物種讓道具飄在身邊
  function props(t) {
    if (!slot.A && !slot.L && !slot.R) return; const cf = ch.cfg, yaw = ch.root.rotation.y, cy = Math.cos(yaw), sy = Math.sin(yaw), H = ch.hands, bob = Math.sin(t * 2.3 + ch.phase0) * 0.012;
    const by = ch.pos.y + ch.yOff, loc = (m, x, y, z) => m.position.set(ch.pos.x + x * cy + z * sy, by + y, ch.pos.z - x * sy + z * cy);
    const pose = ch.extPose, pt = ch.poseT; let tiltR = 0, kR = 0;
    if (pose === 'drink') { const u = (pt % 3.2) / 3.2; kR = sstep(0.1, 0.3, u) * (1 - sstep(0.62, 0.8, u)); tiltR = -0.9 * kR; }
    else if (pose === 'eat') { const u = (pt % 1.9) / 1.9; kR = sstep(0.05, 0.3, u) * (1 - sstep(0.5, 0.7, u)); }
    if (slot.A) { const m = slot.A; if (H.length) { m.position.copy(H[0].p).add(H[1].p).multiplyScalar(0.5); m.position.y += 0.035; m.position.x += sy * 0.03; m.position.z += cy * 0.03; } else loc(m, 0, cf.mouth[1] - 0.14 + bob, cf.front + 0.2); m.rotation.set(pose === 'present' ? 0.35 : 0, yaw, 0); }
    if (slot.L) { const m = slot.L; if (H.length) { m.position.copy(H[0].p); m.position.y += 0.04; m.position.x += sy * 0.05; m.position.z += cy * 0.05; } else loc(m, -0.1, cf.mouth[1] - 0.16 + bob, cf.front + 0.2); m.rotation.set(0, yaw, 0); }
    if (slot.R) {
      const m = slot.R, ty = slotType.R;
      if (H.length) { m.position.copy(H[1].p); m.position.y += ty === 'pen' ? 0.05 : 0.045; if (ty === 'cup' || ty === 'donut') { m.position.x += sy * 0.04; m.position.z += cy * 0.04; } }
      else if (ty === 'phone') loc(m, cf.cheek[0] + 0.08, cf.cheek[1] + 0.03 + bob, cf.cheek[2] - 0.08);
      else if (ty === 'pen') loc(m, 0.02 + Math.sin(t * 13) * 0.035, cf.mouth[1] - 0.06 + Math.sin(t * 21) * 0.012, cf.front + 0.19);
      else if (ty === 'magnifier') loc(m, 0.1 + Math.sin(t * 0.8) * 0.06, cf.mouth[1] + 0.02 + bob, cf.front + 0.24);
      else if (ty === 'paddle') { const u = (pt * 1.25) % 1, k = sstep(0.3, 0.5, u) * (1 - sstep(0.5, 0.8, u)); loc(m, 0.34 - 0.25 * k, cf.mouth[1] + 0.1 * k, cf.front * 0.3 + 0.4 * k); }
      else loc(m, lerp(0.24, 0.04, kR), lerp(cf.mouth[1] - 0.1, cf.mouth[1] + 0.02, kR) + bob, cf.front + lerp(0.14, 0.06, kR));
      m.rotation.set(tiltR, yaw + (ty === 'phone' ? 0.5 : 0), ty === 'pen' ? -0.5 : ty === 'phone' ? 0.25 : 0, 'YXZ');
    }
  }
  // 遠近分級：中距離藏掉很小的零件，遠距離再藏掉手、腳、配件與道具（俯瞰全景時每隻只剩身體與大特徵）
  function setLod(l) { lod = l; for (const o of tiny) o.visible = l === 0; for (const o of small) o.visible = l < 2; for (const k in slot) if (slot[k]) slot[k].visible = l < 2; }
  function step(dt) {
    const p = ch.pos, tgt = c._path[c._pi]; let dx = tgt.x / s - p.x, dz = tgt.z / s - p.z; const dist = Math.hypot(dx, dz) * s;
    if (dist < 0.1) { c._pi++; if (c._pi >= c._path.length) c.stop(true); return; }
    dx /= dist / s; dz /= dist / s; let vx = dx * c._speed, vz = dz * c._speed, slow = 1; c._ghost = Math.max(0, c._ghost - dt);
    if (env.separation && c._ghost <= 0 && !spec.pet) { const q = env.separation(c, dx, dz); vx += q.x; vz += q.z; slow = q.slow ?? 1; }
    const sp = Math.min(c._speed * slow, dist / dt), vl = Math.hypot(vx, vz) || 1; vx = vx / vl * sp; vz = vz / vl * sp;
    if (env.isFree && !env.isFree(p.x * s + vx * dt, p.z * s + vz * dt)) { vx = dx * sp; vz = dz * sp; }
    const prog = (vx * dx + vz * dz) * dt; if (prog < c._speed * dt * 0.25) { c._stuck += dt; if (c._stuck > 0.9) { c._ghost = 1.2; c._stuck = 0; } } else c._stuck = Math.max(0, c._stuck - dt);
    ch.ext.vx = vx / s; ch.ext.vz = vz / s; c.heading = Math.atan2(vx, vz);
  }
  return c;
}
