// 績效獎勵層（rewards_design.md R0、R2）：讀 world/cfg/rewards.json，提供
//   ① 資料查詢：每位同事／部門／CEO 的等第、分數、升降、距離下一級、配件、設備等級（前端不重算等第，全讀檔案裡的結果）
//   ② 名牌上的等第字章、資訊卡的績效區塊
//   ③ 3D：部門設備等級換色（furniture.js／world.js 讀 makeStyleOf），招牌上的等第字章與琥珀小旗（共用一張圖集、一個網格、一次繪製）
//   ④ 點招牌／旗／入口大廳的看板 → 打開績效總表（ledger.js）
// 載入失敗或缺檔：整個獎勵層關閉，辦公室維持原樣（不能因為這個檔壞掉而整個壞掉）。
import { THREE, textPlane } from './kit.js';

export const GRADES = ['S', 'A', 'B', 'C', 'D', 'E', 'F'];
// 等第色（非紅綠；紅綠只給漲跌）。字色挑過對比：金／黃／琥珀底用深字，其餘用白字。
export const GCOL = { S: '#f0b429', A: '#4d73b8', B: '#1f7a75', C: '#f2cf4a', D: '#f2a93b', E: '#c2590c', F: '#5f7089' };
export const GINK = { S: '#4a3200', A: '#ffffff', B: '#ffffff', C: '#4a3a00', D: '#4a2e00', E: '#ffffff', F: '#ffffff' };
export const LV_NAME = ['', '簡配', '基本', '標準', '進階', '旗艦'];
export const DIM = { quality: '品質', speed: '速度', token: 'Token 效率', completion: '完成率', load: '人力負荷' };
const REASONS = ['quality', 'speed', 'token', 'completion', 'load'];

export async function loadRewards() {
  try {
    const r = await fetch('world/cfg/rewards.json'); if (!r.ok) return null;
    const j = await r.json(); if (!j || !Array.isArray(j.weeks) || !j.weeks.length || !j.rules || !Array.isArray(j.rules.grade)) return null;
    return j;
  } catch (e) { console.warn('績效資料載入失敗，獎勵層關閉', e); return null; }
}

// 蓋場景之前先用：回傳「這件家具／地板要用哪個設備等級」的查詢函式（world.js 的 ctx.style）
export function makeStyleOf(data, layout) {
  if (!data) return null;
  const wk = data.weeks[0], lv = new Map(); lv.set('ceo', { level: wk.ceo.level || 3, flag: null });
  for (const d of wk.depts) lv.set(d.id, { level: d.level || 3, flag: d.flag || null });
  const deptRooms = layout.rooms.filter(r => r.kind === 'dept'), ceoRoom = layout.rooms.find(r => r.id === 'ceo');
  const inRoom = (r, f) => f.x >= r.x && f.x <= r.x + r.w && f.z >= r.z && f.z <= r.z + r.d;
  return f => {
    let id = null;
    if (f.type === 'workstation' || f.type === 'deptsign') id = f.dept;
    else if (f.type === 'plant' || f.type === 'plant_big') { const r = deptRooms.find(q => inRoom(q, f)); id = r ? r.dept : (ceoRoom && inRoom(ceoRoom, f) ? 'ceo' : null); }
    else if (f.type === 'floor') id = f.room.dept;
    else if (f.id === 'rug_1' || f.type === 'ceo_desk') id = 'ceo';
    const row = id && lv.get(id); if (!row) return null;
    return { lv: row.level, dept: id, flag: row.flag ? { reason: row.flag.reason, big: row.level <= 1 } : null };
  };
}

