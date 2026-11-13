// 材質預設（Material Preset）六種：軟綿絨毛、柔霧塑膠、半透明果凍、陶瓷、橡膠、柔軟雲朵。
// 設計原則（防「油膩、過度反光、螢光」）：
//   · 非陶瓷 roughness ≥ 0.45、clearcoat ≤ 0.2（陶瓷 ≤ 0.6）、envMapIntensity ≤ 0.5
//   · 完全不使用 emissive；柔軟感來自 sheen、頂點色 AO、上下漸層與極細的絨毛雜訊
//   · 相容 SkinnedMesh 與形態鍵：只在 color_fragment／roughnessmap_fragment 後面「加料」，不改頂點著色器的位置流程
//     （舊版 softMat 的 begin_vertex／project_vertex 改寫在這一階段實測也相容，見 docs/ai_office/upgrade_plan.md 第二階段結果）
// 用法：const mat = makeMaterial('fur', { color: 0xffd2b8, top: 0xfff1e2 });
import * as THREE from 'three';

export const PRESETS = {
  fur:     { zh: '軟綿絨毛', rough: 0.88, ao: 0.4, sheen: 0.75, sheenRough: 0.55, sheenColor: 0xfff0e2, env: 0.30, spec: 0.35, noiseA: 0.022, noiseF: 170, topAmt: 1.0, rough2: 0.08 },
  matte:   { zh: '柔霧塑膠', rough: 0.55, ao: 0.55, coat: 0.15, coatRough: 0.5, env: 0.38, spec: 0.5, noiseA: 0.0, noiseF: 1, topAmt: 0.8, rough2: 0.0 },
  jelly:   { zh: '半透明果凍', rough: 0.34, ao: 0.4, env: 0.45, spec: 0.55, alpha: 0.92, noiseA: 0.0, noiseF: 1, topAmt: 1.0, fresnel: 0.10, rough2: 0.0, sheen: 0.2, sheenRough: 0.5, sheenColor: 0xffffff },
  ceramic: { zh: '陶瓷', rough: 0.28, ao: 0.4, coat: 0.6, coatRough: 0.12, env: 0.45, spec: 0.6, noiseA: 0.0, noiseF: 1, topAmt: 0.6, rough2: 0.0 },
  rubber:  { zh: '橡膠', rough: 0.72, ao: 0.5, env: 0.25, spec: 0.3, sheen: 0.15, sheenRough: 0.7, sheenColor: 0xffffff, noiseA: 0.015, noiseF: 220, topAmt: 0.5, rough2: 0.05 },
  cloud:   { zh: '柔軟雲朵', rough: 1.0, ao: 0.3, sheen: 1.0, sheenRough: 0.8, sheenColor: 0xffffff, env: 0.3, spec: 0.2, noiseA: 0.02, noiseF: 90, topAmt: 0.7, rough2: 0.0, wrap: 0.25 },
};
export const PRESET_IDS = Object.keys(PRESETS);

const NOISE_GLSL = `
float h3(vec3 p){ p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vn(vec3 x){ vec3 i = floor(x), f = fract(x); f = f*f*(3.0-2.0*f);
  return mix(mix(mix(h3(i+vec3(0,0,0)),h3(i+vec3(1,0,0)),f.x), mix(h3(i+vec3(0,1,0)),h3(i+vec3(1,1,0)),f.x), f.y),
             mix(mix(h3(i+vec3(0,0,1)),h3(i+vec3(1,0,1)),f.x), mix(h3(i+vec3(0,1,1)),h3(i+vec3(1,1,1)),f.x), f.y), f.z); }
`;

/** 近景用 Physical（sheen、clearcoat）；far:true 時退化成只有基本參數（遠景省 GPU）。 */
export function makeMaterial(id, o = {}) {
  const P = { ...PRESETS[id] || PRESETS.fur, ...(o.over || {}) };
  const m = new THREE.MeshPhysicalMaterial({
    color: o.color ?? 0xffd2b8, roughness: P.rough, metalness: 0, envMapIntensity: P.env,
    specularIntensity: P.spec ?? 0.5, vertexColors: !!o.vertexAO, side: THREE.FrontSide,
  });
  if (!o.far) {
    if (P.sheen) { m.sheen = P.sheen; m.sheenRoughness = P.sheenRough ?? 0.6; m.sheenColor = new THREE.Color(P.sheenColor ?? 0xffffff); }
    if (P.coat) { m.clearcoat = P.coat; m.clearcoatRoughness = P.coatRough ?? 0.4; }
  }
  if (P.alpha && P.alpha < 1) { m.transparent = true; m.opacity = P.alpha; }
  const U = {
    uTop: { value: new THREE.Color(o.top ?? o.color ?? 0xfff1e2) }, uY: { value: new THREE.Vector2(o.y0 ?? 0.08, o.y1 ?? 0.74) },
    uTopAmt: { value: P.topAmt ?? 1 }, uNoiseA: { value: P.noiseA ?? 0 }, uNoiseF: { value: P.noiseF ?? 100 }, uRough2: { value: P.rough2 ?? 0 },
    uFresnel: { value: P.fresnel ?? 0 }, uWrap: { value: P.wrap ?? 0 },
  };
  m.userData.U = U; m.userData.preset = id; m.userData.P = P;
  m.onBeforeCompile = (s) => {
    Object.assign(s.uniforms, U);
    // 頂點：把「靜止姿勢的物件座標」傳給片段（雜訊與漸層要黏在身上，不隨骨頭動）
    s.vertexShader = s.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vRestP;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\n vRestP = position;');
    s.fragmentShader = s.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vRestP; uniform vec3 uTop; uniform vec2 uY; uniform float uTopAmt, uNoiseA, uNoiseF, uRough2, uFresnel, uWrap;\n${NOISE_GLSL}`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        { float g = smoothstep(uY.x, uY.y, vRestP.y) * uTopAmt; diffuseColor.rgb = mix(diffuseColor.rgb, uTop * (diffuseColor.rgb / max(max(diffuseColor.r, diffuseColor.g), max(diffuseColor.b, 1e-3))), min(g * 0.7, 0.9));
          float n = vn(vRestP * uNoiseF) * 0.6 + vn(vRestP * uNoiseF * 2.3) * 0.4; diffuseColor.rgb *= 1.0 + (n - 0.5) * uNoiseA * 2.0; }`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
        { float n2 = vn(vRestP * uNoiseF * 0.7 + 3.1); roughnessFactor = clamp(roughnessFactor + (n2 - 0.5) * uRough2 * 2.0, 0.0, 1.0); }`)
      .replace('#include <opaque_fragment>', `
        { float fr = pow(1.0 - saturate(dot(normalize(normal), normalize(vViewPosition))), 2.6);
          outgoingLight += diffuseColor.rgb * fr * (uFresnel + uWrap * 0.35); }
        #include <opaque_fragment>`);
  };
  m.customProgramCacheKey = () => 'mat-' + id + (o.far ? 'F' : '') + (o.vertexAO ? 'A' : '');
  return m;
}

