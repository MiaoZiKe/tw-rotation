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

/* ============================================================================
   每日額度的「單位」（2026-10-07，docs/quota_plan.md；Andy：Plus 每日 50 次、Pro 不限）
   ----------------------------------------------------------------------------
   「一次」＝同一天（台北日期）、同一個單位只算一次。單位由**檔名**決定（伺服器說了算，前端改不到）。
   ★ 單位字串跟前端 site/quota.js 的 pageKey 一樣（2026-10-07 CEO：前後端同一份 key 規則）：個股＝代號（'2330'）、產業鏈＝'c.<鏈>'；
     沒有對象的付費分頁前端是「一次造訪」（<頁>.<分頁代號>，伺服器看不到瀏覽器分頁），伺服器退一步用 'p.<功能鍵>'（一天一次）。
     · 個股頁：stock/<代號>、m60/<代號>、hist/<代號>/p<N> 全部算同一個單位 <代號>
       —— 個股頁的總覽／營收／籌碼…分頁切換讀的是同一支 stock/<代號>，K 線翻頁是同一檔的 hist，都不另外扣。
     · 其他付費檔：一個付費分頁＝它的第一個功能鍵 p.<功能鍵>（例如 flow_v3、rrg_members、rotation 都是 p.flow.rot，
       同一個分頁要讀三支檔也只扣一次）。
     · 產業鏈剖析圖：目前所有產業鏈共用一支 supply_chain（p:ind.rel）—— 要做到「一張剖析圖一次」，
       pipeline 得先把它拆成每條鏈一支（chain/<鏈>），拆好之後這裡的 c.<鏈> 規則就會生效（見 docs/quota_plan.md 第 4 節）。
     · 免費檔（feats 空）回 null：不扣額度。
   ============================================================================ */
export function unitOf(name, tier) {
  tier = tier || tierOf(name);
  if (!tier || !tier.feats.length) return null;
  let m = /^(?:stock|m60)\/([0-9A-Z]{4,6})$/.exec(name) || /^hist\/([0-9A-Z]{4,6})\/p[0-9]{1,3}$/.exec(name);
  if (m) return m[1];
  m = /^chain\/([a-z0-9_]{1,30})$/.exec(name);
  if (m) return 'c.' + m[1];
  return 'p.' + tier.feats[0];
}

/* ============================================================================
   每個功能各自的每日次數（範本的 lims，site/quota.js 前端也在數）—— 伺服器端用「同一組單位字串」（2026-10-07，docs/quota_coverage.md）
   ----------------------------------------------------------------------------
   前端 quota.js 的 unitKey：個股頁所有功能的單位＝股票代號（例如 '2330'）。伺服器看得到的也只有檔名，所以：
     · stock/<代號>、m60/<代號>、hist/<代號>/p<N> → 單位 '<代號>'，要扣的功能＝這支檔的功能鍵＋'stock.page'（整個個股頁）
     · 其他付費檔（一支檔餵整頁、內容所有對象共用）→ null：伺服器分不出「看了幾次」，只能由前端計數（限制寫在 docs/quota_coverage.md）
   回 { unit, feats } 或 null。
   ============================================================================ */
export function limUnitOf(name, tier) {
  tier = tier || tierOf(name);
  if (!tier || !tier.feats.length) return null;
  const m = /^(?:stock|m60)\/([0-9A-Z]{4,6})$/.exec(name) || /^hist\/([0-9A-Z]{4,6})\/p[0-9]{1,3}$/.exec(name);
  if (!m) return null;
  return { unit: m[1], feats: [...tier.feats, 'stock.page'] };
}
