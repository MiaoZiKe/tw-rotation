// 家具型錄：每一種家具回傳「一個合併網格＋佔地範圍＋座位＋具名目標點」。
// 區域座標：原點在家具中心、y=0 是地面、正面朝 +z（rot=0 時朝南，對著俯瞰鏡頭）。
// 座位 face 是角色的朝向角（0 朝 +z、π 朝 -z），app 是「走到哪裡再坐下」的候選點。
import { THREE, G, Part, PAL, shade, textPlane } from './kit.js';

export function rng(seedStr) {
  let h = 1779033703; for (let i = 0; i < seedStr.length; i++) { h = Math.imul(h ^ seedStr.charCodeAt(i), 3432918353); h = h << 13 | h >>> 19; }
  return () => { h = Math.imul(h ^ h >>> 16, 2246822507); h = Math.imul(h ^ h >>> 13, 3266489909); h ^= h >>> 16; return (h >>> 0) / 4294967296; };
}
const PASTEL = ['#f7b0c6', '#ffd27a', '#a4c2f7', '#97dfcc', '#cbb2f2', '#ffc48f', '#aedb9a', '#f4a59d', '#8ecfe6', '#fff0c2'];
const q = v => Math.round(v * 50) / 50;

function chair(P, x, z, ang, color, big = false) {
  // ang：椅背所在方向（從座位中心看出去）
  const sx = Math.sin(ang), cz = Math.cos(ang), s = big ? 1.15 : 1;
  P.cyl(PAL.grey, 0.24 * s, 0.05, x, 0, z, 0.02);
  P.cyl(PAL.greyDark, 0.045, 0.3, x, 0.04, z, 0.01);
  P.cyl(color, 0.27 * s, 0.11, x, 0.31, z, 0.045);
  P.box(shade(color, -0.08), 0.52 * s, big ? 0.62 : 0.44, 0.11, x + sx * 0.27 * s, 0.4, z + cz * 0.27 * s, 0.05, ang);
}
function leaves(P, r, x, y, z, n, spread, size) {
  const cols = [PAL.leaf, PAL.leafDark, PAL.leafLight];
  for (let i = 0; i < n; i++) {
    const a = r() * 6.28, d = r() * spread, s = size * (0.75 + r() * 0.5);
    P.sph(cols[i % 3], s, x + Math.cos(a) * d, y + r() * spread * 0.9, z + Math.sin(a) * d, 1, 0.9, 1);
  }
}