/** 頂點色：Blender 匯出的 COLOR_0 是 RGBA——RGB＝局部顏色乘數（耳內淡粉、肚子較淺、手腳掌略粉），A＝AO。
 *  這裡把它們合成成 RGB（= 乘數 × (1 − (1−AO)·強度)）；AO 強度 1＝完整遮蔽、0＝沒有，可反覆調（原始資料存在 userData）。
 *  舊版只有灰階 AO 的檔案（itemSize 3）照舊相容。 */
export function setAOStrength(geo, s) {
  let a = geo.attributes.color || geo.attributes.color_0; if (!a) return;
  if (!geo.userData.aoRaw) {
    const n = a.count, ao = new Float32Array(n), tint = new Float32Array(n * 3), rgba = a.itemSize === 4;
    for (let i = 0; i < n; i++) { ao[i] = rgba ? a.getW(i) : a.getX(i); tint[i * 3] = rgba ? a.getX(i) : 1; tint[i * 3 + 1] = rgba ? a.getY(i) : 1; tint[i * 3 + 2] = rgba ? a.getZ(i) : 1; }
    geo.userData.aoRaw = ao; geo.userData.tintRaw = tint;
    if (rgba || a.normalized) { a = new THREE.BufferAttribute(new Float32Array(n * 3), 3); geo.setAttribute('color', a); if (geo.attributes.color_0) geo.deleteAttribute('color_0'); }
  }
  const raw = geo.userData.aoRaw, t = geo.userData.tintRaw;
  for (let i = 0; i < a.count; i++) { const v = 1 - (1 - raw[i]) * s; a.setXYZ(i, t[i * 3] * v, t[i * 3 + 1] * v, t[i * 3 + 2] * v); }
  a.needsUpdate = true;
}
/** 取得某個點附近的「本體顏色乘數」（局部顏色 × AO）：把眼皮、臉上的零件調到跟身體同色用。取最近的幾個頂點加權平均 */
export function skinColorAt(geo, p, s) {
  const pos = geo.attributes.position, raw = geo.userData.aoRaw, t = geo.userData.tintRaw; if (!raw) return [1, 1, 1];
  const best = [];
  for (let i = 0; i < pos.count; i++) { const d = (pos.getX(i) - p[0]) ** 2 + (pos.getY(i) - p[1]) ** 2 + (pos.getZ(i) - p[2]) ** 2; if (best.length < 6 || d < best[best.length - 1][0]) { best.push([d, i]); best.sort((u, v) => u[0] - v[0]); if (best.length > 6) best.pop(); } }
  let r = 0, g = 0, b = 0, w = 0; for (const [d, i] of best) { const k = 1 / (d + 2e-4), v = 1 - (1 - raw[i]) * s; r += k * t[i * 3] * v; g += k * t[i * 3 + 1] * v; b += k * t[i * 3 + 2] * v; w += k; }
  return [r / w, g / w, b / w];
}

/** 程序化環境貼圖（沒有 HDR 檔、不連網）：暖白天空＋暖米地面＋一塊柔光箱。只供高光反射用。 */
export function makeEnvironment(renderer) {
  const sc = new THREE.Scene();
  const sky = new THREE.Mesh(new THREE.SphereGeometry(10, 32, 16), new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: 'varying vec3 vP; void main(){ float h = vP.y; vec3 top = vec3(1.0,0.96,0.90), mid = vec3(0.96,0.88,0.80), bot = vec3(0.88,0.74,0.62); vec3 c = h > 0.0 ? mix(mid, top, smoothstep(0.0,0.8,h)) : mix(mid, bot, smoothstep(0.0,-0.6,h)); gl_FragColor = vec4(c * 0.9, 1.0); }',
  }));
  sc.add(sky);
  const box = new THREE.Mesh(new THREE.PlaneGeometry(6, 4), new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide }));
  box.material.color.multiplyScalar(2.2); box.position.set(3, 5, 4); box.lookAt(0, 0, 0); sc.add(box);
  const pm = new THREE.PMREMGenerator(renderer), rt = pm.fromScene(sc, 0.04); pm.dispose();
  sky.geometry.dispose(); sky.material.dispose(); box.geometry.dispose(); box.material.dispose();
  return rt.texture;
}
