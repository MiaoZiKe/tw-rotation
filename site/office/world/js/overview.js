// 總覽面板＋通知中心（2026-11-16，遊戲基礎設定第 8 項：誰卡住、誰閒置一眼看）。
//
// 為什麼獨立成一支、用自己的輪詢，不去改 jobs.js／mind.js／fire.js：
//   那幾支的狀態散在各處（派工在 state.agents、著火在 W.fire.states、心情在 W.mind），而且另有同事正在改心情、等級、體力。
//   這裡每秒「看一眼」現成的欄位、把變化翻成通知，不依賴任何一支的內部事件格式，所以對方怎麼改都不會壞。
//   體力、等級是對方還在做的欄位：只有「W 上存在才顯示」（lvOf／staOf 找不到就回 null，畫面不出現那一格）。
//
// 狀態判斷（優先序由上到下，同一個人只算一種）：
//   待業（被開除）→ 著火（W.fire.states 是 burning）→ 卡住（派了工作，超過 state.cfg.stuckMs[0]＝3 分鐘沒有新動靜；
//   CEO 在等你核准／回答也算卡住）→ 疲累（心情的精力低於 0.35、體力低、或正在睡）→ 工作中（手上有派工）→ 閒置。
// 通知（只收這四種，免得吵）：完成、卡住、著火、升等。第一次輪詢只記基準，不把「一開頁就存在的狀態」當新事件。
// 文案禁用字：價格、NT$、付費、升級、訂閱、方案、Plus、Pro、免費、右鍵。
import { hhmm } from './state.js';

const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };

const ST = {   // 狀態 → 顯示字、排序（越小越上面）
  fire: ['著火', 0], stuck: ['卡住', 1], tired: ['疲累', 2], work: ['工作中', 3], idle: ['閒置', 4], jobless: ['待業', 5],
};
const KIND = { done: '完成', stuck: '卡住', fire: '著火', level: '升等' };
const MAXN = 60;

