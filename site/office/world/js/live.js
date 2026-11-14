// 即時模式（2026-11-14，擁有者原話：「目前看起來還是 Demo 版本，我想實際串接我的專案」）
//
// 有接入碼（或擁有者用網站登入身分）時，每 15 秒讀一次 AI Office 收件端（workers/ai-office-bridge）的
// GET /v1/office/<id>/state，把「你的 Claude 真的發生的事」餵進同一個狀態層（state.emit），演出全部沿用 jobs.js／power.js：
//   · 每個工作階段一位 CEO：最近在動的那個是本尊，其他同時開著的在 CEO 桌旁當「分身」（最多 3 位，超過寫 +N）
//   · 子 Agent 類型對應到名冊上的同事；名冊沒有的類型（general-purpose、Explore…）自動坐進後備座位；座位滿了由現有同事兼任
//   · 派工 → 領任務 → 工具類別小動作 → 交件；等你核准／等你回答；回合結束；額度（有回報才顯示）
// 規矩：
//   · 收不到資料就寫「尚未收到回報」，不拿示範資料充數；資訊卡、績效總表、名牌字章在即時模式下只用真實事件算的數字，
//     資料不夠就寫「樣本不足」或「未評等」。示範資料改成可手動切換的「展示模式」。
//   · 分頁在背景時暫停讀取，回到前景立刻讀一次。
//   · 接入碼存在這台裝置的 localStorage（包 try/catch，私密視窗只在這次有效）；不放進網址列（#aio=… 會被讀走後立刻清掉）。
import { hhmm } from './state.js';

const LS = 'aiOffice.live.v1', ACCT_TOK = 'tw.acct.tok';
const POLL_MS = 15000;
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); return true; } catch (e) { return false; } };
const hash = s => { let h = 0; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };
// Claude Code 內建的子 Agent 類型 → 暱稱與物種（名冊裡沒有的類型才用得到）
const BUILTIN = { 'general-purpose': ['通才', 'bird'], Explore: ['探路', 'snail'], Plan: ['規劃', 'note'], 'statusline-setup': ['設定', 'robo'], 'claude-code-guide': ['導覽', 'bulb'], 'output-style-setup': ['樣式', 'pencil'] };
const POOL = ['bird', 'snail', 'robo', 'bulb', 'note', 'cloud', 'mug', 'star', 'seal', 'octo', 'folder', 'stamp'];
const STATE_CATS = new Set(['read', 'write', 'search', 'test', 'deploy', 'wait', 'other']);
const SESS_TEXT = { working: '工作中', idle: '待命中', ended: '已結束', error: '遇到錯誤' };
const isFail = s => /^(失敗|錯誤)[:：]/.test(s || '');
const EMPTY_BASE = { nDone: 0, nDoing: 0, nTodo: 0, list: [], eta: '未提供', etaMin: '—', opt: '', lastDone: '—', lastDoing: '—', nextTodo: '' };

function loadCfg() { try { const o = JSON.parse(lsGet(LS) || 'null'); return o && typeof o === 'object' ? o : {}; } catch (e) { return {}; } }

