// 骨架角色：載入 glb（自動綁骨架的模型）、分區上色材質、正面投影、臉（貼圖＋立體眼球）、姿勢套用（含腿部反向運動學、手指）
import * as THREE from '../vendor/three.module.min.js';
import { GLTFLoader } from '../vendor/GLTFLoader.js';
import { FaceRig } from './face.js';

export const DEFAULT_PALETTE = { hair: '#2b3046', skin: '#ffd6bd', top: '#f58a34', pants: '#5a86c8', shoes: '#f6f3ee' };
const PART_KEYS = ['hair', 'skin', 'top', 'pants', 'shoes'];
const LIMBS = [
  ['upperArmL', 'foreArmL', 'handL', 'armL', 'foreL', 'handL', 'L'], ['upperArmR', 'foreArmR', 'handR', 'armR', 'foreR', 'handR', 'R'],
  ['thighL', 'shinL', 'footL', 'legL', 'shinL', 'footL', 'L'], ['thighR', 'shinR', 'footR', 'legR', 'shinR', 'footR', 'R'],
];
const _q = new THREE.Quaternion(), _v = new THREE.Vector3(), _e = new THREE.Euler();
const V3 = (a) => new THREE.Vector3(a[0], a[1], a[2]);

function makeMaterial(char) {
  const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.6, metalness: 0 });
  const U = char.uniforms;
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
attribute vec4 _parta; attribute vec4 _partb;
varying vec4 vPA; varying vec4 vPB; varying vec2 vPUv; varying vec2 vRestXY; varying float vRestZ;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
vPA=_parta; vPB=_partb; vPUv=uv; vRestXY=position.xy; vRestZ=position.z;`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec4 vPA; varying vec4 vPB; varying vec2 vPUv; varying vec2 vRestXY; varying float vRestZ;
uniform vec4 uBrow; uniform vec3 uBrowHair;
uniform vec3 uPal[5]; uniform sampler2D uRef; uniform sampler2D uFace; uniform vec4 uFaceRect; uniform vec3 uHairHi; uniform vec3 uUpView;
uniform float uProj; uniform float uFlat; uniform float uFaceOn; uniform vec3 uRim; uniform float uRimPow; uniform float uAO;
float gHair=0.0;`)
      .replace('#include <color_fragment>', `
{ // 分區色：每個部位一個平滑的隸屬度，逐像素取最大 → 交界是平滑曲線而不是沿著三角形邊
  float p[5]; p[0]=vPA.x; p[1]=vPA.y; p[2]=vPA.z; p[3]=vPA.w; p[4]=vPB.x;
  vec3 acc=vec3(0.0); float wsum=0.0; float wh=0.0;
  for(int i=0;i<5;i++){ float o=0.0; for(int j=0;j<5;j++){ if(j!=i) o=max(o,p[j]); }
    float d=p[i]-o; float w=clamp(d/(fwidth(d)*1.5+1e-5)+0.5,0.0,1.0); acc+=uPal[i]*w; wsum+=w; if(i==0) wh=w; }
  vec3 base=acc/max(wsum,1e-4); gHair=wh/max(wsum,1e-4);
  if(uFlat>0.5){ base=vec3(0.87,0.84,0.80); gHair=0.0; }
  vec3 ref=texture2D(uRef,vPUv).rgb;
  base=mix(base,ref,uProj*smoothstep(0.35,0.75,vPB.y));
  vec2 fuv=(vRestXY-uFaceRect.xy)/uFaceRect.zw; fuv.y=1.0-fuv.y;
  if(fuv.x>0.0&&fuv.x<1.0&&fuv.y>0.0&&fuv.y<1.0){ vec4 d=texture2D(uFace,fuv); float fm=uFaceOn*smoothstep(0.25,0.6,vPB.z); base=base*(1.0-d.a*fm)+d.rgb*fm;
    // 眉毛透過瀏海顯示（卡通常見畫法）：瀏海蓋到眉毛的地方，用比頭髮亮的顏色把眉毛畫在頭髮上，兩邊眉毛都看得到
    float bw=uFaceOn*uBrow.w*gHair*step(uBrow.z,vRestZ)*smoothstep(uBrow.x-0.008,uBrow.x+0.004,vRestXY.y)*smoothstep(uBrow.y+0.008,uBrow.y-0.004,vRestXY.y)*smoothstep(0.45,0.8,d.a);
    base=mix(base,uBrowHair,bw*0.92); }
  // 凹處陰影（烘在頂點裡）：暗部偏暖，衣服皺摺與髮束才有層次
  float ao=mix(1.0,vPB.w,uAO*(1.0-0.45*vPA.y)); base*=mix(vec3(0.55,0.42,0.48),vec3(1.0),ao);
  diffuseColor.rgb*=base;
}`)
      .replace('#include <opaque_fragment>', `
{ float fr=pow(1.0-saturate(dot(normal,geometryViewDir)),uRimPow); outgoingLight+=uRim*fr*(0.55+0.45*normal.y);
  if(gHair>0.01){ // 頭髮光澤：沿髮流方向的各向異性高光（Kajiya-Kay），加一點頂部的亮面
    vec3 T=normalize(cross(normal,cross(uUpView,normal))+normal*(vPB.w-0.75)*0.6);
    vec3 Lh=normalize(vec3(0.25,0.75,0.6)); vec3 Hh=normalize(Lh+geometryViewDir); float th=dot(T,Hh);
    float sp=pow(sqrt(max(0.0,1.0-th*th)),70.0)*smoothstep(-0.2,0.5,dot(normal,Lh));
    float sp2=pow(sqrt(max(0.0,1.0-th*th)),12.0)*smoothstep(0.0,0.9,dot(normal,Lh));
    outgoingLight+=gHair*(uHairHi*sp*0.55+uHairHi*sp2*0.10); }
}
#include <opaque_fragment>`);
  };
  return mat;
}

