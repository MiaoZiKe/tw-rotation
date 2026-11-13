// 臉部控制（Facial Rig v2）：立體眼球（貼合曲面）＋眼皮殼＋固定高光＋貼合曲面的臉貼片（腮紅、鼻、嘴、眉、淚）。
// 十種狀態：正常睜眼 neutral｜自然眨眼（自動／blink()）｜開心閉眼 happy｜疑惑 confused｜難過 sad｜生氣 angry｜驚訝 surprised｜睡覺 sleep｜嘴角微笑 smile｜視線追蹤（lookAt）
// 座標：全部用「模型座標」（Y 向上、臉朝 +Z、單位公尺），錨點資料來自 mochi.json。
import * as THREE from 'three';
import { EXPR } from '../play/face.js';

const V3 = THREE.Vector3, clamp = (x, a, b) => Math.max(a, Math.min(b, x)), D2R = Math.PI / 180;
// 在舊版 EXPR 之上補：疑惑、微笑、較淺的待機嘴角；asym＝兩側不對稱（疑惑用）
const B2 = { asym: 0 };
export const FACE_EXPR = {};
for (const k of Object.keys(EXPR)) FACE_EXPR[k] = { ...B2, ...EXPR[k] };
// 待機表情＝舊版 neutral（嘴角 0.55、腮紅 0.6），不再另外調淡
FACE_EXPR.smile = { ...FACE_EXPR.neutral, mCurve: 0.78, mW: 1.05, blush: 0.8 };
FACE_EXPR.confused = { ...FACE_EXPR.neutral, asym: 1, brow: 1, browA: -0.5, browY: 7, mCurve: 0.0, mOpen: 0.2, mW: 0.55, mRound: 1, smirk: 0.7, blush: 0.45, lidT: 0.06, eyeS: 1.0 };
FACE_EXPR.sad = { ...FACE_EXPR.sad, lidT: 0.16 };
export const EXPR_LIST = [['neutral', '正常睜眼'], ['happy', '開心閉眼'], ['confused', '疑惑'], ['sad', '難過'], ['angry', '生氣'], ['surprised', '驚訝'], ['sleep', '睡覺'], ['smile', '嘴角微笑']];
const KEYS = Object.keys(FACE_EXPR.neutral);

// 眼球與眼皮的尺寸（公尺）：a 半寬、b 半高、c 沿法線的凸出厚度；center 埋在表面下 d
const EYE = { a: 0.077, b: 0.104, c: 0.054, d: 0.022 };   // 舊版眼睛：rx 36／ry 47（512 貼圖、跨 2.2 弧度）＝直立橢圓

function basisQuat(n) {
  const z = new V3(...n).normalize(), x = new V3(0, 1, 0).cross(z).normalize(), y = z.clone().cross(x);
  return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
}
// 閉眼時線條畫在身體表面上（眼球座標系的 z：表面在 +d，再依曲率往下掉一點，抬高 3.5 mm 讓線條不被皮膚吃掉）
function skinZ(x, y) { return EYE.d + 0.0035 - (x * x + y * y) / (2 * 0.8); }
function ellPoint(x, y, k = 1) { const a = EYE.a * k, b = EYE.b * k, c = EYE.c * k; const t = 1 - (x / a) ** 2 - (y / b) ** 2; return Math.max(0, t) > 0 ? c * Math.sqrt(t) : 0; }

