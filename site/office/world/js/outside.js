// 公司外面的「無業遊民區」：被開除的同事不會消失，而是搬到這裡（擁有者原話）。
// 做法：整區所有靜態物件（地面、長椅、路燈、紙箱、營火石圈、拱門）合併成一個網格，加上拱門招牌與一團會閃的火苗，
// 全場只多 3 次繪製；夜晚的路燈與營火光暈併進原本的暖光點雲（daytime.js 的 W.extraGlow），不另外加光源。
// 位置：大門外小路的右邊（東邊）；通往那裡的路在 layout.json 的 walkAreas（尋路用）。
import { THREE, G, Part, PAL, shade, textPlane } from './kit.js';

export function buildOutside(W) {
  const Ld = W.layout.size.d, zx0 = 22.4, zx1 = 37.6, zz0 = 31.9, zz1 = 38.8;
  const O = { zone: { x0: zx0, x1: zx1, z0: zz0, z1: zz1 }, center: { x: (zx0 + zx1) / 2, z: (zz0 + zz1) / 2 }, seats: [], stands: [], mats: [], fire: { x: 30.2, z: 36.6 } };
  const P = new Part(), feet = [], glow = [];
  // 地面：淺色碎石地＋一圈深色邊
  P.slab(shade('#e6d8bd', 0.0), zx1 - zx0 - 0.4, zz1 - zz0 - 0.5, 0.05, (zx0 + zx1) / 2, 0.0, (zz0 + zz1) / 2 + 0.1, 0.9, 0, 0.02);
  P.slab('#d9c8a4', zx1 - zx0 - 1.6, zz1 - zz0 - 1.5, 0.03, (zx0 + zx1) / 2, 0.045, (zz0 + zz1) / 2 + 0.1, 0.8, 0, 0.012);
  // 長椅兩張，各兩個座位（朝南，面向鏡頭）
  const bench = (cx, cz) => {
    P.slab(PAL.wood, 1.7, 0.46, 0.08, cx, 0.36, cz, 0.14); P.box(PAL.cream, 0.1, 0.36, 0.36, cx - 0.62, 0, cz, 0.04); P.box(PAL.cream, 0.1, 0.36, 0.36, cx + 0.62, 0, cz, 0.04);
    P.box(PAL.woodMid, 1.7, 0.42, 0.07, cx, 0.5, cz - 0.24, 0.03);
    feet.push({ x: cx, z: cz - 0.05, w: 1.7, d: 0.7 });
    for (const dx of [-0.42, 0.42]) O.seats.push({ seat: { x: cx + dx, y: 0.44, z: cz, face: 0 }, ap: { x: cx + dx, z: cz + 1.0 }, taken: null });
  };
  bench(27.4, 34.3); bench(33.2, 34.5);
  // 路燈兩根
  for (const [x, z] of [[23.4, 36.9], [35.9, 33.6]]) { P.cyl('#b9a48f', 0.07, 2.3, x, 0, z, 0.02); P.cyl('#b9a48f', 0.2, 0.06, x, 0, z, 0.02); P.sph('#fff0b8', 0.3, x, 2.5, z); P.cyl('#b9a48f', 0.2, 0.08, x, 2.72, z, 0.03); feet.push({ x, z, r: 0.16 }); glow.push([x, 2.45, z]); }
  // 紙箱（疊著，可以當桌子）、毯子（睡覺的地方）
  const box = (x, z, w, h, d, ry = 0) => { P.box('#d8a56a', w, h, d, x, 0.04, z, 0.02, ry); P.box('#f2dfb5', w * 0.26, 0.012, d * 0.98, x, 0.04 + h, z, 0.004, ry); feet.push({ x, z, w: w + 0.1, d: d + 0.1 }); };
  box(25.2, 37.5, 0.62, 0.42, 0.5, 0.2); box(25.95, 37.95, 0.5, 0.34, 0.42, -0.3); P.box('#c99256', 0.5, 0.3, 0.4, 25.5, 0.46, 37.6, 0.02, 0.4); box(36.2, 37.1, 0.6, 0.4, 0.5, 0.1);
  P.slab('#9dbcf0', 1.9, 1.0, 0.03, 33.2, 0.05, 37.4, 0.12); P.slab('#fdf1b8', 1.6, 0.8, 0.02, 33.2, 0.075, 37.4, 0.1);
  O.mats.push({ x: 33.2, z: 37.4, face: Math.PI / 2, taken: null });
  // 營火：石圈、兩根交叉的木頭（火苗是另一個會動的網格）
  const { x: fx, z: fz } = O.fire;
  for (let i = 0; i < 9; i++) { const a = i / 9 * Math.PI * 2; P.sph('#a7a39b', 0.14, fx + Math.cos(a) * 0.62, 0.12, fz + Math.sin(a) * 0.62, 1.2, 0.8, 1); }
  P.add(G.cyl(0.07, 0.8, 0.02, 8), PAL.woodDark, fx + 0.4, 0.15, fz + 0.05, 0.5, 0, Math.PI / 2); P.add(G.cyl(0.07, 0.8, 0.02, 8), PAL.woodDark, fx + 0.1, 0.22, fz - 0.4, -0.5, 0, Math.PI / 2);   // 兩根交叉躺著的木頭
  feet.push({ x: fx, z: fz, r: 0.78 }); glow.push([fx, 0.9, fz]);
  // 拱門（入口）：兩根柱子＋橫梁，招牌朝南
  const ax = 24.0, az = 32.7;   // 拱門貼近大門外小路，預設俯視就看得到入口
  P.cyl(PAL.cream, 0.07, 1.7, ax - 1.1, 0, az, 0.02); P.cyl(PAL.cream, 0.07, 1.7, ax + 1.1, 0, az, 0.02); P.box(PAL.woodMid, 2.5, 0.12, 0.14, ax, 1.62, az, 0.04);
  feet.push({ x: ax - 1.1, z: az, r: 0.12 }, { x: ax + 1.1, z: az, r: 0.12 });
  const m = P.mesh(); m.castShadow = false; m.receiveShadow = true; m.renderOrder = 0; W.scene.add(m); O.mesh = m;
  const sign = textPlane('無業遊民區', 2.2, 0.5, { pw: 512, bg: '#fff1d8', fg: '#6b5a4a', px: 84, radius: 40, border: '#d9c8a4', borderW: 10 }); sign.position.set(ax, 1.98, az + 0.09); W.scene.add(sign); O.sign = sign;
  // 火苗：一個會晃動的小錐體（不受光）
  const F = new Part(); F.cyl('#ff8a3c', 0.3, 0.62, 0, 0, 0, 0.05, 0.04); F.cyl('#ffd36b', 0.17, 0.42, 0, 0.03, 0, 0.04, 0.02);
  const flame = new THREE.Mesh(F.geometry(), new THREE.MeshBasicMaterial({ vertexColors: true })); flame.position.set(fx, 0.2, fz); flame.renderOrder = 1; W.scene.add(flame); O.flame = flame;
  // 站著取暖、閒晃的點（營火外圈、長椅前、拱門內）
  for (let i = 0; i < 8; i++) { const a = i / 8 * Math.PI * 2 + 0.3; O.stands.push({ x: fx + Math.cos(a) * 1.55, z: fz + Math.sin(a) * 1.55, face: Math.atan2(-Math.cos(a), -Math.sin(a)), taken: null }); }
  for (const [x, z] of [[29.4, 33.7], [31.0, 33.5], [35.2, 35.6], [24.6, 35.2], [27.6, 36.0], [36.4, 35.0], [23.6, 34.2]]) O.stands.push({ x, z, face: Math.PI, taken: null });
  W.extraFeet = feet; W.extraGlow = glow; O.feet = feet;
  W.respot();                                       // 把新增的佔地算進尋路（這時還沒有任何角色，不會弄亂座位）
  O.frame = t => { flame.scale.set(1 + Math.sin(t * 13) * 0.07, 1 + Math.sin(t * 9 + 1) * 0.16 + Math.sin(t * 23) * 0.06, 1 + Math.cos(t * 11) * 0.07); flame.rotation.y = t * 0.7; };
  O.inZone = (x, z) => x >= zx0 - 0.2 && x <= zx1 + 0.2 && z >= zz0 - 0.2 && z <= zz1 + 0.2;
  W.outside = O;
  return O;
}
