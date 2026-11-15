// 員工運動場：場地配置與靜態模型（2026-11-15）。
// 位置：辦公室大門外小路的「西邊」（遊民區在東邊），x 0.7～19.0、z 31.7～48.2。
// 做法：所有靜態物件（地面、泳池池壁、球場、球網柱、涼亭、撞球桌、籃框、路燈、灌木）合併成「一個」網格（頂點色，共用 MAT.solid），
//   球網（鐵絲網格）3 張合併成一個線框網格；泳池水面另有一個網格（sports_water.js）。靜態部分合計 2 次繪製。
// 風格：圓潤、柔和配色、霧面，跟辦公室一致；夜晚的燈併進 daytime.js 的暖光點雲（W.extraGlow），不另加光源。
import { THREE, G, Part, PAL, shade, textPlane } from './kit.js';
import { mergeGeometries } from '../../vendor/BufferGeometryUtils.js';

export const LAY = {
  field: { x0: 0.7, x1: 19.0, z0: 31.7, z1: 48.2 },
  deck: { x0: 0.9, x1: 9.1, z0: 32.2, z1: 38.2 },
  pool: { x0: 1.8, x1: 8.2, z0: 33.0, z1: 37.0, top: 0.34, gap: { x0: 3.5, x1: 5.3 }, rim: 0.2, rimH: 0.42 },
  gaz: { cx: 8.2, cz: 39.8, w: 3.8, d: 2.8 },
  table: { cx: 8.2, cz: 39.8, L: 2.2, W: 1.0, top: 0.62, r: 0.055 },   // 檯面可打的範圍 L×W（球心範圍再往內縮一個半徑）
  bask: { x0: 10.8, x1: 18.6, z0: 32.3, z1: 40.0, hx: 14.7, rimZ: 33.31, rimY: 2.1, R: 0.28, boardZ: 32.95, ballR: 0.13 },
  bad: { cx: 5.4, cz: 44.8, L: 7.2, W: 4.4, netH: 1.2 },
  ten: { cx: 14.4, cz: 44.8, L: 8.4, W: 4.6, netH: 0.95 },
  lamps: [[9.4, 32.4], [8.2, 39.8], [18.7, 40.4], [9.9, 41.6], [1.1, 41.6], [18.7, 47.7], [1.1, 47.7]],   // 路燈（x, z）；涼亭那盞掛在橫樑下
};
export const VENUES = [
  { kind: 'badminton', zh: '羽毛球', zone: { x0: 1.0, x1: 9.2, z0: 41.7, z1: 48.0 }, at: { x: 5.4, z: 44.8 } },
  { kind: 'tennis', zh: '網球', zone: { x0: 10.2, x1: 18.8, z0: 41.7, z1: 48.0 }, at: { x: 14.4, z: 44.8 } },
  { kind: 'basketball', zh: '籃球', zone: { x0: 10.5, x1: 18.8, z0: 32.0, z1: 40.8 }, at: { x: 14.7, z: 36.4 } },
  { kind: 'billiards', zh: '撞球', zone: { x0: 5.6, x1: 10.4, z0: 38.3, z1: 41.5 }, at: { x: 8.2, z: 39.8 } },
  { kind: 'pool', zh: '游泳', zone: { x0: 0.9, x1: 9.1, z0: 32.2, z1: 38.2 }, at: { x: 5.0, z: 35.0 } },
];
export const inRect = (r, x, z) => x >= r.x0 && x <= r.x1 && z >= r.z0 && z <= r.z1;