function boot(W) {
  const S = W.state, O = { notes: [], seq: 0, tab: 'ppl', filter: '', base: null, last: '' };
  W.overview = O;
  const btn = $('ovBtn'); if (!btn) return;

  // ───────── 功能閘門：總覽與通知（office.overview 只有開關，沒有次數）。關掉就把鈕藏起來 ─────────
  const gateOk = () => { try { return !W.gate || W.gate.peek('office.overview').pass; } catch (e) { return true; } };
  // 還沒有人碰鈕之前不打會員伺服器（閘門驗收：沒打開對話框之前不連線）；第一次碰到鈕才載入方案，沒開放就把鈕藏起來
  const gateLoad = () => { if (W.gate && W.gate.load) W.gate.load().then(() => { btn.hidden = !gateOk(); if (btn.hidden) O.close(); }).catch(() => { /* 連不到：維持顯示 */ }); };
  btn.addEventListener('pointerdown', gateLoad, { once: true, capture: true }); btn.addEventListener('keydown', gateLoad, { once: true, capture: true });

  // ───────── 讀取：每個人現在的狀態 ─────────
  const stuckMs = () => ((S.cfg && S.cfg.stuckMs && S.cfg.stuckMs[0]) || 180000);
  const lvOf = (c, id) => { try { const v = W.levelOf ? W.levelOf(id) : (W.mind && W.mind.get && (W.mind.get(id) || {}).level); const n = v != null ? v : c.level; return Number.isFinite(+n) && n != null ? +n : null; } catch (e) { return null; } };
  const staOf = (c, id) => { try { const m = W.mind && W.mind.get ? W.mind.get(id) : null; const v = m && m.stamina != null ? m.stamina : c.stamina; return v != null && Number.isFinite(+v) ? Math.max(0, Math.min(1, +v)) : null; } catch (e) { return null; } };
  const deptOf = c => { const d = W.org && W.org.departments ? W.org.departments.find(x => x.id === c.spec.dept) : null; return d || null; };
  function people() {
    const out = [];
    for (const c of W.chars.values()) {
      if (!c || !c.spec || c.spec.pet || c.absent || (c.object3D && c.object3D.visible === false)) continue;
      out.push(c);
    }
    return out;
  }
  function infoOf(c) {
    const id = c.spec.id, now = S.now(), a = S.agents.get(id), jt = W.jobs && W.jobs.statusOf ? W.jobs.statusOf(c) : '';
    const fired = !!(c.jobless || (W.hr && W.hr.isFired && W.hr.isFired(id)));
    const fo = W.fire && W.fire.states ? W.fire.states.get(id) : null;
    let mood = null; try { mood = W.mind && W.mind.get ? W.mind.get(id) : null; } catch (e) { mood = null; }
    const sta = staOf(c, id), energy = mood && mood.mood ? mood.mood.energy : null;
    const working = !!a && a.phase !== 'idle';
    const idleMs = a && working ? now - (a.lastToolAt || a.since || now) : 0;
    const ceoWait = c.spec.isCeo && (S.flags.permission || S.flags.question);
    const stuck = !!ceoWait || (working && (a.phase === 'delivering' ? !!a.failedNow : idleMs >= stuckMs()));
    const tired = !!c.sleeping || (energy != null && energy < 0.35) || (sta != null && sta < 0.25);
    let st = fired ? 'jobless' : fo && fo.state === 'burning' ? 'fire' : stuck ? 'stuck' : tired ? 'tired' : working ? 'work' : 'idle';
    let det = '';
    if (st === 'jobless') det = (W.statusOf && W.statusOf(c)) || '待業中';
    else if (st === 'fire') det = '身上著火了，快帶他去水池';
    else if (st === 'stuck') det = ceoWait ? (S.flags.permission ? '等你核准' : '等你回答') : a && a.phase === 'delivering' ? '交件時遇到問題' : `已 ${Math.max(1, Math.round(idleMs / 60000))} 分鐘沒有新動靜`;
    else if (st === 'tired') det = c.sleeping ? '睡覺中' : sta != null && sta < 0.25 ? '體力很低，需要休息' : '精神不太好，想休息';
    else if (st === 'work') det = a.task ? short(a.task, 22) : (jt || '工作中');
    else det = (W.statusOf && W.statusOf(c)) || '手上沒有工作';
    const d = deptOf(c);
    return { id, c, st, det, name: c.spec.nick || c.spec.name || id, role: c.spec.isCeo ? 'CEO' : (c.spec.zh || (d && d.name) || ''), color: d ? d.color : '#f58a34', lv: lvOf(c, id), sta,
      done: a ? a.done.length : 0, doneTitle: a && a.done[0] ? a.done[0].title : '', failed: a ? a.failed : 0 };
  }
  const rows = () => people().map(infoOf).sort((x, y) => ST[x.st][1] - ST[y.st][1] || String(x.name).localeCompare(String(y.name), 'zh-Hant'));
  O.rows = rows;
  O.counts = list => { const n = { fire: 0, stuck: 0, tired: 0, work: 0, idle: 0, jobless: 0 }; for (const r of (list || rows())) n[r.st]++; return n; };

  // ───────── 通知 ─────────
  const unread = () => O.notes.filter(n => !n.read).length;
  O.unread = unread;
  function add(kind, r, text) {
    const n = { id: ++O.seq, kind, who: r.id, name: r.name, text, t: Date.now(), read: false };
    O.notes.unshift(n); if (O.notes.length > MAXN) O.notes.length = MAXN;
    paintDot(); if (!$('ovPanel').hidden) paint(true);
    return n;
  }
  O.markAll = () => { O.notes.forEach(n => { n.read = true; }); paintDot(); paint(true); };
  function paintDot() {
    const n = unread(), d = $('ovDot'); d.hidden = n === 0; d.textContent = n > 99 ? '99+' : String(n);
    btn.setAttribute('aria-label', n ? `總覽與通知，${n} 則未讀` : '總覽與通知');
    const t = $('ovTabN'); if (t) { t.hidden = n === 0; t.textContent = n > 99 ? '99+' : String(n); }
  }
  // 升等：等級欄位出現且變大才算；另外也聽事件匯流排的 promoted／levelup（兩種匯流排的回呼格式不同：(id, data) 或 (事件物件)，這裡兩種都收）
  const evId = (a, b) => (a && typeof a === 'object' ? (a.id || a.who) : a) || (b && b.id) || '';
  function onLevelEvent(a, b) {
    const id = evId(a, b), c = W.chars.get(id); if (!c || c.absent) return;
    const r = infoOf(c); add('level', r, `${r.name} 升等了`);
  }
  if (typeof W.on === 'function') { ['promoted', 'levelup'].forEach(k => { try { W.on(k, onLevelEvent); } catch (e) { /* 匯流排不收就算了 */ } }); }

  // 每秒看一眼：跟上一次比，變差或有成果就開一則通知
  O.poll = () => {
    const list = rows(), now = new Map(list.map(r => [r.id, r]));
    if (!O.base) { O.base = now; if (!$('ovPanel').hidden) paint(); return; }   // 第一次只記基準
    for (const r of list) {
      const p = O.base.get(r.id); if (!p) continue;
      if (r.done > p.done) add('done', r, `${r.name} 完成了${r.doneTitle ? '「' + short(r.doneTitle, 20) + '」' : '一件工作'}`);
      if (r.failed > p.failed) add('stuck', r, `${r.name} 的工作失敗了，需要你看一下`);
      if (r.st === 'stuck' && p.st !== 'stuck' && !(r.failed > p.failed)) add('stuck', r, `${r.name} ${r.det}`);
      if (r.st === 'fire' && p.st !== 'fire') add('fire', r, `${r.name} 著火了`);
      if (r.lv != null && p.lv != null && r.lv > p.lv) add('level', r, `${r.name} 升到 Lv ${r.lv}`);
    }
    O.base = now;
    if (!$('ovPanel').hidden) { paint(); place(); }
  };

  // ───────── 面板 ─────────
  const panel = $('ovPanel');
  panel.innerHTML = `<button class="x" id="ovX" aria-label="關閉總覽">×</button>
    <h3>總覽<small id="ovSub"></small></h3>
    <div class="ov-tabs" role="tablist" aria-label="總覽分頁"><button role="tab" id="ovTabP" data-tab="ppl" aria-selected="true">員工</button><button role="tab" id="ovTabNt" data-tab="ntf" aria-selected="false">通知<b class="ov-n" id="ovTabN" hidden>0</b></button></div>
    <div class="ov-chips" id="ovChips"></div>
    <p class="ov-how" id="ovHow"></p>
    <div class="scroll ov-list" id="ovList" role="list"></div>
    <div class="ov-foot" id="ovFoot" hidden><button class="btn ov-read" id="ovAllRead" type="button">全部已讀</button></div>`;

  function paint(force) {
    const list = rows(), cnt = O.counts(list), un = unread();
    const sig = JSON.stringify([O.tab, O.filter, list.map(r => [r.id, r.st, r.det, r.lv, r.sta == null ? null : Math.round(r.sta * 100)]), O.notes.map(n => [n.id, n.read])]);
    if (!force && sig === O.last) return; O.last = sig;
    $('ovTabP').setAttribute('aria-selected', O.tab === 'ppl'); $('ovTabNt').setAttribute('aria-selected', O.tab === 'ntf');
    $('ovSub').textContent = O.tab === 'ppl' ? `共 ${list.length} 人` : `${O.notes.length} 則・${un} 則未讀`;
    const sc = $('ovList'), keep = sc.scrollTop;
    $('ovChips').hidden = $('ovHow').hidden = O.tab !== 'ppl'; $('ovFoot').hidden = O.tab !== 'ntf';
    $('ovAllRead').disabled = un === 0;
    if (O.tab === 'ppl') {
      $('ovChips').innerHTML = [['', '全部', list.length], ...Object.keys(ST).map(k => [k, ST[k][0], cnt[k]])].map(([k, n, v]) => `<button class="ov-chip${O.filter === k ? ' on' : ''}${k ? ' c-' + k : ''}" data-f="${k}" aria-pressed="${O.filter === k}">${n}<b>${v}</b></button>`).join('');
      $('ovHow').textContent = `卡住＝派了工作，超過 ${Math.round(stuckMs() / 60000)} 分鐘沒有新動靜。紅色的先處理，點一列鏡頭就飛過去。`;
      const show = list.filter(r => !O.filter || r.st === O.filter);
      sc.innerHTML = show.length ? show.map(r => `<button class="ov-row" role="listitem" data-id="${esc(r.id)}" data-st="${r.st}" type="button">
          <i class="dot" style="background:${esc(r.color)}"></i>
          <span class="who"><b>${esc(r.name)}</b>${r.role ? `<small>${esc(r.role)}</small>` : ''}${r.lv != null ? `<small class="lv">Lv ${r.lv}</small>` : ''}</span>
          <em class="st st-${r.st}">${ST[r.st][0]}</em>
          <span class="det">${esc(r.det)}${r.sta != null ? `<span class="sta" title="體力 ${Math.round(r.sta * 100)}%"><i style="width:${Math.round(r.sta * 100)}%"></i></span>` : ''}</span></button>`).join('')
        : `<div class="ov-empty">${O.filter ? '目前沒有這個狀態的人' : '辦公室還沒有員工'}</div>`;
    } else {
      sc.innerHTML = O.notes.length ? O.notes.map(n => `<button class="ov-nt${n.read ? '' : ' unread'}" role="listitem" data-nid="${n.id}" data-k="${n.kind}" type="button">
          <em class="k k-${n.kind}">${KIND[n.kind]}</em><span>${esc(n.text)}</span><time>${hhmm(n.t)}</time></button>`).join('')
        : '<div class="ov-empty">還沒有通知。員工完成工作、卡住、著火或升等時，會出現在這裡。</div>';
    }
    sc.scrollTop = keep; place();
  }
  O.paint = paint;

  // 面板位置：桌機在右上（頂列下面；會議紀錄開著就讓到它左邊）；手機是底部抽屜（world.css 的 .panel 規則）
  function place() {
    const bar = $('bar').getBoundingClientRect(); panel.style.top = Math.round(bar.bottom + 8) + 'px';
    const log = $('log'); panel.classList.toggle('beside', !log.hidden && innerWidth > 640);
    // 桌機：選了人會在右下出現「操控提示」卡（pilot.js 的 .pt-tips），面板高度讓出來，不要被它蓋住最下面的按鈕
    const tips = document.querySelector('.pt-tips'); panel.style.maxHeight = '';
    if (tips && !tips.hidden && innerWidth > 640) { const room = tips.getBoundingClientRect().top - 8 - panel.getBoundingClientRect().top; if (room > 160) panel.style.maxHeight = Math.floor(room) + 'px'; }
  }
  O.open = tab => {
    if (!gateOk()) return;
    if (tab) O.tab = tab;
    const lg = $('ledger'); if (lg && !lg.hidden) $('rwBtn').click();
    if (W.ui) { W.ui.closePops && W.ui.closePops(); }
    if (innerWidth <= 640 && document.body.classList.contains('m-more')) $('moreBtn').click();
    panel.hidden = false; place(); paint(true); btn.classList.add('on'); btn.setAttribute('aria-expanded', 'true');
  };
  O.close = () => { if (panel.hidden) return; panel.hidden = true; btn.classList.remove('on'); btn.setAttribute('aria-expanded', 'false'); };
  O.isOpen = () => !panel.hidden;
  O.fly = id => {
    const c = W.chars.get(id); if (!c || c.absent) return false;
    if (W.pov && W.pov.on && W.pov.on()) W.pov.exit(true);
    W.setView(c.spec.isCeo ? 'ceo' : 'char', c); if (W.ui) W.ui.showCard(c);
    if (W.pilot) { if (!c.jobless) W.pilot.select(c); else W.pilot.deselect(); }
    if (innerWidth <= 640) O.close();   // 手機的面板是蓋住下半屏的抽屜，飛過去就收起來，才看得到他
    return true;
  };

  btn.onclick = () => { if (panel.hidden) O.open(); else O.close(); };
  panel.addEventListener('click', e => {
    let b;
    if (e.target.closest('#ovX')) { O.close(); btn.focus({ preventScroll: true }); return; }
    if ((b = e.target.closest('[data-tab]'))) { O.tab = b.dataset.tab; paint(true); return; }
    if ((b = e.target.closest('[data-f]'))) { O.filter = O.filter === b.dataset.f ? '' : b.dataset.f; paint(true); return; }
    if (e.target.closest('#ovAllRead')) { O.markAll(); return; }
    if ((b = e.target.closest('.ov-row'))) { O.fly(b.dataset.id); return; }
    if ((b = e.target.closest('.ov-nt'))) { const n = O.notes.find(x => x.id === +b.dataset.nid); if (n) { n.read = true; paintDot(); paint(true); O.fly(n.who); } }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden && !document.getElementById('trOv')) { O.close(); } });
  addEventListener('resize', () => { if (!panel.hidden) place(); });

  O.poll();
  setInterval(() => { try { O.poll(); } catch (e) { console.warn('總覽輪詢例外', e); } }, 1000);
  paintDot();
}

// 等辦公室建好再接上去（跟 connect_link.js 同一種做法：不改 main.js 的載入順序）
{ let n = 0; const t = setInterval(() => { const W = window.__world; if (W && W.ready && W.state && W.chars) { clearInterval(t); try { boot(W); } catch (e) { console.error('總覽面板載入失敗', e); } } else if (++n > 600) clearInterval(t); }, 150); }
