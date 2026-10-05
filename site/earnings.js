/* ============================================================================
   財報日曆（#earnings）—— Andy 2026-10-05 16:00：
   「總覽下方新增"財報日曆"，並不是子分頁，需要向行事曆那樣標示出台股大公司的開財報日期，
    以及FED公布重大數據也需要標示出來，並且需要在旁邊有點及該個股後，出現對於這次財包的分析及展望(包含FED消息)」

   版面：左＝7 欄真月曆（固定 6 列，切月整張卡不會變高）；右＝固定側欄面板（固定高、內部捲動）：
     · 還沒點 → 本週重點（這週一～週日的全部事件＋下一次 FOMC／CPI）
     · 點公司標籤（或下面時間表的一列）→ 這次財報的分析與展望（規則式，每段附出處與資料日期）＋ FED 背景
     · 點 FED／美國數據標籤 → 數據說明、上次數值（FRED）、市場關注點、下一次日期
     · 點日期格（或「＋N」）→ 那一天的完整清單
   月曆下方：市值前 50 大公司「本季財報時間表」，每列可點（右側面板原地展開，不離開這一頁；面板裡才有「看個股頁」）。

   資料：data/earnings.json（pipeline/compute/earnings.py，build_payload 產出）。
   ⚠ 預覽分支吃的是正式站的資料，earnings.json 上正式站之前不存在 —— 那時退回分支內附的種子檔 earnings_seed.json
     （同一支程式用真資料產出），畫面上明寫「種子資料（資料日 …）」，不冒充最新。
   「分析與展望」全部是規則＋數字組出來的句子（沒有語言模型），口徑在 earnings.py 檔頭。
   排版紀律（Andy：「所有文字單行、操作不影響排版」）：標籤、清單列、表格一律 nowrap＋省略號；月曆固定 6 列、
     面板固定高（內容多就在面板裡捲），點任何東西都不會讓整頁上下跳。分頁鈕選中不加粗。
   驗收：scripts/_uitest.py「財報日曆1005」。
   ========================================================================== */
