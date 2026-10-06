/* 資料檔分級（docs/datagw_plan.md 第 1 節的機器版）。
 *
 * 每支 site/data/*.json 對應到「看它需要哪些功能開關」（site/features.js 的 id）。
 *   · feats 空陣列 ＝ 免費檔：任何人都拿得到（正式上線時照舊放公開 CDN；gateway 也能回，方便前端統一走一條路）。
 *   · feats 非空   ＝ 付費候選：要看的人「生效的功能開關」裡，這些鍵沒有一個是 false 才放行。
 *     開關由 Andy 在 #admin/perm 對「訪客／免費會員／付費範本」設定 —— 跟畫面上的鎖頭是同一份設定，
 *     所以不會出現「畫面鎖了、檔案卻拿得到」或反過來的情況。
 *   · 不在這張表上的檔名 ＝ 一律 404（白名單，fail-closed）。delivery（交付清單，含 Andy 原話）刻意不列。
 *
 * ⚠ 一支檔餵多個功能（例如 stock/<代號> 同時餵營收、獲利、法人分頁）時，第一階段是「整支檔」的粒度。
 *   要做到「營收免費、法人付費」得把檔案拆開（第二階段 pipeline 的工作，見 docs/datagw_plan.md）。
 */
export const TIERS = [
  // ---- 免費（首頁、導覽、搜尋清單用）
  ['meta', []], ['stocks', []], ['groups_today', []], ['logos', []], ['sparks', []],
  ['index_ohlc', []], ['index_intraday', []], ['index_lastday', []], ['intl', []],
  ['news_head', []], ['updown', []], ['rrg_lite', []], ['hist/index', []],
  ['market_heat', ['ov.heat']],
  // ---- 資金流向
  ['flow_v3', ['flow.rot']], ['rrg_members', ['flow.rot']], ['rotation', ['flow.rot']],
  ['sankey_daily', ['flow.sankey']], ['concentration', ['flow.conc']], ['concentration_members', ['flow.conc']],
  // ---- 產業
  ['industry_map', ['ind.map']], ['groups_detail', ['ind.groups']], ['supply_chain', ['ind.rel']],
  ['group_valuation', ['ind.groups']], ['relative_strength', ['ind.groups']],
  // ---- 題材／熱力
  ['themes', ['heat.theme']],
  // ---- 市場明細／週期統計
  ['inst_streak', ['mkt.streak']], ['trust_streak', ['mkt.streak']], ['ma_breadth', ['mkt.ma']], ['candidates', ['mkt.cand']],
  ['seasonality_v3', ['season.month']], ['seasonality', ['season.month']],
  // ---- 個股
  ['fundamental', ['stock.profit']], ['news', ['stock.news']], ['broker_views', ['stock.ai']],
  [/^stock\/[0-9A-Z]{4,6}$/, ['stock.overview']],
  [/^m60\/[0-9A-Z]{4,6}$/, ['stock.k_hour']],
  [/^hist\/[0-9A-Z]{4,6}\/p[0-9]{1,3}$/, ['stock.k_day']],
  // ---- 選股、ETF、財經日曆
  ['explore', ['explore.page']], ['etf', ['etf.list']], ['etf_series', ['etf.returns']], ['earnings', ['earn.page']],
];

export const NAME_RE = /^[a-z0-9_]{1,40}(\/[0-9A-Za-z_]{1,20}){0,2}$/;

/* 回 { feats } 或 null（不在白名單） */
export function tierOf(name) {
  if (typeof name !== 'string' || !NAME_RE.test(name)) return null;
  for (const [k, feats] of TIERS) if (typeof k === 'string' ? k === name : k.test(name)) return { feats };
  return null;
}

/* 這個人（feats＝生效的功能開關）能不能拿這支檔。缺鍵＝預設開（跟 site/features.js 的 def:true 一致）。*/
export function allowed(tier, feats) {
  return tier.feats.every((k) => !(feats && feats[k] === false));
}
