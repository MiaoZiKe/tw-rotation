// 軟質材質與圓潤幾何：所有物種共用
import * as THREE from 'three';
const V3 = THREE.Vector3, _a = new V3();
export const clamp = (x, a, b) => Math.max(a, Math.min(b, x)), lerp = (a, b, t) => a + (b - a) * t;
export const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
// ── 軟質材質：上下漸層、邊緣光、假的次表面散射、戳下去的凹陷、接地壓扁、臉部貼圖
export function softMat(o, sh) {
  const m = new THREE.MeshStandardMaterial({ color: o.color, roughness: o.rough ?? 0.62, metalness: 0 });
  const U = {
    uTop: { value: new THREE.Color(o.top ?? o.color) }, uY: { value: new THREE.Vector2(o.y0 ?? -0.3, o.y1 ?? 0.3) },
    uSss: { value: new THREE.Color(o.sss ?? 0xff8a70) }, uSssAmt: { value: o.sssAmt ?? 0.3 }, uRim: { value: new THREE.Color(o.rim ?? 0xfff6ea) }, uRimAmt: { value: o.rimAmt ?? 0.32 },
    uTint: sh.uTint, uTintAmt: sh.uTintAmt, uPat: { value: new THREE.Vector4(0, 0, 4, 0) }, uPatCol: { value: new THREE.Color(0xffffff) }, uPatC: { value: new V3() }, uPatR: { value: 0.1 }, uGround: sh.uGround, uDent: { value: new THREE.Vector4(0, 1, 0, 0) }, uDentR: { value: 0.17 },
  };
  if (o.root) Object.assign(U, { uBodyC: sh.uBodyC, uBodyK: sh.uBodyK, uBodyYS: sh.uBodyYS, uRootCol: { value: new THREE.Color(o.root.color) }, uRootTop: { value: new THREE.Color(o.root.top ?? o.root.color) }, uRootY: { value: new THREE.Vector2(o.root.y0 ?? -0.3, o.root.y1 ?? 0.3) }, uRootSpan: { value: o.rootSpan ?? 0.3 } });
  m.userData.o = o;
  if (o.face) Object.assign(U, { uFace: { value: o.face.tex }, uHeadC: { value: new V3(...o.headC) }, uFaceSpan: { value: new THREE.Vector2(...o.span) }, uFaceOff: { value: new THREE.Vector2() }, uFaceGlow: { value: o.glow ?? 0 }, uFaceGloss: { value: o.gloss ?? 0.7 } });
  m.userData.U = U; if (o.face || o.root) { m.defines = {}; if (o.face) m.defines.USE_FACE = ''; if (o.root) m.defines.USE_ROOT = ''; }
  m.onBeforeCompile = (s) => {
    Object.assign(s.uniforms, U);
    s.vertexShader = s.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vObjP; uniform vec4 uDent; uniform float uDentR; uniform float uGround;\n#ifdef USE_ROOT\nvarying vec3 vWP;\n#endif')
      .replace('#include <beginnormal_vertex>', '#include <beginnormal_vertex>\n vec3 dP = position - uDent.xyz; float dW = exp(-dot(dP,dP)/(uDentR*uDentR)); objectNormal = normalize(objectNormal - uDent.w*dW*2.0*dP/(uDentR*uDentR));')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\n vObjP = position; transformed -= normal * uDent.w * dW;')
      .replace('#include <project_vertex>', 'vec4 wPos = modelMatrix * vec4(transformed,1.0); float gd = uGround - wPos.y; if (gd > 0.0) wPos.y = uGround - gd*0.06;\n vec4 mvPosition = viewMatrix * wPos; gl_Position = projectionMatrix * mvPosition;\n#ifdef USE_ROOT\n vWP = wPos.xyz;\n#endif');
    s.fragmentShader = s.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vObjP; uniform vec3 uTop; uniform vec2 uY; uniform vec3 uSss; uniform float uSssAmt; uniform vec3 uRim; uniform float uRimAmt; uniform vec3 uTint; uniform float uTintAmt; uniform vec4 uPat; uniform vec3 uPatCol; uniform vec3 uPatC; uniform float uPatR;\n#ifdef USE_ROOT\nvarying vec3 vWP; uniform vec3 uBodyC; uniform vec3 uBodyK; uniform float uBodyYS; uniform vec3 uRootCol; uniform vec3 uRootTop; uniform vec2 uRootY; uniform float uRootSpan;\n#endif\n#ifdef USE_FACE\nuniform sampler2D uFace; uniform vec3 uHeadC; uniform vec2 uFaceSpan; uniform vec2 uFaceOff; uniform float uFaceGlow; uniform float uFaceGloss;\n#endif')
      .replace('#include <color_fragment>', `#include <color_fragment>
        diffuseColor.rgb = mix(diffuseColor.rgb, uTop, smoothstep(uY.x, uY.y, vObjP.y)); diffuseColor.rgb = mix(diffuseColor.rgb, uTint, uTintAmt);
        #ifdef USE_ROOT
          vec3 rpv = vWP - uBodyC; float rootE = sqrt(dot(rpv * rpv, uBodyK)); float rootW = 1.0 - smoothstep(1.08, 1.08 + uRootSpan, rootE);
          vec3 rcol = mix(uRootCol, uRootTop, smoothstep(uRootY.x, uRootY.y, rpv.y / uBodyYS)); rcol = mix(rcol, uTint, uTintAmt);
          diffuseColor.rgb = mix(diffuseColor.rgb, rcol, rootW);
        #endif
        float gPat = 0.0, gStitch = 0.0;
        if (uPat.y > 0.001) {
          vec3 q = vObjP; float pk = uPat.x;
          if (pk < 1.5) {
            vec3 pp = q * uPat.z + uPat.w; vec3 id = floor(pp); vec3 fq = fract(pp) - 0.5;
            float h = fract(sin(dot(id, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
            vec3 off = (vec3(fract(h * 7.13), fract(h * 3.71), fract(h * 5.37)) - 0.5) * 0.4;
            gPat = smoothstep(0.17 + 0.12 * fract(h * 11.7), 0.1, length(fq - off)) * step(0.15, h);
          } else if (pk < 2.5) {
            float sb = sin(q.y * uPat.z * 3.1416 + sin(q.x * uPat.z * 2.0 + uPat.w) * 0.3); gPat = smoothstep(0.1, 0.4, sb);
          } else if (pk < 3.5) {
            vec2 dd = q.xy - uPatC.xy; float d = length(dd); float zz = step(uPatC.z, q.z);
            gPat = smoothstep(uPatR, uPatR * 0.94, d) * zz;
            float ang = atan(dd.y, dd.x) / 6.2832 * 18.0;
            gStitch = smoothstep(uPatR * 0.74, uPatR * 0.78, d) * smoothstep(uPatR * 0.86, uPatR * 0.82, d) * step(0.45, fract(ang)) * zz;
          } else {
            vec2 dd = (q.xy - uPatC.xy) / vec2(uPatR * 0.9, uPatR * 1.1); gPat = smoothstep(1.0, 0.78, length(dd)) * step(uPatC.z, q.z);
          }
          #ifdef USE_FACE
            vec3 fdd = normalize(vObjP - uHeadC); float pm = 1.0 - smoothstep(0.30, 0.72, fdd.z) * (1.0 - smoothstep(0.4, 0.7, abs(fdd.y))) * 0.92; gPat *= pm; gStitch *= pm;
          #endif
          gPat *= uPat.y; gStitch *= uPat.y;
          diffuseColor.rgb = mix(diffuseColor.rgb, uPatCol, gPat);
          diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.96, 0.9, 0.8), gStitch * 0.85);
        }`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        #ifdef USE_ROOT
          { vec3 nW = inverseTransformDirection(normal, viewMatrix); vec3 nb = normalize(rpv * uBodyK); nW = normalize(mix(nW, nb, rootW)); normal = transformDirection(nW, viewMatrix); }
        #endif`)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n roughnessFactor = clamp(roughnessFactor + gPat * 0.28 + gStitch * 0.3, 0.0, 1.0);')
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
        float fr = pow(1.0 - saturate(dot(normal, normalize(vViewPosition))), 2.4);
        #ifdef USE_FACE
          vec3 fd = normalize(vObjP - uHeadC);
          vec2 fuv = vec2(atan(fd.x, fd.z) - uFaceOff.x, asin(clamp(fd.y,-1.0,1.0)) - uFaceOff.y) / uFaceSpan + 0.5;
          vec4 fc = texture2D(uFace, fuv);
          float fm = step(0.0,fuv.x)*step(fuv.x,1.0)*step(0.0,fuv.y)*step(fuv.y,1.0)*step(-0.15, fd.z);
          fc *= fm;
          vec3 fcol = pow(fc.rgb / max(fc.a, 1e-3), vec3(2.2));
          diffuseColor.rgb = mix(diffuseColor.rgb, fcol * (1.0 - 0.7*step(0.5,uFaceGlow)), fc.a);
          float dark = fc.a * (1.0 - dot(fcol, vec3(0.333)));
          roughnessFactor = mix(roughnessFactor, 0.14, clamp(dark*uFaceGloss + fc.a*step(0.5,uFaceGlow)*0.8, 0.0, 1.0));
          totalEmissiveRadiance += fcol * fc.a * uFaceGlow;
          fr *= 1.0 - fc.a*0.85;
          float faceA = fc.a;
        #else
          float faceA = 0.0;
        #endif
        totalEmissiveRadiance += (diffuseColor.rgb * uSss * uSssAmt * (0.3 + 0.7*fr) + uRim * uRimAmt * fr) * (1.0 - faceA);`);
  };
  m.customProgramCacheKey = () => (o.face ? 'softface' : 'soft') + (o.root ? 'R' : '');
  return m;
}

// 用單位球變形成任意圓潤造型；法線用數值微分算，沒有接縫
// 細緻度：辦公室一次幾十隻，建立角色前把 DETAIL.k 調低（0.5＝面數約四分之一）
export const DETAIL = { k: 1 };
const dseg = (n, min) => Math.max(min, Math.round(n * DETAIL.k / 2) * 2);
export function blobGeo(fn, ws = 80, hs = 60) {
  const g = new THREE.SphereGeometry(1, dseg(ws, 20), dseg(hs, 14)), p = g.attributes.position, n = g.attributes.normal;
  const d = new V3(), t1 = new V3(), t2 = new V3(), p0 = new V3(), p1 = new V3(), p2 = new V3(), e = 2e-3;
  for (let i = 0; i < p.count; i++) {
    d.fromBufferAttribute(p, i).normalize();
    t1.crossVectors(Math.abs(d.y) > 0.9 ? _a.set(1, 0, 0) : _a.set(0, 1, 0), d).normalize(); t2.crossVectors(d, t1);
    fn(p0.copy(d)); fn(p1.copy(d).addScaledVector(t1, e).normalize()); fn(p2.copy(d).addScaledVector(t2, e).normalize());
    p1.sub(p0); p2.sub(p0); t1.crossVectors(p1, p2).normalize(); if (t1.dot(d) < 0) t1.negate();
    p.setXYZ(i, p0.x, p0.y, p0.z); n.setXYZ(i, t1.x, t1.y, t1.z);
  }
  return g;
}
// ── 身體網格的「高斯鼓包」：list＝[[dx,dy,dz,高,寬],...]，方向為單位球上的方向；回傳該方向要往外多推的距離。
//   在 blobGeo 的 fn 裡先呼叫（v 還是單位方向），再把 v 乘上形狀後 += 原方向 * 回傳值。
//   耳根、肩丘、大腿根、鼻吻從身體同一張曲面鼓出來，肢體接在鼓包頂端，交界輪廓是內凹過渡（沒有接縫）。
export function bumpS(v, list) { let s = 0; for (const b of list) { const dx = v.x - b[0], dy = v.y - b[1], dz = v.z - b[2]; s += b[3] * Math.exp(-(dx * dx + dy * dy + dz * dz) / (b[4] * b[4])); } return s; }
export const ball = (() => { let g; return () => g || (g = new THREE.SphereGeometry(1, dseg(40, 14), dseg(28, 10))); })();
export const foot = (() => { let g; return () => g || (g = blobGeo(v => { v.y = v.y * (v.y < 0 ? 0.55 : 1) + 0.55; v.z += 0.12 * (1 - Math.abs(v.y - 0.5)); }, 36, 24)); })();

