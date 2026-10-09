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
    ['資料多久更新一次？', '盤後資料每個交易日更新三次（台北時間約 15:30 價量、18:30 與 21:30 補齊法人、融資券等）。'],
    ['「即時」和「盤後」差在哪？', '盤中（9:00～13:30）打開「即時」時，報價與分時走勢每 5 秒更新一次，來源是證交所的即時行情；盤後資料（法人、融資券、族群資金流向）要等收盤後官方公布才會算，所以盤中看到的族群排行是前一個交易日的。即時報價只是參考，下單請以券商報價為準。'],
    ['怎麼把股票加進自選？', '在個股頁按股票名稱旁的「☆」（變成「★」就是加進去了，再點一下可以選要放哪幾頁）。自選清單在左側欄「自選」，最多 5 頁、每頁 50 檔（實際可用頁數依方案）。沒登入時清單只存在這台裝置；登入後會跨裝置同步。'],
    ['要登入嗎？登入會拿到我的什麼資料？', '不登入也能用大部分功能。登入用 Google 帳號，我們只收到名稱、email 與大頭貼，拿不到密碼，也不讀 Gmail 或雲端硬碟。細節在頁尾的「隱私權政策」。'],
    ['免費和付費方案差在哪？', '差在可用的功能與每日瀏覽次數。逐項對照請看「訂閱方案」頁的「查看完整權益」。目前付費方案採申請制，由專人開通；線上付款即將推出。'],
    ['怎麼申請付費方案？會馬上扣款嗎？', '到「訂閱方案」頁按「申請訂閱」，選月繳或年繳、留下 email 送出即可。送出不會扣款，我們會寄信跟你確認方案與付款方式，開通後重新整理網頁就生效。'],
    ['為什麼看到「今日已用完」？', '某些方案的個股頁、AI 分析、題材剖析圖有每日次數上限（同一檔一天內重複看不重算）。台北時間每天 0 點自動恢復，升級方案可以增加次數。'],
    ['為什麼有些區塊有鎖頭「此功能需開通」？', '那個功能不在你目前的方案內。訪客登入後通常會多開放一些；其他功能可以到「訂閱方案」頁看哪個方案有。'],
    ['AI 分析是怎麼來的？', '個股頁的 AI 分析是依技術面、籌碼面、基本面、消息面的固定規則自動產生的整理，不是投資建議，也不是真人分析師的意見。'],
    ['這個網站會告訴我該買哪一檔嗎？', '不會。本網站不是證券投資顧問，只提供資料整理與視覺化，不提供個股買賣建議，所有內容僅供參考，投資請自行判斷。'],
    ['畫面怪怪的、圖表沒出來怎麼辦？', '先按 Ctrl+F5（手機下拉重新整理）強制更新。還是不行的話，請用下面的「意見反饋」選「錯誤回報」（細項可選「畫面顯示異常」），勾選附上目前網址與瀏覽器資訊，我們比較好重現。'],
    ['怎麼聯絡客服？', `用這個面板的「意見反饋」送出，或寄信到 ${SUPPORT_EMAIL}。付款相關的問題請在反饋類別選「帳號與付費」。`],
  ];
  /* 2026-10-07（Andy：「聯絡客服改用連結 Gmail」）：mailto: 在沒設郵件程式的 Windows 會跳「郵件」App 設定畫面。改開 Gmail 網頁撰寫。*/
  const gmail = (to, su) => 'https://mail.google.com/mail/?view=cm&fs=1&to=' + encodeURIComponent(to) + '&su=' + encodeURIComponent(su);
  /* 全站「複製信箱」鈕（法律頁、客服面板、管理頁）：document 委派，畫面重畫也不用重綁 */
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('[data-copymail]'); if (!b) return;
    e.preventDefault(); e.stopPropagation();
    const v = b.dataset.copymail, done = () => { const o = b.textContent; b.textContent = '已複製'; b.classList.add('ok'); setTimeout(() => { b.textContent = o; b.classList.remove('ok'); }, 1600); };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(v).then(done, () => { fallbackCopy(v); done(); });
      else { fallbackCopy(v); done(); }
    } catch (x) { fallbackCopy(v); done(); }
  }, true);
  function fallbackCopy(v) {
    const t = document.createElement('textarea'); t.value = v; t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select();
    try { document.execCommand('copy'); } catch (x) { /* 略 */ } t.remove();
  }
  /* 1007 v2（Andy 15:25：「統計意見類別，類別需要由你幫我規劃級分類」）：兩層類別。
     規劃與理由寫在 docs/feedback_categories.md；鍵要跟 workers/account-api/worker.js 的 FB_TREE 一致。
     大類沿用舊鍵 bug／idea／other（舊資料不用搬），舊的 pay（付款問題）→ 帳號與付費／付款與發票（FB_LEGACY）。
     顏色：六個大類各一色，刻意避開紅綠（紅綠在本站＝漲跌），定義在 css 的 --fbc-*。 */
  const TREE = [
    ['bug', '錯誤回報', [['data', '資料錯誤／數字不對'], ['ui', '畫面顯示異常'], ['func', '功能壞掉／按了沒反應'], ['slow', '載入慢或打不開'], ['mobile', '手機版問題']]],
    ['idea', '功能建議', [['data', '新增資料或指標'], ['chart', '新增圖表或頁面'], ['ux', '操作與介面改善'], ['watch', '自選與提醒']]],
    ['ask', '資料疑問', [['calc', '數字怎麼算'], ['source', '資料來源與更新時間'], ['term', '名詞看不懂']]],
    ['acct', '帳號與付費', [['login', '登入問題'], ['plan', '方案與價格'], ['pay', '付款與發票'], ['refund', '退款與取消']]],
    ['legal', '內容與法務', [['content', '用語或內容不當'], ['copyright', '著作權／資料授權'], ['privacy', '隱私問題']]],
    ['other', '其他', []],
  ];
  const CATS = TREE.map(([k, n]) => [k, n]);
  const SUBN = {}; TREE.forEach(([k, , subs]) => subs.forEach(([sk, sn]) => { SUBN[k + '/' + sk] = sn; }));
  const FB_LEGACY = { pay: ['acct', 'pay', '付款問題'] };
  const norm = (r) => { const lg = FB_LEGACY[r.cat]; return lg ? { ...r, cat: lg[0], sub: lg[1], legacy: r.cat } : { ...r, sub: r.sub || '' }; };

  css('supportCss', `
/* ★ admin-v3（Andy E）：半透明（背景約 80% 不透明＋毛玻璃），看得到後面的底色；深淺主題各自一組前景色 */
.supfab{position:fixed;right:20px;bottom:20px;z-index:1200;display:inline-flex;align-items:center;gap:8px;height:48px;padding:0 18px 0 12px;border-radius:999px;cursor:pointer;
  background:color-mix(in srgb,var(--cyan) 80%,transparent);-webkit-backdrop-filter:blur(10px) saturate(1.3);backdrop-filter:blur(10px) saturate(1.3);
  border:1px solid color-mix(in srgb,#fff 35%,transparent);color:var(--ontop,#04121a);font-size:14.5px;font-weight:700;box-shadow:0 10px 28px -10px rgba(0,0,0,.55);transition:transform .15s,background .15s}
.supfab:hover{transform:translateY(-1px);background:color-mix(in srgb,var(--cyan) 90%,transparent)}
.supfab svg{width:26px;height:26px}
/* ★ 2026-10-07（Andy：「客服圖示改成跟logo一樣可愛的天竺鼠」）：對話泡泡換成品牌頭像（site/brand/mark-64/128）。
   圓形裁切＋一圈白邊，深色（青底）與淺色主題下都跟按鈕底色分得開；滑過時頭像歪頭晃一下（減少動態偏好時不動）。 */
.supfab .supmark{width:34px;height:34px;flex:none;display:block;overflow:visible;transition:transform .2s;color:var(--ontop,#04121a)}
.supfab:hover .supmark{animation:supwig .5s ease-in-out;transform:scale(1.1)}
/* 只有 GIF：蓋掉上面膠囊的底色、框線、陰影與毛玻璃（拖曳／吸邊／避讓那些照舊吃 .supfab） */
.supfab.supgifonly,.supfab.supgifonly:hover{width:76px;height:76px;padding:0;gap:0;justify-content:center;background:none;border:0;box-shadow:none;-webkit-backdrop-filter:none;backdrop-filter:none;border-radius:50%}
.supfab.supgifonly .supgif{width:72px;height:72px;flex:none;display:block;pointer-events:none;filter:drop-shadow(0 4px 8px rgba(0,0,0,.35));animation:none!important;transform:none}
.supfab.supgifonly:hover .supgif{transform:scale(1.06)}
.supfab.supgifonly.supdrag{box-shadow:none}
.supfab.supgifonly:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}
@media (max-width:820px){.supfab.supgifonly,.supfab.supgifonly:hover{width:60px;height:60px}.supfab.supgifonly .supgif{width:56px;height:56px}}
.supfab .supsr{position:absolute!important;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
@keyframes supwig{0%,100%{transform:scale(1.1) rotate(0)}30%{transform:scale(1.1) rotate(-10deg)}65%{transform:scale(1.1) rotate(8deg)}}
@media (prefers-reduced-motion:reduce){.supfab:hover .supmark{animation:none}}
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
.suppanel .mailrow{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:6px}
.suppanel .mail{font-size:15px;color:var(--cyan)}
.cpmail{height:28px;padding:0 10px;border:1px solid var(--line-2);border-radius:7px;background:var(--panel-2);color:var(--ink-2);font-size:12.5px;cursor:pointer;vertical-align:middle;margin-left:6px}
.cpmail:hover{color:var(--ink)}.cpmail.ok{color:var(--fall);border-color:var(--fall)}
.suppanel .mailrow .cpmail{margin-left:0}
/* 條款內文裡的「複製信箱」是行內小鈕：不撐高行距（法律頁的目錄捲動同步依段落高度判斷，行高一變末段就亮錯節）*/
#v-legal .cpmail{height:auto;padding:0 7px;line-height:1.35;font-size:12px;vertical-align:baseline}
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
#v-subadm #fbTable td small{display:block;max-width:260px;white-space:normal;word-break:break-all;overflow-wrap:anywhere}
#v-subadm #fbTable td small a{word-break:break-all}
#v-subadm #fbTable .fbbody{min-width:220px}
#v-subadm .fbflt{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
#v-subadm .fbflt h3{margin:0;flex:1;min-width:200px}
#v-subadm .fbflt select{height:30px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:7px;padding:0 6px}
#v-subadm tr.unread td:first-child{box-shadow:inset 3px 0 0 var(--rise)}
#v-subadm .fbact{white-space:nowrap}#v-subadm .fbact button + button{margin-left:6px}
#v-subadm button.fbdel{color:var(--rise)}
.fbdot{display:inline-grid;place-items:center;min-width:18px;height:18px;padding:0 5px;margin-left:auto;border-radius:999px;background:var(--rise);color:#fff;font-size:11px;font-weight:700;line-height:1;box-sizing:border-box}
.fbdot.big{height:22px;font-size:12px;margin-left:10px;vertical-align:middle}
@media (max-width:820px){#v-subadm table,#v-subadm tbody,#v-subadm tr,#v-subadm td{display:block}#v-subadm thead{display:none}#v-subadm tr{border-bottom:1px solid var(--line-2);padding:6px 0}#v-subadm td{border:0;padding:3px 0}}
/* 1007 v2：類別色（六大類，刻意避開紅綠＝漲跌）、四張小卡、甜甜圈＋細項橫條、每日直條、篩選膠囊 */
#v-subadm,.suppanel{--fbc-bug:var(--amber);--fbc-idea:var(--cyan);--fbc-ask:var(--violet);--fbc-acct:#d873c4;--fbc-legal:#5b8cff;--fbc-other:#8a94a6}
#v-subadm .sat .rpk{margin-right:4px}
#v-subadm .fbkpi{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:12px}
#v-subadm .fbkpi .k{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 14px;display:flex;flex-direction:column;gap:2px;min-width:0}
#v-subadm .fbkpi .k span{font-size:12.5px;color:var(--ink-2)}#v-subadm .fbkpi .k b{font-size:26px;line-height:1.2}#v-subadm .fbkpi .k b.sm{font-size:17px;padding:5px 0 3px}
#v-subadm .fbkpi .k small{font-size:12px;color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-subadm .fbstat{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:14px}
#v-subadm .fbstat .card{margin-top:14px;min-width:0}#v-subadm .fbstat h3{margin:0 0 2px}#v-subadm .fbstat p.muted{margin:0 0 8px;font-size:12.5px}
#v-subadm .fbcatw{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;align-items:start}
#v-subadm .fbdon{display:flex;flex-direction:column;align-items:center;gap:8px}
#v-subadm #fbDonut{width:min(200px,100%);height:auto;overflow:visible}
#v-subadm .fbseg{cursor:pointer;stroke:var(--panel-2);stroke-width:1;transition:transform .15s}
#v-subadm .fbseg.hov,#v-subadm .fbseg.sel{transform:translate(var(--dx),var(--dy));stroke:var(--ink);stroke-width:2}
#v-subadm #fbDonut .dc1{font-size:13px;fill:var(--ink-2);text-anchor:middle}#v-subadm #fbDonut .dc2{font-size:28px;font-weight:700;fill:var(--ink);text-anchor:middle}
#v-subadm .fblgd{list-style:none;margin:0;padding:0;width:100%;font-size:13px}
#v-subadm .fblgd li{display:grid;grid-template-columns:12px 1fr auto auto;gap:6px;align-items:center;padding:3px 6px;border-radius:6px;cursor:pointer}
#v-subadm .fblgd li:hover,#v-subadm .fblgd li.sel{background:var(--panel-3)}
#v-subadm .fblgd i{width:10px;height:10px;border-radius:3px}#v-subadm .fblgd em{font-style:normal;color:var(--ink-2);min-width:44px;text-align:right}
#v-subadm .fbsubc{min-width:0}#v-subadm .fbsubc h4{margin:0 0 6px;font-size:13px;color:var(--ink-2);font-weight:500}
#v-subadm .fbhb{display:flex;flex-direction:column;gap:6px}
#v-subadm .fbhb .hb{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 8px;background:none;border:1px solid transparent;border-radius:8px;padding:4px 6px;color:var(--ink);font-size:13px;text-align:left;cursor:pointer;height:auto}
#v-subadm .fbhb .hb:hover{background:var(--panel-3)}#v-subadm .fbhb .hb.sel{border-color:var(--ink-2);background:var(--panel-3)}
#v-subadm .fbhb .hv{text-align:right;color:var(--ink-2);font-size:12.5px;white-space:nowrap}
#v-subadm .fbhb .tr{grid-column:1 / -1;height:10px;background:var(--panel-3);border-radius:3px;overflow:hidden}#v-subadm .fbhb .tr i{display:block;height:100%;border-radius:0 3px 3px 0}
#v-subadm .fbvb .plot{position:relative;display:flex;align-items:stretch;height:170px;padding-top:16px;border-bottom:1px solid var(--line)}
#v-subadm .fbvb .vb{flex:1;min-width:0;display:flex;background:none;border:0;padding:0;height:auto;cursor:pointer;border-right:1px solid color-mix(in srgb,var(--line) 45%,transparent)}
#v-subadm .fbvb .col{flex:1;position:relative;display:flex;align-items:flex-end;justify-content:center}
#v-subadm .fbvb .col i{display:block;width:min(12px,80%);min-height:1px;border-radius:3px 3px 0 0;background:linear-gradient(180deg,var(--cyan),color-mix(in srgb,var(--cyan) 45%,transparent))}
#v-subadm .fbvb .vb:hover .col i{filter:brightness(1.25);outline:2px solid var(--ink-2)}
#v-subadm .fbvb .vb.sel .col i{background:linear-gradient(180deg,var(--amber),color-mix(in srgb,var(--amber) 45%,transparent))}
#v-subadm .fbvb .col i{position:relative}#v-subadm .fbvb .col em{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);font-style:normal;font-size:11.5px;color:var(--ink);white-space:nowrap}
#v-subadm .fbvb .avgl{position:absolute;left:0;right:0;border-top:1px dashed var(--ink-2);opacity:.6;pointer-events:none}
#v-subadm .fbvb .xl{display:flex}#v-subadm .fbvb .xl span{flex:1;min-width:0;font-size:11px;color:var(--ink-2);white-space:nowrap;overflow:visible;height:18px;line-height:18px}
#v-subadm .fbempty{padding:28px 0;text-align:center;color:var(--ink-2);font-size:13px}
#v-subadm .fbcat,#v-subadm .fbsub{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;margin:0 4px 3px 0;white-space:nowrap}
#v-subadm .fbcat{background:var(--fbc-bug);color:#10141c;font-weight:700}
#v-subadm .fbcat[data-c="idea"]{background:var(--fbc-idea)}#v-subadm .fbcat[data-c="ask"]{background:var(--fbc-ask)}#v-subadm .fbcat[data-c="acct"]{background:var(--fbc-acct)}#v-subadm .fbcat[data-c="legal"]{background:var(--fbc-legal)}#v-subadm .fbcat[data-c="other"]{background:var(--fbc-other)}
#v-subadm .fbsub{border:1px solid var(--fbc-bug);color:var(--ink)}
#v-subadm .fbsub[data-c="idea"]{border-color:var(--fbc-idea)}#v-subadm .fbsub[data-c="ask"]{border-color:var(--fbc-ask)}#v-subadm .fbsub[data-c="acct"]{border-color:var(--fbc-acct)}#v-subadm .fbsub[data-c="legal"]{border-color:var(--fbc-legal)}
#v-subadm .fblg{display:block}
#v-subadm .fbchip{display:inline-flex;align-items:center;gap:4px;height:26px;padding:0 4px 0 10px;border-radius:999px;background:color-mix(in srgb,var(--amber) 22%,transparent);border:1px solid var(--amber);font-size:12.5px}
#v-subadm .fbchip button{height:22px;width:22px;padding:0;border:0;background:none;color:var(--ink);font-size:15px;cursor:pointer}
@media (max-width:1100px){#v-subadm .fbstat{grid-template-columns:minmax(0,1fr)}}
@media (max-width:820px){#v-subadm .fbkpi{grid-template-columns:repeat(2,minmax(0,1fr))}#v-subadm .fbcatw{grid-template-columns:minmax(0,1fr)}#v-subadm .fbvb .plot{height:140px}}
/* 2026-10-08：底部導覽已經拿掉 → 手機與平板（≤820）一律貼右下角＋安全區，52px 圓鈕只放泡泡（不放字），面板開在它正上方 */
@media (max-width:820px){.supfab{bottom:calc(16px + env(safe-area-inset-bottom));right:16px;width:52px;height:52px;padding:0;justify-content:center}.supfab span{display:none}.suppanel{right:12px;bottom:calc(76px + env(safe-area-inset-bottom))}}
/* 2026-10-09（Andy：「客服功能可拖曳，他擋到按鈕了」）：可拖曳＋自動避讓。
   這幾條都不改初始畫面：沒拖過＝沒有任何行內位置，照舊貼右下角（桌機守門 0 差異）。
   touch-action:none 只在手指按在鈕上時生效（拖的時候頁面不跟著捲）；拖曳中關掉過場，手指到哪鈕到哪。
   避讓（supaway）：抽屜／彈窗／底部固定列蓋到鈕的位置時整顆藏起來（不能點、不佔畫面），收起後回原位。 */
.supfab{touch-action:none;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
.supfab.supdrag{transition:none;cursor:grabbing;box-shadow:0 16px 36px -10px rgba(0,0,0,.7)}
.supfab.supdrag:hover{transform:none}
.supfab.supsnap{transition:left .18s ease-out,right .18s ease-out,top .18s ease-out,transform .15s,background .15s}
.supfab.supaway{visibility:hidden;opacity:0;pointer-events:none}
/* 願望清單（2026-10-09）：面板裡「意見回饋｜願望清單」分段控制器；管理頁同款的「全部｜意見回饋｜願望清單」 */
.fbkind{display:flex;gap:0;margin:0 0 10px;border:1px solid var(--line-2);border-radius:10px;overflow:hidden;background:var(--panel)}
.fbkind button{flex:1;min-height:36px;border:0;background:none;color:var(--ink-2);font:inherit;font-size:13.5px;cursor:pointer;padding:6px 10px;display:inline-flex;align-items:center;justify-content:center;gap:6px}
.fbkind button+button{border-left:1px solid var(--line-2)}
.fbkind button.on{background:color-mix(in srgb,var(--cyan) 22%,transparent);color:var(--ink);font-weight:700}
.fbkind button small{font-size:12px;color:var(--ink-3);font-weight:400}
.fbkind.adm{max-width:420px}
.suppanel textarea.sm{min-height:64px}
#v-subadm .fbcat.fbwish{background:color-mix(in srgb,var(--violet) 25%,transparent);color:var(--ink)}
/* 手機（html.m4）：mobile4.css 給 main 裡每顆按鈕 min-width:40px，管理頁每日直條 30 根 × 40px 撐出 818px 橫向捲軸 —— 直條是圖不是按鈕列，放回 0 */
:root.m4 #v-subadm .fbvb .vb{min-width:0!important}
#v-subadm select.wsst{font:inherit;font-size:13px;min-height:32px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px}
/* 帳號選單關掉客服（html.fab-off，claude/acct-menu）：只藏浮動鈕；面板保留，帳號選單「意見回饋」照樣打得開（Andy 10-09「新增一個 客服 關／開 功能」） */
html.fab-off .supfab{display:none!important}`);

  /* ★ admin-v3（Andy E）：圖示改可愛一點 —— 圓角對話泡泡裡一張笑臉（自繪 SVG，stroke＝currentColor，深淺主題都跟字色走）*/
  const ICON = '<svg viewBox="0 0 28 28" fill="none" aria-hidden="true"><path d="M6.5 4.5h15a4 4 0 0 1 4 4v8.5a4 4 0 0 1-4 4h-7.2l-5.1 4.1c-.5.4-1.2 0-1.2-.6v-3.5H6.5a4 4 0 0 1-4-4V8.5a4 4 0 0 1 4-4z" fill="currentColor" fill-opacity=".14" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>'
    + '<circle cx="10.2" cy="11.4" r="1.45" fill="currentColor"/><circle cx="17.8" cy="11.4" r="1.45" fill="currentColor"/>'
    + '<path d="M9.8 15.1c1.1 1.5 2.5 2.2 4.2 2.2s3.1-.7 4.2-2.2" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>'
    + '<circle cx="7.6" cy="14.6" r="1.1" fill="#ff8fa3" fill-opacity=".75"/><circle cx="20.4" cy="14.6" r="1.1" fill="#ff8fa3" fill-opacity=".75"/></svg>';
  // 2026-10-07：浮動鈕改用品牌天竺鼠頭像（上面的 ICON 目前沒人用，留著當退路）
  /* 2026-10-08（Andy：「右下角的客服需要再優化，並且改成原本的 LOGO 樣式，但是表情是天竺鼠」）：
     外形回到原本 ICON 的對話泡泡（同一條路徑），泡泡裡面的笑臉換成天竺鼠頭像（brand/mark-128，裁進泡泡的圓角框裡）。 */
  /* ★ 2026-10-09（Andy：「客服圖示換成這個GIF圖動畫」「客服圖案就直接只有GIF圖」「並且會持續動作」）：
     按鈕只剩天竺鼠動畫本身 —— 沒有青色膠囊底、沒有「客服」字（字留給讀屏，.supsr 視覺隱藏）、不管減少動態偏好一律一直動。
     原檔 site/brand/src/support_anim_1009.gif（512×512・8 格・每格 100ms）→ 裁到身體、米色背景去掉成透明、128px（2 倍螢幕）。*/
  const MARK = '<img class="supmark supgif" src="brand/sup-anim-128.gif" width="64" height="64" alt="" aria-hidden="true" draggable="false">';
  let tab = 'faq', fbKind = 'fb';
  const WISH_TAG = '【願望清單】';
  const isWish = (r) => r.type === 'wish' || String(r.body || '').startsWith(WISH_TAG);
  /* 願望的狀態：新／評估中／已做／不做（Worker 要支援 eval／done／no 才存得住；舊 Worker 只認 new／handled，見 sendWishSt） */
  const WST = [['new', '新'], ['eval', '評估中'], ['done', '已做'], ['no', '不做']];
  const WSTN = Object.fromEntries(WST);
  const wstOver = {};   // 舊 Worker 不收 eval／done／no 時，這次瀏覽先記在記憶體（重新整理就沒了）
  function ensure() {
    let fab = document.getElementById('supFab');
    if (fab) return;
    fab = document.createElement('button'); fab.type = 'button'; fab.id = 'supFab'; fab.className = 'supfab';
    fab.setAttribute('aria-haspopup', 'dialog'); fab.setAttribute('aria-expanded', 'false');
    fab.innerHTML = MARK + '<span class="supsr">客服</span>'; fab.classList.add('supgifonly'); fab.setAttribute('aria-label', '客服'); fab.title = '客服';
    document.body.appendChild(fab);
    const p = document.createElement('div'); p.id = 'supPanel'; p.className = 'suppanel'; p.hidden = true; p.setAttribute('role', 'dialog'); p.setAttribute('aria-label', '客服與意見反饋');
    document.body.appendChild(p);
    fab.onclick = () => toggle();
    wireDrag(fab);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !p.hidden) toggle(false); });
    /* 2026-10-08 Andy：「客服功能點擊後 點其他地方會自動收回」→ 點面板與浮動鈕以外的地方就收起
       （用 composedPath：面板內重畫後 target 可能已脫離 DOM，contains 會誤判成「外面」）*/
    document.addEventListener('pointerdown', (e) => {
      if (p.hidden) return;
      const path = e.composedPath ? e.composedPath() : [];
      if (path.includes(p) || path.includes(fab)) return;
      toggle(false);
    }, true);
  }
  function toggle(want) {
    const p = document.getElementById('supPanel'), fab = document.getElementById('supFab');
    const open = want == null ? p.hidden : want;
    p.hidden = !open; fab.setAttribute('aria-expanded', String(open));
    if (open) { paint(); placePanel(); }
  }

  /* ======================================================================
     客服鈕：拖曳＋吸邊＋記住位置＋自動避讓（2026-10-09，Andy：「客服功能可拖曳，他擋到按鈕了」）
     ----------------------------------------------------------------------
     · 手機（html.m4／≤640）與網頁版都能拖；預設位置不變（右下角），沒拖過就不寫任何行內樣式。
     · 放開後吸到最近的左緣或右緣，上下位置保留；範圍夾在視窗內、不壓頂欄（header.topbar）。
     · 位置記在 localStorage（手機、網頁各一個鍵；tw.layout4. 前綴＝外觀偏好，重新整理保留，見 viewreset.js）。
     · 位移 < 6px 才算點擊（打開客服）；超過就是拖曳，那一下的 click 整個吞掉（連 account.js 的點擊統計都不算）。
     · 位置用行內 left/right/top 加 !important：mobile4.css 對 .supfab 的 right/bottom 有 !important，一般行內樣式蓋不過。
     ====================================================================== */
  const DRAG_PX = 6;
  const isMob = () => document.documentElement.classList.contains('m4') || window.innerWidth <= 640;
  const posKey = () => (isMob() ? 'tw.layout4.supfab.m' : 'tw.layout4.supfab.d');
  const edge = () => (window.innerWidth <= 820 ? 16 : 20);   // 跟 CSS 的預設右距同一個數字
  function loadPos() { try { const v = JSON.parse(localStorage.getItem(posKey()) || 'null'); return v && (v.s === 'L' || v.s === 'R') && isFinite(v.t) ? v : null; } catch (e) { return null; } }
  function savePos(v) { try { localStorage.setItem(posKey(), JSON.stringify(v)); } catch (e) { /* 私密視窗：這次瀏覽有效，下次回右下角 */ } }
  function topLimit() {
    const tb = document.querySelector('header.topbar');
    let lim = 8;
    if (tb && tb.getClientRects().length) {
      const cs = getComputedStyle(tb), r = tb.getBoundingClientRect();
      if ((cs.position === 'fixed' || cs.position === 'sticky') && r.bottom > 0) lim = Math.max(lim, r.bottom + 8);
    }
    return lim;
  }
  function clampTop(t, h) { const lo = topLimit(), hi = window.innerHeight - h - edge(); return Math.round(Math.max(lo, Math.min(hi, t))); }
  /* side：'L' 用 left、'R' 用 right、'' 拖曳中一律用 left */
  function setXY(fab, side, x, top) {
    const st = fab.style;
    if (side === 'R') { st.setProperty('right', x + 'px', 'important'); st.setProperty('left', 'auto', 'important'); }
    else { st.setProperty('left', x + 'px', 'important'); st.setProperty('right', 'auto', 'important'); }
    st.setProperty('top', top + 'px', 'important'); st.setProperty('bottom', 'auto', 'important');
  }
  function clearXY(fab) { ['left', 'right', 'top', 'bottom'].forEach((k) => fab.style.removeProperty(k)); }
  /** 依存好的位置擺（沒存＝清掉行內樣式，回 CSS 的右下角） */
  function applyPos() {
    const fab = document.getElementById('supFab'); if (!fab) return;
    const v = loadPos();
    if (!v) { clearXY(fab); delete fab.dataset.side; placePanel(); return; }
    setXY(fab, v.s, edge(), clampTop(v.t, fab.offsetHeight || 52));
    fab.dataset.side = v.s;
    placePanel();
  }
  /** 鈕被拖走時，面板跟著開在鈕旁邊（左邊就靠左；鈕在上半部就往下開）。沒拖過＝照 CSS 原位。 */
  function placePanel() {
    const p = document.getElementById('supPanel'), fab = document.getElementById('supFab');
    if (!p || !fab) return;
    const pst = p.style;
    ['left', 'right', 'top', 'bottom', 'max-height'].forEach((k) => pst.removeProperty(k));
    if (!fab.dataset.side || p.hidden) return;
    const r = fab.getBoundingClientRect(), vh = window.innerHeight, m = window.innerWidth <= 820 ? 12 : 20;
    if (fab.dataset.side === 'L') { pst.setProperty('left', m + 'px', 'important'); pst.setProperty('right', 'auto', 'important'); }
    else { pst.setProperty('right', m + 'px', 'important'); pst.setProperty('left', 'auto', 'important'); }
    if (r.top + r.height / 2 > vh / 2) {
      pst.setProperty('bottom', Math.round(vh - r.top + 10) + 'px', 'important'); pst.setProperty('top', 'auto', 'important');
      pst.setProperty('max-height', Math.round(Math.min(640, r.top - topLimit() - 10)) + 'px', 'important');
    } else {
      pst.setProperty('top', Math.round(r.bottom + 10) + 'px', 'important'); pst.setProperty('bottom', 'auto', 'important');
      pst.setProperty('max-height', Math.round(Math.min(640, vh - r.bottom - 20)) + 'px', 'important');
    }
  }
  function wireDrag(fab) {
    let st = null;   // { id, x0, y0, l0, t0, drag }
    fab.addEventListener('pointerdown', (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      const r = fab.getBoundingClientRect();
      st = { id: e.pointerId, x0: e.clientX, y0: e.clientY, l0: r.left, t0: r.top, drag: false };
      /* 一按下就抓住指標：滑鼠拖得快時第一步就離開鈕了，沒抓住的話 move 事件會跑到底下的元素去 */
      try { fab.setPointerCapture(e.pointerId); } catch (er) { /* 沒有 capture：照樣用 move 事件 */ }
    });
    fab.addEventListener('pointermove', (e) => {
      if (!st || e.pointerId !== st.id) return;
      const dx = e.clientX - st.x0, dy = e.clientY - st.y0;
      if (!st.drag) {
        if (Math.hypot(dx, dy) < DRAG_PX) return;
        st.drag = true;
        fab.classList.remove('supsnap', 'supaway'); fab.classList.add('supdrag');
        const p = document.getElementById('supPanel'); if (p && !p.hidden) toggle(false);
      }
      e.preventDefault();
      const w = fab.offsetWidth, h = fab.offsetHeight, m = edge();
      const l = Math.round(Math.max(m, Math.min(window.innerWidth - w - m, st.l0 + dx)));
      setXY(fab, '', l, clampTop(st.t0 + dy, h));
    });
    const end = (e) => {
      if (!st || e.pointerId !== st.id) return;
      const was = st; st = null;
      try { fab.releasePointerCapture(e.pointerId); } catch (er) { /* 沒拿過 capture */ }
      if (!was.drag) return;   // 小位移：交給原生 click 打開客服
      fab.classList.remove('supdrag');
      const r = fab.getBoundingClientRect();
      const side = (r.left + r.width / 2) < window.innerWidth / 2 ? 'L' : 'R';
      const v = { s: side, t: clampTop(r.top, r.height) };
      savePos(v);
      /* 先把位置換成同一側的距離（畫面不動），再換成吸邊的數字，過場才會從手放開的地方滑過去 */
      setXY(fab, side, side === 'L' ? Math.round(r.left) : Math.round(window.innerWidth - r.right), v.t);
      void fab.offsetWidth;
      fab.classList.add('supsnap');
      setXY(fab, side, edge(), v.t);
      fab.dataset.side = side;
      setTimeout(() => { fab.classList.remove('supsnap'); checkAway(); }, 260);
      /* 拖曳放開後的那一下 click（滑鼠在鈕上放開會觸發）整個吞掉：不開客服、不記點擊統計 */
      const eat = (ev) => { const t = ev.target; if (t && t.closest && t.closest('#supFab')) { ev.stopImmediatePropagation(); ev.preventDefault(); } };
      window.addEventListener('click', eat, true);
      setTimeout(() => window.removeEventListener('click', eat, true), 400);
    };
    fab.addEventListener('pointerup', end);
    fab.addEventListener('pointercancel', end);
    applyPos();
    let rz = 0;
    window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { applyPos(); checkAway(); }, 120); });
    startAway();
  }

  /* ---- 自動避讓：一套通用偵測，不替每個抽屜各寫一套 ----
     客服鈕現在的位置「被蓋到」的兩種情形（任一成立就整顆藏起來；都不成立就回來）：
       ① role="dialog"／aria-modal／.msheet 的框跟鈕重疊（底部抽屜 #mSheet、帳號／訂閱／報價彈窗、通知、自選、登入提示…）
       ② 鈕底下（取 5 個點）有 position:fixed、或 sticky 且貼底（bottom 不是 auto）的元素，而且不是整個視窗高的
          （排除全螢幕遮罩、桌機側欄、頂欄）—— 升級卡、底部固定列（例如管理區「儲存」列）、吐司走這條
     為什麼選「藏」不選「往上挪」：底部抽屜打開時，剖析圖會把選到的編號捲到抽屜正上方（diagrams.js openNo），
     往上挪剛好又蓋在那顆編號上；藏起來保證什麼都不擋，抽屜收起就回原位。客服自己的面板不算障礙。 */
  /* 帳號選單的「客服 開／關」（claude/acct-menu 負責，存 tw.fab.off）：關掉時 <html> 帶 fab-off。
     這裡只負責相容：fab-off 時鈕與面板不顯示（CSS），避讓的觀察器整個斷開（省效能），class 拿掉就接回來、重新擺位。 */
  const fabOff = () => document.documentElement.classList.contains('fab-off');
  let awayTimer = 0, awayMo = null;
  const kick = () => { if (awayTimer || fabOff()) return; awayTimer = setTimeout(() => { awayTimer = 0; checkAway(); }, 90); };
  function awayOn() {
    if (awayMo || fabOff()) return;
    try {
      awayMo = new MutationObserver(kick);
      awayMo.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden', 'class', 'open', 'aria-hidden', 'aria-modal'] });
    } catch (e) { awayMo = null; /* 沒有 MutationObserver：只靠捲動與縮放觸發 */ }
    kick();
  }
  function awayOff() { if (awayMo) { awayMo.disconnect(); awayMo = null; } clearTimeout(awayTimer); awayTimer = 0; }
  function startAway() {
    window.addEventListener('scroll', kick, { passive: true, capture: true });
    let was = fabOff();
    try {
      new MutationObserver(() => {
        const off = fabOff(); if (off === was) return; was = off;
        if (off) { awayOff(); const p = document.getElementById('supPanel'); if (p && !p.hidden) toggle(false); }
        else { applyPos(); awayOn(); }
      }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    } catch (e) { /* 舊瀏覽器：開關要重新整理才生效 */ }
    awayOn();
  }
  function shown(el) {
    if (!el || !el.isConnected || el.hidden || el.closest('[hidden]')) return false;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false;
    const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0;
  }
  const overlap = (a, b, pad) => a.left - pad < b.right && b.left < a.right + pad && a.top - pad < b.bottom && b.top < a.bottom + pad;
  function blockers(fab) {
    const p = document.getElementById('supPanel');
    /* 新手導覽（#twTour）有一步就是指著客服鈕介紹它：導覽的遮罩與卡片不算障礙 */
    const mine = (el) => el === fab || fab.contains(el) || (p && (el === p || p.contains(el))) || !!(el.closest && el.closest('#twTour'));
    const fr = fab.getBoundingClientRect(), out = [];
    document.querySelectorAll('[role="dialog"], [aria-modal="true"], .msheet').forEach((d) => { if (!mine(d) && out.indexOf(d) < 0 && shown(d) && overlap(d.getBoundingClientRect(), fr, 2)) out.push(d); });
    if (out.length || !fr.width) return out;
    const vh = window.innerHeight, pts = [[0.5, 0.5], [0.15, 0.15], [0.85, 0.15], [0.15, 0.85], [0.85, 0.85]];
    for (const [ax, ay] of pts) {
      for (const el of document.elementsFromPoint(fr.left + fr.width * ax, fr.top + fr.height * ay)) {
        if (el === document.body || el === document.documentElement || mine(el)) continue;
        for (let a = el, n = 0; a && a !== document.body && n < 14; a = a.parentElement, n++) {
          const cs = getComputedStyle(a);
          if (cs.position !== 'fixed' && !(cs.position === 'sticky' && cs.bottom !== 'auto')) continue;
          if (!mine(a) && a.getBoundingClientRect().height < vh * 0.85 && !a.matches('header.topbar') && out.indexOf(a) < 0) out.push(a);
          break;
        }
      }
    }
    return out;
  }
  function checkAway() {
    const fab = document.getElementById('supFab'); if (!fab || fab.hidden || fabOff() || fab.classList.contains('supdrag')) return;
    const p = document.getElementById('supPanel');
    /* 鈕藏起來是 visibility:hidden：框還在原位，elementsFromPoint 也不會回傳它自己 → 可以照樣量「原位被不被蓋」 */
    const b = (p && !p.hidden) ? [] : blockers(fab);
    const away = b.length > 0;
    if (away === fab.classList.contains('supaway')) return;
    fab.classList.toggle('supaway', away);
    if (away) { fab.dataset.away = b.map((x) => x.id || (typeof x.className === 'string' ? x.className : '') || x.tagName).join('|').slice(0, 80); fab.setAttribute('aria-hidden', 'true'); fab.tabIndex = -1; }
    else { delete fab.dataset.away; fab.removeAttribute('aria-hidden'); fab.removeAttribute('tabindex'); }
  }
  window.TwSupFab = { applyPos, checkAway, placePanel, observing: () => !!awayMo };
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
    const ks = p.querySelector('#fbKind'); if (ks) ks.onclick = (e) => { const b = e.target.closest('button[data-fk]'); if (b && b.dataset.fk !== fbKind) { fbKind = b.dataset.fk; paint(); } };
    const cs = p.querySelector('#fbCat');
    if (cs) cs.onchange = () => { const w = p.querySelector('#fbSubWrap'), o = subOpts(cs.value); p.querySelector('#fbSub').innerHTML = o; w.hidden = !o.includes('value="') || cs.value === 'other'; };
  }
  function subOpts(cat) {
    const t = TREE.find((x) => x[0] === cat); if (!t || !t[2].length) return '<option value="">（無細項）</option>';
    return '<option value="">（不選）</option>' + t[2].map(([k, n]) => `<option value="${k}">${n}</option>`).join('');
  }
  function body() {
    // 「即時和盤後差在哪」那一題只給管理者看（data-live-ui，livegate.js 的 CSS 藏；DECISIONS #326）
    if (tab === 'faq') return FAQ.map(([q, a], i) => `<div class="faq" data-i="${i}"${/「即時」/.test(q) ? ' data-live-ui' : ''}><button type="button" aria-expanded="false">${esc(q)}</button><div class="ans">${esc(a)}</div></div>`).join('')
      + `<p class="note">找不到答案？到「意見反饋」留言，或看 <a href="#pricing">訂閱方案</a>。</p>`;
    if (tab === 'mail') return `<p class="note">寄信給客服（一般 1～2 個工作天內回覆）：</p><div class="mailrow"><a class="mail" id="supMail" data-gmail href="${esc(gmail(SUPPORT_EMAIL, '哩股哩股－客服'))}" target="_blank" rel="noopener">用 Gmail 寄信給 ${SUPPORT_EMAIL}</a><button type="button" class="cpmail" id="supCopy" data-copymail="${SUPPORT_EMAIL}">複製信箱</button></div>
      <p class="note">不用 Gmail 的話，按「複製信箱」再貼到你慣用的郵件程式。</p>
      <p class="note">付款或方案問題請在信裡註明你登入用的 email。本網站不是證券投資顧問，無法回答個股買賣問題。</p>`;
    const A = window.TwAccount, u = A && A.on() ? A.user() : null;
    /* 1007：訪客也能送（Worker 端每 IP 每小時上限）；送出只存本站伺服器，不寄任何信。
       只有會員伺服器沒設定（TwSub.call 根本沒有網址）時才關掉。*/
    const can = !!(A && A.on());
    /* 2026-10-09（Andy：「再新增一個願望清單，所以我意見回饋需要多一個功能：願望清單」）：
       分段控制器切「意見回饋｜願望清單」。願望清單＝想要的新功能（必填）＋為什麼需要（選填）＋聯絡方式（選填，會員自動帶入），
       送出走同一條 /v1/feedback（type='wish'），只存本站伺服器。*/
    const seg = `<div class="fbkind" id="fbKind" role="tablist" aria-label="反饋種類">${[['fb', '意見回饋'], ['wish', '願望清單']].map(([k, n]) => `<button type="button" role="tab" data-fk="${k}" class="${fbKind === k ? 'on' : ''}" aria-selected="${fbKind === k}">${n}</button>`).join('')}</div>`;
    const off = can ? '' : '<p class="note" style="color:var(--amber)">線上反饋暫時無法使用，請改用「寄信」。</p>';
    if (fbKind === 'wish') return `${seg}${off}
      <p class="note">想要網站多一個什麼功能？寫下來，我們會逐則評估，做了會在公告裡說。</p>
      <label for="wsWant">想要的功能（必填）</label><textarea id="wsWant" maxlength="600" placeholder="例如：自選股可以設價格提醒、族群頁加上本益比排行…"></textarea>
      <label for="wsWhy">為什麼需要（選填）</label><textarea id="wsWhy" class="sm" maxlength="1000" placeholder="你平常怎麼用、現在卡在哪裡"></textarea>
      <label for="fbMail">聯絡方式 email（選填，做好時通知你）</label><input type="email" id="fbMail" maxlength="200" value="${esc(u && u.email || '')}" autocomplete="email">
      <button type="button" class="go" id="fbSend" ${can ? '' : 'disabled'}>送出願望</button>
      <div class="msg" id="fbMsg" role="status"></div>
      <p class="note">願望只存在本站伺服器（保存 13 個月，刪除帳號時一併刪除），不會提供給第三方。</p>`;
    return `${seg}${off}
      <label for="fbCat">類別（先選大類）</label><select id="fbCat">${CATS.map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}</select>
      <div id="fbSubWrap"><label for="fbSub">細項（可不選）</label><select id="fbSub">${subOpts('bug')}</select></div>
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
    if (fbKind === 'wish') return sendWish(p, msg, btn);
    const text = p.querySelector('#fbBody').value.trim(), contact = p.querySelector('#fbMail').value.trim();
    if (text.length < 2) { msg.className = 'msg bad'; msg.textContent = '請先寫一點內容'; return; }
    if (contact && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)) { msg.className = 'msg bad'; msg.textContent = 'email 格式不對（不想留可以空白）'; return; }
    const ctx = p.querySelector('#fbCtx').checked;
    const body = { cat: p.querySelector('#fbCat').value, body: text };
    const sb = p.querySelector('#fbSub'); if (sb && sb.value && body.cat !== 'other') body.sub = sb.value;
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

  /* 願望清單送出：type='wish'。cat 固定 'idea'（功能建議），內文前面加「【願望清單】」——
     現行 Worker 還沒有 type 欄位時，管理頁靠這個前綴認出願望（Worker 補上 type 欄之後兩種都認）。*/
  async function sendWish(p, msg, btn) {
    const want = p.querySelector('#wsWant').value.trim(), why = p.querySelector('#wsWhy').value.trim(), contact = p.querySelector('#fbMail').value.trim();
    if (want.length < 2) { msg.className = 'msg bad'; msg.textContent = '請先寫下想要的功能'; return; }
    if (contact && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)) { msg.className = 'msg bad'; msg.textContent = 'email 格式不對（不想留可以空白）'; return; }
    const body = { type: 'wish', cat: 'idea', body: (WISH_TAG + want + (why ? '\n為什麼需要：' + why : '')).slice(0, 2000), url: location.href.slice(0, 300) };
    if (contact) body.contact = contact;
    btn.disabled = true; msg.className = 'msg'; msg.textContent = '送出中…';
    const j = await call('/v1/feedback', body);
    btn.disabled = false;
    if (j && j._s === 200 && j.ok) {
      p.querySelector('#wsWant').value = ''; p.querySelector('#wsWhy').value = '';
      msg.className = 'msg ok'; msg.textContent = '願望收到了，謝謝你！' + (contact ? '做好會通知 ' + contact : '');
    } else {
      msg.className = 'msg bad';
      msg.textContent = j && j._s === 429 ? '今天送出太多次了，請改用寄信' : '送出失敗，請稍後再試，或改用「寄信」';
    }
  }

  // ------------------------------------------------------------------ 管理端 #admin/feedback
  const CATN = Object.fromEntries(CATS);
  const dstr = (ms) => { const d = new Date(ms + 8 * 3600 * 1000); return d.toISOString().slice(0, 16).replace('T', ' '); };
  const dayOf = (ms) => dstr(ms).slice(0, 10);
  const todayTpe = () => dayOf(Date.now());
  const shiftDay = (d, n) => new Date(Date.parse(d + 'T00:00:00Z') + n * 86400000).toISOString().slice(0, 10);
  /* 1007 v2：
     · 期間（RG）：今天／近 7／30／90 天／自訂起訖，共用 site/rangepick.js（流量觀測、ETF 同一支）。列表、四張小卡、甜甜圈、每日直條都只算期間內。
     · 篩選（FL）：大類 cat、小類 sub、狀態 st、某一天 day。點甜甜圈扇區＝設 cat；點右邊橫條＝設 cat＋sub；點直條＝設 day。
       一律能取消：再點同一塊、列表標題旁膠囊的 ×、或下拉選「全部」。
     · 篩選只在前端做（Worker 一次給最近 2000 筆），記在記憶體，重新整理回預設（近 30 天、不篩）。
     未讀數紅點：側欄「意見反饋」子項與帳號選單共用 unread（不受期間影響，算全部未讀）。*/
  /* kind：''＝全部、'fb'＝只看意見回饋、'wish'＝只看願望清單（2026-10-09 願望清單）*/
  const FL = { cat: '', sub: '', st: '', day: '', kind: '' };
  const stOf = (r) => wstOver[r.id] || r.status;
  /* 2026-10-09（帳本 48）訂閱申請多了「取消訂閱」「申請退款」兩種（Worker sub_requests.type）：申請列表可篩選類型 */
  const RQT = { subscribe: '訂閱', cancel: '取消訂閱', refund: '申請退款' };
  let RQF = '';
  const RG = { v: '30', from: '', to: '' };
  let unread = 0, last = null;
  function rangeNow() {
    const t = todayTpe();
    if (RG.v === 'custom') return { from: RG.from || shiftDay(t, -29), to: RG.to || t };
    if (RG.v === 'today') return { from: t, to: t };
    return { from: shiftDay(t, -(+RG.v - 1)), to: t };
  }
  function paintDot() {
    const t = document.getElementById('admTabFeedback'); if (!t) return;
    let d = t.querySelector('.fbdot');
    if (!unread) { if (d) d.remove(); return; }
    if (!d) { d = document.createElement('span'); d.className = 'fbdot'; t.appendChild(d); }
    d.textContent = unread > 99 ? '99+' : String(unread); d.title = unread + ' 則未讀反饋';
  }
  async function refreshUnread() {
    const A = window.TwAccount, u = A && A.on() ? A.user() : null;
    if (!u || !u.admin) { unread = 0; paintDot(); return; }
    const j = await call('/v1/admin/feedback/list', {});
    if (j && j._s === 200) { last = j; unread = (j.feedback || []).filter((x) => x.status === 'new').length; paintDot(); }
  }
  async function renderFeedbackAdmin(el) {
    const A = window.TwAccount, u = A && A.on() ? A.user() : null;
    if (!u || !u.admin) { el.innerHTML = '<div class="card" id="fbDenied"><h2>管理頁</h2><p class="muted">這一頁只有管理者看得到' + (u ? '' : '，請先登入') + '。</p></div>'; return; }
    el.innerHTML = '<div class="card"><p class="muted">載入中…</p></div>';
    const j = await call('/v1/admin/feedback/list', {});
    if (!j || j._s !== 200) { el.innerHTML = '<div class="card"><p class="muted">讀取失敗（' + esc(j ? j._s : '連不到') + '）</p></div>'; return; }
    last = j; paintAdmin(el);
  }
  const pct = (a, b) => (b ? Math.round(a / b * 1000) / 10 : 0);
  const catBadge = (r) => `<span class="fbcat" data-c="${esc(r.cat)}">${esc(CATN[r.cat] || r.cat)}</span>${r.sub ? `<span class="fbsub" data-c="${esc(r.cat)}">${esc(SUBN[r.cat + '/' + r.sub] || r.sub)}</span>` : ''}${r.legacy ? `<small class="muted fblg" title="改版前送出的類別，已對應到新大類">（舊類別：${esc((FB_LEGACY[r.legacy] || [])[2] || r.legacy)}）</small>` : ''}`;
  /* A 款甜甜圈（自繪 SVG，類別色是 CSS 變數，深淺主題自動跟）：內徑 68%、外徑 92%、扇區間細縫；
     滑過外凸 4px＋外框＋中心字換成該類名稱與 %；點擊＝篩選該大類（再點取消）*/
  function donut(rows) {
    const tot = rows.length;
    if (!tot) return '<div class="fbempty">這段期間沒有反饋</div>';
    const cnt = CATS.map(([k, n]) => ({ k, n, v: rows.filter((r) => r.cat === k).length })).filter((x) => x.v);
    const R = 92, r0 = 68, cx = 100, cy = 100, gap = cnt.length > 1 ? 0.012 : 0;
    let a = -Math.PI / 2;
    const P = (ang, rr) => `${(cx + rr * Math.cos(ang)).toFixed(2)} ${(cy + rr * Math.sin(ang)).toFixed(2)}`;
    const segs = cnt.map((x) => {
      const sw = x.v / tot * Math.PI * 2, a0 = a + gap, a1 = a + sw - gap, mid = a + sw / 2; a += sw;
      const big = a1 - a0 > Math.PI ? 1 : 0;
      const d = cnt.length === 1 ? `M ${P(-Math.PI / 2, R)} A ${R} ${R} 0 1 1 ${P(Math.PI * 1.5 - 0.0001, R)} L ${P(Math.PI * 1.5 - 0.0001, r0)} A ${r0} ${r0} 0 1 0 ${P(-Math.PI / 2, r0)} Z`
        : `M ${P(a0, R)} A ${R} ${R} 0 ${big} 1 ${P(a1, R)} L ${P(a1, r0)} A ${r0} ${r0} 0 ${big} 0 ${P(a0, r0)} Z`;
      const dx = (4 * Math.cos(mid)).toFixed(2), dy = (4 * Math.sin(mid)).toFixed(2);
      return `<path class="fbseg${FL.cat === x.k ? ' sel' : ''}" data-cat="${x.k}" data-n="${esc(x.n)}" data-v="${x.v}" data-p="${pct(x.v, tot)}" style="fill:var(--fbc-${x.k});--dx:${dx}px;--dy:${dy}px" d="${d}"><title>${esc(x.n)}：${x.v} 則（${pct(x.v, tot)}%）</title></path>`;
    }).join('');
    const sel = FL.cat ? cnt.find((x) => x.k === FL.cat) : null;
    const c1 = sel ? sel.n : '總則數', c2 = sel ? pct(sel.v, tot) + '%' : String(tot);
    return `<div class="fbdon"><svg viewBox="0 0 200 200" id="fbDonut" role="img" aria-label="各大類占比">${segs}
      <text x="100" y="92" class="dc1" id="fbDc1">${esc(c1)}</text><text x="100" y="124" class="dc2" id="fbDc2">${esc(c2)}</text></svg>
      <ul class="fblgd">${cnt.map((x) => `<li data-cat="${x.k}" class="${FL.cat === x.k ? 'sel' : ''}"><i style="background:var(--fbc-${x.k})"></i><span>${esc(x.n)}</span><b>${x.v}</b><em>${pct(x.v, tot)}%</em></li>`).join('')}</ul></div>`;
  }
  /* D 款橫條：細項前 6 名（有選大類時只列該大類的細項）。點一條＝篩到那個細項（再點取消）*/
  function subBars(rows) {
    const m = {};
    rows.forEach((r) => { if (!r.sub) return; const k = r.cat + '/' + r.sub; m[k] = (m[k] || 0) + 1; });
    const list = Object.entries(m).sort((x, y) => y[1] - x[1]).slice(0, 6);
    if (!list.length) return '<div class="fbempty">沒有選細項的反饋</div>';
    const mx = list[0][1], tot = rows.length;
    return `<div class="fbhb" id="fbSubBars">${list.map(([k, v]) => { const [c, sb] = k.split('/');
      return `<button type="button" class="hb${FL.cat === c && FL.sub === sb ? ' sel' : ''}" data-cat="${c}" data-sub="${sb}" title="${esc(CATN[c])}・${esc(SUBN[k] || sb)}：${v} 則（${pct(v, tot)}%）"><span class="hn">${esc(SUBN[k] || sb)}</span><span class="hv">${v}・${pct(v, tot)}%</span><span class="tr"><i style="width:${(v / mx * 100).toFixed(1)}%;background:linear-gradient(90deg,color-mix(in srgb,var(--fbc-${c}) 55%,transparent),var(--fbc-${c}))"></i></span></button>`; }).join('')}</div>`;
  }
  /* C 款直條：期間內每天則數（沒有就 0）；虛線＝平均、只標最高那根。點某天＝只看那天（再點取消）*/
  function dayBars(rows, rg) {
    const days = []; for (let d = rg.from; d <= rg.to && days.length < 400; d = shiftDay(d, 1)) days.push(d);
    const m = {}; rows.forEach((r) => { const d = dayOf(r.created); m[d] = (m[d] || 0) + 1; });
    const mx = Math.max(1, ...days.map((d) => m[d] || 0)), avg = rows.length / Math.max(1, days.length), top = days.reduce((b, d) => ((m[d] || 0) > (m[b] || 0) ? d : b), days[0]);
    const lblEvery = Math.max(1, Math.ceil(days.length / 8));
    return `<div class="fbvb" id="fbDayBars"><div class="plot">${days.map((d, i) => { const v = m[d] || 0;
      return `<button type="button" class="vb${FL.day === d ? ' sel' : ''}" data-day="${d}" data-v="${v}" title="${d}：${v} 則（${pct(v, rows.length)}%）" aria-label="${d} ${v} 則"><span class="col"><i style="height:${(v / mx * 100).toFixed(1)}%">${d === top && v ? `<em>${v}</em>` : ''}</i></span></button>`; }).join('')}<span class="avgl" style="bottom:${(avg / mx * 100).toFixed(1)}%" title="平均每天 ${avg.toFixed(1)} 則"></span></div>
      <div class="xl">${days.map((d, i) => `<span>${i % lblEvery === 0 ? `${+d.slice(5, 7)}/${+d.slice(8)}` : ''}</span>`).join('')}</div></div>`;
  }
  function paintAdmin(el) {
    const j = last || {};
    const fbAll = (j.feedback || []).map(norm), rq = j.requests || [];
    unread = fbAll.filter((x) => x.status === 'new').length; paintDot();
    const rg = rangeNow();
    if (FL.day && (FL.day < rg.from || FL.day > rg.to)) FL.day = '';
    const inR0 = fbAll.filter((x) => { const d = dayOf(x.created); return d >= rg.from && d <= rg.to; });
    const nWish = inR0.filter(isWish).length;
    const inR = inR0.filter((x) => !FL.kind || (FL.kind === 'wish') === isWish(x));
    const byDay = inR.filter((x) => !FL.day || dayOf(x.created) === FL.day);              // 甜甜圈、細項橫條、小卡吃這個（有選某天就只算那天）
    const byCat = inR.filter((x) => (!FL.cat || x.cat === FL.cat) && (!FL.sub || x.sub === FL.sub));   // 每日直條吃這個（有選類別就只畫那類每天幾則）
    const fb = byDay.filter((x) => (!FL.cat || x.cat === FL.cat) && (!FL.sub || x.sub === FL.sub) && (!FL.st || stOf(x) === FL.st));
    const handled = byDay.filter((x) => x.status !== 'new').length, unreadR = byDay.length - handled;
    const sm = {}; byDay.forEach((r) => { if (r.sub) { const k = r.cat + '/' + r.sub; sm[k] = (sm[k] || 0) + 1; } });
    const topSub = Object.entries(sm).sort((a, b) => b[1] - a[1])[0];
    const rNew = rq.filter((x) => x.status === 'new').length;
    const rqv = rq.filter((x) => !RQF || (x.type || 'subscribe') === RQF);
    const rqDone = (r) => ((r.type || 'subscribe') === 'subscribe' ? ['已開通', '標為已開通'] : ['已處理', '標為已處理']);
    const sel = (id, cur, opts) => `<select id="${id}">${opts.map(([k, n]) => `<option value="${k}"${k === cur ? ' selected' : ''}>${n}</option>`).join('')}</select>`;
    const subList = FL.cat ? ((TREE.find((x) => x[0] === FL.cat) || [])[2] || []) : [];
    const stName = (s) => (FL.kind === 'wish' ? WSTN[s] || s : s === 'new' ? '未讀' : s === 'handled' ? '已處理' : WSTN[s] || s);
    const stOpts = FL.kind === 'wish' ? WST : [['new', '未讀'], ['handled', '已處理']];
    if (FL.st && !stOpts.some(([k]) => k === FL.st)) FL.st = '';
    const chips = [FL.cat && ['cat', CATN[FL.cat] + (FL.sub ? '・' + (SUBN[FL.cat + '/' + FL.sub] || FL.sub) : '')], FL.day && ['day', FL.day], FL.st && ['st', stName(FL.st)]].filter(Boolean)
      .map(([k, t]) => `<span class="fbchip" data-clr="${k}"><b>${esc(t)}</b><button type="button" aria-label="取消這個篩選" title="取消這個篩選">×</button></span>`).join('');
    const rtxt = rg.from === rg.to ? rg.from : rg.from + '～' + rg.to;
    el.innerHTML = `<div class="sat"><h2>意見反饋${unread ? `<span class="fbdot big">${unread} 未讀</span>` : ''}</h2>
        ${window.RangePick ? window.RangePick.html({ id: 'fbRange', options: [['today', '今天'], ['7', '近 7 天'], ['30', '近 30 天'], ['90', '近 90 天'], ['custom', '自訂起訖']], value: RG.v, from: rg.from, to: rg.to, max: todayTpe() }) : ''}
        <a href="#admin/notices">公告管理</a><button type="button" id="fbReload">重新整理</button></div>
      <p class="muted">使用者在右下角客服面板送出的反饋只存在本站伺服器，不寄信、只有管理者看得到。<b>怎麼用：</b>先看「最常見細項」與甜甜圈哪一塊最大＝這段期間大家最卡在哪；點扇區或橫條，下面列表只剩那一類，逐則處理完按「標為已處理」。直條突然變高的那天點下去，通常是當天某個改版出了問題。</p>
      <div class="fbkpi" id="fbKpi">
        <div class="k"><span>期間總則數</span><b id="fbKTot">${byDay.length}</b><small>${esc(FL.day || rtxt)}</small></div>
        <div class="k"><span>未讀</span><b id="fbKNew">${unreadR}</b><small>全部未讀 ${unread} 則</small></div>
        <div class="k"><span>已處理率</span><b id="fbKDone">${byDay.length ? pct(handled, byDay.length) + '%' : '—'}</b><small>${handled}／${byDay.length} 則</small></div>
        <div class="k"><span>最常見細項</span><b id="fbKTop" class="sm">${topSub ? esc(SUBN[topSub[0]] || topSub[0]) : '—'}</b><small>${topSub ? esc(CATN[topSub[0].split('/')[0]]) + '・' + topSub[1] + ' 則' : '還沒有選細項的反饋'}</small></div>
      </div>
      <div class="fbstat">
        <div class="card" id="fbCatCard"><h3>哪一類最多？</h3><p class="muted">滑過看占比；點扇區或右邊橫條，下面列表只留那一類（再點一次取消）。</p>
          <div class="fbcatw">${donut(byDay)}<div class="fbsubc"><h4>細項前幾名${FL.cat ? '（' + esc(CATN[FL.cat]) + '）' : ''}</h4>${subBars(FL.cat ? byDay.filter((x) => x.cat === FL.cat) : byDay)}</div></div></div>
        <div class="card" id="fbDayCard"><h3>每天收到幾則？</h3><p class="muted">${FL.cat ? '只算「' + esc(CATN[FL.cat]) + '」' : '全部類別'}；虛線＝平均。點某天的直條，上面統計與下面列表只看那天。</p>${dayBars(byCat, rg)}</div>
      </div>
      <div class="card"><div class="fbkind adm" id="fbFKind" role="tablist" aria-label="反饋種類">${[['', '全部', inR0.length], ['fb', '意見回饋', inR0.length - nWish], ['wish', '願望清單', nWish]].map(([k, n, c]) => `<button type="button" role="tab" data-fk="${k}" class="${FL.kind === k ? 'on' : ''}" aria-selected="${FL.kind === k}">${n}<small>${c}</small></button>`).join('')}</div>
        <div class="fbflt"><h3>${FL.kind === 'wish' ? '願望清單' : '反饋列表'}（期間 ${inR.length} 筆，顯示 ${fb.length}）</h3>${chips}
        <label>大類 ${sel('fbFCat', FL.cat, [['', '全部'], ...CATS])}</label>
        <label>細項 ${sel('fbFSub', FL.sub, [['', '全部'], ...subList])}</label>
        <label>狀態 ${sel('fbFSt', FL.st, [['', '全部'], ...stOpts])}</label></div>
        ${fb.length ? `<table id="fbTable"><thead><tr><th>時間（台北）</th><th>類別</th><th>內容</th><th>聯絡 email</th><th>頁面網址／瀏覽器</th><th>狀態</th><th></th></tr></thead><tbody>${fb.map((r) => { const w = isWish(r); return `<tr data-id="${esc(r.id)}" data-cat="${esc(r.cat)}" data-sub="${esc(r.sub)}"${w ? ' data-wish="1"' : ''} class="${r.status === 'new' ? 'unread' : ''}">
          <td>${dstr(r.created)}</td><td class="fbcatc">${w ? '<span class="fbcat fbwish">願望清單</span>' : catBadge(r)}</td><td class="fbbody">${esc(w ? String(r.body || '').replace(WISH_TAG, '') : r.body)}</td>
          <td>${r.contact ? `<a data-gmail href="${esc(gmail(r.contact, '回覆：哩股哩股意見反饋'))}" target="_blank" rel="noopener">${esc(r.contact)}</a>` : '<span class="muted">（未留）</span>'}${r.member ? '<br><small class="muted">會員' + (r.name ? '：' + esc(r.name) : '') + '</small>' : '<br><small class="muted">訪客</small>'}</td>
          <td><small>${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.url)}</a>` : ''}<br>${esc(r.ua || '')}</small></td>
          ${w ? `<td><select class="wsst" data-id="${esc(r.id)}" aria-label="願望狀態">${WST.map(([k, n]) => `<option value="${k}"${stOf(r) === k ? ' selected' : ''}>${n}</option>`).join('')}${WSTN[stOf(r)] ? '' : '<option value="handled" selected>已處理</option>'}</select></td>
          <td class="fbact"><button type="button" class="fbdel" data-del="${esc(r.id)}">刪除</button></td></tr>`
          : `<td><span class="st ${r.status === 'new' ? 'new' : ''}">${r.status === 'new' ? '未讀' : '已處理'}</span></td>
          <td class="fbact"><button type="button" data-kind="feedback" data-id="${esc(r.id)}" data-st="${r.status === 'new' ? 'handled' : 'new'}">${r.status === 'new' ? '標為已處理' : '改回未讀'}</button><button type="button" class="fbdel" data-del="${esc(r.id)}">刪除</button></td></tr>`}`; }).join('')}</tbody></table>` : `<p class="muted" id="fbEmpty">${inR.length ? '沒有符合篩選的反饋。' : '這段期間還沒有反饋。'}</p>`}</div>
      <div class="card"><div class="fbflt"><h3>訂閱申請（${rq.length} 筆，未處理 ${rNew}）</h3><label>類型 ${sel('rqFType', RQF, [['', '全部'], ['subscribe', '訂閱'], ['cancel', '取消訂閱'], ['refund', '申請退款']])}</label></div><p class="muted">金流尚未串接：訂閱＝確認付款後到「會員管理」替他設定方案與到期日，再標成「已開通」；取消訂閱＝到期日留在本期結束、次期不再續；申請退款＝退款完成後把方案改回免費會員，再標成「已處理」。</p>
        ${rqv.length ? `<table id="rqTable"><thead><tr><th>時間（台北）</th><th>類型</th><th>會員</th><th>方案</th><th>週期</th><th>聯絡 email</th><th>備註</th><th>狀態</th><th></th></tr></thead><tbody>${rqv.map((r) => `<tr data-id="${esc(r.id)}" data-type="${esc(r.type || 'subscribe')}">
          <td>${dstr(r.created)}</td><td>${esc(RQT[r.type || 'subscribe'] || r.type)}</td><td>${esc(r.name || '')}<br><small class="muted">${esc(r.email || '')}</small></td><td>${esc(r.plan)}</td><td>${r.period === 'year' ? '年繳' : '月繳'}</td><td>${esc(r.contact)}</td><td>${esc(r.note || '')}</td>
          <td><span class="st ${r.status === 'new' ? 'new' : ''}">${r.status === 'new' ? '待處理' : rqDone(r)[0]}</span></td>
          <td><button type="button" data-kind="request" data-id="${esc(r.id)}" data-st="${r.status === 'new' ? 'done' : 'new'}">${r.status === 'new' ? rqDone(r)[1] : '改回待處理'}</button></td></tr>`).join('')}</tbody></table>` : `<p class="muted" id="rqEmpty">${rq.length ? '沒有符合這個類型的申請。' : '還沒有人申請。'}</p>`}</div>`;
    const re = () => paintAdmin(el);
    el.querySelector('#fbReload').onclick = () => renderFeedbackAdmin(el);
    if (window.RangePick) window.RangePick.bind(el.querySelector('#fbRange'), { onChange: ({ value, from, to }) => {
      RG.v = value;
      if (value === 'custom') { const r2 = rangeNow(); RG.from = from || r2.from; RG.to = to && to >= RG.from ? to : todayTpe(); }
      FL.day = ''; re(); } });
    el.querySelector('#fbFCat').onchange = (e) => { FL.cat = e.target.value; FL.sub = ''; re(); };
    el.querySelector('#fbFSub').onchange = (e) => { FL.sub = e.target.value; re(); };
    el.querySelector('#fbFSt').onchange = (e) => { FL.st = e.target.value; re(); };
    el.querySelector('#fbFKind').onclick = (e) => { const b = e.target.closest('button[data-fk]'); if (b && b.dataset.fk !== FL.kind) { FL.kind = b.dataset.fk; FL.st = ''; re(); } };
    /* 願望狀態：先試 Worker 的新狀態（eval／done／no）；舊 Worker 回 400 時，伺服器端改記「new／handled」（未讀紅點照樣會消），
       細的狀態這次瀏覽先記在記憶體，並提示 Worker 要更新才存得住。*/
    el.querySelectorAll('select.wsst').forEach((s) => {
      s.onchange = async () => {
        const id = s.dataset.id, v = s.value; s.disabled = true;
        let r = await call('/v1/admin/feedback/set', { kind: 'feedback', id, status: v });
        if (r && r._s === 400 && v !== 'new') {
          r = await call('/v1/admin/feedback/set', { kind: 'feedback', id, status: 'handled' });
          if (r && r._s === 200) { wstOver[id] = v; toast('伺服器還不認「' + WSTN[v] + '」：先記成已處理，細的狀態重新整理後會不見（要更新 Worker）'); }
        } else if (r && r._s === 200) delete wstOver[id];
        if (r && r._s === 200) renderFeedbackAdmin(el); else { s.disabled = false; toast('更新失敗'); }
      };
    });
    el.querySelector('#rqFType').onchange = (e) => { RQF = e.target.value; re(); };
    el.querySelectorAll('.fbchip button').forEach((b) => { b.onclick = () => { const k = b.parentElement.dataset.clr; if (k === 'cat') { FL.cat = ''; FL.sub = ''; } else FL[k] = ''; re(); }; });
    const pickCat = (k) => { if (FL.cat === k && !FL.sub) FL.cat = ''; else FL.cat = k; FL.sub = ''; re(); };
    el.querySelectorAll('#fbDonut .fbseg, .fblgd li').forEach((s) => { s.onclick = () => pickCat(s.dataset.cat); });
    /* 滑過：中心字換成該類名稱與 %（A 款）；滑過圖例同步強調對應扇區 */
    const dc1 = el.querySelector('#fbDc1'), dc2 = el.querySelector('#fbDc2');
    if (dc1) {
      const c0 = [dc1.textContent, dc2.textContent];
      const hl = (k, on) => { const s = el.querySelector(`#fbDonut .fbseg[data-cat="${k}"]`); if (!s) return; s.classList.toggle('hov', on); dc1.textContent = on ? s.dataset.n : c0[0]; dc2.textContent = on ? s.dataset.p + '%' : c0[1]; };
      el.querySelectorAll('#fbDonut .fbseg, .fblgd li').forEach((s) => { s.onmouseenter = () => hl(s.dataset.cat, true); s.onmouseleave = () => hl(s.dataset.cat, false); });
    }
    el.querySelectorAll('#fbSubBars .hb').forEach((b) => { b.onclick = () => { const c = b.dataset.cat, sb = b.dataset.sub; if (FL.cat === c && FL.sub === sb) FL.sub = ''; else { FL.cat = c; FL.sub = sb; } re(); }; });
    el.querySelectorAll('#fbDayBars .vb').forEach((b) => { b.onclick = () => { FL.day = FL.day === b.dataset.day ? '' : b.dataset.day; re(); }; });
    el.querySelectorAll('button[data-kind]').forEach((b) => {
      b.onclick = async () => {
        b.disabled = true;
        const r = await call('/v1/admin/feedback/set', { kind: b.dataset.kind, id: b.dataset.id, status: b.dataset.st });
        if (r && r._s === 200) renderFeedbackAdmin(el); else { b.disabled = false; toast('更新失敗'); }
      };
    });
    el.querySelectorAll('button[data-del]').forEach((b) => {
      b.onclick = async () => {
        if (!window.confirm('確定刪除這則反饋？刪除後無法復原。')) return;
        b.disabled = true;
        const r = await call('/v1/admin/feedback/del', { id: b.dataset.del });
        if (r && r._s === 200) { toast('已刪除'); renderFeedbackAdmin(el); } else { b.disabled = false; toast('刪除失敗'); }
      };
    });
  }
  window.TwSupport = { open: () => toggle(true), close: () => toggle(false), renderFeedbackAdmin, paintDot, refreshUnread, unread: () => unread, email: SUPPORT_EMAIL, faq: FAQ };
  /* 管理端路由：#admin/feedback（這支畫）。#admin/notices 給 notices.js。view 共用 #v-subadm */
  window.TwSubRoutes.push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'feedback') return null;
    const v = view('v-subadm'); if (!v) return null;
    renderFeedbackAdmin(v);
    return 'v-subadm';
  });
  window.addEventListener('tw:account', () => {
    refreshUnread();
    if ((location.hash || '') === '#admin/feedback') { const v = view('v-subadm'); if (v) renderFeedbackAdmin(v); }
    const p = document.getElementById('supPanel'); if (p && !p.hidden && tab === 'fb') paint();
  });
  /* 管理區不放浮動鈕：#admin/perm 底部的「儲存」列是 sticky 在右下角，浮動鈕會正好蓋住「儲存」（驗收實測點不到）。
     管理者在管理區用不到客服；離開管理區就回來。*/
  function syncFab() {
    const fab = document.getElementById('supFab'); if (!fab) return;
    const adm = (location.hash || '').startsWith('#admin');
    fab.hidden = adm;
    /* 2026-10-06（Andy：換頁面後 Default 都要回到收合）：客服面板換頁一律收起，不跟到新頁面。*/
    const p = document.getElementById('supPanel'); if (p && !p.hidden) toggle(false);
  }
  window.addEventListener('hashchange', syncFab);
  const boot = () => { ensure(); syncFab(); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
