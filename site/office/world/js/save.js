// 雲端存檔（2026-11-16，研究報告 docs/ai_office/game_basics_gap.md 第 9 項）
//
// 做什麼：把這台裝置 localStorage 裡的遊戲進度（aiOffice.game.*）與辦公室擺設／整修（aiOffice.world.*）
//   ① 定時（有改動才傳，預設至少隔 20 秒）與離開頁面時上傳到收件服務（workers/ai-office-bridge 的 /v1/office/main/save/<專案>）；
//   ② 進場時下載，跟本機的合併（比「最後改動時間」，比較新的那份贏）；雲端那份比較新而且內容不同 → 寫回本機並重新整理一次，讓擺設套上；
//   ③ 頂列顯示小字「已存檔 HH:MM」；離線、沒登入站長帳號、收件服務連不上時照舊只存在這台裝置（小字寫「只存在這台裝置」）。
// 身分：網站登入權杖（tw.acct.tok）放在 X-AIO-Session（收件服務只認站長）。不碰接入碼、不送任何別的 localStorage 鍵。
// 功能閘門：features.js 的 office.save（每成功上傳一次算一次；站長不受限）。
// 格式：schema 2 ＝ { keys: { <鍵>: <字串> } }；舊格式 schema 1 ＝ { layout, game } 由 migrate() 升級（跟 worker.js 的 migrateSave 同一套規則，改一邊記得改另一邊）。
// 網址參數（驗收用）：save_every=<毫秒> 改上傳間隔、save_scan=<毫秒> 改檢查本機改動的間隔。
// 接法：world.html 在 main.js 之後加 <script type="module" src="world/js/save.js"></script>。

const SCHEMA = 2, ACCT_TOK = 'tw.acct.tok', META = 'aiOffice.save.meta.v1', RELOADED = 'aiOffice.save.reloaded';
const KEY_RE = /^aiOffice\.(game|world)\.[A-Za-z0-9_.-]{1,60}$/;
const MAX_DATA = 64 * 1024;
const qs = new URLSearchParams(location.search);
const EVERY = Math.max(500, +qs.get('save_every') || 20000), SCAN = Math.max(200, +qs.get('save_scan') || 4000);
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); return true; } catch (e) { return false; } };
const hhmm = ms => new Intl.DateTimeFormat('zh-TW', { timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(ms));

/** 舊格式 → 現行格式（回 { keys } 或 null） */
export function migrate(schema, data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  let d = data, v = Number.isInteger(schema) ? schema : 1;
  if (v > SCHEMA) return null;
  if (v === 1) {
    const keys = {};
    if (d.layout && typeof d.layout === 'object') keys['aiOffice.world.layout.v1'] = JSON.stringify(d.layout);
    if (d.game && typeof d.game === 'object') for (const [k, x] of Object.entries(d.game)) keys['aiOffice.game.' + k] = typeof x === 'string' ? x : JSON.stringify(x);
    d = { keys }; v = 2;
  }
  const out = {};
  for (const [k, x] of Object.entries(d.keys || {})) if (KEY_RE.test(k) && typeof x === 'string') out[k] = x;
  return { keys: out };
}
/** 本機要同步的鍵（排除接入設定、登入、鏡頭偏好等） */
function snapshot() {
  const keys = {};
  try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (k && KEY_RE.test(k)) keys[k] = localStorage.getItem(k); } } catch (e) { /* 私密視窗 */ }
  return keys;
}
const sig = keys => JSON.stringify(Object.keys(keys).sort().map(k => [k, keys[k]]));

