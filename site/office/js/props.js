// 道具：椅子＋桌子＋筆電、站立小圓桌、平板、放大鏡、筆記本、筆
import { THREE, softMat, dirSurface, ellipsoid, limbGeo, latheGeo, roundedSlab, canvasTex } from './core.js';
const mesh = (g, m, cast = true) => { const o = new THREE.Mesh(g, m); o.castShadow = cast; o.receiveShadow = true; return o; };
const grp = (parent, x = 0, y = 0, z = 0) => { const g = new THREE.Group(); g.position.set(x, y, z); parent && parent.add(g); return g; };
// 筆電螢幕：會動的內容（程式碼逐行出現、游標閃爍、小圖表）
export function makeScreen() {
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 160; const c = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const cols = ['#ffb3c7', '#9ad0ff', '#b9f0c9', '#ffe08a', '#d9c2ff'];
  const draw = (t) => {
    c.fillStyle = '#fbf7ff'; c.fillRect(0, 0, 256, 160); c.fillStyle = '#cdbcf5'; c.fillRect(0, 0, 256, 20);
    c.fillStyle = '#fff'; for (let i = 0; i < 3; i++) { c.beginPath(); c.arc(12 + i * 14, 10, 4, 0, 7); c.fill(); }
    const n = Math.floor(t * 7), row = Math.floor(n / 9), sc = Math.max(0, row - 6);
    for (let r = sc; r <= row; r++) {
      const y = 32 + (r - sc) * 15; let x = 12 + ((r * 7) % 3) * 12; const words = r === row ? (n % 9) + 1 : 3 + ((r * 5) % 6);
      for (let w = 0; w < Math.min(words, 3 + ((r * 5) % 6)); w++) { const len = 14 + ((r * 13 + w * 29) % 34); c.fillStyle = cols[(r + w * 2) % 5]; c.beginPath(); c.roundRect(x, y, len, 8, 4); c.fill(); x += len + 6; }
      if (r === row && Math.floor(t * 4) % 2) { c.fillStyle = '#6b5a8e'; c.fillRect(x, y - 1, 3, 10); }
    }
    for (let i = 0; i < 5; i++) { const h = 12 + 16 * (0.5 + 0.5 * Math.sin(t * 2 + i * 1.3)); c.fillStyle = cols[i]; c.beginPath(); c.roundRect(186 + i * 13, 150 - h, 9, h, 3); c.fill(); }
    tex.needsUpdate = true;
  };
  draw(0); return { tex, draw };
}

