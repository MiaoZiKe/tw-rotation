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
  /* ★ 2026-10-16 Andy：結帳加姓名＋性別（男／女），性別納入男女用量比例。三個開關（Worker 的 pay.js 有同名常數要一起改）：
       GENDER_REQUIRED          性別必選才能前往付款／送出匯款資料（Andy 10-16 最終決定：選填，所以現在是 false；改 true 就變必填）
       GENDER_CONSENT_REQUIRED  性別另設「獨立勾選同意」（選填版本不需要；改必填時要一起改 true；法遵意見 docs/legal/gender_collection_1016.md 3-3）
       FORM_VERSION             表單版本；Worker 看到 form>=2 才強制檢查，舊版快取網頁不受影響 */
  const GENDER_REQUIRED = false, GENDER_CONSENT_REQUIRED = false, FORM_VERSION = 2;
  const GENDERS = [['male', '男'], ['female', '女']];
  /* 卡號防呆（法遵意見 7-2）：本站任何欄位都不收卡號；連續 13～19 位數字（可夾空白、連字號）一律擋 */
  const looksCard = (v) => /\d(?:[ -]?\d){12,18}/.test(String(v == null ? '' : v));
  const CARD_MSG = '偵測到可能是卡號的內容，為保護您的資料已拒絕，請只填轉出帳號末 5 碼。';
  /* 經營者與客服信箱都讀網站現有常數（legal.js 的 CONTACT_EMAIL、support.js 的 SUPPORT_EMAIL），不在這裡另寫一份 */
  const supportMail = () => (window.TwSupport && window.TwSupport.email) || '';
  const ST_CLS = { pending: 'wait', review: 'wait', paid: 'wait', active: 'ok', failed: 'bad', rejected: 'bad', expired: 'mute', refunded: 'mute', cancelled: 'mute', superseded: 'mute' };
  const ST_NAME = { pending: '待付款', review: '待確認', paid: '已入帳', active: '已開通', failed: '失敗', rejected: '已退回', expired: '已逾期', refunded: '已退款', cancelled: '已取消（未付款）', superseded: '已被取代' };
  const S = { my: null, fly: null, poll: null };
  const me = () => { const a = A(); return a && a.on && a.on() ? a.user() : null; };
  const call = (p, b) => { const a = A(); return a && a.on() ? a.call(p, b || {}) : Promise.resolve(null); };

  function css() {
    if (!T()) return;
    T().css('coCss', `
#subDlg .codlg .cohd .sp{flex:1}
#subDlg .codlg .cohd button{width:32px;height:32px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer;font-size:18px;line-height:1}
#subDlg .codlg .cotest{font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid var(--amber);color:var(--amber);white-space:nowrap}
#subDlg .codlg .codue{grid-column:1/-1;color:var(--amber);font-size:13px}
#subDlg .codlg .cocfm{margin-top:10px;text-align:left;padding:12px 14px}
#subDlg .codlg .cocfm>b{font-size:14px}
#subDlg .codlg .cooff.cocfm{text-align:left}
#subDlg .codlg .cocfm .kv{margin:8px 0 10px;display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 16px;text-align:left}
#subDlg .codlg .cocfm .cfbtn{display:flex;gap:8px;align-items:stretch}
#subDlg .codlg .cocfm .cfbtn button{height:44px;margin:0;border-radius:10px;font:inherit;font-size:14px;white-space:nowrap}
#subDlg .codlg .cocfm #coCfmBack{flex:none;padding:0 16px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer}
#subDlg .codlg .cocfm .cogo{flex:1;font-size:15px}
#subDlg .codlg .cooff{border:1px dashed var(--line-2);border-radius:10px;padding:14px;color:var(--ink-2);font-size:14px;text-align:center}
#subDlg .codlg .msg{margin-top:8px}
#subDlg .codlg .codone{text-align:center;padding:10px 0}
#subDlg .codlg .codone h3{font-size:18px;margin:6px 0}
/* 2026-10-16 結帳視窗重做（Andy 退件：歪七扭八、大小不一、文字沒置中、性別佔太大）：
   一組間距 12／16、三級字 16／14／12、所有輸入框統一 44px 高、同一排用 grid 等分、標籤放欄位上方；一律限定在 #subDlg .codlg 內 */
#subDlg .box.codlg{width:min(560px,100%);padding:0;overflow:auto}
#subDlg .codlg .cohd{display:flex;align-items:center;gap:8px;padding:16px}
#subDlg .codlg .cohd b{font-size:16px;line-height:24px}
#subDlg .codlg .cohd button{font-size:16px;line-height:1}
#subDlg .codlg .cobadge{display:inline-flex;align-items:center;justify-content:center;height:24px;padding:0 12px;border-radius:999px;background:color-mix(in srgb,var(--cyan) 16%,transparent);color:var(--cyan);font-size:12px;font-weight:600;line-height:1;white-space:nowrap}
#subDlg .codlg .cobd{padding:0 16px 16px}
#subDlg .codlg .coamt{display:flex;align-items:baseline;gap:8px;white-space:nowrap;font-size:16px;font-weight:700;line-height:24px;color:var(--ink);font-variant-numeric:tabular-nums;text-align:right}
#subDlg .codlg .coamt .coday{font-size:12px;font-weight:400;color:var(--ink-2);line-height:16px}
#subDlg .codlg .cooid{text-align:center;font-size:12px;line-height:16px;color:var(--ink-2);margin:-8px 0 16px}
#subDlg .codlg .cooid code{font-family:var(--mono,ui-monospace,monospace);color:var(--ink)}
#subDlg .codlg .cotabs{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--line-2);border-radius:10px;overflow:hidden;margin:0 0 16px}
#subDlg .codlg .cotabs button{height:44px;padding:0 8px;border:0;background:transparent;color:var(--ink-2);cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:14px;line-height:18px;text-align:center}
#subDlg .codlg .cotabs button small{display:block;font-size:12px;line-height:16px;font-weight:400;color:var(--ink-2)}
#subDlg .codlg .cotabs button[aria-selected=true]{background:var(--cyan);color:#04121a;font-weight:700}
#subDlg .codlg .cotabs button[aria-selected=true] small{color:#04121a}
#subDlg .codlg .cog{display:grid;gap:12px;margin:0 0 12px}
#subDlg .codlg .cog.c2{grid-template-columns:repeat(2,minmax(0,1fr))}
#subDlg .codlg .cog.c3{grid-template-columns:repeat(3,minmax(0,1fr))}
#subDlg .codlg .cog .fld{display:flex;flex-direction:column;gap:4px;min-width:0}
#subDlg .codlg .cog .nmrow{display:flex;align-items:center;gap:8px;min-width:0}
#subDlg .codlg .cog .nmrow input{flex:1;min-width:0;width:auto}
#subDlg .codlg .cog.cb .dt{grid-column:1/-1}
#subDlg .codlg .cog .fld>label,#subDlg .codlg .cog .fld>.lb{display:block;margin:0;font-size:12px;line-height:16px;font-weight:400;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#subDlg .codlg .cog em{font-style:normal;margin-left:4px;font-size:12px}
#subDlg .codlg .cog em.req{color:var(--rise)}
#subDlg .codlg .cog em.opt{color:var(--ink-2)}
#subDlg .codlg .cog input{display:block;width:100%;box-sizing:border-box;height:44px;margin:0;padding:0 12px;border:1px solid var(--line-2);border-radius:10px;background:var(--panel);color:var(--ink);font:inherit;font-size:14px}
#subDlg .codlg .cog input::placeholder{color:var(--ink-3);font-size:14px}
#subDlg .codlg .cogd{display:inline-flex;gap:8px;margin:0;flex:none}
#subDlg .codlg .cogd button{flex:none;width:32px;height:32px;min-height:0;padding:0;border-radius:50%;border:1px solid var(--line-2);background:transparent;color:var(--ink-2);font-size:14px;line-height:1;display:inline-flex;align-items:center;justify-content:center;cursor:pointer}
#subDlg .codlg .cogd button[aria-checked=true]{background:var(--cyan);border-color:var(--cyan);color:#04121a;font-weight:700}
#subDlg .codlg .cohelpb{flex:none;width:32px;height:32px;padding:0;border-radius:50%;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink-2);font-size:14px;line-height:1;display:inline-flex;align-items:center;justify-content:center;cursor:pointer}
#subDlg .codlg .cohelpb[aria-expanded=true]{border-color:var(--cyan);color:var(--cyan)}
#subDlg .codlg .cohelp{margin:0 0 12px;padding:12px 12px 12px 28px;border:1px solid var(--line-2);border-radius:10px;font-size:12px;line-height:20px;color:var(--ink-2);background:color-mix(in srgb,var(--cyan) 5%,transparent)}
#subDlg .codlg .cohelp[hidden]{display:none}
#subDlg .codlg .cohelp li{margin:0 0 4px}
#subDlg .codlg .cohelp li:last-child{margin:0}
#subDlg .codlg .cohelp b{color:var(--ink)}
#subDlg .codlg .cohelp a,#subDlg .codlg .coagree a{color:var(--cyan)}
#subDlg .codlg .cogc{display:flex;gap:12px;align-items:flex-start;margin:0 0 12px;font-size:12px;line-height:20px;color:var(--ink)}
#subDlg .codlg .cogc input{flex:none;width:20px;height:20px;margin:0}
#subDlg .codlg .coagree{display:flex;gap:12px;align-items:flex-start;margin:4px 0 16px;font-size:12px;line-height:20px;color:var(--ink)}
#subDlg .codlg .coagree input{flex:none;width:20px;height:20px;margin:0}
#subDlg .codlg .coagree b{font-weight:700}
#subDlg .codlg .cobank{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-auto-rows:1fr;gap:12px;margin:0 0 12px}
#subDlg .codlg .cobc{display:flex;align-items:center;gap:8px;min-height:56px;padding:8px 12px;box-sizing:border-box;border:1px solid var(--line-2);border-radius:10px;min-width:0}
#subDlg .codlg .cobt{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center}
#subDlg .codlg .cobt span{font-size:12px;line-height:16px;color:var(--ink-2)}
#subDlg .codlg .cobt b{font-size:14px;line-height:20px;font-variant-numeric:tabular-nums;word-break:break-all}
#subDlg .codlg .cobc button{flex:none;width:48px;height:32px;padding:0;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:12px;line-height:1;display:inline-flex;align-items:center;justify-content:center;cursor:pointer}
#subDlg .codlg .cogo{display:flex;align-items:center;justify-content:center;width:100%;height:48px;margin:0;padding:0;border-radius:10px;border:0;background:var(--cyan);color:#04121a;font-weight:700;font-size:16px;line-height:1;cursor:pointer}
#subDlg .codlg .cogo[hidden]{display:none}
#subDlg .codlg .cogo:disabled{opacity:.45;cursor:not-allowed}
#subDlg .codlg .conote{margin:12px 0 0;font-size:12px;line-height:16px;color:var(--ink-2);text-align:center}
#subDlg .codlg .conote[hidden]{display:none}
#subDlg .codlg .coop{margin:12px 0 0;font-size:12px;line-height:16px;color:var(--ink-2);text-align:center}
#subDlg .codlg .msg{margin-top:12px;text-align:center;font-size:12px;line-height:16px}
#subDlg .codlg .msg:empty{display:none}
#subDlg .codlg .cocfm{margin-top:12px}
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
:root[data-theme=light] #subDlg .codlg .cogo,:root[data-theme=light] #subDlg .codlg .cogd button[aria-checked=true],
:root[data-theme=light] #v-orders button.pri,:root[data-theme=light] #payRenew button.pri{color:#fff}
html.pay-renew #acctBtn.ame{position:relative}
html.pay-renew #acctBtn.ame::after{content:'';position:absolute;top:2px;right:2px;width:9px;height:9px;border-radius:50%;background:var(--rise);box-shadow:0 0 0 2px var(--bg)}
.acctmenu .ordi .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--rise);margin-left:6px;vertical-align:middle}
@media (max-width:640px){
  #subDlg .box.codlg{max-height:calc(100vh - 16px)}
  #subDlg .codlg .cog.c2.ce{grid-template-columns:minmax(0,1fr)}
  #subDlg .codlg .cog.cb .pn{grid-column:1/-1}
  #subDlg .codlg .cog.cb .dt{grid-column:auto}
  #subDlg .codlg .coamt{flex-direction:column;align-items:flex-end;gap:0}
  #subDlg .codlg .cotest{width:10px;height:10px;min-width:10px;padding:0;border-radius:50%;background:var(--amber);border:0;overflow:hidden;flex:none}
  #subDlg .codlg .cotest .tx{display:none}
  #v-orders .ordr{grid-template-columns:minmax(0,1fr) auto;gap:2px 8px;padding:10px 2px}
  #v-orders .ordr.hd{display:none}
  #v-orders .ordr>div{text-align:left}
  #v-orders .ordr>.c-time{grid-column:1/-1;color:var(--ink-2);font-size:12px}
  #v-orders .ordr .act{grid-column:1/-1;justify-content:flex-start}
  #payRenew{margin:8px 0 0}
}`);
  }

  /* ---------------------------------------------------------------- ① 結帳面板 */
  /* 2026-10-16 Andy「版面文字太多且排版太浪費空間，姓名跟性別可以同一排」：
     欄位旁只留一行必要告知（用途＋隱私權政策連結），其餘長說明一律收進「ⓘ 說明」，預設收起、點了才展開（手機五準則第 3、5 條）。
     法遵必要告知一個字都沒少：只是從「常駐」變成「一句常駐＋完整說明可展開」。 */
  /* 2026-10-16 Andy「男女不要文字，改成符號」「性別版面還是佔太多」：♂ ♀ 兩顆 32×32 小鈕直接放在姓名欄同一排右側，
     不再有獨立的性別一行與「性別 選填」標籤；畫面上沒有「男」「女」字，改用 aria-label／title。
     符號用 SVG 畫（♂♀ 字元在不同字型的基線不一樣，字元置中靠不住），畫的圖形外框中心在 viewBox 正中央。 */
  const GSVG = {
    male: '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9.5" cy="14.5" r="5"/><path d="M13.5 10.5 19 5M14.5 5H19v4.5"/></g></svg>',
    female: '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="9" r="5"/><path d="M12 14v7M9 18h6"/></g></svg>',
  };
  const GTITLE = { male: '男', female: '女' };
  function genderBtns() {
    return `<div class="cogd" role="radiogroup" aria-label="性別（${GENDER_REQUIRED ? '必選' : '選填'}）">${GENDERS.map(([k, n]) => `<button type="button" role="radio" aria-checked="false" aria-label="${n}" title="${GTITLE[k] || n}" data-g="${k}">${GSVG[k]}</button>`).join('')}</div>`;
  }
  const helpB = '<button type="button" class="cohelpb" aria-expanded="false" aria-label="說明" title="說明">ⓘ</button>';
  const genderConsent = () => (GENDER_CONSENT_REQUIRED ? '<label class="cogc"><input type="checkbox" class="cogcb"><span>我已閱讀<a href="#privacy" target="_blank" rel="noopener">《隱私權政策》</a>，同意本網站為上述統計目的，蒐集並使用我於結帳時選擇的性別。</span></label>' : '');
  /* 完整說明（預設收起）：kind＝ecpay／bank */
  function helpHtml(kind) {
    const mail = supportMail();
    const g = `<li><b>性別 ♂／♀（${GENDER_REQUIRED ? '必選' : '選填'}）</b>：姓名欄右側的 ♂ 是男、♀ 是女；用於<b>不具名的使用情形統計</b>（只呈現男女比例，不會單獨顯示個別會員，也不用於推薦、行銷或對外提供），僅用於匿名彙總統計，不公開，僅管理者可讀。${GENDER_REQUIRED ? `本欄位為結帳必填，<b>未選擇將無法送出結帳</b>。不願提供性別？請來信客服${mail ? '（' + esc(mail) + '）' : ''}，由人工協助開通。` : '<b>不選擇不影響結帳與任何功能</b>，未選擇者統計時歸入「未填」；選錯了可再按一次選中的按鈕取消。'}</li>`;
    const pr = '<li><b>個資處理</b>：依<a href="#privacy" target="_blank" rel="noopener">《隱私權政策》</a>「付款與訂單資料」辦理。</li>';
    return kind === 'bank'
      ? `<ul class="cohelp" hidden><li><b>匯款人姓名、轉出帳號末 5 碼</b>：僅用於核對這筆匯款是否為您本人所匯。<b>請勿填寫完整帳號、信用卡號、身分證字號。</b></li>${g}${pr}</ul>`
      : `<ul class="cohelp" hidden><li><b>姓名</b>：用於付款核對、確認入帳與退款，請填寫真實姓名。</li>${g}
        <li><b>轉出帳號末 5 碼（選填）</b>：若你之後改用 ATM 轉帳／超商繳款，可填轉出帳號末 5 碼供我們核對。<b>這不是信用卡號，請勿填寫信用卡卡號的任何數字。</b></li>
        <li><b>信用卡</b>：卡片資料將於下一步由綠界科技的付款頁輸入，本網站不會看到、也不會保存你的卡號。可隨時在「我的訂單」取消自動續訂，已付的期間照常用到期滿。</li>${pr}</ul>`;
  }
  const nameOf = (p) => (p && (p.planName || p.name)) || '';
  async function open(opt) {
    const p = opt || {};
    const plan = String(p.plan || '');
    let per = p.per === 'year' ? 'year' : 'month';
    const req = per;   // 使用者在訂閱頁選的週期（被擋時會改成另一個，畫面要說明）
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
    const st = { per, tab: p.tab === 'bank' ? 'bank' : 'ecpay', kind: 'recur', oid: '', bankOrder: null, gender: '', gc: false, cfm: false };
    const base = Q[per];
    box.innerHTML = `<div class="cohd"><b id="coName">${esc(nameOf(base))}</b><span class="cobadge" id="coBadge">${st.per === 'year' ? '年繳' : '月繳'}</span>${base.test ? '<span class="cotest" title="測試模式：綠界金鑰還沒設定，付款會走綠界測試環境，不會真的扣款"><span class="tx">測試模式</span></span>' : ''}<span class="sp"></span><div class="coamt" id="coAmt"></div><button type="button" data-close aria-label="關閉">×</button></div>
      <div class="cobd">
        ${req !== st.per ? `<p class="conote" style="margin:0 0 12px">你選的週期目前不能購買，已改為${st.per === 'year' ? '年繳' : '月繳'}。</p>` : ''}
        <div class="cotabs" role="tablist" aria-label="付款方式"><button type="button" role="tab" id="coTabE" data-tab="ecpay">信用卡<small>綠界 ECPay・自動續扣</small></button><button type="button" role="tab" id="coTabB" data-tab="bank">銀行轉帳<small>預付制・人工確認</small></button></div>
        <div id="coPaneE" role="tabpanel" aria-labelledby="coTabE">
          <div class="cog c2 ce" id="coFrmE">
            <div class="fld"><label for="coNameE">姓名<em class="req">必填</em></label><div class="nmrow"><input id="coNameE" maxlength="40" autocomplete="name" required aria-required="true">${genderBtns()}</div></div>
            <div class="fld"><label for="coL5E">轉出帳號末 5 碼<em class="opt">選填</em></label><div class="nmrow"><input id="coL5E" inputmode="numeric" autocomplete="off" placeholder="5 位數字">${helpB}</div></div>
          </div>
          ${genderConsent()}${helpHtml('ecpay')}
        </div>
        <div id="coPaneB" role="tabpanel" aria-labelledby="coTabB" hidden></div>
        <label class="coagree"><input type="checkbox" id="coAgree"><span id="coAgreeT"></span></label>
        <button type="button" class="cogo" id="coGoE" disabled>前往綠界付款</button>
        <button type="button" class="cogo" id="coSendB" hidden>我已轉帳，送出匯款資料</button>
        <p class="conote" id="coBankNote" hidden>訂單編號 <code id="coOid"></code>・管理者確認入帳後開通，可在「我的訂單」查看。</p>
        <div class="msg" id="coMsg" role="status"></div>
      </div>`;
    const $ = (s) => box.querySelector(s);
    const msg = (t, bad) => { const m = $('#coMsg'); m.className = 'msg ' + (bad ? 'bad' : 'ok'); m.textContent = t; };
    const consent = () => ({ consent_at: new Date().toISOString(), consent_version: window.TwLegal && window.TwLegal.termsVersion ? window.TwLegal.termsVersion() : 'unknown', consent: 'terms+refund+privacy;immediate_start;waive_cpa19' + (st.tab === 'ecpay' ? ';auto_renew' : '') });
    /* 同意句（單一勾選）：信用卡分頁含「自動續扣＋金額＋直到我自行取消」，轉帳分頁沒有續扣那段；金額與每月／每年跟著週期顯示 */
    const agreeHtml = () => {
      const per = st.per === 'year' ? '年' : '月', amt = nt(Q[st.per].amount);
      const renew = st.tab === 'ecpay' ? `同意每${per}自動續扣 <b>NT$ ${amt}</b>，<b>直到我自行取消</b>，` : '';
      return `我已閱讀並同意<a href="#terms" target="_blank" rel="noopener">《使用條款》</a><a href="#refund" target="_blank" rel="noopener">《退款與取消訂閱政策》</a><a href="#privacy" target="_blank" rel="noopener">《隱私權政策》</a>，${renew}並同意付款後立即開通、排除<a href="#refund" target="_blank" rel="noopener">消費者保護法第 19 條之七日解除權</a>。`;
    };
    let agreeKey = '';
    function sync() {
      const q = Q[st.per];
      /* 10-16 Andy：金額旁換算一天多少台幣；跟方案卡同一個函式（TwSub.dayCost），口徑＝一年總價 ÷ 365 */
      const dc = T().dayCost ? T().dayCost(q.amount, st.per) : null;
      $('#coAmt').innerHTML = `<span class="coa1">NT$ ${nt(q.amount)}／${st.per === 'year' ? '年' : '月'}</span>${dc == null ? '' : `<span class="coday" id="coDay">每天約 NT$ ${dc.toFixed(1)}</span>`}`;
      const ak = st.tab + st.per + q.amount;
      if (ak !== agreeKey) { agreeKey = ak; $('#coAgreeT').innerHTML = agreeHtml(); }
      box.querySelectorAll('.cogd button').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.g === st.gender)));
      box.querySelectorAll('.cogcb').forEach((c) => { c.checked = st.gc; });
      const nm = $('#coNameE');
      $('#coGoE').disabled = !($('#coAgree').checked && profOk(nm ? nm.value : '') && l5Ok($('#coL5E') ? $('#coL5E').value : ''));
      box.querySelectorAll('.cotabs button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === st.tab)));
      $('#coPaneE').hidden = st.tab !== 'ecpay'; $('#coPaneB').hidden = st.tab !== 'bank';
      $('#coGoE').hidden = st.tab !== 'ecpay';   // 信用卡鈕與轉帳送出鈕共用視窗底部
      const sb = $('#coSendB'); sb.hidden = st.tab !== 'bank' || !st.bankOrder || st.cfm; sb.disabled = !$('#coAgree').checked;   // 性別／姓名沒填：按下去用文字擋
      $('#coBankNote').hidden = st.tab !== 'bank' || !st.bankOrder;
      const oidTxt = st.tab === 'bank' && st.bankOrder ? st.bankOrder.id : '';
      $('#coOid').textContent = oidTxt;
    }
    /* 10-16 Andy：只剩信用卡定期定額（單次付款拿掉）；姓名、性別、獨立同意、卡號防呆 */
    const genderOk = () => (!GENDER_REQUIRED || !!st.gender) && (!st.gender || !GENDER_CONSENT_REQUIRED || st.gc);
    const profOk = (name) => !!String(name || '').trim() && !looksCard(name) && genderOk();
    const l5Ok = (v) => !String(v || '').trim() || /^\d{5}$/.test(String(v).trim());
    /* ⓘ 說明：展開／收起同一個分頁裡的完整說明（預設收起） */
    box.addEventListener('click', (e) => {
      const hb = e.target.closest('.cohelpb'); if (!hb) return;
      const pane = hb.closest('[role=tabpanel]'), hp = pane && pane.querySelector('.cohelp'); if (!hp) return;
      hp.hidden = !hp.hidden; pane.querySelectorAll('.cohelpb').forEach((x) => x.setAttribute('aria-expanded', String(!hp.hidden)));
    });
    box.addEventListener('click', (e) => { const b = e.target.closest('.cogd button'); if (!b) return; st.gender = st.gender === b.dataset.g && !GENDER_REQUIRED ? '' : b.dataset.g; if (!st.gender) st.gc = false; sync(); });   // 選填時再按一次可取消（單選鈕本身取消不了）
    box.addEventListener('change', (e) => { if (e.target.classList && e.target.classList.contains('cogcb')) { st.gc = e.target.checked; sync(); } });
    box.addEventListener('input', (e) => {
      const el = e.target; if (!el || !/^(coNameE|coL5E|coPayer|coL5)$/.test(el.id)) return;
      /* 末 5 碼欄不設 maxlength：設了的話貼上 16 位卡號會被瀏覽器默默截成前 5 碼，偵測不到；自己處理（卡號格式整串清掉，其餘只留前 5 位數字） */
      if (looksCard(el.value)) { el.value = ''; msg(CARD_MSG, true); }
      else {
        if (/^coL5/.test(el.id)) el.value = el.value.replace(/\D/g, '').slice(0, 5);
        if ($('#coMsg').textContent === CARD_MSG) msg('');   // 卡號提示只在剛擋下時顯示，改填正確內容就收掉
      }
      sync();
    });
    box.addEventListener('paste', (e) => {
      const el = e.target; if (!el || !/^(coNameE|coL5E|coPayer|coL5)$/.test(el.id)) return;
      const t = (e.clipboardData && e.clipboardData.getData('text')) || '';
      if (looksCard(t) || (/^coL5/.test(el.id) && t.replace(/\D/g, '').length > 5)) { e.preventDefault(); msg(looksCard(t) ? CARD_MSG : '末 5 碼欄只能填 5 位數字', true); }
    });
    $('#coAgree').onchange = sync;
    box.querySelectorAll('.cotabs button').forEach((b) => { b.onclick = () => { st.tab = b.dataset.tab; if (st.tab === 'bank' && !st.bankOrder) bankPane(); sync(); }; });
    $('#coGoE').onclick = async () => {
      const btn = $('#coGoE'); btn.disabled = true; msg('建立訂單中…');
      const j = await call('/v1/pay/ecpay/create', { plan, period: st.per, recur: true, back: location.origin + location.pathname, form: FORM_VERSION, name: $('#coNameE').value.trim(), gender: st.gender, gender_consent: st.gc, last5: $('#coL5E').value.trim(), ...consent() });
      if (!j || j._s !== 200 || !j.ok) {
        btn.disabled = false;
        msg(!j ? '連不到會員伺服器，請稍後再試' : j.error === 'blocked' ? (j.msg || '目前方案不能購買這個項目') : j.error === 'too_many' ? '今天建立的訂單太多了，請明天再試或聯絡客服' : j.error === 'need_name' ? '請填姓名' : j.error === 'need_gender' ? '請選擇性別' : j.error === 'need_gender_consent' ? '請勾選性別統計的同意' : j.error === 'card_number' ? CARD_MSG : j.error === 'bad_last5' ? '末 5 碼要是 5 個數字' : j.error === 'no_price' ? '這個方案還沒有線上價格' : `建立訂單失敗（${j._s}）`, true);
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
      const cards = [['銀行', `${b.bank_name}（${b.bank_code}）`, 'coBankName', `${b.bank_name}（${b.bank_code}）`], ['帳號', b.account, 'coBankAcct', b.account], ['戶名', b.holder, '', b.holder], ['應付金額', 'NT$ ' + nt(j.amount), 'coXAmt', String(j.amount)]];
      pane.innerHTML = `<div class="cobank" id="coBank">${cards.map(([k, v, id, cp]) => `<div class="cobc"><div class="cobt"><span>${k}</span><b${id ? ` id="${id}"` : ''}>${esc(v)}</b></div><button type="button" data-copy="${esc(cp)}">複製</button></div>`).join('')}</div>
        <div class="cog c2 cb" id="coFrm">
          <div class="fld pn"><label for="coPayer">匯款人姓名<em class="req">必填</em></label><div class="nmrow"><input id="coPayer" maxlength="40" autocomplete="name" required aria-required="true">${genderBtns()}</div></div>
          <div class="fld"><label for="coL5">轉出帳號末 5 碼</label><div class="nmrow"><input id="coL5" inputmode="numeric" autocomplete="off">${helpB}</div></div>
          <div class="fld dt"><label for="coDate">轉帳日期</label><input id="coDate" type="date" value="${esc(today)}" max="${esc(today)}"></div></div>
        ${genderConsent()}${helpHtml('bank')}`;
      const sbtn = $('#coSendB');
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
      sbtn.onclick = () => {
        const f = { name: $('#coPayer').value.trim(), last5: $('#coL5').value.trim(), date: $('#coDate').value, gender: st.gender, gc: st.gc };
        if (!f.name) { $('#coPayer').focus(); return msg('請填匯款人姓名', true); }
        if (GENDER_REQUIRED && !f.gender) return msg('請選擇性別', true);
        if (f.gender && GENDER_CONSENT_REQUIRED && !f.gc) return msg('請勾選性別統計的同意', true);
        if (!/^\d{5}$/.test(f.last5)) return msg('轉出帳號末 5 碼要是 5 個數字', true);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(f.date)) return msg('請選轉帳日期', true);
        msg('');
        let cf = box.querySelector('#coCfm'); if (cf) cf.remove();
        cf = document.createElement('div'); cf.id = 'coCfm'; cf.className = 'cooff cocfm';
        /* 10-16 Andy：「請調整適當大小排版，文字有點太多」「返回修改」不換行、跟送出鈕同高 */
        cf.innerHTML = `<b>請確認匯款資料（送出後不能修改）</b><div class="kv"><span>匯款人姓名</span><b>${esc(f.name)}</b><span>轉出帳號末 5 碼</span><b>${esc(f.last5)}</b><span>轉帳日期</span><b>${esc(f.date)}</b>${f.gender ? `<span>性別</span><b>${esc((GENDERS.find((g) => g[0] === f.gender) || [])[1] || '')}</b>` : ''}<span>轉帳金額</span><b>NT$ ${nt(j.amount)}</b></div>
          <div class="cfbtn"><button type="button" id="coCfmBack">返回修改</button><button type="button" class="cogo" id="coCfmGo">確認無誤，送出</button></div>`;
        sbtn.after(cf); st.cfm = true; sync();
        cf.querySelector('#coCfmBack').onclick = () => { cf.remove(); st.cfm = false; sync(); };
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
    const j = await call('/v1/pay/bank/report', { id, name: f.name, last5: f.last5, date: f.date, form: FORM_VERSION, gender: f.gender || '', gender_consent: !!f.gc });
    if (j && j._s === 200 && j.ok) { msg(''); done(j.order); return; }
    msg(!j ? '連不到會員伺服器' : j.error === 'need_name' ? '請填匯款人姓名' : j.error === 'need_gender' ? '請選擇性別' : j.error === 'need_gender_consent' ? '請勾選性別統計的同意' : j.error === 'card_number' ? CARD_MSG : j.error === 'bad_date' ? '轉帳日期不對（不能是未來，也不能早於開單日）' : j.error === 'pending_review' ? (j.msg || '你有一筆待審核的訂單，審核完成前只能送出更高級別的方案') : j.error === 'already_reported' ? '這筆已經送出過匯款資料；要更正請用右下角「客服」→「意見反饋」' : j.error === 'bad_status' ? '這筆訂單已經處理過了' : `送出失敗（${j._s}）`, true);
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
