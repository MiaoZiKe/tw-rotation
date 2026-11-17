// 專案區塊辦公室（2026-11-16）：非 tw-rotation 的專案，場景只蓋「CEO 區塊」＋「這個專案實際出現的每個 Agent 各一個區塊」＋共用的員工運動場、無業遊民區。
//
// 擁有者原話：「我如果開一個新專案，舉例來說我只派幫我規劃咖啡廳，那他只會有 CEO 和 規劃的 Agent 或是 驗證資料的 Agent，
//   在 AI Office 內只會出現 3 個 Block，其他的運動場、無業遊民區，而非用我現有的 Block」。
//
// 為什麼要在蓋場景「之前」就知道專案名：場景（地板、牆、家具、尋路格子）是 createWorld 一次蓋好的，蓋完再拆整間示範辦公室風險大
//   （家具、尋路、著火、物理層都綁著）。所以 main.js 在載入 layout.json 之後、蓋場景之前，先向收件端問一次這個專案的名稱（peekProject）：
//     · 名稱是 tw-rotation（或問不到）→ 照舊用完整辦公室（部門房間、名冊露面）；
//     · 其他專案 → blocksLayout() 把示範佈局縮成「只有 CEO 區塊」，其餘區塊由 createBlocks() 在 Agent 出現時一個一個長出來。
//   示範模式（?demo=1／沒登入）完全不經過這裡。
//
// 11-16 追加（擁有者）：「新專案都先不開放運動場」→ 區塊模式不呼叫 mountSports（沒有運動場、按鈕、選單項目、泳池），被燒改跑 CEO 區塊旁的飲水機；外圍米色鋪面依區塊範圍動態生成（見 floorTo）。
// 排版（為什麼這樣排）：大門在南邊（z=30），遊民區在大門外（z≥31.9、座標寫死在 outside），所以區塊都蓋在大門裡面：
//   CEO 區塊固定在大門正前方（最下面一排、置中）；Agent 區塊在它上面一排一排長，每排最多 5 個、每排各自置中——
//   第二個 Agent 一來，同排第一個會往左挪半格，永遠是左右對稱。只有同排的區塊會被挪，CEO 不動。
import { THREE, Part } from './kit.js';

export const TW_NAME = /^tw-rotation$/i;
const FLOOR_M = 2.2, GATE_Z = 30.4, FLOOR_COLOR = '#f1e2c3';   // 外圍鋪面邊距；南緣至少鋪到大門（z=30）外一點，大門與步道才接得上
const CX = 20.5, BW = 7.4, BD = 5.6, PX = 7.8, PER_ROW = 5, MAX_ROWS = 3, ROW0_Z = 13.2, ROW_PZ = 6.4;
const COLORS = ['#cbb2f2', '#ffc48f', '#f7b0c6', '#a4c2f7', '#aedb9a', '#f6c177', '#f7df83', '#97dfcc', '#f4a59d', '#8ecfe6'];
export const CAPACITY = PER_ROW * MAX_ROWS;
const clip = (t, n = 12) => { const a = Array.from(String(t || '')); return a.length > n ? a.slice(0, n - 1).join('') + '…' : a.join(''); };

