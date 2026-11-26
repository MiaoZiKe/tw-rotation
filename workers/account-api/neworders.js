/* ============================================================================ 每日新訂單檢查（2026-11-26）
   Andy：「需要新增這機制，確認每天是否有新訂單」（起因：管理區「訂閱申請」出現兩筆 [預約開放通知]，他分不出是不是真訂閱）。
   · POST /v1/orders/daily/bot  { op:'check'|'ack', upto? }   機器路由：不檢查 Origin，只認 Authorization: Bearer <ARTICLE_BOT_KEY 或 BACKUP_TOKEN>
     （ARTICLE_BOT_KEY 由 deploy-account-worker.yml 從 CLOUDFLARE_API_TOKEN 推導寫入；每日工作流程用同一個公式算 → Andy 不必設任何新金鑰）
   · check：回「上次確認之後」的新資料（水位 kv neworders_wm；從沒確認過＝近 24 小時；最多回溯 7 天），分四類：
       subscribe 真訂閱申請（sub_requests type=subscribe、備註不是 [預約開放通知]）
       reserve   冷啟動預約（備註開頭 [預約開放通知]，不扣款）
       cancel／refund 取消、退款申請
       orders    金流訂單（orders 表，只算 parent 為空的首單、不含測試單），再依狀態分
     只回數量與逐筆的「類型／方案／時間」，不回 email（工作流程會把摘要貼到 public repo 的 issue）。
     有「需要處理」的新單（真訂閱、取消、退款、金流訂單）時，順便用 payNotifyOwner 寄信給站主＋放管理者鈴鐺（ref 冪等：同一個水位只寄一次）。
   · ack { upto }：確認那一批已經送達（issue 開成功）才推進水位；失敗就不推，明天會連同今天一起補報，不會漏。
   ============================================================================ */
const DAY = 86400 * 1000;
const WM_KEY = 'neworders_wm';
const RESERVE_RE = /^\s*\[預約開放通知\]/;
export function classifyRequest(r) {
  const t = r.type || 'subscribe';
  if (t === 'cancel' || t === 'refund') return t;
  return RESERVE_RE.test(String(r.note || '')) ? 'reserve' : 'subscribe';
}
export function installNewOrders(Hub) {
  const eq = (a, b) => { if (a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0; };
  const tpe = (ms) => new Date(ms + 8 * 3600e3).toISOString().slice(0, 16).replace('T', ' ');
  Hub.prototype.ndCheck = function (now) {
    this.billInit();
    let wm = Number(this.kv(WM_KEY)) || 0;
    const floor = now - 7 * DAY;
    if (!wm) wm = now - DAY;
    if (wm < floor) wm = floor;
    const out = { since: wm, upto: now, sinceTpe: tpe(wm), uptoTpe: tpe(now), subscribe: 0, reserve: 0, cancel: 0, refund: 0, orders: 0, items: [] };
    for (const r of this.q('SELECT id, plan, period, note, created, status, type FROM sub_requests WHERE created > ? AND created <= ? ORDER BY created', wm, now)) {
      const k = classifyRequest(r); out[k]++;
      out.items.push({ kind: k, plan: r.plan, period: r.period, at: tpe(r.created) });
    }
    try {
      this.payInit();
      for (const o of this.q('SELECT id, plan, period, amount, method, status, created FROM orders WHERE created > ? AND created <= ? AND parent IS NULL AND COALESCE(test, 0) = 0 ORDER BY created', wm, now)) {
        out.orders++;
        out.items.push({ kind: 'order', plan: o.plan, period: o.period, amount: o.amount, method: o.method, status: o.status, at: tpe(o.created) });
      }
    } catch (e) { /* 金流表還沒建＝沒有訂單 */ }
    out.actionable = out.subscribe + out.cancel + out.refund + out.orders;
    return out;
  };
  const origFetch = Hub.prototype.fetch;
  Hub.prototype.fetch = async function (req) {
    if (req.method !== 'POST' || new URL(req.url).pathname !== '/v1/orders/daily/bot') return origFetch.call(this, req);
    try {
      const h = String(req.headers.get('Authorization') || ''), got = h.startsWith('Bearer ') ? h.slice(7).trim() : '';
      const keys = [this.env.ARTICLE_BOT_KEY, this.env.BACKUP_TOKEN].map((k) => String(k || '')).filter((k) => k.length >= 16);
      if (!got || !keys.some((k) => eq(got, k))) return this.json(req, { error: 'forbidden' }, 403);
      const raw = await req.text(); let b = {};
      try { b = raw.length <= 2048 ? JSON.parse(raw || '{}') || {} : {}; } catch (e) { b = {}; }
      const now = this.now();
      if (b.op === 'ack') {
        const upto = Number(b.upto);
        if (!Number.isFinite(upto) || upto > now + 60e3 || upto < now - 8 * DAY) return this.json(req, { error: 'bad_upto' }, 400);
        if (upto > (Number(this.kv(WM_KEY)) || 0)) this.setKv(WM_KEY, upto);
        return this.json(req, { ok: true, wm: Number(this.kv(WM_KEY)) });
      }
      if (b.op !== 'check') return this.json(req, { error: 'bad_op' }, 400);
      const r = this.ndCheck(now);
      if (r.actionable > 0) {
        const parts = [];
        if (r.orders) parts.push(`金流訂單 ${r.orders}`); if (r.subscribe) parts.push(`訂閱申請 ${r.subscribe}`);
        if (r.cancel) parts.push(`取消申請 ${r.cancel}`); if (r.refund) parts.push(`退款申請 ${r.refund}`);
        this.payNotifyOwner(`每日新訂單檢查：${parts.join('、')}（另有預約 ${r.reserve} 筆）`,
          `${tpe(r.since)} ～ ${tpe(r.upto)}（台北）新增：\n${parts.join('\n')}\n預約開放通知（不扣款）：${r.reserve}\n\n到管理區「付款與訂單」「意見反饋與訂閱申請」處理。`, 'daily-' + r.upto, '每日檢查：');
      }
      return this.json(req, r);
    } catch (e) {
      return this.json(req, { error: 'server', detail: String(e && e.message || e).slice(0, 200) }, 500);
    }
  };
}
