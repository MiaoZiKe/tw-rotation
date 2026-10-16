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

  const S = { idx: null, idxP: null, idxErr: false, cat: 'all', q: '', from: null, to: null, grp: new Set(), ms: null,
    posts: {}, cur: '', curData: null, backOk: false, topics: null, topicsP: null, tcat: 'all', tsort: 'desc' };

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
  --art-t-chip:#6f9dff;--art-t-mem:#3fd6c2;--art-t-interposer:#f2c14e;--art-t-substrate:#e3925c;--art-t-board:#8ea2cc;--art-t-bump:#c6cfdf;--art-t-other:#9aa6c0;--art-t-ink:#0b1220}
:root[data-theme="light"]{--art-news:#b45309;--art-intro:#0f766e;--art-know:#7e22ce;--art-hl:#a36d00;
  --art-t-chip:#2f5fb3;--art-t-mem:#13786d;--art-t-interposer:#946200;--art-t-substrate:#a24a1a;--art-t-board:#4c5d80;--art-t-bump:#6b7385;--art-t-other:#5d6b88;--art-t-ink:#ffffff}
.k-all{--k:var(--art-all)}.k-news{--k:var(--art-news)}.k-intro{--k:var(--art-intro)}.k-know{--k:var(--art-know)}
/* 側欄子項的圖示上類別色（layout4.js 畫的 .l4subtab；選中那格字仍是主色，圖示保留類別色當辨識） */
:root.l4 .l4subtab[data-l4sub="art-news"] .ic{color:var(--art-news);opacity:1}
:root.l4 .l4subtab[data-l4sub="art-intro"] .ic{color:var(--art-intro);opacity:1}
:root.l4 .l4subtab[data-l4sub="art-know"] .ic{color:var(--art-know);opacity:1}
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
.artlist{grid-auto-flow:row dense;display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:var(--gap-card,12px);align-items:stretch;align-content:start}
.artc{position:relative;display:flex;flex-direction:column;gap:6px;min-width:0;min-height:214px;box-sizing:border-box;padding:var(--sp-3) var(--sp-4) var(--sp-3) calc(var(--sp-4) + 4px);
  border:1px solid var(--line);border-radius:var(--r,12px);overflow:hidden;
  background:linear-gradient(135deg,color-mix(in srgb,var(--k) 8%,var(--panel)) 0%,var(--panel) 55%);color:var(--ink);text-decoration:none;transition:border-color .15s,transform .15s}
.artc::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--k)}
.artc.hero{grid-column:1/-1;min-height:200px;padding:var(--sp-4) var(--sp-5) var(--sp-4) calc(var(--sp-5) + 4px);
  background:linear-gradient(120deg,color-mix(in srgb,var(--k) 16%,var(--panel)) 0%,var(--panel) 65%)}
