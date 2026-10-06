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
  const VIEW_NAME = { themes: '題材熱度', etf: 'ETF', explore: '選股策略', overview: '總覽', flow: '資金流向', industry: '產業地圖', heatmap: '熱力圖', market: '市場明細', season: '週期統計',
    delivery: '交付清單', stock: '個股頁', legal: '法律頁', watch: '自選清單', other: '其他' };
  const EV_NAME = { session: '開啟網站（每個分頁一次）', session_login: '登入狀態下開啟網站', login: '登入', logout: '登出',
    search: '搜尋股票', watch_add: '加入自選', watch_remove: '移出自選', watch_tab_new: '新增自選分頁', watch_panel: '打開自選清單',
    stock_tab: '切個股分頁（營收／籌碼…）', k_period: '切 K 線週期', ai_tab: '切 AI 分析面向', open_3d: '打開 3D 剖析圖', zoom: '放大圖表',
    how: '打開「?」說明', theme_toggle: '切深淺色', events_drawer: '打開今日事件', mtf: '四週期同看', indicators: '打開指標設定', draw: '畫線工具', m_seg: '手機切分段' };
  /* 細項事件的元件名（docs/account_analytics.md「細項事件」）*/
  const COMP_NAME = { 'sankey.node': '點資金去向節點', 'sankey.link': '點資金去向連線', 'inst.tab': '切族群×法人分頁', 'inst.group': '點族群×法人族群', ind: '開啟技術指標', 'draw.tool': '使用畫線工具', 'events.link': '點事件連結', 'etf.cat': '點 ETF 類別', 'explore.topic': '選股題目', 'watch.chart': '點走勢圖', 'watch.kline': '切換 K 線', 'support.fab': '打開客服', 'support.tab': '切客服分頁', 'support.faq': '展開常見問題', 'support.send': '送出意見反饋', 'support.mail': '寄信給客服', view: '被觀看', play: '播放（時間軸）', quad: '象限卡（領先／改善／轉弱／落後）', filter_chain: '篩選：產業鏈', filter_group: '篩選：族群（勾選）',
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
  const S = { days: 30, period: '30', since: '', until: '', tab: 'all', sub: 'all', timer: 0, v: null, A: null, page: 'flow', st: null, on: null };
  const TABS = [['perm', '會員權限', 'admTabPerm'], ['traffic', '流量觀測', 'admTabTraffic']];   // 2026-10-05：會員管理拿掉（新增會員、逐人微調併進會員權限的會員名單）
  const tabOf = () => { const m = /^#admin\/(perm|members|traffic)\b/.exec(location.hash || ''); return m ? (m[1] === 'members' ? 'perm' : m[1]) : 'traffic'; };

  function css() {
    if (document.getElementById('admCss')) return;
    const s = document.createElement('style'); s.id = 'admCss';
    s.textContent = `
/* ===== 流量觀測 1005 重設計（Andy 10-05：字級照其他分頁、圖表填滿卡片、其餘照 UI 專家設計）=====
   字級（量自總覽／資金流向／市場明細，1440 實測）：卡標 16/600、副標 13/400、頂部 KPI 24/700 mono、卡內 KPI 18/700 mono、
   表頭 12/600、表格內文 14、軸字／圖例註 12。版型：三欄格線，第一列 2:1（趨勢＋佔比）、第二列三張長條榜、第三列 2:1（表＋散佈）、第四列 1:2（在線＋會員）；
   卡片＝flex 直欄，圖區 .cb 吃掉標題以下全部高度（flex:1），資料少時長條列距、直條寬度、表格列高自動放大，不留白。 */
#v-admin .admgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:minmax(var(--tr-row,300px),auto);gap:var(--gap-card,12px);margin-top:12px}
#v-admin.demo::before{content:"示範資料（預覽版專用，正式站不會出現）";display:inline-flex;align-items:center;height:26px;padding:0 10px;margin:12px 0 0;border-radius:999px;font-size:12px;font-weight:600;color:var(--amber,#e0a93a);border:1px solid var(--amber,#e0a93a);background:color-mix(in srgb,var(--amber,#e0a93a) 12%,transparent)}
#v-admin .admgrid>.s2{grid-column:span 2}
#v-admin .admgrid>.tall{grid-row:span 1;min-height:var(--tr-row-tall,340px)}
#v-admin .secttl h2{font-size:var(--fs-h2,20px);font-weight:600}
#v-admin .trkpi{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:14px 16px}
#v-admin .trkpi .kpis{flex:1 1 560px;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:0}
#v-admin .kpis>div{text-align:center;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:13px;color:var(--ink-2);white-space:nowrap}
#v-admin .kpis b{display:block;font-size:24px;line-height:1.15;font-weight:700;color:var(--ink);font-family:var(--mono);font-variant-numeric:tabular-nums}
#v-admin .kpis .ic{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;margin-bottom:2px;background:color-mix(in srgb,currentColor 16%,transparent)}
#v-admin .kpis .ic svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
#v-admin .trctl{display:flex;align-items:center;gap:8px;flex:none;border-left:1px solid var(--line);padding-left:16px}
#v-admin .trctl label{font-size:13px;color:var(--ink-2);white-space:nowrap}
#v-admin .trctl .icobtn{width:32px;padding:0;display:inline-flex;align-items:center;justify-content:center;color:var(--accent,var(--cyan))}
#v-admin .trctl .icobtn svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
#v-admin .trctl .icobtn.spin svg{animation:trspin .24s ease-out}
@keyframes trspin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){#v-admin .trctl .icobtn.spin svg{animation:none}}
#v-admin .trctl select,#v-admin .trctl button{height:32px;font-size:13px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;cursor:pointer}
#v-admin .qtip{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;border:1px solid var(--cyan);color:var(--cyan);font-size:12px;font-weight:700;cursor:help}
#admBody .admgrid>.card{display:flex;flex-direction:column;min-width:0;padding:14px 16px}
#admBody .admgrid>.card>h3{display:flex;align-items:center;gap:8px;white-space:nowrap;margin:0;font-size:var(--fs-h3,16px);font-weight:600;line-height:1.3}
#admBody .admgrid>.card>h3::before{content:"";width:4px;height:14px;border-radius:2px;background:var(--accent,var(--cyan));flex:none}
#admBody .admgrid>.card>.use{margin:2px 0 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:help;font-size:13px;line-height:20px;color:var(--ink-2)}
#admBody .cb{flex:1 1 auto;min-height:0;display:flex;flex-direction:column}
/* 長條榜：名稱／長條／數字三欄；列高在 30～64 之間隨可用高度長大，多的空間平均分在列間（資料少＝列距變寬，不留底部空白） */
#admBody .bars{flex:1;display:grid;grid-template-columns:minmax(0,9.5em) minmax(0,1fr) 6em;grid-auto-rows:var(--chart-row-h,32px);align-content:space-evenly;column-gap:12px;align-items:center;font-size:var(--fs-body,14px)}
#admBody .bars .bl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:center}
#admBody .bars .bt{height:var(--chart-bar-h,10px);background:var(--panel-3);border-radius:999px;overflow:hidden}
#admBody .bars .bt i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,color-mix(in srgb,var(--cat-1) 55%,transparent),var(--cat-1))}
#admBody .bars .bn{font-family:var(--mono);text-align:center;white-space:nowrap;font-variant-numeric:tabular-nums}
#admBody .bars .bn small{display:inline-block;width:3em;color:var(--ink-2);font-size:12px}
#admBody .bars button.bl{background:none;border:0;color:var(--ink);font:inherit;padding:0;cursor:pointer;text-decoration:underline dotted var(--ink-3,#7a879c)}
#admBody .bars button.bl:hover{color:var(--accent,var(--cyan))}
/* 每天直條：圖區吃滿卡片、y 軸 3 刻度＋淡格線、平均虛線、最高那天標值；天數 ≤ 7 時每根放大並標值與日期 */
#admBody .dayplot{flex:1;display:flex;gap:8px;min-height:180px}
#admBody .dayy{display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;font:12px/1 var(--mono);color:var(--ink-2);min-width:3em}
#admBody .days{position:relative;flex:1;display:flex;align-items:stretch;gap:3px;border-bottom:1px solid color-mix(in srgb,var(--line) 60%,transparent);border-left:1px solid color-mix(in srgb,var(--line) 60%,transparent);background:linear-gradient(color-mix(in srgb,var(--line) 40%,transparent) 1px,transparent 1px) 0 0/100% 25%}
#admBody .dayticks{position:relative;height:20px;margin-top:4px;padding-left:calc(3em + 8px)}
#admBody .dayticks>div{position:relative;height:100%}
#admBody .dayticks span{position:absolute;top:0;transform:translateX(-50%);font:12px/16px var(--mono);color:var(--ink-2);white-space:nowrap}
#admBody .days .dc{flex:1;min-width:2px;max-width:var(--day-max,12px);display:flex;flex-direction:column;justify-content:flex-end;align-items:center;margin:0 auto;position:relative}
#admBody .days.few{gap:var(--day-gap,24px);padding:0 24px}
#admBody .days.few .dc{max-width:var(--day-max,24px)}
#admBody .days i{display:block;width:100%;border-radius:4px 4px 0 0;background:linear-gradient(180deg,var(--cat-1),color-mix(in srgb,var(--cat-1) 45%,transparent))}
#admBody .days .dc.mx i{background:var(--cat-1)}
#admBody .days .dv{font:600 12px/1 var(--mono);color:var(--ink);margin-bottom:4px;white-space:nowrap}
#admBody .days .dd{position:absolute;bottom:-20px;font-size:12px;color:var(--ink-2);white-space:nowrap}
#admBody .days.few{margin-bottom:20px}
#admBody #admDayBars .dc[data-day]{cursor:pointer}
#admBody #admDayBars .dc.sel i{background:var(--amber,#e0a93a);box-shadow:0 0 0 1px var(--amber,#e0a93a)}
#admBody #admDayBars.hov .dc.sel i{opacity:1}
.daychip{display:inline-flex;align-items:center;gap:8px;margin-left:12px;height:28px;padding:0 4px 0 10px;border-radius:999px;font-size:13px;background:color-mix(in srgb,var(--amber,#e0a93a) 14%,transparent);border:1px solid color-mix(in srgb,var(--amber,#e0a93a) 55%,transparent);color:var(--ink);vertical-align:middle;max-width:100%}
.daychip .dot{width:8px;height:8px;border-radius:50%;background:var(--amber,#e0a93a);flex:none}
.daychip b{font-weight:700;white-space:nowrap}.daychip em{font-style:normal;color:var(--ink-2);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.daychip button{width:22px;height:22px;border-radius:50%;border:0;background:transparent;color:var(--ink-2);font-size:16px;line-height:20px;cursor:pointer;flex:none;padding:0}
.daychip button:hover{background:var(--panel-3);color:var(--ink)}
#admBody .days .dc.fut{background:repeating-linear-gradient(135deg,transparent 0 4px,color-mix(in srgb,var(--line) 55%,transparent) 4px 5px);opacity:.7}
#admBody .days.coarse{gap:6px}#admBody .days.coarse .dc{max-width:44px}#admBody .days.many{gap:1px}#admBody .days.many .dc{min-width:1px}
#admBody .days.hrs:not(.few){margin-bottom:20px}#admBody .days.hrs .dd{position:absolute;bottom:-20px;font-size:12px;color:var(--ink-2);white-space:nowrap}
#admBody .days.hrs .dc{max-width:20px}#admBody .days.hrs.few .dc{max-width:64px}
#v-admin .trtabs .nbsw>button.dragging{opacity:.4}#v-admin .trtabs .nbsw>button.dropL{box-shadow:inset 3px 0 0 var(--cyan)}#v-admin .trtabs .nbsw>button.dropR{box-shadow:inset -3px 0 0 var(--cyan)}
#admBody .hrbar{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:6px}#admBody .hrmodes{align-self:flex-start}
#admBody .days.stk2 .dc{justify-content:flex-end}#admBody .days.stk2 .dc>i{border-radius:0}
#admBody .hrlg{display:flex;gap:16px;justify-content:center;font-size:12px;color:var(--ink-2);margin-top:22px}#admBody .hrlg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
#admBody .hrnote{font-size:12px;color:var(--ink-3);margin-top:6px}
#admBody .bigno{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px}#admBody .bigno b{font:700 44px/1 var(--mono)}#admBody .bigno span{font-size:14px;color:var(--ink-2)}#admBody .bigno small{font-size:12px;color:var(--ink-3)}
#admBody .days .avg{position:absolute;left:0;right:0;border-top:1px dashed var(--ink-3,#7a879c);pointer-events:none}
#admBody .days .avg b{position:absolute;right:4px;top:-17px;font:12px/1 var(--mono);color:var(--ink-2);font-weight:400;background:var(--panel);padding:0 4px;border-radius:3px}
#admBody .dayx{display:flex;justify-content:space-between;gap:8px;font-size:12px;color:var(--ink-2);margin-top:6px;padding-left:calc(3em + 8px)}
#admBody .dayx .dayno{color:var(--ink-3)}
/* 甜甜圈：外徑隨卡片可用高度放大（160～260）；圖例放圖下方一排，三欄置中 */
#admBody .cb{container-type:inline-size}
/* 甜甜圈：左圖右圖例（Andy：圖表資訊在右手邊，圓餅才不會被壓縮）；圖例一列一項＝色塊｜名稱｜數量｜占比，數字欄右對齊不截斷；卡寬 < 420px 才退回圖例在下方 */
#admBody .dn{flex:1;display:flex;flex-direction:row;align-items:center;justify-content:center;gap:20px;min-height:0}
#admBody .dn svg{flex:0 1 auto;height:100%;min-height:var(--chart-donut,160px);max-height:300px;aspect-ratio:1;width:auto;min-width:0}
#admBody .dn .dnc{flex:1 1 0;min-width:220px;max-width:360px;max-height:360px;aspect-ratio:1;height:auto;align-self:center}   /* 環撐滿「卡片扣掉圖例」的寬（跟產業地圖一樣），上限 360 */
#admBody .dn ul{list-style:none;margin:0;padding:0;display:flex;gap:20px;justify-content:center;font-size:var(--fs-body,14px)}
#admBody .dn li{display:flex;align-items:center;gap:8px;white-space:nowrap}
#admBody .dn li i{width:12px;height:12px;border-radius:3px;flex:none}
#admBody .dn li b{font-family:var(--mono);font-variant-numeric:tabular-nums}
#admBody .dn li small{color:var(--ink-2);font-size:12px}
#admBody .sc{flex:1;min-height:200px;position:relative}
#admBody .sc svg{position:absolute;inset:0;width:100%;height:100%}
#admBody .sc text{font-size:12px;fill:var(--ink-2)}#admBody .sc text.lb{fill:var(--ink);font-weight:600;paint-order:stroke;stroke:var(--panel);stroke-width:3px}
#admBody .sc .gl{stroke:var(--line)}
/* 表格：表頭 12/600、內文 14；包在 .tbw 裡吃滿卡片，列高隨資料量放大；超過 340 高就卷動、表頭黏住 */
#admBody .tbw{flex:1;min-height:0;display:flex;flex-direction:column;overflow:auto;max-height:var(--tr-tbl-max,340px)}
#admBody table{width:100%;border-collapse:collapse;flex:1 1 auto}
#admBody table th,#admBody table td{padding:4px 10px;line-height:1.4;font-size:14px;text-align:center;border-bottom:1px solid var(--line)}
#admBody table th{font-size:12px;font-weight:600;color:var(--ink-2);white-space:nowrap;position:sticky;top:0;background:var(--panel-3);z-index:1}
#admBody table td{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px}
#admBody table td:first-child{max-width:none}
#admBody table.fx{table-layout:fixed}#admBody table.fx td{max-width:none}
#admBody table tbody tr{height:34px}
#admBody table td.nm{font-weight:600}
#admBody table td .mn{font-family:var(--mono);font-variant-numeric:tabular-nums}
#admBody .chips{display:flex;gap:6px;justify-content:center;flex-wrap:nowrap;overflow:hidden}
#admBody .chip{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 8px;border-radius:999px;font-size:12px;white-space:nowrap;color:var(--ink);background:color-mix(in srgb,var(--cat-1) 14%,transparent);border:1px solid color-mix(in srgb,var(--cat-1) 40%,transparent)}
#admBody .chip:nth-child(2){background:color-mix(in srgb,var(--cat-2) 14%,transparent);border-color:color-mix(in srgb,var(--cat-2) 40%,transparent)}
#admBody .chip:nth-child(3){background:color-mix(in srgb,var(--cat-3) 14%,transparent);border-color:color-mix(in srgb,var(--cat-3) 40%,transparent)}
#admBody .chip b{font-family:var(--mono);font-weight:700}
#admBody .vb{display:flex;align-items:center;gap:8px;justify-content:center}
#admBody .vb i{display:block;height:8px;border-radius:999px;background:var(--cat-1);min-width:4px}
#admBody .vb span{flex:0 0 110px;height:8px;background:var(--panel-3);border-radius:999px;overflow:hidden}
#admBody .vb em{font-style:normal;font-family:var(--mono);min-width:2.5em;text-align:right}
#admBody .okn{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-bottom:10px}
#admBody .okn>div{background:var(--panel-3);border-radius:10px;padding:8px 6px;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:12px;color:var(--ink-2)}
#admBody .okn b{font:700 18px/1.2 var(--mono);color:var(--ink)}
#admBody .okn>div.live b::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--cat-1);margin-right:6px;vertical-align:middle}
#admBody label.tg{margin-top:10px}
#trDetail .cdgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--gap-card,12px)}
#trDetail .cdgrid>div{display:flex;flex-direction:column;min-width:0;min-height:260px}
#trDetail .cdgrid h3{display:flex;align-items:center;gap:8px;margin:0;font-size:var(--fs-h3,16px);font-weight:600}
#trDetail .cdgrid h3::before{content:"";width:4px;height:14px;border-radius:2px;background:var(--accent,var(--cyan));flex:none}
#trDetail .bars{flex:1;display:grid;grid-template-columns:minmax(0,9.5em) minmax(0,1fr) 6em;grid-auto-rows:32px;align-content:space-evenly;column-gap:12px;align-items:center;font-size:14px}
#trDetail .bars .bl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:center}
#trDetail .bars .bt{height:10px;background:var(--panel-3);border-radius:999px;overflow:hidden}
#trDetail .bars .bt i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,color-mix(in srgb,var(--cat-1) 55%,transparent),var(--cat-1))}
#trDetail .bars .bn{font-family:var(--mono);text-align:center;white-space:nowrap}
#trDetail .bars button.bl{background:none;border:0;color:var(--ink);font:inherit;padding:0;cursor:pointer;text-decoration:underline dotted var(--ink-3,#7a879c)}
#trDetail .bars button.bl.on{color:var(--accent,var(--cyan));text-decoration:none;font-weight:700}
/* 管理區 1006：功能開關版面照範本 126（四欄一般 grid、同列頂端對齊等高）；瀑布流已拿掉，樣式在檔尾「範本 126」那一段 */
#v-admin .pmcats.pmcards{margin-top:10px}
#v-admin .pmcards .pmcat.card .pmcathd h3{font-size:var(--fs-h3,16px);font-weight:600}
#v-admin .pmcards .pmcat.card .pmcathd h3 small{font-size:12px}
#v-admin .pmcats .pmrow .pmtx b{font-size:14px;font-weight:500}
/* ===== 流量觀測：分頁式統計（2026-10-05 Andy 新規格）===== */
#v-admin{--pgL:60%}
html[data-theme="light"] #v-admin{--pgL:40%}
#v-admin .trhead{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
#v-admin .trhead .sp{flex:1}
#v-admin .trhead .trctl{border:0;padding:0}
#v-admin .trctl input[type=date]{height:32px;font-size:13px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 8px}
#v-admin .trctl input[hidden],#v-admin .trctl .trto[hidden]{display:none}#v-admin .trctl .trto{color:var(--ink-2)}
#v-admin .trctl{flex-wrap:wrap;min-width:0;max-width:100%}#v-admin .trctl input[type=date]{width:136px;min-width:0}
@media (max-width:640px){#v-admin .trhead .trctl{width:100%}#v-admin .trctl input[type=date]{flex:1 1 110px}}
#v-admin .admgrid.trpair,#v-admin .admgrid.trtop{grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);margin-top:12px}
#v-admin .admgrid.trtop>.s2{grid-column:auto}
#v-admin .admgrid.trpair:first-child{margin-top:0}
#v-admin .trtabs{padding:0;overflow:visible}
#v-admin .trtabs>#trTabsBox{padding:12px 16px 0}
#v-admin .trtabs>#trPageBody{padding:0 16px 16px;border-top:1px solid var(--line-2)}
#v-admin .trtabs .nbsw .tdot,#v-admin .trtabs .nbsw.lv2 .tdot{display:inline-block;width:9px;height:9px;border-radius:3px;flex:none}
#v-admin .trtabs .nbsw em{margin-left:4px}
#v-admin .admgrid.trusers{grid-auto-rows:minmax(var(--tr-row,300px),auto)}
#v-admin .admgrid.trone{margin-top:12px}#v-admin .admgrid.trone>.card{grid-column:1/-1}
#admBody .sbody{flex:1;display:flex;gap:24px;align-items:stretch;min-height:240px}#admBody .sbody .bigno{flex:0 0 220px;border-right:1px solid var(--line);padding-right:24px}#admBody .sbody .sch{flex:1;min-width:0;display:flex;flex-direction:column}
#admBody .dn.clock svg{max-height:320px}
#v-admin .trusers .tbw{max-height:none}
#admBody .admgrid>.card>h3,#admBody .admgrid>.card>.use{flex:none}
#v-admin .trhd{padding-top:12px}
#v-admin .trhd .nbsw{margin-bottom:0}
#v-admin .trempty{padding:40px 0;text-align:center}
#admBody .bars .bt.stk{display:block}
#admBody .bars .bt.stk>span{display:flex;height:100%;border-radius:999px;overflow:hidden}
#admBody .bars .bt.stk i{flex:none;height:100%;border-radius:0}
#admBody .bars .bt.stk i:hover{filter:brightness(1.15)}
#admBody .bars .bt.stk{cursor:pointer}
#admBody .dn ul.lg{display:flex;flex-direction:column;gap:8px;flex:0 1 auto;min-width:190px;max-width:320px;font-size:var(--fs-body,14px);justify-content:center}
#admBody .dn ul.lg li{display:flex;align-items:center;gap:8px;min-width:0}
#admBody .dn ul.lg li span{flex:1;min-width:0;line-height:1.3;overflow-wrap:anywhere}   /* 名稱不准出現「…」：放不下就換行 */
#admBody .dn ul.lg li b{flex:none;min-width:3.4em;text-align:right;font:600 13px var(--mono);color:var(--ink)}
#admBody .dn ul.lg li small{flex:none;min-width:3.1em;text-align:right;font:12px var(--mono);color:var(--ink-2)}
@container (max-width:439px){#admBody .dn{flex-direction:column;gap:14px}#admBody .dn svg,#admBody .dn .dnc{flex:1 1 0;height:auto;width:auto}#admBody .dn ul.lg{flex:none;width:100%;max-width:none}}
#admBody .dn ul.lg li i{width:12px;height:12px;border-radius:3px;flex:none}
/* 圖表互動：滑過高亮、其餘變淡；浮動提示（#trTip，掛在 body） */
#trTip{position:fixed;z-index:1400;pointer-events:none;max-width:280px;padding:8px 10px;border-radius:8px;font-size:13px;line-height:1.5;color:var(--ink);background:var(--panel);border:1px solid var(--line-2);box-shadow:0 8px 24px rgba(0,0,0,.3);white-space:nowrap}
#trTip[hidden]{display:none}
#trTip b{font-weight:700}
#v-admin [data-chart] [data-row],#v-admin [data-chart] li[data-k]{transition:opacity .12s ease,filter .12s ease}
#v-admin [data-chart].hov .dc:not(.hl) i{opacity:.3}
#v-admin [data-chart].hov .dc.hl i{filter:brightness(1.25)}
#v-admin [data-chart].hov .bars>[data-row]:not(.hl),#v-admin .bars.hov>[data-row]:not(.hl),#v-admin .hbars.hov>[data-row]:not(.hl){opacity:.35}
#v-admin .bars.hov>.hl,#v-admin .hbars.hov>.hl{opacity:1}
#v-admin [data-chart].hov li[data-k]:not(.hl){opacity:.7}
#v-admin [data-chart].hov .sc circle:not(.hl),#v-admin .sc.hov circle:not(.hl),#v-admin [data-chart].hov .vbars rect:not(.hl){opacity:.25}
#admBody .sc circle.hl{r:8}
#v-admin .vbars rect.hl{filter:brightness(1.3)}
@media (prefers-reduced-motion:reduce){#admBody [data-chart] [data-row],#admBody [data-chart] li[data-k]{transition:none}}
@media (max-width:1100px){#v-admin .admgrid.trpair,#v-admin .admgrid.trtop{grid-template-columns:minmax(0,1fr)}#v-admin .admgrid{grid-template-columns:repeat(2,minmax(0,1fr))}#v-admin .admgrid>.s2{grid-column:span 2}}
@media (max-width:820px){#v-admin .trkpi .kpis{grid-template-columns:repeat(3,minmax(0,1fr))}#v-admin .trctl{border-left:0;padding-left:0}#v-admin .admgrid{grid-template-columns:minmax(0,1fr)}#v-admin .admgrid>.s2{grid-column:auto}}
#v-admin .admgrid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--gap-card,14px);margin-top:14px}
#v-admin .card{min-width:0}
#v-admin h2{margin:0;font-size:18px}#v-admin h3{margin:0 0 2px;font-size:16px}
#v-admin .use{font-size:13px;color:var(--ink-2);margin:0 0 10px;line-height:1.55}
#v-admin .admtop{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
#v-admin .admtop .sp{flex:1}
#v-admin .admtop select,#v-admin .admtop button{height:32px;font-size:13.5px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;cursor:pointer}
#v-admin table{width:100%;border-collapse:collapse;font-size:13.5px}
#v-admin th,#v-admin td{text-align:left;padding:6px 6px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}
#v-admin th{color:var(--ink-2);font-weight:500;font-size:12.5px}
#v-admin .empty{color:var(--ink-2);font-size:13px;padding:10px 0}
#v-admin label.tg{display:flex;align-items:center;gap:8px;font-size:14px;cursor:pointer}
#v-admin label.tg input{width:18px;height:18px}
#v-admin .err{color:#ff6b7a}
/* 10-05 Andy「會員系統分頁也是，統一」：管理區分頁／範本頁籤／子分頁一律用產業地圖的資料夾分頁 .nbsw（CSS 在 index.html），這裡只補底線 */
#v-admin .admnav{border-bottom:1px solid var(--line);margin-bottom:0}
#v-admin .admnav a{text-decoration:none}
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
#v-admin .ptwrap{margin-top:14px}
#v-admin .ptwrap .ptabs{margin-top:0;padding:0}
#v-admin .ptwrap .ptabs button{min-height:44px;flex-direction:row;align-items:center;padding:0 18px;border-radius:10px 10px 0 0;margin-bottom:-1px}
#v-admin .ptwrap .ptabs button.on{border-bottom-color:var(--panel)}
#v-admin .ptwrap .ptpanel{border-top:1px solid var(--cyan);border-radius:0 10px 10px 10px;padding:0 18px 18px}
#v-admin .ptwrap .ptsub{margin:0 -18px 12px;padding:0 14px}
#v-admin .ptwrap .ptsub.one button{cursor:default}
#v-admin .ptlede{margin:6px 0 0;font-size:12.5px;color:var(--ink-2)}
#v-admin .ptwhoro{display:flex;align-items:center;gap:10px;min-height:32px}
#v-admin .ptwhoro .ptwho{flex:1;min-width:0;font-size:13px;color:var(--ink-2)}
#v-admin .ptgear{flex:none;width:32px;height:32px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);font-size:16px;cursor:pointer}
#v-admin .ptgear[aria-expanded=true]{border-color:var(--cyan);color:var(--cyan)}
#v-admin .ptwrap .secttl{margin-top:14px}
#v-admin .ptwrap .pmgrpbox.card{background:transparent;box-shadow:none}
#v-admin .ptinner{padding:12px 0 4px}#v-admin .ptinner h3{margin:0 0 4px}
#v-admin .ptwrap #pmStat:empty{display:none}
#v-admin .ptabs:has(button.on)+.ptpanel{border-color:var(--cyan)}
#v-admin .pmcats.card{gap:0;padding:0;overflow:hidden;grid-template-columns:repeat(auto-fill,minmax(min(100%,260px),1fr))}
#v-admin .pmcats.card .pmcat{padding:12px 16px;box-shadow:1px 0 0 color-mix(in srgb,var(--line) 70%,transparent),0 1px 0 color-mix(in srgb,var(--line) 70%,transparent);min-width:0}
#v-admin .pmgrpbox.card{display:block;margin-top:10px}
#v-admin #pmGrpTtl{display:flex;align-items:center;gap:10px;flex-wrap:nowrap}#v-admin #pmGrpTtl .pmfold{margin-left:auto}
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
#v-admin .pmcards .pmcat.card .pmcathd h3{display:flex;flex-wrap:nowrap;align-items:center;gap:6px;font-size:15px;white-space:nowrap;overflow:hidden}
#v-admin .pmcards .pmcat.card .pmcathd h3 small{flex:none;margin-left:2px}
#v-admin .pmcards .pmcathd>button[data-all]{height:26px;padding:0 8px;font-size:12.5px}
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
#v-admin .ptsub{border-bottom:1px solid var(--line-2)}
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
#v-admin .pmlimb{width:44px;box-sizing:border-box;text-align:center;font:500 13px var(--mono);line-height:20px;padding:0;border-radius:10px;border:1px solid transparent;background:transparent;color:var(--ink-3,#7a879c);opacity:.8;cursor:pointer;white-space:nowrap;overflow:hidden}
#v-admin .pmlimb:hover,#v-admin .pmlimb[aria-expanded=true]{opacity:1;border-color:var(--line-2)}
#v-admin .pmlimb.set{opacity:1;color:var(--ink);background:color-mix(in srgb,var(--cyan) 16%,transparent)}
#v-admin .pmlimb.mixed{opacity:1;color:var(--ink);background:color-mix(in srgb,var(--amber,#e0a93a) 18%,transparent)}
#v-admin .pmglim{width:auto;min-width:44px;padding:0 8px;flex:none;opacity:1;border-color:var(--line-2)}
#v-admin .pmglim.dirty{box-shadow:inset 0 0 0 1px var(--amber,#e0a93a)}
#v-admin .pmgpop{z-index:1500}
#v-admin .pmlimb.zero{color:#ff6b7a;background:color-mix(in srgb,#ff6b7a 14%,transparent)}
#v-admin .pmlimb:disabled{cursor:not-allowed}
#v-admin .pmlimpop{position:absolute;right:0;bottom:calc(100% - 4px);z-index:30;display:flex;align-items:center;gap:6px;padding:6px 8px;font-size:12px;color:var(--ink-2);background:var(--panel);border:1px solid var(--line-2);border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.25);white-space:nowrap}
#v-admin .pmlimpop input{width:60px;height:26px;font:13px var(--mono);text-align:right;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:6px;padding:0 6px}
#v-admin .pmlimpop input.bad{border-color:#ff6b7a}
#v-admin .pmlimpop button{height:26px;font-size:12px;padding:0 8px;border-radius:6px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);cursor:pointer}
#v-admin .pmlimpop button.ok{background:var(--cyan);color:#06121f;border-color:transparent}
/* perm-cards 單行規則（Andy 10-05：「所有文字皆控制在一行內，並且不可以因為功能影響排版」）：
   ① 開放功能表與 ② 族群觀測共用同一個列元件 —— 固定列高、各欄固定寬、名稱／說明單行省略號（全名在 title），
   撥開關或設次數前後列的位置大小不變。 */
#v-admin .pmcats .pmrow{height:52px;box-sizing:border-box;padding-top:0;padding-bottom:0;align-items:center;overflow:visible}
#v-admin .pmcats .pmrow.sm{height:36px;gap:8px}
#v-admin .pmcats .pmrow .pmtx{min-width:0;overflow:hidden}
#v-admin .pmcats .pmrow .pmtx b{display:flex !important;align-items:center;min-width:0;white-space:nowrap;overflow:hidden}
#v-admin .pmcats .pmrow .pmtx .nm{min-width:0;flex:1 1 auto;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .pmcats .pmrow .pmtx small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.4}
#v-admin .pmcats .pmrow .gico{width:16px;height:16px;flex:0 0 16px;margin-right:6px;vertical-align:0}
#v-admin .pmcats .pmrow .gico svg{width:16px;height:16px}
#v-admin .pmcats .pmrow>.psw{width:44px;flex:none}
#v-admin .pmcat .pmfoldhd,#v-admin .pmcat .pmfoldhd>*{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-admin .pmcat .grpch{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .pmcathd{flex-wrap:nowrap !important;min-width:0}
#v-admin .pmcathd h3 small{white-space:nowrap}
#v-admin .ptwrap .ptabs{flex-wrap:nowrap;overflow:hidden}
#v-admin .ptwrap .ptabs button{white-space:nowrap;min-width:0;flex:0 1 auto;overflow:hidden;text-overflow:ellipsis}
#v-admin .ptwrap .ptabs button>span{overflow:hidden;text-overflow:ellipsis}
#v-admin .ptlede,#v-admin .pmlegend,#v-admin .ptwrap .use,#v-admin .ptwrap .pmwho,#v-admin .ptwrap .ptwho,#v-admin .ptwrap .secttl,#v-admin .ptwrap .secttl>*,#v-admin .ptwrap h3{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
#v-admin .pmlegend{flex-wrap:nowrap}#v-admin .pmlegend span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:inline-block}
#v-admin .pmlegend .lg{vertical-align:-1px;margin-right:6px}

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
@media (max-width:600px){#v-admin .memtbl .c-tpl,#v-admin .memtbl .c-exp,#v-admin .memtbl .c-vis{display:none}#v-admin .mdgrid{grid-template-columns:minmax(0,1fr)}#v-admin .pmrow.wlim{grid-template-columns:auto minmax(0,1fr) auto}#v-admin .pmrow.wlim .pmside{display:none}}
/* ==== perm-v4（2026-10-05，Andy）：資料夾頁籤、範本資訊列、卡片同寬同高、頁籤拖曳／⋮ 選單、會員名單統計圖 ====
   放在最後、選擇器刻意比前面的規則多一層，讓這一段蓋過舊的（舊規則不刪：會員管理頁 #admin/members 還在用一部分）。 */
#v-admin{--st-ok:#0ca30c;--st-soon:#fab219;--st-exp:#d03b3b;--st-new:#898781;--c0:#898781;--c1:#3987e5;--c2:#d95926;--c3:#199e70;--c4:#c98500;--c5:#9085e9}
:root[data-theme="light"] #v-admin{--c1:#2a78d6;--c2:#eb6834;--c3:#1baf7a;--c4:#eda100;--c5:#4a3aa7}
#v-admin .ptlede{display:flex;align-items:baseline;gap:16px;margin:6px 0 0}
#v-admin .ptlede>span{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .ptlede>.pthint{flex:none;margin-left:auto;color:var(--ink-3,#7a879c)}
/* ① 資料夾頁籤：頁籤列底部一條線（::after）＝內容框的上框線；選中的頁籤疊在線上面（z-index 2）、底色＝內容框底色 →
   線在那一段被蓋掉，頁籤和內容框連成一塊。舊版是內容框自己畫上框線＋頁籤 margin-bottom:-1px 去蓋，
   但頁籤列有 overflow:hidden（單行省略號要用），那 1px 被裁掉 → Andy 看到的那條「把頁籤和內容切開的線」。 */
#v-admin .ptwrap{position:relative;margin-top:16px}
#v-admin .ptwrap .ptabs{position:relative;display:flex;align-items:flex-end;gap:4px;margin:0;padding:0;border:0;flex-wrap:nowrap;overflow:hidden}
#v-admin .ptwrap .ptabs::after{content:"";position:absolute;left:0;right:0;bottom:0;height:1px;background:var(--line-2);z-index:1;pointer-events:none}
#v-admin .ptwrap .ptabs button[role=tab]{position:relative;z-index:0;display:flex;flex-direction:row;align-items:center;height:44px;min-height:0;margin:0;padding:0 18px;
  font-size:15.5px;font-weight:600;color:var(--ink-2);background:color-mix(in srgb,var(--panel-3) 75%,var(--bg));border:1px solid var(--line-2);border-bottom:0;
  border-radius:10px 10px 0 0;box-shadow:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:0 1 auto;min-width:0}
#v-admin .ptwrap .ptabs button[role=tab]:hover{color:var(--ink);background:var(--panel-2)}
#v-admin .ptwrap .ptabs button[role=tab].on{z-index:2;color:var(--ink);background:var(--panel);border-color:var(--line-2);box-shadow:inset 0 3px 0 var(--cyan)}
#v-admin .ptwrap .ptabs button[role=tab].add{flex:none;width:46px;justify-content:center;padding:0;font-size:22px;font-weight:400}
#v-admin .ptwrap .ptabs .ptab{position:relative;display:flex;flex:0 1 auto;min-width:0}
#v-admin .ptwrap .ptabs .ptab>button[role=tab]{width:100%;padding-left:34px;padding-right:34px;justify-content:center;text-align:center;cursor:grab}
#v-admin .ptwrap .ptabs button.ptmore{position:absolute;z-index:3;right:6px;top:8px;width:26px;height:28px;min-height:0;margin:0;padding:0;display:block;border:0;border-radius:6px;
  background:transparent;color:var(--ink-2);font-size:18px;font-weight:700;line-height:28px;text-align:center;cursor:pointer;opacity:0;transition:opacity .12s}
#v-admin .ptwrap .ptabs .ptab:hover button.ptmore,#v-admin .ptwrap .ptabs .ptab:focus-within button.ptmore,#v-admin .ptwrap .ptabs button.ptmore[aria-expanded=true]{opacity:1}
#v-admin .ptwrap .ptabs button.ptmore:hover,#v-admin .ptwrap .ptabs button.ptmore[aria-expanded=true]{background:var(--panel-3);color:var(--ink)}
#v-admin .ptwrap .ptabs button.ptmore:focus-visible{outline:2px solid var(--cyan);outline-offset:-2px}
#v-admin .ptwrap .ptabs .ptab.dragging{opacity:.45}
#v-admin .ptwrap .ptabs .ptab.dropL>button[role=tab]{box-shadow:inset 3px 0 0 var(--cyan)}
#v-admin .ptwrap .ptabs .ptab.dropR>button[role=tab]{box-shadow:inset -3px 0 0 var(--cyan)}
#v-admin .ptwrap .ptpanel,#v-admin .ptwrap .ptabs:has(button.on)+.ptpanel{border:1px solid var(--line-2);border-top:0;border-radius:0 0 12px 12px;background:var(--panel);padding:0 20px 20px}
/* ⋮ 選單：掛在 .ptwrap（不在頁籤列裡 —— 頁籤列 overflow:hidden 會把它裁掉），浮在內容上，開關不推擠版面 */
#v-admin .ptmenu{position:absolute;z-index:45;min-width:168px;padding:6px;background:var(--panel);border:1px solid var(--line-2);border-radius:10px;box-shadow:0 10px 28px rgba(0,0,0,.28);white-space:nowrap}
#v-admin .ptmenu[hidden]{display:none}
#v-admin .ptmenu button{display:flex;align-items:center;gap:8px;width:100%;height:34px;padding:0 12px;border:0;border-radius:7px;background:none;color:var(--ink);font-size:14px;text-align:left;cursor:pointer}
#v-admin .ptmenu button:hover:not(:disabled),#v-admin .ptmenu button:focus-visible{background:var(--panel-3);outline:none}
#v-admin .ptmenu button:disabled{opacity:.4;cursor:not-allowed}
#v-admin .ptmenu button.danger{color:var(--st-exp)}
#v-admin .ptmenu hr{border:0;border-top:1px solid var(--line);margin:4px 2px}
#v-admin .ptmenu .pmq{font-size:13.5px;color:var(--ink);padding:6px 8px 8px}
#v-admin .ptmenu .pmq b{color:var(--st-exp)}
#v-admin .ptmenu .pmrow2{display:flex;gap:8px;padding:0 6px 4px;justify-content:flex-end}
#v-admin .ptmenu .pmrow2 button{width:auto;height:32px;border:1px solid var(--line-2);background:var(--panel-2)}
#v-admin .ptmenu .pmrow2 button.danger{background:var(--st-exp);border-color:var(--st-exp);color:#fff;font-weight:700}
#v-admin .ptmenu .pmrow2 button.pri{background:var(--cyan);border-color:var(--cyan);color:var(--ontop,#04121a);font-weight:700}
#v-admin .ptmenu input{height:32px;width:14em;font-size:14px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:7px;padding:0 8px;margin:4px 6px 8px}
/* ② 範本資訊列（內容框頂端）：左＝名稱・價格／週期＋套用人數，右＝⚙；下面一行說明小字 */
#v-admin .ptinfo{display:flex;align-items:center;gap:12px;min-height:40px;padding:14px 0 2px}
#v-admin .ptinfo .ptname{min-width:0;font-size:17px;font-weight:700;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .ptinfo .ptmeta{flex:none;font-size:13px;color:var(--ink-2);padding:2px 10px;border-radius:999px;background:var(--panel-3);white-space:nowrap}
#v-admin .ptinfo .sp{flex:1}
#v-admin .ptnote{margin:2px 0 10px;font-size:12.5px;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .ptdelq{display:flex;align-items:center;gap:10px;flex-wrap:nowrap;margin-top:8px;padding:8px 12px;border-radius:8px;background:color-mix(in srgb,var(--st-exp) 10%,transparent);font-size:13.5px;white-space:nowrap}
#v-admin .ptdelq>span{min-width:0;overflow:hidden;text-overflow:ellipsis}
#v-admin .ptdelq button{flex:none;height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);cursor:pointer;font-size:13.5px}
#v-admin .ptdelq button.danger{background:var(--st-exp);border-color:var(--st-exp);color:#fff;font-weight:700}
#v-admin .ptwrap .ptsub{margin:0 -20px 14px;padding:0 20px;border-bottom:1px solid var(--line)}
/* 族群觀測：裡面那張卡的標題列已經寫「117 項・開 117」，外面大標題旁的同一串數字拿掉（Andy：重複的說明留一處）*/
#v-admin .ptwrap #pmGrpCnt{display:none}
/* ③ 觀看權限：工具列（標題＋圖例＋全部開／全部關）一行 → 卡片格 */
#v-admin .pmtools{display:flex;align-items:center;gap:14px;margin:0 0 10px;min-width:0}
#v-admin .pmtools .pmttl{flex:none;margin:0;font-size:15px;font-weight:700;color:var(--ink)}
#v-admin .pmtools .pmlegend{flex:1 1 auto;margin:0;min-width:0}
#v-admin .pmtools button{flex:none;height:30px;padding:0 12px;font-size:13px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);cursor:pointer}
#v-admin .pmtools button:disabled{opacity:.45;cursor:not-allowed}
/* ④ 卡片同寬同高（Andy 講了好幾次）：固定欄數 → 同一列每張卡同寬（minmax(0,1fr)：內容再寬也不會撐寬某一欄）；
   align-items:stretch → 同一列等高（以那一列最高的為準），清單由上往下排，不足的留白在下面。 */
#v-admin .pmcats.pmcards{grid-template-columns:repeat(4,minmax(0,1fr));align-items:stretch;margin-top:0}
#v-admin .pmcats.pmcards>.pmcat.card{display:flex;flex-direction:column;justify-content:flex-start;align-self:stretch;height:auto;margin:0;min-width:0}
#v-admin .pmcat .grpgrid{grid-template-columns:minmax(0,1fr)}
#v-admin .pmcat .grpgrid>.grpbody{grid-template-columns:repeat(4,minmax(0,1fr));align-items:stretch}
@media (max-width:1279px){#v-admin .pmcats.pmcards,#v-admin .pmcat .grpgrid>.grpbody{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:999px){#v-admin .pmcats.pmcards,#v-admin .pmcat .grpgrid>.grpbody{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:600px){#v-admin .pmcats.pmcards,#v-admin .pmcat .grpgrid>.grpbody{grid-template-columns:minmax(0,1fr)}}
/* ===== 範本 126（1006，Andy 講第二次）：功能開關四欄一般 grid —— 同列卡片頂端對齊、等高（短卡下留白可接受）；
   卡片＝白底細邊框＋3px 粗藍上框；開關實心深藍；卡標題＝小圖示＋粗體名＋「N 項・開 N」＋右上總開關；
   每列＝主標粗體、副標灰字、右邊小「∞」；欄數 1440 四／1024 三／800 兩／390 一（上面 550 行起的 media）。
   藍色用 --pm-blue（深色主題提亮），不動全站 --cyan。 */
#v-admin{--pm-blue:#1f4fd8;--pm-blue-2:#163fb4}
:root:not([data-theme="light"]) #v-admin{--pm-blue:#3d7bff;--pm-blue-2:#2f6df0}
html[data-theme="light"] #v-admin{--pm-blue:#1f4fd8;--pm-blue-2:#163fb4}
#v-admin .pmcats.pmcards{display:grid;column-count:auto;align-items:stretch;gap:12px}
#v-admin .pmcats.pmcards>.pmcat.card{display:flex;flex-direction:column;align-self:stretch;margin:0;padding:10px 12px 6px;background:var(--panel);border:1px solid var(--line);border-top:3px solid var(--pm-blue);border-radius:6px;break-inside:auto}
#v-admin .pmcats.pmcards .pmcathd{display:flex;align-items:center;gap:8px;min-height:36px;margin-bottom:6px}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3{display:flex;align-items:center;gap:6px;flex:1 1 auto;min-width:0;font-size:14.5px;font-weight:700;white-space:nowrap;overflow:hidden}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3 b{font-weight:700;overflow:hidden;text-overflow:ellipsis}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3 small{flex:none;font-size:12px;font-weight:400;color:var(--ink-2)}
#v-admin .pmcats.pmcards .pmcathd button.psw3{margin-left:auto}
#v-admin .pmcats.pmcards .pmrow{border-top:0;border-bottom:1px solid var(--line);border-radius:0;padding-left:0;padding-right:0;height:52px}
#v-admin .pmcats.pmcards .pmrow:last-child{border-bottom:0}
#v-admin .pmcats.pmcards .pmrow .pmtx b{font-size:14px;font-weight:700}
#v-admin .pmcats.pmcards .pmrow .pmtx small{font-size:12.5px;color:var(--ink-2)}
#v-admin .pmcats.pmcards .pmlimb{font-size:12px;color:var(--ink-2);background:none;border:0}
#v-admin .pmcats.pmcards .pmlimb.set{color:var(--pm-blue);font-weight:700}
/* 開關：開＝實心深藍、圓鈕白；關＝灰底（列開關、總開關、族群觀測都一樣） */
#v-admin #ptPermBox label.psw input:checked+span,#v-admin #ptPermBox button.psw3[aria-checked="true"]{background:var(--pm-blue);border-color:var(--pm-blue)}
#v-admin #ptPermBox button.psw3[aria-checked="mixed"]{background:linear-gradient(90deg,var(--pm-blue) 50%,var(--panel-3) 50%);border-color:var(--pm-blue)}
#v-admin #ptPermBox label.psw input:focus-visible+span,#v-admin #ptPermBox button.psw3:focus-visible{outline-color:var(--pm-blue)}
/* 標題列塞了次數鈕後橫向不夠：卡標題改兩行（名稱／「N 項・開 N」），圖示佔左邊兩行高 */
#v-admin .pmcats.pmcards .pmcathd{min-height:44px}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:6px;row-gap:0;align-items:center;white-space:normal}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3>:not(b):not(small){grid-row:1/3;grid-column:1}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3>b{grid-column:2;grid-row:1;white-space:nowrap}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3>small{grid-column:2;grid-row:2;white-space:nowrap}
#v-admin .pmallim{display:inline-flex;align-items:center;flex:none;margin-right:10px}
#v-admin .pmcats.pmcards .pmcathd .pmglim{margin-left:auto;font-size:12px;height:24px;padding:0 6px;white-space:nowrap}
#v-admin .pmcats.pmcards .pmcathd .pmglim+button.psw3{margin-left:0}
#v-admin .pmcats.pmcards .pmcathd .pmglim.set{color:var(--pm-blue);font-weight:700}
#v-admin .pmglim.mixed{font-weight:700}
/* ⑤ 會員名單上方的統計（與展開明細共用）：一排數字＋一排同高圖卡。統計一律「甜甜圈＋長條」；長條用 SVG 畫（每根有 <title>）。 */
#v-admin .mstats{margin:2px 0 14px}
#v-admin .mkpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
#v-admin .mkpi{min-width:0;padding:8px 14px;border:1px solid var(--line);border-radius:10px;background:var(--panel-2)}
#v-admin .mkpi b{display:block;font:700 20px/1.35 var(--mono);color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .mkpi span{display:block;font-size:12.5px;line-height:1.4;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .mdet .mkpi b{font-size:17px}
#v-admin .mcharts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:12px;align-items:stretch}
#v-admin .mchart{min-width:0;display:flex;flex-direction:column;gap:6px;padding:10px 14px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
#v-admin .mchart h4{margin:0;font-size:13.5px;font-weight:700;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .mchart h4 small{font-weight:400;color:var(--ink-2);margin-left:6px;font-size:12px}
#v-admin .mchart .empty{padding:6px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin .mdonut{display:flex;align-items:center;gap:12px;min-width:0}
#v-admin .mdonut svg,#v-admin .mdonut .dnc{flex:none;width:104px;height:104px}#v-admin .mdonut ul{flex:1}
#v-admin .mdonut ul{list-style:none;margin:0;padding:0;min-width:0;flex:1;font-size:12.5px}
#v-admin .mdonut li{display:flex;align-items:center;gap:6px;min-height:21px;min-width:0}
#v-admin .mdonut li i{flex:none;width:10px;height:10px;border-radius:3px}
#v-admin .mdonut li span{min-width:0;line-height:1.3;overflow-wrap:anywhere;color:var(--ink-2)}
#v-admin .mdonut li b{margin-left:auto;font-family:var(--mono);font-weight:600;color:var(--ink)}
#v-admin .mdonut li small{flex:none;width:3.2em;text-align:right;font-family:var(--mono);color:var(--ink-2);font-size:11.5px}
#v-admin .mdonut+.mdonut{margin-top:8px;padding-top:8px;border-top:1px dashed var(--line)}
#v-admin .hbars{display:grid;grid-template-columns:minmax(0,9em) minmax(0,1fr) auto;gap:6px 8px;align-items:center;font-size:12.5px}
#v-admin .hbars .bl{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--ink-2)}
#v-admin .hbars svg{display:block;width:100%;height:10px}
#v-admin .hbars rect.tr{fill:var(--panel-3)}#v-admin .hbars rect.v{fill:var(--cat-1,var(--cyan))}
#v-admin .hbars .bn{font-family:var(--mono);text-align:right;color:var(--ink);min-width:2.2em}
#v-admin .vbwrap{display:flex;gap:6px}#v-admin .vby{display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;font:12px/1 var(--mono);color:var(--ink-2);min-width:2.4em;height:110px}
#v-admin .vbplot{flex:1;min-width:0;border-bottom:1px solid color-mix(in srgb,var(--line) 60%,transparent);border-left:1px solid color-mix(in srgb,var(--line) 60%,transparent);background:linear-gradient(color-mix(in srgb,var(--line) 40%,transparent) 1px,transparent 1px) 0 0/100% 25%}
#v-admin .vbars{display:block;width:100%;height:110px}
#v-admin .vbars rect{fill:var(--cat-1,var(--violet))}#v-admin .vbars rect.z{fill:var(--line-2)}
#v-admin .vbx{display:flex;justify-content:space-between;font-size:11.5px;color:var(--ink-2);font-family:var(--mono)}
#v-admin .vbmax{font-size:12px;color:var(--ink-2);white-space:nowrap}
#v-admin .stt.soon{background:color-mix(in srgb,var(--st-soon) 26%,transparent)}
/* 展開明細是表格裡獨立的一列（colspan 全寬）、自己的底色與內距；裡面不用絕對定位 → 展開／收起只會把下面的列往下推，不會蓋到上下列 */
#v-admin .memtbl tr.pmdet>td{padding:14px 16px 16px;background:color-mix(in srgb,var(--panel-2) 85%,var(--bg));border-top:1px solid var(--line-2);border-bottom:2px solid var(--line-2);white-space:normal!important}
#v-admin .memtbl tr.pmdet .mdet{position:static;display:block;overflow:hidden}
#v-admin .memtbl tr.pmdet .mdet .use{margin:10px 0 0}
#v-admin .mdet .mkpis{grid-template-columns:repeat(4,max-content);gap:10px}
#v-admin .mdet .mkpi{padding:6px 14px}
/* 數字欄夠用就好（Andy 10-05）：日期、時間、次數、狀態用內容寬（width:1%＋不換行），剩下的寬度給會員、功能 Top3、股票 Top3 */
#v-admin table.memtbl th.c-cr,#v-admin table.memtbl td.c-cr,#v-admin table.memtbl th.c-exp,#v-admin table.memtbl td.c-exp,#v-admin table.memtbl th.c-seen,#v-admin table.memtbl td.c-seen,
#v-admin table.memtbl th.c-on,#v-admin table.memtbl td.c-on,#v-admin table.memtbl th.c-vis,#v-admin table.memtbl td.c-vis,#v-admin table.memtbl th.c-vw,#v-admin table.memtbl td.c-vw,
#v-admin table.memtbl th.c-st,#v-admin table.memtbl td.c-st{width:1%;white-space:nowrap!important;overflow-wrap:normal}
#v-admin table.memtbl td.c-cr,#v-admin table.memtbl td.c-exp,#v-admin table.memtbl td.c-seen,#v-admin table.memtbl td.c-st,#v-admin table.memtbl th.c-st{text-align:center}
#v-admin table.memtbl td.c-who b{display:inline-block;vertical-align:top;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;overflow-wrap:normal;max-width:calc(100% - 1.4em)}
#v-admin table.memtbl td.c-who{min-width:10em}
@media (max-width:1500px){#v-admin .memtbl .c-cr{display:none}}
@media (max-width:1240px){#v-admin .memtbl .c-vw{display:none}}
@media (max-width:1320px){#v-admin table.memtbl th,#v-admin table.memtbl td{padding-left:4px;padding-right:4px}#v-admin table.memtbl .mchip .mcn{max-width:6em}}
/* Top3 小標籤：名稱太長就省略（全名在 title），次數一定看得到 —— 不讓一個長名稱把整欄撐寬、擠到別欄 */
#v-admin table.memtbl .mchip{max-width:100%;vertical-align:top}
#v-admin table.memtbl .mchip .mcn{display:inline-block;max-width:7.5em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom}
#v-admin table.memtbl td.c-who small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-admin table.memtbl th.c-tpl,#v-admin table.memtbl td.c-tpl{width:1%;white-space:nowrap!important}
#v-admin table.memtbl td.c-tpl small{display:inline;margin-left:2px}
/* 會員欄一行：▸ email 名字 ★ 排同一排，email 太長才省略（全文在滑過提示）*/
#v-admin table.memtbl td.c-who .who1{display:flex;align-items:center;gap:6px;min-width:0;white-space:nowrap}
#v-admin table.memtbl td.c-who .who1 b{flex:0 1 auto;min-width:0;max-width:none}
#v-admin table.memtbl td.c-who .who1 small{display:inline;flex:0 1 auto;min-width:0}
#v-admin table.memtbl td.c-who .who1 .car{flex:none;margin-right:0}
#v-admin table.memtbl td.c-who .pdbadge{flex:none;margin-top:0;padding:0 5px;font-size:11px;line-height:16px}
@media (max-width:640px){#v-admin table.memtbl td.c-who .who1{contain:inline-size}}  /* 窄螢幕：一行的 email 不撐寬表格（超出的省略），避免橫向捲軸 */
/* 名單的 td small 是 display:block（名字那一行用）；展開明細裡的 small 要照原本的行內排法，不然標題、圖例會掉到下一行 */
#v-admin table.memtbl .mdet small{display:inline;font-size:inherit}
#v-admin table.memtbl .mdet .mchart h4 small{font-size:12px}
#v-admin table.memtbl .mdet .mdonut li small{display:inline-block;font-size:11.5px}
/* 卡片標題：名稱＋「N 項・開 M」＋全開／全關要擠在 1／4 寬裡 —— 兩顆鈕縮小，名稱放不下才省略（全名在 title）*/
#v-admin .pmcats.pmcards .pmcathd{gap:4px}
#v-admin button.psw3{position:relative;display:inline-block;width:44px;height:24px;flex:none;padding:0;margin:0 0 0 auto;border-radius:12px;background:var(--panel-3);border:1px solid var(--line-2);cursor:pointer;transition:background .15s}
#v-admin button.psw3>span{position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:50%;background:var(--ink-2);transition:transform .15s,background .15s}
#v-admin button.psw3[aria-checked="true"]{background:var(--cyan);border-color:var(--cyan)}
#v-admin button.psw3[aria-checked="true"]>span{transform:translateX(20px);background:#fff}
#v-admin button.psw3[aria-checked="mixed"]{background:linear-gradient(90deg,var(--cyan) 50%,var(--panel-3) 50%);border-color:var(--cyan)}
#v-admin button.psw3[aria-checked="mixed"]>span{transform:translateX(10px);background:#fff}
#v-admin button.psw3:disabled{cursor:not-allowed;opacity:.5}
#v-admin button.psw3:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}
#v-admin .pmcat .grpch{display:flex;align-items:center;gap:6px}
#v-admin .pmcat .grpch .pmfoldhd{min-width:0;overflow:hidden;text-overflow:ellipsis}
#v-admin .pmallsw{display:inline-flex;align-items:center;gap:6px;flex:none;font-size:13px;color:var(--ink-2);white-space:nowrap}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3{font-size:14.5px;gap:4px}
#v-admin .pmcats.pmcards .pmcat.card .pmcathd h3 small{font-size:12px;margin-left:0}
/* 會員名單所有欄位標題與內容置中（Andy 10-05：「欄位內文字都置中」）；展開明細那一列不動 */
#v-admin table.memtbl thead th,#v-admin table.memtbl tbody tr:not(.pmdet)>td{text-align:center}
/* 例外（Andy 10-05 截圖）：「會員」欄（email）標題與內容靠左 */
#v-admin table.memtbl th.c-who,#v-admin table.memtbl tbody tr:not(.pmdet)>td.c-who{text-align:left}
#v-admin table.memtbl td.c-who .who1{justify-content:flex-start}
/* 10-05 Andy「會員分頁字體置中，大小 Follow 產業 Map」：範本頁籤蓋掉舊的 15.5px／44px 高，回到 .nbsw 的字級與內距、置中 */
#v-admin .ptwrap .ptabs button[role=tab]{font-size:13.5px;font-weight:400;height:auto;min-height:0;justify-content:center;text-align:center;padding:var(--sp-1) var(--sp-3) var(--sp-2)}
#v-admin .ptwrap .ptabs button[role=tab].on{font-weight:700;padding:var(--sp-2) var(--sp-4) var(--sp-2)}
#v-admin .ptwrap .ptabs .ptab>button[role=tab]{padding-left:32px;padding-right:32px}
#v-admin .ptwrap .ptabs button.ptmore{top:50%;transform:translateY(-50%);width:18px;height:18px;right:6px;font-size:15px;line-height:18px;border-radius:50%}
#v-admin .ptwrap .ptabs .ptrn{width:100%;min-width:6em;height:28px;box-sizing:border-box;text-align:center;font:inherit;font-size:13.5px;color:var(--ink);background:var(--panel);border:1px solid var(--cyan);border-radius:6px;padding:0 6px}
#v-admin .ptwrap.medit>#ptTier{display:none}#v-admin .ptwrap.medit .ptpanel{border-top:1px solid var(--line-2);border-radius:10px}
#v-admin .pmback{height:32px;font-size:13px;background:var(--panel-2);color:var(--cyan);border:1px solid var(--line-2);border-radius:8px;padding:0 12px;cursor:pointer}
#v-admin .ptadd{margin:8px 0;flex-wrap:wrap}
#v-admin .ptpub{margin:10px 2px 4px;font-size:14px}#v-admin .pmsep{width:1px;height:22px;background:var(--line-2);margin:0 4px}#v-admin #pmTuneEmail{width:16em}
#v-admin .ptmenu .pmwho2{list-style:none;margin:0 0 6px;padding:0 8px;font-size:13px}#v-admin .ptmenu .pmwho2 li{height:24px;white-space:nowrap}#v-admin .ptmenu .pmwho2 a,#v-admin .ptmenu .pmgo{color:var(--cyan)}#v-admin .ptmenu .pmgo{align-self:center;font-size:13px;margin-right:auto}#v-admin .ptmenu .more{color:var(--ink-2)}
#v-admin .ptwrap .ptabs button[role=tab].add{font-size:18px;padding:0 14px;height:auto}
#v-admin table.memtbl tbody tr:not(.pmdet)>td.num,#v-admin table.memtbl thead th.num,#v-admin table.memtbl td.c-feat,#v-admin table.memtbl td.c-stk{text-align:center !important}`;
    /* 2026-10-06：會員名單上方的統計（#ptStats）照流量觀測的卡片／直條／橫條／甜甜圈做 → 流量觀測那一整套 #admBody 底下的規則，
       用 :is(#admBody,#ptStats) 讓 #ptStats 也吃到（特異度不變），不複製、不改上面任何一條規則；#ptStats 專屬的版面規則在 MS_CSS。 */
    s.textContent = s.textContent.replace(/#admBody(?![\w-])/g, ':is(#admBody,#ptStats)') + MS_CSS;
    document.head.appendChild(s);
  }
  const ago = (ms) => { const s = Math.max(0, Math.round((Date.now() - ms) / 1000)); return s < 60 ? s + ' 秒前' : Math.round(s / 60) + ' 分前'; };
  const dstr = (ms) => { if (!ms) return '—'; const d = new Date(ms + 8 * 3600 * 1000); return d.toISOString().slice(0, 16).replace('T', ' '); };
  const dday = (ms) => (ms ? dstr(ms).slice(0, 10) : '—');
  /* 名單「最後上線」：今年的省略年份（「10-05 14:41」，滑過看全文）—— 數字欄夠用就好，把寬度讓給會員與 Top3（Andy 10-05）*/
  const seenTxt = (ms) => { if (!ms) return '—'; const s = dstr(ms); return s.slice(0, 4) === dstr(Date.now()).slice(0, 4) ? s.slice(5) : s; };
  const nf = (n) => Number(n || 0).toLocaleString('en-US');

  const tp = (html) => ` data-tip="${esc(html)}"`;
  function bars(list, names, total, opt) {
    if (!list.length) return '<div class="empty">沒有資料</div>';
    const max = Math.max(...list.map((x) => x[1]), 1), o = opt || {};
    const nm = (k) => typeof names === 'function' ? names(k) : (names[k] || k);
    return `<div class="bars" data-chart="bars"${o.id ? ` id="${o.id}"` : ''}>` + list.map(([k, n], r) => { const t = tp(`<b>${esc(nm(k))}</b><br>${nf(n)} 次${total ? `・占 ${(n / total * 100).toFixed(1)}%` : ''}`);
      return (o.click ? `<button type="button" class="bl" data-row="${r}"${t} data-k="${esc(k)}">${esc(nm(k))}</button>` : `<span class="bl" data-row="${r}"${t}>${esc(nm(k))}</span>`)
      + `<span class="bt" data-row="${r}"${t}><i style="width:${(n / max * 100).toFixed(1)}%"></i></span>`
      + `<span class="bn" data-row="${r}"${t}>${nf(n)}${total ? `<small style="color:var(--ink-2)"> ${(n / total * 100).toFixed(0)}%</small>` : ''}</span>`; }).join('') + '</div>';
  }

  /* ---- 頂部：標題（＋三個子分頁 tab：2026-10-05 起桌機版搬到左側欄「管理區」底下的縮排子項，見 layout4.js syncPerm；
     頁內這排只在沒有左側欄的版面（≤820，layout4 沒啟用）才出現，免得那種寬度沒地方切子頁）。有沒存的權限草稿時，換分頁先問一次 */
  function head(v, A, extra) {
    const cur = tabOf();
    /* 2026-10-05（Andy：「上方管理區那欄位拿掉」）：不再顯示「管理區＋email」標題與使用統計說明；期間／重新整理搬進流量觀測的「全站總覽」卡 */
    return `<div class="card" id="admHead" style="margin-top:16px"><div class="admtop">
        ${document.documentElement.classList.contains('l4') ? '' : `<nav class="nbsw admnav" id="admTabs" aria-label="管理區分頁">${TABS.map(([k, n, id]) => `<a href="#admin/${k}" id="${id}" data-tab="${k}" class="${cur === k ? 'on' : ''}"${cur === k ? ' aria-current="page"' : ''}>${n}</a>`).join('')}</nav>`}
        <span class="sp"></span>${extra || ''}</div>`;
  }
  function wireHead(v) {
    const nav = v.querySelector('#admTabs');
    if (nav) nav.onclick = (e) => { const a = e.target.closest('a[data-tab]'); if (a && !guard()) e.preventDefault(); };
  }
  /* ==========================================================================
     預覽版示範資料（Andy 10-05：「預覽版本先給我多點數據，先預設目前超破萬次觀看紀錄」）
     只有網址含 /preview/ 時才啟用（判斷寫死在路徑，正式站一行都不跑）：包住 A.call，把管理區的統計類回應換成示範資料，
     頁面上方標「示範資料」。寫入類（儲存範本、改權限…）一律照舊打真的 Worker，不攔。
     ========================================================================== */
  const IS_PREVIEW = /\/preview\//.test(location.pathname || '');
  const DEMO = (() => {
    let seed = 20261005; const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
    const END = new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10), NDAY = 400;      // 示範資料的最後一天＝今天（台北），期間選單與日期欄才對得上
    const dayKey = (i) => new Date(Date.parse(END + 'T00:00:00Z') - (NDAY - 1 - i) * 86400000).toISOString().slice(0, 10);
    /* 頁面 30 天瀏覽量（合計約 5.4 萬）；沒有在 Worker 白名單的頁（etf／explore／events／support）示範時直接給 pv，正式站只會有功能次數 */
    const PAGES = [['flow', 11800], ['stock', 10300], ['overview', 8600], ['industry', 5500], ['heatmap', 4600], ['market', 3900], ['etf', 2200], ['explore', 1900], ['season', 1800], ['watch', 1600], ['events', 1000], ['legal', 320], ['support', 430]];
    const wsum = PAGES.reduce((s, p) => s + p[1], 0);
    const W = []; for (let i = 0; i < NDAY; i++) { const dow = new Date(Date.parse(dayKey(i) + 'T00:00:00Z')).getUTCDay(); W.push((dow === 0 || dow === 6 ? 0.45 : 1) * (0.8 + rnd() * 0.45) * (0.55 + 0.45 * i / NDAY)); }
    const base30 = sum30(W.slice(-30));
    function sum30(a) { return a.reduce((x, y) => x + y, 0); }
    const SUBS = { flow: [['rotation', 0.58], ['sankey', 0.26], ['inst', 0.16]], heatmap: [['industry', 0.63], ['theme', 0.37]], industry: [['chains', 0.34], ['chain', 0.41], ['group', 0.25]], market: [['updown', 0.37], ['inst', 0.27], ['ma', 0.21], ['pick', 0.15]] };
    const STK = [['2330', 3100], ['2317', 1650], ['2454', 1240], ['3711', 960], ['2382', 820], ['3037', 700], ['2603', 560], ['2308', 470], ['6669', 390], ['3661', 330], ['2881', 250], ['2412', 210]];
    const E2 = [
      ['flow', 'play', 'rotBack', 1480], ['flow', 'quad', '領先', 990], ['flow', 'quad', '改善', 760], ['flow', 'quad', '轉弱', 410], ['flow', 'quad', '落後', 300],
      ['flow', 'filter_chain', '半導體', 520], ['flow', 'filter_chain', 'AI 伺服器', 470], ['flow', 'filter_chain', '電子零組件', 280], ['flow', 'filter_top10', '', 640], ['flow', 'filter_clear', '', 210], ['flow', 'filter_group_open', '', 880],
      ['flow', 'how', 'flowRotCard', 360], ['flow', 'zoom', 'rotZoom', 330], ['flow', 'sankey.node', '', 520], ['flow', 'sankey.link', '', 340], ['flow', 'inst.tab', '', 410], ['flow', 'inst.group', '', 270],
      ['heatmap', 'how', 'ovHeatCard', 190], ['heatmap', 'zoom', 'heatZoom', 160], ['heatmap', 'theme.pick', 'AI 伺服器', 300], ['heatmap', 'theme.pick', 'CoWoS', 260], ['heatmap', 'theme.pick', '矽光子', 210], ['heatmap', 'theme.pick', '低軌衛星', 150], ['heatmap', 'theme.pick', '機器人', 140], ['heatmap', 'open_3d', '', 120],
      ['industry', 'how', 'chainHow', 130], ['industry', 'zoom', 'chainMap', 210], ['industry', 'open_3d', '', 160], ['industry', 'search', '', 90], ['market', 'how', 'mktHow', 90], ['market', 'search', '', 170], ['market', 'm_seg', '', 120],
      ['season', 'how', 'seasonHow', 80], ['season', 'zoom', 'seasonChart', 110], ['watch', 'watch_tab_new', '', 140], ['watch', 'watch.chart', '', 720], ['watch', 'watch.kline', '', 380], ['watch', 'watch_add', '', 520], ['watch', 'watch_remove', '', 160], ['watch', 'watch_panel', '', 280],
      ['stock', 'tab.overview', '2330', 2400], ['stock', 'tab.basics', '2330', 520], ['stock', 'tab.tags', '2317', 610], ['stock', 'tab.dividend', '2412', 450], ['stock', 'tab.holders', '2454', 380], ['stock', 'tab.news', '2603', 640], ['stock', 'tab.holdings', '0050', 330], ['stock', 'tab.profit', '2330', 880], ['stock', 'tab.inst', '2330', 1020], ['stock', 'tab.margin', '2330', 470], ['stock', 'tab.revenue', '2330', 1260],
      ['stock', 'kp.d', '2330', 1800], ['stock', 'kp.w', '2330', 740], ['stock', 'kp.m', '2330', 310], ['stock', 'kp.5m', '2330', 520], ['stock', 'kp.15m', '2330', 260], ['stock', 'mtf', '', 340], ['stock', 'indicators', '', 910], ['stock', 'draw', '', 440], ['stock', 'ai_tab', '', 380],
      ['stock', 'ind', 'MA 均線', 1120], ['stock', 'ind', 'MACD', 830], ['stock', 'ind', 'RSI', 690], ['stock', 'ind', 'KD', 640], ['stock', 'ind', '布林通道', 410], ['stock', 'ind', 'SMC 結構', 330], ['stock', 'ind', '本益比河流', 360], ['stock', 'ind', '成交量', 280],
      ['stock', 'draw.tool', '趨勢線', 260], ['stock', 'draw.tool', '水平線', 210], ['stock', 'draw.tool', '斐波那契', 120], ['stock', 'draw.tool', '矩形', 90], ['other', 'etf.cat', '全部', 410], ['other', 'etf.cat', '配息型', 540], ['other', 'etf.cat', '市值型', 380], ['other', 'etf.cat', '主題型', 290], ['other', 'etf.cat', '主動式', 210], ['other', 'etf.cat', '槓桿反向', 160], ['other', 'etf.cat', '債券型', 120], ['other', 'etf.cat', '其他', 60],
      ['other', 'explore.topic', '營收創高', 330], ['other', 'explore.topic', '法人連買', 290], ['other', 'explore.topic', '突破前高', 240], ['other', 'explore.topic', '低基期', 170], ['other', 'explore.topic', '高殖利率', 130],
      ['other', 'support.fab', '', 310], ['other', 'support.tab', '常見問題', 260], ['other', 'support.tab', '意見反饋', 140], ['other', 'support.tab', '寄信', 70], ['other', 'support.faq', '怎麼加自選？', 150], ['other', 'support.faq', '資料多久更新？', 110], ['other', 'support.faq', '紅漲綠跌？', 60], ['other', 'support.send', '', 52], ['other', 'support.mail', '', 31],
      ['other', 'events.link', '', 720], ['overview', 'events_drawer', '', 330], ['flow', 'events_drawer', '', 210], ['stock', 'events_drawer', '', 190], ['industry', 'events_drawer', '', 120], ['market', 'events_drawer', '', 90],
      ['overview', 'how', 'ovHeatCard', 210], ['overview', 'heat_tile', 'ABF 載板', 360], ['overview', 'zoom', 'ovIndex', 150]];
    const e2Base = [];
    SUBS && Object.entries(SUBS).forEach(([pg, arr]) => arr.forEach(([k, f]) => e2Base.push([pg, 'sub.' + k, '', Math.round(PAGES.find((p) => p[0] === pg)[1] * f)])));
    E2.forEach((r) => { if (r[3]) e2Base.push(r); });
    [['被動元件 MLCC', 410], ['晶圓代工', 340], ['ABF 載板', 290], ['CoWoS 先進封裝', 240], ['散熱模組', 190], ['光通訊', 150], ['矽光子', 110]].forEach(([g, n]) => { e2Base.push(['flow', 'filter_group', g, n]); e2Base.push(['flow', 'rank_bar', g, Math.round(n * 0.55)]); e2Base.push(['flow', 'clock_group', g, Math.round(n * 0.4)]); e2Base.push(['heatmap', 'heat_tile', g, Math.round(n * 0.7)]); });
    STK.forEach(([cd, n], i) => { e2Base.push(['stock', 'view', cd, n]);
      [['tab.revenue', 0.34], ['kp.60m', 0.27], ['tab.inst', 0.22], ['tab.profit', 0.15], ['kp.d', 0.12], ['tab.margin', 0.08]].forEach(([c, f]) => e2Base.push(['stock', c, cd, Math.max(1, Math.round(n * f * (0.7 + (i * 7 % 6) / 10))) ])); });
    const NM = ['王小明', '陳怡君', '林志豪', '張雅婷', '李承恩', '黃柏翰', '吳佩珊', '劉冠宇', '蔡欣怡', '楊家豪', '許雅文', '鄭宇軒', '謝佳穎', '郭俊傑', '洪思妤', '曾冠廷', '邱怡婷', '廖偉誠', '賴淑芬', '徐子豪'];
    const NOW = Date.now(), NU = 520;
    const users = Array.from({ length: NU }, (_, i) => ({ name: NM[i % NM.length] + (i >= NM.length ? String(Math.floor(i / NM.length) + 1) : ''), email: `demo${String(i + 1).padStart(3, '0')}@example.com`,
      seen: NOW - Math.round((i * 0.35 + rnd() * 2) * 3600000), created: NOW - Math.round((8 + i * 0.6) * 86400000), visits: Math.max(1, Math.round(60 - i * 0.1 + rnd() * 8)) }));
    const members = users.map((u, i) => ({ email: u.email, onlineMs: Math.round((12 - i * 0.02 + rnd()) * 3600000), online30: Math.round((6 - i * 0.01 + rnd()) * 3600000), visits30: u.visits,
      days30: Math.max(1, Math.round(24 - i * 0.04)), views30: Math.round(u.visits * (4 + rnd() * 5)), topFeat: [['tab.revenue', 14 - (i % 7)], ['quad', 9 - (i % 5)], ['kp.60m', 5]], topStock: [[STK[i % 12][0], 18 - (i % 9)], [STK[(i + 3) % 12][0], 7], [STK[(i + 6) % 12][0], 3]] }));
    const routes = ['flow', 'stock', 'overview', 'industry', 'market', 'heatmap', 'etf', 'watch', 'explore'];
    const online = { total: 19, guests: 8, public_online: true, users: routes.concat(['flow', 'stock']).map((r, i) => ({ name: users[i].name, email: users[i].email, route: r, seen: NOW - (6 + i * 13) * 1000 })) };
    const mstats = { days: Array.from({ length: 14 }, (_, i) => ({ day: dayKey(NDAY - 14 + i), n: Math.round(120 + rnd() * 90) })), active7: 297,
      feats: [['tab.revenue', 2412], ['quad', 1698], ['kp.60m', 1251], ['filter_group', 1207], ['tab.inst', 988], ['play', 843], ['search', 721], ['zoom', 596]], stocks: STK.slice(0, 8).map(([c, n]) => [c, Math.round(n * 0.6)]) };
    /* 會員名單統計（預覽版）：依 from／to／bin 產生，形狀同 Worker 的 /v1/admin/members/stats（週＝週一起算、月＝每月 1 日；活躍人數是「不同人數」，所以週／月不是每天相加） */
    const mstatsFor = (b) => {
      const to = b.to || END, from = b.from || new Date(Date.parse(to + 'T00:00:00Z') - 29 * 86400000).toISOString().slice(0, 10), bin = ['day', 'week', 'month'].includes(b.bin) ? b.bin : 'day';
      const binOf = (d) => { if (bin === 'month') return d.slice(0, 7) + '-01'; if (bin === 'week') { const t = Date.parse(d + 'T00:00:00Z'); return new Date(t - ((new Date(t).getUTCDay() + 6) % 7) * 86400000).toISOString().slice(0, 10); } return d; };
      const hash = (d) => { let h = 7; for (const c of d) h = (h * 31 + c.charCodeAt(0)) % 997; return h; };
      const days = []; let nd = 0, visits = 0, pv = 0;
      for (let t = Date.parse(from + 'T00:00:00Z'); t <= Date.parse(to + 'T00:00:00Z'); t += 86400000) {
        const d = new Date(t).toISOString().slice(0, 10), k = binOf(d), dow = new Date(t).getUTCDay(), dn = Math.round((dow === 0 || dow === 6 ? 0.5 : 1) * (130 + hash(d) % 70));
        let e = days[days.length - 1]; if (!e || e.day !== k) { e = { day: k, n: 0, visits: 0, pv: 0, _m: 0, _d: 0 }; days.push(e); }
        e._m = Math.max(e._m, dn); e._d += 1; e.visits += dn * 2; e.pv += dn * 9; nd += 1; visits += dn * 2; pv += dn * 9;
      }
      days.forEach((e) => { e.n = Math.min(NU, Math.round(e._m * (1 + 0.45 * Math.log2(e._d)))); delete e._m; delete e._d; });
      const f = nd / 30;
      return { n: NU, scope: b.scope || 'all', from, to, bin, keepDays: 90, since: null, active7: 297, active: Math.min(NU, Math.round(Math.max(...days.map((e) => e.n)) * 1.2)), visits, ms: visits * 21 * 60000, pv, joined: Math.round(nd * 0.9),
        featTotal: Math.round(14000 * f), stockTotal: Math.round(6200 * f), days,
        feats: mstats.feats.map(([k, n]) => [k, Math.round(n * f)]), stocks: mstats.stocks.map(([k, n]) => [k, Math.round(n * f)]) };
    };
    const detail = (email) => { const i = Math.max(0, users.findIndex((u) => u.email === email)), m = members[i] || members[0];
      return { known: true, days: Array.from({ length: 14 }, (_, k) => ({ day: dayKey(NDAY - 14 + k), visits: 1 + ((k + i) % 3), views: 8 + ((k * 7 + i * 3) % 23), ms: (6 + ((k * 5 + i) % 28)) * 60000 })),
        pages: PAGES.slice(0, 6).map(([k, s], j) => [k, Math.round(s / 400 / (j + 1) + i % 5)]), feats: [['stock', 'tab.revenue', 14], ['flow', 'quad', 9], ['stock', 'kp.60m', 7], ['flow', 'filter_group', 5], ['overview', 'how', 3]], stocks: m.topStock }; };
    /* 依期間組出 /v1/admin/stats：每天一列（頁面瀏覽＋開站），細項依 天數／30 縮放；即時＝今天到目前為止每小時 */
    const stats = (days, live, from, to) => {
      const idx = (d) => NDAY - 1 - Math.round((Date.parse(END + 'T00:00:00Z') - Date.parse(d + 'T00:00:00Z')) / 86400000);
      const iA = from ? Math.max(0, idx(from)) : null, iB = to ? Math.min(NDAY - 1, idx(to)) : NDAY - 1;       // 起訖日（Worker 同語意：含頭含尾，to 預設今天）
      const n = iA != null ? Math.max(1, iB - iA + 1) : Math.max(1, Math.min(NDAY, days || 30)), i0 = iA != null ? iA : NDAY - n, rows = [];
      const hourNow = Math.min(23, new Date(Date.now() + 8 * 3600000).getUTCHours());
      const recent = window.__demoRecentDays ? iB - window.__demoRecentDays + 1 : -1;      // 測試用：只有最近 N 天有紀錄（正式站 Worker 只回有資料的日子，from 仍是期間起日）
      for (let i = i0; i <= iB; i++) { if (i < recent) continue; const day = dayKey(i), dn = 54000 * W[i] / base30;
        PAGES.forEach(([k, s]) => rows.push({ day, k: 'pv:' + k, n: window.__demoDayNum ? +day.slice(8, 10) : Math.max(1, Math.round(dn * s / wsum * (0.88 + ((i * 7 + k.length) % 10) / 40))) }));
        const ss = window.__demoDayNum ? +day.slice(8, 10) : Math.round(dn * 0.145); rows.push({ day, k: 'ev:session', n: ss }, { day, k: 'ev:session_login', n: Math.round(ss * (0.34 + ((i % 7) / 100))) }); }
      const pvSum = rows.filter((r) => r.k.startsWith('pv:')).reduce((x, r) => x + r.n, 0), scale = live ? 1.1 / 30 : pvSum / 54000, e2 = e2Base.map(([page, comp, detail, c]) => ({ page, comp, detail, n: Math.max(1, Math.round(c * scale)) }));
      const out = { from: dayKey(i0), to: dayKey(iB), rows, e2, users: { total: NU, recent: users.slice(0, 50).map((u) => ({ name: u.name, email: u.email, created: u.created, seen: u.seen })) } };
      const sess = rows.filter((r) => r.k === 'ev:session').reduce((x, r) => x + r.n, 0), lg = rows.filter((r) => r.k === 'ev:session_login').reduce((x, r) => x + r.n, 0);
      const split = [['free', '註冊會員', 0.6, 'var(--cat-1)'], ['demo_basic', '基本方案（月）', 0.22, null], ['demo_pro', '進階方案（年）', 0.13, null], ['demo_team', '旗艦方案', 0.05, null]];
      out.tiers = { est: false, list: split.map(([id, name, f, col]) => ({ id, name, n: Math.round(lg * f), col: col || planCol(id), login: true })).concat([{ id: 'guest', name: '訪客', n: sess - lg, col: 'var(--cat-2)', login: false }]) };
      const HW = [0.4, 0.25, 0.18, 0.15, 0.2, 0.45, 1.1, 2.3, 4.6, 6.4, 6.9, 6.1, 5.2, 5.0, 5.8, 5.6, 4.4, 3.4, 3.1, 3.6, 4.6, 5.2, 4.1, 1.8], hs = HW.reduce((a, b) => a + b, 0);
      out.hourly = HW.map((w) => Math.round(rows.filter((r) => r.k.startsWith('pv:')).reduce((a, r) => a + r.n, 0) * w / hs));
      if (live) { const h = []; for (let k = 0; k < 24; k++) h.push(k > hourNow ? 0 : Math.round(54000 / 30 * 1.1 * (k < 6 ? 0.18 : k < 9 ? 0.7 : k < 14 ? 1.5 : 1.1) / 11 * (0.85 + (k * 5 % 7) / 20))); out.hours = h; }
      /* hstat（Worker hourly 區塊同形狀）：今天與期間內各時的 開站／登入／訪客／在線分鐘 */
      const todayH = out.hours || (() => { const h = []; for (let k = 0; k < 24; k++) h.push(k > hourNow ? 0 : Math.round(54000 / 30 * 1.1 * HW[k] / hs * (0.9 + (k * 5 % 7) / 40))); return h; })();
      const mk = (pvArr) => { const open = pvArr.map((x) => Math.round(x * 0.145)), login = open.map((x, k) => Math.round(x * (0.34 + (k % 5) / 60))); return { pv: pvArr, open, login, guest: open.map((x, k) => Math.max(0, x - login[k])), mins: pvArr.map((x) => Math.round(x * 0.9)) }; };
      out.hstat = { today: END, hour: hourNow, since: null, day: mk(todayH), period: Object.assign({ from: out.from, to: out.to }, mk(out.hourly)) };

      return out;
    };
    return { stats, online, members, mstats, mstatsFor, detail, users };
  })();
  function demoWrap(A) {
    if (!IS_PREVIEW || !A || A.__demo) return A;
    const ok = (o) => Promise.resolve(Object.assign({ _s: 200 }, o));
    const W = Object.create(A);
    W.__demo = true;
    W.call = async (path, body) => {
      if (path === '/v1/admin/stats') { const nr = !!window.__demoNoRange; return ok(DEMO.stats((body || {}).days, (body || {}).live, nr ? undefined : (body || {}).from, nr ? undefined : (body || {}).to)); }      // __demoNoRange：測試用，模擬還沒更新的 Worker（不認得 from／to）
      if (path === '/v1/admin/online') return ok(DEMO.online);
      if (path === '/v1/admin/members') return ok({ members: DEMO.members });
      if (path === '/v1/admin/members/stats') return ok(DEMO.mstatsFor(body || {}));
      if (path === '/v1/admin/member/detail') return ok(DEMO.detail(String((body || {}).email || '').toLowerCase()));
      const r = await A.call(path, body);
      if (path === '/v1/admin/perm/list' && r && r._s === 200) {                  // 名單：真資料之外補示範會員（前 12 位掛第一個付費範本，其餘免費）
        const paid = (window.__demoPlan || '');
        const have = new Set((r.users || []).map((u) => u.email));
        r.users = (r.users || []).concat(DEMO.users.filter((u) => !have.has(u.email)));
        r.rows = (r.rows || []).concat(DEMO.users.slice(0, 12).filter((u) => paid).map((u) => ({ email: u.email, plan: paid, n: 0, updated: Date.now(), expires: Date.now() + 25 * 86400000 })));
      }
      if (path === '/v1/admin/plans/get' && r && r._s === 200) { const p = (r.plans || []).find((x) => !x.builtin && x.id !== 'guest' && x.id !== 'free'); window.__demoPlan = p ? p.id : ''; }
      return r;
    };
    return W;
  }
  function render(v, A) {
    css();
    /* 舊網址 #admin/members（會員管理）已併進會員權限：導到 #admin/perm 的「註冊會員」→「會員名單」 */
    if (/^#admin\/members\b/.test(location.hash || '')) { PS.tier = 'free'; PS.sub = 'list'; PS.editMember = false; try { history.replaceState(null, '', '#admin/perm'); } catch (e) { location.hash = '#admin/perm'; } }
    A = demoWrap(A);
    v.classList.toggle('demo', IS_PREVIEW);
    S.v = v; S.A = A;
    [250, 900, 2500, 6000].forEach((ms) => setTimeout(() => { if (v.isConnected) mountDonuts(v); }, ms));   // 保險：MutationObserver 沒接到（echarts／App 較晚就緒）也會補掛
    if (!v._dnMo && window.MutationObserver) { v._dnMo = new MutationObserver(() => { if (v._dnRaf) return; v._dnRaf = requestAnimationFrame(() => { v._dnRaf = 0; mountDonuts(v); }); }); v._dnMo.observe(v, { childList: true, subtree: true }); }
    const t = tabOf();
    if (t !== 'traffic') clearInterval(S.timer);
    if (t === 'perm' || t === 'members') { renderPerm(v, A, t); return; }
    renderTraffic(v, A);
  }

  /* ==========================================================================
     #admin/traffic 流量觀測
     ========================================================================== */
  function renderTraffic(v, A) {
    v.innerHTML = `${document.documentElement.classList.contains('l4') ? '' : head(v, A) + '</div>'}<div id="admBody"><div class="card" style="margin-top:14px"><p class="use">載入中…</p></div></div>`;
    wireHead(v);
    paint();
    clearInterval(S.timer);
    S.timer = setInterval(() => { if (tabOf() === 'traffic' && (location.hash || '').startsWith('#admin') && document.visibilityState !== 'hidden') paint(); else if (!(location.hash || '').startsWith('#admin')) clearInterval(S.timer); }, 30000);
  }

  /* ==========================================================================
     流量觀測（2026-10-05 Andy 新規格）
     上方一排：每天直條＋登入甜甜圈（期間選單：即時／近 N 天／指定日期到現在）。
     下方：活頁簿式分頁（全部＋側欄 10 個頁面＋個股頁），每頁有子分頁；每個分頁＝左長條＋右甜甜圈。
     「頁面」是管理區自己的分類：把 Worker 回的 (頁面, 元件, 細項, 次數) 依 PAGES 設定歸到側欄的頁面與子分頁。
     ========================================================================== */
  const PG_H = [190, 262, 36, 150, 338, 56, 214, 14, 292, 98, 170];            // 各頁色相；子分頁在同色相上微調明度／色相
  /* 頁面設定：k 鍵、n 名稱、subs（子分頁：k、n、cs＝歸屬的元件，'x.*' 為前綴）、sk＝子分頁開啟事件 sub.<鍵> 的頁面鍵 */
  const PAGES = [
    { k: 'events', n: '事件', simple: true, subs: [] },
    { k: 'market', n: '市場明細', simple: true, subs: [] },
    { k: 'season', n: '週期統計', simple: true, subs: [] },
    { k: 'flow', n: '資金流向', sk: 'flow', subs: [{ k: 'rotation', n: '資金輪動', cs: ['play', 'quad', 'filter_*', 'clock_group', 'rank_bar'] }, { k: 'sankey', n: '資金去向', cs: ['sankey.*'] }, { k: 'inst', n: '族群×法人', cs: ['inst.*'] }] },
    { k: 'heatmap', n: '熱力圖', sk: 'heatmap', subs: [{ k: 'industry', n: '產業', cs: ['heat_tile'] }, { k: 'theme', n: '題材', cs: ['theme.*'] }] },
    { k: 'industry', n: '產業地圖', sk: 'industry', subs: [{ k: 'chains', n: '產業鏈總覽', cs: [] }, { k: 'chain', n: '單一產業鏈', cs: [] }, { k: 'group', n: '族群頁', cs: [] }] },
    { k: 'explore', n: '選股策略', subs: [] },
    { k: 'etf', n: 'ETF', subs: [] },
    { k: 'watch', n: '自選', subs: [] },
    { k: 'support', n: '客服', subs: [] },
    { k: 'stock', n: '個股', subs: [{ k: 'tabs', n: '分頁點擊', cs: ['tab.*'] }, { k: 'kline', n: 'K 線指標', cs: ['ind', 'indicators', 'kp.*', 'draw', 'draw.*', 'mtf', 'ai_tab', 'open_3d'] }] },
    { k: 'users', n: '使用者', sp: 'users', subs: [] },
  ];
    const PAGE_BY = Object.fromEntries(PAGES.map((p) => [p.k, p]));
  /* 這些元件的「細項」是值得單獨排行的對象（族群／個股／類別…）；其餘元件只統計次數 */
  const DETK = { filter_group: '族群', rank_bar: '族群', clock_group: '族群', heat_tile: '族群', filter_chain: '產業鏈', view: '個股', 'etf.cat': 'ETF 類別', 'explore.topic': '選股題目', 'support.faq': '常見問題', 'support.tab': '客服項目', ind: '技術指標', 'draw.tool': '畫線工具', events_drawer: '來源頁面', 'theme.pick': '題材' };
  const kindOf = (comp) => DETK[comp] || (/^tab\./.test(comp) ? '個股' : '');
  const compIn = (comp, cs) => cs.some((c) => (c.endsWith('*') ? comp.startsWith(c.slice(0, -1)) : comp === c));
  function classify(r) {
    let pg = null, det = r.detail || '';
    if (r.comp === 'events_drawer') { pg = 'events'; det = VIEW_NAME[r.page] || r.page; }
    else if (r.page === 'other') { const m = /^(etf|explore|support|events)\./.exec(r.comp); pg = m ? m[1] : null; }      // 舊資料（切換前記在 other＋前綴）
    /* 新資料：Worker 已收 etf／explore／support／events 等頁面鍵，PAGE_BY 認得就直接歸該頁（兩種寫法加總才是完整期間） */
    else if (PAGE_BY[r.page]) pg = r.page;
    return pg ? { pg, comp: r.comp, det, n: r.n } : null;
  }
  const pgCol = (i, j, m) => { const hs = m > 6 ? 7 : 14, ls = m > 6 ? 3.2 : 9, dh = m > 1 ? (j - (m - 1) / 2) * hs : 0, dl = m > 1 ? (j - (m - 1) / 2) * ls : 0; return `hsl(${PG_H[i] + dh} 72% calc(var(--pgL,58%) + ${dl}%))`; };
  const sum = (a) => a.reduce((s, x) => s + x, 0);
  const todayTpe = () => new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10);
  const periodDays = () => (S.period === 'live' ? 1 : S.period === 'since' ? Math.max(1, Math.min(400, Math.floor((Date.parse(new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10) + 'T00:00:00Z') - Date.parse(S.since + 'T00:00:00Z')) / 86400000) + 1)) : +S.period);
  const periodTxt = () => (S.period === 'live' ? '即時（今天 0–24 時）' : S.period === 'since' ? `${S.since}～${S.until || '至今'}` : `近 ${S.period} 天`);

  async function paint() {
    const v = S.v, A = S.A; if (!v || !A) return;
    if (S.period === 'since' && !/^\d{4}-\d{2}-\d{2}$/.test(S.since || '')) S.period = '30';
    const [st, on] = await Promise.all([A.call('/v1/admin/stats', Object.assign({ days: periodDays(), live: S.period === 'live' ? 1 : 0 }, S.period === 'since' ? { from: S.since, to: S.until || todayTpe() } : {})), A.call('/v1/admin/online', {})]);
    if (!(location.hash || '').startsWith('#admin') || tabOf() !== 'traffic' || !v.querySelector('#admBody')) return;
    if (!st || st._s !== 200 || !on || on._s !== 200) {
      v.querySelector('#admBody').innerHTML = `<div class="card" style="margin-top:14px"><p class="err">讀不到報表（${st ? st._s : '連不到伺服器'}）</p></div>`;
      return;
    }
    /* 點每日直條 → 下面那組統計換成那一天：再打一次 stats 帶 from＝to＝那天。Worker 不認得 from／to（會員系統還沒更新）時，
       回來的起訖不會是那一天 → 改成提示並維持整段期間的統計，畫面不留空白 */
    let stT = st; S.dayMode = '';
    if (S.day) {
      const dTo = S.dayTo || S.day;
      const r = await A.call('/v1/admin/stats', { days: Math.min(400, periodDays() + 1), from: S.day, to: dTo });
      if (r && r._s === 200 && r.from === S.day && r.to === dTo) { stT = r; S.dayMode = 'ok'; } else S.dayMode = 'unsupported';
    }
    S.st = stT; S.on = on;
    const pv = {}, ev = {}, perDay = {};
    const untilDay = S.period === 'since' && S.until && /^\d{4}-\d{2}-\d{2}$/.test(S.until) && S.until < st.to ? S.until : '';      // 結束日（預設＝至今）：只影響上方一排；Worker 只能算到今天，分頁統計仍含到今天
    st.rows.forEach((r) => {
      const [kind, name] = r.k.split(':'), inTop = !untilDay || r.day <= untilDay;
      if (kind === 'pv') { pv[name] = (pv[name] || 0) + r.n; if (inTop) perDay[r.day] = (perDay[r.day] || 0) + r.n; } else if (inTop) ev[name] = (ev[name] || 0) + r.n;
    });
    const e2 = Array.isArray(stT.e2) ? stT.e2 : [];
    const pvT = {}; stT.rows.forEach((r) => { if (r.k.startsWith('pv:')) pvT[r.k.slice(3)] = (pvT[r.k.slice(3)] || 0) + r.n; });
    const pvDay = {}; stT.rows.forEach((r) => { if (r.k.startsWith('pv:')) { const k = r.k.slice(3); (pvDay[k] = pvDay[k] || {})[r.day] = (pvDay[k][r.day] || 0) + r.n; } });
    let days = [], dmap = perDay;
    if (S.period === 'live' && st.hours) { days = st.hours.map((_, h) => String(h).padStart(2, '0') + ':00'); dmap = {}; const nowH = st.hstat && Number.isInteger(st.hstat.hour) ? st.hstat.hour : null; st.hours.forEach((n, h) => { dmap[days[h]] = nowH != null && h > nowH ? null : n; }); }
    else for (let t = Date.parse(st.from + 'T00:00:00Z'); t <= Date.parse((untilDay || st.to) + 'T00:00:00Z'); t += 86400000) days.push(new Date(t).toISOString().slice(0, 10));
    /* 橫軸一律涵蓋整個選定期間（沒紀錄的日子是 0）；期間長就合併粒度：≤31 天按日、32～120 天按週（從起日起每 7 天一格）、>120 天按月 */
    const bk = S.period === 'live' && st.hours ? null : bucketize(days);
    const pvAgg = (m) => { if (!bk || bk.gran === 'day') return m; const o = {}; bk.keys.forEach((k) => { o[k] = 0; }); Object.keys(m).forEach((d) => { const k = bk.of[d]; if (k !== undefined) o[k] += m[d]; }); return o; };
    if (bk && bk.gran !== 'day') { dmap = pvAgg(perDay); days = bk.keys.slice(); }
    const dmax = Math.max(1, ...days.map((d) => dmap[d] || 0));
    const sessions = ev.session || 0, loginSess = Math.min(ev.session_login || 0, sessions), pvTotal = untilDay ? sum(Object.values(perDay)) : sum(Object.values(pv));
    // 個股相關（個股頁分頁用）：被觀看 Top 10、各自最常用的功能、散佈圖點
    const views = e2.filter((r) => r.page === 'stock' && r.comp === 'view' && r.detail).sort((a, b) => b.n - a.n);
    const useBy = {};
    e2.filter((r) => r.page === 'stock' && r.comp !== 'view' && r.detail).forEach((r) => { (useBy[r.detail] = useBy[r.detail] || []).push(r); });
    S.stk = { featRows: views.slice(0, 10).map((r) => { const u = (useBy[r.detail] || []).sort((a, b) => b.n - a.n); return { code: r.detail, views: r.n, top: u.slice(0, 3) }; }),
      scat: views.slice(0, 30).map((r) => ({ code: r.detail, x: r.n, y: ((useBy[r.detail] || []).reduce((s, x) => s + x.n, 0)) / Math.max(1, r.n) })) };
    // 依 PAGES 歸類：S.data[頁] = { pv, rows:[{comp,det,n,sub}], opens:{子頁:次數} }
    const data = {};
    PAGES.filter((p) => !p.sp).forEach((p) => { data[p.k] = { pv: pvT[p.k] || 0, rows: [], opens: {} }; });
    e2.forEach((r) => {
      if (r.comp.startsWith('sub.')) { const d = data[r.page]; if (d) d.opens[r.comp.slice(4)] = (d.opens[r.comp.slice(4)] || 0) + r.n; return; }
      const c = classify(r); if (!c) return;
      const p = PAGE_BY[c.pg], sub = (p.subs.find((s) => compIn(c.comp, s.cs)) || {}).k || '';
      data[c.pg].rows.push({ comp: c.comp, det: c.det, n: c.n, sub });
    });
    PAGES.forEach((p, i) => {
      if (p.sp) return;
      const d = data[p.k], use = sum(d.rows.map((r) => r.n));
      d.use = use; d.fb = !d.pv;                                                  // fb＝沒有瀏覽數（Worker 只記 pv 給舊頁面鍵）→ 改用功能使用次數
      d.subN = p.subs.map((s, j) => ({ k: s.k, n: s.n, v: d.opens[s.k] != null ? d.opens[s.k] : sum(d.rows.filter((r) => r.sub === s.k).map((r) => r.n)), col: pgCol(i, j, p.subs.length) }));
      d.total = d.pv || (sum(d.subN.map((x) => x.v)) || use);
      if (p.subs.length && sum(d.subN.map((x) => x.v)) > 0 && d.pv) { /* 有子頁開啟數：總數仍用 pv */ }
    });
    S.data = data; S.days = periodDays(); S.bk = null;
    if (st.hours) { S.pvDay = pvDay; S.dayList = []; }
    else if (S.dayMode === 'ok') {                          // 點了某一天／某一週／某一月：下面各分頁的每日趨勢只畫那段（≤ 31 天按日）
      const dl = []; for (let t = Date.parse(S.day + 'T00:00:00Z'); t <= Date.parse((S.dayTo || S.day) + 'T00:00:00Z'); t += 86400000) dl.push(new Date(t).toISOString().slice(0, 10));
      S.pvDay = pvDay; S.dayList = dl;
    } else { S.bk = bk; S.dayList = days.slice(); S.pvDay = {}; Object.keys(pvDay).forEach((k) => { S.pvDay[k] = pvAgg(pvDay[k]); }); }
    S.firstDay = Object.keys(perDay).filter((d) => perDay[d] > 0).sort()[0] || ''; S.pvAll = sum(Object.values(pvT));
    data.users = { pv: 0, rows: [], opens: {}, subN: [], total: (stT.users && stT.users.total) || 0, use: 0, fb: false };
    const tiers = st.tiers || await estimateTiers(A, st, sessions, loginSess);
    v.querySelector('#admBody').innerHTML = topHtml(st, days, dmap, dmax, sessions, loginSess, pvTotal, tiers, bk) + `<div class="secttl" id="trDetailTtl"><h2>分頁統計</h2>${dayChip()}</div><div class="card trtabs" id="trDetail"><div id="trTabsBox"></div><div id="trPageBody"></div></div>`;
    wireTop(v, A);
    paintTrTabs();
    bindHover(v.querySelector('#admBody'));
  }
  const WK = '日一二三四五六';
  const dayTxt = (d) => `${+d.slice(5, 7)} 月 ${+d.slice(8, 10)} 日（週${WK[new Date(Date.parse(d + 'T00:00:00Z')).getUTCDay()]}）`;
  /* 現在看的是哪一天：分頁統計標題旁一顆小膠囊＋清除鈕；Worker 不支援時直接說白話 */
  function dayChip() {
    if (!S.day) return '';
    return `<span class="daychip" id="trDayChip"><i class="dot"></i><b>${esc(S.dayTo && S.dayTo !== S.day ? S.day.slice(5) + '～' + S.dayTo.slice(5) : dayTxt(S.day))}</b>${S.dayMode === 'unsupported' ? '<em>這個功能要等會員系統更新後才有，下方暫時顯示整段期間</em>' : ''}<button type="button" id="trDayClr" aria-label="清除，回到原期間" title="清除，回到原期間">×</button></span>`;
  }
  function topHtml(st, days, dmap, dmax, sessions, loginSess, pvTotal, tiers, bk) {
    const opt = [['live', '即時'], ['7', '近 7 天'], ['30', '近 30 天'], ['90', '近 90 天'], ['365', '近 365 天'], ['since', '起始日期～至今']];
    /* 起訖日期框永遠顯示：跟著期間選單同步（近 N 天＝那段的實際起訖、即時＝今天），手動改日期 → 下拉跳成「起始日期～至今」 */
    const today = todayTpe(), shiftDay = (d, n) => new Date(Date.parse(d + 'T00:00:00Z') + n * 86400000).toISOString().slice(0, 10);
    const rng = S.period === 'live' ? { from: today, to: today } : S.period === 'since' ? { from: S.since, to: S.until || today } : { from: shiftDay(today, -(+S.period - 1)), to: today };
    const gw = bk && bk.gran === 'week' ? '每週' : bk && bk.gran === 'month' ? '每月' : '每天';
    const dsub = S.period === 'live' ? '今天 0–24 時每小時的頁面瀏覽' : gw + '的頁面瀏覽總次數';
    const first = S.period === 'live' ? '' : (S.firstDay && S.firstDay > days0(days, bk) ? `統計自 ${S.firstDay} 開始記錄，之前沒有紀錄（算 0）。` : '這段期間每天都有紀錄。');
    const dtip = first + (bk && bk.gran !== 'day' ? `期間較長，已合併成${gw.slice(1)}一格；點一格可看那段的統計。` : '點某天的直條可看當天。');
    return `<div class="secttl trhead"><h2>全站總覽</h2><small>共 ${nf(pvTotal)} 次瀏覽・${nf(sessions)} 次開站</small><span class="sp"></span>
        ${window.RangePick.html({ cls: 'trctl', options: opt, value: S.period, from: rng.from, to: rng.to, max: todayTpe(), custom: 'since',
          ids: { sel: 'admDaysSel', from: 'admSince', to: 'admUntil' },   // 期間列抽成共用元件 site/rangepick.js（10-06，ETF 報酬比較同一支）；id 沿用，驗收靠它們
          extra: `<button type="button" class="icobtn" id="admRefresh" title="重新整理" aria-label="重新整理"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12a9 9 0 0 0-15.5-6.2L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 15.5 6.2L21 16"/><path d="M16 16h5v5"/></svg></button>
          <span class="qtip" id="trPrivacy" tabindex="0" role="note" aria-label="隱私說明" title="使用統計只記「每天每一項的次數」（不記是誰、不存 IP），保留 13 個月；細項只存族群名、股票代號、元件名，不存任何人打的字。線上狀態離線即刪。">?</span>` })}</div>
      <div class="admgrid trtop">
        <div class="card s2" id="admDays"><h3>${S.period === 'live' ? '每小時' : gw}有多少瀏覽？<span class="qtip" id="trDayTip" tabindex="0" role="note" aria-label="說明" title="${esc(dtip)}">?</span></h3><p class="use" title="${esc(dsub)}">${esc(dsub)}</p><div class="cb">${dayChart(days, dmap, dmax, 'admDayBars', S.period === 'live', bk)}</div></div>
        <div class="card" id="trDonut"><h3>開網站的人有多少是登入的？</h3><p class="use" title="訪客、註冊會員、各付費方案各一段${tiers.est ? '（付費與免費依會員名單比例估算）' : ''}">${tiers.est ? '開站身分（估算）' : '開站身分'}</p><div class="cb">${loginDonut(tiers.list, sessions)}</div></div>
      </div>`;
  }

  /* 開站身分甜甜圈：訪客｜註冊會員（免費）｜各付費方案（每個付費範本一段）。登入的幾段（註冊＋各付費）同一組、彼此相連，與訪客之間留 2° 間隙。
     顏色：訪客＝類別色 2、註冊＝類別色 1、付費方案＝依方案 id 雜湊固定色（新增方案多一色、既有方案不跳色）。
     正式站 Worker 目前沒有「開站時的會員等級」欄位 → estimateTiers 依 plans／perm 名單人數比例拆登入人數（標「估算」）；示範資料直接給 st.tiers。 */
  const PLAN_H = [38, 152, 330, 18, 96, 208, 298, 58];
  const planCol = (id) => { let h = 0; String(id).split('').forEach((c) => { h = (h * 31 + c.charCodeAt(0)) % 9973; }); return `hsl(${PLAN_H[h % PLAN_H.length]} 74% calc(var(--pgL,58%) + 2%))`; };
  async function estimateTiers(A, st, sessions, loginSess) {
    const guest = Math.max(0, sessions - loginSess), list = [{ id: 'guest', name: '訪客', n: guest, col: 'var(--cat-2)', login: false }];
    let plans = null, perm = null;
    try { const [pl, li] = await Promise.all([A.call('/v1/admin/plans/get', {}), A.call('/v1/admin/perm/list', {})]); if (pl && pl._s === 200) plans = pl.plans || []; if (li && li._s === 200) perm = li.rows || []; } catch (e) { /* 取不到就只分登入／訪客 */ }
    const total = Math.max(1, (st.users && st.users.total) || 0), paidP = (plans || []).filter((p) => !p.builtin && p.id !== 'guest' && p.id !== 'free' && !/^(訪客|註冊會員|免費會員|付費會員)/.test(p.name || ''));
    const cnt = {}; (perm || []).forEach((r) => { if (paidP.some((p) => p.id === r.plan) && !(r.expires && r.expires < Date.now())) cnt[r.plan] = (cnt[r.plan] || 0) + 1; });
    const paidN = Object.values(cnt).reduce((a, b) => a + b, 0);
    list.unshift({ id: 'free', name: '註冊會員', n: Math.round(loginSess * Math.max(0, total - paidN) / total), col: 'var(--cat-1)', login: true });
    paidP.forEach((p) => { if (cnt[p.id]) list.splice(list.length - 1, 0, { id: p.id, name: p.name, n: Math.round(loginSess * cnt[p.id] / total), col: planCol(p.id), login: true }); });
    return { list, est: true };
  }
  function loginDonut(list, sessions) {
    const tot = sum(list.map((t) => t.n)); if (!tot) return '<div class="empty">沒有資料</div>';
    const login = sum(list.filter((t) => t.login).map((t) => t.n));
    const segs = list.map((t) => ({ label: t.name, n: t.n, color: t.col, g: t.login ? 'in' : 'guest', ltxt: `${nf(t.n)}・${(t.n / tot * 100).toFixed(1)}%` }));
    return donutG(segs, { center: ['登入', Math.round(login / tot * 100) + '%'], legendN: 8, legend: segs.map((x) => Object.assign({}, x)), aria: '開站身分占比' });
  }
  /* 只統計「有沒有被看」的頁（週期統計、市場明細、事件）：被看幾次、每天趨勢、占全站比；不放子頁與功能細項（Andy 10-05） */
  function simpleHtml(p, d, idx) {
    const pd = (S.pvDay || {})[p.k] || {}, has = Object.keys(pd).length > 0 && S.dayList && S.dayList.length;
    const tot = d.total;
    const chart = has ? dayChart(S.dayList, pd, Math.max(1, ...Object.values(pd)), 'trPgDays', false, S.bk) : '<div class="empty">沒有資料</div>';
    return `<div class="admgrid trone"><div class="card" id="trS1"><h3>${esc(p.n)}被看了幾次？</h3><p class="use" title="${esc(p.n)}">被看過幾次</p>
      <div class="cb"><div class="sbody"><div class="bigno"><b>${nf(tot)}</b><span>被看過</span></div><div class="sch">${chart}</div></div></div></div></div>`;
  }
  /* 使用者分頁：使用時段（每小時直條，可切 1H／4H／6H／12H／白天／夜晚）＋ 現在誰在線 ＋ 最近會員 */
  const HR_MODES = [['1', '1H'], ['4', '4H'], ['6', '6H'], ['12', '12H'], ['day', '白天'], ['night', '夜晚']];
  /* 把 24 小時的數列合併成 1H／4H／6H／12H／白天／夜晚：series＝[{k,name,col,arr:[24]}]（一條＝一種顏色；兩條就堆疊） */
  function hourData(series, mode) {
    const two = (n) => String(n).padStart(2, '0'), pad = (a) => { const h = (a || []).slice(0, 24); while (h.length < 24) h.push(0); return h; };
    const ss = series.map((x) => ({ ...x, arr: pad(x.arr) }));
    const pick = (hs) => hs.map((x) => ({ l: two(x), tip: `${two(x)}:00–${two((x + 1) % 24)}:00`, v: ss.map((q) => q.arr[x]) }));
    if (mode === 'day') return pick(Array.from({ length: 12 }, (_, i) => 6 + i));
    if (mode === 'night') return pick(Array.from({ length: 12 }, (_, i) => (18 + i) % 24));
    const w = +mode || 1;
    return Array.from({ length: 24 / w }, (_, i) => ({ l: w === 1 ? two(i) : `${two(i * w)}–${two((i + 1) * w % 24)}`, tip: `${two(i * w)}:00–${two((i + 1) * w % 24)}:00`, v: ss.map((q) => sum(q.arr.slice(i * w, i * w + w))) }));
  }
  function usersBody() {
    const st = S.st, on = S.on, mode = S.hr || '1', hm = S.hm || 'pv', hs = st.hstat || null, live = S.period === 'live';
    const src = live ? { pv: st.hours, login: hs && hs.day && hs.day.login, guest: hs && hs.day && hs.day.guest } : { pv: st.hourly, login: hs && hs.period && hs.period.login, guest: hs && hs.period && hs.period.guest };
    const has = hm === 'open' ? !!(src.login && src.guest) : !!src.pv;
    const series = hm === 'open' ? [{ k: 'guest', name: '訪客開站', col: 'var(--cat-2)', arr: src.guest }, { k: 'login', name: '登入開站', col: 'var(--cat-1)', arr: src.login }] : [{ k: 'pv', name: '頁面瀏覽', col: 'var(--cat-1)', arr: src.pv }];
    const hd = has ? hourData(series, mode) : null;
    let chart;
    if (!hd) chart = '<div class="empty">沒有資料</div>';
    else { const tots = hd.map((x) => sum(x.v)), mx = Math.max(1, ...tots), all = sum(tots), few = hd.length <= 7;
      chart = `<div class="dayplot"><div class="dayy">${[1, 0.75, 0.5, 0.25, 0].map((f) => `<span>${nf(Math.round(mx * f))}</span>`).join('')}</div>
        <div class="days hrs${few ? ' few' : ''}${hm === 'open' ? ' stk2' : ''}" data-chart="days" id="trHrBars">${hd.map((x, i) => { const tot = tots[i];
          const tip = tp(`<b>${x.tip}</b><br>${hm === 'open' ? `${series.map((q, j) => `${q.name} ${nf(x.v[j])}`).join('・')}<br>合計 ${nf(tot)} 次・占 ${(tot / Math.max(1, all) * 100).toFixed(1)}%` : `${nf(tot)} 次・占 ${(tot / Math.max(1, all) * 100).toFixed(1)}%`}`);
          return `<div class="dc" data-row="${i}"${tip}>${few ? `<span class="dv">${nf(tot)}</span>` : ''}${series.map((q, j) => `<i style="height:${(x.v[j] / mx * 100).toFixed(1)}%;${hm === 'open' ? `background:${q.col}` : ''}"></i>`).join('')}<span class="dd">${x.l}</span></div>`; }).join('')}</div></div>
        ${hm === 'open' ? `<div class="hrlg"><span><i style="background:var(--cat-2)"></i>訪客開站</span><span><i style="background:var(--cat-1)"></i>登入開站</span></div>` : ''}`; }
    const since = hs && hs.since && st.from && hs.since > st.from ? `<div class="hrnote">每小時統計從 ${esc(hs.since)} 起</div>` : '';
    const modes = `<div class="hrbar"><div class="nbsw lv2 hrmodes" id="trHrMetric" role="tablist">${[['pv', '頁面瀏覽'], ['open', '開站（登入／訪客）']].map(([k, n]) => `<button type="button" role="tab" data-hm="${k}" class="${hm === k ? 'on' : ''}">${n}</button>`).join('')}</div>
      <div class="nbsw lv2 hrmodes" id="trHrModes" role="tablist">${HR_MODES.map(([k, n]) => `<button type="button" role="tab" data-hr="${k}" class="${mode === k ? 'on' : ''}">${n}</button>`).join('')}</div></div>`;
    const clock = clockHtml(series.length === 2 ? src.login.map((x, i) => x + (src.guest[i] || 0)) : src.pv, hm === 'open' ? '開站' : '瀏覽');
    return `<div class="admgrid trpair trusers">
      <div class="card" id="trHours"><h3>什麼時段最多人用？</h3><p class="use" title="每小時的${hm === 'open' ? '開站次數（登入／訪客堆疊）' : '頁面瀏覽次數'}。白天＝06:00–18:00、夜晚＝18:00–06:00。">白天 06–18／夜晚 18–06</p><div class="cb">${modes}${chart}${since}</div></div>
      <div class="card" id="trClock"><h3>24 小時時鐘</h3><p class="use" title="12 小時錶面、頂端是 12／0、順時針；內圈＝00:00–11:59、外圈＝12:00–23:59；長度與顏色深淺＝該小時的${hm === 'open' ? '開站' : '瀏覽'}量">內圈上午・外圈下午</p><div class="cb">${clock}</div></div></div>`;
  }
  /* 時鐘（12 小時錶面＋內外兩圈）：頂端是 12／0，順時針 12 格；內圈＝00:00–11:59（上午）、外圈＝12:00–23:59（下午），同一個鐘點方向上下午對齊；
     每段長度與顏色深淺＝該小時使用量（兩圈共用同一把尺）；中心＝尖峰時段；圖例在右 */
  function clockHtml(arr, what) {
    const h = (arr || []).slice(0, 24); while (h.length < 24) h.push(0);
    const tot = sum(h); if (!tot) return '<div class="empty">沒有資料</div>';
    const mx = Math.max(...h), two = (n) => String(n).padStart(2, '0'), AM = 'var(--cat-3)', PM = 'var(--cat-2)';
    const BAND = { am: [22, 32], pm: [35, 47] };
    const P = (r, deg) => `${(60 + r * Math.sin(deg * Math.PI / 180)).toFixed(2)} ${(60 - r * Math.cos(deg * Math.PI / 180)).toFixed(2)}`;
    const wedge = (a0, a1, r0, r1) => `M ${P(r0, a0)} L ${P(r1, a0)} A ${r1} ${r1} 0 0 1 ${P(r1, a1)} L ${P(r0, a1)} A ${r0} ${r0} 0 0 0 ${P(r0, a0)} Z`;
    let tr = '', vl = '';
    h.forEach((n, x) => {
      const pm = x >= 12, pos = x % 12, [r0, r1] = BAND[pm ? 'pm' : 'am'], a0 = pos * 30 + 1.2, a1 = pos * 30 + 28.8, col = pm ? PM : AM, pct = (n / tot * 100).toFixed(1) + '%', lab = `${two(x)}:00–${two(x)}:59`;
      tr += `<path d="${wedge(a0, a1, r0, r1)}" fill="${col}" fill-opacity=".13"/>`;
      const r = r0 + Math.max(1.6, (r1 - r0) * n / mx), op = (0.4 + 0.6 * n / mx).toFixed(2);
      vl += `<path class="arc" data-row="${x}" data-k="${pm ? 'pm' : 'am'}" data-lab="${lab}" data-pct="${pct}"${tp(`<b>${lab}</b>　${nf(n)} 次${what}・占 ${pct}`)} d="${wedge(a0, a1, r0, r)}" fill="${col}" fill-opacity="${op}"/>`;
    });
    const amN = sum(h.slice(0, 12)), pmN = tot - amN, top = h.map((n, x) => [n, x]).sort((a, b) => b[0] - a[0]).slice(0, 3);
    const pk = top[0][1], c2 = `${two(pk)} 時`;
    const lbl = [[0, '12'], [90, '3'], [180, '6'], [270, '9']].map(([d, t]) => { const q = P(54, d).split(' '); return `<text x="${q[0]}" y="${(+q[1] + 2.5).toFixed(2)}" text-anchor="middle" style="font-size:7px;fill:var(--ink-2);font-family:var(--mono)">${t}</text>`; }).join('');
    const li = (k, col, name, n, rg) => `<li data-k="${k}" data-n="${n}"${tp(`<b>${esc(name)}（${rg}）</b><br>${nf(n)} 次${what}・占 ${(n / tot * 100).toFixed(1)}%`)}><i style="background:${col}"></i><span>${esc(name)}</span><b>${nf(n)}</b><small>${(n / tot * 100).toFixed(1)}%</small></li>`;
    return `<div class="dn clock" data-chart="donut"><svg viewBox="0 0 120 120" data-d1="尖峰時段" data-d2="${c2}" role="img" aria-label="12 小時錶面、內圈上午外圈下午的使用時鐘">${tr}${vl}${lbl}
      <text class="c1" x="60" y="56" text-anchor="middle" style="font-size:5.4px;fill:var(--ink-2)">尖峰時段</text><text class="c2" x="60" y="67" text-anchor="middle" style="font-size:9px;font-weight:700;fill:var(--ink);font-family:var(--mono)">${c2}</text></svg>
      <ul class="lg">${li('am', AM, '內圈 上午', amN, '00:00–11:59')}${li('pm', PM, '外圈 下午', pmN, '12:00–23:59')}${top.map(([n, x], i) => `<li data-row="${x}"${tp(`<b>${two(x)}:00–${two(x)}:59</b>　${nf(n)} 次${what}・占 ${(n / tot * 100).toFixed(1)}%`)}><i style="background:${x >= 12 ? PM : AM};opacity:${(0.4 + 0.6 * n / mx).toFixed(2)}"></i><span>${i === 0 ? '尖峰' : i === 1 ? '次忙' : '再次'} ${two(x)} 時</span><b>${nf(n)}</b><small>${(n / tot * 100).toFixed(1)}%</small></li>`).join('')}</ul></div>`;
  }
  function wireTop(v, A) {
    const apply = () => { S.tab = S.tab || 'all'; paint(); };
    const okD = (x) => /^\d{4}-\d{2}-\d{2}$/.test(x);
    // 下拉／日期框的同步規則在 site/rangepick.js（手改日期 → 下拉跳「起始日期～至今」）；這裡只管期間狀態怎麼存
    window.RangePick.bind(v.querySelector('#admDaysSel').closest('.rpk'), { onChange: ({ value, from, to, manual }) => {
      S.day = ''; S.dayTo = '';
      if (!manual) { S.period = value; if (S.period === 'since') S.since = S.since || from; apply(); return; }
      if (!okD(from)) return;
      let t = okD(to) ? to : todayTpe(); if (t < from) t = from;
      S.period = 'since'; S.since = from; S.until = t >= todayTpe() ? '' : t; apply();
    } });
    const dv = v.querySelector('#admDays'); if (dv) dv.onclick = (e) => { const dc = e.target.closest('.dc[data-day]'); if (!dc || S.period === 'live') return; const tgl = S.day === dc.dataset.day && (S.dayTo || S.day) === (dc.dataset.to || dc.dataset.day); S.day = tgl ? '' : dc.dataset.day; S.dayTo = tgl ? '' : (dc.dataset.to || dc.dataset.day); paint(); };
    const dcl = v.querySelector('#trDayClr'); if (dcl) dcl.onclick = () => { S.day = ''; S.dayTo = ''; paint(); };
    v.querySelector('#admRefresh').onclick = (e) => { const b = e.currentTarget; b.classList.remove('spin'); void b.offsetWidth; b.classList.add('spin'); S.spin = true; paint(); };
    if (S.spin) { S.spin = false; const rb = v.querySelector('#admRefresh'); if (rb) rb.classList.add('spin'); }
  }


  /* ==== 管理區所有圖表的一致互動（Andy 10-05）：滑過高亮該柱／扇區／點（其餘變淡）＋浮動提示（名稱、數值、占比）＋甜甜圈中心字換成該段；
     圖例滑過連動高亮；點擊：「全部」頁的長條／扇區進入該頁（其餘圖沒有可進的下一層，只提示）。事件委派在 #admBody 上，圖重畫不用重綁。 */
  function tipEl() { let t = document.getElementById('trTip'); if (!t) { t = document.createElement('div'); t.id = 'trTip'; t.hidden = true; t.setAttribute('role', 'tooltip'); document.body.appendChild(t); } return t; }
  function hovClear(chart) {
    if (!chart) return;
    chart.classList.remove('hov'); chart.querySelectorAll('.hl').forEach((e) => e.classList.remove('hl'));
    const sv = chart.querySelector('svg[data-d1]'); if (sv) { sv.querySelector('.c1').textContent = sv.dataset.d1; sv.querySelector('.c2').textContent = sv.dataset.d2; }
    tipEl().hidden = true;
  }
  function bindHover(root) {
    if (!root || root._hov) return; root._hov = true;
    const place = (x0, y0) => { const t = tipEl(); if (t.hidden) return; const w = t.offsetWidth, h = t.offsetHeight; let x = x0 + 14, y = y0 + 16; if (x + w > innerWidth - 8) x = x0 - w - 14; if (y + h > innerHeight - 8) y = y0 - h - 12; t.style.left = Math.max(8, x) + 'px'; t.style.top = Math.max(8, y) + 'px'; };
    /* 高亮＋提示（滑鼠滑過與觸控點一下共用）：target＝事件目標，(x,y)＝提示位置；回傳是否真的有東西可以顯示 */
    const show = (target, x, y) => {
      const chart = target.closest && target.closest('[data-chart]'); if (!chart) return false;
      hovClear(chart);
      const idEl = target.closest('[data-row]'), lg = target.closest('li[data-k]'), te = target.closest('[data-tip]');
      let swap = null;
      if (idEl && chart.contains(idEl)) {
        chart.classList.add('hov');
        chart.querySelectorAll(`[data-row="${idEl.dataset.row}"]`).forEach((q) => q.classList.add('hl'));
        if (idEl.matches('.arc')) { chart.querySelectorAll(`li[data-k="${CSS.escape(idEl.dataset.k)}"]`).forEach((q) => q.classList.add('hl')); swap = [idEl.dataset.lab || idEl.dataset.k, idEl.dataset.pct || (idEl.dataset.tip.match(/（([\d.]+%)）/) || [])[1]]; }
      } else if (lg && chart.contains(lg)) {
        chart.classList.add('hov');
        const k = CSS.escape(lg.dataset.k); chart.querySelectorAll(`[data-k="${k}"]`).forEach((q) => q.classList.add('hl'));
        swap = [lg.dataset.k, (lg.querySelector('small') || {}).textContent];
      }
      const sv = chart.querySelector('svg[data-d1]'); if (sv && swap && swap[1]) { sv.querySelector('.c1').textContent = swap[0]; sv.querySelector('.c2').textContent = swap[1].replace(/^.*・/, ''); }
      if (te && te.dataset.tip) { const t = tipEl(); t.innerHTML = te.dataset.tip; t.hidden = false; place(x, y); return true; }
      return false;
    };
    const clearAll = () => { root.querySelectorAll('[data-chart].hov').forEach(hovClear); tipEl().hidden = true; S.tapEl = null; };
    root.addEventListener('mouseover', (e) => { if (S.touching) return; show(e.target, e.clientX, e.clientY); });
    root.addEventListener('mousemove', (e) => { if (!S.touching) place(e.clientX, e.clientY); });
    root.addEventListener('mouseout', (e) => { if (S.touching) return; const chart = e.target.closest && e.target.closest('[data-chart]'); if (!chart) return; if (e.relatedTarget && chart.contains(e.relatedTarget)) return; hovClear(chart); });
    /* 觸控（手機）：點一下圖就出提示＋高亮，點圖外面收起來。有「下一步」的元素（全部頁的長條／扇區、每日直條）第一下只出提示，同一個再點一下才執行 */
    root.addEventListener('pointerdown', (e) => {
      if (e.pointerType === 'mouse') { S.touching = false; return; }
      S.touching = true;
      const el = e.target.closest && e.target.closest('[data-tip],li[data-k]');
      if (!el || !el.closest('[data-chart]')) { clearAll(); S.suppress = false; return; }
      const act = !!el.closest('[data-p], .dc[data-day]');
      S.suppress = act && S.tapEl !== el;
      show(e.target, e.clientX, e.clientY); S.tapEl = el;
    });
    root.addEventListener('click', (e) => { if (S.suppress) { S.suppress = false; e.stopPropagation(); e.preventDefault(); } }, true);
    document.addEventListener('pointerdown', (e) => { if (e.pointerType === 'mouse' || !root.isConnected) return; if (!(e.target.closest && e.target.closest('#admBody, #v-admin [data-chart]'))) clearAll(); }, true);
  }

  /* ---- 分頁統計 ---- */
  /* 頂層分頁順序：預設照 PAGES；可拖曳排序（「全部」固定第一顆），順序記在 localStorage（tw.adm.trTabs）；沒有刪除鈕（Andy：具備拖曳移動，但不具備刪除） */
  const TAB_KEY = 'tw.adm.trTabs';
  function tabOrder() {
    let saved = []; try { saved = JSON.parse(localStorage.getItem(TAB_KEY) || '[]'); } catch (e) { saved = []; }
    const known = PAGES.map((p) => p.k), out = (Array.isArray(saved) ? saved : []).filter((k, i, a) => known.includes(k) && a.indexOf(k) === i);
    known.forEach((k) => { if (!out.includes(k)) out.push(k); });
    return out;
  }
  function saveTabOrder(o) { try { localStorage.setItem(TAB_KEY, JSON.stringify(o)); } catch (e) { /* 無痕視窗存不了就只在這次有效 */ } }
  function paintTrTabs() {
    const v = S.v, box = v && v.querySelector('#trTabsBox'); if (!box || !S.data) return;
    if (S.tab !== 'all' && !PAGE_BY[S.tab]) S.tab = 'all';
    const d = (k) => S.data[k], ord = tabOrder();
    box.innerHTML = `<div class="nbsw" id="trTabs" role="tablist" aria-label="頁面分頁（可拖曳調整順序）"><button type="button" role="tab" data-t="all" class="${S.tab === 'all' ? 'on' : ''}" aria-selected="${S.tab === 'all'}">全部</button>${ord.map((k) => { const p = PAGE_BY[k]; return `<button type="button" role="tab" draggable="true" data-t="${p.k}" class="${S.tab === p.k ? 'on' : ''}" aria-selected="${S.tab === p.k}" title="拖曳可調整順序" aria-keyshortcuts="Alt+ArrowLeft Alt+ArrowRight">${esc(p.n)}<em>${nf(d(p.k).total)}</em></button>`; }).join('')}</div>`;
    const bar = box.querySelector('#trTabs');
    bar.onclick = (e) => { const b = e.target.closest('button[data-t]'); if (!b) return; S.tab = b.dataset.t; S.sub = 'all'; paintTrTabs(); };
    const move = (k, toK, after) => { const o = tabOrder().filter((x) => x !== k), i = o.indexOf(toK); o.splice(i + (after ? 1 : 0), 0, k); saveTabOrder(o); paintTrTabs(); };
    bar.ondragstart = (e) => { const b = e.target.closest('button[data-t]'); if (!b || b.dataset.t === 'all') { e.preventDefault(); return; } S.drag = b.dataset.t; b.classList.add('dragging'); try { e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', S.drag); } catch (x) { /* 舊瀏覽器 */ } };
    bar.ondragover = (e) => { const b = e.target.closest('button[data-t]'); if (!b || !S.drag || b.dataset.t === 'all' || b.dataset.t === S.drag) return; e.preventDefault(); const o = tabOrder(), after = o.indexOf(b.dataset.t) > o.indexOf(S.drag); bar.querySelectorAll('button').forEach((x) => x.classList.remove('dropL', 'dropR')); b.classList.add(after ? 'dropR' : 'dropL'); };
    bar.ondrop = (e) => { const b = e.target.closest('button[data-t]'), from = S.drag; S.drag = null; if (!b || !from || b.dataset.t === 'all' || b.dataset.t === from) { paintTrTabs(); return; } e.preventDefault(); const o = tabOrder(); move(from, b.dataset.t, o.indexOf(b.dataset.t) > o.indexOf(from)); };
    bar.ondragend = () => { S.drag = null; bar.querySelectorAll('button').forEach((x) => x.classList.remove('dragging', 'dropL', 'dropR')); };
    bar.onkeydown = (e) => { const b = e.target.closest('button[data-t]'); if (!b || b.dataset.t === 'all' || !e.altKey || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return; e.preventDefault(); const o = tabOrder(), i = o.indexOf(b.dataset.t), j = i + (e.key === 'ArrowLeft' ? -1 : 1); if (j < 0 || j >= o.length) return; move(b.dataset.t, o[j], e.key === 'ArrowRight'); const f = box.querySelector(`#trTabs [data-t="${b.dataset.t}"]`); if (f) f.focus(); };
    paintBody();
  }
  function paintBody() {
    const v = S.v, body = v && v.querySelector('#trPageBody'); if (!body) return;
    body.innerHTML = S.tab === 'all' ? allHtml() : S.tab === 'users' ? usersBody() : pageHtml(S.tab);
    body.onclick = (e) => {
      const t = e.target.closest('[data-p]'); if (t && S.tab === 'all') { S.tab = t.dataset.p; S.sub = t.dataset.s || 'all'; paintTrTabs(); return; }
      const sb = e.target.closest('button[data-sub]'); if (sb) { S.sub = sb.dataset.sub; paintBody(); }
      const hb = e.target.closest('button[data-hr]'); if (hb) { S.hr = hb.dataset.hr; paintBody(); }
      const hm = e.target.closest('button[data-hm]'); if (hm) { S.hm = hm.dataset.hm; paintBody(); }
    };
    v.querySelectorAll('#trTabs .on, #trSubs .on').forEach((b) => { if (b.scrollIntoView) b.scrollIntoView({ block: 'nearest', inline: 'nearest' }); });
    const sc = body.querySelector('#trSc');
    if (S.ro) { S.ro.disconnect(); S.ro = null; }
    if (sc && S.stk) { const draw = () => drawScatter(sc, S.stk.scat); draw(); if (window.ResizeObserver) { let lw = sc.clientWidth, lh = sc.clientHeight; S.ro = new ResizeObserver(() => { if (Math.abs(sc.clientWidth - lw) > 2 || Math.abs(sc.clientHeight - lh) > 2) { lw = sc.clientWidth; lh = sc.clientHeight; draw(); } }); S.ro.observe(sc); } }
  }
  const card = (id, ttl, sub, inner, cls) => `<div class="card${cls ? ' ' + cls : ''}" id="${id}"><h3>${esc(ttl)}</h3><p class="use" title="${esc(sub)}">${esc(sub)}</p><div class="cb">${inner}</div></div>`;
  /* 「全部」：左＝各頁堆疊長條（有子頁的頁面依子頁上色，滑過看占比）；右＝各頁占比大甜甜圈（子頁＝同色系子扇區） */
  function allHtml() {
    const list = PAGES.filter((p) => !p.sp).map((p, i) => ({ p, i, d: S.data[p.k] })).sort((a, b) => b.d.total - a.d.total);
    const mx = Math.max(1, ...list.map((x) => x.d.total)), tot = sum(list.map((x) => x.d.total));
    const rows = list.map(({ p, i, d }, ri) => {
      const segs = d.subN.filter((s) => s.v > 0), ssum = sum(segs.map((s) => s.v)), w = d.total / mx * 100;
      const inner = segs.length > 1 ? segs.map((s) => `<i style="width:${(s.v / Math.max(ssum, 1) * 100).toFixed(2)}%;background:${s.col}" ${tp(`<b>${esc(p.n)}・${esc(s.n)}</b><br>${nf(s.v)} 次・占該頁 ${(s.v / ssum * 100).toFixed(1)}%・占全站 ${(s.v / tot * 100).toFixed(1)}%`)}></i>`).join('')
        : `<i style="width:100%;background:${pgCol(i, 0, 1)}" ${tp(`<b>${esc(p.n)}</b><br>${nf(d.total)} 次・占全站 ${(d.total / tot * 100).toFixed(1)}%`)}></i>`;
      const t0 = tp(`<b>${esc(p.n)}</b><br>${nf(d.total)} 次・占全站 ${(d.total / tot * 100).toFixed(1)}%`);
      return `<button type="button" class="bl" data-p="${p.k}" data-row="${ri}"${t0}>${esc(p.n)}</button><span class="bt stk" data-p="${p.k}" data-row="${ri}"><span style="width:${w.toFixed(1)}%">${inner}</span></span><span class="bn" data-row="${ri}" data-p="${p.k}"${t0}>${nf(d.total)}<small>${(d.total / tot * 100).toFixed(0)}%</small></span>`;
    }).join('');
    /* ★ 2026-10-06：跟產業地圖一樣「前 5 ＋ 其他」，不再拆子頁（子頁明細在左邊堆疊長條）；顏色＝頁面色，跟左邊長條對應 */
    const segs = list.map(({ p, i, d }) => ({ label: p.n, n: d.total, color: pgCol(i, 0, 1), tip: p.n, p: p.k }));
    return `<div class="admgrid trpair">${card('trAllBars', '各頁被看了幾次？', '有子頁的以不同顏色堆疊', `<div class="bars stkbars" data-chart="bars" id="trAllB">${rows}</div>`)}
      ${card('trAllDonut', '各頁占比', '前 5 頁＋其他；顏色＝頁面，跟左邊長條一樣', donutG(segs, { aria: '各頁瀏覽占比' }))}</div>`;
  }
  /* 單一頁面：上方小分頁（全部＋子頁）、下方 功能使用次數（長條＋圓餅）、被點最多的對象（長條＋圓餅） */
  function pageHtml(k) {
    const p = PAGE_BY[k], d = S.data[k], idx = PAGES.indexOf(p);
    if (!p.subs.some((s) => s.k === S.sub)) S.sub = 'all';
    const subs = p.subs.length ? `<div class="nbsw lv2" id="trSubs" role="tablist"><button type="button" role="tab" data-sub="all" class="${S.sub === 'all' ? 'on' : ''}">全部</button>${p.subs.map((s, j) => `<button type="button" role="tab" data-sub="${s.k}" class="${S.sub === s.k ? 'on' : ''}"><i class="tdot" style="background:${pgCol(idx, j, p.subs.length)}"></i>${esc(s.n)}<em>${nf(d.subN[j].v)}</em></button>`).join('')}</div>` : '';
    if (p.simple) return simpleHtml(p, d, idx);
    const sel = S.sub === 'all' ? d.rows : d.rows.filter((r) => r.sub === S.sub);
    const sn = S.sub === 'all' ? p.n : `${p.n}・${(p.subs.find((s) => s.k === S.sub) || {}).n}`;
    const byComp = {}; sel.forEach((r) => { byComp[r.comp] = (byComp[r.comp] || 0) + r.n; });
    const fl = Object.entries(byComp).sort((a, b) => b[1] - a[1]);
    const byDet = {}, kinds = new Set();
    sel.forEach((r) => { if (kindOf(r.comp) && r.det) { const key = r.det; byDet[key] = (byDet[key] || 0) + r.n; kinds.add(kindOf(r.comp)); } });
    const dl = Object.entries(byDet).sort((a, b) => b[1] - a[1]);
    const palette = window.App.donut.colors();      // ★ 2026-10-06：共用飽和色盤（App.donut），不再用 --cat-1..5（深色主題是螢光青／萊姆，淺色是粉彩，相鄰扇區分不出來）
    const dsegs = (list, nameFn) => { const t5 = list.slice(0, 5), rest = sum(list.slice(5).map((x) => x[1])); return t5.map(([kk, n], i) => ({ label: nameFn(kk), n, color: palette[i] })).concat(rest ? [{ label: '其他', n: rest, color: window.App.donut.other() }] : []); };
    const pair = (id, ttl, sub, list, nameFn, click, lim) => `${card(id + 'B', ttl, sub, bars(list.slice(0, lim || 10), nameFn, sum(list.map((x) => x[1])), { id: id + 'Bars', click }))}${card(id + 'D', ttl.replace(/？$/, '') + '占比', '前 5 名＋其他', donutG(dsegs(list, nameFn), { legend: dsegs(list, nameFn), legendN: 6, aria: ttl }))}`;
    let body = '';
    if (k === 'stock' && S.sub === 'tabs') {
      const tl = fl.map(([c, n]) => [c.replace(/^tab\./, ''), n]);
      body = `<div class="admgrid trpair">${pair('trF', '各分頁被點幾次？', '個股頁下方分頁（含 ETF 成分股）', tl, (c) => (TAB_NAME[c] || c), false, 12)}</div>`;
    } else if (k === 'stock' && S.sub === 'kline') {
      /* K 線指標：左＝各項功能（技術指標各自計次＋畫線工具各自計次＋AI 面向／四週期同看／指標面板／3D）；右組＝K 線週期切換，不重複 */
      const it = {}; const add = (nm, n) => { it[nm] = (it[nm] || 0) + n; };
      sel.forEach((r) => { if (r.comp === 'ind') add(r.det || '技術指標', r.n); else if (r.comp === 'draw.tool') add('畫線：' + (r.det || '工具'), r.n); else if (!/^kp\./.test(r.comp)) add(compName(r.comp), r.n); });
      const il = Object.entries(it).sort((a, b) => b[1] - a[1]);
      const pl = fl.filter(([c]) => /^kp\./.test(c));
      body = `<div class="admgrid trpair">${pair('trF', '各項功能被用了幾次？', '技術指標／畫線／AI／四週期（含本益比河流）', il, (x) => x, false, 16)}</div>`
        + (pl.length ? `<div class="admgrid trpair">${pair('trD', 'K 線週期切換', '日／週／月／分 K', pl, compName)}</div>` : '');
    } else if (k === 'stock' && S.sub === 'all') {
      body = `<div class="admgrid trpair">${pair('trF', '各功能被用了幾次？', '每個功能被用的次數', fl, compName)}</div>
        <div class="admgrid trpair">${pair('trD', '被點最多的個股', '個股頁被打開次數，前 10 名', dl, stockNm)}</div>
        <div class="admgrid">${card('trStockFeat', '熱門個股的人都在用什麼功能？', '前 10 檔各自最常用的三個功能', S.stk.featRows.length ? stockTable(S.stk.featRows) : '<div class="empty">沒有資料</div>', 's2')}
          ${card('trScatter', '哪些股票「又多人看、看的人又用得深」？', '右上＝熱門又被深度使用', S.stk.scat.length < 2 ? '<div class="empty">沒有資料</div>' : '<div class="sc" data-chart="sc" id="trSc"></div>')}</div>`;
    } else if (!fl.length) {
      body = `<div class="empty trempty">沒有資料</div>`;
    } else {
      const nmDet = (x) => (kinds.has('個股') && /^[0-9A-Z]{4,6}$/.test(x) ? stockNm(x) : x);
      body = (fl.length === 1 && dl.length ? '' : `<div class="admgrid trpair">${pair('trF', '各功能被用了幾次？', sn, fl, compName)}</div>`)
        + (dl.length ? `<div class="admgrid trpair">${pair('trD', `被點最多的${[...kinds].join('／')}`, `${sn}・Top 10`, dl, nmDet)}</div>` : '');
    }
    return `<div class="trhd">${subs}</div>${body}`;
  }
  const stockTable = (rows) => `<div class="tbw"><table class="fx"><colgroup><col style="width:24%"><col style="width:26%"><col style="width:50%"></colgroup><thead><tr><th>代號</th><th>觀看</th><th>最常用的功能</th></tr></thead><tbody>${rows.map((r) => `<tr><td class="nm">${esc(stockNm(r.code))}</td><td><span class="vb"><span><i style="width:${(r.views / Math.max(1, rows[0].views) * 100).toFixed(1)}%"></i></span><em>${nf(r.views)}</em></span></td><td>${r.top.length ? `<div class="chips">${r.top.map((x) => `<span class="chip">${esc(compName(x.comp).replace(/^.*：/, ''))} <b>${nf(x.n)}</b></span>`).join('')}</div>` : '<span style="color:var(--ink-2)">只看沒點功能</span>'}</td></tr>`).join('')}</tbody></table></div>`;
  /* 每天直條：只從「第一筆有資料的日子」起畫（前面沒紀錄的天數用一行字交代）。圖區吃滿卡片高度；y 軸 0／一半／最大值＋淡格線＋平均虛線；
     最高那天標值；天數 ≤ 7 時每根放大（寬到 140）並在柱上標值、柱下標日期，不再是細細兩根留一大片空白 */
  const days0 = (days, bk) => (bk && bk.gran !== 'day' ? bk.info[days[0]].from : days[0]);
  /* 把「整段期間的每一天」分格：≤31 天按日；32～120 天按週（從起日起每 7 天一格，最後一格可能不滿 7 天）；>120 天按日曆月。
     回傳 keys（每格的 key）、info[key]＝{from,to,n,label}、of[日期]＝那天屬於哪一格 */
  function bucketize(days) {
    const n = days.length, gran = n <= 31 ? 'day' : n <= 120 ? 'week' : 'month', keys = [], info = {}, of = {};
    days.forEach((d, i) => {
      const k = gran === 'day' ? d : gran === 'week' ? days[i - (i % 7)] : d.slice(0, 7);
      if (!info[k]) { keys.push(k); info[k] = { from: d, to: d, n: 0 }; }
      info[k].to = d; info[k].n++; of[d] = k;
    });
    return { gran, keys, info, of };
  }
  function dayChart(days, perDay, dmax, idp, full, bk) {
    idp = idp || 'admDayBars';
    const co = bk && bk.gran !== 'day' ? bk : null, gl = co ? (co.gran === 'week' ? '週' : '月') : '';
    if (!full && !days.some((d) => (perDay[d] || 0) > 0)) return '<div class="empty">沒有資料</div>';
    const shown = days.slice(), few = shown.length <= 7, dtot = shown.reduce((s, d) => s + (perDay[d] || 0), 0);
    const avg = shown.reduce((s, d) => s + (perDay[d] || 0), 0) / shown.length, mxd = shown.reduce((a, d) => ((perDay[d] || 0) > (perDay[a] || 0) ? d : a), shown[0]);
    /* X 軸刻度：每 7 天（週一）標一個；期間很長（> 98 天）改成每 4 週，免得擠在一起。時間是每小時（HH:00）就每 4 小時一個 */
    let ticks = [];
    if (!few) {
      if (/^\d\d:00$/.test(shown[0])) ticks = shown.map((d, i) => [d, i]).filter(([d, i]) => i % 4 === 0);
      else if (!co) { ticks.push([shown[0], 0]); shown.forEach((d, i) => { if (i >= 3 && new Date(Date.parse(d + 'T00:00:00Z')).getUTCDay() === 1) ticks.push([d, i]); }); }      // 按日：第一個刻度＝期間起日，其後每個週一
      else { const step = Math.max(1, Math.ceil(shown.length / (co && co.gran === 'month' ? 13 : 8))); shown.forEach((d, i) => { if (i % step === 0) ticks.push([co ? co.info[d].from : d, i]); }); }      // 第一個刻度＝期間起日，其餘等距
    }
    const ys = [1, 0.75, 0.5, 0.25, 0].map((f) => `<span>${nf(Math.round(dmax * f))}</span>`).join('');
    return `<div class="dayplot"><div class="dayy">${ys}</div>
      <div class="days${few ? ' few' : ''}${shown.length > 90 ? ' many' : ''}${co ? ' coarse' : ''}" data-chart="days" id="${idp}" data-first="${esc(shown[0])}">${shown.map((d, di) => perDay[d] === null ? `<div class="dc fut" data-row="${di}"${tp(`<b>${esc(d)}</b><br>還沒到這個小時`)}><i style="height:0"></i></div>` : `<div class="dc${d === mxd ? ' mx' : ''}${idp === 'admDayBars' && S.day && (co ? co.info[d].from : d) === S.day && (S.dayTo || S.day) === (co ? co.info[d].to : d) ? ' sel' : ''}"${idp === 'admDayBars' && /^\d{4}-/.test(d) ? ` data-day="${co ? co.info[d].from : d}" data-to="${co ? co.info[d].to : d}"` : ''} data-row="${di}"${tp(`<b>${esc(co ? (co.gran === 'week' ? co.info[d].from.slice(5) + '～' + co.info[d].to.slice(5) : d + '（' + co.info[d].from.slice(5) + '～' + co.info[d].to.slice(5) + '）') + '　共 ' + co.info[d].n + ' 天' : d)}${!co && /^\d{4}-/.test(d) ? '（週' + '日一二三四五六'[new Date(Date.parse(d + 'T00:00:00Z')).getUTCDay()] + '）' : ''}</b><br>${nf(perDay[d] || 0)} 次・占期間 ${(((perDay[d] || 0) / Math.max(1, dtot)) * 100).toFixed(1)}%<br>${(perDay[d] || 0) >= avg ? '高於' : '低於'}平均 ${nf(Math.round(avg))}${d === mxd ? '（最高）' : ''}`)}>${few || d === mxd || (co && shown.length <= 14 && (perDay[d] || 0) > 0) ? `<span class="dv">${nf(perDay[d] || 0)}</span>` : ''}<i style="height:${((perDay[d] || 0) / dmax * 100).toFixed(1)}%"></i>${few ? `<span class="dd">${d.slice(5)}</span>` : ''}</div>`).join('')}
        ${shown.length > 1 ? `<div class="avg" style="bottom:${(avg / dmax * 100).toFixed(1)}%"><b>${co ? '每' + gl + '平均' : '平均'} ${nf(Math.round(avg))}</b></div>` : ''}</div></div>
      ${few ? '' : `<div class="dayticks" id="${idp}Ticks"><div>${ticks.map(([d, i]) => `<span style="left:${((i + 0.5) / shown.length * 100).toFixed(2)}%">${/^\d\d:00$/.test(d) ? d : d.slice(5)}</span>`).join('')}</div></div>`}
`;
  }
  /* 散佈圖：依容器實際大小畫（ResizeObserver 重畫），圖吃滿卡片；格線 3 條、軸刻度＝真值；標籤避開已放的標籤 */
  function drawScatter(box, pts) {
    if (!box) return;
    const W = Math.max(240, Math.round(box.clientWidth)), H = Math.max(180, Math.round(box.clientHeight));
    const L = 44, B = 40, T = 14, R = 18;
    const xm = Math.max(...pts.map((p) => p.x)), ym = Math.max(0.5, ...pts.map((p) => p.y));
    const X = (x) => L + (x / xm) * (W - L - R - 8), Y = (y) => H - B - (y / ym) * (H - B - T - 8);
    const lab = pts.slice().sort((a, b) => (b.x + b.y * xm / ym) - (a.x + a.y * xm / ym)).slice(0, 6);
    const placed = [], out = [];
    lab.forEach((p) => {
      const w = String(p.code).length * 8 + 6, cx = X(p.x), cy = Y(p.y);
      for (const [dx, dy, anc] of [[9, 4, 'start'], [-9, 4, 'end'], [0, -10, 'middle'], [0, 20, 'middle']]) {
        const x0 = anc === 'start' ? cx + dx : anc === 'end' ? cx + dx - w : cx - w / 2, y0 = cy + dy - 12;
        if (x0 < 0 || x0 + w > W || y0 < 0 || y0 + 16 > H - B + 4) continue;
        if (placed.some((r) => x0 < r[0] + r[2] && x0 + w > r[0] && y0 < r[1] + r[3] && y0 + 16 > r[1])) continue;
        placed.push([x0, y0, w, 16]); out.push(`<text class="lb" x="${(cx + dx).toFixed(1)}" y="${(cy + dy).toFixed(1)}" text-anchor="${anc}">${esc(p.code)}</text>`); return;
      }
    });
    const gl = [0, 0.5, 1].map((f) => { const y = Y(ym * f).toFixed(1); return `<line class="gl" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/><text x="${L - 6}" y="${(+y + 4).toFixed(1)}" text-anchor="end">${f === 0 ? '0' : (ym * f).toFixed(1)}</text>`; }).join('');
    const xt = [0, 0.5, 1].map((f) => `<text x="${X(xm * f).toFixed(1)}" y="${H - B + 16}" text-anchor="${f === 0 ? 'start' : f === 1 ? 'end' : 'middle'}">${nf(Math.round(xm * f))}</text>`).join('');
    box.innerHTML = `<svg id="trScSvg" viewBox="0 0 ${W} ${H}" role="img" aria-label="個股被觀看次數與平均功能使用次數的散佈圖">${gl}<line x1="${L}" y1="${T}" x2="${L}" y2="${H - B}" stroke="var(--line-2)"/>${xt}
      <text x="${W - R}" y="${H - 6}" text-anchor="end">被觀看次數 →</text><text x="${L}" y="${H - 6}" text-anchor="start">每次觀看用幾次功能 ↑</text>
      ${pts.map((p, pi) => `<circle data-row="${pi}"${tp(`<b>${esc(stockNm(p.code))}</b><br>被觀看 ${nf(p.x)} 次<br>每次平均用 ${p.y.toFixed(2)} 次功能`)} cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="6" fill="var(--cat-1)" fill-opacity=".85" stroke="var(--panel)" stroke-width="1.5"></circle>`).join('')}${out.join('')}</svg>`;
  }
  /* ★ 2026-10-06 第三版（Andy 14:45：「管理區甜甜圈還是舊樣式，要一模一樣」，DECISIONS #331）：
     管理區所有甜甜圈（各頁占比、開站身分、功能占比、會員狀態、方案、分頁瀏覽）不再自己用 SVG 畫，
     一律用 ECharts ＋ App.donut（site/app.js，產業地圖「成交值占比」的同一份設定）：環 68／92、間隙 1.2°、圓角 6、邊框 1px、
     滑過外擴 4px＋外框 3px（其他扇區不變暗）、中心字 App.donut.center、提示框 A.tip。
     donutG 只負責「圖例＋容器」，環由 mountDonuts() 在容器進到畫面後掛上去（MutationObserver，見 render）。 */
  function donutG(segs0, o) {
    /* 最多 6 塊（前 5 ＋ 其他）：照產業地圖；超過的併成灰色「其他」，保留原本順序 */
    let segs = segs0.filter((x) => x.n > 0);
    if (segs.length > 6) {
      const keep = new Set(segs.slice().sort((a, b) => b.n - a.n).slice(0, 5)), rest = segs.filter((x) => !keep.has(x));
      segs = segs.filter((x) => keep.has(x)).concat([{ label: '其他', n: sum(rest.map((x) => x.n)), color: 'var(--c0)', tip: '其他（' + rest.length + ' 項）' }]);
    }
    o = Object.assign({}, o, { legend: segs, legendN: 6, top5: null });
    const tot = sum(segs.map((s) => s.n));
    if (!tot) return '<div class="empty">沒有資料</div>';
    const top5 = (o.top5 || segs).slice().sort((x, y) => y.n - x.n).slice(0, 5), t5 = Math.round(sum(top5.map((x) => x.n)) / (o.totalN || tot) * 100);
    const c1 = o.center ? o.center[0] : '前五大', c2 = o.center ? o.center[1] : t5 + '%';
    const lg = (o.legend || segs).slice().sort((x, y) => (x.label === '其他') - (y.label === '其他') || y.n - x.n).slice(0, o.legendN || 6);
    const spec = { c1, c2, segs: segs.filter((s) => s.n > 0).map((s) => ({ name: s.tip || s.label, n: s.n, color: s.color, k: s.k != null ? s.k : s.label, p: s.p || '', s: s.s || '', other: s.label === '其他' })) };
    return `<div class="${o.cls || 'dn'}" data-chart="donut"${o.id ? ` id="${o.id}"` : ''} data-total="${tot}"><div class="dnc" role="img" aria-label="${esc(o.aria || '占比')}" data-spec="${esc(JSON.stringify(spec))}"></div>
      <ul class="lg">${lg.map((s) => `<li data-k="${esc(s.k != null ? s.k : s.label)}" data-n="${s.n}"${tp(`<b>${esc(s.label)}</b><br>${s.ltxt || nf(s.n) + '（' + (s.n / (o.totalN || tot) * 100).toFixed(1) + '%）'}`)}><i style="background:${s.lcolor || s.color}"></i><span>${esc(s.label)}</span><b>${nf(Math.round(s.n))}</b><small>${(s.n / (o.totalN || tot) * 100).toFixed(1)}%</small></li>`).join('')}</ul></div>`;
  }
  /* 把 CSS 變數／hsl(calc(var())) 這類顏色解成 rgb（canvas 讀不懂 var()） */
  function resolveColor(host, c) {
    const t = document.createElement('i'); t.style.cssText = 'position:absolute;visibility:hidden;color:' + c; host.appendChild(t);
    const r = getComputedStyle(t).color; t.remove(); return r || c;
  }
  function mountDonuts(root) {
    const A = window.App; if (!A || !A.donut || !window.echarts || !root) return;
    const D = A.donut;
    root.querySelectorAll('.dnc[data-spec]:not([data-m])').forEach((el) => {
      let sp; try { sp = JSON.parse(el.dataset.spec); } catch (e) { return; }
      el.dataset.m = '1';
      const SZ = Math.round(el.clientWidth) || 160, tot = sum(sp.segs.map((s) => s.n)) || 1;
      const parts = sp.segs.map((s) => ({ name: s.name, value: s.n, key: s.k, p: s.p, s2: s.s, color: s.other ? D.other() : resolveColor(el, s.color) }));
      const box = el.closest('[data-chart]');
      const cur = { hi: null };
      const opt = { tooltip: { ...A.tip, position: D.tipPos, trigger: 'item', formatter: (q) => `<b>${esc(q.name)}</b><br>${nf(Math.round(q.value))}（${(+q.percent).toFixed(1)}%）` },
        title: D.center(sp.c1, sp.c2, SZ), animationDurationUpdate: D.MS,
        series: D.series({ cursor: sp.segs.some((s) => s.p) ? 'pointer' : 'default', data: parts.map((d, i) => D.item(d, i, false)) }) };
      A.chart(el, opt, { notMerge: true });
      const inst = echarts.getInstanceByDom(el); if (!inst) return;
      const setHi = (nm) => {
        if (inst.isDisposed() || cur.hi === nm) return; cur.hi = nm;
        const hd = nm ? parts.find((x) => x.name === nm) : null;
        try { inst.setOption({ title: D.center(hd ? hd.name : sp.c1, hd ? A.fmt.n(hd.value / tot * 100, 1) + '%' : sp.c2, SZ), series: [{ data: parts.map((d, i) => D.item(d, i, !!hd && d.name === nm)) }] }); } catch (e) { /* tooltip 與 dispose 競態 */ }
        if (box) { box.classList.toggle('hov', !!hd); box.querySelectorAll('li[data-k]').forEach((li) => li.classList.toggle('hl', !!hd && hd.key === li.dataset.k)); }
      };
      inst.on('mouseover', (q) => { if (q.seriesIndex === 0) setHi(q.name); });
      inst.on('globalout', () => setHi(null));
      inst.on('click', (q) => { const d = parts.find((x) => x.name === q.name); if (d && d.p && S.tab === 'all') { S.tab = d.p; S.sub = d.s2 || 'all'; paintTrTabs(); } });
      if (box) box.querySelectorAll('li[data-k]').forEach((li) => {
        li.addEventListener('mouseenter', () => { const d = parts.find((x) => x.key === li.dataset.k); if (d) setHi(d.name); });
        li.addEventListener('mouseleave', () => setHi(null));
        li.addEventListener('pointerdown', (e) => { if (e.pointerType !== 'mouse') { const d = parts.find((x) => x.key === li.dataset.k); if (d) setHi(d.name); } });
      });
      requestAnimationFrame(() => { if (!inst.isDisposed()) inst.resize(); });
    });
  }
  function donut(parts) {
    const tot = parts.reduce((s, p) => s + p[1], 0);
    if (!tot) return '<div class="empty">沒有資料</div>';
    return donutG(parts.map(([nm, n, col]) => ({ label: nm, n, color: col, ltxt: `${nf(n)}・${Math.round(n / tot * 100)}%` })), { center: [parts[0][0], Math.round(parts[0][1] / tot * 100) + '%'], legendN: 2, aria: `${parts.map((p) => p[0]).join('與')}比例` });
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
  /* 付費＝非內建範本（Andy 10-05 回報：名單有金色 ★ 但方案欄寫「訪客」）。根因：舊判斷只看「範本存在」，
     內建範本（訪客／免費）或被取名成「訪客」「註冊會員」的範本也會被當成付費。現在內建一律不算付費，
     名字跟層級撞名的範本建立／改名時也擋掉（RESERVED）。 */
  const RESERVED = /^(訪客|註冊會員|免費會員|付費會員)/;
  const tierOf = (planId) => { const p = planId && planOf(planId);
    return planId === 'guest' ? 'guest' : (!p || planId === 'free' || p.builtin || RESERVED.test(p.name || '') ? 'free' : 'paid'); };
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
  const ERR = { has_members: '還有有效會員，請先移到其他範本或等到期', forbidden: '沒有管理者權限', bad_email: 'email 格式不對', bad_plan: '方案不存在', bad_feats: '開關格式不對', bad_lims: '瀏覽次數要是 0～9999 的整數', bad_name: '範本名稱不能空白', too_many: '數量超過上限', builtin: '內建範本不能刪', bad_expires: '到期日格式不對', bad_price: '價格要是 0～999999 的整數', bad_period: '計費週期只能是月／年' };
  const errText = (r) => !r ? '連不到伺服器' : (ERR[r.error] || ('HTTP ' + r._s));
  const EMAIL_OK = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
  /* 到期日：畫面上是台北日期（yyyy-mm-dd），存的是「那一天台北 23:59:59」的毫秒 */
  const expToMs = (s) => { if (!s) return null; const t = Date.parse(s + 'T23:59:59+08:00'); return isFinite(t) ? t : null; };
  const msToDate = (ms) => (ms ? new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10) : '');
  const honest = '';      // 2026-10-05：整張「這個鎖頭擋得住什麼？」說明卡拿掉（內部口徑），一句話改放開放功能表標題旁的 ⓘ 滑過顯示
  const LOCK_NOTE = '鎖頭只擋一般使用者的畫面；資料檔是公開的，懂技術的人仍能直接讀到。';
  /* 在線時間：「3 小時 12 分」「45 分」「—」 */
  const dur = (ms) => { if (!ms) return '—'; const m = Math.round(ms / 60000); if (m < 1) return '< 1 分'; const h = Math.floor(m / 60); return h ? `${h} 小時${m % 60 ? ' ' + (m % 60) + ' 分' : ''}` : m + ' 分'; };

  const GRPSEC = `<div class="secttl" id="pmGrpTtl"><h2>族群觀測</h2><small id="pmGrpCnt"></small><span class="pmfold"><button type="button" id="pmExpandAll">全部展開</button><button type="button" id="pmCollapseAll">全部收合</button></span></div>
        <div class="pmcats pmgrpbox card" id="pmGrp"></div>`;
  async function renderPerm(v, A, tab) {
    PS.v = v; PS.A = A; PS.draft = null; PS.tab = tab;
    PS.mode = 'plan'; PS.editMember = false;
    if (tab === 'perm') {
      /* perm-cards（2026-10-05，Andy）：頁籤 → 子分頁 → 內容 連成一個整體 —— 選中的頁籤底下直接接內容框，
         開放功能表、族群觀測、會員名單都在同一個框內；說明縮成一行小字。 */
      /* perm-v4（2026-10-05，Andy「整頁不直觀」）資訊層級由上而下：
           標題＋一行說明（右側一行小字教頁籤怎麼管）→ 範本頁籤（資料夾頁籤，選中的跟內容框連成一塊）→
           內容框：範本資訊列（名稱・價格／週期・套用人數｜⚙）＋一行說明 → 子分頁（觀看權限｜會員名單）→
           觀看權限：工具列（標題＋圖例＋全部開／全部關）→ 功能卡片（同寬同高）→ 族群觀測；會員名單：統計圖卡 → 名單。
         拿掉舊版「開放功能表　正在編：付費會員・XX」那一行：它跟範本資訊列講同一件事（#ptFor 搬進資訊列，id 不變）。 */
      v.innerHTML = (document.documentElement.classList.contains('l4') ? '' : head(v, A) + '</div>') + `
        <div class="ptwrap" id="pmHead">
          <div class="nbsw ptabs" id="ptTier" role="tablist" aria-label="要設定哪一種人"></div>
          <div class="ptpanel">
            <div id="pmTarget"></div>
            <div class="nbsw lv2 ptsub" id="ptSub" role="tablist" aria-label="子分頁"></div>
            <div class="pmstat" id="pmStat" role="status" aria-live="polite"></div>
            <div id="ptPermBox">
              <div id="ptGuestSum"></div>
              <div class="pmtools" id="pmTools"><h3 class="pmttl">開放功能表<span class="qtip pmq" tabindex="0" role="note" aria-label="說明" title="${esc(LOCK_NOTE)}">?</span></h3>
                <div class="pmlegend"><span><i class="lg dirty"></i>改了還沒儲存</span><span><i class="lg tuned"></i>跟預設不同（已儲存）</span><span><i class="lg lim">∞</i>每日次數上限</span></div>
                <span id="pmAllLim" class="pmallim"></span><span class="pmallsw" title="開放功能表全部開／關（不含族群觀測）"><span>全部</span><button type="button" id="pmAllSw" class="psw3" role="switch" aria-checked="false" aria-label="開放功能表全部開／關（不含族群觀測）"><span></span></button></span></div>
              <div class="pmcats pmcards" id="pmCats"></div>
              ${GRPSEC}</div>
            <div id="ptListBox" hidden></div>
          </div>
          <div class="ptmenu" id="ptMenu" role="menu" hidden></div></div>
        <div class="pmsave" id="pmSave" hidden><span id="pmDirty"></span><button type="button" id="pmCancel">取消</button><button type="button" class="pri" id="pmSaveGo">儲存</button></div>
        ${honest}`;
      wireTabs(v);
      v.querySelector('#pmAllSw').onclick = (e) => allFeats(e.currentTarget.getAttribute('aria-checked') !== 'true');
      v.querySelector('#ptTier').onclick = (e) => {
        const mb = e.target.closest('button[data-more]');
        if (e.target.closest('.ptrn')) return;
        if (mb) { e.stopPropagation(); openMenu(PS.menu === mb.dataset.more ? null : mb.dataset.more, 'del'); return; }
        const b = e.target.closest('button[role=tab]'); if (!b) return;
        if (b.id === 'ptAddTab') { if (PS.adding || !guard()) return; PS.adding = true; PS.cfg = false; PS.confirmDel = false; paintAll(); setStat(''); return; }
        const tier = b.dataset.tier, plan = b.dataset.plan || '';
        if (!PS.adding && tier === PS.tier && (tier !== 'paid' || plan === PS.planSel)) return;
        if (!guard()) return;
        PS.adding = false; PS.cfg = false; PS.delAsk = false; PS.tier = tier; PS.confirmDel = false; if (tier === 'paid') PS.planSel = plan; pickTierPlan();
        if (tier === 'guest') PS.sub = 'perm';
        paintAll(); setStat('');
      };
      v.querySelector('#ptSub').onclick = (e) => {
        const b = e.target.closest('button[data-sub]'); if (!b || b.dataset.sub === PS.sub) return;
        PS.sub = b.dataset.sub; paintSub();
      };
    }
    wireHead(v);
    bindHover(v);
    v.querySelector('#pmSaveGo').onclick = saveDraft;
    v.querySelector('#pmCancel').onclick = () => { PS.draft = null; paintTarget(); paintCats(); setStat('已取消，回到上次儲存的設定'); };
    await loadFeatures();
    if (!FT()) { v.querySelector('#pmCats').innerHTML = '<div class="card"><p class="err">讀不到功能清單</p></div>'; return; }
    const [pl, li, mm] = await Promise.all([A.call('/v1/admin/plans/get', {}), A.call('/v1/admin/perm/list', {}), A.call('/v1/admin/members', {})]);
    if (tabOf() !== tab) return;
    if (!pl || pl._s !== 200) {
      v.querySelector('#pmCats').innerHTML = `<div class="card" style="grid-column:1/-1"><p class="err">讀不到方案範本（${esc(errText(pl))}）</p></div>`;
      return;
    }
    PS.plans = pl.plans || [];
    PS.list = li && li._s === 200 ? li : { rows: [], users: [] };
    PS.mem = mm && mm._s === 200 && Array.isArray(mm.members) ? mm : null;
    if (tab === 'perm') pickTierPlan();
    paintAll();
  }
  function paintAll() { paintTabs(); paintAddPlan(); paintTarget(); paintSub(); paintCats(); paintList(); }
  /* 層級 → 要編的範本：訪客＝guest、註冊會員＝free、付費＝下拉選的那個（沒有就第一個；一個都沒有＝付費分頁只顯示「按＋新增」）*/
  function pickTierPlan() {
    if (PS.tier === 'guest') PS.planSel = 'guest';
    else if (PS.tier === 'free') PS.planSel = 'free';
    else { const pp = paidPlans(); if (!pp.some((p) => p.id === PS.planSel)) { if (pp.length) PS.planSel = pp[0].id; else { PS.tier = 'free'; PS.planSel = 'free'; } } }
  }
  /* 頁籤（perm-cards 2026-10-05，Andy）：預設只有「訪客｜註冊會員｜＋」；每個付費範本自己一個頁籤「名稱（月／年）」，
     不再有「付費會員」母頁籤＋下拉；頁籤上不顯示人數。內建 guest／free 由 paidPlans() 以 id＋builtin 濾掉，不會重複成範本頁籤。 */
  const tabLabel = (p) => `${p.name}（${p.period === 'year' ? '年' : p.period === 'once' ? '一次' : '月'}）`;
  /* perm-v4：付費範本頁籤外面包一層 .ptab（可拖曳），裡面是頁籤本身＋滑過才出現的「⋮」（不是頁籤的子元素 —— 按鈕不能包按鈕）。
     訪客、註冊會員、＋ 沒有包裝、不能拖、沒有 ⋮ → 固定在最前／最後。 */
  /* 頁籤的滑過提示（2026-10-06 起方案頁頂端的標題列拿掉，價格與套用人數改放這裡）：名稱・價格／週期｜套用 N 人（付費頁籤另加「拖曳可調整順序」）*/
  function tabInfo(tier, plan) {
    if (tier === 'guest') return '訪客・NT$0／月｜所有沒登入的人都套這一份';
    if (tier === 'free') return `註冊會員・NT$0／月｜套用 ${members().filter((r) => !r.paid).length} 人（登入後沒被指定付費範本的人、付費到期的人）`;
    const p = planOf(plan);
    return p ? `${planLabel(p)}｜套用 ${planMembers(p.id)} 人（拖曳可調整順序）` : '付費範本';
  }
  function paintTabs() {
    const bar = PS.v && PS.v.querySelector('#ptTier'); if (!bar) return;
    /* 重畫前記住焦點在哪一顆（頁籤或 ⋮），重畫後放回去 —— 鍵盤 Alt＋← 移完、或順序存好回來重畫，焦點不會掉到頁面最上面 */
    const ae = document.activeElement, keep = ae && bar.contains(ae) ? (ae.dataset.more ? `button[data-more="${ae.dataset.more}"]` : ae.dataset.plan ? `button[data-plan="${ae.dataset.plan}"]` : ae.id ? '#' + ae.id : ae.dataset.tier ? `button[data-tier="${ae.dataset.tier}"]` : '') : '';
    const t = (tier, label, plan) => { const on = !PS.adding && PS.tier === tier && (!plan || PS.planSel === plan);
      return `<button type="button" role="tab" aria-selected="${on}" class="${on ? 'on' : ''}" data-tier="${tier}"${plan ? ` data-plan="${esc(plan)}" aria-keyshortcuts="Alt+ArrowLeft Alt+ArrowRight"` : ''} title="${esc(tabInfo(tier, plan))}"><span>${esc(label)}</span></button>`; };
    bar.innerHTML = t('guest', '訪客') + t('free', '註冊會員')
      + paidPlans().map((p) => `<div class="ptab" draggable="true" data-pid="${esc(p.id)}">${t('paid', tabLabel(p), p.id)}<button type="button" class="ptmore" data-more="${esc(p.id)}" aria-haspopup="dialog" aria-expanded="${PS.menu === p.id}" aria-label="刪除「${esc(p.name)}」範本" title="刪除此範本">×</button></div>`).join('')
      + `<button type="button" role="tab" id="ptAddTab" aria-selected="${!!PS.adding}" class="add${PS.adding ? ' on' : ''}" aria-label="新增付費範本" title="新增付費範本（名稱、價格、月／年訂閱）">＋</button>`;
    if (keep) { const k = bar.querySelector(keep); if (k) k.focus(); }
    paintMenu();
  }
  /* ---------------------------------------------------------------- perm-v4 頁籤管理：拖曳排序、⋮ 選單（左移／右移／重新命名／刪除）
     順序存後端 plans.sort（/v1/admin/plans/sort 一次送整串）→ 訂閱頁 #pricing 的方案卡照同一個順序。
     先在畫面上換好（樂觀更新），後端失敗就換回來並說原因 —— 拖完要等網路才動，會以為沒拖到。 */
  const paidIds = () => paidPlans().map((p) => p.id);
  async function reorder(ids, msg) {
    const old = PS.plans.slice(), pos = new Map(ids.map((id, i) => [id, i]));
    const head = PS.plans.filter((p) => !pos.has(p.id)), tail = ids.map((id) => planOf(id)).filter(Boolean);
    PS.plans = head.concat(tail);
    paintTabs();
    setStat('順序更新中…');
    const j = await PS.A.call('/v1/admin/plans/sort', { ids });
    if (j && j._s === 200 && Array.isArray(j.plans)) { PS.plans = j.plans; paintTabs(); setStat(`${msg}・已儲存順序（訂閱頁的方案卡也照這個順序，台北 ${tpeTime()}）`, 'ok'); }
    else { PS.plans = old; paintTabs(); setStat('順序沒存成功：' + (j && j._s === 404 ? '讀不到' : errText(j)) + '，已換回原本的順序', 'bad'); }
  }
  function moveBy(id, d) {
    const ids = paidIds(), i = ids.indexOf(id), j = i + d;
    if (i < 0 || j < 0 || j >= ids.length) return;
    ids.splice(i, 1); ids.splice(j, 0, id);
    reorder(ids, `「${(planOf(id) || {}).name || id}」${d < 0 ? '左移' : '右移'}`);
  }
  /* 這個範本目前有幾個人：後端 plans/get 的 members（perm 表裡指定到它的，含已過期）；舊 Worker 沒有就從名單數 */
  const planMembers = (id) => { const p = planOf(id); return p && Number.isInteger(p.members) ? p.members : people().filter((r) => r.plan === id).length; };
  const delMsg = (id) => `目前有 ${planMembers(id)} 位會員在此範本，刪除後退回註冊會員`;
  /* 還有「有效會員」（指定到這個範本、而且沒到期）的付費範本不能刪：前端先擋（名單來自 perm/list），伺服器也擋（plans/put del → 409 has_members） */
  const activeMembers = (id) => { const now = (PS.list && PS.list.now) || Date.now(); return people().filter((r) => r.plan === id && !(r.expires && r.expires < now)); };
  async function delPlan(id) {
    const p = planOf(id); if (!p) return;
    if (activeMembers(id).length) { openMenu(id, 'del'); return; }
    const nm = p.name, wasSel = PS.planSel === id && PS.tier === 'paid';
    if (wasSel && !guard()) return;
    setStat('刪除中…');
    const j = await PS.A.call('/v1/admin/plans/put', { id, del: true });
    if (j && j._s === 200) {
      PS.plans = j.plans; PS.cfg = false; PS.delAsk = false; PS.menu = null;
      if (wasSel) PS.draft = null;
      pickTierPlan(); paintAll(); setStat(`已刪除「${nm}」；原本用它的會員退回「註冊會員」（個別微調保留）`, 'ok'); refreshList();
    } else if (j && j._s === 409 && j.error === 'has_members') {
      PS.list = PS.list || {}; (PS.list.rows = PS.list.rows || []);
      (j.emails || []).forEach((em) => { if (!PS.list.rows.some((r) => r.email === em)) PS.list.rows.push({ email: em, plan: id, n: 0, updated: 0, expires: 0 }); });
      setStat(`還有 ${j.n} 位有效會員，不能刪`, 'bad'); openMenu(id, 'del');
    } else setStat('刪除失敗：' + errText(j), 'bad');
  }
  async function renamePlan(id, name) {
    const p = planOf(id); name = String(name || '').trim();
    if (!p) return;
    if (!name) { setStat('範本名稱不能空白', 'bad'); return; }
    if (RESERVED.test(name)) { setStat('範本名稱不能叫「訪客／註冊會員／免費會員／付費會員」（會跟層級混淆）', 'bad'); return; }
    setStat('儲存中…');
    /* 只改名：開關與價格照「已存的」送（沒存的草稿不會被一起存掉；草稿留著，存不存照舊由底部儲存列決定）*/
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats: p.feats || {}, price: Number.isInteger(p.price) ? p.price : 0, period: p.period || 'month' });
    if (j && j._s === 200) { PS.plans = j.plans; PS.menu = null; paintTabs(); paintAddPlan(); paintTarget(); setStat(`已改名為「${name}」（台北 ${tpeTime()}）`, 'ok'); }
    else setStat('改名失敗：' + errText(j), 'bad');
  }
  /* 開／關 ⋮ 選單。刻意不重畫頁籤列（只改 aria-expanded）：關選單常發生在「按下另一個頁籤」的 pointerdown，
     這時重畫會把使用者正要點的那顆換掉，click 就落空。refocus＝用鍵盤（Esc）關掉時把焦點還給 ⋮。 */
  function openMenu(id, mode, refocus) {
    const prev = PS.menu;
    PS.menu = id || null; PS.menuMode = mode || 'list';
    if (!PS.v) return;
    PS.v.querySelectorAll('#ptTier button[data-more]').forEach((b) => b.setAttribute('aria-expanded', String(b.dataset.more === PS.menu)));
    paintMenu();
    if (!PS.menu) { if (refocus && prev) { const f = PS.v.querySelector(`#ptTier button[data-more="${prev}"]`); if (f) f.focus(); } return; }
    const m = PS.v.querySelector('#ptMenu');
    const first = m && m.querySelector('input,button:not(:disabled)'); if (first) { first.focus(); if (first.select) first.select(); }
  }
  function paintMenu() {
    const m = PS.v && PS.v.querySelector('#ptMenu'), wrap = PS.v && PS.v.querySelector('#pmHead');
    if (!m || !wrap) return;
    const id = PS.menu, p = id && planOf(id), btn = p && PS.v.querySelector(`#ptTier button[data-more="${id}"]`);
    if (!p || !btn) { m.hidden = true; m.innerHTML = ''; PS.menu = null; return; }
    m.setAttribute('aria-label', `「${p.name}」範本選單`);
    const act = activeMembers(id);
    m.innerHTML = act.length
      ? `<div class="pmq">還有 <b>${act.length}</b> 位有效會員，請先把他們移到其他付費範本，或等訂閱到期。</div>
         <ul class="pmwho2">${act.slice(0, 8).map((r) => `<li><a href="#admin/members" data-email="${esc(r.email)}">${esc(r.email)}</a></li>`).join('')}${act.length > 8 ? `<li class="more">…還有 ${act.length - 8} 位</li>` : ''}</ul>
         <div class="pmrow2"><a class="pmgo" href="#admin/members">到會員管理</a><button type="button" id="ptMDelNo">知道了</button></div>`
      : `<div class="pmq">刪除「${esc(tabLabel(p))}」？<b>${esc(delMsg(id))}</b>。</div>
         <div class="pmrow2"><button type="button" id="ptMDelNo">取消</button><button type="button" class="danger" id="ptMDelGo">確定刪除</button></div>`;
    m.hidden = false;
    /* 位置：⋮ 正下方、右緣對齊 ⋮；超出內容框就往左收（量完才放，不會推擠任何東西）*/
    const wr = wrap.getBoundingClientRect(), br = btn.getBoundingClientRect();
    m.style.top = Math.round(br.bottom - wr.top + 6) + 'px';
    const w = m.offsetWidth, left = Math.min(Math.max(0, br.right - wr.left - w + 8), wr.width - w);
    m.style.left = Math.round(Math.max(0, left)) + 'px';
  }
  function wireTabs(v) {
    const bar = v.querySelector('#ptTier'), m = v.querySelector('#ptMenu');
    /* 拖曳：只有付費範本（.ptab[draggable]）能拖、也只能放在付費範本上 → 訪客、註冊會員永遠在最前、＋ 永遠在最後。
       往右拖＝放到目標的後面、往左拖＝放到目標的前面（跟游標停在目標哪一半無關，結果可預期）。 */
    const clear = () => bar.querySelectorAll('.ptab').forEach((t) => t.classList.remove('dropL', 'dropR', 'dragging'));
    bar.addEventListener('dragstart', (e) => {
      const t = e.target.closest && e.target.closest('.ptab'); if (!t) return;
      PS.drag = t.dataset.pid; t.classList.add('dragging'); openMenu(null);
      try { e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', t.dataset.pid); } catch (err) { /* 舊瀏覽器 */ }
    });
    bar.addEventListener('dragover', (e) => {
      const t = e.target.closest && e.target.closest('.ptab'); if (!t || !PS.drag || t.dataset.pid === PS.drag) return;
      e.preventDefault();
      const ids = paidIds(), after = ids.indexOf(t.dataset.pid) > ids.indexOf(PS.drag);
      bar.querySelectorAll('.ptab').forEach((x) => { if (x !== t) x.classList.remove('dropL', 'dropR'); });
      t.classList.toggle('dropR', after); t.classList.toggle('dropL', !after);
    });
    bar.addEventListener('drop', (e) => {
      const t = e.target.closest && e.target.closest('.ptab'), from = PS.drag; PS.drag = null; clear();
      if (!t || !from || t.dataset.pid === from) return;
      e.preventDefault();
      const ids = paidIds(), to = ids.indexOf(t.dataset.pid);
      ids.splice(ids.indexOf(from), 1); ids.splice(to, 0, from);
      reorder(ids, `「${(planOf(from) || {}).name || from}」移到第 ${to + 1} 個付費範本`);
    });
    bar.addEventListener('dragend', () => { PS.drag = null; clear(); });
    /* 鍵盤：焦點在付費範本頁籤上按 Alt＋←／→ 直接移動（⋮ 選單也有同樣的左移／右移）*/
    bar.addEventListener('keydown', (e) => {
      const b = e.target.closest && e.target.closest('button[data-plan]');
      if (b && e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) { e.preventDefault(); moveBy(b.dataset.plan, e.key === 'ArrowLeft' ? -1 : 1); }
    });
    /* 點兩下付費範本頁籤 → 原地改名（Enter 存、Esc 取消、失焦存）；訪客／註冊會員是內建的，沒有 data-plan，不能改 */
    bar.addEventListener('dblclick', (e) => {
      const b = e.target.closest && e.target.closest('button[data-plan]'); if (!b) return;
      const id = b.dataset.plan, p = planOf(id), holder = b.closest('.ptab'); if (!p || !holder) return;
      e.preventDefault(); openMenu(null);
      holder.draggable = false; b.innerHTML = `<input class="ptrn" type="text" maxlength="20" value="${esc(p.name)}" aria-label="新的範本名稱">`;
      const inp = b.querySelector('input'); inp.focus(); inp.select();
      let done = false;
      const fin = (save) => { if (done) return; done = true; holder.draggable = true; const v = inp.value.trim(); if (save && v && v !== p.name) renamePlan(id, v); else paintTabs(); };
      inp.onkeydown = (ev) => { ev.stopPropagation(); if (ev.key === 'Enter') { ev.preventDefault(); fin(true); } else if (ev.key === 'Escape') { ev.preventDefault(); fin(false); } };
      inp.onblur = () => fin(true);
      inp.onclick = (ev) => ev.stopPropagation();
    });
    m.addEventListener('click', (e) => {
      const id = PS.menu; if (!id) return;
      if (e.target.closest('#ptMDelGo')) { delPlan(id); return; }
      if (e.target.closest('#ptMDelNo')) openMenu(null, null, true);
    });
    m.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); openMenu(null, null, true); return; }
      if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) {
        const its = [...m.querySelectorAll('button:not(:disabled)')]; if (!its.length) return;
        e.preventDefault();
        const k = its.indexOf(document.activeElement);
        const n = e.key === 'Home' ? 0 : e.key === 'End' ? its.length - 1 : (k + (e.key === 'ArrowDown' ? 1 : -1) + its.length) % its.length;
        its[n].focus();
      }
      if (e.key === 'Tab') openMenu(null);
    });
    if (!PS.menuDoc) { PS.menuDoc = true;
      document.addEventListener('pointerdown', (e) => { if (PS.menu && !e.target.closest('#ptMenu,button[data-more]')) openMenu(null); }, true);
      window.addEventListener('resize', () => { if (PS.menu) paintMenu(); });
    }
  }
  /* 工具列的「全部開／全部關」：開放功能表裡每一類（族群觀測另有自己的全開／全關，不一起動）*/
  function allFeats(on) {
    if (!FT() || !(PS.mode === 'plan' ? planOf(PS.planSel) : PS.rec)) return;
    const ch = {};
    FT().cats.filter((c) => c.id !== 'grp').forEach((c) => FT().inCat(c.id).forEach((f) => { ch[f.id] = f.kind === 'limit' ? (on ? f.max : 0) : on; }));
    setVals(ch);
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
  const ST_NAME = { ok: '有效', soon: '即將到期', exp: '過期', new: '未登入過' };
  /* 顯示用的狀態（perm-v4）：有效裡面再分出「7 天內到期」—— 名單的狀態欄與上方甜甜圈用同一個函式，兩邊數字一定對得上。
     篩選（#pmStatF）仍用 r.st（有效／過期／未登入過），即將到期算在有效裡。 */
  const SOON_MS = 7 * 86400 * 1000;
  const stOf = (r) => { const now = (PS.list && PS.list.now) || Date.now(); return r.st === 'ok' && r.expires && r.expires >= now && r.expires - now <= SOON_MS ? 'soon' : r.st; };
  function paintTarget() {
    const v = PS.v, box = v.querySelector('#pmTarget'); if (!box) return;
    if (PS.mode === 'member') {
      const emails = new Map();
      ((PS.list && PS.list.rows) || []).forEach((r) => emails.set(r.email, r.email));
      ((PS.list && PS.list.users) || []).forEach((u) => { if (u.email && !emails.has(u.email)) emails.set(u.email, u.name ? `${u.name}（${u.email}）` : u.email); });
      const r = PS.rec;
      box.innerHTML = `${PS.editMember ? '<div class="pmbar"><button type="button" id="pmBack" class="pmback">← 回會員名單</button></div>' : ''}<div class="pmbar"><input type="email" id="pmEmail" list="pmEmails" placeholder="輸入或選擇會員 email" autocomplete="off" value="${esc(PS.email)}" aria-label="會員 email">
          <datalist id="pmEmails">${[...emails.entries()].map(([e, l]) => `<option value="${esc(e)}">${esc(l)}</option>`).join('')}</datalist>
          <button type="button" id="pmLoad">讀取</button></div>
        <div class="pmwho" id="pmWho">${r ? whoLine(r) : ''}</div>
        ${r ? `<div class="pmbar"><label>層級／範本 <select id="pmPlan">${planOpts(mPlan(), false)}</select></label>
          <label>到期日 <input type="date" id="pmExp" value="${msToDate(mExp())}" aria-label="到期日（留空＝不會到期）"></label>
          <button type="button" id="pmClearOver" ${Object.keys(mOver()).length ? '' : 'disabled'}>清除個別微調</button>
          <button type="button" class="danger" id="pmReset" ${r.set ? '' : 'disabled'}>移除此會員設定</button></div>` : ''}`;
      const bk = v.querySelector('#pmBack'); if (bk) bk.onclick = leaveMember;
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
    if (PS.adding) {
      box.innerHTML = `<div class="ptinfo"><b class="ptname" id="ptFor">新增付費範本</b><span class="ptmeta">名稱・價格・月／年訂閱</span></div>
        <div class="pmbar" id="ptNewForm" style="margin:0 0 6px"><label>名稱 <input type="text" id="ptNewName" maxlength="20" placeholder="例如 進階方案" aria-label="新付費範本名稱" style="width:12em"></label>
          <label>價格 NT$ <input type="number" id="ptNewPrice" min="0" max="999999" step="1" inputmode="numeric" value="0" aria-label="價格（整數新台幣）" style="width:7em"></label>
          <label>訂閱 <select id="ptNewPeriod" aria-label="月訂閱或年訂閱"><option value="month">月訂閱</option><option value="year">年訂閱</option></select></label>
          <button type="button" class="pri" id="ptNewGo">建立</button><button type="button" id="ptNewCancel">取消</button></div>`;
      const nn = v.querySelector('#ptNewName');
      v.querySelector('#ptNewGo').onclick = () => newPaidPlan(nn.value);
      nn.onkeydown = (e) => { if (e.key === 'Enter') newPaidPlan(nn.value); };
      v.querySelector('#ptNewCancel').onclick = () => { PS.adding = false; paintAll(); };
      paintSave(); return;
    }
    /* 範本資訊列（perm-v4）：左＝名稱・價格／週期（#ptFor）＋套用人數，右＝⚙（只有付費範本有）；下面一行說明 */
    const p = planOf(PS.planSel);
    if (PS.tier === 'paid' && !p) { box.innerHTML = '<div class="ptinfo"><b class="ptname" id="ptFor">尚無付費範本</b></div>'; paintSave(); return; }
    /* 2026-10-06（Andy：「方案分頁上方的標題列都拿掉」）：不再有「訪客・NT$0/月　套用 1 人」那一列 —— 它跟頁籤名稱重複。
       價格與套用人數併進頁籤的滑過提示（tabInfo）；⚙ 範本設定搬到子分頁列的右側（paintSub）；這裡只在 ⚙ 展開時畫設定列。 */
    box.innerHTML = `
      ${PS.tier === 'paid' && PS.cfg ? `<div class="pmbar pmed" id="ptEdit" style="margin:0 0 8px"><label>名稱 <input type="text" id="ptEdName" maxlength="20" value="${esc(p.name)}" aria-label="範本名稱" style="width:10em"></label>
        <label>價格 NT$ <input type="number" id="ptEdPrice" min="0" max="999999" step="1" inputmode="numeric" value="${Number.isInteger(p.price) ? p.price : 0}" aria-label="價格（整數新台幣）" style="width:7em"></label>
        <label>訂閱 <select id="ptEdPeriod" aria-label="月訂閱或年訂閱"><option value="month" ${p.period !== 'year' ? 'selected' : ''}>月訂閱</option><option value="year" ${p.period === 'year' ? 'selected' : ''}>年訂閱</option></select></label>
        <button type="button" class="pri" id="ptEdSave">儲存</button>
        <button type="button" class="danger" id="pmPlanDel" aria-expanded="${!!PS.delAsk}" title="${esc(delMsg(p.id))}">刪除此範本</button>
        <small>金流以範本代號 <code>${esc(p.id)}</code> 對價；改名、改價不影響已指定的會員。</small></div>
        ${PS.delAsk ? `<div class="ptdelq" id="ptDelBox" role="alertdialog" aria-label="確認刪除範本"><span>刪除「${esc(tabLabel(p))}」？<b>${esc(delMsg(p.id))}</b>。</span><button type="button" id="ptDelNo">取消</button><button type="button" class="danger" id="ptDelGo">確定刪除</button></div>` : ''}` : ''}`;
    const cf = v.querySelector('#ptPlanCfg'); if (cf) cf.setAttribute('aria-expanded', String(!!PS.cfg));
    const es = v.querySelector('#ptEdSave'); if (es) es.onclick = () => savePlanMeta(p);
    /* 刪除要二次確認：第一下只展開確認列（寫明會影響幾個人），按「確定刪除」才送 */
    const del = v.querySelector('#pmPlanDel'); if (del) del.onclick = () => { if (activeMembers(PS.planSel).length) { PS.delAsk = false; openMenu(PS.planSel, 'del'); return; } PS.delAsk = !PS.delAsk; paintTarget(); const g = v.querySelector('#ptDelGo'); if (g) g.focus(); };
    const dn = v.querySelector('#ptDelNo'); if (dn) dn.onclick = () => { PS.delAsk = false; paintTarget(); };
    const dg = v.querySelector('#ptDelGo'); if (dg) dg.onclick = () => delPlan(p.id);
    paintSave();
  }
  /* 子分頁：觀看權限｜會員名單（訪客：觀看權限｜—，名單換成流量摘要放在觀看權限上方）*/
  function paintSub() {
    const v = PS.v, bar = v && v.querySelector('#ptSub'); if (!bar) return;
    const noPlan = PS.adding || (PS.tier === 'paid' && !planOf(PS.planSel));
    if (PS.tier === 'guest') PS.sub = 'perm';
    const memb = PS.mode === 'member';
    bar.hidden = noPlan || memb;
    bar.classList.toggle('one', PS.tier === 'guest');
    bar.innerHTML = `<button type="button" role="tab" data-sub="perm" id="ptSubPerm" class="${PS.sub === 'perm' ? 'on' : ''}" aria-selected="${PS.sub === 'perm'}">觀看權限</button>`
      + (PS.tier === 'guest' ? '' : `<button type="button" role="tab" data-sub="list" id="ptSubList" class="${PS.sub === 'list' ? 'on' : ''}" aria-selected="${PS.sub === 'list'}">會員名單</button>`)
      + (PS.tier === 'paid' && !noPlan ? `<button type="button" class="ptgear" id="ptPlanCfg" aria-expanded="${!!PS.cfg}" title="範本設定（改名稱／價格／月或年、刪除）" aria-label="範本設定">⚙</button>` : '');
    const cf = bar.querySelector('#ptPlanCfg'); if (cf) cf.onclick = () => { PS.cfg = !PS.cfg; PS.delAsk = false; paintTarget(); };
    const pb = v.querySelector('#ptPermBox'), lb = v.querySelector('#ptListBox');
    if (pb) pb.hidden = memb ? false : (noPlan || PS.sub !== 'perm');
    if (lb) lb.hidden = memb ? true : (noPlan || PS.sub !== 'list');
    paintGuestSum();
    paintList();
  }
  /* 訪客分頁的流量摘要：近 30 天開啟網站（登入／訪客）、頁面瀏覽、目前在線的訪客 */
  async function paintGuestSum() {
    const box = PS.v && PS.v.querySelector('#ptGuestSum'); if (!box) return;
    /* 2026-10-05 Andy：訪客的流量數字卡不要（流量看「流量觀測」）；流量觀測的「現在誰在線上」整塊拿掉後，
       「一般訪客看得到『目前 N 人在線』」這個開關搬到這裡（訪客的權限就是「訪客能看到什麼」）。 */
    if (PS.tier !== 'guest' || PS.adding) { box.innerHTML = ''; return; }
    box.innerHTML = '<label class="tg ptpub" id="ptPubRow"><input type="checkbox" id="admPub" disabled>一般訪客看得到「目前 N 人在線」（只有總數，看不到名字）</label>';
    const on = await PS.A.call('/v1/admin/online', {});
    const cb = box.querySelector('#admPub'); if (!cb || PS.tier !== 'guest') return;
    if (on && on._s === 200) cb.checked = !!on.public_online;
    cb.disabled = !(on && on._s === 200);
    cb.onchange = async () => { const r = await PS.A.call('/v1/admin/settings', { public_online: cb.checked }); if (!r || r._s !== 200) cb.checked = !cb.checked; };
  }
  /* 範本的名稱／價格／月或年：前端先擋一次（整數 0～999999），後端再驗一次（worker.js adminPlansPut）。
     只送這三欄＋目前存好的開關與次數（沒存的草稿不會被偷偷一起存掉 —— 有草稿就先請他存或取消）。 */
  async function savePlanMeta(p) {
    const v = PS.v; if (!p) return;
    const name = String(v.querySelector('#ptEdName').value || '').trim();
    const raw = String(v.querySelector('#ptEdPrice').value || '').trim(), price = Number(raw);
    const period = v.querySelector('#ptEdPeriod').value;
    if (!name) { setStat('範本名稱不能空白', 'bad'); return; }
    if (RESERVED.test(name)) { setStat('範本名稱不能叫「訪客／註冊會員／免費會員／付費會員」（會跟層級混淆）', 'bad'); return; }
    if (!/^\d{1,6}$/.test(raw) || !Number.isInteger(price) || price > 999999) { setStat('價格要是 0～999999 的整數（新台幣，不含小數）', 'bad'); return; }
    if (PS.draft) { setStat('有未儲存的變更', 'bad'); return; }
    setStat('儲存中…');
    const j = await PS.A.call('/v1/admin/plans/put', { id: p.id, name, feats: p.feats || {}, price, period });
    if (j && j._s === 200) { PS.plans = j.plans; paintTabs(); paintAddPlan(); paintTarget(); paintCats(); setStat(`已儲存「${planLabel(planOf(p.id))}」（台北 ${tpeTime()}）`, 'ok'); }
    else setStat('儲存失敗：' + errText(j), 'bad');
  }
  async function newPaidPlan(name) {
    const v = PS.v; name = String(name || '').trim();
    if (!name) { setStat('請輸入範本名稱', 'bad'); return; }
    const pe = v.querySelector('#ptNewPrice'), raw = String((pe && pe.value) || '0').trim(), price = Number(raw);
    if (!/^\d{1,6}$/.test(raw) || !Number.isInteger(price) || price > 999999) { setStat('價格要是 0～999999 的整數（新台幣，不含小數）', 'bad'); return; }
    const period = (v.querySelector('#ptNewPeriod') || {}).value === 'year' ? 'year' : 'month';
    if (!guard()) return;
    const id = 'p' + Date.now().toString(36).slice(-7);
    const j = await PS.A.call('/v1/admin/plans/put', { id, name, feats: {}, lims: {}, price, period });
    if (!j || j._s !== 200) { setStat('新增失敗：' + errText(j), 'bad'); return; }
    PS.plans = j.plans; PS.tier = 'paid'; PS.planSel = id; PS.draft = null; PS.adding = false; PS.sub = 'perm';
    paintAll(); setStat(`已新增付費範本「${planLabel(planOf(id)) || name}」`, 'ok');
  }
  function whoLine(r) {
    const n = Object.keys(mOver()).length, p = planOf(mPlan()), ex = mExp();
    const who = r.known ? `已登入過：<b>${esc(r.known.name || '')}</b>${r.known.seen ? `（最後登入 ${dstr(r.known.seen)}）` : ''}` : '<b>尚未登入過</b>';
    const exs = ex ? (ex < Date.now() ? `・<b style="color:#ff6b7a">已於 ${msToDate(ex)} 到期</b>（目前套註冊會員）` : `・到期 <b>${msToDate(ex)}</b>`) : '';
    return `<b>${esc(r.email)}</b>・${who}・${TIER_NAME[tierOf(mPlan())]}「<b>${esc(p ? p.name : (r.planName || r.plan))}</b>」${exs}・個別微調 <b>${n}</b> 項${r.set ? '' : ''}`;
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
      const badge = lims && f.kind !== 'limit' ? `<button type="button" class="pmlimb${has ? ' set' : ''}${lv === 0 ? ' zero' : ''}" data-limb="${esc(f.id)}" title="每日瀏覽次數上限" aria-label="${esc(f.name)} 每日瀏覽次數：${has ? lv + ' 次' : '不限'}" aria-expanded="${limOpen}" ${ready ? '' : 'disabled'}>${has ? lv + '/日' : '∞'}</button>` : '';
      const pop = limOpen && f.kind !== 'limit' ? `<div class="pmlimpop" role="dialog" aria-label="${esc(f.name)} 每日瀏覽次數"><span>每日最多</span><input type="number" class="pmlim" data-lim="${esc(f.id)}" min="0" max="9999" step="1" inputmode="numeric" placeholder="不限" value="${lv === '' ? '' : lv}" aria-label="${esc(f.name)} 每日瀏覽次數上限（留空＝不限）"><span>次</span><button type="button" data-limclr="${esc(f.id)}">不限</button><button type="button" class="ok" data-limok="1">確定</button></div>` : '';
      /* 改動用顏色表示、不用文字標籤（Andy 10-05 追加）：未存＝淡琥珀底＋左色條（.dirty）、已存的微調／改過＝淡藍左色條（.tuned）。
         色條用 inset box-shadow 畫，不加 padding —— 撥開關前後版面一像素都不能動。 */
      const rev = PS.mode === 'member' ? `<span class="pmrevc">${diff ? `<button type="button" class="pmrev" data-rev="${esc(f.id)}" title="還原成範本（範本是${base[f.id] === false ? '關' : base[f.id] === true ? '開' : base[f.id]}）">還原</button>` : ''}</span>` : '';
      const limc = lims ? `<span class="pmlimc">${badge}</span>` : '';
      return `<div class="pmrow${compact ? ' sm' : ''}${unsaved ? ' dirty' : ''}${diff ? ' tuned' : ''}${lims ? ' wl' : ''}${f.kind === 'limit' ? ' sel' : ''}${PS.mode === 'member' ? ' wr' : ''}" data-f="${esc(f.id)}">${ctl}<div class="pmtx" title="${esc(f.name)}${f.desc ? '：' + esc(f.desc) : ''}"><b>${compact ? grpIcon(f) : ''}<span class="pmnm nm">${esc(f.name)}</span></b>${compact ? '' : `<small>${esc(f.desc)}</small>`}</div>${limc}${rev}${pop}</div>`;
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
    /* 整組開關（Andy 10-05：「全開 全關 都改成 Switch」「族群觀測需要新增對該族群總開關」）：
       一顆三態 Switch 取代兩顆鈕 —— 全開＝on、全關＝off、部分開＝aria-checked="mixed"（圓鈕停中間）。
       點下去：目前不是全開 → 整組開；全開 → 整組關。樣式跟列上的 .psw 同尺寸，換狀態版面不動。 */
    const swSt = (fs) => { const n = fs.filter(isOn).length; return n === 0 ? 'false' : n === fs.length ? 'true' : 'mixed'; };
    const triSw = (attr, fs, label) => `<button type="button" class="psw3" role="switch" ${attr} aria-checked="${swSt(fs)}" aria-label="${esc(label)}：整組開／關" title="${esc(label)}：整組開／關" ${ready ? '' : 'disabled'}><span></span></button>`;
    /* 整組「次數」按鈕（Andy 10-05）：族群觀測大標題與每個分組標題列，總開關旁多一顆「∞／N/日／混合」；點開同款小框一次設整組每日上限 */
    const gLims = PS.mode === 'plan' ? curLims() : null, gSaved = PS.mode === 'plan' ? savedLims() : null;
    const gFs = (key) => groupFs(key);
    const gLimBtn = (key, label, pre) => { if (!gLims) return ''; const fs = gFs(key); if (!fs.length) return '';
      const vals = new Set(fs.map((f) => (Object.prototype.hasOwnProperty.call(gLims, f.id) ? gLims[f.id] : null))), mixed = vals.size > 1, v1 = mixed ? null : [...vals][0];
      const dirty = ready && fs.some((f) => gSaved[f.id] !== gLims[f.id]);
      return `<button type="button" class="pmlimb pmglim${mixed ? ' mixed' : v1 != null ? ' set' : ''}${v1 === 0 ? ' zero' : ''}${dirty ? ' dirty' : ''}" data-glim="${esc(key)}" title="${esc(label)}：整組每日瀏覽次數上限" aria-label="${esc(label)} 整組每日瀏覽次數：${mixed ? '混合' : v1 == null ? '不限' : v1 + ' 次'}" aria-haspopup="dialog" ${ready ? '' : 'disabled'}>${pre || ''}${mixed ? '混合' : v1 == null ? '∞' : v1 + '/日'}</button>`; };
    const allBtns = (id) => gLimBtn('cat:' + id, (cats.find((c) => c.id === id) || {}).name || id) + triSw(`data-allsw="cat" data-cat="${esc(id)}"`, FT().inCat(id), (cats.find((c) => c.id === id) || {}).name || id);
    const alm = v.querySelector('#pmAllLim'); if (alm) alm.innerHTML = gLimBtn('all', '開放功能表全部', '全部次數 ');
    const tsw = v.querySelector('#pmAllSw');
    if (tsw) { tsw.disabled = !ready; tsw.setAttribute('aria-checked', swSt(cats.filter((c) => c.id !== 'grp').flatMap((c) => FT().inCat(c.id)))); }
    const gbox = v.querySelector('#pmGrp');
    if (gbox) gbox.classList.toggle('off', !ready);
    /* 範本 126：卡片順序＝左側選單順序（FT().cats 的宣告順序），一般 grid 排列、欄數由 CSS 決定（1440 四、1024 三、800 兩、390 一）；不再重排、不再瀑布流 */
    /* 小圖示由 icons.js 依卡片標題自動配上（全站統一做法），這裡不另畫，免得出現兩顆 */
    box.innerHTML = cats.filter((c) => c.id !== 'grp').map((c) => { const fs = FT().inCat(c.id);
      return `<div class="pmcat card" data-cat="${esc(c.id)}"><div class="pmcathd"><h3 title="${esc(c.name)}"><b>${esc(c.name)}</b><small>${cnt(fs)}</small></h3>${allBtns(c.id)}</div>
        <div class="pmbody">${catRows(fs, cur, base, saved, now, ready, false)}</div></div>`; }).join('');
    const gc = cats.find((c) => c.id === 'grp');
    if (gbox) gbox.innerHTML = gc ? (() => {
      const fs = FT().inCat('grp'), k = 'cat:grp', open = PS.open.has(k);
      const gcnt = v.querySelector('#pmGrpCnt'); if (gcnt) gcnt.textContent = cnt(fs);
      const by = {}; fs.forEach((f) => { (by[f.chain || ''] = by[f.chain || ''] || []).push(f); });
      const chName = (ch) => { const d = (fs.find((f) => f.chain === ch) || {}).desc; return d ? d.split('・')[0] : (ch || '其他'); };
      return `<div class="pmcat${open ? '' : ' shut'}" data-cat="grp"><div class="pmcathd">${fold(k, gc.name, fs, 'h3')}${allBtns('grp')}</div>
        <div class="pmbody"${open ? '' : ' hidden'}><div class="grpgrid">`
        + Object.keys(by).map((ch) => { const ck = 'ch:' + ch, co = PS.open.has(ck);
          return `<div class="grpch" data-ch="${esc(ch)}">${fold(ck, chName(ch), by[ch], 'span')}${gLimBtn('ch:' + ch, chName(ch))}${triSw(`data-allsw="ch" data-ch="${esc(ch)}"`, by[ch], chName(ch))}</div>`
            + `<div class="grpbody" data-ch="${esc(ch)}"${co ? '' : ' hidden'}>${catRows(by[ch], cur, base, saved, now, ready, true)}</div>`; }).join('') + '</div></div></div>';
    })() : '';
    if (gbox) gbox.onchange = (e) => box.onchange(e);
    if (gbox) gbox.oninput = (e) => box.oninput(e);
    if (gbox) gbox.onclick = (e) => box.onclick(e);
    if (gbox) gbox.onkeydown = (e) => box.onkeydown(e);
    if (alm) alm.onclick = (e) => { const g = e.target.closest('button[data-glim]'); if (g) { e.stopPropagation(); openGLim(g); } };
    const ttl = v.querySelector('#pmGrpTtl'); if (ttl) ttl.onclick = (e) => box.onclick(e);
    /* 單行規則：放不下就省略號，全文放在 title（滑過看得到）*/
    v.querySelectorAll('.ptwrap .use, .ptwrap .pmwho, .pmlegend span, .ptlede, .pmcathd h3, .grpch .pmfoldhd').forEach((el) => { if (!el.title) el.title = el.textContent.trim(); });
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
      const gb = e.target.closest('button[data-glim]');
      if (gb) { e.stopPropagation(); openGLim(gb); return; }
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
      const a = e.target.closest('button[data-allsw]');
      if (a) {
        const on = a.getAttribute('aria-checked') !== 'true';
        const fs = a.dataset.allsw === 'ch' ? FT().inCat('grp').filter((f) => (f.chain || '') === a.dataset.ch) : FT().inCat(a.dataset.cat);
        const ch = {}; fs.forEach((f) => { ch[f.id] = f.kind === 'limit' ? (on ? f.max : 0) : on; });
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
  /* 整組次數：小框浮在按鈕下方（position:fixed，不被標題列的 overflow 裁掉）；確定 → 組內每個族群一次設成同一值（留空＝不限），整批當一次草稿 */
  /* key：'cat:grp'＝族群觀測整塊、'ch:<鏈>'＝族群分組、'cat:<分類>'＝一般功能卡、'all'＝開放功能表全部卡（不含族群觀測）。次數只算開關列（不含「頁數」下拉那種 limit 列） */
  function groupFs(key) { const nl = (f) => f.kind !== 'limit';
    if (key === 'all') return FT().cats.filter((c) => c.id !== 'grp').flatMap((c) => FT().inCat(c.id)).filter(nl);
    if (key.startsWith('ch:')) return FT().inCat('grp').filter((f) => nl(f) && f.chain === key.slice(3));
    return FT().inCat(key.slice(4)).filter(nl); }
  function setLimMany(fids, n) {
    const p = planOf(PS.planSel); if (!p || PS.mode !== 'plan') return;
    const lims = Object.assign({}, curLims());
    fids.forEach((id) => { if (n == null) delete lims[id]; else lims[id] = n; });
    planDraft(Object.assign({}, (PS.draft && PS.draft.feats) || p.feats || {}), lims);
  }
  function closeGLim() { const o = document.getElementById('pmGPop'); if (o) o.remove(); }
  function openGLim(btn) {
    closeGLim();
    const key = btn.dataset.glim, fs = groupFs(key), lims = curLims();
    const vals = [...new Set(fs.map((f) => (Object.prototype.hasOwnProperty.call(lims, f.id) ? lims[f.id] : null)))];
    const pop = document.createElement('div'); pop.id = 'pmGPop'; pop.className = 'pmlimpop pmgpop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', '整組每日瀏覽次數');
    pop.innerHTML = `<span>每日最多</span><input type="number" min="0" max="9999" step="1" inputmode="numeric" placeholder="${vals.length > 1 ? '混合' : '不限'}" value="${vals.length === 1 && vals[0] != null ? vals[0] : ''}" aria-label="整組每日瀏覽次數上限（留空＝不限）"><span>次</span><button type="button" data-g="clr">不限</button><button type="button" class="ok" data-g="ok">確定</button>`;
    PS.v.appendChild(pop);
    const r = btn.getBoundingClientRect(), w = pop.offsetWidth; pop.style.position = 'fixed'; pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.right - w)) + 'px'; pop.style.top = (r.bottom + 6) + 'px'; pop.style.right = 'auto'; pop.style.bottom = 'auto';
    const inp = pop.querySelector('input'); inp.focus(); inp.select();
    const apply = (n) => { closeGLim(); setLimMany(fs.map((f) => f.id), n); paintTarget(); paintCats(); };
    const confirm = () => { const raw = inp.value.trim(); if (raw !== '' && !(/^\d{1,4}$/.test(raw) && +raw <= 9999)) { inp.classList.add('bad'); return; } apply(raw === '' ? null : +raw); };
    pop.onclick = (e) => { const g = e.target.closest('button[data-g]'); if (!g) return; if (g.dataset.g === 'clr') apply(null); else confirm(); };
    pop.onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); confirm(); } else if (e.key === 'Escape') { e.preventDefault(); closeGLim(); btn.focus(); } };
    setTimeout(() => { const off = (e) => { if (!e.target.closest('#pmGPop,button[data-glim]')) { closeGLim(); document.removeEventListener('pointerdown', off, true); } }; document.addEventListener('pointerdown', off, true); }, 0);
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
    else { setStat('儲存失敗：' + errText(j) + '', 'bad'); }
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
    } else { setStat('儲存失敗：' + errText(j) + '', 'bad'); }
  }
  async function refreshList() {
    PS.mst = {};      // 名單變了 → 上方統計重抓（狀態、人數由名單算，Top 8／活躍由伺服器算）
    const [li, mm] = await Promise.all([PS.A.call('/v1/admin/perm/list', {}), PS.A.call('/v1/admin/members', {})]);
    if (li && li._s === 200) PS.list = li;
    if (mm && mm._s === 200 && Array.isArray(mm.members)) PS.mem = mm;
    paintTabs(); if (PS.mode === 'plan' && !PS.cfg) paintTarget(); paintList();
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
    if (PS.tier === 'free') return all;      // 2026-10-05 會員管理併進來：註冊會員的名單＝所有人員（含付費、尚未登入過的）
    if (PS.tier === 'paid') return all.filter((r) => r.plan === PS.planSel);
    return [];
  }
  function sortVal(r, key) {
    switch (key) {
      case 'plan': return (r.paid ? '0' : '1') + r.planName;
      case 'online': return r.onlineMs; case 'visits': return r.visits30; case 'views': return r.views30;
      case 'feat': return (r.topFeat[0] || [, 0])[1]; case 'stock': return (r.topStock[0] || [, 0])[1];
      case 'st': return ['ok', 'soon', 'new', 'exp'].indexOf(stOf(r));
      default: return r[key] == null ? '' : r[key];
    }
  }
  function memTable(rows, id) {
    const key = PS.sort, dir = PS.dir;
    rows = rows.slice().sort((a, b) => { const x = sortVal(a, key), y = sortVal(b, key); return (x > y ? 1 : x < y ? -1 : 0) * dir || a.email.localeCompare(b.email); });
    const top = (a, nm) => (a.length ? a.map(([k, n]) => `<span class="mchip" title="${esc(nm(k))}：${nf(n)} 次"><span class="mcn">${esc(nm(k))}</span><i>${nf(n)}</i></span>`).join('') : '<span class="mdim">—</span>');
    /* 付費標示縮成一顆金色 ★（方案名已在「方案」欄；全名在滑過提示），讓會員欄永遠一行（Andy 10-05：所有文字一行）*/
    const badge = (r) => (r.paid ? `<span class="pdbadge" title="付費會員：${esc(r.planName)}" aria-label="付費會員：${esc(r.planName)}">★</span>` : r.tier === 'paid' ? `<span class="pdbadge off" title="付費已過期：${esc(r.planName)}" aria-label="付費已過期">★</span>` : '');
    const body = rows.map((r) => {
      const open = PS.exp.has(r.email);
      return `<tr data-email="${esc(r.email)}" class="${PS.rec && r.email === PS.rec.email ? 'on' : ''}${r.paid ? ' paid' : ''}" aria-expanded="${open}">`
        + `<td class="c-who"><span class="who1"><span class="car" aria-hidden="true">${open ? '▾' : '▸'}</span><b title="${esc(r.email)}">${esc(r.email)}</b>${r.name ? `<small title="${esc(r.name)}">${esc(r.name)}</small>` : ''}${badge(r)}</span></td>`
        + `<td class="c-tpl"${r.set ? '' : ' title="尚未個別設定"'}>${r.tier === 'paid' ? esc(r.planName) : '註冊會員'}</td>`
        + `<td class="c-cr">${dday(r.created)}</td><td class="c-exp">${dday(r.expires)}</td><td class="c-seen" title="${r.seen ? dstr(r.seen) : ''}">${seenTxt(r.seen)}</td>`
        + `<td class="c-on num">${dur(r.onlineMs)}</td><td class="c-vis num">${nf(r.visits30)}</td><td class="c-vw num">${nf(r.views30)}</td>`
        + `<td class="c-feat">${top(r.topFeat, compName)}</td><td class="c-stk">${top(r.topStock, (k) => k)}</td>`
        + `<td class="c-st"><span class="stt ${stOf(r)}">${ST_NAME[stOf(r)]}</span></td></tr>`
        + (open ? `<tr class="pmdet" data-for="${esc(r.email)}"><td colspan="${COLS.length}">${detailHtml(r)}</td></tr>` : '');
    }).join('');
    return `<table class="pmlist memtbl" id="${id}"><thead><tr>${COLS.map(([k, n, cls]) => `<th data-sort="${k}" class="${cls}${PS.sort === k ? ' sorted' : ''}" aria-sort="${PS.sort === k ? (PS.dir > 0 ? 'ascending' : 'descending') : 'none'}">${n}${PS.sort === k ? (PS.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table>`;
  }
  /* ---------------------------------------------------------------- perm-v4 統計圖小元件（會員名單上方＋展開明細共用）
     選型照流量觀測頁「？ 圖表怎麼選」那條規則：佔比、≤ 5 類、加總＝全部 → 甜甜圈；類別比大小 → 橫向長條（排序過）；每天的量 → 直條。
     全部是 SVG＋HTML 標籤：每個色塊有 <title>（滑過看數字），文字用文字色、不用系列色；顏色跟著「東西」走（狀態色固定、範本色依 id）。 */
  function donut2(parts, opt) {
    const o = opt || {}, tot = parts.reduce((x, p) => x + p[1], 0), unit = o.unit || '人';
    if (!tot) return `<div class="empty">${esc(o.empty || '沒有資料')}</div>`;
    /* 跟流量觀測同一套甜甜圈：直角、非同組扇區間隙一律 2°、細軌道、中心字、滑過連動（donutG）；這裡只是小一號、圖例每列帶人數 */
    const segs = parts.map(([nm, n, col], i) => ({ label: nm, n, color: col, k: o.keys ? o.keys[i] : nm, ltxt: `${nf(n)} ${unit}・${Math.round(n / tot * 100)}%` })).filter((x) => x.n > 0 || true);
    return donutG(segs.filter((x) => x.n > 0), Object.assign({ cls: 'mdonut', id: o.id, center: [unit === '人' ? '合計' : '合計', nf(tot)], legend: segs, legendN: 8, totalN: tot, aria: o.aria || '占比' }));
  }
  function hbars(list, names, opt) {
    const o = opt || {};
    if (!list.length) return `<div class="empty">${esc(o.empty || '沒有資料')}</div>`;
    const max = Math.max(1, ...list.map((x) => x[1])), tot = list.reduce((x, y) => x + y[1], 0);
    return `<div class="hbars" data-chart="bars"${o.id ? ` id="${o.id}"` : ''}>` + list.map(([k, n], r) => { const nm = names(k), t = tp(`<b>${esc(nm)}</b><br>${nf(n)} 次・占 ${(n / tot * 100).toFixed(1)}%`);
      return `<span class="bl" data-row="${r}"${t}>${esc(nm)}</span><svg data-row="${r}"${t}><rect class="tr" width="100%" height="10" rx="5"/><rect class="v" width="${(n / max * 100).toFixed(1)}%" height="10" rx="5"/></svg><span class="bn" data-row="${r}"${t} data-k="${esc(k)}" data-n="${n}">${nf(n)}</span>`; }).join('') + '</div>';
  }
  const mmdd = (d) => String(d || '').slice(5).replace('-', '/');
  function vbars(days, opt) {
    const o = opt || {}, unit = o.unit || '人';
    if (!days.length || !days.some((d) => d.n)) return `<div class="empty">${esc(o.empty || '沒有資料')}</div>`;
    const max = Math.max(1, ...days.map((d) => d.n)), W = days.length * 10, H = 100, bw = W / days.length, tot = days.reduce((x, d) => x + d.n, 0);
    /* 跟流量觀測直條同規格：細柱（寬 ≈ 0.45 格）、左側 5 個 Y 刻度＋很淡的水平格線、滑過高亮並顯示提示 */
    return `<div class="vbwrap" data-chart="days"><div class="vby">${[1, 0.75, 0.5, 0.25, 0].map((f) => `<span>${nf(Math.round(max * f))}</span>`).join('')}</div>
      <div class="vbplot"><svg class="vbars"${o.id ? ` id="${o.id}"` : ''} viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(o.aria || '近 14 天每天的量')}">`
      + days.map((d, i) => { const h = d.n ? Math.max(3, d.n / max * (H - 2)) : 1.5, w = bw * 0.45;
        return `<rect class="${d.n ? 'v' : 'z'}" data-row="${i}"${tp(`<b>${esc(d.day)}</b><br>${esc(d.tip ? d.tip.replace(/^[^：]*：/, '') : nf(d.n) + ' ' + unit)}<br>占期間 ${(d.n / Math.max(1, tot) * 100).toFixed(1)}%`)} data-n="${d.n}" x="${(i * bw + (bw - w) / 2).toFixed(1)}" y="${(H - h).toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}"></rect>`; }).join('')
      + `</svg></div></div><div class="vbx"><span>${mmdd(days[0].day)}</span><span>${mmdd(days[days.length >> 1].day)}</span><span>${mmdd(days[days.length - 1].day)}</span></div>`;
  }
  /* 股票標籤＝代號＋名稱（名稱從站上的全站索引 window.Link.cname 拿；拿不到就只寫代號）*/
  const stockNm = (c) => { const n = window.Link && window.Link.cname && window.Link.cname[c]; return n ? `${c} ${n}` : c; };
  const kpi = (n, label, id, tip) => `<div class="mkpi"${id ? ` id="${id}"` : ''}${tip ? ` title="${esc(tip)}"` : ''}><b>${n}</b><span title="${esc(tip || label)}">${esc(label)}</span></div>`;
  /* ---------------------------------------------------------------- 會員名單上方的統計（2026-10-06 重做）
     Andy：「上方圖表需要優化，Follow 觀測流量 分頁，並且數據請補齊全」。
     設計語彙＝流量觀測：同樣的 .card（問句式粗體標題＋左側色條小圖示＋灰色副標）、期間列（下拉＋起訖日同步）、每天直條（dayplot）、
     甜甜圈（donutG，圖例在右）、橫條（bars）。KPI 與三張圖都跟著期間走；「會員現在是什麼狀態」是現況，不隨期間變（副標寫明）。
     資料：/v1/admin/members/stats { scope, plan, from, to, bin }（伺服器端彙總，不逐人呼叫）。

     ★ 「載入中…」永遠不消失的根因（2026-10-06 查到，admin.js 這一段舊碼）：
       refreshList()（每次儲存、刪範本、逐人微調回來都會跑）第一行 `PS.mst = {}` 把統計快取清空，
       但舊的 loadMStats() 只在「第一次畫殼」時呼叫一次；清空之後 statsHtml() 讀不到快取就當成「載入中」，
       而殼已經畫過了（shellKey 沒變）→ 沒有人再去讀 → 永遠停在「載入中…」，KPI 的「近 7 日活躍」也跟著顯示「—」。
       現在：paintStats() 每次畫之前都先確認有沒有快取、沒有就去讀；讀取最多等 15 秒，逾時／失敗顯示白話原因＋「重新讀取」鈕。 */
  const PER_OPT = [['7', '近 7 天'], ['30', '近 30 天'], ['90', '近 90 天'], ['365', '近 365 天'], ['since', '起始日期～至今']];
  const dayAdd = (d, n) => new Date(Date.parse(d + 'T00:00:00Z') + n * 86400000).toISOString().slice(0, 10);
  const okDay = (x) => /^\d{4}-\d{2}-\d{2}$/.test(x || '');
  const perOf = () => PS.per || (PS.per = { period: '30', since: '', until: '' });
  /* 管理區的期間列（下拉＋起訖日同步）：近 N 天＝那段的實際起訖；手動改日期 → 下拉跳成「起始日期～至今」。最長 400 天（Worker 的上限）。 */
  function perRange(per) {
    const today = todayTpe(), floor = dayAdd(today, -399);
    if (per.period === 'since' && okDay(per.since)) { const from = per.since < floor ? floor : per.since; let to = per.until && okDay(per.until) && per.until < today ? per.until : today; if (to < from) to = from; return { from, to }; }
    const n = Math.min(400, Math.max(1, +per.period || 30));
    return { from: dayAdd(today, -(n - 1)), to: today };
  }
  const perBin = (r) => { const n = (Date.parse(r.to) - Date.parse(r.from)) / 86400000 + 1; return n <= 62 ? 'day' : n <= 210 ? 'week' : 'month'; };
  const perTxt = (per, r) => (per.period === 'since' ? `${r.from}～${r.to}` : `近 ${per.period} 天`);
  function periodCtlHtml(per, id) {
    const r = perRange(per), today = todayTpe();
    return `<div class="trctl" id="${id}"><label>期間 <select id="${id}Sel" aria-label="統計期間">${PER_OPT.map(([k, n]) => `<option value="${k}"${k === per.period ? ' selected' : ''}>${n}</option>`).join('')}</select></label>
      <input type="date" id="${id}From" value="${esc(r.from)}" max="${today}" aria-label="起始日期"><span class="trto">～</span><input type="date" id="${id}To" value="${esc(r.to)}" min="${esc(r.from)}" max="${today}" aria-label="結束日期"></div>`;
  }
  function periodWire(root, per, id, onChange) {
    const sel = root.querySelector('#' + id + 'Sel'), di = root.querySelector('#' + id + 'From'), du = root.querySelector('#' + id + 'To');
    if (!sel || !di || !du) return;
    sel.onchange = () => { per.period = sel.value; if (per.period === 'since') { per.since = di.value; per.until = ''; } onChange(); };
    const manual = () => { if (!okDay(di.value)) return; let to = okDay(du.value) ? du.value : todayTpe(); if (to < di.value) to = di.value; per.period = 'since'; per.since = di.value; per.until = to >= todayTpe() ? '' : to; onChange(); };
    di.onchange = manual; du.onchange = manual;
  }
  const MS_CSS = `
/* ===== 會員名單上方的統計（2026-10-06）：版型＝6 欄格線。第一列「每天多少人」4＋「狀態」2；第二列 註冊會員＝三張各 2、付費＝兩張各 3 ===== */
/* ⚙ 範本設定：2026-10-06 起在子分頁列的最右邊（原本在已拿掉的標題列裡） */
#v-admin .ptwrap .ptsub .ptgear{margin-left:auto;align-self:center;margin-bottom:4px}
/* 標題列拿掉後，子分頁列補回原本標題列的上方留白（不然會貼住內容框頂、蓋到選中頁籤的底邊） */
#pmTarget{padding-top:14px}#pmTarget:empty{padding-top:0}
#ptStats{margin:0 0 14px}
#ptStats .secttl{margin:4px 0 0;flex-wrap:wrap;align-items:center;row-gap:8px}
#ptStats .secttl h2{font-size:var(--fs-h2,20px);font-weight:600}
#ptStats .mkpis{grid-template-columns:repeat(6,minmax(0,1fr));margin-top:12px}
#ptStats .mkpi b{font-size:20px}
#ptStats .mkpi span{font-size:13px}
#ptStats .msnote{margin:8px 2px 0;font-size:12px;color:var(--ink-2)}
#v-admin .admgrid.msgrid{grid-template-columns:repeat(12,minmax(0,1fr));margin-top:12px}
#v-admin .msgrid>.ma{grid-column:span 7}#v-admin .msgrid>.mb{grid-column:span 5}#v-admin .msgrid>.mc{grid-column:span 4}#v-admin .msgrid>.md{grid-column:span 6}
#ptStats .msph{padding:10px 0;font-size:13px;color:var(--ink-2)}
#ptStats .msph.bad{color:var(--st-exp,#e5484d)}
#ptStats .msph button{height:28px;font-size:13px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 10px;margin-left:8px;cursor:pointer}
#ptStats .card .empty{padding:10px 0}
@media (max-width:1100px){#v-admin .msgrid>.ma,#v-admin .msgrid>.mb,#v-admin .msgrid>.mc{grid-column:span 12}#ptStats .mkpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:640px){#ptStats .mkpis{grid-template-columns:repeat(2,minmax(0,1fr))}#ptStats .mkpi{padding:8px 10px}#ptStats .mkpi b{font-size:17px}}
@media (max-width:820px){#v-admin .admgrid.msgrid{grid-template-columns:minmax(0,1fr)}#v-admin .msgrid>.ma,#v-admin .msgrid>.mb,#v-admin .msgrid>.mc,#v-admin .msgrid>.md{grid-column:auto}#ptStats .trhead .trctl{width:100%}}
`;
  const mKey = () => (PS.tier === 'paid' ? 'plan:' + PS.planSel : 'all');
  const durZ = (ms) => (ms > 0 ? dur(ms) : '0 分');
  async function loadMStats(k, r, bin) {
    if (!PS.mst) PS.mst = {};
    if (PS.mst[k]) return;
    PS.mst[k] = { loading: true };
    const body = Object.assign(PS.tier === 'paid' ? { scope: 'plan', plan: PS.planSel } : { scope: 'all' }, { from: r.from, to: r.to, bin });
    let j = null;
    try { j = await Promise.race([PS.A.call('/v1/admin/members/stats', body), new Promise((res) => setTimeout(() => res({ _timeout: true }), 15000))]); } catch (e) { j = null; }
    let out;
    if (j && j._timeout) out = { err: '會員系統 15 秒沒有回應' };
    else if (j && j._s === 200 && Array.isArray(j.days) && j.active != null) out = j;
    else if (j && j._s === 200) out = { err: '會員系統版本較舊，還沒有這個期間的統計（Worker 部署完成後重新整理就會有）' };
    else if (j && j._s === 404) out = { err: '會員系統還沒更新，讀不到這項統計' };
    else if (j && j._s === 400) out = { err: '期間不正確（最長 400 天、起日不能晚於結束日）' };
    else out = { err: '讀不到（' + errText(j) + '）' };
    if (!PS.mst) PS.mst = {};
    PS.mst[k] = out;
    paintStats();
  }
  const PLAN_COL = ['var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)'];
  /* 每個區間（天／週／月）活躍的不同人數：同流量觀測「每天有多少瀏覽？」的直條（.dayplot／.days），Y 軸刻度一律整數（人數） */
  function binChart(days, bin, idp) {
    const mxN = Math.max(0, ...days.map((d) => d.n));
    if (!days.length || !mxN) return '<div class="empty">這段期間沒有活動</div>';
    const ymax = mxN <= 4 ? 4 : Math.ceil(mxN / 4) * 4, few = days.length <= 7, avg = sum(days.map((d) => d.n)) / days.length;
    const mxd = days.reduce((a, d, i) => (d.n > days[a].n ? i : a), 0);
    const lab = (d) => (bin === 'month' ? d.day.slice(0, 7).replace('-', '/') : d.day.slice(5).replace('-', '/'));
    const ttl = (d) => (bin === 'month' ? `${d.day.slice(0, 4)} 年 ${+d.day.slice(5, 7)} 月` : bin === 'week' ? `${d.day.slice(5).replace('-', '/')}～${dayAdd(d.day, 6).slice(5).replace('-', '/')} 這一週` : `${d.day}（週${WK[new Date(Date.parse(d.day + 'T00:00:00Z')).getUTCDay()]}）`);
    const step = Math.max(1, Math.ceil(days.length / 8));
    const ys = [1, 0.75, 0.5, 0.25, 0].map((f) => `<span>${nf(Math.round(ymax * f))}</span>`).join('');
    return `<div class="dayplot"><div class="dayy">${ys}</div>
      <div class="days${few ? ' few' : ''}${days.length > 90 ? ' many' : ''}" data-chart="days" id="${idp}" data-bin="${bin}">${days.map((d, i) => `<div class="dc${i === mxd ? ' mx' : ''}" data-row="${i}" data-n="${d.n}"${tp(`<b>${esc(ttl(d))}</b><br>${nf(d.n)} 人活躍<br>造訪 ${nf(d.visits || 0)} 次・瀏覽 ${nf(d.pv || 0)} 頁`)}>${few || i === mxd ? `<span class="dv">${nf(d.n)}</span>` : ''}<i style="height:${(d.n / ymax * 100).toFixed(1)}%"></i>${few ? `<span class="dd">${esc(lab(d))}</span>` : ''}</div>`).join('')}
        ${days.length > 1 ? `<div class="avg" style="bottom:${(avg / ymax * 100).toFixed(1)}%"><b>平均 ${avg >= 10 ? nf(Math.round(avg)) : avg.toFixed(1)}</b></div>` : ''}</div></div>
      ${few ? '' : `<div class="dayticks" id="${idp}Ticks"><div>${days.map((d, i) => (i % step ? '' : `<span style="left:${((i + 0.5) / days.length * 100).toFixed(2)}%">${esc(lab(d))}</span>`)).join('')}</div></div>`}`;
  }
  /* 名單上方的統計：狀態、人數由「同一份名單 rows」算（跟下面的表一定一致）；活躍、造訪、在線、瀏覽、Top 8、每日活躍由伺服器依期間彙總 */
  function statsHtml(rows, k, r, bin) {
    const per = perOf(), s = (PS.mst || {})[k] || { loading: true };
    const wait = s.loading ? '載入中…' : s.err ? s.err : '', pt = perTxt(per, r);
    const ph = (msg) => `<div class="msph${s.err ? ' bad' : ''}" role="status">${esc(msg)}${s.err ? ' <button type="button" class="msretry">重新讀取</button>' : ''}</div>`;
    const val = (f) => (wait ? (s.err ? '—' : '…') : f());
    const kp = kpi(nf(rows.length), '總人數', 'msTotal', `目前全部會員（含還沒登入過的）；不隨期間變動${wait ? '' : `。${pt}內新加入 ${nf(s.joined)} 人`}`)
      + kpi(val(() => nf(s.active)), `活躍人數`, 'msActive', `${pt}內有開站、在線或使用功能的不同人數`)
      + kpi(val(() => nf(s.visits)), '造訪次數', 'msVisits', `${pt}內開啟網站的次數（登入狀態）`)
      + kpi(val(() => nf(s.pv)), '頁面瀏覽', 'msPv', `${pt}內看過的頁面數（登入狀態）`)
      + kpi(val(() => durZ(s.active ? s.ms / s.active : 0)), '平均每人在線', 'msAvgOn', `${pt}內，每位活躍會員的累計在線時間`)
      + kpi(val(() => durZ(s.visits ? s.ms / s.visits : 0)), '平均每次停留', 'msAvgStay', `${pt}內，每次造訪平均停留多久`);
    const cnt = { ok: 0, soon: 0, exp: 0, new: 0 }; rows.forEach((x) => { cnt[stOf(x)] += 1; });
    /* 甜甜圈：跟流量觀測同一顆（donutG：直角、2° 間隙、細軌道、中心字、圖例在右）；圖例每列帶人數與占比 */
    const dn = (parts, o) => {
      const tot = sum(parts.map((x) => x[1])); if (!tot) return '<div class="empty">沒有資料</div>';
      const segs = parts.map(([nm, n, col], i) => ({ label: nm, n, color: col, k: o.keys[i], ltxt: `${nf(n)} 人・${Math.round(n / tot * 100)}%` }));
      return donutG(segs.filter((x) => x.n > 0), { id: o.id, center: ['合計', nf(tot)], legend: segs, legendN: 8, totalN: tot, aria: o.aria });
    };
    const cards = [card('msDaysC', `${{ day: '每天', week: '每週', month: '每月' }[bin]}有多少人在用？`, `${{ day: '每天', week: '每週（週一起算）', month: '每月' }[bin]}有活動的不同人數`, wait ? ph(wait) : binChart(s.days || [], bin, 'msDays'), 'ma'),
      card('msStatusC', '會員現在是什麼狀態？', '目前狀態，不隨期間變',
        dn([['有效', cnt.ok, 'var(--st-ok)'], ['7 天內到期', cnt.soon, 'var(--st-soon)'], ['已過期', cnt.exp, 'var(--st-exp)'], ['未登入過', cnt.new, 'var(--st-new)']], { id: 'msStDonut', keys: ['ok', 'soon', 'exp', 'new'], aria: '這一層會員的狀態分布' }), 'mb')];
    if (PS.tier === 'free') {
      /* 註冊會員頁：免費 vs 各付費方案（只算付費有效的；過期的算免費 —— 他現在套的就是註冊會員）。最多 4 個方案，其餘併「其他付費」→ ≤ 5 類 */
      const by = new Map(); rows.forEach((x) => { if (x.paid) by.set(x.plan, (by.get(x.plan) || 0) + 1); });
      const ids = [...by.keys()].sort((a, b) => by.get(b) - by.get(a));
      const slot = (id) => PLAN_COL[[...PS.plans.map((p) => p.id)].sort().indexOf(id) % PLAN_COL.length] || 'var(--c5)';
      const head = ids.length > 4 ? ids.slice(0, 3) : ids, rest = ids.length > 4 ? ids.slice(3) : [];
      const parts = [['免費', rows.filter((x) => !x.paid).length, 'var(--c0)']].concat(head.map((id) => [(planOf(id) || {}).name || id, by.get(id), slot(id)]));
      if (rest.length) parts.push(['其他付費', rest.reduce((a, id) => a + by.get(id), 0), 'var(--c5)']);
      cards.push(card('msPlanC', '免費和付費各占多少？', '目前狀態：付費＝有效的付費方案', dn(parts, { id: 'msPlanDonut', keys: ['free'].concat(head, rest.length ? ['other'] : []), aria: '免費與各付費方案人數' }), 'mc'));
    }
    const cls = PS.tier === 'free' ? 'mc' : 'md', none = '<div class="empty">這段期間沒有活動</div>';
    cards.push(card('msFeatC', '最常用哪些功能？', `${pt}・前 8 名`, wait ? ph(wait) : ((s.feats || []).length ? bars(s.feats, compName, s.featTotal || sum(s.feats.map((x) => x[1])), { id: 'msFeat' }) : none), cls),
      card('msStockC', '最常看哪些股票？', `${pt}・前 8 名`, wait ? ph(wait) : ((s.stocks || []).length ? bars(s.stocks, stockNm, s.stockTotal || sum(s.stocks.map((x) => x[1])), { id: 'msStock' }) : none), cls));
    const keep = s.keepDays || 90, note = !wait && r.from < dayAdd(todayTpe(), -(keep - 1)) ? `個人使用紀錄只保留近 ${keep} 天：期間內更早的活動不在活躍人數、功能、股票的統計裡。` : (!wait && s.since && s.since > r.from ? `使用紀錄從 ${s.since} 起；更早的日子沒有資料。` : '');
    return `<div class="secttl trhead"><h2>會員使用概況</h2><small>${esc(PS.tier === 'free' ? '註冊會員（含付費）' : (planOf(PS.planSel) || {}).name || '')}・${esc(pt)}</small><span class="sp"></span>${periodCtlHtml(per, 'msPer')}</div>
      <div class="mkpis">${kp}</div>${note ? `<p class="msnote" id="msNote">${esc(note)}</p>` : ''}<div class="admgrid msgrid" id="msCharts">${cards.join('')}</div>`;
  }
  /* 統計區的唯一畫法：每次都先確認快取在不在（不在＝去讀），再畫；內容沒變（同一期間、同一份名單、同一個讀取狀態）就不重畫，免得搜尋打字時圖一直閃 */
  function paintStats() {
    if (!PS.v || PS.mode !== 'plan' || PS.tier === 'guest') return;
    const el = PS.v.querySelector('#ptStats'); if (!el) return;
    const per = perOf(), rows = listRows(), r = perRange(per), bin = perBin(r), k = `${mKey()}|${r.from}|${r.to}|${bin}`;
    loadMStats(k, r, bin);
    const e = PS.mst[k], sig = [k, e.loading ? 'L' : e.err ? 'E' : 'D', rows.length, rows.map((x) => stOf(x) + (x.paid ? 1 : 0) + x.plan).join(',')].join('|');
    if (el.dataset.sig === sig) return;
    el.dataset.sig = sig;
    const af = document.activeElement && el.contains(document.activeElement) ? document.activeElement.id : '';
    el.innerHTML = statsHtml(rows, k, r, bin);
    periodWire(el, per, 'msPer', () => { el.dataset.sig = ''; paintStats(); });
    const rt = el.querySelector('.msretry'); if (rt) rt.onclick = () => { delete PS.mst[k]; el.dataset.sig = ''; paintStats(); };
    if (af) { const n = el.querySelector('#' + af); if (n) n.focus(); }
  }
  /* 展開明細（Andy 10-05：數字太大、被上一列擋住、四塊位置亂）：一排四個小數字（≤ 20px）＋一排四張同高圖卡，
     放在表格裡獨立的一列（colspan 全寬、自己的底色與內距），不用任何絕對定位 → 不會蓋到上下列。 */
  function detailHtml(r) {
    const tune = PS.mode === 'member' ? '' : `<div class="pmbar"><button type="button" class="pri" data-tune="${esc(r.email)}">逐人微調…</button></div>`;
    const body = detailBody(r);
    return body.replace(/<\/div>$/, tune + '</div>');
  }
  function detailBody(r) {
    const d = PS.det[r.email];
    if (!d) return '<div class="mdet"><div class="empty">讀取使用紀錄中…</div></div>';
    if (d.err) return `<div class="mdet"><div class="empty">${esc(d.err)}</div></div>`;
    if (!d.known) return '<div class="mdet"><div class="empty">尚未登入</div></div>';
    const days = (d.days || []).map((x) => ({ day: x.day, n: x.views || 0, tip: `${x.day}：造訪 ${x.visits} 次、瀏覽 ${x.views} 頁、在線 ${dur(x.ms)}` }));
    const avg = r.visits30 ? r.online30 / r.visits30 : 0;
    const pages = (d.pages || []).slice().sort((a, b) => b[1] - a[1]);
    const pp = pages.length > 5 ? pages.slice(0, 4).concat([['_other', pages.slice(4).reduce((a, x) => a + x[1], 0)]]) : pages;
    const pcol = ['var(--c1)', 'var(--c2)', 'var(--c3)', 'var(--c4)', 'var(--c5)'];
    const feats = (d.feats || []).slice(0, 8).map(([pg, c, n]) => [pg + '|' + c, n]);
    return `<div class="mdet" data-email="${esc(r.email)}">
      <div class="mkpis">${kpi(nf(r.days30), '近 30 天活躍天數')}${kpi(dur(r.online30), '近 30 天在線')}${kpi(avg ? dur(avg) : '—', '平均每次停留')}${kpi(nf(r.views30), '近 30 天頁面瀏覽')}</div>
      <div class="mcharts">
        <div class="mchart" data-ch="days"><h4>近 14 天每日活躍<small>頁面瀏覽</small></h4>${vbars(days, { unit: '頁', aria: '近 14 天每天的頁面瀏覽' })}</div>
        <div class="mchart" data-ch="pages"><h4>各分頁瀏覽<small>近 30 天</small></h4>${donut2(pp.map(([k, n], i) => [k === '_other' ? '其他' : (VIEW_NAME[k] || k), n, k === '_other' ? 'var(--c0)' : pcol[i]]), { unit: '次', aria: '各分頁瀏覽佔比', empty: '沒有資料' })}</div>
        <div class="mchart" data-ch="feats"><h4>功能使用次數 Top 8</h4>${hbars(feats, (k) => { const [pg, c] = k.split('|'); return (VIEW_NAME[pg] || pg) + '・' + compName(c); }, { empty: '沒有資料' })}</div>
        <div class="mchart" data-ch="stocks"><h4>最常看的股票 Top 8</h4>${hbars((d.stocks || []).slice(0, 8), stockNm, { empty: '沒有資料' })}</div></div>
      </div>`;
  }
  async function loadDetail(email) {
    if (PS.det[email] && !PS.det[email].err) return;
    const j = await PS.A.call('/v1/admin/member/detail', { email });
    PS.det[email] = j && j._s === 200 && Array.isArray(j.days) ? j : { err: j && j._s === 404 ? '讀不到使用紀錄' : '讀不到使用紀錄（' + errText(j) + '）' };
    paintList();
  }
  function paintList() {
    if (!PS.v) return;
    if (PS.mode === 'plan') {
      const box = PS.v.querySelector('#ptListBox'); if (!box || box.hidden) return;
      const rows = listRows(), use = (PS.tier === 'free' ? '所有人員（含付費與尚未登入過的）；金色徽章＝付費會員（後面是方案名）、過期的標「過期」。' : '被指定到這個範本的會員。')
        + '';
      const defPlan = PS.tier === 'paid' ? PS.planSel : 'free';
      /* 殼（統計、新增會員列、搜尋列）只在第一次或換層級／範本時畫，之後打字搜尋只換表格，輸入框不會掉焦點 */
      const shellKey = PS.tier + '|' + PS.planSel;
      if (!box.querySelector('#ptTableBox') || box.dataset.shell !== shellKey) {
        box.dataset.shell = shellKey;
        box.innerHTML = `<div class="ptinner" id="ptMail"><div class="mstats" id="ptStats"></div>
          <div class="pmbar"><input type="search" id="pmSearch" placeholder="搜尋 email、名字、層級或範本" aria-label="搜尋會員" value="${esc(PS.q)}">
            <select id="pmStatF" aria-label="依狀態篩選"><option value="">全部狀態</option><option value="ok">有效</option><option value="exp">過期</option><option value="new">未登入過</option></select><span class="pmcnt" id="pmCnt"></span></div>
          <div id="ptTableBox"></div></div>`;
        const vv = PS.v; vv.querySelector('#pmStatF').value = PS.stf;
        vv.querySelector('#pmSearch').oninput = (e) => { PS.q = e.target.value; paintList(); };
        vv.querySelector('#pmStatF').onchange = (e) => { PS.stf = e.target.value; paintList(); };
      }
      paintStats();       // 統計區：換期間／換範本／名單變了都會走到這裡；沒有快取就去讀（不會卡在「載入中」）
      const q = PS.q.trim().toLowerCase();
      let fr = q ? rows.filter((r) => (r.email + ' ' + r.name + ' ' + r.planName + ' ' + TIER_NAME[r.tier]).toLowerCase().includes(q)) : rows.slice();
      if (PS.stf) fr = fr.filter((r) => r.st === PS.stf);
      const cnt = box.querySelector('#pmCnt'); if (cnt) cnt.textContent = (q || PS.stf) ? `${fr.length} ／ ${rows.length} 位` : `共 ${rows.length} 位`;
      if (cnt) cnt.title = use;
      const tb = box.querySelector('#ptTableBox');
      tb.innerHTML = fr.length ? memTable(fr, 'ptTable') : `<div class="empty">${q || PS.stf ? '沒有符合條件的會員。' : '沒有人'}</div>`;
      wireList(tb);
      return;
    }
    const box = PS.v.querySelector('#pmListBody'); if (!box) return;
    const pn = (r) => r.planName;
    const all = members();
    const q = PS.q.trim().toLowerCase();
    let rows = q ? all.filter((r) => (r.email + ' ' + r.name + ' ' + pn(r) + ' ' + TIER_NAME[r.tier]).toLowerCase().includes(q)) : all.slice();
    if (PS.stf) rows = rows.filter((r) => r.st === PS.stf);
    const cnt = PS.v.querySelector('#pmCnt'); if (cnt) cnt.textContent = (q || PS.stf) ? `${rows.length} ／ ${all.length} 位` : `共 ${all.length} 位`;
    box.innerHTML = rows.length ? memTable(rows, 'pmTable') : `<div class="empty">${q || PS.stf ? '沒有符合條件的會員。' : '沒有會員'}</div>`;
    wireList(box);
  }
  /* 逐人微調：從會員名單的展開明細進來。同一個頁框換成「這個人」的設定（層級／範本、到期日、開關），頁籤與子分頁暫時收起，左上「← 回會員名單」 */
  function enterMember(email) {
    if (!guard()) return;
    PS.editMember = true; PS.mode = 'member'; PS.email = email; PS.rec = null; PS.draft = null;
    const h = PS.v.querySelector('#pmHead'); if (h) h.classList.add('medit');
    paintAll(); loadMember(email);
  }
  function leaveMember() {
    if (!guard()) return;
    PS.editMember = false; PS.mode = 'plan'; PS.rec = null; PS.draft = null; PS.sub = 'list';
    const h = PS.v.querySelector('#pmHead'); if (h) h.classList.remove('medit');
    pickTierPlan(); paintAll(); setStat(''); refreshList();
  }
  function wireList(box) {
    box.onclick = (e) => {
      const th = e.target.closest('th[data-sort]');
      if (th) { if (PS.sort === th.dataset.sort) PS.dir = -PS.dir; else { PS.sort = th.dataset.sort; PS.dir = th.dataset.sort === 'email' ? 1 : -1; } paintList(); return; }
      const tu = e.target.closest('button[data-tune]'); if (tu) { enterMember(tu.dataset.tune); return; }
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
