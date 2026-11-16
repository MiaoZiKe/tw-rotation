// 戶外景觀（2026-11-16）：依「辦公室實際範圍」在外圍擺一圈灌木、花叢、樹（圓冠樹、松樹）、石頭、小草，外加 1～2 個小湖泊。
//
// 擁有者原話：「灌木叢留下好了，依據範圍擴大，旁邊多點植物、樹、湖泊等等，這是設定在每個專案都要」。
//   · 所有專案都有：tw-rotation 完整辦公室、區塊辦公室（新專案）、示範模式。
//   · 範圍變大（新 Agent 長出區塊、鋪面往外長）時，景觀跟著往外：沿用同一套「世界格子雜湊」——每個格子該放什麼只由格子座標決定，
//     所以範圍一變，被新鋪面蓋到的格子消失、外面的格子補長，沒被動到的樹原地不動（不是整片亂數重排）。
// 不可以壓到的地方（exclusion）：地板鋪面、每個房間／區塊、運動場、無業遊民區、大門外的步道與路燈長椅、湖泊本身。
// 效能：全部合併成一個網格（只在範圍改變時重建），物件數有上限（MAX_OBJ）；不投影、不可被點選（raycast 關掉）、不進尋路（外面本來就不是可走區）。
// 湖泊目前只當景觀：戶外不是可走區（尋路本來就擋掉），被燒的人沒有路可以走到湖邊，所以沒有接水源選擇（mind_feel.js 仍是辦公室飲水機／泳池）。
import { THREE, G, Part, PAL, shade } from './kit.js';

const CELL = 2.4, RING = 13, MAX_OBJ = 300, PAD = 0.7;
const LEAF = ['#8fd19e', '#7cc68c', '#a8dba0', '#b7e3a4'], PINE = ['#6fb98a', '#5fa87a', '#7cc29a'], FLOWER = ['#ffb3c1', '#fff0a8', '#ffffff', '#ffc9a3', '#d9cdf2'];

// 格子雜湊：同一個 (i,j,k) 永遠同一個 0..1 的數
const H = (i, j, k) => { let x = Math.imul(i | 0, 374761393) ^ Math.imul(j | 0, 668265263) ^ Math.imul(k | 0, 1274126177); x = Math.imul(x ^ (x >>> 13), 1103515245); x ^= x >>> 16; return (x >>> 0) / 4294967296; };

