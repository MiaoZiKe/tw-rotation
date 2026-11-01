/* ============================================================================
   好友邀請碼＋Pro 許願（2026-11-01）
   ----------------------------------------------------------------------------
   帳號選單（桌機 account.js、手機 acctm4.js 共用一份）多一項「邀請好友／許願」，點開一個對話框：
     ① 我的邀請碼與連結（可複製）、已有幾位朋友用了
     ② 輸入朋友的邀請碼（新會員限定，成功送 14 天 Pro）
     ③ 許願：Pro 體驗期內可送一個願望，之後可再覆寫；顯示處理進度
   後端契約：docs/api/20261101_member_promo.md（分支 wip/member-invite-api）。
     全部是 POST、權杖放本文，用 TwAccount.call()。
   ★ 後端還沒部署時（/v1/invite/me 回 404 或連不到）：選單項目整個不顯示，什麼都不出現
     （跟 billing.js 一樣的「寧可不顯示」；桌機版面一個字都不變，選單收著時不插任何節點）。
   ★ 2026-11-02 Andy：邀請人也有獎勵且可累計（每成功邀 1 人也得 14 天 Pro），畫面不寫上限；顯示 reward_days_total。
   ============================================================================ */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const A = () => window.TwAccount || null;
  const S = { data: null, wish: null, st: 'none', fly: null, who: '' };   // st：none／loading／ok／off（後端沒這支或連不到）
  const day = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10) : '');
  const PRE_K = 'tw.invite.pre';      // 從邀請連結進來的碼，登入後自動帶進輸入框（sessionStorage，只在這個分頁）

  /* 邀請連結 ?invite=XXXX／?inv=／?ref= → 先記下來，登入後預填；網址上的參數不動它 */
  (function grab() {
    try {
      const q = new URLSearchParams(location.search);
      const c = q.get('invite') || q.get('inv') || q.get('ref');
      if (c && /^[A-Za-z0-9]{4,16}$/.test(c)) sessionStorage.setItem(PRE_K, c.toUpperCase());
    } catch (e) { /* 無痕或被擋：略過 */ }
  })();
  const pre = () => { try { return sessionStorage.getItem(PRE_K) || ''; } catch (e) { return ''; } };

  (function css() {
    const s = document.createElement('style'); s.id = 'invCss';
    s.textContent = `#invDlg .box{width:min(560px,100%);font-size:14px}
#invDlg h4{margin:14px 0 6px;font-size:15px}
#invDlg .invcode{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:6px 0}
#invDlg .invcode b{font-size:22px;letter-spacing:.14em;font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--cyan)}
#invDlg .invlink{width:100%;box-sizing:border-box;height:38px;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);padding:0 10px;font-size:13px}
#invDlg input[type=text],#invDlg textarea{width:100%;box-sizing:border-box;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);padding:8px 10px;font-size:14px;font-family:inherit}
#invDlg input[type=text]{height:38px}#invDlg textarea{min-height:84px;resize:vertical;margin-top:6px}
#invDlg .invbtn{height:38px;padding:0 14px;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);font-size:14px;cursor:pointer;flex:0 0 auto}
#invDlg .invbtn.pri{background:var(--cyan);border-color:var(--cyan);color:#04121a;font-weight:700}
#invDlg .invbtn:disabled{opacity:.55;cursor:not-allowed}
#invDlg .invrow{display:flex;gap:8px;align-items:center}#invDlg .invrow input{flex:1 1 auto;min-width:0}
#invDlg .ok{color:var(--green,#2fd18b)}#invDlg .msg{min-height:1.3em;font-size:13px;margin:4px 0 0;color:#ff6b7a}#invDlg .msg.good{color:var(--green,#2fd18b)}
#invDlg .invtag{display:inline-block;padding:1px 8px;border-radius:99px;border:1px solid var(--line-2);font-size:12px;color:var(--ink-2)}
#invDlg .invprog{margin:8px 0}#invDlg .invbar{height:8px;border-radius:99px;background:var(--panel-2);border:1px solid var(--line-2);overflow:hidden;margin-top:6px}#invDlg .invbar i{display:block;height:100%;background:var(--cyan)}
#invDlg .invsec{border-top:1px solid var(--line-2);padding-top:4px;margin-top:12px}
@media (max-width:640px){#invDlg .invbtn{height:44px}#invDlg input[type=text]{height:44px;font-size:16px}#invDlg textarea{font-size:16px}#invDlg .invlink{height:44px;font-size:14px}}`;
    document.head.appendChild(s);
  })();

  function me() { const a = A(); return a && a.on && a.on() ? a.user() : null; }

  function refresh() {
    const u = me();
    if (!u) { S.data = null; S.wish = null; S.st = 'none'; S.who = ''; return Promise.resolve(); }
    const who = String(u.email || '');
    if (S.fly && S.who === who) return S.fly;
    S.who = who; S.st = S.st === 'ok' ? 'ok' : 'loading';
    S.fly = A().call('/v1/invite/me', {}).then(async (j) => {
      if (j && j._s === 200 && j.code) {
        S.data = j; S.st = 'ok';
        const w = await A().call('/v1/wish/mine', {});
        S.wish = w && w._s === 200 ? w : null;
      } else { S.data = null; S.wish = null; S.st = 'off'; }   // 404（後端還沒部署）、連不到 → 當作沒有這功能
      S.fly = null; repaintMenu(); repaintDlg();
    });
    return S.fly;
  }
  function repaintMenu() {
    const m = document.getElementById('acctMenu');
    if (!m || m.hidden) return;
    m.querySelectorAll('[data-invwrap]').forEach((w) => { w.innerHTML = inner(w.dataset.invwrap); });
  }

  /* 帳號選單項目：後端沒回應就是空字串（連容器都不留位置以外的東西） */
  function inner(kind) {
    if (S.st !== 'ok') return '';
    const cls = kind === 'm4' ? 'm4i' : '';
    return `<button type="button" role="menuitem" class="${cls}" data-inv="open"><span class="t">邀請好友／許願</span></button>`;
  }
  function menuHTML(kind) {
    if (!me()) return '';
    if (S.st === 'none' || (S.who && S.who !== String(me().email || ''))) refresh();
    return `<div data-invwrap="${kind}">${inner(kind)}</div>`;
  }

  /* ---------------- 對話框 ---------------- */
  const NEED = 5;       // 累計成功邀請幾人升級 Pro（Andy 11-02）；後端有給 next_pro_need 就以後端為準
  function progress(d) {
    const n = d.redeemed_count || 0;
    const unlocked = d.pro_unlocked != null ? !!d.pro_unlocked : n >= NEED;
    const left = d.next_pro_need != null ? Math.max(0, d.next_pro_need) : Math.max(0, NEED - n);
    const pct = Math.round(Math.min(n, NEED) / NEED * 100);
    return `<div class="invprog"><div class="invpt" id="invProgTxt">${unlocked ? '<b class="ok">已升級 Pro</b>' : `已邀請 <b>${n}</b> 人・再邀 <b>${left}</b> 人升級 Pro（7 天）`}</div>
      <div class="invbar" role="progressbar" aria-valuemin="0" aria-valuemax="${NEED}" aria-valuenow="${Math.min(n, NEED)}" aria-label="邀請進度"><i style="width:${unlocked ? 100 : pct}%"></i></div></div>`;
  }
  function body() {
    const d = S.data; if (!d) return '<p class="muted">讀取中…</p>';
    const days = d.pro_days || 14;
    const n = d.redeemed_count || 0;
    let h = `<h3>邀請好友</h3><p class="muted">好友用你的碼註冊：好友得 <b>${days} 天 Plus</b>，你也得 <b>${days} 天 Plus</b>，邀請越多累積越多；累計邀請 <b>${NEED} 人</b>升級 <b>Pro（7 天）</b>。</p>
      ${progress(d)}
      <div class="invcode"><span class="muted">我的邀請碼</span><b id="invCode">${esc(d.code)}</b><button type="button" class="invbtn" data-inv="copy-code">複製邀請碼</button></div>
      <div class="invrow"><input class="invlink" id="invLink" type="text" readonly value="${esc(d.link || '')}" aria-label="邀請連結"><button type="button" class="invbtn" data-inv="copy-link">複製連結</button></div>
      <p class="muted" id="invCnt">${n ? `已有 <b>${n}</b> 位朋友用了你的邀請碼。` : '還沒有朋友用你的邀請碼。'} 已累積 <b id="invDays">${d.reward_days_total || 0}</b> 天。</p><p class="msg" id="invCopyMsg" role="status"></p>`;
    h += '<div class="invsec"><h4>我有朋友的邀請碼</h4>';
    if (d.redeemed) {
      h += `<p class="ok">已兌換，Plus 可用到 <b>${esc(d.redeemed.pro_until || day(d.redeemed.pro_end))}</b>。</p>`;
    } else if (d.can_redeem === false) {
      h += '<p class="muted">只有註冊 7 天內、還不是付費會員的新帳號可以輸入邀請碼。</p>';
    } else {
      h += `<div class="invrow"><input type="text" id="invIn" maxlength="16" autocomplete="off" autocapitalize="characters" placeholder="輸入 8 碼邀請碼" value="${esc(pre())}" aria-label="朋友的邀請碼"><button type="button" class="invbtn pri" id="invGo" data-inv="redeem">兌換</button></div>
        <p class="msg" id="invMsg" role="status"></p>`;
    }
    h += '</div>';
    h += '<div class="invsec"><h4>許願：我想要這個功能</h4>' + wishHTML() + '</div>';
    return h + PRIV + '<div class="row2"><button type="button" data-close>關閉</button></div>';
  }
  /* 隱私：一行小字連結，連到隱私權政策收合段落（Andy 11-02：收納起來、不影響版面）*/
  const PRIV = '<p class="muted" style="font-size:12px;margin:10px 0 0"><a href="#privacy-promo" data-inv="priv">資料怎麼使用</a></p>';
  function wishHTML() {
    const w = S.wish;
    if (!w || !w.ok) return '<p class="muted">邀請滿 5 人升級 Pro 即可許願。</p>';
    const cur = w.wish;
    const stx = { new: '已收到', doing: '開發中', done: '已完成' };
    const was = cur ? `<p class="muted">你的願望：<b>${esc(cur.feature)}</b>　<span class="invtag" id="invWst">${esc(stx[cur.status] || '已收到')}</span><br>${esc(cur.text)}</p>` : '';
    return `${was}<p class="muted">每人一個願望，再送一次會取代上一個。</p>
      <input type="text" id="invWf" maxlength="60" placeholder="功能名稱（60 字內）" aria-label="功能名稱" value="${cur ? esc(cur.feature) : ''}">
      <textarea id="invWt" maxlength="500" placeholder="想怎麼用、解決什麼問題（6～500 字）" aria-label="願望內容">${cur ? esc(cur.text) : ''}</textarea>
      <div class="row2" style="margin-top:6px"><button type="button" class="pri invbtn" id="invWgo" data-inv="wish">${cur ? '更新願望' : '送出願望'}</button></div><p class="msg" id="invWmsg" role="status"></p>`;
  }
  function dlg() {
    let d = document.getElementById('invDlg');
    if (!d) {
      d = document.createElement('div'); d.id = 'invDlg'; d.className = 'acctdlg'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true'); d.setAttribute('aria-label', '邀請好友與許願');
      document.body.appendChild(d);
      d.addEventListener('click', (e) => {
        if (e.target === d || e.target.closest('[data-close]')) { d.hidden = true; return; }
        const b = e.target.closest('[data-inv]'); if (!b) return;
        if (b.dataset.inv === 'copy-code') copy(S.data.code, '邀請碼已複製');
        else if (b.dataset.inv === 'copy-link') copy(S.data.link, '邀請連結已複製');
        else if (b.dataset.inv === 'redeem') redeem(d);
        else if (b.dataset.inv === 'wish') wish(d);
        else if (b.dataset.inv === 'priv') d.hidden = true;     // 連結照常跳到 #privacy-promo，只先把對話框收掉
      });
      /* 掛在 document：重畫後焦點會掉到 body，掛在對話框上就收不到 Esc */
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !d.hidden) d.hidden = true; });
    }
    d.innerHTML = '<div class="box">' + body() + '</div>';
    d.hidden = false;
    refresh();
  }
  function repaintDlg() {
    const d = document.getElementById('invDlg');
    if (!d || d.hidden || d.querySelector('#invIn:focus,#invWf:focus,#invWt:focus')) return;   // 使用者正在打字就不重畫，免得輸入被洗掉
    d.innerHTML = '<div class="box">' + body() + '</div>';
  }
  function say(id, txt, good) { const m = document.getElementById(id); if (m) { m.textContent = txt; m.classList.toggle('good', !!good); } }
  async function copy(txt, okMsg) {
    let done = false;
    try { await navigator.clipboard.writeText(txt); done = true; } catch (e) { /* 沒權限：退回選取 */ }
    if (!done) {
      const el = document.getElementById('invLink');
      if (el) { el.focus(); el.select(); try { done = document.execCommand('copy'); } catch (e) { done = false; } }
    }
    say('invCopyMsg', done ? okMsg : '這個瀏覽器不讓我自動複製，請長按連結欄手動複製。', done);
    if (done && window.TwSub && window.TwSub.toast) window.TwSub.toast(okMsg);
  }
  async function redeem(d) {
    const inp = d.querySelector('#invIn'), go = d.querySelector('#invGo'); if (!inp || go.disabled) return;
    const code = inp.value.trim().toUpperCase();
    if (!code) { say('invMsg', '請先輸入邀請碼。'); return; }
    go.disabled = true; say('invMsg', '兌換中…');
    const j = await A().call('/v1/invite/redeem', { code });
    if (j && j._s === 200 && j.ok) {
      try { sessionStorage.removeItem(PRE_K); } catch (e) { /* 略過 */ }
      S.st = 'ok'; S.fly = null; S.who = '';
      if (window.TwPerm && window.TwPerm.refresh) { try { window.TwPerm.refresh(); } catch (e) { /* 略過 */ } }
      if (window.TwSub && window.TwSub.toast) window.TwSub.toast(`已獲得 ${j.days || 14} 天 Plus`);
      S.data = Object.assign({}, S.data, { can_redeem: false, redeemed: { pro_until: j.pro_until, pro_end: j.pro_end } });
      refresh(); repaintDlg(); return;
    }
    const e = j && j.error;
    say('invMsg', !j ? '連不到會員系統，請確認網路後再試一次。'
      : e === 'bad_code' ? '找不到這個邀請碼，請確認有沒有打錯。'
      : e === 'self' ? '不能輸入自己的邀請碼。'
      : e === 'used' ? '你已經用過邀請碼了。'
      : e === 'not_new' ? '只有註冊 7 天內的新帳號可以輸入邀請碼。'
      : e === 'already_paid' ? '你已經是付費會員，不需要邀請碼。'
      : e === 'same_ip' ? '這個網路已經領過或與邀請人相同，無法重複領取。'
      : e === 'too_many' ? '今天輸入錯太多次了，明天再試。'
      : e === 'no_pro_plan' ? '目前暫時無法發放，請稍後再試。'
      : `兌換沒有成功（${j._s}），請稍後再試。`);
    go.disabled = false;
  }
  async function wish(d) {
    const f = d.querySelector('#invWf'), t = d.querySelector('#invWt'), go = d.querySelector('#invWgo'); if (!f || go.disabled) return;
    const feature = f.value.trim(), text = t.value.trim();
    if (!feature) { say('invWmsg', '請寫一個功能名稱。'); return; }
    if (text.length < 6) { say('invWmsg', '願望內容至少要 6 個字。'); return; }
    go.disabled = true; say('invWmsg', '送出中…');
    const j = await A().call('/v1/wish', { text, feature });
    if (j && j._s === 200 && j.ok) {
      S.wish = { ok: true, wish: { feature, text, status: 'new' } };
      if (window.TwSub && window.TwSub.toast) window.TwSub.toast(j.replaced ? '願望已更新' : '願望已送出，謝謝你');
      repaintDlg(); say('invWmsg', j.replaced ? '已更新你的願望。' : '已送出，我們會看。', true); return;
    }
    const e = j && j.error;
    say('invWmsg', !j ? '連不到會員系統，請確認網路後再試一次。'
      : e === 'no_pro' ? 'Pro 期間已結束，無法再許願。邀請滿 5 人可再升級 Pro。'
      : e === 'bad_feature' ? '功能名稱不合格式（60 字內）。'
      : e === 'bad_text' ? '願望內容需要 6～500 字。'
      : `送出沒有成功（${j._s}），請稍後再試。`);
    go.disabled = false;
  }

  /* 兩份帳號選單都用委派：點了先收選單再開對話框 */
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('#acctMenu [data-inv]'); if (!b) return;
    e.stopPropagation();
    const m = document.getElementById('acctMenu'); if (m) m.hidden = true;
    dlg();
  }, true);
  window.addEventListener('tw:account', () => { S.st = 'none'; S.fly = null; refresh(); });
  window.addEventListener('tw:perm', () => { repaintMenu(); });

  window.TwInvite = { menuHTML, refresh, state: () => ({ st: S.st, data: S.data, wish: S.wish }), open: dlg };
})();
