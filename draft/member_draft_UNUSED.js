/* ============================================================================
   會員中心：到期前意見檢核表（送 7 天）＋好友邀請碼（送 14 天 Pro 體驗）＋許願（site/member.js）—— 2026-11-01
   ----------------------------------------------------------------------------
   Andy 11-01：「快到期時打開首頁會跳出意見檢核表，填完再送 7 天。…哪個功能實用，要給出總覽、財經日報、產業地圖、ETF…等等側邊的母分頁，
   點擊該功能會再跳出子分頁讓他選取。最多 5 個母分頁，子分頁不限」「好友邀請：每人有邀請碼，另一個人使用就送 14 天 Pro 體驗（可以提一個願望）」。
   ★ 全部由 account-api 驗證（/v1/promo/state、/v1/survey/submit、/v1/invite/redeem、/v1/wish/put）；這支只是畫面，前端擋不住的事後端都會再擋。
   ★ 母分頁與子分頁**動態讀側邊欄**（layout4.js 的 window.TwL4Nav：GROUPS／PAGES／SUBS_DESK），不寫死；側邊欄加頁，問卷自動跟著多一個選項。
   對外：window.TwMember = { menuHTML, state, openSurvey, pages }
        window.TwTrial = { active, until }   —— 目前是否在新會員體驗期內與截止日（台北 YYYY-MM-DD）。給首頁活動公告用；事件 'tw:trial'。
   路由：#member（TwSubRoutes）。問卷自動跳出：新會員體驗剩 ≤3 天、還沒填、停在首頁（#overview 或空網址），「稍後再說」24 小時不再跳；到期後不再跳。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const A = () => window.TwAccount || null;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } }, del(k) { try { localStorage.removeItem(k); } catch (e) { /* 略 */ } } };
  const DAY = 86400000, MAXP = 5;
  const S = { st: null, busy: false, loading: false, who: '' };
  const logged = () => { const a = A(); return !!(a && a.on && a.on() && a.user && a.user()); };
  const ymd = (ms) => new Date(ms + 8 * 3600000).toISOString().slice(0, 10);
  const origin = () => (location.origin && location.origin !== 'null' ? location.origin : 'https://liguligu-puipui.com');
  const linkOf = (code) => origin() + '/?invite=' + code;

  /* ---------------- window.TwTrial（給首頁活動公告讀）---------------- */
  window.TwTrial = { active: false, until: '' };
  function pubTrial() {
    const w = S.st && S.st.welcome;
    const next = { active: !!(w && w.end > Date.now()), until: w ? ymd(w.end - 1) : '' };
    const changed = next.active !== window.TwTrial.active || next.until !== window.TwTrial.until;
    window.TwTrial.active = next.active; window.TwTrial.until = next.until;
    if (changed) window.dispatchEvent(new CustomEvent('tw:trial', { detail: next }));
  }

  /* ---------------- 側邊欄 → 母分頁／子分頁（動態讀）---------------- */
  function pages() {
    const N = window.TwL4Nav; if (!N || !N.GROUPS) return [];
    const out = [], seen = new Set();
    for (const g of N.GROUPS) for (const v of g.views) {
      if (seen.has(v) || v === 'admin' || v === 'delivery' || !N.PAGES[v]) continue;
      seen.add(v);
      out.push({ k: v, t: N.PAGES[v].t, subs: ((N.SUBS_DESK || N.SUBS || {})[v] || []).map((s) => ({ k: s.k, t: s.t })) });
    }
    return out;
  }
  const pageName = (k) => { const p = pages().find((x) => x.k === k); return p ? p.t : k; };

  /* ---------------- 選擇器：母分頁（最多 5）→ 點了展開子分頁（不限）---------------- */
  function picker(host, id, init) {
    const list = pages(), sel = new Map();
    (init || []).forEach((it) => sel.set(it.p, new Set(it.s || [])));
    const paint = () => {
      host.innerHTML = `<div class="pkn" id="${id}N" aria-live="polite">已選 ${sel.size}／${MAXP} 個母分頁</div>`
        + `<div class="pkc" role="group" aria-label="母分頁">${list.map((p) => `<button type="button" class="pkchip" data-p="${esc(p.k)}" aria-pressed="${sel.has(p.k)}">${esc(p.t)}${p.subs.length && sel.has(p.k) ? ` <i>${sel.get(p.k).size || '全'}</i>` : ''}</button>`).join('')}</div>`
        + `<div class="pkmsg" id="${id}M" role="alert"></div>`
        + [...sel.keys()].map((k) => { const p = list.find((x) => x.k === k); if (!p || !p.subs.length) return ''; return `<div class="pksub" data-for="${esc(k)}"><b>「${esc(p.t)}」的子分頁</b><small>（可多選，不選＝整個「${esc(p.t)}」）</small><div class="pksl">${p.subs.map((s) => `<label class="pks"><input type="checkbox" data-s="${esc(s.k)}"${sel.get(k).has(s.k) ? ' checked' : ''}><span>${esc(s.t)}</span></label>`).join('')}</div></div>`; }).join('');
    };
    host.addEventListener('click', (e) => {
      const b = e.target.closest('.pkchip'); if (!b) return;
      const k = b.dataset.p, msg = () => host.querySelector('.pkmsg');
      if (sel.has(k)) sel.delete(k);
      else if (sel.size >= MAXP) { paint(); msg().textContent = `最多選 ${MAXP} 個母分頁，請先點一下已選的取消一個`; return; }
      else sel.set(k, new Set());
      paint();
      const f = host.querySelector(`.pksub[data-for="${CSS.escape(k)}"] input`); if (f && sel.has(k)) f.closest('.pksub').scrollIntoView({ block: 'nearest' });
    });
    host.addEventListener('change', (e) => {
      const c = e.target.closest('input[data-s]'); if (!c) return;
      const k = c.closest('.pksub').dataset.for, set = sel.get(k); if (!set) return;
      if (c.checked) set.add(c.dataset.s); else set.delete(c.dataset.s);
      const chip = host.querySelector(`.pkchip[data-p="${CSS.escape(k)}"]`); if (chip) chip.innerHTML = `${esc(pageName(k))} <i>${set.size || '全'}</i>`;
    });
    paint();
    return { value: () => [...sel].map(([p, s]) => ({ p, s: [...s] })), size: () => sel.size };
  }

  function css() {
    if (!T()) return;
    T().css('memCss', `
.svov{position:fixed;inset:0;z-index:1450;display:grid;place-items:center;background:rgba(3,6,14,.6);padding:16px}
.svov[hidden]{display:none}
.svbox{width:min(640px,100%);max-height:calc(100vh - 32px);overflow:auto;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:14px;padding:20px 22px;box-shadow:0 18px 50px rgba(0,0,0,.5)}
.svbox h3{margin:0 0 4px;font-size:19px}
.svbox .svlead{margin:0 0 12px;font-size:14px;line-height:1.65;color:var(--ink-2)}
.svq{margin:16px 0 0;padding-top:14px;border-top:1px solid var(--line)}
.svq>b{display:block;font-size:15px;margin-bottom:6px}
.svq small{color:var(--ink-2);font-size:12.5px}
.svstars{display:flex;gap:6px}
.svstars button{width:44px;height:44px;font-size:26px;line-height:1;border-radius:10px;border:1px solid var(--line-2);background:var(--panel);color:var(--ink-2);cursor:pointer}
.svstars button.on{color:#f5b301;border-color:#f5b301;background:rgba(245,179,1,.12)}
.svbox textarea,.svbox input[type=text],.mem textarea,.mem input[type=text],.mem select{width:100%;box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:8px 10px;font-size:14px;font-family:inherit}
.svbox textarea,.mem textarea{min-height:64px;resize:vertical;margin-top:8px}
.pkn{font-size:13px;color:var(--ink-2);margin:2px 0 6px}
.pkc{display:flex;flex-wrap:wrap;gap:8px}
.pkchip{min-height:36px;padding:0 14px;border-radius:18px;border:1px solid var(--line-2);background:var(--panel);color:var(--ink);font-size:14px;cursor:pointer}
.pkchip[aria-pressed=true]{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
.pkchip i{font-style:normal;font-size:12px;opacity:.85}
.pkmsg{min-height:1.3em;font-size:13px;color:var(--rise);margin-top:6px}
.pksub{margin-top:8px;padding:10px 12px;border:1px solid var(--line-2);border-radius:10px;background:var(--panel)}
.pksub b{font-size:14px}
.pksl{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:8px}
.pks{display:flex;align-items:center;gap:6px;font-size:14px;min-height:32px;cursor:pointer}
.pks input{width:18px;height:18px}
.svopt{display:flex;flex-wrap:wrap;gap:8px}
.svopt button{min-height:36px;padding:0 14px;border-radius:18px;border:1px solid var(--line-2);background:var(--panel);color:var(--ink);font-size:14px;cursor:pointer}
.svopt button[aria-pressed=true]{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
.svfoot{display:flex;gap:10px;justify-content:flex-end;align-items:center;flex-wrap:wrap;margin-top:18px}
.svfoot .msg{flex:1 1 100%;font-size:13.5px;min-height:1.2em;color:var(--rise)}
.svfoot button,.mem .mb{height:38px;padding:0 18px;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:14px;cursor:pointer}
.svfoot button.pri,.mem .mb.pri{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
.svfoot button:disabled,.mem .mb:disabled{opacity:.5;cursor:default}
#v-member .mem{display:grid;gap:14px;max-width:760px;margin-top:16px}
#v-member .mc{border:1px solid var(--line-2);border-radius:12px;padding:16px 18px;background:var(--panel)}
#v-member .mc h3{margin:0 0 6px;font-size:16px}
#v-member .mc p{margin:6px 0;font-size:14px;line-height:1.65;color:var(--ink-2)}
#v-member .mc .big{font:700 26px/1.2 ui-monospace,Menlo,Consolas,monospace;letter-spacing:.12em;color:var(--ink);margin:8px 0}
#v-member .mc .lnk{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#v-member .mc .lnk code{flex:1 1 220px;min-width:0;overflow-wrap:anywhere;font-size:13px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel-2)}
#v-member .mc .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
#v-member .mc .st{font-size:13.5px;min-height:1.2em;margin-top:6px}
#v-member .mc .st.bad{color:var(--rise)}#v-member .mc .st.ok{color:var(--fall)}
#v-member .wl{list-style:none;margin:10px 0 0;padding:0;display:grid;gap:6px;font-size:13.5px}
#v-member .wl li{padding:8px 10px;border:1px solid var(--line);border-radius:8px}
@media (max-width:640px){
 .svbox{padding:16px 14px;border-radius:14px}
 .svstars button{width:48px;height:48px}
 .pkchip,.svopt button{min-height:40px;font-size:14px}
 .pks{min-height:40px}
 .svfoot button,#v-member .mem .mb{flex:1 1 auto;height:44px}
 #v-member .mc{padding:14px}
 #v-member .mc .big{font-size:24px}
}`);
  }

  /* ---------------- 狀態 ---------------- */
  async function load(force) {
    const a = A();
    if (!logged()) { S.st = null; S.who = ''; pubTrial(); return null; }
    if (S.loading && !force) return S.st;
    S.loading = true;
    try {
      const j = await a.call('/v1/promo/state', {});
      S.st = j && j._s === 200 ? j : null;     // 後端還沒部署（404）或連不到：當作沒有這個功能，什麼都不顯示
      S.who = (a.user() || {}).email || '';
    } finally { S.loading = false; }
    pubTrial();
    window.dispatchEvent(new CustomEvent('tw:member', { detail: S.st }));
    return S.st;
  }

  /* ---------------- 意見檢核表 ---------------- */
  const IDEAS = ['更多即時資料', '到價／事件提醒', '自訂選股條件', '更多圖表與比較', '手機操作更順', '更多文章與教學', '其他'];
  function openSurvey(manual) {
    css();
    const st = S.st; if (!st || !st.survey || !st.survey.eligible) return;
    let d = document.getElementById('svDlg');
    if (d) d.remove();
    d = document.createElement('div'); d.id = 'svDlg'; d.className = 'svov'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true'); d.setAttribute('aria-label', '意見檢核表');
    const until = st.welcome ? ymd(st.welcome.end - 1) : '';
    d.innerHTML = `<div class="svbox"><h3>意見檢核表</h3>
      <p class="svlead">你的新會員體驗 ${esc(until)} 到期。花 1 分鐘告訴我們哪裡好、哪裡不好，<b>送出就再送 ${st.survey.bonusDays || 7} 天</b>（每人一次）。</p>
      <div class="svq"><b>1. 整體來說，你滿意嗎？</b><div class="svstars" id="svStars" role="radiogroup" aria-label="滿意度 1 到 5 星">${[1, 2, 3, 4, 5].map((n) => `<button type="button" role="radio" aria-checked="false" aria-label="${n} 星" data-n="${n}">★</button>`).join('')}</div></div>
      <div class="svq"><b>2. 哪些功能最實用？</b><small>先點母分頁（最多 ${MAXP} 個），會跳出它的子分頁讓你勾</small><div id="svU"></div></div>
      <div class="svq"><b>3. 哪些功能最需要優化或改善？</b><small>同樣最多 ${MAXP} 個母分頁，可不選</small><div id="svI"></div><textarea id="svIn" maxlength="200" placeholder="哪裡不好用？一句話就好（選填，200 字內）" aria-label="需要改善的地方"></textarea></div>
      <div class="svq"><b>4. 最希望新增什麼功能？</b><small>選一個方向，再補一句（選填）</small><div class="svopt" id="svW">${IDEAS.map((t) => `<button type="button" aria-pressed="false">${esc(t)}</button>`).join('')}</div><textarea id="svWn" maxlength="300" placeholder="你希望多什麼？（選填，300 字內）" aria-label="希望新增的功能"></textarea></div>
      <div class="svfoot"><div class="msg" id="svMsg" role="alert"></div><button type="button" id="svLater">稍後再說</button><button type="button" class="pri" id="svGo">送出，領 ${st.survey.bonusDays || 7} 天</button></div></div>`;
    document.body.appendChild(d);
    let stars = 0;
    const pu = picker(d.querySelector('#svU'), 'svU'), pi = picker(d.querySelector('#svI'), 'svI');
    let idea = '';
    const msg = (t) => { d.querySelector('#svMsg').textContent = t || ''; };
    d.querySelector('#svStars').addEventListener('click', (e) => {
      const b = e.target.closest('button[data-n]'); if (!b) return;
      stars = +b.dataset.n;
      d.querySelectorAll('#svStars button').forEach((x) => { const on = +x.dataset.n <= stars; x.classList.toggle('on', on); x.setAttribute('aria-checked', String(+x.dataset.n === stars)); });
    });
    d.querySelector('#svW').addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      idea = idea === b.textContent ? '' : b.textContent;
      d.querySelectorAll('#svW button').forEach((x) => x.setAttribute('aria-pressed', String(x.textContent === idea)));
    });
    const close = () => d.remove();
    d.querySelector('#svLater').onclick = () => { if (!manual) ls.set('tw.sv.snooze', String(Date.now() + DAY)); close(); };
    d.addEventListener('keydown', (e) => { if (e.key === 'Escape') d.querySelector('#svLater').click(); });
    d.querySelector('#svGo').onclick = async () => {
      if (!stars) return msg('請先給個星等（第 1 題）');
      if (!pu.size()) return msg('第 2 題請至少選一個最實用的母分頁');
      const btn = d.querySelector('#svGo'); btn.disabled = true; msg('送出中…');
      const j = await A().call('/v1/survey/submit', { stars, useful: pu.value(), improve: pi.value(), improve_note: d.querySelector('#svIn').value, wish_feat: idea, wish_note: d.querySelector('#svWn').value });
      if (j && j._s === 200 && j.ok) {
        close(); ls.del('tw.sv.snooze');
        await load(true);
        try { if (window.TwGrants && window.TwGrants.refresh) window.TwGrants.refresh(true); } catch (e) { /* 略 */ }
        T().toast(`謝謝你的意見！體驗已延長 ${j.bonusDays} 天，新的截止日 ${ymd(j.end - 1)}`);
        if ((location.hash || '').startsWith('#member')) paintMember();
      } else {
        btn.disabled = false;
        msg({ done: '你已經填過了，每人只能領一次', no_trial: '新會員體驗已到期或沒有體驗，無法再延長', bad_pick: '母分頁最多選 5 個', need_useful: '第 2 題請至少選一個' }[j && j.error] || '送出失敗，請稍後再試');
        if (j && (j.error === 'done' || j.error === 'no_trial')) load(true);
      }
    };
    d.querySelector('.svbox').focus && setTimeout(() => d.querySelector('#svStars button').focus(), 30);
  }
  const isHome = () => { const h = location.hash || ''; return h === '' || h === '#' || /^#overview/.test(h); };
  function maybeSurvey() {
    const st = S.st;
    if (!st || !st.survey || !st.survey.due || !isHome() || document.getElementById('svDlg')) return;
    if (Number(ls.get('tw.sv.snooze') || 0) > Date.now()) return;
    openSurvey(false);
  }

  /* ---------------- 邀請碼：?invite=XXXX 帶入、登入後自動領 ---------------- */
  const INVMSG = { self: '這是你自己的邀請碼，不能自己用', used: '你已經用過邀請碼了（每人一次）', not_new: '邀請碼只限註冊 7 天內的新會員使用', already_paid: '你已經是付費會員，不適用邀請碼',
    bad_code: '邀請碼不正確，請再確認一次', same_ip: '這個網路已經有人領過了（同一個網路每 30 天一次），如有疑問請用右下角客服', too_many: '今天試太多次了，請明天再試', no_pro_plan: '目前暫時無法發放，請稍後再試', auth: '請先登入' };
  const TERMINAL = ['self', 'used', 'not_new', 'already_paid', 'bad_code', 'same_ip'];
  async function redeem(code, fromLink) {
    const j = await A().call('/v1/invite/redeem', { code });
    if (j && j._s === 200 && j.ok) {
      ls.del('tw.invite'); await load(true);
      try { if (window.TwPerm && window.TwPerm.refresh) window.TwPerm.refresh(); } catch (e) { /* 略 */ }
      try { window.dispatchEvent(new CustomEvent('tw:perm')); } catch (e) { /* 略 */ }
      T().toast(`邀請碼成功！你獲得 ${j.days} 天 Pro 體驗，到 ${ymd(j.end - 1)}`);
      return { ok: true, end: j.end };
    }
    const err = (j && j.error) || 'net';
    if (TERMINAL.includes(err)) ls.del('tw.invite');
    const text = INVMSG[err] || '暫時無法使用邀請碼，請稍後再試';
    if (fromLink) T().toast(text);
    return { ok: false, text };
  }
  function takeInviteParam() {
    try {
      const u = new URL(location.href), c = (u.searchParams.get('invite') || '').trim();
      if (!c) return;
      if (/^[A-Za-z0-9]{6,12}$/.test(c)) ls.set('tw.invite', c.toUpperCase());
      u.searchParams.delete('invite');
      history.replaceState(null, '', u.pathname + (u.search || '') + u.hash);
    } catch (e) { /* 略 */ }
  }
  async function autoRedeem() {
    const c = ls.get('tw.invite'); if (!c) return;
    if (!logged()) return;
    const st = S.st; if (!st || !st.invite || !st.invite.redeemable) { if (st && st.invite && !st.invite.redeemable) ls.del('tw.invite'); return; }
    await redeem(c, true);
    if ((location.hash || '').startsWith('#member')) paintMember();
  }

  /* ---------------- #member 會員中心 ---------------- */
  function paintMember() {
    const v = T() && T().view('v-member'); if (!v) return;
    css();
    if (!logged()) {
      v.innerHTML = '<div class="card" style="margin-top:16px"><h2>會員中心</h2><p class="muted">登入後可以看到你的邀請碼、新會員體驗與許願。</p><p><button type="button" class="btn" id="memLogin">登入／註冊</button></p></div>';
      v.querySelector('#memLogin').onclick = () => A() && A().login && A().login();
      return;
    }
    const st = S.st;
    if (!st) { v.innerHTML = '<div class="card" style="margin-top:16px"><h2>會員中心</h2><p class="muted">' + (S.loading ? '載入中…' : '讀不到會員資料（伺服器沒回應或功能尚未開放），請稍後再試。') + '</p></div>'; return; }
    const w = st.welcome, sv = st.survey, iv = st.invite, wi = st.wish;
    const trial = w
      ? `<p>你的新會員體驗到 <b>${esc(ymd(w.end - 1))}</b>（還剩 ${Math.max(0, Math.ceil((w.end - Date.now()) / DAY))} 天）。</p>${sv.done ? `<p>意見檢核表已填，謝謝你！已多送 ${sv.bonusDays} 天。</p>` : `<p>填一份 1 分鐘的意見檢核表，<b>再送 ${sv.bonusDays} 天</b>（每人一次）。</p><div class="row"><button type="button" class="mb pri" id="memSv">填意見檢核表</button></div>`}`
      : `<p class="muted">${st.hadWelcome ? '你的新會員體驗已到期。' : '你目前沒有新會員體驗。'}</p>`;
    const redeemed = iv.redeemed
      ? `<p>你已使用邀請碼，Pro 體驗${iv.redeemed.end > Date.now() ? '到 <b>' + esc(ymd(iv.redeemed.end - 1)) + '</b>' : '已於 ' + esc(ymd(iv.redeemed.end - 1)) + ' 結束'}。</p>`
      : iv.redeemable
        ? `<p>有朋友給你邀請碼嗎？註冊 ${iv.newDays} 天內輸入，<b>送你 ${iv.proDays} 天 Pro 體驗</b>（每人一次、不能用自己的碼）。</p><div class="row"><input type="text" id="memCode" maxlength="12" autocomplete="off" placeholder="8 碼邀請碼" aria-label="邀請碼" style="max-width:200px;text-transform:uppercase"><button type="button" class="mb pri" id="memRedeem">領取</button></div><div class="st" id="memRedSt" role="alert"></div>`
        : `<p class="muted">邀請碼只限註冊 ${iv.newDays} 天內的新會員使用一次。</p>`;
    const wishCard = wi.ok
      ? `<div class="mc"><h3>許一個願望</h3><p>Pro 體驗期間，告訴我們你最想要什麼功能，我們會看（最多 ${wi.max} 個）。</p>${wi.list.length < wi.max ? `<label class="muted" for="memWf" style="font-size:13px">想用在哪個功能</label><select id="memWf">${pages().map((p) => `<option>${esc(p.t)}</option>`).join('')}<option>其他</option></select><textarea id="memWb" maxlength="500" placeholder="你想要什麼？（6～500 字）" aria-label="願望內容"></textarea><div class="row"><button type="button" class="mb pri" id="memWgo">送出願望</button></div><div class="st" id="memWst" role="alert"></div>` : '<p class="muted">願望數量已達上限。</p>'}${wi.list.length ? `<ul class="wl">${wi.list.map((x) => `<li><b>${esc(x.feat)}</b>・${esc({ new: '已收到', doing: '製作中', done: '已完成' }[x.status] || '已收到')}<br>${esc(x.body)}</li>`).join('')}</ul>` : ''}</div>`
      : '';
    v.innerHTML = `<div class="mem"><div class="card" style="margin:0"><h2 style="margin:0">會員中心</h2></div>
      <div class="mc"><h3>新會員體驗</h3>${trial}</div>
      <div class="mc"><h3>邀請好友</h3><p>把你的邀請碼或連結傳給朋友，朋友註冊後輸入，<b>朋友獲得 ${iv.proDays} 天 Pro 體驗</b>。已有 ${iv.uses} 位朋友使用。</p>
        <div class="big" id="memCodeShow">${esc(iv.code)}</div>
        <div class="lnk"><code id="memLink">${esc(linkOf(iv.code))}</code><button type="button" class="mb pri" id="memCp">複製連結</button><button type="button" class="mb" id="memCp2">複製邀請碼</button></div><div class="st" id="memCpSt" role="status"></div></div>
      <div class="mc"><h3>輸入邀請碼</h3>${redeemed}</div>${wishCard}</div>`;
    const copy = async (txt, ok) => { const el = v.querySelector('#memCpSt'); try { await navigator.clipboard.writeText(txt); el.className = 'st ok'; el.textContent = ok; } catch (e) { el.className = 'st bad'; el.textContent = '複製失敗，請手動選取上面的文字'; } };
    v.querySelector('#memCp').onclick = () => copy(linkOf(iv.code), '已複製連結，傳給朋友吧');
    v.querySelector('#memCp2').onclick = () => copy(iv.code, '已複製邀請碼 ' + iv.code);
    const b1 = v.querySelector('#memSv'); if (b1) b1.onclick = () => openSurvey(true);
    const b2 = v.querySelector('#memRedeem');
    if (b2) b2.onclick = async () => {
      const el = v.querySelector('#memRedSt'), c = v.querySelector('#memCode').value.trim().toUpperCase();
      if (!c) { el.className = 'st bad'; el.textContent = '請輸入邀請碼'; return; }
      b2.disabled = true; const r = await redeem(c, false);
      if (r.ok) paintMember(); else { b2.disabled = false; el.className = 'st bad'; el.textContent = r.text; }
    };
    const b3 = v.querySelector('#memWgo');
    if (b3) b3.onclick = async () => {
      const el = v.querySelector('#memWst'); b3.disabled = true;
      const j = await A().call('/v1/wish/put', { feat: v.querySelector('#memWf').value, body: v.querySelector('#memWb').value });
      if (j && j._s === 200 && j.ok) { await load(true); T().toast('願望已送出，我們會看'); paintMember(); }
      else { b3.disabled = false; el.className = 'st bad'; el.textContent = { bad_body: '願望內容至少 6 個字', wish_max: '願望數量已達上限', no_pro: 'Pro 體驗已結束，無法再許願' }[j && j.error] || '送出失敗，請稍後再試'; }
    };
  }
  async function showMember() { paintMember(); await load(true); paintMember(); }

  /* ---------------- 選單入口（桌機帳號選單與手機選單共用）---------------- */
  function menuHTML(kind) {
    if (!logged()) return '';
    return kind === 'm4'
      ? '<button type="button" class="m4i" role="menuitem" data-mem="1"><span class="t">會員中心：邀請好友</span></button>'
      : '<button type="button" role="menuitem" data-mem="1">會員中心：邀請好友</button>';
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('#acctMenu [data-mem]'); if (!b) return;
    const m = document.getElementById('acctMenu'); if (m) m.hidden = true;
    location.hash = '#member';
  });

  if (T()) (window.TwSubRoutes = window.TwSubRoutes || []).push((head) => {
    if (head !== 'member' || !T()) return null;
    showMember(); return 'v-member';
  });
  window.addEventListener('tw:account', async () => { S.st = null; pubTrial(); await load(true); maybeSurvey(); autoRedeem(); if ((location.hash || '').startsWith('#member')) paintMember(); });
  window.addEventListener('hashchange', () => { maybeSurvey(); });
  function boot() { takeInviteParam(); if (logged()) load(true).then(() => { maybeSurvey(); autoRedeem(); }); else if (ls.get('tw.invite')) { /* 帶了邀請碼但還沒登入：登入完成後 tw:account 會自動領 */ } }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 600)); else setTimeout(boot, 600);
  window.TwMember = { menuHTML, state: () => S.st, openSurvey: () => openSurvey(true), pages, load };
})();
