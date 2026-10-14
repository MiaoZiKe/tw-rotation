/* ============================================================================
   精選文章（#articles、#articles/<類別>、#article/<id>）＋管理區「精選文章管理」（#admin/articles）—— 2026-10-14
   ----------------------------------------------------------------------------
   Andy 2026-10-14：「幫我成立一個精選文章母分頁，裡面三個小分頁……精選文章也需要分類……分成 消息 介紹 知識……
   有日期可以篩選文章以及關鍵字搜尋標題」；位置標在左側選單「今日市場 → 總覽」正下方（總覽和財經日曆之間）。

   這一頁回答的問題：「網站整理過、值得讀的文章有哪些？這一篇在講什麼、跟站上哪幾頁、哪幾檔股票有關？」
     · 列表頁：上方分類分頁（全部／消息／介紹／知識，跟側欄子項是同一組網址）、標題關鍵字（即時篩選）、日期從～到、
       卡片依日期新到舊。所以該怎麼用：先挑類別，再用關鍵字或日期縮小範圍，點卡片進去讀。
     · 單篇頁：麵包屑、標題、日期與閱讀時間、標籤、內文區塊、相關台股（點了到個股頁）、站內相關頁面、資料來源（外部連結開新分頁）、免責。

   資料：site/articles/index.json（清單）＋ site/articles/posts/<id>.json（點進單篇才讀）。
     ⚠ 放在 site/articles/ 而不是 site/data/：site/data/ 是 gitignore、由工作流每天重寫；文章是人工產出、要進版控。
     pages.yml 整個 site/ 都部署（預覽分支也會帶著它），sw.js 對任何 .json 一律不快取，所以換文章不必改程式。
   安全：文章內容一律當純文字（esc() 跳脫後才放進畫面），不收 HTML；外部網址只收 http(s)；站內連結只收 # 開頭；
     股票代號只收英數 4～6 碼；文章 id 只收英數、底線、點、減號（不能拿來組出別的路徑）。

   管理區 #admin/articles（只有管理者，判斷同 layout4.js isAdmin：TwAccount 登入且 /v1/me 回 admin=true）：
     · 已上架文章清單：每篇「產出貼文」「產出短影片」兩顆按鈕 —— 目前一律反灰＋旁邊小字「待 Andy 確認後開放」
       （Andy 的規矩：限制用反灰＋旁邊小字，不准跳窗）。
     · 主題候選清單：讀 site/articles/topics.json，可依類別篩選、依分數排序。
   路由：app.js 的 VIEWS 收 'articles'（#article/<id> 也落在同一個 view），#admin/articles 走 TwSubRoutes（同 admin_pay.js）。
   驗收：scripts/_uitest.py「精選文章1014」。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  /* 類別：顏色只用中性的類別色（amber／cyan／violet），紅綠保留給漲跌（style_guide 三） */
  const CATS = { news: { t: '消息', c: 'amber' }, intro: { t: '介紹', c: 'cyan' }, know: { t: '知識', c: 'violet' } };
  const CAT_KEYS = Object.keys(CATS);
  const okId = (id) => /^[\w.-]{1,120}$/.test(String(id || ''));
  const okUrl = (u) => /^https?:\/\/[^\s"'<>]+$/i.test(String(u || ''));
  const okHash = (h) => /^#[^\s"'<>]*$/.test(String(h || ''));   // 站內連結只收 # 開頭（族群 id 可能是中文：#industry/group/ind_半導體業）
  const okCode = (c) => /^[0-9A-Z]{4,6}$/.test(String(c || ''));
  const okDate = (d) => /^\d{4}-\d{2}-\d{2}$/.test(String(d || ''));
  const S = { idx: null, idxP: null, idxErr: false, cat: 'all', q: '', from: '', to: '', posts: {}, cur: '', topics: null, topicsP: null, tcat: 'all', tsort: 'desc' };

  /* ------------------------------------------------------------------ 樣式
     字級、顏色、間距都引用主題變數（style_guide 二～四）。內文 15px 起（手機也是），行高 1.8，一欄、最寬 760px，讀起來不累。 */
  function css() {
    if (document.getElementById('artCss')) return;
    const s = document.createElement('style'); s.id = 'artCss';
    s.textContent = `
#v-articles{max-width:1180px;margin:0 auto}
#v-articles .artcard h3{display:flex;align-items:baseline;gap:var(--sp-2);flex-wrap:wrap}
#v-articles .artcard h3 small{font-size:var(--fs-sm);color:var(--ink-3);font-weight:400}
#artCats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));align-items:end;margin-top:var(--sp-2)}
#artCats>button{min-width:0;overflow:hidden;text-overflow:ellipsis}
.artflt{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2) var(--sp-3);margin:var(--sp-2) 0 var(--sp-3)}
.artflt input{height:32px;box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:var(--r-sm,8px);padding:0 10px;font:inherit;font-size:var(--fs-sm)}
.artflt input[type=search]{flex:1 1 220px;min-width:0}
.artflt input[type=date]{width:150px;font-family:var(--mono);font-variant-numeric:tabular-nums}
.artflt input.chg{border-color:var(--amber)}
.artflt label{display:inline-flex;align-items:center;gap:6px;font-size:var(--fs-sm);color:var(--ink-2);white-space:nowrap}
.artflt .cnt{margin-left:auto;font-size:var(--fs-sm);color:var(--ink-2);white-space:nowrap}
.artflt .cnt b{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink)}
.artlist{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--gap-card,12px);align-items:stretch}
.artc{display:flex;flex-direction:column;gap:6px;min-width:0;padding:var(--sp-3) var(--sp-4);border:1px solid var(--line);border-radius:var(--r,12px);
  background:var(--panel);color:var(--ink);text-decoration:none;transition:border-color .15s,background .15s}
.artc:hover,.artc:focus-visible{border-color:var(--cyan);background:color-mix(in srgb,var(--cyan) 5%,var(--panel))}
.artc .r1{display:flex;align-items:center;gap:var(--sp-2);font-size:var(--fs-min);color:var(--ink-3);white-space:nowrap}
.artc .r1 .d{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink-2)}
.artc .r1 .rm{margin-left:auto}
.artc .tt{font-size:var(--fs-h3);font-weight:600;line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artc .st{font-size:var(--fs-sm);color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.artc .sm{font-size:var(--fs-sm);color:var(--ink-3);line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:3.2em}
.arttags{display:flex;gap:6px;flex-wrap:nowrap;overflow:hidden;min-width:0}
.arttags span{flex:none;font-size:var(--fs-min);color:var(--ink-2);background:var(--panel-3);border:1px solid var(--line);border-radius:999px;padding:1px 8px;white-space:nowrap}
.artbadge{display:inline-flex;align-items:center;flex:none;font-size:var(--fs-min);font-weight:600;padding:1px 8px;border-radius:999px;border:1px solid currentColor;white-space:nowrap}
.artbadge.c-amber{color:var(--amber)}.artbadge.c-cyan{color:var(--cyan)}.artbadge.c-violet{color:var(--violet)}
.artempty{grid-column:1/-1;padding:28px 12px;text-align:center;color:var(--ink-2);font-size:var(--fs-body)}
.artempty button{margin-left:8px}
.artfoot{margin:var(--sp-3) 0 0;font-size:var(--fs-min);color:var(--ink-3)}
/* ---- 單篇 ---- */
.artpost{max-width:820px;margin:0 auto}
.artcrumb{display:flex;align-items:center;gap:6px;font-size:var(--fs-sm);color:var(--ink-3);margin-bottom:var(--sp-3);white-space:nowrap;overflow:hidden}
.artcrumb a{color:var(--cyan);text-decoration:none}
.artcrumb a:hover{text-decoration:underline}
.artcrumb .cur{color:var(--ink-2);overflow:hidden;text-overflow:ellipsis}
.artpost h2.artttl{margin:var(--sp-2) 0 6px;font-size:24px;line-height:1.4;font-weight:700}
.artpost .artsub{margin:0 0 var(--sp-3);font-size:var(--fs-h3);color:var(--ink-2);line-height:1.6}
.artmeta{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2) var(--sp-3);font-size:var(--fs-sm);color:var(--ink-2)}
.artmeta .mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.artpost .arttags{flex-wrap:wrap;margin:var(--sp-3) 0}
.artlead{margin:var(--sp-3) 0;padding:var(--sp-3) var(--sp-4);border-left:3px solid var(--cyan);background:var(--panel-3);border-radius:0 var(--r-sm,8px) var(--r-sm,8px) 0;
  font-size:15px;line-height:1.8;color:var(--ink)}
.artbody{font-size:15.5px;line-height:1.85;color:var(--ink)}
.artbody h4{margin:var(--sp-5) 0 var(--sp-2);font-size:18px;line-height:1.4;font-weight:700;display:flex;align-items:center;gap:var(--sp-2)}
.artbody h4::before{content:"";flex:none;width:4px;height:16px;border-radius:2px;background:var(--cyan)}
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
.artmore .artc{padding:var(--sp-2) var(--sp-3)}
.artmore .artc .tt{font-size:var(--fs-body)}
.artdisc{margin:var(--sp-4) 0 0;font-size:var(--fs-min);color:var(--ink-3);line-height:1.6}
.arterr{padding:var(--sp-5) var(--sp-3);text-align:center;color:var(--ink-2);font-size:var(--fs-body)}
.arterr a{color:var(--cyan)}
@media (max-width:820px){.artlist{grid-template-columns:minmax(0,1fr)}}
/* 手機（≤640，只限 m4 這段寬度，桌機一行都不受影響）：一欄、內文 16px、標題 21px、篩選列兩行 */
@media (max-width:640px){
  #artCats>button{padding-left:4px;padding-right:4px}
  .artflt input[type=search]{flex:1 1 100%}
  .artflt label{flex:1 1 calc(50% - 8px);min-width:0}
  .artflt input[type=date]{width:100%;flex:1 1 0;min-width:0}
  .artflt #artClr{flex:none}
  .artflt .cnt{margin-left:0}
  .artc{padding:var(--sp-3)}
  .artc .sm{display:none}   /* 手機只留重點（準則 3）：摘要點進去才看，卡片留類別、日期、標題、副標、標籤 */
  .artpost h2.artttl{font-size:21px}
  .artbody{font-size:16px;line-height:1.85}
  .artlead{font-size:15px}
  .artbody h4{font-size:17px}
  .artstk .g{grid-template-columns:minmax(0,1fr)}
}
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
    document.head.appendChild(s);
  }

  /* ------------------------------------------------------------------ 資料 */
  const fetchJson = (url) => fetch(url, { cache: 'no-cache' }).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); });
  function loadIndex() {
    if (S.idx) return Promise.resolve(S.idx);
    if (!S.idxP) {
      S.idxP = fetchJson('articles/index.json').then((j) => {
        const list = (j && Array.isArray(j.articles) ? j.articles : [])
          .filter((a) => a && okId(a.id) && CATS[a.cat] && okDate(a.date) && (!a.status || a.status === 'published'));
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
  const badge = (cat) => { const C = CATS[cat] || { t: cat, c: 'cyan' }; return `<span class="artbadge c-${C.c}">${esc(C.t)}</span>`; };
  const tagsHTML = (tags) => (Array.isArray(tags) && tags.length ? `<div class="arttags">${tags.slice(0, 8).map((t) => `<span>${esc(t)}</span>`).join('')}</div>` : '');
  const cardHTML = (a) => `<a class="artc" href="#article/${encodeURIComponent(a.id)}" data-id="${esc(a.id)}" data-cat="${esc(a.cat)}" data-date="${esc(a.date)}" title="${esc(a.title)}">
    <div class="r1">${badge(a.cat)}<span class="d">${esc(a.date)}</span><span class="rm">閱讀約 ${esc(Number(a.reading_min) || 1)} 分鐘</span></div>
    <div class="tt">${esc(a.title)}</div>${a.subtitle ? `<div class="st">${esc(a.subtitle)}</div>` : ''}
    ${a.summary ? `<div class="sm">${esc(a.summary)}</div>` : ''}${tagsHTML(a.tags)}</a>`;
  const DISC = 'ⓘ 本站文章為公開資訊與產業知識的整理，不構成任何投資建議；內容以資料來源發布時點為準，投資前請自行查證並評估風險。';

  /* ------------------------------------------------------------------ 列表頁 */
  function filtered(cat) {
    const q = S.q.trim().toLowerCase();
    return (S.idx ? S.idx.list : []).filter((a) => (cat === 'all' || a.cat === cat)
      && (!q || String(a.title).toLowerCase().includes(q))
      && (!S.from || a.date >= S.from) && (!S.to || a.date <= S.to));
  }
  function skeletonList(root) {
    root.innerHTML = `
<div class="card artcard" id="artCard">
  <div class="row spread"><h3>精選文章：消息・介紹・知識 <small id="artUpd"></small></h3></div>
  <div class="nbsw" id="artCats" role="tablist" aria-label="文章分類">
    <button type="button" role="tab" data-cat="all">全部 <em></em></button>${CAT_KEYS.map((k) => `<button type="button" role="tab" data-cat="${k}">${CATS[k].t} <em></em></button>`).join('')}
  </div>
  <div class="nbbody">
    <div class="artflt">
      <input type="search" id="artQ" placeholder="搜尋標題關鍵字" aria-label="搜尋標題關鍵字" autocomplete="off">
      <label>從 <input type="date" id="artFrom" aria-label="開始日期"></label>
      <label>到 <input type="date" id="artTo" aria-label="結束日期"></label>
      <button type="button" class="btn small" id="artClr">清除篩選</button>
      <span class="cnt" id="artCount" aria-live="polite"></span>
    </div>
    <div class="artlist" id="artList"></div>
  </div>
  <p class="artfoot">${esc(DISC)}</p>
</div>`;
    const q = $('#artQ', root), f = $('#artFrom', root), t = $('#artTo', root);
    q.addEventListener('input', () => { S.q = q.value; paintList(); });
    f.addEventListener('change', () => { S.from = okDate(f.value) ? f.value : ''; paintList(); });
    t.addEventListener('change', () => { S.to = okDate(t.value) ? t.value : ''; paintList(); });
    $('#artClr', root).onclick = () => { S.q = ''; S.from = ''; S.to = ''; paintList(); };
    $$('#artCats>button', root).forEach((b) => {
      b.onclick = () => { const h = b.dataset.cat === 'all' ? '#articles' : '#articles/' + b.dataset.cat; if (location.hash !== h) location.hash = h; };
    });
  }
  function paintList() {
    const root = document.getElementById('v-articles'); if (!root || !$('#artList', root)) return;
    const q = $('#artQ', root), f = $('#artFrom', root), t = $('#artTo', root);
    if (q.value !== S.q) q.value = S.q;
    if (f.value !== S.from) f.value = S.from;
    if (t.value !== S.to) t.value = S.to;
    // 改過、跟預設不同的篩選＝外框換色（style_guide 八：狀態用顏色不用文字）
    q.classList.toggle('chg', !!S.q.trim()); f.classList.toggle('chg', !!S.from); t.classList.toggle('chg', !!S.to);
    f.max = S.to || ''; t.min = S.from || '';
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
    $('#artUpd', root).textContent = S.idx.updated ? '更新 ' + S.idx.updated : '';
    const list = filtered(S.cat);
    cnt.innerHTML = `共 <b>${list.length}</b> 篇`;
    cnt.dataset.n = String(list.length);
    const dirty = !!(S.q.trim() || S.from || S.to);
    box.innerHTML = list.length ? list.map(cardHTML).join('')
      : `<div class="artempty" id="artEmpty">${dirty ? '沒有符合條件的文章，換個關鍵字或放寬日期試試。' : '這個分類還沒有文章。'}${dirty ? '<button type="button" class="btn small" data-clr>清除篩選</button>' : ''}</div>`;
    const c2 = $('[data-clr]', box); if (c2) c2.onclick = () => { S.q = ''; S.from = ''; S.to = ''; paintList(); };
  }
  async function showList(cat) {
    css();
    const root = document.getElementById('v-articles'); if (!root) return;
    S.cat = CATS[cat] ? cat : 'all';
    S.cur = '';
    markSub(S.cat);
    if (!$('#artList', root)) skeletonList(root);
    paintList();
    await loadIndex();
    if (location.hash.replace(/^#/, '').split('/')[0] !== 'articles') return;   // 讀清單的時候使用者已經換頁
    paintList();
  }

  /* ------------------------------------------------------------------ 單篇頁 */
  function blockHTML(b) {
    if (!b || typeof b !== 'object') return '';
    switch (b.t) {
      case 'h': return `<h4>${esc(b.text)}</h4>`;
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
      default: return '';
    }
  }
  function postHTML(d, meta) {
    const cat = CATS[d.cat] ? d.cat : (meta && meta.cat) || '';
    const C = CATS[cat];
    const links = (Array.isArray(d.site_links) ? d.site_links : []).filter((l) => l && okHash(l.hash) && l.label);
    const srcs = (Array.isArray(d.sources) ? d.sources : []).filter((s) => s && (s.title || s.url));
    const more = S.idx ? S.idx.list.filter((a) => a.cat === cat && a.id !== d.id).slice(0, 3) : [];
    const upd = okDate(d.updated) && d.updated !== d.date ? `<span>更新 <span class="mono">${esc(d.updated)}</span></span>` : '';
    return `
<article class="card artpost" id="artPost" data-id="${esc(d.id)}">
  <nav class="artcrumb" aria-label="麵包屑"><a href="#articles">精選文章</a><span aria-hidden="true">›</span>${C ? `<a href="#articles/${cat}">${esc(C.t)}</a><span aria-hidden="true">›</span>` : ''}<span class="cur">${esc(d.title)}</span></nav>
  <div class="artmeta">${cat ? badge(cat) : ''}<span class="mono">${esc(d.date || '')}</span>${upd}<span>閱讀約 ${esc(Number(d.reading_min) || 1)} 分鐘</span>${d.confidence ? `<span title="資料信心：依來源數量與一致性自評">資料信心 ${esc(d.confidence)}</span>` : ''}</div>
  <h2 class="artttl">${esc(d.title)}</h2>
  ${d.subtitle ? `<p class="artsub">${esc(d.subtitle)}</p>` : ''}
  ${tagsHTML(d.tags)}
  ${d.summary ? `<div class="artlead">${esc(d.summary)}</div>` : ''}
  <div class="artbody" id="artBody">${(Array.isArray(d.blocks) ? d.blocks : []).map(blockHTML).join('')}</div>
  ${links.length ? `<section class="artsec" id="artLinks"><h4>站內相關頁面</h4><div class="artlinks">${links.map((l) => `<a href="${esc(l.hash)}">${esc(l.label)}</a>`).join('')}</div></section>` : ''}
  ${srcs.length ? `<section class="artsec" id="artSrc"><h4>資料來源</h4><ol class="artsrc">${srcs.map((s) => {
    const t = esc(s.title || s.url), info = [s.publisher, s.date].filter(Boolean).map(esc).join('，');
    return `<li>${okUrl(s.url) ? `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${t}</a>` : t}${info ? `（${info}）` : ''}</li>`; }).join('')}</ol></section>` : ''}
  ${more.length ? `<section class="artsec" id="artMore"><h4>同類別其他文章</h4><div class="artmore">${more.map(cardHTML).join('')}</div></section>` : ''}
  <p class="artdisc">${esc(DISC)}</p>
</article>`;
  }
  async function showPost(id) {
    css();
    const root = document.getElementById('v-articles'); if (!root) return;
    const changed = S.cur !== id; S.cur = id;
    markSub(catOf(id));
    if (changed) { root.innerHTML = '<div class="card artpost"><div class="arterr">載入中…</div></div>'; window.scrollTo({ top: 0 }); }
    const [idx, d] = await Promise.all([loadIndex(), loadPost(id)]);
    if (S.cur !== id || location.hash.replace(/^#/, '').split('/')[0] !== 'article') return;
    const meta = idx ? idx.list.find((a) => a.id === id) : null;
    if (!d || !d.title) {
      root.innerHTML = `<div class="card artpost" id="artPost"><nav class="artcrumb"><a href="#articles">精選文章</a><span aria-hidden="true">›</span><span class="cur">找不到文章</span></nav>
        <div class="arterr" id="artErr">這篇文章暫時讀不到（可能還在整理或已下架）。<br><a href="#articles">回精選文章清單</a></div></div>`;
      return;
    }
    markSub(CATS[d.cat] ? d.cat : meta && meta.cat);
    root.innerHTML = postHTML(d, meta);
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
    const h = (location.hash || '').replace(/^#/, '').split('/').map((x) => { try { return decodeURIComponent(x); } catch (e) { return x; } });
    const v = document.getElementById('v-articles');
    if ((h[0] === 'articles' || h[0] === 'article') && v && !v.firstChild) show(h[0], h.slice(1));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 0)); else setTimeout(boot, 0);
})();
