/* 新會員體驗到期前問卷（2026-11-01 Andy：「快到期時在他們打開首頁會跳出意見檢核表，填寫完再送7天；11-02 改成獎勵 7 天 Plus」）
   · 條件：已登入＋後端 /v1/me/trial 說 survey_eligible 且還沒填過＋人在首頁（#overview 或沒有 hash）→ 跳出。
   · 「稍後再說」／× ／Esc → 24 小時內不再跳（localStorage，存不了就只管這次瀏覽）。
   · 四步：①滿意度 ②最實用功能 ③最需要優化的功能＋一行字 ④最希望新增的功能。
   · ②③的選項「母分頁／子分頁」不寫死：讀側欄清單 window.TwL4Nav（layout4.js；新增分頁自動多一張卡），
     讀不到才退回讀 DOM 的 #tabs。每題最多 5 個母分頁（第 6 個擋下提示），子分頁不限。
   · 送出：POST /v1/survey/submit，成功顯示新的截止日；失敗顯示後端訊息。
   · 呼叫方式跟 account.js 同一個 TwAccount.call（同網址前綴、同登入憑證）；後端沒設定（TwAccount.on() 為假）就整支不動作。 */
(function () {
  'use strict';
  const SNOOZE_KEY = 'tw.survey.snooze', SNOOZE_MS = 24 * 3600e3, MAX_P = 5;
  const WANTS = ['更多 AI 分析', '個股提醒通知', '手機 App', '更多 ETF 工具', '策略回測', '社群討論', '教學內容', '更多資料指標'];
  const SAT_TXT = ['很不滿意', '不太滿意', '普通', '滿意', '非常滿意'];
  const STEPS = 4;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：這次瀏覽有效 */ } } };
  let doneFlag = false, failAt = -1e9, memSnooze = 0, trial = null, checking = false, shown = false, ov = null, lastFocus = null;
  const A = () => window.TwAccount || null;
  const isHome = () => { const h = (location.hash || '').replace(/^#\/?/, ''); return h === '' || h === 'overview'; };
  /* 測試模式（2026-11-02 Andy：他已註冊、不符合條件沒辦法測）：
     ① 預覽版（網址有 /preview/）首頁一律直接跳出，不論登入與資格；② 正式站網址加 ?survey=test，只有站主帳號（user.admin）強制顯示。
     兩種都不打後端（送出走假成功、顯示「示範」）、不寫「稍後再說」的 24 小時記錄。 */
  let demoForce = false;   // TwSurvey.open({demo:true})：展示頁（#promo-demo）叫出來的示範，假資料、送出走假成功
  const testMode = () => {
    if (demoForce) return 'demo';
    if (/\/preview\//.test(location.pathname)) return 'preview';
    const q = (location.search || '') + '&' + ((location.hash || '').split('?')[1] || '');
    const a = A(); const u = a && a.user && a.user();
    return /(^|[?&])survey=test(&|$)/.test(q) && u && u.admin === true ? 'admin' : '';
  };
  const snoozed = () => { const t = Math.max(memSnooze, +ls.get(SNOOZE_KEY) || 0); return Date.now() < t; };
  function snooze() { if (testMode()) return; memSnooze = Date.now() + SNOOZE_MS; ls.set(SNOOZE_KEY, String(memSnooze)); }

  /* ---------- 母／子分頁清單（動態讀側欄） ---------- */
  const ADMIN_ONLY = ['admin', 'delivery', 'tc', 'lab', 'flowcheck'];   // 管理區、交付清單、科技透明圈、交易練習室：只給管理員，一般會員在側欄看不到，不能讓他們評
  const isAdm = () => { const a = A(); const u = a && a.user && a.user(); return !!(u && u.admin === true); };
  const hiddenTab = (k) => { const e = document.querySelector('#tabs .tab[data-view="' + k + '"]'); return !!(e && (e.hidden || e.style.display === 'none')); };   // 側欄對這位會員有藏的也跳過（權限、導覽隱藏）
  const skip = (k) => (ADMIN_ONLY.includes(k) && !isAdm()) || hiddenTab(k);
  function navList() {
    const N = window.TwL4Nav, out = [];
    if (N && N.PAGES) {
      const order = []; (N.GROUPS || []).forEach((g) => (g.views || []).forEach((v) => order.push(v)));
      Object.keys(N.PAGES).forEach((k) => { if (!order.includes(k)) order.push(k); });
      const subs = N.SUBS_DESK || N.SUBS || {};
      order.forEach((k) => {
        if (skip(k) || !N.PAGES[k]) return;
        out.push({ k, t: N.PAGES[k].t, subs: (subs[k] || []).map((s) => ({ k: s.k, t: s.t })) });
      });
    }
    if (out.length) return out;
    /* 退路：直接讀 DOM 的側欄 */
    document.querySelectorAll('#tabs .tab[data-view]').forEach((b) => {
      const k = b.dataset.view; if (skip(k) || out.some((o) => o.k === k)) return;
      out.push({ k, t: (b.textContent || k).trim(), subs: [...document.querySelectorAll('#tabs .l4subtab[data-parent="' + k + '"]')].map((s) => ({ k: s.dataset.l4sub || s.dataset.adm || s.textContent.trim(), t: s.textContent.trim() })) });
    });
    return out;
  }

  /* ---------- 問卷 key → 中文名（管理區「問卷與願望」頁讀 window.TwSurveyLabels）----------
     母分頁 key＝側欄 view（flow），子分頁 key＝「母/子」（flow/flow-inst）。管理員專屬頁一律不列（不管看的人是誰）。
     用 getter：側欄清單（TwL4Nav）晚於本檔載入也沒關係，每次讀都是現算，新增分頁自動多一筆。 */
  function buildLabels() {
    const o = {}, N = window.TwL4Nav; if (!N || !N.PAGES) return o;
    const subs = N.SUBS_DESK || N.SUBS || {};
    Object.keys(N.PAGES).forEach((k) => {
      if (ADMIN_ONLY.includes(k) || !N.PAGES[k]) return;
      o[k] = N.PAGES[k].t;
      (subs[k] || []).forEach((x) => { o[k + '/' + x.k] = x.t; });
    });
    return o;
  }
  try { Object.defineProperty(window, 'TwSurveyLabels', { configurable: true, get: buildLabels }); } catch (e) { /* 略 */ }

  /* ---------- 作答狀態 ---------- */
  function fresh() { return { step: 1, sat: 0, useful: new Map(), improve: new Map(), act: { useful: '', improve: '' }, improve_text: '', want: new Set(), want_text: '', busy: false, err: '', warn: '', done: null }; }
  let st = fresh(), nav = [];

  const pkgList = (m) => [...m.entries()].map(([p, s]) => ({ p, subs: [...s] }));
  function payload() {
    return { sat: st.sat, useful: pkgList(st.useful), improve: pkgList(st.improve), improve_text: st.improve_text.trim(), want: [...st.want], want_text: st.want_text.trim() };
  }

  /* ---------- 畫面 ---------- */
  const TITLES = { 1: '整體來說，你滿意嗎？', 2: '哪些功能對你最實用？', 3: '哪些功能最需要優化或改善？', 4: '最希望我們新增什麼？' };
  const HINTS = {
    1: '填完 4 題就送你 7 天 Plus。點一顆星，1 顆最不滿意、5 顆最滿意。',
    2: '先點左側導覽的大項（最多 5 個），再點開它底下的小項，想選幾個都可以。',
    3: '同樣先點大項（最多 5 個）再選小項，下面可以補一行說明。',
    4: '可多選，選項裡沒有的寫在下面。',
  };
  function build() {
    if (ov) ov.remove();
    ov = document.createElement('div'); ov.id = 'svOv'; ov.className = 'svov';
    ov.innerHTML = '<div class="svbox" role="dialog" aria-modal="true" aria-labelledby="svTitle" tabindex="-1"></div>';
    document.body.appendChild(ov);
    ov.addEventListener('keydown', onKey);
    ov.addEventListener('click', (e) => { if (e.target === ov) later(); });
    paint();
  }
  function paint(keepFocus) {
    const box = ov && ov.querySelector('.svbox'); if (!box) return;
    const body = box.querySelector('.svbody'), top = body ? body.scrollTop : 0;
    if (st.done) { box.innerHTML = successHtml(); const k = box.querySelector('#svOk'); k.addEventListener('click', close); k.focus(); return; }
    box.innerHTML = '<div class="svhd"><div class="svprog" aria-live="polite">第 <b id="svStepNo">' + st.step + '</b> / ' + STEPS + ' 題' + (testMode() ? ' <span class="svtest">測試模式・不會送出</span>' : '') + '</div>' +
      '<button type="button" class="svx" id="svLater" aria-label="稍後再說" title="稍後再說">×</button></div>' +
      '<div class="svbar" aria-hidden="true"><i style="width:' + (st.step / STEPS * 100) + '%"></i></div>' +
      '<div class="svbody"><h2 id="svTitle">' + TITLES[st.step] + '</h2><p class="svhint">' + HINTS[st.step] + '</p>' + stepHtml() +
      '<div class="svwarn" role="alert">' + esc(st.warn) + '</div><div class="sverr" role="alert">' + esc(st.err) + '</div></div>' +
      '<div class="svft"><button type="button" class="svlink" id="svLater2">稍後再說</button><span class="svsp"></span>' +
      (st.step > 1 ? '<button type="button" class="svbtn" id="svPrev">上一步</button>' : '') +
      (st.step < STEPS ? '<button type="button" class="svbtn pri" id="svNext"' + (st.step === 1 && !st.sat ? ' disabled' : '') + '>下一步</button>'
        : '<button type="button" class="svbtn pri" id="svSend"' + (st.busy ? ' disabled' : '') + '>' + (st.busy ? '送出中…' : '送出，領 7 天 Plus') + '</button>') + '</div>' +
      '<div class="svprv"><a href="' + esc(location.pathname) + '#privacy-promo" target="_blank" rel="noopener" id="svPrv">資料怎麼使用</a></div>';
    const nb = box.querySelector('.svbody'); if (nb && keepFocus) nb.scrollTop = top;
    bind(box);
  }
  function starHtml() {
    let h = '<div class="svstars" role="radiogroup" aria-label="滿意度">';
    for (let i = 1; i <= 5; i++) h += '<button type="button" class="svstar' + (i <= st.sat ? ' on' : '') + '" role="radio" aria-checked="' + (i === st.sat) + '" data-sat="' + i + '" aria-label="' + i + ' 顆星，' + SAT_TXT[i - 1] + '">★</button>';
    return h + '</div><div class="svsattx" id="svSatTx">' + (st.sat ? st.sat + ' 顆星：' + SAT_TXT[st.sat - 1] : '尚未選擇') + '</div>';
  }
  function pickHtml(which) {
    const m = st[which], act = st.act[which];
    let h = '<div class="svcount" id="svCnt">已選 <b>' + m.size + '</b> / ' + MAX_P + ' 個大項</div><div class="svgrid" role="group" aria-label="大項（最多 ' + MAX_P + ' 個）">';
    nav.forEach((p) => {
      const on = m.has(p.k), n = on ? m.get(p.k).size : 0;
      h += '<button type="button" class="svpar' + (on ? ' on' : '') + (act === p.k ? ' act' : '') + '" data-par="' + esc(p.k) + '" aria-pressed="' + on + '"><span class="svpt">' + esc(p.t) + '</span>' +
        (n ? '<span class="svbd">' + n + '</span>' : (on && p.subs.length ? '' : '')) + '</button>';
    });
    h += '</div>';
    const cur = nav.find((p) => p.k === act && m.has(p.k));
    if (cur) {
      h += '<div class="svsub" id="svSub"><div class="svsubh">「' + esc(cur.t) + '」的哪些小項？<small>' + (cur.subs.length ? '不限數量，不選也可以' : '這一項沒有小項，已選好了') + '</small></div>';
      if (cur.subs.length) {
        h += '<div class="svchips">' + cur.subs.map((s) => '<button type="button" class="svchip' + (m.get(cur.k).has(s.k) ? ' on' : '') + '" data-sub="' + esc(s.k) + '" aria-pressed="' + m.get(cur.k).has(s.k) + '">' + esc(s.t) + '</button>').join('') + '</div>';
      }
      h += '<button type="button" class="svlink svdrop" data-drop="' + esc(cur.k) + '">取消選「' + esc(cur.t) + '」</button></div>';
    } else if (m.size) h += '<div class="svsub muted">再點一次已選的大項，可看它的小項。</div>';
    return h;
  }
  function stepHtml() {
    if (st.step === 1) return starHtml();
    if (st.step === 2) return pickHtml('useful');
    if (st.step === 3) return pickHtml('improve') + '<label class="svlbl" for="svImp">想補充一句（選填）</label><input id="svImp" class="svin" type="text" maxlength="200" placeholder="例如：圖表載入有點慢" value="' + esc(st.improve_text) + '">';
    return '<div class="svchips big" role="group" aria-label="想新增的功能">' + WANTS.map((w) => '<button type="button" class="svchip' + (st.want.has(w) ? ' on' : '') + '" data-want="' + esc(w) + '" aria-pressed="' + st.want.has(w) + '">' + esc(w) + '</button>').join('') + '</div>' +
      '<label class="svlbl" for="svWant">其他想法（選填）</label><input id="svWant" class="svin" type="text" maxlength="200" placeholder="想要的功能，一行就好" value="' + esc(st.want_text) + '">';
  }
  function successHtml() {
    return '<div class="svok"><div class="svokic" aria-hidden="true">✓</div><h2 id="svTitle">謝謝你的回饋</h2><p class="svokp" id="svOkMsg">' + (st.done.demo ? '預覽測試：已獲得 7 天 Plus（示範）' : '已獲得 7 天 Plus，到 <b>' + esc(st.done.until || '') + '</b>') + '</p>' +
      '<button type="button" class="svbtn pri" id="svOk">好</button></div>';
  }

  function bind(box) {
    const $ = (s) => box.querySelector(s);
    box.querySelectorAll('[data-sat]').forEach((b) => b.addEventListener('click', () => { st.sat = +b.dataset.sat; st.err = ''; paint(); const x = box.querySelector('[data-sat="' + st.sat + '"]'); const y = ov.querySelector('[data-sat="' + st.sat + '"]'); (y || x).focus(); }));
    box.querySelectorAll('[data-par]').forEach((b) => b.addEventListener('click', () => togglePar(b.dataset.par)));
    box.querySelectorAll('[data-sub]').forEach((b) => b.addEventListener('click', () => {
      const w = st.step === 2 ? 'useful' : 'improve', set = st[w].get(st.act[w]); if (!set) return;
      const k = b.dataset.sub; set.has(k) ? set.delete(k) : set.add(k); st.warn = ''; paint(true); ov.querySelector('[data-sub="' + CSS.escape(k) + '"]').focus();
    }));
    box.querySelectorAll('[data-drop]').forEach((b) => b.addEventListener('click', () => {
      const w = st.step === 2 ? 'useful' : 'improve'; st[w].delete(b.dataset.drop); st.act[w] = ''; st.warn = ''; paint(true);
    }));
    box.querySelectorAll('[data-want]').forEach((b) => b.addEventListener('click', () => { const k = b.dataset.want; st.want.has(k) ? st.want.delete(k) : st.want.add(k); paint(true); ov.querySelector('[data-want="' + CSS.escape(k) + '"]').focus(); }));
    const imp = $('#svImp'); if (imp) imp.addEventListener('input', () => { st.improve_text = imp.value; });
    const wt = $('#svWant'); if (wt) wt.addEventListener('input', () => { st.want_text = wt.value; });
    ['#svLater', '#svLater2'].forEach((s) => { const e = $(s); if (e) e.addEventListener('click', later); });
    const nx = $('#svNext'); if (nx) nx.addEventListener('click', () => { if (st.step === 1 && !st.sat) return; st.step++; st.warn = st.err = ''; paint(); focusTitle(); });
    const pv = $('#svPrev'); if (pv) pv.addEventListener('click', () => { st.step--; st.warn = st.err = ''; paint(); focusTitle(); });
    const sd = $('#svSend'); if (sd) sd.addEventListener('click', send);
    const ok = $('#svOk'); if (ok) ok.addEventListener('click', close);
  }
  function focusTitle() { const t = ov && ov.querySelector('#svTitle'); if (t) { t.tabIndex = -1; t.focus({ preventScroll: true }); } }
  function togglePar(k) {
    const w = st.step === 2 ? 'useful' : 'improve', m = st[w];
    if (!m.has(k)) {
      if (m.size >= MAX_P) { st.warn = '最多選 ' + MAX_P + ' 個，請先取消一個再選'; paint(true); return; }
      m.set(k, new Set()); st.act[w] = k; st.warn = '';
    } else if (st.act[w] !== k) { st.act[w] = k; st.warn = ''; }      // 已選但沒展開 → 展開它的小項
    else { m.delete(k); st.act[w] = ''; st.warn = ''; }                  // 已展開再點 → 取消
    paint(true); const b = ov.querySelector('[data-par="' + CSS.escape(k) + '"]'); if (b) b.focus();
  }
  function onKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); st.done ? close() : later(); return; }
    if (e.key !== 'Tab') return;
    const f = [...ov.querySelectorAll('button:not([disabled]),input')].filter((x) => x.offsetParent); if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === ov.querySelector('.svbox'))) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
  function later() { snooze(); close(); }
  function close() { demoForce = false; if (ov) { ov.remove(); ov = null; } shown = false; document.documentElement.classList.remove('svopen'); if (lastFocus && lastFocus.focus) { try { lastFocus.focus(); } catch (e) { /* 略 */ } } }

  async function send() {
    if (st.busy) return;
    if (testMode()) { doneFlag = true; st.done = { demo: true }; paint(); return; }   // 測試模式：假成功，不打後端
    st.busy = true; st.err = ''; paint(true);
    const a = A(); const j = a ? await a.call('/v1/survey/submit', payload()) : null;
    st.busy = false;
    if (j && j.ok) {
      if (!testMode()) doneFlag = true; st.done = { until: j.plus_until || j.until || '' }; if (trial) { trial.survey_done = true; trial.survey_eligible = false; if (j.plus_until) trial.pro_until = j.plus_until; }
      try { window.dispatchEvent(new CustomEvent('tw:survey-done', { detail: { until: j.plus_until || j.until } })); } catch (e) { /* 略 */ }
      paint();
    } else { st.err = (j && (j.error || j.msg || j.message)) ? String(j.error || j.msg || j.message) : '送出失敗，請稍後再試（網路連不到伺服器）'; paint(true); }
  }

  /* ---------- 條件 ---------- */
  function open(opts) {
    if (shown) return;
    demoForce = !!(opts && opts.demo); shown = true; st = fresh(); nav = navList(); lastFocus = document.activeElement;
    document.documentElement.classList.add('svopen'); build();
    const b = ov.querySelector('.svbox'); if (b) b.focus({ preventScroll: true });
  }
  async function check() {
    if (shown || checking || !isHome()) return;
    if (testMode()) { if (!doneFlag) open(); return; }   // 測試模式：不看登入、資格、稍後再說
    const a = A(); if (doneFlag || !a || !a.on() || !a.user() || snoozed()) return;
    if (trial && !trial.survey_eligible) return;
    if (Date.now() - failAt < 300e3) return;   // 後端還沒部署（404）或連不到：靜默，五分鐘內不重打
    checking = true;
    try {
      if (!trial) { const j = await a.call('/v1/me/trial', {}); if (!j || j._s !== 200) { failAt = Date.now(); return; } trial = j; }
      if (trial.survey_eligible && !trial.survey_done && a.user() && isHome() && !snoozed()) open();
    } finally { checking = false; }
  }
  const kick = () => setTimeout(check, 900);
  window.addEventListener('tw:account', (e) => { trial = null; if (e.detail && e.detail.user) kick(); else if (ov) close(); });
  window.addEventListener('hashchange', () => { if (shown && !isHome()) { /* 離開首頁就先收起來，不算稍後再說 */ close(); } else kick(); });
  window.addEventListener('load', kick);
  window.TwSurvey = { check, open, state: () => ({ shown, step: st.step, trial, snoozed: snoozed() }) };
})();
