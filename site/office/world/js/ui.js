// 介面：工具列、區域清單、示範選單、角色進度卡、佈告欄、會議紀錄。全部繁體中文。
import { rng } from './furniture.js';

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export function createUI(W, demo, api) {
  const U = {}; const pops = ['areaPop', 'demoPop', 'helpPop'];
  const closePops = () => pops.forEach(p => { $(p).hidden = true; }), btnOf = { areaPop: 'areaBtn', demoPop: 'demoBtn', helpPop: 'helpBtn' };
  function togglePop(id) {
    const el = $(id), was = el.hidden; closePops(); if (!was) return;
    el.hidden = false; const r = $(btnOf[id]).getBoundingClientRect(), w = el.offsetWidth;
    el.style.top = (r.bottom + 8) + 'px'; el.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px';
  }
  U.closePops = closePops;
  let toastT = 0;
  U.toast = t => { const el = $('toast'); el.textContent = t; el.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => { el.hidden = true; }, 2600); };

  // 說明（收進「?」）
  $('helpPop').innerHTML = `<ul>
    <li>拖曳移動畫面；滾輪或雙指縮放；右鍵拖曳或雙指轉動可旋轉。</li>
    <li>點角色：看他的進度卡，鏡頭跟著他。</li>
    <li>點佈告欄：看 CEO 或該部門的公告。</li>
    <li>「示範」：重播一場會議、上下班與日常行為（示範資料）。</li>
    <li>「整修」：拖曳家具、旋轉、換地板顏色，會記在這台裝置上。</li>
  </ul>`;
  $('helpBtn').onclick = () => togglePop('helpPop');

  // 區域清單
  const rooms = W.layout.rooms, order = ['ceo', 'meeting', 'library', 'pantry', 'food', 'lounge', 'play', 'reserve', 'lobby'];
  const dot = c => `<span class="dot" style="background:${c}"></span>`;
  $('areaPop').innerHTML = `<h4>公共區域</h4><div class="grid c3">${order.map(id => { const r = rooms.find(q => q.id === id); return `<button class="it" data-room="${id}">${dot(r.floor)}${esc(r.name)}</button>`; }).join('')}</div>
    <h4 style="margin-top:12px">部門</h4><div class="grid">${W.org.departments.map(d => `<button class="it" data-room="${d.id}">${dot(d.color)}${esc(d.name)}<small>${d.members.length} 人</small></button>`).join('')}</div>`;
  $('areaBtn').onclick = () => togglePop('areaPop');
  $('areaPop').onclick = e => { const b = e.target.closest('[data-room]'); if (b) { closePops(); api.jumpTo(b.dataset.room); } };

  // 示範選單
  const demos = [['meeting', '開一場會', '召集、討論、白板、散會、回報'], ['clockout', '下班', '幾位同事從大門離開'], ['clockin', '上班', '從大門進來回座位'], ['coffee', '倒咖啡', ''], ['lookup', '查資料', ''], ['rest', '休息一下', ''], ['play', '去遊樂區', ''], ['snack', '吃點心', '']];
  const renderDemo = () => {
    $('demoPop').innerHTML = `<div class="grid">${demos.map(([k, n, s], i) => `<button class="it" data-demo="${k}" ${i === 0 ? 'style="grid-column:1/-1"' : ''}>${esc(n)}${s ? `<small>${esc(s)}</small>` : ''}</button>`).join('')}
      <button class="it" data-demo="ambient" style="grid-column:1/-1">日常行為自動播放<small>${api.ambient() ? '開' : '關'}</small></button></div>`;
  };
  $('demoBtn').onclick = () => { renderDemo(); togglePop('demoPop'); };
  $('demoPop').onclick = e => { const b = e.target.closest('[data-demo]'); if (!b) return; if (b.dataset.demo === 'ambient') { api.runDemo('ambient'); renderDemo(); return; } closePops(); api.runDemo(b.dataset.demo); };

  // 視角與速度
  $('viewSeg').onclick = e => { const b = e.target.closest('button'); if (b) api.setView(b.dataset.v); };
  U.setViewUI = (mode, c) => {
    const vc = $('viewChar'); if (mode === 'char' && c) { vc.hidden = false; vc.textContent = c.spec.nick; } else if (mode !== 'char') vc.hidden = true;
    $('viewSeg').querySelectorAll('button').forEach(b => b.classList.toggle('on', b.dataset.v === mode));
  };
  $('speedSeg').onclick = e => { const b = e.target.closest('button'); if (!b) return; api.setSpeed(+b.dataset.s); $('speedSeg').querySelectorAll('button').forEach(q => q.classList.toggle('on', q === b)); };
  $('editBtn').onclick = () => api.toggleEdit();

  // ── 角色進度卡（示範資料：依職稱代號固定產生，每次打開都一樣） ──
  const pad = n => String(n).padStart(2, '0');
  function progress(spec) {
    const r = rng('p' + spec.id), pool = (demo.tasks[spec.dept] || demo.tasks.ceo).slice(), base = new Date('2026-11-13T10:30:00+08:00').getTime();
    const stamp = minsAgo => { const d = new Date(base - minsAgo * 60000 + 8 * 3600000); return `${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`; };
    const nDone = 3 + Math.floor(r() * 6), nDoing = 1 + Math.floor(r() * 2), nTodo = Math.floor(r() * 3), list = [];
    for (let i = 0; i < nDoing; i++) list.push({ s: 2, title: pool[i % pool.length], t: stamp(20 + i * 35 + Math.floor(r() * 20)) });
    for (let i = 0; i < nTodo; i++) list.push({ s: 1, title: pool[(i + nDoing) % pool.length], t: stamp(-30 - i * 60) });
    for (let i = 0; i < nDone; i++) list.push({ s: 3, title: pool[(i + 2) % pool.length], t: stamp(90 + i * 170 + Math.floor(r() * 60)) });
    const eta = 15 + Math.floor(r() * 50);
    return { nDone, nDoing, nTodo, list, eta: stamp(-eta), etaMin: eta, opt: demo.optimize[Math.floor(r() * demo.optimize.length)], lastDone: list.find(x => x.s === 3).t, lastDoing: list[0].t, nextTodo: nTodo ? list.find(x => x.s === 1).t : '' };
  }
  const STATE = c => c.away ? '已下班' : c.state === 'walk' ? '走路中' : (c.atDesk ? (c.spec.isCeo ? '坐在位子上處理公事' : `坐在位子上工作${c.task ? '：' + c.task : ''}`) : (c.state === 'sit' ? '坐著' : '離開座位'));
  let cardChar = null;
  U.showCard = c => {
    cardChar = c; $('board').hidden = true; const s = c.spec, p = progress(s), m = W.members.get(s.id) || s;
    $('card').innerHTML = `<button class="x" aria-label="關閉">×</button>
      <div class="hd"><div class="ava" style="background:${s.isCeo ? '#ffb057' : s.color}"></div><div><b>${esc(s.nick)}</b>${s.lead ? '<span class="tag2">主管</span>' : ''}
        <p>${esc(s.id)}・${esc(s.zh)}・${esc(s.race)}${m.deptName ? '・' + esc(m.deptName) : ''}</p></div></div>
      <div class="now" id="cardNow">目前：${esc(STATE(c))}</div>
      <div class="kpi"><div class="k1"><span>未完成</span><b>${p.nTodo}</b><em>${p.nextTodo ? '排 ' + p.nextTodo : '—'}</em></div><div class="k2"><span>進行中</span><b>${p.nDoing}</b><em>起 ${p.lastDoing}</em></div><div class="k3"><span>已完成</span><b>${p.nDone}</b><em>末 ${p.lastDone}</em></div></div>
      <dl class="meta"><dt>預估完成</dt><dd>${p.eta}（約 ${p.etaMin} 分鐘後）</dd><dt>能否優化</dt><dd>${esc(p.opt)}</dd></dl>
      <div class="list">${p.list.map(x => `<div class="row"><i class="s${x.s}"></i><span>${esc(x.title)}</span><time>${['', '排定', '開始', '完成'][x.s]} ${x.t}</time></div>`).join('')}</div>
      <div class="acts"><button class="btn" data-a="ceo">回 CEO 視角</button><button class="btn" data-a="god">俯瞰</button></div>`;
    $('card').hidden = false;
  };
  U.tickCard = () => { if (cardChar && !$('card').hidden) { const el = $('cardNow'), t = '目前：' + STATE(cardChar); if (el && el.textContent !== t) el.textContent = t; } };
  $('card').onclick = e => { if (e.target.closest('.x')) { $('card').hidden = true; api.cardClosed(); return; } const b = e.target.closest('[data-a]'); if (b) { $('card').hidden = true; api.setView(b.dataset.a); } };
  U.hideCard = () => { $('card').hidden = true; };

  // ── 佈告欄 ──
  U.showBoard = owner => {
    $('card').hidden = true; const d = W.org.departments.find(q => q.id === owner), name = owner === 'ceo' ? 'CEO 佈告欄' : d.name + '佈告欄', notes = demo.boards[owner] || [];
    $('board').innerHTML = `<button class="x" aria-label="關閉">×</button><h3><span class="dot" style="width:12px;height:12px;border-radius:50%;background:${owner === 'ceo' ? '#ffb057' : d.color}"></span>${esc(name)}</h3>
      <div class="scroll">${notes.map(n => `<div class="note${n.isNew ? ' new' : ''}"><time>${esc(n.t)}</time><b>${esc(n.title)}</b><p>${esc(n.text)}</p></div>`).join('') || '<p>目前沒有公告</p>'}</div>`;
    $('board').hidden = false;
  };
  $('board').onclick = e => { if (e.target.closest('.x')) $('board').hidden = true; };
  U.postBoard = (owner, note) => { (demo.boards[owner] = demo.boards[owner] || []).unshift({ ...note, isNew: true }); U.toast('會議結論已貼上 CEO 佈告欄'); };
  U.fmtTs = ts => { const m = /(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/.exec(ts || ''); return m ? `${m[2]}-${m[3]} ${m[4]}:${m[5]}` : ''; };

  // ── 會議紀錄 ──
  let shown = 0;
  U.meetingOpen = m => {
    shown = 0; $('log').classList.remove('mini');
    $('log').innerHTML = `<button class="x" aria-label="收合">–</button><h3>會議紀錄<small>${esc(m.topic)}</small></h3><button class="lnk" id="logSrcBtn">看原始派工</button><div id="logSrc" hidden>${esc(m.source || '')}</div><div id="logList"></div>`;
    $('log').hidden = false;
  };
  U.meetingLine = m => {
    const list = $('logList'); if (!list) return;
    for (; shown < m.lines.length; shown++) { const l = m.lines[shown], el = document.createElement('div'); el.className = 'ln ' + (l.k === 'note' ? 'note2' : l.k); el.innerHTML = `<b>${esc(l.who)}</b><i>${esc(l.kind)}</i>${esc(l.text)}`; list.appendChild(el); }
    list.scrollTop = list.scrollHeight;
  };
  U.meetingClosed = () => { U.toast('散會，大家回座位開始工作'); };
  $('log').onclick = e => { if (e.target.closest('.x')) { const mini = $('log').classList.toggle('mini'); e.target.closest('.x').textContent = mini ? '+' : '–'; } else if (e.target.id === 'logSrcBtn') { $('logSrc').hidden = !$('logSrc').hidden; } };

  document.addEventListener('pointerdown', e => { if (!e.target.closest('.pop') && !e.target.closest('#bar')) closePops(); });
  return U;
}