(function () {
  'use strict';
  const A = () => window.App;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const WD = ['日', '一', '二', '三', '四', '五', '六'];
  const ROWS = 6;
  const todayTW = () => new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);   // 台北日期
  const md = (d) => `${+d.slice(5, 7)}/${+d.slice(8, 10)}`;
  const wdOf = (d) => WD[new Date(d + 'T00:00:00Z').getUTCDay()];

  /* 事件種類 → 分組（co＝台股公司、tw＝台股全市場期限、fed＝FED 與美國數據）、圖例文字、樣式 */
  const KIND = {
    conf: { g: 'co', lab: '法說會（公告）', cls: 'kconf' },
    board: { g: 'co', lab: '財報董事會（公告）', cls: 'kboard' },
    report: { g: 'co', lab: '已公布財報', cls: 'kboard' },
    invite: { g: 'co', lab: '受邀法說（券商論壇）', cls: 'kinv' },
    est: { g: 'co', lab: '預估財報日', cls: 'kest' },
    rev: { g: 'tw', lab: '營收期限', cls: 'ktw' },
    qdl: { g: 'tw', lab: '財報法定期限', cls: 'ktw' },
    fomc: { g: 'fed', lab: 'FOMC 利率決議', cls: 'kfomc' },
    minutes: { g: 'fed', lab: 'FOMC 紀要', cls: 'kfomc' },
    cpi: { g: 'fed', lab: 'CPI', cls: 'kdata' }, nfp: { g: 'fed', lab: '非農', cls: 'kdata' },
    pce: { g: 'fed', lab: 'PCE', cls: 'kdata' }, gdp: { g: 'fed', lab: 'GDP', cls: 'kdata' },
  };
  const ORDER = { fomc: 0, minutes: 1, cpi: 2, nfp: 3, pce: 4, gdp: 5, conf: 10, board: 11, report: 12, invite: 13, est: 20, rev: 30, qdl: 31 };
  /* 小圖示（currentColor）：公司＝文件、FED＝柱廊建築、美國數據＝長條、台股期限＝沙漏 */
  const IC = {
    co: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1.5h5.5L13 5v9.5H4z" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 8h5M6 11h5" stroke="currentColor" stroke-width="1.4"/></svg>',
    fed: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5 14.5 5h-13z" fill="currentColor"/><path d="M3 6.5v6M6.3 6.5v6M9.7 6.5v6M13 6.5v6" stroke="currentColor" stroke-width="1.5"/><path d="M1.5 14h13" stroke="currentColor" stroke-width="1.8"/></svg>',
    data: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 14.5V9M6.5 14.5V5M10.5 14.5V7.5M14 14.5V2.5" stroke="currentColor" stroke-width="2.2"/></svg>',
    tw: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1.5h8M4 14.5h8M5 1.5c0 4 6 4.5 6 6.5s-6 2.5-6 6.5M11 1.5c0 4-6 4.5-6 6.5s6 2.5 6 6.5" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
  };
  const icOf = (k) => (KIND[k] || {}).g === 'co' ? IC.co : k === 'fomc' || k === 'minutes' ? IC.fed : (KIND[k] || {}).g === 'fed' ? IC.data : IC.tw;

  /* FED／期限標籤上的字：寬螢幕寫全、手機（≤640）用短字（格子只有 48px） */
  const SHORT = { fomc: 'FOMC', minutes: 'FOMC 紀要', cpi: 'CPI', nfp: '非農', pce: 'PCE', gdp: 'GDP', rev: '營收期限', qdl: '財報期限' };
  const S = { data: null, seed: false, month: null, sel: { t: 'week' }, filt: 'all' };

  function injectCSS() {
    if (document.getElementById('earnCss')) return;
    const s = document.createElement('style'); s.id = 'earnCss';
    s.textContent = `
@media (max-width:820px){ .tab[data-view="earnings"]{display:none!important} }
#v-earnings .edisc{display:flex;gap:8px;align-items:flex-start;padding:10px 14px;border:1px solid var(--line-2);border-left:3px solid var(--amber);
  border-radius:10px;background:var(--panel-2);color:var(--ink-2);font-size:13px;line-height:1.55;margin-bottom:10px;white-space:nowrap;overflow:hidden;padding:6px 14px}
#v-earnings .edisc>div{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .edisc b{color:var(--ink)}
#v-earnings .card{margin-bottom:var(--sp-3)}
#v-earnings .card h3{flex-wrap:nowrap;white-space:nowrap;min-width:0}
#v-earnings .card h3 small{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .row.spread{flex-wrap:nowrap;gap:10px;min-width:0}
#v-earnings #earnFilt{flex:none}
#v-earnings .ewrap{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:12px;margin-top:6px}
#v-earnings .ehd{display:flex;align-items:center;gap:8px;margin-bottom:6px;white-space:nowrap;height:32px;min-width:0}
#v-earnings .ehd b{font-size:16px;width:118px;text-align:center;flex:none}
#v-earnings .ehd .sp{flex:1}
#v-earnings .elegend{display:flex;flex-wrap:nowrap;gap:12px;align-items:center;margin:2px 0 8px;font-size:12px;color:var(--ink-2);white-space:nowrap;overflow:hidden;min-width:0}
#v-earnings .elegend span{display:inline-flex;align-items:center;gap:5px;flex:none}
#v-earnings .elegend i{display:inline-flex;align-items:center;justify-content:center;width:18px;height:14px;border-radius:4px;font-style:normal}
#v-earnings svg{width:11px;height:11px;flex:none;display:block}
#v-earnings .eg{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));grid-template-rows:20px repeat(${ROWS},98px);gap:4px}
#v-earnings .eg .wd{font-size:12px;color:var(--ink-3);text-align:center;line-height:20px}
#v-earnings .ed{border:1px solid var(--line);border-radius:8px;background:var(--panel-2);font-size:12px;color:var(--ink-3);
  text-align:left;font-family:inherit;display:flex;flex-direction:column;gap:2px;min-width:0;overflow:hidden;padding:3px 4px;position:relative}
#v-earnings .ed.out{opacity:.35;background:transparent}
#v-earnings .ed.today{border-color:var(--cyan);background:color-mix(in srgb,var(--cyan) 12%,var(--panel-2));box-shadow:0 0 0 1px var(--cyan) inset}
#v-earnings .ed.sel{border-color:var(--amber);box-shadow:0 0 0 2px var(--amber) inset}
#v-earnings .ed .dn{display:flex;align-items:center;gap:6px;height:17px;white-space:nowrap;border:0;background:none;color:inherit;padding:0 2px;
  font:inherit;cursor:pointer;text-align:left;width:100%;border-radius:4px}
#v-earnings .ed .dn:hover{background:var(--panel-3)}
#v-earnings .ed .dn b{font:600 12px var(--mono)}
#v-earnings .ed .dn i{font-style:normal;font-size:11px;padding:0 5px;border-radius:999px;background:var(--cyan);color:var(--ontop);line-height:15px}
#v-earnings .chip{display:flex;align-items:center;gap:3px;height:18px;padding:0 4px;border-radius:5px;border:1px solid transparent;
  font-family:inherit;font-size:11.5px;font-weight:500;line-height:18px;white-space:nowrap;overflow:hidden;cursor:pointer;color:var(--ink);background:var(--panel-3);min-width:0;width:100%;text-align:left}
#v-earnings .chip .cd{font:600 11.5px var(--mono);flex:none}
#v-earnings .chip .nm,#v-earnings .chip .lb{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .chip:hover,#v-earnings .chip:focus-visible{outline:none;border-color:var(--ink-2)}
#v-earnings .chip.on{box-shadow:0 0 0 2px var(--amber) inset}
#v-earnings .kconf{background:color-mix(in srgb,var(--amber) 26%,var(--panel-2));color:var(--ink)}
#v-earnings .kconf svg{color:var(--amber)}
#v-earnings .kboard{background:color-mix(in srgb,var(--cyan) 22%,var(--panel-2))}
#v-earnings .kboard svg{color:var(--cyan)}
#v-earnings .kinv{background:var(--panel-2);border-color:color-mix(in srgb,var(--amber) 60%,transparent)}
#v-earnings .kinv svg{color:var(--amber)}
#v-earnings .kest{background:transparent;border:1px dashed var(--line-2);color:var(--ink-2)}
#v-earnings .kest svg{color:var(--ink-3)}
#v-earnings .ktw{background:transparent;color:var(--ink-3);border:1px solid var(--line)}
#v-earnings .kfomc{background:color-mix(in srgb,var(--violet) 30%,var(--panel-2));color:var(--ink)}
#v-earnings .kfomc svg{color:var(--violet)}
#v-earnings .kdata{background:color-mix(in srgb,var(--lime) 18%,var(--panel-2));color:var(--ink)}
#v-earnings .kdata svg{color:var(--lime)}
#v-earnings .ed .more{font-size:11px;color:var(--cyan);line-height:16px;white-space:nowrap;border:0;background:none;padding:0 2px;text-align:left;cursor:pointer;font-family:inherit}
#v-earnings .epanel{border:1px solid var(--line);border-radius:10px;background:var(--panel-2);padding:10px 12px;box-sizing:border-box;
  height:${32 + 6 + 30 + 20 + ROWS * 98 + ROWS * 4}px;overflow:auto;min-width:0}
#v-earnings .ph{display:flex;align-items:center;gap:8px;white-space:nowrap;min-width:0;margin-bottom:4px}
#v-earnings .ph b{font-size:15.5px;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .ph .sp{flex:1}
#v-earnings .ps{font-size:12.5px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:8px}
#v-earnings .badge{display:inline-block;font-size:11.5px;padding:0 7px;border-radius:999px;border:1px solid currentColor;line-height:18px;white-space:nowrap;flex:none}
#v-earnings .badge.ann{color:var(--amber)} #v-earnings .badge.est{color:var(--ink-3);border-style:dashed} #v-earnings .badge.sch{color:var(--violet)}
#v-earnings .tags{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 4px}
#v-earnings .tag{font-size:12px;padding:2px 8px;border-radius:999px;background:var(--panel-3);white-space:nowrap}
#v-earnings .tag b{font-weight:600;margin-left:4px}
#v-earnings .up{color:var(--rise)} #v-earnings .down{color:var(--fall)}
#v-earnings .sec{border-top:1px solid var(--line);padding:8px 0 6px}
#v-earnings .sec h4{margin:0 0 3px;font-size:13.5px;display:flex;gap:6px;align-items:baseline;white-space:nowrap;min-width:0}
#v-earnings .sec h4 small{font-weight:400;font-size:11.5px;color:var(--ink-3);overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .sec p{margin:3px 0;font-size:13px;line-height:1.55;color:var(--ink-2)}
#v-earnings .sec .src{font-size:11.5px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings table.mt{width:100%;border-collapse:collapse;font-size:12px;table-layout:fixed;margin:4px 0}
#v-earnings table.mt th{color:var(--ink-3);font-weight:600;text-align:right;padding:3px 4px;border-bottom:1px solid var(--line);white-space:nowrap}
#v-earnings table.mt td{text-align:right;padding:3px 4px;font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings table.mt th:first-child,#v-earnings table.mt td:first-child{text-align:left}
#v-earnings .nl{list-style:none;margin:4px 0;padding:0}
#v-earnings .nl li{display:flex;gap:6px;font-size:12.5px;line-height:20px;white-space:nowrap;min-width:0}
#v-earnings .nl li .d{font:11.5px var(--mono);color:var(--ink-3);flex:none}
#v-earnings .nl li .t{overflow:hidden;text-overflow:ellipsis;min-width:0;color:var(--ink-2)}
#v-earnings .nl li a.t{color:var(--ink-2);text-decoration:none} #v-earnings .nl li a.t:hover{color:var(--cyan)}
#v-earnings .elist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}
#v-earnings .erow{display:grid;grid-template-columns:80px 12px minmax(0,1fr) auto;gap:6px;align-items:center;height:30px;padding:0 8px;
  border:1px solid var(--line);border-radius:8px;background:var(--panel-3);color:var(--ink);font:inherit;font-size:13px;text-align:left;cursor:pointer;white-space:nowrap;width:100%}
#v-earnings .erow:hover,#v-earnings .erow:focus-visible{outline:none;border-color:var(--cyan)}
#v-earnings .erow .d{font:12px var(--mono);color:var(--ink-3)}
#v-earnings .erow .t{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .erow .b{font-size:11.5px;color:var(--ink-3)}
#v-earnings .erow.kfomc svg{color:var(--violet)} #v-earnings .erow.kdata svg{color:var(--lime)} #v-earnings .erow.kconf svg,#v-earnings .erow.kinv svg{color:var(--amber)}
#v-earnings .erow.kboard svg{color:var(--cyan)} #v-earnings .erow.kest svg,#v-earnings .erow.ktw svg{color:var(--ink-3)}
#v-earnings .erow.kfomc,#v-earnings .erow.kdata,#v-earnings .erow.kconf,#v-earnings .erow.kboard,#v-earnings .erow.kinv,#v-earnings .erow.kest,#v-earnings .erow.ktw{background:var(--panel-3);border-style:solid;border-color:var(--line);color:var(--ink)}
#v-earnings .lt{display:block;font-size:13px;color:var(--ink-2);margin:10px 0 6px;white-space:nowrap}
#v-earnings .kv{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;font-size:13px;margin:4px 0}
#v-earnings .kv dt{color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings .kv dd{margin:0;text-align:right;font-family:var(--mono);white-space:nowrap}
#v-earnings .kv .pv{grid-column:1/-1;font-size:11.5px;color:var(--ink-3);margin-top:-2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings .note{font-size:12.5px;color:var(--ink-3);line-height:1.55}
#v-earnings .pact{display:flex;gap:8px;margin-top:10px}
@media (max-width:1100px){#v-earnings .ewrap{grid-template-columns:minmax(0,1fr)}#v-earnings .epanel{height:540px}
  #v-earnings .row.spread{flex-wrap:wrap}}
@media (max-width:640px){
  #v-earnings .eg{grid-template-rows:20px repeat(${ROWS},78px);gap:3px}
  #v-earnings .chip .nm{display:none}
  #v-earnings .chip .lb{font-size:11px;text-overflow:clip}
  #v-earnings .ed .dn i{display:none}
  #v-earnings .chip{padding:0 3px;gap:2px} #v-earnings .chip svg{display:none}
  #v-earnings .ed{padding:2px}
  #v-earnings .ehd b{width:96px;font-size:15px}
  #v-earnings .elegend{flex-wrap:wrap;white-space:normal;gap:4px 10px}
  #v-earnings .ehd .btn{padding:0 8px}
  }`;
    document.head.appendChild(s);
  }

  /* ------------------------------------------------------------------ 資料 */
  async function loadData() {
    let d = null;
    try { d = await A().load('earnings', { fallback: null }); } catch (e) { d = null; }
    if (d && Array.isArray(d.events)) { S.data = d; S.seed = false; return; }
    // 退回：分支內附的種子檔（預覽版、或正式站還沒產出 earnings.json 的那一輪）
    try {
      const r = await fetch('earnings_seed.json', { cache: 'no-store' });
      if (r.ok) { const j = await r.json(); if (j && Array.isArray(j.events)) { S.data = j; S.seed = true; return; } }
    } catch (e) { /* 也讀不到 → 下面空狀態 */ }
    S.data = null;
  }
  const evs = () => (S.data && S.data.events) || [];
  const co = (c) => ((S.data && S.data.companies) || {})[c];
  const passF = (e) => S.filt === 'all' || (S.filt === 'co' ? KIND[e.k].g !== 'fed' : KIND[e.k].g === 'fed');
  const rankOf = (e) => (e.code && co(e.code) ? co(e.code).rank : 99);
  const sortEv = (a, b) => (ORDER[a.k] - ORDER[b.k]) || (rankOf(a) - rankOf(b));
  const idxOf = (e) => evs().indexOf(e);
  const label = (e) => (e.code ? `${e.code} ${e.name || ''}` : (KIND[e.k] && KIND[e.k].g === 'fed' ? (e.k === 'fomc' ? 'FOMC 決議' : e.k === 'minutes' ? 'FOMC 紀要' : KIND[e.k].lab) : e.title));

  /* ------------------------------------------------------------------ 骨架 */
  function skeleton(root) {
    const how = (k, q, li) => `<div class="howtxt" id="how-${k}" hidden>${A().howHTML(q, li)}</div>`;
    const hbtn = (k, t) => `<button class="howbtn pop" data-how="${k}" data-ttl="${t}" type="button" aria-label="${t}">?</button>`;
    const lg = [['kconf', IC.co, '法說會（公告）'], ['kboard', IC.co, '財報董事會'], ['kinv', IC.co, '受邀法說'], ['kest', IC.co, '預估財報日'],
      ['kfomc', IC.fed, 'FOMC'], ['kdata', IC.data, '美國數據'], ['ktw', IC.tw, '台股期限']];
    root.innerHTML = `
<div class="edisc" id="earnDisc" role="note" title="「分析與展望」是規則把資料湖的數字組成句子（月營收、季損益、本益比、法人、新聞標題、FRED），沒有用語言模型，也不預測財報數字；每段都寫了出處與資料日期。"><span aria-hidden="true">ⓘ</span><div><b>純資料整理，不構成投資建議。</b>分析由規則把資料湖數字組成句子，沒有用語言模型、不預測財報；每段附出處與日期。</div></div>
<div class="card" id="earnCalCard">
  <div class="row spread"><h3>財報日曆 <small id="earnSub"></small> ${hbtn('earncal', '財報日曆怎麼看')}</h3>
    <div class="nbsw" id="earnFilt" role="tablist"><button data-v="all" class="on" type="button">全部</button><button data-v="co" type="button">台股公司</button><button data-v="fed" type="button">FED／美國數據</button></div></div>
  ${how('earncal', '這張回答：這個月哪幾天有大公司開法說／公布財報、哪幾天有 FED 決議與美國重大數據？點了之後這次財報要看什麼？', [
    '<b>大公司</b>＝市值前 50（收盤 × 最新一季財報的股數，上市＋上櫃普通股，排除 ETF）。資料湖沒有 0050／0051 成分股，所以用市值排名。',
    '<b>實心標籤＝公司已公告</b>（公開資訊觀測站重大訊息：法說會、財報董事會日期）；<b>虛線標籤＝預估</b>：這一季還沒公告日期的公司，先標在法定期限（Q3 是 11/14）。有過去幾季的實際公布日時，改用「平均早於期限幾天」往前推。',
    '<b>FED 與美國數據</b>：FOMC 會議日程（聯準會公布）＋ CPI、非農、PCE、GDP 的公布日（FRED，抓不到時用 BLS／BEA 公布的日程）。日期是美東日期，台灣時間寫在右側面板。',
    '點公司標籤 → 右側出現這次財報的分析與展望（營收、獲利、估值、法人、消息、FED 背景）；點 FED 標籤 → 數據說明、上次數值、市場關注點；點日期 → 那天的完整清單。',
    '所以：月初先看這個月有哪幾家大公司要開法說、FOMC 在哪一天；法說前一週點進去，對照「這次財報看什麼」那段的月營收，就知道營收已經反映多少、要看的是毛利率還是展望。'])}
  <div class="elegend" id="earnLegend">${lg.map(([c, ic, t]) => `<span><i class="${c}">${ic}</i>${t}</span>`).join('')}</div>
  <div class="ewrap">
    <div><div class="ehd"><button type="button" class="btn small" id="earnPrev" aria-label="上個月">‹ 上月</button>
      <b id="earnMonth"></b><button type="button" class="btn small" id="earnNext" aria-label="下個月">下月 ›</button>
      <button type="button" class="btn small" id="earnToday">回本月</button><span class="sp"></span></div>
      <div class="eg" id="earnGrid"></div></div>
    <div class="epanel" id="earnPanel" role="region" aria-label="分析面板" aria-live="polite"></div>
  </div>
</div>
`;
  }

  /* ------------------------------------------------------------------ 月曆 */
  function chipHTML(e, small) {
    const k = KIND[e.k] || KIND.rev;
    const on = S.sel.t === 'ev' && S.sel.i === idxOf(e) ? ' on' : '';
    const t = e.code ? `<span class="cd">${esc(e.code)}</span><span class="nm">${esc(e.name || '')}</span>`
      : `<span class="lb">${esc(SHORT[e.k] || '')}</span>`;
    const tip = `${e.d}（${wdOf(e.d)}）${e.code ? e.code + ' ' + (e.name || '') + '：' : ''}${e.title}${e.status === '預估' ? '（預估）' : ''}`;
    return `<button type="button" class="chip ${k.cls}${on}" data-i="${idxOf(e)}" data-k="${e.k}"${e.code ? ` data-code="${esc(e.code)}"` : ''} title="${esc(tip)}">${icOf(e.k)}${t}</button>`;
  }
  function drawCal() {
    const grid = $('#earnGrid'); if (!grid) return;
    const today = todayTW(), curM = today.slice(0, 7);
    if (!S.month) S.month = curM;
    const [y, mo] = S.month.split('-').map(Number);
    const first = new Date(Date.UTC(y, mo - 1, 1));
    const by = {}; evs().filter(passF).forEach((e) => { (by[e.d] = by[e.d] || []).push(e); });
    const cap = fitRows();
    let cells = WD.map((w) => `<div class="wd">${w}</div>`).join('');
    const start = new Date(first); start.setUTCDate(1 - first.getUTCDay());
    let nIn = 0;
    for (let i = 0; i < ROWS * 7; i++) {
      const dt = new Date(start); dt.setUTCDate(start.getUTCDate() + i);
      const k = dt.toISOString().slice(0, 10), d = dt.getUTCDate();
      if (k.slice(0, 7) !== S.month) { cells += `<div class="ed out" aria-hidden="true"><span class="dn"><b>${d}</b></span></div>`; continue; }
      const L = (by[k] || []).slice().sort(sortEv);
      nIn += L.length;
      const isT = k === today;
      const show = L.length > cap ? L.slice(0, cap - 1) : L;
      const more = L.length > show.length ? `<button type="button" class="more" data-d="${k}">＋${L.length - show.length}</button>` : '';
      cells += `<div class="ed${isT ? ' today' : ''}${S.sel.t === 'day' && S.sel.d === k ? ' sel' : ''}" data-d="${k}" data-n="${L.length}">
        <button type="button" class="dn" data-d="${k}" aria-label="${k}${isT ? '（今天）' : ''} ${L.length} 項">${'<b>' + d + '</b>'}${isT ? '<i>今天</i>' : ''}</button>${show.map((e) => chipHTML(e)).join('')}${more}</div>`;
    }
    grid.innerHTML = cells;
    $('#earnMonth').textContent = `${y} 年 ${mo} 月`;
    $('#earnToday').disabled = S.month === curM;
    const box = $('#earnCalCard'); box.dataset.month = S.month; box.dataset.n = String(nIn);
    $$('.chip', grid).forEach((c) => { c.onclick = (ev) => { ev.stopPropagation(); pick({ t: 'ev', i: +c.dataset.i }); }; });
    $$('.dn,.more', grid).forEach((c) => { c.onclick = () => pick(S.sel.t === 'day' && S.sel.d === c.dataset.d ? { t: 'week' } : { t: 'day', d: c.dataset.d }); });
  }
  function go(m) { S.month = m; drawCal(); }

  /* ------------------------------------------------------------------ 右側面板 */
  function pick(sel) {
    S.sel = sel;
    drawCal(); drawPanel(); markRows();
  }
  function rowHTML(e) {
    const k = KIND[e.k] || KIND.rev;
    const st = e.status === '預估' ? '預估' : e.status === '公告' ? '公告' : '';
    return `<li><button type="button" class="erow ${k.cls}" data-i="${idxOf(e)}" title="${esc(e.title)}"><span class="d">${md(e.d)}（${wdOf(e.d)}）</span>${icOf(e.k)}
      <span class="t">${esc(label(e))}${e.code ? '・' + esc(k.lab.replace('（公告）', '')) : e.tw ? '・台灣 ' + esc(e.tw.slice(6)) : ''}</span><span class="b">${st}</span></button></li>`;
  }
  function bindRows(box) {
    $$('.erow', box).forEach((b) => { b.onclick = () => pick({ t: 'ev', i: +b.dataset.i }); });
  }
  function weekRange() {
    const t = new Date(todayTW() + 'T00:00:00Z');
    const dow = (t.getUTCDay() + 6) % 7;      // 週一＝0
    const a = new Date(t); a.setUTCDate(t.getUTCDate() - dow);
    const b = new Date(a); b.setUTCDate(a.getUTCDate() + 6);
    return [a.toISOString().slice(0, 10), b.toISOString().slice(0, 10)];
  }
  function panelWeek() {
    const [a, b] = weekRange();
    const L = evs().filter((e) => e.d >= a && e.d <= b).filter(passF).sort((x, y) => (x.d < y.d ? -1 : x.d > y.d ? 1 : sortEv(x, y)));
    const fed = (S.data && S.data.fed && S.data.fed.next) || {};
    const nx = (k) => fed[k] ? `${md(fed[k].d)}（${wdOf(fed[k].d)}）・台灣 ${esc(fed[k].tw || '')}` : '—';
    const ahead = L.length ? '' : (() => {
      const n = evs().filter((e) => e.d > b).filter(passF).slice(0, 6);
      return `<p class="note">這一週沒有${S.filt === 'fed' ? ' FED／美國數據' : S.filt === 'co' ? '台股公司' : ''}事件。接下來：</p><ul class="elist">${n.map(rowHTML).join('')}</ul>`;
    })();
    return `<div class="ph"><b>本週重點</b><span class="sp"></span><span class="badge sch">${md(a)}–${md(b)}</span></div>
      <div class="ps">點月曆上的公司或 FED 標籤，這裡換成那一項的分析</div>
      ${L.length ? `<ul class="elist" id="earnWeekList">${L.map(rowHTML).join('')}</ul>` : ahead}
      <span class="lt">接下來的 FED 與美國數據</span>
      <dl class="kv"><dt>FOMC 利率決議</dt><dd>${nx('fomc')}</dd><dt>CPI</dt><dd>${nx('cpi')}</dd><dt>非農就業</dt><dd>${nx('nfp')}</dd><dt>PCE 物價</dt><dd>${nx('pce')}</dd></dl>`;
  }
  function panelDay(d) {
    const L = evs().filter((e) => e.d === d).filter(passF).sort(sortEv);
    return `<div class="ph"><b>${d}（${wdOf(d)}）</b><span class="sp"></span><span class="badge sch">${L.length} 項</span></div>
      <div class="ps">點一列看分析；再點一次同一個日期回到本週重點</div>
      ${L.length ? `<ul class="elist" id="earnDayList">${L.map(rowHTML).join('')}</ul>` : '<p class="note">這一天沒有事件。</p>'}
      <div class="pact"><button type="button" class="btn small" id="earnBack">← 回本週重點</button></div>`;
  }
  const toneCls = (t) => (t > 0 ? 'up' : t < 0 ? 'down' : '');
  function fedBlock(keys) {
    const f = (S.data && S.data.fed) || {};
    const snap = f.snap || {};
    const have = (keys || []).filter((k) => snap[k]);
    if (!have.length) {
      return '<p class="note">FRED 資料尚未取得（資料湖的 FRED 觀測值目前是 0 筆：需要 GitHub Secret <code>FRED_API_KEY</code> 有效）。這裡不拿別的來源的數字湊。</p>';
    }
    return `<dl class="kv">${have.map((k) => { const x = snap[k]; return `<dt>${esc(x.label)}（${esc(x.date)}）</dt><dd>${esc(x.value)}</dd>${x.prev ? `<div class="pv">${esc(x.prev)}・${esc(x.src)}</div>` : `<div class="pv">${esc(x.src)}</div>`}`; }).join('')}</dl>`;
  }
  function panelFed(e) {
    const info = ((S.data && S.data.fed && S.data.fed.info) || {})[e.k] || {};
    const nx = evs().filter((x) => x.k === e.k && x.d > e.d)[0];
    return `<div class="ph">${icOf(e.k)}<b>${esc(e.title)}</b><span class="sp"></span><span class="badge sch">排程</span></div>
      <div class="ps">${e.d}（美東）・台灣時間 ${esc(e.tw || '—')}${e.ref ? '・' + esc(e.ref) : ''}${e.meet ? '・會議 ' + esc(e.meet) : ''}</div>
      <div class="sec"><h4>這是什麼 <small>${esc(info.org || '')}</small></h4><p>${esc(info.desc || '')}</p></div>
      <div class="sec"><h4>上次數值 <small>FRED</small></h4>${fedBlock(info.rel)}</div>
      <div class="sec"><h4>市場關注點</h4>${(info.focus || []).map((t) => `<p>・${esc(t)}</p>`).join('')}</div>
      <div class="sec"><h4>下一次</h4><p>${nx ? `${nx.d}（${wdOf(nx.d)}）・台灣 ${esc(nx.tw || '')}` : '日程表裡還沒有下一次的日期'}</p>
        <div class="src">日期出處：${esc(e.src || '')}</div></div>
      <div class="pact"><button type="button" class="btn small" id="earnBack">← 回本週重點</button></div>`;
  }
  function secHTML(s) {
    const tbl = s.table ? `<table class="mt"><thead><tr>${s.table.cols.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${s.table.rows.map((r) =>
      `<tr>${r.map((v, i) => `<td class="${i && typeof v === 'number' && s.key === 'rev' && i > 1 ? toneCls(v) : ''}">${v == null ? '—' : esc(typeof v === 'number' && i > 1 && s.key === 'rev' ? (v > 0 ? '+' : '') + v : v)}</td>`).join('')}</tr>`).join('')}</tbody></table>` : '';
    const items = s.items ? `<ul class="nl">${s.items.map((n) => `<li><span class="d">${esc(md(n.d))}</span>${n.u ? `<a class="t" href="${esc(n.u)}" target="_blank" rel="noopener" title="${esc(n.t)}">${esc(n.t)}</a>` : `<span class="t" title="${esc(n.t)}">${esc(n.t)}</span>`}<span class="d">${esc(n.s === 'cnyes' ? '鉅亨' : n.s === 'technews' ? 'TechNews' : n.s)}</span></li>`).join('')}</ul>` : '';
    return `<div class="sec" data-sec="${s.key}"><h4>${esc(s.t)} <small>資料 ${esc(s.asof || '—')}</small></h4>${s.lines.map((t) => `<p>${esc(t)}</p>`).join('')}${tbl}${items}<div class="src" title="${esc(s.src)}">出處：${esc(s.src)}</div></div>`;
  }
  function panelCo(e) {
    const c = co(e.code);
    if (!c) return `<div class="ph"><b>${esc(e.code)} ${esc(e.name || '')}</b></div><p class="note">這家公司不在大公司名單裡，沒有整理分析。</p>`;
    const nxt = c.next;
    const isEst = e.status === '預估';
    const head = `<div class="ph"><b>${esc(c.name)} ${esc(e.code)}</b><span class="sp"></span><span class="badge ${isEst ? 'est' : 'ann'}">${isEst ? '預估' : e.status === '公告' ? '已公告' : esc(e.status || '')}</span></div>
      <div class="ps" title="${esc(e.title)}">${md(e.d)}（${wdOf(e.d)}）${esc((KIND[e.k] || {}).lab || '')}・市值第 ${c.rank} 名・${esc(e.title)}</div>`;
    const basis = isEst ? `<p class="note">預估依據：${esc(e.basis || '')}。實際日期以公司公告為準。</p>` : '';
    const tags = (c.tags || []).length ? `<div class="tags">${c.tags.map((t) => `<span class="tag">${esc(t.l)}<b class="${toneCls(t.tone)}">${esc(t.v)}</b></span>`).join('')}</div>` : '';
    const f = (S.data && S.data.fed) || {};
    const fn = f.next || {};
    const fedSec = `<div class="sec" data-sec="fed"><h4>FED 背景 <small>跟這次財報同一段時間</small></h4>
      ${fn.fomc ? `<p>下一次 FOMC 利率決議：${md(fn.fomc.d)}（台灣 ${esc(fn.fomc.tw || '')}）${fn.cpi ? `；下一次 CPI：${md(fn.cpi.d)}（台灣 ${esc(fn.cpi.tw || '')}）` : ''}。</p>` : ''}
      ${fedBlock(['policy', 'cpi_yoy', 'core_pce_yoy', 'unrate'])}</div>`;
    return `${head}${basis}${tags}<p class="note">這次是 <b>${esc(c.target || '')}</b> 的財報${nxt && nxt.d !== e.d ? `（下一個相關日子 ${md(nxt.d)}，${esc(nxt.status)}）` : ''}。</p>
      ${c.err ? `<p class="note">${esc(c.err)}</p>` : ''}${(c.secs || []).map(secHTML).join('')}${fedSec}
      <div class="pact"><button type="button" class="btn small" id="earnBack">← 回本週重點</button><button type="button" class="btn small" id="earnGoStock" data-code="${esc(e.code)}">看 ${esc(c.name)} 個股頁 →</button></div>`;
  }
  function drawPanel() {
    const box = $('#earnPanel'); if (!box) return;
    if (!S.data) { box.innerHTML = '<p class="note">財報日曆資料尚未產出（管線下一輪會建立）。</p>'; return; }
    let html = '', mode = S.sel.t, key = '';
    if (S.sel.t === 'ev') {
      const e = evs()[S.sel.i];
      if (!e) { S.sel = { t: 'week' }; return drawPanel(); }
      html = e.code ? panelCo(e) : KIND[e.k].g === 'fed' ? panelFed(e) : panelTw(e);
      mode = e.code ? 'co' : KIND[e.k].g === 'fed' ? 'fed' : 'tw'; key = e.code || e.k;
    } else if (S.sel.t === 'day') { html = panelDay(S.sel.d); key = S.sel.d; } else html = panelWeek();
    box.innerHTML = html; box.scrollTop = 0;
    box.dataset.mode = mode; box.dataset.key = key;
    bindRows(box);
    const back = $('#earnBack', box); if (back) back.onclick = () => pick({ t: 'week' });
    const gs = $('#earnGoStock', box); if (gs) gs.onclick = () => A().goStock(gs.dataset.code);
  }
  function panelTw(e) {
    return `<div class="ph">${IC.tw}<b>${esc(e.title)}</b><span class="sp"></span><span class="badge sch">期限</span></div>
      <div class="ps">${e.d}（${wdOf(e.d)}）</div><div class="sec"><p>${esc(e.note || '')}</p><div class="src">出處：${esc(e.src || '')}</div></div>
      <div class="pact"><button type="button" class="btn small" id="earnBack">← 回本週重點</button></div>`;
  }

  // 2026-10-05（晚，Andy：「下方不需要」）：大公司時間表整張拿掉，markRows 留空殼讓呼叫端不用改
  function markRows() {}

  /* 一屏看完（Andy：「整理符合一頁就能看到所有資訊的版面」）：寬版（月曆＋右欄並排）時，
     格高＝（視窗剩下的高度 − 星期列 − 間距）÷ 6，夾在 56～98px；格內放得下幾個標籤就放幾個，其餘收成「＋N」。
     窄版（≤1100，面板掉到月曆下方）本來就要捲，不縮格高。 */
  function fitRows() {
    const g = $('#earnGrid'), p = $('#earnPanel'), card = $('#earnCalCard');
    if (!g || !p || !card) return 3;
    if (window.innerWidth <= 1100) { g.style.gridTemplateRows = ''; p.style.height = ''; return window.innerWidth <= 640 ? 2 : 3; }
    const top = g.getBoundingClientRect().top + window.scrollY;
    const padB = parseFloat(getComputedStyle(card).paddingBottom) || 12;
    const avail = window.innerHeight - top - padB - 14;
    const rh = Math.max(56, Math.min(98, Math.floor((avail - 20 - ROWS * 4) / ROWS)));
    g.style.gridTemplateRows = `20px repeat(${ROWS},${rh}px)`;
    const hd = $('.ehd', card);
    p.style.height = `${Math.round(g.getBoundingClientRect().bottom - hd.getBoundingClientRect().top)}px`;
    card.dataset.rowh = String(rh);
    return Math.max(1, Math.floor((rh - 8 - 17 + 2) / 20));
  }

  /* ------------------------------------------------------------------ 入口 */
  async function render() {
    injectCSS();
    const root = document.getElementById('v-earnings'); if (!root) return;
    skeleton(root);
    $('#earnPanel').innerHTML = '<p class="note">載入中…</p>';
    await loadData();
    const d = S.data;
    $('#earnSub').textContent = !d ? '資料尚未產出'
      : `資料日 ${d.asof}${S.seed ? '（預覽用種子資料）' : ''}・大公司＝市值前 ${(d.universe && d.universe.n) || 50}`;
    $('#earnPrev').onclick = () => { const [y, m] = S.month.split('-').map(Number); go(new Date(Date.UTC(y, m - 2, 1)).toISOString().slice(0, 7)); };
    $('#earnNext').onclick = () => { const [y, m] = S.month.split('-').map(Number); go(new Date(Date.UTC(y, m, 1)).toISOString().slice(0, 7)); };
    $('#earnToday').onclick = () => go(todayTW().slice(0, 7));
    $$('#earnFilt button').forEach((b) => {
      b.onclick = () => {
        S.filt = b.dataset.v; $$('#earnFilt button').forEach((x) => x.classList.toggle('on', x === b));
        if (S.sel.t === 'ev') { const e = evs()[S.sel.i]; if (e && !passF(e)) S.sel = { t: 'week' }; }
        drawCal(); drawPanel(); markRows();
      };
    });
    drawCal(); drawPanel();
    let lastNarrow = window.innerWidth <= 640;
    let rzT = 0;
    window.addEventListener('resize', () => { lastNarrow = window.innerWidth <= 640; clearTimeout(rzT); rzT = setTimeout(() => { if (document.getElementById('earnGrid') && root.offsetParent) drawCal(); }, 120); });
    root.dataset.ready = !d ? 'empty' : S.seed ? 'seed' : 'full';
  }
  window.TwEarnings = { render, state: S, pick };
})();
