/* ============================================================================
   ETF 專區（#etf）—— Andy 2026-10-05（參考別家 ETF 專區的截圖，名稱與版面自己做）
   規格與每個數字的口徑：docs/etf_page_spec.md（分類規則、熱門定義、殖利率、年化報酬、填息天數）。

   版面（2026-10-05 第二版，Andy：「配息行事曆放最上面」「每個分類頁內並排前 5」「自選比較清單」）：
     ① 配息行事曆（7 欄真月曆，格內直接寫當天除息的代號與金額，點格子右側展開當天清單＋填息天數）
     ② 分類分頁列（配息型／市值型／…，預設配息型，無「全部」）＋期間（3／5／10 年／自訂，只影響報酬率）
     ③ 分類分頁才有、三張同高並排：最近最受歡迎前 5｜報酬率前 5（含息年化）｜殖利率前 5（附平均填息天數）
        「其他」與「槓桿反向」不出這三張（Andy：「其他 ETF 的不用」）。
     ④ 報酬比較（自選）：「加入比較」可搜尋多選（限該分類、上限 8 檔、預設報酬前 5），依分類分開記在 localStorage
     ⑤ ETF 一覽（卡片清單，點卡片進個股頁）
   舊版的「前五名報酬比較」（只有配息型／市值型兩組）整張由 ③④ 取代。

   資料：data/etf.json（開頁就讀）＋ data/etf_series.json（全部 ETF 的週線走勢，自選比較才讀）。
   ⚠ 預覽分支吃的是正式站的資料，etf.json 上正式站之前不存在 —— 那時退回 stocks.json（ETF 也在裡面）
     列出卡片清單與名稱分類，其他卡寫「尚無資料」，不留空白、不編數字（10-06 廢話普查：不寫「資料準備中」這種交代排程的話）。
   排版紀律（Andy：「所有文字單行、操作不影響排版」）：所有列都 nowrap＋省略號；月曆固定 6 列、清單固定高；
     比較表保留 8 列的高度；分頁鈕選中不加粗（加粗會變寬、整排往旁邊擠）。
   驗收：scripts/_uitest.py「ETF專區1005」。
   ========================================================================== */
