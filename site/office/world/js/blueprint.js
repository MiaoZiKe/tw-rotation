// 藍圖式任務流程（2026-11-16，第二批第 6 項；參考 Prison Architect「先畫後蓋」＋ ChatDev「階段鏈」）。
// 先在編輯器畫一條「需求 → 實作 → 審查 → 測試」的流程：可增刪站、調順序、每站指定負責的同事（不指定＝依專長與優先度表自動挑），存成範本重複使用。
// 套用之後：
//   · 示範／模擬模式：流程真的在辦公室裡走——一站一站派給負責的人（走模擬器、跟手動派工同一套演出），做完才換下一站；
//     畫面左上角有一條流程條標出「現在在第幾站」，負責人的名牌上也掛著「第 N 站・站名」。
//   · 真實專案：不自己呼叫 Claude。只把藍圖轉成一則給 CEO 的指令，放進主對話框、走既有的送出流程（含 office.cmd 閘門），
//     流程條照樣標出目前站（依負責人的真實完成數自動往下一站，也可以手動按「這站完成」）。
// 存檔：範本 aiOffice.game.blueprint.<範圍>、進行中的流程 aiOffice.game.blueprintrun.<範圍>（重新整理後接著走）。
// 閘門：套用一次算一次 office.blueprint（features.js 宣告、plan_presets.js 寫各方案數字）。
import { $, esc, jget, lsSet, scopeOf, GAME, whenWorld, members } from './workkit.js';

const SC = scopeOf(), KEY = GAME + 'blueprint.' + SC, RKEY = GAME + 'blueprintrun.' + SC;
const MAXN = 8, uid = () => 'bp' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
const DEFAULT = () => ({ id: uid(), name: '標準流程', nodes: ['需求', '實作', '審查', '測試'].map(n => ({ name: n, who: '' })) });

