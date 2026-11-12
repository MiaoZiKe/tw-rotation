// 頭髮：頭皮底層＋一束一束有層次的立體髮束（沿頭型曲面掃掠，髮尾收尖、可外翹）
import { THREE, softMat, dirSurface, sweepGeo, paint, canvasTex, clamp, lerp, sstep, C, mergeGeos } from './core.js';

const V3 = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const PI = Math.PI;
const dirOf = (az, y) => { const r = Math.sqrt(Math.max(0, 1 - y * y)); return V3(Math.sin(az) * r, y, Math.cos(az) * r); }; // az：0＝正前，±π＝正後
const slerp = (a, b, t, out) => { const dot = clamp(a.dot(b), -1, 1), th = Math.acos(dot); if (th < 1e-4) return out.copy(a); const s = Math.sin(th); return out.copy(a).multiplyScalar(Math.sin((1 - t) * th) / s).addScaledVector(b, Math.sin(t * th) / s); };

let _streak;
const streakTex = () => _streak || (_streak = (() => { const t = canvasTex(128, 16, (c) => { c.fillStyle = '#dcdcdc'; c.fillRect(0, 0, 128, 16); let s = 5; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647; for (let i = 0; i < 46; i++) { const x = rnd() * 128, v = rnd(); c.fillStyle = v > 0.5 ? `rgba(255,255,255,${0.15 + 0.3 * rnd()})` : `rgba(110,110,110,${0.08 + 0.2 * rnd()})`; c.fillRect(x, 0, 1 + rnd() * 2.5, 16); } }); t.wrapS = t.wrapT = THREE.RepeatWrapping; return t; })());

// 髮線：依方位角給出「這個方向的頭髮長到哪個高度」
const LINES = {
  short: (az) => { const a = Math.abs(az); return lerp(lerp(0.5, 0.2, sstep(0.45, 1.25, a)), -0.42, sstep(1.75, 2.7, a)); },
  bob: (az) => { const a = Math.abs(az); return lerp(lerp(0.5, 0.26, sstep(0.4, 0.95, a)), -0.62, sstep(1.0, 1.75, a)); },
};

