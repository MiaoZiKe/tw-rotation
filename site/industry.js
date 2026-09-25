/* 產業與個股（合併頁）：產業地圖 → 單一產業鏈（族群總覽 + 產品剖析圖 + 分層關聯圖）→ 個股頁。
   個股頁上方永遠帶著它所屬的產業鏈，點任何股票上方同步更新。 */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  let A;                                   // window.App（app.js 提供）
  const state = { level: 0, chain: null, group: null, code: null, tf: '1d', mtfMode: false, cfg: null, tab: 'overview', dg: null };
  /* ★ 2026-09-21：中文名一律先讀 payload（`A.L.chains`，來源是 groups.yaml 的 chains.<id>.name），
     這張表只當「payload 裡沒有的虛擬鍵」與 L 還沒 init 完的 fallback ——
     以前它是第二份對照表，新增的 software / financial 沒補進來就直接印英文 id 上畫面。*/
  const CHAIN_NAME = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子', software: '軟體與資訊服務', financial: '金融', traditional: '傳產', infrastructure: '基礎建設', _other: '其他族群', industry: '法定產業別' };
  const SEG_COLORS = ['#3ee0ff', '#8b7bff', '#ffb454', '#c3ff5b', '#ff8fab', '#5ec8ff', '#f9f871', '#7ee8c7', '#ff9f68', '#b39dff', '#6ee7b7', '#fca5a5', '#93c5fd', '#fde68a'];
  let kchart = null, miniCharts = [];
  // 即時分 K 的訂閱（換頁要退掉，不然背景還在每 5 秒重畫一張看不到的圖）
  let liveOff = null;

  function setLiveNote(txt) {
    const el = document.getElementById('liveNote');
    if (!el) return;
    el.hidden = !txt;
    el.textContent = txt || '';
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
    /* 「放寬蓋住事件面板」是**這一頁**的暫時狀態，換頁就要還原 ——
       不還原的話使用者在產業鏈頁按了放寬，跑去總覽會發現事件面板莫名其妙不見了。
       ★ 2026-09-23：放寬那顆鈕已經跟成分股表一起移除，**這段收尾仍然留著** ——
         使用者可能是在上一版按下放寬之後才重新整理進來的，body 上還掛著 `.memwide`
         卻再也沒有人會把它拿掉，事件面板就會永遠卡在被蓋住的狀態。*/
    if (document.body.classList.contains('memwide')) {
      document.body.classList.remove('memwide');
      if (typeof window.twSetSide === 'function') {
        window.twSetSide(window.twSideWanted ? window.twSideWanted() : true, false);
      }
    }
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
    /* ★ 2026-09-24 說明精簡（Andy：「已經有說明就把表上補充文字拿掉」）：
       原本標題下那段「這張圖回答／怎麼用」搬進「怎麼看 ?」，卡片只留一行短副標。*/
    el.innerHTML = `<div class="card"><div class="row spread"><h3>整個台股一次看 <button class="howbtn pop" data-how="indheat" type="button" aria-label="整個台股一次看怎麼看">?</button></h3>
      <div class="row" style="gap:8px"><label class="hmctl" title="方塊要不要依產業鏈分組">分組：<select id="indTreeGroup" aria-label="熱力圖分組方式">
        <option value="chain"${heatGroup === 'chain' ? ' selected' : ''}>產業鏈</option><option value="flat"${heatGroup === 'flat' ? ' selected' : ''}>不分組</option></select></label>${A.hmDate(im.date)}</div></div>
      <div class="howtxt" id="how-indheat" hidden>${A.howHTML('這張圖回答：今天全市場的錢分佈在哪幾塊、哪一塊在漲。', [
        '方塊大小＝族群成交值（分組時小鏈至少佔 5%）',
        '顏色＝今日漲跌，紅漲綠跌',
        '又大又紅＝錢多而且在漲',
        '大而綠＝資金正在退潮的權值區',
        '點鏈標題進產業鏈，點方塊看它的個股',
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
        if (!d.gid) return A.hmTip(p.name, '', [], '點一下進入這條產業鏈');
        return A.hmTip(p.name, d.chain, [
          { k: '漲跌幅', v: A.fmt.pct(d.chg, 2), c: A.upDown(d.chg), dot: A.hmColor(A.hmBin(d.chg, 'chg'), 'chg') },
          { k: '成交值', v: `${A.fmt.yi(d.to != null ? d.to : p.value)}（${A.fmt.n(d.share, 1)}%）` },
          { k: '成分股', v: `${d.n != null ? d.n : '—'} 檔` },
          { k: '本益比中位', v: d.pe != null ? A.fmt.n(d.pe, 1) : '—' },
        ], '點一下看成分股'); } },
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
    const cn = $('#indChain'); if (cn) cn.innerHTML = '';
    const el = $('#indMap');
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
      tail: '<span class="muted">完整版圖：</span><a class="lk" href="#heatmap" title="方塊大小＝成交值，一眼看出錢集中在哪">產業熱力圖 →</a>',
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
  const GP_LIVE_MS = 60 * 1000;  // 即時每分鐘重算（和輪動時鐘、資金去向同節奏）
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
    let hi = null;                    // 兩圖連動：滑鼠現在停在哪一條／哪一塊
    let barData = [], pieData = [], items = [];
    /* ★ W3-8：圓餅只標前五大，其餘併成一塊灰色的「其他」。
       `pieTopNames` 是「哪幾個族群有自己的扇形」——兩圖連動要靠它把落在「其他」裡的
       那些族群對應回灰色那一塊（不然滑過去會變成沒反應）。*/
    const PIE_TOP = 5;
    const PIE_OTHER = '其他';
    let pieTopNames = [], pieTopShare = 0, pieOtherN = 0;

    /* 標題列只放「標題 ＋ 兩顆鈕」，說明另起一行 ——
       說明擺在同一列的話，長文字會把左邊那一格撐滿，右邊的「即時」被擠到下一行去，
       看起來像一顆浮在半空中、不知道在管什麼的鈕（1440／390 都量到）。*/
    host.innerHTML = `<div class="row spread gphead">
        <h4 id="gpTitle" style="min-width:0"></h4>
        <div class="row gplive">
          <button class="btn small" id="gpBack" type="button" hidden title="回到族群層級的長條圖">← 回到族群</button>
          <span class="rbar"><button class="pb livebtn" id="gpLiveBtn" type="button" aria-pressed="false"
            title="切到盤中即時：用當下的成交價與累積成交量重算漲跌與占比，每分鐘更新（盤中暫定值）">即時</button></span>
          <button class="howbtn" data-how="gp" type="button">怎麼看 ?</button>
        </div>
      </div>
      <!-- ★ 2026-09-24 說明精簡：#gpHint（這張圖回答／怎麼用）與即時的估算口徑搬進「怎麼看 ?」；
           #gpNote 留在卡片上但只寫「現在看的是昨天收盤還是盤中暫定值」一句 —— 那句不能藏（DECISIONS #252 三）。 -->
      <div class="howtxt" id="how-gp" hidden><div id="gpHint"></div></div>
      <div class="note livenote gpnote" id="gpNote"></div>
      <!-- ★ 2026-09-23（W3-8，Andy：「看起來太乾澀了」）：兩張圖各自裝進一張有標題的卡片。
           以前兩張圖裸放在同一片背景上、中間沒有分界 —— 沒有容器，圖就像貼在牆上，
           而且「左邊在講什麼、右邊在講什麼」要靠讀說明才知道。標題直接寫在各自的卡片上。 -->
      <div class="gpgrid">
        <div class="gpcard"><h5>族群漲跌幅</h5><div id="gpBar" class="chart"></div></div>
        <div class="gpcard"><h5>成交值占比</h5><div id="gpPie" class="chart"></div>
          <div class="gplegend" id="gpLegend" aria-label="圖例"></div></div>
      </div>
      <div class="sub" id="gpFocus" style="margin-top:8px"></div>
      ${ctx.tail ? `<div class="linkrow">${ctx.tail}</div>` : ''}`;

    const barEl = $('#gpBar', host), pieEl = $('#gpPie', host), noteEl = $('#gpNote', host);
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
      busy = true; paintNote();
      try {
        if (!window.Live || !window.Live.fetchQuotes) throw new Error('即時報價層還沒載入（live.js）');
        const codes = liveCodes();
        if (!codes.length) throw new Error('這一塊沒有成分股名單，抓不了即時');
        const got = {};
        for (let i = 0; i < codes.length; i += GP_LIVE_BATCH) {
          Object.assign(got, await window.Live.fetchQuotes(codes.slice(i, i + GP_LIVE_BATCH)));
        }
        if (gen !== gpGen) return;          // 回來的時候使用者已經換頁了，這一輪整個丟掉
        q = got; liveErr = '';
        liveAt = Object.keys(got).map(k => got[k] && got[k].time).filter(Boolean).sort().pop() || '';
        const ks = Object.keys(got).filter(k => got[k] && got[k].price != null);
        cov = [ks.length, codes.length];
      } catch (e) {
        if (gen !== gpGen) return;
        liveErr = String((e && e.message) || e).slice(0, 80); q = null; cov = [0, 0];
        // 第二道：萬一哪條路漏掉 live.js 的轉譯，英文的網路錯誤仍然不准原樣上畫面（R3 審查）
        if (/failed to fetch|networkerror|load failed/i.test(liveErr)) liveErr = '連不到報價代理（網路不通或被擋）';
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
      live = !live;
      liveBtn.classList.toggle('on', live);
      liveBtn.setAttribute('aria-pressed', live ? 'true' : 'false');
      stopTimer();                      // 先停再開，計時器永遠只有一個
      if (!live) { q = null; liveErr = ''; cov = [0, 0]; paint(); return; }
      paint();                          // 先把「抓取中」寫上去，不要讓畫面看起來沒反應
      liveTick();
      gpTimer = setInterval(() => { if (!document.hidden && live) liveTick(); }, GP_LIVE_MS);
    };
    backBtn.onclick = () => {
      drill = null; hi = null;
      if (live) { q = null; liveTick(); }
      paint();
      if (ctx.onBack) ctx.onBack();
    };

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
      pieData = top.map(d => ({ name: d.name, value: Math.max(0, d.val || 0), key: d.key,
        itemStyle: { color: d.color, borderColor: CH.panel, borderWidth: 1 } }));
      if (otherVal > 0) {
        pieData.push({ name: PIE_OTHER, value: otherVal, key: '_rest',
          itemStyle: { color: A.hexA(CH.ink3, .38), borderColor: CH.panel, borderWidth: 1 } });
      }
      /* 中心那個數字一定要**真的算**（前五大的占比相加），不准寫死、不准用估的 */
      pieTopShare = total > 0 ? top.reduce((s2, d) => s2 + (d.val || 0), 0) / total * 100 : 0;
      pieOtherN = otherN;
      return { asc, total, restN, restVal };
    }

    function paintNote() {
      const day = ctx.asOf ? `資料日期 ${ctx.asOf}` : '最新一個交易日';
      /* ★ 2026-09-24 說明精簡：這一行只講「現在是哪一種數字」；估算怎麼算、涵蓋率怎麼讀搬進「怎麼看 ?」。
         ⚠ 即時時「盤中暫定值」「估算」「涵蓋幾檔」三件事**一定留在畫面上**（DECISIONS #252 三：即時是估算，畫面上一定要寫出來）。*/
      if (!live) {
        noteEl.innerHTML = `<b>昨天（盤後收盤）</b>　${day}`;
        return;
      }
      if (busy && !q) { noteEl.innerHTML = '<b class="live">即時</b>　抓取中…'; return; }
      if (liveErr) {
        noteEl.innerHTML = `<b class="bad">即時抓不到報價</b>　${A.fmt.esc(liveErr)}`
          + `　<span class="muted">仍畫 ${day} 收盤值；再按「即時」關掉</span>`;
        return;
      }
      noteEl.innerHTML = `<b class="live">⚡ 盤中暫定值</b>　報價 ${A.fmt.esc(liveAt || '—')}`
        + `　<span class="warn">成交值估算</span>　涵蓋 ${cov[0]} / ${cov[1]} 檔`;
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
            + `　<span class="muted">量都太小，沒有各自的扇形</span>`
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
        + (d.live ? '　<span class="live">⚡ 盤中</span>' : (live ? '　<span class="muted">（這一個抓不到即時，是收盤值）</span>' : ''))
        + `　<span class="muted">${drill ? '點一下進個股頁' : '點一下看它的個股'}</span>`;
    }

    /* 甜甜圈中心兩行字（標題＋大數字）。top 用像素算：圓心在 cy，兩行字的總高約 52px。*/
    function pieCenter(cy, t1, t2) {
      const ff = 'Noto Sans TC, sans-serif';
      return [
        { text: t1, left: '50%', top: cy - 30, textAlign: 'center',
          textStyle: { color: CH.ink3, fontSize: 12.5, fontWeight: 400, fontFamily: ff, width: 120, overflow: 'truncate' } },
        { text: t2, left: '50%', top: cy - 10, textAlign: 'center',
          textStyle: { color: CH.ink, fontSize: 34, fontWeight: 700, fontFamily: A.MONO } },
      ];
    }
    /* 圖下方兩欄的圖例：● 名稱 ＋ 百分比（等寬、靠右）。滑過＝跟滑過扇形同一支 setHi；點＝跟點扇形同一支 onPick。*/
    function paintLegend() {
      const el = $('#gpLegend', host); if (!el) return;
      const tot = pieData.reduce((s2, d) => s2 + (d.value || 0), 0) || 1;
      el.innerHTML = pieData.map(d => `<button type="button" class="lg${d.name === PIE_OTHER ? ' other' : ''}" data-n="${A.fmt.esc(d.name)}" title="${A.fmt.esc(d.name)}">`
        + `<i style="background:${(d.itemStyle || {}).color || CH.ink3}"></i><span class="nm">${A.fmt.esc(d.name)}</span>`
        + `<span class="pc">${A.fmt.n(d.value / tot * 100, 1)}%</span></button>`).join('');
      $$('.lg', el).forEach(bn => {
        bn.onmouseenter = () => setHi(bn.dataset.n);
        bn.onmouseleave = () => setHi(null);
        bn.onclick = () => { if (bn.dataset.n !== PIE_OTHER) onPick(bn.dataset.n); };
      });
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
        const ph2 = parseFloat(pieEl.style.height) || pieEl.clientHeight;
        const tot = pieData.reduce((s2, d) => s2 + (d.value || 0), 0) || 1;
        const hd = pieHi ? pieData.find(d => d.name === pieHi) : null;
        pi.setOption({
          // 中心：滑到某一塊就寫它的名字與百分比，滑開回到「前五大 xx%」
          title: hd ? pieCenter(Math.round(ph2 * 0.5), hd.name, A.fmt.n(hd.value / tot * 100, 1) + '%')
            : pieCenter(Math.round(ph2 * 0.5), '前五大', A.fmt.n(pieTopShare, 1) + '%'),
          series: [{ data: pieData.map(d => ({ ...d,
            itemStyle: { ...d.itemStyle, borderWidth: d.name === pieHi ? 3 : 1, borderColor: d.name === pieHi ? CH.ink : CH.panel } })) }] });
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
      paint();
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
      /* ★ 2026-09-24 甜甜圈改版：圖例搬到圖下方（兩欄），圖本身讓出那一塊，兩張卡片仍然一樣高。*/
      const legRows = Math.ceil(Math.min(6, (pieData.length || 1)) / 2);
      const legH = legRows * 24 + 12;
      /* 窄畫面兩張卡上下疊（.gpgrid ≤820px 單欄），這時甜甜圈不必跟長條一樣高 ——
         跟長條一樣高的話 390px 上甜甜圈上下各空出一大片（截圖量到約 200px 的空白）。改成「寬多少、高就差不多多少」。*/
      const stacked = (() => { try { return window.matchMedia('(max-width:820px)').matches; } catch (e) { return false; } })();
      const pw = pieEl.clientWidth || 360;
      const pieH = stacked ? Math.min(Math.max(220, h - legH), Math.max(240, Math.round(pw * 0.86))) : Math.max(220, h - legH);
      barEl.style.height = h + 'px'; pieEl.style.height = pieH + 'px';
      backBtn.hidden = !drill;
      $('#gpTitle', host).innerHTML = drill
        ? `${A.fmt.esc(drill.name)}　<small class="muted">這個族群的個股漲幅（${b.asc.length}／${(drill.members || []).length} 檔）</small>`
        : `${A.fmt.esc(ctx.scope)}族群漲幅與占比　<small class="muted">列出成交值前 ${b.asc.length} 個族群</small>`;
      /* ★ 2026-09-24 說明精簡：同一份內容改成「一句問題 → 條列 → 最下面一行小字」，住在「怎麼看 ?」裡。*/
      const gpFine = '甜甜圈其餘併成「其他」，中心寫前五大合計；滑過任一邊，另一邊對應的那一塊同步標起來，下方那行寫出它的數字。'
        + '按「即時」＝盤中暫定值，每分鐘更新：成交值是<b>估算</b>的（即時端點沒有每檔的累積成交金額，用「最新價 × 累積張數」推算，和輪動時鐘的即時同一個口徑），'
        + '漲跌幅是這批個股的成交值加權；抓不到報價的仍用收盤值，所以占比只能當「相對大小」看。';
      $('#gpHint', host).innerHTML = drill
        ? A.howHTML('這張圖回答：這個族群裡今天是誰在漲、量能集中在哪幾檔。', [
          '左邊長條由高到低，紅漲綠跌',
          '右邊甜甜圈只標成交值前五大',
          '怎麼用：漲得多、量也大＝主流',
          '只有漲幅、成交值卻小＝多半是跟風',
          '點長條進個股頁；「← 回到族群」回上層',
        ], gpFine)
        : A.howHTML(`這張圖回答：${A.fmt.esc(ctx.scope)}今天哪一個族群在漲、錢集中在誰身上。`, [
          '左邊長條看方向，紅漲綠跌、由高到低',
          '右邊甜甜圈看份量，只標前五大',
          '怎麼用：兩邊都靠前＝今天真正的主流',
          '長條長、圓餅小＝小族群在噴，量未跟上',
          '點長條，原地換成該族群的個股',
        ], gpFine);
      paintNote();
      const axl = { ...A.axisStyle.axisLabel, fontSize: 11.5 };
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
            + `<br><small>${drill ? '點一下進個股頁' : '點一下看它的個股'}</small>`; } },
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
         W3-8 的「中心數字是真的算出來的」「只標前五大＋其他」「連動到其他」全部照舊。*/
      const ph = parseFloat(pieEl.style.height) || h;
      const cy = Math.round(ph * 0.5);
      A.chart(pieEl, {
        tooltip: { ...A.tip, trigger: 'item', formatter: p => {
          const d = items.find(x => x.name === p.name);
          return `<b>${A.fmt.esc(p.name)}</b><br>成交值 ${A.fmt.yi(p.value)}（${A.fmt.n(p.percent, 1)}%）`
            + (d ? `<br>漲跌 <span style="color:${A.upDown(d.chg)}">${A.fmt.pct(d.chg)}</span>` : '')
            + (d ? `<br><small>${drill ? '點一下進個股頁' : '點一下看它的個股'}</small>` : '<br><small>其餘的量太小，沒有畫成長條</small>'); } },
        title: pieCenter(cy, '前五大', A.fmt.n(pieTopShare, 1) + '%'),
        animationDurationUpdate: 200,
        series: [{ type: 'pie', radius: ['58%', '78%'], center: ['50%', cy], minAngle: 2, padAngle: 1.2,
          avoidLabelOverlap: false, cursor: 'pointer', label: { show: false }, labelLine: { show: false },
          itemStyle: { borderRadius: 6 },
          emphasis: { scale: true, scaleSize: 4, label: { show: false } },
          data: pieData },
        // 環內側的細軌道：只是一圈底，不能點、沒有提示框、不參與連動
        { type: 'pie', radius: ['55%', '55.8%'], center: ['50%', cy], silent: true, animation: false,
          label: { show: false }, labelLine: { show: false }, tooltip: { show: false }, emphasis: { disabled: true },
          itemStyle: { borderRadius: 0 },
          data: [{ name: '_track', value: 1, itemStyle: { color: A.hexA(CH.ink3, .22) } }] }],
      }, { notMerge: true });
      paintLegend();
      const bi = window.echarts && echarts.getInstanceByDom(barEl);
      const pi = window.echarts && echarts.getInstanceByDom(pieEl);
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
        hi: null, liveCalls: gpDbg.liveCalls, drill: drill ? drill.id : null };
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
  const EST_TIP = '產業推論＝我們從兩段公開資訊推出來的，不是公司或媒體講過的；看的時候要打折。';
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
      + `<a class="segchip${dgId ? '' : ' sel on'}" data-dgtab="overview" href="#industry/${ch.id}/overview" role="tab" style="--c:var(--cyan)" title="這條鏈各族群的漲幅與占比（第一個分頁）"><i></i>族群總覽</a>`
      + dgOpts.map(id => `<a class="segchip${id === dgId ? ' sel on' : ''}" data-dgid="${id}" href="${dgHash(id)}" role="tab" style="--c:${A.L.gcolor[id] || 'var(--cyan)'}" title="${A.fmt.esc(DS.name(id))}${DS.q(id) ? '　·　' + A.fmt.esc(DS.q(id)) : ''}"><i></i>${A.fmt.esc(dgShortName(id))}</a>`).join('')
      + `</div>`;
    /* 產業地圖那一層的內容留在 DOM 裡的話，`#chainSwitch`／`#gpBar` 會同時出現兩份
       （一份看得見、一份被 display:none 藏著），getElementById 只拿得到前面那個。*/
    { const mp = $('#indMap'); if (mp) mp.innerHTML = ''; }
    gpStopLive();
    el.innerHTML = `
      ${chainTabsHtml(im, ch.id)}
      <div class="card nbcard">
        <!-- ★ 2026-09-24 說明精簡：頁首那段「同一套顏色、點了會怎樣」(#nbIntro) 搬進「怎麼看 ?」，頁首只留鏈名。 -->
        <div class="row spread nbhead" data-howsec><h2>${A.fmt.esc(ch.name)}${state.group && ch.id === 'industry' ? ' · ' + A.fmt.esc((groups[0] || {}).name) : ''}</h2>
          ${hasSlots || hasMap ? '<button class="howbtn" data-how="nb" type="button">怎麼看 ?</button>' : ''}</div>
          ${/* ★ 2026-09-24（審查 R3）：這段說明以前還在講退版前的「關聯圖大圓點／個股小點」，
                 而且沒有關聯圖的鏈（傳產、基礎建設）也照樣講關聯圖與色標。改成照這一頁真的有什麼來講：
                 有剖析圖 × 有關聯圖三種組合各一份，不提畫面上沒有的東西。*/ ''}
          ${hasSlots || hasMap ? `<div class="howtxt" id="how-nb" hidden><div id="nbIntro">${hasSlots && hasMap
            ? A.howHTML('這一頁回答：這條鏈由哪些環節組成、每一格有誰。', [
              '零件、環節選單、關聯圖公司卡同一套顏色',
              '點零件：關聯圖上同一格的公司卡一起亮',
              '從「環節 ▾」選一格：圖上亮起、右邊列出族群與個股',
              '點關聯圖的公司卡，右側展開產業關係',
              '看誰在漲：回「族群總覽」點一個族群',
            ], '點公司卡不跳頁，同時把它所屬的環節一起選起來；圖下方的環節詳情寫出那一格有哪幾檔台股、哪幾家外商、對應哪些族群。手機上環節選單是一排色標。')
            : hasSlots
              ? A.howHTML('這一頁回答：這條鏈的產品由哪些零件組成、每一格是誰做的。', [
                '點零件：看它是誰做的（供應商）',
                '同色的零件屬於同一個環節',
                '看誰在漲：回「族群總覽」點一個族群',
              ], '這條鏈還沒有供應鏈關聯圖（supply_chain.yaml 還沒有這條鏈的環節）。')
              : A.howHTML('這一頁回答：這條鏈由哪些環節組成、每一格有誰。', [
                '環節選單、關聯圖公司卡同一套顏色',
                '從「環節 ▾」選一格：圖上亮起、右邊列出族群與個股',
                '點公司卡，右側展開產業關係',
              ], '這條鏈還沒有產品剖析圖。點公司卡不跳頁。手機上環節選單是一排色標。')}</div></div>` : ''}
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
          <div class="dgsectitle"><small class="muted" id="dgTitle"></small></div><span class="row" id="dgTools" style="gap:6px"><button class="howbtn" data-how="dg" type="button">怎麼看 ?</button><span class="seg tiny dgmode" id="dg3d" role="group" aria-label="剖析圖顯示方式：平面或立體" hidden><button type="button" data-dm="2d" class="on" aria-pressed="true" title="平面剖析圖（可左右滑）">2D</button><button type="button" data-dm="3d" aria-pressed="false" title="立體剖析圖（可拖曳轉動、滾輪拉近）">3D</button></span><span class="pill" id="dgDrag" style="cursor:pointer" hidden title="左鍵拖曳要轉動還是平移（右鍵一律平移）">拖曳：轉動</span><span class="pill" id="dgReset" style="cursor:pointer" hidden>重設視角</span><span class="pill" id="dgAnim" style="cursor:pointer">動畫：開</span><span class="pill" id="dgFold" style="cursor:pointer">收合圖 ▴</span></span></div>
          <!-- ★ 2026-09-24 說明精簡：「這張圖回答」(#dgQ) 與操作說明搬進「怎麼看 ?」；圖名與「原創示意圖，非實物比例」留在 #dgTitle。 -->
          <div class="howtxt" id="how-dg" hidden><div id="dgQ"></div>${A.howHTML('', [
            '點零件：看它是誰做的（供應商）',
            '同色的環節色標、關聯圖會一起亮',
            '右上可開關動畫、收合圖',
            '有「2D｜3D」的圖，切到 3D 可拖曳轉動',
            '圖以原尺寸顯示，放不下可左右滑',
          ], '原創示意圖，非實物比例；字不跟著縮小（最小 12px）。')}</div>
          <div id="dgBody">
          <div id="prodDiagram" class="dgwrap" style="transition:opacity .18s">${dgId ? DS.draw(dgId) : ''}</div><div id="prod3d" class="dg3d" hidden></div><div class="note" id="dg3dNote" hidden></div><div id="partCard" class="partcard" hidden></div></div></div>` : ''}
        </div>
        ${hasMap ? `<div class="relsec" id="relSec" data-howsec>
          <div class="row spread" id="relHead"><h4 style="margin:0">供應鏈關聯圖</h4>
            <span class="row" style="gap:6px"><span class="seg relsw" id="relView"><button type="button" data-rv="layer">分層圖</button><button type="button" data-rv="flow">流向圖</button></span><span class="pill" id="relFold" style="cursor:pointer">收合圖 ▴</span><button class="howbtn" data-how="rel" type="button">怎麼看 ?</button></span></div>
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
              <div class="segdd" id="segDD"><button type="button" class="ddbtn" id="segDDBtn" aria-haspopup="listbox" aria-expanded="false" title="選一個環節：圖上只亮那一格，右邊列出那一格的族群與個股">環節：<b>全部</b><i aria-hidden="true">▾</i></button>
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
    let segFilter = opts.seg || null;
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
      highlightSegments(el, segsOn, color, partHi);
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
      const t = $('#dgTitle', el), q = $('#dgQ', el);
      if (t) {
        /* 說明精簡：圖名＋誠實標示留在畫面；「點零件看供應商／原尺寸可左右滑」搬進「怎麼看 ?」 */
        t.textContent = dgId
          ? `${DS.name(dgId)}　·　原創示意圖，非實物比例`
          /* 沒有選圖＝正在看族群總覽。以前這裡寫「在下面選一張」是指圖別選單，
             選單移除之後要改成指**上方的分頁列**，不然會叫使用者去看一個不存在的東西。*/
          : `共 ${dgOpts.length} 張剖析圖，在上方分頁選一張`;
      }
      if (q) q.innerHTML = (dgId && DS.q(dgId)) ? `<b class="howq">這張圖回答：${A.fmt.esc(DS.q(dgId))}</b>` : '';
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
      /* 說明精簡：「怎麼看 ?」的鈕住在 #dgTools 裡，回族群總覽時鈕被藏起來 —— 盒子也要一起收，不然會留一段舊圖的說明 */
      if (!on) { const hb = $('#how-dg', el), hbtn = $('.howbtn[data-how="dg"]', el);
        if (hb) hb.hidden = true; if (hbtn) { hbtn.classList.remove('on'); hbtn.textContent = '怎麼看 ?'; } }
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
         · 圖上的公司卡／個股標籤（.co）、環節標題（.segtitle，流向圖的方塊也掛這個 class）、▸▾ 收合鈕與「全部收合」列
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
        isOpen: () => relStick.isConnected && (
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
         ② 舊版只有一種畫法。現在兩種都做出來、做成畫面上可以切的：
            **分層圖**（節點＝公司卡，依環節排成直欄，上游→下游由左往右，固定走線帶箭頭）＝ 預設，
            **流向圖**（節點＝環節本身，帶寬＝兩格之間的關係條數，看得出「量往哪邊走」）。
            偏好記在 localStorage `tw.relView`，不拿來問 Andy。
         ③ Default 畫面就要看得到「這一格的上游是誰、下游是誰」與底下的個股標籤 —— 那是 `#chainList`。
         ④ 環節詳情與跨鏈對照預設收起（`#segBox` 是空的），點色標／點環節卡才展開。
       點個股標籤或公司卡 → 右側 `#coBox.relside` 資訊欄（窄畫面 <1100px 自動掉到圖下方）。*/
    if (hasMap && sc) {
      /* 點環節卡＝「我要看這一格」（真的篩），刻意跟「點剖析圖零件」（只亮不篩，DECISIONS #73）分開。*/
      const segPick = (seg) => { segFilter = segFilter === seg ? null : seg; segHi = null; partHi = partSel = null; state.group = null; syncHighlight(); };
      /* 點個股標籤：原地開右側資訊欄（不跳頁，N7），同時把它所屬的環節選起來。
         noscroll ＝ 使用者的眼睛就停在剛剛點的那張標籤上，不要把頁面捲走。*/
      const coPick = (co) => { if (!co || !co.segment) return; segFilter = co.segment; segHi = null; partHi = partSel = null; state.group = null; syncHighlight({ noscroll: true }); };
      const stat = drawSegList($('#chainList', el), sc, ch.id, im, { onSegment: segPick, onCompany: coPick });
      const mapHost = $('#chainMap', el);
      let relView = loadRelView();
      /* ★ 2026-09-24 說明精簡：兩種圖的說明改成條列，住在「怎麼看 ?」（#how-rel）裡；圖例口徑放最下面一行小字。*/
      const HINT = {
        layer: (st) => A.howHTML('這張圖回答：這條鏈由哪幾格組成、每一格有誰、誰供貨給誰。', [
          st,
          '怎麼用：左上游、右下游，先找你那檔',
          '往左看誰在供貨（常慢一兩天才反應）',
          '往右看它賣給誰（下游轉弱會被拖到）',
          '滑過卡片或環節標題：提亮上下游、看說明',
        ], '線越粗依存度越高；虛線＝委外、點虛線＝終端指定料號；灰線＝設備／材料；虛線框＝外商；<b style="color:#d9a441">?</b>＝還沒建立上下游關聯。'),
        flow: (st) => A.howHTML('這張圖回答：這條鏈的關係量集中在哪兩格之間。', [
          st,
          '怎麼用：先看最粗的帶子＝這條鏈的主幹',
          '主幹兩端的族群才是行情的主戰場',
          '細到看不見的是邊陲，利多影響小得多',
          '點一格就篩到那一格；滑過一格看它的說明與上下游',
        ], '方塊高度＝這一格的台股檔數；帶子寬度＝兩格之間已建立的上下游關係條數。'),
      };
      /* 容器寬度變了就要重畫：欄寬、欄距、左右內距全部是依容器寬度算出來的。
         最常見的觸發不是改視窗，是**點一檔個股** —— 右側資訊欄（340px）一出現，
         圖的容器就從 998px 縮到 646px，不重畫的話剛剛量好的置中當場歪掉、內容還會溢出。
         `lastW` 是防止 ResizeObserver 自己咬自己：重畫會改 SVG 高度、又觸發一次觀察。*/
      let lastW = -1;
      const drawMap = () => {
        if (!mapHost) return;
        lastW = mapHost.clientWidth;
        if (relView === 'flow') drawSegFlow(mapHost, sc, ch.id, im, { onSegment: segPick });
        else drawChainMap(mapHost, sc, ch.id, im, {
          onSegment: (seg) => { segHi = segHi === seg ? null : seg; segFilter = null; partHi = partSel = null; syncHighlight({ quiet: true }); },
          /* 點公司＝連同它所屬的**環節**一起選起來（不是族群）：一家公司只有一個 segment，
             卻可能掛好幾個族群，選族群就得替他猜一個。環節推族群是自動成立的（A.L.sgroups）。*/
          onFold: () => syncHighlight({ quiet: true, noscroll: true }),
          onCompany: (co) => { if (!co || !co.segment) return; segFilter = co.segment; segHi = null; partHi = partSel = null; state.group = null; syncHighlight({ noscroll: true }); },
        });
        const hint = $('#relHint', el);
        if (hint) hint.innerHTML = HINT[relView](`這條鏈 ${stat.nSeg} 格、${stat.nTw} 檔台股、${stat.nEdge} 條上下游關係`);
        $$('#relView button', el).forEach(b => b.classList.toggle('on', b.dataset.rv === relView));
      };
      /* ★ 2026-09-25 效能（perf-2）：關聯圖在剖析圖下面（1440×900 首屏看不到），改成捲近了（或瀏覽器閒下來）才畫。
         以前跟剖析圖在同一個任務裡畫：drawMap 一開頭讀 clientWidth，逼整頁（含剛插進去的剖析圖）當場排版，
         實測首次開 #industry/semiconductor 這一支自己 202ms。已經在畫面裡（窄畫面、沒有剖析圖的鏈）就跟以前一樣當場畫。
         延後畫完要把目前的選取狀態補畫上去（syncHighlight 宣告在後面，當場畫的那一次交給 renderChain 最後那一行）。*/
      /* ⚠ 不用 App.whenNear：它一進來就讀 getBoundingClientRect 判斷「在不在首屏」—— 那本身就是這裡要避開的強制排版。
         上面有剖析圖（桌機、這條鏈有圖）時關聯圖一定在首屏以下，直接交給 IntersectionObserver ＋ 閒置補畫；
         沒有剖析圖或手機寬時照舊當場畫。*/
      const mapBelow = !!(mapHost && hasSlots && dgId && window.innerWidth > 640);
      if (mapBelow) deferNear(mapHost, () => { if (!mapHost.isConnected) return; drawMap(); syncHighlight({ quiet: true, noscroll: true }); });
      else drawMap();
      // 滑過環節的說明框（圖上的環節標題、沒有台股那格的說明、流向圖方塊共用一個）
      wireSegTip($('#relSec', el), sc, ch.id);
      $$('#relView button', el).forEach(b => b.onclick = () => {
        if (relView === b.dataset.rv) return;            // 已經在這個模式就不要白重畫一次
        relView = b.dataset.rv; saveRelView(relView); drawMap();
        syncHighlight({ quiet: true, noscroll: true });  // 換圖之後選取狀態要跟著畫回去
      });
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
        const sw = $('#relView', el); if (sw) sw.hidden = !relOpen;
        if (foldRel) { foldRel.textContent = relOpen ? '收合圖 ▴' : '展開關聯圖 ▾'; foldRel.classList.toggle('cyan', !relOpen); }
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
        if (host3) { host3.hidden = true; host3.innerHTML = ''; }
        if (note3) note3.hidden = true;
        // ★ 配色不在這裡：它跟著全站主題自動走（見 wirePal），收掉 3D 不等於收掉配色
        ['dg3d', 'dgDrag', 'dgReset'].forEach(id => { const b = $('#' + id, el); if (b) b.hidden = true; });
        host.hidden = false; host.innerHTML = ''; host.style.opacity = '1';
        paintDgMode();
        swapping = false;
        return;
      }
      paintDgTitle();
      host.style.opacity = '0';
      setTimeout(() => {
        /* 換圖之前一定要先收掉 3D：新的那張可能根本沒有 3D 場景，
           不收的話畫面會停在上一張的 WebGL 場景上（看起來像換圖沒生效）。*/
        dispose3D();
        const host3 = $('#prod3d', el), note = $('#dg3dNote', el);
        if (host3) { host3.hidden = true; host3.innerHTML = ''; }
        if (note) note.hidden = true;
        // ★ 配色不在這裡：它跟著全站主題自動走（見 wirePal），收掉 3D 不等於收掉配色
        ['dg3d', 'dgDrag', 'dgReset'].forEach(id => { const b = $('#' + id, el); if (b) b.hidden = true; });
        host.hidden = false;
        host.innerHTML = DS.draw(next);
        paintDgMode();        // 從「選單」換回「有圖」時要先把 #dgBody 打開，3D 才量得到尺寸
        wireDg(!dgOpen);      // 收合狀態下不要順手把 3D 掛起來（手機背景多一個 WebGL context）
        did3d = dgOpen;       // 收合時換的圖 3D 還沒接線 → 展開時 paintFold 要補接
        host.style.opacity = '1';
        swapping = false;
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
    return `<span class="pc-co">${who}<span class="pc-why">${why ? A.fmt.esc(why) : '（這家的負責項目 supply_chain.yaml 還沒填）'}</span></span>`;
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
    const noneRow = tw.length ? '' : `<div class="pc-row"><span class="k">台股有沒有人做</span><span class="pc-none">${
      def && def.none ? A.fmt.esc(def.none)
        : (fo.length ? `台股沒有廠商做這一格，實際上做的是：${A.fmt.esc(fo.map(c => c.name + ((c.tech || []).length ? '（' + c.tech.join('、') + '）' : '')).join('、'))}。`
          : '查不到這一格是誰做的 —— supply_chain.yaml 還沒有這一格的公司。查不到就寫查不到，不編一個對應。')
    }</span></div>`;
    const foRow = (tw.length && fo.length)
      ? `<div class="pc-row"><span class="k">同一格的外商</span>${fo.map(coHtml).join('')}</div>` : '';
    const itemRows = (def && def.items) ? itemsRow('相關料號', inn) : (itemsRow('進料', inn) + itemsRow('出貨', out));
    const noItem = (!inn.length && !out.length)
      ? '<div class="pc-row"><span class="k">相關料號</span><span class="pc-miss">這一格目前查不到具名的上下游料號（supply_chain.yaml 的 edges 還沒有這一格的邊）。</span></div>' : '';

    box.hidden = false;
    box.style.setProperty('--c', segColor(seg));
    box.innerHTML = `<div class="pc-hd"><span class="pc-dot"></span><span class="pc-t">${A.fmt.esc(name)}</span>
        <button type="button" class="pc-seg" id="pcSeg" title="把整張圖聚焦到「${A.fmt.esc(segNm)}」這一格">環節：${A.fmt.esc(segNm)} →</button>
        <span class="pc-btns"><button type="button" id="pcFold">${o.open ? '收合 ▴' : '展開 ▾'}</button></span></div>
      <div class="pc-bd" id="pcBody"${o.open ? '' : ' hidden'}>
        ${desc ? `<div class="pc-desc">${A.fmt.esc(desc)}</div>` : ''}
        ${twRow}${noneRow}${foRow}${itemRows}${noItem}
        ${def && def.note ? `<div class="pc-note">★ ${A.fmt.esc(def.note)}</div>` : ''}
        <div class="pc-ft">公司與「負責什麼」讀 supply_chain 的 <b>companies[].tech</b>，料號讀 <b>edges[].item</b>；標籤是資料可信度（官方揭露／媒體報導／產業推論）。點零件只會亮起來，<b>不會</b>把整張圖聚焦到那一格 —— 要聚焦請按上面的「環節」。</div>
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
      ${cids.map(c => A.fmt.esc(A.L.chains[c] || CHAIN_NAME[c] || c)).join('、')}　<span class="muted">兩張架構圖裡它的位置與上下游都不一樣</span></div>${panels}</div>`;
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
  function highlightSegments(root, segs, color, part) {
    const on = new Set(segs || []);
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
    $$('.chainmap .co', root).forEach(n => n.classList.toggle('dim', on.size > 0 && !on.has(n.dataset.segment)));
    $$('.chainmap .segtitle', root).forEach(n => n.classList.toggle('sel', on.has(n.dataset.seg)));
    /* 環節卡清單（2026-09-23 C5 退版之後回來了）：選到的那一格 `.sel`、其餘 `.dim`。
       手機上還要順手把那張卡攤開 —— 不然「選起來了」但個股標籤還收著，看起來像沒反應。
       流向圖模式下的環節方塊沿用 `.segtitle`，所以上面那兩行一併把它也處理掉了。*/
    $$('.seglist .segcard', root).forEach(n => { const hit = on.has(n.dataset.seg);
      n.classList.toggle('sel', hit);
      n.classList.toggle('dim', on.size > 0 && !hit);
      if (hit && on.size === 1 && segListReveal) segListReveal(n); });
  }
  /* ---------------------------------------------------------------- 3D 剖析圖（Three.js）
     Andy 拍板「先試試看 three.js」。四條硬性驗收都在這裡兌現：
       可以轉、點零件會亮並帶出台股、標籤是 DOM、WebGL 不能用就退回 SVG。
     three.js 是動態載入的，只有真的按下 3D 才付那 670KB。*/
  let view3d = null;                 // 目前掛著的 3D 場景（沒有就是 null）
  // 動畫偏好（平面圖與 3D 共用同一個開關）；沒設定過就是開
  const animPref = () => { try { return localStorage.getItem('tw.dganim') !== '0'; } catch (e) { return true; } };

  function dispose3D() { if (view3d) { try { view3d.dispose(); } catch (e) { /* 忽略 */ } view3d = null; } }

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

  function wire3D(el, chainId, hooks) {
    const hk = hooks || {};
    const onSeg = hk.onSeg || (() => { /* 沒接就不做事 */ });
    const sync = hk.sync || (() => { /* 沒接就不做事 */ });
    const btn = $('#dg3d', el), rst = $('#dgReset', el), note = $('#dg3dNote', el);
    const drg = $('#dgDrag', el);     // 配色已經不是一顆鈕了（跟著全站主題走，見 wirePal）
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
    /* ★ 2026-09-26（Andy：「切回 2D 時，顯示 2D，不要都 3D」）：
       以前這是一顆開關「3D 立體」，2D 時寫「3D 立體」、3D 時寫「3D 立體 ✓」——
       不管在哪個模式，眼睛讀到的都是「3D」，看不出現在到底是哪一種。
       改成分段鈕「2D｜3D」，**亮的那一格就是現在的模式**（樣式跟同一頁的「分層圖｜流向圖」同一種 .seg）。
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
      // 「拖曳：轉動」「重設視角」只對 3D 有意義 —— 2D 時整顆藏起來，不留一顆按了沒反應的鈕
      rst.hidden = !on;
      if (drg) drg.hidden = !on;
      svg.hidden = on; host.hidden = !on;     // 配色不跟著 3D 開關（2D 也吃同一組 --dg-*）
      /* 切換 2D／3D 之後重套一次「原尺寸」規則：native 的橫向捲動只給 2D，
         3D 一律不捲（見 applyDgNative 的註解）。不重套的話切回 2D 會少掉捲動、
         切到 3D 又會留著上一輪的 overflow 設定。*/
      applyDgNative(svg, svg.dataset.dgid || '');
      if (!on) { dispose3D(); note.hidden = true; sync(); return; }
      note.hidden = false;
      note.textContent = '載入 3D 中…';
      dispose3D();
      host.innerHTML = '';
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
        });
      } catch (err) {
        // 起不來就要講出來，不能停在「載入 3D 中…」讓人以為當掉了
        note.textContent = '3D 起不來（' + (err && err.message ? err.message : err) + '），已退回平面剖析圖。';
        svg.hidden = false; host.hidden = true; rst.hidden = true; if (drg) drg.hidden = true; paintMode(false); return;
      }
      if (!v) { note.textContent = '3D 起不來，已退回平面剖析圖。'; svg.hidden = false; host.hidden = true; rst.hidden = true; if (drg) drg.hidden = true; paintMode(false); return; }
      view3d = v;
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
      note.textContent = `${v.sub}　·　拖曳轉視角（可轉到底下看背面）、右鍵或切到「平移」可抓著移動、滾輪拉近拉遠、點零件看供應商`;
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
    rst.onclick = () => { if (view3d) view3d.reset(); };
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
     `tw.relView`   ：關聯圖用哪一種表達形式（layer 分層圖／flow 流向圖），預設 layer
     `tw.segExpand` ：手機上環節卡是「全部展開」還是「只展開重點幾格」
     每次重畫都重讀，不要在模組載入時讀一次就算了 —— 使用者可能在別的分頁改過。*/
  const REL_VIEWS = ['layer', 'flow'];
  const loadRelView = () => { try { const v = localStorage.getItem('tw.relView'); return REL_VIEWS.includes(v) ? v : 'layer'; } catch (e) { return 'layer'; } };
  const saveRelView = (v) => { try { localStorage.setItem('tw.relView', v); } catch (e) { /* 忽略 */ } };
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

  /* ==================================================================== 流向圖（第二種表達形式）
     Andy 2026-09-23：「不然你先展示你認為更好表達的形式」—— 有兩種值得做就兩種都做出來，
     做成畫面上可以切的，不拿來問他（CLAUDE.md 2026-09-23 的規矩）。

     分層圖回答的是「**誰**接誰」（節點是公司，看得到你手上那一檔在哪）；
     流向圖回答的是「**量**往哪裡走」（節點是環節，帶子寬度＝兩格之間已建立的關係條數）。
     同一份 edges，兩個不同的問題 —— 這就是為什麼兩張都留著，而不是二選一。

     ⚠ 帶子寬度是「關係條數」不是「金額」。供應鏈 YAML 沒有金流，硬換算成金額是造假；
        所以圖例與說明都寫「關係條數」，不寫「占比」。*/
  function drawSegFlow(host, sc, chainId, im, handlers) {
    if (!host) return;
    const segs = chainSegments(sc, chainId).slice().sort((a, b) => (a.layer || 0) - (b.layer || 0));
    if (!segs.length) { host.innerHTML = ''; return; }
    const layers = [...new Set(segs.map(s => s.layer || 0))].sort((a, b) => a - b);
    const segIds = new Set(segs.map(s => s.id));
    const cos = sc.companies.filter(c => segIds.has(c.segment));
    const coSeg = {}; cos.forEach(c => (coSeg[c.id] = c.segment));
    const twN = {}; cos.forEach(c => { if (c.tw_code) twN[c.segment] = (twN[c.segment] || 0) + 1; });
    const allN = {}; cos.forEach(c => (allN[c.segment] = (allN[c.segment] || 0) + 1));
    // 兩格之間的關係條數（只算兩端都在這條鏈上、而且不同格的邊；競爭關係不是上下游）
    const pair = {};
    (sc.edges || []).forEach(e => {
      if (e.rel === 'competes') return;
      const a = coSeg[e.from], b = coSeg[e.to];
      if (!a || !b || a === b) return;
      const k = a + '\u0000' + b; pair[k] = (pair[k] || 0) + 1;
    });
    const f = fitCols(host, layers.length, { colW: 150, gap: 62, maxColW: 210, maxGap: 190, minColW: 116, minGap: 34, pad: 18 });
    const boxW = f.colW, padY = 34, gapY = 14;
    const UNIT = 11, MIN_H = 36;                    // 每一檔台股 11px 高，最矮 36px（放得下一行環節名）
    const hOf = (s) => Math.max(MIN_H, (twN[s.id] || 0) * UNIT);
    const cols = layers.map(L => segs.filter(s => (s.layer || 0) === L));
    const colH = cols.map(col => col.reduce((t, s) => t + hOf(s) + gapY, -gapY));
    const bodyH = Math.max.apply(null, colH.concat([120]));
    const H = bodyH + padY * 2;
    const pos = {};
    cols.forEach((col, ci) => {
      let y = padY + (bodyH - colH[ci]) / 2;        // 每一欄自己垂直置中，短的那欄不會黏在上面
      col.forEach(s => { const h = hOf(s); pos[s.id] = { x: f.padX + ci * (boxW + f.colGap), y: y, w: boxW, h: h, out: 0, in: 0 }; y += h + gapY; });
    });
    const maxPair = Math.max.apply(null, Object.values(pair).concat([1]));
    // 先算每一格要吐出／收進多少寬度，才知道帶子從方塊的哪一段接出去
    const outT = {}, inT = {};
    const bandW = (n) => Math.max(3, Math.round((n / maxPair) * 26));
    Object.keys(pair).forEach(k => { const [a, b] = k.split('\u0000'); const w = bandW(pair[k]);
      outT[a] = (outT[a] || 0) + w; inT[b] = (inT[b] || 0) + w; });
    let bands = '';
    Object.keys(pair).sort((x, y) => pair[y] - pair[x]).forEach(k => {
      const [a, b] = k.split('\u0000'); const A1 = pos[a], B1 = pos[b]; if (!A1 || !B1) return;
      const w = bandW(pair[k]);
      const a0 = A1.y + (A1.h - Math.min(A1.h - 6, outT[a])) / 2 + A1.out; A1.out += w;
      const b0 = B1.y + (B1.h - Math.min(B1.h - 6, inT[b])) / 2 + B1.in; B1.in += w;
      const x1 = A1.x + (B1.x >= A1.x ? A1.w : 0), x2 = B1.x + (B1.x >= A1.x ? 0 : B1.w);
      const mx = (x1 + x2) / 2;
      const d = `M${x1},${a0} C${mx},${a0} ${mx},${b0} ${x2},${b0}`
        + ` L${x2},${b0 + w} C${mx},${b0 + w} ${mx},${a0 + w} ${x1},${a0 + w} Z`;
      bands += `<path class="fband" data-a="${a}" data-b="${b}" style="--c:${segColor(a)}" d="${d}">`
        + `<title>${A.fmt.esc(segName(sc, a))} → ${A.fmt.esc(segName(sc, b))}：${pair[k]} 條已建立的上下游關係</title></path>`;
    });
    let boxes = '';
    segs.forEach(s => {
      const p = pos[s.id]; if (!p) return; const c = segColor(s.id);
      const n = twN[s.id] || 0, nAll = allN[s.id] || 0;
      const cnt = n ? `${n} 檔` : (nAll ? `外商 ${nAll}` : '—');
      /* 環節名放在方塊裡；方塊只有 36px 高時仍然放得下一行 12px 的字＋一行 11px 的檔數。
         名稱過長就交給 SVG 的 textLength 縮排不動、改成切字（SVG 不會自己換行）。*/
      const nm = s.name.length > Math.floor(boxW / 13) ? s.name.slice(0, Math.floor(boxW / 13) - 1) + '…' : s.name;
      boxes += `<g class="fseg segtitle" data-seg="${s.id}" style="--c:${c}">`
        + `<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="7" fill="${c}" fill-opacity=".16" stroke="${c}" stroke-opacity=".55"/>`
        + `<rect x="${p.x}" y="${p.y}" width="3.5" height="${p.h}" rx="2" fill="${c}"/>`
        + `<text class="fnm" x="${p.x + 10}" y="${p.y + 17}" fill="${c}">${A.fmt.esc(nm)}</text>`
        + `<text class="fct" x="${p.x + 10}" y="${p.y + 31}">${A.fmt.esc(cnt)}</text></g>`;   // 說明改由 wireSegTip 的說明框顯示（原生提示寬度管不到）
    });
    /* ★ 2026-09-24（審查 R3：金融鏈流向圖 0 條帶子、也沒有任何說明）：沒有帶子就明講，不要讓人以為圖壞了 */
    const emptyF = Object.keys(pair).length ? '' : '<div class="mapempty">此鏈沒有可畫的上下游關係 —— 環節之間還沒有已建立的供貨關係，所以沒有帶子；方塊高度仍然是各環節的台股檔數。</div>';
    host.innerHTML = `${emptyF}<svg viewBox="0 0 ${f.W} ${H}" style="width:100%;height:auto;min-width:${Math.min(f.W, 640)}px;display:block">`
      + `<g class="fbands">${bands}</g>${boxes}</svg>`;
    markFit(host, f);
    /* hover 一格：把「這一格吐出去」與「進到這一格」的帶子一起提亮，其餘壓暗 ——
       這就是 Andy 要的「看得懂誰接誰」：一眼就分得出上游那一側與下游那一側。*/
    $$('.fseg', host).forEach(g => {
      g.onmouseenter = () => $$('.fband', host).forEach(b => {
        const on = b.dataset.a === g.dataset.seg || b.dataset.b === g.dataset.seg;
        b.classList.toggle('hi', on); b.classList.toggle('dim', !on);
      });
      g.onmouseleave = () => $$('.fband', host).forEach(b => b.classList.remove('hi', 'dim'));
      g.onclick = () => handlers && handlers.onSegment && handlers.onSegment(g.dataset.seg);
    });
  }

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
        const tip = `${c.name} ${c.tw_code}${m ? `｜收 ${A.fmt.n(m.close)}　${A.fmt.pct(chg)}` : ''}｜點一下看個股頁`;
        return `<a class="rlco" href="#stock/${c.tw_code}" data-code="${c.tw_code}" title="${A.fmt.esc(tip)}">`
          + `<span class="cd">${c.tw_code}</span><span class="nm">${A.fmt.esc(c.name)}</span>`
          + `<span class="chg ${chg == null ? 'flat' : A.fmt.cls(chg)}">${chg == null ? '—' : A.fmt.pct(chg)}</span></a>`;
      };
      const grp = (gn) => {
        const gid = gn ? A.L.gid[gn] : null;
        const label = gid ? A.L.group(gid, gn, { cls: 'rlgn' }) : `<span class="rlgn muted">${gn ? A.fmt.esc(gn) : '未歸族群'}</span>`;
        return `<div class="rlgrp"><div class="rlgh">${label}<span class="n">${byG[gn].length} 檔</span></div>${byG[gn].map(row).join('')}</div>`;
      };
      const body = order.map(grp).join('')
        + (fo.length ? `<div class="rlfo"><span class="fo">外商</span>${fo.map(c => A.fmt.esc(c.name)).join('、')}</div>` : '')
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
    const segs = chainSegments(sc, chainId).slice().sort((a, b) => (a.layer || 0) - (b.layer || 0));
    const segIds = new Set(segs.map(s => s.id));
    const cos = sc.companies.filter(c => segIds.has(c.segment));
    const inChain = new Set(cos.map(c => c.id));
    const coSeg = {}; cos.forEach(c => (coSeg[c.id] = c.segment));
    const priceOf = {}; (im ? im.chains.flatMap(c => c.groups).concat(im.industries || []) : [])
      .forEach(g => (g.members || []).forEach(m => { priceOf[m.code] = m; }));
    /* 度數與環節層級的上下游，都只算「兩端都在這條鏈上」的邊 —— 跟關聯圖同一個口徑，
       不然同一家公司在圖上沒有線、在清單上卻掛著一個數字，兩邊會對不起來。*/
    const deg = {}, upS = {}, dnS = {}; let nEdge = 0;
    (sc.edges || []).forEach(e => {
      if (e.rel === 'competes' || !inChain.has(e.from) || !inChain.has(e.to)) return;
      nEdge++;
      deg[e.from] = (deg[e.from] || 0) + 1; deg[e.to] = (deg[e.to] || 0) + 1;
      const a = coSeg[e.from], b = coSeg[e.to];
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
        + `｜${n ? n + ' 條上下游關係' : '還沒建立上下游關聯'}｜點開看它的產業關係`;
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
    const openIds = new Set(segs.slice()
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
      return `<div class="segcard${openIds.has(s.id) ? ' pin' : ''}" data-seg="${s.id}" data-n="${list.length}" style="--c:${segColor(s.id)}">
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
          ? `${segs.length} 格全部攤開，往下滑會比較長`
          : `已展開個股最多的 ${Math.min(MOBILE_OPEN, segs.length)} 格；其餘點卡片右邊的 ▾ 就地展開`; };
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
    const NOTE_W = colW - 10, NOTE_LH = 16, NOTE_MAX = 5;   // 文字從欄左 +6 開始，右邊留 4px；5 行（高度已算進 noteLines）
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
      nm = cut(n); while (n > 2 && cw + nmW(nm) > colW) { n--; nm = cut(n); }
      return { nm, code, w: Math.min(colW, Math.ceil(cw + nmW(nm))) };
    };
    const chipLay = (list) => {             // 依欄寬把晶片一排一排排下去，回傳各自相對位置與總高
      let x = 0, row = 0; const out = [];
      list.forEach(c => { const k = chipW(c); if (x && x + k.w > colW) { x = 0; row++; }
        out.push(Object.assign({ dx: x, dy: row * (CHIP_H + CHIP_GY) }, k)); x += k.w + CHIP_GX; });
      return { items: out, h: list.length ? (row + 1) * (CHIP_H + CHIP_GY) - CHIP_GY + 4 : 0 };
    };
    const segBodyH = (s, list) => (list.length && isFolded(s.id)
      ? 4 + chipLay(list).h + 18
      : list.length * (cardH + gapY) + noteLines(s, list) * NOTE_LH + 18);
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
    const inChain = new Set(cos.map(c => c.id)), deg = {};
    sc.edges.forEach(e => { if (e.rel === 'competes' || !inChain.has(e.from) || !inChain.has(e.to)) return;
      deg[e.from] = (deg[e.from] || 0) + 1; deg[e.to] = (deg[e.to] || 0) + 1; });
    let nodes = '';
    segs.forEach(s => { const p = pos[s.id]; if (!p) return; const col = segColor(s.id);
      nodes += `<g class="segtitle" data-seg="${s.id}" style="--c:${col}"><rect x="${p.x}" y="${p.y - 20}" width="${colW}" height="20" rx="5" fill="${col}" fill-opacity=".14"/><circle cx="${p.x + 10}" cy="${p.y - 10}" r="3.5" fill="${col}"/><text class="seg-title" x="${p.x + 19}" y="${p.y - 6}" fill="${col}">${A.fmt.esc(s.name)}</text></g>`;
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
          `<text class="sub" x="${p.x + 6}" y="${p.y + 15 + i * NOTE_LH}" fill="var(--ink-3)">${A.fmt.esc(w)}</text>`).join('') + '</g>';
      }
      if (foldOn && p.list.length) {
        const fd = isFolded(s.id);
        nodes += `<g class="segfold" data-seg="${s.id}" data-folded="${fd ? 1 : 0}"><rect x="${p.x + colW - 24}" y="${p.y - 20}" width="24" height="20" rx="5" fill="transparent"/><text x="${p.x + colW - 12}" y="${p.y - 6}" fill="${col}">${fd ? '▸' : '▾'}</text><title>${fd ? '展開這個環節（每檔一張卡）' : '收合這個環節（只留個股標籤）'}</title></g>`;
      }
      if (p.list.length && isFolded(s.id)) {
        /* 收合：走線的端點接到「整個環節的晶片區塊」左右緣，不是個別晶片 ——
           晶片擠成一排排，線接到中間那顆會從隔壁晶片上穿過去。*/
        const lay = chipLay(p.list), bh = lay.h;
        p.list.forEach((c, i) => { const it = lay.items[i]; const x = p.x + it.dx, y = p.y + 4 + it.dy;
          coPos[c.id] = { x: p.x, y: p.y + 2, w: colW, h: Math.max(bh, CHIP_H) };
          const m = c.tw_code ? priceOf[c.tw_code] : null; const chg = m ? m.chg_pct : null;
          const tip = `${c.name}${c.tw_code ? ' ' + c.tw_code : '（外商）'}${m ? ` · ${A.fmt.n(m.close)} ${A.fmt.pct(chg)}` : ''}${deg[c.id] ? '' : ' · 還沒有上下游關聯'}`;
          nodes += `<g class="co chip ${c.foreign || !c.tw_code ? 'foreign' : ''} ${state.code && c.tw_code === state.code ? 'sel' : ''}" data-id="${c.id}" data-segment="${c.segment}" data-code="${c.tw_code || ''}" style="--c:${col};--ud:${chg == null ? 'var(--line-2)' : A.upDown(chg)}"><rect x="${x}" y="${y}" width="${it.w}" height="${CHIP_H}" rx="11"/><text x="${x + 8}" y="${y + 15}">${A.fmt.esc(it.nm)} <tspan class="sub">${it.code}</tspan></text><title>${A.fmt.esc(tip)}</title></g>`; });
        return;
      }
      p.list.forEach((c, i) => { const y = p.y + 4 + i * (cardH + gapY); coPos[c.id] = { x: p.x, y, w: colW, h: cardH }; const m = c.tw_code ? priceOf[c.tw_code] : null; const chg = m ? m.chg_pct : null;
        nodes += `<g class="co ${c.foreign || !c.tw_code ? 'foreign' : ''} ${state.code && c.tw_code === state.code ? 'sel' : ''}" data-id="${c.id}" data-segment="${c.segment}" data-code="${c.tw_code || ''}" style="--c:${col}"><rect x="${p.x}" y="${y}" width="${colW}" height="${cardH}" rx="7"/><rect x="${p.x}" y="${y}" width="4" height="${cardH}" rx="2" fill="${col}"/><text x="${p.x + 12}" y="${y + 15}">${A.fmt.esc(c.name.length > 13 ? c.name.slice(0, 12) + '…' : c.name)}${c.tw_code ? ` <tspan class="sub">${c.tw_code}</tspan>` : ' <tspan class="sub">外商</tspan>'}</text><text class="sub" x="${p.x + 12}" y="${y + 29}">${m ? `${A.fmt.n(m.close)} <tspan fill="${A.upDown(chg)}">${A.fmt.pct(chg)}</tspan>` : A.fmt.esc((c.tech || []).slice(0, 2).join(' · '))}</text>${deg[c.id] ? '' : `<g class="iso"><circle cx="${p.x + colW - 12}" cy="${y + 12}" r="6.5"/><text x="${p.x + colW - 12}" y="${y + 15.5}">?</text><title>這家還沒有上下游關聯（supply_chain.yaml 的 edges 待補）</title></g>`}</g>`; }); });
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
        const x1 = a.x + a.w, xo = x1 + 24;
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
    const empty = nEdge0 ? '' : '<div class="mapempty">此鏈沒有可畫的上下游關係 —— supply_chain.yaml 還沒有這條鏈公司之間的具名供貨關係，下面只列出各環節有哪些公司（每張卡右上的「?」就是這個意思）。</div>';
    const foldBar = foldOn && cos.length ? `<div class="foldbar"><button type="button" data-fold="all">全部收合</button><button type="button" data-fold="none">全部展開</button><span class="sub">收合＝每個環節只留個股標籤；點環節標題右邊的 ▸／▾ 單獨切換</span></div>` : '';
    host.innerHTML = `${empty}${foldBar}<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;min-width:${Math.min(W, 860)}px;display:block">${defs}${nodes}<g class="elayer">${edges}</g></svg>`;
    markFit(host, fit);
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
    $$('.foldbar button', host).forEach(b => b.onclick = () => { chainFoldSet(chainId, { def: b.dataset.fold === 'all', seg: {} }); redraw(); });
    $$('.segtitle', host).forEach(n => n.onclick = () => handlers.onSegment && handlers.onSegment(n.dataset.seg));
    /* 把目前這檔的卡片捲進視野 —— 但**只捲關聯圖自己那個框**，不准動到整頁。
       原本用 scrollIntoView，它會一路往上找每一個可捲的祖先，連 document 也算。
       在個股頁把產業鏈搬到最下面之後（Andy 2026-09-20），那一下等於把整頁拉到底，
       使用者一進個股頁就看不到 K 線 —— 剛好把這次要修的東西反過來弄壞。*/
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
    if (g.capacity_source) parts.push('（來源：' + g.capacity_source + '）');
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
      ${shares ? `<ul style="margin:6px 0;padding-left:18px;font-size:13.5px">${shares}</ul>` : '<div class="note">尚無市占資料（supply_chain.yaml 待補）</div>'}
      ${co.note ? `<div class="note">${A.fmt.esc(co.note)}</div>` : ''}
      ${growthText(co.growth) ? `<div class="note">成長：${A.fmt.esc(growthText(co.growth))}</div>` : ''}${(co.risks || []).length ? `<div class="note">風險：${co.risks.map(A.fmt.esc).join('；')}</div>` : ''}
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
        cf = `<a class="cf cf-${e.confidence} cf-lk" href="${A.fmt.esc(url)}" target="_blank" rel="noopener noreferrer" title="開新分頁看原文${e.source ? '：' + A.fmt.esc(e.source) : ''}">${ctext} ↗</a>`;
      } else if (e.confidence) {
        cf = `<em class="cf cf-${e.confidence}">${ctext}</em>`;
      }
      const guess = e.confidence === 'estimated';
      const why = guess
        ? `<div class="why"><b>這是推論，不是公司揭露</b>
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
      return `<div class="relbox"><div class="note">這家目前還沒有建立上下游關聯（圖上會標一個橘色「?」）。
        公開來源查不到具名的客戶或供應商時，我們寧可留白，也不畫一條猜的線。</div></div>`;
    }
    return `<div class="relbox">
      <div class="row spread"><b class="rh">產業關係</b>
        <button class="btn sm" id="relHi" data-on="0">在圖上highlight</button></div>
      ${up.length ? `<div class="relcol"><h5>上游 · 誰供給它（${up.length}）</h5><ul>${up.join('')}</ul></div>` : ''}
      ${down.length ? `<div class="relcol"><h5>下游 · 它供給誰（${down.length}）</h5><ul>${down.join('')}</ul></div>` : ''}
      ${rivals.length ? `<div class="relcol"><h5>同業競爭</h5><div class="row" style="gap:6px">${rivals.map(r => r.tw_code ? A.L.stock(r.tw_code, r.name, { cls: 'sm' }) : `<span class="muted">${A.fmt.esc(r.name)}</span>`).join('')}</div>
        <div class="nt">競爭關係不畫在關聯圖上 —— 那不是上下游，畫成線會被讀成供貨。</div></div>` : ''}
      <div class="nt">依存度＝資料裡的 strength（1–5），越滿代表這條關係在圖上的線越粗。<br>
        <b class="cf cf-estimated" title="${A.fmt.esc(EST_TIP)}">產業推論</b>＝我們從兩段公開資訊推出來的，不是誰講過的 ——
        所以會寫「為什麼這樣推」與支撐推論的那篇，看的時候要打折。</div>
    </div>`;
  }

  /* 「在圖上 highlight」：把這家公司的線亮起來、其餘變暗。
     按第二次還原 —— 不還原的話使用者會以為圖壞掉了。*/
  function wireRelBlock(box, sc, host) {
    const btn = box && box.querySelector('#relHi');
    if (!btn) return;
    /* 2026-09-23 C5 退版之後產業鏈頁與個股頁又是同一張圖（`#chainMap`，節點是公司），
       所以這裡只認它一個。流向圖模式下節點是環節不是公司，按鈕按下去不會有東西被提亮 ——
       那是刻意的：那張圖本來就沒有「這一家公司」這個概念，硬亮一格會騙人。*/
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
    renderChainStrip(im, sc, { code, name: known.name, group_id: gid, groups: known.group ? [known.group] : [] });

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
    const why = known.tier === 'thin'
      ? '這一檔的歷史價量還在回補（完整頁需要至少 60 根日線才算得出指標、SMC 與評分）。'
      : '這一版的資料包沒有帶到這一檔的完整個股頁。';
    /* ★ 2026-09-25（Andy：「文字只需要留名稱」）：簡易頁的卡片副標（價量與三大法人、同族群才比本益比…）不再印；
       只留「N 則」這種讀數（副標以數字開頭才印）。*/
    const card = (title, sub, body) => body
      ? `<div class="card" style="margin-top:var(--gap-card)"><h3>${title}${sub && /^\d/.test(sub) ? ` <small data-readout>${sub}</small>` : ''}</h3>${body}</div>` : '';

    $('#stockPage').innerHTML = `
      <div class="card" style="margin-top:var(--gap-card)">
        <div class="row spread">
          <div><h2>${A.fmt.esc(known.name || '')} <span class="mono cyan">${code}</span>
            <small class="muted" style="font-size:13px">${known.market === 'TPEX' ? '上櫃' : known.market === 'TWSE' ? '上市' : (known.market || '')}</small></h2>
            <div class="row" style="gap:6px 12px;margin-top:4px;font-size:13.5px">
              <span class="muted">產業鏈</span>${A.L.chain(state.chain, chainName)}
              <span class="muted">族群</span>${gid ? A.L.group(gid, (mem && mem.group_name) || known.group) : '—'}
              ${themeLinks ? `<span class="muted">題材</span>${themeLinks}` : ''}</div>
            <div class="row" style="margin-top:6px">
              <span class="num" style="font-size:30px;font-weight:700">${close != null ? n(close) : '—'}</span>
              ${chg != null ? `<span class="num ${A.fmt.cls(chg)}" style="font-size:18px">${pct(chg, 2)}</span>` : ''}
              <span class="pill amber">簡版個股頁</span></div></div>
        </div>
        <div class="banner on" style="margin:12px 0 0">
          <b>這一頁是簡版。</b>${why}
          下面是這一檔<b>現在就查得到的完整資訊</b>：今日價量與法人、估值與營收、相關新聞、同族群比較。
          完整版（K 線、多週期 SMC、五年營收獲利、除權息、籌碼）會在<b>下一次盤後更新</b>出現。
        </div>
      </div>
      ${card('今日盤後', '價量與三大法人', today)}
      ${card('估值與營收', '同族群才比本益比', val)}
      ${card('相關新聞', `${ns.length} 則`, ns.length ? `<div class="cards">${ns.map(x => `<div class="scard">
          <a href="${A.fmt.esc(x.url || '#')}" target="_blank" rel="noopener">${A.fmt.esc(x.title || '')}</a>
          <div class="r"><span class="muted">${A.fmt.esc(x.date || '')}</span><span class="muted">${A.fmt.esc(x.source || '')}</span></div></div>`).join('')}</div>` : '')}
      ${card('同族群其他個股', '點進去看完整頁', sibs.length ? `<div class="sibs">${sibs.map(x =>
          `${A.L.stock(x.code, x.name)}<span class="chg ${A.fmt.cls(x.chg_pct)}">${pct(x.chg_pct, 1)}</span>`).join('')}</div>` : '')}
      <div class="card" style="margin-top:var(--gap-card)"><div class="note">資料更新到 <b>${A.fmt.esc((A.D.meta && A.D.meta.data_date) || '—')}</b>（每個交易日盤後自動更新）。${A.L.back()}</div></div>`;
  }

  // ================================================================ Level 2：個股頁
  async function renderStock(code, im, sc, gd) {
    show(false, true, true);
    const pg = await A.load('stock/' + code, { fallback: null });
    if (!pg) { await renderStockLite(code, im, sc, gd); return; }
    const m = pg.meta, s = pg.summary || {};
    // 上方產業鏈（同步高亮）
    state.chain = chainOfGroup(im, m.group_id) || 'industry'; state.group = null;
    const chainName = A.L.chains[state.chain] || CHAIN_NAME[state.chain] || state.chain;   // 中文名以 payload 為準，寫死的表只當 fallback
    crumbs([{ label: '產業地圖', href: '#industry' }, { label: chainName, href: '#industry/' + state.chain }, { label: `${m.name} ${m.code}` }]);
    renderChainStrip(im, sc, m);
    // 個股主體
    const el = $('#stockPage');
    const v = pg.verdict || {}; const gradeCls = v.grade || 'W';
    const groupLinks = (m.groups || []).map(gn => A.L.groupByName(gn)).join(' ');
    const themeLinks = A.L.themesOf(m.code);
    const TIER = { full: ['分 K 完整', 'cyan', '15 分／1 小時／4 小時分 K 每日盤後由 Yahoo 補入'],
                   daily: ['日線以上', '', '這檔不在分 K 名單（族群成分股＋成交值前段才抓），日線／週線／月線與多週期判讀都正常'],
                   thin: ['資料回補中', 'amber', '歷史價量還在回補，目前只有最近幾天的日線'] };
    const tier = TIER[(m.tier || 'daily')] || TIER.daily;
    el.innerHTML = `
      <div class="card" id="skChartCard" style="margin-top:var(--gap-card)">
        <div class="row spread" id="skHead">
          <div id="skIdent"><h2>${A.fmt.esc(m.name)} <span class="mono cyan">${m.code}</span> <small class="muted" style="font-size:13px">${m.market || ''}</small></h2>
            <div class="row" id="skMeta" style="gap:6px 12px;margin-top:4px;font-size:13.5px"><span class="muted">產業鏈</span>${A.L.chain(state.chain, chainName)}<span class="muted">族群</span>${groupLinks || '—'}${themeLinks ? `<span class="muted">題材</span>${themeLinks}` : ''}</div>
            <div class="row" id="skPx" style="margin-top:6px"><span class="num" style="font-size:30px;font-weight:700" id="pxNow" data-live="close" data-lc="${m.code}">${A.fmt.n(s.close)}</span><span class="num ${A.fmt.cls(s.chg_pct)}" style="font-size:18px" data-live="chg" data-lc="${m.code}">${A.fmt.pct(s.chg_pct, 2)}</span><span class="pill">技術分 ${A.fmt.n(s.tech_score, 0)}</span><span class="pill">本益比 ${s.pe ? A.fmt.n(s.pe, 1) : '—'}</span><span class="pill">同業分位 ${s.pe_percentile != null ? A.fmt.n(s.pe_percentile, 0) + '%' : '—'}</span><span class="pill">營收 YoY ${A.fmt.pct(s.rev_yoy)}</span><span class="pill ${tier[1]}" title="${A.fmt.esc(tier[2])}">${tier[0]}</span></div></div>
          <div class="verdict" id="skVerdict" data-readout style="min-width:280px;max-width:520px"><h3><span class="grade ${gradeCls}">${v.grade ? v.grade + ' ' : ''}${v.verdict || '—'}</span> <small>停損 ${A.fmt.n(v.stop)} · 目標 ${A.fmt.n(v.tp1)} · 風報 ${v.rr != null ? A.fmt.n(v.rr, 1) : '—'}</small></h3><ul>${(v.reasons || []).slice(0, 3).map(r => `<li>${A.fmt.esc(r)}</li>`).join('')}</ul>${v.risk_text ? `<div class="note" style="margin-top:6px">風險：${A.fmt.esc(v.risk_text)}</div>` : ''}</div>
        </div>
        <div class="toolbar" id="skTools" style="margin-top:14px">
          <div class="seg" id="tfSeg">${tfButtons()}</div>
          <button class="btn small" id="tfAdd" title="自訂時間週期">＋</button>
          <div id="indChips" class="row" style="gap:6px"></div>
          <div class="sp"></div>
          <button class="btn small" id="cfgBtn" title="圖表設定：線寬、均線、顏色">⚙ 設定</button>
          <button class="btn small" id="mtfBtn">${state.mtfMode ? '單一週期' : '四週期同看'}</button>
          <button class="btn small" id="wideBtn" title="收起右側事件欄，把整個視窗的寬度讓給 K 線圖">⤢ 寬版</button>
          <button class="btn small" id="drawTgl" title="畫線工具（手機預設收起來）">✎ 畫線</button>
          <button class="howbtn pop" data-how="kline" data-ttl="K 線" type="button" aria-label="K 線怎麼看">?</button>
          <button class="iconbtn" id="fitBtn" title="重設縮放（雙擊價格軸也可以）" aria-label="重設縮放">
            <svg viewBox="0 0 18 18"><rect x="2.5" y="2.5" width="13" height="13" rx="2"/><path d="M6,9 H12 M9,6 V12"/></svg></button>
        </div>
        <!-- ★ 2026-09-24 說明精簡：圖下那段滑鼠／拖曳操作說明（.skhelp 第一行）整段搬進「怎麼看 ?」 -->
        <div class="howtxt" id="how-kline" hidden>${A.howHTML('這張圖：這一檔的 K 線、成交量與技術指標。', [
          '圖內滾輪＝時間縮放',
          '價格軸上滾輪或拖曳＝調整上下寬度',
          '雙擊價格軸或按「重設縮放」還原',
          '副圖之間的分隔線可上下拖，會記住',
          '週期鈕被劃掉＝這檔沒有那個週期資料',
        ], '滑鼠移到劃掉的週期鈕上會說原因。分 K 來源 Yahoo Finance（1 小時可回溯 2 年、15 分 60 天），盤後更新；K 棒會跟著上下寬度一起變。')}</div>
        <div class="note livenote" id="liveNote" hidden></div>
        <div class="chartwrap" id="chartWrap">${adjTag(pg)}
          <div class="drawbar" id="drawBar"></div>
          <div id="chartHost"></div>
        </div>
        <div class="cfgpop" id="cfgPop" hidden></div>
        ${pg.note ? `<div class="banner on" style="margin:10px 0 0">${A.fmt.esc(pg.note)}</div>` : ''}
        <div class="note skhelp" style="margin-top:6px" title="每個交易日盤後自動更新一次：價量、法人、籌碼、營收／財報、新聞">資料更新到 <b>${A.fmt.esc(pg.as_of || (A.D.meta && A.D.meta.data_date) || '—')}</b>（每日盤後）</div>
      </div>
      <div class="card" style="margin-top:var(--gap-card)" id="mtfCard"></div>
      <div class="subtabs" id="stockTabs">${[['overview', '總覽'], ['revenue', '營收'], ['profit', '獲利'], ['dividend', '除權息'], ['chips', '籌碼'], ['basics', '基本資料'], ['news', '公告 / 新聞']].map(t => `<button data-t="${t[0]}" class="${state.tab === t[0] ? 'on' : ''}">${t[1]}</button>`).join('')}</div>
      <div id="stockTab"></div>`;
    setupChart(pg);
    renderMtf(pg);
    $$('#stockTabs button').forEach(b => b.onclick = () => { $$('#stockTabs button').forEach(x => x.classList.toggle('on', x === b)); state.tab = b.dataset.t; renderTab(pg, state.tab); });
    renderTab(pg, state.tab);
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
    let lastTxt = '這一檔目前沒有除權息事件，還原價與原始價相同';
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

  // 個股頁上方：產業鏈 › 族群 › 同族群公司（可直接切換）＋ 可收合的剖析圖與關聯圖
  function renderChainStrip(im, sc, m) {
    const el = $('#indChain'); const cid = state.chain;
    const ch = chainData(im, cid);
    if (!ch) { el.innerHTML = ''; return; }
    /* 個股頁的剖析圖：先看**這一檔所屬的族群**有沒有專屬圖，沒有才退回鏈層級的總圖。
       strict＝true，不准退回「這條鏈成交值最大的那張族群圖」——
       一檔面板股掉到 MLCC 那張圖上，等於在網站上說「它做 MLCC」。*/
    /* ★ 2026-09-22（DECISIONS #234）：半導體鏈的鏈層級剖面退場之後，`dgPick` 對
       「所屬族群沒有專屬圖」的半導體個股（例如 2330）會回 null ——
       那一頁的產業鏈圖就整塊不見了。退回這條鏈的**代表圖**，行為跟退場前一致
       （退場前退回的就是鏈層級那張總圖）。
       ⚠ 只在個股頁這樣退，**產業鏈頁不准**：那邊「選到沒有專屬圖的族群 → 收起圖、
         換回圖別選單」是刻意的（見 resolveDg 上面那段），所以 `DS.pick` 本身沒有動。*/
    const dgId = dgPick(ch, m.group_id) || (DS ? DS.rep(cid) : null);
    const hasDiagram = !!dgId;
    const g = ch.groups.find(x => x.id === m.group_id) || (im.industries || []).find(x => x.id === m.group_id);
    const sibs = g ? (g.members || []).slice().sort((a, b) => (b.turnover || 0) - (a.turnover || 0)) : [];
    const co = sc ? sc.companies.find(c => c.tw_code === m.code) : null;
    const segs = chainSegments(sc, cid);
    let open = false; try { open = localStorage.getItem('tw.chainOpen') === '1'; } catch (e) { /* 忽略 */ }
    /* 這一塊現在排在個股頁的最下面（Andy 2026-09-20 要 K 線先出現），
       所以要自己講清楚「這是什麼、看它幹嘛」—— 原本它緊貼在麵包屑下面，
       靠位置就看得懂；搬到底下之後沒有標題就只是一排看不懂的連結。*/
    el.innerHTML = `<div class="card tight">
      <h4 style="margin:0 0 8px">產業鏈位置 ${hq('skchain', '產業鏈位置')}</h4>${hbox('skchain', ['上排：產業鏈 › 族群 › 這一檔的環節', '同族群依成交值排，看誰在動', '點名字直接換一檔', '「展開產業鏈圖」看剖析圖與供應商'])}
      <div class="row spread"><div class="row" style="gap:8px"><b>${A.L.chain(cid, ch.name)}</b><span class="muted">›</span>${g ? A.L.group(g.id, g.name) : A.fmt.esc(m.group || '')}${co ? `<span class="muted">›</span><span class="pill" style="border-color:${segColor(co.segment)};color:${segColor(co.segment)}">● ${A.fmt.esc(segName(sc, co.segment))}</span>` : ''}</div>
        <div class="row" style="gap:8px">${hasDiagram ? `<button class="btn small" id="chainToggle">${open ? '收合產業鏈圖 ▴' : '展開產業鏈圖 ▾'}</button>` : ''}${A.L.back()}</div></div>
      ${sibs.length ? `<div class="sibs" id="sibs"><span class="muted" style="flex:none;font-size:12px;align-self:center">同族群</span>${sibs.map(x => `<a class="lk ${x.code === m.code ? 'cur' : ''}" href="#stock/${x.code}">${A.fmt.esc(x.name)}<span class="code">${x.code}</span><span class="chg ${A.fmt.cls(x.chg_pct)}">${A.fmt.pct(x.chg_pct)}</span></a>`).join('')}</div>` : ''}
      ${!hasDiagram ? `<div class="row" style="margin-top:8px;gap:6px">${ch.groups.map(x => `<span class="pill ${x.id === m.group_id ? 'cyan' : ''}" style="cursor:pointer" onclick="location.hash='#industry/group/${x.id}'"><i class="gdot" style="--c:${A.L.gcolor[x.id] || '#8ea0c4'}"></i>${A.fmt.esc(x.name)} <span class="${A.fmt.cls(x.chg_pct)}">${A.fmt.pct(x.chg_pct)}</span></span>`).join('')}</div>` : ''}
      ${hasDiagram ? `<div id="chainBody" style="${open ? '' : 'display:none'};margin-top:10px">
        <div class="segchips">${segs.map(s => `<span class="segchip ${co && co.segment === s.id ? 'sel' : ''}" data-seg="${s.id}" style="--c:${segColor(s.id)}" title="看這個環節的供應商"><i></i>${A.fmt.esc(s.name)}</span>`).join('')}</div>
        <div class="sub" style="margin:8px 0 2px">${A.fmt.esc(DS.name(dgId))}　<span class="muted">原創示意圖，非實物比例；點零件看這個環節的供應商</span></div>
        <div id="prodDiagram" class="dgwrap" style="margin-top:6px;max-width:1080px">${DS.draw(dgId)}</div><div class="chainmap" id="chainMap" style="margin-top:10px;max-height:380px"></div></div>` : ''}
    </div>`;
    /* 同族群那一列橫向捲到目前這檔 —— 一樣只捲那一列，不用 scrollIntoView。
       產業鏈區塊搬到個股頁最下面之後，scrollIntoView 會把整頁拖到底（見 drawChainMap 的註解）。*/
    const cur = $('#sibs a.cur', el), sibBox = $('#sibs', el);
    if (cur && sibBox) setTimeout(() => {
      // 用兩個 rect 相減，不用 offsetLeft —— offsetLeft 看的是 offsetParent，
      // .sibs 沒有 position 時那會是外面的卡片，算出來整個偏掉。
      const d = cur.getBoundingClientRect().left - sibBox.getBoundingClientRect().left;
      sibBox.scrollLeft = Math.max(0, sibBox.scrollLeft + d - sibBox.clientWidth / 2 + cur.offsetWidth / 2);
    }, 30);
    if (hasDiagram && sc) {
      const tog = $('#chainToggle', el); tog.onclick = () => { const b = $('#chainBody', el); const isOpen = b.style.display !== 'none'; b.style.display = isOpen ? 'none' : ''; tog.textContent = isOpen ? '展開產業鏈圖 ▾' : '收合產業鏈圖 ▴'; try { localStorage.setItem('tw.chainOpen', isOpen ? '0' : '1'); } catch (e) { /* 忽略 */ } };
      applyDgNative($('#prodDiagram', el), dgId);
      paintDiagram($('#prodDiagram', el));
      // 剖析圖不加縮放：Andy 明講「產業與個股 剖析圖不用新增縮放功能」（本來就可以左右滑）
      if (window.DG && window.DG.fillChips) window.DG.fillChips($('#prodDiagram', el), (seg) => { const tw = twOf(sc, seg);
        return { list: tw.slice(0, 4).map(c => ({ code: c.tw_code, name: c.name })), total: tw.length }; });
      drawChainMap($('#chainMap', el), sc, cid, im, { onSegment: (seg) => { location.hash = `#industry/${cid}/${seg}`; } });
      highlightSegments(el, co ? [co.segment] : [], co ? segColor(co.segment) : null);
      wireDiagram(el, (seg) => { location.hash = `#industry/${cid}/${seg}`; });
      $$('.segchip', el).forEach(c => c.onclick = () => { location.hash = `#industry/${cid}/${c.dataset.seg}`; });
      /* 個股頁沒有動畫鈕，但要吃同一個偏好。B4：CSS 的 .noanim 管不到 SMIL（<animateMotion>），
         所以「動畫：關」之後跑到個股頁，流程列那顆白點會自己活過來。兩件事都要做。*/
      try {
        if (localStorage.getItem('tw.dganim') === '0') {
          const wrap = $('#prodDiagram', el);
          wrap.classList.add('noanim');
          wrap.querySelectorAll('svg').forEach(s => { try { s.pauseAnimations(); } catch (e2) { /* 忽略 */ } });
        }
      } catch (e) { /* 忽略 */ }
    }
  }

  // ---------------------------------------------------------------- K 線面板
  const DEFAULT_CFG = { ma: [5, 20, 60, 120], maColor: [], maWidth: [], lineWidth: 1,
    boll: null, vol: true, volma: 20, kd: { n: 9, m1: 3, m2: 3 }, macd: { f: 12, s: 26, g: 9 },
    rsi: null, smc: true, marks: true, lines: true, tfs: null,
    // 每個指標的顏色／線寬／透明度；zone 是 SMC 供需區的填色濃度與框線
    st: {}, zone: null,
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
  const TF_BUILTIN = ['5s', '1m', '5m', '15m', '60m', '240m', '1d', '1w', '1M'];
  const TF_NAME = { '5s': '5秒', '1m': '1分', '5m': '5分', '15m': '15分', '60m': '1時', '240m': '4時', '1d': '日', '1w': '週', '1M': '月' };
  // 15 分也改成即時（Andy 2026-09-18：「1 5 15 分 K 都限制當天即可」）。
  // 後端不再預先產出 15 分 K —— 那是部署最慢的一塊（DECISIONS #156）。
  const LIVE_TF = ['5s', '1m', '5m', '15m'];
  const isLiveTf = (tf) => LIVE_TF.indexOf(tf) >= 0;
  /* 即時週期沒東西可畫時，要講清楚是「還在收」還是「根本沒設來源」。
     2026-09-18 起 15 分也走即時（後端不再預先產出，見 DECISIONS #156）——
     這代表沒設 Worker 的人會多一個週期看不到，所以更不能只寫「還在收集」讓人乾等。*/
  function liveEmptyMsg() {
    const has = !!(window.Live && window.Live.proxy && window.Live.proxy());
    return has ? '即時資料還在收集（開盤後每 5 秒補一根）'
               // ★ 2026-09-24：右上角的 ⚙ 即時來源設定已經拿掉，不能再叫人去按它
               : '這個週期要即時資料，目前沒有即時報價來源，所以看不到';
  }
  const tfLabel = (tf) => TF_NAME[tf] || (/^\d+D$/.test(tf) ? tf.replace('D', ' 日') : /^\d+W$/.test(tf) ? tf.replace('W', ' 週') : tf);
  function tfList() { const c = (state.cfg && state.cfg.tfs) || []; return TF_BUILTIN.concat(c); }
  function tfButtons() { return tfList().map(tf => `<button data-tf="${tf}" class="${tf === state.tf ? 'on' : ''}">${tfLabel(tf)}</button>`).join(''); }
  /* 哪些週期這檔真的有資料：沒有的直接在按鈕上劃掉並寫清楚原因。
     Andy 回報「K 線圖 1 日以下都不見」—— 其實按鈕在，是那檔沒有分 K，
     但按下去才看到一行字，等於要用猜的。現在光看按鈕就知道哪些看得到。 */
  function markTf(pg) {
    $$('#tfSeg button').forEach(b => {
      const tf = b.dataset.tf;
      if (isLiveTf(tf)) {
        // 即時週期永遠可以按：盤中會邊看邊長，盤後顯示今天收集到的
        b.classList.remove('off');
        b.classList.add('livetf');
        b.title = '當天即時（Yahoo 補早盤 ＋ 證交所報價每 5 秒補尾巴）';
        return;
      }
      const has = (barsFor(pg, tf) || []).length >= 5;
      b.classList.toggle('off', !has);
      b.title = has ? '' : (/m$/.test(tf)
        ? `${pg.meta.name} 沒有分 K：分 K 每天只跟 Yahoo 抓族群成分股與成交值前 400 名，這檔不在名單內。日線／週線／月線正常。`
        : '這個週期的資料還在回補');
    });
  }
  function loadCfg() { try { const s = localStorage.getItem('tw.kcfg'); if (s) return Object.assign({}, DEFAULT_CFG, JSON.parse(s)); } catch (e) { /* 忽略 */ } return Object.assign({}, DEFAULT_CFG); }
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
    if (tf === '240m') return groupBars((pg.intraday && pg.intraday['60m']) || [], 4);
    return (pg.intraday && pg.intraday[tf]) || [];
  }
  function zonesFor(pg, tf) { const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf]; if (t) return [...t.demand, ...t.supply].map(z => ({ ...z, tf: t.label })); if (tf === '1d' && pg.verdict) return [...(pg.verdict.demand || []).map(z => ({ ...z, kind: 'demand' })), ...(pg.verdict.supply || []).map(z => ({ ...z, kind: 'supply' }))]; return []; }
  function marksFor(pg, tf) { const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf]; if (t) return t.marks; if (tf === '1d') return pg.marks || {}; return {}; }

  function setupChart(pg) {
    state.cfg = state.cfg || loadCfg();
    /* 即時分 K：切到這一檔就開始收，每收到一筆就重畫（畫面位置由 setBars(..., keepView) 保住）。
       Andy 2026-09-15：「當我點擊一般股票時也能做到這樣的效果」 */
    stopLive();
    if (window.LiveK) {
      window.LiveK.attach(pg.meta.code, pg.meta.market);
      liveOff = window.LiveK.onUpdate(() => {
        if (!document.getElementById('lwc')) return;      // 四週期同看或已離開，不用畫
        // 即時週期固然要重畫；日／週／月因為最後一根是「今天還沒收的」，也要跟著跳
        if (isLiveTf(state.tf) || ['1d', '1w', '1M'].indexOf(state.tf) >= 0) apply();
      });
    }
    const host = $('#chartHost');
    const chips = $('#indChips');
    const cfg = state.cfg;
    const chipDefs = [
      { k: 'ma', label: 'MA', on: () => !!cfg.ma, params: () => cfg.ma ? [{ key: 'ma', val: cfg.ma.join(','), w: 90 }] : [], toggle: () => { cfg.ma = cfg.ma ? null : [5, 20, 60, 120]; }, set: (v) => { cfg.ma = v.split(/[,，\s]+/).map(Number).filter(n => n > 0).slice(0, 6); }, color: '#ffd166' },
      { k: 'boll', label: 'BOLL', on: () => !!cfg.boll, params: () => cfg.boll ? [{ key: 'n', val: cfg.boll.n, w: 34 }, { key: 'k', val: cfg.boll.k, w: 30 }] : [], toggle: () => { cfg.boll = cfg.boll ? null : { n: 20, k: 2 }; }, set: (v, key) => { cfg.boll[key] = +v; }, color: '#8b7bff' },
      { k: 'vol', label: '成交量', on: () => !!cfg.vol, params: () => [], toggle: () => { cfg.vol = !cfg.vol; }, color: '#8ea0c4' },
      { k: 'kd', label: 'KD', on: () => !!cfg.kd, params: () => cfg.kd ? [{ key: 'n', val: cfg.kd.n, w: 30 }, { key: 'm1', val: cfg.kd.m1, w: 26 }, { key: 'm2', val: cfg.kd.m2, w: 26 }] : [], toggle: () => { cfg.kd = cfg.kd ? null : { n: 9, m1: 3, m2: 3 }; }, set: (v, key) => { cfg.kd[key] = +v; }, color: '#ffd166' },
      { k: 'macd', label: 'MACD', on: () => !!cfg.macd, params: () => cfg.macd ? [{ key: 'f', val: cfg.macd.f, w: 30 }, { key: 's', val: cfg.macd.s, w: 30 }, { key: 'g', val: cfg.macd.g, w: 26 }] : [], toggle: () => { cfg.macd = cfg.macd ? null : { f: 12, s: 26, g: 9 }; }, set: (v, key) => { cfg.macd[key] = +v; }, color: '#3ee0ff' },
      { k: 'rsi', label: 'RSI', on: () => !!cfg.rsi, params: () => cfg.rsi ? [{ key: 'n', val: cfg.rsi.n, w: 30 }] : [], toggle: () => { cfg.rsi = cfg.rsi ? null : { n: 14 }; }, set: (v) => { cfg.rsi.n = +v; }, color: '#c3ff5b' },
      { k: 'smc', label: 'SMC 區間', on: () => !!cfg.smc, params: () => [], toggle: () => { cfg.smc = !cfg.smc; }, color: '#2ee59d' },
      { k: 'marks', label: 'BOS/CHoCH', on: () => !!cfg.marks, params: () => [], toggle: () => { cfg.marks = !cfg.marks; }, color: '#ff8fab' },
      // 背離要有 MACD 才算得出來（DIF 是比較基準）
      { k: 'macdDiv', label: 'MACD 背離', on: () => cfg.macdDiv !== false && !!cfg.macd, params: () => [], toggle: () => { const nowOn = cfg.macdDiv !== false && !!cfg.macd; if (nowOn) { cfg.macdDiv = false; } else { cfg.macdDiv = true; if (!cfg.macd) cfg.macd = { f: 12, s: 26, g: 9 }; } }, color: '#ffd166' },
      { k: 'lines', label: '停損/目標', on: () => !!cfg.lines, params: () => [], toggle: () => { cfg.lines = !cfg.lines; }, color: '#ffb454' },
      /* 本益比河流（Andy 2026-09-15：「上方也多一個選項新增河流圖」）：
         把下方那張河流圖的五條倍數線直接疊在 K 棒上，同一套倍數，兩邊對得起來。
         需要近四季 EPS，所以只有日／週／月線畫得出來（分 K 的日期對不到財報那條階梯）。*/
      { k: 'peRiver', label: '本益比河流', on: () => !!cfg.peRiver, params: () => [], toggle: () => { cfg.peRiver = !cfg.peRiver; }, color: '#b39dff' },
    ];
    /* ★ 2026-09-25（審查 R5）：以前參數輸入框直接排在籤裡，KD 籤 156px 寬、大半是三個輸入框 ——
       點籤的正中間點到的是輸入框，指標不會開關（要點左邊的「KD」兩個字才行）。
       改成：籤平常只顯示參數**文字**（整顆都是開關，點哪裡都切換）；
       要改參數按籤尾巴那顆小 ⚙，才把輸入框攤開（按 Enter 或再按一次 ⚙ 收起）。*/
    let chipEdit = null;
    const drawChips = () => {
      chips.innerHTML = chipDefs.map(c => {
        const ps = c.params(), ed = chipEdit === c.k && ps.length;
        const pv = ps.length ? (ed
          ? ps.map(p => `<input data-k="${c.k}" data-p="${p.key}" value="${p.val}" style="width:${p.w}px">`).join('')
          : `<span class="pv">${A.fmt.esc(ps.map(p => p.val).join(','))}</span>`)
          + `<button type="button" class="pedit" data-k="${c.k}" title="改 ${c.label} 參數" aria-label="改 ${c.label} 參數">⚙</button>` : '';
        return `<span class="chip ${c.on() ? 'on' : ''}${ed ? ' editing' : ''}" data-k="${c.k}"><i style="background:${c.color}"></i>${c.label}${pv}</span>`;
      }).join('');
      $$('.chip', chips).forEach(ch => ch.onclick = (e) => {
        if (e.target.tagName === 'INPUT') return;
        if (e.target.closest('.pedit')) {
          e.stopPropagation();
          chipEdit = chipEdit === ch.dataset.k ? null : ch.dataset.k;
          drawChips();
          const f = chipEdit && chips.querySelector(`.chip[data-k="${chipEdit}"] input`); if (f) { f.focus(); f.select(); }
          return;
        }
        chipDefs.find(c => c.k === ch.dataset.k).toggle(); saveCfg(cfg); drawChips(); apply();
      });
      $$('.chip input', chips).forEach(inp => {
        inp.onclick = (e) => e.stopPropagation();
        inp.onchange = () => {
          if (inp._done) return;             // Enter 已經處理過（原生 change 會在元素被換掉之後再補一次）
          chipDefs.find(c => c.k === inp.dataset.k).set(inp.value, inp.dataset.p); saveCfg(cfg);
          const nextP = inp.nextElementSibling && inp.nextElementSibling.tagName === 'INPUT' ? inp.nextElementSibling.dataset.p : null;
          drawChips(); apply();
          // 重畫之後焦點會掉；還在編輯就把焦點交給下一格，連續改 KD 三個數字才順
          if (chipEdit && nextP) { const nx = chips.querySelector(`.chip[data-k="${chipEdit}"] input[data-p="${nextP}"]`); if (nx) nx.focus(); }
        };
        inp.onkeydown = (e) => {
          if (e.key !== 'Enter' && e.key !== 'Escape') return;
          e.preventDefault(); inp._done = true; chipEdit = null;
          if (e.key === 'Enter') { chipDefs.find(c => c.k === inp.dataset.k).set(inp.value, inp.dataset.p); saveCfg(cfg); }
          drawChips(); if (e.key === 'Enter') apply();
        };
      });
    };
    const build = () => {
      if (kchart) { kchart.destroy(); kchart = null; } miniCharts.forEach(c => c.destroy()); miniCharts = [];
      if (state.mtfMode) { host.innerHTML = `<div class="mtf-grid" id="mtfGrid"></div>`; buildMtfGrid(pg); return; }
      host.innerHTML = `<div id="lwc"><div class="legend-ov" id="legendOv"></div><div class="ohlcbox" id="ohlcBox" hidden></div></div>`;
      kchart = new KChart($('#lwc'), { tf: state.tf, onText: () => window.prompt('文字內容', '') });
      apply();
      enableDraw(pg);
    };
    const apply = () => {
      const box = $('#lwc'); if (!box) return;
      state._apply = apply;      // 驗收用：模擬一次「即時更新造成的重畫」
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
          + `。先改畫${fb === '60m' ? ' 1 小時' : '日線'} K（最近一份可用的資料）；即時報價接上後會自動換回 ${TF_NAME[state.tf] || state.tf} K。`;
        tf = fb; bars = barsFor(pg, fb); live = false;
      }
      if (!bars || bars.length < (live ? 2 : 5)) {
        const why = live
          ? (window.LiveK ? window.LiveK.sourceNote(state.tf) : '即時層還沒載入')
          : pg.meta.tier === 'thin' ? (pg.note || '歷史價量還在回補')
          : /m$/.test(state.tf) ? '這檔沒有分 K（只有族群成分股與成交值前段會抓 Yahoo 分 K）；日線／週線／月線可以正常看'
          : '這個週期尚無資料';
        if (kchart) { kchart.destroy(); kchart = null; }
        box.innerHTML = `<div class="empty" style="height:100%">${A.fmt.esc(why)}</div>`;
        setLiveNote(live ? why : '');
        return;
      }
      setLiveNote(fbNote || (live && window.LiveK ? window.LiveK.sourceNote(state.tf) : ''));
      state.fallbackTf = fbNote ? tf : null;      // 驗收讀這個
      // 上一個週期沒資料時圖被拆掉了，換回有資料的週期要重建（不重建的話會整張空白到重新整理為止）
      if (!kchart || !$('#legendOv')) {
        if (kchart) { kchart.destroy(); kchart = null; }
        box.innerHTML = '<div class="legend-ov" id="legendOv"></div><div class="ohlcbox" id="ohlcBox" hidden></div>';
        kchart = new KChart(box, { tf: tf, onText: () => window.prompt('文字內容', '') });
        enableDraw(pg);
      }
      // 即時更新（同一檔、同一個週期、圖還在）就保留目前的縮放與位置
      const keep = kchart._liveKey === pg.meta.code + '|' + tf;
      kchart._liveKey = pg.meta.code + '|' + tf;
      kchart.setBars(bars, tf, keep);
      /* 本益比倍數線：算好之後掛在 chart 上（不要塞進 cfg —— cfg 會被寫進 localStorage，
         幾千筆數字存進去毫無意義）。applyIndicators 會自己去讀 this.peBands。*/
      kchart.peBands = cfg.peRiver ? peBandsForBars(peRiver(pg), bars, peStyle(cfg)) : null;
      kchart.applyIndicators(cfg);
      /* ★ 棒寬只在「換股票／換週期」時套用設定值。
         以前每次 apply() 都套一次 —— 而盤中每幾秒就會 apply() 一次，
         所以使用者滾滾輪放大之後，下一次更新就把棒寬硬拉回 cfg.bar，
         畫面看起來就是「縮放完自己跳回原來大小」（Andy 2026-09-18）。
         keep 為真＝這是即時更新造成的重畫，要尊重使用者自己拉的縮放。*/
      if (!keep && kchart.setBarSpacing) kchart.setBarSpacing(cfg.bar || 11);
      kchart.setZones(cfg.smc && !live ? zonesFor(pg, tf) : [], cfg.zone || undefined);
      kchart.setMarkers(cfg.marks && !live ? marksFor(pg, tf) : {});
      const v = pg.verdict || {};
      kchart.setPriceLines(cfg.lines && tf === '1d' ? [{ price: v.stop, title: '停損', color: '#ffb454' }, { price: v.tp1, title: '目標 1', color: '#3ee0ff' }, { price: v.tp2, title: '目標 2', color: '#8b7bff' }] : []);
      const legend = $('#legendOv');
      const TFN = { '5s': '5 秒（即時）', '1m': '1 分（即時）', '5m': '5 分（即時）', '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' };
      kchart.setWatermark(`${pg.meta.name} ${pg.meta.code} · ${TFN[tf] || tf}${fbNote ? '（分 K 暫代）' : ''}`);
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
        box.addEventListener('pointerup', () => setTimeout(() => {
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
      b.onclick = () => { $$('#tfSeg button').forEach(x => x.classList.toggle('on', x === b)); state.tf = b.dataset.tf; if (state.mtfMode) build(); else apply(); };
      b.oncontextmenu = (e) => { // 自訂的週期按右鍵可以移除
        if (TF_BUILTIN.includes(b.dataset.tf)) return;
        e.preventDefault();
        cfg.tfs = (cfg.tfs || []).filter(t => t !== b.dataset.tf); saveCfg(cfg);
        if (state.tf === b.dataset.tf) state.tf = '1d';
        $('#tfSeg').innerHTML = tfButtons(); wireTf(); markTf(pg); build();
      };
    });
    wireTf(); markTf(pg);
    $('#tfAdd').onclick = () => {
      const pop = $('#cfgPop');
      if (popVisible(pop, 'tf')) { closePop(pop); return; }
      pop.hidden = false; pop.dataset.kind = 'tf';
      pop.innerHTML = `<div class="ttl">自訂時間週期</div>
        <div class="note">用日線合成，例如 3 日＝三根日線併一根；週線同理。輸入後按加入，按鈕上按右鍵可移除。</div>
        <div class="row" style="margin-top:8px"><input id="tfN" type="number" min="2" max="60" value="3" style="width:64px">
        <select id="tfU"><option value="D">日</option><option value="W">週</option></select>
        <button class="btn small primary" id="tfOk">加入</button><button class="btn small" id="tfNo">關閉</button></div>`;
      $('#tfOk').onclick = () => {
        const n = Math.max(2, Math.min(60, +$('#tfN').value || 3)), u = $('#tfU').value;
        const id = n + u;
        cfg.tfs = [...new Set([...(cfg.tfs || []), id])].slice(0, 6); saveCfg(cfg);
        state.tf = id; pop.hidden = true; $('#tfSeg').innerHTML = tfButtons(); wireTf(); markTf(pg); build();
      };
      $('#tfNo').onclick = () => { closePop(pop); };
      placePop(pop, $('#tfAdd'));
    };

    // ---- 圖表設定：線寬、均線條數／週期／顏色／粗細
    $('#cfgBtn').onclick = () => {
      const pop = $('#cfgPop');
      // ★ 用「畫面上真的看得到嗎」決定開或關，不是只看 hidden —— 理由見 popVisible() 上面那段
      if (popVisible(pop, 'style')) { closePop(pop); return; }
      pop.hidden = false; pop.dataset.kind = 'style';
      const mas = cfg.ma || [];
      const zn = Object.assign({}, KUtil.ZONE_DEF, cfg.zone || {});
      const pes = peStyle(cfg);
      pop.innerHTML = `<div class="ttl">圖表設定</div>
        <div class="frow"><label>整體線寬</label><input id="lw" type="range" min="1" max="4" step="1" value="${cfg.lineWidth || 1}"><span class="val" id="lwv">${cfg.lineWidth || 1}px</span></div>
        <div class="frow"><label>K 棒寬度</label><input id="bw" type="range" min="3" max="28" step="1" value="${cfg.bar || 11}"><span class="val" id="bwv">${cfg.bar || 11}px</span></div>
        <div class="ttl2">均線（最多 6 條）</div>
        <div id="maRows">${mas.map((n, i) => `<div class="frow marow" data-i="${i}">
          <input type="number" min="2" max="480" value="${n}" data-f="n" style="width:62px">
          <input type="color" value="${(cfg.maColor || [])[i] || KUtil.colors.ma[i % 6]}" data-f="c">
          <input type="range" min="1" max="4" step="1" value="${(cfg.maWidth || [])[i] || cfg.lineWidth || 1}" data-f="w" style="width:78px">
          <button class="btn small" data-f="del" title="移除這條">✕</button></div>`).join('')}</div>
        <div class="row" style="margin-top:6px"><button class="btn small" id="maAdd" ${mas.length >= 6 ? 'disabled' : ''}>＋ 新增均線</button></div>
        <div class="ttl2">指標樣式（顏色 · 線寬 · 透明度）</div>
        <div id="stRows">${STYLE_ROWS.map(([k, label, keys, names]) => {
          const v = Object.assign({ w: cfg.lineWidth || 1, o: 100 }, STYLE_DEF[k], (cfg.st || {})[k] || {});
          return `<div class="frow strow" data-k="${k}"><label>${label}</label>
            ${keys.map((ck, i) => `<span class="cwrap" title="${names[i]}"><input type="color" data-f="${ck}" value="${v[ck]}"><em>${names[i]}</em></span>`).join('')}
            <input type="range" min="1" max="4" step="1" data-f="w" value="${v.w}" title="線寬" style="width:64px">
            <input type="range" min="15" max="100" step="5" data-f="o" value="${v.o}" title="透明度" style="width:78px">
            <span class="val" data-f="ov">${v.o}%</span></div>`;
        }).join('')}</div>
        <div class="ttl2">本益比河流（六個區間的顏色 · 線寬 · 色帶透明度）</div>
        <div class="frow strow" id="peRow" style="flex-wrap:wrap">
          ${PE_ZONES.map((z, i) => `<span class="cwrap" title="${z.name}"><input type="color" data-z="${i}" value="${pes.z[i]}"><em>${z.name}</em></span>`).join('')}
          <label style="min-width:0">線寬</label><input type="range" min="1" max="4" step="1" data-f="w" value="${pes.w}" style="width:60px">
          <label style="min-width:0">透明</label><input type="range" min="5" max="100" step="5" data-f="o" value="${pes.o}" style="width:70px">
          <span class="val" id="peOv">${pes.o}%</span>
        </div>
        <div class="ttl2">SMC 供需區</div>
        <div class="frow" id="zoneRow">
          <span class="cwrap" title="需求區"><input type="color" data-f="demand" value="${zn.demand}"><em>需求</em></span>
          <span class="cwrap" title="供給區"><input type="color" data-f="supply" value="${zn.supply}"><em>供給</em></span>
          <label style="margin-left:4px">填色</label><input type="range" min="0" max="45" step="1" data-f="fill" value="${zn.fill}" style="width:74px">
          <label>框線</label><input type="range" min="20" max="100" step="5" data-f="line" value="${zn.line}" style="width:66px">
          <input type="range" min="1" max="3" step="1" data-f="width" value="${zn.width}" title="框線粗細" style="width:54px">
          <label class="chk"><input type="checkbox" data-f="label" ${zn.label ? 'checked' : ''}>標籤</label>
        </div>
        <div class="row" style="margin-top:8px">
          <button class="btn small" id="cfgReset">回復預設</button><div class="sp"></div><button class="btn small primary" id="cfgClose">完成</button></div>`;
      placePop(pop, $('#cfgBtn'));
      const sync = () => {
        cfg.ma = []; cfg.maColor = []; cfg.maWidth = [];
        $$('#maRows .marow').forEach(r => {
          cfg.ma.push(+$('[data-f=n]', r).value || 20);
          cfg.maColor.push($('[data-f=c]', r).value);
          cfg.maWidth.push(+$('[data-f=w]', r).value || 1);
        });
        cfg.lineWidth = +$('#lw').value || 1;
        cfg.bar = +$('#bw').value || 11;
        cfg.st = {};
        $$('#stRows .strow').forEach(r => {
          const o = {};
          $$('input', r).forEach(i => { o[i.dataset.f] = i.type === 'color' ? i.value : +i.value; });
          const ov = $('[data-f=ov]', r); if (ov) ov.textContent = o.o + '%';
          cfg.st[r.dataset.k] = o;
        });
        // 本益比河流：六個顏色 ＋ 線寬 ＋ 透明度（cfg.st 上面被整個重建了，所以在這裡補回去）
        const pr = $('#peRow');
        if (pr) {
          const z = PE_ZONES.map((_, i) => $(`[data-z="${i}"]`, pr).value);
          const w = +$('[data-f=w]', pr).value || 1, o = +$('[data-f=o]', pr).value || 30;
          const ov = $('#peOv'); if (ov) ov.textContent = o + '%';
          cfg.st.pe = { z, w, o };
        }
        const zr = $('#zoneRow');
        if (zr) { const z = {}; $$('input', zr).forEach(i => {
          z[i.dataset.f] = i.type === 'color' ? i.value : i.type === 'checkbox' ? i.checked : +i.value; });
          cfg.zone = z; }
        const add = $('#maAdd'); if (add) add.disabled = cfg.ma.length >= 6;   // 刪到剩 5 條要能再加回來
        saveCfg(cfg); drawChips(); apply();
      };
      $('#lw').oninput = () => {
        $('#lwv').textContent = $('#lw').value + 'px';
        $$('#maRows [data-f=w]').forEach(i => { i.value = $('#lw').value; });   // 整體線寬帶動每條均線
        sync();
      };
      $('#bw').oninput = () => { $('#bwv').textContent = $('#bw').value + 'px'; sync(); };
      $$('#peRow input').forEach(i => { i.oninput = sync; i.onchange = sync; });
      const wireRows = () => $$('#maRows .marow').forEach(r => {
        $$('input', r).forEach(i => { i.oninput = sync; i.onchange = sync; });
        $('[data-f=del]', r).onclick = () => { r.remove(); sync(); };
      });
      wireRows();
      $$('#stRows .strow input, #zoneRow input').forEach(i => { i.oninput = sync; i.onchange = sync; });
      $('#maAdd').onclick = () => {
        const i = $$('#maRows .marow').length; if (i >= 6) return;
        const d = document.createElement('div'); d.className = 'frow marow';
        d.innerHTML = `<input type="number" min="2" max="480" value="10" data-f="n" style="width:62px">
          <input type="color" value="${KUtil.colors.ma[i % 6]}" data-f="c">
          <input type="range" min="1" max="4" step="1" value="1" data-f="w" style="width:78px">
          <button class="btn small" data-f="del" title="移除這條">✕</button>`;
        $('#maRows').appendChild(d); wireRows(); sync();
      };
      $('#cfgReset').onclick = () => { Object.assign(cfg, JSON.parse(JSON.stringify(DEFAULT_CFG))); saveCfg(cfg); closePop(pop); drawChips(); apply(); };
      $('#cfgClose').onclick = () => { closePop(pop); };
    };

    $('#mtfBtn').onclick = () => { state.mtfMode = !state.mtfMode; $('#mtfBtn').textContent = state.mtfMode ? '單一週期' : '四週期同看'; build(); };
    $('#fitBtn').onclick = () => {
      // 連同拖過的面板高度一起還原 —— 拉壞了要有一鍵回去的地方
      const c = state.cfg || loadCfg();
      if (c.paneH) { delete c.paneH; saveCfg(c); state.cfg = c; if (kchart) kchart.applyIndicators(c); }
      if (kchart) kchart.resetView(160);
    };
    /* 寬版（Andy：「K 線圖太小，版面需要擴大」）：把右側事件欄收起來，整個視窗寬度都給圖。
       Lightweight Charts 是 autoSize，容器一變寬它自己重畫；ECharts 的小圖要自己踢一下 resize。
       狀態存 localStorage，下次進個股頁維持同一個版面。 */
    const wideBtn = $('#wideBtn');
    const paintWide = () => {
      const on = document.body.classList.contains('kwide');
      wideBtn.classList.toggle('on', on);
      wideBtn.textContent = on ? '⤢ 寬版 ✓' : '⤢ 寬版';
      wideBtn.title = on ? '關掉寬版，把右側事件欄叫回來' : '收起右側事件欄，把整個視窗的寬度讓給 K 線圖';
    };
    wideBtn.onclick = () => {
      const on = document.body.classList.toggle('kwide');
      try { localStorage.setItem('tw.kwide', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
      paintWide();
      setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 60);
    };
    paintWide();
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
        drawTgl.title = on ? '收起畫線工具列（畫過的線不會消失）' : '打開畫線工具列';
      };
      drawTgl.onclick = () => {
        on = !on;
        try { localStorage.setItem('tw.drawbar', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
        paintDraw();
      };
      paintDraw();
    }
    drawChips(); drawBar(); build();
  }

  // 每檔每週期各存一份手繪線，換股或換週期就換一組
  function enableDraw(pg) {
    if (!kchart) return;
    const d = kchart.enableDrawing(`tw.draw.${pg.meta.code}.${state.tf}`);
    d.setTool(drawTool); d.setColor(drawColor); d.setWidth(drawW); d.setFill(drawFill);
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
  // Andy 2026-09-15：「劃線需要有5種不同粗細可選，框格可選擇填滿或透明」
  const DRAW_WIDTHS = [1, 1.5, 2.5, 4, 6];
  const DW_KEY = 'tw.draw.style';
  let drawTool = 'cursor', drawColor = KUtil.DRAW_COLORS[0], drawW = 1.5, drawFill = false;
  try {
    const st = JSON.parse(localStorage.getItem(DW_KEY) || '{}');
    if (DRAW_WIDTHS.indexOf(+st.w) >= 0) drawW = +st.w;
    if (KUtil.DRAW_COLORS.indexOf(st.c) >= 0) drawColor = st.c;
    drawFill = !!st.fill;
  } catch (e) { /* 忽略 */ }
  const saveDrawStyle = () => {
    try { localStorage.setItem(DW_KEY, JSON.stringify({ w: drawW, c: drawColor, fill: drawFill })); }
    catch (e) { /* 忽略 */ }
  };

  function drawBar() {
    const bar = $('#drawBar'); if (!bar) return;
    bar.innerHTML = KUtil.DRAW_TOOLS.map(t =>
      `<button class="dtool ${t.k === drawTool ? 'on' : ''}" data-t="${t.k}" title="${t.label}${t.pts === 2 ? '（拉的時候按住 Shift ＝ 鎖水平／垂直）' : ''}">
         <svg viewBox="0 0 18 18"><path d="${t.icon}"/></svg></button>`).join('')
      + `<div class="dsep"></div>`
      + KUtil.DRAW_COLORS.map(c => `<button class="dcol ${c === drawColor ? 'on' : ''}" data-c="${c}" style="background:${c}" title="顏色"></button>`).join('')
      + `<div class="dsep"></div>`
      // 五段粗細：用線條本身的厚度表示，一眼看得出差別
      + DRAW_WIDTHS.map(w => `<button class="dw ${w === drawW ? 'on' : ''}" data-w="${w}" title="線寬 ${w}px">
           <span style="height:${w}px"></span></button>`).join('')
      + `<div class="dsep"></div>
         <button class="dtool dfill ${drawFill ? 'on' : ''}" data-a="fill" title="方框：${drawFill ? '填滿（點一下改成透明）' : '透明（點一下改成填滿）'}">
           <svg viewBox="0 0 18 18"><rect x="3" y="4" width="12" height="10" ${drawFill ? 'fill="currentColor"' : ''}/></svg></button>
         <button class="dtool" data-a="undo" title="復原上一筆"><svg viewBox="0 0 18 18"><path d="M7,4 L3,8 L7,12 M3,8 H11 a4,4 0 0 1 0,8 H8"/></svg></button>
         <button class="dtool" data-a="clear" title="清空這檔這個週期的所有線"><svg viewBox="0 0 18 18"><path d="M3,3 L15,15 M15,3 L3,15"/></svg></button>`;
    $$('.dtool[data-t]', bar).forEach(b => b.onclick = () => {
      drawTool = b.dataset.t; drawBar(); if (kchart && kchart.draw) kchart.draw.setTool(drawTool);
    });
    $$('.dcol', bar).forEach(b => b.onclick = () => {
      drawColor = b.dataset.c; saveDrawStyle(); drawBar(); if (kchart && kchart.draw) kchart.draw.setColor(drawColor);
    });
    $$('.dw', bar).forEach(b => b.onclick = () => {
      drawW = +b.dataset.w; saveDrawStyle(); drawBar(); if (kchart && kchart.draw) kchart.draw.setWidth(drawW);
    });
    $$('.dtool[data-a]', bar).forEach(b => b.onclick = () => {
      if (b.dataset.a === 'fill') {
        drawFill = !drawFill; saveDrawStyle(); drawBar();
        if (kchart && kchart.draw) kchart.draw.setFill(drawFill);
        return;
      }
      if (!kchart || !kchart.draw) return;
      if (b.dataset.a === 'undo') kchart.draw.undo(); else kchart.draw.clear();
    });
  }
  /* 四週期同看。
     Andy 2026-09-15：「同事看4個週期那頁需要新增可以切換週期，不然我看不到我要的」——
     以前四格是程式挑的（有 15 分就 15m/60m/240m/1d，沒有就取最後四個），使用者換不掉。
     現在每一格上面都有一個下拉選單，選什麼記在 `tw.kcfg` 的 mtfTfs 裡，換股票也還在。 */
  const MTF_LABEL = (tf) => ({ '5s': '5 秒（即時）', '1m': '1 分（即時）', '5m': '5 分（即時）',
    '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' })[tf] || tfLabel(tf);

  function mtfPick(pg) {
    const cfg = state.cfg || loadCfg();
    const saved = Array.isArray(cfg.mtfTfs) ? cfg.mtfTfs.filter(t => tfList().indexOf(t) >= 0) : null;
    if (saved && saved.length === 4) return saved;
    const have = (tf) => barsFor(pg, tf).length >= 20;
    const pref = ['15m', '60m', '240m', '1d', '1w', '1M'].filter(have);
    const pick = pref.length >= 4 ? (have('15m') ? ['15m', '60m', '240m', '1d'] : pref.slice(-4)) : pref;
    while (pick.length < 4 && pick.length) pick.push(pick[pick.length - 1]);
    return pick;
  }

  function buildMtfGrid(pg) {
    const cfg = state.cfg || loadCfg();
    const pick = mtfPick(pg);
    const grid = $('#mtfGrid');
    const opts = (cur) => tfList().map(tf =>
      `<option value="${tf}"${tf === cur ? ' selected' : ''}>${MTF_LABEL(tf)}</option>`).join('');
    grid.innerHTML = pick.map((tf, i) => {
      const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf];
      return `<div class="mtf-cell"><div class="cap">
        <select class="mtfsel" data-i="${i}" title="換這一格要看的週期">${opts(tf)}</select>
        ${t ? `<span style="color:${A.upDown(t.trend)}">${t.trend > 0 ? '多頭結構' : t.trend < 0 ? '空頭結構' : '盤整'}</span> · 均線${t.ma_align > 0 ? '多排' : t.ma_align < 0 ? '空排' : '糾結'}${t.rsi != null ? ' · RSI ' + t.rsi.toFixed(0) : ''}` : ''}
        </div><div class="cv" id="mini-${i}"></div></div>`;
    }).join('');
    pick.forEach((tf, i) => {
      const el = $('#mini-' + i);
      const bars = barsFor(pg, tf);
      if (!bars || bars.length < 2) {
        el.innerHTML = `<div class="empty" style="height:100%">${A.fmt.esc(isLiveTf(tf) ? liveEmptyMsg() : '這個週期尚無資料')}</div>`;
        return;
      }
      const c = new KChart(el, { mini: true, tf });
      c.setBars(bars, tf);
      c.applyIndicators({ ma: [20, 60], vol: false });
      if (!isLiveTf(tf)) { c.setZones(zonesFor(pg, tf)); c.setMarkers(marksFor(pg, tf)); }
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
  function renderMtf(pg) {
    const el = $('#mtfCard'); const sm = pg.mtf && pg.mtf.summary; if (!sm || !sm.headline) { el.innerHTML = '<h3>多週期判讀</h3><div class="empty">資料不足</div>'; return; }
    const lv = sm.key_levels || {};
    const row = (z, kind) => `<div class="k" style="border-left:3px solid ${kind === 'support' ? '#2ee59d' : '#ff4d6d'}"><div class="l">${A.fmt.esc(z.label)} ${kind === 'support' ? '需求區' : '供給區'}</div><div class="v" style="font-size:15px">${z.low} – ${z.high}</div><div class="l">距現價 ${A.fmt.pct(z.dist_pct)} · 分數 ${z.score}</div></div>`;
    /* ★ 2026-09-24 說明精簡：副標縮成一句，完整讀法搬進「怎麼看 ?」 */
    el.innerHTML = `<div class="row spread"><h3>多週期判讀 ${hq('mtf', '多週期判讀')}</h3></div>
      <div class="howtxt" id="how-mtf" hidden>${A.howHTML('這張卡回答：各週期方向一不一致、該在哪裡進場。', [
        '大週期（週線、日線）定方向',
        '小週期（4 小時、1 小時、15 分）找進場',
        '每個週期一顆燈：多／空／盤整',
        '支撐＝需求區、壓力＝供給區，由近到遠',
        '距現價＝那一區離現在價格多遠',
      ], '分 K 還沒取得時，小週期暫以日線代替（判讀裡會寫出來）。')}</div>
      <div class="lights">${(sm.tf_used || []).map(tf => { const t = sm.per_tf[tf]; return `<span class="light ${t.trend > 0 ? 'pos' : t.trend < 0 ? 'neg' : ''}">${({ '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' })[tf]} ${t.trend > 0 ? '多' : t.trend < 0 ? '空' : '盤整'}</span>`; }).join('')}</div>
      <div class="verdict" data-readout style="margin:10px 0"><h3 style="font-size:16px">${A.fmt.esc(sm.headline)}</h3><ul>${(sm.script || []).map(x => `<li>${A.fmt.esc(x)}</li>`).join('')}</ul></div>
      <div class="grid g2"><div><h4>支撐（由近到遠）</h4><div class="kvs" style="margin-top:6px">${(lv.support || []).map(z => row(z, 'support')).join('') || '<div class="note">沒有通過門檻的需求區</div>'}</div></div><div><h4>壓力（由近到遠）</h4><div class="kvs" style="margin-top:6px">${(lv.resistance || []).map(z => row(z, 'resistance')).join('') || '<div class="note">上方沒有通過門檻的供給區</div>'}</div></div></div>
      ${pg.verdict && pg.verdict.weekly_note ? `<div class="note" data-readout style="margin-top:8px">${A.fmt.esc(pg.verdict.weekly_note)}</div>` : ''}`;
  }

  // ---------------------------------------------------------------- 個股分頁
  function renderTab(pg, tab) {
    const el = $('#stockTab');
    ({ overview: tabOverview, revenue: tabRevenue, profit: tabProfit, dividend: tabDividend, chips: tabChips, basics: tabBasics, news: tabNews })[tab](pg, el);
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
  const statK = (l, v, cls) => `<div class="k"><div class="l">${l}</div><div class="v ${cls || ''}">${v}</div></div>`;
  function fundCard(pg) {
    const f = pg.fundamental || {}, dv = pg.dividends || {};
    const k = statK;
    return `<div class="card"><h3>基本面 <small data-readout>財報到 ${f.latest_period || '—'}</small></h3><div class="kvs" style="margin-top:8px">${k('近四季 EPS', f.ttm_eps != null ? A.fmt.n(f.ttm_eps) : '—')}${k('本益比', f.pe ? A.fmt.n(f.pe, 1) : '—')}${k('同業分位', f.percentile != null ? A.fmt.n(f.percentile, 0) + '%' : '<small>樣本不足</small>')}${k('ROE', f.roe != null ? A.fmt.n(f.roe, 1) + '%' : '—')}${k('毛利率', f.gross_margin != null ? A.fmt.n(f.gross_margin, 1) + '%' : '—')}${k('月營收 YoY', A.fmt.pct(f.rev_yoy), A.fmt.cls(f.rev_yoy))}${k('營運動能', f.momentum_score != null ? A.fmt.n(f.momentum_score, 0) + ' / 100' : '—')}${k('殖利率（近四次）', dv.yield_ttm != null ? A.fmt.n(dv.yield_ttm) + '%' : '—')}</div><div class="note" style="margin-top:8px">${f.group_name ? `同族群（${f.group_name}，n=${f.group_n}）本益比中位 ${f.group_median != null ? A.fmt.n(f.group_median, 1) : '—'}${f.vs_median != null ? (Math.abs(f.vs_median) < 0.5 ? '，本檔與中位相當' : '，本檔 ' + (f.vs_median > 0 ? '高於' : '低於') + '中位 ' + A.fmt.n(Math.abs(f.vs_median), 0) + '%') : ''}` : '本益比只在同族群內比較'}</div></div>`;
  }
  function chipCard(pg) {
    const s = pg.summary || {}, iv = pg.inst_v3 || {};
    const holders = pg.holders && pg.holders.length ? pg.holders[pg.holders.length - 1] : null; const hPrev = pg.holders && pg.holders.length > 4 ? pg.holders[pg.holders.length - 5] : null;
    const k = statK;
    return `<div class="card"><h3>籌碼快照 ${hq('skchip', '籌碼快照')}</h3>${hbox('skchip', ['法人 20 日＝近 20 個交易日買賣超合計', '千張大戶＝集保持股 ≥1000 張的比例', '大戶 4 週變化＝跟 4 週前比', '散戶＝持股 ≤10 張的比例'], '「主力家數差」需券商分點資料（免費開放資料沒有）；這裡以集保千張大戶增減＋法人動向作替代指標。')}<div class="kvs" style="margin-top:8px">${k('法人 20 日', iv.sum20 != null ? A.fmt.lot(iv.sum20 / 1000) : '—', A.fmt.cls(iv.sum20))}${k('外資 20 日', iv.foreign20 != null ? A.fmt.lot(iv.foreign20 / 1000) : '—', A.fmt.cls(iv.foreign20))}${k('投信 20 日', iv.trust20 != null ? A.fmt.lot(iv.trust20 / 1000) : '—', A.fmt.cls(iv.trust20))}${k('千張大戶', holders ? A.fmt.n(holders[1], 1) + '%' : '—')}${k('大戶 4 週變化', holders && hPrev && holders[1] != null && hPrev[1] != null ? A.fmt.pct(holders[1] - hPrev[1], 2).replace('%', ' pp') : '—', holders && hPrev ? A.fmt.cls(holders[1] - hPrev[1]) : '')}${k('散戶（≤10 張）', holders ? A.fmt.n(holders[3], 1) + '%' : '—')}${k('融資餘額', pg.margin && pg.margin.length ? A.fmt.lot(pg.margin[pg.margin.length - 1][1]) : '—')}${k('量比', s.vol_ratio != null ? A.fmt.n(s.vol_ratio, 2) : '—')}</div></div>`;
  }
  function tabOverview(pg, el) {
    const signal = window.StockSignal ? window.StockSignal.view({ summary: pg.summary, verdict: pg.verdict }, A.fmt) : '';
    el.innerHTML = `<div class="grid g3">
      ${fundCard(pg)}
      ${chipCard(pg)}
      ${signal}</div>`;
  }
  function tabRevenue(pg, el) {
    const rv = pg.revenue || {}; const mo = rv.monthly || [];
    if (!mo.length) { el.innerHTML = '<div class="card"><div class="empty">尚無月營收歷史（回補進行中，每小時自動接續）</div></div>'; return; }
    const last = mo[mo.length - 1];
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">最新月份</div><div class="v">${last[0]}</div></div><div class="k"><div class="l">單月營收</div><div class="v">${A.fmt.yi(last[1])}</div></div><div class="k"><div class="l">YoY</div><div class="v ${A.fmt.cls(last[2])}">${A.fmt.pct(last[2])}</div></div><div class="k"><div class="l">MoM</div><div class="v ${A.fmt.cls(last[3])}">${A.fmt.pct(last[3])}</div></div><div class="k"><div class="l">累計營收</div><div class="v">${A.fmt.yi(last[4])}</div></div><div class="k"><div class="l">累計 YoY</div><div class="v ${A.fmt.cls(last[5])}">${A.fmt.pct(last[5])}</div></div></div>
      <div class="grid g2"><div class="card"><h3>每月營收與 YoY ${hq('skrev', '每月營收與 YoY')}</h3>${hbox('skrev', ['柱＝單月營收（左軸）', '線＝年增率 YoY（右軸）', '最多畫近 60 個月', 'YoY 連續翻正＝營收動能轉強'])}<div id="revBar" class="chart"></div></div>
      <div class="card"><div class="row spread"><h3>年度走勢 ${hq('skrevy', '年度走勢')}</h3>${hbox('skrevy', ['每條線＝一年，同月份疊在一起比', '最粗那條＝今年', '看哪幾個月固定比較高＝旺季', '右上切單月／累計'])}<div class="seg" id="revMode"><button data-v="m" class="on">單月</button><button data-v="c">累計</button></div></div><div id="revYear" class="chart"></div></div></div>
      <div class="card" style="margin-top:var(--gap-card)"><h3>月營收明細</h3><div class="tw" style="max-height:360px"><table><thead><tr><th class="l">月份</th><th>營收</th><th>YoY</th><th>MoM</th><th>累計</th><th>累計 YoY</th></tr></thead><tbody>${mo.slice().reverse().slice(0, 36).map(r => `<tr><td class="l mono">${r[0]}</td><td class="num">${A.fmt.yi(r[1])}</td><td class="num ${A.fmt.cls(r[2])}">${A.fmt.pct(r[2])}</td><td class="num ${A.fmt.cls(r[3])}">${A.fmt.pct(r[3])}</td><td class="num">${A.fmt.yi(r[4])}</td><td class="num ${A.fmt.cls(r[5])}">${A.fmt.pct(r[5])}</td></tr>`).join('')}</tbody></table></div></div>`;
    const t = mo.slice(-60);
    A.chart('revBar', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${p.seriesName === '營收' ? A.fmt.yi(p.value) : A.fmt.pct(p.value)}`).join('<br>') }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 50, top: 30, bottom: 30 },
      xAxis: { ...A.axisStyle, type: 'category', data: t.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2) } }, yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.yi(v) } }, { ...A.axisStyle, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }],
      series: [{ name: '營收', type: 'bar', data: t.map(r => r[1]), itemStyle: { color: 'rgba(62,224,255,.55)', borderRadius: [3, 3, 0, 0] } }, { name: 'YoY', type: 'line', yAxisIndex: 1, data: t.map(r => r[2]), smooth: .3, showSymbol: false, lineStyle: { color: '#ffb454', width: 2 } }] });
    const yr = (rv.yearly || []).slice(-6); let mode = 'm';
    const drawYear = () => { A.chart('revYear', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue} 月</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${A.fmt.yi(p.value)}`).join('<br>') }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 20, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: Array.from({ length: 12 }, (_, i) => i + 1), axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle, axisLabel: { formatter: v => A.fmt.yi(v) } },
      series: yr.map((y, i) => { let acc = 0; const d = Array.from({ length: 12 }, (_, m) => { const v = y.by_month[m + 1]; if (v == null) return null; if (mode === 'c') { acc += v; return acc; } return v; }); return { name: String(y.year), type: 'line', data: d, smooth: .2, symbolSize: 5, lineStyle: { width: i === yr.length - 1 ? 3 : 1.5, color: A.PALETTE[i] }, itemStyle: { color: A.PALETTE[i] } }; }) }); };
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
    { name: '低估', c: '#1c7a5a' }, { name: '價值', c: '#2ee59d' }, { name: '合理', c: '#c3ff5b' },
    { name: '觀望', c: '#ffd166' }, { name: '高估', c: '#ff8fab' }, { name: '警示', c: '#ff4d6d' },
  ];

  /* 河流圖的樣式也要能自己調（Andy 2026-09-15：「需要新增本益比河流圖的顏色 線條粗細 透明度 等設定」）。
     存在 cfg.st.pe：z＝六個區間的顏色（由下到上）、w＝線寬、o＝色帶透明度。
     沒設定過就回預設，所以舊的 localStorage 不用搬。 */
  function peStyle(cfg) {
    // of＝填滿模式自己的透明度（預設 90，一眼就是「填滿」的樣子）；o 是色帶模式的
    const raw = Object.assign({ w: 1, o: 30, of: 90 }, ((cfg || {}).st || {}).pe || {});
    const z = (Array.isArray(raw.z) && raw.z.length === 6) ? raw.z : PE_ZONES.map(x => x.c);
    return { w: Math.max(1, Math.min(4, +raw.w || 1)), o: Math.max(5, Math.min(100, +raw.o || 30)),
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
    pop = pop || document.getElementById('cfgPop');
    if (!pop) return;
    pop.hidden = true;
    pop.dataset.kind = '';
  }

  function wirePopDismiss() {
    if (wirePopDismiss._done) return;              // 只掛一次，否則每次重畫都多一個監聽
    wirePopDismiss._done = true;
    // 用 mousedown 而不是 click：在面板裡拖曳滑桿時，放開滑鼠的位置可能已經在面板外，
    // 那一下 click 的 target 會是面板外面，用 click 判斷會在拖到一半時把面板關掉。
    document.addEventListener('mousedown', (e) => {
      const pop = document.getElementById('cfgPop');
      if (!pop || pop.hidden) return;
      if (e.target.closest && (e.target.closest('.cfgpop') || e.target.closest('#cfgBtn, #tfAdd'))) return;
      closePop(pop);
    }, true);
    // 換頁一律收掉：不收的話 hidden 會留在 false，回來按 ⚙ 就變成「關掉看不見的面板」
    window.addEventListener('hashchange', () => closePop());
    // 2026-09-24：外面點一下本來就會關（上面那段）；登記進全站那一份是為了多一個 Esc
    const pop0 = document.getElementById('cfgPop');
    if (pop0 && A && A.dismissable) A.dismissable(pop0, () => closePop(pop0), { ignore: ['.cfgpop', '#cfgBtn', '#tfAdd'] });
  }

  function placePop(pop, btn) {
    if (!pop || !btn) return;
    wirePopDismiss();
    pop.hidden = false;                                  // 要先顯示才量得到寬高
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
  let peWired = false;
  function wirePeWin(el, r, redraw) {
    if (peWired || !r || !r.dates || r.dates.length < 30) return;
    const box = $('#peEnd', el); if (!box) return;
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
    peWired = true;
    apply();
  }

  function drawPeRiver(id, r0, mode, st) {
    const S = st || peStyle(null), ZN = S.zones;
    if (!r0) { A.empty(id, '需要至少四季連續財報，才算得出近四季 EPS'); return; }
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
        lineStyle: solid ? { color: 'rgba(0,0,0,.26)', width: 1 } : { width: 0 },
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
        lineStyle: { color: light ? 'rgba(255,255,255,.75)' : 'rgba(0,0,0,.55)', width: S.w + 3.4 } });
    }
    series.push({ name: '收盤', type: 'line', data: r.close, symbol: 'none', z: 6, silent: true,
      lineStyle: { color: closeC, width: S.w + 0.8 } });

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
    const place = () => {
      if (inst.isDisposed && inst.isDisposed()) return;
      const H = inst.getHeight(), W = inst.getWidth();
      const top = 26, bot = H - 36, gap = 14;
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
        style: { text: p.t, fill: p.c, font: '600 11px "Noto Sans TC", sans-serif', textVerticalAlign: 'middle', textAlign: 'left' } })) },
      { replaceMerge: ['graphic'] });
    };
    /* 'finished' 在滾輪放大時每一格都會發；每次都當場 setOption 會多一輪重畫，
       連續滾動時會拖慢到讓 wheelZoom 的 450ms 緩衝失效（整頁被帶著捲）。所以停手 150ms 才重排。*/
    inst.off('finished', inst._peSideFn);
    inst._peSideFn = () => { clearTimeout(inst._peSideT); inst._peSideT = setTimeout(place, 150); };
    inst.on('finished', inst._peSideFn);
    place();
  }

  function tabProfit(pg, el) {
    const q = (pg.profit || {}).quarters || []; const pe = pg.pe_history || [];
    if (!q.length) { el.innerHTML = '<div class="card"><div class="empty">尚無季報歷史（回補進行中）</div></div>'; return; }
    const last = q[q.length - 1];
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">最新季度</div><div class="v">${last[0]}</div></div><div class="k"><div class="l">單季 EPS</div><div class="v">${A.fmt.n(last[5])}</div></div><div class="k"><div class="l">年度累計 EPS</div><div class="v">${A.fmt.n(last[6])}</div></div><div class="k"><div class="l">EPS 年增（元）</div><div class="v ${A.fmt.cls(last[7])}">${last[7] != null ? (last[7] > 0 ? '+' : '') + A.fmt.n(last[7]) : '—'}</div></div><div class="k"><div class="l">毛利率</div><div class="v">${A.fmt.n(last[2], 1)}%</div></div><div class="k"><div class="l">營益率</div><div class="v">${A.fmt.n(last[3], 1)}%</div></div><div class="k"><div class="l">淨利率</div><div class="v">${A.fmt.n(last[4], 1)}%</div></div></div>
      <div class="card"><div class="row spread"><h3>本益比河流圖 ${hq('pe', '本益比河流圖')}</h3>
        <div class="row" style="gap:10px;align-items:center">
          <div class="seg" id="peMode"><button data-v="band">色帶分區</button><button data-v="fill">填滿</button><button data-v="mult">倍數線</button></div>
          <label class="opabox" title="色帶透明度（跟上面 K 線的本益比帶共用同一組設定）">透明度
            <input id="peOpa" type="range" min="10" max="100" step="5"><span class="val" id="peOpaV"></span></label>
        </div></div>
        <div class="row" style="gap:12px;flex-wrap:wrap;margin-bottom:6px">
          <div id="peLen" title="這張圖一次看多長一段"></div>
          <div id="peEnd" title="截止到哪一天：往回拉看以前的評價，按 ▶ 一天一天播"></div>
        </div>
        <div class="howtxt" id="how-pe" hidden>${A.howHTML('這張圖回答：市場現在給這一檔幾倍的評價。', [
          '每條帶＝近四季 EPS × 某個倍數',
          '收盤線落在哪條帶＝市場現在給的評價',
          '倍數用這檔自己的歷史分位，非固定',
          '色帶越紅＝市場給的評價越高',
          '拉 Bar 選長度與截止日，▶ 一天天播',
        ], '倍數不是寫死的 15／20／25 倍。右上三種畫法：色帶分區（顏色越紅評價越高）／填滿（整片實色，一眼看出收盤線落在哪一塊）／倍數線（線尾標本益比倍數）；透明度跟上面 K 線的本益比帶共用。')}</div>
        <div id="peWrap"><div id="peChart" class="chart" style="height:340px"></div></div><div class="note" id="peNote" data-readout></div></div>
      <div class="grid g2" style="margin-top:var(--gap-card)"><div class="card"><h3>EPS 與三率 ${hq('skeps', 'EPS 與三率')}</h3>${hbox('skeps', ['柱＝單季 EPS（左軸）', '線＝毛利率／營益率／淨利率（右軸）', '三率同步往上＝獲利品質變好'], '財報法規是季報，所以只有單季、沒有每月。')}<div id="profitChart" class="chart"></div></div><div class="card"><h3>本益比（每季）${hq('skpeq', '本益比（每季）')}</h3>${hbox('skpeq', ['每季一點＝財報可用日收盤 ÷ 近四季 EPS', '虧損（EPS ≤ 0）那季不算', '跟自己的過去比，看現在貴不貴'])}<div id="peQ" class="chart"></div></div></div>
      <div class="card" style="margin-top:var(--gap-card)"><h3>季報明細</h3><div class="tw" style="max-height:360px"><table><thead><tr><th class="l">季度</th><th>營收</th><th>毛利率</th><th>營益率</th><th>淨利率</th><th>淨利</th><th>EPS</th><th>累計 EPS</th><th>EPS 年增</th></tr></thead><tbody>${q.slice().reverse().map(r => `<tr><td class="l mono">${r[0]}</td><td class="num">${A.fmt.yi(r[1])}</td><td class="num">${A.fmt.n(r[2], 1)}%</td><td class="num">${A.fmt.n(r[3], 1)}%</td><td class="num">${A.fmt.n(r[4], 1)}%</td><td class="num">${A.fmt.yi(r[8])}</td><td class="num">${A.fmt.n(r[5])}</td><td class="num">${A.fmt.n(r[6])}</td><td class="num ${A.fmt.cls(r[7])}">${r[7] != null ? (r[7] > 0 ? '+' : '') + A.fmt.n(r[7]) : '—'}</td></tr>`).join('')}</tbody></table></div></div>`;
    A.chart('profitChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 50, right: 50, top: 30, bottom: 30 },
      xAxis: { ...A.axisStyle, type: 'category', data: q.map(r => r[0]), axisLabel: { color: A.CH.ink3 } }, yAxis: [{ ...A.axisStyle, name: 'EPS' }, { ...A.axisStyle, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }],
      series: [{ name: 'EPS', type: 'bar', itemStyle: { color: 'rgba(255,77,109,.7)' }, data: q.map(r => ({ value: r[5], itemStyle: { color: r[5] >= 0 ? 'rgba(255,77,109,.7)' : 'rgba(46,229,157,.7)', borderRadius: [3, 3, 0, 0] } })) }, { name: '毛利率', type: 'line', yAxisIndex: 1, data: q.map(r => r[2]), smooth: .3, showSymbol: false, lineStyle: { color: '#ffd166' } }, { name: '營益率', type: 'line', yAxisIndex: 1, data: q.map(r => r[3]), smooth: .3, showSymbol: false, lineStyle: { color: '#3ee0ff' } }, { name: '淨利率', type: 'line', yAxisIndex: 1, data: q.map(r => r[4]), smooth: .3, showSymbol: false, lineStyle: { color: '#8b7bff' } }] });
    if (pe.length) A.chart('peQ', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => { const r = pe[ps[0].dataIndex]; return `<b>${r.period}</b><br>本益比 ${r.pe ?? '—'}（區間 ${r.pe_low ?? '—'}–${r.pe_high ?? '—'}）<br>近四季 EPS ${r.ttm_eps}`; } }, grid: { left: 50, right: 20, top: 20, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: pe.map(r => r.period), axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle, scale: true },
      series: [{ name: '區間', type: 'line', data: pe.map(r => r.pe_low), lineStyle: { opacity: 0 }, stack: 'pe', showSymbol: false }, { name: '高低', type: 'line', data: pe.map(r => r.pe_high != null && r.pe_low != null ? r.pe_high - r.pe_low : null), lineStyle: { opacity: 0 }, stack: 'pe', areaStyle: { color: 'rgba(139,123,255,.2)' }, showSymbol: false }, { name: '本益比', type: 'line', data: pe.map(r => r.pe), lineStyle: { color: '#8b7bff', width: 2 }, symbolSize: 5 }] });
    else A.empty('peQ', '需要四季連續財報');

    // ---- 河流圖：兩種模式，選過就記住（換股票、重新整理都沿用）
    const river = peRiver(pg);
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
      if (note) {
        note.innerHTML = river
          ? `目前本益比 <b>${A.fmt.n(river.curPe, 1)}</b> 倍（近四季 EPS ${A.fmt.n(river.lastEps)} 元）`
            + `　·　落在 <b style="color:${st.zones[river.zoneIdx].c}">${river.zone.name}</b> 區`
            + `　·　這一檔的歷史倍數帶：${river.mult.join(' / ')}`
            + `　·　${HOWTO[mode]}`
          : '這一檔還沒有四季連續財報（或近四季 EPS 是負的），河流圖算不出來。';
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
    /* 縮放與拖曳（Andy 2026-09-16：「具備縮放功能，游標可以抓取移動」）。
       用全站那一套 wheelZoom，不用 ECharts 的 dataZoom —— dataZoom 會把 wheel 吃掉，
       頁面就捲不動了（DECISIONS #139 已經踩過一次）。*/
    A.wheelZoom($('#peWrap', el), { onZoom: () => {
      const i = window.echarts && echarts.getInstanceByDom($('#peChart', el)); if (i) i.resize();
    } });
    paint();
  }
  function tabDividend(pg, el) {
    const dv = pg.dividends || {}; const ev = dv.events || [], rs = dv.results || [];
    if (!ev.length && !rs.length) { el.innerHTML = '<div class="card"><div class="empty">尚無除權息資料（回補進行中；ETF 暫不抓）</div></div>'; return; }
    const byYear = {}; ev.filter(e => e.kind === 'cash').forEach(e => { const y = e.fiscal_year || (e.period || '').slice(0, 4); byYear[y] = (byYear[y] || 0) + (e.amount || 0); });
    const years = Object.keys(byYear).sort();
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">近四次現金股利</div><div class="v">${dv.cash_ttm != null ? A.fmt.n(dv.cash_ttm) + ' 元' : '—'}</div></div><div class="k"><div class="l">殖利率</div><div class="v">${dv.yield_ttm != null ? A.fmt.n(dv.yield_ttm) + '%' : '—'}</div></div><div class="k"><div class="l">最近除息</div><div class="v" style="font-size:15px">${rs[0] ? rs[0].date : '—'}</div></div><div class="k"><div class="l">最近填息</div><div class="v">${rs[0] ? (rs[0].fill_days === -1 ? '一年未填' : rs[0].fill_days != null ? rs[0].fill_days + ' 天' : '進行中') : '—'}</div></div></div>
      <div class="grid g2"><div class="card"><h3>各年度現金股利 ${hq('skdiv', '各年度現金股利')}</h3>${hbox('skdiv', ['柱＝那一年度配的現金股利合計', '年度＝股利所屬年度，不是發放年', '連年穩定或往上＝配息能力好'])}<div id="divBar" class="chart"></div></div>
      <div class="card"><h3>除權息紀錄 ${hq('skfill', '除權息紀錄')}</h3>${hbox('skfill', ['每一列＝一次除權或除息', '填息天數＝除息後第一次收回除息前收盤', '天數越短＝市場越認同', '「未填」＝到今天還沒填回'])}<div class="tw" style="max-height:300px"><table><thead><tr><th class="l">除權息日</th><th class="l">類別</th><th>股利</th><th>前收盤</th><th>參考價</th><th>填息</th></tr></thead><tbody>${rs.map(r => `<tr><td class="l mono">${r.date}</td><td class="l">${r.kind}</td><td class="num">${A.fmt.n(r.dividend)}</td><td class="num">${A.fmt.n(r.before_price)}</td><td class="num">${A.fmt.n(r.reference_price)}</td><td class="num">${r.fill_days === -1 ? '<span class="down">未填</span>' : r.fill_days != null ? r.fill_days + ' 天' : '—'}</td></tr>`).join('') || '<tr><td colspan="6" class="l muted">—</td></tr>'}</tbody></table></div></div></div>
      <div class="card" style="margin-top:var(--gap-card)"><h3>股利公告</h3><div class="tw" style="max-height:320px"><table><thead><tr><th class="l">所屬期間</th><th class="l">類別</th><th>金額（元/股）</th><th class="l">公告日</th><th class="l">除權息日</th><th class="l">發放日</th></tr></thead><tbody>${ev.map(e => `<tr><td class="l">${A.fmt.esc(e.period)}</td><td class="l">${e.kind === 'cash' ? '現金' : '股票'}</td><td class="num">${A.fmt.n(e.amount, 3)}</td><td class="l mono">${e.announce_date || '—'}</td><td class="l mono">${e.ex_date || '—'}</td><td class="l mono">${e.payment_date || '—'}</td></tr>`).join('')}</tbody></table></div></div>`;
    /* ★ 2026-09-25（審查 R5）：① 字族以前只寫 'JetBrains Mono'，沒裝的電腦退回襯線體 → 用全站 NUM_FONT；
       ② 數值以前直接印 4.036／22.999／144.392，小數位一格一個樣 → 一律最多 2 位（股利公告表才看到 3 位）；
       ③ 標籤色以前寫死近白 #e8eeff，淺色主題印在白底上看不見 → 跟主題走。*/
    const MF = A.NUM_FONT || 'JetBrains Mono, monospace';
    const d2 = (v) => { const x = Math.round(v * 100) / 100; return x.toFixed(Number.isInteger(x) ? 0 : 2); };
    if (years.length) A.chart('divBar', { tooltip: { ...A.tip, valueFormatter: (v) => d2(v) + ' 元' }, grid: { left: 50, right: 20, top: 16, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: years, axisLabel: { color: A.CH.ink3, fontFamily: MF } }, yAxis: { ...A.axisStyle, axisLabel: { color: A.CH.ink3, fontFamily: MF, formatter: (v) => d2(v) } }, series: [{ type: 'bar', data: years.map(y => +byYear[y].toFixed(2)), itemStyle: { color: '#ffb454', borderRadius: [3, 3, 0, 0] }, label: { show: true, position: 'top', color: A.CH.ink2, fontFamily: MF, fontSize: 12, formatter: (q) => d2(q.value) }, barWidth: '55%' }] }); else A.empty('divBar');
  }
  /* 籌碼頁：資料不夠就不要畫一張空圖。
     Andy：「若是籌碼下方無法抓取到數據，就把他替換其他方式，或是直接刪除」。
     規則：≥3 個點才畫線圖；只有 1~2 個點就改成把「現在的數字」直接列出來；
     一個點都沒有的那張卡片整張不出現。 */
  const CHIP_MIN = 3;
  function tabChips(pg, el) {
    const iv = (pg.inst_v3 || {}).daily || [], mg = pg.margin || [], ho = pg.holders || [];
    const cards = [];
    /* ★ 2026-09-25：副標搬進標題旁「?」；「最新一筆 日期」是資料狀態（只剩一兩筆時在列哪一天），留在標題上。
       numCard 的 why（「只回補到 N 天，先列數字」）也留著 —— 不寫會被讀成「這檔籌碼就這樣」。
       原本整頁最下面那行「主力需付費資料」搬進第一張卡的「?」小字。*/
    const MAIN_FINE = '主力（券商分點家數差）需付費資料，尚未提供；以千張大戶週變化與法人連續買賣作替代。';
    let hn = 0;
    const help = (title, sub) => { const key = 'skc' + (hn++);
      return [hq(key, title), hbox(key, [sub, '滑過圖看每天的數字', '點上方圖例可以關掉某一條'], hn === 1 ? MAIN_FINE : '')]; };
    const card = (id, title, sub) => { const [b, x] = help(title, sub); cards.push(`<div class="card"><h3>${title} ${b}</h3>${x}<div id="${id}" class="chart"></div></div>`); };
    const numCard = (title, sub, kvs, why) => { const [b, x] = help(title, '回補天數不夠，先直接列最新數字');
      cards.push(`<div class="card"><h3>${title} <small data-readout>${sub}</small> ${b}</h3>${x}
      <div class="kvs" style="margin-top:10px">${kvs}</div><div class="note" style="margin-top:8px">${why}</div></div>`); };
    const k = (l, v, cls) => `<div class="k"><div class="l">${l}</div><div class="v ${cls || ''}">${v}</div></div>`;

    if (iv.length >= CHIP_MIN) card('instChart', '三大法人', '每日買賣超（張）與累計');
    else if (iv.length) { const r = iv[iv.length - 1];
      numCard('三大法人', `最新一筆 ${r[0]}`,
        k('外資', A.fmt.lot(r[1] / 1000), A.fmt.cls(r[1])) + k('投信', A.fmt.lot(r[2] / 1000), A.fmt.cls(r[2]))
        + k('自營', A.fmt.lot(r[3] / 1000), A.fmt.cls(r[3])),
        `法人歷史只回補到 ${iv.length} 天，畫成走勢圖看不出東西，先直接列數字；回補滿 ${CHIP_MIN} 天以上就會變成走勢圖。`); }

    if (mg.length >= CHIP_MIN) card('marginChart', '融資融券', '餘額（張）');
    else if (mg.length) { const r = mg[mg.length - 1];
      numCard('融資融券', `最新一筆 ${r[0]}`,
        k('融資餘額', A.fmt.lot(r[1])) + k('融券餘額', A.fmt.lot(r[2])),
        `融資券歷史只回補到 ${mg.length} 天，兩個點連起來是一條假的斜線，先直接列數字。`); }

    if (ho.length >= CHIP_MIN) {
      card('holderChart', '大戶 / 散戶持股', '集保每週：≥1000、400–1000、≤10 張');
      card('holderCount', '股東人數', '人數下降＋大戶比例上升＝籌碼集中');
    } else if (ho.length) { const r = ho[ho.length - 1];
      numCard('集保股權分散', `最新一週 ${r[0]}`,
        k('千張大戶', A.fmt.n(r[1], 1) + '%') + k('400–1000 張', A.fmt.n(r[2], 1) + '%')
        + k('散戶 ≤10 張', A.fmt.n(r[3], 1) + '%') + k('股東人數', A.fmt.yi(r[4])),
        `集保是每週一筆，目前只累積到 ${ho.length} 週；滿 ${CHIP_MIN} 週就會變成走勢圖，看得出籌碼是在集中還是分散。`); }

    if (!cards.length) {
      el.innerHTML = `<div class="card"><div class="empty">這一檔的籌碼資料（法人、融資券、集保）還在回補，下一次盤後更新就會出現。</div></div>`;
      return;
    }
    el.innerHTML = cards.map((c, i) => (i % 2 === 0 ? `<div class="grid g2"${i ? ' style="margin-top:var(--gap-card)"' : ''}>` : '') + c + (i % 2 === 1 || i === cards.length - 1 ? '</div>' : '')).join('')
;

    if (iv.length >= CHIP_MIN) A.chart('instChart', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${A.fmt.lot(p.value / 1000)}`).join('<br>') }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 66, right: 78, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: iv.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(5) } }, yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) } }, { ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) }, splitLine: { show: false } }],
      series: [{ name: '外資', type: 'bar', stack: 'i', data: iv.map(r => r[1]), itemStyle: { color: '#3ee0ff' } }, { name: '投信', type: 'bar', stack: 'i', data: iv.map(r => r[2]), itemStyle: { color: '#ffb454' } }, { name: '自營', type: 'bar', stack: 'i', data: iv.map(r => r[3]), itemStyle: { color: '#8b7bff' } }, { name: '累計', type: 'line', yAxisIndex: 1, data: iv.map(r => r[4]), showSymbol: false, lineStyle: { color: '#ff8fab', width: 2 } }] });
    if (mg.length >= CHIP_MIN) A.chart('marginChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 60, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: mg.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(5) } }, yAxis: [{ ...A.axisStyle, scale: true }, { ...A.axisStyle, scale: true, splitLine: { show: false } }],
      series: [{ name: '融資餘額', type: 'line', data: mg.map(r => r[1]), showSymbol: false, areaStyle: { color: 'rgba(255,77,109,.12)' }, lineStyle: { color: '#ff4d6d', width: 2 } }, { name: '融券餘額', type: 'line', yAxisIndex: 1, data: mg.map(r => r[2]), showSymbol: false, lineStyle: { color: '#2ee59d', width: 1.5 } }] });
    if (ho.length >= CHIP_MIN) {
      /* ★ 2026-09-25（審查 R5）：集保是**每週**一筆，X 軸以前切 `YY-MM`，同一個月的三週全部寫「26-09」；
         改成 `MM-DD`。股東人數 Y 軸以前用「萬」取整數，21.3 萬～21.4 萬之間九個刻度全部印「21 萬」；
         改成依刻度間距決定小數位（間距 ≥ 1 萬印整數萬、再小就多一兩位），還小於 100 人就直接印人數。*/
      const hoDay = (v) => String(v).slice(5, 10);
      const cnts = ho.map(r => r[4]).filter(v => v != null);
      const span = cnts.length ? Math.max(...cnts) - Math.min(...cnts) : 0;
      const hoCnt = (v) => {
        if (Math.abs(v) < 1e4 || span < 400) return Math.round(v).toLocaleString('en-US');
        const dp = span >= 4e4 ? 0 : span >= 4e3 ? 1 : 2;
        return (v / 1e4).toFixed(dp) + ' 萬';
      };
      A.chart('holderChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 50, right: 20, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: ho.map(r => r[0]), axisLabel: { color: A.CH.ink3, fontFamily: A.NUM_FONT, formatter: hoDay } }, yAxis: { ...A.axisStyle, scale: true, axisLabel: { color: A.CH.ink3, fontFamily: A.NUM_FONT, formatter: '{value}%' } },
        series: [{ name: '千張大戶', type: 'line', data: ho.map(r => r[1]), showSymbol: false, lineStyle: { color: '#ff4d6d', width: 2 } }, { name: '400–1000 張', type: 'line', data: ho.map(r => r[2]), showSymbol: false, lineStyle: { color: '#ffb454' } }, { name: '散戶 ≤10 張', type: 'line', data: ho.map(r => r[3]), showSymbol: false, lineStyle: { color: '#2ee59d' } }] });
      A.chart('holderCount', { tooltip: { ...A.tip, trigger: 'axis', valueFormatter: (v) => v != null ? Math.round(v).toLocaleString('en-US') + ' 人' : '—' }, grid: { left: 74, right: 20, top: 16, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: ho.map(r => r[0]), axisLabel: { color: A.CH.ink3, fontFamily: A.NUM_FONT, formatter: hoDay } }, yAxis: { ...A.axisStyle, scale: true, minInterval: 1, axisLabel: { color: A.CH.ink3, fontFamily: A.NUM_FONT, formatter: hoCnt } }, series: [{ name: '股東人數', type: 'line', data: ho.map(r => r[4]), showSymbol: false, areaStyle: { color: 'rgba(62,224,255,.12)' }, lineStyle: { color: '#3ee0ff', width: 2 } }] });
    }
  }
  function tabBasics(pg, el) {
    const b = pg.basics || {}; const f = pg.fundamental || {};
    const indLink = b.industry ? (A.L.gname['ind_' + b.industry] ? A.L.group('ind_' + b.industry, b.industry) : A.fmt.esc(b.industry)) : null;
    const rows = [['公司全名', b.full_name], ['市場', b.market], ['產業別', indLink, true], ['上市日', b.listed_date], ['股本', b.capital_billion != null ? b.capital_billion + ' 億' : null], ['董事長', b.chairman], ['網站', b.website ? `<a href="${A.fmt.esc(b.website)}" target="_blank" rel="noopener">${A.fmt.esc(b.website)}</a>` : null, true], ['市值', f.market_cap != null ? A.fmt.yi(f.market_cap) : null], ['股價淨值比', f.pb != null ? A.fmt.n(f.pb) : null], ['股價營收比', f.ps != null ? A.fmt.n(f.ps) : null], ['所屬族群', (pg.meta.groups || []).length ? `<span class="tagrow">${(pg.meta.groups || []).map(gn => A.L.groupByName(gn)).join('')}</span>` : null, true], ['題材', A.L.themesOf(pg.meta.code) ? `<span class="tagrow">${A.L.themesOf(pg.meta.code)}</span>` : null, true]];
    el.innerHTML = `<div class="card"><h3>基本資料</h3><dl class="kv" style="margin-top:10px">${rows.map(r => `<dt>${r[0]}</dt><dd>${r[1] != null && r[1] !== '' ? (r[2] ? r[1] : A.fmt.esc(r[1])) : '—'}</dd>`).join('')}</dl></div>
      <div class="card" style="margin-top:var(--gap-card)"><div class="row spread">
        <h3>1–12 月平均漲幅 <small id="msSub" data-readout></small> ${hq('ms', '1–12 月平均漲幅')}</h3>
        <div class="row" style="gap:10px;align-items:center">
          <div class="seg" id="msYears"><button data-v="1">1 年</button><button data-v="3">3 年</button><button data-v="5" class="on">5 年</button><button data-v="0">全部</button></div>
          <label class="opabox">自填 <input id="msCustom" type="number" min="1" max="15" step="1" style="width:56px" placeholder="年"></label>
        </div></div>
        <div class="howtxt" id="how-ms" hidden>${A.howHTML('這張圖回答：這一檔哪幾個月歷史上容易漲。', [
          '柱高＝那個月的平均漲幅',
          '柱上 x/y＝上漲年數／取樣年數',
          '只看平均會被一次暴漲暴跌帶偏',
          '樣本少於 3 年的月份參考就好',
          '右上切 1／3／5 年、全部或自填年數',
        ])}</div>
        <div id="msChart" class="chart" style="min-height:320px"></div>
        <div class="note" id="msNote" data-readout></div></div>`;
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
      el.innerHTML = '<div class="empty" style="height:100%">這一檔的歷史價量還不夠算月季節性</div>';
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
      n = +b.dataset.v; mark(); $('#msCustom').value = '';
      try { localStorage.setItem('tw.ms.years', n); } catch (e) { /* 忽略 */ }
      paint();
    });
    const cu = $('#msCustom');
    if (cu) cu.oninput = () => {
      const v = Math.max(1, Math.min(15, +cu.value || 0));
      if (!cu.value) return;
      n = v; $$('#msYears button').forEach(b => b.classList.remove('on'));
      try { localStorage.setItem('tw.ms.years', n); } catch (e) { /* 忽略 */ }
      paint();
    };
    mark();
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
  function tabNews(pg, el) {
    // bv（券商觀點）只負責交給積木 `broker.views`（site/blocks/broker_views.js），這裡不拆它的欄位
    const news = newsAbout(pg.news, pg.meta.code, pg.meta.name), bv = pg.broker_views || [], mn = pg.material_news || [];
    /* ★ 2026-09-19：重大訊息擺在最上面，而且跟「新聞」分開一張卡。
       兩者的可信度完全不同 —— 新聞是媒體寫的，重大訊息是**公司自己公告的**，
       減資、解散、訴訟、重大處分、財報更正都在這裡。
       M4 事件面要否決一筆進場，靠的是公告不是報導，混在一起會讓那個判斷失去意義。
       來源一定要寫出來，而且要能點回公開資訊觀測站看全文（我們只存前 800 字）。 */
    const mnHtml = mn.length
      ? mn.map(m => `<details class="ev" style="padding-left:0;padding-right:0">
          <summary style="cursor:pointer"><b>${A.fmt.esc(m.subject || '')}</b>
            <div class="m"><span class="mono">${A.fmt.esc(m.date || '')}${m.time ? ' ' + A.fmt.esc(m.time) : ''}</span>
              ${m.clause ? `<span class="cat">${A.fmt.esc(m.clause)}</span>` : ''}
              ${m.occurred && m.occurred !== m.date ? `<span>事實發生日 ${A.fmt.esc(m.occurred)}</span>` : ''}</div>
          </summary>
          <div class="note" style="white-space:pre-wrap;margin-top:6px">${A.fmt.esc(m.detail || '')}</div>
        </details>`).join('')
      : '<div class="empty">近期沒有這檔的重大訊息公告</div>';
    el.innerHTML = `<div class="card" style="margin-bottom:16px"><div class="row spread">
        <h3>重大訊息 ${hq('skmops', '重大訊息')}</h3>
        <a class="pill" href="https://mops.twse.com.tw/mops/web/t05st01" target="_blank" rel="noopener">公開資訊觀測站 ↗</a></div>
      ${hbox('skmops', ['公司自己在公開資訊觀測站發的公告', '不是媒體報導', '點一則展開摘要', '只存摘要前 800 字，全文請到觀測站'])}
      ${mnHtml}</div>
      <div class="grid g2"><div class="card" id="stockNews"><h3>相關新聞 ${hq('sknews', '相關新聞')}</h3>${hbox('sknews', [`只列標題或內文提到${A.fmt.esc(pg.meta.name || '')}的`, '點標題開原文（新分頁）'])}${news.length ? news.map(n => `<div class="ev" style="padding-left:0;padding-right:0"><a href="${A.fmt.esc(n.url)}" target="_blank" rel="noopener">${A.fmt.esc(n.title)}</a><div class="m"><span class="mono">${n.date}</span><span class="cat">${A.fmt.esc(n.category || '')}</span><span>${A.fmt.esc(n.source || '')}</span></div></div>`).join('') : '<div class="empty isnews">近期無相關新聞</div>'}</div>
      ${window.BrokerViews ? window.BrokerViews.view(bv, 'card', A.fmt) : ''}</div>`;
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
    drawKey: kchart && kchart.draw ? kchart.draw.key : null,
    shapes: kchart && kchart.draw ? kchart.draw.shapes.length : -1,
    hasChart: !!kchart, w: drawW, fill: drawFill,
    // 驗收用：圖上最後一根的日期與收盤、各面板目前高度
    lastBar: kchart && kchart.bars && kchart.bars.length ? String(kchart.bars[kchart.bars.length - 1][0]) : null,
    lastClose: kchart && kchart.bars && kchart.bars.length ? kchart.bars[kchart.bars.length - 1][4] : null,
    paneH: kchart && kchart.paneHeights ? kchart.paneHeights() : null,
    // 驗收用：目前算出幾組背離
    div: kchart && kchart.divergences ? { top: kchart.divergences.top.length, bottom: kchart.divergences.bottom.length } : null,
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
    zoneLabels: kchart && kchart.zones ? (kchart.zones.placed || []) : [],
    zoneSkipped: kchart && kchart.zones ? (kchart.zones.skipped || 0) : 0,
    markers: kchart && kchart.markerList ? kchart.markerList.map(m => ({ time: String(m.time), i: m.i, pos: m.position, text: m.text })) : [],
    markerNear: kchart && kchart.chart ? Math.max(2, Math.min(12, Math.ceil(60 / (kchart.chart.timeScale().options().barSpacing || 7)))) : null,
    divLabels: kchart && kchart.divPrice ? (kchart.divPrice.lastLabels || []) : [],
    legendRect: kchart && kchart.legendRect ? kchart.legendRect() : null }) };
})();
