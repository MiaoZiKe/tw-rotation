/* ============================================================================
   取消訂閱／申請退款＋「七天保證」防呆（2026-10-09，帳本 48）
   ----------------------------------------------------------------------------
   Andy 07:5x（看著網頁版右上角帳號選單）：「這邊需要新增退款以及取消訂閱功能，並且需要防呆機制，
   他取消後就不能再享有七天免費功能」。這次他明確要網頁版也加 → 桌機（account.js）與手機（acctm4.js）兩份帳號選單都放這兩項，
   內容由這支產生，兩邊長得一樣、規則只寫一次。選單平常收著，頁面初始版面不變（桌機守門1008）。

   誰看得到：只有付費方案（Plus、Pro…）。訪客、免費會員不顯示；站主顯示但停用（站主沒有訂閱可取消／退款）。
   後端（workers/account-api/worker.js「取消訂閱／退款」區塊）：
     POST /v1/billing/me         → { paid, periodEnd, firstPaid, refundDays, trialUsed, refundUsed, canRefund, refundWhy, cancel, refund }
     POST /v1/subscribe/change   → { type:'cancel'|'refund' } 建立一筆申請（管理區「意見反饋與訂閱申請」看得到、可篩選、標已處理）
   現在沒有線上金流：兩項都是「送申請、專人處理」，不會當場扣款或退錢。

   ★ 防呆（Andy 的重點）：一個帳號只要申請過取消或退款，就不能再享有七天免費試用與七天退款保證。
     · 旗標在 Worker 以 email 雜湊存（刪帳號重註冊同一個信箱也比得到），前端只讀。
     · 試用入口：任何畫面上標了 [data-trial] 的元素，只有 Worker 明確回「沒用過」時才顯示（html.trial-ok）。
       Worker 還沒部署／連不到／沒登入 → 一律不顯示（寧可不給，避免被濫用）。目前 #pricing 沒有「七天免費／試用」字樣；之後加的人請掛 data-trial。
     · 退款鈕：Worker 說 canRefund 才按得下去；其他狀況停用並寫原因（用過保證、超過 N 天、處理中、伺服器還沒開放）。
   REFUND_DAYS：讀 site/legal_config.js 的 TW_LEGAL.REFUND_DAYS（法遵同事在 claude/refund-policy 新增）；
     還沒有那個欄位就先用常數 7。⚠ 這個數字只用於顯示，能不能退以 Worker 的 BILL_REFUND_DAYS 為準（改一邊要改另一邊）。
   ============================================================================ */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const A = () => window.TwAccount || null;
  const P = () => window.TwPerm || null;
  const L = window.TW_LEGAL || {};
  const REFUND_DAYS = Number.isInteger(L.REFUND_DAYS) && L.REFUND_DAYS > 0 ? L.REFUND_DAYS : 7;   // 常數 7：等 claude/refund-policy 合併後改讀設定檔
  const HASH_DAYS = Number.isInteger(L.HASH_RETENTION_DAYS) && L.HASH_RETENTION_DAYS > 0 ? L.HASH_RETENTION_DAYS : 365;   // 同上；Worker 端 BILL_HASH_DAYS
  const S = { data: null, st: 'none', fly: null, who: '' };    // st：none（沒登入）／loading／ok／off（Worker 沒這支 API 或連不到）
  const day = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10) : '');

  /* 試用入口：預設藏起來，Worker 明確說「沒用過」才掛 html.trial-ok 放出來 */
  (function css() {
    const s = document.createElement('style'); s.id = 'billCss';
    s.textContent = `html:not(.trial-ok) [data-trial]{display:none!important}
.acctmenu .billi[aria-disabled="true"]{opacity:.6;cursor:not-allowed}
.acctmenu .billi small{display:block;color:var(--ink-2);font-size:12px;line-height:1.4;white-space:normal}
.acctmenu .billi.refund:not([aria-disabled="true"]){color:var(--amber)}
#billDlg .box{font-size:14px}#billDlg .msg{min-height:1.4em;font-size:13px;color:#ff6b7a;margin:6px 0 0}`;
    document.head.appendChild(s);
  })();
  const trialOk = () => S.st === 'ok' && !!S.data && !S.data.trialUsed && !S.data.refundUsed && !S.data.owner;   // 站主不需要試用
  const paintTrial = () => document.documentElement.classList.toggle('trial-ok', trialOk());

  function me() { const a = A(); return a && a.on && a.on() ? a.user() : null; }
  /* 付費身分：看 TwPerm（跟徽章同一個來源）；站主另外顯示停用版 */
  function tier() {
    const u = me(); if (!u) return 'guest';
    if (u.owner) return 'owner';
    const st = P() ? P().state() : {};
    return st.plan && st.plan !== 'free' && st.plan !== 'guest' && st.who !== 'guest' ? 'paid' : 'free';
  }
  function refresh() {
    const u = me();
    if (!u) { S.data = null; S.st = 'none'; S.who = ''; paintTrial(); return Promise.resolve(); }
    const who = String(u.email || '');
    if (S.fly && S.who === who) return S.fly;
    S.who = who; S.st = S.st === 'ok' ? 'ok' : 'loading';
    S.fly = A().call('/v1/billing/me', {}).then((j) => {
      S.fly = null;
      if (j && j._s === 200) { S.data = j; S.st = 'ok'; }
      else { S.data = null; S.st = 'off'; }      // 404（Worker 還沒部署這支）、連不到 → 一律當「不提供」
      paintTrial(); repaintMenu();
    });
    return S.fly;
  }
  function repaintMenu() {
    const m = document.getElementById('acctMenu');
    if (!m || m.hidden) return;
    m.querySelectorAll('[data-billwrap]').forEach((w) => { w.innerHTML = inner(w.dataset.billwrap); });
  }

  /* 選單項目（kind＝'desk' 桌機選單／'m4' 手機選單：只差 class，文字與規則一樣） */
  function inner(kind) {
    const t = tier(); if (t !== 'paid' && t !== 'owner') return '';
    const cls = kind === 'm4' ? 'm4i billi' : 'billi';
    const item = (k, label, why, dis, extra) => `<button type="button" role="menuitem" class="${cls}${extra || ''}" data-b="${k}"${dis ? ' aria-disabled="true"' : ''}><span class="t">${label}${why ? `<small>${why}</small>` : ''}</span></button>`;
    if (t === 'owner') {
      const why = '站主帳號不受方案限制，沒有訂閱可取消或退款';
      return item('cancel', '取消訂閱', why, true) + item('refund', '申請退款', why, true, ' refund');
    }
    const d = S.data;
    if (S.st !== 'ok' || !d) {
      const why = S.st === 'loading' ? '讀取訂閱狀態中…' : '伺服器尚未開放線上申請，請用「意見回饋」聯絡我們';
      return item('cancel', '取消訂閱', why, true) + item('refund', '申請退款', why, true, ' refund');
    }
    const until = d.periodEnd ? day(d.periodEnd) : '';
    const c = d.cancel
      ? item('cancel', '取消訂閱', `已申請取消，可用到 ${until || '本期結束'}`, true)
      : item('cancel', '取消訂閱', until ? `可用到 ${until}，次期不再扣款` : '', false);
    const n = d.refundDays || REFUND_DAYS;
    const rWhy = d.refund ? '已送出退款申請，專人處理中'
      : d.refundUsed || d.trialUsed ? '此帳號已使用過七天保證'
      : !d.canRefund ? `首次付款已超過 ${n} 天，不在七天退款保證內`
      : `首次付款 ${n} 天內可申請，每個帳號限一次`;
    const r = item('refund', '申請退款', rWhy, !!d.refund || !d.canRefund || d.refundUsed || d.trialUsed, ' refund');
    return c + r;
  }
  function menuHTML(kind) {
    const t = tier(); if (t !== 'paid' && t !== 'owner') return '';
    if (S.st === 'none' || (S.who && S.who !== String((me() || {}).email || ''))) refresh();
    return `<div data-billwrap="${kind}">${inner(kind)}</div>`;
  }

  /* ---------------- 確認框 ---------------- */
  function dlg(type) {
    const d0 = S.data || {};
    let d = document.getElementById('billDlg');
    if (!d) {
      d = document.createElement('div'); d.id = 'billDlg'; d.className = 'acctdlg'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true');
      document.body.appendChild(d);
      d.addEventListener('click', (e) => { if (e.target === d || e.target.closest('[data-close]')) d.hidden = true; if (e.target.closest('#billYes')) send(d); });
      d.addEventListener('keydown', (e) => { if (e.key === 'Escape') d.hidden = true; });
    }
    d.dataset.type = type;
    const until = d0.periodEnd ? day(d0.periodEnd) : '';
    const plan = esc(d0.planName || (P() && P().state().planName) || '付費方案');
    const warn = `<p class="muted"><b>防呆提醒：</b>送出後，這個帳號<b>不再享有退款保證（目前不提供免費試用；日後如提供，亦不適用）</b>（刪除帳號後用同一個信箱重新註冊也一樣：我們只保存一組無法還原成信箱的比對碼 ${HASH_DAYS} 天，用來防止重複使用）。</p>`;
    d.setAttribute('aria-label', type === 'cancel' ? '取消訂閱' : '申請退款');
    d.innerHTML = '<div class="box">' + (type === 'cancel'
      ? `<h3>取消訂閱</h3><p>你目前是 <b>${plan}</b>。取消後：</p><ul><li>${until ? `可以繼續使用到本期結束日 <b>${until}</b>` : '可以繼續使用到本期結束'}</li><li>次期<b>不再扣款</b>，到期後自動回到註冊會員</li><li>自選清單與設定都會保留</li></ul>
        <p class="muted">目前是申請制：送出後由專人處理，處理完成會寄信通知。想要退款請改按「申請退款」。</p>${warn}`
      : `<h3>申請退款</h3><p>首次付款 <b>${d0.refundDays || REFUND_DAYS} 天內</b>可申請全額退款（每個帳號限一次）。核准後方案立即停止，回到註冊會員。</p>
        <p class="muted">目前是申請制：送出後由專人與你聯繫退款方式（不會在這裡要你輸入任何付款資料）。</p>${warn}`)
      + `<p class="msg" id="billMsg" role="status"></p><div class="row2"><button type="button" data-close>先不要</button><button type="button" class="danger" id="billYes">${type === 'cancel' ? '確定取消訂閱' : '送出退款申請'}</button></div></div>`;
    d.hidden = false;
  }
  async function send(d) {
    const y = d.querySelector('#billYes'), msg = d.querySelector('#billMsg'); if (!y || y.disabled) return;
    y.disabled = true; msg.textContent = '送出中…';
    const type = d.dataset.type;
    const j = await A().call('/v1/subscribe/change', { type });
    if (j && j._s === 200 && j.ok) {
      S.data = j; S.st = 'ok'; paintTrial(); d.hidden = true;
      const txt = type === 'cancel' ? `已申請取消，可用到 ${j.periodEnd ? day(j.periodEnd) : '本期結束'}` : '退款申請已送出，專人會與你聯繫';
      if (window.TwSub && window.TwSub.toast) window.TwSub.toast(txt);
      return;
    }
    const e = j && j.error;
    msg.textContent = !j ? '連不到會員系統，請確認網路後再試一次。'
      : j._s === 404 ? '伺服器尚未開放線上申請，請用「意見回饋」聯絡我們。'
      : e === 'exists' ? '你已經送過這個申請了，專人處理中。'
      : e === 'refund_used' ? '此帳號已使用過七天保證。'
      : e === 'refund_window' ? `首次付款已超過 ${REFUND_DAYS} 天，不在七天退款保證內。`
      : e === 'owner' ? '站主帳號沒有訂閱可取消或退款。'
      : e === 'not_paid' ? '你目前不是付費方案。'
      : `送出沒有成功（${j._s}），請稍後再試。`;
    if (j && j._s === 409 && j.paid != null) { S.data = j; paintTrial(); }
    y.disabled = false;
  }
  /* 兩份選單都用委派：點了先收選單、停用的不動作 */
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('#acctMenu [data-b]'); if (!b) return;
    e.stopPropagation();
    if (b.getAttribute('aria-disabled') === 'true') return;
    const m = document.getElementById('acctMenu'); if (m) m.hidden = true;
    dlg(b.dataset.b);
  }, true);
  window.addEventListener('tw:account', () => { S.st = 'none'; refresh(); });
  window.addEventListener('tw:perm', () => { if (tier() === 'paid' && S.st === 'none') refresh(); repaintMenu(); });
  paintTrial();

  window.TwBilling = { menuHTML, refresh, state: () => ({ st: S.st, data: S.data }), trialOk, REFUND_DAYS, open: dlg };
})();