// ───────── 道具：椅子＋桌子＋筆電、站立桌、平板、放大鏡、筆記本、筆 ─────────
export function buildProps(ch) {
  const P = ch.props, M = softMat, root = ch.root, n = ch.n;
  // 辦公椅＋桌＋筆電
  const desk = P.desk = grp(root); desk.visible = false;
  const seatY = ch.spec.ghost ? 0.3 : 0.3;
  const chair = grp(desk, 0, 0, -0.02); chair.visible = !ch.spec.ghost;
  const seat = mesh(latheGeo([[0, -0.035], [0.17, -0.035], [0.215, -0.012], [0.215, 0.012], [0.17, 0.035], [0, 0.035]], { rows: 30, tension: 0.2 }), M('#ffc9b8')); seat.position.y = seatY - 0.035; chair.add(seat);
  const back = mesh(dirSurface((d, p) => p.set(d.x * 0.19, d.y * 0.15, d.z * 0.035 - 0.035 * d.x * d.x), { w: 40, h: 28 }), M('#ffc9b8')); back.position.set(0, seatY + 0.2, -0.215); back.rotation.x = -0.12; chair.add(back);
  const bp = mesh(limbGeo(0.018, 0.2), M('#b9b4c9')); bp.position.set(0, seatY + 0.12, -0.225); chair.add(bp);
  const pole = mesh(limbGeo(0.026, seatY - 0.09), M('#b9b4c9')); pole.position.y = seatY - 0.05; chair.add(pole);
  for (let i = 0; i < 5; i++) { const a = i / 5 * Math.PI * 2, leg = mesh(limbGeo(0.02, 0.17), M('#b9b4c9')); leg.position.y = 0.05; leg.rotation.set(Math.PI / 2 - 0.12, a, 0, 'YXZ'); chair.add(leg); const wh = mesh(ellipsoid(0.03, 0.03, 0.03, { w: 16, h: 12 }), M('#8d88a3')); wh.position.set(Math.sin(a) * 0.18, 0.03, Math.cos(a) * 0.18); chair.add(wh); }
  const dz = 0.52, top = mesh(roundedSlab(0.92, 0.46, 0.06, 0.03, 0.012), M('#ffe9c9')); top.rotation.x = -Math.PI / 2; top.position.set(0, 0.5, dz); desk.add(top);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const l = mesh(limbGeo(0.024, 0.44), M('#f5cfa0')); l.position.set(sx * 0.38, 0.49, dz + sz * 0.16); desk.add(l); }
  const lap = P.laptop = grp(desk, 0, 0.527, dz - 0.07);
  const lb = mesh(roundedSlab(0.34, 0.2, 0.025, 0.012, 0.004), M('#f1eefa')); lb.rotation.x = -Math.PI / 2; lap.add(lb);
  const kb = new THREE.Mesh(new THREE.PlaneGeometry(0.29, 0.12), softMat(0xffffff, { map: canvasTex(256, 112, (c) => { c.fillStyle = '#f1eefa'; c.fillRect(0, 0, 256, 112); c.fillStyle = '#cfc8e6'; for (let r = 0; r < 4; r++) for (let k = 0; k < 11; k++) { c.beginPath(); c.roundRect(6 + k * 22.4 + (r % 2) * 5, 6 + r * 26, 18, 20, 5); c.fill(); } }) })); kb.rotation.x = -Math.PI / 2; kb.position.set(0, 0.0115, -0.025); lap.add(kb);
  const lid = grp(lap, 0, 0.008, 0.1); lid.rotation.x = 0.3;
  const ls = mesh(roundedSlab(0.34, 0.21, 0.025, 0.01, 0.004), M('#e4dcf7')); ls.position.y = 0.105; lid.add(ls);
  const scr = ch.screen = makeScreen(); const sm = new THREE.Mesh(new THREE.PlaneGeometry(0.31, 0.185), new THREE.MeshBasicMaterial({ map: scr.tex })); sm.position.set(0, 0.105, -0.0096); sm.rotation.y = Math.PI; lid.add(sm);
  const logo = mesh(ellipsoid(0.03, 0.03, 0.004, { w: 24, h: 12 }), M('#ffffff')); logo.position.set(0, 0.11, 0.0095); lid.add(logo);
  const mug = grp(desk, 0.33, 0.515, dz + 0.02); mug.add(mesh(latheGeo([[0, 0], [0.036, 0], [0.04, 0.012], [0.04, 0.07], [0.034, 0.074], [0.03, 0.066], [0.03, 0.02], [0, 0.018]], { rows: 40, tension: 0.15 }), M('#ffb3c7')));
  const hd = mesh(new THREE.TorusGeometry(0.022, 0.007, 10, 24), M('#ffb3c7')); hd.position.set(0.045, 0.04, 0); mug.add(hd);
  const plant = grp(desk, -0.35, 0.515, dz + 0.04); plant.add(mesh(latheGeo([[0, 0], [0.034, 0], [0.045, 0.06], [0.04, 0.064], [0, 0.06]], { rows: 24, tension: 0.2 }), M('#fff6ea')));
  for (const [x, z, r, s] of [[0, 0, 0, 1.15], [0.03, 0.01, 0.5, 0.85], [-0.03, 0, -0.5, 0.9], [0, -0.02, 0.2, 0.7]]) { const lf = mesh(ellipsoid(0.026 * s, 0.06 * s, 0.014 * s, { w: 18, h: 14 }), M('#9fe0b0')); lf.position.set(x, 0.1 * s + 0.01, z); lf.rotation.z = -r; plant.add(lf); }

  // 爭執用的小圓桌
  const tb = P.table = grp(root, 0, 0, 0.56); tb.visible = false;
  const tt = mesh(latheGeo([[0, -0.02], [0.27, -0.02], [0.3, 0], [0.27, 0.02], [0, 0.02]], { rows: 28, tension: 0.2 }), M('#ffe9c9')); tt.position.y = 0.385; tb.add(tt);
  const tl = mesh(limbGeo(0.035, 0.33), M('#f5cfa0')); tl.position.y = 0.37; tb.add(tl);
  const tf = mesh(latheGeo([[0, 0], [0.16, 0], [0.17, 0.012], [0.05, 0.035], [0, 0.035]], { rows: 24, tension: 0.2 }), M('#f5cfa0')); tb.add(tf);
  const paper = P.paper = grp(tb, 0.06, 0.407, -0.02); const pm = mesh(roundedSlab(0.15, 0.2, 0.012, 0.004, 0.001), M('#ffffff')); pm.rotation.set(-Math.PI / 2, 0, 0.3); paper.add(pm);
  const tmug = P.tmug = grp(tb, -0.14, 0.405, 0.06); tmug.add(mesh(latheGeo([[0, 0], [0.036, 0], [0.04, 0.012], [0.04, 0.07], [0.034, 0.074], [0.03, 0.066], [0.03, 0.02], [0, 0.018]], { rows: 40, tension: 0.15 }), M('#9ad0ff')));

  // 平板（左手）＋放大鏡（右手）
  const tab = P.tablet = grp(n.gripL); tab.visible = false; tab.rotation.set(0.15, 0, 0); tab.position.set(-0.085, 0.0, 0.05);
  tab.add(mesh(roundedSlab(0.27, 0.19, 0.024, 0.012, 0.004), M('#8fdcc8')));
  { const lg = mesh(ellipsoid(0.034, 0.034, 0.004, { w: 24, h: 10 }), M('#ffffff'), false); lg.position.z = -0.011; tab.add(lg); }
  const ts = new THREE.Mesh(new THREE.PlaneGeometry(0.245, 0.165), new THREE.MeshBasicMaterial({ map: canvasTex(256, 172, (c) => { c.fillStyle = '#f4fbff'; c.fillRect(0, 0, 256, 172); c.strokeStyle = '#ff9a8b'; c.lineWidth = 5; c.lineJoin = 'round'; c.beginPath(); [[14, 120], [50, 96], [86, 110], [122, 66], [158, 80], [194, 40], [240, 52]].forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.stroke(); c.fillStyle = '#b9e3ff'; for (let i = 0; i < 7; i++) { c.beginPath(); c.roundRect(16 + i * 33, 150 - (10 + (i * 37) % 22), 20, 10 + (i * 37) % 22, 4); c.fill(); } c.fillStyle = '#cdbcf5'; c.beginPath(); c.roundRect(14, 12, 110, 14, 7); c.fill(); }) })); ts.position.z = 0.0106; tab.add(ts);
  const mg = P.glass = grp(n.gripR); mg.visible = false; mg.rotation.set(2.45, 0, -0.35); mg.position.set(0, 0.0, 0.0); mg.userData.s0 = 1.25;
  const ring = mesh(new THREE.TorusGeometry(0.07, 0.013, 16, 48), M('#ffb86b')); ring.position.y = 0.14; mg.add(ring);
  const lens = new THREE.Mesh(new THREE.CircleGeometry(0.066, 40), new THREE.MeshBasicMaterial({ color: 0xd9f1ff, transparent: true, opacity: 0.42, side: THREE.DoubleSide, depthWrite: false })); lens.position.y = 0.14; mg.add(lens);
  const hl = mesh(limbGeo(0.014, 0.075), M('#c98a5a')); hl.position.y = 0.065; mg.add(hl);

  // 筆記本（左手）＋鉛筆（右手）
  const nb = P.book = grp(n.gripL); nb.visible = false; nb.rotation.set(0.2, 0, 0); nb.position.set(-0.08, 0.0, 0.035);
  nb.add(mesh(roundedSlab(0.2, 0.25, 0.015, 0.016, 0.004), M('#ff9ac1')));
  const pg = ch.noteTex = makeNotes(); const pgm = new THREE.Mesh(new THREE.PlaneGeometry(0.18, 0.23), softMat(0xffffff, { map: pg.tex })); pgm.position.z = 0.0125; nb.add(pgm);
  for (let i = 0; i < 6; i++) { const r = mesh(new THREE.TorusGeometry(0.011, 0.0035, 8, 16), M('#b9b4c9'), false); r.position.set(-0.07 + i * 0.028, 0.125, 0.004); r.rotation.y = Math.PI / 2; nb.add(r); }
  const pen = P.pen = grp(n.gripR); pen.visible = false; pen.rotation.set(0.88, 0, 0.5); pen.position.set(0, -0.01, 0.01); pen.userData.s0 = 1.5;
  pen.add(mesh(latheGeo([[0, -0.085], [0.004, -0.082], [0.011, -0.055], [0.011, 0.06], [0.012, 0.062], [0.012, 0.08], [0.008, 0.088], [0, 0.089]], { rows: 40, seg: 20, tension: 0.1 }), softMat(0xffffff, { map: canvasTex(8, 64, (c) => { c.fillStyle = '#ffd24d'; c.fillRect(0, 0, 8, 64); c.fillStyle = '#ffb7c0'; c.fillRect(0, 0, 8, 9); c.fillStyle = '#c9ccd8'; c.fillRect(0, 9, 8, 3); c.fillStyle = '#f5d9b5'; c.fillRect(0, 53, 8, 8); c.fillStyle = '#5a4a4a'; c.fillRect(0, 61, 8, 3); }) })));
}
// 筆記本頁面：字跡逐漸寫出來
export function makeNotes() {
  const cv = document.createElement('canvas'); cv.width = 144; cv.height = 184; const c = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; let last = -1;
  const draw = (t) => {
    const n = Math.floor(t * 9) % 70; if (n === last) return; last = n;
    c.fillStyle = '#fffdf6'; c.fillRect(0, 0, 144, 184); c.strokeStyle = '#d6e6fb'; c.lineWidth = 1.5;
    for (let y = 30; y < 180; y += 22) { c.beginPath(); c.moveTo(10, y); c.lineTo(134, y); c.stroke(); }
    c.strokeStyle = '#6b6f9c'; c.lineWidth = 2.6; c.lineCap = 'round'; c.lineJoin = 'round';
    for (let i = 0; i < n; i++) { const row = Math.floor(i / 10), k = i % 10, x = 14 + k * 12, y = 26 + row * 22; c.beginPath(); c.moveTo(x, y); c.lineTo(x + 3, y - 6 - ((i * 7) % 5)); c.lineTo(x + 6, y - ((i * 3) % 4)); c.lineTo(x + 9, y - 5); c.stroke(); }
    tex.needsUpdate = true;
  };
  draw(0); return { tex, draw };
}

