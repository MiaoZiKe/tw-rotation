/* ============================================================================
   結帳與付款（2026-10-11，docs/payment_checkout_1011.md）
   ----------------------------------------------------------------------------
   Andy 10-11：「訂閱畫面，點擊訂閱後需要跳出金流服務，我已經申請綠界科技了，但還需要新增帳戶匯款，並且是需要有紀錄清單的…所以會有兩種方式可以進行」
   追加：手動匯款不能每月自動扣款 → 轉帳＝預付制，到期前 7 天與 1 天站內提醒＋「再匯一期」；信用卡才有定期定額。
   追加：「千萬不要發生付款後還沒開放」→ 付款完成頁輪詢訂單，開通後立刻 TwPerm.refresh()，畫面寫「已開通 X，到期日 Y」。

   這支做四件事：
     ① 結帳面板（#pricing 方案卡按「升級」）：方案、月繳／年繳、金額（伺服器價）、訂單編號；兩個分頁
        · 信用卡／ATM／超商（綠界）：再分「信用卡每月自動扣款（定期定額）」與「單次付款」→ 伺服器產生表單＋CheckMacValue → 自動送到綠界
        · 銀行轉帳：收款資訊（伺服器設定，不在 repo）＋回報末 5 碼／日期／金額／備註 → 待確認
     ② 我的訂單（#orders、#orders/<訂單號>）：每筆的方式、金額、狀態、時間、開通期間、退款；取消自動續訂；回報匯款；付款完成輪詢
     ③ 到期提醒（轉帳等不會自動續扣的人）：帳號鈕紅點＋頁首一行字＋「再匯一期」（到期前 7 天一次、前 1 天再一次）
     ④ 帳號選單（桌機 account.js、手機 acctm4.js 都經 billing.js 的 menuHTML）多一列「我的訂單／付款紀錄」
   ★ 金額只顯示伺服器回的（/v1/pay/quote），前端算的價格只用在方案卡；送出時也不帶金額。
   ★ 沒登入：記住要買的方案（sessionStorage）→ 走既有登入 → 登入回來自動重開結帳。
   ★ 版面：只新增自己的節點與 #coDlg／#v-orders／#payRenew 開頭的樣式；手機（≤640）規則一律包在 @media (max-width:640px)。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const A = () => window.TwAccount || null;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const nt = (n) => (Number(n) || 0).toLocaleString('en-US');
  const ymd = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10) : '');
  const ymdhm = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 16).replace('T', ' ') : '');
  const ss = { get(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } }, del(k) { try { sessionStorage.removeItem(k); } catch (e) { /* 同上 */ } } };
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 同上 */ } } };
  const PEND = 'tw.co.pending', DISMISS = 'tw.pay.renew.off';
  const ST_CLS = { pending: 'wait', review: 'wait', paid: 'wait', active: 'ok', failed: 'bad', rejected: 'bad', expired: 'mute', refunded: 'mute', cancelled: 'mute', superseded: 'mute' };
  const ST_NAME = { pending: '待付款', review: '待確認', paid: '已入帳', active: '已開通', failed: '失敗', rejected: '已退回', expired: '已逾期', refunded: '已退款', cancelled: '已取消（未付款）', superseded: '已被取代' };
  const S = { my: null, fly: null, poll: null };
  const me = () => { const a = A(); return a && a.on && a.on() ? a.user() : null; };
  const call = (p, b) => { const a = A(); return a && a.on() ? a.call(p, b || {}) : Promise.resolve(null); };

  function css() {
    if (!T()) return;
    T().css('coCss', `
#subDlg .box.codlg{width:min(560px,100%);padding:0;overflow:auto}
#subDlg .codlg .cohd{display:flex;align-items:center;gap:10px;padding:16px 20px;border-bottom:1px solid var(--line)}
#subDlg .codlg .cohd b{font-size:18px}
#subDlg .codlg .cohd .sp{flex:1}
#subDlg .codlg .cohd button{width:32px;height:32px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer;font-size:18px;line-height:1}
#subDlg .codlg .cotest{font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid var(--amber);color:var(--amber);white-space:nowrap}
#subDlg .codlg .cobd{padding:14px 20px 18px}
#subDlg .codlg .cosum{display:grid;grid-template-columns:88px minmax(0,1fr);gap:8px 12px;align-items:center;font-size:14px;margin-bottom:12px}
#subDlg .codlg .cosum>span{color:var(--ink-2)}
#subDlg .codlg .cosum .amt{font-size:22px;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums}
#subDlg .codlg .cosum code{font-family:var(--mono,ui-monospace,monospace);font-size:13.5px;color:var(--ink)}
#subDlg .codlg .cotabs{display:flex;border:1px solid var(--line-2);border-radius:10px;overflow:hidden;margin:4px 0 12px}
#subDlg .codlg .cotabs button{flex:1;min-height:44px;border:0;background:transparent;color:var(--ink-2);font-size:14px;cursor:pointer;padding:6px 8px;line-height:1.25}
#subDlg .codlg .cotabs button small{display:block;font-size:11.5px;color:var(--ink-3,var(--ink-2));font-weight:400}
#subDlg .codlg .cotabs button[aria-selected=true]{background:var(--cyan);color:#04121a;font-weight:700}
#subDlg .codlg .cotabs button[aria-selected=true] small{color:#04121a}
#subDlg .codlg .coopt{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--line-2);border-radius:10px;padding:10px 12px;margin:0 0 8px;cursor:pointer;color:var(--ink);font-size:14px}
#subDlg .codlg .coopt:has(input:checked){border-color:var(--cyan);background:color-mix(in srgb,var(--cyan) 8%,transparent)}
#subDlg .codlg .coopt input{margin-top:3px;flex:none}
#subDlg .codlg .coopt small{display:block;color:var(--ink-2);font-size:12.5px;line-height:1.5;margin-top:2px}
#subDlg .codlg .cobank{display:grid;grid-template-columns:88px minmax(0,1fr) auto;gap:6px 10px;align-items:center;border:1px solid var(--line-2);border-radius:10px;padding:10px 12px;font-size:14px;margin-bottom:10px}
#subDlg .codlg .cobank>span{color:var(--ink-2)}
#subDlg .codlg .cobank b{font-variant-numeric:tabular-nums;word-break:break-all}
#subDlg .codlg .cobank button{height:28px;padding:0 10px;border-radius:7px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:12.5px;cursor:pointer}
#subDlg .codlg .codue{grid-column:1/-1;color:var(--amber);font-size:13px}
#subDlg .codlg .cofrm{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px 10px}
#subDlg .codlg .cofrm label{margin:0;font-size:12.5px}
#subDlg .codlg .cofrm .w3{grid-column:1/-1}
#subDlg .codlg .cofrm>div{display:flex;flex-direction:column;justify-content:flex-end;min-width:0}
#subDlg .codlg .cofrm label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#subDlg .codlg .cofrm input::placeholder{color:var(--ink-3);font-size:13px}
#subDlg .codlg .cocfm{margin-top:10px;text-align:left;padding:12px 14px}
#subDlg .codlg .cocfm>b{font-size:14px}
#subDlg .codlg .cooff.cocfm{text-align:left}
#subDlg .codlg .cocfm .kv{margin:8px 0 10px;display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 16px;text-align:left}
#subDlg .codlg .cocfm .cfbtn{display:flex;gap:8px;align-items:stretch}
#subDlg .codlg .cocfm .cfbtn button{height:44px;margin:0;border-radius:10px;font:inherit;font-size:14px;white-space:nowrap}
#subDlg .codlg .cocfm #coCfmBack{flex:none;padding:0 16px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer}
#subDlg .codlg .cocfm .cogo{flex:1;font-size:15px}
#subDlg .codlg .cofrm label,#subDlg .codlg .cofrm .lb{display:block;margin:0 0 4px;font-size:12.5px;color:var(--ink)}
#subDlg .codlg .cofrm label small,#subDlg .codlg .cofrm .lb small{margin-left:6px;color:var(--ink-2);font-size:11.5px;font-weight:400}
#subDlg .codlg .cofrm .req{font-style:normal;margin-left:4px;color:var(--rise);font-size:11px}
#subDlg .codlg .cofrm .ro{height:36px;display:flex;align-items:center;padding:0 10px;border:1px dashed var(--line-2);border-radius:8px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--ink)}
#subDlg .codlg .cofrm input{width:100%;box-sizing:border-box;height:36px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;font:inherit;font-size:14px}
#subDlg .codlg .cooff{border:1px dashed var(--line-2);border-radius:10px;padding:14px;color:var(--ink-2);font-size:14px;text-align:center}
#subDlg .codlg .colegal{border-top:1px solid var(--line);margin-top:14px;padding-top:12px;font-size:13px;color:var(--ink-2);line-height:1.6}
#subDlg .codlg .colegal label{display:flex;gap:8px;align-items:flex-start;margin:0 0 6px;color:var(--ink);font-size:13px}
#subDlg .codlg .colegal a{color:var(--cyan)}
#subDlg .codlg .cogo{width:100%;height:44px;border-radius:10px;border:0;background:var(--cyan);color:#04121a;font-weight:700;font-size:15px;cursor:pointer;margin-top:10px}
#subDlg .codlg .cogo:disabled{opacity:.45;cursor:not-allowed}
#subDlg .codlg .msg{margin-top:8px}
#subDlg .codlg .codone{text-align:center;padding:10px 0}
#subDlg .codlg .codone h3{font-size:18px;margin:6px 0}
#v-orders .ordp{margin-top:16px}
#v-orders .ordp h2{margin:0 0 4px;font-size:18px}
#v-orders .ordp .muted{color:var(--ink-2);font-size:13px;margin:0 0 10px}
#v-orders .ordsum{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;padding:10px 12px;border:1px solid var(--line);border-radius:10px;font-size:14px;margin:8px 0 12px}
#v-orders .ordsum b{font-variant-numeric:tabular-nums}
#v-orders .ordbn{border:1px solid var(--line-2);border-radius:10px;padding:12px 14px;margin:0 0 12px;font-size:14px;line-height:1.6}
#v-orders .ordbn.ok{border-color:color-mix(in srgb,var(--fall) 60%,transparent);background:color-mix(in srgb,var(--fall) 8%,transparent)}
#v-orders .ordbn.wait{border-color:color-mix(in srgb,var(--amber) 60%,transparent);background:color-mix(in srgb,var(--amber) 8%,transparent)}
#v-orders .ordbn.bad{border-color:color-mix(in srgb,var(--rise) 60%,transparent)}
#v-orders .ordl{border-top:1px solid var(--line)}
#v-orders .ordr{display:grid;grid-template-columns:132px minmax(0,1.3fr) 96px minmax(0,1.2fr) 86px minmax(0,1.2fr);gap:4px 12px;align-items:center;padding:8px 4px;border-bottom:1px solid var(--line);font-size:13.5px;min-height:32px}
#v-orders .ordr.hd{color:var(--ink-2);font-size:12.5px;font-weight:600;min-height:0;text-align:center}
#v-orders .ordr.hit{background:color-mix(in srgb,var(--cyan) 8%,transparent)}
#v-orders .ordr>div{text-align:center;min-width:0}
#v-orders .ordr .n{font-variant-numeric:tabular-nums}
#v-orders .ordr .t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-orders .ordr>.sub{grid-column:1/-1;color:var(--ink-2);font-size:12.5px;line-height:1.55;text-align:left}
#v-orders .ordr .act{display:flex;gap:6px;justify-content:center;flex-wrap:wrap}
#v-orders button,#payRenew button{height:32px;padding:0 12px;border-radius:var(--r-sm,10px);border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:13px;cursor:pointer;white-space:nowrap}
#v-orders button.pri,#payRenew button.pri{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
.stp{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;border:1px solid var(--line-2);white-space:nowrap}
.stp.ok{color:var(--fall);border-color:color-mix(in srgb,var(--fall) 55%,transparent)}
.stp.wait{color:var(--amber);border-color:color-mix(in srgb,var(--amber) 55%,transparent)}
.stp.bad{color:var(--rise);border-color:color-mix(in srgb,var(--rise) 55%,transparent)}
.stp.mute{color:var(--ink-2)}
#payRenew{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:10px 0 0;padding:8px 12px;border:1px solid color-mix(in srgb,var(--amber) 60%,transparent);background:color-mix(in srgb,var(--amber) 10%,var(--panel));border-radius:10px;font-size:13.5px;color:var(--ink)}
#payRenew .sp{flex:1;min-width:0}
#payRenew .x{width:32px;padding:0}
/* 淺色主題：--cyan 是深青色，上面的字改白色（深色主題維持深字） */
:root[data-theme=light] #subDlg .codlg .cotabs button[aria-selected=true],:root[data-theme=light] #subDlg .codlg .cotabs button[aria-selected=true] small,
:root[data-theme=light] #subDlg .codlg .cogo,:root[data-theme=light] #subDlg .codlg .seg button.on,
:root[data-theme=light] #v-orders button.pri,:root[data-theme=light] #payRenew button.pri{color:#fff}
html.pay-renew #acctBtn.ame{position:relative}
html.pay-renew #acctBtn.ame::after{content:'';position:absolute;top:2px;right:2px;width:9px;height:9px;border-radius:50%;background:var(--rise);box-shadow:0 0 0 2px var(--bg)}
.acctmenu .ordi .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--rise);margin-left:6px;vertical-align:middle}
@media (max-width:640px){
  #subDlg .box.codlg{max-height:calc(100vh - 16px)}
  #subDlg .codlg .cohd{padding:12px 14px}
  #subDlg .codlg .cobd{padding:12px 14px 16px}
  #subDlg .codlg .cosum{grid-template-columns:72px minmax(0,1fr)}
  #subDlg .codlg .cofrm{grid-template-columns:minmax(0,1fr)}
  #subDlg .codlg .cobank{grid-template-columns:64px minmax(0,1fr) auto}
  #v-orders .ordr{grid-template-columns:minmax(0,1fr) auto;gap:2px 8px;padding:10px 2px}
  #v-orders .ordr.hd{display:none}
  #v-orders .ordr>div{text-align:left}
  #v-orders .ordr>.c-time{grid-column:1/-1;color:var(--ink-2);font-size:12px}
  #v-orders .ordr .act{grid-column:1/-1;justify-content:flex-start}
  #payRenew{margin:8px 0 0}
}`);
  }

  /* ---------------------------------------------------------------- ① 結帳面板 */
  const nameOf = (p) => (p && (p.planName || p.name)) || '';
  async function open(opt) {
    const p = opt || {};
    const plan = String(p.plan || '');
    let per = p.per === 'year' ? 'year' : 'month';
    const a = A();
    if (!a || !a.on()) { T().toast('會員功能尚未開放'); return; }
    if (!me()) {
      ss.set(PEND, JSON.stringify({ plan, per, tab: p.tab || '' }));
      T().toast('結帳前請先登入 —— 登入完成後會自動回到結帳');
      a.login();
      return;
    }
    ss.del(PEND);
    css();
    const D = T().dialog('<div class="cohd"><b>結帳</b></div><div class="cobd"><p class="muted">讀取價格…</p></div>', (d) => { d.querySelector('.box').className = 'box codlg'; });
    const [qm, qy] = await Promise.all([call('/v1/pay/quote', { plan, period: 'month' }), call('/v1/pay/quote', { plan, period: 'year' })]);
    const Q = { month: qm && qm._s === 200 ? qm : null, year: qy && qy._s === 200 ? qy : null };
    if (!Q[per] || Q[per].blocked) per = Q.month && !Q.month.blocked ? 'month' : Q.year && !Q.year.blocked ? 'year' : per;
    const box = D.querySelector('.box');
    /* 2026-10-12 Andy：已是年繳不能再出現月繳；降級／重複購買一律不能付款 → 兩種週期都被擋就只顯示說明，不產生任何訂單 */
    const okPer = ['month', 'year'].filter((k) => Q[k] && !Q[k].blocked);
    if ((Q.month || Q.year) && !okPer.length) {
      const bm = (Q.month && Q.month.blockedMsg) || (Q.year && Q.year.blockedMsg) || '你目前的方案不能購買這個項目。';
      box.innerHTML = `<div class="cohd"><b>結帳</b><span class="sp"></span><button type="button" data-close aria-label="關閉">×</button></div><div class="cobd"><p>${esc(bm)}</p></div>`;
      return;
    }
    if (!Q.month && !Q.year) {
      const e = (qm && qm.error) || (qy && qy.error);
      box.innerHTML = `<div class="cohd"><b>結帳</b><span class="sp"></span><button type="button" data-close aria-label="關閉">×</button></div><div class="cobd"><p>${!qm ? '連不到會員伺服器，請稍後再試。' : e === 'no_price' ? '這個方案還沒有線上價格，請從右下角「客服」聯絡我們。' : e === 'auth' ? '登入已過期，請重新登入。' : '讀不到價格（' + esc((qm && qm._s) || '') + '）'}</p></div>`;
      return;
    }
    const st = { per, tab: p.tab === 'bank' ? 'bank' : 'ecpay', kind: 'recur', oid: '', bankOrder: null };
    const base = Q[per];
    box.innerHTML = `<div class="cohd"><b id="coName">${esc(nameOf(base))}</b>${base.test ? '<span class="cotest" title="綠界金鑰還沒設定：付款會走綠界測試環境，不會真的扣款">測試模式</span>' : ''}<span class="sp"></span><button type="button" data-close aria-label="關閉">×</button></div>
      <div class="cobd">
        <div class="cosum"><span>方案</span><div>${esc(nameOf(base))}</div>
          <span>週期</span><div><div class="seg" id="coPer">${Q.month ? `<button type="button" data-per="month"${Q.month.blocked ? ' disabled title="' + esc(Q.month.blockedMsg) + '"' : ''}>月繳</button>` : ''}${Q.year ? `<button type="button" data-per="year"${Q.year.blocked ? ' disabled title="' + esc(Q.year.blockedMsg) + '"' : ''}>年繳</button>` : ''}</div>${(Q.month && Q.month.blocked) || (Q.year && Q.year.blocked) ? `<small class="muted" style="display:block;margin-top:4px">${esc((Q.month && Q.month.blockedMsg) || (Q.year && Q.year.blockedMsg))}</small>` : ''}</div>
          <span>金額</span><div class="amt" id="coAmt"></div>
          <span>訂單編號</span><div><code id="coOid">選擇付款方式後產生</code></div></div>
        <div class="cotabs" role="tablist" aria-label="付款方式"><button type="button" role="tab" id="coTabE" data-tab="ecpay">信用卡／ATM／超商<small>綠界 ECPay</small></button><button type="button" role="tab" id="coTabB" data-tab="bank">銀行轉帳<small>預付制・人工確認</small></button></div>
        <div id="coPaneE" role="tabpanel" aria-labelledby="coTabE">
          <label class="coopt"><input type="radio" name="coKind" value="recur"><span><b id="coRecurT"></b><small id="coRecurS"></small></span></label>
          <label class="coopt"><input type="radio" name="coKind" value="once"><span><b>單次付款（信用卡／ATM／超商）</b><small>付一期就好，不會自動續扣；到期前網站會提醒你續訂</small></span></label>
          <label class="coopt" id="coRenewL" style="border:0;padding:4px 2px;background:none"><input type="checkbox" id="coRenew"><span id="coRenewT"></span></label>
          <button type="button" class="cogo" id="coGoE" disabled>前往綠界付款</button>
        </div>
        <div id="coPaneB" role="tabpanel" aria-labelledby="coTabB" hidden></div>
        <div class="colegal"><label><input type="checkbox" id="coAgree"><span>我已閱讀並同意<a href="#terms" target="_blank" rel="noopener">《使用條款》</a><a href="#refund" target="_blank" rel="noopener">《退款與取消訂閱政策》</a>，並同意付款後立即開通服務、排除消費者保護法第 19 條之七日解除權。</span></label>
          付款即表示同意使用條款。退款規則見<a href="#refund" target="_blank" rel="noopener">退款政策</a>；個人資料之處理見<a href="#privacy" target="_blank" rel="noopener">《隱私權政策》</a>。</div>
        <div class="msg" id="coMsg" role="status"></div>
      </div>`;
    const $ = (s) => box.querySelector(s);
    const msg = (t, bad) => { const m = $('#coMsg'); m.className = 'msg ' + (bad ? 'bad' : 'ok'); m.textContent = t; };
    const consent = () => ({ consent_at: new Date().toISOString(), consent_version: window.TwLegal && window.TwLegal.termsVersion ? window.TwLegal.termsVersion() : 'unknown', consent: 'terms+refund;immediate_start;waive_cpa19' + (st.kind === 'recur' && st.tab === 'ecpay' ? ';auto_renew' : '') });
    function sync() {
      const q = Q[st.per];
      box.querySelectorAll('#coPer button').forEach((b) => b.classList.toggle('on', b.dataset.per === st.per));
      $('#coAmt').innerHTML = `NT$ ${nt(q.amount)}<small style="font-size:13px;font-weight:400;color:var(--ink-2)">／${st.per === 'year' ? '年' : '月'}</small>`;
      $('#coRecurT').textContent = st.per === 'year' ? '信用卡每年自動扣款（定期定額）' : '信用卡每月自動扣款（定期定額）';
      $('#coRecurS').textContent = `每${st.per === 'year' ? '年' : '月'}自動扣 NT$ ${nt(q.amount)}，可隨時在「我的訂單」取消自動續訂（已付的期間照常用到期滿）`;
      $('#coRenewT').textContent = `我同意每${st.per === 'year' ? '年' : '月'}自動續扣 NT$ ${nt(q.amount)}，直到我自行取消。`;
      box.querySelectorAll('input[name=coKind]').forEach((r) => { r.checked = r.value === st.kind; });
      $('#coRenewL').hidden = st.kind !== 'recur';
      $('#coGoE').disabled = !$('#coAgree').checked || (st.kind === 'recur' && !$('#coRenew').checked);
      box.querySelectorAll('.cotabs button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === st.tab)));
      $('#coPaneE').hidden = st.tab !== 'ecpay'; $('#coPaneB').hidden = st.tab !== 'bank';
      $('#coOid').textContent = st.tab === 'bank' && st.bankOrder ? st.bankOrder.id : st.oid || '選擇付款方式後產生';
      const sb = $('#coSendB'); if (sb) sb.disabled = !$('#coAgree').checked;
    }
    box.querySelectorAll('#coPer button').forEach((b) => { b.onclick = () => { if (st.per === b.dataset.per) return; st.per = b.dataset.per; st.bankOrder = null; if (st.tab === 'bank') bankPane(); sync(); }; });
    box.querySelectorAll('input[name=coKind]').forEach((r) => { r.onchange = () => { st.kind = r.value; sync(); }; });
    $('#coRenew').onchange = sync; $('#coAgree').onchange = sync;
    box.querySelectorAll('.cotabs button').forEach((b) => { b.onclick = () => { st.tab = b.dataset.tab; if (st.tab === 'bank' && !st.bankOrder) bankPane(); sync(); }; });
    $('#coGoE').onclick = async () => {
      const btn = $('#coGoE'); btn.disabled = true; msg('建立訂單中…');
      const j = await call('/v1/pay/ecpay/create', { plan, period: st.per, recur: st.kind === 'recur', back: location.origin + location.pathname, ...consent() });
      if (!j || j._s !== 200 || !j.ok) {
        btn.disabled = false;
        msg(!j ? '連不到會員伺服器，請稍後再試' : j.error === 'blocked' ? (j.msg || '目前方案不能購買這個項目') : j.error === 'too_many' ? '今天建立的訂單太多了，請明天再試或聯絡客服' : j.error === 'no_price' ? '這個方案還沒有線上價格' : `建立訂單失敗（${j._s}）`, true);
        return;
      }
      st.oid = j.id; sync();
      msg('前往綠界付款頁…');
      const f = document.createElement('form');
      f.method = 'POST'; f.action = j.action; f.id = 'coEcForm'; f.style.display = 'none'; f.acceptCharset = 'UTF-8';
      Object.entries(j.fields).forEach(([k, v]) => { const i = document.createElement('input'); i.type = 'hidden'; i.name = k; i.value = v; f.appendChild(i); });
      document.body.appendChild(f);
      if (window.TW_CO_NOSUBMIT) return;   // 驗收用：只檢查表單，不真的離開頁面
      f.submit();
    };
    async function bankPane() {
      const pane = $('#coPaneB');
      const bank = Q[st.per].bank;
      if (!bank) { pane.innerHTML = '<div class="cooff">銀行轉帳<b>尚未開放</b>，請先用信用卡／ATM／超商付款。</div>'; return; }
      pane.innerHTML = '<p class="muted">產生轉帳訂單…</p>';
      const j = await call('/v1/pay/bank/create', { plan, period: st.per, ...consent() });
      if (!j || j._s !== 200 || !j.ok) {
        pane.innerHTML = `<div class="cooff">${!j ? '連不到會員伺服器' : j.error === 'blocked' ? esc(j.msg || '目前方案不能購買這個項目') : j.error === 'too_many' ? '24 小時內最多建立 5 筆轉帳訂單，請明天再試或聯絡客服' : j.error === 'bank_off' ? '銀行轉帳尚未開放' : '產生訂單失敗（' + esc(j._s) + '）'}</div>`;
        return;
      }
      st.bankOrder = j; sync();
      paintBank(pane, j, () => sync());
    }
    function paintBank(pane, j) {
      const b = j.bank;
      const today = ymd(Date.now());
      pane.innerHTML = `<div class="cobank" id="coBank">
          <span>銀行</span><b id="coBankName">${esc(b.bank_name)}（${esc(b.bank_code)}）</b><span></span>
          <span>帳號</span><b id="coBankAcct">${esc(b.account)}</b><button type="button" data-copy="${esc(b.account)}">複製</button>
          <span>戶名</span><b>${esc(b.holder)}</b><span></span>
          <span>應付金額</span><b>NT$ ${nt(j.amount)}</b><button type="button" data-copy="${esc(j.amount)}">複製</button>
          <span>訂單編號</span><b>${esc(j.id)}</b><button type="button" data-copy="${esc(j.id)}">複製</button></div>
        <div class="cofrm" id="coFrm">
          <div><label for="coPayer">匯款人姓名<em class="req">必填</em></label><input id="coPayer" maxlength="40" autocomplete="name" required aria-required="true"></div>
          <div><label for="coL5">轉出帳號末 5 碼</label><input id="coL5" inputmode="numeric" maxlength="5" autocomplete="off"></div>
          <div><label for="coDate">轉帳日期</label><input id="coDate" type="date" value="${esc(today)}" max="${esc(today)}"></div>
          <div class="w3"><span class="lb">轉帳金額（依訂單，不用填）</span><div class="ro" id="coXAmt" aria-readonly="true">NT$ ${nt(j.amount)}</div></div></div>
        <button type="button" class="cogo" id="coSendB">我已轉帳，送出匯款資料</button>
        <p class="muted" style="font-size:12.5px;margin:6px 0 0">管理者確認入帳後開通，可在「我的訂單」查看。</p>`;
      pane.querySelectorAll('[data-copy]').forEach((c) => { c.onclick = () => { try { navigator.clipboard.writeText(c.dataset.copy); c.textContent = '已複製'; } catch (e) { /* 沒權限就算了 */ } }; });
      /* 2026-10-12 Andy：送出前要有確認機制，金額和應付不同要明確提醒（客戶可能不是匯 2,990）。確認區放在按鈕下方，不用彈窗。 */
      const doneBank = (o) => {
        box.innerHTML = `<div class="cohd"><b>已送出匯款資料</b><span class="sp"></span><button type="button" data-close aria-label="關閉">×</button></div>
          <div class="cobd codone"><h3>狀態：<span class="stp wait">待確認</span></h3><p>訂單 <code>${esc(o.id)}</code>・NT$ ${nt(o.amount)}・${o.period === 'year' ? '年繳' : '月繳'}</p>
          <p class="muted">管理者確認入帳後會自動開通方案，重新整理網頁就生效。</p>
          <button type="button" class="cogo" id="coSeeOrders">看我的訂單</button></div>`;
        box.querySelector('#coSeeOrders').onclick = () => { D.hidden = true; location.hash = '#orders/' + o.id; };
        refresh();
      };
      /* 2026-10-16 Andy：金額寫死＝訂單金額（客戶不能改，只有管理區能改）、匯款人姓名必填、不放範例字與備註 */
      $('#coSendB').onclick = () => {
        const f = { name: $('#coPayer').value.trim(), last5: $('#coL5').value.trim(), date: $('#coDate').value };
        if (!f.name) { $('#coPayer').focus(); return msg('請填匯款人姓名', true); }
        if (!/^\d{5}$/.test(f.last5)) return msg('轉出帳號末 5 碼要是 5 個數字', true);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(f.date)) return msg('請選轉帳日期', true);
        msg('');
        let cf = pane.querySelector('#coCfm'); if (cf) cf.remove();
        cf = document.createElement('div'); cf.id = 'coCfm'; cf.className = 'cooff cocfm';
        /* 10-16 Andy：「請調整適當大小排版，文字有點太多」「返回修改」不換行、跟送出鈕同高 */
        cf.innerHTML = `<b>請確認匯款資料（送出後不能修改）</b><div class="kv"><span>匯款人姓名</span><b>${esc(f.name)}</b><span>轉出帳號末 5 碼</span><b>${esc(f.last5)}</b><span>轉帳日期</span><b>${esc(f.date)}</b><span>轉帳金額</span><b>NT$ ${nt(j.amount)}</b></div>
          <div class="cfbtn"><button type="button" id="coCfmBack">返回修改</button><button type="button" class="cogo" id="coCfmGo">確認無誤，送出</button></div>`;
        $('#coSendB').after(cf); $('#coSendB').hidden = true;
        cf.querySelector('#coCfmBack').onclick = () => { cf.remove(); $('#coSendB').hidden = false; };
        cf.querySelector('#coCfmGo').onclick = () => report(j.id, f, msg, doneBank);
      };
      sync();
    }
    if (st.tab === 'bank') bankPane();
    sync();
  }
  async function report(id, f, msg, done) {
    if (!f.name) return msg('請填匯款人姓名', true);
    if (!/^\d{5}$/.test(f.last5)) return msg('轉出帳號末 5 碼要是 5 個數字', true);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(f.date)) return msg('請選轉帳日期', true);
    msg('送出中…');
    const j = await call('/v1/pay/bank/report', { id, name: f.name, last5: f.last5, date: f.date });
    if (j && j._s === 200 && j.ok) { msg(''); done(j.order); return; }
    msg(!j ? '連不到會員伺服器' : j.error === 'need_name' ? '請填匯款人姓名' : j.error === 'bad_date' ? '轉帳日期不對（不能是未來，也不能早於開單日）' : j.error === 'pending_review' ? (j.msg || '你有一筆待審核的訂單，審核完成前只能送出更高級別的方案') : j.error === 'already_reported' ? '這筆已經送出過匯款資料；要更正請用右下角「客服」→「意見反饋」' : j.error === 'bad_status' ? '這筆訂單已經處理過了' : `送出失敗（${j._s}）`, true);
  }

  /* ---------------------------------------------------------------- ② 我的訂單 */
  function refresh() {
    if (!me()) { S.my = null; paintRenew(); return Promise.resolve(null); }
    if (S.fly) return S.fly;
    S.fly = call('/v1/pay/my', {}).then((j) => {
      S.fly = null; S.my = j && j._s === 200 ? j : null; paintRenew();
      try { window.dispatchEvent(new CustomEvent('tw:pay-my')); } catch (e) { /* 略 */ }   // 10-16：方案頁的「待審核」按鈕要跟著換
      /* 2026-10-12：帳務通知（開通／退款／退回）在鈴鐺裡 —— 訂單狀態一變就叫鈴鐺重抓，不等它 10 分鐘的快取 */
      if (S.my) {
        const sig = (S.my.orders || []).map((o) => o.id + ':' + o.status + ':' + (o.refunded || 0) + ':' + ((o.reports || []).length)).join('|') + '#' + (S.my.reqs || []).map((r) => r.id + r.status).join('|') + '#' + S.my.plan + S.my.expires;
        let old = null; try { old = sessionStorage.getItem('tw.pay.sig'); sessionStorage.setItem('tw.pay.sig', sig); } catch (e) { /* 略 */ }
        if (old !== null && old !== sig && window.TwNotices && window.TwNotices.refresh) window.TwNotices.refresh();
      }
      return S.my;
    });
    return S.fly;
  }
  const methodName = (o) => o.method === 'bank' ? '銀行轉帳' : o.recur ? (o.parent ? `綠界・自動扣款第 ${o.periodN} 期` : '綠界・信用卡自動扣款') : /^ATM/.test(o.payType) ? '綠界・ATM' : /^CVS|^BARCODE/.test(o.payType) ? '綠界・超商' : '綠界・' + (o.payType ? '信用卡' : '單次付款');
  function subLine(o) {
    const a = [];
    if (o.grantTo) a.push(`開通期間 ${ymd(o.grantFrom)}～${ymd(o.grantTo)}`);
    /* 2026-10-12 Andy：記錄每一次回報的時間與真實輸入的金額，不可修改；重送的舊紀錄標「已作廢」 */
    /* 2026-10-16 Andy：「拿掉補送匯款資料這功能」→ 只列送出的那一筆；送錯改用意見反饋聯絡 */
    if (o.method === 'bank' && o.last5) a.push(`${o.payerName ? '匯款人 ' + esc(o.payerName) + '・' : ''}轉出末 5 碼 ${esc(o.last5)}・${esc(o.xferDate)}`);
    if (o.method === 'bank' && o.status === 'review') a.push('<span class="ordfix">資料填錯？請從右下角「客服」→「意見反饋」告訴我們</span>');
    if (o.payInfo && o.status === 'pending') a.push(o.payInfo.account ? `ATM 繳費帳號 ${esc(o.payInfo.bank)}-${esc(o.payInfo.account)}（${esc(o.payInfo.expire)} 前）` : o.payInfo.code ? `超商繳費代碼 ${esc(o.payInfo.code)}（${esc(o.payInfo.expire)} 前）` : '');
    if (o.recur && !o.parent) a.push(o.periodState === 'active' ? '自動續訂：開' : o.periodState === 'cancelled' ? `自動續訂：已取消（${ymd(o.cancelAt)}）` : '');
    if (o.rejectReason) a.push('退回原因：' + esc(o.rejectReason));
    if (o.refunded) a.push(`<b style="color:var(--rise)">已退款 NT$ ${nt(o.refunded)}</b>${o.refunds.length ? '（' + o.refunds.map((r) => ymd(r.at)).join('、') + '）' : ''}`);
    if (o.test) a.push('測試模式訂單');
    return a.filter(Boolean).join('・');
  }
  function rowHTML(o, hit) {
    const act = [];
    if (o.recur && !o.parent && o.periodState === 'active') act.push(`<button type="button" data-cxl="${esc(o.id)}">取消自動續訂</button>`);
    return `<div class="ordr${hit ? ' hit' : ''}" data-oid="${esc(o.id)}">
      <div class="c-time t" title="${esc(ymdhm(o.created))}">${esc(ymdhm(o.created))}</div>
      <div class="t" title="${esc(o.planName)}"><b>${esc(o.planName)}</b>・${o.period === 'year' ? '年繳' : '月繳'}</div>
      <div class="n">NT$ ${nt(o.amount)}</div>
      <div class="t" title="${esc(methodName(o))}">${esc(methodName(o))}</div>
      <div><span class="stp ${ST_CLS[o.status] || 'mute'}">${esc(o.refunded && o.status !== 'refunded' ? '部分退款' : ST_NAME[o.status] || o.status)}</span></div>
      <div class="act">${act.join('')}</div>
      <div class="sub">訂單 ${esc(o.id)}${subLine(o) ? '・' + subLine(o) : ''}</div></div>`;
  }
  async function renderOrders(v, focus) {
    css();
    if (!me()) {
      v.innerHTML = '<div class="card ordp"><h2>我的訂單／付款紀錄</h2><p class="muted">登入後才看得到你的訂單。</p><button type="button" class="pri" id="ordLogin">登入</button></div>';
      const b = v.querySelector('#ordLogin'); if (b) b.onclick = () => { const a = A(); if (a) a.login(); };
      return;
    }
    if (!S.my) v.innerHTML = '<div class="card ordp"><h2>我的訂單／付款紀錄</h2><p class="muted">載入中…</p></div>';
    /* 付款完成頁：先向伺服器查這一筆（伺服器會順手查綠界、該開通就開通），之後才抓會員資料 ——
       順序反過來的話，摘要會是「查單之前」那一份（橫幅寫已開通、摘要還是註冊會員）。
       還沒確認付款的這一筆不列在清單裡，只拿來顯示「正在確認付款結果」並輪詢。 */
    let f = null, cur = null;
    if (focus) {
      const r = await call('/v1/pay/order', { id: focus });
      if (r && r._s === 200 && r.order) { f = r.order; cur = r; }
      if (f && f.status === 'active') { S.my = null; S.fly = null; if (window.TwPerm && window.TwPerm.refresh) await window.TwPerm.refresh(); }
      if (!/^#orders\b/.test(location.hash || '')) return;
    }
    const j = await refresh();
    if (!/^#orders\b/.test(location.hash || '')) return;
    if (!j) { v.innerHTML = '<div class="card ordp"><h2>我的訂單／付款紀錄</h2><p class="muted">讀不到訂單（會員伺服器沒有回應）。</p></div>'; return; }
    const os = j.orders || [];   // 伺服器只回真的付過錢的（待付款／未完成付款不列，Andy 10-11）
    cur = cur || j;
    let banner = '';
    if (f) banner = bannerOf(f, cur);
    const rn = j.renew;
    v.innerHTML = `<div class="card ordp"><h2>我的訂單／付款紀錄</h2><p class="muted">每一筆付款的方式、金額、狀態與時間；退款也會列在這裡。</p>
      <div id="ordBn">${banner}</div>
      <div class="ordsum" id="ordSum"><span>目前方案 <b>${esc(j.planName || '註冊會員')}</b></span>${j.expires && j.plan !== 'free' ? `<span>到期日 <b>${esc(ymd(j.expires))}</b></span>` : ''}
        ${j.plan !== 'free' ? `<span>自動續訂 <b>${j.autoRenew ? '開' : os.some((o) => o.recur && !o.parent) ? '已取消' : '不適用'}</b>${!j.autoRenew && !os.some((o) => o.recur && !o.parent) ? '<small class="muted">（轉帳／單次付款是預付制，不會自動扣款）</small>' : ''}</span>` : ''}${rn ? `<span style="color:var(--amber)">剩 ${rn.days} 天到期</span><button type="button" class="pri" data-renew="1">${rn.method === 'bank' ? '再匯一期' : '續訂一期'}</button>` : ''}
        <span style="flex:1"></span><a href="#pricing">看方案</a></div>
      <div class="ordl" id="ordList">${os.length ? '<div class="ordr hd"><div>時間</div><div>方案</div><div>金額</div><div>方式</div><div>狀態</div><div></div></div>' + os.map((o) => rowHTML(o, o.id === focus)).join('') : '<p class="muted" id="ordEmpty" style="padding:12px 4px">還沒有付款紀錄。到 <a href="#pricing">訂閱方案</a> 挑一個吧。</p>'}</div>
      ${(j.reqs || []).length ? `<h3 style="margin:16px 0 6px;font-size:15px">我的取消／退款申請</h3><div class="ordl" id="ordReqs">${j.reqs.map((r) => `<div class="ordr" style="grid-template-columns:auto auto 1fr auto"><div class="c-time t">${esc(ymdhm(r.created))}</div><div><b>${r.type === 'refund' ? '申請退款' : '取消訂閱'}</b></div><div class="t" title="${esc(r.note || '')}">${esc(r.note || '')}</div><div><span class="stp ${r.status === 'new' ? 'wait' : 'ok'}" title="${esc(r.closeReason || '')}">${r.status === 'new' ? '處理中' : r.closedBy === 'auto' ? '已結案' : '已處理'}</span>${r.status !== 'new' && r.closeReason ? `<small class="muted" style="display:block">${esc(r.closeReason)}</small>` : ''}</div></div>`).join('')}</div>` : ''}</div>`;
    bind(v, j);
    if (f && ['pending', 'paid'].includes(f.status) && f.method === 'ecpay') startPoll(v, f.id);
  }
  function bannerOf(o, j) {
    if (o.status === 'active') return `<div class="ordbn ok" id="ordDone"><b>付款完成，已開通 ${esc(j.planName || o.planName)}</b>，到期日 <b>${esc(ymd(j.expires || o.grantTo))}</b>。功能已經解鎖，不用重新登入。</div>`;
    if (o.status === 'review') return '<div class="ordbn wait">已收到你的匯款資料，管理者確認入帳後就會開通。</div>';
    if (o.status === 'pending' && o.method === 'ecpay') return `<div class="ordbn wait" id="ordWait">正在確認付款結果…（訂單 ${esc(o.id)}）<br><small>ATM／超商要等你繳費後才會開通；信用卡通常幾秒內完成。</small></div>`;
    if (o.status === 'paid') return '<div class="ordbn wait">已收到款項，正在開通…</div>';
    if (o.status === 'failed' || o.status === 'cancelled') return '<div class="ordbn bad">這筆沒有完成付款，會員狀態沒有變更；要訂閱請重新結帳。</div>';
    return '';
  }
  function bind(v, j) {
    v.querySelectorAll('[data-cxl]').forEach((b) => { b.onclick = () => cancelDlg(b.dataset.cxl, j); });
    const rn = v.querySelector('[data-renew]'); if (rn) rn.onclick = () => renewNow();
  }
  /* 付款完成頁輪詢（每 3 秒，最多 3 分鐘）：開通了 → TwPerm.refresh() 讓功能馬上解鎖 */
  function startPoll(v, id) {
    clearTimeout(S.poll);
    let n = 0;
    const tick = async () => {
      if (!(location.hash || '').startsWith('#orders/' + id)) return;
      const j = await call('/v1/pay/order', { id });
      n++;
      if (j && j._s === 200 && j.order && j.order.status === 'active') {
        if (window.TwPerm && window.TwPerm.refresh) await window.TwPerm.refresh();
        if (window.TwBilling && window.TwBilling.refresh) window.TwBilling.refresh();
        S.my = null; S.fly = null; renderOrders(v, id);
        return;
      }
      if (j && j.order && ['failed', 'expired', 'cancelled'].includes(j.order.status)) { S.my = null; renderOrders(v, id); return; }
      if (n < 60) S.poll = setTimeout(tick, n < 5 ? 1500 : 3000);
    };
    S.poll = setTimeout(tick, 600);
  }
  function cancelDlg(id, j) {
    const d = T().dialog(`<h3>取消自動續訂？</h3><p>取消後：</p><ul style="margin:4px 0 8px 18px;font-size:14px;line-height:1.7"><li>綠界<b>不再自動扣款</b></li><li>已付的期間照常用到 <b>${esc(ymd(j.expires))}</b>，到期後自動回到註冊會員</li><li>這個動作無法復原，之後想續訂要重新結帳</li></ul>
      <p class="muted">想退款請改用右下角客服申請（見<a href="#refund">退款政策</a>）。</p><div class="msg" id="cxMsg" role="status"></div>
      <div class="row2"><button type="button" data-close>先不要</button><button type="button" class="pri" id="cxGo">確定取消自動續訂</button></div>`);
    d.querySelector('#cxGo').onclick = async () => {
      const b = d.querySelector('#cxGo'), m = d.querySelector('#cxMsg'); b.disabled = true; m.className = 'msg'; m.textContent = '向綠界取消中…';
      const r = await call('/v1/pay/period/cancel', { id });
      if (r && r._s === 200) { d.hidden = true; T().toast('已取消自動續訂'); S.my = null; const v = document.getElementById('v-orders'); if (v) renderOrders(v, ''); return; }
      b.disabled = false; m.className = 'msg bad'; m.textContent = '取消沒有成功：' + ((r && r.msg) || (r ? r._s : '連不到會員伺服器'));
    };
  }

  /* ---------------------------------------------------------------- ③ 到期提醒（轉帳／單次付款，不會自動續扣的人）*/
  const renewKey = (rn) => `${rn.plan}:${rn.expires}:${rn.stage}`;
  function paintRenew() {
    const rn = S.my && S.my.renew;
    const on = !!(rn && me() && ls.get(DISMISS) !== renewKey(rn));
    document.documentElement.classList.toggle('pay-renew', !!(rn && me()));
    let bar = document.getElementById('payRenew');
    if (!on) { if (bar) bar.remove(); return; }
    css();
    const main = document.querySelector('main'); if (!main) return;
    if (!bar) { bar = document.createElement('div'); bar.id = 'payRenew'; bar.setAttribute('role', 'status'); main.insertBefore(bar, main.firstChild); }
    bar.innerHTML = `<span class="sp">你的 <b>${esc(rn.planName)}</b> 方案將於 <b>${esc(ymd(rn.expires))}</b> 到期（剩 ${rn.days} 天）。${rn.method === 'bank' ? '銀行轉帳不會自動續扣，' : ''}要繼續使用請再付一期。</span>
      <button type="button" class="pri" id="payRenewGo">${rn.method === 'bank' ? '再匯一期' : '續訂一期'}</button><button type="button" class="x" id="payRenewX" aria-label="先不要提醒">×</button>`;
    bar.querySelector('#payRenewGo').onclick = renewNow;
    bar.querySelector('#payRenewX').onclick = () => { ls.set(DISMISS, renewKey(rn)); bar.remove(); };
  }
  function renewNow() {
    const rn = S.my && S.my.renew; if (!rn) return;
    open({ plan: rn.plan, per: rn.period, tab: rn.method === 'bank' ? 'bank' : 'ecpay' });
  }

  /* ---------------------------------------------------------------- ④ 帳號選單一列 */
  function menuItem(kind) {
    if (!me()) return '';
    if (!S.my && !S.fly) refresh();
    const dot = S.my && S.my.renew ? '<i class="dot" aria-label="即將到期"></i>' : '';
    return kind === 'm4'
      ? `<button type="button" class="m4i ordi" role="menuitem" data-ord="1"><span class="t">我的訂單／付款紀錄${dot}</span></button>`
      : `<button type="button" role="menuitem" class="ordi" data-ord="1">我的訂單／付款紀錄${dot}</button>`;
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('#acctMenu [data-ord]'); if (!b) return;
    e.stopPropagation();
    const m = document.getElementById('acctMenu'); if (m) m.hidden = true;
    location.hash = '#orders';
  }, true);

  /* ---------------------------------------------------------------- 路由與事件 */
  (window.TwSubRoutes = window.TwSubRoutes || []).push((head, rest) => {
    if (head !== 'orders' || !T()) return null;
    const v = T().view('v-orders'); if (!v) return null;
    const id = Array.isArray(rest) ? rest[0] || '' : '';
    renderOrders(v, /^LG[0-9A-Z]{10,22}$/.test(id) ? id : '');
    return 'v-orders';
  });
  window.addEventListener('tw:account', () => {
    S.my = null;
    if (me()) {
      refresh();
      const p = ss.get(PEND);
      if (p) { try { const o = JSON.parse(p); setTimeout(() => open(o), 200); } catch (e) { ss.del(PEND); } }
    } else paintRenew();
    if (/^#orders\b/.test(location.hash || '')) { const v = document.getElementById('v-orders'); if (v) renderOrders(v, (location.hash.split('/')[1] || '')); }
  });
  /* 開頁時已經登入：抓一次（提醒要在頁首出現）*/
  setTimeout(() => { if (me()) refresh(); }, 1200);
  window.TwCheckout = { open, refresh, menuItem, state: () => ({ my: S.my }), renderOrders };
})();