.artc.hero .tt{font-size:var(--fs-h2);-webkit-line-clamp:2}
.artc.hero .st{font-size:var(--fs-body)}
.artc.hero .sm{font-size:var(--fs-body);-webkit-line-clamp:3;max-width:78%}
.artlist[data-cols="3"] .artc.hero,.artlist[data-cols="4"] .artc.hero,.artlist[data-cols="5"] .artc.hero{grid-column:span 2;grid-row:span 2}
.artlist[data-cols="3"] .artc.hero .sm,.artlist[data-cols="4"] .artc.hero .sm,.artlist[data-cols="5"] .artc.hero .sm{-webkit-line-clamp:6;max-width:none}
.artc .hx{display:none}
.artlist[data-cols="3"] .artc.hero .hx,.artlist[data-cols="4"] .artc.hero .hx,.artlist[data-cols="5"] .artc.hero .hx{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--sp-2);margin-top:var(--sp-2);position:relative;z-index:1;max-width:82%}
.artc .hx .hk{padding:8px 10px;border:1px solid color-mix(in srgb,var(--k) 35%,var(--line));border-radius:10px;background:color-mix(in srgb,var(--panel) 85%,transparent);min-width:0}
.artc .hx .hk i{display:block;font-style:normal;font-size:var(--fs-min);color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artc .hx .hk b{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:20px;color:var(--ink)}
.artc .hx .hk small{font-size:var(--fs-min);color:var(--ink-3);margin-left:3px}
.artc .hx .hk em{font-style:normal;font-family:var(--mono);font-size:var(--fs-min);font-weight:700;margin-left:6px}
.artc .hx .hk em.up{color:var(--rise)}.artc .hx .hk em.dn{color:var(--fall)}
.artc .hx .hs{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:var(--fs-sm);color:var(--ink-2)}
.artc .hx .hs span::before{content:"▸";color:var(--k);margin-right:4px}
.artc.hero .wm{right:24px;bottom:auto;top:50%;transform:translateY(-50%);opacity:.13}
.artc .wm{position:absolute;right:-10px;bottom:-12px;color:var(--k);opacity:.08;pointer-events:none}
.artc:hover,.artc:focus-visible{border-color:var(--k);transform:translateY(-1px)}
.artc .r1{display:flex;align-items:center;gap:var(--sp-2);font-size:var(--fs-min);color:var(--ink-3);white-space:nowrap}
.artc .r1 .d{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink-2)}
.artc .r1 .rm{margin-left:auto;overflow:hidden;text-overflow:ellipsis}
.artc .tt{font-size:var(--fs-h3);font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.artc .st{font-size:var(--fs-sm);color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artc .sm{font-size:var(--fs-sm);color:var(--ink-3);line-height:1.6;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.artc .ft{margin-top:auto;display:flex;gap:6px;flex-wrap:wrap;overflow:hidden;min-width:0;max-height:58px;padding-top:4px}
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
.artpage{display:grid;grid-template-columns:minmax(0,1fr);gap:var(--sp-4);align-items:start;max-width:1240px;margin:0 auto}
@media (min-width:1280px){.artpage{grid-template-columns:minmax(0,1fr) 250px}}
.artpost{min-width:0}
.artback{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;margin-bottom:var(--sp-2);border:1px solid var(--line-2);border-radius:var(--r-sm,8px);background:var(--panel-3);color:var(--ink);font:inherit;font-size:var(--fs-sm);cursor:pointer}
.artback:hover{border-color:var(--k,var(--cyan));color:var(--k,var(--cyan))}
.artcrumb{display:flex;align-items:center;gap:6px;font-size:var(--fs-sm);color:var(--ink-3);margin-bottom:var(--sp-3);white-space:nowrap;overflow:hidden}
.artcrumb a{color:var(--cyan);text-decoration:none;display:inline-flex;align-items:center;gap:4px}
.artcrumb a.kc{color:var(--k)}
.artcrumb a:hover{text-decoration:underline}
.artcrumb .cur{color:var(--ink-2);overflow:hidden;text-overflow:ellipsis}
.artpost h2.artttl{margin:var(--sp-2) 0 6px;font-size:24px;line-height:1.4;font-weight:700}
.artpost .artsub{margin:0 0 var(--sp-3);font-size:var(--fs-h3);color:var(--ink-2);line-height:1.6}
.artmeta{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2) var(--sp-3);font-size:var(--fs-sm);color:var(--ink-2)}
.artmeta .mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.artpost .arttags{flex-wrap:wrap;margin:var(--sp-3) 0}
.artgps{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 var(--sp-3)}
.artgps .lb{font-size:var(--fs-sm);color:var(--ink-3)}
.artgps button.artgp{font:inherit;font-size:var(--fs-min);cursor:pointer;height:24px}
.artgps button.artgp:hover{border-color:var(--k)}
.artlead{margin:var(--sp-3) 0;padding:var(--sp-3) var(--sp-4);border-left:3px solid var(--k,var(--cyan));background:var(--panel-3);border-radius:0 var(--r-sm,8px) var(--r-sm,8px) 0;
  font-size:15px;line-height:1.8;color:var(--ink)}
.artbody{font-size:15.5px;line-height:1.85;color:var(--ink)}
.artbody>p,.artbody>ul,.artbody>h4{max-width:860px}
.artbody h4{margin:var(--sp-5) 0 var(--sp-2);font-size:18px;line-height:1.4;font-weight:700;display:flex;align-items:center;gap:var(--sp-2);scroll-margin-top:16px}
.artbody h4::before{content:"";flex:none;width:4px;height:16px;border-radius:2px;background:var(--k,var(--cyan))}
.artbody p{margin:0 0 var(--sp-3)}
.artbody ul{margin:0 0 var(--sp-3);padding-left:1.4em}
.artbody li{margin:4px 0}
.artbody .callout{margin:var(--sp-4) 0;padding:var(--sp-3) var(--sp-4);border:1px solid color-mix(in srgb,var(--amber) 55%,transparent);border-radius:var(--r-sm,8px);
  background:color-mix(in srgb,var(--amber) 9%,var(--panel));font-weight:600}
.artbody .tbw{overflow-x:auto;margin:var(--sp-3) 0 var(--sp-4);border:1px solid var(--line);border-radius:var(--r-sm,8px)}
.artbody table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.5}
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
.artfig{margin:var(--sp-4) 0;padding:var(--sp-3) var(--sp-4);border:1px solid var(--line);border-radius:var(--r,12px);background:var(--panel-2);font-size:var(--fs-body);line-height:1.5}
.artfig .fh{display:flex;align-items:center;gap:var(--sp-2);margin:0 0 var(--sp-2);font-size:var(--fs-h3);font-weight:600;color:var(--ink)}
.artfig .fh::before{content:"";flex:none;width:4px;height:14px;border-radius:2px;background:var(--k,var(--cyan))}
.artfig .fn2{margin:var(--sp-2) 0 0;font-size:var(--fs-min);color:var(--ink-3);line-height:1.6}
.artfig .fn2 span+span::before{content:"　"}
.artfig .mk{margin:var(--sp-2) 0 0;display:flex;flex-wrap:wrap;gap:6px 12px;font-size:var(--fs-sm);color:var(--ink-2)}
.artfig .mk span::before{content:"◆";color:var(--art-hl);margin-right:4px}
.artchart .cv{width:100%;height:300px}
/* kpi 數字卡 */
.artkpi{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));gap:var(--sp-2);margin:var(--sp-4) 0}
.artkpi .akc{min-width:0;padding:var(--sp-3);border:1px solid var(--line);border-radius:var(--r,12px);background:var(--panel-2);text-align:center;display:flex;flex-direction:column;gap:4px;justify-content:center}
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
.artflow .fnd{min-width:0;padding:8px 10px;border:1px solid var(--line-2);border-left:3px solid var(--fc);border-radius:10px;background:var(--panel);transition:border-color .12s,box-shadow .12s}
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
.artmore .artc{min-height:0;padding-top:var(--sp-2);padding-bottom:var(--sp-2)}
.artmore .artc .tt{font-size:var(--fs-body)}
.artmore .artc .sm{display:none}
.artdisc{margin:var(--sp-4) 0 0;font-size:var(--fs-min);color:var(--ink-3);line-height:1.6}
.artend{display:flex;justify-content:center;margin-top:var(--sp-4)}
.artend a{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 18px;border:1px solid var(--k,var(--cyan));border-radius:999px;color:var(--k,var(--cyan));text-decoration:none;font-size:var(--fs-sm);font-weight:600}
.artend a:hover{background:color-mix(in srgb,var(--k,var(--cyan)) 12%,transparent)}
.arterr{padding:var(--sp-5) var(--sp-3);text-align:center;color:var(--ink-2);font-size:var(--fs-body)}
.arterr a{color:var(--cyan)}
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
  .artc{padding:var(--sp-3) var(--sp-3) var(--sp-3) calc(var(--sp-3) + 4px);min-height:0}
  .artc .sm{display:none}   /* 手機只留重點（準則 3）：摘要點進去才看 */
  .artempty{min-height:260px}
  .artpost h2.artttl{font-size:21px}
  .artbody{font-size:16px;line-height:1.85}
  .artlead{font-size:15px}
  .artbody h4{font-size:17px}
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
}
`;
    s.textContent += ADM_CSS;
    document.head.appendChild(s);
  }
  const ADM_CSS = `
