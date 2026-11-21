/* ============================================================================ 全市場信用風險（官方儀表板）人工登錄（2026-11-06）
   Andy 11-06：證交所「臺股儀表板」信用交易頁的條款不准自動抓 →「每天看儀表板，手動把五個數字（維持率、追繳戶數、追繳金額、
   處分戶數、處分金額）填進網站，並標註來源和日期」。站主在 #market/credit 的登錄表單填，所有訪客都看得到。
   · 公開讀：/v1/mdash/get {} → {rows:[…], src:'server'|'seed'}（訪客也要看得到，所以不用登入）
   · 管理者寫：/v1/admin/mdash/put {t, row:{d, mmr, call_n, call_amt, disp_n, disp_amt, note}} → {rows}（同一天＝覆蓋）
   · 管理者刪：/v1/admin/mdash/del {t, d} → {rows}
     （/v1/admin/ 開頭：worker.js 管理權限區塊已統一擋非管理者 403；這裡再驗一次，不靠外層）
   存在 kv（鍵 margin_dash，JSON 陣列，依日期排序），所以備份匯出（kv 表）一起帶走，不必新增資料表。
   ★ 從來沒存過（kv 空）時回種子 SEED（Andy 11-05 截圖上的兩筆）；管理者存過一次（包含刪到空）就以存的為準。
     SEED 要跟 site/margin_dashboard_seed.json 一致：tests/margindash.test.mjs 會比對，對不上就測試失敗。
   不記是誰填的（不寫 email）。
   檢查：日期 YYYY-MM-DD 且在 2020～2100；維持率 100～300；戶數 0～9,999,999 整數；金額（億元）0～100,000；
         五個數字至少要有一個；備註 ≤ 120 字。最多 3000 筆（約 12 年）。
   ============================================================================ */
export const MDASH_SEED = [
  { d: '2026-10-30', mmr: null, call_n: 199, call_amt: null, disp_n: 21, disp_amt: null, note: '' },
  { d: '2026-11-05', mmr: 159.77, call_n: 2352, call_amt: 26.86, disp_n: 222, disp_amt: 6.42, note: '' },
];
const KV = 'margin_dash', MAX_ROWS = 3000, NOTE_MAX = 120;
const D_RE = /^(20[2-9]\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;
const FIELDS = ['mmr', 'call_n', 'call_amt', 'disp_n', 'disp_amt'];
const RULES = {
  mmr: (v) => v >= 100 && v <= 300,
  call_n: (v) => Number.isInteger(v) && v >= 0 && v <= 9999999,
  disp_n: (v) => Number.isInteger(v) && v >= 0 && v <= 9999999,
  call_amt: (v) => v >= 0 && v <= 100000,
  disp_amt: (v) => v >= 0 && v <= 100000,
};
const r2 = (v) => Math.round(v * 100) / 100;

/** 檢查一筆；回 [錯誤代碼, null] 或 [null, 乾淨的列] */
export function mdashClean(row) {
  if (!row || typeof row !== 'object' || Array.isArray(row)) return ['bad_row', null];
  const d = String(row.d || '');
  if (!D_RE.test(d) || Number.isNaN(Date.parse(d + 'T00:00:00Z')) || new Date(d + 'T00:00:00Z').toISOString().slice(0, 10) !== d) return ['bad_date', null];
  const out = { d };
  let n = 0;
  for (const k of FIELDS) {
    const v = row[k];
    if (v === null || v === undefined || v === '') { out[k] = null; continue; }
    if (typeof v !== 'number' || !Number.isFinite(v) || !RULES[k](v)) return ['bad_' + k, null];
    out[k] = k.endsWith('_n') ? v : r2(v);
    n++;
  }
  if (!n) return ['empty', null];
  const note = row.note == null ? '' : String(row.note);
  if (note.length > NOTE_MAX) return ['bad_note', null];
  out.note = note.replace(/[\u0000-\u001f<>]/g, ' ').trim();
  return [null, out];
}

export function installMarginDash(Hub) {
  const read = (hub) => {
    const raw = hub.kv(KV);
    if (raw == null) return { rows: MDASH_SEED.map((r) => ({ ...r })), src: 'seed' };
    try { const a = JSON.parse(raw); return { rows: Array.isArray(a) ? a.filter((r) => r && D_RE.test(r.d)) : [], src: 'server' }; } catch (e) { return { rows: [], src: 'server' }; }
  };
  const save = (hub, rows) => { rows.sort((a, b) => (a.d < b.d ? -1 : a.d > b.d ? 1 : 0)); hub.setKv(KV, JSON.stringify(rows)); };
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/mdash/get': async function (req) { return this.json(req, read(this)); },
    '/v1/admin/mdash/put': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      const [err, row] = mdashClean(b.row);
      if (err) return this.json(req, { error: err }, 400);
      const cur = read(this).rows.filter((r) => r.d !== row.d);
      if (cur.length >= MAX_ROWS) return this.json(req, { error: 'too_many' }, 400);
      cur.push({ ...row, at: this.now() });
      save(this, cur);
      return this.json(req, { ok: true, ...read(this) });
    },
    '/v1/admin/mdash/del': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      const d = String(b.d || '');
      if (!D_RE.test(d)) return this.json(req, { error: 'bad_date' }, 400);
      const all = read(this).rows, cur = all.filter((r) => r.d !== d);
      if (cur.length === all.length) return this.json(req, { error: 'not_found' }, 404);
      save(this, cur);
      return this.json(req, { ok: true, ...read(this) });
    },
  });
}
/* ============================================================================ 全市場信用風險人工登錄區塊結束 */
