/* ============================================================================ 自設提醒的 email 通知（2026-11-02）
   Andy 11-02：「自設提醒條數 plus = 體驗 最多 5 條，pro 先 20 條，通知方式 email 和網頁通知」。
   · 每個交易日台北 18:40 一次（wrangler.toml cron "40 10 * * 1-5"，UTC）：抓公開的 https://liguligu-puipui.com/data/digest.json（事實表，
     跟瀏覽器載入的是同一份），逐一比對 alerts 表中 nt.m（email 通知）為真的條件。
   · 判斷邏輯＝site/digest.js 的 evalRule／ruleText／邊緣觸發（run() 裡 rev／exdiv／其他三種各自的規則），一行一行移植；
     tests/alertmail.test.mjs 把 digest.js 的原始碼切出來跑，跟這裡的結果逐案比對，兩邊對不上就部署失敗。改一邊要改另一邊。
   · 邊緣觸發：上次不成立 → 這次成立才寄（狀態存 alert_mail_st，跟瀏覽器的 st.met 同一個概念）；新建的營收條件先記下現有那一期、不補寄。
   · 寄信＝寫進 pay.js 的寄信佇列 mail_out（每 10 分鐘 paySweep 送出）。沒設 RESEND_API_KEY／MAIL_FROM 時只進佇列、不報錯、不送。
   · 每人每天最多 5 封（alert_mail_sent）；超過的條件這次不更新狀態，下次交易日仍會補寄（不會因為額度被吃掉就永遠不寄）。
   · 同一個資料日只處理一次（kv alertmail_asof）：假日／資料還沒更新時 asof 沒變，直接跳過。
   · 法遵 L-13：信件只寫「你設定的條件成立：…」＋資料日期＋「非投資建議」＋取消方式，不含評分、排名、買賣建議。
   ============================================================================ */
export const ALERT_MAIL_DAILY_MAX = 5;
export const DIGEST_URL = 'https://liguligu-puipui.com/data/digest.json';
const SITE = 'https://liguligu-puipui.com/';