/* ---- 管理區 #admin/articles ---- */
#v-subadm .artadm h3{margin:0;font-size:var(--fs-h3);font-weight:600}
#v-subadm .artadm .hd{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap;margin-bottom:var(--sp-2)}
#v-subadm .artadm .hd .sp{flex:1}
#v-subadm .artadm .tbw{overflow-x:auto}
#v-subadm .artadm table{width:100%;border-collapse:collapse;font-size:var(--fs-sm)}
#v-subadm .artadm th,#v-subadm .artadm td{padding:6px 8px;border-bottom:1px solid var(--line);height:32px;white-space:nowrap;text-align:center}
#v-subadm .artadm th{color:var(--ink-2);font-weight:600;font-size:var(--fs-min)}
#v-subadm .artadm td.l{text-align:left;max-width:300px;overflow:hidden;text-overflow:ellipsis}
#v-subadm .artadm td.l a{color:var(--ink);text-decoration:none}
#v-subadm .artadm td.l a:hover{color:var(--cyan)}
#v-subadm .artadm td.n{font-family:var(--mono);font-variant-numeric:tabular-nums}
#v-subadm .artadm td.act{text-align:left}
#v-subadm .artadm td.act button{height:28px;padding:0 10px;margin-right:6px;border-radius:var(--r-sm,8px);border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:var(--fs-min)}
#v-subadm .artadm td.act button:disabled{opacity:.45;cursor:not-allowed}
#v-subadm .artadm td.act small{font-size:var(--fs-min);color:var(--ink-3)}
#v-subadm .artadm .stp{display:inline-block;font-size:var(--fs-min);padding:1px 8px;border-radius:999px;border:1px solid color-mix(in srgb,var(--cyan) 55%,transparent);color:var(--cyan)}
#v-subadm .artadm .stp.draft{border-color:var(--line-2);color:var(--ink-2)}
#v-subadm .artadm .scb{display:inline-flex;align-items:center;gap:6px}
#v-subadm .artadm .scb i{display:block;height:6px;border-radius:3px;background:var(--cat-1,var(--cyan))}
#v-subadm .artadm .why{text-align:left;color:var(--ink-2);max-width:320px;overflow:hidden;text-overflow:ellipsis}   /* 一行＋滑過看全文（style_guide 一-3：文字一行，不准換行撐高列）*/
#v-subadm .artadm .muted{color:var(--ink-3);font-size:var(--fs-sm)}
#v-subadm .artadm .lnk{text-align:left;max-width:240px;overflow:hidden;text-overflow:ellipsis}
#v-subadm .artadm .lnk a{color:var(--cyan);margin-right:6px;text-decoration:none;font-size:var(--fs-min)}
#v-subadm .artadm .nbsw{margin-top:var(--sp-1)}
#v-subadm .artadm .nbbody{margin-bottom:0}
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
  const catOf = (id) => { const a = S.idx && S.idx.list.find((x) => x.id === id); return a ? a.cat : ''; };

  /* 側欄子項亮哪一格（<html data-l4sub>）：單篇頁在清單讀到之前不知道類別，讀到之後補上 */
  function markSub(cat) {
    const r = document.documentElement;
    if (!r.classList.contains('l4') && !r.classList.contains('m4')) return;
    const want = 'art-' + (CATS[cat] ? cat : 'all');
    if (r.getAttribute('data-l4sub') !== want) r.setAttribute('data-l4sub', want);
  }

  /* ------------------------------------------------------------------ 共用小片段 */
  const catT = (k) => (CATS[k] ? CATS[k].t : ALL_T);
  const badge = (cat) => `<span class="artbadge k-${CATS[cat] ? cat : 'all'}">${icon(CATS[cat] ? cat : 'all', 13)}${esc(catT(cat))}</span>`;
  const tagsHTML = (tags) => (Array.isArray(tags) && tags.length ? `<div class="arttags">${tags.slice(0, 8).map((t) => `<span>${esc(t)}</span>`).join('')}</div>` : '');
  const cardHTML = (a, hero) => `<a class="artc k-${esc(a.cat)}${hero ? ' hero' : ''}" href="#article/${encodeURIComponent(a.id)}" data-id="${esc(a.id)}" data-cat="${esc(a.cat)}" data-date="${esc(a.date)}" data-groups="${esc((a.groups || []).map((g) => g.id).join(' '))}" title="${esc(a.title)}">
    <span class="wm">${icon(a.cat, hero ? 150 : 96)}</span>
    <div class="r1">${badge(a.cat)}<span class="d">${esc(a.date)}</span><span class="rm" title="閱讀時間">約 ${esc(Number(a.reading_min) || 1)} 分鐘</span></div>
    <div class="tt">${esc(a.title)}</div>${a.subtitle ? `<div class="st">${esc(a.subtitle)}</div>` : ''}
    ${a.summary ? `<div class="sm">${esc(a.summary)}</div>` : ''}${hero ? '<div class="hx" aria-hidden="true"></div>' : ''}
    <div class="ft">${(a.groups || []).slice(0, 4).map((g) => `<span class="artgp">${esc(g.name)}</span>`).join('')}${(a.groups || []).length ? '' : (Array.isArray(a.tags) ? a.tags.slice(0, 5).map((t) => `<span class="artgp">${esc(t)}</span>`).join('') : '')}</div></a>`;
  const DISC = 'ⓘ 本站文章為公開資訊與產業知識的整理，不構成任何投資建議；內容以資料來源發布時點為準，投資前請自行查證並評估風險。';

  /* ------------------------------------------------------------------ 列表頁 */
  /* 最新一篇放大成橫跨整排的焦點卡（寬螢幕篇數少時，版面不會只有一排小卡＋下面大片空白）；手機不放大 */
  const isNarrow = () => window.innerWidth <= 640;
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
    ${['all'].concat(CAT_KEYS).map((k) => `<button type="button" role="tab" class="k-${k}" data-cat="${k}" title="${esc(catT(k))}">${icon(k, 15)}<span>${esc(catT(k))}</span><em></em></button>`).join('')}
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
    box.innerHTML = list.length ? list.map((a, i) => cardHTML(a, i === 0 && list.length > 1 && !isNarrow())).join('')
      : `<div class="artempty k-${S.cat === 'all' ? 'all' : S.cat}" id="artEmpty">${icon(S.cat, 40)}<div>${dirty ? '這個條件下沒有符合的文章，換個關鍵字、族群或放寬日期試試。' : '近一個月這個分類還沒有文章。'}</div>`
        + `${dirty ? '<button type="button" class="btn small" data-clr>清除篩選</button>' : '<button type="button" class="btn small" data-wide>看全部日期</button>'}</div>`;
    const c2 = $('[data-clr]', box); if (c2) c2.onclick = () => { resetFilters(); paintList(); };
    const c3 = $('[data-wide]', box); if (c3) c3.onclick = () => { S.from = ''; S.to = ''; paintList(); };
    paintSide(root);
    watchCols(box);
    fillHero(box);
  }
  /* 焦點卡：先讀那一篇的內文，把第一組「數字卡」與段落標題放進卡片中段（2×2 的大卡不會只有標題＋大片空白） */
  function fillHero(box) {
    const hx = $('.artc.hero .hx', box); if (!hx) return;
    const id = hx.closest('.artc').dataset.id;
    loadPost(id).then((d) => {
      if (!d || !hx.isConnected) return;
      const bl = Array.isArray(d.blocks) ? d.blocks : [];
      const k = bl.find((b) => b && b.t === 'kpi' && Array.isArray(b.items));
      const ks = k ? k.items.filter((x) => x && x.label).slice(0, 4) : [];
      const hs = bl.filter((b) => b && b.t === 'h' && b.text).slice(0, 6);
      const nf = bl.filter((b) => b && ['chart', 'flow', 'stack'].includes(b.t)).length;
      hx.innerHTML = ks.map((x) => { const dl = String(x.delta == null ? '' : x.delta).trim(); const dc = /^\+/.test(dl) ? 'up' : /^[-−]/.test(dl) ? 'dn' : '';
        return `<div class="hk"><i>${esc(x.label)}</i><b>${esc(x.value)}</b>${x.unit ? `<small>${esc(x.unit)}</small>` : ''}${dl ? `<em class="${dc}">${esc(dl)}</em>` : ''}</div>`; }).join('')
        + (hs.length ? `<div class="hs">${hs.map((h) => `<span>${esc(h.text)}</span>`).join('')}${nf ? `<span>${nf} 張圖表與示意圖</span>` : ''}</div>` : '');
    });
  }
  /* 量目前幾欄（auto-fill 由寬度決定，CSS 不知道）：≥3 欄時焦點卡佔 2×2，旁邊一欄疊兩張，篇數少也不會留一個空格 */
  function watchCols(box) {
    const upd = () => { const n = getComputedStyle(box).gridTemplateColumns.split(' ').filter(Boolean).length; if (box.dataset.cols !== String(n)) box.dataset.cols = String(n); };
    upd();
    if (!box._ro && typeof ResizeObserver !== 'undefined') { box._ro = new ResizeObserver(upd); box._ro.observe(box); }
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
    await loadIndex();
    if (location.hash.replace(/^#/, '').split('/')[0] !== 'articles') return;   // 讀清單的時候使用者已經換頁
    paintList();
  }

  /* ------------------------------------------------------------------ 單篇：內文區塊 */
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
    return `<div class="artkpi" style="--n:${Math.min(4, its.length)}">${its.map((x) => {
      const d = String(x.delta == null ? '' : x.delta).trim();
      const dc = /^\+/.test(d) ? 'up' : /^[-−]/.test(d) ? 'dn' : '';
      return `<div class="akc"><div class="akl" title="${esc(x.label)}">${esc(x.label)}</div><div class="akv"><b>${esc(x.value)}</b>${x.unit ? `<small>${esc(x.unit)}</small>` : ''}</div>`
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
      <div class="fl" style="--cols:${cols.length}"><svg class="fe" aria-hidden="true"></svg>${cols.map((c, ci) => `<div class="fcol" style="--fc:var(--cat-${(ci % 4) + 1})"><div class="fch" title="${esc(c.label)}">${esc(c.label || '')}</div><div class="fnodes">${c.nodes.filter((n) => n && n.label).map((n) => {
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
        const col = [C.c1, C.c2, C.c3][si % 3];
        names.push(sName(s, si));
        out.push({ name: sName(s, si) + '__base', type: 'bar', stack: 'r' + si, silent: true, itemStyle: { color: 'transparent' }, barMaxWidth: 22, data: pr.map((p) => (p ? p[0] : null)),
          label: { show: true, position: 'insideRight', color: C.ink2, fontSize: 12, fontFamily: NF, formatter: (q) => fmtN(q.value) }, tooltip: { show: false } });
        out.push({ name: sName(s, si), type: 'bar', stack: 'r' + si, barMaxWidth: 22, data: pr.map((p, i) => (p ? { value: p[1] - p[0], _r: p, itemStyle: { color: hl.has(i) ? C.hl : col, borderRadius: 3 } } : null)),
          itemStyle: { color: col, borderRadius: 3 },
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
          data: vals.map((v, i) => ({ value: v, itemStyle: hl.has(i) || marks.has(i) ? { color: C.hl } : undefined })),
          itemStyle: { color: C.c1 },
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
      const col = typ === 'bar' ? [C.c1, C.c3][barK++ % 2] : (ax === 1 ? C.c2 : [C.c2, C.c3, C.c1][si % 3]);
      const vals = x.map((_, i) => num(s.data[i]));
      const lab = { show: false, position: 'top', color: C.ink2, fontSize: 12, fontFamily: NF, formatter: (q) => fmtN(q.value) };
      const o = { name: sName(s, si), type: typ, yAxisIndex: ax, itemStyle: { color: col }, label: lab,
        data: vals.map((v, i) => { const d = { value: v }; if (typ === 'bar' && hl.has(i)) d.itemStyle = { color: C.hl }; if (si === 0 || typ === 'bar' || ser0.length === 1) { if (showLab(i)) d.label = { show: true }; } return d; }) };
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
  <div class="artmeta">${cat ? badge(cat) : ''}<span class="mono">${esc(d.date || '')}</span>${upd}<span>閱讀約 ${esc(Number(d.reading_min) || 1)} 分鐘</span>${d.confidence ? `<span title="資料信心：依來源數量與一致性自評">資料信心 ${esc(d.confidence)}</span>` : ''}</div>
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
    document.title = d.title + '｜精選文章';
  }

  /* ------------------------------------------------------------------ 進入點（app.js route() 呼叫） */
  function show(head, rest) {
    if (head === 'article') return showPost(rest && rest[0]);
    return showList(rest && rest[0]);
  }

  /* ------------------------------------------------------------------ 管理區 #admin/articles */
  function isAdmin() { const A = window.TwAccount; const u = A && A.on && A.on() && A.user && A.user(); return !!(u && u.admin); }
  async function renderAdmin(v) {
    css();
    if (!isAdmin()) {
      v.innerHTML = '<div class="card artadm"><h3>精選文章管理</h3><p class="muted">這一頁只有管理者看得到。</p></div>';
      return;
    }
    v.innerHTML = '<div class="card artadm"><p class="muted">載入中…</p></div>';
    const [idx, tp] = await Promise.all([loadIndex(), loadTopics()]);
    if (location.hash !== '#admin/articles') return;
    const list = idx ? idx.list : [];
    const LOCK = '待 Andy 確認後開放';
    v.innerHTML = `
<div class="card artadm" id="artAdmList">
  <div class="hd"><h3>精選文章管理：已上架文章</h3><span class="muted">${list.length} 篇${idx && idx.updated ? '・清單更新 ' + esc(idx.updated) : ''}</span></div>
  <div class="tbw"><table><thead><tr><th>類別</th><th>標題</th><th>日期</th><th>狀態</th><th>產出</th></tr></thead><tbody>
  ${list.length ? list.map((a) => `<tr data-id="${esc(a.id)}"><td>${badge(a.cat)}</td><td class="l"><a href="#article/${encodeURIComponent(a.id)}" title="${esc(a.title)}">${esc(a.title)}</a></td>
    <td class="n">${esc(a.date)}</td><td><span class="stp">已上架</span></td>
    <td class="act"><button type="button" disabled aria-disabled="true" data-act="post" title="${LOCK}">產出貼文</button><button type="button" disabled aria-disabled="true" data-act="video" title="${LOCK}">產出短影片</button><small>${LOCK}</small></td></tr>`).join('')
    : `<tr><td colspan="5" class="muted">${idx ? '還沒有上架的文章' : '文章清單讀不到'}</td></tr>`}
  </tbody></table></div>
</div>
<div class="card artadm" id="artAdmTopics" style="margin-top:var(--gap-card,12px)">
  <div class="hd"><h3>精選文章管理：主題候選清單</h3><span class="muted" id="artTpUpd">${tp && tp.updated ? '更新 ' + esc(tp.updated) : ''}</span><span class="sp"></span>
    <button type="button" class="btn small" id="artTpSort" title="切換分數排序方向"></button></div>
  <div class="nbsw lv2" id="artTpCats" role="tablist" aria-label="候選主題分類"><button type="button" role="tab" data-cat="all">全部</button>${CAT_KEYS.map((k) => `<button type="button" role="tab" data-cat="${k}">${CATS[k].t}</button>`).join('')}</div>
  <div class="nbbody"><div class="tbw"><table><thead><tr><th>分數</th><th>類別</th><th>標題</th><th>理由</th><th>建議形式</th><th>站內頁面</th></tr></thead><tbody id="artTpBody"></tbody></table></div></div>
</div>`;
    $$('#artTpCats>button', v).forEach((b) => { b.onclick = () => { S.tcat = b.dataset.cat; paintTopics(v); }; });
    $('#artTpSort', v).onclick = () => { S.tsort = S.tsort === 'desc' ? 'asc' : 'desc'; paintTopics(v); };
    paintTopics(v);
  }
  function paintTopics(v) {
    const body = $('#artTpBody', v); if (!body) return;
    $$('#artTpCats>button', v).forEach((b) => { const on = b.dataset.cat === S.tcat; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); });
    $('#artTpSort', v).textContent = S.tsort === 'desc' ? '分數：高 → 低' : '分數：低 → 高';
    if (!S.topics) { body.innerHTML = '<tr><td colspan="6" class="muted">主題候選清單讀不到</td></tr>'; return; }
    const mx = 5;   // 分數是 1～5 分（市場研調的評分口徑）
    const rows = S.topics.list.filter((t) => S.tcat === 'all' || t.cat === S.tcat)
      .sort((a, b) => ((Number(b.score) || 0) - (Number(a.score) || 0)) * (S.tsort === 'desc' ? 1 : -1));
    body.innerHTML = rows.length ? rows.map((t) => `<tr data-tid="${esc(t.id)}" data-score="${esc(Number(t.score) || 0)}">
      <td class="n"><span class="scb"><i style="width:${Math.round(40 * Math.min(mx, Number(t.score) || 0) / mx)}px"></i>${esc(Number(t.score) || 0)}<small class="muted">/5</small></span></td>
      <td>${CATS[t.cat] ? badge(t.cat) : esc(t.cat || '')}</td><td class="l" title="${esc(t.title)}">${esc(t.title)}</td>
      <td class="why" title="${esc(t.why || '')}">${esc(t.why || '')}</td><td>${esc(t.format_hint || '')}</td>
      <td class="lnk" title="${esc((Array.isArray(t.site_links) ? t.site_links : []).join('  '))}">${(Array.isArray(t.site_links) ? t.site_links : []).filter(okHash).map((h) => `<a href="${esc(h)}">${esc(h.slice(1))}</a>`).join('')}</td></tr>`).join('')
      : '<tr><td colspan="6" class="muted">這個分類沒有候選主題</td></tr>';
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
