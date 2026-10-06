/* 產業與個股（合併頁）：產業地圖 → 單一產業鏈（族群總覽 + 產品剖析圖 + 分層關聯圖）→ 個股頁。
   個股頁上方永遠帶著它所屬的產業鏈，點任何股票上方同步更新。 */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  /* ★ 2026-10-01 卡頓（DECISIONS #284）：換掉一塊 innerHTML 之前，先把裡面的 ECharts 實例 dispose。
     不 dispose 的話，ECharts 自己的實例表一直抓著舊容器（脫離畫面的 DOM、畫布、事件），永遠回收不掉 ——
     實測切頁 10 輪：每進一次產業地圖漏 2 張（gpBar／gpPie）、熱力圖漏 1 張（indTree），
     JS 記憶體 24 → 55MB、事件監聽每輪 +138。只釋放「即將被換掉的那一塊」裡的圖，畫面行為不變。*/
  function disposeCharts(root) {
    if (!root || !window.echarts) return;
    root.querySelectorAll('[_echarts_instance_]').forEach(d => {
      try { const i = echarts.getInstanceByDom(d); if (i && !i.isDisposed()) i.dispose(); } catch (e) { /* 已經沒了 */ }
    });
  }
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  /* ★ 2026-10-06 即時僅管理者（Andy：「所有的即時功能，只有在我這帳號才會出現，其他帳號都隱藏」，DECISIONS #326）。
     這支檔裡的即時入口：族群總覽的「即時」鈕、個股週期列的 1分／5分／15分（只有即時來源，非管理者沒有任何資料可畫）。
     分時（tick）留著：非管理者看的是資料湖 60 分 K 的最近交易日（盤後版本），livek.js 不 attach 輪詢。*/
  const liveOK = () => !!(window.TwLive && window.TwLive.allowed());
  let A;                                   // window.App（app.js 提供）
  /* ★ 2026-09-28 預設週期改成「分時」（Andy：「K線圖新增分時走勢（Default 設定在上面…）」）。
     tfAuto＝這次的週期是「預設帶進來的」不是使用者按的：分時真的沒資料時只有這種情況才自動改用日 K；
     tickFb＝上一檔是自動退回日 K 的 → 換下一檔要回到分時（不然一檔沒資料就把之後每一檔都變成日 K）。*/
  const state = { level: 0, chain: null, group: null, code: null, tf: 'tick', mtfMode: false, cfg: null, tab: 'overview', dg: null,
    tfAuto: true, tickFb: false };
  /* ★ 2026-09-21：中文名一律先讀 payload（`A.L.chains`，來源是 groups.yaml 的 chains.<id>.name），
     這張表只當「payload 裡沒有的虛擬鍵」與 L 還沒 init 完的 fallback ——
     以前它是第二份對照表，新增的 software / financial 沒補進來就直接印英文 id 上畫面。*/
  const CHAIN_NAME = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子', software: '軟體與資訊服務', financial: '金融', traditional: '傳產', infrastructure: '基礎建設', _other: '其他族群', industry: '法定產業別' };
  const SEG_COLORS = ['#3ee0ff', '#8b7bff', '#ffb454', '#c3ff5b', '#ff8fab', '#5ec8ff', '#f9f871', '#7ee8c7', '#ff9f68', '#b39dff', '#6ee7b7', '#fca5a5', '#93c5fd', '#fde68a'];
  let kchart = null, miniCharts = [];
  // 分時走勢（週期「分時」）的圖：跟 kchart 不會同時存在（見 setupChart 的 applyTick）
  let tchart = null, tickTimer = null, tickT0 = 0;
  const TICK_WAIT = 8000;       // 即時層抓 Yahoo 最多等 8 秒；還沒回來就當作沒有（不然網路卡住會一直轉圈）
  // 指標下拉裡哪幾列是展開的（換股票、關掉再打開都維持；只活在這一次瀏覽）
  const indOpen = new Set();
  // 即時分 K 的訂閱（換頁要退掉，不然背景還在每 5 秒重畫一張看不到的圖）
  let liveOff = null;

  function setLiveNote(txt) {
    const el = document.getElementById('liveNote');
    if (!el) return;
    el.hidden = !txt;
    el.textContent = txt || '';
    el.title = txt || '';      // 桌機兩欄時短註只顯示一行（stock_ai.js #293），滑過看全文
    if (!txt) el.classList.remove('open');
    /* 手機上短註只佔一行（CSS 見 body.m3on.mbon #liveNote）→ 點一下展開全文、再點收回。
       桌機是完整換行的，class 切了也沒有差別，所以不分寬度一律掛上。*/
    if (!el.onclick) el.onclick = () => el.classList.toggle('open');
  }
  function stopLive() {
    if (liveOff) { liveOff(); liveOff = null; }
    if (window.LiveK) window.LiveK.detach();
  }

  /* 「使用者明確要看族群總覽」的哨兵（網址 `#industry/<chain>/overview`）。
     放在 state.dg 裡，因為 state.dg 就是「這一頁要畫哪一張圖」的唯一來源。*/
  const DG_OVERVIEW = '__overview__';
  // ================================================================ 路由
  async function route(head, rest) {
    A = window.App;
    dispose3D();   // 換頁一定要收掉 WebGL context（瀏覽器最多只給十幾個，不收會整個掛掉）
    gpStopLive();  // 族群總覽的即時輪詢同理：不收的話背景會一直打報價端點、對著離開 DOM 的容器畫圖
    if (head !== 'stock') stopLive();   // 離開個股頁就不要再每 5 秒抓報價了
    const [im, sc, gd] = await Promise.all([A.load('industry_map'), A.load('supply_chain'), A.load('groups_detail')]);
    if (head === 'stock') { state.level = 2; state.code = rest[0]; state.dg = null; await renderStock(rest[0], im, sc, gd); return; }
    if (rest[0] === 'group' && rest[1]) { state.group = rest[1]; state.dg = null; state.chain = chainOfGroup(im, rest[1]); state.level = 1; renderChain(im, sc, gd); return; }
    if (rest[0]) {
      state.chain = rest[0]; state.group = null; state.dg = null; state.level = 1;
      /* ★ 2026-09-21（Andy：「不能一般電子點進去後就是 MLCC…則需要獨立分頁」）
         `#industry/<chain>/dg/<slotId>` ＝ 每一張產品剖析圖自己的網址。
         沒有自己的網址就不叫分頁：不能分享、不能回上一頁、重新整理就掉回去。
         路由沿用 app.js 那一套（hash 切 '/'、每段 decodeURIComponent 過才進來），
         沒有第二套機制。'dg' 這個字不可能撞到環節 id（環節 id 全都是
         supply_chain.yaml 裡的具名字串，例如 passive_comp／abf_pcb）。
         ⚠ 一定要驗「這張圖真的掛在這條鏈上」—— 有人手打 #industry/semiconductor/dg/mlcc
         就會在半導體鏈上畫出 MLCC，那正是這次要修掉的錯。驗不過就當作沒指定（回選單）。*/
      /* ★ 2026-09-23 第二批（Andy：「點擊 AI 伺服器進去就直接看到第一個族群的 2D 圖 3D 圖」）
         `#industry/<chain>` 的 Default 從「族群總覽」換成**這條鏈的第一張剖析圖**，
         族群總覽本身沒有被刪，只是搬去自己的網址 `#industry/<chain>/overview`
         （分頁列的位置不動，它仍然是第一個分頁）。
         用一個哨兵值而不是 boolean：state.dg 本來就是「這一頁要畫哪一張圖」的唯一來源，
         多開一個旗標會出現兩份真相。哨兵不可能撞到真的 slot id（DS.has 一定回 false）。*/
      if (rest[1] === 'overview') { state.dg = DG_OVERVIEW; renderChain(im, sc, gd); return; }
      if (rest[1] === 'dg') {
        const want = rest[2] || '';
        if (DS && DS.has(want) && DS.chainOf(want) === rest[0]) {
          state.dg = want;
          /* 族群層級的 slot，它的 id 就是族群 id（見 diagrams.js 的 SLOTS）。
             一併把族群選起來，整頁（關聯圖、環節詳情）才真的是「這個產品的分頁」，
             而不是「一張圖浮在整條鏈的資料上」。*/
          if (DS.level(want) === 'group') state.group = want;
        }
        renderChain(im, sc, gd); return;
      }
      renderChain(im, sc, gd, { seg: rest[1] || null }); return;
    }
    state.level = 0; state.chain = null; state.group = null; state.dg = null; renderMap(im);
  }
  function chainOfGroup(im, gid) {
    if (!im) return null;
    if (gid.startsWith('ind_')) return 'industry';
    for (const c of im.chains) if (c.groups.some(g => g.id === gid)) return c.id;
    return null;
  }
  function crumbs(items) { $('#indCrumbs').innerHTML = items.map((it, i) => it.href ? `<a onclick="location.hash='${it.href}'">${it.label}</a>${i < items.length - 1 ? '›' : ''}` : `<span class="cur">${it.label}</span>`).join(' '); }
  /* Andy 2026-09-20：「當點擊個股時 最新出現的是K線圖、多週期判對、總攬、營收…公告/新聞，
     下方才是 產業地圖等資訊」。
     index.html 的順序寫死是 #indMap → #indChain → #stockPage，所以個股頁第一眼看到的
     是產業鏈那條 strip，K 線要捲一段才看得到。這裡用 DOM 搬移換順序（不動 index.html，
     因為 #industry 與 #industry/<chain> 兩頁仍然要「產業鏈在上」）：
       個股頁 → #indChain 搬到 #stockPage 後面；離開個股頁 → 搬回去。
     搬的是 #indChain 而不是 #stockPage —— K 線（lightweight-charts）掛在 #stockPage 裡，
     把它從 DOM 拔起來再插回去會讓圖表容器重新量一次尺寸，最糟的情況是高度變 0。
     而且 show() 一律在寫 innerHTML **之前**呼叫，所以搬的當下兩邊都還是空的。 */
  function show(map, chain, stock) {
    /* 舊版「成分股放寬」留在 <body> 上的 `.memwide` 只清 class ——
       2026-09-28 起事件是預設關著的浮層抽屜，不再需要「換頁把事件欄還回來」（那會變成換頁就彈出抽屜）。*/
    document.body.classList.remove('memwide');
    const mp = $('#indMap'), cn = $('#indChain'), st = $('#stockPage');
    mp.style.display = map ? '' : 'none'; cn.style.display = chain ? '' : 'none'; st.style.display = stock ? '' : 'none';
    const par = st.parentNode; if (!par) return;
    // 用文件位置判斷，不要假設兩者一定相鄰（將來中間插一塊就會安靜地失效）
    const chainBeforeStock = !!(cn.compareDocumentPosition(st) & Node.DOCUMENT_POSITION_FOLLOWING);
    if (stock) { if (chainBeforeStock) par.insertBefore(cn, st.nextSibling); cn.style.marginTop = 'var(--gap-card)'; }
    else { if (!chainBeforeStock) par.insertBefore(cn, st); cn.style.marginTop = ''; }
  }

  // ================================================================ 產業熱力圖（自己的頂層分頁）
  /* Andy 2026-09-23：「圖五 產業熱力圖需要獨立一個大分頁，而當前分頁改成產業地圖
     就是放他所點進去後的畫面」。所以這張 treemap 從 #industry 搬到 #heatmap 這個頂層分頁，
     #industry 改成「族群漲幅長條圖＋占比圓餅圖」（見 renderMap）。
     ⚠ treemap 仍然叫 #indTree（縮放白名單、淺色主題掃描都認這個 id），但它現在只住在
       #indHeat 裡 —— #indMap 那邊不准再畫第二份，不然同一個 id 出現兩次，
       getElementById 只拿得到前面那一個，縮放與主題掃描就會量到看不見的那一張。*/
  /* ★ 2026-09-24 熱力圖 v2（docs/design_system_v2.md §3.1）：7 格離散色階＋圖例、2px 間隙（鏈之間 6px）、
     圓角 3、標籤分三級、半透明提示框。標題列多兩樣：
       「分組」下拉 —— 產業鏈（原本的畫法）｜不分組（平鋪一層，一眼比大小）。**新選項，不取代舊的**。
       日期膠囊 —— 這份資料的交易日，只顯示、不能改。
     共用的工具（hmBin／hmItem／hmSeries／hmLegend／hmRelabel／hmTip）在 app.js，三張熱力圖同一套。*/
  let heatGroup = null, heatFocusT = null;
  function renderHeat(im) {
    const el = document.getElementById('indHeat');
    if (!el) return;
    if (!im || !im.chains) { el.innerHTML = '<div class="empty">尚無產業資料</div>'; return; }
    if (heatGroup === null) heatGroup = A.hmLS('tw.hmGroup', 'chain') === 'flat' ? 'flat' : 'chain';
    disposeCharts(el);
    /* ★ 2026-09-24 說明精簡（Andy：「已經有說明就把表上補充文字拿掉」）：
       原本標題下那段「這張圖回答／怎麼用」搬進「怎麼看 ?」，卡片只留一行短副標。*/
    el.innerHTML = `<div class="card"><div class="row spread"><h3>整個台股一次看 <button class="howbtn pop" data-how="indheat" type="button" aria-label="整個台股一次看怎麼看">?</button></h3>
      <div class="row" style="gap:8px"><label class="hmctl" title="方塊要不要依產業鏈分組">分組：<select id="indTreeGroup" aria-label="熱力圖分組方式">
        <option value="chain"${heatGroup === 'chain' ? ' selected' : ''}>產業鏈</option><option value="flat"${heatGroup === 'flat' ? ' selected' : ''}>不分組</option></select></label></div></div>
      <div class="howtxt" id="how-indheat" hidden>${A.howHTML('今天全市場的錢分佈在哪幾塊、哪一塊在漲。', [
        '方塊大小＝族群成交值（分組時小鏈至少佔 5%）',
        '顏色＝今日漲跌，紅漲綠跌',
        '又大又紅＝錢多而且在漲；大而綠＝權值區退潮',
      ], '要比同一條鏈裡誰漲誰跌，用<a class="lk" href="#industry">產業地圖</a>的長條圖比較快；右上「分組」可以改成不分組平鋪，一眼比大小。')}</div>
      <div class="zwrap" id="indTreeWrap"><div id="indTree" class="chart" style="min-height:560px"></div></div></div>`;
    const gsel = document.getElementById('indTreeGroup');
    if (gsel) gsel.onchange = () => { heatGroup = gsel.value; A.hmLSset('tw.hmGroup', heatGroup); renderHeat(im); };
    /* ★ 2026-09-24（審查 R4）：產業鏈模式下，傳產／金融／基礎建設／軟體四條鏈的成交值加起來不到 5%，
       被擠在最右一條窄欄，鏈小標截成「傳產與…」、方塊截成「石化…」「基礎建…」這種殘字，很多塊乾脆沒字。
       做法：分組時每條鏈的**面積**至少佔全圖 CHAIN_MIN（鏈內各族群等比放大），名字才放得下；
       真實成交值另存在 `to`，提示框一律讀它，「怎麼看」也寫明這件事 —— 面積失真要講清楚，不能偷偷做。
       不分組模式照原本的成交值，不做任何放大（那是「一眼比大小」的模式）。*/
    const CHAIN_MIN = 0.05;
    const nested0 = heatGroup !== 'flat';
    const allTo = im.chains.reduce((s, c) => s + c.groups.reduce((t, g) => t + (g.turnover || 0), 0), 0) || 1;
    const chainK = {};
    im.chains.forEach(c => {
      const t = c.groups.reduce((s2, g) => s2 + (g.turnover || 0), 0);
      chainK[c.id] = nested0 && t > 0 ? Math.max(1, (allTo * CHAIN_MIN) / t) : 1;
    });
    const leaf = (c, g) => ({ name: g.name, value: (g.turnover || 1) * (chainK[c.id] || 1), to: g.turnover, gid: g.id, chg: g.chg_pct, share: g.turnover_share, chain: c.name,
      pe: g.valuation && g.valuation.median, n: g.n, ...A.hmItem(A.hmBin(g.chg_pct, 'chg'), 'chg', heatFocusT) });
    const nested = heatGroup !== 'flat';
    const data = nested
      ? im.chains.map(c => ({ name: c.name, cid: c.id, itemStyle: { color: A.CH.hmNa }, children: c.groups.map(g => leaf(c, g)) }))
      : [].concat(...im.chains.map(c => c.groups.map(g => leaf(c, g))));
    const HS = A.hmSeries(nested, 22);
    const valOf = (d) => (d && d.gid ? A.fmt.pct(d.chg) : '');
    const c = A.chart('indTree', { tooltip: { ...A.hmTipOpt(), formatter: p => { const d = p.data || {};
        if (!d.gid) return A.hmTip(p.name, '', [], '');
        return A.hmTip(p.name, d.chain, [
          { k: '漲跌幅', v: A.fmt.pct(d.chg, 2), c: A.upDown(d.chg), dot: A.hmColor(A.hmBin(d.chg, 'chg'), 'chg') },
          { k: '成交值', v: `${A.fmt.yi(d.to != null ? d.to : p.value)}（${A.fmt.n(d.share, 1)}%）` },
          { k: '成分股', v: `${d.n != null ? d.n : '—'} 檔` },
          { k: '本益比中位', v: d.pe != null ? A.fmt.n(d.pe, 1) : '—' },
        ], ''); } },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, top: 0, left: 0, width: '100%', height: '100%',
        leafDepth: nested ? 2 : 1, visibleMin: 900,
        ...HS, label: { ...HS.label, formatter: () => '' }, data }] }, { notMerge: true });
    A.hmRelabel(c, valOf);
    A.hmLegend('indTree', 'chg', heatFocusT, (f) => { heatFocusT = f; renderHeat(im); });
    A.wheelZoom(document.getElementById('indTreeWrap'), { onZoom: () => { const i = window.echarts && echarts.getInstanceByDom(document.getElementById('indTree')); if (i) i.resize(); } });
    // 放大狀態下單擊延後判定，雙擊（還原）不會被當成點方塊而跳頁（審查 R4，見 app.js wheelZoom 的 defer）
    if (c) c.off('click').on('click', p => A.zoomClick(document.getElementById('indTreeWrap'), () => {
      // 手機 v3（≤640px）：沒有 hover，小方塊的字又被截掉 —— 先開抽屜給全名與數字，「族群 ›」再進去（桌機照舊直接進族群頁）
      if (p.data && p.data.gid && window.M3 && window.M3.isM()) { window.M3.tileSheet(p.data); return; }
      if (p.data.gid) location.hash = '#industry/group/' + p.data.gid; else if (p.data.cid) location.hash = '#industry/' + p.data.cid; else if (p.treePathInfo && p.treePathInfo[1]) { const cid = (im.chains.find(x => x.name === p.treePathInfo[1].name) || {}).id; if (cid) location.hash = '#industry/' + cid; } }));
  }

  // ================================================================ 活頁簿分頁（第一層：產業鏈）
  /* Andy 2026-09-23：「上面的族群都改成分頁式可作切換，像是 EXCEL 活頁簿那樣，但是位置在上方」。
     第一個分頁是「全市場」（＝#industry 本身），後面每一條鏈一頁，最後是法定產業別。
     ⚠ 法定產業別這一頁**不准拿掉** —— 35 個法定產業別只有從這裡進得去
       （2026-09-19 修過一次的舊 bug，那時卡片還在，現在卡片移除了，這一頁就是唯一入口）。
     id 沿用 `chainSwitch`：產業地圖與產業鏈頁各畫一份，但兩者互斥
     （renderMap 會清掉 #indChain、renderChain 會清掉 #indMap），所以同一時間只有一個。*/
  function chainTabsHtml(im, cur) {
    const tabs = [{ id: '_all', name: '全市場', n: (im.chains || []).reduce((s, c) => s + c.groups.reduce((t, g) => t + (g.n || 0), 0), 0) }]
      .concat((im.chains || []).map(c => ({ id: c.id, name: c.name, n: c.groups.reduce((s, g) => s + (g.n || 0), 0) })))
      .concat([{ id: 'industry', name: '法定產業別', n: (im.industries || []).reduce((s, g) => s + (g.n || 0), 0) }]);
    return `<div class="chainsw nbsw" id="chainSwitch" role="tablist">${tabs.map(t => `<button data-c="${t.id}" role="tab" aria-selected="${t.id === cur}" class="${t.id === cur ? 'on' : ''}"${t.id !== '_all' && HAS_DIAGRAM(t.id) ? ' data-dg="1"' : ''}>${A.fmt.esc(t.name)}<em>${t.n}</em></button>`).join('')}</div>`;
  }
  /* 分頁列放不下時左右捲，但**選中的那一頁一定要在視野裡** ——
     捲的是分頁列自己（不是 scrollIntoView，那會連整頁一起捲，使用者的位置就跑掉了）。*/
  /* ★ 2026-09-25 效能（perf-2）：改到下一幀開頭才量。
     這支讀 scrollWidth／clientWidth／offsetLeft —— 在 renderChain 的中途讀，等於逼瀏覽器把還沒排好的整頁**當場排版**，
     之後 render 又改一大堆 DOM、再排一次。實測首次開 #industry/semiconductor 光這支就 210ms（整個任務 778ms 的 27%）。
     rAF 在畫面畫出來之前跑，捲的結果一樣、看不出差別；同一條分頁列一幀內叫幾次都只量一次。*/
  /* ★ 2026-09-25 效能（perf-2）：首屏以下的區塊延後畫 —— 捲近了（IntersectionObserver，提前 240px）或瀏覽器閒下來
     （requestIdleCallback，最慢 2.5 秒）先到的那一個觸發，只跑一次。跟 app.js 的 whenNear 同一個概念，
     但**不先量位置**（呼叫端自己知道它在首屏以下），所以不會在畫頁途中逼整頁排版。*/
  function deferNear(el, fn) {
    let done = false, io = null;
    const go = () => { if (done) return; done = true; if (io) io.disconnect(); try { fn(); } catch (e) { console.warn('延後畫的區塊失敗', e); } };
    if (window.IntersectionObserver) {
      io = new IntersectionObserver((es) => { if (es.some(e => e.isIntersecting)) go(); }, { rootMargin: '240px 0px' });
      io.observe(el);
    }
    const ric = window.requestIdleCallback || ((f) => setTimeout(f, 120));
    ric(go, { timeout: 2500 });
  }
  function scrollTabIntoView(strip) {
    if (!strip || strip._tabQ) return;
    strip._tabQ = true;
    requestAnimationFrame(() => {
      strip._tabQ = false;
      if (!strip.isConnected) return;
      const on = strip.querySelector('.on');
      if (!on || strip.scrollWidth <= strip.clientWidth + 2) return;
      strip.scrollLeft = Math.max(0, on.offsetLeft - (strip.clientWidth - on.offsetWidth) / 2);
    });
  }
  function wireChainTabs(root, cur) {
    const strip = $('#chainSwitch', root);
    if (!strip) return;
    $$('#chainSwitch button', root).forEach(b => b.onclick = () => {
      const id = b.dataset.c;
      if (id === cur) { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
      location.hash = id === '_all' ? '#industry' : '#industry/' + id;
    });
    scrollTabIntoView(strip);
  }

  // ================================================================ Level 0：產業地圖（族群總覽）
  function renderMap(im) {
    /* ★ 2026-09-23：Andy「將產業地圖移到分頁名稱上」。
       分頁本身已經叫「產業地圖」了，底下再寫一次同樣四個字是重複的，
       而且它佔掉一整列。所以**第 0 層不畫麵包屑**。
       ⚠ 更深的層級照舊要畫（產業地圖 › 半導體 › 台積電），那是導覽不是標題。 */
    show(true, false, false); crumbs([]);
    /* 產業鏈頁的內容留在 DOM 裡的話，`#chainSwitch`／`#gpBar` 這些 id 會同時出現兩份
       （一份看得見、一份被 display:none 藏著），getElementById 只拿得到前面那個 ——
       畫面上按的是後面那個，程式改的卻是前面那個。所以換層級一定要把另一邊清掉。*/
    const cn = $('#indChain'); if (cn) { disposeCharts(cn); cn.innerHTML = ''; }
    const el = $('#indMap');
    disposeCharts(el);
    if (!im || !im.chains) { el.innerHTML = '<div class="empty">尚無產業資料</div>'; return; }
    const groups = [];
    (im.chains || []).forEach(c => (c.groups || []).forEach(g => groups.push(g)));
    /* 活頁簿：分頁列在**卡片外面**、卡片就是那一頁的內容 ——
       分頁列放在卡片裡面的話，上面還壓著一層卡片的內距與邊框，看起來就只是「卡片裡的一排鈕」，
       不是 Excel 那種「分頁貼著內容上緣、連成一片」。產業鏈頁用的是同一套（見 renderChain）。*/
    el.innerHTML = `${chainTabsHtml(im, '_all')}<div class="card nbcard" id="gpHost"></div>`;
    wireChainTabs(el, '_all');
    renderGroupPanel($('#gpHost', el), {
      scope: '全市場', groups: groups, asOf: (im && im.date) || '',
      tail: '<span class="muted">完整版圖：</span><a class="lk" href="#heatmap">產業熱力圖 →</a>',
    });
  }
  /* ================================================================ 族群總覽：長條圖 ＋ 圓餅圖
     Andy 2026-09-23：「產業地圖 以及 產業地圖裡面的族群如半導體，Default 是各族群漲幅的長條圖
     以及占比圓餅圖（圓餅圖在右邊顯示），並且就顯示第一分頁，
     長條圖內的族群點進去後 會再出現族群對應所有個股漲幅長條圖」。

     **這張圖回答**：這一塊（全市場或這一條鏈）今天誰在漲、錢集中在誰身上。
     兩張圖是一組的，缺一張都答不完：長條只講方向（誰漲）、圓餅只講份量（誰的量大），
     真正要找的是**兩邊都在前面**的那一個。所以兩張圖連動、共用一行讀數（#gpFocus）——
     滑到哪一條，另一邊就標起來，讀數列同時把「漲多少、占多少、幾檔」講完。

     為什麼點長條是「原地換內容」不是跳頁：使用者的問題是「這個族群裡面是誰在漲」，
     那是同一個問題的下一層，跳頁會把他剛剛比較出來的上下文丟掉（也回不去原來的捲動位置）。 */
  const GP_TOP = 18;             // 族群層級最多列幾條（超過的併進圓餅的「其餘」，長條不列）
  const GP_TOP_STOCK = 24;       // 個股層級最多列幾條
  const GP_LIVE_MS = 5 * 1000;   // ★ 2026-09-29：60 秒 → 5 秒（和 live.js 盤中節奏一致；最多 3 個請求一輪，排節流閥、輪完才接下一輪）
  const GP_LIVE_MAX = 300;       // 即時一輪最多問幾檔（live.js 一批 110，這裡切 100 × 3 個請求）
  const GP_LIVE_BATCH = 100;
  /* gpTimer／gpGen 是模組層級的：同一時間畫面上只會有一個族群總覽，
     換頁或重畫一定要先把上一個的計時器停掉，不然背景會一直打即時端點
     （而且舊 panel 的 paint 會對著已經離開 DOM 的容器畫圖）。
     gpGen 是「世代」：非同步的報價回來時先比對世代，過期的就整輪丟掉。*/
  let gpTimer = null, gpGen = 0;
  function gpStopLive() { gpGen++; if (gpTimer) { clearInterval(gpTimer); gpTimer = null; } }
  // 驗收用：現在的族群總覽是什麼狀態（真人操作驗收要量「畫面真的變了」）
  let gpDbg = { mode: 'group', rows: 0, live: false, hi: null, liveCalls: 0, drill: null };

  function renderGroupPanel(host, ctx) {
    if (!host) return null;
    gpStopLive();
    const gen = gpGen;
    const all = (ctx.groups || []).filter(g => g && (g.turnover || 0) > 0);
    const byTurn = (a, b) => (b.turnover || 0) - (a.turnover || 0);
    if (!all.length) { host.innerHTML = '<div class="empty">這一塊今天沒有成交資料</div>'; return null; }

    /* 從網址（#industry/group/<gid>）或關聯圖帶進來的族群，一進來就展開它的個股長條圖 ——
       使用者明確指定了一個族群，先給他看「這個族群裡面誰在漲」才是他要的那一步。*/
    let drill = ctx.drillGid ? (all.find(g => g.id === ctx.drillGid) || null) : null;
    let live = false, q = null, liveErr = '', liveAt = '', busy = false, cov = [0, 0];
    let gpOkAt = 0;                   // 最後一次真的拿到報價的時間（卡上印「最後更新 HH:MM:SS」）
    let hi = null;                    // 兩圖連動：滑鼠現在停在哪一條／哪一塊
    let barData = [], pieData = [], items = [];
    /* ★ W3-8：圓餅只標前五大，其餘併成一塊灰色的「其他」。
       `pieTopNames` 是「哪幾個族群有自己的扇形」——兩圖連動要靠它把落在「其他」裡的
       那些族群對應回灰色那一塊（不然滑過去會變成沒反應）。*/
    const PIE_TOP = 5;
    const PIE_OTHER = '其他';
    let pieTopNames = [], pieTopShare = 0, pieOtherN = 0;
    /* ★ 2026-10-06 Andy：「圖表資訊需要在右手邊，這樣圓餅圖才不會被壓縮」＋「其他圓餅圖也一樣」。
       改前：圖例在圖下方兩欄，甜甜圈的高＝長條高 − 圖例高 —— 族群少的鏈（長條只有 320 高）甜甜圈被擠到約 184px，
       而且名稱與數字隔一整張卡寬。改後：甜甜圈在左、圖例一列一項在右（色塊｜名稱｜成交值｜占比），
       甜甜圈是正方形，邊長＝「卡片扣掉圖例後的寬」與「卡片可用高」取小（兩欄並排時可用高＝長條高，所以會跟卡高一起放大）。
       卡寬（含框）< 420 才退回「圖例在下」——那時右邊放不下圖例又留得下 160 的圓。
       ⚠ 甜甜圈邊長下限 160（＝ --chart-donut）：右邊放圖例後若剩不到 160，就讓圖例的名稱欄縮（省略＋滑過看全名），
         數字欄永遠不縮。 */
    const DN_MIN = 160, DN_SIDE_MIN = 420, DN_GAP = 16, DN_GAP_V = 8, DN_CAP1 = 340;
    const DN_R_IN = A.donut.R_IN, DN_R_OUT = A.donut.R_OUT;   // 環：內 68%、外 92%（★ 2026-10-06 起從共用風格 A.donut 取，DECISIONS #331；容器剛好包住圓）
    let dnS = 0, dnBarH = 0;             // 甜甜圈邊長、長條圖高（layoutDonut 的輸入）

    /* 標題列只放「標題 ＋ 兩顆鈕」，說明另起一行 ——
       說明擺在同一列的話，長文字會把左邊那一格撐滿，右邊的「即時」被擠到下一行去，
       看起來像一顆浮在半空中、不知道在管什麼的鈕（1440／390 都量到）。*/
    host.innerHTML = `<div class="row spread gphead">
        <h4 id="gpTitle" style="min-width:0"></h4>
        <div class="row gplive">
          <button class="btn small" id="gpBack" type="button" hidden title="回到族群層級的長條圖">← 回到族群</button>
          <span class="rbar" data-live-ui><button class="pb livebtn" id="gpLiveBtn" type="button" aria-pressed="false"
            title="切到盤中即時：用當下的成交價與累積成交量重算漲跌與占比，每 5 秒更新（盤中暫定值）">即時</button></span>
        </div>
      </div>
      <!-- ★ 2026-09-24 說明精簡：#gpHint（這張圖回答／怎麼用）與即時的估算口徑搬進「怎麼看 ?」；
           #gpNote 2026-10-06 起盤後不顯示；即時只寫「成交值估算・涵蓋 N / M 檔」（DECISIONS #329，取代 #252 三「寫出昨天收盤／盤中暫定值」那半句）。 -->
      <div class="howtxt" id="how-gp" hidden><div id="gpHint"></div></div>
      <div class="note livenote gpnote" id="gpNote" hidden></div>
      <!-- ★ 2026-09-23（W3-8，Andy：「看起來太乾澀了」）：兩張圖各自裝進一張有標題的卡片。
           以前兩張圖裸放在同一片背景上、中間沒有分界 —— 沒有容器，圖就像貼在牆上，
           而且「左邊在講什麼、右邊在講什麼」要靠讀說明才知道。標題直接寫在各自的卡片上。 -->
      <!-- ★ 2026-10-06 Andy：「圖表資訊需要在右手邊，這樣圓餅圖才不會被壓縮」—— 甜甜圈與圖例包成一個 .gpdonut：
           預設圖左、圖例右（一列一項）；卡寬 < 420 由 layoutDonut 切成 .dnbelow（圖例退回圖下方）。 -->
      <div class="gpgrid">
        <div class="gpcard"><h5>族群漲跌幅</h5><div id="gpBar" class="chart"></div></div>
        <div class="gpcard gppie"><h5>成交值占比</h5>
          <div class="gpdonut"><div id="gpPie" class="chart"></div>
          <div class="gplegend" id="gpLegend" aria-label="圖例"></div></div></div>
      </div>
      <div class="sub" id="gpFocus" style="margin-top:8px"></div>
      ${ctx.tail ? `<div class="linkrow gptail">${ctx.tail}</div>` : ''}`;

    const barEl = $('#gpBar', host), pieEl = $('#gpPie', host), noteEl = $('#gpNote', host);
    /* ★ 設計 v4 第二批 2B（docs/design_v4/04_第二批2B.md §0 ⑧）：桌機（≥641）三行各佔一整列的東西收進既有的列裡：
         · #gpNote（「昨天（盤後收盤）資料日期…」／「⚡ 盤中暫定值…」）→ 標題列（標題右邊、「即時」左邊），省一整列 ≈ 42px
         · #gpFocus（滑過讀數，沒滑過時是一行空白佔位）→ 「族群漲跌幅」卡片標題列的右半邊（那一列右邊本來就空著，
           高度固定、單行、放不下省略 —— 滑過時版面照樣不跳），圖下方那條空白列不見了 ≈ 32px
         · 「完整版圖：產業熱力圖 →」（產業地圖那一層才有）→ 標題列「即時」左邊，圖下方那一整列（含虛線）不見了 ≈ 40px
       只搬位置，元素、id、內容、行為都不變（寫入的程式碼照 id 找）。手機（≤640）維持改前的順序：
       視窗跨過 640 時 matchMedia 來回搬；這個族群總覽被重畫（元素離開 DOM）就把監聽拿掉。*/
    {
      const mq = window.matchMedia ? window.matchMedia('(min-width:641px)') : null;
      const head = $('.gphead', host), live = head && $('.gplive', head), grid = $('.gpgrid', host);
      const foc = $('#gpFocus', host), tail = $('.gptail', host), barCard = barEl.parentElement;
      const place = () => {
        if (!noteEl.isConnected) { if (mq) { try { mq.removeEventListener('change', place); } catch (e) { /* 舊瀏覽器 */ } } return; }
        const desk = !mq || mq.matches;
        host.classList.toggle('gpdesk', desk);
        if (desk) {
          head.insertBefore(noteEl, live);
          if (tail) head.insertBefore(tail, live);
          barCard.insertBefore(foc, barEl);
        } else {
          grid.before(noteEl);
          grid.after(foc);
          if (tail) foc.after(tail);
        }
      };
      if (head && live && grid && foc && barCard) {
        place();
        if (mq) { try { mq.addEventListener('change', place); } catch (e) { /* 舊瀏覽器：照初始位置 */ } }
      }
    }
    const backBtn = $('#gpBack', host), liveBtn = $('#gpLiveBtn', host);
    const CH = A.CH;

    // ---------------------------------------------------------------- 即時
    /* 即時的成交值是**估**的：mis 那支端點沒有每檔的累積成交金額，只有最新價與累積張數，
       所以用「最新價 × 累積張數 × 1000」當成交值（和輪動時鐘的即時同一個口徑，
       見 app.js rlvCompute 的誠實界線 ①）。這件事一定要寫在畫面上。*/
    const liveAgg = (members) => {
      if (!q || !members) return null;
      let v = 0, c = 0, n = 0;
      members.forEach(m => {
        const x = q[String(m.code)];
        if (!x || x.price == null || x.volume == null || x.chgPct == null) return;
        const amt = x.price * x.volume * 1000;
        if (!(amt > 0)) return;
        v += amt; c += x.chgPct * amt; n++;
      });
      return n ? { val: v, chg: c / v, n } : null;
    };
    const shownGroups = () => all.slice().sort(byTurn).slice(0, GP_TOP);
    const liveCodes = () => {
      const out = [], seen = new Set();
      const push = (c) => { c = String(c || ''); if (c && !seen.has(c) && out.length < GP_LIVE_MAX) { seen.add(c); out.push(c); } };
      if (drill) (drill.members || []).slice().sort(byTurn).forEach(m => push(m.code));
      else {
        const gs = shownGroups();
        // 平均分配額度：不分配的話前面幾個大族群就把 300 檔吃光，後面整排都沒有即時值
        const per = Math.max(3, Math.floor(GP_LIVE_MAX / Math.max(1, gs.length)));
        gs.forEach(g => (g.members || []).slice().sort(byTurn).slice(0, per).forEach(m => push(m.code)));
      }
      return out;
    };
    async function liveTick() {
      if (busy) return;
      // ★ 2026-09-29：計時器 5 秒一跳；盤後只在還沒抓過／超過 30 分鐘才真的抓（Live.due）
      if (window.Live && window.Live.due && !window.Live.due(gpOkAt)) return;
      if (window.Live && window.Live.cooling && window.Live.cooling('gp')) return;   // 上一輪失敗 → 退避中（10、20、40…秒）
      busy = true; paintNote();
      const t0 = Date.now();
      try {
        if (!window.Live || !window.Live.fetchQuotes) throw new Error('即時報價載入失敗');
        const codes = liveCodes();
        if (!codes.length) throw new Error('尚無成分股名單');
        const got = {};
        for (let i = 0; i < codes.length; i += GP_LIVE_BATCH) {
          Object.assign(got, await window.Live.fetchQuotes(codes.slice(i, i + GP_LIVE_BATCH)));
        }
        if (gen !== gpGen) return;          // 回來的時候使用者已經換頁了，這一輪整個丟掉
        q = got; liveErr = ''; gpOkAt = Date.now();
        liveAt = Object.keys(got).map(k => got[k] && got[k].time).filter(Boolean).sort().pop() || '';
        const ks = Object.keys(got).filter(k => got[k] && got[k].price != null);
        cov = [ks.length, codes.length];
        if (window.Live && window.Live.report) window.Live.report('gp', true);
      } catch (e) {
        if (window.Live && window.Live.report) window.Live.report('gp', false, t0);
        if (gen !== gpGen) return;
        liveErr = String((e && e.message) || e).slice(0, 80); q = null; cov = [0, 0];
        // 第二道：萬一哪條路漏掉 live.js 的轉譯，英文的網路錯誤仍然不准原樣上畫面（R3 審查）
        if (/failed to fetch|networkerror|load failed/i.test(liveErr)) liveErr = '連不到報價來源';
      } finally {
        busy = false;
        if (gen === gpGen) paint();
      }
    }
    /* ★ 「綁之前先解綁」（規格書第三節，坑在 app.js 第 445 行）：
       A.onLive 對同一個元素只會真的掛一次事件（旗標 + WeakMap 覆蓋 closure），
       所以這裡**只在建立面板時掛一次**，切換即時開關不再掛第二次 ——
       每按一次就掛一個的話，監聽器會 1→2→4→8 指數成長。
       計時器同理：開之前一律先 clearInterval。*/
    A.onLive(host, () => {
      gpDbg.liveCalls++;
      if (!live || !host.isConnected) return;
      // live.js 自己那一輪（畫面上看得到的代號）也會更新報價，順手併進來一起用
      const got = (window.Live && window.Live.quotes) || null;
      if (!got) return;
      q = Object.assign({}, q || {}, got);
      paint();
    });
    const stopTimer = () => { if (gpTimer) { clearInterval(gpTimer); gpTimer = null; } };
    liveBtn.onclick = () => {
      if (!live && !liveOK()) return;   // 不是管理者：即時打不開（鈕本來就藏著，這裡是第二道，DECISIONS #326）
      live = !live;
      liveBtn.classList.toggle('on', live);
      liveBtn.setAttribute('aria-pressed', live ? 'true' : 'false');
      stopTimer();                      // 先停再開，計時器永遠只有一個
      if (!live) { q = null; liveErr = ''; cov = [0, 0]; paint(); return; }
      paint();                          // 先把「抓取中」寫上去，不要讓畫面看起來沒反應
      if (window.Live && window.Live.report) window.Live.report('gp', true);   // 重新打開：清掉上次的退避
      liveTick();
      gpTimer = setInterval(() => { if (!document.hidden && live) liveTick(); }, GP_LIVE_MS);
    };
    backBtn.onclick = () => {
      drill = null; hi = null;
      if (live) { q = null; liveTick(); }
      keepPlace(paint);
      if (ctx.onBack) ctx.onBack();
    };
    /* ★ 2026-09-26 晚（Andy：「點擊後出現位置跑掉，請處理」——全市場分頁點「族群漲跌幅」長條進到某族群個股之後，
       整頁往左偏、左邊被切掉，標題只剩半截、分頁「全市場」的「全」不見）。
       本機四種寬度（1440／1100／800／390）、開關事件抽屜、顯示真捲軸、盤中即時開關都重現不出 scrollX≠0，
       所以不押寶在單一機制上，改成「換層級前後由這支把位置顧好」—— 不管是誰把頁面往旁邊帶，這裡都會拉回來：
         ① 水平：整頁（window）與這塊的每一層祖先裡，**使用者本來就捲不動**（overflow-x hidden／clip）卻被捲了的，
            scrollLeft 一律歸零。≤820px 時 body 是 overflow-x:hidden，會傳給整個視窗 —— 那種被程式捲走的頁面
            沒有捲軸可以拉回來，就是「左邊被切掉而且回不來」的樣子。使用者自己能捲的框（overflow:auto）不動。
         ② 垂直：個股層級的長條比族群層級矮（18 條 → 5 條），頁面一變短，瀏覽器會把捲動位置往上夾，
            原本看得到的標題列（「← 回到族群」就在上面）可能被夾到頂欄底下。只有「點之前看得到、點之後被蓋住」時才補捲回原位。
         ECharts 的 resize 在下一幀才發生（ResizeObserver），所以下一幀再檢查一次水平。*/
    function keepPlace(fn) {
      const head = host.querySelector('.gphead');
      const t0 = head ? head.getBoundingClientRect().top : null;
      fn();
      const fixX = () => {
        if (window.scrollX) window.scrollTo({ left: 0, top: window.scrollY, behavior: 'instant' });
        for (let a = host.parentElement; a; a = a.parentElement) {
          if (!a.scrollLeft) continue;
          const ox = getComputedStyle(a).overflowX;
          if (ox === 'hidden' || ox === 'clip' || ox === 'visible' || a === document.body || a === document.documentElement) a.scrollLeft = 0;
        }
      };
      fixX();
      if (head && t0 != null) {
        const t1 = head.getBoundingClientRect().top;
        if (t0 >= 64 && t1 < 64) window.scrollBy({ top: t1 - t0, behavior: 'instant' });
      }
      requestAnimationFrame(fixX);
    }

    // ---------------------------------------------------------------- 資料 → 兩張圖
    function build() {
      if (drill) {
        const ms = (drill.members || []).slice().sort(byTurn).slice(0, GP_TOP_STOCK);
        items = ms.map((m, i) => {
          const x = live && q ? q[String(m.code)] : null;
          const okq = x && x.price != null && x.volume != null && x.chgPct != null && x.price * x.volume > 0;
          return { key: m.code, code: m.code, name: m.name || m.code,
            chg: okq ? x.chgPct : m.chg_pct, val: okq ? x.price * x.volume * 1000 : (m.turnover || 0),
            live: !!okq, color: A.PALETTE[i % A.PALETTE.length], n: null };
        });
      } else {
        const gs = shownGroups();
        items = gs.map(g => {
          const lv = live ? liveAgg(g.members) : null;
          return { key: g.id, gid: g.id, name: g.name,
            chg: lv ? lv.chg : g.chg_pct, val: lv ? lv.val : (g.turnover || 0),
            live: !!lv, color: A.L.gcolor[g.id] || A.PALETTE[0], n: g.n, group: g };
        });
      }
      const restN = drill ? Math.max(0, (drill.members || []).length - items.length)
                          : Math.max(0, all.length - items.length);
      const restVal = drill
        ? (drill.members || []).slice().sort(byTurn).slice(items.length).reduce((s, m) => s + (m.turnover || 0), 0)
        : all.slice().sort(byTurn).slice(items.length).reduce((s, g) => s + (g.turnover || 0), 0);
      const total = items.reduce((s, d) => s + (d.val || 0), 0) + restVal;
      items.forEach(d => { d.share = total > 0 ? d.val / total * 100 : 0; });
      // 長條由高到低（ECharts 的類別軸是由下往上長，所以資料要由低到高餵進去）
      const asc = items.slice().sort((a, b) => (a.chg == null ? -1e9 : a.chg) - (b.chg == null ? -1e9 : b.chg));
      barData = asc.map(d => ({ name: d.name, value: d.chg == null ? 0 : +(+d.chg).toFixed(2), key: d.key,
        /* ★ 2026-09-23（W3-8，Andy：「看起來太乾澀了」＋目標圖）：長條**兩端都做圓角**。
           以前只有末端那一端圓、貼著零軸那一端是直角，目標圖兩端都是圓的。*/
        itemStyle: { color: A.upDown(d.chg), borderRadius: 5, borderWidth: 0, borderColor: CH.ink },
        /* 色票（CH.*）在切主題時由 applyTheme 就地換掉，所以這裡不必自己分深／淺兩套 */
        label: { show: true, position: (d.chg || 0) >= 0 ? 'right' : 'left', fontSize: 12, fontFamily: A.MONO,
          color: CH.ink2, formatter: A.fmt.pct(d.chg) } }));
      /* ★ 2026-09-23（W3-8）：圓餅只標**前五大**，其餘全部併成一塊中性灰的「其他」。
         以前是把十幾塊小碎片全部畫出來、標籤貼在旁邊互相干擾 —— 那張圖回答不了
         「錢集中在誰身上」，因為前三名跟第十三名長得一樣重要。
         併起來之後：五個有名字的區塊各自回答「誰」，灰色那一塊回答「剩下的加起來多少」。*/
      const bySize = items.slice().sort((a, b) => (b.val || 0) - (a.val || 0));
      const top = bySize.slice(0, PIE_TOP);
      // 「其他」＝第六名以後 ＋ 連長條都沒有列出來的那一批（restVal）
      const otherVal = bySize.slice(PIE_TOP).reduce((s2, d) => s2 + Math.max(0, d.val || 0), 0) + restVal;
      const otherN = Math.max(0, bySize.length - top.length) + restN;
      pieTopNames = top.map(d => d.name);
      /* ★ 2026-10-06（圓餅風格1006 驗出來的）：不同族群可能撞同一個顏色（半導體鏈的「封測代工」與「HBM」都是 #7ee8c7），
         甜甜圈上兩塊貼在一起分不出來。同色的後一塊改取共用色盤裡還沒用過的顏色（只動甜甜圈與它的圖例，族群本身的顏色不變）。*/
      const usedC = new Set();
      pieData = top.map((d, i) => {
        let col = d.color;
        if (usedC.has(col)) col = A.donut.colors().find(c => !usedC.has(c) && !top.some(t => t.color === c)) || col;
        usedC.add(col);
        return A.donut.item({ name: d.name, value: Math.max(0, d.val || 0), key: d.key, color: col }, i, false);
      });
      if (otherVal > 0) {
        pieData.push(A.donut.item({ name: PIE_OTHER, value: otherVal, key: '_rest', isOther: true }, top.length, false));
      }
      /* 中心那個數字一定要**真的算**（前五大的占比相加），不准寫死、不准用估的 */
      pieTopShare = total > 0 ? top.reduce((s2, d) => s2 + (d.val || 0), 0) / total * 100 : 0;
      pieOtherN = otherN;
      return { asc, total, restN, restVal };
    }

    function paintNote() {
      /* ★ 2026-09-24 說明精簡：這一行只講「現在是哪一種數字」；估算怎麼算、涵蓋率怎麼讀搬進「怎麼看 ?」。
         ★ 2026-10-06（Andy 圈了「昨天（盤後收盤）資料日期 2026-10-05」：「這類資訊一律拿掉」，DECISIONS #329）：
           · 盤後：整行不顯示（不寫昨天、盤後收盤、資料日期）—— 新鮮度看全站資料狀態徽章與頁首時間。
           · 即時：不寫「⚡ 盤中暫定值」「最後更新 HH:MM:SS」「報價時間」；只留口徑「成交值估算・涵蓋 N / M 檔」
             （那是口徑不是時段：少了它盤中的成交值會被讀成真實值，#252 三的那一半仍成立）。
           · 抓取中／抓不到：狀態訊息照留，但不再寫「仍畫 YYYY-MM-DD 收盤值」。*/
      const put = (html) => { noteEl.innerHTML = html; noteEl.hidden = !html; };
      if (!live) { put(''); return; }
      if (busy && !q) { put('<b class="live">即時</b>　抓取中…'); return; }
      if (liveErr) {
        put(`<b class="bad">即時抓不到報價</b>　${A.fmt.esc(liveErr)}`
          + '　<span class="muted">仍顯示收盤值</span>');
        return;
      }
      put(`<span class="warn">成交值估算</span>　涵蓋 ${cov[0]} / ${cov[1]} 檔`);
    }

    function paintFocus() {
      const el = $('#gpFocus', host);
      if (!el) return;
      const d = items.find(x => x.name === hi);
      /* ★ 2026-09-25（R3 審查）：滑到灰色「其他」那一塊，讀數列以前是清空的 —— 等於那一塊不能讀。
         它沒有單一族群可以對應，所以寫「其餘幾個、合計占多少、成交值多少」，也就是那一塊本身的意思。*/
      if (!d && hi === PIE_OTHER) {
        const od = pieData.find(x => x.name === PIE_OTHER);
        const tot = pieData.reduce((s2, x) => s2 + (x.value || 0), 0) || 1;
        el.innerHTML = od
          ? `<b style="color:${CH.ink2}">其他</b>　其餘 <b>${pieOtherN}</b> 個${drill ? '個股' : '族群'}合計`
            + `　占${drill ? '本族群' : '本頁'}成交值 <b>${A.fmt.n(od.value / tot * 100, 1)}%</b>`
            + `　成交值 ${A.fmt.yi(od.value)}`

          : '&nbsp;';
        return;
      }
      /* 說明精簡：沒滑過時不寫操作說明（搬進「怎麼看 ?」），留一個空白佔住這一行的高度，滑過時版面不會跳 */
      if (!d) {
        el.innerHTML = '&nbsp;';
        return;
      }
      el.innerHTML = `<b style="color:${d.color}">${A.fmt.esc(d.name)}</b>`
        + `　漲跌 <b class="${A.fmt.cls(d.chg)}">${A.fmt.pct(d.chg)}</b>`
        + `　占${drill ? '本族群' : '本頁'}成交值 <b>${A.fmt.n(d.share, 1)}%</b>`
        + `　成交值 ${A.fmt.yi(d.val)}`
        + (d.n != null ? `　${d.n} 檔` : '')
        + (d.live ? '　<span class="live">⚡ 盤中</span>' : (live ? '　<span class="muted">（收盤值）</span>' : ''));
    }

    /* 甜甜圈中心兩行字（標題＋大數字）。top 用像素算：圓心在 cy，兩行字的總高約 52px。*/
    /* ★ 2026-10-05 Andy：「圈內文字置中」—— 以前兩段 title 用像素 top（cy-30／cy-10）疊，容器後來被撐高、或字的行高不同，
       整塊字就偏上。改成一個 title、兩行 rich text、top:'middle' ＋ 圓心也用 '50%'，不管容器怎麼變都跟圓心對齊。cy 參數保留不用（呼叫端不必改）。 */
    /* ★ 2026-10-06（圖例搬到右邊之後甜甜圈的大小跟著卡片變）：中心字跟著圓的大小縮放 ——
       圓最小 160 時內圈只剩約 109px，34px 的「37.3%」（約 102px）會頂到環上。
       大數字＝邊長 × 0.115（夾在 20～34），小字標題的框不超過內圈的 86%（放不下的名字省略，全名在右邊圖例那一列）。*/
    function pieCenter(cy, t1, t2) { return A.donut.center(t1, t2, dnS || 300); }   // 規格在 A.donut.center（共用）
    /* 中心字「現在該寫什麼」：滑到某一塊＝那一塊的名字與占比，沒滑＝前五大合計（setHi 與 layoutDonut 共用）*/
    function pieTitleNow() {
      const pieHi = hi == null ? null : (pieTopNames.includes(hi) || hi === PIE_OTHER ? hi : PIE_OTHER);
      const tot = pieData.reduce((s2, d) => s2 + (d.value || 0), 0) || 1;
      const hd = pieHi ? pieData.find(d => d.name === pieHi) : null;
      return hd ? pieCenter(0, hd.name, A.fmt.n(hd.value / tot * 100, 1) + '%') : pieCenter(0, '前五大', A.fmt.n(pieTopShare, 1) + '%');
    }
    /* ★ 2026-10-06 Andy：「圖表資訊需要在右手邊，這樣圓餅圖才不會被壓縮」＋「其他圓餅圖也一樣」。
       圖例改成一列一項：色塊｜名稱｜成交值｜占比（四欄用 CSS subgrid 對齊，數字等寬、靠右、不截斷）。
       滑過＝跟滑過扇形同一支 setHi；點＝跟點扇形同一支 onPick（「其他」只看不點）。*/
    function paintLegend() {
      const el = $('#gpLegend', host); if (!el) return;
      const tot = pieData.reduce((s2, d) => s2 + (d.value || 0), 0) || 1;
      el.innerHTML = pieData.map(d => {
        const pc = A.fmt.n(d.value / tot * 100, 1) + '%', vl = A.fmt.yi(d.value);
        return `<button type="button" class="lg${d.name === PIE_OTHER ? ' other' : ''}" data-n="${A.fmt.esc(d.name)}" title="${A.fmt.esc(d.name)}：成交值 ${vl}（${pc}）">`
          + `<i style="background:${(d.itemStyle || {}).color || CH.ink3}"></i><span class="nm">${A.fmt.esc(d.name)}</span>`
          + `<span class="vl">${vl}</span><span class="pc">${pc}</span></button>`;
      }).join('');
      $$('.lg', el).forEach(bn => {
        bn.onmouseenter = () => setHi(bn.dataset.n);
        bn.onmouseleave = () => setHi(null);
        bn.onclick = () => { if (bn.dataset.n !== PIE_OTHER) onPick(bn.dataset.n); };
      });
    }
    /* 甜甜圈與圖例的排法（★ 2026-10-06）。輸入只有四個：卡寬（格線決定，不受內容影響）、是不是跟長條並排、
       長條圖高（paint 給）、圖例自己的寬高 —— 輸出（甜甜圈邊長）不會回頭改到輸入，所以 ResizeObserver 再叫一次也只會得到同一個答案，不會來回抖。
       · 卡寬 ≥ 420：圖例在右。邊長＝min(卡內寬 − 圖例寬 − 16, 可用高)；可用高＝並排時的長條高（卡片本來就跟長條一樣高）、上下疊時 340。
         剩不到 160 → 邊長 160、圖例的名稱欄讓出（max-width），數字欄不讓。
       · 卡寬 < 420：圖例在下（.dnbelow）。邊長＝min(卡內寬, 並排時「長條高 − 圖例高 − 8」／上下疊時 340)，下限 160（但不超過卡內寬）。
       回傳邊長有沒有變。*/
    function layoutDonut() {
      const card = pieEl.closest('.gpcard'), lg = $('#gpLegend', host), barCard = barEl.closest('.gpcard');
      if (!card || !lg || !card.isConnected) return false;
      const cr = card.getBoundingClientRect();
      if (!(cr.width > 0)) return false;
      const twoCol = !!barCard && Math.abs(barCard.getBoundingClientRect().top - cr.top) < 2;
      const side = cr.width >= DN_SIDE_MIN;
      card.classList.toggle('dnside', side); card.classList.toggle('dnbelow', !side);
      const cs = getComputedStyle(card);
      const cw = card.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
      lg.style.maxWidth = '';
      const lr = lg.getBoundingClientRect();
      const barH = dnBarH || barEl.clientHeight || 320;
      let S, lgMax = '';
      if (side) {
        let wAvail = cw - lr.width - DN_GAP;
        if (wAvail < DN_MIN) { wAvail = DN_MIN; lgMax = Math.max(0, Math.floor(cw - DN_MIN - DN_GAP)) + 'px'; }
        S = Math.max(DN_MIN, Math.min(wAvail, twoCol ? barH : DN_CAP1));
      } else {
        S = Math.min(cw, Math.max(DN_MIN, Math.min(cw, twoCol ? barH - lr.height - DN_GAP_V : DN_CAP1)));
      }
      S = Math.max(1, Math.floor(S));
      lg.style.maxWidth = lgMax;
      const changed = S !== dnS;
      if (changed || pieEl.style.width !== S + 'px') { pieEl.style.width = S + 'px'; pieEl.style.height = S + 'px'; }
      dnS = S;
      card.dataset.dn = (side ? 'side' : 'below') + ':' + S;
      gpDbg.donut = { side, S, twoCol, cardW: Math.round(cr.width), legendW: Math.round(lr.width), squeezed: !!lgMax };
      return changed;
    }
    /* 卡片寬度變了（拉視窗、側欄收合、跨過 820 由兩欄變一欄）→ 重排甜甜圈。延到下一幀做，免得在 ResizeObserver 回呼裡
       改尺寸觸發「ResizeObserver loop」錯誤；重排之後中心字依新邊長重寫（尺寸變了才寫）。
       字型晚到（Noto Sans TC 從 Google Fonts 下載）會讓圖例變寬但卡寬不變 —— 所以也盯著圖例本身。*/
    if (window.ResizeObserver) {
      let raf = 0;
      const ro = new ResizeObserver(() => {
        if (!pieEl.isConnected) { ro.disconnect(); return; }
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
          if (!pieEl.isConnected || !dnBarH) return;
          if (!layoutDonut()) return;
          const pi = window.echarts && echarts.getInstanceByDom(pieEl);
          if (pi && !pi.isDisposed()) { try { pi.resize(); pi.setOption({ title: pieTitleNow() }); } catch (e) { /* 正在被銷毀 */ } }
        });
      });
      const pc = pieEl.closest('.gpcard'), lg0 = $('#gpLegend', host);
      if (pc) ro.observe(pc);
      if (lg0) ro.observe(lg0);
    }

    /* 兩圖連動。**刻意用 setOption 改真的樣式**，而不是只送 highlight 事件：
       只送事件的話「扇形的樣式到底有沒有變」在畫面之外量不到，驗收就只能驗「我有呼叫」，
       那不是「畫面真的因此改變了」。這裡改的是描邊寬度與顏色，是真的畫上去的樣式。*/
    function setHi(name) {
      if (hi === name) return;
      hi = name || null;
      gpDbg.hi = hi;
      /* ★ 2026-09-23 修一個真的 JS 例外：`_uitest --only 產業` 在
         `#industry/ai_server/overview` 抓到
         `TypeError: Cannot set properties of null (setting 'innerHTML')`，
         堆疊在 echarts 的 `tooltip.setContent ← manuallyShowTip`。
         成因：`setOption` 會讓正在顯示的 tooltip 重繪，而這一頁換分頁／換主題時
         圖會被 dispose，滑鼠殘留的 hover 事件仍然排在後面 ——
         於是對著一個**已經被銷毀、tooltip DOM 已經是 null** 的實例重畫。
         兩道防線：① 先問 `isDisposed()`；② 整段包 try/catch。
         ② 不是偷懶 —— 這是「滑鼠事件與銷毀的競態」，不可能靠先後順序完全排除，
         而它一旦丟出例外就會污染整個驗收（那正是它被抓到的方式）。*/
      const live2 = (el) => { const i = window.echarts && echarts.getInstanceByDom(el);
        return (i && !i.isDisposed()) ? i : null; };
      const pi = live2(pieEl);
      const bi = live2(barEl);
      try {
      /* ★ W3-8：滑過的那個族群如果沒有自己的扇形（落在前五大以外），
         要讓**「其他」那一塊**亮起來 —— 不然滑過去等於沒反應，連動就斷在那裡。
         反過來滑「其他」時，長條那邊沒有單一對應，所以只亮圓餅（既有行為，不用特判）。*/
      const pieHi = hi == null ? null : (pieTopNames.includes(hi) || hi === PIE_OTHER ? hi : PIE_OTHER);
      if (pi) {
        pi.setOption({
          // 中心：滑到某一塊就寫它的名字與百分比，滑開回到「前五大 xx%」（字級跟著甜甜圈邊長，見 pieCenter）
          title: pieTitleNow(),
          series: [{ data: pieData.map(d => ({ ...d,
            itemStyle: { ...d.itemStyle, borderWidth: d.name === pieHi ? A.donut.BORDER_HI : A.donut.BORDER, borderColor: d.name === pieHi ? CH.ink : CH.panel } })) }] });
      }
      $$('#gpLegend .lg', host).forEach(bn => bn.classList.toggle('on', !!pieHi && bn.dataset.n === pieHi));
      if (bi) bi.setOption({ series: [{ data: barData.map(d => ({ ...d,
        itemStyle: { ...d.itemStyle, borderWidth: d.name === hi ? 2 : 0, borderColor: CH.ink } })) }] });
      } catch (e) { /* tooltip 與 dispose 的競態，下一次 hover 就會正常，不要炸掉整頁 */ }
      pieEl.dataset.hi = hi || '';
      barEl.dataset.hi = hi || '';
      paintFocus();
    }

    function onPick(name) {
      const d = items.find(x => x.name === name);
      if (!d) return;
      if (drill) { if (d.code) A.goStock(d.code); return; }
      drill = d.group; hi = null;
      if (live) { q = null; liveTick(); }
      keepPlace(paint);        // 換層級前後把整頁的水平／垂直位置顧好（見 keepPlace）
      if (ctx.onGroup) ctx.onGroup(d.gid);      // 產業鏈頁：順手把選取狀態換成這個族群（剖析圖與關聯圖都吃它）
    }

    function paint() {
      if (!host.isConnected) return;
      /* ★ 2026-09-25（R3 審查）：滑鼠停在甜甜圈上時點長條下鑽，主控台必噴
         `TypeError: Cannot set properties of null (setting 'innerHTML')`（echarts tooltip.setContent）。
         成因：下面兩張圖都用 notMerge 整個重設，重設會把 tooltip 元件拆掉重建，
         但正停在扇形上的那個提示框還排著一次「更新內容」，更新時它的 DOM 已經是 null。
         重畫之前先對兩張圖送 hideTip，把排著的那一次收掉；setHi 的 try/catch 管不到這一條（這條是 echarts 自己排的）。*/
      [barEl, pieEl].forEach(el => {
        const i = window.echarts && echarts.getInstanceByDom(el);
        if (i && !i.isDisposed()) { try { i.dispatchAction({ type: 'hideTip' }); } catch (e) { /* 沒有提示框可收 */ } }
      });
      const b = build();
      const n = Math.max(barData.length, 6);
      const h = Math.max(320, Math.min(660, n * 26 + 56));
      /* ★ 2026-10-06：甜甜圈改成「圖左、圖例右」—— 邊長交給 layoutDonut（依卡寬、長條高、圖例寬算），
         圖例要先畫出來才量得到寬，所以 paintLegend 提到這裡（改前在畫完圓餅之後）。
         改前的「圖例在下兩欄、甜甜圈高＝長條高 − 圖例高、窄畫面寬多少高就多少」整段由 layoutDonut 取代。*/
      barEl.style.height = h + 'px';
      dnBarH = h;
      paintLegend();
      if (!layoutDonut() && !dnS) { pieEl.style.width = pieEl.style.height = DN_MIN + 'px'; dnS = DN_MIN; }   // 卡片還沒排版：先給下限，ResizeObserver 會補
      backBtn.hidden = !drill;
      /* ★ 2026-09-26（Andy：「將所有『怎麼看』變成『?』，說明方式 Follow 總覽頁」）：
         改前：右上工具列一顆「怎麼看 ?」膠囊鈕，點了在卡片裡就地展開一整塊說明（把兩張圖往下推）。
         改後：標題文字右側一顆小圓「?」（.howbtn.pop），點了走 app.js howPop 的置中彈窗（點背景／Esc 關）。
         鈕寫在標題樣板裡，因為 #gpTitle 每次重畫都整段換 innerHTML；彈窗標題取標題的第一段字。*/
      const gpQ = '<button class="howbtn pop" data-how="gp" type="button" aria-label="這張圖怎麼看">?</button>';
      $('#gpTitle', host).innerHTML = drill
        ? `${A.fmt.esc(drill.name)}${gpQ}　<small class="muted">這個族群的個股漲幅（${b.asc.length}／${(drill.members || []).length} 檔）</small>`
        : `${A.fmt.esc(ctx.scope)}族群漲幅與占比${gpQ}　<small class="muted">列出成交值前 ${b.asc.length} 個族群</small>`;
      /* ★ 2026-09-24 說明精簡：同一份內容改成「一句問題 → 條列 → 最下面一行小字」，住在「怎麼看 ?」裡。*/
      const gpFine = '甜甜圈其餘併成「其他」，中心寫前五大合計；滑過任一邊，另一邊對應的那一塊同步標起來，下方那行寫出它的數字。'
        + '按「即時」＝盤中暫定值，每 5 秒更新：成交值是<b>估算</b>的（最新價 × 累積張數），'
        + '漲跌幅是這批個股的成交值加權；抓不到報價的仍用收盤值，所以占比只能當「相對大小」看。';
      // 彈窗開著時 #gpHint 被搬到 body 底下的 #howPop，host 裡找不到 —— 退回全域找，不然即時每分鐘重畫會丟例外
      ($('#gpHint', host) || document.getElementById('gpHint') || {}).innerHTML = drill
        ? A.howHTML('這個族群裡今天是誰在漲、量能集中在哪幾檔。', [
          '左邊長條由高到低，紅漲綠跌',
          '右邊甜甜圈只標成交值前五大',
          '怎麼用：漲得多、量也大＝主流',
          '只有漲幅、成交值卻小＝多半是跟風',
        ], gpFine)
        : A.howHTML(`${A.fmt.esc(ctx.scope)}今天哪一個族群在漲、錢集中在誰身上。`, [
          '左邊長條看方向，紅漲綠跌、由高到低',
          '右邊甜甜圈看份量，只標前五大',
          '怎麼用：兩邊都靠前＝今天真正的主流',
          '長條長、圓餅小＝小族群在噴，量未跟上',
        ], gpFine);
      paintNote();
      const axl = { ...A.axisStyle.axisLabel, fontSize: 12 };     // 設計 v4 2B：12px 下限（原 11.5）
      /* ★ 2026-09-24（Andy：長條一律「數值貼在末端外側，正右負左」）：負值的數字寫在長條左端外面，
         但長條左邊緊貼著的就是族群名 —— 390px 實測「AI 伺服器組裝」後面直接疊上「1.6%」，
         連負號都被名字蓋掉（看起來像正的）。所以跟資金流向排行同一個做法：
         把 x 軸下限往左多撐出「最寬那個負值標籤」的寬度（字寬是量的，不是估的），
         負值標籤就落在零軸左邊自己的空間裡，不會壓到名字。
         plotW 要扣掉左邊族群名的寬度（containLabel 會自己留那一塊）與右邊 52px 留白。*/
      /* ★ 2026-09-25（R3 審查）：**一檔極端值不准把其他長條壓扁**。
         法定產業別的「半導體・其他」因為 7856 漢測上櫃首日 +110%，一個族群 +37.8% 就把 x 軸撐到 40%，
         其他族群全擠在零軸旁邊幾個像素，這張圖就回答不了「哪個族群在漲」。
         做法：軸的兩端各用 95 百分位（取「下取整」那一名，15～20 條時剛好排除最極端的一條）當上限，
         超出的長條畫到上限就停，數字標籤改成長條內側的「▸ 實際值」—— 使用者一眼知道「這條被截了，真的是多少」。
         只有真的離群（超過 95 百分位的 2 倍、而且多出 5 個百分點以上）才截，平常的分布照畫原比例 ——
         半導體那種 +9.9% 對 +6.4% 是正常的領漲，不是離群，截了反而把「誰漲最多」藏起來。
         提示框與讀數列讀的是 items 的原值，不受影響。*/
      const q95 = (arr) => { if (arr.length < 4) return null;
        const a = arr.slice().sort((x, y) => x - y); return a[Math.floor(0.95 * (a.length - 1))]; };
      const rawVals = barData.map(d => +d.value || 0);
      const capOf = (arr) => { const q = q95(arr), mx = arr.length ? Math.max(...arr) : 0;
        return (q != null && q > 0 && mx > Math.max(q * 2, q + 5)) ? +(q * 1.12).toFixed(3) : null; };
      const capHi = capOf(rawVals.filter(v => v > 0));
      const capLo0 = capOf(rawVals.filter(v => v < 0).map(v => -v));
      const capLo = capLo0 != null ? -capLo0 : null;
      barData.forEach(d => {
        const v = +d.value || 0;
        const cut = (capHi != null && v > capHi) ? capHi : (capLo != null && v < capLo) ? capLo : null;
        d.raw = v; d.capped = cut != null;
        if (cut == null) return;
        d.value = cut;
        d.label = { ...d.label, position: v >= 0 ? 'insideRight' : 'insideLeft', color: '#fff', fontWeight: 700,
          formatter: (v >= 0 ? '▸ ' : '◂ ') + A.fmt.pct(v) };
      });
      const vals = barData.map(d => +d.value || 0);
      const negL = barData.filter(d => (+d.value || 0) < 0 && !d.capped).map(d => A.fmt.pct(d.value));
      const vMin = Math.min(0, ...vals), vMax = Math.max(0, ...vals);
      const nameW = A.textW ? A.textW(barData.map(d => d.name), 12) : 0;
      const plotW = Math.max(60, (barEl.clientWidth || 360) - 4 - 52 - nameW - 10);
      /* 負值標籤要留的寬度：用**等寬字**量（標籤畫的就是等寬字，用黑體量會量窄 3～4px），
         再加 5px 標籤離長條的距離與 12px 跟族群名之間的空隙。
         R3 審查量到以前只留 8px，扣掉 5px 距離剩 3px，於是「HBM 高頻寬記憶體-3.3%」黏成一串。*/
      const needL = negL.length && A.textW ? Math.ceil(A.textW(negL, 12, A.MONO)) + 5 + 12 : 0;
      const span0 = (vMax - vMin) || 1;
      const xMin = needL ? +(vMin - needL * span0 / Math.max(30, plotW - needL)).toFixed(3) : undefined;
      const narrowBar = plotW < 260;
      A.chart(barEl, {
        grid: { left: 4, right: 52, top: 8, bottom: 4, containLabel: true },
        tooltip: { ...A.tip, trigger: 'item', formatter: p => {
          const d = items.find(x => x.name === p.name) || {};
          return `<b>${A.fmt.esc(p.name)}</b><br>漲跌 <span style="color:${A.upDown(d.chg)}">${A.fmt.pct(d.chg)}</span>`
            + `<br>成交值 ${A.fmt.yi(d.val)}（${A.fmt.n(d.share, 1)}%）${d.n != null ? ' · ' + d.n + ' 檔' : ''}`
            ; } },
        /* ★ W3-8：格線收到極淡（有格線會跟長條搶注意力），改由**零軸那一條**負責分正負 */
        /* 軸刻度：窄畫面只留 3 格並開 hideOverlap —— 390px 實測五個刻度（-3.0%～9.0%）擠成一串疊在一起。
           撐出來的下限不是整數，刻度字只寫「落在資料範圍內」的那幾個，免得左端冒出一個 -4.37% 這種怪值。*/
        xAxis: { type: 'value', min: xMin, max: capHi != null ? capHi : undefined, splitNumber: narrowBar ? 3 : 5,
          axisLabel: { ...axl, hideOverlap: true, formatter: v => ((xMin != null && v < vMin - 1e-9) || (capHi != null && Math.abs(v - capHi) < 1e-6)) ? '' : A.fmt.n(v, 1) + '%' },
          splitLine: { show: false }, axisLine: { show: false }, axisTick: { show: false } },
        /* ★ W3-8：族群名**不准再被截斷**（以前超過 8 個字就加省略號，
           使用者看到的是「被動元件 MLC…」「AI PC 筆電…」—— 那等於沒寫名字）。
           `containLabel: true` 會自己把左邊留夠寬，所以拿掉 formatter 就好。
           ★ 零軸線：類別軸預設就畫在 x=0 上（onZero），只是以前用的是很淡的 line 色，
             正負分不開。改成用 ink3 ＋ 1.5px，讓它真的看得出來是一條分界。*/
        yAxis: { type: 'category', data: barData.map(d => d.name), axisTick: { show: false },
          axisLine: { show: true, onZero: true, lineStyle: { color: CH.ink3, width: 1.5 } },
          axisLabel: { ...axl, fontFamily: 'Noto Sans TC, sans-serif', color: CH.ink2 } },
        series: [{ type: 'bar', barMaxWidth: 17, data: barData, cursor: 'pointer' }],
      }, { notMerge: true });
      /* ★ 2026-09-24 甜甜圈改版（Andy 給了參考圖：「圓餅圖幫我設計這樣的樣式」）：
           · 粗環：內半徑 58%、外半徑 78%（環寬約半徑的 1/4），扇區之間只留 1.2° 的底色縫、扇區端點圓角
           · 環的內側一圈很細的淡色軌道（下面那個 series[1]），讓中心像一個圓盤
           · 中心兩行：上面小字標題（12.5px、輔助色）、下面大數字（34px、粗體、等寬）——
             平常寫「前五大」與它們的合計；滑到某一塊就換成那一塊的名字與百分比（setHi 裡改），滑開還原
           · 標籤**不再用引線拉到圓外**，改成圖下方兩欄的圖例（HTML，#gpLegend），名字不會跟引線搶位置
           · 滑到扇區：外擴 4px（emphasis.scaleSize），動畫 200ms
         W3-8 的「中心數字是真的算出來的」「只標前五大＋其他」「連動到其他」全部照舊。
         ★ 2026-10-06：圖例搬到右邊、一列一項（見 layoutDonut）；容器改成剛好包住圓的正方形，環放大成內 68%、外 92%
           （改前 58／78 是因為容器比圓大、要留白；外擴 4px 仍在 92% 之內：邊長 160 時外半徑 73.6＋4 < 80）。
           圓心照舊用 '50%'（2026-09-26 晚：容器高與 style 不一致會切掉上半截 —— 現在 #gpPie 的 min-height 已歸零、寬高都由 layoutDonut 寫死）。*/
      const cy = Math.round((pieEl.clientHeight || dnS || h) * 0.5);
      A.chart(pieEl, {
        tooltip: { ...A.tip, trigger: 'item', formatter: p => {
          const d = items.find(x => x.name === p.name);
          /* 2026-10-06 main：提示框拿掉「點一下…」操作說明（Andy 的清廢話）—— 共用風格的 hint 欄位留著，但產業地圖不給 */
          return A.donut.tipHtml(p.name, { valLabel: '成交值', val: A.fmt.yi(p.value), pct: p.percent, chg: d ? d.chg : null }); } },
        title: pieCenter(cy, '前五大', A.fmt.n(pieTopShare, 1) + '%'),
        animationDurationUpdate: A.donut.MS,
        series: A.donut.series({ cursor: 'pointer', data: pieData }),
      }, { notMerge: true });
      const bi = window.echarts && echarts.getInstanceByDom(barEl);
      const pi = window.echarts && echarts.getInstanceByDom(pieEl);
      /* 兩張圖的容器剛改過高度：當場對齊一次，不等下一幀的 ResizeObserver —— 不然這一幀甜甜圈的外半徑還是舊高度算的 */
      [[bi, barEl], [pi, pieEl]].forEach(([c, e]) => { if (c && e.clientHeight > 0 && (c.getHeight() !== e.clientHeight || c.getWidth() !== e.clientWidth)) c.resize(); });
      /* ⚠ 滑鼠**整個離開圖表**時 ECharts 發的是 `globalout`，不是 `mouseout`
         —— 只接 mouseout 的話，把滑鼠移到圖外面高亮會卡住不收（實測：描邊一直停在 3）。*/
      [[bi, 'bar'], [pi, 'pie']].forEach(([c]) => {
        if (!c) return;
        c.off('mouseover'); c.off('mouseout'); c.off('globalout'); c.off('click');
        c.on('mouseover', p => setHi(p.name));
        c.on('mouseout', () => setHi(null));
        c.on('globalout', () => setHi(null));
        c.on('click', p => onPick(p.name));
      });
      hi = null; pieEl.dataset.hi = ''; barEl.dataset.hi = '';
      paintFocus();
      gpDbg = { mode: drill ? 'stock' : 'group', rows: barData.length, live: live,
        capHi: capHi, capLo: capLo, capped: barData.filter(d => d.capped).map(d => ({ name: d.name, raw: d.raw, shown: d.value })),
        hi: null, liveCalls: gpDbg.liveCalls, drill: drill ? drill.id : null, donut: gpDbg.donut || null };
    }

    /* ★ 2026-09-25 效能（perf-2）：這一塊（族群總覽）在「選了一張剖析圖」時是藏起來的（#gpSec hidden，跟剖析圖互斥），
       以前照樣當場畫兩張 ECharts —— 首次開 #industry/semiconductor 在同一個任務裡白畫 174ms，而且畫在 0 寬的容器裡。
       改成：藏著就等它**真的露出來**（ResizeObserver：從 display:none 變成有尺寸就會通知）才畫第一次；
       沒藏就跟以前一樣當場畫。判斷只看 hidden 屬性（不量尺寸，免得又逼整頁排版）。*/
    const hiddenNow = () => !!(host.hidden || (host.closest && host.closest('[hidden]')));
    if (hiddenNow() && window.ResizeObserver) {
      const ro = new ResizeObserver(() => {
        if (!host.isConnected) { ro.disconnect(); return; }
        if (hiddenNow() || !host.clientWidth) return;
        ro.disconnect();
        if (gen === gpGen) paint();
      });
      ro.observe(host);
    } else paint();
    return { paint, stop: () => { stopTimer(); }, dbg: () => gpDbg };
  }
  // （`median` / `wavg` 已移除：它們只服務標題下那排標籤，W3-6 把那排整排拿掉了）

  // ================================================================ Level 1：單一產業鏈
  function chainData(im, cid) {
    if (!im) return null;
    // 跟分頁名一致（R3 審查：分頁寫「法定產業別」、h2 與麵包屑卻寫「產業別」）
    if (cid === 'industry') return { id: 'industry', name: '法定產業別', groups: im.industries };
    return im.chains.find(c => c.id === cid) || null;
  }
  /* ---------------------------------------------------------------- 剖析圖掛點（DECISIONS #225）
     2026-09-21 之前是「一條產業鏈一張圖」（`window.Diagrams[<chain id>]`），
     所以 docs/diagram_specs/ 那五張寫好的規格書一張都沒地方掛 ——
     它們畫的全是**族群層級**的東西（MLCC／面板／網通板卡都在 electronics 這一條鏈上）。
     現在查找順序：**選到的族群有專屬圖 → 這條鏈的預設圖 → 這條鏈成交值最大的那張族群圖 → 不畫。**
     名單只有一份，在 site/diagrams.js 的 SLOTS；這裡不准再維護第二份。*/
  const DS = window.DiagramSlots || null;
  // 這條鏈上有專屬剖析圖的族群，照成交值由大到小（沒選族群時就用第一個當預設）
  /* ★ 2026-09-23（Andy：「圖一這邊的標籤只需要顯示：以前族群名稱即可，後面說明在文章內有就好」）
     分頁上只印冒號前面那一段。SLOTS 裡的 `name` 是「族群名：這張圖在講什麼」的完整句子
     （例：「晶圓代工：一顆電晶體與一個製程迴圈」），整串印在分頁上會把一排分頁撐爆。
     ⚠ 只切**顯示用的那一份**，`DS.name()` 本身一個字都沒有動 ——
       完整名稱在「產品剖析圖」標題列、分頁的 title 提示、圖別選單的卡片標題都還要用。
     全形「：」與半形「:」都切（SLOTS 兩種都有寫過），取第一刀的前段；沒有冒號就整串照用。*/
  const dgShortName = (id) => String((DS && DS.name(id)) || id).split(/[：:]/)[0].trim() || id;
  const dgGroupsOf = (ch) => {
    if (!DS || !ch) return [];
    const has = new Set(DS.groupsOf(ch.id));
    return (ch.groups || []).filter(g => has.has(g.id))
      .slice().sort((a, b) => (b.turnover || 0) - (a.turnover || 0)).map(g => g.id);
  };
  /* ★ 2026-09-21：**不准再跨族群退回**（Andy：「一般電子點進去後就是 MLCC…
     他不代表全部」）。以前產業鏈頁沒選族群時會退回「這條鏈成交值最大的那張族群圖」，
     electronics 只有 MLCC 一張，於是「點進一般電子 ＝ 看到 MLCC」——
     MLCC 是被動元件，它代表不了面板、交換器板卡、PCB。
     現在查找只剩兩層（都在 DS.pick 裡）：**選到的族群有自己的圖 → 這條鏈的鏈層級圖 → 沒有**。
     沒有就是沒有，不借別人的；鏈層級沒圖的鏈改成顯示「圖別選單」（見 renderChain）。
     個股頁本來就走這一條（一檔面板股掉到 MLCC 圖上等於宣稱它做 MLCC），行為不變。*/
  const dgPick = (ch, gid) => (DS && ch) ? DS.pick(ch.id, gid) : null;
  const HAS_DIAGRAM = (cid) => !!(DS && DS.anyIn(cid));
  /* ---------------------------------------------------------------- 圖別入口
     Andy 2026-09-21：「不能一般電子點進去後就是 MLCC，因為他不代表全部…
     若像是 IC 設計、晶圓代工、封裝等等，那就可以放同一頁，形成一個架構，
     但若是其他同個族群、為不同產品，則需要獨立分頁」。
     那條規則沒有變：**同一條鏈但彼此不相干的產品各自獨立分頁、各有各的網址**。

     ★ 2026-09-23 第二批（W3-7，Andy：「下方的字卡也拿掉 因為上方分頁就有同樣功能了」）：
       承載它的 `dgMenuHtml()`（下方那排大卡片）整支移除 ——
       它跟二層分頁列 `dgTabsHtml()` 是**同一份東西畫兩次**：同樣的 `dgOpts`、
       同樣的 `dgHash(id)`、連網址都一模一樣。
       原本寫在卡片上的三件事現在的位置：
         ①圖名的完整版 → 分頁的 `title=`（分頁上只印冒號前那一段，見 W3-4）
         ②這張圖回答什麼問題 → 分頁的 `title=` ＋ 進到圖裡之後的 `#dgQ` 那一行
         ③這個族群現在多大 → 第一個分頁（族群總覽）的長條圖與圓餅圖
       —— 一件都沒有消失，只是不再畫兩次。*/
  // 哪些環節屬於這條鏈（半導體鏈把載板／封測也畫進來；AI 伺服器鏈把代工／封裝／HBM 畫進來）
  /* 一條鏈要畫哪些環節。
     ★ 2026-09-19（Andy 圖十「連線根本都沒對齊 確實連線」）查出來的第一個根因：
       AI 伺服器鏈**沒有把 ic_design 算進來**，可是 supply_chain.yaml 裡
       NVIDIA / AMD / Broadcom / Marvell 都掛在 ic_design ——
       它們不在圖上，於是所有「IC 設計 → 代工／封裝／載板」的邊在
       `coPos[e.from]` 查不到節點而被整條丟掉（實測 17 條）。
       結果就是 34 家裡有 11 家完全沒有線，看起來像「連線漏畫」。 */
  /* 2026-09-19 查證後改：`abf_pcb`（IC 載板）的 chain 從 ai_server 改成 semiconductor
     —— 載板本來就是半導體封裝環節，這一改，載板三雄在半導體鏈上孤立的問題就一起解決了。
     反過來 AI 伺服器鏈要把載板、封測、測試介面、載板材料都拉進來：
     `kyec → nvidia`（AI 晶片測試）這種邊以前在 AI 鏈的圖上會被整條丟掉。
     成果：孤立節點 AI 鏈 10 → 1、半導體鏈 13 → 0。*/
  const CHAIN_EXTRA = {
    ai_server: ['ic_design', 'foundry', 'adv_pkg', 'hbm', 'abf_pcb',
                'substrate_material', 'osat_test', 'test_interface'],
    semiconductor: [],
    /* 2026-09-19：一般電子鏈本來一個環節都沒有，補了 8 格之後還缺三格別條鏈的。
       為什麼要拉進來（而不是在 electronics 再開一次節點）：鴻海 2317、緯創 3231、
       智邦 2345 的節點已經在 assembly／switch，同一檔台股不准有第二個節點 ——
       tw_code 重複 pytest 當場紅，而且個股頁的麵包屑會由 YAML 順序決定要顯示哪一格。
         assembly  → 鴻海與緯創（handset_chain 權重最大的兩檔）看得到，
                     而且 foxconn → apple 這條邊才畫得出來
         ic_design → 聯發科（手機 SoC）、聯詠（驅動 IC）、瑞昱（網通晶片）
                     才是這條鏈真正的上游；catcher → nvidia 也要靠它
         switch    → 智邦是 networking 族群最大那檔，不拉進來它在自己的鏈上是隱形的
       ★ 已知副作用：會一併帶進緯穎 6669（純雲端，最突兀）與 NVIDIA／AMD／Broadcom／
         Marvell。廣達與英業達本來就是筆電 EMS 巨頭，不算誤導；緯穎是接受的代價。 */
    electronics: ['ic_design', 'switch', 'assembly'],
  };
  function chainSegments(sc, cid) {
    if (!sc) return [];
    const extra = CHAIN_EXTRA[cid] || [];
    return sc.segments.filter(s => s.chain === cid || extra.includes(s.id));
  }
  /* ---------------------------------------------------------------- 產業關係的措辭
     Andy 2026-09-19：「點擊關聯圖時，在旁邊新增這類說明，更加明白產業關係」。
     這幾支是**唯一**產生關係文字的地方 —— 圖上的 tooltip 與旁邊的說明面板走同一套，
     不然同一條邊會出現兩種講法。*/
  /* up＝這條邊的另一端在上游（它供給我）、down＝另一端在下游（我供給它）。
     措辭一律站在「被點開的那家公司」的角度講，不然「供貨給 味之素」會被讀成方向相反。*/
  const REL_TEXT = {
    supplies: { up: '供應商', down: '客戶', label: '供貨' },
    outsources_to: { up: '把製程委外給它的是', down: '委外代工給', label: '委外代工' },
    designated_by: { up: '它的料號由這家指定', down: '料號由它指定', label: '指定料號 AVL' },
    produced_by: { up: '由它生產', down: '生產', label: '生產' },
  };
  /* confidence 一定要看得見。這份資料有一半是「產業邏輯推論」而不是公司揭露，
     不標出來的話，使用者會把推論當成事實 —— 那正是這張圖最容易造成的傷害。*/
  const CONF_TEXT = { verified: '官方揭露', reported: '媒體報導', estimated: '產業推論' };
  /* 推論標籤的滑過說明（Andy 2026-09-25：只有推理的才要說明）。*/
  const EST_TIP = '產業推論＝由公開資訊推得，非公司或媒體揭露';
  /* 佐證連結。只認 https:// 開頭的 —— YAML 是人維護的，
     萬一有人寫了 javascript: 這種東西，這裡就是最後一道關。*/
  const srcLink = (u) => {
    const url = String(u || '').trim();
    if (!/^https:\/\//.test(url)) return '';
    let host = url; try { host = new URL(url).hostname.replace(/^www\./, ''); } catch (e) { /* 壞網址就印全文 */ }
    return `<a class="src" href="${A.fmt.esc(url)}" target="_blank" rel="noopener noreferrer">佐證：${A.fmt.esc(host)} ↗</a>`;
  };
  const relLabel = (e) => {
    const r = (REL_TEXT[e.rel] || {}).label || e.rel || '關聯';
    return `${e.item || r}${e.note ? '（' + e.note + '）' : ''}`;
  };
  const segName = (sc, id) => ((sc && sc.segments.find(s => s.id === id)) || {}).name || id;
  const segColor = (id) => A.L.segColor(id);      // 讀的當下才取色，切主題才跟得上
  const twOf = (sc, seg) => (sc ? sc.companies.filter(c => c.segment === seg && c.tw_code) : []);
  const foreignOf = (sc, seg) => (sc ? sc.companies.filter(c => c.segment === seg && !c.tw_code) : []);

  function renderChain(im, sc, gd, opts) {
    opts = opts || {};
    const ch = chainData(im, state.chain);
    if (!ch) { show(true, false, false); renderMap(im); return; }
    show(false, true, false); crumbs([{ label: '產業地圖', href: '#industry' }, { label: ch.name }]);
    const el = $('#indChain');
    /* 重畫這一頁之前先把上一個 3D 場景收掉。
       innerHTML 一換，舊的 canvas 就離開 DOM，但它的 requestAnimationFrame 迴圈還活著 ——
       用上方切換列連續換幾條鏈，就會累積好幾個在背景空轉的 WebGL context（瀏覽器上限約 16 個）。*/
    dispose3D();
    /* 這一頁要畫哪一張剖析圖（族群優先、鏈為預設）。dgId 會隨「點族群卡片」換，
       所以它是 let；換圖走 swapDiagram()（有淡出淡入，不會閃一下）。*/
    /* 「使用者正在族群總覽裡看某個族群的個股長條圖」。它不是網址的一部分
       （原地展開不是一次導覽），但 resolveDg 要看得到它，所以宣告在這一層。*/
    let gpDrilled = false;
    const dgGroups = dgGroupsOf(ch);
    // 這條鏈總共有哪幾張圖（鏈層級的排前面）。圖別選單與切換晶片都讀這一份
    const dgOpts = (DS && DS.chainDefault(ch.id) ? [DS.chainDefault(ch.id)] : []).concat(dgGroups);
    /* ★ 2026-09-23：**鏈層級的架構圖也要帶 /dg/**（以前它的網址就是 `#industry/<chain>`）。
       因為 `#industry/<chain>` 現在是「族群總覽」那一個分頁（Andy：每一條鏈的 Default
       都是族群漲幅長條圖＋占比圓餅圖），鏈層級的圖不能再跟它共用同一個網址 ——
       共用的話那條鏈就永遠打不開族群總覽。*/
    const dgHash = (id) => '#industry/' + ch.id + '/dg/' + id;
    /* ★ 2026-09-21：**畫面換了，網址就一定要跟著換。**
       踩到的情形：在 `#industry/electronics/dg/mlcc` 上點「面板」族群（它沒有專屬圖），
       畫面正確地換回圖別選單了，**網址卻還停在 /dg/mlcc** ——
       於是「複製網址貼給別人，對方看到的跟你看到的不是同一個東西」，
       而那正是「剖析圖改成獨立分頁」這件事要解決的問題本身。
       按重新整理或上一頁也會跳回剖析圖。

       用 `history.replaceState` 而**不是**改 `location.hash`：
       改 hash 會觸發 router 整頁重畫，把 segFilter 之類的頁內狀態沖掉；
       而點族群卡片是**頁內篩選**，不是一次導覽 —— 不該在歷史紀錄裡多留一筆。
       （從圖別選單點進某一張圖那條路徑仍然是真的導覽，用的還是 hash，上一頁回得去。）*/
    const syncDgHash = () => {
      const want = resolveDg();
      state.dg = want;
      /* ★ 沒有圖＝族群總覽，它的網址是 `/overview`（不是光禿禿的 `#industry/<chain>`
         —— 那個現在是「第一張剖析圖」的網址，寫回去會讓重新整理跳到圖上）。*/
      const h = want ? dgHash(want) : '#industry/' + ch.id + '/overview';
      try { if (location.hash !== h) history.replaceState(null, '', h); } catch (e) { /* 舊瀏覽器沒這支就算了 */ }
    };
    /* 這一頁現在該畫哪一張剖析圖（或不畫）。順序是刻意的：
         ① 在族群總覽上「點長條鑽進某個族群」→ 一律不畫圖（使用者正在看個股長條圖，
            把它換成一張剖析圖等於把他剛剛點開的東西搶走）
         ② 使用者選到的族群有**自己的**圖 → 就是那一張（strict，不借別人的）
         ③ 網址指定了 /dg/<slot> 而且那張圖真的掛在這條鏈上 → 那一張
       都不成立就回 null ＝ **族群總覽分頁**（第一個分頁，Andy 2026-09-23 指定的 Default）。
       ★ 這裡**刻意不再退回 `DS.chainDefault`**：退回去的話 AI 伺服器鏈永遠打不開族群總覽，
         因為它有一張鏈層級的機櫃圖，會把第一個分頁吃掉。*/
    const resolveDg = () => {
      if (gpDrilled) return null;
      const cur = (state.dg && DS && DS.has(state.dg) && DS.chainOf(state.dg) === ch.id) ? state.dg : null;
      if (state.group) {
        const own = (DS && DS.level(state.group) === 'group' && DS.chainOf(state.group) === ch.id) ? state.group : null;
        if (own) return own;
        /* 選到一個沒有自己的圖的族群：
             正在看的是**整條鏈的架構圖** → 留著（它本來就涵蓋整條鏈，不是在替某個族群說話）
             正在看的是別的族群的產品圖   → 收起來，回族群總覽
           （後者就是 DECISIONS #225「不准跨族群退回」那一條，一個字都沒有放寬。）*/
        return (cur && DS.level(cur) === 'chain') ? cur : null;
      }
      return cur;
    };
    /* ★ 2026-09-23 第二批：`#industry/<chain>` 的 Default ＝ **這條鏈的第一張剖析圖**
       （鏈層級有圖就那張，沒有就這條鏈成交值最大的那個族群圖 —— dgOpts 本來就是這個順序）。
       只在「使用者沒有指定任何東西」時才補：
         · 走 `/overview` 進來（DG_OVERVIEW 哨兵）→ 他明講要族群總覽，不補
         · 已經指定了某一張圖（`/dg/<slot>`）或某個族群 → 照他的，不補
       補完就把哨兵清掉，後面 resolveDg 只要照原本的規則讀 state.dg 就好。
       ⚠ 這一條**蓋掉 DECISIONS #252 的 Default**，但族群總覽沒有被刪（見上面 /overview 那條路）。*/
    /* 「使用者自己走到某一張圖的網址」＝ /dg/<slot>。手機的預設收合只對「順著鏈逛進來」
       的人有效，不該蓋掉明確的意圖；但**自動補上的 Default 不算明確意圖** ——
       不然手機一進產業鏈就直接吃到一張 1000px 高的圖，Andy 抱怨過兩次的「上下框度太長」會回來。*/
    const dgExplicit = !!state.dg && state.dg !== DG_OVERVIEW;
    if (state.dg === DG_OVERVIEW) state.dg = null;
    else if (!state.dg && !state.group && dgOpts.length) state.dg = dgOpts[0];
    let dgId = resolveDg();
    const hasSlots = dgOpts.length > 0;     // 這條鏈有圖可看（可能是選單狀態）
    // 宣告要早於任何會呼叫 swapDiagram 的路徑（wireDg → wire3D → sync），不然會踩到 TDZ
    let swapping = false;
    // 剖析圖是展開還是收起來（手機預設收）。swapDiagram 也要看得到它，所以放在這一層
    let dgOpen = true;
    /* 3D 有沒有接上線（wireDg 沒帶 skip3d 跑過一次）。★ 2026-09-24 從 `if (hasSlots && sc)` 區塊裡搬上來：
       收合狀態下換圖（點族群晶片 → swapDiagram）會用 wireDg(true) 把 3D 鈕藏起來，
       但區塊裡那份 did3d 還是上一張圖留下的 true —— 展開時 paintFold 以為「接過了」，
       結果新那張圖**連 3D 鈕都不見**。放在這一層，swapDiagram 才改得到它。*/
    let did3d = false;
    const groups = state.group && ch.id === 'industry' ? ch.groups.filter(g => g.id === state.group) : ch.groups;
    /* ★ 2026-09-23 第二批（W3-6，Andy：「分頁的這紅框處標籤都拿掉」）：
       標題底下那排 `N 檔 ／ 今日 +x% ／ 本益比中位 ／ ← 返回` 整排移除。
       三個數字**不搬家**（他說的是拿掉，不是換位置）—— 檔數、今日漲跌、本益比
       在族群總覽那一頁的長條圖與圓餅圖上本來就看得到。
       `A.L.back()` 這支工具**沒有刪**，個股頁與題材頁還在用，只是這一頁不再呼叫它；
       換鏈走上方的分頁列、回上一頁走瀏覽器，導覽沒有任何一條路徑只靠它。
       `chg` / `pes` 跟著沒人用了（`wavg` / `median` 也只有這裡呼叫），一起清掉。*/
    const segs = chainSegments(sc, ch.id);
    /* ★ 2026-09-19：關聯圖跟剖析圖拆開判定。
       以前兩者共用 hasDiagram（只有 semiconductor / ai_server 有剖析圖），
       所以一般電子鏈補了 8 個環節、16 家公司、6 條邊之後，環節色標出現了，
       **關聯圖卻整張不見** —— 因為它被綁在「有沒有剖析圖」這個完全不相干的條件上。
       兩者的資料來源本來就不同：剖析圖來自 window.Diagrams，關聯圖來自 YAML 的 edges。 */
    const hasMap = !!(sc && segs.length);
    const otherChains = (im.chains || []).filter(c => c.id !== ch.id);
    /* E5：頁面最上方的類別切換列（Andy 2026-09-18：「產業鏈頁上方要有類別切換列，不用退回去」）。
       以前只有卡片最下面那排「其他產業鏈」連結 —— 看完剖析圖要換一條鏈，得先捲到最底或退回產業地圖。
       這一列固定在標題上方，按了直接換鏈（換 hash，router 會重畫），現在這條標成 on。*/
    /* 二層分頁（這條鏈的產品剖析圖）。**第一個分頁固定是「族群總覽」**
       —— 那是 Andy 指定的 Default 畫面（族群漲幅長條圖＋占比圓餅圖）。
       每一頁都是真的 <a href>（有自己的網址，可分享、可回上一頁、重新整理打得開），
       class 沿用 `segchip` 並保留 `.sel`：既有的換圖邏輯與驗收都認這兩個，
       活頁簿的外觀由 `.nbsw` 負責（它的選擇器權重比 `.segchip` 高）。*/
    const dgTabsHtml = () => `<div class="chainsw nbsw lv2" id="dgPick" role="tablist">`
      + `<a class="segchip${dgId ? '' : ' sel on'}" data-dgtab="overview" href="#industry/${ch.id}/overview" role="tab" style="--c:var(--cyan)" title="這條鏈各族群的漲幅與占比"><i></i>族群總覽</a>`
      + dgOpts.map(id => `<a class="segchip${id === dgId ? ' sel on' : ''}" data-dgid="${id}" href="${dgHash(id)}" role="tab" style="--c:${A.L.gcolor[id] || 'var(--cyan)'}" title="${A.fmt.esc(DS.name(id))}${DS.q(id) ? '　·　' + A.fmt.esc(DS.q(id)) : ''}"><i></i>${A.fmt.esc(dgShortName(id))}</a>`).join('')
      + `</div>`;
    /* 產業地圖那一層的內容留在 DOM 裡的話，`#chainSwitch`／`#gpBar` 會同時出現兩份
       （一份看得見、一份被 display:none 藏著），getElementById 只拿得到前面那個。*/
    { const mp = $('#indMap'); if (mp) { disposeCharts(mp); mp.innerHTML = ''; } }
    gpStopLive();
    disposeCharts(el);
    el.innerHTML = `
      ${chainTabsHtml(im, ch.id)}
      <div class="card nbcard">
        <!-- ★ 2026-09-24 說明精簡：頁首那段「同一套顏色、點了會怎樣」(#nbIntro) 搬進「怎麼看 ?」，頁首只留鏈名。 -->
        <div class="row spread nbhead" data-howsec><h2>${A.fmt.esc(ch.name)}${state.group && ch.id === 'industry' ? ' · ' + A.fmt.esc((groups[0] || {}).name) : ''}${hasSlots || hasMap ? '<button class="howbtn pop" data-how="nb" type="button" aria-label="這一頁怎麼看">?</button>' : ''}</h2></div>
          ${/* ★ 2026-09-26（Andy：「將所有『怎麼看』變成『?』，說明方式 Follow 總覽頁」）：
                 nb／dg／rel 三顆（加上族群總覽的 gp）改前是右側「怎麼看 ?」膠囊＋就地展開；
                 改後是標題文字右側的小圓「?」（.howbtn.pop），點了走 app.js howPop 的置中彈窗。
                 #how-xx 盒子留在卡片裡（howPop 關的時候搬回原位，驗收與 #nbIntro／#dgQ／#relHint 的寫入照 id 找得到）。*/ ''}
          ${/* ★ 2026-09-24（審查 R3）：這段說明以前還在講退版前的「關聯圖大圓點／個股小點」，
                 而且沒有關聯圖的鏈（傳產、基礎建設）也照樣講關聯圖與色標。改成照這一頁真的有什麼來講：
                 有剖析圖 × 有關聯圖三種組合各一份，不提畫面上沒有的東西。*/ ''}
          ${hasSlots || hasMap ? `<div class="howtxt" id="how-nb" hidden><div id="nbIntro">${hasSlots && hasMap
            ? A.howHTML('這條鏈由哪些環節組成、每一格有誰。', [
              '零件、環節選單、關聯圖公司卡同一套顏色',
            ])
            : hasSlots
              ? A.howHTML('這條鏈的產品由哪些零件組成、每一格是誰做的。', [
                '同色的零件屬於同一個環節',
              ])
              : A.howHTML('這條鏈由哪些環節組成、每一格有誰。', [
                '環節選單、關聯圖公司卡同一套顏色',
              ])}</div></div>` : ''}
        ${dgTabsHtml()}
        <div class="nbbody">
        <div id="gpSec" data-howsec></div>
        ${hasSlots ? `<div style="margin-top:2px" id="dgSec" data-howsec><div class="row spread dgsechead">
          <!-- ★ 2026-09-23 第十批 C1（Andy：「幫我將 產品剖析圖、族群總覽、配色拿掉、另外收合圖 移動到上方同一排」）
               ⚠ 這段註解住在樣板字串裡，所以**不能出現反引號**（會把字串提早結束掉）。
               三件一起拿掉，各自的功能都沒有消失：
                 ·「產品剖析圖」那個 h4：上方二層分頁列本來就寫著現在在看哪一張，標題只是把同一句話再講一次。
                   圖名 #dgTitle 留著（改成獨立的一行小字），它還寫了「原創示意圖、點零件看供應商」這些真的資訊。
                 ·「← 族群總覽」#dgBack：分頁列第一格就是族群總覽，同一個目的地兩顆鈕。
                 ·「配色：科技」#dgPal：上一批（W3-10）做好「切全站主題 → 剖析圖配色自動跟著切」之後，
                   手動那顆就是多餘的；他要的是跟著主題，不是自己按。
                   自動切換那條路（themePal／tw:theme）一行都沒動，wirePal 仍然會被呼叫來接 3D 的 setPal。
               「收合圖 ▴」#dgFold 因此不再被前面三顆擠到第二行，跟其餘設定鈕同一排。 -->
          <div class="dgsectitle"><small class="muted" id="dgTitle"></small><button class="howbtn pop" data-how="dg" data-ttl="產品剖析圖" type="button" aria-label="產品剖析圖怎麼看">?</button></div><span class="row" id="dgTools" style="gap:6px"><span class="seg tiny dgmode" id="dg3d" data-mode="2d" role="group" aria-label="剖析圖顯示方式：平面或立體" hidden><button type="button" data-dm="2d" class="on" aria-pressed="true" title="平面剖析圖">2D</button><button type="button" data-dm="3d" aria-pressed="false" title="立體剖析圖（可拖曳轉動、滾輪拉近）">3D</button></span><span class="pill" id="dgAnim" style="cursor:pointer">動畫：開</span><span class="pill" id="dgFold" style="cursor:pointer">收合圖 ▴</span></span></div>
          <!-- ★ 2026-09-24 說明精簡：「這張圖回答」(#dgQ) 與操作說明搬進「怎麼看 ?」；圖名與「原創示意圖，非實物比例」留在 #dgTitle。 -->
          <div class="howtxt" id="how-dg" hidden><div id="dgQ"></div>${A.howHTML('', [
            /* ★ 2026-10-04（docs/howto_audit_1004.md 第 5 項）：改前五條寫死給所有鏈，傳產這類鏈沒有關聯圖、也沒有 2D/3D，
               照樣寫「關聯圖會一起亮」「3D 可拖曳」。改成：關聯圖那句只在 hasMap 時出現；
               3D 那條由 wire3D 在 2D/3D 切換鈕真的出現時才補進這份條列（見 wire3D 的 btn.hidden = false 那段）。*/
            ...(hasMap ? ['同色的環節色標、關聯圖會一起亮'] : []),
          ])}</div>
          <!-- ★ 2026-09-26（Andy：「拖曳、重設視角，移動到下面，另外新增 點兩下重設視角」）
               ⚠ 這段註解住在樣板字串裡，所以不能出現反引號。
               「拖曳：轉動」「重設視角」兩顆從上面的設定列搬進 3D 畫面框內的右上角（#dg3dCtl）：
                 · 它們只對 3D 有意義，放在設定列裡跟「怎麼看／2D 3D／動畫／收合」擠在同一排，
                   2D 時要藏、3D 時要冒出來，整排的寬度跟著跳；放進 3D 畫面裡就跟著畫面一起出現、一起消失。
                 · 包一層 .dg3dbox（position:relative）而不是塞進 #prod3d 裡面：
                   #prod3d 在換圖、切 2D 時會被 innerHTML 清空，住在裡面的鈕會被一起清掉、id 也查不到。
                 · 右欄的卡片由 three3d.js 的 pack 從這組鈕的下緣開始排（mount 傳 reserveTR），所以不會壓到編號卡片。 -->
          <div id="dgBody">
          <div id="prodDiagram" class="dgwrap" style="transition:opacity .18s">${dgId ? DS.draw(dgId) : ''}</div><div class="dg3dbox"><div id="prod3d" class="dg3d" hidden></div><div class="dg3dctl" id="dg3dCtl" role="group" aria-label="3D 視角操作" hidden><button type="button" class="pill" id="dgDrag" title="左鍵拖曳要轉動還是平移（右鍵一律平移）">拖曳：轉動</button><button type="button" class="pill" id="dgReset" title="回到一開始的視角（也可以在 3D 畫面上點兩下）">重設視角</button></div></div><div class="note" id="dg3dNote" hidden></div><div id="partCard" class="partcard" hidden></div></div></div>` : ''}
        </div>
        ${hasMap ? `<div class="relsec" id="relSec" data-howsec>
          <div class="row spread" id="relHead"><h4 style="margin:0">供應鏈關聯圖<button class="howbtn pop" data-how="rel" type="button" aria-label="供應鏈關聯圖怎麼看">?</button></h4>
            <span class="row" style="gap:6px"><span class="pill" id="relFold" style="cursor:pointer">收合圖 ▴</span></span></div>
          <div class="howtxt" id="how-rel" hidden><div id="relHint"></div></div>
          <!-- ★ 2026-09-24（Andy：「只留下供應鏈關聯圖，其他的用清單方式呈現族群以及個股」，
               之後再補明確指示：上方的標籤改成下拉清單、下方那片環節字卡全部拿掉）。桌機（大於 820px）才動：
               ⚠ 這段註解住在樣板字串裡，所以不能出現反引號。
               · 圖上方那一大片環節色標 → 一顆「環節：全部 ▾」下拉（樣式照資金輪動卡的「產業鏈：全部 ▾」）。
                 下拉面板就是原本的 #segChips，裡面每一列仍然是 .segchip[data-seg]（.sel、.nomem 全部沿用），
                 所以「點色標＝篩這一格／再點取消」那條路一行都沒換，只是從一排按鈕收進一個選單。
               · 選了一格之後，圖的右邊才長出 #relList：那一格有哪些族群、每個族群是哪幾檔、今天漲跌。
                 沒選的時候不顯示（全部列出來就又是一份跟圖重複的東西），圖用滿整個寬度。
               · 圖下方的環節字卡 #chainList 在桌機藏起來（跟圖重複）；手機照舊。
               · 環節詳情 #segBox 移到圖的下面（放上面的話，選一格會把圖往下推）。
               手機（820px 以下）：下拉鈕藏起來、面板攤開成原本那排色標，#relList 不顯示，順序照舊「色標 → 環節詳情 → 圖」。 -->
          <div class="chainrow" id="relRow"><div class="chainpane">
            <div class="relmain" id="relMain">
              <div class="segdd" id="segDD"><button type="button" class="ddbtn" id="segDDBtn" aria-haspopup="listbox" aria-expanded="false" title="環節">環節：<b>全部</b><i aria-hidden="true">▾</i></button>
                <div class="segchips ddpanel" id="segChips" role="listbox" aria-label="環節"></div></div>
              <div class="relcol"><div class="relstick" id="relStick"><div class="rellist" id="relList"></div></div></div>
              <div id="segBox"></div>
              <div class="chainmap" id="chainMap"></div>
            </div>
            <div class="segtools" id="segTools"></div>
            <div class="seglist" id="chainList"></div>
          </div></div></div>` : ''}
        ${otherChains.length && !(window.matchMedia && matchMedia('(min-width: 821px)').matches) ? `<div class="linkrow chainothers"><span class="muted">其他產業鏈</span>${otherChains.map(c => A.L.chain(c.id, c.name)).join('')}${A.L.chain('industry', '法定產業別')}</div>` : ''}
      </div>`;
    /* ★ 族群卡片 `#groupCards` 已移除（DECISIONS #248）。
       它承載的兩件事都搬到關聯圖上，一件都沒有消失：
         「檔數／占比／漲跌／族群頁連結」→ 大圓點本身與右側資訊欄
         「點卡片選起這個族群」         → 點大圓點（onGroup → state.group，同一條路）*/
    /* ★ 2026-09-23 第十批 C5 退版（Andy 逐字：「下方的關聯圖回到之前的設計，幫我退版
       回到之前的格式，但是需要將關聯圖置中，並且，Default 顯示族群相連標籤個股，
       點擊後才會跳初下拉清單，並且點擊股票 右側會顯示對應訊息」）。
       族群力導向星際圖（DECISIONS #248）整組退場，換回 a846f16 的分層形式。
       這裡只負責把環節色標填回 `#segChips`（它是這一頁「選一格」的總入口）——
       圖與清單要等 syncHighlight／segPick 都宣告完才畫得起來，所以放在下面。*/
    /* ★ 2026-09-24：色標收進「環節：全部 ▾」下拉，選中的那一格在圖右邊列族群與個股（見 renderSegPicker）。
       下拉裡的每一列仍然是同一顆 .segchip，所以下面掛事件、syncHighlight 切 .sel 的程式碼不用換路。*/
    renderSegPicker($('#segChips', el), $('#relList', el), sc, segs, im);
    const segDDOpen = wireSegDD(el);
    /* ★ 設計 v4 第二批 2B（04 文件 §0 ⑨⑩）：產業鏈頁兩處「一個元件獨佔一整列」收進既有的列：
         · 鏈名標題（h2＋「?」）跟二層分頁列（族群總覽／各張剖析圖）同一列 —— 標題在左、分頁接在右邊；
           **放得下才併**（分頁列沒被擠出橫向捲動），放不下照改前兩列（fitNbHead，視窗寬度一變重量一次）。
         · 「環節：全部 ▾」下拉搬進「供應鏈關聯圖」標題列（標題右邊）—— 只在桌機（≥821，下拉本來就只在桌機是一顆鈕；
           手機那排色標不動）。元素、id、事件都不變，只換父層；視窗跨過 820 時搬回去。*/
    fitNbHead($('.nbcard', el));
    {
      const mq = window.matchMedia ? window.matchMedia('(min-width:821px)') : null;
      const dd = $('#segDD', el), rh = $('#relHead', el), rm = $('#relMain', el), rs = $('#relSec', el);
      const place = () => {
        if (!dd.isConnected) { if (mq) { try { mq.removeEventListener('change', place); } catch (e) { /* 舊瀏覽器 */ } } return; }
        const desk = !mq || mq.matches;
        if (desk) { if (dd.parentElement !== rh) rh.insertBefore(dd, rh.children[1] || null); }
        else if (dd.parentElement !== rm) rm.insertBefore(dd, rm.firstChild);
        if (rs) rs.classList.toggle('ddhead', desk);
      };
      if (dd && rh && rm) {
        place();
        if (mq) { try { mq.addEventListener('change', place); } catch (e) { /* 舊瀏覽器：照初始位置 */ } }
      }
    }
    let segFilter = opts.seg || null;
    /* ★ 2026-10-03（Andy 看「一般電子 → CNC 工具機」：上面是工具機拆解圖，下面關聯圖卻是 IC 設計、面板、被動元件……
       原話：「這兩張圖關係要對上，若無關則下方不需顯示」）。
       relScope ＝上方這張剖析圖上**真的掛了 data-seg 的環節** ∩ 這條鏈在 supply_chain.yaml 的環節：
         · 族群總覽分頁（沒有剖析圖）→ null，整條鏈、沒有反亮
         · 交集是空的（CNC 工具機、工業自動化、寬能隙、矽晶圓這幾張圖刻意一個 data-seg 都不掛，
           因為 supply_chain.yaml 沒有對應的環節）→ 整塊「供應鏈關聯圖」藏起來，不顯示一張無關的圖
       ★★ 同日晚（Andy：「下方的關聯圖為何其他的都不見了，需要有對應那族群的所有關聯圖，並且反亮那族群」，DECISIONS #317）：
         交集非空時**不再只留那幾格**（#306 第 3 節的「只留交集」推翻）—— 關聯圖、手機環節清單、「環節 ▾」下拉一律畫整條鏈，
         relScope 改當「反亮」用：那幾格亮框亮底、其餘降到 60% 透明度（仍可讀、可點），關聯圖框自己捲到反亮的那幾欄。
       ⚠ 只用既有資料，不新增、不推測任何供應關係。*/
    let relScope = null;
    let applyRelScope = () => {};       // 有關聯圖時在下面接上；swapDiagram（換圖不換網址）也會呼叫它
    const relScopeNow = () => {
      if (!dgId) return null;
      const host = $('#prodDiagram', el); if (!host) return null;
      const inChain = new Set(segs.map(s => s.id)), on = new Set();
      $$('[data-seg]', host).forEach(n => { if (inChain.has(n.dataset.seg)) on.add(n.dataset.seg); });
      return on;
    };
    /* ★ 2026-09-23 第二批（Andy 點名）：下方那張「成分股」卡片整塊移除。
       連同 renderMembers／COLS／排序記憶／市場別 seg／展開更多／放寬蓋住事件面板 一起拿掉 ——
       它們只服務那張表，留著就是留一堆沒有人看得到的程式碼。
       它承載的事情沒有消失，只是換了地方回答同一個問題「這一格裡面誰在漲」：
         · 族群層級 → 族群總覽分頁的族群漲幅長條圖＋占比圓餅圖（`renderGroupPanel`）
         · 個股層級 → 在長條圖上點一個族群，原地換成該族群所有個股的漲幅長條圖，點一條就進個股頁
         · 某一個環節有哪幾檔 → 環節詳情 `#segBox`（台股／外商／相關族群，全部可點）
       ⚠ segFilter／state.group **沒有**跟著拿掉：剖析圖高亮與關聯圖還在讀它們。*/
    /* 點剖析圖上的零件只做「亮起來 + 在原地說明這個環節」，
       不捲動、也不把整張圖聚焦到那一格 —— Andy：「當我點擊圖片時，不用馬上切換到下方股票」。
       要真的聚焦到某一格，用圖上的環節色標、關聯圖的大圓點，或零件小卡裡那顆「環節 →」。 */
    let segHi = null;
    /* partHi ＝**剛剛被點的那一個零件**（`data-part`，或 stampParts 自動補的 key）。
       為什麼要跟 segHi 分開：高亮以前只有環節這一層，所以「點一個零件」在程式裡
       等於「選一個環節」—— 多環節的圖還說得通，但**單一環節的圖**
       （MLCC 14 個零件全是 passive_comp，後面 13 張多數也是）就變成
       「14 個全部 .sel、0 個 dim」＝ 點下去畫面沒有任何事情發生。
       分成兩層之後：被點的那一個最強（.sel-part）、同環節其餘次強（.sel）、其餘 dim。
       ★ 這仍然只是「亮」，不是「篩」—— DECISIONS #73 沒有被動到。*/
    let partHi = null;
    /* partSel ＝「小卡現在在講哪一個零件」。為什麼要跟 partHi 分開：
       partHi 只是「高亮的主角」，而 segHi 也會被**關聯圖上的環節標題**設起來
       （drawChainMap 的 onSegment）—— 那不是「點零件」，不該彈出零件小卡。
       所以只有 pickPart（點剖析圖或 3D 的零件）會寫 partSel，其餘一律清掉。*/
    let partSel = null;
    let pcOpen = partCardOpen();        // 小卡收合狀態（localStorage 記住）
    const syncHighlight = (opt) => {
      const o = opt || {};
      const shown = segFilter || segHi;
      const segsOn = shown ? [shown] : (state.group ? (A.L.gsegs[state.group] || []) : []);
      const color = shown ? segColor(shown) : (state.group ? A.L.gcolor[state.group] : null);
      /* ★ #317：剖析圖分頁打開時 state.group 常常就是這張圖的族群（晶圓代工、HBM…），以前會把關聯圖上其他環節的公司卡壓到 0.28。
         現在那幾格已經由「反亮」標出來了，族群帶出來的選取就不再壓關聯圖（只在剖析圖上亮）——
         不然其餘環節會淡到讀不出字（要的是降 35～45%、仍可讀）。使用者自己點一格（segFilter／segHi）照舊壓。*/
      const mapOn = (shown || !(relScope && relScope.size)) ? segsOn : [];
      highlightSegments(el, segsOn, color, partHi, mapOn);
      // 切主題會整頁重畫，選取狀態要有人記得（見上面 `_dgSnap` 那段註解）
      _dgSnap = { dg: dgId, segHi, partHi, partSel, segFilter };
      /* 「這個零件是誰做的」小卡。只有點零件才畫（partSel），
         點環節色標／族群卡片走的是下面那個 segBox，兩者不互相取代。*/
      renderPartCard($('#partCard', el), el, sc, dgId, partSel && partSel.seg, partSel && partSel.key, {
        open: pcOpen,
        onToggle: () => { pcOpen = !pcOpen; setPartCardOpen(pcOpen); syncHighlight({ quiet: true, noscroll: true }); },
        // ✕＝取消選取這個零件（跟再點一次同一個零件同一個結果）
        onClose: () => { partHi = partSel = null; segHi = null; syncHighlight({ quiet: true, noscroll: true }); },
        /* 小卡上的「環節 →」是唯一一個「從零件走到篩選」的入口 ——
           它是一顆寫著環節名的按鈕，不是零件本身，所以 DECISIONS #73 沒有被動到。*/
        onSeg: (sg) => { segFilter = sg; segHi = null; partHi = partSel = null; state.group = null; syncHighlight(); },
      });
      /* noscroll：從關聯圖上「點公司」進來的那一條路。使用者的眼睛就在關聯圖上，
         再把圖捲到那一欄只會讓他剛剛點的那張卡片跑掉。點環節色標（在圖下面）才需要捲。*/
      if (segFilter && !o.quiet && !o.noscroll) scrollChainTo(el, segFilter);
      $$('#segChips .segchip', el).forEach(c => c.classList.toggle('sel', segsOn.includes(c.dataset.seg)));
      /* 清單版面：選到的那一節 .on、其餘淡一階（.hassel），一眼看得出「現在圖上亮的是哪一格」 */
      /* 下拉：「全部環節」那一列在沒選時亮；按鈕上寫目前選的是哪一格（選了族群就寫幾格） */
      { const all = $('#segChips .segall', el); if (all) all.classList.toggle('on', !segsOn.length); }
      { const bb = $('#segDDBtn b', el); if (bb) bb.textContent = !segsOn.length ? '全部'
          : (segsOn.length === 1 ? segName(sc, segsOn[0]) : `${segsOn.length} 格（${(A.L.gname[state.group] || '族群')}）`); }
      /* 右欄只列選中的那幾格；一格都沒選就整欄收掉（.hassel 由 CSS 決定要不要切成兩欄） */
      /* ⚠ 點剖析圖的零件（partHi）也會亮一格，但那時候**不開右欄**：右欄一開圖就變窄重畫、整頁高度跟著變，
         使用者明明在上面看剖析圖，下面的關聯圖卻整張跳一下（驗收「點零件不會把畫面捲走」就是在守這件事）。
         右欄只回應「真的選了一格」：下拉、點公司卡、點圖上的環節標題。*/
      const listOn = (partHi || partSel) ? (segFilter ? [segFilter] : []) : segsOn;
      $$('#relList .rlseg', el).forEach(c => c.classList.toggle('on', listOn.includes(c.dataset.seg)));
      { const rm = $('#relMain', el); if (rm) rm.classList.toggle('hassel', listOn.length > 0); }
      /* 說明卡浮在圖上（2026-09-26 晚）：開關狀態定了之後，依被點的那一格決定貼左還是貼右（見 placeRelCol） */
      placeRelCol(el);
      /* 退版之後「選起來」的視覺回到分層圖的公司卡與環節卡清單上，
         由 highlightSegments 一次做完（它同時處理剖析圖、分層圖、環節卡）。*/
      /* 環節詳情 `#segBox` ＝ Andy 說的「點擊後才會跳出的下拉清單」：
         Default（沒選任何一格）時它是空的、高度 0；點色標或環節卡才展開。
         它跟右側資訊欄 `#coBox.relside` 是兩件事：資訊欄講「某一檔公司」，
         環節詳情講「某一格環節」，各自有自己的位置，不互相取代。*/
      renderSegBox($('#segBox', el), sc, shown, ch, { filtered: !!segFilter, onFilter: () => {
        segFilter = shown; segHi = null; partHi = partSel = null; state.group = null; syncHighlight();
      } });
      /* 族群換了就換圖。★ 2026-09-21：換到「沒有圖」也是一種結果 ——
         選到還沒有專屬剖析圖的族群（例：面板），圖真的收起來、換回圖別選單，
         **不會**退回別的族群的圖。沒換就什麼都不做（不會閃）。*/
      swapDiagram(resolveDg());
    };
    /* ★ 2026-09-21 拿掉了「你選的族群還沒有專屬剖析圖，這張是這條鏈目前有的那一張」。
       那句話是在**替一個不該發生的行為道歉**（跨族群退回）。現在不會再退回了：
       選到沒有圖的族群＝收起圖、換回圖別選單，所以那句文案永遠不會出現，留著只是噪音。
       改成永遠寫「這張圖回答什麼問題」—— 每張圖都要能回答一個具體問題，而且要寫在旁邊。*/
    function paintDgTitle() {
      const t = $('#dgTitle', el), q = $('#dgQ', el) || document.getElementById('dgQ');   // 「?」開著時 #dgQ 在 #howPop 裡
      if (t) {
        /* 說明精簡：圖名＋誠實標示留在畫面；「點零件看供應商／原尺寸可左右滑」搬進「怎麼看 ?」 */
        t.textContent = dgId
          ? `${DS.name(dgId)}　·　原創示意圖，非實物比例`
          /* 沒有選圖＝正在看族群總覽。以前這裡寫「在下面選一張」是指圖別選單，
             選單移除之後要改成指**上方的分頁列**，不然會叫使用者去看一個不存在的東西。*/
          : `共 ${dgOpts.length} 張剖析圖`;
      }
      // 「?」彈窗的標題＝這張圖的名字（跟總覽一樣：彈窗標題＝卡片／區塊名稱）
      { const qb = $('.howbtn[data-how="dg"]', el); if (qb) qb.dataset.ttl = dgId ? DS.name(dgId) : '產品剖析圖'; }
      if (q) q.innerHTML = (dgId && DS.q(dgId)) ? `<b class="howq">${A.fmt.esc(DS.q(dgId))}</b>` : '';
    }
    /* 「族群總覽」與「剖析圖」兩種模式的顯示切換。
       用的是 hidden 屬性，但 .row 這幾個有 display 規則的類別會蓋掉
       UA 預設的 [hidden]{display:none}，所以 index.html 裡補了對應的收尾規則。
       ★ 2026-09-23 第二批（W3-7，Andy：「下方的字卡也拿掉 因為上方分頁就有同樣功能了」）：
         圖別選單 `#dgMenu` 整塊移除。它跟二層分頁列是**同一份東西畫兩次** ——
         兩邊都是拿 `dgOpts` 與 `dgHash(id)` 產生的，連網址都一模一樣。
         資訊沒有消失：圖名的完整版與「這張圖回答什麼問題」掛在分頁的 `title=` 上（見 W3-4），
         進到圖裡之後 `#dgQ` 那一行也會把問題寫出來。*/
    function paintDgMode() {
      const on = !!dgId;
      const body = $('#dgBody', el), tools = $('#dgTools', el);
      if (body) body.hidden = !on;
      if (tools) tools.hidden = !on;
      /* ★ 2026-09-25（R3 審查）：族群總覽分頁底下多出一行「共 N 張剖析圖，在上方分頁選一張」——
         那是剖析圖區的標題列，工具鈕藏起來之後只剩這句孤零零掛在長條圖下面，像是漏刪的字。
         上方分頁列本來就列著每一張圖，這句沒有新資訊，所以沒選圖時整列收起來。*/
      const sh = $('.dgsechead', el);
      if (sh) sh.style.display = on ? '' : 'none';     // .row 有 display:flex，hidden 屬性蓋不過它
      /* 說明精簡：「?」住在圖名旁（.dgsechead），回族群總覽時整列收起來 —— 盒子也要一起收，不然會留一段舊圖的說明。
         ★ 2026-09-26 改成跳出式「?」：鈕上的字固定是「?」，不再改回「怎麼看 ?」。*/
      if (!on) { const hb = $('#how-dg', el), hbtn = $('.howbtn[data-how="dg"]', el);
        if (hb) hb.hidden = true; if (hbtn) { hbtn.classList.remove('on'); hbtn.setAttribute('aria-expanded', 'false'); } }
      // 族群總覽（第一個分頁）與剖析圖互斥：沒有選任何一張圖的時候就是它
      const gp = $('#gpSec', el);
      if (gp) gp.hidden = on;
      /* ★ C1：「← 族群總覽」`#dgBack` 已移除 —— 分頁列第一格就是族群總覽，
         同一個目的地留一顆鈕就好（跟上一批移除「← 返回」同一個理由）。*/
      paintTabs();
      paintDgTitle();
    }
    /* 二層分頁的選取狀態。`.sel` 是既有的（換圖邏輯與驗收都認它），
       `.on` 是活頁簿外觀用的；兩個一起切，不要只切一個。*/
    function paintTabs() {
      $$('#dgPick .segchip', el).forEach(c => {
        const sel = c.dataset.dgtab === 'overview' ? !dgId : c.dataset.dgid === dgId;
        c.classList.toggle('sel', sel); c.classList.toggle('on', sel);
      });
      scrollTabIntoView($('#dgPick', el));
    }
    /* 點零件（2D 剖析圖與 3D 場景共用這一支）。
       ★ 跟舊版的差別：以前是「再點同一個 **環節** 就取消」，所以在單一環節的圖上
         點第二個零件會把整個選取取消掉（14 個零件全是同一個環節）——
         使用者以為自己點到了別的零件，畫面卻整個暗下來。
         現在是「再點同一個 **零件** 才取消」，點別的零件就是把主角換過去。*/
    const pickPart = (seg, key) => {
      if (key && partHi === key) { partHi = partSel = null; segHi = null; }
      else if (!key && segHi === seg) { partHi = partSel = null; segHi = null; }
      else { partHi = key || null; segHi = seg; }
      // 只有「真的選起來了」才有小卡；再點一次同一個零件＝取消，小卡跟著收掉
      partSel = (partHi || segHi) ? { seg, key: key || null } : null;
      segFilter = null;
      syncHighlight({ quiet: true });
    };
    /* 點背景 ＝ 回到 Default：全部零件恢復全亮、零件小卡收掉（Andy 2026-09-22）。
       ⚠ **刻意不動 segFilter** —— 那是環節色標的「篩選」，跟零件的「高亮」是兩件事。
         把它一起清掉的話，使用者只是想退出零件選取，圖下方的環節詳情卻莫名其妙整個收掉。
       已經是 Default 就什麼都不做：避免每點一次背景就重畫一次環節詳情。
       noscroll：使用者的眼睛在圖上，不要把頁面捲到別的地方去。*/
    const clearPart = () => {
      if (!partHi && !segHi && !partSel) return;
      partHi = partSel = segHi = null;      // partSel 是小卡的狀態，忘了清小卡就收不掉
      syncHighlight({ quiet: true, noscroll: true });
    };
    /* ★ 2026-09-24（Andy：「不需要"收起"選項，點擊背景即可消除（每個點擊資訊都確保是這樣功能）」）：
       零件小卡登記進全站那一份「點外面就關、按 Esc 也關」（app.js 的 dismissable）。
       剖析圖那一整區（含 3D／拖曳／重設／動畫／收合那排鈕）與關聯圖**不算外面**：
       圖上點背景本來就會 clearPart（上面那段），而按 3D、換拖曳模式時「選起來的零件不准弄丟」是既有的決定。
       所以「外面」指的是這兩區以外（頁首、族群總覽、其他產業鏈那排…），外加任何地方按 Esc。*/
    if (A.dismissable && $('#partCard', el)) {
      A.dismissable($('#partCard', el), clearPart, { ignore: ['#dgSec', '#relSec', '.dgtabs', '#chainSwitch'],
        isOpen: () => !!partSel && el.isConnected && !$('#partCard', el).hidden && $('#partCard', el).getClientRects().length > 0 });
    }
    /* 環節色標 `#segChips`（2026-09-23 C5 退版之後回到圖的上方，不再藏在「篩選」面板裡）：
       點一下篩、再點一下取消。內容是上面那個區塊填的，這裡只掛事件。*/
    /* ★ 2026-09-24：色標住進下拉之後，選好一格就把下拉收起來（跟資金輪動卡的下拉同一個手感）。
       「全部環節」＝取消選取；右欄標題的 × 也是取消選取。*/
    $$('#segChips .segchip', el).forEach(c => c.onclick = () => { segFilter = segFilter === c.dataset.seg ? null : c.dataset.seg; segHi = null; partHi = partSel = null; state.group = null; if (segDDOpen) segDDOpen(false); syncHighlight(); });
    { const all = $('#segChips .segall', el);
      if (all) all.onclick = () => { segFilter = null; segHi = null; partHi = partSel = null; state.group = null; if (segDDOpen) segDDOpen(false); syncHighlight({ quiet: true }); }; }
    $$('#relList .rlx', el).forEach(x => x.onclick = () => { segFilter = null; segHi = null; partHi = partSel = null; state.group = null; closeCoBox(); syncHighlight({ quiet: true }); });
    /* ★ 2026-09-26（Andy：「點擊背景後說明欄會消失」）：關聯圖右邊那張「● 晶圓代工 3 檔 …」說明卡
       （#relList 選中的那一節）、公司資訊欄 #coBox、窄畫面的環節詳情 #segBox，以前只有 × 關得掉。
       改成跟零件小卡一樣登記進全站那一份 dismissable：點圖的空白處、點頁面其他地方、按 Esc 都收，
       收的時候**連選取一起取消**（圖上的 .dim／.sel 高亮全部恢復）—— 跟按 × 是同一個結果，不另寫一套。
       「不算外面」的地方，每一個都是「點了本來就會改選取」的入口，不能被當成點背景而抵銷：
         · 圖上的公司卡／個股標籤（.co）、環節標題（.segtitle）、▸▾ 收合鈕與「全部收合」列
         · 「環節：全部 ▾」下拉（#segDD）、關聯圖標題列（分層／流向切換、收合圖、怎麼看）
         · 手機的環節卡清單（#chainList）、剖析圖那一整區（點零件／背景有自己的 pickPart／clearPart，
           而且「點剖析圖背景不動 segFilter」是既有決定，見 clearPart 的註解）、族群總覽（#gpSec，點長條＝換族群）、
           兩層分頁列（換頁本來就會重畫）
       ⚠ 圖的邊線（.edge）、環節底下那幾行小字（.segnote）算背景：它們不是節點也不是標籤，點了本來就沒有反應。*/
    const relStick = $('#relStick', el), segBox0 = $('#segBox', el), relMain0 = $('#relMain', el);
    if (A.dismissable && relStick) {
      const clearRel = () => {
        if (!segFilter && !segHi && !state.group && !document.getElementById('coBox')) return;
        segFilter = null; segHi = null; partHi = partSel = null; state.group = null; closeCoBox();
        syncHighlight({ quiet: true, noscroll: true });
      };
      const relDz = A.dismissable(relStick, clearRel, {
        also: [segBox0].filter(Boolean),
        ignore: ['.chainmap .co', '.chainmap .segtitle', '.chainmap .segfold', '.chainmap .foldbar', '#segDD', '#relHead',
          '#chainList', '#segTools', '#coBox', '#dgSec', '#gpSec', '.dgtabs', '#dgPick', '#chainSwitch'],
        /* 開著＝右欄真的攤開（.hassel）、公司資訊欄在、或窄畫面的環節詳情有內容。
           ⚠ 不能用預設的「el 看不看得到」：桌機沒選時 .relcol 是 display:none，窄畫面 .relstick 是 display:contents（沒有框）。*/
        /* ⚠ 「環節 ▾」下拉開著時一律當成「沒開」：一層一層收 —— 下拉開著時按 Esc／點外面只收下拉（它自己接），
           說明卡留著；再按一次才收說明卡。不然使用者只是想關掉下拉，選好的那一格卻跟著一起不見。
           （判斷放在 isOpen：dismissable 在 pointerdown 當下與 Esc 當下都是用它挑「要關誰」。）*/
        isOpen: () => relStick.isConnected && !($('#segDD', el) && $('#segDD', el).classList.contains('open')) && (
          !!(relMain0 && relMain0.classList.contains('hassel'))
          || !!document.getElementById('coBox')
          || !!(segBox0 && segBox0.childElementCount && segBox0.getClientRects().length)),
      });
      /* 關聯圖在窄畫面是左右滑的（SVG 有 min-width）。按住它自己的捲軸拖，pointerdown 的 target 是 #chainMap 這個 div、
         座標落在內容寬高之外 —— 那是在捲圖，不是點背景。dismissable 的 pointerdown 在 document 的 capture 階段先跑，
         這裡（冒泡階段）再把這一筆標成 dirty，dzFinish 看到 dirty 就不關。*/
      const mh = $('#chainMap', el);
      if (mh && relDz) mh.addEventListener('pointerdown', (ev) => {
        if (ev.target === mh && (ev.offsetX >= mh.clientWidth || ev.offsetY >= mh.clientHeight)) relDz.dirty = true;
      });
    }
    /* ★「放寬 ⤢」（成分股暫時蓋住今日事件面板）跟著成分股表一起移除 ——
       它是為了那張表才存在的，表沒了就沒有服務對象。
       ⚠ **`show()` 裡「換頁還原事件面板」那段收尾不准拿掉**（見檔案上方）：
         使用者可能是在上一版按下放寬之後才重新整理／換頁進來的，
         body 上還掛著 `.memwide` 卻再也沒有人會把它拿掉，事件面板就永遠卡在被蓋住的狀態。*/
    // E5：上方切換列（2026-09-23 改成活頁簿分頁）—— 按了直接換一條鏈，不用退回產業地圖
    wireChainTabs(el, ch.id);
    /* ================= 供應鏈關聯圖（2026-09-23 C5 退版＋優化） =================
       退版回 a846f16 的分層形式，並補上舊版四個毛病：
         ① 舊版 SVG 有 `max-width: W×1.25`，1358px 的容器只用掉左邊 1020px、右邊空一大塊 ——
            現在欄寬與欄距依容器寬度算，內容水平置中、撐滿率 ≥ 90%（`drawChainMap` 裡有量測用的
            `data-fill` / `data-dx`，驗收就是讀它們再自己用 getBoundingClientRect 對一次）。
         ② **分層圖**（節點＝公司卡，依環節排成直欄，上游→下游由左往右，固定走線帶箭頭）是唯一的畫法。
            ★ 2026-09-26 Andy：「刪除流向圖」—— 2026-09-23 做成可切的第二種畫法「流向圖」（節點＝環節、
            帶寬＝兩格之間的關係條數）整個拿掉：標題列的「分層圖｜流向圖」切換、drawSegFlow、
            「怎麼看 ?」裡流向圖那一段、樣式一起刪。localStorage 以前記過的 `tw.relView`（'flow'）
            一律不讀，順手清掉，免得留一個再也沒有人用的值。
         ③ Default 畫面就要看得到「這一格的上游是誰、下游是誰」與底下的個股標籤 —— 那是 `#chainList`。
         ④ 環節詳情與跨鏈對照預設收起（`#segBox` 是空的），點色標／點環節卡才展開。
       點個股標籤或公司卡 → 右側 `#coBox.relside` 資訊欄（窄畫面 <1100px 自動掉到圖下方）。*/
    if (hasMap && sc) {
      /* 點環節卡＝「我要看這一格」（真的篩），刻意跟「點剖析圖零件」（只亮不篩，DECISIONS #73）分開。*/
      const segPick = (seg) => { segFilter = segFilter === seg ? null : seg; segHi = null; partHi = partSel = null; state.group = null; syncHighlight(); };
      /* 點個股標籤：原地開右側資訊欄（不跳頁，N7），同時把它所屬的環節選起來。
         noscroll ＝ 使用者的眼睛就停在剛剛點的那張標籤上，不要把頁面捲走。*/
      const coPick = (co) => { if (!co || !co.segment) return; segFilter = co.segment; segHi = null; partHi = partSel = null; state.group = null; syncHighlight({ noscroll: true }); };
      relScope = relScopeNow();
      const scopeFocus = () => relScope;      // 反亮的那幾格（null＝族群總覽，沒有反亮）
      let stat = drawSegList($('#chainList', el), sc, ch.id, im, { onSegment: segPick, onCompany: coPick, focus: scopeFocus });
      const mapHost = $('#chainMap', el);
      try { localStorage.removeItem('tw.relView'); } catch (e) { /* 私密視窗：讀不到也寫不了，本來就不會用它 */ }
      /* ★ 2026-09-24 說明精簡：圖的說明改成條列，住在「怎麼看 ?」（#how-rel）裡；圖例口徑放最下面一行小字。
         （2026-09-26 流向圖拿掉之後只剩分層圖這一份。）*/
      const HINT = {
        layer: (st) => A.howHTML('這條鏈由哪幾格組成、每一格有誰、誰供貨給誰。', [
          st,
          '怎麼用：左上游、右下游，先找你那檔',
          '往左看誰在供貨（常慢一兩天才反應）',
          '往右看它賣給誰（下游轉弱會被拖到）',
          '線越粗依存度越高；虛線＝委外、點虛線＝指定料號',
        ]),
      };
      /* 容器寬度變了就要重畫：欄寬、欄距、左右內距全部是依容器寬度算出來的。
         最常見的觸發不是改視窗，是**點一檔個股** —— 右側資訊欄（340px）一出現，
         圖的容器就從 998px 縮到 646px，不重畫的話剛剛量好的置中當場歪掉、內容還會溢出。
         `lastW` 是防止 ResizeObserver 自己咬自己：重畫會改 SVG 高度、又觸發一次觀察。*/
      let lastW = -1;
      const drawMap = () => {
        if (!mapHost) return;
        lastW = mapHost.clientWidth;
        drawChainMap(mapHost, sc, ch.id, im, {
          focus: scopeFocus,
          onSegment: (seg) => { segHi = segHi === seg ? null : seg; segFilter = null; partHi = partSel = null; syncHighlight({ quiet: true }); },
          /* 點公司＝連同它所屬的**環節**一起選起來（不是族群）：一家公司只有一個 segment，
             卻可能掛好幾個族群，選族群就得替他猜一個。環節推族群是自動成立的（A.L.sgroups）。*/
          onFold: () => syncHighlight({ quiet: true, noscroll: true }),
          onCompany: (co) => { if (!co || !co.segment) return; segFilter = co.segment; segHi = null; partHi = partSel = null; state.group = null; syncHighlight({ noscroll: true }); },
        });
        const hint = $('#relHint', el) || document.getElementById('relHint');   // 「?」彈窗開著時盒子在 #howPop 裡
        if (hint) hint.innerHTML = HINT.layer(relScope && relScope.size
          ? `這條鏈 ${stat.nSeg} 格、${stat.nTw} 檔台股、${stat.nEdge} 條上下游關係；亮框＝上方剖析圖畫到的 ${relScope.size} 格`
          : `這條鏈 ${stat.nSeg} 格、${stat.nTw} 檔台股、${stat.nEdge} 條上下游關係`);
      };
      /* ★ 2026-09-25 效能（perf-2）：關聯圖在剖析圖下面（1440×900 首屏看不到），改成捲近了（或瀏覽器閒下來）才畫。
         以前跟剖析圖在同一個任務裡畫：drawMap 一開頭讀 clientWidth，逼整頁（含剛插進去的剖析圖）當場排版，
         實測首次開 #industry/semiconductor 這一支自己 202ms。已經在畫面裡（窄畫面、沒有剖析圖的鏈）就跟以前一樣當場畫。
         延後畫完要把目前的選取狀態補畫上去（syncHighlight 宣告在後面，當場畫的那一次交給 renderChain 最後那一行）。*/
      /* ⚠ 不用 App.whenNear：它一進來就讀 getBoundingClientRect 判斷「在不在首屏」—— 那本身就是這裡要避開的強制排版。
         上面有剖析圖（桌機、這條鏈有圖）時關聯圖一定在首屏以下，直接交給 IntersectionObserver ＋ 閒置補畫；
         沒有剖析圖或手機寬時照舊當場畫。*/
      const mapBelow = !!(mapHost && hasSlots && dgId && window.innerWidth > 640);
      /* 範圍的兩個出口：整塊藏起來（交集是空的）、整條鏈＋反亮那幾格（DECISIONS #317）。只有反亮的範圍真的變了才重畫。*/
      let relKey = relScope ? [...relScope].sort().join(',') : '*';
      const paintRelScope = () => {
        const rs = $('#relSec', el);
        if (rs) rs.hidden = !!relScope && relScope.size === 0;
        /* 「環節 ▾」下拉（手機是那排色標）列整條鏈，反亮的那幾格加 .relfocus（CSS 在後面補一顆「圖上」標記）。
           不再 display:none —— 那是 #306「只留交集」的做法。*/
        $$('#segChips .segchip[data-seg]', el).forEach(c => {
          c.style.display = '';
          const on = !!(relScope && relScope.has(c.dataset.seg));
          c.classList.toggle('relfocus', on);
          if (on) c.setAttribute('data-focus', '圖上'); else c.removeAttribute('data-focus');
        });
      };
      paintRelScope();
      applyRelScope = () => {
        relScope = relScopeNow();
        paintRelScope();
        const key = relScope ? [...relScope].sort().join(',') : '*';
        if (key === relKey) return;
        relKey = key;
        stat = drawSegList($('#chainList', el), sc, ch.id, im, { onSegment: segPick, onCompany: coPick, focus: scopeFocus });
        if (lastW >= 0 && !(relScope && relScope.size === 0)) drawMap();          // 還沒畫過（延後畫）就等輪到它
        syncHighlight({ quiet: true, noscroll: true });
      };
      if (mapBelow) deferNear(mapHost, () => { if (!mapHost.isConnected) return; drawMap(); syncHighlight({ quiet: true, noscroll: true }); });
      else drawMap();
      // 滑過環節的說明框（圖上的環節標題、沒有台股那格的說明共用一個）
      wireSegTip($('#relSec', el), sc, ch.id);
      /* 收合關聯圖：手機（<640px）預設收起來 —— 分層圖在 390px 上是要左右滑的，
         而 Default 真正要給人看的是下面那份環節卡清單（有上下游與個股標籤）。
         桌機預設展開；選擇記在 localStorage，跟剖析圖那顆是同一種做法。*/
      const foldRel = $('#relFold', el);
      let relOpen = window.innerWidth >= 640;
      try { const v = localStorage.getItem('tw.relOpen'); if (v != null) relOpen = v === '1'; } catch (e) { /* 忽略 */ }
      const paintRelFold = () => {
        if (mapHost) mapHost.hidden = !relOpen;
        /* 清單平常與圖等高（它自己的高度不算進版面）；圖收起來之後沒有「圖的高度」可以對齊，
           .mapfold 讓清單改成佔滿整列、用自己的高度（上限 70vh）—— 不然收合圖會連清單一起收成 0。*/
        const rm = $('#relMain', el); if (rm) rm.classList.toggle('mapfold', !relOpen);
        if (foldRel) { foldRel.textContent = relOpen ? '收合圖 ▴' : '展開關聯圖 ▾'; foldRel.classList.toggle('cyan', !relOpen); }
        placeRelCol(el);        // 圖收起來 → 卡片回到文件流（清掉浮動座標）；展開 → 重新貼回圖上
      };
      if (foldRel) foldRel.onclick = () => {
        relOpen = !relOpen;
        try { localStorage.setItem('tw.relOpen', relOpen ? '1' : '0'); } catch (e) { /* 忽略 */ }
        paintRelFold();
        // 收起來的時候量不到寬度，展開的當下要重畫一次，不然欄寬還是收合前算的那一份
        if (relOpen) { drawMap(); syncHighlight({ quiet: true, noscroll: true }); }
      };
      paintRelFold();
      /* 容器寬度變了就重算（改視窗、開關右側資訊欄、開關事件抽屜都算）。
         8px 的死區：捲軸出現／消失那種一兩個 pixel 的抖動不值得重畫一整張圖。
         換頁時 `el` 已經不在文件裡，用它當存活判斷把 observer 自己收掉。*/
      let rt = null;
      /* ★ 存活判斷一定要看 `mapHost`，**不可以看 `el`**。
         `el` ＝ `#indChain`，它是**常駐的容器**：換一條鏈只是換它的 innerHTML，
         元素本身永遠 isConnected。第一版寫成 `el.isConnected` 的下場是：
         上一條鏈的 observer 永遠拆不掉，換頁時舊 mapHost 被移除觸發它，
         它就用**上一條鏈的閉包**呼叫 syncHighlight → swapDiagram，
         把**新那一頁**的剖析圖整張換掉（實測：從半導體切到
         `#industry/ai_server/dg/ai_server`，機櫃圖整張不見，要重新整理才回來）。
         `mapHost` 是這一次 render 產生的節點，innerHTML 一換它就 isConnected=false，
         所以它才是「這一輪還算不算數」的正確判準。*/
      const alive = () => !!(mapHost && mapHost.isConnected);
      const reflow = () => {
        if (!alive()) { if (ro) ro.disconnect(); window.removeEventListener('resize', reflow); return; }
        if (lastW < 0) return;            // 還沒畫過（延後畫，見上面 whenNear）：輪到它畫時會自己量寬度
        if (!relOpen || Math.abs(mapHost.clientWidth - lastW) < 8) return;
        clearTimeout(rt); rt = setTimeout(() => {
          if (!alive() || !relOpen) return;
          drawMap(); syncHighlight({ quiet: true, noscroll: true });
        }, 120);
      };
      let ro = null;
      if (window.ResizeObserver && mapHost) { ro = new ResizeObserver(reflow); ro.observe(mapHost); }
      window.addEventListener('resize', reflow);
      /* 圖在窄畫面會左右滑（SVG 有 min-width）：滑了之後被點的那一欄在畫面上的位置變了，說明卡要跟著重新挑邊，
         不然滑過去就變成蓋在那一欄上面。一幀最多算一次。*/
      if (mapHost) { let pq = false; mapHost.addEventListener('scroll', () => {
        if (pq) return; pq = true; requestAnimationFrame(() => { pq = false; if (mapHost.isConnected) placeRelCol(el); }); }, { passive: true }); }
    }
    if (hasSlots && sc) {
      /* 手機（<640px）預設把剖析圖收起來。
         Andy 抱怨過兩次「上下框度太長」，而一張剖析圖在 390px 上就是 1000px 高 ——
         一般電子鏈補上 MLCC 之後，390px 的整頁從 3944 直接變成 6082（_uitest 當場紅）。
         收起來不是把功能拿掉：鈕就在標題旁邊，按一下就展開，而且會記住。
         640px 這條線刻意比 820px（手機版面斷點）低 —— 800px 的筆電半視窗仍然直接看得到圖。*/
      const foldBtn = $('#dgFold', el), dgBody = $('#dgBody', el);
      dgOpen = window.innerWidth >= 640;
      try { const v = localStorage.getItem('tw.dgOpen'); if (v != null) dgOpen = v === '1'; } catch (e) { /* 忽略 */ }
      /* ★ 直接走到某一張圖自己的網址（#industry/<chain>/dg/<slot>）＝使用者明確說
         「我就是要看這張」。手機的預設收合是給「順著鏈逛進來」的人省高度用的，
         不該蓋掉明確的意圖 —— 否則從圖別選單點一張圖進來，看到的是一顆收合鈕。*/
      if (dgExplicit) dgOpen = true;
      /* ★ 手機 v3（≤640px，docs/mobile_v3_spec.md §9 第 1 條）：剖析圖預設**展開**。
         當初收合的理由是「字卡把圖撐到 1000px 以上」；手機 v3 字卡拿掉、只留編號之後圖只剩約 300px，
         收合反而讓這一頁的主角要多點一下才看得到。手機上「收合圖」那顆鈕也一起藏起來（index.html）。
         桌機（>640）不走這一行。*/
      if (window.innerWidth <= 640) dgOpen = true;
      did3d = false;
      const dgSecEl = $('#dgSec', el);
      /* ★ 2026-09-23 第二批（W3-1 ＋ W3-9）：設定列改到**右上角**，
         而且是**跟標題同一列、靠右**（不是浮在圖上面）。

         第一版把它絕對定位在 `#dgSec` 的上緣內側，結果 `_preview.py` 當場量到
         `industry_chain` 頁文字重疊 —— 圖的右上角本來就有東西：
         「產品剖析圖 <圖名>」那一行標題。浮上去就是跟它搶同一塊。

         改成並排之後，三件事一起解決：
           ① 不可能再跟標題重疊（它們是同一列的兩個 flex 子元素，由版面決定位置）
           ② 也不可能蓋住圖的內容（它根本不在畫布上）
           ③ **`placeDgTools()` 與它那一整套防抖動機制可以整個拿掉** ——
              那套東西（8px／2px 死區、[300,1200,3000,5000] 的補算、對 #prod3d 與
              #prodDiagram 的 ResizeObserver、replaceDgTools 的多次重算）存在的唯一理由
              是「工具列浮在一個會非同步長高的畫布上，量到的高度隨時在變」。
              現在它在一般排版裡，瀏覽器自己會排好，沒有東西需要量、也沒有東西會抖。
              留著它就是留一套對著 `tools.style.top` 寫值、卻再也沒有人讀的死碼。
         ⚠ 2026-09-23 第十批 C1 之後這一排只剩「3D 立體／拖曳／重設視角／動畫／收合圖」五顆，
           `#dgBack`、`#dgPal` 已移除，所以「收合圖」不會再被擠到第二行。
         ⚠ 收合狀態（`.dgfold`）下工具列仍然在、仍然點得到 —— 它本來就在標題那一列，
           跟 `#dgBody` 的顯示與否無關，這比舊版的「絕對定位 ＋ .dgfold 退回一般排版」更穩。*/
      const paintFold = () => {
        if (dgBody) dgBody.style.display = dgOpen ? '' : 'none';
        /* 收起來之後 `#dgSec` 只剩一列標題，工具列再絕對定位在右下角就會飄到標題外面。
           `.dgfold` 讓它退回一般排版，**仍然在畫面上、仍然點得到**
           —— 不然「展開剖析圖」那顆鈕自己也不見了，圖就再也開不回來。*/
        if (dgSecEl) dgSecEl.classList.toggle('dgfold', !dgOpen);
        if (foldBtn) { foldBtn.textContent = dgOpen ? '收合圖 ▴' : '展開剖析圖 ▾'; foldBtn.classList.toggle('cyan', !dgOpen); }
        // 收起來的時候不要掛 3D：背景多一個 WebGL context 在空轉，手機最吃不消
        if (dgOpen && !did3d && dgId) { did3d = true; wireDg(); }
      };
      // 選單模式（dgId 為 null）沒有圖可以接線，wireDg 會對著空的 #prodDiagram 做事
      if (dgId) { wireDg(!dgOpen); did3d = dgOpen; }
      if (foldBtn) foldBtn.onclick = () => {
        dgOpen = !dgOpen;
        try { localStorage.setItem('tw.dgOpen', dgOpen ? '1' : '0'); } catch (e) { /* 忽略 */ }
        paintFold();
      };
      if (dgBody) dgBody.style.display = dgOpen ? '' : 'none';
      if (dgSecEl) dgSecEl.classList.toggle('dgfold', !dgOpen);
      if (foldBtn) { foldBtn.textContent = dgOpen ? '收合圖 ▴' : '展開剖析圖 ▾'; foldBtn.classList.toggle('cyan', !dgOpen); }
      /* 圖別切換晶片現在是**真的連結**（href＝那張圖自己的網址），所以不用再自己
         改 state —— 讓它走 hash 路由，跟圖別選單、跟直接貼網址完全同一條路。
         這樣「換一張圖」才會留下瀏覽紀錄（上一頁回得去）。*/
      paintDgMode();
    }
    // 換族群 → 換圖。放在 syncHighlight 之外自己判斷，沒換就什麼都不做（不會閃）
    function wireDg(skip3d) {
      applyDgNative($('#prodDiagram', el), dgId);
      paintDiagram($('#prodDiagram', el));
      // 剖析圖不加縮放：Andy 明講「產業與個股 剖析圖不用新增縮放功能」（本來就可以左右滑）
      wireDiagram(el, pickPart, clearPart);
      if (window.DG && window.DG.fillChips) window.DG.fillChips($('#prodDiagram', el), (seg) => { const tw = twOf(sc, seg);
        return { list: tw.slice(0, 4).map(c => ({ code: c.tw_code, name: c.name })), total: tw.length }; });
      /* 配色鈕：跟 3D 無關，只要這一頁上有剖析圖就該能按（2D 也要能換配色）。
         放在 skip3d 的 return 之前 —— 收合狀態下也要先接好，不然展開前按它是死的。*/
      wirePal(el, () => view3d);
      /* E4：動畫鈕現在同時管平面圖與 3D（Andy 2026-09-18：「3D 可切動態／靜止」）。
         以前它只把 SVG 加上 .noanim，切到 3D 之後這顆鈕等於是壞的。
         3D 的「動態」＝場景緩慢自轉 ＋ 風扇轉 ＋ 指示燈呼吸；「靜止」＝完全不自己動。*/
      const animBtn = $('#dgAnim', el);
      const setAnimAll = (on) => {
        const wrap = $('#prodDiagram', el);
        wrap.classList.toggle('noanim', !on);
        /* B4（art-director 2026-09-21）：`.dgwrap.noanim *{animation:none!important}` **只管 CSS 動畫**。
           processBar 那顆白點走的是 SVG 的 SMIL（<animateMotion>），CSS 完全管不到它 ——
           實測按下「動畫：關」之後白點照樣每 900ms 跑約 200px（x: 283.4 → 486.2 → 685.3）。
           SMIL 要用 SVG 自己的時間軸 API 停：pauseAnimations() / unpauseAnimations()。
           三張圖都在發作（流程列是共用函式），所以修在這裡而不是修某一張圖。*/
        wrap.querySelectorAll('svg').forEach(s => {
          try { if (on) s.unpauseAnimations(); else s.pauseAnimations(); } catch (e) { /* 舊瀏覽器沒這支就算了 */ }
        });
        if (animBtn) { animBtn.textContent = on ? '動畫：開' : '動畫：關'; animBtn.classList.toggle('cyan', on); }
        if (view3d && view3d.setAnim) view3d.setAnim(on);
        try { localStorage.setItem('tw.dganim', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
      };
      if (animBtn) animBtn.onclick = () => setAnimAll($('#prodDiagram', el).classList.contains('noanim'));
      setAnimAll(animPref());
      // wire3D 是模組層級的函式，看不到這裡的 segHi／segFilter／syncHighlight，
      // 所以把要用到的動作當參數傳進去（之前直接寫在函式裡會噴 syncHighlight is not defined）。
      if (skip3d) return;                 // 收合狀態下不掛 3D（展開時才補掛）
      wire3D(el, DS.scene(dgId), {
        onSeg: (seg, data) => pickPart(seg, data && data.part),
        // 3D 場景點空白處＝跟 2D 一樣回到 Default（Andy 2026-09-22 明講「3D 也要」）
        onBg: clearPart,
        sync: () => syncHighlight({ quiet: true }),
        /* 圖九 2-3（規格書 docs/diagram_specs/dg3d_standard.md）：
           3D 的文字框以前只有「零件名＋一行說明」，是死的。
           現在把該環節的台股掛上去，點了直接進個股頁 ——
           資料本來就在前端（twOf(sc, seg)），不用多抓任何東西。*/
        members: (seg) => { const tw = twOf(sc, seg);
          return { list: tw.slice(0, 4).map(c => ({ code: c.tw_code, name: c.name })), total: tw.length }; },
        onStock: (code) => A.goStock(code),
      });
    }
    /* 換一張剖析圖。刻意做成「淡出 → 換內容 → 淡入」180ms：
       直接換 innerHTML 會在畫面上閃一下白（SVG 很大，瀏覽器重排那一幀是空的）。
       swapping 這個旗標是因為 wireDg() 裡的 wire3D 會回頭呼叫 sync()，
       而 sync() 又會走到 swapDiagram —— 沒有旗標就會無限遞迴。*/
    function swapDiagram(next) {
      if (!hasSlots || next === dgId || swapping) return;
      const host = $('#prodDiagram', el); if (!host) return;
      swapping = true;
      dgId = next;
      partHi = partSel = null;          // 換一張圖，上一張的零件身分在新圖上不存在
      paintTabs();
      /* ★ 2026-09-21 新增的狀態：換成「沒有圖」。
         選到一個還沒有專屬剖析圖的族群（例：面板）時，以前會退回 MLCC 那張再加一句道歉；
         現在是**真的把圖收掉、換回圖別選單** —— 畫面上不會再出現一張不屬於這個族群的圖。
         沒有淡出淡入：這一步是「圖不見了」，淡出反而看起來像壞掉。*/
      if (!next) {
        dispose3D();
        const host3 = $('#prod3d', el), note3 = $('#dg3dNote', el);
        if (host3) { host3.hidden = true; clear3dHost(host3); }
        if (note3) note3.hidden = true;
        // ★ 配色不在這裡：它跟著全站主題自動走（見 wirePal），收掉 3D 不等於收掉配色
        ['dg3d', 'dg3dCtl'].forEach(id => { const b = $('#' + id, el); if (b) b.hidden = true; });   // 3D 視角那組鈕整組收（見 wire3D）
        host.hidden = false; host.innerHTML = ''; host.style.opacity = '1';
        paintDgMode();
        swapping = false;
        applyRelScope();      // 回族群總覽 → 關聯圖回到整條鏈
        return;
      }
      paintDgTitle();
      host.style.opacity = '0';
      setTimeout(() => {
        /* 換圖之前一定要先收掉 3D：新的那張可能根本沒有 3D 場景，
           不收的話畫面會停在上一張的 WebGL 場景上（看起來像換圖沒生效）。*/
        dispose3D();
        const host3 = $('#prod3d', el), note = $('#dg3dNote', el);
        if (host3) { host3.hidden = true; clear3dHost(host3); }
        if (note) note.hidden = true;
        // ★ 配色不在這裡：它跟著全站主題自動走（見 wirePal），收掉 3D 不等於收掉配色
        ['dg3d', 'dg3dCtl'].forEach(id => { const b = $('#' + id, el); if (b) b.hidden = true; });   // 3D 視角那組鈕整組收（見 wire3D）
        host.hidden = false;
        host.innerHTML = DS.draw(next);
        paintDgMode();        // 從「選單」換回「有圖」時要先把 #dgBody 打開，3D 才量得到尺寸
        wireDg(!dgOpen);      // 收合狀態下不要順手把 3D 掛起來（手機背景多一個 WebGL context）
        did3d = dgOpen;       // 收合時換的圖 3D 還沒接線 → 展開時 paintFold 要補接
        host.style.opacity = '1';
        swapping = false;
        applyRelScope();      // 換了一張圖 → 關聯圖的範圍跟著換（2026-10-03）
        syncHighlight({ quiet: true, noscroll: true });
      }, 180);
    }
    /* 第一個分頁：這條鏈的族群漲幅長條圖 ＋ 占比圓餅圖（Andy 2026-09-23）。
       掛在這裡而不是版面那一段，是因為它的 callback 要用到 syncHighlight／segFilter ——
       那兩個宣告在後面，太早掛會踩到 TDZ。
       · drillGid：從 `#industry/group/<gid>` 或關聯圖進來時，直接展開那個族群的個股長條圖
       · onGroup：點長條＝原地展開，同時把選取狀態換成這個族群（跟點關聯圖的大圓點同一條路）
       · onBack：回到族群層級，篩選一起還原 */
    renderGroupPanel($('#gpSec', el), {
      scope: ch.name, groups: groups, asOf: (im && im.date) || '',
      drillGid: state.group || null,
      onGroup: (gid) => {
        gpDrilled = true;
        state.group = gid; segFilter = null; segHi = null; partHi = partSel = null;
        syncDgHash(); syncHighlight({ noscroll: true });
      },
      onBack: () => {
        gpDrilled = false;
        if (state.group) { state.group = null; syncDgHash(); syncHighlight({ noscroll: true }); }
      },
    });
    // sc（supply_chain）還沒產出時上面那個 if 進不去，選單／圖的顯示狀態會沒人設過，
    // 所以在這裡統一再畫一次（重複呼叫是冪等的）
    if (hasSlots) paintDgMode();
    else { const gp = $('#gpSec', el); if (gp) gp.hidden = false; }
    /* 剛剛因為切主題被重畫掉的選取，在這裡放回去（同一張圖、3 秒內才算數）。
       放在第一次 syncHighlight 之前 —— 它會把高亮、零件小卡、環節詳情一次畫對。*/
    if (_dgKeep && _dgKeep.dg === dgId && Date.now() - _dgKeep.t < 3000) {
      segHi = _dgKeep.segHi; partHi = _dgKeep.partHi;
      partSel = _dgKeep.partSel; segFilter = _dgKeep.segFilter;
    }
    _dgKeep = null;                   // 領過就丟，免得之後逛回來又被還原一次
    syncHighlight();
  }
  // 環節說明盒：這個環節的台股（可點）、外商、相關族群（可點）
  // （`marketOf` 只服務成分股表的「上市／上櫃」篩選，表移除後一併拿掉）

  function renderSegBox(box, sc, seg, ch, opt) {
    if (!box) return;
    if (!seg || !sc) { box.innerHTML = ''; return; }
    /* ★ 2026-09-25 Andy：桌機（>820px）整塊環節資訊面板拿掉（標題列、台股、相關族群、跨鏈比較卡）。
       理由：右側 #relList 已經列出那一格的族群與個股，下拉「環節：」也看得到目前選哪一格，
       這塊在圖下方是第三份重複資訊；「已只看這一格」的取消交給下拉的「全部環節」。
       手機另有人處理，這裡只擋桌機 —— 用 matchMedia 而非 CSS 藏，才是真的「不存在」，
       不會留下一顆看不到但還能被 Tab 到的按鈕。*/
    if (window.matchMedia && matchMedia('(min-width: 821px)').matches) { box.innerHTML = ''; return; }
    const o = opt || {};
    const tw = twOf(sc, seg), fo = foreignOf(sc, seg), gids = A.L.sgroups[seg] || [];
    const s = sc.segments.find(x => x.id === seg) || {};
    box.innerHTML = `<div class="segbox" style="--c:${segColor(seg)}"><div class="row spread">
        <div><b class="t">${A.fmt.esc(s.name || seg)}</b> <span class="muted">${s.desc ? A.fmt.esc(s.desc) : ''}</span></div>
        <button class="btn small" id="segOnly">${o.filtered ? '已只看這一格' : '只看這一格 →'}</button></div>
      <div class="row"><span class="muted">台股</span>${tw.length ? tw.map(c => A.L.stock(c.tw_code, c.name)).join('') : '<span class="muted">沒有直接對應的台股</span>'}</div>
      ${fo.length ? `<div class="row"><span class="muted">外商</span>${fo.map(c => `<span class="pill" title="${A.fmt.esc((c.tech || []).join('、'))}">${A.fmt.esc(c.name)}</span>`).join('')}</div>` : ''}
      ${gids.length ? `<div class="row"><span class="muted">相關族群</span>${gids.map(g => A.L.group(g)).join('')}</div>` : ''}
      ${crossHtml(sc, seg, ch)}</div>`;
    const btn = $('#segOnly', box);
    if (btn) { btn.disabled = !!o.filtered; if (o.onFilter && !o.filtered) btn.onclick = o.onFilter; }
    paintCross(box, seg);
  }


  /* ================================================================ 「這個零件是誰做的」小卡
     docs/diagram_purpose.md §4。以前點零件只會亮 —— `segPick` 上面那段註解自己就寫了
     「使用者只是想知道『這個零件是誰做的』」，但程式碼從來沒有回答過這個問題。
     這張小卡就是那個答案：**這是什麼 → 屬於哪個環節 → 做這個的台股有誰（負責什麼）
     → 相關料號 → 台股沒人做的話是誰做的**，順序照 docs 那五條。

     ★ 它是「多給資訊」，不是「改掉既有行為」：DECISIONS #73 的「點零件只亮不篩」
       一個字都沒有動 —— 圖下方的環節詳情不會因為點零件而變，要聚焦仍然是點環節色標。

     兩層資料來源，順序是刻意的：
       ① 預設 —— 零件的 `data-seg` → 那個環節的台股（附 companies[].tech）＋
          流進／流出那一格的 edges[].item。**九張已經畫好的圖一行都不用改就馬上有東西看。**
       ② 精修 —— 那張圖在 `DG.register` 的定義裡宣告 `parts: { <data-part>: {...} }`，有就蓋掉預設。
          精修只住在繪圖端（`site/dg/<slot>.js` 與 `diagrams.js` 的 SLOTS），
          **不准寫進 `pipeline/groups/supply_chain.yaml`** —— 那份是 Andy 校訂的成分表。
     誠實（R4／R5）：查不到就寫查不到，`edges[].confidence` 照實顯示在畫面上，
     台股沒人做的一律用 `none` 明講是誰做的，不留白、也不湊一個對應出來。*/

  /* 樣式為什麼注入在這裡，而不是寫進 site/index.html 的 :root
     ------------------------------------------------------------
     這一輪同時有別的 agent 在改 `site/index.html`（配色）與 `site/diagrams.js` 的 MLCC 版面，
     那個檔一動就撞。DECISIONS #227 當時為了同一個理由把 native 的樣式寫成 inline；
     這裡要的是 media query 與多條子選擇器，inline 寫不了，所以改成注入一次。
     ⚠ 這是暫時的：等這一批合完，這段應該搬回 index.html 跟 .segbox 放在一起。
     顏色全部走既有變數與零件的環節色 `--c`，**一個色票都沒有寫死**。*/
  function ensurePartCss() {
    if (document.getElementById('partCardCss')) return;
    const st = document.createElement('style');
    st.id = 'partCardCss';
    /* ★ 小卡吃的是**剖析圖那一套** `--dg-*`，不是全站主題的 `--panel`／`--ink`。
       理由：它就貼在圖的正下方，屬於圖的一部分。
       2026-09-21 截圖看出來的：換成「休閒」配色之後圖是暖炭底，
       小卡卻還是深藍底＋青字（那是全站主題的色），兩塊貼在一起像兩個不同的網站。
       改成 `--dg-*` 之後，配色切到哪一個，圖跟卡一起換。
       ⚠ 淺色主題也一樣是深底 —— 那不是 bug：剖析圖的畫布本來就恆為深色
       （`--illus` 的既有決策），卡片跟著圖走才對得起來。
       文字一律用 `--dg-ink*`（三個配色都保證是亮色），所以不會踩到
       DECISIONS #198「淺色主題一堆白字白線」那個坑。
       語意色 `--amber`／`--fall` 刻意留著：資料可信度跟配色無關，而且兩個在深底上都讀得到。*/
    st.textContent = `
      .partcard{margin-top:10px;padding:10px 12px;border-radius:10px;
        --pc-line:color-mix(in srgb,var(--dg-ink-3) 34%,transparent);
        --pc-chip:color-mix(in srgb,var(--dg-ink-3) 12%,var(--dg-bg));
        border:1px solid var(--c,var(--pc-line));
        background:color-mix(in srgb,var(--c,var(--dg-ink-3)) 8%,var(--dg-bg));
        font-size:13px;line-height:1.6;overflow-wrap:anywhere}
      .partcard[hidden]{display:none}
      .partcard .pc-hd{display:flex;flex-wrap:wrap;align-items:center;gap:6px 9px}
      .partcard .pc-dot{width:10px;height:10px;border-radius:50%;background:var(--c);
        box-shadow:0 0 8px var(--c);flex:none}
      .partcard .pc-t{font-size:14px;color:var(--dg-ink);font-weight:700}
      .partcard .pc-seg{font-size:12px;color:var(--c);border:1px solid var(--c);
        border-radius:999px;padding:1px 9px;cursor:pointer;background:transparent}
      .partcard .pc-seg:hover{background:color-mix(in srgb,var(--c) 20%,transparent)}
      .partcard .pc-btns{margin-left:auto;display:flex;gap:6px;flex:none}
      .partcard .pc-btns button{font-size:12px;color:var(--dg-ink-2);background:var(--pc-chip);
        border:1px solid var(--pc-line);border-radius:7px;padding:2px 9px;cursor:pointer}
      .partcard .pc-btns button:hover{color:var(--dg-ink);border-color:var(--c)}
      .partcard .pc-bd{margin-top:7px}
      .partcard .pc-desc{font-size:12.5px;color:var(--dg-ink-2)}
      .partcard .pc-row{display:flex;flex-wrap:wrap;gap:5px 9px;align-items:baseline;margin-top:7px}
      .partcard .pc-row>.k{font-size:12px;color:var(--dg-ink-3);letter-spacing:.06em;flex:none}
      .partcard .pc-co{display:inline-flex;align-items:baseline;gap:5px;flex-wrap:wrap;
        border:1px solid var(--pc-line);border-radius:8px;padding:2px 8px;background:var(--pc-chip)}
      .partcard .pc-why{font-size:12px;color:var(--dg-ink-3)}
      .partcard .pc-item{font-size:12px;color:var(--dg-ink-2);border:1px solid var(--pc-line);
        border-radius:8px;padding:2px 8px;background:var(--pc-chip)}
      .partcard .pc-none{font-size:12.5px;color:var(--amber)}
      .partcard .pc-miss{font-size:12.5px;color:var(--dg-ink-3)}
      .partcard .pc-note{font-size:12px;color:var(--dg-ink-3);margin-top:6px}
      .partcard .pc-ft{margin-top:8px;padding-top:6px;border-top:1px dashed var(--pc-line);
        font-size:12px;color:var(--dg-ink-3)}
      .partcard .cf{font-style:normal;font-size:12px;margin-left:4px;padding:0 5px;
        border-radius:4px;border:1px solid var(--pc-line);color:var(--dg-ink-3)}
      .partcard .cf-verified{color:var(--fall);border-color:color-mix(in srgb,var(--fall) 45%,transparent)}
      .partcard .cf-estimated{color:var(--amber);border-color:color-mix(in srgb,var(--amber) 45%,transparent)}
      /* 窄畫面（筆電半視窗與手機）：間距收一點，字級仍然守住 12px 下限 */
      @media (max-width:640px){
        .partcard{padding:9px 10px;font-size:12.5px}
        .partcard .pc-t{font-size:13px}
        .partcard .pc-row{gap:5px 7px}
      }`;
    document.head.appendChild(st);
  }

  // 這個零件在圖上本來就寫了什麼（labelRow／lrow 的標題與副標）。
  // 名稱與白話說明直接拿圖上的字 —— 那幾句是規格書簽過、審查過的，
  // 另外再編一份只會讓小卡跟圖對不起來（而且那才是真正會編出假資訊的地方）。
  function partTextOf(root, key) {
    const DG = window.DG || {};
    if (!key || !DG.partHit) return null;
    const nodes = $$('#prodDiagram [data-seg]', root).filter(n => DG.partHit(n, key));
    for (let i = 0; i < nodes.length; i++) {
      const lbl = nodes[i].querySelector('text.lbl');
      if (!lbl) continue;
      const subs = [].slice.call(nodes[i].querySelectorAll('text.sub'))
        .map(t => (t.textContent || '').trim()).filter(Boolean);
      const name = (lbl.textContent || '').trim();
      if (name) return { name, desc: subs.join('') };
    }
    return null;
  }

  /* 這一格流進／流出的料號。**只看跨出這一格的邊** ——
     同一格內部互相供貨（例如日東紡供建榮玻璃原紗）不是「這個零件的進出料」，
     放進來只會讓清單看起來比較長，卻回答不了「這塊東西吃什麼、出什麼」。*/
  function segItems(sc, seg) {
    const ids = new Set((sc.companies || []).filter(c => c.segment === seg).map(c => c.id));
    const inn = [], out = [], seenI = new Set(), seenO = new Set();
    (sc.edges || []).forEach(e => {
      if (!e || !e.item) return;
      const fi = ids.has(e.from), ti = ids.has(e.to);
      if (ti && !fi && !seenI.has(e.item)) { seenI.add(e.item); inn.push(e); }
      else if (fi && !ti && !seenO.has(e.item)) { seenO.add(e.item); out.push(e); }
    });
    return { inn, out };
  }

  const confTag = (c) => (c ? `<em class="cf cf-${c}">${CONF_TEXT[c] || c}</em>` : '');
  const itemHtml = (e) => `<span class="pc-item">${A.fmt.esc(e.item)}${confTag(e.confidence)}</span>`;
  // 上限 6 筆：再多就變成一面料號牆，讀不出「這塊東西吃什麼、出什麼」
  const itemsRow = (k, list) => (list.length
    ? `<div class="pc-row"><span class="k">${k}</span>${list.slice(0, 6).map(itemHtml).join('')}`
      + (list.length > 6 ? `<span class="pc-why">還有 ${list.length - 6} 項</span>` : '') + '</div>'
    : '');

  function coHtml(c) {
    const why = (c.tech || []).join(' · ');
    const who = c.tw_code ? A.L.stock(c.tw_code, c.name) : `<b>${A.fmt.esc(c.name)}</b>`;
    return `<span class="pc-co">${who}<span class="pc-why">${why ? A.fmt.esc(why) : ''}</span></span>`;
  }

  /* 小卡本體。`seg` 一定有（零件的 data-seg）；`key` 可能沒有（3D 場景的零件沒對到 2D 時）。*/
  function renderPartCard(box, root, sc, dgId, seg, key, opt) {
    if (!box) return;
    ensurePartCss();
    const o = opt || {};
    const def = (key && DS && DS.parts && (DS.parts(dgId) || {})[key]) || null;
    /* ★ 沒有 `data-seg` 也要能開小卡（2026-09-22）。
       起因：矽晶圓那張**一個 data-seg 都不掛是對的** —— 半導體鏈 14 個環節裡沒有一格是矽晶圓，
       掛 `semi_material` 等於宣稱「光洋科做矽晶圓」、掛 `foundry` 等於宣稱「台積電自己長晶圓」。
       但舊的第一行是 `if (!seg) 收起來`，於是整張圖點下去完全沒反應 ——
       **誠實地不掛環節，代價卻是整張圖變成死的**，那不是誠實該付的代價。
       第三代半導體那張也是同一條路。
       現在的判準改成：**有 seg，或這個零件自己有 `parts[key]`，就開卡。**
       沒有 seg 時環節那顆鈕自然不會畫（下面 `s` 會是空物件、`segNm` 拿不到名字），
       小卡就只講「這是什麼、誰做的、料號」—— 那正是使用者要的答案。*/
    if (!sc || (!seg && !def)) { box.hidden = true; box.innerHTML = ''; return; }
    const onFig = partTextOf(root, key);
    const s = (sc.segments || []).find(x => x.id === seg) || {};
    const segNm = s.name || seg;
    const name = (def && def.name) || (onFig && onFig.name) || segNm;
    const desc = (def && def.desc) || (onFig && onFig.desc) || (s.desc || '');

    // 誰做的：精修有指名就用指名的那幾家，沒有就是「這個環節的台股全部」
    let tw;
    if (def && def.cos) tw = def.cos.map(c => (sc.companies || []).find(x => x.tw_code === c || x.id === c)).filter(Boolean);
    else tw = twOf(sc, seg);
    const fo = foreignOf(sc, seg);

    // 料號：精修指名的字串要回去 edges 對一次，對得到就把 confidence 一起顯示（誠實）
    let inn, out;
    if (def && def.items) {
      const all = (sc.edges || []).filter(e => e && e.item);
      inn = def.items.map(it => all.find(e => e.item === it) || { item: it, confidence: null });
      out = [];
    } else { const r = segItems(sc, seg); inn = r.inn; out = r.out; }

    const twRow = tw.length
      ? `<div class="pc-row"><span class="k">做這個的台股</span>${tw.map(coHtml).join('')}</div>`
      : '';
    /* R4：台股沒有人做就明說，而且要寫出實際上是誰做的 —— 留白會讓人以為「這裡漏了」。
       `none` 是繪圖端寫的整句話；沒寫 none 又真的沒有台股，就退回「外商是誰」，
       連外商都沒有就寫「查不到」（R5：不准為了讓卡片看起來完整而編一個對應）。*/
    /* ★ 標題不可以還是寫「做這個的台股」—— 後面接的是外商名字，
       第一眼會讀成「味之素是台股」。沒有台股時標題要自己就講清楚是在回答哪個問題。*/
    const noneTxt = def && def.none ? A.fmt.esc(def.none)
      : (fo.length ? `台股沒有廠商做這一格，實際上做的是：${A.fmt.esc(fo.map(c => c.name + ((c.tech || []).length ? '（' + c.tech.join('、') + '）' : '')).join('、'))}。` : '');
    const noneRow = (tw.length || !noneTxt) ? '' : `<div class="pc-row"><span class="k">台股有沒有人做</span><span class="pc-none">${noneTxt}</span></div>`;
    const foRow = (tw.length && fo.length)
      ? `<div class="pc-row"><span class="k">同一格的外商</span>${fo.map(coHtml).join('')}</div>` : '';
    const itemRows = (def && def.items) ? itemsRow('相關料號', inn) : (itemsRow('進料', inn) + itemsRow('出貨', out));
    const noItem = '';

    box.hidden = false;
    box.style.setProperty('--c', segColor(seg));
    box.innerHTML = `<div class="pc-hd"><span class="pc-dot"></span><span class="pc-t">${A.fmt.esc(name)}</span>
        <button type="button" class="pc-seg" id="pcSeg" title="聚焦「${A.fmt.esc(segNm)}」">環節：${A.fmt.esc(segNm)} →</button>
        <span class="pc-btns"><button type="button" id="pcFold">${o.open ? '收合 ▴' : '展開 ▾'}</button></span></div>
      <div class="pc-bd" id="pcBody"${o.open ? '' : ' hidden'}>
        ${desc ? `<div class="pc-desc">${A.fmt.esc(desc)}</div>` : ''}
        ${twRow}${noneRow}${foRow}${itemRows}${noItem}
        ${def && def.note ? `<div class="pc-note">★ ${A.fmt.esc(def.note)}</div>` : ''}
        <div class="pc-ft">標籤＝資料可信度（官方揭露／媒體報導／產業推論）</div>
      </div>`;
    const bSeg = $('#pcSeg', box); if (bSeg && o.onSeg) bSeg.onclick = () => o.onSeg(seg);
    /* 2026-09-24：「✕」拿掉（Andy：「不需要"收起"選項，點擊背景即可消除」）。取消選取的入口：
       再點一次同一個零件、點剖析圖的空白處、點這兩區以外的地方、按 Esc（見 clearPart 下面那段）。*/
    const bF = $('#pcFold', box); if (bF && o.onToggle) bF.onclick = () => o.onToggle();
  }

  // 收合狀態記在 localStorage：Andy「可以收納就收納」。讀不到就當展開，不要讓整頁掛掉。
  const partCardOpen = () => { try { return localStorage.getItem('tw.dgPartOpen') !== '0'; } catch (e) { return true; } };
  /* ★ 2026-09-23 修「切全站主題之後，使用者選起來的零件被清掉」。
     DECISIONS 已經寫明「換模式不准把使用者選起來的零件弄丟」，但切主題走的是另一條路：
     `app.js` 的 `applyTheme(name, true)` 會 dispose 全部圖表再 `route()` 整頁重畫，
     選取狀態住在這一頁的 render 閉包裡，重畫就跟著沒了。

     修法刻意**不碰 `applyTheme`**（那支是全站共用的重畫路徑，動它會影響每一頁）：
     改成在剖析圖這一側自己記住再還原 ——
       · `_dgSnap`：每次 syncHighlight 都把當下的選取記在模組層級（閉包會死，模組不會）
       · `tw:theme`：applyTheme 在 `route()` **之前**就發這個事件，這裡趁機把快照收起來
       · 下一次重畫時，同一張圖（`dg` 相同）而且在 3 秒內，才把狀態放回去
     為什麼要加 3 秒與同圖的條件：切主題時如果人不在這一頁，這份快照沒有人領走，
     留著會變成「之後逛到產業鏈時莫名其妙有一個零件是亮的」。過期就丟掉最乾淨。
     ⚠ 已知限制沒有變：3D 的鏡頭角度、ECharts 的縮放仍然會回到初始狀態 ——
       那是整頁重畫本來就有的代價，要一起解只能動 `applyTheme`。*/
  let _dgSnap = null;                 // 目前這一頁剖析圖的選取（隨時更新）
  let _dgKeep = null;                 // 切主題那一瞬間的快照，只給下一次重畫領一次
  window.addEventListener('tw:theme', () => {
    _dgKeep = (_dgSnap && (_dgSnap.partHi || _dgSnap.segHi || _dgSnap.segFilter))
      ? Object.assign({ t: Date.now() }, _dgSnap) : null;
  });
  const setPartCardOpen = (v) => { try { localStorage.setItem('tw.dgPartOpen', v ? '1' : '0'); } catch (e) { /* 忽略 */ } };

  /* ⚠ 這裡原本有一支 revealPartCard()：小卡不在畫面上時，用最小幅度把它捲進視野。
     **拿掉了**，因為它違反 2026-09-19 就定下來的「點零件不會把畫面捲走」
     （`_uitest` 的「點零件不會把畫面捲走」當場紅：451 → 565，容許值是 40px）。
     那條規則的由來跟這張小卡是同一件事：Andy 說「當我點擊圖片時，不用馬上切換到下方股票」——
     畫面自己動，使用者剛剛點的那個零件就跑掉了。

     代價要寫清楚：**剖析圖很長**（PCB 那張 1446px、載板 1300px），
     所以點圖最上面的零件時，小卡（排在圖下面）可能落在畫面外，看起來像「沒反應」。
     沒有把它改成浮層，是因為浮層一定會蓋住圖，而 Andy 要的是「看著圖、同時知道誰做的」。
     下一步該做的是**寬螢幕改成「圖左、卡右」兩欄**（卡片在自己的欄裡 sticky），
     那樣才是同時解決「不蓋圖」「不捲畫面」「看得到」三件事，而不是在這裡二選一。*/

  /* ---------------------------------------------------------------- E6：跨產業鏈的環節
     Andy 2026-09-18：「ABF 這種跨類別環節要同時出現兩張架構圖與兩邊內容」。
     ABF 載板／封測／晶圓代工／先進封裝／HBM 這五個環節同時掛在半導體與 AI 伺服器兩條鏈上
     （chainSegments() 的那兩條 include 規則），但以前不管從哪條鏈點進去，
     看到的都只有「當下這條鏈」的畫面 —— 另一半的上下游關係整個看不到。
     現在跨鏈的環節會多出一塊：**兩條鏈各一張剖析圖縮圖**（這個環節在各自的圖上亮起來）＋
     各自的上下游鄰居、各自的相關族群，以及直接跳過去的入口。*/
  /* 跨鏈面板的縮圖只放**鏈層級**的總圖（半導體、AI 伺服器）——
     名單從 window.DiagramSlots 拿，不再另外寫死一份。族群層級的圖不進這裡：
     這個面板回答的是「這個環節在哪幾條鏈上、位置有什麼不同」，不是「這個族群長什麼樣」。*/
  const DG_CHAINS = () => (DS ? DS.chains() : []);
  function chainsOfSeg(sc, seg) {
    if (!sc || !seg) return [];
    return DG_CHAINS().filter(cid => chainSegments(sc, cid).some(x => x.id === seg));
  }
  /* 同一張剖析圖被畫兩次時，裡面的漸層 id 會撞在一起（後畫的把先畫的蓋掉，顏色整個跑掉）。
     縮圖一律把 id 加上後綴，連 url(#) 與 href="#" 一起改，兩張才互不干擾。*/
  const uniqIds = (svg, tag) => String(svg)
    .replace(/id="([^"]+)"/g, (m, a) => `id="${a}${tag}"`)
    .replace(/url\(#([^)]+)\)/g, (m, a) => `url(#${a}${tag})`)
    .replace(/((?:xlink:)?href)="#([^"]+)"/g, (m, k, a) => `${k}="#${a}${tag}"`);
  /* 縮圖不可以靠「SVG 自己算 100% 該多寬」。
     窄畫面（約 1100px 以下，兩欄各只剩 320px）量到的是 **940px** —— 圖根本沒縮小，
     被 overflow 切掉一半，而且剛好切在亮起來的那個環節上，等於這張縮圖白畫了。
     （改成 width/height 實際像素 ＋ max-width:100% 一樣是 940，所以不是百分比本身的問題。）
     可靠的做法是把尺寸交給外框：外框用 aspect-ratio 撐出「跟 viewBox 同比例」的空間，
     SVG 絕對定位撐滿它 —— 絕對定位的 100% 是對著定位祖先的 padding box 算的，任何寬度都準。*/
  /* 縮圖**量完再縮**，不要相信 CSS 能把 SVG 的寬度算對。
     窄畫面（約 1100px 以下，兩欄各只剩 320px）實測到一個排版怪象：同一個父層裡
     放一個 `width:100%` 的 div 量到 320px，這張 SVG 卻量到 **940px** ——
     連 `width:200px !important` 與整段重新插入 DOM 都改不動它。
     結果就是圖沒縮小、被 overflow 切掉一半，而且剛好切在亮起來的那個環節上。
     所以改成「先量它實際多寬，再用 transform 等比縮到框裡」：
     transform 是畫的時候套的，不吃排版那套規則，量到多少就一定縮得對。*/
  function fitMini(wrap) {
    const inner = wrap.querySelector('.xinner'), svg = wrap.querySelector('svg');
    if (!inner || !svg) return;
    // 用 getBoundingClientRect 而不是 clientWidth：這一塊的 clientWidth 會回 grid 的最小值（300），
    // 不是它實際佔的寬度（334），照它算會永遠少縮一截、右邊空一塊
    const box = Math.round(wrap.getBoundingClientRect().width);
    if (!box || wrap._fw === box) return;      // 寬度沒變就不重算（fitMini 會改高度，不擋會自己觸發自己）
    inner.style.transform = 'none';
    const r = svg.getBoundingClientRect();
    if (!r.width) return;
    /* ★ 2026-09-22：除了寬度，也要吃**高度上限**。
       半導體鏈的代表圖換成先進封裝那張之後，它比原本的鏈圖（1220×545，長寬比 2.24）方得多，
       只照寬度縮的話同樣的框寬會長出兩倍高，兩張疊起來就把整個跨鏈面板撐開。
       縮圖的工作只有一個：讓人看到「這個環節在圖上的哪個位置」，所以照兩者取小。*/
    const maxH = 260;
    const k = Math.min(1, box / r.width, r.height ? maxH / r.height : 1);
    inner.style.transformOrigin = '0 0';
    inner.style.transform = 'scale(' + k.toFixed(4) + ')';
    wrap.style.height = Math.round(r.height * k) + 'px';
    wrap._fw = box;
  }

  function crossHtml(sc, seg, ch) {
    const cids = chainsOfSeg(sc, seg);
    if (cids.length < 2) return '';
    const cur = ch && ch.id;
    const panels = cids.map(cid => {
      const segs = chainSegments(sc, cid);
      const me = segs.find(x => x.id === seg) || {};
      const up = segs.filter(x => x.layer === me.layer - 1).map(x => x.name);
      const dn = segs.filter(x => x.layer === me.layer + 1).map(x => x.name);
      const gs = (A.L.sgroups[seg] || []).filter(g => A.L.gchain[g] === cid);
      const nm = A.L.chains[cid] || CHAIN_NAME[cid] || cid;
      /* ★ 2026-09-22：從 chainDefault 改成 rep —— 半導體鏈的鏈層級剖面退場之後
         （DECISIONS #234），chainDefault('semiconductor') 是 null，這塊縮圖會整個空掉。
         rep() 會退回這條鏈宣告 `rep: true` 的族群圖（半導體＝先進封裝那張）。*/
      const dgSlot = DS ? DS.rep(cid) : null;
      const dg = dgSlot ? uniqIds(DS.draw(dgSlot), '__x' + cid) : '';
      return `<div class="xchain${cid === cur ? ' cur' : ''}" data-c="${cid}">
        <div class="row spread"><b>${A.fmt.esc(nm)}${cid === cur ? ' <span class="muted">（現在這條）</span>' : ''}</b>
          ${cid === cur ? '' : `<button class="btn small xgo" data-c="${cid}">切到這條鏈看 →</button>`}</div>
        <div class="dgwrap noanim xmini"><div class="xinner">${dg}</div></div>
        <div class="xrow"><span class="muted">上游</span>${up.length ? up.map(t => `<span class="pill">${A.fmt.esc(t)}</span>`).join('') : '<span class="muted">這條鏈的最上游</span>'}</div>
        <div class="xrow"><span class="muted">下游</span>${dn.length ? dn.map(t => `<span class="pill">${A.fmt.esc(t)}</span>`).join('') : '<span class="muted">這條鏈的最下游</span>'}</div>
        <div class="xrow"><span class="muted">族群</span>${gs.length ? gs.map(g => A.L.group(g)).join('') : '<span class="muted">這條鏈沒有掛族群</span>'}</div></div>`;
    }).join('');
    return `<div class="xchains" id="cgXChains"><div class="xhd">這個環節跨 ${cids.length} 條產業鏈：
      ${cids.map(c => A.fmt.esc(A.L.chains[c] || CHAIN_NAME[c] || c)).join('、')}　</div>${panels}</div>`;
  }
  // 縮圖插進 DOM 之後才上色：跟大圖同一套環節色，這個環節亮起來、其餘壓暗
  function paintCross(box, seg) {
    const wrap = $('#cgXChains', box); if (!wrap) return;
    /* ★ 2026-09-22：縮圖也要吃「章節收合」。
       半導體鏈的代表圖（先進封裝）把四塊內容收進章節列，收合後 690px、全展開 2105px ——
       而**靜態的 SVG 本身是全展開的那一份**（wireFolds 的設計，見 diagrams.js）。
       縮圖不跑 stampParts 的話就會拿到 2105px 那一份，照高度縮之後整張只剩一指寬。
       這裡補上 stampParts：縮圖跟大圖看到的是同一個收合狀態，而且它的工作
       （讓人看到「這個環節在圖上的哪個位置」）本來就只需要主畫面那一塊。*/
    if (window.DG && window.DG.stampParts) window.DG.stampParts(wrap);
    $$('.xmini [data-seg]', wrap).forEach(n => {
      n.style.setProperty('--c', segColor(n.dataset.seg));
      n.classList.toggle('sel', n.dataset.seg === seg);
      n.classList.toggle('dim', n.dataset.seg !== seg);
    });
    $$('.xgo', wrap).forEach(b => b.onclick = () => { location.hash = '#industry/' + b.dataset.c + '/' + seg; });
    // 量完再縮；視窗寬度變了要重算（欄寬跟著變，縮放比例也得跟著變）
    const minis = $$('.xmini', wrap);
    const fitAll = () => minis.forEach(fitMini);
    fitAll();
    // 剛插進去那一刻欄寬還沒定案（grid 的 minmax 先給最小值），補量兩次才會填滿整欄
    setTimeout(fitAll, 60); setTimeout(fitAll, 400);
    if (window.ResizeObserver) { const ro = new ResizeObserver(fitAll); minis.forEach(m => ro.observe(m)); }
    else window.addEventListener('resize', fitAll);
  }
  /* ---------------------------------------------------------------- 原尺寸剖析圖
     Andy 從 2026-09-15 一直在講「文字太小」。這次量出根因：**不是字級，是欄寬。**
     產業鏈頁的 main 只有 1080px（右邊有側欄），量到的 #prodDiagram 實際寬度是
       1440px 螢幕 → 984px（×0.81）｜1100px → 644px（×0.53）｜900px → 444px（×0.36）
     1220 寬的 viewBox 被壓到 0.36 倍，12px 的字就只剩 4.4px —— 怎麼調字級都沒用。
     所以新的量產圖在 SLOTS 裡宣告 native 寬度：圖維持原尺寸、字維持 12px，
     欄位不夠寬就**左右滑**（外框改成 overflow-x:auto）。
     樣式直接寫成 inline，不走 CSS —— site/index.html 現在有別的 agent 在改，不碰它。*/
  function applyDgNative(host, id) {
    if (!host) return;
    /* ★ 2026-09-22（Andy 的「圖二」：3D 的卡片被切掉、要左右滑才看得到）。
       「圖以原尺寸顯示、放不下時左右滑」這條規則是給 **2D** 的 —— 2D 的字不能縮，
       所以寧可讓它超出欄寬。但 **3D 沒有「原尺寸」這回事**：它是 WebGL，
       相機可以退、畫布寬度就該吃剩下的欄寬。把 native 的橫向捲動套到 3D 上，
       等於讓一個本來就塞得進去的東西去捲，卡片就被捲到畫面外。
       3D 開著的時候（#prod3d 沒有 hidden）一律不給橫向捲動。*/
    const host3 = document.getElementById('prod3d');
    const on3d = !!(host3 && !host3.hidden);
    // 記住這張圖的 id：切 2D／3D 時要重套一次，那時候只拿得到 DOM
    if (id) host.dataset.dgid = id; else id = host.dataset.dgid || '';
    const w = (!on3d && DS && DS.native) ? DS.native(id) : 0;
    const svg = host.querySelector('svg');
    /* ★ 2026-09-23（W3-5）：v2 版面的 svg 已經被 `externalize()` 包進 `.dgcanvas`
       （diagrams.js:286 當場就把 host 的 overflow 清掉，捲動交給那一層）。
       這一支在切 2D／3D、換圖時會再跑一次 —— 如果照舊把 `overflow-x:auto` 設回 host，
       整個 `.dggrid`（單欄時連說明卡片一起）就又變成可捲的，下面那段置中一推就走。*/
    const inCanvas = !!(svg && svg.closest && svg.closest('.dgcanvas'));
    host.style.overflowX = (w && !inCanvas) ? 'auto' : '';
    host.style.overflowY = (w && !inCanvas) ? 'hidden' : '';
    if (svg) svg.style.minWidth = w ? w + 'px' : '';
    // 3D 畫布永遠不准比容器寬（它自己會依 clientWidth 取景，撐寬只會產生橫向捲動）
    if (host3) { host3.style.maxWidth = '100%'; host3.style.overflowX = 'hidden'; }
    /* ★ 2026-09-21（art-director 複驗 C）：手機寬展開之後，看得到的是**左欄**，
       主角（等角切開的本體）整個在畫面外 —— 讀者第一眼看到的是尺寸表而不是那顆電容。
       欄寬窄到一定程度（不到原尺寸的 62%）就先把捲軸捲到圖的正中央，
       主角先進畫面，要看左右兩欄再自己滑。**沒有動幾何、沒有動字級**。
       ⚠ 這只是止血。規格書 §7 要求的「窄畫面把右側說明欄改成圖下方堆疊」還沒做。*/
    /* ★ 2026-09-23 第二批（W3-5）：**要捲的是「裝著畫布的那一個框」，不是整個 `#prodDiagram`。**
       量到的事實：390px 載入 AI 伺服器機櫃圖時，這行置中把整個 `.dggrid` 左移 143px
       （MLCC 123px）—— 窄畫面的 `.dggrid` 是單欄、裡面還有 HTML 說明卡片，
       那些卡片本來就該貼著左邊，一進來就被切掉半邊。19 張圖全中，因為這是框架層的行為。
       v2 版面本來就有 `.dgcanvas` 這一層（CSS 給了它自己的 overflow-x:auto），
       畫布超出欄寬是它在捲 —— 置中套在它身上才是原本那條規則要的意思
       （「圖以原尺寸顯示、放不下時左右滑」講的是**圖**，不是整個版面）。
       舊版面沒有這一層（`#prodDiagram` 底下就是 svg），才退回 host 自己，行為不變。
       ⚠ 另外一定要把 host 自己的 scrollLeft 壓回 0：它的 overflow-x 是 auto，
         不壓回去的話下一次重算（換圖、轉向、ResizeObserver）又會把 grid 推走。*/
    /* ★ 2026-09-23 修「390px 時整個 `.dggrid` 被推走 178px、左欄說明卡片被切掉」。

       ⚠ 這是既有缺陷（`saas`、`cloud_msp` 早就這樣），不是哪一批改出來的。
       我照轉來的推測自己重驗過一次，**結論一致**：
         舊版把 `box`（要捲的那一層）**在外面算一次就固定住**。
         這一支是在 `externalize()` 把 svg 包進 `.dgcanvas` **之前**跑的，
         所以那一刻 `svg.closest('.dgcanvas')` 是 null，`box` 就落回 `host` 自己 ——
         於是「捲到正中央」捲的是整個 `#prodDiagram`（連 `.dghead` 與左欄卡片一起推走），
         而且 `if (box !== host) host.scrollLeft = 0` 那條保險因為 `box === host` 永遠不會執行。
         連 `requestAnimationFrame` 那一次補算也救不回來 —— 它用的是同一個被鎖死的 `box`。
       為什麼只有 `scene: null` 的圖看得到：有 3D 場景的圖之後還會再跑一次 `applyDgNative()`，
         那一次 `.dgcanvas` 已經存在，等於順手被修掉了。純 2D 的圖沒有第二次機會。

       修法兩件事（跟上面那個「410～659 切右邊」是同一支函式、同一類問題，所以合併處理）：
         1. **`box` 每次都重新找**，不要在外面鎖死。
         2. **同步那一次只做 fitCanvas，不捲**。捲動一律等到 rAF 之後 ——
            那時候 `externalize()` 已經跑完，`.dgcanvas` 找得到，捲的才是「圖」而不是「整個版面」。
            差一幀，肉眼看不出來；捲錯元素則是整片內容被切掉。*/
    if (w && svg) {
      const boxOf = () => (svg.closest && svg.closest('.dgcanvas')) || host;
      const settle = () => {
        const box = boxOf();
        fitCanvas(svg, box, w);
        const cw = box.clientWidth;
        // 窄到連 0.62 都不到（手機）→ 先把圖的正中央帶進畫面，要看左右再自己滑
        if (cw && cw < w * 0.62) box.scrollLeft = Math.max(0, (w - cw) / 2);
        if (box !== host) host.scrollLeft = 0;   // 說明卡片貼左邊，不准被推走
        return box;
      };
      /* 同步這一次只縮畫布，不捲。★ 2026-09-25 效能（perf-2）：只在 `.dgcanvas` 已經存在（切 2D／3D、重套）時做 ——
         第一次畫圖時它還沒建出來，縮的是 host，接著 externalize() 又把 svg 寬度釘回 viewBox 寬，這一次的量測（逼整頁排版）是白做的；
         真正生效的是下面 rAF 那一次。*/
      if (inCanvas) fitCanvas(svg, boxOf(), w);
      requestAnimationFrame(() => {
        const box = settle();
        /* 視窗寬度在 410～659 這一段變動時要重算（Andy 常常把瀏覽器縮成半邊）。
           掛在 rAF 之後才掛得到真正的 `.dgcanvas`；掛在 host 上的話寬度永遠是欄寬，量不到重點。*/
        if (box._dgRO) { try { box._dgRO.disconnect(); } catch (e) { /* 忽略 */ } }
        try { box._dgRO = new ResizeObserver(() => settle()); box._dgRO.observe(box); }
        catch (e) { /* 舊瀏覽器沒有 RO 就算了，換圖／換分頁時仍會重算 */ }
      });
    }
  }
  /* ★ 2026-09-23：修「容器寬 410～659px 時剖析圖右半邊被切掉」。

     怎麼發生的：`externalize()`（diagrams.js）把 svg 的 `width` 與 `min-width` 釘成 viewBox 寬
     （這一批 v2 圖是 660），`.dgcanvas` 是 `overflow-x:auto`；
     而上面那段「捲到正中央」的止血只在 `clientWidth < native × 0.62`（＝409px）才啟動。
     **410～659 這一整段兩邊都沒接到**：不縮、不置中、scrollLeft 是 0，
     畫面上就是主剖面的右半邊不見了、右側章節列被切在框緣。
     實測（ai_adv_packaging，事件抽屜開著）：視窗 980px → 畫布欄寬 486px、被切掉 174px；
     1050px → 切 104px；1150px → 切 4px。23 張 v2 圖全中，因為這是框架層的行為。

     為什麼不是「直接把 svg 縮到欄寬」：縮了字會跟著等比例變小，
     12px 是硬下限（DECISIONS #226，Andy 抱怨過三次「文字太小」），縮到 0.74 倍就破線。
     所以**縮畫布的同時把 `--dg-fs-*` 反向放大**：畫布縮 k 倍、字級 token 除以 k，
     兩者相乘之後畫面上的實際字級**一點都沒變**。

     只動 0.62～1.0 這一段（就是那道裂縫本身）：
       · k ≥ 1（1440px、以及任何塞得下的欄寬）→ 一行都不動，維持原尺寸。
       · k < 0.62（390px 手機）→ 交給既有的「捲到正中央」，行為完全不變。
     這樣「修這件事最大的風險是把 1440 與 390 弄壞」在結構上就不可能發生。*/
  const DG_FS_VARS = ['--dg-fs-ttl', '--dg-fs-hd', '--dg-fs-lbl', '--dg-fs-min'];
  function fitCanvas(svg, box, w) {
    if (!svg || !box || !w) return;
    const cw = box.clientWidth;
    if (!cw) return;
    const k = cw / w;
    /* ★ 2026-09-23 修「畫布被擠壓時閱讀模式的字級靜悄悄掉回科技那一組」。
       基準值以前是從 `:root` 讀的，但閱讀模式那一組（19/15/14/13）定義在
       `:root[data-dgpal="read"] .dg.rs` —— **那是後代選擇器**，`:root` 上永遠只有
       科技的 12px 起。於是每次縮放都用 12 當基準，畫面上的字就從 13 掉到 12。
       改成**從 svg 自己身上量**：那一層才吃得到 `.dg.rs` 那條規則。
       原本不敢這樣讀是怕「第二次讀到上一輪放大過的值、愈放愈大」——
       所以量之前先把上一輪的覆寫整組清掉（`getComputedStyle` 會即時重算），
       量到的一定是還沒被動過手腳的基準值。
       只動這裡：`:root` 上那組 token 一個字都沒改，非 rs 的圖行為完全不變。*/
    DG_FS_VARS.forEach(v => svg.style.removeProperty(v));
    if (k >= 0.995 || k < 0.62) {          // 塞得下，或窄到交給置中止血 —— 兩種都退回原尺寸
      svg.style.width = w + 'px'; svg.style.minWidth = w + 'px';
      return;
    }
    const rs = getComputedStyle(svg);
    DG_FS_VARS.forEach(v => {
      const base = parseFloat(rs.getPropertyValue(v));
      if (base) svg.style.setProperty(v, (base / k).toFixed(2) + 'px');
    });
    svg.style.minWidth = '0';
    svg.style.width = Math.floor(cw) + 'px';
  }
  // 讓剖析圖每個零件帶上環節色（CSS 用 var(--c)）
  function paintDiagram(root) {
    if (!root) return;
    $$('[data-seg]', root).forEach(n => { n.style.setProperty('--c', segColor(n.dataset.seg)); n.style.cursor = 'pointer'; });
    $$('[data-chain]', root).forEach(n => { n.style.cursor = 'pointer'; n.onclick = () => { location.hash = '#industry/' + n.dataset.chain; }; });
  }
  /* 選到某一格環節之後，把那一格帶進視野。
     ★ 2026-09-23 C5 退版：環節色標回到 `#segChips`（圖的上方，永遠看得到），
     所以先把色標帶進視野；`block:'nearest'` —— 色標本來就看得到時完全不動，
     不會把整頁拉走（個股頁被 scrollIntoView 拉到底那個坑，2026-09-20 記過一次）。
     色標帶完再把分層圖自己那個框捲到那一欄，但**不准動到整頁**。*/
  function scrollChainTo(root, seg) {
    if (!seg) return;
    /* ★ 2026-09-24 桌機（下拉＋圖＋右欄）：選一格會讓右欄長出來、圖變窄並重畫（ResizeObserver 延遲 120ms），
       所以等圖重畫完再量位置。只做兩件事：右欄捲回頂端；圖上那一格的標題不在畫面裡才把整頁捲過去
       （右欄是 sticky 的，整頁捲動時它跟著黏在旁邊）。圖比框寬時，框自己左右捲到那一欄 —— 只捲框。*/
    if (relListMode()) {
      setTimeout(() => {
        const list = $('#relList', root); if (list) list.scrollTop = 0;
        const map2 = $('#chainMap', root);
        const t2 = map2 && !map2.hidden && ($(`.chainmap .segtitle[data-seg="${seg}"]`, root) || $(`.chainmap .co[data-segment="${seg}"]`, root));
        if (!t2) return;
        const r = t2.getBoundingClientRect(), mr = map2.getBoundingClientRect();
        if (r.width > 0 && (r.left < mr.left || r.right > mr.right)) map2.scrollTo({ left: Math.max(0, map2.scrollLeft + (r.left - mr.left) - 40), behavior: 'instant' });
        if (r.height > 0 && (r.top < 70 || r.bottom > window.innerHeight - 20)) window.scrollBy({ top: r.top - Math.round(window.innerHeight / 3), behavior: 'instant' });   // 瞬間到位：平滑捲動會拖好幾百毫秒，期間下拉鈕在游標底下一直移動，接著點什麼都會點歪
      }, 200);
      return;
    }
    const chip = $(`#segChips .segchip[data-seg="${seg}"]`, root);
    if (chip && chip.scrollIntoView) {
      const r = chip.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) chip.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    const map = $('#chainMap', root); if (!map || map.hidden) return;
    const t = $(`.chainmap .segtitle[data-seg="${seg}"]`, root) || $(`.chainmap .co[data-segment="${seg}"]`, root);
    if (!t || !t.getBBox) return;
    const svg = map.querySelector('svg'); if (!svg) return;
    const vb = (svg.getAttribute('viewBox') || '').split(/\s+/).map(Number);
    const scale = vb.length === 4 && vb[2] ? (svg.clientWidth || map.clientWidth) / vb[2] : 1;
    const b = t.getBBox();
    map.scrollTo({ left: Math.max(0, b.x * scale - 40), top: Math.max(0, b.y * scale - 40), behavior: 'smooth' });
    if (map.scrollIntoView) map.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  /* 高亮分三層（2026-09-21 晚間）：
       `part` ＝被點的那一個零件的身分 → `.sel-part`（最強）
       同一個 `data-seg` 的其餘          → `.sel`（次強，值一個都沒改＝多環節圖零回歸）
       其餘                              → `.dim`（本來就有的行為）
     單一環節的圖（整張只有一個 data-seg）在 CSS 那邊多一條：次強要退到 --dg-sib-o，
     不然「14 個一起亮」跟「沒點」長得一模一樣。`.haspart` 就是那條規則的開關。*/
  function highlightSegments(root, segs, color, part, mapSegs) {
    const on = new Set(segs || []);
    const onMap = mapSegs ? new Set(mapSegs) : on;     // 關聯圖、環節卡清單那一側用的（#317：族群帶出來的選取在有反亮時不壓關聯圖）
    const DG = window.DG || {};
    /* ★ 沒有環節的零件也要亮得起來（2026-09-22）。
       `on` 空的時候（點的是一個沒有 data-seg 的零件）第一個條件永遠 false ——
       所以矽晶圓、第三代半導體那種「刻意不掛環節」的圖，點下去一片死寂。
       改成：**有環節就照舊比環節，沒有環節就只比零件身分。**
       兩條路的 `dim` 行為也因此自然分開：`on` 是空的就沒有人被壓暗，
       只有主角被提亮 —— 那正是單一主體的圖該有的樣子。*/
    const nodes = $$('#prodDiagram [data-seg]', root);
    /* ★ 2026-09-25（審查 R3）：傳產鏈一打開預設的「輕油裂解廠」整張被壓暗（71 個 .dim、0 個 .sel）。
       原因：`segs` 是**族群**的環節（石化族群的 gsegs），這張圖上的 data-seg 一個都對不上，
       於是「有選東西、但不是你」的規則把每一個零件都壓暗了。
       修法：剖析圖這一側只用「這張圖上真的有的環節」（交集）；交集是空的就當作沒選 —— 不壓暗、不提亮。
       關聯圖、環節卡清單那一側照舊用完整的 `on`（那裡的環節本來就對得上）。
       3D 同理，拿它自己場景裡有的環節取交集。*/
    const onDg = new Set([...on].filter(sg => nodes.some(n => n.dataset.seg === sg)));
    const hit = (n) => (onDg.size ? onDg.has(n.dataset.seg) : !n.dataset.seg)
      && !!DG.partHit && DG.partHit(n, part);
    if (view3d) {
      const have3 = view3d.segs ? new Set(view3d.segs()) : null;
      const on3 = have3 ? new Set([...on].filter(sg => have3.has(sg))) : on;
      view3d.highlight(on3, color, part || null);   // 3D 場景與 SVG 用同一套高亮規則
    }
    /* ★ 只有 `data-part`、沒有 `data-seg` 的零件**另外處理**，不可以併進上面那一份。
       2026-09-22 踩到：我第一版把它們併進 `nodes`，結果
       `dim` 的條件 `on.size > 0 && !on.has(n.dataset.seg)` 對它們永遠成立
       （`on.has(undefined)` 是 false）—— 於是只要選了任何一個環節，
       這些本來不該被影響的裝飾零件全部被壓暗。實測 AI 伺服器鏈那張
       `dim` 從 0 變 15，連帶讓既有的 3D 驗收整段紅。
       它們只該做一件事：**自己被點到的時候提亮**。不參與 sel，也不參與 dim。*/
    const bare = $$('#prodDiagram [data-part]:not([data-seg])', root);
    /* `.haspart` ＝「這張圖上真的有一個主角」。一定要先數過才掛：
       2D 與 3D 的零件不是一一對應（3D 的 MLCC 焊墊在 2D 是畫在端電極剖面裡的），
       從 3D 點完再切回 2D 時可能一個都對不上 —— 那時候掛了 .haspart 就會變成
       「同環節全部退一階、卻沒有任何主角」，比改之前還糟。*/
    const anyPart = nodes.some(hit) || bare.some(n => !!DG.partHit && DG.partHit(n, part));
    $$('#prodDiagram svg', root).forEach(svg => svg.classList.toggle('haspart', anyPart));
    nodes.forEach(n => { n.classList.toggle('sel', onDg.has(n.dataset.seg)); n.classList.toggle('sel-part', hit(n)); n.classList.toggle('dim', onDg.size > 0 && !onDg.has(n.dataset.seg)); if (color && onDg.has(n.dataset.seg)) n.style.setProperty('--c', color); else n.style.setProperty('--c', segColor(n.dataset.seg)); });
    bare.forEach(n => n.classList.toggle('sel-part', !!DG.partHit && DG.partHit(n, part)));
    $$('.chainmap .co', root).forEach(n => n.classList.toggle('dim', onMap.size > 0 && !onMap.has(n.dataset.segment)));
    $$('.chainmap .segtitle', root).forEach(n => n.classList.toggle('sel', onMap.has(n.dataset.seg)));
    $$('.chainmap .segbox', root).forEach(n => n.classList.toggle('sel', onMap.has(n.dataset.seg)));   // 環節外框跟著標題一起亮（2026-10-03）
    /* 環節卡清單（2026-09-23 C5 退版之後回來了）：選到的那一格 `.sel`、其餘 `.dim`。
       手機上還要順手把那張卡攤開 —— 不然「選起來了」但個股標籤還收著，看起來像沒反應。
*/
    $$('.seglist .segcard', root).forEach(n => { const hit = onMap.has(n.dataset.seg);
      n.classList.toggle('sel', hit);
      n.classList.toggle('dim', onMap.size > 0 && !hit);
      if (hit && onMap.size === 1 && segListReveal) segListReveal(n); });
  }
  /* ---------------------------------------------------------------- 3D 剖析圖（Three.js）
     Andy 拍板「先試試看 three.js」。四條硬性驗收都在這裡兌現：
       可以轉、點零件會亮並帶出台股、標籤是 DOM、WebGL 不能用就退回 SVG。
     three.js 是動態載入的，只有真的按下 3D 才付那 670KB。*/
  let view3d = null;                 // 目前掛著的 3D 場景（沒有就是 null）
  // 動畫偏好（平面圖與 3D 共用同一個開關）；沒設定過就是開
  const animPref = () => { try { return localStorage.getItem('tw.dganim') !== '0'; } catch (e) { return true; } };

  let fit3dOff = null;               // Fit.on 的取消函式（3D 畫布高度跟著視窗高度走，#317）
  function dispose3D() {
    if (fit3dOff) { try { fit3dOff(); } catch (e) { /* 忽略 */ } fit3dOff = null; }
    if (view3d) { try { view3d.dispose(); } catch (e) { /* 忽略 */ } view3d = null; }
  }
  /* ★ 2026-10-03 晚（Andy：「這頁 3D 回到之前那樣的大小，並且需要打開這頁就能看到完整頁面」，DECISIONS #317）：
     3D 畫布最多能多高 ＝ 打開頁面（不捲動）時，畫布上緣到視窗底之間、扣掉畫布底下那行 3D 說明與 #dgSec 的下內距、再留 8px。
     另外整個剖析圖區（#dgSec）本身也不超過 Fit.cap()（一屏可視高 − 跳轉列 − 上下邊距，#308）。
     手機（≤820，Fit.desk() 為假）不限，照舊用寬度算的高度。零件小卡（#partCard）是點了才出現的，不算進去 ——
     點零件不應該讓畫布縮一下。three3d.js 拿這個值當上限，再跟「寬 × hk」取小、下限 340。*/
  function dg3dCap(el, host) {
    const F = window.Fit;
    if (!F || !F.desk() || !host || !host.getClientRects().length) return Infinity;
    const sec = $('#dgSec', el); if (!sec) return Infinity;
    const hr = host.getBoundingClientRect(), sr = sec.getBoundingClientRect();
    const note = $('#dg3dNote', el);
    const noteB = note && !note.hidden && note.getClientRects().length ? note.getBoundingClientRect().bottom : hr.bottom;
    const cs = getComputedStyle(sec);
    const below = Math.max(0, noteB - hr.bottom) + (parseFloat(cs.paddingBottom) || 0) + (parseFloat(cs.borderBottomWidth) || 0);
    const byPage = window.innerHeight - (hr.top + window.scrollY) - below - 8;
    const byCard = F.cap() - (hr.top - sr.top) - below;
    return Math.floor(Math.min(byPage, byCard));
  }

  /* ================================================================ 剖析圖配色（2D ＋ 3D）
     2026-09-21 深夜改（Andy：「幫我圖片色系色調多個休閒風格，更平易近人」
     ＋「2D3D 都需要新增那樣的風格」）。

     改之前：`#dgPal` 這顆鈕**只在 3D 模式才出現**（wire3D 的 setMode 會把它跟
     「重設視角」「拖曳」一起 hidden），而且只呼叫 view3d.setPal() ——
     也就是 **9 張 2D 剖析圖從頭到尾只有一種配色**，切都切不了。
     現在改成：配色掛在 `<html data-dgpal>`，2D 的 SVG（吃 :root 的 --dg-*）與
     3D（three3d.js 讀同一組 --dg-*）同時生效，鈕在 2D 也看得見。

     ★ 2026-09-22（art-director，Andy 拍板）：四個配色收斂成**兩種模式** —— 科技（深底）／閱讀（紙底），
       規格在 docs/diagram_specs/_STYLE.md。
       · **預設跟著全站主題走**：深色主題 → 科技、淺色主題 → 閱讀（沒有存過偏好時）。
         這改掉了「剖析圖畫布恆為深底」的既有決策：淺色主題下畫布是暖白。
       · `#dgPal` 仍可手動切；手動切過就記住（跨主題都用那一個，直到再按一次）。
       · localStorage 的 key 沿用 `tw.dg3d.pal`。**舊值（soft／calm／casual）一律當成「沒設定」清掉、
         退回跟主題走** —— 深色主題下就是科技（＝那些人以前的預設），不會看到破圖。
       · 切主題時（app.js 的 tw:theme 事件）沒有手動偏好的人跟著換模式，3D 開著也一起換。*/
  const DG_PALS = ['tech', 'read'];
  const DG_PAL_NAME = { tech: '科技', read: '閱讀' };
  const themePal = () => (document.documentElement.getAttribute('data-theme') === 'light' ? 'read' : 'tech');
  function palPref() {
    try {
      const v = localStorage.getItem('tw.dg3d.pal');
      if (DG_PALS.includes(v)) return v;
      if (v) localStorage.removeItem('tw.dg3d.pal');   // 舊配色名 → 當成沒設定
    } catch (e) { /* 私密視窗 */ }
    return themePal();
  }
  /* 把配色掛到 <html> 上。掛在 :root 而不是掛在某一個容器上，是因為題材頁的產品圖
     （site/themes3d.js）也吃同一組 --dg-*，掛在 #prodDiagram 上它就吃不到。*/
  function applyDgPal(name) {
    const v = DG_PALS.includes(name) ? name : 'tech';
    try { document.documentElement.dataset.dgpal = v; } catch (e) { /* 忽略 */ }
    // 字級跟著模式變，diagrams.js 聽這個事件重新「量完再縮」（fitTexts）
    try { window.dispatchEvent(new CustomEvent('tw:dgpal', { detail: { pal: v } })); } catch (e) { /* 忽略 */ }
    return v;
  }
  applyDgPal(palPref());      // 一載入就套用，不要等使用者走到產業頁才變色
  /* ★ 2026-09-23 第二批（W3-10，Andy：「當切換明亮介面時，所有圖片會自動切換閱讀模式；
     同理切暗色介面時，也會切回來」）：**切主題一律重新對齊配色，不管先前有沒有手動按過。**

     改之前是「沒有手動偏好的人才跟著換」—— 手動按過一次之後那個選擇就黏住，
     之後再切主題圖都不動，那正是 Andy 看到的行為。
     做法是把存起來的偏好**清掉**再套主題對應的那一個：
       · 清掉而不是覆寫，是因為 `palPref()` 的語意就是「沒存過就跟主題走」——
         清掉之後那條路自己就對了，重新整理也不會跳回舊的（不清的話 localStorage 還留著舊值）。
       · 手動按 `#dgPal` 仍然有效（它會重新寫進 localStorage），
         那個選擇維持到**下一次切主題**為止。
     ⚠ 這裡**不重畫任何一張圖**：2D 吃的是 `:root` 上的 `--dg-*`（換 data-dgpal 就變色），
       3D 走 `view.setPal()` 就地換材質 —— 所以使用者選起來的零件、3D 的鏡頭角度、
       爆炸拆解的進度全部留著。整張重畫是最省事但最錯的解法。*/
  let palBtnPaint = null, palView = null;
  window.addEventListener('tw:theme', () => {
    try { localStorage.removeItem('tw.dg3d.pal'); } catch (e) { /* 私密視窗 */ }
    const v = applyDgPal(themePal());
    const view = palView && palView();
    if (view && view.setPal) view.setPal(v);
    if (palBtnPaint) palBtnPaint();
  });

  /* 配色。★ 2026-09-23 第十批 C1：手動切換鈕 `#dgPal` 已經整顆移除
     （Andy：「配色拿掉」）—— 上一批做好「切全站主題 → 剖析圖配色自動跟著切」之後，
     手動那顆就是多餘的。**自動那條路一行都沒動**，這支仍然要被呼叫，理由是它負責
     把 `palView` 接起來：`tw:theme` 事件要靠它才拿得到 3D 的 view，才叫得到 `view.setPal()`。
     所以 `palView = getView` 移到「找不到鈕就 return」**之前** ——
     鈕沒了，但 3D 正開著時切主題仍然要跟著換材質。
     ⚠ 下面那段鈕的程式碼刻意留著：`#dgPal` 是這一頁拿掉，
       將來若有別的地方要一顆手動鈕，掛上同一個 id 就能用，不必重寫一次配色邏輯。*/
  function wirePal(el, getView) {
    palView = getView;
    const plb = $('#dgPal', el); if (!plb) return;
    const paint = () => {
      const cur = palPref();
      plb.textContent = '配色：' + (DG_PAL_NAME[cur] || cur);
      plb.classList.toggle('cyan', cur !== themePal());   // 跟主題預設不一樣的時候才亮，表示「你手動切過」
      plb.title = '換一種模式（2D 與 3D 共用）：科技（深底）／閱讀（紙底）。'
        + '跟著全站主題走：深色→科技、淺色→閱讀；手動切過的選擇會保留到下一次切主題為止';
    };
    palBtnPaint = paint;
    plb.hidden = false;
    paint();
    plb.onclick = () => {
      const cur = palPref();
      const next = DG_PALS[(DG_PALS.indexOf(cur) + 1) % DG_PALS.length];
      try { localStorage.setItem('tw.dg3d.pal', next); } catch (e) { /* 忽略 */ }
      applyDgPal(next);
      const v = getView && getView();
      if (v && v.setPal) v.setPal(next);     // 3D 正開著就一起換，不用等重掛
      paint();
    };
  }

  /* ★ 2026-09-26：「拖曳／重設視角」那組鈕（#dg3dCtl）3D 開著時住在 #prod3d **裡面**。
     住在外面（兄弟元素疊上去）的話，游標從畫布移到鈕上就算「離開 #prod3d」——
     three3d.js 的 hover 展開（#246，pointerleave 收攏）會在你要按鈕的那一刻把爆炸圖收回去。
     但 #prod3d 在換圖、切 2D 時會被清空，所以清空之前先把鈕停回外面那層 .dg3dbox，id 永遠查得到。*/
  function clear3dHost(host) {
    const c = host && host.querySelector('#dg3dCtl');
    if (c && host.parentNode) host.parentNode.appendChild(c);
    if (host) host.innerHTML = '';
  }

  function wire3D(el, chainId, hooks) {
    const hk = hooks || {};
    const onSeg = hk.onSeg || (() => { /* 沒接就不做事 */ });
    const sync = hk.sync || (() => { /* 沒接就不做事 */ });
    const btn = $('#dg3d', el), rst = $('#dgReset', el), note = $('#dg3dNote', el);
    const drg = $('#dgDrag', el);     // 配色已經不是一顆鈕了（跟著全站主題走，見 wirePal）
    const ctl = $('#dg3dCtl', el);    // 「拖曳」「重設視角」住在 3D 畫面框內右上角的這一組（2026-09-26）
    const svg = $('#prodDiagram', el), host = $('#prod3d', el);
    if (!btn || !host) return;
    const R = window.Rack3D;
    if (!R || !R.hasScene(chainId)) return;         // 這條鏈還沒有 3D 場景 → 維持平面圖
    if (!R.supported()) {                            // WebGL 不能用 → 連鈕都不出現，安靜退回 SVG
      note.hidden = false;
      note.textContent = '這台裝置不支援 WebGL，改用平面剖析圖（內容一樣）。';
      return;
    }
    btn.hidden = false;
    // 2D/3D 切換鈕真的出現了，才在「?」條列補上 3D 的讀法（2026-10-04 稽核第 5 項：沒有 3D 的鏈不寫這條）
    { const ul = $('#how-dg ul', el) || (document.getElementById('how-dg') || {}).querySelector?.('ul');
      if (ul && !ul.querySelector('[data-dg3dhow]')) {
        /* 2026-10-06 廢話普查：3D 操作教學不再補進「?」 */
      } }
    /* ★ 2026-09-26（Andy：「切回 2D 時，顯示 2D，不要都 3D」）：
       以前這是一顆開關「3D 立體」，2D 時寫「3D 立體」、3D 時寫「3D 立體 ✓」——
       不管在哪個模式，眼睛讀到的都是「3D」，看不出現在到底是哪一種。
       改成分段鈕「2D｜3D」，**亮的那一格就是現在的模式**（樣式是站上通用的 .seg 分段鈕，亮的那格實心青色）。
       記憶沿用 localStorage `tw.dg3d`（'1'＝3D），全站剖析圖共用一個值：換分頁、重新整理都照最後選的那個。
       paintMode 畫的是「實際上現在是哪個」，不是「使用者想要哪個」：3D 掛不起來退回平面時，亮的要是 2D。*/
    const paintMode = (is3d) => {
      $$('button[data-dm]', btn).forEach(b => {
        const on3 = b.dataset.dm === '3d', cur = on3 === !!is3d;
        b.classList.toggle('on', cur); b.setAttribute('aria-pressed', cur ? 'true' : 'false');
      });
      btn.dataset.mode = is3d ? '3d' : '2d';
    };
    const setMode = async (on) => {
      try { localStorage.setItem('tw.dg3d', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
      paintMode(on);
      // 「拖曳：轉動」「重設視角」只對 3D 有意義 —— 2D 時整組藏起來，不留一顆按了沒反應的鈕。
      // ★ 2026-09-26 起藏的是外面那層 #dg3dCtl：兩顆是 .pill（display:inline-flex），單獨設 hidden 會被蓋掉。
      if (ctl) ctl.hidden = !on;
      svg.hidden = on; host.hidden = !on;     // 配色不跟著 3D 開關（2D 也吃同一組 --dg-*）
      /* 切換 2D／3D 之後重套一次「原尺寸」規則：native 的橫向捲動只給 2D，
         3D 一律不捲（見 applyDgNative 的註解）。不重套的話切回 2D 會少掉捲動、
         切到 3D 又會留著上一輪的 overflow 設定。*/
      applyDgNative(svg, svg.dataset.dgid || '');
      if (!on) { dispose3D(); note.hidden = true; sync(); return; }
      note.hidden = false;
      note.textContent = '載入 3D 中…';
      dispose3D();
      clear3dHost(host);
      let v = null;
      try {
        v = await R.mount(host, chainId, {
          color: segColor,
          // 第二個參數是零件身分（three3d.js 的 userData.part）—— 兩層高亮靠它，別在這裡吃掉
          onSeg: (seg, data) => onSeg(seg, data),
          // 點到場景空白處（raycast 沒打到任何零件）→ 回到 Default，跟 2D 同一支 clearPart
          onBg: hk.onBg || null,
          anim: animPref(),          // E4：一掛上去就照使用者目前的動畫偏好，不要先動起來再被關掉
          members: hk.members || null,   // 圖九 2-3：文字框底下那排可點的台股晶片
          onStock: hk.onStock || null,
          pal: palPref(),                // 圖九 2-2：三種配色，記在 localStorage
          // 右上角那組「拖曳／重設視角」的高度：右欄卡片從它下面開始排，不會被鈕壓住（2026-09-26）
          reserveTR: () => (ctl && !ctl.hidden ? Math.ceil(ctl.getBoundingClientRect().height) + 8 : 0),
          // 畫布高度上限：打開頁面不用捲就看到整個剖析圖區（#317，見 dg3dCap）
          maxH: () => dg3dCap(el, host),
        });
      } catch (err) {
        // 起不來就要講出來，不能停在「載入 3D 中…」讓人以為當掉了
        note.textContent = '3D 起不來（' + (err && err.message ? err.message : err) + '），已退回平面剖析圖。';
        svg.hidden = false; host.hidden = true; if (ctl) ctl.hidden = true; paintMode(false); return;
      }
      if (!v) { note.textContent = '3D 起不來，已退回平面剖析圖。'; svg.hidden = false; host.hidden = true; if (ctl) ctl.hidden = true; paintMode(false); return; }
      view3d = v;
      if (ctl) host.appendChild(ctl);   // 3D 掛好才搬進畫面框（原因見 clear3dHost 上面的說明）
      // 手機 v3（≤640px）：3D 的字卡欄與 .ld-no 收掉，改用會自己避讓的 HTML 編號層（桌機進去就 return）
      if (window.DG && window.DG.mobileNums3d) window.DG.mobileNums3d(host, v);
      /* N1（Andy 2026-09-19）：「3D圖需要可以游標抓取移動，並且可以 360 都觀測，
         我發現下面看不到」。仰角限制已在 three3d.js 解開（0 ~ π），
         這裡再補一顆「拖曳：轉動／平移」——OrbitControls 預設右鍵才平移，
         但一般人只會左鍵拖，所以給一顆看得見的切換。*/
      if (drg) {
        let mode = 'rotate';
        try { mode = localStorage.getItem('tw.dg3d.drag') === 'pan' ? 'pan' : 'rotate'; } catch (e) { /* 忽略 */ }
        const paint = () => {
          drg.textContent = mode === 'pan' ? '拖曳：平移' : '拖曳：轉動';
          drg.classList.toggle('cyan', mode === 'pan');
        };
        if (v.setDrag) v.setDrag(mode);
        paint();
        drg.onclick = () => {
          mode = mode === 'pan' ? 'rotate' : 'pan';
          try { localStorage.setItem('tw.dg3d.drag', mode); } catch (e) { /* 忽略 */ }
          if (view3d && view3d.setDrag) view3d.setDrag(mode);
          paint();
        };
      }
      /* 圖九 2-2 的配色鈕已經搬到 wirePal()（2026-09-21 深夜）——
         它現在 2D 也要用，不能再掛在「3D 掛起來之後」這條路上。
         這裡只剩「3D 剛掛好，把目前選的配色套上去」，而 R.mount 的 pal: palPref()
         已經做掉了，所以這裡什麼都不用做。*/
      note.textContent = v.sub || '';
      /* 說明從「載入 3D 中…」一行變成完整說明（1440 寬是兩行），畫布底下多出來的那一行要從畫布高度扣掉；
         之後上方分頁列折行、視窗高度變了（Fit.on 盯 .nbcard 的高度與視窗尺寸）也重算一次。refit 高度沒變就什麼都不做。*/
      if (v.refit) {
        v.refit();
        if (window.Fit && window.Fit.on) fit3dOff = window.Fit.on(() => { if (view3d === v && v.refit) v.refit(); }, host);
      }
      sync();
    };
    /* 點「2D」或「3D」那一格＝切到那個模式；點的是已經亮著的那一格就什麼都不做（分段鈕的慣例，不是開關）。
       點在兩格之間的縫、或程式直接呼叫容器的 .click()（target 是容器本身）才當成「切到另一個」——
       保留這條是為了舊的呼叫方式（驗收裡有 eval_on_selector('#dg3d', e => e.click())）不必全部改寫。*/
    btn.onclick = (ev) => {
      const b = ev && ev.target && ev.target.closest ? ev.target.closest('button[data-dm]') : null;
      const want3 = b ? b.dataset.dm === '3d' : host.hidden;
      if (want3 === !host.hidden) return;
      setMode(want3);
    };
    /* ★ 2026-09-26（Andy：「另外新增 點兩下重設視角」）：按鈕與雙擊走**同一支** resetView。
       view3d.reset() 本來就是瞬間回位（沒有補間）—— 雙擊也照舊，不另外加過渡，兩條路的結果才會一模一樣。
       雙擊的副作用怎麼處理：瀏覽器的 dblclick 前面一定先有兩次 click，three3d.js 的 pointerup
       會把它們各當成一次「點零件／點背景」—— 點在零件上，第一下選起來、第二下再點同一個＝取消；
       點在背景上兩下都是 clearPart。所以雙擊之後本來就不太會留下選取，
       但「兩下落在不同零件上」（相機在動、手滑）就會留一個 —— 這裡在重設之後一律再 onBg（clearPart）一次，
       保證「雙擊＝回到一開始的樣子」：視角回預設、沒有選取、零件小卡收掉。
       不做「延遲單擊等看看是不是雙擊」：那會讓每一次單擊選零件都慢 300ms，而單擊是主要操作。
       只認畫布本身（target 是 canvas）：卡片、台股晶片、底下那一排卡片上的雙擊不算 —— 在那些地方雙擊的人是想選字。
       用 ondblclick 指派而不是 addEventListener：wire3D 每換一張圖就跑一次，host 是同一個元素，疊上去會重設好幾次。*/
    const resetView = () => { if (view3d) view3d.reset(); };
    rst.onclick = resetView;
    host.ondblclick = (e) => {
      if (!view3d || host.hidden || !e.target || e.target.tagName !== 'CANVAS') return;
      e.preventDefault();
      resetView();
      if (hk.onBg) hk.onBg();
    };
    let want = false;
    try { want = localStorage.getItem('tw.dg3d') === '1'; } catch (e) { /* 忽略 */ }
    setMode(want);
  }

  /* 每一個零件在綁 click 之前先被蓋上「零件身分」（data-dgkey）——
     沒有身分就只認得出環節，單一環節的圖點下去等於沒事發生。stampParts 也會順手
     替「整張只有一個環節」的圖補上 .dg1，畫圖的人不用記得自己加。*/
  function wireDiagram(root, onSeg, onBg) {
    const host = $('#prodDiagram', root);
    if (window.DG && window.DG.stampParts) window.DG.stampParts(host);
    // 手機 v3（≤640px）：字卡收掉、只留編號（diagrams.js DG.mobileNums；桌機進去就 return）
    if (window.DG && window.DG.mobileNums) window.DG.mobileNums(host);
    $$('#prodDiagram [data-seg]', root).forEach(n => { n.onclick = (e) => { e.stopPropagation(); onSeg(n.dataset.seg, n.dataset.dgkey || null); }; });
    /* ★ 只有 `data-part`、沒有 `data-seg` 的零件也要點得動（2026-09-22，同上）。
       `:not([data-seg])` 是為了不要跟上面那一圈重複綁 —— 有 seg 的走上面那條，行為完全不變。
       傳 `null` 當環節：`pickPart` 會把 segHi 設成 null，所以**不會篩成分股**（DECISIONS #73），
       但 partHi／partSel 會寫進去，小卡就開得起來。*/
    $$('#prodDiagram [data-part]:not([data-seg])', root).forEach(n => {
      n.onclick = (e) => { e.stopPropagation(); onSeg(null, n.dataset.dgkey || n.dataset.part || null); };
    });
    /* ★ 點空白背景 → 取消選取、全部恢復全亮（Andy 2026-09-22）。
       改之前只有「再點同一個零件」才取消 —— 使用者要先記得剛剛點的是哪一個才退得出來，
       而單一環節的圖上十幾個零件長得很像，等於退不出來。
       為什麼掛在 host 上就夠：零件的 onclick 與章節列都有 stopPropagation，
       能冒泡到這裡的**本來就只有背景**。closest 那一層是保險。*/
    if (host && onBg) host.onclick = (e) => {
      if (e.target.closest && e.target.closest('[data-seg],[data-part],[data-fold],[data-chain],a')) return;
      onBg();
    };
  }

  // ---------------------------------------------------------------- 分層關聯圖（SVG）
  /* ================================================================ 供應鏈環節卡清單
     Andy 2026-09-20：「供應鏈關聯圖 這邊我覺得上下框度太長，改成 顯示族群以及族群標題
     底下顯示個股小卡 如圖那樣」（他附的圖＝總覽「熱門題材」那種卡片）。

     為什麼一定要換掉版面，而不是把 SVG 縮小
     --------------------------------------------------
     那張關聯圖是「一個環節一欄、一家公司一張 36px 的卡」，所以**最高的那一欄有多高，
     整張圖就有多高**，其他欄下面全是空白。實測半導體鏈在 1500px 量到 1345px 高
     （整頁 4738px），而它最擠的那一欄只有 8 家。縮小只會讓字看不清，空白還是在。
     改成一格一張卡、用 CSS multi-column 讓卡片自己找位置塞，空白被擠掉，
     高度大約只剩三分之一 —— 這是版面的問題，不是字級的問題。

     ★ 換掉的代價（不可以裝作沒有）
     --------------------------------------------------
     SVG 畫的是 supply_chain.yaml 裡的 **140 條邊**：線粗＝依存度、虛線＝委外、
     點虛線＝終端指定料號、灰線＝設備／材料。清單上沒有線，所以這裡用三件事把關係接回來：
       ① 每張環節卡寫出「上游 ← 哪幾格、下游 → 哪幾格」，而且那幾格可以點（直接選過去）
       ② 每張個股小卡右下角一個數字＝**這家已經建立的上下游關係條數**；
          0 就沿用關聯圖那個橘色「?」（公開來源查不到具名客戶／供應商，寧可留白）
       ③ 點小卡照舊開右側「產業關係」面板 —— 那一塊把每條邊的品項、依存度、
          confidence（官方揭露／媒體報導／產業推論）攤開講，資訊量本來就比一條線多
     真的要看線本身（誰連到誰、多粗），右上角「看關聯圖」一鍵切回原本那張 SVG。

     漲跌沒有印在小卡上（Andy 的參考圖就是名稱＋代號兩行），改放進 title 提示；
     完整價量在第一個分頁的族群／個股漲幅長條圖上，那裡本來就照漲幅排好了。*/
  /* ---------------------------------------------------------------- 三個偏好
     （`tw.relView` 已於 2026-09-26 隨流向圖一起拿掉，renderChain 會把舊值清掉）
     `tw.segExpand` ：手機上環節卡是「全部展開」還是「只展開重點幾格」
     每次重畫都重讀，不要在模組載入時讀一次就算了 —— 使用者可能在別的分頁改過。*/
  const loadSegExpand = () => { try { return localStorage.getItem('tw.segExpand') === 'all'; } catch (e) { return false; } };
  const saveSegExpand = (v) => { try { localStorage.setItem('tw.segExpand', v ? 'all' : 'key'); } catch (e) { /* 忽略 */ } };
  /* 從外面選到某一格（點色標、點剖析圖零件、點公司卡）時，手機要順手把那張環節卡攤開。
     由 drawSegList 在每次重畫時重新指派；沒有清單的頁面它就是 null。*/
  let segListReveal = null;
  let segFoldMQ = null, segFoldFn = null;

  /* ================================================================ 關聯圖的欄寬與置中
     ★ 這一支就是 Andy「需要將關聯圖置中」那句話的落地點（2026-09-23 C5）。

     舊版（a846f16）把 SVG 寫成 `width:100%;max-width:W×1.25`，而 W 是「內容有多寬」——
     於是 1358px 的容器裡內容只佔左邊約 1020px，右邊空一大塊，而且整塊靠左。
     兩個毛病其實是同一個根因：**版面寬度沒有參與佈局計算**。

     現在反過來：先量容器有多寬，再決定欄寬與欄距 ——
       · 容器比自然寬度寬 → 先把欄加寬（卡片裡是名稱＋代號＋價格，寬一點更好讀），
         加到上限再把剩下的給欄距（走線的通道也跟著變寬，線不會擠在一起）
       · 容器比自然寬度窄 → 先把欄收窄到下限（178→132）再說；還是塞不下才讓它左右滑
     最後把剩下的空隙**左右對半**當內距，所以內容一定水平置中（誤差＝四捨五入的 0.5px）。

     `pad` 的下限刻意留 26px：同一欄的回頭線要從卡片右緣繞 24px 再回來，
     留不夠的話最後一欄那條線會被 viewBox 切掉（舊版就是靠 W 額外 +24 硬補，
     那 24px 只加在右邊，正是「看起來偏左」的另一半原因）。*/
  function fitCols(host, ncol, opt) {
    const o = opt || {};
    const PAD = o.pad != null ? o.pad : 26;
    let colW = o.colW || 178, colGap = o.gap || 30;
    const HW = Math.max(0, (host && host.clientWidth) || 0);
    const natural = () => ncol * colW + (ncol - 1) * colGap;
    if (HW > PAD * 2 + 80) {
      const avail = HW - PAD * 2;
      if (natural() < avail) {
        const maxColW = o.maxColW || 300, maxGap = o.maxGap || 96;
        // ① 先把欄加寬到「好讀」的上限
        colW = Math.min(maxColW, Math.floor((avail - (ncol - 1) * colGap) / ncol));
        // ② 還有剩就給欄距（走線的通道跟著變寬，線不會擠在一起）
        if (ncol > 1) colGap = Math.max(colGap, Math.min(maxGap, Math.floor((avail - ncol * colW) / (ncol - 1))));
        // ③ 欄距也頂到上限還有剩 → 回頭再把欄加寬。撐滿優先於「卡片不要太寬」，
        //    因為剩下的空白全部會變成左右內距，那正是 Andy 說的「右邊空一大塊」。
        colW = Math.min(o.hardColW || 380, Math.floor((avail - (ncol - 1) * colGap) / ncol));
      } else {
        /* 塞不下：先把欄距收到下限、再把欄寬收到下限。內距也一起讓步到 `padTight`——
           放不下的時候「同一欄回頭線那 24px 通道」的優先度，低於「整張圖不要變成左右滑」。*/
        const minColW = o.minColW || 132, minGap = o.minGap || 18, padTight = o.padTight || 16;
        const avail2 = HW - padTight * 2;
        colGap = minGap;
        colW = Math.max(minColW, Math.floor((avail2 - (ncol - 1) * colGap) / ncol));
        // 收完還有餘裕就把欄距加一點回來（線才不會貼著卡片走）
        if (ncol > 1 && ncol * colW + (ncol - 1) * colGap < avail2) {
          colGap = Math.min(o.gap || 30, Math.floor((avail2 - ncol * colW) / (ncol - 1)));
        }
      }
    }
    const CW = ncol * colW + (ncol - 1) * colGap;
    const padX = Math.max(CW + PAD * 2 <= HW ? PAD : (o.padTight || 16), Math.round((HW - CW) / 2));
    return { colW: colW, colGap: colGap, padX: padX, W: CW + padX * 2, CW: CW, HW: HW };
  }
  /* 量測用的標記：驗收（`_uitest.py` 批次25-關聯圖）讀這三個數字，再自己用
     getBoundingClientRect 對一次。寫在 DOM 上是為了「前端自己算的」與「畫面上量到的」
     對不上時一眼看得出是誰錯 —— 只寫其中一邊的話，錯了只會知道「有問題」。*/
  function markFit(host, f) {
    if (!host || !host.dataset) return;
    host.dataset.fill = (f.HW ? (f.CW / f.HW) * 100 : 0).toFixed(1);
    host.dataset.colw = String(f.colW);
    host.dataset.padx = String(f.padX);
  }

  /* ★ 2026-09-26 Andy：「刪除流向圖」—— 這裡原本是 drawSegFlow（第二種表達形式：節點＝環節、帶寬＝關係條數），
     整支拿掉。分層圖本身就看得到「誰接誰」，右欄與下拉看得到每一格有誰；流向圖多出來的只有「哪兩格關係條數最多」，
     而那是條數不是金額，讀起來容易被當成資金量。*/

  /* ==================================================================== 環節下拉 ＋ 選中環節的族群／個股
     Andy 2026-09-24 兩句話：
       「只留下供應鏈關聯圖，其他的用清單方式呈現族群以及個股」
       「上方標籤式的環節一律改成下拉清單（樣式參考資金輪動卡的『產業鏈：全部 ▾』）；
        下方那片環節字卡全部拿掉 —— 跟上面的關聯圖重複了」
     他看到的是：圖上方兩三排環節色標（銅箔／玻纖布／樹脂 6、IC 設計 4…）＋ 圖下方一整片環節字卡，
     同一份「每一格有誰」講了三次（色標、圖、字卡），真正的主角（圖）被夾在中間。

     ★ 下拉面板就是原本的 #segChips，每一列仍然是那顆 .segchip（data-seg、.nomem、.sel 全部沿用）：
       色標是這一頁「選一格」的總入口（syncHighlight 切 .sel、E6 跨鏈、十幾段驗收都認它），
       收進選單而不是另寫一個選單，篩選功能就一件都不會掉。
       手機（≤820px）用 CSS 把下拉鈕藏起來、面板攤開，看起來就是原本那一排色標 —— 手機這次不動。
     ★ #relList（圖右邊）只列**選中的那一格**：那一格有哪些族群、每個族群是哪幾檔、今天漲跌。
       全部都列就又是一份跟圖重複的字卡，所以沒選的時候整欄不顯示、圖用滿寬度。
       族群用 supply_chain.yaml 的 companies[].groups（取第一個，比環節細：IC 設計底下分成
       「HPC 與網通 IC」「顯示驅動 IC」…）。沒有台股的環節寫「外商」灰字並列出外商名字；
       連外商都沒有的（例：先進封裝 CoWoS/SoIC）寫它自己的 note —— 那句話本來就在解釋為什麼是空的。
       點個股＝進個股頁（一般連結，上一頁回得來、也能在新分頁開）。*/
  function renderSegPicker(chipHost, listHost, sc, segs, im) {
    const priceOf = {}; (im ? im.chains.flatMap(c => c.groups).concat(im.industries || []) : [])
      .forEach(g => (g.members || []).forEach(m => { if (!priceOf[m.code]) priceOf[m.code] = m; }));
    let nTw = 0;
    segs.forEach(s2 => { nTw += twOf(sc, s2.id).length; });
    if (chipHost) {
      /* 「全部環節」那一列只在下拉裡出現（class 是 segall，不是 segchip —— 驗收數色標時不會把它算進去）。
         色標內部結構（<i>、名稱、.n）一個都沒改：手機上它照舊長成一顆膠囊。*/
      chipHost.innerHTML = `<button type="button" class="segall on" data-seg="" role="option">全部環節<em>${segs.length} 格 · ${nTw} 檔</em></button>`
        + segs.map(s2 => {
          const tw = twOf(sc, s2.id), fo = foreignOf(sc, s2.id);
          return `<span class="segchip ${tw.length ? '' : 'nomem'}" role="option" data-seg="${s2.id}" style="--c:${segColor(s2.id)}" title="${tw.length ? tw.length + ' 檔台股' : '台股沒有直接對應，看外商'}"><i></i>${A.fmt.esc(s2.name)}<span class="n">${tw.length ? tw.length : (fo.length ? '外商 ' + fo.length : '—')}</span></span>`;
        }).join('');
    }
    if (!listHost) return;
    const sec = (s2) => {
      const tw = twOf(sc, s2.id), fo = foreignOf(sc, s2.id);
      /* 族群分組：保持 YAML 的順序（那是人工校訂過的），第一次出現的族群排前面 */
      const order = [], byG = {};
      tw.forEach(c => {
        const gn = (c.groups || [])[0] || '';
        if (!byG[gn]) { byG[gn] = []; order.push(gn); }
        byG[gn].push(c);
      });
      const row = (c) => {
        const m = priceOf[c.tw_code], chg = m ? m.chg_pct : null;
        const tip = `${c.name} ${c.tw_code}${m ? `｜收 ${A.fmt.n(m.close)}　${A.fmt.pct(chg)}` : ''}`;
        return `<a class="rlco" href="#stock/${c.tw_code}" data-code="${c.tw_code}" title="${A.fmt.esc(tip)}">`
          + `<span class="cd">${c.tw_code}</span><span class="nm">${A.fmt.esc(c.name)}</span>`
          + `<span class="chg ${chg == null ? 'flat' : A.fmt.cls(chg)}">${chg == null ? '—' : A.fmt.pct(chg)}</span></a>`;
      };
      const grp = (gn) => {
        const gid = gn ? A.L.gid[gn] : null;
        const label = gid ? A.L.group(gid, gn, { cls: 'rlgn' }) : `<span class="rlgn muted">${gn ? A.fmt.esc(gn) : '未歸族群'}</span>`;
        return `<div class="rlgrp"><div class="rlgh">${label}<span class="n">${byG[gn].length} 檔</span></div>${byG[gn].map(row).join('')}</div>`;
      };
      /* ★ 2026-10-03（DECISIONS #310）：只有外商的環節（面板材料＝康寧、終端品牌＝Apple／SpaceX）在桌機右欄只剩一行外商名字，
         點進來沒有任何東西可以往下點 —— 09-19 補一般電子鏈時要的是「點只有外商的那一格要接得到台股族群」（app.js FALLBACK），
         手機的環節詳情 #segBox 一直有「相關族群」那一列，桌機 #segBox 拿掉（29149fc）之後這一列沒有搬過來。
         補回來：沒有台股時列出 A.L.sgroups 的族群連結（跟 #segBox 同一份資料、同一個 A.L.group 連結）。有台股的環節不加（族群已經是分組標題）。*/
      const fbG = tw.length ? [] : ((A.L.sgroups || {})[s2.id] || []);
      const body = order.map(grp).join('')
        + (fo.length ? `<div class="rlfo"><span class="fo">外商</span>${fo.map(c => A.fmt.esc(c.name)).join('、')}</div>` : '')
        + (fbG.length ? `<div class="rlfo rlfb"><span class="fo">相關台股族群</span>${fbG.map(g => A.L.group(g)).join(' ')}</div>` : '')
        + (tw.length || fo.length ? '' : `<div class="rlnt">${A.fmt.esc(s2.note || '台股無直接對應')}</div>`);
      return `<div class="rlseg" data-seg="${s2.id}" style="--c:${segColor(s2.id)}">`
        + `<div class="rlsh"><i></i><b>${A.fmt.esc(s2.name)}</b><span class="n">${tw.length ? tw.length + ' 檔' : (fo.length ? '外商 ' + fo.length : '—')}</span>`
        + `<button type="button" class="rlx" data-seg="${s2.id}" title="取消選取這一格" aria-label="取消選取">×</button></div>`
        + `<div class="rlbody">${body}</div></div>`;
    };
    listHost.innerHTML = segs.map(sec).join('');
  }
  /* 關聯圖是不是桌機的「下拉＋圖（＋右欄）」版面。手機（≤820px）照舊是一排色標。*/
  const relListMode = () => { try { return window.matchMedia('(min-width:821px)').matches; } catch (e) { return false; } };
  /* ★ 2026-09-26 晚（Andy：「點選族群（環節）時，不會動到關聯圖版面，例如我點最右邊的族群，資訊會顯示在左側，同理顯示右側」）：
     關聯圖的說明卡（.relcol：選中環節的族群清單＋公司資訊欄）浮在圖上，這支決定它貼哪裡。
     規則：
       ① 被點的環節（那一欄的標題列）中心在圖框右半邊 → 卡片貼圖框**左緣**；在左半邊 → 貼**右緣**。
          環節欄寬 136～200px，卡片 260～320px，圖框至少 800px，所以「放到另一半」一定不會蓋到那一欄。
       ② 垂直對齊被點的東西（點公司 → 那張公司卡；點環節 → 環節標題），再夾進圖框的可視範圍裡；
          卡片高度上限＝圖框高度（最多 560px 或視窗高減 120），內容多就在卡片裡自己捲。
       ③ 圖框太窄、兩邊都擺不下（821～900px、或圖本身在左右滑）→ 改放在那一欄的**上方或下方**：
          先試那一格整欄（標題＋底下的公司）的下面，不夠再試標題上面，都不夠就放到圖框下緣之外。
          寬度一律夾在圖框內，所以不會撐出橫向捲軸。
     量的是畫面座標（getBoundingClientRect）再換成 .relmain 的座標 —— SVG 有 viewBox 縮放，直接讀 SVG 座標會差一個比例。
     驗收用：data-side＝left／right／below／above／under（貼哪裡）、data-seg＝以哪一格為準。*/
  function placeRelCol(root) {
    const rm = root && root.querySelector('#relMain'); if (!rm) return;
    const col = rm.querySelector('.relcol'), stick = rm.querySelector('.relstick'); if (!col || !stick) return;
    const reset = () => { col.style.left = ''; col.style.top = ''; col.style.width = ''; stick.style.removeProperty('--rc-h');
      delete col.dataset.side; delete col.dataset.seg; };
    const map = rm.querySelector('#chainMap');
    const coBox = document.getElementById('coBox');
    const open = rm.classList.contains('hassel') || !!(coBox && rm.contains(coBox));
    if (!relListMode() || rm.classList.contains('mapfold') || !open || !map || map.hidden) { reset(); return; }
    const R = rm.getBoundingClientRect(), M = map.getBoundingClientRect();
    if (!(R.width > 0) || !(M.width > 0)) { reset(); return; }
    // 以誰為準：開著公司資訊欄 → 那家公司（與它的環節）；否則 → 右欄亮著的那一格
    const coEl = coBox && coBox.dataset.co ? map.querySelector(`.co[data-id="${coBox.dataset.co}"]`) : null;
    const seg = (coEl && coEl.dataset.segment) || ((rm.querySelector('#relList .rlseg.on') || { dataset: {} }).dataset.seg);
    const tEl = seg ? map.querySelector(`.segtitle[data-seg="${seg}"]`) : null;
    const T = tEl ? tEl.getBoundingClientRect() : (coEl ? coEl.getBoundingClientRect() : null);
    const pad = 8, gap = 10;
    // 圖框的可視範圍（扣掉圖自己的捲軸），換成 .relmain 的座標
    const fL = M.left - R.left + pad, fR = M.left - R.left + map.clientWidth - pad;
    let fT = M.top - R.top + pad;
    const fB = M.top - R.top + map.clientHeight - pad;
    /* ★ 2026-10-03（DECISIONS #310）：圖框最上面那一列是「全部展開／全部收合」切換鈕（.foldbar，整張圖共用的控制）。
       改前：卡片上緣夾在圖框頂 + 8px，1440 寬點右半邊的公司（台積電、南亞科、日月光…）→ 卡片貼左、正好蓋住那顆鈕，
       elementFromPoint 量到的是卡片裡的 h3 —— 卡片開著時「全部展開」按不到（13 檔抽樣 8 檔被蓋）。
       改後：可放的範圍從切換列的下緣開始，卡片永遠在它下面；切換列只有一行字高，卡片的可用高度只少約 30px。*/
    const fbar = map.querySelector(':scope > .foldbar');
    if (fbar) { const B = fbar.getBoundingClientRect(); if (B.height > 0) fT = Math.max(fT, B.bottom - R.top + 6); }
    const w = Math.round(Math.max(200, Math.min(fR - fL, Math.max(260, Math.min(320, R.width * 0.26)))));
    const maxH = Math.round(Math.max(180, Math.min(fB - fT, 560, window.innerHeight - 120)));
    col.style.width = w + 'px';
    stick.style.setProperty('--rc-h', maxH + 'px');
    const h = col.offsetHeight || 200;
    col.dataset.seg = seg || '';
    const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
    if (!T) { col.style.left = Math.round(fR - w) + 'px'; col.style.top = Math.round(fT) + 'px'; col.dataset.side = 'right'; return; }
    const sL = T.left - R.left, sR = T.right - R.left, mid = (sL + sR) / 2;
    const ar = (coEl || tEl).getBoundingClientRect();
    const aTop = ar.top - R.top - 4;
    const yIn = Math.round(clamp(aTop, fT, Math.max(fT, fB - h)));
    const fitsL = fL + w <= sL - gap, fitsR = fR - w >= sR + gap;
    const want = mid > (fL + fR) / 2 ? 'left' : 'right';
    const side = want === 'left' ? (fitsL ? 'left' : (fitsR ? 'right' : null)) : (fitsR ? 'right' : (fitsL ? 'left' : null));
    if (side) {
      col.style.left = Math.round(side === 'left' ? fL : fR - w) + 'px';
      col.style.top = yIn + 'px';
      col.dataset.side = side;
      return;
    }
    // ③ 兩邊都擺不下：放在那一欄的上方或下方（整欄＝標題＋它底下的公司卡／標籤）
    let segB = T.bottom;
    map.querySelectorAll(`.co[data-segment="${seg}"]`).forEach(c => { const r = c.getBoundingClientRect(); if (r.height > 0) segB = Math.max(segB, r.bottom); });
    const x = Math.round(clamp(mid - w / 2, fL, Math.max(fL, fR - w)));
    const below = segB - R.top + gap, above = T.top - R.top - gap - h;
    let y, where;
    if (below + h <= fB) { y = below; where = 'below'; }
    else if (above >= fT) { y = above; where = 'above'; }
    else { y = M.top - R.top + map.offsetHeight + gap; where = 'under'; }   // 圖框下緣之外（仍是覆蓋層，不推版面）
    col.style.left = x + 'px'; col.style.top = Math.round(y) + 'px'; col.dataset.side = where;
  }
  /* ★ 設計 v4 第二批 2B：產業鏈頁的鏈名標題跟二層分頁列「放得下才併成一列」。
     放得下＝加上 .nbinl（標題浮在左邊、分頁列接在右邊）之後，分頁列自己沒有被擠出橫向捲動。
     手機（≤640）不併（手機版面這一批不動）。全站只掛一個 resize 監聽，量的是畫面上現在那一張 .nbcard。*/
  function fitNbHead(card) {
    if (!card) return;
    const head = card.querySelector(':scope>.nbhead'), sw = card.querySelector(':scope>#dgPick');
    card.classList.remove('nbinl');
    if (!head || !sw || !(window.innerWidth > 640)) return;
    card.classList.add('nbinl');
    if (sw.scrollWidth > sw.clientWidth + 1) card.classList.remove('nbinl');
  }
  let nbFitT = 0;
  window.addEventListener('resize', () => { clearTimeout(nbFitT); nbFitT = setTimeout(() => {
    const c = document.querySelector('#indChain .nbcard'); if (c && c.isConnected) fitNbHead(c); }, 150); });
  /* 下拉的開合。點外面、按 Esc、選好一格都會收起來；只在第一次掛全站的監聽器（換鏈不會一路疊上去）。*/
  let segDDWired = false;
  function wireSegDD(root) {
    const dd = $('#segDD', root), btn = $('#segDDBtn', root);
    if (!dd || !btn) return;
    const setOpen = (on) => { dd.classList.toggle('open', on); btn.setAttribute('aria-expanded', on ? 'true' : 'false');
      if (on) { const s = $('#segChips .segchip.sel', dd); if (s && s.scrollIntoView) s.scrollIntoView({ block: 'nearest' }); } };
    btn.onclick = (ev) => { ev.stopPropagation(); setOpen(!dd.classList.contains('open')); };
    if (!segDDWired) {
      segDDWired = true;
      document.addEventListener('click', (ev) => {
        const cur = document.getElementById('segDD');
        if (cur && cur.classList.contains('open') && !cur.contains(ev.target)) { cur.classList.remove('open'); const b = document.getElementById('segDDBtn'); if (b) b.setAttribute('aria-expanded', 'false'); }
      });
      document.addEventListener('keydown', (ev) => {
        if (ev.key !== 'Escape') return;
        const cur = document.getElementById('segDD');
        if (cur && cur.classList.contains('open')) { cur.classList.remove('open'); const b = document.getElementById('segDDBtn'); if (b) { b.setAttribute('aria-expanded', 'false'); b.focus(); } }
      });
    }
    return setOpen;
  }

  /* ==================================================================== 環節說明框（滑過環節時）
     Andy 看到的是：滑過「先進封裝 CoWoS/SoIC」時，說明框窄到字一個一個斷行
     （「CoWoS/SoIC 由台 / 積電自己做…」）。SVG 的 <title> 是瀏覽器原生提示，寬度與斷行都管不到，
     所以改成自己畫的說明框：寬度 240～360px、正常斷行（中文不會被拆成一字一行）、跟著游標走、不吃滑鼠。
     內容一次講完：這一格是什麼、台股幾檔／外商幾家、說明（desc／note）、上游是誰、下游是誰 ——
     清單上沒有線，上下游就靠這裡補回來。
     只在有滑鼠的裝置掛（hover:hover）；觸控裝置沒有「滑過」，點下去本來就會選起那一格。*/
  function segTipHtml(sc, chainId, seg) {
    const s = (sc && sc.segments.find(x => x.id === seg)) || null; if (!s) return '';
    const segs = chainSegments(sc, chainId), ids = new Set(segs.map(x => x.id));
    const coSeg = {}; sc.companies.forEach(c => { if (ids.has(c.segment)) coSeg[c.id] = c.segment; });
    const up = new Set(), dn = new Set();
    (sc.edges || []).forEach(e => {
      if (e.rel === 'competes') return;
      const a = coSeg[e.from], b = coSeg[e.to]; if (!a || !b || a === b) return;
      if (b === seg) up.add(a); if (a === seg) dn.add(b);
    });
    const tw = twOf(sc, seg).length, fo = foreignOf(sc, seg).length;
    const nm = (set) => [...set].map(x => A.fmt.esc(segName(sc, x))).join('、') || '（沒有）';
    const txt = [s.desc, s.note].filter(Boolean).map(A.fmt.esc).join('　');
    return `<b style="color:${segColor(seg)}">${A.fmt.esc(s.name)}</b>`
      + `<div class="rtn">${tw ? tw + ' 檔台股' : '沒有台股'}${fo ? ' · 外商 ' + fo + ' 家' : ''}</div>`
      + (txt ? `<div class="rtd">${txt}</div>` : '')
      + `<div class="rtr"><span class="k">上游</span>${nm(up)}</div><div class="rtr"><span class="k">下游</span>${nm(dn)}</div>`;
  }
  function wireSegTip(root, sc, chainId) {
    if (!root || !sc) return;
    let can = true; try { can = window.matchMedia('(hover:hover)').matches; } catch (e) { /* 舊瀏覽器當成有滑鼠 */ }
    if (!can) return;
    let tip = document.getElementById('relTip');
    if (!tip) {
      tip = document.createElement('div'); tip.id = 'relTip'; tip.className = 'reltip'; tip.hidden = true; document.body.appendChild(tip);
      /* 換頁／捲動時一定要收掉：position:fixed 的框不收會留在原地，壓在別頁的內容上。
         只在第一次建立說明框時掛一次 —— 每畫一次鏈就掛一次的話，監聽器會一路疊上去。*/
      const off = () => { tip.hidden = true; tip._seg = null; };
      window.addEventListener('scroll', off, { passive: true });
      window.addEventListener('hashchange', off);
    }
    const SEL = '#chainMap .segtitle, #chainMap .segnote';
    const place = (ev) => {
      const r = tip.getBoundingClientRect(), W = window.innerWidth, H = window.innerHeight;
      let x = ev.clientX + 14, y = ev.clientY + 16;
      if (x + r.width > W - 8) x = Math.max(8, ev.clientX - r.width - 14);
      if (y + r.height > H - 8) y = Math.max(8, ev.clientY - r.height - 12);
      tip.style.left = Math.round(x) + 'px'; tip.style.top = Math.round(y) + 'px';
    };
    const hide = () => { tip._seg = null; tip.hidden = true; };
    root.addEventListener('mouseover', (ev) => {
      const t = ev.target.closest && ev.target.closest(SEL);
      if (!t || !root.contains(t)) return;
      const seg = t.dataset.seg; if (!seg) return;
      if (tip._seg !== seg) { const h = segTipHtml(sc, chainId, seg); if (!h) return; tip.innerHTML = h; tip._seg = seg; }
      tip.hidden = false; place(ev);
    });
    root.addEventListener('mousemove', (ev) => { if (!tip.hidden && tip._seg) place(ev); });
    root.addEventListener('mouseout', (ev) => {
      const t = ev.target.closest && ev.target.closest(SEL); if (!t) return;
      const to = ev.relatedTarget && ev.relatedTarget.closest ? ev.relatedTarget.closest(SEL) : null;
      if (to !== t) hide();
    });
  }

  /* ==================================================================== 環節卡清單（Default 畫面）
     ★ 這就是 Andy「Default 顯示族群相連標籤個股」那句話的落地點：
       不用點任何東西，就看得到每一格的「上游 ← 哪幾格、下游 → 哪幾格」與底下的個股標籤。
     退版自 a846f16；行為一模一樣，只有註解與 `#segBox` 預設收起那條規則是這次補的。*/
  function drawSegList(host, sc, chainId, im, handlers) {
    if (!host) return { nSeg: 0, nTw: 0, nEdge: 0 };
    // 依 layer 排序＝由上游排到下游；同一層維持 YAML 的順序（那是人工校訂過的）
    /* handlers.focus()：要反亮的環節（上方剖析圖畫到的那幾格，見 renderChain 的 relScopeNow）；null／空＝沒有反亮。
       ★ 2026-10-03 晚（DECISIONS #317）：清單一律列整條鏈，不再只留那幾格（#306 的 only 拿掉）。*/
    const focus0 = handlers && typeof handlers.focus === 'function' ? handlers.focus() : null;
    const focus = focus0 && focus0.size ? focus0 : null;
    const segs = chainSegments(sc, chainId).slice().sort((a, b) => (a.layer || 0) - (b.layer || 0));
    const segIds = new Set(segs.map(s => s.id));
    const cos = sc.companies.filter(c => segIds.has(c.segment));
    const inChain = new Set(cos.map(c => c.id));
    const coSeg = {}; cos.forEach(c => (coSeg[c.id] = c.segment));
    const priceOf = {}; (im ? im.chains.flatMap(c => c.groups).concat(im.industries || []) : [])
      .forEach(g => (g.members || []).forEach(m => { priceOf[m.code] = m; }));
    /* 度數與環節層級的上下游，都只算「兩端都在這條鏈上」的邊 —— 跟關聯圖同一個口徑，
       不然同一家公司在圖上沒有線、在清單上卻掛著一個數字，兩邊會對不起來。*/
    /* 度數（「?」＝沒有任何上下游關聯）與每格的上下游照**整條鏈**算；nEdge 是兩端都在這條鏈上的邊，給「怎麼看 ?」那行數字用。*/
    const fullSegIds = new Set(chainSegments(sc, chainId).map(s => s.id));
    const coSegAll = {}; sc.companies.forEach(c => { if (fullSegIds.has(c.segment)) coSegAll[c.id] = c.segment; });
    const deg = {}, upS = {}, dnS = {}; let nEdge = 0;
    (sc.edges || []).forEach(e => {
      if (e.rel === 'competes' || !coSegAll[e.from] || !coSegAll[e.to]) return;
      if (inChain.has(e.from) && inChain.has(e.to)) nEdge++;
      deg[e.from] = (deg[e.from] || 0) + 1; deg[e.to] = (deg[e.to] || 0) + 1;
      const a = coSegAll[e.from], b = coSegAll[e.to];
      if (a !== b) { (dnS[a] = dnS[a] || new Set()).add(b); (upS[b] = upS[b] || new Set()).add(a); }
    });
    const ROLE = { equipment: '設備', material: '材料' };
    /* 上下游那兩行是版面高度的大戶：不縮寫的話兩三個就換行，一張卡多 34px、20 格就是 680px。
       所以顯示縮寫、每個方向只列 1 格、其餘收成「+N」，完整名稱留在 title。
       只列 1 格還有一個理由：欄寬只有 236px，列 2 格會**真的溢出卡片** ——
       雖然 overflow:hidden 看起來沒事，但溢出去的字框在版面上仍然壓在隔壁欄的卡片上，
       `_preview.py` 的重疊掃描量的就是字框，會判成壓字。*/
    const shortSeg = (nm) => { const t = String(nm).split(/[（(]/)[0].split(/\s*\/\s*/)[0].trim();
      return t.length > 5 ? t.slice(0, 5) + '…' : (t || nm); };
    const NBR_MAX = 1;
    const nbr = (set) => { const ids = [...(set || [])];
      const head = ids.slice(0, NBR_MAX).map(id =>
        `<span class="sg" data-seg="${id}" style="--c:${segColor(id)}" title="切到「${A.fmt.esc(segName(sc, id))}」這一格">${A.fmt.esc(shortSeg(segName(sc, id)))}</span>`).join('');
      const rest = ids.slice(NBR_MAX);
      return head + (rest.length ? `<span class="more" title="${A.fmt.esc(rest.map(id => segName(sc, id)).join('、'))}">+${rest.length}</span>` : ''); };
    const mini = (c) => {
      const m = c.tw_code ? priceOf[c.tw_code] : null;
      const n = deg[c.id] || 0;
      const tip = `${c.name}${c.tw_code ? ' ' + c.tw_code : '（外商）'}`
        + (m ? `｜${A.fmt.n(m.close)} ${A.fmt.pct(m.chg_pct)}` : '')
        + (n ? `｜${n} 條上下游關係` : '');
      /* 名稱不在這裡切字 —— 標籤是用 grid 排的，切幾個字要看欄寬，JS 算不準。
         交給 CSS 的 text-overflow:ellipsis，完整名稱留在 title。*/
      return `<button type="button" class="sco${c.tw_code ? '' : ' foreign'}" data-id="${c.id}" data-segment="${c.segment}" data-code="${c.tw_code || ''}"`
        + `${m && m.chg_pct != null ? ` style="--u:${A.upDown(m.chg_pct)}"` : ''} title="${A.fmt.esc(tip)}">`
        + `<span class="nm">${A.fmt.esc(c.name)}</span>`
        + (c.tw_code ? `<span class="code">${c.tw_code}</span>` : '<span class="code fo">外商</span>')
        + `<i class="rel${n ? '' : ' iso'}">${n || '?'}</i></button>`;
    };
    const flowTip = (id) => {
      const nm = (set) => [...(set || [])].map(x => segName(sc, x)).join('、') || '（沒有）';
      return `上游：${nm(upS[id])}\n下游：${nm(dnS[id])}`;
    };
    /* ---------------------------------------------------------------- 手機的「重點展開」
       390px 一欄，14~20 個環節全攤開一定很長。量出來的成本結構是
       「每張卡固定成本 ~70px × 環節數」遠大於標籤本身，所以收的**不是標籤，是卡片的數量**：
       手機（≤560px）預設展開台股檔數最多的前 4 格，其餘只留標題列與一顆 ▾。
       ★ 不可以改成「把個股標籤收起來」—— Andy 的原始需求就是「Default 顯示族群相連標籤個股」。
       ★ 為什麼是「整段 DOM 拆下來」而不是 display:none：隱藏起來的標籤**版面框還在**，
         `_uitest.py` 量的就是這些框，會判成「標籤跑出環節卡」。*/
    const MOBILE_OPEN = 4;
    /* 有反亮（剖析圖分頁）時，手機預設展開的是「反亮的那幾格」裡台股最多的前 4 格 —— 使用者是從那張圖下來的（DECISIONS #317）。*/
    const openIds = new Set(segs.filter(s => !focus || focus.has(s.id))
      .map((s, i) => ({ id: s.id, i, n: cos.filter(c => c.segment === s.id && c.tw_code).length }))
      .sort((a, b) => (b.n - a.n) || (a.i - b.i)).slice(0, MOBILE_OPEN).map(x => x.id));
    let nTw = 0;
    host.innerHTML = segs.map(s => {
      const list = cos.filter(c => c.segment === s.id);
      const tw = list.filter(c => c.tw_code), fo = list.filter(c => !c.tw_code);
      nTw += tw.length;
      const tags = tw.concat(fo).map(mini).join('');
      const body = `${upS[s.id] || dnS[s.id] ? `<div class="sf" title="${A.fmt.esc(flowTip(s.id))}">${upS[s.id] ? `<span class="lb">上游</span>${nbr(upS[s.id])}` : ''}${dnS[s.id] ? `<span class="lb">下游</span>${nbr(dnS[s.id])}` : ''}</div>` : ''}`
        + `${tags ? `<div class="sms">${tags}</div>` : ''}`
        + `${list.length ? '' : `<div class="nt">${A.fmt.esc(s.note || '（台股無直接對應）')}</div>`}`;
      // 沒有公司的環節只有一段說明文字，收起來反而什麼都不剩 —— 那種卡片不給收合鈕
      const foldable = list.length > 0;
      return `<div class="segcard${openIds.has(s.id) ? ' pin' : ''}${focus ? (focus.has(s.id) ? ' relfocus' : ' relout') : ''}" data-seg="${s.id}" data-n="${list.length}" style="--c:${segColor(s.id)}">
        <div class="sh"><i class="dot"></i><b class="nm">${A.fmt.esc(s.name)}</b>${ROLE[s.role] ? `<span class="rl">${ROLE[s.role]}</span>` : ''}<span class="cnt">${tw.length ? tw.length + ' 檔' : (fo.length ? '外商 ' + fo.length : '—')}</span>${foldable ? '<button type="button" class="sx" aria-expanded="true">▾</button>' : ''}</div>
        <div class="sb">${body}</div></div>`;
    }).join('');
    // 點卡片本身＝選這一格；點標籤、上下游名稱、收合鈕各自有自己的動作，不要一起觸發
    $$('.segcard', host).forEach(card => { card.onclick = (ev) => {
      if (ev.target.closest('.sco') || ev.target.closest('.sg') || ev.target.closest('.sx')) return;
      if (handlers && handlers.onSegment) handlers.onSegment(card.dataset.seg); }; });
    $$('.segcard .sf .sg', host).forEach(t => { t.onclick = (ev) => {
      ev.stopPropagation(); if (handlers && handlers.onSegment) handlers.onSegment(t.dataset.seg); }; });
    $$('.segcard .sco', host).forEach(n => { n.onclick = (ev) => {
      ev.stopPropagation();
      const co = cos.find(c => c.id === n.dataset.id); if (!co) return;
      closeCoBox();
      // Andy：「點擊股票 右側會顯示對應訊息」—— 原地開右側資訊欄（不跳頁），再同步選起它的環節
      showCompany(co, sc, host);
      if (handlers && handlers.onCompany) handlers.onCompany(co); }; });

    /* ---- 展開／收合：事件全部綁完之後才拆 DOM，拆下來的節點事件還在，掛回去就能點 ---- */
    const cards = $$('.segcard', host);
    cards.forEach(c => { c._sb = c.querySelector('.sb'); });
    const narrow = () => { try { return window.matchMedia('(max-width:560px)').matches; } catch (e) { return false; } };
    let expandAll = loadSegExpand();
    const setOpen = (card, open) => {
      if (!card._sb) return;
      if (open && !card._sb.parentNode) card.appendChild(card._sb);
      else if (!open && card._sb.parentNode) card._sb.remove();
      card.classList.toggle('open', open);
      const x = $('.sx', card);
      if (x) { x.setAttribute('aria-expanded', open ? 'true' : 'false');
        x.title = open ? '收起這一格的個股標籤' : `展開這一格的 ${card.dataset.n} 檔個股標籤`; }
    };
    const wantOpen = (c) => {
      // 沒有公司的環節（只有一段說明文字）沒有收合鈕，收起來會什麼都不剩 —— 一律攤開
      if (!c._sb || !$('.sx', c)) return true;
      if (!narrow() || expandAll) return true;
      if (c.dataset.user) return c.dataset.user === '1';
      return c.classList.contains('pin');
    };
    const applyFold = () => cards.forEach(c => setOpen(c, wantOpen(c)));
    $$('.segcard .sx', host).forEach(x => { x.onclick = (ev) => {
      ev.stopPropagation();
      const card = x.closest('.segcard'); const open = !card.classList.contains('open');
      card.dataset.user = open ? '1' : '0'; setOpen(card, open); }; });
    segListReveal = (card) => { if (card && card._sb && !card.classList.contains('open')) {
      card.dataset.user = '1'; setOpen(card, true); } };

    // 上方的總開關（只在手機顯示，CSS 控制）
    const tools = host.previousElementSibling && host.previousElementSibling.classList.contains('segtools')
      ? host.previousElementSibling : null;
    if (tools) {
      const paint = () => { const b = $('.segx', tools);
        if (b) b.textContent = expandAll ? '只展開重點' : '全部展開';
        const t = $('.segxn', tools);
        if (t) t.textContent = expandAll
          ? `已全部展開（${segs.length} 格）`
          : `已展開個股最多的 ${Math.min(MOBILE_OPEN, segs.length)} 格`; };
      tools.innerHTML = '<button type="button" class="btn small segx"></button><span class="muted segxn"></span>';
      $('.segx', tools).onclick = () => {
        expandAll = !expandAll; saveSegExpand(expandAll);
        cards.forEach(c => delete c.dataset.user);   // 總開關按下去＝重新來過，蓋掉個別卡片的選擇
        applyFold(); paint();
      };
      paint();
    }
    applyFold();
    // 轉橫向／改視窗寬度跨過 560px 時要重算，不然桌機會留著手機的收合狀態。
    // 掛新的之前先把上一條鏈的拆掉，否則每換一條鏈就多疊一個監聽器。
    try {
      if (segFoldMQ && segFoldFn) segFoldMQ.removeEventListener('change', segFoldFn);
      segFoldMQ = window.matchMedia('(max-width:560px)'); segFoldFn = applyFold;
      segFoldMQ.addEventListener('change', segFoldFn);
    } catch (e) { /* 舊瀏覽器沒有 addEventListener 就算了，重新整理一樣會對 */ }
    return { nSeg: segs.length, nTw: nTw, nEdge: nEdge };
  }

  function drawChainMap(host, sc, chainId, im, handlers) {
    if (!host) return;
    /* ★ 2026-10-03 晚（Andy：「下方的關聯圖為何其他的都不見了，需要有對應那族群的所有關聯圖，並且反亮那族群」，DECISIONS #317）：
       一律畫整條鏈。handlers.focus() 回傳「上方這張剖析圖上真的出現的環節」—— 那幾格反亮（亮框亮底）、其餘淡一點（paintRelFocus）。
       null／空＝族群總覽分頁（沒有剖析圖），沒有反亮。交集是空集合時 renderChain 直接把整塊關聯圖藏起來，不會走到這裡。*/
    const focus0 = handlers && typeof handlers.focus === 'function' ? handlers.focus() : null;
    const focus = focus0 && focus0.size ? focus0 : null;
    const segs = chainSegments(sc, chainId);
    const layers = [...new Set(segs.map(s => s.layer))].sort((a, b) => a - b);
    const cos = sc.companies.filter(c => segs.some(s => s.id === c.segment));
    const priceOf = {}; (im ? im.chains.flatMap(c => c.groups).concat(im.industries || []) : []).forEach(g => (g.members || []).forEach(m => { priceOf[m.code] = m; }));
    /* ★ 2026-09-23 C5：欄寬、欄距、左右內距全部改成依容器寬度算（見 fitCols 的註解）。
       舊版寫死 `colW=178, padX=14, colGap=30` 再配上 `max-width:W×1.25`，
       1358px 的容器只用掉左邊約 1020px —— 那就是 Andy 說「需要將關聯圖置中」的那個毛病。*/
    /* ★ 2026-09-24（審查 R3：金融鏈分層圖只用到 28% 寬）：整條鏈**一條上下游都沒有**時，
       「一層一欄」沒有意義（沒有線要走、上下游也分不出來），金融鏈 3 個環節全擠在同一欄、左右各空 480px。
       這種時候改成**一個環節一欄**：寬度用得開、高度也跟著縮，圖上方再明講「這條鏈沒有可畫的上下游關係」。
       有任何一條邊就照舊一層一欄 —— 那時候欄的左右就是上下游，不能拆。*/
    const inChain0 = new Set(cos.map(c => c.id));
    const nEdge0 = (sc.edges || []).filter(e => e.rel !== 'competes' && inChain0.has(e.from) && inChain0.has(e.to)).length;
    const noEdge = nEdge0 === 0 && segs.length > layers.length;
    const layerCols = noEdge ? segs.length : layers.length;
    const fit = fitCols(host, layerCols, { colW: 178, gap: 30, maxColW: 260, maxGap: 86, minColW: 136, minGap: 18, pad: 26 });
    const colW = fit.colW, colGap = fit.colGap, padX = fit.padX;
    const cardH = 36, gapY = 8, padY = 36;
    const bySeg = {}; cos.forEach(c => (bySeg[c.segment] = bySeg[c.segment] || []).push(c));
    const cols = noEdge ? segs.map(s => [s]) : layers.map(Lr => segs.filter(s => s.layer === Lr));
    let maxH = 0; const pos = {};
    /* 沒有台股的環節要顯示 note（見下面的 nodes 迴圈）。那幾行字**要先算進版面高度**，
       不然它會壓到下一個環節的標題列 —— 2026-09-19 實測到「先進封裝 CoWoS/SoIC」的說明
       整段蓋在「封測 / 測試」上面。*/
    /* 一行放多少：以前寫死 13 字（欄寬 178 − 左右留白 12 = 166px、11px 字級的安全值；
       切 18 字會超出欄寬壓到隔壁欄，2026-09-19 用 getBBox 量到的）。
       ★ 2026-09-24 改成依**實際欄寬**算：欄寬現在依容器在 136～260 之間變，寫死 13 的話
       寬的時候一樣 13 字一行，看起來就是「字一個一個斷行」（Andy 回報的「CoWoS/SoIC 由台 / 積電自己做」）。
       上限仍然是欄寬本身，所以不會重演超出欄寬那個坑。完整說明另外有滑過才出現的說明框（wireSegTip）。
       依**字寬**斷行：中文與全形標點約 11px、英數約 6.5px（11px 字級量出來的）。
       以前一律當成一字 11px，所以「CoWoS/SoIC」這種英數混排會被切得特別碎。
       快滿的時候（最後 3 個字以內）剛好遇到「，」「）」「、」就在那裡斷，不把詞從中間切開。*/
    /* ★ 2026-10-03（Andy：「供應鏈關聯圖族群需要框線框起來比較簡潔」）：每個環節包一個 1px 細框（.segbox）。
       框的外緣＝欄的外緣（x 到 x＋colW），**不往欄距外擴** —— 欄距最窄只有 18px，走線的通道（gapMid）就在那裡，
       外擴會讓豎線貼著或穿過隔壁的框。所以改成「框不動、裡面的東西往內縮 SEG_IN」：
       標題色塊內縮 3px、晶片與公司卡內縮 6px、說明文字從 +10 開始。
       連線端點仍接在 coPos（＝框的左右緣），所以線停在框邊、不會伸進框裡。*/
    const SEG_IN = 6, inW = colW - SEG_IN * 2;
    const NOTE_W = inW - 4, NOTE_LH = 16, NOTE_MAX = 5;   // 文字從欄左 +6 開始，右邊留 4px；5 行（高度已算進 noteLines）
    /* 字寬用畫布真的量（字級沿用這個框實際吃到的字型；量不到就退回「中文 13、英數 7.5」的估計）。
       ⚠ 這段 SVG 文字沒有自己的字級規則，吃的是繼承下來的 13px，不是註解上寫的 11px —— 用猜的會溢出欄寬。*/
    const cs0 = (() => { try { return getComputedStyle(host); } catch (e) { return null; } })();
    const ctx0 = (() => { try { const c = document.createElement('canvas').getContext('2d');
      c.font = `${(cs0 && cs0.fontSize) || '13px'} ${(cs0 && cs0.fontFamily) || 'sans-serif'}`; return c; } catch (e) { return null; } })();
    const chW = (ch) => (ctx0 ? ctx0.measureText(ch).width : (/[\u0000-ÿ]/.test(ch) ? 7.5 : 13));
    const CLOSE = '，）、。)';
    const noteWrap = (txt) => {
      const t = String(txt || ''), out = [];
      let line = '', w = 0, lastP = -1;
      for (const ch of t) {
        const cw = chW(ch);
        /* 收尾標點不准落在行首（避頭點）：讓它吊在上一行的行尾，最多伸進欄距一個字寬（欄距最小 18px，不會碰到隔壁欄） */
        if (w + cw > NOTE_W && line && !CLOSE.includes(ch)) {
          if (lastP >= line.length - 3 && lastP > 0) { out.push(line.slice(0, lastP + 1)); line = line.slice(lastP + 1); }
          else { out.push(line); line = ''; }
          w = [...line].reduce((a, c) => a + chW(c), 0); lastP = -1;
        }
        line += ch; w += cw;
        if ('，）、。'.includes(ch)) lastP = line.length - 1;
      }
      if (line) out.push(line);
      return out.map(x => x.trim()).filter(Boolean);
    };
    const noteLines = (sg, list) => (list.length ? 0 : Math.min(NOTE_MAX, noteWrap(sg.note || '台股無直接對應').length));
    /* ★ 2026-09-23 C5 優化：**每一欄各自垂直置中**。
       舊版每一欄都從最上面開始排，所以「IP/EDA 只有 5 家」那一欄下面是一大片空白，
       而旁邊「封測有 20 家」那一欄一路排到底 —— 視覺上整張圖像是重心壓在右下角。
       各自置中之後，同一條水平線上的才真的是「同一階的東西」，走線也短一截。*/
    /* ★ 2026-09-25 環節收合（Andy：「族群需要可以收起來，收起來的時候只能留下個股標籤」）。
       每檔一張兩行高的大卡，半導體鏈一欄就排到 900px 以上。收合的環節改成一排排緊湊的
       個股小晶片（名稱＋代號、漲跌色邊、外商灰字），高度只剩原本的三分之一左右。
       預設全部收合（Andy 要短），逐鏈記在 localStorage `tw.chainFold`。
       只在桌機（>820px）生效：手機另有一套清單版面，窄畫面一律照舊展開。*/
    const foldOn = (window.innerWidth || 1440) > 820;
    const foldSt = chainFoldGet(chainId);
    const isFolded = (sid) => foldOn && (foldSt.seg[sid] != null ? foldSt.seg[sid] : foldSt.def);
    const CHIP_H = 22, CHIP_GX = 5, CHIP_GY = 5;
    const chipW = (c) => {
      const code = c.tw_code || '外商';
      const cw = 16 + 4 + code.length * (c.tw_code ? 7 : 11.5);
      const nmW = (t) => { let w1 = 0; for (const ch of t) w1 += chW(ch) * 12 / 13; return w1; };
      /* 名稱最多 6 字；欄寬窄（136px 下限）時再往下切，文字絕不准超出晶片框 ——
         超出的話量到的內容寬度會比欄寬寬，置中就歪了（1100px 實測偏 1.1%）。*/
      let n = Math.min(6, c.name.length), nm = c.name;
      const cut = (k) => (k >= c.name.length ? c.name : c.name.slice(0, Math.max(1, k - 1)) + '…');
      nm = cut(n); while (n > 2 && cw + nmW(nm) > inW) { n--; nm = cut(n); }
      return { nm, code, w: Math.min(inW, Math.ceil(cw + nmW(nm))) };
    };
    const chipLay = (list) => {             // 依欄寬把晶片一排一排排下去，回傳各自相對位置與總高
      let x = 0, row = 0; const out = [];
      list.forEach(c => { const k = chipW(c); if (x && x + k.w > inW) { x = 0; row++; }
        out.push(Object.assign({ dx: x, dy: row * (CHIP_H + CHIP_GY) }, k)); x += k.w + CHIP_GX; });
      return { items: out, h: list.length ? (row + 1) * (CHIP_H + CHIP_GY) - CHIP_GY + 4 : 0 };
    };
    const segBodyH = (s, list) => (list.length && isFolded(s.id)
      ? 4 + chipLay(list).h + 18
      : list.length * (cardH + gapY) + (list.length ? 0 : noteLines(s, list) * NOTE_LH + 6) + 18);   // 沒台股只有說明的環節多 6px：說明最後一行的字腳才不會貼在外框底線上（2026-10-03）
    const colH = cols.map(col => col.reduce((t, s) => t + 24 + segBodyH(s, bySeg[s.id] || []), 0));
    const bodyH = Math.max.apply(null, colH.concat([0]));
    cols.forEach((col, ci) => { let y = padY + Math.round((bodyH - colH[ci]) / 2); col.forEach(s => { const list = bySeg[s.id] || []; pos[s.id] = { x: padX + ci * (colW + colGap), y, list }; y += 24 + segBodyH(s, list); }); maxH = Math.max(maxH, y); });
    /* 寬度＝內容寬＋左右各 padX。**左右對稱**，內容就一定水平置中。
       舊版是 `... + 24`（只加在右邊，給同一欄回頭線那條 24px 通道用），
       那 24px 正是「看起來偏左」的另一半原因 —— 現在改成把它含進 padX 的下限（26px）。*/
    const W = fit.W;
    const coPos = {};
    /* 孤立節點要標「?」，所以連線度數得在畫卡片之前就算好。
       只算兩端都在這條鏈上的邊 —— 另一端不在圖上的邊本來就畫不出來，
       算進去會讓一個明明沒有線的節點不被標記。競爭關係（competes）不是上下游，不算。*/
    /* ★ 2026-10-03：度數照整條鏈算（同 drawSegList 那段）—— 範圍縮小時，客戶不在這張圖上的公司不能被標成「?」。*/
    const inChain = new Set(sc.companies.filter(c => chainSegments(sc, chainId).some(s2 => s2.id === c.segment)).map(c => c.id)), deg = {};
    sc.edges.forEach(e => { if (e.rel === 'competes' || !inChain.has(e.from) || !inChain.has(e.to)) return;
      deg[e.from] = (deg[e.from] || 0) + 1; deg[e.to] = (deg[e.to] || 0) + 1; });
    /* ★ 2026-09-26（批次6-圖十 1500px 紅燈）：環節標題改成「量過放得下才整段印」。
       ▸／▾ 收合鈕佔色塊最右邊 24px，而標題從 +19 一路印到底 —— 欄數多的鏈（ai_server 1500px 時
       fitCols 把欄寬收到 154）「IC 載板（ABF / BT）」這種長標題就直接壓在 ▾ 上。
       可用寬度＝欄寬 − 19（圓點）− 右側留白（有收合鈕 26、沒有 4）；放不下就切字加「…」。
       完整名稱不另外塞 <title>：滑過標題本來就會出 wireSegTip 的說明框，第一行就是全名，
       再加原生 tooltip 會兩個框疊在一起。字寬用 12px（.seg-title 的字級）＋ .06em 字距真的量。*/
    const ctx12 = (() => { try { const c = document.createElement('canvas').getContext('2d');
      c.font = `12px ${(cs0 && cs0.fontFamily) || 'sans-serif'}`; return c; } catch (e) { return null; } })();
    /* 公司卡第二行（.co .sub）的等寬字：index.html 寫 11px、theme4.css（v4 骨架）在桌機拉到 12px，取大的那個量 —— 寧可多切一個字也不要印出卡片。*/
    const ctx11 = (() => { try { const c = document.createElement('canvas').getContext('2d');
      c.font = `12px ${getComputedStyle(document.documentElement).getPropertyValue('--mono') || 'monospace'}`; return c; } catch (e) { return null; } })();
    const titleW = (t) => { let w1 = 0; for (const ch of t) w1 += (ctx12 ? ctx12.measureText(ch).width : (/[\u0000-ÿ]/.test(ch) ? 7 : 12)) + 0.72; return w1; };
    const fitTitle = (t, maxW) => { t = String(t || ''); if (titleW(t) <= maxW) return t;
      let a = [...t]; while (a.length > 1 && titleW(a.join('') + '…') > maxW) a.pop(); return a.join('').trimEnd() + '…'; };
    let nodes = '';
    const segBoxes = [];                      // 每個環節外框的範圍：走線的匯流道要從框底下過，不能切過框
    segs.forEach(s => { const p = pos[s.id]; if (!p) return; const col = segColor(s.id);
      const tMax = colW - 25 - (foldOn && p.list.length ? 29 : 7);
      /* 外框：頂端比標題色塊高 4px、底端在最後一列內容下方 6px（segBodyH 的 18px 段距裡，框吃掉 2px、框與框之間留 16px）。
         畫在最前面，標題、晶片、卡片都疊在它上面。*/
      const fy = p.y - 24, fh = segBodyH(s, p.list) + 8;
      segBoxes.push({ x: p.x, y: fy, w: colW, h: fh });
      nodes += `<rect class="segbox" data-seg="${s.id}" x="${p.x + 0.5}" y="${fy + 0.5}" width="${colW - 1}" height="${fh - 1}" rx="8" style="--c:${col}"/>`;
      nodes += `<g class="segtitle" data-seg="${s.id}" style="--c:${col}"><rect x="${p.x + 3}" y="${p.y - 21}" width="${colW - 6}" height="19" rx="5" fill="${col}" fill-opacity=".14"/><circle cx="${p.x + 13}" cy="${p.y - 11.5}" r="3.5" fill="${col}"/><text class="seg-title" x="${p.x + 22}" y="${p.y - 7}" fill="${col}">${A.fmt.esc(fitTitle(s.name, tMax))}</text></g>`;
      /* 沒有台股的環節：有 note 就講 note，不要一律寫「台股無直接對應」。
         2026-09-19 踩到：三家設備商搬去 pkg_equipment 之後，「先進封裝 CoWoS/SoIC」變成空的，
         但 CoWoS 明明是台積電自己做的 —— 寫「台股無直接對應」是錯的。*/
      if (!p.list.length) {
        const msg = s.note || '（台股無直接對應）';
        const words = noteWrap(msg);
        const shown = words.slice(0, NOTE_MAX);
        if (words.length > NOTE_MAX) shown[NOTE_MAX - 1] = shown[NOTE_MAX - 1].slice(0, -1) + '…';
        /* ★ 2026-09-23：這裡的 fill 本來寫死 #6f7ea3（深色主題的舊 --ink-3），
           切到明亮主題不會換色，而且吃不到這次把 --ink-3 提亮的修正。
           SVG 的 fill 讀得到 CSS 變數，所以直接指到 token 就好。*/
        // 說明全文改由 wireSegTip 的說明框顯示（原生 <title> 寬度管不到，會窄到逐字斷行）
        nodes += `<g class="segnote" data-seg="${s.id}">` + shown.map((w, i) =>
          `<text class="sub" x="${p.x + SEG_IN + 4}" y="${p.y + 15 + i * NOTE_LH}" fill="var(--ink-3)">${A.fmt.esc(w)}</text>`).join('') + '</g>';
      }
      if (foldOn && p.list.length) {
        const fd = isFolded(s.id);
        nodes += `<g class="segfold" data-seg="${s.id}" data-folded="${fd ? 1 : 0}"><rect x="${p.x + colW - 27}" y="${p.y - 21}" width="24" height="19" rx="5" fill="transparent"/><text x="${p.x + colW - 15}" y="${p.y - 7}" fill="${col}">${fd ? '▸' : '▾'}</text><title>${fd ? '展開這個環節（每檔一張卡）' : '收合這個環節（只留個股標籤）'}</title></g>`;
      }
      if (p.list.length && isFolded(s.id)) {
        /* 收合：走線的端點接到「整個環節的晶片區塊」左右緣，不是個別晶片 ——
           晶片擠成一排排，線接到中間那顆會從隔壁晶片上穿過去。*/
        const lay = chipLay(p.list), bh = lay.h;
        p.list.forEach((c, i) => { const it = lay.items[i]; const x = p.x + SEG_IN + it.dx, y = p.y + 4 + it.dy;
          coPos[c.id] = { x: p.x, y: p.y + 2, w: colW, h: Math.max(bh, CHIP_H) };
          const m = c.tw_code ? priceOf[c.tw_code] : null; const chg = m ? m.chg_pct : null;
          const tip = `${c.name}${c.tw_code ? ' ' + c.tw_code : '（外商）'}${m ? ` · ${A.fmt.n(m.close)} ${A.fmt.pct(chg)}` : ''}`;
          nodes += `<g class="co chip ${c.foreign || !c.tw_code ? 'foreign' : ''} ${state.code && c.tw_code === state.code ? 'sel' : ''}" data-id="${c.id}" data-segment="${c.segment}" data-code="${c.tw_code || ''}" style="--c:${col};--ud:${chg == null ? 'var(--line-2)' : A.upDown(chg)}"><rect x="${x}" y="${y}" width="${it.w}" height="${CHIP_H}" rx="11"/><text x="${x + 8}" y="${y + 15}">${A.fmt.esc(it.nm)} <tspan class="sub">${it.code}</tspan></text><title>${A.fmt.esc(tip)}</title></g>`; });
        return;
      }
      /* 展開的公司卡畫在框裡（左右各內縮 SEG_IN），但 coPos 仍記框的左右緣：線停在框邊，不穿進框裡碰到卡片。*/
      const cx0 = p.x + SEG_IN;
      /* 卡片內縮之後少了 12px，「應用材料 Applied…」「Intel x86 CPU · Intel Foundry」這種第二行（技術）會直接印出卡片右緣。
         兩行都改成量過再切：第一行＝名稱（12.5px）＋代號（11px 等寬），第二行＝技術（11px 等寬）；右邊留 ? 標記的位置。*/
      const textMax = inW - 12 - 8;
      const lineFit = (txt, maxW, fw) => { const t = [...String(txt || '')]; const w = (a) => a.reduce((t1, ch) => t1 + fw(ch), 0);
        if (w(t) <= maxW) return t.join(''); while (t.length > 1 && w(t) + fw('…') > maxW) t.pop(); return t.join('').trimEnd() + '…'; };
      const fwName = (ch) => chW(ch) * 12.5 / 13, fwMono = (ch) => (ctx11 ? ctx11.measureText(ch).width : (/[\u0000-ÿ]/.test(ch) ? 6.7 : 11));
      p.list.forEach((c, i) => { const y = p.y + 4 + i * (cardH + gapY); coPos[c.id] = { x: p.x, y, w: colW, h: cardH }; const m = c.tw_code ? priceOf[c.tw_code] : null; const chg = m ? m.chg_pct : null;
        nodes += `<g class="co ${c.foreign || !c.tw_code ? 'foreign' : ''} ${state.code && c.tw_code === state.code ? 'sel' : ''}" data-id="${c.id}" data-segment="${c.segment}" data-code="${c.tw_code || ''}" style="--c:${col}"><rect x="${cx0}" y="${y}" width="${inW}" height="${cardH}" rx="7"/><rect x="${cx0}" y="${y}" width="4" height="${cardH}" rx="2" fill="${col}"/><text x="${cx0 + 12}" y="${y + 15}">${A.fmt.esc(lineFit(c.name.length > 12 ? c.name.slice(0, 11) + '…' : c.name, textMax - (deg[c.id] ? 0 : 16) - fwName(' ') - [...(c.tw_code || '外商')].reduce((t1, ch) => t1 + fwMono(ch), 0), fwName))}${c.tw_code ? ` <tspan class="sub">${c.tw_code}</tspan>` : ' <tspan class="sub">外商</tspan>'}</text><text class="sub" x="${cx0 + 12}" y="${y + 29}">${m ? `${A.fmt.n(m.close)} <tspan fill="${A.upDown(chg)}">${A.fmt.pct(chg)}</tspan>` : A.fmt.esc(lineFit((c.tech || []).slice(0, 2).join(' · '), textMax, fwMono))}</text>${deg[c.id] ? '' : `<g class="iso"><circle cx="${cx0 + inW - 12}" cy="${y + 12}" r="6.5"/><text x="${cx0 + inW - 12}" y="${y + 15.5}">?</text><title>尚無上下游資料</title></g>`}</g>`; }); });
    /* 圖十（Andy 2026-09-19：「供應鏈關聯圖 連線對不起來」）。
       以前每一條邊都寫死「來源右緣 → 目標左緣」，於是目標在左邊的邊整條倒著走、
       從卡片底下穿過去，看起來就像連錯人；邊又排在 nodes 之前，被卡片蓋掉一半。
       現在端點依相對位置決定，而且一律走「欄與欄之間那條 30px 的空白通道」——
       通道裡沒有任何卡片，所以線不會穿過不相干的公司：
         目標在右、只隔一欄 → 右緣出 → 貝茲曲線走通道 → 目標左緣
         目標在右、隔好幾欄 → 右緣出 → 下到卡片下方的匯流道 → 橫過去 → 上到目標左緣
         目標在左           → 左緣出 →「先下再橫」正交折線 → 上到目標右緣
         同一欄             → 右緣出 → 繞 24px 通道 → 回到目標右緣
       線型由 rel 決定：supplies／produced_by 實線帶箭頭、outsources_to 虛線、
       competes 不是上下游所以不畫；設備／材料環節（segment 的 role）走灰色細線。
       粗細（依存度）用 CSS 變數 --w 傳 —— index.html 的 .chainmap .edge{stroke-width:1.2}
       會蓋掉 stroke-width 屬性，改成 inline style 又會反過來蓋掉 .hi 的加粗。*/
    const gapMid = 14;                       // 通道中線（colGap=30）
    const coSeg = {}; cos.forEach(c => (coSeg[c.id] = c.segment));
    const segRole = {}; segs.forEach(s2 => (segRole[s2.id] = s2.role || ''));
    const corner = (pts) => {                // 正交折線，轉角切 6px 圓角
      let d = `M${pts[0][0]},${pts[0][1]}`;
      for (let i = 1; i < pts.length - 1; i++) {
        const [px, py] = pts[i - 1], [x, y] = pts[i], [nx, ny] = pts[i + 1];
        const r = Math.min(6, Math.hypot(x - px, y - py) / 2, Math.hypot(nx - x, ny - y) / 2);
        d += `L${x - Math.sign(x - px) * r},${y - Math.sign(y - py) * r}`;
        d += `Q${x},${y} ${x + Math.sign(nx - x) * r},${y + Math.sign(ny - y) * r}`;
      }
      const e2 = pts[pts.length - 1];
      return d + `L${e2[0]},${e2[1]}`;
    };
    /* 匯流道要壓多低，只由「這條橫線真的會經過誰」決定，不是整張圖的最底下。
       半導體鏈最高的那一欄有 900px，一條「先進封裝 → 晶圓代工」的回頭線
       其實整段都走在兩欄之間那條 30px 的空白通道裡，一張卡片都沒碰到 ——
       以前拉到最底再繞回來，多走 1200px，中間一大片空白，看起來像線斷了。*/
    const allCards = Object.values(coPos), laneUse = {};
    let edges = '', laneMax = 0;
    const nextLane = (xa, xb, ay, by) => {
      const xl = Math.min(xa, xb), xr = Math.max(xa, xb);
      let base = Math.max(ay, by) + 12;
      allCards.forEach(c => { if (c.x < xr - 1 && c.x + c.w > xl + 1) base = Math.max(base, c.y + c.h + 10); });
      /* ★ 2026-10-03：環節加了外框之後，橫越的匯流道也要從**框底下**過（框底比最後一列內容低 6px），
         只看卡片的話線會從框的下緣那一條切過去，看起來像穿進框裡。*/
      segBoxes.forEach(f => { if (f.x < xr - 1 && f.x + f.w > xl + 1) base = Math.max(base, f.y + f.h + 6); });
      const k = Math.round(base);
      const y = base + 4 + (((laneUse[k] = (laneUse[k] || 0) + 1) - 1) % 6) * 7;
      laneMax = Math.max(laneMax, y); return y;
    };
    sc.edges.forEach(e => {
      if (e.rel === 'competes') return;
      const a = coPos[e.from], b = coPos[e.to]; if (!a || !b) return;
      const ay = a.y + a.h / 2, by = b.y + b.h / 2;
      let d;
      if (b.x > a.x) {
        const x1 = a.x + a.w, x2 = b.x;
        if (x2 - x1 <= colGap + 1) { const mx = (x1 + x2) / 2; d = `M${x1},${ay} C${mx},${ay} ${mx},${by} ${x2},${by}`; }
        else { const ly = nextLane(x1 + gapMid, x2 - gapMid, ay, by); d = corner([[x1, ay], [x1 + gapMid, ay], [x1 + gapMid, ly], [x2 - gapMid, ly], [x2 - gapMid, by], [x2, by]]); }
      } else if (b.x < a.x) {
        const x1 = a.x, x2 = b.x + b.w, ly = nextLane(x1 - gapMid, x2 + gapMid, ay, by);
        d = corner([[x1, ay], [x1 - gapMid, ay], [x1 - gapMid, ly], [x2 + gapMid, ly], [x2 + gapMid, by], [x2, by]]);
      } else {
        /* ★ 2026-09-26（批次6-圖十 800／1500px 紅燈，main 既有）：同一欄的回頭線以前寫死往右繞 24px。
           那是欄距固定 30px 時代的數字；fitCols（C5）之後欄多或畫面窄時欄距會收到下限 18px，
           24px 的繞線就伸進**隔壁欄的卡片裡 6px**，整段豎線從那一欄的公司身上穿過去 ——
           ai_server 的「金居→NVIDIA 穿過味之素」、半導體的「帆宣→AMAT 穿過群聯」全是這一條。
           改成依實際欄距算：離隔壁欄至少留 8px、離圖的右邊界（最右欄時是 padX）至少留 4px，
           上限仍是 24（寬的時候長相跟以前一樣），下限 6（線才看得出是往外繞一圈）。*/
        const x1 = a.x + a.w, xo = x1 + Math.max(6, Math.min(24, colGap - 8, padX - 4));
        d = corner([[x1, ay], [xo, ay], [xo, by], [x1, by]]);
      }
      /* 兩種灰線分開：
         equipment（設備）→ 灰色**細**線，粗細鎖 1，不跟主鏈搶視覺
         material（材料）→ 灰色，但**粗細仍依 strength** —— CCL 占高階 AI 伺服器 PCB
           材料成本 50% 以上，是這輪行情的「因」不是「果」，弱化成細線會誤導 */
      const role = [coSeg[e.from], coSeg[e.to]].map(sg => segRole[sg] || '');
      const eq = role.includes('equipment'), mat = !eq && role.includes('material');
      const w = eq ? 1 : 0.8 + (e.strength || 1) * 0.5;
      const cls = `edge${e.rel === 'outsources_to' ? ' dash' : ''}${e.rel === 'designated_by' ? ' spec' : ''}${eq ? ' eq' : ''}${mat ? ' mat' : ''}`;
      edges += `<path class="${cls}" data-from="${e.from}" data-to="${e.to}" data-rel="${A.fmt.esc(e.rel || '')}" style="--w:${w.toFixed(2)}" marker-end="url(#scArrow)" d="${d}"><title>${A.fmt.esc(relLabel(e))}</title></path>`;
    });
    const H = Math.max(maxH, laneMax + 18, 300);
    /* 箭頭：markerUnits 用 userSpaceOnUse，不然細線的箭頭會跟著縮到看不見；
       fill 用 context-stroke，線變色（hover 成青色、設備灰）箭頭才跟著變。*/
    const defs = '<defs><marker id="scArrow" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M0.5,0.8 L7.5,4 L0.5,7.2 z" fill="context-stroke"/></marker></defs>';
    /* ⚠ `max-width` 拿掉了。它是舊版靠左的直接原因：W×1.25 常常小於容器寬度，
       SVG 是 block 元素，撐不滿就靠左。現在寬度已經等於容器寬度，width:100% 剛好 1:1。
       `min-width` 留著 —— 容器真的太窄（390px）時寧可讓這個框自己左右滑，
       也不要把 12.5px 的字縮到 5px。手機的 Default 畫面本來就是下面那份環節卡清單。*/
    const empty = nEdge0 ? '' : '<div class="mapempty">此鏈沒有可畫的上下游關係</div>';
    /* ★ 2026-09-26 晚（Andy：「收合 展開合併」）：「全部收合」「全部展開」兩顆鈕合併成**一顆切換鈕**。
       兩顆並排時永遠有一顆是「按了沒反應」的（已經全收了還能按全收），使用者要先讀懂現在是哪個狀態才知道該按哪顆。
       現在鈕上只寫「按下去會發生的那件事」：全部展開中 → 「全部收合」；只要有任何一個環節收著 → 「全部展開」。
       data-fold 跟著寫「按下去要變成什麼」（all＝全收、none＝全展），tw.chainFold 的存法一個字都沒改。*/
    const anyFolded = segs.some(s => (pos[s.id] && pos[s.id].list.length) && isFolded(s.id));
    const foldBar = foldOn && cos.length ? `<div class="foldbar"><button type="button" class="foldtg" data-fold="${anyFolded ? 'none' : 'all'}" title="${anyFolded ? '每檔一張卡' : '只留個股標籤'}">${anyFolded ? '全部展開' : '全部收合'}</button></div>` : '';
    host.innerHTML = `${empty}${foldBar}<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;min-width:${Math.min(W, 860)}px;display:block">${defs}${nodes}<g class="elayer">${edges}</g></svg>`;
    markFit(host, fit);
    paintRelFocus(host, focus, cos);
    /* ★ 2026-09-23 C5 優化：hover 一張卡，**線與另一端的公司卡一起提亮**。
       舊版只提亮線 —— 線一多（半導體鏈 140 條）就看不出那條線通到誰，
       使用者還要自己用眼睛沿著線找過去，那正是「看不懂」的典型形態。
       另一端一起亮之後，「誰供貨給它、它賣給誰」一眼就讀得出來。*/
    $$('.co', host).forEach(n => { n.onmouseenter = () => { const rel = new Set([n.dataset.id]);
      $$('.edge', host).forEach(e => { const on = e.dataset.from === n.dataset.id || e.dataset.to === n.dataset.id;
        if (on) { rel.add(e.dataset.from); rel.add(e.dataset.to); }
        e.classList.toggle('hi', on); e.classList.toggle('dim', !on); });
      $$('.co', host).forEach(m => m.classList.toggle('near', rel.has(m.dataset.id)));
    }; n.onmouseleave = () => { $$('.edge', host).forEach(e => e.classList.remove('hi', 'dim')); $$('.co', host).forEach(m => m.classList.remove('near')); }; n.onclick = () => { const co = cos.find(c => c.id === n.dataset.id); if (!co) return;
      /* 2026-09-18（Andy 圖12）：以前無論點誰都先開一張 position:fixed 掛在 <body> 的卡，
         同時又跳去個股頁 —— 那張卡不屬於任何 view，換頁不會被清掉，
         於是「點 6116 之後，個股頁右下角一直浮著台積電 2330」。
         現在分兩條路：有台股代號的直接進個股頁（卡片本來就是為了進去看的），
         外商／無代號的才在產業鏈圖下方原地展開小面板。*/
      closeCoBox();
      /* N7（Andy 2026-09-19：「點擊供應鏈關聯圖 個股時不要馬上跳到股票介面，
         可以跳出觀看股票這選項」）。
         2026-09-18 為了修圖12（浮動卡跟到個股頁）改成「有代號就直接跳」，
         但那樣一點就走，想看它在鏈上的位置、同環節有誰都來不及。
         現在一律先開原地小面板（同環節、市占、技術、成長），
         面板裡有一顆「看個股頁 →」要跳再跳。*/
      showCompany(co, sc, host);
      /* Andy 2026-09-20：「當我點擊『日月光頭控』時 他所對應的族群會被選取」。
         以前點公司只開右側面板，下面的環節色標、族群卡片、成分股表完全沒反應 ——
         使用者看到「日月光投控在封測」，卻得自己再回頭去點一次「封測」才篩得到。
         現在把它接到**既有那一套**上（onCompany → 跟點環節色標同一條路），
         不另外寫一套高亮邏輯。選的是**環節**（co.segment）不是族群，理由見 renderChain 的註解。*/
      if (handlers && handlers.onCompany) handlers.onCompany(co); }; });
    const redraw = () => { drawChainMap(host, sc, chainId, im, handlers); if (handlers && handlers.onFold) handlers.onFold(); };
    $$('.segfold', host).forEach(n => n.onclick = (ev) => { ev.stopPropagation();
      const st2 = chainFoldGet(chainId); st2.seg[n.dataset.seg] = n.dataset.folded !== '1'; chainFoldSet(chainId, st2); redraw(); });
    // 切換鈕：data-fold 就是「按下去要變成的狀態」（畫的時候依目前狀態寫好），清掉逐環節的例外
    $$('.foldbar button', host).forEach(b => b.onclick = () => { chainFoldSet(chainId, { def: b.dataset.fold === 'all', seg: {} }); redraw(); });
    $$('.segtitle', host).forEach(n => n.onclick = () => handlers.onSegment && handlers.onSegment(n.dataset.seg));
    /* 把目前這檔的卡片捲進視野 —— 但**只捲關聯圖自己那個框**，不准動到整頁。
       原本用 scrollIntoView，它會一路往上找每一個可捲的祖先，連 document 也算。
       在個股頁把產業鏈搬到最下面之後（Andy 2026-09-20），那一下等於把整頁拉到底，
       使用者一進個股頁就看不到 K 線 —— 剛好把這次要修的東西反過來弄壞。*/
    if (focus && !state.code) centerRelFocus(host);
    if (state.code) {
      const sel = $(`.co[data-code="${state.code}"]`, host);
      if (sel && sel.getBBox) setTimeout(() => {
        try {
          const svg = host.querySelector('svg'); if (!svg) return;
          const vb = (svg.getAttribute('viewBox') || '').split(/\s+/).map(Number);
          const scale = vb.length === 4 && vb[2] ? (svg.clientWidth || host.clientWidth) / vb[2] : 1;
          const b = sel.getBBox();
          host.scrollTo({ left: Math.max(0, b.x * scale - host.clientWidth / 2 + b.width * scale / 2),
                          top: Math.max(0, b.y * scale - 60), behavior: 'smooth' });
        } catch (e) { /* 收合狀態下 getBBox 量不到，忽略 */ }
      }, 50);
    }
  }
  /* ★ 2026-10-03 晚（DECISIONS #317）：關聯圖畫整條鏈，上方剖析圖畫到的環節（focus）反亮。
     反亮＝亮框（環節色 2px）＋亮底（環節色 16%），標題色塊加深；其餘環節的框、標題、說明、公司卡掛 .relout（CSS 透明度 0.6，
     降 40%：仍讀得到字、仍點得到）。連線：兩端都不在反亮範圍的才淡掉，碰到反亮那幾格的維持原樣 —— 「它賣給誰／誰供貨給它」要看得清楚。
     跟選取（.sel／.dim）是兩套 class：使用者點一格選起來時，選取照舊疊在上面。*/
  function paintRelFocus(host, focus, cos) {
    const f = focus && focus.size ? focus : null;
    const svg = host.querySelector('svg'); if (svg) svg.classList.toggle('hasfocus', !!f);
    const tog = (n, seg) => { const on = !!f && f.has(seg); n.classList.toggle('relfocus', on); n.classList.toggle('relout', !!f && !on); };
    $$('.segbox, .segtitle, .segnote, .segfold', host).forEach(n => tog(n, n.dataset.seg));
    $$('.co', host).forEach(n => tog(n, n.dataset.segment));
    const segOf = {}; (cos || []).forEach(c => { segOf[c.id] = c.segment; });
    $$('.edge', host).forEach(e => {
      const a = segOf[e.dataset.from], b = segOf[e.dataset.to];
      const touch = !!f && (f.has(a) || f.has(b));
      e.classList.toggle('relfocus', touch); e.classList.toggle('relout', !!f && !touch);
    });
  }
  /* 關聯圖框比容器寬（窄視窗時 SVG 有 min-width，要左右滑）時，框自己捲到反亮那幾欄的正中間。
     只捲關聯圖自己的框，**不動整頁** —— 打開剖析圖分頁要先看到上面的整張剖析圖（Andy 同一則回饋的第 1 點）。*/
  function centerRelFocus(host) {
    setTimeout(() => {
      try {
        if (!host.isConnected || host.hidden || host.scrollWidth <= host.clientWidth + 2) return;
        const hr = host.getBoundingClientRect();
        let l = Infinity, r = -Infinity;
        $$('.segbox.relfocus', host).forEach(b => { const q = b.getBoundingClientRect(); if (q.width) { l = Math.min(l, q.left); r = Math.max(r, q.right); } });
        if (!(r > l)) return;
        const mid = (l + r) / 2 - hr.left + host.scrollLeft;
        host.scrollTo({ left: Math.max(0, Math.round(mid - host.clientWidth / 2)), behavior: 'instant' });
      } catch (e) { /* 量不到（收合中）就算了 */ }
    }, 60);
  }
  /* 關掉外商小面板。換頁（route）與點下一家公司之前都會呼叫，
     這樣 #coBox 永遠不會活過它所屬的那一頁。*/
  /* supply_chain.yaml 的 growth 是一個 dict（capacity_plan / capacity_source / drivers），
     以前直接丟進 fmt.esc → 畫面上印出「成長：[object Object]」（Andy 圖12 順手抓到）。*/
  function growthText(g) {
    if (!g) return '';
    if (typeof g === 'string') return g;
    const parts = [];
    if (g.capacity_plan) parts.push(g.capacity_plan);
    if (Array.isArray(g.drivers) && g.drivers.length) parts.push('動能：' + g.drivers.join('、'));
    return parts.join(' · ');
  }
  /* 關聯圖環節收合狀態：{ 鏈 id: { def: 預設收合?, seg: { 環節 id: 收合? } } }。
     讀不到（無痕、被擋）就當成預設全部收合，不影響畫圖。*/
  function chainFoldGet(cid) {
    try { const all = JSON.parse(localStorage.getItem('tw.chainFold') || '{}'); const v = all[cid];
      if (v && typeof v === 'object') return { def: v.def !== false, seg: v.seg || {} }; } catch (e) { /* 忽略 */ }
    return { def: true, seg: {} };
  }
  function chainFoldSet(cid, v) {
    try { const all = JSON.parse(localStorage.getItem('tw.chainFold') || '{}'); all[cid] = v;
      localStorage.setItem('tw.chainFold', JSON.stringify(all)); } catch (e) { /* 忽略 */ }
  }
  function closeCoBox() { const b = document.getElementById('coBox'); if (b) b.remove(); }
  /* 外商／無台股代號的公司：在產業鏈圖正下方原地展開，不再用浮動卡。
     host＝畫產業鏈圖的容器，面板就插在它後面，捲動時跟著圖一起走。*/
  function showCompany(co, sc, host) {
    if (!co) return;
    closeCoBox();
    const box = document.createElement('div');
    box.id = 'coBox'; box.className = 'card'; box.dataset.co = co.id;
    box.style.cssText = 'margin-top:12px';
    /* Andy 2026-09-19：「在**旁邊**新增這類說明」。
       .chainrow 是 flex：寬螢幕時面板排在圖的右邊（340px），
       窄畫面（<1100px）自動 wrap 掉到圖的下面 —— 800px 硬要並排會把圖擠到看不清。*/
    const anchor = host || $('#chainMap');
    const row = anchor && anchor.closest ? anchor.closest('.chainrow') : null;
    /* ★ 2026-09-24 桌機：圖的右邊是「選中環節的族群／個股」那一欄，資訊欄就住進同一欄、疊在它上面
       （.relstick 是上下兩格：資訊欄在上、族群清單在下，各自捲；CSS 看到 #coBox 就把那一欄打開）。
       不另開第三欄：圖｜清單｜資訊欄三欄並排會把圖擠到要左右滑。
       ⚠ 不能先量那一欄看不看得到：點公司時那一格是在這支之後才被選起來的，這一刻那一欄可能還收著。*/
    const stick = relListMode() && row ? row.querySelector('.relstick') : null;
    if (stick) { box.classList.add('relside'); stick.insertBefore(box, stick.firstChild); }
    else if (row) { box.classList.add('relside'); row.appendChild(box); }
    else if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(box, anchor.nextSibling);
    else document.body.appendChild(box);
    /* 市占數字要三件事同時看得到：值、什麼時候的、以及**這是實績還是預估**。
       2026-09-19 修：以前 F 結尾的預估值在後端被當成「永遠不會過期」，
       畫面上又跟實績長得一模一樣 —— 一筆 2026 年初的法人預估，到 2028 年還是綠的。*/
    const shares = (co.share || []).map(s => `<li>${A.fmt.esc(s.metric || s.product || '市占')}：<b class="mono">${s.value_pct != null ? s.value_pct + '%' : (s.value_pct_range ? s.value_pct_range.join('–') + '%' : (s.value || '—'))}</b>${s.forecast ? ' <em class="cf cf-estimated">預估</em>' : ''} <small class="muted">${A.fmt.esc(String(s.as_of || '').replace(/F$/, ''))} · ${A.fmt.esc(s.source || '')}${s.stale ? ' · 已過期' : ''}</small></li>`).join('');
    const peers = sc.companies.filter(c => c.segment === co.segment && c.id !== co.id);
    box.innerHTML = `<div class="row spread"><h3>${A.fmt.esc(co.name)} ${co.tw_code ? `<span class="mono cyan">${co.tw_code}</span>` : '<span class="pill">外商</span>'}</h3><button class="close" onclick="document.getElementById('coBox').remove()">×</button></div>
      <div class="sub"><span style="color:${segColor(co.segment)}">● ${A.fmt.esc(segName(sc, co.segment))}</span>${(co.groups || []).length ? ' · ' + co.groups.map(gn => A.L.groupByName(gn)).join(' ') : ''}</div>
      ${(co.tech || []).length ? `<div class="row" style="gap:6px;margin:6px 0">${co.tech.map(t => `<span class="pill">${A.fmt.esc(t)}</span>`).join('')}</div>` : ''}
      ${shares ? `<ul style="margin:6px 0;padding-left:18px;font-size:13.5px">${shares}</ul>` : ''}
      ${co.note ? `<div class="note">${A.fmt.esc(co.note)}</div>` : ''}
      ${growthText(co.growth) ? `<div class="note">成長：${A.fmt.esc(growthText(co.growth))}${co.growth && co.growth.capacity_source ? A.srcInfo(co.growth.capacity_source) : ''}</div>` : ''}${(co.risks || []).length ? `<div class="note">風險：${co.risks.map(A.fmt.esc).join('；')}</div>` : ''}
      ${relBlock(co, sc)}
      ${peers.length ? `<div class="row" style="gap:4px 8px;margin-top:8px;font-size:12.5px"><span class="muted">同環節</span>${peers.map(p => p.tw_code ? A.L.stock(p.tw_code, p.name, { cls: 'sm' }) : `<span class="muted">${A.fmt.esc(p.name)}</span>`).join('')}</div>` : ''}
      ${co.tw_code ? `<button class="btn primary" style="margin-top:8px" onclick="goStock('${co.tw_code}')">看個股頁 →</button>` : ''}`;
    wireRelBlock(box, sc, host);
    /* ★ 2026-09-26：點背景／Esc 收掉這張卡（全站 dismissable）。
       產業鏈頁（#relSec 裡）由 renderChain 那一筆負責 —— 它收卡的同時還要取消環節選取，兩筆一起登記會各關各的。
       其他地方（個股頁的產業鏈小圖）只有這張卡本身要收；點另一家公司＝換卡（舊卡會先被 closeCoBox 拿掉），不算點外面。*/
    if (A.dismissable && !(box.closest && box.closest('#relSec'))) {
      A.dismissable(box, closeCoBox, { ignore: ['.chainmap .co'] });
    }
  }

  /* ---------------------------------------------------------------- 產業關係說明
     Andy 2026-09-19：「點擊關聯圖時，在旁邊新增這類說明，更加明白產業關係」。
     圖上只有一條線與一個 tooltip，看得到「有關係」但看不懂「是什麼關係」。
     這一塊把那條線攤開來講：**上游是誰供什麼給它、它又把什麼賣給誰**，
     每一條都帶品項、依存度、以及「這是官方揭露還是產業推論」。
     最後一項很重要 —— 這份資料有一半是推論，不標的話使用者會當成事實。*/
  function relBlock(co, sc) {
    if (!co || !sc || !Array.isArray(sc.edges)) return '';
    const byId = {}; (sc.companies || []).forEach(c => (byId[c.id] = c));
    const line = (e, dir) => {
      const other = byId[dir === 'up' ? e.from : e.to];
      if (!other) return '';
      const rt = REL_TEXT[e.rel] || { up: '關聯', down: '關聯' };
      const nm = other.tw_code
        ? `<a class="lk" href="#stock/${other.tw_code}">${A.fmt.esc(other.name)} <span class="mono">${other.tw_code}</span></a>`
        : `<span class="muted">${A.fmt.esc(other.name)}${other.foreign ? '（外商）' : ''}</span>`;
      /* 依存度：Andy 2026-09-25「那條藍色小條看不懂」—— 小條保留，但旁邊一定要寫出 n/5，
         滑過再講清楚它量的是什麼、依據是什麼（strength 是人工依占比／獨供／長約給的分數）。*/
      const sv = Math.max(1, Math.min(5, Number(e.strength) || 0));
      const sw = e.strength ? `<span class="depw" title="依存度＝這段關係對它的重要程度，1 弱～5 強（依據：營收或採購占比、是否獨家或長約、替代難度，人工評分）"><i class="dep" style="--n:${sv}"></i><span class="depn">依存度 ${sv}/5</span></span>` : '';
      /* 可信度標籤。Andy 2026-09-25：「有媒體報導，需要貼文章，因為給讀者看；
         也不用特別說事實，只有我們推理的才要說」。
         → 官方揭露／媒體報導有 source_url 就把標籤本身做成連到原文的連結（開新分頁）；
           沒有來源的照樣顯示但不是連結（YAML 裡註記待補來源），絕不編網址。
         → 產業推論的說明放在標籤的滑過提示裡。*/
      const url = String(e.source_url || '').trim();
      const okUrl = /^https?:\/\//.test(url);
      const ctext = A.fmt.esc(CONF_TEXT[e.confidence] || e.confidence || '');
      let cf = '';
      if (e.confidence === 'estimated') {
        cf = `<em class="cf cf-estimated" title="${A.fmt.esc(EST_TIP)}">${ctext}</em>`;
      } else if (e.confidence && okUrl) {
        cf = `<a class="cf cf-${e.confidence} cf-lk" href="${A.fmt.esc(url)}" target="_blank" rel="noopener noreferrer" title="${e.source ? '出處：' + A.fmt.esc(e.source) : '原文'}">${ctext} ↗</a>`;
      } else if (e.confidence) {
        cf = `<em class="cf cf-${e.confidence}">${ctext}</em>`;
      }
      const guess = e.confidence === 'estimated';
      const why = guess
        ? `<div class="why"><b>推論依據</b>
             <div>${A.fmt.esc(e.note || '')}</div>
             ${srcLink(e.source_url)}</div>`
        : (e.note ? `<div class="nt">${A.fmt.esc(e.note)}</div>` : '');
      /* 排版：標籤原本黏在品項文字尾巴，品項一長就被擠到折行、邊框壓到下一行說明
         （弘塑、竑騰那幾條）。改成公司名那一行用 flex-wrap 排，標籤自成一塊不斷字。*/
      return `<li class="${guess ? 'guess' : ''}"><div class="rhd"><span class="rl">${A.fmt.esc(rt[dir])}</span>${nm}${sw}${cf}</div>
        <div class="it">${A.fmt.esc(e.item || '')}</div>${why}</li>`;
    };
    const up = sc.edges.filter(e => e.to === co.id && e.rel !== 'produced_by').map(e => line(e, 'up')).filter(Boolean);
    const down = sc.edges.filter(e => e.from === co.id && e.rel !== 'produced_by').map(e => line(e, 'down')).filter(Boolean);
    const rivals = (sc.competitors || []).filter(x => x.a === co.id || x.b === co.id)
      .map(x => byId[x.a === co.id ? x.b : x.a]).filter(Boolean);
    if (!up.length && !down.length && !rivals.length) {
      return '';
    }
    return `<div class="relbox">
      <div class="row spread"><b class="rh">產業關係</b>
        <button class="btn sm" id="relHi" data-on="0">在圖上highlight</button></div>
      ${up.length ? `<div class="relcol"><h5>上游 · 誰供給它（${up.length}）</h5><ul>${up.join('')}</ul></div>` : ''}
      ${down.length ? `<div class="relcol"><h5>下游 · 它供給誰（${down.length}）</h5><ul>${down.join('')}</ul></div>` : ''}
      ${rivals.length ? `<div class="relcol"><h5>同業競爭</h5><div class="row" style="gap:6px">${rivals.map(r => r.tw_code ? A.L.stock(r.tw_code, r.name, { cls: 'sm' }) : `<span class="muted">${A.fmt.esc(r.name)}</span>`).join('')}</div></div>` : ''}
      <div class="nt"><b class="cf cf-estimated" title="${A.fmt.esc(EST_TIP)}">產業推論</b>＝由公開資訊推得，非公司或媒體揭露</div>
    </div>`;
  }

  /* 「在圖上 highlight」：把這家公司的線亮起來、其餘變暗。
     按第二次還原 —— 不還原的話使用者會以為圖壞掉了。*/
  function wireRelBlock(box, sc, host) {
    const btn = box && box.querySelector('#relHi');
    if (!btn) return;
    /* 2026-09-23 C5 退版之後產業鏈頁與個股頁又是同一張圖（`#chainMap`，節點是公司），
       所以這裡只認它一個。*/
    const svgHost = $('#chainMap') || host;
    btn.onclick = () => {
      const on = btn.dataset.on === '1';
      btn.dataset.on = on ? '0' : '1';
      btn.classList.toggle('cyan', !on);
      btn.textContent = on ? '在圖上highlight' : '取消 highlight';
      // 釘住這組高亮：滑鼠經過公司卡不准把它洗掉（見 drawChainMap 的 hover）
      if (svgHost && svgHost.classList) svgHost.classList.toggle('cghold', !on);
      const id = box.dataset.co, gid = box.dataset.gid || '';
      $$('.edge', svgHost).forEach(e => {
        const d = e.dataset;
        const hit = !on && (d.from === id || d.to === id || (!!gid && (d.a === gid || d.b === gid)));
        e.classList.toggle('hi', hit);
        e.classList.toggle('dim', !on && !hit);
      });
      $$('.co', svgHost).forEach(n => n.classList.toggle('dim', !on && n.dataset.id !== id));
      $$('.cgnode', svgHost).forEach(n => n.classList.toggle('dim',
        !on && n.dataset.gid !== gid && n.dataset.code !== (box.dataset.code || '\u0000')));
    };
  }

  /* ============================================================ 簡版個股頁
     Andy：「不可以出現沒有資訊狀況」。
     完整個股頁（stock/<代號>.json）偶爾會缺 —— 新上市、歷史價量還不到 60 根日線，
     或像預覽版那樣只帶了一部分個股頁。以前這種情況給的是一句「還沒產生」＋一個返回鍵，
     那就是一個死路。現在改成：用手上「已經載入的」資料重新組一頁真的有東西的頁面 ——
     stocks.json 有今日價量、groups_detail 有法人與技術分、fundamental 有估值與營收、
     news 有相關新聞、族群有同業名單。看得到的資訊只會少，不會沒有。 */
  async function renderStockLite(code, im, sc, gd) {
    const [stocks, fund, news, th] = await Promise.all([
      A.load('stocks', { fallback: [] }), A.load('fundamental', { fallback: [] }),
      A.load('news', { fallback: [] }), A.load('themes', { fallback: null }),
    ]);
    const known = (stocks || []).find(x => x.code === code) || (A.L.all || []).find(x => x.code === code);
    if (!known) {
      $('#indChain').innerHTML = '';
      crumbs([{ label: '產業地圖', href: '#industry' }, { label: code }]);
      $('#stockPage').innerHTML = `<div class="card"><div class="empty">
        找不到代號 ${A.fmt.esc(code)}。個股頁只做上市櫃普通股，權證／期貨／指數不列入。<br><br>${A.L.back()}</div></div>`;
      return;
    }
    // 同族群成員表裡有法人、技術分、判定 —— 這些是完整頁才會算的，但族群頁已經算好了
    let mem = null, sibs = [];
    Object.entries(gd || {}).forEach(([gid, g]) => {
      (g.members || []).forEach(mm => {
        if (mm.code === code) { mem = { ...mm, group_id: gid, group_name: g.group_name }; }
      });
    });
    const gid = (mem && mem.group_id) || known.group_id;
    if (gid && gd && gd[gid]) {
      sibs = (gd[gid].members || []).filter(x => x.code !== code)
        .sort((a, b) => (b.turnover || 0) - (a.turnover || 0)).slice(0, 24);
    }
    const fu = (fund || []).find(x => x.code === code) || {};
    // 同一道把關（newsAbout）：後端標了 codes 也要標題／內文真的提到才算
    const ns = newsAbout((news || []).filter(n => String(n.codes || '').split(',').includes(code)), code, known.name).slice(0, 8);

    state.chain = chainOfGroup(im, gid) || 'industry'; state.group = null;
    const chainName = A.L.chains[state.chain] || CHAIN_NAME[state.chain] || state.chain;   // 中文名以 payload 為準，寫死的表只當 fallback
    crumbs([{ label: '產業地圖', href: '#industry' },
            { label: chainName, href: '#industry/' + state.chain },
            { label: `${known.name || ''} ${code}` }]);
    $('#indChain').innerHTML = '';      // 精簡版個股頁同樣不掛產業鏈位置卡（2026-09-26，見 renderStock）

    const n = A.fmt.n, pct = A.fmt.pct;
    // 有值才放進去 —— 寧可少一格，也不要放一格「—」在那裡佔位
    const kv = (pairs) => {
      const out = pairs.filter(p => p[1] !== null && p[1] !== undefined && p[1] !== '');
      return out.length ? `<div class="kvs">${out.map(p => `<div class="k"><div class="l">${p[0]}</div><div class="v${p[2] || ''}">${p[1]}</div></div>`).join('')}</div>` : '';
    };
    // 法人是「股」，全站一律換算成張再顯示
    const lot = (v) => (v === null || v === undefined ? null : `<span class="${A.fmt.cls(v)}">${A.fmt.lot(v / 1000)}</span>`);
    const close = known.close != null ? known.close : (mem && mem.close);
    const chg = known.chg_pct != null ? known.chg_pct : (mem && mem.chg_pct);
    const today = kv([
      ['收盤', close != null ? `<span class="num">${n(close)}</span>` : null],
      ['漲跌', chg != null ? `<span class="${A.fmt.cls(chg)}">${pct(chg, 2)}</span>` : null],
      ['成交值', known.turnover != null ? A.fmt.yi(known.turnover) : null],
      ['外資', mem ? lot(mem.foreign) : null],
      ['投信', mem ? lot(mem.trust) : null],
      ['自營', mem ? lot(mem.dealer) : null],
      ['技術分', mem && mem.tech_score != null ? n(mem.tech_score, 0) : null],
      ['目前判定', mem && mem.verdict ? A.fmt.esc(mem.verdict) : null],
    ]);
    const val = kv([
      ['本益比', fu.pe != null ? n(fu.pe, 1) : null],
      ['同族群中位', fu.group_median != null ? n(fu.group_median, 1) : null],
      ['股價淨值比', fu.pb != null ? n(fu.pb, 2) : null],
      ['ROE', fu.roe != null ? n(fu.roe, 1) + '%' : null],
      ['毛利率', fu.gross_margin != null ? n(fu.gross_margin, 1) + '%' : null],
      ['市值', fu.market_cap != null ? A.fmt.yi(fu.market_cap) : null],
      ['TTM EPS', fu.ttm_eps != null ? n(fu.ttm_eps, 2) : null],
      ['營收 YoY', fu.rev_yoy != null ? `<span class="${A.fmt.cls(fu.rev_yoy)}">${pct(fu.rev_yoy, 1)}</span>` : null],
      ['營收 MoM', fu.rev_mom != null ? `<span class="${A.fmt.cls(fu.rev_mom)}">${pct(fu.rev_mom, 1)}</span>` : null],
      ['營運動能', fu.momentum_score != null ? n(fu.momentum_score, 0) : null],
    ]);
    const themeLinks = A.L.themesOf(code);
    /* ★ 2026-09-25（Andy：「文字只需要留名稱」）：簡易頁的卡片副標（價量與三大法人、同族群才比本益比…）不再印；
       只留「N 則」這種讀數（副標以數字開頭才印）。*/
    const card = (title, sub, body) => body
      ? `<div class="card" style="margin-top:var(--gap-card)"><h3>${title}${sub && /^\d/.test(sub) ? ` <small data-readout>${sub}</small>` : ''}</h3>${body}</div>` : '';

    $('#stockPage').innerHTML = `
      <div class="card" style="margin-top:var(--gap-card)">
        <div class="row spread">
          <div><h2>${A.logo ? A.logo(code, known.name, 32, 'sklogo') : ''}${A.fmt.esc(known.name || '')} <span class="mono cyan">${code}</span>
            <small class="muted" style="font-size:13px">${A.fmt.mkt(known.market)}</small></h2>
            <div class="row" style="gap:6px 12px;margin-top:4px;font-size:13.5px">
              <span class="muted">產業鏈</span>${A.L.chain(state.chain, chainName)}
              <span class="muted">族群</span>${gid ? A.L.group(gid, (mem && mem.group_name) || known.group) : '—'}
              ${themeLinks ? `<span class="muted">題材</span>${themeLinks}` : ''}</div>
            <div class="row" style="margin-top:6px">
              <span class="num" style="font-size:30px;font-weight:700">${close != null ? n(close) : '—'}</span>
              ${chg != null ? `<span class="num ${A.fmt.cls(chg)}" style="font-size:18px">${pct(chg, 2)}</span>` : ''}
              <span class="pill amber">簡版個股頁</span></div></div>
        </div>
      </div>
      ${card('今日盤後', '價量與三大法人', today)}
      ${card('估值與營收', '同族群才比本益比', val)}
      ${card('相關新聞', `${ns.length} 則`, ns.length ? `<div class="cards">${ns.map(x => `<div class="scard">
          <a href="${A.fmt.esc(x.url || '#')}" target="_blank" rel="noopener">${A.fmt.esc(x.title || '')}</a>
          <div class="r"><span class="muted">${A.fmt.esc(x.date || '')}</span><span class="muted">${A.fmt.esc(x.source || '')}</span></div></div>`).join('')}</div>` : '')}
      ${card('同族群其他個股', '', sibs.length ? `<div class="sibs">${sibs.map(x =>
          `${A.L.stock(x.code, x.name)}<span class="chg ${A.fmt.cls(x.chg_pct)}">${pct(x.chg_pct, 1)}</span>`).join('')}</div>` : '')}
      <div class="muted" style="margin-top:var(--sp-2);font-size:12px">資料更新到 <b>${A.fmt.esc((A.D.meta && A.D.meta.data_date) || '—')}</b>　${A.L.back()}</div>`;
  }

  /* ★ 2026-10-02（Andy #stock/3189 截圖三，DECISIONS #293）個股 K 線卡工具列的五顆資訊標籤。
     改前住在現價那一行（現價｜漲跌｜即時｜技術分｜本益比｜同業分位｜營收 YoY｜分 K 完整），1440 寬右欄 AI 區一占，
     「分 K 完整」就自己掉到第二行，左欄多一整行；800 寬更是三行。
     改後住在工具列「指標 ▾」與「四週期同看」之間的空白：工具列**一律一行**，放不下的從最右邊一顆一顆收進「⋯ N」，
     點「⋯ N」原地展開一個小框列出收起來的那幾顆（點外面／Esc 收）。每顆：[鍵, 字, 額外 class, 滑過說明]。*/
  function stockTags(s, tier, code) {
    /* ★ 2026-10-05（Andy，#stock/00947）：ETF 沒有本益比、同業分位、營收 YoY —— 只留技術分與資料完整度 */
    if (isEtf(code)) return [['tech', `技術分 ${A.fmt.n(s.tech_score, 0)}`, '', ''], ['tier', tier[0], tier[1], tier[2]]];
    return [
      ['tech', `技術分 ${A.fmt.n(s.tech_score, 0)}`, '', ''],
      ['pe', `本益比 ${s.pe ? A.fmt.n(s.pe, 1) : '—'}`, '', ''],
      ['pct', `同業分位 ${s.pe_percentile != null ? A.fmt.n(s.pe_percentile, 0) + '%' : '—'}`, '', ''],
      ['yoy', `營收 YoY ${A.fmt.pct(s.rev_yoy)}`, '', ''],
      ['tier', tier[0], tier[1], tier[2]],
    ];
  }
  let tagRO = null;
  function tagPopClose() {
    const pop = document.getElementById('skTagPop'), more = document.getElementById('skTagMore');
    if (pop) pop.hidden = true;
    if (more) more.setAttribute('aria-expanded', 'false');
    window.removeEventListener('scroll', tagPopClose, true);
    window.removeEventListener('resize', tagPopClose);
  }
  function tagPopFill() {
    const pop = document.getElementById('skTagPop'), more = document.getElementById('skTagMore');
    if (!pop || !more) return;
    const hid = $$('#skTags>.pill[data-tag]').filter(t => t.hidden);
    pop.innerHTML = hid.map(t => `<span class="${A.fmt.esc(t.className)}"${t.title ? ` title="${A.fmt.esc(t.title)}"` : ''}>${A.fmt.esc(t.textContent)}</span>`).join('');
    // 框是 position:fixed（窄畫面工具列可以橫向滑，絕對定位會被裁掉）：左緣對齊「⋯ N」、在它正下方；太靠右就往左收，不超出視窗
    const r = more.getBoundingClientRect();
    pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pop.offsetWidth - 8)) + 'px';
    pop.style.top = Math.round(r.bottom + 6) + 'px';
  }
  /* 量一次：先全部放回去，還是超出就從最右邊一顆一顆收，收到放得下為止（最多 5 輪排版，很便宜）。
     工具列的寬由欄寬決定（拖分隔線、開關事件欄、縮放視窗都會變），週期鈕被勾掉／加上會改標籤可用的寬 → 兩者都觀察。*/
  function fitTags() {
    const box = document.getElementById('skTags'), more = document.getElementById('skTagMore');
    if (!box || !more) return;
    const tags = $$('#skTags>.pill[data-tag]');
    tags.forEach(t => { t.hidden = false; });
    more.hidden = true;
    if (!box.getClientRects().length) { tagPopClose(); return; }      // 手機（CSS 藏起來）或還沒排版
    const over = () => box.scrollWidth > box.clientWidth + 1;
    if (!over()) { tagPopClose(); return; }
    more.hidden = false;
    let n = 0;
    for (let i = tags.length - 1; i >= 0; i--) {
      tags[i].hidden = true; n++;
      more.textContent = '⋯ ' + n;
      if (!over()) break;
    }
    const names = tags.filter(t => t.hidden).map(t => t.textContent).join('、');
    more.title = `還有 ${n} 個標籤：${names}`;
    more.setAttribute('aria-label', `還有 ${n} 個標籤：${names}`);
    const pop = document.getElementById('skTagPop');
    if (pop && !pop.hidden) tagPopFill();
  }
  function wireTags() {
    const tb = document.getElementById('skTools'), more = document.getElementById('skTagMore'), pop = document.getElementById('skTagPop');
    if (!tb || !more || !pop) return;
    more.onclick = (e) => {
      e.stopPropagation();
      if (!pop.hidden) { tagPopClose(); return; }
      pop.hidden = false; more.setAttribute('aria-expanded', 'true');
      tagPopFill();
      if (A.dismissable) A.dismissable(pop, tagPopClose, { also: [more] });
      // 固定定位的小框不跟著頁面走：一捲動（頁面或工具列）、一縮放視窗就收，免得框留在原地跟「⋯ N」分家
      window.addEventListener('scroll', tagPopClose, true);
      window.addEventListener('resize', tagPopClose);
    };
    if (tagRO) tagRO.disconnect();
    if (window.ResizeObserver) {
      tagRO = new ResizeObserver(() => fitTags());
      tagRO.observe(tb);
      ['#tfSeg', '#indBtn', '#mtfBtn'].forEach(s => { const e = document.querySelector(s); if (e) tagRO.observe(e); });
    }
    fitTags();
  }

  // ================================================================ Level 2：個股頁
  async function renderStock(code, im, sc, gd) {
    /* ★ 2026-09-26（Andy：「下方產業鏈位置表格 拿掉」）：個股頁最下面那張「產業鏈位置」卡
       （麵包屑、同族群列、環節晶片、剖析圖＋編號清單）整張不掛了 —— #indChain 在個股頁一律收起來。
       ⚠ 只拿掉個股頁的掛載：剖析圖、環節晶片、drawChainMap 這些共用元件照舊給產業地圖頁用。
       上面麵包屑與 K 線卡的「產業鏈／族群」連結還在，要看產業鏈照樣點得過去。*/
    show(false, false, true);
    const pgP = A.load('stock/' + code, { fallback: null });
    /* 索引（stocks.json）說這檔有 60 分 K（tier full）就同時開始載分 K 檔，不用等個股頁回來再多等一趟；
       ensureM60 會接手同一個請求（A.load 對同一個名字只打一次）。*/
    const ix = ((A.D && A.D.stocks) || []).find(r => r.code === code);
    if (ix && ix.tier === 'full') A.load('m60/' + code, { fallback: null });
    const pg = await pgP;
    if (!pg) { await renderStockLite(code, im, sc, gd); return; }
    await ensureM60(pg);
    const m = pg.meta, s = pg.summary || {};
    // 上方產業鏈（同步高亮）
    state.chain = chainOfGroup(im, m.group_id) || 'industry'; state.group = null;
    const chainName = A.L.chains[state.chain] || CHAIN_NAME[state.chain] || state.chain;   // 中文名以 payload 為準，寫死的表只當 fallback
    crumbs([{ label: '產業地圖', href: '#industry' }, { label: chainName, href: '#industry/' + state.chain }, { label: `${m.name} ${m.code}` }]);
    $('#indChain').innerHTML = '';      // 產業鏈位置卡不在個股頁掛了（見 renderStock 開頭）
    // 個股主體
    const el = $('#stockPage');
    const groupLinks = (m.groups || []).map(gn => A.L.groupByName(gn)).join(' ');
    const themeLinks = A.L.themesOf(m.code);
    const TIER = { full: ['分 K 完整', 'cyan', '1 小時／4 小時：每日盤後更新；15 分以下：當天即時'],
                   daily: ['日線以上', '', m60Why(pg)],
                   thin: ['資料準備中', 'amber', '目前只有最近幾天的日線'] };
    const tier = TIER[(m.tier || 'daily')] || TIER.daily;
    /* 週期列（tfButtons）在這裡就要畫，所以設定要先讀進來 —— 以前 state.cfg 到 setupChart 才讀，
       週期列用不到存檔裡的 tfOn，第一次進來會排出預設的週期、跟使用者勾的對不起來。
       選中的週期已經不在列上（被取消勾選）就先換成剩下的（優先日線）。*/
    state.cfg = state.cfg || loadCfg();
    // 上一檔是「分時沒資料、自動退回日 K」→ 這一檔回到預設的分時（見 state 宣告處的 tickFb）
    if (state.tickFb) { state.tf = 'tick'; state.tickFb = false; state.tfAuto = true; }
    if (state.tf === 'tick') state.tfAuto = true;
    if (state.tickNone !== code) state.tickNone = null;
    ensureTf();
    el.innerHTML = `
      <div class="card" id="skChartCard" style="margin-top:var(--gap-card)">
        <div class="row spread" id="skHead">
          <div id="skIdent"><h2>${A.logo ? A.logo(m.code, m.name, 32, 'sklogo') : ''}${A.fmt.esc(m.name)} <span class="mono cyan">${m.code}</span> <small class="muted" style="font-size:13px">${A.fmt.mkt(m.market)}</small></h2>
            <div class="row" id="skMeta" style="gap:6px 12px;margin-top:4px;font-size:13.5px"><span class="muted">產業鏈</span>${A.L.chain(state.chain, chainName)}<span class="muted">族群</span>${groupLinks || '—'}${themeLinks ? `<span class="muted">題材</span>${themeLinks}` : ''}</div>
            <!-- ★ 2026-10-02（Andy #stock/3189，DECISIONS #293）：現價列只留現價、漲跌、即時徽章與時間（徽章由 live.js 插在漲跌後面）；
                 技術分／本益比／同業分位／營收 YoY／分 K 完整五顆標籤搬到下面工具列（#skTags），左欄少一行。-->
            <div class="row" id="skPx" style="margin-top:6px"><span class="num" style="font-size:30px;font-weight:700" id="pxNow" data-live="close" data-lc="${m.code}">${A.fmt.n(s.close)}</span><span class="num ${A.fmt.cls(s.chg_pct)}" style="font-size:18px" data-live="chg" data-lc="${m.code}">${A.fmt.pct(s.chg_pct, 2)}</span></div></div>
        </div>
        <!-- ★ 2026-09-27（Andy：「AI 分析 需要在右上角出現，並且技術面 籌碼面 基本面 消息面 用標籤頁切換」）：
             改前右上只有一行結論（#skAiLine），完整分析是 K 線與分頁之間的長卡（#aiCard）；
             改後整塊 AI 分析住在這裡（K 線卡右上角，卡片夠寬時是跨「名稱區＋工具列」兩列的右欄），
             四個面向用標籤頁切換。版面細節與理由見 site/blocks/stock_ai.js 檔頭。-->
        ${window.StockAI ? '<section class="aipanel" id="skAi" aria-label="AI 分析"></section>' : ''}
        <div class="toolbar" id="skTools" style="margin-top:14px">
          <div class="seg" id="tfSeg">${tfButtons()}</div>
          <button class="btn small" id="tfAdd" title="自訂時間週期">＋</button>
          <!-- ★ 2026-09-26（Andy：「將所有指標納入在 Setting，並且以下拉清單形式呈現」）：
               以前這裡是一整排指標晶片＋右邊一顆「⚙ 設定」開獨立的「圖表設定」面板，兩處管同一件事。
               合成一顆下拉：清單每列＝一個指標（左開關、右 ▸ 就地展開該指標的參數與樣式）。-->
          <button class="btn small inddd" id="indBtn" type="button" aria-haspopup="true" aria-expanded="false" title="指標：開關、參數、顏色與線寬">指標 ▾ <span class="indn" id="indN"></span></button>
          <!-- ★ 2026-10-02（Andy #stock/3189 截圖三，DECISIONS #293）：五顆資訊標籤從現價列搬來「指標」與「四週期同看」中間的空白。
               工具列一律一行（不准折行把週期鈕擠下去）：放不下的標籤從右邊收進「⋯ N」，點開看全部（fitTags）。手機不顯示（手機的數字在「指標」「財務」分頁）。-->
          <div class="sktags" id="skTags" role="group" aria-label="這一檔的關鍵數字">${stockTags(s, tier, code).map(t => `<span class="pill${t[2] ? ' ' + t[2] : ''}" data-tag="${t[0]}"${t[3] ? ` title="${A.fmt.esc(t[3])}"` : ''}>${t[1]}</span>`).join('')}<button type="button" class="pill sktmore" id="skTagMore" aria-haspopup="true" aria-expanded="false" aria-controls="skTagPop" hidden>⋯</button></div>
          <div class="sktagpop" id="skTagPop" role="dialog" aria-label="其他標籤" hidden></div>
          <div class="sp"></div>
          <button class="btn small" id="mtfBtn">${state.mtfMode ? '單一週期' : '四週期同看'}</button>

          <button class="btn small" id="drawTgl" title="畫線工具（手機預設收起來）">✎ 畫線</button>
          <button class="howbtn pop" data-how="kline" data-ttl="K 線" type="button" aria-label="K 線怎麼看">?</button>
          <!-- 「重設縮放」鈕 2026-09-26 搬進圖裡（主圖 K 棒區右下角、價格軸左邊），由 KChart 自己掛（opts.fit）-->
        </div>
        <!-- ★ 2026-09-24 說明精簡：圖下那段滑鼠／拖曳操作說明（.skhelp 第一行）整段搬進「怎麼看 ?」 -->
        <div class="howtxt" id="how-kline" hidden>${A.howHTML('這張圖：這一檔的走勢（預設分時）、K 線、成交量與技術指標。', [
          /* ★ 2026-10-04（稽核第 6 項）：預設週期是「分時」（一條價格線＋昨收虛線），改前條列全是 K 線縮放、分時讀法只在不顯示的小字裡 */
          '預設是分時：線在昨收虛線上＝漲、下＝跌',
          '切 K 線週期：圖內滾輪縮放、價格軸拖曳調高度',
          '雙擊價格軸或按右下 ⌜⌟ 還原；副圖分隔線可拖',
          '週期鈕被劃掉＝這檔沒有那個週期資料',
        ], '「分時」：線在虛線（昨收）上面＝今天漲、下面＝跌，最後一段往哪邊走就是尾盤的方向；要看指標或畫線請切到 K 線週期。滑鼠移到劃掉的週期鈕上會說原因。分 K 每日盤後更新；K 棒會跟著上下寬度一起變。')}</div>
        <!-- ★ 2026-09-29 data-readout：這一行是「這一檔此刻畫的是哪一天、哪個來源、量是不是估計值、有沒有分時」的狀態讀數
             （LiveK.sourceNote／「此檔暫無分時資料，已改用日 K」），跟 #peNote 同一類 —— 每一檔、每個時段都不一樣，
             而且「量是估計值」這種資料誠實聲明必須看得到（個股即時分K 驗收在守），不是可以搬進「?」的說明文字。
             所以不算進「卡片說明 ≤ 40 字」（說明精簡）。⚠ 分時那幾句尾巴還帶一句讀法「虛線＝昨收…」（09-28 分時預設那批寫的，手機一行收起、點開才全文），
             這句要不要搬進 K 線的「?」留給下一批判斷（K 線「?」已經 5 條滿了）。-->
        <div class="note livenote" id="liveNote" data-readout hidden></div>
        <div class="chartwrap" id="chartWrap">${adjTag(pg)}
          <div class="drawbar" id="drawBar"></div>
          <div id="chartHost"></div>
        </div>
        <div class="cfgpop" id="cfgPop" hidden></div>
        ${pg.note ? `<div class="banner on" style="margin:10px 0 0">${A.fmt.esc(pg.note)}</div>` : ''}
        <!-- ★ 2026-10-06（Andy：「這類資訊一律拿掉」，DECISIONS #329）：圖下「資料更新到 YYYY-MM-DD」那行拿掉；新鮮度看全站資料狀態徽章 -->
      </div>
      <!-- #aiCard：只給手機（≤640，mobile v3 分段的「AI 分析」那一段）用的空殼。
           桌機永遠是空的（CSS #aiCard:empty 收掉，不留黑方塊）；手機由 app.js miaStock 把 #skAi 整個節點搬進來，
           回到桌機再搬回 K 線卡右上角。改前（09-26）這裡是完整的 AI 分析長卡，09-27 起內容搬到右上角。-->
      ${window.StockAI ? '<div class="card" style="margin-top:var(--gap-card)" id="aiCard"></div>' : ''}
      <!-- ★ 2026-09-28（Andy）：「籌碼」拆成「法人｜資券｜大戶／散戶」三頁（說明在 tabInst 上方）-->
      <div class="subtabs" id="stockTabs">${tabsFor(code).map(t => `<button data-t="${t[0]}" class="${state.tab === t[0] ? 'on' : ''}">${t[1]}</button>`).join('')}</div>
      <div id="stockTab"></div>`;
    setupChart(pg);
    wireTags();
    if (window.StockAI) window.StockAI.mount(pg, $('#skAi'), A.fmt);
    $$('#stockTabs button').forEach(b => b.onclick = () => { $$('#stockTabs button').forEach(x => x.classList.toggle('on', x === b)); state.tab = b.dataset.t; switchTab(pg, state.tab); });
    renderTab(pg, state.tab);   // 第一次進個股頁：不碰捲動位置（switchTab 只給「點分頁鈕」用）
  }
  /* ★ 2026-10-04（Andy：分頁列切換時位置跳動，「切換時分頁標題固定對齊在同一位置（對齊上方）」）：
     症狀：在「大戶／散戶」（內容很高）捲到分頁列附近，切到「公告 / 新聞」（內容很短）→ 頁面變短，
     瀏覽器把 scrollY 夾到新的最大值，分頁列在視窗裡往下跑一大段。
     做法：① 切之前記下分頁列在視窗裡的 top（被捲出頁首上方時改成「貼齊頁首下方」）；
           ② 內容區給 min-height＝視窗高 − 分頁列底部 −（內容區下面還有的高度）—— 頁面至少長到「分頁列停在原位時視窗還填得滿」，
              瀏覽器就沒有理由夾 scrollY；
           ③ 畫完再補捲一次，把分頁列放回原本的 top（圖表非同步長高不影響：分頁列上方的東西沒變）。
     min-height 只在點分頁時設；第一次進個股頁（renderTab 直接畫）不設、不捲，位置照舊。*/
  function switchTab(pg, tab) {
    const bar = $('#stockTabs'), el = $('#stockTab');
    if (!bar || !el) { renderTab(pg, tab); return; }
    const tb = document.querySelector('.topbar');
    const hdr = tb && getComputedStyle(tb).position !== 'static' ? Math.max(0, tb.getBoundingClientRect().bottom) : 0;
    const top0 = bar.getBoundingClientRect().top;
    const want = top0 < hdr ? hdr + 8 : top0;
    let lastY = null;
    const fit = (late) => {
      if (late && lastY != null && Math.abs(window.scrollY - lastY) > 1) return;   // 使用者已經自己捲了：不搶回來
      const r = bar.getBoundingClientRect();
      const below = Math.max(0, document.documentElement.scrollHeight - (window.scrollY + el.getBoundingClientRect().bottom));
      el.style.minHeight = Math.max(0, Math.ceil(window.innerHeight - (want + r.height) - below)) + 'px';
      const d = bar.getBoundingClientRect().top - want;
      if (Math.abs(d) > 0.5) window.scrollTo({ top: window.scrollY + d, behavior: 'instant' });   // html 有 scroll-behavior:smooth，不指定會用動畫捲、量到的位置是半路
      lastY = window.scrollY;
    };
    el.style.minHeight = Math.ceil(el.getBoundingClientRect().height) + 'px';   // 先撐住舊高度，畫的過程中不先回彈
    renderTab(pg, tab);
    fit();
    requestAnimationFrame(() => fit(true));
    setTimeout(() => fit(true), 120);   // 圖表 setTimeout(20) 的 resize 之後再對一次
  }

  /* ★ 2026-09-25（除權息還原上線後的前端收尾，DECISIONS #261）：K 線與均線已經是**除權息還原價**
     （payload `price_adjust.daily_adjusted`），但畫面上的報價與漲跌是原始價 —— 兩個數字對不上時，
     使用者會以為其中一個錯了（6669 除權後，原始價 2,115、還原後的舊 K 棒只剩三分之一）。
     所以 K 線圖右上角掛一個「還原」小標，滑過（或鍵盤 focus、手機點一下）說清楚哪個是哪個，
     有還原事件就列最近一次：日期、除權（配股比例）或除息、還原係數。沒有還原就不掛，不留一個空標。*/
  function adjTag(pg) {
    const pa = pg && pg.price_adjust;
    if (!pa || !pa.daily_adjusted) return '';
    const ev = (pa.events || []).filter(e => e && e[0]);
    const last = ev.length ? ev[ev.length - 1] : null;
    let lastTxt = '無除權息事件';
    if (last) {
      const sr = +last[2] || 0, pf = +last[1];
      const kind = sr > 0 ? `除權，配股比例 1:${A.fmt.n(sr, 2)}` : '除息（現金股利）';
      lastTxt = `最近一次：<b>${A.fmt.esc(String(last[0]))}</b> ${kind}${Number.isFinite(pf) ? `，還原係數 ${pf.toFixed(4)}` : ''}`;
    }
    return `<span class="adjtag" id="adjTag" tabindex="0" role="note" aria-label="K 線為除權息還原價">還原`
      + `<span class="adjtip" role="tooltip"><b>K 線與均線用除權息還原價；報價與漲跌是原始價</b>`
      + `<span class="adjlast">${lastTxt}</span>`
      + (ev.length > 1 ? `<span class="adjn">共 ${ev.length} 次還原事件</span>` : '')
      + `</span></span>`;
  }

  /* 個股頁的「產業鏈位置」卡（renderChainStrip）2026-09-26 整支拿掉：Andy「下方產業鏈位置表格 拿掉」。
     它只給個股頁用；裡面呼叫的剖析圖（DS.draw／applyDgNative／paintDiagram）、環節晶片、drawChainMap
     都是產業地圖頁的共用元件，一個都沒動。*/

  // ---------------------------------------------------------------- K 線面板
  /* ★ 2026-09-26 晚（Andy）：沒設定過的人預設只開「均線 MA」與「成交量」—— KD／MACD／RSI／BOLL／本益比河流
     一律預設關（參數照舊記得：關著時 prmOf 回 IND_DEF，打開就是 9,3,3／12,26,9）。
     已經有 tw.kcfg 的人不強制改：loadCfg 是 Object.assign(DEFAULT, 存檔)，存檔裡的 kd／macd 會蓋過這裡的 null。
     「停損／目標」（lines）與「MACD 背離」同一天從清單拿掉，所以這裡也沒有 lines 這個鍵了。
     tfOn＝週期列要出現哪些週期；null＝沒設定過 → 用 TF_DEFAULT_ON（見 tfOnSet）。*/
  const DEFAULT_CFG = { ma: [5, 20, 60, 120], maColor: [], maWidth: [], lineWidth: 1,
    boll: null, vol: true, volma: 20, kd: null, macd: null,
    rsi: null, tfs: null, tfOn: null,
    // 每個指標的顏色／線寬／透明度（SMC 供需區那一組 zone 設定 2026-09-26 跟著 SMC 一起拿掉）
    st: {},
    // K 棒寬度（Lightweight Charts 的 barSpacing）；預設比函式庫的 7 寬，Andy 要「default 先長一點」
    bar: 11 };
  // 設定面板要列出來的指標樣式（key、標題、幾個顏色、顏色的名字）
  const STYLE_ROWS = [
    ['boll', 'BOLL 通道', ['c'], ['線']],
    ['vol', '成交量', ['c', 'c2'], ['漲', '跌']],
    ['kd', 'KD', ['c', 'c2'], ['K', 'D']],
    ['macd', 'MACD', ['c', 'c2'], ['DIF', 'MACD']],
    ['rsi', 'RSI', ['c'], ['線']],
  ];
  const STYLE_DEF = {
    boll: { c: '#b39dff' }, vol: { c: '#ff4d6d', c2: '#2ee59d', o: 55 },
    kd: { c: '#3ee0ff', c2: '#ffd166' }, macd: { c: '#3ee0ff', c2: '#ffd166' }, rsi: { c: '#c3ff5b' },
  };
  // 內建週期＋使用者自訂的（nD = N 日合成、nW = N 週合成；分 K 只能用抓得到的那幾檔）
  /* 5秒 / 1分 / 5分 是「當天即時」的，資料不在 payload 裡，而是 livek.js 現場合成的
     （證交所沒有個股的分時檔，所以是 Yahoo 補早盤 ＋ 即時報價每 5 秒補尾巴）。 */
  /* 'tick'＝分時走勢（2026-09-28）：不是 K 棒，是「當日（盤中）或最近一個交易日（盤後）」的一條價格線＋昨收虛線＋分時量，
     由 TickChart（chart.js）畫，資料見 tickData()。放在最前面＝週期列最左邊，而且是預設週期。*/
  /* ★ 2026-10-05（Andy：「5S 週期在指標內刪除」）：5 秒拿掉 —— 週期列、＋週期設定、四週期下拉都不再列。
     livek.js 內部仍收 5 秒序列（分時、1 分 K 的尾巴靠它），只是不再當一個可選週期；存檔裡的 '5s' 由 loadCfg 退回 1分。*/
  const TF_BUILTIN = ['tick', '1m', '5m', '15m', '60m', '240m', '1d', '1w', '1M'];
  const TF_NAME = { tick: '分時', '5s': '5秒', '1m': '1分', '5m': '5分', '15m': '15分', '60m': '1時', '240m': '4時', '1d': '日', '1w': '週', '1M': '月' };
  // 15 分也改成即時（Andy 2026-09-18：「1 5 15 分 K 都限制當天即可」）。
  // 後端不再預先產出 15 分 K —— 那是部署最慢的一塊（DECISIONS #156）。
  const LIVE_TF = ['1m', '5m', '15m'];
  const isLiveTf = (tf) => LIVE_TF.indexOf(tf) >= 0;
  /* 即時週期沒東西可畫時，要講清楚是「還在收」還是「根本沒設來源」。
     2026-09-18 起 15 分也走即時（後端不再預先產出，見 DECISIONS #156）——
     這代表沒設 Worker 的人會多一個週期看不到，所以更不能只寫「還在收集」讓人乾等。*/
  function liveEmptyMsg(tf) {
    const has = !!(window.Live && window.Live.proxy && window.Live.proxy());
    /* 非交易時段（週末、休市、開盤前）：livek.js 會改畫最近交易日；還是空的話，由它講清楚是
       「還在抓」還是「最近交易日也沒有分 K」（冷門股），不要只寫「還在收集」讓人乾等到週一。*/
    const L = window.LiveK;
    if (has && tf && L && L.session && !L.session().live) return L.sourceNote(tf);
    return has ? '即時資料收集中'
               : '尚無即時報價來源';
  }
  const tfLabel = (tf) => TF_NAME[tf] || (/^\d+D$/.test(tf) ? tf.replace('D', ' 日') : /^\d+W$/.test(tf) ? tf.replace('W', ' 週') : tf);
  /* ★ 2026-09-26 晚（Andy）：「週期設置」—— 指標下拉最上面多一區「週期」，勾起來的才出現在週期列
     （與四週期同看每一格的週期下拉）。以前九個內建週期全部排在工具列上，1 分／5 秒這種當天即時的
     對多數人用不到、卻把「指標 ▾」擠到很右邊。預設只勾 1時、4時、日、週、月。
     · tfAll()   ＝可以勾的全部（內建九個＋使用者自訂的 nD／nW）
     · tfOnSet() ＝勾起來的（存在 tw.kcfg 的 tfOn；沒設定過用預設。自訂週期是使用者自己加的，沒設定過時一併算勾起來）
     · tfList()  ＝週期列真的要排的：tfAll 依原本順序濾出勾起來的
     至少留一個：全部被濾光（例如存檔被手改壞）就退回日線。*/
  const TF_DEFAULT_ON = ['tick', '60m', '240m', '1d', '1w', '1M'];
  // 四週期同看每一格是一張 K 線小圖，分時不是 K 線 → 不列進四格的下拉，也不會被自動挑進去
  function mtfTfList() { const l = tfList().filter(t => t !== 'tick'); return l.length ? l : ['1d']; }
  /* ★ 2026-10-06（DECISIONS #326）：1分／5分／15分只有即時來源（livek.js：Yahoo 1 分 K＋報價尾巴，都經過報價代理），
     非管理者一律不列 —— 週期列、＋週期設定、四週期下拉都讀這一支，存檔裡選著這三個的人由 ensureTf 退回日線。*/
  function tfAll() { const c = (state.cfg && state.cfg.tfs) || []; return (liveOK() ? TF_BUILTIN : TF_BUILTIN.filter(t => !isLiveTf(t))).concat(c); }
  function tfOnSet() {
    const c = state.cfg || {}, all = tfAll();
    let on = Array.isArray(c.tfOn) ? c.tfOn.filter(t => all.indexOf(t) >= 0) : TF_DEFAULT_ON.concat(c.tfs || []);
    if (!on.length) on = ['1d'];
    return on;
  }
  function tfList() { const on = tfOnSet(); return tfAll().filter(t => on.indexOf(t) >= 0); }
  /* 目前選中的週期被取消勾選（或存檔裡的週期已經不在列上）→ 自動切到剩下的：優先日線，沒有日線就第一個。
     回傳有沒有換，呼叫端決定要不要重畫。*/
  function ensureTf() {
    const l = tfList();
    if (l.indexOf(state.tf) >= 0) return false;
    state.tf = l.indexOf('1d') >= 0 ? '1d' : l[0];
    return true;
  }
  function tfButtons() { return tfList().map(tf => `<button data-tf="${tf}" class="${tf === state.tf ? 'on' : ''}">${tfLabel(tf)}</button>`).join(''); }
  /* 哪些週期這檔真的有資料：沒有的直接在按鈕上劃掉並寫清楚原因。
     Andy 回報「K 線圖 1 日以下都不見」—— 其實按鈕在，是那檔沒有分 K，
     但按下去才看到一行字，等於要用猜的。現在光看按鈕就知道哪些看得到。 */
  function markTf(pg) {
    $$('#tfSeg button').forEach(b => {
      const tf = b.dataset.tf;
      if (tf === 'tick') {
        // 分時：有沒有資料要等即時層回來才知道（tickData），確定沒有的那一檔才劃掉
        const none = state.tickNone === pg.meta.code;
        b.classList.add('ticktf');
        b.classList.toggle('off', none);
        b.title = none ? '此檔暫無分時資料，已改用日 K'
                       : liveOK() ? '分時走勢：盤中是今天，盤後是最近一個交易日；虛線＝昨收' : '分時走勢：最近一個交易日（盤後資料）；虛線＝昨收';
        return;
      }
      if (isLiveTf(tf)) {
        // 即時週期永遠可以按：盤中會邊看邊長，盤後顯示今天收集到的
        b.classList.remove('off');
        b.classList.add('livetf');
        b.title = '當天即時（每 5 秒更新）';
        return;
      }
      const has = (barsFor(pg, tf) || []).length >= 5;
      // 1時／4時：今天的即時 1 分 K 已經合成接上 → 跟分 K 一樣掛紅點
      const hl = (tf === '60m' || tf === '240m') && hourLive(pg);
      b.classList.toggle('livehr', hl);
      if (hl) { b.classList.remove('off'); b.title = '盤中由即時 1 分 K 合成，收盤後換成正式資料'; return; }
      b.classList.toggle('off', !has);
      b.title = has ? '' : (/m$/.test(tf) ? `${pg.meta.name}：${m60Why(pg)}` : '尚無這個週期的資料');
    });
    // 即時週期的點：非交易時段改灰點（livek.js 判定；它每次收到資料也會自己重塗一次）
    if (window.LiveK && window.LiveK.paintDots) window.LiveK.paintDots();
  }
  function loadCfg() {
    try {
      const s = localStorage.getItem('tw.kcfg');
      if (s) {
        const c = Object.assign({}, DEFAULT_CFG, JSON.parse(s));
        // 2026-09-26 拿掉的 SMC 區間／BOS-CHoCH／供需區樣式：舊的存檔值直接丟掉，下次存檔就乾淨了
        delete c.smc; delete c.marks; delete c.zone;
        /* 同一天晚上拿掉的「MACD 背離」「停損／目標」（Andy：「MACD & 停損／目標背離先拿掉」）：
           舊存檔寫著 macdDiv:true／lines:true 也不畫 —— 鍵直接丟掉，畫圖時另外強制 macdDiv:false（見 mainCfg）。*/
        delete c.macdDiv; delete c.lines;
        /* 2026-10-05 拿掉 5秒週期：存檔裡的 5s（週期勾選、四週期格、目前週期）一律換成 1 分，不留一顆按了沒反應的週期。*/
        const no5 = (a) => (Array.isArray(a) ? a.map(t => (t === '5s' ? '1m' : t)) : a);
        if (Array.isArray(c.tfOn)) c.tfOn = no5(c.tfOn).filter((t, i, x) => x.indexOf(t) === i);
        c.mtfTfs = no5(c.mtfTfs);      // 四格不去重：格數要留 4 格，兩格同為 1 分也照畫（使用者可再換）
        if (c.tf === '5s') c.tf = '1m';
        /* ★ 2026-09-28 分時走勢上線：已經存過週期勾選（tfOn）的舊使用者，自動補勾「分時」（Andy 明講要補，而且要當預設）。
           只補一次（tickMig）：補完之後使用者自己取消勾選，下次載入不會又被勾回來。*/
        if (Array.isArray(c.tfOn) && !c.tickMig) {
          if (c.tfOn.indexOf('tick') < 0) c.tfOn = ['tick'].concat(c.tfOn);
          c.tickMig = 1;
          saveCfg(c);
        }
        return c;
      }
    } catch (e) { /* 忽略 */ }
    return Object.assign({}, DEFAULT_CFG);
  }
  function saveCfg(c) { try { localStorage.setItem('tw.kcfg', JSON.stringify(c)); } catch (e) { /* 忽略 */ } }
  // N 根合成一根（自訂 N 日 / N 週用）
  function groupBars(bars, n) {
    const out = [];
    for (let i = 0; i < bars.length; i += n) {
      const g = bars.slice(i, i + n); if (!g.length) continue;
      out.push([g[g.length - 1][0], g[0][1], Math.max(...g.map(b => b[2])), Math.min(...g.map(b => b[3])),
        g[g.length - 1][4], g.reduce((s, b) => s + (b[5] || 0), 0)]);
    }
    return out;
  }
  /* 資料湖的日線最後一根是「上一個交易日」—— 今天那一筆要等 15:30 那輪管線才寫進去。
     Andy 2026-09-15：「為何個股會是 9/14，而非 9/15呢?…我的目的就是要即時訊息」。
     報價本身就帶著今天的開高低收與累計量，所以盤中就把它接成「今天這根還沒收的日 K」。
     週線／月線是從日線合成的，所以接在日線上，週月線也會跟著長出今天。
     管線晚上把正式資料寫進來之後，日期一樣就直接覆蓋掉，不會變成兩根。 */
  function withToday(daily) {
    const t = window.LiveK && window.LiveK.todayBar ? window.LiveK.todayBar() : null;
    if (!t || !daily || !daily.length) return daily;
    const out = daily.slice();
    const lastDate = String(out[out.length - 1][0]);
    if (t[0] < lastDate) return daily;                 // 報價比資料湖還舊（假日），不動
    if (t[0] === lastDate) out[out.length - 1] = t;    // 同一天 → 用比較新的報價蓋掉
    else out.push(t);
    return out;
  }

  /* 分時走勢的資料（2026-09-28）。回 {pts:[[時間, 價, 量]], prev, date, live, src} 或 null（真的沒有）。
     來源順序：
       ① 即時層 livek.js 的 1 分 K（盤中＝今天：Yahoo 1 分 K 補早盤＋證交所即時報價每 5 秒補尾巴；
          盤後／週末＝最近一個交易日的 Yahoo 1 分 K；Yahoo 查不到的冷門股，盤中開著頁面收到的報價也會疊成點）；
       ② 資料湖的 60 分 K（payload 的 intraday['60m']）最近一個交易日 —— 一天 6 點（開盤＋每小時收盤），
          只在即時層拿不到時當備援，而且那一天必須就是日線的最新交易日（落後的不拿，免得把前天當成今天）。
     昨收：盤中用報價的昨收（證交所的參考價，除權息當天也對）；其他情況用日線裡「那一天之前」的最後一根收盤。*/
  /* 分時說明（2026-10-02，DECISIONS #287）：照實講每一段是哪裡來的，時間寫出來 ——
     「09:00～10:06 來自 Yahoo（延遲）；10:07～10:25 在你打開頁面之前，暫無資料；10:26 之後是本頁即時累積，每 5 秒更新」。
     以前寫「最近一段是證交所即時報價每 5 秒更新」，畫面上卻是 10:06 一條直線跳到 10:26 —— 說明跟圖對不上。
     分段照時間排（livek.minuteSeries 的 segs），所以「中途切到背景又回來」那種兩段即時中間夾一段缺口也講得對。*/
  const TICK_GAP_WHY = {
    lead: '開盤後的分 K 延遲約 20 分鐘',
    open: '在你打開頁面之前',
    idle: '頁面在背景或連線中斷、沒收到報價',
  };
  /* ★ 2026-10-05（Andy：「分時沒有資訊」，10:28～10:43 一段斜線）查證結論：
     · Yahoo 官方說明（help.yahoo.com SLN2310）：.TW／.TWO 由 ICE Data Services 提供、延遲 20 分鐘 —— 不是我們抓太慢；
     · 這段缺口＝「Yahoo 最後一根」到「打開頁面、開始收報價」之間。mis getStockInfo 只有當下快照、證交所沒有個股分時檔，
       www.twse.com.tw/rwd 禁爬，沒有可合法補回過去分鐘的免費來源 → 補不了，只能等 Yahoo 追上來。
     · 盤中每 2 分鐘重抓 Yahoo（livek.refreshHist），缺口會從左邊一路縮掉；分鐘 m 的資料約在 m＋20 分鐘出現，最多再等一輪 2 分鐘。
     所以小標直接寫「Yahoo 延遲約 20 分，約 HH:MM 補上」，時間到了還沒補（重抓失敗）就寫「補資料中」。*/
  const YAHOO_DELAY_MIN = 20;
  function tickGapEta(g) {
    const eta = +g[1] + 60 + (YAHOO_DELAY_MIN + 2) * 60;           // 缺口最後一分鐘＋延遲＋一輪重抓（epoch+8h）
    const now = Date.now() / 1000 + 8 * 3600;
    return now >= eta ? '' : new Date(eta * 1000).toISOString().slice(11, 16);
  }
  function tickGapLabel(g, wait) {
    // 小標只寫一句短的：Yahoo 還會追上來＝寫幾點補上；這檔 Yahoo 根本沒有分 K（冷門股）＝「沒有」，不可以叫人等一個不會來的東西
    if (!wait) return '此段沒有資料';
    const eta = tickGapEta(g);
    return eta ? `Yahoo 延遲約 ${YAHOO_DELAY_MIN} 分，約 ${eta} 補上` : `Yahoo 延遲約 ${YAHOO_DELAY_MIN} 分，補資料中`;
  }
  function tickGapTitle(g, wait) {
    const eta = tickGapEta(g);
    return `${TICK_GAP_WHY[g[2]] || '沒收到資料'}，${wait ? `暫無資料（${eta ? '約 ' + eta + ' 補上' : '稍後補上'}）` : '此段無資料'}`;
  }
  function tickLiveNote(d) {
    const hm = (t) => KUtil.fmtTime(t, '1m').slice(11, 16);
    const rng = (sg) => (sg.a === sg.b ? hm(sg.a) : `${hm(sg.a)}～${hm(sg.b)}`);
    const segs = d.segs || [];
    const lastLive = segs.map(sg => sg.k).lastIndexOf('live');
    const parts = segs.map((sg, i) => {
      if (sg.k === 'yahoo') return `${rng(sg)} 來自 Yahoo（延遲約 20 分鐘）`;
      if (sg.k === 'live') {
        // 盤後（13:35 以後）不再每 5 秒更新，不可以還寫「之後…每 5 秒更新」
        if (i === lastLive && i === segs.length - 1) {
          return d.intraday === false ? `${rng(sg)} 是本頁開著時即時累積的（已收盤，量為估計值）`
            : `${hm(sg.a)} 之後是本頁即時累積，每 5 秒更新、量為估計值`;
        }
        return `${rng(sg)} 是本頁即時累積`;
      }
      const why = sg.why === 'lead' ? 'Yahoo 還沒給今天的 1 分 K（延遲約 20 分鐘）'
        : sg.why === 'idle' ? '頁面在背景或連線中斷、沒收到報價' : '在你打開頁面之前';
      const eta = tickGapEta([sg.a, sg.b]);
      return `${rng(sg)} ${why}，${d.yahooWait === false ? '此段無資料' : `暫無資料（${eta ? '約 ' + eta + ' 補上' : '補資料中'}）`}`;
    });
    if (!parts.length) parts.push('今天的分時');
    return '今天的分時：' + parts.join('；') + '。';
  }
  function tickData(pg) {
    const L = window.LiveK;
    const daily = pg.daily && pg.daily.length ? pg.daily : (pg.ohlcv || []);
    const prevOf = (date) => {
      for (let i = daily.length - 1; i >= 0; i--) if (String(daily[i][0]) < date) return +daily[i][4];
      return null;
    };
    if (L && L.bars && L.session) {
      const ses = L.session();
      /* ★ 2026-10-02（Andy：「個股分時需要有即時走勢」，DECISIONS #287）：今天有盤就改用 minuteSeries ——
         逐分鐘挑來源（一直開著收的那幾分鐘用報價疊、其他用 Yahoo），並帶出 Yahoo 跟報價都沒涵蓋到的缺口，
         讓 TickChart 畫虛線、標「此段等待資料」，不再一條直線從 Yahoo 最後一根拉到第一筆報價。*/
      const ms = ses && ses.live && L.minuteSeries ? L.minuteSeries() : null;
      if (ms && ms.bars.length >= 1) {
        const pc = L.state && +L.state.prevClose;
        const wait = ms.yahooWait !== false;
        return { pts: ms.bars.map(x => [x[0], +x[4], +x[5] || 0]), prev: pc > 0 ? pc : prevOf(ms.date), date: ms.date,
                 live: true, src: 'live', minute: true,
                 gaps: ms.gaps.map(g => [g[0], g[1], tickGapLabel(g, wait), tickGapTitle(g, wait)]),
                 segs: ms.segs, yahooWait: ms.yahooWait, yahoo: ms.yahoo, liveSeg: ms.live,
                 intraday: L.isIntraday ? L.isIntraday() : true };
      }
      const b = L.bars('1m') || [];
      if (b.length >= 2 && ses && ses.date) {
        const pc = L.state && +L.state.prevClose;
        const prev = ses.live && pc > 0 ? pc : prevOf(ses.date);
        return { pts: b.map(x => [x[0], +x[4], +x[5] || 0]), prev, date: ses.date, live: !!ses.live, src: 'live' };
      }
    }
    const h = (pg.intraday && pg.intraday['60m']) || [];
    const lastD = daily.length ? String(daily[daily.length - 1][0]) : null;
    if (h.length && lastD) {
      const day = h.filter(x => String(x[0]).slice(0, 10) === lastD);
      if (day.length) {
        const close = Date.parse(lastD + 'T00:00:00Z') / 1000 + (13 * 60 + 30) * 60;   // 那天 13:30（epoch+8h 口徑）
        const t0 = KUtil.toTime(String(day[0][0]));
        const pts = [[t0, +day[0][1], 0]];
        day.forEach(x => { const t = KUtil.toTime(String(x[0])); pts.push([Math.min(t + 3600, close), +x[4], +x[5] || 0]); });
        return { pts, prev: prevOf(lastD), date: lastD, live: false, src: 'm60' };
      }
    }
    return null;
  }

  /* ★ 2026-09-30 個股 60 分 K 擴到全市場（Andy：「有部分股票…1 小時 4 小時都會是找不到數據」）。
     分 K 不再塞在個股頁 JSON 裡 —— 全市場約 2,000 檔都塞的話網站要多三百多 MB、只看日線的人也要多下載一份 ——
     改成每檔一個 data/m60/<代號>.json（精簡格式：日期一次＋HHMM，見 pipeline/build_payload._m60_payload），
     開個股頁時才載入，還原成原本的 [ISO 時間, 開, 高, 低, 收, 量] 掛回 pg.intraday['60m']，
     所以 barsFor／tickData／四週期小圖一行都不用改。
     meta.m60：ok＝有；none＝沒有（Yahoo 查無、或不在名單）；pending＝還在回補。沒有時一律用 m60Why 講一句話，不留白。*/
  function expandM60(j) {
    const out = [];
    if (!j || !Array.isArray(j.days)) return out;
    const tz = j.tz || '+08:00';
    for (const day of j.days) {
      const d = day[0];
      for (const r of (day[1] || [])) {
        const hm = String(r[0]).padStart(4, '0');
        out.push([`${d}T${hm.slice(0, 2)}:${hm.slice(2)}:00${tz}`, r[1], r[2], r[3], r[4], r[5]]);
      }
    }
    return out;
  }
  async function ensureM60(pg) {
    if (!pg || !pg.meta) return;
    const has = pg.intraday && pg.intraday['60m'] && pg.intraday['60m'].length;   // 舊版 payload 還塞在頁裡
    if (has || pg.meta.m60 !== 'ok') return;
    const j = await A.load('m60/' + pg.meta.code, { fallback: null });
    const bars = expandM60(j);
    pg.m60Failed = !bars.length;          // 標成有卻載不到（網路斷、檔案不在）：講清楚是載入失敗，不是沒資料
    if (bars.length) pg.intraday = Object.assign({}, pg.intraday || {}, { '60m': fixM60(bars, pg) });
  }
  /* ★ 2026-10-04（Andy 截圖：合晶 6182 分時「為何這麼奇怪」）：Yahoo 的 60 分 K 有兩個系統性缺口，
     全市場最近一天 2,062 檔裡 1,613 檔中招：
       ① 09:00 那一根量＝0（Yahoo 把開盤第一小時的量吃掉了）→ 分時／1 時 K 的量柱開頭一片空白；
       ② 沒有 13:30 收盤撮合 → 最後一點停在 13:25 的價，跟日線收盤對不上（6182：134.5 vs 135）。
     修法：用同一天日線（證交所口徑，權威）回補 —— 量缺的那一根＝日量 − 其他根量合計（含收盤撮合量，
     拆不開，所以一起算在開盤那根，註解講明）；最後一根的收盤改成日線收盤、高低跟著撐開。*/
  function fixM60(bars, pg) {
    const daily = (pg.daily && pg.daily.length ? pg.daily : pg.ohlcv) || [];
    const dmap = {};
    daily.forEach(r => { dmap[String(r[0])] = r; });
    const byDay = {};
    bars.forEach((b, i) => { const d = String(b[0]).slice(0, 10); (byDay[d] = byDay[d] || []).push(i); });
    const out = bars.map(b => b.slice());
    // 日線是「還原權值」：最後一次除權息（因子≠1）之前的日子，日線價已乘上因子，跟分 K 原始價不能直接比 → 只修之後的日子
    const ev = ((pg.price_adjust && pg.price_adjust.daily_adjusted && pg.price_adjust.events) || []).filter(e => +e[1] !== 1);
    const cut = ev.length ? String(ev[ev.length - 1][0]) : '';
    Object.keys(byDay).forEach(d => {
      const r = dmap[d]; if (!r || d < cut) return;
      const idx = byDay[d], dv = +r[5], dc = +r[4];
      const zero = idx.filter(i => !(+out[i][5] > 0));
      if (zero.length === 1 && dv > 0) {
        const rest = idx.reduce((s, i) => s + (+out[i][5] || 0), 0);
        if (dv > rest) out[zero[0]][5] = dv - rest;
      }
      const last = out[idx[idx.length - 1]];
      if (dc > 0 && Math.abs(+last[4] - dc) / dc < 0.1) {   // 差超過一成不是收盤撮合，是除權息或資料錯，不碰
        last[4] = dc; last[2] = Math.max(+last[2], dc); last[3] = Math.min(+last[3], dc);
      }
    });
    return out;
  }
  function m60Why(pg) {
    const st = pg && pg.meta && pg.meta.m60;
    if (pg && pg.m60Failed) return '1 小時分 K 載入失敗，請重新整理';
    if (st === 'none') return '此檔沒有盤中分 K 資料';
    if (st === 'pending') return '1 小時分 K 還在補資料';
    return '此檔沒有 1 小時分 K';
  }

  /* ★ 2026-10-05（Andy 10:47 回報 3221：「1時／4時沒有即時」）：資料湖的 60 分 K 最後一根是上一個交易日（盤後管線才寫今天），
     盤中 1時／4時 停在昨天。改成：今天有盤時，把 livek.js 今天的 1 分 K（Yahoo 早盤＋報價尾巴）照後端 session_key 的切法
     合成今天的 1 時棒 —— 09:00 起每小時一根、13:00～13:30 併進 13:00 那根（pipeline/compute/intraday_bars.session_key）——
     接在資料湖後面；資料湖之後補上同一天時以資料湖為準（那天的即時棒整天丟掉，不混兩種口徑）。
     4 時＝一天一根（session_key 的 H4 就是 09:00 一格），由合併後的 1 時依日期併。*/
  function liveHourBars(pg) {
    const L = window.LiveK;
    if (!L || !L.session || !L.bars) return [];
    const ses = L.session();
    if (!ses || !ses.live || !ses.date) return [];
    const out = []; let cur = null, key = null;
    for (const b of (L.bars('1m') || [])) {
      const t = +b[0]; if (!isFinite(t)) continue;
      const iso = new Date(t * 1000).toISOString();         // epoch+8h → 台北牆鐘
      if (iso.slice(0, 10) !== ses.date) continue;
      const h = Math.min(13, Math.max(9, +iso.slice(11, 13)));
      const k = `${ses.date}T${String(h).padStart(2, '0')}:00:00+08:00`;
      if (k !== key) { if (cur) out.push(cur); key = k; cur = [k, +b[1], +b[2], +b[3], +b[4], +b[5] || 0]; }
      else { cur[2] = Math.max(cur[2], +b[2]); cur[3] = Math.min(cur[3], +b[3]); cur[4] = +b[4]; cur[5] += +b[5] || 0; }
    }
    if (cur) out.push(cur);
    return out;
  }
  function hourBars(pg) {
    const lake = (pg.intraday && pg.intraday['60m']) || [];
    const live = liveHourBars(pg);
    if (!live.length) return lake;
    const days = new Set(lake.map(b => String(b[0]).slice(0, 10)));
    const add = live.filter(b => !days.has(b[0].slice(0, 10)));
    return add.length ? lake.concat(add) : lake;
  }
  /** 今天的 1時／4時 有沒有接上即時（週期鈕紅點用）。*/
  function hourLive(pg) {
    const lake = (pg.intraday && pg.intraday['60m']) || [];
    const live = liveHourBars(pg);
    return live.length > 0 && !lake.some(b => String(b[0]).slice(0, 10) === live[0][0].slice(0, 10));
  }
  function byDay(bars) {
    const out = []; let cur = null, d = null;
    for (const b of bars) {
      const k = String(b[0]).slice(0, 10);
      if (k !== d) { if (cur) out.push(cur); d = k; cur = [`${k}T09:00:00+08:00`, +b[1], +b[2], +b[3], +b[4], +b[5] || 0]; }
      else { cur[2] = Math.max(cur[2], +b[2]); cur[3] = Math.min(cur[3], +b[3]); cur[4] = +b[4]; cur[5] += +b[5] || 0; }
    }
    if (cur) out.push(cur);
    return out;
  }
  function barsFor(pg, tf) {
    // 即時週期不吃 payload，直接跟 livek.js 拿（它自己在收）
    if (isLiveTf(tf)) return (window.LiveK ? window.LiveK.bars(tf) : []) || [];
    const daily = withToday(pg.daily && pg.daily.length ? pg.daily : pg.ohlcv);
    if (tf === '1d') return daily;
    if (tf === '1w') return KUtil.resampleDaily(daily, 'W');
    if (tf === '1M') return KUtil.resampleDaily(daily, 'M');
    let m = /^(\d+)D$/.exec(tf); if (m) return groupBars(daily || [], +m[1]);
    m = /^(\d+)W$/.exec(tf); if (m) return groupBars(KUtil.resampleDaily(daily || [], 'W'), +m[1]);
    // 240 分由 60 分現場合成（4 根併 1 根），後端不再預先產出 800 根
    // —— 同一份資料存兩次是浪費（DECISIONS #156）。
    // 4 時＝一天一根（session_key H4）。以前是「每 4 根併 1 根」，一天 5 根 → 會跨日錯位。
    if (tf === '240m') return byDay(hourBars(pg));
    if (tf === '60m') return hourBars(pg);
    return (pg.intraday && pg.intraday[tf]) || [];
  }
  /* 四週期小圖吃的指標：跟大圖同一份設定，但只取主圖疊加（均線、BOLL）與成交量 ——
     KD／MACD／RSI 是副圖，300px 的小格塞不下；本益比河流只對日線有意義（停損目標 2026-09-26 晚整個拿掉）。*/
  /* 主圖吃的指標：就是 cfg，只是 MACD 背離一律關掉（2026-09-26 晚從清單拿掉）。
     chart.js 的背離是「macdDiv !== false 就畫」—— 大盤頁（market3.js）還在用那個預設，所以不改 chart.js，
     而是在個股頁這一層強制關；也不寫進 tw.kcfg（寫進去會連大盤頁一起關掉）。*/
  function mainCfg(cfg) { return Object.assign({}, cfg, { macdDiv: false }); }
  function miniCfg(cfg) {
    return { ma: cfg.ma || [], maColor: cfg.maColor, maWidth: cfg.maWidth, lineWidth: cfg.lineWidth,
             boll: cfg.boll || null, vol: !!cfg.vol, volma: cfg.volma, st: cfg.st };
  }


  /* ================================================================ SMC 區域疊圖（2026-10-05）
     Andy：「AI 分析／技術分析卡裡提到的價位，需要補在上方 K 線圖，並且這是可以開啟關閉的指標，在設定內可以勾選」。
     ★ 資料一律取 payload 現成的，**前端不另算**（不然圖上跟 AI 卡會出現兩套數字）：
       · 需求／供給區、BOS／CHoCH 日期：pg.mtf.tf[週期]（compute/mtf.py；與 AI 卡技術面週期列同一份）
       · 最近支撐／壓力：pg.analysis.facets.tech.levels（AI 卡「支撐／壓力區」那兩欄本人）
       · 停損：pg.analysis.facets.tech.checks.risk.a.stop（AI 卡「停損距離」那一條）
     週期對應：看日線畫日線的區域、週線畫週線、月線畫月線；1 時／4 時 只有 payload 有那一格才畫
     （mtf.py 只對有分 K 的個股算），其餘週期（分時、分 K、自訂 N 日）沒有區域資料 —— 只畫支撐壓力與停損，圖底小字講明。
     BOS／CHoCH 的線價：payload 只給「突破那根的日期」，沒給被突破的擺動點價位 ——
     所以線畫在**突破那根的收盤價**，標籤寫明「收」，不假裝那是擺動點價位（要精準價位得改 mtf.py 輸出，另案）。
     2026-09-26 Andy 曾說「將這兩個指標拿掉」—— 這次是他自己要求加回、而且是**可開關、預設關**，不改變沒開的人的畫面。*/
  const SMC_KINDS = [['demand', '需求區'], ['supply', '供給區'], ['bos', 'BOS'], ['choch', 'CHoCH'], ['sr', '支撐／壓力'], ['stop', '停損']];
  const SMC_TFS = ['60m', '240m', '1d', '1w', '1M'];
  function smcKindsOf(cfg) { return Object.assign({ demand: true, supply: true, bos: true, choch: true, sr: true, stop: true }, cfg.smcKinds || {}); }
  function smcOverlay(pg, tf, kc, cfg) {
    if (!kc || !kc.setSmc) return null;
    if (!cfg.smcOv) { kc.setSmc(null); state.smc = null; return null; }
    const on = smcKindsOf(cfg), data = kc.data || [];
    if (!data.length) { kc.setSmc(null); return null; }
    const tt = KUtil.toTime;
    const ge = (a, b) => (typeof a === 'number' ? a >= b : String(a) >= String(b));
    // 這個週期裡第一根 ≥ 該日期的 K 棒（週線的區域 since 是週中某一天，要對到那一週那根）
    const snap = (date) => { if (!date) return null; const t = tt(String(date)); const d = data.find(x => ge(x.time, t)); return d || null; };
    const n = (v) => A.fmt.n(v);
    // 日期：跟最後一根同一年只寫 月-日，跨年寫完整日期（週線的區域常是前一兩年形成的，只寫 06-07 會看錯年）
    const yr = String((pg.mtf && pg.mtf.tf && pg.mtf.tf['1d'] && pg.mtf.tf['1d'].last_bar) || pg.as_of || '').slice(0, 4);
    const md = (d) => { const x = String(d || '').slice(0, 10); return x.slice(0, 4) === yr ? x.slice(5) : x; };
    const mt = pg.mtf && pg.mtf.tf && SMC_TFS.indexOf(tf) >= 0 ? pg.mtf.tf[tf] : null;
    const tfLab = mt ? (mt.label || tf) : '';
    const zones = [], lines = [];
    if (mt) {
      ['demand', 'supply'].forEach(k => {
        if (!on[k]) return;
        (mt[k] || []).forEach(z => {
          const b = snap(z.since);
          const nm = k === 'demand' ? '需求區' : '供給區';
          zones.push({ kind: k, low: z.low, high: z.high, since: b ? b.time : null, sinceDate: z.since, tf: tfLab,
            label: `${nm} ${tfLab} ${n(z.low)}–${n(z.high)}`,
            tip: `${nm}（${tfLab}）${n(z.low)}–${n(z.high)}，形成於 ${md(z.since)}` });
        });
      });
      const mk = mt.marks || {};
      const ch = (mk.choch || []).slice().sort((a, b) => String(a[0]).localeCompare(String(b[0])));
      if (on.bos && (mk.bos || []).length) {
        const d = mk.bos.slice().sort().pop(), b = snap(d);
        if (b) {
          const prev = ch.filter(c => String(c[0]) <= String(d)).pop();
          const dir = prev ? prev[1] : (mt.trend || 1);
          lines.push({ kind: 'bos', price: b.close, t0: b.time, date: d, dir, color: '#ffd166', width: 1.2, dash: [5, 4],
            label: `BOS ${dir < 0 ? '↓' : '↑'} ${md(d)} 收 ${n(b.close)}` });
        }
      }
      if (on.choch && ch.length) {
        const c = ch[ch.length - 1], b = snap(c[0]);
        if (b) lines.push({ kind: 'choch', price: b.close, t0: b.time, date: c[0], dir: c[1], color: '#b39dff', width: 1.2, dash: [2, 3],
          label: `CHoCH ${c[1] < 0 ? '↓' : '↑'} ${md(c[0])} 收 ${n(b.close)}` });
      }
    }
    const tech = pg.analysis && pg.analysis.facets && pg.analysis.facets.tech;
    if (tech && on.sr) {
      const lv = tech.levels || {};
      const s = (lv.support || [])[0], r = (lv.resistance || [])[0];
      // 支撐畫在區間上緣（價格回落先碰到的那一邊）、壓力畫在下緣；標籤寫完整區間與來源週期
      if (s) lines.push({ kind: 'sup', price: s.high, color: '#2ee59d', width: 2.4, label: `最近支撐 ${s.label || ''} ${n(s.low)}–${n(s.high)}` });
      if (r) lines.push({ kind: 'res', price: r.low, color: '#ff4d6d', width: 2.4, label: `最近壓力 ${r.label || ''} ${n(r.low)}–${n(r.high)}` });
    }
    const ra = tech && tech.checks && tech.checks.risk && tech.checks.risk.a;
    if (on.stop && ra && ra.stop != null) lines.push({ kind: 'stop', price: ra.stop, color: '#ffb020', width: 1.4, dash: [6, 3],
      label: `停損 ${n(ra.stop)}${ra.pct != null ? `（距現價 ${Number(ra.pct).toFixed(1)}%）` : ''}` });
    const noTf = !mt ? ` · ${TF_NAME[tf] || tf}線沒有 SMC 區域資料（只畫支撐壓力與停損）` : '';
    const note = `技術區域僅供研究參考，不構成投資建議${noTf}`;
    const o = { tf, zones, lines, note, style: { label: true } };
    kc.setSmc(o);
    state.smc = o;          // 驗收讀這個（跟 AI 卡比對數字）
    return o;
  }

  function setupChart(pg) {
    state.cfg = state.cfg || loadCfg();
    /* 即時分 K：切到這一檔就開始收，每收到一筆就重畫（畫面位置由 setBars(..., keepView) 保住）。
       Andy 2026-09-15：「當我點擊一般股票時也能做到這樣的效果」 */
    stopLive();
    tickT0 = Date.now(); clearTimeout(tickTimer);
    if (tchart) { try { tchart.destroy(); } catch (e) { /* 容器已換掉 */ } tchart = null; }
    if (window.LiveK) {
      window.LiveK.attach(pg.meta.code, pg.meta.market);
      liveOff = window.LiveK.onUpdate(() => {
        if (!document.getElementById('lwc')) {
          /* 四週期同看：只有「開的時候 Yahoo 還沒回來、所以空著」的即時格，資料到了重建一次
             （非交易時段那幾格就是這樣才畫得出最近交易日）。盤中不會每 5 秒重建四張圖。*/
          if (state.mtfMode && document.querySelector('#mtfGrid .empty[data-live]') && !window.LiveK.loading) {
            miniCharts.forEach(c => { try { c.destroy(); } catch (e) { /* 忽略 */ } }); miniCharts = [];
            buildMtfGrid(pg);
          }
          return;      // 四週期同看或已離開，不用畫主圖
        }
        // 即時週期固然要重畫；日／週／月因為最後一根是「今天還沒收的」，也要跟著跳；分時的尾巴也是即時的
        if (state.tf === 'tick' || isLiveTf(state.tf) || ['1d', '1w', '1M', '60m', '240m'].indexOf(state.tf) >= 0) apply();
        markTf(pg);
      });
    }
    const host = $('#chartHost');
    const cfg = state.cfg;
    /* ================================================================ 指標下拉（2026-09-26）
       Andy：「將所有指標納入在 Setting，並且以下拉清單形式呈現，在點擊下拉是清單設定」。
       以前同一件事分兩處：工具列一整排晶片（開關＋參數）、「⚙ 設定」開另一個面板（顏色、線寬、透明度、均線）。
       現在只有一顆「指標 ▾（已開 N）」：
         · 清單每一列＝一個指標：左邊開關＋名稱＋參數摘要（整塊都是開關，點哪裡都切），右邊 ▸ 就地展開設定
         · 最上面「整體」一列：整體線寬、K 棒寬度（不是指標，沒有開關）
         · 均線那一列展開＝原本的均線編輯（最多 6 條、新增／刪除、顏色、粗細）
       面板沿用 #cfgPop（fixed、貼著按鈕、夾進視窗、內部捲動；點外面或 Esc 關 —— dismissable）。
       所有改動照舊寫 tw.kcfg、即時套用；單一週期與四週期同看共用同一份（四週期只畫主圖疊加＋成交量，
       KD／MACD／RSI 這類副圖在 300px 的小格裡放不下，那幾列會標「四週期不畫」）。
       ★ 同一天 Andy 要拿掉的「SMC 區間」「BOS/CHoCH」不在清單裡，供需區顏色那一段設定也一起拿掉了；
         localStorage 裡舊的 smc／marks／zone 值直接忽略（loadCfg 會清掉）。*/
    const IND_DEF = { ma: [5, 20, 60, 120], boll: { n: 20, k: 2 }, kd: { n: 9, m1: 3, m2: 3 }, macd: { f: 12, s: 26, g: 9 }, rsi: { n: 14 } };
    const clone = (o) => JSON.parse(JSON.stringify(o));
    /* 指標關著的時候參數去哪：記在 cfg.prm[k]。關掉 KD 再打開，剛剛調的 5,3,3 要還在，
       以前關掉就是 null、再開回 9,3,3 —— 使用者調過的東西被悄悄丟掉。*/
    const prmOf = (k) => cfg[k] || (cfg.prm || {})[k] || clone(IND_DEF[k]);
    const flip = (k) => {
      if (cfg[k] && (!Array.isArray(cfg[k]) || cfg[k].length)) { (cfg.prm = cfg.prm || {})[k] = cfg[k]; cfg[k] = null; }
      else { const v = prmOf(k); cfg[k] = Array.isArray(v) && !v.length ? clone(IND_DEF[k]) : v; }
    };
    const setPrm = (k, p, v) => {
      if (cfg[k]) { cfg[k][p] = v; return; }
      const o = prmOf(k); o[p] = v; (cfg.prm = cfg.prm || {})[k] = o;
    };
    const P = (k) => ({ get: (p) => prmOf(k)[p], set: (p, v) => setPrm(k, p, v) });
    const MINI_SKIP = '四週期不畫';
    const IND = [
      { k: 'base', label: '整體', base: true, sum: () => `線寬 ${cfg.lineWidth || 1}px · K 棒 ${cfg.bar || 11}px` },
      { k: 'ma', label: '均線 MA', color: '#ffd166', on: () => !!(cfg.ma && cfg.ma.length), toggle: () => flip('ma'),
        sum: () => prmOf('ma').join(',') },
      { k: 'boll', label: 'BOLL 通道', color: '#8b7bff', on: () => !!cfg.boll, toggle: () => flip('boll'),
        sum: () => { const p = prmOf('boll'); return `${p.n},${p.k}`; },
        params: [{ p: 'n', lab: '天數', min: 2, max: 240 }, { p: 'k', lab: '倍數', min: 0.5, max: 5, step: 0.1 }], io: P('boll'), st: 'boll' },
      { k: 'vol', label: '成交量', color: '#8ea0c4', on: () => !!cfg.vol, toggle: () => { cfg.vol = !cfg.vol; },
        sum: () => (cfg.volma ? `量均 ${cfg.volma}` : ''),
        params: [{ p: 'volma', lab: '量均線（0＝不畫）', min: 0, max: 240 }],
        io: { get: () => cfg.volma || 0, set: (p, v) => { cfg.volma = v; } }, st: 'vol' },
      { k: 'kd', label: 'KD', color: '#ffd166', mini: MINI_SKIP, on: () => !!cfg.kd, toggle: () => flip('kd'),
        sum: () => { const p = prmOf('kd'); return `${p.n},${p.m1},${p.m2}`; },
        params: [{ p: 'n', lab: '天數', min: 2, max: 120 }, { p: 'm1', lab: 'K 平滑', min: 1, max: 30 }, { p: 'm2', lab: 'D 平滑', min: 1, max: 30 }], io: P('kd'), st: 'kd' },
      { k: 'macd', label: 'MACD', color: '#3ee0ff', mini: MINI_SKIP, on: () => !!cfg.macd, toggle: () => flip('macd'),
        sum: () => { const p = prmOf('macd'); return `${p.f},${p.s},${p.g}`; },
        params: [{ p: 'f', lab: '快線', min: 2, max: 120 }, { p: 's', lab: '慢線', min: 3, max: 240 }, { p: 'g', lab: '訊號', min: 2, max: 120 }], io: P('macd'), st: 'macd' },
      /* 「MACD 背離」與「停損／目標」兩列 2026-09-26 晚拿掉（Andy：「MACD & 停損／目標背離先拿掉」）。
         MACD 本身留著（預設關）；背離在主圖由 mainCfg() 強制 macdDiv:false，停損目標的價位線整段不畫了。
         右側分析卡上那行「停損・目標」文字是分析卡的事，不在這裡。*/
      { k: 'rsi', label: 'RSI', color: '#c3ff5b', mini: MINI_SKIP, on: () => !!cfg.rsi, toggle: () => flip('rsi'),
        sum: () => String(prmOf('rsi').n), params: [{ p: 'n', lab: '天數', min: 2, max: 120 }], io: P('rsi'), st: 'rsi' },
      /* 本益比河流：把下方那張河流圖的五條倍數線疊在 K 棒上（需要近四季 EPS，只有日／週／月線畫得出來）。*/
      { k: 'peRiver', label: '本益比河流', color: '#b39dff', mini: MINI_SKIP, on: () => !!cfg.peRiver, toggle: () => { cfg.peRiver = !cfg.peRiver; },
        sum: () => '日週月' },
      /* SMC 區域（2026-10-05）：AI 卡講的需求／供給區、BOS／CHoCH、最近支撐壓力、停損畫上主圖。預設關；子項勾選存 cfg.smcKinds。*/
      { k: 'smcOv', label: 'SMC 區域（需求／供給／BOS）', color: '#2ee59d', mini: MINI_SKIP, on: () => !!cfg.smcOv, toggle: () => { cfg.smcOv = !cfg.smcOv; },
        sum: () => { const o = smcKindsOf(cfg); return SMC_KINDS.filter(x => o[x[0]]).map(x => x[1]).join('・') || '全部不畫'; } },
    ];
    const IDX = {}; IND.forEach(d => { IDX[d.k] = d; });
    const nOn = () => IND.filter(d => !d.base && d.on()).length;
    const indBtn = $('#indBtn');
    const paintBtn = () => { const n = $('#indN'); if (n) n.textContent = `（已開 ${nOn()}）`; };
    const hasBody = (d) => !!(d.base || d.k === 'ma' || d.k === 'peRiver' || d.k === 'smcOv' || d.params || d.st);
    const stVal = (k) => Object.assign({ w: cfg.lineWidth || 1, o: 100 }, STYLE_DEF[k], (cfg.st || {})[k] || {});
    const maRow = (n, i) => `<div class="frow marow" data-i="${i}">
          <input type="number" min="2" max="480" value="${n}" data-f="n" aria-label="第 ${i + 1} 條均線天數">
          <input type="color" value="${(cfg.maColor || [])[i] || KUtil.colors.ma[i % 6]}" data-f="c" aria-label="顏色">
          <input type="range" min="1" max="4" step="1" value="${(cfg.maWidth || [])[i] || cfg.lineWidth || 1}" data-f="w" style="width:78px" aria-label="粗細">
          <button class="btn small" data-f="del" type="button" title="移除這條">✕</button></div>`;
    const bodyHTML = (d) => {
      if (d.base) return `<div class="frow"><label>整體線寬</label><input id="lw" type="range" min="1" max="4" step="1" value="${cfg.lineWidth || 1}"><span class="val" id="lwv">${cfg.lineWidth || 1}px</span></div>
        <div class="frow"><label>K 棒寬度</label><input id="bw" type="range" min="3" max="28" step="1" value="${cfg.bar || 11}"><span class="val" id="bwv">${cfg.bar || 11}px</span></div>`;
      if (d.k === 'ma') {
        const mas = prmOf('ma');
        return `<div id="maRows">${mas.map(maRow).join('')}</div>
          <div class="row" style="margin-top:6px"><button class="btn small" id="maAdd" type="button" ${mas.length >= 6 ? 'disabled' : ''}>＋ 新增均線</button></div>`;
      }
      if (d.k === 'smcOv') {
        const o = smcKindsOf(cfg);
        return `<div class="note">日／週／月線畫該週期的區域；分時與分 K 只畫支撐壓力與停損。</div>
          <div class="frow" id="smcKinds" style="flex-wrap:wrap;gap:4px 12px">${SMC_KINDS.map(x => `<label class="plab"><input type="checkbox" class="smck" data-s="${x[0]}"${o[x[0]] ? ' checked' : ''}> ${x[1]}</label>`).join('')}</div>`;
      }
      if (d.k === 'peRiver') {
        const pes = peStyle(cfg);
        return `<div class="note">與下方本益比河流圖共用</div>
          <div class="frow strow" id="peRow" style="flex-wrap:wrap">
          ${PE_ZONES.map((z, i) => `<span class="cwrap" title="${z.name}"><input type="color" data-z="${i}" value="${pes.z[i]}"><em>${z.name}</em></span>`).join('')}
          <label class="plab">線寬</label><input type="range" min="1" max="4" step="1" data-f="w" value="${pes.w}" style="width:60px">
          <label class="plab">透明</label><input type="range" min="5" max="100" step="5" data-f="o" value="${pes.o}" style="width:70px">
          <span class="val" id="peOv">${pes.o}%</span></div>`;
      }
      let h = '';
      if (d.params) h += `<div class="frow prow">${d.params.map(p => `<label class="plab">${p.lab} <input type="number" data-p="${p.p}" min="${p.min}" max="${p.max}" step="${p.step || 1}" value="${d.io.get(p.p)}"></label>`).join('')}</div>`;
      if (d.st) {
        const row = STYLE_ROWS.find(r => r[0] === d.st), v = stVal(d.st);
        h += `<div class="frow strow" data-k="${d.st}">
          ${row[2].map((ck, i) => `<span class="cwrap" title="${row[3][i]}"><input type="color" data-f="${ck}" value="${v[ck]}"><em>${row[3][i]}</em></span>`).join('')}
          <label class="plab">線寬</label><input type="range" min="1" max="4" step="1" data-f="w" value="${v.w}" style="width:64px">
          <label class="plab">透明</label><input type="range" min="15" max="100" step="5" data-f="o" value="${v.o}" style="width:78px">
          <span class="val" data-f="ov">${v.o}%</span></div>`;
      }
      return h;
    };
    const rowHTML = (d) => {
      const open = indOpen.has(d.k), body = hasBody(d);
      const note = d.mini && state.mtfMode ? `<span class="inote">${d.mini}</span>` : '';
      const head = d.base
        ? `<span class="isw" data-exp="1"><i style="background:transparent;border:1px solid var(--ink-3)"></i><span class="iname">${d.label}</span><span class="isum"></span></span>`
        : `<label class="isw"><input type="checkbox" class="ion" data-k="${d.k}"${d.on() ? ' checked' : ''}><i style="background:${d.color}"></i><span class="iname">${d.label}</span><span class="isum"></span>${note}</label>`;
      return `<div class="indrow${!d.base && d.on() ? ' on' : ''}${open ? ' open' : ''}" data-k="${d.k}">
        <div class="ihead">${head}${body ? `<button type="button" class="iexp" data-k="${d.k}" aria-expanded="${open}" aria-label="${d.label} 設定" title="${d.label} 設定">▸</button>` : ''}</div>
        ${body ? `<div class="ibody"${open ? '' : ' hidden'}>${bodyHTML(d)}</div>` : ''}</div>`;
    };
    /* ---- 週期區（2026-09-26 晚，Andy「新增週期設置」）：放在「整體」下面、指標上面，一直攤開（不用按 ▸），
       每個週期一顆勾選晶片。勾＝出現在 K 線上方的週期列與四週期同看的下拉；至少留一個（最後一顆勾不掉）。*/
    const tfRowHTML = () => {
      const on = tfOnSet();
      return `<div class="indrow tfrow on" data-k="tf"><div class="ihead"><span class="isw tfhd"><i style="background:transparent;border:1px solid var(--ink-3)"></i><span class="iname">週期</span><span class="isum" id="tfSum"></span></span></div>
        <div class="ibody tfbody"><div class="tfchk" id="tfChk">${tfAll().map(tf => `<label class="tfc${on.indexOf(tf) >= 0 ? ' on' : ''}" data-tf="${tf}"><input type="checkbox" class="tfon" data-tf="${tf}"${on.indexOf(tf) >= 0 ? ' checked' : ''}>${tfLabel(tf)}</label>`).join('')}</div></div></div>`;
    };
    const paintTfSet = (pop) => {
      const on = tfList();
      $$('.tfc', pop).forEach(l => {
        const c = $('input', l), v = on.indexOf(l.dataset.tf) >= 0, last = v && on.length <= 1;
        c.checked = v; c.disabled = last; l.classList.toggle('on', v); l.classList.toggle('last', last);
        l.title = last ? '至少要留一個週期' : isLiveTf(l.dataset.tf) ? '當天即時（盤中每 5 秒補一根）' : '';
      });
      const sm = $('#tfSum', pop); if (sm) sm.textContent = on.map(tfLabel).join(' ');
    };
    // 開關、摘要、「已開 N」只改字，不重畫清單 —— 重畫會把正在打字的輸入框換掉、焦點跟著掉
    const paintHead = () => {
      const pop = $('#cfgPop');
      if (pop && pop.dataset.kind === 'ind') {
        paintTfSet(pop);
        $$('.indrow', pop).forEach(r => {
          const d = IDX[r.dataset.k]; if (!d) return;
          const s = $('.isum', r); if (s) s.textContent = d.sum() || '';
          if (d.base) return;
          const on = d.on(); r.classList.toggle('on', on);
          const c = $('input.ion', r); if (c) c.checked = on;
        });
      }
      paintBtn();
    };
    // 設定改了 → 存檔 → 目前這個模式重畫（單一週期重跑 apply；四週期只把四張小圖的指標重套）
    const commit = () => {
      saveCfg(cfg); paintHead();
      if (state.mtfMode) miniCharts.forEach(c => { try { c.applyIndicators(miniCfg(cfg)); } catch (e) { /* 小圖已銷毀 */ } });
      else apply();
    };
    const syncMa = () => {
      const list = [], col = [], wid = [];
      $$('#maRows .marow').forEach(r => {
        list.push(+$('[data-f=n]', r).value || 20);
        col.push($('[data-f=c]', r).value);
        wid.push(+$('[data-f=w]', r).value || 1);
      });
      if (cfg.ma && cfg.ma.length) cfg.ma = list; else (cfg.prm = cfg.prm || {}).ma = list;
      cfg.maColor = col; cfg.maWidth = wid;
      const add = $('#maAdd'); if (add) add.disabled = list.length >= 6;   // 刪到剩 5 條要能再加回來
      commit();
    };
    const wireMa = () => $$('#maRows .marow').forEach(r => {
      $$('input', r).forEach(i => { i.oninput = syncMa; i.onchange = syncMa; });
      $('[data-f=del]', r).onclick = () => { r.remove(); syncMa(); };
    });
    /* 勾／取消一個週期：存檔 → 重排週期列 → 目前的週期被取消就切走（ensureTf，優先日線）。
       四週期同看：每一格的下拉只列勾起來的週期，所以整片重建（存檔裡那一格的週期被取消時 mtfPick 會重挑）。*/
    const setTfOn = (tf, on) => {
      let cur = tfOnSet();
      if (on) { if (cur.indexOf(tf) < 0) cur = cur.concat(tf); }
      else { if (cur.length <= 1) { paintHead(); return; } cur = cur.filter(t => t !== tf); }
      cfg.tfOn = tfAll().filter(t => cur.indexOf(t) >= 0);
      saveCfg(cfg);
      const moved = ensureTf();
      $('#tfSeg').innerHTML = tfButtons(); wireTf(); markTf(pg);
      paintHead();
      if (state.mtfMode) build(); else if (moved) apply();
    };
    const wireInd = (pop) => {
      $$('input.tfon', pop).forEach(c => { c.onchange = () => setTfOn(c.dataset.tf, c.checked); });
      $$('input.ion', pop).forEach(c => { c.onchange = () => { IDX[c.dataset.k].toggle(); commit(); }; });
      $$('input.smck', pop).forEach(c => { c.onchange = () => { cfg.smcKinds = Object.assign(smcKindsOf(cfg), { [c.dataset.s]: c.checked }); commit(); }; });
      const expand = (k) => {
        const r = pop.querySelector(`.indrow[data-k="${k}"]`); if (!r) return;
        const b = $('.ibody', r); if (!b) return;
        const open = b.hidden; b.hidden = !open; r.classList.toggle('open', open);
        const x = $('.iexp', r); if (x) x.setAttribute('aria-expanded', String(open));
        if (open) indOpen.add(k); else indOpen.delete(k);
      };
      $$('.iexp', pop).forEach(b => { b.onclick = () => expand(b.dataset.k); });
      $$('.isw[data-exp]', pop).forEach(s => { s.onclick = () => expand(s.closest('.indrow').dataset.k); });
      // 參數：數字框改完（離開或按 Enter）才套用；範圍外的值退回原本的數字，不讓一個 0 把指標弄壞
      $$('.prow input[data-p]', pop).forEach(inp => {
        const d = IDX[inp.closest('.indrow').dataset.k];
        const take = () => {
          const v = +inp.value, lo = +inp.min, hi = +inp.max;
          if (inp.value === '' || !Number.isFinite(v) || v < lo || v > hi) { inp.value = d.io.get(inp.dataset.p); return; }
          const val = inp.step && +inp.step < 1 ? Math.round(v * 10) / 10 : Math.round(v);
          inp.value = val;
          if (val === d.io.get(inp.dataset.p)) return;
          d.io.set(inp.dataset.p, val); commit();
        };
        inp.onchange = take;
        inp.onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); take(); } };
      });
      $$('.strow[data-k]', pop).forEach(r => {
        const upd = () => {
          const o = Object.assign({}, (cfg.st || {})[r.dataset.k] || {});
          $$('input', r).forEach(i => { o[i.dataset.f] = i.type === 'color' ? i.value : +i.value; });
          const ov = $('[data-f=ov]', r); if (ov) ov.textContent = o.o + '%';
          (cfg.st = cfg.st || {})[r.dataset.k] = o; commit();
        };
        $$('input', r).forEach(i => { i.oninput = upd; i.onchange = upd; });
      });
      const pr = $('#peRow', pop);
      if (pr) {
        const upd = () => {
          const z = PE_ZONES.map((_, i) => $(`[data-z="${i}"]`, pr).value);
          const w = +$('[data-f=w]', pr).value || 1, o = +$('[data-f=o]', pr).value || 30;
          const ov = $('#peOv'); if (ov) ov.textContent = o + '%';
          // 保留 of（填滿模式自己的透明度，下方河流圖在用）—— 以前整包覆寫會把它弄丟
          cfg.st = cfg.st || {};
          cfg.st.pe = Object.assign({}, cfg.st.pe || {}, { z, w, o }); commit();
        };
        $$('input', pr).forEach(i => { i.oninput = upd; i.onchange = upd; });
      }
      const lw = $('#lw', pop), bw = $('#bw', pop);
      if (lw) lw.oninput = () => {
        cfg.lineWidth = +lw.value || 1; $('#lwv').textContent = lw.value + 'px';
        // 整體線寬帶動每條均線（跟以前的設定面板一樣）
        $$('#maRows [data-f=w]').forEach(i => { i.value = lw.value; });
        cfg.maWidth = prmOf('ma').map(() => cfg.lineWidth);
        commit();
      };
      if (bw) bw.oninput = () => {
        cfg.bar = +bw.value || 11; $('#bwv').textContent = bw.value + 'px'; commit();
        // apply() 對「同一檔同一週期」的重畫會保留使用者滾輪縮放過的棒寬（即時更新那條路）；這裡是親手調的 → 直接套
        if (kchart && kchart.setBarSpacing && !state.mtfMode) kchart.setBarSpacing(cfg.bar);
      };
      wireMa();
      const add = $('#maAdd', pop);
      if (add) add.onclick = () => {
        const i = $$('#maRows .marow').length; if (i >= 6) return;
        const d = document.createElement('div'); d.innerHTML = maRow(10, i).trim();
        $('#maRows').appendChild(d.firstChild); wireMa(); syncMa();
      };
      const rs = $('#cfgReset', pop);
      if (rs) rs.onclick = () => {
        // 自訂週期（tfs）與四週期各格選的週期（mtfTfs）不是「指標」，回復預設不動它們
        // 週期列勾了哪些（tfOn）也一樣不是指標
        const keep = { tfs: cfg.tfs, mtfTfs: cfg.mtfTfs, tfOn: cfg.tfOn };
        Object.keys(cfg).forEach(k => { delete cfg[k]; });
        Object.assign(cfg, clone(DEFAULT_CFG), keep);
        closePop(pop); commit();
        if (kchart && kchart.setBarSpacing && !state.mtfMode) kchart.setBarSpacing(cfg.bar);
      };
    };
    const openInd = () => {
      const pop = $('#cfgPop');
      // ★ 用「畫面上真的看得到嗎」決定開或關，不是只看 hidden —— 理由見 popVisible() 上面那段
      if (popVisible(pop, 'ind')) { closePop(pop); return; }
      pop.hidden = false; pop.dataset.kind = 'ind'; pop.classList.add('indpop');
      pop.innerHTML = `<div class="ttl">指標</div>
        ${state.tf === 'tick' && !state.mtfMode ? '<div class="note tknote" id="tkNote">分時不畫指標，設定套用於 K 線</div>' : ''}
        <div class="indlist" id="indList">${rowHTML(IND[0])}${tfRowHTML()}${IND.slice(1).map(rowHTML).join('')}</div>
        <div class="ifoot"><button class="btn small" id="cfgReset" type="button">回復預設</button><div class="sp" style="flex:1"></div></div>`;
      wireInd(pop); paintHead();
      indBtn.setAttribute('aria-expanded', 'true');
      placePop(pop, indBtn);
    };
    indBtn.onclick = openInd;
    paintBtn();
    /* 主圖右下角的「重設縮放」（KChart 自己掛那顆 #fitBtn，見 chart.js）：
       連同拖過的面板高度一起還原 —— 拉壞了要有一鍵回去的地方。*/
    const mainFit = () => {
      const c = state.cfg || loadCfg();
      if (c.paneH) { delete c.paneH; saveCfg(c); state.cfg = c; if (kchart) kchart.applyIndicators(mainCfg(c)); }
      if (kchart) kchart.resetView(160);
    };
    /* ★ 2026-10-02（DECISIONS #289）：文字工具不再跳 window.prompt（「miaozike.github.io 顯示：文字內容」），
       改成在點下去的位置直接出現可編輯的文字框（drawtools.js），所以這裡拿掉 onText。*/
    const newMain = (box, tf) => new KChart(box, { tf, fit: mainFit, fitId: 'fitBtn' });
    const build = () => {
      if (kchart) { kchart.destroy(); kchart = null; } miniCharts.forEach(c => c.destroy()); miniCharts = [];
      if (tchart) { tchart.destroy(); tchart = null; }
      if (state.mtfMode) { paintTickMode(false); host.innerHTML = `<div class="mtf-grid" id="mtfGrid"></div>`; buildMtfGrid(pg); return; }
      host.innerHTML = `<div id="lwc"><div class="legend-ov" id="legendOv"></div><div class="ohlcbox" id="ohlcBox" hidden></div></div>`;
      if (state.tf !== 'tick') kchart = newMain($('#lwc'), state.tf);
      apply();
      enableDraw(pg);
    };
    /* ---- 分時模式下不適用的東西（2026-09-28）：
       · 畫線工具：手繪線是存在「某一檔某個 K 線週期」的座標上，分時沒有 K 棒 → 工具列收起、✎ 畫線鈕停用；
       · 指標下拉：不停用（週期勾選也住在裡面），但按鈕變淡、說明寫「分時不畫指標」；
       · 「還原」小標：分時是原始成交價，不是還原價，收起來免得誤會。*/
    const paintTickMode = (on) => {
      const w = $('#chartWrap'); if (w) w.classList.toggle('tickmode', !!on);
      const dt = $('#drawTgl');
      if (dt) {
        if (on && !dt.disabled) { dt.dataset.t0 = dt.title; dt.title = '分時不能畫線'; }
        if (!on && dt.disabled && dt.dataset.t0) dt.title = dt.dataset.t0;
        dt.disabled = !!on;
      }
      const ib = $('#indBtn');
      if (ib) {
        ib.classList.toggle('tickdim', !!on);
        ib.title = on ? '分時不畫指標' : '指標';
      }
    };
    /* ---- 分時走勢（週期「分時」）：資料見 tickData()，圖見 chart.js 的 TickChart。*/
    const applyTick = (box) => {
      paintTickMode(true);
      state.fallbackTf = null; state.offDay = null;
      if (kchart) { kchart.destroy(); kchart = null; }
      const L = window.LiveK;
      const d = tickData(pg);
      if (!d) {
        if (tchart) { tchart.destroy(); tchart = null; }
        const waiting = L && !L.settled && Date.now() - tickT0 < TICK_WAIT;
        if (waiting) {
          box.innerHTML = '<div class="empty" style="height:100%" data-tickwait="1">分時資料載入中…</div>';
          setLiveNote('');
          clearTimeout(tickTimer);
          tickTimer = setTimeout(() => { if (state.tf === 'tick' && !state.mtfMode && $('#lwc')) apply(); }, Math.max(300, TICK_WAIT - (Date.now() - tickT0) + 100));
          return;
        }
        state.tickNone = pg.meta.code;
        if (state.tfAuto) {
          // 預設帶進來的分時沒有資料 → 這一檔自動改用日 K 當預設（Andy 的規格），按鈕與短註講清楚
          const rest = tfList().filter(t => t !== 'tick');
          const fb = rest.indexOf('1d') >= 0 ? '1d' : (rest[0] || '1d');
          state.tf = fb; state.tfAuto = false; state.tickFb = true; state.tickFbTf = fb;
          $$('#tfSeg button').forEach(x => x.classList.toggle('on', x.dataset.tf === fb));
          markTf(pg); paintTickMode(false);
          box.innerHTML = '';
          apply();
          return;
        }
        markTf(pg);
        box.innerHTML = '<div class="empty" style="height:100%">此檔暫無分時資料</div>';
        setLiveNote('此檔暫無分時資料');
        return;
      }
      if (state.tickNone === pg.meta.code) { state.tickNone = null; markTf(pg); }
      if (!tchart || !box.contains(tchart.el) || tchart.el !== box) {
        if (tchart) { tchart.destroy(); tchart = null; }
        box.innerHTML = '<div class="legend-ov" id="legendOv"></div>';
        tchart = new TickChart(box);
      }
      tchart.setData(d);
      state.tickSrc = d.src; state.tickDate = d.date;
      tchart.setWatermark(`${pg.meta.name} ${pg.meta.code} · 分時 · ${d.date}${d.live ? '' : '（非即時）'}`);
      setLiveNote(d.src === 'm60'
        ? (liveOK() ? `${d.date} 分時（60 分 K 備援，非即時）` : `${d.date} 分時（盤後資料）`)
        : d.live
          ? tickLiveNote(d)
          : `${d.date} 分時（非即時，開盤後自動換即時）`);
      const legend = $('#legendOv');
      const rows = tchart.pts;
      const show = (r) => {
        if (!legend) return;
        const p = r || rows[rows.length - 1]; if (!p) { legend.innerHTML = ''; return; }
        const chg = d.prev ? p.value - d.prev : null;
        const col = A.upDown(chg || 0);
        legend.innerHTML = `<b>${KUtil.fmtTime(p.time, '1m').slice(11)}</b>　價 <b style="color:${col}">${A.fmt.n(p.value)}</b>`
          + (chg != null ? `　<span style="color:${col}">${chg > 0 ? '+' : ''}${A.fmt.n(chg)}（${A.fmt.pct(chg / d.prev * 100, 2)}）</span>` : '')
          + (p.v != null ? `　量 ${A.fmt.lot((p.v || 0) / 1000)}` : '')
          + (d.prev ? `<br><span class="muted">昨收 ${A.fmt.n(d.prev)}</span>` : '');
      };
      show(null); tchart.onCrosshair(show);
    };
    const apply = () => {
      const box = $('#lwc'); if (!box) return;
      state._apply = apply;      // 驗收用：模擬一次「即時更新造成的重畫」
      if (state.tf === 'tick') { applyTick(box); return; }
      paintTickMode(false);
      if (tchart) { tchart.destroy(); tchart = null; box.innerHTML = ''; }
      /* ★ 2026-09-25（審查 R5）：即時分 K（1／5／15 分）在 Yahoo 抓不到時，以前只剩一塊空白＋一行字。
         改成**先退回有資料的週期**（有 1 時 K 就畫 1 時，沒有就畫日線），上面那行說明講清楚
         「分 K 抓不到、現在畫的是哪一個」；即時報價一接上（每收到一筆都會重跑 apply），自動換回分 K。
         ⚠ state.tf 不動（按鈕仍亮在 1 分），只是這一次畫的是 tf。沒設即時來源的情況不退回 ——
         那是「根本沒有即時」，照舊顯示空狀態文案（驗收 `個股` 段就是驗這個）。*/
      let tf = state.tf;
      let bars = barsFor(pg, tf);
      let live = isLiveTf(tf);
      let fbNote = '';
      if (live && (!bars || bars.length < 2) && window.LiveK && window.LiveK.histFailed && window.LiveK.histFailed()) {
        const fb = (barsFor(pg, '60m') || []).length >= 5 ? '60m' : '1d';
        fbNote = window.LiveK.sourceNote(state.tf).replace(/，目前只有.*$/, '')
          + `。先顯示${fb === '60m' ? ' 1 小時' : '日線'} K`;
        tf = fb; bars = barsFor(pg, fb); live = false;
      }
      /* 非交易時段（Andy 2026-09-26「為何這邊分 K 無法使用？」）：即時週期畫的是「最近交易日」那一天，
         livek.js 判定哪一天；5 秒那天沒收過就改畫 1 分（時間軸與游標才會印到分鐘、日期是那一天）。*/
      const offDay = live && window.LiveK && window.LiveK.offDay ? window.LiveK.offDay() : null;
      if (offDay && window.LiveK.drawnTf) tf = window.LiveK.drawnTf(state.tf);
      state.offDay = offDay;      // 驗收讀這個
      if (!bars || bars.length < (live ? 2 : 5)) {
        const why = live
          ? (window.LiveK ? window.LiveK.sourceNote(state.tf) : '即時報價載入中')
          : pg.meta.tier === 'thin' ? (pg.note || '尚無歷史價量資料')
          : /m$/.test(state.tf) ? m60Why(pg)
          : '這個週期尚無資料';
        if (kchart) { kchart.destroy(); kchart = null; }
        box.innerHTML = `<div class="empty" style="height:100%">${A.fmt.esc(why)}</div>`;
        setLiveNote(live ? why : '');
        return;
      }
      setLiveNote(fbNote || (live && window.LiveK ? window.LiveK.sourceNote(state.tf) : '')
        || (state.tickFbTf === state.tf && state.tickNone === pg.meta.code ? '此檔暫無分時資料，已改用日 K。' : ''));
      state.fallbackTf = fbNote ? tf : null;      // 驗收讀這個
      // 上一個週期沒資料時圖被拆掉了，換回有資料的週期要重建（不重建的話會整張空白到重新整理為止）
      if (!kchart || !$('#legendOv')) {
        if (kchart) { kchart.destroy(); kchart = null; }
        box.innerHTML = '<div class="legend-ov" id="legendOv"></div><div class="ohlcbox" id="ohlcBox" hidden></div>';
        kchart = newMain(box, tf);
        enableDraw(pg);
      }
      // 即時更新（同一檔、同一個週期、圖還在）就保留目前的縮放與位置
      const keep = kchart._liveKey === pg.meta.code + '|' + tf;
      kchart._liveKey = pg.meta.code + '|' + tf;
      kchart.setBars(bars, tf, keep);
      /* 本益比倍數線：算好之後掛在 chart 上（不要塞進 cfg —— cfg 會被寫進 localStorage，
         幾千筆數字存進去毫無意義）。applyIndicators 會自己去讀 this.peBands。*/
      kchart.peBands = cfg.peRiver ? peBandsForBars(peRiver(pg), bars, peStyle(cfg)) : null;
      kchart.applyIndicators(mainCfg(cfg));
      smcOverlay(pg, tf, kchart, cfg);
      /* ★ 棒寬只在「換股票／換週期」時套用設定值。
         以前每次 apply() 都套一次 —— 而盤中每幾秒就會 apply() 一次，
         所以使用者滾滾輪放大之後，下一次更新就把棒寬硬拉回 cfg.bar，
         畫面看起來就是「縮放完自己跳回原來大小」（Andy 2026-09-18）。
         keep 為真＝這是即時更新造成的重畫，要尊重使用者自己拉的縮放。*/
      if (!keep && kchart.setBarSpacing) kchart.setBarSpacing(cfg.bar || 11);
      /* SMC 需求／供給區塊與 BOS／CHoCH／掃蕩標記 2026-09-26 從 K 線上拿掉（Andy：「將這兩個指標拿掉」）。
         多週期判讀卡（renderMtf）與 Python 端 compute/mtf.py 的 SMC 判讀照舊 —— 拿掉的只是圖上那兩層。*/
      /* 停損／目標 1／目標 2 三條價位線 2026-09-26 晚拿掉（Andy「停損／目標…先拿掉」），不再 setPriceLines。*/
      const legend = $('#legendOv');
      const TFN = { '5s': '5 秒（即時）', '1m': '1 分（即時）', '5m': '5 分（即時）', '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' };
      kchart.setWatermark(`${pg.meta.name} ${pg.meta.code} · ${offDay ? `${TF_NAME[tf] || tf} · ${offDay}（非即時）` : (TFN[tf] || tf)}${fbNote ? '（分 K 暫代）' : ''}`);
      const at = (arr, i) => (arr ? arr[i == null ? arr.length - 1 : i] : null);
      const show = (i, pt) => {
        const idx = i == null ? kchart.data.length - 1 : i; const d = kchart.data[idx]; if (!d) return; const prev = kchart.data[idx - 1]; const vals = kchart.values || {};
        showOhlcBox(d, prev, pt, tf);
        const chg = prev ? (d.close - prev.close) / prev.close * 100 : null; const amp = d.low ? (d.high - d.low) / d.low * 100 : null;
        // 顏色一定要跟著主題走，不可以寫死深色主題那兩個螢光色 ——
        // #2ee59d 印在淺色主題的圖例底（近白）對比只有 1.64，等於看不見。
        // 這是 D1（DECISIONS #152）漏掉的一行，2026-09-18 被淺色主題掃描抓到。
        const col = A.upDown(d.close >= d.open ? 1 : -1);
        let s = `<b>${KUtil.fmtTime(d.time, tf)}</b>　開 ${A.fmt.n(d.open)}　高 ${A.fmt.n(d.high)}　低 ${A.fmt.n(d.low)}　收 <b style="color:${col}">${A.fmt.n(d.close)}</b>${chg != null ? ` <span style="color:${A.upDown(chg)}">${A.fmt.pct(chg, 2)}</span>` : ''}　振幅 ${amp != null ? A.fmt.n(amp, 1) + '%' : '—'}　量 ${A.fmt.lot(d.volume / 1000)}`;
        const parts = []; (cfg.ma || []).forEach((n, k) => { const m = at(vals['MA' + n], i); if (m != null) parts.push(`<span style="color:${KUtil.colors.ma[k % 6]}">MA${n} ${A.fmt.n(m)}</span>`); });
        if (vals.BOLL) { const u = at(vals.BOLL.up, i), lo = at(vals.BOLL.low, i); if (u != null) parts.push(`<span style="color:${KUtil.colors.boll}">BOLL ${A.fmt.n(lo)} – ${A.fmt.n(u)}</span>`); }
        // 本益比倍數線：直接把「幾倍＝股價多少」寫在圖例上，不然圖上五條虛線看不出誰是誰
        if (vals.PE) {
          const bits = vals.PE.map(b => { const v = at(b.vals, i); return v == null ? null : `<span style="color:${b.color}">${b.mult}倍 ${A.fmt.n(v)}</span>`; }).filter(Boolean);
          if (bits.length) parts.push('本益比 ' + bits.join('　'));
        }
        legend.innerHTML = s + (parts.length ? '<br>' + parts.join('　') : '');
        /* 資訊列佔多高，主圖頂端就留多少（kchart.reserveTop，見 chart.js）：K 棒最高點永遠在資訊列下面 */
        if (kchart.reserveTop && legend.offsetParent) {
          const r0 = kchart.el.getBoundingClientRect(), r1 = legend.getBoundingClientRect();
          kchart.reserveTop(Math.max(0, r1.bottom - r0.top));
        }
        const pl = {};
        if (cfg.vol) pl.vol = `成交量 <b>${A.fmt.lot(d.volume / 1000)}</b>${cfg.volma && at(vals.VOLMA, i) != null ? `　<span style="color:${KUtil.colors.ma[0]}">MA${cfg.volma} ${A.fmt.lot(at(vals.VOLMA, i) / 1000)}</span>` : ''}`;
        if (vals.KD) pl.kd = `KD(${cfg.kd.n},${cfg.kd.m1},${cfg.kd.m2})　<span style="color:${KUtil.colors.k}">K ${A.fmt.n(at(vals.KD.k, i), 1)}</span>　<span style="color:${KUtil.colors.d}">D ${A.fmt.n(at(vals.KD.d, i), 1)}</span>`;
        if (vals.MACD) pl.macd = `MACD(${cfg.macd.f},${cfg.macd.s},${cfg.macd.g})　<span style="color:${KUtil.colors.dif}">DIF ${A.fmt.n(at(vals.MACD.dif, i))}</span>　<span style="color:${KUtil.colors.dea}">MACD ${A.fmt.n(at(vals.MACD.dea, i))}</span>　OSC <span style="color:${A.upDown(at(vals.MACD.osc, i))}">${A.fmt.n(at(vals.MACD.osc, i))}</span>`;
        if (vals.RSI) pl.rsi = `RSI(${cfg.rsi.n})　<span style="color:${KUtil.colors.rsi}">${A.fmt.n(at(vals.RSI, i), 1)}</span>`;
        kchart.setPaneLabels(pl);
      };
      show(null, null); kchart.onCrosshair(show);
      /* 面板高度：拖完（滑鼠放開）就記下來，下次打開、換股票、換週期都沿用。
         Andy 2026-09-15：「下方MACD KD 成交量等範圍上下可以拉大」—— 拉得動只是第一步，
         拉完換一檔又縮回去等於白拉。 */
      if (!box._paneSave) {
        box._paneSave = true;
        /* 放開的是右下角那顆「重設縮放」就不存：它的 click 會把 paneH 清掉、面板高度改回預設，
           120ms 後這裡再量一次就會把「預設高度」當成使用者拖出來的存回去 —— 等於重設沒生效。*/
        box.addEventListener('pointerup', (ev) => (ev.target && ev.target.closest && ev.target.closest('.kfit')) ? null : setTimeout(() => {
          if (!kchart || !kchart.paneHeights) return;
          const h = kchart.paneHeights();
          // 面板在還沒畫出來時 getHeight() 會回 0，那種讀數不能存（存了下次就把版面壓扁）
          if (!h || !h.main) return;
          if (Object.keys(h).some(k => k !== 'main' && !h[k])) return;
          const before = JSON.stringify(cfg.paneH || {});
          if (JSON.stringify(h) === before) return;
          cfg.paneH = h; saveCfg(cfg);
        }, 120));
      }
      // 手繪線是「每檔每週期一組」，換週期要換一組，不然會畫到上一個週期的檔案裡
      if (kchart.draw && kchart.draw.key !== `tw.draw.${pg.meta.code}.${state.tf}`) enableDraw(pg);
    };
    // ---- 時間週期（含自訂）
    const wireTf = () => $$('#tfSeg button').forEach(b => {
      b.onclick = () => {
        $$('#tfSeg button').forEach(x => x.classList.toggle('on', x === b)); state.tf = b.dataset.tf;
        // 使用者自己按的週期：不再自動退回（分時沒資料就明講沒資料）；換下一檔也照這個週期
        state.tfAuto = false; state.tickFb = false; state.tickFbTf = null;
        if (state.mtfMode) build(); else apply();
      };
      b.oncontextmenu = (e) => { // 自訂的週期按右鍵可以移除
        if (TF_BUILTIN.includes(b.dataset.tf)) return;
        e.preventDefault();
        cfg.tfs = (cfg.tfs || []).filter(t => t !== b.dataset.tf);
        if (Array.isArray(cfg.tfOn)) cfg.tfOn = cfg.tfOn.filter(t => t !== b.dataset.tf);
        saveCfg(cfg);
        ensureTf();
        $('#tfSeg').innerHTML = tfButtons(); wireTf(); markTf(pg); build();
      };
    });
    wireTf(); markTf(pg);
    $('#tfAdd').onclick = () => {
      const pop = $('#cfgPop');
      if (popVisible(pop, 'tf')) { closePop(pop); return; }
      pop.hidden = false; pop.dataset.kind = 'tf'; pop.classList.remove('indpop');
      const ib = $('#indBtn'); if (ib) ib.setAttribute('aria-expanded', 'false');
      pop.innerHTML = `<div class="ttl">自訂時間週期</div>
        <div class="note">用日線合成，例如 3 日＝三根日線併一根</div>
        <div class="row" style="margin-top:8px"><input id="tfN" type="number" min="2" max="60" value="3" style="width:64px">
        <select id="tfU"><option value="D">日</option><option value="W">週</option></select>
        <button class="btn small primary" id="tfOk">加入</button><button class="btn small" id="tfNo">關閉</button></div>`;
      $('#tfOk').onclick = () => {
        const n = Math.max(2, Math.min(60, +$('#tfN').value || 3)), u = $('#tfU').value;
        const id = n + u;
        // 自己加的週期當然要看得到：一併勾進週期列（tfOn），不然按了「加入」週期列上卻沒有它
        const onBefore = tfOnSet();
        cfg.tfs = [...new Set([...(cfg.tfs || []), id])].slice(0, 6);
        cfg.tfOn = tfAll().filter(t => onBefore.indexOf(t) >= 0 || t === id);
        saveCfg(cfg);
        state.tf = id; pop.hidden = true; $('#tfSeg').innerHTML = tfButtons(); wireTf(); markTf(pg); build();
      };
      $('#tfNo').onclick = () => { closePop(pop); };
      placePop(pop, $('#tfAdd'));
    };

    // ---- 「⚙ 設定」鈕與獨立的「圖表設定」面板 2026-09-26 拿掉：內容全部搬進上面的「指標 ▾」下拉

    $('#mtfBtn').onclick = () => { state.mtfMode = !state.mtfMode; $('#mtfBtn').textContent = state.mtfMode ? '單一週期' : '四週期同看'; build(); drawBarLock(); };
    /* 2026-09-28：「⤢ 寬版」鈕拿掉 —— 它唯一的作用是收起右側事件欄；事件改成浮層抽屜之後圖本來就吃滿全寬，
       寬版那組較高的圖高也直接收成預設（index.html 的 #lwc）。*/
    /* ★ 2026-09-23 手機優先改版 G8（依據 `docs/mobile_audit.md`）：
       390px 量到 `.drawbar` 被攤平成橫向兩列、約 20 顆 20×20～30×24px 的鈕，
       而桌機是圖表左側的直排工具列 —— 位置對不起來，手指也點不準。
       手機預設收起來，這顆開關就在同一排工具列上（桌機 display:none，因為那裡本來就常駐）。
       ⚠ 收起來不是拿掉：畫過的線照樣在圖上，只是工具列收著；狀態會記住。 */
    const drawTgl = $('#drawTgl'), wrap = $('#chartWrap');
    if (drawTgl && wrap) {
      let on = false;
      try { on = localStorage.getItem('tw.drawbar') === '1'; } catch (e) { /* 忽略 */ }
      const paintDraw = () => {
        wrap.classList.toggle('drawon', on);
        drawTgl.classList.toggle('on', on);
        drawTgl.textContent = on ? '✎ 畫線 ✓' : '✎ 畫線';
        drawTgl.title = on ? '收起畫線工具列' : '打開畫線工具列';
      };
      drawTgl.onclick = () => {
        on = !on;
        try { localStorage.setItem('tw.drawbar', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
        paintDraw();
      };
      paintDraw();
    }
    drawBar(); build(); drawBarLock();
  }

  // 每檔每週期各存一份手繪線，換股或換週期就換一組
  function enableDraw(pg) {
    if (!kchart) return;
    const d = kchart.enableDrawing(`tw.draw.${pg.meta.code}.${state.tf}`);
    // 顏色／線寬／填滿這些預設樣式由 DrawTools 自己記（tw.draw.style），這裡只要把目前選的工具交給新的那一組
    if (d) d.setTool(drawTool);
  }

  /* 跟著游標走的資訊框（Andy 2026-09-15：「當游標移動過去時 需要在旁邊顯示開高收低 日期 時間等基本資訊」，
     附了一張看盤軟體的截圖當範例）。
     原本只有左上角那一條 legend，游標移到右半邊要一直回頭看，而且會蓋到 K 棒。
     這個框跟著十字線跑，靠近右邊界就自動翻到游標左側，不會被切掉。 */
  function showOhlcBox(d, prev, pt, tf) {
    const el = $('#ohlcBox'); if (!el) return;
    if (!pt) { el.hidden = true; return; }
    const chg = prev ? d.close - prev.close : null;
    const pct = prev && prev.close ? chg / prev.close * 100 : null;
    const cls = chg == null ? '' : chg > 0 ? 'up' : chg < 0 ? 'down' : '';
    const row = (k, v, c) => `<tr><th>${k}</th><td class="${c || ''}">${v}</td></tr>`;
    const amt = d.volume && d.close ? d.volume * d.close : null;   // 概算：量(股) × 收盤
    el.innerHTML = `<div class="oh">${A.fmt.esc(KUtil.fmtTime(d.time, tf))}</div>
      <table>
        ${row('開盤', A.fmt.n(d.open), d.open >= (prev ? prev.close : d.open) ? 'up' : 'down')}
        ${row('最高', A.fmt.n(d.high), 'up')}
        ${row('最低', A.fmt.n(d.low), 'down')}
        ${row('收盤', A.fmt.n(d.close), cls)}
        ${row('漲跌額', chg == null ? '—' : (chg > 0 ? '+' : '') + A.fmt.n(chg), cls)}
        ${row('漲跌幅', pct == null ? '—' : A.fmt.pct(pct, 2), cls)}
        ${row('成交量', A.fmt.lot(d.volume / 1000))}
        ${row('成交額', amt ? A.fmt.yi(amt) : '—')}
      </table>`;
    el.hidden = false;
    // 游標在左半邊就放右邊，反之亦然；上下也夾在圖內
    const host = el.parentElement;
    const W = host.clientWidth, H = host.clientHeight;
    const bw = el.offsetWidth || 150, bh = el.offsetHeight || 190;
    let x = pt.x + 16;
    if (x + bw > W - 8) x = pt.x - bw - 16;
    if (x < 6) x = 6;
    let y = pt.y - bh / 2;
    y = Math.max(6, Math.min(y, H - bh - 6));
    el.style.left = Math.round(x) + 'px';
    el.style.top = Math.round(y) + 'px';
  }

  // ---------------------------------------------------------------- 繪圖工具列（TradingView 式）
  /* ★ 2026-10-02（DECISIONS #289）：工具列與所有繪圖互動搬到 site/drawtools.js。
     這裡只剩掛載：工具列上留工具本身，顏色／線寬／方框填滿與透明度搬進圖上的屬性列
     （Andy：「方框在上面，『填滿』卻是工具列最下面另一顆獨立按鈕」）。
     drawTool／drawW／drawFill 留著是因為 _dbg() 與舊驗收還讀它們，由 DrawTools 回呼同步。 */
  let drawTool = 'cursor', drawW = DrawTools.STYLE.w, drawFill = DrawTools.STYLE.fill;
  function drawBar() {
    const bar = $('#drawBar'); if (!bar) return;
    DrawTools.mountBar(bar, {
      tool: drawTool,
      get: () => (kchart && kchart.draw) || null,
      onTool: (t) => { drawTool = t; },
      onStyle: (st) => { drawW = st.w; drawFill = st.fill; },
    });
  }
  /* ★ 2026-10-04（Andy：「開啟四週期同看時，左側畫線工具列要整排反灰」）：四格小圖沒有掛繪圖層，
     工具列照舊亮著會讓人以為能畫、點了卻沒反應。四週期時整排 disabled＋aria-disabled（disabled 的按鈕點了不會觸發 onclick），
     CSS 反灰＋not-allowed 游標；切回單一週期恢復。 */
  function drawBarLock() {
    const bar = $('#drawBar'); if (!bar) return;
    const on = !!state.mtfMode;
    bar.classList.toggle('dt-locked', on);
    bar.setAttribute('aria-disabled', String(on));
    bar.title = on ? '四週期同看時不能畫線' : '';
    bar.querySelectorAll('button').forEach(b => { b.disabled = on; b.setAttribute('aria-disabled', String(on)); });
  }
  /* 四週期同看。
     Andy 2026-09-15：「同事看4個週期那頁需要新增可以切換週期，不然我看不到我要的」——
     以前四格是程式挑的（有 15 分就 15m/60m/240m/1d，沒有就取最後四個），使用者換不掉。
     現在每一格上面都有一個下拉選單，選什麼記在 `tw.kcfg` 的 mtfTfs 裡，換股票也還在。 */
  const MTF_LABEL = (tf) => ({ '5s': '5 秒（即時）', '1m': '1 分（即時）', '5m': '5 分（即時）',
    '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' })[tf] || tfLabel(tf);

  function mtfPick(pg) {
    const cfg = state.cfg || loadCfg();
    const saved = Array.isArray(cfg.mtfTfs) ? cfg.mtfTfs.filter(t => mtfTfList().indexOf(t) >= 0) : null;
    if (saved && saved.length === 4) return saved;
    const have = (tf) => barsFor(pg, tf).length >= 20;
    /* 自動挑的四格也只從「週期設置」勾起來的週期裡挑（2026-09-26 晚）：沒勾的週期不該自己冒出來。
       有 15 分資料而且 15 分有勾 → 最細的四個；否則取最粗的四個。一個都挑不到（例如只勾了即時週期）就直接用勾的前四個。*/
    const en = mtfTfList();
    const pref = ['15m', '60m', '240m', '1d', '1w', '1M'].filter(t => en.indexOf(t) >= 0).filter(have);
    let pick = pref.length >= 4 ? (pref[0] === '15m' ? pref.slice(0, 4) : pref.slice(-4)) : pref.slice();
    if (!pick.length) pick = en.slice(0, 4);
    while (pick.length < 4 && pick.length) pick.push(pick[pick.length - 1]);
    return pick;
  }

  function buildMtfGrid(pg) {
    const cfg = state.cfg || loadCfg();
    const pick = mtfPick(pg);
    const grid = $('#mtfGrid');
    const offDay = window.LiveK && window.LiveK.offDay ? window.LiveK.offDay() : null;
    const opts = (cur) => mtfTfList().map(tf =>
      `<option value="${tf}"${tf === cur ? ' selected' : ''}>${MTF_LABEL(tf)}</option>`).join('');
    grid.innerHTML = pick.map((tf, i) => {
      const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf];
      return `<div class="mtf-cell"><div class="cap">
        <select class="mtfsel" data-i="${i}" title="換這一格要看的週期">${opts(tf)}</select>
        ${t ? `<span style="color:${A.upDown(t.trend)}">${t.trend > 0 ? '多頭結構' : t.trend < 0 ? '空頭結構' : '盤整'}</span> · 均線${t.ma_align > 0 ? '多排' : t.ma_align < 0 ? '空排' : '糾結'}${t.rsi != null ? ' · RSI ' + t.rsi.toFixed(0) : ''}` : ''}
        </div><div class="mtip" id="mtip-${i}" hidden></div><div class="cv" id="mini-${i}"></div></div>`;
    }).join('');
    pick.forEach((tf, i) => {
      const el = $('#mini-' + i);
      /* ★ 2026-09-26（Andy：「四週期成交量呢？」）：每張小圖各自畫自己週期的成交量副圖（紅漲綠跌量柱＋量均線，
         圖高約 20%、軸標「張」），跟大圖同一份設定（miniCfg）—— 指標下拉把「成交量」關掉，四張一起不畫。
         量從哪來：日／週／月＝日線（週月是日線合成時把量加總）；1 小時＝payload 的 60 分 K；
         4 小時＝60 分 K 四根併一根（groupBars 把量加總）；即時週期＝livek.js 收的分 K。
         SMC 供需區與 BOS／CHoCH 標記同一天從小圖拿掉（Andy「將這兩個指標拿掉」）；
         標題列那行「多頭結構・均線多排・RSI」是判讀摘要，不是圖上的指標，照舊留著。*/
      const bars = barsFor(pg, tf);
      if (!bars || bars.length < 2) {
        const wait = isLiveTf(tf) && window.LiveK && window.LiveK.loading;
        el.innerHTML = `<div class="empty"${wait ? ' data-live="1"' : ''} style="height:100%">${A.fmt.esc(isLiveTf(tf) ? liveEmptyMsg(tf) : /m$/.test(tf) ? m60Why(pg) : '這個週期尚無資料')}</div>`;
        return;
      }
      // 非交易時段的 5 秒格沒收過就畫 1 分（livek.js 決定），游標時間要用分鐘格式
      const dtf = isLiveTf(tf) && window.LiveK && window.LiveK.drawnTf ? window.LiveK.drawnTf(tf) : tf;
      // 右下角「重設縮放」：每張小圖各一顆，重設的是這一張自己的縮放（四格可以各自滾輪縮放）
      const c = new KChart(el, { mini: true, tf: dtf, fit: (kc) => kc.defaultView() });
      c.setBars(bars, dtf);
      c.applyIndicators(miniCfg(cfg));
      /* 四週期小圖：游標看板（.mtip，兩行）蓋在圖的左上角，頂端同樣留兩行高，K 棒最高點不被蓋住 */
      if (c.reserveTop) requestAnimationFrame(() => c.reserveTop(38));
      /* 游標看板：滑過哪一根就寫那一根的時間、開高低收與量。小圖沒有大圖那條圖例，
         不寫的話量柱只有高低、看不出是幾張。*/
      const tip = $('#mtip-' + i);
      c.onCrosshair((k) => {
        const d = k == null ? null : c.data[k];
        if (!d || !tip) { if (tip) tip.hidden = true; return; }
        const prev = c.data[k - 1];
        const col = A.upDown(prev ? d.close - prev.close : d.close - d.open);
        tip.hidden = false;
        tip.innerHTML = `<b>${A.fmt.esc(KUtil.fmtTime(d.time, dtf))}</b>　開 ${A.fmt.n(d.open)} 高 ${A.fmt.n(d.high)} 低 ${A.fmt.n(d.low)} 收 <b style="color:${col}">${A.fmt.n(d.close)}</b>`
          + `<br>量 <b data-vol>${A.fmt.lot((d.volume || 0) / 1000)}</b>`;
      });
      miniCharts.push(c);
    });
    $$('.mtfsel', grid).forEach(sel => sel.onchange = () => {
      const next = mtfPick(pg).slice();
      next[+sel.dataset.i] = sel.value;
      cfg.mtfTfs = next; saveCfg(cfg); state.cfg = cfg;
      miniCharts.forEach(c => { try { c.destroy(); } catch (e) { /* 忽略 */ } });
      miniCharts = [];
      buildMtfGrid(pg);
    });
  }
  /* renderMtf（「多週期判讀」卡）2026-09-26 拿掉：合進 site/blocks/stock_ai.js 的「AI 分析」卡。
     支撐／壓力區、各週期多空都還在，搬到那張卡的技術面裡（只到週線，月線不列）。*/

  // ---------------------------------------------------------------- 個股分頁
  /* 分頁順序（2026-10-02 Andy，DECISIONS #294）：總覽、基本資料、指標、營收、獲利、除權息、法人、資券、大戶／散戶、公告／新聞。
     改前（09-28）「基本資料」排在倒數第二 —— 想先知道「這家公司做什麼」的人要越過七個財報籌碼分頁才找得到，
     所以搬到「總覽」旁邊。手機（mobile3.js SK_TABS）同一個順序。
     會員權限（features.js 的 stab）是用 data-t 對分頁鈕，不看位置 —— 換順序不影響 perm.js 的攔截。
     舊的「籌碼」分頁已拆掉；state.tab 若還停在 'chips'（同一個分頁開著時換版）就落到「法人」。*/
  /* ★ 2026-10-05（Andy，#stock/00947 台新臺灣IC設計）：ETF 個股頁拿掉不屬於 ETF 的分頁。
     判定：代號 00 開頭（ETF／ETN／受益證券；普通股不會 0 開頭 —— 與 pipeline/compute/etf.is_etf_code 同一條）。
     拿掉：基本資料（company_info 對 ETF 幾乎全空）、指標（條件多是營收／EPS）、營收、獲利。
     保留：總覽（技術訊號）、配息（＝除權息分頁）、法人、資券、受益人分布（集保對 ETF 有資料）、公告／新聞；
     新增：成分股。分頁鍵沿用個股的（dividend／holders…），features.js 的權限開關照樣吃得到。*/
  const isEtf = (code) => /^00/.test(String(code || ''));
  const ETF_TABS = [['overview', '總覽'], ['holdings', '成分股'], ['dividend', '配息'], ['inst', '法人'], ['margin', '資券'],
    ['holders', '受益人分布'], ['news', '公告 / 新聞']];
  const tabsFor = (code) => (isEtf(code) ? ETF_TABS : STOCK_TABS);
  /* 成分股：目前沒有可合法自動取得的來源（查證紀錄在 docs/etf_page_spec.md §成分股），誠實標示、不編造 */
  function tabHoldings(pg, el) {
    el.innerHTML = `<div class="card" id="etfHoldCard"><h3>成分股</h3><div class="empty" style="text-align:left;line-height:1.7">
      成分股以發行投信官網公告的每日持股為準</div></div>`;
  }
  const STOCK_TABS = [['overview', '總覽'], ['basics', '基本資料'], ['tags', '指標'], ['revenue', '營收'], ['profit', '獲利'], ['dividend', '除權息'],
    ['inst', '法人'], ['margin', '資券'], ['holders', '大戶／散戶'], ['news', '公告 / 新聞']];
  function renderTab(pg, tab) {
    const el = $('#stockTab');
    const T = { overview: tabOverview, holdings: tabHoldings, tags: tabTags, revenue: tabRevenue, profit: tabProfit, dividend: tabDividend,
      inst: tabInst, margin: tabMargin, holders: tabHolders, basics: tabBasics, news: tabNews };
    if (T[tab] && !tabsFor(pg.meta && pg.meta.code).some(t => t[0] === tab)) { tab = 'overview'; state.tab = tab; $$('#stockTabs button').forEach(x => x.classList.toggle('on', x.dataset.t === tab)); }
    if (!T[tab]) { tab = tab === 'chips' ? 'inst' : 'overview'; state.tab = tab; $$('#stockTabs button').forEach(x => x.classList.toggle('on', x.dataset.t === tab)); }
    delete el.dataset.chip;
    T[tab](pg, el);
    setTimeout(() => Object.values(A.charts).forEach(c => c && c.resize && c.resize()), 20);
  }
  /* ★ 2026-09-24 積木化第一梯次（docs/feature_modules.md §4 第 3 項）：
     「總覽」分頁以前是**一個 template literal 一次輸出三張卡**，🟡 與 🔴 綁在同一行字串裡。
     拆成三支，各自只讀自己要的欄位：
       · fundCard  —— 積木 `stock.fund` 的基本面卡（🟡，公開財報事實）
       · chipCard  —— 積木 `stock.fund` 的籌碼快照（🟡，法人與集保的公開數字）
       · 技術面訊號 —— 積木 `stock.signal`（🔴），搬到 site/blocks/stock_signal.js，
                      那支檔沒載入時這裡就只剩兩張卡，其他照常（原則三：能單獨關閉）。
     ⚠ 純重構：輸出字串跟拆之前一個字元都不差（逐頁像素比對 ＋ 全部個股頁逐檔比字串）。*/
  /* ★ 2026-09-25（Andy：「所有說明都拿掉，改成 ? 點擊後可觀看說明，文字只需要留名稱」）：個股頁每張卡的副標／圖下註腳
     一律搬進標題旁的「?」（跟總覽同一套 howPop：點背景、Esc、再按一次都會關）。
     `hq(key, title)` 產生那顆鈕；`hbox(key, items, fine)` 產生說明盒（條列 ≤5 條、每條 ≤30 字，_uitest「說明精簡」在量）。
     盒子要放在卡片裡（howPop 關的時候會把它搬回原位，驗收照 #how-<key> 找得到）。*/
  const hq = (key, title) => `<button class="howbtn pop" data-how="${key}" type="button" aria-label="${title}怎麼看">?</button>`;
  const hbox = (key, items, fine) => `<div class="howtxt" id="how-${key}" hidden>${A.howHTML('', items, fine)}</div>`;
  /* ★ 2026-09-29 設計 v4 第二批 2B（01 §4「圖例一律在繪圖區外」，改前→改後量測在 docs/design_v4/04_第二批2B.md）：
     個股頁的 ECharts 圖例（畫在圖表容器頂端、佔 30px 一行）改成卡片標題列裡的 HTML 圖例（.chlegend，
     跟資金流向頁 #instLegend 同一套樣式）。點 HTML 圖例送的是 ECharts 同一個 legendSelect／legendUnSelect；
     隱藏了哪幾條記在 extLegOff[圖 id]，重畫（切月／年、切區間、切分段）後補回去。
     **放得下才搬**：HTML 圖例放進標題列之後如果被擠到下一行（半寬卡片、窄視窗），多出來的那一行（≈30px）
     會把整張卡撐高、頁面變長 —— 那比改前差。所以量一次：
       · 跟標題列同一行 → ECharts 圖例收起來、繪圖區頂端 30 → o.top（10～12），容器高度不變，省下的高度全部給繪圖區；
       · 被擠到下一行 → HTML 圖例藏起來、ECharts 圖例照改前畫（o.fb），版面跟改前一模一樣。
       視窗寬度一變（debounce 200ms）重量一次，兩種狀態來回切，選取狀態兩邊同步（legendselectchanged）。
       · 色樣讀 ECharts 算好的系列顏色（getVisual('style')），不另寫色碼；長條＝方塊、折線＝細條。
       · o.dual[name]＝[正色, 負色]：逐根上色的長條（紅買綠賣、EPS 正負）畫成左右兩半，不讓人以為只有紅色。
       · o.labels[name]：圖例上顯示的字（例如把原本寫在 Y 軸上方的「EPS」單位併進圖例）。
     驗收：_uitest「設計v4第二批2B」。*/
  const extLegOff = {};
  const extLegRec = {};
  function extLegFit(r) {
    const c = r.c; if (!c || (c.isDisposed && c.isDisposed()) || !r.box.isConnected) return;
    r.box.hidden = false;
    const first = r.host.firstElementChild;
    const bb = r.box.getBoundingClientRect(), fb = first && first !== r.box ? first.getBoundingClientRect() : null;
    // 被擠到下一行＝圖例的頂端已經在同一列第一個東西的底下（留 2px 誤差）
    /* 手機（≤640）一律照改前畫（ECharts 圖例在圖裡）：這一批手機版面不動，而且 390 寬標題列加了標題圖示之後
       HTML 圖例一定被擠到下一行（驗收「標題圖示」390 個股／資券、大戶／散戶抓到標題列 44 → 84）。*/
    const wrapped = (window.innerWidth || 1440) <= 640 || !!(fb && bb.width > 0 && bb.top >= fb.bottom - 2);
    if (wrapped === r.wrapped) { r.box.hidden = wrapped; return; }
    r.wrapped = wrapped;
    r.box.hidden = wrapped;
    r.box.dataset.fit = wrapped ? 'wrap' : 'row';
    c.setOption(wrapped ? { legend: { show: true, ...r.fb }, grid: { top: r.fbTop }, ...(r.fbOpt || {}) }
      : { legend: { show: false }, grid: { top: r.top }, ...(r.okOpt || {}) });
  }
  let extLegT = null;
  window.addEventListener('resize', () => {
    clearTimeout(extLegT);
    extLegT = setTimeout(() => Object.values(extLegRec).forEach(r => { r.wrapped = null; extLegFit(r); }), 200);
  });
  function extLegend(c, host, opt) {
    if (!c || !host || !host.isConnected) return;
    const o = opt || {};
    /* 手機（≤640）不搬：這一批手機版面不動，DOM 要跟改前一模一樣（標題列裡連一個藏起來的圖例都不放）——
       只把 option 裡關掉的 ECharts 圖例照改前打開。驗收「標題圖示」390 抓到標題列在加了圖示之後變高（44 → 84）。*/
    if ((window.innerWidth || 1440) <= 640) {
      const id0 = c.getDom().id, old = document.querySelector(`.chlegend[data-for="${id0}"]`);
      if (old) old.remove();
      delete extLegRec[id0];
      c.setOption({ legend: { show: true, ...(o.fb || { top: 0, textStyle: { color: A.CH.ink2, fontSize: 12 } }) },
        grid: { top: o.fbTop != null ? o.fbTop : 30 }, ...(o.fbOpt || {}) });
      return;
    }
    const dom = c.getDom(); const id = dom.id;
    const op = c.getOption();
    const lg = (op.legend || [])[0] || {};
    const names = (lg.data && lg.data.length ? lg.data.map(d => (d && typeof d === 'object' ? d.name : d))
      : (op.series || []).map(s => s.name)).filter(n => n != null && n !== '').map(String);
    const m = c.getModel();
    const sw = (n) => { try { const s = m.getSeriesByName(n)[0]; if (!s) return {}; const st = s.getData().getVisual('style') || {};
      const line = s.subType === 'line'; return { line, col: line ? (st.stroke || st.fill) : (st.fill || st.stroke) }; } catch (e) { return {}; } };
    const off = (extLegOff[id] = extLegOff[id] || {});
    let box = document.querySelector(`.chlegend[data-for="${id}"]`);
    if (box && box.parentElement !== host) { box.remove(); box = null; }
    if (!box) {
      box = document.createElement('div'); box.className = 'chlegend skleg'; box.dataset.for = id;
      box.setAttribute('role', 'group'); box.setAttribute('aria-label', '圖例');
      host.appendChild(box);
    }
    const esc = A.fmt.esc;
    const paint = () => {
      box.innerHTML = names.map(n => {
        const v = sw(n); const lab = (o.labels && o.labels[n]) || n; const on = !off[n];
        const d = o.dual && o.dual[n];
        const bg = d ? `linear-gradient(90deg,${d[0]} 50%,${d[1]} 50%)` : (v.col || 'currentColor');
        return `<button type="button" data-n="${esc(n)}" aria-pressed="${on}" title="${esc(lab)}"><i class="${v.line ? 'ln' : ''}" style="background:${bg}"></i>${esc(lab)}</button>`;
      }).join('');
    };
    paint();
    names.forEach(n => { if (off[n]) c.dispatchAction({ type: 'legendUnSelect', name: n }); });
    box.onclick = (e) => {
      const b = e.target.closest('button[data-n]'); if (!b) return;
      const n = b.dataset.n;
      const ch = window.echarts && echarts.getInstanceByDom(document.getElementById(id));
      /* ★ 收尾修正：先記自己的狀態再送 action。ECharts 對 legendSelect／legendUnSelect 發的事件是
         legendselected／legendunselected，**不是** legendselectchanged（那個只有 legendToggleSelect 會發）——
         以前只聽 legendselectchanged，點 HTML 圖例之後 off 永遠沒寫進去：按鈕的 aria-pressed 不變、
         切 12／24 月重畫之後藏起來的那條又跑回來（驗收 ①「切 24 月重畫之後 YoY 仍然藏著」抓到）。*/
      off[n] = !off[n]; paint();
      if (ch) ch.dispatchAction({ type: off[n] ? 'legendUnSelect' : 'legendSelect', name: n });
    };
    // 兩種狀態共用 ECharts 的選取：不管點的是 HTML 圖例還是（放不下時的）ECharts 圖例，都從這裡同步回來
    ['legendselectchanged', 'legendselected', 'legendunselected'].forEach(t => c.off(t, c._extLegSync));
    c._extLegSync = (ev) => { Object.entries(ev.selected || {}).forEach(([k, v]) => { off[k] = v === false; }); paint(); };
    ['legendselectchanged', 'legendselected', 'legendunselected'].forEach(t => c.on(t, c._extLegSync));
    const r = extLegRec[id] = { c, host, box, top: o.top != null ? o.top : 10, fbTop: o.fbTop != null ? o.fbTop : 30,
      fb: o.fb || { top: 0, textStyle: { color: A.CH.ink2, fontSize: 12 } }, fbOpt: o.fbOpt, okOpt: o.okOpt, wrapped: null };
    // 圖剛畫出來是「HTML 圖例版」（option 裡 legend.show:false、grid.top 小）；量完放不下才退回改前的畫法
    r.wrapped = false;
    box.dataset.fit = 'row';      // 初始就是「同一行」版；extLegFit 只在狀態改變時才寫，不先寫的話放得下的圖永遠讀不到 row
    extLegFit(r);
    /* 標題列的寬度分配在圖畫完之後還會變（標題圖示、「?」、資料日期這些是之後才補進標題的）——
       只在視窗縮放時重量的話，圖例量的時候放得下、補完標題之後就被擠到下一行，卡片多出一行。
       所以盯著標題列本身的尺寸：一變就重量（狀態沒變時 extLegFit 什麼都不做，不會來回切）。*/
    if (!host._extRO && typeof ResizeObserver !== 'undefined') {
      host._extRO = new ResizeObserver(() => Object.values(extLegRec).forEach(x => { if (x.host === host) extLegFit(x); }));
      host._extRO.observe(host);
    }
  }
  const extLegendDrop = (id) => { const b = document.querySelector(`.chlegend[data-for="${id}"]`); if (b) b.remove(); delete extLegRec[id]; };
  /* ==========================================================================
     ★ 2026-10-03（Andy：「基本面卡：純數字小格、有圖表的大格並補充詳細；本益比這邊的算法需要新增到獲利那邊」，DECISIONS #305）
     本益比位置（peStand）：**目前本益比落在這一檔自己過去每天本益比的第幾百分位**，總覽基本面卡與「獲利」分頁共用這一支，數字一定一致。
       · 樣本＝peRiver(pg) 那一條逐日本益比（每天收盤 ÷ 當時最新的近四季 EPS，財報可用日起算、虧損季不算），
         跟獲利分頁的本益比河流圖是同一條 —— 河流圖的五條倍數線就是這條的 10／30／50／70／90 分位。
       · 便宜端＝第 10 百分位、貴端＝第 90 百分位、中位＝第 50 百分位（同河流圖最下、最上那兩條帶的界線）。
       · 目前＝fundamental.pe（收盤 ÷ 近四季 EPS，卡片上那個大數字），分位＝樣本裡比它低的比例（相等的算一半）。
       · 族群中位（fundamental.group_median）也換算成它在這一檔歷史裡的分位，畫成菱形 —— 一眼看出「族群現在給的倍數，
         放在這一檔自己的歷史裡算貴還是便宜」。同業分位（族群內估值比它低的比例）照舊寫在下面一行。
       · 為什麼條是「分位」刻度而不是本益比數值刻度：3105 那種 TTM 很小的季會衝到 500 倍（#303），數值刻度會把其他 95% 的日子壓成一個點；
         分位刻度永遠是 0～100，極端值只佔最右邊那一小段。刻度上的數字（便宜／中位／貴）才是本益比倍數。
       · 樣本不到 60 個交易日（peRiver 回 null）→ 不畫歷史位置，退回「同業位置」那條舊刻度；目前本益比沒有（虧損）→ 只寫一句虧損。
     ========================================================================== */
  function peStand(pg) {
    const f = pg.fundamental || {};
    const cur = f.pe != null && isFinite(f.pe) && f.pe > 0 ? +f.pe : null;
    const gmed = f.group_median != null && isFinite(f.group_median) && f.group_median > 0 ? +f.group_median : null;
    const peer = f.percentile != null && isFinite(f.percentile) ? Math.max(0, Math.min(100, +f.percentile)) : null;
    const base = { cur, gmed, peer, gname: f.group_name || '', gn: f.group_n || null, thin: !!f.thin_sample, loss: !!f.is_loss || cur == null };
    const r = peRiver(pg);
    if (!r || cur == null) return { ...base, ok: false };
    const pes = r.dates.map((d, i) => r.close[i] / r.eps[i]).filter(v => isFinite(v) && v > 0);
    if (pes.length < 60) return { ...base, ok: false };
    const s = pes.slice().sort((a, b) => a - b), n = s.length;
    const q = (p) => { const i = (n - 1) * p, lo = Math.floor(i), hi = Math.ceil(i); return s[lo] + (s[hi] - s[lo]) * (i - lo); };
    const rank = (x) => { let lt = 0, eq = 0; for (const v of s) { if (v < x) lt++; else if (v === x) eq++; } return (lt + eq / 2) / n * 100; };
    const from = r.dates[0], to = r.dates[r.dates.length - 1];
    const yrs = (Date.parse(to) - Date.parse(from)) / (365.25 * 864e5);
    const span = yrs >= 1 ? `近 ${yrs.toFixed(1)} 年` : `近 ${Math.max(1, Math.round(yrs * 12))} 個月`;
    const r1 = (v) => Math.round(v * 10) / 10;
    return { ...base, ok: true, n, from, to, span, lo: r1(s[0]), hi: r1(s[n - 1]), p10: r1(q(0.1)), p50: r1(q(0.5)), p90: r1(q(0.9)),
      pct: Math.round(rank(cur) * 10) / 10, gpct: gmed != null ? Math.round(rank(gmed) * 10) / 10 : null };
  }
  /* 本益比位置那一塊的 HTML（id 由呼叫端給：總覽 #peStandOv、獲利 #peStandProf）。data-* 帶原始數字，兩邊對帳用。*/
  function peStandHTML(m, id) {
    const n1 = (v) => A.fmt.n(v, 1), esc = A.fmt.esc;
    if (!m.ok) {
      if (m.cur == null) return `<div class="pestand" id="${id}" data-ok="0">${m.loss ? '<div class="psnote">近四季 EPS ≤ 0（虧損），不計本益比</div>' : ''}</div>`;
      // 歷史樣本不夠 → 退回同業位置刻度（左＝族群最便宜、右＝最貴，中線＝中位）
      if (m.peer == null) return `<div class="pestand" id="${id}" data-ok="0"></div>`;
      return `<div class="pestand" id="${id}" data-ok="0" data-peer="${m.peer.toFixed(1)}"><div class="pescale" style="--p:${m.peer.toFixed(1)}%" role="img" aria-label="同族群本益比分位 ${A.fmt.n(m.peer, 0)}%（越右越貴）"><i class="pemid"></i><b class="pedot"></b></div>`
        + `<div class="minil"><span>族群便宜</span><span class="pep" data-pct="${m.peer.toFixed(1)}">同業分位 ${A.fmt.n(m.peer, 0)}%${m.thin ? '*' : ''}</span><span>族群貴</span></div>`
        + `<div class="psnote">歷史本益比不足 60 個交易日，改看同族群（${esc(m.gname || '—')}，${m.gn || '—'} 檔）位置</div></div>`;
    }
    const zone = m.pct < 10 ? '低於便宜端' : m.pct > 90 ? '高於貴端' : m.pct < 50 ? '中位以下' : '中位以上';
    const aria = `目前本益比 ${n1(m.cur)} 倍，在${m.span}每日本益比的第 ${A.fmt.n(m.pct, 0)} 百分位；便宜端 ${n1(m.p10)} 倍、中位 ${n1(m.p50)} 倍、貴端 ${n1(m.p90)} 倍`;
    return `<div class="pestand" id="${id}" data-ok="1" data-pct="${m.pct}" data-cur="${m.cur}" data-p10="${m.p10}" data-p50="${m.p50}" data-p90="${m.p90}" data-lo="${m.lo}" data-hi="${m.hi}" data-n="${m.n}"`
      + `${m.gmed != null ? ` data-gmed="${m.gmed}" data-gpct="${m.gpct}"` : ''}${m.peer != null ? ` data-peer="${m.peer.toFixed(1)}"` : ''}>`
      + `<div class="psbar" role="img" aria-label="${esc(aria)}"><i class="pst" style="left:10%"></i><i class="pst pmid" style="left:50%"></i><i class="pst" style="left:90%"></i>`
      + `${m.gpct != null ? `<b class="psgm" style="left:${m.gpct}%" title="族群中位 ${n1(m.gmed)} 倍＝這一檔歷史的第 ${A.fmt.n(m.gpct, 0)} 百分位"></b>` : ''}`
      + `<b class="psdot" style="left:${m.pct}%" title="目前 ${n1(m.cur)} 倍＝第 ${A.fmt.n(m.pct, 0)} 百分位"></b></div>`
      + `<div class="pslab"><span>便宜 <b>${n1(m.p10)}</b></span><span>中位 <b>${n1(m.p50)}</b></span><span>貴 <b>${n1(m.p90)}</b></span></div>`
      + `<div class="psnote">目前 <b>${n1(m.cur)}</b> 倍＝${m.span}本益比第 <b class="pspct">${A.fmt.n(m.pct, 0)}</b> 百分位（${zone}；區間 ${n1(m.lo)}～${n1(m.hi)} 倍）</div>`
      + `${m.gmed != null ? `<div class="psnote"><i class="psgmk" aria-hidden="true"></i>族群中位 <b>${n1(m.gmed)}</b> 倍（${esc(m.gname || '—')} ${m.gn || '—'} 檔）${m.peer != null ? `・同業分位 ${A.fmt.n(m.peer, 0)}%${m.thin ? '*' : ''}` : ''}</div>` : ''}`
      + `</div>`;
  }
  /* 毛利率：最新一季（財報到那一季）、前一季、去年同季，與近 8 季小趨勢。季別照 profit.quarters 的順序（管線把缺的季補成空列，往前數 1／4 列就是前一季／去年同季）*/
  function gmTrend(pg) {
    const q = (pg.profit || {}).quarters || [];
    const f = pg.fundamental || {};
    let i = f.latest_period ? q.findIndex(r => r && r[0] === f.latest_period) : -1;
    if (i < 0) for (let j = q.length - 1; j >= 0; j--) if (q[j] && q[j][2] != null) { i = j; break; }
    if (i < 0 || q[i][2] == null) return null;
    const at = (k) => (k >= 0 && q[k] && q[k][2] != null ? { p: q[k][0], v: +q[k][2] } : null);
    const ser = q.slice(Math.max(0, i - 7), i + 1).map(r => ({ p: r[0], v: r[2] != null ? +r[2] : null }));
    return { cur: at(i), prev: at(i - 1), ly: at(i - 4), ser };
  }
  /* 營運動能的組成：照管線 fundamental.momentum_score 的公式逐項算（起始 50；月營收 YoY 夾在 −40～60 乘 0.5；連續年增月數最多 12 乘 1.5；
     創新高 +6；MoM 比歷年同月中位的差夾在 ±20 乘 0.3；YoY > 100% 扣 8；總分夾在 0～100）。⚠ 管線改公式這裡要跟著改（_uitest 會比總分）。
     缺資料的那一項不列（例如 MoM 沒有 3 年同月可比）。*/
  function momParts(f) {
    if (f.momentum_score == null || !isFinite(f.momentum_score)) return null;
    const clip = (v, a, b) => Math.max(a, Math.min(b, v));
    const sg = (v) => (v > 0 ? '+' : v < 0 ? '−' : '±') + A.fmt.n(Math.abs(v), 1);
    const P = [];
    if (f.rev_yoy != null && isFinite(f.rev_yoy)) P.push({ k: 'yoy', l: `月營收 YoY${f.rev_yoy_note ? '（' + f.rev_yoy_note + '）' : ''}`, v: A.fmt.pct(f.rev_yoy), pts: clip(+f.rev_yoy, -40, 60) * 0.5 });
    if (f.rev_streak != null) P.push({ k: 'streak', l: '連續年增', v: `${f.rev_streak} 個月`, pts: Math.min(+f.rev_streak, 12) * 1.5 });
    if (f.rev_record_high != null) P.push({ k: 'high', l: '營收創新高', v: f.rev_record_high ? '是' : '否', pts: f.rev_record_high ? 6 : 0 });
    if (f.rev_mom_vs_typical != null && isFinite(f.rev_mom_vs_typical)) P.push({ k: 'mom', l: 'MoM 比歷年同月', v: (f.rev_mom_vs_typical > 0 ? '+' : '') + A.fmt.n(f.rev_mom_vs_typical, 1) + 'pp', pts: clip(+f.rev_mom_vs_typical, -20, 20) * 0.3 });
    if (f.rev_flag_spike) P.push({ k: 'spike', l: 'YoY 超過 100%（一次性？）', v: '是', pts: -8 });
    const raw = 50 + P.reduce((a, x) => a + x.pts, 0);
    return { parts: P.map(x => ({ ...x, txt: sg(x.pts) })), raw, score: clip(raw, 0, 100) };
  }
  /* 近 8 季毛利率小趨勢：SVG 只畫線與點（沒有字 —— SVG 的字會跟著縮放，手機量不準 11px），頭尾季別寫在 HTML */
  function gmSpark(ser) {
    /* ★ 2026-10-05（Andy：「走勢圖太單調」）：補上每季的點、最高／最低季數值、近 8 季平均淡虛線、淡面積與中間季別刻度。
       線、面積、平均線放 SVG（non-scaling-stroke）；點與數字一律用 HTML 疊上去 —— SVG 字會被 preserveAspectRatio=none 拉變形、手機也量不準 11px。
       滑過每點用 title 顯示「季別 毛利率」，不另掛 tooltip 元件，卡片高度只多 12px。 */
    const pts = ser.map((x, i) => [i, x.v]).filter(x => x[1] != null);
    if (pts.length < 4) return '';
    const vs = pts.map(x => x[1]), lo = Math.min(...vs), hi = Math.max(...vs), pad = Math.max(0.5, (hi - lo) * 0.15);
    const avg = vs.reduce((a, b) => a + b, 0) / vs.length, H = 44, T = 13, B = 30;
    const X = (i) => (ser.length > 1 ? i / (ser.length - 1) * 92 + 4 : 50), Y = (v) => B - (v - (lo - pad)) / ((hi + pad) - (lo - pad)) * (B - T);
    const d = pts.map((p, k) => `${k ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ');
    const area = `${d} L${X(pts[pts.length - 1][0]).toFixed(1)} ${H} L${X(pts[0][0]).toFixed(1)} ${H} Z`;
    const iHi = pts.find(p => p[1] === hi)[0], iLo = pts.find(p => p[1] === lo)[0], L = pts[pts.length - 1];
    const pct = (y) => (y / H * 100).toFixed(1);
    const dots = pts.map(p => `<i class="gmp${p === L ? ' gmd' : ''}" style="left:${X(p[0]).toFixed(1)}%;top:${pct(Y(p[1]))}%" title="${A.fmt.esc(ser[p[0]].p)} 毛利率 ${A.fmt.n(p[1], 1)}%" data-q="${A.fmt.esc(ser[p[0]].p)}"></i>`).join('');
    // 最高放點的正上方（上緣留了 13px）；最低放點的正下方（下緣留 14px，放側邊會壓到線、放更低會壓到季別刻度 —— 2026-10-05 截圖實測）
    const lab = (i, v, cls) => { const x = X(i);
      const tf = cls === 'hi' ? `${x < 15 ? 'translateX(-4px)' : x > 85 ? 'translateX(calc(-100% + 4px))' : 'translateX(-50%)'} translateY(calc(-100% - 4px))`
        : `${x < 15 ? 'translateX(-4px)' : x > 85 ? 'translateX(calc(-100% + 4px))' : 'translateX(-50%)'} translateY(4px)`;
      return `<b class="gmv ${cls}" style="left:${x.toFixed(1)}%;top:${pct(Y(v))}%;transform:${tf}">${A.fmt.n(v, 1)}%</b>`; };
    const mid = Math.floor((ser.length - 1) / 2);
    return `<div class="gmspark"><div class="gmsv"><svg viewBox="0 0 100 ${H}" preserveAspectRatio="none" role="img" aria-label="近 ${ser.length} 季毛利率：${pts.map(p => ser[p[0]].p + ' ' + A.fmt.n(p[1], 1) + '%').join('、')}；平均 ${A.fmt.n(avg, 1)}%" data-n="${pts.length}">`
      + `<path d="${area}" class="gma"/><line x1="0" x2="100" y1="${Y(avg).toFixed(1)}" y2="${Y(avg).toFixed(1)}" class="gmavg" vector-effect="non-scaling-stroke"/>`
      + `<path d="${d}" class="gml" vector-effect="non-scaling-stroke"/></svg>${dots}${lab(iHi, hi, 'hi')}${iLo !== iHi ? lab(iLo, lo, 'lo') : ''}</div>`
      + `<div class="minil"><span>${A.fmt.esc(ser[0].p)}</span><span>${A.fmt.esc(ser[mid].p)}</span><span class="gmavgl">平均 ${A.fmt.n(avg, 1)}%</span><span>${A.fmt.esc(ser[ser.length - 1].p)}</span></div></div>`;
  }
  function fundCard(pg) {
    const f = pg.fundamental || {}, dv = pg.dividends || {};
    /* ★ 2026-09-28（Andy：「總覽 基本面 也需要新增 "?" 說明」）：逐欄一句話（≤30 字），口徑照管線。
       ★ 2026-10-02（DECISIONS #294）：能用小圖的用小圖（營運動能半圓儀表、本益比刻度、毛利率進度條）。
       ★ 2026-10-03（Andy，DECISIONS #305）：改前 7 格等大方塊（每格約 190×120px，數字只佔一角），Andy：「純數字的格子做成小格，
         縱向堆在一窄欄；有圖表的格子做成大格放旁邊，有圖表的需要補充詳細點」「其他文字框需要調整適當版面，空白太多了」。
         · 小格（窄欄，由上往下）：近四季 EPS、ROE、月營收 YoY、殖利率 —— 數字＋一行有資料才寫的小字
         · 大格（寬欄）：本益比位置（peStand，跟「獲利」分頁共用）、毛利率（前一季／去年同季增減＋近 8 季小趨勢）、營運動能（儀表＋組成分數）
         · 兩欄底部對齊：小格平均分掉窄欄高度（內容垂直置中）、大格依內容；卡片寬 < 360px（手機）改成小格 2×2 在上、大格在下。
         資料不足的子項整行不出現（不寫「資料不足」）。*/
    const help = hbox('skfund', [
      // ★ 2026-10-04（稽核第 11 項）：改前 8 條超過 5 條上限，且卡上的「股價淨值比」沒有說明 —— 兩兩合併、補上淨值比
      'EPS＝近四季相加；ROE＝近四季淨利 ÷ 權益',
      '本益比條：◆族群中位；自己第 10／90 百分位＝便宜／貴',
      '毛利率＝最新季毛利 ÷ 營收；營收 YoY 比去年同月',
      '營運動能＝營收成長各項加分，0～100',
      '殖利率＝近四次現金 ÷ 股價；淨值比＝股價 ÷ 每股淨值']);
    const q = (pg.profit || {}).quarters || [];
    const qi = f.latest_period ? q.findIndex(r => r && r[0] === f.latest_period) : -1;
    const sub = (t) => (t ? `<div class="s">${t}</div>` : '');
    const ks = (key, l, v, s2, cls) => `<div class="k ksm" data-f="${key}"><div class="l">${l}</div><div class="v ${cls || ''}">${v}</div>${sub(s2)}</div>`;
    const kb = (key, l, v, body, cls) => `<div class="k kbig" data-f="${key}"><div class="kh"><span class="l">${l}</span><span class="v ${cls || ''}">${v}</span></div>${body || ''}</div>`;
    // 小格的小字：有資料才寫
    const epsQ = qi >= 0 && q[qi][5] != null ? `單季 ${A.fmt.esc(q[qi][0])} ${A.fmt.n(q[qi][5])} 元` : '';
    const pbT = f.pb != null && isFinite(f.pb) ? `股價淨值比 ${A.fmt.n(f.pb, 1)} 倍` : '';
    const yoyT = f.rev_ym ? `${A.fmt.esc(f.rev_ym)}${f.rev_yoy_note ? '（' + A.fmt.esc(f.rev_yoy_note) + '）' : ''}${f.rev_yoy_3m != null && isFinite(f.rev_yoy_3m) ? `・近 3 月 ${A.fmt.pct(f.rev_yoy_3m)}` : ''}` : '';
    /* 月營收 YoY 小基期會到 +41,420%（1438 實測）：窄欄只有約 80px，≥1000% 改成整數加千分位（「+41,421%」），不帶小數 */
    const yoyV = f.rev_yoy != null && isFinite(f.rev_yoy) && Math.abs(f.rev_yoy) >= 1000 ? (f.rev_yoy > 0 ? '+' : '−') + A.fmt.i(Math.round(Math.abs(f.rev_yoy))) + '%' : A.fmt.pct(f.rev_yoy);
    const dvT = dv.cash_ttm != null && dv.cash_ttm > 0 ? `近四次現金 ${A.fmt.n(dv.cash_ttm)} 元` : '';
    // 大格 ①：本益比位置
    const ps = peStand(pg);
    // 大格 ②：毛利率
    const gm = f.gross_margin != null && isFinite(f.gross_margin) ? Math.max(0, Math.min(100, +f.gross_margin)) : null;
    const gt = gmTrend(pg);
    const dpp = (a, b) => { const d = a - b; return `<b class="${d > 0 ? 'up' : d < 0 ? 'down' : ''}">${d > 0 ? '▲ +' : d < 0 ? '▼ −' : '± '}${A.fmt.n(Math.abs(d), 1)}pp</b>`; };
    let gmBody = '';
    if (gm != null) {
      gmBody = `<div class="meter" style="--p:${gm.toFixed(1)}%;--c:var(--cyan)" role="img" aria-label="毛利率 ${A.fmt.n(gm, 1)}%（0～100%）"><i></i>${gt && gt.ly ? `<b class="tick" style="left:${Math.max(0, Math.min(100, gt.ly.v)).toFixed(1)}%" title="去年同季 ${A.fmt.n(gt.ly.v, 1)}%"></b>` : ''}</div>`;
      const rows = [];
      if (gt && gt.prev) rows.push(`<div class="gmr" data-k="prev" data-v="${gt.prev.v}"><span>前一季 ${A.fmt.esc(gt.prev.p)}</span><span>${A.fmt.n(gt.prev.v, 1)}%</span>${dpp(gm, gt.prev.v)}</div>`);
      if (gt && gt.ly) rows.push(`<div class="gmr" data-k="ly" data-v="${gt.ly.v}"><span>去年同季 ${A.fmt.esc(gt.ly.p)}</span><span>${A.fmt.n(gt.ly.v, 1)}%</span>${dpp(gm, gt.ly.v)}</div>`);
      gmBody += (rows.length ? `<div class="gmrs">${rows.join('')}</div>` : '') + (gt ? gmSpark(gt.ser) : '');
    }
    // 大格 ③：營運動能
    const mp = momParts(f);
    const ms = mp ? Math.max(0, Math.min(100, +f.momentum_score)) : null;
    const arc = 'M6 32 A26 26 0 0 1 58 32';
    let momV = '—', momBody = '';
    if (ms != null) {
      /* 半圓儀表放在標題列（分數旁），組成分數用整格寬列在下面 —— 儀表放左邊的話，右邊只剩約 170px，「MoM 比歷年同月」那一列會被截掉 */
      momV = `<span class="gaugev"><svg class="gauge" viewBox="0 0 64 36" width="48" height="27" role="img" aria-label="營運動能 ${A.fmt.n(ms, 0)} 分（滿分 100）" data-score="${ms.toFixed(1)}">`
        + `<path d="${arc}" pathLength="100" class="gtrack"/><path d="${arc}" pathLength="100" class="gfill" stroke-dasharray="${ms.toFixed(1)} 100"/></svg>`
        + `<span>${A.fmt.n(ms, 0)}<small> / 100</small></span></span>`;
      momBody = `<div class="momw"><div class="momps" data-raw="${mp.raw.toFixed(2)}"><div class="mpr base"><span>起始分</span><span></span><b>50</b></div>`
        + mp.parts.map(x => `<div class="mpr" data-k="${x.k}" data-pts="${x.pts.toFixed(2)}"><span>${A.fmt.esc(x.l)}</span><span>${x.v}</span><b class="${x.pts > 0 ? 'up' : x.pts < 0 ? 'down' : ''}">${x.txt}</b></div>`).join('')
        + `${mp.raw > 100 || mp.raw < 0 ? `<div class="mpr cap"><span>加總 ${A.fmt.n(mp.raw, 1)}，夾在 0～100</span><span></span><b>${A.fmt.n(ms, 0)}</b></div>` : ''}</div></div>`;
    }
    /* 2026-10-06：標題列右側加一行免責（動能分是評分、本益比條有便宜／貴）—— h3 包進 .row.spread 才有「右側」可放 */
    return `<div class="card" id="skFundCard"><div class="row spread"><h3>基本面 ${hq('skfund', '基本面')}</h3>${A.disc ? A.disc('fund') : ''}</div>${help}<div class="kvs skfund" style="margin-top:8px">`
      + `<div class="fsm">`
      + ks('eps', '近四季 EPS', f.ttm_eps != null ? A.fmt.n(f.ttm_eps) : '—', epsQ)
      + ks('roe', 'ROE', f.roe != null ? A.fmt.n(f.roe, 1) + '%' : '—', pbT)
      + ks('yoy', '月營收 YoY', yoyV, yoyT, A.fmt.cls(f.rev_yoy))
      + ks('yld', '殖利率（近四次）', dv.yield_ttm != null ? A.fmt.n(dv.yield_ttm) + '%' : '—', dvT)
      + `</div><div class="fbig">`
      + kb('pe', '本益比', ps.cur != null ? A.fmt.n(ps.cur, 1) + ' <small>倍</small>' : '—', peStandHTML(ps, 'peStandOv'))
      + kb('gm', '毛利率', gm != null ? A.fmt.n(gm, 1) + '%' : '—', gmBody)
      + kb('mom', '營運動能', momV, momBody)
      + `</div></div><div class="note" style="margin-top:8px">${f.group_name ? `同族群（${f.group_name}，n=${f.group_n}）本益比中位 ${f.group_median != null ? A.fmt.n(f.group_median, 1) : '—'}${f.vs_median != null ? (Math.abs(f.vs_median) < 0.5 ? '，本檔與中位相當' : '，本檔 ' + (f.vs_median > 0 ? '高於' : '低於') + '中位 ' + A.fmt.n(Math.abs(f.vs_median), 0) + '%') : ''}` : '本益比只在同族群內比較'}</div></div>`;
  }
  /* ★ 2026-09-28（Andy：「總覽 籌碼快照『?』欄位說明，並移除 大戶4週 與 散戶」）：
     · 拿掉「大戶 4 週變化」「散戶（≤10 張）」兩格。千張大戶的週變化在「籌碼」分頁的集保圖有完整走勢，
       散戶比例的口徑（集保 1–3 級）又跟券商 App 對不起來（DECISIONS #268「散戶口徑不跟 App」），擺在快照裡只會招來誤讀。
     · 每一格名稱旁一顆小「?」，點了跳出**那一格**的定義與怎麼用（同一套 howPop：點背景／Esc／再按一次都會關）。
       以前只有標題那顆「?」，而且它列的正好是被拿掉的兩格，剩下的外資、投信、融資、量比都沒講。
     · 說明格式照「說明精簡」：每格 2 條、每條 ≤30 字、不附註。*/
  /* ★ 2026-10-02（Andy 五張截圖之一、DECISIONS #294）：籌碼快照從「六格數字」改成三張比例小圖＋量比一條。
     樣式照總覽「資金去向」摘要卡：上面一條分段色條、下面圖例＋數值。每一張只回答一個問題：
       ① 法人近 20 日：外資、投信、自營商誰在買、誰在賣、各佔多少？
          比重＝各自買賣超張數的絕對值 ÷ 三者絕對值合計（買超與賣超都算「動作的份量」）。
          色條分成兩段：左邊實色＝買超、中間一道分隔、右邊斜紋淡色＝賣超；顏色跟著法人走（外資青、投信琥珀、自營紫，
          跟資金流向頁「族群 × 法人」同一組），不跟著正負走 —— 紅綠在本站是漲跌，拿來分法人會跟「買賣超」打架。
          色條右上寫合計（＝改前「法人 20 日」那一格的數字，所以那一格拿掉不會少資訊）。
       ② 集保持股分布：≥1,000 張、400～1,000 張、≤10 張各佔總股數幾成（中間 10～400 張畫成灰色「其他」，色條才是 100%），
          每一段附近 4 週變化（pp）。⚠ 這裡寫「≤10 張」不寫「散戶」：本站散戶口徑（集保 1–3 級）跟券商 App 不同（#268），
          09-28 拿掉「散戶」那格就是因為這個字招誤讀；Andy 10-02 要求把 ≤10 張加回來，用級距名稱就不會被拿去跟 App 比。
       ③ 信用與借券（單位一律「張」，標日期）：融資餘額、融券餘額、借券賣出餘額三段（都是「餘額」才放同一條色條），
          當沖另起一條進度條＝當沖率（當沖張數 ÷ 成交張數，%）—— 當沖是當天的成交量、不是餘額，跟前三個放進同一條比例會誤導。
          數字跟「資券」分頁最上面那一列同一支 mgLatest() 算，兩邊永遠一致（#294 對帳）。
     資料不夠的那一張寫一句「資料準備中」，不畫空色條。*/
  const CHIP_HELP = {
    inst:   ['法人近 20 日', ['比重＝各自買賣超張數 ÷ 三者絕對值合計', '實色＝買超、斜紋淡色＝賣超；右上是合計']],
    hold:   ['集保持股分布', ['各級距持股佔總股數的比例（每週公布）', 'N 週＝近 N 週變化（最多 4 週），單位 pp']],
    credit: ['信用與借券', ['融資、融券、借券賣出都是「餘額」，單位張', '融資多＝信用追價；券＋借券多＝放空部位']],
    dt:     ['當沖率', ['當沖成交張數 ÷ 當日成交張數', '當沖率高＝短線客多，價格容易暴漲暴跌']],
    volr:   ['量比', ['今日成交量 ÷ 近 20 日平均量（含今日）', '≥1.5 算爆量；帶量突破比無量突破可信']],
  };
  const MIX_C = { f: 'var(--cyan)', t: 'var(--amber)', d: 'var(--violet)', big: 'var(--cyan)', mid: 'var(--amber)', ret: 'var(--violet)',
    rest: 'color-mix(in srgb,var(--ink-3) 45%,transparent)', mb: 'var(--cyan)', sb: 'var(--amber)', sbl: 'var(--violet)' };
  const md5 = (d) => String(d || '').slice(5, 10);
  /* 小圖標題列的「?」：data-ttl 給彈窗標題（這顆鈕不在 h3 裡，howPop 讀不到標題）*/
  const mixQ = (key) => { const [l, items] = CHIP_HELP[key];
    return `<button class="howbtn pop kq" data-how="skc-${key}" data-ttl="${l}" type="button" aria-label="${l}是什麼">?</button>${hbox('skc-' + key, items)}`; };
  /* 一條分段色條：segs＝[{k, v(>0 才畫), lab, sell?}]，'|' ＝買超／賣超之間的分隔 */
  const mixBar = (segs, aria) => `<div class="mixbar" role="img" aria-label="${A.fmt.esc(aria)}">${segs.map(s => s === '|' ? '<b class="mixsep" aria-hidden="true"></b>'
    : (s.v > 0 ? `<i data-k="${s.k}"${s.sell ? ' class="sell"' : ''} style="flex-grow:${s.v};--c:${MIX_C[s.k]}" title="${A.fmt.esc(s.lab)}"></i>` : '')).join('')}</div>`;
  /* 圖例格三行：色塊＋名稱／數值／小字（比重或 4 週變化、資料日）。比重不跟名稱擠同一行：
     390 寬一格只有約 95px，「借券賣出餘額 15.6%」放一行會被省略號切掉（_uitest「個股總覽1002」量到過）。*/
  const mixItem = (k, label, pct, val, cls, extra) => { const e = extra || {};
    // 每一小段各自不斷行（「資料日 09-24」不會被拆成「09-」「24」兩行），要換行只在「・」之間換
    const sub = [pct != null ? `${e.pre || '佔'} ${pct}` : '', e.sub || ''].filter(Boolean).map(x => `<span class="nw">${x}</span>`).join('・');
    return `<div class="mixi${e.sell ? ' sell' : ''}" data-k="${k}"${e.attrs || ''} style="--c:${MIX_C[k]}">`
      + `<small>${label}</small><b class="${cls || ''}">${val}</b>${sub ? `<span class="mixsub">${sub}</span>` : ''}</div>`; };
  /* ★ 2026-10-06（Andy：「這類資訊一律拿掉」，DECISIONS #329）：小圖標題列的日期（.mixd「09-03～10-02」「09-24」「10-02」）拿掉；
     dateTxt 參數留著不用（呼叫端三處不必改）。*/
  const mixBox = (key, dateTxt, sumTxt, body) => `<div class="mix" data-mix="${key}"><div class="mixh"><span class="mixt">${CHIP_HELP[key][0]}</span>${mixQ(key)}`
    + `${sumTxt ? `<span class="mixs">${sumTxt}</span>` : ''}</div>${body}</div>`;
  const signLot = (v) => (v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + A.fmt.i(Math.abs(v)) + ' 張');
  const pp = (v) => (v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toFixed(2) + 'pp');

  /* 法人近 20 日（張）：跟管線 inst_v3.sum20／foreign20／trust20 同一個窗（最後 20 列），自營商＝那 20 列的 dealer 加總 */
  function instMix(pg) {
    const rows = ((pg.inst_v3 || {}).daily || []).filter(r => r && (r[1] != null || r[2] != null || r[3] != null)).slice(-20);
    if (!rows.length) return null;
    const sum = (i) => rows.reduce((a, r) => a + (r[i] || 0), 0) / 1000;
    const v = { f: Math.round(sum(1)), t: Math.round(sum(2)), d: Math.round(sum(3)) };
    const abs = Math.abs(v.f) + Math.abs(v.t) + Math.abs(v.d);
    return { v, abs, total: v.f + v.t + v.d, from: rows[0][0], to: rows[rows.length - 1][0], n: rows.length };
  }
  /* 集保：最新一週 ＋ 比較基準那一週＝34 天內、日期最接近「最新 − 28 天」的那一列（4 週前；遇到休市週可能是 27～34 天）。
     ⚠ 2026-10-02 實測：資料湖的集保週資料目前每一檔都只有 4 筆（09-04～09-24，集保開放資料只給最新一週、從 9 月初才開始累積），
       最早那一筆距最新只有 20 天 —— 硬要「4 週」就永遠是空的。所以基準取「4 週內能拿到的最早一筆」，
       畫面上照實寫跨幾週（「3 週 +2.12pp」「近 3 週變化」；2026-10-06 起不再寫「09-04 → 09-24」兩端日期，DECISIONS #329），資料滿 4 週之後自動變成「4 週」。
       不到 2 週（< 13 天）就不給變化：一週的雜訊太大，寫出來只會被誤讀成趨勢。*/
  function holdMix(pg) {
    const ho = (pg.holders || []).filter(r => r && r[1] != null);
    if (!ho.length) return null;
    const last = ho[ho.length - 1];
    const day = (r) => Date.parse(String(r[0]).slice(0, 10));
    const lim = day(last) - (28 + 6) * 864e5;
    const t28 = day(last) - 28 * 864e5;
    let prev = null;      // 34 天內、最接近 28 天的那一列（都不到 28 天時＝最早那一列）
    ho.slice(0, -1).forEach(r => { if (day(r) >= lim && (!prev || Math.abs(day(r) - t28) < Math.abs(day(prev) - t28))) prev = r; });
    const days = prev ? Math.round((day(last) - day(prev)) / 864e5) : 0;
    if (!prev || days < 13) return { last, prev: null, weeks: 0 };
    return { last, prev, weeks: Math.round(days / 7) };
  }
  /* 資券最新值：每一欄各自找「最後一個有值的交易日」——融資券（證交所，每天）與當沖／借券（另一個來源，常晚幾天）日期可能不同，
     所以一律連日期一起帶著走，畫面上寫出來。資券分頁最上面那一列用同一支，兩邊不會對不上（DECISIONS #294）。*/
  function mgLatest(pg) {
    const mg = pg.margin || [];
    const at = (i) => { for (let j = mg.length - 1; j >= 0; j--) if (mg[j] && mg[j][i] != null) return { d: String(mg[j][0]).slice(0, 10), v: mg[j][i], r: mg[j] }; return null; };
    const dt = at(5);
    return { mb: at(1), sb: at(2), mc: at(3), sc: at(4), dt, dr: dt && dt.r[6] != null ? { d: dt.d, v: dt.r[6] } : null, sl: at(7), sbl: at(8) };
  }
  function chipCard(pg) {
    const s = pg.summary || {};
    const pct1 = (v, n) => (n > 0 ? A.fmt.n(v / n * 100, 1) + '%' : '—');
    const P = (v, n) => (n > 0 ? (v / n * 100).toFixed(2) : '');
    const parts = [];
    /* ① 法人 */
    const im = instMix(pg);
    if (im && im.abs > 0) {
      const NM = { f: '外資', t: '投信', d: '自營商' };
      const buy = ['f', 't', 'd'].filter(k => im.v[k] > 0), sell = ['f', 't', 'd'].filter(k => im.v[k] < 0);
      const segs = buy.map(k => ({ k, v: im.v[k], lab: `${NM[k]} 買超 ${A.fmt.i(im.v[k])} 張（${pct1(im.v[k], im.abs)}）` }))
        .concat(buy.length && sell.length ? ['|'] : [])
        .concat(sell.map(k => ({ k, v: -im.v[k], sell: true, lab: `${NM[k]} 賣超 ${A.fmt.i(-im.v[k])} 張（${pct1(-im.v[k], im.abs)}）` })));
      const items = ['f', 't', 'd'].map(k => mixItem(k, NM[k], pct1(Math.abs(im.v[k]), im.abs), signLot(im.v[k]), A.fmt.cls(im.v[k]),
        { sell: im.v[k] < 0, pre: '比重', attrs: ` data-v="${im.v[k]}" data-pct="${P(Math.abs(im.v[k]), im.abs)}"` })).join('');
      parts.push(mixBox('inst', `${md5(im.from)}～${md5(im.to)}`, `合計 <b class="${A.fmt.cls(im.total)}" data-v="${im.total}">${signLot(im.total)}</b>`,
        mixBar(segs, `法人近 20 日：${['f', 't', 'd'].map(k => NM[k] + ' ' + signLot(im.v[k])).join('、')}；合計 ${signLot(im.total)}`)
        + `<div class="mixn">${items}</div><div class="mixf">實色＝買超、斜紋＝賣超（${im.n} 個交易日）</div>`));
    } else parts.push(mixBox('inst', '', '', '<div class="mixf">尚無法人買賣超資料</div>'));
    /* ② 集保 */
    const hm = holdMix(pg);
    if (hm) {
      const L = hm.last, Pv = hm.prev;
      const v = { big: L[1], mid: L[2], ret: L[3] };
      const rest = Math.max(0, 100 - (v.big || 0) - (v.mid || 0) - (v.ret || 0));
      const ch = (i) => (Pv && L[i] != null && Pv[i] != null ? L[i] - Pv[i] : null);
      const NM = { big: '≥1,000 張', mid: '400～1,000 張', ret: '≤10 張' };
      const IX = { big: 1, mid: 2, ret: 3 };
      const segs = [{ k: 'big', v: v.big, lab: `≥1,000 張 ${A.fmt.n(v.big, 2)}%` }, { k: 'mid', v: v.mid, lab: `400～1,000 張 ${A.fmt.n(v.mid, 2)}%` },
        { k: 'rest', v: rest, lab: `其他（10～400 張）${A.fmt.n(rest, 2)}%` }, { k: 'ret', v: v.ret, lab: `≤10 張 ${A.fmt.n(v.ret, 2)}%` }];
      const items = ['big', 'mid', 'ret'].map(k => { const c = ch(IX[k]);
        return mixItem(k, NM[k], null, v[k] != null ? A.fmt.n(v[k], 1) + '%' : '—', '',
          { attrs: ` data-v="${v[k] != null ? v[k] : ''}" data-ch="${c != null ? c.toFixed(4) : ''}"`, sub: `${hm.weeks || 4} 週 <span class="${c == null ? '' : c > 0 ? 'up' : c < 0 ? 'down' : ''}">${pp(c)}</span>` }); }).join('');
      parts.push(mixBox('hold', md5(L[0]), '<span class="muted">灰＝10～400 張</span>',
        mixBar(segs, `集保持股：≥1,000 張 ${A.fmt.n(v.big, 1)}%、400～1,000 張 ${A.fmt.n(v.mid, 1)}%、≤10 張 ${A.fmt.n(v.ret, 1)}%`)
        + `<div class="mixn">${items}</div><div class="mixf">${Pv ? `近 ${hm.weeks} 週變化` : ''}</div>`));
    } else parts.push(mixBox('hold', '', '', '<div class="mixf">尚無集保持股資料</div>'));
    /* ③ 信用與借券（張）＋ 當沖率 */
    const m = mgLatest(pg);
    if (m.mb) {
      const v = { mb: m.mb.v, sb: m.sb ? m.sb.v : 0, sbl: m.sbl ? m.sbl.v : 0 };
      const tot = v.mb + v.sb + v.sbl;
      const dTag = (x) => (x && x.d !== m.mb.d ? `（${md5(x.d)}）` : '');
      const segs = [{ k: 'mb', v: v.mb, lab: `融資餘額 ${A.fmt.i(v.mb)} 張` }, { k: 'sb', v: v.sb, lab: `融券餘額 ${A.fmt.i(v.sb)} 張` },
        { k: 'sbl', v: v.sbl, lab: `借券賣出餘額 ${A.fmt.i(v.sbl)} 張${dTag(m.sbl)}` }];
      const items = mixItem('mb', '融資餘額', pct1(v.mb, tot), A.fmt.i(v.mb) + ' 張', '', { attrs: ` data-v="${v.mb}" data-d="${m.mb.d}" data-pct="${P(v.mb, tot)}"` })
        + mixItem('sb', '融券餘額', m.sb ? pct1(v.sb, tot) : null, m.sb ? A.fmt.i(v.sb) + ' 張' : '—', '', { attrs: ` data-v="${m.sb ? v.sb : ''}" data-d="${m.sb ? m.sb.d : ''}" data-pct="${P(v.sb, tot)}"` })
        + mixItem('sbl', '借券賣出餘額', m.sbl ? pct1(v.sbl, tot) : null, m.sbl ? A.fmt.i(v.sbl) + ' 張' : '—', '',
          { attrs: ` data-v="${m.sbl ? v.sbl : ''}" data-d="${m.sbl ? m.sbl.d : ''}" data-pct="${P(v.sbl, tot)}"`, sub: m.sbl ? '' : '資料準備中' });
      const ratio = v.mb > 0 && m.sb ? v.sb / v.mb * 100 : null;
      let dtRow = '';
      if (m.dt) {
        const dr = m.dr ? m.dr.v : null;
        const p = dr != null ? Math.max(0, Math.min(100, dr)) : null;
        dtRow = `<div class="mixdt" data-v="${m.dt.v}" data-d="${m.dt.d}" data-r="${dr != null ? dr : ''}"><span class="mixt">${CHIP_HELP.dt[0]}</span>${mixQ('dt')}`
          + `${p != null ? `<div class="meter" style="--p:${p.toFixed(1)}%;--c:var(--amber)" role="img" aria-label="當沖率 ${A.fmt.n(dr, 1)}%"><i></i></div>` : ''}`
          + `<span class="mixdtv"><b>${p != null ? A.fmt.n(dr, 1) + '%' : '—'}</b> <small>當沖 ${A.fmt.i(m.dt.v)} 張</small></span></div>`;
      }
      parts.push(mixBox('credit', md5(m.mb.d), ratio != null ? `券資比 <b>${A.fmt.n(ratio, 1)}%</b>` : '',
        mixBar(segs, `信用與借券（張）：融資餘額 ${A.fmt.i(v.mb)}、融券餘額 ${A.fmt.i(v.sb)}、借券賣出餘額 ${A.fmt.i(v.sbl)}`)
        + `<div class="mixn">${items}</div>${dtRow}<div class="mixf">單位：張（餘額）；比例＝佔三項餘額合計</div>`));
    } else parts.push(mixBox('credit', '', '', '<div class="mixf">尚無融資融券資料</div>'));
    /* 量比：一條 0～3 的進度條，1.5 畫刻度（爆量門檻）*/
    const vr = s.vol_ratio != null && isFinite(s.vol_ratio) ? +s.vol_ratio : null;
    parts.push(`<div class="mixdt mixvr" data-v="${vr != null ? vr : ''}"><span class="mixt">${CHIP_HELP.volr[0]}</span>${mixQ('volr')}`
      + `${vr != null ? `<div class="meter" style="--p:${Math.min(100, vr / 3 * 100).toFixed(1)}%;--c:var(--cyan)" role="img" aria-label="量比 ${A.fmt.n(vr, 2)}（刻度＝1.5 爆量）"><i></i><b class="tick" style="left:50%"></b></div>` : ''}`
      + `<span class="mixdtv"><b>${vr != null ? A.fmt.n(vr, 2) : '—'}</b> <small>${vr != null ? (vr >= 1.5 ? '爆量（≥1.5）' : '未達 1.5') : ''}</small></span></div>`);
    return `<div class="card" id="skChipCard"><h3>籌碼快照 ${hq('skchip', '籌碼快照')}</h3>${hbox('skchip', ['法人：近 20 個交易日誰買誰賣、各佔多少', '集保：三個級距的持股比例與近幾週變化', '信用：融資、融券、借券賣出餘額（張）'])}`
      + `<div class="mixes">${parts.join('')}</div></div>`;
  }
  /* ★ 2026-10-02（Andy，DECISIONS #294）「總覽」分頁的版面，由上到下：
       ① AI 分析重點（積木 stock.mtf，site/blocks/stock_ai.js 的 brief）：一行結論＋四顆小標籤，點標籤捲到下面那一張細節卡
       ② 基本面、籌碼快照（積木 stock.fund，本檔）：上下兩張滿寬。改前並排（g2）時基本面七格只佔左卡上半、下半截空著跟右邊等高；
          滿寬之後基本面七格排成一列，籌碼快照三張小圖在寬畫面（容器 ≥900px）也排成一列，窄畫面才往下排
       ③ 各面向細節四張並排（桌機一列四張、窄畫面依序往下排）：技術面、技術面訊號、基本面、消息面。
          技術面訊號那一張就是積木 stock.signal 的出口（StockSignal.view），其他三張是 stock.mtf 的 facetCards。
     擋掉任何一支積木檔，只少那幾張，其他照常（積木原則三）。K 線卡右上角那一份 #skAi（頂部、另一支分支在改）這裡不動。
     ★ 2026-10-02 深夜（Andy 看了上線版說「誤解了」，DECISIONS #297）：改成**桌機三欄並排**（#skOv3）：
       左欄＝基本面卡｜中欄＝籌碼快照卡（卡內四塊由上往下：法人近 20 日 → 集保 → 信用與借券（含當沖率）→ 量比）｜
       右欄＝AI 卡（StockAI.ovCard：標題＋免責 → 一行重點 → 膠囊分頁籤 → 一次一面，技術面訊號那一面照舊是 StockSignal.view 的出口）。
       欄寬 1 : 1 : 1.2（右欄字多）；頂端對齊、各自自然高度（理由見 #297：切 AI 分頁時左、中兩欄不跟著變高）。
       容器 1080～790px（視窗約 1100～820）兩欄：基本面＋籌碼疊成左欄、AI 右欄；更窄一欄、依序往下排。
       .skovkpi 這層包裝留著（三欄時 display:contents 讓兩張卡各佔一欄；兩欄時它就是左欄）—— 積木驗收用 `.skovkpi > .card` 找 stock.fund 那兩張。
       擋掉 stock_ai.js：右欄只剩技術面訊號那一張（舊樣式的 #ovFacets 單卡）；兩支都擋：右欄整個不出現，左、中兩欄照常。
     ★ 2026-10-03（Andy：「三欄改成固定、等高」，DECISIONS #303）：三欄時改等高、底部對齊（高度＝籌碼快照自然高度，下限 560px），
       AI 卡 contain:size、分頁內容在卡裡捲（切籤三欄高度不變）；基本面格子平均撐開、族群中位那一句釘卡底。全部是 CSS（index.html），這支沒改。*/
  function tabOverview(pg, el) {
    const AI = window.StockAI, SG = window.StockSignal;
    const sig = SG ? SG.view({ summary: pg.summary, verdict: pg.verdict }, A.fmt, { tag: true, id: 'ovF-sig' }) : '';
    const etf = isEtf(pg.meta && pg.meta.code);
    // ETF：不放基本面卡（EPS／ROE／毛利率）與 AI 分析（含基本面一面），只留籌碼快照與技術面訊號
    const right = !etf && AI && AI.ovCard ? AI.ovCard(pg, A.fmt, sig) : (sig ? `<div class="skfacets" id="ovFacets" data-n="1">${sig}</div>` : '');
    el.innerHTML = `<div class="skov" id="skOv"><div class="skov3" id="skOv3" data-cols="${right ? 3 : 2}">
      <div class="skovkpi">${etf ? '' : fundCard(pg)}${chipCard(pg)}</div>${right}</div></div>`;
    if (etf) return;
    if (AI && AI.bindOverview) AI.bindOverview(el);
  }
  /* ★ 2026-09-27「指標」分頁（Andy 給的券商 App「符合 65 項指標」截圖）：
     題材、族群（groups.yaml／themes.yaml）＋管線算的事實條件標籤（stockpage.stock_tags）。
     **只陳述條件成不成立，不是推介**。台灣 50／MSCI 成分股、集團：沒有經查證的白名單來源，不做（DECISIONS #268）。
     ★ 2026-10-02（Andy，DECISIONS #294）：一條一列的清單 → 小方塊卡片（grid），分「符合」「未符合」兩區：
       · 符合＝強調色（紅框＋淡紅底，紅＝條件成立，跟 App 同一個語意）、未符合＝淡色；資料不足另一區、更淡。
       · 每一塊＝指標名稱＋一行判斷數字（「連三月營收年增>20%｜26-06 +32.3%…」）。一行放不下的數字點方塊**原地展開**全文，
         再點收回 —— 不跳頁、不開彈窗。
       · 題材、族群兩列移到最上面當標籤（點了照舊進題材／族群頁）。
       · 改前「未符合」收在 <details> 裡要多點一下才看得到；改後兩區都直接攤開，一眼看得出「6 項成立、2 項沒有」。
     #tagN（符合數）、#tagCard 這兩個 id 不變（別的驗收在讀）。
     ★ 2026-10-02 深夜（Andy：「誤解了」，DECISIONS #297）：
       · 「資料不足、無法判斷」那一區整區拿掉（不顯示、也不計入標題的 N ／ M）—— 那些條件既不成立也不是不成立，攤出來只是佔版面。
       · 「符合」「未符合」改成**左右並排兩欄**（#tagCols）：左＝符合、右＝未符合，欄內方塊一塊一塊往下排；視窗 ≤820px 才上下排。
       · 其中一區是 0 項時照樣佔一欄、寫一句「沒有…的條件」，不讓另一欄孤零零地撐滿（也不留空方塊）。*/
  function tabTags(pg, el) {
    const tg = (pg.tags || {}).items || [];
    const code = pg.meta.code;
    const th = A.L.themesOf ? A.L.themesOf(code) : '';
    const grp = (pg.meta.groups || []).map(gn => A.L.groupByName(gn)).join('');
    const hit = tg.filter(t => t.hit === true), miss = tg.filter(t => t.hit === false);
    const tile = (t, cls) => `<button type="button" class="tagtile ${cls}" data-hit="${cls}" data-id="${A.fmt.esc(t.id || '')}" aria-expanded="false" title="${A.fmt.esc((t.label || '') + (t.detail ? '｜' + t.detail : ''))}">`
      + `<b class="tagnm">${A.fmt.esc(t.label)}</b><span class="tagd">${t.detail ? A.fmt.esc(t.detail) : '—'}</span></button>`;
    const zone = (id, cls, title, list) => `<section class="tagzone ${cls}" id="${id}" aria-label="${title}"><div class="tagzh"><i aria-hidden="true"></i>${title} <b>${list.length}</b> 項</div>`
      + (list.length ? `<div class="taggrid">${list.map(t => tile(t, cls)).join('')}</div>` : `<div class="tagnone">沒有${title}的條件</div>`) + `</section>`;
    // 2026-10-05：頂部先放技術分析卡（stock_ai.js 的 techCardHTML，與 AI 卡技術面同源），原本的指標卡在其下
    const tech = window.StockAI && window.StockAI.techCardHTML ? window.StockAI.techCardHTML(pg, A.fmt) : '';
    el.innerHTML = tech + `<div class="card" id="tagCard"><div class="row spread"><h3>指標 <small>符合 <b id="tagN">${hit.length}</b> ／ ${hit.length + miss.length} 項</small> ${hq('sktag', '指標')}</h3>${A.disc ? A.disc('tag') : ''}</div>
      ${hbox('sktag', ['題材／族群＝本站依產業鏈整理的歸類', '指標＝用月營收、季報算的事實條件', '紅框＝條件成立；淡色＝不成立', '這些是條件描述，不是買賣建議'])}
      ${th || grp ? `<div class="tagmeta" id="tagMeta">${th ? `<div class="tagmr"><span class="tagk">題材</span><span class="tagrow">${th}</span></div>` : ''}${grp ? `<div class="tagmr"><span class="tagk">族群</span><span class="tagrow">${grp}</span></div>` : ''}</div>` : ''}
      ${hit.length || miss.length ? `<div class="tagcols" id="tagCols">${zone('tagHit', 'on', '符合', hit)}${zone('tagMiss', 'off', '未符合', miss)}</div>` : ''}
      ${!hit.length && !miss.length ? '<div class="empty">尚無月營收／季報資料</div>' : ''}
    </div>`;
    /* 點方塊＝原地展開那一行判斷數字的全文（再點收回）；同一時間可以開好幾塊，方便對照 */
    $$('.tagtile', el).forEach(b => b.onclick = () => { const o = b.getAttribute('aria-expanded') !== 'true'; b.setAttribute('aria-expanded', String(o)); b.classList.toggle('open', o); });
  }
  function tabRevenue(pg, el) {
    const rv = pg.revenue || {}; const mo = rv.monthly || [];
    const mil = (v) => (v == null ? '—' : A.fmt.i(Math.round(v / 1e6)));
    if (!mo.length) { el.innerHTML = '<div class="card"><div class="empty">尚無月營收資料</div></div>'; return; }
    const last = mo[mo.length - 1];
    /* ★ 2026-10-03（Andy：「營收分頁上面那排 6 個 KPI 方塊拿掉」，DECISIONS #305）：最新月份／單月營收／YoY／MoM／累計營收／累計 YoY
       全部是下方「月營收明細」表第一列的數字（同一份 revenue.monthly 最後一列），擺兩次只是把三張卡往下推。拿掉後三張卡直接頂到分頁列下面。*/
    // ★ 2026-10-04：「?」緊接標題文字、讀數放在「?」後面（EPS 與三率同）—— 改前讀數夾在中間，讀數一長「?」就被擠到下一行
    el.innerHTML = `<div class="grid skrev3" id="revGrid"><div class="card"><div class="row spread" style="gap:8px;flex-wrap:wrap"><h3>營收走勢 ${hq('skrev', '營收走勢')} <small id="revSub" data-readout></small></h3>
        <div class="row" style="gap:8px"><div class="seg" id="revView" role="group" aria-label="月或年"><button type="button" data-v="m">月走勢</button><button type="button" data-v="y">年度走勢</button></div>
        <div class="seg" id="revWin" role="group" aria-label="幾個月"><button type="button" data-v="12">12 月</button><button type="button" data-v="24">24 月</button><button type="button" data-v="36">36 月</button></div></div></div>
        ${hbox('skrev', ['月走勢：當月（青）＋去年同期（灰）並排', '線＝MoM、YoY（右軸 %）', '年度走勢：每年合計＋年增率', '今年未滿 12 個月＝跟去年同期幾個月比'])}<div id="revBar" class="chart"></div></div>
      <div class="card"><div class="row spread"><h3>逐年同月比較 ${hq('skrevy', '逐年同月比較')}</h3>${hbox('skrevy', ['每條線＝一年，同月份疊在一起比', '最粗那條＝今年', '看哪幾個月固定比較高＝旺季'])}<div class="seg" id="revMode"><button data-v="m" class="on">單月</button><button data-v="c">累計</button></div></div><div id="revYear" class="chart"></div></div>
      <div class="card tblcard" id="revTblCard"><h3>月營收明細 <small data-readout>單位：百萬元</small> ${hq('skrevtbl', '月營收明細')}</h3>${hbox('skrevtbl', ['YoY＝比去年同月；MoM＝比上個月', '累計營收＝今年 1 月加到這個月', '累計 YoY＝今年累計 ÷ 去年同期累計 − 1', '1 月到這個月缺任一月，累計留「—」'])}<div class="tw"><table id="revTbl"><thead><tr><th class="l">年/月</th><th>月營收</th><th>去年同期</th><th>YoY</th><th>MoM</th><th>累計營收</th><th>累計 YoY</th></tr></thead><tbody>${mo.slice().reverse().slice(0, 36).map(r => `<tr><td class="l mono">${r[0].replace('-', '/')}</td><td class="num">${mil(r[1])}</td><td class="num muted">${mil(r[6])}</td><td class="num ${A.fmt.cls(r[2])}">${A.fmt.pct(r[2])}</td><td class="num ${A.fmt.cls(r[3])}">${A.fmt.pct(r[3])}</td><td class="num">${mil(r[4])}</td><td class="num ${A.fmt.cls(r[5])}">${A.fmt.pct(r[5])}</td></tr>`).join('')}</tbody></table></div></div></div>`;
    /* ★ 2026-10-02（Andy #stock/1709，DECISIONS #295）：改前「營收走勢｜逐年同月」兩欄＋下面一張整列的月營收明細長表；
       改後三張卡並排（#revGrid .skrev3，跟總覽三欄同一套），明細表是第三欄、高度跟兩張圖卡一樣、在卡裡捲（.tblcard）。
       ≤1100 兩欄（明細表跨滿第二列）、≤820 一欄依序往下排。*/
    /* ★ 2026-09-27（Andy 給的券商 App「營收：月走勢｜年度走勢」）：
       月走勢＝當月與去年同期兩組柱並排（去年同期取 payload 第 7 欄；舊 payload 沒有就從月份表自己對），MoM、YoY 兩條線吃右軸 %；
       年度走勢＝每年合計柱＋年增率線。今年還沒過完：年增率只跟「去年同樣那幾個月」比，x 軸寫「2026（1–8 月）」，
       不拿 8 個月去跟 12 個月比。視窗 12／24／36 個月記在 tw.revWin，月／年記在 tw.revView。*/
    const byYm = new Map(mo.map(r => [r[0], r[1]]));
    const lyOf = (r) => (r[6] != null ? r[6] : byYm.get((+r[0].slice(0, 4) - 1) + r[0].slice(4)) ?? null);
    let rview = lsGet('tw.revView', v => v === 'm' || v === 'y', 'm');
    let rwin = +lsGet('tw.revWin', v => ['12', '24', '36'].includes(v), '12');
    const yrsAll = rv.yearly || [];
    const drawRev = () => {
      $$('#revView button', el).forEach(b => b.classList.toggle('on', b.dataset.v === rview));
      $$('#revWin button', el).forEach(b => b.classList.toggle('on', +b.dataset.v === rwin));
      const wEl = $('#revWin', el); if (wEl) wEl.hidden = rview !== 'm';
      el.dataset.revView = rview; el.dataset.revWin = String(rwin);
      const sub = $('#revSub', el);
      const pctAx = { ...A.axisStyle, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } };
      let revC = null;
      if (rview === 'm') {
        const t = mo.slice(-rwin);
        /* ★ 2026-09-28（營收普查）：管線把缺的月份補成空列（營收 null，不是 0），類別軸才不會把 3 月跟 5 月畫成相鄰；
           讀數要講出來「這一段缺幾個月」，不然空一格看起來像是營收掉到 0。
           右軸（YoY／MoM）遇到極端值（小基期、建設交屋月動輒 +30,000%）會把其他月份壓成一條平線 ——
           軸的上下界改成可見值的 5～95 百分位再留 15% 邊，超出的點被圖框切掉、數字照樣在提示框裡，讀數標「右軸已截斷」。
           只動顯示範圍，不改任何數字。*/
        const gapN = t.filter(r => r[1] == null).length;
        const pv = t.flatMap(r => [r[2], r[3]]).filter(v => v != null && isFinite(v)).sort((a, b) => a - b);
        let pMin = null, pMax = null, clipped = false;
        if (pv.length >= 4) {
          const q = (p) => pv[Math.min(pv.length - 1, Math.max(0, Math.round((pv.length - 1) * p)))];
          const lo = Math.min(0, q(0.05)), hi = Math.max(0, q(0.95)), pad = Math.max(10, (hi - lo) * 0.15);
          if (pv[0] < lo - pad || pv[pv.length - 1] > hi + pad) {
            pMin = Math.floor((lo - pad) / 10) * 10; pMax = Math.ceil((hi + pad) / 10) * 10; clipped = true;
          }
        }
        el.dataset.revGap = String(gapN); el.dataset.revClip = clipped ? '1' : '0';
        if (sub) sub.textContent = t.length ? `${t[0][0]}～${t[t.length - 1][0]}，${t.length} 個月${gapN ? `（缺 ${gapN} 個月，留空）` : ''}${clipped ? '　·　右軸已截斷' : ''}` : '';
        if (pMin != null) { pctAx.min = pMin; pctAx.max = pMax; }
        revC = A.chart('revBar', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${p.seriesName.includes('營收') || p.seriesName === '去年同期' ? A.fmt.yi(p.value) : A.fmt.pct(p.value)}`).join('<br>') },
          legend: { show: false }, grid: { left: 60, right: 50, top: 10, bottom: 30 },
          xAxis: { ...A.axisStyle, type: 'category', data: t.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2).replace('-', '/'), hideOverlap: true } },
          yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.yi(v) } }, pctAx],
          series: [{ name: '當月營收', type: 'bar', label: { show: false }, data: t.map(r => r[1]), itemStyle: { color: 'rgba(62,224,255,.75)', borderRadius: [3, 3, 0, 0] } },
            { name: '去年同期', type: 'bar', label: { show: false }, data: t.map(lyOf), itemStyle: { color: 'rgba(160,170,190,.45)', borderRadius: [3, 3, 0, 0] } },
            { name: 'MoM', type: 'line', yAxisIndex: 1, data: t.map(r => r[3]), smooth: .3, showSymbol: t.length <= 24, symbolSize: 4, lineStyle: { color: '#8b7bff', width: 1.6 }, itemStyle: { color: '#8b7bff' } },
            { name: 'YoY', type: 'line', yAxisIndex: 1, data: t.map(r => r[2]), smooth: .3, showSymbol: t.length <= 24, symbolSize: 4, lineStyle: { color: '#ffb454', width: 2 }, itemStyle: { color: '#ffb454' } }] }, { notMerge: true });
      } else {
        const ys = yrsAll.slice(-10);
        const bm = new Map(yrsAll.map(y => [y.year, y.by_month || {}]));
        const rows = ys.map(y => { const mths = Object.keys(y.by_month || {}).map(Number); const prev = bm.get(y.year - 1);
          let yoy = null;
          if (prev && mths.length && mths.every(m => prev[m] != null)) { const a = mths.reduce((s_, m) => s_ + y.by_month[m], 0), b = mths.reduce((s_, m) => s_ + prev[m], 0); if (b) yoy = (a / b - 1) * 100; }
          const part = y.months < 12;
          return { lab: part ? `${y.year}（${Math.min(...mths)}–${Math.max(...mths)} 月）` : String(y.year), rev: y.revenue, yoy, part }; });
        if (sub) sub.textContent = rows.length ? `${ys[0].year}～${ys[ys.length - 1].year}，${rows.length} 年` : '';
        revC = A.chart('revBar', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => { const r = rows[ps[0].dataIndex]; return `<b>${r.lab}</b><br>營收 ${A.fmt.yi(r.rev)}<br>年增率 ${A.fmt.pct(r.yoy)}${r.part ? '（跟去年同樣月份比）' : ''}`; } },
          legend: { show: false }, grid: { left: 60, right: 50, top: 10, bottom: 30 },
          xAxis: { ...A.axisStyle, type: 'category', data: rows.map(r => r.lab), axisLabel: { color: A.CH.ink3, hideOverlap: true, formatter: v => v.slice(0, 4) } },
          yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.yi(v) } }, pctAx],
          series: [{ name: '年營收', type: 'bar', label: { show: false }, data: rows.map(r => ({ value: r.rev, itemStyle: { color: r.part ? 'rgba(62,224,255,.35)' : 'rgba(62,224,255,.75)', borderRadius: [3, 3, 0, 0] } })) },
            { name: '年增率', type: 'line', yAxisIndex: 1, data: rows.map(r => r.yoy), symbolSize: 6, lineStyle: { color: '#ffb454', width: 2 }, itemStyle: { color: '#ffb454' } }] }, { notMerge: true });
      }
      const rvw = $('#revView', el);
      extLegend(revC, rvw && rvw.parentElement);        // 設計 v4 2B：圖例搬到月／年、12／24／36 那一列的右端
    };
    $$('#revView button', el).forEach(b => b.onclick = () => { rview = b.dataset.v; lsSet('tw.revView', rview); drawRev(); });
    $$('#revWin button', el).forEach(b => b.onclick = () => { rwin = +b.dataset.v; lsSet('tw.revWin', String(rwin)); drawRev(); });
    drawRev();
    const yr = (rv.yearly || []).slice(-6); let mode = 'm';
    /* ★ 2026-10-04（Andy 截圖 6182：「逐年同月比較 Y 軸從 0 開始，資料都擠在上半部」）：
       Y 軸改依資料極值上下各留 8% 邊（scale:true），曲線置中；單月與累計同一套，切換時各自重算。*/
    const drawYear = () => { const yc = A.chart('revYear', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue} 月</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${A.fmt.yi(p.value)}`).join('<br>') }, legend: { show: false, type: 'scroll' }, grid: { left: 60, right: 20, top: 10, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: Array.from({ length: 12 }, (_, i) => i + 1), axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle, scale: true, min: (e) => e.min - (e.max - e.min) * 0.08, max: (e) => e.max + (e.max - e.min) * 0.08, axisLabel: { formatter: v => A.fmt.yi(v), showMinLabel: false, showMaxLabel: false } },
      series: yr.map((y, i) => { let acc = 0, broke = false; const d = Array.from({ length: 12 }, (_, m) => { const v = y.by_month[m + 1]; if (v == null) { broke = true; return null; } if (mode === 'c') { if (broke) return null; acc += v; return acc; } return v; }); /* ★ 2026-09-28：累計遇缺月就停（跳過缺月繼續加，後面每個月都少算一個月，線會系統性偏低）*/ return { name: String(y.year), type: 'line', data: d, smooth: .2, symbolSize: 5, lineStyle: { width: i === yr.length - 1 ? 3 : 1.5, color: A.PALETTE[i] }, itemStyle: { color: A.PALETTE[i] } }; }) });
      /* ★ 2026-10-02（DECISIONS #295）：營收改三欄之後這張卡只剩約 430px 寬，六個年份的 HTML 圖例放不進標題列，
         退回 ECharts 圖例時會折成兩行、第二行（2026）壓到 Y 軸最上面的「14.0 億」。退回時改成單行可捲（type:'scroll'）、色樣縮小，永遠只佔一行；繪圖區頂 30 → 36（可捲圖例外框底約 25px，
         Y 軸最上面那個刻度字半高約 7px，30 只剩 5px 會貼在一起 —— _uitest「個股分頁版面1002」的圖例越界檢查量的）。
         ⚠ 一開始的 option 就要寫 legend.type:'scroll'：plain 跟 scroll 是兩種元件，退回時才換 type 會整個換掉圖例元件，
         藏起來的年份（legend.selected）就丟了 —— _uitest「設計v4第二批2B」⑧（800→1000→800 來回後 2021 要仍藏著）抓到的。*/
      const rm = $('#revMode', el); if (rm) extLegend(yc, rm.parentElement, { fb: { top: 0, type: 'scroll', itemWidth: 10, itemGap: 5,
        pageIconColor: A.CH.ink2, pageTextStyle: { color: A.CH.ink3 }, textStyle: { color: A.CH.ink2, fontSize: 12 } }, fbTop: 36 }); };   // 設計 v4 2B：六個年份的圖例放標題列最右端（放不下退回圖內單行）
    $$('#revMode button').forEach(b => b.onclick = () => { $$('#revMode button').forEach(x => x.classList.toggle('on', x === b)); mode = b.dataset.v; drawYear(); });
    drawYear();
  }
  /* ------------------------------------------------------------ 本益比河流圖
     Andy 2026-09-15：「本益比這邊需要新增像是財報狗那樣的河流圖…兩種模式可切換」。

     做法跟 Goodinfo／財報狗一樣：把「近四季 EPS」當成一條**階梯函數**（每次財報公布才跳一次），
     再乘上幾個本益比倍數，就得到幾條「這個倍數對應的股價」。股價線穿梭在這幾條之間，
     它現在在哪一條帶，就是市場現在給的評價。

     倍數刻意**不寫死** 13/15/17/19/21/23：那是 Goodinfo 對台積電的預設值。
     金融股合理本益比十倍出頭、AI 股三十倍，寫死對大多數股票沒有意義。
     改用這一檔自己的歷史本益比分位數（10/30/50/70/90%），等於「跟自己比貴不貴」。*/
  const PE_ZONES = [            // 由下到上；顏色跟著「貴＝紅、便宜＝綠」（Andy 給的參考圖就是這個方向）
    { name: '低估', c: '#1f9e89' }, { name: '價值', c: '#5fe08a' }, { name: '合理', c: '#d4f25a' },
    { name: '觀望', c: '#ffc53d' }, { name: '高估', c: '#ff7a45' }, { name: '警示', c: '#ff2e63' },
  ];
  /* ★ 2026-09-28（Andy：「本益比河流圖 顏色」）：配色分深／淺兩組，並把色帶預設透明度 30% → 45%。
     舊的一組（#1c7a5a #2ee59d #c3ff5b #ffd166 #ff8fab #ff4d6d）在淺色主題的白底上，
     合理／觀望兩帶疊 30% 後跟底色的對比只有 1.06～1.12:1（等於看不見），高估（粉）與警示（紅）相鄰色差 ΔE 只有 9～11。
     新的兩組是「青綠→綠→黃綠→琥珀→橘→紅」的發散色階，相鄰帶同時差色相與明度；
     算過（CIELAB ΔE、疊在卡片底色上）：預設 45% 時相鄰帶 ΔE 深色 19～27、淺色 18～27，每一帶對底色 ≥1.35:1。
     _uitest「本益比河流配色與Y軸0928」在瀏覽器裡用實際畫出來的顏色再驗一次（門檻 ΔE ≥ 15、對比 ≥ 1.25）。*/
  const PE_Z_LIGHT = ['#0b7a75', '#2fa84f', '#a0c020', '#f0b000', '#ef6a20', '#c8102e'];
  const PE_Z_OLD = ['#1c7a5a', '#2ee59d', '#c3ff5b', '#ffd166', '#ff8fab', '#ff4d6d'];
  const peDefaultZ = () => (document.documentElement.getAttribute('data-theme') === 'light' ? PE_Z_LIGHT : PE_ZONES.map(x => x.c));

  /* 河流圖的樣式也要能自己調（Andy 2026-09-15：「需要新增本益比河流圖的顏色 線條粗細 透明度 等設定」）。
     存在 cfg.st.pe：z＝六個區間的顏色（由下到上）、w＝線寬、o＝色帶透明度。
     沒設定過就回預設，所以舊的 localStorage 不用搬。 */
  function peStyle(cfg) {
    // of＝填滿模式自己的透明度（預設 90，一眼就是「填滿」的樣子）；o 是色帶模式的
    const raw = Object.assign({ w: 1, o: 45, of: 90 }, ((cfg || {}).st || {}).pe || {});
    // 存著的 z 若跟任何一組預設（舊預設、深色、淺色）一模一樣＝沒自己調過，只是設定面板存檔時順手把畫面上的預設寫進去
    // → 一律換成「目前主題」的預設。不然在深色主題碰過設定，切到淺色還是深色那組（淺底上看不清楚）。
    const same = (a) => raw.z.every((c, i) => String(c).toLowerCase() === a[i]);
    const own = Array.isArray(raw.z) && raw.z.length === 6 && ![PE_Z_OLD, PE_Z_LIGHT, PE_ZONES.map(x => x.c)].some(same);
    const z = own ? raw.z : peDefaultZ();
    return { w: Math.max(1, Math.min(4, +raw.w || 1)), o: Math.max(5, Math.min(100, +raw.o || 45)),
             of: Math.max(20, Math.min(100, +raw.of || 90)),
             z, zones: PE_ZONES.map((x, i) => ({ name: x.name, c: z[i] })) };
  }

  /* 設定面板要開在按鈕旁邊。用 fixed ＋ 按鈕的實際座標算，再夾進視窗裡；
     放不下就翻到按鈕上方。以前靠 CSS 的 right:18px，錨點跟按鈕沒關係，所以會飄走。*/
  /* 設定面板「叫不回來」的修正（Andy 2026-09-16：
     「當我按下其他地方時，沒有點到設定內的範圍，設定面板會消失，我需要會再呼叫」）。

     原本 ⚙ 的開關只看 `pop.hidden`。問題是**面板可以在 hidden 還是 false 的情況下消失** ——
     換分頁再回來、圖表重畫、或面板被定位到畫面外都會這樣。
     這時候按 ⚙ 走的是「關閉」那一條，等於關掉一個本來就看不見的東西，
     從使用者的角度就是「按了沒反應」。實測重現：開著面板切到資金流向再回來，
     下一次按 ⚙ 完全沒動靜，要按第二次才開。

     修法兩件一起做：
     1. 開關改用「**現在畫面上真的看得到嗎**」判斷，不是只看 hidden
     2. 補上正規的「點面板外面就收起來」，收的時候把 kind 一起清掉，狀態不會殘留 */
  function popVisible(pop, kind) {
    if (!pop || pop.hidden) return false;
    if (kind && pop.dataset.kind !== kind) return false;
    const r = pop.getBoundingClientRect();
    return r.width > 0 && r.height > 0 &&
           r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
  }

  function closePop(pop) {
    untrackPop();
    pop = pop || document.getElementById('cfgPop');
    if (!pop) return;
    pop.hidden = true;
    pop.dataset.kind = '';
    pop.classList.remove('indpop');
    const b = document.getElementById('indBtn'); if (b) b.setAttribute('aria-expanded', 'false');
  }

  function wirePopDismiss() {
    if (wirePopDismiss._done) return;              // 只掛一次，否則每次重畫都多一個監聽
    wirePopDismiss._done = true;
    // 用 mousedown 而不是 click：在面板裡拖曳滑桿時，放開滑鼠的位置可能已經在面板外，
    // 那一下 click 的 target 會是面板外面，用 click 判斷會在拖到一半時把面板關掉。
    document.addEventListener('mousedown', (e) => {
      const pop = document.getElementById('cfgPop');
      if (!pop || pop.hidden) return;
      if (e.target.closest && (e.target.closest('.cfgpop') || e.target.closest('#indBtn, #tfAdd'))) return;
      closePop(pop);
    }, true);
    // 換頁一律收掉：不收的話 hidden 會留在 false，回來按 ⚙ 就變成「關掉看不見的面板」
    window.addEventListener('hashchange', () => closePop());
  }

  /* 2026-09-24：外面點一下本來就會關（wirePopDismiss 那段）；登記進全站那一份是為了多一個 Esc。
     ★ 2026-09-26 改成**每次打開都登記目前這一顆** #cfgPop：它是個股頁模板的一部分，換一檔／換頁回來就是新的元素，
     以前只在第一次打開時登記，之後登記表裡抓的是已經被拆掉的舊元素 —— 換過頁之後按 Esc 就關不掉（驗收抓到的）。
     dismissable 對同一個元素重複登記只會更新，不會疊。*/
  function popEsc(pop) {
    if (pop && A && A.dismissable) A.dismissable(pop, () => closePop(pop), { ignore: ['.cfgpop', '#indBtn', '#tfAdd'] });
  }

  /* ★ 2026-09-26 晚（Andy：「打開指標 ▾ 後面板出現在圖的中央」）——根因與修法：
     面板是 position:fixed，**只在打開那一刻**依按鈕位置算一次座標。之後頁面一捲動，按鈕跟著內容往上走，
     面板卻釘在視窗的同一個位置 —— 個股頁的 K 線圖就在工具列正下方，捲個幾百 px，面板看起來就「浮在圖中央」。
     另一條同源的路：`.view.on` 進場動畫那 0.25 秒內祖先有 transform，fixed 會改以祖先為基準；
     placePop 的 (0,0) 校正是在動畫中量的，動畫一結束 transform 拿掉，校正值就變成多出來的偏移。
     修法：面板開著的時候，**捲動（任何捲動容器，capture）／視窗改大小／動畫結束**都重新貼一次按鈕；
     按鈕被捲到頂欄底下或畫面外（看不到錨點了）就直接關掉 —— 不留一塊沒有主人的面板。
     面板自己裡面的捲動不算（那是使用者在捲清單，重算只會把清單捲回頂端）。*/
  let popTrack = null;
  function untrackPop() {
    if (!popTrack) return;
    window.removeEventListener('scroll', popTrack.on, true);
    window.removeEventListener('resize', popTrack.on);
    document.removeEventListener('animationend', popTrack.on, true);
    if (popTrack.raf) cancelAnimationFrame(popTrack.raf);
    clearTimeout(popTrack.t);
    popTrack = null;
  }
  function trackPop(pop, btn) {
    untrackPop();
    const T = { raf: 0, t: 0 };
    const redo = () => {
      T.raf = 0;
      if (popTrack !== T) return;
      if (!pop.isConnected || pop.hidden || !btn.isConnected) { untrackPop(); return; }
      const r = btn.getBoundingClientRect();
      const bar = document.querySelector('.topbar');
      const hb = bar ? Math.max(0, bar.getBoundingClientRect().bottom) : 0;
      if (!r.width || r.bottom <= hb + 2 || r.top >= innerHeight - 8) { closePop(pop); return; }
      placePop(pop, btn, true);
    };
    T.on = (e) => {
      if (e && e.type === 'scroll' && e.target && e.target.nodeType === 1 && pop.contains(e.target)) return;
      if (!T.raf) T.raf = requestAnimationFrame(redo);
    };
    popTrack = T;
    window.addEventListener('scroll', T.on, true);
    window.addEventListener('resize', T.on);
    document.addEventListener('animationend', T.on, true);
    // 保險：剛換頁就點開時，進場動畫可能還沒跑完（animationend 會補一次；這裡再補一次，動畫被瀏覽器省略時也對）
    T.t = setTimeout(T.on, 320);
  }

  function placePop(pop, btn, again) {
    if (!pop || !btn) return;
    if (!again) { wirePopDismiss(); popEsc(pop); }
    pop.hidden = false;                                  // 要先顯示才量得到寬高
    const keepScroll = pop.scrollTop;                    // 重貼時保住清單捲到哪（清 max-height 會把 scrollTop 歸零）
    pop.style.maxHeight = '';
    const r = btn.getBoundingClientRect();
    const w = pop.offsetWidth || 376, h = pop.offsetHeight || 360, pad = 10;
    /* 水平：先試「從按鈕左緣往右展開」（按鈕在畫面左半邊時這樣最自然）；
       右邊放不下才改成「右緣跟按鈕右緣切齊」。兩個都不行才夾進視窗。*/
    let left = r.left;
    if (left + w > innerWidth - pad) left = r.right - w;
    left = Math.min(Math.max(pad, left), Math.max(pad, innerWidth - w - pad));
    /* 面板比視窗還高是常態（均線＋五個指標＋SMC＋本益比）。
       選上下空間比較大的那一邊，並且把 max-height 夾到那一邊的可用高度 ——
       讓它「貼著按鈕、裡面自己捲」，而不是為了塞下整個面板而跑到畫面另一頭。*/
    const below = innerHeight - r.bottom - pad - 6, above = r.top - pad - 6;
    const useBelow = below >= Math.min(h, 320) || below >= above;
    const room = Math.max(160, useBelow ? below : above);
    const top = useBelow ? r.bottom + 6 : Math.max(pad, r.top - Math.min(h, room) - 6);
    /* ★ 不要直接把視窗座標寫進 left/top。
       `position:fixed` 只要祖先有 transform / filter / backdrop-filter 就會改以那個祖先為基準
       —— 本站 `.view.on` 的進場動畫正是 `transform: translateY(4px) → none`，
       在那 0.25 秒內（或動畫被重新觸發時）面板就會整個偏掉（線上實測偏了 195px）。
       所以先把它擺到 (0,0)，量出「(0,0) 實際落在視窗的哪裡」，再用差值校正。
       這樣不管祖先是什麼都準。*/
    pop.style.left = '0px'; pop.style.top = '0px';
    const zero = pop.getBoundingClientRect();
    pop.style.left = (left - zero.left) + 'px';
    pop.style.top = (top - zero.top) + 'px';
    pop.style.maxHeight = room + 'px';
    if (again) pop.scrollTop = keepScroll;
    else trackPop(pop, btn);
  }

  function peRiver(pg) {
    const hist = (pg.pe_history || []).filter(r => r && r.ttm_eps > 0 && r.from);
    const daily = (pg.daily && pg.daily.length ? pg.daily : pg.ohlcv) || [];
    if (hist.length < 4 || daily.length < 60) return null;
    const steps = hist.slice().sort((a, b) => (String(a.from) < String(b.from) ? -1 : 1));
    const dates = [], close = [], eps = [], pes = [];
    let si = 0;
    for (const b of daily) {
      const d = String(b[0]).slice(0, 10);
      if (d < String(steps[0].from)) continue;          // 第一份能算 TTM 的財報之前，沒有本益比可言
      while (si + 1 < steps.length && String(steps[si + 1].from) <= d) si++;
      const e = steps[si].ttm_eps, c = b[4];
      if (!(e > 0) || !(c > 0)) continue;
      dates.push(d); close.push(c); eps.push(e); pes.push(c / e);
    }
    if (dates.length < 60) return null;
    const sorted = pes.slice().sort((a, b) => a - b);
    const q = (p) => { const i = (sorted.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i);
      return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo); };
    const mult = [q(0.1), q(0.3), q(0.5), q(0.7), q(0.9)].map(v => Math.round(v * 10) / 10);
    /* EPS 幾乎沒變、股價也沒動的股票，五個分位數會全部擠在一起，河流就變成一條線。
       撞在一起就強制拉開，至少看得出層次。*/
    for (let i = 1; i < mult.length; i++) {
      if (mult[i] <= mult[i - 1]) mult[i] = +(mult[i - 1] + Math.max(0.5, mult[0] * 0.08)).toFixed(1);
    }
    /* 河流要平滑、貼著走勢（Andy 2026-09-15：「本益比河流圖需要平滑點 更貼近走勢」）。
       財報一季才公布一次，直接照階梯畫就是一格一格的台階，跟他給的參考圖差很多。
       把 EPS 那條階梯用**只看過去**的指數平滑抹平 —— 不可以往前內插，
       那等於在財報還沒公布前就先用它的數字，是這個專案一直禁止的前視偏誤。
       半衰期約 30 個交易日（一個半月），新財報會在一個多月內被吃進帶子裡。
       顯示用的「目前本益比」仍然用**真實**的近四季 EPS，不用平滑值。*/
    const K = 2 / (30 + 1);
    let acc = null;
    const epsSmooth = eps.map(v => { acc = acc === null ? v : v * K + acc * (1 - K); return +acc.toFixed(4); });
    const bands = mult.map(m => epsSmooth.map(e => +(m * e).toFixed(2)));
    const lastClose = close[close.length - 1], lastEps = eps[eps.length - 1];
    const curPe = +(lastClose / lastEps).toFixed(1);
    let zi = 0; while (zi < mult.length && curPe >= mult[zi]) zi++;   // 0＝低估 … 5＝警示
    return { dates, close, eps, epsSmooth, mult, bands, curPe, lastEps, zone: PE_ZONES[zi], zoneIdx: zi };
  }

  /** 把河流的倍數線對齊到 K 線圖的每一根（日期不同、根數也不同，所以要各自對表）。 */
  function peBandsForBars(r, bars, st) {
    if (!r || !bars || !bars.length) return null;
    const idx = new Map(); r.dates.forEach((d, i) => idx.set(d, i));
    const style = st || peStyle(null);
    // 五條線用「上面那個區間」的顏色：9.5 倍那條是價值／25 倍那條是警示
    return r.mult.map((m, k) => ({
      mult: m, color: style.z[k + 1], width: style.w, alpha: Math.max(35, style.o + 35),
      vals: bars.map(b => {
        // 週線／月線的一根對應到那個區間的最後一個交易日；分 K 的日期在前 10 碼
        const i = idx.get(String(b[0]).slice(0, 10));
        // 用平滑後的 EPS，K 線上那幾條線才跟下面那張河流圖長得一樣
        return i == null ? null : +(m * r.epsSmooth[i]).toFixed(2);
      }),
    }));
  }

  /** 畫下方那張大圖。mode：'band' 色帶分區（fugle 那種）／'mult' 倍數線（Goodinfo 那種）。 */
  /* 本益比河流的可視區間（0-100 的百分比），由下方的「看哪一段」拉Bar 控制。
     2026-09-18（Andy 圖七）：「本益比河流圖也是，需要播放功能 拉Bar + & -」。

     ★ 用「切資料」實作，**絕對不要用 ECharts 的 dataZoom**（DECISIONS #192）。
       `dataZoom: {type:'inside'}` 會註冊 wheel 事件並吃掉它，
       #peWrap 的滾輪放大就失效了 —— 而那是 Andy 2026-09-16 親口要的功能，
       peWrap 本來就在 t_zoom_sweep 的白名單裡（#104）。
       這件事這支檔案 1631 行早就寫過一次；2026-09-19 我沒看到又踩一次，
       驗收立刻抓到「本益比河流圖往上滾沒有放大」。*/
  let peWin = { start: 0, end: 100 };
  /* ★ 2026-09-28（Andy：「本益比河流圖 … 縮放（Y 軸拖曳）」）：沿用 K 線圖價格軸的手感（chart.js _wheelOnPriceAxis、
     Lightweight Charts 的價格軸拖曳）—— 在**左側 Y 軸**上：按住往上拖＝拉開（放大）、往下拖＝壓扁（縮小）、
     滾輪一格 1.12 倍、雙擊還原自動範圍。圖區內部照舊交給 wheelZoom（滾輪放大整張、放大後拖曳平移）。
     做法是在 Y 軸那一條疊一塊透明的 .peyaxis 接事件並 stopPropagation：
       · 不用 ECharts dataZoom —— 它會吃掉 wheel（DECISIONS #192，這支檔案已經踩過兩次）；
       · 不在整張圖上判座標 —— wheelZoom 的 pointerdown 掛在外層 pane，疊一塊自己的元素，事件在它身上就停，兩邊不打架。
     peY＝null 是自動；換股票歸零（tabProfit），切畫法、拉時間 Bar 都保留（使用者調好的價格區間不該被重設）。*/
  let peY = null;
  function wirePeYAxis(id, redraw) {
    const dom = document.getElementById(id); if (!dom) return;
    dom._peRedraw = redraw;
    const resetBtn = document.getElementById('peYReset');
    if (resetBtn) resetBtn.hidden = !peY;
    let ax = dom.querySelector(':scope > .peyaxis');
    if (!ax) {
      ax = document.createElement('div');
      ax.className = 'peyaxis';
      ax.title = 'Y 軸：按住上下拖曳縮放、滾輪縮放、雙擊還原';
      ax.setAttribute('aria-label', '本益比河流圖 Y 軸縮放區（上下拖曳、滾輪、雙擊還原）');
      ax.style.cssText = 'position:absolute;left:0;top:24px;bottom:34px;width:56px;z-index:6;cursor:ns-resize;touch-action:none;background:transparent';
      if (getComputedStyle(dom).position === 'static') dom.style.position = 'relative';
      dom.appendChild(ax);
      const inst = () => window.echarts && echarts.getInstanceByDom(dom);
      const base = () => { const i = inst(); return (i && i._peY) || null; };
      let raf = 0;
      const apply = (min, max) => {
        if (!(max > min)) return;
        peY = { min: +min.toFixed(2), max: +max.toFixed(2) };
        if (!raf) raf = requestAnimationFrame(() => { raf = 0; if (dom._peRedraw) dom._peRedraw(); });
      };
      const scale = (b, f) => { const c = (b.min + b.max) / 2, h = Math.max(0.01, (b.max - b.min) / 2 * f); apply(c - h, c + h); };
      let drag = null;
      ax.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        const b = base(); if (!b) return;
        e.preventDefault(); e.stopPropagation();
        drag = { y: e.clientY, b: { min: b.min, max: b.max }, id: e.pointerId };
        try { ax.setPointerCapture(e.pointerId); } catch (err) { /* 忽略 */ }
        dom.classList.add('peydrag');
      });
      ax.addEventListener('pointermove', (e) => {
        if (!drag) return;
        e.preventDefault(); e.stopPropagation();
        // 往上拖（dy<0）→ f<1 → 範圍變窄＝放大；往下拖 → 範圍變寬＝縮小。160px 約一倍，跟 K 線價格軸的手感接近
        scale(drag.b, Math.exp((e.clientY - drag.y) / 160));
      });
      const end = (e) => {
        if (!drag) return;
        try { ax.releasePointerCapture(drag.id); } catch (err) { /* 忽略 */ }
        drag = null; dom.classList.remove('peydrag');
        if (e) e.stopPropagation();
      };
      ax.addEventListener('pointerup', end);
      ax.addEventListener('pointercancel', end);
      ax.addEventListener('wheel', (e) => {
        const b = base(); if (!b) return;
        e.preventDefault(); e.stopPropagation();
        scale(b, e.deltaY > 0 ? 1.12 : 1 / 1.12);
      }, { passive: false });
      ax.addEventListener('dblclick', (e) => {
        e.preventDefault(); e.stopPropagation();
        peY = null; if (dom._peRedraw) dom._peRedraw();
      });
      ax.addEventListener('click', (e) => e.stopPropagation());
    }
  }
  function sliceRiver(r, win) {
    if (!r || !r.dates || !r.dates.length) return r;
    const N = r.dates.length;
    const end = Math.max(2, Math.min(N, Math.round(win.end / 100 * N)));
    const from = Math.max(0, Math.min(end - 2, Math.round(win.start / 100 * N)));
    if (from === 0 && end === N) return r;
    const cut = (a) => (Array.isArray(a) ? a.slice(from, end) : a);
    return { ...r, dates: cut(r.dates), close: cut(r.close), eps: cut(r.eps),
             bands: (r.bands || []).map(cut) };
  }
  /* 河流圖的「看哪一段」拉Bar（Andy 2026-09-18 圖七要播放與 ＋ −）。
     兩支：一支調**視窗長度**（看多長一段），一支調**截止位置**（看到哪一天為止，可播放）。
     只建一次；重畫時只更新視窗值，不要重建（重建會把播放中的計時器孤兒化）。*/
  /* ★ 2026-10-04（Andy：「本益比河流圖滾輪縮放後，上方『看多長／截止』那一列不見、右側多了『警示』」）：
     根因：改前用一個模組層級的 peWired 旗標「整個網頁只接一次」。獲利分頁每次進來（切分頁回來、換股票、重畫）都會重建
     #peLen／#peEnd 兩個空殼，但旗標已是 true → 新的空殼永遠沒人填，控制列整列消失；peWin 又停在上一次的視窗，
     畫面變成「沒有控制列、範圍跟上次不一樣」（右側標籤因此多出「警示」那一帶）。
     修法：旗標改掛在這一次的 #peEnd 元素上（box._peWired）——同一個元素只接一次（不重建、不孤兒化計時器），
     新建的元素一定會被接上，並由 apply() 把 peWin 重設成這一次的預設視窗。*/
  function wirePeWin(el, r, redraw) {
    if (!r || !r.dates || r.dates.length < 30) return;
    const box = $('#peEnd', el); if (!box || box._peWired) return;
    const lenBox = $('#peLen', el);
    const N = r.dates.length;
    let len = 60, end = 100;                          // len＝幾個交易日，end＝截止百分比
    const apply = () => {
      const span = Math.max(2, Math.min(100, len / N * 100));
      peWin = { start: Math.max(0, end - span), end };
      redraw();
    };
    if (lenBox) {
      A.rangeBar(lenBox, { min: 20, max: N, value: Math.min(N, 120), key: 'tw.pe.len',
        label: '看多長', fmt: (v) => v + ' 天',
        onChange: (v) => { len = v; apply(); } });
      len = Math.min(N, 120);
    }
    A.playBar(box, { min: 10, max: 100, value: 100, key: 'tw.pe.end',
      label: '截止', fmt: (v) => (v >= 100 ? '最新' : (r.dates[Math.round((v / 100) * (N - 1))] || '')),
      onChange: (v) => { end = v; apply(); } });
    box._peWired = true;
    apply();
  }

  /* ★ 2026-10-02（Andy #stock/1709：「中間那條本益比線的粗細可以調整」，DECISIONS #295）：
     河流圖中間那條收盤線的寬度，工具列「線寬」滑桿 1～5px（0.5 一格），存 localStorage tw.peLineW。
     沒調過＝改前的口徑（設定面板的本益比線寬 w ＋ 0.8，預設 1.8px），所以沒碰過滑桿的人畫面不變。
     只管河流圖這一條線；上面 K 線的本益比帶仍吃設定面板的 w。*/
  const PE_LW_KEY = 'tw.peLineW';
  function peLineW(S) {
    let v = null;
    try { v = parseFloat(localStorage.getItem(PE_LW_KEY)); } catch (e) { /* 私密視窗 */ }
    if (v >= 1 && v <= 5) return v;
    return (S && S.w ? S.w : 1) + 0.8;
  }
  function drawPeRiver(id, r0, mode, st) {
    const S = st || peStyle(null), ZN = S.zones;
    if (!r0) { A.empty(id, '財報不足四季'); return; }
    const r = sliceRiver(r0, peWin);
    const maxClose = Math.max(...r.close), minClose = Math.min(...r.close);
    const lab = (i) => `${r.mult[i]} 倍`;
    let series, yMin, yMax;

    if (mode === 'mult') {
      /* 倍數線：只有線，線尾直接標倍數（Goodinfo 那張圖的讀法）。
         上下界只看收盤與五條線本身 —— 不要留色帶模式那塊「警示區」的空間，
         不然五條線會全部擠在畫面下半部。*/
      yMin = Math.floor(Math.min(minClose, Math.min(...r.bands[0])) * 0.95);
      yMax = Math.ceil(Math.max(maxClose, Math.max(...r.bands[4])) * 1.04);
      series = r.bands.map((b, i) => ({
        name: lab(i), type: 'line', data: b, symbol: 'none', silent: true, z: 2, smooth: 0.3,
        lineStyle: { color: ZN[i + 1].c, width: S.w + 0.2, type: 'dashed' },
      }));
    } else {
      /* 色帶：堆疊面積，一層一個評價區間。
         兩種：
         - `band` 半透明，看得到底下的格線（fugle 那張圖的讀法）
         - `fill` 整片填滿、不透明（財報狗 PE 區間評價法，Andy 2026-09-16 給的圖四）
           填滿之後帶與帶之間要有一條細的分隔線，不然六塊顏色黏成一片分不出界線。*/
      const solid = mode === 'fill';
      /* 填滿模式用**自己那一個**透明度（S.of），不是跟色帶共用再夾一個下限。
         之前寫成 Math.max(0.8, S.o/100)：滑桿從 5% 拉到 80% 畫面完全沒反應，
         等於 Andy 要的「可以調整透明度」在填滿模式下是壞的。*/
      const op = solid ? S.of / 100 : S.o / 100;
      const top = r.bands[4].map(v => Math.max(v * 1.18, maxClose * 1.03));
      yMin = Math.floor(Math.min(minClose, Math.min(...r.bands[0])) * 0.93);
      yMax = Math.ceil(Math.max(maxClose, Math.max(...r.bands[4]) * 1.05) * 1.02);
      const diff = (a, b) => a.map((v, i) => +(v - b[i]).toFixed(2));
      const layers = [r.bands[0], diff(r.bands[1], r.bands[0]), diff(r.bands[2], r.bands[1]),
        diff(r.bands[3], r.bands[2]), diff(r.bands[4], r.bands[3]), diff(top, r.bands[4])];
      series = layers.map((d, i) => ({
        name: ZN[i].name, type: 'line', data: d, stack: 'pe', symbol: 'none', silent: true, smooth: 0.3,
        /* ★ 2026-09-28：色帶模式每一帶的上緣描一條同色實線（最上面那塊是畫面留白，不描）——
           半透明的兩塊相鄰時邊界靠的是這條線，不是靠兩塊透明色的差。*/
        lineStyle: solid ? { color: 'rgba(0,0,0,.26)', width: 1 } : (i < 5 ? { color: ZN[i].c, width: 1.2, opacity: 0.95 } : { width: 0 }),
        areaStyle: { color: ZN[i].c, opacity: op }, z: 1,
      }));
    }
    /* 收盤線。以前寫死白色 —— 淺色主題的圖表底色就是白的，那條線直接消失
       （Andy 2026-09-16「切換回白色 UI 後需要更改的顏色」）。
       改成：深色主題白線、淺色主題深墨線；填滿模式再描一圈相反色的外框，
       不然線壓在實色帶上還是會被吃掉。*/
    const light = document.documentElement.getAttribute('data-theme') === 'light';
    const closeC = light ? '#10182e' : '#ffffff';
    if (mode === 'fill') {
      series.push({ name: '收盤外框', type: 'line', data: r.close, symbol: 'none', z: 5, silent: true,
        lineStyle: { color: light ? 'rgba(255,255,255,.75)' : 'rgba(0,0,0,.55)', width: peLineW(S) + 2.6 } });   // 外框永遠比收盤線粗 2.6（改前 w+3.4＝(w+0.8)+2.6）
    }
    series.push({ name: '收盤', type: 'line', data: r.close, symbol: 'none', z: 6, silent: true,
      lineStyle: { color: closeC, width: peLineW(S) } });
    /* Y 軸手動範圍（拖曳左側價格軸縮放，見 wirePeYAxis）：有設就蓋過自動算的上下界；自動值留著給拖曳當起點。*/
    const autoY = { min: yMin, max: yMax };
    if (peY) { yMin = peY.min; yMax = peY.max; }

    /* X 軸：以前每隔幾根就印一次 `YYYY-MM`，同一個月連印三四次「2026-04、2026-04…」。
       改成只在**每個月的第一個交易日**落刻度，月份太多時再每 N 個月取一個，整條軸最多約 8 個。*/
    const mStart = []; r.dates.forEach((d, i) => { if (!i || String(d).slice(0, 7) !== String(r.dates[i - 1]).slice(0, 7)) mStart.push(i); });
    const stepM = Math.max(1, Math.ceil(mStart.length / 8));
    const tickAt = new Set(mStart.filter((_, k) => k % stepM === 0));
    const inst = A.chart(id, {
      grid: { left: 56, right: 62, top: 24, bottom: 34 },
      tooltip: { ...A.tip, trigger: 'axis', formatter: (ps) => {
        const i = ps[0].dataIndex, c = r.close[i], e = r.eps[i], pe = e > 0 ? c / e : null;
        let z = 0; while (z < r.mult.length && pe >= r.mult[z]) z++;
        return `<b>${r.dates[i]}</b><br>收盤 ${A.fmt.n(c)}　近四季 EPS ${A.fmt.n(e)}<br>`
          + `本益比 <b>${pe != null ? A.fmt.n(pe, 1) : '—'}</b> 倍　`
          + `<span style="color:${ZN[z].c}">${ZN[z].name}</span><br>`
          + r.mult.map((m, k) => `${m} 倍 ＝ ${A.fmt.n(m * e)}`).join('　');
      } },
      xAxis: { ...A.axisStyle, type: 'category', data: r.dates, boundaryGap: false,
        axisLabel: { color: A.CH.ink3, fontFamily: A.NUM_FONT, interval: (i) => tickAt.has(i), formatter: (v) => String(v).slice(0, 7) } },
      // showMinLabel:false —— 下界是算出來的（例如 816），緊貼著 900 那格會疊成「900／816」兩行
      yAxis: { ...A.axisStyle, min: yMin, max: yMax, axisLabel: { color: A.CH.ink3, fontFamily: A.NUM_FONT, showMinLabel: false } },
      series,
      // 一定要 notMerge：兩種模式的 series 數量與型態都不一樣，
      // 用合併的話切到「倍數線」時，上一次的色帶還留在圖上（實測就是這樣糊成一片）
    }, { notMerge: true });
    if (inst) { inst._peAutoY = autoY; inst._peY = { min: yMin, max: yMax, manual: !!peY }; }
    wirePeYAxis(id, () => drawPeRiver(id, r0, mode, st));
    /* 右側的倍數／區間名稱：以前用每條 series 的 endLabel，ECharts 的 moveOverlap 管不到 endLabel，
       「價值」「低估」兩個字疊在一起。改成自己排：算出每一塊（或每一條線）在最後一天的中點，
       由上往下排、兩兩至少隔 14px，擠不進圖框的那個就不印（滑過 tooltip 仍看得到區間名）。*/
    const last = r.dates.length - 1;
    const items = mode === 'mult'
      ? r.bands.map((b, i) => ({ v: b[last], t: lab(i), c: ZN[i + 1].c }))
      : ZN.map((z, i) => {
        const lo = i === 0 ? Math.max(yMin, 0) : r.bands[i - 1][last];
        const hi = i < 5 ? r.bands[i][last] : yMax;
        return { v: (lo + hi) / 2, t: z.name, c: mode === 'fill' ? A.CH.ink : z.c };
      });
    peSideLabels(inst, items);
  }
  function peSideLabels(inst, items) {
    if (!inst || !items.length) return;
    let sig = '';
    /* ★ 2026-10-04（Andy：「河流圖縮放後右側多了『警示』」）：根因是上一次呼叫留下的計時器（150ms 去抖動）還沒跑，
       它拿的是上一次（全段、Y 軸較大）的 items，晚一步把標籤蓋回舊的（少了「警示」）；之後任何重排（滾輪縮放、切分頁）
       才由新的 items 排對，看起來就像「縮放後多了一個標籤」。每次呼叫發一個世代號，舊世代的 place 一律不做事。*/
    const gen = inst._peSideGen = (inst._peSideGen || 0) + 1;
    clearTimeout(inst._peSideT);
    const place = () => {
      if (inst.isDisposed && inst.isDisposed()) return;
      if (inst._peSideGen !== gen) return;
      const H = inst.getHeight(), W = inst.getWidth();
      const top = 26, bot = H - 36, gap = 15;          // 設計 v4 2B：字 11 → 12px，行距 14 → 15（不互疊）
      let xs; try { xs = inst.convertToPixel({ xAxisIndex: 0 }, inst.getOption().xAxis[0].data.length - 1); } catch (e) { return; }
      const pts = items.map(it => {
        let y = null; try { y = inst.convertToPixel({ yAxisIndex: 0 }, it.v); } catch (e) { /* 忽略 */ }
        return { ...it, y };
      }).filter(p => p.y != null && isFinite(p.y) && p.y >= top - 6 && p.y <= bot + 6).sort((a, b) => a.y - b.y);
      // 往下推開 → 超出底線的往上推 → 還是超出圖框的就不印
      for (let i = 0; i < pts.length; i++) pts[i].y = Math.max(pts[i].y, i ? pts[i - 1].y + gap : top);
      for (let i = pts.length - 1; i >= 0; i--) pts[i].y = Math.min(pts[i].y, i < pts.length - 1 ? pts[i + 1].y - gap : bot);
      const keep = pts.filter(p => p.y >= top - 0.5 && p.y <= bot + 0.5);
      const s2 = W + 'x' + H + '|' + keep.map(p => p.t + '@' + Math.round(p.y)).join(',');
      if (s2 === sig) return;
      sig = s2;
      inst._peSide = keep.map(p => ({ t: p.t, y: Math.round(p.y) }));      // 驗收讀這個
      inst.setOption({ graphic: keep.map((p, k) => ({ type: 'text', id: 'peside' + k, silent: true, z: 20,
        x: Math.min(xs + 5, W - 4), y: p.y,
        style: { text: p.t, fill: p.c, font: '600 12px "Noto Sans TC", sans-serif', textVerticalAlign: 'middle', textAlign: 'left' } })) },
      { replaceMerge: ['graphic'] });
    };
    /* 'finished' 在滾輪放大時每一格都會發；每次都當場 setOption 會多一輪重畫，
       連續滾動時會拖慢到讓 wheelZoom 的 450ms 緩衝失效（整頁被帶著捲）。所以停手 150ms 才重排。*/
    inst.off('finished', inst._peSideFn);
    inst._peSideFn = () => { clearTimeout(inst._peSideT); inst._peSideT = setTimeout(place, 150); };
    inst.on('finished', inst._peSideFn);
    place();
  }

  /* ★ 2026-10-03（Andy：「本益比（每季）部分個股畫壞」，DECISIONS #303）
     根因（抽樣 3105 穩懋、3081 聯亞、3707 漢磊、6919 康霈、2330 台積電對照；管線 pe_history 算得是對的，壞在畫法）：
       ① 線中間斷段：虧損季（近四季 EPS ≤ 0）管線給 pe＝null，線就斷開，圖上卻什麼都沒寫 ——
          3105 的 2023Q2～Q4、2025Q2 四季，3081 的 2023Q3～2024Q4 六季。讀者看到的是「資料壞了」，不是「這幾季在虧錢」。
       ② 衝到 500 的帶狀尖峰：TTM EPS 只剩一點點（3105 2025Q3 的 TTM 0.74 元），本益比對股價極度敏感；
          帶的上緣＝那一季每天本益比的最高（收盤從 120 漲到 390.5 → 527.7 倍），線卻是那一季第一天（162.2 倍），
          ECharts 自動 Y 軸就被撐到 600，其他季（15～100 倍）全擠在底部。3707 2021Q3 的 TTM 0.01 元更到 16,550 倍。
     修法（前端，管線不動）：
       · 灰底＋「虧損」：虧損季整格灰底、只在每一段連續虧損的第一格寫字；提示框寫「虧損（近四季 EPS -0.53 元），不計本益比」
       · 圖上限 cap＝max(200, 近 5 年第 75 百分位 × 1.5)，最多 1000：一般股票永遠不會被截（200 倍以下照畫）；
         整段歷史就是高本益比的（3081 近一年 240～350 倍）上限跟著抬到 435，不會整段貼在天花板；只有真正的離群值被截。
         超過的值（線或帶）畫在上限、上面放 ▲；提示框照寫實際值與「超出圖上限」。
       · 線與帶同一口徑：本來就是同一條逐日本益比（同一個 TTM，線＝第一天、帶＝整季高低），
         現在兩者一起被截、一起在虧損季留空 —— 不會出現「線在 160、帶衝到 527」那種一個被截一個沒被截的畫面。*/
  const PEQ_FLOOR = 200, PEQ_CEIL = 1000;
  function peQModel(pe) {
    const ok = pe.filter(r => r.pe != null && isFinite(r.pe)).map(r => +r.pe).sort((a, b) => a - b);
    const qtl = (p) => { if (!ok.length) return null; const i = (ok.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i); return ok[lo] + (ok[hi] - ok[lo]) * (i - lo); };
    const p75 = qtl(0.75), med = qtl(0.5);
    const cap = Math.round(Math.min(PEQ_CEIL, Math.max(PEQ_FLOOR, p75 != null ? p75 * 1.5 : PEQ_FLOOR)));
    const clip = (v) => (v == null || !isFinite(v) ? null : Math.min(+v, cap));
    const loss = pe.map(r => r.pe == null);
    const over = pe.map(r => !!r && r.pe != null && Math.max(+r.pe, r.pe_high != null ? +r.pe_high : 0) > cap);
    return { cap, med, loss, over, clip, nLoss: loss.filter(Boolean).length, nOver: over.filter(Boolean).length };
  }
  /* ★ 2026-10-04（Andy：「虧損可以呈現負值上去」）：虧損季不再灰底留空，改畫負本益比＝財報可用日收盤 ÷ 近四季 EPS（EPS<0 → 負值）。
     · 管線 pe_history 對虧損季給 pe＝null（只留 ttm_eps 與 from），所以負值在前端用日 K 收盤自己算；管線不動。
       from 那天不是交易日 → 取那天之前最近一個收盤；EPS 剛好 0 → 除不了，照舊留空。
     · 負值同樣有上限：EPS 只剩 -0.07 元時會到 -2000 倍，下限＝−cap，超過的畫在下緣、放綠色 ▼，提示框照寫實際值。
     · 負值點用綠色（台股慣例綠＝不好），提示框註明「虧損（近四季 EPS 為負）」；帶（每天高低）仍只畫獲利季。
     · 中位數仍只拿獲利季算（負本益比沒有「便宜／貴」的意義），所以 peQModel 不動。*/
  function drawPeQ(pe, el, daily) {
    const nt = $('#peQNote', el);
    if (!pe.length) { A.empty('peQ', '需要四季連續財報'); if (nt) nt.textContent = ''; return; }
    const m = peQModel(pe);
    const x = (v) => (v == null ? '—' : A.fmt.n(v, 1));
    const lo = pe.map(r => m.clip(r.pe_low)), hi = pe.map(r => m.clip(r.pe_high));
    const dd = daily || [];
    const closeAt = (d) => { if (!d) return null; let c = null; for (const b of dd) { if (String(b[0]).slice(0, 10) > d) break; if (b[4] != null) c = +b[4]; } return c; };
    const neg = pe.map(r => (r && r.pe == null && r.ttm_eps != null && r.ttm_eps < 0 ? (() => { const c = closeAt(r.from); return c != null ? c / r.ttm_eps : null; })() : null));
    const negClip = neg.map(v => (v == null ? null : Math.max(v, -m.cap)));
    const nNeg = neg.filter(v => v != null).length, nUnder = neg.filter(v => v != null && v < -m.cap).length;
    /* 線：獲利季畫正值、虧損季畫負值，連成同一條（Andy 要看到「掉到負的」那段走勢） */
    const line = pe.map((r, i) => (r.pe != null ? m.clip(r.pe) : negClip[i]));
    const el0 = document.getElementById('peQ');
    if (el0) { el0.dataset.cap = m.cap; el0.dataset.nloss = m.nLoss; el0.dataset.nover = m.nOver; el0.dataset.nneg = nNeg; }
    A.chart('peQ', {
      tooltip: { ...A.tip, trigger: 'axis', formatter: ps => { const i = ps[0].dataIndex, r = pe[i]; if (!r) return '';
        if (r.pe == null) return `<b>${r.period}</b><br>${neg[i] != null ? `本益比 <b style="color:${A.CH.down || '#2fbf71'}">${x(neg[i])}</b> 倍${neg[i] < -m.cap ? `（超出圖下限 −${m.cap} 倍，畫在下緣 ▼）` : ''}<br>` : ''}虧損（近四季 EPS 為負${r.ttm_eps != null ? '，' + A.fmt.n(r.ttm_eps, 2) + ' 元' : ''}）${r.from ? `<br><small>＝${r.from} 收盤 ÷ 近四季 EPS</small>` : ''}`;
        const ov = m.over[i];
        return `<b>${r.period}</b><br>本益比 ${x(r.pe)} 倍${r.pe > m.cap ? `（超出圖上限 ${m.cap} 倍，圖上畫在上緣 ▲）` : ''}<br>`
          + `這一季每天的區間 ${x(r.pe_low)}–${x(r.pe_high)} 倍${ov && !(r.pe > m.cap) ? `（上緣超出圖上限 ${m.cap} 倍）` : ''}<br>`
          + `近四季 EPS ${r.ttm_eps != null ? A.fmt.n(r.ttm_eps, 2) + ' 元' : '—'}${r.from ? `<br><small>線＝${r.from} 收盤（財報可用日）</small>` : ''}`; } },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { ...A.axisStyle, type: 'category', data: pe.map(r => r.period), axisLabel: { color: A.CH.ink3, hideOverlap: true } },
      yAxis: { ...A.axisStyle, scale: true },
      series: [
        { name: '區間', type: 'line', data: lo, lineStyle: { opacity: 0 }, stack: 'pe', showSymbol: false, z: 2 },
        { name: '高低', type: 'line', data: hi.map((h, i) => (h != null && lo[i] != null ? h - lo[i] : null)), lineStyle: { opacity: 0 }, stack: 'pe', areaStyle: { color: 'rgba(139,123,255,.2)' }, showSymbol: false, z: 2 },
        { name: '本益比', type: 'line', data: line, connectNulls: false, lineStyle: { color: '#8b7bff', width: 2 },
          itemStyle: { color: (p) => (neg[p.dataIndex] != null ? (A.CH.down || '#2fbf71') : '#8b7bff') }, symbolSize: 6, z: 3,
          markLine: nNeg ? { silent: true, symbol: 'none', label: { show: false }, lineStyle: { color: A.CH.ink3, type: 'dashed', width: 1 }, data: [{ yAxis: 0 }] } : undefined },
        { name: '超出範圍', type: 'scatter', data: m.over.map(o => (o ? m.cap : null)), symbol: 'triangle', symbolSize: 10, itemStyle: { color: A.CH.amber }, z: 4 },
        { name: '低於下限', type: 'scatter', data: neg.map(v => (v != null && v < -m.cap ? -m.cap : null)), symbol: 'triangle', symbolRotate: 180, symbolSize: 10, itemStyle: { color: A.CH.down || '#2fbf71' }, z: 4 },
      ],
    }, { notMerge: true });
    /* 圖下一行：中位數（跟自己的過去比）＋這張圖哪裡被特別處理（有才寫） */
    if (nt) {
      const parts = [m.med != null ? `近 ${pe.length} 季中位 <b>${x(m.med)}</b> 倍` : `近 ${pe.length} 季都在虧損，算不出本益比中位`];
      if (nNeg) parts.push(`綠點＝虧損 ${nNeg} 季（負值）`);
      if (m.nLoss > nNeg) parts.push(`${m.nLoss - nNeg} 季 EPS 為 0，留空`);
      if (m.nOver) parts.push(`▲＝超過圖上限 ${m.cap} 倍`);
      if (nUnder) parts.push(`▼＝低於 −${m.cap} 倍`);
      nt.innerHTML = parts.join('；');
    }
  }

  function tabProfit(pg, el) {
    const q = (pg.profit || {}).quarters || [];
    /* ★ 2026-09-26（小數點普查）：3504、6226 各有一季 ttm_eps 捨入後是 0.00、本益比卻是 5.3e+18 ——
       四季 EPS 相加的浮點殘差（例如 0.1＋(-0.3)＋0.2＝5.5e-17）被當成「正的 TTM」拿去除。
       資料端已修（pe_daily 先捨入再判正負），這裡再守一層：TTM 捨入後 ≤ 0 的季一律當虧損季、不給本益比，
       跟卡片說明「虧損（EPS ≤ 0）那季不算」同一個口徑。*/
    const pe = (pg.pe_history || []).map(r => (r && !(r.ttm_eps > 0) ? { ...r, pe: null, pe_high: null, pe_low: null } : r));
    if (!q.length) { el.innerHTML = '<div class="card"><div class="empty">尚無季報資料</div></div>'; return; }
    /* ★ 2026-09-27（個股頁數據普查）：payload 現在把缺的季補成空列（季標籤連續），最新一列一定有資料；
       保險起見仍取「最後一列有 EPS 或營收的」。年度（yearly）與法定期限判定（timing）由管線算（stockpage.profit_series）。*/
    const lastQ = q.slice().reverse().find(r => r[5] != null || r[1] != null) || q[q.length - 1];
    const last = lastQ;
    const yr = (pg.profit || {}).yearly || [];
    const tm = (pg.profit || {}).timing || null;
    const ylab = (y) => y.partial ? `${y.year}（前 ${y.quarters} 季）` : String(y.year);
    /* ★ 2026-10-06（Andy：「這類資訊一律拿掉」，DECISIONS #329）：正常（ok）時副標不再寫「財報到 X（至 YYYY-MM-DD 法定應有到 X）」；
       只有「法定期限已過卻缺季」「季底還沒到卻有資料」這兩種**資料出錯**的警示留著 —— 那是警告，不是資料日期。*/
    const tmTxt = tm ? (tm.status === 'ok' ? ''
      : tm.status === 'missing' ? `⚠ 法定期限已過、應有 ${tm.expected}，目前只到 ${tm.latest || '—'}`
      : `⚠ ${tm.latest} 的季底還沒到，資料有誤`) : '';
    /* ★ 2026-10-03（Andy：「本益比（這邊的算法需要新增到獲利那邊）」，DECISIONS #305）：總覽基本面卡的「本益比位置」
       （目前本益比在自己歷史每日本益比的第幾百分位、便宜端／貴端、族群中位）放進「本益比（每季）」卡的圖上方。
       同一支 peStand(pg)＋peStandHTML 畫，兩邊數字一定一樣（_uitest「獲利並排本益比1003」逐項比 data-*）。*/
    const psProf = `<div class="psprof"><div class="psh">本益比位置 <small>跟自己過去每天的本益比比</small></div>${peStandHTML(peStand(pg), 'peStandProf')}</div>`;
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">最新季度</div><div class="v">${lastQ[0]}</div></div><div class="k"><div class="l">單季 EPS</div><div class="v">${A.fmt.n(last[5])}</div></div><div class="k"><div class="l">年度累計 EPS</div><div class="v">${A.fmt.n(last[6])}</div></div><div class="k"><div class="l">EPS 年增（元）</div><div class="v ${A.fmt.cls(last[7])}">${last[7] != null ? (last[7] > 0 ? '+' : '') + A.fmt.n(last[7]) : '—'}</div></div><div class="k"><div class="l">毛利率</div><div class="v">${last[2] == null ? "—" : A.fmt.n(last[2], 2) + "%"}</div></div><div class="k"><div class="l">營益率</div><div class="v">${last[3] == null ? "—" : A.fmt.n(last[3], 2) + "%"}</div></div><div class="k"><div class="l">淨利率</div><div class="v">${last[4] == null ? "—" : A.fmt.n(last[4], 2) + "%"}</div></div></div>
      <div class="grid skprof" id="profGrid"><div class="card" id="peRiverCard"><div class="row spread"><h3>本益比河流圖 ${hq('pe', '本益比河流圖')}</h3>
        <!-- 2026-10-06：免責那一行（A.disc('pe')）排在控制鈕後面：這一列控制鈕很寬，排在中間會把標題與控制鈕擠成三行 -->
        <div class="row" style="gap:10px;align-items:center">
          <div class="seg" id="peMode"><button data-v="band">色帶分區</button><button data-v="fill">填滿</button><button data-v="mult">倍數線</button></div>
          <label class="opabox" title="色帶透明度（跟上面 K 線的本益比帶共用同一組設定）">透明度
            <input id="peOpa" type="range" min="10" max="100" step="5"><span class="val" id="peOpaV"></span></label>
          <label class="opabox" title="中間那條收盤線的粗細（1～5px，記在這台瀏覽器）">線寬
            <input id="peLw" type="range" min="1" max="5" step="0.5"><span class="val" id="peLwV"></span></label>
          <button type="button" class="btn small" id="peYReset" hidden title="Y 軸回到自動範圍（在左側價格軸上雙擊也可以）">Y 軸還原</button>
        </div>${A.disc ? A.disc('pe') : ''}</div>
        <div class="row" style="gap:12px;flex-wrap:wrap;margin-bottom:6px">
          <div id="peLen" title="這張圖一次看多長一段"></div>
          <div id="peEnd" title="截止到哪一天：往回拉看以前的評價，按 ▶ 一天一天播"></div>
        </div>
        <div class="howtxt" id="how-pe" hidden>${A.howHTML('市場現在給這一檔幾倍的評價。', [
          '每條帶＝近四季 EPS × 倍數，越紅越貴',
          '收盤線落在哪條帶＝市場現在給的評價',
          '倍數用這檔自己的歷史分位，非固定',
          '左側 Y 軸上下拖曳或滾輪縮放，雙擊還原',
        ], '倍數不是寫死的 15／20／25 倍。右上三種畫法：色帶分區（顏色越紅評價越高）／填滿（整片實色，一眼看出收盤線落在哪一塊）／倍數線（線尾標本益比倍數）；透明度跟上面 K 線的本益比帶共用。')}</div>
        <div id="peWrap"><div id="peChart" class="chart" style="height:340px"></div></div><div class="pekvs" id="peNote" data-readout></div></div>
      <div class="card" id="peQCard"><h3>本益比（每季）${hq('skpeq', '本益比（每季）')}</h3>${hbox('skpeq', ['線＝財報可用日收盤 ÷ 近四季 EPS', '帶＝同一季每天的本益比高低', '綠點＝虧損季（EPS < 0），本益比畫成負值', '▲＝超過圖上限，游標看實際值', '跟自己的過去比，看現在貴不貴'], '線與帶是同一條逐日本益比：線取那一季第一天（財報可用日），帶是那一季每天的最低～最高。圖上限＝max(200 倍, 近 5 年第 75 百分位 × 1.5)，最多 1000 倍。')}${psProf}<div id="peQ" class="chart"></div><div class="note" id="peQNote" data-readout></div></div>
      <div class="card" id="profitCard"><div class="row spread"><h3>EPS 與三率 ${hq('skeps', 'EPS 與三率')} <small id="profitSub" data-readout>${A.fmt.esc(tmTxt)}</small></h3><div class="seg" id="profitMode" role="group" aria-label="季或年"><button type="button" data-v="q">季</button><button type="button" data-v="y">年</button></div></div>${hbox('skeps', ['柱＝EPS（左軸）；線＝三率（右軸）', '季＝單季；年＝四季相加', '今年未滿四季標「前 n 季」', '缺季留空，不拿別季湊'], '財報法規是季報，所以只有單季、沒有每月。年度三率＝全年毛利 ÷ 全年營收（不是四季比率平均）。')}<div id="profitChart" class="chart"></div></div>
      <div class="card tblcard" id="profitTblCard"><h3><span id="profitTblTtl">季報明細</span> ${hq('skproftbl', '季報明細')}</h3>${hbox('skproftbl', ['季＝單季數字；年＝四季相加，「季數」不滿 4＝還沒過完', '累計 EPS＝同一年 Q1 起逐季相加，跨年歸零', '中間缺一季，那季起的累計留「—」，不拿缺季湊', 'EPS 年增＝這季 EPS 減去年同季（元）', '營收、淨利的單位寫在數字後（億／萬）'])}<div class="tw" style="max-height:360px" id="profitTbl"></div></div></div>`;
    const pct = (v) => (v == null ? '—' : A.fmt.n(v, 2) + '%');
    const tblQ = () => `<table><thead><tr><th class="l">季度</th><th>營收</th><th>毛利率</th><th>營益率</th><th>淨利率</th><th>淨利</th><th>EPS</th><th>累計 EPS</th><th>EPS 年增</th></tr></thead><tbody>${q.slice().reverse().map(r => `<tr><td class="l mono">${r[0]}</td><td class="num">${r[1] == null ? '—' : A.fmt.yi(r[1])}</td><td class="num">${pct(r[2])}</td><td class="num">${pct(r[3])}</td><td class="num">${pct(r[4])}</td><td class="num">${r[8] == null ? '—' : A.fmt.yi(r[8])}</td><td class="num">${r[5] == null ? '—' : A.fmt.n(r[5])}</td><td class="num">${r[6] == null ? '—' : A.fmt.n(r[6])}</td><td class="num ${A.fmt.cls(r[7])}">${r[7] != null ? (r[7] > 0 ? '+' : '') + A.fmt.n(r[7]) : '—'}</td></tr>`).join('')}</tbody></table>`;
    const tblY = () => `<table><thead><tr><th class="l">年度</th><th>營收</th><th>毛利率</th><th>營益率</th><th>淨利率</th><th>淨利</th><th>EPS</th><th>季數</th></tr></thead><tbody>${yr.slice().reverse().map(y => `<tr><td class="l mono">${ylab(y)}</td><td class="num">${y.revenue == null ? '—' : A.fmt.yi(y.revenue)}</td><td class="num">${pct(y.gm)}</td><td class="num">${pct(y.om)}</td><td class="num">${pct(y.nm)}</td><td class="num">${y.net_income == null ? '—' : A.fmt.yi(y.net_income)}</td><td class="num">${y.eps == null ? '—' : A.fmt.n(y.eps)}</td><td class="num">${y.quarters}</td></tr>`).join('')}</tbody></table>`;
    /* ★ 2026-09-26（小數點普查）：以前沒寫 formatter，提示框只印原值、沒有單位 —— EPS 補「元」、三率補「%」，位數跟下方季報明細表一致（EPS 2 位、三率 1 位）。*/
    let pmode = 'q';
    try { const v = localStorage.getItem('tw.profitMode'); if (v === 'q' || v === 'y') pmode = v; } catch (e) { /* 私密視窗 */ }
    const drawProfit = () => {
      const isY = pmode === 'y' && yr.length;
      const X = isY ? yr.map(ylab) : q.map(r => r[0]);
      const E = isY ? yr.map(y => y.eps) : q.map(r => r[5]);
      const M = (k, i) => (isY ? yr.map(y => y[k]) : q.map(r => r[i]));
      el.dataset.profitMode = isY ? 'y' : 'q';
      $$('#profitMode button', el).forEach(b => b.classList.toggle('on', b.dataset.v === (isY ? 'y' : 'q')));
      const tt = $('#profitTblTtl', el); if (tt) tt.textContent = isY ? '年度明細' : '季報明細';
      const tb = $('#profitTbl', el); if (tb) tb.innerHTML = isY ? tblY() : tblQ();
      const pc = A.chart('profitChart', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${p.value == null ? '—' : p.seriesName === 'EPS' ? A.fmt.n(p.value, 2) + ' 元' : A.fmt.n(p.value, 1) + '%'}`).join('<br>') }, legend: { show: false, type: 'scroll' }, grid: { left: 50, right: 50, top: 10, bottom: 30 },
        xAxis: { ...A.axisStyle, type: 'category', data: X, axisLabel: { color: A.CH.ink3, hideOverlap: true } }, yAxis: [{ ...A.axisStyle }, { ...A.axisStyle, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }],
        series: [{ name: 'EPS', type: 'bar', itemStyle: { color: 'rgba(255,77,109,.7)' }, data: E.map(v => ({ value: v, itemStyle: { color: v >= 0 ? 'rgba(255,77,109,.7)' : 'rgba(46,229,157,.7)', borderRadius: [3, 3, 0, 0] } })) }, { name: '毛利率', type: 'line', yAxisIndex: 1, data: M('gm', 2), smooth: .3, showSymbol: isY, connectNulls: false, lineStyle: { color: '#ffd166' }, itemStyle: { color: '#ffd166' } }, { name: '營益率', type: 'line', yAxisIndex: 1, data: M('om', 3), smooth: .3, showSymbol: isY, connectNulls: false, lineStyle: { color: '#3ee0ff' }, itemStyle: { color: '#3ee0ff' } }, { name: '淨利率', type: 'line', yAxisIndex: 1, data: M('nm', 4), smooth: .3, showSymbol: isY, connectNulls: false, lineStyle: { color: '#8b7bff' }, itemStyle: { color: '#8b7bff' } }] }, { notMerge: true });
      /* 設計 v4 2B：圖例搬到標題列最右端（季／年後面，放不下自己換行）；原本寫在左軸頂上的「EPS」字樣（佔繪圖區上方一行）併進圖例：EPS（元，左軸） */
      const pm = $('#profitMode', el);
      /* ★ 2026-10-02（DECISIONS #295）：放不下退回 ECharts 圖例時，以前會把左軸頂上的「EPS」還原 ——
         390 寬圖例佔滿整行，那個「EPS」跟圖例第一顆「EPS」疊在一起（_uitest「個股分頁版面1002」用 SVG 量到）。
         改成跟 HTML 圖例同一個講法：軸名不畫、圖例第一顆寫「EPS（元，左軸）」；圖例單行可捲，不會折兩行壓到繪圖區。
         （option 一開始就是 legend.type:'scroll'，理由同營收「逐年同月比較」：退回時換 type 會丟掉藏起來的那幾條。）*/
      if (pm) extLegend(pc, pm.parentElement, { labels: { EPS: 'EPS（元，左軸）' }, dual: { EPS: ['rgba(255,77,109,.7)', 'rgba(46,229,157,.7)'] },
        fb: { top: 0, type: 'scroll', itemWidth: 14, itemGap: 8, formatter: (n) => (n === 'EPS' ? 'EPS（元，左軸）' : n),
          pageIconColor: A.CH.ink2, pageTextStyle: { color: A.CH.ink3 }, textStyle: { color: A.CH.ink2, fontSize: 12 } },
        fbTop: 36, fbOpt: { yAxis: [{ name: '' }, {}] }, okOpt: { yAxis: [{ name: '' }, {}] } });
    };
    $$('#profitMode button', el).forEach(b => b.onclick = () => {
      pmode = b.dataset.v;
      try { localStorage.setItem('tw.profitMode', pmode); } catch (e) { /* 忽略 */ }
      drawProfit();
    });
    drawProfit();
    drawPeQ(pe, el, pg.daily);

    // ---- 河流圖：兩種模式，選過就記住（換股票、重新整理都沿用）
    const river = peRiver(pg);
    peY = null;                                   // 換股票（或重進獲利分頁）Y 軸回自動：上一檔的價格區間對這一檔沒有意義
    const yRst = $('#peYReset', el);
    if (yRst) yRst.onclick = () => { peY = null; const d = $('#peChart', el); if (d && d._peRedraw) d._peRedraw(); };
    const MODES = ['band', 'fill', 'mult'];
    let mode = 'band';
    try { const s = localStorage.getItem('tw.periver'); if (MODES.includes(s)) mode = s; } catch (e) { /* 忽略 */ }
    const note = $('#peNote', el);
    /* 說明精簡（2026-09-24）：三種畫法的完整說明搬進「怎麼看 ?」（#how-pe）最下面一行；
       讀數後面只留一句短的「現在這種畫法怎麼讀」（切畫法時要跟著換，_uitest「個股」在驗）。*/
    const HOWTO = {
      band: '色帶分區：越紅評價越高',
      fill: '填滿：看收盤落在哪一塊',
      mult: '倍數線：線尾標本益比倍數',
    };
    const paint = () => {
      $$('#peMode button', el).forEach(b => b.classList.toggle('on', b.dataset.v === mode));
      const st = peStyle(state.cfg || loadCfg());
      // 透明度滑桿跟上面 K 線的本益比帶共用同一組設定（DECISIONS #145），所以每次重畫都同步一次
      // 滑桿吃的是「這個模式自己的那一個值」：色帶用 o、填滿用 of。
      // 共用一個值的話，填滿模式非得夾一個高下限才看得出是填滿，滑桿就等於壞的。
      const opa = $('#peOpa', el), opaV = $('#peOpaV', el);
      const cur = mode === 'fill' ? st.of : st.o;
      if (opa) { opa.value = cur; opa.disabled = mode === 'mult'; }   // 倍數線沒有色帶可調
      if (opaV) opaV.textContent = mode === 'mult' ? '—' : cur + '%';
      drawPeRiver('peChart', river, mode, st);
      wirePeWin(el, river, () => drawPeRiver('peChart', river, mode, peStyle(state.cfg || loadCfg())));
      const lw = $('#peLw', el), lwV = $('#peLwV', el), lwNow = peLineW(st);
      if (lw) lw.value = String(Math.round(lwNow * 2) / 2);
      if (lwV) lwV.textContent = (Math.round(lwNow * 10) / 10) + 'px';
      /* ★ 2026-10-02（Andy #stock/1709，DECISIONS #295）：改前圖下一整行用「·」串四件事，寬螢幕一行讀不完、窄畫面折成三四行；
         改成四個並排的小資訊塊：目前本益比｜落在哪一區｜歷史倍數帶｜色帶說明（六格小色票由便宜到貴＋這種畫法怎麼讀），
         窄畫面自己換行（.pekvs auto-fit）。「色帶說明」裡一定要留 HOWTO 那句 —— 切畫法時跟著換（_uitest「個股」在驗）。*/
      if (note) {
        const kv = (l, v, k) => `<div class="k" data-k="${k}"><div class="l">${l}</div><div class="v">${v}</div></div>`;
        const sw = mode === 'mult' ? '' : `<span class="zsw" aria-hidden="true">${st.zones.map(z => `<i style="background:${z.c}" title="${z.name}"></i>`).join('')}</span><small>${st.zones[0].name} → ${st.zones[st.zones.length - 1].name}</small><br>`;
        note.innerHTML = river
          ? kv('目前本益比', `<b>${A.fmt.n(river.curPe, 1)}</b> 倍 <small>近四季 EPS ${A.fmt.n(river.lastEps)} 元</small>`, 'pe')
            + kv('落在哪一區', `<b style="color:${st.zones[river.zoneIdx].c}">${river.zone.name}</b> 區 <small>第 ${river.zoneIdx + 1}／${st.zones.length} 帶，越上面越貴</small>`, 'zone')
            + kv('歷史倍數帶', `<span class="mono">${river.mult.join(' / ')}</span> <small>倍</small>`, 'mult')
            + kv(mode === 'mult' ? '倍數線說明' : '色帶說明', `${sw}${HOWTO[mode]}`, 'how')
          : '<div class="k"><div class="v">財報不足四季或近四季 EPS 為負</div></div>';
      }
    };
    $$('#peMode button', el).forEach(b => b.onclick = () => {
      mode = b.dataset.v;
      try { localStorage.setItem('tw.periver', mode); } catch (e) { /* 忽略 */ }
      paint();
    });
    /* 透明度（Andy 2026-09-16：「底下的本益比河流圖需要新增可以調整透明度」）。
       寫回 cfg.st.pe.o —— 跟設定面板裡那根滑桿、跟上面 K 線的本益比帶是同一個值，
       不然同一張圖在兩個地方會長得不一樣。*/
    const opa = $('#peOpa', el);
    if (opa) opa.oninput = () => {
      const c = state.cfg || loadCfg();
      c.st = c.st || {};
      // 色帶模式寫 o（跟上面 K 線的本益比帶共用，DECISIONS #145）；填滿模式寫自己的 of
      c.st.pe = Object.assign({}, c.st.pe, mode === 'fill' ? { of: +opa.value } : { o: +opa.value });
      state.cfg = c; saveCfg(c);
      paint();
    };
    const lwIn = $('#peLw', el);
    if (lwIn) lwIn.oninput = () => {
      const v = Math.max(1, Math.min(5, +lwIn.value || 2));
      try { localStorage.setItem(PE_LW_KEY, String(v)); } catch (e) { /* 私密視窗：這一次照樣重畫，只是不記 */ }
      paint();
    };
    /* 縮放與拖曳（Andy 2026-09-16：「具備縮放功能，游標可以抓取移動」）。
       用全站那一套 wheelZoom，不用 ECharts 的 dataZoom —— dataZoom 會把 wheel 吃掉，
       頁面就捲不動了（DECISIONS #139 已經踩過一次）。*/
    A.wheelZoom($('#peWrap', el), { onZoom: () => {
      const i = window.echarts && echarts.getInstanceByDom($('#peChart', el)); if (i) i.resize();
    } });
    paint();
  }
  /* ★ 2026-09-26（Andy：「為什麼只有一筆，幫我找找其他筆數據，沒有配就顯示空值，但需要標示年份」）
     證據：3026 禾伸堂的除權息結果（官方）2016～2026 每年都有，股利公告卻只有 114 年一筆 ——
     回補把「每日管線先寫進的那一筆今年公告」當成「已經補過」，2016 起的歷史整個被跳過（662 檔同病，
     run_backfill.already_covered 已修，下一輪回補補齊）。以前年度圖只拿公告畫，所以只剩一根。
     現在改吃管線算好的 `by_year`（口徑在 stockpage.div_year_bars）：
       · 年度＝除權息日所在的西元年，近 10 年起（不早於 2016 回補起點與上市年），每年一根
       · 沒配息的年份 0 高度、x 軸照樣標年份、柱頂寫「未配」
       · 現金（琥珀）與股票（紫）堆疊；同一年多次配息加總，提示框逐次列出
       · 含權又對不到公告的那一次金額不猜，柱頂寫「待補」、提示框講原因 */
  function divBars(dv, rs) {
    if ((dv.by_year || []).length) return dv.by_year;
    // 舊版 payload（還沒重算）退路：用除權息紀錄的年份，至少不會只剩一根
    const by = {};
    rs.forEach(r => { const y = +String(r.date).slice(0, 4); const b = by[y] || (by[y] = { year: y, cash: 0, stock: 0, n: 0, unknown: 0, items: [] });
      b.n++; b.cash += r.cash_dividend || 0; b.stock += r.stock_dividend || 0; if (r.dividend == null) b.unknown++;
      b.items.push({ date: r.date, kind: r.kind, cash: r.cash_dividend, stock: r.stock_dividend }); });
    const ys = Object.keys(by).map(Number).sort((a, b) => a - b);
    if (!ys.length) return [];
    const out = [];
    for (let y = ys[0]; y <= ys[ys.length - 1]; y++) out.push(by[y] || { year: y, cash: 0, stock: 0, n: 0, unknown: 0, items: [] });
    return out;
  }
  /* ★ 2026-09-28（Andy：「所有內容不要再出現這樣的說明，我是要給讀者看，他不需要知道這類資訊（股利政策&股利公告移除）」）：
     「股利政策（依所屬期間）」與「股利公告」兩張表整張拿掉 —— 年度圖（每年配多少）＋除權息紀錄（每一次、填息幾天）
     已經回答「這檔配得穩不穩、配完填不填得回來」；兩張表多的是公告日、所屬期間這些讀者用不到的欄位，
     還得配一段「資料來源／回補中／共 N 筆」的說明才讀得懂。後端 dividends.events／by_period 照舊產出（年度圖的拆分與 AI 分析在用）。*/
  function tabDividend(pg, el) {
    const dv = pg.dividends || {}; const ev = dv.events || [], rs = dv.results || [];
    if (!ev.length && !rs.length) { el.innerHTML = `<div class="card"><div class="empty">尚無除權息資料</div></div>`; return; }
    const bars = divBars(dv, rs);
    const cov = dv.coverage || {};
    const MF = A.NUM_FONT || 'JetBrains Mono, monospace';
    const d2 = (v) => { const x = Math.round(v * 100) / 100; return x.toFixed(Number.isInteger(x) ? 0 : 2); };
    const yrsWith = bars.filter(b => b.n > 0).length;
    /* 2026-10-05（Andy：「記得要備註花多久填息」）：跟 ETF 專區配息行事曆同一套字 ——
       已填「N 天」；沒填「尚未填息（已 N 天）」（fill_wait＝管線算的已經過交易日數，含除息日）；
       舊資料沒有 fill_wait 時，-1 仍寫「一年未填」、其餘「—」（算不出來就不猜）。*/
    const fillTxt = (r) => (r.fill_days != null && r.fill_days !== -1 ? r.fill_days + ' 天'
      : r.fill_wait != null ? `尚未填息（已 ${r.fill_wait} 天）` : r.fill_days === -1 ? '一年未填' : '—');
    const divSub = bars.length ? `${bars[0].year}～${bars[bars.length - 1].year}，${yrsWith} 年有配` : '';
    const up = dv.upcoming || [];
    const upTxt = up.length ? '已公告、尚未除權息：' + up.slice(0, 3).map(u => `${A.fmt.esc(u.period || '')} ${u.kind === 'stock' ? '股票' : '現金'} ${d2(u.amount || 0)} 元`
      + (u.ex_date ? `（${u.ex_date} 除${u.kind === 'stock' ? '權' : '息'}）` : '（除權息日未定）')).join('；') : '';
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">近四次現金股利</div><div class="v">${dv.cash_ttm != null ? A.fmt.n(dv.cash_ttm) + ' 元' : '—'}</div></div><div class="k"><div class="l">殖利率</div><div class="v">${dv.yield_ttm != null ? A.fmt.n(dv.yield_ttm) + '%' : '—'}</div></div><div class="k"><div class="l">最近除息</div><div class="v" style="font-size:15px">${rs[0] ? rs[0].date : '—'}</div></div><div class="k"><div class="l">最近填息</div><div class="v">${rs[0] ? fillTxt(rs[0]) : '—'}</div></div></div>
      <div class="grid g2"><div class="card" id="divCard"><div class="row spread" id="divHead" style="gap:8px;flex-wrap:wrap"><h3>各年度股利 <small data-readout id="divSub">${divSub}</small> ${hq('skdiv', '各年度股利')}</h3></div>${hbox('skdiv', ['每年一根：琥珀＝現金、紫＝股票股利（元／股）', '年度＝實際除權息那一年，對得上右邊紀錄表', '同一年多次配息（季配、半年配）加總', '「未配」＝沒除權息；最右是今年', '線＝現金殖利率（右軸）＝現金股利 ÷ 除息前一日收盤'], `${cov.cover_from || 2016} 年以前與上市以前的年份不畫 —— 那些是「沒有資料」，不是「沒配」。季配、半年配的股利可能跨年發放，所以歸在實際配發那一年。`)}<div id="divBar" class="chart"></div>${upTxt ? `<div class="note" data-readout style="margin-top:6px">${upTxt}</div>` : ''}</div>
      <div class="card"><h3>除權息紀錄 ${hq('skfill', '除權息紀錄')}</h3>${hbox('skfill', ['每一列＝一次除權或除息', '填息天數＝從除息日當天算第 1 個交易日，收盤第一次回到除息前一日收盤是第幾個交易日', '天數越短＝市場越認同', '「尚未填息（已 N 天）」＝到資料最後一天還沒填回、已經過 N 個交易日；「—」＝行情不足算不出來'])}<div class="tw" style="max-height:300px"><table><thead><tr><th class="l">除權息日</th><th class="l">類別</th><th>股利</th><th>前收盤</th><th>參考價</th><th>填息</th></tr></thead><tbody id="divRec">${rs.map(r => `<tr><td class="l mono">${r.date}</td><td class="l">${r.kind}</td><td class="num">${A.fmt.n(r.dividend)}</td><td class="num">${A.fmt.n(r.before_price)}</td><td class="num">${A.fmt.n(r.reference_price)}</td><td class="num" style="white-space:nowrap">${r.fill_days != null && r.fill_days !== -1 ? r.fill_days + ' 天' : `<span class="down">${fillTxt(r)}</span>`}</td></tr>`).join('') || '<tr><td colspan="6" class="l muted">—</td></tr>'}</tbody></table></div></div></div>`;
    /* ★ 2026-09-25（審查 R5）：① 字族用全站 NUM_FONT；② 數值一律最多 2 位；③ 標籤色跟主題走。*/
    if (!bars.length) { A.empty('divBar'); return; }
    const yrs = bars.map(b => String(b.year));
    const top = (b) => b.n === 0 ? '未配' : (b.cash || 0) + (b.stock || 0) > 0 ? d2((b.cash || 0) + (b.stock || 0)) : b.unknown ? '待補' : '0';
    const narrowDiv = (($('#divBar') || {}).clientWidth || 600) < 420;
    /* 設計 v4 2B：年份字 12px 一格要多寬才不疊 —— 「2009」≈ 32px、「'09」≈ 22px（12px 等寬字）。
       一格（繪圖區寬 ÷ 年數）放不下四位數就縮成 'YY（改前只有容器 < 420 才縮，1100 寬半欄卡片 18 年一格 22px，「2009」疊成一串）；
       連 'YY 都放不下（< 24px，例如 390）才直排。*/
    const divSlot = ((($('#divBar') || {}).clientWidth || 600) - 88) / Math.max(1, bars.length);
    const divShort = narrowDiv || divSlot < 34, divRot = divSlot < 24;
    const kindTxt = (k) => ({ '息': '除息', '權': '除權', '權息': '除權息' })[k] || (k || '');
    const dc = A.chart('divBar', {
      tooltip: { ...A.tip, trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: (ps) => { const b = bars[ps[0].dataIndex]; if (!b) return '';
          let h = `<b>${b.year} 年</b>${b.partial ? '（今年，還沒過完）' : ''}`;
          if (!b.n) return h + '<br>這一年沒有除權息';
          h += `<br>現金 ${d2(b.cash || 0)} 元・股票 ${d2(b.stock || 0)} 元（共 ${b.n} 次）`;
          h += (b.items || []).map(it => `<br>· ${String(it.date).slice(5)} ${kindTxt(it.kind)}`
            + (it.cash == null || it.stock == null ? '：金額未公告'
              : `：現金 ${d2(it.cash || 0)}${it.stock ? '・股票 ' + d2(it.stock) : ''}`)
            + (it.period ? `（${A.fmt.esc(it.period)}）` : '')).join('');
          if (b.cash_yield != null) h += `<br>現金殖利率 ${A.fmt.n(b.cash_yield, 2)}%（Σ 每次現金 ÷ 除息前收盤）`;
          return h; } },
      legend: { show: false, data: ['現金股利', '股票股利', '現金殖利率'] },
      /* 設計 v4 2B：12px 下限。窄（容器 < 420px）以前把年份縮成 10.5px 硬塞，改成 12px 直排（每格 15px 放得下），底部多留 8px */
      grid: { left: 44, right: 44, top: 12, bottom: divRot ? 38 : 30 },
      xAxis: { ...A.axisStyle, type: 'category', data: yrs,
        axisLabel: { color: A.CH.ink3, fontFamily: MF, interval: 0, fontSize: 12, rotate: divRot ? 90 : 0,
          formatter: (v) => divShort ? "'" + String(v).slice(2) : v } },
      yAxis: [{ ...A.axisStyle, axisLabel: { color: A.CH.ink3, fontFamily: MF, formatter: (v) => d2(v) } },
        { ...A.axisStyle, splitLine: { show: false }, axisLabel: { color: A.CH.ink3, fontFamily: MF, formatter: (v) => d2(v) + '%' } }],
      series: [
        { name: '現金股利', type: 'bar', stack: 'd', barWidth: '55%', data: bars.map(b => +(b.cash || 0).toFixed(2)),
          itemStyle: { color: A.CH.amber }, label: { show: false, fontFamily: MF, formatter: (q) => d2(q.value) } },
        { name: '股票股利', type: 'bar', stack: 'd', barWidth: '55%', data: bars.map(b => +(b.stock || 0).toFixed(2)),
          itemStyle: { color: A.CH.violet, borderRadius: [3, 3, 0, 0] } },
        /* 柱頂標籤：堆疊最上層一根 0 高度的柱子專門掛字（合計／未配／待補），不佔高度、不進圖例 */
        { name: '合計', type: 'bar', stack: 'd', barWidth: '55%', data: bars.map(() => 0), silent: true, tooltip: { show: false },
          itemStyle: { color: 'transparent' },
          labelLayout: divShort ? { hideOverlap: true } : undefined,   // 格子窄時柱頂數字（12.50、10.50…）互相疊，疊到的先藏（滑過提示框照樣有）
          label: { show: true, position: 'top', fontFamily: MF, fontSize: 12,
            color: A.CH.ink2, formatter: (q) => top(bars[q.dataIndex]) } },
        /* 現金殖利率線放在最後：驗收（DIV_PROBE）照索引讀 series[0]＝現金、[1]＝股票 */
        { name: '現金殖利率', type: 'line', yAxisIndex: 1, data: bars.map(b => (b.cash_yield == null ? null : +b.cash_yield.toFixed(2))), symbolSize: 5, connectNulls: false, z: 5,
          lineStyle: { color: A.CH.cyan, width: 1.8 }, itemStyle: { color: A.CH.cyan } },
      ],
    }, { notMerge: true });
    extLegend(dc, $('#divHead', el), { top: 12, fb: { top: 0, right: 0, textStyle: { color: A.CH.ink2, fontSize: 12 } } });   // 設計 v4 2B：圖例搬到標題列右端（繪圖區頂 30 → 12）
  }
  /* 籌碼頁：資料不夠就不要畫一張空圖。
     Andy：「若是籌碼下方無法抓取到數據，就把他替換其他方式，或是直接刪除」。
     規則：≥3 個點才畫線圖；只有 1~2 個點就改成把「現在的數字」直接列出來；
     一個點都沒有的那張卡片整張不出現。 */
  const CHIP_MIN = 3;
  /* ★ 2026-09-26（Andy：「這邊的時間週期都需要 4 週最少，然後都呈現每日狀況」）
     以前四張圖各畫各的：三大法人 120 天、融資融券 250 天、集保只有幾週的時間軸 —— 起訖日對不起來。
     現在四張共用**同一條逐交易日的日期軸**（這一檔的日 K 日期 ∪ 法人／融資券／集保的日期），
     預設「近 4 週」＝最近 20 個交易日，上方一組共用區間切「4 週｜3 個月｜6 個月｜1 年」（記 tw.chipWin），四張一起換。
     法人、融資券是日資料，逐日畫；集保是**每週**資料，點落在實際公布日，兩點之間只連線、不補假的每日值；
     視窗內沒有資料的日子留空（柱子不畫、線斷開）。 */
  const CHIP_WINS = [{ v: 20, t: '4 週' }, { v: 63, t: '3 個月' }, { v: 126, t: '6 個月' }, { v: 250, t: '1 年' }];
  /* ★ 2026-09-27（Andy 給的券商 App 截圖：法人／資券的時間窗都是一季，7/02～9/24 約 60 個交易日；
     「季的週期要對，我發現部分數據太少」）：預設改「3 個月」（63 個交易日），4 週／6 個月／1 年照樣可切。*/
  const CHIP_DEFAULT = 63;
  /* 法人四段（外資｜投信｜自營商｜合計）與資券四段（融資｜當沖｜融券｜借券賣），照截圖；選擇記在 localStorage。
     inst_v3.daily 欄位：[日期, 外資, 投信, 自營商, 區間累計(舊), 自營自行買賣, 自營避險]（股）
     margin 欄位：pg.margin_columns（融資／融券餘額與增減是「張」；當沖、借券是管線換好的「張」、當沖率 %）*/
  const INST_SEGS = [{ v: 'f', t: '外資', i: 1 }, { v: 't', t: '投信', i: 2 }, { v: 'd', t: '自營商', i: 3 }, { v: 'a', t: '合計', i: -1 }];
  const MG_SEGS = [{ v: 'm', t: '融資' }, { v: 'dt', t: '當沖' }, { v: 's', t: '融券' }, { v: 'sbl', t: '借券賣' }];
  const lsGet = (k, ok, dflt) => { try { const v = localStorage.getItem(k); if (v !== null && ok(v)) return v; } catch (e) { /* 私密視窗 */ } return dflt; };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 忽略 */ } };
  function chipWinGet() {
    let v = CHIP_DEFAULT;
    try { const r = localStorage.getItem('tw.chipWin'); if (r !== null && CHIP_WINS.some(w => String(w.v) === r)) v = +r; } catch (e) { /* 私密視窗 */ }
    return v;
  }
  function chipDates(pg, n) {
    const iv = (pg.inst_v3 || {}).daily || [], mg = pg.margin || [], ho = pg.holders || [];
    const set = new Set();
    const add = (d) => { const s = String(d || '').slice(0, 10); if (/^\d{4}-\d{2}-\d{2}$/.test(s)) set.add(s); };
    (pg.daily || []).forEach(b => add(b[0])); iv.forEach(r => add(r[0])); mg.forEach(r => add(r[0])); ho.forEach(r => add(r[0]));
    return [...set].sort().slice(-n);
  }
  /* ★ 2026-09-28（Andy：「資券獨立一個分頁出來」「三大法人也獨立分頁出來」「大戶／散戶持股獨立分頁」
     「籌碼內股東人數拿掉」「主力（替代：三大法人）→ 拿掉」）：
     以前「籌碼」一頁疊了五到六張圖（法人、資券、大戶散戶、股東人數、主力替代），要看其中一張得一路往下捲，
     而且五張圖擠在兩欄裡每張都偏小。拆成三頁、每頁只回答一件事：
       · 法人：外資／投信／自營商／合計這段期間是在買還是在賣？
       · 資券：散戶的融資、融券、當沖、借券賣出最近是加碼還是退場？
       · 大戶／散戶：籌碼是往大戶集中還是往散戶分散？
     三頁共用同一組區間（tw.chipWin，在一頁切了另外兩頁也記得）與同一條逐交易日軸（chipDates，#266 口徑不變）。
     股東人數長條與主力替代卡整張拿掉；後端 main_proxy 欄位留著，前端不讀。
     畫面上的說明一律用讀者語言：資料不夠時寫「資料準備中」，不寫資料集名稱、來源帳號等級這類工程原因。*/
  function chipAxis(dates, win) {
    const long = win > 126;
    /* 刻度：4 週～6 個月寫 MM-DD；1 年會跨年，寫 YY/MM/DD（R5-4：不可以好幾個點寫成同一個日期） */
    const dayLbl = (v) => long ? String(v).slice(2).replace(/-/g, '/') : String(v).slice(5);
    const xCat = (extra) => Object.assign({ ...A.axisStyle, type: 'category', data: dates, boundaryGap: true,
      axisLabel: { color: A.CH.ink3, fontFamily: A.NUM_FONT, formatter: dayLbl, hideOverlap: true } }, extra || {});
    return { dayLbl, xCat, showLbl: win <= 63 };      // 3 個月以內才在點／柱上標數字，1 年標上去會疊成一片
  }
  /* 三頁共用的外殼：上方區間鈕＋日期範圍，下面是這一頁的卡片；draw(dates, win) 由各頁自己畫 */
  /* ★ 2026-10-03（Andy，DECISIONS #302）：opts.wins＝這一頁允許的區間值。大戶／散戶資料只有約 6 週（集保每週才一筆、要 11/27 才滿 13 週），
     6 個月、1 年的圖只是一小段線後面一片空白，所以只留 4 週、3 個月。存著的區間不在允許清單（例如在法人頁選了 1 年）
     → 這一頁退回 3 個月，**不改寫 localStorage**（回到法人頁仍是原本選的 1 年）。沒傳 opts 的頁（法人、資券）行為完全不變。*/
  function chipPage(pg, el, kind, body, draw, opts) {
    const wins = opts && opts.wins ? CHIP_WINS.filter(w => opts.wins.includes(w.v)) : CHIP_WINS;
    /* ★ 2026-10-04（Andy：「大戶那頁 Default 4 周」）：opts.key／opts.dflt＝這一頁自己的記憶鍵與預設值。
       大戶／散戶頁若跟法人、資券共用 tw.chipWin，在法人頁選過 3 個月就會把這頁也蓋掉，預設永遠回不到 4 週；
       所以這頁改記自己的鍵（tw.chipWinHo），沒存過就用 4 週。法人、資券沒傳 opts，行為不變。*/
    const wkey = (opts && opts.key) || 'tw.chipWin';
    let win = chipWinGet();
    if (opts && opts.key) win = +lsGet(wkey, (v) => wins.some(w => String(w.v) === v), String(opts.dflt || CHIP_DEFAULT));
    if (!wins.some(w => w.v === win)) win = (opts && opts.dflt) || CHIP_DEFAULT;
    el.innerHTML = `<div class="row chipBar" style="gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px">
        <div class="seg" id="chipWin" role="group" aria-label="區間">${wins.map(w => `<button type="button" data-v="${w.v}">${w.t}</button>`).join('')}</div>
        <span class="note" id="chipRange" data-readout></span></div>${body}`;
    el.dataset.chip = kind;
    const redraw = () => {
      const dates = chipDates(pg, win);
      const rg = $('#chipRange', el);
      /* ★ 2026-10-06（Andy：「這類資訊一律拿掉」，DECISIONS #329）：區間鈕旁的「YYYY-MM-DD ～ YYYY-MM-DD，N 個交易日」不再顯示
         （區間鈕本身寫了 4 週／3 個月）；起訖日改放 data-range 當機器讀數（驗收用），畫面上是空的。*/
      if (rg) { rg.textContent = ''; rg.dataset.range = dates.length ? `${dates[0]} ～ ${dates[dates.length - 1]}，${dates.length} 個交易日` : ''; }
      el.dataset.win = String(win);
      $$('#chipWin button', el).forEach(b => b.classList.toggle('on', +b.dataset.v === win));
      draw(dates, win);
    };
    $$('#chipWin button', el).forEach(b => b.onclick = () => {
      win = +b.dataset.v;
      try { localStorage.setItem(wkey, String(win)); } catch (e) { /* 忽略 */ }
      redraw();
    });
    redraw();
    return redraw;
  }
  const chipSeg = (id, list, lbl) => `<div class="seg" id="${id}" role="group" aria-label="${lbl}">${list.map(x => `<button type="button" data-v="${x.v}">${x.t}</button>`).join('')}</div>`;
  /* ★ 2026-10-02（Andy #stock/1709，DECISIONS #295）：三頁「上圖下長表」→ 左圖右表並排（.skduo），明細表自成一張卡（.tblcard），
     高度跟左邊圖卡一樣、表在卡裡捲；≤1100 疊成上下。三頁共用這一組（chipTbl／chipCardHtml），版型一致。
     foot＝接在表下面的一句（大戶散戶的「目前累積 N 週，每週五自動增加」放這裡：講的就是右邊這張表為什麼只有這幾列）。*/
  /* ★ 2026-10-04（docs/howto_audit_1004.md 第三節）：how＝[key, 問句, 條列]，有給才在標題旁出「?」（法人、資券兩張；大戶散戶那張在改版中，先不加）。*/
  const chipTbl = (id, title, foot, how) => `<div class="card tblcard" id="${id}Card"><h3>${title || '每日明細'}${how ? ' ' + hq(how[0], title || '每日明細') : ''}</h3>${how ? `<div class="howtxt" id="how-${how[0]}" hidden>${A.howHTML(how[1], how[2])}</div>` : ''}<div class="tw chipTbl" id="${id}"></div>${foot || ''}</div>`;
  const chipK = (l, v, cls) => `<div class="k"><div class="l">${l}</div><div class="v ${cls || ''}">${v}</div></div>`;
  /* 資料還不到 CHIP_MIN 天：不畫一條兩點的假斜線，直接列最新數字 */
  const chipNums = (key, title, sub, kvs, why) => `<div class="card"><h3>${title} <small data-readout>${sub}</small> ${hq(key, title)}</h3>
      <div class="kvs" style="margin-top:10px">${kvs}</div><div class="note" style="margin-top:8px">${why}</div></div>`;
  const chipCardHtml = (key, id, title, seg, items, extra, style) => `<div class="skduo chipduo" id="${id}Duo"><div class="card"><div class="row spread" style="gap:8px;flex-wrap:wrap"><h3>${title} ${hq(key, title)}</h3>${seg || ''}</div>${hbox(key, items)}<div id="${id}" class="chart chipChart"${style ? ` style="${style}"` : ''}></div></div>${extra || ''}</div>`;

  /* ---- 法人：外資｜投信｜自營商｜合計；柱＝每日買賣超、線＝區間累計（視窗第一天起算）；下方每日表 ---- */
  function tabInst(pg, el) {
    const iv = (pg.inst_v3 || {}).daily || [];
    if (!iv.length) { el.innerHTML = '<div class="card"><div class="empty">尚無法人買賣超資料</div></div>'; return; }
    if (iv.length < CHIP_MIN) { const r = iv[iv.length - 1];
      el.innerHTML = chipNums('skinst', '三大法人', `最新一筆 ${r[0]}`,
        chipK('外資', A.fmt.lot(r[1] / 1000), A.fmt.cls(r[1])) + chipK('投信', A.fmt.lot(r[2] / 1000), A.fmt.cls(r[2])) + chipK('自營商', A.fmt.lot(r[3] / 1000), A.fmt.cls(r[3])),
        `目前只有 ${iv.length} 天`);
      return; }
    let iseg = lsGet('tw.instSeg', v => INST_SEGS.some(x => x.v === v), 'f');
    const imap = new Map(iv.map(r => [String(r[0]).slice(0, 10), r]));
    const body = chipCardHtml('skinst', 'instChart', '三大法人買賣超', chipSeg('instSeg', INST_SEGS, '法人別'),
      ['柱＝每日買賣超（紅＝買超、綠＝賣超，張）', '線＝區間累計（從區間第一天起算）', '自營商＝自行買賣＋避險', '累計線一路往上＝這段期間持續買進'],
      chipTbl('instTbl', '每日明細', '', ['skinsttbl', '法人每天各買賣了幾張。', ['單位：張，買超－賣超；紅＝買超、綠＝賣超', '亮起來那一欄＝左圖目前選的法人別', '合計＝外資＋投信＋自營商']]), 'min-height:340px');
    const redraw = chipPage(pg, el, 'inst', body, (dates, win) => {
      const { xCat } = chipAxis(dates, win);
      const seg = INST_SEGS.find(x => x.v === iseg) || INST_SEGS[0];
      const valOf = (r) => (!r ? null : seg.i > 0 ? r[seg.i] : (r[1] == null && r[2] == null && r[3] == null ? null : (r[1] || 0) + (r[2] || 0) + (r[3] || 0)));
      const vals = dates.map(d => valOf(imap.get(d)));
      let s = 0;
      const cum = vals.map(v => { if (v == null) return null; s += v; return s; });
      $$('#instSeg button', el).forEach(b => b.classList.toggle('on', b.dataset.v === seg.v));
      el.dataset.instSeg = seg.v;
      const lot = (v) => (v == null ? '—' : A.fmt.lot(v / 1000));
      const ic = A.chart('instChart', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => { const d = ps[0].axisValue; const r = imap.get(d);
          if (!r) return `<b>${d}</b><br>這天沒有法人資料`;
          let h = `<b>${d}</b><br>${seg.t} ${lot(valOf(r))}`;
          if (seg.v === 'd' && (r[5] != null || r[6] != null)) h += `<br>· 自行買賣 ${lot(r[5])}<br>· 避險 ${lot(r[6])}`;
          const c = ps.find(p => p.seriesName === '區間累計'); if (c) h += `<br>區間累計 ${lot(c.value)}`;
          return h; } },
        legend: { show: false, data: [seg.t, '區間累計'] }, grid: { left: 66, right: 78, top: 10, bottom: 30 },
        xAxis: xCat(), yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) } }, { ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) }, splitLine: { show: false } }],
        series: [{ name: seg.t, type: 'bar', data: vals.map(v => (v == null ? null : { value: v, itemStyle: { color: v >= 0 ? A.CH.up : A.CH.down } })), itemStyle: { color: A.CH.up } },
          { name: '區間累計', type: 'line', yAxisIndex: 1, data: cum, showSymbol: false, connectNulls: false, lineStyle: { color: '#ffb454', width: 2 }, itemStyle: { color: '#ffb454' } }] }, { notMerge: true });
      // 設計 v4 2B：圖例搬到標題列最右端（外資／投信／自營商／合計那組鈕後面）；柱是紅買綠賣，色樣畫成兩半
      const isg = $('#instSeg', el); if (isg) extLegend(ic, isg.parentElement, { dual: { [seg.t]: [A.CH.up, A.CH.down] } });
      const tb = $('#instTbl', el);
      if (tb) {
        const cell = (v, on) => `<td class="num ${A.fmt.cls(v)}${on ? ' sel' : ''}">${v == null ? '—' : A.fmt.i(Math.round(v / 1000))}</td>`;
        const rows = dates.slice().reverse().map(d => [d, imap.get(d)]).filter(x => x[1]);
        const th = (t, v) => `<th${seg.v === v ? ' class="sel"' : ''}>${t}</th>`;
        tb.innerHTML = `<table><thead><tr><th class="l">日期</th>${th('外資', 'f')}${th('投信', 't')}${th('自營商', 'd')}${th('合計', 'a')}</tr></thead><tbody>${rows.map(([d, r]) => `<tr><td class="l mono">${d.slice(5)}</td>${cell(r[1], seg.v === 'f')}${cell(r[2], seg.v === 't')}${cell(r[3], seg.v === 'd')}${cell((r[1] || 0) + (r[2] || 0) + (r[3] || 0), seg.v === 'a')}</tr>`).join('') || '<tr><td colspan="5" class="l muted">這段期間沒有法人資料</td></tr>'}</tbody></table><div class="note" style="margin-top:4px">單位：張（買超－賣超）</div>`;
      }
    });
    $$('#instSeg button', el).forEach(b => b.onclick = () => { iseg = b.dataset.v; lsSet('tw.instSeg', iseg); redraw(); });
  }

  /* ---- 資券：融資｜當沖｜融券｜借券賣；融資／融券＝每日增減柱＋餘額線；當沖＝張數柱＋當沖率線；借券賣＝賣出柱＋餘額線 ---- */
  function tabMargin(pg, el) {
    const mg = pg.margin || [];
    if (!mg.length) { el.innerHTML = '<div class="card"><div class="empty">尚無融資融券資料</div></div>'; return; }
    /* ★ 2026-10-02（Andy：「總覽籌碼快照的『融資餘額 2.1 萬張』和『資券』分頁的數字對不上」，對帳表在 DECISIONS #294）：
       根因不是算錯，是**兩邊顯示的根本不是同一個指標**：總覽寫的是「融資餘額」（margin_balance，張），
       資券分頁的每日表那一欄標題只寫「融資」、內容卻是「融資增減」（margin_change，張，例如 −503），
       圖上的長條也是增減，餘額只是右軸那條線、畫面上沒有任何地方寫出最新餘額的數字 —— 讀者只能拿 2.1 萬去對 −503。
       修法：① 分頁最上面加一列「最新數字」（融資餘額／融券餘額／借券賣出餘額／當沖），跟總覽同一支 mgLatest()，日期一起寫；
       ② 每日表的欄名全部寫清楚「融資增減」「融資餘額」…，餘額欄補回來。數字本身一個都沒改。*/
    /* ★ 2026-10-03（Andy：「資券分頁那排 4 個 KPI 方塊直接整排拿掉」，DECISIONS #305，推翻 #294 ①「最上面加一列最新數字」）：
       最新的融資／融券／借券賣出餘額與當沖，總覽「籌碼快照」的「信用與借券」那一塊已經有（同一支 mgLatest），
       下方每日明細表第一列也有；這一頁留圖與明細表就好，圖卡直接頂到區間鈕下面。②（每日表欄名寫全、餘額欄）照舊。*/
    const ML = mgLatest(pg);
    /* ★ 2026-10-03（DECISIONS #304）：當沖／借券賣出被管線誤封印，09-25 之後全市場一筆都沒有，
       每日表那兩欄一路「—」，讀者會以為是 0 或沒人當沖。pg.margin_asof＝三個來源**全市場**最新到哪天：
       某個來源比其他來源舊，就是資料源自己停在那天（不是這檔的事）→ 照實寫「更新到 MM-DD」，
       之後的日期在表格寫「未提供」、提示框寫「這天還沒提供」（畫面不寫「資料源」：09-28 Andy 要求讀者看不懂的內部字眼全清，_uitest 禁用字）。某一檔自己沒有（不能當沖的處置股）不在這裡講。*/
    const AS = pg.margin_asof || {};
    const asRef = [AS.margin, AS.daytrade, AS.sbl].filter(Boolean).sort().pop() || '';
    const cutOf = (k) => (AS[k] && asRef && AS[k] < asRef ? AS[k] : null);
    const CUT = { dt: cutOf('daytrade'), sbl: cutOf('sbl') };
    const naCut = (k, d) => !!(CUT[k] && d > CUT[k]);
    const srcNote = (CUT.dt || CUT.sbl)
      ? `<div class="note" id="mgSrcNote" data-dt-cut="${CUT.dt || ''}" data-sbl-cut="${CUT.sbl || ''}" style="margin:-4px 0 10px">${[CUT.dt && `當沖資料目前只更新到 <b class="mono">${md5(CUT.dt)}</b>`, CUT.sbl && `借券賣出資料目前只更新到 <b class="mono">${md5(CUT.sbl)}</b>`].filter(Boolean).join('、')}；之後寫「未提供」，不是 0</div>`
      : '';
    if (mg.length < CHIP_MIN) {
      el.innerHTML = srcNote + chipNums('skmg', '融資融券', `最新一筆 ${ML.mb ? ML.mb.d : mg[mg.length - 1][0]}`, chipK('融資增減', ML.mc ? A.fmt.lot(ML.mc.v) : '—') + chipK('融券增減', ML.sc ? A.fmt.lot(ML.sc.v) : '—'),
        `目前只有 ${mg.length} 天`);
      return; }
    let mseg = lsGet('tw.mgSeg', v => MG_SEGS.some(x => x.v === v), 'm');
    const mmap = new Map(mg.map(r => [String(r[0]).slice(0, 10), r]));
    const body = srcNote + chipCardHtml('skmg', 'marginChart', '資券', chipSeg('mgSeg', MG_SEGS, '資券類別'),
      ['融資／融券：柱＝每日增減（張）、線＝餘額', '當沖：柱＝當沖成交張數、線＝當沖率', '借券賣：柱＝當日借券賣出、線＝借券賣出餘額', '明細表最新一列若是「—」＝資券資料尚未公布（常晚一天）', '借券賣出多為法人避險，不是融券'],
      chipTbl('mgTbl', '每日明細', '', ['skmgtbl', '融資、融券、當沖、借券每天各多少張。', ['餘額＝當日收盤後；增減＝比前一日多或少', '最新一列若是「—」＝資券資料尚未公布（常晚一天）', '「未提供」＝那天來源沒給，不是 0', '亮起來那一欄＝左圖目前選的類別']]), 'min-height:340px');
    const redraw = chipPage(pg, el, 'margin', body, (dates, win) => {
      const { xCat } = chipAxis(dates, win);
      const nTrade = dates.length;
      const seg = MG_SEGS.find(x => x.v === mseg) || MG_SEGS[0];
      $$('#mgSeg button', el).forEach(b => b.classList.toggle('on', b.dataset.v === seg.v));
      const C = { m: [3, 1, '融資增減', '融資餘額', '張'], s: [4, 2, '融券增減', '融券餘額', '張'], dt: [5, 6, '當沖張數', '當沖率', '%'], sbl: [7, 8, '借券賣出', '借券賣出餘額', '張'] }[seg.v];
      const col = (i) => dates.map(d => { const r = mmap.get(d); return r && r[i] != null ? r[i] : null; });
      const bar = col(C[0]), line = col(C[1]);
      const any = mg.some(r => r[C[0]] != null || r[C[1]] != null);
      el.dataset.mgSeg = seg.v;
      if (!any) {
        extLegendDrop('marginChart');
        A.empty('marginChart', seg.v === 'dt' ? '尚無當沖資料'
          : seg.v === 'sbl' ? '尚無借券賣出資料'
            : '尚無信用交易資料');
      } else {
        const mEl = document.getElementById('marginChart');
        if (mEl && mEl.classList.contains('isempty')) { mEl.classList.remove('isempty'); mEl.innerHTML = ''; }   // 從沒資料的分段切回來：先清掉那行字
        const fmtV = (v, unit) => (v == null ? '—' : unit === '%' ? A.fmt.n(v, 2) + '%' : A.fmt.lot(v));
        const mc = A.chart('marginChart', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => { const d = ps[0].axisValue;
            if (!mmap.get(d)) return `<b>${d}</b><br>這天沒有資券資料`;
            if (naCut(seg.v, d)) return `<b>${d}</b><br>這天還沒提供（${seg.v === 'dt' ? '當沖' : '借券賣出'}只更新到 ${md5(CUT[seg.v])}）`;
            return `<b>${d}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${fmtV(p.value, p.seriesIndex === 1 ? C[4] : '張')}`).join('<br>'); } },
          legend: { show: false, data: [C[2], C[3]] }, grid: { left: 60, right: 64, top: 10, bottom: 30 },
          xAxis: xCat(), yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v) } }, { ...A.axisStyle, scale: true, splitLine: { show: false }, axisLabel: { formatter: v => (C[4] === '%' ? v + '%' : A.fmt.lot(v)) } }],
          series: [{ name: C[2], type: 'bar', data: bar.map(v => (v == null ? null : { value: v, itemStyle: { color: (seg.v === 'm' || seg.v === 's') ? (v >= 0 ? A.CH.up : A.CH.down) : A.CH.violet } })), itemStyle: { color: A.CH.violet } },
            { name: C[3], type: 'line', yAxisIndex: 1, data: line, showSymbol: nTrade <= 30, symbolSize: 4, connectNulls: false, lineStyle: { color: '#ffb454', width: 2 }, itemStyle: { color: '#ffb454' } }] }, { notMerge: true });
        // 設計 v4 2B：圖例搬到標題列；融資／融券增減逐根紅綠，色樣畫成兩半（當沖、借券賣是單色）
        const msg = $('#mgSeg', el); if (msg) extLegend(mc, msg.parentElement, { dual: (seg.v === 'm' || seg.v === 's') ? { [C[2]]: [A.CH.up, A.CH.down] } : null });
      }
      const tb = $('#mgTbl', el);
      if (tb) {
        const num = (v, sg, on, na) => (v == null && na
          ? `<td class="num muted${on ? ' sel' : ''}" data-na="src" title="這天還沒提供（不是 0）"><small>未提供</small></td>`
          : `<td class="num ${sg ? A.fmt.cls(v) : ''}${on ? ' sel' : ''}">${v == null ? '—' : A.fmt.i(v)}</td>`);
        const rows = dates.slice().reverse().map(d => [d, mmap.get(d)]).filter(x => x[1]);
        const th = (t, v) => `<th${seg.v === v ? ' class="sel"' : ''}>${t}</th>`;
        /* 2026-10-02（#294 對帳）：欄名寫全（改前只寫「融資」「融券」，內容卻是增減，讀者拿去跟總覽的餘額比就對不上），餘額欄補回來 */
        tb.innerHTML = `<table><thead><tr><th class="l">日期</th>${th('融資餘額', 'm')}${th('融資增減', 'm')}${th('融券餘額', 's')}${th('融券增減', 's')}${th('當沖張數', 'dt')}${th('借券賣出', 'sbl')}</tr></thead><tbody>${rows.map(([d, r]) => `<tr><td class="l mono">${d.slice(5)}</td>${num(r[1], false, seg.v === 'm')}${num(r[3], true, seg.v === 'm')}${num(r[2], false, seg.v === 's')}${num(r[4], true, seg.v === 's')}${num(r[5], false, seg.v === 'dt', naCut('dt', d))}${num(r[7], false, seg.v === 'sbl', naCut('sbl', d))}</tr>`).join('') || '<tr><td colspan="7" class="l muted">這段期間沒有資券資料</td></tr>'}</tbody></table><div class="note" style="margin-top:4px">單位：張。餘額＝當日收盤後的餘額；增減＝比前一日多或少；當沖張數＝當沖成交張數；借券賣出＝當日借券賣出張數</div>`;
      }
    });
    $$('#mgSeg button', el).forEach(b => b.onclick = () => { mseg = b.dataset.v; lsSet('tw.mgSeg', mseg); redraw(); });
  }

  /* ---- 大戶／散戶：千張以上、400～1000 張、≤10 張三條持股比例週線 ----
     Andy 2026-09-28：「千張、400–1000、≤10 持股線圖需重點且可篩選」。
     · 三條各自一格、各自一根 Y 軸（不從 0 起）：千張大戶 80% 上下、另外兩條 3～6%，擠在同一根軸上每週 ±0.05pp 連 1px 都不到。
     · 上方三顆色塊按鈕＝圖例兼開關：按掉一條，那一格整格收掉、其他格自動變高；選擇記在 tw.hoLines。
     · 線 3px、點 8px、配色避開紅綠（紅綠在本站是漲跌）：千張＝青、400～1000＝琥珀、≤10＝紫。
     · 集保每週公布一次：點落在公布日，點與點之間只是連線，不補每日假值（#266）。*/
  const HO_LINES = [{ k: 1, key: 'big', name: '千張以上', full: '千張大戶（≥1,000 張）', c: 'cyan' },
    { k: 2, key: 'mid', name: '400～1000 張', full: '中實戶（400～1,000 張）', c: 'amber' },
    { k: 3, key: 'ret', name: '≤10 張', full: '散戶（≤10 張）', c: 'violet' }];
  function hoLinesGet() {
    const raw = lsGet('tw.hoLines', v => /^[123,]*$/.test(v), '1,2,3');
    return new Set(raw.split(',').filter(Boolean).map(Number));
  }
  function tabHolders(pg, el) {
    const ho = (pg.holders || []).filter(r => r && (r[1] != null || r[2] != null || r[3] != null));
    const insL = (pg.insider || {}).latest;
    /* 董監持股（每月申報）：放在圖下一行，不塞進每週的表。散戶口徑寫明（本站＝持股 ≤10 張，跟部分券商 App 的散戶定義不同）*/
    const insNote = `<div class="note insNote" data-readout style="margin-top:6px">${insL && insL.director_pct != null && insL.flag !== 'over100'
      ? `董監持股 <b class="mono">${A.fmt.n(insL.director_pct, 2)}%</b>（${A.fmt.esc(insL.ym)} 月底申報，董監 ${insL.n_directors} 人${insL.pledge_pct != null ? `，設質 ${A.fmt.n(insL.pledge_pct, 1)}%` : ''}）`
      : ''}${insL && insL.director_pct != null && insL.flag !== 'over100' ? '；' : ''}散戶＝持股 ≤10 張</div>`;
    if (!ho.length) { el.innerHTML = '<div class="card"><div class="empty">尚無大戶／散戶持股資料</div></div>'; return; }
    const hmap = new Map(ho.map(r => [String(r[0]).slice(0, 10), r]));
    const prevOf = (r) => { const i = ho.indexOf(r); return i > 0 ? ho[i - 1] : null; };
    const pp = (v) => v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toFixed(2) + 'pp';
    const ppCls = (v) => v == null ? 'fl' : v > 0 ? 'up' : v < 0 ? 'dn' : 'fl';
    const last = ho[ho.length - 1], lastPrev = prevOf(last);
    let on = hoLinesGet();
    const tgl = HO_LINES.map(L => { const w = lastPrev && lastPrev[L.k] != null && last[L.k] != null ? last[L.k] - lastPrev[L.k] : null;
      return `<button type="button" class="hoTgl" data-k="${L.k}" aria-pressed="true" style="--hc:${A.CH[L.c]}">`
        + `<span class="sw"></span><span class="nm">${L.name}</span><b class="mono">${last[L.k] != null ? A.fmt.n(last[L.k], 2) + '%' : '—'}</b>`
        + `<span class="mono ${ppCls(w) === 'dn' ? 'down' : ppCls(w) === 'up' ? 'up' : 'muted'}">${pp(w)}</span></button>`; }).join('');
    /* 歷史回補（Andy：「歷史資料能回補就回補，補不了要講原因」）：補不了 ——
       集保中心的開放資料每週只給「最新一週」，FinMind 的歷史集保表免費帳號不開（DECISIONS #210，2026-09-12 那輪 500 檔全回空），
       集保官網的歷史查詢頁不在合規來源白名單內（CLAUDE.md 絕對不做 1）。所以只能從資料湖第一週（2026-09-04）起往後累積。
       畫面上用讀者聽得懂的一句話講，不寫資料集或帳號等級；滿一年（52 週）之後這句自動換成一般的讀圖提示。
       ★ 2026-10-02（Andy：「大戶／散戶資料只有 4 週，至少要 3 個月」，DECISIONS #295）重新查證：湖裡真的只有 4 週、payload 與這裡都沒截短，
       集保官網逐檔查詢頁是網頁表單不是開放資料，不碰。開頭改成 Andy 指定的「目前累積 N 週，每週五自動增加」。
       右邊每週明細表列出全部週別（不跟著區間鈕截），_uitest「個股分頁版面1002」驗「表的列數＝個股 JSON 週數＝資料湖週數」。*/
    const growing = ho.length < 52
      ? `<div class="note hoNote" data-readout data-weeks="${ho.length}" style="margin-top:6px"><b>目前累積 ${ho.length} 週，每週五自動增加</b>（從 ${A.fmt.esc(ho[0][0])} 起）</div>`
      : '';
    /* 設計 v4 2B：三顆色塊（圖例兼開關）從標題下面獨佔的一列（10＋36＋4＝50px）搬進標題列，
       放不下（窄畫面）時整組自己換到下一行，跟改前一樣。id、按鈕、行為都不變。
       DOM 順序是「標題、日期、色塊」：窄的時候先換行的是色塊（日期留在標題那一行），寬的時候 CSS 用 order 把色塊排到中間。*/
    const body = `<div class="skduo chipduo" id="hoDuo"><div class="card" id="hoCard"><div class="row spread" id="hoHead" style="gap:8px;flex-wrap:wrap"><h3>大戶／散戶持股比例 ${hq('skho', '大戶／散戶持股')}</h3><div class="hoTgls" id="hoTgls" role="group" aria-label="顯示哪幾條線">${tgl}</div></div>
      ${hbox('skho', ['千張以上往上、≤10 張往下＝籌碼往大戶集中', '反過來＝大戶在賣、散戶在接', '每條各自一格、Y 軸不從 0 起，看方向', '色塊右邊＝最新比例與跟上一週比（pp＝百分點）'])}
      <div id="holderChart" class="chart chipChart" style="min-height:420px"></div>${insNote}</div>${chipTbl('hoTbl', '每週明細', growing)}</div>`;
    /* 設計 v4 2B：手機（≤640）三顆色塊維持改前的位置（標題列下面獨佔一列）—— 手機版面這一批不動。
       chipPage 會先把 body 寫進去再畫圖，所以在第一次畫圖之前（draw 的最前面）搬一次就好。*/
    let hoPlaced = false;
    const hoPlace = () => { if (hoPlaced) return; hoPlaced = true;
      if ((window.innerWidth || 1440) > 640) return;
      const t = $('#hoTgls', el), hb = $('#how-skho', el); if (t && hb) hb.after(t); };
    const redraw = chipPage(pg, el, 'holders', body, (dates, win) => {
      hoPlace();
      const { xCat, dayLbl, showLbl } = chipAxis(dates, win);
      const LINES = HO_LINES.filter(L => on.has(L.k));
      $$('#hoTgls .hoTgl', el).forEach(b => { const x = on.has(+b.dataset.k); b.classList.toggle('off', !x); b.setAttribute('aria-pressed', String(x)); });
      el.dataset.hoLines = LINES.map(L => L.k).join(',');
      const hEl = document.getElementById('holderChart');
      if (!LINES.length) { A.empty('holderChart', '三條線都已隱藏'); }
      else {
        if (hEl && hEl.classList.contains('isempty')) { hEl.classList.remove('isempty'); hEl.innerHTML = ''; }   // 從「三條都隱藏」回來：先清掉那行字再重建圖
        const H = Math.max(360, (hEl && hEl.clientHeight) || 420);
        const TOP = 4, BOT = 28, CELL = (H - TOP - BOT) / LINES.length;
        const inWin = dates.filter(d => hmap.has(d)).map(d => hmap.get(d));
        const first = inWin[0], lw = inWin[inWin.length - 1];
        const rangeTxt = CHIP_WINS.find(w => w.v === win).t.replace(' ', '');
        A.chart('holderChart', {
          axisPointer: { link: [{ xAxisIndex: 'all' }] },
          tooltip: { ...A.tip, trigger: 'axis', axisPointer: { type: 'line' },
            formatter: (ps) => { const d = ps[0].axisValue; const r = hmap.get(d);
              if (!r) return `<b>${d}</b><br>這天不是公布日（每週公布一次）`; const p = prevOf(r);
              return `<b>${r[0]}</b>` + LINES.map(L => `<br><span style="color:${A.CH[L.c]}">●</span> ${L.full} ${A.fmt.n(r[L.k], 2)}%`
                + `　週 ${p && p[L.k] != null ? pp(r[L.k] - p[L.k]) : '—（第一週）'}`).join(''); } },
          title: LINES.map((L, i) => { const m = lw && first && first !== lw && first[L.k] != null ? lw[L.k] - first[L.k] : null;
            return { left: 52, top: TOP + i * CELL, padding: 0, textStyle: { rich: {
                d: { color: A.CH[L.c], fontSize: 14 }, n: { color: A.CH.ink, fontSize: 13, fontWeight: 700 },
                l: { color: A.CH.ink3, fontSize: 12 }, up: { color: A.CH.up, fontSize: 12, fontFamily: A.NUM_FONT },
                dn: { color: A.CH.down, fontSize: 12, fontFamily: A.NUM_FONT }, fl: { color: A.CH.ink3, fontSize: 12, fontFamily: A.NUM_FONT } } },
              text: lw ? `{d|━} {n|${L.full}}  {l|${rangeTxt}} {${ppCls(m)}|${pp(m)}}` : `{d|━} {n|${L.full}}  {l|這個區間沒有公布日}` }; }),
          grid: LINES.map((L, i) => ({ left: 52, right: 30, top: TOP + i * CELL + 26, height: CELL - 38 })),
          xAxis: LINES.map((L, i) => xCat({ gridIndex: i, boundaryGap: false, splitLine: { show: false },
            axisTick: { show: i === LINES.length - 1 }, axisLabel: { show: i === LINES.length - 1, color: A.CH.ink3, fontFamily: A.NUM_FONT, formatter: dayLbl, hideOverlap: true } })),
          yAxis: LINES.map((L, i) => ({ ...A.axisStyle, type: 'value', gridIndex: i, scale: true, splitNumber: 2,
            axisLabel: { color: A.CH.ink3, fontFamily: A.NUM_FONT, fontSize: 12, formatter: (v) => +v.toFixed(2) + '%' } })),   // 設計 v4 2B：11 → 12
          series: LINES.map((L, i) => ({ name: L.full, type: 'line', xAxisIndex: i, yAxisIndex: i,
            data: dates.map(d => { const r = hmap.get(d); return r ? r[L.k] : null; }), showSymbol: true, symbolSize: 8, connectNulls: true,
            lineStyle: { color: A.CH[L.c], width: 3 }, itemStyle: { color: A.CH[L.c] },
            label: { show: showLbl, position: 'top', distance: 5, color: A.CH.ink2, fontSize: 12, fontFamily: A.NUM_FONT,
              formatter: (q) => q.value == null ? '' : A.fmt.n(q.value, 2) + '%' } })),
        }, { notMerge: true });
      }
      /* 每週表：新的在上；隱藏的那一條欄位照樣列（表是完整紀錄），只是不反白 */
      const ht = $('#hoTbl', el);
      if (ht) {
        const cell = (r, L) => { const p = prevOf(r); const w = p && p[L.k] != null && r[L.k] != null ? r[L.k] - p[L.k] : null;
          return `<td class="num${on.has(L.k) ? ' sel' : ''}">${r[L.k] == null ? '—' : A.fmt.n(r[L.k], 2) + '%'}<small class="${ppCls(w) === 'dn' ? 'down' : ppCls(w) === 'up' ? 'up' : 'muted'}" style="margin-left:6px">${w == null ? '' : pp(w)}</small></td>`; };
        ht.innerHTML = `<table><thead><tr><th class="l">公布日</th>${HO_LINES.map(L => `<th${on.has(L.k) ? ' class="sel"' : ''}>${L.name}</th>`).join('')}</tr></thead><tbody>${ho.slice().reverse().map(r => `<tr><td class="l mono">${String(r[0])}</td>${HO_LINES.map(L => cell(r, L)).join('')}</tr>`).join('')}</tbody></table><div class="note" style="margin-top:4px">持股比例＝該級距持股 ÷ 總股數；小字＝跟上一週比（pp＝百分點）</div>`;
      }
    }, { wins: [20, 63], key: 'tw.chipWinHo', dflt: 20 });   // 大戶／散戶只留 4 週、3 個月（#302），預設 4 週、自己記
    $$('#hoTgls .hoTgl', el).forEach(b => b.onclick = () => {
      const k = +b.dataset.k;
      if (on.has(k)) on.delete(k); else on.add(k);
      lsSet('tw.hoLines', [...on].sort().join(','));
      redraw();
    });
  }
  function tabBasics(pg, el) {
    const b = pg.basics || {}; const f = pg.fundamental || {};
    const indLink = b.industry ? (A.L.gname['ind_' + b.industry] ? A.L.group('ind_' + b.industry, b.industry) : A.fmt.esc(b.industry)) : null;
    const rows = [['公司全名', b.full_name], ['市場', A.fmt.mkt(b.market)], ['產業別', indLink, true], ['上市日', b.listed_date], ['股本', b.capital_billion != null ? b.capital_billion + ' 億' : null], ['董事長', b.chairman], ['網站', b.website ? `<a href="${A.fmt.esc(b.website)}" target="_blank" rel="noopener">${A.fmt.esc(b.website)}</a>` : null, true], ['市值', f.market_cap != null ? A.fmt.yi(f.market_cap) : null], ['股價淨值比', f.pb != null ? A.fmt.n(f.pb) : null], ['股價營收比', f.ps != null ? A.fmt.n(f.ps) : null], ['所屬族群', (pg.meta.groups || []).length ? `<span class="tagrow">${(pg.meta.groups || []).map(gn => A.L.groupByName(gn)).join('')}</span>` : null, true], ['題材', A.L.themesOf(pg.meta.code) ? `<span class="tagrow">${A.L.themesOf(pg.meta.code)}</span>` : null, true]];
    /* ★ 2026-09-26（Andy：「將過往歷史數據移動到圖三那位置」）：基本資料表只佔左半，右半一大塊空白，
       「1–12 月平均漲幅」卻排在整張表下面要往下捲才看得到。改成兩欄並排（.skBasics，桌機等高），≤900px 疊成上下。
       季節卡是 flex 直欄、圖吃掉剩下的高度，跟左邊基本資料表一樣高。 */
    el.innerHTML = `<div class="grid g2 skBasics"><div class="card"><h3>基本資料 ${hq('skbasic', '基本資料')}</h3>${hbox('skbasic', ['市值＝收盤價 × 股數', '股價淨值比＝股價 ÷ 每股淨值', '股價營收比＝市值 ÷ 近四季營收'])}<dl class="kv" style="margin-top:10px">${rows.map(r => `<dt>${r[0]}</dt><dd>${r[1] != null && r[1] !== '' ? (r[2] ? r[1] : A.fmt.esc(r[1])) : '—'}</dd>`).join('')}</dl></div>
      <div class="card msCard" id="msCard"><div class="row spread">
        <h3>1–12 月平均漲幅 <small id="msSub" data-readout></small> ${hq('ms', '1–12 月平均漲幅')}</h3>
        <div class="row" style="gap:10px;align-items:center">
          <div class="seg" id="msYears"><button data-v="1">1 年</button><button data-v="3">3 年</button><button data-v="5" class="on">5 年</button><button data-v="0">全部</button></div>
          <label class="opabox" for="msCustom">自填 <input id="msCustom" type="number" min="1" max="15" step="1" style="width:78px" placeholder="輸入年數" title="輸入要統計的最近 N 年（1～最多可用年數）" aria-label="自填年數"> 年</label>
        </div></div>
        <div class="mshint" id="msHint" role="status" hidden></div>
        <div class="howtxt" id="how-ms" hidden>${A.howHTML('這一檔哪幾個月歷史上容易漲。', [
          '柱高＝那個月的平均漲幅',
          '柱上 x/y＝上漲年數／取樣年數',
          '只看平均會被一次暴漲暴跌帶偏',
          '樣本少於 3 年的月份參考就好',
        ])}</div>
        <div id="msChart" class="chart"></div>
        <div class="note" id="msNote" data-readout></div></div></div>`;
    drawMonthSeason(pg);
  }

  /* C5：個股的 1–12 月平均漲幅（Andy 2026-09-18 拍板要做）。
     payload 給的是**逐年逐月**的原始報酬，所以切 1／3／5／自填年數都在前端算，
     不用為了換一個年數回頭問後端。
     每一根柱子旁邊同時寫「上漲的年數／總年數」—— 只看平均會被一次暴漲暴跌帶偏，
     十年裡漲八年的 +3% 跟漲兩年的 +3%，意思完全不同。*/
  function drawMonthSeason(pg) {
    const ms = pg.month_season || {};
    const el = $('#msChart');
    if (!el) return;
    const byYear = ms.by_year || {};
    const allYears = Object.keys(byYear).sort();
    if (!allYears.length) {
      el.innerHTML = '<div class="empty" style="height:100%">歷史價量不足</div>';
      $('#msSub').textContent = '';
      return;
    }
    /* 預設 5 年。★ 一定要先確認 localStorage 真的有值 ——
       沒設定過時 getItem() 回 null，而 `+null` 是 0，0 在這裡的意思是「全部年份」，
       結果是「第一次打開就變成 15 年」，跟預設值完全不同。*/
    let n = 5;
    try {
      const raw = localStorage.getItem('tw.ms.years');
      if (raw !== null && raw !== '') { const s = +raw; if (s >= 0 && s <= 15) n = s; }
    } catch (e) { /* 私密視窗，忽略 */ }
    const paint = () => {
      const years = n > 0 ? allYears.slice(-n) : allYears;
      const stat = ms.months.map(m => {
        const vs = years.map(y => byYear[y][String(m)]).filter(v => v != null);
        const up = vs.filter(v => v > 0).length;
        return { m, avg: vs.length ? vs.reduce((s, v) => s + v, 0) / vs.length : null,
                 up, n: vs.length };
      });
      $('#msSub').textContent = years.length
        ? `${years[0]} ～ ${years[years.length - 1]}，共 ${years.length} 年`
        : '';
      A.chart('msChart', {
        tooltip: { ...A.tip, trigger: 'axis',
          formatter: (ps) => { const s = stat[ps[0].dataIndex];
            return `<b>${s.m} 月</b><br>平均漲幅 ${s.avg == null ? '—' : A.fmt.pct(s.avg)}`
              + `<br>上漲 ${s.up} / ${s.n} 年（勝率 ${s.n ? Math.round(s.up / s.n * 100) : 0}%）`; } },
        grid: { left: 52, right: 20, top: 28, bottom: 28 },
        xAxis: { ...A.axisStyle, type: 'category', data: ms.months.map(m => m + ' 月'),
                 axisLabel: { color: A.CH.ink2 } },
        yAxis: { ...A.axisStyle, axisLabel: { color: A.CH.ink3, formatter: (v) => (v > 0 ? '+' : '') + v + '%' } },
        series: [{ type: 'bar', barWidth: '58%',
          /* ★ 2026-09-24（Andy：長條一律「數字寫在長出去那一端的外側」）：負值那幾個月的「上漲年數」
             以前固定寫在 top —— 負值長條的 top 是零軸，字貼在零軸上、離長條的末端最遠。改成依正負放上／下。*/
          data: stat.map(s => ({ value: s.avg == null ? null : +s.avg.toFixed(2),
            itemStyle: { color: s.avg > 0 ? A.CH.up : s.avg < 0 ? A.CH.down : A.CH.ink3, borderRadius: 4 },
            label: { position: s.avg < 0 ? 'bottom' : 'top' } })),
          label: { show: true, color: A.CH.ink3, fontSize: 12,
            formatter: (q) => { const s = stat[q.dataIndex]; return s.n ? `${s.up}/${s.n}` : ''; } } }],
      }, { notMerge: true });
      const best = stat.filter(s => s.avg != null).sort((a, b) => b.avg - a.avg)[0];
      const worst = stat.filter(s => s.avg != null).sort((a, b) => a.avg - b.avg)[0];
      $('#msNote').innerHTML = best && worst
        /* 說明精簡：讀數留著，「x/y 是什麼、樣本少參考就好」搬進「怎麼看 ?」（#how-ms） */
        ? `最強 <b>${best.m} 月</b>（平均 ${A.fmt.pct(best.avg)}、${best.up}/${best.n} 年上漲）；`
          + `最弱 <b>${worst.m} 月</b>（平均 ${A.fmt.pct(worst.avg)}、${worst.up}/${worst.n} 年上漲）`
        : '';
    };
    const mark = () => $$('#msYears button').forEach(b => b.classList.toggle('on', +b.dataset.v === n));
    $$('#msYears button').forEach(b => b.onclick = () => {
      n = +b.dataset.v; mark(); $('#msCustom').value = ''; say('');
      try { localStorage.setItem('tw.ms.years', n); } catch (e) { /* 忽略 */ }
      paint();
    });
    /* ★ 2026-09-26（Andy：「自填這邊要寫清楚 填寫什麼」）：以前只有一個寫「年」的小框，看不出要填年數還是西元年。
       改成「自填 [輸入年數] 年」＋滑過說明；範圍是 1～這一檔實際有的年數（不是寫死 15）。
       超出範圍 → 夾到最近的有效值、框裡的數字一起改掉，下面一行寫清楚「最多 N 年，已改為 N」，不是默默吞掉。 */
    const cu = $('#msCustom'), hint = $('#msHint');
    const maxY = allYears.length;
    const say = (t) => { if (!hint) return; hint.textContent = t || ''; hint.hidden = !t; };
    if (cu) {
      cu.max = String(maxY);
      cu.title = `輸入要統計的最近 N 年（1～${maxY}，這一檔最多可用 ${maxY} 年）`;
      cu.oninput = () => {
        if (cu.value === '') { say(''); return; }
        const raw = Math.floor(+cu.value);
        if (!Number.isFinite(raw)) return;
        const v = Math.max(1, Math.min(maxY, raw));
        if (v !== raw) { cu.value = String(v); say(raw > maxY ? `最多只有 ${maxY} 年資料，已改為 ${v} 年` : `最少 1 年，已改為 1 年`); }
        else say('');
        n = v; $$('#msYears button').forEach(b => b.classList.remove('on'));
        try { localStorage.setItem('tw.ms.years', n); } catch (e) { /* 忽略 */ }
        paint();
      };
    }
    mark();
    /* 上次存的是自填值（不是 1／3／5／全部）→ 框裡要看得到那個數字，不然四顆鈕都沒亮、看不出現在是幾年 */
    if (cu && n > 0 && ![1, 3, 5].includes(n)) cu.value = String(Math.min(n, maxY));
    paint();
  }
  /* ★ 2026-09-25（審查 R5）：個股「相關新聞」以前是後端給什麼就列什麼 —— 2330 的清單裡出現
     「康舒快充」「訊芯-KY 量產」「聯發科新平台」，跟台積電完全無關（後端的比對條件太寬，另有人修）。
     前端先守一道：**標題或內文**真的提到這檔的代號或名稱才列，其餘不列；一則都沒有就寫「近期無相關新聞」。
     代號用「前後不是數字」比對，免得 2330 撞到 12330 這種數字；名稱去掉 -KY／* 這類後綴再比。*/
  function newsAbout(list, code, name) {
    const nm = String(name || '').replace(/\*/g, '').replace(/-(KY|創|DR)$/i, '').trim();
    const reCode = new RegExp('(^|\\D)' + String(code).replace(/\W/g, '') + '(\\D|$)');
    return (list || []).filter(n => {
      const t = [n.title, n.summary, n.content, n.desc].filter(Boolean).join(' ');
      return reCode.test(t) || (nm.length >= 2 && t.indexOf(nm) >= 0);
    });
  }
  /* ★ 2026-09-26（Andy：「這邊跟相關新聞、券商觀點（新聞引述）、重大訊息合併，並標註屬於哪種新聞」）
     以前三張卡（重大訊息、相關新聞、券商觀點）各自一塊，要上下捲著比對時間。改成**一張時間排序的列表**，
     每一列前面一個類型標籤（琥珀＝重大訊息、青＝新聞、紫＝券商觀點；不用紅綠，紅綠在這個站是漲跌），
     上方分段鈕篩「全部｜重大訊息｜新聞｜券商觀點」。
     · 可信度的差別照樣看得出來：重大訊息是公司自己在公開資訊觀測站的公告（M4 事件面否決靠它），
       新聞是媒體寫的，券商觀點是新聞引述、**不是本站預估**（那一列標籤旁永遠寫著，法遵 🔴）。
     · 券商那一列的字串只從積木出口 BrokerViews.view(rows, 'feed') 拿（欄位只在積木的 pick() 決定）；
       積木被關掉時這一類就是空的，其他照常。
     · 相關新聞仍先過 newsAbout（標題或內文真的提到這檔才列）。 */
  const NEWS_TYPES = [{ v: 'all', t: '全部' }, { v: 'mops', t: '重大訊息' }, { v: 'news', t: '新聞' }, { v: 'broker', t: '券商觀點' }];
  const NEWS_EMPTY = { all: '近期沒有這檔的重大訊息、相關新聞或券商觀點', mops: '近期沒有這檔的重大訊息公告',
    news: '近期無相關新聞', broker: '近 60 天沒有引述到目標價的新聞' };
  function tabNews(pg, el) {
    const esc = A.fmt.esc;
    const news = newsAbout(pg.news, pg.meta.code, pg.meta.name), mn = pg.material_news || [];
    const bv = window.BrokerViews ? window.BrokerViews.view(pg.broker_views || [], 'feed') : [];
    const ORD = { mops: 0, news: 1, broker: 2 };
    const items = [
      ...mn.map(m => ({ t: 'mops', date: String(m.date || ''), time: String(m.time || ''), m })),
      ...news.map(n => ({ t: 'news', date: String(n.date || ''), time: String(n.time || ''), n })),
      ...bv.map(b => ({ t: 'broker', date: String(b.date || ''), time: '', b })),
    ].sort((a, b) => (b.date.localeCompare(a.date)) || (b.time.localeCompare(a.time)) || (ORD[a.t] - ORD[b.t]));
    const TAG = { mops: '重大訊息', news: '新聞', broker: '券商觀點' };
    const tag = (t) => `<span class="ntag ${t}">${TAG[t]}</span>`;
    const row = (it) => {
      if (it.t === 'mops') { const m = it.m;
        return `<details class="ev nrow" data-type="mops"><summary style="cursor:pointer"><div class="nhead">${tag('mops')}<b>${esc(m.subject || '')}</b></div>
            <div class="m"><span class="mono">${esc(m.date || '')}${m.time ? ' ' + esc(m.time) : ''}</span>
              ${m.clause ? `<span class="cat">${esc(m.clause)}</span>` : ''}
              ${m.occurred && m.occurred !== m.date ? `<span>事實發生日 ${esc(m.occurred)}</span>` : ''}<span>公開資訊觀測站</span></div>
          </summary><div class="note" style="white-space:pre-wrap;margin-top:6px">${esc(m.detail || '')}</div></details>`; }
      if (it.t === 'news') { const n = it.n;
        return `<div class="ev nrow" data-type="news"><div class="nhead">${tag('news')}<a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title)}</a></div>
          <div class="m"><span class="mono">${esc(n.date || '')}${n.time ? ' ' + esc(n.time) : ''}</span>${n.category ? `<span class="cat">${esc(n.category)}</span>` : ''}<span>${esc(n.source || '')}</span></div></div>`; }
      const b = it.b;
      return `<div class="ev nrow" data-type="broker"><div class="nhead">${tag('broker')}<small class="nwarn" data-warn title="券商看法是新聞引述，不是本站的預估或建議">不是本站預估</small><a href="${esc(b.url || '#')}" target="_blank" rel="noopener">${esc(b.title)}</a></div>
        <div class="m"><span class="mono">${esc(b.date || '')}</span><span>${esc(b.source || '新聞引述')}</span></div></div>`;
    };
    const cnt = { all: items.length, mops: mn.length, news: news.length, broker: bv.length };
    el.innerHTML = `<div class="card" id="stockNews"><div class="row spread" style="gap:10px;flex-wrap:wrap">
        <h3>公告 / 新聞 ${hq('sknews', '公告 / 新聞')}</h3>
        <a class="pill" href="https://mops.twse.com.tw/mops/web/t05st01" target="_blank" rel="noopener">公開資訊觀測站 ↗</a></div>
      ${hbox('sknews', ['重大訊息＝公司在觀測站的公告',
        `新聞＝提到${esc(pg.meta.name || '')}的媒體報導`,
        '券商觀點＝新聞引述的券商目標價，不是本站預估'])}
      <div class="seg" id="newsSeg" role="group" aria-label="新聞類型" style="margin:8px 0 4px">${NEWS_TYPES.map(x => `<button type="button" data-v="${x.v}"${x.v === 'all' ? ' class="on"' : ''}>${x.t} <span class="mono">${cnt[x.v]}</span></button>`).join('')}</div>
      <div id="newsList">${items.map(row).join('')}</div>
      <div class="empty" id="newsEmpty"${items.length ? ' hidden' : ''}>${NEWS_EMPTY.all}</div></div>`;
    const apply = (v) => {
      $$('#newsSeg button', el).forEach(b => b.classList.toggle('on', b.dataset.v === v));
      let shown = 0;
      $$('#newsList .nrow', el).forEach(r => { const on = v === 'all' || r.dataset.type === v; r.hidden = !on; if (on) shown++; });
      const em = $('#newsEmpty', el);
      if (em) { em.hidden = shown > 0; em.textContent = NEWS_EMPTY[v]; em.classList.toggle('isnews', v === 'news'); }
    };
    $$('#newsSeg button', el).forEach(b => b.onclick = () => apply(b.dataset.v));
    apply('all');
  }

  // _dbg 只給 scripts/_preview.py 驗證用（檢查圖表與繪圖狀態），正式頁面不會呼叫
  /* 產業熱力圖（頂層分頁 #heatmap）。它跟產業地圖吃同一份 industry_map，
     所以路由也走這裡，不用在 app.js 再開一份載入邏輯。*/
  async function routeHeat() {
    A = window.App;
    gpStopLive();
    const im = await A.load('industry_map');
    renderHeat(im);
  }

  window.Industry = { route, routeHeat,
    // 驗收用：族群總覽現在是什麼狀態（族群／個股、幾條、即時開沒開、滑到誰、onLive 被呼叫幾次）
    _gp: () => Object.assign({}, gpDbg, { timer: !!gpTimer }),
    // 驗收用：盤中每幾秒就會走一次這條路，用它驗「重畫不會把使用者的縮放彈回去」
    _apply: () => { if (state._apply) state._apply(); },
    _dbg: () => ({ tf: state.tf, mtf: state.mtfMode, tool: drawTool,
    // 驗收用（2026-10-05 SMC 區域疊圖）：這次畫了哪些區域／線（價位原值）、圖上實際印出哪些標籤、底部小字
    smc: state.smc && kchart && kchart._smc === state.smc ? { tf: state.smc.tf, note: state.smc.note,
      zones: state.smc.zones.map(z => ({ kind: z.kind, low: z.low, high: z.high, since: z.sinceDate, tip: z.tip })),
      lines: state.smc.lines.map(l => ({ kind: l.kind, price: l.price, label: l.label, date: l.date || null })),
      zoneLabels: (kchart.zones.placed || []).map(x => x.label), lineLabels: (kchart.smcLines.placed || []).map(x => x.label) } : null,
    // 驗收用（2026-09-28 分時走勢）：分時圖在不在、畫了幾個點、哪一天、資料來源、顏色方向、這檔是不是確定沒分時、是不是自動退回的
    tick: tchart ? { pts: (tchart.pts || []).length, rows: (tchart.rows || []).length, date: state.tickDate, src: state.tickSrc,
                     dir: tchart.dir, color: tchart.color, prev: tchart.prev, setData: tchart.stats.setData } : null,
    tickNone: state.tickNone || null, tickFb: !!state.tickFb, tfAuto: !!state.tfAuto,
    drawKey: kchart && kchart.draw ? kchart.draw.key : null,
    shapes: kchart && kchart.draw ? kchart.draw.shapes.length : -1,
    hasChart: !!kchart, w: drawW, fill: drawFill,
    // 驗收用：圖上最後一根的日期與收盤、各面板目前高度
    lastBar: kchart && kchart.bars && kchart.bars.length ? String(kchart.bars[kchart.bars.length - 1][0]) : null,
    lastClose: kchart && kchart.bars && kchart.bars.length ? kchart.bars[kchart.bars.length - 1][4] : null,
    paneH: kchart && kchart.paneHeights ? kchart.paneHeights() : null,
    // 驗收用：目前算出幾組背離
    div: kchart && kchart.divergences ? { top: kchart.divergences.top.length, bottom: kchart.divergences.bottom.length } : null,
    // 驗收用：主圖上掛了幾條價位線（停損／目標 2026-09-26 晚拿掉，應該永遠是 0）
    priceLines: kchart && kchart.priceLines ? kchart.priceLines.length : -1,
    /* 驗收用：K 棒實際多寬、畫面上看得到幾根。
       Andy 2026-09-15：「切換到不同時間週期，K棒會很窄」—— 這兩個數字就是那件事的證據，
       只驗「有畫出來」看不出棒子被壓成一條線。 */
    barPx: kchart && kchart.chart ? +kchart.chart.timeScale().options().barSpacing.toFixed(2) : null,
    barsTotal: kchart && kchart.data ? kchart.data.length : 0,
    // 價格軸的上下界：K 棒被壓扁是「軸沒跟著週期重算」，不是棒子變窄
    priceRange: kchart && kchart.priceRange ? kchart.priceRange() : null,
    visibleBars: (() => {
      if (!kchart || !kchart.chart) return null;
      const r = kchart.chart.timeScale().getVisibleLogicalRange();
      return r ? +(r.to - r.from).toFixed(1) : null;
    })(),
    // 驗收用（審查 R5）：K 線上的字有沒有互相壓住 —— 區間標籤放在哪、省略幾個，訊號標記併成什麼，背離字框、圖例框
    fallbackTf: state.fallbackTf || null,
    // 驗收用：即時週期在非交易時段畫的是哪一天（盤中是 null）
    offDay: state.offDay || null,
    zoneLabels: kchart && kchart.zones ? (kchart.zones.placed || []) : [],
    zoneSkipped: kchart && kchart.zones ? (kchart.zones.skipped || 0) : 0,
    markers: kchart && kchart.markerList ? kchart.markerList.map(m => ({ time: String(m.time), i: m.i, pos: m.position, text: m.text })) : [],
    markerNear: kchart && kchart.chart ? Math.max(2, Math.min(12, Math.ceil(60 / (kchart.chart.timeScale().options().barSpacing || 7)))) : null,
    divLabels: kchart && kchart.divPrice ? (kchart.divPrice.lastLabels || []) : [],
    legendRect: kchart && kchart.legendRect ? kchart.legendRect() : null,
    // 2026-09-26 驗收用：主圖上還有沒有 SMC 區塊（應該永遠是 0）、四週期小圖各自有沒有量副圖、量副圖佔幾成
    zoneCount: kchart && kchart.zones ? (kchart.zones.zones || []).length : 0,
    mini: miniCharts.map(c => {
      let ps = []; try { ps = c.chart.panes().map(p => p.getHeight()); } catch (e) { /* 已銷毀 */ }
      const vi = c.paneIndex ? c.paneIndex.vol : null, tot = ps.reduce((a, v) => a + v, 0);
      return { tf: c.tf, panes: ps.length, vol: vi != null, volShare: vi != null && tot ? +(ps[vi] / tot).toFixed(3) : 0,
               zones: c.zones ? (c.zones.zones || []).length : 0, markers: (c.markerList || []).length, bars: (c.data || []).length,
               v4: (c.bars || []).slice(0, 4).map(b => b[5] || 0) };
    }) }) };
})();
