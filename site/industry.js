/* 產業與個股（合併頁）：產業地圖 → 單一產業鏈（產品剖析圖 + 分層關聯圖 + 成分股）→ 個股頁。
   個股頁上方永遠帶著它所屬的產業鏈，點任何股票上方同步更新。 */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  let A;                                   // window.App（app.js 提供）
  const state = { level: 0, chain: null, group: null, code: null, tf: '1d', mtfMode: false, cfg: null, tab: 'overview' };
  const CHAIN_NAME = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子', traditional: '傳產', infrastructure: '基礎建設', _other: '其他族群', industry: '產業別' };
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

  // ================================================================ 路由
  async function route(head, rest) {
    A = window.App;
    dispose3D();   // 換頁一定要收掉 WebGL context（瀏覽器最多只給十幾個，不收會整個掛掉）
    if (head !== 'stock') stopLive();   // 離開個股頁就不要再每 5 秒抓報價了
    const [im, sc, gd] = await Promise.all([A.load('industry_map'), A.load('supply_chain'), A.load('groups_detail')]);
    if (head === 'stock') { state.level = 2; state.code = rest[0]; await renderStock(rest[0], im, sc, gd); return; }
    if (rest[0] === 'group' && rest[1]) { state.group = rest[1]; state.chain = chainOfGroup(im, rest[1]); state.level = 1; renderChain(im, sc, gd); return; }
    if (rest[0]) { state.chain = rest[0]; state.group = null; state.level = 1; renderChain(im, sc, gd, { seg: rest[1] || null }); return; }
    state.level = 0; state.chain = null; state.group = null; renderMap(im);
  }
  function chainOfGroup(im, gid) {
    if (!im) return null;
    if (gid.startsWith('ind_')) return 'industry';
    for (const c of im.chains) if (c.groups.some(g => g.id === gid)) return c.id;
    return null;
  }
  function crumbs(items) { $('#indCrumbs').innerHTML = items.map((it, i) => it.href ? `<a onclick="location.hash='${it.href}'">${it.label}</a>${i < items.length - 1 ? '›' : ''}` : `<span class="cur">${it.label}</span>`).join(' '); }
  function show(map, chain, stock) { $('#indMap').style.display = map ? '' : 'none'; $('#indChain').style.display = chain ? '' : 'none'; $('#stockPage').style.display = stock ? '' : 'none'; }

  // ================================================================ Level 0：產業地圖
  function renderMap(im) {
    show(true, false, false); crumbs([{ label: '產業地圖' }]);
    if (!im || !im.chains) { $('#indMap').innerHTML = '<div class="empty">尚無產業資料</div>'; return; }
    const el = $('#indMap');
    el.innerHTML = `<div class="card"><h3>整個台股一次看 <small>方塊＝族群成交值，顏色＝今日漲跌（紅漲綠跌）；點產業鏈進入單一鏈，點族群直接看成分股</small></h3><div class="zwrap" id="indTreeWrap"><div id="indTree" class="chart" style="min-height:520px"></div></div></div>
      <div class="grid g2" style="margin-top:16px"><div class="card"><h3>產業鏈總覽 <small>本益比為族群中位數（同族群才比）</small></h3><div class="tiles" id="chainTiles"></div></div>
      <div class="card"><h3>法定產業別 <small>沒被歸入題材族群的公司依證交所產業別歸戶</small></h3><div class="tiles" id="indTiles"></div></div></div>`;
    const data = im.chains.map(c => ({ name: c.name, cid: c.id, children: c.groups.map(g => ({ name: g.name, value: g.turnover || 1, gid: g.id, chg: g.chg_pct, share: g.turnover_share, pe: g.valuation && g.valuation.median, n: g.n, itemStyle: { color: A.chgColor(g.chg_pct, 3) } })) }));
    const SK = A.treeSkin();
    const c = A.chart('indTree', { tooltip: { ...A.tip, formatter: p => p.data.gid ? `<b>${p.name}</b><br>成交值 ${A.fmt.yi(p.value)}（${A.fmt.n(p.data.share, 1)}%）· ${p.data.n} 檔<br>漲跌 <span style="color:${A.upDown(p.data.chg)}">${A.fmt.pct(p.data.chg)}</span> · 本益比中位 ${p.data.pe != null ? A.fmt.n(p.data.pe, 1) : '—'}` : `<b>${p.name}</b>（點進入產業鏈）` },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, top: 0, left: 0, width: '100%', height: '100%', leafDepth: 2, visibleMin: 900,
        label: { formatter: p => `${p.name}\n${A.fmt.pct(p.data.chg)}`, fontSize: 13, ...SK.label },
        upperLabel: { show: true, height: 26, fontSize: 13, fontWeight: 700, ...SK.upper },
        itemStyle: { borderColor: SK.border, borderWidth: 2, gapWidth: 2 }, levels: [{ itemStyle: { borderWidth: 4, gapWidth: 4 }, upperLabel: { show: true } }, { itemStyle: { gapWidth: 1 } }], data }] });
    A.wheelZoom($('#indTreeWrap'), { onZoom: () => { const i = window.echarts && echarts.getInstanceByDom($('#indTree')); if (i) i.resize(); } });
    if (c) c.off('click').on('click', p => { if (p.data.gid) location.hash = '#industry/group/' + p.data.gid; else if (p.data.cid) location.hash = '#industry/' + p.data.cid; else if (p.treePathInfo && p.treePathInfo[1]) { const cid = (im.chains.find(x => x.name === p.treePathInfo[1].name) || {}).id; if (cid) location.hash = '#industry/' + cid; } });
    $('#chainTiles').innerHTML = im.chains.map(ch => { const pes = ch.groups.map(g => g.valuation && g.valuation.median).filter(Boolean); const chg = wavg(ch.groups); return `<div class="tile" onclick="location.hash='#industry/${ch.id}'"><div class="t">${ch.name}</div><div class="m">${ch.groups.length} 個族群 · ${ch.groups.reduce((s, g) => s + (g.n || 0), 0)} 檔</div><div class="v"><span class="${A.fmt.cls(chg)}">${A.fmt.pct(chg)}</span> <small style="font-size:12px;color:var(--ink-3)">PE 中位 ${pes.length ? A.fmt.n(median(pes), 1) : '—'}</small></div></div>`; }).join('');
    /* ★ 2026-09-19：拿掉 slice(0, 18)。資料裡有 35 個法定產業別，這裡只列前 18 個，
       剩下 17 個（造紙、農業科技、玻璃陶瓷…）在產業地圖上**點不到**，
       只能從 #industry/industry 那一頁進去。
       今天剛修好中文 id 的族群頁（hash 沒解碼那條），這 17 個才真的有地方可去。 */
    $('#indTiles').innerHTML = im.industries.map(g => `<div class="tile" onclick="location.hash='#industry/group/${g.id}'"><div class="t">${g.name}</div><div class="m">${g.n} 檔 · 佔比 ${A.fmt.n(g.turnover_share, 1)}%</div><div class="v ${A.fmt.cls(g.chg_pct)}">${A.fmt.pct(g.chg_pct)}</div></div>`).join('');
  }
  const median = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : null; };
  const wavg = (gs) => { let w = 0, s = 0; gs.forEach(g => { if (g.chg_pct != null && g.turnover) { w += g.turnover; s += g.chg_pct * g.turnover; } }); return w ? s / w : null; };

  // ================================================================ Level 1：單一產業鏈
  function chainData(im, cid) {
    if (!im) return null;
    if (cid === 'industry') return { id: 'industry', name: '產業別', groups: im.industries };
    return im.chains.find(c => c.id === cid) || null;
  }
  const HAS_DIAGRAM = (cid) => ['semiconductor', 'ai_server'].includes(cid);
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
    const hasDiagram = HAS_DIAGRAM(ch.id);
    const groups = state.group && ch.id === 'industry' ? ch.groups.filter(g => g.id === state.group) : ch.groups;
    const chg = wavg(groups); const pes = groups.map(g => g.valuation && g.valuation.median).filter(Boolean);
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
    const swTabs = (im.chains || []).map(c => ({ id: c.id, name: c.name, n: c.groups.reduce((s, g) => s + (g.n || 0), 0) }))
      .concat([{ id: 'industry', name: '法定產業別', n: (im.industries || []).reduce((s, g) => s + (g.n || 0), 0) }]);
    el.innerHTML = `
      <div class="card">
        <div class="chainsw" id="chainSwitch">${swTabs.map(t => `<button data-c="${t.id}" class="${t.id === ch.id ? 'on' : ''}"${HAS_DIAGRAM(t.id) ? ' data-dg="1"' : ''}>${A.fmt.esc(t.name)}<em>${t.n}</em></button>`).join('')}</div>
        <div class="row spread"><div><h2>${A.fmt.esc(ch.name)}${state.group && ch.id === 'industry' ? ' · ' + A.fmt.esc((groups[0] || {}).name) : ''}</h2>
          <div class="sub">${hasDiagram ? '剖析圖的零件、環節色標、關聯圖的公司、族群卡片都是同一套顏色：點任一個，其餘同色的一起亮，下方成分股同步篩選；點關聯圖的公司會在右側展開它的產業關係，不會跳走。' : (hasMap ? '環節色標、關聯圖的公司、族群卡片都是同一套顏色：點任一個，其餘同色的一起亮，下方成分股同步篩選；點關聯圖的公司會在右側展開它的產業關係，不會跳走。（這條鏈還沒有產品剖析圖）' : '點族群卡片篩選成分股；點股票進入個股頁。')}</div></div>
          <div class="row"><span class="pill">${groups.reduce((s, g) => s + (g.n || 0), 0)} 檔</span><span class="pill ${A.fmt.cls(chg)}">今日 ${A.fmt.pct(chg)}</span><span class="pill violet">本益比中位 ${pes.length ? A.fmt.n(median(pes), 1) : '—'}</span>${A.L.back()}</div></div>
        ${hasDiagram ? `<div style="margin-top:14px"><div class="row spread"><h4>產品剖析圖 <small class="muted">原創示意圖，非實物比例；每個零件對應一個供應鏈環節，點零件看供應商</small></h4><div class="row" style="gap:6px"><span class="pill" id="dg3d" style="cursor:pointer" hidden>3D 立體</span><span class="pill" id="dgDrag" style="cursor:pointer" hidden title="左鍵拖曳要轉動還是平移（右鍵一律平移）">拖曳：轉動</span><span class="pill" id="dgPal" style="cursor:pointer" hidden title="換一種配色：科技／柔和／沉穩">配色：科技</span><span class="pill" id="dgReset" style="cursor:pointer" hidden>重設視角</span><span class="pill" id="dgAnim" style="cursor:pointer">動畫：開</span></div></div><div id="prodDiagram" class="dgwrap">${window.Diagrams[ch.id]()}</div><div id="prod3d" class="dg3d" hidden></div><div class="note" id="dg3dNote" hidden></div></div>` : ''}
        ${segs.length ? `<div class="segchips" id="segChips">${segs.map(s => { const tw = twOf(sc, s.id), fo = foreignOf(sc, s.id); return `<span class="segchip ${tw.length ? '' : 'nomem'}" data-seg="${s.id}" style="--c:${segColor(s.id)}" title="${tw.length ? tw.length + ' 檔台股' : '台股沒有直接對應，看外商'}"><i></i>${A.fmt.esc(s.name)}<span class="n">${tw.length ? tw.length : (fo.length ? '外商 ' + fo.length : '—')}</span></span>`; }).join('')}</div><div id="segBox"></div>` : ''}
        ${hasMap ? `<div style="margin-top:14px"><h4>供應鏈關聯圖 <small class="muted">上游 → 下游；線越粗依存度越高；虛線＝委外、點虛線＝終端指定料號；灰線＝設備／材料；虛線框＝外商；「?」＝還沒建立上下游關聯。點公司看它的產業關係</small></h4><div class="chainrow"><div class="chainmap" id="chainMap"></div></div></div>` : ''}
        <div style="margin-top:14px"><h4>族群 <small class="muted">卡片顏色＝剖析圖零件與環節色；點卡片篩選成分股，點「族群頁」看該族群全部</small></h4><div class="row" id="groupCards" style="margin-top:8px;align-items:stretch"></div></div>
        ${otherChains.length ? `<div class="linkrow"><span class="muted">其他產業鏈</span>${otherChains.map(c => A.L.chain(c.id, c.name)).join('')}${A.L.chain('industry', '法定產業別')}</div>` : ''}
      </div>
      <div class="card" style="margin-top:16px"><div class="row spread"><h3 id="memberTitle">成分股</h3><div class="seg" id="mktSeg"><button data-v="ALL" class="on">全部</button><button data-v="TWSE">上市</button><button data-v="TPEX">上櫃</button></div></div>
        <div class="tw" style="margin-top:10px"><table id="memberTable"><thead></thead><tbody></tbody></table></div></div>`;
    // 族群卡片（顏色跟環節一致）
    const cardHtml = (g) => `<div class="tile colored ${state.group === g.id ? 'sel' : ''}" data-gid="${g.id}" style="min-width:180px;flex:1 1 200px;max-width:360px;--c:${A.L.gcolor[g.id] || '#8ea0c4'}"><div class="t">${A.fmt.esc(g.name)}</div><div class="m">${g.n} 檔 · 佔比 ${A.fmt.n(g.turnover_share, 1)}%${g.valuation && g.valuation.median ? ' · PE ' + A.fmt.n(g.valuation.median, 1) : ''}</div><div class="row spread" style="margin-top:4px"><div class="v ${A.fmt.cls(g.chg_pct)}" style="margin:0">${A.fmt.pct(g.chg_pct)}</div>${A.L.group(g.id, '族群頁 →', { dot: false, cls: 'sm' })}</div></div>`;
    $('#groupCards', el).innerHTML = groups.map(cardHtml).join('');
    let segFilter = opts.seg || null, mkt = 'ALL';
    const members = () => {
      let rows = []; groups.forEach(g => (g.members || []).forEach(m => rows.push({ ...m, group_name: g.name, gid: g.id })));
      if (state.group) rows = rows.filter(r => r.gid === state.group);
      if (segFilter && sc) { const codes = new Set(twOf(sc, segFilter).map(c => c.tw_code)); rows = rows.filter(r => codes.has(r.code)); }
      if (mkt !== 'ALL') rows = rows.filter(r => marketOf(r) === mkt);
      const seen = new Set(); return rows.filter(r => seen.has(r.code) ? false : (seen.add(r.code), true));
    };
    const COLS = [['code', '代號', r => `<span class="mono">${r.code}</span>`, 'l'], ['name', '簡稱', r => A.L.stock(r.code, r.name), 'l'], ['group_name', '族群', r => A.L.group(r.gid, r.group_name), 'l'], ['close', '收盤', r => `<span class="num" data-live="close" data-lc="${r.code}">${A.fmt.n(r.close)}</span>`], ['chg_pct', '漲跌', r => `<span class="num ${A.fmt.cls(r.chg_pct)}" data-live="chg" data-lc="${r.code}">${A.fmt.pct(r.chg_pct, 2)}</span>`], ['turnover', '成交值', r => `<span class="num">${A.fmt.yi(r.turnover)}</span>`], ['pe', '本益比', r => `<span class="num">${r.pe ? A.fmt.n(r.pe, 1) : '—'}</span>`], ['pe_percentile', '同業分位', r => `<span class="num">${r.pe_percentile != null ? A.fmt.n(r.pe_percentile, 0) + '%' : '—'}</span>`], ['momentum', '營運動能', r => `<span class="num">${r.momentum != null ? A.fmt.n(r.momentum, 0) : '—'}</span>`], ['foreign', '外資', r => `<span class="num ${A.fmt.cls(r.foreign)}">${r.foreign != null ? A.fmt.lot(r.foreign / 1000) : '—'}</span>`], ['trust', '投信', r => `<span class="num ${A.fmt.cls(r.trust)}">${r.trust != null ? A.fmt.lot(r.trust / 1000) : '—'}</span>`], ['grade', '技術判定', r => r.verdict ? `<span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' : ''}${r.verdict}</span>` : '<span class="muted">—</span>', 'l']];
    /* 成分股預設照漲幅排（Andy 2026-09-15：「族群 Default 排序適用漲幅」）。
       以前預設是成交值，結果打開族群頁看到的永遠是那幾檔權值股，
       今天真的在動的中小型股要自己按一次表頭才看得到。
       按過表頭就記住，下次打開沿用他自己選的那一欄。 */
    const SORT_KEY = 'tw.memberSort';
    let sort = { key: 'chg_pct', dir: -1 };
    try {
      const s = JSON.parse(localStorage.getItem(SORT_KEY) || 'null');
      if (s && s.key) sort = { key: s.key, dir: s.dir === 1 ? 1 : -1 };
    } catch (e) { /* 忽略 */ }
    const renderMembers = () => {
      // 先把即時值疊回去，排的才是使用者眼睛看到的那個數字（見 app.js 的 liveMerge）
      let rows = A.liveMerge(members()); rows.sort((a, b) => { const x = a[sort.key], y = b[sort.key]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * sort.dir; });
      const segTw = segFilter ? twOf(sc, segFilter) : [];
      $('#memberTitle', el).innerHTML = `成分股 <small>${rows.length} 檔${segFilter ? ' · 環節：<span style="color:' + segColor(segFilter) + '">' + A.fmt.esc(segName(sc, segFilter)) + '</span>' : ''}${state.group ? ' · ' + A.fmt.esc((groups.find(g => g.id === state.group) || {}).name || '') : ''}</small>`;
      $('#memberTable thead', el).innerHTML = '<tr>' + COLS.map(c => `<th class="${c[3] || ''}" data-k="${c[0]}">${c[1]}${sort.key === c[0] ? (sort.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>';
      $('#memberTable tbody', el).innerHTML = rows.slice(0, 200).map(r => `<tr data-code="${r.code}">` + COLS.map(c => `<td class="${c[3] || ''}">${c[2](r)}</td>`).join('') + '</tr>').join('')
        || `<tr><td colspan="12" class="l muted">${segFilter ? (segTw.length ? '這個環節的台股不在本鏈成分股裡：' + segTw.map(c => A.L.stock(c.tw_code, c.name)).join('　') : '這個環節目前沒有台股直接對應（' + foreignOf(sc, segFilter).map(c => c.name).join('、') + '），可看上方環節說明裡的相關族群') : '沒有符合的股票'}</td></tr>`;
      $$('#memberTable th', el).forEach(th => th.onclick = () => {
        sort = { key: th.dataset.k, dir: sort.key === th.dataset.k ? -sort.dir : -1 };
        try { localStorage.setItem(SORT_KEY, JSON.stringify(sort)); } catch (e) { /* 忽略 */ }
        renderMembers();
      });
      $$('#memberTable tbody tr', el).forEach(tr => tr.onclick = () => { if (tr.dataset.code) A.goStock(tr.dataset.code); });
      // 即時層更新之後重排一次 —— 只有正照著即時欄（收盤／漲跌）排序時才有意義
      A.onLive($('#memberTable', el), () => { if (A.LIVE_KEYS.includes(sort.key)) renderMembers(); });
    };
    /* 點剖析圖上的零件只做「亮起來 + 在原地說明這個環節」，
       不捲動、也不動下面的成分股表 —— Andy：「當我點擊圖片時，不用馬上切換到下方股票」。
       要真的篩成分股，用下面的環節晶片、族群卡片，或說明框裡那顆按鈕。 */
    let segHi = null;
    const syncHighlight = (opt) => {
      const o = opt || {};
      const shown = segFilter || segHi;
      const segsOn = shown ? [shown] : (state.group ? (A.L.gsegs[state.group] || []) : []);
      const color = shown ? segColor(shown) : (state.group ? A.L.gcolor[state.group] : null);
      highlightSegments(el, segsOn, color);
      if (segFilter && !o.quiet) scrollChainTo(el, segFilter);
      $$('#groupCards .tile', el).forEach(t => t.classList.toggle('sel', !!state.group && t.dataset.gid === state.group || (!!segFilter && (A.L.sgroups[segFilter] || []).includes(t.dataset.gid))));
      $$('#segChips .segchip', el).forEach(c => c.classList.toggle('sel', segsOn.includes(c.dataset.seg)));
      renderSegBox($('#segBox', el), sc, shown, ch, { filtered: !!segFilter, onFilter: () => {
        segFilter = shown; segHi = null; state.group = null; syncHighlight();
      } });
      if (!o.quiet) renderMembers();
    };
    $$('#groupCards .tile', el).forEach(t => t.onclick = (e) => { if (e.target.closest('a.lk')) return; state.group = state.group === t.dataset.gid ? null : t.dataset.gid; segFilter = null; segHi = null; syncHighlight(); });
    $$('#segChips .segchip', el).forEach(c => c.onclick = () => { segFilter = segFilter === c.dataset.seg ? null : c.dataset.seg; segHi = null; state.group = null; syncHighlight(); });
    $$('#mktSeg button', el).forEach(b => b.onclick = () => { $$('#mktSeg button', el).forEach(x => x.classList.toggle('on', x === b)); mkt = b.dataset.v; renderMembers(); });
    // E5：上方切換列 —— 按了直接換一條鏈，不用退回產業地圖（按自己就捲回頁首，不重畫）
    $$('#chainSwitch button', el).forEach(b => b.onclick = () => {
      if (b.dataset.c === ch.id) { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
      location.hash = '#industry/' + b.dataset.c;
    });
    // 關聯圖只要這條鏈有環節就畫，不管有沒有剖析圖（見上面 hasMap 的註解）
    if (hasMap) {
      drawChainMap($('#chainMap', el), sc, ch.id, im, { onSegment: (seg) => { segHi = segHi === seg ? null : seg; segFilter = null; syncHighlight({ quiet: true }); } });
    }
    if (hasDiagram && sc) {
      paintDiagram($('#prodDiagram', el));
      // 剖析圖不加縮放：Andy 明講「產業與個股 剖析圖不用新增縮放功能」（本來就可以左右滑）
      wireDiagram(el, (seg) => { segHi = segHi === seg ? null : seg; segFilter = null; syncHighlight({ quiet: true }); });
      /* E4：動畫鈕現在同時管平面圖與 3D（Andy 2026-09-18：「3D 可切動態／靜止」）。
         以前它只把 SVG 加上 .noanim，切到 3D 之後這顆鈕等於是壞的。
         3D 的「動態」＝場景緩慢自轉 ＋ 風扇轉 ＋ 指示燈呼吸；「靜止」＝完全不自己動。*/
      const animBtn = $('#dgAnim', el);
      const setAnimAll = (on) => {
        $('#prodDiagram', el).classList.toggle('noanim', !on);
        if (animBtn) { animBtn.textContent = on ? '動畫：開' : '動畫：關'; animBtn.classList.toggle('cyan', on); }
        if (view3d && view3d.setAnim) view3d.setAnim(on);
        try { localStorage.setItem('tw.dganim', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
      };
      if (animBtn) animBtn.onclick = () => setAnimAll($('#prodDiagram', el).classList.contains('noanim'));
      setAnimAll(animPref());
      // wire3D 是模組層級的函式，看不到這裡的 segHi／segFilter／syncHighlight，
      // 所以把要用到的動作當參數傳進去（之前直接寫在函式裡會噴 syncHighlight is not defined）。
      wire3D(el, ch.id, {
        onSeg: (seg) => { segHi = segHi === seg ? null : seg; segFilter = null; syncHighlight({ quiet: true }); },
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
    syncHighlight();
  }
  // 環節說明盒：這個環節的台股（可點）、外商、相關族群（可點）
  // 市場別一律以全市場索引（stocks.json）為準：groups_detail 的 market 欄位常常是空的
  const marketOf = (r) => String(A.L.cmarket[r.code] || r.market || '').toUpperCase() || null;

  function renderSegBox(box, sc, seg, ch, opt) {
    if (!box) return;
    if (!seg || !sc) { box.innerHTML = ''; return; }
    const o = opt || {};
    const tw = twOf(sc, seg), fo = foreignOf(sc, seg), gids = A.L.sgroups[seg] || [];
    const s = sc.segments.find(x => x.id === seg) || {};
    box.innerHTML = `<div class="segbox" style="--c:${segColor(seg)}"><div class="row spread">
        <div><b class="t">${A.fmt.esc(s.name || seg)}</b> <span class="muted">${s.desc ? A.fmt.esc(s.desc) : ''}</span></div>
        <button class="btn small" id="segOnly">${o.filtered ? '已套用到下方成分股' : '只看這個環節的成分股 →'}</button></div>
      <div class="row"><span class="muted">台股</span>${tw.length ? tw.map(c => A.L.stock(c.tw_code, c.name)).join('') : '<span class="muted">沒有直接對應的台股</span>'}</div>
      ${fo.length ? `<div class="row"><span class="muted">外商</span>${fo.map(c => `<span class="pill" title="${A.fmt.esc((c.tech || []).join('、'))}">${A.fmt.esc(c.name)}</span>`).join('')}</div>` : ''}
      ${gids.length ? `<div class="row"><span class="muted">相關族群</span>${gids.map(g => A.L.group(g)).join('')}</div>` : ''}
      ${crossHtml(sc, seg, ch)}</div>`;
    const btn = $('#segOnly', box);
    if (btn) { btn.disabled = !!o.filtered; if (o.onFilter && !o.filtered) btn.onclick = o.onFilter; }
    paintCross(box, seg);
  }

  /* ---------------------------------------------------------------- E6：跨產業鏈的環節
     Andy 2026-09-18：「ABF 這種跨類別環節要同時出現兩張架構圖與兩邊內容」。
     ABF 載板／封測／晶圓代工／先進封裝／HBM 這五個環節同時掛在半導體與 AI 伺服器兩條鏈上
     （chainSegments() 的那兩條 include 規則），但以前不管從哪條鏈點進去，
     看到的都只有「當下這條鏈」的畫面 —— 另一半的上下游關係整個看不到。
     現在跨鏈的環節會多出一塊：**兩條鏈各一張剖析圖縮圖**（這個環節在各自的圖上亮起來）＋
     各自的上下游鄰居、各自的相關族群，以及直接跳過去的入口。*/
  const DG_CHAINS = ['semiconductor', 'ai_server'];       // 目前有剖析圖的兩條鏈
  function chainsOfSeg(sc, seg) {
    if (!sc || !seg) return [];
    return DG_CHAINS.filter(cid => chainSegments(sc, cid).some(x => x.id === seg));
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
    const k = Math.min(1, box / r.width);
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
      const dg = window.Diagrams && window.Diagrams[cid] ? uniqIds(window.Diagrams[cid](), '__x' + cid) : '';
      return `<div class="xchain${cid === cur ? ' cur' : ''}" data-c="${cid}">
        <div class="row spread"><b>${A.fmt.esc(nm)}${cid === cur ? ' <span class="muted">（現在這條）</span>' : ''}</b>
          ${cid === cur ? '' : `<button class="btn small xgo" data-c="${cid}">切到這條鏈看 →</button>`}</div>
        <div class="dgwrap noanim xmini"><div class="xinner">${dg}</div></div>
        <div class="xrow"><span class="muted">上游</span>${up.length ? up.map(t => `<span class="pill">${A.fmt.esc(t)}</span>`).join('') : '<span class="muted">這條鏈的最上游</span>'}</div>
        <div class="xrow"><span class="muted">下游</span>${dn.length ? dn.map(t => `<span class="pill">${A.fmt.esc(t)}</span>`).join('') : '<span class="muted">這條鏈的最下游</span>'}</div>
        <div class="xrow"><span class="muted">族群</span>${gs.length ? gs.map(g => A.L.group(g)).join('') : '<span class="muted">這條鏈沒有掛族群</span>'}</div></div>`;
    }).join('');
    return `<div class="xchains" id="xChains"><div class="xhd">這個環節跨 ${cids.length} 條產業鏈：
      ${cids.map(c => A.fmt.esc(A.L.chains[c] || CHAIN_NAME[c] || c)).join('、')}　<span class="muted">兩張架構圖裡它的位置與上下游都不一樣</span></div>${panels}</div>`;
  }
  // 縮圖插進 DOM 之後才上色：跟大圖同一套環節色，這個環節亮起來、其餘壓暗
  function paintCross(box, seg) {
    const wrap = $('#xChains', box); if (!wrap) return;
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
  // 讓剖析圖每個零件帶上環節色（CSS 用 var(--c)）
  function paintDiagram(root) {
    if (!root) return;
    $$('[data-seg]', root).forEach(n => { n.style.setProperty('--c', segColor(n.dataset.seg)); n.style.cursor = 'pointer'; });
    $$('[data-chain]', root).forEach(n => { n.style.cursor = 'pointer'; n.onclick = () => { location.hash = '#industry/' + n.dataset.chain; }; });
  }
  // 點下方環節後，右側供應鏈關聯圖自動捲到那一欄（不然要自己拉很久才找得到）
  function scrollChainTo(root, seg) {
    const map = $('#chainMap', root); if (!map || !seg) return;
    const t = $(`.chainmap .segtitle[data-seg="${seg}"]`, root) || $(`.chainmap .co[data-segment="${seg}"]`, root);
    if (!t || !t.getBBox) return;
    const svg = map.querySelector('svg'); if (!svg) return;
    const vb = (svg.getAttribute('viewBox') || '').split(/\s+/).map(Number);
    const scale = vb.length === 4 && vb[2] ? (svg.clientWidth || map.clientWidth) / vb[2] : 1;
    const b = t.getBBox();
    map.scrollTo({ left: Math.max(0, b.x * scale - 40), top: Math.max(0, b.y * scale - 40), behavior: 'smooth' });
    // 關聯圖本身也要進到視野裡，不然捲對了位置使用者還是看不到
    if (map.scrollIntoView) map.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  function highlightSegments(root, segs, color) {
    const on = new Set(segs || []);
    if (view3d) view3d.highlight(on, color);       // 3D 場景與 SVG 用同一套高亮規則
    $$('#prodDiagram [data-seg]', root).forEach(n => { n.classList.toggle('sel', on.has(n.dataset.seg)); n.classList.toggle('dim', on.size > 0 && !on.has(n.dataset.seg)); if (color && on.has(n.dataset.seg)) n.style.setProperty('--c', color); else n.style.setProperty('--c', segColor(n.dataset.seg)); });
    $$('.chainmap .co', root).forEach(n => n.classList.toggle('dim', on.size > 0 && !on.has(n.dataset.segment)));
    $$('.chainmap .segtitle', root).forEach(n => n.classList.toggle('sel', on.has(n.dataset.seg)));
  }
  /* ---------------------------------------------------------------- 3D 剖析圖（Three.js）
     Andy 拍板「先試試看 three.js」。四條硬性驗收都在這裡兌現：
       可以轉、點零件會亮並帶出台股、標籤是 DOM、WebGL 不能用就退回 SVG。
     three.js 是動態載入的，只有真的按下 3D 才付那 670KB。*/
  let view3d = null;                 // 目前掛著的 3D 場景（沒有就是 null）
  // 動畫偏好（平面圖與 3D 共用同一個開關）；沒設定過就是開
  const animPref = () => { try { return localStorage.getItem('tw.dganim') !== '0'; } catch (e) { return true; } };

  function dispose3D() { if (view3d) { try { view3d.dispose(); } catch (e) { /* 忽略 */ } view3d = null; } }

  /* 圖九 2-2：記住使用者選的色票。讀不到（無痕、擋 localStorage）就回預設，不要讓整個 3D 掛掉。*/
  function palPref() {
    try { const v = localStorage.getItem('tw.dg3d.pal'); return ['tech', 'soft', 'calm'].includes(v) ? v : 'tech'; }
    catch (e) { return 'tech'; }
  }

  function wire3D(el, chainId, hooks) {
    const hk = hooks || {};
    const onSeg = hk.onSeg || (() => { /* 沒接就不做事 */ });
    const sync = hk.sync || (() => { /* 沒接就不做事 */ });
    const btn = $('#dg3d', el), rst = $('#dgReset', el), note = $('#dg3dNote', el);
    const drg = $('#dgDrag', el), plb = $('#dgPal', el);
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
    const setMode = async (on) => {
      try { localStorage.setItem('tw.dg3d', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
      btn.classList.toggle('cyan', on);
      btn.textContent = on ? '3D 立體 ✓' : '3D 立體';
      rst.hidden = !on;
      if (drg) drg.hidden = !on;
      if (plb) plb.hidden = !on;
      svg.hidden = on; host.hidden = !on;
      if (!on) { dispose3D(); note.hidden = true; sync(); return; }
      note.hidden = false;
      note.textContent = '載入 3D 中…';
      dispose3D();
      host.innerHTML = '';
      let v = null;
      try {
        v = await R.mount(host, chainId, {
          color: segColor,
          onSeg: (seg) => onSeg(seg),
          anim: animPref(),          // E4：一掛上去就照使用者目前的動畫偏好，不要先動起來再被關掉
          members: hk.members || null,   // 圖九 2-3：文字框底下那排可點的台股晶片
          onStock: hk.onStock || null,
          pal: palPref(),                // 圖九 2-2：三種配色，記在 localStorage
        });
      } catch (err) {
        // 起不來就要講出來，不能停在「載入 3D 中…」讓人以為當掉了
        note.textContent = '3D 起不來（' + (err && err.message ? err.message : err) + '），已退回平面剖析圖。';
        svg.hidden = false; host.hidden = true; rst.hidden = true; return;
      }
      if (!v) { note.textContent = '3D 起不來，已退回平面剖析圖。'; svg.hidden = false; host.hidden = true; rst.hidden = true; return; }
      view3d = v;
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
      /* 圖九 2-2（規格書 docs/diagram_specs/dg3d_standard.md）：三種配色。
         一顆鈕輪流切 科技 → 柔和 → 沉穩。「柔和」是淺底、零件不發光，
         Andy 要拿去給客戶看的時候印得出來。*/
      if (plb && v.setPal) {
        const paintPal = () => { plb.textContent = '配色：' + v.palName(v.pal()); plb.classList.toggle('cyan', v.pal() !== 'tech'); };
        paintPal();
        plb.onclick = () => {
          if (!view3d || !view3d.setPal) return;
          const list = view3d.pals(), next = list[(list.indexOf(view3d.pal()) + 1) % list.length];
          view3d.setPal(next);
          try { localStorage.setItem('tw.dg3d.pal', next); } catch (e) { /* 忽略 */ }
          paintPal();
        };
      }
      note.textContent = `${v.sub}　·　拖曳轉視角（可轉到底下看背面）、右鍵或切到「平移」可抓著移動、滾輪拉近拉遠、點零件看供應商`;
      sync();
    };
    btn.onclick = () => setMode(host.hidden);
    rst.onclick = () => { if (view3d) view3d.reset(); };
    let want = false;
    try { want = localStorage.getItem('tw.dg3d') === '1'; } catch (e) { /* 忽略 */ }
    setMode(want);
  }

  function wireDiagram(root, onSeg) { $$('#prodDiagram [data-seg]', root).forEach(n => { n.onclick = (e) => { e.stopPropagation(); onSeg(n.dataset.seg); }; }); }

  // ---------------------------------------------------------------- 分層關聯圖（SVG）
  function drawChainMap(host, sc, chainId, im, handlers) {
    if (!host) return;
    const segs = chainSegments(sc, chainId);
    const layers = [...new Set(segs.map(s => s.layer))].sort((a, b) => a - b);
    const cos = sc.companies.filter(c => segs.some(s => s.id === c.segment));
    const priceOf = {}; (im ? im.chains.flatMap(c => c.groups).concat(im.industries || []) : []).forEach(g => (g.members || []).forEach(m => { priceOf[m.code] = m; }));
    const colW = 178, cardH = 36, gapY = 8, padX = 14, padY = 36, colGap = 30;
    const bySeg = {}; cos.forEach(c => (bySeg[c.segment] = bySeg[c.segment] || []).push(c));
    const cols = layers.map(Lr => segs.filter(s => s.layer === Lr));
    let maxH = 0; const pos = {};
    /* 沒有台股的環節要顯示 note（見下面的 nodes 迴圈）。那幾行字**要先算進版面高度**，
       不然它會壓到下一個環節的標題列 —— 2026-09-19 實測到「先進封裝 CoWoS/SoIC」的說明
       整段蓋在「封測 / 測試」上面。*/
    /* 一行放幾個字：欄寬 178 − 左右留白 12 = 166px，說明字級 11px，
       中文大約 1 字 1 字寬 → 13 字是安全值。切 18 字會**超出欄寬**，
       整段跑到隔壁欄去壓到別人的卡片（2026-09-19 用 getBBox 量到的）。*/
    const NOTE_CPL = 13, NOTE_LH = 16, NOTE_MAX = 4;
    const noteWrap = (txt) => (String(txt || '').match(new RegExp(`.{1,${NOTE_CPL}}`, 'g')) || []);
    const noteLines = (sg, list) => (list.length ? 0 : Math.min(NOTE_MAX, noteWrap(sg.note || '台股無直接對應').length));
    cols.forEach((col, ci) => { let y = padY; col.forEach(s => { const list = bySeg[s.id] || []; pos[s.id] = { x: padX + ci * (colW + colGap), y, list }; y += 24 + list.length * (cardH + gapY) + noteLines(s, list) * NOTE_LH + 18; }); maxH = Math.max(maxH, y); });
    /* 右邊多留 24px：同一欄的兩張卡要從右緣繞一條 24px 的通道再回來，
       不留的話最後一欄那條線會被 viewBox 切掉。*/
    const W = padX * 2 + cols.length * (colW + colGap) - colGap + 24;
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
        nodes += `<g><title>${A.fmt.esc(msg)}</title>` + shown.map((w, i) =>
          `<text class="sub" x="${p.x + 6}" y="${p.y + 15 + i * NOTE_LH}" fill="#6f7ea3">${A.fmt.esc(w)}</text>`).join('') + '</g>';
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
    host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;min-width:${Math.min(W, 860)}px;max-width:${Math.round(W * 1.25)}px;display:block">${defs}${nodes}<g class="elayer">${edges}</g></svg>`;
    $$('.co', host).forEach(n => { n.onmouseenter = () => { $$('.edge', host).forEach(e => { const on = e.dataset.from === n.dataset.id || e.dataset.to === n.dataset.id; e.classList.toggle('hi', on); e.classList.toggle('dim', !on); }); }; n.onmouseleave = () => $$('.edge', host).forEach(e => e.classList.remove('hi', 'dim')); n.onclick = () => { const co = cos.find(c => c.id === n.dataset.id); if (!co) return;
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
      showCompany(co, sc, host); }; });
    $$('.segtitle', host).forEach(n => n.onclick = () => handlers.onSegment && handlers.onSegment(n.dataset.seg));
    if (state.code) { const sel = $(`.co[data-code="${state.code}"]`, host); if (sel && sel.scrollIntoView) setTimeout(() => sel.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' }), 50); }
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
    if (row) { box.classList.add('relside'); row.appendChild(box); }
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
      const sw = e.strength ? `<i class="dep" style="--n:${Math.min(5, e.strength)}" title="依存度 ${e.strength}/5"></i>` : '';
      const cf = e.confidence
        ? `<em class="cf cf-${e.confidence}">${CONF_TEXT[e.confidence] || e.confidence}</em>` : '';
      /* Andy 2026-09-19：「若是事實可以不上相關連結，若是你的推論也記得補上，並說明原因」。
         事實（官方揭露／媒體報導）→ 有 note 就平鋪直敘，不強迫附連結，他自己查得到。
         **推論** → 整塊換成橘色的「這是推論」，把「為什麼這樣推」與佐證連結攤開 ——
         那是我的主張，不是誰講過的事實，不攤開就會被當成事實。*/
      const guess = e.confidence === 'estimated';
      const why = guess
        ? `<div class="why"><b>這是推論，不是公司揭露</b>
             <div>${A.fmt.esc(e.note || '')}</div>
             ${srcLink(e.source_url)}</div>`
        : (e.note ? `<div class="nt">${A.fmt.esc(e.note)}</div>` : '');
      return `<li class="${guess ? 'guess' : ''}"><span class="rl">${A.fmt.esc(rt[dir])}</span>${nm}${sw}
        <div class="it">${A.fmt.esc(e.item || '')}${cf}</div>${why}</li>`;
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
        <b class="cf cf-verified">官方揭露</b> 與 <b class="cf cf-reported">媒體報導</b> 是**事實**，你自己也查得到，所以不另外附連結；<br>
        <b class="cf cf-estimated">產業推論</b> 是**我從兩段事實推出來的**，不是誰講過的 ——
        所以一定會寫「為什麼這樣推」和「缺的是什麼」，並附上支撐推論的那篇。看的時候要打折。</div>
    </div>`;
  }

  /* 「在圖上 highlight」：把這家公司的線亮起來、其餘變暗。
     按第二次還原 —— 不還原的話使用者會以為圖壞掉了。*/
  function wireRelBlock(box, sc, host) {
    const btn = box && box.querySelector('#relHi');
    if (!btn) return;
    const svgHost = host || $('#chainMap');
    btn.onclick = () => {
      const on = btn.dataset.on === '1';
      btn.dataset.on = on ? '0' : '1';
      btn.classList.toggle('cyan', !on);
      btn.textContent = on ? '在圖上highlight' : '取消 highlight';
      const id = box.dataset.co;
      $$('.edge', svgHost).forEach(e => {
        const hit = !on && (e.dataset.from === id || e.dataset.to === id);
        e.classList.toggle('hi', hit);
        e.classList.toggle('dim', !on && !hit);
      });
      $$('.co', svgHost).forEach(n => n.classList.toggle('dim', !on && n.dataset.id !== id));
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
    const ns = (news || []).filter(n => String(n.codes || '').split(',').includes(code)).slice(0, 8);

    state.chain = chainOfGroup(im, gid) || 'industry'; state.group = null;
    const chainName = CHAIN_NAME[state.chain] || state.chain;
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
    const card = (title, sub, body) => body
      ? `<div class="card" style="margin-top:16px"><h3>${title}${sub ? ` <small>${sub}</small>` : ''}</h3>${body}</div>` : '';

    $('#stockPage').innerHTML = `
      <div class="card" style="margin-top:16px">
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
      <div class="card" style="margin-top:16px"><div class="note">資料更新到 <b>${A.fmt.esc((A.D.meta && A.D.meta.data_date) || '—')}</b>（每個交易日盤後自動更新）。${A.L.back()}</div></div>`;
  }

  // ================================================================ Level 2：個股頁
  async function renderStock(code, im, sc, gd) {
    show(false, true, true);
    const pg = await A.load('stock/' + code, { fallback: null });
    if (!pg) { await renderStockLite(code, im, sc, gd); return; }
    const m = pg.meta, s = pg.summary || {};
    // 上方產業鏈（同步高亮）
    state.chain = chainOfGroup(im, m.group_id) || 'industry'; state.group = null;
    const chainName = CHAIN_NAME[state.chain] || state.chain;
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
      <div class="card" style="margin-top:16px">
        <div class="row spread">
          <div><h2>${A.fmt.esc(m.name)} <span class="mono cyan">${m.code}</span> <small class="muted" style="font-size:13px">${m.market || ''}</small></h2>
            <div class="row" style="gap:6px 12px;margin-top:4px;font-size:13.5px"><span class="muted">產業鏈</span>${A.L.chain(state.chain, chainName)}<span class="muted">族群</span>${groupLinks || '—'}${themeLinks ? `<span class="muted">題材</span>${themeLinks}` : ''}</div>
            <div class="row" style="margin-top:6px"><span class="num" style="font-size:30px;font-weight:700" id="pxNow" data-live="close" data-lc="${m.code}">${A.fmt.n(s.close)}</span><span class="num ${A.fmt.cls(s.chg_pct)}" style="font-size:18px" data-live="chg" data-lc="${m.code}">${A.fmt.pct(s.chg_pct, 2)}</span><span class="pill">技術分 ${A.fmt.n(s.tech_score, 0)}</span><span class="pill">本益比 ${s.pe ? A.fmt.n(s.pe, 1) : '—'}</span><span class="pill">同業分位 ${s.pe_percentile != null ? A.fmt.n(s.pe_percentile, 0) + '%' : '—'}</span><span class="pill">營收 YoY ${A.fmt.pct(s.rev_yoy)}</span><span class="pill ${tier[1]}" title="${A.fmt.esc(tier[2])}">${tier[0]}</span></div></div>
          <div class="verdict" style="min-width:280px;max-width:520px"><h3><span class="grade ${gradeCls}">${v.grade ? v.grade + ' ' : ''}${v.verdict || '—'}</span> <small>停損 ${A.fmt.n(v.stop)} · 目標 ${A.fmt.n(v.tp1)} · 風報 ${v.rr != null ? A.fmt.n(v.rr, 1) : '—'}</small></h3><ul>${(v.reasons || []).slice(0, 3).map(r => `<li>${A.fmt.esc(r)}</li>`).join('')}</ul>${v.risk_text ? `<div class="note" style="margin-top:6px">風險：${A.fmt.esc(v.risk_text)}</div>` : ''}</div>
        </div>
        <div class="toolbar" style="margin-top:14px">
          <div class="seg" id="tfSeg">${tfButtons()}</div>
          <button class="btn small" id="tfAdd" title="自訂時間週期">＋</button>
          <div id="indChips" class="row" style="gap:6px"></div>
          <div class="sp"></div>
          <button class="btn small" id="cfgBtn" title="圖表設定：線寬、均線、顏色">⚙ 設定</button>
          <button class="btn small" id="mtfBtn">${state.mtfMode ? '單一週期' : '四週期同看'}</button>
          <button class="btn small" id="wideBtn" title="收起右側事件欄，把整個視窗的寬度讓給 K 線圖">⤢ 寬版</button>
          <button class="iconbtn" id="fitBtn" title="重設縮放（雙擊價格軸也可以）" aria-label="重設縮放">
            <svg viewBox="0 0 18 18"><rect x="2.5" y="2.5" width="13" height="13" rx="2"/><path d="M6,9 H12 M9,6 V12"/></svg></button>
        </div>
        <div class="note livenote" id="liveNote" hidden></div>
        <div class="chartwrap">
          <div class="drawbar" id="drawBar"></div>
          <div id="chartHost"></div>
        </div>
        <div class="cfgpop" id="cfgPop" hidden></div>
        ${pg.note ? `<div class="banner on" style="margin:10px 0 0">${A.fmt.esc(pg.note)}</div>` : ''}
        <div class="note" style="margin-top:6px">滑鼠在圖內滾輪＝時間縮放；在右側價格軸上滾輪或拖曳＝調整上下寬度（K 棒跟著變）；雙擊價格軸還原。
          <b>成交量／KD／MACD／RSI 之間的分隔線可以上下拖，把哪一格拉大都行，拉完會記住；按右上角「重設縮放」還原。</b>分 K 來源 Yahoo Finance（1 小時可回溯 2 年、15 分 60 天），盤後更新。
          <b>週期鈕上被劃掉的＝這檔沒有那個週期的資料</b>，滑鼠移上去會說原因。</div>
        <div class="note" style="margin-top:4px">資料更新到 <b>${A.fmt.esc(pg.as_of || (A.D.meta && A.D.meta.data_date) || '—')}</b>（每個交易日盤後自動更新一次：價量、法人、籌碼、營收／財報、新聞）。</div>
      </div>
      <div class="card" style="margin-top:16px" id="mtfCard"></div>
      <div class="subtabs" id="stockTabs">${[['overview', '總覽'], ['revenue', '營收'], ['profit', '獲利'], ['dividend', '除權息'], ['chips', '籌碼'], ['basics', '基本資料'], ['news', '公告 / 新聞']].map(t => `<button data-t="${t[0]}" class="${state.tab === t[0] ? 'on' : ''}">${t[1]}</button>`).join('')}</div>
      <div id="stockTab"></div>`;
    setupChart(pg);
    renderMtf(pg);
    $$('#stockTabs button').forEach(b => b.onclick = () => { $$('#stockTabs button').forEach(x => x.classList.toggle('on', x === b)); state.tab = b.dataset.t; renderTab(pg, state.tab); });
    renderTab(pg, state.tab);
  }

  // 個股頁上方：產業鏈 › 族群 › 同族群公司（可直接切換）＋ 可收合的剖析圖與關聯圖
  function renderChainStrip(im, sc, m) {
    const el = $('#indChain'); const cid = state.chain;
    const ch = chainData(im, cid);
    const hasDiagram = HAS_DIAGRAM(cid);
    if (!ch) { el.innerHTML = ''; return; }
    const g = ch.groups.find(x => x.id === m.group_id) || (im.industries || []).find(x => x.id === m.group_id);
    const sibs = g ? (g.members || []).slice().sort((a, b) => (b.turnover || 0) - (a.turnover || 0)) : [];
    const co = sc ? sc.companies.find(c => c.tw_code === m.code) : null;
    const segs = chainSegments(sc, cid);
    let open = false; try { open = localStorage.getItem('tw.chainOpen') === '1'; } catch (e) { /* 忽略 */ }
    el.innerHTML = `<div class="card tight">
      <div class="row spread"><div class="row" style="gap:8px"><b>${A.L.chain(cid, ch.name)}</b><span class="muted">›</span>${g ? A.L.group(g.id, g.name) : A.fmt.esc(m.group || '')}${co ? `<span class="muted">›</span><span class="pill" style="border-color:${segColor(co.segment)};color:${segColor(co.segment)}">● ${A.fmt.esc(segName(sc, co.segment))}</span>` : ''}</div>
        <div class="row" style="gap:8px">${hasDiagram ? `<button class="btn small" id="chainToggle">${open ? '收合產業鏈圖 ▴' : '展開產業鏈圖 ▾'}</button>` : ''}${A.L.back()}</div></div>
      ${sibs.length ? `<div class="sibs" id="sibs"><span class="muted" style="flex:none;font-size:12px;align-self:center">同族群</span>${sibs.map(x => `<a class="lk ${x.code === m.code ? 'cur' : ''}" href="#stock/${x.code}">${A.fmt.esc(x.name)}<span class="code">${x.code}</span><span class="chg ${A.fmt.cls(x.chg_pct)}">${A.fmt.pct(x.chg_pct)}</span></a>`).join('')}</div>` : ''}
      ${!hasDiagram ? `<div class="row" style="margin-top:8px;gap:6px">${ch.groups.map(x => `<span class="pill ${x.id === m.group_id ? 'cyan' : ''}" style="cursor:pointer" onclick="location.hash='#industry/group/${x.id}'"><i class="gdot" style="--c:${A.L.gcolor[x.id] || '#8ea0c4'}"></i>${A.fmt.esc(x.name)} <span class="${A.fmt.cls(x.chg_pct)}">${A.fmt.pct(x.chg_pct)}</span></span>`).join('')}</div>` : ''}
      ${hasDiagram ? `<div id="chainBody" style="${open ? '' : 'display:none'};margin-top:10px">
        <div class="segchips">${segs.map(s => `<span class="segchip ${co && co.segment === s.id ? 'sel' : ''}" data-seg="${s.id}" style="--c:${segColor(s.id)}" title="看這個環節的供應商"><i></i>${A.fmt.esc(s.name)}</span>`).join('')}</div>
        <div id="prodDiagram" class="dgwrap" style="margin-top:10px;max-width:1080px">${window.Diagrams[cid]()}</div><div class="chainmap" id="chainMap" style="margin-top:10px;max-height:380px"></div></div>` : ''}
    </div>`;
    const cur = $('#sibs a.cur', el); if (cur && cur.scrollIntoView) setTimeout(() => cur.scrollIntoView({ block: 'nearest', inline: 'center' }), 30);
    if (hasDiagram && sc) {
      const tog = $('#chainToggle', el); tog.onclick = () => { const b = $('#chainBody', el); const isOpen = b.style.display !== 'none'; b.style.display = isOpen ? 'none' : ''; tog.textContent = isOpen ? '展開產業鏈圖 ▾' : '收合產業鏈圖 ▴'; try { localStorage.setItem('tw.chainOpen', isOpen ? '0' : '1'); } catch (e) { /* 忽略 */ } };
      paintDiagram($('#prodDiagram', el));
      // 剖析圖不加縮放：Andy 明講「產業與個股 剖析圖不用新增縮放功能」（本來就可以左右滑）
      drawChainMap($('#chainMap', el), sc, cid, im, { onSegment: (seg) => { location.hash = `#industry/${cid}/${seg}`; } });
      highlightSegments(el, co ? [co.segment] : [], co ? segColor(co.segment) : null);
      wireDiagram(el, (seg) => { location.hash = `#industry/${cid}/${seg}`; });
      $$('.segchip', el).forEach(c => c.onclick = () => { location.hash = `#industry/${cid}/${c.dataset.seg}`; });
      try { if (localStorage.getItem('tw.dganim') === '0') $('#prodDiagram', el).classList.add('noanim'); } catch (e) { /* 忽略 */ }
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
               : '這個週期要即時資料：右上角 ⚙ 設定即時報價來源之後才看得到';
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
    const drawChips = () => {
      chips.innerHTML = chipDefs.map(c => `<span class="chip ${c.on() ? 'on' : ''}" data-k="${c.k}"><i style="background:${c.color}"></i>${c.label}${c.params().map(p => `<input data-k="${c.k}" data-p="${p.key}" value="${p.val}" style="width:${p.w}px" onclick="event.stopPropagation()">`).join('')}</span>`).join('');
      $$('.chip', chips).forEach(ch => ch.onclick = (e) => { if (e.target.tagName === 'INPUT') return; chipDefs.find(c => c.k === ch.dataset.k).toggle(); saveCfg(cfg); drawChips(); apply(); });
      $$('.chip input', chips).forEach(inp => inp.onchange = () => { chipDefs.find(c => c.k === inp.dataset.k).set(inp.value, inp.dataset.p); saveCfg(cfg); drawChips(); apply(); });
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
      const bars = barsFor(pg, state.tf);
      const live = isLiveTf(state.tf);
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
      setLiveNote(live && window.LiveK ? window.LiveK.sourceNote(state.tf) : '');
      // 上一個週期沒資料時圖被拆掉了，換回有資料的週期要重建（不重建的話會整張空白到重新整理為止）
      if (!kchart || !$('#legendOv')) {
        if (kchart) { kchart.destroy(); kchart = null; }
        box.innerHTML = '<div class="legend-ov" id="legendOv"></div><div class="ohlcbox" id="ohlcBox" hidden></div>';
        kchart = new KChart(box, { tf: state.tf, onText: () => window.prompt('文字內容', '') });
        enableDraw(pg);
      }
      // 即時更新（同一檔、同一個週期、圖還在）就保留目前的縮放與位置
      const keep = kchart._liveKey === pg.meta.code + '|' + state.tf;
      kchart._liveKey = pg.meta.code + '|' + state.tf;
      kchart.setBars(bars, state.tf, keep);
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
      kchart.setZones(cfg.smc && !live ? zonesFor(pg, state.tf) : [], cfg.zone || undefined);
      kchart.setMarkers(cfg.marks && !live ? marksFor(pg, state.tf) : {});
      const v = pg.verdict || {};
      kchart.setPriceLines(cfg.lines && state.tf === '1d' ? [{ price: v.stop, title: '停損', color: '#ffb454' }, { price: v.tp1, title: '目標 1', color: '#3ee0ff' }, { price: v.tp2, title: '目標 2', color: '#8b7bff' }] : []);
      const legend = $('#legendOv');
      const TFN = { '5s': '5 秒（即時）', '1m': '1 分（即時）', '5m': '5 分（即時）', '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' };
      kchart.setWatermark(`${pg.meta.name} ${pg.meta.code} · ${TFN[state.tf] || state.tf}`);
      const at = (arr, i) => (arr ? arr[i == null ? arr.length - 1 : i] : null);
      const show = (i, pt) => {
        const idx = i == null ? kchart.data.length - 1 : i; const d = kchart.data[idx]; if (!d) return; const prev = kchart.data[idx - 1]; const vals = kchart.values || {};
        showOhlcBox(d, prev, pt, state.tf);
        const chg = prev ? (d.close - prev.close) / prev.close * 100 : null; const amp = d.low ? (d.high - d.low) / d.low * 100 : null;
        // 顏色一定要跟著主題走，不可以寫死深色主題那兩個螢光色 ——
        // #2ee59d 印在淺色主題的圖例底（近白）對比只有 1.64，等於看不見。
        // 這是 D1（DECISIONS #152）漏掉的一行，2026-09-18 被淺色主題掃描抓到。
        const col = A.upDown(d.close >= d.open ? 1 : -1);
        let s = `<b>${KUtil.fmtTime(d.time, state.tf)}</b>　開 ${A.fmt.n(d.open)}　高 ${A.fmt.n(d.high)}　低 ${A.fmt.n(d.low)}　收 <b style="color:${col}">${A.fmt.n(d.close)}</b>${chg != null ? ` <span style="color:${A.upDown(chg)}">${A.fmt.pct(chg, 2)}</span>` : ''}　振幅 ${amp != null ? A.fmt.n(amp, 1) + '%' : '—'}　量 ${A.fmt.lot(d.volume / 1000)}`;
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
    el.innerHTML = `<h3>多週期判讀 <small>大週期定方向（週 › 日），小週期找進場（4H › 1H › 15 分）</small></h3>
      <div class="lights">${(sm.tf_used || []).map(tf => { const t = sm.per_tf[tf]; return `<span class="light ${t.trend > 0 ? 'pos' : t.trend < 0 ? 'neg' : ''}">${({ '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' })[tf]} ${t.trend > 0 ? '多' : t.trend < 0 ? '空' : '盤整'}</span>`; }).join('')}</div>
      <div class="verdict" style="margin:10px 0"><h3 style="font-size:16px">${A.fmt.esc(sm.headline)}</h3><ul>${(sm.script || []).map(x => `<li>${A.fmt.esc(x)}</li>`).join('')}</ul></div>
      <div class="grid g2"><div><h4>支撐（由近到遠）</h4><div class="kvs" style="margin-top:6px">${(lv.support || []).map(z => row(z, 'support')).join('') || '<div class="note">沒有通過門檻的需求區</div>'}</div></div><div><h4>壓力（由近到遠）</h4><div class="kvs" style="margin-top:6px">${(lv.resistance || []).map(z => row(z, 'resistance')).join('') || '<div class="note">上方沒有通過門檻的供給區</div>'}</div></div></div>
      ${pg.verdict && pg.verdict.weekly_note ? `<div class="note" style="margin-top:8px">${A.fmt.esc(pg.verdict.weekly_note)}</div>` : ''}`;
  }

  // ---------------------------------------------------------------- 個股分頁
  function renderTab(pg, tab) {
    const el = $('#stockTab');
    ({ overview: tabOverview, revenue: tabRevenue, profit: tabProfit, dividend: tabDividend, chips: tabChips, basics: tabBasics, news: tabNews })[tab](pg, el);
    setTimeout(() => Object.values(A.charts).forEach(c => c && c.resize && c.resize()), 20);
  }
  function tabOverview(pg, el) {
    const f = pg.fundamental || {}, s = pg.summary || {}, iv = pg.inst_v3 || {}, dv = pg.dividends || {};
    const holders = pg.holders && pg.holders.length ? pg.holders[pg.holders.length - 1] : null; const hPrev = pg.holders && pg.holders.length > 4 ? pg.holders[pg.holders.length - 5] : null;
    const k = (l, v, cls) => `<div class="k"><div class="l">${l}</div><div class="v ${cls || ''}">${v}</div></div>`;
    el.innerHTML = `<div class="grid g3">
      <div class="card"><h3>基本面 <small>財報到 ${f.latest_period || '—'}</small></h3><div class="kvs" style="margin-top:8px">${k('近四季 EPS', f.ttm_eps != null ? A.fmt.n(f.ttm_eps) : '—')}${k('本益比', f.pe ? A.fmt.n(f.pe, 1) : '—')}${k('同業分位', f.percentile != null ? A.fmt.n(f.percentile, 0) + '%' : '<small>樣本不足</small>')}${k('ROE', f.roe != null ? A.fmt.n(f.roe, 1) + '%' : '—')}${k('毛利率', f.gross_margin != null ? A.fmt.n(f.gross_margin, 1) + '%' : '—')}${k('月營收 YoY', A.fmt.pct(f.rev_yoy), A.fmt.cls(f.rev_yoy))}${k('營運動能', f.momentum_score != null ? A.fmt.n(f.momentum_score, 0) + ' / 100' : '—')}${k('殖利率（近四次）', dv.yield_ttm != null ? A.fmt.n(dv.yield_ttm) + '%' : '—')}</div><div class="note" style="margin-top:8px">${f.group_name ? `同族群（${f.group_name}，n=${f.group_n}）本益比中位 ${f.group_median != null ? A.fmt.n(f.group_median, 1) : '—'}${f.vs_median != null ? '，本檔 ' + (f.vs_median > 0 ? '高於' : '低於') + '中位 ' + A.fmt.n(Math.abs(f.vs_median), 0) + '%' : ''}` : '本益比只在同族群內比較'}</div></div>
      <div class="card"><h3>籌碼快照</h3><div class="kvs" style="margin-top:8px">${k('法人 20 日', iv.sum20 != null ? A.fmt.lot(iv.sum20 / 1000) : '—', A.fmt.cls(iv.sum20))}${k('外資 20 日', iv.foreign20 != null ? A.fmt.lot(iv.foreign20 / 1000) : '—', A.fmt.cls(iv.foreign20))}${k('投信 20 日', iv.trust20 != null ? A.fmt.lot(iv.trust20 / 1000) : '—', A.fmt.cls(iv.trust20))}${k('千張大戶', holders ? A.fmt.n(holders[1], 1) + '%' : '—')}${k('大戶 4 週變化', holders && hPrev && holders[1] != null && hPrev[1] != null ? A.fmt.pct(holders[1] - hPrev[1], 2).replace('%', ' pp') : '—', holders && hPrev ? A.fmt.cls(holders[1] - hPrev[1]) : '')}${k('散戶（≤10 張）', holders ? A.fmt.n(holders[3], 1) + '%' : '—')}${k('融資餘額', pg.margin && pg.margin.length ? A.fmt.lot(pg.margin[pg.margin.length - 1][1]) : '—')}${k('量比', s.vol_ratio != null ? A.fmt.n(s.vol_ratio, 2) : '—')}</div><div class="note" style="margin-top:8px">「主力家數差」需券商分點資料（免費開放資料沒有）；這裡以集保千張大戶增減＋法人動向作替代指標。</div></div>
      <div class="card"><h3>技術面訊號</h3><div class="lights" style="margin-top:8px">${[['均線', s.ma_align > 0 ? '多頭排列' : s.ma_align < 0 ? '空頭排列' : '糾結', s.ma_align], ['結構', s.trend > 0 ? '多頭（HH/HL）' : s.trend < 0 ? '空頭（LH/LL）' : '盤整', s.trend], ['RSI', s.rsi != null ? s.rsi.toFixed(0) : '—', s.rsi > 50 ? 1 : -1], ['KD', s.k != null ? `K ${s.k.toFixed(0)} D ${s.d.toFixed(0)}` : '—', s.k > s.d ? 1 : -1], ['MACD OSC', s.osc != null ? s.osc.toFixed(2) : '—', s.osc > 0 ? 1 : -1], ['乖離 20', s.bias20 != null ? A.fmt.pct(s.bias20) : '—', 0], ['BOS', s.bos ? '出現' : '—', s.bos ? 1 : 0], ['CHoCH', s.choch ? '出現' : '—', s.choch ? 1 : 0], ['假跌破', s.sweep_low ? '出現' : '—', s.sweep_low ? 1 : 0]].map(x => `<span class="light ${x[2] > 0 ? 'pos' : x[2] < 0 ? 'neg' : ''}">${x[0]} ${x[1]}</span>`).join('')}</div>${pg.verdict && pg.verdict.invalidation ? `<div class="note" style="margin-top:8px">失效條件：${A.fmt.esc(pg.verdict.invalidation)}</div>` : ''}<div class="note" style="margin-top:6px">本頁為決策輔助，技術評分與規則權重尚未經 walk-forward 檢驗；不構成投資建議。</div></div></div>`;
  }
  function tabRevenue(pg, el) {
    const rv = pg.revenue || {}; const mo = rv.monthly || [];
    if (!mo.length) { el.innerHTML = '<div class="card"><div class="empty">尚無月營收歷史（回補進行中，每小時自動接續）</div></div>'; return; }
    const last = mo[mo.length - 1];
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">最新月份</div><div class="v">${last[0]}</div></div><div class="k"><div class="l">單月營收</div><div class="v">${A.fmt.yi(last[1])}</div></div><div class="k"><div class="l">YoY</div><div class="v ${A.fmt.cls(last[2])}">${A.fmt.pct(last[2])}</div></div><div class="k"><div class="l">MoM</div><div class="v ${A.fmt.cls(last[3])}">${A.fmt.pct(last[3])}</div></div><div class="k"><div class="l">累計營收</div><div class="v">${A.fmt.yi(last[4])}</div></div><div class="k"><div class="l">累計 YoY</div><div class="v ${A.fmt.cls(last[5])}">${A.fmt.pct(last[5])}</div></div></div>
      <div class="grid g2"><div class="card"><h3>每月營收與 YoY <small>近 ${Math.min(mo.length, 60)} 個月</small></h3><div id="revBar" class="chart"></div></div>
      <div class="card"><div class="row spread"><h3>年度走勢 <small>同月對比，看淡旺季</small></h3><div class="seg" id="revMode"><button data-v="m" class="on">單月</button><button data-v="c">累計</button></div></div><div id="revYear" class="chart"></div></div></div>
      <div class="card" style="margin-top:16px"><h3>月營收明細</h3><div class="tw" style="max-height:360px"><table><thead><tr><th class="l">月份</th><th>營收</th><th>YoY</th><th>MoM</th><th>累計</th><th>累計 YoY</th></tr></thead><tbody>${mo.slice().reverse().slice(0, 36).map(r => `<tr><td class="l mono">${r[0]}</td><td class="num">${A.fmt.yi(r[1])}</td><td class="num ${A.fmt.cls(r[2])}">${A.fmt.pct(r[2])}</td><td class="num ${A.fmt.cls(r[3])}">${A.fmt.pct(r[3])}</td><td class="num">${A.fmt.yi(r[4])}</td><td class="num ${A.fmt.cls(r[5])}">${A.fmt.pct(r[5])}</td></tr>`).join('')}</tbody></table></div></div>`;
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
        endLabel: { show: true, color: ZN[i + 1].c, fontSize: 11, formatter: () => lab(i) },
        labelLayout: { moveOverlap: 'shiftY' },
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
        // 區間名稱標在自己那條帶的上緣、往下掛，讀起來就是「這一塊叫什麼」
        endLabel: { show: true, color: solid ? A.CH.ink2 : ZN[i].c, fontSize: 11, verticalAlign: 'top',
          offset: [4, 3], formatter: () => ZN[i].name },
        labelLayout: { moveOverlap: 'shiftY' },
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

    A.chart(id, {
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
        axisLabel: { color: A.CH.ink3, formatter: (v) => String(v).slice(0, 7) } },
      yAxis: { ...A.axisStyle, min: yMin, max: yMax, axisLabel: { color: A.CH.ink3 } },
      series,
      // 一定要 notMerge：兩種模式的 series 數量與型態都不一樣，
      // 用合併的話切到「倍數線」時，上一次的色帶還留在圖上（實測就是這樣糊成一片）
    }, { notMerge: true });
  }

  function tabProfit(pg, el) {
    const q = (pg.profit || {}).quarters || []; const pe = pg.pe_history || [];
    if (!q.length) { el.innerHTML = '<div class="card"><div class="empty">尚無季報歷史（回補進行中）</div></div>'; return; }
    const last = q[q.length - 1];
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">最新季度</div><div class="v">${last[0]}</div></div><div class="k"><div class="l">單季 EPS</div><div class="v">${A.fmt.n(last[5])}</div></div><div class="k"><div class="l">年度累計 EPS</div><div class="v">${A.fmt.n(last[6])}</div></div><div class="k"><div class="l">EPS 年增（元）</div><div class="v ${A.fmt.cls(last[7])}">${last[7] != null ? (last[7] > 0 ? '+' : '') + A.fmt.n(last[7]) : '—'}</div></div><div class="k"><div class="l">毛利率</div><div class="v">${A.fmt.n(last[2], 1)}%</div></div><div class="k"><div class="l">營益率</div><div class="v">${A.fmt.n(last[3], 1)}%</div></div><div class="k"><div class="l">淨利率</div><div class="v">${A.fmt.n(last[4], 1)}%</div></div></div>
      <div class="card"><div class="row spread"><h3>本益比河流圖 <small>近四季 EPS × 各倍數 ＝ 那個倍數對應的股價；白線是實際收盤，它落在哪一條帶就是市場現在給的評價。倍數用這一檔自己的歷史分位數，不是寫死的 15/20/25 倍</small></h3>
        <div class="row" style="gap:10px;align-items:center">
          <div class="seg" id="peMode"><button data-v="band">色帶分區</button><button data-v="fill">填滿</button><button data-v="mult">倍數線</button></div>
          <label class="opabox" title="色帶透明度（跟上面 K 線的本益比帶共用同一組設定）">透明度
            <input id="peOpa" type="range" min="10" max="100" step="5"><span class="val" id="peOpaV"></span></label>
        </div></div>
        <div class="row" style="gap:12px;flex-wrap:wrap;margin-bottom:6px">
          <div id="peLen" title="這張圖一次看多長一段"></div>
          <div id="peEnd" title="截止到哪一天：往回拉看以前的評價，按 ▶ 一天一天播"></div>
        </div>
        <div id="peWrap"><div id="peChart" class="chart" style="height:340px"></div></div><div class="note" id="peNote"></div></div>
      <div class="grid g2" style="margin-top:16px"><div class="card"><h3>EPS 與三率 <small>單季；財報法規為季報，沒有每月</small></h3><div id="profitChart" class="chart"></div></div><div class="card"><h3>本益比（每季）<small>每季財報可用日後的收盤 / 近四季 EPS；虧損不算</small></h3><div id="peQ" class="chart"></div></div></div>
      <div class="card" style="margin-top:16px"><h3>季報明細</h3><div class="tw" style="max-height:360px"><table><thead><tr><th class="l">季度</th><th>營收</th><th>毛利率</th><th>營益率</th><th>淨利率</th><th>淨利</th><th>EPS</th><th>累計 EPS</th><th>EPS 年增</th></tr></thead><tbody>${q.slice().reverse().map(r => `<tr><td class="l mono">${r[0]}</td><td class="num">${A.fmt.yi(r[1])}</td><td class="num">${A.fmt.n(r[2], 1)}%</td><td class="num">${A.fmt.n(r[3], 1)}%</td><td class="num">${A.fmt.n(r[4], 1)}%</td><td class="num">${A.fmt.yi(r[8])}</td><td class="num">${A.fmt.n(r[5])}</td><td class="num">${A.fmt.n(r[6])}</td><td class="num ${A.fmt.cls(r[7])}">${r[7] != null ? (r[7] > 0 ? '+' : '') + A.fmt.n(r[7]) : '—'}</td></tr>`).join('')}</tbody></table></div></div>`;
    A.chart('profitChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 50, right: 50, top: 30, bottom: 30 },
      xAxis: { ...A.axisStyle, type: 'category', data: q.map(r => r[0]), axisLabel: { color: A.CH.ink3 } }, yAxis: [{ ...A.axisStyle, name: 'EPS' }, { ...A.axisStyle, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }],
      series: [{ name: 'EPS', type: 'bar', data: q.map(r => ({ value: r[5], itemStyle: { color: r[5] >= 0 ? 'rgba(255,77,109,.7)' : 'rgba(46,229,157,.7)', borderRadius: [3, 3, 0, 0] } })) }, { name: '毛利率', type: 'line', yAxisIndex: 1, data: q.map(r => r[2]), smooth: .3, showSymbol: false, lineStyle: { color: '#ffd166' } }, { name: '營益率', type: 'line', yAxisIndex: 1, data: q.map(r => r[3]), smooth: .3, showSymbol: false, lineStyle: { color: '#3ee0ff' } }, { name: '淨利率', type: 'line', yAxisIndex: 1, data: q.map(r => r[4]), smooth: .3, showSymbol: false, lineStyle: { color: '#8b7bff' } }] });
    if (pe.length) A.chart('peQ', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => { const r = pe[ps[0].dataIndex]; return `<b>${r.period}</b><br>本益比 ${r.pe ?? '—'}（區間 ${r.pe_low ?? '—'}–${r.pe_high ?? '—'}）<br>近四季 EPS ${r.ttm_eps}`; } }, grid: { left: 50, right: 20, top: 20, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: pe.map(r => r.period), axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle, scale: true },
      series: [{ name: '區間', type: 'line', data: pe.map(r => r.pe_low), lineStyle: { opacity: 0 }, stack: 'pe', showSymbol: false }, { name: '高低', type: 'line', data: pe.map(r => r.pe_high != null && r.pe_low != null ? r.pe_high - r.pe_low : null), lineStyle: { opacity: 0 }, stack: 'pe', areaStyle: { color: 'rgba(139,123,255,.2)' }, showSymbol: false }, { name: '本益比', type: 'line', data: pe.map(r => r.pe), lineStyle: { color: '#8b7bff', width: 2 }, symbolSize: 5 }] });
    else A.empty('peQ', '需要四季連續財報');

    // ---- 河流圖：兩種模式，選過就記住（換股票、重新整理都沿用）
    const river = peRiver(pg);
    const MODES = ['band', 'fill', 'mult'];
    let mode = 'band';
    try { const s = localStorage.getItem('tw.periver'); if (MODES.includes(s)) mode = s; } catch (e) { /* 忽略 */ }
    const note = $('#peNote', el);
    const HOWTO = {
      band: '色帶分區：顏色越紅代表市場給的評價越高',
      fill: '填滿：整片實色，一眼看出收盤線落在哪一塊評價區間',
      mult: '倍數線：線尾標的是本益比倍數',
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
      <div class="grid g2"><div class="card"><h3>各年度現金股利 <small>依股利所屬年度</small></h3><div id="divBar" class="chart"></div></div>
      <div class="card"><h3>除權息紀錄 <small>填息天數＝除息後首次收在除息前收盤之上</small></h3><div class="tw" style="max-height:300px"><table><thead><tr><th class="l">除權息日</th><th class="l">類別</th><th>股利</th><th>前收盤</th><th>參考價</th><th>填息</th></tr></thead><tbody>${rs.map(r => `<tr><td class="l mono">${r.date}</td><td class="l">${r.kind}</td><td class="num">${A.fmt.n(r.dividend)}</td><td class="num">${A.fmt.n(r.before_price)}</td><td class="num">${A.fmt.n(r.reference_price)}</td><td class="num">${r.fill_days === -1 ? '<span class="down">未填</span>' : r.fill_days != null ? r.fill_days + ' 天' : '—'}</td></tr>`).join('') || '<tr><td colspan="6" class="l muted">—</td></tr>'}</tbody></table></div></div></div>
      <div class="card" style="margin-top:16px"><h3>股利公告</h3><div class="tw" style="max-height:320px"><table><thead><tr><th class="l">所屬期間</th><th class="l">類別</th><th>金額（元/股）</th><th class="l">公告日</th><th class="l">除權息日</th><th class="l">發放日</th></tr></thead><tbody>${ev.map(e => `<tr><td class="l">${A.fmt.esc(e.period)}</td><td class="l">${e.kind === 'cash' ? '現金' : '股票'}</td><td class="num">${A.fmt.n(e.amount, 3)}</td><td class="l mono">${e.announce_date || '—'}</td><td class="l mono">${e.ex_date || '—'}</td><td class="l mono">${e.payment_date || '—'}</td></tr>`).join('')}</tbody></table></div></div>`;
    if (years.length) A.chart('divBar', { tooltip: { ...A.tip }, grid: { left: 50, right: 20, top: 16, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: years, axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle }, series: [{ type: 'bar', data: years.map(y => +byYear[y].toFixed(3)), itemStyle: { color: '#ffb454', borderRadius: [3, 3, 0, 0] }, label: { show: true, position: 'top', color: '#e8eeff', fontFamily: 'JetBrains Mono', fontSize: 11 }, barWidth: '55%' }] }); else A.empty('divBar');
  }
  /* 籌碼頁：資料不夠就不要畫一張空圖。
     Andy：「若是籌碼下方無法抓取到數據，就把他替換其他方式，或是直接刪除」。
     規則：≥3 個點才畫線圖；只有 1~2 個點就改成把「現在的數字」直接列出來；
     一個點都沒有的那張卡片整張不出現。 */
  const CHIP_MIN = 3;
  function tabChips(pg, el) {
    const iv = (pg.inst_v3 || {}).daily || [], mg = pg.margin || [], ho = pg.holders || [];
    const cards = [];
    const card = (id, title, sub) => { cards.push(`<div class="card"><h3>${title} <small>${sub}</small></h3><div id="${id}" class="chart"></div></div>`); };
    const numCard = (title, sub, kvs, why) => cards.push(`<div class="card"><h3>${title} <small>${sub}</small></h3>
      <div class="kvs" style="margin-top:10px">${kvs}</div><div class="note" style="margin-top:8px">${why}</div></div>`);
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
      card('holderChart', '大戶 / 散戶持股', '集保每週：千張大戶、400–1000 張、10 張以下');
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
    el.innerHTML = cards.map((c, i) => (i % 2 === 0 ? `<div class="grid g2"${i ? ' style="margin-top:16px"' : ''}>` : '') + c + (i % 2 === 1 || i === cards.length - 1 ? '</div>' : '')).join('')
      + `<div class="note" style="margin-top:10px">主力（券商分點家數差）需付費資料，尚未提供；以千張大戶週變化與法人連續買賣作替代。</div>`;

    if (iv.length >= CHIP_MIN) A.chart('instChart', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${A.fmt.lot(p.value / 1000)}`).join('<br>') }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 60, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: iv.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(5) } }, yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) } }, { ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) }, splitLine: { show: false } }],
      series: [{ name: '外資', type: 'bar', stack: 'i', data: iv.map(r => r[1]), itemStyle: { color: '#3ee0ff' } }, { name: '投信', type: 'bar', stack: 'i', data: iv.map(r => r[2]), itemStyle: { color: '#ffb454' } }, { name: '自營', type: 'bar', stack: 'i', data: iv.map(r => r[3]), itemStyle: { color: '#8b7bff' } }, { name: '累計', type: 'line', yAxisIndex: 1, data: iv.map(r => r[4]), showSymbol: false, lineStyle: { color: '#ff8fab', width: 2 } }] });
    if (mg.length >= CHIP_MIN) A.chart('marginChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 60, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: mg.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(5) } }, yAxis: [{ ...A.axisStyle, scale: true }, { ...A.axisStyle, scale: true, splitLine: { show: false } }],
      series: [{ name: '融資餘額', type: 'line', data: mg.map(r => r[1]), showSymbol: false, areaStyle: { color: 'rgba(255,77,109,.12)' }, lineStyle: { color: '#ff4d6d', width: 2 } }, { name: '融券餘額', type: 'line', yAxisIndex: 1, data: mg.map(r => r[2]), showSymbol: false, lineStyle: { color: '#2ee59d', width: 1.5 } }] });
    if (ho.length >= CHIP_MIN) {
      A.chart('holderChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 50, right: 20, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: ho.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2, 7) } }, yAxis: { ...A.axisStyle, scale: true, axisLabel: { formatter: '{value}%' } },
        series: [{ name: '千張大戶', type: 'line', data: ho.map(r => r[1]), showSymbol: false, lineStyle: { color: '#ff4d6d', width: 2 } }, { name: '400–1000 張', type: 'line', data: ho.map(r => r[2]), showSymbol: false, lineStyle: { color: '#ffb454' } }, { name: '散戶 ≤10 張', type: 'line', data: ho.map(r => r[3]), showSymbol: false, lineStyle: { color: '#2ee59d' } }] });
      A.chart('holderCount', { tooltip: { ...A.tip, trigger: 'axis' }, grid: { left: 70, right: 20, top: 16, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: ho.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2, 7) } }, yAxis: { ...A.axisStyle, scale: true, axisLabel: { formatter: v => A.fmt.yi(v) } }, series: [{ name: '股東人數', type: 'line', data: ho.map(r => r[4]), showSymbol: false, areaStyle: { color: 'rgba(62,224,255,.12)' }, lineStyle: { color: '#3ee0ff', width: 2 } }] });
    }
  }
  function tabBasics(pg, el) {
    const b = pg.basics || {}; const f = pg.fundamental || {};
    const indLink = b.industry ? (A.L.gname['ind_' + b.industry] ? A.L.group('ind_' + b.industry, b.industry) : A.fmt.esc(b.industry)) : null;
    const rows = [['公司全名', b.full_name], ['市場', b.market], ['產業別', indLink, true], ['上市日', b.listed_date], ['股本', b.capital_billion != null ? b.capital_billion + ' 億' : null], ['董事長', b.chairman], ['網站', b.website ? `<a href="${A.fmt.esc(b.website)}" target="_blank" rel="noopener">${A.fmt.esc(b.website)}</a>` : null, true], ['市值', f.market_cap != null ? A.fmt.yi(f.market_cap) : null], ['股價淨值比', f.pb != null ? A.fmt.n(f.pb) : null], ['股價營收比', f.ps != null ? A.fmt.n(f.ps) : null], ['所屬族群', (pg.meta.groups || []).map(gn => A.L.groupByName(gn)).join(' ') || null, true], ['題材', A.L.themesOf(pg.meta.code) || null, true]];
    el.innerHTML = `<div class="card"><h3>基本資料 <small>產業別、族群、題材都可以點</small></h3><dl class="kv" style="margin-top:10px">${rows.map(r => `<dt>${r[0]}</dt><dd>${r[1] != null && r[1] !== '' ? (r[2] ? r[1] : A.fmt.esc(r[1])) : '—'}</dd>`).join('')}</dl></div>
      <div class="card" style="margin-top:16px"><div class="row spread">
        <h3>1–12 月平均漲幅 <small id="msSub"></small></h3>
        <div class="row" style="gap:10px;align-items:center">
          <div class="seg" id="msYears"><button data-v="1">1 年</button><button data-v="3">3 年</button><button data-v="5" class="on">5 年</button><button data-v="0">全部</button></div>
          <label class="opabox">自填 <input id="msCustom" type="number" min="1" max="15" step="1" style="width:56px" placeholder="年"></label>
        </div></div>
        <div id="msChart" class="chart" style="min-height:320px"></div>
        <div class="note" id="msNote"></div></div>`;
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
          data: stat.map(s => ({ value: s.avg == null ? null : +s.avg.toFixed(2),
            itemStyle: { color: s.avg > 0 ? A.CH.up : s.avg < 0 ? A.CH.down : A.CH.ink3, borderRadius: 4 } })),
          label: { show: true, position: 'top', color: A.CH.ink3, fontSize: 10.5,
            formatter: (q) => { const s = stat[q.dataIndex]; return s.n ? `${s.up}/${s.n}` : ''; } } }],
      }, { notMerge: true });
      const best = stat.filter(s => s.avg != null).sort((a, b) => b.avg - a.avg)[0];
      const worst = stat.filter(s => s.avg != null).sort((a, b) => a.avg - b.avg)[0];
      $('#msNote').innerHTML = best && worst
        ? `這段期間最強的是 <b>${best.m} 月</b>（平均 ${A.fmt.pct(best.avg)}、${best.up}/${best.n} 年上漲），`
          + `最弱的是 <b>${worst.m} 月</b>（平均 ${A.fmt.pct(worst.avg)}、${worst.up}/${worst.n} 年上漲）。`
          + `<br><span class="muted">柱子上的 ${'x/y'} 是「上漲年數／取樣年數」—— 只看平均會被一次暴漲暴跌帶偏。`
          + `樣本少於 3 年的月份參考就好。</span>`
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
  function tabNews(pg, el) {
    const news = pg.news || [], bv = pg.broker_views || [], mn = pg.material_news || [];
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
        <h3>重大訊息 <small>公司自己公告的，不是媒體報導</small></h3>
        <a class="pill" href="https://mops.twse.com.tw/mops/web/t05st01" target="_blank" rel="noopener">公開資訊觀測站 ↗</a></div>
      <div class="note" style="margin:6px 0 4px">只存摘要前 800 字；要看全文請到公開資訊觀測站查該公司該日期的公告。</div>
      ${mnHtml}</div>
      <div class="grid g2"><div class="card"><h3>相關新聞 <small>鉅亨 / TechNews / 經濟日報</small></h3>${news.length ? news.map(n => `<div class="ev" style="padding-left:0;padding-right:0"><a href="${A.fmt.esc(n.url)}" target="_blank" rel="noopener">${A.fmt.esc(n.title)}</a><div class="m"><span class="mono">${n.date}</span><span class="cat">${A.fmt.esc(n.category || '')}</span><span>${A.fmt.esc(n.source || '')}</span></div></div>`).join('') : '<div class="empty">近期沒有提到這檔的新聞</div>'}</div>
      <div class="card"><h3>券商觀點（新聞引述） <small>不是本站預估</small></h3>${bv.length ? `<div class="tw"><table><thead><tr><th class="l">日期</th><th class="l">券商</th><th>目標價</th><th class="l">動作</th></tr></thead><tbody>${bv.map(b => `<tr onclick="window.open('${A.fmt.esc(b.url || '#')}','_blank')"><td class="l mono">${b.date}</td><td class="l">${A.fmt.esc(b.broker || '—')}</td><td class="num">${A.fmt.n(b.target_price)}</td><td class="l">${A.fmt.esc(b.action || b.rating || '—')}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">近 60 天沒有引述到目標價的新聞</div>'}</div></div>`;
  }

  // _dbg 只給 scripts/_preview.py 驗證用（檢查圖表與繪圖狀態），正式頁面不會呼叫
  window.Industry = { route,
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
    })() }) };
})();
