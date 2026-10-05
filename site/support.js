/* ============================================================================
   右下角客服／意見反饋（sub-v1，2026-10-05）＋ 管理端 #admin/feedback
   ----------------------------------------------------------------------------
   Andy：參考 stockintelli 右下角的浮動客服。這裡做三件事，回答「我卡住了，去哪裡問」：
     ① 常見問題：點一題就在原地展開答案（答案照這個網站實際的功能寫，不是罐頭文字）
     ② 意見反饋：類別＋內容＋（可選）目前網址與瀏覽器資訊＋聯絡 email（登入者預填）→ Worker /v1/feedback（feedback 表）
     ③ 寄信給客服：mailto（SUPPORT_EMAIL）
   AI 回答先不接（要 API 金鑰與費用），面板上留「AI 客服即將推出」。
   隱私：反饋只存在我們的 Worker（13 個月、刪帳號一起刪），不送第三方、不進 repo。
   管理端：#admin/feedback（只有管理者）—— 反饋列表＋訂閱申請列表，各自可以標「已處理」。
     不掛進 admin.js：另一條分支正在改它；這一頁由這支自己畫（app.js 的 TwSubRoutes 先攔下來）。
   ============================================================================ */
(function () {
  'use strict';
  /* ⚠ 客服信箱：Andy 2026-10-05 指定暫用此信箱*/
  const SUPPORT_EMAIL = 'kcq01010909@gmail.com';
  const T = () => window.TwSub;
  if (!T()) return;
  const { esc, css, call, view, toast } = T();

  const FAQ = [
    ['資料多久更新一次？', '盤後資料每個交易日更新三次（台北時間約 15:30 價量、18:30 與 21:30 補齊法人、融資券等）。頁面右上角的版號與「資料狀態」會寫最後更新時間。歷史資料每小時自動回補。'],
    ['「即時」和「盤後」差在哪？', '盤中（9:00～13:30）打開「即時」時，報價與分時走勢每 5 秒更新一次，來源是證交所的即時行情；盤後資料（法人、融資券、族群資金流向）要等收盤後官方公布才會算，所以盤中看到的族群排行是前一個交易日的。即時報價只是參考，下單請以券商報價為準。'],
    ['怎麼把股票加進自選？', '在個股頁按股票名稱旁的「☆」（變成「★」就是加進去了，再點一下可以選要放哪幾頁）。自選清單在左側欄「自選」，最多 5 頁、每頁 50 檔（實際可用頁數依方案）。沒登入時清單只存在這台裝置；登入後會跨裝置同步。'],
    ['要登入嗎？登入會拿到我的什麼資料？', '不登入也能用大部分功能。登入用 Google 帳號，我們只收到名稱、email 與大頭貼，拿不到密碼，也不讀 Gmail 或雲端硬碟。細節在頁尾的「隱私權政策」。'],
    ['免費和付費方案差在哪？', '差在可用的功能與每日瀏覽次數。逐項對照請看「訂閱方案」頁的「查看完整權益」。目前付費方案採申請制，由專人開通；線上付款即將推出。'],
    ['怎麼申請付費方案？會馬上扣款嗎？', '到「訂閱方案」頁按「申請訂閱」，選月繳或年繳、留下 email 送出即可。送出不會扣款，我們會寄信跟你確認方案與付款方式，開通後重新整理網頁就生效。'],
    ['為什麼看到「今日已用完」？', '某些方案的個股頁、AI 分析、題材剖析圖有每日次數上限（同一檔一天內重複看不重算）。台北時間每天 0 點自動恢復，升級方案可以增加次數。'],
    ['為什麼有些區塊有鎖頭「此功能需開通」？', '那個功能不在你目前的方案內。訪客登入後通常會多開放一些；其他功能可以到「訂閱方案」頁看哪個方案有。'],
    ['AI 分析是怎麼來的？', '個股頁的 AI 分析是依技術面、籌碼面、基本面、消息面的固定規則自動產生的整理，不是投資建議，也不是真人分析師的意見。'],
    ['這個網站會告訴我該買哪一檔嗎？', '不會。本網站不是證券投資顧問，只提供資料整理與視覺化，不提供個股買賣建議，所有內容僅供參考，投資請自行判斷。'],
    ['畫面怪怪的、圖表沒出來怎麼辦？', '先按 Ctrl+F5（手機下拉重新整理）強制更新。還是不行的話，請用下面的「意見反饋」選「錯誤回報」，勾選附上目前網址與瀏覽器資訊，我們比較好重現。'],
    ['怎麼聯絡客服？', `用這個面板的「意見反饋」送出，或寄信到 ${SUPPORT_EMAIL}。付款相關的問題請在反饋類別選「付款問題」。`],
  ];
  const CATS = [['bug', '錯誤回報'], ['idea', '功能建議'], ['pay', '付款問題'], ['other', '其他']];

  css('supportCss', `
.supfab{position:fixed;right:20px;bottom:20px;z-index:1200;display:inline-flex;align-items:center;gap:8px;height:46px;padding:0 18px 0 14px;border-radius:999px;border:0;cursor:pointer;
  background:var(--cyan);color:#04121a;font-size:14.5px;font-weight:700;box-shadow:0 10px 28px -10px rgba(0,0,0,.6)}
.supfab svg{width:20px;height:20px}
.supfab[hidden]{display:none}
.suppanel{position:fixed;right:20px;bottom:78px;z-index:1201;width:min(400px,calc(100vw - 32px));max-height:min(640px,calc(100vh - 110px));display:flex;flex-direction:column;
  background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:16px;box-shadow:0 24px 60px -20px rgba(0,0,0,.75);overflow:hidden}
.suppanel[hidden]{display:none}
.suppanel .sph{display:flex;align-items:center;gap:10px;padding:14px 16px 10px;border-bottom:1px solid var(--line)}
.suppanel .sph b{font-size:16px;flex:1}
.suppanel .sph button{background:none;border:0;color:var(--ink-2);font-size:20px;cursor:pointer;width:32px;height:32px;border-radius:8px}
.suppanel .spai{margin:10px 16px 0;font-size:12.5px;color:var(--ink-2);background:var(--panel);border:1px dashed var(--line-2);border-radius:10px;padding:8px 10px}
.suppanel .spai b{color:var(--violet)}
.suppanel .sptabs{display:flex;gap:4px;padding:10px 16px 0}
.suppanel .sptabs button{flex:1;height:34px;border:1px solid var(--line-2);background:transparent;color:var(--ink-2);border-radius:9px;font-size:13.5px;cursor:pointer}
.suppanel .sptabs button.on{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
.suppanel .spbody{padding:10px 16px 16px;overflow:auto}
.suppanel .faq{border-bottom:1px solid var(--line)}
.suppanel .faq button{width:100%;text-align:left;background:none;border:0;color:var(--ink);font-size:14px;padding:10px 22px 10px 0;cursor:pointer;position:relative;line-height:1.5}
.suppanel .faq button::after{content:"+";position:absolute;right:2px;top:9px;color:var(--ink-2);font-size:16px}
.suppanel .faq.on button::after{content:"−"}
.suppanel .faq .ans{display:none;font-size:13.5px;line-height:1.7;color:var(--ink-2);padding:0 0 12px}
.suppanel .faq.on .ans{display:block}
.suppanel label{display:block;font-size:13px;color:var(--ink-2);margin:10px 0 4px}
.suppanel select,.suppanel textarea,.suppanel input[type=email]{width:100%;box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:8px 10px;font:inherit;font-size:14px}
.suppanel textarea{min-height:110px;resize:vertical}
.suppanel .chk{display:flex;gap:8px;align-items:flex-start;font-size:13px;color:var(--ink-2);margin-top:10px}
.suppanel .chk input{margin-top:3px}
.suppanel .go{margin-top:12px;width:100%;height:40px;border:0;border-radius:10px;background:var(--cyan);color:#04121a;font-weight:700;font-size:14.5px;cursor:pointer}
.suppanel .go[disabled]{opacity:.6}
.suppanel .msg{font-size:13.5px;margin-top:8px;min-height:1.2em}
.suppanel .msg.bad{color:var(--rise)}.suppanel .msg.ok{color:var(--fall)}
.suppanel .mail{display:block;margin-top:6px;font-size:15px;color:var(--cyan)}
.suppanel .note{font-size:12.5px;color:var(--ink-2);line-height:1.65;margin-top:10px}
#v-subadm{max-width:1280px;margin:0 auto;padding-top:12px}
#v-subadm .card{margin-top:14px}
#v-subadm .sat{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#v-subadm .sat h2{margin:0;font-size:18px;flex:1}
#v-subadm .sat a,#v-subadm .sat button{height:32px;display:inline-flex;align-items:center;padding:0 12px;border:1px solid var(--line-2);border-radius:8px;background:var(--panel-2);color:var(--ink);font-size:13.5px;text-decoration:none;cursor:pointer}
#v-subadm table{width:100%;border-collapse:collapse;font-size:13.5px}
#v-subadm th,#v-subadm td{text-align:left;padding:7px 6px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}
#v-subadm th{color:var(--ink-2);font-weight:500;font-size:12.5px}
#v-subadm td .st{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;background:var(--panel-3)}
#v-subadm td .st.new{background:var(--amber);color:#1a1203;font-weight:700}
#v-subadm td button{height:28px;padding:0 10px;border:1px solid var(--line-2);border-radius:7px;background:var(--panel-2);color:var(--ink);font-size:12.5px;cursor:pointer}
#v-subadm .muted{color:var(--ink-2);font-size:13px}
#v-subadm .fbbody{white-space:pre-wrap;max-width:520px}
@media (max-width:820px){.supfab{bottom:84px;right:14px;height:42px;padding:0 12px}.supfab span{display:none}.suppanel{right:12px;bottom:134px}}`);

  const ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/><path d="M9 10h.01M12 10h.01M15 10h.01"/></svg>';
  let tab = 'faq';
  function ensure() {
    let fab = document.getElementById('supFab');
    if (fab) return;
    fab = document.createElement('button'); fab.type = 'button'; fab.id = 'supFab'; fab.className = 'supfab';
    fab.setAttribute('aria-haspopup', 'dialog'); fab.setAttribute('aria-expanded', 'false');
    fab.innerHTML = ICON + '<span>客服</span>';
    document.body.appendChild(fab);
    const p = document.createElement('div'); p.id = 'supPanel'; p.className = 'suppanel'; p.hidden = true; p.setAttribute('role', 'dialog'); p.setAttribute('aria-label', '客服與意見反饋');
    document.body.appendChild(p);
    fab.onclick = () => toggle();
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !p.hidden) toggle(false); });
  }
  function toggle(want) {
    const p = document.getElementById('supPanel'), fab = document.getElementById('supFab');
    const open = want == null ? p.hidden : want;
    p.hidden = !open; fab.setAttribute('aria-expanded', String(open));
    if (open) paint();
  }
  function paint() {
    const p = document.getElementById('supPanel'); if (!p) return;
    p.innerHTML = `<div class="sph"><b>需要幫忙嗎？</b><button type="button" id="supClose" aria-label="關閉">×</button></div>
      <div class="spai"><b>AI 客服即將推出</b>　目前請先看常見問題，或留言給我們（真人回覆）。</div>
      <div class="sptabs" role="tablist">${[['faq', '常見問題'], ['fb', '意見反饋'], ['mail', '寄信']].map(([k, n]) => `<button type="button" role="tab" data-t="${k}" class="${tab === k ? 'on' : ''}" aria-selected="${tab === k}">${n}</button>`).join('')}</div>
      <div class="spbody" id="supBody">${body()}</div>`;
    p.querySelector('#supClose').onclick = () => toggle(false);
    p.querySelector('.sptabs').onclick = (e) => { const b = e.target.closest('button[data-t]'); if (b) { tab = b.dataset.t; paint(); } };
    p.querySelectorAll('.faq > button').forEach((b) => { b.onclick = () => { const f = b.parentElement; f.classList.toggle('on'); b.setAttribute('aria-expanded', String(f.classList.contains('on'))); }; });
    const go = p.querySelector('#fbSend'); if (go) go.onclick = send;
  }
  function body() {
    if (tab === 'faq') return FAQ.map(([q, a], i) => `<div class="faq" data-i="${i}"><button type="button" aria-expanded="false">${esc(q)}</button><div class="ans">${esc(a)}</div></div>`).join('')
      + `<p class="note">找不到答案？到「意見反饋」留言，或看 <a href="#pricing">訂閱方案</a>。</p>`;
    if (tab === 'mail') return `<p class="note">寄信給客服（一般 1～2 個工作天內回覆）：</p><a class="mail" id="supMail" href="mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent('台股資金輪動儀表板｜客服')}">${SUPPORT_EMAIL}</a>
      <p class="note">付款或方案問題請在信裡註明你登入用的 email。本網站不是證券投資顧問，無法回答個股買賣問題。</p>`;
    const A = window.TwAccount, u = A && A.on() ? A.user() : null;
    const can = !!(A && A.on());
    return `${can ? '' : '<p class="note" style="color:var(--amber)">線上反饋暫時無法使用，請改用「寄信」。</p>'}
      <label for="fbCat">類別</label><select id="fbCat">${CATS.map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}</select>
      <label for="fbBody">內容</label><textarea id="fbBody" maxlength="2000" placeholder="發生了什麼事、在哪一頁、希望怎麼改…"></textarea>
      <label class="chk"><input type="checkbox" id="fbCtx" checked> 附上目前網址與瀏覽器資訊（幫助我們重現問題）</label>
      <label for="fbMail">聯絡 email（選填，要回覆時用）</label><input type="email" id="fbMail" maxlength="200" value="${esc(u && u.email || '')}" autocomplete="email">
      <button type="button" class="go" id="fbSend" ${can ? '' : 'disabled'}>送出</button>
      <div class="msg" id="fbMsg" role="status"></div>
      <p class="note">反饋只存在本站伺服器（保存 13 個月，刪除帳號時一併刪除），不會提供給第三方。</p>`;
  }
  async function send() {
    const p = document.getElementById('supPanel');
    const msg = p.querySelector('#fbMsg'), btn = p.querySelector('#fbSend');
    const text = p.querySelector('#fbBody').value.trim(), contact = p.querySelector('#fbMail').value.trim();
    if (text.length < 2) { msg.className = 'msg bad'; msg.textContent = '請先寫一點內容'; return; }
    if (contact && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)) { msg.className = 'msg bad'; msg.textContent = 'email 格式不對（不想留可以空白）'; return; }
    const ctx = p.querySelector('#fbCtx').checked;
    const body = { cat: p.querySelector('#fbCat').value, body: text };
    if (contact) body.contact = contact;
    if (ctx) { body.url = location.href.slice(0, 300); body.ua = (navigator.userAgent + ' ｜ ' + innerWidth + '×' + innerHeight).slice(0, 300); }
    btn.disabled = true; msg.className = 'msg'; msg.textContent = '送出中…';
    const j = await call('/v1/feedback', body);
    btn.disabled = false;
    if (j && j._s === 200 && j.ok) {
      p.querySelector('#fbBody').value = '';
      msg.className = 'msg ok'; msg.textContent = '已收到，謝謝你！' + (contact ? '我們會回信到 ' + contact : '');
    } else {
      msg.className = 'msg bad';
      msg.textContent = j && j._s === 429 ? '今天送出太多次了，請改用寄信' : '送出失敗，請稍後再試，或改用「寄信」';
    }
  }

  // ------------------------------------------------------------------ 管理端 #admin/feedback
  const CATN = Object.fromEntries(CATS);
  const dstr = (ms) => { const d = new Date(ms + 8 * 3600 * 1000); return d.toISOString().slice(0, 16).replace('T', ' '); };
  async function renderFeedbackAdmin(el) {
    const A = window.TwAccount, u = A && A.on() ? A.user() : null;
    if (!u || !u.admin) { el.innerHTML = '<div class="card"><h2>管理頁</h2><p class="muted">這一頁只有管理者看得到' + (u ? '' : '，請先登入') + '。</p></div>'; return; }
    el.innerHTML = '<div class="card"><p class="muted">載入中…</p></div>';
    const j = await call('/v1/admin/feedback/list', {});
    if (!j || j._s !== 200) { el.innerHTML = '<div class="card"><p class="muted">讀取失敗（' + esc(j ? j._s : '連不到') + '）。Worker 可能還沒更新成有這支 API 的版本。</p></div>'; return; }
    const fb = j.feedback || [], rq = j.requests || [];
    const nNew = fb.filter((x) => x.status === 'new').length, rNew = rq.filter((x) => x.status === 'new').length;
    el.innerHTML = `<div class="sat"><h2>意見反饋與訂閱申請</h2><a href="#admin/notices">公告管理</a><a href="#admin/traffic">回管理區</a><button type="button" id="fbReload">重新整理</button></div>
      <div class="card"><h3>訂閱申請（${rq.length} 筆，未處理 ${rNew}）</h3><p class="muted">金流尚未串接：確認付款後到「會員管理」替他設定方案與到期日，再把這筆標成「已開通」。</p>
        ${rq.length ? `<table id="rqTable"><thead><tr><th>時間（台北）</th><th>會員</th><th>方案</th><th>週期</th><th>聯絡 email</th><th>備註</th><th>狀態</th><th></th></tr></thead><tbody>${rq.map((r) => `<tr data-id="${esc(r.id)}">
          <td>${dstr(r.created)}</td><td>${esc(r.name || '')}<br><small class="muted">${esc(r.email || '')}</small></td><td>${esc(r.plan)}</td><td>${r.period === 'year' ? '年繳' : '月繳'}</td><td>${esc(r.contact)}</td><td>${esc(r.note || '')}</td>
          <td><span class="st ${r.status === 'new' ? 'new' : ''}">${r.status === 'new' ? '待處理' : '已開通'}</span></td>
          <td><button type="button" data-kind="request" data-id="${esc(r.id)}" data-st="${r.status === 'new' ? 'done' : 'new'}">${r.status === 'new' ? '標為已開通' : '改回待處理'}</button></td></tr>`).join('')}</tbody></table>` : '<p class="muted">還沒有人申請。</p>'}</div>
      <div class="card"><h3>意見反饋（${fb.length} 筆，未處理 ${nNew}）</h3>
        ${fb.length ? `<table id="fbTable"><thead><tr><th>時間（台北）</th><th>類別</th><th>內容</th><th>聯絡</th><th>網址／瀏覽器</th><th>狀態</th><th></th></tr></thead><tbody>${fb.map((r) => `<tr data-id="${esc(r.id)}">
          <td>${dstr(r.created)}</td><td>${esc(CATN[r.cat] || r.cat)}</td><td class="fbbody">${esc(r.body)}</td>
          <td>${r.contact ? `<a href="mailto:${esc(r.contact)}">${esc(r.contact)}</a>` : '<span class="muted">（未留）</span>'}${r.member ? '<br><small class="muted">會員' + (r.name ? '：' + esc(r.name) : '') + '</small>' : '<br><small class="muted">訪客</small>'}</td>
          <td><small>${esc(r.url || '')}<br>${esc(r.ua || '')}</small></td>
          <td><span class="st ${r.status === 'new' ? 'new' : ''}">${r.status === 'new' ? '未處理' : '已處理'}</span></td>
          <td><button type="button" data-kind="feedback" data-id="${esc(r.id)}" data-st="${r.status === 'new' ? 'handled' : 'new'}">${r.status === 'new' ? '標為已處理' : '改回未處理'}</button></td></tr>`).join('')}</tbody></table>` : '<p class="muted">還沒有反饋。</p>'}</div>`;
    el.querySelector('#fbReload').onclick = () => renderFeedbackAdmin(el);
    el.querySelectorAll('button[data-kind]').forEach((b) => {
      b.onclick = async () => {
        b.disabled = true;
        const r = await call('/v1/admin/feedback/set', { kind: b.dataset.kind, id: b.dataset.id, status: b.dataset.st });
        if (r && r._s === 200) renderFeedbackAdmin(el); else { b.disabled = false; toast('更新失敗'); }
      };
    });
  }
  window.TwSupport = { open: () => toggle(true), close: () => toggle(false), renderFeedbackAdmin, email: SUPPORT_EMAIL, faq: FAQ };
  /* 管理端路由：#admin/feedback（這支畫）。#admin/notices 給 notices.js。view 共用 #v-subadm */
  window.TwSubRoutes.push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'feedback') return null;
    const v = view('v-subadm'); if (!v) return null;
    renderFeedbackAdmin(v);
    return 'v-subadm';
  });
  window.addEventListener('tw:account', () => {
    if ((location.hash || '') === '#admin/feedback') { const v = view('v-subadm'); if (v) renderFeedbackAdmin(v); }
    const p = document.getElementById('supPanel'); if (p && !p.hidden && tab === 'fb') paint();
  });
  /* 管理區不放浮動鈕：#admin/perm 底部的「儲存」列是 sticky 在右下角，浮動鈕會正好蓋住「儲存」（驗收實測點不到）。
     管理者在管理區用不到客服；離開管理區就回來。*/
  function syncFab() {
    const fab = document.getElementById('supFab'); if (!fab) return;
    const adm = (location.hash || '').startsWith('#admin');
    fab.hidden = adm;
    if (adm) { const p = document.getElementById('supPanel'); if (p && !p.hidden) toggle(false); }
  }
  window.addEventListener('hashchange', syncFab);
  const boot = () => { ensure(); syncFab(); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
