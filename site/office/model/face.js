// 臉：立體眼球（嵌在眼窩位置的球面，虹膜與高光在球面上算，眼皮開合用裁切）＋ Canvas 貼圖（眉毛、腮紅、嘴、閉眼線）
// 表情是一組參數，切換時逐格內插，眉、眼皮、嘴一起連動。位置用模型座標：
// meta.face = { eyeL:[x,y], eyeR:[x,y], r: 眼睛半寬, mouth:[x,y], brow: 眉毛高出眼睛中心多少 }
import * as THREE from '../vendor/three.module.min.js';

export const EXPRESSIONS = { neutral: '微笑', happy: '開口笑', talk: '講話', surprised: '驚訝', angry: '生氣', sad: '難過', smug: '得意', focus: '專注', dizzy: '暈眩' };
const BASE = { top: 0.84, bot: -1, tilt: 0, arcB: 0, iris: 1, lookX: 0, lookY: 0, browY: 0, browTilt: 0, browArc: 0.5, browAsym: 0, mCurve: 0.55, mOpen: 0, mW: 1, mAsym: 0, blush: 0.55, cross: 0, puff: 0, arcUp: 0 };
const EXPR = {
  neutral: {},
  talk: { mOpen: 0.55, mCurve: 0.45, mW: 0.9, browY: 0.2 },
  happy: { top: -1, arcUp: 1, browY: 0.45, browArc: 0.8, mCurve: 1, mOpen: 0.75, mW: 1.25, blush: 0.8 },
  surprised: { top: 1.05, iris: 0.8, browY: 1, browArc: 0.9, mCurve: 0, mOpen: 0.7, mW: 0.55, blush: 0.4 },
  angry: { top: 0.6, tilt: 0.42, bot: -0.9, browY: -0.55, browTilt: 0.5, browArc: 0.15, mCurve: -0.55, mW: 0.75, blush: 0.75, puff: 1 },
  sad: { top: 0.66, tilt: -0.3, bot: -0.92, lookY: -0.25, browY: 0.25, browTilt: -0.55, browArc: 0.3, mCurve: -0.6, mW: 0.7, blush: 0.35 },
  smug: { top: 0.5, bot: -0.8, arcB: 0.2, tilt: 0.08, lookX: 0.45, browY: 0.35, browAsym: 0.6, browArc: 0.6, mCurve: 0.7, mAsym: 0.75, mW: 0.95, blush: 0.6 },
  focus: { top: 0.7, tilt: 0.14, lookY: -0.35, browY: -0.25, browTilt: 0.15, mCurve: 0.05, mW: 0.6, blush: 0.4 },
  dizzy: { top: -1, cross: 1, browY: 0.3, browTilt: -0.3, mCurve: -0.2, mOpen: 0.25, mW: 0.7, blush: 0.3 },
};
const EYE_VS = `varying vec3 vP; void main(){ vP=position; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`;
const EYE_FS = `varying vec3 vP;
uniform float uRx,uRy,uTop,uBot,uTilt,uArcB,uIris,uPupil,uSide; uniform vec2 uLook; uniform vec3 uIrisIn,uIrisOut,uLash,uSkinSh;
void main(){
  if(vP.z<0.0) discard;
  vec2 e=vec2(vP.x/uRx,vP.y/uRy); float el=dot(e,e); if(el>1.0) discard;
  float top=uTop+uTilt*e.x*uSide, bot=uBot+uArcB*(1.0-e.x*e.x);
  if(e.y>top||e.y<bot) discard;
  float er=sqrt(el); vec3 n=normalize(vP); vec3 g=normalize(vec3(uLook,1.0));
  float t=acos(clamp(dot(n,g),-1.0,1.0))/uIris; vec2 ic=(n.xy-g.xy)/sin(uIris);
  vec3 scl=vec3(0.99,0.98,0.975)*mix(vec3(1.0),vec3(0.93,0.90,0.90),smoothstep(0.55,1.0,er));
  vec3 col=mix(uIrisIn,uIrisOut,smoothstep(0.25,1.0,t));
  col+=vec3(0.26,0.14,0.05)*smoothstep(0.1,-0.95,ic.y)*smoothstep(1.0,0.5,t);      // 虹膜下緣的透光亮弧
  col=mix(col,vec3(0.05,0.025,0.02),smoothstep(uPupil+0.07,uPupil-0.03,t));             // 瞳孔
  col*=1.0-0.6*smoothstep(0.76,1.0,t);                                                  // 虹膜外圈變深
  col=mix(col,scl,smoothstep(0.97,1.05,t));
  col*=1.0-0.42*smoothstep(0.8,0.0,top-e.y);                                            // 上眼皮投在眼球上的陰影
  float lash=max(smoothstep(0.26,0.09,top-e.y),smoothstep(0.84,0.96,er)*smoothstep(0.05,0.5,e.y));
  col=mix(col,uLash,lash*0.92);                                                         // 上眼線（深棕、柔邊，不是黑框）
  float low=max(smoothstep(0.86,1.0,er)*smoothstep(0.15,-0.4,e.y),smoothstep(0.12,0.0,e.y-bot)*step(-0.99,uBot));
  col=mix(col,uSkinSh,low*0.3);
  vec3 h1=normalize(g+vec3(-0.21,0.25,0.0)), h2=normalize(g+vec3(0.20,-0.24,0.0));
  float s1=smoothstep(cos(0.125),cos(0.085),dot(n,h1)), s2=smoothstep(cos(0.06),cos(0.035),dot(n,h2));
  col=mix(col,vec3(1.0),max(s1*(1.0-lash),s2*0.75));                                     // 高光
  gl_FragColor=vec4(pow(col,vec3(2.2)),1.0);
  #include <colorspace_fragment>
}`;

