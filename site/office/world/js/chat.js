// 對 Agent 下指令（2026-11-15，規格 docs/ai_office/chat_command_spec.md 第六節）
//
// 網站只是「留言板」：站長在這裡送出指令 → 收件服務（workers/ai-office-bridge）存起來 → 站長自己的 Claude 去取走、做完、把回覆貼回來。
// 網站與收件服務完全不呼叫任何模型。
//
// 鐵則（為什麼這樣寫）：
//   · 只用「網站登入權杖」（localStorage tw.acct.tok，標頭 X-AIO-Session）。接入碼在這裡一律不碰、也不顯示——收件服務本來就拒絕用接入碼寫收件匣，
//     前端碰了只會多一條外洩路徑。
//   · 沒登入、不是站長、收件服務還沒開收件匣：一律顯示白話說明與下一步，不丟錯誤、不留空白。
//   · 沒打開對話框時不發任何請求（只有「上次還有進行中的指令」才在載入後讀一次），避免辦公室一載入就打收件服務。
//   · 3D 反應只走既有事件匯流排 W.emit／W.on（cmd_queued／cmd_claimed／cmd_running／cmd_done／cmd_failed／cmd_gone），
//     真正的演出沿用 jobs.js（派工→走去 CEO 桌領任務→回座位工作→交件）；這裡只加「待辦小圖示」與「完成小慶祝」。
import { hhmm } from './state.js';

