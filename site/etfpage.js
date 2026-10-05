/* ============================================================================
   ETF 專區（#etf）—— Andy 2026-10-05（參考別家 ETF 專區的截圖，名稱與版面自己做）
   規格與每個數字的口徑：docs/etf_page_spec.md（分類規則、熱門定義、殖利率、年化報酬、填息天數）。

   版面（2026-10-05 第二版，Andy：「配息行事曆放最上面」「每個分類頁內並排前 5」「自選比較清單」）：
     ① 配息行事曆（7 欄真月曆，格內直接寫當天除息的代號與金額，點格子右側展開當天清單＋填息天數）
     ② 分類分頁列（全部／配息型／市值型／…）＋期間（3／5／10 年／自訂，只影響報酬率）
     ③ 分類分頁才有、三張同高並排：最近最受歡迎前 5｜報酬率前 5（含息年化）｜殖利率前 5（附平均填息天數）
        「全部」與「其他」不出這三張（Andy：「其他 ETF 的不用」）。
     ④ 報酬比較（自選）：「加入比較」可搜尋多選（限該分類、上限 8 檔、預設報酬前 5），依分類分開記在 localStorage
     ⑤ ETF 一覽（卡片清單，點卡片進個股頁）
   舊版的「前五名報酬比較」（只有配息型／市值型兩組）整張由 ③④ 取代。

   資料：data/etf.json（開頁就讀）＋ data/etf_series.json（全部 ETF 的週線走勢，自選比較才讀）。
   ⚠ 預覽分支吃的是正式站的資料，etf.json 上正式站之前不存在 —— 那時退回 stocks.json（ETF 也在裡面）
     列出卡片清單與名稱分類，其他卡明確標「資料準備中」，不留空白、不編數字。
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
  const CATS = ['配息型', '市值型', '主題型', '債券型', '槓桿反向', '主動式', '其他'];
  const NO_RANK = { all: 1, 其他: 1, 槓桿反向: 1 };   // 不出「前 5 名」三張卡的分頁（Andy：「其他 ETF 的不用」；10-05 再加槓桿反向：「這兩個都比較少人做」）
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

  const S = { data: null, series: null, fallback: false, cat: 'all', sort: 'tv', shown: PAGE, pop: 'holders',
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
#v-etf .etfdisc{display:flex;gap:8px;align-items:flex-start;padding:10px 14px;border:1px solid var(--line-2);border-left:3px solid var(--amber);
  border-radius:10px;background:var(--panel-2);color:var(--ink-2);font-size:13px;line-height:1.55;margin-bottom:var(--sp-3)}
#v-etf .etfdisc b{color:var(--ink)}
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
#v-etf .etfcatbar{display:flex;align-items:center;gap:10px;margin:0 0 var(--sp-3);white-space:nowrap;min-width:0}
#v-etf .etfcatbar .seg{overflow:hidden;flex:0 1 auto;min-width:0}
#v-etf .etfcatbar .sp{flex:1}
#v-etf .etfper{display:flex;align-items:center;gap:8px;flex:none}
#v-etf .etfper.off{visibility:hidden}
#v-etf .etfper .lb{font-size:12.5px;color:var(--ink-3)}
#v-etf #etfFrom.inv{visibility:hidden}
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
#v-etf .etag.lime{color:var(--lime)} #v-etf .etag.up{color:var(--up)} #v-etf .etag.ink3{color:var(--ink-3)}
#v-etf .up{color:var(--up)} #v-etf .down{color:var(--down)} #v-etf .flat{color:var(--ink-2)}
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
#v-etf .rettw{min-height:${34 + CMP_MAX * 33}px;margin-top:10px;overflow-x:auto}
#v-etf .rettw table.et{min-width:960px}
#v-etf .cmpmsg{font-size:12.5px;color:var(--amber);width:150px;overflow:hidden;text-overflow:ellipsis}
#v-etf #etfCmpDD .ddbtn{max-width:230px}
#v-etf select.etsel{height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font:inherit;font-size:13px}
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
  const byCode = () => { const m = new Map(); items().forEach((it) => m.set(it.code, it)); return m; };
  const inCat = () => items().filter((it) => it.cat === S.cat);
  const sizeKey = (it) => (it.size != null ? it.size : -1) * 1e3 + ((it.tv20 || 0) / 1e12);

  /* ------------------------------------------------------------------ 骨架 */
  function skeleton(root) {
    const how = (k, q, li) => `<div class="howtxt" id="how-${k}" hidden>${A().howHTML(q, li)}</div>`;
    const hbtn = (k, t) => `<button class="howbtn pop" data-how="${k}" data-ttl="${t}" type="button" aria-label="${t}">?</button>`;
    root.innerHTML = `
<div class="etfdisc" id="etfDisc" role="note"><span aria-hidden="true">ⓘ</span><div><b>本頁僅為公開資料整理與統計，非投資顧問、不構成任何投資建議或推薦。</b>
過去績效不代表未來報酬；殖利率與報酬率依下方各卡「?」寫明的口徑計算，資料不足的一律標「無資料」，不以 0 或推估代替。</div></div>

<div class="card" id="etfCalCard">
  <div class="row spread"><h3>配息行事曆 <small id="etfCalSub"></small> ${hbtn('etfcal', '配息行事曆怎麼看')}</h3></div>
  ${how('etfcal', '這張回答：這個月哪幾天有 ETF 除息、各配多少、多久填息？', [
    '格子裡直接寫當天除息的 ETF 代號與每單位配息（元）；超過 2 檔只列前 2 檔，其餘寫「+N 檔」。藍框＝今天。',
    '點有除息的格子，右邊列出那天每一檔的配息金額、當次殖利率、發放日與<b>填息天數</b>；再點一次回到整月清單。',
    '<b>當次殖利率</b>＝該次配息 ÷ 除息前一個交易日收盤；尚未除息的（未來日期）改用最新收盤估算，標「估」。',
    '<b>填息天數</b>＝從除息日當天算第 1 個交易日，收盤第一次回到「除息前一日收盤」是第幾個交易日（與個股除權息分頁同一口徑）。還沒回到的寫「尚未填息（已 N 天）」，還沒除息或行情不足的寫「—」。',
    '所以：想領某一次的息，要在除息日「前一個交易日」收盤前持有；發放日才是錢入帳的日子。填息天數短＝除息後股價很快補回，長或尚未填息＝領到的息被價差吃掉。',
    '資料：FinMind 股利公告（TaiwanStockDividend）與除權息結果，逐檔回補進資料湖；沒回補到的 ETF 不會出現在月曆上。'])}
  <div id="etfCal"></div>
</div>

<div class="etfcatbar" id="etfCatBar">
  <div class="seg" id="etfCatSeg" role="tablist" aria-label="ETF 分類"></div><span class="sp"></span>
  <div class="etfper" id="etfPerBox"><span class="lb">報酬率期間</span>
    <div class="seg" id="etfPerSeg"><button data-v="3y">3 年</button><button data-v="5y">5 年</button><button data-v="10y">10 年</button><button data-v="custom">自訂</button></div>
    <select id="etfFrom" class="etsel inv" aria-label="自訂起始年"></select></div>
</div>

<div class="etftri" id="etfTri" hidden>
  <div class="card" id="etfPopCard">
    <div class="row spread"><h3>最近最受歡迎前 5 ${hbtn('etfpop', '最受歡迎怎麼算')}</h3>
      <div class="seg" id="etfPopSeg"><button data-v="holders">受益人週增</button><button data-v="turnover">成交值</button></div></div>
    ${how('etfpop', '這張回答：這一類裡，最近人潮與錢往哪幾檔去？', [
      '<b>受益人週增</b>：集保結算所每週公布的受益人數（合計列），最新一週減前一週，增加最多的前 5 檔。代表「新進場的人」。',
      '<b>成交值</b>：最近 20 個交易日成交金額的平均。代表「交易熱度」。',
      '只在目前這個分類裡排；所以：兩個口徑都在前面的，是人潮與交易都熱的。點一列進個股頁看 K 線。'])}
    <p class="etfq" id="etfPopSub"></p>
    <div class="rklist" id="etfPop"></div>
  </div>
  <div class="card" id="etfRetTopCard">
    <div class="row spread"><h3>報酬率前 5 <small id="etfRetTopSub"></small> ${hbtn('etfrettop', '報酬率前 5 怎麼排')}</h3></div>
    ${how('etfrettop', '這張回答：這一類裡，長期抱下來（含配息再投入）誰報酬最高？', [
      '依<b>含息總報酬年化</b>由高到低排（配息在除息日以當天收盤再投入）。期間跟著上方「報酬率期間」3／5／10 年／自訂。',
      '期間內上市未滿、或價量歷史還沒回補的不排進來（不拿短期數字跟長期比）。',
      '整個分類都還沒有配息資料時，暫依<b>價格年化（不含息）</b>排，卡片上會寫明，不拿價格報酬冒充含息報酬。',
      '所以：先看這裡誰長期最好，再到下面「報酬比較」把想比的幾檔勾進去看走勢。'])}
    <p class="etfq" id="etfRetTopQ"></p>
    <div class="rklist" id="etfRetTop"></div>
  </div>
  <div class="card" id="etfYldCard">
    <div class="row spread"><h3>殖利率前 5 <small>近 12 個月</small> ${hbtn('etfyld', '殖利率前 5 怎麼看')}</h3></div>
    ${how('etfyld', '這張回答：這一類裡，誰配得最多？配完多久填息？', [
      '<b>殖利率</b>＝近 12 個月現金配息合計 ÷ 最新收盤。只看現金配息，不受上方期間影響。',
      '<b>平均填息</b>＝最近 4 次已除息裡「已經填息」那幾次的填息天數平均（交易日）；還沒填息的不算進平均，另外寫「N 次未填」。完全沒有填過的寫「尚未填息」。',
      '填息天數口徑：除息日當天算第 1 天，收盤第一次回到除息前一日收盤是第幾個交易日（與個股除權息分頁相同）。',
      '所以：殖利率高但填息慢（或尚未填息），代表配的息常被除息後的價差吃掉，實拿的報酬沒有殖利率看起來那麼高。'])}
    <p class="etfq" id="etfYldQ">回答：<b>誰配得最多？配完多久填息？</b></p>
    <div class="rklist" id="etfYld"></div>
  </div>
</div>

<div class="card" id="etfRetCard">
  <div class="row spread"><h3>報酬比較 <small id="etfRetSub"></small> ${hbtn('etfret', '報酬比較的口徑')}</h3>
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
  ${how('etfret', '這張回答：我挑的這幾檔，長期抱下來誰報酬好？配息算進去差多少？', [
    '用右上「加入比較」挑這個分類裡的 ETF（可搜尋、最多 8 檔）；沒挑過時預設是「報酬率前 5」。每個分類各自記住你挑的。',
    '<b>價格年化（不含息）</b>＝(期末收盤 ÷ 期初收盤)^(1/年數) − 1；分割（例：0050 2025-06 一拆四）已還原，配息不算進去。',
    '<b>含息年化</b>＝配息在除息日以當天收盤再投入（還原權值）後的年化報酬。<b>殖利率</b>＝近 12 個月現金配息 ÷ 最新收盤。',
    '<b>配息年化</b>＝(1 ＋ 期間累計配息 ÷ 期初收盤)^(1/年數) − 1：只看配息本身每年貢獻多少。',
    '期間：跟著上方「報酬率期間」。<b>上市未滿</b>或湖裡沒有那段歷史的，一律標「上市未滿 N 年／價量歷史尚未回補」，不以 0 或外插代替。',
    '所以：左圖看一路走勢（同起點 = 0%），右圖直接比年化數字；含息與不含息差距越大，代表報酬越依賴配息。'])}
  <p class="etfq" id="etfRetQ">回答：<b>我挑的這幾檔，長期抱下來誰報酬好？配息算進去差多少？</b></p>
  <div id="etfRetBody"></div>
</div>

<div class="card" id="etfListCard">
  <div class="row spread"><h3>ETF 一覽 <small id="etfCount"></small> ${hbtn('etflist', 'ETF 分類與欄位')}</h3>
    <div class="etfrow"><label class="note" for="etfSort">排序</label>
      <select id="etfSort" class="etsel"><option value="tv">成交值</option><option value="size">規模</option><option value="yield">殖利率</option><option value="chg">今日漲跌</option></select></div></div>
  ${how('etflist', '這張回答：有哪些 ETF、各是哪一型、殖利率多少？', [
    '<b>分類</b>（依序判斷，先符合先歸類）：槓桿反向（代號尾 L/R 或名稱含 正2／反1）→ 債券型（尾 B 或名稱含「債」）→ 其他（期貨／商品／貨幣，尾 U 或「期」開頭）→ 主動式（尾 A）→ 市值型（名稱含 台灣50、台50、中型100、加權、MSCI台灣、摩台）→ 配息型（名稱含 高股息／高息／股息／收益／優息…，或近 400 天除息 ≥ 4 次）→ 其餘股票型為主題型。',
    '<b>殖利率</b>＝近 12 個月現金配息合計 ÷ 最新收盤。<b>配息頻率</b>＝近 400 天除息次數（≥10 月配、≥3 季配、2 半年配、1 年配）。',
    '<b>規模</b>＝集保受益權單位數 × 收盤（估算值，不是投信公告的基金淨資產）。<b>成交值</b>＝近 20 日平均。',
    '所以：先用上方分類切出同一型，再用「殖利率」或「規模」排序比較；點卡片進個股頁看 K 線與除權息。'])}
  <p class="etfq">回答：<b>現在有哪些 ETF、各是哪一型、殖利率多少？</b> <span id="etfFbNote"></span></p>
  <div class="etfgrid" id="etfGrid"></div>
  <div class="etfmore"><button type="button" class="btn small" id="etfMore" hidden>顯示更多</button></div>
</div>`;
  }

  /* ------------------------------------------------------------------ 分類列（全頁共用） */
  function drawCats() {
    const all = items();
    const cnt = {}; all.forEach((it) => { cnt[it.cat] = (cnt[it.cat] || 0) + 1; });
    const seg = $('#etfCatSeg');
    seg.innerHTML = `<button data-v="all" role="tab">全部 ${all.length}</button>` + CATS.filter((c) => cnt[c])
      .map((c) => `<button data-v="${c}" role="tab">${c} ${cnt[c]}</button>`).join('');
    $$('button', seg).forEach((b) => { b.classList.toggle('on', b.dataset.v === S.cat); b.setAttribute('aria-selected', b.dataset.v === S.cat);
      b.onclick = () => { if (S.cat === b.dataset.v) return; S.cat = b.dataset.v; S.shown = PAGE; LS.set('tw.etf.cat', S.cat); drawAll(); }; });
    // 期間只影響報酬率：「全部」沒有報酬卡，期間整組隱形但保留位置（不讓分類鈕跟著左右跳）
    $('#etfPerBox').classList.toggle('off', S.cat === 'all');
    $$('#etfPerSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.per);
      b.onclick = () => { S.per = b.dataset.v; LS.set('tw.etf.per', S.per); drawPer(); drawRetTop(); drawRet(); }; });
    drawPer();
  }
  function drawPer() {
    $$('#etfPerSeg button').forEach((b) => b.classList.toggle('on', b.dataset.v === S.per));
    const sel = $('#etfFrom');
    const years = Object.keys((S.data && S.data.periods) || {}).filter((k) => k[0] === 'Y').map((k) => k.slice(1)).sort();
    if (!S.from && years.length) S.from = years[Math.max(0, years.length - 6)];
    sel.innerHTML = years.map((y) => `<option value="${y}"${y === S.from ? ' selected' : ''}>${y} 年起～至今</option>`).join('')
      || '<option value="">（無資料）</option>';
    sel.classList.toggle('inv', S.per !== 'custom');
    sel.onchange = () => { S.from = sel.value; drawRetTop(); drawRet(); };
  }
  function perKey() { return S.per === 'custom' ? 'Y' + (S.from || '') : S.per; }
  function perLabel(short) {
    const st = ((S.data && S.data.periods) || {})[perKey()];
    const nm = S.per === 'custom' ? `${S.from || '?'} 年起` : { '3y': '近 3 年', '5y': '近 5 年', '10y': '近 10 年' }[S.per];
    return st && !short ? `${nm}（${st}～${S.data.asof}）` : nm;
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
    return `<button type="button" class="etfc" data-code="${esc(it.code)}" title="進 ${esc(it.name)} 個股頁">
  <div class="h"><span class="nm">${esc(it.name)}</span><span class="cd">${esc(it.code)}</span><span class="sp" style="flex:1"></span>
    <span class="etag ${CAT_TONE[it.cat] || 'ink3'}">${esc(it.cat)}</span></div>
  <div class="px"><b class="${cls(it.chg_pct)}" data-live="close" data-code="${esc(it.code)}">${it.close != null ? A().fmt.n(it.close, 2) : '—'}</b>
    <span class="${cls(it.chg_pct)}" data-live="chg" data-code="${esc(it.code)}">${it.chg_pct != null ? A().fmt.pct(it.chg_pct, 2) : '—'}</span>
    <span class="sp"></span>${spark(it.code)}</div>
  <dl><dt>成交值${it.tv20 != null ? '（20日均）' : ''}</dt><dd>${yi(it.tv20 != null ? it.tv20 : it.tv)}</dd>
      <dt>殖利率</dt><dd>${y}</dd><dt>配息頻率</dt><dd>${esc(fq)}</dd><dt>規模（估）</dt><dd>${yi(it.size)}</dd></dl>
</button>`;
  }
  function drawList() {
    const list = items().filter((it) => S.cat === 'all' || it.cat === S.cat).sort((a, b) => sortVal(b) - sortVal(a));
    $('#etfCount').textContent = `${S.cat === 'all' ? '全部' : S.cat} ${list.length} 檔${S.data.asof ? '・資料日 ' + S.data.asof : ''}`;
    const g = $('#etfGrid');
    g.innerHTML = list.slice(0, S.shown).map(cardHTML).join('') || '<div class="etfprep">這個分類目前沒有 ETF。</div>';
    $$('.etfc', g).forEach((c) => { c.onclick = () => A().goStock(c.dataset.code); });
    const more = $('#etfMore'); more.hidden = list.length <= S.shown;
    more.textContent = `顯示更多（還有 ${Math.max(0, list.length - S.shown)} 檔）`;
    more.onclick = () => { S.shown += PAGE; drawList(); };
    $('#etfFbNote').innerHTML = S.fallback
      ? '<span class="note">（ETF 專區資料準備中：目前依名稱暫分，殖利率／配息頻率／規模待資料產出後顯示）</span>' : '';
    g.dataset.n = String(Math.min(list.length, S.shown)); g.dataset.cat = S.cat;
  }

  /* ------------------------------------------------------------------ 2. 分類內前 5 名（三張同高） */
  // 一列：名次｜名稱 代號｜主數字｜副數字。不足 5 列補隱形列，三張卡永遠一樣高。
  function rkRows(box, rows) {
    const hd = rows.head ? `<div class="rkhd"><span></span><span>ETF</span><span>${rows.head[0]}</span><span>${rows.head[1]}</span></div>` : '';
    const body = rows.list.map((r, i) => `<button type="button" class="rkrow" data-code="${esc(r.it.code)}" title="${esc(r.title || '進 ' + r.it.name + ' 個股頁')}">
      <span class="rk">${i + 1}</span><span class="nm">${esc(r.it.name)}<span class="cd">${esc(r.it.code)}</span></span>
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
    $('#etfPopSub').innerHTML = S.pop === 'holders' ? `口徑：集保受益人數 <b>${esc(wk[0] || '?')} → ${esc(wk[1] || '?')}</b> 的增減`
      : '口徑：<b>近 20 個交易日</b>平均成交值';
    if (S.fallback) { rkPrep(box, '資料準備中：排行要等下一次資料產出（etf.json）後才有。'); return; }
    const key = S.pop === 'holders' ? 'd_holders' : 'tv20';
    const L = inCat().filter((it) => it[key] != null).sort((a, b) => b[key] - a[key]).slice(0, 5);
    if (!L.length) { rkPrep(box, S.pop === 'holders' ? '這個分類目前沒有受益人數資料（集保至少要兩週才算得出週增加）。' : '這個分類目前沒有成交值資料。'); return; }
    rkRows(box, { head: S.pop === 'holders' ? ['受益人週增', '今日漲跌'] : ['日均成交值', '今日漲跌'],
      list: L.map((it) => ({ it,
        v: S.pop === 'holders' ? `${it.d_holders > 0 ? '+' : ''}${A().fmt.i(it.d_holders)}` : yi(it.tv20),
        vc: S.pop === 'holders' ? cls(it.d_holders) : '',
        v2: it.chg_pct != null ? A().fmt.pct(it.chg_pct, 2) : '—', v2c: cls(it.chg_pct) })) });
  }
  /* 報酬率排行：分類內、這個期間有完整資料的，依含息年化排；整類都沒有配息資料才暫依價格年化（並寫明）。*/
  function retRank() {
    const pk = perKey();
    const L = inCat().map((it) => ({ it, st: ((it.stats || {})[pk]) || null })).filter((x) => x.st && x.st.ok);
    const anyTr = L.some((x) => x.st.tr_ann != null);
    const key = anyTr ? 'tr_ann' : 'price_ann';
    const R = L.filter((x) => x.st[key] != null).sort((a, b) => b.st[key] - a.st[key]);
    return { rows: R, key, nOk: L.length, nNoTr: anyTr ? L.length - R.length : 0 };
  }
  function drawRetTop() {
    const box = $('#etfRetTop'); if (!box || NO_RANK[S.cat]) return;
    $('#etfRetTopSub').textContent = perLabel(true);
    const q = $('#etfRetTopQ');
    if (S.fallback) { q.innerHTML = '回答：<b>長期抱下來誰報酬最高？</b>'; rkPrep(box, '資料準備中：報酬率要等 ETF 專區資料產出後才有。'); return; }
    const R = retRank();
    q.innerHTML = R.key === 'tr_ann'
      ? `依<b>含息年化</b>排${R.nNoTr ? `（${R.nNoTr} 檔配息資料尚未取得，未列入）` : ''}`
      : '<b>配息資料尚未取得</b>：暫依價格年化（不含息）排';
    if (!R.rows.length) {
      rkPrep(box, `這段期間沒有任何一檔有完整資料（上市未滿或價量歷史尚未回補；這一類有 ${inCat().length} 檔）。`); return;
    }
    rkRows(box, { head: R.key === 'tr_ann' ? ['含息年化', '不含息'] : ['價格年化', '期間'],
      list: R.rows.slice(0, 5).map(({ it, st }) => ({ it,
        v: pct(st[R.key], 2), vc: cls(st[R.key]),
        v2: R.key === 'tr_ann' ? pct(st.price_ann, 1) : `${st.years} 年`, v2c: R.key === 'tr_ann' ? cls(st.price_ann) : '' })) });
  }
  function drawYld() {
    const box = $('#etfYld'); if (!box || NO_RANK[S.cat]) return;
    if (S.fallback) { rkPrep(box, '資料準備中：殖利率要等 ETF 專區資料產出後才有。'); return; }
    const L = inCat().filter((it) => it.yield_ttm != null).sort((a, b) => b.yield_ttm - a.yield_ttm).slice(0, 5);
    if (!L.length) {
      rkPrep(box, '配息資料尚未取得：這一類的 ETF 除息紀錄還在回補（歷史回補排程的 ETF 步驟），補進資料湖後這裡會自動出現。'); return;
    }
    const fillCell = (it) => {
      if (it.fill_avg != null) return { v: `${it.fill_avg} 天`, t: `近 ${it.fill_n} 次除息：已填息的平均 ${it.fill_avg} 天${it.fill_open ? `，${it.fill_open} 次尚未填息` : ''}` };
      const w = it.fill_last && it.fill_last[1];
      if (w != null) return { v: '尚未填息', t: `最近一次除息尚未填息（已 ${w} 天）` };
      return { v: '—', t: '填息資料不足（除息日不在行情裡）' };
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
    const by = {}; cal.forEach((e) => { (by[e.ex] = by[e.ex] || []).push(e); });
    const nIn = cal.filter((e) => e.ex.slice(0, 7) === S.month).length;
    const status = S.fallback ? '資料準備中：配息行事曆要等 ETF 專區資料產出後才有'
      : !cal.length ? '配息資料尚未取得（ETF 除息紀錄回補中）'
        : `${y} 年 ${mo} 月共 ${nIn} 筆除息`;
    $('#etfCalSub').textContent = S.fallback || !cal.length ? '' : `資料日 ${S.data.asof || ''}`;
    let cells = WD.map((w) => `<div class="wd">${w}</div>`).join('');
    const start = new Date(first); start.setUTCDate(1 - first.getUTCDay());
    for (let i = 0; i < CAL_ROWS * 7; i++) {
      const dt = new Date(start); dt.setUTCDate(start.getUTCDate() + i);
      const k = dt.toISOString().slice(0, 10), d = dt.getUTCDate();
      if (k.slice(0, 7) !== S.month) { cells += `<div class="cald out" aria-hidden="true"><span class="dn"><b>${d}</b></span></div>`; continue; }
      const L = by[k] || [];
      const isT = k === today;
      // 格內金額去掉尾巴的 0（0.700 → 0.7）：格子窄，代號才不會被省略號吃掉；完整金額在右側清單
      const ent = L.slice(0, 2).map((e) => `<span class="ce"><span class="cc">${esc(e.code)}</span><span class="ca">${String(+(+e.amt).toFixed(3))}</span></span>`).join('');
      const more = L.length > 2 ? `<span class="cm">+${L.length - 2} 檔</span>` : '';
      cells += `<button type="button" class="cald${L.length ? ' has' : ''}${isT ? ' today' : ''}${S.day === k ? ' sel' : ''}" data-d="${k}" data-n="${L.length}"
        ${L.length ? '' : 'tabindex="-1"'} aria-label="${k}${isT ? '（今天）' : ''}${L.length ? ' 有 ' + L.length + ' 檔除息' : ''}"><span class="dn"><b>${d}</b>${isT ? '<i>今天</i>' : ''}</span>${ent}${more}</button>`;
    }
    const sel = S.day && by[S.day] ? by[S.day] : null;
    box.innerHTML = `<div class="calwrap"><div><div class="calhd"><button type="button" class="btn small" id="etfCalPrev" aria-label="上個月">‹ 上月</button>
      <b id="etfCalMonth">${y} 年 ${mo} 月</b><button type="button" class="btn small" id="etfCalNext" aria-label="下個月">下月 ›</button>
      <button type="button" class="btn small" id="etfCalToday"${S.month === curM ? ' disabled' : ''}>回本月</button>
      <span class="note1" id="etfCalStatus">${esc(status)}</span></div>
      <div class="calg" id="etfCalGrid">${cells}</div></div>
      <div class="callist" id="etfCalList">${sel ? calList(S.day, sel) : monthList(cal.filter((e) => e.ex.slice(0, 7) === S.month), y, mo)}</div></div>`;
    box.dataset.month = S.month; box.dataset.day = S.day || '';
    const go = (m) => { S.month = m; S.day = null; drawCal(); };
    $('#etfCalPrev').onclick = () => go(new Date(Date.UTC(y, mo - 2, 1)).toISOString().slice(0, 7));
    $('#etfCalNext').onclick = () => go(new Date(Date.UTC(y, mo, 1)).toISOString().slice(0, 7));
    $('#etfCalToday').onclick = () => go(curM);
    $$('.cald.has', box).forEach((c) => { c.onclick = () => { S.day = S.day === c.dataset.d ? null : c.dataset.d; drawCal(); }; });
    $$('tr[data-code]', box).forEach((tr) => { tr.onclick = () => A().goStock(tr.dataset.code); });
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
  function calList(day, L) {
    const wd = WD[new Date(day + 'T00:00:00Z').getUTCDay()];
    return `<b class="lt">${day}（${wd}）除息 ${L.length} 檔</b><table class="et" id="etfDayTbl">${COLS}${THEAD('ETF')}<tbody>${calRows(L, false)}</tbody></table>
      <p class="note">再點一次同一格，回到整月清單。</p>`;
  }
  function monthList(L, y, mo) {
    const head = `<b class="lt">${y} 年 ${mo} 月除息一覽（${L.length} 筆）</b>`;
    if (!L.length) return head + `<p class="note">${S.fallback || !((S.data && S.data.calendar) || []).length ? '配息資料尚未取得，這個月先空著。' : '這個月沒有除息紀錄；可切上／下月。'}</p>`;
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
  const PALC = () => { const P = A().PALETTE || []; return [P[0], P[2], P[1], P[3], P[4], P[5], P[8], P[6]]; };
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
    card.hidden = S.cat === 'all';
    if (card.hidden) return;
    $$('#etfBasisSeg button').forEach((b) => { b.classList.toggle('on', b.dataset.v === S.basis);
      b.onclick = () => { S.basis = b.dataset.v; LS.set('tw.etf.basis', S.basis); drawRet(); }; });
    $('#etfRetSub').textContent = `${S.cat}・${perLabel()}`;
    if (S.fallback) {
      body.innerHTML = '<div class="etfprep">資料準備中：報酬比較要等 ETF 專區資料產出後才有。</div>';
      body.dataset.k = ''; body.dataset.codes = ''; syncDD([], {}); return;
    }
    const sel = getCmp();
    const PC = PALC(), colorOf = {}; sel.forEach((c, i) => { colorOf[c] = PC[i % PC.length]; });
    syncDD(sel, colorOf);
    const m = byCode(), pk = perKey();
    if (!sel.length) {
      body.innerHTML = `<div class="etfprep">還沒選任何 ETF：按右上「加入比較」勾這個分類裡想比的（最多 ${CMP_MAX} 檔）。</div>`;
      body.dataset.k = pk; body.dataset.codes = ''; return;
    }
    const rows = sel.map((c) => ({ it: m.get(c) || { code: c, name: c, stats: {} }, st: ((m.get(c) || {}).stats || {})[pk] || { ok: false, why: '無資料' } }));
    const num = (v, f) => (v == null ? '<span class="na">—</span>' : f(v));
    body.innerHTML = `<div class="retcharts"><div><div class="note note1">累積報酬走勢（${S.basis === 'tr' ? '含息總報酬' : '價格，不含息'}；期初 = 0%）</div><div id="etfRetLine" class="chart"></div></div>
      <div><div class="note note1">年化報酬率（不含息 vs 含息）</div><div id="etfRetBar" class="chart"></div></div></div>
      <div class="rettw"><table class="et" id="etfRetTbl"><colgroup><col><col style="width:190px"><col style="width:150px"><col style="width:180px"><col style="width:150px"><col style="width:120px"></colgroup>
      <thead><tr><th>ETF</th><th>期間</th><th>價格年化（不含息）</th><th>含息年化</th><th>殖利率（近 12 月）</th><th>配息年化</th></tr></thead><tbody>
      ${rows.map(({ it, st }) => `<tr data-code="${esc(it.code)}"><td><i style="display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;background:${colorOf[it.code]}"></i>${esc(it.name)} <span class="note">${esc(it.code)}</span></td>
        ${st.ok ? `<td>${st.from}～ <span class="note">${st.years} 年</span></td><td class="${cls(st.price_ann)}">${num(st.price_ann, (v) => pct(v, 2))}</td>
        <td class="${cls(st.tr_ann)}">${st.tr_ann == null ? `<span class="na">${esc(st.why_div || '無資料')}</span>` : pct(st.tr_ann, 2)}</td>`
        : `<td colspan="3"><span class="na">${esc(st.why || '無資料')}</span></td>`}
        <td>${num(it.yield_ttm, (v) => pctU(v))}</td><td>${st.ok ? num(st.div_ann, (v) => pctU(v)) : '<span class="na">—</span>'}</td></tr>`).join('')}</tbody></table></div>`;
    body.dataset.k = pk + '|' + S.cat + '|' + S.basis; body.dataset.codes = sel.join(',');
    $$('tr[data-code]', body).forEach((tr) => { tr.onclick = () => A().goStock(tr.dataset.code); });
    drawRetCharts(rows, colorOf);
    if (!S.series) loadSeries().then(() => { if (!$('#etfRetCard').hidden && $('#etfRetBody').dataset.codes === sel.join(',')) drawRetCharts(rows, colorOf); });
  }
  function drawRetCharts(rows, colorOf) {
    const a = A(), CH = a.CH;
    const lines = [];
    rows.forEach(({ it, st }) => {
      const s = seriesOf(it.code); if (!s || !st.ok) return;
      const vals = S.basis === 'tr' ? s.t : s.p; if (!vals) return;
      const i0 = s.d.findIndex((d) => d >= st.from); if (i0 < 0) return;
      const base = vals[i0]; if (!base) return;
      const col = colorOf[it.code];
      lines.push({ name: `${it.name} ${it.code}`, type: 'line', showSymbol: false, smooth: false, lineStyle: { width: 1.8, color: col }, itemStyle: { color: col },
        data: s.d.slice(i0).map((d, j) => [d, +((vals[i0 + j] / base - 1) * 100).toFixed(2)]) });
    });
    const lineEl = $('#etfRetLine'); if (!lineEl) return;
    if (!lines.length) {
      holdEmpty('etfRetLine', !S.series ? '走勢載入中…'
        : S.basis === 'tr' ? '含息走勢無資料（配息資料尚未取得，或期間內上市未滿）—— 可切「不含息」看價格走勢'
          : '這段期間你選的 ETF 都沒有完整的價量歷史（見下表理由）');
    } else {
      lineEl.innerHTML = '';
      a.chart('etfRetLine', {
        grid: { left: 52, right: 14, top: 34, bottom: 28 }, legend: { top: 0, textStyle: { color: CH.ink2, fontSize: 12 }, type: 'scroll' },
        tooltip: { trigger: 'axis', valueFormatter: (v) => (v > 0 ? '+' : '') + v + '%' },
        xAxis: { type: 'time', ...a.axisStyle, splitLine: { show: false } },
        yAxis: { type: 'value', ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, formatter: (v) => v + '%' } },
        series: lines,
      });
    }
    lineEl.dataset.n = String(lines.length);
    const ok = rows.filter(({ st }) => st.ok);
    const barEl = $('#etfRetBar');
    if (!ok.length) { holdEmpty('etfRetBar', '這段期間你選的 ETF 都資料不足（見下表理由）'); barEl.dataset.n = '0'; return; }
    const sorted = ok.slice().sort((x, y) => ((y.st.tr_ann != null ? y.st.tr_ann : y.st.price_ann) - (x.st.tr_ann != null ? x.st.tr_ann : x.st.price_ann)));
    const v = (x) => (x == null ? null : +(x * 100).toFixed(2));
    barEl.innerHTML = '';
    a.chart('etfRetBar', {
      grid: { left: 96, right: 52, top: 30, bottom: 24 }, legend: { top: 0, textStyle: { color: CH.ink2, fontSize: 12 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (x) => (x == null ? '無資料' : x + '%') },
      xAxis: { type: 'value', ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, formatter: (x) => x + '%' } },
      yAxis: { type: 'category', inverse: true, data: sorted.map(({ it }) => it.name), ...a.axisStyle, axisLabel: { ...a.axisStyle.axisLabel, fontSize: 12, width: 86, overflow: 'truncate' } },
      series: [
        { name: '不含息', type: 'bar', data: sorted.map(({ st }) => v(st.price_ann)), itemStyle: { color: CH.cyan }, barMaxWidth: 14,
          label: { show: true, position: 'right', color: CH.ink2, fontSize: 11, formatter: (p) => (p.value == null ? '' : p.value + '%') } },
        { name: '含息', type: 'bar', data: sorted.map(({ st }) => v(st.tr_ann)), itemStyle: { color: CH.amber }, barMaxWidth: 14,
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
    S.cat = LS.get('tw.etf.cat', 'all'); S.pop = LS.get('tw.etf.pop', 'holders');
    S.per = LS.get('tw.etf.per', '5y'); S.basis = LS.get('tw.etf.basis', 'tr'); S.cmp = {};
    skeleton(root);
    $('#etfSort').onchange = (e) => { S.sort = e.target.value; S.shown = PAGE; drawList(); };
    $('#etfGrid').innerHTML = '<div class="etfprep">載入中…</div>';
    await loadData();
    if (!S.fallback) loadSeries();
    if (S.cat !== 'all' && !items().some((it) => it.cat === S.cat)) S.cat = 'all';
    drawCal(); drawAll();
    root.dataset.ready = S.fallback ? 'fallback' : 'full';
  }
  window.TwEtfPage = { render, classify, state: S };
})();