// ───────── 開場前先問收件端：這個專案叫什麼、目前有哪些 Agent ─────────
// 認證與網址的取得方式跟 live.js 一致（網址 #aio= 接入碼、或登入權杖＋設定裡的收件端網址／會員 API 推出來的網址）；這裡只讀、不清掉網址上的接入碼（那是 live.js 的事）。
function loadScript(src) { return new Promise(res => { const s = document.createElement('script'); s.src = src; s.onload = s.onerror = () => res(); setTimeout(res, 3000); document.head.append(s); }); }
/** 一般會員的辦公室沒有專案可選（剛建好、或網址沒帶專案）時用的「佔位專案」：只用來讓場景走區塊模式；讀狀態時不帶專案（看全部），之後出現的專案自己長出區塊 */
export const MEMBER_PH = '0000000000000000';
const myUser = () => { try { const u = JSON.parse(localStorage.getItem('tw.acct.user') || 'null'); return u && !u.admin && !u.owner ? u : null; } catch (e) { return null; } };
/** 一般會員（非站長）打開辦公室頁、網址沒帶專案：改成帶專案（讀自己辦公室最近的專案，沒有就用佔位）→ 場景走區塊模式，不沿用站長的整棟示範格局與部門。回傳 true＝已換網址、這一輪開場中止。 */
export async function memberRedirect(qs) {
  try {
    if (/^[0-9a-f]{16}$/.test(qs.get('project') || '') || qs.get('demo') === '1' || !myUser()) return false;
    let cfg = {}; try { cfg = JSON.parse(localStorage.getItem('aiOffice.live.v1') || 'null') || {}; } catch (e) { cfg = {}; }
    const tok = localStorage.getItem('tw.acct.tok'); if (!tok || !cfg.login || cfg.show) return false;
    let url = qs.get('aio_url') ? qs.get('aio_url').replace(/\/+$/, '') : cfg.url;
    if (!url) {
      if (!window.TW_ACCOUNT) await loadScript('../account_config.js');
      const api = window.TW_ACCOUNT && window.TW_ACCOUNT.api; if (api && /\/\/tw-account\./.test(api)) url = api.replace('//tw-account.', '//tw-ai-office-bridge.').replace(/\/+$/, '');
    }
    if (!url) return false;
    const ctl = new AbortController(), tm = setTimeout(() => ctl.abort(), 5000);
    const r = await fetch(`${url}/v1/office/me/state?since=0`, { headers: { 'X-AIO-Session': tok }, cache: 'no-store', credentials: 'omit', signal: ctl.signal });
    clearTimeout(tm);
    let ph = MEMBER_PH;
    if (r.ok) { const j = await r.json(), ps = j.projects || []; if (ps[0] && /^[0-9a-f]{16}$/.test(ps[0].hash || '')) ph = ps[0].hash; }
    else if (r.status !== 401 && r.status !== 403) return false;      // 連不上：照舊，不冒險
    const u = new URL(location.href); u.searchParams.set('project', ph); location.replace(u.toString()); return true;
  } catch (e) { return false; }
}
export async function peekProject(qs) {
  try {
    const ph = qs.get('project'); if (!/^[0-9a-f]{16}$/.test(ph || '')) return null;
    if (ph === MEMBER_PH) return { name: '我的辦公室' };
    let cfg = {}; try { cfg = JSON.parse(localStorage.getItem('aiOffice.live.v1') || 'null') || {}; } catch (e) { cfg = {}; }
    let tok = null; try { tok = localStorage.getItem('tw.acct.tok'); } catch (e) { tok = null; }
    const m = /(?:^#|&)aio=([A-Za-z0-9_-]{8,200})/.exec(location.hash || '');
    const hdr = m ? { Authorization: 'Bearer ' + m[1] } : (cfg.login && tok ? { 'X-AIO-Session': tok } : null); if (!hdr) return null;
    let url = qs.get('aio_url') ? qs.get('aio_url').replace(/\/+$/, '') : cfg.url;
    if (!url) {
      if (!window.TW_ACCOUNT) await loadScript('../account_config.js');
      const api = window.TW_ACCOUNT && window.TW_ACCOUNT.api; if (api && /\/\/tw-account\./.test(api)) url = api.replace('//tw-account.', '//tw-ai-office-bridge.').replace(/\/+$/, '');
    }
    if (!url) return null;
    const office = /^[A-Za-z0-9_-]{1,40}$/.test(qs.get('office') || '') ? qs.get('office') : (cfg.office || 'main'), view = /^o_[A-Za-z0-9_-]{6,30}$/.test(qs.get('office') || '') ? qs.get('office') : null;
    const ctl = new AbortController(), tm = setTimeout(() => ctl.abort(), 5000);
    let r = await fetch(`${url}/v1/office/${encodeURIComponent(office)}/state?since=0&project=${ph}${view ? '&view=' + view : ''}`, { headers: hdr, cache: 'no-store', credentials: 'omit', signal: ctl.signal });
    if (r.status === 403 && office === 'main') r = await fetch(`${url}/v1/office/me/state?since=0&project=${ph}`, { headers: hdr, cache: 'no-store', credentials: 'omit', signal: ctl.signal });   // 一般會員網址帶 office=main：改讀自己的
    clearTimeout(tm); if (!r.ok) return null;
    const j = await r.json(), p = (j.projects || []).find(x => x.hash === ph); if (!p) return null;
    return { name: String(p.name || '') };
  } catch (e) { return null; }
}
/** 要不要用區塊辦公室：問得到名稱、而且不是 tw-rotation（問不到＝照舊完整辦公室，不冒險） */
export const wantsBlocks = pk => !!pk && !TW_NAME.test(pk.name.trim());

// ───────── 開場佈局：示範佈局縮成「只有 CEO 區塊」 ─────────
// CEO 區塊＝示範的 CEO 辦公室搬到大門正前方（保留桌子、地毯、書架、立燈、盆栽；沙發、第二個書架拿掉）。沒有牆、沒有窗、沒有其他房間。
export function blocksLayout(base) {
  const ceo = base.rooms.find(r => r.id === 'ceo'), dx = 16.5, dz = 19.6, keep = new Set(['rug_1', 'ceo_desk_2', 'bookshelf_3', 'plant_big_6', 'lamp_7', 'plant_8', 'plant_9', 'roomsign_10']);
  const furniture = base.furniture.filter(f => keep.has(f.id)).map(f => {
    const g = { ...f, x: Math.round((f.x + dx) * 100) / 100, z: Math.round((f.z + dz) * 100) / 100 };
    if (g.type === 'roomsign') { g.stand = true; g.z = dz + 0.5; }      // 沒有牆可以掛，改成立牌
    return g;
  });
  return { ...base, rooms: [{ ...ceo, x: dx, z: dz, d: 8.4 }], walls: [], windows: [], furniture: [...furniture, { id: 'blk_water', type: 'water', x: 23.2, z: 20.3, rot: 0 }], spots: base.spots, walkAreas: base.walkAreas };
}

// ───────── 區塊管理 ─────────
export function createBlocks(W, X) {
  const B = { on: true, agents: [], n: 0, log: [] }, layout = W.layout;
  const SIGN_Z = 0.6;
  if (W.floorBase) W.floorBase.visible = false;     // 示範辦公室那整片木地板拿掉：區塊直接放在外面那圈米色鋪面上，沒有區塊的地方就是空地

  // ───────── 外圍米色鋪面：依區塊實際範圍動態生成（區塊模式不鋪固定 40×30 的大片空地）─────────
  // 範圍 ＝ 所有區塊（含 CEO）的包圍盒 ＋ 邊距；南緣至少到大門外。新區塊長出來、同排重新置中時，鋪面用約 0.6 秒平順長到新範圍，不是瞬間跳。
  const floorRect = () => { let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; for (const r of layout.rooms) { x0 = Math.min(x0, r.x); x1 = Math.max(x1, r.x + r.w); z0 = Math.min(z0, r.z); z1 = Math.max(z1, r.z + r.d); } return { x0: x0 - FLOOR_M, x1: x1 + FLOOR_M, z0: z0 - FLOOR_M, z1: Math.max(z1 + FLOOR_M, GATE_Z) }; };
  const F = { mesh: null, cur: null, goal: null, busy: false };
  const paint = r => { const P = new Part(); P.slab(FLOOR_COLOR, r.x1 - r.x0, r.z1 - r.z0, 0.12, (r.x0 + r.x1) / 2, -0.13, (r.z0 + r.z1) / 2, 1.6); const g = P.geometry(); if (F.mesh) { F.mesh.geometry.dispose(); F.mesh.geometry = g; } else { F.mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 })); F.mesh.receiveShadow = true; F.mesh.castShadow = false; W.scene.add(F.mesh); } F.cur = { ...r }; W.shadowDirty && W.shadowDirty(); };
  B.floor = () => ({ ...(F.goal || floorRect()) });
  B.floorMesh = () => F.mesh;
  async function floorTo(instant) {
    F.goal = floorRect(); if (!F.cur || instant) { paint(F.goal); return; }
    if (F.busy) return; F.busy = true;
    try { const a = { ...F.cur }, t0 = W.time; for (;;) { const k = Math.min(1, (W.time - t0) / 0.6), e = k * k * (3 - 2 * k), g = F.goal, m = {}; for (const q of ['x0', 'x1', 'z0', 'z1']) m[q] = a[q] + (g[q] - a[q]) * e; paint(m); if (k >= 1) break; await W.sleep(0.02); } } finally { F.busy = false; }
    if (JSON.stringify(F.cur) !== JSON.stringify(F.goal)) paint(F.goal);
  }
  floorTo(true);

  const posOf = i => {
    const row = Math.floor(i / PER_ROW), inRow = Math.min(PER_ROW, B.agents.length - row * PER_ROW), col = i - row * PER_ROW;
    return { x: CX + (col - (inRow - 1) / 2) * PX - BW / 2, z: ROW0_Z - ROW_PZ * row };
  };
  const furnAdd = f => { const inst = W.addFurniture(f); return inst; };
  function signFurn(blk, x0, z0) { return { id: `blk${blk.n}_sign`, type: 'roomsign', x: Math.round((x0 + BW / 2) * 100) / 100, z: z0 + SIGN_Z, rot: 0, text: blk.title, color: blk.color, stand: true }; }

  /** 蓋一個區塊（地板＋桌子＋盆栽＋立牌）；回傳桌子 id */
  function build(blk, x0, z0) {
    const cx = x0 + BW / 2;
    const room = { id: 'blk_' + blk.n, name: blk.title, kind: 'zone', x: x0, z: z0, w: BW, d: BD, floor: blk.color };
    layout.rooms.push(room); W.buildRoomFloor(room); blk.room = room;
    const fs = [
      { id: `blk${blk.n}_desk`, type: 'workstation', x: cx, z: z0 + 3.0, rot: 2, owner: blk.id, dept: 'reserve' },
      { id: `blk${blk.n}_p1`, type: 'plant', x: x0 + 0.75, z: z0 + BD - 0.8, rot: 0 },
      { id: `blk${blk.n}_p2`, type: 'plant', x: x0 + BW - 0.75, z: z0 + BD - 0.8, rot: 0 },
      signFurn(blk, x0, z0),
    ];
    blk.fids = fs.map(f => f.id); blk.deskId = fs[0].id; blk.signId = fs[3].id;
    for (const f of fs) furnAdd(f);
  }
  /** 把一個蓋好的區塊平移到新位置（同排有人加入、排隊置中時用）：地板、家具、坐在桌前的人一起搬 */
  function move(blk, x0, z0) {
    const room = blk.room, dx = x0 - room.x, dz = z0 - room.z; if (!dx && !dz) return false;
    for (const id of blk.fids) { const inst = W.furn.get(id); if (!inst) continue; inst.f.x = Math.round((inst.f.x + dx) * 100) / 100; inst.f.z = Math.round((inst.f.z + dz) * 100) / 100; inst.home = { x: inst.f.x, z: inst.f.z, rot: inst.f.rot }; W.place(inst); }
    room.x = x0; room.z = z0; W.buildRoomFloor(room); return true;
  }
  /** 家具動過、座位物件被重建（respot 每次都產生新的座位物件）：把所有角色手上的座位換成新的同一個（用 uid 對）；搬動過的區塊裡坐著的人原地重新坐一次 */
  function rebind(blks) {
    const fids = new Set((blks || []).flatMap(b => b.fids));
    for (const c of W.chars.values()) {
      for (const k of ['spot', 'homeSpot']) { const o = c[k]; if (o && o.uid) { const n = W.spots.find(s => s.uid === o.uid); if (n && n !== o) { n.taken = o.taken || n.taken; c[k] = n; } } }
      if (c.state === 'sit' && c.atDesk && c.spot && c.spot.seat && fids.has(c.spot.fid)) { try { c.sitAt(c.spot.seat, { instant: true }); } catch (e) { /* 略 */ } }
    }
  }
  function relayout() {
    const moved = [];
    B.agents.forEach((blk, i) => { if (!blk.room) return; const p = posOf(i); if (move(blk, p.x, p.z)) moved.push(blk); });
    if (moved.length) { W.respot(); W.glowRebuild && W.glowRebuild(); rebind(moved); W.shadowDirty && W.shadowDirty(); }
  }
  // 新區塊「長出來」：地板由小放大、家具一個一個彈出（約 0.8 秒）。只做視覺，位置一開始就是最後的位置
  async function grow(blk) {
    const mesh = () => (W.rooms.get(blk.room.id) || {}).mesh, objs = () => blk.fids.map(id => (W.furn.get(id) || {}).obj).filter(Boolean), t0 = W.time, ease = k => { const c = 1.70158; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); };
    for (;;) {
      const k = Math.min(1, (W.time - t0) / 0.9), m = mesh(); if (m) m.scale.set(Math.max(0.001, ease(Math.min(1, k * 1.4))), 1, Math.max(0.001, ease(Math.min(1, k * 1.4))));
      objs().forEach((o, i) => { const s = Math.max(0.001, ease(Math.max(0, Math.min(1, (k - 0.15 - i * 0.08) / 0.5)))); o.scale.setScalar(s); });
      W.shadowDirty && W.shadowDirty();
      if (k >= 1) break; await W.sleep(0.02);
    }
    const m = mesh(); if (m) m.scale.set(1, 1, 1); objs().forEach(o => o.scale.setScalar(1)); W.shadowDirty && W.shadowDirty();
  }

  /** 替一位新同事配一個區塊；回傳他的座位（區塊滿了回 null＝站著）。b＝{id,nick,title} */
  B.claim = (b, arrive) => {
    if (B.agents.length >= CAPACITY) return null;
    const blk = { id: b.id, n: ++B.n, title: clip(b.title || b.nick || b.id), color: COLORS[B.n % COLORS.length], fids: [] };
    B.agents.push(blk); relayout();
    const p = posOf(B.agents.length - 1); build(blk, p.x, p.z); floorTo(false); W.scenery && W.scenery.update();   // 鋪面要等新區塊的房間登記進 layout 之後才算得到新範圍
    W.respot(); W.glowRebuild && W.glowRebuild(); rebind([]);
    const sp = W.spots.find(s => s.fid === blk.deskId && s.seat) || null;
    B.log.push('claim:' + b.id); if (W.refit) W.refit(!arrive);
    if (arrive) grow(blk);
    return sp;
  };
  /** 區塊名稱換成任務簡稱（先用類型名報到、之後才拿到派工說明時）。沒變就不動 */
  B.retitle = (id, title) => {
    const blk = B.agents.find(x => x.id === id), t = clip(title); if (!blk || !t || blk.title === t || !blk.room) return false;
    blk.title = t; blk.room.name = t;
    const old = W.furn.get(blk.signId);
    if (old) {
      const f = { ...old.f, text: t }; old.obj.parent && old.obj.parent.remove(old.obj); W.furn.delete(blk.signId);
      const k = W.pickFurn.indexOf(old.mesh); if (k >= 0) W.pickFurn.splice(k, 1);
      const inst = furnAdd(f); if (inst) { W.respot(); rebind([]); }
    }
    const m = W.members.get(id); if (m) m.deptName = t;
    return true;
  };
  /** 全部區塊（含 CEO）＋運動場＋遊民區的範圍，算出俯視鏡頭要看哪裡、拉多遠 */
  B.framing = aspect => {
    let x0 = 22.4, x1 = 37.6, z0 = 31.9, z1 = 38.8;          // 無業遊民區（22.4～37.6, 31.9～38.8）；新專案不開放運動場
    for (const r of layout.rooms) { x0 = Math.min(x0, r.x); x1 = Math.max(x1, r.x + r.w); z0 = Math.min(z0, r.z); }
    const wb = (x1 - x0) + 9, zb = (z1 - z0) + 5, dh = wb / (0.688 * Math.max(0.3, aspect)), dv = zb * 1.34;
    return { t: new THREE.Vector3((x0 + x1) / 2, 0, (z0 + z1) / 2), d: Math.max(30, Math.min(110, Math.max(dh, dv))) };
  };
  B.count = () => B.agents.length + 1;
  return B;
}
