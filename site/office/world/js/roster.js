// 專案名冊（2026-11-16）：進入某個專案的辦公室時，只顯示 CEO ＋ 這個專案「真的有」的 Agent，不再載入示範的 40 多位。
//
// 擁有者原話：「理論上不同專案裡面的辦公室、員工 Agent 都不同，Agent 都會依據當前專案需求新增員工。」
//
// 做法（為什麼不是「不建立示範角色」）：示範的 40 位在 main.js 開場一次建好，很多模組（心情、績效、人事…）都靠 W.chars 查人，
//   拿掉會到處出現 undefined。所以沿用 empty.js「空辦公室」已經驗過的做法：建好之後全部標成 away＋absent、看不見、不佔座位；
//   名冊裡有誰才讓誰露面。名冊來源是收件端 state 的 roster（專案 .claude/agents 檔名 ∪ 事件裡出現過的子 Agent 類型），
//   live.js 的 memberFor 在 roster 模式下把每個類型交給這裡：
//     · 跟示範編制同代號的（例如 inspector）→ 直接讓那位露面，坐他原本的座位（沒空就坐別的空位）；
//     · 其他的 → 依類型自動分配部門（關鍵字對照；對不上＝「一般」），坐該部門的空桌；沒空桌就坐別部門的、再沒有就自動加一張桌。
//   開場時（第一次讀到名冊）直接就座；之後才出現的新類型＝「報到演出」：從大門走進來、走到新座位坐下。
//
// 只在「網址帶 project＋即時模式（有登入或接入碼、沒開展示模式）」時啟用；示範辦公室（world.html）完全不經過這裡。
import { textPlane } from './kit.js';

