/* 管理區：付款與訂單（#admin/pay）—— 2026-10-11，docs/payment_checkout_1011.md
   ----------------------------------------------------------------------------
   Andy 10-11：「需要有紀錄清單的，他如果適用帳戶匯款我是可以看到清單，為了以後確認會員資訊用…需要一個完整介面」
   追加：「當確認他付款後，會紀錄他付款時間，他訂閱多久，多久後會自動取消…總之我需要清單…退款機制我是否能快速退款」＋要能匯出。
   四個分頁：
     ① 訂單：最上面「待確認的轉帳（N）」與「異常（已付款沒開通、開通出錯、金額不符）」＋一鍵補開通；篩選（方式／狀態／期間／搜尋／即將到期的轉帳會員）；
        每筆：確認入帳並開通、退回（寫原因）、加備註、退款、查單（綠界）；點一列展開明細（開通期間、綠界交易號、退款紀錄）
     ② 會員訂閱：每個付費會員一列（目前方案、付款方式、第一次／最近付款、週期、本期起訖、自動續訂、到期降回日、累計金額、筆數），點一列展開他所有訂單與退款
     ③ 退款紀錄
     ④ 收款帳號設定（銀行名稱、代碼、帳號、戶名；存在伺服器 kv，不進 repo）
   每個動作按下去都先跳確認框說明會發生什麼。三份 CSV（訂單、會員訂閱、退款）含 BOM，Excel 直接開不亂碼。
   API：account-api /v1/admin/pay/*（只有管理者；這一頁只是排版）。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const nt = (n) => (Number(n) || 0).toLocaleString('en-US');
  const ymd = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10) : '');
  const ymdhm = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 16).replace('T', ' ') : '');
  const fromYmd = (s) => Date.parse(s + 'T00:00:00+08:00');
  const ST = { pending: '待付款', review: '待確認', paid: '已入帳', active: '已開通', failed: '失敗', rejected: '已退回', expired: '已逾期', refunded: '已退款', cancelled: '已取消（未付款）' };
  const ST_CLS = { pending: 'wait', review: 'wait', paid: 'wait', active: 'ok', failed: 'bad', rejected: 'bad', expired: 'mute', refunded: 'mute', cancelled: 'mute' };
  const EV = { activate: '開通', extend: '延長', expire: '到期降級', refund_downgrade: '退款降級', refund_keep: '退款（到期才停）', auto_renew_off: '取消自動續訂' };
  const S = { d: null, tab: 'bankord', f: { method: '', status: '', from: '', to: '', q: '', expiring: false, all: false }, open: {} };
  const methodName = (o) => o.method === 'bank' ? '銀行轉帳' : o.recur ? (o.parent ? `綠界自動扣款 第${o.periodN}期` : '綠界定期定額') : /^ATM/.test(o.payType) ? '綠界 ATM' : /^CVS|^BARCODE/.test(o.payType) ? '綠界超商' : '綠界單次';
  const stName = (o) => (o.refunded && o.status !== 'refunded' ? '部分退款' : ST[o.status] || o.status);

  function css() {
    T().css('payAdmCss', `
#v-subadm .pay [hidden]{display:none!important}
#v-subadm .pay h3{margin:0;font-size:16px}
#v-subadm .pay .muted{color:var(--ink-2);font-size:13px;line-height:1.6;margin:4px 0 10px}
#v-subadm .pay .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
#v-subadm .pay .hd .sp{flex:1}
#v-subadm .pay .tst{font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid var(--amber);color:var(--amber)}
#v-subadm .pay .anom{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:700;color:#fff;background:var(--rise);border-radius:999px;padding:3px 10px}
#v-subadm .pay .anom.zero{background:transparent;color:var(--ink-2);font-weight:400;border:1px solid var(--line-2)}
#v-subadm .pay button{height:32px;padding:0 12px;border-radius:var(--r-sm,10px);border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer;font-size:13px;white-space:nowrap}
#v-subadm .pay button.pri{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
#v-subadm .pay button.danger{color:var(--rise)}
:root[data-theme=light] #v-subadm .pay button.pri,:root[data-theme=light] #v-subadm .pay .cnt,:root[data-theme=light] #v-subadm .pay .anom[style]{color:#fff!important}
:root[data-theme=light] #subDlg .payd button.pri{color:#fff}
#v-subadm .pay button.sm{height:28px;padding:0 9px;font-size:12.5px}
#v-subadm .pay .sec{border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin:10px 0}
#v-subadm .pay .sec.warn{border-color:color-mix(in srgb,var(--amber) 55%,transparent)}
#v-subadm .pay .sec.bad{border-color:color-mix(in srgb,var(--rise) 60%,transparent)}
#v-subadm .pay .sec h4{margin:0 0 6px;font-size:14px;display:flex;align-items:center;gap:8px}
#v-subadm .pay .cnt{display:inline-grid;place-items:center;min-width:20px;height:20px;padding:0 6px;border-radius:999px;background:var(--amber);color:#04121a;font-size:12px;font-weight:700}
#v-subadm .pay .sec.bad .cnt{background:var(--rise);color:#fff}
#v-subadm .pay .flt{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
#v-subadm .pay .flt select,#v-subadm .pay .flt input,#v-subadm .pay .frm input{height:32px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 8px;font:inherit;font-size:13.5px;box-sizing:border-box}
#v-subadm .pay .flt input[type=search]{flex:1 1 200px;min-width:0}
#v-subadm .pay .flt label{font-size:13px;color:var(--ink-2);display:inline-flex;align-items:center;gap:4px}
#v-subadm .pay .tw{overflow-x:auto}
#v-subadm .pay table{width:100%;border-collapse:collapse;font-size:13px}
#v-subadm .pay th,#v-subadm .pay td{padding:6px 8px;border-bottom:1px solid var(--line);height:32px;white-space:nowrap;text-align:center}
#v-subadm .pay th{color:var(--ink-2);font-weight:600;font-size:12.5px}
#v-subadm .pay td.l{text-align:left;max-width:220px;overflow:hidden;text-overflow:ellipsis}
#v-subadm .pay td.n{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono,ui-monospace,monospace)}
#v-subadm .pay td.act{text-align:right}
#v-subadm .pay td.act button{margin-left:4px}
#v-subadm .pay tr.prow{cursor:pointer}
#v-subadm .pay tr.prow:hover td{background:color-mix(in srgb,var(--cyan) 5%,transparent)}
#v-subadm .pay tr.det td{white-space:normal;text-align:left;background:var(--panel-2);font-size:12.5px;line-height:1.65;color:var(--ink-2)}
#v-subadm .pay tr.det b{color:var(--ink)}
#v-subadm .pay .stp{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;border:1px solid var(--line-2);white-space:nowrap}
#v-subadm .pay .stp.ok{color:var(--fall);border-color:color-mix(in srgb,var(--fall) 55%,transparent)}
#v-subadm .pay .stp.wait{color:var(--amber);border-color:color-mix(in srgb,var(--amber) 55%,transparent)}
#v-subadm .pay .stp.bad{color:var(--rise);border-color:color-mix(in srgb,var(--rise) 55%,transparent)}
#v-subadm .pay .stp.mute{color:var(--ink-2)}
#v-subadm .pay .frm{display:grid;grid-template-columns:110px minmax(0,320px);gap:10px 14px;align-items:center;margin-top:8px}
#v-subadm .pay .frm label{font-size:13px;color:var(--ink-2)}
#v-subadm .pay .st{font-size:13px;min-height:18px;margin-top:8px}
#v-subadm .pay .st.bad{color:var(--rise)}#v-subadm .pay .st.ok{color:var(--fall)}
#subDlg .payd label{display:block;font-size:13px;color:var(--ink-2);margin:10px 0 4px}
#subDlg .payd .two{display:grid;grid-template-columns:1fr 1fr;gap:8px 12px}
#subDlg .payd input[type=number],#subDlg .payd input[type=date],#subDlg .payd input[type=text]{width:100%;box-sizing:border-box;height:36px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;font:inherit;font-size:14px}
#subDlg .payd .rad{display:flex;gap:8px;align-items:flex-start;color:var(--ink);font-size:14px;margin:6px 0}
#subDlg .payd .rad small{display:block;color:var(--ink-2);font-size:12.5px}
#subDlg .payd .kv{display:grid;grid-template-columns:96px minmax(0,1fr);gap:4px 10px;font-size:14px;margin:6px 0 4px}
#subDlg .payd .kv span{color:var(--ink-2)}
#subDlg .payd .warn{border:1px solid color-mix(in srgb,var(--amber) 55%,transparent);border-radius:8px;padding:8px 10px;font-size:13px;color:var(--ink);margin:8px 0}
@media (max-width:640px){
  #v-subadm .pay .frm{grid-template-columns:minmax(0,1fr);gap:4px}
  #v-subadm .pay .frm label{margin-top:6px}
  #subDlg .payd .two{grid-template-columns:minmax(0,1fr)}
}`);
  }
  const call = (p, b) => T().call(p, b || {});

  async function load() {
    const j = await call('/v1/admin/pay/list', {});
    if (j && j._s === 200) S.d = j;
    return j;
  }
  async function render(v) {
    css();
    if (!S.d) v.innerHTML = '<div class="card pay"><p class="muted">載入中…</p></div>';
    const j = await load();
    if (!(location.hash || '').startsWith('#admin/pay')) return;
    if (!j || j._s !== 200) { v.innerHTML = `<div class="card pay"><h3>付款與訂單</h3><p class="muted">${j && j._s === 403 ? '這個帳號不是管理者。' : '讀不到訂單（' + esc(j ? j._s : '連不到會員伺服器') + '）。'}</p></div>`; return; }
    paint(v);
  }
  function paint(v) {
    const d = S.d;
    const nAn = d.anomalies.length, nRev = d.orders.filter((o) => o.method === 'bank' && o.status === 'review').length;
    const nReq = (d.reqs || []).filter((r) => r.status === 'new').length;
    const tabs = [['bankord', '銀行轉帳訂單'], ['orders', '綠界訂單'], ['reqs', '取消／退款申請' + (nReq ? `<span class="anom" style="margin-left:4px;padding:0 6px;background:#e5484d;color:#fff">${nReq}</span>` : '')], ['subs', '會員訂閱'], ['refunds', '退款紀錄'], ['bank', '收款帳號設定']];
    v.innerHTML = `<div class="card pay" id="payAdm">
      <div class="hd"><h3>付款與訂單</h3>${d.test ? '<span class="tst" title="綠界正式金鑰還沒設：綠界付款走測試環境">綠界測試模式</span>' : ''}
        <span class="anom${nAn ? '' : ' zero'}" id="payAnom" title="已付款但沒開通、開通出錯、金額不符">異常 ${nAn}</span>
        ${nRev ? `<span class="anom" style="background:var(--amber);color:#04121a" id="payRevCnt">待確認轉帳 ${nRev}</span>` : ''}
        ${nReq ? `<span class="anom" style="background:#e5484d;color:#fff;cursor:pointer" id="payReqCnt" title="會員按了取消訂閱或申請退款，還沒處理">待處理申請 ${nReq}</span>` : ''}
        <span class="sp"></span><button type="button" id="payReload">重新整理</button></div>
      <div class="nbsw" id="payTabs" role="tablist" aria-label="付款與訂單分頁">${tabs.map(([k, n]) => `<button type="button" role="tab" data-ptab="${k}" class="${S.tab === k ? 'on' : ''}" aria-selected="${S.tab === k}">${n}</button>`).join('')}</div>
      <div id="payView"></div><div class="st" id="paySt" role="status"></div></div>`;
    v.querySelector('#payReload').onclick = () => render(v);
    const rq = v.querySelector('#payReqCnt'); if (rq) rq.onclick = () => { S.tab = 'reqs'; paint(v); };
    v.querySelectorAll('[data-ptab]').forEach((b) => { b.onclick = () => { S.tab = b.dataset.ptab; paint(v); }; });
    const box = v.querySelector('#payView');
    if (S.tab === 'orders' || S.tab === 'bankord') ordersView(v, box, S.tab === 'bankord' ? 'bank' : 'ecpay');
    else if (S.tab === 'reqs') reqsView(v, box);
    else if (S.tab === 'subs') subsView(v, box);
    else if (S.tab === 'refunds') refundsView(v, box);
    else bankView(v, box);
  }
  const st = (v, m, bad) => { const e = v.querySelector('#paySt'); if (e) { e.textContent = m; e.className = 'st ' + (bad ? 'bad' : 'ok'); } };

  /* ---------------------------------------------------------------- 寄信給客戶（2026-10-12 Andy：所有客戶 Mail 都能點擊回覆、信件內容依退回原因帶入方案／金額／原因）*/
  const perName = (o) => o.period === 'year' ? '年繳' : '月繳';
  function mailHref(email, o, reason) {
    let sub = '【哩股哩股】關於你的訂閱', body = `${email} 您好，\n\n`;
    if (o) {
      const stt = stName(o);
      sub = `【哩股哩股】關於你的訂單 ${o.id}（${o.planName}・${perName(o)}）`;
      body += `關於你的訂單 ${o.id}：\n方案：${o.planName}・${perName(o)}\n應付金額：NT$ ${nt(o.amount)}\n` + (o.last5 ? `你回報的匯款：NT$ ${nt(o.xferAmount)}（轉出帳號末 5 碼 ${o.last5}，${o.xferDate}）\n` : '') + `目前狀態：${stt}\n`;
      const why = reason || o.rejectReason || '';
      if (why) body += `\n原因：${why}\n`;
      if (o.status === 'rejected' || reason) body += '\n這筆訂單這次沒有開通。若你已經匯款，請依上面的原因確認或補正後，到「我的訂單」重新回報匯款資料；有任何問題也可以直接回覆這封信。\n';
    } else body += '\n';
    body += '\n哩股哩股 客服 敬上\nhttps://liguligu-puipui.com/';
    return 'mailto:' + encodeURIComponent(email).replace(/%40/g, '@') + '?subject=' + encodeURIComponent(sub) + '&body=' + encodeURIComponent(body);
  }
  const mailA = (email, o) => `<a class="ml" href="${esc(mailHref(email, o))}" title="用信箱寄信給 ${esc(email)}（內容會帶入訂單資料）" style="color:inherit;text-decoration:underline dotted">${esc(email)}</a>`;
  /* 退回原因快速字卡：預設幾張常用的，「＋」把目前輸入的字存成新字卡（存在這台瀏覽器），自訂的可點 × 刪除 */
  const RS_DEF = ['查無這筆入帳，請確認轉出帳號末 5 碼後重新回報', '匯款金額與應付金額不符，請補匯差額或來信聯絡', '轉帳日期或末 5 碼填寫有誤，請更正後重新回報', '訂單已逾期（超過 3 天未入帳），請重新下單', '重複下單或重複匯款，我們會另行聯絡退款', '你目前已是同方案或更高方案，不需要重複購買'];
  const rsLoad = () => { try { const j = JSON.parse(localStorage.getItem('twpay.reasons') || '[]'); return Array.isArray(j) ? j.filter((x) => typeof x === 'string').slice(0, 30) : []; } catch (e) { return []; } };
  const rsSave = (a) => { try { localStorage.setItem('twpay.reasons', JSON.stringify(a)); } catch (e) { /* 存不了就算了 */ } };

  /* 會員每一次匯款回報（不可改；重送的舊紀錄標「已作廢」）*/
  function repHist(o) {
    const a = o.reports || [];
    if (!a.length) return '';
    return `<div style="margin-top:8px;font-size:12.5px"><b>會員回報紀錄（${a.length} 筆）</b>${a.map((r, i) => `<div style="${r.state === 'void' ? 'opacity:.6;text-decoration:line-through' : ''}">${i + 1}. ${esc(ymdhm(r.at))} 送出：末 5 碼 ${esc(r.last5)}・轉帳日 ${esc(r.date)}・<b style="${r.amount < o.amount ? 'color:#e5484d' : r.amount > o.amount ? 'color:#30a46c' : ''}">NT$ ${nt(r.amount)}</b>${r.note ? '・' + esc(r.note) : ''}${r.state === 'void' ? `　<span style="text-decoration:none">（已作廢：${esc(r.voidWhy || '')}）</span>` : '　（目前這筆）'}</div>`).join('')}</div>`;
  }
  /* ---------------------------------------------------------------- ① 訂單 */
  /* 2026-10-11 Andy：未付款的不算訂單 → 預設不顯示「待付款」「已取消（未付款）」；對帳時打開「顯示未完成付款」 */
  const UNPAID = ['pending', 'cancelled'];
  const isUnpaid = (o) => UNPAID.includes(o.status) && !o.applied;
  function filtered(kind) {
    const f = S.f, d = S.d, exp = new Set(d.expiring);
    const t0 = f.from ? fromYmd(f.from) : 0, t1 = f.to ? fromYmd(f.to) + 86400000 : Infinity;
    const q = f.q.trim().toLowerCase();
    return d.orders.filter((o) => (f.all || f.status || !isUnpaid(o)) && (!kind || o.method === kind) && (!f.status || o.status === f.status)
      && o.created >= t0 && o.created < t1 && (!q || o.email.includes(q) || o.id.toLowerCase().includes(q)) && (!f.expiring || exp.has(o.email)));
  }
  function orderRow(o, actions, kind) {
    const acts = [];
    if (actions) {
      if (o.method === 'bank' && o.last5 && ['review', 'expired'].includes(o.status)) acts.push(`<button type="button" class="sm pri" data-pa="confirm" data-id="${esc(o.id)}">確認入帳並開通</button><button type="button" class="sm danger" data-pa="reject" data-id="${esc(o.id)}">退回</button>`);
      if (o.applied && o.status !== 'refunded') acts.push(`<button type="button" class="sm" data-pa="refund" data-id="${esc(o.id)}">退款</button>`);
      if (!o.applied && (o.anomaly || o.actErr || o.status === 'paid')) acts.push(`<button type="button" class="sm pri" data-pa="fix" data-id="${esc(o.id)}">補開通</button>`);
      if (o.applied && (o.anomaly || o.actErr)) acts.push(`<button type="button" class="sm" data-pa="ack" data-id="${esc(o.id)}">標記已處理</button>`);
      if (o.method === 'ecpay' && !o.parent && (!o.applied || o.recur)) acts.push(`<button type="button" class="sm" data-pa="sync" data-id="${esc(o.id)}">${o.recur && o.applied ? '對帳' : '查單'}</button>`);
      acts.push(`<button type="button" class="sm" data-pa="note" data-id="${esc(o.id)}">備註</button>`);
    }
    /* 2026-10-12 Andy：少於應付＝紅字、多於應付＝綠字、相同＝一般顏色（紅綠是金額對錯，不是台股漲跌） */
    const xa = o.method === 'bank' && o.last5 ? o.xferAmount : 0;
    const xc = !xa ? '' : xa < o.amount ? ' style="color:#e5484d;font-weight:700" title="少於應付金額 NT$ ' + nt(o.amount - xa) + '"' : xa > o.amount ? ' style="color:#30a46c;font-weight:700" title="多於應付金額 NT$ ' + nt(xa - o.amount) + '"' : '';
    const bankCols = kind === 'ecpay' ? '' : `<td class="n"${xc}>${xa ? nt(xa) + (xa < o.amount ? ' ⚠' : '') : ''}</td>`;
    const bankCols2 = kind === 'ecpay' ? '' : `<td style="text-align:center;font-variant-numeric:tabular-nums">${esc(o.last5 || '')}</td><td>${esc(o.xferDate || '')}</td>`;
    return `<tr class="prow" data-oid="${esc(o.id)}"><td>${esc(ymdhm(o.created))}</td><td class="l" title="${esc(o.email)}">${mailA(o.email, o)}</td><td>${esc(o.planName)}</td><td>${o.period === 'year' ? '年繳' : '月繳'}</td>
      <td class="n">${nt(o.amount)}</td>${bankCols}<td>${esc(methodName(o))}</td><td><span class="stp ${ST_CLS[o.status] || 'mute'}">${esc(stName(o))}</span></td>
      ${bankCols2}<td class="l" style="max-width:90px" title="${esc(o.adminNote)}">${esc(o.adminNote)}</td><td class="act">${acts.join('')}</td></tr>`
      + (S.open[o.id] ? `<tr class="det"><td colspan="${kind === 'ecpay' ? 9 : 12}">${detail(o)}</td></tr>` : '');
  }
  function detail(o) {
    const a = [`訂單 <b>${esc(o.id)}</b>${o.test ? '（測試）' : ''}`, o.name ? '會員：' + esc(o.name) : ''];
    if (o.paidAt) a.push('付款時間 <b>' + esc(ymdhm(o.paidAt)) + '</b>');
    if (o.grantTo) a.push(`開通期間 <b>${esc(ymd(o.grantFrom))}～${esc(ymd(o.grantTo))}</b>（${esc(o.actSrc)}，${esc(ymdhm(o.confirmedAt))}）`);
    if (o.tradeNo) a.push('綠界交易號 ' + esc(o.tradeNo)); if (o.payType) a.push('付款方式 ' + esc(o.payType));
    if (o.recur && !o.parent) a.push('自動續訂：' + (o.periodState === 'active' ? '開' : o.periodState === 'cancelled' ? '已取消 ' + esc(ymd(o.cancelAt)) : '—') + `・已扣 ${o.periodN || 0} 期`);
    if (o.note) a.push('會員備註：' + esc(o.note)); if (o.rejectReason) a.push('退回原因：' + esc(o.rejectReason));
    if (o.anomaly) a.push('<b style="color:var(--rise)">異常：' + esc(o.anomaly) + '</b>'); if (o.actErr) a.push('<b style="color:var(--rise)">開通出錯：' + esc(o.actErr) + '</b>');
    if (o.recvAmount) a.push(`管理者確認實收 <b>NT$ ${nt(o.recvAmount)}</b>`);
    if ((o.reports || []).length) a.push(repHist(o));
    if (o.rtnMsg) a.push('綠界訊息：' + esc(o.rtnMsg));
    (o.refundRows || []).forEach((r) => a.push(`退款 <b>NT$ ${nt(r.amount)}</b>・${r.status === 'done' ? '完成' : r.status === 'failed' ? '失敗' : '處理中'}・${r.kind === 'manual' ? '人工' + (r.acct_last5 ? '（退到末 5 碼 ' + esc(r.acct_last5) + '）' : '') : '綠界 ' + esc(r.action)}・${esc(r.rdate || ymd(r.created))}・${r.perm === 'end' ? '到期才停' : '立即降級'}${r.note ? '・' + esc(r.note) : ''}${r.msg ? '・' + esc(r.msg) : ''}`));
    return a.filter(Boolean).join('　');
  }
  const TH = '<thead><tr><th>時間</th><th>會員 email</th><th>方案</th><th>週期</th><th>應付金額</th><th>客戶匯款</th><th>方式</th><th>狀態</th><th>轉出末5碼</th><th>轉帳日期</th><th>備註</th><th></th></tr></thead>';
  const TH_EC = '<thead><tr><th>時間</th><th>會員 email</th><th>方案</th><th>週期</th><th>金額</th><th>方式</th><th>狀態</th><th>管理者備註</th><th></th></tr></thead>';
  function ordersView(v, box, kind) {
    const TH_K = kind === 'ecpay' ? TH_EC : TH;
    const d = S.d, f = S.f;
    const rev = d.orders.filter((o) => o.method === 'bank' && o.status === 'review');
    const an = d.orders.filter((o) => d.anomalies.includes(o.id) && o.method === kind);
    const list = filtered(kind);
    box.innerHTML = `${an.length ? `<div class="sec bad" id="payAnomSec"><h4>異常 <span class="cnt">${an.length}</span><small class="muted" style="margin:0">已付款但沒開通、開通出錯或金額不符 —— 先按「補開通」（綠界單會先查單確認）</small></h4><div class="tw"><table>${TH_K}<tbody>${an.map((o) => orderRow(o, true, kind)).join('')}</tbody></table></div></div>` : ''}
      ${kind === 'bank' ? `<div class="sec warn" id="payRevSec"><h4>待確認的轉帳 <span class="cnt">${rev.length}</span></h4>${rev.length ? `<div class="tw"><table>${TH}<tbody>${rev.map((o) => orderRow(o, true, 'bank')).join('')}</tbody></table></div>` : '<p class="muted" style="margin:0">沒有待確認的轉帳。</p>'}</div>` : ''}
      <div class="flt" id="payFlt">
        <select id="pfS" aria-label="狀態"><option value="">全部狀態</option>${Object.entries(ST).map(([k, n]) => `<option value="${k}"${f.status === k ? ' selected' : ''}>${n}</option>`).join('')}</select>
        <label>從 <input type="date" id="pfFrom" value="${esc(f.from)}"></label><label>到 <input type="date" id="pfTo" value="${esc(f.to)}"></label>
        <input type="search" id="pfQ" placeholder="搜尋 email／訂單號" value="${esc(f.q)}" aria-label="搜尋 email 或訂單號">
        <label title="待付款、已取消（未付款）：會員還沒付錢的單，預設不顯示"><input type="checkbox" id="pfAll"${f.all ? ' checked' : ''}> 顯示未完成付款（${d.orders.filter(isUnpaid).length}）</label>
        ${kind === 'bank' ? `<label title="最近一筆是轉帳、7 天內到期的會員"><input type="checkbox" id="pfExp"${f.expiring ? ' checked' : ''}> 即將到期的轉帳會員（${d.expiring.length}）</label>` : ''}
        <span style="flex:1"></span><button type="button" id="pfCsv">匯出 CSV（${list.length} 筆）</button></div>
      <div class="tw"><table id="payTbl">${TH_K}<tbody>${list.map((o) => orderRow(o, true, kind)).join('') || `<tr><td colspan="${kind === 'ecpay' ? 9 : 12}" class="muted">沒有符合的訂單</td></tr>`}</tbody></table></div>`;
    const re = () => ordersView(v, box, kind);
    box.querySelector('#pfS').onchange = (e) => { f.status = e.target.value; re(); };
    box.querySelector('#pfFrom').onchange = (e) => { f.from = e.target.value; re(); };
    box.querySelector('#pfTo').onchange = (e) => { f.to = e.target.value; re(); };
    const pe = box.querySelector('#pfExp'); if (pe) pe.onchange = (e) => { f.expiring = e.target.checked; re(); };
    box.querySelector('#pfAll').onchange = (e) => { f.all = e.target.checked; re(); };
    const q = box.querySelector('#pfQ'); q.oninput = () => { clearTimeout(q._t); q._t = setTimeout(() => { f.q = q.value; re(); const n = box.querySelector('#pfQ'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 250); };
    box.querySelector('#pfCsv').onclick = () => csvOrders(list);
    bindRows(v, box, re);
  }
  function bindRows(v, box, re) {
    box.querySelectorAll('tr.prow').forEach((tr) => { tr.onclick = (e) => { if (e.target.closest('button,a')) return; S.open[tr.dataset.oid] = !S.open[tr.dataset.oid]; re(); }; });
    box.querySelectorAll('[data-pa]').forEach((b) => { b.onclick = (e) => { e.stopPropagation(); act(v, b.dataset.pa, S.d.orders.find((o) => o.id === b.dataset.id)); }; });
  }

  /* ---------------------------------------------------------------- 取消／退款申請（2026-10-12 Andy：會員按退款後我這邊要收到通知、有分頁看紀錄）*/
  const RQ = { cancel: '取消訂閱', refund: '申請退款' };
  function reqsView(v, box) {
    const rs = S.d.reqs || [];
    box.innerHTML = `<p class="muted" style="margin:0 0 8px">會員在帳號選單按「取消訂閱」或「申請退款」都會列在這裡；紅色數字＝還沒處理。退款請到「銀行轉帳訂單／綠界訂單」找那筆按「退款」，處理完再回來按「標記已處理」。</p>
      <div class="tw"><table id="payReqs"><thead><tr><th>申請時間</th><th>種類</th><th>會員 email</th><th>當時方案</th><th>會員留言</th><th>狀態</th><th></th></tr></thead>
      <tbody>${rs.map((r) => `<tr><td>${esc(ymdhm(r.created))}</td><td>${esc(RQ[r.type] || r.type)}</td><td class="l">${mailA(r.email)}</td><td>${esc(((S.d.orders || []).find((o) => o.plan === r.plan) || {}).planName || r.plan || '')}</td><td class="l" style="max-width:260px" title="${esc(r.note || '')}">${esc(r.note || '')}</td>
        <td>${r.status === 'new' ? '<span class="stp bad">待處理</span>' : '<span class="stp ok">已處理</span>'}</td>
        <td class="act">${r.status === 'new' ? `<button type="button" class="sm pri" data-rqd="${esc(r.id)}">標記已處理</button>` : `<button type="button" class="sm" data-rqn="${esc(r.id)}">改回待處理</button>`}</td></tr>`).join('') || '<tr><td colspan="7" class="muted">沒有申請</td></tr>'}</tbody></table></div>`;
    const set = async (id, status) => { const r = await call('/v1/admin/feedback/set', { kind: 'request', id, status }); if (r && r._s === 200) { await load(); paint(v); st(v, status === 'done' ? '已標記處理' : '已改回待處理'); } else st(v, '沒有成功', true); };
    box.querySelectorAll('[data-rqd]').forEach((b) => { b.onclick = () => set(b.dataset.rqd, 'done'); });
    box.querySelectorAll('[data-rqn]').forEach((b) => { b.onclick = () => set(b.dataset.rqn, 'new'); });
  }

  /* ---------------------------------------------------------------- 動作（每個都先確認）*/
  async function done(v, r, okMsg) {
    if (r && r._s === 200 && r.ok !== false) { await load(); paint(v); st(v, okMsg); return true; }
    return false;
  }
  function act(v, k, o) {
    if (!o) return;
    const D = T().dialog;
    const who = `<div class="kv"><span>訂單</span><b>${esc(o.id)}</b><span>會員</span><b>${mailA(o.email, o)}</b><span>方案</span><b>${esc(o.planName)}・${o.period === 'year' ? '年繳' : '月繳'}</b><span>應付金額</span><b>NT$ ${nt(o.amount)}</b>${o.last5 ? `<span>客戶匯款</span><b${o.xferAmount < o.amount ? ' style="color:#e5484d"' : o.xferAmount > o.amount ? ' style="color:#30a46c"' : ''}>末 5 碼 ${esc(o.last5)}（${esc(o.xferDate)}，NT$ ${nt(o.xferAmount)}）${o.xferAmount < o.amount ? ' ⚠ 少於應付' : o.xferAmount > o.amount ? '（多於應付）' : ''}</b>` : ''}</div>`;
    const err = (dl, r) => { const m = dl.querySelector('.msg'); m.className = 'msg bad'; m.textContent = '沒有成功：' + ((r && (r.msg || (r.error === 'not_reported' ? '會員還沒回報匯款資料，不能確認入帳' : r.error === 'underpaid' ? '實收金額少於應付，不能開通' : r.error === 'need_received' ? '請輸入網銀實際入帳金額' : r.error))) || (r ? r._s : '連不到會員伺服器')); };
    if (k === 'confirm') {
      /* 2026-10-12 Andy：資金確認第二道 CHK —— 一定要輸入網銀實際入帳金額；少於應付按不下去（伺服器也擋） */
      const dl = D(`<div class="payd"><h3>確認入帳並開通？</h3>${who}${repHist(o)}
        <label for="pdRecv" style="display:block;margin-top:8px"><b>網銀實際入帳金額</b>（請登入網銀看這筆入帳，照實輸入）</label>
        <input type="text" id="pdRecv" inputmode="numeric" autocomplete="off" placeholder="例如 ${esc(o.amount)}">
        <div id="pdRecvM" style="margin:6px 0;font-size:13px"></div>
        <p>按下去會：① 這筆標成「已開通」② 會員立刻變成 <b>${esc(o.planName)}</b>，到期日${o.period === 'year' ? '加 12 個月' : '加 1 個月'}（從目前到期日或今天較晚的那天起算）③ 記一筆開通紀錄（含你輸入的實收金額）。</p>
        <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo" disabled>確認入帳並開通</button></div></div>`);
      const inp = dl.querySelector('#pdRecv'), go = dl.querySelector('#pdGo'), rm = dl.querySelector('#pdRecvM');
      const val = () => { const n = parseInt(String(inp.value).replace(/[,\s]/g, ''), 10); return Number.isInteger(n) && n > 0 ? n : 0; };
      inp.oninput = () => {
        const n = val();
        go.disabled = !(n >= o.amount); go.style.opacity = go.disabled ? '.35' : ''; go.style.cursor = go.disabled ? 'not-allowed' : '';
        rm.style.color = !n ? '' : n < o.amount ? '#e5484d' : n > o.amount ? '#30a46c' : '';
        rm.textContent = !n ? '' : n < o.amount ? `少收 NT$ ${nt(o.amount - n)}，不能開通。請按「退回」並寫原因（例如請補匯差額）。` : n > o.amount ? `多收 NT$ ${nt(n - o.amount)}，可以開通；多的部分請另外退還或備註。` : '金額相符。';
      };
      go.onclick = async () => { const n = val(); if (n < o.amount) return; go.disabled = true; const r = await call('/v1/admin/pay/confirm', { id: o.id, received: n }); if (await done(v, r, `已開通 ${o.email}（實收 NT$ ${nt(n)}）`)) dl.hidden = true; else { err(dl, r); go.disabled = false; } };
      go.style.opacity = '.35'; go.style.cursor = 'not-allowed';
      setTimeout(() => inp.focus(), 50);
    } else if (k === 'reject') {
      const dl = D(`<div class="payd"><h3>退回這筆轉帳？</h3>${who}<p>按下去會把這筆標成「已退回」，<b>不會開通</b>；會員在「我的訂單」看得到退回原因，可以重新回報。</p>
        <label for="pdWhy">退回原因（會員看得到）</label><input type="text" id="pdWhy" maxlength="200" placeholder="例如：查無這筆入帳／金額不符">
        <div id="pdChips" style="display:flex;flex-wrap:wrap;gap:6px;margin:8px 0" aria-label="常用退回原因"></div>
        <div class="msg" role="status"></div><div class="row2"><a id="pdMail" class="btn" href="#" style="margin-right:auto">寫信通知他</a><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">確定退回</button></div></div>`);
      const why = dl.querySelector('#pdWhy'), chips = dl.querySelector('#pdChips');
      const paintChips = () => {
        const mine = rsLoad();
        chips.innerHTML = RS_DEF.map((t, i) => `<button type="button" class="rsc" data-rs="${i}" style="background:var(--panel-2);color:var(--ink);border:1px solid var(--line);border-radius:14px;padding:4px 10px;font-size:12.5px;cursor:pointer;text-align:left;white-space:normal">${esc(t)}</button>`).join('')
          + mine.map((t, i) => `<span style="display:inline-flex;align-items:center;gap:2px"><button type="button" class="rsc" data-rm="${i}" style="background:var(--panel-2);color:var(--ink);border:1px solid var(--line);border-radius:14px;padding:4px 10px;font-size:12.5px;cursor:pointer;text-align:left;white-space:normal">${esc(t)}</button><button type="button" class="rsc" data-del="${i}" style="background:var(--panel-2);color:var(--ink);border:1px solid var(--line);border-radius:14px;padding:4px 10px;font-size:12.5px;cursor:pointer;text-align:left;white-space:normal;padding:4px 8px" title="刪除這張字卡" aria-label="刪除這張字卡">×</button></span>`).join('')
          + '<button type="button" class="rsc" id="pdAdd" style="background:var(--panel-2);color:var(--ink);border:1px solid var(--line);border-radius:14px;padding:4px 10px;font-size:12.5px;cursor:pointer;text-align:left;white-space:normal;font-weight:700" title="把上面輸入框目前的文字存成新字卡" aria-label="新增字卡">＋</button>';
        chips.querySelectorAll('[data-rs]').forEach((b) => { b.onclick = () => { why.value = RS_DEF[+b.dataset.rs]; why.focus(); }; });
        chips.querySelectorAll('[data-rm]').forEach((b) => { b.onclick = () => { why.value = rsLoad()[+b.dataset.rm] || ''; why.focus(); }; });
        chips.querySelectorAll('[data-del]').forEach((b) => { b.onclick = () => { const a = rsLoad(); a.splice(+b.dataset.del, 1); rsSave(a); paintChips(); }; });
        chips.querySelector('#pdAdd').onclick = () => {
          const t = why.value.trim();
          if (!t) { err(dl, { msg: '先在上面輸入框寫好原因，再按「＋」存成字卡' }); return; }
          const a = rsLoad(); if (!a.includes(t) && !RS_DEF.includes(t)) { a.push(t); rsSave(a); } paintChips();
          const m = dl.querySelector('.msg'); m.className = 'msg ok'; m.textContent = '已新增字卡';
        };
      };
      paintChips();
      const mailBtn = dl.querySelector('#pdMail');
      mailBtn.onclick = (e) => { mailBtn.href = mailHref(o.email, o, why.value.trim()); };
      dl.querySelector('#pdGo').onclick = async () => { const w = why.value.trim(); if (!w) { err(dl, { msg: '請寫退回原因' }); return; } const r = await call('/v1/admin/pay/reject', { id: o.id, reason: w }); if (await done(v, r, '已退回')) dl.hidden = true; else err(dl, r); };
    } else if (k === 'note') {
      const dl = D(`<div class="payd"><h3>管理者備註</h3>${who}<p class="muted">只有管理者看得到，會出現在清單與 CSV。</p><input type="text" id="pdNote" maxlength="300" value="${esc(o.adminNote)}">
        <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">儲存備註</button></div></div>`);
      dl.querySelector('#pdGo').onclick = async () => { const r = await call('/v1/admin/pay/note', { id: o.id, note: dl.querySelector('#pdNote').value }); if (await done(v, r, '已存備註')) dl.hidden = true; else err(dl, r); };
    } else if (k === 'fix') {
      const ec = o.method === 'ecpay' && !o.parent;
      const dl = D(`<div class="payd"><h3>補開通？</h3>${who}${o.anomaly ? `<p class="warn">異常：${esc(o.anomaly)}</p>` : ''}${o.actErr ? `<p class="warn">開通出錯：${esc(o.actErr)}</p>` : ''}
        <p>${ec ? '會先向綠界<b>查單</b>：確定已付款、金額相符就開通。查單不過時可以按「強制開通」（請先在綠界後台確認這筆真的收到錢）。' : '會把這筆開通（期間照月繳／年繳加上去），同一筆不會加兩次。'}</p>
        <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button>${ec ? '<button type="button" id="pdForce">強制開通</button>' : ''}<button type="button" class="pri" id="pdGo">${ec ? '查單並開通' : '補開通'}</button></div></div>`);
      dl.querySelector('#pdGo').onclick = async () => { const r = await call('/v1/admin/pay/reactivate', { id: o.id, force: !ec }); if (await done(v, r, '已補開通')) dl.hidden = true; else err(dl, r); };
      const fz = dl.querySelector('#pdForce'); if (fz) fz.onclick = async () => { const r = await call('/v1/admin/pay/reactivate', { id: o.id, force: true }); if (await done(v, r, '已強制開通')) dl.hidden = true; else err(dl, r); };
    } else if (k === 'ack') {
      const dl = D(`<div class="payd"><h3>標記已處理？</h3>${who}<p class="warn">${esc(o.anomaly || o.actErr)}</p><p>這筆已經開通了。確認你看過、處理完（例如跟會員聯絡過）後按下去，就會從異常清單拿掉；訂單本身不變。</p>
        <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">標記已處理</button></div></div>`);
      dl.querySelector('#pdGo').onclick = async () => { const r = await call('/v1/admin/pay/ack', { id: o.id }); if (await done(v, r, '已標記處理')) dl.hidden = true; else err(dl, r); };
    } else if (k === 'sync') {
      (async () => { st(v, '向綠界查單中…'); const r = await call('/v1/admin/pay/sync', { id: o.id }); await load(); paint(v); st(v, r && r.ok ? (r.added != null ? `對帳完成，補了 ${r.added} 期` : r.dup ? '已經開通過' : '查單完成') : '查單結果：' + ((r && (r.error === 'unpaid' ? '還沒付款' : r.error)) || '連不到'), !(r && r.ok)); })();
    } else if (k === 'refund') refundDlg(v, o);
  }
  async function refundDlg(v, o) {
    const q = await call('/v1/admin/pay/refund_quote', { id: o.id });
    if (!q || q._s !== 200) { st(v, '讀不到可退金額', true); return; }
    const rid = 'r-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    const manual = q.kind === 'manual';
    const today = ymd(Date.now());
    const dl = T().dialog(`<div class="payd" id="payRefundDlg"><h3>退款</h3>
      <div class="kv"><span>訂單</span><b>${esc(o.id)}</b><span>會員</span><b>${esc(o.email)}</b><span>付款方式</span><b>${esc(methodName(o))}${o.payType ? '（' + esc(o.payType) + '）' : ''}</b><span>訂單金額</span><b>NT$ ${nt(o.amount)}</b><span>可退金額</span><b id="rfLeft">NT$ ${nt(q.left)}</b><span>試算</span><b>NT$ ${nt(q.suggest)}<small style="color:var(--ink-2);font-weight:400">・${esc(q.rule)}</small></b></div>
      <label for="rfAmt">退款金額（可改）</label><input type="number" id="rfAmt" min="1" max="${q.left}" value="${q.suggest || q.left}">
      <label>退款後權限</label>
      <label class="rad"><input type="radio" name="rfPerm" value="now" checked><span>立即降級<small>會員馬上回到註冊會員</small></span></label>
      <label class="rad"><input type="radio" name="rfPerm" value="end"><span>到期才停<small>用到 ${esc(ymd(o.grantTo))} 才回到註冊會員</small></span></label>
      ${q.recur && q.periodActive ? '<p class="warn">這是信用卡定期定額：退款時會同時向綠界<b>終止之後的自動扣款</b>。</p>' : ''}
      ${manual ? `<p class="warn">${o.method === 'bank' ? '銀行轉帳' : 'ATM／超商付款'}沒辦法用 API 退款：這裡只做<b>登記</b>，<b>請到網銀把錢匯回</b>給會員。</p>
        <div class="two"><div><label for="rfL5">退款帳號末 5 碼</label><input type="text" id="rfL5" inputmode="numeric" maxlength="5"></div><div><label for="rfDate">退款日期</label><input type="date" id="rfDate" value="${esc(today)}"></div></div>`
        : q.test ? '<p class="warn">綠界<b>測試環境不提供信用卡退刷 API</b>（官方文件註明）。請到綠界後台退刷後，用下面「改登記人工退款」記錄。</p>'
          : '<p class="muted">會向綠界送出退款：還在授權階段 → 放棄授權（N）；已關帳 → 退刷（R）；部分退款且未關帳 → 調整關帳金額（C）。成功才標「已退款」，失敗會顯示綠界的原因。</p>'}
      <label for="rfNote">備註（選填）</label><input type="text" id="rfNote" maxlength="200">
      ${!manual ? '<label class="rad"><input type="checkbox" id="rfManual"><span>改登記人工退款（已在綠界後台操作過）<small>勾了就不呼叫綠界，只記錄</small></span></label><div class="two" id="rfManBox" hidden><div><label for="rfDate2">退款日期</label><input type="date" id="rfDate2" value="' + esc(today) + '"></div></div>' : ''}
      <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="rfGo">確定退款</button></div></div>`);
    const mb = dl.querySelector('#rfManual'); if (mb) mb.onchange = () => { dl.querySelector('#rfManBox').hidden = !mb.checked; };
    const go = dl.querySelector('#rfGo');
    go.onclick = async () => {
      const m = dl.querySelector('.msg');
      const amount = parseInt(dl.querySelector('#rfAmt').value, 10);
      if (!Number.isInteger(amount) || amount < 1 || amount > q.left) { m.className = 'msg bad'; m.textContent = `金額要在 1～${q.left} 之間`; return; }
      const asManual = manual || (mb && mb.checked);
      const body = { id: o.id, rid, amount, perm: dl.querySelector('input[name=rfPerm]:checked').value, note: dl.querySelector('#rfNote').value.trim(), manual: !!asManual };
      if (manual) { body.last5 = dl.querySelector('#rfL5').value.trim(); body.date = dl.querySelector('#rfDate').value; if (!/^\d{5}$/.test(body.last5)) { m.className = 'msg bad'; m.textContent = '請填退款帳號末 5 碼'; return; } }
      else if (asManual) body.date = dl.querySelector('#rfDate2').value;
      go.disabled = true; m.className = 'msg'; m.textContent = asManual ? '登記中…' : '向綠界送出退款…';
      const r = await call('/v1/admin/pay/refund', body);
      if (await done(v, r, `已退款 NT$ ${nt(amount)}（${o.email}）`)) { dl.hidden = true; return; }
      go.disabled = false; m.className = 'msg bad';
      m.textContent = '退款沒有成功：' + ((r && (r.msg || ({ over: '超過可退金額', running: '這筆有退款正在處理中', bad_last5: '請填退款帳號末 5 碼', bad_date: '請選退款日期', stage_no_refund: '測試環境不能退刷' })[r.error] || r.error)) || '連不到會員伺服器');
    };
  }

  /* ---------------------------------------------------------------- ② 會員訂閱 */
  const subMethod = (s) => (s.method === 'period' ? '信用卡定期定額' : s.method === 'bank' ? '銀行轉帳' : '單次付款');
  function subsView(v, box) {
    const d = S.d, subs = d.subs;
    const ev = (email) => d.events.filter((e) => e.email === email);
    box.innerHTML = `<p class="muted">每個付過錢的會員一列。權限以伺服器的到期日為準：到期日一過自動回到註冊會員，並記一筆「到期降級」。點一列看他所有訂單、退款與方案異動。</p>
      <div class="flt"><span style="flex:1"></span><button type="button" id="psCsv">匯出 CSV（${subs.length} 人）</button></div>
      <div class="tw"><table id="paySubs"><thead><tr><th>會員 email</th><th>目前方案</th><th>付款方式</th><th>第一次付款</th><th>最近付款</th><th>週期</th><th>本期開始</th><th>到期日</th><th>自動續訂</th><th>到期後降回註冊會員</th><th>累計付款</th><th>筆數</th></tr></thead>
      <tbody>${subs.map((s) => `<tr class="prow" data-em="${esc(s.email)}"><td class="l" title="${esc(s.email)}">${mailA(s.email)}</td><td>${esc(s.expired ? '註冊會員（已到期）' : s.planName)}</td><td>${esc(subMethod(s))}</td>
        <td>${esc(ymd(s.firstPaid))}</td><td>${esc(ymd(s.lastPaid))}</td><td>${s.period === 'year' ? '年繳' : '月繳'}</td><td>${esc(ymd(s.curFrom))}</td><td>${esc(ymd(s.expires))}</td>
        <td>${s.autoRenew ? '<span class="stp ok">開</span>' : s.recur ? '<span class="stp mute">已取消</span>' : '<span class="muted" title="銀行轉帳與單次付款是預付制，沒有自動扣款">不適用</span>'}</td><td>${s.downgradeAt ? esc(ymd(s.downgradeAt)) : '自動續扣中'}</td>
        <td class="n">${nt(s.total)}${s.refunded ? `<small style="color:var(--rise)">（退 ${nt(s.refunded)}）</small>` : ''}</td><td class="n">${s.count}</td></tr>`
        + (S.open['s:' + s.email] ? `<tr class="det"><td colspan="12"><div class="tw"><table>${TH}<tbody>${d.orders.filter((o) => o.email === s.email).map((o) => orderRow(o, true)).join('')}</tbody></table></div>
          <p style="margin:6px 0 0">方案異動：${ev(s.email).map((e) => `${esc(ymdhm(e.at))} ${esc(EV[e.kind] || e.kind)}${e.detail ? '（' + esc(e.detail) + '）' : ''}`).join('　') || '—'}</p></td></tr>` : '')).join('') || '<tr><td colspan="12" class="muted">還沒有付費會員</td></tr>'}</tbody></table></div>`;
    box.querySelector('#psCsv').onclick = () => csvSubs(subs);
    box.querySelectorAll('tr.prow[data-em]').forEach((tr) => { tr.onclick = (e) => { if (e.target.closest('button,a')) return; const k = 's:' + tr.dataset.em; S.open[k] = !S.open[k]; subsView(v, box); }; });
    box.querySelectorAll('[data-pa]').forEach((b) => { b.onclick = (e) => { e.stopPropagation(); act(v, b.dataset.pa, S.d.orders.find((o) => o.id === b.dataset.id)); }; });
  }

  /* ---------------------------------------------------------------- ③ 退款紀錄 */
  function refundsView(v, box) {
    const rs = S.d.refunds;
    box.innerHTML = `<div class="flt"><span class="muted" style="margin:0">所有退款（含失敗的嘗試）。</span><span style="flex:1"></span><button type="button" id="prCsv">匯出 CSV（${rs.length} 筆）</button></div>
      <div class="tw"><table id="payRefunds"><thead><tr><th>時間</th><th>訂單</th><th>會員 email</th><th>金額</th><th>方式</th><th>結果</th><th>權限</th><th>退款帳號末5碼</th><th>退款日期</th><th>備註</th><th>操作者</th></tr></thead>
      <tbody>${rs.map((r) => `<tr><td>${esc(ymdhm(r.created))}</td><td>${esc(r.oid)}</td><td class="l">${mailA(r.email)}</td><td class="n">${nt(r.amount)}</td><td>${r.kind === 'manual' ? '人工登記' : '綠界 ' + esc(r.action)}</td>
        <td><span class="stp ${r.status === 'done' ? 'ok' : r.status === 'failed' ? 'bad' : 'wait'}">${r.status === 'done' ? '完成' : r.status === 'failed' ? '失敗' : '處理中'}</span></td><td>${r.perm === 'end' ? '到期才停' : '立即降級'}</td>
        <td>${esc(r.acct_last5)}</td><td>${esc(r.rdate)}</td><td class="l" title="${esc((r.note || '') + (r.msg ? '／' + r.msg : ''))}">${esc(r.note)}${r.msg ? '／' + esc(r.msg) : ''}</td><td class="l">${esc(r.by)}</td></tr>`).join('') || '<tr><td colspan="11" class="muted">沒有退款</td></tr>'}</tbody></table></div>`;
    box.querySelector('#prCsv').onclick = () => csvRefunds(rs);
  }

  /* ---------------------------------------------------------------- ④ 收款帳號設定 */
  function bankView(v, box) {
    const b = S.d.bank || {};
    box.innerHTML = `<p class="muted">會員選「銀行轉帳」時看到的收款資訊。存在會員伺服器的設定裡（<b>不寫進網站程式碼</b>，public repo 看不到）；只有已登入的會員在結帳時看得到。沒填之前，轉帳分頁會顯示「尚未開放」。</p>
      <div class="frm" id="payBankFrm">
        <label for="pbName">銀行名稱</label><input id="pbName" maxlength="30" value="${esc(b.bank_name || '')}" placeholder="例如：○○銀行">
        <label for="pbCode">銀行代碼</label><input id="pbCode" maxlength="3" inputmode="numeric" value="${esc(b.bank_code || '')}" placeholder="3 碼">
        <label for="pbAcct">帳號</label><input id="pbAcct" maxlength="24" inputmode="numeric" value="${esc(b.account || '')}">
        <label for="pbHolder">戶名</label><input id="pbHolder" maxlength="40" value="${esc(b.holder || '')}">
        <span></span><div style="display:flex;gap:8px"><button type="button" class="pri" id="pbSave">儲存</button>${S.d.bank ? '<button type="button" class="danger" id="pbClear">關閉銀行轉帳</button>' : ''}</div></div>`;
    box.querySelector('#pbSave').onclick = () => {
      const body = { bank_name: box.querySelector('#pbName').value.trim(), bank_code: box.querySelector('#pbCode').value.trim(), account: box.querySelector('#pbAcct').value.trim(), holder: box.querySelector('#pbHolder').value.trim() };
      const dl = T().dialog(`<div class="payd"><h3>儲存收款帳號？</h3><div class="kv"><span>銀行</span><b>${esc(body.bank_name)}（${esc(body.bank_code)}）</b><span>帳號</span><b>${esc(body.account)}</b><span>戶名</span><b>${esc(body.holder)}</b></div>
        <p>儲存後，會員在結帳的「銀行轉帳」分頁會<b>立刻看到這組帳號</b>。請再核對一次帳號。</p><div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">確定儲存</button></div></div>`);
      dl.querySelector('#pdGo').onclick = async () => {
        const r = await call('/v1/admin/pay/bank/put', body);
        if (await done(v, r, '收款帳號已儲存')) { dl.hidden = true; return; }
        const m = dl.querySelector('.msg'); m.className = 'msg bad'; m.textContent = r && r.error === 'bad_input' ? '格式不對：代碼要 3 碼數字、帳號 6～20 碼數字、名稱與戶名要填' : '沒有存進去';
      };
    };
    const cl = box.querySelector('#pbClear');
    if (cl) cl.onclick = () => {
      const dl = T().dialog('<div class="payd"><h3>關閉銀行轉帳？</h3><p>清掉收款帳號後，結帳的「銀行轉帳」分頁會顯示「尚未開放」。已經建立的轉帳訂單不受影響，照樣可以確認入帳。</p><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">確定關閉</button></div></div>');
      dl.querySelector('#pdGo').onclick = async () => { const r = await call('/v1/admin/pay/bank/put', { clear: true }); if (await done(v, r, '已關閉銀行轉帳')) dl.hidden = true; };
    };
  }

  /* ---------------------------------------------------------------- CSV（含 BOM：Excel 直接開不亂碼）*/
  function csv(name, head, rows) {
    const q = (x) => { const s = String(x == null ? '' : x); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
    const txt = '﻿' + [head, ...rows].map((r) => r.map(q).join(',')).join('\r\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([txt], { type: 'text/csv;charset=utf-8' }));
    a.download = `${name}_${ymd(Date.now())}.csv`;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    window.__payCsv = txt;   // 驗收用：最後一次匯出的內容
  }
  function csvOrders(list) {
    csv('訂單', ['訂單編號', '建立時間', '會員email', '方案', '週期', '金額', '方式', '付款類型', '狀態', '付款時間', '開通起', '開通迄', '轉出末5碼', '轉帳日期', '轉帳金額', '綠界交易號', '已退款金額', '退款明細', '自動續訂', '母訂單', '期數', '會員備註', '管理者備註', '退回原因', '測試'],
      list.map((o) => [o.id, ymdhm(o.created), o.email, o.planName, o.period === 'year' ? '年繳' : '月繳', o.amount, methodName(o), o.payType, stName(o), ymdhm(o.paidAt), ymd(o.grantFrom), ymd(o.grantTo), o.last5, o.xferDate, o.xferAmount || '', o.tradeNo, o.refunded || 0,
        (o.refundRows || []).filter((r) => r.status === 'done').map((r) => `${r.amount}@${r.rdate || ymd(r.done_at)}${r.acct_last5 ? '→' + r.acct_last5 : ''}`).join('; '),
        o.recur && !o.parent ? (o.periodState === 'active' ? '開' : '關') : '', o.parent || '', o.periodN || '', o.note, o.adminNote, o.rejectReason, o.test ? '是' : '']));
  }
  function csvSubs(subs) {
    csv('會員訂閱', ['會員email', '目前方案', '付款方式', '第一次付款', '最近付款', '週期', '本期開始', '到期日', '自動續訂', '到期後降回註冊會員', '累計付款（扣退款）', '退款合計', '筆數'],
      subs.map((s) => [s.email, s.expired ? '註冊會員（已到期）' : s.planName, subMethod(s), ymdhm(s.firstPaid), ymdhm(s.lastPaid), s.period === 'year' ? '年繳' : '月繳', ymd(s.curFrom), ymd(s.expires), s.autoRenew ? '開' : '關', s.downgradeAt ? ymd(s.downgradeAt) : '自動續扣中', s.total, s.refunded, s.count]));
  }
  function csvRefunds(rs) {
    csv('退款', ['退款編號', '建立時間', '完成時間', '訂單編號', '會員email', '金額', '方式', '綠界動作', '結果', '權限處理', '退款帳號末5碼', '退款日期', '備註', '綠界訊息', '操作者'],
      rs.map((r) => [r.id, ymdhm(r.created), ymdhm(r.done_at), r.oid, r.email, r.amount, r.kind === 'manual' ? '人工登記' : '綠界', r.action, r.status === 'done' ? '完成' : r.status === 'failed' ? '失敗' : '處理中', r.perm === 'end' ? '到期才停' : '立即降級', r.acct_last5, r.rdate, r.note, r.msg, r.by]));
  }

  (window.TwSubRoutes = window.TwSubRoutes || []).push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'pay' || !T()) return null;
    const v = T().view('v-subadm'); if (!v) return null;
    render(v);
    return 'v-subadm';
  });
  window.TwAdminPay = { render, state: () => S };
})();