export function buildHair(skull, fn, style, col) {
  const g = new THREE.Group(); skull.add(g); const springs = [];
  const base = C(col.c), hi = C(col.hi), dk = C(col.c).multiplyScalar(0.72);
  const mat = softMat(0xffffff, { vc: true, map: streakTex(), rough: 0.46, rimStr: 0.55, rimPow: 2.2, rim: col.rim ?? 0xffe9d2 });
  const line = LINES[style.line || 'short'];
  // 頭皮底層：比頭型略大一圈，髮線以下縮進頭裡
  const cap = dirSurface((d, p) => { fn(d, p); const m = d.y - line(Math.atan2(d.x, d.z)); p.multiplyScalar(lerp(0.9, 1.05 + (style.vol ?? 0.05) * sstep(0.2, 1, d.y), sstep(-0.03, 0.05, m))); }, { w: 96, h: 64 });
  paint(cap, (p, n, c) => c.copy(dk).lerp(base, Math.max(sstep(-0.1, 0.25, p.y), sstep(0, 0.12, p.z))));
  const capM = new THREE.Mesh(cap, softMat(0xffffff, { vc: true, rough: 0.7, rimStr: 0.4, rim: col.rim ?? 0xffe9d2 })); capM.castShadow = true; g.add(capM);

  // 一束：從 a 方向沿頭型到 b 方向；lift 中段蓬起、tip 髮尾外翹（負值內彎）、side 中段往旁邊甩
  const p = V3(), d = V3(), bag = [];
  const strand = (a, b, o = {}, parent = g) => {
    const pts = [], n = o.n ?? 7, lift = o.lift ?? 0.03, tip = o.tip ?? 0.03, r0 = o.r0 ?? 1.02, sd = o.side ?? 0, up = o.up ?? 0;
    const sideV = V3().crossVectors(a, b).normalize();
    for (let i = 0; i < n; i++) {
      const t = i / (n - 1) * (o.len ?? 1); slerp(a, b, t, d); if (sd) d.addScaledVector(sideV, sd * Math.sin(PI * Math.min(1, t))).normalize(); fn(d, p);
      const k = r0 + lift * Math.sin(PI * Math.min(1, t)) ** 0.8 + tip * Math.max(0, t) ** 3;
      p.multiplyScalar(k); p.y += up * t * t; if (o.off) p.addScaledVector(o.off, t * t); pts.push(p.clone());
    }
    const w = o.w ?? 0.06, th = o.th ?? 0.02;
    const geo = sweepGeo(pts, (t) => { const k = Math.sin(PI * clamp(0.1 + 0.9 * t)) ** (o.pw ?? 0.55) * (t < 0.12 ? 0.55 + 0.45 * t / 0.12 : 1); return [w * k, th * (0.45 + 0.55 * k)]; }, { rows: Math.round((o.rows ?? 16) * 1.6), seg: 18, under: 0.3, nrm: (q, t, out) => out.copy(q).normalize() });
    const sh = o.shade ?? 0;
    paint(geo, (q, nn, c) => { c.copy(base).lerp(hi, 0.4 * sstep(-0.3, 0.9, nn.y) + sh).lerp(dk, 0.3 * sstep(0.2, -0.8, nn.y)); });
    const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 2.0 + (o.seed ?? 0) * 0.37, uv.getY(i));
    if (parent === g) { bag.push(geo); return null; }
    const m = new THREE.Mesh(geo, mat); m.castShadow = true; parent.add(m); return m;
  };

  if (style.kind === 'tuft') { // 蓬鬆短髮：外層大片髮束髮尾微翹、上層較短、左右分開的瀏海、頭頂一撮翹起的呆毛
    const crown = dirOf(PI, 0.95).normalize();
    for (let i = 0; i < 8; i++) { const az = lerp(1.0, 2 * PI - 1.0, i / 7) + 0.06 * Math.sin(i * 2.3), a = az > PI ? az - 2 * PI : az; strand(crown, dirOf(a, line(a) - 0.16 - 0.06 * (i % 2)), { w: 0.125, th: 0.036, lift: 0.045, tip: 0.09 + 0.04 * (i % 3), r0: 1.04, seed: i, rows: 20, n: 8 }); }
    for (let i = 0; i < 6; i++) { const az = lerp(0.75, 2 * PI - 0.75, i / 5) + 0.1 * Math.cos(i * 1.7), a = az > PI ? az - 2 * PI : az; strand(crown, dirOf(a, 0.34 - 0.14 * Math.abs(Math.sin(a))), { w: 0.12, th: 0.04, lift: 0.085, tip: 0.1, r0: 1.075, seed: i + 20, shade: 0.1, rows: 18 }); }
    const top = dirOf(0.3, 0.955).normalize();
    for (const [az, y, sd, w, tp] of [[-0.98, 0.22, -0.1, 0.085, 0.085], [-0.56, 0.33, -0.2, 0.1, 0.05], [-0.12, 0.44, -0.26, 0.078, 0.07], [0.28, 0.41, 0.22, 0.085, 0.05], [0.7, 0.3, 0.2, 0.098, 0.06], [1.04, 0.2, 0.08, 0.082, 0.09]])
      strand(top, dirOf(az, y), { w, th: 0.036, lift: 0.1, tip: tp, side: sd, r0: 1.07, seed: az * 9, shade: 0.14, rows: 20, n: 8 });
    const ah = new THREE.Group(); const root = V3(); fn(dirOf(0.2, 0.97).normalize(), root); ah.position.copy(root).multiplyScalar(1.07); g.add(ah);
    for (const [dx, h, bend, w] of [[0.0, 0.1, 0.07, 0.036], [-0.04, 0.066, -0.06, 0.028]]) {
      const pts = [V3(dx, -0.03, -0.01), V3(dx * 1.2, h * 0.5, -0.02), V3(dx * 1.4 + bend * 0.3, h * 0.92, 0.0), V3(dx * 1.5 + bend, h, 0.04)];
      const geo = sweepGeo(pts, (t) => { const k = Math.sin(PI * clamp(0.16 + 0.84 * t)) ** 0.6; return [w * k, 0.014 * k + 0.003]; }, { rows: 24, seg: 16, nrm: (q, t, out) => out.set(0, 0.2, 1) });
      paint(geo, (q, nn, c) => c.copy(base).lerp(hi, 0.3 + 0.3 * sstep(0, 0.1, q.y))); const m = new THREE.Mesh(geo, mat); ah.add(m);
    }
    springs.push([ah, 0.1, { k: 170, c: 7, acc: 2.6 }]);
  } else if (style.kind === 'bob') { // 及肩短鮑伯：兩側與後面往內收、齊瀏海、後腦一顆小馬尾
    const crown = dirOf(PI, 0.96).normalize();
    for (let i = 0; i < 13; i++) { const az = lerp(0.98, 2 * PI - 0.98, i / 12), a = az > PI ? az - 2 * PI : az, side = 1 - sstep(1.2, 2.4, Math.abs(a)); strand(crown, dirOf(a, -0.74 + 0.06 * (i % 2) - 0.05 * side), { w: 0.1, th: 0.03, lift: 0.045, tip: -0.035 - 0.03 * side, r0: 1.03, seed: i, rows: 22, n: 9, pw: 0.4 }); }
    for (let i = 0; i < 8; i++) { const az = lerp(0.8, 2 * PI - 0.8, i / 7), a = az > PI ? az - 2 * PI : az; strand(crown, dirOf(a, -0.2 - 0.1 * (i % 2)), { w: 0.095, th: 0.03, lift: 0.07, tip: 0.02, r0: 1.05, seed: i + 30, shade: 0.12, rows: 18 }); }
    const top = dirOf(0, 0.92).normalize();
    for (const [az, y, sd, w] of [[-0.82, 0.2, -0.05, 0.07], [-0.52, 0.27, 0.06, 0.07], [-0.24, 0.3, 0.1, 0.064], [0.04, 0.3, 0.12, 0.06], [0.32, 0.29, 0.1, 0.066], [0.6, 0.24, 0.06, 0.07], [0.86, 0.18, 0.02, 0.066]])
      strand(top, dirOf(az, y), { w, th: 0.026, lift: 0.05, tip: -0.012, side: sd, r0: 1.045, seed: az * 7, shade: 0.15, rows: 18, pw: 0.42 });
    // 側邊兩撮較長的鬢髮
    for (const s of [1, -1]) strand(dirOf(s * 0.5, 0.86).normalize(), dirOf(s * 1.02, -0.62), { w: 0.05, th: 0.02, lift: 0.03, tip: 0.035, r0: 1.045, seed: s, shade: 0.1, rows: 20, n: 8 });
    // 小馬尾（彈簧擺動）
    const pt = new THREE.Group(); const root = V3(); fn(dirOf(PI, 0.52).normalize(), root); pt.position.copy(root).multiplyScalar(1.06); g.add(pt);
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.03, 0.012, 10, 24), softMat(col.band ?? '#ff8fa8')); band.rotation.x = 0.9; pt.add(band);
    for (const [dx, w, l] of [[0, 0.05, 0.19], [0.03, 0.036, 0.16], [-0.03, 0.036, 0.165]]) {
      const pts = [V3(dx * 0.3, 0.0, 0.0), V3(dx, 0.03, -0.055), V3(dx * 1.4, -0.03, -0.1), V3(dx * 1.6, -l * 0.7, -0.105), V3(dx * 1.2, -l, -0.07)];
      const geo = sweepGeo(pts, (t) => { const k = Math.sin(PI * clamp(0.1 + 0.9 * t)) ** 0.5; return [w * k, w * 0.6 * k + 0.003]; }, { rows: 28, seg: 16, nrm: (q, t, out) => out.set(0, 0.3, -1) });
      paint(geo, (q, nn, c) => c.copy(base).lerp(hi, 0.35 * sstep(-0.2, 0.8, -nn.z))); const m = new THREE.Mesh(geo, mat); m.castShadow = true; pt.add(m);
    }
    springs.push([pt, 0.16, { k: 110, c: 7, acc: 2.2, axis: V3(0, -0.6, -0.8) }]);
  } else if (style.kind === 'part') { // 中分微捲：從分線往兩側披下、髮尾外翹，後面較短
    for (const s of [1, -1]) {
      for (let i = 0; i < 6; i++) { const z = lerp(0.42, -0.75, i / 5), a0 = V3(s * 0.05, 0.96, z * 0.6).normalize(), az = s * lerp(0.62, 2.5, i / 5); strand(a0, dirOf(az, lerp(-0.12, -0.5, sstep(0, 5, i)) - 0.06 * (i % 2)), { w: 0.095, th: 0.03, lift: 0.07, tip: 0.085, r0: 1.035, seed: i + s * 3, rows: 20, n: 8, shade: i === 0 ? 0.15 : 0 }); }
      strand(V3(s * 0.04, 0.95, 0.3).normalize(), dirOf(s * 0.5, 0.2), { w: 0.07, th: 0.026, lift: 0.085, tip: 0.05, side: -s * 0.1, r0: 1.04, seed: 9 * s, shade: 0.18, rows: 18 });
      strand(V3(s * 0.05, 0.95, 0.25).normalize(), dirOf(s * 0.9, 0.02), { w: 0.07, th: 0.026, lift: 0.075, tip: 0.07, r0: 1.045, seed: 5 * s, shade: 0.12, rows: 18 });
    }
    const crown = dirOf(PI, 0.9).normalize();
    for (let i = 0; i < 5; i++) { const a = lerp(-0.9, 0.9, i / 4); strand(crown, dirOf(a > 0 ? PI - a : -PI - a, -0.55), { w: 0.1, th: 0.03, lift: 0.04, tip: 0.06, r0: 1.03, seed: i + 40, rows: 18 }); }
  }
  if (bag.length) { const m = new THREE.Mesh(mergeGeos(bag), mat); m.castShadow = true; g.add(m); }
  return { g, springs };
}