/* ---- 以下四個小工具與 evalAlert／alertRuleText 是 site/digest.js 的逐行移植（不要「順手改好」，改了測試會紅）---- */
const num = (v, d) => (v == null || !isFinite(v) ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: d == null ? 0 : d, minimumFractionDigits: d || 0 }));
const sgn = (v, d) => (v == null || !isFinite(v) ? '—' : (v > 0 ? '+' : '') + num(v, d));
const md = (iso) => String(iso || '').slice(5).replace('-', '/');
const dayStart = (iso) => { const m = /^(\d{4})-(\d\d)-(\d\d)/.exec(iso || ''); return m ? Date.UTC(+m[1], m[2] - 1, +m[3]) - 8 * 3600e3 : Date.now(); };
const daysTo = (a, b) => Math.round((dayStart(b) - dayStart(a)) / 86400e3);
export function alertRuleText(r) {
  if (r.type === 'rev') return '月營收公布時';
  if (r.type === 'streak') return `${{ total: '三大法人合計', foreign: '外資', trust: '投信' }[r.who]}連續${r.side === 'buy' ? '買超' : '賣超'} ${r.n} 天以上`;
  if (r.type === 'above') return `收盤價高於 ${num(r.x, 2)} 元`;
  if (r.type === 'below') return `收盤價低於 ${num(r.x, 2)} 元`;
  return `距離除息日 ${r.n} 天內`;
}
export function evalAlert(asof, r, s) {
  if (!s) return { met: false };
  if (r.type === 'rev') return s.r ? { met: true, key: s.r.ym, text: `${s.n}（${r.code}）公布 ${s.r.ym} 月營收 ${num(s.r.rev, 1)} 億元${s.r.yoy != null ? `，年增 ${sgn(s.r.yoy, 1)}%` : ''}${s.r.mom != null ? `、月增 ${sgn(s.r.mom, 1)}%` : ''}` } : { met: false };
  if (r.type === 'above' || r.type === 'below') {
    const hit = r.type === 'above' ? s.c > r.x : s.c < r.x;
    return { met: hit, text: `${s.n}（${r.code}）收盤價 ${num(s.c, 2)} 元，${r.type === 'above' ? '高於' : '低於'}你設定的 ${num(r.x, 2)} 元` };
  }
  if (r.type === 'streak') {
    if (!s.k) return { met: false };
    const k = s.k[{ foreign: 0, trust: 1, total: 2 }[r.who]], hit = r.side === 'buy' ? k >= r.n : k <= -r.n;
    const lot = s.i ? s.i[{ foreign: 0, trust: 1, total: 3 }[r.who]] : null;
    return { met: hit, text: `${s.n}（${r.code}）${{ total: '三大法人合計', foreign: '外資', trust: '投信' }[r.who]}已連續${r.side === 'buy' ? '買超' : '賣超'} ${Math.abs(k)} 天（最近一日 ${sgn(lot)} 張）` };
  }
  if (r.type === 'exdiv' && s.x) {
    const dd = daysTo(asof, s.x.d);
    return { met: dd >= 0 && dd <= r.n, key: s.x.d, text: `${s.n}（${r.code}）除息日 ${md(s.x.d)}，還有 ${dd} 天${s.x.a != null ? `（現金股利 ${num(s.x.a, 2)} 元）` : ''}` };
  }
  return { met: false };
}
/* 邊緣觸發（digest.js run() 的提醒段）：回 { send, st }；st 是這條條件新的狀態 */
export function alertStep(st0, r, e) {
  const st = { ...(st0 || {}) };
  let send = false;
  if (r.type === 'rev') {
    if (st.key === undefined) st.key = e.key || '';
    else if (e.met && e.key !== st.key) { st.key = e.key; send = true; }
  } else if (r.type === 'exdiv') {
    if (e.met && e.key !== st.key) { st.key = e.key; send = true; }
  } else if (e.met && !st.met) send = true;
  st.met = !!e.met;
  return { send, st };
}
const hash = (str) => { let h1 = 0x811c9dc5, h2 = 0x01000193; for (const ch of String(str)) { const c = ch.codePointAt(0); h1 = Math.imul(h1 ^ c, 16777619) >>> 0; h2 = Math.imul(h2 + c, 2246822519) >>> 0; } return h1.toString(36) + h2.toString(36); };