export function buildSports(W) {
  const B = { feet: [], glow: [], lamps: LAY.lamps };
  const P = new Part(), feet = B.feet, F = LAY.field;
  const cx = (a, b) => (a + b) / 2;
  // ── 地面：柔和的草地＋一圈深邊；泳池平台、各球場鋪面各自高一點點（避免共面閃爍）
  P.slab('#cfe3bd', F.x1 - F.x0, F.z1 - F.z0, 0.04, cx(F.x0, F.x1), 0, cx(F.z0, F.z1), 0.5, 0, 0.02);
  const D = LAY.deck; P.slab('#f3e8d3', D.x1 - D.x0, D.z1 - D.z0, 0.05, cx(D.x0, D.x1), 0.04, cx(D.z0, D.z1), 0.3, 0, 0.015);
  // ── 泳池：池底、池壁（南側留一個缺口當入口）、入口的小台階、水面另外做（sports_water.js）
  const L = LAY.pool, T = L.rim, H = L.rimH;
  P.slab('#8ed2e4', L.x1 - L.x0, L.z1 - L.z0, 0.03, cx(L.x0, L.x1), 0.09, cx(L.z0, L.z1), 0.1, 0, 0.01);
  P.slab('#b9e6f0', L.x1 - L.x0 - 1.2, L.z1 - L.z0 - 1.0, 0.012, cx(L.x0, L.x1), 0.121, cx(L.z0, L.z1), 0.4, 0, 0.004);   // 池底淺色地磚（淡淡的格子感）
  const rim = (x0, z0, x1, z1) => { P.box('#fff4e3', x1 - x0, H, z1 - z0, cx(x0, x1), 0.09, cx(z0, z1), 0.07); feet.push({ x: cx(x0, x1), z: cx(z0, z1), w: x1 - x0, d: z1 - z0 }); };
  rim(L.x0 - T, L.z0 - T, L.x1 + T, L.z0);                       // 北
  rim(L.x0 - T, L.z0, L.x0, L.z1);                               // 西
  rim(L.x1, L.z0, L.x1 + T, L.z1);                               // 東
  rim(L.x0 - T, L.z1, L.gap.x0, L.z1 + T);                       // 南（缺口左）
  rim(L.gap.x1, L.z1, L.x1 + T, L.z1 + T);                       // 南（缺口右）
  P.box('#ffe6a3', L.gap.x1 - L.gap.x0, 0.12, 0.5, cx(L.gap.x0, L.gap.x1), 0.09, L.z1 - 0.2, 0.05);   // 入口小台階
  P.box('#ffe6a3', L.gap.x1 - L.gap.x0, 0.1, 0.4, cx(L.gap.x0, L.gap.x1), 0.09, L.z1 + 0.25, 0.05);
  // 躺椅兩張、救生圈一個（裝飾；佔地）
  for (const [x, z] of [[9.6 - 0.2, 33.6], [9.6 - 0.2, 35.0]]) { P.slab('#f9c5cf', 0.62, 1.2, 0.05, x - 0.3, 0.09, z, 0.12, 0); P.slab('#fff4e3', 0.62, 0.5, 0.05, x - 0.3, 0.14, z - 0.55, 0.12, -0.35); feet.push({ x: x - 0.3, z, w: 0.7, d: 1.3 }); }
  P.add(G.torus(0.24, 0.07, 18), '#f28b82', 3.0, 0.05, 32.62 + 0.1, 0, Math.PI / 2);   // 池邊的救生圈（平放在平台上）
  // ── 涼亭＋撞球桌：四根柱子、疏疏的橫樑（俯視看得到桌面）、桌子
  const Z = LAY.gaz, X = LAY.table;
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const px = Z.cx + sx * (Z.w / 2 - 0.1), pz = Z.cz + sz * (Z.d / 2 - 0.1); P.cyl(PAL.woodMid, 0.09, 2.3, px, 0, pz, 0.03); feet.push({ x: px, z: pz, r: 0.1 }); }
  // 屋頂只做一圈細框＋兩端各兩根橫條（中間全空，俯視與斜視都看得到桌面）
  P.box(PAL.woodMid, Z.w + 0.2, 0.07, 0.07, Z.cx, 2.3, Z.cz - Z.d / 2 + 0.1, 0.02); P.box(PAL.woodMid, Z.w + 0.2, 0.07, 0.07, Z.cx, 2.3, Z.cz + Z.d / 2 - 0.1, 0.02);
  P.box(PAL.woodMid, 0.07, 0.07, Z.d - 0.1, Z.cx - Z.w / 2 + 0.1, 2.3, Z.cz, 0.02); P.box(PAL.woodMid, 0.07, 0.07, Z.d - 0.1, Z.cx + Z.w / 2 - 0.1, 2.3, Z.cz, 0.02);
  for (const dx of [0.35, 0.7, 1.05]) for (const sg of [-1, 1]) P.box(PAL.wood, 0.07, 0.05, Z.d - 0.1, Z.cx + sg * (Z.w / 2 - 0.1 - dx), 2.31, Z.cz, 0.015);
  P.slab('#ecdcc2', Z.w - 0.1, Z.d - 0.1, 0.03, Z.cx, 0.04, Z.cz, 0.2, 0, 0.01);
  const tw = X.L + 0.34, td = X.W + 0.34;
  P.box('#8a5a3a', tw, 0.5, td, X.cx, 0.1, X.cz, 0.06);                            // 桌身
  P.slab('#4aa37a', X.L + 0.04, X.W + 0.04, 0.03, X.cx, X.top - 0.03, X.cz, 0.08, 0, 0.01);   // 檯呢
  for (const [dx, dz, w, d] of [[0, -(X.W / 2 + 0.07), tw, 0.14], [0, X.W / 2 + 0.07, tw, 0.14], [-(X.L / 2 + 0.07), 0, 0.14, td], [X.L / 2 + 0.07, 0, 0.14, td]]) P.box('#b57a52', w, 0.1, d, X.cx + dx, X.top - 0.02, X.cz + dz, 0.04);   // 邊框
  for (const [dx, dz] of [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, -1], [0, 1]]) P.cyl('#3a3340', 0.085, 0.012, X.cx + dx * (X.L / 2), X.top + 0.0, X.cz + dz * (X.W / 2), 0.004);   // 六個袋口
  feet.push({ x: X.cx, z: X.cz, w: tw + 0.04, d: td + 0.04 });
  // ── 籃球半場：橘色鋪面、白線、禁區；籃框（柱、籃板、框）
  const K = LAY.bask, kc = { x: cx(K.x0, K.x1), z: cx(K.z0, K.z1) };
  P.slab('#f2cfa6', K.x1 - K.x0, K.z1 - K.z0, 0.03, kc.x, 0.04, kc.z, 0.25, 0, 0.01);
  P.slab('#e7a98f', 2.6, 3.6, 0.012, K.hx, 0.07, K.z0 + 0.1 + 1.8, 0.1, 0, 0.004);                // 禁區
  const line = (x, z, w, d, y = 0.075) => P.box('#fffaf2', w, 0.008, d, x, y, z, 0.002);
  line(kc.x, K.z0 + 0.06, K.x1 - K.x0, 0.07); line(kc.x, K.z1 - 0.06, K.x1 - K.x0, 0.07); line(K.x0 + 0.06, kc.z, 0.07, K.z1 - K.z0); line(K.x1 - 0.06, kc.z, 0.07, K.z1 - K.z0);   // 邊線
  line(K.hx, K.z0 + 3.7, 2.6, 0.07); line(K.hx - 1.3, K.z0 + 1.9, 0.07, 3.6); line(K.hx + 1.3, K.z0 + 1.9, 0.07, 3.6);                   // 罰球線與禁區邊線
  P.cyl('#9aa0aa', 0.07, 2.5, K.hx, 0, K.z0 + 0.35, 0.02); feet.push({ x: K.hx, z: K.z0 + 0.35, r: 0.12 });                                 // 籃框柱
  P.box('#9aa0aa', 0.08, 0.08, 0.6, K.hx, 2.38, K.z0 + 0.62, 0.02);                                                                         // 支臂
  P.box('#fffaf2', 1.3, 0.85, 0.06, K.hx, 2.0, K.boardZ, 0.03); P.box('#e86a6a', 0.5, 0.35, 0.065, K.hx, 2.12, K.boardZ + 0.003, 0.02);   // 籃板（外框紅）
  P.add(G.torus(K.R, 0.025, 20), '#f28b82', K.hx, K.rimY, K.rimZ, 0, Math.PI / 2);                                                          // 籃框
  P.box('#f28b82', 0.1, 0.05, K.rimZ - K.boardZ - K.R + 0.04, K.hx, K.rimY - 0.03, K.boardZ + (K.rimZ - K.boardZ - K.R) / 2 + 0.02, 0.01);   // 框與籃板的連接片
  // ── 羽毛球、網球場：外圍鋪面＋球場＋白線＋球網柱＋球網下緣的白帶
  const court = (C, apron, fill) => {
    P.slab(apron, C.L + 1.4, C.W + 1.4, 0.03, C.cx, 0.04, C.cz, 0.3, 0, 0.01);
    P.slab(fill, C.L, C.W, 0.012, C.cx, 0.07, C.cz, 0.12, 0, 0.004);
    line(C.cx, C.cz - C.W / 2 + 0.035, C.L, 0.07, 0.078); line(C.cx, C.cz + C.W / 2 - 0.035, C.L, 0.07, 0.078);
    line(C.cx - C.L / 2 + 0.035, C.cz, 0.07, C.W, 0.078); line(C.cx + C.L / 2 - 0.035, C.cz, 0.07, C.W, 0.078);
    line(C.cx - C.L / 4, C.cz, 0.05, C.W, 0.078); line(C.cx + C.L / 4, C.cz, 0.05, C.W, 0.078); line(C.cx, C.cz, C.L / 2, 0.05, 0.078);   // 發球區線與中線
    const nz0 = C.cz - C.W / 2 - 0.5, nz1 = C.cz + C.W / 2 + 0.5;
    for (const z of [nz0, nz1]) { P.cyl(PAL.cream, 0.05, C.netH + 0.1, C.cx, 0, z, 0.02); }
    P.box('#ffffff', 0.04, 0.07, nz1 - nz0, C.cx, C.netH - 0.06, cx(nz0, nz1), 0.01);                 // 網頂白帶
    // 球網兩端往外：細柱＋繩（把整條邊界封起來，免得從網的兩端繞過去）
    for (const [za, zb] of [[nz0 - 0.0, 40.4], [nz1, F.z1 + 0.0]]) { const n = Math.max(1, Math.round(Math.abs(zb - za) / 1.2)); for (let i = 1; i <= n; i++) { const zz = za + (zb - za) * i / n; P.cyl('#e9c79c', 0.035, 0.55, C.cx, 0, zz, 0.01); } P.box('#fffaf2', 0.025, 0.025, Math.abs(zb - za), C.cx, 0.5, cx(za, zb), 0.005); }
    feet.push({ x: C.cx, z: cx(40.4, F.z1), w: 0.1, d: F.z1 - 40.4 });                              // 球網與兩端的繩：整條擋住，分出兩個半場
  };
  court(LAY.bad, '#d7ebd9', '#bfe3d0'); court(LAY.ten, '#cfe5c4', '#a8c8ec');
  // ── 路燈：燈柱＋燈罩（夜晚的光暈在 daytime.js 的暖光點雲）
  for (const [x, z] of LAY.lamps) {
    const under = Math.abs(x - Z.cx) < 0.01 && Math.abs(z - Z.cz) < 0.01; if (under) { P.sph('#fff0b8', 0.16, x, 2.15, z); B.glow.push([x, 2.3, z]); continue; }
    P.cyl('#b9a48f', 0.07, 2.3, x, 0, z, 0.02); P.cyl('#b9a48f', 0.2, 0.06, x, 0, z, 0.02); P.sph('#fff0b8', 0.3, x, 2.5, z); P.cyl('#b9a48f', 0.2, 0.08, x, 2.72, z, 0.03); feet.push({ x, z, r: 0.16 }); B.glow.push([x, 2.7, z]);
  }
  // ── 外圈灌木（南邊與西邊，圓圓的）
  for (let x = 1.4; x < F.x1; x += 1.9) { P.sph(x % 3.8 < 1.9 ? PAL.leafDark : PAL.leaf, 0.36, x, 0.3, F.z1 + 0.5, 1.2, 0.9, 1); }
  for (let z = 32.6; z < F.z1; z += 2.2) P.sph(z % 4.4 < 2.2 ? PAL.leaf : PAL.leafDark, 0.34, F.x0 - 0.15, 0.28, z, 0.9, 0.9, 1.2);
  { const sx0 = 12.4, sz0 = 31.85; for (const dx of [-1.5, 1.5]) { P.cyl(PAL.woodMid, 0.06, 2.2, sx0 + dx, 0, sz0, 0.02); feet.push({ x: sx0 + dx, z: sz0, r: 0.1 }); } }   // 招牌的兩根柱子
  const m = P.mesh(); m.castShadow = false; m.receiveShadow = true; m.renderOrder = 0; W.scene.add(m); B.mesh = m;
  // ── 招牌：員工運動場（木牌、兩根柱子，朝南）
  const sx = 12.4, sz = 31.85;
  const sg = textPlane(['員工運動場', '羽毛球・籃球・網球・撞球・游泳'], 3.3, 0.95, { bg: '#7fc4a0', fg: '#ffffff', fg2: '#f3fff7', px: 84, subScale: 0.42, radius: 30, border: '#4c8d6d', borderW: 12, pw: 720 });
  sg.material = new THREE.MeshBasicMaterial({ map: sg.userData.tex, transparent: true, alphaTest: 0.3, toneMapped: false }); sg.position.set(sx, 2.1, sz + 0.08); W.scene.add(sg); B.sign = sg;
  // ── 球網（鐵絲網格）：三張（羽毛球、網球；籃框的網）合併成一個線框網格
  const geos = [];
  for (const C of [LAY.bad, LAY.ten]) {
    const len = C.W + 1.0, g = new THREE.PlaneGeometry(len, C.netH - 0.08, Math.round(len / 0.14), Math.round((C.netH - 0.08) / 0.14)); g.rotateY(Math.PI / 2); g.translate(C.cx, (C.netH - 0.08) / 2 + 0.04, C.cz); geos.push(g.toNonIndexed());
  }
  { const g = new THREE.CylinderGeometry(K.R, K.R * 0.55, 0.34, 10, 3, true); g.translate(K.hx, K.rimY - 0.19, K.rimZ); geos.push(g.toNonIndexed()); }
  for (const g of geos) { g.deleteAttribute('uv'); if (g.attributes.normal) g.deleteAttribute('normal'); }
  const nets = new THREE.Mesh(mergeGeometries(geos, false), new THREE.MeshBasicMaterial({ color: '#ffffff', wireframe: true, transparent: true, opacity: 0.7, fog: false })); nets.frustumCulled = false; nets.renderOrder = 2; W.scene.add(nets); B.nets = nets;
  // 夜晚的光暈與地面光斑：併進 daytime.js 的點雲
  W.extraFeet = [...(W.extraFeet || []), ...feet]; W.extraGlow = [...(W.extraGlow || []), ...B.glow];
  return B;
}
