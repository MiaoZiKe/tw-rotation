/* ============================================================================ 金流訂單 pay-1011（2026-10-11）
   Andy 10-11：「訂閱畫面，點擊訂閱後需要跳出金流服務，我已經申請綠界科技了，但還需要新增帳戶匯款，並且是需要有紀錄清單的…
               所以會有兩種方式可以進行」
   追加：「若是手動匯款，是否有辦法達成訂閱每月扣款」→ 做不到（docs/payment_checkout_1011.md 第 7 節）：轉帳＝預付制，信用卡才有定期定額。
   追加（最高優先）：「當確認他付款後，會紀錄他付款時間，他訂閱多久，多久後會自動取消…千萬不要發生付款後還沒開放…退款機制我是否能快速退款」。

   設計（細節、流程圖與查證來源在 docs/payment_checkout_1011.md）：
   ① 兩種付款方式
      · 綠界 ECPay 全方位金流（AioCheckOut V5）：單次（信用卡／ATM／超商，ChoosePayment=ALL）或信用卡定期定額（ChoosePayment=Credit＋PeriodAmount…）。
        表單參數與 CheckMacValue 由這裡產生，前端只負責 auto-submit；金額一律以伺服器 plans 為準。
      · 銀行轉帳（預付制）：會員開單 → 看收款帳號 → 匯款後回報末 5 碼 → 管理者確認入帳 → 開通。
   ② 付款後一定開通（多重保險，每一層 tests/pay.test.mjs 都有測）
      1. ReturnURL（伺服器對伺服器）驗章成功、RtnCode=1、金額相符 → 開通
      2. 使用者被導回（OrderResultURL）→ 伺服器主動 QueryTradeInfo/V5 查單（驗章）→ 已付款就開通
      3. 每 10 分鐘排程：3 天內還沒開通的綠界訂單逐筆查單；定期定額用 QueryCreditCardPeriodInfo 補漏掉的期數
      4. 前端付款完成頁輪詢 /v1/pay/order，開通後立刻 TwPerm.refresh()
      5. 異常清單：已付款但沒開通、開通出錯、金額不符 → 管理區紅色數字＋一鍵補開通
      6. 冪等：orders.applied＝1 之後同一筆不會再加期間；每筆記錄開通的期間（grant_from～grant_to）
   ③ 到期降級：權限判斷本來就以 perm.expires 為準（effective() 讀取時判斷，不靠排程）；排程另外寫一筆 plan_events 'expire' 紀錄。
   ④ 退款：信用卡走綠界 CreditDetail/DoAction（放棄 N／關帳改金額 C／退刷 R）；ATM／超商／轉帳登記人工退款；定期定額同時 Cancel。
   ★ 金鑰：ECPAY_MERCHANT_ID／ECPAY_HASH_KEY／ECPAY_HASH_IV 是 Worker Secret；三個都沒設＝綠界公開的測試環境（下面 ECPAY_STAGE）。
   ★ 收款帳號不寫在 repo（public）：存在 kv 'pay_bank'，管理區設定。
   ============================================================================ */

/* 綠界官方公開的測試資料（不是金鑰）：developers.ecpay.com.tw「測試環境／Test Information」頁（?p=2856、/49114/、/22867/）列的
   「模擬銀行 3D 驗證」特店 3002607；同一組也是官方「檢查碼機制」附錄範例用的 HashKey／HashIV。官方註明不可用在正式環境。 */
export const ECPAY_STAGE = { id: '3002607', key: 'pwFHCqoQZGmho4w6', iv: 'EkRm7iFT261dpevs' };
const ECPAY_STAGE_HOST = 'https://payment-stage.ecpay.com.tw';
const ECPAY_PROD_HOST = 'https://payment.ecpay.com.tw';

/* ---------------------------------------------------------------- CheckMacValue（官方附錄「檢查碼機制」）
   1. 參數（不含 CheckMacValue）依參數名稱 A→Z 排序（不分大小寫）
   2. 前面加 HashKey=…&，後面加 &HashIV=…
   3. 整串做 .NET 風格的 URL encode（空白→+；- _ . ! * ( ) 不編碼），再轉小寫
   4. SHA256 → 轉大寫
   官方範例（tests/pay.test.mjs 驗算）：特店 3002607、MerchantTradeNo ecpay20230312153023、TotalAmount 30000 …
   → 6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840 */
export function ecNetEncode(s) {
  return encodeURIComponent(s).replace(/%20/g, '+').replace(/[!*()']/g, (c) => '%' + c.charCodeAt(0).toString(16).toUpperCase())
    .replace(/%2D/gi, '-').replace(/%5F/gi, '_').replace(/%2E/gi, '.').replace(/%21/gi, '!').replace(/%2A/gi, '*').replace(/%28/gi, '(').replace(/%29/gi, ')');
}
export function ecMacSource(params, key, iv) {
  const ks = Object.keys(params).filter((k) => k !== 'CheckMacValue').sort((a, b) => { const x = a.toLowerCase(), y = b.toLowerCase(); return x < y ? -1 : x > y ? 1 : 0; });
  return ecNetEncode(`HashKey=${key}&` + ks.map((k) => `${k}=${params[k] == null ? '' : params[k]}`).join('&') + `&HashIV=${iv}`).toLowerCase();
}
export async function ecpayMac(params, key, iv) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ecMacSource(params, key, iv)));
  return Array.from(new Uint8Array(d), (x) => x.toString(16).padStart(2, '0')).join('').toUpperCase();
}

/* ---------------------------------------------------------------- 可調參數 */
export const PAY_BANK_DAYS = 3;          // 轉帳訂單：開單後 3 天內匯款（畫面寫「請於 3 天內轉帳」），過了標「已逾期」
export const PAY_MAX_NEW_DAY = 5;        // 同一會員 24 小時內最多開幾筆新訂單（Andy 規格：轉帳 5 筆；綠界同一個上限另外算）
export const PAY_MAX_ECPAY_DAY = 10;
const PAY_ECPAY_EXPIRE_DAYS = 3;         // 2026-10-11 Andy：綠界待付款超過 3 天沒付 → 排程標「已取消（未付款）」（之後綠界才通知付款成功照樣開通＋列異常）
const PAY_SWEEP_DAYS = 3;                // 排程：3 天內還沒開通的綠界訂單逐筆查單
const PAY_PERIOD_SYNC_MS = 6 * 3600 * 1000;   // 定期定額對帳：每筆最多 6 小時查一次
const PAY_RENEW_DAYS = 7;                // 轉帳會員：到期前 7 天與 1 天提醒
export const PAY_STATUS = { pending: '待付款', review: '待確認', paid: '已入帳', active: '已開通', failed: '失敗', rejected: '已退回', expired: '已逾期', refunded: '已退款', cancelled: '已取消（未付款）', superseded: '已被取代' };
/* 2026-10-16 Andy：結帳要填姓名＋性別（男／女），性別納入男女用量比例統計。
   GENDER_REQUIRED 是「性別要不要必填」的唯一開關（Andy 10-16：先必填；法遵意見若要求改選填就改這個 false，
   前端 site/checkout.js 開頭有同名常數，兩邊一起改）。只有新版結帳表單（form >= 2）才檢查必填：
   瀏覽器快取裡的舊版網頁不會送這些欄位，先部署 Worker 時不能讓它們結帳失敗。 */
export const GENDERS = ['male', 'female'];
export const GENDER_REQUIRED = false;
/* 法遵意見（docs/legal/gender_collection_1016.md 3-3）：性別要有「獨立勾選同意」（不併進條款勾選）。GENDER_CONSENT_REQUIRED 是它的開關，
   前端 checkout.js 同名常數。要改成選填版本：兩個常數都改 false。 */
export const GENDER_CONSENT_REQUIRED = false;
export const PAY_FORM_VERSION = 2;
/* 卡號防呆：任何欄位出現連續 13～19 位數字（可夾空白、連字號）就拒收。本站任何欄位都不該有卡號。 */
export const looksLikeCard = (v) => /\d(?:[ -]?\d){12,18}/.test(String(v == null ? '' : v));
/* 驗結帳表單的個人欄位：回 { name, gender, last5 } 或 { error }。
   · 末 5 碼＝銀行轉帳對帳用的轉出帳號末 5 碼，只收 5 個數字（綠界分頁選填）；絕不收信用卡卡號任何位數。 */
export function payProfile(b, subClean, opt) {
  const o = opt || {};
  const strict = Number(b.form) >= PAY_FORM_VERSION;
  const name = subClean(b.name, 40);
  const gender = b.gender == null || b.gender === '' ? '' : String(b.gender);
  if (gender && !GENDERS.includes(gender)) return { error: 'bad_gender' };
  if (looksLikeCard(name) || looksLikeCard(b.last5)) return { error: 'card_number' };
  if (strict && !name) return { error: 'need_name' };
  if (strict && GENDER_REQUIRED && !gender) return { error: 'need_gender' };
  if (strict && gender && GENDER_CONSENT_REQUIRED && b.gender_consent !== true) return { error: 'need_gender_consent' };
  let last5 = '';
  if (o.last5 && b.last5 != null && String(b.last5).trim() !== '') {
    last5 = String(b.last5).trim();
    if (!/^\d{5}$/.test(last5)) return { error: 'bad_last5' };
  }
  return { name, gender, last5 };
}
const ID_RE = /^LG[0-9A-Z]{10,18}(P\d{1,3})?$/;
const DAY = 86400 * 1000;