/** 跟 live.js 的 hasCred()／展示模式判斷同一套（要在 live.js 載入之前、開場建角色時就知道，所以這裡自己讀一次） */
export function rosterWanted(qs) {
  try {
    if (!/^[0-9a-f]{16}$/.test(qs.get('project') || '') || qs.get('demo') === '1') return false;
    if (/(?:^#|&)aio=[A-Za-z0-9_-]{8,200}/.test(location.hash || '')) return true;
    let cfg = {}; try { cfg = JSON.parse(localStorage.getItem('aiOffice.live.v1') || 'null') || {}; } catch (e) { cfg = {}; }
    let tok = null; try { tok = localStorage.getItem('tw.acct.tok'); } catch (e) { tok = null; }
    return !!(cfg.code || (cfg.login && tok)) && !cfg.show;
  } catch (e) { return false; }
}

// 類型名稱 → 部門（先比先贏）。只是「放在哪一區」的建議，對不上就放「一般」；不影響這位 Agent 能做什麼。
export const DEPT_KEYS = [
  ['audit', /test|qa\b|review|audit|inspect|verif|check|lint|critic|monitor|watch/i],
  ['legal', /legal|law|secur|privacy|complian|policy|licen[sc]e|safety|risk/i],
  ['ops', /deploy|release|ops\b|devops|infra|\bci\b|\bcd\b|build|plan|schedul|deliver|runner|migrat|setup|config|status/i],
  ['frontend', /front|\bui\b|\bux\b|web|css|html|react|vue|mobile|\bapp\b|browser|canvas|three|component|page/i],
  ['design', /design|art\b|artist|illustr|visual|brand|logo|style|figma|draw|image/i],
  ['video', /video|anim|motion|film|story|sound|audio|music|voice/i],
  ['social', /social|content|writer|editor|post|copy|blog|doc|translat|community|news/i],
  ['biz', /market|sales|pric|pay|billing|business|growth|product|seo|customer|support|store/i],
  ['data', /data|scrap|crawl|etl|sql|database|pipeline|ingest|storage|index|parse/i],
  ['quant', /quant|backtest|strateg|math|stat|model|\bml\b|finance|algo|forecast/i],
  ['industry', /research|analy|explor|search|survey|intel|domain|industry|knowledge|guide|librar|fetch|find/i],
];
export function deptOf(type) {
  const t = String(type || '');
  for (const [d, re] of DEPT_KEYS) if (re.test(t)) return d;
  return null;                                  // 對不上＝一般
}

export function createRoster(W, X) {
  const D = X.director, C = id => W.chars.get(id);
  const R = { on: true, hired: new Map(), desks: 0, log: [] };
  W.seatOwner = new Map();                      // 桌子原本的主人代號 → 現在坐的人（螢幕亮不亮要看現在坐的人）
  const furnOf = s => W.furn.get(s.fid), ownerOf = s => (furnOf(s) && furnOf(s).f.owner) || s.name.replace(/^seat:/, '');
  const isDeskSpot = s => s.seat && s.name !== 'seat:ceo' && (/^seat:/.test(s.name) || s.name === 'reserve');
  const deptColor = d => ((W.org.departments || []).find(q => q.id === d) || {}).color || '#8aa4d6';

  // ── 桌上的名牌：換成現在坐的人（沒人坐＝收起來），不然別人的桌上寫著示範同事的名字 ──
  function plateOf(inst) { const e = inst && inst.spec && inst.spec.extras; return e && e[0] && e[0].material && e[0].userData && e[0].userData.tex ? e[0] : null; }
  function relabel(s, spec) {
    const inst = furnOf(s), pl = plateOf(inst); if (!pl) return;
    if (!spec) { pl.visible = false; return; }
    if (!inst.f || inst.f.type !== 'workstation') { pl.visible = false; return; }        // 其他家具的名牌尺寸不同，不硬換
    try {
      const nw = textPlane([spec.nick || spec.id, spec.zh || ''], 0.44, 0.17, { pw: 256, bg: '#fffaf2', border: deptColor(inst.f.dept), borderW: 8, px: 44, subScale: 0.5, radius: 22 });
      const old = pl.userData.tex; pl.material.map = nw.userData.tex; pl.userData.tex = nw.userData.tex; pl.material.needsUpdate = true; pl.visible = true;
      nw.geometry.dispose(); nw.material.dispose(); if (old && old.dispose) old.dispose();
    } catch (e) { /* 名牌換不了就留原樣，不影響就座 */ }
  }

  // ── 藏起來／露面 ──
  function hide(c) {
    if (!c || c.spec.isCeo) return;
    c.absent = true; c.away = true; c.busy = true; c.atDesk = false; c.setVisible(false);
    try { D.release && D.release(c); } catch (e) { /* 略 */ }
    for (const s of [c.spot, c.homeSpot]) if (s && s.taken === c.spec.id) s.taken = null;
    c.spot = null; c.homeSpot = null;
  }
  R.boot = () => {
    for (const c of [...W.chars.values()]) hide(c);
    for (const p of W.pets || []) { p.away = true; p.setVisible(false); }
    for (const s of W.spots) if (isDeskSpot(s)) { s.taken = null; relabel(s, null); }
    R.log.push('boot');
  };
  // CEO 的寵物只跟著 CEO（CEO 一直在）
  R.petsOf = id => { for (const p of W.pets || []) if (p.spec.owner === id) { p.away = false; p.setVisible(true); } };

  // ── 找座位 ──
  function freeSpots() { return W.spots.filter(s => isDeskSpot(s) && !s.taken); }
  function pickSeat(dept, own) {
    const fr = freeSpots(); if (!fr.length) return null;
    const ws = fr.filter(s => /^seat:/.test(s.name));
    return (own && ws.find(s => s.name === 'seat:' + own)) || (dept && ws.find(s => furnOf(s) && furnOf(s).f.dept === dept)) || ws[0] || fr.find(s => s.name === 'reserve') || null;
  }
  // 座位不夠：在辦公室空地加一張桌子（優先放在該部門的房間，再來是任何部門房間、最後整間）。找不到空位就回 null，角色改站著。
  function addDesk(dept, id) {
    if (!W.addFurniture || !W.respot) return null;
    const rooms = W.layout.rooms || [], pref = [...rooms.filter(r => r.kind === 'dept' && r.dept === dept), ...rooms.filter(r => r.kind === 'dept'), ...rooms];
    const isF = (x, z) => W.nav.isFree(x, z);
    for (const r of pref) for (let z = r.z + 1.2; z < r.z + r.d - 1.2; z += 1.0) for (let x = r.x + 1.2; x < r.x + r.w - 1.2; x += 1.0) {
      if (Math.abs(x - 20.5) < 2.2 && z > 22) continue;                 // 大門正前方的走道不擋
      const pts = [[0, 0], [-0.8, 0], [0.8, 0], [0, 0.8], [-0.7, 1.2], [0.7, 1.2], [0, 1.6], [0, -0.4]];
      if (!pts.every(([dx, dz]) => isF(x + dx, z + dz))) continue;
      const fid = 'workstation_dyn_' + (++R.desks), f = { id: fid, type: 'workstation', x: Math.round(x * 100) / 100, z: Math.round(z * 100) / 100, rot: 2, owner: id, dept: dept || 'reserve' };
      let inst = null;
      try { inst = W.addFurniture(f); W.respot(); W.glowRebuild && W.glowRebuild(); } catch (e) { inst = null; }
      const sp = inst && W.spots.find(s => s.fid === fid && s.seat);
      if (sp && W.nav.isReach(sp.x, sp.z)) return sp;
      if (inst) { try { inst.obj.parent && inst.obj.parent.remove(inst.obj); W.furn.delete(fid); const k = W.pickFurn.indexOf(inst.mesh); if (k >= 0) W.pickFurn.splice(k, 1); W.respot(); W.glowRebuild && W.glowRebuild(); } catch (e) { /* 略 */ } }
    }
    return null;
  }

  // ── 就座／報到演出 ──
  function seat(c, s, arrive) {
    c.absent = false; c.away = false; c.busy = false;
    if (s) {
      s.taken = c.spec.id; c.spot = s; c.homeSpot = s; W.seatOwner.set(ownerOf(s), c.spec.id); relabel(s, c.spec);
    }
    R.petsOf(c.spec.id);
    if (arrive && D.arrive) { c.busy = true; D.arrive(c).then(() => { c.busy = false; }, () => { c.busy = false; }); return; }
    c.setVisible(true);
    if (s) { c.sitAt(s.seat, { instant: true }); c.atDesk = true; c.setAction('type'); c.workAt = W.time + 3 + Math.random() * 6; }
    else { const f = W.nav.nearestFree(21, 27, 12) || { x: 21, z: 27 }; c.standAt(f.x, f.z, Math.PI); c.setAction('idle'); }
  }

  /** 示範編制裡同代號的人：讓他露面。已經在了就不動。 */
  R.reveal = (id, arrive) => {
    const c = C(id); if (!c || c.spec.isCeo || c.spec.pet) return null;
    if (!c.absent) return c;
    seat(c, pickSeat(c.spec.dept, id) || addDesk(c.spec.dept, id), arrive); R.hired.set(id, c); return c;
  };
  /** 編制外的新同事：b＝{id,nick,zh,species,pal,hue,acc,accColor}；回傳角色（座位都沒有時站著） */
  R.hire = (b, arrive) => {
    if (C(b.id)) return C(b.id);
    const dept = deptOf(b.zh || b.id), spec = { ...b, dept: dept || 'reserve' };
    let c; try { c = W.addExtra(spec); } catch (e) { console.warn('新增同事失敗', e); return null; }
    W.extras.splice(W.extras.indexOf(c), 1); W.chars.set(b.id, c);
    const dn = dept && (W.org.departments.find(q => q.id === dept) || {}).name;
    W.members.set(b.id, { id: b.id, nick: b.nick, zh: b.zh, dept: dept || 'reserve', deptName: dn || '一般' });
    seat(c, pickSeat(dept, null) || addDesk(dept, b.id), arrive); R.hired.set(b.id, c); R.log.push('hire:' + b.id + ':' + (dept || '一般'));
    return c;
  };
  return R;
}