export class Char {
  constructor() {
    this.root = new THREE.Group();
    this.bones = {}; this.rest = {}; this.restDir = {};
    this.uniforms = {
      uPal: { value: PART_KEYS.map((k) => new THREE.Color(DEFAULT_PALETTE[k])) },
      uRef: { value: null }, uFace: { value: null }, uFaceRect: { value: new THREE.Vector4(0, 0, 1, 1) },
      uProj: { value: 0 }, uFlat: { value: 0 }, uFaceOn: { value: 1 }, uAO: { value: 1 },
      uHairHi: { value: new THREE.Color('#aab4e6') }, uUpView: { value: new THREE.Vector3(0, 1, 0) },
      uBrow: { value: new THREE.Vector4(0, 0, 0, 0) }, uBrowHair: { value: new THREE.Color('#8d90b4') },
      uRim: { value: new THREE.Color(0.5, 0.4, 0.34) }, uRimPow: { value: 2.6 },
    };
    this.from = null; this.blend = 1; this.blendDur = 0.35;
    this.cur = {};
  }
  async load(base, name, lod = 'hi') {
    this.base = base; this.name = name;
    if (!this.meta) this.meta = await (await fetch(`${base}${name}.meta.json`)).json();
    const gltf = await new GLTFLoader().loadAsync(`${base}${name}_${lod}.glb`);
    if (this.face) this.face.detach();
    if (this.model) this.root.remove(this.model);
    this.model = gltf.scene; this.root.add(this.model);
    this.bones = {};
    this.model.traverse((o) => {
      if (o.isBone) { this.bones[o.name] = o; this.rest[o.name] = o.position.clone(); }
      if (o.isSkinnedMesh) { this.mesh = o; o.frustumCulled = false; }
    });
    this.material = makeMaterial(this); this.mesh.material = this.material;
    const J = this.meta.joints; this.J = {}; for (const k in J) this.J[k] = V3(J[k]);
    for (const [u, f, h] of LIMBS) {
      this.restDir[u] = V3(J[f]).sub(V3(J[u])).normalize();
      this.restDir[f] = V3(J[h]).sub(V3(J[f])).normalize();
      this.restDir[h] = V3(J[h + '_end']).sub(V3(J[h])).normalize();
    }
    this.legLen = { a: this.J.shinL.distanceTo(this.J.thighL), b: this.J.footL.distanceTo(this.J.shinL) };
    this.fingers = (this.meta.fingers || []).map((f) => ({ ...f, ax: V3(f.axis) }));
    if (!this.face) {
      this.face = new FaceRig(this.meta.face || {});
      const tex = new THREE.CanvasTexture(this.face.canvas); tex.colorSpace = THREE.SRGBColorSpace; tex.flipY = false; tex.premultiplyAlpha = true;
      tex.anisotropy = 4; this.faceTex = tex; this.uniforms.uFace.value = tex;
      const r = this.face.rect; this.uniforms.uFaceRect.value.set(r.x, r.y, r.w, r.h);
      const ref = await new THREE.TextureLoader().loadAsync(`${base}${name}_ref.png`);
      ref.colorSpace = THREE.SRGBColorSpace; ref.flipY = false; this.uniforms.uRef.value = ref;
    }
    this.face.attach(this.bones.head, this.J.head, this.mesh.geometry);
    { const f = this.face.f, by = f.eyeL[1] + f.brow; this.uniforms.uBrow.value.set(by - 0.032, by + 0.05, this.face.surfZ - 0.2, 1); }
    this.count = { verts: this.mesh.geometry.attributes.position.count, tris: this.mesh.geometry.index.count / 3, bones: Object.keys(this.bones).length };
    return this;
  }
  setPalette(p) { PART_KEYS.forEach((k, i) => { if (p[k]) this.uniforms.uPal.value[i].set(p[k]); }); }
  setMode(m) { this.mode = m; this.uniforms.uProj.value = m === 'proj' ? 1 : 0; this.uniforms.uFlat.value = m === 'clay' ? 1 : 0; this.uniforms.uFaceOn.value = m === 'clay' ? 0 : 1; this.face.setVisible(m !== 'clay'); }
  updateFace(dt, target, camera) { if (camera) this.uniforms.uUpView.value.set(0, 1, 0).transformDirection(camera.matrixWorldInverse); if (this.face.update(dt, target)) this.faceTex.needsUpdate = true; }