export function createLive(W, X) {
  const { state: S, ui, sim } = X, R = X.rewards || W.rewards, qs = new URLSearchParams(location.search);
  const L = { mode: 'demo', status: 'off', cfg: loadCfg(), seq: 0, pollMs: Math.max(500, +qs.get('live_poll') || POLL_MS), polls: 0, timer: 0, inflight: false, data: null, lastOk: 0, fails: 0,
    project: null, primary: null, clones: [], typeMap: new Map(), extras: new Map(), seen: new Set(), sharedNoted: new Set(), revealCode: null, msg: '', lastQuota: '', url: '' };
  W.live = L;
  const save = () => lsSet(LS, JSON.stringify(L.cfg));
  const emit = (name, o = {}) => S.emit({ hook_event_name: name, live: true, ...o });
  const C = id => W.chars.get(id);

  // 網址 #aio=<接入碼>：讀走、存起來、立刻從網址列清掉（不留在瀏覽紀錄）
  { const m = /(?:^#|&)aio=([A-Za-z0-9_-]{8,200})/.exec(location.hash || ''); if (m) { L.cfg.code = m[1]; L.cfg.office = L.cfg.office || 'main'; delete L.cfg.show; save(); try { history.replaceState(null, '', location.pathname + location.search); } catch (e) { /* 略 */ } } }
  if (qs.get('aio_url')) { L.cfg.url = qs.get('aio_url').replace(/\/+$/, ''); save(); }

  // ───────── 收件端網址：設定 → 從會員 API 網址推（tw-account. → tw-ai-office-bridge.） ─────────
  function loadScript(src) { return new Promise(res => { const s = document.createElement('script'); s.src = src; s.onload = s.onerror = () => res(); setTimeout(res, 4000); document.head.append(s); }); }
  async function resolveUrl() {
    if (L.cfg.url) return L.cfg.url;
    if (L.url) return L.url;
    if (!window.TW_ACCOUNT) await loadScript('../account_config.js');
    const api = window.TW_ACCOUNT && window.TW_ACCOUNT.api;
    if (api && /\/\/tw-account\./.test(api)) L.url = api.replace('//tw-account.', '//tw-ai-office-bridge.').replace(/\/+$/, '');
    return L.url;
  }
  const loginTok = () => lsGet(ACCT_TOK);
  function authHeaders() {
    if (L.cfg.code) return { Authorization: 'Bearer ' + L.cfg.code };
    const t = loginTok(); if (L.cfg.login && t) return { 'X-AIO-Session': t };
    return null;
  }
  const hasCred = () => !!(L.cfg.code || (L.cfg.login && loginTok()));

  // ───────── 樣式（只加新檔，不動既有 css） ─────────
  const css = document.createElement('style'); css.id = 'aioCss';
  css.textContent = `
.btn.aio-b{gap:6px}.btn.aio-b i.dot{width:8px;height:8px;border-radius:50%;background:#b9aca2;flex:none}
.btn.aio-b.live i.dot{background:#35b36b;box-shadow:0 0 0 3px rgba(53,179,107,.18)}.btn.aio-b.warn i.dot{background:#f2a93b}.btn.aio-b.bad i.dot{background:#c2590c}
.btn.aio-b.demo{color:var(--sub)}.btn.aio-b .s{display:none}
.aio-pop{width:340px;line-height:1.55;font-size:14px}.aio-pop h4{font-size:15px;color:var(--ink);margin:2px 4px 6px}
.aio-pop p{margin:4px 4px 8px;font-size:13px;color:var(--sub)}.aio-pop .st{color:var(--ink);font-weight:700}
.aio-pop .row{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 10px}.aio-pop .row .btn{box-shadow:none;border:1px solid var(--line);height:34px;padding:0 12px}
.aio-pop .row .btn.on{background:var(--on);border-color:var(--on);color:#fff}
.aio-pop input,.aio-pop select{font:inherit;font-size:14px;border:1px solid var(--line);border-radius:12px;padding:6px 10px;background:#fff;min-width:0;flex:1}
.aio-pop label{display:block;font-size:12px;color:var(--sub);margin:6px 4px 2px}
.aio-pop ul{list-style:none;margin:4px 0 8px;padding:0}.aio-pop li{display:flex;gap:6px;align-items:baseline;padding:5px 4px;border-bottom:1px solid var(--line);font-size:13px}
.aio-pop li b{flex:none}.aio-pop li span{flex:1;min-width:0;color:var(--sub);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.aio-pop li em{font-style:normal;font-size:12px;color:var(--sub)}
.aio-code{display:flex;gap:6px;align-items:center;background:var(--on2);border-radius:12px;padding:8px;margin:4px 0 6px}
.aio-code code{flex:1;min-width:0;word-break:break-all;font-size:12.5px}
.aio-pop details summary{cursor:pointer;font-size:13px;color:var(--sub);margin:4px}
#aioLedger{right:12px;top:64px;width:min(760px,calc(100vw - 24px));z-index:22}
#aioLedger h3{margin:0 0 6px;font-size:16px;display:flex;align-items:center;gap:8px;padding-right:36px;flex-wrap:wrap}
#aioLedger .chip2{font-size:12px;font-weight:600;color:var(--sub);background:var(--on2);border-radius:999px;padding:2px 8px}
#aioLedger table{width:100%;border-collapse:collapse;font-size:13px}#aioLedger th,#aioLedger td{padding:6px 6px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
#aioLedger th:first-child,#aioLedger td:first-child{text-align:left;white-space:normal}#aioLedger th{color:var(--sub);font-weight:600;font-size:12px}
#aioLedger .na{color:var(--sub);font-size:12px}#aioLedger .help{font-size:12px;color:var(--sub);margin:6px 0 0}
#aioLedger .empty{padding:18px 4px;color:var(--sub);font-size:14px}#aioLedger .ceo{margin:2px 0 8px;font-size:13px;background:var(--on2);border-radius:12px;padding:6px 10px}
.rw.aio-rw{font-size:13px;line-height:1.6}.rw.aio-rw b{font-size:13px}.rw.aio-rw .na{color:var(--sub)}
body.aio-live :is(#demoBtn,#simBtn,#rwTip){display:none!important}
@media (max-width:640px){
  #bar #aioBadge{order:3}.btn.aio-b .l{display:none}.btn.aio-b .s{display:inline}
  .aio-pop{width:auto}
  #aioLedger{left:8px!important;right:8px!important;width:auto;top:auto!important;bottom:8px!important;max-height:56dvh}
  #aioLedger thead{display:none}#aioLedger tr{display:grid;grid-template-columns:1fr 1fr 1fr;gap:2px 8px;padding:6px 0;border-bottom:1px solid var(--line)}
  #aioLedger td{border:0;padding:1px 0;text-align:left;white-space:normal}#aioLedger td:first-child{grid-column:1/-1;font-weight:700}
  #aioLedger td[data-l]:before{content:attr(data-l) " ";color:var(--sub);font-size:11px}
}`;
  document.head.append(css);

  // ───────── 頂列標章＋說明框 ─────────
  const bar = $('bar'), badge = document.createElement('button'); badge.className = 'btn aio-b demo'; badge.id = 'aioBadge'; badge.setAttribute('aria-haspopup', 'dialog'); badge.setAttribute('aria-expanded', 'false');
  bar.insertBefore(badge, $('pwBtn') || $('editBtn'));
  const pop = document.createElement('div'); pop.className = 'pop aio-pop'; pop.id = 'aioPop'; pop.hidden = true; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', '連接我的 Claude'); $('app').append(pop);
  const placePop = () => { const r = badge.getBoundingClientRect(), w = pop.offsetWidth; pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px'; };
  badge.onclick = () => { const was = pop.hidden; ui.closePops && ui.closePops(); closeLedger(); pop.hidden = !was; badge.setAttribute('aria-expanded', String(was)); if (was) { renderPop(); placePop(); } };
  document.addEventListener('pointerdown', e => { if (!pop.hidden && !e.target.closest('#aioPop') && !e.target.closest('#aioBadge')) { pop.hidden = true; badge.setAttribute('aria-expanded', 'false'); } });
  addEventListener('resize', () => { if (!pop.hidden) placePop(); });

  function badgeState() {
    if (L.mode !== 'live') return hasCred() && L.cfg.show ? ['展示模式', 'demo', '展示模式：目前顯示示範資料，點這裡回到即時', '展示模式'] : ['連接我的 Claude', 'demo', '目前是示範資料：點這裡連接你的 Claude', '連接 Claude'];
    switch (L.status) {
      case 'ok': return [`即時・最後更新 ${hhmm(L.lastOk)}`, 'live', '即時：資料來自你的 Claude', `即時 ${hhmm(L.lastOk)}`];
      case 'nodata': return ['即時・尚未收到回報', 'live warn', '已連上，但還沒收到你的 Claude 送來的任何消息', '尚未收到回報'];
      case 'error': return ['即時・連不上，重試中', 'live bad', '辦公室暫時連不上收件端，正在重試', '連不上'];
      case 'auth': return ['接入碼失效', 'live bad', '這組接入碼失效了，請重新取得', '接入碼失效'];
      case 'setup': return ['即時・尚未設定', 'live warn', '還缺收件端網址或接入碼', '尚未設定'];
      default: return ['即時・連線中…', 'live', '正在連線', '連線中'];
    }
  }
  function render() {
    const [t, cls, aria, ts] = badgeState();
    badge.className = 'btn aio-b ' + cls; badge.innerHTML = `<i class="dot" aria-hidden="true"></i><span id="aioTxt" class="l">${esc(t)}</span><span class="s" aria-hidden="true">${esc(ts)}</span>`; badge.setAttribute('aria-label', aria); badge.title = aria;
    document.body.classList.toggle('aio-live', L.mode === 'live');
    if (!pop.hidden) { renderPop(); placePop(); }
    if (ledgerEl && !ledgerEl.hidden) renderLedger();
  }
  L.render = render;

  // 說明框內容：示範時＝「連接我的 Claude」；即時＝狀態、專案、工作階段、展示模式、中斷連接
  function sessionsOfProject() { const d = L.data; return d ? d.sessions.filter(s => !L.project || s.project_hash === L.project) : []; }
  function renderPop() {
    const owner = !!loginTok(), d = L.data;
    let h = '';
    if (L.revealCode) h += `<h4>你的接入碼（只顯示這一次）</h4><div class="aio-code"><code id="aioCode">${esc(L.revealCode)}</code><button class="btn" data-a="copy">複製</button></div><p>雲端環境的「網路金鑰」值填這一組（前綴 Bearer）；本機外掛填在設定檔。關掉這個框之後就看不到了，弄丟可以再產生一組新的（舊的會失效）。</p>`;
    if (L.mode === 'live') {
      const [t] = badgeState();
      h += `<h4>即時模式</h4><p class="st" id="aioSt">${esc(t)}</p>`;
      if (L.status === 'nodata') h += '<p>還沒收到你的 Claude 送來的消息。在 Claude 開一個工作（例如請它派一位子 Agent 做件小事），15 秒內這裡會更新。</p>';
      if (L.status === 'auth') h += '<p>收件端不認得這組接入碼（可能已換新）。請重新產生或重新輸入。</p>';
      if (L.status === 'error') h += `<p>連不上收件端（${esc(L.msg || '網路問題')}）。會自動重試，間隔越來越長。</p>`;
      if (L.status === 'setup') h += '<p>還缺收件端網址或接入碼，請到下方「進階」填寫，或先中斷連接重新設定。</p>';
      if (d && d.last_event_at) h += `<p>最後一次收到消息：${hhmm(d.last_event_at)}（台北）・共 ${d.total_events} 筆</p>`;
      if (d && d.projects.length) {
        h += d.projects.length > 1 ? `<label for="aioProj">專案</label><div class="row"><select id="aioProj">${d.projects.map(p => `<option value="${esc(p.hash)}" ${p.hash === L.project ? 'selected' : ''}>${esc(p.name || '未命名專案')}</option>`).join('')}</select></div>` : `<p>專案：<b>${esc(d.projects[0].name || '未命名專案')}</b></p>`;
        const ss = sessionsOfProject();
        if (ss.length) {
          const ci = new Map(L.clones.map((c, i) => [c.sid, i]));
          h += `<ul aria-label="工作階段">${ss.slice(0, 8).map(s => { const who = s.id === L.primary ? 'CEO' : ci.has(s.id) ? `CEO（分身 ${ci.get(s.id) + 2}）` : 'CEO'; const st = s.ended ? '已結束' : s.flag === 'permission' ? '等你核准' : s.flag === 'question' ? '等你回答' : SESS_TEXT[s.state] || '待命中'; return `<li><b>${who}</b><span>${esc(st)}・${s.cloud ? '雲端' : s.cloud === false ? '本機' : ''}</span><em>${hhmm(s.last)}</em></li>`; }).join('')}</ul>`;
          if (L.more) h += `<p>另外還有 ${L.more} 個工作階段同時開著（畫面最多放 3 位分身）。</p>`;
        }
      }
      h += `<div class="row"><button class="btn" data-a="now">立即更新</button><button class="btn" data-a="show">展示模式</button><button class="btn" data-a="off">中斷連接</button></div>`;
      h += `<details><summary>進階</summary><label for="aioUrl">收件端網址</label><div class="row"><input id="aioUrl" value="${esc(L.cfg.url || L.url || '')}" placeholder="https://tw-ai-office-bridge.….workers.dev"><button class="btn" data-a="url">儲存</button></div>${owner ? '<div class="row"><button class="btn" data-a="rotate">產生新的接入碼（舊的會失效）</button><button class="btn" data-a="wipe">刪除所有紀錄</button></div>' : ''}</details>`;
    } else {
      h += `<h4>連接我的 Claude</h4><p>接好之後，辦公室顯示的是你自己的 Claude 真正在做的事；現在看到的是示範資料。</p>`;
      if (hasCred() && L.cfg.show) h += `<div class="row"><button class="btn on" data-a="back">回到即時模式</button></div>`;
      h += owner ? `<label>擁有者：產生一組接入碼</label><div class="row"><button class="btn on" data-a="claim">產生接入碼</button><button class="btn" data-a="login">直接用登入身分觀看</button></div>`
        : `<p>擁有者請先回<a href="../index.html">網站首頁</a>右上角用 Google 登入，再回到這裡按「產生接入碼」。</p>`;
      h += `<label for="aioIn">已經有接入碼</label><div class="row"><input id="aioIn" autocomplete="off" spellcheck="false" placeholder="aio_…"><button class="btn" data-a="code">連接</button></div>`;
      h += `<details><summary>進階</summary><label for="aioUrl">收件端網址（通常不用填）</label><div class="row"><input id="aioUrl" value="${esc(L.cfg.url || L.url || '')}" placeholder="https://tw-ai-office-bridge.….workers.dev"><button class="btn" data-a="url">儲存</button></div></details>`;
    }
    if (L.msg2) h += `<p class="st" role="status">${esc(L.msg2)}</p>`;
    if (h !== pop._html) { pop._html = h; pop.innerHTML = h; }
  }
  pop.addEventListener('change', e => { if (e.target.id === 'aioProj') { L.cfg.project = e.target.value; save(); restartLive(); } });
  pop.addEventListener('click', async e => {
    const b = e.target.closest('[data-a]'); if (!b) return; const a = b.dataset.a; L.msg2 = '';
    if (a === 'copy') { try { await navigator.clipboard.writeText(L.revealCode); L.msg2 = '已複製'; } catch (x) { const r = document.createRange(); r.selectNodeContents($('aioCode')); const s = getSelection(); s.removeAllRanges(); s.addRange(r); L.msg2 = '請按 Ctrl+C（手機長按）複製'; } renderPop(); return; }
    if (a === 'code') { const v = ($('aioIn').value || '').trim(); if (!/^[A-Za-z0-9_-]{8,200}$/.test(v)) { L.msg2 = '接入碼格式不對（應該是 aio_ 開頭的一串英數字）'; renderPop(); return; } L.cfg = { ...L.cfg, code: v, office: 'main', login: false }; delete L.cfg.show; save(); enterLive(); return; }
    if (a === 'login') { L.cfg = { ...L.cfg, login: true, office: 'main' }; delete L.cfg.code; delete L.cfg.show; save(); enterLive(); return; }
    if (a === 'url') { const v = ($('aioUrl').value || '').trim().replace(/\/+$/, ''); if (v && !/^https?:\/\/[^\s]+$/.test(v)) { L.msg2 = '網址格式不對'; renderPop(); return; } if (v) L.cfg.url = v; else delete L.cfg.url; save(); L.msg2 = '已儲存'; if (L.mode === 'live') restartLive(); else renderPop(); return; }
    if (a === 'claim' || a === 'rotate') { await claim(a === 'rotate'); return; }
    if (a === 'wipe') { if (!confirm('要刪除這間辦公室收到的所有紀錄嗎？（接入碼保留）')) return; await wipe(); return; }
    if (a === 'now') { poll(); return; }
    if (a === 'show') { L.cfg.show = true; save(); enterDemo(); return; }
    if (a === 'back') { delete L.cfg.show; save(); enterLive(); return; }
    if (a === 'off') { L.cfg = {}; save(); L.revealCode = null; enterDemo(); return; }
  });

  async function claim(rotate) {
    const url = await resolveUrl(), t = loginTok();
    if (!url) { L.msg2 = '還不知道收件端網址：請到「進階」填寫'; renderPop(); return; }
    try {
      const r = await fetch(url + '/v1/claim', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ t, rotate: !!rotate }), credentials: 'omit' });
      const j = await r.json().catch(() => ({}));
      if (r.status === 403) { L.msg2 = j.error === 'not_owner' ? '這個帳號不是辦公室擁有者，不能產生接入碼' : '這個網站沒有被允許'; renderPop(); return; }
      if (r.status === 503) { L.msg2 = '會員登入服務還沒接上收件端，暫時不能產生接入碼'; renderPop(); return; }
      if (!r.ok) { L.msg2 = '產生失敗（' + r.status + '），請稍後再試'; renderPop(); return; }
      if (j.exists && !j.code) { L.msg2 = '已經產生過接入碼。要換新的請按下面的「產生新的接入碼」（舊的會失效）'; L.cfg = { ...L.cfg, login: true, office: j.office || 'main' }; delete L.cfg.show; save(); enterLive(); return; }
      L.revealCode = j.code; L.cfg = { ...L.cfg, code: j.code, office: j.office || 'main', login: false }; delete L.cfg.show; save();
      if (L.mode === 'live') restartLive(); else enterLive();
    } catch (x) { L.msg2 = '連不上收件端，請稍後再試'; renderPop(); }
  }
  async function wipe() {
    const url = await resolveUrl();
    try { const r = await fetch(`${url}/v1/office/${encodeURIComponent(L.cfg.office || 'main')}/wipe`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ t: loginTok() }), credentials: 'omit' }); L.msg2 = r.ok ? '已刪除所有紀錄' : '刪除失敗（' + r.status + '）'; if (r.ok) restartLive(); else renderPop(); }
    catch (x) { L.msg2 = '連不上收件端'; renderPop(); }
  }

  // ───────── 示範資料的開關：即時模式下把示範數字全部換掉 ─────────
  const rwBtn = $('rwBtn');
  const orig = { showCard: ui.showCard, adjust: W.hr && W.hr.adjust, rwClick: rwBtn && rwBtn.onclick, rwHidden: rwBtn && rwBtn.hidden,
    gradeOf: R && R.gradeOf, cardBlock: R && R.cardBlock, openLedger: R && R.openLedger };
  function patchCard() {
    const m = document.querySelector('#card .meta'); if (!m) return;
    m.innerHTML = '<dt>資料來源</dt><dd>即時：你的 Claude 回報的事件</dd><dt>預估完成</dt><dd>未提供（即時模式不推估）</dd>';
  }
  function patchDemo(on) {
    if (on) {
      if (R && R.on) { R.gradeOf = () => null; R.cardBlock = liveCardBlock; R.openLedger = () => openLedger(); if (R.refreshTags) R.refreshTags(); if (R.marks) R.marks.visible = false; if (R.ledger && R.ledger.close) R.ledger.close(); }
      if (W.hr && orig.adjust) W.hr.adjust = (spec, base) => orig.adjust(spec, { ...EMPTY_BASE, list: [] });
      ui.showCard = c => { orig.showCard(c); patchCard(c); };
      if (rwBtn) { rwBtn.hidden = false; rwBtn.onclick = () => (ledgerEl && !ledgerEl.hidden ? closeLedger() : openLedger()); }
    } else {
      if (R && R.on) { R.gradeOf = orig.gradeOf; R.cardBlock = orig.cardBlock; R.openLedger = orig.openLedger; if (R.refreshTags) R.refreshTags(); if (R.marks) R.marks.visible = true; }
      if (W.hr && orig.adjust) W.hr.adjust = orig.adjust;
      ui.showCard = orig.showCard;
      if (rwBtn) { rwBtn.onclick = orig.rwClick; rwBtn.hidden = orig.rwHidden; }
      closeLedger();
    }
    if (ui.refreshCard) ui.refreshCard();
  }

  // ───────── 狀態層歸零（切換模式時，不讓示範的狀態混進真資料，反之亦然） ─────────
  function resetState() {
    if (S.q.exhausted) S.emit({ hook_event_name: 'QuotaRecovered', source: 'reset' });
    Object.assign(S.q, { five: null, week: null, provided: false, exhausted: false, resetsAt: null, asOf: null });
    S.agents.clear(); S.byAgentId.clear(); S.flags.permission = null; S.flags.question = null; S.seen.clear(); S.log.length = 0;
    Object.assign(S.session, { active: false, startedAt: null, lastEventAt: null, hadEvent: false, forcedUnknown: false }); S.signal = 'ok';
    if (W.power && W.power.refresh) W.power.refresh(true);
    if (W.jobs && W.jobs.flagsChanged) W.jobs.flagsChanged();
    if (W.jobs && W.jobs.statusSync) W.jobs.statusSync();
    L.seq = 0; L.seen.clear(); L.primary = null; L.data = null; L.lastQuota = ''; L.more = 0;
    for (const c of L.clones) c.ch.setVisible(false); L.clones.forEach(c => { c.sid = null; });
  }

  // ───────── 子 Agent 類型 → 同事 ─────────
  function memberFor(type) {
    if (!type) return null;
    if (L.typeMap.has(type)) return L.typeMap.get(type);
    const c = C(type);
    if (c && !c.spec.isCeo && !c.spec.pet) { L.typeMap.set(type, type); return type; }
    const id = ensureExtra(type);
    if (!id && !L.sharedNoted.has(type)) { L.sharedNoted.add(type); S.say(`座位已滿：「${short(type, 20)}」先由現有同事兼任`); }
    L.typeMap.set(type, id || type); return id || type;
  }
  function ensureExtra(type) {
    const id = 'x-' + String(type).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);
    if (C(id)) return id;
    const spot = W.spots.find(q => q.name === 'reserve' && !q.taken);
    if (!spot || !W.addExtra) return null;
    const h = hash(type), [nick, species] = BUILTIN[type] || [short(type.replace(/[-_]+/g, ' '), 8), POOL[h % POOL.length]];
    let c; try { c = W.addExtra({ id, nick, zh: type, dept: 'reserve', species, pal: h % 4, hue: 0, acc: ['badge'], accColor: '#ffd28a' }); } catch (e) { console.warn('新增後備同事失敗', e); return null; }
    W.extras.splice(W.extras.indexOf(c), 1); W.chars.set(id, c);
    W.members.set(id, { id, nick, zh: type, dept: 'reserve', deptName: '後備區（自動新增）' });
    c.busy = false; spot.taken = id; c.spot = spot; c.homeSpot = spot;
    if (spot.seat) { c.sitAt(spot.seat, { instant: true }); c.atDesk = true; c.setAction('type'); c.workAt = W.time + 3; }
    L.extras.set(type, id); S.say(`新同事報到：${nick}（${short(type, 24)}，坐後備座位）`); c.emote && c.emote('star', 2);
    return id;
  }
  const typeLabel = t => (BUILTIN[t] ? BUILTIN[t][0] : (W.members.get(t) || {}).nick || t);

  // ───────── 多個工作階段：本尊＋分身 ─────────
  function clonePlace(i) {
    const s = W.spots.find(q => q.name === 'seat:ceo') || { x: 4, z: 5 }, off = [[-1.7, 1.5], [1.7, 1.5], [0, 2.4]][i] || [0, 2.4];
    const f = W.nav && W.nav.nearestFree ? W.nav.nearestFree(s.x + off[0], s.z + off[1], 14) : null; return f || { x: s.x + off[0], z: s.z + off[1] };
  }
  function syncSessions() {
    const ss = sessionsOfProject(), now = Date.now();
    const active = ss.filter(s => !s.ended && now - (s.last || 0) < 6 * 3600e3);
    // 本尊：原本那位還開著就留著；否則換成最近在動的那個
    const cur = ss.find(s => s.id === L.primary);
    if (!cur || (cur.ended && active.length)) {
      const nxt = active[0] || ss[0];
      if (nxt && nxt.id !== L.primary) { L.primary = nxt.id; if (!nxt.ended) emit('SessionStart', { uid: 'ss:' + nxt.id, ts: nxt.last || now, session_id: nxt.id }); }
    }
    const others = active.filter(s => s.id !== L.primary);
    L.more = Math.max(0, others.length - 3);
    for (let i = 0; i < 3; i++) {
      const s = others[i];
      let cl = L.clones[i];
      if (!s) { if (cl) { cl.ch.setVisible(false); cl.sid = null; } continue; }
      if (!cl && W.addExtra) {
        const base = (W.roster && W.roster.base && W.roster.base.ceo) || {};
        try { const ch = W.addExtra({ ...base, id: 'ceo-clone-' + (i + 2), nick: `CEO（分身 ${i + 2}）`, zh: '同時開著的工作階段', pet: false }); cl = L.clones[i] = { ch, sid: null }; } catch (e) { console.warn('分身建立失敗', e); continue; }
      }
      if (!cl) continue;
      if (cl.sid !== s.id) { const p = clonePlace(i); cl.ch.setVisible(true); cl.ch.standAt(p.x, p.z, Math.PI); cl.ch.setAction('tablet'); cl.sid = s.id; }
      if (s.flag === 'permission' && !cl.ch.emoteSym) cl.ch.emote('shield', 2.4);
      else if (s.flag === 'question' && !cl.ch.emoteSym) cl.ch.emote('question', 2.4);
    }
  }

  // ───────── 事件 → 狀態層 ─────────
  function sessOf(sid) { return L.data && L.data.sessions.find(s => s.id === sid); }
  function agentOf(aid) { return L.data && L.data.agents.find(a => a.agent_id === aid); }
  function startAgent(aid, type, desc, uid, tool) {
    const mid = memberFor(type);
    emit('SubagentStart', { uid, agent_id: aid, agent_type: mid || type, description: desc || typeLabel(type) + ' 的任務', ...(tool && STATE_CATS.has(tool) ? { tool_category: tool } : {}) });
  }
  function applyEvent(e) {
    if (L.seen.has(e.seq)) return; L.seen.add(e.seq);
    const ph = e.project_hash || (sessOf(e.session_id) || {}).project_hash;
    if (L.project && ph && ph !== L.project) return;
    const uid = 'e:' + e.seq, ts = e.rcv || Date.now(), sid = e.session_id, cat = e.tool_category;
    const clearFlags = () => { if (S.flags.permission || S.flags.question) emit('NotificationClear', { uid: uid + ':c', ts }); };
    switch (e.event) {
      case 'SessionStart': if (!L.primary || sid === L.primary || (sessOf(L.primary) || {}).ended) { L.primary = sid; emit('SessionStart', { uid, ts, session_id: sid }); } break;
      case 'SessionEnd': if (sid === L.primary) emit('SessionEnd', { uid, ts, session_id: sid }); break;
      case 'UserPromptSubmit': if (!e.prompt_is_system) emit('UserPromptSubmit', { uid, ts, session_id: sid }); break;
      case 'PreToolUse':
        if (cat === 'dispatch') break;
        if (cat === 'ask') { emit('Notification', { uid, ts, notification_type: 'elicitation_dialog' }); break; }
        clearFlags();
        if (e.agent_id && !S.byAgentId.has(e.agent_id)) { const a = agentOf(e.agent_id); if (!a || a.status === 'running') startAgent(e.agent_id, e.agent_type || (a && a.agent_type), a && a.description, uid + ':s', cat); }
        emit('PreToolUse', { uid, ts, tool_category: STATE_CATS.has(cat) ? cat : 'other', ...(e.agent_id ? { agent_id: e.agent_id } : {}) });
        break;
      case 'PostToolUse': if (cat === 'answered') emit('NotificationClear', { uid, ts, kinds: ['question'] }); break;
      case 'SubagentStart': { const a = agentOf(e.agent_id); startAgent(e.agent_id, e.agent_type, (a && a.description) || e.description, uid); break; }
      case 'SubagentStop': {
        const mid = memberFor(e.agent_type), a = agentOf(e.agent_id);
        if (!S.byAgentId.has(e.agent_id)) startAgent(e.agent_id, e.agent_type, a && a.description, uid + ':s');
        emit('SubagentStop', { uid, ts, agent_id: e.agent_id, agent_type: mid || e.agent_type, status: isFail(e.summary) ? 'failed' : 'completed', last_assistant_message: e.summary || '做完了' });
        break;
      }
      case 'PermissionRequest': emit('Notification', { uid, ts, notification_type: 'permission_prompt', category: e.perm_category || 'other' }); break;
      case 'Notification':
        if (e.notification_type === 'permission_prompt') emit('Notification', { uid, ts, notification_type: 'permission_prompt', category: 'other' });
        else if (e.notification_type === 'elicitation_dialog') emit('Notification', { uid, ts, notification_type: 'elicitation_dialog' });
        break;
      case 'Stop': {
        clearFlags();
        if (sid === L.primary || !L.primary) { S.say('CEO 做完了，輪到你' + (e.summary ? '：' + short(e.summary, 30) : '')); const ceo = C('ceo'); if (ceo && !ceo.piloted && !ceo.sleeping) ceo.emote('star', 1.2); }
        break;
      }
      case 'StopFailure':
        if (/rate|limit|quota|usage|overload|billing/i.test(e.error_type || '')) emit('rate_limit_event', { uid, ts, status: 'rejected' });
        else S.say('CEO 遇到錯誤，這一輪先停下來');
        break;
      case 'PreCompact': S.say('CEO 整理了一下記憶'); break;
    }
  }
  function applySnapshot(j) {
    const inP = x => !L.project || x.project_hash === L.project;
    syncSessions();
    const p = sessOf(L.primary);
    if (p && !p.ended) { if (p.flag === 'permission') emit('Notification', { uid: 'sf:' + p.id, notification_type: 'permission_prompt', category: p.perm || 'other' }); else if (p.flag === 'question') emit('Notification', { uid: 'sf:' + p.id, notification_type: 'elicitation_dialog' }); }
    const ag = j.agents.filter(inP);
    for (const a of ag.filter(x => x.status === 'done' || x.status === 'failed').reverse()) {     // 已交件的：只記進資訊卡，不重演
      const mid = memberFor(a.agent_type); if (!mid || !C(mid)) continue; const st = S.agent(mid);
      if (a.status === 'done') st.done.unshift({ title: a.description || typeLabel(a.agent_type) + ' 的任務', t: a.ended || a.last, summary: a.summary || '' }); else st.failed++;
    }
    const run = ag.filter(x => x.status === 'running');
    run.slice(0, 12).forEach(a => startAgent(a.agent_id, a.agent_type, a.description, 'as:' + a.agent_id, a.tool));
    for (const e of j.events) L.seen.add(e.seq);                                                    // 連上之前的事件不重演
    if (j.total_events) ui.toast(`已連上你的 Claude：${sessionsOfProject().filter(s => !s.ended).length} 個工作階段開著、${run.length} 位同事進行中`);
  }
  function applyQuota(qt) {
    if (!qt || !qt.rate_limits) return;
    const k = JSON.stringify(qt); if (k === L.lastQuota) return; L.lastQuota = k;
    emit('rate_limits', { ts: qt.at, five_hour: qt.rate_limits.five_hour, seven_day: qt.rate_limits.seven_day });
  }
  function ingest(j) {
    if (L.seq && j.seq < L.seq) { resetState(); }                                                   // 收件端被清空過：從頭來
    const first = L.seq === 0;
    L.data = j;
    const ps = j.projects || [];
    L.project = L.cfg.project && ps.some(p => p.hash === L.cfg.project) ? L.cfg.project : (ps[0] || {}).hash || null;
    if (first) applySnapshot(j);
    else {
      const evs = (j.events || []).filter(e => !L.seen.has(e.seq));
      if (evs.length > 40) ui.toast(`補上你離線期間的 ${evs.length} 件事`);
      for (const e of evs) { try { applyEvent(e); } catch (x) { console.warn('即時事件處理失敗', x); } }
      syncSessions();
    }
    applyQuota(j.quota);
    L.seq = Math.max(L.seq, j.seq || 0);
    L.status = j.total_events ? 'ok' : 'nodata';
    if (L.cfg.login && !L.cfg.code) L.msg = '';
  }

  // ───────── 讀取迴圈（分頁在背景時暫停） ─────────
  function schedule(ms) { clearTimeout(L.timer); L.timer = 0; if (L.mode === 'live' && document.visibilityState !== 'hidden') L.timer = setTimeout(poll, ms); }
  async function poll() {
    clearTimeout(L.timer); L.timer = 0;
    if (L.mode !== 'live' || L.inflight) return;
    if (document.visibilityState === 'hidden') { L.paused = true; return; }
    L.paused = false;
    const url = await resolveUrl(), hdr = authHeaders();
    if (!url || !hdr) { L.status = 'setup'; render(); return; }
    L.inflight = true; L.polls++;
    try {
      const ctl = new AbortController(), tm = setTimeout(() => ctl.abort(), 10000);
      const r = await fetch(`${url}/v1/office/${encodeURIComponent(L.cfg.office || 'main')}/state?since=${L.seq}`, { headers: hdr, cache: 'no-store', credentials: 'omit', signal: ctl.signal });
      clearTimeout(tm);
      if (L.mode !== 'live') return;
      if (r.status === 401 || r.status === 403) { L.status = 'auth'; L.fails++; render(); L.inflight = false; schedule(60000); return; }
      if (r.status === 429) throw new Error('太頻繁');
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json(); L.fails = 0; L.lastOk = Date.now(); L.msg = '';
      ingest(j);
    } catch (e) { if (L.mode === 'live') { L.fails++; L.status = 'error'; L.msg = e.name === 'AbortError' ? '逾時' : String(e.message || e).slice(0, 40); } }
    finally { L.inflight = false; }
    render();
    schedule(L.fails ? Math.min(120000, L.pollMs * 2 ** Math.min(3, L.fails)) : L.pollMs);
  }
  L.poll = poll;
  document.addEventListener('visibilitychange', () => {
    if (L.mode !== 'live') return;
    if (document.visibilityState === 'hidden') { clearTimeout(L.timer); L.timer = 0; L.paused = true; }
    else poll();
  });

  function enterLive() {
    if (L.mode !== 'live') { L.mode = 'live'; if (sim && sim.stopDay) sim.stopDay(); resetState(); patchDemo(true); }
    L.status = 'connecting'; render(); poll();
  }
  function restartLive() { resetState(); L.status = 'connecting'; render(); poll(); }
  function enterDemo() {
    clearTimeout(L.timer); L.timer = 0;
    if (L.mode === 'live') { L.mode = 'demo'; resetState(); patchDemo(false); }
    L.status = 'off'; render();
  }
  L.enterLive = enterLive; L.enterDemo = enterDemo;

  // ───────── 績效總表（即時版）：只用真實事件算，資料不夠就寫「樣本不足」 ─────────
  let ledgerEl = null;
  const pct = (a, b) => (b >= 3 ? Math.round(a / b * 100) + '%' : null);
  const mins = ms => (ms < 60000 ? Math.max(1, Math.round(ms / 1000)) + ' 秒' : Math.round(ms / 60000) + ' 分');
  const fmtTok = n => (n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'K' : String(n));
  const NA = '<span class="na">樣本不足</span>';
  function typeRows() { return (L.data && L.data.types) || []; }
  function renderLedger() {
    const types = typeRows(), ceo = (L.data && L.data.ceo) || {};
    const row = t => {
      const fin = (t.done || 0) + (t.failed || 0), mid = L.typeMap.get(t.agent_type) || (C(t.agent_type) ? t.agent_type : null), who = mid && W.members.get(mid) ? W.members.get(mid).nick : '（兼任）';
      return `<tr><td>${esc(who)}<br><span class="na">${esc(t.agent_type)}</span></td><td data-l="派工">${t.dispatched}</td><td data-l="完成">${t.done || 0}</td><td data-l="進行中">${t.running || 0}</td><td data-l="失敗">${t.failed || 0}</td>
        <td data-l="完成率">${pct(t.done || 0, fin) || NA}</td><td data-l="平均耗時">${t.n_dur >= 3 && t.avg_ms != null ? mins(t.avg_ms) : NA}</td><td data-l="Token">${t.n_tokens ? fmtTok(t.tokens) : '<span class="na">未提供</span>'}</td><td data-l="等第"><span class="na" title="等第要滿一週、每類至少 3 件交件，而且計分規則接上真資料之後才評">未評等</span></td></tr>`;
    };
    const ceoLine = `<p class="ceo"><b>CEO（主 Claude）</b>　工作階段 ${ceo.sessions || 0}・你下的指令 ${ceo.prompts || 0}・完成回合 ${ceo.turns || 0}・Token ${ceo.tokens ? fmtTok(ceo.tokens) : '<span class="na">未提供</span>'}・等第 <span class="na">未評等</span></p>`;
    const body = !L.data ? '<p class="empty">尚未收到回報。</p>' : !types.length && !ceo.sessions ? '<p class="empty">樣本不足：近 7 天還沒收到任何工作階段或派工。</p>'
      : `${ceoLine}${types.length ? `<div class="scroll"><table><thead><tr><th>同事</th><th>派工</th><th>完成</th><th>進行中</th><th>失敗</th><th>完成率</th><th>平均耗時</th><th>Token</th><th>等第</th></tr></thead><tbody>${types.map(row).join('')}</tbody></table></div>` : '<p class="empty">樣本不足：近 7 天還沒有派出子 Agent。</p>'}`;
    ledgerEl.innerHTML = `<button class="x" data-a="close" aria-label="關閉">×</button><h3>績效總表<span class="chip2">即時・近 7 天</span></h3>${body}
      <p class="help">數字全部來自你的 Claude 回報的事件（我方統計，不是官方額度）。完成率與平均耗時要至少 3 件交件才算；Token 只有回報裡有用量時才顯示。</p>`;
  }
  function openLedger() {
    if (!ledgerEl) { ledgerEl = document.createElement('aside'); ledgerEl.className = 'panel'; ledgerEl.id = 'aioLedger'; ledgerEl.setAttribute('role', 'dialog'); ledgerEl.setAttribute('aria-label', '績效總表（即時）'); ledgerEl.hidden = true; $('app').append(ledgerEl); ledgerEl.addEventListener('click', e => { if (e.target.closest('[data-a=close]')) closeLedger(); }); }
    pop.hidden = true; renderLedger(); ledgerEl.hidden = false; if (rwBtn) { rwBtn.classList.add('on'); rwBtn.setAttribute('aria-expanded', 'true'); }
  }
  function closeLedger() { if (ledgerEl) ledgerEl.hidden = true; if (rwBtn) { rwBtn.classList.remove('on'); rwBtn.setAttribute('aria-expanded', 'false'); } }
  L.openLedger = openLedger;
  function liveCardBlock(spec) {
    const ts = [...L.typeMap].filter(([, id]) => id === spec.id).map(([t]) => t), rows = typeRows().filter(t => ts.includes(t.agent_type));
    if (spec.id === 'ceo') { const c = (L.data && L.data.ceo) || {}; return `<div class="rw aio-rw"><b>近 7 天（真實）</b>　工作階段 ${c.sessions || 0}・指令 ${c.prompts || 0}・回合 ${c.turns || 0}</div>`; }
    if (!rows.length) return '<div class="rw aio-rw"><b>近 7 天（真實）</b>　<span class="na">樣本不足：還沒有派工紀錄</span></div>';
    const s = rows.reduce((a, t) => ({ d: a.d + t.dispatched, ok: a.ok + (t.done || 0), f: a.f + (t.failed || 0) }), { d: 0, ok: 0, f: 0 });
    return `<div class="rw aio-rw"><b>近 7 天（真實）</b>　派工 ${s.d}・完成 ${s.ok}・失敗 ${s.f}・完成率 ${pct(s.ok, s.ok + s.f) || '<span class="na">樣本不足</span>'}</div>`;
  }

  // ───────── 開場 ─────────
  if (hasCred() && !L.cfg.show) enterLive(); else render();
  return L;
}
