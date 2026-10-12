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
export const PAY_STATUS = { pending: '待付款', review: '待確認', paid: '已入帳', active: '已開通', failed: '失敗', rejected: '已退回', expired: '已逾期', refunded: '已退款', cancelled: '已取消（未付款）' };
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
    this._payOk = true;
  };
  Hub.prototype.payEv = function (oid, kind, detail) {
    this.q('INSERT INTO pay_events (at, oid, kind, detail) VALUES (?, ?, ?, ?)', this.now(), oid || '', kind, String(typeof detail === 'string' ? detail : JSON.stringify(detail || {})).slice(0, 1500));
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
  Hub.prototype.payChangeCheck = function (email, plan, period) {
    const now = this.now(), e = this.effective(email);
    if (e.expired || !e.plan || e.plan === 'free' || !e.expires || e.expires <= now) return { ok: true };
    const cur = this.q('SELECT period FROM orders WHERE email = ? AND applied = 1 AND plan = ? AND grant_from <= ? AND grant_to > ? ORDER BY grant_to DESC LIMIT 1', email, e.plan, now, now)[0];
    const rc = PAY_RANK[e.plan], rt = PAY_RANK[plan];
    if (!cur || !rc || !rt) return { ok: true };
    const curName = `${e.planName}・${cur.period === 'year' ? '年繳' : '月繳'}`;
    const no = (reason, msg) => ({ ok: false, reason, msg });
    if (rt < rc) return no('lower_plan', `你目前是 ${curName}，不能再購買比現在低的方案。`);
    if (rt === rc) {
      if (cur.period === 'year' && period === 'month') return no('year_to_month', `你目前是 ${curName}，不能改買月繳；要換週期請等這期到期後再選。`);
      if (cur.period === period && e.expires - now > PAY_RENEW_DAYS * DAY) return no('same_active', `你目前已是 ${curName}，到期日前 ${PAY_RENEW_DAYS} 天才能續訂。`);
      return { ok: true };
    }
    if (cur.period === 'year' && period === 'month') return no('year_to_month', `你目前是 ${curName}，要升級只能買年繳。`);
    return { ok: true };
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
      this.paySet(o.id, { applied: 1, status: 'active', grant_from: from, grant_to: to, confirmed_at: now, act_src: src, act_err: null, paid_at: o.paid_at || now });
      this.planEv(email, same && from > now ? 'extend' : 'activate', o.plan, o.id, `${tpeDay(from)}～${tpeDay(to)}（${src}）`);
      this.payEv(o.id, 'activate', { src, from, to });
      return { ok: true, order: this.payOrder(o.id) };
    } catch (e) {
      this.paySet(o.id, { act_err: String(e && e.message || e).slice(0, 200) });
      return { ok: false, error: 'activate_failed' };
    }
  };

  /* 綠界付款成功（ReturnURL／查單／排程共用）：驗金額 → 記付款 → 開通 */
  Hub.prototype.payMarkPaid = function (o, info, src) {
    if (o.applied) return { ok: true, dup: true };
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
    this.paySet(o.id, set);
    return this.payActivate(o.id, src);
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
    if (!(await this.ecVerify(r.form))) { this.payEv(o.id, 'query_badmac', r.text.slice(0, 300)); return { ok: false, error: 'bad_mac' }; }
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
    if ((parseInt(info.amount, 10) || p.amount) !== p.amount) { this.paySet(cid, { anomaly: `金額不符：綠界 ${info.amount}、訂單 ${p.amount}` }); return { ok: false, error: 'amount_mismatch' }; }
    return c.applied ? { ok: true, dup: true } : this.payActivate(cid, src);
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
    if (!j || String(j.MerchantTradeNo || p.id) !== p.id) { this.payEv(p.id, 'period_query_bad', r.text.slice(0, 300)); return { ok: false, error: 'bad_reply' }; }
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
    this.payEv(p.id, 'period_cancel', r.text.slice(0, 300));
    if (r.form.CheckMacValue && !(await this.ecVerify(r.form))) return { ok: false, error: 'bad_mac', msg: '綠界回應驗章失敗' };
    if (String(r.form.RtnCode) !== '1') return { ok: false, error: 'ecpay', msg: r.form.RtnMsg || `HTTP ${r.status}` };
    this.paySet(p.id, { period_state: 'cancelled', cancel_at: this.now() });
    this.planEv(p.email, 'auto_renew_off', p.plan, p.id, by || '');
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
    }
    this.q("UPDATE orders SET status = 'expired', updated = ? WHERE method = 'bank' AND status = 'pending' AND created < ?", now, now - PAY_BANK_DAYS * DAY);
    this.q("UPDATE orders SET status = 'cancelled', rtn_msg = '超過 3 天未付款，自動取消', updated = ? WHERE method = 'ecpay' AND status = 'pending' AND applied = 0 AND parent IS NULL AND created < ?", now, now - PAY_ECPAY_EXPIRE_DAYS * DAY);
  };
  /* 排程（每 10 分鐘，wrangler.toml）：補開通 → 對帳 → 到期紀錄 */
  Hub.prototype.paySweep = async function () {
    this.payInit();
    const now = this.now(), out = { query: 0, fixed: 0, period: 0 };
    for (const o of this.q("SELECT id FROM orders WHERE method = 'ecpay' AND parent IS NULL AND applied = 0 AND status IN ('pending', 'paid', 'cancelled') AND created > ? ORDER BY created LIMIT 30", now - (PAY_SWEEP_DAYS + 1) * DAY)) {
      out.query++;
      const r = await this.payQuery(o.id, 'sweep');
      if (r.ok && !r.dup) out.fixed++;
    }
    for (const o of this.q("SELECT id FROM orders WHERE method = 'ecpay' AND recur = 1 AND parent IS NULL AND applied = 1 AND period_state = 'active' AND (last_sync IS NULL OR last_sync < ?) ORDER BY last_sync LIMIT 20", now - PAY_PERIOD_SYNC_MS)) {
      const r = await this.payPeriodSync(o.id, 'sweep');
      if (r.ok) out.period += r.added;
    }
    this.payExpireLog();
    return out;
  };

  /* ---------------------------------------------------------------- 輸出給前端的訂單 */
  const pubOrder = (o, refunds) => ({
    id: o.id, plan: o.plan, planName: o.plan_name, period: o.period, amount: o.amount, method: o.method, recur: !!o.recur, parent: o.parent || null,
    periodN: o.period_n || 0, periodState: o.period_state || '', status: o.status, statusName: PAY_STATUS[o.status] || o.status,
    payType: o.pay_type || '', payInfo: (() => { try { return JSON.parse(o.pay_info || 'null'); } catch (e) { return null; } })(),
    last5: o.from_last5 || '', xferDate: o.xfer_date || '', xferAmount: o.xfer_amount || 0, note: o.note || '', rejectReason: o.reject_reason || '',
    reports: (() => { try { const a = JSON.parse(o.reports || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; } })(),
    recvAmount: o.recv_amount || 0,
    grantFrom: o.grant_from || 0, grantTo: o.grant_to || 0, refunded: o.refunded || 0, test: !!o.test,
    created: o.created, paidAt: o.paid_at || 0, confirmedAt: o.confirmed_at || 0, cancelAt: o.cancel_at || 0,
    refunds: (refunds || []).filter((r) => r.oid === o.id && r.status === 'done').map((r) => ({ amount: r.amount, at: r.done_at || r.created, kind: r.kind })),
  });
  const admOrder = (o, refunds, names) => ({ ...pubOrder(o, refunds), email: o.email, name: (names && names[o.uid]) || '', adminNote: o.admin_note || '', actSrc: o.act_src || '',
    actErr: o.act_err || '', anomaly: o.anomaly || '', tradeNo: o.trade_no || '', gwsr: o.gwsr || '', rtnMsg: o.rtn_msg || '', applied: !!o.applied,
    refundRows: (refunds || []).filter((r) => r.oid === o.id) });

  Hub.prototype.payMine = function (v) {
    const email = norm(v.user.email), now = this.now();
    const all = this.q('SELECT * FROM orders WHERE uid = ? OR email = ? ORDER BY created DESC LIMIT 300', v.user.uid, email);
    /* 2026-10-11 Andy：「只要還沒付費 就不能出現這樣 只有真的付費了 才能變更當前會員狀態」→ 會員端只列真的付過錢的：
       已付款／已開通／已退款／部分退款，以及銀行轉帳「已送出匯款資料」的（待確認、被退回看得到原因）。綠界待付款、未完成付款一律不列。 */
    const rows = all.filter((o) => o.applied || ['paid', 'active', 'refunded'].includes(o.status) || o.refunded > 0
      || (o.method === 'bank' && o.from_last5 && ['review', 'rejected'].includes(o.status)));
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
    const reqs = this.q("SELECT id, type, plan, note, created, status FROM sub_requests WHERE uid = ? AND type IN ('cancel', 'refund') ORDER BY created DESC LIMIT 50", v.user.uid);
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
    const left = o.amount - done;
    const bf = this.billFlags(o.email) || {};
    const first = bf.first_paid || o.paid_at || 0;
    let suggest = left, rule = '';
    if (first && now - first <= 7 * DAY && !bf.refund_used) { rule = '首次付款 7 天內：全額退款保證'; }
    else if (o.grant_to && o.grant_from && o.grant_to > now) {
      const ratio = Math.max(0, Math.min(1, (o.grant_to - Math.max(now, o.grant_from)) / (o.grant_to - o.grant_from)));
      suggest = Math.min(left, Math.round(o.amount * ratio)); rule = `超過 7 天：依未使用日數比例（剩 ${Math.ceil((o.grant_to - now) / DAY)} 天）`;
    } else { suggest = 0; rule = '這一筆的期間已經用完，政策上不退（可手動改金額）'; }
    const credit = o.method === 'ecpay' && /^Credit/.test(o.pay_type || '');
    return { left, suggest, rule, kind: credit ? 'ecpay' : 'manual', test: !!o.test || this.ecCfg().test, recur: !!o.recur && !o.parent, periodActive: o.period_state === 'active' };
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
        this.payEv(o.id, 'credit_query', st || q.text.slice(0, 200));
      } catch (e) { stage = ''; }
    }
    if (!stage) {
      /* 推估：付款時間早於「最近一次已經過去的台北 20:00」→ 已關帳；否則還在授權階段 */
      const now = this.now(), d = new Date(now + 8 * 3600 * 1000);
      let cut = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), 20 - 8, 0, 0);
      if (cut > now) cut -= DAY;
      stage = (o.paid_at || 0) < cut ? 'closed' : 'auth';
    }
    const steps = stage === 'closed' ? [['R', amount]] : stage === 'closing' ? (full ? [['E', o.amount], ['N', o.amount]] : [['C', o.amount - amount]]) : (full ? [['N', o.amount]] : [['C', o.amount - amount]]);
    for (const [act, amt] of steps) {
      const r = await this.ecPost('/CreditDetail/DoAction', { MerchantTradeNo: o.id, TradeNo: o.trade_no || '', Action: act, TotalAmount: String(amt) }, c.test ? c.host : ECPAY_PROD_HOST);
      this.payEv(o.id, 'doaction_' + act, r.text.slice(0, 300));
      if (r.form.CheckMacValue && !(await this.ecVerify(r.form))) return { ok: false, action: act, msg: '綠界回應驗章失敗' };
      if (String(r.form.RtnCode) !== '1') return { ok: false, action: act, msg: r.form.RtnMsg || `HTTP ${r.status}` };
    }
    return { ok: true, action: steps.map((s) => s[0]).join('+'), stage };
  };

  /* ---------------------------------------------------------------- 會員 API（JSON，走 subRoutes：Origin 白名單＋權杖）*/
  const consentOf = (b) => JSON.stringify({ at: subClean(b.consent_at, 40), ver: subClean(b.consent_version, 40), c: subClean(b.consent, 80) });
  const backOk = (hub, back) => { try { const u = new URL(String(back || '')); return hub.originOk(u.origin) ? u.origin + u.pathname : ''; } catch (e) { return ''; } };
  const newCount = (hub, uid, method) => hub.q('SELECT COUNT(*) AS c FROM orders WHERE uid = ? AND method = ? AND parent IS NULL AND created > ?', uid, method, hub.now() - DAY)[0].c;
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
      /* 2026-10-12 Andy：會員不能修改已送出的匯款資料；重送＝新增一筆，前一筆標「已作廢（已有最新匯款資料）」，每一筆都留時間與真實輸入的金額 */
      if (!['pending', 'review'].includes(o.status)) return this.json(req, { error: 'bad_status', status: o.status }, 409);
      const last5 = String(b.last5 || '').trim(), date = String(b.date || '').trim(), amt = b.amount;
      if (!/^\d{5}$/.test(last5)) return this.json(req, { error: 'bad_last5' }, 400);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Date.parse(date + 'T00:00:00+08:00') > this.now() + DAY || Date.parse(date + 'T00:00:00+08:00') < o.created - 2 * DAY) return this.json(req, { error: 'bad_date' }, 400);
      if (!Number.isInteger(amt) || amt < 1 || amt > 9999999) return this.json(req, { error: 'bad_amount' }, 400);
      let hist = []; try { hist = JSON.parse(o.reports || '[]'); if (!Array.isArray(hist)) hist = []; } catch (e) { hist = []; }
      if (hist.length >= 10) return this.json(req, { error: 'too_many_reports' }, 429);
      const at = this.now();
      hist = hist.map((r) => (r.state === 'active' ? { ...r, state: 'void', voidAt: at, voidWhy: '已有最新匯款資料' } : r));
      hist.push({ at, last5, date, amount: amt, note: subClean(b.note, 200), state: 'active' });
      this.paySet(o.id, { status: 'review', from_last5: last5, xfer_date: date, xfer_amount: amt, note: subClean(b.note, 200), reports: JSON.stringify(hist) });
      this.payEv(o.id, hist.length > 1 ? 'report_again' : 'report', { last5, date, amt, n: hist.length });
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
      if (!o || o.uid !== v.user.uid || !o.recur || o.parent) return this.json(req, { error: 'not_found' }, 404);
      const r = await this.payPeriodCancel(o.id, 'member');
      if (!r.ok) return this.json(req, { error: r.error, msg: r.msg || '' }, 502);
      return this.json(req, { ok: true, ...this.payMine(v) });
    },

    /* ---------------- 管理者（/v1/admin/* 另外有總閘：權杖必須是管理者）*/
    '/v1/admin/pay/list': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit(); this.payExpireLog();
      const rows = this.q('SELECT * FROM orders ORDER BY created DESC LIMIT 3000');
      const refunds = this.q('SELECT * FROM refunds ORDER BY created DESC');
      const names = {}; this.q('SELECT uid, name FROM users').forEach((u) => { names[u.uid] = u.name; });
      const orders = rows.map((o) => admOrder(o, refunds, names));
      const anomalies = orders.filter((o) => o.anomaly || o.actErr || (o.status === 'paid' && !o.applied)).map((o) => o.id);
      const now = this.now();
      const subs = this.paySubs();
      const expiring = subs.filter((s) => s.lastMethod === 'bank' && !s.autoRenew && s.expires > now && s.expires - now <= PAY_RENEW_DAYS * DAY).map((s) => s.email);
      const events = this.q("SELECT email, kind, plan, at, ref, detail FROM plan_events ORDER BY id DESC LIMIT 2000");
      const reqs = this.q("SELECT s.id, s.type, s.email, s.plan, s.note, s.created, s.status, u.name FROM sub_requests s LEFT JOIN users u ON u.uid = s.uid WHERE s.type IN ('cancel', 'refund') ORDER BY s.created DESC LIMIT 500");
      return this.json(req, { now, reqs, orders, refunds, subs, anomalies, expiring, events, bank: this.payBank(), test: this.ecCfg().test, status: PAY_STATUS });
    },
    '/v1/admin/pay/confirm': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id);
      if (!o || o.method !== 'bank') return this.json(req, { error: 'not_found' }, 404);
      if (o.applied) return this.json(req, { ok: true, dup: true, order: admOrder(o) });
      if (!['pending', 'review', 'expired'].includes(o.status)) return this.json(req, { error: 'bad_status', status: o.status }, 409);
      /* 2026-10-12 Andy：會員只是打開訂閱頁沒付款，管理者不該有確認鍵 → 沒回報匯款資料（沒有末 5 碼）的轉帳單一律不能確認入帳 */
      if (!o.from_last5) return this.json(req, { error: 'not_reported' }, 409);
      /* 2026-10-12 Andy：「若是發生他給 2000 但我沒注意到，就等於少收錢」→ 管理者必須輸入網銀實際入帳金額，少於應付不能開通 */
      const recv = b.received;
      if (!Number.isInteger(recv) || recv < 1 || recv > 9999999) return this.json(req, { error: 'need_received' }, 400);
      if (recv < o.amount) return this.json(req, { error: 'underpaid', amount: o.amount, received: recv }, 409);
      this.paySet(o.id, { recv_amount: recv });
      this.paySet(o.id, { status: 'paid', paid_at: o.xfer_date ? Date.parse(o.xfer_date + 'T12:00:00+08:00') : this.now() });
      this.payEv(o.id, 'confirm', { by: v.user.email, received: recv, amount: o.amount, reported: o.xfer_amount });
      const r = this.payActivate(o.id, 'admin:' + norm(v.user.email));
      if (!r.ok) return this.json(req, { error: r.error }, 500);
      return this.json(req, { ok: true, order: admOrder(this.payOrder(o.id)) });
    },
    '/v1/admin/pay/reject': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id);
      if (!o || o.method !== 'bank') return this.json(req, { error: 'not_found' }, 404);
      if (o.applied) return this.json(req, { error: 'applied' }, 409);
      const reason = subClean(b.reason, 200);
      if (!reason) return this.json(req, { error: 'need_reason' }, 400);
      this.paySet(o.id, { status: 'rejected', reject_reason: reason });
      this.payEv(o.id, 'reject', { by: v.user.email, reason });
      return this.json(req, { ok: true, order: admOrder(this.payOrder(o.id)) });
    },
    /* 已開通但帶異常註記（例如取消後才付款）→ 管理者看過後「標記已處理」，從異常清單拿掉 */
    '/v1/admin/pay/ack': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      if (!o.applied) return this.json(req, { error: 'not_applied' }, 409);
      this.paySet(o.id, { anomaly: null, act_err: null });
      this.payEv(o.id, 'ack', v.user.email);
      return this.json(req, { ok: true });
    },
    '/v1/admin/pay/note': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      this.paySet(o.id, { admin_note: subClean(b.note, 300) });
      return this.json(req, { ok: true });
    },
    /* 補開通（異常清單的一鍵）：綠界單先查一次單；查不到也可以強制（force，金額不符或綠界連不到時管理者自己判斷）*/
    '/v1/admin/pay/reactivate': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      let o = this.payOrder(b.id); if (!o) return this.json(req, { error: 'not_found' }, 404);
      if (o.applied) return this.json(req, { ok: true, dup: true });
      if (o.method === 'ecpay' && !o.parent && !b.force) {
        const q = await this.payQuery(o.id, 'admin_query');
        o = this.payOrder(o.id);
        if (o.applied) return this.json(req, { ok: true, via: 'query' });
        /* 查單沒能開通（沒付、金額不符、連不到綠界）→ 不自動開；要開請管理者看過後按「強制開通」（force） */
        return this.json(req, { error: q.error || 'unpaid', msg: q.error === 'amount_mismatch' ? '綠界金額跟訂單不符' : q.error === 'network' ? '連不到綠界' : '綠界查單顯示還沒付款' }, 409);
      }
      if (!b.force && o.status !== 'paid') return this.json(req, { error: 'unpaid' }, 409);
      this.paySet(o.id, { anomaly: null, status: 'paid', paid_at: o.paid_at || this.now() });
      this.payEv(o.id, 'reactivate', { by: v.user.email, force: !!b.force });
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
      if (!o.applied && !['paid', 'active'].includes(o.status)) return this.json(req, { error: 'not_paid' }, 409);
      const quote = this.payRefundQuote(o);
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
      this.q("UPDATE refunds SET status = 'done', action = ?, done_at = ? WHERE id = ?", res.action || '', this.now(), rid);
      const sum = this.q("SELECT COALESCE(SUM(amount), 0) AS s FROM refunds WHERE oid = ? AND status = 'done'", o.id)[0].s;
      this.paySet(o.id, { refunded: sum, status: sum >= o.amount ? 'refunded' : o.status });
      this.billUpsert(o.email, { refund_used: 1, trial_used: 1, refund_at: now });
      let cancel = null;
      const parent = o.parent ? this.payOrder(o.parent) : o;
      if (parent && parent.recur && parent.period_state === 'active') cancel = await this.payPeriodCancel(parent.id, 'refund');
      if (permAct === 'now') {
        const cur = this.q('SELECT plan, expires FROM perm WHERE email = ?', o.email)[0];
        if (cur && cur.plan === o.plan && (!cur.expires || cur.expires > now)) {
          this.q('UPDATE perm SET expires = ?, updated = ? WHERE email = ?', now - 1, now, o.email);   // effective() 判斷「到期日 < 現在」，減 1 毫秒＝當下就降
          this.planEv(o.email, 'refund_downgrade', o.plan, rid, `退款 NT$ ${amount}，立即回到註冊會員`);
        }
      } else this.planEv(o.email, 'refund_keep', o.plan, rid, `退款 NT$ ${amount}，用到 ${tpeDay((this.effective(o.email).expires) || now)} 才停`);
      this.payEv(o.id, 'refund', { rid, amount, perm: permAct, action: res.action });
      return this.json(req, { ok: true, refund: this.q('SELECT * FROM refunds WHERE id = ?', rid)[0], cancel, order: admOrder(this.payOrder(o.id)) });
    },
    '/v1/admin/pay/period_cancel': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.payInit();
      const r = await this.payPeriodCancel(String(b.id || ''), 'admin:' + norm(v.user.email));
      return r.ok ? this.json(req, { ok: true }) : this.json(req, { error: r.error, msg: r.msg || '' }, 502);
    },
    '/v1/admin/pay/bank/get': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      return this.json(req, { bank: this.payBank() });
    },
    '/v1/admin/pay/bank/put': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      if (b.clear === true) { this.setKv('pay_bank', ''); return this.json(req, { ok: true, bank: null }); }
      const bank = { bank_name: subClean(b.bank_name, 30), bank_code: String(b.bank_code || '').trim(), account: String(b.account || '').replace(/[\s-]/g, ''), holder: subClean(b.holder, 40) };
      if (!bank.bank_name || !bank.holder || !/^\d{3}$/.test(bank.bank_code) || !/^\d{6,20}$/.test(bank.account)) return this.json(req, { error: 'bad_input' }, 400);
      this.setKv('pay_bank', JSON.stringify(bank));
      return this.json(req, { ok: true, bank });
    },
  });

  /* ---------------------------------------------------------------- 綠界打進來的三支（不是瀏覽器 JSON：form-urlencoded、沒有 Origin）*/
  const formOf = async (req) => { const t = await req.text(); if (t.length > 20000) return null; return Object.fromEntries(new URLSearchParams(t)); };
  const txt = (s, status = 200) => new Response(s, { status, headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store' } });
  Hub.prototype.payNotify = async function (req) {
    this.payInit();
    const f = await formOf(req);
    if (!f || !(await this.ecVerify(f))) { this.payEv(f && f.MerchantTradeNo, 'notify_badmac', f ? JSON.stringify(f).slice(0, 300) : ''); return txt('0|CheckMacValue Error', 400); }
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
    try { this.payExpireLog(); this.q('DELETE FROM pay_events WHERE at < ?', this.now() - 400 * DAY); } catch (e) { /* 不擋其他清理 */ }
  };
  /* 刪除帳號：訂單、退款是交易紀錄（對帳、稅務），不跟著刪；只把 uid 斷開（docs/payment_checkout_1011.md 第 9 節）*/
  const payOrigDelete = Hub.prototype.deleteMe;
  Hub.prototype.deleteMe = async function (req, b) {
    const v = await this.auth(req, b || {});
    const res = await payOrigDelete.call(this, req, b);
    if (v && res.status === 200) { this.payInit(); this.q("UPDATE orders SET uid = '' WHERE uid = ?", v.user.uid); }
    return res;
  };
  const payOrigExpInit = Hub.prototype.expInit;
  Hub.prototype.expInit = function () { payOrigExpInit.call(this); this.payInit(); };
  for (const t of ['orders', 'refunds', 'plan_events', 'pay_events']) if (!EXPORT_TABLES.includes(t)) EXPORT_TABLES.push(t);
}
