// 主對話框（2026-11-15 晚改版，規格 docs/ai_office/plan.md 最後一節「主對話框」＋ docs/ai_office/chat_command_spec.md 第六節）
//
// 擁有者原話：不管對哪個 Agent 下達指令，其實都是對 CEO 下達指令；點某位 Agent 只是讓 Claude 知道這件事是給誰做，目的是更可視化、更直觀。
// 所以這裡的做法是：
//   · 對話框常駐在畫面下方（像聊天軟體的輸入列）。沒選人＝對 CEO 說；點 3D 裡的 Agent 或資訊卡「對他說」＝對象切成他。
//   · 技術上一律送進 CEO 的收件匣（POST /v1/office/main/inbox），收件匣的 `to` 欄位就是「指定給哪位 Agent」；CEO 的 Claude 取走後派給那位。
//     畫面是聊天軟體的長相（2026-11-15 夜再改版）：左邊對話清單（每位對象一列）、右邊對話串（我靠右彩色氣泡、對方靠左白氣泡＋頭像）；
//     狀態只用聊天軟體的說法（傳送中→已送達→對方輸入中…→直接看到回覆），不再寫「由 CEO 轉交給 ○○」。
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


const ACCT_TOK = 'tw.acct.tok', LS_LIVE = 'aiOffice.live.v1', LS_ACTIVE = 'aiOffice.chat.active', LS_WIN = 'aiOffice.chat.win';
const MAX_TEXT = 2000, ONLINE_MS = 5 * 60e3, WIDE_PX = 1180;
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { /* 略 */ } };
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
// 狀態用聊天軟體的說法：傳送中（排隊）→ 已送達（Claude 取走）→ 對方輸入中…（執行中，三點動畫在對方那側）→ 已回覆（不另外標，直接看到回覆）
const ST = { queued: ['傳送中', 'sq'], claimed: ['已送達', 'sc'], running: ['已送達', 'sc'], done: ['已回覆', 'sd'], failed: ['沒做成', 'sf'], canceled: ['已撤回', 'sx'], expired: ['沒有人取走（過期）', 'sx'], stale: ['沒有回音', 'sw'] };   // 類別名加 s 前綴：單一字母的 .x 會撞到面板的關閉鈕樣式
// 辦公室外的內建類型（沒有座位的子 Agent）也要顯示中文暱稱；跟 live.js 的 BUILTIN 同一份對照
const BUILTIN_ZH = { 'general-purpose': '通才', Explore: '探路', Plan: '規劃', 'statusline-setup': '設定', 'claude-code-guide': '導覽', 'output-style-setup': '樣式' };
const ACTIVE = new Set(['queued', 'claimed', 'running']);
const ERR = { too_long: '最多 2000 字', queue_full: '排隊已滿 20 則，等 Claude 取走一些再送', rate: '送太快了，一分鐘後再試', rate_day: '今天已送 100 則，明天再送', empty: '請先輸入要說的話', bad_to: '收件對象格式不對，請重新選一位' };
// 把回覆裡的網址變成可點的連結（先跳脫再換，避免把回覆當 HTML 執行）
const linkify = s => esc(s).replace(/(https?:\/\/[^\s<>"')]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
const when = ms => { const p = {}; for (const x of new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Taipei', month: '2-digit', day: '2-digit' }).formatToParts(new Date(ms))) p[x.type] = x.value; return `${p.month}/${p.day} ${hhmm(ms)}`; };
// 3D 頭上泡泡用的短句：回覆的第一句、去掉網址，最多 18 字
const bubbleLine = r => { const t = String(r || '').replace(/【\s*動作\s*[:：]\s*[^】]*】/g, '').replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' ').trim(); return short(t.split(/[。！!？?\n]/)[0] || t, 18); };

export function createChat(W, X) {
  const { ui } = X, S = X.state || W.state, qs = new URLSearchParams(location.search), C = id => W.chars.get(id);
  const K = { open: false, mode: 'idle', to: 'ceo', touched: false, msgs: new Map(), rev: 0, lastSeen: null, srvNow: null, busy: false, err: '', timer: 0, inflight: false, first: true, started: new Set(), todo: new Map(), url: '', fails: 0, seen: new Set(), cardFor: null,
    pollMs: Math.max(300, +qs.get('chat_poll') || 5000),
    // 有指令在傳送中／已送達／輸入中時，不管展開或收合一律每 2 秒讀一次（以前收合時 15 秒，等回覆等得最久）；測試用 chat_fast（或舊參數 chat_bg_poll）縮短
    fastMs: Math.max(300, +qs.get('chat_fast') || +qs.get('chat_bg_poll') || 2000), polls: 0, view: 'list', again: false, pref: null };
  W.chat = K;

  // ───────── 介面骨架 ─────────
  // 展開＝聊天視窗：標題列（拖曳把手＋位置／鎖定／透明）→ 左邊對話清單、右邊對話串 → 底部輸入列；收合＝只有一行輸入列。
  // .mc-top 用 display:contents，裡面的標題列、清單、對話串直接參與 #chatPanel 的格線（輸入列只在對話串那一欄底下，像 Teams）。
  const pn = document.createElement('section');
  pn.className = 'mc pl'; pn.id = 'chatPanel'; pn.setAttribute('role', 'region'); pn.setAttribute('aria-label', '主對話框');
  pn.innerHTML = `<div class="mc-top" id="mcTop" hidden>
      <div class="mc-head" id="mcHead">
        <button class="mc-bk" id="mcBack" type="button" aria-label="回到對話清單">‹</button>
        <div class="mc-who" id="mcWho"></div>
        <span class="c-live" id="chatLive" role="status"></span>
        <div class="mc-ctl" id="mcCtl">
          <span class="mc-seg" role="group" aria-label="視窗位置"><button type="button" data-pos="left" title="靠左">左</button><button type="button" data-pos="center" title="置中">中</button><button type="button" data-pos="right" title="靠右">右</button></span>
          <button type="button" class="mc-tool" id="mcLock" aria-pressed="false" title="鎖定視窗位置">鎖定</button>
          <button type="button" class="mc-tool" id="mcOp" title="視窗透明度（滑鼠移上去會恢復清楚）">透明 100%</button>
        </div>
        <button class="mc-help" id="mcHelp" type="button" aria-label="說明" aria-expanded="false">?</button>
        <button class="mc-x" id="chatX" type="button" aria-label="收合對話框" title="收合（Esc）">﹀</button>
      </div>
      <aside class="mc-side" id="mcSide"><div class="mc-sh">對話</div><div class="mc-strip" id="mcStrip" role="tablist" aria-label="對話清單"></div></aside>
      <div class="mc-main">
        <p class="mc-tip" id="mcTip" hidden>訊息會先交給 CEO，由 CEO 分派給你指定的同事；這個網頁本身不呼叫任何模型。</p>
        <div class="c-list" id="chatList" aria-live="polite"></div>
      </div>
    </div>
    <div class="mc-dock" id="mcDock">
      <button class="mc-peek" id="chatPeek" type="button" hidden></button>
      <div class="c-note" id="chatNote" role="status" hidden></div>
      <div class="c-note c-gate" id="chatGate" role="status" hidden></div>
      <p class="c-err" id="chatErr" role="alert" hidden></p>
      <form class="mc-bar" id="chatForm" autocomplete="off">
        <button class="mc-tg" id="chatBtn" type="button" aria-haspopup="dialog" aria-expanded="false"><span class="mc-ava" id="mcAva"></span><span class="mc-nm" id="mcNm">CEO</span><i class="cn" id="chatN" hidden></i><em class="mc-chev" aria-hidden="true">︿</em></button>
        <select id="chatTo" class="mc-sel" aria-label="對誰說" hidden></select>
        <textarea id="chatText" rows="1" enterkeyhint="send" placeholder="對 CEO 說…" spellcheck="false" aria-label="要說的話"></textarea>
        <button class="btn on" id="chatSend" type="submit">送出</button>
      </form>
      <div class="c-row"><span id="chatCount" class="c-cnt" hidden>已輸入 0／${MAX_TEXT}</span></div>
      <p class="c-hint" id="chatHint">Enter 送出，Shift＋Enter 換行</p>
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
      if (silent && !ACTIVE.has(m.status)) K.seen.add(seenKey(m));        // 載入時就已完成的舊訊息：不當成「沒看過的新回覆」
      if (old && old.status === m.status) continue;
      const ev = { queued: 'cmd_queued', claimed: 'cmd_claimed', running: 'cmd_running', done: 'cmd_done', failed: 'cmd_failed', canceled: 'cmd_gone', expired: 'cmd_gone', stale: 'cmd_gone' }[m.status];
      // 載入時就已完成的舊指令不再慶祝一次（silent）；進行中的照樣演出
      if (ev && !(silent && !ACTIVE.has(m.status))) emit(ev, agentFor(toOf(m)), { mid: m.id, text: m.text, reply: m.reply, status: m.status });
    }
  }
  const activeCount = () => [...K.msgs.values()].filter(m => ACTIVE.has(m.status)).length;
  const toOf = m => m.to || 'ceo';
  const seenKey = m => m.id + '|' + m.status;      // 狀態變了（排隊中→完成）就算新的，收合時才會跳出「有新回覆」的提示
  // 一個聊天室＝一個單位（CEO 一間、每個部門一間）：對部門裡任何一位、或對整個部門說的話都進同一間（to 欄位仍是成員代號或 dept:<部門代號>）
  const threadOf = target => { const r = roomOfTo(target); return [...K.msgs.values()].filter(m => roomOfTo(toOf(m)) === r).sort((a, b) => a.created - b.created); };

  async function fetchInbox(manual) {
    if (K.inflight) { K.again = true; return; } K.inflight = true; K.polls++;
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
    } finally { K.inflight = false; render(); schedule(); if (K.again) { K.again = false; setTimeout(() => fetchInbox(), 0); } }
  }
  function schedule() {
    clearTimeout(K.timer);
    if (!tok() || K.mode === 'auth' || K.mode === 'forbidden' || K.mode === 'noinbox') return;       // 這幾種等使用者處理，不自己一直敲
    const act = activeCount() > 0; if (!K.open && !act) return;
    const ms = (act ? K.fastMs : K.pollMs) * (K.fails > 2 ? 4 : 1);      // 有進行中的指令＝2 秒；只是開著看＝5 秒；其餘不輪詢
    K.timer = setTimeout(() => { if (document.hidden) { schedule(); return; } fetchInbox(); }, ms);
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden && (K.open || activeCount())) fetchInbox(); });
  // 第一次碰對話框（聚焦輸入框／展開／送出）才開始跟收件服務與功能閘門對話
  function touch(noGate) {
    if (!K.touched) K.touched = true;
    if (!tok()) K.mode = 'nologin';
    else if (K.mode === 'idle' || K.mode === 'neterr') { K.mode = K.mode === 'idle' ? 'loading' : K.mode; fetchInbox(true); }
    if (W.gate && !noGate) W.gate.load().then(render);        // 送出時 W.gate.begin 自己會載入，這裡不重複
    render();
  }

  // ───────── 對象（誰）：名字、頭像 ─────────
  const isAgent = id => { const c = C(id); return !!c && !c.spec.pet && !c.spec.isCeo && !c.jobless; };
  const hasThread = id => [...K.msgs.values()].some(m => toOf(m) === id);
  // 部門與聊天室：聊天室代號 'ceo'｜'d:<部門代號>'（後備區 d:reserve、辦公室外的內建類型都歸 d:_ext「外部協助」）
  const live = m => !(W.hr && W.hr.isFired && W.hr.isFired(m.id));
  const deptList = () => (W.org && W.org.departments) || [];
  const deptOfMember = id => { const c = C(id); if (c && c.spec.isCeo) return 'ceo'; const mm = W.members && W.members.get && W.members.get(id); return (c && c.spec.dept) || (mm && mm.dept) || ''; };
  const deptInfo = did => { const d = deptList().find(q => q.id === did); if (d) return { id: did, name: d.name, color: d.color }; if (did === 'reserve') return { id: did, name: '後備區', color: '#b9aca2' }; return { id: '_ext', name: '外部協助', color: '#b9aca2' }; };
  const roomOfTo = to => { to = to || 'ceo'; if (to === 'ceo') return 'ceo'; if (/^dept:/.test(to)) return 'd:' + to.slice(5); const dp = deptOfMember(to); if (dp === 'ceo') return 'ceo'; return 'd:' + (dp && deptInfo(dp).id !== '_ext' ? dp : '_ext'); };
  const roomDept = r => r.slice(2);
  const membersOf = r => {
    const did = roomDept(r), d = deptList().find(q => q.id === did);
    if (d) return d.members.filter(live).map(m => m.id);
    const ids = new Set(); if (did === 'reserve') for (const id of W.chars.keys()) if (isAgent(id) && deptOfMember(id) === 'reserve') ids.add(id);
    for (const m of K.msgs.values()) { const t = toOf(m); if (roomOfTo(t) === r && !/^dept:/.test(t)) ids.add(t); } return [...ids];
  };
  const knownRoom = r => r === 'ceo' || deptList().some(q => 'd:' + q.id === r) || [...K.msgs.values()].some(m => roomOfTo(toOf(m)) === r) || (r === 'd:reserve' && membersOf(r).length > 0);
  const knownTo = id => id === 'ceo' || (/^dept:/.test(id) ? knownRoom('d:' + id.slice(5)) : (isAgent(id) || hasThread(id)));
  // 這個聊天室的「對整個部門」代表值（CEO 室＝ceo；外部協助沒有整體對象，用第一位）
  const roomTarget = r => r === 'ceo' ? 'ceo' : r === 'd:_ext' ? (membersOf(r)[0] || 'ceo') : 'dept:' + roomDept(r);
  // 這則指令真正要動的角色：成員本人；整個部門＝主管（沒有主管就第一位）
  const agentFor = to => { to = to || 'ceo'; if (/^dept:/.test(to)) { const d = deptList().find(q => q.id === to.slice(5)); const ms = d ? d.members.filter(live) : []; return (ms.find(m => m.lead) || ms[0] || { id: 'ceo' }).id; } return to; };
  // 對象一律顯示中文暱稱：名冊暱稱 → 內建類型的中文名（general-purpose＝通才）→ 都沒有才顯示代號；整個部門＝「設計部全體」
  const nickOf = id => { if (id === 'ceo') return 'CEO'; if (/^dept:/.test(id)) return deptInfo(id.slice(5)).name + '全體'; const c = C(id); if (c && !c.spec.pet) return c.spec.nick; const mm = W.members && W.members.get && W.members.get(id); return (mm && mm.nick) || BUILTIN_ZH[id] || id; };
  const roleOf = id => { if (id === 'ceo') return '分派工作'; if (/^dept:/.test(id)) return '整個部門'; const c = C(id); return c && c.spec.zh ? c.spec.zh : (BUILTIN_ZH[id] ? '外部協助' : ''); };
  const roomName = r => r === 'ceo' ? 'CEO' : deptInfo(roomDept(r)).name;
  const deptAva = did => { const i = deptInfo(did); return `<span class="da" style="background:${esc(i.color || '#b9aca2')}">${esc(i.name.slice(0, 1))}</span>`; };
  const avaOf = id => { if (/^dept:/.test(id)) return deptAva(id.slice(5)); const c = id === 'ceo' ? C('ceo') : C(id); if (c && ui.ava) { try { return ui.ava(c.spec); } catch (e) { /* 略 */ } } return '<div class="ava" style="background:#ffb057"></div>'; };
  const avaRoom = r => r === 'ceo' ? avaOf('ceo') : deptAva(roomDept(r));
  // 回覆裡的動作標記：【動作：轉圈】【動作：跳】【動作：揮手】…；網頁解析後讓那位角色在 3D 做出動作，標記本身不顯示
  const ACT_RE = /【\s*動作\s*[:：]\s*([^】]*)】/g;
  const ACT_MAP = { 轉圈: 'spin', 轉圈圈: 'spin', 旋轉: 'spin', 原地轉圈: 'spin', 跳: 'jump', 跳躍: 'jump', 跳一下: 'jump', 揮手: 'wave', 打招呼: 'wave', 點頭: 'nod', 搖頭: 'shake', 鼓掌: 'clap', 歡呼: 'cheer', 舉手: 'raise', 喝水: 'drink' };
  const clean = r => String(r == null ? '' : r).replace(ACT_RE, '').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  const actsOf = r => { const out = []; String(r || '').replace(ACT_RE, (_, g) => { for (const w of g.split(/[、,，\s+＋]+/)) if (ACT_MAP[w.trim()]) out.push(ACT_MAP[w.trim()]); return ''; }); return out.slice(0, 4); };
  K.actsOf = actsOf; K.clean = clean;

  // ───────── 視窗位置、鎖定、透明（記在 localStorage，重新整理後保留） ─────────
  const OPS = [1, .7, .4];
  function loadPref() {
    let o = null; try { o = JSON.parse(lsGet(LS_WIN) || 'null'); } catch (e) { o = null; }
    o = o && typeof o === 'object' ? o : {};
    K.pref = { pos: ['left', 'center', 'right', 'free'].includes(o.pos) ? o.pos : 'left', last: ['left', 'center', 'right'].includes(o.last) ? o.last : 'left', x: +o.x || 0, y: +o.y || 0, lock: !!o.lock, op: OPS.includes(+o.op) ? +o.op : 1 };
    if (K.pref.pos !== 'free') K.pref.last = K.pref.pos;
  }
  const savePref = () => lsSet(LS_WIN, JSON.stringify(K.pref));
  const desk = () => innerWidth > 640;
  const topLimit = () => { const b = $('bar'); const r = b ? b.getBoundingClientRect() : null; return Math.round(r && r.height ? r.bottom + 8 : 64); };       // 視窗不能蓋住頂列
  function applyPos() {
    const P = K.pref, eff = P.pos === 'free' ? P.last : P.pos, app = $('app');
    for (const k of ['left', 'center', 'right']) { pn.classList.toggle({ left: 'pl', center: 'pc', right: 'pr' }[k], eff === k); app.classList.toggle({ left: 'mc-pl', center: 'mc-pc', right: 'mc-pr' }[k], eff === k); }
    const free = P.pos === 'free' && K.open && desk();
    pn.classList.toggle('pf', free);
    if (free) { const r = pn.getBoundingClientRect(), w = r.width || 680, h = r.height || 480; P.x = Math.max(0, Math.min(P.x, innerWidth - w)); P.y = Math.max(topLimit(), Math.min(P.y, innerHeight - h)); pn.style.left = P.x + 'px'; pn.style.top = P.y + 'px'; }
    else { pn.style.left = ''; pn.style.top = ''; }
    pn.style.setProperty('--mc-op', String(P.op));
    pn.classList.toggle('locked', P.lock);
    const lk = $('mcLock'); lk.setAttribute('aria-pressed', String(P.lock)); lk.textContent = P.lock ? '已鎖定' : '鎖定'; lk.title = P.lock ? '按一下解除鎖定' : '鎖定視窗位置（鎖定後拖不動、也不能換位置）';
    $('mcOp').textContent = '透明 ' + Math.round(P.op * 100) + '%';
    for (const b of pn.querySelectorAll('[data-pos]')) { b.classList.toggle('on', P.pos === b.dataset.pos || (P.pos === 'free' && false)); b.disabled = P.lock; b.setAttribute('aria-pressed', String(P.pos === b.dataset.pos)); }
    avoid(); measure();
  }
  // 展開的視窗不能壓到資訊卡／佈告欄／群組（靠左）與紀錄欄（靠右）：能放得下就把它們平移到視窗旁邊，放不下就收起來（收合的輸入列另由 CSS 抬高）
  function avoid(final) {
    const open = K.open && desk() && pn.getBoundingClientRect().width > 0, p = open ? pn.getBoundingClientRect() : null;
    for (const [id, side] of [['card', 'left'], ['board', 'left'], ['grp', 'left'], ['log', 'right']]) {
      const e = $(id); if (!e) continue; e.style[side] = ''; if (e.hidden) continue; if (!p) continue;
      const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
      if (!(r.left < p.right && r.right > p.left && r.top < p.bottom && r.bottom > p.top)) continue;
      if (side === 'left') {
        if (p.right + 12 + r.width <= innerWidth - 12) e.style.left = Math.round(p.right + 12) + 'px';
        else if (p.left - 12 - r.width >= 8) e.style.left = Math.round(p.left - 12 - r.width) + 'px';
        else if (final) e.hidden = true;
      } else {
        if (p.left - 12 - r.width >= 8) e.style.right = Math.round(innerWidth - p.left + 12) + 'px';
        else if (p.right + 12 + r.width <= innerWidth - 8) e.style.right = Math.round(innerWidth - p.right - 12 - r.width) + 'px';
        else if (final) e.hidden = true;
      }
    }
  }
  let drag = null;
  $('mcHead').addEventListener('pointerdown', e => {
    if (!desk() || !K.open || K.pref.lock || e.button !== 0 || e.target.closest('button')) return;
    const r = pn.getBoundingClientRect(); drag = { dx: e.clientX - r.left, dy: e.clientY - r.top, id: e.pointerId };
    try { $('mcHead').setPointerCapture(e.pointerId); } catch (x) { /* 略 */ }
    pn.classList.add('dragging'); e.preventDefault();
  });
  $('mcHead').addEventListener('pointermove', e => { if (!drag) return; K.pref.pos = 'free'; K.pref.x = e.clientX - drag.dx; K.pref.y = e.clientY - drag.dy; applyPos(); });
  const endDrag = () => { if (!drag) return; drag = null; pn.classList.remove('dragging'); savePref(); avoid(true); };
  $('mcHead').addEventListener('pointerup', endDrag); $('mcHead').addEventListener('pointercancel', endDrag);
  pn.addEventListener('click', e => {
    const t = e.target.closest('button'); if (!t) return;
    if (t.dataset.pos && !K.pref.lock) { K.pref.pos = t.dataset.pos; K.pref.last = t.dataset.pos; K.pref.x = K.pref.y = 0; savePref(); applyPos(); avoid(true); }
    else if (t.id === 'mcLock') { K.pref.lock = !K.pref.lock; savePref(); applyPos(); }
    else if (t.id === 'mcOp') { K.pref.op = OPS[(OPS.indexOf(K.pref.op) + 1) % OPS.length]; savePref(); applyPos(); }
    else if (t.id === 'mcHelp') { const h = $('mcTip'); h.hidden = !h.hidden; t.setAttribute('aria-expanded', String(!h.hidden)); }
  });
  loadPref();

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
    return on ? '<i class="dot on"></i>Claude 在線' : '<i class="dot"></i><span title="訊息會排隊，下次開工作階段時才會被取走（最多保留 24 小時）">Claude 沒開，訊息會排隊</span>';
  }
  // 時間：同一天只寫時:分，不同天加日期
  const clock = ms => { const w = when(ms), t = when(Date.now()); return w.slice(0, 5) === t.slice(0, 5) ? w.slice(6) : w; };
  const minute = ms => Math.floor(ms / 60000);
  // 我這則的狀態小字（只放在我的最後一則底下；沒做成／沒人取走這類要明顯標出的，不管是不是最後一則都標）
  function stHtml(m, last) {
    const [lab, cls] = ST[m.status] || [m.status, 'x'];
    if (m.status === 'done') return '';
    if (!last && !ACTIVE.has(m.status) && m.status !== 'failed' && m.status !== 'expired' && m.status !== 'stale') return '';
    const ic = { sq: '<i class="ic-clock"></i>', sc: '<i class="ic-tick"></i>', sf: '<i class="ic-warn">!</i>', sw: '<i class="ic-warn">!</i>', sx: '' }[cls] || '';
    const again = ['failed', 'stale', 'expired'].includes(m.status) ? `<button class="c-again" type="button" data-again="${esc(m.id)}">重送</button>` : '';
    return `<div class="c-stl c-st ${cls}" data-s="${esc(m.status)}">${ic}<span>${esc(lab)}</span>${again}</div>`;
  }
  function msgHtml(m, prev, last) {
    const to = toOf(m), nk = esc(nickOf(to)), showTime = !prev || minute(prev.created) !== minute(m.created), inDept = roomOfTo(to) !== 'ceo';
    const rtx = clean(m.reply), reply = rtx ? linkify(rtx) : (m.status === 'done' ? '做完了。' : '');
    const typing = m.status === 'running' ? `<div class="c-rp c-typing" aria-label="${nk} 輸入中"><span class="c-av">${avaOf(to)}</span><div class="c-rb"><span class="c-dots"><i></i><i></i><i></i></span></div><small>${nk} 輸入中…</small></div>` : '';
    const more = m.status === 'queued' ? `<button class="c-more" type="button" data-menu="${esc(m.id)}" aria-label="更多" aria-haspopup="menu">⋯</button><div class="c-menu" role="menu" hidden><button type="button" role="menuitem" data-cancel="${esc(m.id)}">撤回</button></div>` : '';
    return `<article class="c-msg${showTime ? '' : ' same'}" data-id="${esc(m.id)}" data-st="${esc(m.status)}">
      ${showTime ? `<time class="c-tm">${esc(clock(m.created))}</time>` : ''}
      ${inDept ? `<span class="c-to">→ ${esc(/^dept:/.test(to) ? '整個部門' : nickOf(to))}</span>` : ''}
      <div class="c-mine"><div class="c-me${m.status === 'canceled' ? ' gone' : ''}"><p class="c-tx">${esc(m.text)}</p>${more}</div></div>
      ${stHtml(m, last)}
      ${typing}
      ${reply ? `<div class="c-rp"><span class="c-av">${avaOf(to)}</span><div class="c-rb"><b>${nk}${m.done_at || m.updated ? `<time>${esc(clock(m.done_at || m.updated))}</time>` : ''}</b><div>${reply}</div></div></div>` : ''}</article>`;
  }
  const unreadOf = id => threadOf(id).filter(m => (m.status === 'done' || m.status === 'failed') && !K.seen.has(seenKey(m))).length;
  // 左邊對話清單：一個單位一間聊天室（CEO、每個部門）；有說過話的依最後時間排前面，其餘照部門順序
  function roomIds() {
    const ids = ['ceo', ...deptList().map(d => 'd:' + d.id)], last = new Map();
    for (const m of K.msgs.values()) { const r = roomOfTo(toOf(m)); last.set(r, Math.max(last.get(r) || 0, m.created)); if (!ids.includes(r)) ids.push(r); }
    if (!ids.includes('d:reserve') && membersOf('d:reserve').length) ids.push('d:reserve');
    const rk = roomOfTo(K.to); if (!ids.includes(rk)) ids.push(rk);
    const head = ids.slice(0, 1), rest = ids.slice(1), orig = new Map(rest.map((r, i) => [r, i]));
    rest.sort((a, b) => (last.get(b) || 0) - (last.get(a) || 0) || orig.get(a) - orig.get(b));
    return head.concat(rest);
  }
  function stripHtml() {
    const rk = roomOfTo(K.to), row = r => {
      const tg = r === rk ? K.to : roomTarget(r), list = threadOf(tg), m = list[list.length - 1], un = r === rk && K.open && (desk() || K.view === 'thread') ? 0 : unreadOf(tg), act = list.filter(x => ACTIVE.has(x.status)).length;
      let pv = r === 'ceo' ? roleOf('ceo') : `${membersOf(r).length} 位成員`, tm = '';
      if (m) { const rt = clean(m.reply); pv = m.status === 'done' && rt ? short(rt.replace(/https?:\/\/\S+/g, '').trim() || '做完了', 22) : m.status === 'running' ? '輸入中…' : '你：' + short(m.text, 20); tm = clock(m.created); }
      return `<button class="mc-th${r === rk ? ' on' : ''}" type="button" role="tab" aria-selected="${r === rk}" data-th="${esc(r === rk ? K.to : roomTarget(r))}" data-room="${esc(r)}"><span class="mc-ava">${avaRoom(r)}</span><span class="mc-tb"><span class="mc-t1"><b>${esc(roomName(r))}</b><time>${esc(tm)}</time></span><span class="mc-t2"><span class="mc-pv">${esc(pv)}</span>${un ? `<i class="cn">${un}</i>` : act ? '<i class="mc-wait" title="進行中"></i>' : ''}</span></span></button>`;
    };
    return roomIds().map(row).join('');
  }
  function peekOf() {
    const list = threadOf(K.to), m = list[list.length - 1]; if (!m || K.open) return '';
    const unseen = !ACTIVE.has(m.status) && m.status !== 'canceled' && !K.seen.has(seenKey(m));
    if (!ACTIVE.has(m.status) && !unseen) return '';
    const [lab] = ST[m.status] || [m.status];
    const rt = clean(m.reply), nm = nickOf(toOf(m));
    return rt ? `${nm}：${short(rt.replace(/https?:\/\/\S+/g, '').trim() || '做完了', 40)}` : m.status === 'running' ? `${nm} 輸入中…` : `${lab}・${short(m.text, 26)}`;
  }
  function render() {
    // 目前對象不在了（被開除、改成寵物）→ 回到 CEO
    if (K.to !== 'ceo' && !knownTo(K.to) && W.chars.size) K.to = 'ceo';
    const n = activeCount(), bn = $('chatN'); bn.hidden = !n; bn.textContent = n || ''; lsSet(LS_ACTIVE, n ? '1' : null);
    btn.setAttribute('aria-label', (n ? `對話（${n} 則進行中）` : '對話') + `，目前對 ${nickOf(K.to)} 說`); btn.setAttribute('aria-expanded', String(K.open)); btn.classList.toggle('on', K.open);
    pn.classList.toggle('open', K.open); $('app').classList.toggle('mc-open', K.open); $('mcTop').hidden = !K.open;
    pn.classList.toggle('v-list', K.view === 'list'); pn.classList.toggle('v-thread', K.view === 'thread');
    // 對象：頭像＋名字＋輸入框提示
    const who = nickOf(K.to), av = avaOf(K.to);
    if ($('mcAva').dataset.k !== K.to + av.length) { $('mcAva').innerHTML = av; $('mcAva').dataset.k = K.to + av.length; }
    $('mcNm').textContent = who;
    tx.placeholder = /^dept:/.test(K.to) ? `對整個${deptInfo(K.to.slice(5)).name}說…` : `對 ${who} 說…`;
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
    const sh = stripHtml(), st = $('mcStrip'); if (st.dataset.h !== sh) { st.innerHTML = sh; st.dataset.h = sh; }
    const list = threadOf(K.to), mobList = !desk() && K.view === 'list';
    const rk = roomOfTo(K.to), isDept = rk !== 'ceo';
    $('mcWho').innerHTML = mobList ? '<span class="mc-nmx"><b>對話</b></span>' : `<span class="mc-ava">${avaRoom(rk)}</span><span class="mc-nmx"><b>${esc(roomName(rk))}</b><small>${esc(isDept ? membersOf(rk).length + ' 位成員・可對整個部門或指定一位說' : roleOf('ceo'))}</small></span>`;
    // 輸入框左邊的「對誰說」：只有部門聊天室才有（整個部門或某位成員）
    const sel = $('chatTo'), ops = isDept ? [...(rk === 'd:_ext' ? [] : [['dept:' + roomDept(rk), `整個部門（${membersOf(rk).length} 人）`]]), ...membersOf(rk).map(id => [id, nickOf(id) + (roleOf(id) ? '・' + roleOf(id) : '')])] : [];
    const oh = rk + '|' + ops.map(o => o.join(':')).join('|'); if (sel.dataset.h !== oh) { sel.innerHTML = ops.map(([v, t]) => `<option value="${esc(v)}">${esc(t)}</option>`).join(''); sel.dataset.h = oh; }
    sel.hidden = !isDept; if (isDept) sel.value = K.to;
    const lv = liveHtml(); if ($('chatLive').dataset.h !== lv) { $('chatLive').innerHTML = lv; $('chatLive').dataset.h = lv; }
    const box = $('chatList');
    const html = list.length ? list.map((m, i) => msgHtml(m, list[i - 1], i === list.length - 1)).join('') : (K.mode === 'ok' ? `<p class="c-empty">還沒有跟${esc(roomName(rk))}說過話。在下面打字，按 Enter 送出。</p>` : '');
    if (box.dataset.h !== html) { const stick = box.scrollHeight - box.scrollTop - box.clientHeight < 40 || box.dataset.t !== K.to; box.innerHTML = html; box.dataset.h = html; box.dataset.t = K.to; if (stick) box.scrollTop = box.scrollHeight; }
    if (desk() || K.view === 'thread') for (const m of list) K.seen.add(seenKey(m));
  }
  function grow() { tx.style.height = 'auto'; tx.style.height = Math.min(tx.scrollHeight, 104) + 'px'; }

  // 展開時：手機是全螢幕（先看清單、點進對話）；桌機是浮動視窗，擋到的面板由 avoid() 平移或收起
  function open(to, focus) {
    if (to) setTarget(to, true);
    touch(); K.open = true; K.err = '';
    if (!desk()) K.view = to ? 'thread' : (K.view || 'list');
    const box = $('chatList'); box.dataset.h = ''; applyPos(); render(); applyPos(); avoid(true); fetchInbox(true);
    if (focus !== false && (desk() || K.view === 'thread')) setTimeout(() => { try { tx.focus({ preventScroll: true }); } catch (e) { /* 略 */ } }, 30);
  }
  function close() { K.open = false; render(); applyPos(); schedule(); }
  function setTarget(id, quiet) {
    id = id || 'ceo'; if (C(id) && C(id).spec.isCeo) id = 'ceo'; if (id !== 'ceo' && !knownTo(id)) id = 'ceo';
    const ch = K.to !== id; K.to = id; K.err = ''; $('chatList').dataset.h = '';
    if (ch && !quiet) { btn.classList.remove('flash'); void btn.offsetWidth; btn.classList.add('flash'); }
    render();
  }
  K.openTo = (to) => open(to); K.close = close; K.setTarget = id => setTarget(id);
  btn.onclick = () => { if (K.open) close(); else { K.view = 'list'; open(null, false); } };       // 手機按下去先看清單
  $('chatX').onclick = () => { close(); try { btn.focus(); } catch (e) { /* 略 */ } };
  $('mcBack').onclick = () => { K.view = 'list'; render(); };
  $('chatPeek').onclick = () => { K.view = 'thread'; open(null, true); };
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
    touch(true); if (K.mode === 'loading') { K.busy = true; render(); while (K.inflight) await new Promise(r => setTimeout(r, 60)); K.busy = false; }
    if (K.mode !== 'ok') { render(); return; }
    K.busy = true; K.err = ''; render();
    const gt = W.gate ? await W.gate.begin('office.cmd') : null;           // 功能閘門：今天的次數用完就不送（說明由 render 顯示在對話框裡）
    if (gt && !gt.pass) { K.busy = false; render(); return; }
    const to = K.to, r = await call('', { method: 'POST', body: JSON.stringify({ to, text }) });
    K.busy = false; if (gt) { if (r.status === 200 && r.json.message) gt.done(); else gt.cancel(); }
    if (r.status === 200 && r.json.message) { tx.value = ''; grow(); merge([r.json.message]); K.rev = Math.max(K.rev, r.json.message.rev || 0); K.mode = 'ok'; schedule(); const box = $('chatList'); render(); box.scrollTop = box.scrollHeight; setTimeout(() => fetchInbox(), 0); }       // 送出後立刻讀一次（不等下一輪計時）：Claude 取走得快的話馬上看到「已送達」
    else if (r.status === 401) { K.mode = 'auth'; render(); }
    else if (r.status === 403) { K.mode = 'forbidden'; render(); }
    else if (r.status === 0 || r.status === -1) K.err = '連不上收件服務，訊息沒有送出，請稍後再試';
    else if (r.status === 404 || r.status === 501 || r.status === 503) { K.mode = 'noinbox'; render(); }
    else K.err = ERR[r.json.error] || ('送出失敗（' + r.status + '），請稍後再試');
    render();
  }
  $('chatForm').addEventListener('submit', e => { e.preventDefault(); send(); });
  $('chatTo').addEventListener('change', e => { setTarget(e.target.value, true); tx.focus(); });
  // 我的訊息的小選單：滑鼠停上去出現「⋯」，觸控長按也能叫出；目前只有「撤回」（還在傳送中才有）
  const closeMenus = except => { for (const m of pn.querySelectorAll('.c-menu')) if (m !== except) m.hidden = true; };
  let lp = 0;
  pn.addEventListener('pointerdown', e => {
    const me = e.target.closest('.c-me'); if (!me || e.pointerType === 'mouse') return;
    clearTimeout(lp); lp = setTimeout(() => { const mn = me.querySelector('.c-menu'); if (mn) { closeMenus(mn); mn.hidden = false; me.classList.add('menu'); } }, 520);
  });
  for (const ev of ['pointerup', 'pointercancel', 'pointermove']) pn.addEventListener(ev, e => { if (ev !== 'pointermove' || Math.abs(e.movementX) + Math.abs(e.movementY) > 6) clearTimeout(lp); });
  document.addEventListener('pointerdown', e => { if (!e.target.closest || !e.target.closest('.c-me')) { closeMenus(); for (const x of pn.querySelectorAll('.c-me.menu')) x.classList.remove('menu'); } }, true);
  pn.addEventListener('click', async e => {
    const t = e.target.closest('button'); if (!t) return;
    if (t.dataset.menu) { const mn = t.parentNode.querySelector('.c-menu'); closeMenus(mn); mn.hidden = !mn.hidden; return; }
    if (t.dataset.th) { setTarget(t.dataset.th, true); K.view = 'thread'; render(); if (!desk()) setTimeout(() => { try { tx.focus({ preventScroll: true }); } catch (x) { /* 略 */ } }, 30); return; }
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
    if (K.cardFor !== c.spec.id) { K.cardFor = c.spec.id; setTarget(c.spec.id, false); if (K.open && !desk()) K.view = 'thread'; }
    const cardEl = $('card'), acts = [...cardEl.querySelectorAll('.acts')].pop(); if (!acts || cardEl.querySelector('[data-chat]')) return;
    const b = document.createElement('button'); b.className = 'btn on'; b.type = 'button'; b.dataset.chat = c.spec.id; b.textContent = c.spec.isCeo ? '對 CEO 說' : '對他說';
    acts.append(b);
    if (K.open) requestAnimationFrame(() => avoid(true));          // 對話視窗開著時才跳出的資訊卡：放得下就平移到視窗旁，放不下就收起（對象已經切過去了）
  };
  try { new MutationObserver(() => { if ($('card').hidden) K.cardFor = null; }).observe($('card'), { attributes: true, attributeFilter: ['hidden'] }); } catch (e) { /* 略 */ }
  $('card').addEventListener('click', e => { const b = e.target.closest('[data-chat]'); if (!b) return; $('card').hidden = true; open(b.dataset.chat === 'ceo' || (C(b.dataset.chat) && C(b.dataset.chat).spec.isCeo) ? 'ceo' : b.dataset.chat, true); });

  // ───────── 量高度：讓其他底部元件（版本標記、運動場鈕、整修列、搖桿、緊急橫幅…）知道要讓出多少（--mc-h，chat.css 用） ─────────
  const root = document.documentElement;
  const measure = () => { if (pn.classList.contains('pf')) return; const h = $('mcDock').offsetHeight, b = parseFloat(getComputedStyle(pn).bottom) || 12; root.style.setProperty('--mc-h', (h ? h + b + 6 : 0) + 'px'); };      // 對話框底邊離畫面底的距離＋自己的高度＋6px 縫隙
  try { new ResizeObserver(measure).observe($('mcDock')); } catch (e) { /* 略 */ }
  addEventListener('resize', () => { applyPos(); measure(); }); applyPos(); measure();

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
  // 回覆的動作標記 → 3D 動作：轉圈＝原地轉一圈（沿用 mind.js 的 spin 走位）、跳＝原地跳一下（沿用 doAct('sig')）、其餘是角色的一次型動作
  function doAct(id, a) {
    const c = who(id); if (!c || c.piloted) return; K.acted = (K.acted || []).concat([id + ':' + a]).slice(-20);
    try {
      if (a === 'spin') { const mm = W.mind && W.mind.mindOf && W.mind.mindOf(id); if (mm && c.state === 'stand') mm.spin = { t0: W.time, h0: c.heading || 0, dur: 1.1 }; else c.setAction('cheer', { duration: 1.4 }); c.emote('star', 1.4); }
      else if (a === 'jump') { if (c.inner && c.inner.doAct && c.state === 'stand') c.inner.doAct('sig'); else c.setAction('cheer', { duration: 1.4 }); }
      else c.setAction(a, { duration: a === 'wave' ? 1.8 : undefined });
    } catch (e) { console.warn('動作標記例外', e); }
  }
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
      if (!failed) { if (wasRun && !c.spec.isCeo) setTimeout(cheer, 6500); else cheer(); }
      if (!failed) actsOf(d.reply).forEach((a, i) => setTimeout(() => doAct(id, a), (wasRun && !c.spec.isCeo ? 6900 : 400) + i * 1500));       // 回覆裡的【動作：…】標記   // 走去交件的人，等交件演出收尾再慶祝（不打斷）
      else { c.emote('cloud', 2.4); c.say(line, 4); }
      K.started.delete(d.mid);
      if (!(K.open && roomOfTo(K.to) === roomOfTo(K.msgs.has(d.mid) ? toOf(K.msgs.get(d.mid)) : id)) && ui.toast) ui.toast(failed ? `${c.spec.nick}沒做成：點對話框看回覆` : `${c.spec.nick}回覆了：點對話框看`);
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
