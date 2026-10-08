/* ============================================================================
   財報日曆（#earnings）—— Andy 2026-10-05 16:00：
   「總覽下方新增"財報日曆"，並不是子分頁，需要向行事曆那樣標示出台股大公司的開財報日期，
    以及FED公布重大數據也需要標示出來，並且需要在旁邊有點及該個股後，出現對於這次財包的分析及展望(包含FED消息)」

   版面：左＝7 欄真月曆（固定 6 列，切月整張卡不會變高）；右＝固定側欄面板（固定高、內部捲動）：
     · 還沒點 → 本週重點（目前分頁那一類這週一～週日的事件；FED 消息分頁另列接下來的 FOMC／CPI）
   分類分頁：公司財報｜公司法說｜FED 消息，沒有「全部」，預設公司財報、重新整理一律回公司財報（不記憶，同 #330 選股）。
     · 點公司標籤（或下面時間表的一列）→ 這次財報的分析與展望（每段標題旁 ⓘ 滑過看出處）＋ FED 背景
     · 點 FED／美國數據標籤 → 數據說明、上次數值（FRED）、市場關注點、下一次日期
     · 點日期格（或「＋N」）→ 那一天的完整清單
   面板標題列（← 回本週重點＋股票名稱代號＝個股頁連結）釘在面板最上方，捲動不跑；面板底部不放按鈕。
   （月曆下方的「大公司時間表」10-05 晚 Andy「下方不需要」已拿掉。）

   資料：data/earnings.json（pipeline/compute/earnings.py，build_payload 產出）。
   ⚠ 預覽分支吃的是正式站的資料，earnings.json 上正式站之前不存在 —— 那時退回分支內附的種子檔 earnings_seed.json
     （同一支程式用真資料產出）。畫面不寫「種子」「資料日」（10-06 Andy：內部口徑、資料日期膠囊一律拿掉）。
   「分析與展望」是規則＋數字組出來的句子，口徑在 earnings.py 檔頭。
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
    /* 2026-10-05（晚，Andy：「裡面有 3 大分類：公司財報、公司法說、FED 消息」）：g＝分類 rep／conf／fed */
    conf: { g: 'conf', lab: '法說會（公司自辦）', cls: 'kconf' },
    board: { g: 'rep', lab: '財報董事會（公告）', cls: 'kboard' },
    report: { g: 'rep', lab: '已公布財報', cls: 'kboard' },
    invite: { g: 'conf', lab: '受邀法說（券商論壇）', cls: 'kinv' },
    est: { g: 'rep', lab: '預估財報日', cls: 'kest' },
    rev: { g: 'rep', lab: '營收期限', cls: 'ktw' },
    qdl: { g: 'rep', lab: '財報法定期限', cls: 'ktw' },
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
    mic: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="5.5" y="1.5" width="5" height="8" rx="2.5" fill="currentColor"/><path d="M3.5 7.5a4.5 4.5 0 0 0 9 0M8 12v2.5M5.5 14.5h5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    tw: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1.5h8M4 14.5h8M5 1.5c0 4 6 4.5 6 6.5s-6 2.5-6 6.5M11 1.5c0 4-6 4.5-6 6.5s6 2.5 6 6.5" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>',
  };
  const icOf = (k) => (KIND[k] || {}).g === 'conf' ? IC.mic : ['board', 'report', 'est'].includes(k) ? IC.co : k === 'fomc' || k === 'minutes' ? IC.fed : (KIND[k] || {}).g === 'fed' ? IC.data : IC.tw;

  /* FED／期限標籤上的字：寬螢幕寫全、手機（≤640）用短字（格子只有 48px） */
  const SHORT = { fomc: 'FOMC', minutes: 'FOMC 紀要', cpi: 'CPI', nfp: '非農', pce: 'PCE', gdp: 'GDP', rev: '營收期限', qdl: '財報期限' };
  const S = { data: null, seed: false, month: null, sel: { t: 'week' }, filt: 'rep' };

  function injectCSS() {
    if (document.getElementById('earnCss')) return;
    const s = document.createElement('style'); s.id = 'earnCss';
    s.textContent = `
@media (max-width:820px){ :root:not(.l4) .tab[data-view="earnings"]{display:none!important} }
#v-earnings .edisc{margin:8px 2px 0;font-size:12px;line-height:16px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings .card{margin-bottom:var(--sp-3)}
#v-earnings .card h3{flex-wrap:nowrap;white-space:nowrap;min-width:0}
#v-earnings .card h3 small{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .row.spread{flex-wrap:nowrap;gap:10px;min-width:0}
/* 2026-10-06 12:10（Andy：「全部拿掉，並平均分散 三個分頁」＋12:14「分頁和本週重點之間那一大塊空白好奇怪」）：
   分頁同時控制左邊月曆與右邊面板 → 照產業地圖（#321 .nbsw）：分頁列放在整塊內容的最上方，下面直接接 .nbbody 內容框
   （選中那顆疊在框的上框線上、底色相連，中間不留空白）。三顆等寬、填滿整排：用 grid 而不是 flex:1，
   因為選中那顆的 padding 比較大（.nbsw 規範），flex 會讓它比較寬。tabdrag.js 改的是 CSS order，grid 一樣吃。 */
#v-earnings #earnFilt{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:end;margin-top:6px}
#v-earnings #earnFilt>button{min-width:0;overflow:hidden;text-overflow:ellipsis}
#v-earnings .earnbody{margin-bottom:0;background:var(--panel)}
#v-earnings .earnbody .elegend{margin-top:4px}
#v-earnings .ewrap{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:12px;margin-top:6px}
#v-earnings .ehd{display:flex;align-items:center;gap:8px;margin-bottom:6px;white-space:nowrap;height:32px;min-width:0}
#v-earnings .ehd b{font-size:16px;width:118px;text-align:center;flex:none}
#v-earnings .ehd .sp{flex:1}
#v-earnings .elegend{display:flex;flex-wrap:nowrap;gap:12px;align-items:center;margin:2px 0 8px;font-size:12px;color:var(--ink-2);white-space:nowrap;overflow:hidden;min-width:0}
#v-earnings .elegend span{display:inline-flex;align-items:center;gap:5px;flex:none}
#v-earnings .elegend i.wk{background:color-mix(in srgb,var(--ink) 9%,var(--panel));border:1px solid var(--line)}
#v-earnings .elegend i.hd{background:color-mix(in srgb,var(--amber) 13%,var(--panel-2));border:1px solid var(--amber)}
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
#v-earnings .ed .dn i{font-style:normal;font-size:12px;padding:0 5px;border-radius:999px;background:var(--cyan);color:var(--ontop);line-height:15px}
#v-earnings .chip{display:flex;align-items:center;gap:3px;height:18px;padding:0 4px;border-radius:5px;border:1px solid transparent;
  font-family:inherit;font-size:12px;font-weight:500;line-height:18px;white-space:nowrap;overflow:hidden;cursor:pointer;color:var(--ink);background:var(--panel-3);min-width:0;width:100%;text-align:left}
#v-earnings .chip .cd{font:600 12px var(--mono);flex:none}
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
#v-earnings .kest svg{color:var(--cyan)}
#v-earnings .ktw{background:transparent;color:var(--ink-2);border:1px solid var(--line)}
#v-earnings .ktw svg{color:var(--cyan)}
#v-earnings .kfomc{background:color-mix(in srgb,var(--violet) 30%,var(--panel-2));color:var(--ink)}
#v-earnings .kfomc svg{color:var(--violet)}
#v-earnings .kdata{background:color-mix(in srgb,var(--lime) 18%,var(--panel-2));color:var(--ink)}
#v-earnings .kdata svg{color:var(--lime)}
#v-earnings .ed .more{font-size:12px;color:var(--cyan);line-height:16px;white-space:nowrap;border:0;background:none;padding:0 2px;text-align:left;cursor:pointer;font-family:inherit}
#v-earnings .epanel{border:1px solid var(--line);border-radius:10px;background:var(--panel-2);padding:10px 12px;box-sizing:border-box;
  height:${32 + 6 + 30 + 20 + ROWS * 98 + ROWS * 4}px;overflow:auto;min-width:0}
#v-earnings .ph{display:flex;align-items:center;gap:8px;white-space:nowrap;min-width:0;margin-bottom:4px}
#v-earnings .ph b{font-size:15.5px;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .ph .sp{flex:1}
#v-earnings .ps{font-size:12.5px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:8px}
#v-earnings .badge{display:inline-block;font-size:12px;padding:0 7px;border-radius:999px;border:1px solid currentColor;line-height:18px;white-space:nowrap;flex:none}
#v-earnings .badge.ann{color:var(--amber)} #v-earnings .badge.est{color:var(--ink-3);border-style:dashed} #v-earnings .badge.sch{color:var(--violet)}
#v-earnings .tags{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 4px}
#v-earnings .tag{font-size:12px;padding:2px 8px;border-radius:999px;background:var(--panel-3);white-space:nowrap}
#v-earnings .tag b{font-weight:600;margin-left:4px}
#v-earnings .up{color:var(--rise)} #v-earnings .down{color:var(--fall)}
#v-earnings .sec{border-top:1px solid var(--line);padding:8px 0 6px}
#v-earnings .sec h4{margin:0 0 3px;font-size:13.5px;display:flex;gap:6px;align-items:baseline;white-space:nowrap;min-width:0}
#v-earnings .sec h4 small{font-weight:400;font-size:12px;color:var(--ink-3);overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .sec p{margin:3px 0;font-size:13px;line-height:1.55;color:var(--ink-2)}
#v-earnings .flk{display:flex;align-items:center;gap:10px;margin-top:6px;font-size:12px;white-space:nowrap;overflow:hidden;min-width:0;color:var(--ink-3)}
#v-earnings .flk svg{width:12px;height:12px;color:var(--cyan);flex:none}
#v-earnings .flk a{color:var(--cyan);text-decoration:none;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .flk a:hover,#v-earnings .flk a:focus-visible{text-decoration:underline;outline:none}
#v-earnings table.mt{width:100%;border-collapse:collapse;font-size:12px;table-layout:fixed;margin:4px 0}
#v-earnings table.mt th{color:var(--ink-3);font-weight:600;text-align:right;padding:3px 4px;border-bottom:1px solid var(--line);white-space:nowrap}
#v-earnings table.mt td{text-align:right;padding:3px 4px;font-family:var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings table.mt th:first-child,#v-earnings table.mt td:first-child{text-align:left}
#v-earnings .nl{list-style:none;margin:4px 0;padding:0}
#v-earnings .nl li{display:flex;gap:6px;font-size:12.5px;line-height:20px;white-space:nowrap;min-width:0}
#v-earnings .nl li .d{font:12px var(--mono);color:var(--ink-3);flex:none}
#v-earnings .nl li .t{overflow:hidden;text-overflow:ellipsis;min-width:0;color:var(--ink-2)}
#v-earnings .nl li a.t{color:var(--ink-2);text-decoration:none} #v-earnings .nl li a.t:hover{color:var(--cyan)}
#v-earnings .elist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}
#v-earnings .erow{display:grid;grid-template-columns:80px 12px minmax(0,1fr) auto;gap:6px;align-items:center;height:30px;padding:0 8px;
  border:1px solid var(--line);border-radius:8px;background:var(--panel-3);color:var(--ink);font:inherit;font-size:13px;text-align:left;cursor:pointer;white-space:nowrap;width:100%}
#v-earnings .erow:hover,#v-earnings .erow:focus-visible{outline:none;border-color:var(--cyan)}
#v-earnings .erow .d{font:12px var(--mono);color:var(--ink-3)}
#v-earnings .erow .t{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .erow .b{font-size:12px;color:var(--ink-3)}
#v-earnings .erow.kfomc svg{color:var(--violet)} #v-earnings .erow.kdata svg{color:var(--lime)} #v-earnings .erow.kconf svg,#v-earnings .erow.kinv svg{color:var(--amber)}
#v-earnings .erow.kboard svg{color:var(--cyan)} #v-earnings .erow.kest svg,#v-earnings .erow.ktw svg{color:var(--cyan)}
#v-earnings .erow.kfomc,#v-earnings .erow.kdata,#v-earnings .erow.kconf,#v-earnings .erow.kboard,#v-earnings .erow.kinv,#v-earnings .erow.kest,#v-earnings .erow.ktw{background:var(--panel-3);border-style:solid;border-color:var(--line);color:var(--ink)}
#v-earnings .lt{display:block;font-size:13px;color:var(--ink-2);margin:10px 0 6px;white-space:nowrap}
#v-earnings .kv{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;font-size:13px;margin:4px 0}
#v-earnings .kv dt{color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings .kv dd{margin:0;text-align:right;font-family:var(--mono);white-space:nowrap}
#v-earnings .sec[data-sec=conf] .kv{grid-template-columns:auto minmax(0,1fr)}
#v-earnings .sec[data-sec=conf] .kv dd{font-family:inherit;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .kv .pv{grid-column:1/-1;font-size:12px;color:var(--ink-3);margin-top:-2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings .note{font-size:12.5px;color:var(--ink-3);line-height:1.55}
#v-earnings .ph.stk{position:sticky;top:-10px;z-index:3;background:var(--panel-2);margin:-10px -12px 6px;padding:8px 12px;border-bottom:1px solid var(--line)}
#v-earnings .ph .plink{font-size:15.5px;font-weight:700;color:var(--ink);text-decoration:none;overflow:hidden;text-overflow:ellipsis;min-width:0;cursor:pointer}
#v-earnings .ph .plink:hover,#v-earnings .ph .plink:focus-visible{text-decoration:underline;color:var(--cyan);outline:none}
#v-earnings .ph .btn{flex:none}
/* 2026-10-06：週末反灰／休市標記由 calgrid.js 提供；這裡是面板裡的小圖、星級、數值列 */
#v-earnings .stars{color:var(--amber);font-size:13px;letter-spacing:1px;white-space:nowrap;flex:none}
#v-earnings .stars i{font-style:normal;color:var(--ink-3);opacity:.5}
#v-earnings .mini{display:grid;grid-template-columns:92px minmax(0,1fr);gap:10px;align-items:center;margin:6px 0 2px}
#v-earnings .mk{min-width:0;text-align:center}
#v-earnings .mk b{display:block;font:700 19px var(--mono);line-height:24px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings .mk small{display:block;font-size:12px;color:var(--ink-3);line-height:16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings .mc{min-width:0}
#v-earnings .mc svg{width:100%;height:84px;display:block}
#v-earnings .ml{display:flex;justify-content:space-between;gap:6px;font-size:12px;color:var(--ink-3);white-space:nowrap;margin-top:2px}
#v-earnings .ml span{overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .ml .lg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
#v-earnings .pe-track{position:relative;height:10px;border-radius:999px;background:linear-gradient(90deg,color-mix(in srgb,var(--fall) 55%,var(--panel-3)),var(--panel-3) 50%,color-mix(in srgb,var(--rise) 55%,var(--panel-3)));margin:14px 6px 6px}
#v-earnings .pe-track b{position:absolute;top:-4px;width:4px;height:18px;border-radius:2px;background:var(--ink);transform:translateX(-2px)}
#v-earnings .fcard{border:1px solid var(--line);border-radius:10px;background:var(--panel-3);padding:8px 10px;margin:0 0 8px}
#v-earnings .fcard .fh{display:flex;align-items:center;gap:6px;white-space:nowrap;min-width:0}
#v-earnings .fcard .fh b{font-size:14px;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-earnings .fcard .fh .sp{flex:1}
#v-earnings .fcard .fh svg{color:var(--lime)}
#v-earnings .fcard .fd{font-size:12px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:2px 0 4px}
#v-earnings .fcard p{margin:2px 0;font-size:13px;line-height:1.5;color:var(--ink-2)}
#v-earnings .fcard p b{color:var(--ink);font-weight:600;margin-right:4px}
#v-earnings .fnum{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin:6px 0 2px}#v-earnings .fnum.n1{grid-template-columns:minmax(0,1fr)}
#v-earnings .fnum div{border:1px solid var(--line);border-radius:8px;text-align:center;padding:3px 4px;min-width:0;background:var(--panel-2)}
#v-earnings .fnum small{display:block;font-size:12px;color:var(--ink-3);line-height:16px}
#v-earnings .fnum b{display:block;font:600 13px var(--mono);line-height:20px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-earnings .verd{display:inline-block;font-size:12px;padding:0 7px;border-radius:999px;border:1px solid currentColor;line-height:18px;white-space:nowrap;cursor:help}
#v-earnings .verd.bull{color:var(--rise)} #v-earnings .verd.bear{color:var(--fall)}
@media (max-width:1100px){#v-earnings .ewrap{grid-template-columns:minmax(0,1fr)}#v-earnings .epanel{height:540px}
  #v-earnings .row.spread{flex-wrap:wrap}}
@media (max-width:640px){
  #v-earnings .eg{grid-template-rows:20px repeat(${ROWS},78px);gap:3px}
  #v-earnings .chip .nm{display:none}
  #v-earnings .chip .lb{font-size:12px;text-overflow:clip}
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
    try { await window.CalGrid.load(); } catch (e) { /* 沒有休市日資料就只標週末 */ }
    // v2（2026-10-06）才有圖表序列與 FED 說明；正式站還是舊格式時退回種子（預覽用）
    if (d && Array.isArray(d.events) && (d.v || 1) >= 2) { S.data = d; S.seed = false; return; }
    // 退回：分支內附的種子檔（預覽版、或正式站還沒產出 earnings.json 的那一輪）
    try {
      const r = await fetch('earnings_seed.json', { cache: 'no-store' });
      if (r.ok) { const j = await r.json(); if (j && Array.isArray(j.events)) { S.data = j; S.seed = true; return; } }
    } catch (e) { /* 也讀不到 → 下面空狀態 */ }
    S.data = null;
  }
  const evs = () => (S.data && S.data.events) || [];
  const co = (c) => ((S.data && S.data.companies) || {})[c];
  /* 2026-10-06 12:10 拿掉「全部」：月曆、本週重點、當天清單一律只顯示目前這一類（Andy：分類不可混） */
  const passF = (e) => (KIND[e.k] || {}).g === S.filt;
  const FILT_LAB = { rep: '公司財報', conf: '公司法說', fed: 'FED 消息' };
  const rankOf = (e) => (e.code && co(e.code) ? (co(e.code).rank || 99) : 99);
  const sortEv = (a, b) => (ORDER[a.k] - ORDER[b.k]) || (rankOf(a) - rankOf(b));
  const idxOf = (e) => evs().indexOf(e);
  const label = (e) => (e.code ? `${e.code} ${e.name || ''}` : (KIND[e.k] && KIND[e.k].g === 'fed' ? (e.k === 'fomc' ? 'FOMC 決議' : e.k === 'minutes' ? 'FOMC 紀要' : KIND[e.k].lab) : e.title));

  /* ------------------------------------------------------------------ 骨架 */
  function skeleton(root) {
    const how = (k, q, li) => `<div class="howtxt" id="how-${k}" hidden>${A().howHTML(q, li)}</div>`;
    const hbtn = (k, t) => `<button class="howbtn pop" data-how="${k}" data-ttl="${t}" type="button" aria-label="${t}">?</button>`;
    /* ★ 2026-10-07 標題重複普查：頁首已有「財經日曆」，卡標題改成「頁名：這張在看什麼」（週期統計同一個模式）。*/
    root.innerHTML = `
<div class="card" id="earnCalCard">
  <div class="row spread"><h3>財經日曆：財報・法說・FED 行事曆 <small id="earnSub"></small> ${hbtn('earncal', '財經日曆怎麼看')}</h3></div>
  ${how('earncal', '', [
    '<b>大公司</b>＝市值前 50（收盤 × 最新一季股數，上市＋上櫃普通股，排除 ETF）。',
    '<b>公司財報</b>＝大公司公告的財報董事會與已公布財報；<b>公司法說</b>＝全部上市櫃公司公告的法說會；<b>FED 消息</b>＝FOMC 與美國重大數據的官方公布日。',
    '日曆上是美東日期，台灣時間在右側面板。',
    '所以：月初先看這個月有哪幾家要開法說、FOMC 在哪一天；法說前一週點進去，對照「這次財報看什麼」的月營收，就知道營收已反映多少、要看的是毛利率還是展望。'])}
  <div class="nbsw" id="earnFilt" role="tablist" aria-label="財經日曆分類"><button data-v="rep" class="on" type="button" role="tab">公司財報</button><button data-v="conf" type="button" role="tab">公司法說</button><button data-v="fed" type="button" role="tab">FED 消息</button></div>
  <div class="nbbody earnbody" id="earnBody">
  <div class="elegend" id="earnLegend"></div>
  <div class="ewrap">
    <div><div class="ehd"><button type="button" class="btn small" id="earnPrev" aria-label="上個月">‹ 上月</button>
      <b id="earnMonth"></b><button type="button" class="btn small" id="earnNext" aria-label="下個月">下月 ›</button>
      <button type="button" class="btn small" id="earnToday">回本月</button><span class="sp"></span></div>
      <div class="eg" id="earnGrid"></div></div>
    <div class="epanel" id="earnPanel" role="region" aria-label="分析面板" aria-live="polite"></div>
  </div>
  </div>
  <p class="edisc" id="earnDisc" role="note">ⓘ 純資料整理，不構成投資建議。</p>
</div>
`;
  }

  /* ------------------------------------------------------------------ 月曆 */
  function chipHTML(e, small) {
    const k = KIND[e.k] || KIND.rev;
    const on = S.sel.t === 'ev' && S.sel.i === idxOf(e) ? ' on' : '';
    const t = e.code ? `<span class="cd">${esc(e.code)}</span><span class="nm">${esc(e.name || '')}</span>`
      : `<span class="lb">${esc(SHORT[e.k] || '')}</span>`;
    const tip = `${e.d}（${wdOf(e.d)}）${e.code ? e.code + ' ' + (e.name || '') + '：' : ''}${e.title}`;
    return `<button type="button" class="chip ${k.cls}${on}" data-i="${idxOf(e)}" data-k="${e.k}"${e.code ? ` data-code="${esc(e.code)}"` : ''} title="${esc(tip)}">${icOf(e.k)}${t}</button>`;
  }
  /* 圖例＝只列目前分類有的種類（Andy：「法說就法說、財報就是財報，不可以參雜其他分頁內容」）；最後固定附週末／休市說明 */
  const LEG = [['rep', 'kboard', 'co', '財報董事會／已公布財報'], ['conf', 'kconf', 'mic', '自辦法說'], ['conf', 'kinv', 'mic', '受邀法說'],
    ['fed', 'kfomc', 'fed', 'FOMC'], ['fed', 'kdata', 'data', '美國數據']];
  function drawLegend() {
    const box = $('#earnLegend'); if (!box) return;
    box.innerHTML = LEG.filter((x) => x[0] === S.filt).map(([, c, ic, t]) => `<span><i class="${c}">${IC[ic]}</i>${t}</span>`).join('')
      + '<span><i class="wk"></i>週末</span><span><i class="hd"></i>台股休市日</span>';
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
      const hol = window.CalGrid ? window.CalGrid.tag(k) : '';
      const capE = hol ? Math.max(1, cap - 1) : cap;
      const show = L.length > capE ? L.slice(0, capE - 1) : L;
      const more = L.length > show.length ? `<button type="button" class="more" data-d="${k}">＋${L.length - show.length}</button>` : '';
      const cg = window.CalGrid ? window.CalGrid.cls(k) : '';
      cells += `<div class="ed${cg}${isT ? ' today' : ''}${S.sel.t === 'day' && S.sel.d === k ? ' sel' : ''}" data-d="${k}" data-n="${L.length}"${hol ? ' data-hol="1"' : ''}${window.CalGrid && window.CalGrid.isWeekend(k) ? ' data-we="1"' : ''}>
        <button type="button" class="dn" data-d="${k}" aria-label="${k}${isT ? '（今天）' : ''} ${L.length} 項">${'<b>' + d + '</b>'}${isT ? '<i>今天</i>' : ''}</button>${hol}${show.map((e) => chipHTML(e)).join('')}${more}</div>`;
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
      const n = evs().filter((e) => e.d > b).filter(passF).slice(0, 12);
      return `<p class="note">本週無事件</p>${n.length ? `<span class="lt">接下來</span><ul class="elist">${n.map(rowHTML).join('')}</ul>` : ''}`;
    })();
    return `${phead('本週重點', `<span class="badge sch">${md(a)}–${md(b)}</span>`, { noBack: true })}
      ${L.length ? `<ul class="elist" id="earnWeekList">${L.map(rowHTML).join('')}</ul>` : ahead}
      ${S.filt !== 'fed' ? '' : `<span class="lt">接下來的 FED 與美國數據（星數＝重要性）</span>${upcomingFed(6).map((e) => fedCard(e, true)).join('')}`}
      ${S.filt === 'fed' ? '' : (() => { const later = evs().filter((e) => e.d > b).filter(passF).slice(0, 20);
        return later.length && L.length ? `<span class="lt">之後的${FILT_LAB[S.filt] || '事件'}</span><ul class="elist" id="earnLaterList">${later.map(rowHTML).join('')}</ul>` : ''; })()}
      ${S.filt === 'fed' ? '' : (() => {
        /* 拿掉「全部」之後，單一分類一週常只有幾筆（公司財報尤其少），面板下半大片空白（Andy 1006：「空白處不可以太多」）→
           不夠 12 列時，補「近 30 天已過」的同類事件（新到舊），讓讀者看得到這一類最近發生了什麼。 */
        const shown = L.length + Math.min(20, evs().filter((e) => e.d > b).filter(passF).length);
        if (shown >= 12) return '';
        const a30 = new Date(new Date(a + 'T00:00:00Z').getTime() - 30 * 864e5).toISOString().slice(0, 10);
        const past = evs().filter((e) => e.d < a && e.d >= a30).filter(passF).sort((x, y) => (x.d < y.d ? 1 : x.d > y.d ? -1 : sortEv(x, y))).slice(0, 12 - shown);
        return past.length ? `<span class="lt">近 30 天已過的${FILT_LAB[S.filt]}</span><ul class="elist" id="earnPastList">${past.map(rowHTML).join('')}</ul>` : ''; })()}`;
  }
  function panelDay(d) {
    const L = evs().filter((e) => e.d === d).filter(passF).sort(sortEv);
    return `${phead(`${d}（${wdOf(d)}）`, `<span class="badge sch">${L.length} 項</span>`)}
      ${L.length ? `<ul class="elist" id="earnDayList">${L.map(rowHTML).join('')}</ul>` : '<p class="note">當天無事件</p>'}`;
  }
  /* 面板標題列（釘在面板最上方，內容捲動時不動）：左＝「← 回本週重點」，中＝標題（有代號就是連結，進個股頁），右＝徽章 */
  function phead(title, badge, o) {
    o = o || {};
    const t = o.code ? `<a class="plink" href="#stock/${esc(o.code)}" data-code="${esc(o.code)}" title="看 ${esc(o.name || '')} ${esc(o.code)} 個股頁">${esc(title)}</a>` : `<b>${esc(title)}</b>`;
    return `<div class="ph stk">${o.noBack ? '' : '<button type="button" class="btn small" id="earnBack">← 回本週重點</button>'}${t}<span class="sp"></span>${badge || ''}</div>`;
  }
  /* 出處：不整行顯示，改成標題旁小 ⓘ，滑過只顯示「出處：機構名」—— 不放資料日期（DECISIONS #329「這類資訊一律拿掉」，
     協調者 10-06 定口徑：ⓘ 一律不放日期）。
     寫法跟全站 App.srcInfo 一樣（claude/copy-trim2 分支，還沒上 main）—— 有就直接用它（日期參數一律給空字串）；沒有就產出同樣的標記
     （class srcinfo＋title；樣式等 .srcinfo 進 index.html 才有，這之前借既有的 .muted 灰字）。App.srcInfo 上 main 後退回寫法可刪。
     FED 事件的 src 以前帶著管線的查證紀錄（「（https://…；查證 …（WebSearch 摘要，未讀原文））」「FRED 日程未取得時的退回值」）；
     10-06 起產出端只寫發布機關名（pipeline/compute/earnings.py macro_events），這裡的替換留著當保險（舊種子檔、舊快取）。 */
  const AGENCY = { federalreserve: '聯準會', bls: '美國勞工統計局', bea: '美國經濟分析局' };
  const cleanSrc = (src) => String(src || '').replace(/（[^（）]*（[^（）]*）[^（）]*）|（[^（）]*）/g, (m) => {
    if (!/https?:|查證|未取得|退回|WebSearch|未讀原文/.test(m)) return m;
    const h = /https?:\/\/(?:www\.)?([a-z]+)\./.exec(m), ag = h && AGENCY[h[1]];
    return ag && !String(src).includes(ag) ? `（${ag}）` : '';
  }).trim();
  const si = (src) => {
    const s0 = cleanSrc(src), f = A() && A().srcInfo;
    if (!s0) return '';
    if (f) return f(s0, '');
    return `<span class="srcinfo muted" tabindex="0" role="note" aria-label="出處" title="${esc('出處：' + s0)}">ⓘ</span>`;
  };
  const toneCls = (t) => (t > 0 ? 'up' : t < 0 ? 'down' : '');
  /* ------------------------------------------------------------------ 小圖
     2026-10-08（Andy：「日曆圖內的長條圖都要優化，符合我們原本要的漸層效果及回應互動效果」）：
     以前這裡自己手刻一套 SVG 直條（跟 ETF 行事曆各一份），平的實心方塊、沒有提示框。
     改用 calgrid.js 的共用小圖（CalGrid.mini → App.chart）：同色漸層、頂端圓角、寬 ≤ 12px、滑過加亮其他變淡＋提示框、點了選取。
     圖內仍然不放文字（標籤用 HTML，字級守得住 12px 下限）。 */
  const nz = (v) => v != null && isFinite(v);
  const cgMini = (spec) => (window.CalGrid && window.CalGrid.mini ? window.CalGrid.mini(spec) : '');
  const sgn = (v, d) => (v == null ? '—' : (v > 0 ? '+' : '') + (+v).toFixed(d == null ? 1 : d));
  const mini = (k1, k2, k3, chart, lab) => `<div class="mini"><div class="mk"><b class="${k3 || ''}">${k1}</b><small>${k2}</small></div><div class="mc">${chart}<div class="ml">${lab}</div></div></div>`;
  function chartFor(s) {
    const ser = s.series || [];
    if (s.key === 'rev' && ser.length >= 3) {
      const last = ser[ser.length - 1];
      const ch = cgMini({ labels: ser.map((r) => r[0]), bars: { vals: ser.map((r) => r[1]), color: 'var(--cat-1)', name: '營收' },
        line: { vals: ser.map((r) => r[2]), color: 'var(--amber)', name: '年增' }, aria: '月營收與年增率',
        tip: (i) => `<b>${esc(ser[i][0])}</b><br>營收 <b>${esc(ser[i][1])} 億</b><br>年增 ${sgn(ser[i][2])}%` });
      return mini(`${last[1]} 億`, `年增 ${sgn(last[2])}%`, toneCls(last[2]), ch,
        `<span>${esc(ser[0][0])}</span><span class="lg"><i style="background:var(--cat-1)"></i>營收　<i style="background:var(--amber)"></i>年增</span><span>${esc(last[0])}</span>`);
    }
    if (s.key === 'profit' && ser.length >= 3) {
      const last = ser[ser.length - 1];
      const ch = cgMini({ labels: ser.map((r) => r[0]), bars: { vals: ser.map((r) => r[1]), color: (x) => (x >= 0 ? 'var(--cat-1)' : 'var(--fall)'), name: 'EPS' },
        line: { vals: ser.map((r) => r[2]), color: 'var(--amber)', name: '毛利率' }, aria: 'EPS 與毛利率',
        tip: (i) => `<b>${esc(ser[i][0])}</b><br>EPS <b>${esc(ser[i][1])}</b><br>毛利率 ${ser[i][2] == null ? '—' : esc(ser[i][2]) + '%'}` });
      return mini(`${(+last[1]).toFixed(2)}`, `EPS・毛利率 ${last[2] == null ? '—' : last[2] + '%'}`, '', ch,
        `<span>${esc(ser[0][0])}</span><span class="lg"><i style="background:var(--cat-1)"></i>EPS　<i style="background:var(--amber)"></i>毛利率</span><span>${esc(last[0])}</span>`);
    }
    if (s.key === 'inst' && ser.length >= 5) {
      const tot = ser.reduce((a, r) => a + (r[1] || 0), 0);
      const ch = cgMini({ labels: ser.map((r) => r[0]), bars: { vals: ser.map((r) => r[1]), color: (x) => (x >= 0 ? 'var(--rise)' : 'var(--fall)'), name: '三大法人' }, aria: '三大法人每日買賣超',
        tip: (i) => `<b>${esc(ser[i][0])}</b><br>三大法人 <b>${ser[i][1] > 0 ? '買超' : '賣超'} ${Math.abs(ser[i][1]).toLocaleString()} 張</b>` });
      return mini(`${tot > 0 ? '+' : ''}${tot.toLocaleString()}`, `20 日合計（張）${tot >= 0 ? '買超' : '賣超'}`, toneCls(tot), ch,
        `<span>${esc(md(ser[0][0]))}</span><span>三大法人每日買賣超（紅買綠賣）</span><span>${esc(md(ser[ser.length - 1][0]))}</span>`);
    }
    if (s.key === 'val' && s.pos != null && s.lo != null) {
      return `<div class="mini"><div class="mk"><b>${s.pe} 倍</b><small>第 ${s.pos} 百分位</small></div><div class="mc"><div class="pe-track" title="位置 ${s.pos}（0＝自己歷史最便宜、100＝最貴）"><b style="left:${Math.max(2, Math.min(98, s.pos))}%"></b></div>
        <div class="ml"><span>${s.lo} 倍（低）</span><span>自己近 20 季本益比</span><span>${s.hi} 倍（高）</span></div></div></div>`;
    }
    return '';
  }
  /* FED 數值的小走勢（一條折線＋最後一點） */
  function sparkFor(x) {
    const ser = (x && x.series) || []; if (ser.length < 3) return '';
    const vals = ser.map((r) => r[1]), isBar = !!(x.label && /新增就業/.test(x.label));
    const tip = (i) => `<b>${esc(ser[i][0])}</b><br>${esc(x.label || '')} <b>${esc(ser[i][1])}</b>`;
    const ch = cgMini(isBar ? { labels: ser.map((r) => r[0]), bars: { vals, color: (v) => (v >= 0 ? 'var(--cat-1)' : 'var(--fall)'), name: x.label || '' }, tip, aria: x.label || '' }
      : { labels: ser.map((r) => r[0]), line: { vals, color: 'var(--cat-1)', name: x.label || '' }, tip, aria: x.label || '' });
    return mini(esc(x.value), esc(x.label), '', ch, `<span>${esc(ser[0][0])}</span><span>近 ${ser.length} 期</span><span>${esc(ser[ser.length - 1][0])}</span>`);
  }


  const starsHTML = (n) => `<span class="stars" title="重要性 ${n}／5" aria-label="重要性 ${n} 星">${'★'.repeat(n)}<i>${'★'.repeat(Math.max(0, 5 - n))}</i></span>`;
  const refYM = (ref) => { let m = /(\d{4})\s*年\s*(\d{1,2})\s*月/.exec(ref || ''); if (m) return `${m[1]}-${String(m[2]).padStart(2, '0')}`; m = /(\d{4})\s*Q(\d)/.exec(ref || ''); return m ? `${m[1]}-${String((+m[2] - 1) * 3 + 1).padStart(2, '0')}` : null; };
  /* 前值／公布值＋偏多偏空（預期值沒有合法免費來源，不顯示也不編）；沒有 FRED 數字就整格不出現。 */
  function fedNums(e, info) {
    const x = ((S.data.fed || {}).snap || {})[info.main];
    if (!x) return { html: '', verdict: '' };
    const released = e.d <= todayTW() && refYM(e.ref) && x.date && x.date.slice(0, 7) === refYM(e.ref);
    const prevTxt = released ? (x.prev || '—').replace(/^前一期（[^）]*）/, '') : x.value;
    let verdict = '';
    if (released && info.dir && info.dir !== 'none' && nz(x.v) && nz(x.pv) && x.v !== x.pv) {
      const up = x.v > x.pv, bull = info.dir === 'up_bull' ? up : !up;
      verdict = `<span class="verd ${bull ? 'bull' : 'bear'}" title="${esc(info.rule || '')}">${bull ? '偏多' : '偏空'}</span>`;
    }
    const cells = [`<div><small>${released ? '前值' : '最近一次'}</small><b title="${esc(x.label)}（${esc(x.date)}）">${esc(prevTxt)}</b></div>`];
    if (released) cells.push(`<div><small>公布值</small><b>${esc(x.value)}</b></div>`);
    return { html: `<div class="fnum n${cells.length}">${cells.join('')}</div>`, verdict };
  }
  const EXT = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M9 2h5v5M14 2 7.5 8.5M12 9.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  function fedLinks(info) {
    const L = (info.links || []).filter((l) => /^https:\/\//.test(l.url || ''));
    return L.length ? `<div class="flk">${EXT}<span>官方數據</span>${L.map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer" title="${esc(l.name)}（新分頁開啟）">${esc(l.name)}</a>`).join('')}</div>` : '';
  }
  function fedCard(e) {
    const info = ((S.data.fed || {}).info || {})[e.k] || {};
    const n = fedNums(e, info);
    return `<div class="fcard" data-k="${e.k}"><div class="fh">${icOf(e.k)}<b>${esc(e.title)}</b><span class="sp"></span>${n.verdict}${info.stars ? starsHTML(info.stars) : ''}</div>
      <div class="fd">${e.d}（${wdOf(e.d)}，美東）・台灣 ${esc(e.tw || '—')}${e.ref ? '・' + esc(e.ref) : ''}</div>
      ${info.what ? `<p><b>是什麼</b>${esc(info.what)}</p>` : ''}${info.how ? `<p><b>怎麼看</b>${esc(info.how)}</p>` : ''}${info.impact ? `<p><b>影響</b>${esc(info.impact)}</p>` : ''}
      ${n.html}${fedLinks(info)}</div>`;
  }
  function upcomingFed(limit) {
    const t = todayTW(), seen = {}, out = [];
    evs().filter((e) => (KIND[e.k] || {}).g === 'fed' && e.d >= t).forEach((e) => { if (!seen[e.k] && out.length < limit) { seen[e.k] = 1; out.push(e); } });
    return out;
  }
  function fedBlock(keys) {
    const snap = ((S.data && S.data.fed) || {}).snap || {};
    const have = (keys || []).filter((k) => snap[k]);
    if (!have.length) return '';
    return `<dl class="kv">${have.map((k) => { const x = snap[k]; return `<dt>${esc(x.label)}（${esc(x.date)}）</dt><dd>${esc(x.value)}</dd>${x.prev ? `<div class="pv">${esc(x.prev)}</div>` : ''}`; }).join('')}</dl>`;
  }
  function panelFed(e) {
    const info = ((S.data && S.data.fed && S.data.fed.info) || {})[e.k] || {};
    const snap = (S.data.fed || {}).snap || {};
    const nx = evs().filter((x) => x.k === e.k && x.d > e.d)[0];
    const sparks = (info.rel || []).map((k) => sparkFor(snap[k])).filter(Boolean).slice(0, 3).join('');
    return `${phead(e.title, '<span class="badge sch">排程</span>')}
      ${fedCard(e)}
      ${sparks ? `<div class="sec" data-sec="spark"><h4>近期數值走勢${si('FRED（聯準會聖路易分行經濟資料庫）')}</h4>${sparks}</div>` : ''}
      ${(info.focus || []).length ? `<div class="sec"><h4>市場關注點</h4>${info.focus.map((t) => `<p>・${esc(t)}</p>`).join('')}</div>` : ''}
      ${info.rule && info.dir && info.dir !== 'none' ? `<div class="sec" data-sec="rule"><h4>偏多偏空規則</h4><p>${esc(info.rule)}</p></div>` : ''}
      ${nx ? `<div class="sec"><h4>下一次${si(e.src)}</h4><p>${nx.d}（${wdOf(nx.d)}）・台灣 ${esc(nx.tw || '')}</p></div>` : ''}`;
  }
  function secHTML(s) {
    const tbl = s.table ? `<table class="mt"><thead><tr>${s.table.cols.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${s.table.rows.map((r) =>
      `<tr>${r.map((v, i) => `<td class="${i && typeof v === 'number' && s.key === 'rev' && i > 1 ? toneCls(v) : ''}">${v == null ? '—' : esc(typeof v === 'number' && i > 1 && s.key === 'rev' ? (v > 0 ? '+' : '') + v : v)}</td>`).join('')}</tr>`).join('')}</tbody></table>` : '';
    const items = s.items ? `<ul class="nl">${s.items.map((n) => `<li><span class="d">${esc(md(n.d))}</span>${n.u ? `<a class="t" href="${esc(n.u)}" target="_blank" rel="noopener" title="${esc(n.t)}">${esc(n.t)}</a>` : `<span class="t" title="${esc(n.t)}">${esc(n.t)}</span>`}<span class="d">${esc(n.s === 'cnyes' ? '鉅亨' : n.s === 'technews' ? 'TechNews' : n.s)}</span></li>`).join('')}</ul>` : '';
    const ch = chartFor(s);
    const lines = ch ? s.lines.slice(0, s.key === 'val' || s.key === 'inst' ? 2 : 1) : s.lines;
    return `<div class="sec" data-sec="${s.key}" data-chart="${ch ? 1 : 0}"><h4>${esc(s.t)}${si(s.src)}</h4>${ch}${s.key === 'news' ? '' : lines.map((t) => `<p>${esc(t)}</p>`).join('')}${ch ? '' : tbl}${items}</div>`;
  }
  /* 法說會這一場的資訊：只放重大訊息內文裡公司自己寫的欄位（日期／時間／地點／擇要），沒寫的欄位就不出現 */
  function confSec(e) {
    if (KIND[e.k].g !== 'conf') return '';
    const r = [['日期', `${e.d}（${wdOf(e.d)}）`], ['時間', e.time], ['地點', e.place], ['內容', e.brief]].filter((x) => x[1]);
    return `<div class="sec" data-sec="conf"><h4>這場法說 <small>${esc(KIND[e.k].lab)}</small>${si(e.src)}</h4>
      <dl class="kv">${r.map(([k, v]) => `<dt>${k}</dt><dd title="${esc(v)}">${esc(v)}</dd>`).join('')}</dl></div>`;
  }
  function panelCo(e) {
    const c = co(e.code);
    if (!c) return `${phead(`${e.name || ''} ${e.code}`, '<span class="badge ann">已公告</span>', { code: e.code, name: e.name })}
      <div class="ps" title="${esc(e.title)}">${esc(e.title)}</div>${confSec(e)}`;
    const nxt = c.next;
    const isEst = e.status === '預估';
    const head = `${phead(`${c.name} ${e.code}`, `<span class="badge ${isEst ? 'est' : 'ann'}">${isEst ? '預估' : e.status === '公告' ? '已公告' : esc(e.status || '')}</span>`, { code: e.code, name: c.name })}
      <div class="ps" title="${esc(e.title)}">${md(e.d)}（${wdOf(e.d)}）${esc((KIND[e.k] || {}).lab || '')}・${c.rank ? '市值第 ' + c.rank + ' 名・' : ''}${esc(e.title)}</div>`;
    const basis = '';
    const tags = (c.tags || []).length ? `<div class="tags">${c.tags.map((t) => `<span class="tag">${esc(t.l)}<b class="${toneCls(t.tone)}">${esc(t.v)}</b></span>`).join('')}</div>` : '';
    const f = (S.data && S.data.fed) || {};
    const fn = f.next || {};
    const fedBody = `${fn.fomc ? `<p>下一次 FOMC 利率決議：${md(fn.fomc.d)}（台灣 ${esc(fn.fomc.tw || '')}）${fn.cpi ? `；下一次 CPI：${md(fn.cpi.d)}（台灣 ${esc(fn.cpi.tw || '')}）` : ''}。</p>` : ''}
      ${fedBlock(['policy', 'cpi_yoy', 'core_pce_yoy', 'unrate'])}`;
    const fedSec = fedBody.trim() ? `<div class="sec" data-sec="fed"><h4>FED 背景</h4>${fedBody}</div>` : '';
    return `${head}${basis}${confSec(e)}${tags}<p class="note">對應 <b>${esc(c.target || '')}</b> 財報</p>
      ${(c.secs || []).map(secHTML).join('')}${S.filt === 'fed' ? fedSec : ''}`;
  }
  function drawPanel() {
    const box = $('#earnPanel'); if (!box) return;
    if (!S.data) { box.innerHTML = '<p class="note">尚無財經日曆資料</p>'; return; }
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
    if (window.CalGrid && window.CalGrid.mount) window.CalGrid.mount(box);   // 面板小圖（共用 C 款直條）
    const back = $('#earnBack', box); if (back) back.onclick = () => pick({ t: 'week' });
    $$('.plink', box).forEach((a) => { a.onclick = (ev) => { ev.preventDefault(); A().goStock(a.dataset.code); }; });
  }
  function panelTw(e) {
    return `${phead(e.title, '<span class="badge sch">期限</span>')}
      <div class="ps">${e.d}（${wdOf(e.d)}）</div><div class="sec"><p>${esc(e.note || '')}</p></div>`;
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
    const rh = window.CalGrid ? window.CalGrid.fit(g, ROWS, 56, 110, 4, 42) : Math.max(56, Math.min(98, Math.floor((avail - 20 - ROWS * 4) / ROWS)));
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
    S.filt = 'rep';      // 每次進頁都回公司財報（不記憶）
    skeleton(root);
    $('#earnPanel').innerHTML = '<p class="note">載入中…</p>';
    await loadData();
    const d = S.data;
    $('#earnSub').textContent = !d ? '' : `大公司＝市值前 ${(d.universe && d.universe.n) || 50}`;
    /* 2026-10-08 權限矩陣 earn.tab：切到其他月份算一次（回本月不算） */
    const goQ = (m) => { if (m !== todayTW().slice(0, 7) && window.TwQuota && !window.TwQuota.act('earn.tab', 'tab', m)) return; go(m); };
    $('#earnPrev').onclick = () => { const [y, m] = S.month.split('-').map(Number); goQ(new Date(Date.UTC(y, m - 2, 1)).toISOString().slice(0, 7)); };
    $('#earnNext').onclick = () => { const [y, m] = S.month.split('-').map(Number); goQ(new Date(Date.UTC(y, m, 1)).toISOString().slice(0, 7)); };
    $('#earnToday').onclick = () => goQ(todayTW().slice(0, 7));
    $$('#earnFilt button').forEach((b) => {
      b.onclick = () => {
        S.filt = b.dataset.v; $$('#earnFilt button').forEach((x) => x.classList.toggle('on', x === b));
        if (S.sel.t === 'ev') { const e = evs()[S.sel.i]; if (e && !passF(e)) S.sel = { t: 'week' }; }
        drawLegend(); drawCal(); drawPanel(); markRows();
      };
    });
    drawLegend(); drawCal(); drawPanel();
    let lastNarrow = window.innerWidth <= 640;
    let rzT = 0;
    window.addEventListener('resize', () => { lastNarrow = window.innerWidth <= 640; clearTimeout(rzT); rzT = setTimeout(() => { if (document.getElementById('earnGrid') && root.offsetParent) drawCal(); }, 120); });
    root.dataset.ready = !d ? 'empty' : S.seed ? 'seed' : 'full';
  }
  window.TwEarnings = { render, state: S, pick };
})();
