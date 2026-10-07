/* ============================================================================
   ETF 專區（#etf）—— Andy 2026-10-05（參考別家 ETF 專區的截圖，名稱與版面自己做）
   規格與每個數字的口徑：docs/etf_page_spec.md（分類規則、熱門定義、殖利率、年化報酬、填息天數）。

   版面（2026-10-05 第二版，Andy：「配息行事曆放最上面」「每個分類頁內並排前 5」「自選比較清單」）：
     ① 配息行事曆（7 欄真月曆，格內直接寫當天除息的代號與金額，點格子右側展開當天清單＋填息天數）
     ② 分類分頁列（配息型／市值型／…，預設配息型，無「全部」）；期間 10-06 搬到 ④ 的標題列（site/rangepick.js 共用元件）
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
#v-etf .etfsub{margin:0 0 10px}
#v-etf .etfcatbar[hidden],#v-etf .etfbody[hidden]{display:none}   /* v8：.etfcatbar 有 display:flex，hidden 屬性蓋不掉 */
#v-etf .etfcatbar{display:flex;align-items:center;gap:10px;margin:0;white-space:nowrap;min-width:0}
#v-etf .etfcatbar .seg{overflow:hidden;flex:0 1 auto;min-width:0}
/* 分類頁籤：全站共用 .nbsw（產業地圖同款資料夾分頁，DECISIONS #321）；只補「不擠掉右邊期間」 */
#v-etf .etfcatbar .nbsw{flex:0 1 auto;min-width:0;align-self:flex-end}
#v-etf .etfcatbar{align-items:flex-end}
#v-etf .etfcatbar .sp{flex:1}
#v-etf #etfRngBox{display:inline-flex;min-width:0}
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
#v-etf .etfmore .btn[hidden],#v-etf .incmore .btn[hidden]{display:none}
/* ---- 三張前 5 名：同高並排 */
#v-etf .etftri{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--sp-3);margin-bottom:var(--sp-3);align-items:stretch}
#v-etf .etftri>.card{margin:0;display:flex;flex-direction:column;min-width:0}
#v-etf .etftri[hidden]{display:none}
/* Andy 10-07「需要同一排」：三張卡的標題列、副標、表頭、5 列資料要水平對齊。
   受歡迎卡的標題列多一組切換鈕會比較高，所以標題列給固定最小高度；副標固定一行高，空的也佔位。 */
/* 卡寬約 300～345px 放不下「標題＋? ＋口徑切換」一整行（會擠到 ? 鈕），所以切換鈕縮小後移到副標那一行右側。 */
#v-etf .etftri>.card>.row.spread{height:32px;min-height:32px;align-items:center;flex-wrap:nowrap}
#v-etf .etftri .etfq{height:26px;line-height:26px;min-height:26px;margin:2px 0 10px}
#v-etf .etfqrow{display:flex;align-items:center;gap:8px;height:26px;margin:2px 0 10px}
#v-etf .etfqrow .etfq{margin:0;flex:1;min-width:0}
#v-etf .etfqseg{flex:none}
#v-etf .etfqseg button{height:24px;min-height:24px;padding:0 8px;font-size:12px;line-height:22px}
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
#v-etf .etfc dt{text-align:left} #v-etf .etfc dd{text-align:right;font-variant-numeric:tabular-nums}
#v-etf .etfc .h .fq.fqtag{background:var(--fc);color:var(--ontop,#0b1220);flex:none;font-size:11.5px;line-height:17px;padding:1px 7px;border-radius:999px;font-weight:700;white-space:nowrap}
#v-etf .etfc .etag{flex:none}
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
/* ---- 2026-10-07 配息頻率色（Andy：「不同週期配息的顏色需要有差異才能直觀看得出來」）。
   不准用紅綠（那是漲跌色）；月配 青綠、雙月配 紫、季配 琥珀、半年配 藍、年配 灰。深淺主題各一組（淺色加深到對白底 ≥ 4.5:1）。
   卡片牆徽章＋左色條、現金流試算的徽章與 12 格月曆都用這一套；寫進 docs/style_guide.md。 */