  // 把姿勢描述轉成每根骨頭的本地四元數與髖位移
  solve(pose, w = 1) {
    const out = { q: {}, pos: new THREE.Vector3() };
    const eul = (a) => (a ? new THREE.Quaternion().setFromEuler(_e.set(a[0] || 0, a[1] || 0, a[2] || 0, 'YXZ')) : new THREE.Quaternion());
    const r = pose.root || {};
    out.pos.set(r.x || 0, r.y || 0, r.z || 0);
    out.q.hips = eul([r.rx || 0, r.ry || 0, r.rz || 0]).multiply(eul(pose.hips));
    // 過渡中而且腿是鎖地的：髖先內插好再解腿，腳才不會在過渡時滑動
    out.pre = {};
    if (w < 1 && this.from && this.from.q.hips && (pose.ikL || pose.ikR)) { out.q.hips = this.from.q.hips.clone().slerp(out.q.hips, w); out.pos = this.from.pos.clone().lerp(out.pos, w); out.pre.hips = out.pre.pos = true; }
    for (const b of ['spine', 'chest', 'neck', 'head', 'shoulderL', 'shoulderR']) out.q[b] = eul(pose[b]);
    for (const [u, f, h, ku, kf, kh, sd] of LIMBS) {
      const ik = u.startsWith('thigh') && pose['ik' + sd];
      let qu, qf = new THREE.Quaternion(), qh = new THREE.Quaternion();
      if (ik) { // 雙骨反向運動學：腳踝目標（角色座標）→ 大腿、小腿方向；腳掌朝向另外給
        const qH = out.q.hips, inv = qH.clone().invert();
        const hip = this.J.hips.clone().add(out.pos).add(this.J[u].clone().sub(this.J.hips).applyQuaternion(qH));
        const tv = new THREE.Vector3(...ik.ankle).sub(hip).applyQuaternion(inv);
        const { a, b } = this.legLen; let d = tv.length(); const dmax = (a + b) * 0.999; out['reach' + sd] = d / (a + b);
        if (d > dmax) { tv.multiplyScalar(dmax / d); d = dmax; }
        const ax = tv.clone().normalize();
        const pole = new THREE.Vector3(...(ik.pole || [0, 0, 1])).applyQuaternion(inv); pole.addScaledVector(ax, -pole.dot(ax)).normalize();
        const x = (a * a - b * b + d * d) / (2 * d), hgt = Math.sqrt(Math.max(0, a * a - x * x));
        const knee = ax.clone().multiplyScalar(x).addScaledVector(pole, hgt);
        qu = new THREE.Quaternion().setFromUnitVectors(this.restDir[u], knee.clone().normalize());
        const sd2 = tv.clone().sub(knee).normalize().applyQuaternion(_q.copy(qu).invert());
        qf.setFromUnitVectors(this.restDir[f], sd2);
        qh.copy(_q.copy(qH).multiply(qu).multiply(qf).invert()).multiply(ik.q || new THREE.Quaternion()); out.pre[u] = out.pre[f] = out.pre[h] = true;
      } else {
        const du = pose[ku] ? _v.set(...pose[ku].dir).normalize() : this.restDir[u];
        qu = new THREE.Quaternion().setFromUnitVectors(this.restDir[u], du);
        if (pose[ku] && pose[ku].twist) qu.multiply(_q.setFromAxisAngle(this.restDir[u], pose[ku].twist));
        // 下段：在上段的本地座標裡做最小轉動（純彎曲，不帶扭轉）
        if (pose[kf]) {
          const d = new THREE.Vector3(...pose[kf].dir).normalize().applyQuaternion(_q.copy(qu).invert());
          qf.setFromUnitVectors(this.restDir[f], d);
          if (pose[kf].twist) qf.multiply(_q.setFromAxisAngle(this.restDir[f], pose[kf].twist));
        }
        const ph = pose[kh + '_'];
        if (ph && ph.dir) { // 指定末端方向（身體座標）
          const d = new THREE.Vector3(...ph.dir).normalize().applyQuaternion(_q.copy(qu).multiply(qf).invert());
          qh.setFromUnitVectors(this.restDir[h], d);
        } else if (ph && ph.world) { // 末端維持身體座標下的固定朝向（腳掌貼地用）
          qh.copy(_q.copy(qu).multiply(qf).invert()).multiply(eul(ph.world));
        } else if (ph && ph.rot) qh.copy(eul(ph.rot));
      }
      out.q[u] = qu; out.q[f] = qf; out.q[h] = qh;
    }
    // 手指：curl 0 張開、1 握緊；可分別指定拇指、食指、其餘三指
    for (const fg of this.fingers) {
      const c = pose['fingers' + fg.side]; let v = 0.12;
      if (typeof c === 'number') v = c; else if (c) v = c[fg.kind] != null ? c[fg.kind] : (c.all != null ? c.all : 0.12);
      if (fg.kind === 'thumb') out.q[fg.bones[0]] = new THREE.Quaternion().setFromAxisAngle(fg.ax, v * 1.0);
      else { out.q[fg.bones[0]] = new THREE.Quaternion().setFromAxisAngle(fg.ax, v * 1.25); out.q[fg.bones[1]] = new THREE.Quaternion().setFromAxisAngle(fg.ax, v * 1.35); }
    }
    return out;
  }
  // 換動作時記下目前姿勢，之後用球面內插過渡
  beginBlend(dur = 0.35) {
    this.from = { q: {}, pos: this.cur.pos ? this.cur.pos.clone() : new THREE.Vector3() };
    for (const k in this.cur.q || {}) this.from.q[k] = this.cur.q[k].clone();
    this.blend = this.cur.q ? 0 : 1; this.blendDur = dur;
  }
  apply(pose, dt = 0) {
    let w = 1;
    if (this.blend < 1 && this.from) { this.blend = Math.min(1, this.blend + dt / this.blendDur); w = this.blend * this.blend * (3 - 2 * this.blend); }
    const s = this.solve(pose, w);
    if (w < 1) {
      for (const k in s.q) if (this.from.q[k] && !s.pre[k]) s.q[k] = this.from.q[k].clone().slerp(s.q[k], w);
      if (!s.pre.pos) s.pos = this.from.pos.clone().lerp(s.pos, w);
    }
    this.cur = s;
    for (const k in s.q) if (this.bones[k]) this.bones[k].quaternion.copy(s.q[k]);
    this.bones.hips.position.copy(this.rest.hips).add(s.pos);
  }
}