export class FaceRig {
  constructor(f) {
    this.f = Object.assign({ eyeL: [0.085, 1.56], eyeR: [-0.125, 1.56], r: 0.05, mouth: [-0.02, 1.455], brow: 0.07 }, f);
    const cx = (this.f.eyeL[0] + this.f.eyeR[0]) / 2, w = 0.62, h = 0.62, cy = this.f.eyeL[1] - 0.04;
    this.rect = { x: cx - w / 2, y: cy - h / 2, w, h };
    this.canvas = document.createElement('canvas'); this.canvas.width = this.canvas.height = 1024;
    this.ctx = this.canvas.getContext('2d'); this.key = '';
    this.p = { ...BASE }; this.eyes = []; this.skin = '#ffd6bd'; this.browCol = '#3a3040';
  }
  // 眼球掛在頭骨上：球心放在臉表面後方，只露出一小片球冠
  attach(headBone, headJoint, geom) {
    const f = this.f, pos = geom.attributes.position, Re = f.r * 1.6, prot = f.protrude != null ? f.protrude : 0.017;
    this.eyes = [[f.eyeL, 1], [f.eyeR, -1]].map(([e, side]) => {
      let z = -1e9; for (let i = 0; i < pos.count; i++) { const dx = pos.getX(i) - e[0], dy = pos.getY(i) - e[1]; if (dx * dx + dy * dy < f.r * f.r * 0.5 && pos.getZ(i) > z) z = pos.getZ(i); }
      const mat = new THREE.ShaderMaterial({ vertexShader: EYE_VS, fragmentShader: EYE_FS, uniforms: {
        uRx: { value: f.r * 1.02 }, uRy: { value: f.r * 1.08 }, uTop: { value: 0.9 }, uBot: { value: -1 }, uTilt: { value: 0 }, uArcB: { value: 0 }, uIris: { value: 0.5 }, uPupil: { value: 0.47 }, uSide: { value: side }, uLook: { value: new THREE.Vector2() },
        uIrisIn: { value: new THREE.Color(0.50, 0.27, 0.13) }, uIrisOut: { value: new THREE.Color(0.17, 0.08, 0.05) }, uLash: { value: new THREE.Color(0.2, 0.12, 0.11) }, uSkinSh: { value: new THREE.Color(0.86, 0.6, 0.5) } } });
      const m = new THREE.Mesh(new THREE.SphereGeometry(Re, 48, 32), mat); m.rotation.x = Math.PI / 2; // 極點朝前後，避免極點落在上方
      const holder = new THREE.Group(); holder.position.set(e[0] - headJoint.x, e[1] - headJoint.y, z + prot - Re - headJoint.z);
      // 球體自己不轉（裁切用球的本地座標）；把幾何轉回來
      m.rotation.x = 0; holder.add(m); headBone.add(holder); return { holder, mat, side };
    });
    this.irisBase = Math.asin(Math.min(0.95, f.r * 0.74 / Re));
    this.applyEyes(0);
  }
  detach() { for (const e of this.eyes) e.holder.parent && e.holder.parent.remove(e.holder); this.eyes = []; }
  setVisible(v) { for (const e of this.eyes) e.holder.visible = v; }
  applyEyes(blink) {
    const p = this.p;
    for (const e of this.eyes) { const u = e.mat.uniforms; const top = p.top + (p.bot - 0.05 - p.top) * blink;
      u.uTop.value = top; u.uBot.value = p.bot; u.uTilt.value = p.tilt; u.uArcB.value = p.arcB; u.uIris.value = this.irisBase * p.iris; u.uLook.value.set(p.lookX * 0.32, p.lookY * 0.25); }
  }
  px(p) { const r = this.rect, S = this.canvas.width; return [(p[0] - r.x) / r.w * S, (1 - (p[1] - r.y) / r.h) * S]; }
  // dt 內把目前參數往目標表情靠攏；回傳貼圖是否需要更新
  update(dt, { expr = 'neutral', blink = 0, mouth = 0, look = null } = {}) {
    const tg = { ...BASE, ...(EXPR[expr] || {}) }; if (mouth > 0) { tg.mOpen = Math.max(tg.mOpen * 0.4, mouth); }
    if (look) { tg.lookX += look[0]; tg.lookY += look[1]; }
    const k = Math.min(1, dt * 14); for (const key in tg) this.p[key] += (tg[key] - this.p[key]) * k;
    this.blink = blink; this.applyEyes(blink); return this.draw();
  }
  draw() {
    const p = this.p, closed = (p.top + (p.bot - 0.05 - p.top) * this.blink) - p.bot < 0.12;
    const key = ['browY', 'browTilt', 'browArc', 'browAsym', 'mCurve', 'mOpen', 'mW', 'mAsym', 'blush', 'cross', 'puff', 'top', 'tilt', 'arcUp'].map((k) => p[k].toFixed(2)).join('|') + closed;
    if (key === this.key) return false; this.key = key;
    const c = this.ctx, S = this.canvas.width, u = S / this.rect.w, f = this.f, R = f.r * u;
    c.clearRect(0, 0, S, S); c.lineCap = 'round'; c.lineJoin = 'round';
    const eyes = [[f.eyeL, 1], [f.eyeR, -1]];
    for (const [e, s] of eyes) {
      // 腮紅（柔和）
      { const [x, y] = this.px([e[0] + s * f.r * 0.62, e[1] - f.r * 1.55]); const rr = R * (1.3 + 0.25 * p.puff);
        const g = c.createRadialGradient(x, y, 0, x, y, rr); g.addColorStop(0, `rgba(255,105,105,${0.95 * p.blush})`); g.addColorStop(0.6, `rgba(255,105,105,${0.45 * p.blush})`); g.addColorStop(1, 'rgba(255,128,120,0)');
        c.fillStyle = g; c.beginPath(); c.ellipse(x, y, rr, rr * 0.72, 0, 0, 7); c.fill(); }
      // 眼窩的柔和陰影（讓眼睛像嵌在臉裡）
      { const [x, y] = this.px(e); const g = c.createRadialGradient(x, y - R * 0.15, R * 0.7, x, y - R * 0.15, R * 1.55); g.addColorStop(0, 'rgba(205,125,105,0.22)'); g.addColorStop(1, 'rgba(205,125,105,0)');
        c.fillStyle = g; c.beginPath(); c.ellipse(x, y - R * 0.15, R * 1.5, R * 1.6, 0, 0, 7); c.fill(); }
      const [x, y] = this.px(e);
      if (p.cross > 0.5) { c.save(); c.translate(x, y); c.strokeStyle = '#4a3232'; c.lineWidth = R * 0.2; c.shadowColor = '#4a3232'; c.shadowBlur = R * 0.06;
        c.beginPath(); c.moveTo(-R * 0.55, -R * 0.55); c.lineTo(R * 0.55, R * 0.55); c.moveTo(R * 0.55, -R * 0.55); c.lineTo(-R * 0.55, R * 0.55); c.stroke(); c.restore(); }
      else if (closed) { // 閉眼：上下眼皮合起來的弧線，加一點睫毛厚度
        c.save(); c.translate(x, y + R * 0.42); c.strokeStyle = '#3a2424'; c.lineWidth = R * 0.17; c.shadowColor = '#3a2424'; c.shadowBlur = R * 0.08;
        const up = p.arcUp > 0.5; c.beginPath();
        if (up) { c.translate(0, -R * 0.5); c.moveTo(-R * 0.88, R * 0.3); c.quadraticCurveTo(0, -R * 0.62, R * 0.88, R * 0.3); }
        else { c.moveTo(-R * 0.85, -R * 0.12); c.quadraticCurveTo(0, R * 0.34, R * 0.85, -R * 0.12); }
        c.stroke(); c.restore(); }
      // 眉毛：有厚度、內粗外細、柔邊
      { const by = f.brow + f.r * (0.22 * p.browY + (s > 0 ? 0.3 : -0.1) * p.browAsym); const [bx, byy] = this.px([e[0], e[1] + by]);
        c.save(); c.translate(bx, byy); c.rotate(s * p.browTilt * 0.55); c.scale(s, 1); // 之後 +x 是外側
        const a = R * 0.26 * p.browArc, L = R * 0.92, ti = R * 0.19, to = R * 0.085;
        c.fillStyle = this.browCol; c.shadowColor = this.browCol; c.shadowBlur = R * 0.09;
        c.beginPath(); c.moveTo(-L, R * 0.05 - ti); c.quadraticCurveTo(0, -a - ti * 1.1, L, R * 0.1 - to); c.quadraticCurveTo(L + to, R * 0.1, L, R * 0.1 + to);
        c.quadraticCurveTo(0, -a + ti * 0.9, -L, R * 0.05 + ti); c.quadraticCurveTo(-L - ti, R * 0.05, -L, R * 0.05 - ti); c.fill(); c.restore(); }
    }
    // 嘴
    { const [x, y] = this.px(f.mouth); c.save(); c.translate(x + p.mAsym * R * 0.12, y);
      const w = R * 0.6 * p.mW, lift = p.mCurve * R * 0.2, as = p.mAsym * R * 0.14, open = Math.max(0, p.mOpen);
      const Lc = [-w, -lift + as], Rc = [w, -lift - as], up = [0, lift * 0.55 - open * R * 0.06], lo = [0, lift * 0.75 + open * R * 0.95];
      if (open > 0.07) {
        const path = () => { c.beginPath(); c.moveTo(...Lc); c.quadraticCurveTo(up[0], up[1] * 2 - (Lc[1] + Rc[1]) / 2, ...Rc); c.quadraticCurveTo(w * 0.85, lo[1] * 0.9, 0, lo[1]); c.quadraticCurveTo(-w * 0.85, lo[1] * 0.9, ...Lc); c.closePath(); };
        path(); const g = c.createLinearGradient(0, up[1], 0, lo[1]); g.addColorStop(0, '#5a1c20'); g.addColorStop(1, '#8a3236'); c.fillStyle = g; c.shadowColor = 'rgba(150,70,60,0.5)'; c.shadowBlur = R * 0.08; c.fill(); c.shadowBlur = 0;
        c.save(); path(); c.clip();
        c.fillStyle = '#ff9a9a'; c.beginPath(); c.ellipse(0, lo[1] + R * 0.05, w * 0.62, Math.max(R * 0.08, (lo[1] - up[1]) * 0.42), 0, 0, 7); c.fill();      // 舌頭
        if (p.mCurve > 0.4 && open > 0.4) { c.fillStyle = '#fffaf4'; c.fillRect(-w, Math.min(Lc[1], Rc[1]) - R * 0.3, w * 2, R * 0.3 + R * 0.13); }        // 上排牙
        c.restore();
        path(); c.strokeStyle = 'rgba(150,62,52,0.9)'; c.lineWidth = R * 0.07; c.stroke();
      } else {
        c.strokeStyle = '#a8483c'; c.lineWidth = R * 0.105; c.shadowColor = 'rgba(168,72,60,0.6)'; c.shadowBlur = R * 0.06;
        c.beginPath(); c.moveTo(...Lc); c.quadraticCurveTo(0, lift * 1.5 + (Lc[1] + Rc[1]) / 2 + lift, ...Rc); c.stroke(); c.shadowBlur = 0;
        // 嘴角的小凹陷
        c.fillStyle = 'rgba(190,105,90,0.55)'; for (const q of [Lc, Rc]) { c.beginPath(); c.arc(q[0] + Math.sign(q[0]) * R * 0.05, q[1] - R * 0.01, R * 0.065, 0, 7); c.fill(); }
        // 下唇下方的淡影
        c.strokeStyle = 'rgba(215,140,120,0.35)'; c.lineWidth = R * 0.1; c.beginPath(); c.moveTo(-w * 0.4, lift * 0.9 + R * 0.24); c.quadraticCurveTo(0, lift * 0.9 + R * 0.3, w * 0.4, lift * 0.9 + R * 0.24); c.stroke();
      }
      c.restore(); }
    return true;
  }
}