#v-etf{--fq-m:#2dd4bf;--fq-b:#c084fc;--fq-q:#fbbf24;--fq-h:#60a5fa;--fq-y:#9ca3af}
:root[data-theme="light"] #v-etf{--fq-m:#0f766e;--fq-b:#7e22ce;--fq-q:#a16207;--fq-h:#1d4ed8;--fq-y:#4b5563}
#v-etf .fqc-m{--fc:var(--fq-m)} #v-etf .fqc-b{--fc:var(--fq-b)} #v-etf .fqc-q{--fc:var(--fq-q)} #v-etf .fqc-h{--fc:var(--fq-h)} #v-etf .fqc-y{--fc:var(--fq-y)}
#v-etf .etfc .fq[class*="fqc-"],#v-etf .fqb{color:var(--fc);background:color-mix(in srgb,var(--fc) 16%,transparent)}
#v-etf .fqb{display:inline-block;padding:0 6px;border-radius:999px;font-size:11.5px;line-height:17px;white-space:nowrap;font-family:inherit;font-weight:600}
#v-etf .etfc.fqbar{--tc:var(--fc)}
#v-etf .fqhd{grid-column:1/-1;display:flex;align-items:center;gap:8px;margin:8px 0 0;font-size:14px;font-weight:700;color:var(--ink);white-space:nowrap}
#v-etf .fqhd:first-child{margin-top:0}
#v-etf .fqhd i{width:10px;height:10px;border-radius:3px;background:var(--fc);flex:none}
/* 子類型色（2026-10-07）：低飽和、不用紅綠，只拿來分組，不帶好壞意思；照組順序輪用 8 色 */
#v-etf{--sg0:#8fa3bf;--sg1:#a3a0d6;--sg2:#b8a0cc;--sg3:#8db4c8;--sg4:#c4b08a;--sg5:#c49fb6;--sg6:#a3a3a3;--sg7:#9db0c4}
:root[data-theme="light"] #v-etf{--sg0:#475569;--sg1:#4f46a5;--sg2:#6b4a8a;--sg3:#2f6680;--sg4:#7a5c1e;--sg5:#7d3f66;--sg6:#525252;--sg7:#3f5670}
#v-etf .sgc-0{--fc:var(--sg0)} #v-etf .sgc-1{--fc:var(--sg1)} #v-etf .sgc-2{--fc:var(--sg2)} #v-etf .sgc-3{--fc:var(--sg3)}
#v-etf .sgc-4{--fc:var(--sg4)} #v-etf .sgc-5{--fc:var(--sg5)} #v-etf .sgc-6{--fc:var(--sg6)} #v-etf .sgc-7{--fc:var(--sg7)}
#v-etf .fqhd small{font-weight:400;color:var(--ink-3);font-size:12px}
/* ---- 現金流試算（2026-10-07） */
#v-etf .etfcatbar .etfinctab{flex:none;margin-left:6px}
#v-etf #etfInc .incdisc{margin:0 0 10px;font-size:12px;line-height:17px;color:var(--ink-3)}
#v-etf .incctl{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;margin-bottom:12px}
#v-etf .incctl .grp{display:flex;align-items:center;gap:6px;flex-wrap:wrap;min-width:0;max-width:100%}
#v-etf .incctl .grp>b{font-size:13px;color:var(--ink-2);font-weight:600;white-space:nowrap}
#v-etf .incctl input[type=number]{width:104px;height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font:13px var(--mono);box-sizing:border-box}
#v-etf .incctl label.chk{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--ink-2);cursor:pointer}
#v-etf .incsec{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}
#v-etf .incq{font-size:13px;color:var(--ink-2);margin:0 0 8px;line-height:1.55}
#v-etf .incq b{color:var(--ink)}
#v-etf #incBar{height:340px}
#v-etf .inctw{overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch;margin-top:8px}
#v-etf table.inct{width:100%;min-width:900px;border-collapse:separate;border-spacing:0;font-size:13px}
#v-etf table.inct th{color:var(--ink-3);font-weight:600;padding:6px;border-bottom:1px solid var(--line);white-space:nowrap;text-align:center;background:var(--panel)}
#v-etf table.inct td{padding:6px;border-bottom:1px solid var(--line);font-family:var(--mono);white-space:nowrap;text-align:center}
#v-etf table.inct td.nm,#v-etf table.inct th.nm{position:sticky;left:0;z-index:1;background:var(--panel);text-align:left;font-family:inherit;max-width:190px;overflow:hidden;text-overflow:ellipsis;cursor:pointer}
#v-etf table.inct tr[data-code]{cursor:pointer}
#v-etf table.inct tr[data-code]:hover td,#v-etf table.inct tr.on td{background:var(--panel-3)}
#v-etf table.inct td.nm .cd{font:12px var(--mono);color:var(--ink-3);margin:0 4px}
#v-etf .incmore{text-align:center;margin-top:8px}
#v-etf .combos{display:flex;flex-direction:column;gap:10px}
#v-etf .combo{border:1px solid var(--line);border-radius:10px;background:var(--panel-2);padding:10px 12px;min-width:0}
#v-etf .combo .ch{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:6px}
#v-etf .combo .ch .rk{font:700 16px var(--mono);color:var(--amber)}
#v-etf .combo .kp{display:flex;gap:6px 14px;flex-wrap:wrap;font-size:12.5px;color:var(--ink-3)}
#v-etf .combo .kp b{font:700 14px var(--mono);color:var(--ink);margin-left:4px}
#v-etf .combo .mem{display:flex;flex-wrap:wrap;gap:6px 14px;margin:4px 0 8px;font-size:13px}
#v-etf .combo .mem button{display:flex;align-items:center;gap:6px;background:none;border:0;padding:0;color:var(--ink);font:inherit;cursor:pointer;white-space:nowrap;max-width:100%;min-width:0}
#v-etf .combo .mem .mn{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-etf .combo .mem button:hover .mn{text-decoration:underline}
#v-etf .combo .mem .ml{font-family:var(--mono);color:var(--ink-2)}
#v-etf .mgrid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:4px}
#v-etf .mcell{border-radius:6px;padding:3px 2px;text-align:center;background:color-mix(in srgb,var(--fc,var(--ink-3)) 18%,var(--panel-3));border:1px solid color-mix(in srgb,var(--fc,var(--ink-3)) 55%,transparent);min-width:0;overflow:hidden}
#v-etf .mcell small{display:block;font-size:11px;color:var(--ink-3);line-height:14px}
#v-etf .mcell b{display:block;font:700 12px var(--mono);line-height:16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--ink)}
#v-etf .mcell span{display:block;font:11px var(--mono);color:var(--ink-2);line-height:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-etf .inclg{display:flex;flex-wrap:wrap;gap:6px 10px;font-size:12px;color:var(--ink-3);margin:2px 0 8px;align-items:center}
/* ---- 現金流試算 v2（2026-10-07 晚）：二級分頁、主圖＋總清單、細節卡、時鐘、再投入回測 */
#v-etf .incctl.incrx{margin-top:-4px}
#v-etf .incrx .rxchips{font-size:12.5px;color:var(--ink-2);white-space:nowrap}
#v-etf .incrx input{width:170px;height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font:13px var(--mono);box-sizing:border-box;max-width:100%}
#v-etf .incrx .rxmsg{color:var(--amber);font-size:12px}
#v-etf .inctabs{margin:4px 0 0}
#v-etf .incsg{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:12px;align-items:start}
#v-etf .incbarw{min-width:0}
#v-etf .inclist{border:1px solid var(--line);border-radius:10px;background:var(--panel-2);padding:8px;min-width:0;display:flex;flex-direction:column;max-height:380px}
#v-etf .inclist .ilhd{display:flex;gap:6px;align-items:center}
#v-etf .inclist input[type=search]{flex:1;min-width:0;height:28px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font-size:13px}
#v-etf .inclist .ilfq{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0 2px}
#v-etf .inclist .ilfq button{font-size:12px;height:24px;padding:0 8px;border-radius:12px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink-2);cursor:pointer}
#v-etf .inclist .ilfq button.on{background:var(--cyan);border-color:var(--cyan);color:var(--bg)}
#v-etf .inclist .ilfq button small{opacity:.75;margin-left:2px}
#v-etf .inclist .ilmsg{margin:4px 0 0;font-size:12px;color:var(--amber);min-height:0}
#v-etf .inclist .ilmsg:empty{display:none}
#v-etf .inclist .ilbody{overflow-y:auto;margin-top:6px;flex:1;min-height:0}
#v-etf .ilr{display:grid;grid-template-columns:18px 22px minmax(0,1fr) auto;grid-template-rows:auto auto;column-gap:6px;align-items:center;padding:4px 4px;border-bottom:1px solid var(--line);font-size:12.5px}
#v-etf .ilr.on{background:var(--panel-3)}
#v-etf .ilr input{grid-row:1/3;margin:0;cursor:pointer}
#v-etf .ilr .rk{grid-row:1/3;font:11px var(--mono);color:var(--ink-3);text-align:right}
#v-etf .ilr .iln{display:flex;align-items:center;gap:5px;background:none;border:0;padding:0;color:var(--ink);font:inherit;cursor:pointer;min-width:0;text-align:left}
#v-etf .ilr .iln .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
#v-etf .ilr .iln:hover .nm{text-decoration:underline}
#v-etf .ilr .cd{font:11.5px var(--mono);color:var(--ink-3)}
#v-etf .ilr .mv{font:12px var(--mono);color:var(--ink);text-align:right}
#v-etf .ilr .lt{grid-column:3/5;font:11.5px var(--mono);color:var(--ink-3)}
#v-etf .incdet{margin-top:12px;border:1px solid var(--line-2);border-radius:10px;background:var(--panel-2);padding:10px 12px}
#v-etf .incdet .dethd{display:flex;align-items:center;gap:8px 12px;flex-wrap:wrap}
#v-etf .incdet .dethd>b{font-size:14px;display:flex;align-items:center;gap:6px}
#v-etf .incdet .dlots{display:flex;align-items:center;gap:4px;font-size:12.5px;color:var(--ink-2)}
#v-etf .incdet .dlots input{width:80px;height:28px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 6px;font:13px var(--mono)}
#v-etf .detg{display:grid;grid-template-columns:220px minmax(0,1fr);gap:12px}
#v-etf #incMb{height:190px}
#v-etf .sth{font-size:12px;color:var(--ink-3);margin-bottom:2px}
#v-etf .incsim{margin-top:10px;border-top:1px dashed var(--line);padding-top:8px;min-width:0}
#v-etf .incsim .simhd{display:flex;gap:4px 10px;align-items:baseline;flex-wrap:wrap;font-size:13px}
#v-etf .incsim .simhd small{color:var(--ink-3);font-size:12px}
#v-etf .incsim .simch{height:280px}
#v-etf .incsim .simtw{overflow-x:auto;max-width:100%}
#v-etf table.simt{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:4px}
#v-etf table.simt th{color:var(--ink-3);font-weight:600;padding:4px 6px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
#v-etf table.simt td{padding:4px 6px;border-bottom:1px solid var(--line);font-family:var(--mono);text-align:right;white-space:nowrap}
#v-etf table.simt .nm{text-align:left;font-family:inherit;white-space:normal}
#v-etf table.simt tr.dim td{color:var(--ink-3)}
#v-etf .incsim .simlev{margin:4px 0 0;font-size:11.5px;color:var(--ink-3)}
#v-etf .combo .cbody{display:grid;grid-template-columns:240px 180px minmax(0,1fr);gap:12px;align-items:center}
#v-etf .combo .cbody.noclk{grid-template-columns:180px minmax(0,1fr)}
#v-etf .combo .cbody .mem{flex-direction:column;align-items:stretch;margin:0;min-width:0}
#v-etf .combo .cbody .mem button{flex-wrap:wrap;white-space:normal;text-align:left}
#v-etf .combo .mem button i{width:9px;height:9px;border-radius:2px;flex:none}
#v-etf .combo .mgrid{margin-top:8px}
/* ---- v3（17:40 回饋）：組合 A～E 分頁、左欄兩圖上下同尺寸、右欄曲線＋清單；曲線工具列 */
#v-etf .cmbtabs{margin:4px 0 8px;flex-wrap:wrap}
#v-etf .cmbtabs button small{margin-left:6px;font:11.5px var(--mono);opacity:.8}
#v-etf .incctl input,#v-etf h3 .mlab input{font-family:var(--mono)}
#v-etf h3 .mlab{font-size:13px;font-weight:600;color:var(--ink-2);display:inline-flex;align-items:center;gap:4px;margin-left:6px}
#v-etf h3 .mlab input{width:92px;height:28px;border-radius:8px;border:1px solid var(--cat-1,var(--line-2));background:var(--panel-3);color:var(--ink);padding:0 6px;font-size:14px;font-weight:700}
#v-etf .cgrid{display:grid;grid-template-columns:minmax(300px,420px) minmax(0,1fr);gap:16px;align-items:start}
#v-etf .cgrid .cleft,#v-etf .cgrid .cright{min-width:0}
#v-etf .cgrid .cright .incsim{margin-top:0;border-top:0;padding-top:0}
#v-etf .cdnrow{display:grid;grid-template-columns:300px minmax(0,1fr);align-items:center;gap:6px}
#v-etf .cdnrow .mem{display:flex;flex-direction:column;gap:6px;margin:0;min-width:0}
#v-etf .cdnrow .mem button{white-space:normal;text-align:left}
#v-etf .cleft #incDn{width:100%}
#v-etf .simbar{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin:4px 0 6px}
#v-etf .simbar .cmpw{display:flex;gap:4px;align-items:center;min-width:0}
#v-etf .simbar .cmpin{width:190px;max-width:100%;height:28px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font-size:12.5px;box-sizing:border-box}
#v-etf .simbar .cmpchips{display:flex;flex-wrap:wrap;gap:4px}
#v-etf .simbar .chip{border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);border-radius:999px;padding:1px 8px;font-size:12px;cursor:pointer}
#v-etf .simbar .rxmsg{color:var(--amber);font-size:12px}
#v-etf .simbar .rxmsg:empty{display:none}
#v-etf #incLine{height:400px}
#v-etf table.simt td.nm i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;vertical-align:middle}
#v-etf .mcell[style*="--fc"]{background:color-mix(in srgb,var(--fc) 30%,var(--panel-3));border-color:var(--fc)}
@media (max-width:1100px){#v-etf .cgrid{grid-template-columns:1fr}#v-etf .cleft .clk,#v-etf .cleft .cdn{margin:0 auto}}
@media (max-width:640px){#v-etf .cdnrow{grid-template-columns:1fr}#v-etf .cdnrow .cdn{margin:0 auto}#v-etf .simbar .cmpw{flex:1 1 100%}#v-etf .simbar .cmpin{flex:1}}
/* ---- v4（18:20 回饋）：月配試算表／複利試算表兩大分頁；圖放大（甜甜圈 320）、清單可拉寬、複利曲線 460 高可縮放 */
#v-etf .incmain{margin:0 0 10px}
#v-etf .incmain button{font-size:14.5px;font-weight:700;padding-left:16px;padding-right:16px}
#v-etf .incsg{display:flex;gap:12px;align-items:flex-start}
#v-etf .incsg .incbarw{flex:1 1 auto;min-width:0}
#v-etf .inclist{flex:0 0 auto;width:360px;min-width:260px;max-width:60%;resize:horizontal;overflow:hidden;max-height:460px}
#v-etf .ilr .mv{font-size:12px;white-space:nowrap}
#v-etf .cgrid{grid-template-columns:minmax(320px,360px) minmax(0,1fr)}
#v-etf .dnbig{width:320px;max-width:100%;height:320px}
#v-etf .mbars{height:320px}
#v-etf small.lbl{color:var(--ink-3);font-size:12px}
#v-etf #incCTbl td.nm button{display:flex;align-items:center;gap:6px;background:none;border:0;padding:0;color:var(--ink);font:inherit;cursor:pointer;text-align:left}
#v-etf #incCTbl td.nm i{margin:0}
#v-etf #incCTbl td.nm button:hover{text-decoration:underline}
#v-etf .cxctl{margin-bottom:8px}
#v-etf .cxctl select{height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font-size:13px;max-width:100%;min-width:0}
#v-etf .cxctl input[type=date]{height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font:13px var(--mono)}
#v-etf .cxctl .cmpin{width:200px;max-width:100%;height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font-size:12.5px;box-sizing:border-box}
#v-etf .cxctl .cmpchips{display:flex;flex-wrap:wrap;gap:4px}
#v-etf .cxctl .chip{border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);border-radius:999px;padding:1px 8px;font-size:12px;cursor:pointer}
#v-etf .cxctl .rxmsg{color:var(--amber);font-size:12px}
#v-etf .cxhead{font-size:14px;line-height:1.6;color:var(--ink-2);margin:6px 0 4px;min-height:4.8em}   /* v6：固定最小高度，點圖例改結論句時整張圖不會上下跳 */
@media (max-width:600px){#v-etf .cxhead{min-height:8em}}
#v-etf .cxhead b{color:var(--ink)}
#v-etf #cxChart{height:540px}
#v-etf .simtw{overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch}
#v-etf #cxTbl td.nm i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;vertical-align:middle}
@media (max-width:1100px){#v-etf .incsg{flex-direction:column;align-items:stretch}#v-etf .inclist{width:auto;max-width:none;resize:none}#v-etf .cgrid{grid-template-columns:1fr}#v-etf .dnbig{margin:0 auto}}
@media (max-width:640px){#v-etf #cxChart{height:380px}#v-etf .dnbig{width:300px;height:300px}#v-etf .cxctl .cmpin{width:100%}#v-etf .cxctl select{width:100%}}
/* ---- v5（18:50 回饋）：組合三等分、月曆一季一排、複利左圖右表、單檔直條＋膠囊 */
#v-etf .c3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;align-items:start;margin-bottom:12px}
#v-etf .c3c{min-width:0}
#v-etf .c3 .dnbig{width:100%;max-width:340px;height:320px;margin:0 auto}
#v-etf .c3h{display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap}
#v-etf .c3h .seg button{padding:2px 10px;font-size:12px}
#v-etf .mgrid.q4{grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
#v-etf .mgrid.q4 .mqh{text-align:center;font:600 12px var(--mono);color:var(--ink-2)}
#v-etf .inctabrow{display:flex;align-items:flex-end;justify-content:space-between;gap:8px 12px;flex-wrap:wrap;margin:4px 0 0}
#v-etf .inctabrow .inctabs{margin:0;min-width:0;flex:1 1 auto}
#v-etf .inctabs button small{margin-left:6px;font:11.5px var(--mono);opacity:.8}
#v-etf .csortw{display:inline-flex;align-items:center;gap:4px;font-size:13px;color:var(--ink-2);flex-wrap:wrap}
#v-etf .csortw.dim{opacity:.55}
#v-etf .mgrid.q4 .mcell{padding:8px 4px}
#v-etf .mgrid.q4 .mcell b{font-size:14px;line-height:20px}
#v-etf .cml{display:flex;flex-direction:column;gap:8px}
#v-etf .cmr{border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--panel)}
#v-etf .cmr .cmn{display:inline-flex;align-items:center;gap:6px;background:none;border:0;padding:0;color:var(--ink);font:600 13px inherit;cursor:pointer;text-align:left;margin-right:6px}
#v-etf .cmr .cmn i{width:10px;height:10px;border-radius:2px;flex:none}
#v-etf .cmr .cmn:hover{text-decoration:underline}
#v-etf .cmr dl{display:grid;grid-template-columns:auto 1fr auto 1fr;gap:2px 8px;margin:6px 0 0;font-size:12.5px}
#v-etf .cmr dt{color:var(--ink-3)}
#v-etf .cmr dd{margin:0;font-family:var(--mono);color:var(--ink);text-align:right}
#v-etf #incChips{margin:0 0 6px}
#v-etf #incChips .addk{cursor:pointer;color:var(--cat-1,var(--ink))}
#v-etf .cxg{display:grid;grid-template-columns:minmax(0,2fr) minmax(300px,1fr);gap:16px;align-items:start}
#v-etf .cxl,#v-etf .cxr{min-width:0}
/* v8（Andy：「複利試算表 清單下方很多空白處」）：右欄跟左圖等高——表格撐滿、列高與字級加大，結論句移到表下面 */
#v-etf .cxg{align-items:stretch}
#v-etf .cxr{display:flex;flex-direction:column;gap:8px}
#v-etf .cxr .simtw{flex:1 1 auto;display:flex}
#v-etf .cxr table.simt{height:100%;font-size:13.5px}
#v-etf .cxr table.simt td,#v-etf .cxr table.simt th{padding:8px 8px}
#v-etf .cxr .cxhead{min-height:0;margin:0;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel-2)}
@media (max-width:900px){#v-etf .cxr table.simt{height:auto}}
#v-etf .cxlg{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin-bottom:4px}
#v-etf .cxlg small{color:var(--ink-3);font-size:12px}
#v-etf .cxlg .cmpw{display:flex;gap:4px;align-items:center}
#v-etf .cxlg .cmpin{width:220px;max-width:100%;height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font-size:12.5px;box-sizing:border-box}
#v-etf .cxlg .chip{border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);border-radius:999px;padding:1px 8px;font-size:12px;cursor:pointer}
#v-etf .cxlg .rxmsg{color:var(--amber);font-size:12px}
#v-etf .cxlg .rxmsg:empty{display:none}
#v-etf .cxr table.simt td,#v-etf .cxr table.simt th{padding:6px 4px}
@media (max-width:1100px){#v-etf .c3{grid-template-columns:1fr}#v-etf .cxg{grid-template-columns:1fr}}
@media (max-width:640px){#v-etf .cxlg .cmpw{flex:1 1 100%}#v-etf .cxlg .cmpin{flex:1}}
@media (max-width:1100px){#v-etf .incsg{grid-template-columns:1fr}#v-etf .inclist{max-height:320px}
  #v-etf .combo .cbody{grid-template-columns:240px minmax(0,1fr)}#v-etf .combo .cbody .mem{grid-column:1/-1}}
@media (max-width:640px){#v-etf #incSort,#v-etf #incCSort,#v-etf #incCView{max-width:100%;overflow-x:auto}#v-etf .detg{grid-template-columns:1fr}#v-etf .combo .cbody,#v-etf .combo .cbody.noclk{grid-template-columns:1fr}
  #v-etf .combo .cbody .clkw,#v-etf .combo .cbody .cdnw{max-width:260px;width:100%;margin:0 auto}#v-etf .incsim .simch{height:240px}
  #v-etf .incrx input{width:100%}}
@media (max-width:640px){#v-etf .mgrid{grid-template-columns:repeat(6,minmax(0,1fr))}#v-etf #incBar{height:300px}
  #v-etf .incctl{gap:8px}#v-etf .etfcatbar .etfinctab{margin-left:0}#v-etf #etfInc .row.spread{flex-wrap:wrap}}
@media (max-width:1100px){#v-etf .etftri{grid-template-columns:1fr}#v-etf .calwrap,#v-etf .retcharts{grid-template-columns:1fr}
  #v-etf .callist{height:320px}#v-etf .etfcatbar{flex-wrap:wrap}#v-etf .etfcatbar .seg{overflow-x:auto;max-width:100%}
  #v-etf .row.spread{flex-wrap:wrap}#v-etf #etfRetCtl{flex-wrap:wrap;white-space:normal;row-gap:6px}#v-etf .cmpmsg:empty{display:none}}
/* 2026-10-06 手機 390 擋路修正（最小改動，不是整套 ETF 手機版）：改前「自訂」日期框兩格橫排（136px×2）＋分頁鈕
   把整頁撐到 608px，底部導覽跟著被推出畫面、點不到。改成：期間那一組自己換行、日期框縮成一欄（上下兩格、各佔滿寬）、
   沒選「自訂」時日期框不佔位；報酬比較表留在它自己的橫向捲動容器（.rettw）裡捲，整頁不跟著變寬；「含息／不含息」那一列可換行。 */
@media (max-width:640px){
  #v-etf .etfrow{flex-wrap:wrap;white-space:normal;min-width:0;max-width:100%}
  #v-etf .etfrow .sp{display:none}
  #v-etf .etfcatbar{flex-wrap:wrap}
  #v-etf .etfper{flex:1 1 100%;flex-wrap:wrap;min-width:0;max-width:100%}
  #v-etf .cust{display:flex;flex-direction:column;align-items:stretch;flex:1 1 100%;min-width:0;gap:4px;white-space:normal}
  #v-etf .cust.inv{display:none}
  #v-etf .cust input{width:100%;box-sizing:border-box}
  #v-etf .rettw{max-width:100%;-webkit-overflow-scrolling:touch}   /* 報酬比較表（820px 寬）本來就包在 .rettw（overflow-x:auto）裡，這裡只保證容器不比畫面寬 */
  #v-etf .card,#v-etf .etfbody{min-width:0;max-width:100%}
  /* 合併 main 後月曆（≤1100 是 1fr，吃內容最小寬）又把頁撐到 507px：改 minmax(0,1fr)，月曆標題列的狀態字可省略 */
  #v-etf .calwrap{grid-template-columns:minmax(0,1fr)}
  #v-etf .calwrap>*{min-width:0}
  #v-etf .calhd{min-width:0}
  #v-etf .calhd .note1{min-width:0}
}
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
      fixSplits(S.series);
      return S.series;
    });
    return seriesP;
  }
  /* ★ 分割／合併還原（v6）：etf_series.json 的週線價格與含息指數都沒還原分割（例：00631L 2026-04-08 一拆 22，443.15→22.93），
     直接拿來算「再投入」會把分割當成暴跌，報酬整段算錯（再投入 00631L 反而輸給只領現金）。
     預覽站讀的是正式站資料，所以先在前端讀進來的唯一入口修：單週漲跌超過 60%、而且含息指數跟價格同比例跳（＝那週不是除息）
     就視為分割／合併，把那週之前的價格與含息指數乘上同一比例。比例取最接近的整數拆分比（差 15% 以內），否則用原始比例。
     單檔年化（seriesOf）、複利試算（alignEtf）都吃同一份 S.series，所以一起被修到。
     TODO：之後在 pipeline 產出 etf_series 那一端（build_payload）就還原分割，前端這段改成只做保險。 */
  function fixSplits(g) {
    Object.keys(g.s || {}).forEach((c) => {
      const x = g.s[c], p = x.p, t = x.t; if (!p) return;
      for (let k = 1; k < p.length; k++) {
        if (!(p[k] > 0 && p[k - 1] > 0)) continue;
        const r = p[k] / p[k - 1]; if (r > 0.4 && r < 1.6) continue;
        if (t && t[k] > 0 && t[k - 1] > 0 && Math.abs((t[k] / t[k - 1]) / r - 1) > 0.05) continue;   // 含息跟價格不同步＝有除息，不是分割
        const n = r < 1 ? Math.round(1 / r) : Math.round(r), f0 = r < 1 ? 1 / n : n;
        const f = n >= 2 && Math.abs(r / f0 - 1) < 0.15 ? f0 : r;
        for (let j = 0; j < k; j++) { if (p[j] != null) p[j] *= f; if (t && t[j] != null) t[j] *= f; }
      }
    });
  }
  function seriesOf(code) {
    const g = S.series;
    if (g && g.s && g.s[code]) { const x = g.s[code]; return { d: g.D.slice(x.i), p: x.p, t: x.t }; }
    return ((S.data && S.data.series) || {})[code] || null;
  }
  const items = () => (S.data && S.data.items) || [];
  /* 2026-10-06（Andy：「無配息就純算報酬率」）：已確認不配息的（槓桿反向／期貨／累積型，或查過配息資料確定 0 筆）含息＝不含息 */
  const NODIV_RE = /期貨|累積|正2|反1|正二|反一/;
  /* 10-06 晚：再加 div_none（pipeline：FinMind 配息資料集對這檔明確回空、湖裡 0 列）—— 期貨型「其他」就是靠這條判成不配息 */
  const noDiv = (it) => !!it && (it.cat === '槓桿反向' || !!it.div_none || NODIV_RE.test(it.name || '') || (!!it.div_done && !it.freq_n && !(it.div_ttm > 0)));
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
  const SUBS = [['cal', '配息行事曆'], ['list', 'ETF 總覽'], ['inc', '現金流試算']], VIEW_OF = { cal: 'cal', list: 'cat', inc: 'inc' };
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
    /* v8（Andy：「ETF 分成三個子分頁：配息行事曆／ETF 總覽／現金流試算」）：最上層三個子分頁，hash＝#etf/cal、#etf/list、#etf/inc。
       切換只是顯示／隱藏，S 的狀態（分類、比較清單、試算目標）都留著。#etf 不帶子頁＝ETF 總覽（原本的主畫面，舊連結不變）。 */
    root.innerHTML = `
<div class="nbsw etfsub" id="etfSub" role="tablist" aria-label="ETF 子分頁">${SUBS.map(([v, t]) => `<button type="button" role="tab" data-v="${v}">${t}</button>`).join('')}</div>
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
  <div class="nbsw etfcats" id="etfCatSeg" role="tablist" aria-label="ETF 分類"></div>
<span class="sp"></span>
</div>
<div class="etfbody" id="etfBody">
<div id="etfInc" hidden></div>

<div class="etftri" id="etfTri" hidden>
  <div class="card" id="etfPopCard">
    <div class="row spread"><h3 data-icon="flame" data-tone="heat">最近最受歡迎前 5 ${hbtn('etfpop', '最受歡迎怎麼算')}</h3></div>
    ${how('etfpop', '', [
      '<b>受益人週增</b>：集保結算所每週公布的受益人數（合計列），最新一週減前一週，增加最多的前 5 檔。代表「新進場的人」。',
      '<b>成交值</b>：最近 20 個交易日成交金額的平均。代表「交易熱度」。',
      '只在目前這個分類裡排；所以：兩個口徑都在前面的，是人潮與交易都熱的。'])}
    <div class="etfqrow"><p class="etfq" id="etfPopSub"></p>
      <div class="seg etfqseg" id="etfPopSeg"><button data-v="holders">受益人</button><button data-v="turnover">成交值</button></div></div>
    <div class="rklist" id="etfPop"></div>
  </div>
  <div class="card" id="etfRetTopCard">
    <div class="row spread"><h3 data-icon="arrow-up" data-tone="up">報酬率前 5 <small id="etfRetTopSub"></small> ${hbtn('etfrettop', '報酬率前 5 怎麼排')}</h3></div>
    ${how('etfrettop', '', [
      '依<b>含息總報酬年化</b>由高到低排（配息在除息日以當天收盤再投入）。期間跟著下方「報酬比較」標題列的期間（近 1／3／5／10 年、上市以來、起始日期～至今）。',
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
    <p class="etfq" id="etfYldQ">依<b>近 12 個月現金配息 ÷ 最新收盤</b>排</p>
    <div class="rklist" id="etfYld"></div>
  </div>
</div>

<div class="card" id="etfRetCard">
  <div class="row spread"><h3 data-icon="line" data-tone="tech">報酬比較 <small id="etfRetSub"></small> ${hbtn('etfret', '報酬比較的口徑')}</h3>
    <div class="etfrow" id="etfRetCtl">
      <span id="etfRngBox"></span>
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
  ${how('etfret', '', retHowLines(true))}
  <div id="etfRetBody"></div>
</div>

<div class="card" id="etfListCard">
  <div class="row spread"><h3 data-icon="table" data-tone="chip">ETF 一覽 <small id="etfCount"></small> ${hbtn('etflist', 'ETF 分類與欄位')}</h3>
    <div class="etfrow"><label class="note" for="etfSort">排序</label>
      <select id="etfSort" class="etsel"><option value="tv">成交值</option><option value="size">規模</option><option value="yield">殖利率</option><option value="chg">今日漲跌</option></select></div></div>
  ${how('etflist', '', [
    '<b>分類</b>（依序判斷，先符合先歸類）：槓桿反向（代號尾 L/R 或名稱含 正2／反1）→ 債券型（尾 B 或名稱含「債」）→ 其他（期貨／商品／貨幣，尾 U 或「期」開頭）→ 主動式（尾 A）→ 市值型（名稱含 台灣50、台50、中型100、加權、MSCI台灣、摩台）→ 配息型（名稱含 高股息／高息／股息／收益／優息…，或近 400 天除息 ≥ 4 次）→ 其餘股票型為主題型。',
    '<b>殖利率</b>＝近 12 個月現金配息合計 ÷ 最新收盤。<b>配息頻率</b>（分類旁的彩色小徽章）＝近 400 天相鄰兩次除息的間隔中位數（約 1 個月＝月配、2 個月＝雙月配、3 個月＝季配、半年＝半年配、只有 1 次＝年配）；沒有配息的不標。',
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
    const catOn = S.view === 'cat';
    $$('button', seg).forEach((b) => { const on = catOn && b.dataset.v === S.cat; b.classList.toggle('on', on); b.setAttribute('aria-selected', on);
      b.onclick = () => { if (catOn && S.cat === b.dataset.v) return; S.view = 'cat'; S.cat = b.dataset.v; S.shown = PAGE; if (/^#etf\/(cal|inc)/.test(location.hash)) history.replaceState(null, '', '#etf/list'); drawAll(); }; });
    $$('#etfSub button').forEach((b) => { const v = VIEW_OF[b.dataset.v], on = v === S.view; b.classList.toggle('on', on); b.setAttribute('aria-selected', on);
      b.onclick = () => { const h = '#etf/' + b.dataset.v; if (location.hash !== h) location.hash = h; else show(b.dataset.v); }; });
  }
  /* ---- 期間（2026-10-06 Andy：「週期切換……可以選擇時段如圖二那樣，切換到不同時間週期也可以在旁邊顯示對應年限日期」）
     從分類列最右邊搬到「報酬比較」標題列（只留一套）；元件是共用的 site/rangepick.js（管理區流量觀測同款）。
     近 3／5／10 年用 etf.json 預先算好的（日線，較精準）；近 1 年／上市以來／起始日期～至今用週線走勢自己算。 */
  const PERS = [['1y', '近 1 年'], ['3y', '近 3 年'], ['5y', '近 5 年'], ['10y', '近 10 年'], ['since', '上市以來'], ['custom', '起始日期～至今']];
  const PRE = { '3y': 1, '5y': 1, '10y': 1 };
  const asofD = () => (S.data && S.data.asof) || todayTW();
  const yrsAgo = (d, n) => { const t = new Date(d + 'T00:00:00Z'); t.setUTCFullYear(t.getUTCFullYear() - n); return t.toISOString().slice(0, 10); };
  /* 這個期間的起訖（給日期框顯示、也給自算用）。上市以來的起點＝目前比較的幾檔裡最早上市那檔的第一筆。 */
  function perRange() {
    // 結束日一律顯示今天（跟管理區同一個規則；資料只到最近交易日，算的時候自然停在那天）
    const to = todayTW();
    if (S.per === 'custom') return { from: S.cfrom, to: S.cto || todayTW() };
    if (PRE[S.per]) return { from: ((S.data && S.data.periods) || {})[S.per] || yrsAgo(to, +S.per.replace('y', '')), to };
    if (S.per === '1y') return { from: yrsAgo(to, 1), to };
    const firsts = (S.cat ? getCmp() : []).map((c) => { const x = seriesOf(c); return x && x.d && x.d[0]; }).filter(Boolean).sort();
    return { from: firsts[0] || '', to };
  }
  function drawPer() {
    if (!S.cfrom) S.cfrom = LS.get('tw.etf.cfrom', '') || yrsAgo(todayTW(), 3);
    if (!S.cto) S.cto = todayTW();   // 結束日預設今天，可改
    const box = $('#etfRngBox'); if (!box || !window.RangePick) return;
    const r = perRange();
    if (!$('#etfRng')) {
      box.innerHTML = window.RangePick.html({ id: 'etfRng', options: PERS, value: S.per, from: r.from, to: r.to, max: todayTW() });
      window.RangePick.bind($('#etfRng'), { onChange: ({ value, from, to, manual }) => {
        S.per = value; LS.set('tw.etf.per', S.per);
        if (value === 'custom') {
          // 手改日期 → 用新起訖；從下拉直接選「起始日期～至今」→ 沿用框裡現在顯示的起訖（使用者看到什麼就算什麼）
          if (from) { S.cfrom = from; LS.set('tw.etf.cfrom', from); }
          S.cto = to || todayTW();
        }
        if (S.view === 'inc') drawInc(); else { drawRetTop(); drawRet(); }
      } });
    }
    window.RangePick.set($('#etfRng'), { value: S.per, from: r.from, to: r.to });
  }
  function perKey() { return PRE[S.per] ? S.per : S.per === 'custom' ? 'C' + S.cfrom + '~' + S.cto : S.per; }
  /* 近 1 年／上市以來／自訂：用週序列自己算（起始日早於上市就從上市第一天算起＝上市以來） */
  function rangeStats(it) {
    const s = seriesOf(it.code);
    if (!s || !s.d || !s.p) return { ok: false, why: S.series ? '無資料' : '走勢載入中' };
    // 上市以來不走 perRange()（它要讀比較清單，比較清單的預設又要靠這裡排名 → 會繞圈）
    const R = S.per === 'since' ? { from: '', to: asofD() } : perRange();
    const from = R.from || '', to = R.to || '9999';
    let i0 = s.d.findIndex((d) => d >= from); if (i0 < 0) return { ok: false, why: '起始日晚於最後一筆資料' };
    let i1 = s.d.length - 1; while (i1 > 0 && s.d[i1] > to) i1--;
    if (i1 - i0 < 2) return { ok: false, why: '這段日期內資料不足' };
    const yrs = (Date.parse(s.d[i1]) - Date.parse(s.d[i0])) / (365.25 * 864e5);
    const ann = (a) => (a && a[i0] && a[i1] ? Math.pow(a[i1] / a[i0], 1 / yrs) - 1 : null);
    const o = { ok: true, since: S.per === 'since' || s.d[0] > from, from: s.d[i0], years: +yrs.toFixed(1), price_ann: ann(s.p), tr_ann: s.t ? ann(s.t) : null, div_ann: null };
    return noDiv(it) && o.tr_ann == null ? { ...o, tr_ann: o.price_ann, nodiv: true } : o;
  }
  const statOf = (it) => (!PRE[S.per] ? rangeStats(it) : effSt(it, ((it.stats || {})[perKey()]) || { ok: false, why: '無資料' }));
  function perLabel() {
    return S.per === 'custom' ? '自訂期間' : (PERS.find((x) => x[0] === S.per) || [0, '近 5 年'])[1];
  }


  /* ---- 2026-10-07 Andy：「每個分頁不同類型 ETF，下方 ETF 也需要按照類型排序，可以參考配息型那分頁」
     非配息型分頁依「子類型」分組。etf.json 只有代號與名稱可用（沒有追蹤指數／資產類別／地區欄位），
     所以一律依「名稱關鍵字＋代號尾碼」判斷；判斷不到的歸「其他」，不准猜。規則與理由見 docs/etf_subgroups.md。
     每條規則依陣列順序比對，先中先贏（例：「非投等」要排在「投等」前面，否則高收益債會被當成投資級）。 */
  const SG_OVS = /上証|上證|滬深|深証|深100|中國|中証|A股|恒生|香港|日本|日經|東證|美國|美股|S&P|標普|NASDAQ|那斯達克|納斯達克|道瓊|北美|歐洲|印度|越南|韓|KOSPI|新興|全球|世界|MAG7|FANG/;
  const SG = {
    市值型: [
      ['台股大型', /台灣50|台50|臺灣50|MSCI台灣|摩台|加權|領袖50/],
      ['中小型', /中型100|中小|富櫃/],
      ['海外市場', SG_OVS],
    ],
    主題型: [
      ['半導體', /半導體|晶圓|PCB/],
      ['AI 與科技', /AI|科技|電子|5G|通訊|網路|資安|元宇宙|算力|數據|機器人|太空|航太|FANG|MAG7|研發/],
      ['ESG 永續', /ESG|永續|低碳|淨零|公司治理/],
      ['電動車與綠能', /電動車|未來車|智能車|電池|儲能|潔淨能源|綠色電力|電力/],
      ['金融', /金融/],
      ['高股息主題', /高股息|高息|股息/],
      ['產業其他', /生技|基因|稀土|商社|品牌|支付|不動產|防衛|資源/],
      ['海外主題', SG_OVS],
    ],
    主動式: [
      // 代號尾碼 A＝股票型主動；D 而且名稱寫明債／投等／非投＝債券型；D 但寫「入息」「收益」的是多重資產，歸其他
      ['債券型主動', (it) => /D$/.test(it.code) && /債|投等|非投/.test(it.name)],
      ['股票型主動', (it) => /A$/.test(it.code)],
    ],
    債券型: [
      ['高收益債', /非投|高收益/],
      ['新興市場債', /新興|EM|亞洲/],
      ['美國公債・長天期', (it) => SG_UST(it.name) && /20|25|超長/.test(it.name)],
      ['美國公債・中天期', (it) => SG_UST(it.name) && /7-10|10年/.test(it.name)],
      ['美國公債・短天期', (it) => SG_UST(it.name) && /1-3|0-1|短期/.test(it.name)],
      ['投資等級公司債', /投資級|投等|IG|A級|AAA|AA|BBB|A3|Aa|A公司債|A債|高評級/],
    ],
    槓桿反向: [],   // 下面用 levSub() 組出「方向・標的」
    其他: [
      ['商品', /黃金|白銀|銅|石油|原油|黃豆|小麥/],
      ['REITs', /REIT|不動產/],
    ],
  };
  // 美國公債：名稱寫美債／美公債／美國公債／US 短期公債，而且沒有寫評等或公司債（那些是美元計價公司債，不是公債）
  function SG_UST(n) { return /美債|美公債|美國公債|US短期公債/.test(n) && !/投等|投資級|IG|A債|Aa|A-|公司|優息/.test(n); }
  const LEV_DIR = [['正 2 槓桿', /正2/], ['反 1', /反1/], ['反向其他', /反向/]];
  const LEV_UND = [['台股', /台灣50|臺灣加權|台灣加權/], ['美股', /S&P500|NASDAQ|道瓊/], ['陸港股', /上証|滬深|中國|香港|恒生/],
    ['其他海外股', /日本|印度/], ['美債', /美債/], ['商品', /黃金|原油|布蘭特/], ['匯率', /美元|日圓/]];
  function levSub(n) {
    const d = LEV_DIR.find((r) => r[1].test(n)), u = LEV_UND.find((r) => r[1].test(n));
    return d ? d[0] + '・' + (u ? u[0] : '其他') : '其他';
  }
  // 組順序：照上面規則的順序；槓桿反向是「方向 × 標的」的笛卡兒積；「其他」永遠最後
  function sgOrder(cat) {
    if (cat === '槓桿反向') { const o = []; LEV_DIR.forEach((d) => { LEV_UND.forEach((u) => o.push(d[0] + '・' + u[0])); o.push(d[0] + '・其他'); }); return o.concat('其他'); }
    return (SG[cat] || []).map((r) => r[0]).concat('其他');
  }
  function subOf(it) {
    if (it.cat === '槓桿反向') return levSub(it.name || '');
    const r = (SG[it.cat] || []).find(([, t]) => (typeof t === 'function' ? t(it) : t.test(it.name || '')));
    return r ? r[0] : '其他';
  }
  /* 卡片不加子類型文字標籤：名稱列已經有「分類＋配息頻率」兩個徽章，再加第三個會把 ETF 名稱擠成「富…」（實測 1440 寬）。
     改用卡片左色條＝組色（跟配息型的頻率左色條同一套 .fqbar），完整組名寫在組標題上。 */

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
    /* 2026-10-07 Andy：「月 雙月 季配 標註在配息型旁邊」「把配息頻率那欄位拿掉」「沒有配息或沒有殖利率就不用特別寫出來」
       → 頻率改成右上分類徽章旁的彩色小徽章；沒有殖利率（空／0）的不放頻率、殖利率那列留白佔位（同排卡片等高）。 */
    const hasY = it.yield_ttm != null && it.yield_ttm > 0;
    const fk = hasY ? FQK[it.freq] || '' : '';
    return `<button type="button" class="etfc t-${CAT_TONE[it.cat] || 'ink3'}${fk && it.cat === '配息型' ? ` fqbar fqc-${fk}` : ''}${it._sg ? ` fqbar sgbar sgc-${it._sgi % 8}` : ''}"${it._sg ? ` data-sg="${esc(it._sg)}"` : ''} data-fq="${esc(it.freq || '')}" data-code="${esc(it.code)}" title="進 ${esc(it.name)} 個股頁">
  <div class="h"><span class="nm">${esc(it.name)}</span><span class="cd">${esc(it.code)}</span><span class="sp" style="flex:1"></span>
    <span class="etag ${CAT_TONE[it.cat] || 'ink3'}">${esc(it.cat)}</span>${hasY && fk ? `<span class="fq fqtag fqc-${fk}">${esc(it.freq)}</span>` : ''}</div>
  <div class="px"><b class="${cls(it.chg_pct)}" data-live="close" data-code="${esc(it.code)}">${it.close != null ? A().fmt.n(it.close, 2) : '—'}</b>
    <span class="${cls(it.chg_pct)}" data-live="chg" data-code="${esc(it.code)}">${it.chg_pct != null ? A().fmt.pct(it.chg_pct, 2) : '—'}</span>
    <span class="sp"></span>${spark(it.code)}</div>
  <dl><dt>成交值${it.tv20 != null ? '（20日均）' : ''}</dt><dd>${yi(it.tv20 != null ? it.tv20 : it.tv)}</dd>
      ${hasY ? `<dt>殖利率</dt><dd class="yv">${y}</dd>` : '<dt class="blank" aria-hidden="true">&nbsp;</dt><dd class="blank" aria-hidden="true">&nbsp;</dd>'}<dt>規模（估）</dt><dd>${yi(it.size)}</dd></dl>
</button>`;
  }
  function drawList() {
    let list = items().filter((it) => it.cat === S.cat).sort((a, b) => sortVal(b) - sortVal(a));
    $('#etfCount').textContent = `${S.cat} ${list.length} 檔`;
    const g = $('#etfGrid');
    /* 2026-10-07 Andy：「配息型這邊幫我用月配 雙月配 季配 半年配等等為組合排序」——只在配息型分組；組內維持原本排序 */
    const grp = S.cat === '配息型';
    if (grp) list = list.map((it, i) => ({ it, i })).sort((a, b) => fqRank(a.it.freq) - fqRank(b.it.freq) || a.i - b.i).map((x) => x.it);
    const shown = list.slice(0, S.shown);
    if (grp) {
      const cnt = {}; list.forEach((it) => { const k = fqName(it.freq); cnt[k] = (cnt[k] || 0) + 1; });
      let html = '', cur = null;
      shown.forEach((it) => { const k = fqName(it.freq); if (k !== cur) { cur = k;
        html += `<div class="fqhd${FQK[k] ? ' fqc-' + FQK[k] : ''}" data-fq="${esc(k)}">${FQK[k] ? '<i></i>' : ''}${esc(k)}<small>${cnt[k]} 檔</small></div>`; }
        html += cardHTML(it); });
      g.innerHTML = html || '<div class="etfprep">無資料</div>';
    } else {
      /* 子類型分組（2026-10-07）：做法同配息型——組順序照 sgOrder()、組內維持原排序、小標題寫全組檔數（不是已顯示的檔數） */
      const ord = sgOrder(S.cat), rk = (k) => { const i = ord.indexOf(k); return i < 0 ? ord.length : i; };
      list = list.map((it, i) => ({ it, i, k: subOf(it) })).sort((a, b) => rk(a.k) - rk(b.k) || a.i - b.i)
        .map((x) => Object.assign({}, x.it, { _sg: x.k, _sgi: rk(x.k) }));
      const cnt = {}; list.forEach((it) => { cnt[it._sg] = (cnt[it._sg] || 0) + 1; });
      let html = '', cur = null;
      list.slice(0, S.shown).forEach((it) => { if (it._sg !== cur) { cur = it._sg;
        html += `<div class="fqhd sghd sgc-${it._sgi % 8}" data-sg="${esc(cur)}"><i></i>${esc(cur)}<small>${cnt[cur]} 檔</small></div>`; }
        html += cardHTML(it); });
      g.innerHTML = html || '<div class="etfprep">無資料</div>';
      g.dataset.sgcnt = JSON.stringify(cnt);
    }
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
    const on = new Set(sel);
    const all = inCat().slice().sort((a, b) => sizeKey(b) - sizeKey(a));
    const val = (it) => { const st = statOf(it); if (!st || !st.ok) return '—';
      return st.tr_ann != null ? pct(st.tr_ann, 1) : pct(st.price_ann, 1); };
    ms.sync({
      rows: all.map((it) => ({ name: `${it.code} ${it.name}`, on: on.has(it.code), color: on.has(it.code) ? colorOf[it.code] : A().hexA(A().CH.ink3, 0.45),
        val: val(it), valTitle: `${perLabel()} 年化報酬率（有配息的含息）` })),
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
  /* 2026-10-06（Andy：「槓桿沒有配息 圖表就拿掉含息以及不含息」「只留下報酬率」「也不需要下方備註 殖利率 配息年化多少」）
     「這一檔在這段期間有沒有配息」依資料判斷、不寫死分類：含息年化與價格年化差 ≥ 0.01 個百分點才算有。
     （確定不配息的 —— 槓桿反向、或上游配息資料明確回空的 div_none —— 含息年化已設成等於價格年化，這裡自然判成沒有。）
     沒有 → 只畫一條「年化報酬率」、不寫殖利率／配息年化；全部都沒有 → 圖例、含息／不含息切換、殖利率欄整個拿掉。 */
  const hasDiv = (st) => !!(st && st.ok && st.tr_ann != null && st.price_ann != null && Math.abs(st.tr_ann - st.price_ann) >= 1e-4);
  function retHowLines(anyDiv) {
    const L = ['用右上「加入比較」挑這個分類裡的 ETF（可搜尋、最多 8 檔）；沒挑過時預設是「報酬率前 5」。每個分類各自記住你挑的。',
      '<b>期間</b>：標題列的下拉選近 1／3／5／10 年或上市以來，旁邊兩個日期框同步顯示這段的起訖；直接改日期就變成「起始日期～至今」。'
      + '<b>上市未滿</b>的改用上市以來計算並標「上市以來 N 年」，不和滿期的直接比較。'];
    if (!anyDiv) {
      L.push('<b>年化報酬率</b>＝(期末收盤 ÷ 期初收盤)^(1/年數) − 1；分割已還原。這一組 ETF 在這段期間都沒有配息，報酬就只有價格這一種，不分含息、不含息。');
      L.push('所以：左圖看一路走勢（同起點 = 0%），右圖直接比年化數字。槓桿反向 ETF 每天重設倍數，放得越久越會偏離「指數 × 倍數」，長期年化只能當參考。');
      return L;
    }
    L.push('<b>價格年化（不含息）</b>＝(期末收盤 ÷ 期初收盤)^(1/年數) − 1；分割（例：0050 2025-06 一拆四）已還原，配息不算進去。');
    L.push('<b>含息年化</b>＝配息在除息日以當天收盤再投入（還原權值）後的年化報酬。<b>殖利率</b>＝近 12 個月現金配息 ÷ 最新收盤。<b>配息年化</b>＝(1 ＋ 期間累計配息 ÷ 期初收盤)^(1/年數) − 1。');
    L.push('這段期間<b>沒有配息</b>的 ETF 只畫一條報酬率、名字旁標「無配息」，殖利率與配息欄不寫數字。');
    L.push('所以：左圖看一路走勢（同起點 = 0%），右圖直接比年化數字；含息與不含息差距越大，代表報酬越依賴配息。');
    return L;
  }
  /* 這一檔畫不畫得出走勢（有週線、期間內有起點） */
  const lineable = (it, st) => { if (!st || !st.ok) return false; const s = seriesOf(it.code); return !!(s && s.d && s.p && s.d.some((d) => d >= st.from)); };
  /* 走勢一條都畫不出來時的白話原因（不寫「無資料」了事） */
  /* 表格裡「這段期間算不出來」的原因：白話、不寫內部口徑（回補／資料湖 —— 樣式指南禁止） */
  const whyTxt = (w) => (!w ? '這段期間沒有資料' : /尚未回補/.test(w) ? '歷史股價未補齊' : w);
  function whyNone(rows) {
    const w = rows.map(({ st }) => (st && st.why) || '').filter(Boolean);
    if (!S.series) return '走勢載入中…';
    if (w.some((x) => /尚未回補/.test(x))) return '這幾檔的歷史股價還沒補進資料庫（每小時自動接力補），補到後這裡會自動畫出走勢';
    if (w.some((x) => /上市未滿|資料不足|晚於/.test(x))) return '這幾檔在這段期間內的交易資料不足（上市太晚或日期區間太短），請把期間拉長或改選上市以來';
    return '這幾檔在這段期間沒有可畫的走勢資料';
  }
  function drawRet() {
    const card = $('#etfRetCard'), body = $('#etfRetBody');
    card.hidden = false;
    $$('#etfBasisSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.basis);
      b.onclick = () => { S.basis = b.dataset.v; LS.set('tw.etf.basis', S.basis); drawRet(); }; });
    $('#etfRetSub').textContent = S.cat;   // 期間改由標題列的下拉＋日期框表示，副標不再重複寫「近 5 年」
    drawPer();
    if (S.fallback) {
      body.innerHTML = '<div class="etfprep">尚無資料</div>';
      body.dataset.k = ''; body.dataset.codes = ''; syncDD([], {}); return;
    }
    let sel = getCmp(), auto = false;
    const m = byCode(), pk = perKey();
    const rowsOf = (codes) => codes.map((c) => { const it = m.get(c) || { code: c, name: c, stats: {} }; return { it, st: statOf(it) }; });
    let rows = rowsOf(sel);
    // 選中的全部畫不出走勢（例：回補還沒補到、期間太短）→ 自動改看這一類「畫得出來」的前 5 檔，不讓整塊空白（不寫回使用者的選擇）
    if (S.series && sel.length && !rows.some(({ it, st }) => lineable(it, st))) {
      const alt = retRank().rows.filter(({ it, st }) => lineable(it, st)).slice(0, 5).map(({ it }) => it.code);
      if (alt.length) { sel = alt; rows = rowsOf(sel); auto = true; }
    }
    const PC = PALC(), colorOf = {}; sel.forEach((c, i) => { colorOf[c] = PC[i % PC.length]; });
    syncDD(sel, colorOf);
    if (!sel.length) {
      body.innerHTML = '<div class="etfprep">尚未選擇 ETF</div>';
      body.dataset.k = pk; body.dataset.codes = ''; return;
    }
    const okRows = rows.filter(({ st }) => st.ok);
    const anyDiv = okRows.some(({ st }) => hasDiv(st)), allNo = !anyDiv;
    const seg = $('#etfBasisSeg'); if (seg) seg.style.display = allNo ? 'none' : '';
    const hw = $('#how-etfret'); if (hw && A().howHTML) hw.innerHTML = A().howHTML('', retHowLines(anyDiv));
    const num = (v, f) => (v == null ? '<span class="na">—</span>' : f(v));
    const NODIV = '<span class="na">無配息</span>';
    const perCell = (st) => (st.since ? `<span title="上市以來：不和滿期的直接比較">${esc(st.from)}～ <span class="note">上市以來 ${st.years} 年</span></span>` : `${st.from}～ <span class="note">${st.years} 年</span>`);
    const nameCell = (it) => `<td class="nmc"><span class="nmw"><i style="background:${colorOf[it.code]}"></i><span class="nmt" title="${esc(it.name)} ${esc(it.code)}">${esc(it.name)}</span><span class="note">${esc(it.code)}</span></span></td>`;
    const lineTtl = allNo ? '累積報酬率（期初 = 0%）' : `累積報酬走勢（${S.basis === 'tr' ? '含息總報酬' : '價格，不含息'}；期初 = 0%）`;
    const barTtl = allNo ? '年化報酬率' : '年化報酬率（不含息 vs 含息）';
    const tbl = allNo
      ? `<table class="et fullw" id="etfRetTbl"><colgroup><col style="width:40%"><col style="width:35%"><col style="width:25%"></colgroup>
      <thead><tr><th class="nmc">ETF</th><th>期間</th><th>年化報酬率</th></tr></thead><tbody>
      ${rows.map(({ it, st }) => `<tr data-code="${esc(it.code)}">${nameCell(it)}${st.ok ? `<td>${perCell(st)}</td><td class="${cls(st.price_ann)}">${num(st.price_ann, (v) => pct(v, 2))}</td>` : `<td colspan="2"><span class="na">${esc(whyTxt(st.why))}</span></td>`}</tr>`).join('')}</tbody></table>`
      : `<table class="et fullw" id="etfRetTbl"><colgroup><col style="width:27%"><col style="width:21%"><col style="width:13%"><col style="width:13%"><col style="width:13%"><col style="width:13%"></colgroup>
      <thead><tr><th class="nmc">ETF</th><th>期間</th><th>價格年化（不含息）</th><th>含息年化</th><th>殖利率（近 12 月）</th><th>配息年化</th></tr></thead><tbody>
      ${rows.map(({ it, st }) => { const dv = hasDiv(st); return `<tr data-code="${esc(it.code)}"${dv ? '' : ' data-nodiv="1"'}>${nameCell(it)}
        ${st.ok ? `<td>${perCell(st)}</td><td class="${cls(st.price_ann)}">${num(st.price_ann, (v) => pct(v, 2))}</td>
        <td class="${dv ? cls(st.tr_ann) : ''}">${dv ? pct(st.tr_ann, 2) : NODIV}</td>`
        : `<td colspan="3"><span class="na">${esc(whyTxt(st.why))}</span></td>`}
        <td>${dv && it.yield_ttm != null ? pctU(it.yield_ttm) : dv ? '<span class="na">—</span>' : NODIV}</td><td>${dv ? num(st.div_ann, (v) => pctU(v)) : NODIV}</td></tr>`; }).join('')}</tbody></table>`;
    body.innerHTML = `${auto ? '<p class="note" id="etfRetAuto">原本選的幾檔這段期間畫不出走勢，先改看這一類畫得出來的前 5 檔。</p>' : ''}<div class="retcharts"><div><div class="note note1" id="etfRetLineTtl">${lineTtl}</div><div id="etfRetLine" class="chart"></div></div>
      <div><div class="note note1" id="etfRetBarTtl">${barTtl}</div><div id="etfRetBar" class="chart"></div></div></div>
      <div class="rettw">${tbl}</div>`;
    body.dataset.k = pk + '|' + S.cat + '|' + S.basis; body.dataset.codes = sel.join(',');
    body.dataset.div = allNo ? 'none' : okRows.every(({ st }) => hasDiv(st)) ? 'all' : 'mixed';
    body.dataset.auto = auto ? '1' : '';
    $$('tr[data-code]', body).forEach((tr) => { tr.onclick = () => A().goStock(tr.dataset.code); });
    drawRetCharts(rows, colorOf, allNo);
    if (!S.series) loadSeries().then(() => { if (!$('#etfRetCard').hidden) drawRet(); });
  }
  function drawRetCharts(rows, colorOf, allNo) {
    const a = A(), CH = a.CH;
    const lines = [];
    rows.forEach(({ it, st }) => {
      const s = seriesOf(it.code); if (!s || !st.ok) return;
      const dv = hasDiv(st);
      // 有配息且選「含息」→ 含息總報酬；其餘一律價格（沒配息的含息＝價格，不分兩種）
      const vals = dv && S.basis === 'tr' && s.t ? s.t : s.p; if (!vals) return;
      const i0 = s.d.findIndex((d) => d >= st.from); if (i0 < 0) return;
      const base = vals[i0]; if (!base) return;
      const col = colorOf[it.code];
      lines.push({ name: `${it.name} ${it.code}${!allNo && !dv ? '・無配息' : ''}${st.since && S.per !== 'since' ? `（自 ${st.from.slice(0, 7)} 上市）` : ''}`, type: 'line', showSymbol: false, smooth: false, lineStyle: { width: 1.8, color: col }, emphasis: { focus: 'series' }, itemStyle: { color: col },
        data: s.d.slice(i0).map((d, j) => [d, +((vals[i0 + j] / base - 1) * 100).toFixed(2)]) });
    });
    const lineEl = $('#etfRetLine'); if (!lineEl) return;
    const yrsSpan = Math.max(...rows.map(({ st }) => (st.ok ? +st.years || 0 : 0)), 0.5);
    const SC = SOFT();
    if (!lines.length) {
      holdEmpty('etfRetLine', whyNone(rows));
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
        series: lines,   // 月份分隔線由全站 TimeGrid（DECISIONS #337）自動補，時間軸不必自己畫
      });
    }
    lineEl.dataset.n = String(lines.length);
    lineEl.dataset.first = lines.length ? lines.map((l) => l.data[0][0]).sort()[0] : '';
    const ok = rows.filter(({ st }) => st.ok);
    const barEl = $('#etfRetBar');
    if (!ok.length) { holdEmpty('etfRetBar', whyNone(rows)); barEl.dataset.n = '0'; barEl.dataset.series = ''; return; }
    const best = (st) => (hasDiv(st) ? st.tr_ann : st.price_ann);
    const sorted = ok.slice().sort((x, y) => best(y.st) - best(x.st));
    const v = (x) => (x == null ? null : +(x * 100).toFixed(2));
    const lab = { show: true, position: 'right', color: CH.ink2, fontSize: 11, formatter: (p) => (p.value == null ? '' : p.value + '%') };
    const series = allNo
      ? [{ name: '年化報酬率', type: 'bar', data: sorted.map(({ st }) => v(st.price_ann)), itemStyle: { color: SC.a, borderRadius: [0, 3, 3, 0] }, barMaxWidth: 12, label: lab }]
      : [{ name: '不含息', type: 'bar', data: sorted.map(({ st }) => v(st.price_ann)), itemStyle: { color: SC.a, borderRadius: [0, 3, 3, 0] }, barMaxWidth: 10, label: lab },
        { name: '含息', type: 'bar', data: sorted.map(({ st }) => (hasDiv(st) ? v(st.tr_ann) : null)), itemStyle: { color: SC.b, borderRadius: [0, 3, 3, 0] }, barMaxWidth: 10, label: lab }];
    const ylab = ({ it, st }) => [it.name, st.since && S.per !== 'since' ? `上市以來 ${st.years} 年` : '', !allNo && !hasDiv(st) ? '無配息' : ''].filter(Boolean).join('\n');
    barEl.innerHTML = '';
    a.chart('etfRetBar', {
      grid: { left: 96, right: 52, top: allNo ? 8 : 30, bottom: 24 }, legend: { show: !allNo, top: 0, textStyle: { color: CH.ink2, fontSize: 12 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (x) => (x == null ? '無配息' : x + '%') },
      xAxis: { type: 'value', ...a.axisStyle, splitLine: { show: true, lineStyle: { color: CH.grid, opacity: 1 } }, axisLabel: { ...a.axisStyle.axisLabel, formatter: (x) => x + '%' } },
      yAxis: { type: 'category', inverse: true, data: sorted.map(ylab), ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, fontSize: 12, width: 86, overflow: 'truncate' } },
      series,
    });
    barEl.dataset.n = String(ok.length);
    barEl.dataset.series = series.map((x) => x.name).join(',');
  }

  /* ------------------------------------------------------------------ 5. 現金流試算（2026-10-07）
     Andy：「專門算持有這檔 ETF 配息下來的錢，需要多少張才能配息達到一年 100W……也需要前五名的 ETF 組合搭配，
     有些是季配息，4 檔搭配也能滿足每個月配息……目的為了讓退休沒工作的人需要現金流」。
     放成分類列右邊一顆獨立頁籤（不塞進 #etfCatSeg）：它是「工具」不是「分類」——不篩卡片、不出前 5，
     而且分類頁籤的順序與數量是既有驗收鎖住的（ETF專區1005／財經日曆1006）。

     口徑（全部只用 etf.json 已有的資料，不編數字）：
     · 每單位配息：配息行事曆（calendar，證交所／櫃買除息紀錄）裡「除息日在近 12 個月內（含已公告未除息）」的現金配息，
       依「發放月」歸到 1～12 月（錢真正入帳的月份；沒有發放日的用除息月）；同一個月有兩筆只留最新那筆（窗口頭尾重疊時不重算）。
     · 張數＝無條件進位(年領目標 ÷ (每單位年配息 × 1000))；勾「扣除二代健保」時，每一次發放金額 ≥ 2 萬元的整筆扣 2.11%，
       張數再往上加到扣完仍達標。投入金額＝張數 × 1000 × 最新收盤。
     · 殖利率＝每單位年配息 ÷ 最新收盤（當下值）；含息總報酬＝上方期間的含息年化（跟報酬比較同一口徑）。
     · 組合：候選池＝範圍內的月配／雙月配／季配、近 20 日均成交值 ≥ 2000 萬（避免冷門）、殖利率前 20 檔；
       窮舉 2～4 檔、只留 12 個月都有配息的組合；每個組合用「缺口最大的月份 → 補這個月最便宜的那檔」貪婪補到每月 ≥ 目標，
       再逐檔把張數往下壓到剛好不破目標（二分搜尋），任何一檔壓到 0 張的組合丟掉（那是更小的組合）。 */
  const FQK = { 月配: 'm', 雙月配: 'b', 季配: 'q', 半年配: 'h', 年配: 'y' };
  const FQ_ORDER = ['月配', '雙月配', '季配', '半年配', '年配'];
  const fqName = (f) => (FQK[f] ? f : '其他');
  const fqRank = (f) => { const i = FQ_ORDER.indexOf(f); return i < 0 ? 99 : i; };
  const fqBadge = (f) => (FQK[f] ? `<span class="fqb fqc-${FQK[f]}">${esc(f)}</span>` : '');
  const NHI = 0.0211, NHI_MIN = 20000;
  const INC_Y = [[200000, '20 萬'], [500000, '50 萬'], [1000000, '100 萬'], [2000000, '200 萬']];
  const INC_M = [[5000, '5000'], [10000, '1 萬'], [20000, '2 萬'], [30000, '3 萬']];
  const wan = (v) => (v == null ? '—' : v >= 1e8 ? (v / 1e8).toFixed(2) + ' 億' : v >= 1e4 ? (v / 1e4).toFixed(v >= 1e6 ? 0 : 1) + ' 萬' : Math.round(v).toLocaleString());
  const netOf = (g) => (S.inc.nhi && g >= NHI_MIN ? g * (1 - NHI) : g);
  /* 每檔 ETF 的「12 個月配息表」：{m: [每單位金額 ×12], sum, n} */
  function incMonths() {
    if (S._incM && S._incM.k === S.data) return S._incM.v;
    const since = yrsAgo(asofD(), 1), out = {};
    ((S.data && S.data.calendar) || []).forEach((e) => {
      if (!e || !(e.amt > 0) || e.ex <= since) return;
      const mo = +String(e.pay || e.ex).slice(5, 7) - 1; if (!(mo >= 0 && mo < 12)) return;
      const o = out[e.code] || (out[e.code] = { m: Array(12).fill(0), ex: Array(12).fill(''), sum: 0, n: 0 });
      if (o.ex[mo] && o.ex[mo] > e.ex) return;
      o.m[mo] = +e.amt; o.ex[mo] = e.ex;
    });
    Object.values(out).forEach((o) => { o.sum = o.m.reduce((a, b) => a + b, 0); o.n = o.m.filter((x) => x > 0).length; });
    S._incM = { k: S.data, v: out };
    return out;
  }
  const scopeOk = (it) => it.cat === '配息型' || (S.inc.scope === 'bond' && it.cat === '債券型');
  function incPool() {
    const M = incMonths();
    return items().filter((it) => scopeOk(it) && it.close > 0 && M[it.code] && M[it.code].sum > 0)
      .map((it) => ({ it, mm: M[it.code], st: statOf(it) }));
  }
  /* 單檔：達到年領目標的最少張數（扣健保時逐張往上加到達標） */
  function lotsFor(target, mm) {
    let L = Math.max(1, Math.ceil(target / (mm.sum * 1000)));
    const net = (L) => mm.m.reduce((a, x) => a + (x > 0 ? netOf(L * x * 1000) : 0), 0);
    for (let k = 0; k < 5000 && net(L) < target; k++) L++;
    return { lots: L, net: net(L), gross: L * mm.sum * 1000 };
  }
  const trOf = (st) => (st && st.ok ? st.tr_ann : null);
  const divAnn = (st) => (st && st.ok && st.tr_ann != null && st.price_ann != null ? (1 + st.tr_ann) / (1 + st.price_ann) - 1 : null);
  function incSingles() {
    const T = S.inc.year;
    const R = incPool().map((x) => { const l = lotsFor(T, x.mm); return { ...x, ...l, cost: l.lots * 1000 * x.it.close, y: x.mm.sum / x.it.close, tr: trOf(x.st) }; });
    const k = S.inc.sort === 'tr' ? 'tr' : 'y';
    return R.filter((r) => r[k] != null).sort((a, b) => b[k] - a[k]).concat(R.filter((r) => r[k] == null));
  }
  /* 組合：貪婪補缺口＋逐檔二分壓張數 */
  function solveCombo(mem, N) {
    const k = mem.length, A = mem.map((x) => x.mm.m.map((v) => v * 1000)), P = mem.map((x) => x.it.close * 1000);
    const lots = Array(k).fill(0);
    const month = (m, L) => { let s = 0; for (let i = 0; i < k; i++) if (A[i][m] > 0 && L[i] > 0) s += netOf(L[i] * A[i][m]); return s; };
    const feas = (L) => { for (let m = 0; m < 12; m++) if (month(m, L) < N) return false; return true; };
    for (let it = 0; it < 60; it++) {
      let wm = -1, wd = 0;
      for (let m = 0; m < 12; m++) { const d = N - month(m, lots); if (d > wd) { wd = d; wm = m; } }
      if (wm < 0) break;
      let bi = -1, bc = Infinity;
      for (let i = 0; i < k; i++) if (A[i][wm] > 0 && P[i] / A[i][wm] < bc) { bc = P[i] / A[i][wm]; bi = i; }
      if (bi < 0) return null;
      const f = S.inc.nhi ? 1 - NHI : 1;
      lots[bi] += Math.max(1, Math.ceil(wd / (A[bi][wm] * f)));
    }
    if (!feas(lots)) return null;
    for (let pass = 0; pass < 2; pass++) {
      for (let i = 0; i < k; i++) {
        let lo = 0, hi = lots[i];
        while (lo < hi) { const mid = (lo + hi) >> 1; const t = lots.slice(); t[i] = mid; if (feas(t)) hi = mid; else lo = mid + 1; }
        lots[i] = hi;
      }
    }
    if (lots.some((l) => l < 1)) return null;
    const mon = Array.from({ length: 12 }, (_, m) => month(m, lots));
    const by = Array.from({ length: 12 }, (_, m) => mem.map((x, i) => (A[i][m] > 0 ? netOf(lots[i] * A[i][m]) : 0)));
    const costs = lots.map((l, i) => l * P[i]), cost = costs.reduce((a, b) => a + b, 0), year = mon.reduce((a, b) => a + b, 0);
    const trs = mem.map((x) => trOf(x.st));
    const tr = trs.every((v) => v != null) ? trs.reduce((a, v, i) => a + v * costs[i], 0) / cost : null;
    return { mem, lots, costs, cost, mon, by, year, min: Math.min(...mon), y: year / cost, tr };
  }
  function incCombos() {
    /* ★ 18:50 剖析：窮舉 2～4 檔（20 選 4 約 6000 組×二分壓張數）只跟「每月目標／健保／範圍」有關；
       以前快取鍵連「排序方式、報酬期間」一起算，切一次排序就整個重算一輪（CPU 降速 4 倍時單次 1.4 秒＝「卡住」）。
       現在窮舉結果只看前三者快取；排序與含息年化（隨期間）每次重排即可。 */
    const N = S.inc.mon, key = [N, S.inc.nhi, S.inc.scope].join('|'), sk = [key, S.inc.csort, perKey(), !!S.series].join('|');
    if (S._incC && S._incC.sk === sk && S._incC.d === S.data) return S._incC.v;
    if (!S._incCM || S._incCM.d !== S.data) S._incCM = { d: S.data, m: new Map() };   // 窮舉結果依「目標｜健保｜範圍」各存一份（來回切不重算）
    const hit = S._incCM.m.get(key);
    if (hit) { const out = rankCombos(hit.res, hit.n); S._incC = { key, sk, d: S.data, v: out }; return out; }
    const pool = incPool().filter(({ it, mm }) => /^(月配|雙月配|季配)$/.test(it.freq || '') && mm.n >= 3 && (it.tv20 || 0) >= 2e7)
      .sort((a, b) => b.mm.sum / b.it.close - a.mm.sum / a.it.close).slice(0, 20);
    const masks = pool.map((x) => x.mm.m.reduce((a, v, i) => a | (v > 0 ? 1 << i : 0), 0));
    const res = [], n = pool.length, FULL = 4095;
    const tryC = (ix) => { let u = 0; ix.forEach((i) => { u |= masks[i]; }); if (u !== FULL) return; const r = solveCombo(ix.map((i) => pool[i]), N); if (r) res.push(r); };
    for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) {
      tryC([a, b]);
      for (let c = b + 1; c < n; c++) { tryC([a, b, c]); for (let d = c + 1; d < n; d++) tryC([a, b, c, d]); }
    }
    const out = rankCombos(res, n);
    S._incC = { key, sk, d: S.data, v: out };
    if (S._incCM.m.size > 24) S._incCM.m.clear();
    S._incCM.m.set(key, { res, n });
    return out;
  }
  function rankCombos(res, n) {
    res.forEach((r) => { const trs = r.mem.map((x) => trOf(statOf(x.it))); r.tr = trs.every((v) => v != null) ? trs.reduce((a, v, i) => a + v * r.costs[i], 0) / r.cost : null; });
    const v = S.inc.csort === 'tr' ? res.filter((r) => r.tr != null).sort((a, b) => b.tr - a.tr || a.cost - b.cost) : res.slice().sort((a, b) => a.cost - b.cost);
    return { list: v.slice(0, 5), n: res.length, pool: n };
  }
  /* ------------------------------------------------------------------ 5b. 現金流試算 v4（2026-10-07 晚，Andy 16:40／17:40／18:20 三輪回饋）
     18:20「幫我改這邊分頁變成兩大項目：第一個是『月配試算表』，裡面就會有單檔 ETF 以及組合 ETF 分頁，並且組合 ETF 內會有 A B C… 組合分頁，
          月配是在計算若是我一年或是一個月（兩者是切換功能）要配息多少錢，我可以哪些搭配；第二個是『複利試算表』，基於這些組合我可以選定組合，
          再去投入其他標的或是原來的標的或是不投入，那麼從選定的該日期算起，我的獲利會差多少%」
          「Y 軸改用 %」「上面的週期可以自己選日期到至今」「圖表需要給出對應單位」「圓餅圖內資訊不可以有換行」「曲線圖太小就用可以用滾輪放大」。
     · 月配試算表：年領｜月領切換；單檔＝D 款橫條排行（右側總清單勾選替換，最多 10）＋點一檔看甜甜圈與 12 個月直條；
       組合＝A～E 分頁，左欄投入甜甜圈＋12 個月時鐘（同尺寸、同一套顏色），右欄每月入帳直條＋各檔清單。不放回測曲線。
     · 複利試算表：選對象（月配試算表裡的組合 A～E 或任一單檔，張數沿用月配試算表算出的）→ 起始日（日期選擇器＋1／3／5 年快捷）→
       情境（只領現金／再投入原標的／0050／00631L 可勾，另可加自訂標的；合計最多 6 條）→ 報酬率 % 曲線（滾輪縮放、拖曳、下方滑桿）＋結論句＋情境表。
     · 17:40 修過的「再投入標的沒作用」：個股一律走 App.load('stock/<代號>')、名稱代號都認、Enter／按鈕／選單都觸發（見 addCmp）。 */
  const LEV_RE = /正2|正二|槓桿|L$/;
  const CMB = ['A', 'B', 'C', 'D', 'E'];
    function incLoad() {
    if (S.inc) return;
    const num = (k, d) => { const v = +LS.get(k, ''); return v > 0 ? v : d; };
    S.inc = { fq: LS.get('tw.etf.inc.fq', 'all') || 'all', year: num('tw.etf.inc.year', 1000000), mon: num('tw.etf.inc.mon', 20000), mode: LS.get('tw.etf.inc.mode', 'y') === 'm' ? 'm' : 'y',
      main: LS.get('tw.etf.inc.main', 'm') === 'x' ? 'x' : 'm',
      tab: LS.get('tw.etf.inc.tab', 's') === 'c' ? 'c' : 's', sort: LS.get('tw.etf.inc.sort', 'y'), csort: LS.get('tw.etf.inc.csort', 'cost'),
      scope: LS.get('tw.etf.inc.scope', 'div'), nhi: LS.get('tw.etf.inc.nhi', '') === '1', cview: LS.get('tw.etf.inc.cview', 'clock'),
      ci: 0, sel: null, det: null, q: '', cmp: [], scn: { cash: 1, self: 1, '0050': 1, '00631L': 1 }, obj: '', xfrom: '' };
    if (!/^(y|tr|pr)$/.test(S.inc.sort)) S.inc.sort = 'y';
  }
  const incYearT = () => (S.inc.mode === 'm' ? S.inc.mon * 12 : S.inc.year);
  const incMonT = () => (S.inc.mode === 'm' ? S.inc.mon : Math.ceil(S.inc.year / 12));
  const ntw = (v) => (v == null ? '—' : 'NT$ ' + wan(v));
  const wan1 = (v) => wan(v).replace(' ', '');
  const prOf = (st) => (st && st.ok && st.price_ann != null ? st.price_ann : null);
  function incSinglesV2() {
    const T = incYearT();
    const R = incPool().map((x) => {
      const l = lotsFor(T, x.mm);
      return { ...x, ...l, cost: l.lots * 1000 * x.it.close, y: x.mm.sum / x.it.close, tr: trOf(x.st), pr: prOf(x.st) };
    });
    const k = S.inc.sort;
    return R.filter((r) => r[k] != null).sort((a, b) => b[k] - a[k]).concat(R.filter((r) => r[k] == null));
  }
  const SORT_L = [['y', '殖利率'], ['tr', '含息總報酬'], ['pr', '不含息總報酬']];
  const metricTxt = (r, k) => (k === 'tr' ? `含息年化 ${pct(r.tr, 1)}` : k === 'pr' ? `價格年化 ${pct(r.pr, 1)}` : `殖利率 ${pctU(r.y, 1)}`);

  /* ---------------- 再投入複利模擬：核心（純函式，_uitest 用假資料直接驗口徑）
     D：週日期陣列（'YYYY-MM-DD'，etf_series 的共同時間軸）；i0：起算那一週。
     mem：[{ shares, px:[], ev:[{ k: 除息那週索引, amt: 每單位配息, pay: 'YYYY-MM-DD' 發放日 }], T:[] 再投入標的的「含息指數」（標的自己的配息也滾進去）}]
     口徑：
       1. 起始日那一週收盤買進 shares 單位，本金之後不動、不加碼。
       2. 每次配息在「發放日」入帳現金（勾二代健保：單筆 ≥ 2 萬扣 2.11%）；除息週 ≤ i0 的不算（買進時已除息）。
       3. 入帳的現金在「發放月的下一個月」第一個資料點（週收盤）買進再投入標的（允許零股；以標的含息指數記單位，
          標的自己的配息在除息日再投入同一標的）。⇒ 1 月發放的錢，2 月才進場。標的那天還沒有價格就續抱現金，等第一個有價的點。
       4. 總資產＝原持股市值＋已入帳未買進的現金＋再投入部位市值。「只領現金」＝原持股市值＋累積入帳現金（不再投入）。
          報酬率＝總資產 ÷ 本金（起始日買進成本）− 1。 */
  function simCore(D, mem, i0, nhi) {
    const n = D.length, tot = Array(n).fill(null), cash = Array(n).fill(null), price = Array(n).fill(null), buys = [];
    const st = mem.map((m) => ({ units: 0, cum: 0, ev: (m.ev || []).filter((e) => e.k > i0)
      .map((e) => { const g = m.shares * e.amt, net = nhi && g >= NHI_MIN ? g * (1 - NHI) : g; return { ...e, net, ym: String(e.pay).slice(0, 7), got: false, done: false }; }) }));
    for (let k = i0; k < n; k++) {
      let T = 0, C = 0, P = 0, ok = true;
      mem.forEach((m, j) => {
        const s = st[j], p = m.px[k];
        if (p == null) { ok = false; return; }
        s.ev.forEach((e) => {
          if (!e.got && D[k] >= e.pay) { e.got = true; s.cum += e.net; }
          if (e.got && !e.done && D[k].slice(0, 7) > e.ym && m.T[k] != null && m.T[k] > 0) { e.done = true; s.units += e.net / m.T[k]; buys.push({ k, d: D[k], amt: e.net, pay: e.pay, j }); }
        });
        const pend = s.ev.reduce((a, e) => a + (e.got && !e.done ? e.net : 0), 0);
        const tv = s.units > 0 ? s.units * (m.T[k] != null ? m.T[k] : 0) : 0;
        T += m.shares * p + pend + tv; C += m.shares * p + s.cum; P += m.shares * p;
      });
      if (ok) { tot[k] = T; cash[k] = C; price[k] = P; }
    }
    const cost = mem.reduce((a, m) => a + m.shares * (m.px[i0] || 0), 0);
    return { tot, cash, price, buys, cost };
  }
  const ALN = {};
  function alignEtf(code) {
    const g = S.series; if (!g || !g.s || !g.s[code]) return null;
    if (ALN[code] && ALN[code].g === g) return ALN[code].v;
    const x = g.s[code], n = g.D.length, p = Array(n).fill(null), t = Array(n).fill(null);
    for (let k = x.i; k < n; k++) { p[k] = x.p[k - x.i]; t[k] = x.t ? x.t[k - x.i] : x.p[k - x.i]; }
    const v = { p, t, hasT: !!x.t };
    ALN[code] = { g, v };
    return v;
  }
  /* 從週線「含息÷價格」的跳動反推每次配息（etf_series 沒存配息明細）：g＝(t_k/t_{k-1})/(p_k/p_{k-1})−1 > 0.15% 視為那週除息，
     每單位配息 ≈ p_k × g；配息行事曆（近 12 個月）同檔除息日落在那週的，改用行事曆的金額與發放日；查不到發放日就以除息後 21 天估。 */
  const EVC = {};
  function evOf(code, a) {
    if (!a || !a.hasT) return [];
    if (EVC[code] && EVC[code].a === a) return EVC[code].v;
    const D = S.series.D, cal = ((S.data && S.data.calendar) || []).filter((e) => e.code === code && e.amt > 0), out = [];
    for (let k = 1; k < D.length; k++) {
      const p0 = a.p[k - 1], p1 = a.p[k], t0 = a.t[k - 1], t1 = a.t[k];
      if (!(p0 > 0 && p1 > 0 && t0 > 0 && t1 > 0)) continue;
      const g = (t1 / t0) / (p1 / p0) - 1; if (!(g > 0.0015)) continue;
      const c = cal.find((e) => e.ex > D[k - 1] && e.ex <= D[k]);
      const pay = c && c.pay ? c.pay : new Date(Date.parse(D[k] + 'T00:00:00Z') + 21 * 864e5).toISOString().slice(0, 10);
      out.push({ k, amt: c ? +c.amt : +(p1 * g).toFixed(4), pay });
    }
    EVC[code] = { a, v: out };
    return out;
  }
  const RXC = {};
  function rxSeries(code) {
    if (code === 'self') return Promise.resolve('self');
    const e = alignEtf(code);
    if (e) return Promise.resolve(e.t);
    if (RXC[code]) return RXC[code];
    if (!/^\d{4,6}[A-Z]?$/.test(code)) return Promise.resolve(null);
    RXC[code] = Promise.resolve(A().load('stock/' + code, { fallback: null })).catch(() => null).then((j) => {
      const dl = j && j.daily; if (!dl || !dl.length || !S.series) return null;
      const D = S.series.D, T = Array(D.length).fill(null); let q = 0;
      for (let k = 0; k < D.length; k++) { while (q < dl.length && dl[q][0] <= D[k]) q++; if (q > 0 && D[k] >= dl[0][0]) T[k] = dl[q - 1][4]; }
      return T.some((v) => v != null) ? T : null;
    });
    return RXC[code];
  }
  const nameOf = (c) => { const it = items().find((x) => x.code === c); if (it) return it.name; const L = A().L; return (L && L.cname && L.cname[c]) || ''; };
  function codeFromInput(v) {
    v = String(v || '').trim(); if (!v) return '';
    const m = /([0-9]{4,6}[A-Za-z]?)\s*$/.exec(v) || /^([0-9]{4,6}[A-Za-z]?)/.exec(v);
    if (m) return m[1].toUpperCase();
    const it = items().find((x) => x.name === v) || items().find((x) => x.name && x.name.indexOf(v) >= 0);
    if (it) return it.code;
    const L = A().L; if (L && L.cname) { const hit = Object.keys(L.cname).find((c) => L.cname[c] === v); if (hit) return hit; }
    return v.toUpperCase();
  }
  const segH = (id, L, v) => `<div class="seg" id="${id}">${L.map(([x, t]) => `<button type="button" data-v="${x}"${String(x) === String(v) ? ' class="on"' : ''}>${t}</button>`).join('')}</div>`;
  const howH = (k, li) => `<div class="howtxt" id="how-${k}" hidden>${A().howHTML('', li)}</div>`;
  const hbtnH = (k, t) => `<button class="howbtn pop" data-how="${k}" data-ttl="${t}" type="button" aria-label="${t}">?</button>`;

  function incSkeleton(box) {
    const L = A().L, stocks = L && L.cname ? Object.keys(L.cname).filter((c) => /^\d{4}$/.test(c)).slice(0, 2500) : [];
    const dl = items().filter((x) => x.close > 0).map((x) => `<option value="${esc(x.code)}">${esc(x.name)}</option>`).join('')
      + stocks.map((c) => `<option value="${esc(c)}">${esc(L.cname[c])}</option>`).join('');
    box.innerHTML = `
<p class="incdisc" id="incDisc">ⓘ 以下依歷史價格與配息回測／試算，不代表未來；配息可能變動、可能配到本金；槓桿型 ETF 波動與耗損大。僅供參考，不構成投資建議。</p>
<div class="nbsw incmain" id="incMain" role="tablist"><button type="button" role="tab" data-v="m">月配試算表</button><button type="button" role="tab" data-v="x">複利試算表</button></div>
<datalist id="incRxList">${dl}</datalist>
<div id="incPM">
<div class="incctl">
  <div class="grp"><b>目標</b>${segH('incMode', [['y', '年領'], ['m', '月領']], S.inc.mode)}<span id="incAmtBox"></span><input type="number" id="incAmt" min="1000" step="1000" aria-label="自訂目標（元）"><small>元</small></div>
  <div class="grp"><b>範圍</b>${segH('incScope', [['div', '配息型'], ['bond', '配息型＋債券型']], S.inc.scope)}</div>
  <label class="chk"><input type="checkbox" id="incNhi"${S.inc.nhi ? ' checked' : ''}>扣除二代健保（單筆 ≥ 2 萬扣 2.11%）</label>
  <div class="grp"><b>報酬期間</b><span id="etfIncRngBox"></span></div>
</div>
<div class="inctabrow"><div class="nbsw inctabs" id="incTabs" role="tablist"><button type="button" role="tab" data-v="s">單檔 ETF</button></div>
  <span class="csortw" id="incCSortW"><b>組合</b>（${segH('incCSort', [['cost', '投入最少'], ['tr', '含息報酬最高']], S.inc.csort)}）${hbtnH('incc', '組合怎麼找')}</span></div>
<div class="incsec" id="incSingle">
  <div class="row spread"><h3 data-icon="coins" data-tone="yield">單檔：要幾張、要多少錢 <small id="incYLab"></small> ${hbtnH('incs', '單檔試算怎麼看')}</h3>
    <span class="row" style="gap:6px"><small class="lbl">排序</small>${segH('incSort', SORT_L, S.inc.sort)}</span></div>
  ${howH('incs', ['<b>每單位年配息</b>＝近 12 個月（含已公告、還沒除息的）每次現金配息加總；依「發放月」算，同一個月只算最新一筆。',
    '<b>張數</b>＝年目標 ÷（每單位年配息 × 1000），無條件進位；月領模式的年目標＝月領 × 12。<b>金額</b>＝張數 × 1000 × 最新收盤。',
    '<b>殖利率</b>＝每單位年配息 ÷ 最新收盤。<b>含息年化</b>＝「報酬期間」的含息總報酬年化；<b>價格年化</b>＝不含息（只看價格）的年化。這三種決定排序。',
    '直條＝前 5 名每個月入帳（萬），灰線＝平均；右側清單勾選替換（最多 5 檔），上方膠囊按 × 也會同步取消。點直條或清單名稱看該檔細節。想看「配息再投入能多賺多少」請到上方「複利試算表」。'])}
  <p class="incq" id="incSQ"></p>
  <div class="incsg"><div class="incbarw"><div class="snkey" id="incChips"></div><div id="incBar" class="chart"></div></div>
    <div class="inclist" id="incListBox"><div class="ilhd"><input type="search" id="incSearch" placeholder="搜尋名稱或代號" aria-label="搜尋 ETF"><button type="button" class="btn small" id="incReset">回前 5</button></div>
      <div class="ilfq" id="incFq" role="tablist" aria-label="依配息頻率分類"></div>
      <p class="ilmsg" id="incListMsg"></p><div class="ilbody" id="incList"></div></div></div>
  <div class="incdet" id="incDet" hidden></div>
</div>
<div class="incsec" id="incCombo" hidden>
  ${howH('incc', ['季配 ETF 的發放月份錯開，三、四檔搭在一起就能每個月都有錢入帳。每月目標用上方「目標」：月領＝那個金額；年領＝年領 ÷ 12。',
    '<b>候選</b>：範圍內的月配／雙月配／季配、近 20 日均成交值 ≥ 2000 萬、殖利率前 20 檔；<b>窮舉</b> 2～4 檔，只留 12 個月都有配息的組合，前 5 名分成 A～E 分頁。',
    '<b>張數</b>：先補缺最多的月份（補那個月每元配息最便宜的那檔），直到每月 ≥ 目標，再逐檔把張數往下壓到剛好不破目標。每檔至少 1 張。',
    '<b>甜甜圈</b>＝各檔投入金額占比；<b>時鐘</b>＝12 個月，頂端 12 月、順時針，月份 m 落在 m 點鐘；<b>直條</b>＝每個月入帳金額。三張圖的顏色都＝甜甜圈上那檔的顏色（月份用當月主要入帳那檔）。',
    '未計入二代健保補充保費與所得稅；勾上方「扣除二代健保」會改用扣除後的金額。選定組合後，可到「複利試算表」看配息再投入的差別。'])}
  <p class="incq" id="incCQ"></p>
  <div class="combos" id="incCombos"></div>
</div>
</div>
<div id="incPX" hidden>
  <div class="row spread"><h3 data-icon="arrow-up" data-tone="up">複利試算：配息拿去再投入，能多賺幾 % ${hbtnH('incx', '複利試算怎麼算')}</h3></div>
  ${howH('incx', ['<b>對象</b>：月配試算表裡的組合 A～E，或任一檔配息 ETF；張數沿用月配試算表依目標算出的張數（上方改目標，這裡跟著變）。',
    '<b>起始日</b>：那一週收盤買進，本金之後不動、不加碼；算到資料最新一天。',
    '<b>配息</b>：每次配息在發放日入帳；<b>再投入</b>＝在發放月的<b>下一個月</b>第一個週收盤買進（零股；標的自己的配息再滾入同一標的）。⇒ 1 月發放的錢 2 月才進場。',
    '<b>報酬率</b>＝（原持股市值＋待投入現金＋再投入部位）÷ 本金 − 1。<b>只領現金</b>＝原持股＋累積領到的現金；<b>只看價格</b>＝原持股市值（不含任何配息）。',
    '一年以前的配息由週線含息指數反推、發放日以除息後 21 天估，會有些微誤差；近 12 個月用配息行事曆的實際金額與發放日。'])}
  <div class="incctl cxctl">
    <div class="grp"><b>對象</b><select id="cxObj" aria-label="複利試算對象"></select></div>
    <div class="grp"><b>起始日</b><input type="date" id="cxFrom" aria-label="起始日期">${segH('cxQuick', [['1', '1 年'], ['3', '3 年'], ['5', '5 年']], '')}<small>～至今</small></div>
  </div>
  <div class="cxg"><div class="cxl">
    <div class="cxlg"><small>點下方圖例可開關那條線（右表與結論跟著變）</small><span class="cmpw"><input class="cmpin" id="cxIn" list="incRxList" placeholder="＋自訂再投入標的（代號／名稱）" aria-label="加入自訂再投入標的"><button type="button" class="btn small" id="cxAdd">加入</button></span>
      <span class="cmpchips" id="cxChips"></span><small class="rxmsg" id="cxMsg"></small></div>
    <div id="cxChart" class="chart"></div></div>
    <div class="cxr"><div class="simtw"><table class="simt" id="cxTbl"></table></div>
    <p class="cxhead" id="cxHead"></p><p class="simlev" id="cxLev">00631L 為 2 倍槓桿型（每日重設），長期報酬受波動耗損影響大，回測結果高度依賴期間。</p></div></div>
</div>`;
    const setAmt = (v) => { if (!(v > 0)) return; v = Math.round(v); if (S.inc.mode === 'm') { S.inc.mon = v; LS.set('tw.etf.inc.mon', v); } else { S.inc.year = v; LS.set('tw.etf.inc.year', v); } drawInc(); };
    box._setAmt = setAmt;
    $$('#incMain button').forEach((b) => { b.onclick = () => { S.inc.main = b.dataset.v; LS.set('tw.etf.inc.main', S.inc.main); drawInc(); }; });
    $$('#incMode button').forEach((b) => { b.onclick = () => { S.inc.mode = b.dataset.v; LS.set('tw.etf.inc.mode', S.inc.mode); drawInc(); }; });
    $('#incAmt').onchange = (e) => setAmt(+e.target.value);
    $$('#incTabs button').forEach((b) => { b.onclick = () => { S.inc.tab = b.dataset.v; LS.set('tw.etf.inc.tab', S.inc.tab); drawInc(); }; });
    $$('#incScope button').forEach((b) => { b.onclick = () => { S.inc.scope = b.dataset.v; LS.set('tw.etf.inc.scope', S.inc.scope); S.inc.sel = null; drawInc(); }; });
    $$('#incSort button').forEach((b) => { b.onclick = () => { S.inc.sort = b.dataset.v; LS.set('tw.etf.inc.sort', S.inc.sort); drawInc(); }; });
    $$('#incCSort button').forEach((b) => { b.onclick = () => { S.inc.csort = b.dataset.v; LS.set('tw.etf.inc.csort', S.inc.csort); S.inc.ci = 0; drawInc(); }; });
    $('#incNhi').onchange = (e) => { S.inc.nhi = e.target.checked; LS.set('tw.etf.inc.nhi', S.inc.nhi ? '1' : ''); drawInc(); };
    $('#incSearch').oninput = (e) => { S.inc.q = e.target.value.trim(); drawIncList(S._incR || []); };
    // v7（Andy：清單要依月配／雙月配／季配／半年配分類）：「回前 5」取目前這一類的前 5 檔；「全部」時照舊回整體前 5
    $('#incReset').onclick = () => { const fq = S.inc.fq || 'all', R0 = S._incR || [];
      S.inc.sel = fq === 'all' ? null : R0.filter((r) => r.it.freq === fq).slice(0, 5).map((r) => r.it.code);
      $('#incListMsg').textContent = ''; drawInc(); };
    // 複利
    $('#cxObj').onchange = (e) => { S.inc.obj = e.target.value; drawCx(); };
    $('#cxFrom').max = todayTW();
    $('#cxFrom').onchange = (e) => { if (e.target.value) { S.inc.xfrom = e.target.value; S.inc.xq = ''; drawCx(); } };
    $$('#cxQuick button').forEach((b) => { b.onclick = () => { S.inc.xq = b.dataset.v; S.inc.xfrom = yrsAgo(todayTW(), +b.dataset.v); drawCx(); }; });
    const go = () => addCmp($('#cxIn').value);
    $('#cxAdd').onclick = go;
    $('#cxIn').onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); go(); } };   // ★ v6：拿掉 onchange——按「加入」時輸入框失焦也會觸發 change，一次加兩檔
    if (window.RangePick) {
      const r = perRange();
      $('#etfIncRngBox').innerHTML = window.RangePick.html({ id: 'etfIncRng', options: PERS, value: S.per, from: r.from, to: r.to, max: todayTW() });
      window.RangePick.bind($('#etfIncRng'), { onChange: ({ value, from, to }) => {
        S.per = value; LS.set('tw.etf.per', S.per);
        if (value === 'custom') { if (from) { S.cfrom = from; LS.set('tw.etf.cfrom', from); } S.cto = to || todayTW(); }
        drawInc();
      } });
    }
  }
  async function addCmp(v) {
    const code = codeFromInput(v), msg = $('#cxMsg'); if (!code) return;
    if (S.inc.cmp.includes(code) || code === '0050' || code === '00631L') { msg.textContent = `${code} 已在情境裡`; return; }
    if (S.inc.cmp.length >= 5) { msg.textContent = '自訂標的最多 5 檔，請先移除一檔'; return; }
    if (!S.series) await loadSeries();
    const T = await rxSeries(code);
    if (!T) { msg.textContent = `${code} 沒有歷史價格，不能加入`; return; }
    if (S.inc.cmp.includes(code)) { msg.textContent = `${code} 已在情境裡`; return; }   // 等資料期間可能被別的觸發先加進去了，回來再查一次
    if (S.inc.cmp.length >= 5) { msg.textContent = '自訂標的最多 5 檔，請先移除一檔'; return; }
    S.inc.cmp = S.inc.cmp.concat([code]); msg.textContent = ''; $('#cxIn').value = ''; drawCx();
  }
  function drawInc() {
    incLoad();
    const box = $('#etfInc'); if (!box) return;
    if (!$('#incPX', box)) incSkeleton(box);
    const segOn = (id, v) => $$(`#${id} button`).forEach((b) => b.classList.toggle('on', String(b.dataset.v) === String(v)));
    const P = S.inc.mode === 'm' ? INC_M : INC_Y, amt = S.inc.mode === 'm' ? S.inc.mon : S.inc.year;
    $('#incAmtBox').innerHTML = `<div class="seg" id="incAmtSeg">${P.map(([x, t]) => `<button type="button" data-v="${x}"${x === amt ? ' class="on"' : ''}>${t}</button>`).join('')}</div>`;
    $$('#incAmtSeg button').forEach((b) => { b.onclick = () => box._setAmt(+b.dataset.v); });
    $('#incAmt').value = amt; $('#incAmt').step = S.inc.mode === 'm' ? 1000 : 10000;
    segOn('incMain', S.inc.main); segOn('incMode', S.inc.mode); segOn('incScope', S.inc.scope); segOn('incSort', S.inc.sort); segOn('incCSort', S.inc.csort); segOn('incCView', S.inc.cview);
    $('#incNhi').checked = S.inc.nhi;
    $('#incPM').hidden = S.inc.main !== 'm'; $('#incPX').hidden = S.inc.main !== 'x';
    $('#incSingle').hidden = S.inc.tab !== 's'; $('#incCombo').hidden = S.inc.tab !== 'c';
    $('#incCSortW').classList.toggle('dim', S.inc.tab !== 'c');
    if ($('#etfIncRng')) { const r = perRange(); window.RangePick.set($('#etfIncRng'), { value: S.per, from: r.from, to: r.to }); }
    if (S.fallback || !((S.data && S.data.calendar) || []).length) {
      $('#incSQ').textContent = '尚無配息資料'; $('#incList').innerHTML = ''; $('#incCombos').innerHTML = '<div class="etfprep">尚無配息資料</div>'; return;
    }
    if (!S.series) { loadSeries().then(() => { if (S.view === 'inc') drawInc(); }); }
    if (S.inc.main === 'x') drawCx();
    else { incTabsDraw(); if (S.inc.tab === 's') drawIncSingle(); else drawIncCombos(); }
    reflow(S.inc.main === 'x' ? $('#incPX') : S.inc.tab === 's' ? $('#incSingle') : $('#incCombo'));
    box.dataset.k = [S.inc.mode, incYearT(), incMonT(), S.inc.sort, S.inc.csort, S.inc.scope, S.inc.nhi ? 1 : 0, perKey(), S.inc.tab, S.inc.main].join('|');
  }
  const touchy = () => !!(window.matchMedia && window.matchMedia('(hover: none)').matches);
  function twoTap(key, fn) { if (touchy() && S._tap !== key) { S._tap = key; return; } S._tap = null; fn(); }

  /* ================= 月配試算表：單檔 ================= */
  function drawIncSingle() {
    const R = incSinglesV2(), T = incYearT(), k = S.inc.sort;
    S._incR = R;
    $('#incYLab').textContent = S.inc.mode === 'm' ? `月領 ${wan(S.inc.mon)}（＝年領 ${wan(T)}）${S.inc.nhi ? '扣健保後' : ''}` : `年領 ${wan(T)}${S.inc.nhi ? '（扣健保後）' : ''}`;
    const codes = R.map((r) => r.it.code);
    const sel = S.inc.sel ? S.inc.sel.filter((c) => codes.includes(c)) : codes.slice(0, 5);
    if (S.inc.sel) S.inc.sel = sel;
    const top = R.filter((r) => sel.includes(r.it.code));
    const best = R.slice().sort((a, b) => a.cost - b.cost)[0];
    $('#incSQ').innerHTML = R.length ? `要${S.inc.mode === 'm' ? `每月領 <b>${wan(S.inc.mon)}</b>` : `每年領 <b>${wan(T)}</b>`}：${R.length} 檔裡投入最少的是 <b>${esc(best.it.name)}</b>（<b>${best.lots.toLocaleString()} 張・${ntw(best.cost)}</b>）。`
      + `直條＝依<b>${SORT_L.find((x) => x[0] === k)[1]}</b>排序的前 5 檔，各買上述張數後每個月入帳多少（萬），灰線＝平均；右側清單勾選替換（最多 5 檔）。` : '這個範圍沒有近 12 個月有配息的 ETF';
    const el = $('#incBar');
    el.dataset.codes = top.map((r) => r.it.code).join(',');
    el.dataset.lots = top.map((r) => r.lots).join(',');
    el.dataset.costs = top.map((r) => Math.round(r.cost)).join(',');
    el.dataset.vals = top.map((r) => (r[k] == null ? '' : r[k])).join(',');
    drawSingleCurve(top);
    drawIncList(R);
    drawDet();
  }
  const firstOfMonthFn = (X) => (i) => i === 0 || X[i].slice(0, 7) !== X[i - 1].slice(0, 7);
  /* v8（Andy：「曲線圖月份之間都要微微線條區隔」）：每個月一條很淡的直線。顏色用 ink-3 的 16% 透明，深淺主題都看得到但不搶線。 */
  const monthLine = (a) => ({ color: a.hexA(a.CH.ink3, 0.16), width: 0.8, type: 'solid' });
  const monthAxis = (X, a) => {
    const f = firstOfMonthFn(X), CH = a.CH;
    return { type: 'category', data: X, boundaryGap: false, ...a.axisStyle, axisTick: { show: true, interval: f }, splitLine: { show: true, interval: f, lineStyle: monthLine(a) },
      axisLabel: { ...a.axisStyle.axisLabel, fontSize: 11, interval: f, hideOverlap: true, formatter: (v) => (v.slice(5, 7) === '01' ? v.slice(0, 4) : String(+v.slice(5, 7)) + '月') } };
  };
  /* 18:52「單檔 ETF 改用這方式如圖表示，並且改成前 5 名即可」＋「有需要再從旁邊清單篩選，至多 5 檔」：
     照週期統計頁的「長條圖」模式（X 軸 1～12 月、每月一組並排直條、每檔一色、一條平均折線、上方膠囊可 ×、提示框依大小排並標高於／低於平均）。
     值＝該檔依目標張數「那個月入帳多少（萬）」；平均線＝這幾檔的平均。膠囊與右側清單勾選雙向同步，最多 5 檔。
     配色與膠囊直接用週期統計那支（App.snColor／App.msTags），長條參數照抄 seasonLine（barGap 12%、組間 22%、barMaxWidth 16）。 */
  function drawSingleCurve(top) {
    const el = $('#incBar'), a = A(), CH = a.CH, mob = window.matchMedia && window.matchMedia('(max-width: 640px)').matches;
    const MONTHS = Array.from({ length: 12 }, (_, i) => `${i + 1} 月`), AVG = '平均';
    const colOf = (i) => (a.snColor ? a.snColor(i) : a.donut.color(i));
    const vals = top.map((r) => r.mm.m.map((x) => (x > 0 ? +(netOf(r.lots * x * 1000) / 1e4).toFixed(2) : 0)));
    const avg = MONTHS.map((_, m) => (vals.length ? +(vals.reduce((s, v) => s + v[m], 0) / vals.length).toFixed(2) : null));
    el.style.height = (mob ? 360 : 440) + 'px';
    const series = top.map((r, i) => ({ name: `${r.it.name} ${r.it.code}`, code: r.it.code, type: 'bar', barGap: mob ? '0%' : '12%', barCategoryGap: mob ? '16%' : '22%', barMaxWidth: 16, z: 2,
      label: { show: false }, cursor: 'pointer', emphasis: { focus: 'series' }, itemStyle: { color: colOf(i), borderRadius: [3, 3, 0, 0] }, data: vals[i].map((v) => (v > 0 ? v : null)) }));
    series.push({ name: AVG, type: 'line', smooth: false, symbol: 'circle', symbolSize: 5, z: 5, data: avg, lineStyle: { width: 2, color: a.hexA(CH.ink2, 0.9) }, itemStyle: { color: CH.ink2 } });
    a.chart('incBar', {
      animation: false, timeGrid: false,
      tooltip: { ...a.tip, confine: true, trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: (ps) => { const m = ps[0].dataIndex, av = avg[m];
          const rest = ps.filter((q) => q.seriesName !== AVG && q.value != null).sort((p, q) => q.value - p.value);
          el.dataset.tip = `${m + 1}|` + rest.map((q) => q.value).join(',');
          return `<b>${m + 1} 月入帳</b><br>${a.hexA ? '' : ''}<span style="color:${CH.ink3}">— ${AVG} ${av} 萬</span>`
            + rest.map((q) => { const r = top[q.seriesIndex]; return `<br>${q.marker}${esc(q.seriesName)} <b>${q.value} 萬</b>（${r.lots.toLocaleString()} 張）<span style="color:${CH.ink3}">（${q.value >= av ? '高於' : '低於'}平均）</span>`; }).join('')
            + (rest.length < top.length ? `<br><span style="color:${CH.ink3}">其餘 ${top.length - rest.length} 檔這個月沒有配息</span>` : ''); } },
      legend: { show: false },
      grid: { left: 52, right: mob ? 12 : 20, top: 16, bottom: 28 },
      xAxis: { ...a.axisStyle, type: 'category', data: MONTHS, axisTick: { show: false }, axisLabel: { color: CH.ink2, fontSize: 12, interval: 0 },
        splitLine: { show: true, keep: true, interval: 0, lineStyle: { color: CH.ink2, opacity: 0.18, width: 1, type: 'solid' } } },
      yAxis: { ...a.axisStyle, type: 'value', name: '萬', nameTextStyle: { color: CH.ink3, fontSize: 11 }, axisLabel: { color: CH.ink3, fontSize: 12, formatter: (v) => v + ' 萬' } },
      series,
    }, { notMerge: true });
    const key = $('#incChips');
    if (key && a.msTags) {
      a.msTags(key, top.map((r, i) => ({ name: `${r.it.name} ${r.it.code}`, color: colOf(i), title: `從圖上拿掉 ${r.it.name}（清單也會取消勾選）` })), (n) => {
        const c = (top.find((r) => `${r.it.name} ${r.it.code}` === n) || {}).it; if (!c) return;
        S.inc.sel = top.map((r) => r.it.code).filter((x) => x !== c.code); drawIncSingle();
      }, `<span class="snk avg" title="這幾檔的平均（細灰線）"><i></i>平均</span>`);
      key.insertAdjacentHTML('beforeend', `<button type="button" class="snk addk" id="incChipAdd" title="從右側清單勾選加入（最多 5 檔）">＋加入</button>`);
      const ad = $('#incChipAdd'); if (ad) ad.onclick = () => { const s = $('#incSearch'); if (s) { s.focus(); s.scrollIntoView({ block: 'nearest' }); } };
    }
    const ch = window.echarts && window.echarts.getInstanceByDom(el);
    if (ch) { ch.off('click'); ch.on('click', (p) => { const s = series[p.seriesIndex]; if (!s || !s.code) return; twoTap('l' + s.code, () => openDet(S.inc.det === s.code ? null : s.code)); }); }
    el.dataset.n = String(top.length);
    el.dataset.groups = vals.map((v) => v.join('/')).join(',');
  }
  function drawIncList(R) {
    const k = S.inc.sort, q = (S.inc.q || '').toLowerCase(), list = $('#incList'); if (!list) return;
    const sel = S.inc.sel || R.slice(0, 5).map((r) => r.it.code), full = sel.length >= 5;
    /* v7：頻率分頁。只顯示有檔數的類別；已勾選但不在這一類的檔照樣留在圖上（sel 不動），只是清單不列。搜尋在這一類裡面找。 */
    const FQS = ['月配', '雙月配', '季配', '半年配', '年配'], cnt = {}; R.forEach((r) => { cnt[r.it.freq] = (cnt[r.it.freq] || 0) + 1; });
    if (S.inc.fq && S.inc.fq !== 'all' && !cnt[S.inc.fq]) S.inc.fq = 'all';
    const fq = S.inc.fq || 'all', fb = $('#incFq');
    if (fb) {
      fb.innerHTML = [['all', '全部', R.length]].concat(FQS.filter((x) => cnt[x]).map((x) => [x, x, cnt[x]]))
        .map(([v, t, n]) => `<button type="button" role="tab" data-v="${esc(v)}"${v === fq ? ' class="on" aria-selected="true"' : ''}>${esc(t)}<small>${n}</small></button>`).join('');
      $$('button', fb).forEach((b) => { b.onclick = () => { S.inc.fq = b.dataset.v; LS.set('tw.etf.inc.fq', S.inc.fq); drawIncList(R); }; });
    }
    const rows = R.filter((r) => fq === 'all' || r.it.freq === fq).map((r, i) => ({ r, i })).filter(({ r }) => !q || r.it.code.toLowerCase().includes(q) || (r.it.name || '').toLowerCase().includes(q));
    list.innerHTML = rows.map(({ r, i }) => `<div class="ilr${sel.includes(r.it.code) ? ' in' : ''}${S.inc.det === r.it.code ? ' on' : ''}" data-code="${esc(r.it.code)}" data-fq="${esc(r.it.freq || '')}">
      <input type="checkbox" aria-label="加入主圖" ${sel.includes(r.it.code) ? 'checked' : full ? 'disabled title="最多 5 檔，先取消一檔"' : ''}><span class="rk">${i + 1}</span>
      <button type="button" class="iln" title="${esc(r.it.name)} ${esc(r.it.code)}">${fqBadge(r.it.freq)}<span class="nm">${esc(r.it.name)}</span><span class="cd">${esc(r.it.code)}</span></button>
      <span class="mv">${metricTxt(r, k)}</span><span class="lt">現價 NT$ ${A().fmt.n(r.it.close, 2)}・需 ${r.lots.toLocaleString()} 張・${ntw(r.cost)}</span></div>`).join('') || '<div class="etfprep">找不到</div>';
    list.dataset.n = String(rows.length);
    $$('.ilr', list).forEach((row) => {
      const c = row.dataset.code;
      $('input', row).onchange = (e) => {
        let cur = (S.inc.sel || R.slice(0, 5).map((r) => r.it.code)).slice();
        if (e.target.checked) { if (cur.length >= 5) { e.target.checked = false; $('#incListMsg').textContent = '最多 5 檔，請先取消一檔'; return; } cur.push(c); }
        else cur = cur.filter((x) => x !== c);
        $('#incListMsg').textContent = ''; S.inc.sel = cur; drawIncSingle();
      };
      $('.iln', row).onclick = () => openDet(S.inc.det === c ? null : c);
    });
  }
  function openDet(code) {
    S.inc.det = code; drawIncSingle();
    if (code) { const d = $('#incDet'); if (d && d.scrollIntoView) d.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
  }
  const DN = 320;
  /* 甜甜圈：中心兩行（小標＋數字）是 A 款規格；扇區外標籤一律單行 */
  /* 提示框位置：先照 A 款規則（環外側、避開中心字），再夾回圖框內——自訂 position 函式時 ECharts 的 confine 不會幫忙夾（219：跑到側欄底下）。 */
  const clampPos = (fn) => (pt, params, dom, rect, size) => {
    const r = typeof fn === 'function' ? fn(pt, params, dom, rect, size) : [pt[0] + 12, pt[1] + 12];
    const W = size.viewSize[0], H = size.viewSize[1], w = size.contentSize[0], h = size.contentSize[1];
    return [Math.max(0, Math.min(W - w, r[0])), Math.max(0, Math.min(H - h, r[1]))];
  };
  function donutBig(id, parts, op) {
    const a = A(), dop = { size: DN, fmtVal: (v) => ntw(v), ...op };
    const o = a.donut.option(parts, dop).option;
    o.tooltip = { ...o.tooltip, confine: true, position: clampPos(o.tooltip.position) };   // ★ 18:50（219）：提示框限制在圖框內，不會跑到側欄底下（appendToBody 每次重畫 echarts 會掃整頁 DOM，降速 4 倍時一次 150ms，不用）
    // ★ 18:20「圓餅圖內資訊不可以有換行」：環跟時鐘同尺寸（內徑 50%、外徑 94%），扇區內單行「N 張・X 萬」，放不下就不畫（滑過看）
    o.series[0] = { ...o.series[0], radius: ['50%', '94%'], minAngle: 6, label: { show: !!op.label, position: 'inside', color: '#fff', textBorderColor: 'rgba(0,0,0,.5)', textBorderWidth: 2, fontSize: 11.5, overflow: 'none', formatter: op.label || '' }, labelLine: { show: false }, labelLayout: { hideOverlap: true } };
    o.series[1] = { ...o.series[1], radius: ['48%', '48.6%'] };
    o.title = a.donut.center(op.centerLabel, op.centerValue, DN, 0.5);
    $('#' + id).style.height = DN + 'px';
    a.chart(id, o);
    a.donut.wireHover(window.echarts && window.echarts.getInstanceByDom($('#' + id)), parts, { ...dop, size: DN });
  }
  function monthBars(id, vals, colOf, tipOf) {
    const a = A(), CH = a.CH, B = a.barStyle;
    a.chart(id, {
      grid: { left: 4, right: 4, top: 24, bottom: 4, containLabel: true },
      tooltip: { ...a.tip, confine: true, trigger: 'item', formatter: (p) => tipOf(p.dataIndex) },
      xAxis: { type: 'category', data: Array.from({ length: 12 }, (_, i) => `${i + 1}月`), ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, fontSize: 11, interval: 0 } },
      yAxis: { type: 'value', show: false },
      series: [{ type: 'bar', barMaxWidth: 22, emphasis: { itemStyle: { borderColor: CH.ink, borderWidth: 2 } },
        itemStyle: { borderRadius: [3, 3, 0, 0], color: colOf ? (p) => { const c = colOf(p.dataIndex); return { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: c }, { offset: 1, color: a.hexA(c, 0.45) }] }; } : B.grad(false) },
        label: { show: true, position: 'top', fontSize: 11, color: CH.ink2, formatter: (p) => (p.value > 0 ? wan1(p.value) : '') }, data: vals.map((v) => Math.round(v)) }],
    });
    $('#' + id).dataset.vals = vals.map((v) => Math.round(v)).join(',');
  }
  function drawDet() {
    const box = $('#incDet'), r = (S._incR || []).find((x) => x.it.code === S.inc.det);
    if (!r) { disposeIn(box); box.hidden = true; box.innerHTML = ''; box.dataset.code = ''; return; }
    const lots = r.lots, cost = lots * 1000 * r.it.close;
    const mon = r.mm.m.map((x) => (x > 0 ? netOf(lots * x * 1000) : 0)), year = mon.reduce((p, q) => p + q, 0);
    if (box.dataset.code !== r.it.code || !$('#incDn', box)) {
      disposeIn(box);
      box.innerHTML = `<div class="dethd"><b>${fqBadge(r.it.freq)} ${esc(r.it.name)} ${esc(r.it.code)}</b>
        <button type="button" class="btn small" id="incDetCx">看複利試算 →</button><button type="button" class="btn small" id="incDetGo">個股頁 →</button><button type="button" class="btn small" id="incDetX" aria-label="收起細節">收起 ✕</button></div>
        <p class="incq" id="incDetQ"></p>
        <div class="cgrid"><div class="cleft"><div class="sth">投入本金 vs 一年領回</div><div id="incDn" class="chart dnbig"></div></div>
        <div class="cright"><div class="sth">一年 12 個月入帳（依發放月，單位：元）</div><div id="incMb" class="chart mbars"></div></div></div>`;
      $('#incDetX').onclick = () => openDet(null);
      $('#incDetGo').onclick = () => A().goStock(r.it.code);
      $('#incDetCx').onclick = () => { S.inc.obj = 's:' + r.it.code; S.inc.main = 'x'; LS.set('tw.etf.inc.main', 'x'); drawInc(); };
    }
    box.hidden = false; box.dataset.code = r.it.code;
    $('#incDetQ').innerHTML = `買 <b>${lots.toLocaleString()} 張・${ntw(cost)}</b>，依近 12 個月配息一年領 <b>${ntw(year)}</b>（殖利率 ${pctU(year / cost)}）；只靠配息約 <b>${year > 0 ? (cost / year).toFixed(1) : '—'} 年</b>領回本金（不計價格變動）。`;
    const a = A();
    const parts = [{ name: '一年領回', value: Math.round(year), color: a.donut.color(2) }, { name: '本金其餘', value: Math.max(0, Math.round(cost - year)), isOther: true }];
    donutBig('incDn', parts, { valLabel: '金額', centerLabel: '殖利率', centerValue: pctU(year / cost, 1), label: (p) => `${p.name} ${wan1(p.value)}` });
    monthBars('incMb', mon, null, (i) => `${i + 1} 月入帳 <b>${ntw(mon[i])}</b><br>${lots.toLocaleString()} 張 × 每單位 ${r.mm.m[i]} 元`);
  }

  /* ================= 月配試算表：組合 ================= */
  function clockOpt(c, S0) {
    const a = A(), CH = a.CH;
    const mx = Math.max(...c.mon), mn = Math.min(...c.mon);
    const data = c.mon.map((v, m) => {
      const by = c.by[m].map((x, i) => [x, i]).filter((x) => x[0] > 0).sort((p, q) => q[0] - p[0]);
      const mi = by.length ? by[0][1] : -1, col = mi >= 0 ? a.donut.color(mi) : CH.ink3;
      const al = mx > mn ? 0.6 + 0.4 * (v - mn) / (mx - mn) : 0.85;
      return { name: `${m + 1}月`, value: 1, amt: v, by, mi, itemStyle: { color: a.hexA(col, al) } };
    });
    return { data, option: {
      tooltip: { ...a.tip, confine: true, position: clampPos(a.donut.tipPosFor(0.5)), trigger: 'item', formatter: (p) => { const d = data[p.dataIndex];
        return `<b>${d.name}入帳 ${ntw(d.amt)}</b><br>` + d.by.map(([x, i]) => `${esc(c.mem[i].it.name)} ${c.mem[i].it.code}：${c.lots[i].toLocaleString()} 張 → ${ntw(x)}`).join('<br>'); } },
      title: a.donut.center('最低月', wan(c.min), S0, 0.5),
      series: [{ type: 'pie', radius: ['50%', '94%'], center: ['50%', '50%'], startAngle: 75, clockwise: true, padAngle: 1, minAngle: 0,
        itemStyle: { borderRadius: 4, borderColor: CH.panel, borderWidth: 1 }, avoidLabelOverlap: false, labelLine: { show: false },
        label: { show: true, position: 'inside', fontSize: 11, lineHeight: 14, color: '#fff', textBorderColor: 'rgba(0,0,0,.45)', textBorderWidth: 2, formatter: (p) => `${p.dataIndex + 1}月\n${wan1(data[p.dataIndex].amt)}` },
        emphasis: { scale: true, scaleSize: 4, itemStyle: { borderColor: CH.ink, borderWidth: 3 } }, data }],
    } };
  }
  /* ★ 18:50 剖析：整塊 innerHTML 換掉前要先 dispose 裡面的 ECharts 實例，不然舊實例（含 resize 監聽與畫布）留在記憶體——
     連切 50 次組合 A～E，JS heap 37→107MB 一路漲；這是「用久了變卡」的根因之一（見 docs/income_audit_1007.md）。 */
  function disposeIn(box) { if (!box || !window.echarts) return; box.querySelectorAll('[_echarts_instance_]').forEach((d) => { const c = window.echarts.getInstanceByDom(d); if (c) c.dispose(); }); }
  function drawIncCombos() {
    const C = combosNow(), box = $('#incCombos');
    S._incC2 = C;
    $('#incCQ').innerHTML = C.list.length ? `每月目標 <b>${wan(incMonT())}</b>${S.inc.mode === 'y' ? `（＝上方年領 ${wan(S.inc.year)} ÷ 12）` : ''}${S.inc.nhi ? '（扣健保後）' : ''}：從 ${C.pool} 檔候選裡找到 ${C.n.toLocaleString()} 種「12 個月都有配息」的 2～4 檔組合，${S.inc.csort === 'tr' ? `${esc(perLabel())}含息總報酬最高` : '總投入最少'}的前 ${C.list.length} 名分成 ${CMB.slice(0, C.list.length).join('／')} 分頁。`
      : '這個範圍找不到 12 個月都有配息的組合';
    if (S.inc.ci >= C.list.length) S.inc.ci = 0;
    $$('#incTabs button').forEach((b) => b.classList.toggle('on', S.inc.tab === 'c' ? b.dataset.i === String(S.inc.ci) : b.dataset.v === 's'));
    const c = C.list[S.inc.ci];
    if (!c) { box.innerHTML = '<div class="etfprep">無符合的組合</div>'; box.dataset.n = '0'; return; }
    const a = A(), clock = S.inc.cview !== 'grid', MN = Array.from({ length: 12 }, (_, i) => `${i + 1}月`);
    const mainOf = (m) => { const by = c.by[m].map((x, i) => [x, i]).filter((x) => x[0] > 0).sort((p, q) => q[0] - p[0]); return by.length ? by[0][1] : -1; };
    const cell = (m) => { const v = c.mon[m], mi = mainOf(m), col = mi >= 0 ? a.donut.color(mi) : '';
      return `<div class="mcell" style="--fc:${col}" data-m="${m + 1}" data-v="${Math.round(v)}"><small>${MN[m]}</small><b>${wan(v)}</b><span>${mi >= 0 ? esc(c.mem[mi].it.code) : ''}</span></div>`; };
    // v7（圖一轉置）：每一欄是一季（Q1～Q4），由上往下是那一季的 3 個月 ⇒ 3 排 × 4 欄，欄頭標 Q1～Q4
    const cells = ['Q1', 'Q2', 'Q3', 'Q4'].map((q) => `<div class="mqh">${q}</div>`).join('') + [0, 1, 2].map((r) => [0, 3, 6, 9].map((q) => cell(q + r)).join('')).join('');
    const rows = c.mem.map((x, i) => `<div class="cmr"><button type="button" class="cmn" data-code="${esc(x.it.code)}" title="進個股頁"><i style="background:${a.donut.color(i)}"></i>${esc(x.it.name)} ${esc(x.it.code)}</button>${fqBadge(x.it.freq)}
      <dl><dt>現價</dt><dd>NT$ ${A().fmt.n(x.it.close, 2)}</dd><dt>張數</dt><dd>${c.lots[i].toLocaleString()} 張</dd><dt>投入金額</dt><dd>${ntw(c.costs[i])}</dd><dt>一年領</dt><dd>${ntw(c.by.reduce((s, m) => s + m[i], 0))}</dd></dl></div>`).join('');
    disposeIn(box);
    box.innerHTML = `<div class="combo" data-ci="${S.inc.ci}" data-cost="${Math.round(c.cost)}" data-min="${Math.round(c.min)}" data-tr="${c.tr == null ? '' : c.tr}" data-codes="${c.mem.map((x) => x.it.code).join(',')}" data-lots="${c.lots.join(',')}" data-vals="${c.mon.map((v) => Math.round(v)).join(',')}">
      <div class="ch"><span class="rk">組合 ${CMB[S.inc.ci]}</span><span class="kp"><span>總投入<b>${ntw(c.cost)}</b></span><span>年領<b>${ntw(c.year)}</b></span><span>最低月<b>${ntw(c.min)}</b></span>
      <span>整體殖利率<b>${pctU(c.y)}</b></span><span>含息年化<b>${c.tr == null ? '—' : pct(c.tr, 2)}</b></span><button type="button" class="btn small" id="incToCx">看複利試算 →</button></span></div>
      <div class="c3"><div class="c3c"><div class="sth">總投入（各檔張數・金額）</div><div id="incCdn" class="chart dnbig"></div></div>
        <div class="c3c"><div class="sth c3h"><span>12 個月入帳${clock ? '時鐘（格色＝當月主要入帳那檔）' : '月曆（一欄一季）'}</span>${segH('incCView', [['clock', '時鐘'], ['grid', '月曆格']], S.inc.cview)}</div>
          ${clock ? '<div class="clk chart dnbig" id="incClk"></div>' : `<div class="mgrid q4" id="incGrid">${cells}</div>`}</div>
        <div class="c3c"><div class="sth">各檔明細</div><div class="cml" id="incCTbl">${rows}</div></div></div>
      <div class="sth">每月入帳（單位：萬；顏色＝當月主要入帳那檔）</div><div id="incCmb" class="chart mbars"></div></div>`;
    const parts = c.mem.map((x, i) => ({ name: `${x.it.name} ${x.it.code}`, value: Math.round(c.costs[i]), color: a.donut.color(i), lots: c.lots[i] }));
    donutBig('incCdn', parts, { valLabel: '投入', centerLabel: '總投入', centerValue: wan(c.cost), label: (p) => `${parts[p.dataIndex].lots.toLocaleString()} 張・${wan1(p.value)}` });
    $('#incCdn').dataset.labels = parts.map((p) => `${p.lots.toLocaleString()} 張・${wan1(p.value)}`).join('|');
    if (clock) {
      const el = $('#incClk'); el.style.height = DN + 'px';
      const ck = clockOpt(c, DN);
      a.chart('incClk', ck.option);
      el.dataset.n = '12'; el.dataset.cols = ck.data.map((d) => d.mi).join(',');
      const ch = window.echarts && window.echarts.getInstanceByDom(el);
      if (ch) { ch.off('mouseover'); ch.off('globalout');
        ch.on('mouseover', (p) => { try { ch.setOption({ title: a.donut.center(`${p.dataIndex + 1}月`, wan(c.mon[p.dataIndex]), DN, 0.5) }); } catch (e) { /* 競態 */ } });
        ch.on('globalout', () => { try { ch.setOption({ title: a.donut.center('最低月', wan(c.min), DN, 0.5) }); } catch (e) { /* 競態 */ } }); }
    }
    monthBars('incCmb', c.mon, (m) => { const mi = mainOf(m); return mi >= 0 ? a.donut.color(mi) : a.CH.ink3; },
      (m) => `<b>${m + 1} 月入帳 ${ntw(c.mon[m])}</b><br>` + c.mem.map((x, i) => [x, i]).filter(([, i]) => c.by[m][i] > 0).map(([x, i]) => `${esc(x.it.name)} ${x.it.code}：${c.lots[i].toLocaleString()} 張 → ${ntw(c.by[m][i])}`).join('<br>'));
    $$('#incCView button').forEach((b) => { b.onclick = () => { S.inc.cview = b.dataset.v; LS.set('tw.etf.inc.cview', S.inc.cview); drawIncCombos(); }; });
    $$('#incCTbl button[data-code]').forEach((b) => { b.onclick = () => twoTap('m' + b.dataset.code, () => A().goStock(b.dataset.code)); });
    $('#incToCx').onclick = () => { S.inc.obj = 'c:' + S.inc.ci; S.inc.main = 'x'; LS.set('tw.etf.inc.main', 'x'); drawInc(); };
    box.dataset.n = String(C.list.length);
  }
  /* v7（Andy：把組合 A～E 往上拉到「單檔 ETF」那一排）：分頁列＝單檔 ETF｜組合 A～E，停在單檔時也要知道 A～E 的投入金額，
     所以組合結果依「目標／範圍／健保／期間／排序」快取，切分頁不重算窮舉。 */
  function combosNow() {
    const N = incMonT(), k = [N, S.inc.scope, S.inc.nhi ? 1 : 0, perKey(), S.inc.csort, S.series ? 1 : 0].join('|');
    if (!S._cC || S._cC.k !== k || S._cC.d !== S.data) S._cC = { k, d: S.data, C: incCombosV2(N) };
    return S._cC.C;
  }
  function incTabsDraw() {
    const C = combosNow(), tabs = $('#incTabs'); if (!tabs) return;
    if (S.inc.ci >= C.list.length) S.inc.ci = 0;
    tabs.innerHTML = `<button type="button" role="tab" data-v="s"${S.inc.tab === 's' ? ' class="on"' : ''}>單檔 ETF</button>`
      + C.list.map((c, i) => `<button type="button" role="tab" data-v="c" data-i="${i}"${S.inc.tab === 'c' && i === S.inc.ci ? ' class="on"' : ''}>組合 ${CMB[i]}<small>投入 ${wan(c.cost)}</small></button>`).join('');
    $$('button', tabs).forEach((b) => { b.onclick = () => { S.inc.tab = b.dataset.v; LS.set('tw.etf.inc.tab', S.inc.tab); if (b.dataset.i != null) S.inc.ci = +b.dataset.i; drawInc(); }; });
  }
  /* v7（圖二：單檔直條被擠成左邊一條細縫）：圖在 hidden 的分頁裡初始化會量到 0 寬；分頁一顯示就把裡面每個 ECharts 實例 resize 一次。 */
  function reflow(sec) {
    if (!sec || !window.echarts) return;
    const go = () => sec.querySelectorAll('[_echarts_instance_]').forEach((d) => { const c = window.echarts.getInstanceByDom(d); if (c && d.clientWidth > 0) c.resize(); });
    requestAnimationFrame(go); setTimeout(go, 250);
  }
  function incCombosV2(N) {
    const save = S.inc.mon; S.inc.mon = N;
    try { return incCombos(); } finally { S.inc.mon = save; }
  }

  /* ================= 複利試算表 =================
     18:50：「圖表清單需並排，並且上方標籤需要連動下方圖表……情境拿掉，改用下面紅框處（圖例）點擊即可進行篩選」。
     → 左圖右表（約 2:1）；情境勾選列拿掉，線一律畫（原標的／0050／00631L／只領現金／只看價格＋自訂最多 5 檔），
       圖例點一下＝開關那條線（ECharts legend selected，記在 S.inc.lsel），右表與結論句只算「看得到的線」。
     「上方標籤沒連動」根因：對象下拉的選項文字寫的是張數，月配試算表改目標後，複利頁沿用舊的 S.inc.obj 索引（組合排名換了，c:0 指到不同組合，
       而下拉清單只在重畫時重建）；1／3／5 年按鈕是用「今天往回 N 年」比對亮燈，資料最後一天不是今天時不亮；起始日改完沒有重新同步按鈕。
       現在：每次重畫都重建下拉、對象改用代號組合字串當鍵、快捷鈕以 S.inc.xq 記住按了哪顆、起始日手改就清掉快捷亮燈。 */
  function cxObjects() {
    const C = incCombosV2(incMonT()), R = incSinglesV2(), out = [];
    C.list.forEach((c, i) => out.push({ v: 'c:' + c.mem.map((x) => x.it.code).join('+'), t: `組合 ${CMB[i]}：${c.mem.map((x, j) => `${x.it.code} ${c.lots[j]}張`).join('＋')}`, mems: c.mem.map((x, j) => ({ code: x.it.code, lots: c.lots[j] })) }));
    R.forEach((r) => out.push({ v: 's:' + r.it.code, t: `單檔：${r.it.name} ${r.it.code}（${r.lots.toLocaleString()} 張）`, mems: [{ code: r.it.code, lots: r.lots }] }));
    return out;
  }
  async function drawCx() {
    const objs = cxObjects(), sel = $('#cxObj');
    if (!objs.length) { $('#cxHead').textContent = '沒有可試算的對象'; return; }
    if (/^c:\d$/.test(S.inc.obj || '')) { const o = objs.filter((x) => x.v[0] === 'c')[+S.inc.obj.slice(2)]; S.inc.obj = o ? o.v : ''; }
    if (!objs.some((o) => o.v === S.inc.obj)) S.inc.obj = objs[0].v;
    sel.innerHTML = `<optgroup label="組合（月配試算表）">${objs.filter((o) => o.v[0] === 'c').map((o) => `<option value="${o.v}">${esc(o.t)}</option>`).join('')}</optgroup>`
      + `<optgroup label="單檔">${objs.filter((o) => o.v[0] === 's').map((o) => `<option value="${o.v}">${esc(o.t)}</option>`).join('')}</optgroup>`;
    sel.value = S.inc.obj;
    if (!S.inc.xfrom) { S.inc.xq = '5'; S.inc.xfrom = yrsAgo(todayTW(), 5); }
    $('#cxFrom').value = S.inc.xfrom;
    $$('#cxQuick button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.inc.xq));
    $('#cxChips').innerHTML = S.inc.cmp.map((c) => `<button type="button" class="chip cmpx" data-code="${esc(c)}" title="移除">再投入 ${esc(nameOf(c))} ${esc(c)} ✕</button>`).join('');
    $$('#cxChips .cmpx').forEach((b) => { b.onclick = () => { S.inc.cmp = S.inc.cmp.filter((c) => c !== b.dataset.code); drawCx(); }; });
    const obj = objs.find((o) => o.v === S.inc.obj), el = $('#cxChart'), tok = (el._tok = (el._tok || 0) + 1);
    el.dataset.state = 'loading';
    if (!S.series) await loadSeries();
    if (el._tok !== tok) return;
    const D = (S.series && S.series.D) || [];
    const A0 = obj.mems.map((m) => ({ ...m, a: alignEtf(m.code) }));
    const err = (t) => { $('#cxHead').textContent = t; holdEmpty('cxChart', t); $('#cxTbl').innerHTML = ''; el.dataset.state = 'err'; };
    if (!D.length || A0.some((m) => !m.a)) { err('這個對象沒有歷史走勢，無法回測'); return; }
    let i0 = D.findIndex((d) => d >= S.inc.xfrom); if (i0 < 0) { err('起始日晚於最新資料'); return; }
    while (i0 < D.length && !A0.every((m) => m.a.p[i0] != null)) i0++;
    if (i0 >= D.length - 3) { err('這段期間資料不足（對象上市較晚，請把起始日往後）'); return; }
    const ev = A0.map((m) => evOf(m.code, m.a));
    const keys = ['self', '0050', '00631L'].concat(S.inc.cmp);
    const runs = [];
    for (const key of keys) {
      const T = await rxSeries(key); if (el._tok !== tok) return;
      if (!T) continue;
      runs.push({ key, name: key === 'self' ? '再投入原標的' : `再投入 ${nameOf(key)} ${key}`.replace(/\s+/g, ' '),
        r: simCore(D, A0.map((m, j) => ({ shares: m.lots * 1000, px: m.a.p, ev: ev[j], T: T === 'self' ? m.a.t : T })), i0, S.inc.nhi) });
    }
    if (!runs.length) { err('無法計算'); return; }
    const base = runs[0].r, cost = base.cost, last = D.length - 1, pctA = (arr) => arr.map((v) => (v == null ? null : +((v / cost - 1) * 100).toFixed(2)));
    const a = A(), CH = a.CH, cols = [0, 1, 5, 2, 3, 4, 6, 7].map((i) => a.donut.color(i));
    const lines = runs.map((x, i) => ({ key: x.key, name: x.name, col: cols[i], vals: pctA(x.r.tot), fin: x.r.tot[last] }));
    lines.push({ key: 'cash', name: '只領現金（不投入）', col: CH.ink2, dash: 'dashed', vals: pctA(base.cash), fin: base.cash[last] });
    lines.push({ key: 'price', name: '只看價格（不含息）', col: CH.ink3, dash: 'dotted', vals: pctA(base.price), fin: base.price[last] });
    S.inc.lsel = S.inc.lsel || {};
    const shown = () => lines.filter((l) => S.inc.lsel[l.key] !== false);
    const X = D.slice(i0);
    const ser = lines.map((l) => ({ name: l.name, type: 'line', showSymbol: false, data: l.vals.slice(i0), lineStyle: { width: l.key === 'self' ? 2.2 : 1.5, color: l.col, type: l.dash || 'solid' }, itemStyle: { color: l.col },
      emphasis: { focus: 'series' }, endLabel: { show: true, color: l.col, fontSize: 11.5, formatter: (p) => (p.value == null ? '' : (p.value > 0 ? '+' : '') + (+p.value).toFixed(1) + '%') }, labelLayout: { moveOverlap: 'shiftY' } }));
    /* v8（Andy：「曲線圖月份之間都要微微線條區隔」）：每月第一週畫一條很淡的直線（markLine 掛在第一條線上、不吃滑鼠）。
       這張圖有 dataZoom，不走全站 TimeGrid（timeGrid:false），所以自己畫。 */
    const mk = X.map((d, k) => (k > 0 && d.slice(0, 7) !== X[k - 1].slice(0, 7) ? { xAxis: d } : null)).filter(Boolean);
    if (ser[0]) ser[0].markLine = { silent: true, symbol: ['none', 'none'], label: { show: false }, emphasis: { disabled: true }, animation: false, lineStyle: monthLine(a), data: mk };
    el.dataset.mlines = String(mk.length);
    const selected = {}; lines.forEach((l) => { selected[l.name] = S.inc.lsel[l.key] !== false; });
    a.chart('cxChart', {
      timeGrid: false,
      grid: { left: 8, right: 64, top: el.clientWidth < 600 ? 104 : 64, bottom: 56, containLabel: true },   // v6：窄寬圖例換成三列，top 加大才不會壓到 y 軸名稱「報酬率 %」
      legend: { type: 'plain', top: 0, left: 0, right: 0, itemWidth: 16, itemHeight: 3, selected, textStyle: { color: CH.ink2, fontSize: 12 }, selectedMode: true, inactiveColor: a.hexA(CH.ink3, 0.45) },
      // v8：提示框放在滑鼠左／右側、貼圖頂（不壓在線上），confine 不出圖框
      tooltip: { ...a.tip, confine: true, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: CH.ink3 } },
        position: (pt, _p, _d, _r, sz) => [pt[0] > sz.viewSize[0] / 2 ? Math.max(0, pt[0] - sz.contentSize[0] - 18) : pt[0] + 18, 70],
        formatter: (ps) => { const i = ps[0].dataIndex, d = X[i]; el.dataset.tip = d + '|' + ps.map((p) => p.value).join(',');
          return `<b>${d}</b><br>` + ps.slice().sort((p, q) => (q.value || 0) - (p.value || 0)).map((p) => {
            const v = p.value == null ? null : cost * (1 + p.value / 100);
            return `${p.marker}${esc(p.seriesName)}：<b>${p.value == null ? '—' : (p.value > 0 ? '+' : '') + (+p.value).toFixed(1) + '%'}</b>（${ntw(v)}）`; }).join('<br>'); } },
      xAxis: monthAxis(X, a),
      // v8：y 軸貼緊資料（上下各留 4% 再取整 5），不再從 −10%／−30% 留一大段空白
      yAxis: { type: 'value', scale: true, name: '報酬率 %', min: (v) => Math.floor((v.min - Math.min(3, (v.max - v.min) * 0.02)) / 5) * 5, max: (v) => Math.ceil((v.max + Math.min(3, (v.max - v.min) * 0.02)) / 5) * 5, nameTextStyle: { color: CH.ink3, fontSize: 11, align: 'left' }, ...a.axisStyle, splitLine: { lineStyle: { color: CH.grid } },
        axisLabel: { ...a.axisStyle.axisLabel, fontSize: 11, formatter: (v) => v + '%' } },
      dataZoom: [{ type: 'inside', xAxisIndex: 0, zoomOnMouseWheel: true, moveOnMouseMove: true, minValueSpan: 8 },
        { type: 'slider', xAxisIndex: 0, height: 18, bottom: 6, labelFormatter: (i) => X[i] || '' }],
      series: ser,
    });
    const pctF = (v) => (v > 0 ? '+' : '') + (v * 100).toFixed(1) + '%';
    const yrs = (Date.parse(D[last]) - Date.parse(D[i0])) / (365.25 * 864e5);
    const cashFin = base.cash[last];
    const paint = () => {
      const vis = shown(), vr = vis.filter((l) => l.key !== 'cash' && l.key !== 'price');
      const best = vr.slice().sort((p, q) => q.fin - p.fin)[0], pr = vis.find((l) => l.key === 'price'), ca = vis.find((l) => l.key === 'cash');
      $('#cxHead').innerHTML = `從 <b>${D[i0]}</b> 至 ${D[last]}（本金 ${ntw(cost)}）：`
        + [pr ? `只持有、不算配息成長 <b>${pctF(pr.fin / cost - 1)}</b>` : '', ca ? `把配息領出來 <b>${pctF(cashFin / cost - 1)}</b>` : '',
          best ? `配息<b>${esc(best.name)}</b>為 <b>${pctF(best.fin / cost - 1)}</b>，比只領現金多 <b>${((best.fin - cashFin) / cost * 100).toFixed(1)} 個百分點</b>` : ''].filter(Boolean).join('；') + '。';
      const row = (l) => { const v = l.fin, r = v / cost - 1, ann = yrs > 0.2 ? Math.pow(v / cost, 1 / yrs) - 1 : null, pp = (v - cashFin) / cost * 100;
        return `<tr data-key="${esc(l.key)}"><td class="nm"><i style="background:${l.col}"></i>${esc(l.name)}</td><td>${wan(v)}</td><td><span class="${cls(r)}">${pctF(r)}</span></td><td>${l.key === 'cash' ? '—' : `<span class="${cls(pp)}">${pp > 0 ? '+' : ''}${pp.toFixed(1)} 個百分點</span>`}</td><td>${ann == null ? '—' : `<span class="${cls(ann)}">${pctF(ann)}</span>`}</td></tr>`; };
      $('#cxTbl').innerHTML = `<thead><tr><th class="nm">情境</th><th>期末總資產</th><th>報酬率</th><th>比只領現金多</th><th>年化</th></tr></thead><tbody>${vis.map(row).join('')}</tbody>`;
      $('#cxLev').hidden = !vis.some((l) => l.key === '00631L' || LEV_RE.test(nameOf(l.key)));
      el.dataset.shown = vis.map((l) => l.key).join(',');
    };
    paint();
    const ch = window.echarts && window.echarts.getInstanceByDom(el);
    if (ch) { ch.off('legendselectchanged'); ch.on('legendselectchanged', (e) => { lines.forEach((l) => { S.inc.lsel[l.key] = e.selected[l.name] !== false; }); paint(); }); }
    el.dataset.lines = lines.map((l) => l.key).join(',');
    el.dataset.fin = lines.map((l) => +(l.fin / cost - 1).toFixed(4)).join(',');
    el.dataset.from = D[i0]; el.dataset.cost = String(Math.round(cost)); el.dataset.obj = S.inc.obj;
    el.dataset.state = 'ok';
  }

  /* ------------------------------------------------------------------ 入口 */
  function drawAll() {
    drawCats();
    const inc = S.view === 'inc', cal = S.view === 'cal', cat = S.view === 'cat';
    $('#etfCalCard').hidden = !cal; $('#etfCatBar').hidden = !cat; $('#etfBody').hidden = cal;
    $('#etfInc').hidden = !inc; $('#etfRetCard').hidden = !cat; $('#etfListCard').hidden = !cat;
    const tri = $('#etfTri'); tri.hidden = !cat || !!NO_RANK[S.cat];
    $('#v-etf').dataset.view = S.view;
    if (cal) return;
    if (inc) { drawInc(); return; }
    if (!tri.hidden) { drawPop(); drawRetTop(); drawYld(); }
    drawRet(); drawList();
    $('#v-etf').dataset.cat = S.cat;
  }
  /* 子分頁：hash 的第二段 → S.view。分類頁籤點下去會把 S.view 設成 'cat'，所以從試算點分類頁籤也會回到總覽。 */
  function show(sub) {
    const v = VIEW_OF[sub] || 'cat';
    if (!document.getElementById('etfSub')) { S._sub = sub; return; }
    if (S.view === v && $('#v-etf').dataset.view === v) return;
    S.view = v; drawAll();
    if (window.echarts) setTimeout(() => $$('#v-etf [_echarts_instance_]').forEach((d) => { const c = window.echarts.getInstanceByDom(d); if (c && d.clientWidth > 0) c.resize(); }), 30);
  }
  async function render(sub) {
    injectCSS();
    const root = document.getElementById('v-etf'); if (!root) return;
    S.cat = '配息型'; S.view = VIEW_OF[sub] || 'cat'; S.pop = LS.get('tw.etf.pop', 'holders');
    S.per = LS.get('tw.etf.per', '5y'); if (!PERS.some((x) => x[0] === S.per)) S.per = '5y';
    S.cfrom = LS.get('tw.etf.cfrom', '') || yrsAgo(todayTW(), 3); S.cto = todayTW(); S.basis = LS.get('tw.etf.basis', 'tr'); S.cmp = {};
    try { await window.CalGrid.load(); } catch (e) { /* 沒有休市日只標週末 */ }
    skeleton(root);
    $('#etfSort').onchange = (e) => { S.sort = e.target.value; S.shown = PAGE; drawList(); };
    $('#etfGrid').innerHTML = '<div class="etfprep">載入中…</div>';
    await loadData();
    if (!S.fallback) loadSeries().then(() => { if (S.view === 'inc') drawInc(); else { drawRetTop(); drawRet(); } });
    if (!items().some((it) => it.cat === S.cat)) S.cat = (CATS.find((c) => items().some((it) => it.cat === c)) || S.cat);
    drawCal(); drawAll();
    root.dataset.ready = S.fallback ? 'fallback' : 'full';
  }
  window.TwEtfPage = { render, show, classify, state: S, simCore };
})();