export function createRewards(W, data, X) {
  const { ui, cv, camera } = X, R = { data, on: !!data, wi: 0, ledger: null };
  W.rewards = R; if (!data) return R;
  const rules = data.rules.grade, wkOf = i => data.weeks[Math.max(0, Math.min(data.weeks.length - 1, i))];
  const deptName = id => (id === 'ceo' ? 'CEO' : (W.org.departments.find(d => d.id === id) || {}).name || id);
  const nickOf = id => (id === 'ceo' ? 'CEO' : (W.members.get(id) || {}).nick || id), zhOf = id => (W.members.get(id) || {}).zh || '';
  R.deptName = deptName; R.nickOf = nickOf; R.zhOf = zhOf; R.weeks = data.weeks; R.rules = rules;
  R.reasonLabel = c => (c && data.reasonLabels[c]) || '';
  R.accLabel = c => data.accLabels[c] || c;

  // ── 查詢：第 wi 週的 CEO、部門、同事（wi=0 是最新一週）──
  const cache = new Map();
  function index(wi) {
    if (cache.has(wi)) return cache.get(wi);
    const w = wkOf(wi), depts = new Map(), agents = new Map();
    for (const d of w.depts) { depts.set(d.id, d); for (const [id, m] of Object.entries(d.members)) agents.set(id, { row: m, dept: d.id }); }
    const o = { w, ceo: w.ceo, depts, agents }; cache.set(wi, o); return o;
  }
  R.index = index;
  R.unit = (id, wi = 0) => { const x = index(wi); if (id === 'ceo') return { kind: 'ceo', id, row: x.ceo, dept: 'ceo' }; const a = x.agents.get(id); if (a) return { kind: 'agent', id, row: a.row, dept: a.dept, deptRow: x.depts.get(a.dept) }; const d = x.depts.get(id); return d ? { kind: 'dept', id, row: d, dept: id } : null; };
  R.gradeOf = id => { const u = R.unit(id); return u && u.row.grade ? u.row.grade : null; };
  R.levelOfDept = id => { const x = index(0); return id === 'ceo' ? x.ceo.level : (x.depts.get(id) || {}).level || 3; };
  // 距離下一級：回傳 { top, need, to, loss }（樣本不足 → null）
  R.next = row => {
    if (!row || row.grade == null) return null; const i = rules.findIndex(r => r[1] === row.grade); if (i < 0) return null;
    if (i === 0) return { top: true, streak: row.streak || 0 };
    return { top: false, need: Math.max(0.1, Math.round((rules[i - 1][0] - row.score) * 10) / 10), to: rules[i - 1][1], loss: row.top_loss && DIM[row.top_loss] ? DIM[row.top_loss] : '' };
  };
  // 需要加強：等第 D 以下、本週降級（等第比上週低）、有回報不實、部門有琥珀旗
  R.need = row => { if (!row) return false; const gi = g => GRADES.indexOf(g); return (row.grade && gi(row.grade) >= gi('D')) || !!(row.grade && row.prevGrade && gi(row.grade) > gi(row.prevGrade)) || (row.false_reports || 0) > 0 || !!row.flag; };
  const fmtDelta = r => (r.delta == null || r.grade == null ? null : r.delta);
  R.deltaHtml = r => { const d = fmtDelta(r); if (d == null) return '<span class="dl na">—</span>'; if (d === 0) return '<span class="dl flat">持平</span>'; return d > 0 ? `<span class="dl up" title="比上週高 ${d.toFixed(1)} 分">▲ +${d.toFixed(1)}</span>` : `<span class="dl down" title="比上週低 ${Math.abs(d).toFixed(1)} 分">▼ −${Math.abs(d).toFixed(1)}</span>`; };
  R.chip = g => (g ? `<span class="gc g-${g}" aria-label="等第 ${g}">${g}</span>` : '<span class="gc g-na" aria-label="樣本不足">—</span>');
  const ACC_G = { ring: '環', halo: '光', star: '星', cape: '披', glasses: '鏡', scarf: '巾', nameplate: '牌', trophy: '盃', frame: '狀', mvp: '最', pet: '寵', todo: '待', lamp: '燈', mentor: '導', sprout: '芽', pause: '停' };
  const accCls = c => (/gold|halo|trophy|mvp|pet/.test(c) ? 'au' : /silver|satin|frame/.test(c) ? 'ag' : 'am');
  R.accChips = (codes, max = 9) => { const l = (codes || []).filter(c => c !== 'grade_chip'); if (!l.length) return '<span class="na">—</span>'; return l.slice(0, max).map(c => `<i class="ac ${accCls(c)}" title="${R.accLabel(c)}" aria-label="${R.accLabel(c)}">${ACC_G[c.split('_')[0]] || '·'}</i>`).join(''); };
  R.levelText = (row, short) => { const lv = row.level || 3; return `L${lv}${short ? '' : '（' + LV_NAME[lv] + '）'}${row.levelPending ? (short ? '↻' : '・緩衝中，之後 L' + row.levelPending.to) : ''}`; };

  // ── 名牌字章 ──
  R.tagChip = c => {
    const L = c._lab; if (!L || !L.gr) return; const g = c.spec.pet ? null : R.gradeOf(c.spec.id);
    if (L.grv !== g) { L.grv = g; L.gr.textContent = g || ''; L.gr.className = 'gr' + (g ? ' g-' + g : ''); L.tag.classList.toggle('hasgr', !!g); L.mk = ''; }
  };
  R.refreshTags = () => { for (const c of [...W.chars.values()]) R.tagChip(c); };

  // ── 資訊卡的績效區塊（ui.showCard 呼叫）──
  const HELP = '等第依六個面向計分：品質 30%、完成率 25%、速度 15%、Token 效率 15%、可靠度 10%、協作與主動 5%。' + rules.map((r, i) => `${r[1]}：${i === 0 ? '≥' + r[0] : i === rules.length - 1 ? '<' + rules[i - 1][0] : r[0] + '–' + (rules[i - 1][0] - 1)}`).join('、') + '。單週派工件數不到 3 件顯示「樣本不足」，不扣也不加。';
  R.HELP = HELP;
  R.cardBlock = spec => {
    const u = R.unit(spec.id); if (!u) return ''; const r = u.row, wk = index(0).w.week.slice(5), dr = u.deptRow || (u.kind === 'ceo' ? r : null), lvRow = u.kind === 'ceo' ? r : dr;
    const nx = R.next(r);
    const l1 = r.grade ? `${R.chip(r.grade)}<b class="sc">${r.score}</b><span class="u">分</span>${R.deltaHtml(r)}<em>${wk}</em>` : `${R.chip(null)}<b class="sc na">樣本不足</b><em>${wk}</em>`;
    const l2 = nx ? (nx.top ? `已是最高等第${nx.streak ? '・連勝第 ' + nx.streak + ' 週' : ''}` : `距離下一級：再 +${nx.need} 分到 ${nx.to}${nx.loss ? '・最拖分：' + nx.loss : ''}`) : '本週派工不到 3 件，不評等第';
    const l3 = `<span class="rwa">配件 ${R.accChips(r.acc, 8)}</span><span class="rwl">${u.kind === 'ceo' ? '辦公室' : '設備'} ${lvRow ? R.levelText(lvRow) : '—'}</span>`;
    return `<div class="rw" id="rwBox"><div class="rw1">${l1}<button class="q2" data-rwq aria-expanded="false" aria-label="等第怎麼算">?</button></div><div class="rw2">${l2}</div><div class="rw3">${l3}</div><p class="rwh" hidden>${HELP}</p></div>`;
  };

  // ── 3D：招牌字章＋琥珀小旗（一張圖集、一個網格、一次繪製）──
  const CWID = 96, atlas = document.createElement('canvas'); atlas.width = CWID * 7; atlas.height = CWID * 2;
  { const c = atlas.getContext('2d'); c.textAlign = 'center'; c.textBaseline = 'middle';
    GRADES.forEach((g, i) => { const x = i * CWID + CWID / 2, y = CWID / 2; c.fillStyle = '#fffaf2'; c.beginPath(); c.arc(x, y, 42, 0, 7); c.fill(); c.fillStyle = GCOL[g]; c.beginPath(); c.arc(x, y, 36, 0, 7); c.fill(); c.fillStyle = GINK[g]; c.font = '800 54px "Noto Sans TC","Microsoft JhengHei",sans-serif'; c.fillText(g, x, y + 3); });
    REASONS.forEach((k, i) => {
      const x0 = i * CWID, y0 = CWID; c.fillStyle = '#f2a93b'; c.strokeStyle = '#a8710f'; c.lineWidth = 4; c.beginPath(); c.roundRect(x0 + 5, y0 + 10, CWID - 10, CWID - 20, 8); c.fill(); c.stroke();   // 旗面（正反兩面各一片，不做燕尾，避免背面左右顛倒）
      const cx = x0 + CWID / 2, cy = y0 + CWID / 2; c.strokeStyle = '#4a2e00'; c.fillStyle = '#4a2e00'; c.lineWidth = 6; c.lineCap = 'round'; c.lineJoin = 'round';
      if (k === 'quality') { c.beginPath(); c.arc(cx, cy, 17, 0, 7); c.stroke(); c.beginPath(); c.arc(cx, cy, 4, 0, 7); c.fill(); }
      else if (k === 'speed') { c.beginPath(); c.arc(cx, cy, 18, 0, 7); c.stroke(); c.beginPath(); c.moveTo(cx, cy - 11); c.lineTo(cx, cy); c.lineTo(cx + 8, cy + 5); c.stroke(); }
      else if (k === 'token') { c.beginPath(); c.arc(cx, cy, 18, 0, 7); c.stroke(); c.fillRect(cx - 9, cy - 3, 18, 6); }
      else if (k === 'completion') { c.strokeRect(cx - 16, cy - 16, 32, 32); c.beginPath(); c.moveTo(cx - 9, cy); c.lineTo(cx - 2, cy + 8); c.lineTo(cx + 10, cy - 8); c.stroke(); }
      else { [[-14, 24], [-3, 34], [8, 16]].forEach(([dy, w]) => { c.beginPath(); c.moveTo(cx - 17, cy + dy); c.lineTo(cx - 17 + w, cy + dy); c.stroke(); }); }
    });
  }
  const atlasTex = new THREE.CanvasTexture(atlas); atlasTex.colorSpace = THREE.SRGBColorSpace; atlasTex.anisotropy = 4;
  const marksMat = new THREE.MeshBasicMaterial({ map: atlasTex, transparent: true, alphaTest: 0.15, toneMapped: false });
  let marks = null, quads = [];
  R.rebuildMarks = () => {
    if (marks) { marks.geometry.dispose(); marks.removeFromParent(); marks = null; } quads = [];
    const pos = [], uv = [], idx = [], info = [];
    const quad = (cx, cy, cz, w, h, front, col, row, meta) => {
      const u0 = col / 7, u1 = (col + 1) / 7, v1 = 1 - row / 2, v0 = 1 - (row + 1) / 2, a = front ? -1 : 1, n = pos.length / 3;
      pos.push(cx + a * w / 2, cy - h / 2, cz, cx - a * w / 2, cy - h / 2, cz, cx - a * w / 2, cy + h / 2, cz, cx + a * w / 2, cy + h / 2, cz);
      uv.push(u0, v0, u1, v0, u1, v1, u0, v1); idx.push(n, n + 1, n + 2, n, n + 2, n + 3); info.push(meta);
    };
    const wk = index(0).w;
    for (const inst of W.furn.values()) {
      const dept = inst.spec.deptsign; if (!dept) continue; const row = index(0).depts.get(dept); if (!row) continue; const f = inst.f;
      if (row.grade) for (const fr of [true, false]) quad(f.x + 0.6, 1.8, f.z + (fr ? 0.04 : -0.04), 0.34, 0.34, fr, GRADES.indexOf(row.grade), 0, { dept, kind: 'chip' });
      if (row.flag) { const k = Math.max(0, REASONS.indexOf(row.flag.reason)), big = row.level <= 1, w = big ? 0.68 : 0.52, h = big ? 0.47 : 0.36, top = big ? 1.9 : 1.65;
        for (const fr of [true, false]) quad(f.x - 1.12 - w / 2 + 0.01, top - h / 2 - 0.04, f.z + (fr ? 0.012 : -0.012), w, h, fr, k, 1, { dept, kind: 'flag', reason: row.flag.reason }); }
    }
    quads = info; if (!info.length) return;
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx);
    marks = new THREE.Mesh(g, marksMat); marks.frustumCulled = false; marks.userData.rewardsMarks = true; W.scene.add(marks); R.marks = marks; void wk;
  };
  R.rebuildMarks(); R.markInfo = () => quads.map(q => ({ ...q }));
  // 入口大廳的看板（打卡機）：加一塊小招牌＋一個隱形的大點擊範圍（不畫出來、不加繪製次數）
  const kiosk = [...W.furn.values()].find(i => i.f.type === 'kiosk');
  let kProxy = null;
  if (kiosk) {
    const tp = textPlane('績效總表', 0.78, 0.22, { pw: 384, bg: '#fff3d6', border: '#f2a93b', borderW: 8, px: 70, radius: 28 }); tp.position.set(0, 1.5, 0.02); kiosk.obj.add(tp);
    kProxy = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.7, 1.0), new THREE.MeshBasicMaterial()); kProxy.visible = false; kProxy.position.set(0, 0.85, 0); kiosk.obj.add(kProxy); kProxy.updateMatrixWorld(true);
  }
  const signMeshes = [...W.furn.values()].filter(i => i.spec.deptsign).map(i => i.mesh);
  R.pick = ray => {   // main.js 點一下時呼叫：點到旗、字章、招牌、看板 → 打開績效總表
    const list = [...(marks ? [marks] : []), ...signMeshes, ...(kProxy ? [kProxy] : [])]; kProxy && kProxy.updateMatrixWorld(true);
    const hit = ray.intersectObjects(list, false)[0]; if (!hit) return false;
    let dept = null; const o = hit.object;
    if (o === marks) { const m = quads[hit.faceIndex >> 1]; dept = m && m.dept; } else if (o !== kProxy) dept = (W.furn.get(o.userData.fid) || { spec: {} }).spec.deptsign || null;
    R.openLedger(dept); return true;
  };
  R.openLedger = dept => { if (R.ledger) R.ledger.open(dept); };

  // 滑到琥珀旗上顯示原因（HTML 提示框）；滑到可點的東西游標變手指
  const tip = document.createElement('div'); tip.id = 'rwTip'; tip.className = 'rw-tip'; tip.hidden = true; document.getElementById('app').append(tip);
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(); let tT = 0, hovering = false;
  cv.addEventListener('pointermove', e => {
    if (e.pointerType === 'touch' || (e.buttons & 7)) return; const t = performance.now(); if (t - tT < 70) return; tT = t;
    const r = cv.getBoundingClientRect(); ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); ray.setFromCamera(ndc, camera);
    const list = [...(marks ? [marks] : []), ...signMeshes, ...(kProxy ? [kProxy] : [])]; const hit = ray.intersectObjects(list, false)[0];
    if (!hit) { if (hovering) { cv.style.cursor = ''; hovering = false; } tip.hidden = true; return; }
    hovering = true; cv.style.cursor = 'pointer';
    let txt = '';
    if (hit.object === marks) { const m = quads[hit.faceIndex >> 1]; if (m && m.kind === 'flag') { const d = index(0).depts.get(m.dept); txt = `${deptName(m.dept)}・${(d.flag && d.flag.text) || '待加強'}：${R.reasonLabel(m.reason)}${d.advice ? '。' + d.advice : ''}`; } else if (m) { const d = index(0).depts.get(m.dept); txt = `${deptName(m.dept)}　本週等第 ${d.grade}・設備 ${R.levelText(d, true)}`; } }
    else if (hit.object === kProxy) txt = '績效總表';
    else { const dp = (W.furn.get(hit.object.userData.fid) || { spec: {} }).spec.deptsign, d = dp && index(0).depts.get(dp); if (d) txt = `${deptName(dp)}　本週等第 ${d.grade}・設備 ${R.levelText(d, true)}`; }
    if (!txt) { tip.hidden = true; return; }
    tip.textContent = txt; tip.hidden = false; const w = tip.offsetWidth; tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, e.clientX + 14)) + 'px'; tip.style.top = Math.max(8, e.clientY - 44) + 'px';
  });
  cv.addEventListener('pointerleave', () => { tip.hidden = true; });
  R.refreshTags();
  return R;
}
