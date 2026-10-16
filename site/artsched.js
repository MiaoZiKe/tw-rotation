/* ============================================================================
   產貼文頻率設定（管理區 #admin/articles「文章主題」分頁最下面那張卡）—— 2026-10-16 建
   ----------------------------------------------------------------------------
   Andy 2026-10-16：「我需要可以產貼文頻率設定……我可以設定每週幾、哪個時段幫我產出精選貼文」。
   這一塊回答的問題：「Claude 每週哪幾天的哪一輪要自動幫我產精選文章？每輪各產幾篇、什麼類別？」
   所以怎麼用：開「啟用」→ 在「星期 × 時段」表格點你要的格子 → 設各類別每輪幾篇 → 按「儲存」。
   儲存方式照既有的「產出佇列」（DECISIONS 見 docs/articles/production_guide.md）：
     按儲存 → 會員 Worker /v1/articles/schedule/add（只有管理者）→ article-jobs.yml 每小時同步成
     data/_state/article_schedule.json → Claude 排程（台北 09:50／14:50／20:50）醒來時讀它，
     今天星期幾、這一輪的時段對得上，就依類別與篇數自己排進佇列。所以設定最多等 1 小時同步＋排程到點才會生效，頁面明講。
   時段先限定現有排程的三輪（Worker 的 allowed.times 回來什麼就畫什麼；日後增加時段只要改 Worker 清單與 Claude 排程）。
   權限：只有 articles.js 的管理者畫面會呼叫 mount；Worker 端另外驗證管理者。
   預覽版：寫入會被 preview_boot.js 擋（回 preview_readonly）→ 畫面寫「預覽版不會真的儲存」。
   後端還沒部署新版（404／bad_op）→ 寫「後端還沒更新」，設定留在畫面上不丟（也存 localStorage 草稿，鍵 tw.art.sched.draft）。
   安全：所有字串 esc() 後才放進畫面。
   驗收：scripts/_uitest.py「文章主題兩分頁1016」。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const WD = ['一', '二', '三', '四', '五', '六', '日'];
  const LS = 'tw.art.sched.draft';
  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：只在這次有效 */ } };

  /* 狀態：enabled 總開關；slots {"1":["09:50",…]}；cats {news,intro,know}；saved＝伺服器上那一份（判斷有沒有未儲存的變更） */
  const S = { enabled: false, slots: {}, cats: { news: 0, intro: 0, know: 0 }, times: ['09:50', '14:50', '20:50'], max: 3, saved: null, savedAt: '', backend: 'loading', msg: '', err: false, busy: false };
  let O = { call: () => Promise.resolve(null), cats: [['news', '比比快訊'], ['intro', '比比產業鏈'], ['know', '比比知識']] };

  const norm = () => JSON.stringify({ e: !!S.enabled, s: Object.keys(S.slots).sort().map((d) => [d, S.slots[d].slice().sort()]).filter((x) => x[1].length), c: O.cats.map(([k]) => S.cats[k] || 0) });
  const has = (d, t) => (S.slots[d] || []).includes(t);
  function toggle(d, t) {
    const a = (S.slots[d] || []).slice(), i = a.indexOf(t);
    if (i >= 0) a.splice(i, 1); else a.push(t);
    if (a.length) S.slots[d] = S.times.filter((x) => a.includes(x)); else delete S.slots[d];
  }
  const nRuns = () => Object.values(S.slots).reduce((n, a) => n + a.length, 0);
  const perRun = () => O.cats.reduce((n, [k]) => n + (S.cats[k] || 0), 0);
  /* 開啟的條件（Andy：先都不要填、開關自己選；要有星期＋時段＋類別才准開）→ 回傳「還缺什麼」，空字串＝可以開 */
  function lack() {
    const a = [];
    if (!nRuns()) a.push('③ 還沒勾任何「星期 × 時段」');
    if (!perRun()) a.push('② 還沒有任何類別設成 1 篇以上');
    return a.join('；');
  }
  const err = () => (S.enabled ? lack() : '');
  /* 白話摘要：時間組合相同的星期併成一句 */
  function summary() {
    if (!S.enabled) { const w = nRuns() && perRun() ? '（已填的設定先保留：' + summaryBody() + '）' : ''; return '目前未啟用，不會自動排文章' + w + '；你仍可以在上面手動「產生精選文章」。'; }
    return summaryBody();
  }
  function summaryBody() {
    const g = {};
    Object.keys(S.slots).sort().forEach((d) => { const k = S.slots[d].join('、'); (g[k] = g[k] || []).push(+d); });
    const when = Object.keys(g).map((k) => { const ds = g[k]; const nm = ds.length === 7 ? '每天' : ds.join() === '1,2,3,4,5' ? '週一至週五' : ds.map((n) => '週' + WD[n - 1]).join('、'); return nm + ' ' + k; }).join('；');
    const what = O.cats.filter(([k]) => S.cats[k] > 0).map(([k, n]) => n + ' ' + S.cats[k] + ' 篇').join('、');
    return (when || '（還沒勾時段）') + '（台北時間），每輪各產：' + (what || '（篇數全是 0）') + '；一週共 ' + (nRuns() * perRun()) + ' 篇。';
  }

  const BACK = {
    loading: '讀取中…', ok: '', none: '', preview: '預覽版：按儲存不會真的寫進正式站，只用來看畫面。',
    old: '後端還沒更新到新版（會員 Worker 尚未部署「頻率設定」），所以現在存不進去；設定先留在這個畫面與瀏覽器草稿。',
    off: '連不到會員伺服器，設定先留在這個畫面與瀏覽器草稿。', denied: '登入身分不是管理者（請重新登入）。',
  };
  function stateLine() {
    if (S.backend === 'ok') return S.savedAt ? '已儲存的版本：' + S.savedAt + (norm() === S.saved ? '（畫面與已儲存的一致）' : '（畫面有尚未儲存的變更）') : '還沒儲存過任何設定（目前＝關閉）。';
    return BACK[S.backend] || '';
  }

  function html() {
    const cell = (d, t) => `<button type="button" class="dd${has(d, t) ? ' on' : ''}" data-d="${d}" data-t="${esc(t)}" aria-pressed="${has(d, t)}" aria-label="週${WD[d - 1]} ${esc(t)}" title="週${WD[d - 1]} ${esc(t)}">${WD[d - 1]}</button>`;
    return `<div class="card artadm asd" id="artSchedCard">
  <div class="hd"><h3>產貼文頻率設定</h3><span class="muted">設好之後，Claude 到點會自己把文章排進上面的「產出進度」，不用你每次按</span></div>
  <p class="asd-lag" id="asdLag">設定要等「每小時一次的同步」＋「Claude 排程到點（台北 09:50、14:50、20:50）」才會生效，最久約 1 小時多；要立刻產，請用上面的「產生精選文章」，或直接在對話告訴 CEO。</p>
  <div class="asd-grid">
    <div class="asd-box"><h4>① 啟用開關</h4>
      <label class="asd-sw"><input type="checkbox" id="asdOn"${S.enabled ? ' checked' : ''}><span>啟用自動產精選文章（切換就立即儲存）</span></label>
      <p class="asd-why" id="asdOnWhy" role="status"></p>
      <p class="muted" id="asdState" role="status"></p></div>
    <div class="asd-box"><h4>② 每個時段，各類別產幾篇 <span class="asd-off" data-off>未啟用，不會自動產出</span></h4>
      ${O.cats.map(([k, n]) => `<div class="asd-kr" data-cat="${esc(k)}"><span>${esc(n)}</span><span class="asd-stp"><button type="button" data-st="-1" aria-label="${esc(n)}減一篇">−</button><input type="number" min="0" max="${S.max}" step="1" inputmode="numeric" data-kn="${esc(k)}" value="${S.cats[k] || 0}" aria-label="${esc(n)}每輪篇數"><button type="button" data-st="1" aria-label="${esc(n)}加一篇">＋</button></span></div>`).join('')}
      <p class="muted">每一輪每個類別最多 ${S.max} 篇。</p></div>
    <div class="asd-box asd-w2"><h4>③ 每週幾 × 哪個時段（台北時間；點格子開／關） <span class="asd-off" data-off>未啟用，不會自動產出</span></h4>
      <div class="asd-tbl" id="asdTbl">
        ${S.times.map((t) => `<div class="asd-row" data-t="${esc(t)}"><span class="asd-tm">${esc(t)}</span><span class="asd-days">${[1, 2, 3, 4, 5, 6, 7].map((d) => cell(d, t)).join('')}</span></div>`).join('')}
      </div>
      <div class="asd-q"><button type="button" data-q="work">全部時段 週一至週五</button><button type="button" data-q="all">全部時段 每天</button><button type="button" data-q="none">全部取消</button>
        <span class="muted">目前 Claude 排程每天 ${S.times.length} 輪（${esc(S.times.join('、'))}）；日後要增加時段，請告訴 CEO。</span></div></div>
    <div class="asd-box asd-w2"><h4>④ 確認並儲存</h4>
      <div class="asd-sum" id="asdSum"></div><div class="asd-why" id="asdWhy" role="status"></div>
      <div class="asd-act"><button type="button" class="asd-save" id="asdSave">儲存設定</button><button type="button" id="asdReload">重新讀取已儲存的</button><span class="asd-msg" id="asdMsg" role="status"></span></div></div>
  </div>
</div>`;
  }

  function css() {
    if (document.getElementById('asdCss')) return;
    const s = document.createElement('style'); s.id = 'asdCss';
    s.textContent = `
#v-subadm .asd .asd-lag{border-left:3px solid var(--accent,var(--cyan));background:var(--panel-3);border-radius:0 8px 8px 0;padding:8px 12px;color:var(--ink);font-size:13.5px;line-height:1.6;margin:0 0 10px}
#v-subadm .asd .asd-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
#v-subadm .asd .asd-box{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:10px 14px 12px;min-width:0}
#v-subadm .asd .asd-w2{grid-column:1/-1}
#v-subadm .asd h4{margin:0 0 8px;font-size:13.5px;font-weight:700;color:var(--ink)}
#v-subadm .asd .muted{color:var(--ink-2);font-size:13px;line-height:1.6;margin:6px 0 0}
#v-subadm .asd button{box-sizing:border-box;min-height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}
#v-subadm .asd button:hover{border-color:var(--cyan)}
#v-subadm .asd .asd-sw{display:flex;align-items:center;gap:10px;min-height:40px;cursor:pointer;font-size:14px}
#v-subadm .asd .asd-sw input{width:20px;height:20px;margin:0;accent-color:var(--cyan)}
#v-subadm .asd .asd-kr{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:8px;min-height:40px;border-bottom:1px solid var(--line);font-size:14px}
#v-subadm .asd .asd-kr:last-of-type{border-bottom:0}
#v-subadm .asd .asd-stp{display:inline-flex;align-items:center;gap:4px}
#v-subadm .asd .asd-stp button{width:32px;padding:0;font-size:16px}
#v-subadm .asd .asd-stp input{box-sizing:border-box;width:44px;height:32px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-family:var(--mono);font-size:13px;text-align:center;padding:0 6px;-moz-appearance:textfield;appearance:textfield}
#v-subadm .asd .asd-stp input::-webkit-outer-spin-button,#v-subadm .asd .asd-stp input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
#v-subadm .asd .asd-off{display:inline-block;margin-left:6px;padding:0 8px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink-3);font-size:12px;font-weight:500}
#v-subadm .asd .asd-off[hidden]{display:none}
#v-subadm .asd .asd-sw.dis{opacity:.55;cursor:not-allowed}
#v-subadm .asd .asd-tbl{display:flex;flex-direction:column;gap:6px}
#v-subadm .asd .asd-row{display:grid;grid-template-columns:80px minmax(0,1fr);align-items:center;gap:8px}
#v-subadm .asd .asd-tm{font-family:var(--mono);font-size:14px;color:var(--ink)}
#v-subadm .asd .asd-days{display:grid;grid-template-columns:repeat(7,40px);gap:6px}
#v-subadm .asd .dd{width:40px;padding:0;font-weight:600}
#v-subadm .asd .dd.on{background:var(--panel);border-color:var(--cyan);color:var(--cyan)}
#v-subadm .asd .asd-q{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:8px}
#v-subadm .asd .asd-q .muted{margin:0 0 0 4px;font-size:12.5px}
#v-subadm .asd .asd-sum{font-size:13.5px;line-height:1.7;color:var(--ink)}
#v-subadm .asd .asd-why{font-size:12.5px;color:var(--amber);min-height:20px;margin-top:4px}
#v-subadm .asd .asd-act{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
#v-subadm .asd .asd-save{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
#v-subadm .asd .asd-save:disabled{opacity:.45;cursor:not-allowed}
#v-subadm .asd .asd-msg{font-size:13px;color:var(--ink-2)}
#v-subadm .asd .asd-msg.err{color:var(--amber)}
@media (max-width:820px){#v-subadm .asd .asd-grid{grid-template-columns:minmax(0,1fr)}}
@media (max-width:640px){
  /* 手機：時間在上、七顆星期平分一整行（每顆 ≥ 32px）；說明文字縮短 */
  #v-subadm .asd .asd-box{padding:10px 10px 12px}
  #v-subadm .asd .asd-row{grid-template-columns:minmax(0,1fr)}
  #v-subadm .asd .asd-days{grid-template-columns:repeat(7,minmax(0,1fr));gap:4px}
  #v-subadm .asd .dd{width:auto}
  #v-subadm .asd .asd-q .muted{display:none}
}
`;
    document.head.appendChild(s);
  }

  function sync(host) {
    const c = $('#artSchedCard', host); if (!c) return;
    if (S.enabled && lack()) { S.enabled = false; S.msg = '已自動關閉：設定不完整（' + lack() + '）'; S.err = true; setTimeout(() => save(host, true), 0); }   // 開著的時候把時段或類別清空 → 不能讓它「開著卻什麼都不做」
    const lk = lack(), on = $('#asdOn', c);
    on.checked = !!S.enabled; on.disabled = !!lk && !S.enabled; on.closest('.asd-sw').classList.toggle('dis', on.disabled);
    $('#asdOnWhy', c).textContent = on.disabled ? '還不能開啟：' + lk : '';
    $$('[data-off]', c).forEach((x) => { x.hidden = !!S.enabled; });
    $$('.dd', c).forEach((b) => { const on = has(+b.dataset.d, b.dataset.t); b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    $$('.asd-kr', c).forEach((r) => { const i = $('input', r); if (document.activeElement !== i) i.value = String(S.cats[r.dataset.cat] || 0); });
    $('#asdSum', c).textContent = summary();
    const e = err();
    $('#asdWhy', c).textContent = e ? '無法儲存：' + e : '';
    $('#asdSave', c).disabled = !!e || S.busy;
    $('#asdState', c).textContent = stateLine();
    const m = $('#asdMsg', c); m.textContent = S.msg; m.classList.toggle('err', S.err);
    lsSet(LS, JSON.stringify({ enabled: S.enabled, slots: S.slots, cats: S.cats }));
  }
  function apply(sc) {
    S.enabled = !!sc.enabled;
    S.slots = {}; Object.keys(sc.slots || {}).forEach((d) => { const a = (sc.slots[d] || []).filter((t) => S.times.includes(t)); if (a.length) S.slots[d] = a; });
    O.cats.forEach(([k]) => { S.cats[k] = Math.max(0, Math.min(S.max, Math.round(Number(sc.cats && sc.cats[k]) || 0))); });
  }
  const tpe = (ms) => { const d = new Date(Number(ms) + 8 * 3600e3); return d.toISOString().slice(0, 16).replace('T', ' '); };
  async function load(host) {
    S.backend = 'loading'; sync(host);
    const r = await O.call('/v1/articles/schedule/get', {});
    if (!host.isConnected) return;
    if (!r) S.backend = 'off';
    else if (r._s === 403) S.backend = 'denied';
    else if (r._s === 404 || r.error === 'not_found' || (r._s >= 400 && !r.allowed)) S.backend = 'old';
    else {
      S.backend = 'ok';
      if (r.allowed && Array.isArray(r.allowed.times) && r.allowed.times.length) S.times = r.allowed.times.slice();
      if (r.allowed && r.allowed.max) S.max = r.allowed.max;
      if (r.schedule) { apply(r.schedule); S.savedAt = r.schedule.updated ? tpe(r.schedule.updated) : '已儲存'; S.saved = norm(); }
      else { S.savedAt = ''; S.saved = norm(); }
    }
    host.innerHTML = html(); bind(host); sync(host);
  }
  async function save(host, revertOnFail) {
    if (err() || S.busy) return;
    const was = S.enabled;
    S.busy = true; S.msg = '儲存中…'; S.err = false; sync(host);
    const r = await O.call('/v1/articles/schedule/add', { enabled: !!S.enabled, slots: S.slots, cats: O.cats.reduce((o, [k]) => { o[k] = S.cats[k] || 0; return o; }, {}) });
    S.busy = false;
    const okSave = !!(r && r.ok);
    if (!okSave && revertOnFail === 'toggle') S.enabled = !was;   // 開關切了但沒存成 → 退回去，不假裝已經開了
    if (r && r.ok) { S.backend = 'ok'; S.savedAt = r.schedule && r.schedule.updated ? tpe(r.schedule.updated) : '剛剛'; S.saved = norm(); S.msg = revertOnFail === true ? '已自動關閉：設定不完整（時段或類別被清空），並已同步儲存為關閉。' : '已儲存。' + (S.enabled ? '最晚下一輪 Claude 排程（台北 09:50／14:50／20:50）起生效。' : '已關閉。'); S.err = false; }
    else if (r && r.error === 'preview_readonly') { S.backend = 'preview'; S.msg = '預覽版不會真的儲存（寫入被擋下）。'; S.err = true; }
    else if (!r) { S.backend = 'off'; S.msg = '儲存失敗：連不到會員伺服器。'; S.err = true; }
    else if (r._s === 403) { S.backend = 'denied'; S.msg = '儲存失敗：登入身分不是管理者。'; S.err = true; }
    else if (r._s === 404) { S.backend = 'old'; S.msg = '儲存失敗：後端還沒更新到新版。'; S.err = true; }
    else { S.msg = '儲存失敗：' + (r.error || ('HTTP ' + r._s)); S.err = true; }
    sync(host);
  }
  function bind(host) {
    const c = $('#artSchedCard', host);
    /* 開關＝即時生效：切換就送出（Andy 要的是「關掉就立刻停止自動排隊」），不用再按儲存；其他欄位照舊要按「儲存設定」 */
    $('#asdOn', c).onchange = (e) => { S.enabled = e.target.checked; S.msg = ''; sync(host); save(host, 'toggle'); };
    $('#asdTbl', c).onclick = (e) => { const b = e.target.closest('button[data-d]'); if (!b) return; toggle(+b.dataset.d, b.dataset.t); S.msg = ''; sync(host); };
    $$('.asd-q button', c).forEach((b) => { b.onclick = () => {
      S.slots = {}; if (b.dataset.q !== 'none') (b.dataset.q === 'work' ? [1, 2, 3, 4, 5] : [1, 2, 3, 4, 5, 6, 7]).forEach((d) => { S.slots[d] = S.times.slice(); });
      S.msg = ''; sync(host); }; });
    c.addEventListener('click', (e) => { const st = e.target.closest('button[data-st]'); if (!st) return; const k = st.closest('.asd-kr').dataset.cat; S.cats[k] = Math.max(0, Math.min(S.max, (S.cats[k] || 0) + (+st.dataset.st))); S.msg = ''; sync(host); });
    c.addEventListener('change', (e) => { const i = e.target.closest('input[data-kn]'); if (!i) return; const n = Math.round(Number(i.value)); S.cats[i.dataset.kn] = Math.max(0, Math.min(S.max, Number.isFinite(n) ? n : 0)); i.value = String(S.cats[i.dataset.kn]); S.msg = ''; sync(host); });   // 輸入框還有焦點時 sync 不會改它，所以這裡直接把修正後的數字寫回去
    $('#asdSave', c).onclick = () => save(host);
    $('#asdReload', c).onclick = () => { S.msg = ''; load(host); };
  }
  function mount(host, opts) {
    css(); if (opts) O = Object.assign(O, opts);
    try { const d = JSON.parse(lsGet(LS) || 'null'); if (d && typeof d === 'object' && !S.saved) apply({ enabled: d.enabled, slots: d.slots, cats: d.cats }); } catch (e) { /* 壞草稿就不理它 */ }
    host.innerHTML = html(); bind(host); sync(host);
    load(host);
  }
  window.TwArtSched = { mount, state: () => S };
})();
