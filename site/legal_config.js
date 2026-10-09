/* ============================================================================
   法律頁與同意橫幅的開關（設計系統 v2 第 6 批，docs/design_system_v2.md ④）

   ★ 要正式上線，只改這一個檔。

   為什麼是一支 .js 而不是 legal.json：
     · 同步載入 —— 橫幅要不要出現，必須在第一次畫面出來時就決定；用 fetch 讀 JSON 會先閃一下。
     · stamp_assets.py 會自動給它加版本戳，改完部署一定換得掉（JSON 不會被戳，會卡在快取）。
     · 用 file:// 直接打開 index.html 也讀得到（fetch 讀不到）。

   ⚠ 為什麼預設關著：條款草稿（docs/compliance_and_tiers.md ③）還有【】空格。
     **不准讓使用者「同意」一份有空格的草稿** —— 所以下面「必填」任何一格是空的、
     或還留著【】，同意橫幅就不出現、平台導覽不自動彈出、兩份條款頁頂端掛「草稿，尚未生效」。
     必填全部填好 **而且** enabled: true，才會正式啟用。
     判斷在 legal.js 的 `ready()`，它另外會掃「畫出來的條款全文」還有沒有【】，
     所以就算有人漏填了一個這裡沒列到的空格，也一樣不會啟用。

   ⚠ 這不是律師擬的定稿，上線前請專業人士看過一次（compliance_and_tiers.md ⑥）。
   ========================================================================== */
window.TW_LEGAL = {
  /* ---- 必填（Andy 2026-10-09 18:1x 回覆；enabled 仍是 false，等 Andy 說「可以開」）---- */
  operator: '哩股哩股',              // 服務提供者。Andy：「哩股哩股」
  email: 'kcq01010909@gmail.com',    // 聯絡 email。Andy：「沿用 kcq01010909@gmail.com 後面會更改」（改的時候連 legal.js 的 CONTACT_EMAIL 一起換）
  effective_date: '2026-10-01',      // 生效日期，同時是「條款版本」：改了它，所有人會重新看到一次同意橫幅。Andy：「先設定10/01 後面上架 會在改」
  tax_id: '尚未辦理',                // 統一編號。Andy：「尚未辦理」
  court: '臺灣臺北地方法院',          // 第一審管轄法院。CEO 查證後採用；使用條款另加消保法 §47／民訴 §436-9 但書（legal.js 讀這一格，不再寫死）

  /* ---- 選填（空的時候有退路，寫在右邊）---- */
  updated_date: '',      // 最後更新日期；空的＝同生效日期
  copyright_holder: '',  // 著作權人；空的＝同服務提供者
  license_url: '',       // 商業授權方案頁；空的＝改寫「請來信 email 洽詢」

  /* ---- 已知的事實，先幫忙填好（不對就改）---- */
  site_name: '哩股哩股',   // 2026-10-07 Andy 定案站名「哩股哩股」
  repo_url: '',          // ★ 2026-09-24 Andy：原始碼不能公開，網站上不准出現 repo 連結；這一欄保持空的
  // 隱私權政策「資料存在哪裡」：本站目前實際用到的第三方服務（2026-10-09 依程式碼更新：會員資料也在 Cloudflare；期貨盤中報價走 Deno Deploy）
  hosting: 'GitHub Pages（GitHub, Inc.，美國；網站本身）、Cloudflare Workers（Cloudflare, Inc.，全球節點；會員資料、自選清單、使用統計與盤中報價轉送）、Deno Deploy（Deno Land Inc.；期貨盤中報價轉送）、Google（Google 帳號登入）',

  /* ---- 功能旗標（2026-10-09 依現況改正）----
     ⚠ 2026-10-07 起 legal.js 的三份條文改成直接寫死現況（不再用這四個旗標切段落），所以這四格目前只是「現況紀錄」，
       不會讓畫面多出或少掉段落；改它們不影響版面。保留的理由：日後若改回旗標切段，值必須是對的。
     · paid：#pricing 已在販售 Plus／Pro（申請制、專人開通；線上付款尚未上線）→ true
     · sync：會員雲端自選清單已上線（workers/account-api，/v1/lists）→ true
     · analytics：管理區「流量觀測」有不具名彙總統計＋登入者使用明細（worker.js USAGE_KEEP_MONTHS=13）→ true
     · presence：頂欄「N 人在線」與管理區線上名單（worker.js presence 表，PRESENCE_TTL_MS=7 分鐘）→ true
     · newsletter：目前不寄任何電子報或行銷信 → false */
  paid: true,
  newsletter: false,
  sync: true,
  analytics: true,
  presence: true,

  /* ---- 退款與取消訂閱政策（#refund，2026-10-09）----
     ★ 下面的數字是「商業承諾」，由 Andy 決定；目前先照 Andy 給的參考預設（docs/legal_refund_1009.md 第五節）。
     ★ 2026-10-09 18:1x Andy 決定：先不提供免費試用，只保留 REFUND_DAYS 天退款保證；退款保證與（日後若開的）試用合計一次。
     其他檔要讀：window.TW_LEGAL.REFUND_DAYS（或 window.TwLegal.refund().days，有驗收覆寫時以後者為準）。
     claude/acct-menu（帳號選單「申請退款」「取消訂閱」）請讀這裡，不要自己再寫一個 7。*/
  REFUND_DAYS: 7,            // 首次付款後幾日內可申請全額退款（退款保證）
  REFUND_PROCESS_DAYS: 14,   // 收到退款申請後，幾日內完成審核並通知金流服務商退款（日曆天）
  REFUND_OUTAGE_DAYS: 7,     // 本站連續幾日無法提供核心功能時，付費者得按未使用日數比例申請退款
  // 刪除帳號後，信箱比對碼（以 Worker secret 金鑰 HMAC 過的信箱，只用來判斷退款保證／試用資格）保存幾天；期滿自動刪除。
  // 2026-10-09 CEO 決定預設 365（Andy：「寧可不給也不讓人鑽漏洞」；網路實例 30 天～6 個月，沒有業界標準）
  HASH_RETENTION_DAYS: 365,
  PAY_ONLINE: false,         // 線上付款上線 → true：退款頁改寫「帳號選單自助取消」；⚠ 同時結帳頁必須有七日解除權例外的勾選同意
  PAY_PROVIDER: '',          // 金流服務商名稱（上線時填，例如公司全名）；空的＝寫「第三方金流服務商（上線時於本頁公告名稱）」
  APP_STORE_IAP: false,      // 有 App 且在 App Store／Google Play 內購時才開；目前沒有 App
  SELF_DELETE: false,        // 帳號選單「刪除帳號」上線（claude/acct-menu）→ true：隱私權政策改寫「可於帳號選單自行刪除」

  /* ---- 總開關 ---- */
  enabled: false,
};
