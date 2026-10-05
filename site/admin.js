/* ============================================================================
   管理區 #admin（只有管理者看得到）—— 2026-10-05 admin-v2 改版（Andy A～E）
   三個子分頁，用網址分（上一頁回得來、可以直接貼網址），頁內頂部一排 tab 切換：
     #admin/perm      會員權限（admin-v3 簡化）：訪客｜註冊會員｜付費會員 三個大分頁＋「＋」新增付費範本；
                      每頁兩個子分頁「觀看權限」（開放功能表＋族群觀測，每個功能一格每日瀏覽次數）「會員名單」（訪客改放流量摘要）
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
#v-admin .ptabs{display:flex;align-items:flex-end;gap:4px;flex-wrap:wrap;margin-top:8px;border-bottom:1px solid var(--line-2);padding:0 4px}
#v-admin .ptabs button{display:flex;flex-direction:column;align-items:flex-start;gap:1px;min-height:52px;padding:8px 18px;font-size:15.5px;font-weight:600;background:color-mix(in srgb,var(--panel-2) 70%,transparent);color:var(--ink-2);
  border:1px solid var(--line-2);border-bottom:0;border-radius:10px 10px 0 0;margin-bottom:-1px;cursor:pointer;text-align:left}
#v-admin .ptabs button small{font-size:12px;font-weight:400;color:var(--ink-2)}
#v-admin .ptabs button:hover{color:var(--ink)}
#v-admin .ptabs button.on{background:var(--panel);color:var(--ink);border-color:var(--cyan);border-bottom:1px solid var(--panel);box-shadow:inset 0 3px 0 var(--cyan);position:relative;z-index:1}
#v-admin .ptabs button.add{min-width:52px;align-items:center;justify-content:center;font-size:22px;font-weight:400}
#v-admin .ptpanel{border:1px solid var(--line-2);border-top:0;border-radius:0 0 10px 10px;padding:4px 14px 12px;background:var(--panel)}
#v-admin .ptabs:has(button.on)+.ptpanel{border-color:var(--cyan)}
#v-admin .pmcats.card{gap:0;padding:0;overflow:hidden;grid-template-columns:repeat(auto-fill,minmax(min(100%,260px),1fr))}
#v-admin .pmcats.card .pmcat{padding:12px 16px;box-shadow:1px 0 0 color-mix(in srgb,var(--line) 70%,transparent),0 1px 0 color-mix(in srgb,var(--line) 70%,transparent);min-width:0}
#v-admin .pmgrpbox.card{display:block;margin-top:10px}
#v-admin #pmGrpTtl{display:flex;align-items:center;gap:10px;flex-wrap:wrap}#v-admin #pmGrpTtl .pmfold{margin-left:auto}
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
#v-admin .pmcats.off .pmbody,#v-admin .pmcats.off [data-all]{opacity:.5;pointer-events:none}
#v-admin .pmfold{display:inline-flex;align-items:center;gap:6px}
#v-admin .pmfold button{height:30px;font-size:13px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 12px;cursor:pointer}
#v-admin .pmfold small{font-size:12.5px;color:var(--ink-2)}
#v-admin .pmcats{align-items:start}
#v-admin .pmfoldhd{display:flex;align-items:baseline;gap:6px;flex:1 1 auto;min-width:0;background:none!important;border:0!important;box-shadow:none!important;height:auto!important;padding:2px 0!important;color:var(--ink);text-align:left;cursor:pointer;font:inherit}
#v-admin .pmfoldhd h3{margin:0;font-size:inherit;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}#v-admin .pmfoldhd small{flex:none;white-space:nowrap}#v-admin .pmfoldhd .car{width:1em;color:var(--ink-2);flex:none}
#v-admin .pmfoldhd small{font-size:12.5px;color:var(--ink-2);font-weight:400}
#v-admin .pmfoldhd:hover h3,#v-admin .pmfoldhd:hover span:not(.car){color:var(--cyan)}
#v-admin .pmcat.shut .pmcathd{margin-bottom:0}
#v-admin .pmcat .grpch .pmfoldhd{font-size:13px;font-weight:600;color:var(--ink-2)}
#v-admin .pmcat .grpbody{grid-column:1/-1;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,230px),1fr));column-gap:14px}
#v-admin .pmcat .grpbody[hidden],#v-admin .pmbody[hidden]{display:none}
#v-admin .pmcat[data-cat=grp]{grid-column:1/-1}
#v-admin .pmcat .grpgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,230px),1fr));column-gap:14px}
#v-admin .pmcat .grpch{grid-column:1/-1;font-size:13px;color:var(--ink-2);margin:10px 0 2px;font-weight:600}
#v-admin .gico{display:inline-flex;vertical-align:-3px;margin-right:6px;color:var(--cyan);flex:none}
#v-admin .pmcat[data-cat=grp] .pmcathd{flex-wrap:wrap}#v-admin .pmcat[data-cat=grp] .pmfold{display:inline-flex;gap:6px;margin-left:auto}
#v-admin .pmfoldnote{margin:0 0 6px;font-size:12.5px}
#v-admin .pmcat .pmrow.sm{padding:5px 0;gap:8px}#v-admin .pmcat .pmrow.sm .pmtx b{font-size:13.5px;font-weight:500}
#v-admin .pmcathd{display:flex;align-items:center;gap:6px;flex-wrap:nowrap;margin-bottom:6px}#v-admin .pmcathd>button[data-all]{flex:none}
#v-admin .pmcathd h3{margin:0;min-width:0;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
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
#v-admin .pmlist th[data-sort]{cursor:pointer;user-select:none}#v-admin .pmlist th[data-sort]:hover{color:var(--ink)}
#v-admin .pmlist th.sorted{color:var(--ink);font-weight:700}
#v-admin .pmlist td small{display:block;font-size:12px;color:var(--ink-2)}#v-admin .pmlist tr.on td{background:color-mix(in srgb,var(--cyan) 12%,transparent)}
#v-admin .pmlist td.num{font-family:var(--mono);text-align:right}#v-admin .pmlist th.num{text-align:right}
#v-admin .stt{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;white-space:nowrap}
#v-admin .stt.ok{background:color-mix(in srgb,#35d07f 20%,transparent)}#v-admin .stt.exp{background:color-mix(in srgb,#ff6b7a 22%,transparent)}#v-admin .stt.new{background:var(--panel-3)}
#v-admin .pmcnt{font-size:13px;color:var(--ink-2)}#v-admin .pmbar input[type=search]{flex:1 1 220px;max-width:360px}
#v-admin .pmtpl{align-items:flex-start}#v-admin .pmtpl small{flex:1 1 260px;font-size:12.5px;color:var(--ink-2);line-height:1.5}#v-admin .pmtpl span{font-size:13px;color:var(--ink-2)}
#v-admin .pmtag.new{background:color-mix(in srgb,var(--cyan) 22%,transparent)}
#v-admin .pmsave{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);width:min(720px,calc(100vw - 32px));box-sizing:border-box;z-index:40;box-shadow:0 8px 24px rgba(0,0,0,.28);display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;border-radius:12px;
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
@media (max-width:600px){#v-admin .pmlist .c-exp,#v-admin .pmlist .c-n,#v-admin .pmlist .c-vis,#v-admin .pmlist .c-tpl{display:none}}
/* ---- admin-v3：三個大分頁＋子分頁、每列瀏覽次數、會員名單（memTable）---- */
#v-admin .ptsub{display:flex;gap:4px;margin:12px 0 0;border-bottom:1px solid var(--line-2)}
#v-admin .ptsub[hidden]{display:none}
#v-admin .ptsub button{height:36px;padding:0 16px;font-size:14.5px;background:none;border:0;border-bottom:3px solid transparent;color:var(--ink-2);cursor:pointer;margin-bottom:-1px}
#v-admin .ptsub button.on{color:var(--ink);border-bottom-color:var(--cyan);font-weight:700}
#v-admin .ptsub button small{font-family:var(--mono);font-size:12px;margin-left:6px;padding:0 6px;border-radius:8px;background:var(--panel-3)}
#v-admin .ptpick select{max-width:min(100%,360px)}#v-admin .ptwho{font-size:12.5px;color:var(--ink-2);flex:1 1 220px}
#v-admin .pmlimhelp{margin:4px 0 0}
#v-admin .pmlegend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:6px 0 0;font-size:12px;color:var(--ink-2)}
#v-admin .pmlegend span{display:inline-flex;align-items:center;gap:6px}
#v-admin .pmlegend .lg{display:inline-block;width:14px;height:12px;border-radius:3px;font:normal 11px/12px var(--mono);text-align:center}
#v-admin .pmlegend .lg.dirty{background:color-mix(in srgb,#f5a524 26%,transparent);box-shadow:inset 3px 0 0 #f5a524}
#v-admin .pmlegend .lg.tuned{box-shadow:inset 3px 0 0 #4c9dff;background:color-mix(in srgb,#4c9dff 10%,transparent)}
#v-admin .pmlegend .lg.lim{width:auto;padding:0 4px;color:var(--ink-3,#7a879c)}
#v-admin .pmrow{position:relative;border-radius:6px}
#v-admin .pmrow.tuned{box-shadow:inset 3px 0 0 #4c9dff;background:color-mix(in srgb,#4c9dff 7%,transparent)}
#v-admin .pmrow.dirty{box-shadow:inset 3px 0 0 #f5a524;background:color-mix(in srgb,#f5a524 16%,transparent)}
#v-admin .pmcards .pmrow,#v-admin .pmcats .pmrow{padding:6px 6px 6px 8px;gap:10px;grid-template-columns:44px minmax(0,1fr)}
#v-admin .pmcats .pmrow.wl{grid-template-columns:44px minmax(0,1fr) 44px}
#v-admin .pmcats .pmrow.wr{grid-template-columns:44px minmax(0,1fr) 44px}
#v-admin .pmcats .pmrow.wl.wr{grid-template-columns:44px minmax(0,1fr) 44px 44px}
#v-admin .pmcats .pmrow .pmtx b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
#v-admin .pmcats .pmrow.sel{grid-template-columns:76px minmax(0,1fr) 44px}#v-admin .pmcats .pmrow.sel.wr{grid-template-columns:76px minmax(0,1fr) 44px 44px}#v-admin .pmcats .pmrow.sel select{width:76px}
#v-admin .pmlimc,#v-admin .pmrevc{width:44px;display:flex;justify-content:center;min-width:0}
#v-admin .pmrevc .pmrev{font-size:11.5px;padding:0 4px;height:22px}
#v-admin .pmcats.pmcards{grid-template-columns:repeat(auto-fill,minmax(min(100%,260px),1fr));gap:12px;margin-top:10px}
#v-admin .pmcards .pmcat.card{padding:10px 12px;min-width:0}
#v-admin .pmcards .pmrow:first-of-type{border-top:0}
#v-admin .pmlimb{width:44px;box-sizing:border-box;text-align:center;font:500 11.5px var(--mono);line-height:20px;padding:0;border-radius:10px;border:1px solid transparent;background:transparent;color:var(--ink-3,#7a879c);opacity:.65;cursor:pointer;white-space:nowrap;overflow:hidden}
#v-admin .pmlimb:hover,#v-admin .pmlimb[aria-expanded=true]{opacity:1;border-color:var(--line-2)}
#v-admin .pmlimb.set{opacity:1;color:var(--ink);background:color-mix(in srgb,var(--cyan) 16%,transparent)}
#v-admin .pmlimb.zero{color:#ff6b7a;background:color-mix(in srgb,#ff6b7a 14%,transparent)}
#v-admin .pmlimb:disabled{cursor:not-allowed}
#v-admin .pmlimpop{position:absolute;right:0;bottom:calc(100% - 4px);z-index:30;display:flex;align-items:center;gap:6px;padding:6px 8px;font-size:12px;color:var(--ink-2);background:var(--panel);border:1px solid var(--line-2);border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.25);white-space:nowrap}
#v-admin .pmlimpop input{width:60px;height:26px;font:13px var(--mono);text-align:right;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:6px;padding:0 6px}
#v-admin .pmlimpop input.bad{border-color:#ff6b7a}
#v-admin .pmlimpop button{height:26px;font-size:12px;padding:0 8px;border-radius:6px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);cursor:pointer}
#v-admin .pmlimpop button.ok{background:var(--cyan);color:#06121f;border-color:transparent}

