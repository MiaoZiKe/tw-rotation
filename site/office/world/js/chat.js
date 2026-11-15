// 主對話框（2026-11-15 晚改版，規格 docs/ai_office/plan.md 最後一節「主對話框」＋ docs/ai_office/chat_command_spec.md 第六節）
//
// 擁有者原話：不管對哪個 Agent 下達指令，其實都是對 CEO 下達指令；點某位 Agent 只是讓 Claude 知道這件事是給誰做，目的是更可視化、更直觀。
// 所以這裡的做法是：
//   · 對話框常駐在畫面下方（像聊天軟體的輸入列）。沒選人＝對 CEO 說；點 3D 裡的 Agent 或資訊卡「對他說」＝對象切成他。
//   · 技術上一律送進 CEO 的收件匣（POST /v1/office/main/inbox），收件匣的 `to` 欄位就是「指定給哪位 Agent」；CEO 的 Claude 取走後派給那位。
//     畫面上每則訊息下方寫「由 CEO 轉交給 ○○」，回覆用那位 Agent 的頭像顯示在他自己的對話串，3D 裡他頭上冒短短的對話泡泡。
//   · 對話串依收件匣資料的 `to` 分組：每位 Agent 一串、CEO 一串，不另存任何資料（重新整理後從收件匣讀回來）。
//
// 網站只是「留言板」：站長在這裡送出 → 收件服務（workers/ai-office-bridge）存起來 → 站長自己的 Claude 去取走、做完、把回覆貼回來。網站與收件服務完全不呼叫任何模型。
//
// 鐵則（為什麼這樣寫）：
//   · 只用「網站登入權杖」（localStorage tw.acct.tok，標頭 X-AIO-Session）。接入碼在這裡一律不碰、也不顯示——收件服務本來就拒絕用接入碼寫收件匣，
//     前端碰了只會多一條外洩路徑。
//   · 沒登入、不是站長、收件服務還沒開收件匣：一律顯示白話說明與下一步，不丟錯誤、不留空白。
//   · 使用者還沒碰對話框（沒聚焦輸入框、沒展開、沒送出）之前不發任何請求（只有「上次還有進行中的指令」才在載入後讀一次），避免辦公室一載入就打收件服務。
//   · 送出前一定過功能閘門 W.gate.begin('office.cmd')（gate.js；用到上限就不送、顯示說明）。這條不能拿掉。
//   · 3D 反應只走既有事件匯流排 W.emit／W.on（cmd_queued／cmd_claimed／cmd_running／cmd_done／cmd_failed／cmd_gone），
//     真正的演出沿用 jobs.js（派工→走去 CEO 桌領任務→回座位工作→交件）；這裡只加「待辦小圖示」「完成小慶祝」與「回覆短句泡泡」。
//   · 輸入框打字時不能觸發場景快捷鍵：pilot.js／multi.js／sports.js 都用 typing() 擋掉 INPUT／TEXTAREA，這裡再把 keydown 在輸入框就地吃掉（不往 window 冒）。
import { hhmm } from './state.js';