export function installAlertMail(Hub, { tpeDay }) {
  Hub.prototype.alertMailInit = function () {
    if (this._amOk) return;
    this.q('CREATE TABLE IF NOT EXISTS alert_mail_st (uid TEXT, rid TEXT, met INTEGER, key TEXT, asof TEXT, PRIMARY KEY (uid, rid))');
    this.q('CREATE TABLE IF NOT EXISTS alert_mail_sent (uid TEXT, day TEXT, n INTEGER, PRIMARY KEY (uid, day))');
    this.alertInit(); this.payInit();
    this._amOk = true;
  };
  /* 跑一輪。digest 可以由呼叫端給（測試），沒給就去抓公開網址。回 { skipped?, asof, sent, queued, dropped } */
  Hub.prototype.alertMailRun = async function (digest) {
    this.alertMailInit();
    let d = digest;
    if (!d) {
      try { const r = await fetch(this.env.DIGEST_URL || DIGEST_URL, { headers: { 'cache-control': 'no-cache' } }); d = r.ok ? await r.json() : null; } catch (e) { d = null; }
    }
    if (!d || !d.s || !d.asof) return { skipped: 'no_digest' };
    if (this.kv('alertmail_asof') === d.asof) return { skipped: 'same_asof', asof: d.asof };
    const day = tpeDay(this.now()), out = { asof: d.asof, queued: 0, dropped: 0 };
    for (const row of this.q('SELECT a.uid AS uid, a.data AS data, u.email AS email FROM alerts a JOIN users u ON u.uid = a.uid')) {
      let rules; try { rules = JSON.parse(row.data || '[]'); } catch (e) { continue; }
      const email = String(row.email || '').toLowerCase();
      if (!email || !Array.isArray(rules)) continue;
      const live = new Set(rules.map((r) => r.id));
      for (const g of this.q('SELECT rid FROM alert_mail_st WHERE uid = ?', row.uid)) if (!live.has(g.rid)) this.q('DELETE FROM alert_mail_st WHERE uid = ? AND rid = ?', row.uid, g.rid);
      for (const r of rules) {
        if (r.on === false || !r.nt || r.nt.m !== true) {
          /* 沒開 email 的條件不留狀態：以後才打開時，等同新建（營收先記現有那一期、價格當下成立就寄一次）*/
          this.q('DELETE FROM alert_mail_st WHERE uid = ? AND rid = ?', row.uid, r.id);
          continue;
        }
        const old = this.q('SELECT met, key FROM alert_mail_st WHERE uid = ? AND rid = ?', row.uid, r.id)[0];
        const e = evalAlert(d.asof, r, d.s[r.code]);
        const { send, st } = alertStep(old ? { met: !!old.met, key: old.key == null ? undefined : old.key } : undefined, r, e);
        if (send) {
          const used = (this.q('SELECT n FROM alert_mail_sent WHERE uid = ? AND day = ?', row.uid, day)[0] || { n: 0 }).n;
          if (used >= ALERT_MAIL_DAILY_MAX) { out.dropped++; continue; }     // 額度滿：狀態不更新，下次還會補寄
          const nm = (d.s[r.code] || {}).n || r.code;
          const subject = `【哩股哩股】提醒：${nm} ${alertRuleText(r)}`;
          const body = `你設定的條件成立：${e.text}\n資料日期：${d.asof}\n條件由你自設，成立不代表買賣時機；公開資料整理，非投資建議。\n\n不想再收到這封信：到 ${SITE}#watch 的「自設提醒」把這條的 email 通知關掉。\n哩股哩股 ${SITE}`;
          this.q('INSERT OR IGNORE INTO mail_out (id, email, subject, body, created, status) VALUES (?, ?, ?, ?, ?, ?)', 'a' + hash(row.uid + '|' + r.id + '|' + d.asof), email, subject.slice(0, 150), body.slice(0, 3000), this.now(), 'pending');
          this.q('INSERT INTO alert_mail_sent (uid, day, n) VALUES (?, ?, 1) ON CONFLICT(uid, day) DO UPDATE SET n = n + 1', row.uid, day);
          out.queued++;
        }
        this.q('INSERT INTO alert_mail_st (uid, rid, met, key, asof) VALUES (?, ?, ?, ?, ?) ON CONFLICT(uid, rid) DO UPDATE SET met = excluded.met, key = excluded.key, asof = excluded.asof',
          row.uid, r.id, st.met ? 1 : 0, st.key === undefined ? null : st.key, d.asof);
      }
    }
    this.q('DELETE FROM alert_mail_sent WHERE day < ?', tpeDay(this.now() - 3 * 86400 * 1000));
    this.setKv('alertmail_asof', d.asof);
    return out;
  };
  /* 內部請求（Worker 自己的 scheduled() 打進來；主機 internal.cron 外面打不到）*/
  const origFetch = Hub.prototype.fetch;
  Hub.prototype.fetch = async function (req) {
    const u = new URL(req.url);
    if (u.hostname === 'internal.cron' && u.pathname === '/cron/alert-mail') {
      let r; try { r = await this.alertMailRun(); } catch (e) { r = { error: String(e && e.message || e).slice(0, 100) }; }
      return new Response(JSON.stringify(r));
    }
    return origFetch.call(this, req);
  };
  /* 刪帳號：狀態一起刪 */
  const origDelete = Hub.prototype.deleteMe;
  Hub.prototype.deleteMe = async function (req, b) {
    const v = await this.auth(req, b || {});
    const res = await origDelete.call(this, req, b);
    if (v && res.status === 200) { try { this.alertMailInit(); this.q('DELETE FROM alert_mail_st WHERE uid = ?', v.user.uid); this.q('DELETE FROM alert_mail_sent WHERE uid = ?', v.user.uid); } catch (e) { /* 略 */ } }
    return res;
  };
}