function irisTexture() {
  // 深色亮眼：極深的外緣、一圈略淺的暖棕虹膜（下半部更亮，像被光穿過）、中央瞳孔
  const s = 256, cv = document.createElement('canvas'); cv.width = cv.height = s; const g = cv.getContext('2d'), c = s / 2;
  // 舊版眼睛：#3a2622 為主、下緣漸變到 #6e4638（偏灰棕，不偏紅）；中央只留一點略深的瞳孔給視線追蹤看
  g.fillStyle = '#2a1a16'; g.fillRect(0, 0, s, s);
  let gr = g.createRadialGradient(c, c, 0, c, c, c);
  gr.addColorStop(0, '#3a2c29'); gr.addColorStop(0.25, '#4a3a36'); gr.addColorStop(0.6, '#43332f'); gr.addColorStop(0.85, '#2c1c18'); gr.addColorStop(1, '#241512');
  g.fillStyle = gr; g.beginPath(); g.arc(c, c, c, 0, 7); g.fill();
  gr = g.createLinearGradient(0, c * 0.5, 0, c * 1.9); gr.addColorStop(0, 'rgba(120,86,74,0)'); gr.addColorStop(1, 'rgba(120,86,74,0.8)');
  g.fillStyle = gr; g.fillRect(0, 0, s, s);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}
let IRIS = null; const SHARED = {};   // 所有角色共用的不變幾何（眼球帽、眼皮殼、笑眼弧）：每隻只剩高光網格與臉貼片是自己的
const shared = (k, mk) => SHARED[k] || (SHARED[k] = (() => { const g = mk(); g.userData.shared = true; return g; })());