const ACCT_TOK = 'tw.acct.tok', LS_LIVE = 'aiOffice.live.v1', LS_ACTIVE = 'aiOffice.chat.active';
const MAX_TEXT = 2000, ONLINE_MS = 5 * 60e3, WIDE_PX = 1180;
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { /* 略 */ } };
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const ST = { queued: ['排隊中', 'sq'], claimed: ['已取走', 'sc'], running: ['執行中', 'sr'], done: ['完成', 'sd'], failed: ['失敗', 'sf'], canceled: ['已撤回', 'sx'], expired: ['過期（沒有 Claude 來拿）', 'sx'], stale: ['沒有回音', 'sw'] };   // 類別名加 s 前綴：單一字母的 .x 會撞到面板的關閉鈕樣式
const ACTIVE = new Set(['queued', 'claimed', 'running']);
const ERR = { too_long: '最多 2000 字', queue_full: '排隊已滿 20 則，等 Claude 取走一些再送', rate: '送太快了，一分鐘後再試', rate_day: '今天已送 100 則，明天再送', empty: '請先輸入要說的話', bad_to: '收件對象格式不對，請重新選一位' };
// 把回覆裡的網址變成可點的連結（先跳脫再換，避免把回覆當 HTML 執行）
const linkify = s => esc(s).replace(/(https?:\/\/[^\s<>"')]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
const when = ms => { const p = {}; for (const x of new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Taipei', month: '2-digit', day: '2-digit' }).formatToParts(new Date(ms))) p[x.type] = x.value; return `${p.month}/${p.day} ${hhmm(ms)}`; };
// 3D 頭上泡泡用的短句：回覆的第一句、去掉網址，最多 18 字
const bubbleLine = r => { const t = String(r || '').replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' ').trim(); return short(t.split(/[。！!？?\n]/)[0] || t, 18); };

export function createChat(W, X) {
  const { ui } = X, S = X.state || W.state, qs = new URLSearchParams(location.search), C = id => W.chars.get(id);
  const K = { open: false, mode: 'idle', to: 'ceo', touched: false, msgs: new Map(), rev: 0, lastSeen: null, srvNow: null, busy: false, err: '', timer: 0, inflight: false, first: true, started: new Set(), todo: new Map(), url: '', fails: 0, seen: new Set(), cardFor: null,
    pollMs: Math.max(300, +qs.get('chat_poll') || 5000), bgMs: Math.max(300, +qs.get('chat_bg_poll') || 15000), polls: 0 };
  W.chat = K;

  // ───────── 介面骨架 ─────────
  // 上半（展開才有）：標題列＋對話串切換列＋訊息串；下半（常駐）：一行提示＋說明＋輸入列。
  const pn = document.createElement('section');
  pn.className = 'mc'; pn.id = 'chatPanel'; pn.setAttribute('role', 'region'); pn.setAttribute('aria-label', '主對話框');
  pn.innerHTML = `<div class="mc-top" id="mcTop" hidden>
      <div class="mc-head">
        <div class="mc-who" id="mcWho"></div>
        <button class="btn mc-ceo" id="chatCeo" type="button" hidden>回到 CEO</button>
        <button class="mc-x" id="chatX" type="button" aria-label="收合對話框" title="收合（Esc）">﹀</button>
      </div>
      <div class="c-live" id="chatLive" role="status"></div>
      <div class="mc-strip" id="mcStrip" role="tablist" aria-label="對話串" hidden></div>
      <div class="c-list" id="chatList" aria-live="polite"></div>
    </div>
    <div class="mc-dock" id="mcDock">
      <button class="mc-peek" id="chatPeek" type="button" hidden></button>
      <div class="c-note" id="chatNote" role="status" hidden></div>
      <div class="c-note c-gate" id="chatGate" role="status" hidden></div>
      <p class="c-err" id="chatErr" role="alert" hidden></p>
      <form class="mc-bar" id="chatForm" autocomplete="off">
        <button class="mc-tg" id="chatBtn" type="button" aria-haspopup="dialog" aria-expanded="false"><span class="mc-ava" id="mcAva"></span><span class="mc-nm" id="mcNm">CEO</span><i class="cn" id="chatN" hidden></i><em class="mc-chev" aria-hidden="true">︿</em></button>
        <textarea id="chatText" rows="1" enterkeyhint="send" placeholder="對 CEO 說…" spellcheck="false" aria-label="要說的話"></textarea>
        <button class="btn on" id="chatSend" type="submit">送出</button>
      </form>
      <div class="c-row"><span id="chatCount" class="c-cnt" hidden>已輸入 0／${MAX_TEXT}</span></div>
      <p class="c-hint" id="chatHint">Enter 送出，Shift＋Enter 換行。訊息一律由 CEO 收下，再轉交給你指定的人；這個網頁不會呼叫任何模型。</p>
    </div>`;
  $('app').append(pn);
  const btn = $('chatBtn'), tx = $('chatText');

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
      if (silent && !ACTIVE.has(m.status)) K.seen.add(m.id);        // 載入時就已完成的舊訊息：不當成「沒看過的新回覆」
      if (old && old.status === m.status) continue;
      const ev = { queued: 'cmd_queued', claimed: 'cmd_claimed', running: 'cmd_running', done: 'cmd_done', failed: 'cmd_failed', canceled: 'cmd_gone', expired: 'cmd_gone', stale: 'cmd_gone' }[m.status];
      // 載入時就已完成的舊指令不再慶祝一次（silent）；進行中的照樣演出
      if (ev && !(silent && !ACTIVE.has(m.status))) emit(ev, m.to, { mid: m.id, text: m.text, reply: m.reply, status: m.status });
    }
  }
  const activeCount = () => [...K.msgs.values()].filter(m => ACTIVE.has(m.status)).length;
  const toOf = m => m.to || 'ceo';
  const threadOf = id => [...K.msgs.values()].filter(m => toOf(m) === id).sort((a, b) => a.created - b.created);

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
  // 第一次碰對話框（聚焦輸入框／展開／送出）才開始跟收件服務與功能閘門對話
  function touch() {
    if (!K.touched) K.touched = true;
    if (!tok()) K.mode = 'nologin';
    else if (K.mode === 'idle' || K.mode === 'neterr') { K.mode = K.mode === 'idle' ? 'loading' : K.mode; fetchInbox(true); }
    if (W.gate) W.gate.load().then(render);
    render();
  }

  // ───────── 對象（誰）：名字、頭像 ─────────
  const isAgent = id => { const c = C(id); return !!c && !c.spec.pet && !c.spec.isCeo && !c.jobless; };
  const nickOf = id => { if (id === 'ceo') return 'CEO'; const c = C(id); return c && !c.spec.pet ? c.spec.nick : id; };
  const fullName = id => { if (id === 'ceo') return 'CEO（分派）'; const c = C(id); return c && !c.spec.pet ? `${c.spec.nick}（${c.spec.zh}）` : id; };
  const subOf = id => { if (id === 'ceo') return '所有訊息都先交給 CEO'; const c = C(id); return c ? `${c.spec.zh}・由 CEO 轉交` : '由 CEO 轉交'; };
  const avaOf = id => { const c = id === 'ceo' ? C('ceo') : C(id); if (c && ui.ava) { try { return ui.ava(c.spec); } catch (e) { /* 略 */ } } return '<div class="ava" style="background:#ffb057"></div>'; };

  // ───────── 畫面 ─────────
  function noteHtml() {
    const home = '<a href="../index.html">網站首頁</a>';
    switch (K.mode) {
      case 'nologin': return `<b>要用站長帳號登入才能說話。</b><br>請先到${home}用管理者的 Google 帳號登入，再回到這裡。`;
      case 'auth': return `<b>登入已過期，或目前登入的不是站長帳號。</b><br>請到${home}重新登入站長帳號，再回到這裡。`;
      case 'forbidden': return '<b>這個網址不能說話。</b><br>只有正式網站上的站長帳號可以使用；預覽版與其他網址不開放。';
      case 'noinbox': return '<b>收件匣還沒有開放。</b><br>收件服務還沒更新，或站長還沒開啟這個功能，所以現在送出的話不會被保存。開放之後這裡就能直接用；在那之前，請先在你的 Claude 裡直接交代。<br><button class="btn" id="chatRetry" type="button">再試一次</button>';
      case 'neterr': return '<b>暫時連不上收件服務。</b><br>會自動重試，也可以<button class="btn" id="chatRetry" type="button">現在再試一次</button>';
      default: return '';
    }
  }
  function liveHtml() {
    if (K.mode !== 'ok') return '';
    const ref = K.srvNow || Date.now(), on = K.lastSeen != null && ref - K.lastSeen < ONLINE_MS;
    return on ? '<i class="dot on"></i>你的 Claude 在線上' : '<i class="dot"></i>你的 Claude 目前沒開，訊息會排隊，下次開工作階段時才會被取走（最多保留 24 小時）';
  }
  function msgHtml(m) {
    const [lab, cls] = ST[m.status] || [m.status, 'x'], to = toOf(m), nk = esc(nickOf(to));
    const reply = m.reply ? linkify(m.reply) : (m.status === 'done' ? '做完了。' : '');
    return `<article class="c-msg" data-id="${esc(m.id)}" data-st="${esc(m.status)}">
      <div class="c-me"><header><time>${esc(when(m.created))}</time><span class="c-st ${cls}">${m.status === 'running' ? '<i class="spin"></i>' : ''}${esc(lab)}</span></header>
        <p class="c-tx">${esc(m.text)}</p>
        <p class="c-relay">${to === 'ceo' ? '送給 CEO' : `由 CEO 轉交給 ${nk}`}</p>
        ${m.status === 'queued' ? `<button class="btn c-mini" type="button" data-cancel="${esc(m.id)}">撤回</button>` : ''}${m.status === 'stale' || m.status === 'expired' ? `<button class="btn c-mini" type="button" data-again="${esc(m.id)}">重送</button>` : ''}</div>
      ${reply ? `<div class="c-rp"><span class="c-av">${avaOf(to)}</span><div class="c-rb"><b>${nk}</b><div>${reply}</div></div></div>` : ''}</article>`;
  }
  function stripHtml() {
    const ids = ['ceo']; const last = new Map();
    for (const m of K.msgs.values()) { const t = toOf(m); last.set(t, Math.max(last.get(t) || 0, m.created)); }
    [...last.entries()].sort((a, b) => b[1] - a[1]).forEach(([t]) => { if (t !== 'ceo' && !ids.includes(t)) ids.push(t); });
    if (!ids.includes(K.to)) ids.push(K.to);
    const act = {}; for (const m of K.msgs.values()) if (ACTIVE.has(m.status)) act[toOf(m)] = (act[toOf(m)] || 0) + 1;
    return ids.length < 2 ? '' : ids.map(id => `<button class="mc-th${id === K.to ? ' on' : ''}" type="button" role="tab" aria-selected="${id === K.to}" data-th="${esc(id)}"><span class="mc-ava">${avaOf(id)}</span><span>${esc(nickOf(id))}</span>${act[id] ? `<i class="cn">${act[id]}</i>` : ''}</button>`).join('');
  }
  function peekOf() {
    const list = threadOf(K.to), m = list[list.length - 1]; if (!m || K.open) return '';
    const unseen = !ACTIVE.has(m.status) && m.status !== 'canceled' && !K.seen.has(m.id);
    if (!ACTIVE.has(m.status) && !unseen) return '';
    const [lab] = ST[m.status] || [m.status];
    return m.reply ? `${nickOf(K.to)}：${short(m.reply.replace(/https?:\/\/\S+/g, '').trim() || '做完了', 40)}` : `${lab}・${short(m.text, 26)}`;
  }
  const gtxt = e => e.textContent;
  function render() {
    // 目前對象不在了（被開除、改成寵物）→ 回到 CEO
    if (K.to !== 'ceo' && !isAgent(K.to) && W.chars.size) K.to = 'ceo';
    const n = activeCount(), bn = $('chatN'); bn.hidden = !n; bn.textContent = n || ''; lsSet(LS_ACTIVE, n ? '1' : null);
    btn.setAttribute('aria-label', (n ? `對話（${n} 則進行中）` : '對話') + `，目前對 ${nickOf(K.to)} 說`); btn.setAttribute('aria-expanded', String(K.open)); btn.classList.toggle('on', K.open);
    pn.classList.toggle('open', K.open); $('app').classList.toggle('mc-open', K.open); $('mcTop').hidden = !K.open;
    // 對象：頭像＋名字＋輸入框提示
    const who = nickOf(K.to), av = avaOf(K.to);
    if ($('mcAva').dataset.k !== K.to + av.length) { $('mcAva').innerHTML = av; $('mcAva').dataset.k = K.to + av.length; }
    $('mcNm').textContent = who;
    tx.placeholder = K.to === 'ceo' ? '對 CEO 說…' : innerWidth <= 640 ? `對 ${who} 說…` : `對 ${who} 說…（由 CEO 轉交）`;      // 手機輸入列窄，轉交的說明留在對話串裡
    // 說明與閘門（收合時也要看得到：鎖了要知道為什麼）
    const note = $('chatNote'), nh = K.touched ? noteHtml() : ''; if (note.dataset.h !== nh) { note.innerHTML = nh; note.dataset.h = nh; } note.hidden = !nh;
    // 功能閘門（features.js 的 office.cmd）：只在已經能送（連線正常）時才顯示，沒登入等情況已經有自己的說明
    const gt = W.gate && K.mode === 'ok' ? W.gate.peek('office.cmd') : null, gnote = gt && gt.note ? gt.note : '', gbox = $('chatGate');
    if (gbox.textContent !== gnote) gbox.textContent = gnote; gbox.hidden = !gnote; K.gated = !!(gt && !gt.pass);
    const pk = peekOf(), pe = $('chatPeek'); pe.hidden = !pk; if (pe.textContent !== pk) pe.textContent = pk;
    const t = tx.value.length, over = t > MAX_TEXT, can = ['ok', 'idle', 'loading'].includes(K.mode) && !K.busy && t > 0 && !over && !K.gated;
    const cnt = $('chatCount'); cnt.textContent = `已輸入 ${t}／${MAX_TEXT}`; cnt.classList.toggle('over', over); cnt.hidden = !(K.open || t > 1500);
    const sb = $('chatSend'); sb.disabled = !can;
    sb.textContent = K.mode === 'nologin' ? '請先登入' : K.busy ? '送出中…' : '送出';
    sb.title = over ? '超過 2000 字，請縮短' : '';
    const er = $('chatErr'); er.hidden = !K.err; er.textContent = K.err;
    $('chatHint').hidden = !K.open;
    if (K.open) renderThread();
  }
  function renderThread() {
    $('mcWho').innerHTML = `<span class="mc-ava">${avaOf(K.to)}</span><span class="mc-nmx"><b>${esc(fullName(K.to))}</b><small>${esc(subOf(K.to))}</small></span>`;
    $('chatCeo').hidden = K.to === 'ceo';
    const lv = liveHtml(); if ($('chatLive').dataset.h !== lv) { $('chatLive').innerHTML = lv; $('chatLive').dataset.h = lv; }
    const sh = stripHtml(), st = $('mcStrip'); if (st.dataset.h !== sh) { st.innerHTML = sh; st.dataset.h = sh; } st.hidden = !sh;
    const list = threadOf(K.to), box = $('chatList'), me = fullName(K.to);
    const html = list.length ? list.map(msgHtml).join('') : (K.mode === 'ok' ? `<p class="c-empty">還沒有跟 ${esc(me)} 說過話。${K.to === 'ceo' ? '直接在下面打字，按 Enter 送出。' : `打字後按 Enter 送出，訊息會先交給 CEO，再由 CEO 轉交給 ${esc(nickOf(K.to))}。`}</p>` : '');
    if (box.dataset.h !== html) { const stick = box.scrollHeight - box.scrollTop - box.clientHeight < 40 || box.dataset.t !== K.to; box.innerHTML = html; box.dataset.h = html; box.dataset.t = K.to; if (stick) box.scrollTop = box.scrollHeight; }
    for (const m of list) K.seen.add(m.id);
  }
  function grow() { tx.style.height = 'auto'; tx.style.height = Math.min(tx.scrollHeight, 104) + 'px'; }

  // 展開時：窄螢幕上其他面板讓位（寬螢幕時對話框在中間，跟左邊資訊卡、右邊紀錄不重疊，不必讓）
  const narrow = () => innerWidth < WIDE_PX;
  function open(to, focus) {
    if (to) setTarget(to, true);
    touch(); K.open = true; K.err = '';
    if (narrow()) for (const id of ['log', 'card', 'board']) { const e = $(id); if (e && !e.hidden && !e.classList.contains('mini')) e.hidden = true; }
    const box = $('chatList'); box.dataset.h = ''; render(); fetchInbox(true);
    if (focus !== false) setTimeout(() => { try { tx.focus({ preventScroll: true }); } catch (e) { /* 略 */ } }, 30);
  }
  function close() { K.open = false; render(); schedule(); }
  function setTarget(id, quiet) {
    id = id || 'ceo'; if (id !== 'ceo' && !isAgent(id) && !(C(id) && C(id).spec.isCeo)) id = 'ceo'; if (C(id) && C(id).spec.isCeo) id = 'ceo';
    const ch = K.to !== id; K.to = id; K.err = ''; $('chatList').dataset.h = '';
    if (ch && !quiet) { btn.classList.remove('flash'); void btn.offsetWidth; btn.classList.add('flash'); }
    render();
  }
  K.openTo = (to) => open(to); K.close = close; K.setTarget = id => setTarget(id);
  btn.onclick = () => { if (K.open) close(); else open(null, false); };
  $('chatX').onclick = () => { close(); try { btn.focus(); } catch (e) { /* 略 */ } };
  $('chatCeo').onclick = () => { setTarget('ceo'); tx.focus(); };
  $('chatPeek').onclick = () => open(null, true);
  // 手機虛擬鍵盤與縮放：輸入框內容高度跟著長
  tx.addEventListener('focus', () => touch());
  // 輸入框打字不得觸發場景快捷鍵：這裡就地吃掉，不讓 keydown 往 window（pilot／multi／sports 的捕捉監聽在更外層，它們各自有 typing() 擋）
  tx.addEventListener('keydown', e => {
    e.stopPropagation();
    if (e.key === 'Escape') { e.preventDefault(); if (K.open) close(); try { tx.blur(); } catch (x) { /* 略 */ } return; }
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); send(); }        // 注音／拼音選字時的 Enter 不算送出
  });
  tx.addEventListener('keyup', e => e.stopPropagation());
  tx.addEventListener('input', () => { K.err = ''; grow(); render(); });
  pn.addEventListener('keydown', e => { if (e.key === 'Escape' && K.open) { e.stopPropagation(); close(); try { btn.focus(); } catch (x) { /* 略 */ } } });

  async function send() {
    const text = tx.value.trim(); if (K.busy || !text || text.length > MAX_TEXT) return;
    touch(); if (K.mode === 'loading') { K.busy = true; render(); while (K.inflight) await new Promise(r => setTimeout(r, 60)); K.busy = false; }
    if (K.mode !== 'ok') { render(); return; }
    K.busy = true; K.err = ''; render();
    const gt = W.gate ? await W.gate.begin('office.cmd') : null;           // 功能閘門：今天的次數用完就不送（說明由 render 顯示在對話框裡）
    if (gt && !gt.pass) { K.busy = false; render(); return; }
    const to = K.to, r = await call('', { method: 'POST', body: JSON.stringify({ to, text }) });
    K.busy = false; if (gt) { if (r.status === 200 && r.json.message) gt.done(); else gt.cancel(); }
    if (r.status === 200 && r.json.message) { tx.value = ''; grow(); merge([r.json.message]); K.rev = Math.max(K.rev, r.json.message.rev || 0); K.mode = 'ok'; schedule(); const box = $('chatList'); render(); box.scrollTop = box.scrollHeight; }
    else if (r.status === 401) { K.mode = 'auth'; render(); }
    else if (r.status === 403) { K.mode = 'forbidden'; render(); }
    else if (r.status === 0 || r.status === -1) K.err = '連不上收件服務，訊息沒有送出，請稍後再試';
    else if (r.status === 404 || r.status === 501 || r.status === 503) { K.mode = 'noinbox'; render(); }
    else K.err = ERR[r.json.error] || ('送出失敗（' + r.status + '），請稍後再試');
    render();
  }
  $('chatForm').addEventListener('submit', e => { e.preventDefault(); send(); });
  pn.addEventListener('click', async e => {
    const t = e.target.closest('button'); if (!t) return;
    if (t.dataset.th) { setTarget(t.dataset.th, true); return; }
    if (t.id === 'chatRetry') { K.mode = 'loading'; K.fails = 0; render(); fetchInbox(true); return; }
    if (t.dataset.cancel) {
      t.disabled = true; const r = await call('/' + encodeURIComponent(t.dataset.cancel) + '/cancel', { method: 'POST', body: '{}' });
      if (r.status === 200) merge([{ ...K.msgs.get(t.dataset.cancel), status: 'canceled' }]);
      else { K.err = r.status === 409 ? '這則已經被取走，不能撤回了' : '撤回失敗，請稍後再試'; await fetchInbox(); }
      render(); return;
    }
    if (t.dataset.again) { const m = K.msgs.get(t.dataset.again); if (m) { setTarget(toOf(m), true); tx.value = m.text; grow(); render(); tx.focus(); ui.toast('已帶回輸入框，按 Enter 就會再送一次'); } }
  });

  // ───────── 3D 裡點人、資訊卡「對他說」 ─────────
  // 在 main.js 裡、live.js 載入之前就包好 ui.showCard（live.js 切換模式時會還原成它記住的版本，所以順序不能反）。
  // 點 3D 的人 → showCard → 對象切成他。refreshCard 也會重呼叫 showCard（同一張卡），所以用 cardFor 記住「這張卡已經處理過」，卡片關掉才重置。
  const origShow = ui.showCard;
  ui.showCard = c => {
    origShow(c);
    if (c.jobless || (c.spec && c.spec.pet)) return;
    if (K.cardFor !== c.spec.id) { K.cardFor = c.spec.id; setTarget(c.spec.id, false); }
    const cardEl = $('card'), acts = [...cardEl.querySelectorAll('.acts')].pop(); if (!acts || cardEl.querySelector('[data-chat]')) return;
    const b = document.createElement('button'); b.className = 'btn on'; b.type = 'button'; b.dataset.chat = c.spec.id; b.textContent = c.spec.isCeo ? '對 CEO 說' : '對他說';
    acts.append(b);
  };
  try { new MutationObserver(() => { if ($('card').hidden) K.cardFor = null; }).observe($('card'), { attributes: true, attributeFilter: ['hidden'] }); } catch (e) { /* 略 */ }
  $('card').addEventListener('click', e => { const b = e.target.closest('[data-chat]'); if (!b) return; $('card').hidden = true; open(b.dataset.chat === 'ceo' || (C(b.dataset.chat) && C(b.dataset.chat).spec.isCeo) ? 'ceo' : b.dataset.chat, true); });

  // ───────── 量高度：讓其他底部元件（版本標記、運動場鈕、整修列、搖桿、緊急橫幅…）知道要讓出多少（--mc-h，chat.css 用） ─────────
  const root = document.documentElement;
  const measure = () => { const h = $('mcDock').offsetHeight, b = parseFloat(getComputedStyle(pn).bottom) || 12; root.style.setProperty('--mc-h', (h ? h + b + 6 : 0) + 'px'); };      // 對話框底邊離畫面底的距離＋自己的高度＋6px 縫隙
  try { new ResizeObserver(measure).observe($('mcDock')); } catch (e) { /* 略 */ }
  addEventListener('resize', measure); measure();

  // ───────── 3D 反應：待辦小圖示、去座位工作、完成小慶祝、回覆短句泡泡 ─────────
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
      const wasRun = K.started.has(d.mid), line = bubbleLine(d.reply) || (failed ? '這次沒做成…' : '做完了！');
      const cheer = () => { const q = who(id); if (q) { q.emote('star', 2.6); q.say(line, 4); } };   // 頭上泡泡就是回覆的第一句（短句），完整內容在他的對話串
      if (!failed) { if (wasRun && !c.spec.isCeo) setTimeout(cheer, 6500); else cheer(); }   // 走去交件的人，等交件演出收尾再慶祝（不打斷）
      else { c.emote('cloud', 2.4); c.say(line, 4); }
      K.started.delete(d.mid);
      if (!(K.open && K.to === toKey(id)) && ui.toast) ui.toast(failed ? `${c.spec.nick}沒做成：點對話框看回覆` : `${c.spec.nick}回覆了：點對話框看`);
    };
    sub('cmd_done', fin(false)); sub('cmd_failed', fin(true));
    sub('cmd_gone', (id, d) => { endTodo(id, d.mid); });
  };
  const toKey = id => { const c = C(id); return c && c.spec.isCeo ? 'ceo' : id; };
  // 事件匯流排由 mind.js 建（main.js 先建 mind 再建這支）；保險：沒有就等一下
  if (W.on) hook(); else { let n = 0; const t = setInterval(() => { if (W.on || ++n > 40) { clearInterval(t); if (W.on) hook(); } }, 250); }

  // 開頁時如果上次還有進行中的指令，讀一次（讓小圖示與工作演出接得上）；其餘不主動打收件服務
  if (tok() && lsGet(LS_ACTIVE) === '1') setTimeout(() => fetchInbox(), 1200);
  render();
  return K;
}