const ACCT_TOK = 'tw.acct.tok', LS_LIVE = 'aiOffice.live.v1', LS_ACTIVE = 'aiOffice.chat.active';
const MAX_TEXT = 2000, ONLINE_MS = 5 * 60e3;
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { /* 略 */ } };
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const ST = { queued: ['排隊中', 'sq'], claimed: ['已取走', 'sc'], running: ['執行中', 'sr'], done: ['完成', 'sd'], failed: ['失敗', 'sf'], canceled: ['已撤回', 'sx'], expired: ['過期（沒有 Claude 來拿）', 'sx'], stale: ['沒有回音', 'sw'] };   // 類別名加 s 前綴：單一字母的 .x 會撞到面板的關閉鈕樣式
const ACTIVE = new Set(['queued', 'claimed', 'running']);
const ERR = { too_long: '最多 2000 字', queue_full: '排隊已滿 20 則，等 Claude 取走一些再送', rate: '送太快了，一分鐘後再試', rate_day: '今天已送 100 則，明天再送', empty: '請先輸入指令內容', bad_to: '收件對象格式不對，請重新選一位' };
// 把回覆裡的網址變成可點的連結（先跳脫再換，避免把回覆當 HTML 執行）
const linkify = s => esc(s).replace(/(https?:\/\/[^\s<>"')]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
const when = ms => { const p = {}; for (const x of new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Taipei', month: '2-digit', day: '2-digit' }).formatToParts(new Date(ms))) p[x.type] = x.value; return `${p.month}/${p.day} ${hhmm(ms)}`; };

export function createChat(W, X) {
  const { ui } = X, S = X.state || W.state, qs = new URLSearchParams(location.search), C = id => W.chars.get(id);
  const K = { open: false, mode: 'idle', to: 'ceo', msgs: new Map(), rev: 0, lastSeen: null, srvNow: null, busy: false, err: '', timer: 0, inflight: false, first: true, started: new Set(), todo: new Map(), url: '', fails: 0,
    pollMs: Math.max(300, +qs.get('chat_poll') || 5000), bgMs: Math.max(300, +qs.get('chat_bg_poll') || 15000), polls: 0 };
  W.chat = K;

  // ───────── 介面骨架 ─────────
  const bar = $('bar'), btn = document.createElement('button');
  btn.className = 'btn chat-b'; btn.id = 'chatBtn'; btn.type = 'button'; btn.setAttribute('aria-haspopup', 'dialog'); btn.setAttribute('aria-expanded', 'false');
  btn.innerHTML = '下指令<i class="cn" id="chatN" hidden></i>';
  bar.insertBefore(btn, $('editBtn') || null);
  const pn = document.createElement('aside');
  pn.className = 'panel'; pn.id = 'chatPanel'; pn.setAttribute('role', 'dialog'); pn.setAttribute('aria-label', '對 Agent 下指令'); pn.hidden = true;
  pn.innerHTML = `<button class="x" id="chatX" type="button" aria-label="關閉">×</button>
    <h3 id="chatT">對 Agent 下指令</h3>
    <div class="c-live" id="chatLive" role="status"></div>
    <div class="c-note" id="chatNote" role="status" hidden></div>
    <div class="c-note c-gate" id="chatGate" role="status" hidden></div>
    <div class="c-list" id="chatList" aria-live="polite"></div>
    <form class="c-form" id="chatForm" autocomplete="off">
      <label for="chatTo">收件對象</label><select id="chatTo"></select>
      <label for="chatText">指令內容</label><textarea id="chatText" rows="3" placeholder="例如：手機版頂列按鈕太小，幫我調大" spellcheck="false"></textarea>
      <div class="c-row"><span id="chatCount" class="c-cnt">已輸入 0／${MAX_TEXT}</span><button class="btn on" id="chatSend" type="submit">送出</button></div>
      <p class="c-hint">Enter 換行，Ctrl／⌘＋Enter 送出。指令由你自己的 Claude 取走執行，這個網頁不會呼叫任何模型。</p>
      <p class="c-err" id="chatErr" role="alert" hidden></p>
    </form>`;
  $('app').append(pn);

  // ───────── 連線：收件服務網址＋登入權杖 ─────────
  const tok = () => lsGet(ACCT_TOK);
  function loadScript(src) { return new Promise(res => { const s = document.createElement('script'); s.src = src; s.onload = s.onerror = () => res(); setTimeout(res, 4000); document.head.append(s); }); }
  async function bridgeUrl() {
    if (K.url) return K.url;
    if (W.live && W.live.resolveUrl) K.url = (await W.live.resolveUrl()) || '';
    else {
      try { const o = JSON.parse(lsGet(LS_LIVE) || 'null'); if (o && o.url) K.url = o.url; } catch (e) { /* 略 */ }
      if (!K.url) { if (!window.TW_ACCOUNT) await loadScript('../account_config.js'); const api = window.TW_ACCOUNT && window.TW_ACCOUNT.api; if (api && /\/\/tw-account\./.test(api)) K.url = api.replace('//tw-account.', '//tw-ai-office-bridge.').replace(/\/+$/, ''); }
    }
    return K.url;
  }
  // 回傳 { status, json }；連不上＝status 0
  async function call(path, opt = {}) {
    const url = await bridgeUrl(), t = tok(); if (!url) return { status: -1, json: {} };
    try {
      const r = await fetch(url + '/v1/office/main/inbox' + path, { method: opt.method || 'GET', headers: { 'X-AIO-Session': t, ...(opt.body ? { 'Content-Type': 'application/json' } : {}) }, body: opt.body, cache: 'no-store', credentials: 'omit' });
      const j = await r.json().catch(() => ({}));
      return { status: r.status, json: j || {} };
    } catch (e) { return { status: 0, json: {} }; }
  }

  // ───────── 資料合併與狀態轉換 → 事件匯流排 ─────────
  const emit = (name, id, data) => { try { W.emit && W.emit(name, id, data); } catch (e) { console.warn('指令事件例外', e); } };
  function merge(list, silent) {
    for (const m of list || []) {
      if (!m || !m.id) continue; const old = K.msgs.get(m.id); K.msgs.set(m.id, m);
      if (old && old.status === m.status) continue;
      const ev = { queued: 'cmd_queued', claimed: 'cmd_claimed', running: 'cmd_running', done: 'cmd_done', failed: 'cmd_failed', canceled: 'cmd_gone', expired: 'cmd_gone', stale: 'cmd_gone' }[m.status];
      // 載入時就已完成的舊指令不再慶祝一次（silent）；進行中的照樣演出
      if (ev && !(silent && !ACTIVE.has(m.status))) emit(ev, m.to, { mid: m.id, text: m.text, reply: m.reply, status: m.status });
    }
  }
  const activeCount = () => [...K.msgs.values()].filter(m => ACTIVE.has(m.status)).length;
  function syncBadge() {
    const n = activeCount(), el = $('chatN'); el.hidden = !n; el.textContent = n || '';
    btn.setAttribute('aria-label', n ? `下指令（${n} 則進行中）` : '下指令'); lsSet(LS_ACTIVE, n ? '1' : null);
  }

  async function fetchInbox(manual) {
    if (K.inflight) return; K.inflight = true; K.polls++;
    try {
      if (!tok()) { K.mode = 'nologin'; return; }
      const r = await call('?since=' + K.rev);
      if (r.status === 200) {
        K.mode = 'ok'; K.fails = 0; const j = r.json; K.srvNow = j.now || null; K.lastSeen = j.session_last_seen == null ? null : j.session_last_seen;
        merge(j.messages, K.first); merge(j.open, K.first); if (j.rev != null) K.rev = j.rev; K.first = false;
      } else if (r.status === 401) K.mode = 'auth';
      else if (r.status === 403) K.mode = 'forbidden';
      else if (r.status === 0 || r.status === 429 || r.status >= 500 && r.status !== 501 && r.status !== 503) { K.fails++; if (K.mode !== 'ok' || manual) K.mode = 'neterr'; }
      else K.mode = 'noinbox';          // 404／501／503…：收件服務還沒有收件匣這條路（還沒更新或還沒開）
    } finally { K.inflight = false; render(); schedule(); }
  }
  function schedule() {
    clearTimeout(K.timer);
    if (!tok() || K.mode === 'auth' || K.mode === 'forbidden' || K.mode === 'noinbox') return;       // 這幾種等使用者處理，不自己一直敲
    const need = K.open || activeCount() > 0; if (!need) return;
    const ms = (K.open ? K.pollMs : K.bgMs) * (K.fails > 2 ? 4 : 1);
    K.timer = setTimeout(() => { if (document.hidden) { schedule(); return; } fetchInbox(); }, ms);
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden && (K.open || activeCount())) fetchInbox(); });

  // ───────── 畫面 ─────────
  function noteHtml() {
    const home = '<a href="../index.html">網站首頁</a>';
    switch (K.mode) {
      case 'nologin': return `<b>要用站長帳號登入才能下指令。</b><br>請先到${home}用管理者的 Google 帳號登入，再回到這裡。`;
      case 'auth': return `<b>登入已過期，或目前登入的不是站長帳號。</b><br>請到${home}重新登入站長帳號，再回到這裡。`;
      case 'forbidden': return '<b>這個網址不能下指令。</b><br>只有正式網站上的站長帳號可以使用；預覽版與其他網址不開放。';
      case 'noinbox': return '<b>指令收件匣還沒有開放。</b><br>收件服務還沒更新，或站長還沒開啟這個功能，所以現在送出的指令不會被保存。開放之後這裡就能直接用；在那之前，請先在你的 Claude 裡直接交代。<br><button class="btn" id="chatRetry" type="button">再試一次</button>';
      case 'neterr': return '<b>暫時連不上收件服務。</b><br>會自動重試，也可以<button class="btn" id="chatRetry" type="button">現在再試一次</button>';
      default: return '';
    }
  }
  function liveHtml() {
    if (K.mode !== 'ok') return '';
    const ref = K.srvNow || Date.now(), on = K.lastSeen != null && ref - K.lastSeen < ONLINE_MS;
    return on ? '<i class="dot on"></i>你的 Claude 在線上' : '<i class="dot"></i>你的 Claude 目前沒開，指令會排隊，下次開工作階段時才會被取走（最多保留 24 小時）';
  }
  function targetsHtml() {
    const list = [...W.chars.values()].filter(c => !c.spec.pet && !c.spec.isCeo && !c.jobless).map(c => c.spec);
    const opts = [['ceo', '交給 CEO 分派']].concat(list.map(s => [s.id, `${s.nick}（${s.zh}）`]));
    if (!opts.some(o => o[0] === K.to)) K.to = 'ceo';
    return opts.map(([v, t]) => `<option value="${esc(v)}"${v === K.to ? ' selected' : ''}>${esc(t)}</option>`).join('');
  }
  const nameOf = id => { if (id === 'ceo') return 'CEO（分派）'; const c = C(id); return c && !c.spec.pet ? `${c.spec.nick}（${c.spec.zh}）` : id; };
  function msgHtml(m) {
    const [lab, cls] = ST[m.status] || [m.status, 'x'];
    return `<article class="c-msg" data-id="${esc(m.id)}" data-st="${esc(m.status)}"><header><b>${esc(nameOf(m.to))}</b><time>${esc(when(m.created))}</time><span class="c-st ${cls}">${m.status === 'running' ? '<i class="spin"></i>' : ''}${esc(lab)}</span></header>
      <p class="c-tx">${esc(m.text)}</p>${m.reply ? `<div class="c-rp"><b>回覆</b><div>${linkify(m.reply)}</div></div>` : ''}
      ${m.status === 'queued' ? `<button class="btn c-mini" type="button" data-cancel="${esc(m.id)}">撤回</button>` : ''}${m.status === 'stale' || m.status === 'expired' ? `<button class="btn c-mini" type="button" data-again="${esc(m.id)}">重送</button>` : ''}</article>`;
  }
  function render() {
    syncBadge(); if (!K.open) return;
    const note = $('chatNote'), nh = noteHtml(); if (note.dataset.h !== nh) { note.innerHTML = nh; note.dataset.h = nh; } note.hidden = !nh;
    // 功能閘門（features.js 的 office.cmd）：只在已經能送（連線正常）時才顯示，沒登入等情況已經有自己的說明
    const gt = W.gate && K.mode === 'ok' ? W.gate.peek('office.cmd') : null, gnote = gt && gt.note ? gt.note : '', gbox = $('chatGate');
    if (gbox.textContent !== gnote) gbox.textContent = gnote; gbox.hidden = !gnote; K.gated = !!(gt && !gt.pass);
    const lv = liveHtml(); if ($('chatLive').dataset.h !== lv) { $('chatLive').innerHTML = lv; $('chatLive').dataset.h = lv; }
    const list = [...K.msgs.values()].sort((a, b) => a.created - b.created), box = $('chatList');
    const html = list.length ? list.map(msgHtml).join('') : (K.mode === 'ok' ? '<p class="c-empty">還沒有送出過指令。選好收件對象、寫下要做的事，按「送出」。</p>' : '');
    if (box.dataset.h !== html) { const stick = box.scrollHeight - box.scrollTop - box.clientHeight < 40; box.innerHTML = html; box.dataset.h = html; if (stick) box.scrollTop = box.scrollHeight; }
    const sel = $('chatTo'); if (sel.dataset.n !== String(W.chars.size) + K.to) { sel.innerHTML = targetsHtml(); sel.dataset.n = String(W.chars.size) + K.to; }
    const n = $('chatText').value.length, over = n > MAX_TEXT, can = K.mode === 'ok' && !K.busy && n > 0 && !over && !K.gated;
    $('chatCount').textContent = `已輸入 ${n}／${MAX_TEXT}`; $('chatCount').classList.toggle('over', over);
    const sb = $('chatSend'); sb.disabled = !can;
    sb.textContent = K.mode === 'nologin' ? '請先登入' : K.mode === 'ok' ? (K.busy ? '送出中…' : '送出') : K.mode === 'loading' ? '連線中…' : '暫時不能送';
    sb.title = over ? '超過 2000 字，請縮短' : '';
    const er = $('chatErr'); er.hidden = !K.err; er.textContent = K.err;
  }
  function open(to) {
    if (to) K.to = to;
    K.open = true; K.err = ''; pn.hidden = false; btn.setAttribute('aria-expanded', 'true'); btn.classList.add('on');
    for (const id of ['log', 'card', 'board']) { const e = $(id); if (e && !e.hidden && !e.classList.contains('mini')) e.hidden = true; }   // 右側／左下的面板讓出位置（不疊在一起）
    const sel = $('chatTo'); sel.dataset.n = ''; render();
    K.mode = !tok() ? 'nologin' : K.mode === 'ok' ? 'ok' : 'loading';
    render(); fetchInbox(true);
    if (W.gate) W.gate.load().then(render);
    setTimeout(() => { try { $('chatText').focus({ preventScroll: true }); } catch (e) { /* 略 */ } }, 30);
  }
  function close() { K.open = false; pn.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.classList.remove('on'); schedule(); }
  K.openTo = open; K.close = close;
  btn.onclick = () => (K.open ? close() : open());
  $('chatX').onclick = close;
  pn.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); close(); try { btn.focus(); } catch (x) { /* 略 */ } } });

  async function send() {
    const text = $('chatText').value.trim(); if (K.busy || !text || text.length > MAX_TEXT || K.mode !== 'ok') return;
    K.busy = true; K.err = ''; render();
    const gt = W.gate ? await W.gate.begin('office.cmd') : null;           // 功能閘門：今天的次數用完就不送（說明由 render 顯示在對話框裡）
    if (gt && !gt.pass) { K.busy = false; render(); return; }
    const r = await call('', { method: 'POST', body: JSON.stringify({ to: K.to, text }) });
    K.busy = false; if (gt) { if (r.status === 200 && r.json.message) gt.done(); else gt.cancel(); }
    if (r.status === 200 && r.json.message) { $('chatText').value = ''; merge([r.json.message]); K.rev = Math.max(K.rev, r.json.message.rev || 0); K.mode = 'ok'; schedule(); const box = $('chatList'); render(); box.scrollTop = box.scrollHeight; }
    else if (r.status === 401) { K.mode = 'auth'; render(); }
    else if (r.status === 403) { K.mode = 'forbidden'; render(); }
    else if (r.status === 0 || r.status === -1) K.err = '連不上收件服務，指令沒有送出，請稍後再試';
    else if (r.status === 404 || r.status === 501 || r.status === 503) { K.mode = 'noinbox'; render(); }
    else K.err = ERR[r.json.error] || ('送出失敗（' + r.status + '），請稍後再試');
    render();
  }
  $('chatForm').addEventListener('submit', e => { e.preventDefault(); send(); });
  $('chatText').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); } });
  $('chatText').addEventListener('input', () => { K.err = ''; render(); });
  $('chatTo').addEventListener('change', e => { K.to = e.target.value; });
  pn.addEventListener('click', async e => {
    const t = e.target.closest('button'); if (!t) return;
    if (t.id === 'chatRetry') { K.mode = 'loading'; K.fails = 0; render(); fetchInbox(true); return; }
    if (t.dataset.cancel) {
      t.disabled = true; const r = await call('/' + encodeURIComponent(t.dataset.cancel) + '/cancel', { method: 'POST', body: '{}' });
      if (r.status === 200) merge([{ ...K.msgs.get(t.dataset.cancel), status: 'canceled' }]);
      else { K.err = r.status === 409 ? '這則已經被取走，不能撤回了' : '撤回失敗，請稍後再試'; await fetchInbox(); }
      render(); return;
    }
    if (t.dataset.again) { const m = K.msgs.get(t.dataset.again); if (m) { K.to = m.to; $('chatTo').dataset.n = ''; $('chatText').value = m.text; render(); $('chatText').focus(); ui.toast('已帶回輸入框，按「送出」就會再送一次'); } }
  });

  // ───────── 資訊卡：「對他下指令」 ─────────
  // 在 main.js 裡、live.js 載入之前就包好 ui.showCard（live.js 切換模式時會還原成它記住的版本，所以順序不能反）。
  const origShow = ui.showCard;
  ui.showCard = c => {
    origShow(c);
    if (c.jobless || (c.spec && c.spec.pet)) return;
    const cardEl = $('card'), acts = [...cardEl.querySelectorAll('.acts')].pop(); if (!acts || cardEl.querySelector('[data-chat]')) return;
    const b = document.createElement('button'); b.className = 'btn on'; b.type = 'button'; b.dataset.chat = c.spec.id; b.textContent = c.spec.isCeo ? '對 CEO 下指令' : '對他下指令';
    acts.append(b);
  };
  $('card').addEventListener('click', e => { const b = e.target.closest('[data-chat]'); if (!b) return; $('card').hidden = true; open(b.dataset.chat === 'ceo' || (C(b.dataset.chat) && C(b.dataset.chat).spec.isCeo) ? 'ceo' : b.dataset.chat); });

  // ───────── 3D 反應：待辦小圖示、去座位工作、完成小慶祝 ─────────
  const who = id => { const c = C(id); return c && !c.spec.pet && !c.jobless ? c : (id === 'ceo' ? C('ceo') : null); };
  function stopTodo(id) { const t = K.todo.get(id); if (t) { clearInterval(t.h); K.todo.delete(id); } }
  function startTodo(id, mid) {
    const c = who(id); if (!c) return; const t = K.todo.get(id) || { mids: new Set() }; t.mids.add(mid);
    if (!t.h) { const ping = () => { const q = who(id); if (q && !q.piloted && !q.sleeping && !(q.busy && q.job)) q.emote('note', 2.4); }; ping(); t.h = setInterval(ping, 2600); }
    K.todo.set(id, t);
  }
  function endTodo(id, mid) { const t = K.todo.get(id); if (!t) return; t.mids.delete(mid); if (!t.mids.size) stopTodo(id); }
  const cmdAgent = mid => 'cmd:' + mid;
  // 事件匯流排有兩種長相：phys.js 的處理函式只收一個事件物件 { type, id, …附加欄位 }；mind.js 的收 (代號, 附加欄位)。兩種都吃。
  const ok = (fn) => (a, b) => { try { if (a && typeof a === 'object') fn(a.id, a); else fn(a, b || {}); } catch (e) { console.warn('指令反應例外', e); } };
  function sub(name, fn) { if (W.on) W.on(name, ok(fn)); }
  const hook = () => {
    sub('cmd_queued', (id, d) => startTodo(id, d.mid));
    sub('cmd_claimed', (id, d) => { startTodo(id, d.mid); });
    sub('cmd_running', (id, d) => {
      endTodo(id, d.mid); const c = who(id); if (!c || K.started.has(d.mid)) return; K.started.add(d.mid);
      if (c.spec.isCeo) { c.say('收到，我來處理', 2.2); c.emote('bulb', 1.8); if (c.state === 'sit') c.setAction('type'); return; }
      const a = S.agents.get(c.spec.id);
      if (a && a.phase !== 'idle') { c.emote('bulb', 1.8); return; }       // 已經有真的事件在做同一位的工作：不重複派
      S.emit({ hook_event_name: 'SubagentStart', uid: 'cmd:' + d.mid + ':s', agent_id: cmdAgent(d.mid), agent_type: c.spec.id, description: short(d.text, 24) || '站長的指令', tool_category: 'write' });
    });
    const fin = failed => (id, d) => {
      endTodo(id, d.mid); const c = who(id); if (!c) return;
      if (K.started.has(d.mid) && !c.spec.isCeo) S.emit({ hook_event_name: 'SubagentStop', uid: 'cmd:' + d.mid + ':e', agent_id: cmdAgent(d.mid), agent_type: c.spec.id, status: failed ? 'failed' : 'completed', last_assistant_message: failed ? '指令沒做成' : '指令做完了' });
      const wasRun = K.started.has(d.mid);
      const cheer = () => { const q = who(id); if (q) { q.emote('star', 2.6); q.say('指令做完了！', 2.6); } };
      if (!failed) { if (wasRun && !c.spec.isCeo) setTimeout(cheer, 6500); else cheer(); }   // 走去交件的人，等交件演出收尾再慶祝（不打斷）
      else c.emote('cloud', 2.4);
      K.started.delete(d.mid);
      if (K.open && ui.toast) ui.toast(failed ? `${c.spec.nick}沒做成：看看回覆` : `${c.spec.nick}做完了：看回覆`);
    };
    sub('cmd_done', fin(false)); sub('cmd_failed', fin(true));
    sub('cmd_gone', (id, d) => { endTodo(id, d.mid); });
  };
  // 事件匯流排由 mind.js 建（main.js 先建 mind 再建這支）；保險：沒有就等一下
  if (W.on) hook(); else { let n = 0; const t = setInterval(() => { if (W.on || ++n > 40) { clearInterval(t); if (W.on) hook(); } }, 250); }

  // 開頁時如果上次還有進行中的指令，讀一次（讓小圖示與工作演出接得上）；其餘不主動打收件服務
  if (tok() && lsGet(LS_ACTIVE) === '1') setTimeout(() => fetchInbox(), 1200);
  render();
  return K;
}