export const BUILD = {
  workstation(f, ctx) {
    const P = new Part(), r = rng(f.id + (f.owner || '')), col = ctx.deptColor(f.dept) || PAL.sky, soft = shade(col, 0.45);
    P.slab(PAL.wood, 1.5, 0.74, 0.07, 0, 0.6, 0, 0.14);
    P.box(PAL.white, 0.08, 0.6, 0.6, -0.66, 0, 0, 0.035); P.box(PAL.white, 0.08, 0.6, 0.6, 0.66, 0, 0, 0.035);
    P.box(soft, 1.26, 0.3, 0.05, 0, 0.26, -0.3, 0.02);
    // 螢幕
    P.cyl(PAL.grey, 0.11, 0.025, 0, 0.67, -0.2, 0.01); P.cyl(PAL.grey, 0.03, 0.14, 0, 0.68, -0.2, 0.01);
    P.box(PAL.white, 0.6, 0.4, 0.06, 0, 0.78, -0.2, 0.028);
    P.box('#7d8fb5', 0.52, 0.31, 0.02, 0, 0.825, -0.172, 0.008);
    // 鍵盤、滑鼠、杯子
    P.box(PAL.grey, 0.36, 0.025, 0.13, 0, 0.67, 0.1, 0.012); P.sph(PAL.grey, 0.035, 0.28, 0.685, 0.12, 1, 0.6, 1.3);
    P.cyl(col, 0.05, 0.1, 0.52, 0.67, 0.08, 0.02);
    const deco = Math.floor(r() * 4);
    if (deco === 0) { P.cyl(PAL.pot, 0.07, 0.09, -0.56, 0.67, -0.18, 0.02, 0.085); leaves(P, r, -0.56, 0.82, -0.18, 4, 0.05, 0.075); }
    else if (deco === 1) { for (let i = 0; i < 3; i++) P.box(PASTEL[Math.floor(r() * 10)], 0.24 - i * 0.02, 0.04, 0.17, -0.54, 0.67 + i * 0.04, -0.15, 0.012, r() * 0.5 - 0.25); }
    else if (deco === 2) { P.cyl(PAL.yellow, 0.06, 0.02, -0.56, 0.67, -0.2, 0.008); P.cyl(PAL.grey, 0.012, 0.22, -0.56, 0.68, -0.2, 0.004); P.sph(PAL.gold, 0.07, -0.56, 0.93, -0.17, 1, 0.75, 1); }
    else { P.box(PASTEL[Math.floor(r() * 10)], 0.2, 0.16, 0.02, -0.56, 0.67, -0.2, 0.008, 0.3, -0.25); P.sph(PASTEL[Math.floor(r() * 10)], 0.05, -0.36, 0.72, -0.22); }
    chair(P, 0, 0.78, 0, col);
    const extras = [];
    if (f.owner) {
      const m = ctx.member(f.owner);
      P.box(PAL.white, 0.46, 0.035, 0.1, 0.42, 0.67, -0.02, 0.012);
      const tp = textPlane([m ? m.nick : f.owner, m ? m.zh : ''], 0.44, 0.17, { pw: 256, bg: '#fffaf2', border: col, borderW: 8, px: 44, subScale: 0.5, radius: 22 });
      tp.position.set(0.42, 0.775, -0.01); tp.rotation.x = -0.5; extras.push(tp);
    }
    return {
      part: P, extras, foot: [{ x: 0, z: 0, w: 1.5, d: 0.74 }, { x: 0, z: 0.78, r: 0.28 }],
      seats: [{ key: f.owner ? 'seat:' + f.owner : 'spare', x: 0, z: 0.78, y: 0.42, face: Math.PI, app: [[0, 1.5], [0.85, 1.05], [-0.85, 1.05], [0.9, 1.6], [-0.9, 1.6]] }],
      screen: { x: 0, y: 0.98, z: -0.158, w: 0.5, h: 0.29 }
    };
  },
  ceo_desk(f, ctx) {
    const P = new Part();
    P.slab(PAL.woodMid, 2.5, 1.05, 0.08, 0, 0.62, 0, 0.2);
    P.box(PAL.woodDark, 0.5, 0.62, 0.8, -0.9, 0, 0, 0.06); P.box(PAL.woodDark, 0.5, 0.62, 0.8, 0.9, 0, 0, 0.06);
    P.box(shade(PAL.woodMid, 0.2), 1.9, 0.42, 0.06, 0, 0.16, -0.42, 0.025);
    P.cyl(PAL.grey, 0.13, 0.025, 0, 0.7, -0.22, 0.01); P.cyl(PAL.grey, 0.035, 0.16, 0, 0.71, -0.22, 0.01);
    P.box(PAL.white, 0.86, 0.46, 0.06, 0, 0.82, -0.22, 0.03); P.box('#7d8fb5', 0.78, 0.37, 0.02, 0, 0.865, -0.192, 0.008);
    P.box(PAL.grey, 0.4, 0.025, 0.14, 0, 0.7, 0.14, 0.012);
    P.cyl(PAL.gold, 0.055, 0.11, 0.62, 0.7, 0.12, 0.02);
    P.cyl(PAL.pot, 0.09, 0.11, -0.95, 0.7, -0.25, 0.02, 0.105); leaves(P, rng('ceoplant'), -0.95, 0.9, -0.25, 5, 0.07, 0.1);
    for (let i = 0; i < 3; i++) P.box(PASTEL[i * 3], 0.3, 0.045, 0.22, 0.95, 0.7 + i * 0.045, -0.2, 0.014, i * 0.2 - 0.2);
    P.box(PAL.gold, 0.5, 0.05, 0.12, 0, 0.7, -0.47, 0.02);
    chair(P, 0, 0.98, 0, '#ffb86b', true);
    const tp = textPlane('CEO', 0.46, 0.18, { pw: 256, bg: '#fff3d6', border: '#ffb86b', borderW: 10, px: 56, radius: 24 });
    tp.position.set(0, 0.84, -0.5); tp.rotation.y = Math.PI; tp.rotation.x = 0.35;
    return {
      part: P, extras: [tp], foot: [{ x: 0, z: 0, w: 2.5, d: 1.05 }, { x: 0, z: 0.98, r: 0.32 }],
      seats: [{ key: 'seat:ceo', x: 0, z: 0.98, y: 0.42, face: Math.PI, app: [[1.1, 1.3], [-1.1, 1.3], [0, 1.75]] }],
      spots: [{ name: 'ceo_front', x: 0, z: -1.25, face: 0 }, { name: 'ceo_front', x: -1.0, z: -1.4, face: 0.3 }, { name: 'ceo_front', x: 1.0, z: -1.4, face: -0.3 }],
      screen: { x: 0, y: 1.05, z: -0.178, w: 0.76, h: 0.35 }
    };
  },
  meeting_table() {
    const P = new Part(), seats = [], foot = [{ x: 0, z: 0, r: 1.7 }];
    P.cyl(PAL.cream, 0.55, 0.62, 0, 0, 0, 0.08, 0.4); P.cyl(PAL.wood, 1.75, 0.09, 0, 0.6, 0, 0.04, 1.75, 36);
    P.cyl(shade(PAL.wood, 0.25), 1.2, 0.012, 0, 0.69, 0, 0.005);
    P.cyl(PAL.pot, 0.13, 0.12, 0, 0.7, 0, 0.03, 0.15); leaves(P, rng('mt'), 0, 0.92, 0, 6, 0.09, 0.12);
    const R = 2.25;
    for (let i = 0; i < 8; i++) {
      const a = Math.PI + i * Math.PI / 4, sx = Math.sin(a), cz = Math.cos(a);
      chair(P, sx * R, cz * R, a, PASTEL[i]);
      P.box(PAL.white, 0.24, 0.012, 0.32, sx * 1.3, 0.695, cz * 1.3, 0.005, a + 0.15);
      if (i % 2) P.cyl(PASTEL[(i + 4) % 10], 0.045, 0.09, sx * 1.25 + cz * 0.3, 0.695, cz * 1.25 - sx * 0.3, 0.02);
      foot.push({ x: sx * R, z: cz * R, r: 0.28 });
      const ap = (da, rr) => [Math.sin(a + da) * rr, Math.cos(a + da) * rr];
      seats.push({ key: 'meet', x: sx * R, z: cz * R, y: 0.42, face: a + Math.PI, app: [ap(0, 3.05), ap(0.2, 3.0), ap(-0.2, 3.0), ap(0.39, 2.5), ap(-0.39, 2.5)] });
    }
    return { part: P, foot, seats };
  },
  whiteboard() {
    const P = new Part();
    P.box(PAL.grey, 3.5, 1.55, 0.07, 0, 0.72, 0, 0.035); P.box('#ffffff', 3.36, 1.41, 0.03, 0, 0.79, 0.03, 0.012);
    P.box(PAL.grey, 3.0, 0.05, 0.14, 0, 0.7, 0.08, 0.02);
    P.box(PAL.red, 0.14, 0.035, 0.035, -0.6, 0.75, 0.1, 0.015); P.box('#6fa8dc', 0.14, 0.035, 0.035, -0.35, 0.75, 0.1, 0.015); P.box(PAL.leafDark, 0.14, 0.035, 0.035, -0.1, 0.75, 0.1, 0.015);
    P.cyl(PAL.grey, 0.04, 0.75, -1.5, 0, 0, 0.01); P.cyl(PAL.grey, 0.04, 0.75, 1.5, 0, 0, 0.01);
    P.box(PAL.grey, 0.12, 0.05, 0.5, -1.5, 0, 0, 0.02); P.box(PAL.grey, 0.12, 0.05, 0.5, 1.5, 0, 0, 0.02);
    return { part: P, foot: [{ x: 0, z: 0, w: 3.5, d: 0.3 }], spots: [{ name: 'whiteboard', x: -1.3, z: 0.95, face: Math.PI }], whiteboard: { x: 0, y: 1.495, z: 0.05, w: 3.3, h: 1.35 } };
  },
  bookshelf(f) {
    const P = new Part(), r = rng(f.id);
    P.box(PAL.woodMid, 1.8, 1.7, 0.42, 0, 0, 0, 0.07); P.box(shade(PAL.woodMid, 0.5), 1.62, 1.5, 0.02, 0, 0.1, 0.205, 0.008);
    for (let s = 0; s < 3; s++) {
      const y = 0.1 + s * 0.5; P.box(PAL.wood, 1.64, 0.05, 0.1, 0, y + 0.44, 0.22, 0.02);
      let x = -0.76;
      while (x < 0.7) {
        const w = q(0.07 + r() * 0.07), h = q(0.26 + r() * 0.14);
        if (r() < 0.12) { x += 0.12; continue; }
        if (r() < 0.1) { P.sph(PASTEL[Math.floor(r() * 10)], 0.09, x + 0.09, y + 0.1, 0.25); x += 0.22; continue; }
        P.add(G.box(w, h, 0.2, 0.015, 1), PASTEL[Math.floor(r() * 10)], x + w / 2, y + h / 2 + 0.005, 0.22, 0, 0, r() < 0.15 ? 0.18 : 0); x += w + 0.012;
      }
    }
    return { part: P, foot: [{ x: 0, z: 0, w: 1.8, d: 0.42 }], spots: f.nospot ? [] : [{ name: f.spot || 'shelf', x: 0, z: 0.95, face: Math.PI }] };
  },
  cabinet(f) {
    const P = new Part(), c = '#bcd3e6';
    P.box(c, 0.95, 1.2, 0.5, 0, 0, 0, 0.07);
    for (let i = 0; i < 3; i++) { P.box(shade(c, 0.35), 0.8, 0.31, 0.03, 0, 0.1 + i * 0.36, 0.25, 0.02); P.box(PAL.white, 0.24, 0.04, 0.04, 0, 0.28 + i * 0.36, 0.275, 0.018); }
    P.box(PAL.white, 0.3, 0.02, 0.22, 0.1, 1.2, 0, 0.008, 0.3); P.cyl(PAL.pot, 0.07, 0.09, -0.25, 1.2, 0, 0.02); leaves(P, rng(f.id), -0.25, 1.36, 0, 3, 0.04, 0.07);
    return { part: P, foot: [{ x: 0, z: 0, w: 0.95, d: 0.5 }], spots: [{ name: f.spot || 'cabinet', x: 0, z: 0.95, face: Math.PI }] };
  },
  sofa(f) { return sofa(f, 1.9, 2); },
  armchair(f) { return sofa(f, 1.05, 1); },
  reserve_seat(f, ctx) {
    const o = sofa({ ...f, color: '#d8cfc0' }, 1.05, 1); const m = ctx.member(f.owner);
    o.part.box('#f7b0c6', 0.5, 0.05, 0.5, 0.1, 0.5, 0.05, 0.02, 0.2); o.part.sph(PAL.white, 0.16, -0.2, 0.62, -0.1, 1.2, 0.7, 0.8);
    const tp = textPlane([m ? m.nick : '後備', '留職停薪'], 0.6, 0.24, { pw: 256, bg: '#fffaf2', border: '#c9bca6', borderW: 8, px: 44, subScale: 0.55, radius: 22 });
    tp.position.set(0, 1.06, -0.2); o.extras = [tp]; o.seats[0].key = 'reserve';
    return o;
  },
  beanbag(f) {
    const P = new Part(), c = f.color || PAL.pink;
    P.sph(c, 0.52, 0, 0.27, 0, 1, 0.56, 1); P.sph(shade(c, 0.15), 0.36, 0, 0.42, -0.14, 1.1, 0.75, 0.9);
    return { part: P, foot: [{ x: 0, z: 0, r: 0.46 }], seats: [{ key: 'bean', x: 0, z: 0.06, y: 0.4, face: 0, app: [[0, 0.95], [0.95, 0], [-0.95, 0], [0, -0.95]] }] };
  },
  coffee_table(f) {
    const P = new Part(), r = rng(f.id);
    P.cyl(PAL.wood, 0.6, 0.07, 0, 0.34, 0, 0.03); P.cyl(PAL.cream, 0.2, 0.34, 0, 0, 0, 0.04, 0.12);
    P.cyl(PASTEL[Math.floor(r() * 10)], 0.05, 0.09, 0.25, 0.41, 0.1, 0.02); P.box(PASTEL[Math.floor(r() * 10)], 0.3, 0.025, 0.22, -0.15, 0.41, -0.1, 0.01, 0.4);
    P.cyl(PAL.pot, 0.07, 0.08, -0.05, 0.41, 0.28, 0.02); leaves(P, r, -0.05, 0.55, 0.28, 3, 0.04, 0.07);
    return { part: P, foot: [{ x: 0, z: 0, r: 0.6 }] };
  },
  side_table(f) {
    const P = new Part(), h = f.tall ? 0.95 : 0.5, r = rng(f.id);
    P.cyl(PAL.cream, 0.28, 0.04, 0, 0, 0, 0.015); P.cyl(PAL.cream, 0.06, h, 0, 0, 0, 0.01); P.cyl(PAL.wood, 0.5, 0.06, 0, h, 0, 0.025);
    if (f.tall) { P.cyl(PASTEL[2], 0.05, 0.1, 0.2, h + 0.06, 0.05, 0.02); P.cyl(PASTEL[0], 0.05, 0.1, -0.15, h + 0.06, -0.12, 0.02); }
    else { P.box(PASTEL[4], 0.34, 0.04, 0.26, 0, h + 0.06, 0, 0.012, 0.3); P.box(PASTEL[1], 0.3, 0.04, 0.24, 0.02, h + 0.1, 0, 0.012, -0.2); P.sph(PAL.red, 0.06, 0.24, h + 0.12, 0.22); }
    return { part: P, foot: [{ x: 0, z: 0, r: 0.5 }], spots: f.tall ? [{ name: 'chat', x: 0, z: 0.95, face: Math.PI }, { name: 'chat', x: 0.9, z: -0.3, face: -1.9 }, { name: 'chat', x: -0.9, z: -0.3, face: 1.9 }] : [{ name: 'read', x: 0, z: 0.95, face: Math.PI }] };
  },
  dining(f) {
    const P = new Part(), seats = [], foot = [{ x: 0, z: 0, r: 0.8 }], r = rng(f.id);
    P.cyl(PAL.cream, 0.32, 0.04, 0, 0, 0, 0.015); P.cyl(PAL.cream, 0.08, 0.62, 0, 0, 0, 0.01); P.cyl(PAL.white, 0.82, 0.07, 0, 0.62, 0, 0.03, 0.82, 28);
    P.cyl(PAL.peach, 0.2, 0.05, 0, 0.69, 0, 0.02, 0.26); for (let i = 0; i < 4; i++) P.sph([PAL.red, PAL.gold, '#ffb86b', PAL.leaf][i], 0.07, Math.cos(i * 1.6) * 0.09, 0.78, Math.sin(i * 1.6) * 0.09);
    for (let i = 0; i < 4; i++) {
      const a = Math.PI / 4 + i * Math.PI / 2, sx = Math.sin(a), cz = Math.cos(a), c = PASTEL[Math.floor(r() * 10)];
      P.cyl(PAL.cream, 0.2, 0.36, sx * 1.2, 0, cz * 1.2, 0.03, 0.16); P.cyl(c, 0.24, 0.09, sx * 1.2, 0.35, cz * 1.2, 0.04);
      P.cyl(PAL.white, 0.14, 0.018, sx * 0.52, 0.69, cz * 0.52, 0.008);
      foot.push({ x: sx * 1.2, z: cz * 1.2, r: 0.24 });
      seats.push({ key: 'dine', x: sx * 1.2, z: cz * 1.2, y: 0.44, face: a + Math.PI, app: [[sx * 1.95, cz * 1.95], [Math.sin(a + 0.4) * 1.8, Math.cos(a + 0.4) * 1.8], [Math.sin(a - 0.4) * 1.8, Math.cos(a - 0.4) * 1.8]] });
    }
    return { part: P, foot, seats };
  },
  counter(f) {
    const P = new Part();
    P.box(PAL.cream, 2.6, 0.86, 0.62, 0, 0, 0, 0.06); P.slab(PAL.wood, 2.72, 0.72, 0.06, 0, 0.85, 0, 0.1);
    for (let i = 0; i < 4; i++) { P.box(PAL.white, 0.56, 0.62, 0.03, -0.93 + i * 0.62, 0.12, 0.31, 0.03); P.sph(PAL.woodMid, 0.03, -0.75 + i * 0.62, 0.55, 0.335); }
    let spots;
    if (f.variant === 'coffee') {
      P.box('#f28b82', 0.46, 0.52, 0.4, -0.7, 0.91, -0.04, 0.07); P.box(PAL.ink, 0.3, 0.2, 0.06, -0.7, 1.0, 0.16, 0.02);
      P.cyl(PAL.white, 0.05, 0.08, -0.7, 0.93, 0.17, 0.015); P.cyl(PAL.grey, 0.1, 0.08, -0.7, 1.43, -0.04, 0.03); P.box(PAL.grey, 0.3, 0.03, 0.2, -0.7, 0.91, 0.16, 0.012);
      for (let i = 0; i < 3; i++) P.cyl([PAL.white, PAL.sky, PAL.yellow][i], 0.05, 0.09, -0.2 + i * 0.13, 0.91, -0.12, 0.02);
      P.cyl('#c9a27a', 0.09, 0.2, 0.35, 0.91, -0.08, 0.03); P.cyl(PAL.woodDark, 0.095, 0.03, 0.35, 1.11, -0.08, 0.012);
      P.cyl(PAL.mint, 0.11, 0.2, 0.75, 0.91, -0.05, 0.05, 0.08); P.cyl(PAL.white, 0.03, 0.05, 0.75, 1.11, -0.05, 0.01); P.box(PAL.white, 0.3, 0.02, 0.2, 1.05, 0.91, 0.05, 0.008);
      spots = [{ name: 'coffee', x: -0.7, z: 1.0, face: Math.PI }, { name: 'coffee', x: 0.1, z: 1.0, face: Math.PI }, { name: 'coffee', x: 0.9, z: 1.0, face: Math.PI }];
    } else {
      P.box(PAL.grey, 0.62, 0.36, 0.42, -0.65, 0.91, -0.04, 0.05); P.box('#7d8fb5', 0.38, 0.24, 0.02, -0.72, 0.97, 0.17, 0.01); P.cyl(PAL.white, 0.03, 0.02, -0.43, 1.0, 0.18, 0.008);
      P.box(PAL.yellow, 0.3, 0.2, 0.2, 0.05, 0.91, -0.05, 0.05); P.box(PAL.wood, 0.1, 0.06, 0.02, 0.0, 1.1, -0.05, 0.008); P.box(PAL.wood, 0.1, 0.06, 0.02, 0.1, 1.1, -0.05, 0.008);
      P.cyl(PAL.peach, 0.17, 0.07, 0.75, 0.91, 0, 0.03, 0.2); for (let i = 0; i < 5; i++) P.sph([PAL.red, PAL.gold, '#ffb86b', PAL.leaf, PAL.red][i], 0.07, 0.75 + Math.cos(i * 1.3) * 0.09, 1.02 + (i === 4 ? 0.06 : 0), Math.sin(i * 1.3) * 0.09);
      spots = [{ name: 'snack', x: -0.65, z: 1.0, face: Math.PI }, { name: 'snack', x: 0.6, z: 1.0, face: Math.PI }];
    }
    return { part: P, foot: [{ x: 0, z: 0, w: 2.72, d: 0.72 }], spots };
  },
  water() {
    const P = new Part();
    P.box(PAL.white, 0.46, 1.0, 0.42, 0, 0, 0, 0.07); P.cyl('#9fd6f2', 0.17, 0.42, 0, 1.0, 0, 0.07); P.cyl(PAL.white, 0.08, 0.05, 0, 1.4, 0, 0.02);
    P.box(PAL.grey, 0.3, 0.2, 0.04, 0, 0.6, 0.2, 0.02); P.sph(PAL.red, 0.03, -0.07, 0.72, 0.23); P.sph('#6fa8dc', 0.03, 0.07, 0.72, 0.23);
    P.box(PAL.grey, 0.3, 0.03, 0.12, 0, 0.5, 0.24, 0.012);
    return { part: P, foot: [{ x: 0, z: 0, w: 0.46, d: 0.42 }], spots: [{ name: 'water', x: 0, z: 0.9, face: Math.PI }] };
  },
  fridge() {
    const P = new Part(), c = '#bfe3d0';
    P.box(c, 0.95, 1.85, 0.78, 0, 0, 0, 0.12); P.box(shade(c, 0.3), 0.85, 0.55, 0.04, 0, 1.22, 0.38, 0.05); P.box(shade(c, 0.3), 0.85, 1.05, 0.04, 0, 0.1, 0.38, 0.05);
    P.box(PAL.white, 0.05, 0.3, 0.05, 0.32, 1.32, 0.42, 0.02); P.box(PAL.white, 0.05, 0.4, 0.05, 0.32, 0.65, 0.42, 0.02);
    P.box(PAL.yellow, 0.14, 0.14, 0.01, -0.2, 1.5, 0.405, 0.004, 0, 0, 0.15); P.box(PAL.pink, 0.12, 0.12, 0.01, -0.05, 1.36, 0.405, 0.004, 0, 0, -0.1);
    return { part: P, foot: [{ x: 0, z: 0, w: 0.95, d: 0.78 }], spots: [{ name: 'snack', x: 0, z: 1.1, face: Math.PI }] };
  },
  snack(f) {
    const P = new Part(), r = rng(f.id);
    P.box(PAL.cream, 1.6, 1.4, 0.46, 0, 0, 0, 0.07); P.box(shade(PAL.peach, 0.3), 1.44, 1.2, 0.02, 0, 0.1, 0.225, 0.008);
    for (let s = 0; s < 3; s++) {
      const y = 0.1 + s * 0.4; P.box(PAL.wood, 1.46, 0.045, 0.1, 0, y + 0.35, 0.24, 0.02);
      for (let i = 0; i < 6; i++) {
        const x = -0.6 + i * 0.24, c = PASTEL[Math.floor(r() * 10)], k = Math.floor(r() * 3);
        if (k === 0) P.cyl(c, 0.085, 0.2, x, y + 0.01, 0.25, 0.03); else if (k === 1) P.add(G.box(0.18, 0.24, 0.12, 0.03, 1), c, x, y + 0.13, 0.25); else P.sph(c, 0.09, x, y + 0.1, 0.25);
      }
    }
    return { part: P, foot: [{ x: 0, z: 0, w: 1.6, d: 0.46 }], spots: [{ name: 'snack', x: 0, z: 1.0, face: Math.PI }] };
  },
  pingpong() {
    const P = new Part();
    P.slab('#7fcfc0', 2.7, 1.5, 0.07, 0, 0.66, 0, 0.1); P.box(PAL.white, 0.03, 0.012, 1.44, 0, 0.726, 0, 0.004); P.box(PAL.white, 2.6, 0.012, 0.03, 0, 0.726, 0, 0.004);
    P.box(PAL.white, 0.03, 0.15, 1.56, 0, 0.73, 0, 0.012);
    for (const [x, z] of [[-1.05, -0.5], [1.05, -0.5], [-1.05, 0.5], [1.05, 0.5]]) P.cyl(PAL.cream, 0.06, 0.66, x, 0, z, 0.02);
    P.cyl(PAL.red, 0.09, 0.02, -0.9, 0.73, 0.3, 0.008); P.box(PAL.wood, 0.04, 0.02, 0.12, -0.9, 0.73, 0.44, 0.008); P.cyl('#6fa8dc', 0.09, 0.02, 0.9, 0.73, -0.3, 0.008); P.box(PAL.wood, 0.04, 0.02, 0.12, 0.9, 0.73, -0.44, 0.008);
    P.sph('#ffb86b', 0.035, 0.3, 0.765, 0.1);
    return { part: P, foot: [{ x: 0, z: 0, w: 2.7, d: 1.5 }], spots: [{ name: 'play', x: -2.05, z: 0, face: Math.PI / 2 }, { name: 'play', x: 2.05, z: 0, face: -Math.PI / 2 }] };
  },
  arcade(f) {
    const P = new Part(), c = f.color || '#cbb2f2';
    P.box(c, 0.82, 1.55, 0.72, 0, 0, 0, 0.1); P.box(PAL.yellow, 0.74, 0.22, 0.1, 0, 1.3, 0.33, 0.04);
    P.box('#5d6fb3', 0.62, 0.44, 0.05, 0, 0.8, 0.34, 0.03, 0, -0.18); P.box(shade(c, 0.3), 0.76, 0.09, 0.34, 0, 0.66, 0.44, 0.035, 0, 0.12);
    P.cyl(PAL.grey, 0.015, 0.1, -0.2, 0.74, 0.46, 0.005); P.sph(PAL.red, 0.045, -0.2, 0.86, 0.46); P.sph(PAL.gold, 0.035, 0.1, 0.77, 0.47); P.sph('#6fa8dc', 0.035, 0.22, 0.77, 0.47);
    P.sph(PAL.pink, 0.05, -0.12, 0.98, 0.37, 1, 1, 0.3); P.sph(PAL.yellow, 0.04, 0.12, 1.06, 0.36, 1, 1, 0.3);
    return { part: P, foot: [{ x: 0, z: 0.05, w: 0.82, d: 0.85 }], spots: [{ name: 'play', x: 0, z: 1.05, face: Math.PI }] };
  },
  plant(f) {
    const P = new Part(), r = rng(f.id), alt = r() < 0.5;
    P.cyl(alt ? PAL.potAlt : PAL.pot, 0.19, 0.3, 0, 0, 0, 0.05, 0.25); P.cyl('#a9825f', 0.2, 0.03, 0, 0.27, 0, 0.01);
    leaves(P, r, 0, 0.5, 0, 6, 0.16, 0.2);
    return { part: P, foot: [{ x: 0, z: 0, r: 0.24 }] };
  },
  plant_big(f) {
    const P = new Part(), r = rng(f.id);
    P.cyl(PAL.potAlt, 0.26, 0.42, 0, 0, 0, 0.07, 0.33); P.cyl('#a9825f', 0.27, 0.03, 0, 0.39, 0, 0.01); P.cyl(PAL.woodDark, 0.05, 0.6, 0, 0.4, 0, 0.01);
    leaves(P, r, 0, 1.1, 0, 8, 0.27, 0.34); P.sph(PAL.leafLight, 0.3, 0, 1.6, 0);
    return { part: P, foot: [{ x: 0, z: 0, r: 0.32 }] };
  },
  lamp() {
    const P = new Part();
    P.cyl(PAL.cream, 0.2, 0.05, 0, 0, 0, 0.02); P.cyl(PAL.woodMid, 0.025, 1.35, 0, 0.04, 0, 0.008);
    P.cyl('#fff0c2', 0.3, 0.34, 0, 1.32, 0, 0.06, 0.18);
    return { part: P, foot: [{ x: 0, z: 0, r: 0.2 }], glow: { y: 1.4 } };
  },
  board(f, ctx) {
    const P = new Part(), r = rng(f.id), w = f.small ? 1.5 : 2.0, col = f.owner === 'ceo' ? '#ffb86b' : (ctx.deptColor(f.owner) || PAL.wood);
    P.box(PAL.woodMid, w, 1.15, 0.09, 0, 0.72, 0, 0.06); P.box('#e9c69a', w - 0.16, 0.86, 0.03, 0, 0.78, 0.04, 0.02);
    P.cyl(PAL.woodMid, 0.045, 0.75, -w / 2 + 0.2, 0, 0, 0.01); P.cyl(PAL.woodMid, 0.045, 0.75, w / 2 - 0.2, 0, 0, 0.01);
    P.box(PAL.woodMid, 0.12, 0.05, 0.44, -w / 2 + 0.2, 0, 0, 0.02); P.box(PAL.woodMid, 0.12, 0.05, 0.44, w / 2 - 0.2, 0, 0, 0.02);
    const n = f.small ? 4 : 6, cw = (w - 0.3) / (f.small ? 2 : 3);
    for (let i = 0; i < n; i++) {
      const cx = -w / 2 + 0.15 + cw * (i % (n / 2) + 0.5), cy = 0.98 + Math.floor(i / (n / 2)) * 0.4, c = i === 0 ? shade(col, 0.2) : PASTEL[Math.floor(r() * 10)];
      P.box(c, q(cw * (0.62 + r() * 0.2)), q(0.24 + r() * 0.08), 0.012, cx + r() * 0.04, cy - 0.14, 0.058, 0.004, 0, 0, r() * 0.24 - 0.12);
      P.sph(PAL.red, 0.022, cx, cy + 0.12, 0.066);
    }
    const tp = textPlane(f.label || '佈告欄', w * 0.62, 0.2, { pw: 384, bg: '#fffaf2', border: col, borderW: 8, px: 50, radius: 30 });
    tp.position.set(0, 1.82, 0.05);
    return { part: P, extras: [tp], foot: [{ x: 0, z: 0, w, d: 0.3 }], spots: [{ name: 'board:' + f.owner, x: 0, z: 0.95, face: Math.PI }], board: f.owner };
  },
  deptsign(f) {
    const P = new Part();
    P.cyl(PAL.cream, 0.045, 1.0, -0.72, 0, 0, 0.01); P.cyl(PAL.cream, 0.045, 1.0, 0.72, 0, 0, 0.01);
    P.box(PAL.cream, 0.14, 0.05, 0.4, -0.72, 0, 0, 0.02); P.box(PAL.cream, 0.14, 0.05, 0.4, 0.72, 0, 0, 0.02);
    P.box(f.color, 1.9, 0.62, 0.1, 0, 0.95, 0, 0.05);
    const tp = textPlane(f.text, 1.74, 0.46, { pw: 512, bg: '#fffaf2', fg: '#5a4638', px: 84, radius: 40 });
    tp.position.set(0, 1.26, 0.056);
    const tb = new THREE.Mesh(tp.geometry, tp.material); tb.position.set(0, 1.26, -0.056); tb.rotation.y = Math.PI;   // 背面也有字（從北邊看過來也讀得到）
    return { part: P, extras: [tp, tb], foot: [{ x: 0, z: 0, w: 1.9, d: 0.26 }], deptsign: f.dept };
  },
  roomsign(f) {
    const P = new Part(), w = 0.5 + f.text.length * 0.3, y = f.stand ? 0.95 : (f.high ? 1.86 : 1.86);
    if (f.stand) { P.cyl(PAL.cream, 0.045, 1.0, -w / 2 + 0.25, 0, 0, 0.01); P.cyl(PAL.cream, 0.045, 1.0, w / 2 - 0.25, 0, 0, 0.01); }
    P.box(f.color, w, 0.56, 0.1, 0, y, 0, 0.05);
    const tp = textPlane(f.text, w - 0.14, 0.42, { pw: 384, bg: '#fffaf2', px: 70, radius: 36 });
    tp.position.set(0, y + 0.28, 0.056);
    return { part: P, extras: [tp], foot: f.stand ? [{ x: 0, z: 0, w, d: 0.2 }] : [], noshadow: !f.stand };
  },
  doormat() {
    const P = new Part(); P.slab('#e7b98c', 2.0, 1.0, 0.035, 0, 0.012, 0, 0.2, 0, 0.012); P.slab('#f6dcb8', 1.6, 0.6, 0.02, 0, 0.035, 0, 0.14, 0, 0.008);
    return { part: P, foot: [], flat: true };
  },
  door() {
    const P = new Part();
    P.box(PAL.woodMid, 0.34, 2.35, 0.44, -1.28, 0, 0, 0.1); P.box(PAL.woodMid, 0.34, 2.35, 0.44, 1.28, 0, 0, 0.1);
    P.box(PAL.woodMid, 3.0, 0.5, 0.48, 0, 2.2, 0, 0.16); P.sph(PAL.gold, 0.1, -1.28, 2.8, 0); P.sph(PAL.gold, 0.1, 1.28, 2.8, 0);
    const tp = textPlane('AI 辦公室', 1.9, 0.36, { pw: 512, bg: '#fffaf2', px: 70, radius: 36 });
    tp.position.set(0, 2.45, 0.245);
    return { part: P, extras: [tp], foot: [{ x: -1.28, z: 0, w: 0.34, d: 0.44 }, { x: 1.28, z: 0, w: 0.34, d: 0.44 }], fixed: true };
  },
  kiosk() {
    const P = new Part();
    P.cyl(PAL.cream, 0.2, 0.05, 0, 0, 0, 0.02); P.cyl(PAL.cream, 0.05, 1.0, 0, 0.04, 0, 0.01);
    P.box(PAL.sky, 0.46, 0.34, 0.1, 0, 0.98, 0.02, 0.05, 0, -0.3); P.box(PAL.white, 0.36, 0.22, 0.02, 0, 1.05, 0.065, 0.01, 0, -0.3);
    return { part: P, foot: [{ x: 0, z: 0, r: 0.22 }], spots: [{ name: 'clock', x: 0, z: 0.8, face: Math.PI }] };
  },
  bench() {
    const P = new Part();
    P.slab(PAL.wood, 1.7, 0.46, 0.08, 0, 0.36, 0, 0.14); P.box(PAL.cream, 0.1, 0.36, 0.36, -0.62, 0, 0, 0.04); P.box(PAL.cream, 0.1, 0.36, 0.36, 0.62, 0, 0, 0.04);
    P.box(PAL.pink, 0.4, 0.07, 0.36, -0.4, 0.44, 0, 0.03); P.box(PAL.mint, 0.4, 0.07, 0.36, 0.4, 0.44, 0, 0.03);
    return { part: P, foot: [{ x: 0, z: 0, w: 1.7, d: 0.46 }] };
  },
  rug(f) {
    const P = new Part(), c = f.color || PAL.peach;
    if (f.round && Math.abs(f.w - f.d) < 0.01) { P.cyl(c, f.w / 2, 0.03, 0, 0.01, 0, 0.012, f.w / 2, 44); P.cyl(shade(c, 0.4), f.w / 2 - 0.28, 0.012, 0, 0.034, 0, 0.005, f.w / 2 - 0.28, 44); }
    else { const rr = f.round ? Math.min(f.w, f.d) / 2 - 0.01 : 0.5; P.slab(c, f.w, f.d, 0.03, 0, 0.01, 0, rr, 0, 0.012); P.slab(shade(c, 0.4), f.w - 0.56, f.d - 0.56, 0.012, 0, 0.034, 0, Math.max(0.1, rr - 0.28), 0, 0.005); }
    return { part: P, foot: [], flat: true, w: f.w, d: f.d };
  }
};