export function installPay(Hub, H) {
  const { rand, safeEq, tpeDay, subClean, EXPORT_TABLES } = H;
  const norm = (e) => String(e || '').trim().toLowerCase();
  const tpeStr = (ms) => new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 19).replace('T', ' ').replace(/-/g, '/');   // yyyy/MM/dd HH:mm:ss（台北）
  const parseTpe = (s) => { const m = /^(\d{4})\/(\d{1,2})\/(\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(String(s || '')); return m ? Date.UTC(+m[1], m[2] - 1, +m[3], +m[4] - 8, +m[5], +(m[6] || 0)) : 0; };
  /* 加 n 個月（台北日曆）：1/31 + 1 個月 → 2/28（不跳到 3 月） */
  const addMonths = (ms, n) => {
    const d = new Date(ms + 8 * 3600 * 1000), day = d.getUTCDate();
    d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + n);
    const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
    d.setUTCDate(Math.min(day, last));
    return d.getTime() - 8 * 3600 * 1000;
  };

  Hub.prototype.payInit = function () {
    if (this._payOk) return;
    this.billInit();
    this.q(`CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, uid TEXT, email TEXT, plan TEXT, plan_name TEXT, period TEXT, amount INTEGER,
      method TEXT, recur INTEGER DEFAULT 0, parent TEXT, period_n INTEGER, period_state TEXT, status TEXT,
      trade_no TEXT, gwsr TEXT, pay_type TEXT, pay_info TEXT, rtn_msg TEXT,
      from_last5 TEXT, xfer_date TEXT, xfer_amount INTEGER, note TEXT, admin_note TEXT, reject_reason TEXT,
      applied INTEGER DEFAULT 0, grant_from INTEGER, grant_to INTEGER, act_src TEXT, act_err TEXT, anomaly TEXT,
      refunded INTEGER DEFAULT 0, test INTEGER DEFAULT 0, back TEXT, consent TEXT,
      created INTEGER, paid_at INTEGER, confirmed_at INTEGER, cancel_at INTEGER, last_sync INTEGER, updated INTEGER)`);
    this.q('CREATE INDEX IF NOT EXISTS orders_uid ON orders (uid, created)');
    this.q('CREATE INDEX IF NOT EXISTS orders_email ON orders (email, created)');
    this.q(`CREATE TABLE IF NOT EXISTS refunds (id TEXT PRIMARY KEY, oid TEXT, email TEXT, amount INTEGER, kind TEXT, action TEXT, status TEXT,
      perm TEXT, acct_last5 TEXT, rdate TEXT, note TEXT, msg TEXT, by TEXT, created INTEGER, done_at INTEGER)`);
    /* 方案異動紀錄（開通／延長／到期降級／退款降級）。ref＋kind＋email 唯一 → 同一件事只記一次 */
    this.q('CREATE TABLE IF NOT EXISTS plan_events (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, kind TEXT, plan TEXT, at INTEGER, ref TEXT, detail TEXT)');
    this.q('CREATE UNIQUE INDEX IF NOT EXISTS plan_events_u ON plan_events (email, kind, ref)');
    /* 金流原始事件（通知、查單、退款回應）：對帳與查問題用 */
    this.q('CREATE TABLE IF NOT EXISTS pay_events (id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER, oid TEXT, kind TEXT, detail TEXT)');
    /* 2026-10-12：管理者確認時輸入的網銀實收金額（recv_amount）；會員每一次匯款回報的不可改紀錄（reports，JSON 陣列，新的在後）*/
    const cols = new Set(this.q('PRAGMA table_info(orders)').map((c) => c.name));
    if (!cols.has('recv_amount')) this.q('ALTER TABLE orders ADD COLUMN recv_amount INTEGER');
    if (!cols.has('reports')) this.q('ALTER TABLE orders ADD COLUMN reports TEXT');
    /* 2026-10-16 Andy：「需要多一個客戶填姓名的欄位，強制要求填寫」→ 匯款人姓名 */
    if (!cols.has('payer_name')) this.q('ALTER TABLE orders ADD COLUMN payer_name TEXT');
    /* 2026-10-16 Andy：結帳加性別；綠界分頁的姓名放 payer_name、選填末 5 碼放 payer_last5（不用 from_last5：那欄有「已回報匯款」的意思，很多判斷靠它）*/
    if (!cols.has('gender')) this.q('ALTER TABLE orders ADD COLUMN gender TEXT');
    if (!cols.has('payer_last5')) this.q('ALTER TABLE orders ADD COLUMN payer_last5 TEXT');
    /* 性別只存「計數」（法遵意見 4-2 做法 A）：gender_counts 每列＝一天 × 男／女 的人數，不含 uid、email、訂單編號。
       orders.gender 只是「付款完成前的暫存」：訂單開通那一刻 payCountGender 把它算進計數並清成 NULL；
       沒付款的單，排程 14 天後也清掉。所以長期留在資料庫的性別只有計數。 */
    this.q('CREATE TABLE IF NOT EXISTS gender_counts (day TEXT, g TEXT, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, g))');
    /* 2026-10-12 Andy：「使用者升級以及退款這類重大資訊都需要給他們通知」→ 個人帳務通知（站內鈴鐺）＋選用 email 佇列 */
    this.q('CREATE TABLE IF NOT EXISTS user_notices (id TEXT PRIMARY KEY, email TEXT, title TEXT, body TEXT, ref TEXT, created INTEGER, read_at INTEGER)');
    this.q('CREATE INDEX IF NOT EXISTS user_notices_em ON user_notices (email, created)');
    this.q('CREATE TABLE IF NOT EXISTS mail_out (id TEXT PRIMARY KEY, email TEXT, subject TEXT, body TEXT, created INTEGER, status TEXT, tries INTEGER DEFAULT 0, msg TEXT, sent_at INTEGER)');
    /* 2026-10-16 Andy：「一個mail 身份只能存在一個，若他有最新的一筆資訊，就只會留下最新的一筆」→ 申請被自動結案／管理者處理的原因與時間；
       pinned＝管理者「改回待處理」的時間（之後比它舊的訂單事件不會再把它結案）。退款紀錄記下是從哪一筆申請來的（req）。 */
    const rqCols = new Set(this.q('PRAGMA table_info(sub_requests)').map((c) => c.name));
    for (const [c, t] of [['close_reason', 'TEXT'], ['closed_at', 'INTEGER'], ['closed_by', 'TEXT'], ['pinned', 'INTEGER']]) if (!rqCols.has(c)) this.q(`ALTER TABLE sub_requests ADD COLUMN ${c} ${t}`);
    if (!this.q('PRAGMA table_info(refunds)').some((c) => c.name === 'req')) this.q('ALTER TABLE refunds ADD COLUMN req TEXT');
    this._payOk = true;
  };
  /* 綠界回傳／通知的原文只留白名單欄位（交易編號、金額、狀態、時間），其餘（含 NeedExtraPaidInfo=Y 時會帶的 card6no／card4no 等持卡人資訊）一律丟掉 */
  const EV_KEEP = /^(MerchantTradeNo|TradeNo|RtnCode|RtnMsg|TradeAmt|TradeStatus|PaymentType|PaymentDate|TradeDate|PeriodType|Frequency|ExecTimes|PeriodAmount|ExecStatus|TotalSuccessTimes|TotalSuccessAmount|amount|gwsr|process_date|SimulatePaid)$/;
  const evSafe = (src) => {
    let o = null;
    if (src && typeof src === 'object') o = src;
    else { const t = String(src == null ? '' : src); try { o = JSON.parse(t); } catch (e) { o = null; } if (!o || typeof o !== 'object') { try { o = Object.fromEntries(new URLSearchParams(t)); } catch (e) { o = null; } } }
    if (!o) return '(格式無法解析，未記錄)';
    const out = {};
    for (const k of Object.keys(o)) if (EV_KEEP.test(k) && (typeof o[k] === 'string' || typeof o[k] === 'number')) out[k] = String(o[k]).slice(0, 80);
    return JSON.stringify(out);
  };
  Hub.prototype.payEv = function (oid, kind, detail) {
    /* 2026-10-16 稽核：事件紀錄不留卡號資訊。最後一道關卡：連續 13～19 位數字一律遮成 [已遮蔽]（各呼叫處另用 evSafe 只留白名單欄位） */
    this.q('INSERT INTO pay_events (at, oid, kind, detail) VALUES (?, ?, ?, ?)', this.now(), oid || '', kind, String(typeof detail === 'string' ? detail : JSON.stringify(detail || {})).replace(/\d(?:[ -]?\d){12,18}/g, '[已遮蔽]').slice(0, 1500));
  };
  /* 個人帳務通知：同一件事（ref）只通知一次。站內鈴鐺一定有；設了 Resend 才另外寄 email（排程每 10 分鐘送出）*/
  Hub.prototype.payTell = function (email, title, body, ref) {
    try {
      const em = norm(email); if (!em) return;
      let h1 = 0x811c9dc5, h2 = 0x01000193; for (const ch of String(ref)) { const c = ch.codePointAt(0); h1 = Math.imul(h1 ^ c, 16777619) >>> 0; h2 = Math.imul(h2 + c, 2246822519) >>> 0; }
      const id = 'u' + h1.toString(36) + h2.toString(36);   // ref 的雜湊：同一件事同一個 id（冪等）
      if (this.q('SELECT 1 FROM user_notices WHERE id = ?', id).length) return;
      const now = this.now();
      const full = body + '\n\n有任何問題，直接回覆這封信或從網站右下角「客服」聯絡我們。\n哩股哩股 https://liguligu-puipui.com/';
      this.q('INSERT INTO user_notices (id, email, title, body, ref, created) VALUES (?, ?, ?, ?, ?, ?)', id, em, title.slice(0, 80), body.slice(0, 1500), ref, now);
      this.q('INSERT OR IGNORE INTO mail_out (id, email, subject, body, created, status) VALUES (?, ?, ?, ?, ?, ?)', id, em, '【哩股哩股】' + title.slice(0, 80), full.slice(0, 3000), now, 'pending');
    } catch (e) { /* 通知失敗不影響金流本身 */ }
  };
  /* 2026-10-16 Andy：「當訂閱後，我這邊也會收到mail 標題是他的姓名 + 方案 日期」→ 寄給站方（NOTIFY_EMAIL，沒設＝liguligu0818@gmail.com）。
     只進寄信佇列：RESEND_API_KEY／MAIL_FROM 沒設時佇列不會送、也不會報錯，付款流程照常。ref 冪等：同一筆回報只寄一次。*/
  Hub.prototype.payNotifyOwner = function (subject, body, ref, prefix) {
    try {
      const to = norm(this.env.NOTIFY_EMAIL || 'liguligu0818@gmail.com'); if (!to) return;
      let h1 = 0x811c9dc5, h2 = 0x01000193; for (const ch of String(ref)) { const c = ch.codePointAt(0); h1 = Math.imul(h1 ^ c, 16777619) >>> 0; h2 = Math.imul(h2 + c, 2246822519) >>> 0; }
      this.q('INSERT OR IGNORE INTO mail_out (id, email, subject, body, created, status) VALUES (?, ?, ?, ?, ?, ?)',
        'o' + h1.toString(36) + h2.toString(36), to, String(subject).slice(0, 150), String(body).slice(0, 3000), this.now(), 'pending');
      /* 2026-10-16 Andy：「客戶下訂單 我這邊會有通知」→ 管理者的站內鈴鐺也放一則（不另外寄信，信上面已經寄了）。
         id 以 u 開頭才走得到既有的「已讀」路徑；每位管理者各一則、ref 冪等 */
      for (const am of this.admins()) {
        const r2 = 'adm|' + ref + '|' + am;
        let a1 = 0x811c9dc5, a2 = 0x01000193; for (const ch of r2) { const c = ch.codePointAt(0); a1 = Math.imul(a1 ^ c, 16777619) >>> 0; a2 = Math.imul(a2 + c, 2246822519) >>> 0; }
        this.q('INSERT OR IGNORE INTO user_notices (id, email, title, body, ref, created) VALUES (?, ?, ?, ?, ?, ?)', 'u' + a1.toString(36) + a2.toString(36), norm(am),
          ((prefix || '新訂單：') + String(subject)).slice(0, 80), String(body).slice(0, 1500), r2.slice(0, 200), this.now());
      }
    } catch (e) { /* 通知失敗不影響金流本身 */ }
  };
  Hub.prototype.payMailFlush = async function () {
    const e = this.env;
    if (!e.RESEND_API_KEY || !e.MAIL_FROM) return 0;
    let n = 0;
    for (const m of this.q("SELECT * FROM mail_out WHERE status = 'pending' AND tries < 5 AND created > ? ORDER BY created LIMIT 20", this.now() - 3 * DAY)) {
      try {
        const r = await fetch('https://api.resend.com/emails', { method: 'POST', headers: { 'content-type': 'application/json', Authorization: 'Bearer ' + e.RESEND_API_KEY },
          body: JSON.stringify({ from: e.MAIL_FROM, to: [m.email], subject: m.subject, text: m.body, reply_to: e.MAIL_REPLY_TO || 'liguligu0818@gmail.com' }) });
        if (r.ok) { this.q("UPDATE mail_out SET status = 'sent', sent_at = ?, tries = tries + 1 WHERE id = ?", this.now(), m.id); n++; }
        else this.q('UPDATE mail_out SET tries = tries + 1, msg = ? WHERE id = ?', ('HTTP ' + r.status + ' ' + (await r.text()).slice(0, 150)), m.id);
      } catch (err) { this.q('UPDATE mail_out SET tries = tries + 1, msg = ? WHERE id = ?', String(err && err.message || err).slice(0, 150), m.id); }
    }
    return n;
  };
  Hub.prototype.planEv = function (email, kind, plan, ref, detail) {
    this.q('INSERT OR IGNORE INTO plan_events (email, kind, plan, at, ref, detail) VALUES (?, ?, ?, ?, ?, ?)', norm(email), kind, plan || '', this.now(), String(ref || ''), String(detail || '').slice(0, 300));
  };

  /* ---------------------------------------------------------------- 綠界設定 */
  Hub.prototype.ecCfg = function () {
    const e = this.env;
    if (e.ECPAY_MERCHANT_ID && e.ECPAY_HASH_KEY && e.ECPAY_HASH_IV) {
      return { id: String(e.ECPAY_MERCHANT_ID), key: String(e.ECPAY_HASH_KEY), iv: String(e.ECPAY_HASH_IV), test: false, host: ECPAY_PROD_HOST };
    }
    /* 測試環境；ECPAY_STAGE_HOST 只給本機 devserver 的假綠界用（只收 127.0.0.1，正式部署沒有這個變數） */
    const ov = /^http:\/\/127\.0\.0\.1:\d+$/.test(String(e.ECPAY_STAGE_HOST || '')) ? e.ECPAY_STAGE_HOST : ECPAY_STAGE_HOST;
    return { ...ECPAY_STAGE, test: true, host: ov };
  };
  Hub.prototype.ecVerify = async function (p) {
    const c = this.ecCfg();
    if (!p || typeof p.CheckMacValue !== 'string') return false;
    if (p.MerchantID && String(p.MerchantID) !== c.id) return false;
    return safeEq(String(p.CheckMacValue).toUpperCase(), await ecpayMac(p, c.key, c.iv));
  };
  /* 打綠界的後台 API（form POST）。回 { status, text, form } */
  Hub.prototype.ecPost = async function (path, params, host) {
    const c = this.ecCfg();
    const p = { MerchantID: c.id, ...params };
    p.CheckMacValue = await ecpayMac(p, c.key, c.iv);
    const r = await fetch((host || c.host) + path, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(p).toString() });
    const text = await r.text();
    let form = {}; try { form = Object.fromEntries(new URLSearchParams(text.trim())); } catch (e) { form = {}; }
    return { status: r.status, text, form };
  };
  const ts = (hub) => String(Math.floor(hub.now() / 1000));

  /* ---------------------------------------------------------------- 方案異動規則（2026-10-12 Andy：「已經是年繳，除非要升級 Pro，不然不可以再出現月繳帳單；原本月繳可以升 Pro 或 Plus 年繳」）
     目前方案 × 週期 → 能買什麼：同方案同週期只有「快到期（PAY_RENEW_DAYS 天內）」才能續訂；月繳→年繳（同方案）可以；
     升到更高方案：目前是年繳就只能買年繳，目前是月繳月年都行；降級、年繳改月繳一律擋。方案不在排行表（自訂方案）或查不到目前訂單時不擋。 */
  const PAY_RANK = { plus: 1, pro: 2 };
  /* 2026-10-16 Andy：「級別排序 pro(年) > pro(月) > plus(年) > plus(月)」→ 方案＋週期一起排成一個級別數字 */
  const payTier = (plan, period) => (PAY_RANK[plan] ? PAY_RANK[plan] * 2 + (period === 'year' ? 1 : 0) : 0);
  const perName = (p) => (p === 'year' ? '年繳' : '月繳');
  Hub.prototype.payChangeCheck = function (email, plan, period) {
    const now = this.now(), no = (reason, msg) => ({ ok: false, reason, msg }), want = payTier(plan, period);
    /* 2026-10-16 Andy：「已經有訂單狀態的情況，不能再訂閱其他項目，除非他是訂閱升級的版本」→ 有待審核（銀行轉帳已送出匯款資料）的訂單時，
       只能買級別比待審核那筆更高的；同級或更低一律擋（前端按鈕顯示「待審核」反灰）。 */
    const rev = this.q("SELECT plan, plan_name, period FROM orders WHERE email = ? AND status = 'review' AND parent IS NULL", email);
    if (rev.length && want) {
      const top = rev.reduce((a, o) => (payTier(o.plan, o.period) > payTier(a.plan, a.period) ? o : a));
      if (want <= payTier(top.plan, top.period)) return no('pending_review', `你有一筆「${top.plan_name}・${perName(top.period)}」待審核中，審核完成前只能申請更高級別的方案。`);
    }
    const e = this.effective(email);
    if (e.expired || !e.plan || e.plan === 'free' || !e.expires || e.expires <= now) return { ok: true };
    const cur = this.q('SELECT period FROM orders WHERE email = ? AND applied = 1 AND plan = ? AND grant_from <= ? AND grant_to > ? ORDER BY grant_to DESC LIMIT 1', email, e.plan, now, now)[0];
    const have = cur ? payTier(e.plan, cur.period) : 0;
    if (!cur || !have || !want) return { ok: true };
    const curName = `${e.planName}・${perName(cur.period)}`;
    /* 級別比現在高＝升級，可以買；同級＝到期前 PAY_RENEW_DAYS 天內才能續訂；比現在低一律擋（含年繳改月繳） */
    if (want > have) return { ok: true };
    if (want === have) return e.expires - now > PAY_RENEW_DAYS * DAY ? no('same_active', `你目前已是 ${curName}，到期日前 ${PAY_RENEW_DAYS} 天才能續訂。`) : { ok: true };
    return no(PAY_RANK[plan] < PAY_RANK[e.plan] ? 'lower_plan' : 'year_to_month', `你目前是 ${curName}，不能改買級別較低的方案（級別：Pro 年繳 > Pro 月繳 > Plus 年繳 > Plus 月繳）。`);
  };

  /* ---------------------------------------------------------------- 同一個 email 只留最新一件待處理的事（2026-10-16，docs/payment_admin_tabs_1016.md）
     Andy 10-16：「不應該發生 他待審核，另一個退款分頁還有這個人，一個mail 身份只能存在一個，若他有最新的一筆資訊，就只會留下最新的一筆」
     「待處理的事」只有兩種：銀行轉帳「待確認」（review）的訂單、還沒處理的取消／退款申請（sub_requests status='new'）。
     「訂單事件」＝會員真的送出錢的那一刻：銀行轉帳送出匯款資料的時間；綠界付款完成的時間（paid_at）。
       ① 待確認的轉帳，比最新的訂單事件舊 → 標「已被取代」（superseded；管理者在歷史裡照樣能確認入帳、退回、退款，錢不會卡住）
       ② 待處理的申請，比最新的訂單事件舊 → 自動結案（status='done'，close_reason＝已被新訂單 X 取代）
          管理者「改回待處理」過的申請，以改回的時間當它的時間（pinned），比那之前的訂單事件不會再把它結案
       ③ 同一個人好幾筆待處理的申請 → 只留最新那筆，舊的自動結案（管理者改回過的不動）
       ④ 申請比待確認的轉帳還新（10-16 之前留下的舊資料；之後新申請在有待確認訂單時會被擋）→ 那筆轉帳標「已被取代」
     每一次自動處理都寫 payEv（金流事件），可以查是誰、什麼時候、為什麼。全部是同步 SQL，冪等：重跑不會多做事。 */
  const RQN = { cancel: '取消訂閱', refund: '退款' };
  /* ---- 狀態機（docs/payment_admin_tabs_1016.md「處理措施」第 1 條）：管理者動作 → 允許的「目前狀態」。不在表裡的一律 409 bad_status。
     會員：送出匯款資料只准 pending → review；系統：排程 pending → expired／cancelled、綠界通知 → paid → active、規則 review → superseded。 */
  const PAY_FLOW = {
    confirm: ['review', 'expired', 'superseded'],             // → paid → active（或方案衝突停在 paid）
    reject: ['pending', 'review', 'expired', 'superseded'],    // → rejected
    amount: ['pending', 'review', 'expired', 'rejected', 'superseded'],
  };
  Hub.prototype.payLastBy = function (oid) {
    const e = this.q("SELECT at, kind, detail FROM pay_events WHERE oid = ? AND detail LIKE '%\"by\"%' ORDER BY id DESC LIMIT 1", oid)[0];
    if (!e) return {};
    let d = {}; try { d = JSON.parse(e.detail); } catch (x) { d = {}; }
    return { lastBy: d.by || '', lastAt: e.at, lastKind: e.kind };
  };
  /* 兩個管理者同時處理（第 3 條）：前端送「我看到的狀態」expect；跟伺服器現在的不一樣 → 409 stale，回現在的狀態與上一個動手的人 */
  Hub.prototype.payStale = function (o, b) {
    if (!b || !b.expect || b.expect === o.status) return null;
    return { error: 'stale', status: o.status, statusName: PAY_STATUS[o.status] || o.status, ...this.payLastBy(o.id), msg: `這筆已經是「${PAY_STATUS[o.status] || o.status}」（可能另一位管理者剛處理過），畫面已重新整理，請再確認一次。` };
  };
  /* 稽核（第 4 條）：管理者每個動作都記 誰（by）、何時（at）、做了什麼（kind）、前後狀態（from → to）*/
  Hub.prototype.payAudit = function (oid, kind, by, from, to, extra) { this.payEv(oid, kind, { by: norm(by), from: from || '', to: to || '', ...(extra || {}) }); };
  const repAt = (o) => { try { const a = JSON.parse(o.reports || '[]'); if (Array.isArray(a) && a.length && a[a.length - 1].at) return a[a.length - 1].at; } catch (e) { /* 略 */ } return o.updated || o.created || 0; };
  const evAt = (o) => (o.method === 'bank' ? (o.from_last5 ? repAt(o) : 0) : o.paid_at && (o.applied || ['paid', 'active', 'refunded'].includes(o.status)) ? Math.max(o.paid_at, o.created || 0) : 0);   // 綠界：付了錢才算；時間取「開單」與「付款」較晚的（綠界回的付款時間是台北時間字串，可能早於開單時間的毫秒）
  Hub.prototype.payReqClose = function (r, reason, by, oid) {
    this.q("UPDATE sub_requests SET status = 'done', close_reason = ?, closed_at = ?, closed_by = ? WHERE id = ? AND status = 'new'", String(reason).slice(0, 200), this.now(), by, r.id);
    this.payEv(oid || '', 'req_close', { req: r.id, type: r.type, email: r.email, reason, by, from: 'new', to: 'done' });
    /* 通知（第 5 條）：申請被結案，會員收到一則（同一筆申請只通知一次）*/
    this.payTell(r.email, `你的${RQN[r.type] || ''}申請已結案`, `你在 ${tpeStr(r.created || this.now())} 送出的${RQN[r.type] || ''}申請已結案：${reason}。\n如果你仍然需要${RQN[r.type] || ''}，請重新從帳號選單送出申請，或從右下角「客服」聯絡我們。`, 'rqc-' + r.id + '-' + (r.pinned || 0));
  };
  Hub.prototype.paySupersede = function (o, reason, by) {
    this.paySet(o.id, { status: 'superseded', reject_reason: reason });
    this.payEv(o.id, 'superseded', { reason, by });
    this.payTell(o.email, '你的一筆待確認訂單已被較新的資料取代', `你的訂單 ${o.id}（${o.plan_name}・${perName(o.period)}，NT$ ${o.amount}）${reason}，這筆不會再單獨審核。\n如果這兩筆你都已經匯款，請從網站右下角「客服」告訴我們，我們會退還多匯的款項。`, 'sup-' + o.id);
  };
  Hub.prototype.payReconcile = function (email) {
    this.payInit();
    const em = norm(email); if (!em) return 0;
    let n = 0;
    const evs = this.q('SELECT * FROM orders WHERE email = ? AND parent IS NULL', em).map((o) => ({ o, t: evAt(o) })).filter((x) => x.t).sort((a, b) => a.t - b.t);
    const top = evs[evs.length - 1];
    const ordName = (o) => `訂單 ${o.id}（${o.plan_name}・${perName(o.period)}）`;
    if (top) for (const x of evs) if (x !== top && x.o.status === 'review' && x.t <= top.t) { this.paySupersede(x.o, `已被較新的${ordName(top.o)}取代`, 'auto:' + top.o.id); n++; }
    const open = [];
    for (const r of this.q("SELECT * FROM sub_requests WHERE email = ? AND type IN ('cancel', 'refund') AND status = 'new' ORDER BY created, id", em)) {
      if (top && top.t > Math.max(r.created || 0, r.pinned || 0)) { this.payReqClose(r, `已被新${ordName(top.o)}取代`, 'auto', top.o.id); n++; } else open.push(r);
    }
    const R = open[open.length - 1];
    for (const r of open) if (r !== R && !r.pinned && (r.created || 0) <= (R.created || 0)) { this.payReqClose(r, `已被較新的${RQN[R.type] || ''}申請取代`, 'auto'); n++; }
    if (R) for (const x of evs) { const cur = this.payOrder(x.o.id); if (cur && cur.status === 'review' && (R.created || 0) > x.t) { this.paySupersede(cur, `已被較新的${RQN[R.type] || ''}申請取代`, 'auto:req:' + R.id); n++; } }
    return n;
  };
  /* 管理區打開清單時順手對全部有待處理事項的 email 跑一次（修正 10-16 之前留下來的重複）*/
  Hub.prototype.payReconcileAll = function () {
    this.payInit();
    let n = 0;
    for (const r of this.q("SELECT DISTINCT email FROM sub_requests WHERE type IN ('cancel', 'refund') AND status = 'new' UNION SELECT DISTINCT email FROM orders WHERE status = 'review' AND parent IS NULL")) n += this.payReconcile(r.email);
    return n;
  };
  /* 申請退款時建議退哪一筆：目前生效中的那筆（開通期間包含現在），沒有就最近開通的；全額退過的不算 */
  Hub.prototype.payRefundTarget = function (email) {
    const now = this.now();
    const os = this.q("SELECT id, grant_from, grant_to, confirmed_at, amount, recv_amount, refunded FROM orders WHERE email = ? AND applied = 1 AND status <> 'refunded' ORDER BY confirmed_at DESC", norm(email))
      .filter((o) => (o.refunded || 0) < (o.recv_amount || o.amount));
    return (os.find((o) => o.grant_from <= now && o.grant_to > now) || os[0] || {}).id || '';
  };

  /* ---------------------------------------------------------------- 價格（只信伺服器 plans）*/
  Hub.prototype.payPrice = function (planId, period) {
    if (!/^[a-z0-9_-]{1,20}$/.test(String(planId || '')) || planId === 'guest' || planId === 'free') return null;
    const p = this.plan(planId);
    if (!p || p.builtin) return null;
    const int = (v) => (Number.isInteger(v) && v > 0 ? v : null);
    const per = p.period || 'month';
    const amt = period === 'month' ? (per === 'month' ? int(p.price) : null)
      : period === 'year' ? (int(p.price_year) || (per === 'year' ? int(p.price) : null)) : null;
    return amt ? { plan: p.id, planName: p.name, period, amount: amt } : null;
  };
  Hub.prototype.payBank = function () {
    let b = null; try { b = JSON.parse(this.kv('pay_bank') || 'null'); } catch (e) { b = null; }
    return b && b.account && b.holder && b.bank_name ? b : null;
  };
  Hub.prototype.payNewId = function () {
    const t = new Date(this.now() + 8 * 3600 * 1000).toISOString();
    const s = t.slice(2, 4) + t.slice(5, 7) + t.slice(8, 10) + t.slice(11, 13) + t.slice(14, 16) + t.slice(17, 19);
    const A = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789', r = crypto.getRandomValues(new Uint8Array(4));
    return 'LG' + s + Array.from(r, (x) => A[x % A.length]).join('');   // 18 碼英數（綠界 MerchantTradeNo 上限 20）
  };
  Hub.prototype.payOrder = function (id) { return this.q('SELECT * FROM orders WHERE id = ?', String(id || ''))[0] || null; };
  /* 訂單開通時把暫存的性別算進計數（冪等：算完清成 NULL）。包在 try 裡：統計出任何問題都不能影響開通 */
  Hub.prototype.payCountGender = function (oid) {
    const o = this.payOrder(oid);
    if (!o || !o.applied || o.parent || !o.gender) return;
    if (GENDERS.includes(o.gender)) this.q('INSERT INTO gender_counts (day, g, n) VALUES (?, ?, 1) ON CONFLICT(day, g) DO UPDATE SET n = n + 1', tpeDay(this.now()), o.gender);
    this.q('UPDATE orders SET gender = NULL WHERE id = ?', oid);
  };
  /* 男女用量比例：只回彙總人數。paid＝已開通的首期付費訂單數（定期定額續扣不重複算）；
     沒有性別資料的（計數機制上線前的舊訂單、或客服人工開通的）＝ paid − 男 − 女，前端標「估算」。 */
  Hub.prototype.payGenderStats = function () {
    this.payInit();
    const r = this.q("SELECT COALESCE(SUM(CASE WHEN g = 'male' THEN n END), 0) AS male, COALESCE(SUM(CASE WHEN g = 'female' THEN n END), 0) AS female, MIN(day) AS since FROM gender_counts")[0];
    const paid = this.q('SELECT COUNT(*) AS c FROM orders WHERE applied = 1 AND parent IS NULL')[0].c;
    return { male: r.male, female: r.female, paid, unset: Math.max(0, paid - r.male - r.female), since: r.since || null };
  };
  const payOrigAdminStats = Hub.prototype.adminStats;
  Hub.prototype.adminStats = async function (req, b) {
    const res = await payOrigAdminStats.call(this, req, b);
    if (res.status !== 200) return res;
    const j = await res.json();
    j.gender = this.payGenderStats();
    return this.json(req, j);
  };
  Hub.prototype.paySet = function (id, set) {
    const ks = Object.keys(set); if (!ks.length) return;
    this.q(`UPDATE orders SET ${ks.map((k) => k + ' = ?').join(', ')}, updated = ? WHERE id = ?`, ...ks.map((k) => set[k]), this.now(), id);
  };

  /* ---------------------------------------------------------------- 開通（冪等）
     · 已開通（applied=1）的訂單一律不再加期間
     · 起算日：同方案且還沒到期 → 從目前到期日；否則（沒方案、已到期、換方案）→ 從現在
     · 月繳 +1 個月、年繳 +12 個月；這一筆開通了哪一段期間記在 grant_from～grant_to
     · 全部是同步 SQL（中間沒有 await）：Durable Object 單執行緒，兩個通知同時到也不會交錯 */
  Hub.prototype.payActivate = function (oid, src) {
    this.payInit();
    const o = this.payOrder(oid);
    if (!o) return { ok: false, error: 'not_found' };
    if (o.applied) return { ok: true, dup: true, order: o };
    try {
      const now = this.now(), email = norm(o.email);
      const cur = this.q('SELECT plan, over, expires FROM perm WHERE email = ?', email)[0];
      const months = o.period === 'year' ? 12 : 1;
      const same = cur && cur.plan === o.plan;
      /* 稽核 H7（2026-10-12）：目前有效方案等級較高 → 不准用較低方案蓋掉已付的期間；這筆停在「已入帳」進異常清單，管理者決定延長／轉換／退款 */
      const live = cur && cur.plan !== 'free' && (!cur.expires || cur.expires > now);
      const rc = live ? PAY_RANK[cur.plan] : 0, ro = PAY_RANK[o.plan];
      if (live && rc && ro && rc > ro) {
        this.paySet(o.id, { status: 'paid', anomaly: `方案衝突：會員目前是 ${cur.plan}（${cur.expires ? '到 ' + tpeDay(cur.expires) : '不到期'}），這筆 ${o.plan_name}・${o.period === 'year' ? '年繳' : '月繳'} 沒有開通；請決定延長、轉換或退款`, paid_at: o.paid_at || now });
        this.payEv(o.id, 'plan_conflict', { cur: cur.plan, exp: cur.expires });
        this.payTell(email, '已收到款項，專人處理中', `我們已收到你的訂單 ${o.id}（${o.plan_name}・${o.period === 'year' ? '年繳' : '月繳'}，NT$ ${o.recv_amount || o.amount}）的款項。\n因為你目前已有較高的方案（到 ${cur.expires ? tpeDay(cur.expires) : '不到期'}），這筆沒有自動開通，專人會在 1～2 個工作天內跟你聯絡（延長、轉換或退款）。`, 'conflict-' + o.id);
        return { ok: false, error: 'plan_conflict' };
      }
      /* 稽核 H9：升級（較低→較高）時舊方案剩餘期間不折抵 → 記一筆待處理，管理者決定是否部分退款 */
      const upNote = live && rc && ro && ro > rc && cur.expires ? `升級：舊方案 ${cur.plan} 還剩 ${Math.ceil((cur.expires - now) / DAY)} 天（到 ${tpeDay(cur.expires)}）沒有折抵，請決定是否部分退款舊方案` : null;
      if (same && !cur.expires && cur.plan !== 'free') {
        /* 管理者手動設成「不會到期」的同方案：不動到期日，只記這筆已開通 */
        this.paySet(o.id, { applied: 1, status: 'active', grant_from: now, grant_to: 0, confirmed_at: now, act_src: src, act_err: null, paid_at: o.paid_at || now });
        this.planEv(email, 'activate', o.plan, o.id, '同方案原本就不會到期');
        return { ok: true, order: this.payOrder(o.id) };
      }
      const from = same && cur.expires > now ? cur.expires : now;
      const to = addMonths(from, months);
      if (cur) this.q('UPDATE perm SET plan = ?, expires = ?, updated = ? WHERE email = ?', o.plan, to, now, email);
      else this.q('INSERT INTO perm (email, plan, over, updated, expires) VALUES (?, ?, ?, ?, ?)', email, o.plan, '{}', now, to);
      const bf = this.billFlags(email);
      if (!bf || !bf.first_paid) this.billUpsert(email, { first_paid: o.paid_at || now });
      this.paySet(o.id, { applied: 1, status: 'active', grant_from: from, grant_to: to, confirmed_at: now, act_src: src, act_err: null, paid_at: o.paid_at || now, ...(upNote ? { anomaly: upNote } : {}) });
      this.planEv(email, same && from > now ? 'extend' : 'activate', o.plan, o.id, `${tpeDay(from)}～${tpeDay(to)}（${src}）`);
      this.payEv(o.id, 'activate', { src, from, to });
      const per = o.period === 'year' ? '年繳' : '月繳', paid = o.recv_amount || o.amount;
      const kindT = upNote ? '升級完成' : same && from > now ? '續訂完成' : '付款完成，已開通';
      this.payTell(email, `${kindT}：${o.plan_name}・${per}`, `你的訂單 ${o.id} 已經${o.parent ? '自動扣款' : '付款'}完成。\n方案：${o.plan_name}・${per}${o.parent ? `（自動扣款第 ${o.period_n} 期）` : ''}\n金額：NT$ ${paid}\n使用期間：${tpeDay(from)} ～ ${tpeDay(to)}\n${upNote ? `\n你原本的方案 ${cur.plan} 還剩 ${Math.ceil((cur.expires - now) / DAY)} 天，這部分我們會另外跟你聯絡處理。\n` : ''}功能已經解鎖，重新整理網頁就生效。`, 'act-' + o.id);
      /* 2026-10-16：綠界訂閱（不含自動扣款的後續期）付款開通時也通知站方；轉帳單在會員送出匯款資料時已經通知過 */
      if (o.method === 'ecpay' && !o.parent) {
        const nm = ((this.q('SELECT name FROM users WHERE uid = ?', o.uid)[0] || {}).name || email);
        this.payNotifyOwner(`${nm} ${o.plan_name}（${per}） ${tpeDay(o.paid_at || now)}`,
          `有一筆綠界訂閱付款完成、已自動開通。\n\n訂單編號：${o.id}\n方案：${o.plan_name}（${per}${o.recur ? '・自動續訂' : ''}）\n金額：NT$ ${paid}\n付款方式：${o.pay_type || '綠界'}\n會員：${nm}\n會員 email：${email}\n使用期間：${tpeDay(from)} ～ ${tpeDay(to)}`, 'own-act-' + o.id);
      }
      return { ok: true, order: this.payOrder(o.id) };
    } catch (e) {
      this.paySet(o.id, { act_err: String(e && e.message || e).slice(0, 200) });
      return { ok: false, error: 'activate_failed' };
    }
  };

  /* 綠界付款成功（ReturnURL／查單／排程共用）：驗金額 → 記付款 → 開通 */
  Hub.prototype.payMarkPaid = function (o, info, src) {
    if (o.applied) return { ok: true, dup: true };
    /* 稽核 H1：綠界通知只能開綠界單（轉帳單一律走管理者確認）*/
    if (o.method !== 'ecpay') { this.payEv(o.id, 'notify_not_ecpay', info); return { ok: false, error: 'not_ecpay' }; }
    const amt = parseInt(info.amount, 10);
    const set = { trade_no: info.trade_no || o.trade_no, pay_type: info.pay_type || o.pay_type, paid_at: o.paid_at || info.paid_at || this.now(), rtn_msg: info.msg || o.rtn_msg };
    if (info.gwsr) set.gwsr = info.gwsr;
    /* 2026-10-11 Andy：已取消（未付款）或逾期的單，之後綠界才通知付款成功 → 照樣開通（錢收了），但列進異常清單讓管理者看 */
    if (['cancelled', 'expired', 'failed'].includes(o.status)) set.anomaly = `${PAY_STATUS[o.status] || o.status}之後才收到付款，已照樣開通，請確認`;
    if (o.recur) { set.period_state = o.period_state === 'cancelled' ? 'cancelled' : 'active'; set.period_n = Math.max(1, o.period_n || 0); }
    if (amt !== o.amount) {
      set.status = 'paid'; set.anomaly = `金額不符：綠界 ${info.amount}、訂單 ${o.amount}`;
      this.paySet(o.id, set); this.payEv(o.id, 'amount_mismatch', info);
      return { ok: false, error: 'amount_mismatch' };
    }
    set.status = 'paid';
    /* 稽核 H1：測試模式（沒設正式金鑰）用的是 repo 公開的測試金鑰，任何人都算得出驗章碼 → 只記付款、不寫權限；
       只有本機 devserver（ECPAY_STAGE_HOST）或明確打開 PAY_TEST_ACTIVATE 才准開通 */
    if (this.ecCfg().test && !this.env.ECPAY_STAGE_HOST && String(this.env.PAY_TEST_ACTIVATE || '') !== '1') {
      set.anomaly = '測試模式付款：沒有設定正式金鑰，不自動開通（防偽造通知）';
      this.paySet(o.id, set); this.payEv(o.id, 'test_no_activate', info);
      return { ok: false, error: 'test_mode' };
    }
    this.paySet(o.id, set);
    const res = this.payActivate(o.id, src);
    /* 10-16：綠界付款完成也是「新訂單事件」→ 同一個 email 比它舊的待確認轉帳、待處理申請自動處理 */
    if (!o.parent) this.payReconcile(o.email);
    return res;
  };

  /* 主動查單（QueryTradeInfo/V5，回應要驗章）*/
  Hub.prototype.payQuery = async function (oid, src) {
    this.payInit();
    const o = this.payOrder(oid);
    if (!o || o.method !== 'ecpay' || o.parent) return { ok: false, error: 'not_ecpay' };
    if (o.applied) return { ok: true, dup: true };
    let r;
    try { r = await this.ecPost('/Cashier/QueryTradeInfo/V5', { MerchantTradeNo: o.id, TimeStamp: ts(this) }); } catch (e) { return { ok: false, error: 'network' }; }
    this.paySet(o.id, { last_sync: this.now() });
    if (!(await this.ecVerify(r.form))) { this.payEv(o.id, 'query_badmac', evSafe(r.text)); return { ok: false, error: 'bad_mac' }; }
    const f = r.form;
    this.payEv(o.id, 'query', { TradeStatus: f.TradeStatus, TradeAmt: f.TradeAmt, PaymentType: f.PaymentType });
    const o2 = this.payOrder(o.id);
    if (o2.applied) return { ok: true, dup: true };
    if (String(f.TradeStatus) === '1') {
      return this.payMarkPaid(o2, { amount: f.TradeAmt, trade_no: f.TradeNo, pay_type: f.PaymentType, paid_at: parseTpe(f.PaymentDate) || this.now(), msg: '查單：已付款' }, src);
    }
    if (String(f.TradeStatus) !== '0' && o2.status === 'pending') this.paySet(o.id, { status: 'failed', rtn_msg: `查單：交易狀態 ${f.TradeStatus}` });
    return { ok: false, error: 'unpaid', status: f.TradeStatus };
  };

  /* 定期定額每一期（通知或對帳補的）：子訂單 id＝母單＋P＋期數 → INSERT OR IGNORE，同一期只會開通一次 */
  Hub.prototype.payPeriodCharge = function (p, n, info, src) {
    if (n <= 1) {
      const o = this.payOrder(p.id);
      return o.applied ? { ok: true, dup: true } : this.payMarkPaid(o, { ...info, amount: info.amount }, src);
    }
    const cid = p.id + 'P' + n;
    const exists = this.payOrder(cid);
    if (exists && exists.applied) return { ok: true, dup: true };
    if (!exists) {
      this.q(`INSERT OR IGNORE INTO orders (id, uid, email, plan, plan_name, period, amount, method, recur, parent, period_n, status, trade_no, pay_type, paid_at, test, created, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'ecpay', 1, ?, ?, 'paid', ?, 'Credit_CreditCard', ?, ?, ?, ?)`,
      cid, p.uid, p.email, p.plan, p.plan_name, p.period, parseInt(info.amount, 10) || p.amount, p.id, n, info.trade_no || '', info.paid_at || this.now(), p.test, this.now(), this.now());
    }
    if (n > (p.period_n || 0)) this.paySet(p.id, { period_n: n });
    const c = this.payOrder(cid);
    /* 稽核 H8：這個定期定額之後會員又買了別的（升級／改年繳）→ 這期不開通（不准蓋回舊方案），列異常、排程會去終止 */
    const sup = this.paySuperseding(p);
    if (sup && !c.applied) { this.paySet(cid, { anomaly: `舊的定期定額照扣：會員已改買 ${sup.plan_name}（訂單 ${sup.id}），這期沒有開通，請退款並確認已終止自動扣款` }); return { ok: false, error: 'superseded' }; }
    if ((parseInt(info.amount, 10) || p.amount) !== p.amount) { this.paySet(cid, { anomaly: `金額不符：綠界 ${info.amount}、訂單 ${p.amount}` }); return { ok: false, error: 'amount_mismatch' }; }
    return c.applied ? { ok: true, dup: true } : this.payActivate(cid, src);
  };
  /* 這個定期定額母單之後，同一會員有沒有「別張單」開通（不是自己的子單）→ 有就代表舊的自動扣款該停了 */
  Hub.prototype.paySuperseding = function (p) {
    return this.q("SELECT * FROM orders WHERE email = ? AND applied = 1 AND id <> ? AND (parent IS NULL OR parent <> ?) AND confirmed_at > ? ORDER BY confirmed_at DESC LIMIT 1", p.email, p.id, p.id, p.confirmed_at || 0)[0] || null;
  };
  /* 定期定額對帳（QueryCreditCardPeriodInfo；回 JSON）*/
  Hub.prototype.payPeriodSync = async function (oid, src) {
    this.payInit();
    const p = this.payOrder(oid);
    if (!p || !p.recur || p.parent) return { ok: false, error: 'not_period' };
    let r;
    try { r = await this.ecPost('/Cashier/QueryCreditCardPeriodInfo', { MerchantTradeNo: p.id, TimeStamp: ts(this) }); } catch (e) { return { ok: false, error: 'network' }; }
    this.paySet(p.id, { last_sync: this.now() });
    let j = null; try { j = JSON.parse(r.text); } catch (e) { j = null; }
    if (!j || String(j.MerchantTradeNo || p.id) !== p.id) { this.payEv(p.id, 'period_query_bad', evSafe(r.text)); return { ok: false, error: 'bad_reply' }; }
    this.payEv(p.id, 'period_query', { ExecStatus: j.ExecStatus, TotalSuccessTimes: j.TotalSuccessTimes, PeriodAmount: j.PeriodAmount });
    const n = parseInt(j.TotalSuccessTimes, 10) || 0;
    const amt = parseInt(j.PeriodAmount, 10) || p.amount;
    let added = 0;
    for (let i = 1; i <= Math.min(n, 120); i++) {
      const before = i === 1 ? this.payOrder(p.id).applied : (this.payOrder(p.id + 'P' + i) || {}).applied;
      if (before) continue;
      const res = this.payPeriodCharge(this.payOrder(p.id), i, { amount: i === 1 ? (parseInt(j.amount, 10) || amt) : amt, gwsr: i === 1 ? String(j.gwsr || '') : '', paid_at: i === 1 ? parseTpe(j.process_date) || this.now() : this.now(), msg: '對帳補登' }, src);
      if (res.ok && !res.dup) added++;
    }
    if (String(j.ExecStatus) === '0' && p.period_state !== 'cancelled') this.paySet(p.id, { period_state: 'cancelled', cancel_at: p.cancel_at || this.now() });
    return { ok: true, added, n };
  };

  /* 定期定額終止（CreditCardPeriodAction Action=Cancel）。綠界回 RtnCode=1 才算成功 */
  Hub.prototype.payPeriodCancel = async function (oid, by) {
    const p = this.payOrder(oid);
    if (!p || !p.recur || p.parent) return { ok: false, error: 'not_period' };
    if (p.period_state === 'cancelled') return { ok: true, dup: true };
    let r;
    try { r = await this.ecPost('/Cashier/CreditCardPeriodAction', { MerchantTradeNo: p.id, Action: 'Cancel', TimeStamp: ts(this) }); } catch (e) { return { ok: false, error: 'network', msg: '連不到綠界' }; }
    this.payEv(p.id, 'period_cancel', evSafe(r.text));
    if (r.form.CheckMacValue && !(await this.ecVerify(r.form))) return { ok: false, error: 'bad_mac', msg: '綠界回應驗章失敗' };
    if (String(r.form.RtnCode) !== '1') return { ok: false, error: 'ecpay', msg: r.form.RtnMsg || `HTTP ${r.status}` };
    this.paySet(p.id, { period_state: 'cancelled', cancel_at: this.now() });
    this.planEv(p.email, 'auto_renew_off', p.plan, p.id, by || '');
    { const e2 = this.effective(norm(p.email)); this.payTell(p.email, '信用卡自動扣款已停止', `你的訂單 ${p.id}（${p.plan_name}・${p.period === 'year' ? '年繳' : '月繳'}）的信用卡自動扣款已經停止，之後不會再扣款。${e2.expires && !e2.expired ? `\n已付的期間照常用到 ${tpeDay(e2.expires)}。` : ''}`, 'pc-' + p.id); }
    return { ok: true };
  };

  /* ---------------------------------------------------------------- 到期降級紀錄（權限本身由 effective() 以 perm.expires 判斷）*/
  Hub.prototype.payExpireLog = function () {
    this.payInit();
    const now = this.now();
    /* 退款「立即降級」那一刻已經記過「退款降級」→ 不再重複記「到期降級」 */
    for (const r of this.q(`SELECT email, plan, expires FROM perm p WHERE expires IS NOT NULL AND expires > 0 AND expires <= ? AND plan <> 'free' AND expires > ?
      AND NOT EXISTS (SELECT 1 FROM plan_events e WHERE e.email = p.email AND e.kind = 'refund_downgrade' AND e.at BETWEEN p.expires - 60000 AND p.expires + 60000)`, now, now - 400 * DAY)) {
      this.planEv(r.email, 'expire', r.plan, String(r.expires), `到期日 ${tpeDay(r.expires)} 已過，自動回到註冊會員`);
      this.payTell(r.email, '方案已到期', `你的方案已在 ${tpeDay(r.expires)} 到期，帳號回到註冊會員。想繼續使用，到網站「訂閱方案」重新訂閱即可。`, 'exp-' + r.email + '-' + r.expires);
    }
    this.q("UPDATE orders SET status = 'expired', updated = ? WHERE method = 'bank' AND status = 'pending' AND created < ?", now, now - PAY_BANK_DAYS * DAY);
    this.q("UPDATE orders SET status = 'cancelled', rtn_msg = '超過 3 天未付款，自動取消', updated = ? WHERE method = 'ecpay' AND status = 'pending' AND applied = 0 AND parent IS NULL AND created < ?", now, now - PAY_ECPAY_EXPIRE_DAYS * DAY);
  };
  /* 排程（每 10 分鐘，wrangler.toml）：補開通 → 對帳 → 到期紀錄 */
  /* 開通後把暫存性別算進計數（要放在 payActivate 定義之後才包得到） */
  const payOrigActivate = Hub.prototype.payActivate;
  Hub.prototype.payActivate = function (oid, src) {
    const r = payOrigActivate.call(this, oid, src);
    try { this.payCountGender(oid); } catch (e) { /* 統計失敗不影響開通 */ }
    return r;
  };
  Hub.prototype.paySweep = async function () {
    this.payInit();
    const now = this.now(), out = { query: 0, fixed: 0, period: 0 };
    /* 沒付款的訂單不留性別：14 天還沒開通就清掉暫存 */
    this.q('UPDATE orders SET gender = NULL WHERE gender IS NOT NULL AND applied = 0 AND created < ?', now - 14 * DAY);
    for (const o of this.q("SELECT id FROM orders WHERE method = 'ecpay' AND parent IS NULL AND applied = 0 AND status IN ('pending', 'paid', 'cancelled') AND created > ? ORDER BY created LIMIT 30", now - (PAY_SWEEP_DAYS + 1) * DAY)) {
      out.query++;
      const r = await this.payQuery(o.id, 'sweep');
      if (r.ok && !r.dup) out.fixed++;
    }
    for (const o of this.q("SELECT id FROM orders WHERE method = 'ecpay' AND recur = 1 AND parent IS NULL AND applied = 1 AND period_state = 'active' AND (last_sync IS NULL OR last_sync < ?) ORDER BY last_sync LIMIT 20", now - PAY_PERIOD_SYNC_MS)) {
      const r = await this.payPeriodSync(o.id, 'sweep');
      if (r.ok) out.period += r.added;
    }
    /* 稽核 H8／H14：被新訂單取代的定期定額 → 自動向綠界終止；失敗留在異常清單，下次排程再試 */
    for (const p of this.q("SELECT * FROM orders WHERE method = 'ecpay' AND recur = 1 AND parent IS NULL AND applied = 1 AND period_state = 'active' LIMIT 50")) {
      const sup = this.paySuperseding(p);
      const refunded = p.refunded > 0;
      if (!sup && !refunded) continue;
      const r = await this.payPeriodCancel(p.id, sup ? 'superseded:' + sup.id : 'refund_retry');
      if (!r.ok) this.paySet(p.id, { anomaly: `自動扣款還沒停：${sup ? '會員已改買 ' + sup.plan_name : '已退款'}，向綠界終止失敗（${r.msg || r.error}），排程會重試；也可到綠界後台手動終止` });
      else out.cancelled = (out.cancelled || 0) + 1;
    }
    this.payExpireLog();
    try { out.mail = await this.payMailFlush(); } catch (e) { /* 寄信失敗下次再試 */ }
    return out;
  };

  /* ---------------------------------------------------------------- 輸出給前端的訂單 */
  const pubOrder = (o, refunds) => ({
    id: o.id, plan: o.plan, planName: o.plan_name, period: o.period, amount: o.amount, method: o.method, recur: !!o.recur, parent: o.parent || null,
    periodN: o.period_n || 0, periodState: o.period_state || '', status: o.status, statusName: PAY_STATUS[o.status] || o.status,
    payType: o.pay_type || '', payInfo: (() => { try { return JSON.parse(o.pay_info || 'null'); } catch (e) { return null; } })(),
    payerName: o.payer_name || '', last5: o.from_last5 || '', xferDate: o.xfer_date || '', xferAmount: o.xfer_amount || 0, note: o.note || '', rejectReason: o.reject_reason || '',
    reports: (() => { try { const a = JSON.parse(o.reports || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; } })(),
    recvAmount: o.recv_amount || 0,
    grantFrom: o.grant_from || 0, grantTo: o.grant_to || 0, refunded: o.refunded || 0, test: !!o.test,
    created: o.created, paidAt: o.paid_at || 0, confirmedAt: o.confirmed_at || 0, cancelAt: o.cancel_at || 0,
    refunds: (refunds || []).filter((r) => r.oid === o.id && r.status === 'done').map((r) => ({ amount: r.amount, at: r.done_at || r.created, kind: r.kind })),
  });
  const admOrder = (o, refunds, names) => ({ ...pubOrder(o, refunds), email: o.email, name: (names && names[o.uid]) || '', payerLast5: o.payer_last5 || '', adminNote: o.admin_note || '', actSrc: o.act_src || '',
    actErr: o.act_err || '', anomaly: o.anomaly || '', tradeNo: o.trade_no || '', gwsr: o.gwsr || '', rtnMsg: o.rtn_msg || '', applied: !!o.applied,
    refundRows: (refunds || []).filter((r) => r.oid === o.id) });

  Hub.prototype.payMine = function (v) {
    const email = norm(v.user.email), now = this.now();
    const all = this.q('SELECT * FROM orders WHERE uid = ? OR email = ? ORDER BY created DESC LIMIT 300', v.user.uid, email);
    /* 2026-10-11 Andy：「只要還沒付費 就不能出現這樣 只有真的付費了 才能變更當前會員狀態」→ 會員端只列真的付過錢的：
       已付款／已開通／已退款／部分退款，以及銀行轉帳「已送出匯款資料」的（待確認、被退回看得到原因）。綠界待付款、未完成付款一律不列。 */
    const rows = all.filter((o) => o.applied || ['paid', 'active', 'refunded'].includes(o.status) || o.refunded > 0
      || (o.method === 'bank' && o.from_last5 && ['review', 'rejected', 'superseded'].includes(o.status)));
    const refunds = this.q('SELECT * FROM refunds WHERE email = ?', email);
    const e = this.effective(email);
    const plan = e.expired ? 'free' : e.plan;
    const active = rows.find((o) => !o.parent && o.recur && o.applied && o.period_state === 'active' && o.plan === plan);
    let renew = null;
    if (plan !== 'free' && e.expires && e.expires > now && e.expires - now <= PAY_RENEW_DAYS * DAY && !active) {
      const last = rows.find((o) => o.applied && o.plan === plan);
      const per = last ? last.period : 'month';
      const pr = this.payPrice(plan, per);
      const days = Math.max(0, Math.ceil((e.expires - now) / DAY));
      renew = { plan, planName: e.planName, period: per, amount: pr ? pr.amount : null, expires: e.expires, days, stage: days <= 1 ? 1 : 7, method: last ? last.method : '' };
    }
    const reqs = this.q("SELECT id, type, plan, note, created, status, close_reason AS closeReason, closed_by AS closedBy FROM sub_requests WHERE uid = ? AND type IN ('cancel', 'refund') ORDER BY created DESC LIMIT 50", v.user.uid);
    return { reqs, orders: rows.map((o) => pubOrder(o, refunds)), plan, planName: e.planName, expires: e.expires || 0, autoRenew: !!active, autoRenewId: active ? active.id : '', renew, test: this.ecCfg().test, now };
  };

  /* ---------------------------------------------------------------- 會員訂閱清單（管理區）*/
  Hub.prototype.paySubs = function () {
    const now = this.now();
    const orders = this.q('SELECT * FROM orders WHERE applied = 1 OR refunded > 0 ORDER BY created');
    const refunds = this.q("SELECT oid, email, amount, done_at FROM refunds WHERE status = 'done'");
    const by = new Map();
    for (const o of orders) { if (!by.has(o.email)) by.set(o.email, []); by.get(o.email).push(o); }
    const out = [];
    for (const [email, os] of by) {
      const e = this.effective(email);
      const plan = e.expired ? 'free' : e.plan;
      const last = os[os.length - 1];
      const rec = os.filter((o) => !o.parent && o.recur).pop();
      const paid = os.filter((o) => o.paid_at);
      const refundSum = refunds.filter((r) => r.email === email).reduce((s, r) => s + r.amount, 0);
      const cur = os.filter((o) => o.grant_to && o.grant_from <= now && o.grant_to > now).pop() || last;
      out.push({
        email, plan, planName: e.planName, expired: !!e.expired, method: rec && rec.period_state === 'active' ? 'period' : last.method === 'bank' ? 'bank' : 'once',
        lastMethod: last.method, recur: !!(rec && rec.applied), autoRenew: !!(rec && rec.period_state === 'active'), autoRenewId: rec ? rec.id : '',
        firstPaid: paid.length ? Math.min(...paid.map((o) => o.paid_at)) : 0, lastPaid: paid.length ? Math.max(...paid.map((o) => o.paid_at)) : 0,
        period: last.period, curFrom: cur ? cur.grant_from || 0 : 0, expires: e.expires || 0,
        downgradeAt: rec && rec.period_state === 'active' ? 0 : e.expires || 0,
        total: os.reduce((s, o) => s + (o.applied ? o.amount : 0), 0) - refundSum, refunded: refundSum, count: os.filter((o) => o.applied).length,
      });
    }
    return out.sort((a, b) => (b.lastPaid || 0) - (a.lastPaid || 0));
  };

  /* ---------------------------------------------------------------- 退款試算（照 #refund 政策）
     · 首次付款 7 天內、沒用過退款保證 → 全額
     · 其他 → 依這一筆開通期間的未使用日數比例（第六節「按未使用日數比例」）；管理者可以改金額 */
  Hub.prototype.payRefundQuote = function (o) {
    const now = this.now();
    const done = this.q("SELECT COALESCE(SUM(amount), 0) AS s FROM refunds WHERE oid = ? AND status = 'done'", o.id)[0].s;
    /* 稽核 H4：轉帳單以管理者確認的實收金額為準（多收的也能退；少收的不會多退）*/
    const base = o.method === 'bank' && o.recv_amount ? o.recv_amount : o.amount;
    const left = base - done;
    const bf = this.billFlags(o.email) || {};
    const first = bf.first_paid || o.paid_at || 0;
    let suggest = left, rule = '';
    /* 稽核 H11：七天以「會員申請退款的時間」為準（申請時間在七天內，管理者晚幾天處理也一樣全額）*/
    const asked = bf.refund_req_at || 0;
    if (!o.applied) { rule = '這筆沒有開通過（已被取代／未確認）：收到的錢全額退回'; }
    else if (first && (now - first <= 7 * DAY || (asked && asked - first <= 7 * DAY)) && !bf.refund_used) { rule = '首次付款 7 天內：全額退款保證' + (asked && now - first > 7 * DAY ? '（以申請日為準）' : ''); }
    else if (o.grant_to && o.grant_from && o.grant_to > now) {
      const ratio = Math.max(0, Math.min(1, (o.grant_to - Math.max(now, o.grant_from)) / (o.grant_to - o.grant_from)));
      suggest = Math.min(left, Math.round(base * ratio)); rule = `超過 7 天：依未使用日數比例（剩 ${Math.ceil((o.grant_to - now) / DAY)} 天）`;
    } else { suggest = 0; rule = '這一筆的期間已經用完，政策上不退（可手動改金額）'; }
    const credit = o.method === 'ecpay' && /^Credit/.test(o.pay_type || '');
    return { base, left, suggest, rule, kind: credit ? 'ecpay' : 'manual', test: !!o.test || this.ecCfg().test, recur: !!o.recur && !o.parent, periodActive: o.period_state === 'active' };
  };
  /* 信用卡退款：判斷授權／關帳階段 → 選 Action（N 放棄、C 改關帳金額、R 退刷）。
     有 ECPAY_CREDIT_CHECK_CODE＋gwsr 就查 CreditDetail/QueryTrade/V2 拿真實狀態；沒有就用「每日 20:00 自動關帳」推估（docs 第 6 節）。*/
  Hub.prototype.payCreditRefund = async function (o, amount) {
    const c = this.ecCfg();
    const full = amount >= o.amount - (this.q("SELECT COALESCE(SUM(amount), 0) AS s FROM refunds WHERE oid = ? AND status = 'done'", o.id)[0].s);
    let stage = '';
    if (this.env.ECPAY_CREDIT_CHECK_CODE && o.gwsr) {
      try {
        const q = await this.ecPost('/CreditDetail/QueryTrade/V2', { CreditRefundId: o.gwsr, CreditAmount: String(o.amount), CreditCheckCode: String(this.env.ECPAY_CREDIT_CHECK_CODE) });
        const st = (() => { try { const j = JSON.parse(q.text); return String((j.RtnValue && j.RtnValue.status) || j.status || ''); } catch (e) { return ''; } })();
        stage = /已關帳/.test(st) ? 'closed' : /要關帳/.test(st) ? 'closing' : st ? 'auth' : '';
        this.payEv(o.id, 'credit_query', st || evSafe(q.text));
      } catch (e) { stage = ''; }
    }
    if (!stage) {
      /* 推估：付款時間早於「最近一次已經過去的台北 20:00」→ 已關帳；否則還在授權階段 */
      const now = this.now(), d = new Date(now + 8 * 3600 * 1000);
      let cut = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), 20 - 8, 0, 0);
      if (cut > now) cut -= DAY;
      stage = (o.paid_at || 0) < cut ? 'closed' : 'auth';
    }
    const doneSum = this.q("SELECT COALESCE(SUM(amount), 0) AS s FROM refunds WHERE oid = ? AND status = 'done'", o.id)[0].s;
    /* 稽核 H6：關帳前（授權階段）只准做一次部分退款；第二次要等關帳後走退刷，避免關帳金額算錯 */
    if (stage !== 'closed' && !full && doneSum > 0) return { ok: false, action: 'C', msg: '這筆今天已經部分退過一次，請等今晚 20:00 關帳後（明天）再退剩下的' };
    const steps = stage === 'closed' ? [['R', amount]] : stage === 'closing' ? (full ? [['E', o.amount], ['N', o.amount]] : [['C', o.amount - amount]]) : (full ? [['N', o.amount]] : [['C', o.amount - amount]]);
    for (const [act, amt] of steps) {
      const r = await this.ecPost('/CreditDetail/DoAction', { MerchantTradeNo: o.id, TradeNo: o.trade_no || '', Action: act, TotalAmount: String(amt) }, c.test ? c.host : ECPAY_PROD_HOST);
      this.payEv(o.id, 'doaction_' + act, evSafe(r.text));
      if (r.form.CheckMacValue && !(await this.ecVerify(r.form))) return { ok: false, action: act, msg: '綠界回應驗章失敗' };
      if (String(r.form.RtnCode) !== '1') return { ok: false, action: act, msg: r.form.RtnMsg || `HTTP ${r.status}` };
    }
    return { ok: true, action: steps.map((s) => s[0]).join('+'), stage };
  };

  /* ---------------------------------------------------------------- 會員 API（JSON，走 subRoutes：Origin 白名單＋權杖）*/
  const consentOf = (b) => JSON.stringify({ at: subClean(b.consent_at, 40), ver: subClean(b.consent_version, 40), c: subClean(b.consent, 80) });
  const backOk = (hub, back) => { try { const u = new URL(String(back || '')); return hub.originOk(u.origin) ? u.origin + u.pathname : ''; } catch (e) { return ''; } };
  const newCount = (hub, uid, method) => hub.q('SELECT COUNT(*) AS c FROM orders WHERE uid = ? AND method = ? AND parent IS NULL AND created > ?', uid, method, hub.now() - DAY)[0].c;
  /* 個人帳務通知併進 /v1/notices（前端鈴鐺不用改資料流）；已讀一樣走 /v1/notices/read */
  const origNotices = Hub.prototype.subRoutes['/v1/notices'], origRead = Hub.prototype.subRoutes['/v1/notices/read'];
  const unOut = (r) => ({ id: r.id, title: r.title, body: r.body, kind: 'pay', audience: 'me', start: r.created, end: 0, pinned: false, created: r.created, updated: r.created, read: !!r.read_at });
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/notices': async function (req, b) {
      const res = await origNotices.call(this, req, b);
      if (res.status !== 200 || !b || !b.t) return res;
      const v = await this.auth(req, b); if (!v) return res;
      this.payInit();
      const j = await res.clone().json();
      const mine = this.q('SELECT * FROM user_notices WHERE email = ? ORDER BY created DESC LIMIT 50', norm(v.user.email)).map(unOut);
      return this.json(req, { ...j, notices: mine.concat(j.notices || []).sort((x, y) => (y.pinned - x.pinned) || (y.start - x.start)) });
    },
    '/v1/notices/read': async function (req, b) {
      const v = b && b.t ? await this.auth(req, b) : null;
      if (v && Array.isArray(b.ids)) { this.payInit(); for (const id of b.ids.slice(0, 200)) if (typeof id === 'string' && id[0] === 'u') this.q('UPDATE user_notices SET read_at = COALESCE(read_at, ?) WHERE id = ? AND email = ?', this.now(), id, norm(v.user.email)); }
      const res = await origRead.call(this, req, b);
      if (res.status !== 200 || !v) return res;
      const j = await res.clone().json();
      return this.json(req, { ...j, read: (j.read || []).concat(this.q('SELECT id FROM user_notices WHERE email = ? AND read_at IS NOT NULL', norm(v.user.email)).map((r) => r.id)) });
    },
    '/v1/admin/pay/mail': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      return this.json(req, { on: !!(this.env.RESEND_API_KEY && this.env.MAIL_FROM), notices: this.q('SELECT n.id, n.email, n.title, n.created, n.read_at, m.status AS mail, m.msg AS mail_msg, m.sent_at FROM user_notices n LEFT JOIN mail_out m ON m.id = n.id ORDER BY n.created DESC LIMIT 500') });
    },
  });
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/pay/quote': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.payInit();
      const pr = this.payPrice(String(b.plan || ''), b.period === 'year' ? 'year' : 'month');
      if (!pr) return this.json(req, { error: 'no_price' }, 400);
      const bank = this.payBank();
      const chk = this.payChangeCheck(norm(v.user.email), pr.plan, pr.period);
      return this.json(req, { ...pr, blocked: chk.ok ? '' : chk.reason, blockedMsg: chk.ok ? '' : chk.msg, test: this.ecCfg().test, bank: bank ? { ...bank, days: PAY_BANK_DAYS } : null, recurOk: true });
    },
    '/v1/pay/ecpay/create': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.payInit();
      const period = b.period === 'year' ? 'year' : b.period === 'month' ? 'month' : null;
      const pr = period && this.payPrice(String(b.plan || ''), period);
      if (!pr) return this.json(req, { error: 'no_price' }, 400);
      const chkE = this.payChangeCheck(norm(v.user.email), pr.plan, period);
      if (!chkE.ok) return this.json(req, { error: 'blocked', reason: chkE.reason, msg: chkE.msg }, 409);
      if (newCount(this, v.user.uid, 'ecpay') >= PAY_MAX_ECPAY_DAY) return this.json(req, { error: 'too_many' }, 429);
      const back = backOk(this, b.back);
      if (!back) return this.json(req, { error: 'bad_back' }, 400);
      const recur = b.recur === true;
      const prof = payProfile(b, subClean, { last5: true });
      if (prof.error) return this.json(req, { error: prof.error }, 400);
      const c = this.ecCfg(), id = this.payNewId(), now = this.now();
      /* 同一個會員重新點結帳：舊的未付款綠界單作廢，不讓它一直累積（綠界的 MerchantTradeNo 送出過就不能重用，所以是建新單）。
         已經取號（ATM 帳號／超商代碼）的留著，等 3 天排程；作廢的單如果之後綠界才通知付款成功，照樣開通＋列異常。 */
      this.q("UPDATE orders SET status = 'cancelled', rtn_msg = '重新結帳，舊的未付款訂單作廢', updated = ? WHERE uid = ? AND method = 'ecpay' AND status = 'pending' AND applied = 0 AND parent IS NULL AND (pay_info IS NULL OR pay_info = '')", now, v.user.uid);
      const api = new URL(req.url).origin;
      this.q(`INSERT INTO orders (id, uid, email, plan, plan_name, period, amount, method, recur, status, test, back, consent, note, created, updated, period_state)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'ecpay', ?, 'pending', ?, ?, ?, ?, ?, ?, ?)`, id, v.user.uid, norm(v.user.email), pr.plan, pr.planName, period, pr.amount,
      recur ? 1 : 0, c.test ? 1 : 0, back, consentOf(b), subClean(b.note, 120), now, now, recur ? 'new' : null);
      const f = {
        MerchantID: c.id, MerchantTradeNo: id, MerchantTradeDate: tpeStr(now), PaymentType: 'aio', TotalAmount: String(pr.amount),
        TradeDesc: '哩股哩股訂閱', ItemName: `${pr.planName} ${period === 'year' ? '年繳' : '月繳'}${recur ? '（自動續扣）' : ''}`.slice(0, 200),
        ReturnURL: api + '/v1/pay/ecpay/notify', ChoosePayment: recur ? 'Credit' : 'ALL', EncryptType: '1',
        ClientBackURL: back + '#orders/' + id, OrderResultURL: api + '/v1/pay/ecpay/result', NeedExtraPaidInfo: 'Y',
      };
      if (recur) Object.assign(f, { PeriodAmount: String(pr.amount), PeriodType: period === 'year' ? 'Y' : 'M', Frequency: '1', ExecTimes: period === 'year' ? '9' : '99', PeriodReturnURL: api + '/v1/pay/ecpay/period' });
      else f.PaymentInfoURL = api + '/v1/pay/ecpay/notify';
      f.CheckMacValue = await ecpayMac(f, c.key, c.iv);
      this.paySet(id, { payer_name: prof.name, gender: prof.gender || null, payer_last5: prof.last5 });
      this.payEv(id, 'create', { recur, amount: pr.amount });
      return this.json(req, { ok: true, id, amount: pr.amount, test: c.test, action: c.host + '/Cashier/AioCheckOut/V5', fields: f });
    },
    '/v1/pay/bank/create': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.payInit();
      const bank = this.payBank(); if (!bank) return this.json(req, { error: 'bank_off' }, 409);
      const period = b.period === 'year' ? 'year' : b.period === 'month' ? 'month' : null;
      const pr = period && this.payPrice(String(b.plan || ''), period);
      if (!pr) return this.json(req, { error: 'no_price' }, 400);
      const chkB = this.payChangeCheck(norm(v.user.email), pr.plan, period);
      if (!chkB.ok) return this.json(req, { error: 'blocked', reason: chkB.reason, msg: chkB.msg }, 409);
      const now = this.now();
      /* 同方案同週期、3 天內還沒回報的待付款單 → 沿用（切分頁、重新打開不會一直開新單）*/
      const old = this.q("SELECT * FROM orders WHERE uid = ? AND method = 'bank' AND status = 'pending' AND plan = ? AND period = ? AND created > ? ORDER BY created DESC LIMIT 1", v.user.uid, pr.plan, period, now - PAY_BANK_DAYS * DAY)[0];
      if (old) return this.json(req, { ok: true, id: old.id, amount: old.amount, reused: true, deadline: old.created + PAY_BANK_DAYS * DAY, bank: { ...bank, days: PAY_BANK_DAYS } });
      if (newCount(this, v.user.uid, 'bank') >= PAY_MAX_NEW_DAY) return this.json(req, { error: 'too_many' }, 429);
      const id = this.payNewId();
      this.q(`INSERT INTO orders (id, uid, email, plan, plan_name, period, amount, method, status, test, consent, created, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'bank', 'pending', 0, ?, ?, ?)`, id, v.user.uid, norm(v.user.email), pr.plan, pr.planName, period, pr.amount, consentOf(b), now, now);
      this.payEv(id, 'create', { amount: pr.amount });
      return this.json(req, { ok: true, id, amount: pr.amount, deadline: now + PAY_BANK_DAYS * DAY, bank: { ...bank, days: PAY_BANK_DAYS } });
    },
    '/v1/pay/bank/report': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.payInit();
      const o = this.payOrder(b.id);
      if (!o || o.uid !== v.user.uid || o.method !== 'bank') return this.json(req, { error: 'not_found' }, 404);
      /* 2026-10-16 Andy：「拿掉補送匯款資料這功能」→ 一張單只收一次匯款資料（已送出就不能再送；送錯請用意見回饋聯絡，管理者可改金額或退回）*/
      if (o.status === 'review') return this.json(req, { error: 'already_reported', status: o.status }, 409);
      if (o.status !== 'pending') return this.json(req, { error: 'bad_status', status: o.status }, 409);
      /* 10-16：跟 payChangeCheck 同一條規則 —— 已有待確認（review）的訂單時，只能送出級別更高的（Pro 年 > Pro 月 > Plus 年 > Plus 月）。
         擋的是「先開了較低級別的單、之後才回報」這條路：不擋的話，較低的那張會把較高的待確認單取代掉。 */
      const myTier = payTier(o.plan, o.period);
      const hiRev = myTier ? this.q("SELECT plan, plan_name, period FROM orders WHERE email = ? AND status = 'review' AND parent IS NULL AND id <> ?", norm(o.email), o.id).find((x) => payTier(x.plan, x.period) >= myTier) : null;
      if (hiRev) return this.json(req, { error: 'pending_review', msg: `你有一筆「${hiRev.plan_name}・${perName(hiRev.period)}」待審核中，審核完成前只能送出更高級別方案的匯款資料。` }, 409);
      const name = subClean(b.name, 40);
      if (!name) return this.json(req, { error: 'need_name' }, 400);
      const prof = payProfile(b, subClean);
      if (prof.error) return this.json(req, { error: prof.error }, 400);
      const last5 = String(b.last5 || '').trim(), date = String(b.date || '').trim();
      if (!/^\d{5}$/.test(last5)) return this.json(req, { error: 'bad_last5' }, 400);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Date.parse(date + 'T00:00:00+08:00') > this.now() + DAY || Date.parse(date + 'T00:00:00+08:00') < o.created - 2 * DAY) return this.json(req, { error: 'bad_date' }, 400);
      /* 2026-10-16 Andy：「金額直接當客戶寫死對應金額，只有我這還有可以更改」→ 客戶送來的金額一律不看，以訂單金額為準 */
      const amt = o.amount;
      let hist = []; try { hist = JSON.parse(o.reports || '[]'); if (!Array.isArray(hist)) hist = []; } catch (e) { hist = []; }
      const at = this.now();
      hist.push({ at, name, last5, date, amount: amt, state: 'active' });
      this.paySet(o.id, { status: 'review', payer_name: name, gender: prof.gender || null, from_last5: last5, xfer_date: date, xfer_amount: amt, note: '', reports: JSON.stringify(hist) });
      this.payEv(o.id, 'report', { name, last5, date, amt });
      /* 10-16：送出匯款資料＝新訂單事件 → 同一個 email 比它舊的待確認轉帳標「已被取代」、待處理的取消／退款申請自動結案 */
      this.payReconcile(o.email);
      const per = o.period === 'year' ? '年繳' : '月繳';
      this.payTell(o.email, '已收到你的匯款資料', `我們已收到你的訂單 ${o.id}（${o.plan_name}・${per}，金額 NT$ ${o.amount}）的匯款資料：\n送出時間：${tpeStr(at)}\n匯款人姓名：${name}\n轉出帳號末 5 碼：${last5}\n轉帳日期：${date}\n\n管理者確認入帳後就會開通，屆時會再通知你。資料填錯的話，請從網站右下角「客服」→「意見反饋」告訴我們。`, 'rep-' + o.id + '-' + hist.length);
      this.payNotifyOwner(`${name} ${o.plan_name}（${per}） ${tpeDay(at)}`,
        `有一筆銀行轉帳訂閱送出了匯款資料，請到管理區「金流」確認入帳。\n\n訂單編號：${o.id}\n方案：${o.plan_name}（${per}）\n金額：NT$ ${o.amount}\n匯款人姓名：${name}\n轉出帳號末 5 碼：${last5}\n轉帳日期：${date}\n會員 email：${o.email}\n送出時間：${tpeStr(at)}（台北）`,
        'own-rep-' + o.id + '-' + hist.length);
      /* 馬上送一次（不等每 10 分鐘的排程）；沒設 Resend＝什麼都不做，寄失敗留在佇列下次再試，都不影響回應 */
      try { await this.payMailFlush(); } catch (e) { /* 略 */ }
      return this.json(req, { ok: true, order: pubOrder(this.payOrder(o.id)) });
    },
    '/v1/pay/my': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.payInit();
      return this.json(req, this.payMine(v));
    },
    /* 付款完成頁輪詢：自己的一筆；還沒開通的綠界單順手查一次單（每筆每 20 秒最多一次）*/
    '/v1/pay/order': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.payInit();
      let o = this.payOrder(b.id);
      if (!o || (o.uid !== v.user.uid && norm(o.email) !== norm(v.user.email))) return this.json(req, { error: 'not_found' }, 404);
      if (o.method === 'ecpay' && !o.applied && !o.parent && ['pending', 'paid'].includes(o.status) && (!o.last_sync || this.now() - o.last_sync > 20000)) {
        await this.payQuery(o.id, 'poll'); o = this.payOrder(o.id);
      }
      const e = this.effective(norm(v.user.email));
      return this.json(req, { order: pubOrder(o, this.q('SELECT * FROM refunds WHERE oid = ?', o.id)), plan: e.expired ? 'free' : e.plan, planName: e.planName, expires: e.expires || 0 });
    },
    '/v1/pay/period/cancel': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.payInit();
      const o = this.payOrder(b.id);
      if (!o || (o.uid !== v.user.uid && norm(o.email) !== norm(v.user.email)) || !o.recur || o.parent) return this.json(req, { error: 'not_found' }, 404);
      const r = await this.payPeriodCancel(o.id, 'member');
      if (!r.ok) return this.json(req, { error: r.error, msg: r.msg || '' }, 502);
      return this.json(req, { ok: true, ...this.payMine(v) });
    },

    /* ---------------- 管理者（/v1/admin/* 另外有總閘：權杖必須是管理者）*/
    '/v1/admin/pay/list': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit(); this.payExpireLog(); this.payReconcileAll();
      const rows = this.q('SELECT * FROM orders ORDER BY created DESC LIMIT 3000');
      const refunds = this.q('SELECT * FROM refunds ORDER BY created DESC');
      const names = {}; this.q('SELECT uid, name FROM users').forEach((u) => { names[u.uid] = u.name; });
      const orders = rows.map((o) => admOrder(o, refunds, names));
      const anomalies = orders.filter((o) => o.anomaly || o.actErr || (o.status === 'paid' && !o.applied)).map((o) => o.id);
      const now = this.now();
      const subs = this.paySubs();
      const expiring = subs.filter((s) => s.lastMethod === 'bank' && !s.autoRenew && s.expires > now && s.expires - now <= PAY_RENEW_DAYS * DAY).map((s) => s.email);
      const events = this.q("SELECT email, kind, plan, at, ref, detail FROM plan_events ORDER BY id DESC LIMIT 2000");
      const reqs = this.q("SELECT s.id, s.type, s.email, s.plan, s.note, s.created, s.status, s.close_reason AS closeReason, s.closed_at AS closedAt, s.closed_by AS closedBy, s.pinned, u.name FROM sub_requests s LEFT JOIN users u ON u.uid = s.uid WHERE s.type IN ('cancel', 'refund') ORDER BY s.created DESC LIMIT 500")
        .map((r) => ({ ...r, oid: r.type === 'refund' ? this.payRefundTarget(r.email) : '' }));
      /* 稽核（第 4 條）：管理者與規則自動做的每個動作（誰、何時、做了什麼、前後狀態）*/
      const AUD = ['confirm', 'reject', 'ack', 'amount', 'note', 'reactivate', 'refund', 'purge', 'req_set', 'req_close', 'req_refunded', 'superseded', 'period_cancel_admin', 'bank_put'];
      const audit = this.q(`SELECT id, at, oid, kind, detail FROM pay_events WHERE kind IN (${AUD.map(() => '?').join(',')}) ORDER BY id DESC LIMIT 2000`, ...AUD)
        .map((e) => { let d = {}; try { d = JSON.parse(e.detail); } catch (x) { d = {}; } return { id: e.id, at: e.at, oid: e.oid, kind: e.kind, by: d.by || '', from: d.from || '', to: d.to || '', email: d.email || '', detail: d }; });
      return this.json(req, { now, reqs, orders, refunds, subs, anomalies, expiring, events, audit, bank: this.payBank(), test: this.ecCfg().test, status: PAY_STATUS });
    },
    '/v1/admin/pay/confirm': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id);
      if (!o || o.method !== 'bank') return this.json(req, { error: 'not_found' }, 404);
      /* 重複按／另一位管理者已確認：不重複開通，回是誰、何時開通的 */
      if (o.applied) return this.json(req, { ok: true, dup: true, order: admOrder(o), ...this.payLastBy(o.id) });
      const stC = this.payStale(o, b); if (stC) return this.json(req, stC, 409);
      /* 2026-10-12 Andy：會員只是打開訂閱頁沒付款，管理者不該有確認鍵 → 沒回報匯款資料（沒有末 5 碼）的轉帳單一律不能確認入帳 */
      if (!o.from_last5 && o.status === 'pending') return this.json(req, { error: 'not_reported' }, 409);
      /* 已退回又確認入帳、已退款又確認……：不在狀態機允許的「目前狀態」一律 409 */
      if (!PAY_FLOW.confirm.includes(o.status)) return this.json(req, { error: 'bad_status', status: o.status, statusName: PAY_STATUS[o.status] || o.status, msg: `這筆是「${PAY_STATUS[o.status] || o.status}」，不能確認入帳`, ...this.payLastBy(o.id) }, 409);
      if (!o.from_last5) return this.json(req, { error: 'not_reported' }, 409);
      /* 2026-10-12 Andy：「若是發生他給 2000 但我沒注意到，就等於少收錢」→ 管理者必須輸入網銀實際入帳金額，少於應付不能開通 */
      const recv = b.received;
      if (!Number.isInteger(recv) || recv < 1 || recv > 9999999) return this.json(req, { error: 'need_received' }, 400);
      if (recv < o.amount) return this.json(req, { error: 'underpaid', amount: o.amount, received: recv }, 409);
      /* 稽核 H3：同一筆入帳（末 5 碼＋轉帳日期）已經確認過別張單 → 擋下；管理者確定是另一筆錢才可勾選並寫理由 */
      const dupO = this.q("SELECT id, email FROM orders WHERE id <> ? AND method = 'bank' AND applied = 1 AND from_last5 = ? AND xfer_date = ?", o.id, o.from_last5, o.xfer_date)[0];
      const dupWhy = subClean(b.dupReason, 200);
      if (dupO && !(b.dupOk === true && dupWhy)) return this.json(req, { error: 'dup_xfer', other: dupO.id, otherEmail: dupO.email }, 409);
      this.paySet(o.id, { recv_amount: recv });
      this.paySet(o.id, { status: 'paid', paid_at: o.xfer_date ? Date.parse(o.xfer_date + 'T12:00:00+08:00') : this.now() });
      const r = this.payActivate(o.id, 'admin:' + norm(v.user.email));
      this.payAudit(o.id, 'confirm', v.user.email, o.status, (this.payOrder(o.id) || {}).status, { received: recv, amount: o.amount, reported: o.xfer_amount, dupOf: dupO ? dupO.id : '', dupWhy });
      this.payReconcile(o.email);
      if (!r.ok) return this.json(req, { error: r.error, msg: r.error === 'plan_conflict' ? '會員目前有較高的方案，這筆沒有開通，已列入異常清單' : '' }, r.error === 'plan_conflict' ? 409 : 500);
      return this.json(req, { ok: true, order: admOrder(this.payOrder(o.id)) });
    },
    '/v1/admin/pay/reject': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id);
      if (!o || o.method !== 'bank') return this.json(req, { error: 'not_found' }, 404);
      if (o.applied) return this.json(req, { error: 'applied', msg: '這筆已經開通了，不能退回（要退錢請用「退款」）', ...this.payLastBy(o.id) }, 409);
      const stR = this.payStale(o, b); if (stR) return this.json(req, stR, 409);
      if (!PAY_FLOW.reject.includes(o.status)) return this.json(req, { error: 'bad_status', status: o.status, statusName: PAY_STATUS[o.status] || o.status, msg: `這筆是「${PAY_STATUS[o.status] || o.status}」，不能退回`, ...this.payLastBy(o.id) }, 409);
      const reason = subClean(b.reason, 200);
      if (!reason) return this.json(req, { error: 'need_reason' }, 400);
      this.paySet(o.id, { status: 'rejected', reject_reason: reason });
      this.payAudit(o.id, 'reject', v.user.email, o.status, 'rejected', { reason });
      this.payTell(o.email, '你的轉帳沒有通過確認', `你的訂單 ${o.id}（${o.plan_name}・${o.period === 'year' ? '年繳' : '月繳'}，應付 NT$ ${o.amount}）的匯款資料沒有通過確認。\n你回報的匯款：末 5 碼 ${o.from_last5 || '—'}，NT$ ${o.xfer_amount || 0}，${o.xfer_date || ''}\n原因：${reason}\n\n這筆沒有開通。請依原因確認後重新下單回報；如果你已經匯款，請直接回覆這封信，我們會協助處理。`, 'rej-' + o.id + '-' + this.now());
      return this.json(req, { ok: true, order: admOrder(this.payOrder(o.id)) });
    },
    /* 已開通但帶異常註記（例如取消後才付款）→ 管理者看過後「標記已處理」，從異常清單拿掉 */
    '/v1/admin/pay/ack': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      if (!o.applied) return this.json(req, { error: 'not_applied' }, 409);
      this.payAudit(o.id, 'ack', v.user.email, o.status, o.status, { anomaly: o.anomaly || '', actErr: o.act_err || '' });
      this.paySet(o.id, { anomaly: null, act_err: null });
      return this.json(req, { ok: true });
    },
    /* 2026-10-16 Andy：「金額直接當客戶寫死對應金額，只有我這還有可以更改」→ 管理者改這筆轉帳單的金額（應付＝客戶匯款金額），
       只限還沒開通的銀行轉帳單；改前改後與理由記進金流事件。*/
    '/v1/admin/pay/amount': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id);
      if (!o || o.method !== 'bank') return this.json(req, { error: 'not_found' }, 404);
      const stA = this.payStale(o, b); if (stA) return this.json(req, stA, 409);
      if (o.applied || !PAY_FLOW.amount.includes(o.status)) return this.json(req, { error: 'bad_status', status: o.status }, 409);
      const amt = b.amount;
      if (!Number.isInteger(amt) || amt < 1 || amt > 9999999) return this.json(req, { error: 'bad_amount' }, 400);
      const why = subClean(b.reason, 200);
      this.payAudit(o.id, 'amount', v.user.email, o.status, o.status, { before: o.amount, after: amt, why });
      this.paySet(o.id, { amount: amt, ...(o.from_last5 ? { xfer_amount: amt } : {}) });
      return this.json(req, { ok: true, order: admOrder(this.payOrder(o.id)) });
    },
    '/v1/admin/pay/note': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      this.payAudit(o.id, 'note', v.user.email, o.status, o.status, { before: o.admin_note || '', after: subClean(b.note, 300) });
      this.paySet(o.id, { admin_note: subClean(b.note, 300) });
      return this.json(req, { ok: true });
    },
    /* 補開通（異常清單的一鍵）：綠界單先查一次單；查不到也可以強制（force，金額不符或綠界連不到時管理者自己判斷）*/
    '/v1/admin/pay/reactivate': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      let o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      if (o.applied) return this.json(req, { ok: true, dup: true });
      /* 稽核 M1：退過款的單不准補開通 */
      if (o.refunded > 0 || o.status === 'refunded') return this.json(req, { error: 'refunded', msg: '這筆已經退過款，不能再開通' }, 409);
      /* 稽核 M2：轉帳單一律走「確認入帳」（要有回報、要輸入實收），不能用強制補開通繞過 */
      if (o.method === 'bank') return this.json(req, { error: 'use_confirm', msg: '轉帳單請用「確認入帳並開通」（要輸入網銀實收金額）' }, 409);
      if (o.method === 'ecpay' && !o.parent && !b.force) {
        const q = await this.payQuery(o.id, 'admin_query');
        o = this.payOrder(o.id);
        if (o.applied) return this.json(req, { ok: true, via: 'query' });
        /* 查單沒能開通（沒付、金額不符、連不到綠界）→ 不自動開；要開請管理者看過後按「強制開通」（force） */
        return this.json(req, { error: q.error || 'unpaid', msg: q.error === 'amount_mismatch' ? '綠界金額跟訂單不符' : q.error === 'network' ? '連不到綠界' : '綠界查單顯示還沒付款' }, 409);
      }
      if (!b.force && o.status !== 'paid') return this.json(req, { error: 'unpaid' }, 409);
      /* 稽核 M3／M10：強制開通要寫理由；原本的異常文字保留在事件裡 */
      const why = subClean(b.reason, 200);
      if (b.force && !why) return this.json(req, { error: 'need_reason', msg: '強制開通請寫理由（例如：已到綠界後台確認實收金額）' }, 400);
      this.payAudit(o.id, 'reactivate', v.user.email, o.status, 'active', { force: !!b.force, reason: why, prevAnomaly: o.anomaly || '' });
      this.paySet(o.id, { anomaly: null, status: 'paid', paid_at: o.paid_at || this.now() });
      const r = this.payActivate(o.id, 'admin_fix:' + norm(v.user.email));
      return r.ok ? this.json(req, { ok: true }) : this.json(req, { error: r.error }, 500);
    },
    '/v1/admin/pay/sync': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      const r = o.recur && !o.parent ? await this.payPeriodSync(o.id, 'admin_sync') : await this.payQuery(o.id, 'admin_query');
      return this.json(req, { ...r, order: admOrder(this.payOrder(o.id)) });
    },
    '/v1/admin/pay/refund_quote': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      return this.json(req, { id: o.id, amount: o.amount, ...this.payRefundQuote(o) });
    },
    /* 退款：rid＝確認框打開時產生的一次性編號 → 同一個 rid 按兩次只會執行一次 */
    '/v1/admin/pay/refund': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const rid = String(b.rid || '');
      if (!/^[A-Za-z0-9_-]{8,40}$/.test(rid)) return this.json(req, { error: 'bad_rid' }, 400);
      const prev = this.q('SELECT * FROM refunds WHERE id = ?', rid)[0];
      if (prev) return this.json(req, { ok: prev.status === 'done', dup: true, refund: prev, error: prev.status === 'done' ? undefined : prev.status === 'running' ? 'running' : 'failed', msg: prev.msg || '' }, prev.status === 'done' ? 200 : 409);
      const o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      /* 10-16：被取代的轉帳單（會員回報過匯款、沒開通）也能登記人工退款，把多匯的錢退回去 */
      const supPaid = o.method === 'bank' && o.status === 'superseded' && !!o.from_last5;
      if (!o.applied && !['paid', 'active'].includes(o.status) && !supPaid) return this.json(req, { error: 'not_paid' }, 409);
      /* 10-16 Andy：「會多出現已退款功能按鈕 並且跳到退款紀錄那邊紀錄」→ 從申請按「已退款」登記時帶 req；退款成功那一刻把申請標成已處理 */
      const rq = b.req ? this.q("SELECT * FROM sub_requests WHERE id = ? AND type = 'refund'", String(b.req))[0] : null;
      if (b.req && (!rq || norm(rq.email) !== norm(o.email))) return this.json(req, { error: 'bad_req', msg: '這筆申請跟訂單不是同一個會員' }, 400);
      /* 兩個管理者同時處理同一筆申請：另一位已經處理（結案）→ 擋下，不重複退錢 */
      if (rq && rq.status !== 'new') return this.json(req, { error: 'req_done', msg: `這筆申請已經由 ${rq.closed_by || '管理者'} 在 ${rq.closed_at ? tpeStr(rq.closed_at) : '稍早'} 處理（${rq.close_reason || '已處理'}），沒有再退一次`, closedBy: rq.closed_by || '', closedAt: rq.closed_at || 0 }, 409);
      const stF = this.payStale(o, b); if (stF) return this.json(req, stF, 409);
      const quote = this.payRefundQuote(o);
      /* 已退款又要求退款：可退金額 0 → 409（不是 400 格式錯）*/
      if (quote.left <= 0) return this.json(req, { error: 'already_refunded', msg: '這筆已經全額退款了', ...this.payLastBy(o.id) }, 409);
      const amount = b.amount;
      if (!Number.isInteger(amount) || amount < 1) return this.json(req, { error: 'bad_amount' }, 400);
      if (amount > quote.left) return this.json(req, { error: 'over', left: quote.left }, 400);
      if (this.q("SELECT 1 FROM refunds WHERE oid = ? AND status = 'running'", o.id).length) return this.json(req, { error: 'running' }, 409);
      const permAct = b.perm === 'end' ? 'end' : 'now';
      const manual = b.manual === true || quote.kind === 'manual';
      if (manual) {
        if (!/^\d{5}$/.test(String(b.last5 || '')) && quote.kind === 'manual') return this.json(req, { error: 'bad_last5' }, 400);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(String(b.date || ''))) return this.json(req, { error: 'bad_date' }, 400);
      } else if (quote.test) {
        return this.json(req, { error: 'stage_no_refund', msg: '綠界測試環境不提供信用卡退刷 API（官方文件註明），請改用「登記人工退款」或到綠界後台操作' }, 409);
      }
      const now = this.now();
      this.q('INSERT INTO refunds (id, oid, email, amount, kind, action, status, perm, acct_last5, rdate, note, by, created) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        rid, o.id, o.email, amount, manual ? 'manual' : 'ecpay', '', 'running', permAct, manual ? String(b.last5 || '') : '', manual ? String(b.date || '') : '', subClean(b.note, 200), norm(v.user.email), now);
      let res = { ok: true, action: 'manual' };
      if (!manual) {
        try { res = await this.payCreditRefund(o, amount); } catch (e) { res = { ok: false, msg: String(e && e.message || e).slice(0, 120) }; }
      }
      if (!res.ok) {
        this.q("UPDATE refunds SET status = 'failed', action = ?, msg = ?, done_at = ? WHERE id = ?", res.action || '', res.msg || '', this.now(), rid);
        return this.json(req, { error: 'ecpay', msg: res.msg || '綠界退款失敗' }, 502);
      }
      this.q("UPDATE refunds SET status = 'done', action = ?, done_at = ?, req = ? WHERE id = ?", res.action || '', this.now(), rq ? rq.id : null, rid);
      /* 一個 email 一筆（第 2 條）：退款完成 → 這位會員所有還沒處理的退款申請一起結案（從申請按「已退款」來的那筆記 req_refunded）*/
      for (const r0 of this.q("SELECT * FROM sub_requests WHERE email = ? AND type = 'refund' AND status = 'new'", norm(o.email))) {
        this.q("UPDATE sub_requests SET status = 'done', close_reason = ?, closed_at = ?, closed_by = ? WHERE id = ?", `已退款 NT$ ${amount}（訂單 ${o.id}）`, this.now(), norm(v.user.email), r0.id);
        this.payEv(o.id, r0.id === (rq && rq.id) ? 'req_refunded' : 'req_close', { req: r0.id, rid, amount, by: norm(v.user.email), from: 'new', to: 'done', reason: '已退款' });
      }
      const sum = this.q("SELECT COALESCE(SUM(amount), 0) AS s FROM refunds WHERE oid = ? AND status = 'done'", o.id)[0].s;
      this.paySet(o.id, { refunded: sum, status: sum >= o.amount ? 'refunded' : o.status });
      /* 退回被取代的重複匯款（沒開通過）不算用掉七天退款保證 */
      if (o.applied) this.billUpsert(o.email, { refund_used: 1, trial_used: 1, refund_at: now });
      let cancel = null;
      const parent = o.parent ? this.payOrder(o.parent) : o;
      if (parent && parent.recur && parent.period_state === 'active') {
        cancel = await this.payPeriodCancel(parent.id, 'refund');
        /* 稽核 H14：退款成功但終止自動扣款失敗 → 列異常，排程會重試 */
        if (!cancel.ok) this.paySet(parent.id, { anomaly: `已退款，但向綠界終止自動扣款失敗（${cancel.msg || cancel.error}），排程會重試；也可到綠界後台手動終止` });
      }
      /* 稽核 M13：沒開通過的單退款不動權限；H10：依這一筆實際給的期間回收（不是一律砍到現在）*/
      const cur = this.q('SELECT plan, expires FROM perm WHERE email = ?', o.email)[0];
      if (o.applied && cur && cur.plan === o.plan && cur.expires && cur.expires > now && o.grant_to) {
        const future = o.grant_from > now;                                   // 這一筆是還沒開始的續訂期
        const cut = permAct === 'now' || future ? Math.max(0, o.grant_to - Math.max(o.grant_from, now)) : 0;
        if (cut > 0) {
          let nexp = cur.expires - cut; if (nexp <= now) nexp = now - 1;   // effective() 判斷「到期日 < 現在」，減 1 毫秒＝當下就降
          this.q('UPDATE perm SET expires = ?, updated = ? WHERE email = ?', nexp, now, o.email);
          this.planEv(o.email, nexp <= now ? 'refund_downgrade' : 'refund_keep', o.plan, rid, nexp <= now ? `退款 NT$ ${amount}，立即回到註冊會員` : `退款 NT$ ${amount}，收回這一筆的期間，到期日改為 ${tpeDay(nexp)}`);
        } else this.planEv(o.email, 'refund_keep', o.plan, rid, `退款 NT$ ${amount}，用到 ${tpeDay(cur.expires)} 才停`);
      } else this.planEv(o.email, 'refund_keep', o.plan, rid, `退款 NT$ ${amount}${o.applied ? '' : '（這筆沒開通過，不動權限）'}`);
      this.payAudit(o.id, 'refund', v.user.email, o.status, (this.payOrder(o.id) || {}).status, { rid, amount, perm: permAct, action: res.action, req: rq ? rq.id : '' });
      {
        const e2 = this.effective(norm(o.email));
        const after = e2.expired || e2.plan === 'free' ? '你的帳號已回到註冊會員。' : `你的方案 ${e2.planName} 可以用到 ${tpeDay(e2.expires)}。`;
        const how = manual ? (quote.kind === 'manual' ? `退款會匯回你的帳戶（末 5 碼 ${String(b.last5 || '')}），一般 1～3 個工作天入帳。` : '退款已在綠界處理，依發卡銀行作業時間退回你的信用卡。') : '退款已送出到綠界，會退回你付款的信用卡；實際入帳時間依發卡銀行而定（通常 7～14 個工作天）。';
        this.payTell(o.email, `退款完成：NT$ ${amount}`, `你的訂單 ${o.id}（${o.plan_name}・${o.period === 'year' ? '年繳' : '月繳'}）已退款 NT$ ${amount}。\n${how}\n${after}${cancel && cancel.ok ? '\n信用卡自動扣款也已經停止，之後不會再扣款。' : ''}`, 'rf-' + rid);
      }
      return this.json(req, { ok: true, refund: this.q('SELECT * FROM refunds WHERE id = ?', rid)[0], cancel, order: admOrder(this.payOrder(o.id)) });
    },
    /* 2026-10-14 Andy：「liguligu0818 重複開通的測試資料要不要清掉」→ OK。
       清除「測試帳號」的金流資料：訂單、退款、帳務通知、通知信、取消／退款申請、方案異動紀錄，權限回到註冊會員。
       防呆：① 管理者要再打一次 email ② 有綠界正式付款（非測試、已付款）的訂單一律拒絕（那是真的錢，只能走退款）③ 刪了什麼寫進 pay_events（不刪）*/
    '/v1/admin/pay/purge': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const email = norm(b.email);
      if (!email || norm(b.confirm) !== email) return this.json(req, { error: 'confirm', msg: '請再輸入一次相同的 email' }, 400);
      const os = this.q('SELECT * FROM orders WHERE email = ?', email);
      const real = os.filter((o) => o.method === 'ecpay' && !o.test && (o.applied || ['paid', 'active', 'refunded'].includes(o.status)));
      if (real.length) return this.json(req, { error: 'real_payment', msg: `這個帳號有 ${real.length} 筆綠界正式付款，不能用清除，請用退款處理` }, 409);
      const recurOn = os.filter((o) => o.recur && !o.parent && o.period_state === 'active');
      if (recurOn.length) return this.json(req, { error: 'recur_active', msg: '這個帳號還有信用卡自動扣款，請先終止' }, 409);
      const ids = os.map((o) => o.id);
      const cnt = { orders: ids.length, refunds: 0, notices: 0, requests: 0 };
      for (const id of ids) cnt.refunds += this.q('SELECT COUNT(*) AS c FROM refunds WHERE oid = ?', id)[0].c;
      this.payEv('', 'purge', { by: v.user.email, email, orders: os.map((o) => ({ id: o.id, plan: o.plan, period: o.period, amount: o.amount, method: o.method, status: o.status, recv: o.recv_amount || 0 })), refunds: cnt.refunds });
      for (const id of ids) { this.q('DELETE FROM refunds WHERE oid = ?', id); }
      this.q('DELETE FROM orders WHERE email = ?', email);
      cnt.notices = this.q('SELECT COUNT(*) AS c FROM user_notices WHERE email = ?', email)[0].c;
      this.q('DELETE FROM user_notices WHERE email = ?', email);
      this.q('DELETE FROM mail_out WHERE email = ?', email);
      cnt.requests = this.q("SELECT COUNT(*) AS c FROM sub_requests WHERE email = ? AND type IN ('cancel', 'refund')", email)[0].c;
      this.q("DELETE FROM sub_requests WHERE email = ? AND type IN ('cancel', 'refund')", email);
      this.q('DELETE FROM plan_events WHERE email = ?', email);
      this.q('DELETE FROM bill_flags WHERE email = ?', email);
      this.q('DELETE FROM perm WHERE email = ?', email);   // 權限回到註冊會員（範本與個別微調一起清掉）
      return this.json(req, { ok: true, email, ...cnt });
    },
    '/v1/admin/pay/period_cancel': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const r = await this.payPeriodCancel(String(b.id || ''), 'admin:' + norm(v.user.email));
      this.payAudit(String(b.id || ''), 'period_cancel_admin', v.user.email, '', r.ok ? 'cancelled' : 'failed', { msg: r.msg || r.error || '' });
      return r.ok ? this.json(req, { ok: true }) : this.json(req, { error: r.error, msg: r.msg || '' }, 502);
    },
    '/v1/admin/pay/bank/get': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      return this.json(req, { bank: this.payBank() });
    },
    '/v1/admin/pay/bank/put': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const prevB = this.payBank();
      if (b.clear === true) { this.setKv('pay_bank', ''); this.payAudit('', 'bank_put', v.user.email, prevB ? '開放' : '關閉', '關閉', {}); return this.json(req, { ok: true, bank: null }); }
      const bank = { bank_name: subClean(b.bank_name, 30), bank_code: String(b.bank_code || '').trim(), account: String(b.account || '').replace(/[\s-]/g, ''), holder: subClean(b.holder, 40) };
      if (!bank.bank_name || !bank.holder || !/^\d{3}$/.test(bank.bank_code) || !/^\d{6,20}$/.test(bank.account)) return this.json(req, { error: 'bad_input' }, 400);
      this.setKv('pay_bank', JSON.stringify(bank));
      this.payAudit('', 'bank_put', v.user.email, prevB ? '開放' : '關閉', '開放', { bank: bank.bank_name + '（' + bank.bank_code + '）', acct: '…' + bank.account.slice(-4) });
      return this.json(req, { ok: true, bank });
    },
  });

  /* ---------------------------------------------------------------- 綠界打進來的三支（不是瀏覽器 JSON：form-urlencoded、沒有 Origin）*/
  const formOf = async (req) => { const t = await req.text(); if (t.length > 20000) return null; return Object.fromEntries(new URLSearchParams(t)); };
  const txt = (s, status = 200) => new Response(s, { status, headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store' } });
  Hub.prototype.payNotify = async function (req) {
    this.payInit();
    const f = await formOf(req);
    if (!f || !(await this.ecVerify(f))) { this.payEv(f && f.MerchantTradeNo, 'notify_badmac', f ? evSafe(f) : ''); return txt('0|CheckMacValue Error', 400); }
    const o = this.payOrder(f.MerchantTradeNo);
    this.payEv(f.MerchantTradeNo, 'notify', { RtnCode: f.RtnCode, TradeAmt: f.TradeAmt, PaymentType: f.PaymentType, SimulatePaid: f.SimulatePaid });
    if (!o) return txt('0|Order Not Found', 404);
    if (String(f.SimulatePaid) === '1') return txt('1|OK');   // 綠界後台「模擬付款」：官方註明不要改訂單狀態
    const rc = String(f.RtnCode);
    if (rc === '1') {
      const r = this.payMarkPaid(o, { amount: f.TradeAmt || f.Amount || f.amount, trade_no: f.TradeNo, pay_type: f.PaymentType, gwsr: f.gwsr, paid_at: parseTpe(f.PaymentDate) || this.now(), msg: f.RtnMsg }, 'notify');
      if (!r.ok && r.error === 'activate_failed') return txt('0|Activate Failed', 500);   // 讓綠界 5～15 分鐘後重送
      return txt('1|OK');
    }
    if (rc === '2' || rc === '10100073') {   // ATM 取號／超商代碼取號成功：還沒付錢，只存繳費資訊
      const info = { bank: f.BankCode || '', account: f.vAccount || '', code: f.PaymentNo || '', expire: f.ExpireDate || '' };
      this.paySet(o.id, { pay_type: f.PaymentType || o.pay_type, pay_info: JSON.stringify(info), rtn_msg: f.RtnMsg || '' });
      return txt('1|OK');
    }
    if (!o.applied && o.status === 'pending') this.paySet(o.id, { status: 'failed', rtn_msg: subClean(f.RtnMsg, 120) });
    return txt('1|OK');
  };
  Hub.prototype.payPeriodNotify = async function (req) {
    this.payInit();
    const f = await formOf(req);
    if (!f || !(await this.ecVerify(f))) { this.payEv(f && f.MerchantTradeNo, 'period_badmac', ''); return txt('0|CheckMacValue Error', 400); }
    const p = this.payOrder(f.MerchantTradeNo);
    this.payEv(f.MerchantTradeNo, 'period_notify', { RtnCode: f.RtnCode, Amount: f.Amount, TotalSuccessTimes: f.TotalSuccessTimes });
    if (!p || !p.recur) return txt('0|Order Not Found', 404);
    if (String(f.SimulatePaid) === '1') return txt('1|OK');
    if (String(f.RtnCode) !== '1') { this.paySet(p.id, { rtn_msg: '續扣失敗：' + subClean(f.RtnMsg, 100) }); return txt('1|OK'); }
    const n = parseInt(f.TotalSuccessTimes, 10) || 1;
    const r = this.payPeriodCharge(p, n, { amount: f.Amount, trade_no: f.Gwsr || '', paid_at: parseTpe(f.ProcessDate) || this.now(), msg: f.RtnMsg }, 'period_notify');
    if (!r.ok && r.error === 'activate_failed') return txt('0|Activate Failed', 500);
    return txt('1|OK');
  };
  /* 使用者付完被導回（瀏覽器 POST）：驗章 → 伺服器主動查單（第 2 層保險）→ 導回網站的付款完成頁 */
  Hub.prototype.payResult = async function (req) {
    this.payInit();
    const f = await formOf(req) || {};
    const o = this.payOrder(f.MerchantTradeNo);
    const good = await this.ecVerify(f);
    this.payEv(f.MerchantTradeNo, 'result', { good, RtnCode: f.RtnCode });
    if (o && good && !o.applied) {
      if (o.recur) await this.payPeriodSync(o.id, 'result'); else await this.payQuery(o.id, 'result');
    }
    const to = o && o.back ? o.back + '#orders/' + o.id : '';
    if (!to) return this.page('付款結果', '<h1>付款結果</h1><p>找不到這筆訂單，請回到網站的「我的訂單」查看。</p>', 404);
    return new Response(null, { status: 303, headers: { Location: to, 'cache-control': 'no-store' } });
  };

  const PAY_PUBLIC = { '/v1/pay/ecpay/notify': 'payNotify', '/v1/pay/ecpay/period': 'payPeriodNotify', '/v1/pay/ecpay/result': 'payResult' };
  const payOrigFetch = Hub.prototype.fetch;
  Hub.prototype.fetch = async function (req) {
    const u = new URL(req.url);
    if (u.hostname === 'internal.cron' && u.pathname === '/cron/pay-sweep') { const r = await this.paySweep(); return new Response(JSON.stringify(r)); }
    if (req.method === 'POST' && Object.prototype.hasOwnProperty.call(PAY_PUBLIC, u.pathname)) {
      try { return await this[PAY_PUBLIC[u.pathname]](req); } catch (e) { return txt('0|' + String(e && e.message || e).slice(0, 80), 500); }
    }
    return payOrigFetch.call(this, req);
  };
  /* 每小時 alarm 也順手寫到期紀錄、把逾期的待付款單標起來（不連外網）*/
  const payOrigCleanup = Hub.prototype.cleanup;
  Hub.prototype.cleanup = function () {
    payOrigCleanup.call(this);
    try { this.payExpireLog(); /* 稽核 M10：金流事件是唯一的時間軸證據，只增不刪（不再 400 天清除）*/ } catch (e) { /* 不擋其他清理 */ }
  };
  /* 刪除帳號：訂單、退款是交易紀錄（對帳、稅務），不跟著刪；只把 uid 斷開（docs/payment_checkout_1011.md 第 9 節）*/
  const payOrigDelete = Hub.prototype.deleteMe;
  Hub.prototype.deleteMe = async function (req, b) {
    const v = await this.auth(req, b || {});
    /* 稽核 H13：刪帳號前先終止所有自動扣款；終止失敗就不刪，請他稍後再試或聯絡客服 */
    if (v) {
      this.payInit();
      for (const p of this.q("SELECT id FROM orders WHERE (uid = ? OR email = ?) AND recur = 1 AND parent IS NULL AND applied = 1 AND period_state = 'active'", v.user.uid, norm(v.user.email))) {
        const r = await this.payPeriodCancel(p.id, 'delete_account');
        if (!r.ok) return this.json(req, { error: 'period_cancel_failed', msg: '你的信用卡自動扣款還沒能終止，帳號先不刪除；請稍後再試或聯絡客服' }, 409);
      }
    }
    const res = await payOrigDelete.call(this, req, b);
    if (v && res.status === 200) { this.payInit(); this.q("UPDATE orders SET uid = '' WHERE uid = ?", v.user.uid); }
    return res;
  };
  /* 10-16：會員送出取消／退款申請 —— 有待確認（review）的轉帳時先擋（不能兩邊同時掛著待處理，也避免已匯的錢被申請蓋掉）；
     送出成功後跑一次 payReconcile：同一個人比它舊的待處理申請自動結案（只留最新一筆）。 */
  const payOrigChange = Hub.prototype.subRoutes['/v1/subscribe/change'];
  const payOrigFbSet = Hub.prototype.subRoutes['/v1/admin/feedback/set'];
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/subscribe/change': async function (req, b) {
      const v = await this.auth(req, b);
      if (v && b && (b.type === 'cancel' || b.type === 'refund')) {
        this.payInit();
        const rv = this.q("SELECT plan_name, period FROM orders WHERE email = ? AND status = 'review' AND parent IS NULL ORDER BY created DESC LIMIT 1", norm(v.user.email))[0];
        if (rv) return this.json(req, { error: 'pending_review', msg: `你有一筆「${rv.plan_name}・${perName(rv.period)}」的轉帳正在審核中，審核完成後才能申請${b.type === 'refund' ? '退款' : '取消訂閱'}；急的話請從右下角「客服」聯絡我們。` }, 409);
      }
      const res = await payOrigChange.call(this, req, b);
      if (res.status === 200 && v) {
        this.payReconcile(v.user.email);
        /* 通知（第 5 條）：管理者鈴鐺＋寄給站方一封（沒設 Resend 只進佇列）*/
        let rid = ''; try { rid = (await res.clone().json()).id || ''; } catch (e) { rid = ''; }
        const nm = ((this.q('SELECT name FROM users WHERE uid = ?', v.user.uid)[0] || {}).name || v.user.email);
        this.payNotifyOwner(`${nm} ${RQN[b.type]}申請 ${tpeDay(this.now())}`, `會員送出了${RQN[b.type]}申請，請到管理區「付款與訂單 → 取消／退款申請」處理。\n\n會員：${nm}\n會員 email：${norm(v.user.email)}\n留言：${subClean(b.note, 300) || '（沒有留言）'}\n送出時間：${tpeStr(this.now())}（台北）`, 'own-req-' + rid, '新申請：');
      }
      return res;
    },
    /* 管理者手動「標記已處理／改回待處理」：記原因與時間；改回待處理＝pinned（之後比它舊的訂單事件不再自動結案它）。
       重複按／兩個管理者同時按：狀態已經是目標狀態 → 409 same_status（回是誰、何時處理的），不重複記、不重複通知。 */
    '/v1/admin/feedback/set': async function (req, b) {
      if (!b || b.kind !== 'request') return payOrigFbSet.call(this, req, b);
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const id = String(b.id || ''), row = this.q('SELECT * FROM sub_requests WHERE id = ?', id)[0];
      if (!row) return this.json(req, { error: 'not_found' }, 404);
      if (row.status === b.status) return this.json(req, { error: 'same_status', status: row.status, closedBy: row.closed_by || '', closedAt: row.closed_at || 0, closeReason: row.close_reason || '',
        msg: b.status === 'done' ? `這筆已經處理過了（${row.close_reason || '已處理'}${row.closed_by ? '・' + row.closed_by : ''}${row.closed_at ? '・' + tpeStr(row.closed_at) : ''}）` : '這筆本來就是待處理' }, 409);
      const res = await payOrigFbSet.call(this, req, b);
      if (res.status !== 200) return res;
      const by = norm(v.user.email), now = this.now();
      if (b.status === 'done') {
        this.q('UPDATE sub_requests SET close_reason = ?, closed_at = ?, closed_by = ? WHERE id = ?', '管理者標記已處理', now, by, id);
        if (['cancel', 'refund'].includes(row.type)) this.payTell(row.email, `你的${RQN[row.type]}申請已處理`, `你在 ${tpeStr(row.created || now)} 送出的${RQN[row.type]}申請，管理者已經處理完成。有任何問題請從右下角「客服」聯絡我們。`, 'rqd-' + id + '-' + now);
      } else this.q('UPDATE sub_requests SET close_reason = NULL, closed_at = NULL, closed_by = NULL, pinned = ? WHERE id = ?', now, id);
      this.payAudit('', 'req_set', by, row.status, b.status, { req: id, type: row.type, email: row.email });
      return res;
    },
  });
  const payOrigExpInit = Hub.prototype.expInit;
  Hub.prototype.expInit = function () { payOrigExpInit.call(this); this.payInit(); };
  for (const t of ['orders', 'refunds', 'plan_events', 'pay_events']) if (!EXPORT_TABLES.includes(t)) EXPORT_TABLES.push(t);
}
