/* ============================================================================
   管理區 #admin（只有管理者看得到）—— 2026-10-05 admin-v2 改版（Andy A～E）
   三個子分頁，用網址分（上一頁回得來、可以直接貼網址），頁內頂部一排 tab 切換：
     #admin/perm      會員權限：訪客｜註冊會員｜付費會員（付費底下可有多個範本，例如 399／799）
                      每一層：① 開放功能表（features.js 的開關＋族群觀測）② Mail 人員名單（訪客沒有名單）
     #admin/members   會員管理：新增會員（email＋層級／範本＋到期日）、所有人員狀況表（可搜尋、排序）、點一列逐項微調
     #admin/traffic   流量觀測：全站總覽（各頁瀏覽、「?」總數、個股被觀看 Top N、熱門個股最常用的功能）＋分頁明細
     #admin           ＝ 流量觀測（舊網址：線上人數徽章、帳號選單都還指著它）
   · 這支只在「已登入的管理者打開 #admin」時才由 account.js 載入，一般訪客完全不下載它。
   · 真正的權限檢查在 Worker（ADMIN_EMAILS）：就算有人把這支檔案叫出來，沒有管理者權杖一樣拿不到任何資料。
   · 圖用純 HTML 長條／小 SVG（不用 ECharts）：資料只有幾十列，HTML 在任何寬度都不會被裁。
   每張卡片標題就是它回答的問題，下面一行寫「所以我該怎麼用」。
   圖表選型（Andy 要評估長條／圓餅／散佈，判斷寫在流量觀測頁的「？ 圖表怎麼選」與 docs/account_analytics.md）：
     · 預設橫向排序長條：類別多、要比大小 —— 人眼比「長度」最準，排序後第一名、最後一名一眼就知道。
     · 圓餅／甜甜圈：只在「≤ 5 類、加總 = 100%」時用（登入／訪客開啟比例）。類別一多，扇形角度就比不出大小。
     · 散佈：只用在兩個數量之間的關係（個股「被觀看次數 × 平均每次觀看用了幾個功能」），其他一律不用。
   ========================================================================== */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const VIEW_NAME = { overview: '總覽', flow: '資金流向', industry: '產業地圖', heatmap: '熱力圖', market: '市場明細', season: '週期統計',
    delivery: '交付清單', stock: '個股頁', legal: '法律頁', watch: '自選清單', other: '其他' };
  const EV_NAME = { session: '開啟網站（每個分頁一次）', session_login: '登入狀態下開啟網站', login: '登入', logout: '登出',
    search: '搜尋股票', watch_add: '加入自選', watch_remove: '移出自選', watch_tab_new: '新增自選分頁', watch_panel: '打開自選清單',
    stock_tab: '切個股分頁（營收／籌碼…）', k_period: '切 K 線週期', ai_tab: '切 AI 分析面向', open_3d: '打開 3D 剖析圖', zoom: '放大圖表',
    how: '打開「?」說明', theme_toggle: '切深淺色', events_drawer: '打開今日事件', mtf: '四週期同看', indicators: '打開指標設定', draw: '畫線工具', m_seg: '手機切分段' };
  /* 細項事件的元件名（docs/account_analytics.md「細項事件」）*/
  const COMP_NAME = { view: '被觀看', play: '播放（時間軸）', quad: '象限卡（領先／改善／轉弱／落後）', filter_chain: '篩選：產業鏈', filter_group: '篩選：族群（勾選）',
    filter_group_open: '打開族群下拉', filter_top10: '只看前 10 大', filter_clear: '清除篩選', rank_bar: '右側排行長條', clock_group: '輪盤上的族群點',
    heat_tile: '熱力圖方塊', how: '「?」說明', search: '搜尋（只記有搜尋）', zoom: '放大圖表', ai_tab: '切 AI 面向', mtf: '四週期同看', indicators: '指標設定',
    draw: '畫線工具', open_3d: '3D 剖析圖', theme_toggle: '切深淺色', events_drawer: '今日事件', m_seg: '手機切分段', watch_add: '加入自選', watch_remove: '移出自選',
    watch_panel: '打開自選清單', watch_tab_new: '新增自選分頁' };
  const TAB_NAME = { overview: '總覽', basics: '基本資料', tags: '指標', revenue: '營收', profit: '獲利', dividend: '除權息', inst: '法人', margin: '資券',
    holders: '大戶／散戶', news: '公告／新聞', rev: '營收', fin: '財務', div: '除權息', big: '大戶', basic: '基本資料', tag: '指標', ai: 'AI' };
  const compName = (c) => {
    if (COMP_NAME[c]) return COMP_NAME[c];
    if (c.startsWith('tab.')) return '分頁：' + (TAB_NAME[c.slice(4)] || c.slice(4));
    if (c.startsWith('kp.')) return 'K 線週期：' + c.slice(3).toUpperCase().replace(/^(\d+)M$/, '$1 分');
    return c;
  };
  const S = { days: 30, timer: 0, v: null, A: null, page: 'flow', st: null, on: null };
  const TABS = [['perm', '會員權限', 'admTabPerm'], ['members', '會員管理', 'admTabMembers'], ['traffic', '流量觀測', 'admTabTraffic']];
  const tabOf = () => { const m = /^#admin\/(perm|members|traffic)\b/.exec(location.hash || ''); return m ? m[1] : 'traffic'; };

  function css() {
    if (document.getElementById('admCss')) return;
    const s = document.createElement('style'); s.id = 'admCss';
    s.textContent = `
#v-admin .admgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--gap-card,14px);margin-top:14px}
#v-admin .admgrid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--gap-card,14px);margin-top:14px}
#v-admin .card{min-width:0}
#v-admin h2{margin:0;font-size:18px}#v-admin h3{margin:0 0 2px;font-size:16px}
#v-admin .use{font-size:13px;color:var(--ink-2);margin:0 0 10px;line-height:1.55}
#v-admin .admtop{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
#v-admin .admtop .sp{flex:1}
#v-admin .admtop select,#v-admin .admtop button{height:32px;font-size:13.5px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;cursor:pointer}
#v-admin .kpis{display:flex;gap:18px;flex-wrap:wrap;margin:4px 0 10px}
#v-admin .kpis div{font-size:13px;color:var(--ink-2)}#v-admin .kpis b{display:block;font-size:26px;color:var(--ink);font-family:var(--mono)}
#v-admin .bars{display:grid;grid-template-columns:minmax(0,11em) minmax(0,1fr) auto;gap:6px 10px;align-items:center;font-size:13.5px}
#v-admin .bars .bl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-admin .bars .bt{height:14px;background:var(--panel-3);border-radius:4px;overflow:hidden}
#v-admin .bars .bt i{display:block;height:100%;background:var(--cyan);border-radius:4px}
#v-admin .bars .bn{font-family:var(--mono);text-align:right;min-width:3em}
#v-admin .bars button.bl{background:none;border:0;color:var(--ink);text-align:left;font:inherit;padding:0;cursor:pointer;text-decoration:underline dotted var(--ink-3,#7a879c)}
#v-admin .days{display:flex;align-items:flex-end;gap:2px;height:120px;border-bottom:1px solid var(--line);padding-top:6px}
#v-admin .days i{flex:1;min-width:2px;background:var(--violet);border-radius:3px 3px 0 0}
#v-admin .dayx{display:flex;justify-content:space-between;font-size:12px;color:var(--ink-2);margin-top:4px}
#v-admin table{width:100%;border-collapse:collapse;font-size:13.5px}
#v-admin th,#v-admin td{text-align:left;padding:6px 6px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}
#v-admin th{color:var(--ink-2);font-weight:500;font-size:12.5px}
#v-admin .empty{color:var(--ink-2);font-size:13px;padding:10px 0}
#v-admin label.tg{display:flex;align-items:center;gap:8px;font-size:14px;cursor:pointer}
#v-admin label.tg input{width:18px;height:18px}
#v-admin .err{color:#ff6b7a}
#v-admin .admnav{display:flex;gap:6px;flex-wrap:wrap}
#v-admin .admnav a{display:inline-flex;align-items:center;height:34px;padding:0 14px;border-radius:8px;border:1px solid var(--line-2);color:var(--ink-2);text-decoration:none;font-size:14px}
#v-admin .admnav a.on{background:var(--cyan);border-color:var(--cyan);color:var(--ontop,#04121a);font-weight:700}
#v-admin .tier{display:flex;gap:0;border:1px solid var(--line-2);border-radius:10px;overflow:hidden;width:max-content;max-width:100%;margin-top:4px}
#v-admin .tier button{height:36px;padding:0 18px;font-size:14px;background:var(--panel-2);color:var(--ink-2);border:0;border-right:1px solid var(--line-2);cursor:pointer}
#v-admin .tier button:last-child{border-right:0}
#v-admin .tier button.on{background:var(--cyan);color:var(--ontop,#04121a);font-weight:700}
#v-admin .tier button small{font-size:12px;opacity:.85;margin-left:4px}
#v-admin .plchips{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:10px}
#v-admin .plchips button{height:32px;padding:0 12px;border-radius:16px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);font-size:13.5px;cursor:pointer}
#v-admin .plchips button.on{border-color:var(--cyan);box-shadow:inset 0 0 0 1px var(--cyan);font-weight:700}
#v-admin .plchips button small{color:var(--ink-2);font-size:12px;margin-left:4px}
#v-admin .pmbar{display:flex;align-items:center;gap:8px 10px;flex-wrap:wrap;margin-top:8px}
#v-admin .pmbar input,#v-admin .pmbar select{height:34px;font-size:14px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;min-width:0}
#v-admin .pmbar input[type=email]{flex:1 1 240px;max-width:360px}
#v-admin .pmbar label{font-size:13.5px;color:var(--ink-2);display:inline-flex;align-items:center;gap:6px}
#v-admin .pmbar button{height:34px;font-size:13.5px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 12px;cursor:pointer}
#v-admin .pmbar button.pri{background:var(--cyan);border-color:var(--cyan);color:var(--ontop,#04121a);font-weight:700}
#v-admin .pmbar button.danger{color:#ff6b7a}
#v-admin .pmbar button:disabled,#v-admin .pmcat button:disabled{opacity:.45;cursor:not-allowed}
#v-admin .pmwho{font-size:13.5px;color:var(--ink-2);margin-top:8px;min-height:1.4em}
#v-admin .pmwho b{color:var(--ink)}
#v-admin .pmstat{font-size:13px;margin-top:6px;min-height:1.3em;color:var(--ink-2)}
#v-admin .pmstat.ok{color:#35d07f}#v-admin .pmstat.bad{color:#ff6b7a}
#v-admin .pmcats{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:var(--gap-card,14px);margin-top:14px}
#v-admin .pmcats.off{opacity:.5;pointer-events:none}
#v-admin .pmcat[data-cat=grp]{grid-column:1/-1}
#v-admin .pmcat .grpgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,230px),1fr));column-gap:14px}
#v-admin .pmcat .grpch{grid-column:1/-1;font-size:13px;color:var(--ink-2);margin:10px 0 2px;font-weight:600}
#v-admin .pmcat .pmrow.sm{padding:5px 0;gap:8px}#v-admin .pmcat .pmrow.sm .pmtx b{font-size:13.5px;font-weight:500}
#v-admin .pmcathd{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px}
#v-admin .pmcathd h3{margin:0;flex:1;min-width:0}
#v-admin .pmcathd h3 small{font-size:12.5px;color:var(--ink-2);font-weight:400;margin-left:6px}
#v-admin .pmcathd button{height:30px;font-size:13px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;cursor:pointer}
#v-admin .pmrow{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--line)}
#v-admin .pmrow .pmtx b{display:block;font-size:14px;font-weight:600}
#v-admin .pmrow .pmtx small{display:block;font-size:12.5px;color:var(--ink-2);line-height:1.45}
#v-admin .pmrow .pmside{display:flex;align-items:center;gap:6px}
#v-admin .pmtag{font-size:12px;padding:1px 6px;border-radius:6px;background:color-mix(in srgb,var(--amber,#f5b942) 22%,transparent);color:var(--ink);white-space:nowrap}
#v-admin .pmrev{font-size:12px;background:none;border:0;color:var(--cyan);cursor:pointer;padding:2px 4px}
#v-admin label.psw{position:relative;display:inline-block;width:44px;height:24px;flex:none}
#v-admin label.psw input{position:absolute;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:pointer;z-index:1}
#v-admin label.psw span{position:absolute;inset:0;border-radius:12px;background:var(--panel-3);border:1px solid var(--line-2);transition:background .15s}
#v-admin label.psw span::before{content:'';position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:50%;background:var(--ink-2);transition:transform .15s,background .15s}
#v-admin label.psw input:checked+span{background:var(--cyan);border-color:var(--cyan)}
#v-admin label.psw input:checked+span::before{transform:translateX(20px);background:#fff}
#v-admin label.psw input:focus-visible+span{outline:2px solid var(--cyan);outline-offset:2px}
#v-admin label.psw input:disabled{cursor:not-allowed}
#v-admin .pmrow select{height:30px;font-size:13.5px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 8px}
#v-admin table.pmlist{table-layout:fixed;width:100%}#v-admin .pmlist th,#v-admin .pmlist td{white-space:normal!important;overflow-wrap:anywhere}
#v-admin .pmlist th:nth-child(1){width:26%}
#v-admin .pmlist th[data-sort]{cursor:pointer;user-select:none}#v-admin .pmlist th[data-sort]:hover{color:var(--ink)}
#v-admin .pmlist th.sorted{color:var(--ink);font-weight:700}
#v-admin .pmlist td small{display:block;font-size:12px;color:var(--ink-2)}#v-admin .pmlist tr.on td{background:color-mix(in srgb,var(--cyan) 12%,transparent)}
#v-admin .pmlist td.num{font-family:var(--mono);text-align:right}#v-admin .pmlist th.num{text-align:right}
#v-admin .stt{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;white-space:nowrap}
#v-admin .stt.ok{background:color-mix(in srgb,#35d07f 20%,transparent)}#v-admin .stt.exp{background:color-mix(in srgb,#ff6b7a 22%,transparent)}#v-admin .stt.new{background:var(--panel-3)}
#v-admin .pmcnt{font-size:13px;color:var(--ink-2)}#v-admin .pmbar input[type=search]{flex:1 1 220px;max-width:360px}
#v-admin .pmtpl{align-items:flex-start}#v-admin .pmtpl small{flex:1 1 260px;font-size:12.5px;color:var(--ink-2);line-height:1.5}#v-admin .pmtpl span{font-size:13px;color:var(--ink-2)}
#v-admin .pmtag.new{background:color-mix(in srgb,var(--cyan) 22%,transparent)}#v-admin .pmrow.dirty{box-shadow:inset 3px 0 0 var(--cyan);padding-left:8px}
#v-admin .pmsave{position:sticky;bottom:12px;z-index:20;display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:14px;padding:10px 14px;border-radius:12px;
  background:var(--panel,#111a2b);border:1px solid var(--cyan);box-shadow:0 6px 24px rgba(0,0,0,.35);font-size:14px}
#v-admin .pmsave[hidden]{display:none}#v-admin .pmsave #pmDirty{flex:1 1 180px;min-width:0;overflow-wrap:anywhere}
#v-admin .pmsave button{height:34px;font-size:14px;border-radius:8px;padding:0 16px;cursor:pointer;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2)}
#v-admin .pmsave button.pri{background:var(--cyan);border-color:var(--cyan);color:var(--ontop,#04121a);font-weight:700}
#v-admin .pmlist tr[data-email]{cursor:pointer}#v-admin .pmlist tr[data-email]:hover td{background:var(--row-hover)}
#v-admin .pmwarn{font-size:13px;color:var(--ink-2);line-height:1.6;margin:0}
#v-admin .seg2{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 10px}
#v-admin .seg2 button{height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink-2);font-size:13.5px;cursor:pointer}
#v-admin .seg2 button.on{background:var(--cyan);border-color:var(--cyan);color:var(--ontop,#04121a);font-weight:700}
#v-admin .seg2 button small{font-family:var(--mono);margin-left:4px;opacity:.8}
#v-admin details.trhow{margin-top:8px;font-size:13px;color:var(--ink-2);line-height:1.65}
#v-admin details.trhow summary{cursor:pointer;color:var(--cyan);width:max-content}
#v-admin details.trhow ul{margin:6px 0 0;padding-left:1.2em}
#v-admin .secttl{display:flex;align-items:baseline;gap:10px;margin:22px 0 0}#v-admin .secttl h2{font-size:17px}#v-admin .secttl small{color:var(--ink-2);font-size:13px}
#v-admin .cdgrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:var(--gap-card,14px)}
#v-admin .donut{display:flex;align-items:center;gap:16px;flex-wrap:wrap}#v-admin .donut ul{list-style:none;margin:0;padding:0;font-size:13.5px}
#v-admin .donut li{display:flex;align-items:center;gap:6px;margin:3px 0}#v-admin .donut li i{width:12px;height:12px;border-radius:3px;display:inline-block}
#v-admin svg.sc text{font-size:12px;fill:var(--ink-2)}#v-admin svg.sc .lb{fill:var(--ink);font-size:12px}
@media (max-width:1180px){#v-admin .admgrid3{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:820px){ #v-admin .admgrid,#v-admin .admgrid3,#v-admin .cdgrid{grid-template-columns:minmax(0,1fr)} #v-admin .bars{grid-template-columns:minmax(0,8em) minmax(0,1fr) auto} #v-admin .pmsave{bottom:72px} }
@media (max-width:600px){#v-admin .pmlist .c-exp,#v-admin .pmlist .c-n,#v-admin .pmlist .c-vis,#v-admin .pmlist .c-tpl{display:none}}`;
    document.head.appendChild(s);
  }
  const ago = (ms) => { const s = Math.max(0, Math.round((Date.now() - ms) / 1000)); return s < 60 ? s + ' 秒前' : Math.round(s / 60) + ' 分前'; };
  const dstr = (ms) => { if (!ms) return '—'; const d = new Date(ms + 8 * 3600 * 1000); return d.toISOString().slice(0, 16).replace('T', ' '); };
  const dday = (ms) => (ms ? dstr(ms).slice(0, 10) : '—');
  const nf = (n) => Number(n || 0).toLocaleString('en-US');

  function bars(list, names, total, opt) {
    if (!list.length) return '<div class="empty">這段期間還沒有紀錄。</div>';
    const max = Math.max(...list.map((x) => x[1]), 1), o = opt || {};
    const nm = (k) => typeof names === 'function' ? names(k) : (names[k] || k);
    return `<div class="bars"${o.id ? ` id="${o.id}"` : ''}>` + list.map(([k, n]) => (o.click ? `<button type="button" class="bl" data-k="${esc(k)}" title="${esc(nm(k))}">${esc(nm(k))}</button>` : `<span class="bl" title="${esc(k)}">${esc(nm(k))}</span>`)
      + `<span class="bt"><i style="width:${(n / max * 100).toFixed(1)}%"></i></span>`
      + `<span class="bn">${nf(n)}${total ? `<small style="color:var(--ink-2)"> ${(n / total * 100).toFixed(0)}%</small>` : ''}</span>`).join('') + '</div>';
  }

  /* ---- 頂部：標題＋三個子分頁 tab（有沒存的權限草稿時，換分頁先問一次）*/
  function head(v, A, extra) {
    const u = A.user() || {}, cur = tabOf();
    return `<div class="card" style="margin-top:16px"><div class="admtop"><h2>管理區</h2><small style="color:var(--ink-2)">${esc(u.email || '')}</small>
        <nav class="admnav" id="admTabs" aria-label="管理區分頁">${TABS.map(([k, n, id]) => `<a href="#admin/${k}" id="${id}" data-tab="${k}" class="${cur === k ? 'on' : ''}"${cur === k ? ' aria-current="page"' : ''}>${n}</a>`).join('')}</nav>
        <span class="sp"></span>${extra || ''}</div>`;
  }
  function wireHead(v) {
    const nav = v.querySelector('#admTabs');
    if (nav) nav.onclick = (e) => { const a = e.target.closest('a[data-tab]'); if (a && !guard()) e.preventDefault(); };
  }
  function render(v, A) {
    css();
    S.v = v; S.A = A;
    const t = tabOf();
    if (t !== 'traffic') clearInterval(S.timer);
    if (t === 'perm' || t === 'members') { renderPerm(v, A, t); return; }
    renderTraffic(v, A);
  }

  /* ==========================================================================
     #admin/traffic 流量觀測
     ========================================================================== */
  function renderTraffic(v, A) {
    v.innerHTML = head(v, A, `<label style="font-size:13.5px;color:var(--ink-2)">期間 <select id="admDaysSel">${[7, 30, 90, 365].map((d) => `<option value="${d}" ${d === S.days ? 'selected' : ''}>近 ${d} 天</option>`).join('')}</select></label>
        <button type="button" id="admRefresh">重新整理</button>`)
      + `<p class="use" style="margin:8px 0 0">使用統計只記「每天每一項的次數」（不記是誰、不存 IP），保留 13 個月；細項只存族群名、股票代號、元件名，不存任何人打的字。線上狀態離線即刪。</p>
        <details class="trhow" id="trHow"><summary>？ 圖表怎麼選（長條／圓餅／散佈）</summary><ul>
          <li><b>預設用橫向排序長條</b>：這一頁的問題幾乎都是「哪個最多」—— 類別多、要比大小時，人眼比長度最準，排序之後第一名、最後一名一眼就知道。</li>
          <li><b>圓餅（甜甜圈）只在「≤ 5 類、加總 = 100%」時用</b>：例如「開網站的人有多少是登入的」。類別一多，扇形角度就比不出誰大。</li>
          <li><b>散佈圖只用在兩個數量之間的關係</b>：例如個股「被看幾次 × 每次看用了幾個功能」—— 右上角＝又多人看、看的人又用得深。其他問題不用散佈。</li>
          <li>所以我該怎麼用：先看上面「全站總覽」找出最常被用的頁與股票，再到下面「分頁明細」看那一頁裡哪個按鈕／哪個族群被點最多 —— 常用的放更顯眼，幾乎沒人按的考慮收起來。</li></ul></details></div>
      <div id="admBody"><div class="card" style="margin-top:14px"><p class="use">載入中…</p></div></div>`;
    wireHead(v);
    v.querySelector('#admDaysSel').onchange = (e) => { S.days = +e.target.value; paint(); };
    v.querySelector('#admRefresh').onclick = () => paint();
    paint();
    clearInterval(S.timer);
    S.timer = setInterval(() => { if (tabOf() === 'traffic' && (location.hash || '').startsWith('#admin') && document.visibilityState !== 'hidden') paint(); else if (!(location.hash || '').startsWith('#admin')) clearInterval(S.timer); }, 30000);
  }

  async function paint() {
    const v = S.v, A = S.A; if (!v || !A) return;
    const [st, on] = await Promise.all([A.call('/v1/admin/stats', { days: S.days }), A.call('/v1/admin/online', {})]);
    if (!(location.hash || '').startsWith('#admin') || tabOf() !== 'traffic' || !v.querySelector('#admBody')) return;
    if (!st || st._s !== 200 || !on || on._s !== 200) {
      v.querySelector('#admBody').innerHTML = `<div class="card" style="margin-top:14px"><p class="err">讀不到報表（${st ? st._s : '連不到伺服器'}）。只有管理者帳號看得到；若你是管理者，確認 Worker 的 ADMIN_EMAILS 有你的 email（docs/login_setup.md 第 6 步）。</p></div>`;
      return;
    }
    S.st = st; S.on = on;
    const pv = {}, ev = {}, perDay = {};
    st.rows.forEach((r) => {
      const [kind, name] = r.k.split(':');
      if (kind === 'pv') { pv[name] = (pv[name] || 0) + r.n; perDay[r.day] = (perDay[r.day] || 0) + r.n; } else ev[name] = (ev[name] || 0) + r.n;
    });
    const e2 = Array.isArray(st.e2) ? st.e2 : [];
    const pvList = Object.entries(pv).sort((a, b) => b[1] - a[1]);
    const evList = Object.entries(ev).filter(([k]) => !['session', 'session_login', 'login', 'logout'].includes(k)).sort((a, b) => b[1] - a[1]);
    const pvTotal = pvList.reduce((s, x) => s + x[1], 0);
    const days = [];
    for (let t = Date.parse(st.from + 'T00:00:00Z'); t <= Date.parse(st.to + 'T00:00:00Z'); t += 86400000) days.push(new Date(t).toISOString().slice(0, 10));
    const dmax = Math.max(1, ...days.map((d) => perDay[d] || 0));
    const sessions = ev.session || 0, loginSess = Math.min(ev.session_login || 0, sessions);
    /* 「?」總數：細項有記就用細項（含是哪一張卡），沒有（Worker 還是舊版）退回舊的 ev:how */
    const howE2 = e2.filter((r) => r.comp === 'how').reduce((s, r) => s + r.n, 0);
    const howN = howE2 || ev.how || 0;
    // 個股：被觀看 Top 10、各自最常用的功能
    const views = e2.filter((r) => r.page === 'stock' && r.comp === 'view' && r.detail).sort((a, b) => b.n - a.n);
    const useBy = {};
    e2.filter((r) => r.page === 'stock' && r.comp !== 'view' && r.detail).forEach((r) => { (useBy[r.detail] = useBy[r.detail] || []).push(r); });
    const topV = views.slice(0, 10);
    const featRows = topV.map((r) => { const u = (useBy[r.detail] || []).sort((a, b) => b.n - a.n); const tot = u.reduce((s, x) => s + x.n, 0); return { code: r.detail, views: r.n, top: u.slice(0, 3), tot }; });
    const scat = views.slice(0, 30).map((r) => ({ code: r.detail, x: r.n, y: ((useBy[r.detail] || []).reduce((s, x) => s + x.n, 0)) / Math.max(1, r.n) }));
    const pages = [...new Set(e2.map((r) => r.page))];
    if (!pages.includes(S.page)) S.page = pages.includes('flow') ? 'flow' : (pages[0] || 'flow');
    v.querySelector('#admBody').innerHTML = `
      <div class="secttl"><h2>全站總覽</h2><small>${esc(st.from)} ～ ${esc(st.to)}（台北）</small></div>
      <div class="card" id="trKpi" style="margin-top:10px"><div class="kpis"><div><b>${nf(pvTotal)}</b>頁面瀏覽</div><div><b>${nf(sessions)}</b>開啟網站</div>
        <div><b>${sessions ? Math.round(loginSess / sessions * 100) : 0}%</b>登入狀態開啟</div><div><b id="trHowN">${nf(howN)}</b>全站「?」點擊</div><div><b>${nf(views.reduce((s, r) => s + r.n, 0))}</b>個股被觀看</div></div></div>
      <div class="admgrid">
        <div class="card" id="admPv"><h3>哪一頁最多人看？</h3><p class="use">${S.days} 天內每一頁被打開的次數與佔比（橫向長條，已排序）。排在後面的頁面，要嘛入口太深、要嘛內容不被需要 —— 改版優先順序從這裡排。點一頁看它的明細。</p>${bars(pvList, VIEW_NAME, pvTotal, { click: true, id: 'trPvBars' })}</div>
        <div class="card" id="admDays"><h3>每天有多少瀏覽？</h3><p class="use">每天的頁面瀏覽總次數。突然掉下來先查網站是不是壞了，突然衝高看當天發生了什麼。</p>
          <div class="days" id="admDayBars">${days.map((d) => `<i style="height:${((perDay[d] || 0) / dmax * 100).toFixed(1)}%" title="${d}：${perDay[d] || 0} 次"></i>`).join('')}</div>
          <div class="dayx"><span>${esc(st.from)}</span><span>${esc(st.to)}</span></div></div>
        <div class="card" id="trStockTop"><h3>哪幾檔個股最多人看？</h3><p class="use">個股頁被打開的次數（換一檔算一次），前 10 名。這些股票值得優先把資料補齊、放進首頁的推薦。</p>
          ${bars(topV.map((r) => [r.detail, r.n]), (k) => k, 0, { id: 'trStockBars' })}</div>
        <div class="card" id="trStockFeat"><h3>熱門個股的人都在用什麼功能？</h3><p class="use">上面那 10 檔，各自被用最多的三個功能（次數）。同一個功能在每一檔都排第一 → 它是個股頁的主力，應該放最前面。</p>
          ${featRows.length ? `<table><thead><tr><th>代號</th><th>觀看</th><th>最常用的功能</th></tr></thead><tbody>${featRows.map((r) => `<tr><td>${esc(r.code)}</td><td>${nf(r.views)}</td><td>${r.top.length ? r.top.map((x) => `${esc(compName(x.comp))} <small style="color:var(--ink-2)">${nf(x.n)}</small>`).join('・') : '<span style="color:var(--ink-2)">只看沒點功能</span>'}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">這段期間還沒有個股觀看紀錄。</div>'}</div>
        <div class="card" id="trScatter"><h3>哪些股票「又多人看、看的人又用得深」？</h3><p class="use">散佈圖：橫軸＝被觀看次數、縱軸＝平均每次觀看用了幾次功能。右上角＝熱門而且被深度使用；右下角＝很多人看但只看一眼（可能缺資料或缺吸引人的圖）。</p>${scatter(scat)}</div>
        <div class="card" id="trDonut"><h3>開網站的人有多少是登入的？</h3><p class="use">只有兩類、加總 100%，所以用甜甜圈。登入比例低 → 登入的好處說得不夠清楚，或登入鈕太不顯眼。</p>${donut([['登入狀態', loginSess, 'var(--cyan)'], ['訪客', Math.max(0, sessions - loginSess), 'var(--violet)']])}</div>
        <div class="card" id="admOnline"><h3>現在誰在線上？</h3><p class="use">最近 2 分半有動作的分頁。登入者列出名稱與所在頁面；訪客只算人數。每 30 秒自動更新。</p>
          <div class="kpis"><div><b id="admOnN">${on.total}</b>在線（分頁數）</div><div><b>${on.users.length}</b>登入者</div><div><b>${on.guests}</b>訪客</div></div>
          ${on.users.length ? `<table><thead><tr><th>名稱</th><th>email</th><th>在看</th><th>最後動作</th></tr></thead><tbody>${on.users.map((u) => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${esc(VIEW_NAME[u.route] || u.route)}</td><td>${ago(u.seen)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">目前沒有登入者在線上。</div>'}
          <label class="tg" style="margin-top:12px"><input type="checkbox" id="admPub" ${on.public_online ? 'checked' : ''}>一般訪客看得到「目前 N 人在線」（只有總數，看不到名字）</label></div>
        <div class="card" id="admEv"><h3>哪個功能最常被用？（全站）</h3><p class="use">${S.days} 天內每個功能被按的總次數（不分頁）。分頁裡的細節看下面「分頁明細」。</p>${bars(evList, EV_NAME, 0)}</div>
        <div class="card" id="admUsers" style="grid-column:1 / -1"><h3>最近有哪些會員來過？</h3><p class="use">共 ${st.users.total} 位；依最後使用時間排序（最多列 50 位）。要新增、設到期日、看造訪次數，到「會員管理」。</p>
          ${st.users.recent.length ? `<table><thead><tr><th>名稱</th><th>email</th><th>加入</th><th>最後使用（台北）</th></tr></thead><tbody>${st.users.recent.map((u) => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${dstr(u.created)}</td><td>${dstr(u.seen)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">還沒有會員。</div>'}</div>
      </div>
      <div class="secttl" id="trDetailTtl"><h2>分頁明細</h2><small>選一頁，看那一頁的每個元件被用幾次、細項（哪個族群、哪一檔）是誰</small></div>
      <div class="card" id="trDetail" style="margin-top:10px">
        <div class="seg2" id="trPageSeg" role="tablist">${(pages.length ? pages : ['flow']).sort((a, b) => (pv[b] || 0) - (pv[a] || 0)).map((p) => `<button type="button" data-p="${esc(p)}" class="${p === S.page ? 'on' : ''}">${esc(VIEW_NAME[p] || p)}<small>${nf(e2.filter((r) => r.page === p).reduce((s, r) => s + r.n, 0))}</small></button>`).join('')}</div>
        <div id="trPageBody"></div></div>`;
    const pub = v.querySelector('#admPub');
    pub.onchange = async () => { const r = await A.call('/v1/admin/settings', { public_online: pub.checked }); if (!r || r._s !== 200) pub.checked = !pub.checked; };
    v.querySelector('#trPageSeg').onclick = (e) => { const b = e.target.closest('button[data-p]'); if (!b) return; S.page = b.dataset.p; v.querySelectorAll('#trPageSeg button').forEach((x) => x.classList.toggle('on', x === b)); paintPage(); };
    v.querySelector('#trPvBars') && (v.querySelector('#trPvBars').onclick = (e) => {
      const b = e.target.closest('button[data-k]'); if (!b) return;
      S.page = b.dataset.k; const seg = v.querySelector(`#trPageSeg button[data-p="${CSS.escape(S.page)}"]`);
      v.querySelectorAll('#trPageSeg button').forEach((x) => x.classList.toggle('on', x === seg));
      paintPage(); const d = v.querySelector('#trDetailTtl'); if (d && d.scrollIntoView) d.scrollIntoView({ block: 'start', behavior: 'smooth' });
    });
    paintPage();
  }
  /* 分頁明細：左＝這一頁各元件的次數（長條）；右＝點一個元件看它的細項 Top 10（例如「篩選：族群」裡被選最多的族群）*/
  function paintPage() {
    const v = S.v, box = v && v.querySelector('#trPageBody'); if (!box || !S.st) return;
    const rows = (S.st.e2 || []).filter((r) => r.page === S.page);
    const byComp = {};
    rows.forEach((r) => { byComp[r.comp] = (byComp[r.comp] || 0) + r.n; });
    const comps = Object.entries(byComp).sort((a, b) => b[1] - a[1]);
    if (!comps.length) { box.innerHTML = `<div class="empty">「${esc(VIEW_NAME[S.page] || S.page)}」這段期間還沒有細項紀錄。</div>`; return; }
    const withDet = comps.filter(([c]) => rows.some((r) => r.comp === c && r.detail));
    if (!S.comp || !byComp[S.comp] || !withDet.some(([c]) => c === S.comp)) S.comp = (withDet[0] || [])[0] || null;
    const det = S.comp ? rows.filter((r) => r.comp === S.comp && r.detail).sort((a, b) => b.n - a.n).slice(0, 10) : [];
    box.innerHTML = `<div class="cdgrid"><div><h3>${esc(VIEW_NAME[S.page] || S.page)}：哪個元件最常被用？</h3><p class="use">點元件名稱，右邊列出它的細項 Top 10。</p>${bars(comps, compName, 0, { click: true, id: 'trCompBars' })}</div>
      <div id="trCompDetail"><h3>${S.comp ? esc(compName(S.comp)) + '：細項 Top 10' : '細項'}</h3><p class="use">${S.comp ? (S.comp === 'how' ? '細項＝被點「?」的那張卡（元件 id）。' : S.comp.startsWith('filter') || ['rank_bar', 'clock_group', 'heat_tile'].includes(S.comp) ? '細項＝族群／產業鏈名稱。排第一的就是大家最想追的族群。' : S.page === 'stock' ? '細項＝股票代號。' : '細項＝元件或名稱。') : '這一頁的元件都沒有細項。'}</p>
        ${S.comp ? bars(det.map((r) => [r.detail, r.n]), (k) => k, 0, { id: 'trDetBars' }) : ''}</div></div>`;
    box.querySelector('#trCompBars').onclick = (e) => { const b = e.target.closest('button[data-k]'); if (!b) return; S.comp = b.dataset.k; paintPage(); };
  }
  function scatter(pts) {
    if (pts.length < 2) return '<div class="empty">至少要有兩檔個股的觀看紀錄才畫得出關係。</div>';
    const W = 480, H = 260, L = 44, B = 34, T = 12, R = 16;
    const xm = Math.max(...pts.map((p) => p.x)), ym = Math.max(0.5, ...pts.map((p) => p.y));
    const X = (x) => L + (x / xm) * (W - L - R), Y = (y) => H - B - (y / ym) * (H - B - T);
    const lab = pts.slice().sort((a, b) => (b.x + b.y * xm / ym) - (a.x + a.y * xm / ym)).slice(0, 6).map((p) => p.code);
    return `<svg class="sc" id="trScSvg" viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;height:auto" role="img" aria-label="個股被觀看次數與平均功能使用次數的散佈圖">
      <line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="var(--line-2)"/><line x1="${L}" y1="${T}" x2="${L}" y2="${H - B}" stroke="var(--line-2)"/>
      <text x="${W - R}" y="${H - 8}" text-anchor="end">被觀看次數 →（最多 ${nf(xm)}）</text><text x="6" y="${T + 4}" transform="rotate(90 6 ${T + 4})">每次觀看用幾次功能 →</text>
      <text x="${L - 4}" y="${H - B + 14}" text-anchor="end">0</text><text x="${L - 4}" y="${T + 10}" text-anchor="end">${ym.toFixed(1)}</text>
      ${pts.map((p) => `<circle cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="5" fill="var(--cyan)" fill-opacity=".75"><title>${esc(p.code)}：觀看 ${p.x}、平均 ${p.y.toFixed(2)} 次功能</title></circle>`
        + (lab.includes(p.code) ? `<text class="lb" x="${(X(p.x) > W - 70 ? X(p.x) - 7 : X(p.x) + 7).toFixed(1)}" y="${(Y(p.y) + 4).toFixed(1)}" text-anchor="${X(p.x) > W - 70 ? 'end' : 'start'}">${esc(p.code)}</text>` : '')).join('')}</svg>`;
  }
  function donut(parts) {
    const tot = parts.reduce((s, p) => s + p[1], 0);
    if (!tot) return '<div class="empty">這段期間還沒有開啟紀錄。</div>';
    const r = 44, c = 2 * Math.PI * r; let off = 0;
    const arcs = parts.map(([, n, col]) => { const len = n / tot * c; const s = `<circle r="${r}" cx="60" cy="60" fill="none" stroke="${col}" stroke-width="20" stroke-dasharray="${len.toFixed(2)} ${(c - len).toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 60 60)"/>`; off += len; return s; }).join('');
    return `<div class="donut"><svg viewBox="0 0 120 120" width="120" height="120" role="img" aria-label="登入與訪客比例">${arcs}<text x="60" y="65" text-anchor="middle" style="font-size:16px;font-weight:700;fill:var(--ink)">${Math.round(parts[0][1] / tot * 100)}%</text></svg>
      <ul>${parts.map(([nm, n, col]) => `<li><i style="background:${col}"></i>${esc(nm)}　<b>${nf(n)}</b>（${Math.round(n / tot * 100)}%）</li>`).join('')}</ul></div>`;
  }

  /* ==========================================================================
     #admin/perm 會員權限（層級 × 開放功能表 × Mail 名單）與 #admin/members 會員管理（新增、人員狀況、逐人微調）
     資料怎麼合：features.js 的預設值 ← 方案範本 ← 個別微調（後面蓋前面）；到期日過了就退回「免費會員」（Worker 端判斷）。
     層級對照：訪客＝內建範本 guest；註冊會員＝內建範本 free；付費會員＝其他所有（自建）範本，例如 399、799。
     撥開關只是「草稿」，按底部「儲存」才送出，「取消」整批放棄；有沒存的變更時，換人／換層級／換分頁／關分頁都會先問一次。
     範本只存「跟預設不同」的項目、微調只存「跟範本不同」的項目 —— 之後新增功能時，沒人設過的一律照預設（開），不會突然鎖住誰。
     ========================================================================== */
  const PS = { mode: 'member', tab: 'members', tier: 'guest', email: '', rec: null, plans: [], planSel: 'guest', list: null, confirmDel: false, A: null, v: null, seq: 0, draft: null, q: '',
    sort: 'seen', dir: -1, stf: '' };
  const FT = () => window.TwFeatures;
  const tpeTime = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(11, 19);
  /* 定價規劃（docs/commercialization_plan.md：免費／399／799）對應的範本。只「建立範本」，不套用到任何人、不改內建的「訪客」「免費會員」。*/
  const PRICE_TPL = [
    { id: 'pfree', name: '免費', off: ['live.tick', 'stock.tick', 'stock.k_min', 'stock.k_hour', 'ov.theme', 'heat.theme', 'heat.detail', 'ind.groups', 'ind.diagram', 'ind.3d', 'ind.rel'] },
    { id: 'p399', name: '399 即時', off: ['ov.theme', 'heat.theme', 'heat.detail', 'ind.groups', 'ind.diagram', 'ind.3d', 'ind.rel'] },
    { id: 'p799', name: '799 題材與產業地圖', off: [] },
  ];
  const TIER = [['guest', '訪客', '沒登入的人'], ['free', '註冊會員', '登入後沒被指定付費範本的人'], ['paid', '付費會員', '被指定付費範本的人']];
  function loadFeatures() {
    const grp = () => (FT() && !FT().inCat('grp').length ? fetch('data/groups_today.json').then((r) => (r.ok ? r.json() : [])).then((d) => { FT().addGroups(Array.isArray(d) ? d : []); }).catch(() => {}) : Promise.resolve());
    if (window.TwFeatures) return grp();
    return new Promise((res) => {
      const s = document.createElement('script'); s.src = 'features.js'; s.onload = () => res(); s.onerror = () => res(); document.head.appendChild(s);
    }).then(grp);
  }
  const planOf = (id) => PS.plans.find((p) => p.id === id) || null;
  const paidPlans = () => PS.plans.filter((p) => !p.builtin && p.id !== 'guest' && p.id !== 'free');
  const tierOf = (planId) => (planId === 'guest' ? 'guest' : (!planId || planId === 'free' || !planOf(planId) ? 'free' : 'paid'));
  const TIER_NAME = { guest: '訪客', free: '註冊會員', paid: '付費會員' };
  const mPlan = () => (PS.draft && PS.draft.plan) || (PS.rec ? PS.rec.plan : 'free');
  const mOver = () => (PS.draft && PS.draft.over) || (PS.rec && PS.rec.over) || {};
  const mExp = () => (PS.draft && PS.draft.expires !== undefined ? PS.draft.expires : (PS.rec ? PS.rec.expires || 0 : 0));
  function baseVals() {
    const o = FT().defaults();
    if (PS.mode === 'member') { const p = planOf(mPlan()); if (p) Object.assign(o, p.feats); }
    return o;
  }
  function curVals() {
    if (PS.mode === 'plan') {
      const o = FT().defaults(), p = planOf(PS.planSel);
      Object.assign(o, (PS.draft && PS.draft.feats) || (p && p.feats) || {});
      return o;
    }
    const o = baseVals();
    if (PS.rec) Object.assign(o, mOver());
    return o;
  }
  const diffKeys = (a, b) => new Set([...Object.keys(a || {}), ...Object.keys(b || {})].filter((k) => (a || {})[k] !== (b || {})[k])).size;
  function dirtyN() {
    const d = PS.draft; if (!d) return 0;
    if (PS.mode === 'plan') { const p = planOf(PS.planSel); return diffKeys((p && p.feats) || {}, d.feats || {}); }
    if (!PS.rec) return 0;
    return (d.plan !== PS.rec.plan ? 1 : 0) + ((d.expires !== undefined && (d.expires || 0) !== (PS.rec.expires || 0)) ? 1 : 0) + diffKeys(PS.rec.over || {}, d.over || {});
  }
  function guard() {
    if (!dirtyN()) { PS.draft = null; return true; }
    if (!window.confirm(`有 ${dirtyN()} 項變更還沒儲存，確定放棄？`)) return false;
    PS.draft = null; return true;
  }
  window.addEventListener('beforeunload', (e) => { if (/^#admin\/(perm|members)\b/.test(location.hash || '') && dirtyN()) { e.preventDefault(); e.returnValue = ''; } });
  function setStat(msg, cls) { const s = PS.v && PS.v.querySelector('#pmStat'); if (s) { s.textContent = msg; s.className = 'pmstat' + (cls ? ' ' + cls : ''); } }
  const ERR = { forbidden: '沒有管理者權限', bad_email: 'email 格式不對', bad_plan: '方案不存在', bad_feats: '開關格式不對', bad_name: '範本名稱不能空白', too_many: '數量超過上限', builtin: '內建範本不能刪', bad_expires: '到期日格式不對' };
  const errText = (r) => !r ? '連不到伺服器' : (ERR[r.error] || ('HTTP ' + r._s));
  const EMAIL_OK = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
  /* 到期日：畫面上是台北日期（yyyy-mm-dd），存的是「那一天台北 23:59:59」的毫秒 */
  const expToMs = (s) => { if (!s) return null; const t = Date.parse(s + 'T23:59:59+08:00'); return isFinite(t) ? t : null; };
  const msToDate = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10) : '');
  const honest = `<div class="card" style="margin-top:14px"><h3>這個鎖頭擋得住什麼？</h3><p class="pmwarn">鎖頭只擋一般使用者的畫面。這個網站是 GitHub Pages 靜態站，資料檔（site/data/*.json）是公開的，懂技術的人仍然能直接讀到。
        真正保護付費內容，要讓付費資料改由會員 Worker 驗證身分後才提供 —— 設計與工作量寫在 DECISIONS #288，這一版還沒做。</p></div>`;

  async function renderPerm(v, A, tab) {
    PS.v = v; PS.A = A; PS.draft = null; PS.tab = tab;
    PS.mode = tab === 'perm' ? 'plan' : 'member';
    if (tab === 'perm') {
      v.innerHTML = head(v, A) + `<p class="use" style="margin:8px 0 0">每一層一份「開放功能表」：關掉的功能在對方畫面上模糊並蓋鎖頭「此功能需開通」（不會整頁消失）；族群觀測關掉的族群，族群頁蓋鎖頭、下拉鎖住、圖上點了不展開。付費會員底下可以有多個範本（例如 399／799）。</p></div>
        <div class="card" id="pmHead" style="margin-top:14px"><h3>要設定哪一層？</h3>
          <div class="tier" id="ptTier" role="tablist">${TIER.map(([k, n]) => `<button type="button" role="tab" data-tier="${k}" class="${PS.tier === k ? 'on' : ''}">${n}<small id="ptCnt-${k}"></small></button>`).join('')}</div>
          <div id="pmTarget"></div>
          <div class="pmstat" id="pmStat" role="status" aria-live="polite"></div></div>
        <div class="secttl"><h2>① 開放功能表</h2><small id="ptFor"></small></div>
        <div class="pmcats" id="pmCats"></div>
        <div class="pmsave" id="pmSave" hidden><span id="pmDirty"></span><button type="button" id="pmCancel">取消</button><button type="button" class="pri" id="pmSaveGo">儲存</button></div>
        <div id="ptMailWrap"></div>${honest}`;
      v.querySelector('#ptTier').onclick = (e) => {
        const b = e.target.closest('button[data-tier]'); if (!b || b.dataset.tier === PS.tier || !guard()) return;
        PS.tier = b.dataset.tier; PS.confirmDel = false; pickTierPlan();
        v.querySelectorAll('#ptTier button').forEach((x) => x.classList.toggle('on', x === b));
        paintTarget(); paintCats(); paintMail(); setStat('');
      };
    } else {
      v.innerHTML = head(v, A) + `<p class="use" style="margin:8px 0 0">收費會員在這裡開通：新增他的 email、選層級／範本、設到期日（到期自動退回註冊會員），再逐項微調。下面的表列出所有人員的狀況。</p></div>
        <div class="card" id="pmAdd" style="margin-top:14px"><h3>① 新增會員</h3>
          <p class="use">輸入對方登入用的 Google email、選層級（付費會員要選範本）、需要的話填到期日，按「新增」。對方還沒登入過也可以先設好，登入後就生效。</p>
          <div class="pmbar"><input type="email" id="pmAddEmail" placeholder="member@example.com" autocomplete="off" aria-label="新會員 email">
            <select id="pmAddPlan" aria-label="新會員的層級與範本"></select>
            <label>到期日 <input type="date" id="pmAddExp" aria-label="到期日（留空＝不會到期）"></label>
            <button type="button" class="pri" id="pmAddGo">新增</button></div></div>
        <div class="card" id="pmList" style="margin-top:14px"><h3>② 所有人員狀況</h3><p class="use">設定過的會員＋登入過的人。點欄位標題排序；點一列就載入那個人，在下面逐項微調。狀態：有效＝登入過且沒過期；過期＝到期日已過（已自動退回註冊會員）；未登入過＝先設好、對方還沒來。</p>
          <div class="pmbar"><input type="search" id="pmSearch" placeholder="搜尋 email、名字、層級或範本" aria-label="搜尋會員" value="${esc(PS.q)}">
            <select id="pmStatF" aria-label="依狀態篩選"><option value="">全部狀態</option><option value="ok">有效</option><option value="exp">過期</option><option value="new">未登入過</option></select><span class="pmcnt" id="pmCnt"></span></div>
          <div id="pmListBody"><div class="empty">載入中…</div></div></div>
        <div class="card" id="pmHead" style="margin-top:14px"><h3>③ 逐人微調</h3>
          <p class="use">先選層級／範本，再個別微調。開關撥完按最下面的「儲存」才會生效。</p>
          <div id="pmTarget"></div>
          <div class="pmstat" id="pmStat" role="status" aria-live="polite"></div></div>
        <div class="pmcats" id="pmCats"></div>
        <div class="pmsave" id="pmSave" hidden><span id="pmDirty"></span><button type="button" id="pmCancel">取消</button><button type="button" class="pri" id="pmSaveGo">儲存</button></div>${honest}`;
      v.querySelector('#pmSearch').oninput = (e) => { PS.q = e.target.value; paintList(); };
      v.querySelector('#pmStatF').value = PS.stf;
      v.querySelector('#pmStatF').onchange = (e) => { PS.stf = e.target.value; paintList(); };
      v.querySelector('#pmAddGo').onclick = addMember;
      v.querySelector('#pmAddEmail').onkeydown = (e) => { if (e.key === 'Enter') addMember(); };
    }
    wireHead(v);
    v.querySelector('#pmSaveGo').onclick = saveDraft;
    v.querySelector('#pmCancel').onclick = () => { PS.draft = null; paintTarget(); paintCats(); setStat('已取消，回到上次儲存的設定'); };
    await loadFeatures();
    if (!FT()) { v.querySelector('#pmCats').innerHTML = '<div class="card"><p class="err">功能清單（features.js）載入失敗。</p></div>'; return; }
    const [pl, li] = await Promise.all([A.call('/v1/admin/plans/get', {}), A.call('/v1/admin/perm/list', {})]);
    if (tabOf() !== tab) return;
    if (!pl || pl._s !== 200) {
      v.querySelector('#pmCats').innerHTML = `<div class="card" style="grid-column:1/-1"><p class="err">讀不到方案範本（${esc(errText(pl))}）。${pl && pl._s === 404 ? '會員 Worker 可能還沒更新成有功能權限的版本（deploy-account-worker.yml）。' : '只有管理者帳號看得到；確認 Worker 的 ADMIN_EMAILS 有你的 email。'}</p></div>`;
      return;
    }
    PS.plans = pl.plans || [];
    PS.list = li && li._s === 200 ? li : { rows: [], users: [] };
    if (tab === 'perm') pickTierPlan(true);
    paintAddPlan(); paintTarget(); paintCats(); paintList(); paintMail(); paintTierCnt();
    if (PS.mode === 'member' && PS.email) loadMember(PS.email);
  }
  /* 層級 → 要編的範本：訪客＝guest、註冊會員＝free、付費＝目前選的付費範本（沒有就第一個）*/
  function pickTierPlan(keep) {
    if (PS.tier === 'guest') PS.planSel = 'guest';
    else if (PS.tier === 'free') PS.planSel = 'free';
    else { const pp = paidPlans(); if (!(keep && pp.some((p) => p.id === PS.planSel)) && !pp.some((p) => p.id === PS.planSel)) PS.planSel = pp.length ? pp[0].id : ''; }
  }
  function planOpts(sel, withGuest) {
    const pp = paidPlans();
    return (withGuest ? `<option value="guest" ${sel === 'guest' ? 'selected' : ''}>訪客</option>` : '')
      + `<option value="free" ${sel === 'free' ? 'selected' : ''}>註冊會員（${esc((planOf('free') || {}).name || '免費會員')}）</option>`
      + (pp.length ? `<optgroup label="付費會員">${pp.map((p) => `<option value="${esc(p.id)}" ${p.id === sel ? 'selected' : ''}>付費：${esc(p.name)}</option>`).join('')}</optgroup>` : '');
  }
  function paintAddPlan() {
    const s = PS.v && PS.v.querySelector('#pmAddPlan'); if (!s) return;
    s.innerHTML = planOpts(s.value || 'free', false);
  }
  /* 合併「設定過的（perm）」與「登入過的（users）」→ 一人一列，帶狀態 */
  function people() {
    const now = (PS.list && PS.list.now) || Date.now();
    const users = new Map(((PS.list && PS.list.users) || []).map((u) => [u.email, u]));
    const all = ((PS.list && PS.list.rows) || []).map((r) => { const u = users.get(r.email) || {}; return Object.assign({ set: true }, r, { name: u.name || '', seen: r.seen || u.seen || 0, visits: u.visits || 0, known: users.has(r.email) }); });
    const have = new Set(all.map((r) => r.email));
    users.forEach((u, e) => { if (e && !have.has(e)) all.push({ email: e, name: u.name || '', plan: 'free', n: 0, updated: 0, expires: 0, seen: u.seen || 0, visits: u.visits || 0, set: false, known: true }); });
    all.forEach((r) => {
      r.tier = tierOf(r.plan);
      r.st = r.expires && r.expires < now ? 'exp' : (r.known ? 'ok' : 'new');
    });
    return all;
  }
  const ST_NAME = { ok: '有效', exp: '過期', new: '未登入過' };
  async function addMember() {
    const v = PS.v, inp = v.querySelector('#pmAddEmail'), e = (inp.value || '').trim().toLowerCase();
    if (!EMAIL_OK(e)) { setStat('email 格式不對（例如 member@example.com）', 'bad'); inp.focus(); return; }
    if (!guard()) return;
    const plan = v.querySelector('#pmAddPlan').value || 'free';
    const expRaw = v.querySelector('#pmAddExp').value, expires = expToMs(expRaw);
    if (expRaw && !expires) { setStat('到期日格式不對', 'bad'); return; }
    setStat('新增中…');
    const j = await PS.A.call('/v1/admin/perm/put', Object.assign({ email: e, plan, over: {} }, expires ? { expires } : {}));
    if (!j || j._s !== 200) { setStat('新增失敗：' + errText(j), 'bad'); return; }
    inp.value = ''; v.querySelector('#pmAddExp').value = '';
    PS.email = j.email; PS.rec = j; PS.draft = null;
    afterSave(j.email, `已新增 ${j.email}（${TIER_NAME[tierOf(plan)]}「${(planOf(plan) || {}).name || plan}」${expires ? '，到期 ' + expRaw : ''}）・下面可以再逐項微調，改完按「儲存」`);
    const h = v.querySelector('#pmHead'); if (h && h.scrollIntoView) h.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  function paintTierCnt() {
    if (PS.tab !== 'perm' || !PS.v) return;
    const ps = people(), c = { free: ps.filter((r) => r.tier === 'free').length, paid: ps.filter((r) => r.tier === 'paid').length };
    ['free', 'paid'].forEach((k) => { const el = PS.v.querySelector('#ptCnt-' + k); if (el) el.textContent = c[k] + ' 人'; });
  }
  function paintTarget() {
    const v = PS.v, box = v.querySelector('#pmTarget'); if (!box) return;
    if (PS.mode === 'member') {
      const emails = new Map();
      ((PS.list && PS.list.rows) || []).forEach((r) => emails.set(r.email, r.email));
      ((PS.list && PS.list.users) || []).forEach((u) => { if (u.email && !emails.has(u.email)) emails.set(u.email, u.name ? `${u.name}（${u.email}）` : u.email); });
      const r = PS.rec;
      box.innerHTML = `<div class="pmbar"><input type="email" id="pmEmail" list="pmEmails" placeholder="輸入或選擇會員 email" autocomplete="off" value="${esc(PS.email)}" aria-label="會員 email">
          <datalist id="pmEmails">${[...emails.entries()].map(([e, l]) => `<option value="${esc(e)}">${esc(l)}</option>`).join('')}</datalist>
          <button type="button" id="pmLoad">讀取</button></div>
        <div class="pmwho" id="pmWho">${r ? whoLine(r) : '從上面的表點一位會員，或在這裡輸入 email 按「讀取」。'}</div>
        ${r ? `<div class="pmbar"><label>層級／範本 <select id="pmPlan">${planOpts(mPlan(), false)}</select></label>
          <label>到期日 <input type="date" id="pmExp" value="${msToDate(mExp())}" aria-label="到期日（留空＝不會到期）"></label>
          <button type="button" id="pmClearOver" ${Object.keys(mOver()).length ? '' : 'disabled'}>清除個別微調</button>
          <input type="text" id="pmNewName" maxlength="20" placeholder="新範本名稱" aria-label="新範本名稱" style="width:9em">
          <button type="button" id="pmSaveAs">把這組存成新付費範本</button>
          <button type="button" class="danger" id="pmReset" ${r.set ? '' : 'disabled'}>移除此會員設定</button></div>` : ''}`;
      const go = () => { const e = (v.querySelector('#pmEmail').value || '').trim(); if (e && guard()) loadMember(e); };
      v.querySelector('#pmLoad').onclick = go;
      v.querySelector('#pmEmail').onkeydown = (e) => { if (e.key === 'Enter') go(); };
      const ps = v.querySelector('#pmPlan');
      if (ps) ps.onchange = () => { draftMember({ plan: ps.value }); setStat(`改成「${(planOf(ps.value) || {}).name || ps.value}」（還沒儲存）`); };
      const ex = v.querySelector('#pmExp');
      if (ex) ex.onchange = () => { draftMember({ expires: expToMs(ex.value) || 0 }); setStat(ex.value ? `到期日改成 ${ex.value}（還沒儲存）` : '改成不會到期（還沒儲存）'); };
      const co = v.querySelector('#pmClearOver');
      if (co) co.onclick = () => { draftMember({ over: {} }); setStat('已清除個別微調（還沒儲存）'); };
      const rs = v.querySelector('#pmReset');
      if (rs) rs.onclick = async () => {
        if (!PS.confirmDel) { PS.confirmDel = true; rs.textContent = '確定移除？（回到註冊會員預設）'; return; }
        PS.confirmDel = false;
        const j = await PS.A.call('/v1/admin/perm/put', { email: PS.rec.email, reset: true });
        if (j && j._s === 200) { PS.rec = j; PS.draft = null; afterSave(j.email, '已移除此會員的設定，回到「註冊會員」預設'); } else setStat('移除失敗：' + errText(j), 'bad');
      };
      const sa = v.querySelector('#pmSaveAs');
      if (sa) sa.onclick = () => saveAsPlan(v.querySelector('#pmNewName').value);
    } else {
      const p = planOf(PS.planSel), missing = PRICE_TPL.filter((t) => !planOf(t.id));
      const pp = paidPlans();
      const tierLine = PS.tier === 'guest' ? '<b>訪客</b>：所有沒登入的人都套這一份。'
        : PS.tier === 'free' ? '<b>註冊會員</b>：登入後沒被指定付費範本的人（以及付費到期的人）都套這一份。'
          : '<b>付費會員</b>：每個範本是一個價位（例如 399／799）。在「會員管理」把會員指定到範本，或在下面的名單看誰在用。';
      box.innerHTML = `<div class="pmwho">${tierLine}</div>
        ${PS.tier === 'paid' ? `<div class="plchips" id="ptPlans">${pp.map((x) => `<button type="button" data-p="${esc(x.id)}" class="${x.id === PS.planSel ? 'on' : ''}">${esc(x.name)}<small>${x.members || 0} 人</small></button>`).join('') || '<span class="pmcnt">還沒有付費範本 —— 用右邊新增，或按下面「建立定價範本」。</span>'}</div>
          <div class="pmbar"><input type="text" id="ptNewName" maxlength="20" placeholder="新範本名稱（例如 399 即時）" aria-label="新付費範本名稱" style="width:14em">
            <button type="button" id="ptNewGo">＋ 新增付費範本</button>
            <input type="text" id="pmNewName" maxlength="20" placeholder="另存名稱" aria-label="另存的範本名稱" style="width:8em" ${p ? '' : 'disabled'}>
            <button type="button" id="pmSaveAs" ${p ? '' : 'disabled'}>把這組另存成新範本</button>
            <button type="button" class="danger" id="pmPlanDel" ${p && !p.builtin ? '' : 'disabled'} title="用這個範本的會員會退回註冊會員">刪除這個範本</button></div>
          <div class="pmbar pmtpl">${missing.length ? `<button type="button" id="pmTpl">建立定價範本（${missing.map((t) => esc(t.name)).join('／')}）</button>` : '<span>定價範本（免費／399 即時／799 題材與產業地圖）都已建立。</span>'}
            <small>依定價規劃預先關好對應的功能；<b>只建立範本，不會套用到任何人</b>，也不改「訪客」「註冊會員」。</small></div>` : ''}
        <div class="pmwho" id="pmWho">${p ? planLine(p) : ''}</div>`;
      const forEl = v.querySelector('#ptFor'); if (forEl) forEl.textContent = p ? `正在編：${TIER_NAME[PS.tier]}${PS.tier === 'paid' ? '・' + p.name : ''}` : '';
      const chips = v.querySelector('#ptPlans');
      if (chips) chips.onclick = (e) => { const b = e.target.closest('button[data-p]'); if (!b || b.dataset.p === PS.planSel || !guard()) return; PS.planSel = b.dataset.p; PS.confirmDel = false; paintTarget(); paintCats(); paintMail(); setStat(''); };
      const ng = v.querySelector('#ptNewGo');
      if (ng) ng.onclick = () => newPaidPlan(v.querySelector('#ptNewName').value);
      const sa = v.querySelector('#pmSaveAs'); if (sa) sa.onclick = () => saveAsPlan(v.querySelector('#pmNewName').value);
      const tb = v.querySelector('#pmTpl'); if (tb) tb.onclick = makePriceTemplates;
      const del = v.querySelector('#pmPlanDel');
      if (del) del.onclick = async () => {
        if (!PS.confirmDel) { PS.confirmDel = true; del.textContent = '確定刪除？'; return; }
        PS.confirmDel = false;
        const nm = p.name;
        const j = await PS.A.call('/v1/admin/plans/put', { id: PS.planSel, del: true });
        if (j && j._s === 200) { PS.plans = j.plans; PS.draft = null; pickTierPlan(); paintAddPlan(); paintTarget(); paintCats(); setStat(`已刪除「${nm}」；原本用它的會員退回「註冊會員」（個別微調保留）`, 'ok'); refreshList(); }
        else setStat('刪除失敗：' + errText(j), 'bad');
      };
    }
    paintSave();
  }
  async function newPaidPlan(name) {
    name = String(name || '').trim();
    if (!name) { setStat('先輸入新範本的名稱（例如 399 即時）', 'bad'); return; }
    if (!guard()) return;
    const id = 'p' + Date.now().toString(36).slice(-7);
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats: {} });
    if (!j || j._s !== 200) { setStat('新增失敗：' + errText(j), 'bad'); return; }
    PS.plans = j.plans; PS.planSel = id; PS.draft = null;
    paintAddPlan(); paintTarget(); paintCats(); paintMail(); setStat(`已新增付費範本「${name}」（目前全開，下面逐項關掉這個價位不給的功能）`, 'ok');
  }
  async function makePriceTemplates() {
    if (!guard()) return;
    let last = null;
    for (const t of PRICE_TPL) {
      if (planOf(t.id)) continue;
      const feats = {};
      t.off.forEach((k) => { const f = FT().byId(k); if (f) feats[k] = f.kind === 'limit' ? 0 : false; });
      const j = await PS.A.call('/v1/admin/plans/put', { id: t.id, name: t.name, feats });
      if (!j || j._s !== 200) { setStat(`建立「${t.name}」失敗：` + errText(j), 'bad'); return; }
      PS.plans = j.plans; last = t.id;
    }
    if (last) PS.planSel = last;
    paintAddPlan(); paintTarget(); paintCats(); paintMail(); setStat('已建立定價範本（沒有套用到任何人）', 'ok');
  }
  function whoLine(r) {
    const n = Object.keys(mOver()).length, p = planOf(mPlan()), ex = mExp();
    const who = r.known ? `已登入過：<b>${esc(r.known.name || '')}</b>${r.known.seen ? `（最後登入 ${dstr(r.known.seen)}）` : ''}` : '<b>尚未登入過</b>（先設好，對方登入後就生效）';
    const exs = ex ? (ex < Date.now() ? `・<b style="color:#ff6b7a">已於 ${msToDate(ex)} 到期</b>（目前套註冊會員）` : `・到期 <b>${msToDate(ex)}</b>`) : '';
    return `<b>${esc(r.email)}</b>・${who}・${TIER_NAME[tierOf(mPlan())]}「<b>${esc(p ? p.name : (r.planName || r.plan))}</b>」${exs}・個別微調 <b>${n}</b> 項${r.set ? '' : '（還沒個別設定過＝照免費會員）'}`;
  }
  function planLine(p) {
    const n = Object.keys((PS.draft && PS.draft.feats) || p.feats || {}).length;
    const who = p.id === 'guest' ? '套用對象：所有沒登入的訪客' : p.id === 'free' ? '套用對象：登入後沒被指定付費範本的會員' : `套用對象：被指定這個範本的會員（目前 ${p.members || 0} 位）`;
    return `${who}・跟預設不同的項目 <b>${n}</b> 項`;
  }
  function paintSave() {
    const bar = PS.v && PS.v.querySelector('#pmSave'); if (!bar) return;
    const n = dirtyN();
    bar.hidden = !n;
    const who = PS.mode === 'plan' ? `${TIER_NAME[PS.tier]}「${(planOf(PS.planSel) || {}).name || ''}」` : (PS.rec ? PS.rec.email : '');
    bar.querySelector('#pmDirty').innerHTML = n ? `<b>${n}</b> 項變更還沒儲存・${esc(who)}` : '';
  }
  /* ② Mail 人員名單：屬於這一層／這個範本的會員（訪客沒有名單）*/
  function paintMail() {
    const box = PS.v && PS.v.querySelector('#ptMailWrap'); if (!box) return;
    if (PS.tier === 'guest') { box.innerHTML = ''; return; }
    const ps = people().filter((r) => (PS.tier === 'free' ? r.tier === 'free' : r.plan === PS.planSel));
    const ttl = PS.tier === 'free' ? '註冊會員' : `付費・${(planOf(PS.planSel) || {}).name || ''}`;
    box.innerHTML = `<div class="secttl"><h2>② Mail 人員名單</h2><small>${esc(ttl)}・${ps.length} 人</small></div>
      <div class="card" id="ptMail" style="margin-top:10px"><p class="use">${PS.tier === 'free' ? '登入過、沒被指定付費範本的人，加上付費已過期的人（過期的人也列在原本的範本底下，標「過期」）。' : '被指定到這個範本的會員。'}要新增、改到期日或換範本，到「會員管理」。</p>
        ${ps.length ? `<table class="pmlist"><thead><tr><th>email</th><th>名字</th><th class="c-exp">到期日</th><th>狀態</th></tr></thead><tbody>${ps.map((r) => `<tr><td>${esc(r.email)}</td><td>${esc(r.name || '—')}</td><td class="c-exp">${dday(r.expires)}</td><td><span class="stt ${r.st}">${ST_NAME[r.st]}</span></td></tr>`).join('')}</tbody></table>`
          : '<div class="empty">這一層目前沒有人。</div>'}
        <div class="pmbar"><a href="#admin/members" id="ptGoMembers">到會員管理新增會員 →</a></div></div>`;
  }

  function catRows(fs, cur, base, saved, now, ready, compact) {
    return fs.map((f) => {
      const val = cur[f.id], diff = PS.mode === 'member' ? (PS.rec && Object.prototype.hasOwnProperty.call(mOver(), f.id)) : val !== f.def;
      const unsaved = ready && saved[f.id] !== now[f.id];
      const ctl = f.kind === 'limit'
        ? `<select data-f="${esc(f.id)}" aria-label="${esc(f.name)}" ${ready ? '' : 'disabled'}>${Array.from({ length: f.max + 1 }, (_, i) => `<option value="${i}" ${i === val ? 'selected' : ''}>${i === 0 ? '不能用' : i + ' 頁'}</option>`).join('')}</select>`
        : `<label class="psw"><input type="checkbox" role="switch" data-f="${esc(f.id)}" aria-label="${esc(f.name)}" ${val !== false ? 'checked' : ''} ${ready ? '' : 'disabled'}><span></span></label>`;
      const tag = (unsaved ? '<span class="pmtag new" title="改了還沒按儲存">未存</span>' : '') + (diff ? (PS.mode === 'member' ? `<span class="pmtag" title="跟範本不同（範本是${base[f.id] === false ? '關' : base[f.id] === true ? '開' : base[f.id]}）">微調</span><button type="button" class="pmrev" data-rev="${esc(f.id)}">還原</button>`
        : `<span class="pmtag" title="跟預設不同">改過</span>`) : '');
      return `<div class="pmrow${compact ? ' sm' : ''}${unsaved ? ' dirty' : ''}" data-f="${esc(f.id)}">${ctl}<div class="pmtx"><b>${esc(f.name)}</b>${compact ? '' : `<small>${esc(f.desc)}</small>`}</div><div class="pmside">${tag}</div></div>`;
    }).join('');
  }
  function paintCats() {
    const v = PS.v, box = v.querySelector('#pmCats'); if (!box || !FT()) return;
    const ready = PS.mode === 'plan' ? !!planOf(PS.planSel) : !!PS.rec;
    const cur = curVals(), base = baseVals();
    const saved = PS.mode === 'plan' ? ((planOf(PS.planSel) || {}).feats || {}) : ((PS.rec && PS.rec.over) || {});
    const now = PS.mode === 'plan' ? ((PS.draft && PS.draft.feats) || saved) : mOver();
    box.classList.toggle('off', !ready);
    box.innerHTML = FT().cats.map((c) => {
      const fs = FT().inCat(c.id); if (!fs.length) return '';
      const nOn = fs.filter((f) => f.kind === 'limit' ? cur[f.id] > 0 : cur[f.id] !== false).length;
      const hd = `<div class="card pmcat" data-cat="${esc(c.id)}"><div class="pmcathd"><h3>${esc(c.name)}<small>${fs.length} 項・開 ${nOn}</small></h3>
          <button type="button" data-all="1" data-cat="${esc(c.id)}" ${ready ? '' : 'disabled'}>全開</button><button type="button" data-all="0" data-cat="${esc(c.id)}" ${ready ? '' : 'disabled'}>全關</button></div>`;
      if (c.id === 'grp') {
        /* 族群觀測：117 個，依產業鏈分小標、三欄緊湊排（不寫說明，說明寫在卡片上方一行）*/
        const by = {}; fs.forEach((f) => { (by[f.chain || ''] = by[f.chain || ''] || []).push(f); });
        return hd + `<p class="use" style="margin:0 0 4px">關掉的族群：族群頁模糊＋鎖頭、資金輪動的族群下拉那一列鎖住、熱力圖／排行／輪盤點了只跳「此族群需開通」（canvas 圖上的方塊無法模糊，見 perm.js）。</p><div class="grpgrid">`
          + Object.keys(by).map((ch) => `<div class="grpch">${esc((fs.find((f) => f.chain === ch) || {}).desc ? (fs.find((f) => f.chain === ch).desc.split('・')[0]) : ch)}（${by[ch].length}）</div>` + catRows(by[ch], cur, base, saved, now, ready, true)).join('') + '</div></div>';
      }
      return hd + catRows(fs, cur, base, saved, now, ready, false) + '</div>';
    }).join('');
    box.onchange = (e) => {
      const el = e.target.closest('[data-f]'); if (!el) return;
      const f = FT().byId(el.dataset.f); if (!f) return;
      setVals({ [f.id]: f.kind === 'limit' ? parseInt(el.value, 10) : !!el.checked });
    };
    box.onclick = (e) => {
      const a = e.target.closest('button[data-all]');
      if (a) {
        const on = a.dataset.all === '1';
        const ch = {}; FT().inCat(a.dataset.cat).forEach((f) => { ch[f.id] = f.kind === 'limit' ? (on ? f.max : 0) : on; });
        setVals(ch);
        return;
      }
      const r = e.target.closest('button[data-rev]');
      if (r && PS.rec) { const over = Object.assign({}, mOver()); delete over[r.dataset.rev]; draftMember({ over }); }
    };
    paintSave();
  }
  function draftMember(patch) {
    if (!PS.rec) return;
    PS.draft = Object.assign({ plan: mPlan(), over: Object.assign({}, mOver()), expires: mExp() }, PS.draft || {}, patch);
    if (!dirtyN()) PS.draft = null;
    paintTarget(); paintCats();
  }
  function setVals(ch) {
    if (PS.mode === 'member') {
      if (!PS.rec) return;
      const base = baseVals(), over = Object.assign({}, mOver());
      Object.entries(ch).forEach(([k, v2]) => { if (base[k] === v2) delete over[k]; else over[k] = v2; });
      draftMember({ over });
    } else {
      const p = planOf(PS.planSel); if (!p) return;
      const feats = Object.assign({}, (PS.draft && PS.draft.feats) || p.feats || {});
      Object.entries(ch).forEach(([k, v2]) => { const f = FT().byId(k); if (f && f.def === v2) delete feats[k]; else feats[k] = v2; });
      PS.draft = diffKeys(feats, p.feats || {}) ? { feats } : null;
      paintTarget(); paintCats();
    }
  }
  async function saveDraft() {
    const n = dirtyN(); if (!n) return;
    if (PS.mode === 'member') await saveMember(PS.draft, `${n} 項變更`);
    else { const p = planOf(PS.planSel); if (p) await savePlan(p.id, p.name, PS.draft.feats, `${n} 項變更`); }
  }
  async function loadMember(email) {
    const seq = ++PS.seq;
    setStat('讀取中…');
    const j = await PS.A.call('/v1/admin/perm/get', { email });
    if (seq !== PS.seq) return;
    if (!j || j._s !== 200) { setStat('讀不到：' + errText(j), 'bad'); return; }
    PS.email = j.email; PS.rec = j; PS.confirmDel = false; PS.draft = null;
    paintTarget(); paintCats(); paintList(); setStat('');
  }
  async function saveMember(patch, label) {
    const r = PS.rec; if (!r) return;
    setStat('儲存中…');
    const body = { email: r.email, plan: patch.plan || r.plan, over: patch.over || r.over || {} };
    if (patch.expires !== undefined && (patch.expires || 0) !== (r.expires || 0)) body.expires = patch.expires || null;
    const j = await PS.A.call('/v1/admin/perm/put', body);
    if (j && j._s === 200) { PS.rec = Object.assign({}, j, { known: r.known }); PS.draft = null; afterSave(j.email, label + `・已儲存（台北 ${tpeTime()}）`); }
    else { setStat('儲存失敗：' + errText(j) + '（變更還在，可以再按一次儲存）', 'bad'); }
  }
  function afterSave(email, msg) {
    paintTarget(); paintCats(); setStat(msg, 'ok'); refreshList();
    const me = (PS.A.user() || {}).email;
    if (me && String(me).toLowerCase() === email && window.TwPerm) window.TwPerm.refresh();
  }
  async function savePlan(id, name, feats, label) {
    setStat('儲存中…');
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats });
    if (j && j._s === 200) {
      PS.plans = j.plans; PS.draft = null; paintAddPlan(); paintTarget(); paintCats(); setStat(label + `・已儲存到「${name}」範本（台北 ${tpeTime()}）`, 'ok');
      if (window.TwPerm) window.TwPerm.refresh();
    } else { setStat('儲存失敗：' + errText(j) + '（變更還在，可以再按一次儲存）', 'bad'); }
  }
  async function saveAsPlan(name) {
    name = String(name || '').trim();
    if (!name) { setStat('先在旁邊輸入新範本的名稱', 'bad'); return; }
    const cur = curVals(), feats = {};
    FT().list.forEach((f) => { if (cur[f.id] !== f.def) feats[f.id] = cur[f.id]; });
    const id = 'p' + Date.now().toString(36).slice(-7);
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats });
    if (!j || j._s !== 200) { setStat('另存失敗：' + errText(j), 'bad'); return; }
    PS.plans = j.plans; paintAddPlan();
    if (PS.mode === 'plan') { PS.tier = 'paid'; PS.planSel = id; PS.draft = null; PS.v.querySelectorAll('#ptTier button').forEach((x) => x.classList.toggle('on', x.dataset.tier === 'paid')); paintTarget(); paintCats(); paintMail(); setStat(`已另存為新付費範本「${name}」`, 'ok'); }
    else { await saveMember({ plan: id, over: {} }, `已存成新範本「${name}」並套用到這位會員`); }
  }
  async function refreshList() {
    const li = await PS.A.call('/v1/admin/perm/list', {});
    if (li && li._s === 200) { PS.list = li; paintList(); paintMail(); paintTierCnt(); }
  }
  /* 所有人員狀況：email、名字、層級、範本、到期日、最後登入、近 30 天造訪、狀態；點標題排序、搜尋、依狀態篩 */
  const COLS = [['email', 'email', ''], ['tier', '層級', ''], ['plan', '範本', 'c-tpl'], ['expires', '到期日', 'c-exp'], ['seen', '最後登入（台北）', 'c-seen'], ['visits', '近 30 天造訪', 'c-vis num'], ['st', '狀態', '']];
  function paintList() {
    const box = PS.v && PS.v.querySelector('#pmListBody'); if (!box) return;
    const pn = (id) => (planOf(id) || {}).name || id;
    const all = people();
    const q = PS.q.trim().toLowerCase();
    let rows = q ? all.filter((r) => (r.email + ' ' + r.name + ' ' + pn(r.plan) + ' ' + TIER_NAME[r.tier]).toLowerCase().includes(q)) : all.slice();
    if (PS.stf) rows = rows.filter((r) => r.st === PS.stf);
    const key = PS.sort, dir = PS.dir;
    const val = (r) => key === 'plan' ? pn(r.plan) : key === 'tier' ? ['guest', 'free', 'paid'].indexOf(r.tier) : key === 'st' ? ['ok', 'new', 'exp'].indexOf(r.st) : (r[key] == null ? '' : r[key]);
    rows.sort((a, b) => { const x = val(a), y = val(b); return (x > y ? 1 : x < y ? -1 : 0) * dir || a.email.localeCompare(b.email); });
    const cnt = PS.v.querySelector('#pmCnt'); if (cnt) cnt.textContent = (q || PS.stf) ? `${rows.length} ／ ${all.length} 位` : `共 ${all.length} 位`;
    box.innerHTML = rows.length ? `<table class="pmlist" id="pmTable"><thead><tr>${COLS.map(([k, n, cls]) => `<th data-sort="${k}" class="${cls}${PS.sort === k ? ' sorted' : ''}" aria-sort="${PS.sort === k ? (PS.dir > 0 ? 'ascending' : 'descending') : 'none'}">${n}${PS.sort === k ? (PS.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('')}<th class="c-n">微調</th></tr></thead><tbody>${rows.map((r) =>
      `<tr data-email="${esc(r.email)}" class="${PS.rec && r.email === PS.rec.email ? 'on' : ''}"><td>${esc(r.email)}${r.name ? `<small>${esc(r.name)}</small>` : ''}</td><td>${TIER_NAME[r.tier]}${r.set ? '' : '<small>（預設）</small>'}</td><td class="c-tpl">${r.tier === 'paid' ? esc(pn(r.plan)) : '—'}</td><td class="c-exp">${dday(r.expires)}</td><td class="c-seen">${dstr(r.seen)}</td><td class="c-vis num">${nf(r.visits)}</td><td><span class="stt ${r.st}">${ST_NAME[r.st]}</span></td><td class="c-n">${r.n || 0}</td></tr>`).join('')}</tbody></table>`
      : `<div class="empty">${q || PS.stf ? '沒有符合條件的會員。' : '還沒有任何會員。用上面的「新增會員」加第一位。'}</div>`;
    box.onclick = (e) => {
      const th = e.target.closest('th[data-sort]');
      if (th) { if (PS.sort === th.dataset.sort) PS.dir = -PS.dir; else { PS.sort = th.dataset.sort; PS.dir = th.dataset.sort === 'email' ? 1 : -1; } paintList(); return; }
      const tr = e.target.closest('tr[data-email]'); if (!tr || !guard()) return;
      PS.email = tr.dataset.email; loadMember(tr.dataset.email);
      const h = PS.v.querySelector('#pmHead'); if (h && h.scrollIntoView) h.scrollIntoView({ block: 'start', behavior: 'smooth' });
    };
  }

  window.TwAdmin = { render };
})();
