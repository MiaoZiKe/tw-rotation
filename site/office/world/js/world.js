// 場景：依 layout.json 蓋出辦公室（地板、牆、窗、家具、戶外），並管理家具、座位與具名目標點。
import { THREE, G, Part, PAL, MAT, shade, textTexture } from './kit.js';
import { BUILD } from './furniture.js';
import { createNav, footToWorld, localToWorld } from './nav.js';

const LS_KEY = 'aiOffice.world.layout.v1';
export function loadOverrides() { try { return JSON.parse(localStorage.getItem(LS_KEY) || '{}') || {}; } catch (e) { return {}; } }
export function saveOverrides(o) { try { localStorage.setItem(LS_KEY, JSON.stringify(o)); return true; } catch (e) { return false; } }
export function clearOverrides() { try { localStorage.removeItem(LS_KEY); } catch (e) { } }

function canvasTex(w, h, draw, repeat) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h; draw(cv.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
  return t;
}

export function createWorld(canvas, layout, org, quality) {
  const W = { layout, org, quality, time: 0, speed: 1, timers: [], furn: new Map(), chars: new Map(), spots: [], boardsMesh: [], pickFurn: [] };
  const members = new Map(); members.set('ceo', org.ceo);
  for (const d of org.departments) for (const m of d.members) members.set(m.id, { ...m, dept: d.id, deptName: d.name, color: d.color });
  for (const m of org.reserve) members.set(m.id, { ...m, zh: '後備', dept: 'reserve' });
  W.members = members;
  const deptColor = id => (org.departments.find(d => d.id === id) || {}).color;
  const ctx = { deptColor, member: id => members.get(id) };

  // ── 繪圖器、場景、光 ──
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: quality !== 'low', powerPreference: 'high-performance' });
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.NoToneMapping;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = quality === 'low' ? THREE.PCFShadowMap : THREE.PCFSoftShadowMap; renderer.shadowMap.autoUpdate = false;
  const scene = new THREE.Scene(); scene.fog = new THREE.Fog('#e3f4fc', 110, 260);
  scene.background = canvasTex(8, 256, (c, w, h) => { const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#a9ddf8'); g.addColorStop(0.55, '#d7f0fc'); g.addColorStop(1, '#f1fbff'); c.fillStyle = g; c.fillRect(0, 0, w, h); });
  const camera = new THREE.PerspectiveCamera(38, 1, 0.3, 320);
  const hemi = new THREE.HemisphereLight('#fffaf3', '#f3d5b4', 1.5); scene.add(hemi);
  const sun = new THREE.DirectionalLight('#fff3e0', 1.55); sun.position.set(20 - 10, 36, 15 + 9); sun.target.position.set(20, 0, 15); scene.add(sun, sun.target);
  sun.castShadow = true; const sm = quality === 'low' ? 1024 : 2048; sun.shadow.mapSize.set(sm, sm);
  Object.assign(sun.shadow.camera, { left: -24, right: 24, top: 20, bottom: -20, near: 1, far: 90 }); sun.shadow.bias = -0.0006; sun.shadow.normalBias = 0.035; sun.shadow.radius = 3;
  Object.assign(W, { renderer, scene, camera, sun });
  W.shadowDirty = () => { renderer.shadowMap.needsUpdate = true; };

  const Lw = layout.size.w, Ld = layout.size.d;

  // ── 戶外：草地、小路、樹、花 ──
  {
    const P = new Part(); let s = 7; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
    P.add(G.cyl(120, 0.2, 0.05, 48), '#c4ecb4', Lw / 2, -0.22, Ld / 2);
    P.slab('#f1e2c3', Lw + 3, Ld + 3, 0.12, Lw / 2, -0.13, Ld / 2, 1.6);
    P.slab('#f3dfb8', 3.0, 9, 0.06, 20.5, -0.05, Ld + 4.2, 1.2);
    for (let i = 0; i < 46; i++) {
      const a = r() * 6.283, d = 30 + r() * 34, x = Lw / 2 + Math.cos(a) * d * 1.25, z = Ld / 2 + Math.sin(a) * d * 0.95;
      if (x > -3 && x < Lw + 3 && z > -3 && z < Ld + 3) continue; if (z > Ld + 1) continue;
      const h = 1.4 + r() * 1.6, cr = 1.5 + r() * 1.3, c = [PAL.leaf, PAL.leafDark, PAL.leafLight, '#a8dba0'][i % 4];
      P.add(G.cyl(0.28, h, 0.05, 10), PAL.woodDark, x, 0, z); P.add(G.sph(cr, 10, 7), c, x, h + cr * 0.7, z, 0, 0, 0, 1, 0.9, 1);
      P.add(G.sph(cr * 0.7, 8, 6), shade(c, 0.15), x + cr * 0.5, h + cr * 0.4, z + cr * 0.3);
    }
    for (let i = 0; i < 70; i++) {
      const side = Math.floor(r() * 4), t = r(); let x, z;
      if (side === 0) { x = t * Lw; z = -2.5 - r() * 2; } else if (side === 1) { x = t * Lw; z = Ld + 2.2 + r() * 2.5; } else if (side === 2) { x = -2.5 - r() * 2; z = t * Ld; } else { x = Lw + 2.5 + r() * 2; z = t * Ld; }
      if (Math.abs(x - 20.5) < 2.2 && z > Ld) continue;
      if (i % 3 === 0) P.add(G.sph(0.5 + r() * 0.35, 10, 8), [PAL.leaf, PAL.leafLight][i % 2], x, 0.25, z, 0, 0, 0, 1.2, 0.8, 1);
      else P.add(G.sph(0.13, 8, 6), ['#ffb3c1', '#fff0a8', '#ffffff', '#ffc9a3'][i % 4], x, 0.08, z);
    }
    // 大門外：踏石、路燈、信箱、長椅
    for (let i = 0; i < 6; i++) P.add(G.cyl(0.5, 0.05, 0.02, 16), '#fbf0da', 20.5 + (i % 2 ? 0.35 : -0.35), 0.0, Ld + 1.5 + i * 1.25);
    for (const x of [18.4, 22.6]) { P.add(G.cyl(0.07, 2.3, 0.02, 10), '#b9a48f', x, 0, Ld + 2.4); P.add(G.cyl(0.2, 0.06, 0.02, 12), '#b9a48f', x, 0, Ld + 2.4); P.add(G.sph(0.3, 12, 9), '#fff0b8', x, 2.5, Ld + 2.4); P.add(G.cyl(0.2, 0.08, 0.03, 12), '#b9a48f', x, 2.72, Ld + 2.4); }
    P.add(G.cyl(0.05, 0.9, 0.01, 8), PAL.woodDark, 23.4, 0, Ld + 1.0); P.add(G.box(0.5, 0.36, 0.34, 0.12), '#f28b82', 23.4, 1.05, Ld + 1.0); P.add(G.box(0.3, 0.05, 0.02, 0.01), '#fffaf2', 23.4, 1.08, Ld + 1.18);
    P.add(G.slab(1.8, 0.5, 0.08, 0.16), PAL.wood, 17.0, 0.4, Ld + 1.0); P.add(G.box(0.1, 0.4, 0.4, 0.04), PAL.cream, 16.3, 0.2, Ld + 1.0); P.add(G.box(0.1, 0.4, 0.4, 0.04), PAL.cream, 17.7, 0.2, Ld + 1.0); P.add(G.box(1.8, 0.4, 0.08, 0.035), PAL.wood, 17.0, 0.75, Ld + 0.78);
    for (let i = 0; i < 26; i++) { const x = 1 + r() * (Lw - 2), z = Ld + 0.9 + r() * 0.9; if (Math.abs(x - 20.5) < 3.4) continue; P.add(G.sph(0.38 + r() * 0.2, 8, 6), [PAL.leaf, PAL.leafLight, PAL.leafDark][i % 3], x, 0.15, z, 0, 0, 0, 1.3, 0.8, 1); P.add(G.sph(0.09, 6, 5), ['#ffb3c1', '#fff0a8', '#ffffff', '#ffc9a3'][i % 4], x + 0.15, 0.48, z + 0.1); P.add(G.sph(0.08, 6, 5), ['#fff0a8', '#ffb3c1'][i % 2], x - 0.2, 0.42, z + 0.18); }
    for (let i = 0; i < 14; i++) { const a = i / 14 * 6.283 + r() * 0.3, d = 88 + r() * 16, hr = 14 + r() * 12; P.add(G.sph(hr, 14, 8), ['#b7e3a4', '#a8dba0', '#c4ecb4'][i % 3], Lw / 2 + Math.cos(a) * d, -hr * 0.45, Ld / 2 + Math.sin(a) * d, 0, 0, 0, 1.5, 0.75, 1); }
    const m = P.mesh(); m.castShadow = false; scene.add(m);
    const C = new Part();
    for (let i = 0; i < 9; i++) { const a = i / 9 * 6.283 + r(), d = 70 + r() * 30, x = Lw / 2 + Math.cos(a) * d, z = Ld / 2 + Math.sin(a) * d, y = 26 + r() * 10, k = 3 + r() * 2; for (let j = 0; j < 4; j++) C.add(G.sph(k * (0.7 + r() * 0.5), 10, 7), '#ffffff', x + (j - 1.5) * k * 0.95, y + (j % 2) * k * 0.3, z + r() * 2, 0, 0, 0, 1, 0.62, 1); }
    const cm = new THREE.Mesh(C.geometry(), new THREE.MeshBasicMaterial({ color: '#ffffff', fog: false })); scene.add(cm); W.clouds = cm;
  }

  // ── 木地板底 ──
  {
    const tex = canvasTex(512, 512, (c, w, h) => {
      c.fillStyle = '#f3dcba'; c.fillRect(0, 0, w, h);
      for (let row = 0; row < 8; row++) {
        const y = row * 64; let x = -((row * 173) % 256);
        while (x < w) { const pw = 200 + ((row * 97 + x) % 90); c.fillStyle = ['#f6e0c0', '#f2d8b4', '#f8e4c6', '#efd3ad'][Math.abs((row * 3 + Math.floor(x / 97))) % 4]; c.beginPath(); c.roundRect(x + 2, y + 2, pw - 4, 60, 10); c.fill(); x += pw; }
      }
    }, [Lw / 4, Ld / 4]);
    const g = G.slab(Lw, Ld, 0.1, 0.4, 0.03).clone(); const pos = g.attributes.position, uv = new Float32Array(pos.count * 2);
    for (let i = 0; i < pos.count; i++) { uv[i * 2] = pos.getX(i) / Lw + 0.5; uv[i * 2 + 1] = pos.getZ(i) / Ld + 0.5; } g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: tex, roughness: 0.9 })); m.position.set(Lw / 2, -0.1, Ld / 2); m.receiveShadow = true; scene.add(m); W.floorBase = m;
  }

  // ── 房間與部門的地板色塊（各自一個網格，整修時可換色） ──
  W.rooms = new Map();
  const ov = W.overrides = loadOverrides();
  function buildRoomFloor(room) {
    const old = W.rooms.get(room.id); if (old && old.mesh) { old.mesh.geometry.dispose(); old.mesh.removeFromParent(); }
    const col = (ov.floor && ov.floor[room.id]) || room.floor, P = new Part(), inset = room.kind === 'room' ? 0.22 : 0;
    const w = room.w - inset * 2, d = room.d - inset * 2;
    if (room.kind === 'dept') { P.slab(shade(col, 0.12), w, d, 0.03, 0, 0, 0, 0.7, 0, 0.012); P.slab(shade(col, 0.52), w - 0.5, d - 0.5, 0.014, 0, 0.024, 0, 0.5, 0, 0.006); }
    else { P.slab(col, w, d, 0.03, 0, 0, 0, 0.5, 0, 0.012); P.slab(shade(col, 0.35), w - 0.7, d - 0.7, 0.014, 0, 0.024, 0, 0.35, 0, 0.006); }
    const m = P.mesh(); m.castShadow = false; m.position.set(room.x + room.w / 2, 0.001, room.z + room.d / 2); m.userData.room = room.id; scene.add(m);
    W.rooms.set(room.id, { room, mesh: m, color: col });
  }
  layout.rooms.forEach(buildRoomFloor); W.buildRoomFloor = buildRoomFloor;

  // ── 牆與窗 ──
  {
    const P = new Part(), glass = [], WALL = '#fff3df', LOW = '#fbe6cb', T = 0.25;
    const wins = layout.windows || [];
    for (const w of layout.walls) {
      const horiz = w.z1 === w.z2, len = horiz ? Math.abs(w.x2 - w.x1) : Math.abs(w.z2 - w.z1), cx = (w.x1 + w.x2) / 2, cz = (w.z1 + w.z2) / 2;
      const side = horiz ? (w.z1 === 0 ? 'n' : (w.z1 === Ld ? 's' : '')) : (w.x1 === 0 ? 'w' : (w.x1 === Lw ? 'e' : ''));
      const myW = w.h > 2 ? wins.filter(q => q.side === side) : [];
      const seg = (a, b, y0, y1, col) => { const l = b - a + (y0 === 0 ? T : 0), c = (a + b) / 2; if (b - a < 0.02) return; horiz ? P.box(col, l, y1 - y0, T, c, y0, cz, 0.09) : P.box(col, T, y1 - y0, l, cx, y0, c, 0.09); };
      const a0 = horiz ? Math.min(w.x1, w.x2) : Math.min(w.z1, w.z2), a1 = a0 + len;
      if (!myW.length) { seg(a0, a1, 0, w.h, w.h > 1 ? LOW : WALL); if (w.h <= 1.2) { horiz ? P.box(PAL.wood, len + T + 0.06, 0.07, T + 0.08, cx, w.h - 0.02, cz, 0.03) : P.box(PAL.wood, T + 0.08, 0.07, len + T + 0.06, cx, w.h - 0.02, cz, 0.03); } continue; }
      const sill = 0.95, head = 2.1; seg(a0, a1, 0, sill, WALL); seg(a0, a1, head, w.h, WALL);
      horiz ? P.box(PAL.wood, len + T + 0.06, 0.08, T + 0.1, cx, w.h - 0.02, cz, 0.035) : P.box(PAL.wood, T + 0.1, 0.08, len + T + 0.06, cx, w.h - 0.02, cz, 0.035);
      let cur = a0; const sorted = myW.slice().sort((p, q) => p.at - q.at);
      for (const q of sorted) {
        const x0 = q.at - q.w / 2, x1 = q.at + q.w / 2; seg(cur, x0, sill - 0.05, head + 0.05, WALL); cur = x1;
        // 窗框與窗台
        if (horiz) { P.box(PAL.white, q.w + 0.1, 0.07, T + 0.14, q.at, sill - 0.03, cz, 0.03); P.box(PAL.white, 0.06, head - sill, 0.08, q.at, sill, cz, 0.025); P.box(PAL.white, q.w, 0.06, 0.08, q.at, (sill + head) / 2, cz, 0.025); }
        else { P.box(PAL.white, T + 0.14, 0.07, q.w + 0.1, cx, sill - 0.03, q.at, 0.03); P.box(PAL.white, 0.08, head - sill, 0.06, cx, sill, q.at, 0.025); P.box(PAL.white, 0.08, 0.06, q.w, cx, (sill + head) / 2, q.at, 0.025); }
        glass.push({ horiz, at: q.at, w: q.w, c: horiz ? cz : cx, y0: sill, y1: head, side });
      }
      seg(cur, a1, sill - 0.05, head + 0.05, WALL);
    }
    const m = P.mesh(); scene.add(m); W.wallMesh = m;
    // 玻璃與地上的光斑（一個網格）
    const gp = [], sp = [], suv = [];
    for (const q of glass) {
      const a = q.at - q.w / 2, b = q.at + q.w / 2;
      if (q.horiz) gp.push(a, q.y0, q.c, b, q.y0, q.c, b, q.y1, q.c, a, q.y0, q.c, b, q.y1, q.c, a, q.y1, q.c);
      else gp.push(q.c, q.y0, a, q.c, q.y0, b, q.c, q.y1, b, q.c, q.y0, a, q.c, q.y1, b, q.c, q.y1, a);
      const L = 2.6, sk = 0.7, y = 0.062; let p;
      if (q.side === 'n') p = [[a, 0.2], [b, 0.2], [b + sk, L], [a + sk, L]]; else if (q.side === 'w') p = [[0.2, a], [0.2, b], [L, b + sk], [L, a + sk]]; else if (q.side === 'e') p = [[Lw - 0.2, a], [Lw - 0.2, b], [Lw - L, b + sk], [Lw - L, a + sk]]; else continue;
      const ix = [0, 1, 2, 0, 2, 3], uvs = [[0, 0], [1, 0], [1, 1], [0, 1]];
      for (const i of ix) { sp.push(p[i][0], y, p[i][1]); suv.push(uvs[i][0], uvs[i][1]); }
    }
    const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.Float32BufferAttribute(gp, 3));
    scene.add(new THREE.Mesh(gg, new THREE.MeshBasicMaterial({ color: '#cfefff', transparent: true, opacity: 0.38, side: THREE.DoubleSide, depthWrite: false })));
    const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3)); sg.setAttribute('uv', new THREE.Float32BufferAttribute(suv, 2));
    const stex = canvasTex(64, 128, (c, w, h) => { const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, 'rgba(255,244,200,0.9)'); g.addColorStop(1, 'rgba(255,244,200,0)'); c.fillStyle = g; c.fillRect(0, 0, w, h); c.clearRect(w / 2 - 2, 0, 4, h); });
    const sunPatch = new THREE.Mesh(sg, new THREE.MeshBasicMaterial({ map: stex, transparent: true, opacity: 0.1, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending })); sunPatch.renderOrder = 2; scene.add(sunPatch);
  }

  // ── 家具 ──
  const nav = W.nav = createNav(layout);
  const furnRoot = new THREE.Group(); scene.add(furnRoot);
  // 螢幕：全部共用一個實例網格，畫面是一張會動的小畫布
  const scrCv = document.createElement('canvas'); scrCv.width = 64; scrCv.height = 40; const scrCtx = scrCv.getContext('2d');
  const scrTex = new THREE.CanvasTexture(scrCv); scrTex.colorSpace = THREE.SRGBColorSpace; scrTex.magFilter = THREE.NearestFilter;
  const screens = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: scrTex }), 64); screens.frustumCulled = false; scene.add(screens);
  let scrRow = 0, scrT = 0;
  function tickScreens(dt) {
    scrT += dt; if (scrT < 0.22) return; scrT = 0;
    const c = scrCtx; c.drawImage(scrCv, 0, -4); c.fillStyle = '#f7fbff'; c.fillRect(0, 36, 64, 4);
    const ind = [3, 7, 7, 11, 3, 7][scrRow % 6], len = 10 + (scrRow * 37 % 34); c.fillStyle = ['#8fb6f0', '#f3a6bd', '#8fd3a6', '#f6c177'][scrRow % 4]; c.fillRect(ind, 37, Math.min(len, 58 - ind), 2); scrRow++;
    scrTex.needsUpdate = true;
  }
  scrCtx.fillStyle = '#f7fbff'; scrCtx.fillRect(0, 0, 64, 40); for (let i = 0; i < 10; i++) { scrT = 1; tickScreens(0); }

  function place(inst) {
    const f = inst.f; inst.obj.position.set(f.x, 0, f.z); inst.obj.rotation.y = f.rot * Math.PI / 2; inst.obj.updateMatrixWorld(true);
  }
  function addFurniture(f) {
    const b = BUILD[f.type]; if (!b) { console.warn('未知家具', f.type); return null; }
    const spec = b(f, ctx), obj = new THREE.Group(), mesh = spec.part.mesh();
    if (spec.flat || spec.noshadow) mesh.castShadow = false;
    obj.add(mesh); (spec.extras || []).forEach(e => obj.add(e));
    mesh.userData.fid = f.id; obj.userData.fid = f.id;
    const inst = { f, spec, obj, mesh, home: { x: f.x, z: f.z, rot: f.rot } };
    const o = ov.f && ov.f[f.id]; if (o) { f.x = o[0]; f.z = o[1]; f.rot = o[2]; }
    place(inst); furnRoot.add(obj); W.furn.set(f.id, inst);
    if (spec.board) { mesh.userData.board = spec.board; W.boardsMesh.push(mesh); }
    if (!spec.fixed) W.pickFurn.push(mesh);
    if (spec.whiteboard) W.whiteboard = makeWhiteboard(inst);
    return inst;
  }
  function makeWhiteboard(inst) {
    const wb = inst.spec.whiteboard, cv = document.createElement('canvas'); cv.width = 1024; cv.height = 420;
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(wb.w, wb.h), new THREE.MeshBasicMaterial({ map: tex })); m.position.set(wb.x, wb.y, wb.z); inst.obj.add(m);
    const api = {
      lines: [], title: '', draw() {
        const c = cv.getContext('2d'); c.fillStyle = '#ffffff'; c.fillRect(0, 0, 1024, 420);
        const font = (px, b) => `${b ? 800 : 600} ${px}px "Noto Sans TC","PingFang TC","Microsoft JhengHei","WenQuanYi Zen Hei",sans-serif`;
        if (!api.title && !api.lines.length) { c.fillStyle = '#d9cfc4'; c.font = font(54, 1); c.textAlign = 'center'; c.fillText('白板', 512, 225); tex.needsUpdate = true; return; }
        c.textAlign = 'left'; c.fillStyle = '#e8743b'; c.font = font(62, 1); c.fillText(api.title, 40, 76); c.fillStyle = '#f6c9a8'; c.fillRect(40, 98, 944, 7);
        const cols = ['#3f6fb5', '#3d9a63', '#c2527a', '#8a5bc4', '#b5762a'];
        api.lines.forEach((t, i) => { c.fillStyle = cols[i % 5]; c.font = font(52, 1); c.fillText(`${i + 1}. ${t}`, 48, 168 + i * 62); });
        tex.needsUpdate = true;
      },
      set(title) { api.title = title; api.lines = []; api.draw(); }, add(t) { api.lines.push(t); api.draw(); }, clear() { api.title = ''; api.lines = []; api.draw(); }
    };
    api.draw(); return api;
  }
  layout.furniture.forEach(addFurniture);
  W.addFurniture = addFurniture; W.place = place;

  // 座位與具名目標點；家具動過就重算
  function respot() {
    const feet = []; for (const inst of W.furn.values()) feet.push(...footToWorld(inst.f, inst.spec.foot || []));
    nav.rebuild(feet);
    const old = new Map(W.spots.map(s => [s.uid, s.taken])); const spots = []; let n = 0;
    for (const inst of W.furn.values()) {
      const f = inst.f, rot = f.rot * Math.PI / 2;
      (inst.spec.seats || []).forEach((s, i) => {
        const p = localToWorld(f, s.x, s.z); let ap = null;
        for (const a of s.app) { const q = localToWorld(f, a[0], a[1]); if (nav.isReach(q.x, q.z)) { ap = q; break; } }
        if (!ap) ap = nav.nearestFree(p.x, p.z, 16) || p;
        spots.push({ uid: f.id + '#s' + i, name: s.key, x: ap.x, z: ap.z, face: s.face + rot, seat: { x: p.x, y: s.y, z: p.z, face: s.face + rot }, fid: f.id, idx: i });
      });
      (inst.spec.spots || []).forEach((s, i) => {
        let p = localToWorld(f, s.x, s.z); if (!nav.isReach(p.x, p.z)) p = nav.nearestFree(p.x, p.z, 10) || p;
        spots.push({ uid: f.id + '#p' + i, name: s.name, x: p.x, z: p.z, face: s.face + rot, fid: f.id });
      });
    }
    for (const s of layout.spots || []) spots.push({ uid: 'L' + (n++), name: s.name, x: s.x, z: s.z, face: s.face * Math.PI / 2 });
    spots.forEach(s => { s.taken = old.get(s.uid) || null; }); W.spots = spots;
    // 螢幕位置
    let k = 0; const m4 = new THREE.Matrix4(), l = new THREE.Matrix4(); W.screenOwner = [];
    for (const inst of W.furn.values()) {
      const s = inst.spec.screen; if (!s) continue; inst.obj.updateMatrixWorld(true);
      l.makeScale(s.w, s.h, 1).setPosition(s.x, s.y, s.z); m4.multiplyMatrices(inst.obj.matrixWorld, l); screens.setMatrixAt(k, m4); W.screenOwner[k] = inst.f.owner; k++;
    }
    screens.count = k; screens.instanceMatrix.needsUpdate = true; W.shadowDirty();
  }
  W.respot = respot; respot();
  const _on = new THREE.Color('#ffffff'), _off = new THREE.Color('#55607a');
  W.updateScreens = dt => {
    tickScreens(dt);
    for (let i = 0; i < screens.count; i++) { const c = W.chars.get(W.screenOwner[i]); screens.setColorAt(i, c && c.state === 'sit' && c.atDesk ? _on : _off); }
    if (screens.instanceColor) screens.instanceColor.needsUpdate = true;
  };

  W.findSpots = name => W.spots.filter(s => s.name === name);
  W.spot = (name, near, who) => {
    const all = W.findSpots(name); if (!all.length) return null;
    const free = all.filter(s => !s.taken || s.taken === who); const pool = free.length ? free : all;
    if (!near) return pool[Math.floor(Math.random() * pool.length)];
    return pool.reduce((b, s) => (Math.hypot(s.x - near.x, s.z - near.z) < Math.hypot(b.x - near.x, b.z - near.z) ? s : b));
  };

  // 角色腳下的接觸陰影（一個實例網格）
  const blobTex = canvasTex(64, 64, (c) => { const g = c.createRadialGradient(32, 32, 2, 32, 32, 31); g.addColorStop(0, 'rgba(90,60,40,0.42)'); g.addColorStop(0.6, 'rgba(90,60,40,0.18)'); g.addColorStop(1, 'rgba(90,60,40,0)'); c.fillStyle = g; c.fillRect(0, 0, 64, 64); });
  const blobG = new THREE.PlaneGeometry(1, 1); blobG.rotateX(-Math.PI / 2);
  const blobs = new THREE.InstancedMesh(blobG, new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false }), 64); blobs.frustumCulled = false; blobs.renderOrder = 3; scene.add(blobs);
  const bm = new THREE.Matrix4();
  W.updateBlobs = () => {
    let i = 0;
    for (const c of W.chars.values()) {
      const p = c.object3D.position, vis = c.object3D.visible && c.state !== 'sit', s = vis ? 0.85 - Math.min(0.3, p.y * 1.5) : 0.0001;
      bm.makeScale(s, 1, s).setPosition(p.x, 0.07, p.z); blobs.setMatrixAt(i++, bm);
    }
    blobs.count = i; blobs.instanceMatrix.needsUpdate = true;
  };

  // 選取圈
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.4, 0.5, 40), new THREE.MeshBasicMaterial({ color: '#ff9a3c', transparent: true, opacity: 0.9, depthWrite: false })); ring.rotation.x = -Math.PI / 2; ring.visible = false; ring.renderOrder = 4; scene.add(ring); W.ring = ring;

  W.roomAt = (x, z) => layout.rooms.find(r => x >= r.x && x <= r.x + r.w && z >= r.z && z <= r.z + r.d);
  W.sleep = s => new Promise(r => W.timers.push({ at: W.time + s, r }));
  W.tickTimers = () => { if (!W.timers.length) return; const due = W.timers.filter(t => t.at <= W.time); if (due.length) { W.timers = W.timers.filter(t => t.at > W.time); due.forEach(t => t.r()); } };
  return W;
}