function boot(W) {
  const P = { proj: 'main', status: 'local', at: 0, savedAt: 0, ver: null, dirty: false, busy: false, lastUp: 0, last: '', note: '', ups: 0, conflicts: 0, restored: false, migrated: false };
  W.save = P;
  const L = W.live || {};
  P.proj = (L.qProject && /^[0-9a-f]{16}$/.test(L.qProject)) ? L.qProject : 'main';
  // 本機的存檔紀錄：{ <專案>: { ver, at（本機最後改動）, saved（最後上傳成功）, sig } }
  const metaAll = () => { try { return JSON.parse(lsGet(META) || '{}') || {}; } catch (e) { return {}; } };
  const meta = () => metaAll()[P.proj] || {};
  const setMeta = o => { const m = metaAll(); m[P.proj] = { ...(m[P.proj] || {}), ...o }; lsSet(META, JSON.stringify(m)); };

  // ── 頂列小字 ──
  const css = document.createElement('style'); css.id = 'saveCss';
  css.textContent = `#saveTag{font-size:11.5px;color:var(--sub,#7a6f66);background:rgba(255,255,255,.72);border-radius:10px;padding:3px 8px;white-space:nowrap;line-height:1.3}
#saveTag.ok{color:#2f7d51}#saveTag.warn{color:#a8641a}
@media (max-width:640px){#saveTag{font-size:11px;padding:2px 6px;order:20}}`;
  document.head.append(css);
  const tag = document.createElement('span'); tag.id = 'saveTag'; tag.setAttribute('role', 'status'); tag.setAttribute('aria-live', 'polite');
  const bar = document.getElementById('bar'); if (bar) bar.append(tag);
  function show() {
    let t = '', c = '';
    if (P.status === 'saved') { t = '已存檔 ' + hhmm(P.savedAt); c = 'ok'; }
    else if (P.status === 'saving') t = '存檔中…';
    else if (P.status === 'out') { t = '雲端存檔今天的次數用完了，先存在這台裝置'; c = 'warn'; }
    else t = '只存在這台裝置';
    tag.textContent = t; tag.className = c; tag.title = P.note || (P.status === 'saved' ? '辦公室擺設與進度已存到雲端，換裝置也能接著玩' : '登入站長帳號、連上收件服務後，會自動存到雲端');
  }
  show();

  const tok = () => lsGet(ACCT_TOK);
  async function base() { try { return L.resolveUrl ? await L.resolveUrl() : ''; } catch (e) { return ''; } }
  async function call(method, body, keepalive) {
    const u = await base(), t = tok();
    if (!u || !t) return { s: 0 };
    try {
      const r = await fetch(u + '/v1/office/main/save/' + P.proj, { method, keepalive: !!keepalive, headers: { 'X-AIO-Session': t, ...(body ? { 'Content-Type': 'application/json' } : {}) }, body: body ? JSON.stringify(body) : undefined, credentials: 'omit', cache: 'no-store' });
      let j = null; try { j = await r.json(); } catch (e) { j = null; }
      return { s: r.status, j };
    } catch (e) { return { s: 0 }; }
  }
  // 雲端那份寫進本機：只動同步範圍內的鍵（雲端有的寫入；雲端沒有、而本機有的刪掉＝跟雲端一致）
  function apply(keys) {
    const cur = snapshot();
    for (const k of Object.keys(cur)) if (!(k in keys)) lsSet(k, null);
    for (const [k, v] of Object.entries(keys)) lsSet(k, v);
  }
  function adoptRemote(sv, why) {
    const m = migrate(sv.schema, sv.data); if (!m) return false;
    if (sv.schema !== SCHEMA || (sv.data && !sv.data.keys)) P.migrated = true;
    const changed = sig(m.keys) !== sig(snapshot());
    apply(m.keys);
    P.ver = sv.version; P.at = sv.at; P.savedAt = sv.saved_at || sv.at; P.status = 'saved'; P.last = sig(m.keys);
    setMeta({ ver: sv.version, at: sv.at, saved: P.savedAt, sig: P.last });
    show();
    if (changed) {
      P.restored = true;
      // 擺設在開場時就讀進場景：寫回本機後重新整理一次（同一個分頁只做一次，避免來回跳）
      let again = false; try { again = sessionStorage.getItem(RELOADED) === P.proj + ':' + sv.version; } catch (e) { again = false; }
      if (!again) {
        try { sessionStorage.setItem(RELOADED, P.proj + ':' + sv.version); } catch (e) { /* 略 */ }
        if (W.ui && W.ui.toast) W.ui.toast(why === 'conflict' ? '另一台裝置有比較新的存檔，已換成那一份' : '已從雲端還原存檔');
        setTimeout(() => location.reload(), 700);
      }
    }
    return true;
  }

  async function upload(keepalive) {
    if (P.busy) return;
    const keys = snapshot(), s = sig(keys);
    if (s.length > MAX_DATA) { P.note = '存檔太大，這次只存在這台裝置'; P.status = 'local'; show(); return; }
    const g = W.gate ? W.gate.peek('office.save') : { pass: true };
    if (!g.pass) { P.status = 'out'; P.note = g.note || ''; show(); return; }
    P.busy = true; if (!keepalive) { P.status = 'saving'; show(); }
    const gt = W.gate && !keepalive ? await W.gate.begin('office.save') : null;
    if (gt && !gt.pass) { P.busy = false; P.status = 'out'; P.note = gt.note || ''; show(); return; }
    const at = meta().at || Date.now();
    const r = await call('POST', { schema: SCHEMA, base: P.ver, at, data: { keys } }, keepalive);
    P.busy = false; P.lastUp = Date.now();
    if (r.s === 200 && r.j && r.j.ok) {
      if (gt) gt.done();
      P.ups++; P.ver = r.j.version; P.savedAt = r.j.saved_at || Date.now(); P.status = 'saved'; P.dirty = false; P.last = s; P.note = '';
      if (r.j.conflict) P.conflicts++;
      setMeta({ ver: P.ver, saved: P.savedAt, sig: s }); show(); return;
    }
    if (gt) gt.cancel();
    if (r.s === 409 && r.j && r.j.error === 'conflict' && r.j.save) { P.conflicts++; P.dirty = false; adoptRemote(r.j.save, 'conflict'); return; }
    P.status = 'local'; P.note = r.s === 401 ? '雲端存檔只開放站長帳號，目前存在這台裝置' : r.s === 0 ? '連不上收件服務，目前存在這台裝置，連上後會自動補傳' : '這次沒有存到雲端，稍後會再試'; show();
  }

  // 本機改動偵測：每隔 SCAN 比一次同步範圍內的內容；有變就記下「最後改動時間」，滿 EVERY 才上傳
  function scan() {
    const k = snapshot(), s = sig(k);
    if (!Object.keys(k).length && (P.last || meta().sig || '[]') !== '[]') return;   // 本機被整個清空（清除網站資料、別的分頁清掉）：不當成改動，免得把雲端那份蓋成空的

    if (s !== (P.last || meta().sig || '')) {
      if (!P.dirty) { P.dirty = true; setMeta({ at: Math.max(Date.now(), (meta().at || 0) + 1) }); }   // 換成雲端那份之後的新改動一定比那份新（別台裝置時鐘快也一樣）
      if (Date.now() - P.lastUp >= EVERY) upload(false);
    }
  }
  P.flush = () => upload(false);
  P.scan = scan;

  async function start() {
    const m0 = meta(); P.ver = m0.ver ?? null; P.at = m0.at || 0; P.last = m0.sig || '';
    if (m0.saved) P.savedAt = m0.saved;
    const r = await call('GET');
    if (r.s === 200 && r.j && r.j.ok) {
      const sv = r.j.save, local = snapshot(), ls = sig(local);
      if (sv && (!m0.at || sv.at > m0.at || (sv.version !== m0.ver && !Object.keys(local).length))) adoptRemote(sv, 'load');
      else if (sv && sv.version === m0.ver && ls === m0.sig) { P.status = 'saved'; P.savedAt = sv.saved_at || sv.at; show(); }
      else if (Object.keys(local).length) { if (sv && P.ver == null) P.ver = sv.version; P.dirty = true; if (!m0.at) setMeta({ at: Date.now() }); await upload(false); }
      else { P.status = 'saved'; P.savedAt = sv ? (sv.saved_at || sv.at) : Date.now(); show(); }
    } else {
      P.status = 'local'; P.note = r.s === 401 ? '雲端存檔只開放站長帳號，目前存在這台裝置' : r.s === 0 ? '' : '收件服務暫時讀不到存檔，目前存在這台裝置'; show();
    }
    setInterval(scan, SCAN);
  }
  // 離開頁面：有沒傳的改動就用 keepalive 補傳一次
  // 只補傳「真的改過」的：本機被清空（例如清除網站資料）不算改動，不然會把雲端那份蓋成空的
  const bye = () => { const k = snapshot(); if (P.dirty || (Object.keys(k).length && sig(k) !== P.last)) { if (!P.dirty) setMeta({ at: Date.now() }); upload(true); } };
  addEventListener('pagehide', bye);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') bye(); });
  start();
}

// 等辦公室（main.js）建好 window.__world 再開始
{ let n = 0; const t = setInterval(() => { const W = window.__world; if (W && W.live) { clearInterval(t); boot(W); } else if (++n > 300) clearInterval(t); }, 100); }
