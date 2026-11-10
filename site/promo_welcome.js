/* ============================================================================
   新會員體驗活動訊息框（site/promo_welcome.js）—— 2026-11-01，Andy 23:30
   Andy 原話：「這是剛開放的體驗，需要寄送通知給每個註冊會員，用訊息框形式出現在首頁；有人體驗到期、
   他再刪掉、再不理，就不會出現這活動；記得要有驚喜，煙火慶祝的特效感覺」。
   顯示條件（全部成立才出現，缺一不顯示，不猜）：
     ① 已登入的註冊會員  ② 在首頁（無 hash／#overview）  ③ 仍在新會員體驗期內（還沒到期）  ④ 這個會員沒按過關閉
   體驗資料來源（依序）：window.TwTrial = { active, until }（until＝毫秒時間戳或 ISO 字串）
                       → 沒有的話讀 grants.js 的 TwGrants.state().me.grants 裡 gid==='welcome' 且 end 還沒到的那筆
                       → 都沒有就不顯示。
   關閉：×／Esc／點遮罩／「不再顯示」都一樣 —— localStorage 記 tw.promoWelcome.off.<email 雜湊>，之後不再出現（沒有「稍後」）。
   驚喜：開啟時 約 2.5 秒 canvas 粒子煙火（5 朵依序綻放、只用一支 rAF、播完把 canvas 縮到 0 並移除）。
         prefers-reduced-motion → 不放煙火、不彈入，卡片上緣一條靜態彩帶。
   對外：window.TwPromoWelcome = { check(), close(remember), isOpen() }；事件 'tw:trial' 可叫它重算。
   ============================================================================ */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ls = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } },
  };
  const DAY = 86400000;
  const P = { seq: 0, srv: null, el: null, fx: null, raf: 0, played: false, lastFocus: null, timer: 0 };

  const reduced = () => { try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } };
  const tpe = (ms) => { const d = new Date(ms + 8 * 3600000); return { m: d.getUTCMonth() + 1, d: d.getUTCDate() }; };
  const md = (ms) => { const t = tpe(ms); return `${t.m}/${t.d}`; };
  function fnv(s) { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h.toString(16); }

  function email() { const a = window.TwAccount; try { const u = a && a.on && a.on() && a.user && a.user(); return u && u.email ? String(u.email).toLowerCase() : ''; } catch (e) { return ''; } }
  const offKey = (em) => 'tw.promoWelcome.off.' + fnv(em);
  /* 體驗截止時間（毫秒，含截止日當天結束前）；沒有有效體驗回 0 */
  function trialEnd() {
    const T = window.TwTrial;
    if (T && typeof T === 'object') {
      if (!T.active) return 0;
      const u = typeof T.until === 'number' ? T.until : Date.parse(T.until);
      return u > Date.now() ? u : 0;
    }
    try {
      const G = window.TwGrants && window.TwGrants.state && window.TwGrants.state();
      const w = G && G.me && (G.me.grants || []).find((g) => g.gid === 'welcome' && g.end > Date.now() && g.start <= Date.now() + 60000);
      return w ? w.end : 0;
    } catch (e) { return 0; }
  }
  const onHome = () => { const h = location.hash || ''; return h === '' || h === '#' || h === '#/' || /^#overview(\/|\?|$)/.test(h); };
  /* 同意橫幅／導覽正在跑時先讓路，等它們結束（事件或定時重算）再出現 */
  const busy = () => !!(document.documentElement.classList.contains('svopen') || document.getElementById('twTour') || document.querySelector('.lgmask:not([hidden])'));

  /* 後端為準（POST /v1/ann/state → {seen, trial:{active,until,end}}；契約 docs/api/20261101_member_promo.md），localStorage 只是快取。
     後端還沒部署（404）、沒網路、回不是 200 → 退回 localStorage＋window.TwTrial／grants。 */
  const AID = 'launch-1101';
  async function fetchSrv(em) {
    if (P.srv && P.srv.em === em) return P.srv.d;
    let d = null;
    try {
      const a = window.TwAccount, r = a && a.call ? await a.call('/v1/ann/state', { aid: AID }) : null;
      if (r && r._s === 200 && r.trial) d = r;
    } catch (e) { d = null; }
    P.srv = { em, d };
    return d;
  }
  function srvEnd(t) {
    if (!t || !t.active) return 0;
    let u = typeof t.end === 'number' ? t.end : 0;
    if (!u && t.until) { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(t.until); u = m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) - 8 * 3600000 + DAY : Date.parse(t.until); }
    return u > Date.now() ? u : 0;
  }
  /* 測試模式（Andy 11-02「幫我改成直接可以測試預覽」；不改正式規則）：
     ① 預覽版（網址含 /preview/）：只有網址帶 ?promo=test 才強制跳出（11-09 Andy：以前每個預覽都硬跳，擋住要看的功能）；
        跳出時不論登入、體驗到期、關過與否；
     ③ 與使用者問卷（survey.js）同一次載入最多開一個：問卷開著（html.svopen）就等，問卷關掉（tw:survey-closed）後才判斷；
     ② 正式站：網址帶 ?promo=test 且是站主帳號（TwAccount.user().admin）才強制顯示；一般使用者帶參數無效。
     測試模式關閉不寫 localStorage、不打 /v1/ann/dismiss，重新整理就再出現。 */
  function testMode() {
    if (/\/preview\//.test(location.pathname || '')) return /[?&#]promo=test(&|$)|[?&]promo=test(&|$)/.test((location.search || '') + '&' + ((location.hash || '').split('?')[1] || ''));
    try {
      const a = window.TwAccount, u = a && a.on && a.on() && a.user && a.user();
      return !!(u && u.admin && /[?&]promo=test(&|$)/.test(location.search || ''));
    } catch (e) { return false; }
  }
  async function check() {
    const em = email(), tm = testMode();
    if (P.forced && P.el) return true;   // 展示頁強制開的，不被「不在首頁」收掉
    if (P.testClosed && tm) return false;
    if ((!em && !tm) || !onHome()) { if (P.el) hide(); return false; }
    if (P.el) return true;
    if (tm) {
      if (busy()) { schedule(1500); return false; }
      const real = em ? trialEnd() : 0;
      show(em, real || Date.now() + 9 * DAY, { test: true, demo: !real }); return true;
    }
    const seq = ++P.seq, d = await fetchSrv(em);
    if (seq !== P.seq || P.el || email() !== em || !onHome()) return false;
    let end;
    if (d) { if (d.seen) { ls.set(offKey(em), '1'); return false; } end = srvEnd(d.trial); }
    else end = trialEnd();
    if (!end || ls.get(offKey(em)) === '1') return false;
    if (busy()) { schedule(1500); return false; }
    show(em, end); return true;
  }
  function schedule(ms) { clearTimeout(P.timer); P.timer = setTimeout(check, ms); }

  // ------------------------------------------------------------------ 訊息框
  function show(em, end, opt) {
    opt = opt || {};
    P.test = !!opt.test;
    const left = Math.max(1, Math.ceil((end - Date.now()) / DAY));
    const still = reduced();
    const ov = document.createElement('div');
    ov.id = 'pwOv'; ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true'); ov.setAttribute('aria-labelledby', 'pwTitle');
    if (still) ov.classList.add('pw-still');
    const rib = ['#8FB2F2', '#37B6E8', '#F5C451', '#C9B8FF', '#5FD0C0', '#F2A65A'].map((c) => `<i style="background:${c}"></i>`).join('');
    ov.innerHTML = `<div class="pw-card" data-em="">
      <div class="pw-rib" aria-hidden="true">${rib}</div>
      <button type="button" class="pw-x" aria-label="關閉並不再顯示">×</button>
      <div class="pw-head"><img class="pw-bibi" src="promo_welcome_bibi.png" alt="" width="76" height="76">
        <div><h2 class="pw-title" id="pwTitle">歡迎加入，體驗開跑</h2>
        <p class="pw-sub">你的新會員體驗到 <b>${esc(md(end - 1))}</b> 截止（臺北時間），還有 <b>${left}</b> 天。</p></div></div>
      <ul class="pw-list">
        <li><span class="pw-n">1</span><span><b>新會員註冊即享 14 天體驗</b><small>免綁卡、到期不扣款，結束後回到註冊會員額度。</small></span></li>
        <li><span class="pw-n">2</span><span><b>體驗到期前填問卷，送 7 天 Plus</b><small>你的想法會直接影響我們接下來先做什麼。</small></span></li>
        <li><span class="pw-n">3</span><span><b>邀請好友，你和好友各得 14 天 Plus</b><small>好友用你的邀請碼註冊即可。累計成功邀請 5 位好友，升級 Pro 7 天；Pro 可許一個客製化功能的願望。</small></span></li>
      </ul>
      <div class="pw-btns"><button type="button" class="pw-pri" data-go="trial">看我的體驗</button><button type="button" data-go="invite">邀請好友</button></div>
      <button type="button" class="pw-off">不再顯示</button>
      ${opt.test ? '<span class="pw-tag">預覽測試' + (opt.demo ? '（示範日期）' : '') + '</span>' : ''}
    </div>`;
    document.body.appendChild(ov); P.el = ov; P.lastFocus = document.activeElement;
    ov.addEventListener('click', (e) => {
      if (e.target === ov) return close(true);
      const t = e.target.closest('button'); if (!t) return;
      if (t.classList.contains('pw-x') || t.classList.contains('pw-off')) return close(true);
      if (t.dataset.go) go(t.dataset.go);
    });
    ov.addEventListener('keydown', trap);
    document.addEventListener('keydown', onKey, true);
    requestAnimationFrame(() => { ov.classList.add('on'); const b = ov.querySelector('.pw-pri'); if (b) b.focus({ preventScroll: true }); });
    if (!still && (!P.played || P.test)) { P.played = true; fireworks(); }
  }
  function go(which) {
    close(true);
    if (which === 'trial') { location.hash = '#pricing'; return; }
    /* 邀請好友：會員中心的邀請碼區（另一位同事做）。有 TwMemberCenter 就開到邀請區，沒有就開帳號選單（會員中心入口） */
    if (window.TwInvite && typeof window.TwInvite.open === 'function') { window.TwInvite.open(); return; }   // 帳號選單的「邀請好友／許願」對話框
    const M = window.TwMemberCenter;
    if (M && typeof M.open === 'function') { M.open('invite'); return; }
    const b = document.querySelector('#acctBar .abtn.ame, .abtn.ame');
    if (b) b.click(); else location.hash = '#pricing';
  }
  function onKey(e) { if (e.key === 'Escape' && P.el) { e.stopPropagation(); close(true); } }
  function trap(e) {
    if (e.key !== 'Tab' || !P.el) return;
    const f = [...P.el.querySelectorAll('button')].filter((b) => b.offsetParent !== null); if (!f.length) return;
    const a = document.activeElement, first = f[0], last = f[f.length - 1];
    if (e.shiftKey && a === first) { e.preventDefault(); last.focus(); } else if (!e.shiftKey && a === last) { e.preventDefault(); first.focus(); }
  }
  function hide() {
    P.forced = false;
    stopFx();
    document.removeEventListener('keydown', onKey, true);
    if (P.el) { P.el.remove(); P.el = null; }
  }
  function close(remember) {
    if (P.test) { P.testClosed = true; remember = false; }   // 測試模式：不記錄
    if (remember) {
      const em = email();
      if (em) { ls.set(offKey(em), '1'); try { const a = window.TwAccount; if (a && a.call) Promise.resolve(a.call('/v1/ann/dismiss', { aid: AID })).catch(() => {}); } catch (e) { /* 後端沒部署：只有本機記住 */ } }
    }
    const lf = P.lastFocus; hide();
    try { if (lf && lf.focus && document.contains(lf)) lf.focus({ preventScroll: true }); } catch (e) { /* 略 */ }
  }

  // ------------------------------------------------------------------ 煙火（canvas 粒子，播完釋放）
  const DUR = 2000;
  function palette() {
    let a = '#8FB2F2'; try { a = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || a; } catch (e) { /* 略 */ }
    return [a, '#37B6E8', '#F5C451', '#C9B8FF', '#5FD0C0', '#FFFFFF'];   // 主色＋青＋金＋淡紫＋薄荷＋白；刻意不放紅／綠（紅漲綠跌）
  }
  function fireworks() {
    const cv = document.createElement('canvas'); cv.id = 'pwFx'; cv.setAttribute('aria-hidden', 'true');
    (P.el || document.body).insertBefore(cv, (P.el || document.body).firstChild); P.fx = cv;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let W = window.innerWidth, H = window.innerHeight;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); cv.style.width = W + 'px'; cv.style.height = H + 'px';
    const ctx = cv.getContext('2d'); ctx.scale(dpr, dpr);
    const cols = palette();
    const small = W < 641, N = small ? 40 : 64;
    /* 5 朵依序：左上、右上、中上、左中、右中（避開正中央卡片也沒關係，煙火在卡片後面） */
    const shots = [[.22, .3, 0], [.78, .26, 280], [.5, .2, 560], [.14, .55, 840], [.86, .5, 1120]];
    const rockets = shots.map((s) => ({ x: s[0] * W, ty: s[1] * H, at: s[2], y: H, vy: 0, done: false, col: cols[(Math.random() * 5) | 0] }));
    const pool = []; for (let i = 0; i < N * 5; i++) pool.push({ on: false, x: 0, y: 0, vx: 0, vy: 0, life: 0, max: 1, c: '#fff', r: 2 });
    let t0 = 0, last = 0;
    const burst = (x, y, c) => {
      let k = 0;
      for (const p of pool) {
        if (p.on) continue; if (k++ >= N) break;
        const a = Math.random() * Math.PI * 2, sp = (small ? 90 : 130) * (0.35 + Math.random() * .75);
        p.on = true; p.x = x; p.y = y; p.vx = Math.cos(a) * sp; p.vy = Math.sin(a) * sp; p.life = 0; p.max = 0.8 + Math.random() * .5;
        p.c = Math.random() < .55 ? c : cols[(Math.random() * cols.length) | 0]; p.r = 2 + Math.random() * 2;
      }
    };
    function frame(ts) {
      if (!P.fx) return;
      if (!t0) { t0 = ts; last = ts; }
      const el = ts - t0, dt = Math.min(.05, (ts - last) / 1000); last = ts;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter';
      for (const r of rockets) {
        if (r.done || el < r.at) continue;
        const k = Math.min(1, (el - r.at) / 360);
        const y = H + (r.ty - H) * (1 - Math.pow(1 - k, 2));
        ctx.globalAlpha = .9; ctx.fillStyle = r.col; ctx.fillRect(r.x - 1.2, y, 2.4, 14 * (1 - k * .6));
        if (k >= 1) { r.done = true; burst(r.x, r.ty, r.col); }
      }
      let alive = 0;
      for (const p of pool) {
        if (!p.on) continue;
        p.life += dt; if (p.life >= p.max) { p.on = false; continue; }
        alive++;
        p.vx *= .985; p.vy = p.vy * .985 + 120 * dt; p.x += p.vx * dt; p.y += p.vy * dt;
        const a = 1 - p.life / p.max;
        ctx.globalAlpha = Math.min(1, a * 1.4); ctx.fillStyle = p.c;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r * (0.6 + .4 * a), 0, 6.2832); ctx.fill();
      }
      ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
      const pending = rockets.some((r) => !r.done);
      if (pending || alive || el < DUR) P.raf = requestAnimationFrame(frame); else stopFx();
    }
    P.raf = requestAnimationFrame(frame);
    P.kill = setTimeout(stopFx, DUR + 2500);   // 保底：機器很忙 rAF 被拖慢時，最晚這時一定釋放 canvas
  }
  function stopFx() {
    clearTimeout(P.kill);
    if (P.raf) { cancelAnimationFrame(P.raf); P.raf = 0; }
    if (P.fx) { P.fx.width = 0; P.fx.height = 0; P.fx.remove(); P.fx = null; }
  }


  // ------------------------------------------------------------------ 預覽版展示頁 #promo-demo（只在 /preview/ 路徑；正式站這個路由不存在）
  /* Andy 11-02：「我要先看到預覽畫面…直接讓我都看得到」。三顆大按鈕：公告（含煙火）、邀請碼／許願視窗（假資料）、到期前問卷。 */
  function force() {
    P.testClosed = false; hide(); P.forced = true;
    show(email(), Date.now() + 9 * DAY, { test: true, demo: true });
  }
  if (/\/preview\//.test(location.pathname || '')) {
    (window.TwSubRoutes = window.TwSubRoutes || []).push((head) => {
      if (head !== 'promo-demo') return null;
      let v = document.getElementById('v-promodemo');
      if (!v) { const main = document.querySelector('main'); if (!main) return null; v = document.createElement('section'); v.className = 'view'; v.id = 'v-promodemo'; main.insertBefore(v, document.getElementById('siteFoot') || null); }
      v.innerHTML = `<div class="card pd"><h3>活動預覽展示</h3><p class="muted">這一頁只有預覽版才有。三顆鈕都用示範資料，按了不會寫入任何真實資料。</p>
        <div class="pd-btns"><button type="button" class="pd-b" style="min-height:64px!important" data-pd="promo">看活動公告（含煙火）</button>
        <button type="button" class="pd-b" style="min-height:64px!important" data-pd="invite">看邀請碼／許願視窗</button>
        <button type="button" class="pd-b" style="min-height:64px!important" data-pd="survey">看到期前問卷</button></div><p class="pd-msg" id="pdMsg" role="status"></p></div>`;
      if (!v.dataset.bound) {
        v.dataset.bound = '1';
        v.addEventListener('click', (e) => {
          const b = e.target.closest('[data-pd]'); if (!b) return;
          const msg = document.getElementById('pdMsg'); if (msg) msg.textContent = '';
          if (b.dataset.pd === 'promo') force();
          else if (b.dataset.pd === 'invite') { if (window.TwInvite && window.TwInvite.open) window.TwInvite.open({ demo: true }); else if (msg) msg.textContent = '邀請視窗還沒上預覽。'; }
          else if (window.TwSurvey && window.TwSurvey.open) window.TwSurvey.open({ demo: true });
          else if (msg) msg.textContent = '問卷製作中：做好並部署到預覽後，這顆鈕會直接打開問卷（示範資料）。';
        });
      }
      return 'v-promodemo';
    });
  }

  // ------------------------------------------------------------------ 觸發
  window.addEventListener('tw:account', () => { P.srv = null; });
  ['tw:account', 'tw:grants', 'tw:trial', 'hashchange'].forEach((ev) => window.addEventListener(ev, () => schedule(ev === 'hashchange' ? 200 : 600)));
  window.addEventListener('tw:tour', () => schedule(800));
  window.addEventListener('tw:survey-closed', () => schedule(600));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => schedule(1200)); else schedule(1200);
  window.TwPromoWelcome = { check, force, close, isOpen: () => !!P.el, offKey, email };
})();