(function () {
  'use strict';
  const A = () => window.App;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const LS = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } },
  };
  const CATS = ['配息型', '市值型', '主題型', '主動式', '債券型', '槓桿反向', '其他'];   // 2026-10-06 Andy：「槓桿反向」與「債券型」交換
  const NO_RANK = { 其他: 1, 槓桿反向: 1 };   // 不出「前 5 名」三張卡的分頁（Andy：「其他 ETF 的不用」；10-05 再加槓桿反向：「這兩個都比較少人做」）
  const CAT_TONE = { 配息型: 'amber', 市值型: 'cyan', 主題型: 'violet', 債券型: 'lime', 槓桿反向: 'up', 主動式: 'cyan', 其他: 'ink3' };
  const PAGE = 48;   // 一次列幾張卡（「顯示更多」再加）
  const CMP_MAX = 8; // 自選比較上限：再多折線就分不出誰是誰
  const CAL_ROWS = 6; // 月曆固定 6 列：每個月都一樣高，切月不會讓下面的卡上下跳
  const WD = ['日', '一', '二', '三', '四', '五', '六'];

  /* ---- 名稱分類（只給「etf.json 還不存在」的退回模式用）：跟 pipeline/compute/etf.py classify() 同一套規則。
     少了「近 400 天除息 ≥ 4 次」那一條（退回模式沒有配息資料），所以名稱沒寫「息」的月配 ETF 會落在主題型 ——
     畫面上有寫「依名稱暫分」。改規則兩邊一起改。 */
  const RE = {
    lev: /正2|反1|反向|槓桿|正向2|2倍|-1倍/, bond: /債|美債|公債|投資級|非投等/,
    mcap: /台灣50|台50|臺灣50|中型100|加權|MSCI台灣|摩台|富時台灣|台灣領袖/,
    div: /高股息|高息|股息|收益|優息|月配|季配|息收|股利|優利|高利|穩利|配息|高收/,
    com: /^期|黃金|原油|白銀|黃豆|小麥|商品|美元|日圓|期街口/,
  };
  function classify(code, name) {
    const c = String(code), n = String(name || ''), t = c.slice(-1);
    if (t === 'L' || t === 'R' || RE.lev.test(n)) return '槓桿反向';
    if (t === 'B' || RE.bond.test(n)) return '債券型';
    if (t === 'U' || RE.com.test(n)) return '其他';
    if (t === 'A' || n.indexOf('主動') === 0) return '主動式';
    if (RE.mcap.test(n) && !/正2|反1/.test(n)) return '市值型';
    if (RE.div.test(n)) return '配息型';
    return n ? '主題型' : '其他';
  }

  const S = { data: null, series: null, fallback: false, cat: '配息型', sort: 'tv', shown: PAGE, pop: 'holders',
    month: null, day: null, per: '5y', from: null, basis: 'tr', cmp: {}, msg: '' };
  const pct = (v, d = 1) => (v == null || Number.isNaN(v) ? '—' : (v > 0 ? '+' : '') + (v * 100).toFixed(d) + '%');
  const pctU = (v, d = 2) => (v == null || Number.isNaN(v) ? '—' : (v * 100).toFixed(d) + '%');
  const yi = (v) => (v == null ? '—' : A().fmt.yi(v));
  const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : 'flat');
  const todayTW = () => new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);   // 台北日期（容器與使用者都可能不在 +8）

  /* 填息：沿用個股除權息分頁的口徑（pipeline/compute/etf.py fill_info）——除息日算第 1 個交易日。
     已填 → 「N 天」；還沒填 → 「尚未填息（已 N 天）」；除息日不在行情裡／還沒除息 → 「—」。*/
  const fillTxt = (f, w) => (f != null ? `${f} 天` : w != null ? `尚未填息（已 ${w} 天）` : '—');

  function injectCSS() {
    if (document.getElementById('etfCss')) return;
    const s = document.createElement('style'); s.id = 'etfCss';
    s.textContent = `
#v-etf .card{margin-bottom:var(--sp-3)}
#v-etf .card h3{flex-wrap:nowrap;white-space:nowrap;min-width:0}
#v-etf .card h3 small{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-etf .row.spread{flex-wrap:nowrap;gap:10px;min-width:0}
#v-etf .seg{flex:none}
#v-etf .seg button{white-space:nowrap}
/* 選中不加粗：加粗會讓那顆鈕變寬、整排往旁邊擠（Andy：「操作不影響排版」）*/
#v-etf .seg button.on{font-weight:inherit;text-shadow:.35px 0 0 currentColor}
#v-etf .etfq{margin:2px 0 10px;font-size:13px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-etf .etfq b{color:var(--ink)}
#v-etf .etfprep{padding:14px 16px;border:1px dashed var(--line-2);border-radius:10px;color:var(--ink-2);font-size:13.5px;line-height:1.6}
#v-etf .etfrow{display:flex;flex-wrap:nowrap;gap:8px;align-items:center;white-space:nowrap}
#v-etf .etfrow .sp{flex:1}
#v-etf .note1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
/* ---- 分類列 */
#v-etf .etfcatbar{display:flex;align-items:center;gap:10px;margin:0;white-space:nowrap;min-width:0}
#v-etf .etfcatbar .seg{overflow:hidden;flex:0 1 auto;min-width:0}
/* 分類頁籤：全站共用 .nbsw（產業地圖同款資料夾分頁，DECISIONS #321）；只補「不擠掉右邊期間」 */
#v-etf .etfcatbar .nbsw{flex:0 1 auto;min-width:0;align-self:flex-end}
#v-etf .etfcatbar{align-items:flex-end}
#v-etf .etfcatbar .sp{flex:1}
#v-etf .etfper{display:flex;align-items:center;gap:8px;flex:none}
#v-etf .etfper.off{visibility:hidden}
#v-etf .etfper .lb{font-size:12.5px;color:var(--ink-3)}
#v-etf .cust.inv{visibility:hidden} #v-etf .cust{display:inline-flex;align-items:center;gap:6px;color:var(--ink-3);white-space:nowrap}
#v-etf .cust input{width:136px;text-align:center}
/* ---- 卡片清單 */
#v-etf .etfgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:10px;margin-top:10px}
#v-etf .etfc{position:relative;display:flex;flex-direction:column;gap:4px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;
  background:var(--panel-2);cursor:pointer;text-align:left;color:var(--ink);font:inherit;min-width:0}
#v-etf .etfc:hover,#v-etf .etfc:focus-visible{border-color:var(--cyan);outline:none}
#v-etf .etfc .h{display:flex;align-items:baseline;gap:6px;min-width:0}
#v-etf .etfc .nm{font-weight:700;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-etf .etfc .cd{font:12px var(--mono);color:var(--ink-3)}
#v-etf .etfc .px{display:flex;align-items:center;gap:8px}
#v-etf .etfc .px b{font:700 17px var(--mono)}
#v-etf .etfc .px .sp{flex:1}
#v-etf .etfc dl{display:grid;grid-template-columns:auto 1fr;gap:1px 8px;margin:2px 0 0;font-size:12px}
#v-etf .etfc dt{color:var(--ink-3)} #v-etf .etfc dd{margin:0;text-align:right;font-family:var(--mono);color:var(--ink-2)}
#v-etf .etag{display:inline-block;font-size:11.5px;padding:1px 7px;border-radius:999px;border:1px solid currentColor;white-space:nowrap;line-height:17px}
#v-etf .etag.amber{color:var(--amber)} #v-etf .etag.cyan{color:var(--cyan)} #v-etf .etag.violet{color:var(--violet)}
#v-etf .etag.lime{color:var(--lime)} #v-etf .etag.up{color:var(--rise)} #v-etf .etag.ink3{color:var(--ink-3)}
#v-etf .up{color:var(--rise)} #v-etf .down{color:var(--fall)} #v-etf .flat{color:var(--ink-2)}
#v-etf .etfmore{margin-top:10px;text-align:center}
/* ---- 三張前 5 名：同高並排 */
#v-etf .etftri{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--sp-3);margin-bottom:var(--sp-3);align-items:stretch}
#v-etf .etftri>.card{margin:0;display:flex;flex-direction:column;min-width:0}
#v-etf .etftri[hidden]{display:none}
#v-etf .rklist{display:flex;flex-direction:column;gap:4px;flex:1}
#v-etf .rkhd,#v-etf .rkrow{display:grid;grid-template-columns:20px minmax(0,1fr) 84px 92px;gap:8px;align-items:center;white-space:nowrap}
#v-etf .rkhd{font-size:11.5px;color:var(--ink-3);padding:0 8px}
#v-etf .rkhd span:nth-child(n+3){text-align:right}
#v-etf .rkrow{height:36px;padding:0 8px;border:1px solid var(--line);border-radius:8px;background:var(--panel-2);color:var(--ink);font:inherit;
  text-align:left;cursor:pointer;min-width:0}
#v-etf .rkrow:hover,#v-etf .rkrow:focus-visible{border-color:var(--cyan);outline:none}
#v-etf .rkrow.ghost{visibility:hidden}
#v-etf .rkrow .rk{font:700 15px var(--mono);color:var(--amber)}
#v-etf .rkrow .nm{overflow:hidden;text-overflow:ellipsis;min-width:0;font-weight:600}
#v-etf .rkrow .nm .cd{font:12px var(--mono);color:var(--ink-3);font-weight:400;margin-left:4px}
#v-etf .rkrow .v{font:700 13.5px var(--mono);text-align:right;overflow:hidden;text-overflow:ellipsis}
#v-etf .rkrow .v2{font:12px var(--mono);color:var(--ink-2);text-align:right;overflow:hidden;text-overflow:ellipsis}
#v-etf .rkprep{flex:1;display:flex;align-items:center;min-height:${5 * 40 + 18}px}
/* ---- 配息行事曆：左月曆、右清單，兩邊固定高 */
#v-etf .calwrap{display:grid;grid-template-columns:minmax(0,1fr) 520px;gap:14px;margin-top:6px}
#v-etf .calhd{display:flex;align-items:center;gap:8px;margin-bottom:6px;white-space:nowrap;height:32px}
#v-etf .calhd b{font-size:16px;width:118px;text-align:center}
#v-etf .calhd .note1{flex:1;text-align:right;font-size:12.5px;color:var(--ink-3)}
#v-etf .calg{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));grid-template-rows:20px repeat(${CAL_ROWS},76px);gap:4px}
#v-etf .calg .wd{font-size:12px;color:var(--ink-3);text-align:center;line-height:20px}
#v-etf .cald{border:1px solid var(--line);border-radius:8px;padding:3px 6px;background:var(--panel-2);font-size:12px;color:var(--ink-3);
  cursor:default;text-align:left;font-family:inherit;display:flex;flex-direction:column;gap:1px;min-width:0;overflow:hidden;padding:3px 5px}
#v-etf .cald.has{cursor:pointer;color:var(--ink)} #v-etf .cald.has:hover{border-color:var(--cyan)}
#v-etf .cald.out{opacity:.35;background:transparent}
#v-etf .cald.today{border-color:var(--cyan);background:color-mix(in srgb,var(--cyan) 12%,var(--panel-2));box-shadow:0 0 0 1px var(--cyan) inset}
#v-etf .cald.sel{border-color:var(--amber);box-shadow:0 0 0 2px var(--amber) inset}
#v-etf .cald .dn{display:flex;align-items:center;gap:6px;height:16px;white-space:nowrap}
#v-etf .cald .dn b{font:600 12px var(--mono)}
#v-etf .cald .dn i{font-style:normal;font-size:11px;padding:0 5px;border-radius:999px;background:var(--cyan);color:var(--ontop);line-height:15px}
#v-etf .cald .ce{display:flex;gap:4px;white-space:nowrap;line-height:16px;min-width:0}
#v-etf .cald .ce .cc{font:600 11.5px var(--mono);color:var(--ink);overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-etf .cald .ce .ca{font:11.5px var(--mono);color:var(--amber);margin-left:auto;flex:none}
#v-etf .cald .cm{font-size:11px;color:var(--cyan);line-height:15px;white-space:nowrap}
#v-etf .callist{border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:var(--panel-2);
  height:${32 + 6 + 20 + CAL_ROWS * 76 + CAL_ROWS * 4}px;overflow:auto;box-sizing:border-box}
#v-etf .callist .lt{display:block;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-etf table.et{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}
#v-etf table.et th{color:var(--ink-3);font-weight:600;text-align:right;padding:5px 6px;border-bottom:1px solid var(--line);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-etf table.et td{text-align:right;padding:5px 6px;border-bottom:1px solid var(--line);font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-etf table.et th:first-child,#v-etf table.et td:first-child{text-align:left;font-family:inherit}
#v-etf table.et tr[data-code]{cursor:pointer} #v-etf table.et tr[data-code]:hover td{background:var(--panel-3)}
#v-etf .na{color:var(--ink-3);font-family:inherit;font-size:12px}
/* ---- 報酬比較（自選） */
#v-etf .retcharts{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:14px;margin-top:8px}
#v-etf .retcharts .chart{height:320px}
#v-etf .retcharts .chart>.etfprep{height:100%;box-sizing:border-box;display:flex;align-items:center;justify-content:center;text-align:center}
#v-etf .rettw{margin-top:10px;overflow-x:auto}
#v-etf .rettw table.et{min-width:820px}
#v-etf .cmpmsg{font-size:12.5px;color:var(--amber);width:150px;overflow:hidden;text-overflow:ellipsis}
#v-etf #etfCmpDD .ddbtn{max-width:230px}
#v-etf select.etsel{height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font:inherit;font-size:13px}
/* ---- 2026-10-05 第三版（Andy：「圖案需要給他顏色」）：標題圖示由 icons.js 依 data-icon／data-tone 上色；
   卡片左緣一條分類色、殖利率與配息頻率有語意色；所有標籤一行不換行（版面不因字長晃動） */
#v-etf .etfdisc .dico{color:var(--amber);font-weight:700}
#v-etf .etfc{border-left:3px solid var(--tc,var(--line))}
#v-etf .etfc.t-amber{--tc:var(--amber)} #v-etf .etfc.t-cyan{--tc:var(--cyan)} #v-etf .etfc.t-violet{--tc:var(--violet)}
#v-etf .etfc.t-lime{--tc:var(--lime)} #v-etf .etfc.t-up{--tc:var(--rise)} #v-etf .etfc.t-ink3{--tc:var(--ink-3)}
#v-etf .etfc .etag{background:color-mix(in srgb,currentColor 12%,transparent)}
#v-etf .etfc dl{grid-template-columns:minmax(0,max-content) minmax(0,1fr)}
#v-etf .etfc dt,#v-etf .etfc dd{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:18px}
#v-etf .etfc dd.yv{color:var(--amber);font-weight:700} #v-etf .etfc dd .na{font-weight:400}
#v-etf .etfc .fq{display:inline-block;padding:0 6px;border-radius:999px;background:color-mix(in srgb,var(--violet) 16%,transparent);color:var(--violet);font-family:inherit;line-height:16px}
#v-etf .rkrow .rk{color:var(--tc,var(--amber))}
#v-etf #etfPopCard{--tc:var(--amber)} #v-etf #etfRetTopCard{--tc:var(--rise)} #v-etf #etfYldCard{--tc:var(--violet)}
#v-etf .cald.has{background:color-mix(in srgb,var(--amber) 8%,var(--panel-2))}
/* Andy 10-05：「所有欄位文字置中」（DECISIONS #321 同一條：欄位內文字一律置中、無例外） */
#v-etf table.et th,#v-etf table.et td,#v-etf table.et th:first-child,#v-etf table.et td:first-child{text-align:center}
#v-etf .rkhd span,#v-etf .rkhd span:nth-child(n+3),#v-etf .rkrow .v,#v-etf .rkrow .v2,#v-etf .rkrow .rk{text-align:center}
#v-etf .etfc dt,#v-etf .etfc dd{text-align:center}
/* 2026-10-06（Andy：「分頁為何分開了，Follow 產業 MAP」）：資料夾式——頁籤底線＝內容框上框線，選中頁籤疊在線上；分類切換影響的內容全包在框內 */
#v-etf .etfbody{border:1px solid var(--line);border-radius:0 var(--r-lg,14px) var(--r-lg,14px) var(--r-lg,14px);background:var(--panel);padding:var(--sp-3);position:relative;z-index:1}
#v-etf .etfbody>#etfRetCard,#v-etf .etfbody>#etfListCard{border:0;border-top:1px solid var(--line);border-radius:0;background:transparent;box-shadow:none;margin:var(--sp-3) 0 0;padding:var(--sp-3) 2px 0}
#v-etf .etfbody>.card:last-child,#v-etf .etfbody>.etftri:last-child{margin-bottom:0}
#v-etf .etfdisc{margin:10px 2px 0;font-size:12px;line-height:16px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* 2026-10-06：月曆週末反灰／休市（calgrid.js）、面板細節、報酬比較表名稱欄靠左 */
#v-etf .cald.cg-we .ce .cc{color:var(--ink-3)}
#v-etf .callist .ph{display:flex;align-items:center;gap:8px;white-space:nowrap;min-width:0;margin-bottom:4px}
#v-etf .callist .ph b{font-size:15.5px;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-etf .callist .ph .sp{flex:1}
#v-etf .callist .kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:6px 0}
#v-etf .callist .kpis div{border:1px solid var(--line);border-radius:8px;text-align:center;padding:4px;background:var(--panel-3);min-width:0}
#v-etf .callist .kpis small{display:block;font-size:12px;color:var(--ink-3);line-height:16px}
#v-etf .callist .kpis b{display:block;font:700 15px var(--mono);line-height:22px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-etf .callist .mini{display:grid;grid-template-columns:96px minmax(0,1fr);gap:10px;align-items:center;margin:8px 0 2px}
#v-etf .callist .mk{text-align:center;min-width:0} #v-etf .callist .mk b{display:block;font:700 18px var(--mono);line-height:24px}
#v-etf .callist .mk small{display:block;font-size:12px;color:var(--ink-3);line-height:16px;white-space:nowrap}
#v-etf .callist .mc svg{width:100%;height:84px;display:block}
#v-etf .callist .ml{display:flex;justify-content:space-between;gap:6px;font-size:12px;color:var(--ink-3);white-space:nowrap;margin-top:2px}
#v-etf .callist .ml i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
#v-etf .callist .ph.stk{position:sticky;top:-8px;z-index:3;background:var(--panel-2);margin:-8px -10px 6px;padding:8px 10px;border-bottom:1px solid var(--line)}
#v-etf .callist .plink{font-size:15.5px;font-weight:700;color:var(--ink);text-decoration:none;overflow:hidden;text-overflow:ellipsis;min-width:0;cursor:pointer}
#v-etf .callist .plink:hover,#v-etf .callist .plink:focus-visible{text-decoration:underline;color:var(--cyan);outline:none}
#v-etf .callist .ph .btn{flex:none}
#v-etf .callist tr[data-code].on td{background:var(--panel-3)}
#v-etf .nmw{display:flex;align-items:center;gap:6px;min-width:0}
#v-etf .nmw i{width:9px;height:9px;border-radius:2px;flex:none}
#v-etf .nmw .nmt{overflow:hidden;text-overflow:ellipsis;min-width:0;font-family:inherit}
#v-etf .nmw .note{flex:none}
#v-etf table.et td.nmc,#v-etf table.et th.nmc{text-align:left}
#v-etf table.et.fullw{width:100%}
@media (max-width:1100px){#v-etf .etftri{grid-template-columns:1fr}#v-etf .calwrap,#v-etf .retcharts{grid-template-columns:1fr}
  #v-etf .callist{height:320px}#v-etf .etfcatbar{flex-wrap:wrap}#v-etf .etfcatbar .seg{overflow-x:auto;max-width:100%}
  #v-etf .row.spread{flex-wrap:wrap}}
`;
    document.head.appendChild(s);
  }

  /* ------------------------------------------------------------------ 資料 */
  async function loadData() {
    const a = A();
    let d = null;
    try { if (a.sparkLoad) await a.sparkLoad(); } catch (e) { /* 迷你走勢讀不到就不畫，不擋整頁 */ }
    try { d = await a.load('etf', { fallback: null }); } catch (e) { d = null; }
    if (d && Array.isArray(d.items) && d.items.length) { S.data = d; S.fallback = false; return; }
    // 退回：stocks.json 裡的 ETF（代號 00 開頭）＋名稱分類
    const st = (await a.load('stocks', { fallback: [] })) || [];
    const items = st.filter((r) => r && /^00/.test(String(r.code))).map((r) => ({
      code: String(r.code), name: r.name || '', cat: classify(r.code, r.name), close: r.close, chg_pct: r.chg_pct,
      tv20: null, tv: r.turnover, yield_ttm: null, freq: null, size: null, holders: null, d_holders: null, stats: {},
    }));
    S.data = { items, top: {}, popular: {}, calendar: [], series: {}, periods: {}, asof: null };
    S.fallback = true;
  }
  /* 全部 ETF 的週線走勢（etf_series.json）：只有自選比較要畫線時才需要，所以不擋開頁，背景讀完再重畫比較圖。
     讀不到（正式站還沒產出這一檔）就退回 etf.json 內附的那幾檔走勢，其他檔的線不畫、表照列。*/
  let seriesP = null;
  function loadSeries() {
    if (seriesP) return seriesP;
    seriesP = A().load('etf_series', { fallback: null }).catch(() => null).then((d) => {
      S.series = d && d.D && d.s ? d : { D: [], s: {} };
      return S.series;
    });
    return seriesP;
  }
  function seriesOf(code) {
    const g = S.series;
    if (g && g.s && g.s[code]) { const x = g.s[code]; return { d: g.D.slice(x.i), p: x.p, t: x.t }; }
    return ((S.data && S.data.series) || {})[code] || null;
  }
  const items = () => (S.data && S.data.items) || [];
  /* 2026-10-06（Andy：「無配息就純算報酬率」）：已確認不配息的（槓桿反向／期貨／累積型，或查過配息資料確定 0 筆）含息＝不含息 */
  const NODIV_RE = /期貨|累積|正2|反1|正二|反一/;
  const noDiv = (it) => !!it && (it.cat === '槓桿反向' || NODIV_RE.test(it.name || '') || (!!it.div_done && !it.freq_n && !(it.div_ttm > 0)));
  /* 上市未滿期間的 ETF：改用「上市以來」年化（從序列第一天算起）；不配息的含息年化＝價格年化 */
  function effSt(it, st) {
    let o = st;
    if (!st.ok && /上市未滿/.test(st.why || '')) {
      const s = seriesOf(it.code);
      if (s && s.d && s.d.length > 12 && s.p) {
        const n = s.d.length, yrs = (Date.parse(s.d[n - 1]) - Date.parse(s.d[0])) / (365.25 * 864e5);
        const ann = (a) => (a && a[0] && a[n - 1] ? Math.pow(a[n - 1] / a[0], 1 / yrs) - 1 : null);
        if (yrs >= 0.25) o = { ok: true, since: true, from: s.d[0], years: +yrs.toFixed(1), price_ann: ann(s.p), tr_ann: s.t ? ann(s.t) : null, div_ann: null };
      }
    }
    if (o.ok && noDiv(it) && o.tr_ann == null) o = { ...o, tr_ann: o.price_ann, nodiv: true };
    return o;
  }
  /* 柔和專業色盤（Andy：「長條圖配色好醜」）：不含息＝柔和鋼藍、含息＝柔和杏橘（藍／橘對色盲友善）；線圖系列同一套 */
  const SOFT = () => {
    const light = document.documentElement.getAttribute('data-theme') === 'light';
    return light
      ? { a: '#5B86B8', b: '#D8964A', pal: ['#5B86B8', '#4FA394', '#D8964A', '#8E78C4', '#C9788F', '#86A650', '#4E9DB8', '#B79A4C'] }
      : { a: '#7FA7D9', b: '#EDB36F', pal: ['#7FA7D9', '#6CC4B0', '#EDB36F', '#AB95DB', '#DB91A8', '#A3C477', '#74C3DE', '#D2B76F'] };
  };
  const byCode = () => { const m = new Map(); items().forEach((it) => m.set(it.code, it)); return m; };
  const inCat = () => items().filter((it) => it.cat === S.cat);
  const sizeKey = (it) => (it.size != null ? it.size : -1) * 1e3 + ((it.tv20 || 0) / 1e12);

  /* 出處 ⓘ：跟全站 App.srcInfo 同一個寫法（claude/copy-trim2 分支，還沒上 main）—— 有就直接用它；沒有就產出同樣的標記
     （class srcinfo＋title；樣式等 .srcinfo 進 index.html 才有，這之前借既有的 .muted 灰字）。App.srcInfo 上 main 後退回寫法可刪。 */
  const srcI = (src) => (A().srcInfo ? A().srcInfo(src, '')
    : (src ? `<span class="srcinfo muted" tabindex="0" role="note" aria-label="出處" title="${esc('出處：' + src)}">ⓘ</span>` : ''));

  /* ------------------------------------------------------------------ 骨架 */
  function skeleton(root) {
    const how = (k, q, li) => `<div class="howtxt" id="how-${k}" hidden>${A().howHTML(q, li)}</div>`;
    const hbtn = (k, t) => `<button class="howbtn pop" data-how="${k}" data-ttl="${t}" type="button" aria-label="${t}">?</button>`;
    root.innerHTML = `
<div class="card" id="etfCalCard">
  <div class="row spread"><h3 data-icon="calendar" data-tone="yield">配息行事曆 <small id="etfCalSub"></small> ${hbtn('etfcal', '配息行事曆怎麼看')}</h3></div>
  ${how('etfcal', '', [
    '格子裡直接寫當天除息的 ETF 代號與每單位配息（元）；超過 2 檔只列前 2 檔，其餘寫「+N 檔」。藍框＝今天。',
    '點有除息的格子，右邊列出那天每一檔的配息金額、當次殖利率、發放日與<b>填息天數</b>。',
    '<b>當次殖利率</b>＝該次配息 ÷ 除息前一個交易日收盤；尚未除息的（未來日期）改用最新收盤估算，標「估」。',
    '<b>填息天數</b>＝從除息日當天算第 1 個交易日，收盤第一次回到「除息前一日收盤」是第幾個交易日（與個股除權息分頁同一口徑）。還沒回到的寫「尚未填息（已 N 天）」，還沒除息或行情不足的寫「—」。',
    '所以：想領某一次的息，要在除息日「前一個交易日」收盤前持有；發放日才是錢入帳的日子。填息天數短＝除息後股價很快補回，長或尚未填息＝領到的息被價差吃掉。'])}
  <div id="etfCal"></div>
</div>

<div class="etfcatbar" id="etfCatBar">
  <div class="nbsw etfcats" id="etfCatSeg" role="tablist" aria-label="ETF 分類"></div><span class="sp"></span>
  <div class="etfper" id="etfPerBox"><span class="lb">報酬率期間</span>
    <div class="seg" id="etfPerSeg"><button data-v="3y">3 年</button><button data-v="5y">5 年</button><button data-v="10y">10 年</button><button data-v="custom">自訂</button></div>
    <span class="cust inv" id="etfCust"><input type="date" id="etfFrom" class="etsel" aria-label="起始日"> ～ <input type="date" id="etfTo" class="etsel" aria-label="結束日（預設今天）"></span></div>
</div>
<div class="etfbody" id="etfBody">

<div class="etftri" id="etfTri" hidden>
  <div class="card" id="etfPopCard">
    <div class="row spread"><h3 data-icon="flame" data-tone="heat">最近最受歡迎前 5 ${hbtn('etfpop', '最受歡迎怎麼算')}</h3>
      <div class="seg" id="etfPopSeg"><button data-v="holders">受益人週增</button><button data-v="turnover">成交值</button></div></div>
    ${how('etfpop', '', [
      '<b>受益人週增</b>：集保結算所每週公布的受益人數（合計列），最新一週減前一週，增加最多的前 5 檔。代表「新進場的人」。',
      '<b>成交值</b>：最近 20 個交易日成交金額的平均。代表「交易熱度」。',
      '只在目前這個分類裡排；所以：兩個口徑都在前面的，是人潮與交易都熱的。'])}
    <p class="etfq" id="etfPopSub"></p>
    <div class="rklist" id="etfPop"></div>
  </div>
  <div class="card" id="etfRetTopCard">
    <div class="row spread"><h3 data-icon="arrow-up" data-tone="up">報酬率前 5 <small id="etfRetTopSub"></small> ${hbtn('etfrettop', '報酬率前 5 怎麼排')}</h3></div>
    ${how('etfrettop', '', [
      '依<b>含息總報酬年化</b>由高到低排（配息在除息日以當天收盤再投入）。期間跟著上方「報酬率期間」3／5／10 年／自訂。',
      '期間內上市未滿的，改用<b>上市以來</b>年化計算並標「上市以來 N 年」，不和滿期的直接比較。',
      '所以：先看這裡誰長期最好，再到下面「報酬比較」把想比的幾檔勾進去看走勢。'])}
    <p class="etfq" id="etfRetTopQ"></p>
    <div class="rklist" id="etfRetTop"></div>
  </div>
  <div class="card" id="etfYldCard">
    <div class="row spread"><h3 data-icon="coins" data-tone="yield">殖利率前 5 <small>近 12 個月</small> ${hbtn('etfyld', '殖利率前 5 怎麼看')}</h3></div>
    ${how('etfyld', '', [
      '<b>殖利率</b>＝近 12 個月現金配息合計 ÷ 最新收盤。只看現金配息，不受上方期間影響。',
      '<b>平均填息</b>＝最近 4 次已除息裡「已經填息」那幾次的填息天數平均（交易日）；還沒填息的不算進平均，另外寫「N 次未填」。完全沒有填過的寫「尚未填息」。',
      '填息天數口徑：除息日當天算第 1 天，收盤第一次回到除息前一日收盤是第幾個交易日（與個股除權息分頁相同）。',
      '所以：殖利率高但填息慢（或尚未填息），代表配的息常被除息後的價差吃掉，實拿的報酬沒有殖利率看起來那麼高。'])}
    <div class="rklist" id="etfYld"></div>
  </div>
</div>

<div class="card" id="etfRetCard">
  <div class="row spread"><h3 data-icon="line" data-tone="tech">報酬比較 <small id="etfRetSub"></small> ${hbtn('etfret', '報酬比較的口徑')}</h3>
    <div class="etfrow">
      <span class="cmpmsg" id="etfCmpMsg" aria-live="polite"></span>
      <div class="rotdd wide msdd" id="etfCmpDD" data-dd="etfcmp">
        <button type="button" class="ddbtn" aria-haspopup="true" aria-expanded="false" title="挑要比較的 ETF（可搜尋、可複選，限這個分類、最多 ${CMP_MAX} 檔）">加入比較：<b>已選 0 檔</b><i aria-hidden="true">▾</i></button>
        <div class="ddpanel" aria-label="加入比較（可複選）" hidden>
          <input type="search" class="sndd-q" placeholder="搜尋代號或名稱" aria-label="搜尋 ETF 代號或名稱" autocomplete="off">
          <div class="ddbar"><span class="muted sndd-n"></span>
            <button type="button" class="btn small dd-all">全選</button>
            <button type="button" class="btn small dd-none">全不選</button></div>
          <div class="ddlist"></div>
        </div>
      </div>
      <div class="seg" id="etfBasisSeg"><button data-v="tr">含息</button><button data-v="price">不含息</button></div>
    </div></div>
  ${how('etfret', '', [
    '用右上「加入比較」挑這個分類裡的 ETF（可搜尋、最多 8 檔）；沒挑過時預設是「報酬率前 5」。每個分類各自記住你挑的。',
    '<b>價格年化（不含息）</b>＝(期末收盤 ÷ 期初收盤)^(1/年數) − 1；分割（例：0050 2025-06 一拆四）已還原，配息不算進去。',
    '<b>含息年化</b>＝配息在除息日以當天收盤再投入（還原權值）後的年化報酬。<b>殖利率</b>＝近 12 個月現金配息 ÷ 最新收盤。',
    '<b>配息年化</b>＝(1 ＋ 期間累計配息 ÷ 期初收盤)^(1/年數) − 1：只看配息本身每年貢獻多少。',
    '期間：跟著上方「報酬率期間」。<b>上市未滿</b>的改用上市以來計算並標「自 YYYY-MM 上市」；不配息的 ETF 含息＝不含息，標「不配息」。',
    '所以：左圖看一路走勢（同起點 = 0%），右圖直接比年化數字；含息與不含息差距越大，代表報酬越依賴配息。'])}
  <div id="etfRetBody"></div>
</div>

<div class="card" id="etfListCard">
  <div class="row spread"><h3 data-icon="table" data-tone="chip">ETF 一覽 <small id="etfCount"></small> ${hbtn('etflist', 'ETF 分類與欄位')}</h3>
    <div class="etfrow"><label class="note" for="etfSort">排序</label>
      <select id="etfSort" class="etsel"><option value="tv">成交值</option><option value="size">規模</option><option value="yield">殖利率</option><option value="chg">今日漲跌</option></select></div></div>
  ${how('etflist', '', [
    '<b>分類</b>（依序判斷，先符合先歸類）：槓桿反向（代號尾 L/R 或名稱含 正2／反1）→ 債券型（尾 B 或名稱含「債」）→ 其他（期貨／商品／貨幣，尾 U 或「期」開頭）→ 主動式（尾 A）→ 市值型（名稱含 台灣50、台50、中型100、加權、MSCI台灣、摩台）→ 配息型（名稱含 高股息／高息／股息／收益／優息…，或近 400 天除息 ≥ 4 次）→ 其餘股票型為主題型。',
    '<b>殖利率</b>＝近 12 個月現金配息合計 ÷ 最新收盤。<b>配息頻率</b>＝近 400 天除息次數（≥10 月配、≥3 季配、2 半年配、1 年配）。',
    '<b>規模</b>＝集保受益權單位數 × 收盤（估算值，不是投信公告的基金淨資產）。<b>成交值</b>＝近 20 日平均。',
    '所以：先用上方分類切出同一型，再用「殖利率」或「規模」排序比較；點卡片進個股頁看 K 線與除權息。'])}
  <span id="etfFbNote"></span>
  <div class="etfgrid" id="etfGrid"></div>
  <div class="etfmore"><button type="button" class="btn small" id="etfMore" hidden>顯示更多</button></div>
</div>
<p class="etfdisc" id="etfDisc" role="note">ⓘ 公開資料整理與統計，非投資建議；過去績效不代表未來報酬。</p>
</div>`;
  }

  /* ------------------------------------------------------------------ 分類列（全頁共用） */
  function drawCats() {
    const all = items();
    const cnt = {}; all.forEach((it) => { cnt[it.cat] = (cnt[it.cat] || 0) + 1; });
    const seg = $('#etfCatSeg');
    seg.innerHTML = CATS.filter((c) => cnt[c])
      .map((c) => `<button data-v="${c}" role="tab">${c}<em>${cnt[c]}</em></button>`).join('');
    $$('button', seg).forEach((b) => { b.classList.toggle('on', b.dataset.v === S.cat); b.setAttribute('aria-selected', b.dataset.v === S.cat);
      b.onclick = () => { if (S.cat === b.dataset.v) return; S.cat = b.dataset.v; S.shown = PAGE; drawAll(); }; });
    // 期間只影響報酬率：「全部」沒有報酬卡，期間整組隱形但保留位置（不讓分類鈕跟著左右跳）
    $('#etfPerBox').classList.remove('off');
    $$('#etfPerSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.per);
      b.onclick = () => { S.per = b.dataset.v; LS.set('tw.etf.per', S.per); drawPer(); drawRetTop(); drawRet(); }; });
    drawPer();
  }
  function drawPer() {
    $$('#etfPerSeg button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.per));
    const f = $('#etfFrom'), t = $('#etfTo');
    if (!S.cfrom) S.cfrom = LS.get('tw.etf.cfrom', '') || new Date(Date.now() + 8 * 3600e3 - 3 * 365.25 * 864e5).toISOString().slice(0, 10);
    if (!S.cto) S.cto = new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);   // 結束日預設今天，可改
    f.value = S.cfrom; t.value = S.cto; t.max = S.cto > S.cfrom ? '' : '';
    $('#etfCust').classList.toggle('inv', S.per !== 'custom');
    const ch = () => { if (f.value) { S.cfrom = f.value; LS.set('tw.etf.cfrom', S.cfrom); } if (t.value) S.cto = t.value; drawRetTop(); drawRet(); };
    f.onchange = ch; t.onchange = ch;
  }
  function perKey() { return S.per === 'custom' ? 'C' + S.cfrom + '~' + S.cto : S.per; }
  /* 自訂期間：用週序列自己算（起始日早於上市就從上市第一天算起＝上市以來） */
  function rangeStats(it) {
    const s = seriesOf(it.code);
    if (!s || !s.d || !s.p) return { ok: false, why: S.series ? '無資料' : '走勢載入中' };
    const from = S.cfrom || '', to = S.cto || '9999';
    let i0 = s.d.findIndex((d) => d >= from); if (i0 < 0) return { ok: false, why: '起始日晚於最後一筆資料' };
    let i1 = s.d.length - 1; while (i1 > 0 && s.d[i1] > to) i1--;
    if (i1 - i0 < 2) return { ok: false, why: '這段日期內資料不足' };
    const yrs = (Date.parse(s.d[i1]) - Date.parse(s.d[i0])) / (365.25 * 864e5);
    const ann = (a) => (a && a[i0] && a[i1] ? Math.pow(a[i1] / a[i0], 1 / yrs) - 1 : null);
    const o = { ok: true, since: s.d[0] > from, from: s.d[i0], years: +yrs.toFixed(1), price_ann: ann(s.p), tr_ann: s.t ? ann(s.t) : null, div_ann: null };
    return noDiv(it) && o.tr_ann == null ? { ...o, tr_ann: o.price_ann, nodiv: true } : o;
  }
  const statOf = (it) => (S.per === 'custom' ? rangeStats(it) : effSt(it, ((it.stats || {})[perKey()]) || { ok: false, why: '無資料' }));
  function perLabel(short) {
    const st = S.per === 'custom' ? null : ((S.data && S.data.periods) || {})[perKey()];
    const nm = S.per === 'custom' ? '自訂期間' : { '3y': '近 3 年', '5y': '近 5 年', '10y': '近 10 年' }[S.per];
    return nm;
  }

  /* ------------------------------------------------------------------ 1. 卡片清單 */
  function sortVal(it) {
    if (S.sort === 'size') return it.size == null ? -Infinity : it.size;
    if (S.sort === 'yield') return it.yield_ttm == null ? -Infinity : it.yield_ttm;
    if (S.sort === 'chg') return it.chg_pct == null ? -Infinity : it.chg_pct;
    return (it.tv20 != null ? it.tv20 : it.tv) || 0;
  }
  function spark(code) {
    const a = A();
    return a.sparkSVG ? `<span class="spkw" data-spk="${esc(code)}" data-w="80" data-h="26">${a.sparkSVG(code, { w: 80, h: 26 })}</span>` : '';
  }
  function cardHTML(it) {
    const y = it.yield_ttm != null ? pctU(it.yield_ttm) : '—';
    const fq = it.freq || '—';
    // 殖利率／配息頻率還沒有資料時寫「—」（不拿 0 冒充）；確定不配息的寫「不配息」
    const pend = '<span class="na">—</span>';
    return `<button type="button" class="etfc t-${CAT_TONE[it.cat] || 'ink3'}" data-code="${esc(it.code)}" title="進 ${esc(it.name)} 個股頁">
  <div class="h"><span class="nm">${esc(it.name)}</span><span class="cd">${esc(it.code)}</span><span class="sp" style="flex:1"></span>
    <span class="etag ${CAT_TONE[it.cat] || 'ink3'}">${esc(it.cat)}</span></div>
  <div class="px"><b class="${cls(it.chg_pct)}" data-live="close" data-code="${esc(it.code)}">${it.close != null ? A().fmt.n(it.close, 2) : '—'}</b>
    <span class="${cls(it.chg_pct)}" data-live="chg" data-code="${esc(it.code)}">${it.chg_pct != null ? A().fmt.pct(it.chg_pct, 2) : '—'}</span>
    <span class="sp"></span>${spark(it.code)}</div>
  <dl><dt>成交值${it.tv20 != null ? '（20日均）' : ''}</dt><dd>${yi(it.tv20 != null ? it.tv20 : it.tv)}</dd>
      <dt>殖利率</dt><dd class="yv">${it.yield_ttm != null ? y : noDiv(it) ? '<span class="na">不配息</span>' : pend}</dd><dt>配息頻率</dt><dd>${it.freq ? `<span class="fq">${esc(fq)}</span>` : noDiv(it) ? '<span class="na">不配息</span>' : pend}</dd><dt>規模（估）</dt><dd>${yi(it.size)}</dd></dl>
</button>`;
  }
  function drawList() {
    const list = items().filter((it) => it.cat === S.cat).sort((a, b) => sortVal(b) - sortVal(a));
    $('#etfCount').textContent = `${S.cat} ${list.length} 檔`;
    const g = $('#etfGrid');
    g.innerHTML = list.slice(0, S.shown).map(cardHTML).join('') || '<div class="etfprep">無資料</div>';
    $$('.etfc', g).forEach((c) => { c.onclick = () => A().goStock(c.dataset.code); });
    const more = $('#etfMore'); more.hidden = list.length <= S.shown;
    more.textContent = `顯示更多（還有 ${Math.max(0, list.length - S.shown)} 檔）`;
    more.onclick = () => { S.shown += PAGE; drawList(); };
    $('#etfFbNote').innerHTML = '';
    g.dataset.n = String(Math.min(list.length, S.shown)); g.dataset.cat = S.cat;
  }

  /* ------------------------------------------------------------------ 2. 分類內前 5 名（三張同高） */
  // 一列：名次｜名稱 代號｜主數字｜副數字。不足 5 列補隱形列，三張卡永遠一樣高。
  function rkRows(box, rows) {
    const hd = rows.head ? `<div class="rkhd"><span></span><span>ETF</span><span>${rows.head[0]}</span><span>${rows.head[1]}</span></div>` : '';
    const body = rows.list.map((r, i) => `<button type="button" class="rkrow" data-code="${esc(r.it.code)}" title="${esc(r.title || '進 ' + r.it.name + ' 個股頁')}">
      <span class="rk">${i + 1}</span><span class="nm">${esc(r.it.name)}<span class="cd">${esc(r.it.code)}${r.tag ? '・' + esc(r.tag) : ''}</span></span>
      <span class="v ${r.vc || ''}">${r.v}</span><span class="v2 ${r.v2c || ''}">${r.v2}</span></button>`).join('');
    const ghost = '<div class="rkrow ghost" aria-hidden="true"></div>'.repeat(Math.max(0, 5 - rows.list.length));
    box.innerHTML = hd + body + ghost;
    box.dataset.codes = rows.list.map((r) => r.it.code).join(',');
    $$('button.rkrow', box).forEach((b) => { b.onclick = () => A().goStock(b.dataset.code); });
  }
  function rkPrep(box, msg) {
    box.innerHTML = `<div class="etfprep rkprep">${msg}</div>`; box.dataset.codes = '';
  }
  function drawPop() {
    const box = $('#etfPop');
    $$('#etfPopSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.pop);
      b.onclick = () => { S.pop = b.dataset.v; LS.set('tw.etf.pop', S.pop); drawPop(); }; });
    const P = (S.data && S.data.popular) || {}, wk = P.holders_week || [];
    $('#etfPopSub').innerHTML = S.pop === 'holders' ? '口徑：集保受益人數<b>週增減</b>'
      : '口徑：<b>近 20 個交易日</b>平均成交值';
    if (S.fallback) { rkPrep(box, '尚無資料'); return; }
    const key = S.pop === 'holders' ? 'd_holders' : 'tv20';
    const L = inCat().filter((it) => it[key] != null).sort((a, b) => b[key] - a[key]).slice(0, 5);
    if (!L.length) { rkPrep(box, '無資料'); return; }
    rkRows(box, { head: S.pop === 'holders' ? ['受益人週增', '今日漲跌'] : ['日均成交值', '今日漲跌'],
      list: L.map((it) => ({ it,
        v: S.pop === 'holders' ? `${it.d_holders > 0 ? '+' : ''}${A().fmt.i(it.d_holders)}` : yi(it.tv20),
        vc: S.pop === 'holders' ? cls(it.d_holders) : '',
        v2: it.chg_pct != null ? A().fmt.pct(it.chg_pct, 2) : '—', v2c: cls(it.chg_pct) })) });
  }
  /* 報酬率排行：分類內、這個期間有完整資料的，依含息年化排；整類都沒有配息資料才暫依價格年化（並寫明）。*/
  function retRank() {
    const pk = perKey();
    const L = inCat().map((it) => ({ it, st: statOf(it) })).filter((x) => x.st && x.st.ok);
    const anyTr = L.some((x) => x.st.tr_ann != null);
    const key = anyTr ? 'tr_ann' : 'price_ann';
    const R = L.filter((x) => x.st[key] != null).sort((a, b) => b.st[key] - a.st[key]);
    return { rows: R, key, nOk: L.length, nNoTr: anyTr ? L.length - R.length : 0 };
  }
  function drawRetTop() {
    const box = $('#etfRetTop'); if (!box || NO_RANK[S.cat]) return;
    $('#etfRetTopSub').textContent = perLabel(true);
    const q = $('#etfRetTopQ');
    if (S.fallback) { q.innerHTML = ''; rkPrep(box, '尚無資料'); return; }
    const R = retRank();
    q.innerHTML = R.key === 'tr_ann'
      ? '依<b>含息年化</b>排'
      : '依<b>價格年化</b>（不含息）排';
    if (!R.rows.length) {
      rkPrep(box, '無資料'); return;
    }
    rkRows(box, { head: R.key === 'tr_ann' ? ['含息年化', '不含息'] : ['價格年化', '期間'],
      list: R.rows.slice(0, 5).map(({ it, st }) => ({ it, tag: st.since ? `上市以來 ${st.years} 年` : '',
        v: pct(st[R.key], 2), vc: cls(st[R.key]),
        v2: R.key === 'tr_ann' ? pct(st.price_ann, 1) : `${st.years} 年`, v2c: R.key === 'tr_ann' ? cls(st.price_ann) : '' })) });
  }
  function drawYld() {
    const box = $('#etfYld'); if (!box || NO_RANK[S.cat]) return;
    if (S.fallback) { rkPrep(box, '尚無資料'); return; }
    const L = inCat().filter((it) => it.yield_ttm != null).sort((a, b) => b.yield_ttm - a.yield_ttm).slice(0, 5);
    if (!L.length) {
      rkPrep(box, '無資料'); return;
    }
    const fillCell = (it) => {
      if (it.fill_avg != null) return { v: `${it.fill_avg} 天`, t: `近 ${it.fill_n} 次除息：已填息的平均 ${it.fill_avg} 天${it.fill_open ? `，${it.fill_open} 次尚未填息` : ''}` };
      const w = it.fill_last && it.fill_last[1];
      if (w != null) return { v: '尚未填息', t: `最近一次除息尚未填息（已 ${w} 天）` };
      return { v: '—', t: '無填息資料' };
    };
    rkRows(box, { head: ['殖利率', '平均填息'],
      list: L.map((it) => { const f = fillCell(it); return { it, v: pctU(it.yield_ttm), v2: f.v, title: `${it.name}：殖利率 ${pctU(it.yield_ttm)}；${f.t}` }; }) });
  }

  /* ------------------------------------------------------------------ 3. 配息行事曆（7 欄真月曆） */
  function drawCal() {
    const box = $('#etfCal');
    const cal = (S.data && S.data.calendar) || [];
    const today = todayTW(), curM = today.slice(0, 7);
    if (!S.month) S.month = curM;
    const [y, mo] = S.month.split('-').map(Number);
    const first = new Date(Date.UTC(y, mo - 1, 1));
    const CG = window.CalGrid;
    S.rh = S.rh || 76; S.capE = Math.min(2, Math.max(1, Math.floor((S.rh - 8 - 16 + 2) / 16)));
    const by = {}; cal.forEach((e) => { (by[e.ex] = by[e.ex] || []).push(e); });
    const nIn = cal.filter((e) => e.ex.slice(0, 7) === S.month).length;
    const status = S.fallback || !cal.length ? '' : nIn ? `${y} 年 ${mo} 月共 ${nIn} 筆除息` : '本月無除息';
    $('#etfCalSub').textContent = '';
    let cells = WD.map((w) => `<div class="wd">${w}</div>`).join('');
    const start = new Date(first); start.setUTCDate(1 - first.getUTCDay());
    for (let i = 0; i < CAL_ROWS * 7; i++) {
      const dt = new Date(start); dt.setUTCDate(start.getUTCDate() + i);
      const k = dt.toISOString().slice(0, 10), d = dt.getUTCDate();
      if (k.slice(0, 7) !== S.month) { cells += `<div class="cald out" aria-hidden="true"><span class="dn"><b>${d}</b></span></div>`; continue; }
      const L = by[k] || [];
      const hol = CG.tag(k), nE = Math.max(1, S.capE - (hol ? 1 : 0));
      const isT = k === today;
      // 格內金額去掉尾巴的 0（0.700 → 0.7）：格子窄，代號才不會被省略號吃掉；完整金額在右側清單
      const ent = L.slice(0, nE).map((e) => `<span class="ce"><span class="cc">${esc(e.code)}</span><span class="ca">${String(+(+e.amt).toFixed(3))}</span></span>`).join('');
      const more = L.length > nE ? `<span class="cm">+${L.length - nE} 檔</span>` : '';
      cells += `<button type="button" class="cald${CG.cls(k)}${L.length ? ' has' : ''}${isT ? ' today' : ''}${S.day === k ? ' sel' : ''}" data-d="${k}" data-n="${L.length}"
        ${L.length ? '' : 'tabindex="-1"'} aria-label="${k}${isT ? '（今天）' : ''}${L.length ? ' 有 ' + L.length + ' 檔除息' : ''}"><span class="dn"><b>${d}</b>${isT ? '<i>今天</i>' : ''}</span>${hol}${ent}${more}</button>`;
    }
    const sel = S.day && by[S.day] ? by[S.day] : null;
    box.innerHTML = `<div class="calwrap"><div><div class="calhd"><button type="button" class="btn small" id="etfCalPrev" aria-label="上個月">‹ 上月</button>
      <b id="etfCalMonth">${y} 年 ${mo} 月</b><button type="button" class="btn small" id="etfCalNext" aria-label="下個月">下月 ›</button>
      <button type="button" class="btn small" id="etfCalToday"${S.month === curM ? ' disabled' : ''}>回本月</button>
      <span class="note1" id="etfCalStatus">${esc(status)}</span></div>
      <div class="calg" id="etfCalGrid">${cells}</div></div>
      <div class="callist" id="etfCalList">${S.code ? codeDetail(S.code) : sel ? calList(S.day, sel) : monthList(cal.filter((e) => e.ex.slice(0, 7) === S.month), y, mo)}</div></div>`;
    box.dataset.month = S.month; box.dataset.day = S.day || ''; box.dataset.code = S.code || '';
    if (window.innerWidth > 1100) {      // 一屏：格高自適應，右側清單與月曆同高
      const g = $('#etfCalGrid'), rh = CG.fit(g, CAL_ROWS, 64, 100, 4);
      g.style.gridTemplateRows = `20px repeat(${CAL_ROWS},${rh}px)`;
      $('#etfCalList').style.height = Math.round(g.getBoundingClientRect().bottom - $('.calhd', box).getBoundingClientRect().top) + 'px';
      box.dataset.rowh = String(rh);
      if (rh !== S.rh && !S._re) { S.rh = rh; S._re = 1; drawCal(); S._re = 0; return; }
    }
    const go = (m) => { S.month = m; S.day = null; S.code = null; drawCal(); };
    $('#etfCalPrev').onclick = () => go(new Date(Date.UTC(y, mo - 2, 1)).toISOString().slice(0, 7));
    $('#etfCalNext').onclick = () => go(new Date(Date.UTC(y, mo, 1)).toISOString().slice(0, 7));
    $('#etfCalToday').onclick = () => go(curM);
    $$('.cald.has', box).forEach((c) => { c.onclick = () => { S.code = null; S.day = S.day === c.dataset.d ? null : c.dataset.d; drawCal(); }; });
    $$('#etfCalList tr[data-code]', box).forEach((tr) => { tr.onclick = () => { S.code = tr.dataset.code; drawCal(); }; });
    const bk = $('#etfCodeBack', box); if (bk) bk.onclick = () => { S.code = null; drawCal(); };
    const db = $('#etfDayBack', box); if (db) db.onclick = () => { S.day = null; drawCal(); };
    $$('#etfCalList .plink', box).forEach((a) => { a.onclick = (ev) => { ev.preventDefault(); A().goStock(a.dataset.code); }; });
    $$('#etfRetTbl tr[data-code]').forEach((tr) => { tr.onclick = () => A().goStock(tr.dataset.code); });
  }
  const COLS = '<colgroup><col><col style="width:56px"><col style="width:80px"><col style="width:58px"><col style="width:162px"></colgroup>';
  function calRows(L, withDate) {
    return L.map((e) => `<tr data-code="${esc(e.code)}" title="${esc(e.name)} ${esc(e.code)}：除息 ${e.ex}，配 ${e.amt} 元">
      <td>${withDate ? `<span class="note">${e.ex.slice(5)}</span> ` : ''}${esc(e.name)} <span class="note">${esc(e.code)}</span></td>
      <td>${A().fmt.n(e.amt, 3)}</td><td title="${esc(e.basis)}">${pctU(e.y)}${/估/.test(e.basis || '') ? '<span class="na">估</span>' : ''}</td>
      <td>${e.pay ? e.pay.slice(5) : '<span class="na">—</span>'}</td>
      <td class="fill${e.fill == null && e.fill_wait != null ? ' down' : ''}">${fillTxt(e.fill, e.fill_wait)}</td></tr>`).join('');
  }
  const THEAD = (first) => `<thead><tr><th>${first}</th><th title="每單位配息（元）">配息</th><th>當次殖利率</th><th>發放</th><th>填息天數</th></tr></thead>`;
  /* 點某一檔：近幾次配息小長條＋當次殖利率走勢＋填息天數（資料＝行事曆近 400 天的除息紀錄） */
  function codeDetail(code) {
    const CGs = window.CalGrid.svg, all = ((S.data && S.data.calendar) || []).filter((e) => e.code === code).sort((a, b) => (a.ex < b.ex ? -1 : 1));
    const it = byCode().get(code) || { name: code };
    const done = all.filter((e) => e.ex <= (S.data.asof || '9999')), L = (done.length ? done : all).slice(-8);
    const src = '證交所／櫃買中心除息紀錄（近 400 天）；當次殖利率＝配息 ÷ 除息前一日收盤（未除息者用最新收盤估算）';
    const head = `<div class="ph stk"><button type="button" class="btn small" id="etfCodeBack">← 回清單</button><a class="plink" href="#stock/${esc(code)}" data-code="${esc(code)}" title="看 ${esc(it.name)} ${esc(code)} 個股頁">${esc(it.name)} ${esc(code)}</a><span class="sp"></span>${srcI(src)}</div>`;
    if (!L.length) return `${head}<p class="note">無除息紀錄</p>`;
    const fills = all.filter((e) => e.fill != null).map((e) => e.fill), avg = fills.length ? Math.round(fills.reduce((a, b) => a + b, 0) / fills.length) : null;
    const last = L[L.length - 1], ys = L.map((e) => (e.y == null ? null : +(e.y * 100).toFixed(2)));
    const bars = CGs.bars(L.map((e) => +e.amt), { color: () => 'var(--amber)', tip: (i) => `${L[i].ex} 配 ${L[i].amt} 元` });
    const ln = CGs.line(ys, { color: 'var(--cyan)', tip: (i) => `${L[i].ex} 當次殖利率 ${ys[i]}%` });
    return `${head}
      <div class="kpis"><div><small>最近一次配息</small><b>${A().fmt.n(last.amt, 3)} 元</b></div><div><small>當次殖利率</small><b>${last.y == null ? '—' : pctU(last.y, 2)}</b></div>
        <div><small>平均填息</small><b>${avg == null ? '—' : avg + ' 天'}</b></div></div>
      <div class="mini"><div class="mk"><b>${L.length} 次</b><small>近期配息</small></div><div class="mc">${CGs.wrap(bars + ln)}
        <div class="ml"><span>${esc(L[0].ex.slice(2))}</span><span><i style="background:var(--amber)"></i>配息　<i style="background:var(--cyan)"></i>殖利率</span><span>${esc(last.ex.slice(2))}</span></div></div></div>
      <table class="et" id="etfCodeTbl">${COLS}${THEAD('除息日')}<tbody>${calRows(L.slice().reverse(), true)}</tbody></table>`;
  }
  function calList(day, L) {
    const wd = WD[new Date(day + 'T00:00:00Z').getUTCDay()];
    return `<div class="ph stk"><button type="button" class="btn small" id="etfDayBack">← 回整月</button><b>${day}（${wd}）除息 ${L.length} 檔</b><span class="sp"></span></div>
      <table class="et" id="etfDayTbl">${COLS}${THEAD('ETF')}<tbody>${calRows(L, false)}</tbody></table>`;
  }
  function monthList(L, y, mo) {
    const head = `<b class="lt">${y} 年 ${mo} 月除息一覽（${L.length} 筆）</b>`;
    if (!L.length) return head + `<p class="note">${S.fallback || !((S.data && S.data.calendar) || []).length ? '尚無除息資料' : '本月無除息'}</p>`;
    return head + `<table class="et">${COLS}${THEAD('除息日 ETF')}<tbody>${calRows(L, true)}</tbody></table>`;
  }

  /* ------------------------------------------------------------------ 4. 報酬比較（自選） */
  const cmpKey = () => 'tw.etf.cmp.' + S.cat;
  function defaultCmp() {
    // 預設＝報酬率前 5；這段期間有資料的不足 5 檔，就用規模大的補滿（讓表格誠實列出「上市未滿／尚未回補」）
    const top = retRank().rows.slice(0, 5).map((x) => x.it.code);
    const rest = inCat().slice().sort((a, b) => sizeKey(b) - sizeKey(a)).map((it) => it.code).filter((c) => !top.includes(c));
    return top.concat(rest).slice(0, 5);
  }
  function getCmp() {
    if (!(S.cat in S.cmp)) {
      let v = null;
      try { v = JSON.parse(LS.get(cmpKey(), 'null')); } catch (e) { v = null; }
      S.cmp[S.cat] = Array.isArray(v) ? v : null;
    }
    const has = new Set(inCat().map((it) => it.code));
    const v = S.cmp[S.cat];
    return v ? v.filter((c) => has.has(c)).slice(0, CMP_MAX) : defaultCmp();
  }
  function setCmp(codes) {
    S.cmp[S.cat] = codes.slice(0, CMP_MAX);
    LS.set(cmpKey(), JSON.stringify(S.cmp[S.cat]));
  }
  function flash(msg) {
    const el = $('#etfCmpMsg'); if (!el) return;
    el.textContent = msg; clearTimeout(flash._t);
    flash._t = setTimeout(() => { el.textContent = ''; }, 2600);
  }
  const PALC = () => SOFT().pal;
  function cmpDD() {
    const dd = $('#etfCmpDD'); if (!dd || !A().msDD) return null;
    const codeOf = (n) => String(n).split(' ')[0];
    return A().msDD(dd, {
      menu: { rf: 'etf', kind: 'etfcmp' },
      onToggle: (c) => {
        const code = codeOf(c.dataset.n); let cur = getCmp();
        if (c.checked) {
          if (cur.length >= CMP_MAX) { c.checked = false; flash(`最多比較 ${CMP_MAX} 檔`); return; }
          if (!cur.includes(code)) cur = cur.concat(code);
        } else cur = cur.filter((x) => x !== code);
        setCmp(cur); drawRet();
      },
      onAll: (vis) => {
        let cur = getCmp(); const add = vis.map(codeOf).filter((c) => !cur.includes(c));
        if (cur.length + add.length > CMP_MAX) flash(`最多比較 ${CMP_MAX} 檔，只加到滿`);
        cur = cur.concat(add).slice(0, CMP_MAX); setCmp(cur); drawRet();
      },
      onNone: (vis) => {
        const rm = new Set((vis || getCmp()).map(codeOf));
        setCmp(getCmp().filter((c) => !rm.has(c))); drawRet();
      },
    });
  }
  function syncDD(sel, colorOf) {
    const ms = cmpDD(); if (!ms) return;
    const pk = perKey(), on = new Set(sel);
    const all = inCat().slice().sort((a, b) => sizeKey(b) - sizeKey(a));
    const val = (it) => { const st = (it.stats || {})[pk]; if (!st || !st.ok) return '—';
      return st.tr_ann != null ? pct(st.tr_ann, 1) : pct(st.price_ann, 1); };
    ms.sync({
      rows: all.map((it) => ({ name: `${it.code} ${it.name}`, on: on.has(it.code), color: on.has(it.code) ? colorOf[it.code] : A().hexA(A().CH.ink3, 0.45),
        val: val(it), valTitle: `${perLabel()} 年化（含息；無配息資料時為不含息）` })),
      count: `${S.cat} 共 ${all.length} 檔 · 已選 ${sel.length}／${CMP_MAX}`,
      label: `已選 ${sel.length} 檔`,
      n: sel.length,
    });
  }
  function holdEmpty(id, msg) {
    const el = document.getElementById(id); if (!el) return;
    const c = window.echarts && echarts.getInstanceByDom(el); if (c) c.dispose();
    el.classList.remove('isempty');
    el.innerHTML = `<div class="etfprep">${esc(msg)}</div>`;
  }
  function drawRet() {
    const card = $('#etfRetCard'), body = $('#etfRetBody');
    card.hidden = false;
    if (card.hidden) return;
    $$('#etfBasisSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.basis);
      b.onclick = () => { S.basis = b.dataset.v; LS.set('tw.etf.basis', S.basis); drawRet(); }; });
    $('#etfRetSub').textContent = `${S.cat}・${perLabel()}`;
    if (S.fallback) {
      body.innerHTML = '<div class="etfprep">尚無資料</div>';
      body.dataset.k = ''; body.dataset.codes = ''; syncDD([], {}); return;
    }
    const sel = getCmp();
    const PC = PALC(), colorOf = {}; sel.forEach((c, i) => { colorOf[c] = PC[i % PC.length]; });
    syncDD(sel, colorOf);
    const m = byCode(), pk = perKey();
    if (!sel.length) {
      body.innerHTML = '<div class="etfprep">尚未選擇 ETF</div>';
      body.dataset.k = pk; body.dataset.codes = ''; return;
    }
    const rows = sel.map((c) => { const it = m.get(c) || { code: c, name: c, stats: {} }; return { it, st: statOf(it) }; });
    const num = (v, f) => (v == null ? '<span class="na">—</span>' : f(v));
    body.innerHTML = `<div class="retcharts"><div><div class="note note1">累積報酬走勢（${S.basis === 'tr' ? '含息總報酬' : '價格，不含息'}；期初 = 0%）</div><div id="etfRetLine" class="chart"></div></div>
      <div><div class="note note1">年化報酬率（不含息 vs 含息）</div><div id="etfRetBar" class="chart"></div></div></div>
      <div class="rettw"><table class="et fullw" id="etfRetTbl"><colgroup><col style="width:27%"><col style="width:21%"><col style="width:13%"><col style="width:13%"><col style="width:13%"><col style="width:13%"></colgroup>
      <thead><tr><th class="nmc">ETF</th><th>期間</th><th>價格年化（不含息）</th><th>含息年化</th><th>殖利率（近 12 月）</th><th>配息年化</th></tr></thead><tbody>
      ${rows.map(({ it, st }) => `<tr data-code="${esc(it.code)}"><td class="nmc"><span class="nmw"><i style="background:${colorOf[it.code]}"></i><span class="nmt" title="${esc(it.name)} ${esc(it.code)}">${esc(it.name)}</span><span class="note">${esc(it.code)}</span></span></td>
        ${st.ok ? `<td>${st.since ? `<span title="上市以來：不和 5 年期直接比較">${esc(st.from)}～ <span class="note">上市以來 ${st.years} 年</span></span>` : `${st.from}～ <span class="note">${st.years} 年</span>`}</td><td class="${cls(st.price_ann)}">${num(st.price_ann, (v) => pct(v, 2))}</td>
        <td class="${cls(st.tr_ann)}">${st.tr_ann == null ? `<span class="na">${'—'}</span>` : `${pct(st.tr_ann, 2)}${st.nodiv ? ' <span class="na">不配息</span>' : ''}`}</td>`
        : `<td colspan="3"><span class="na">無資料</span></td>`}
        <td>${noDiv(it) ? '<span class="na">不配息</span>' : num(it.yield_ttm, (v) => pctU(v))}</td><td>${st.ok ? (noDiv(it) ? '<span class="na">不配息</span>' : num(st.div_ann, (v) => pctU(v))) : '<span class="na">—</span>'}</td></tr>`).join('')}</tbody></table></div>`;
    body.dataset.k = pk + '|' + S.cat + '|' + S.basis; body.dataset.codes = sel.join(',');
    $$('tr[data-code]', body).forEach((tr) => { tr.onclick = () => A().goStock(tr.dataset.code); });
    drawRetCharts(rows, colorOf);
    if (!S.series) loadSeries().then(() => { if (!$('#etfRetCard').hidden && $('#etfRetBody').dataset.codes === sel.join(',')) drawRet(); });
  }
  function drawRetCharts(rows, colorOf) {
    const a = A(), CH = a.CH;
    const lines = [];
    rows.forEach(({ it, st }) => {
      const s = seriesOf(it.code); if (!s || !st.ok) return;
      const vals = S.basis === 'tr' ? (s.t || (noDiv(it) ? s.p : null)) : s.p; if (!vals) return;
      const i0 = s.d.findIndex((d) => d >= st.from); if (i0 < 0) return;
      const base = vals[i0]; if (!base) return;
      const col = colorOf[it.code];
      lines.push({ name: `${it.name} ${it.code}${st.since ? `（自 ${st.from.slice(0, 7)} 上市）` : ''}`, type: 'line', showSymbol: false, smooth: false, lineStyle: { width: 1.8, color: col }, emphasis: { focus: 'series' }, itemStyle: { color: col },
        data: s.d.slice(i0).map((d, j) => [d, +((vals[i0 + j] / base - 1) * 100).toFixed(2)]) });
    });
    const lineEl = $('#etfRetLine'); if (!lineEl) return;
    const yrsSpan = Math.max(...rows.map(({ st }) => (st.ok ? +st.years || 0 : 0)), 0.5);
    const SC = SOFT();
    if (!lines.length) {
      holdEmpty('etfRetLine', !S.series ? '載入中…' : '無資料');
    } else {
      lineEl.innerHTML = '';
      a.chart('etfRetLine', {
        grid: { left: 52, right: 14, top: 34, bottom: 28 }, legend: { top: 0, textStyle: { color: CH.ink2, fontSize: 12 }, type: 'scroll' },
        tooltip: { trigger: 'axis', valueFormatter: (v) => (v > 0 ? '+' : '') + v + '%' },
        xAxis: { type: 'time', ...a.axisStyle, splitNumber: yrsSpan <= 3.2 ? 14 : yrsSpan <= 6 ? 12 : 10, splitLine: { show: false },
          axisLabel: { ...a.axisStyle.axisLabel, hideOverlap: true, formatter: { year: '{yyyy}', month: '{M}月', day: '{M}/{d}' } },
          minorTick: { show: true, splitNumber: yrsSpan <= 3.2 ? 1 : 3 }, minorSplitLine: { show: false } },
        yAxis: { type: 'value', ...a.axisStyle, splitLine: { show: true, lineStyle: { color: CH.grid, opacity: 1, width: 1 } },
          axisLabel: { ...a.axisStyle.axisLabel, formatter: (v) => v + '%' } },
        series: lines,
      });
    }
    lineEl.dataset.n = String(lines.length);
    const ok = rows.filter(({ st }) => st.ok);
    const barEl = $('#etfRetBar');
    if (!ok.length) { holdEmpty('etfRetBar', '無資料'); barEl.dataset.n = '0'; return; }
    const sorted = ok.slice().sort((x, y) => ((y.st.tr_ann != null ? y.st.tr_ann : y.st.price_ann) - (x.st.tr_ann != null ? x.st.tr_ann : x.st.price_ann)));
    const v = (x) => (x == null ? null : +(x * 100).toFixed(2));
    barEl.innerHTML = '';
    a.chart('etfRetBar', {
      grid: { left: 96, right: 52, top: 30, bottom: 24 }, legend: { top: 0, textStyle: { color: CH.ink2, fontSize: 12 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (x) => (x == null ? '無資料' : x + '%') },
      xAxis: { type: 'value', ...a.axisStyle, splitLine: { show: true, lineStyle: { color: CH.grid, opacity: 1 } }, axisLabel: { ...a.axisStyle.axisLabel, formatter: (x) => x + '%' } },
      yAxis: { type: 'category', inverse: true, data: sorted.map(({ it, st }) => (st.since ? `${it.name}\n上市以來 ${st.years} 年` : it.name)), ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, fontSize: 12, width: 86, overflow: 'truncate' } },
      series: [
        { name: '不含息', type: 'bar', data: sorted.map(({ st }) => v(st.price_ann)), itemStyle: { color: SC.a, borderRadius: [0, 2, 2, 0] }, barMaxWidth: 10,
          label: { show: true, position: 'right', color: CH.ink2, fontSize: 11, formatter: (p) => (p.value == null ? '' : p.value + '%') } },
        { name: '含息', type: 'bar', data: sorted.map(({ st }) => v(st.tr_ann)), itemStyle: { color: SC.b, borderRadius: [0, 2, 2, 0] }, barMaxWidth: 10,
          label: { show: true, position: 'right', color: CH.ink2, fontSize: 11, formatter: (p) => (p.value == null ? '無資料' : p.value + '%') } },
      ],
    });
    barEl.dataset.n = String(ok.length);
  }

  /* ------------------------------------------------------------------ 入口 */
  function drawAll() {
    drawCats();
    const tri = $('#etfTri'); tri.hidden = !!NO_RANK[S.cat];
    if (!tri.hidden) { drawPop(); drawRetTop(); drawYld(); }
    drawRet(); drawList();
    $('#v-etf').dataset.cat = S.cat;
  }
  async function render() {
    injectCSS();
    const root = document.getElementById('v-etf'); if (!root) return;
    S.cat = '配息型'; S.pop = LS.get('tw.etf.pop', 'holders');
    S.per = LS.get('tw.etf.per', '5y'); S.basis = LS.get('tw.etf.basis', 'tr'); S.cmp = {};
    try { await window.CalGrid.load(); } catch (e) { /* 沒有休市日只標週末 */ }
    skeleton(root);
    $('#etfSort').onchange = (e) => { S.sort = e.target.value; S.shown = PAGE; drawList(); };
    $('#etfGrid').innerHTML = '<div class="etfprep">載入中…</div>';
    await loadData();
    if (!S.fallback) loadSeries().then(() => { drawRetTop(); drawRet(); });
    if (!items().some((it) => it.cat === S.cat)) S.cat = (CATS.find((c) => items().some((it) => it.cat === c)) || S.cat);
    drawCal(); drawAll();
    root.dataset.ready = S.fallback ? 'fallback' : 'full';
  }
  window.TwEtfPage = { render, classify, state: S };
})();
