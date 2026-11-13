// 介面：工具列、區域清單、示範選單、角色進度卡、佈告欄、會議紀錄。全部繁體中文。
import { rng } from './furniture.js';
import { SPECIES, SPECIES_IDS, ACCESSORIES, canWear } from '../../play/species.js';
import { renderThumb } from '../../play/lite.js';

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
    <li>點角色：看進度卡，可以摸頭、敲頭、餵點心、叫他去休息或回座位，也能改名字、暱稱、物種與配色（原職稱不能改）。</li>
    <li>按住角色拖曳：把他拎起來放到別處，放開後他會自己走回座位。寵物也可以摸、餵、拎。</li>
    <li>點佈告欄：看 CEO 或該部門的公告。</li>
    <li>「示範」：重播一場會議、交件、上下班與日常行為（示範資料）。</li>
    <li>「整修」：拖曳家具、旋轉、換地板顏色。改動都只記在這台裝置上。</li>
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
  const demos = [['meeting', '開一場會', '召集、討論、爭執、白板、散會、交件'], ['clockout', '下班', '幾位同事從大門離開'], ['clockin', '上班', '從大門進來回座位'], ['coffee', '倒咖啡', ''], ['lookup', '查資料', ''], ['rest', '休息一下', ''], ['play', '去遊樂區', ''], ['snack', '吃點心', ''], ['chat', '站著聊天', ''], ['report', '拿文件交件', '']];
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
  U.progress = progress;      // 操控模式的「按 E 溝通」要用對方現有的進度資料當對話內容
  const DOING = { type: '打電腦', note: '做筆記', think: '想事情', phone: '講電話', drink: '喝咖啡', tablet: '看平板', doc: '讀文件', read: '翻書查資料', magnify: '拿放大鏡細看', stretch: '伸懶腰', doze: '打瞌睡', sleep: '睡著了', listen: '聽人說話', talk: '發言中', eat: '吃點心', paddle: '打桌球', carry: '拿著文件', present: '交件中', slam: '拍桌', sulk: '有點委屈', clap: '鼓掌', cheer: '歡呼' };
  const STATE = c => { const d = DOING[c.action]; if (c.piloted) return '被你操控中'; return c.away ? '已下班' : c.state === 'held' ? '被拎起來了' : c.state === 'walk' ? '走路中' + (d && c.action !== 'type' ? `（${d}）` : '') : (c.atDesk ? `坐在位子上${d || '工作'}${c.task ? '：' + c.task : ''}` : (d || (c.state === 'sit' ? '坐著' : '離開座位'))); };
  // 頭像：用同一個繪圖器把角色畫成小圖（同一種長相只畫一次）
  const thumbs = new Map();
  function thumb(sp) { const k = [sp.species, sp.pal, sp.hue, (sp.acc || []).join('+'), sp.accColor].join('|'); if (!thumbs.has(k)) { let u = ''; try { u = renderThumb(W.renderer, { species: sp.species, pal: sp.pal, hue: sp.hue, acc: sp.acc, accColor: sp.accColor }, { size: 128, frames: 12 }); } catch (e) { u = ''; } thumbs.set(k, u); } return thumbs.get(k); }
  const spName = sp => (SPECIES[sp.species] ? `${SPECIES[sp.species].name}（${SPECIES[sp.species].sub}）` : '');
  let cardChar = null, draft = null, cardP = null, cardF = 0, cardOpen = -1;
  const ava = sp => { const u = thumb(sp); return u ? `<img class="ava2" src="${u}" alt="">` : `<div class="ava" style="background:${sp.color || '#ffb057'}"></div>`; };
  // 任務清單：依點選的狀態格篩選；點一列展開細節（只列有資料的欄位，沒有的不顯示空白列）
  const SN = ['', '未完成', '進行中', '已完成'], TL = ['', '排定', '開始', '完成'];
  function taskDetail(x, spec, p) {
    const m = W.members.get(spec.id) || spec, rows = [['狀態', SN[x.s]], [TL[x.s] + '時間', x.t], ['負責人', `${spec.nick}（${spec.id}・${spec.zh}）`]];
    if (m.deptName) rows.push(['所屬部門', m.deptName]);
    if (x.s === 2) { rows.push(['預估完成', `${p.eta}（約 ${p.etaMin} 分鐘後）`]); if (p.opt) rows.push(['能否優化', p.opt]); }
    return `<dl class="det">${rows.filter(r => r[1]).map(r => `<dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd>`).join('')}</dl>`;
  }
  function renderList() {
    const el = $('cardList'); if (!el || !cardP || !cardChar) return; const p = cardP, spec = cardChar.spec;
    $('cardKpi').querySelectorAll('[data-k]').forEach(b => { const on = +b.dataset.k === cardF; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
    const rows = p.list.map((x, i) => ({ x, i })).filter(r => !cardF || r.x.s === cardF);
    el.innerHTML = rows.length ? rows.map(({ x, i }) => `<div class="rowx${cardOpen === i ? ' open' : ''}"><div class="row" role="button" tabindex="0" data-r="${i}" aria-expanded="${cardOpen === i}"><i class="s${x.s}"></i><span>${esc(x.title)}</span><em class="st">${SN[x.s]}</em><time>${TL[x.s]} ${x.t}</time></div>${cardOpen === i ? taskDetail(x, spec, p) : ''}</div>`).join('') : `<div class="empty">這個狀態目前沒有任務</div>`;
  }
  U.showCard = c => {
    cardChar = c; draft = null; $('board').hidden = true; const s = c.spec, p = progress(s), m = W.members.get(s.id) || s; cardP = p; cardF = 0; cardOpen = -1;
    $('card').innerHTML = `<button class="x" aria-label="關閉">×</button>
      <div class="hd">${ava(s)}<div><b>${esc(s.nick)}</b>${s.name && s.name !== s.nick ? `<span class="nm2">${esc(s.name)}</span>` : ''}${s.lead ? '<span class="tag2">主管</span>' : ''}
        <p>${esc(s.id)}・${esc(s.zh)}${m.deptName ? '・' + esc(m.deptName) : ''}</p><p>${esc(spName(s))}</p></div></div>
      <div class="now" id="cardNow">目前：${esc(STATE(c))}</div>
      <div class="acts g3"><button class="btn" data-i="pet">摸頭</button><button class="btn" data-i="bonk">敲頭</button><button class="btn" data-i="feed">餵點心</button><button class="btn" data-i="rest">去休息</button><button class="btn" data-i="home">回座位</button><button class="btn" data-i="edit">改造型</button></div>
      <div class="kpi" id="cardKpi">${[[1, 'k1', '未完成', p.nTodo, p.nextTodo ? '排 ' + p.nextTodo : '—'], [2, 'k2', '進行中', p.nDoing, '起 ' + p.lastDoing], [3, 'k3', '已完成', p.nDone, '末 ' + p.lastDone]].map(([k, c, n, v, em]) => `<button class="${c}" data-k="${k}" aria-pressed="false" title="點一下只看「${n}」的任務，再點一次回到全部"><span>${n}</span><b>${v}</b><em>${em}</em></button>`).join('')}</div>
      <dl class="meta"><dt>預估完成</dt><dd>${p.eta}（約 ${p.etaMin} 分鐘後）</dd><dt>能否優化</dt><dd>${esc(p.opt)}</dd></dl>
      <div class="list" id="cardList"></div>
      <div class="acts"><button class="btn" data-a="ceo">回 CEO 視角</button><button class="btn" data-a="god">俯瞰</button></div>`;
    $('card').hidden = false; renderList();
  };
  // 寵物的小卡
  U.showPet = c => {
    cardChar = c; draft = null; $('board').hidden = true; const s = c.spec;
    $('card').innerHTML = `<button class="x" aria-label="關閉">×</button>
      <div class="hd">${ava(s)}<div><b>${esc(s.nick)}</b><span class="tag2">寵物</span><p>${esc(s.zh || '')}</p><p>${esc(spName(s))}</p></div></div>
      <div class="acts g3"><button class="btn" data-i="pet">摸摸</button><button class="btn" data-i="feed">餵點心</button><button class="btn" data-i="bonk">彈一下</button></div>`;
    $('card').hidden = false;
  };
  // 改造型：名字、暱稱、物種、配色、配件（原職稱鎖定）
  function showEdit() {
    const c = cardChar, s = c.spec; draft = draft || { name: s.name || s.nick, nick: s.nick, species: s.species, pal: s.pal | 0, acc: [...(s.acc || [])] };
    const cfg = SPECIES[draft.species] || SPECIES.mochi, hex = n => '#' + (n >>> 0).toString(16).padStart(6, '0');
    $('card').innerHTML = `<button class="x" aria-label="關閉">×</button>
      <div class="hd">${ava({ ...s, ...draft })}<div><b>改造型</b><p>原職稱：${esc(s.id)}・${esc(s.zh)}（不可改）</p></div></div>
      <div class="form"><label>名字<input id="edName" maxlength="12" value="${esc(draft.name)}"></label><label>暱稱<input id="edNick" maxlength="8" value="${esc(draft.nick)}"></label></div>
      <div class="lab">物種</div><div class="chips" id="edSp">${SPECIES_IDS.map(id => `<button class="chip${id === draft.species ? ' on' : ''}" data-sp="${id}">${esc(SPECIES[id].name)}</button>`).join('')}</div>
      <div class="lab">配色</div><div class="chips">${cfg.pals.map((q, i) => `<button class="sw${i === draft.pal % cfg.pals.length ? ' on' : ''}" data-pal="${i}" style="background:${hex(q.body)}" aria-label="${esc(q.n)}" title="${esc(q.n)}"></button>`).join('')}</div>
      <div class="lab">配件</div><div class="chips">${ACCESSORIES.filter(([k]) => canWear(cfg, k)).map(([k, n]) => `<button class="chip${draft.acc.includes(k) ? ' on' : ''}" data-acc="${k}">${esc(n)}</button>`).join('')}</div>
      <div class="acts"><button class="btn on" data-e="save">儲存</button><button class="btn" data-e="reset">還原預設</button><button class="btn" data-e="cancel">取消</button></div>`;
  }
  function readDraft() { if (!draft) return; const n = $('edName'), k = $('edNick'); if (n) draft.name = n.value.trim().slice(0, 12); if (k) draft.nick = k.value.trim().slice(0, 8); }
  function applyEdit(reset) {
    const id = cardChar.spec.id, R = W.roster; readDraft();
    if (reset) delete R.edits[id]; else { if (!draft.nick) draft.nick = cardChar.spec.nick0 || cardChar.spec.nick; R.edits[id] = { name: draft.name || draft.nick, nick: draft.nick, species: draft.species, pal: draft.pal, acc: draft.acc }; }
    const saved = R.save(), c = api.rebuild(id);
    if (!c) { U.toast('他正在開會，散會後再改'); return; }
    draft = null; U.showCard(c); api.setView('char', c); U.toast(reset ? '已還原預設造型' : saved ? '已儲存（只記在這台裝置）' : '這台裝置無法儲存，重新整理後會還原');
  }
  U.tickCard = () => { if (cardChar && !$('card').hidden) { const el = $('cardNow'), t = '目前：' + STATE(cardChar); if (el && el.textContent !== t) el.textContent = t; } };
  $('card').addEventListener('keydown', e => { const r = e.target.closest && e.target.closest('[data-r]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); } });
  $('card').onclick = e => {
    { const t = e.target.closest('button,[role=button]'); if (t && e.detail) queueMicrotask(() => t.blur()); }   // 滑鼠點過就放掉焦點，之後按 Space 才是「跳躍」而不是再點一次這顆按鈕（鍵盤操作不受影響）
    if (e.target.closest('.x')) { $('card').hidden = true; draft = null; api.cardClosed(); return; }
    const c = cardChar, D = api.director(); let b;
    if ((b = e.target.closest('[data-k]'))) { const k = +b.dataset.k; cardF = cardF === k ? 0 : k; cardOpen = -1; renderList(); if (e.detail) b.blur(); return; }
    if ((b = e.target.closest('[data-r]'))) { const i = +b.dataset.r; cardOpen = cardOpen === i ? -1 : i; renderList(); const nb = $('cardList').querySelector(`[data-r="${i}"]`); if (nb && !e.detail) nb.focus(); return; }
    if ((b = e.target.closest('[data-a]'))) { $('card').hidden = true; api.setView(b.dataset.a); return; }
    if ((b = e.target.closest('[data-i]'))) {
      const k = b.dataset.i, inMeet = D.meeting && D.meeting.people.includes(c);
      if (c.state === 'held' || c.away) return;
      if (k === 'pet') { c.pet(2.4); U.toast(`摸摸${c.spec.nick}，他很開心`); }
      else if (k === 'bonk') { c.bonk(); U.toast(`敲了${c.spec.nick}一下，他有點委屈`); }
      else if (k === 'feed') { c.feed(); U.toast(`給${c.spec.nick}一個甜甜圈`); }
      else if (k === 'rest') { if (inMeet) U.toast('他正在開會'); else if (c.busy) U.toast('他手上有事，等一下再叫他'); else { D.routine(c.spec.id, 'rest'); U.toast(`${c.spec.nick}去休息區了`); } }
      else if (k === 'home') { U.toast(D.sendHome(c) ? `${c.spec.nick}走回座位` : '他正在開會'); }
      else if (k === 'edit') { if (inMeet) U.toast('他正在開會，散會後再改'); else showEdit(); }
      return;
    }
    if ((b = e.target.closest('[data-sp]'))) { readDraft(); draft.species = b.dataset.sp; draft.pal = 0; draft.acc = draft.acc.filter(a => canWear(SPECIES[draft.species], a)); showEdit(); return; }
    if ((b = e.target.closest('[data-pal]'))) { readDraft(); draft.pal = +b.dataset.pal; showEdit(); return; }
    if ((b = e.target.closest('[data-acc]'))) { readDraft(); const k = b.dataset.acc; draft.acc = draft.acc.includes(k) ? draft.acc.filter(a => a !== k) : [...draft.acc, k]; showEdit(); return; }
    if ((b = e.target.closest('[data-e]'))) { const k = b.dataset.e; if (k === 'cancel') { draft = null; U.showCard(c); } else applyEdit(k === 'reset'); }
  };
  U.hideCard = () => { $('card').hidden = true; draft = null; };

  // ── 佈告欄 ──
  // 佈告欄面板：公告（便利貼）＋該部門的人數、主管、成員事項彙總（進行中／未完成／已完成，可點篩選，點一列看細節）
  let boardOwner = null, boardF = 2, boardOpen = -1, boardTasks = [];
  function boardData(owner) {
    const d = W.org.departments.find(q => q.id === owner), people = owner === 'ceo' ? [{ ...W.org.ceo, dept: 'ceo', isCeo: true }] : d.members.map(m => ({ ...m, dept: d.id }));
    const all = owner === 'ceo' ? 1 + W.org.departments.reduce((n, q) => n + q.members.length, 0) : d.members.length, lead = owner === 'ceo' ? 'CEO' : ((d.members.find(m => m.lead) || {}).nick || '—');
    const tasks = []; people.forEach(sp => { const p = progress(sp); p.list.forEach(x => tasks.push({ ...x, who: sp.nick, whoId: sp.id, zh: sp.zh, p })); });
    tasks.sort((a, b) => (a.t < b.t ? 1 : -1));
    return { name: owner === 'ceo' ? 'CEO' : d.name, color: owner === 'ceo' ? '#ffb057' : d.color, all, lead, tasks, notes: demo.boards[owner] || [] };
  }
  function renderBoard() {
    const B = boardData(boardOwner); boardTasks = B.tasks; const cnt = k => B.tasks.filter(x => x.s === k).length;
    const rows = B.tasks.map((x, i) => ({ x, i })).filter(r => !boardF || r.x.s === boardF);
    $('board').innerHTML = `<button class="x" aria-label="關閉">×</button><h3><span class="dot" style="width:12px;height:12px;border-radius:50%;background:${B.color}"></span>${esc(B.name)}佈告欄</h3>
      <p class="bmeta">${boardOwner === 'ceo' ? '全公司' : '部門'}人數 ${B.all} 人・主管：${esc(B.lead)}</p>
      <div class="scroll" id="boardScroll"><div class="bsec">便利貼公告</div>${B.notes.map(n => `<div class="note${n.isNew ? ' new' : ''}"><time>${esc(n.t)}</time><b>${esc(n.title)}</b><p>${esc(n.text)}</p></div>`).join('') || '<p class="empty">目前沒有公告</p>'}
      <div class="bsec">事項彙總（${boardOwner === 'ceo' ? 'CEO' : esc(B.name) + '成員'}）</div>
      <div class="kpi" id="boardKpi">${[[1, 'k1', '未完成'], [2, 'k2', '進行中'], [3, 'k3', '已完成']].map(([k, c, n]) => `<button class="${c}${boardF === k ? ' on' : ''}" data-bk="${k}" aria-pressed="${boardF === k}" title="只看「${n}」的事項，再點一次看全部"><span>${n}</span><b>${cnt(k)}</b></button>`).join('')}</div>
      <div class="list bl" id="boardList">${rows.length ? rows.map(({ x, i }) => `<div class="rowx${boardOpen === i ? ' open' : ''}"><div class="row" role="button" tabindex="0" data-br="${i}" aria-expanded="${boardOpen === i}"><i class="s${x.s}"></i><span>${esc(x.who)}：${esc(x.title)}</span><em class="st">${SN[x.s]}</em><time>${TL[x.s]} ${x.t}</time></div>${boardOpen === i ? `<dl class="det"><dt>狀態</dt><dd>${SN[x.s]}</dd><dt>${TL[x.s]}時間</dt><dd>${esc(x.t)}</dd><dt>負責人</dt><dd>${esc(x.who)}（${esc(x.whoId)}・${esc(x.zh)}）</dd>${x.s === 2 ? `<dt>預估完成</dt><dd>${esc(x.p.eta)}（約 ${x.p.etaMin} 分鐘後）</dd>` : ''}</dl>` : ''}</div>`).join('') : '<div class="empty">這個狀態目前沒有事項</div>'}</div></div>`;
  }
  U.showBoard = owner => {
    $('card').hidden = true; boardOwner = owner; boardF = 2; boardOpen = -1; renderBoard(); $('board').hidden = false;
  };
  $('board').onclick = e => {
    let b; { const t = e.target.closest('button,[role=button]'); if (t && e.detail) queueMicrotask(() => t.blur()); }
    if (e.target.closest('.x')) { $('board').hidden = true; return; }
    if ((b = e.target.closest('[data-bk]'))) { const k = +b.dataset.bk; boardF = boardF === k ? 0 : k; boardOpen = -1; const sc = $('boardScroll').scrollTop; renderBoard(); $('boardScroll').scrollTop = sc; if (e.detail) document.activeElement.blur(); return; }
    if ((b = e.target.closest('[data-br]'))) { const i = +b.dataset.br; boardOpen = boardOpen === i ? -1 : i; const sc = $('boardScroll').scrollTop; renderBoard(); $('boardScroll').scrollTop = sc; return; }
  };
  $('board').addEventListener('keydown', e => { const r = e.target.closest && e.target.closest('[data-br]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); } });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('board').hidden) { e.preventDefault(); $('board').hidden = true; } });
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