export function createBlueprint(W) {
  const B = { key: KEY, stepSec: +new URLSearchParams(location.search).get('bpstep') || 9, run: null };   // 每站模擬幾秒（?bpstep= 給驗收用）
  W.blueprint = B;
  let store = jget(KEY, null); if (!store || !Array.isArray(store.tpls) || !store.tpls.length) store = { v: 1, tpls: [DEFAULT()], cur: null };
  if (!store.tpls.some(t => t.id === store.cur)) store.cur = store.tpls[0].id;
  const save = () => lsSet(KEY, JSON.stringify(store));
  let draft = JSON.parse(JSON.stringify(store.tpls.find(t => t.id === store.cur)));
  let desc = '';
  const real = () => !!(W.live && W.live.mode === 'live');
  B.real = real; B.templates = () => store.tpls.map(t => ({ ...t, nodes: t.nodes.map(n => ({ ...n })) })); B.draft = () => draft;

  // ───────── 編輯器 ─────────
  const el = document.createElement('aside'); el.className = 'panel'; el.id = 'bpPanel'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', '任務藍圖'); el.hidden = true; ($('app') || document.body).append(el);
  const HELP = '任務藍圖：先把一件事要經過哪幾站畫出來（例如需求、實作、審查、測試），每一站指定誰負責；不指定就依專長與優先度表自動挑人。存成範本後可以重複套用。\n套用後，辦公室左上角會標出流程走到第幾站，負責人的名牌上也會掛著站名。\n示範模式：流程會真的一站一站派給負責的人。真實專案：只會把這條流程寫成一則給 CEO 的指令放進對話框，由 CEO 的 Claude 去安排，這裡不會自己呼叫任何東西。';
  const ownerOpts = sel => `<option value="">（自動挑選）</option>` + members(W).map(c => `<option value="${esc(c.spec.id)}"${c.spec.id === sel ? ' selected' : ''}>${esc(c.spec.nick)}・${esc(c.spec.zh)}</option>`).join('');
  function render() {
    if (el.hidden) return; const keepScroll = el.querySelector('.scroll') ? el.querySelector('.scroll').scrollTop : 0;
    const act = document.activeElement, focusKey = act && el.contains(act) && act.dataset ? (act.dataset.f || '') : '', selS = act && act.selectionStart != null ? act.selectionStart : null;
    const tplOpts = store.tpls.map(t => `<option value="${esc(t.id)}"${t.id === store.cur ? ' selected' : ''}>${esc(t.name)}</option>`).join('');
    const flow = draft.nodes.map((n, i) => `<span class="bp-chip">${i + 1} ${esc(n.name || '（沒有名字）')}</span>`).join('<i class="bp-ar" aria-hidden="true">→</i>');
    const rows = draft.nodes.map((n, i) => `<li data-i="${i}"><b class="bp-no">${i + 1}</b><input class="bp-n" data-f="n${i}" value="${esc(n.name)}" maxlength="10" aria-label="第 ${i + 1} 站的名字" placeholder="站名"><select class="bp-w" data-f="w${i}" aria-label="第 ${i + 1} 站的負責人">${ownerOpts(n.who)}</select><span class="bp-m"><button data-bp="up" aria-label="第 ${i + 1} 站往前"${i === 0 ? ' disabled' : ''}>▲</button><button data-bp="dn" aria-label="第 ${i + 1} 站往後"${i === draft.nodes.length - 1 ? ' disabled' : ''}>▼</button><button data-bp="del" aria-label="刪除第 ${i + 1} 站"${draft.nodes.length <= 1 ? ' disabled' : ''}>✕</button></span></li>`).join('');
    const rl = real();
    el.innerHTML = `<button class="x" data-bp="x" aria-label="關閉">×</button><h3>任務藍圖<button class="gm-q" data-bp="q" aria-expanded="false" aria-label="藍圖說明">?</button></h3>
      <div class="bp-help" hidden>${esc(HELP).replace(/\n/g, '<br>')}</div>
      <div class="bp-top"><select id="bpTpl" aria-label="選擇範本">${tplOpts}</select><button class="btn" data-bp="new">新範本</button><button class="btn" data-bp="delt"${store.tpls.length <= 1 ? ' disabled' : ''}>刪除範本</button></div>
      <div class="bp-flow" aria-label="流程預覽">${flow}</div>
      <div class="scroll bp-body"><label class="bp-l">範本名稱<input id="bpName" data-f="name" value="${esc(draft.name)}" maxlength="14"></label>
      <ol class="bp-nodes">${rows}</ol>
      <button class="btn bp-add" id="bpAdd" data-bp="add"${draft.nodes.length >= MAXN ? ' disabled' : ''}>＋ 加一站</button>
      <label class="bp-l">這次要做的事（會一起帶進流程）<textarea id="bpDesc" data-f="desc" rows="2" maxlength="300" placeholder="例如：把盤後貼文的版型改好">${esc(desc)}</textarea></label></div>
      <div class="bp-msg" id="bpMsg" role="status"></div>
      <div class="acts"><button class="btn" id="bpSave" data-bp="save">儲存範本</button><button class="btn on" id="bpRun" data-bp="run">${rl ? '轉成指令送給 CEO' : '套用並開始'}</button></div>`;
    const sc = el.querySelector('.scroll'); if (sc) sc.scrollTop = keepScroll;
    if (focusKey) { const f = el.querySelector(`[data-f="${focusKey}"]`); if (f) { f.focus(); if (selS != null && f.setSelectionRange) try { f.setSelectionRange(selS, selS); } catch (e) { /* 略 */ } } }
  }
  const msg = t => { const m = $('bpMsg'); if (m) m.textContent = t || ''; };
  B.open = () => { W.ui.closePops(); const o = $('prPanel'); if (o) o.hidden = true; el.hidden = false; render(); };
  B.close = () => { el.hidden = true; };
  B.addNode = (name = '新的一站', who = '') => { if (draft.nodes.length >= MAXN) return false; draft.nodes.push({ name, who }); render(); return true; };
  B.removeNode = i => { if (draft.nodes.length <= 1) return false; draft.nodes.splice(i, 1); render(); return true; };
  B.save = () => { draft.nodes = draft.nodes.map(n => ({ name: (n.name || '').trim() || '一站', who: n.who || '' })); draft.name = (draft.name || '').trim() || '我的流程'; const i = store.tpls.findIndex(t => t.id === draft.id); const c = JSON.parse(JSON.stringify(draft)); if (i >= 0) store.tpls[i] = c; else store.tpls.push(c); store.cur = c.id; save(); return c; };
  const load = id => { const t = store.tpls.find(x => x.id === id); if (t) { store.cur = id; draft = JSON.parse(JSON.stringify(t)); save(); } };
  el.addEventListener('input', e => {
    const t = e.target; if (t.classList.contains('bp-n')) draft.nodes[+t.closest('li').dataset.i].name = t.value; else if (t.id === 'bpName') draft.name = t.value; else if (t.id === 'bpDesc') desc = t.value;
    if (t.classList.contains('bp-n') || t.id === 'bpName') { const fl = el.querySelector('.bp-flow'); if (fl) fl.innerHTML = draft.nodes.map((n, i) => `<span class="bp-chip">${i + 1} ${esc(n.name || '（沒有名字）')}</span>`).join('<i class="bp-ar" aria-hidden="true">→</i>'); }
  });
  el.addEventListener('change', e => {
    const t = e.target; if (t.classList.contains('bp-w')) draft.nodes[+t.closest('li').dataset.i].who = t.value;
    else if (t.id === 'bpTpl') { load(t.value); render(); }
  });
  el.addEventListener('click', async e => {
    const b = e.target.closest('[data-bp]'); if (!b) return; const k = b.dataset.bp, li = b.closest('li'), i = li ? +li.dataset.i : -1, n = draft.nodes;
    if (k === 'x') B.close();
    else if (k === 'q') { const h = el.querySelector('.bp-help'); h.hidden = !h.hidden; b.setAttribute('aria-expanded', !h.hidden); }
    else if (k === 'add') B.addNode();
    else if (k === 'del') B.removeNode(i);
    else if (k === 'up' && i > 0) { [n[i - 1], n[i]] = [n[i], n[i - 1]]; render(); }
    else if (k === 'dn' && i < n.length - 1) { [n[i + 1], n[i]] = [n[i], n[i + 1]]; render(); }
    else if (k === 'new') { draft = { id: uid(), name: '新範本', nodes: [{ name: '需求', who: '' }, { name: '實作', who: '' }] }; store.tpls.push(JSON.parse(JSON.stringify(draft))); store.cur = draft.id; save(); render(); }
    else if (k === 'delt') { store.tpls = store.tpls.filter(t => t.id !== store.cur); store.cur = store.tpls[0].id; load(store.cur); render(); }
    else if (k === 'save') { const c = B.save(); render(); msg(`已存成範本「${c.name}」`); }
    else if (k === 'run') { b.disabled = true; try { const r = await B.apply(); if (r && r.error) msg(r.error); else if (r) { B.close(); } } finally { b.disabled = false; } }
  });

  // ───────── 流程條與名牌 ─────────
  const bar = document.createElement('div'); bar.id = 'bpFlow'; bar.hidden = true; bar.setAttribute('role', 'status'); bar.setAttribute('aria-live', 'polite'); ($('app') || document.body).append(bar);
  const tagOf = id => { const c = W.chars.get(id); return c && c._lab && c._lab.tag ? c._lab.tag : null; };
  function marks() {
    for (const o of document.querySelectorAll('.tag .gbp')) o.remove();
    const r = B.run; if (!r) return; const nd = r.nodes[r.step]; if (!nd || !nd.who) return; const t = tagOf(nd.who); if (!t) return;
    const s = document.createElement('i'); s.className = 'gbp'; s.textContent = `第 ${r.step + 1} 站・${nd.name}`; t.append(s);
  }
  function drawBar() {
    const r = B.run; if (!r) { bar.hidden = true; bar.innerHTML = ''; return; }
    const fin = r.step >= r.nodes.length;
    bar.hidden = false; bar.dataset.step = String(r.step);
    bar.innerHTML = `<b class="bp-t">${esc(r.name)}</b><span class="bp-st">${r.nodes.map((n, i) => `<span class="bp-s ${i < r.step ? 'done' : i === r.step ? 'cur' : ''}" data-i="${i}" aria-current="${i === r.step ? 'step' : 'false'}">${i < r.step ? '✓ ' : ''}${esc(n.name)}${n.who ? '・' + esc(nickFor(n.who)) : ''}</span>`).join('<i aria-hidden="true">→</i>')}</span>
      <span class="bp-ct">${fin ? '全部完成' : `走到第 ${r.step + 1} 站／共 ${r.nodes.length} 站`}</span>${fin ? '' : '<button class="btn" data-bf="next">這站完成</button>'}<button class="btn" data-bf="stop" aria-label="結束流程">${fin ? '收起' : '結束'}</button>`;
  }
  const nickFor = id => { const c = W.chars.get(id); return c ? c.spec.nick : id; };
  bar.addEventListener('click', e => { const b = e.target.closest('[data-bf]'); if (!b) return; if (b.dataset.bf === 'next') B.next(); else B.stop(); });
  const persistRun = () => lsSet(RKEY, B.run ? JSON.stringify(B.run) : null);

  // ───────── 跑流程 ─────────
  let tok = 0;
  function resolveOwners(nodes) {
    const G = W.growth, used = [], ms = members(W);
    return nodes.map((n, i) => {
      let who = n.who && W.chars.has(n.who) ? n.who : '';
      if (!who) { const sk = G && G.skillOfText ? G.skillOfText(n.name) : null; if (G && G.rank) { const l = G.rank(sk || '研究', { exclude: used }); if (l[0]) who = l[0].id; } }
      if (!who && ms.length) who = ms[i % ms.length].spec.id;
      if (who) used.push(who); return { name: n.name, who: who || '' };
    });
  }
  function startStep() {
    const r = B.run; if (!r) return; marks(); drawBar(); persistRun(); const my = ++tok;
    if (r.step >= r.nodes.length) { W.emit && W.emit('blueprint_done', 'ceo', { name: r.name }); try { W.ui.toast(`流程「${r.name}」全部走完了`); } catch (e) { /* 略 */ } setTimeout(() => { if (B.run === r && r.step >= r.nodes.length) B.stop(); }, 8000); return; }
    const nd = r.nodes[r.step], a = nd.who && W.state && W.state.agents ? W.state.agents.get(nd.who) : null;
    if (r.real) {          // 真實專案：不派工，只看負責人的真實完成數增加了沒
      r.base = a ? a.done.length : 0; return;
    }
    const sim = W.sim; if (sim && nd.who) { try { sim.start(nd.who, `${r.name}・${nd.name}${r.text ? '：' + r.text.slice(0, 20) : ''}`); } catch (e) { /* 模擬器不在就只走流程條 */ } }
    (async () => { await W.sleep(B.stepSec); if (tok !== my || B.run !== r) return; if (sim && nd.who) { try { sim.stop(nd.who, true); } catch (e) { /* 略 */ } } B.next(true); })();
  }
  B.next = auto => { const r = B.run; if (!r || r.step >= r.nodes.length) return false; const nd = r.nodes[r.step]; if (!auto && !r.real && W.sim && nd.who) { try { W.sim.stop(nd.who, true); } catch (e) { /* 略 */ } } r.step++; startStep(); return true; };
  B.stop = () => { tok++; const r = B.run; B.run = null; if (r && !r.real && W.sim && r.step < r.nodes.length) { const nd = r.nodes[r.step]; if (nd && nd.who) { try { W.sim.stop(nd.who, false); } catch (e) { /* 略 */ } } } marks(); drawBar(); persistRun(); };
  setInterval(() => { const r = B.run; if (!r || !r.real || r.step >= r.nodes.length) return; const nd = r.nodes[r.step], a = nd.who && W.state.agents.get(nd.who); if (a && a.done.length > (r.base || 0)) B.next(true); }, 1500);
  setInterval(() => { if (B.run) marks(); }, 2000);        // 名牌被重建（換裝、重新聘用）時補掛

  // 組成給 CEO 的指令（真實專案）
  B.compose = (name, nodes, text) => {
    const lines = nodes.map((n, i) => `${i + 1}. ${n.name}：${n.who ? nickFor(n.who) : '（請你挑適合的人）'}`).join('\n');
    return `請依照下面的「${name}」流程處理，共 ${nodes.length} 站，依序進行，每一站做完交給下一站：\n${lines}${text ? '\n\n這次要做的事：' + text : ''}`;
  };
  B.apply = async (opt = {}) => {
    const c = opt.keep ? draft : B.save(); const text = (opt.text != null ? opt.text : desc).trim(); if (B.run) B.stop();
    const gt = W.gate ? await W.gate.begin('office.blueprint') : null;
    if (gt && !gt.pass) { try { W.gate.say(gt.note); } catch (e) { /* 略 */ } return { error: gt.note, blocked: true }; }
    const rl = real(), nodes = resolveOwners(c.nodes);
    B.run = { tplId: c.id, name: c.name, nodes, step: 0, text, real: rl, at: Date.now() };
    let okk = true;
    try {
      if (rl) {
        const body = B.compose(c.name, nodes, text), tx = $('chatText'), form = $('chatForm');
        if (W.chat && W.chat.openTo) W.chat.openTo('ceo');
        if (tx && form) { tx.value = body; tx.dispatchEvent(new Event('input', { bubbles: true })); try { form.requestSubmit(); } catch (e) { /* 舊瀏覽器：留在對話框讓使用者按送出 */ } B.lastText = body; setTimeout(() => { if (tx.value === body) { try { W.ui.toast('流程已寫進對話框，連線後按「送出」就會交給 CEO'); } catch (e) { /* 略 */ } } }, 600); }
        else okk = false;
      }
    } finally { if (gt) { if (okk) gt.done(); else gt.cancel(); } }
    startStep(); return { ok: true, run: B.run };
  };
  // 重新整理後接著走（超過 6 小時的舊流程不復原）
  const old = jget(RKEY, null);
  if (old && Array.isArray(old.nodes) && old.step <= old.nodes.length && Date.now() - (old.at || 0) < 6 * 3600e3) { B.run = old; setTimeout(startStep, 300); }
  return B;
}
whenWorld(W => { if (!W.blueprint) createBlueprint(W); });