export class FaceRig {
  /** meta：mochi.json；holder：掛在 head 骨頭下、已抵銷骨頭靜止矩陣的群組；decal：臉貼片 SkinnedMesh；skinMat：眼皮用的毛料材質 */
  constructor(meta, holder, decal, lidMat, opts = {}) {
    this.meta = meta; this.holder = holder; this.cur = { ...FACE_EXPR.neutral }; this.target = FACE_EXPR.neutral; this.name = 'neutral'; this.time = 0;
    this.blinkT = 1.2; this.blink = 0; this.blinkV = 0; this.gaze = { yaw: 0, pitch: 0, ty: 0, tp: 0 }; this.sac = { x: 0, y: 0, t: 1 }; this.talk = 0; this.dirty = true; this.autoBlink = true; this.eyeScale = 1;
    this.morphScale = new V3(1, 1, 1);
    this.eyeSeg = opts.lod >= 1 ? [28, 10] : [56, 18]; this.hlSeg = opts.lod >= 1 ? 14 : 28;
    this.eyes = [-1, 1].map(s => this.buildEye(s, lidMat[s > 0 ? 'L' : 'R']));
    this.decal = decal; this.initDecal(opts.faceW || 640);
    this.update(0.001);
  }
  buildEye(side, lidMat) {
    const nm = side > 0 ? 'eye.L' : 'eye.R', A = this.meta.anchors[nm], n = new V3(...A.n), p = new V3(...A.p), q = basisQuat(A.n);
    const grp = new THREE.Group(); grp.position.copy(p).addScaledVector(n, -EYE.d); grp.quaternion.copy(q); grp.userData.base = grp.position.clone(); this.holder.add(grp);
    // dep：眼球、高光、眼皮殼的共同外層。閉眼時沿法線方向壓平埋進身體（見 applyEyes），閉眼處就只剩身體本身的皮膚，沒有任何一塊「眼皮殼」可以跟周圍顏色對不上。
    const dep = new THREE.Group(); grp.add(dep);
    const ball = new THREE.Group(); dep.add(ball);
    // 眼球：只做會露出來的前半球帽（75°），一顆網格＋一張極座標貼圖（瞳孔、虹膜、外圍深色），跟著眼球轉＝瞳孔在動
    const [CS, CR] = this.eyeSeg, geo = shared('cap' + CS, () => { const g = new THREE.SphereGeometry(1, CS, CR, 0, Math.PI * 2, 0, 75 * D2R).rotateX(Math.PI / 2); const pos = g.attributes.position, uv = g.attributes.uv, tm = 64 * D2R; for (let i = 0; i < pos.count; i++) { const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i), th = Math.acos(Math.max(-1, Math.min(1, z))), ph = Math.atan2(y, x), r = 0.5 * Math.min(1, th / tm); uv.setXY(i, 0.5 + r * Math.cos(ph), 0.5 + r * Math.sin(ph)); } return g; });
    IRIS ||= irisTexture();
    // 每隻眼睛自己一個材質（共用貼圖與著色器程式）：眼皮不再用「另一層殼」遮眼球，而是在著色器裡把眼球被眼皮蓋住的半球直接切掉（discard），
    // 露出的就是身體本身的皮膚——所以半閉的眼（生氣、難過、疑惑、想睡）也不會有一塊顏色對不上的眼皮圓片。切面＝通過球心、法線＝眼皮極點的平面，與原本殼的邊緣同一條線。
    const eyeMat = new THREE.MeshStandardMaterial({ map: IRIS, roughness: 0.3, metalness: 0, envMapIntensity: 0.15 });
    const clip = { uPole: { value: new V3(0, 1, 0) }, uOn: { value: 0 } };
    eyeMat.onBeforeCompile = (sh) => { sh.uniforms.uPole = clip.uPole; sh.uniforms.uOn = clip.uOn;
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vUnitP;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvUnitP = position;');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vUnitP; uniform vec3 uPole; uniform float uOn;').replace('#include <clipping_planes_fragment>', '#include <clipping_planes_fragment>\nif (uOn > 0.5 && dot(normalize(vUnitP), uPole) > 0.0) discard;'); };
    eyeMat.customProgramCacheKey = () => 'mochi-eyeclip1'; eyeMat.userData.clip = clip;
    const sph = new THREE.Mesh(geo, eyeMat); sph.scale.set(EYE.a, EYE.b, EYE.c); ball.add(sph);
    // 高光：兩個小圓合併成一個網格，固定在眼窩上（不隨眼球轉），頂點貼在橢球表面（強度改變時重算）
    const hlGeo = new THREE.BufferGeometry(), NSEG = this.hlSeg, hlDefs = [[-0.024, 0.038, 0.025, 1.0], [0.028, -0.043, 0.0107, 1.0]];
    hlGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(hlDefs.length * (NSEG + 1) * 3), 3));
    { const idx = []; hlDefs.forEach((_, k) => { const o = k * (NSEG + 1); for (let i = 0; i < NSEG; i++) idx.push(o, o + 1 + i, o + 1 + ((i + 1) % NSEG)); }); hlGeo.setIndex(idx); }
    const hlMat = new THREE.MeshBasicMaterial({ color: 0xfff4ec, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }), hlClip = { uPole: { value: new V3(0, 1, 0) }, uOn: { value: 0 } };   // 高光也要被眼皮切掉（否則會浮在皮膚上）
    hlMat.onBeforeCompile = (sh) => { sh.uniforms.uPole = hlClip.uPole; sh.uniforms.uOn = hlClip.uOn;
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vUnitP;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvUnitP = position / vec3(0.077, 0.104, 0.054);');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vUnitP; uniform vec3 uPole; uniform float uOn;').replace('#include <clipping_planes_fragment>', '#include <clipping_planes_fragment>\nif (uOn > 0.5 && dot(normalize(vUnitP), uPole) > 0.0) discard;'); };
    hlMat.customProgramCacheKey = () => 'mochi-hlclip1'; hlMat.userData.clip = hlClip;
    const hl = new THREE.Mesh(hlGeo, hlMat);
    hl.frustumCulled = false; hl.userData.defs = hlDefs; hl.userData.NSEG = NSEG; dep.add(hl);
    const setHl = (k) => { const P = hlGeo.attributes.position; hlDefs.forEach(([cx, cy, r, sy], d) => { const o = d * (NSEG + 1); const put = (n, x, y) => P.setXYZ(o + n, x, y, ellPoint(x, y, 1.0) + 0.0025); put(0, cx, cy); for (let i = 0; i < NSEG; i++) { const a = i / NSEG * Math.PI * 2; put(1 + i, cx + Math.cos(a) * r * k, cy + Math.sin(a) * r * k * sy); } }); P.needsUpdate = true; };
    setHl(1); hl.userData.setHl = setHl;
    // 眼皮殼：半球殼（極點方向決定蓋住多少）。外層群組負責橢球縮放，內層負責旋轉。
    const lidS = new THREE.Group(); lidS.scale.set(EYE.a * 1.07, EYE.b * 1.07, EYE.c * 1.12); dep.add(lidS);
    const lid = new THREE.Mesh(shared('lid', () => new THREE.SphereGeometry(1, 40, 16, 0, Math.PI * 2, 0, Math.PI / 2)), new THREE.MeshBasicMaterial({ visible: false })); lidS.add(lid);   // 眼皮殼本身不畫（只當睫毛線的座標系）
    // 笑眼 ∩、睡眼 ∪ 的弧線（畫在眼皮殼上）
    const arc = (sgn) => { const key = 'arc' + sgn; const pts = []; const w = 0.074, h = 0.068 * sgn; for (let i = 0; i <= 18; i++) { const u = i / 18 * 2 - 1, x = u * w, t = (u + 1) / 2, y = h * (-0.42 * ((1 - t) ** 2 + t * t) + 2.3 * t * (1 - t)); pts.push(new V3(x, y, skinZ(x, y))); }
      const m = new THREE.Mesh(shared(key, () => new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 22, 0.0075, 6)), (SHARED.arcMat ||= new THREE.MeshBasicMaterial({ color: 0x3a2622 }))); m.visible = false; grp.add(m); return m; };
    const arcUp = arc(1), arcDn = arc(-1);
    // 眼皮邊緣的睫毛線（半閉、生氣、疑惑時看得到眼皮的邊）＋全閉時的睫毛弧（比 ∪ 眼更淺、兩端微上揚，像眨眼的睫毛線）
    const rim = new THREE.Mesh(shared('rim', () => new THREE.TorusGeometry(1, 0.034, 6, 56).rotateX(Math.PI / 2)), (SHARED.arcMat ||= new THREE.MeshBasicMaterial({ color: 0x3a2622 }))); rim.visible = false; lid.add(rim);
    const lash = (() => { const pts = []; const w = 0.071; for (let i = 0; i <= 20; i++) { const u = i / 20 * 2 - 1, x = u * w, y = -0.008 * (1 - u * u) + 0.003 * u * u; pts.push(new V3(x, y, skinZ(x, y))); }
      const m = new THREE.Mesh(shared('lash', () => new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, 0.0062, 6)), SHARED.arcMat); m.visible = false; grp.add(m); return m; })();
    return { side, eyeMat, hlMat, grp, dep, ball, lid, hl, arcUp, arcDn, rim, lash, q, n, hlK: 1 };
  }
  dispose() { for (const e of this.eyes) { e.eyeMat.dispose(); e.hlMat.dispose(); e.lid.material.dispose(); } }
  // ── 臉貼片（Canvas 貼圖）
  initDecal(W) {
    const d = this.meta.decal, H = Math.round(W * (d.z1 - d.z0) / (2 * d.x)); this.W = W; this.H = H; this.K = W / (2 * d.x);
    const cv = this.cv = document.createElement('canvas'); cv.width = W; cv.height = H; this.g = cv.getContext('2d');
    const t = this.tex = new THREE.CanvasTexture(cv); t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter;
    this.decal.material = new THREE.MeshStandardMaterial({ map: t, transparent: true, roughness: 0.9, metalness: 0, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 });
    this.decal.renderOrder = 2;
  }
  px(x, y) { const d = this.meta.decal; return [(x + d.x) / (2 * d.x) * this.W, (d.z1 - y) / (d.z1 - d.z0) * this.H]; }
  paint() {
    const g = this.g, c = this.cur, K = this.K, A = this.meta.anchors, W = this.W, H = this.H, col = '#3a2622';
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, H);
    // 腮紅
    for (const sd of ['L', 'R']) {
      const a = A['cheek.' + sd].p, [x, y] = this.px(a[0], a[1]); const rw = 0.0725 * K * (1 + c.cheek * 0.25), rh = 0.042 * K * (1 + c.cheek * 0.3);
      const al = Math.min(0.9, 0.62 * c.blush); if (al < 0.02) continue;
      g.save(); g.translate(x, y); g.scale(1, rh / rw); const gr = g.createRadialGradient(0, 0, 0, 0, 0, rw);
      gr.addColorStop(0, `rgba(255,128,140,${al})`); gr.addColorStop(0.55, `rgba(255,128,140,${al * 0.55})`); gr.addColorStop(1, 'rgba(255,128,140,0)'); g.fillStyle = gr; g.beginPath(); g.arc(0, 0, rw, 0, 7); g.fill(); g.restore();
      if (c.hatch > 0.05) { g.save(); g.globalAlpha = Math.min(1, c.hatch) * 0.7; g.strokeStyle = 'rgb(255,128,140)'; g.lineWidth = 0.0032 * K; g.lineCap = 'round'; for (let i = -1; i <= 1; i++) { g.beginPath(); g.moveTo(x + i * 0.011 * K + 0.003 * K, y - 0.007 * K); g.lineTo(x + i * 0.011 * K - 0.003 * K, y + 0.007 * K); g.stroke(); } g.restore(); }
    }
    // 眉
    if (c.brow > 0.04) for (const sd of [-1, 1]) {
      const a = A[sd > 0 ? 'brow.L' : 'brow.R'].p, [x, y] = this.px(a[0], a[1]);
      const asy = c.asym ? (sd > 0 ? 1.0 : -0.75) : 0;   // 疑惑：一側上揚、一側壓低
      g.save(); g.globalAlpha = Math.min(1, c.brow); g.strokeStyle = col; g.lineWidth = 0.0114 * K; g.lineCap = 'round';
      g.translate(x, y - c.browY * 0.0011 * K - asy * 0.011 * K + c.lidT * 0.01 * K); g.rotate(-c.browA * 0.36 * sd * (c.asym ? (sd > 0 ? 0.4 : -1.3) : 1));
      g.beginPath(); g.moveTo(-0.041 * K, 0); g.quadraticCurveTo(0, -0.0045 * K, 0.041 * K, 0); g.stroke(); g.restore();
    }
    // 鼻：舊版糰糰沒有鼻子（face.js 的 s.nose 未開），這裡也不畫
    // 眼淚
    if (c.tear > 0.04) for (const sd of ['L', 'R']) {
      const a = A['eye.' + sd].p, s = sd === 'L' ? 1 : -1, [x, y] = this.px(a[0] + s * 0.03, a[1] - 0.112 - Math.sin(this.time * 3 + s) * 0.002), k = (0.0085 + c.tear * 0.003) * K;
      g.save(); g.globalAlpha = Math.min(1, c.tear) * 0.92; g.translate(x, y); g.beginPath(); g.moveTo(0, -k * 1.3); g.bezierCurveTo(k, -k * 0.1, k * 0.85, k, 0, k); g.bezierCurveTo(-k * 0.85, k, -k, -k * 0.1, 0, -k * 1.3);
      g.fillStyle = '#9fd8ff'; g.fill(); g.globalAlpha *= 0.8; g.fillStyle = '#fff'; g.beginPath(); g.arc(-k * 0.28, k * 0.1, k * 0.24, 0, 7); g.fill(); g.restore();
    }
    // 嘴
    { const a = A.mouth.p, [mx0, my] = this.px(a[0], a[1]); const mo = Math.max(0, c.mOpen + this.talk), w = 0.0325 * K * c.mW * (1 - 0.35 * Math.min(1, c.mRound) * Math.min(1, mo * 2)), mx = mx0 + c.smirk * 0.007 * K;
      g.save(); g.translate(mx, my); g.rotate(-c.smirk * 0.2); g.strokeStyle = col; g.lineCap = 'round'; g.lineJoin = 'round'; g.lineWidth = 0.0114 * K;
      if (mo > 0.06) {
        const Hh = mo * 0.0425 * K, cc = (c.mCurve + 1) / 2, r = Math.min(1, c.mRound), tY = -Hh * ((1 - cc) * (1 - r) + 0.5 * r), bY = Hh * (cc * (1 - r) + 0.5 * r);
        g.beginPath(); g.moveTo(-w, 0); g.bezierCurveTo(-w, tY * 1.33, w, tY * 1.33, w, 0); g.bezierCurveTo(w, bY * 1.33, -w, bY * 1.33, -w, 0); g.closePath();
        g.fillStyle = '#8a3344'; g.fill(); if (r < 0.5) { g.save(); g.clip(); g.fillStyle = '#ff8fa0'; g.beginPath(); g.ellipse(0, bY + Hh * 0.3, w * 0.62, Hh * 0.62, 0, 0, 7); g.fill(); g.restore(); } g.lineWidth = 0.0092 * K; g.stroke();
      } else {
        const dd = c.mCurve * w * 0.75; g.beginPath();
        if (c.mCurve > 0 && c.smirk < 0.3) { const k = Math.min(1, c.mCurve * 1.6); g.moveTo(-w, -dd * 0.2); g.quadraticCurveTo(-w * 0.5, dd * (0.55 + 0.5 * k), 0, -dd * 0.1 * k); g.quadraticCurveTo(w * 0.5, dd * (0.55 + 0.5 * k), w, -dd * 0.2); }
        else { g.moveTo(-w, -dd * 0.3); g.quadraticCurveTo(0, dd * 1.25, w, -dd * 0.3 - c.smirk * 0.004 * K); }
        g.stroke();
      }
      g.restore(); }
    this.tex.needsUpdate = true;
  }
  // ── 對外
  set(name) { this.target = FACE_EXPR[name] || FACE_EXPR.neutral; this.name = name; this.dirty = true; }
  snap() { for (const k of KEYS) this.cur[k] = this.target[k]; this.blink = 0; this.blinkV = 0; this.dirty = true; this.gaze.yaw = this.gaze.ty; this.gaze.pitch = this.gaze.tp; this.sac.x = this.sac.y = 0; this.sac.t = 99; }
  blinkNow() { if (this.blinkV === 0) this.blinkV = 1; }
  /** 視線目標（弧度）：yaw 左右（+ 往角色的左＝模型 +X）、pitch 上下（+ 往上）。 */
  lookAt(yaw, pitch) { this.gaze.ty = yaw; this.gaze.tp = pitch; }
  setMorphScale(sx, sy, sz) { this.morphScale.set(sx, sy, sz); }
  /** frozen＝靜止模式：表情與視線目標仍會平滑過去（按鈕要有反應），但眨眼排程、微跳視、時間都停住 */
  update(dt, speed = 12, frozen = false) {
    if (!frozen) this.time += dt; const k = 1 - Math.exp(-dt * speed), c = this.cur, t = this.target;
    for (const key of KEYS) c[key] += (t[key] - c[key]) * k;
    if (!frozen) this.blinkT -= dt;
    if (!frozen && this.autoBlink && this.blinkT <= 0) { this.blinkV = 1; this.blinkT = Math.random() < 0.2 ? 0.28 : 1.8 + Math.random() * 3.6; }
    if (frozen) { /* 眨眼進行到一半就停在原處 */ }
    else if (this.blinkV > 0) { this.blink += dt / 0.055; if (this.blink >= 1) { this.blink = 1; this.blinkV = -1; } }
    else if (this.blinkV < 0) { this.blink -= dt / 0.09; if (this.blink <= 0) { this.blink = 0; this.blinkV = 0; } }
    // 視線：平滑追上目標；微跳視
    const g = this.gaze, kg = 1 - Math.exp(-dt * 14); g.yaw += (g.ty - g.yaw) * kg; g.pitch += (g.tp - g.pitch) * kg;
    if (!frozen) this.sac.t -= dt; if (!frozen && this.sac.t <= 0) { this.sac.t = 0.8 + Math.random() * 1.7; this.sac.x = (Math.random() - 0.5) * 0.09; this.sac.y = (Math.random() - 0.5) * 0.06; }
    this.applyEyes(dt);
    const sig = KEYS.map(q => Math.round(c[q] * 40)).join() + '|' + Math.round(this.talk * 24) + '|' + (c.tear > 0.04 ? Math.round(this.time * 8) : 0);
    if (this.dirty || sig !== this._sig) { this._sig = sig; this.dirty = false; this.paint(); }
  }
  applyEyes(dt) {
    const c = this.cur, g = this.gaze, ms = this.morphScale, cz = -this.meta.bodyCy;
    const gy = clamp(g.yaw + this.sac.x * 0.5, -0.34, 0.34), gp = clamp(g.pitch + this.sac.y * 0.5, -0.22, 0.22);
    for (const e of this.eyes) {
      const s = e.side, asy = c.asym ? (s > 0 ? 1.0 : 0.72) : 1;
      let open = clamp(c.open * (1 - this.blink) * asy, 0, 1); const cover = clamp(c.lidT * 1.5 + c.lidB * 0.4, 0, 0.9); open = clamp(open * (1 - cover), 0, 1);
      const beta = (8 + 134 * Math.pow(open, 0.85)) * D2R, roll = c.lidA * 0.5 * (s > 0 ? 1 : -1) *   /* 第四階段修正：原本符號相反，生氣的眼皮斜成難過、難過斜成生氣。s>0 是角色的左眼＝畫面右側，生氣要「內側低」 */  (c.lidT > 0.02 ? 1 : 0) * Math.min(1, c.lidT * 5);
      const pole = new V3(0, Math.sin(beta), Math.cos(beta)).applyAxisAngle(new V3(0, 0, 1), roll);
      e.lid.quaternion.setFromUnitVectors(new V3(0, 1, 0), pole);
      e.lid.visible = open < 0.97; e.rim.visible = open > 0.06 && open < 0.95;
      { const t = clamp((open - 0.03) / 0.20, 0, 1), zk = t * t * (3 - 2 * t); e.dep.scale.z = Math.max(zk, 1e-3); e.dep.visible = zk > 0.004; }   // 閉眼：壓平埋進身體；睜眼（open≥0.23）時 zk＝1，與舊版一模一樣
      { e.ball.rotation.set(-gp, gy * (1), 0, 'YXZ'); const k = e.eyeMat.userData.clip; k.uOn.value = e.lid.visible ? 1 : 0; k.uPole.value.copy(pole).applyQuaternion(e.ball.quaternion.clone().invert()); const h = e.hlMat.userData.clip; h.uOn.value = k.uOn.value; h.uPole.value.copy(pole); }   // 被眼皮蓋住的半球（極點方向）在眼球座標系的樣子
      // 視線：眼球轉（瞳孔在動）。眼睛朝向角色的左為 +yaw（繞局部 Y 轉）
      e.ball.rotation.set(-gp, gy * (1), 0, 'YXZ');
      const es = clamp(this.eyeScale * c.eyeS * (c.asym ? (s > 0 ? 1.0 : 0.88) : 1), 0.5, 1.4);
      e.grp.scale.setScalar(es);
      // 高光強度
      if (Math.abs(e.hlK - c.hl) > 0.01) { e.hlK = c.hl; e.hl.userData.setHl(c.hl); }
      // 笑眼／睡眼弧
      const closed = clamp(1 - open / 0.35, 0, 1), up = clamp(c.arc, 0, 1) * closed, dn = clamp(-c.arc, 0, 1) * closed;
      e.arcUp.visible = up > 0.05; e.arcUp.scale.set(0.6 + 0.4 * up, 0.6 + 0.4 * up, 1); e.arcDn.visible = dn > 0.05; e.arcDn.scale.set(0.6 + 0.4 * dn, 0.6 + 0.4 * dn, 1);
      e.lash.visible = open < 0.12 && !e.arcUp.visible && !e.arcDn.visible;
      // 形態鍵造成的身體變形：位置跟著走（只位移，不縮放）
      const b = e.grp.userData.base, ms2 = ms; e.grp.position.set(b.x * ms2.x, b.y * ms2.y, cz + (b.z - cz) * ms2.z);
    }
  }
}