#v-admin #pmCats.card:has(.pmrow.wlim){grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr))}
#v-admin .pmrow.wlim{grid-template-columns:auto minmax(0,1fr) auto auto}
#v-admin .pmlimw{display:inline-flex;align-items:center;gap:4px;font-size:12px;color:var(--ink-2)}
#v-admin .pmlimw input{width:64px;height:28px;font:13px var(--mono);text-align:right;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:7px;padding:0 6px}
#v-admin .pmlimw input::placeholder{color:var(--ink-3,#7a879c);font-family:inherit}
#v-admin .pmlimw input.bad{border-color:#ff6b7a;box-shadow:0 0 0 1px #ff6b7a}
#v-admin .pmlimw.zero input{border-color:color-mix(in srgb,#ff6b7a 70%,transparent);color:#ff6b7a}
#v-admin .pmlimhd{font-size:12px;color:var(--ink-2);margin-left:auto;padding-left:8px;white-space:nowrap}
#v-admin .pmcathd .pmlimhd{flex:none}
#v-admin table.memtbl{table-layout:auto;font-size:13px}
#v-admin .memtbl th{white-space:nowrap!important}
#v-admin .memtbl td{vertical-align:top}
#v-admin .memtbl td.c-who b{font-weight:600;overflow-wrap:anywhere}
#v-admin .memtbl td.c-who .car{color:var(--ink-2);margin-right:4px}
#v-admin .memtbl tr.paid td.c-who{box-shadow:inset 3px 0 0 #e8b54a}
#v-admin .pdbadge{display:inline-block;margin-top:3px;font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;color:#2a1a00;background:linear-gradient(135deg,#ffd86b,#e8a93a);white-space:nowrap}
#v-admin .pdbadge.off{background:var(--panel-3);color:var(--ink-2);font-weight:500}
#v-admin .mchip{display:inline-flex;align-items:center;gap:4px;margin:0 4px 3px 0;padding:1px 7px;border-radius:8px;background:var(--panel-3);font-size:12px;white-space:nowrap}
#v-admin .mchip i{font-style:normal;font-family:var(--mono);color:var(--ink-2)}
#v-admin .mdim{color:var(--ink-3,#7a879c)}
#v-admin tr.pmdet td{background:color-mix(in srgb,var(--panel-2) 60%,transparent);cursor:default;padding:10px 12px}
#v-admin .mdet h4{margin:0 0 6px;font-size:13.5px}
#v-admin .mdgrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
#v-admin .mdays{display:flex;align-items:flex-end;gap:3px;height:70px;border-bottom:1px solid var(--line)}
#v-admin .mdays i{flex:1;background:var(--cyan);border-radius:3px 3px 0 0;min-width:4px}
#v-admin .bars.sm{grid-template-columns:minmax(0,9em) minmax(0,1fr) auto;font-size:12.5px;gap:4px 8px}
#v-admin .bars.sm .bt{height:10px}
@media (max-width:1320px){#v-admin .memtbl .c-cr{display:none}}
@media (max-width:1180px){#v-admin .memtbl .c-stk,#v-admin .memtbl .c-vw{display:none}#v-admin .mdgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:900px){#v-admin .memtbl .c-feat,#v-admin .memtbl .c-on,#v-admin .memtbl .c-seen{display:none}}
@media (max-width:600px){#v-admin .memtbl .c-tpl,#v-admin .memtbl .c-exp,#v-admin .memtbl .c-vis{display:none}#v-admin .mdgrid{grid-template-columns:minmax(0,1fr)}#v-admin .pmrow.wlim{grid-template-columns:auto minmax(0,1fr) auto}#v-admin .pmrow.wlim .pmside{display:none}}`;
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

  /* ---- 頂部：標題（＋三個子分頁 tab：2026-10-05 起桌機版搬到左側欄「管理區」底下的縮排子項，見 layout4.js syncPerm；
     頁內這排只在沒有左側欄的版面（≤820，layout4 沒啟用）才出現，免得那種寬度沒地方切子頁）。有沒存的權限草稿時，換分頁先問一次 */
  function head(v, A, extra) {
    const u = A.user() || {}, cur = tabOf();
    return `<div class="card" style="margin-top:16px"><div class="admtop"><h2>管理區</h2><small style="color:var(--ink-2)">${esc(u.email || '')}</small>
        ${document.documentElement.classList.contains('l4') ? '' : `<nav class="admnav" id="admTabs" aria-label="管理區分頁">${TABS.map(([k, n, id]) => `<a href="#admin/${k}" id="${id}" data-tab="${k}" class="${cur === k ? 'on' : ''}"${cur === k ? ' aria-current="page"' : ''}>${n}</a>`).join('')}</nav>`}
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
     #admin/perm 會員權限 與 #admin/members 會員管理 —— admin-v3（2026-10-05）簡化版
     Andy 看了 admin-v2 預覽：「弄得好複雜，看了不清楚」。改成：
       · 頂部只有三個大分頁：訪客｜註冊會員｜付費會員，旁邊一顆「＋」新增付費範本（名稱、價格 NT$、月訂閱或年訂閱）。
       · 付費會員分頁裡有多個範本時，用一個下拉選範本；名稱／價格／週期與「刪除」收在「⚙ 範本設定」裡（不再一大排按鈕）。
         拿掉：另存成新範本、一次建立定價範本、每個付費範本各一個大頁籤。
       · 每個分頁（付費會員＝每個範本）裡只有兩個子分頁：「觀看權限」「會員名單」（訪客沒有名單，改放訪客流量摘要）。
         觀看權限＝開放功能表（一張大卡、細線分隔、不收合）＋族群觀測（可收合）；**每個功能後面一格「瀏覽次數」**（每日上限，
         留空＝不限、0＝不能看；存在範本的 lims，套用在 perm.js／quota.js）。
         會員名單＝跟「會員管理」共用的名單元件（memTable）：付費會員金色徽章、加入／到期、最後上線、累計在線、
         近 30 天造訪、觀看次數、最常用的功能 Top3、最常看的股票 Top3、狀態；點一列原地展開那個人的使用明細。
     資料怎麼合：features.js 的預設值 ← 方案範本 ← 個別微調（後面蓋前面）；到期日過了就退回「註冊會員」（Worker 端判斷）。
     撥開關、改次數只是「草稿」，按底部「儲存」才送出，「取消」整批放棄；有沒存的變更時，換分頁／換範本／換人都會先問一次。
     範本只存「跟預設不同」的項目、微調只存「跟範本不同」的項目 —— 之後新增功能時，沒人設過的一律照預設（開、不限）。
     ========================================================================== */
  const PS = { mode: 'member', tab: 'members', tier: 'guest', sub: 'perm', email: '', rec: null, plans: [], planSel: 'guest', list: null, mem: null,
    confirmDel: false, A: null, v: null, seq: 0, draft: null, q: '', sort: 'seen', dir: -1, stf: '', adding: false, cfg: false, exp: new Set(), det: {} };
  const FT = () => window.TwFeatures;
  const tpeTime = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(11, 19);
  const PERIOD = { month: '月', year: '年', once: '一次' };
  /* 「基本方案・NT$399/月」；一次付清（舊資料）寫「NT$399（一次）」；沒有價格欄（舊 Worker）就只寫名稱 */
  const priceTxt = (p) => (p && Number.isInteger(p.price) ? `NT$${p.price.toLocaleString('en-US')}${p.period === 'once' ? '（一次）' : '/' + (PERIOD[p.period] || '月')}` : '');
  const planLabel = (p) => (p ? p.name + (priceTxt(p) ? '・' + priceTxt(p) : '') : '');
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
  /* 瀏覽次數上限（只有範本有；逐人微調不改上限 —— 人跟著範本走，Worker 的 /v1/perm/me 也是回範本的 lims）*/
  const savedLims = () => ((planOf(PS.planSel) || {}).lims || {});
  const curLims = () => (PS.draft && PS.draft.lims) || savedLims();
  const diffKeys = (a, b) => new Set([...Object.keys(a || {}), ...Object.keys(b || {})].filter((k) => (a || {})[k] !== (b || {})[k])).size;
  function dirtyN() {
    const d = PS.draft; if (!d) return 0;
    if (PS.mode === 'plan') { const p = planOf(PS.planSel) || {}; return diffKeys(p.feats || {}, d.feats || {}) + diffKeys(p.lims || {}, d.lims || {}); }
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
  const ERR = { forbidden: '沒有管理者權限', bad_email: 'email 格式不對', bad_plan: '方案不存在', bad_feats: '開關格式不對', bad_lims: '瀏覽次數要是 0～9999 的整數', bad_name: '範本名稱不能空白', too_many: '數量超過上限', builtin: '內建範本不能刪', bad_expires: '到期日格式不對', bad_price: '價格要是 0～999999 的整數', bad_period: '計費週期只能是月／年' };
  const errText = (r) => !r ? '連不到伺服器' : (ERR[r.error] || ('HTTP ' + r._s));
  const EMAIL_OK = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
  /* 到期日：畫面上是台北日期（yyyy-mm-dd），存的是「那一天台北 23:59:59」的毫秒 */
  const expToMs = (s) => { if (!s) return null; const t = Date.parse(s + 'T23:59:59+08:00'); return isFinite(t) ? t : null; };
  const msToDate = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10) : '');
  const honest = `<div class="card" style="margin-top:14px"><h3>這個鎖頭擋得住什麼？</h3><p class="pmwarn">鎖頭只擋一般使用者的畫面。這個網站是 GitHub Pages 靜態站，資料檔（site/data/*.json）是公開的，懂技術的人仍然能直接讀到。
        真正保護付費內容，要讓付費資料改由會員 Worker 驗證身分後才提供 —— 設計與工作量寫在 DECISIONS #288，這一版還沒做。</p></div>`;
  /* 在線時間：「3 小時 12 分」「45 分」「—」 */
  const dur = (ms) => { if (!ms) return '—'; const m = Math.round(ms / 60000); if (m < 1) return '< 1 分'; const h = Math.floor(m / 60); return h ? `${h} 小時${m % 60 ? ' ' + (m % 60) + ' 分' : ''}` : m + ' 分'; };

  const GRPSEC = `<div class="secttl" id="pmGrpTtl"><h2>族群觀測</h2><small id="pmGrpCnt"></small><span class="pmfold"><button type="button" id="pmExpandAll">全部展開</button><button type="button" id="pmCollapseAll">全部收合</button></span></div>
        <div class="pmcats pmgrpbox card" id="pmGrp"></div>`;
  async function renderPerm(v, A, tab) {
    PS.v = v; PS.A = A; PS.draft = null; PS.tab = tab;
    PS.mode = tab === 'perm' ? 'plan' : 'member';
    if (tab === 'perm') {
      v.innerHTML = head(v, A) + `<p class="use" style="margin:8px 0 0">三個大分頁對應三種人。每一頁兩件事：<b>觀看權限</b>（哪些功能開、每天能看幾次）與<b>會員名單</b>（誰在這一層、用得多不多）。
          關掉的功能在對方畫面上模糊並蓋鎖頭，鎖頭上有「升級查看」直接帶到訂閱頁。</p></div>
        <div class="card" id="pmHead" style="margin-top:14px">
          <div class="ptabs" id="ptTier" role="tablist" aria-label="要設定哪一種人"></div>
          <div class="ptpanel">
            <div id="pmTarget"></div>
            <div class="ptsub" id="ptSub" role="tablist" aria-label="子分頁"></div>
            <div class="pmstat" id="pmStat" role="status" aria-live="polite"></div></div></div>
        <div id="ptPermBox">
          <div id="ptGuestSum"></div>
          <div class="secttl"><h2>開放功能表</h2><small id="ptFor"></small></div>
          <p class="use pmlimhelp">每一列：左邊開關＝能不能看；名稱旁的小徽章＝每天最多看幾次（<b>∞＝不限</b>，點一下可設定；<b>0＝不能看</b>；名稱旁小圓點＝跟預設不同；個股頁、題材、族群頁算「看了幾個不同的」，其他頁算「開了幾次」）。超過的人會看到「今日已用完」與升級鈕。</p>
          <div class="pmlegend"><span><i class="lg dirty"></i>改了還沒儲存</span><span><i class="lg tuned"></i>跟預設不同（已儲存）</span><span><i class="lg lim">∞</i>每日次數，點一下設定</span></div>
          <div class="pmcats pmcards" id="pmCats"></div>
          ${GRPSEC}</div>
        <div id="ptListBox" hidden></div>
        <div class="pmsave" id="pmSave" hidden><span id="pmDirty"></span><button type="button" id="pmCancel">取消</button><button type="button" class="pri" id="pmSaveGo">儲存</button></div>
        ${honest}`;
      v.querySelector('#ptTier').onclick = (e) => {
        const b = e.target.closest('button[role=tab]'); if (!b) return;
        if (b.id === 'ptAddTab') { if (PS.adding || !guard()) return; PS.adding = true; PS.cfg = false; PS.confirmDel = false; paintAll(); setStat(''); return; }
        const tier = b.dataset.tier;
        if (!PS.adding && tier === PS.tier) return;
        if (!guard()) return;
        PS.adding = false; PS.cfg = false; PS.tier = tier; PS.confirmDel = false; pickTierPlan();
        if (tier === 'guest') PS.sub = 'perm';
        paintAll(); setStat('');
      };
      v.querySelector('#ptSub').onclick = (e) => {
        const b = e.target.closest('button[data-sub]'); if (!b || b.dataset.sub === PS.sub) return;
        PS.sub = b.dataset.sub; paintSub();
      };
    } else {
      v.innerHTML = head(v, A) + `<p class="use" style="margin:8px 0 0">收費會員在這裡開通：新增他的 email、選層級／範本、設到期日（到期自動退回註冊會員）。下面的名單是所有人員的狀況，點一列展開他的使用紀錄，並在最下面逐項微調。</p></div>
        <div class="card" id="pmAdd" style="margin-top:14px"><h3>① 新增會員</h3>
          <p class="use">輸入對方登入用的 Google email、選層級（付費會員要選範本）、需要的話填到期日，按「新增」。對方還沒登入過也可以先設好，登入後就生效。</p>
          <div class="pmbar"><input type="email" id="pmAddEmail" placeholder="member@example.com" autocomplete="off" aria-label="新會員 email">
            <select id="pmAddPlan" aria-label="新會員的層級與範本"></select>
            <label>到期日 <input type="date" id="pmAddExp" aria-label="到期日（留空＝不會到期）"></label>
            <button type="button" class="pri" id="pmAddGo">新增</button></div></div>
        <div class="card" id="pmList" style="margin-top:14px"><h3>② 所有人員狀況</h3><p class="use">金色徽章＝付費會員（後面是方案名）。點欄位標題排序；點一列展開他的使用紀錄（各分頁瀏覽、功能次數、近 14 天每日活躍），同時在下面「③ 逐人微調」載入他。</p>
          <div class="pmbar"><input type="search" id="pmSearch" placeholder="搜尋 email、名字、層級或範本" aria-label="搜尋會員" value="${esc(PS.q)}">
            <select id="pmStatF" aria-label="依狀態篩選"><option value="">全部狀態</option><option value="ok">有效</option><option value="exp">過期</option><option value="new">未登入過</option></select><span class="pmcnt" id="pmCnt"></span></div>
          <div id="pmListBody"><div class="empty">載入中…</div></div></div>
        <div class="card" id="pmHead" style="margin-top:14px"><h3>③ 逐人微調</h3>
          <p class="use">先選層級／範本，再個別微調。開關撥完按最下面的「儲存」才會生效。瀏覽次數跟著範本走（在「會員權限」設）。</p>
          <div id="pmTarget"></div>
          <div class="pmstat" id="pmStat" role="status" aria-live="polite"></div></div>
        <div class="pmlegend"><span><i class="lg dirty"></i>改了還沒儲存</span><span><i class="lg tuned"></i>跟預設不同（已儲存）</span><span><i class="lg lim">∞</i>每日次數，點一下設定</span></div>
          <div class="pmcats pmcards" id="pmCats"></div>
        ${GRPSEC}
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
    const [pl, li, mm] = await Promise.all([A.call('/v1/admin/plans/get', {}), A.call('/v1/admin/perm/list', {}), A.call('/v1/admin/members', {})]);
    if (tabOf() !== tab) return;
    if (!pl || pl._s !== 200) {
      v.querySelector('#pmCats').innerHTML = `<div class="card" style="grid-column:1/-1"><p class="err">讀不到方案範本（${esc(errText(pl))}）。${pl && pl._s === 404 ? '會員 Worker 可能還沒更新成有功能權限的版本（deploy-account-worker.yml）。' : '只有管理者帳號看得到；確認 Worker 的 ADMIN_EMAILS 有你的 email。'}</p></div>`;
      return;
    }
    PS.plans = pl.plans || [];
    PS.list = li && li._s === 200 ? li : { rows: [], users: [] };
    PS.mem = mm && mm._s === 200 && Array.isArray(mm.members) ? mm : null;
    if (tab === 'perm') pickTierPlan();
    paintAll();
    if (PS.mode === 'member' && PS.email) loadMember(PS.email);
  }
  function paintAll() { paintTabs(); paintAddPlan(); paintTarget(); paintSub(); paintCats(); paintList(); }
  /* 層級 → 要編的範本：訪客＝guest、註冊會員＝free、付費＝下拉選的那個（沒有就第一個；一個都沒有＝付費分頁只顯示「按＋新增」）*/
  function pickTierPlan() {
    if (PS.tier === 'guest') PS.planSel = 'guest';
    else if (PS.tier === 'free') PS.planSel = 'free';
    else { const pp = paidPlans(); if (!pp.some((p) => p.id === PS.planSel)) PS.planSel = pp.length ? pp[0].id : ''; }
  }
  function paintTabs() {
    const bar = PS.v && PS.v.querySelector('#ptTier'); if (!bar) return;
    const all = members();
    const nPaid = all.filter((r) => r.tier === 'paid').length, nReg = all.filter((r) => r.st !== 'new').length;
    const t = (tier, label, sub) => { const on = !PS.adding && PS.tier === tier;
      return `<button type="button" role="tab" aria-selected="${on}" class="${on ? 'on' : ''}" data-tier="${tier}"><span>${label}</span><small>${sub}</small></button>`; };
    bar.innerHTML = t('guest', '訪客', '沒登入的人') + t('free', '註冊會員', nReg + ' 人') + t('paid', '付費會員', `${paidPlans().length} 個範本・${nPaid} 人`)
      + `<button type="button" role="tab" id="ptAddTab" aria-selected="${!!PS.adding}" class="add${PS.adding ? ' on' : ''}" aria-label="新增付費範本" title="新增付費範本（名稱、價格、月／年訂閱）">＋</button>`;
  }
  function planOpts(sel, withGuest) {
    const pp = paidPlans();
    return (withGuest ? `<option value="guest" ${sel === 'guest' ? 'selected' : ''}>訪客</option>` : '')
      + `<option value="free" ${sel === 'free' ? 'selected' : ''}>註冊會員</option>`
      + (pp.length ? `<optgroup label="付費會員">${pp.map((p) => `<option value="${esc(p.id)}" ${p.id === sel ? 'selected' : ''}>付費：${esc(planLabel(p))}</option>`).join('')}</optgroup>` : '');
  }
  function paintAddPlan() {
    const s = PS.v && PS.v.querySelector('#pmAddPlan'); if (!s) return;
    s.innerHTML = planOpts(s.value || 'free', false);
  }
  /* 合併「設定過的（perm）」與「登入過的（users）」→ 一人一列，帶狀態 */
  function people() {
    const now = (PS.list && PS.list.now) || Date.now();
    const users = new Map(((PS.list && PS.list.users) || []).map((u) => [u.email, u]));
    const all = ((PS.list && PS.list.rows) || []).map((r) => { const u = users.get(r.email) || {}; return Object.assign({ set: true }, r, { name: u.name || '', seen: r.seen || u.seen || 0, created: u.created || 0, visits: u.visits || 0, known: users.has(r.email) }); });
    const have = new Set(all.map((r) => r.email));
    users.forEach((u, e) => { if (e && !have.has(e)) all.push({ email: e, name: u.name || '', plan: 'free', n: 0, updated: 0, expires: 0, seen: u.seen || 0, created: u.created || 0, visits: u.visits || 0, set: false, known: true }); });
    all.forEach((r) => {
      r.tier = tierOf(r.plan);
      r.st = r.expires && r.expires < now ? 'exp' : (r.known ? 'ok' : 'new');
    });
    return all;
  }
  /* 名單的每一列 = people() ＋ /v1/admin/members 的使用數據（新 Worker 才有；舊的就只有造訪次數）*/
  function members() {
    const st = new Map(((PS.mem && PS.mem.members) || []).map((m) => [m.email, m]));
    return people().map((r) => {
      const m = st.get(r.email) || {};
      return Object.assign(r, { paid: r.tier === 'paid' && r.st !== 'exp', planName: (planOf(r.plan) || {}).name || r.plan,
        onlineMs: m.onlineMs || 0, online30: m.online30 || 0, visits30: m.visits30 != null ? m.visits30 : r.visits || 0, days30: m.days30 || 0,
        views30: m.views30 || 0, topFeat: m.topFeat || [], topStock: m.topStock || [], hasStats: !!st.size });
    });
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
        <div class="pmwho" id="pmWho">${r ? whoLine(r) : '從上面的名單點一位會員，或在這裡輸入 email 按「讀取」。'}</div>
        ${r ? `<div class="pmbar"><label>層級／範本 <select id="pmPlan">${planOpts(mPlan(), false)}</select></label>
          <label>到期日 <input type="date" id="pmExp" value="${msToDate(mExp())}" aria-label="到期日（留空＝不會到期）"></label>
          <button type="button" id="pmClearOver" ${Object.keys(mOver()).length ? '' : 'disabled'}>清除個別微調</button>
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
      paintSave(); return;
    }
    const forEl = v.querySelector('#ptFor');
    if (PS.adding) {
      box.innerHTML = `<div class="pmwho"><b>新增付費範本</b>：填名稱、價格、月訂閱或年訂閱，按「建立」。建立後一開始全開、不限次數，再到「觀看權限」關掉這個價位不給的功能。</div>
        <div class="pmbar" id="ptNewForm"><label>名稱 <input type="text" id="ptNewName" maxlength="20" placeholder="例如 進階方案" aria-label="新付費範本名稱" style="width:12em"></label>
          <label>價格 NT$ <input type="number" id="ptNewPrice" min="0" max="999999" step="1" inputmode="numeric" value="0" aria-label="價格（整數新台幣）" style="width:7em"></label>
          <label>訂閱 <select id="ptNewPeriod" aria-label="月訂閱或年訂閱"><option value="month">月訂閱</option><option value="year">年訂閱</option></select></label>
          <button type="button" class="pri" id="ptNewGo">建立</button><button type="button" id="ptNewCancel">取消</button></div>`;
      if (forEl) forEl.textContent = '';
      const nn = v.querySelector('#ptNewName');
      v.querySelector('#ptNewGo').onclick = () => newPaidPlan(nn.value);
      nn.onkeydown = (e) => { if (e.key === 'Enter') newPaidPlan(nn.value); };
      v.querySelector('#ptNewCancel').onclick = () => { PS.adding = false; paintAll(); };
      paintSave(); return;
    }
    const p = planOf(PS.planSel);
    if (PS.tier === 'paid') {
      const pp = paidPlans();
      box.innerHTML = pp.length ? `<div class="pmbar ptpick"><label>範本 <select id="ptPlanSel" aria-label="選付費範本">${pp.map((x) => `<option value="${esc(x.id)}" ${x.id === PS.planSel ? 'selected' : ''}>${esc(planLabel(x))}（${x.members || 0} 人）</option>`).join('')}</select></label>
            <button type="button" id="ptPlanCfg" aria-expanded="${PS.cfg}">⚙ 範本設定</button><small class="ptwho">被指定這個範本的會員都套這一份；到期的人自動退回註冊會員。</small></div>
          ${PS.cfg && p ? `<div class="pmbar pmed" id="ptEdit"><label>名稱 <input type="text" id="ptEdName" maxlength="20" value="${esc(p.name)}" aria-label="範本名稱" style="width:10em"></label>
            <label>價格 NT$ <input type="number" id="ptEdPrice" min="0" max="999999" step="1" inputmode="numeric" value="${Number.isInteger(p.price) ? p.price : 0}" aria-label="價格（整數新台幣）" style="width:7em"></label>
            <label>訂閱 <select id="ptEdPeriod" aria-label="月訂閱或年訂閱"><option value="month" ${p.period !== 'year' ? 'selected' : ''}>月訂閱</option><option value="year" ${p.period === 'year' ? 'selected' : ''}>年訂閱</option></select></label>
            <button type="button" class="pri" id="ptEdSave">儲存</button>
            <button type="button" class="danger" id="pmPlanDel" title="用這個範本的會員會退回註冊會員">刪除這個範本</button>
            <small>金流以範本代號 <code>${esc(p.id)}</code> 對價；改名、改價不影響已指定的會員。</small></div>` : ''}`
        : '<div class="pmwho">還沒有付費範本 —— 按右上的「＋」新增（填名稱、價格、月或年訂閱）。</div>';
      const sel = v.querySelector('#ptPlanSel');
      if (sel) sel.onchange = () => { if (!guard()) { sel.value = PS.planSel; return; } PS.planSel = sel.value; PS.confirmDel = false; paintTarget(); paintCats(); paintList(); setStat(''); };
      const cf = v.querySelector('#ptPlanCfg'); if (cf) cf.onclick = () => { PS.cfg = !PS.cfg; PS.confirmDel = false; paintTarget(); };
      const es = v.querySelector('#ptEdSave'); if (es) es.onclick = () => savePlanMeta(p);
      const del = v.querySelector('#pmPlanDel');
      if (del) del.onclick = async () => {
        if (!PS.confirmDel) { PS.confirmDel = true; del.textContent = '確定刪除？（再按一次）'; return; }
        PS.confirmDel = false;
        const nm = p.name;
        const j = await PS.A.call('/v1/admin/plans/put', { id: PS.planSel, del: true });
        if (j && j._s === 200) { PS.plans = j.plans; PS.draft = null; PS.cfg = false; pickTierPlan(); paintAll(); setStat(`已刪除「${nm}」；原本用它的會員退回「註冊會員」（個別微調保留）`, 'ok'); refreshList(); }
        else setStat('刪除失敗：' + errText(j), 'bad');
      };
    } else {
      box.innerHTML = `<div class="pmwho">${PS.tier === 'guest' ? '<b>訪客</b>：所有沒登入的人都套這一份。' : '<b>註冊會員</b>：登入後沒被指定付費範本的人（以及付費到期的人）都套這一份。'}</div>`;
    }
    if (forEl) forEl.textContent = p ? `正在編：${TIER_NAME[PS.tier]}${PS.tier === 'paid' ? '・' + p.name : ''}` : '';
    paintSave();
  }
  /* 子分頁：觀看權限｜會員名單（訪客：觀看權限｜—，名單換成流量摘要放在觀看權限上方）*/
  function paintSub() {
    const v = PS.v, bar = v && v.querySelector('#ptSub'); if (!bar) return;
    const noPlan = PS.adding || (PS.tier === 'paid' && !planOf(PS.planSel));
    if (PS.tier === 'guest') PS.sub = 'perm';
    bar.hidden = noPlan;
    bar.innerHTML = `<button type="button" role="tab" data-sub="perm" id="ptSubPerm" class="${PS.sub === 'perm' ? 'on' : ''}" aria-selected="${PS.sub === 'perm'}">觀看權限</button>`
      + (PS.tier === 'guest' ? '' : `<button type="button" role="tab" data-sub="list" id="ptSubList" class="${PS.sub === 'list' ? 'on' : ''}" aria-selected="${PS.sub === 'list'}">會員名單<small>${listRows().length}</small></button>`);
    const pb = v.querySelector('#ptPermBox'), lb = v.querySelector('#ptListBox');
    if (pb) pb.hidden = noPlan || PS.sub !== 'perm';
    if (lb) lb.hidden = noPlan || PS.sub !== 'list';
    paintGuestSum();
    paintList();
  }
  /* 訪客分頁的流量摘要：近 30 天開啟網站（登入／訪客）、頁面瀏覽、目前在線的訪客 */
  async function paintGuestSum() {
    const box = PS.v && PS.v.querySelector('#ptGuestSum'); if (!box) return;
    if (PS.tier !== 'guest' || PS.adding) { box.innerHTML = ''; return; }
    box.innerHTML = `<div class="card" id="ptGuestCard" style="margin-top:14px"><h3>訪客整體流量（近 30 天）</h3><p class="use">訪客不記名，只有總數。訪客比例高 → 登入的好處說得不夠清楚；下面關掉的功能，就是訪客想看卻要先登入／升級的東西。</p><div class="kpis" id="ptGuestKpi"><div><b>…</b>載入中</div></div></div>`;
    const [st, on] = await Promise.all([PS.A.call('/v1/admin/stats', { days: 30 }), PS.A.call('/v1/admin/online', {})]);
    const k = PS.v && PS.v.querySelector('#ptGuestKpi'); if (!k || PS.tier !== 'guest') return;
    if (!st || st._s !== 200) { k.innerHTML = `<div class="err">讀不到流量（${esc(errText(st))}）</div>`; return; }
    let ses = 0, sl = 0, pv = 0;
    (st.rows || []).forEach((r) => { if (r.k === 'ev:session') ses += r.n; else if (r.k === 'ev:session_login') sl += r.n; else if (String(r.k).startsWith('pv:')) pv += r.n; });
    const g = Math.max(0, ses - Math.min(sl, ses));
    k.innerHTML = `<div><b>${nf(g)}</b>訪客開啟網站</div><div><b>${ses ? Math.round(g / ses * 100) : 0}%</b>佔全部開啟</div><div><b>${nf(pv)}</b>全站頁面瀏覽</div><div><b>${on && on._s === 200 ? nf(on.guests) : '—'}</b>目前在線訪客</div>`;
  }
  /* 範本的名稱／價格／月或年：前端先擋一次（整數 0～999999），後端再驗一次（worker.js adminPlansPut）。
     只送這三欄＋目前存好的開關與次數（沒存的草稿不會被偷偷一起存掉 —— 有草稿就先請他存或取消）。 */
  async function savePlanMeta(p) {
    const v = PS.v; if (!p) return;
    const name = String(v.querySelector('#ptEdName').value || '').trim();
    const raw = String(v.querySelector('#ptEdPrice').value || '').trim(), price = Number(raw);
    const period = v.querySelector('#ptEdPeriod').value;
    if (!name) { setStat('範本名稱不能空白', 'bad'); return; }
    if (!/^\d{1,6}$/.test(raw) || !Number.isInteger(price) || price > 999999) { setStat('價格要是 0～999999 的整數（新台幣，不含小數）', 'bad'); return; }
    if (PS.draft) { setStat('觀看權限還有沒存的變更 —— 先按下面「儲存」或「取消」，再改範本設定', 'bad'); return; }
    setStat('儲存中…');
    const j = await PS.A.call('/v1/admin/plans/put', { id: p.id, name, feats: p.feats || {}, price, period });
    if (j && j._s === 200) { PS.plans = j.plans; paintTabs(); paintAddPlan(); paintTarget(); paintCats(); setStat(`已儲存「${planLabel(planOf(p.id))}」（台北 ${tpeTime()}）`, 'ok'); }
    else setStat('儲存失敗：' + errText(j), 'bad');
  }
  async function newPaidPlan(name) {
    const v = PS.v; name = String(name || '').trim();
    if (!name) { setStat('先輸入新範本的名稱（例如 進階方案）', 'bad'); return; }
    const pe = v.querySelector('#ptNewPrice'), raw = String((pe && pe.value) || '0').trim(), price = Number(raw);
    if (!/^\d{1,6}$/.test(raw) || !Number.isInteger(price) || price > 999999) { setStat('價格要是 0～999999 的整數（新台幣，不含小數）', 'bad'); return; }
    const period = (v.querySelector('#ptNewPeriod') || {}).value === 'year' ? 'year' : 'month';
    if (!guard()) return;
    const id = 'p' + Date.now().toString(36).slice(-7);
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats: {}, lims: {}, price, period });
    if (!j || j._s !== 200) { setStat('新增失敗：' + errText(j), 'bad'); return; }
    PS.plans = j.plans; PS.tier = 'paid'; PS.planSel = id; PS.draft = null; PS.adding = false; PS.sub = 'perm';
    paintAll(); setStat(`已新增付費範本「${planLabel(planOf(id)) || name}」（目前全開、不限次數；下面關掉這個價位不給的功能）`, 'ok');
  }
  function whoLine(r) {
    const n = Object.keys(mOver()).length, p = planOf(mPlan()), ex = mExp();
    const who = r.known ? `已登入過：<b>${esc(r.known.name || '')}</b>${r.known.seen ? `（最後登入 ${dstr(r.known.seen)}）` : ''}` : '<b>尚未登入過</b>（先設好，對方登入後就生效）';
    const exs = ex ? (ex < Date.now() ? `・<b style="color:#ff6b7a">已於 ${msToDate(ex)} 到期</b>（目前套註冊會員）` : `・到期 <b>${msToDate(ex)}</b>`) : '';
    return `<b>${esc(r.email)}</b>・${who}・${TIER_NAME[tierOf(mPlan())]}「<b>${esc(p ? p.name : (r.planName || r.plan))}</b>」${exs}・個別微調 <b>${n}</b> 項${r.set ? '' : '（還沒個別設定過＝照免費會員）'}`;
  }
  function paintSave() {
    const bar = PS.v && PS.v.querySelector('#pmSave'); if (!bar) return;
    const n = dirtyN();
    bar.hidden = !n;
    const who = PS.mode === 'plan' ? `${TIER_NAME[PS.tier]}「${(planOf(PS.planSel) || {}).name || ''}」` : (PS.rec ? PS.rec.email : '');
    bar.querySelector('#pmDirty').innerHTML = n ? `<b>${n}</b> 項變更還沒儲存・${esc(who)}` : '';
  }

  /* 族群小圖示（admin-v2c）：站上沒有「族群 → 圖示」的現成表（icons.js 是依卡片標題配圖），所以重用 icons.js 的圖示庫（TwIcons.svg，
     同一套線條圖、stroke=currentColor 深淺主題都跟字色走），用族群名稱關鍵字挑；比不中就用所屬產業鏈的預設圖示。 */
  const GICON = [[/記憶體|HBM|CXL|NOR/i, 'layers'], [/IC|晶圓|半導體|矽|封測|封裝|ASIC|CPU|光感測/i, 'cpu'], [/伺服器|雲端|MSP|SaaS|資安|軟體|資訊服務|數位/i, 'server'],
    [/PCB|載板|基板|軟板|CCL|銅箔|玻纖/i, 'board'], [/光|CPO|交換器|網路|網通|互連|連接器|電信|衛星|通信/i, 'network'], [/散熱|液冷|氣冷/i, 'waves'],
    [/電源|電池|BBU|儲能|電力|重電|風電|太陽能|電纜|油電|燃氣|電芯/i, 'zap'], [/金控|銀行|證券|壽險|金融|ETF/i, 'landmark'], [/航運|空運|陸運|宅配/i, 'compass'],
    [/設備|機台|自動化|工具機|機械|廠務|機殼|滑軌|機構/i, 'hammer'], [/營建|地產|水泥|鋼鐵|玻璃陶瓷/i, 'building'], [/綠能|環保|農業|生技|醫療|食品/i, 'leaf'],
    [/百貨|零售|電商|觀光|餐旅|居家|運動|文化|紡織/i, 'shopping'], [/石化|塑膠|化學|造紙|橡膠|材料|化學品/i, 'factory'], [/國防/i, 'target']];
  const CHICON = { semiconductor: 'cpu', ai_server: 'server', electronics: 'board', traditional: 'factory', infrastructure: 'zap', software: 'code', financial: 'landmark', industry: 'box' };
  function grpIcon(f) {
    const I = window.TwIcons; if (!I || !I.svg) return '';
    const r = GICON.find((x) => x[0].test(f.name || '')); const k = r ? r[1] : (CHICON[f.chain] || 'box');
    return `<span class="gico" data-ico="${k}">${I.svg(k, 16)}</span>`;
  }
  function catRows(fs, cur, base, saved, now, ready, compact) {
    const lims = PS.mode === 'plan' ? curLims() : null, sl = PS.mode === 'plan' ? savedLims() : null;
    return fs.map((f) => {
      const val = cur[f.id], diff = PS.mode === 'member' ? (PS.rec && Object.prototype.hasOwnProperty.call(mOver(), f.id)) : val !== f.def;
      const unsaved = ready && (saved[f.id] !== now[f.id] || (lims && sl[f.id] !== lims[f.id]));
      const ctl = f.kind === 'limit'
        ? `<select data-f="${esc(f.id)}" aria-label="${esc(f.name)}" ${ready ? '' : 'disabled'}>${Array.from({ length: f.max + 1 }, (_, i) => `<option value="${i}" ${i === val ? 'selected' : ''}>${i === 0 ? '不能用' : i + ' 頁'}</option>`).join('')}</select>`
        : `<label class="psw"><input type="checkbox" role="switch" data-f="${esc(f.id)}" aria-label="${esc(f.name)}" ${val !== false ? 'checked' : ''} ${ready ? '' : 'disabled'}><span></span></label>`;
      /* 瀏覽次數（每日上限）：perm-cards（2026-10-05）改成名稱右側一顆小徽章（∞／N/日），點了才彈出小輸入框 ——
         Andy 要回到「每類一張卡、每列只有開關＋名稱＋一行說明」的乾淨版，但次數上限功能不能丟，所以不讓它常駐佔一欄。 */
      const has = lims && Object.prototype.hasOwnProperty.call(lims, f.id), lv = has ? lims[f.id] : '';
      const limOpen = lims && PS.limOpen === f.id;
      const badge = lims && f.kind !== 'limit' ? `<button type="button" class="pmlimb${has ? ' set' : ''}${lv === 0 ? ' zero' : ''}" data-limb="${esc(f.id)}" title="每日瀏覽次數上限（點一下設定）" aria-label="${esc(f.name)} 每日瀏覽次數：${has ? lv + ' 次' : '不限'}" aria-expanded="${limOpen}" ${ready ? '' : 'disabled'}>${has ? lv + '/日' : '∞'}</button>` : '';
      const pop = limOpen && f.kind !== 'limit' ? `<div class="pmlimpop" role="dialog" aria-label="${esc(f.name)} 每日瀏覽次數"><span>每日最多</span><input type="number" class="pmlim" data-lim="${esc(f.id)}" min="0" max="9999" step="1" inputmode="numeric" placeholder="不限" value="${lv === '' ? '' : lv}" aria-label="${esc(f.name)} 每日瀏覽次數上限（留空＝不限）"><span>次</span><button type="button" data-limclr="${esc(f.id)}">不限</button><button type="button" class="ok" data-limok="1">確定</button></div>` : '';
      /* 改動用顏色表示、不用文字標籤（Andy 10-05 追加）：未存＝淡琥珀底＋左色條（.dirty）、已存的微調／改過＝淡藍左色條（.tuned）。
         色條用 inset box-shadow 畫，不加 padding —— 撥開關前後版面一像素都不能動。 */
      const rev = PS.mode === 'member' ? `<span class="pmrevc">${diff ? `<button type="button" class="pmrev" data-rev="${esc(f.id)}" title="還原成範本（範本是${base[f.id] === false ? '關' : base[f.id] === true ? '開' : base[f.id]}）">還原</button>` : ''}</span>` : '';
      const limc = lims ? `<span class="pmlimc">${badge}</span>` : '';
      return `<div class="pmrow${compact ? ' sm' : ''}${unsaved ? ' dirty' : ''}${diff ? ' tuned' : ''}${lims ? ' wl' : ''}${f.kind === 'limit' ? ' sel' : ''}${PS.mode === 'member' ? ' wr' : ''}" data-f="${esc(f.id)}">${ctl}<div class="pmtx"><b>${compact ? grpIcon(f) : ''}<span class="pmnm">${esc(f.name)}</span></b>${compact ? '' : `<small>${esc(f.desc)}</small>`}</div>${limc}${rev}${pop}</div>`;
    }).join('');
  }
  function paintCats() {
    const v = PS.v, box = v.querySelector('#pmCats'); if (!box || !FT()) return;
    const ready = PS.mode === 'plan' ? !!planOf(PS.planSel) : !!PS.rec;
    const cur = curVals(), base = baseVals();
    const saved = PS.mode === 'plan' ? ((planOf(PS.planSel) || {}).feats || {}) : ((PS.rec && PS.rec.over) || {});
    const now = PS.mode === 'plan' ? ((PS.draft && PS.draft.feats) || saved) : mOver();
    box.classList.toggle('off', !ready);
    /* 一般功能：每個分類各一張卡、四欄格狀（perm-cards 2026-10-05，Andy 要回 10-04 第一版的樣子）；族群觀測：整塊預設收合、每個產業鏈分組各自可收合 */
    const cats = FT().cats.filter((c) => FT().inCat(c.id).length);
    if (!PS.open) PS.open = new Set();
    const isOn = (f) => (f.kind === 'limit' ? cur[f.id] > 0 : cur[f.id] !== false);
    const cnt = (fs) => `${fs.length} 項・開 ${fs.filter(isOn).length}`;
    const fold = (k, label, fs, tag) => { const o = PS.open.has(k);
      return `<button type="button" class="pmfoldhd" data-fold="${esc(k)}" aria-expanded="${o}"><span class="car" aria-hidden="true">${o ? '▾' : '▸'}</span><${tag}>${esc(label)}</${tag}><small>${cnt(fs)}</small></button>`; };
    const allBtns = (id) => `<button type="button" data-all="1" data-cat="${esc(id)}" ${ready ? '' : 'disabled'}>全開</button><button type="button" data-all="0" data-cat="${esc(id)}" ${ready ? '' : 'disabled'}>全關</button>`;
    const gbox = v.querySelector('#pmGrp');
    if (gbox) gbox.classList.toggle('off', !ready);
    box.innerHTML = cats.filter((c) => c.id !== 'grp').map((c) => { const fs = FT().inCat(c.id);
      return `<div class="pmcat card" data-cat="${esc(c.id)}"><div class="pmcathd"><h3>${esc(c.name)}<small>${cnt(fs)}</small></h3>${allBtns(c.id)}</div>
        <div class="pmbody">${catRows(fs, cur, base, saved, now, ready, false)}</div></div>`; }).join('');
    const gc = cats.find((c) => c.id === 'grp');
    if (gbox) gbox.innerHTML = gc ? (() => {
      const fs = FT().inCat('grp'), k = 'cat:grp', open = PS.open.has(k);
      const gcnt = v.querySelector('#pmGrpCnt'); if (gcnt) gcnt.textContent = cnt(fs);
      const by = {}; fs.forEach((f) => { (by[f.chain || ''] = by[f.chain || ''] || []).push(f); });
      const chName = (ch) => { const d = (fs.find((f) => f.chain === ch) || {}).desc; return d ? d.split('・')[0] : (ch || '其他'); };
      return `<div class="pmcat${open ? '' : ' shut'}" data-cat="grp"><div class="pmcathd">${fold(k, gc.name, fs, 'h3')}${allBtns('grp')}</div>
        <p class="use pmfoldnote">族群多，整塊預設收起來；點上面標題或「全部展開」打開。關掉的族群：族群頁模糊＋鎖頭、資金輪動的族群下拉那一列鎖住、熱力圖／排行／輪盤點了只跳「此族群需開通」。${PS.mode === 'plan' ? '瀏覽次數＝一天能打開幾個不同族群頁。' : ''}</p>
        <div class="pmbody"${open ? '' : ' hidden'}><div class="grpgrid">`
        + Object.keys(by).map((ch) => { const ck = 'ch:' + ch, co = PS.open.has(ck);
          return `<div class="grpch" data-ch="${esc(ch)}">${fold(ck, chName(ch), by[ch], 'span')}</div>`
            + `<div class="grpbody" data-ch="${esc(ch)}"${co ? '' : ' hidden'}>${catRows(by[ch], cur, base, saved, now, ready, true)}</div>`; }).join('') + '</div></div></div>';
    })() : '';
    if (gbox) gbox.onchange = (e) => box.onchange(e);
    if (gbox) gbox.oninput = (e) => box.oninput(e);
    if (gbox) gbox.onclick = (e) => box.onclick(e);
    if (gbox) gbox.onkeydown = (e) => box.onkeydown(e);
    const ttl = v.querySelector('#pmGrpTtl'); if (ttl) ttl.onclick = (e) => box.onclick(e);
    box.onchange = (e) => {
      if (e.target.closest('[data-lim]')) return;
      const el = e.target.closest('[data-f]'); if (!el) return;
      const f = FT().byId(el.dataset.f); if (!f) return;
      setVals({ [f.id]: f.kind === 'limit' ? parseInt(el.value, 10) : !!el.checked });
    };
    /* 瀏覽次數：邊打邊記進草稿，不重畫（重畫會把游標從輸入框拿走）；空白＝不限、不合法就標紅不收 */
    box.oninput = (e) => {
      const inp = e.target.closest('input[data-lim]'); if (!inp) return;
      const raw = String(inp.value || '').trim();
      const ok = raw === '' || (/^\d{1,4}$/.test(raw) && +raw <= 9999);
      inp.classList.toggle('bad', !ok);
      if (!ok) return;
      setLim(inp.dataset.lim, raw === '' ? null : +raw);
      const row = inp.closest('.pmrow'), sl = savedLims(), cl = curLims(), fid = inp.dataset.lim;
      const b = row && row.querySelector('button[data-limb]');
      if (b) { const h = Object.prototype.hasOwnProperty.call(cl, fid); b.textContent = h ? cl[fid] + '/日' : '∞'; b.classList.toggle('set', h); b.classList.toggle('zero', h && cl[fid] === 0); }
      if (row) row.classList.toggle('dirty', sl[fid] !== cl[fid] || (((planOf(PS.planSel) || {}).feats || {})[fid] !== ((PS.draft && PS.draft.feats) || {})[fid]));
      paintSave();
    };
    if (!PS.limDoc) { PS.limDoc = true; document.addEventListener('pointerdown', (e) => {
      if (PS.limOpen && !e.target.closest('.pmlimpop,button[data-limb]')) { PS.limOpen = null; paintCats(); } }, true); }
    box.onkeydown = (e) => { if (e.target.closest('input[data-lim]') && (e.key === 'Enter' || e.key === 'Escape')) { e.preventDefault(); PS.limOpen = null; paintCats(); } };
    box.onclick = (e) => {
      const lb = e.target.closest('button[data-limb]');
      if (lb) { PS.limOpen = PS.limOpen === lb.dataset.limb ? null : lb.dataset.limb; paintCats();
        const i = box.querySelector('input[data-lim]'); if (i) { i.focus(); i.select(); } return; }
      const lc = e.target.closest('button[data-limclr]');
      if (lc) { setLim(lc.dataset.limclr, null); PS.limOpen = null; paintTarget(); paintCats(); return; }
      if (e.target.closest('button[data-limok]')) { PS.limOpen = null; paintTarget(); paintCats(); return; }
      if (PS.limOpen && !e.target.closest('.pmlimpop')) { PS.limOpen = null; paintCats(); }
      const fb = e.target.closest('button[data-fold]');
      if (fb) { const k = fb.dataset.fold; if (PS.open.has(k)) PS.open.delete(k); else PS.open.add(k); paintCats(); return; }
      if (e.target.closest('#pmExpandAll,#pmCollapseAll')) {
        const all = e.target.closest('#pmExpandAll');
        PS.open = new Set();
        if (all) { PS.open.add('cat:grp'); FT().inCat('grp').forEach((f) => PS.open.add('ch:' + (f.chain || ''))); }
        paintCats(); return;
      }
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
  function planDraft(feats, lims) {
    const p = planOf(PS.planSel) || {};
    PS.draft = diffKeys(feats, p.feats || {}) || diffKeys(lims, p.lims || {}) ? { feats, lims } : null;
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
      planDraft(feats, Object.assign({}, curLims()));
      paintTarget(); paintCats();
    }
  }
  function setLim(fid, n) {
    const p = planOf(PS.planSel); if (!p || PS.mode !== 'plan') return;
    const lims = Object.assign({}, curLims());
    if (n == null) delete lims[fid]; else lims[fid] = n;
    planDraft(Object.assign({}, (PS.draft && PS.draft.feats) || p.feats || {}), lims);
  }
  async function saveDraft() {
    const n = dirtyN(); if (!n) return;
    if (PS.mode === 'member') await saveMember(PS.draft, `${n} 項變更`);
    else { const p = planOf(PS.planSel); if (p) await savePlan(p.id, p.name, PS.draft.feats || {}, PS.draft.lims || {}, `${n} 項變更`); }
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
  async function savePlan(id, name, feats, lims, label) {
    setStat('儲存中…');
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats, lims });
    if (j && j._s === 200) {
      PS.plans = j.plans; PS.draft = null; paintAddPlan(); paintTarget(); paintCats(); setStat(label + `・已儲存到「${(planOf(id) || {}).name || name}」（台北 ${tpeTime()}）`, 'ok');
      if (window.TwPerm) window.TwPerm.refresh();
    } else { setStat('儲存失敗：' + errText(j) + '（變更還在，可以再按一次儲存）', 'bad'); }
  }
  async function refreshList() {
    const [li, mm] = await Promise.all([PS.A.call('/v1/admin/perm/list', {}), PS.A.call('/v1/admin/members', {})]);
    if (li && li._s === 200) PS.list = li;
    if (mm && mm._s === 200 && Array.isArray(mm.members)) PS.mem = mm;
    paintTabs(); paintList();
    const sb = PS.v && PS.v.querySelector('#ptSubList small'); if (sb) sb.textContent = listRows().length;
  }

  /* ---------------------------------------------------------------- 會員名單（會員權限的「會員名單」子分頁＋會員管理的「所有人員狀況」共用）
     欄位與理由（Andy B 要的＋我補的，回報有列）：
       會員（email、名字、付費金色徽章＋方案名）｜方案｜加入日｜到期日｜最後上線｜累計在線｜近 30 天造訪｜觀看次數（近 30 天頁面瀏覽）｜
       最常用的功能 Top3｜最常看的股票 Top3｜狀態。展開：近 14 天每日活躍、各分頁瀏覽、功能次數、常看股票、活躍天數、平均每次停留。 */
  const COLS = [['email', '會員', 'c-who'], ['plan', '方案', 'c-tpl'], ['created', '加入日', 'c-cr'], ['expires', '到期日', 'c-exp'], ['seen', '最後上線', 'c-seen'],
    ['online', '累計在線', 'c-on num'], ['visits', '近 30 天造訪', 'c-vis num'], ['views', '觀看次數', 'c-vw num'], ['feat', '最常用的功能 Top3', 'c-feat'],
    ['stock', '最常看的股票 Top3', 'c-stk'], ['st', '狀態', 'c-st']];
  /* 會員權限 → 會員名單：註冊會員＝所有註冊會員（付費的也在、金色標示）；付費＝這個範本的人 */
  function listRows() {
    const all = members();
    if (PS.mode !== 'plan') return all;
    if (PS.tier === 'free') return all.filter((r) => r.st !== 'new' || r.tier === 'free');
    if (PS.tier === 'paid') return all.filter((r) => r.plan === PS.planSel);
    return [];
  }
  function sortVal(r, key) {
    switch (key) {
      case 'plan': return (r.paid ? '0' : '1') + r.planName;
      case 'online': return r.onlineMs; case 'visits': return r.visits30; case 'views': return r.views30;
      case 'feat': return (r.topFeat[0] || [, 0])[1]; case 'stock': return (r.topStock[0] || [, 0])[1];
      case 'st': return ['ok', 'new', 'exp'].indexOf(r.st);
      default: return r[key] == null ? '' : r[key];
    }
  }
  function memTable(rows, id) {
    const key = PS.sort, dir = PS.dir;
    rows = rows.slice().sort((a, b) => { const x = sortVal(a, key), y = sortVal(b, key); return (x > y ? 1 : x < y ? -1 : 0) * dir || a.email.localeCompare(b.email); });
    const top = (a, nm) => (a.length ? a.map(([k, n]) => `<span class="mchip" title="${esc(nm(k))}：${nf(n)} 次">${esc(nm(k))}<i>${nf(n)}</i></span>`).join('') : '<span class="mdim">—</span>');
    const badge = (r) => (r.paid ? `<span class="pdbadge" title="付費會員：${esc(r.planName)}">★ ${esc(r.planName)}</span>` : r.tier === 'paid' ? `<span class="pdbadge off" title="付費已過期">${esc(r.planName)}（過期）</span>` : '');
    const body = rows.map((r) => {
      const open = PS.exp.has(r.email);
      return `<tr data-email="${esc(r.email)}" class="${PS.rec && r.email === PS.rec.email ? 'on' : ''}${r.paid ? ' paid' : ''}" aria-expanded="${open}">`
        + `<td class="c-who"><span class="car" aria-hidden="true">${open ? '▾' : '▸'}</span><b>${esc(r.email)}</b>${r.name ? `<small>${esc(r.name)}</small>` : ''}${badge(r)}</td>`
        + `<td class="c-tpl">${r.tier === 'paid' ? esc(r.planName) : '註冊會員'}${r.set ? '' : '<small>（預設）</small>'}</td>`
        + `<td class="c-cr">${dday(r.created)}</td><td class="c-exp">${dday(r.expires)}</td><td class="c-seen">${dstr(r.seen)}</td>`
        + `<td class="c-on num">${dur(r.onlineMs)}</td><td class="c-vis num">${nf(r.visits30)}</td><td class="c-vw num">${nf(r.views30)}</td>`
        + `<td class="c-feat">${top(r.topFeat, compName)}</td><td class="c-stk">${top(r.topStock, (k) => k)}</td>`
        + `<td class="c-st"><span class="stt ${r.st}">${ST_NAME[r.st]}</span></td></tr>`
        + (open ? `<tr class="pmdet" data-for="${esc(r.email)}"><td colspan="${COLS.length}">${detailHtml(r)}</td></tr>` : '');
    }).join('');
    return `<table class="pmlist memtbl" id="${id}"><thead><tr>${COLS.map(([k, n, cls]) => `<th data-sort="${k}" class="${cls}${PS.sort === k ? ' sorted' : ''}" aria-sort="${PS.sort === k ? (PS.dir > 0 ? 'ascending' : 'descending') : 'none'}">${n}${PS.sort === k ? (PS.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table>`;
  }
  function miniBars(list, names) {
    if (!list.length) return '<div class="empty">近 30 天沒有紀錄。</div>';
    const max = Math.max(1, ...list.map((x) => x[1]));
    return `<div class="bars sm">${list.map(([k, n]) => `<span class="bl" title="${esc(names(k))}">${esc(names(k))}</span><span class="bt"><i style="width:${(n / max * 100).toFixed(1)}%"></i></span><span class="bn">${nf(n)}</span>`).join('')}</div>`;
  }
  function detailHtml(r) {
    const d = PS.det[r.email];
    if (!d) return '<div class="mdet"><div class="empty">讀取使用紀錄中…</div></div>';
    if (d.err) return `<div class="mdet"><div class="empty">${esc(d.err)}</div></div>`;
    if (!d.known) return '<div class="mdet"><div class="empty">這位還沒登入過，沒有使用紀錄。</div></div>';
    const days = d.days || [], dmax = Math.max(1, ...days.map((x) => x.views || 0), ...days.map((x) => x.visits || 0));
    const avg = r.visits30 ? r.online30 / r.visits30 : 0;
    return `<div class="mdet" data-email="${esc(r.email)}">
      <div class="kpis"><div><b>${nf(r.days30)}</b>近 30 天活躍天數</div><div><b>${dur(r.online30)}</b>近 30 天在線</div><div><b>${avg ? dur(avg) : '—'}</b>平均每次停留</div><div><b>${nf(r.views30)}</b>近 30 天頁面瀏覽</div></div>
      <div class="mdgrid">
        <div><h4>近 14 天每日活躍</h4><div class="mdays" role="img" aria-label="近 14 天每天的頁面瀏覽">${days.map((x) => `<i style="height:${Math.max(x.views || x.visits ? 6 : 0, (Math.max(x.views || 0, x.visits || 0)) / dmax * 100).toFixed(1)}%" title="${esc(x.day)}：造訪 ${x.visits} 次、瀏覽 ${x.views} 頁、在線 ${dur(x.ms)}"></i>`).join('')}</div>
          <div class="dayx"><span>${esc((days[0] || {}).day || '')}</span><span>${esc((days[days.length - 1] || {}).day || '')}</span></div></div>
        <div><h4>各分頁瀏覽</h4>${miniBars(d.pages || [], (k) => VIEW_NAME[k] || k)}</div>
        <div><h4>功能使用次數</h4>${miniBars((d.feats || []).slice(0, 8).map(([pg, c, n]) => [pg + '|' + c, n]), (k) => { const [pg, c] = k.split('|'); return (VIEW_NAME[pg] || pg) + '・' + compName(c); })}</div>
        <div><h4>最常看的股票</h4>${miniBars(d.stocks || [], (k) => k)}</div></div>
      ${PS.mode === 'member' ? '<p class="use" style="margin:8px 0 0">這位已載入下面「③ 逐人微調」。</p>' : ''}</div>`;
  }
  async function loadDetail(email) {
    if (PS.det[email] && !PS.det[email].err) return;
    const j = await PS.A.call('/v1/admin/member/detail', { email });
    PS.det[email] = j && j._s === 200 && Array.isArray(j.days) ? j : { err: j && j._s === 404 ? '會員 Worker 還沒更新成有使用明細的版本（admin-v3）。' : '讀不到使用紀錄（' + errText(j) + '）' };
    paintList();
  }
  function paintList() {
    if (!PS.v) return;
    if (PS.mode === 'plan') {
      const box = PS.v.querySelector('#ptListBox'); if (!box || box.hidden) return;
      const rows = listRows();
      const ttl = PS.tier === 'free' ? '註冊會員' : `付費・${(planOf(PS.planSel) || {}).name || ''}`;
      box.innerHTML = `<div class="card" id="ptMail" style="margin-top:14px"><h3>${esc(ttl)}・${rows.length} 人</h3><p class="use">${PS.tier === 'free' ? '所有註冊會員（登入過的人）；金色徽章＝付費會員（後面是方案名），過期的付費會員標「過期」。' : '被指定到這個範本的會員。'}點欄位標題排序、點一列展開他的使用紀錄。要新增、改到期日或換範本，到「會員管理」。</p>
        ${rows.length ? memTable(rows, 'ptTable') : '<div class="empty">這一層目前沒有人。</div>'}
        <div class="pmbar"><a href="#admin/members" id="ptGoMembers">到會員管理新增會員 →</a></div></div>`;
      wireList(box);
      return;
    }
    const box = PS.v.querySelector('#pmListBody'); if (!box) return;
    const pn = (r) => r.planName;
    const all = members();
    const q = PS.q.trim().toLowerCase();
    let rows = q ? all.filter((r) => (r.email + ' ' + r.name + ' ' + pn(r) + ' ' + TIER_NAME[r.tier]).toLowerCase().includes(q)) : all.slice();
    if (PS.stf) rows = rows.filter((r) => r.st === PS.stf);
    const cnt = PS.v.querySelector('#pmCnt'); if (cnt) cnt.textContent = (q || PS.stf) ? `${rows.length} ／ ${all.length} 位` : `共 ${all.length} 位`;
    box.innerHTML = rows.length ? memTable(rows, 'pmTable') : `<div class="empty">${q || PS.stf ? '沒有符合條件的會員。' : '還沒有任何會員。用上面的「新增會員」加第一位。'}</div>`;
    wireList(box);
  }
  function wireList(box) {
    box.onclick = (e) => {
      const th = e.target.closest('th[data-sort]');
      if (th) { if (PS.sort === th.dataset.sort) PS.dir = -PS.dir; else { PS.sort = th.dataset.sort; PS.dir = th.dataset.sort === 'email' ? 1 : -1; } paintList(); return; }
      if (e.target.closest('tr.pmdet')) return;
      const tr = e.target.closest('tr[data-email]'); if (!tr) return;
      const em = tr.dataset.email;
      if (PS.mode === 'member') {
        if (!(PS.rec && PS.rec.email === em) && !guard()) return;
        PS.email = em; if (!(PS.rec && PS.rec.email === em)) loadMember(em);
      }
      if (PS.exp.has(em)) PS.exp.delete(em); else { PS.exp.add(em); loadDetail(em); }
      paintList();
    };
  }

  window.TwAdmin = { render, guard: () => guard() };
})();
