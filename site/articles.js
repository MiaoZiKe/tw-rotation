/* ============================================================================
   精選文章（#articles、#articles/<類別>、#article/<id>）＋管理區「精選文章管理」（#admin/articles）—— 2026-10-14 建、2026-10-16 改版
   ----------------------------------------------------------------------------
   Andy 2026-10-14：「幫我成立一個精選文章母分頁，裡面三個小分頁……精選文章也需要分類……分成 消息 介紹 知識……
   有日期可以篩選文章以及關鍵字搜尋標題」；位置標在左側選單「今日市場 → 總覽」正下方（總覽和財經日曆之間）。
   Andy 2026-10-16 看完預覽版：
     「日期 Default 前一個月到今天」「需要填滿版面，不可以過多空白」
     「需要有族群篩選功能，上方分頁需要不同顏色以及小圖示，名稱改比比消息、比比知識、比比產業鏈，或是你幫我想更好的名稱」
     「文章內需要退回上一頁功能，且內文需要附上圖表和對應圖，或是產業關析圖，設備拆解圖……有數據都需要圖表化」
   → 分類改名：news＝比比快訊（橘、喇叭）、intro＝比比產業鏈（青綠、鏈結）、know＝比比知識（紫、燈泡）、全部＝全部文章（中性）。
     「快訊」比「消息」更像一個欄目名，而且跟選股策略的「消息面」不會撞名。顏色與圖示在頁內分頁、側欄子項、卡片徽章、麵包屑同一組（CAT_IC＋--art-*）。

   這一頁回答的問題：「網站整理過、值得讀的文章有哪些？這一篇在講什麼、數字長怎樣、跟哪些族群與股票有關？」
     · 列表頁：上方分類分頁、標題關鍵字、族群（下拉多選）、日期（預設＝台北今天往前一個月到今天）；
       卡片自適應格線（1440 三欄、800 兩欄、390 一欄）；寬螢幕右側「快速瀏覽」（各分類篇數、熱門族群一鍵篩選、最近更新）。
       所以該怎麼用：先挑類別或族群，再用關鍵字或日期縮小範圍，點卡片進去讀。
     · 單篇頁：「← 返回」（有上一頁就回上一頁，直接開網址的就回該類別清單）、麵包屑、內文區塊、圖表與示意圖、
       相關台股、站內相關頁面、資料來源、免責、文末「回到清單」；寬螢幕右側目錄。
   內文區塊（全部吃 JSON、textContent／esc 輸出、不收 HTML）：
     h／p／ul／callout／table／stocks（原有）＋ kpi（數字卡）＋ chart（bar／line／barline／hbar／range，ECharts）
     ＋ flow（產業關係圖：欄由左到右、手機由上到下，SVG 曲線箭頭）＋ stack（剖面拆解圖：由上到下疊層、右側引出線說明）。
     ＋ steps（編號流程圖：橫向一排、手機直向）＋ compare（2～4 欄對照卡，欄頂色條依 tone）。
   Andy 2026-10-16 看完第二版：
     「這邊的大小需要一致」→ 拿掉 2×2 焦點卡，清單每張卡同寬同高（內容過長截斷）。
     「版面需要調整適當大小，左右側還有空白處」→ 單篇內容欄填滿主欄（扣右側目錄），寬螢幕改放大字級而不是限寬留白。
     「需要新增點閱次數」→ 卡片與單篇「眼睛＋N 次」（會員 Worker /v1/articles/view、/v1/articles/stats；失敗就不寫）、管理區多一欄。
     「內容除了圖表，盡可能新增剖析、分解 說明圖片」→ steps／compare 兩種說明圖區塊。
     「圖表色彩需要豐富點且多樣，不要太單一」→ 文章專用調色盤 --art-p1..7（只這一頁用，紅綠保留給漲跌）。
     防複製與浮水印是全站的，在 site/protect.js，不在這支。

   資料：site/articles/index.json（清單）＋ site/articles/posts/<id>.json（點進單篇才讀）。
     ⚠ 放在 site/articles/ 而不是 site/data/：site/data/ 是 gitignore、由工作流每天重寫；文章是人工產出、要進版控。
   安全：文章內容一律當純文字（esc() 跳脫後才放進畫面），不收 HTML；圖表提示框是 HTML，所以名稱一律先 esc；
     外部網址只收 http(s)；站內連結只收 # 開頭；股票代號只收英數 4～6 碼；文章 id 只收英數、底線、點、減號。
   驗收：scripts/_uitest.py「精選文章1014」。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  /* 類別圖示（Lucide 同一套線寬，currentColor 上色）：喇叭＝快訊、鏈結＝產業鏈、燈泡＝知識、四格＝全部 */
  const CAT_IC = {
    all: '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    news: '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
    intro: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    know: '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
  };
  const icon = (k, sz) => `<svg class="artic" viewBox="0 0 24 24" width="${sz || 16}" height="${sz || 16}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${CAT_IC[k] || CAT_IC.all}</svg>`;
  /* 類別：名稱＋色（--art-<k>，深淺主題各一組，在 css() 定義）。紅綠保留給漲跌，所以快訊用橘、產業鏈用青綠（偏藍，跟跌的綠分得開）、知識用紫 */
  const CATS = { news: { t: '比比快訊' }, intro: { t: '比比產業鏈' }, know: { t: '比比知識' } };
  /* 手機（≤640）分頁用的短名（mobile4.css 檔尾「精選文章分頁」那節用 attr(data-s) 換上）：
     2026-10-16 Andy「手機版的分頁需要適當調整寬度」—— 360 寬四格各只有 ~84px，「比比產業鏈＋篇數」塞不下，短名才能四格等寬、不換行、不被切 */
  const CAT_S = { all: '全部', news: '快訊', intro: '產業鏈', know: '知識' };
  const ALL_T = '全部文章';
  const CAT_KEYS = Object.keys(CATS);
  const okId = (id) => /^[\w.-]{1,120}$/.test(String(id || ''));
  const okUrl = (u) => /^https?:\/\/[^\s"'<>]+$/i.test(String(u || ''));
  const okHash = (h) => /^#[^\s"'<>]*$/.test(String(h || ''));   // 站內連結只收 # 開頭（族群 id 可能是中文：#industry/group/ind_半導體業）
  const okCode = (c) => /^[0-9A-Z]{4,6}$/.test(String(c || ''));
  const okDate = (d) => /^\d{4}-\d{2}-\d{2}$/.test(String(d || ''));
  const num = (v) => { const x = typeof v === 'string' ? Number(v.replace(/,/g, '')) : Number(v); return isFinite(x) ? x : null; };
  const fmtN = (v) => { const x = num(v); return x == null ? '—' : x.toLocaleString('zh-TW', { maximumFractionDigits: 2 }); };

  /* 預設日期區間＝台北今天往前一個月到今天（Andy 10-16「日期 Default 前一個月到今天」）。
     用台北日期不用瀏覽器本地：人在國外打開也是同一個區間；一個月前的同一天不存在（3/31 → 2/31）就取那個月最後一天。 */
  const tpeToday = () => new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);
  const monthAgo = (ds) => {
    const [y, m, d] = ds.split('-').map(Number);
    let yy = y, mm = m - 1; if (mm < 1) { mm = 12; yy -= 1; }
    const last = new Date(Date.UTC(yy, mm, 0)).getUTCDate();
    return `${yy}-${String(mm).padStart(2, '0')}-${String(Math.min(d, last)).padStart(2, '0')}`;
  };
  const defRange = () => { const t = tpeToday(); return { from: monthAgo(t), to: t }; };

  const S = { views: null, statsP: null, statsAt: 0, idx: null, idxP: null, idxErr: false, cat: 'all', q: '', from: null, to: null, grp: new Set(), ms: null,
    posts: {}, cur: '', curData: null, backOk: false, topics: null, topicsP: null, tcat: 'all', tsort: 'desc', tsels: [], jobs: null, af: { cat: 'all', grp: '', from: '', to: '', q: '' }, jf: { kind: '', st: '', q: '' }, ss: { period: '30', from: '', to: '', cat: '', grp: '', daily: null, first: null } };

  /* 「← 返回」要不要用 history.back()：只有「在站內從別頁換過來」才有上一頁可回；直接貼網址開的，回該類別清單 */
  window.addEventListener('hashchange', (e) => {
    const nh = (location.hash || '').split('/')[0];
    if (nh === '#article') { try { S.backOk = !!(e.oldURL && new URL(e.oldURL).hash && new URL(e.oldURL).pathname === location.pathname); } catch (x) { S.backOk = false; } }
  });

  /* ------------------------------------------------------------------ 樣式
     字級、顏色、間距都引用主題變數（style_guide 二～四）。類別色與剖面圖層色是這一頁自己的語意色，深淺主題各定義一組。 */
  function css() {
    if (document.getElementById('artCss')) return;
    const s = document.createElement('style'); s.id = 'artCss';
    s.textContent = `
:root{--art-all:var(--ink-2);--art-news:#ff9d4a;--art-intro:#2fd1c1;--art-know:#b99bff;--art-hl:#f5c842;
  --art-t-chip:#5b9cff;--art-t-mem:#2ec4b6;--art-t-interposer:#f2c14e;--art-t-substrate:#ff8a65;--art-t-board:#a88bff;--art-t-bump:#c6cfdf;--art-t-other:#9aa6c0;--art-t-ink:#0b1220;
  /* 文章圖表調色盤（Andy 10-16：「圖表色彩需要豐富點且多樣，不要太單一」）：只給這一頁的區塊用，全站其他圖不吃這一組。
     刻意避開紅、綠（紅漲綠跌保留給漲跌）與標註用的金色（--art-hl）；彩度壓在不刺眼的範圍。深淺主題各一組，淺色每色都 ≥ 3:1。 */
  --art-p1:#5b9cff;--art-p2:#2ec4b6;--art-p3:#a88bff;--art-p4:#ff8a65;--art-p5:#ec74b5;--art-p6:#d39b5b;--art-p7:#4cc3ef;
  --art-tn-neutral:#8e9bb8;--art-tn-accent:#5b9cff;--art-tn-warn:#f2a93b;--art-tn-good:#2ec4b6}
:root[data-theme="light"]{--art-news:#b45309;--art-intro:#0f766e;--art-know:#7e22ce;--art-hl:#a36d00;
  --art-t-chip:#2f5fb3;--art-t-mem:#0f7d72;--art-t-interposer:#946200;--art-t-substrate:#c0461e;--art-t-board:#6d4bd1;--art-t-bump:#6b7385;--art-t-other:#5d6b88;--art-t-ink:#ffffff;
  --art-p1:#2563c9;--art-p2:#0e8a74;--art-p3:#6e44d6;--art-p4:#c9502b;--art-p5:#b83a7f;--art-p6:#8a5a1e;--art-p7:#0f7fa8;
  --art-tn-neutral:#5d6b88;--art-tn-accent:#2563c9;--art-tn-warn:#a86400;--art-tn-good:#0e8a74}
.pc1{--pc:var(--art-p1)}.pc2{--pc:var(--art-p2)}.pc3{--pc:var(--art-p3)}.pc4{--pc:var(--art-p4)}.pc5{--pc:var(--art-p5)}.pc6{--pc:var(--art-p6)}.pc7{--pc:var(--art-p7)}
.k-all{--k:var(--art-all)}.k-news{--k:var(--art-news)}.k-intro{--k:var(--art-intro)}.k-know{--k:var(--art-know)}
.artic{flex:none;display:block}
#v-articles .artcard{display:flex;flex-direction:column}
@media (min-width:821px){#v-articles .artcard{min-height:calc(100vh - 110px);box-sizing:border-box}}
#v-articles .artcard h3{display:flex;align-items:baseline;gap:var(--sp-2);flex-wrap:wrap}
#v-articles .artcard h3 small{font-size:var(--fs-sm);color:var(--ink-3);font-weight:400}
#artCats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));align-items:end;margin-top:var(--sp-2)}
#artCats>button{min-width:0;overflow:hidden;text-overflow:ellipsis;gap:6px}
#artCats>button .artic{color:var(--k)}
#artCats>button.on{color:var(--k);box-shadow:inset 0 3px 0 var(--k)}
#artCats>button.on em{color:var(--k)}
#artCats>button:hover{border-color:var(--k)}
#v-articles .nbbody{flex:1 1 auto;display:flex;flex-direction:column}
.artflt{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2) var(--sp-3);margin:var(--sp-2) 0 var(--sp-3)}
.artflt input{height:32px;box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:var(--r-sm,8px);padding:0 10px;font:inherit;font-size:var(--fs-sm)}
.artflt input[type=search]{flex:1 1 220px;min-width:0}
.artflt input[type=date]{width:150px;font-family:var(--mono);font-variant-numeric:tabular-nums}
.artflt input.chg{border-color:var(--amber)}
.artflt label{display:inline-flex;align-items:center;gap:6px;font-size:var(--fs-sm);color:var(--ink-2);white-space:nowrap}
.artflt #artGrp{--ms-w:12em}
.artflt #artGrp[hidden]{display:none}
.artflt .cnt{margin-left:auto;font-size:var(--fs-sm);color:var(--ink-2);white-space:nowrap;display:inline-flex;align-items:center;gap:var(--sp-2)}
.artflt .cnt b{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink)}
.artflt .cnt .rg{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:var(--fs-min);color:var(--ink-3);padding:1px 8px;border:1px solid var(--line);border-radius:999px}
.artmain{flex:1 1 auto;display:grid;grid-template-columns:minmax(0,1fr);gap:var(--sp-4);align-items:start}
@media (min-width:1280px){.artmain{grid-template-columns:minmax(0,1fr) 280px}}
/* 卡片一律同寬同高（Andy 10-16：「這邊的大小需要一致」）：格線決定寬、固定高度決定高，內容過長一律截斷（標題 2 行、副標 1 行、摘要 3 行、族群 1 行） */
.artlist{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));grid-auto-rows:var(--art-card-h,236px);gap:var(--gap-card,12px);align-items:stretch;align-content:start}
.artc{position:relative;display:flex;flex-direction:column;gap:6px;min-width:0;height:100%;box-sizing:border-box;padding:var(--sp-3) var(--sp-4) var(--sp-3) calc(var(--sp-4) + 4px);
  border:1px solid var(--line);border-radius:var(--r,12px);overflow:hidden;
  background:linear-gradient(135deg,color-mix(in srgb,var(--k) 8%,var(--panel)) 0%,var(--panel) 55%);color:var(--ink);text-decoration:none;transition:border-color .15s,transform .15s}
.artc::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--k)}
.artc .wm{position:absolute;right:-10px;bottom:-12px;color:var(--k);opacity:.08;pointer-events:none}
.artc:hover,.artc:focus-visible{border-color:var(--k);transform:translateY(-1px)}
.artc .r1{display:flex;align-items:center;gap:var(--sp-2);font-size:var(--fs-min);color:var(--ink-3);white-space:nowrap}
.artc .r1 .d{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink-2)}
.artc .r1 .rm{margin-left:auto;overflow:hidden;text-overflow:ellipsis}
.artc .tt{font-size:var(--fs-h3);font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.artc .st{font-size:var(--fs-sm);color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artc .sm{font-size:var(--fs-sm);color:var(--ink-3);line-height:1.6;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
/* 卡片最底一列：左邊族群膠囊（只留一行，放不下的藏起來）、右邊點閱數（不被族群擠掉） */
.artc .fr{margin-top:auto;display:flex;align-items:center;gap:var(--sp-2);min-width:0;flex:none}
.artc .ft{flex:1 1 auto;display:flex;gap:6px;flex-wrap:wrap;overflow:hidden;min-width:0;height:22px}
.artc .fr .artvw{font-size:var(--fs-min)}
.artc .tt,.artc .st,.artc .r1{flex:none}
.artc .sm{flex:0 1 auto;min-height:0}
/* 點閱次數（眼睛圖示＋N 次）：只有 API 有回數字才出現，失敗就整個不畫（不顯示 0） */
.artvw{display:inline-flex;align-items:center;gap:3px;font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink-2);white-space:nowrap;flex:none}
.artvw[hidden]{display:none}
.artvw svg{flex:none;color:var(--ink-3)}
.artc .ft .artgp{max-width:100%;overflow:hidden;text-overflow:ellipsis;box-sizing:border-box}
.arttags{display:flex;gap:6px;flex-wrap:nowrap;overflow:hidden;min-width:0}
.arttags span,.artgp{flex:none;font-size:var(--fs-min);color:var(--ink-2);background:var(--panel-3);border:1px solid var(--line);border-radius:999px;padding:1px 8px;white-space:nowrap}
.artgp{color:var(--ink);border-color:color-mix(in srgb,var(--k,var(--cyan)) 45%,var(--line))}
.artgp::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--k,var(--cyan));margin-right:5px;vertical-align:1px}
.artbadge{display:inline-flex;align-items:center;gap:4px;flex:none;font-size:var(--fs-min);font-weight:600;padding:1px 8px 1px 6px;border-radius:999px;color:var(--k);
  border:1px solid color-mix(in srgb,var(--k) 60%,transparent);background:color-mix(in srgb,var(--k) 12%,transparent);white-space:nowrap}
.artempty{grid-column:1/-1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:var(--sp-3);min-height:max(300px,calc(100vh - 420px));
  box-sizing:border-box;padding:28px 12px;text-align:center;color:var(--ink-2);font-size:var(--fs-body);border:1px dashed var(--line-2);border-radius:var(--r,12px)}
.artempty .artic{color:var(--ink-3)}
.artfoot{margin:var(--sp-3) 0 0;font-size:var(--fs-min);color:var(--ink-3)}
/* ⚠ 側欄用 div 不用 aside：全站 aside 規則是今日事件抽屜（position:fixed 貼右邊），用 aside 會整塊飛到畫面外。
   寬螢幕右側「快速瀏覽」：各分類篇數（受篩選影響）、熱門族群（點了就篩）、最近更新 */
.artside{display:none}
@media (min-width:1280px){.artside{display:flex;flex-direction:column;gap:var(--sp-3);position:sticky;top:var(--sp-3)}}
.artside section{border:1px solid var(--line);border-radius:var(--r,12px);background:var(--panel-2);padding:var(--sp-3)}
.artside h5{margin:0 0 var(--sp-2);font-size:var(--fs-sm);font-weight:700;color:var(--ink-2)}
.artside .cr{display:grid;grid-template-columns:20px minmax(0,1fr) 2.5em;align-items:center;gap:6px;width:100%;padding:5px 4px;border:0;border-radius:var(--r-sm,8px);background:none;color:var(--ink);font:inherit;font-size:var(--fs-sm);cursor:pointer;text-align:left}
.artside .cr:hover,.artside .cr.on{background:color-mix(in srgb,var(--k) 12%,transparent)}
.artside .cr .artic{color:var(--k)}
.artside .cr .bar{grid-column:2/4;height:4px;border-radius:2px;background:var(--panel-3);overflow:hidden}
.artside .cr .bar i{display:block;height:100%;background:var(--k);border-radius:2px}
.artside .cr b{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
.artside .gps{display:flex;flex-wrap:wrap;gap:6px}
.artside .gps button{font:inherit;font-size:var(--fs-min);height:26px;padding:0 9px;border-radius:999px;border:1px solid var(--line-2);background:var(--panel);color:var(--ink-2);cursor:pointer;white-space:nowrap}
.artside .gps button em{font-style:normal;font-family:var(--mono);color:var(--ink-3);margin-left:4px}
.artside .gps button.on{border-color:var(--t4-accent-solid,var(--cyan));color:var(--t4-accent-solid,var(--cyan));font-weight:700}
.artside .rc a{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 8px;padding:6px 2px;border-top:1px solid var(--line);color:var(--ink);text-decoration:none;font-size:var(--fs-sm)}
.artside .rc a:first-of-type{border-top:0}
.artside .rc a .artic{color:var(--k);margin-top:2px}
.artside .rc a span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.artside .rc a small{grid-column:2;font-family:var(--mono);font-size:var(--fs-min);color:var(--ink-3)}
.artside .rc a:hover span{color:var(--k)}
/* ---- 單篇 ---- */
/* 單篇：內容欄填滿主欄（扣掉右側目錄），不再限 1240 置中（Andy 10-16：「版面需要調整適當大小，左右側還有空白處」）。
   寬螢幕行寬變長，用字級跟著放大（15.5 → 最多 18px）維持每行字數好讀，不用限寬留白。 */
.artpage{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--sp-4);align-items:start}
@media (min-width:1280px){.artpage{grid-template-columns:minmax(0,1fr) 250px}}
.artpost{min-width:0}
.artback{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;margin-bottom:var(--sp-2);border:1px solid var(--line-2);border-radius:var(--r-sm,8px);background:var(--panel-3);color:var(--ink);font:inherit;font-size:var(--fs-sm);cursor:pointer}
.artback:hover{border-color:var(--k,var(--cyan));color:var(--k,var(--cyan))}
.artcrumb{display:flex;align-items:center;gap:6px;font-size:var(--fs-sm);color:var(--ink-3);margin-bottom:var(--sp-3);white-space:nowrap;overflow:hidden}
.artcrumb a{color:var(--cyan);text-decoration:none;display:inline-flex;align-items:center;gap:4px}
.artcrumb a.kc{color:var(--k)}
.artcrumb a:hover{text-decoration:underline}
.artcrumb .cur{color:var(--ink-2);overflow:hidden;text-overflow:ellipsis}
.artpost h2.artttl{margin:var(--sp-2) 0 6px;font-size:21px;line-height:1.4;font-weight:700}
.artpost .artsub{margin:0 0 var(--sp-3);font-size:14.5px;color:var(--ink-2);line-height:1.6}
.artmeta{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2) var(--sp-3);font-size:var(--fs-sm);color:var(--ink-2)}
.artmeta .mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.artpost .arttags{flex-wrap:wrap;margin:var(--sp-3) 0}
.artgps{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 var(--sp-3)}
.artgps .lb{font-size:var(--fs-sm);color:var(--ink-3)}
.artgps button.artgp{font:inherit;font-size:var(--fs-min);cursor:pointer;height:24px}
.artgps button.artgp:hover{border-color:var(--k)}
.artlead{margin:var(--sp-3) 0;padding:var(--sp-3) var(--sp-4);border-left:3px solid var(--k,var(--cyan));background:var(--panel-3);border-radius:0 var(--r-sm,8px) var(--r-sm,8px) 0;
  font-size:14.5px;line-height:1.75;color:var(--ink)}
/* 2026-10-16 Andy：「精選文章字體有點大 調整一下」—— 內文 15px（原本寬螢幕放大到 16～18px）、標題 21px、小標 16px */
.artbody{font-size:15px;line-height:1.8;color:var(--ink)}
.artbody h4{margin:var(--sp-5) 0 var(--sp-2);font-size:16px;line-height:1.4;font-weight:700;display:flex;align-items:center;gap:var(--sp-2);scroll-margin-top:16px}
.artbody h4::before{content:"";flex:none;width:4px;height:16px;border-radius:2px;background:var(--k,var(--cyan))}
.artbody p{margin:0 0 var(--sp-3)}
.artbody ul{margin:0 0 var(--sp-3);padding-left:1.4em}
.artbody li{margin:4px 0}
.artbody .callout{margin:var(--sp-4) 0;padding:var(--sp-3) var(--sp-4);border:1px solid color-mix(in srgb,var(--amber) 55%,transparent);border-radius:var(--r-sm,8px);
  background:color-mix(in srgb,var(--amber) 9%,var(--panel));font-weight:600}
.artbody .tbw{overflow-x:auto;margin:var(--sp-3) 0 var(--sp-4);border:1px solid var(--line);border-radius:var(--r-sm,8px)}
.artbody table{width:100%;border-collapse:collapse;font-size:13.5px;line-height:1.5}
.artbody th,.artbody td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.artbody th{white-space:nowrap}
.artbody td:first-child{white-space:nowrap;font-weight:600}   /* 第一欄多半是項目名：一行；其餘欄是說明句，讓它換行（不然整張表要左右捲）*/
.artbody th{font-size:var(--fs-min);font-weight:600;color:var(--ink-2);background:var(--panel-3)}
.artbody tr:last-child td{border-bottom:0}
.artstk{margin:var(--sp-4) 0}
.artstk .lbl{font-size:var(--fs-sm);font-weight:700;color:var(--ink-2);margin-bottom:var(--sp-2)}
.artstk .g{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:var(--sp-2)}
.artstk a{display:flex;flex-direction:column;gap:2px;min-width:0;padding:var(--sp-2) var(--sp-3);border:1px solid var(--line);border-radius:var(--r-sm,8px);background:var(--panel);
  color:var(--ink);text-decoration:none;line-height:1.5}
.artstk a:hover{border-color:var(--cyan)}
.artstk a .h{display:flex;gap:8px;align-items:baseline;white-space:nowrap;overflow:hidden}
.artstk a .h b{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--cyan)}
.artstk a .h span{font-weight:600;overflow:hidden;text-overflow:ellipsis}
.artstk a .w{font-size:var(--fs-sm);color:var(--ink-2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
/* ---- 圖類區塊共用外框（figure）：標題一行、圖、底部一行小字（說明＋資料來源） ---- */
.artfig{margin:var(--sp-4) 0;padding:var(--sp-3) var(--sp-4);border:1px solid var(--line);border-radius:var(--r,12px);background-color:var(--panel-2);font-size:var(--fs-body);line-height:1.5}
/* 圖類區塊自己也帶一層浮水印（protect.js 的 --tw-wm；整頁那層被卡片底色蓋住時仍看得到） */
.artfig,.artkpi .akc{background-image:var(--tw-wm,none);background-repeat:repeat;background-size:260px 170px}
.artfig .fh{display:flex;align-items:center;gap:var(--sp-2);margin:0 0 var(--sp-2);font-size:var(--fs-h3);font-weight:600;color:var(--ink)}
.artfig .fh::before{content:"";flex:none;width:4px;height:14px;border-radius:2px;background:var(--k,var(--cyan))}
.artfig .fn2{margin:var(--sp-2) 0 0;font-size:var(--fs-min);color:var(--ink-3);line-height:1.6}
.artfig .fn2 span+span::before{content:"　"}
.artfig .mk{margin:var(--sp-2) 0 0;display:flex;flex-wrap:wrap;gap:6px 12px;font-size:var(--fs-sm);color:var(--ink-2)}
.artfig .mk span::before{content:"◆";color:var(--art-hl);margin-right:4px}
.artchart .cv{width:100%;height:300px}
/* kpi 數字卡 */
.artkpi{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));gap:var(--sp-2);margin:var(--sp-4) 0}
.artkpi .akc{position:relative;overflow:hidden;min-width:0;padding:var(--sp-3);border:1px solid var(--line);border-radius:var(--r,12px);background-color:color-mix(in srgb,var(--pc,var(--cyan)) 7%,var(--panel-2));text-align:center;display:flex;flex-direction:column;gap:4px;justify-content:center}
.artkpi .akc::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--pc,var(--cyan))}
.artkpi .akl{color:color-mix(in srgb,var(--pc,var(--ink-2)) 55%,var(--ink-2))!important}
.artkpi .akl{font-size:var(--fs-sm);color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artkpi .akv{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artkpi .akv b{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:24px;font-weight:700;color:var(--ink);line-height:1.15}
.artkpi .akv small{font-size:var(--fs-sm);color:var(--ink-2);margin-left:4px}
.artkpi .akd{font-size:var(--fs-sm);font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:700}
.artkpi .akd.up{color:var(--rise)}.artkpi .akd.dn{color:var(--fall)}
.artkpi .akd span,.artkpi .akn{font-family:inherit;font-weight:400;color:var(--ink-3);font-size:var(--fs-min)}
.artkpi .akd span{margin-left:4px;font-family:"Noto Sans TC",system-ui,sans-serif}
/* flow 產業關係圖：欄由左到右、節點卡片在 SVG 線上面（卡片實心底，線從卡片後面穿過也不會壓到字） */
.artflow .fl{position:relative;display:grid;grid-template-columns:repeat(var(--cols,3),minmax(0,1fr));column-gap:48px;row-gap:28px;padding:4px 0}
.artflow svg.fe{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible;pointer-events:none;z-index:0}
.artflow .fe g path{fill:none;stroke:var(--ink-3);stroke-width:1.5;opacity:.7;transition:opacity .12s,stroke .12s}
.artflow .fe g polygon{fill:var(--ink-3);opacity:.8}
.artflow .fl.hov .fe g{opacity:.15}
.artflow .fl.hov .fe g.on{opacity:1}
.artflow .fl.hov .fe g.on path{stroke:var(--k,var(--cyan));stroke-width:2.2;opacity:1}
.artflow .fl.hov .fe g.on polygon{fill:var(--k,var(--cyan))}
.artflow .fcol{position:relative;z-index:1;display:flex;flex-direction:column;gap:10px;min-width:0}
.artflow .fch{align-self:flex-start;max-width:100%;font-size:var(--fs-min);font-weight:700;color:var(--fc);padding:2px 10px;border-radius:999px;border:1px solid color-mix(in srgb,var(--fc) 55%,transparent);
  background:color-mix(in srgb,var(--fc) 12%,var(--panel));white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artflow .fnodes{display:flex;flex-direction:column;gap:12px;flex:1;justify-content:center}
.artflow .fnd{min-width:0;padding:8px 10px;border:1px solid color-mix(in srgb,var(--fc) 35%,var(--line-2));border-left:3px solid var(--fc);border-radius:10px;background:color-mix(in srgb,var(--fc) 9%,var(--panel));transition:border-color .12s,box-shadow .12s}
.artflow .fnd:hover{border-color:var(--fc);box-shadow:0 0 0 1px var(--fc)}
.artflow .fnd>b{display:block;font-size:var(--fs-sm);font-weight:700;color:var(--ink);line-height:1.4}
.artflow .fnd>span{display:block;font-size:var(--fs-min);color:var(--ink-2);line-height:1.5;margin-top:2px}
.artflow .fcodes{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.artflow .fcodes a{display:inline-flex;align-items:center;gap:3px;height:22px;padding:0 7px;border-radius:999px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);text-decoration:none;
  font-size:var(--fs-min);white-space:nowrap}
.artflow .fcodes a b{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--cyan);font-weight:600}
.artflow .fcodes a:hover{border-color:var(--cyan)}
/* stack 剖面拆解圖：左邊疊層（寬度依 w、置中）、右邊引出線＋說明 */
.artstack .sk{display:flex;flex-direction:column;gap:6px}
.artstack .skr{display:grid;grid-template-columns:minmax(0,58fr) minmax(0,42fr);align-items:center;min-height:42px}
.artstack .skw{position:relative;display:flex;justify-content:center;align-items:center;height:100%;min-height:42px}
.artstack .skb{position:relative;z-index:1;display:flex;width:var(--w);height:38px;border-radius:6px;overflow:hidden;box-shadow:0 1px 0 rgba(0,0,0,.25)}
.artstack .sks{display:flex;align-items:center;justify-content:center;min-width:0;padding:0 6px;font-size:var(--fs-min);font-weight:700;color:var(--art-t-ink);
  background:linear-gradient(180deg,color-mix(in srgb,var(--tc) 100%,#fff 0%),color-mix(in srgb,var(--tc) 78%,var(--panel)));white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artstack .sks+.sks{border-left:2px solid var(--panel-2)}
.artstack .skw i{position:absolute;left:calc(50% + var(--w) / 2);right:0;top:50%;border-top:1px dashed var(--ink-3);opacity:.8}
.artstack .skl{position:relative;padding:4px 0 4px 14px;min-width:0}
.artstack .skl::before{content:"";position:absolute;left:0;top:50%;width:7px;height:7px;margin-top:-4px;border-radius:50%;background:var(--tc)}
.artstack .skl b{display:block;font-size:var(--fs-sm);font-weight:700;color:var(--ink);line-height:1.4}
.artstack .skl span{display:block;font-size:var(--fs-min);color:var(--ink-2);line-height:1.5}
.t-chip{--tc:var(--art-t-chip)}.t-mem{--tc:var(--art-t-mem)}.t-interposer{--tc:var(--art-t-interposer)}.t-substrate{--tc:var(--art-t-substrate)}
.t-board{--tc:var(--art-t-board)}.t-bump{--tc:var(--art-t-bump)}.t-other{--tc:var(--art-t-other)}
.artsec{margin-top:var(--sp-5);padding-top:var(--sp-3);border-top:1px solid var(--line)}
.artsec h4{margin:0 0 var(--sp-2);font-size:var(--fs-h3);font-weight:600}
.artlinks{display:flex;flex-wrap:wrap;gap:var(--sp-2)}
.artlinks a{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;border:1px solid var(--line-2);border-radius:999px;background:var(--panel-3);color:var(--ink);
  text-decoration:none;font-size:var(--fs-sm);white-space:nowrap}
.artlinks a::after{content:"›";color:var(--cyan)}
.artlinks a:hover{border-color:var(--cyan)}
.artsrc{margin:0;padding-left:1.4em;font-size:14px;line-height:1.7;color:var(--ink-2)}
.artsrc li{margin:4px 0;overflow-wrap:anywhere}
.artsrc a{color:var(--cyan)}
.artmore{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:var(--sp-2)}
.artmore{grid-auto-rows:150px}
.artmore .artc{padding-top:var(--sp-2);padding-bottom:var(--sp-2)}
.artmore .artc .tt{font-size:var(--fs-body)}
.artmore .artc .sm{display:none}
.artdisc{margin:var(--sp-4) 0 0;font-size:var(--fs-min);color:var(--ink-3);line-height:1.6}
.artend{display:flex;justify-content:center;margin-top:var(--sp-4)}
.artend a{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 18px;border:1px solid var(--k,var(--cyan));border-radius:999px;color:var(--k,var(--cyan));text-decoration:none;font-size:var(--fs-sm);font-weight:600}
.artend a:hover{background:color-mix(in srgb,var(--k,var(--cyan)) 12%,transparent)}
.arterr{padding:var(--sp-5) var(--sp-3);text-align:center;color:var(--ink-2);font-size:var(--fs-body)}
.arterr a{color:var(--cyan)}
/* steps 編號流程圖：橫向一排（每步＝圓形圖示＋編號＋標題＋說明，步與步之間箭頭）；手機改直向（圓在左、箭頭往下） */
.artsteps .stp{--g:28px;list-style:none;margin:var(--sp-2) 0 0;padding:0;display:grid;grid-template-columns:repeat(var(--n,4),minmax(0,1fr));column-gap:var(--g);row-gap:var(--sp-3)}
.artsteps .sti{position:relative;min-width:0;display:flex;flex-direction:column;align-items:center;text-align:center;gap:6px}
.artsteps .stc{position:relative;flex:none;width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:var(--pc);
  border:2px solid var(--pc);background:color-mix(in srgb,var(--pc) 14%,var(--panel));box-sizing:border-box}
.artsteps .stc em{position:absolute;right:-6px;top:-6px;min-width:20px;height:20px;padding:0 4px;box-sizing:border-box;border-radius:999px;background:var(--pc);color:var(--art-t-ink);
  font-style:normal;font-family:var(--mono);font-size:12px;font-weight:700;line-height:20px;text-align:center}
.artsteps .sti>b{display:block;max-width:100%;font-size:var(--fs-body);font-weight:700;color:var(--ink);line-height:1.4;overflow-wrap:anywhere}
.artsteps .sti>span{display:block;font-size:var(--fs-sm);color:var(--ink-2);line-height:1.6;overflow-wrap:anywhere}
.artsteps .sta{position:absolute;top:27px;left:calc(50% + 36px);width:calc(100% + var(--g) - 72px);height:2px;background:color-mix(in srgb,var(--pc) 60%,var(--ink-3));border-radius:1px}
.artsteps .sta::after{content:"";position:absolute;right:-1px;top:-4px;border-left:7px solid color-mix(in srgb,var(--pc) 60%,var(--ink-3));border-top:5px solid transparent;border-bottom:5px solid transparent}
/* compare 對照卡：2～4 欄，欄頂色條依 tone；結論固定貼在每欄底部（各欄結論同一條水平線） */
.artcmp .cmg{display:grid;grid-template-columns:repeat(var(--n,2),minmax(0,1fr));gap:var(--sp-3);margin-top:var(--sp-2)}
.artcmp .cmc{position:relative;min-width:0;display:flex;flex-direction:column;gap:var(--sp-2);padding:var(--sp-4) var(--sp-3) var(--sp-3);border:1px solid color-mix(in srgb,var(--tn) 40%,var(--line));
  border-radius:var(--r,12px);background:color-mix(in srgb,var(--tn) 6%,var(--panel));overflow:hidden}
.artcmp .cmc::before{content:"";position:absolute;left:0;right:0;top:0;height:4px;background:var(--tn)}
.artcmp .cmc h5{margin:0;font-size:var(--fs-h3);font-weight:700;color:var(--tn);line-height:1.4;overflow-wrap:anywhere}
.artcmp .cmc ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px}
.artcmp .cmc li{position:relative;padding-left:16px;font-size:var(--fs-sm);line-height:1.6;color:var(--ink);overflow-wrap:anywhere}
.artcmp .cmc li::before{content:"";position:absolute;left:2px;top:.62em;width:7px;height:7px;border-radius:2px;background:var(--tn)}
.artcmp .cmc .vd{margin:auto 0 0;padding:8px 10px;border-radius:8px;background:color-mix(in srgb,var(--tn) 14%,transparent);font-size:var(--fs-sm);font-weight:700;color:var(--ink);line-height:1.5}
.tn-neutral{--tn:var(--art-tn-neutral)}.tn-accent{--tn:var(--art-tn-accent)}.tn-warn{--tn:var(--art-tn-warn)}.tn-good{--tn:var(--art-tn-good)}
/* 單篇右側目錄（≥1280）：跟著捲動、點了捲到那一節（不換網址） */
.arttoc{display:none}
@media (min-width:1280px){.arttoc{display:flex;flex-direction:column;gap:var(--sp-3);position:sticky;top:var(--sp-3)}}
.arttoc section{border:1px solid var(--line);border-radius:var(--r,12px);background:var(--panel-2);padding:var(--sp-3)}
.arttoc h5{margin:0 0 var(--sp-2);font-size:var(--fs-sm);font-weight:700;color:var(--ink-2)}
.arttoc .tl button{display:block;width:100%;padding:5px 8px;border:0;border-left:2px solid var(--line-2);background:none;color:var(--ink-2);font:inherit;font-size:var(--fs-sm);text-align:left;cursor:pointer;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.arttoc .tl button:hover{color:var(--k);border-left-color:var(--k)}
.arttoc .sc{display:flex;flex-wrap:wrap;gap:6px}
.arttoc .sc a{display:inline-flex;gap:4px;align-items:center;height:24px;padding:0 8px;border-radius:999px;border:1px solid var(--line-2);background:var(--panel);color:var(--ink);text-decoration:none;font-size:var(--fs-min);white-space:nowrap}
.arttoc .sc a b{font-family:var(--mono);color:var(--cyan);font-weight:600}
@media (max-width:820px){.artflow .fl{column-gap:32px}}
/* 手機（≤640，只限 m4 這段寬度，桌機一行都不受影響）：一欄、內文 16px、標題 21px、篩選列兩行；分類分頁四格等寬；關係圖改由上到下 */
@media (max-width:640px){
  #artCats{grid-template-columns:repeat(4,minmax(0,1fr))!important;width:100%!important}
  :root.m4 #v-articles #artCats>button{padding:0 2px!important;gap:3px!important;min-width:0;font-size:12.5px!important}
  :root.m4 #v-articles #artCats>button em{display:none}
  :root.m4 #v-articles #artCats>button .artic{color:var(--k)}
  :root.m4 #v-articles #artCats>button.on{background:color-mix(in srgb,var(--k) 22%,transparent)!important;color:var(--k)!important;box-shadow:inset 0 -2px 0 var(--k)!important}
  :root.m4 #v-articles #artCats>button.on .artic{color:var(--k)}
  .artflt input[type=search]{flex:1 1 100%}
  .artflt label{flex:1 1 calc(50% - 8px);min-width:0}
  .artflt input[type=date]{width:100%;flex:1 1 0;min-width:0}
  .artflt #artGrp{flex:1 1 auto;--ms-w:100%}
  .artflt #artClr{flex:none}
  .artflt .cnt{margin-left:0}
  .artlist{--art-card-h:164px}
  .artc{padding:var(--sp-3) var(--sp-3) var(--sp-3) calc(var(--sp-3) + 4px)}
  .artc .sm{display:none}   /* 手機只留重點（準則 3）：摘要點進去才看 */
  .artempty{min-height:260px}
  .artpost h2.artttl{font-size:19px}
  .artbody{font-size:15px;line-height:1.8}
  .artlead{font-size:14.5px}
  .artbody h4{font-size:16px}
  .artstk .g{grid-template-columns:minmax(0,1fr)}
  .artfig{padding:var(--sp-3) var(--sp-2);margin-left:0;margin-right:0}
  .artchart .cv{height:260px}
  .artkpi{grid-template-columns:repeat(2,minmax(0,1fr))!important}
  .artkpi .akv b{font-size:20px}
  .artflow .fl{grid-template-columns:minmax(0,1fr)!important;row-gap:34px}
  .artflow .fnodes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .artflow .fnodes>.fnd:only-child{grid-column:1/-1}
  .artstack .skr{grid-template-columns:minmax(0,52fr) minmax(0,48fr)}
  .artstack .sks{padding:0 3px}
  .artsteps .stp{grid-template-columns:minmax(0,1fr)!important;row-gap:22px}
  .artsteps .sti{display:grid;grid-template-columns:56px minmax(0,1fr);column-gap:var(--sp-3);align-items:start;text-align:left}
  .artsteps .stc{grid-row:1/3}
  .artsteps .sti>b{align-self:end;padding-top:6px}
  .artsteps .sta{top:60px;left:27px;width:2px;height:calc(100% - 64px + 22px)}
  .artsteps .sta::after{right:auto;left:-4px;top:auto;bottom:-1px;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid color-mix(in srgb,var(--pc) 60%,var(--ink-3));border-bottom:0}
  .artcmp .cmg{grid-template-columns:minmax(0,1fr)!important}
}
`;
    s.textContent += ADM_CSS;
    document.head.appendChild(s);
  }
  const ADM_CSS = `
/* ---- 管理區 #admin/articles（2026-10-16 二版：Andy「版面需要調整適當，周圍不要空白太多，字體也需要調整適當，表格需要對齊」）---- */
#v-subadm:has(>.artadm){max-width:none;padding-left:var(--sp-2);padding-right:var(--sp-2)}   /* 管理區預設 1280 置中 —— 這頁表格欄位多，吃滿主欄 */
#v-subadm .artadm{margin-top:var(--gap-card,12px)}
#v-subadm .artadm h3{margin:0;font-size:15px;font-weight:700}
#v-subadm .artadm .hd{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap;margin-bottom:var(--sp-2)}
#v-subadm .artadm .hd .sp{flex:1}
#v-subadm .artadm .hd .muted{font-size:var(--fs-min)}
/* ---- 點閱統計（Andy 10-16：「新增統計數據，可以統計文章點擊次數，可以篩選族群 類型，需要將資訊可視化，並且圖表 排版格式follow 流量觀測」）
   版型照 admin.js 流量觀測：區段標題列（h2＋小字＋期間元件）→ KPI 卡 → 三欄格線卡片（h3 前面一條色塊、灰色副標、.cb 圖區吃滿） */
#artStats .secttl{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap;margin:var(--sp-2) 0 0}
#artStats .secttl h2{margin:0;font-size:18px;font-weight:700}
#artStats .secttl small{color:var(--ink-2);font-size:13px}
#artStats .secttl .sp{flex:1}
#artStats .secttl .rpk{flex-wrap:nowrap}
#artStats .secttl select{height:30px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);padding:0 8px;font:inherit;font-size:13px}
#artStats .secttl .icobtn{height:30px;width:30px;display:inline-grid;place-items:center;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer}
#artStats .secttl .icobtn svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
#artStats .trkpi{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:14px 16px;margin-top:12px}
#artStats .kpis{flex:1 1 560px;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:0}
#artStats .kpis>div{text-align:center;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:13px;color:var(--ink-2);white-space:nowrap;min-width:0}
#artStats .kpis b{display:block;font-size:24px;line-height:1.15;font-weight:700;color:var(--ink);font-family:var(--mono);font-variant-numeric:tabular-nums;max-width:100%;overflow:hidden;text-overflow:ellipsis}
#artStats .kpis b.t{font-family:inherit;font-size:15px;line-height:1.6}
#artStats .kpis .ic{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;margin-bottom:2px;background:color-mix(in srgb,currentColor 16%,transparent)}
#artStats .kpis .ic svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
#artStats .admgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:minmax(300px,auto);gap:var(--gap-card,12px);margin-top:12px}
#artStats .admgrid>.s2{grid-column:span 2}
#artStats .admgrid>.card{display:flex;flex-direction:column;min-width:0;padding:14px 16px;margin:0}
#artStats .admgrid>.card>h3{display:flex;align-items:center;gap:8px;white-space:nowrap;margin:0;font-size:var(--fs-h3,16px);font-weight:600;line-height:1.3}
#artStats .admgrid>.card>h3::before{content:"";width:4px;height:14px;border-radius:2px;background:var(--accent,var(--cyan));flex:none}
#artStats .admgrid>.card>.use{margin:2px 0 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px;line-height:20px;color:var(--ink-2)}
#artStats .cb{flex:1 1 auto;min-height:0;display:flex;flex-direction:column}
#artStats .empty{flex:1;display:grid;place-items:center;color:var(--ink-3);font-size:13px;min-height:120px}
#artStats .bars{flex:1;display:grid;grid-template-columns:minmax(0,9.5em) minmax(0,1fr) 6em;grid-auto-rows:32px;align-content:space-evenly;column-gap:12px;align-items:center;font-size:14px}
#artStats .bars .bl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#artStats #artStTop.bars{grid-template-columns:minmax(0,22em) minmax(0,1fr) 6em}
#artStats .secttl small{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#artStats .bars .bt{height:10px;background:var(--panel-3);border-radius:3px;overflow:hidden;display:flex}
#artStats .bars .bt i{display:block;height:100%}
#artStats .bars .bn{font-family:var(--mono);text-align:center;white-space:nowrap;font-variant-numeric:tabular-nums}
#artStats .bars .bn small{display:inline-block;width:3em;color:var(--ink-2);font-size:12px}
#artStats .dayplot{flex:1;display:flex;gap:6px;min-height:200px}
#artStats .dayy{display:flex;flex-direction:column;justify-content:space-between;font-family:var(--mono);font-size:11px;color:var(--ink-3);text-align:right;min-width:2.5em;padding-bottom:18px}
#artStats .days{flex:1;position:relative;display:flex;align-items:flex-end;gap:2px;border-bottom:1px solid var(--line);margin-bottom:18px}
#artStats .days .dc{flex:1;min-width:0;height:100%;display:flex;flex-direction:column-reverse;position:relative;cursor:default}
#artStats .days .dc i{display:block;width:100%;flex:none}
#artStats .days .dc i:last-child{border-radius:3px 3px 0 0}
#artStats .days .dc:hover{background:color-mix(in srgb,var(--ink) 6%,transparent)}
#artStats .days .dc .dd{position:absolute;bottom:-18px;left:50%;transform:translateX(-50%);font-family:var(--mono);font-size:10.5px;color:var(--ink-3);white-space:nowrap}
#artStats .days .avg{position:absolute;left:0;right:0;border-top:1px dashed var(--ink-3);pointer-events:none}
#artStats .days .avg b{position:absolute;left:4px;top:-18px;font-size:11px;font-weight:600;color:var(--ink-2);background:var(--panel);padding:0 4px}
#artStats .dn{flex:1;display:flex;align-items:center;gap:16px;min-height:200px}
#artStats .dnc{flex:none;width:150px;height:150px;border-radius:50%;position:relative;display:grid;place-items:center}
#artStats .dnc::after{content:"";position:absolute;inset:26px;border-radius:50%;background:var(--panel)}
#artStats .dnc span{position:relative;z-index:1;text-align:center;font-size:12px;color:var(--ink-2);line-height:1.3}
#artStats .dnc span b{display:block;font-family:var(--mono);font-size:20px;color:var(--ink)}
#artStats .lg{list-style:none;margin:0;padding:0;flex:1;min-width:0;display:flex;flex-direction:column;gap:8px;font-size:13px}
#artStats .lg li{display:grid;grid-template-columns:12px minmax(0,1fr) auto 3.5em;gap:8px;align-items:center}
#artStats .lg li i{width:10px;height:10px;border-radius:3px}
#artStats .lg li span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#artStats .lg li b{font-family:var(--mono);font-weight:600}
#artStats .lg li small{color:var(--ink-3);text-align:right;font-family:var(--mono)}
#artStats .note{font-size:12px;color:var(--ink-3);margin:6px 0 0}
/* Andy 10-16：「文章管理 每個表格清單都需要限制長度，太長都使用拉Bar」→ 三張表各自限高、表內捲動、表頭固定 */
#v-subadm .artadm .tbw{overflow:auto;max-height:var(--artadm-h,420px);overscroll-behavior:contain;border:1px solid var(--line);border-radius:var(--r-sm,8px)}
#v-subadm .artadm #artAdmTopics .tbw{--artadm-h:520px}
#v-subadm .artadm thead th{position:sticky;top:0;z-index:2}
#v-subadm .artadm tbody tr:last-child>td{border-bottom:0}
#v-subadm .artadm table{width:100%;min-width:860px;border-collapse:collapse;table-layout:fixed;font-size:13px}
#v-subadm .artadm th,#v-subadm .artadm td{padding:0 10px;border-bottom:1px solid var(--line);height:36px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left;vertical-align:middle}
#v-subadm .artadm th{color:var(--ink-2);font-weight:600;font-size:12px;background:var(--panel-3);height:32px}
#v-subadm .artadm th.c,#v-subadm .artadm td.c{text-align:center}
#v-subadm .artadm th.r,#v-subadm .artadm td.r{text-align:right}
#v-subadm .artadm td a{color:var(--ink);text-decoration:none}
#v-subadm .artadm td a:hover{color:var(--cyan)}
#v-subadm .artadm td.n{font-family:var(--mono);font-variant-numeric:tabular-nums}
#v-subadm .artadm .artbadge{vertical-align:middle}
#v-subadm .artadm .muted{color:var(--ink-3);font-size:12px}
#v-subadm .artadm .scb{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-variant-numeric:tabular-nums}
#v-subadm .artadm .scb i{display:block;width:40px;height:6px;border-radius:3px;background:var(--line);position:relative;overflow:hidden}
#v-subadm .artadm .scb i>b{position:absolute;left:0;top:0;bottom:0;border-radius:3px;background:var(--cat-1,var(--cyan))}
#v-subadm .artadm td.dm{color:var(--ink-2)}
#v-subadm .artadm .nbsw{margin-top:var(--sp-1)}
#v-subadm .artadm .nbbody{margin-bottom:0}
/* 主題可點選（整列）＋選取後的動作列 */
#v-subadm .artadm #artTpBody tr[data-tid]{cursor:pointer}
#v-subadm .artadm #artTpBody tr[data-tid]:hover>td{background:color-mix(in srgb,var(--cyan) 6%,transparent)}
#v-subadm .artadm #artTpBody tr[aria-selected=true]>td{background:color-mix(in srgb,var(--cyan) 14%,transparent)}
#v-subadm .artadm .rd{display:inline-grid;place-items:center;width:16px;height:16px;border-radius:4px;border:2px solid var(--line-2);vertical-align:middle;box-sizing:border-box;color:#fff;font-size:11px;line-height:1}
#v-subadm .artadm tr[aria-selected=true] .rd{border-color:var(--cyan);background:var(--cyan)}
#v-subadm .artadm tr[aria-selected=true] .rd::after{content:"✓"}
#v-subadm .artadm .tpact .sel{display:flex;align-items:center;gap:6px;flex-wrap:wrap;max-width:none;flex:1 1 100%;white-space:normal}
#v-subadm .artadm .tpchip{display:inline-flex;align-items:center;gap:4px;max-width:260px;height:26px;padding:0 4px 0 8px;border-radius:999px;border:1px solid var(--line-2);background:var(--panel);font-size:12.5px}
#v-subadm .artadm .tpchip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-subadm .artadm .tpchip button{height:20px!important;width:20px;padding:0!important;border:0!important;background:none!important;color:var(--ink-3)!important;font-size:14px!important;line-height:1;cursor:pointer}
#v-subadm .artadm .tpcnt{font-family:var(--mono);font-size:12px;color:var(--ink-3)}
/* 已上架文章的篩選列：類別、族群、日期、關鍵字 */
#v-subadm .artadm .aflt{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap;margin-bottom:var(--sp-2);font-size:13px}
#v-subadm .artadm .aflt .nbsw{margin:0}
#v-subadm .artadm .aflt select,#v-subadm .artadm .aflt input{height:30px;box-sizing:border-box;padding:0 8px;border:1px solid var(--line-2);border-radius:var(--r-sm,8px);background:var(--panel);color:var(--ink);font:inherit;font-size:13px}
#v-subadm .artadm .aflt input[type=search]{width:180px}
#v-subadm .artadm .aflt label{display:inline-flex;align-items:center;gap:4px;color:var(--ink-2);white-space:nowrap}
#v-subadm .artadm .aflt .cnt{margin-left:auto;font-size:12px;color:var(--ink-3);white-space:nowrap}
#v-subadm .artadm .aflt button.clr{height:30px;padding:0 10px;border-radius:var(--r-sm,8px);border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-size:12.5px;cursor:pointer}
#v-subadm .artadm .tpact{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap;padding:var(--sp-2) var(--sp-3);margin-bottom:var(--sp-2);border:1px solid var(--line);border-radius:var(--r-sm,8px);background:var(--panel-2);font-size:13px}
#v-subadm .artadm .tpact .sel{flex:0 1 auto;min-width:0;max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-subadm .artadm .tpact .sel b{color:var(--ink)}
#v-subadm .artadm .tpact input{flex:1 1 220px;min-width:160px;height:32px;box-sizing:border-box;padding:0 10px;border:1px solid var(--line-2);border-radius:var(--r-sm,8px);background:var(--panel);color:var(--ink);font:inherit;font-size:13px}
#v-subadm .artadm .tpact button{height:32px;padding:0 14px;border-radius:var(--r-sm,8px);border:1px solid var(--cyan);background:color-mix(in srgb,var(--cyan) 14%,var(--panel));color:var(--ink);font:inherit;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap}
#v-subadm .artadm .tpact button:disabled{opacity:.45;cursor:not-allowed;border-color:var(--line-2);background:var(--panel-3)}
#v-subadm .artadm .tpact .lk{display:flex;gap:6px;flex-wrap:wrap;width:100%;font-size:12px;color:var(--ink-3)}
#v-subadm .artadm .tpact .lk a{color:var(--cyan);text-decoration:none}
#v-subadm .artadm .tpmsg{font-size:12.5px;color:var(--ink-2);margin:0 0 var(--sp-2)}
#v-subadm .artadm .tpmsg.err{color:var(--red,#e5484d)}
#v-subadm .artadm .js{display:inline-flex;align-items:center;gap:4px;font-size:12px;padding:1px 8px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink-2);margin-right:4px}
#v-subadm .artadm .js.queued{border-color:color-mix(in srgb,var(--amber,#f5a524) 60%,transparent);color:var(--amber,#f5a524)}
#v-subadm .artadm .js.working{border-color:color-mix(in srgb,var(--cyan) 60%,transparent);color:var(--cyan)}
#v-subadm .artadm .js.done{border-color:color-mix(in srgb,var(--green,#30a46c) 60%,transparent);color:var(--green,#30a46c)}
#v-subadm .artadm .js.failed{border-color:color-mix(in srgb,var(--red,#e5484d) 60%,transparent);color:var(--red,#e5484d)}
#v-subadm .artadm .js .kd{font-style:normal;font-weight:700;font-size:11px;padding:0 5px;margin-left:-4px;border-radius:999px;color:#fff;line-height:16px}
#v-subadm .artadm .js .kd.article{background:#2563eb}
#v-subadm .artadm .js .kd.video{background:#db2777}
#v-subadm .artadm .js.kdc{border:0;padding:0;margin:0}#v-subadm .artadm .js.kdc .kd{margin:0;font-size:12px;padding:1px 8px;line-height:18px}
#v-subadm .artadm td button.cx{height:26px;padding:0 10px;border-radius:var(--r-sm,8px);border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font:inherit;font-size:12px;cursor:pointer}
`;

  /* ------------------------------------------------------------------ 資料 */
  const fetchJson = (url) => fetch(url, { cache: 'no-cache' }).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); });
  /* 族群欄位：[{id,name}]；只收字串、長度有上限（id 拿來比對與當 data-*，一律 esc 後才進 HTML） */
  const cleanGroups = (g) => (Array.isArray(g) ? g : []).filter((x) => x && typeof x.id === 'string' && x.id && x.id.length <= 80 && x.name)
    .map((x) => ({ id: x.id, name: String(x.name).slice(0, 40) }));
  function loadIndex() {
    if (S.idx) return Promise.resolve(S.idx);
    if (!S.idxP) {
      S.idxP = fetchJson('articles/index.json').then((j) => {
        const list = (j && Array.isArray(j.articles) ? j.articles : [])
          .filter((a) => a && okId(a.id) && CATS[a.cat] && okDate(a.date) && (!a.status || a.status === 'published'))
          .map((a) => Object.assign({}, a, { groups: cleanGroups(a.groups) }));
        list.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : String(a.id).localeCompare(String(b.id))));
        S.idx = { updated: j && j.updated, list }; S.idxErr = false; return S.idx;
      }).catch(() => { S.idxP = null; S.idxErr = true; return null; });
    }
    return S.idxP;
  }
  function loadPost(id) {
    if (!okId(id)) return Promise.resolve(null);
    if (S.posts[id]) return S.posts[id];
    S.posts[id] = fetchJson('articles/posts/' + encodeURIComponent(id) + '.json').catch(() => { delete S.posts[id]; return null; });
    return S.posts[id];
  }
  function loadTopics() {
    if (S.topics) return Promise.resolve(S.topics);
    if (!S.topicsP) S.topicsP = fetchJson('articles/topics.json').then((j) => { S.topics = { updated: j && j.updated, list: (j && Array.isArray(j.topics) ? j.topics : []).filter((t) => t && t.title) }; return S.topics; })
      .catch(() => { S.topicsP = null; return null; });
    return S.topicsP;
  }
  /* ------------------------------------------------------------------ 點閱次數（Andy 10-16：「需要新增點閱次數」）
     會員 Worker 的兩支公開 API（不需要登入，所以不帶權杖 t —— 也不經過 TwAccount.call，免得權杖失效時被當成登出）：
       POST {api}/v1/articles/view  {"id"} → {"ok":true,"id","views":N}   單篇打開時送一次；同一個瀏覽器分頁 30 分鐘內同一篇不重送（sessionStorage）
       POST {api}/v1/articles/stats {}     → {"views":{"<id>":N,…}}      列表頁載入時讀一次
     帳號 API 網址沒設定（repo 預設）、連不到、回非 2xx、格式不對 → 一律當作沒有數字，畫面上不寫（不顯示 0、不跳錯）。 */
  const VIEW_TTL = 30 * 60 * 1000;
  const acctApi = () => { const A = window.TwAccount; const u = A && typeof A.api === 'function' ? A.api() : ''; return typeof u === 'string' ? u : ''; };
  function apiPost(path, body) {
    const base = acctApi(); if (!base) return Promise.resolve(null);
    return fetch(base + path, { method: 'POST', headers: { 'content-type': 'text/plain' }, body: JSON.stringify(body || {}), credentials: 'omit' })
      .then((r) => (r.ok ? r.json() : null)).catch(() => null);
  }
  const putViews = (m) => { if (!m || typeof m !== 'object') return; S.views = S.views || {}; Object.keys(m).forEach((k) => { const v = Number(m[k]); if (okId(k) && Number.isFinite(v) && v >= 0) S.views[k] = Math.floor(v); }); };
  function loadStats(force) {
    if (!acctApi()) return Promise.resolve(null);
    if (S.statsP && !force && Date.now() - S.statsAt < 60e3) return S.statsP;
    S.statsAt = Date.now();
    S.statsP = apiPost('/v1/articles/stats', {}).then((j) => { if (j && j.views && typeof j.views === 'object') { putViews(j.views); paintViews(); } return S.views; });
    return S.statsP;
  }
  function recordView(id) {
    if (!okId(id) || !acctApi()) return Promise.resolve(null);
    let seen = 0; try { seen = Number(sessionStorage.getItem('tw.art.seen.' + id)) || 0; } catch (e) { seen = 0; }
    if (Date.now() - seen < VIEW_TTL) return loadStats();   // 30 分鐘內看過：不重送，只讀目前數字
    try { sessionStorage.setItem('tw.art.seen.' + id, String(Date.now())); } catch (e) { /* 私密視窗：照送 */ }
    return apiPost('/v1/articles/view', { id }).then((j) => {
      if (j && j.ok !== false && Number.isFinite(Number(j.views))) { putViews({ [id]: Number(j.views) }); paintViews(); }
      else { try { sessionStorage.removeItem('tw.art.seen.' + id); } catch (e) { /* 略 */ } }
      return S.views;
    });
  }
  /* 拿到數字之後只改畫面上的點閱格（不整頁重畫，免得清單捲動位置、輸入框焦點被打斷） */
  function paintViews() {
    $$('[data-vw]').forEach((el) => {
      const v = viewsOf(el.dataset.vw);
      if (v == null) { el.hidden = true; const t0 = el.querySelector('span'); if (t0) t0.textContent = ''; return; }
      el.hidden = false; const t = el.querySelector('span'); if (t) t.textContent = v.toLocaleString('zh-TW') + ' 次';
    });
    $$('#artAdmList td[data-vwc]').forEach((td) => { const v = viewsOf(td.dataset.vwc); td.textContent = v == null ? '—' : v.toLocaleString('zh-TW'); });
  }
  window.addEventListener('tw:account-config', () => {   // 帳號 API 網址比文章頁晚就緒（直接開文章網址）：就緒時補讀
    const h = (location.hash || '').replace(/^#/, '').split('/');
    if (h[0] === 'articles' || h[0] === 'admin') loadStats(true);
    else if (h[0] === 'article' && S.cur) recordView(S.cur);
  });
  const catOf = (id) => { const a = S.idx && S.idx.list.find((x) => x.id === id); return a ? a.cat : ''; };

  /* 2026-10-16 Andy：「精選文章已經裡面有分頁，側邊子分頁就拿掉」→ 側欄沒有子項可亮，這裡只負責把殘留的 art-* 清掉
     （舊版快取的 app.js 還會掛 data-l4sub="art-…"，留著會讓母項變成「讓位給子項」的半亮樣式） */
  function markSub() {
    const r = document.documentElement;
    if (/^art-/.test(r.getAttribute('data-l4sub') || '')) r.removeAttribute('data-l4sub');
  }

  /* ------------------------------------------------------------------ 共用小片段 */
  const catT = (k) => (CATS[k] ? CATS[k].t : ALL_T);
  const badge = (cat) => `<span class="artbadge k-${CATS[cat] ? cat : 'all'}">${icon(CATS[cat] ? cat : 'all', 13)}${esc(catT(cat))}</span>`;
  const tagsHTML = (tags) => (Array.isArray(tags) && tags.length ? `<div class="arttags">${tags.slice(0, 8).map((t) => `<span>${esc(t)}</span>`).join('')}</div>` : '');
  const EYE = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  /* 點閱數：只有拿到有效數字才寫（API 失敗、沒有這一篇 → 不畫，不顯示 0） */
  const viewsOf = (id) => { const v = S.views && S.views[id]; return Number.isFinite(v) && v >= 0 ? Math.floor(v) : null; };
  const vwHTML = (id) => { const v = viewsOf(id); return `<span class="artvw" data-vw="${esc(id)}" title="點閱次數"${v == null ? ' hidden' : ''}>${EYE}<span>${v == null ? '' : v.toLocaleString('zh-TW') + ' 次'}</span></span>`; };
  const cardHTML = (a) => `<a class="artc k-${esc(a.cat)}" href="#article/${encodeURIComponent(a.id)}" data-id="${esc(a.id)}" data-cat="${esc(a.cat)}" data-date="${esc(a.date)}" data-groups="${esc((a.groups || []).map((g) => g.id).join(' '))}" title="${esc(a.title)}">
    <span class="wm">${icon(a.cat, 96)}</span>
    <div class="r1">${badge(a.cat)}<span class="d">${esc(a.date)}</span><span class="rm" title="閱讀時間">約 ${esc(Number(a.reading_min) || 1)} 分鐘</span></div>
    <div class="tt">${esc(a.title)}</div>${a.subtitle ? `<div class="st">${esc(a.subtitle)}</div>` : ''}
    ${a.summary ? `<div class="sm">${esc(a.summary)}</div>` : ''}
    <div class="fr"><div class="ft">${(a.groups || []).slice(0, 4).map((g) => `<span class="artgp">${esc(g.name)}</span>`).join('')}${(a.groups || []).length ? '' : (Array.isArray(a.tags) ? a.tags.slice(0, 5).map((t) => `<span class="artgp">${esc(t)}</span>`).join('') : '')}</div>${vwHTML(a.id)}</div></a>`;
  const DISC = 'ⓘ 本站文章為公開資訊與產業知識的整理，不構成任何投資建議；內容以資料來源發布時點為準，投資前請自行查證並評估風險。';

  /* ------------------------------------------------------------------ 列表頁 */
  /* ★ 10-16 拿掉「最新一篇放大成 2×2 焦點卡」（Andy：「這邊的大小需要一致」）：所有卡片同一尺寸，見 .artlist／.artc 的 CSS */
  function ensureRange() { if (S.from == null || S.to == null) { const d = defRange(); S.from = d.from; S.to = d.to; } }
  function resetFilters() { const d = defRange(); S.q = ''; S.from = d.from; S.to = d.to; S.grp = new Set(); if (S.ms) S.ms.set({ selected: [] }); }
  function filtered(cat, ignoreCat) {
    const q = S.q.trim().toLowerCase();
    return (S.idx ? S.idx.list : []).filter((a) => (ignoreCat || cat === 'all' || a.cat === cat)
      && (!q || String(a.title).toLowerCase().includes(q))
      && (!S.from || a.date >= S.from) && (!S.to || a.date <= S.to)
      && (!S.grp.size || (a.groups || []).some((g) => S.grp.has(g.id))));
  }
  function groupStats() {
    const m = new Map();
    (S.idx ? S.idx.list : []).forEach((a) => (a.groups || []).forEach((g) => { const o = m.get(g.id) || { id: g.id, name: g.name, n: 0 }; o.n += 1; m.set(g.id, o); }));
    return [...m.values()].sort((a, b) => b.n - a.n || a.name.localeCompare(b.name, 'zh-Hant'));
  }
  function skeletonList(root) {
    root.innerHTML = `
<div class="card artcard" id="artCard">
  <div class="row spread"><h3>精選文章 <small id="artUpd"></small></h3></div>
  <div class="nbsw" id="artCats" role="tablist" aria-label="文章分類">
    ${['all'].concat(CAT_KEYS).map((k) => `<button type="button" role="tab" class="k-${k}" data-cat="${k}" data-s="${esc(CAT_S[k])}" title="${esc(catT(k))}">${icon(k, 15)}<span>${esc(catT(k))}</span><em></em></button>`).join('')}
  </div>
  <div class="nbbody">
    <div class="artflt">
      <input type="search" id="artQ" placeholder="搜尋標題關鍵字" aria-label="搜尋標題關鍵字" autocomplete="off">
      <div id="artGrp" hidden></div>
      <label>從 <input type="date" id="artFrom" aria-label="開始日期"></label>
      <label>到 <input type="date" id="artTo" aria-label="結束日期"></label>
      <button type="button" class="btn small" id="artClr" title="回到預設：近一個月、全部族群、不限關鍵字">清除篩選</button>
      <span class="cnt"><span class="rg" id="artRange"></span><span id="artCount" aria-live="polite"></span></span>
    </div>
    <div class="artmain">
      <div class="artlist" id="artList"></div>
      <div class="artside" id="artSide" role="complementary" aria-label="快速瀏覽"></div>
    </div>
  </div>
  <p class="artfoot">${esc(DISC)}</p>
</div>`;
    const q = $('#artQ', root), f = $('#artFrom', root), t = $('#artTo', root);
    q.addEventListener('input', () => { S.q = q.value; paintList(); });
    f.addEventListener('change', () => { S.from = okDate(f.value) ? f.value : ''; paintList(); });
    t.addEventListener('change', () => { S.to = okDate(t.value) ? t.value : ''; paintList(); });
    $('#artClr', root).onclick = () => { resetFilters(); paintList(); };
    $$('#artCats>button', root).forEach((b) => {
      b.onclick = () => { const h = b.dataset.cat === 'all' ? '#articles' : '#articles/' + b.dataset.cat; if (location.hash !== h) location.hash = h; };
    });
    S.ms = null;
  }
  function mountGroups(root) {
    const host = $('#artGrp', root); if (!host) return;
    const gs = groupStats();
    host.hidden = !gs.length;
    if (!gs.length || !window.TwMS) return;
    const items = gs.map((g) => ({ v: g.id, t: g.name, n: g.n }));
    if (!S.ms || S.ms.host !== host) {
      S.ms = window.TwMS.mount(host, { id: 'artGroups', label: '族群', items, selected: [...S.grp], placeholder: '搜尋族群…', width: '12em',
        onChange: (set) => { S.grp = set ? new Set(set) : new Set(); paintList(); } });
    } else S.ms.set({ items, selected: [...S.grp] });
  }
  function paintSide(root) {
    const side = $('#artSide', root); if (!side || !S.idx) return;
    const pool = filtered('all', true);
    const mx = Math.max(1, ...CAT_KEYS.map((k) => pool.filter((a) => a.cat === k).length));
    const gs = groupStats().slice(0, 14);
    const recent = S.idx.list.slice(0, 5);
    side.innerHTML = `
<section><h5>分類篇數（目前篩選）</h5>${CAT_KEYS.map((k) => { const n = pool.filter((a) => a.cat === k).length;
      return `<button type="button" class="cr k-${k}${S.cat === k ? ' on' : ''}" data-cat="${k}">${icon(k, 16)}<span>${esc(catT(k))}</span><b>${n}</b><span class="bar"><i style="width:${Math.round(100 * n / mx)}%"></i></span></button>`; }).join('')}</section>
${gs.length ? `<section><h5>熱門族群</h5><div class="gps">${gs.map((g) => `<button type="button" data-gid="${esc(g.id)}" class="${S.grp.has(g.id) ? 'on' : ''}" title="只看提到「${esc(g.name)}」的文章">${esc(g.name)}<em>${g.n}</em></button>`).join('')}</div></section>` : ''}
<section class="rc"><h5>最近更新</h5>${recent.map((a) => `<a class="k-${esc(a.cat)}" href="#article/${encodeURIComponent(a.id)}" title="${esc(a.title)}">${icon(a.cat, 14)}<span>${esc(a.title)}</span><small>${esc(a.date)}</small></a>`).join('')}</section>`;
    $$('.cr', side).forEach((b) => { b.onclick = () => { const h = '#articles/' + b.dataset.cat; if (location.hash !== h) location.hash = h; }; });
    $$('.gps button', side).forEach((b) => {
      b.onclick = () => { const id = b.dataset.gid; if (S.grp.has(id)) S.grp.delete(id); else S.grp.add(id); if (S.ms) S.ms.set({ selected: [...S.grp] }); paintList(); };
    });
  }
  function paintList() {
    const root = document.getElementById('v-articles'); if (!root || !$('#artList', root)) return;
    ensureRange();
    const q = $('#artQ', root), f = $('#artFrom', root), t = $('#artTo', root);
    if (q.value !== S.q) q.value = S.q;
    if (f.value !== S.from) f.value = S.from;
    if (t.value !== S.to) t.value = S.to;
    // 跟預設不同的篩選＝外框換色（style_guide 八：狀態用顏色不用文字）；預設日期區間不算「改過」
    const D = defRange();
    q.classList.toggle('chg', !!S.q.trim()); f.classList.toggle('chg', S.from !== D.from); t.classList.toggle('chg', S.to !== D.to);
    f.max = S.to || ''; t.min = S.from || '';
    const rg = $('#artRange', root);
    rg.textContent = (S.from || '不限') + ' ～ ' + (S.to || '不限');
    rg.dataset.from = S.from || ''; rg.dataset.to = S.to || '';
    $$('#artCats>button', root).forEach((b) => {
      const on = b.dataset.cat === S.cat;
      b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false');
      const em = $('em', b); if (em) em.textContent = S.idx ? String(filtered(b.dataset.cat).length) : '';
    });
    const box = $('#artList', root), cnt = $('#artCount', root);
    if (!S.idx) {
      box.innerHTML = S.idxErr ? '<div class="artempty">文章清單暫時讀不到，請稍後重新整理。</div>' : '<div class="artempty">載入中…</div>';
      cnt.textContent = ''; return;
    }
    mountGroups(root);
    $('#artUpd', root).textContent = S.idx.updated ? '更新 ' + S.idx.updated : '';
    const list = filtered(S.cat);
    cnt.innerHTML = `共 <b>${list.length}</b> 篇`;
    cnt.dataset.n = String(list.length);
    const dirty = !!(S.q.trim() || S.from !== D.from || S.to !== D.to || S.grp.size);
    box.innerHTML = list.length ? list.map((a) => cardHTML(a)).join('')
      : `<div class="artempty k-${S.cat === 'all' ? 'all' : S.cat}" id="artEmpty">${icon(S.cat, 40)}<div>${dirty ? '這個條件下沒有符合的文章，換個關鍵字、族群或放寬日期試試。' : '近一個月這個分類還沒有文章。'}</div>`
        + `${dirty ? '<button type="button" class="btn small" data-clr>清除篩選</button>' : '<button type="button" class="btn small" data-wide>看全部日期</button>'}</div>`;
    const c2 = $('[data-clr]', box); if (c2) c2.onclick = () => { resetFilters(); paintList(); };
    const c3 = $('[data-wide]', box); if (c3) c3.onclick = () => { S.from = ''; S.to = ''; paintList(); };
    paintSide(root);
  }
  async function showList(cat) {
    css();
    const root = document.getElementById('v-articles'); if (!root) return;
    S.cat = CATS[cat] ? cat : 'all';
    S.cur = ''; S.curData = null;
    ensureRange();
    markSub(S.cat);
    if (!$('#artList', root)) { disposeCharts(root); skeletonList(root); }
    paintList();
    loadStats();
    await loadIndex();
    if (location.hash.replace(/^#/, '').split('/')[0] !== 'articles') return;   // 讀清單的時候使用者已經換頁
    paintList();
  }

  /* ------------------------------------------------------------------ 單篇：內文區塊 */
  const NPAL = 7;   // 文章調色盤 --art-p1..7（css() 定義，深淺主題各一組）
  const TONES = ['chip', 'mem', 'interposer', 'substrate', 'board', 'bump'];
  const tone = (t) => (TONES.includes(t) ? t : 'other');
  const clampW = (w) => { const x = num(w); return x == null ? 1 : Math.max(0.12, Math.min(1, x)); };
  const figFoot = (b) => {
    const parts = [];
    if (b.note) parts.push(`<span>${esc(b.note)}</span>`);
    if (b.source) parts.push(`<span>資料來源：${esc(b.source)}</span>`);
    return parts.length ? `<p class="fn2">${parts.join('')}</p>` : '';
  };
  function kpiHTML(b) {
    const its = (Array.isArray(b.items) ? b.items : []).filter((x) => x && (x.label || x.value != null)).slice(0, 8);
    if (!its.length) return '';
    return `<div class="artkpi" style="--n:${Math.min(4, its.length)}">${its.map((x, i) => {
      const d = String(x.delta == null ? '' : x.delta).trim();
      const dc = /^\+/.test(d) ? 'up' : /^[-−]/.test(d) ? 'dn' : '';
      return `<div class="akc pc${(i % NPAL) + 1}"><div class="akl" title="${esc(x.label)}">${esc(x.label)}</div><div class="akv"><b>${esc(x.value)}</b>${x.unit ? `<small>${esc(x.unit)}</small>` : ''}</div>`
        + (d ? `<div class="akd ${dc}">${esc(d)}${x.note ? `<span>${esc(x.note)}</span>` : ''}</div>` : (x.note ? `<div class="akn" title="${esc(x.note)}">${esc(x.note)}</div>` : '')) + '</div>';
    }).join('')}</div>`;
  }
  function chartHTML(b, bi) {
    if (!Array.isArray(b.x) || !b.x.length || !Array.isArray(b.series) || !b.series.length) return '';
    const horiz = b.kind === 'hbar' || b.kind === 'range';
    const h = horiz ? Math.max(170, b.x.length * (b.kind === 'range' ? 46 : 30) + 70) : null;
    const marks = (Array.isArray(b.marks) ? b.marks : []).filter((m) => m && m.text && b.x.map(String).includes(String(m.x)));
    return `<figure class="artfig artchart" data-bi="${bi}" data-kind="${esc(b.kind || 'bar')}">${b.title ? `<figcaption class="fh">${esc(b.title)}</figcaption>` : ''}
      <div class="cv" id="artCh${bi}"${h ? ` style="height:${h}px"` : ''}></div>
      ${horiz && marks.length ? `<div class="mk">${marks.map((m) => `<span>${esc(m.x)}：${esc(m.text)}</span>`).join('')}</div>` : ''}${figFoot(b)}</figure>`;
  }
  function flowHTML(b, bi) {
    const cols = (Array.isArray(b.columns) ? b.columns : []).filter((c) => c && Array.isArray(c.nodes) && c.nodes.length).slice(0, 6);
    if (!cols.length) return '';
    const nm = (c) => { const L = window.App && window.App.L; return (L && L.cname && L.cname[c]) || ''; };
    return `<figure class="artfig artflow" data-bi="${bi}">${b.title ? `<figcaption class="fh">${esc(b.title)}</figcaption>` : ''}
      <div class="fl" style="--cols:${cols.length}"><svg class="fe" aria-hidden="true"></svg>${cols.map((c, ci) => `<div class="fcol" style="--fc:var(--art-p${(ci % NPAL) + 1})"><div class="fch" title="${esc(c.label)}">${esc(c.label || '')}</div><div class="fnodes">${c.nodes.filter((n) => n && n.label).map((n) => {
        const codes = (Array.isArray(n.codes) ? n.codes : []).filter(okCode).slice(0, 6);
        return `<div class="fnd" data-nid="${esc(n.id || '')}"><b>${esc(n.label)}</b>${n.sub ? `<span>${esc(n.sub)}</span>` : ''}${codes.length ? `<div class="fcodes">${codes.map((c) => `<a href="#stock/${esc(c)}" title="到個股頁"><b>${esc(c)}</b>${nm(c) ? esc(nm(c)) : ''}</a>`).join('')}</div>` : ''}</div>`;
      }).join('')}</div></div>`).join('')}</div>${figFoot(b)}</figure>`;
  }
  function stackHTML(b, bi) {
    const ls = (Array.isArray(b.layers) ? b.layers : []).filter((l) => l && l.label).slice(0, 14);
    if (!ls.length) return '';
    return `<figure class="artfig artstack" data-bi="${bi}">${b.title ? `<figcaption class="fh">${esc(b.title)}</figcaption>` : ''}<div class="sk">${ls.map((l) => {
      const w = clampW(l.w);
      const sp = (Array.isArray(l.split) ? l.split : []).filter((x) => x && x.label);
      const tot = sp.reduce((s, x) => s + clampW(x.w), 0) || 1;
      const segs = sp.length ? sp.map((x) => `<span class="sks t-${tone(x.tone || l.tone)}" style="flex:${(clampW(x.w) / tot).toFixed(4)} 1 0" title="${esc(x.label)}">${esc(x.label)}</span>`).join('')
        : `<span class="sks t-${tone(l.tone)}" style="flex:1 1 0" title="${esc(l.label)}">${esc(l.label)}</span>`;
      return `<div class="skr t-${tone(l.tone)}" style="--w:${(w * 100).toFixed(1)}%"><div class="skw"><div class="skb">${segs}</div><i></i></div><div class="skl"><b>${esc(l.label)}</b>${l.sub ? `<span>${esc(l.sub)}</span>` : ''}</div></div>`;
    }).join('')}</div>${figFoot(b)}</figure>`;
  }
  /* steps 說明圖的圖示（簡潔線條風、currentColor 上色；Lucide 同一套 24×24、線寬 2） */
  const STEP_IC = {
    chip: '<rect x="6" y="6" width="12" height="12" rx="1.5"/><rect x="9.5" y="9.5" width="5" height="5" rx=".5"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    wafer: '<circle cx="12" cy="12" r="9"/><path d="M7.5 8.5h9M6.5 12h11M7.5 15.5h9M9.5 6v12M14.5 6v12"/><path d="M10.5 20.9h3"/>',
    package: '<rect x="3" y="10" width="18" height="8" rx="1.5"/><rect x="8" y="6" width="8" height="4" rx="1"/><path d="M6 18v3M10 18v3M14 18v3M18 18v3"/>',
    substrate: '<path d="M3 16l9 4 9-4"/><path d="M3 12l9 4 9-4"/><path d="M3 8l9 4 9-4-9-4-9 4z"/>',
    board: '<rect x="3" y="4" width="18" height="16" rx="2"/><rect x="7" y="8" width="5" height="5" rx=".5"/><path d="M15 9h2M15 12h2M7 16.5h10"/>',
    server: '<rect x="3" y="4" width="18" height="7" rx="1.5"/><rect x="3" y="13" width="18" height="7" rx="1.5"/><path d="M7 7.5h.01M7 16.5h.01M11 7.5h6M11 16.5h6"/>',
    cool: '<circle cx="12" cy="12" r="2"/><path d="M12 10c-.5-3.5.5-7 3.5-7 2.5 0 2.5 4-1.5 7.2"/><path d="M14 12c3.5-.5 7 .5 7 3.5 0 2.5-4 2.5-7.2-1.5"/><path d="M12 14c.5 3.5-.5 7-3.5 7-2.5 0-2.5-4 1.5-7.2"/><path d="M10 12c-3.5.5-7-.5-7-3.5 0-2.5 4-2.5 7.2 1.5"/>',
    power: '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/>',
    net: '<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="19" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M12 7.5V12M12 12l-5.3 5.3M12 12l5.3 5.3"/>',
    money: '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 9.5v.01M18 14.5v.01"/>',
    chart: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 5-6"/>',
    factory: '<path d="M3 21V10l6 4v-4l6 4V5l6 3v13z"/><path d="M7 18h2M12 18h2M17 18h2"/>',
    truck: '<path d="M2 6h11v10H2z"/><path d="M13 10h4l4 4v2h-8z"/><circle cx="6" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    memory: '<rect x="2" y="7" width="20" height="10" rx="1.5"/><path d="M6 10v4M10 10v4M14 10v4M18 10v4M5 17v3M9 17v3M15 17v3M19 17v3"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  };
  const stepIc = (k) => (STEP_IC[k] ? `<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${STEP_IC[k]}</svg>` : '');
  /* steps 編號流程圖：{t:'steps', title, note, items:[{label, text, icon}]}（2～8 步）。
     這張圖回答「這件事是怎麼一步一步走到下一環的」：由左到右照順序讀，每步顏色不同、圓圈右上是第幾步。 */
  /* ⚠ 圖示名記在 data-sic 不是 data-icon：icons.js 會替全站任何 [data-icon] 元素自動補一顆標題小圖示（實測每一步上面多一顆長條圖）。 */
  function stepsHTML(b, bi) {
    const its = (Array.isArray(b.items) ? b.items : []).filter((x) => x && x.label).slice(0, 8);
    if (!its.length) return '';
    return `<figure class="artfig artsteps" data-bi="${bi}">${b.title ? `<figcaption class="fh">${esc(b.title)}</figcaption>` : ''}
      <ol class="stp" style="--n:${its.length}">${its.map((x, i) => `<li class="sti pc${(i % NPAL) + 1}" data-sic="${esc(STEP_IC[x.icon] ? x.icon : '')}"><div class="stc">${stepIc(x.icon) || `<b style="font-family:var(--mono);font-size:20px">${i + 1}</b>`}<em>${i + 1}</em></div>`
        + `<b>${esc(x.label)}</b>${x.text ? `<span>${esc(x.text)}</span>` : ''}${i < its.length - 1 ? '<i class="sta" aria-hidden="true"></i>' : ''}</li>`).join('')}</ol>${figFoot(b)}</figure>`;
  }
  /* compare 對照卡：{t:'compare', title, note, cols:[{label, tone:'neutral|accent|warn|good', points:[…], verdict}]}（2～4 欄）。
     這張圖回答「這幾個選項差在哪、各自的結論是什麼」：同一列由左到右比，每欄最底下那句是結論。 */
  const CMP_TONES = ['neutral', 'accent', 'warn', 'good'];
  function compareHTML(b, bi) {
    const cols = (Array.isArray(b.cols) ? b.cols : []).filter((c) => c && c.label).slice(0, 4);
    if (!cols.length) return '';
    return `<figure class="artfig artcmp" data-bi="${bi}">${b.title ? `<figcaption class="fh">${esc(b.title)}</figcaption>` : ''}
      <div class="cmg" style="--n:${cols.length}">${cols.map((c) => { const tn = CMP_TONES.includes(c.tone) ? c.tone : 'neutral';
        const pts = (Array.isArray(c.points) ? c.points : []).filter((x) => x != null && String(x).trim()).slice(0, 10);
        return `<section class="cmc tn-${tn}" data-tone="${tn}"><h5>${esc(c.label)}</h5>${pts.length ? `<ul>${pts.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}${c.verdict ? `<p class="vd">${esc(c.verdict)}</p>` : ''}</section>`; }).join('')}</div>${figFoot(b)}</figure>`;
  }
  function blockHTML(b, bi) {
    if (!b || typeof b !== 'object') return '';
    switch (b.t) {
      case 'h': return `<h4 data-bi="${bi}">${esc(b.text)}</h4>`;
      case 'p': return `<p>${esc(b.text)}</p>`;
      case 'ul': return Array.isArray(b.items) ? `<ul>${b.items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : '';
      case 'callout': return `<div class="callout" role="note">${esc(b.text)}</div>`;
      case 'table': {
        const head = Array.isArray(b.head) ? b.head : [], rows = Array.isArray(b.rows) ? b.rows : [];
        return `<div class="tbw"><table>${head.length ? `<thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead>` : ''}<tbody>${rows.map((r) => `<tr>${(Array.isArray(r) ? r : [r]).map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
      }
      case 'stocks': {
        const its = (Array.isArray(b.items) ? b.items : []).filter((x) => x && okCode(x.code));
        if (!its.length) return '';
        return `<div class="artstk"><div class="lbl">相關台股</div><div class="g">${its.map((x) => `<a href="#stock/${esc(x.code)}" data-code="${esc(x.code)}" title="${esc((x.name || '') + ' ' + x.code)}：到個股頁看 K 線與基本面">
          <div class="h"><b>${esc(x.code)}</b><span>${esc(x.name || '')}</span></div>${x.why ? `<div class="w">${esc(x.why)}</div>` : ''}</a>`).join('')}</div></div>`;
      }
      case 'kpi': return kpiHTML(b);
      case 'chart': return chartHTML(b, bi);
      case 'flow': return flowHTML(b, bi);
      case 'stack': return stackHTML(b, bi);
      case 'steps': return stepsHTML(b, bi);
      case 'compare': return compareHTML(b, bi);
      default: return '';
    }
  }

  /* ------------------------------------------------------------------ 單篇：圖表（ECharts，走 App.chart 包裝層：提示框掛 body、長條漸層、尺寸自動跟） */
  function cssv(n, fb) { try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || fb; } catch (e) { return fb; } }
  function chartOption(b) {
    const C = { c1: cssv('--cat-1', '#3ee0ff'), c2: cssv('--cat-3', '#ffb454'), c3: cssv('--cat-2', '#8b7bff'), hl: cssv('--art-hl', '#f5c842'),
      ink: cssv('--ink', '#e8eeff'), ink2: cssv('--ink-2', '#a9b6d6'), ink3: cssv('--ink-3', '#6f7ea3'), line: cssv('--line', '#1e2a48'), grid: cssv('--grid', 'rgba(255,255,255,.06)'), panel: cssv('--panel', '#0f172b') };
    const A = window.App || {};
    const NF = A.NUM_FONT || 'monospace';
    /* 調色盤（--art-p1..7）：不同系列不同色、橫條每列不同色、區間條每列不同色；長條一律自己給「同色漸層物件」——
       App.chart 的長條共用風格只會把「字串色」換成全站青藍，漸層物件原樣保留，所以文章的配色不會被統一蓋掉。 */
    const P = [1, 2, 3, 4, 5, 6, 7].map((k) => cssv('--art-p' + k, ['#5b9cff', '#2ec4b6', '#a88bff', '#ff8a65', '#ec74b5', '#d39b5b', '#4cc3ef'][k - 1]));
    const rgbaOf = (c, a) => { const m = /^#([0-9a-f]{6})$/i.exec(String(c).trim()); if (!m) return c; const h = m[1]; return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4), 16)},${a})`; };
    const grad = (c, horiz) => (horiz ? { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: rgbaOf(c, 0.5) }, { offset: 1, color: rgbaOf(c, 1) }] }
      : { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: rgbaOf(c, 1) }, { offset: 1, color: rgbaOf(c, 0.42) }] });
    const hlStyle = (horiz) => ({ color: grad(C.hl, horiz), borderColor: C.ink, borderWidth: 1.5, borderRadius: 3 });
    const kind = ['bar', 'line', 'barline', 'hbar', 'range'].includes(b.kind) ? b.kind : 'bar';
    const x = b.x.map(String), n = x.length;
    const unit = b.unit ? String(b.unit) : '', u2 = b.y2unit ? String(b.y2unit) : '';
    const hl = new Set((Array.isArray(b.highlight) ? b.highlight : []).map(Number).filter((i) => i >= 0 && i < n));
    const marks = new Map(); (Array.isArray(b.marks) ? b.marks : []).forEach((m) => { if (m && m.text) { const i = x.indexOf(String(m.x)); if (i >= 0) marks.set(i, String(m.text)); } });
    const tipBase = Object.assign({}, A.tip || {}, { trigger: 'axis', triggerOn: 'mousemove|click' });
    const axLab = { color: C.ink3, fontSize: 12, fontFamily: NF };
    const legend = (names) => (names.length > 1 ? { top: 0, left: 0, itemWidth: 14, itemHeight: 8, textStyle: { color: C.ink2, fontSize: 12 }, data: names } : undefined);
    const ser0 = b.series.filter((s) => s && Array.isArray(s.data)).slice(0, 4);
    const sName = (s, i) => String(s.name || ('系列' + (i + 1)));

    if (kind === 'range') {
      const out = [], names = [];
      let lo = Infinity, hi = -Infinity;
      ser0.forEach((s, si) => {
        const pr = x.map((_, i) => { const d = s.data[i]; const a = Array.isArray(d) ? num(d[0]) : null, z = Array.isArray(d) ? num(d[1]) : null; return a == null || z == null ? null : [Math.min(a, z), Math.max(a, z)]; });
        pr.forEach((p) => { if (p) { lo = Math.min(lo, p[0]); hi = Math.max(hi, p[1]); } });
        const multi = ser0.length > 1;
        const col = P[si % P.length];
        names.push(sName(s, si));
        out.push({ name: sName(s, si) + '__base', type: 'bar', stack: 'r' + si, silent: true, itemStyle: { color: 'transparent' }, barMaxWidth: 22, data: pr.map((p) => (p ? p[0] : null)),
          label: { show: true, position: 'insideRight', color: C.ink2, fontSize: 12, fontFamily: NF, formatter: (q) => fmtN(q.value) }, tooltip: { show: false } });
        out.push({ name: sName(s, si), type: 'bar', stack: 'r' + si, barMaxWidth: 22, data: pr.map((p, i) => (p ? { value: p[1] - p[0], _r: p, itemStyle: hl.has(i) ? hlStyle(true) : { color: grad(multi ? col : P[i % P.length], true), borderRadius: 3 } } : null)),
          itemStyle: { color: grad(col, true), borderRadius: 3 },
          label: { show: true, position: 'right', color: C.ink, fontSize: 12, fontWeight: 700, fontFamily: NF, formatter: (q) => (q.data && q.data._r ? fmtN(q.data._r[1]) + unit : '') } });
      });
      if (!isFinite(lo)) return null;
      const pad = Math.max((hi - lo) * 0.3, Math.abs(hi) * 0.05, 1);
      let mn = Math.floor(lo - pad); if (lo >= 0 && mn < 0) mn = 0;
      return {
        grid: { left: 8, right: 64, top: names.length > 1 ? 30 : 8, bottom: 4, containLabel: true },
        legend: legend(names),
        tooltip: Object.assign({}, tipBase, { axisPointer: { type: 'shadow' }, formatter: (ps) => {
          const arr = (Array.isArray(ps) ? ps : [ps]).filter((p) => p.data && p.data._r);
          if (!arr.length) return '';
          const i = arr[0].dataIndex;
          return `<b>${esc(x[i])}</b>` + arr.map((p) => `<br>${p.marker}${esc(p.seriesName)}：${fmtN(p.data._r[0])} ～ ${fmtN(p.data._r[1])}${esc(unit)}`).join('') + (marks.has(i) ? `<br>◆ ${esc(marks.get(i))}` : '');
        } }),
        xAxis: { type: 'value', min: mn, name: unit, nameLocation: 'end', nameTextStyle: { color: C.ink3, fontSize: 12 }, axisLabel: axLab, splitLine: { lineStyle: { color: C.grid } } },
        yAxis: { type: 'category', inverse: true, data: x, axisLabel: { color: C.ink2, fontSize: 12, width: 120, overflow: 'truncate' }, axisTick: { show: false }, axisLine: { lineStyle: { color: C.line } } },
        series: out, timeGrid: false, m4dz: false,
      };
    }

    if (kind === 'hbar') {
      const s = ser0[0]; if (!s) return null;
      const vals = x.map((_, i) => num(s.data[i]));
      const pos = vals.filter((v) => v != null && v > 0);
      const logAx = pos.length === vals.length && pos.length > 1 && Math.max(...pos) / Math.min(...pos) > 200;   // 差距太大（6 萬倍 vs 100 倍）改對數軸，小的那條才看得到
      return {
        grid: { left: 8, right: 64, top: 8, bottom: logAx ? 24 : 4, containLabel: true },
        tooltip: Object.assign({}, tipBase, { axisPointer: { type: 'shadow' }, formatter: (ps) => { const p = (Array.isArray(ps) ? ps : [ps])[0]; if (!p) return ''; const i = p.dataIndex;
          return `<b>${esc(x[i])}</b><br>${p.marker}${esc(p.seriesName)}：${fmtN(vals[i])}${esc(unit)}` + (marks.has(i) ? `<br>◆ ${esc(marks.get(i))}` : ''); } }),
        xAxis: logAx ? { type: 'log', logBase: 10, name: (unit ? unit + '・' : '') + '對數刻度', nameLocation: 'middle', nameGap: 26, nameTextStyle: { color: C.ink3, fontSize: 12 }, axisLabel: axLab, splitLine: { lineStyle: { color: C.grid } } }
          : { type: 'value', name: unit, nameTextStyle: { color: C.ink3, fontSize: 12 }, axisLabel: axLab, splitLine: { lineStyle: { color: C.grid } } },
        yAxis: { type: 'category', inverse: true, data: x, axisLabel: { color: C.ink2, fontSize: 12, width: 130, overflow: 'truncate' }, axisTick: { show: false }, axisLine: { lineStyle: { color: C.line } } },
        series: [{ name: sName(s, 0), type: 'bar', barMaxWidth: 18,
          data: vals.map((v, i) => ({ value: v, itemStyle: hl.has(i) || marks.has(i) ? hlStyle(true) : { color: grad(P[i % P.length], true), borderRadius: 3 } })),
          itemStyle: { color: grad(P[0], true) },
          label: { show: true, position: 'right', color: C.ink, fontSize: 12, fontFamily: NF, formatter: (q) => fmtN(q.value) + (marks.has(q.dataIndex) ? ' ◆' : '') } }],
        timeGrid: false, m4dz: false,
      };
    }

    // bar／line／barline：直的
    const isM = document.documentElement.classList.contains('m4') || window.innerWidth <= 640;
    const hasY2 = ser0.some((s) => Number(s.axis) === 1);
    const names = ser0.map(sName);
    const showLab = (i) => !marks.has(i) && (n <= (isM ? 6 : 10) || i === n - 1 || hl.has(i));
    let barK = 0;
    const series = ser0.map((s, si) => {
      const typ = s.type === 'line' || s.type === 'bar' ? s.type : (kind === 'line' ? 'line' : kind === 'barline' && si > 0 ? 'line' : 'bar');
      const ax = hasY2 && Number(s.axis) === 1 ? 1 : 0;
      // 柱子從 p1 起輪、折線從 p4（珊瑚）起輪：同一張圖的柱與線一定是兩個色系，一眼分得出
      const col = typ === 'bar' ? P[(barK++ * 2) % P.length] : P[(3 + si) % P.length];
      const vals = x.map((_, i) => num(s.data[i]));
      const lab = { show: false, position: 'top', color: C.ink2, fontSize: 12, fontFamily: NF, formatter: (q) => fmtN(q.value) };
      const o = { name: sName(s, si), type: typ, yAxisIndex: ax, itemStyle: { color: typ === 'bar' ? grad(col, false) : col }, label: lab,
        data: vals.map((v, i) => { const d = { value: v }; if (typ === 'bar' && hl.has(i)) d.itemStyle = hlStyle(false); if (si === 0 || typ === 'bar' || ser0.length === 1) { if (showLab(i)) d.label = { show: true }; } return d; }) };
      if (typ === 'line') Object.assign(o, { symbol: 'circle', symbolSize: 7, showAllSymbol: true, lineStyle: { width: 2, color: col }, z: 3 });
      else Object.assign(o, { barMaxWidth: 40 });
      return o;
    });
    // 標註點：放在第一個系列的那根上，文字在點上方；右半邊的靠右對齊（不衝出圖外）
    if (marks.size && series[0]) {
      const s0 = series[0];
      s0.markPoint = { symbol: 'circle', symbolSize: 9, itemStyle: { color: C.hl, borderColor: C.panel, borderWidth: 2 },
        data: [...marks.entries()].sort((p, q) => p[0] - q[0]).map(([i, t], k) => { const v = s0.data[i].value; const right = i > (n - 1) / 2 && n > 1;
          // 好幾個標註時一高一低錯開（不然相鄰兩根的標籤會疊在一起）
          return { coord: [x[i], v], value: v, name: t, label: { show: true, position: 'top', distance: 6 + (k % 2) * 26, align: n === 1 ? 'center' : right ? 'right' : 'left', offset: [right ? 6 : -6, 0],
            formatter: () => `${t}　${fmtN(v)}${unit}`, color: C.ink, fontSize: 12, backgroundColor: C.panel, borderColor: C.hl, borderWidth: 1, borderRadius: 4, padding: [3, 6] } }; }) };
    }
    const unitOf = (si) => (series[si] && series[si].yAxisIndex === 1 ? u2 : unit);
    const y = (ax) => ({ type: 'value', name: ax ? u2 : unit, nameTextStyle: { color: C.ink3, fontSize: 12, align: ax ? 'right' : 'left' }, axisLabel: Object.assign({}, axLab, ax ? { formatter: (v) => fmtN(v) } : { formatter: (v) => (Math.abs(v) >= 10000 ? Math.round(v).toLocaleString('zh-TW') : fmtN(v)) }),
      splitLine: ax ? { show: false } : { lineStyle: { color: C.grid } }, scale: false });
    return {
      grid: { left: 8, right: hasY2 ? 8 : 14, top: (names.length > 1 ? 34 : 14) + (marks.size > 1 ? 56 : marks.size ? 30 : 12), bottom: 4, containLabel: true },
      legend: legend(names),
      tooltip: Object.assign({}, tipBase, { axisPointer: { type: series.some((s) => s.type === 'bar') ? 'shadow' : 'line' }, formatter: (ps) => {
        const arr = Array.isArray(ps) ? ps : [ps]; if (!arr.length) return '';
        const i = arr[0].dataIndex;
        return `<b>${esc(x[i])}</b>` + arr.map((p) => `<br>${p.marker}${esc(p.seriesName)}：${fmtN(p.value)}${esc(unitOf(p.seriesIndex))}`).join('') + (marks.has(i) ? `<br>◆ ${esc(marks.get(i))}` : '');
      } }),
      xAxis: { type: 'category', data: x, axisLabel: { color: C.ink3, fontSize: 12, hideOverlap: true }, axisTick: { alignWithLabel: true }, axisLine: { lineStyle: { color: C.line } } },
      yAxis: hasY2 ? [y(0), y(1)] : [y(0)],
      series, m4dz: false,
    };
  }
  function disposeCharts(root) {
    if (typeof echarts === 'undefined') return;
    $$('.artchart .cv', root).forEach((el) => { const c = echarts.getInstanceByDom(el); if (c) c.dispose(); if (el._ro) { el._ro.disconnect(); el._ro = null; } });
    $$('.artflow .fl', root).forEach((el) => { if (el._ro) { el._ro.disconnect(); el._ro = null; } });
  }

  /* ------------------------------------------------------------------ 單篇：關係圖的線（量完節點位置才畫；容器尺寸一變就重畫） */
  function drawFlow(fig, b) {
    const box = $('.fl', fig), svg = $('svg.fe', fig); if (!box || !svg) return;
    const R = box.getBoundingClientRect(); if (!R.width) return;
    const nodes = new Map(); $$('.fnd', box).forEach((n) => { if (n.dataset.nid) nodes.set(n.dataset.nid, n); });
    const cols = $$('.fcol', box);
    const vert = cols.length > 1 && cols[1].getBoundingClientRect().top > cols[0].getBoundingClientRect().bottom - 2;   // 欄被排成上下（手機）
    const rel = (el) => { const r = el.getBoundingClientRect(); return { l: r.left - R.left, r: r.right - R.left, t: r.top - R.top, b: r.bottom - R.top, cx: (r.left + r.right) / 2 - R.left, cy: (r.top + r.bottom) / 2 - R.top }; };
    const out = [];
    (Array.isArray(b.edges) ? b.edges : []).forEach((e) => {
      if (!Array.isArray(e) || e.length < 2) return;
      const A = nodes.get(String(e[0])), B = nodes.get(String(e[1])); if (!A || !B || A === B) return;
      const a = rel(A), z = rel(B);
      let p, tip, dir;
      if (!vert && z.l > a.r + 8) { const dx = (z.l - a.r) / 2; p = `M${a.r},${a.cy} C${a.r + dx},${a.cy} ${z.l - 2 - dx},${z.cy} ${z.l - 2},${z.cy}`; tip = [z.l - 1, z.cy]; dir = [1, 0]; }
      else if (!vert && a.l > z.r + 8) { const dx = (a.l - z.r) / 2; p = `M${a.l},${a.cy} C${a.l - dx},${a.cy} ${z.r + 2 + dx},${z.cy} ${z.r + 2},${z.cy}`; tip = [z.r + 1, z.cy]; dir = [-1, 0]; }
      else if (z.t > a.b) { const dy = (z.t - a.b) / 2; p = `M${a.cx},${a.b} C${a.cx},${a.b + dy} ${z.cx},${z.t - 2 - dy} ${z.cx},${z.t - 2}`; tip = [z.cx, z.t - 1]; dir = [0, 1]; }
      else if (a.t > z.b) { const dy = (a.t - z.b) / 2; p = `M${a.cx},${a.t} C${a.cx},${a.t - dy} ${z.cx},${z.b + 2 + dy} ${z.cx},${z.b + 2}`; tip = [z.cx, z.b + 1]; dir = [0, -1]; }
      else if (z.l > a.r + 4) { const dx = (z.l - a.r) / 2; p = `M${a.r},${a.cy} C${a.r + dx},${a.cy} ${z.l - 2 - dx},${z.cy} ${z.l - 2},${z.cy}`; tip = [z.l - 1, z.cy]; dir = [1, 0]; }   // 手機同一列左右兩張
      else if (a.l > z.r + 4) { const dx = (a.l - z.r) / 2; p = `M${a.l},${a.cy} C${a.l - dx},${a.cy} ${z.r + 2 + dx},${z.cy} ${z.r + 2},${z.cy}`; tip = [z.r + 1, z.cy]; dir = [-1, 0]; }
      else return;
      const [tx, ty] = tip, [ux, uy] = dir, L = 7, W = 4;
      const poly = `${tx},${ty} ${tx - ux * L + uy * W},${ty - uy * L - ux * W} ${tx - ux * L - uy * W},${ty - uy * L + ux * W}`;
      out.push(`<g data-a="${esc(e[0])}" data-b="${esc(e[1])}"><path d="${p}"/><polygon points="${poly}"/></g>`);
    });
    svg.setAttribute('viewBox', `0 0 ${Math.round(R.width)} ${Math.round(R.height)}`);
    svg.innerHTML = out.join('');
    fig.dataset.edges = String(out.length);
  }
  function wireFlow(fig, b) {
    const box = $('.fl', fig); if (!box) return;
    drawFlow(fig, b);
    if (typeof ResizeObserver !== 'undefined') { let raf = 0; box._ro = new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => drawFlow(fig, b)); }); box._ro.observe(box); }
    // 滑過節點：跟它相連的線亮起來、其他變淡（看得出「這一環接到誰」）
    box.addEventListener('pointerover', (ev) => {
      const n = ev.target.closest('.fnd'); if (!n) return;
      box.classList.add('hov'); const id = n.dataset.nid;
      $$('svg.fe g', box).forEach((g) => g.classList.toggle('on', g.dataset.a === id || g.dataset.b === id));
    });
    box.addEventListener('pointerleave', () => { box.classList.remove('hov'); $$('svg.fe g.on', box).forEach((g) => g.classList.remove('on')); });
  }
  function hydrate(root, d) {
    const blocks = Array.isArray(d.blocks) ? d.blocks : [];
    $$('.artchart', root).forEach((fig) => {
      const b = blocks[+fig.dataset.bi]; const el = $('.cv', fig); if (!b || !el) return;
      const opt = chartOption(b);
      if (!opt || !window.App || !window.App.chart) { fig.remove(); return; }
      window.App.chart(el, opt);
    });
    $$('.artflow', root).forEach((fig) => { const b = blocks[+fig.dataset.bi]; if (b) wireFlow(fig, b); });
    $$('.arttoc .tl button', root).forEach((bt) => { bt.onclick = () => { const h = root.querySelector(`#artBody h4[data-bi="${bt.dataset.bi}"]`); if (h) h.scrollIntoView({ behavior: 'smooth', block: 'start' }); }; });
    $$('.artgps button[data-gid]', root).forEach((bt) => { bt.onclick = () => { S.grp = new Set([bt.dataset.gid]); location.hash = '#articles'; }; });
    const back = $('#artBack', root);
    if (back) back.onclick = () => { if (S.backOk && history.length > 1) history.back(); else location.hash = back.dataset.to; };
  }

  function postHTML(d, meta) {
    const cat = CATS[d.cat] ? d.cat : (meta && meta.cat) || '';
    const kk = CATS[cat] ? cat : 'all';
    const links = (Array.isArray(d.site_links) ? d.site_links : []).filter((l) => l && okHash(l.hash) && l.label);
    const srcs = (Array.isArray(d.sources) ? d.sources : []).filter((s) => s && (s.title || s.url));
    const more = S.idx ? S.idx.list.filter((a) => a.cat === cat && a.id !== d.id).slice(0, 3) : [];
    const groups = cleanGroups(d.groups && d.groups.length ? d.groups : meta && meta.groups);
    const upd = okDate(d.updated) && d.updated !== d.date ? `<span>更新 <span class="mono">${esc(d.updated)}</span></span>` : '';
    const blocks = Array.isArray(d.blocks) ? d.blocks : [];
    const toc = blocks.map((b, i) => (b && b.t === 'h' && b.text ? `<button type="button" data-bi="${i}" title="${esc(b.text)}">${esc(b.text)}</button>` : '')).join('');
    const codes = [];
    blocks.forEach((b) => { if (b && b.t === 'stocks' && Array.isArray(b.items)) b.items.forEach((x) => { if (x && okCode(x.code) && !codes.some((c) => c.code === x.code)) codes.push({ code: x.code, name: x.name || '' }); }); });
    const listHash = CATS[cat] ? '#articles/' + cat : '#articles';
    return `
<div class="artpage k-${kk}">
<article class="card artpost" id="artPost" data-id="${esc(d.id)}">
  <button type="button" class="artback" id="artBack" data-to="${listHash}" title="回上一頁">← 返回</button>
  <nav class="artcrumb" aria-label="麵包屑"><a href="#articles">精選文章</a><span aria-hidden="true">›</span>${CATS[cat] ? `<a class="kc" href="#articles/${cat}">${icon(cat, 14)}${esc(catT(cat))}</a><span aria-hidden="true">›</span>` : ''}<span class="cur">${esc(d.title)}</span></nav>
  <div class="artmeta">${cat ? badge(cat) : ''}<span class="mono">${esc(d.date || '')}</span>${upd}<span>閱讀約 ${esc(Number(d.reading_min) || 1)} 分鐘</span>${vwHTML(d.id)}${d.confidence ? `<span title="資料信心：依來源數量與一致性自評">資料信心 ${esc(d.confidence)}</span>` : ''}</div>
  <h2 class="artttl">${esc(d.title)}</h2>
  ${d.subtitle ? `<p class="artsub">${esc(d.subtitle)}</p>` : ''}
  ${groups.length ? `<div class="artgps"><span class="lb">相關族群</span>${groups.map((g) => `<button type="button" class="artgp" data-gid="${esc(g.id)}" title="看其他提到「${esc(g.name)}」的文章">${esc(g.name)}</button>`).join('')}</div>` : ''}
  ${tagsHTML(d.tags)}
  ${d.summary ? `<div class="artlead">${esc(d.summary)}</div>` : ''}
  <div class="artbody" id="artBody">${blocks.map(blockHTML).join('')}</div>
  ${links.length ? `<section class="artsec" id="artLinks"><h4>站內相關頁面</h4><div class="artlinks">${links.map((l) => `<a href="${esc(l.hash)}">${esc(l.label)}</a>`).join('')}</div></section>` : ''}
  ${srcs.length ? `<section class="artsec" id="artSrc"><h4>資料來源</h4><ol class="artsrc">${srcs.map((s) => {
    const t = esc(s.title || s.url), info = [s.publisher, s.date].filter(Boolean).map(esc).join('，');
    return `<li>${okUrl(s.url) ? `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${t}</a>` : t}${info ? `（${info}）` : ''}</li>`; }).join('')}</ol></section>` : ''}
  ${more.length ? `<section class="artsec" id="artMore"><h4>同類別其他文章</h4><div class="artmore">${more.map((a) => cardHTML(a)).join('')}</div></section>` : ''}
  <p class="artdisc">${esc(DISC)}</p>
  <div class="artend"><a href="${listHash}" id="artEnd">${icon(kk, 15)}回到${esc(catT(cat))}清單</a></div>
</article>
<div class="arttoc" role="complementary" aria-label="本文目錄">
  ${toc ? `<section><h5>本文目錄</h5><div class="tl">${toc}</div></section>` : ''}
  ${codes.length ? `<section><h5>文中提到的股票</h5><div class="sc">${codes.map((c) => `<a href="#stock/${esc(c.code)}"><b>${esc(c.code)}</b>${esc(c.name)}</a>`).join('')}</div></section>` : ''}
</div>
</div>`;
  }
  async function showPost(id) {
    css();
    const root = document.getElementById('v-articles'); if (!root) return;
    const changed = S.cur !== id; S.cur = id;
    markSub(catOf(id));
    if (changed) { disposeCharts(root); root.innerHTML = '<div class="card artpost"><div class="arterr">載入中…</div></div>'; window.scrollTo({ top: 0 }); }
    const [idx, d] = await Promise.all([loadIndex(), loadPost(id)]);
    if (S.cur !== id || location.hash.replace(/^#/, '').split('/')[0] !== 'article') return;
    const meta = idx ? idx.list.find((a) => a.id === id) : null;
    if (!d || !d.title) {
      root.innerHTML = `<div class="card artpost" id="artPost"><button type="button" class="artback" id="artBack" data-to="#articles">← 返回</button><nav class="artcrumb"><a href="#articles">精選文章</a><span aria-hidden="true">›</span><span class="cur">找不到文章</span></nav>
        <div class="arterr" id="artErr">這篇文章暫時讀不到（可能還在整理或已下架）。<br><a href="#articles">回精選文章清單</a></div></div>`;
      hydrate(root, {});
      return;
    }
    markSub(CATS[d.cat] ? d.cat : meta && meta.cat);
    disposeCharts(root);
    root.innerHTML = postHTML(d, meta);
    S.curData = d;
    hydrate(root, d);
    recordView(d.id);
    document.title = d.title + '｜精選文章';
  }

  /* ------------------------------------------------------------------ 進入點（app.js route() 呼叫） */
  function show(head, rest) {
    if (head === 'article') return showPost(rest && rest[0]);
    return showList(rest && rest[0]);
  }

  /* ------------------------------------------------------------------ 管理區 #admin/articles */
  function isAdmin() { const A = window.TwAccount; const u = A && A.on && A.on() && A.user && A.user(); return !!(u && u.admin); }
  /* 產出佇列（2026-10-16，Andy：「claude 指負責產出文章，內容……點選清單內主題，點選後我可以再次點選產生精選文章，或是短影片」）
     按鈕 → 會員 Worker /v1/articles/jobs/add 排一筆 → GitHub Actions（article-jobs.yml）每小時同步進 repo →
     Claude 排程撰寫、推上 main → 文章 index.json 帶同一個 topic 時自動標「已上架」。*/
  const KIND_T = { article: '精選文章', video: '短影片' };
  const JST = { queued: '排隊中', working: '撰寫中', done: '已完成', failed: '失敗', cancelled: '已取消' };
  const acctCall = (path, body) => { const A = window.TwAccount; return A && typeof A.call === 'function' ? A.call(path, body) : Promise.resolve(null); };
  function loadJobs() {
    return acctCall('/v1/articles/jobs/list', {}).then((j) => { S.jobs = j && Array.isArray(j.jobs) ? j.jobs : null; return S.jobs; });
  }
  const twTime = (ms) => { if (!Number.isFinite(Number(ms))) return ''; const d = new Date(Number(ms) + 8 * 3600e3); return d.toISOString().slice(5, 16).replace('T', ' '); };
  const pubOfTopic = (tid) => { const l = S.idx ? S.idx.list.filter((a) => a.topic === tid) : []; return l.length ? l[0] : null; };   // 清單已依日期新到舊
  /* 一個主題的產出狀態：已上架的文章優先，其次是各種類最新一筆請求 */
  function jobChips(tid) {
    const out = [], pub = pubOfTopic(tid);
    /* Andy 10-16：「產出狀態必須備註是文章還是短影片」→ 每顆狀態前面一個種類小標（文章／短影片） */
    if (pub) out.push(`<a class="js done" data-kind="article" href="#article/${encodeURIComponent(pub.id)}" title="${esc(pub.title)}"><em class="kd article">文章</em>已上架</a>`);
    ['article', 'video'].forEach((k) => {
      if (k === 'article' && pub) return;
      const j = (S.jobs || []).find((x) => x.topic_id === tid && x.kind === k && x.status !== 'cancelled');
      if (j) out.push(`<span class="js ${esc(j.status)}" data-kind="${k}" title="#${esc(j.id)} ${esc(twTime(j.created))} 送出"><em class="kd ${k}">${k === 'article' ? '文章' : '短影片'}</em>${esc(JST[j.status] || j.status)}</span>`);
    });
    return out.join('') || '<span class="muted">—</span>';
  }
  async function renderAdmin(v) {
    css();
    if (!isAdmin()) {
      v.innerHTML = '<div class="card artadm"><h3>精選文章管理</h3><p class="muted">這一頁只有管理者看得到。</p></div>';
      return;
    }
    v.innerHTML = '<div class="card artadm"><p class="muted">載入中…</p></div>';
    const [idx, tp] = await Promise.all([loadIndex(), loadTopics(), loadJobs()]);
    if (location.hash !== '#admin/articles') return;
    loadStats(true);
    const list = idx ? idx.list : [];
    const gm = new Map(); list.forEach((a) => (a.groups || []).forEach((g) => { if (!gm.has(g.id)) gm.set(g.id, g.name); }));
    const grpOpts = [...gm].sort((x, y) => x[1].localeCompare(y[1], 'zh-Hant')).map(([id, n]) => `<option value="${esc(id)}">${esc(n)}</option>`).join('');
    v.innerHTML = `
<section id="artStats" class="artadm"></section>
<div class="card artadm" id="artAdmList">
  <div class="hd"><h3>已上架文章</h3><span class="muted">${list.length} 篇${idx && idx.updated ? '・清單更新 ' + esc(idx.updated) : ''}</span></div>
  <div class="aflt" id="artAdmFlt">
    <div class="nbsw lv2" id="artAfCats" role="tablist" aria-label="已上架文章類別"><button type="button" role="tab" data-cat="all">全部</button>${CAT_KEYS.map((k) => `<button type="button" role="tab" data-cat="${k}">${CATS[k].t}</button>`).join('')}</div>
    <select id="artAfGrp" aria-label="族群"><option value="">全部族群</option>${grpOpts}</select>
    <label>日期 <input type="date" id="artAfFrom" aria-label="起"></label><label>～ <input type="date" id="artAfTo" aria-label="迄"></label>
    <input type="search" id="artAfQ" placeholder="搜尋標題" aria-label="搜尋標題">
    <button type="button" class="clr" id="artAfClr">清除</button>
    <span class="cnt" id="artAfCnt"></span>
  </div>
  <div class="tbw"><table><colgroup><col style="width:120px"><col><col style="width:110px"><col style="width:70px"><col style="width:18%"><col style="width:22%"></colgroup>
  <thead><tr><th class="c">類別</th><th>標題</th><th class="c">日期</th><th class="r" title="會員 Worker 統計的點閱次數；讀不到寫「—」">點閱</th><th>相關族群</th><th>來源主題</th></tr></thead><tbody id="artAdmBody"></tbody></table></div>
</div>
<div class="card artadm" id="artAdmTopics">
  <div class="hd"><h3>主題候選清單</h3><span class="muted" id="artTpUpd">${tp && tp.updated ? '更新 ' + esc(tp.updated) : ''}・點列勾選主題（最多 5 個、可跨類別），再按上方按鈕交給 Claude 撰寫</span><span class="sp"></span>
    <button type="button" class="btn small" id="artTpSort" title="切換分數排序方向"></button></div>
  <div class="tpact" id="artTpAct">
    <div class="sel" id="artTpSel"></div>
    <input type="text" id="artTpNote" maxlength="500" placeholder="給 Claude 的補充（選填；會寫進公開的 repo，請勿填個資）">
    <button type="button" id="artGenArt" data-kind="article" disabled>產生精選文章</button>
    <button type="button" id="artGenVid" data-kind="video" disabled>產生短影片</button>
  </div>
  <p class="tpmsg" id="artTpMsg" role="status" hidden></p>
  <div class="nbsw lv2" id="artTpCats" role="tablist" aria-label="候選主題分類"><button type="button" role="tab" data-cat="all">全部</button>${CAT_KEYS.map((k) => `<button type="button" role="tab" data-cat="${k}">${CATS[k].t}</button>`).join('')}</div>
  <div class="nbbody"><div class="tbw"><table><colgroup><col style="width:44px"><col style="width:96px"><col style="width:120px"><col style="width:30%"><col><col style="width:84px"><col style="width:190px"></colgroup>
  <thead><tr><th class="c">選</th><th>分數</th><th class="c">類別</th><th>標題</th><th>理由</th><th class="c">建議形式</th><th>產出狀態</th></tr></thead><tbody id="artTpBody"></tbody></table></div></div>
</div>
<div class="card artadm" id="artAdmJobs">
  <div class="hd"><h3>產出進度</h3><span class="muted">排隊中的請求由 Claude 每天台北 09:50、14:50、20:50 三輪處理；文章推上線後這裡自動變「已完成」</span></div>
  <div class="aflt" id="artJobFlt">
    <select id="artJfKind" aria-label="產出種類"><option value="">全部種類</option><option value="article">精選文章</option><option value="video">短影片</option></select>
    <select id="artJfSt" aria-label="狀態"><option value="">全部狀態</option>${Object.keys(JST).map((k) => `<option value="${k}">${JST[k]}</option>`).join('')}</select>
    <input type="search" id="artJfQ" placeholder="搜尋主題或補充" aria-label="搜尋主題或補充">
    <button type="button" class="clr" id="artJfClr">清除</button>
    <span class="cnt" id="artJfCnt"></span>
  </div>
  <div class="tbw"><table><colgroup><col style="width:64px"><col style="width:96px"><col style="width:30%"><col><col style="width:96px"><col style="width:120px"><col style="width:96px"></colgroup>
  <thead><tr><th class="r">編號</th><th class="c">產出</th><th>主題</th><th>補充</th><th class="c">狀態</th><th class="c">送出時間</th><th class="c">操作</th></tr></thead><tbody id="artJobBody"></tbody></table></div>
</div>`;
    $$('#artTpCats>button', v).forEach((b) => { b.onclick = () => { S.tcat = b.dataset.cat; paintTopics(v); }; });
    $('#artTpSort', v).onclick = () => { S.tsort = S.tsort === 'desc' ? 'asc' : 'desc'; paintTopics(v); };
    $('#artTpBody', v).addEventListener('click', (e) => {
      if (e.target.closest('a')) return;
      const tr = e.target.closest('tr[data-tid]'); if (!tr) return;
      toggleSel(v, tr.dataset.tid);
    });
    $('#artTpSel', v).addEventListener('click', (e) => { const b = e.target.closest('button[data-rm]'); if (b) toggleSel(v, b.dataset.rm); });
    // 已上架文章篩選
    const af = S.af;
    $$('#artAfCats>button', v).forEach((b) => { b.onclick = () => { af.cat = b.dataset.cat; paintAdmList(v); }; });
    const bind = (id, k, ev) => { const el = $(id, v); el.value = af[k]; el.addEventListener(ev, () => { af[k] = el.value.trim(); paintAdmList(v); }); };
    bind('#artAfGrp', 'grp', 'change'); bind('#artAfFrom', 'from', 'change'); bind('#artAfTo', 'to', 'change'); bind('#artAfQ', 'q', 'input');
    if (af.grp && !gm.has(af.grp)) af.grp = '';
    $('#artAfClr', v).onclick = () => { Object.assign(af, { cat: 'all', grp: '', from: '', to: '', q: '' }); ['#artAfGrp', '#artAfFrom', '#artAfTo', '#artAfQ'].forEach((id) => { $(id, v).value = ''; }); paintAdmList(v); };
    paintAdmList(v);
    // 產出進度篩選（Andy 10-16：「產出進度也需要有篩選功能」）
    const jf = S.jf;
    const jb = (id, k, ev) => { const el = $(id, v); el.value = jf[k]; el.addEventListener(ev, () => { jf[k] = el.value.trim(); paintJobs(v); }); };
    jb('#artJfKind', 'kind', 'change'); jb('#artJfSt', 'st', 'change'); jb('#artJfQ', 'q', 'input');
    $('#artJfClr', v).onclick = () => { Object.assign(jf, { kind: '', st: '', q: '' }); ['#artJfKind', '#artJfSt', '#artJfQ'].forEach((id) => { $(id, v).value = ''; }); paintJobs(v); };
    $$('#artGenArt,#artGenVid', v).forEach((b) => { b.onclick = () => submitJob(v, b.dataset.kind); });
    $('#artJobBody', v).addEventListener('click', async (e) => {
      const b = e.target.closest('button[data-cancel]'); if (!b) return;
      b.disabled = true;
      const r = await acctCall('/v1/articles/jobs/cancel', { id: Number(b.dataset.cancel) });
      tpMsg(v, r && r.ok ? `已取消 #${b.dataset.cancel}` : '取消失敗：這筆可能已經開始撰寫', !(r && r.ok));
      await loadJobs(); paintTopics(v); paintJobs(v);
    });
    paintTopics(v); paintJobs(v);
    paintStats(v); Promise.all([loadDaily(), loadStats(true)]).then(() => { if (location.hash === '#admin/articles') paintStats(v); });
  }
  function tpMsg(v, t, err) { const m = $('#artTpMsg', v); if (!m) return; m.hidden = !t; m.textContent = t || ''; m.classList.toggle('err', !!err); }
  const SEL_MAX = 5;
  function toggleSel(v, tid) {
    const i = S.tsels.indexOf(tid);
    if (i >= 0) { S.tsels.splice(i, 1); tpMsg(v, ''); }
    else if (S.tsels.length >= SEL_MAX) { tpMsg(v, `最多一次選 ${SEL_MAX} 個主題，先取消一個再選`, true); return; }
    else { S.tsels.push(tid); tpMsg(v, ''); }
    paintTopics(v);
  }
  async function submitJob(v, kind) {
    const picks = S.tsels.map((id) => S.topics && S.topics.list.find((x) => x.id === id)).filter(Boolean);
    if (!picks.length || !KIND_T[kind]) return;
    $$('#artGenArt,#artGenVid', v).forEach((b) => { b.disabled = true; });
    const note = (($('#artTpNote', v) || {}).value || '').trim();
    const ok = [], dup = [], bad = []; let err = '';
    for (const t of picks) {   // 一筆一筆送（Worker 端逐筆檢查重複），不並發
      const r = await acctCall('/v1/articles/jobs/add', { topic_id: t.id, kind, title: t.title, note });
      if (r && r.job) (r.dup ? dup : ok).push(`#${r.job.id}「${t.title}」`);
      else { bad.push(`「${t.title}」`); err = err || (r && r._s === 403 ? '登入身分不是管理者（請重新登入）' : r && r.error === 'too_many' ? '排隊中的請求太多（上限 100 筆）' : '連不到會員伺服器，請稍後再試'); }
    }
    const parts = [];
    if (ok.length) parts.push(`已送出 ${ok.length} 筆${KIND_T[kind]}：${ok.join('、')}`);
    if (dup.length) parts.push(`已經在排隊、不重複送出：${dup.join('、')}`);
    if (bad.length) parts.push(`送出失敗（${err}）：${bad.join('、')}`);
    tpMsg(v, parts.join('；') + (ok.length ? '。Claude 下一輪會撰寫，完成後出現在「已上架文章」' : ''), !!bad.length);
    if (!bad.length) { S.tsels = []; if ($('#artTpNote', v)) $('#artTpNote', v).value = ''; }
    await loadJobs(); paintTopics(v); paintJobs(v);
  }
  function paintAdmList(v) {
    const body = $('#artAdmBody', v); if (!body) return;
    const af = S.af, all = S.idx ? S.idx.list : [];
    $$('#artAfCats>button', v).forEach((b) => { const on = b.dataset.cat === af.cat; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); });
    const q = af.q.toLowerCase();
    const rows = all.filter((a) => (af.cat === 'all' || a.cat === af.cat) && (!af.grp || (a.groups || []).some((g) => g.id === af.grp))
      && (!af.from || a.date >= af.from) && (!af.to || a.date <= af.to) && (!q || String(a.title).toLowerCase().includes(q) || (a.tags || []).some((t) => String(t).toLowerCase().includes(q))));
    const c = $('#artAfCnt', v); if (c) { c.textContent = `${rows.length}／${all.length} 篇`; c.dataset.n = String(rows.length); }
    const tpTitle = (id) => { const t = S.topics && S.topics.list.find((x) => x.id === id); return t ? t.title : ''; };
    body.innerHTML = rows.length ? rows.map((a) => { const gs = (a.groups || []).map((g) => g.name);
      return `<tr data-id="${esc(a.id)}" data-cat="${esc(a.cat)}" data-date="${esc(a.date)}"><td class="c">${badge(a.cat)}</td><td class="l" title="${esc(a.title)}"><a href="#article/${encodeURIComponent(a.id)}">${esc(a.title)}</a></td>
    <td class="n c">${esc(a.date)}</td><td class="n r" data-vwc="${esc(a.id)}">${viewsOf(a.id) == null ? '—' : viewsOf(a.id).toLocaleString('zh-TW')}</td>
    <td class="dm" title="${esc(gs.join('、'))}">${gs.length ? esc(gs.join('、')) : '<span class="muted">—</span>'}</td>
    <td class="dm" title="${esc(tpTitle(a.topic))}">${a.topic && tpTitle(a.topic) ? esc(tpTitle(a.topic)) : '<span class="muted">—</span>'}</td></tr>`; }).join('')
      : `<tr><td colspan="6" class="muted">${S.idx ? (all.length ? '沒有符合篩選條件的文章' : '還沒有上架的文章') : '文章清單讀不到'}</td></tr>`;
  }
  /* ---------------- 點閱統計 ---------------- */
  function loadDaily() {
    return acctCall('/v1/articles/stats/daily', {}).then((j) => { const ss = S.ss;
      ss.daily = j && Array.isArray(j.rows) ? j.rows.filter((r) => Array.isArray(r) && /^\d{4}-\d\d-\d\d$/.test(r[0]) && okId(r[1]) && Number.isFinite(+r[2])) : null;
      ss.first = j && /^\d{4}-\d\d-\d\d$/.test(String(j.first || '')) ? j.first : null; return ss.daily; });
  }
  const dShift = (d, n) => new Date(Date.parse(d + 'T00:00:00Z') + n * 86400e3).toISOString().slice(0, 10);
  const nf = (n) => Math.round(n).toLocaleString('zh-TW');
  const CAT_COL = { news: 'var(--art-news)', intro: 'var(--art-intro)', know: 'var(--art-know)' };
  const ICO = { eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>', avg: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    doc: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>', star: '<path d="M12 3l2.9 6 6.1.9-4.5 4.3 1.1 6.3L12 17.8 6.4 20.5l1.1-6.3L3 9.9 9.1 9z"/>', sum: '<path d="M18 4H6l6 8-6 8h12"/>' };
  const kpi = (ic, col, n, lab, cls) => `<div style="color:${col}"><span class="ic"><svg viewBox="0 0 24 24" aria-hidden="true">${ICO[ic]}</svg></span><b${cls ? ` class="${cls}"` : ''} title="${esc(String(n))}">${esc(String(n))}</b><span>${esc(lab)}</span></div>`;
  function statRange() {
    const ss = S.ss, today = tpeToday();
    if (ss.period === 'since') return { from: ss.from || dShift(today, -29), to: ss.to || today };
    return { from: dShift(today, -(+ss.period - 1)), to: today };
  }
  function paintStats(v) {
    const box = $('#artStats', v); if (!box) return;
    const ss = S.ss, list = S.idx ? S.idx.list : [], byId = new Map(list.map((a) => [a.id, a]));
    const gm = new Map(); list.forEach((a) => (a.groups || []).forEach((g) => { if (!gm.has(g.id)) gm.set(g.id, g.name); }));
    if (ss.grp && !gm.has(ss.grp)) ss.grp = '';
    const rng = statRange();
    const pass = (a) => a && (!ss.cat || a.cat === ss.cat) && (!ss.grp || (a.groups || []).some((g) => g.id === ss.grp));
    const rows = (ss.daily || []).filter((r) => r[0] >= rng.from && r[0] <= rng.to && pass(byId.get(r[1])));
    const days = []; for (let d = rng.from; d <= rng.to && days.length < 400; d = dShift(d, 1)) days.push(d);
    const perDay = {}, perArt = {}, perCat = {}, perGrp = {};
    rows.forEach(([d, id, n]) => { const a = byId.get(id); n = +n;
      (perDay[d] = perDay[d] || {})[a.cat] = (perDay[d][a.cat] || 0) + n;
      perArt[id] = (perArt[id] || 0) + n; perCat[a.cat] = (perCat[a.cat] || 0) + n;
      (a.groups || []).forEach((g) => { if (!ss.grp || g.id === ss.grp) perGrp[g.id] = (perGrp[g.id] || 0) + n; }); });
    const tot = Object.values(perCat).reduce((x, y) => x + y, 0);
    const dsum = (d) => Object.values(perDay[d] || {}).reduce((x, y) => x + y, 0);
    const top = Object.entries(perArt).sort((x, y) => y[1] - x[1]);
    const life = list.filter(pass).reduce((s0, a) => s0 + (viewsOf(a.id) || 0), 0);
    const opt = [['7', '近 7 天'], ['30', '近 30 天'], ['90', '近 90 天'], ['365', '近 365 天'], ['since', '起始日期～至今']];
    const dmax = Math.max(1, ...days.map(dsum)), avg = tot / Math.max(1, days.length), few = days.length <= 14;
    const tip = (d) => `${d}：${nf(dsum(d))} 次` + CAT_KEYS.filter((k) => perDay[d] && perDay[d][k]).map((k) => `\n${CATS[k].t} ${nf(perDay[d][k])}`).join('');
    const dayHtml = !ss.daily ? '<div class="empty">讀不到每日點閱（會員伺服器沒回應）</div>' : !tot ? '<div class="empty">這段期間沒有點閱紀錄</div>'
      : `<div class="dayplot"><div class="dayy">${[1, 0.75, 0.5, 0.25, 0].map((f) => `<span>${nf(dmax * f)}</span>`).join('')}</div><div class="days" id="artStDays">${days.map((d, i) =>
        `<div class="dc" data-day="${d}" data-n="${dsum(d)}" title="${esc(tip(d))}">${CAT_KEYS.filter((k) => perDay[d] && perDay[d][k]).map((k) => `<i style="height:${(perDay[d][k] / dmax * 100).toFixed(1)}%;background:${CAT_COL[k]}"></i>`).join('')}${few || i % Math.ceil(days.length / 8) === 0 ? `<span class="dd">${d.slice(5).replace('-', '/')}</span>` : ''}</div>`).join('')}
        ${days.length > 1 ? `<div class="avg" style="bottom:${(avg / dmax * 100).toFixed(1)}%"><b>平均 ${nf(avg)}</b></div>` : ''}</div></div>`;
    let acc = 0;
    const segs = CAT_KEYS.filter((k) => perCat[k]).map((k) => { const a0 = acc; acc += perCat[k] / tot * 360; return `${CAT_COL[k]} ${a0.toFixed(2)}deg ${acc.toFixed(2)}deg`; });
    const donut = !tot ? '<div class="empty">沒有資料</div>' : `<div class="dn" id="artStDonut"><div class="dnc" role="img" aria-label="各類別點閱占比" style="background:conic-gradient(${segs.join(',')})"><span>期間點閱<b>${nf(tot)}</b></span></div>
      <ul class="lg">${CAT_KEYS.filter((k) => perCat[k]).sort((x, y) => perCat[y] - perCat[x]).map((k) => `<li data-k="${k}" data-n="${perCat[k]}"><i style="background:${CAT_COL[k]}"></i><span>${CATS[k].t}</span><b>${nf(perCat[k])}</b><small>${(perCat[k] / tot * 100).toFixed(1)}%</small></li>`).join('')}</ul></div>`;
    const barsH = (ents, nm, colOf, id) => !ents.length ? '<div class="empty">沒有資料</div>' : `<div class="bars" id="${id}">` + (() => { const mx = Math.max(...ents.map((e) => e[1]), 1);
      return ents.map(([k, n]) => `<span class="bl" title="${esc(nm(k))}" data-k="${esc(k)}">${esc(nm(k))}</span><span class="bt"><i style="width:${(n / mx * 100).toFixed(1)}%;background:${colOf(k)}"></i></span><span class="bn" data-n="${n}">${nf(n)}<small> ${(n / Math.max(1, tot) * 100).toFixed(0)}%</small></span>`).join(''); })() + '</div>';
    const topArt = barsH(top.slice(0, 10), (id) => (byId.get(id) || {}).title || id, (id) => CAT_COL[(byId.get(id) || {}).cat] || 'var(--cyan)', 'artStTop');
    const grpEnts = Object.entries(perGrp).sort((x, y) => y[1] - x[1]).slice(0, 10);
    const grpBars = barsH(grpEnts, (g) => gm.get(g) || g, () => 'var(--cat-1,var(--cyan))', 'artStGrp');
    const best = top[0] && byId.get(top[0][0]);
    box.innerHTML = `<div class="secttl"><h2>點閱統計</h2><small>共 ${nf(tot)} 次點閱</small><span class="sp"></span>
      <select id="artStCat" aria-label="類別"><option value="">全部類別</option>${CAT_KEYS.map((k) => `<option value="${k}"${ss.cat === k ? ' selected' : ''}>${CATS[k].t}</option>`).join('')}</select>
      <select id="artStGrpSel" aria-label="族群"><option value="">全部族群</option>${[...gm].sort((x, y) => x[1].localeCompare(y[1], 'zh-Hant')).map(([id, n]) => `<option value="${esc(id)}"${ss.grp === id ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select>
      ${(() => { const ref = '<button type="button" class="icobtn" id="artStRef" title="重新整理" aria-label="重新整理"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a9 9 0 0 0-15.5-6.2L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 15.5 6.2L21 16"/><path d="M16 16h5v5"/></svg></button>';
        return window.RangePick ? window.RangePick.html({ id: 'artStRng', options: opt, value: ss.period, from: rng.from, to: rng.to, max: tpeToday(), custom: 'since', extra: ref }) : ref; })()}</div>
    <div class="card trkpi"><div class="kpis" id="artStKpi">${kpi('eye', 'var(--cyan)', nf(tot), '期間點閱')}${kpi('avg', 'var(--art-intro)', nf(avg), '日平均')}${kpi('doc', 'var(--art-know)', nf(top.length), '被點文章數')}${kpi('star', 'var(--art-news)', best ? best.title : '—', '最熱門文章', 't')}${kpi('sum', 'var(--ink-2)', nf(life), '累計點閱（上架至今）')}</div></div>
    <div class="admgrid">
      <div class="card s2" id="artStDayCard"><h3>每天被點幾次？</h3><p class="use" title="每天的文章點閱次數，依類別顏色堆疊；虛線＝期間平均">依類別堆疊・虛線＝平均</p><div class="cb">${dayHtml}</div></div>
      <div class="card" id="artStCatCard"><h3>各類別占多少？</h3><p class="use">期間點閱依類別分</p><div class="cb">${donut}</div></div>
      <div class="card s2" id="artStTopCard"><h3>哪篇文章最多人看？</h3><p class="use">期間點閱前 10 名・顏色＝類別</p><div class="cb">${topArt}</div></div>
      <div class="card" id="artStGrpCard"><h3>哪個族群最多人看？</h3><p class="use" title="一篇文章掛多個族群時，點閱分別算進每個族群">文章點閱依相關族群加總・前 10</p><div class="cb">${grpBars}</div></div>
    </div>
    <p class="note">每日點閱自 ${esc(ss.first || '2026-10-16')} 開始記錄；之前的只有累計數。只記「哪天、哪篇、幾次」，不記是誰；同一人 30 分鐘內重複打開只算一次。</p>`;
    $('#artStCat', box).onchange = (e) => { ss.cat = e.target.value; paintStats(v); };
    $('#artStGrpSel', box).onchange = (e) => { ss.grp = e.target.value; paintStats(v); };
    $('#artStRef', box).onclick = () => { loadDaily().then(() => { loadStats(true); paintStats(v); }); };
    if (window.RangePick) window.RangePick.bind($('#artStRng', box), { onChange: ({ value, from, to }) => { ss.period = value; if (value === 'since') { ss.from = from; ss.to = to; } paintStats(v); } });
  }
  function paintJobs(v) {
    const body = $('#artJobBody', v); if (!body) return;
    if (!S.jobs) { body.innerHTML = '<tr><td colspan="7" class="muted">讀不到產出紀錄（會員伺服器沒回應）</td></tr>'; return; }
    const jf = S.jf, q = jf.q.toLowerCase();
    const hit = S.jobs.filter((j) => (!jf.kind || j.kind === jf.kind) && (!jf.st || j.status === jf.st)
      && (!q || String(j.title || '').toLowerCase().includes(q) || String(j.note || '').toLowerCase().includes(q)));
    const rows = hit.slice(0, 100);
    const c = $('#artJfCnt', v); if (c) { c.textContent = `${hit.length}／${S.jobs.length} 筆${hit.length > rows.length ? '（顯示前 100 筆）' : ''}`; c.dataset.n = String(hit.length); }
    body.innerHTML = rows.length ? rows.map((j) => {
      const pub = j.kind === 'article' && j.status === 'done' && j.result && S.idx && S.idx.list.find((a) => a.id === j.result);
      const op = j.status === 'queued' ? `<button type="button" class="cx" data-cancel="${esc(j.id)}">取消</button>`
        : pub ? `<a href="#article/${encodeURIComponent(pub.id)}">看文章</a>` : '<span class="muted">—</span>';
      return `<tr data-job="${esc(j.id)}"><td class="n r">#${esc(j.id)}</td><td class="c"><span class="kdc js"><em class="kd ${esc(j.kind)}">${esc(KIND_T[j.kind] || j.kind)}</em></span></td><td title="${esc(j.title)}">${esc(j.title)}</td>
        <td class="dm" title="${esc(j.note || '')}">${j.note ? esc(j.note) : '<span class="muted">—</span>'}</td><td class="c"><span class="js ${esc(j.status)}">${esc(JST[j.status] || j.status)}</span></td>
        <td class="n c">${esc(twTime(j.created))}</td><td class="c">${op}</td></tr>`;
    }).join('') : `<tr><td colspan="7" class="muted">${S.jobs.length ? '沒有符合篩選條件的請求' : '還沒有送出過產出請求'}</td></tr>`;
  }
  function paintTopics(v) {
    const body = $('#artTpBody', v); if (!body) return;
    $$('#artTpCats>button', v).forEach((b) => { const on = b.dataset.cat === S.tcat; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); });
    $('#artTpSort', v).textContent = S.tsort === 'desc' ? '分數：高 → 低' : '分數：低 → 高';
    S.tsels = S.tsels.filter((id) => S.topics && S.topics.list.some((x) => x.id === id));
    const sels = S.tsels.map((id) => S.topics.list.find((x) => x.id === id));
    const st = $('#artTpSel', v);
    if (st) st.innerHTML = `已選主題 <span class="tpcnt">${sels.length}／${SEL_MAX}</span>：` + (sels.length
      ? sels.map((t) => `<span class="tpchip" data-tid="${esc(t.id)}">${badge(t.cat)}<span title="${esc(t.title)}">${esc(t.title)}</span><button type="button" data-rm="${esc(t.id)}" aria-label="取消選取 ${esc(t.title)}">×</button></span>`).join('')
      : '<span class="muted">尚未選擇（點下方列勾選，最多 5 個，可跨類別）</span>');
    $$('#artGenArt,#artGenVid', v).forEach((b) => { b.disabled = !sels.length; });
    if (!S.topics) { body.innerHTML = '<tr><td colspan="7" class="muted">主題候選清單讀不到</td></tr>'; return; }
    const mx = 5;   // 分數是 1～5 分（市場研調的評分口徑）
    const rows = S.topics.list.filter((t) => S.tcat === 'all' || t.cat === S.tcat)
      .sort((a, b) => ((Number(b.score) || 0) - (Number(a.score) || 0)) * (S.tsort === 'desc' ? 1 : -1));
    body.innerHTML = rows.length ? rows.map((t) => `<tr data-tid="${esc(t.id)}" data-score="${esc(Number(t.score) || 0)}" aria-selected="${S.tsels.includes(t.id) ? 'true' : 'false'}">
      <td class="c"><span class="rd" aria-hidden="true"></span></td>
      <td class="n"><span class="scb"><i><b style="width:${Math.round(100 * Math.min(mx, Number(t.score) || 0) / mx)}%"></b></i>${esc(Number(t.score) || 0)}<small class="muted">/5</small></span></td>
      <td class="c">${CATS[t.cat] ? badge(t.cat) : esc(t.cat || '')}</td><td class="l" title="${esc(t.title)}">${esc(t.title)}</td>
      <td class="dm" title="${esc(t.why || '')}">${esc(t.why || '')}</td><td class="c">${esc(t.format_hint || '')}</td><td>${jobChips(t.id)}</td></tr>`).join('')
      : '<tr><td colspan="7" class="muted">這個分類沒有候選主題</td></tr>';
  }

  (window.TwSubRoutes = window.TwSubRoutes || []).push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'articles') return null;
    const T = window.TwSub; const v = T && T.view ? T.view('v-subadm') : document.getElementById('v-subadm'); if (!v) return null;
    renderAdmin(v);
    return 'v-subadm';
  });
  // 管理者身分是非同步回來的（登入、/v1/me）：回來時若正停在這一頁就重畫一次
  window.addEventListener('tw:account', () => { if (location.hash === '#admin/articles') { const v = document.getElementById('v-subadm'); if (v) renderAdmin(v); } });

  window.TwArticles = { show, catOf, state: () => S, renderAdmin };
  /* 保險：這支排在 app.js 後面載入。若 app.js 第一次跑 route() 時這支還沒載好（直接開 #articles／#article/<id> 的網址），
     那一次就沒人畫 —— 開站後看一眼：頁面已經切到 #v-articles 但裡面是空的，就自己補畫一次。*/
  function boot() {
    css();   // 側欄子項的類別色、--art-* 變數要在第一次進文章頁之前就有
    const h = (location.hash || '').replace(/^#/, '').split('/').map((x) => { try { return decodeURIComponent(x); } catch (e) { return x; } });
    const v = document.getElementById('v-articles');
    if ((h[0] === 'articles' || h[0] === 'article') && v && !v.firstChild) show(h[0], h.slice(1));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 0)); else setTimeout(boot, 0);
})();
