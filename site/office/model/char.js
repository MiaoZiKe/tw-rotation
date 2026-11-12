// 骨架角色：載入 glb（自動綁骨架的模型）、分區上色材質、正面投影、臉部貼圖、姿勢套用
import * as THREE from '../vendor/three.module.min.js';
import { GLTFLoader } from '../vendor/GLTFLoader.js';
import { FaceDecal } from './face.js';

export const DEFAULT_PALETTE = { hair: '#262b3d', skin: '#ffd6bd', top: '#f58a34', pants: '#5a86c8', shoes: '#f6f3ee' };
const PART_KEYS = ['hair', 'skin', 'top', 'pants', 'shoes'];
const LIMBS = [
  ['upperArmL', 'foreArmL', 'handL', 'armL', 'foreL', 'handL'], ['upperArmR', 'foreArmR', 'handR', 'armR', 'foreR', 'handR'],
  ['thighL', 'shinL', 'footL', 'legL', 'shinL', 'footL'], ['thighR', 'shinR', 'footR', 'legR', 'shinR', 'footR'],
];
const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _v = new THREE.Vector3(), _e = new THREE.Euler();
const V3 = (a) => new THREE.Vector3(a[0], a[1], a[2]);

function makeMaterial(char) {
  const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.62, metalness: 0 });
  const U = char.uniforms;
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
attribute vec4 _parta; attribute vec4 _partb;
varying vec4 vPA; varying vec4 vPB; varying vec2 vPUv; varying vec2 vRestXY;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
vPA=_parta; vPB=_partb; vPUv=uv; vRestXY=position.xy;`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec4 vPA; varying vec4 vPB; varying vec2 vPUv; varying vec2 vRestXY;
uniform vec3 uPal[5]; uniform sampler2D uRef; uniform sampler2D uFace; uniform vec4 uFaceRect;
uniform float uProj; uniform float uFlat; uniform float uFaceOn; uniform vec3 uRim; uniform float uRimPow;`)
      .replace('#include <color_fragment>', `
{ // 分區色：每個部位一個平滑的隸屬度，逐像素取最大 → 交界是平滑曲線而不是沿著三角形邊
  float p[5]; p[0]=vPA.x; p[1]=vPA.y; p[2]=vPA.z; p[3]=vPA.w; p[4]=vPB.x;
  vec3 acc=vec3(0.0); float wsum=0.0;
  for(int i=0;i<5;i++){ float o=0.0; for(int j=0;j<5;j++){ if(j!=i) o=max(o,p[j]); }
    float d=p[i]-o; float w=clamp(d/(fwidth(d)*1.5+1e-5)+0.5,0.0,1.0); acc+=uPal[i]*w; wsum+=w; }
  vec3 base=acc/max(wsum,1e-4);
  if(uFlat>0.5) base=vec3(0.87,0.84,0.80);
  vec3 ref=texture2D(uRef,vPUv).rgb;
  base=mix(base,ref,uProj*smoothstep(0.35,0.75,vPB.y));
  vec2 fuv=(vRestXY-uFaceRect.xy)/uFaceRect.zw; fuv.y=1.0-fuv.y;
  if(fuv.x>0.0&&fuv.x<1.0&&fuv.y>0.0&&fuv.y<1.0){ vec4 d=texture2D(uFace,fuv); float fm=uFaceOn*smoothstep(0.25,0.6,vPB.z); base=base*(1.0-d.a*fm)+d.rgb*fm; }
  diffuseColor.rgb*=base;
}`)
      .replace('#include <opaque_fragment>', `
{ float fr=pow(1.0-saturate(dot(normal,geometryViewDir)),uRimPow); outgoingLight+=uRim*fr*(0.55+0.45*normal.y); }
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
      uProj: { value: 0 }, uFlat: { value: 0 }, uFaceOn: { value: 1 },
      uRim: { value: new THREE.Color(0.55, 0.42, 0.34) }, uRimPow: { value: 2.6 },
    };
    this.from = null; this.blend = 1; this.blendDur = 0.35;
    this.cur = {};
  }
  async load(base, name, lod = 'hi') {
    this.base = base; this.name = name;
    if (!this.meta) this.meta = await (await fetch(`${base}${name}.meta.json`)).json();
    const gltf = await new GLTFLoader().loadAsync(`${base}${name}_${lod}.glb`);
    if (this.model) this.root.remove(this.model);
    this.model = gltf.scene; this.root.add(this.model);
    this.bones = {};
    this.model.traverse((o) => {
      if (o.isBone) { this.bones[o.name] = o; this.rest[o.name] = o.position.clone(); }
      if (o.isSkinnedMesh) { this.mesh = o; o.frustumCulled = false; }
    });
    this.material = makeMaterial(this); this.mesh.material = this.material;
    const J = this.meta.joints;
    for (const [u, f, h] of LIMBS) {
      const end = J[h + '_end'];
      this.restDir[u] = V3(J[f]).sub(V3(J[u])).normalize();
      this.restDir[f] = V3(J[h]).sub(V3(J[f])).normalize();
      this.restDir[h] = V3(end).sub(V3(J[h])).normalize();
    }
    if (!this.face) {
      this.face = new FaceDecal(this.meta.face || {});
      const tex = new THREE.CanvasTexture(this.face.canvas); tex.colorSpace = THREE.SRGBColorSpace; tex.flipY = false; tex.premultiplyAlpha = true;
      tex.anisotropy = 4; this.faceTex = tex; this.uniforms.uFace.value = tex;
      const r = this.face.rect; this.uniforms.uFaceRect.value.set(r.x, r.y, r.w, r.h);
      const ref = await new THREE.TextureLoader().loadAsync(`${base}${name}_ref.png`);
      ref.colorSpace = THREE.SRGBColorSpace; ref.flipY = false; this.uniforms.uRef.value = ref;
    }
    this.count = { verts: this.mesh.geometry.attributes.position.count, tris: this.mesh.geometry.index.count / 3 };
    return this;
  }
  setPalette(p) { PART_KEYS.forEach((k, i) => { if (p[k]) this.uniforms.uPal.value[i].set(p[k]); }); }
  setMode(m) { this.uniforms.uProj.value = m === 'proj' ? 1 : 0; this.uniforms.uFlat.value = m === 'clay' ? 1 : 0; this.uniforms.uFaceOn.value = m === 'clay' ? 0 : 1; }
  setFace(state) { if (this.face.draw(state)) this.faceTex.needsUpdate = true; }

  // 把姿勢描述轉成每根骨頭的本地四元數與髖位移
  solve(pose) {
    const out = { q: {}, pos: new THREE.Vector3() };
    const eul = (a) => (a ? new THREE.Quaternion().setFromEuler(_e.set(a[0] || 0, a[1] || 0, a[2] || 0, 'YXZ')) : new THREE.Quaternion());
    const r = pose.root || {};
    out.pos.set(r.x || 0, r.y || 0, r.z || 0);
    out.q.hips = eul([r.rx || 0, r.ry || 0, r.rz || 0]).multiply(eul(pose.hips));
    for (const b of ['spine', 'chest', 'neck', 'head', 'shoulderL', 'shoulderR']) out.q[b] = eul(pose[b]);
    for (const [u, f, h, ku, kf, kh] of LIMBS) {
      const du = pose[ku] ? _v.set(...pose[ku].dir).normalize() : this.restDir[u];
      const qu = new THREE.Quaternion().setFromUnitVectors(this.restDir[u], du);
      if (pose[ku] && pose[ku].twist) qu.multiply(_q.setFromAxisAngle(this.restDir[u], pose[ku].twist));
      out.q[u] = qu;
      // 下段：在上段的本地座標裡做最小轉動（純彎曲，不帶扭轉）
      const qf = new THREE.Quaternion();
      if (pose[kf]) {
        const d = new THREE.Vector3(...pose[kf].dir).normalize().applyQuaternion(_q.copy(qu).invert());
        qf.setFromUnitVectors(this.restDir[f], d);
        if (pose[kf].twist) qf.multiply(_q.setFromAxisAngle(this.restDir[f], pose[kf].twist));
      }
      out.q[f] = qf;
      const ph = pose[kh + '_']; // 手、腳：
      const qh = new THREE.Quaternion();
      if (ph && ph.dir) { // 指定末端方向（身體座標）
        const d = new THREE.Vector3(...ph.dir).normalize().applyQuaternion(_q.copy(qu).multiply(qf).invert());
        qh.setFromUnitVectors(this.restDir[h], d);
      } else if (ph && ph.world) { // 末端維持身體座標下的固定朝向（腳掌貼地用）
        qh.copy(_q.copy(qu).multiply(qf).invert()).multiply(eul(ph.world));
      } else if (ph && ph.rot) qh.copy(eul(ph.rot));
      out.q[h] = qh;
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
    const s = this.solve(pose);
    if (this.blend < 1 && this.from) {
      this.blend = Math.min(1, this.blend + dt / this.blendDur);
      const w = this.blend * this.blend * (3 - 2 * this.blend);
      for (const k in s.q) if (this.from.q[k]) s.q[k] = this.from.q[k].clone().slerp(s.q[k], w);
      s.pos = this.from.pos.clone().lerp(s.pos, w);
    }
    this.cur = s;
    for (const k in s.q) if (this.bones[k]) this.bones[k].quaternion.copy(s.q[k]);
    this.bones.hips.position.copy(this.rest.hips).add(s.pos);
  }
}
