// 尋路：依佈局（牆＋家具佔地）產生可走格子，A* 找路，再把路徑拉直。
// block＝把障礙物外擴一個角色半徑後的格子（找路用）；solid＝障礙物本體（驗證「沒有穿牆穿家具」用）。
export const AGENT_R = 0.27;

export function createNav(layout) {
  const cs = layout.cell || 0.25, W = layout.size.w, D = layout.size.d;
  const ox = -1, oz = -1, nx = Math.ceil((W + 2) / cs), nz = Math.ceil((D + 11) / cs);   // 多留到 D+11：大門外的小路與無業遊民區
  let block = new Uint8Array(nx * nz), solid = new Uint8Array(nx * nz), reach = new Uint8Array(nx * nz);
  const idx = (i, j) => j * nx + i;
  const ci = x => Math.floor((x - ox) / cs), cj = z => Math.floor((z - oz) / cs);
  const cx = i => ox + (i + 0.5) * cs, cz = j => oz + (j + 0.5) * cs;
  const inb = (i, j) => i >= 0 && j >= 0 && i < nx && j < nz;

  function fillRect(g, x0, z0, x1, z1) {
    const i0 = Math.max(0, ci(x0 + 1e-6)), i1 = Math.min(nx - 1, ci(x1 - 1e-6)), j0 = Math.max(0, cj(z0 + 1e-6)), j1 = Math.min(nz - 1, cj(z1 - 1e-6));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const px = cx(i), pz = cz(j);
      if (px >= x0 && px <= x1 && pz >= z0 && pz <= z1) g[idx(i, j)] = 1;
    }
  }
  function fillCirc(g, x, z, r) {
    const i0 = Math.max(0, ci(x - r)), i1 = Math.min(nx - 1, ci(x + r)), j0 = Math.max(0, cj(z - r)), j1 = Math.min(nz - 1, cj(z + r));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) { const dx = cx(i) - x, dz = cz(j) - z; if (dx * dx + dz * dz <= r * r) g[idx(i, j)] = 1; }
  }

  // feet：[{x,z,w,d} | {x,z,r}]（世界座標）
  function rebuild(feet) {
    block.fill(0); solid.fill(0);
    // 建築物外面不能走（大門外的小路除外）
    for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
      const x = cx(i), z = cz(j);
      const inside = x > 0 && x < W && z > 0 && z < D, path = x > 19.2 && x < 21.8 && z >= D && z < D + 5, yard = (layout.walkAreas || []).some(a => x > a.x0 && x < a.x1 && z > a.z0 && z < a.z1);   // walkAreas：戶外可走的區域（無業遊民區與通往那裡的路）
      if (!inside && !path && !yard) { block[idx(i, j)] = 1; solid[idx(i, j)] = 1; }
    }
    const T = 0.125, R = AGENT_R + 0.05;
    for (const w of layout.walls) {
      const x0 = Math.min(w.x1, w.x2), x1 = Math.max(w.x1, w.x2), z0 = Math.min(w.z1, w.z2), z1 = Math.max(w.z1, w.z2);
      fillRect(solid, x0 - T, z0 - T, x1 + T, z1 + T); fillRect(block, x0 - T - R, z0 - T - R, x1 + T + R, z1 + T + R);
    }
    for (const f of feet) {
      if (f.r != null) { fillCirc(solid, f.x, f.z, f.r); fillCirc(block, f.x, f.z, f.r + R); }
      else { fillRect(solid, f.x - f.w / 2, f.z - f.d / 2, f.x + f.w / 2, f.z + f.d / 2); fillRect(block, f.x - f.w / 2 - R, f.z - f.d / 2 - R, f.x + f.w / 2 + R, f.z + f.d / 2 + R); }
    }
    // 從大門口往外擴散，標出「真的走得到」的格子；被家具圍死的小空隙不算
    reach.fill(0); const seed = idx(ci(W / 2 + 0.5), cj(D - 1.1)), stack = [seed];
    if (!block[seed]) { reach[seed] = 1; while (stack.length) { const k = stack.pop(), i = k % nx, j = (k - i) / nx; for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const ni = i + di, nj = j + dj; if (!inb(ni, nj)) continue; const nk = idx(ni, nj); if (block[nk] || reach[nk]) continue; reach[nk] = 1; stack.push(nk); } } }
    else reach.set(block.map(v => v ? 0 : 1));
  }
  const isFree = (x, z) => { const i = ci(x), j = cj(z); return inb(i, j) && !block[idx(i, j)]; };
  const isReach = (x, z) => { const i = ci(x), j = cj(z); return inb(i, j) && !!reach[idx(i, j)]; };
  const isSolid = (x, z) => { const i = ci(x), j = cj(z); return !inb(i, j) || !!solid[idx(i, j)]; };

  function nearestFree(x, z, maxR = 12) {
    const i0 = ci(x), j0 = cj(z); if (inb(i0, j0) && reach[idx(i0, j0)]) return { x, z };
    let best = null, bd = 1e9;
    for (let r = 1; r <= maxR; r++) {
      for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) {
        if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue;
        const i = i0 + di, j = j0 + dj; if (!inb(i, j) || !reach[idx(i, j)]) continue;
        const d = (cx(i) - x) ** 2 + (cz(j) - z) ** 2; if (d < bd) { bd = d; best = { x: cx(i), z: cz(j) }; }
      }
      if (best) return best;
    }
    return null;
  }
  function los(ax, az, bx, bz) {
    const d = Math.hypot(bx - ax, bz - az), n = Math.max(1, Math.ceil(d / (cs * 0.4)));
    for (let k = 0; k <= n; k++) { const t = k / n; if (!isFree(ax + (bx - ax) * t, az + (bz - az) * t)) return false; }
    return true;
  }

  const gS = new Float32Array(nx * nz), from = new Int32Array(nx * nz), stamp = new Uint32Array(nx * nz); let gen = 0;
  const DIRS = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, 1.4142], [1, -1, 1.4142], [-1, 1, 1.4142], [-1, -1, 1.4142]];
  function findPath(a, b) {
    const s = nearestFree(a.x, a.z), e = nearestFree(b.x, b.z); if (!s || !e) return null;
    const si = ci(s.x), sj = cj(s.z), ei = ci(e.x), ej = cj(e.z), sK = idx(si, sj), eK = idx(ei, ej);
    gen++; const hk = [], hf = [];
    const push = (k, f) => { hk.push(k); hf.push(f); let c = hk.length - 1; while (c > 0) { const p = (c - 1) >> 1; if (hf[p] <= hf[c]) break; [hk[p], hk[c]] = [hk[c], hk[p]]; [hf[p], hf[c]] = [hf[c], hf[p]]; c = p; } };
    const pop = () => { const top = hk[0], lk = hk.pop(), lf = hf.pop(); if (hk.length) { hk[0] = lk; hf[0] = lf; let p = 0; for (;;) { let l = p * 2 + 1, r = l + 1, m = p; if (l < hk.length && hf[l] < hf[m]) m = l; if (r < hk.length && hf[r] < hf[m]) m = r; if (m === p) break; [hk[p], hk[m]] = [hk[m], hk[p]]; [hf[p], hf[m]] = [hf[m], hf[p]]; p = m; } } return top; };
    const h = (i, j) => { const dx = Math.abs(i - ei), dz = Math.abs(j - ej); return (dx + dz) + (1.4142 - 2) * Math.min(dx, dz); };
    const done = new Set();
    gS[sK] = 0; from[sK] = -1; stamp[sK] = gen; push(sK, h(si, sj));
    let found = false;
    while (hk.length) {
      const k = pop(); if (k === eK) { found = true; break; }
      if (done.has(k)) continue; done.add(k);
      const i = k % nx, j = (k - i) / nx, g0 = gS[k];
      for (const [di, dj, c] of DIRS) {
        const ni = i + di, nj = j + dj; if (!inb(ni, nj)) continue; const nk = idx(ni, nj); if (block[nk]) continue;
        if (di && dj && (block[idx(i + di, j)] || block[idx(i, j + dj)])) continue;
        const g = g0 + c; if (stamp[nk] === gen && g >= gS[nk]) continue;
        stamp[nk] = gen; gS[nk] = g; from[nk] = k; push(nk, g + h(ni, nj));
      }
    }
    if (!found) return null;
    const cells = []; for (let k = eK; k !== -1; k = from[k]) cells.push(k); cells.reverse();
    const pts = cells.map(k => ({ x: cx(k % nx), z: cz((k - k % nx) / nx) }));
    pts[0] = { x: s.x, z: s.z }; if (isReach(b.x, b.z)) pts[pts.length - 1] = { x: b.x, z: b.z };
    // 拉直：能直線走到的中間點都省掉
    const out = [pts[0]]; let a0 = 0;
    while (a0 < pts.length - 1) {
      let far = a0 + 1;
      for (let t = Math.min(pts.length - 1, a0 + 60); t > a0 + 1; t--) if (los(pts[a0].x, pts[a0].z, pts[t].x, pts[t].z)) { far = t; break; }
      out.push(pts[far]); a0 = far;
    }
    return out;
  }
  const pathLength = p => { let d = 0; for (let i = 1; i < p.length; i++) d += Math.hypot(p[i].x - p[i - 1].x, p[i].z - p[i - 1].z); return d; };
  // 驗證用：沿路每 5 公分取樣，回報有幾個點落在障礙物本體裡
  function pathHits(p) { let hits = 0; for (let i = 1; i < p.length; i++) { const d = Math.hypot(p[i].x - p[i - 1].x, p[i].z - p[i - 1].z), n = Math.max(1, Math.ceil(d / 0.05)); for (let k = 0; k <= n; k++) { const t = k / n; if (isSolid(p[i - 1].x + (p[i].x - p[i - 1].x) * t, p[i - 1].z + (p[i].z - p[i - 1].z) * t)) hits++; } } return hits; }

  return { rebuild, isFree, isReach, isSolid, nearestFree, findPath, los, pathLength, pathHits, cs, nx, nz, ox, oz, get block() { return block; } };
}

// 家具佔地：區域座標 → 世界座標（rot 是 90 度的倍數）
export function footToWorld(f, foot) {
  const k = ((f.rot % 4) + 4) % 4, c = [1, 0, -1, 0][k], s = [0, 1, 0, -1][k];
  return foot.map(o => {
    const x = f.x + o.x * c + o.z * s, z = f.z - o.x * s + o.z * c;
    return o.r != null ? { x, z, r: o.r } : { x, z, w: k % 2 ? o.d : o.w, d: k % 2 ? o.w : o.d };
  });
}
export function localToWorld(f, x, z) {
  const k = ((f.rot % 4) + 4) % 4, c = [1, 0, -1, 0][k], s = [0, 1, 0, -1][k];
  return { x: f.x + x * c + z * s, z: f.z - x * s + z * c };
}