export function createScenery(W) {
  const scene = W.scene, Lw = W.layout.size.w, Ld = W.layout.size.d, blocks = !!W.blocks;
  const S = { count: 0, objs: [], lakes: [], rects: [], bbox: null, mesh: null, key: '', max: MAX_OBJ };

  /** 不能壓到的矩形（世界座標）：地板鋪面、房間／區塊、運動場、無業遊民區、大門外步道 */
  function exclusions() {
    const R = [];
    if (blocks && W.blocks) { const f = W.blocks.floor(); R.push({ x0: f.x0, x1: f.x1, z0: f.z0, z1: f.z1, k: 'floor' }); }
    else R.push({ x0: -1.5, x1: Lw + 1.5, z0: -1.5, z1: Ld + 1.5, k: 'floor' });    // 完整辦公室：40×30 加外圈鋪面
    for (const r of W.layout.rooms) R.push({ x0: r.x, x1: r.x + r.w, z0: r.z, z1: r.z + r.d, k: 'room' });
    if (!blocks) R.push({ x0: 0.7, x1: 19.0, z0: 31.7, z1: 48.2, k: 'sports' });      // 員工運動場（sports_build.js 的 field）
    const z = W.outside && W.outside.zone; if (z) R.push({ x0: z.x0 - 1.2, x1: z.x1 + 1.2, z0: z.z0 - 1.2, z1: z.z1 + 1.2, k: 'jobless' });
    R.push({ x0: 15.6, x1: 24.4, z0: Ld - 1.2, z1: Ld + 9.5, k: 'gate' });             // 大門外：踏石、路燈、信箱、長椅
    return R;
  }
  const rectDist = (r, x, z) => Math.hypot(Math.max(r.x0 - x, 0, x - r.x1), Math.max(r.z0 - z, 0, z - r.z1));
  const inLake = (L, x, z, m) => { const dx = (x - L.x) / (L.rx + m), dz = (z - L.z) / (L.rz + m); return dx * dx + dz * dz < 1; };

  function lakesFor(R) {
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; for (const r of R) { x0 = Math.min(x0, r.x0); x1 = Math.max(x1, r.x1); z0 = Math.min(z0, r.z0); z1 = Math.max(z1, r.z1); }
    S.bbox = { x0, x1, z0, z1 };
    const h = z1 - z0, A = { rx: 5.2, rz: 3.5 }, B = { rx: 3.4, rz: 2.6 };
    // 西邊一個大湖、東北邊一個小湖；跟著包圍盒往外移（範圍變大時它們一起往外搬，不會被鋪面蓋到）
    return [{ ...A, x: x0 - 2.6 - A.rx, z: z0 + h * 0.36 }, { ...B, x: x1 + 2.4 + B.rx, z: z0 + h * 0.28 }];
  }

  function build() {
    const R = exclusions(), key = JSON.stringify(R.map(r => [r.x0, r.x1, r.z0, r.z1].map(v => Math.round(v * 10))));
    if (key === S.key) return false; S.key = key; S.rects = R;
    const lakes = lakesFor(R), P = new Part(), objs = [], old = W.decoOld || [];
    const gi0 = Math.floor((S.bbox.x0 - RING) / CELL), gi1 = Math.ceil((S.bbox.x1 + RING) / CELL), gj0 = Math.floor((S.bbox.z0 - RING) / CELL), gj1 = Math.ceil((S.bbox.z1 + RING) / CELL);
    const cand = [];
    for (let j = gj0; j <= gj1; j++) for (let i = gi0; i <= gi1; i++) {
      const x = (i + 0.15 + H(i, j, 1) * 0.7) * CELL, z = (j + 0.15 + H(i, j, 2) * 0.7) * CELL;
      let dm = 1e9; for (const r of R) dm = Math.min(dm, rectDist(r, x, z)); if (dm > RING) continue;
      const near = dm < 3.4, t = H(i, j, 3);
      const p = near ? 0.78 : 0.62 - (dm - 3.4) / (RING - 3.4) * 0.34; if (H(i, j, 4) > p) continue;
      let kind, r;
      if (near) { kind = t < 0.42 ? 'bush' : t < 0.74 ? 'flower' : t < 0.88 ? 'grass' : t < 0.96 ? 'rock' : 'bush'; }
      else kind = t < 0.26 ? 'tree' : t < 0.46 ? 'pine' : t < 0.64 ? 'bush' : t < 0.78 ? 'flower' : t < 0.88 ? 'grass' : t < 0.95 ? 'rock' : 'tree';
      r = { tree: 1.7, pine: 1.3, bush: 0.75, flower: 0.6, grass: 0.35, rock: 0.5 }[kind] * (0.85 + H(i, j, 5) * 0.4);
      // 不壓到任何東西：離每個排除範圍至少 PAD＋自身半徑，不在湖裡（含岸邊），不貼近舊的散落樹
      if (R.some(q => rectDist(q, x, z) < PAD + r * (kind === 'tree' || kind === 'pine' ? 0.8 : 0.5))) continue;
      if (lakes.some(L => inLake(L, x, z, r + 1.0))) continue;
      if (old.some(o => Math.hypot(o.x - x, o.z - z) < o.r + r + 0.6)) continue;
      cand.push({ kind, x, z, r, dm, i, j });
    }
    cand.sort((a, b) => a.dm - b.dm); const keep = cand.slice(0, MAX_OBJ);
    for (const c of keep) {
      const { kind, x, z, r, i, j } = c, a = H(i, j, 6) * 6.283, s = r / { tree: 1.7, pine: 1.3, bush: 0.75, flower: 0.6, grass: 0.35, rock: 0.5 }[kind];
      if (kind === 'tree') {
        const h = (1.5 + H(i, j, 7) * 1.1) * s, cr = r * 0.85, col = LEAF[(i + j & 3)];
        P.add(G.cyl(0.24 * s, h, 0.04, 8), PAL.woodDark, x, 0, z); P.add(G.sph(cr, 8, 6), col, x, h + cr * 0.6, z, 0, 0, 0, 1, 0.92, 1);
        P.add(G.sph(cr * 0.62, 7, 5), shade(col, 0.16), x + cr * 0.5, h + cr * 0.32, z + cr * 0.25); P.add(G.sph(cr * 0.5, 7, 5), shade(col, -0.08), x - cr * 0.45, h + cr * 0.4, z - cr * 0.2);
      } else if (kind === 'pine') {
        const h = (1.0 + H(i, j, 7) * 0.7) * s, col = PINE[(i + j) % 3];
        P.add(G.cyl(0.2 * s, h, 0.03, 8), PAL.woodDark, x, 0, z);
        for (let k = 0; k < 3; k++) P.add(G.cyl((1.15 - k * 0.3) * s, 1.15 * s, 0.05, 9, 0.05), shade(col, k * 0.07), x, h * 0.75 + k * 0.78 * s, z);
      } else if (kind === 'bush') {
        const col = LEAF[(i * 3 + j) & 3]; P.add(G.sph(r * 0.8, 8, 6), col, x, r * 0.3, z, 0, 0, 0, 1.25, 0.8, 1); P.add(G.sph(r * 0.5, 7, 5), shade(col, 0.14), x + r * 0.45, r * 0.25, z + r * 0.2);
        if (H(i, j, 8) < 0.4) P.add(G.sph(0.09, 6, 5), FLOWER[(i + j) % 5], x - r * 0.2, r * 0.62, z + r * 0.35);
      } else if (kind === 'flower') {
        P.add(G.sph(r * 0.55, 7, 5), PAL.leafDark, x, 0.1, z, 0, 0, 0, 1.3, 0.45, 1);
        for (let k = 0; k < 6; k++) { const aa = a + k * 1.05, dd = r * (0.15 + 0.4 * H(i, j, 9 + k)); P.add(G.sph(0.1, 6, 5), FLOWER[(i + j + k) % 5], x + Math.cos(aa) * dd, 0.26, z + Math.sin(aa) * dd); }
      } else if (kind === 'grass') {
        for (let k = 0; k < 4; k++) { const aa = a + k * 1.6, dd = 0.14 + 0.1 * k % 3; P.add(G.cyl(0.07, 0.5 + 0.1 * k, 0.01, 5, 0.01), k % 2 ? '#9edb94' : '#8fd19e', x + Math.cos(aa) * dd, 0, z + Math.sin(aa) * dd, 0, 0, 0); }
      } else {
        const g = H(i, j, 7) < 0.5 ? '#cfd3d6' : '#bfc4c9'; P.add(G.sph(r * 0.7, 8, 6), g, x, r * 0.22, z, 0, 0, 0, 1.2, 0.62, 1); if (H(i, j, 8) < 0.5) P.add(G.sph(r * 0.38, 7, 5), shade(g, 0.1), x + r * 0.7, r * 0.12, z + r * 0.2, 0, 0, 0, 1.1, 0.6, 1);
      }
      objs.push({ kind, x, z, r });
    }
    // 湖泊：沙色岸 → 水面 → 淺色水心 → 岸邊石頭 → 荷葉
    for (let li = 0; li < lakes.length; li++) {
      const L = lakes[li]; P.add(G.cyl(1, 0.05, 0.015, 36), '#f3e2b8', L.x, -0.01, L.z, 0, 0, 0, L.rx + 0.7, 1, L.rz + 0.7);
      P.add(G.cyl(1, 0.06, 0.015, 36), '#8ed2e4', L.x, 0.0, L.z, 0, 0, 0, L.rx, 1, L.rz); P.add(G.cyl(1, 0.02, 0.008, 30), '#b9e6f0', L.x - 0.15, 0.058, L.z, 0, 0, 0, L.rx * 0.62, 1, L.rz * 0.6);
      const ns = li ? 9 : 13; for (let k = 0; k < ns; k++) { const aa = (k + H(li, k, 20) * 0.7) / ns * 6.283, rr = 0.2 + H(li, k, 21) * 0.28; P.add(G.sph(rr, 7, 5), H(li, k, 22) < 0.5 ? '#cfd3d6' : '#b9bec4', L.x + Math.cos(aa) * (L.rx + 0.45), rr * 0.3, L.z + Math.sin(aa) * (L.rz + 0.45), 0, 0, 0, 1.2, 0.65, 1); }
      for (let k = 0; k < (li ? 3 : 5); k++) { const aa = H(li, k, 23) * 6.283, d = 0.25 + H(li, k, 24) * 0.45, px = L.x + Math.cos(aa) * L.rx * d, pz = L.z + Math.sin(aa) * L.rz * d; P.add(G.cyl(0.34, 0.02, 0.005, 12), '#7fcf8e', px, 0.062, pz); if (k % 2 === 0) P.add(G.sph(0.1, 6, 5), '#ffb3c1', px + 0.05, 0.1, pz); }
      objs.push({ kind: 'lake', x: L.x, z: L.z, r: Math.max(L.rx, L.rz), rx: L.rx, rz: L.rz });
    }
    const m = P.mesh(); m.castShadow = false; m.receiveShadow = false; m.raycast = () => { }; m.name = 'scenery';
    if (S.mesh) { S.mesh.geometry.dispose(); S.mesh.removeFromParent(); } S.mesh = m; scene.add(m);
    S.lakes = lakes; S.objs = objs; S.count = objs.length; W.outdoorDeco = (W.decoCount || 0) + S.count;
    return true;
  }
  S.update = build; build();
  return S;
}