function sofa(f, w, n) {
  const P = new Part(), c = f.color || PAL.pink, lt = shade(c, 0.25);
  P.box(c, w, 0.3, 0.86, 0, 0.08, 0, 0.1); P.box(c, w, 0.62, 0.26, 0, 0.28, -0.3, 0.12);
  P.box(c, 0.26, 0.44, 0.86, -w / 2 + 0.13, 0.2, 0, 0.11); P.box(c, 0.26, 0.44, 0.86, w / 2 - 0.13, 0.2, 0, 0.11);
  const sw = (w - 0.52) / n, seats = [];
  for (let i = 0; i < n; i++) {
    const x = -w / 2 + 0.26 + sw * (i + 0.5);
    P.box(lt, sw - 0.03, 0.17, 0.6, x, 0.34, 0.1, 0.07); P.box(lt, sw - 0.06, 0.36, 0.14, x, 0.46, -0.16, 0.065, 0, -0.18);
    if (!f.noseat) seats.push({ key: 'sofa', x, z: 0.12, y: 0.5, face: 0, app: [[x, 1.0], [x + 0.5, 1.1], [x - 0.5, 1.1]] });
  }
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) P.cyl(PAL.woodDark, 0.04, 0.09, sx * (w / 2 - 0.12), 0, sz * 0.34, 0.01);
  if (n > 1) P.box(PASTEL[(c.charCodeAt(2) + 3) % 10], 0.3, 0.3, 0.12, -w / 2 + 0.42, 0.5, 0.0, 0.055, 0.3, -0.25);
  return { part: P, foot: [{ x: 0, z: 0, w, d: 0.86 }], seats };
}

// 整修模式可新增的家具（顯示名稱）
export const CATALOG = {
  plant: '小盆栽', plant_big: '大盆栽', lamp: '立燈', sofa: '雙人沙發', armchair: '單人沙發', beanbag: '懶骨頭',
  coffee_table: '茶几', bookshelf: '書架', cabinet: '資料櫃', bench: '長凳'
};
