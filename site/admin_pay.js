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
   2026-10-16 Andy：「這邊好亂…一個mail 身份只能存在一個，若他有最新的一筆資訊，就只會留下最新的一筆」「會多出現已退款功能按鈕 並且跳到退款紀錄那邊紀錄」
     「並且需要制定完善的措施」→ 分頁關係與規則手冊寫在 docs/payment_admin_tabs_1016.md：
     · 待確認的轉帳、取消／退款申請：同一個 email 只顯示最新一筆（後端 payReconcile 會把舊的結案／標「已被取代」）
     · 訂單完整列表、退款紀錄、申請：依 email 摺疊，只顯示最新一筆，「＋N 筆歷史」展開
     · 退款申請多一顆「已退款」→ 跳到「退款紀錄」分頁、預填會員與對應訂單、直接打開退款登記；登記完成那筆申請自動變已處理
     · 每個動作送出「我看到的狀態」（expect）：另一位管理者剛處理過 → 伺服器回 409，畫面重新整理並說是誰處理的
     · 第七個分頁「操作紀錄」：誰、何時、做了什麼、前後狀態
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
  const ST = { pending: '待付款', review: '待確認', paid: '已入帳', active: '已開通', failed: '失敗', rejected: '已退回', expired: '已逾期', refunded: '已退款', cancelled: '已取消（未付款）', superseded: '已被取代' };
  const ST_CLS = { pending: 'wait', review: 'wait', paid: 'wait', active: 'ok', failed: 'bad', rejected: 'bad', expired: 'mute', refunded: 'mute', cancelled: 'mute', superseded: 'mute' };
  const EV = { activate: '開通', extend: '延長', expire: '到期降級', refund_downgrade: '退款降級', refund_keep: '退款（到期才停）', auto_renew_off: '取消自動續訂' };
  const S = { d: null, tab: 'bankord', f: { method: '', status: '', from: '', to: '', q: '', expiring: false, all: false }, open: {}, pre: null, aq: '' };
  /* 依 email 摺疊：每個 email 一組，latest＝最新一筆、older＝其他（新到舊）；組與組之間照最新一筆的時間新到舊 */
  const byEmail = (list, at) => {
    const m = new Map();
    for (const x of list) { const k = String(x.email || '').toLowerCase(); if (!m.has(k)) m.set(k, []); m.get(k).push(x); }
    return [...m.entries()].map(([email, a]) => { a.sort((p, q) => at(q) - at(p)); return { email, latest: a[0], older: a.slice(1) }; }).sort((p, q) => at(q.latest) - at(p.latest));
  };
  const histBtn = (key, n) => (n ? `<button type="button" class="sm hist" data-hist="${esc(key)}" aria-expanded="${!!S.open['h:' + key]}" title="這個 email 還有 ${n} 筆較舊的紀錄">${S.open['h:' + key] ? '收起歷史' : `＋${n} 筆歷史`}</button>` : '');
  const bindHist = (box, re) => box.querySelectorAll('[data-hist]').forEach((b) => { b.onclick = (e) => { e.stopPropagation(); const k = 'h:' + b.dataset.hist; S.open[k] = !S.open[k]; re(); }; });
  /* 衝突（另一位管理者剛處理過、重複按、狀態不允許）：伺服器回 409 → 重新整理畫面、寫清楚是誰什麼時候處理的 */
  const CONFLICT = ['stale', 'same_status', 'req_done', 'bad_status', 'already_refunded', 'applied'];
  const whoTxt = (r) => (r && r.lastBy ? `（上一個動作：${r.lastBy}，${ymdhm(r.lastAt)}）` : r && r.closedBy ? `（${r.closedBy}，${ymdhm(r.closedAt)}）` : '');
  async function conflict(v, dl, r) {
    if (!r || !CONFLICT.includes(r.error)) return false;
    if (dl) dl.hidden = true;
    await load(); paint(v);
    st(v, (r.msg || '這筆的狀態已經變了，畫面已重新整理') + whoTxt(r), true);
    return true;
  }
  const methodName = (o) => o.method === 'bank' ? '銀行轉帳' : o.recur ? (o.parent ? `綠界自動扣款 第${o.periodN}期` : '綠界定期定額') : '綠界信用卡';
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
#v-subadm .pay td.act{text-align:right;white-space:normal;min-width:200px}
#v-subadm .pay td.act button{margin:2px 0 2px 4px}
#v-subadm .pay tr.prow{cursor:pointer}
#v-subadm .pay tr.prow:hover td{background:color-mix(in srgb,var(--cyan) 5%,transparent)}
#v-subadm .pay tr.det td{white-space:normal;text-align:left;background:var(--panel-2);font-size:12.5px;line-height:1.65;color:var(--ink-2)}
#v-subadm .pay tr.det b{color:var(--ink)}
#v-subadm .pay tr.old td{opacity:.62;background:color-mix(in srgb,var(--ink-2) 6%,transparent)}
#v-subadm .pay td.wrap{white-space:normal}
#v-subadm .pay .why{font-size:11.5px;color:var(--ink-2);line-height:1.4;margin-top:2px;white-space:normal;max-width:240px}
#v-subadm .pay button.hist{color:var(--cyan);border-style:dashed}
#v-subadm .pay button:disabled{opacity:.4;cursor:not-allowed}
#v-subadm .pay td.l .hist{display:block;margin-top:3px}
#v-subadm .pay td.l:has(.hist){overflow:visible}
/* 10-16：≤820 時 support.js 把整個管理區的表格改成一列一張卡（display:block）→ 付款頁的格子改成一行流式排列、不要固定 32px 高（原因文字才不會被裁掉）*/
@media (max-width:820px){
  #v-subadm .pay tbody tr{display:flex!important;flex-wrap:wrap;align-items:center;gap:2px 12px;padding:8px 4px}
  #v-subadm .pay tbody td{display:block;height:auto;max-width:none!important;text-align:left;white-space:normal;padding:2px 0}
  #v-subadm .pay tbody td:empty{display:none}
  #v-subadm .pay tbody td.act,#v-subadm .pay tbody td.wrap,#v-subadm .pay tr.det td{flex:1 1 100%;text-align:left}
  #v-subadm .pay td.act button{margin:2px 6px 2px 0}
}
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
    const nAn = d.anomalies.length;
    /* 一個 email 只算一件：以每個 email 最新的那筆申請為準 */
    const nReq = byEmail(d.reqs || [], (r) => r.created).filter((g) => g.latest.status === 'new').length;
    const nRev = byEmail(d.orders.filter((o) => o.method === 'bank' && o.status === 'review'), (o) => o.created).length;
    const tabs = [['bankord', '銀行轉帳訂單'], ['orders', '綠界訂單'], ['reqs', '取消／退款申請' + (nReq ? `<span class="anom" style="margin-left:4px;padding:0 6px;background:#e5484d;color:#fff">${nReq}</span>` : '')], ['subs', '會員訂閱'], ['refunds', '退款紀錄'], ['bank', '收款帳號設定'], ['audit', '操作紀錄']];
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
    else if (S.tab === 'audit') auditView(v, box);
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
  /* 可退款：開通過且沒全額退；或被取代的轉帳單（會員回報過匯款、沒開通 → 退回多匯的錢）*/
  const refundable = (o) => o.status !== 'refunded' && ((o.applied && (o.refunded || 0) < (o.recvAmount || o.amount)) || (o.method === 'bank' && o.status === 'superseded' && !!o.last5 && !(o.refunded > 0)));
  function orderRow(o, actions, kind, extra) {
    const acts = [];
    if (actions) {
      if (o.method === 'bank' && o.last5 && ['review', 'expired', 'superseded'].includes(o.status)) acts.push(`<button type="button" class="sm pri" data-pa="confirm" data-id="${esc(o.id)}">確認入帳並開通</button><button type="button" class="sm danger" data-pa="reject" data-id="${esc(o.id)}">退回</button>`);
      /* 2026-10-16 Andy：「金額直接當客戶寫死對應金額，只有我這還有可以更改」→ 還沒開通的轉帳單可以改金額 */
      if (o.method === 'bank' && !o.applied && ['pending', 'review', 'expired', 'rejected', 'superseded'].includes(o.status)) acts.push(`<button type="button" class="sm" data-pa="amt" data-id="${esc(o.id)}">改金額</button>`);
      if (refundable(o)) acts.push(`<button type="button" class="sm" data-pa="refund" data-id="${esc(o.id)}">退款</button>`);
      if (!o.applied && o.method !== 'bank' && !o.refunded && o.status !== 'refunded' && (o.anomaly || o.actErr || o.status === 'paid')) acts.push(`<button type="button" class="sm pri" data-pa="fix" data-id="${esc(o.id)}">補開通</button>`);
      if (o.applied && (o.anomaly || o.actErr)) acts.push(`<button type="button" class="sm" data-pa="ack" data-id="${esc(o.id)}">標記已處理</button>`);
      if (o.method === 'ecpay' && !o.parent && (!o.applied || o.recur)) acts.push(`<button type="button" class="sm" data-pa="sync" data-id="${esc(o.id)}">${o.recur && o.applied ? '對帳' : '查單'}</button>`);
      acts.push(`<button type="button" class="sm" data-pa="note" data-id="${esc(o.id)}">備註</button>`);
    }
    /* 2026-10-12 Andy：少於應付＝紅字、多於應付＝綠字、相同＝一般顏色（紅綠是金額對錯，不是台股漲跌） */
    const xa = o.method === 'bank' && o.last5 ? o.xferAmount : 0;
    const xc = !xa ? '' : xa < o.amount ? ' style="color:#e5484d;font-weight:700" title="少於應付金額 NT$ ' + nt(o.amount - xa) + '"' : xa > o.amount ? ' style="color:#30a46c;font-weight:700" title="多於應付金額 NT$ ' + nt(xa - o.amount) + '"' : '';
    const bankCols = kind === 'ecpay' ? '' : `<td class="n"${xc}>${xa ? nt(xa) + (xa < o.amount ? ' ⚠' : '') : ''}</td>`;
    const bankCols2 = kind === 'ecpay' ? '' : `<td style="text-align:center;font-variant-numeric:tabular-nums">${esc(o.last5 || '')}</td><td>${esc(o.xferDate || '')}</td>`;
    const nameCol = `<td class="l pname" title="${esc(o.payerName || '')}">${esc(o.payerName || '')}</td>`;
    return `<tr class="prow${extra && extra.old ? ' old' : ''}" data-oid="${esc(o.id)}"><td>${esc(ymdhm(o.created))}</td><td class="l" title="${esc(o.email)}">${mailA(o.email, o)}${extra && extra.hist ? extra.hist : ''}</td>${nameCol}<td>${esc(o.planName)}</td><td>${o.period === 'year' ? '年繳' : '月繳'}</td>
      <td class="n">${nt(o.amount)}</td>${bankCols}<td>${esc(methodName(o))}</td><td><span class="stp ${ST_CLS[o.status] || 'mute'}">${esc(stName(o))}</span></td>
      ${bankCols2}<td class="l" style="max-width:90px" title="${esc(o.adminNote)}">${esc(o.adminNote)}</td><td class="act">${acts.join('')}</td></tr>`
      + (S.open[o.id] ? `<tr class="det"><td colspan="${kind === 'ecpay' ? 9 : 13}">${detail(o)}</td></tr>` : '');
  }
  function detail(o) {
    const a = [`訂單 <b>${esc(o.id)}</b>${o.test ? '（測試）' : ''}`, o.name ? '會員：' + esc(o.name) : ''];
    if (o.payerName) a.push('匯款人姓名 <b>' + esc(o.payerName) + '</b>');
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
  const TH = '<thead><tr><th>時間</th><th>會員 email</th><th>匯款人姓名</th><th>方案</th><th>週期</th><th>應付金額</th><th>客戶匯款</th><th>方式</th><th>狀態</th><th>轉出末5碼</th><th>轉帳日期</th><th>備註</th><th></th></tr></thead>';
  const TH_EC = '<thead><tr><th>時間</th><th>會員 email</th><th>姓名</th><th>方案</th><th>週期</th><th>金額</th><th>方式</th><th>狀態</th><th>管理者備註</th><th></th></tr></thead>';
  function ordersView(v, box, kind) {
    const TH_K = kind === 'ecpay' ? TH_EC : TH;
    const d = S.d, f = S.f;
    /* 待確認：一個 email 只顯示最新一筆（後端規則本來就只會留一筆，這裡再保險一次）*/
    const rev = byEmail(d.orders.filter((o) => o.method === 'bank' && o.status === 'review'), (o) => o.created).map((g) => g.latest);
    const an = d.orders.filter((o) => d.anomalies.includes(o.id) && o.method === kind);
    const list = filtered(kind);
    const grp = byEmail(list, (o) => o.created);
    box.innerHTML = `${an.length ? `<div class="sec bad" id="payAnomSec"><h4>異常 <span class="cnt">${an.length}</span><small class="muted" style="margin:0">已付款但沒開通、開通出錯或金額不符 —— 先按「補開通」（綠界單會先查單確認）</small></h4><div class="tw"><table>${TH_K}<tbody>${an.map((o) => orderRow(o, true, kind)).join('')}</tbody></table></div></div>` : ''}
      ${kind === 'bank' ? `<div class="sec warn" id="payRevSec"><h4>待確認的轉帳 <span class="cnt">${rev.length}</span></h4>${rev.length ? `<div class="tw"><table>${TH}<tbody>${rev.map((o) => orderRow(o, true, 'bank')).join('')}</tbody></table></div>` : '<p class="muted" style="margin:0">沒有待確認的轉帳。</p>'}</div>` : ''}
      <div class="flt" id="payFlt">
        <select id="pfS" aria-label="狀態"><option value="">全部狀態</option>${Object.entries(ST).map(([k, n]) => `<option value="${k}"${f.status === k ? ' selected' : ''}>${n}</option>`).join('')}</select>
        <label>從 <input type="date" id="pfFrom" value="${esc(f.from)}"></label><label>到 <input type="date" id="pfTo" value="${esc(f.to)}"></label>
        <input type="search" id="pfQ" placeholder="搜尋 email／訂單號" value="${esc(f.q)}" aria-label="搜尋 email 或訂單號">
        <label title="待付款、已取消（未付款）：會員還沒付錢的單，預設不顯示"><input type="checkbox" id="pfAll"${f.all ? ' checked' : ''}> 顯示未完成付款（${d.orders.filter(isUnpaid).length}）</label>
        ${kind === 'bank' ? `<label title="最近一筆是轉帳、7 天內到期的會員"><input type="checkbox" id="pfExp"${f.expiring ? ' checked' : ''}> 即將到期的轉帳會員（${d.expiring.length}）</label>` : ''}
        <span style="flex:1"></span><button type="button" id="pfCsv">匯出 CSV（${list.length} 筆）</button></div>
      <p class="muted" style="margin:0 0 4px">同一個 email 只顯示最新一筆，按「＋N 筆歷史」看他較舊的訂單（共 ${list.length} 筆、${grp.length} 位會員）。</p>
      <div class="tw"><table id="payTbl">${TH_K}<tbody>${grp.map((g) => orderRow(g.latest, true, kind, { hist: histBtn('o' + kind + ':' + g.email, g.older.length) })
        + (S.open['h:o' + kind + ':' + g.email] ? g.older.map((o) => orderRow(o, true, kind, { old: true })).join('') : '')).join('') || `<tr><td colspan="${kind === 'ecpay' ? 9 : 13}" class="muted">沒有符合的訂單</td></tr>`}</tbody></table></div>`;
    const re = () => ordersView(v, box, kind);
    box.querySelector('#pfS').onchange = (e) => { f.status = e.target.value; re(); };
    box.querySelector('#pfFrom').onchange = (e) => { f.from = e.target.value; re(); };
    box.querySelector('#pfTo').onchange = (e) => { f.to = e.target.value; re(); };
    const pe = box.querySelector('#pfExp'); if (pe) pe.onchange = (e) => { f.expiring = e.target.checked; re(); };
    box.querySelector('#pfAll').onchange = (e) => { f.all = e.target.checked; re(); };
    const q = box.querySelector('#pfQ'); q.oninput = () => { clearTimeout(q._t); q._t = setTimeout(() => { f.q = q.value; re(); const n = box.querySelector('#pfQ'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 250); };
    box.querySelector('#pfCsv').onclick = () => csvOrders(list);
    bindHist(box, re);
    bindRows(v, box, re);
  }
  function bindRows(v, box, re) {
    box.querySelectorAll('tr.prow').forEach((tr) => { tr.onclick = (e) => { if (e.target.closest('button,a')) return; S.open[tr.dataset.oid] = !S.open[tr.dataset.oid]; re(); }; });
    box.querySelectorAll('[data-pa]').forEach((b) => { b.onclick = (e) => { e.stopPropagation(); act(v, b.dataset.pa, S.d.orders.find((o) => o.id === b.dataset.id)); }; });
  }

  /* ---------------------------------------------------------------- 取消／退款申請（2026-10-12 Andy：會員按退款後我這邊要收到通知、有分頁看紀錄）*/
  const RQ = { cancel: '取消訂閱', refund: '申請退款' };
  const byWho = (b) => (b === 'auto' ? '規則自動' : b || '');
  function reqRow(r, hist, old) {
    const d = S.d, o = r.oid ? d.orders.find((x) => x.id === r.oid) : null;
    const planN = ((d.orders || []).find((x) => x.plan === r.plan) || {}).planName || r.plan || '';
    const stt = r.status === 'new' ? '<span class="stp bad">待處理</span>' : `<span class="stp ${r.closedBy === 'auto' ? 'mute' : 'ok'}" title="${esc(r.closeReason || '')}">${r.closedBy === 'auto' ? '已結案' : '已處理'}</span>`;
    const why = r.status === 'new' ? '' : `<div class="why">${esc(r.closeReason || '已處理')}${r.closedBy ? '・' + esc(byWho(r.closedBy)) : ''}${r.closedAt ? '・' + esc(ymdhm(r.closedAt)) : ''}</div>`;
    const acts = [hist || ''];
    if (r.status === 'new') {
      /* 10-16 Andy：「會多出現已退款功能按鈕 並且跳到退款紀錄那邊紀錄」→ 只有退款申請有（取消訂閱不用） */
      if (r.type === 'refund') acts.push(`<button type="button" class="sm pri" data-rqr="${esc(r.id)}" title="跳到「退款紀錄」，預填這位會員與對應訂單，登記完成後這筆自動變已處理">已退款</button>`);
      acts.push(`<button type="button" class="sm${r.type === 'refund' ? '' : ' pri'}" data-rqd="${esc(r.id)}">標記已處理</button>`);
    } else acts.push(`<button type="button" class="sm" data-rqn="${esc(r.id)}">改回待處理</button>`);
    return `<tr class="${old ? 'old' : ''}" data-rq="${esc(r.id)}"><td>${esc(ymdhm(r.created))}</td><td>${esc(RQ[r.type] || r.type)}</td><td class="l">${mailA(r.email)}</td><td>${esc(planN)}</td>
      <td>${o ? `<span title="${esc(o.planName)}・${esc(perName(o))}・NT$ ${nt(o.amount)}">${esc(o.id)}</span>` : r.type === 'refund' && r.status === 'new' ? '<span class="muted">沒有可退款的訂單</span>' : ''}</td>
      <td class="l wrap" style="max-width:260px" title="${esc(r.note || '')}">${esc(r.note || '')}</td><td class="l wrap">${stt}${why}</td><td class="act">${acts.join('')}</td></tr>`;
  }
  function reqsView(v, box) {
    const grp = byEmail(S.d.reqs || [], (r) => r.created);
    const re = () => reqsView(v, box);
    box.innerHTML = `<p class="muted" style="margin:0 0 8px">會員按「取消訂閱」或「申請退款」都會列在這裡，<b>同一個 email 只顯示最新一筆</b>（舊的被新訂單或新申請取代時會自動結案，按「＋N 筆歷史」看）。退款申請按「<b>已退款</b>」→ 跳到「退款紀錄」登記，完成後這筆自動變已處理。</p>
      <div class="tw"><table id="payReqs"><thead><tr><th>申請時間</th><th>種類</th><th>會員 email</th><th>當時方案</th><th>對應訂單</th><th>會員留言</th><th>狀態</th><th></th></tr></thead>
      <tbody>${grp.map((g) => reqRow(g.latest, histBtn('r:' + g.email, g.older.length)) + (S.open['h:r:' + g.email] ? g.older.map((r) => reqRow(r, '', true)).join('') : '')).join('') || '<tr><td colspan="8" class="muted">沒有申請</td></tr>'}</tbody></table></div>`;
    const set = async (id, status) => {
      const r = await call('/v1/admin/feedback/set', { kind: 'request', id, status });
      if (r && r._s === 200) { await load(); paint(v); st(v, status === 'done' ? '已標記處理' : '已改回待處理'); return; }
      if (!(await conflict(v, null, r))) st(v, '沒有成功', true);
    };
    box.querySelectorAll('[data-rqd]').forEach((b) => { b.onclick = () => set(b.dataset.rqd, 'done'); });
    box.querySelectorAll('[data-rqn]').forEach((b) => { b.onclick = () => set(b.dataset.rqn, 'new'); });
    box.querySelectorAll('[data-rqr]').forEach((b) => { b.onclick = () => {
      const r = (S.d.reqs || []).find((x) => x.id === b.dataset.rqr); if (!r) return;
      S.pre = { email: r.email, oid: r.oid || '', req: r.id, reqAt: r.created, auto: true };
      S.tab = 'refunds'; paint(v);
    }; });
    bindHist(box, re);
  }

  /* ---------------------------------------------------------------- 動作（每個都先確認）*/
  async function done(v, r, okMsg) {
    if (r && r._s === 200 && r.ok !== false) { await load(); paint(v); st(v, okMsg); return true; }
    return false;
  }
  function act(v, k, o) {
    if (!o) return;
    const D = T().dialog;
    const who = `<div class="kv"><span>訂單</span><b>${esc(o.id)}</b><span>會員</span><b>${mailA(o.email, o)}</b><span>方案</span><b>${esc(o.planName)}・${o.period === 'year' ? '年繳' : '月繳'}</b><span>應付金額</span><b>NT$ ${nt(o.amount)}</b>${o.payerName ? `<span>匯款人姓名</span><b>${esc(o.payerName)}</b>` : ''}${o.last5 ? `<span>客戶匯款</span><b${o.xferAmount < o.amount ? ' style="color:#e5484d"' : o.xferAmount > o.amount ? ' style="color:#30a46c"' : ''}>末 5 碼 ${esc(o.last5)}（${esc(o.xferDate)}，NT$ ${nt(o.xferAmount)}）${o.xferAmount < o.amount ? ' ⚠ 少於應付' : o.xferAmount > o.amount ? '（多於應付）' : ''}</b>` : ''}</div>`;
    const err = (dl, r) => { if (r && CONFLICT.includes(r.error)) { conflict(v, dl, r); return; } const m = dl.querySelector('.msg'); m.className = 'msg bad'; m.textContent = '沒有成功：' + ((r && (r.msg || (r.error === 'not_reported' ? '會員還沒回報匯款資料，不能確認入帳' : r.error === 'underpaid' ? '實收金額少於應付，不能開通' : r.error === 'need_received' ? '請輸入網銀實際入帳金額' : r.error === 'need_reason' ? '請寫理由' : r.error))) || (r ? r._s : '連不到會員伺服器')); };
    if (k === 'confirm') {
      /* 2026-10-12 Andy：資金確認第二道 CHK —— 一定要輸入網銀實際入帳金額；少於應付按不下去（伺服器也擋） */
      const dl = D(`<div class="payd"><h3>確認入帳並開通？</h3>${who}${o.status === 'superseded' ? `<p class="warn">這筆<b>已被取代</b>：${esc(o.rejectReason)}。只有在網銀確實看到這筆錢、而且要讓它生效時才確認；多匯的錢請改按「退款」退回。</p>` : ''}${repHist(o)}
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
      let dupOk = false;
      go.onclick = async () => {
        const n = val(); if (n < o.amount) return; go.disabled = true;
        const body = { id: o.id, received: n, expect: o.status };
        if (dupOk) { body.dupOk = true; body.dupReason = (dl.querySelector('#pdDupWhy') || {}).value || ''; if (!body.dupReason.trim()) { err(dl, { msg: '請寫為什麼確定是另一筆入帳' }); go.disabled = false; return; } }
        const r = await call('/v1/admin/pay/confirm', body);
        /* 另一位管理者已經確認過：伺服器回 dup（不重複開通）→ 說清楚是誰開通的 */
        if (r && r._s === 200 && r.dup) { dl.hidden = true; await load(); paint(v); st(v, `這筆已經開通過了，沒有重複開通${whoTxt(r)}`, true); return; }
        if (await done(v, r, `已開通 ${o.email}（實收 NT$ ${nt(n)}）`)) { dl.hidden = true; return; }
        go.disabled = false;
        /* 稽核 H3：同一筆入帳已經確認過別張單 → 顯示是哪張，要勾選並寫理由才能再送 */
        if (r && r.error === 'dup_xfer' && !dupOk) {
          dupOk = true;
          rm.insertAdjacentHTML('afterend', `<div id="pdDupBox" style="border:1px solid #e5484d;border-radius:8px;padding:8px;margin:6px 0;color:#e5484d;font-size:13px">⚠ 末 5 碼 ${esc(o.last5)}、轉帳日 ${esc(o.xferDate)} 這筆入帳，<b>已經確認過另一張訂單</b>（${esc(r.other)}・${esc(r.otherEmail)}）。同一筆錢不能開通兩次。<br>只有在網銀確實看到<b>兩筆不同的入帳</b>時才繼續：<input type="text" id="pdDupWhy" maxlength="200" placeholder="寫下理由，例如：網銀有兩筆，交易序號不同" style="width:100%;margin-top:4px"></div>`);
          err(dl, { msg: '同一筆入帳已用過，請確認後寫理由再按一次' });
          return;
        }
        err(dl, r);
      };
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
      dl.querySelector('#pdGo').onclick = async () => { const w = why.value.trim(); if (!w) { err(dl, { msg: '請寫退回原因' }); return; } const r = await call('/v1/admin/pay/reject', { id: o.id, reason: w, expect: o.status }); if (await done(v, r, '已退回')) dl.hidden = true; else err(dl, r); };
    } else if (k === 'amt') {
      const dl = D(`<div class="payd"><h3>修改這筆轉帳金額</h3>${who}<p class="muted">會員端金額是鎖定的（不能自己填），只有這裡能改。改了之後應付金額與會員看到的金額都會變，確認入帳時照新金額核對；改前改後會留紀錄。</p>
        <label for="pdAmt">新的金額（NT$）</label><input type="text" id="pdAmt" inputmode="numeric" autocomplete="off" value="${esc(o.amount)}">
        <label for="pdAmtWhy" style="display:block;margin-top:6px">原因（只有管理者看得到）</label><input type="text" id="pdAmtWhy" maxlength="200">
        <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">儲存金額</button></div></div>`);
      dl.querySelector('#pdGo').onclick = async () => {
        const n = parseInt(String(dl.querySelector('#pdAmt').value).replace(/[,\s]/g, ''), 10);
        if (!Number.isInteger(n) || n < 1) { err(dl, { msg: '請輸入正整數金額' }); return; }
        const r = await call('/v1/admin/pay/amount', { id: o.id, amount: n, reason: dl.querySelector('#pdAmtWhy').value, expect: o.status });
        if (await done(v, r, `已把 ${o.id} 改成 NT$ ${nt(n)}`)) dl.hidden = true; else err(dl, r);
      };
    } else if (k === 'note') {
      const dl = D(`<div class="payd"><h3>管理者備註</h3>${who}<p class="muted">只有管理者看得到，會出現在清單與 CSV。</p><input type="text" id="pdNote" maxlength="300" value="${esc(o.adminNote)}">
        <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">儲存備註</button></div></div>`);
      dl.querySelector('#pdGo').onclick = async () => { const r = await call('/v1/admin/pay/note', { id: o.id, note: dl.querySelector('#pdNote').value }); if (await done(v, r, '已存備註')) dl.hidden = true; else err(dl, r); };
    } else if (k === 'fix') {
      const ec = o.method === 'ecpay' && !o.parent;
      const dl = D(`<div class="payd"><h3>補開通？</h3>${who}${o.anomaly ? `<p class="warn">異常：${esc(o.anomaly)}</p>` : ''}${o.actErr ? `<p class="warn">開通出錯：${esc(o.actErr)}</p>` : ''}
        <p>${ec ? '會先向綠界<b>查單</b>：確定已付款、金額相符就開通。查單不過時可以按「強制開通」（請先在綠界後台確認這筆真的收到錢）。' : '會把這筆開通（期間照月繳／年繳加上去），同一筆不會加兩次。'}</p>
        <label for="pdWhyF">${ec ? '強制開通的理由（必填，會永久記錄）' : '開通理由（必填，會永久記錄）'}</label><input type="text" id="pdWhyF" maxlength="200" placeholder="例如：已到綠界後台確認實收 NT$ ${esc(o.amount)}">
        <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button>${ec ? '<button type="button" id="pdForce">強制開通</button>' : ''}<button type="button" class="pri" id="pdGo">${ec ? '查單並開通' : '補開通'}</button></div></div>`);
      const fwhy = () => dl.querySelector('#pdWhyF').value.trim();
      dl.querySelector('#pdGo').onclick = async () => { if (!ec && !fwhy()) { err(dl, { msg: '請寫開通理由' }); return; } const r = await call('/v1/admin/pay/reactivate', { id: o.id, force: !ec, reason: fwhy() }); if (await done(v, r, '已補開通')) dl.hidden = true; else err(dl, r); };
      const fz = dl.querySelector('#pdForce'); if (fz) fz.onclick = async () => { if (!fwhy()) { err(dl, { msg: '強制開通請寫理由' }); return; } const r = await call('/v1/admin/pay/reactivate', { id: o.id, force: true, reason: fwhy() }); if (await done(v, r, '已強制開通')) dl.hidden = true; else err(dl, r); };
    } else if (k === 'ack') {
      const dl = D(`<div class="payd"><h3>標記已處理？</h3>${who}<p class="warn">${esc(o.anomaly || o.actErr)}</p><p>這筆已經開通了。確認你看過、處理完（例如跟會員聯絡過）後按下去，就會從異常清單拿掉；訂單本身不變。</p>
        <div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">標記已處理</button></div></div>`);
      dl.querySelector('#pdGo').onclick = async () => { const r = await call('/v1/admin/pay/ack', { id: o.id }); if (await done(v, r, '已標記處理')) dl.hidden = true; else err(dl, r); };
    } else if (k === 'sync') {
      (async () => { st(v, '向綠界查單中…'); const r = await call('/v1/admin/pay/sync', { id: o.id }); await load(); paint(v); st(v, r && r.ok ? (r.added != null ? `對帳完成，補了 ${r.added} 期` : r.dup ? '已經開通過' : '查單完成') : '查單結果：' + ((r && (r.error === 'unpaid' ? '還沒付款' : r.error)) || '連不到'), !(r && r.ok)); })();
    } else if (k === 'refund') refundDlg(v, o);
  }
  async function refundDlg(v, o, opt) {
    opt = opt || {};
    const q = await call('/v1/admin/pay/refund_quote', { id: o.id });
    if (!q || q._s !== 200) { st(v, '讀不到可退金額', true); return; }
    const rid = 'r-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    const manual = q.kind === 'manual';
    const today = ymd(Date.now());
    const rq0 = opt.req ? (S.d.reqs || []).find((r) => r.id === opt.req) : null;
    const dl = T().dialog(`<div class="payd" id="payRefundDlg"><h3>退款</h3>${rq0 ? `<p class="warn" id="rfReqNote">來自 ${esc(rq0.email)} 在 ${esc(ymdhm(rq0.created))} 的退款申請：退款成功後，這筆申請會<b>自動標成已處理</b>。</p>` : ''}${o.status === 'superseded' ? '<p class="warn">這筆是<b>已被取代</b>的轉帳（沒有開通過）：退款只是把會員多匯的錢退回，<b>不會動到他的方案</b>，也不算用掉七天退款保證。</p>' : ''}
      <div class="kv"><span>訂單</span><b>${esc(o.id)}</b><span>會員</span><b>${esc(o.email)}</b><span>付款方式</span><b>${esc(methodName(o))}${o.payType ? '（' + esc(o.payType) + '）' : ''}</b><span>訂單金額</span><b>NT$ ${nt(o.amount)}</b><span>可退金額</span><b id="rfLeft">NT$ ${nt(q.left)}</b><span>試算</span><b>NT$ ${nt(q.suggest)}<small style="color:var(--ink-2);font-weight:400">・${esc(q.rule)}</small></b></div>
      <label for="rfAmt">退款金額（可改）</label><input type="number" id="rfAmt" min="1" max="${q.left}" value="${q.suggest}">${q.suggest === 0 ? '<small style="color:#e5484d;display:block">試算是 0 元（政策上不退）；要退請自己填金額並在備註寫原因</small>' : ''}
      <label>退款後權限</label>
      <label class="rad"><input type="radio" name="rfPerm" value="now" checked><span>立即降級<small>會員馬上回到註冊會員</small></span></label>
      <label class="rad"><input type="radio" name="rfPerm" value="end"><span>到期才停<small>用到 ${esc(ymd(o.grantTo))} 才回到註冊會員</small></span></label>
      ${q.recur && q.periodActive ? '<p class="warn">這是信用卡定期定額：退款時會同時向綠界<b>終止之後的自動扣款</b>。</p>' : ''}
      ${manual ? `<p class="warn">${o.method === 'bank' ? '銀行轉帳' : '這種付款方式'}沒辦法用 API 退款：這裡只做<b>登記</b>，<b>請到網銀把錢匯回</b>給會員。</p>
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
      /* 稽核 H5：退得比政策試算多 → 一定要寫原因 */
      if (amount > q.suggest && !dl.querySelector('#rfNote').value.trim()) { m.className = 'msg bad'; m.textContent = `退款金額 NT$ ${nt(amount)} 高於試算 NT$ ${nt(q.suggest)}，請在備註寫原因`; return; }
      const asManual = manual || (mb && mb.checked);
      const body = { id: o.id, rid, amount, perm: dl.querySelector('input[name=rfPerm]:checked').value, note: dl.querySelector('#rfNote').value.trim(), manual: !!asManual, expect: o.status, ...(opt.req ? { req: opt.req } : {}) };
      if (manual) { body.last5 = dl.querySelector('#rfL5').value.trim(); body.date = dl.querySelector('#rfDate').value; if (!/^\d{5}$/.test(body.last5)) { m.className = 'msg bad'; m.textContent = '請填退款帳號末 5 碼'; return; } }
      else if (asManual) body.date = dl.querySelector('#rfDate2').value;
      go.disabled = true; m.className = 'msg'; m.textContent = asManual ? '登記中…' : '向綠界送出退款…';
      const r = await call('/v1/admin/pay/refund', body);
      if (r && r._s === 200 && r.cancel && !r.cancel.ok) { await load(); paint(v); st(v, `已退款 NT$ ${nt(amount)}，但綠界自動扣款「沒有」終止成功（${r.cancel.msg || r.cancel.error}）：已列入異常，排程會重試，也請到綠界後台確認`, true); dl.hidden = true; return; }
      if (r && r._s === 200 && r.ok !== false) S.pre = null;
      if (await done(v, r, `已退款 NT$ ${nt(amount)}（${o.email}）${opt.req ? '，那筆退款申請已自動標成已處理' : ''}`)) { dl.hidden = true; return; }
      if (await conflict(v, dl, r)) return;
      go.disabled = false; m.className = 'msg bad';
      m.textContent = '退款沒有成功：' + ((r && (r.msg || ({ over: '超過可退金額', running: '這筆有退款正在處理中', bad_last5: '請填退款帳號末 5 碼', bad_date: '請選退款日期', stage_no_refund: '測試環境不能退刷' })[r.error] || r.error)) || '連不到會員伺服器');
    };
  }

  /* ---------------------------------------------------------------- ② 會員訂閱 */
  const subMethod = (s) => (s.method === 'period' ? '信用卡定期定額' : s.method === 'bank' ? '銀行轉帳' : '綠界信用卡');
  function subsView(v, box) {
    const d = S.d, subs = d.subs;
    const ev = (email) => d.events.filter((e) => e.email === email);
    box.innerHTML = `<p class="muted">每個付過錢的會員一列。權限以伺服器的到期日為準：到期日一過自動回到註冊會員，並記一筆「到期降級」。點一列看他所有訂單、退款與方案異動。</p>
      <div class="flt"><span style="flex:1"></span><button type="button" id="psCsv">匯出 CSV（${subs.length} 人）</button></div>
      <div class="tw"><table id="paySubs"><thead><tr><th>會員 email</th><th>目前方案</th><th>付款方式</th><th>第一次付款</th><th>最近付款</th><th>週期</th><th>本期開始</th><th>到期日</th><th>自動續訂</th><th>到期後降回註冊會員</th><th>累計付款</th><th>筆數</th></tr></thead>
      <tbody>${subs.map((s) => `<tr class="prow" data-em="${esc(s.email)}"><td class="l" title="${esc(s.email)}">${mailA(s.email)}</td><td>${esc(s.expired ? '註冊會員（已到期）' : s.planName)}</td><td>${esc(subMethod(s))}</td>
        <td>${esc(ymd(s.firstPaid))}</td><td>${esc(ymd(s.lastPaid))}</td><td>${s.period === 'year' ? '年繳' : '月繳'}</td><td>${esc(ymd(s.curFrom))}</td><td>${esc(ymd(s.expires))}</td>
        <td>${s.autoRenew ? '<span class="stp ok">開</span>' : s.recur ? '<span class="stp mute">已取消</span>' : '<span class="muted" title="銀行轉帳是預付制，沒有自動扣款">不適用</span>'}</td><td>${s.downgradeAt ? esc(ymd(s.downgradeAt)) : '自動續扣中'}</td>
        <td class="n">${nt(s.total)}${s.refunded ? `<small style="color:var(--rise)">（退 ${nt(s.refunded)}）</small>` : ''}</td><td class="n">${s.count}</td></tr>`
        + (S.open['s:' + s.email] ? `<tr class="det"><td colspan="12"><div class="tw"><table>${TH}<tbody>${d.orders.filter((o) => o.email === s.email).map((o) => orderRow(o, true)).join('')}</tbody></table></div>
          <p style="margin:6px 0 0">方案異動：${ev(s.email).map((e) => `${esc(ymdhm(e.at))} ${esc(EV[e.kind] || e.kind)}${e.detail ? '（' + esc(e.detail) + '）' : ''}`).join('　') || '—'}</p></td></tr>` : '')).join('') || '<tr><td colspan="12" class="muted">還沒有付費會員</td></tr>'}</tbody></table></div>`;
    box.querySelector('#psCsv').onclick = () => csvSubs(subs);
    /* 2026-10-14：清除測試帳號的金流資料（防呆：要再打一次 email；有綠界正式付款的帳號伺服器會拒絕）*/
    box.insertAdjacentHTML('beforeend', `<details class="sec" id="payPurge" style="margin-top:14px"><summary style="cursor:pointer"><b>清除測試資料</b> <small class="muted">只用在自己測試用的帳號；真的客戶請用「退款」</small></summary>
      <p class="muted" style="margin:6px 0">會刪掉這個 email 的<b>所有訂單、退款紀錄、帳務通知、取消／退款申請、方案異動紀錄</b>，會員回到「註冊會員」。刪除無法復原（刪了哪些會留一筆紀錄在金流事件裡）。有綠界正式付款的帳號不能清除。</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><input type="email" id="ppEm" placeholder="測試帳號 email" style="min-width:240px"><input type="email" id="ppEm2" placeholder="再輸入一次" style="min-width:240px"><button type="button" class="danger" id="ppGo">清除</button></div>
      <div class="msg" id="ppMsg" role="status" style="margin-top:6px"></div></details>`);
    const pm = box.querySelector('#ppMsg');
    box.querySelector('#ppGo').onclick = async () => {
      const em = box.querySelector('#ppEm').value.trim(), em2 = box.querySelector('#ppEm2').value.trim();
      if (!em || em.toLowerCase() !== em2.toLowerCase()) { pm.className = 'msg bad'; pm.textContent = '兩次輸入的 email 要一樣'; return; }
      const n = S.d.orders.filter((o) => o.email === em.toLowerCase()).length;
      const dl = T().dialog(`<div class="payd"><h3>清除 ${esc(em)} 的測試資料？</h3><p>會刪掉 <b>${n}</b> 筆訂單與相關的退款、通知、申請紀錄，會員回到註冊會員。<b>無法復原。</b></p><div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="danger" id="pdGo">確定清除</button></div></div>`);
      dl.querySelector('#pdGo').onclick = async () => {
        const r = await call('/v1/admin/pay/purge', { email: em, confirm: em2 });
        if (r && r._s === 200 && r.ok) { dl.hidden = true; await load(); paint(v); st(v, `已清除 ${em}：訂單 ${r.orders} 筆、退款 ${r.refunds} 筆、通知 ${r.notices} 則、申請 ${r.requests} 筆`); return; }
        const m = dl.querySelector('.msg'); m.className = 'msg bad'; m.textContent = '沒有清除：' + ((r && (r.msg || r.error)) || '連不到會員伺服器');
      };
    };
    box.querySelectorAll('tr.prow[data-em]').forEach((tr) => { tr.onclick = (e) => { if (e.target.closest('button,a')) return; const k = 's:' + tr.dataset.em; S.open[k] = !S.open[k]; subsView(v, box); }; });
    box.querySelectorAll('[data-pa]').forEach((b) => { b.onclick = (e) => { e.stopPropagation(); act(v, b.dataset.pa, S.d.orders.find((o) => o.id === b.dataset.id)); }; });
  }

  /* ---------------------------------------------------------------- ③ 退款紀錄
     上面「為會員登記退款」：選會員 → 選訂單 → 打開退款登記（從申請的「已退款」來會自動預填並直接打開）；
     下面清單依 email 摺疊，只顯示每位會員最新一筆退款，「＋N 筆歷史」展開。 */
  function refundsView(v, box) {
    const d = S.d, rs = d.refunds, pre = S.pre || {};
    const cand = d.orders.filter(refundable);
    const emails = [...new Set(cand.map((o) => o.email))].sort();
    const em = pre.email || S.rfEm || '';
    const opts = (e) => cand.filter((o) => o.email === String(e || '').toLowerCase()).sort((a, b) => b.created - a.created);
    const oSel = (e, sel) => opts(e).map((o) => `<option value="${esc(o.id)}"${o.id === sel ? ' selected' : ''}>${esc(o.id)}・${esc(o.planName)}・${esc(perName(o))}・NT$ ${nt(o.recvAmount || o.amount)}・${esc(stName(o))}</option>`).join('');
    const reqRow0 = pre.req ? (d.reqs || []).find((r) => r.id === pre.req) : null;
    const grp = byEmail(rs, (r) => r.created);
    const row = (r, hist, old) => `<tr class="${old ? 'old' : ''}"><td>${esc(ymdhm(r.created))}</td><td>${esc(r.oid)}</td><td class="l">${mailA(r.email)}</td><td class="n">${nt(r.amount)}</td><td>${r.kind === 'manual' ? '人工登記' : '綠界 ' + esc(r.action)}</td>
        <td><span class="stp ${r.status === 'done' ? 'ok' : r.status === 'failed' ? 'bad' : 'wait'}">${r.status === 'done' ? '完成' : r.status === 'failed' ? '失敗' : '處理中'}</span></td><td>${r.perm === 'end' ? '到期才停' : '立即降級'}</td>
        <td>${esc(r.acct_last5)}</td><td>${esc(r.rdate)}</td><td>${r.req ? '<span class="stp mute" title="從「取消／退款申請」按「已退款」登記">來自申請</span>' : ''}</td><td class="l" title="${esc((r.note || '') + (r.msg ? '／' + r.msg : ''))}">${esc(r.note)}${r.msg ? '／' + esc(r.msg) : ''}</td><td class="l">${esc(r.by)}</td><td class="act">${hist || ''}</td></tr>`;
    box.innerHTML = `<div class="sec${pre.req ? ' warn' : ''}" id="payRfNew"><h4>為會員登記一筆退款</h4>
        ${reqRow0 ? `<p class="muted" style="margin:0 0 6px" id="payRfFrom">來自 <b>${esc(reqRow0.email)}</b> 在 ${esc(ymdhm(reqRow0.created))} 的退款申請${reqRow0.note ? `（留言：${esc(reqRow0.note)}）` : ''}：登記完成後這筆申請會<b>自動標成已處理</b>。</p>` : ''}
        <div class="flt" style="margin:0">
          <input type="search" id="rfEm" list="rfEmList" placeholder="會員 email" value="${esc(em)}" aria-label="會員 email" style="flex:0 1 260px">
          <datalist id="rfEmList">${emails.map((e) => `<option value="${esc(e)}">`).join('')}</datalist>
          <select id="rfOid" aria-label="要退款的訂單" style="flex:1 1 260px;min-width:0;max-width:520px">${oSel(em, pre.oid) || '<option value="">（這個 email 沒有可退款的訂單）</option>'}</select>
          <button type="button" class="pri" id="rfOpen"${opts(em).length ? '' : ' disabled'}>登記退款</button>
          ${pre.req ? '<button type="button" id="rfPreX" title="不從申請登記，清掉預填">清除預填</button>' : ''}
        </div></div>
      <div class="flt"><span class="muted" style="margin:0">所有退款（含失敗的嘗試）；同一個 email 只顯示最新一筆。</span><span style="flex:1"></span><button type="button" id="prCsv">匯出 CSV（${rs.length} 筆）</button></div>
      <div class="tw"><table id="payRefunds"><thead><tr><th>時間</th><th>訂單</th><th>會員 email</th><th>金額</th><th>方式</th><th>結果</th><th>權限</th><th>退款帳號末5碼</th><th>退款日期</th><th>來源</th><th>備註</th><th>操作者</th><th></th></tr></thead>
      <tbody>${grp.map((g) => row(g.latest, histBtn('f:' + g.email, g.older.length)) + (S.open['h:f:' + g.email] ? g.older.map((r) => row(r, '', true)).join('') : '')).join('') || '<tr><td colspan="13" class="muted">沒有退款</td></tr>'}</tbody></table></div>`;
    const re = () => refundsView(v, box);
    box.querySelector('#prCsv').onclick = () => csvRefunds(rs);
    const emIn = box.querySelector('#rfEm'), oidSel = box.querySelector('#rfOid'), go = box.querySelector('#rfOpen');
    emIn.onchange = () => {
      S.rfEm = emIn.value.trim().toLowerCase();
      if (S.pre && S.pre.email !== S.rfEm) S.pre = null;   // 改成別人 → 不再是那筆申請
      re();
    };
    const px = box.querySelector('#rfPreX'); if (px) px.onclick = () => { S.pre = null; re(); };
    const open = () => { const o = d.orders.find((x) => x.id === oidSel.value); if (o) refundDlg(v, o, S.pre && S.pre.email === o.email ? { req: S.pre.req } : {}); };
    go.onclick = open;
    bindHist(box, re);
    /* 從「已退款」過來：直接進入登記流程 */
    if (pre.auto) { S.pre.auto = false; if (opts(em).length) open(); else st(v, `${em} 沒有可退款的訂單（可能已全額退過）；如果已經在別處退過，請回「取消／退款申請」按「標記已處理」`, true); }
  }

  /* ---------------------------------------------------------------- ⑤ 操作紀錄（處理措施第 4 條：誰、何時、做了什麼、前後狀態）*/
  const AK = { confirm: '確認入帳', reject: '退回', ack: '異常標記已處理', amount: '改金額', note: '備註', reactivate: '補開通', refund: '退款', purge: '清除測試資料', req_set: '申請改狀態',
    req_close: '申請結案', req_refunded: '申請已退款', superseded: '訂單被取代', period_cancel_admin: '終止自動扣款', bank_put: '收款帳號設定', events_clean: '清理舊事件紀錄' };
  const stw = (x) => ST[x] || ({ new: '待處理', done: '已處理' })[x] || x || '';
  function auditView(v, box) {
    const d = S.d, em = {}; d.orders.forEach((o) => { em[o.id] = o.email; });
    const q = (S.aq || '').trim().toLowerCase();
    const rows = (d.audit || []).map((a) => ({ ...a, mail: a.email || em[a.oid] || (a.detail && a.detail.email) || '' }))
      .filter((a) => !q || [a.mail, a.oid, a.by, AK[a.kind] || a.kind].some((x) => String(x || '').toLowerCase().includes(q)));
    const det = (a) => { const x = a.detail || {}; return [x.reason, x.why, x.received ? '實收 NT$ ' + nt(x.received) : '', x.amount && a.kind !== 'confirm' ? 'NT$ ' + nt(x.amount) : '', x.before != null && a.kind === 'amount' ? `NT$ ${nt(x.before)} → ${nt(x.after)}` : '', x.req ? '申請 ' + x.req : '', x.rid ? '退款 ' + x.rid : '', x.bank || '', x.scanned != null ? `掃描 ${x.scanned} 筆、裁 ${x.trimmed} 遮 ${x.masked}` : '', x.msg || ''].filter(Boolean).join('・'); };
    box.innerHTML = `<p class="muted" style="margin:0 0 8px">管理者與規則自動做的每個動作：誰、何時、做了什麼、前後狀態。<b>規則自動</b>＝同一個 email 出現較新的訂單／申請時，系統把舊的結案或標「已被取代」。</p>
      <div class="flt"><input type="search" id="paQ" placeholder="搜尋 email／訂單號／操作者" value="${esc(S.aq || '')}" aria-label="搜尋操作紀錄"><span class="muted" style="margin:0">${rows.length} 筆</span></div>
      <div class="tw"><table id="payAudit"><thead><tr><th>時間</th><th>操作者</th><th>動作</th><th>訂單</th><th>會員 email</th><th>前 → 後</th><th>細節</th></tr></thead>
      <tbody>${rows.slice(0, 500).map((a) => `<tr><td>${esc(ymdhm(a.at))}</td><td class="l">${esc(byWho(a.by) || '規則自動')}</td><td>${esc(AK[a.kind] || a.kind)}</td><td>${esc(a.oid || '')}</td><td class="l">${esc(a.mail)}</td>
        <td>${a.from || a.to ? `${esc(stw(a.from))} → ${esc(stw(a.to))}` : ''}</td><td class="l wrap" style="max-width:360px" title="${esc(det(a))}">${esc(det(a))}</td></tr>`).join('') || '<tr><td colspan="7" class="muted">還沒有紀錄</td></tr>'}</tbody></table></div>`;
    const qi = box.querySelector('#paQ'); qi.oninput = () => { clearTimeout(qi._t); qi._t = setTimeout(() => { S.aq = qi.value; auditView(v, box); const n = box.querySelector('#paQ'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 250); };
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
    /* 2026-10-16 維護：清理舊付款事件紀錄（Andy 同意）。以前驗章失敗會把綠界通知原文寫進事件紀錄，其中可能有卡號前 6／後 4 碼。
       不自動執行、不跟 Worker 部署一起跑；只有管理者在正式站按。可重複按（冪等）。預覽版寫入被擋，所以預覽版按了只說明不送出。 */
    box.insertAdjacentHTML('beforeend', `<div id="payMaint" style="margin-top:20px;border-top:1px solid var(--line);padding-top:12px"><b>維護工具</b>
      <p class="muted" style="margin:4px 0 8px">把舊的付款事件紀錄裡可能殘留的綠界通知原文裁成只剩交易編號、金額、狀態，並遮掉長串數字。只動事件紀錄的內容欄，不動訂單與退款；可重複執行。</p>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><button type="button" class="danger" id="pmClean">清理舊事件紀錄</button><span id="pmRes" class="muted" role="status"></span></div></div>`);
    box.querySelector('#pmClean').onclick = () => {
      const res = box.querySelector('#pmRes');
      const dl = T().dialog('<div class="payd"><h3>清理舊事件紀錄？</h3><p>會把<b>舊的綠界通知／回傳原文</b>裁成白名單欄位、純文字事件裡 13～19 碼的數字遮成「[已遮蔽]」。<b>不會動訂單、退款、方案</b>；做完會顯示處理筆數，重複按不會再改。</p><div class="msg" role="status"></div><div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="pdGo">確定清理</button></div></div>');
      dl.querySelector('#pdGo').onclick = async () => {
        const m = dl.querySelector('.msg');
        if (/\/preview\//.test(location.pathname || '')) { m.className = 'msg bad'; m.textContent = '預覽版的寫入被擋，不會送出；請到正式站執行。'; return; }
        const r = await call('/v1/admin/pay/events/clean', { confirm: true });
        if (r && r._s === 200 && r.ok) { dl.hidden = true; res.textContent = `已掃描 ${nt(r.scanned)} 筆，裁成白名單 ${nt(r.trimmed)} 筆、遮蔽數字 ${nt(r.masked)} 筆（共改 ${nt(r.changed)} 筆）`; return; }
        m.className = 'msg bad'; m.textContent = r && r._s === 404 ? '會員系統還沒更新（Worker 尚未部署）' : '沒有處理成功';
      };
    };
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
    csv('訂單', ['訂單編號', '建立時間', '會員email', '方案', '週期', '金額', '方式', '付款類型', '狀態', '付款時間', '開通起', '開通迄', '匯款人姓名', '轉出末5碼', '轉帳日期', '轉帳金額', '綠界交易號', '已退款金額', '退款明細', '自動續訂', '母訂單', '期數', '會員備註', '管理者備註', '退回原因', '測試'],
      list.map((o) => [o.id, ymdhm(o.created), o.email, o.planName, o.period === 'year' ? '年繳' : '月繳', o.amount, methodName(o), o.payType, stName(o), ymdhm(o.paidAt), ymd(o.grantFrom), ymd(o.grantTo), o.payerName || '', o.last5, o.xferDate, o.xferAmount || '', o.tradeNo, o.refunded || 0,
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
