/* ============================================================================
   產業地圖「地圖」檢視（site/indmap.js）
   ----------------------------------------------------------------------------
   Andy 2026-10-02：「產業地圖需要圖案結合 Map 概念」。
   原本 #industry 首頁（全市場分頁）是「族群漲跌長條＋成交值圓餅」，讀起來像清單。
   這支把同一份資料畫成一張**地圖**：

     · 每條產業鏈＝一塊「區域」（島），區域裡放那條鏈的圖示（晶片、機櫃、電路板、銀行…）
     · 族群＝區域裡的「街區／地標」，方塊之間 3px 的縫就是街道
         顏色＝今日漲跌（7 格離散色階，跟熱力圖同一套 --hm-*，紅漲綠跌）
               或「資金熱度」＝本週成交占比 − 上週（pp，flow_v3.periods[w0]）
         大小＝成交值占比（預設開根號壓縮：大的仍然大、小的也點得到；可切「等比」）
         區域內由左到右＝上游 → 中游 → 下游（groups_today 的 tier）
     · 區域之間的「道路」＝資料裡真的有的跨區關係，**不畫憑空想像的路**：
         實線路＝supply_chain.json 的公司級供應邊，兩端落在不同區域（數字＝邊數）
         虛線路＝同一家公司同時是兩區族群的成分股（industry_map.json 的成分股交集）
       沒有道路的島＝資料裡找不到跨區的供應邊或共用成分股（金融、傳產、軟體目前就是）。
     · 點區域 → #industry/<chain>；點族群 → #industry/group/<gid>；滑過顯示數字。

   只用既有的 site/data（industry_map／supply_chain／groups_today；資金熱度才去拿 flow_v3），不動 pipeline。
   顏色全部走主題 token（--hm-*、--panel*、--ink*、--cyan…），深淺主題與 v4 三主題（casual／hud／pro）
   只換變數，骨架只有一套。手機（≤820）不用這支 —— industry.js 在窄畫面一律畫清單。
   ============================================================================ */
(function () {
  'use strict';
  if (window.IndMap) return;
  const NS = 'http://www.w3.org/2000/svg';

  /* ---------------------------------------------------------------- 圖示
     Lucide 那一組（cpu／server／board／factory…）直接跟 icons.js 借（ISC，授權在 site/vendor/lucide.LICENSE）；
     其餘是這支自己畫的 24×24 線稿（stroke 1.8、圓頭），不走 CDN。*/
  const OWN = {
    memory: '<rect x="2" y="6" width="20" height="10" rx="1.5"/><path d="M6 16v3M10 16v3M14 16v3M18 16v3"/><path d="M6 9.5h3v3H6zM11 9.5h2v3h-2zM15 9.5h3v3h-3z"/>',
    wafer: '<circle cx="12" cy="12" r="9"/><path d="M7.5 8.5h9v7h-9zM12 8.5v7M7.5 12h9"/>',
    monitor: '<rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
    phone: '<rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M11 18h2"/>',
    laptop: '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19h20"/>',
    lens: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><path d="M12 3v4.5M19.8 7.5l-3.9 2.3M19.8 16.5l-3.9-2.3"/>',
    vr: '<path d="M3 8h18a1 1 0 0 1 1 1v6a2 2 0 0 1-2 2h-4l-2-2.5h-4L8 17H4a2 2 0 0 1-2-2V9a1 1 0 0 1 1-1z"/>',
    droplet: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/><path d="M9.5 14.5a2.5 2.5 0 0 0 2.5 2.5"/>',
    fan: '<circle cx="12" cy="12" r="1.8"/><path d="M12 10.2c-.6-3.8.4-7.2 3-7.2 2.8 0 2.6 4.4-1.4 7.4M13.8 12c3.8-.6 7.2.4 7.2 3 0 2.8-4.4 2.6-7.4-1.4M12 13.8c.6 3.8-.4 7.2-3 7.2-2.8 0-2.6-4.4 1.4-7.4M10.2 12c-3.8.6-7.2-.4-7.2-3 0-2.8 4.4-2.6 7.4 1.4"/>',
    plug: '<path d="M9 2v5M15 2v5M6 7h12v4a6 6 0 0 1-12 0V7zM12 17v5"/>',
    battery: '<rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 11v2M6 10v4M10 10v4"/>',
    laser: '<circle cx="6" cy="12" r="3"/><path d="M9 12h13M13 8l4-3M13 16l4 3"/>',
    connector: '<rect x="3" y="9" width="18" height="8" rx="1.5"/><path d="M8 9V5h8v4M7 12v2M10 12v2M13 12v2M16 12v2"/>',
    car: '<path d="M3 16v-3l2.2-5h13.6L21 13v3"/><path d="M2 16h20v2H2zM6 13h12"/><circle cx="7" cy="18.5" r="1.6"/><circle cx="17" cy="18.5" r="1.6"/>',
    pill: '<rect x="1.8" y="8.5" width="20.4" height="7" rx="3.5" transform="rotate(-35 12 12)"/><path d="M9.6 8.6l4.8 6.8"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    cloud: '<path d="M7 18h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.2 10.6 3.8 3.8 0 0 0 7 18z"/>',
    ship: '<path d="M3 15l2 5h14l2-5z"/><path d="M5 15V10h14v5M9 10V6h6v4M12 3v3"/>',
    plane: '<path d="M21 15.5 13.5 11V5.2a1.5 1.5 0 0 0-3 0V11L3 15.5V17l7.5-2v4l-2 1.4V22l3.5-1 3.5 1v-1.6l-2-1.4v-4L21 17z"/>',
    truck: '<path d="M2 6h11v10H2zM13 9.5h4.5L21 13v3h-8"/><circle cx="6" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    antenna: '<path d="M12 12v10M8 22h8M5 7a9 9 0 0 1 14 0M8 9.5a5 5 0 0 1 8 0"/><circle cx="12" cy="12" r="1.5"/>',
    satellite: '<rect x="9.5" y="9.5" width="5" height="5" rx="1" transform="rotate(45 12 12)"/><path d="M3 9l3-3 3 3-3 3zM15 15l3-3 3 3-3 3zM14.5 9.5 16 8M9.5 14.5 8 16"/>',
    star: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M12 8.2l1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.4 1.3.5-2.6-1.9-1.8 2.6-.4z"/>',
    flask: '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3"/><path d="M7.4 15h9.2"/>',
    tower: '<path d="M8 22l4-20 4 20M6 7h12M5 12h14M9.6 12l5 10M14.4 12l-5 10"/>',
    cable: '<path d="M4 20c0-6 4-6 8-8s8-2 8-8"/><circle cx="4" cy="20" r="1.6"/><circle cx="20" cy="4" r="1.6"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5V22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M2 12h2.5M19.5 12H22M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/>',
    wind: '<path d="M12 12v10M9 22h6M12 12V3M12 12l7.8 4.5M12 12l-7.8 4.5"/><circle cx="12" cy="12" r="1.6"/>',
    gear: '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
    cap: '<path d="M2 12h8M14 12h8M10 5v14M14 5v14"/>',
    resistor: '<path d="M2 12h4l2-4 3 8 3-8 3 8 2-4h3"/>',
    inductor: '<path d="M1 14h3a2.7 2.7 0 0 1 5.4 0 2.7 2.7 0 0 1 5.4 0 2.7 2.7 0 0 1 5.4 0H23"/>',
    crystal: '<rect x="5" y="6" width="14" height="10" rx="5"/><path d="M8.5 16v5M15.5 16v5"/>',
    mlcc: '<rect x="3" y="8" width="18" height="8" rx="1.2"/><path d="M7.5 8v8M16.5 8v8"/>',
    tool: '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M3 8.5h18M8 21h8M12 16v5M6.5 12h4"/>',
    glass: '<rect x="4" y="4" width="16" height="16" rx="1.5"/><path d="M8 9l3-3M8 14l8-8M13 17l5-5"/>',
    roll: '<ellipse cx="7" cy="12" rx="3" ry="7"/><path d="M7 5h11M7 19h11M18 5a3 7 0 0 1 0 14"/>',
    weave: '<path d="M3 7h18M3 12h18M3 17h18M7 3v18M12 3v18M17 3v18"/>',
    rack: '<rect x="4" y="2.5" width="16" height="19" rx="1.5"/><path d="M4 8.8h16M4 15.2h16M7.5 5.6h.01M7.5 12h.01M7.5 18.4h.01M11 5.6h5.5M11 12h5.5M11 18.4h5.5"/>',
    rail: '<path d="M3 8h18v8H3zM3 12h18M6.5 8V5.5M17.5 8V5.5M6.5 16v2.5M17.5 16v2.5"/>',
    wave: '<path d="M2 12c2.5-6 5.5-6 8 0s5.5 6 8 0h4"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    beam: '<path d="M4 5h16M4 19h16M12 5v14M8 5v2M16 5v2M8 19v-2M16 19v-2"/>',
    shirt: '<path d="M8 3 3 6l2 4 3-1v12h8V9l3 1 2-4-5-3a4 4 0 0 1-8 0z"/>',
    bowl: '<path d="M3 11h18a9 9 0 0 1-18 0zM9 3c-1 1.5 1 2.5 0 4M13 3c-1 1.5 1 2.5 0 4"/>',
    ball: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3.5 3 3.5 15 0 18M12 3c-3.5 3-3.5 15 0 18"/>',
    home: '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    tire: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 3v5M12 16v5M3 12h5M16 12h5"/>',
    hotel: '<path d="M3 21h18M5 21V7l7-4 7 4v14M9 9h.01M15 9h.01M9 13h.01M15 13h.01M10 21v-4h4v4"/>',
    recycle: '<path d="M7 19H4.5a1.5 1.5 0 0 1-1.3-2.3L7 10M11 4.5l1-1.6a1.5 1.5 0 0 1 2.6 0L18 9M17 19h2.5a1.5 1.5 0 0 0 1.3-2.3L19.5 14.5M7 10l-3 .5M7 10l1 3M18 9l.5-3M18 9l-3 .5M10 19h7M14 16l3 3-3 3"/>',
    chip: '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    stack: '<path d="M12 3 2 8l10 5 10-5z"/><path d="M2 12.5l10 5 10-5M2 17l10 5 10-5"/>',
    pkg: '<path d="M12 2 3 7v10l9 5 9-5V7z"/><path d="M3 7l9 5 9-5M12 12v10"/>',
    test: '<path d="M4 12l4 4L18 6M9 20h11"/>',
    probe: '<path d="M7 3h10v4l-3 3v4l-2 7-2-7v-4L7 7z"/>',
    store: '<path d="M3 9l2-5h14l2 5M3 9h18v11H3zM3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0M10 20v-5h4v5"/>',
    hat: '<path d="M2 18h20M4 18v-2a8 8 0 0 1 16 0v2M10 8V5h4v3"/>',
    bank: '<path d="M3 21h18M5 18V10M9.5 18V10M14.5 18V10M19 18V10M2 10h20L12 3z"/>',
    heart: '<path d="M12 20s-8-4.7-8-10.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15.3 12 20 12 20z"/>',
    candle: '<path d="M7 3v4M7 17v4M17 3v6M17 19v2"/><rect x="5" y="7" width="4" height="10" rx="1"/><rect x="15" y="9" width="4" height="10" rx="1"/>',
    code: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>',
    cart: '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.6 12.4a2 2 0 0 0 2 1.6h8.8a2 2 0 0 0 2-1.6L22 7H6"/>',
    factory: '<path d="M3 21V10l5 3V10l5 3V5h4l1 16zM3 21h18M7 17h2M12 17h2"/>',
    switch: '<rect x="2" y="8" width="20" height="8" rx="1.5"/><path d="M5.5 12h.01M8.5 12h.01M11.5 12h.01M14.5 12h.01M18 10.5v3"/>',
    fiber: '<path d="M2 16c4 0 4-8 8-8s4 8 8 8h4M2 8c4 0 4 8 8 8"/>',
    bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    pie: '<path d="M12 3a9 9 0 1 0 9 9h-9z"/><path d="M15 2.5A9 9 0 0 1 21.5 9H15z"/>',
    building: '<path d="M4 21V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v16M15 10h4a1 1 0 0 1 1 1v10M2 21h20M8 8h3M8 12h3M8 16h3"/>',
    sparkle: '<path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6z"/><path d="M19 16v4M17 18h4"/>',
    box: '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    leaf: '<path d="M5 19c0-9 6-14 15-14 0 9-5 15-14 15M5 19l7-7"/>',
    flame: '<path d="M12 3q1 4 4 6.5t3 5.5a7 7 0 0 1-14 0 5 5 0 0 1 1-3 3 3 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4z"/>',
    file: '<path d="M6 2h8l4 4v16H6zM14 2v4h4M9 12h6M9 16h6"/>',
    island: '<path d="M3 18c3-1 6-1 9 0s6 1 9 0M12 18V9M12 9c-2-3-6-3-7-1M12 9c2-3 6-3 7-1M12 9c-1-3 0-5 2-6"/>',
  };
  function iconBody(k) {
    if (OWN[k]) return OWN[k];
    return OWN.box;
  }

  /* 族群 id → 圖示。沒列到的族群用它所在區域的圖示。法定產業別用中文名的關鍵字（id 是 ind_<中文>）。*/
  const GROUP_ICON = {
    ip_asic: 'chip', hpc_network_ic: 'chip', cpu_agentic_ai: 'chip', cxl: 'link', display_driver_ic: 'monitor',
    analog_power_ic: 'wave', optical_sensing: 'eye', foundry: 'wafer', wide_bandgap: 'bolt', silicon_wafer: 'wafer',
    fab_material: 'flask', fab_process_equip: 'tool', fab_equipment: 'tool', pkg_equipment: 'tool', pkg_metrology: 'probe',
    osat: 'pkg', ic_test_service: 'test', ai_adv_packaging: 'stack', hbm: 'stack', nor_niche_memory: 'memory',
    memory_module: 'memory', leadframe_chem: 'flask', ic_distribution: 'box', semi_facility: 'hat',
    ai_server_odm: 'rack', chassis_rail: 'rail', liquid_cooling: 'droplet', air_cooling: 'fan', server_psu: 'plug',
    bbu: 'battery', switch_wireless: 'switch', optical_module: 'fiber', silicon_photonics: 'laser', ic_substrate: 'chip',
    pcb_rigid: 'chip', flex_pcb: 'wave', ccl: 'stack', copper_foil: 'roll', glass_fiber: 'weave', glass_substrate: 'glass',
    ai_interconnect: 'connector', connector_ind: 'connector', connector_auto: 'car',
    ai_pc: 'laptop', ems: 'factory', edge_ai: 'chip', smartphone: 'phone', optical_lens: 'lens', ar_vr_optics: 'vr',
    panel: 'monitor', microled: 'monitor', mlcc: 'mlcc', resistor_protect: 'resistor', jp_passive: 'cap', capacitor: 'cap',
    power_inductor: 'inductor', crystal: 'crystal', satellite: 'satellite', precision_parts: 'gear',
    factory_automation: 'factory', machine_tool: 'gear',
    cyber_security: 'shield', cloud_msp: 'cloud', saas: 'code', ecommerce: 'cart',
    bank: 'bank', life_fhc: 'heart', securities_fhc: 'candle',
    shipping_container: 'ship', shipping_bulk: 'ship', airline: 'plane', land_transport: 'truck', telecom: 'antenna',
    defense: 'star', petrochemical: 'flask', env_recycle: 'recycle',
    heavy_electric: 'tower', wire_cable: 'cable', solar: 'sun', wind_power: 'wind', energy_storage: 'battery',
    battery_cell: 'battery', battery_material: 'flask',
  };
  // 印刷電路板那幾格用 icons.js 的 board（Lucide circuit-board）；載板也是板
  const LUCIDE_PREF = { pcb_rigid: 'board', ic_substrate: 'board', ccl: 'board' };
  const IND_ICON = [
    ['ETF', 'pie'], ['半導體', 'chip'], ['電子零組件', 'mlcc'], ['光電', 'lens'], ['生技', 'pill'], ['鋼鐵', 'beam'],
    ['化學', 'flask'], ['文化創意', 'sparkle'], ['其他電子', 'chip'], ['電腦', 'laptop'], ['通信', 'antenna'],
    ['電機', 'gear'], ['水泥', 'building'], ['汽車', 'car'], ['金融', 'bank'], ['營建', 'building'], ['玻璃', 'glass'],
    ['綠能', 'leaf'], ['紡織', 'shirt'], ['資訊服務', 'code'], ['食品', 'bowl'], ['運動', 'ball'], ['貿易', 'cart'],
    ['電子通路', 'box'], ['數位雲端', 'cloud'], ['居家', 'home'], ['電器電纜', 'cable'], ['橡膠', 'tire'],
    ['觀光', 'hotel'], ['塑膠', 'flask'], ['造紙', 'file'], ['油電', 'flame'], ['農業', 'leaf'], ['其他', 'box'],
  ];
  const CHAIN_ICON = { semiconductor: 'chip', ai_server: 'rack', electronics: 'phone', software: 'code', financial: 'bank',
    traditional: 'ship', infrastructure: 'tower', industry: 'building' };
  // 區域的底色色相：只用主題 token 混出來（不寫死色碼），紅綠留給漲跌，區域一律不用 --rise／--fall
  const CHAIN_TINT = {
    semiconductor: 'var(--cyan)', ai_server: 'var(--violet)', electronics: 'var(--amber)', software: 'var(--lime)',
    financial: 'color-mix(in srgb,var(--cyan) 45%,var(--violet))', traditional: 'color-mix(in srgb,var(--amber) 55%,var(--violet))',
    infrastructure: 'color-mix(in srgb,var(--lime) 55%,var(--amber))', industry: 'var(--ink-3)',
  };
  const TIER_ORD = { upstream: 0, midstream: 1, downstream: 2, standalone: 3 };
  const TIER_NAME = { upstream: '上游', midstream: '中游', downstream: '下游', standalone: '' };

  function groupIcon(g) {
    if (!g) return 'box';
    if (LUCIDE_PREF[g.id] && window.TwIcons && window.TwIcons.ICONS[LUCIDE_PREF[g.id]]) return 'L:' + LUCIDE_PREF[g.id];
    if (GROUP_ICON[g.id]) return GROUP_ICON[g.id];
    if (String(g.id).startsWith('ind_')) {
      const nm = g.name || '';
      for (const [kw, ic] of IND_ICON) if (nm.indexOf(kw) >= 0) return ic;
      return 'box';
    }
    return CHAIN_ICON[g.chain] || 'box';
  }
  function iconSvg(k) {
    if (String(k).startsWith('L:')) { const L = window.TwIcons && window.TwIcons.ICONS[k.slice(2)]; if (L) return L; }
    return iconBody(k);
  }

  /* ---------------------------------------------------------------- 樣式（跟著這支檔走）*/
  const CSS = `
  .imwrap{position:relative;margin-top:var(--sp-2);border-radius:var(--r-md,16px);overflow:hidden;
    --im-sea:var(--bg-2);--im-sea2:color-mix(in srgb,var(--bg-2) 78%,var(--cyan));--im-grid:color-mix(in srgb,var(--cyan) 8%,transparent);
    --im-land:var(--panel-2);--im-land2:var(--panel);--im-shoal:color-mix(in srgb,var(--cyan) 22%,transparent);
    --im-road:var(--panel-3);--im-road-edge:color-mix(in srgb,var(--ink-3) 55%,transparent);--im-road-mark:color-mix(in srgb,var(--amber) 80%,transparent);
    --im-coast-w:1.4px;--im-tint:10%;--im-glow:0px;--im-blk-r:4px;--im-ink-blk:#fff}
  :root[data-theme="light"] .imwrap{--im-sea:color-mix(in srgb,var(--bg-2) 90%,var(--cyan));--im-sea2:var(--bg);--im-grid:color-mix(in srgb,var(--ink-3) 10%,transparent);
    --im-land:var(--panel);--im-land2:var(--panel-2);--im-shoal:color-mix(in srgb,var(--cyan) 28%,transparent);
    --im-road:#ffffff;--im-road-edge:color-mix(in srgb,var(--ink-3) 45%,transparent);--im-road-mark:color-mix(in srgb,var(--amber) 85%,var(--ink))}
  :root[data-theme4="casual"] .imwrap{--im-tint:16%;--im-blk-r:7px}
  :root[data-theme4="hud"] .imwrap{--im-glow:5px;--im-tint:8%;--im-grid:color-mix(in srgb,var(--cyan) 14%,transparent)}
  :root[data-theme4="pro"] .imwrap{--im-coast-w:2px;--im-tint:7%;--im-blk-r:2px}
  .imwrap svg{display:block;width:100%;height:auto;user-select:none;-webkit-user-select:none}
  .imwrap .im-sea{fill:var(--im-sea)}
  .imwrap .im-grid{stroke:var(--im-grid);stroke-width:1;fill:none}
  .imwrap .im-shoal{fill:none;stroke:var(--im-shoal);stroke-width:1;stroke-dasharray:2 5}
  .imwrap .im-land{fill:color-mix(in srgb,var(--rc) var(--im-tint),var(--im-land));stroke:color-mix(in srgb,var(--rc) 62%,transparent);
    stroke-width:var(--im-coast-w);cursor:pointer;transition:stroke var(--dur-fast,120ms)}
  :root[data-theme4="casual"] .imwrap .im-land{fill:url(#imLandG)}
  :root[data-theme4="hud"] .imwrap .im-land{fill:color-mix(in srgb,var(--rc) 9%,color-mix(in srgb,var(--im-land) 72%,transparent));
    filter:drop-shadow(0 0 var(--im-glow) color-mix(in srgb,var(--rc) 55%,transparent))}
  .imwrap .im-reg.hov .im-land,.imwrap .im-reg:focus-visible .im-land{stroke:var(--rc);stroke-width:2.4px}
  .imwrap .im-reg:focus{outline:none}
  .imwrap .im-plate{cursor:pointer}
  .imwrap .im-badge{fill:color-mix(in srgb,var(--rc) 22%,transparent);stroke:color-mix(in srgb,var(--rc) 70%,transparent);stroke-width:1}
  .imwrap .im-bico{color:var(--rc)}
  .imwrap .im-rname{fill:var(--ink);font-weight:700;font-size:14px}
  .imwrap .im-rstat{fill:var(--ink-2);font-size:12px;font-family:var(--mono);font-variant-numeric:tabular-nums}
  .imwrap .im-rstat .up{fill:var(--rise)} .imwrap .im-rstat .down{fill:var(--fall)}
  .imwrap .im-tier{fill:var(--ink-3);font-size:12px}
  .imwrap .im-river{stroke:color-mix(in srgb,var(--rc) 30%,transparent);stroke-width:1;stroke-dasharray:3 4}
  .imwrap .imb{cursor:pointer}
  .imwrap .imb rect.blk{rx:var(--im-blk-r);ry:var(--im-blk-r);transition:opacity var(--dur-fast,120ms)}
  .imwrap .imb .shine{display:none;pointer-events:none}
  :root[data-theme4="casual"] .imwrap .imb .shine{display:inline}
  :root[data-theme4="hud"] .imwrap .imb rect.blk{stroke:color-mix(in srgb,var(--cyan) 30%,transparent);stroke-width:1}
  .imwrap .imb text{fill:var(--im-ink-blk);pointer-events:none}
  .imwrap .imb .nm{font-size:12px;font-weight:600}
  .imwrap .imb .vl{font-size:12px;font-family:var(--mono);font-variant-numeric:tabular-nums;opacity:.92}
  .imwrap .imb .wm{color:var(--im-ink-blk);opacity:.24;pointer-events:none}
  .imwrap .imb .ic{color:var(--im-ink-blk);opacity:.9;pointer-events:none}
  .imwrap .imb.na text,.imwrap .imb.na .wm,.imwrap .imb.na .ic{fill:var(--ink);color:var(--ink)}
  .imwrap .imb.na text{fill:var(--ink)}
  .imwrap .imb:hover rect.blk,.imwrap .imb:focus-visible rect.blk,.imwrap .imb.hi rect.blk{stroke:var(--ink);stroke-width:2}
  .imwrap .imb:focus{outline:none}
  .imwrap .dim{opacity:.26}
  .imwrap .im-road{fill:none;stroke-linecap:round;stroke-linejoin:round;pointer-events:none}
  .imwrap .im-road.edge{stroke:var(--im-road-edge)}
  .imwrap .im-road.body{stroke:var(--im-road)}
  .imwrap .im-road.mark{stroke:var(--im-road-mark);stroke-dasharray:7 6;stroke-width:1.6}
  .imwrap .im-rd.share .im-road.body{stroke-dasharray:2 7}
  .imwrap .im-rd.share .im-road.mark{display:none}
  .imwrap .im-rd .hit{fill:none;stroke:transparent;stroke-width:22;cursor:help;pointer-events:stroke}
  .imwrap .im-rd.hov .im-road.edge{stroke:var(--cyan)}
  .imwrap .im-shield rect{fill:var(--panel);stroke:var(--im-road-mark);stroke-width:1.4}
  .imwrap .im-shield text{fill:var(--ink);font-size:12px;font-weight:700;font-family:var(--mono)}
  .imwrap .im-rd.share .im-shield rect{stroke:var(--im-road-edge);stroke-dasharray:2 2}
  .imtip{position:absolute;z-index:5;pointer-events:none;background:var(--tip-bg);border:1px solid var(--tip-line);box-shadow:var(--tip-sh);
    border-radius:10px;padding:12px 14px;max-width:320px;backdrop-filter:blur(8px)}
  .imfoot{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2) var(--sp-4);margin-top:var(--sp-2)}
  .imfoot .hmlegend{margin:0 0 0 auto}
  .imkeys{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-1) var(--sp-4);font-size:12px;color:var(--ink-3)}
  .imkeys i{display:inline-block;vertical-align:middle;width:26px;height:6px;border-radius:3px;margin-right:6px;background:var(--panel-3);
    box-shadow:0 0 0 1px color-mix(in srgb,var(--ink-3) 55%,transparent)}
  .imkeys i.sh{background:repeating-linear-gradient(90deg,var(--panel-3) 0 3px,transparent 3px 8px)}
  .imkeys .lk{margin-left:var(--sp-1)}
  .imhead .seg button{font-size:12.5px;padding:2px 10px}
  .imhead .imctl{gap:var(--sp-2);flex-wrap:wrap;align-items:center;margin-left:auto}
  .imhead .imlbl{font-size:12px;color:var(--ink-3);margin-right:-4px}
  .gplive .imview{margin-right:var(--sp-1)}
  .gplive .imview button{font-size:12.5px;padding:2px 10px}
  @media (prefers-reduced-motion:reduce){.imwrap *{transition:none!important}}
  `;
  function injectCss() {
    if (document.getElementById('indmap-css')) return;
    const st = document.createElement('style'); st.id = 'indmap-css'; st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  /* ---------------------------------------------------------------- 小工具 */
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  let mctx = null, fontFam = null;
  function measure(txt, px, weight, mono) {
    if (!mctx) mctx = document.createElement('canvas').getContext('2d');
    if (!fontFam) {
      const cs = getComputedStyle(document.body);
      fontFam = { sans: cs.fontFamily || 'sans-serif', mono: (cs.getPropertyValue('--mono') || 'monospace').trim() };
    }
    mctx.font = `${weight || 400} ${px}px ${mono ? fontFam.mono : fontFam.sans}`;
    return mctx.measureText(String(txt)).width;
  }
  /* 放得下就整串、放不下就截成「前 N 字…」，連兩個字都放不下就回空字串（不要印殘字） */
  function fitText(txt, maxW, px, weight, mono) {
    txt = String(txt || '');
    if (maxW <= 0) return '';
    if (measure(txt, px, weight, mono) <= maxW) return txt;
    for (let n = txt.length - 1; n >= 2; n--) {
      const t = txt.slice(0, n).replace(/\s+$/, '') + '…';
      if (measure(t, px, weight, mono) <= maxW) return t;
    }
    return '';
  }
  // 決定性亂數（同一個區域每次畫都長一樣的海岸線，不會每次重畫就抖一下）
  function seeded(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return () => { h ^= h << 13; h ^= h >>> 17; h ^= h << 5; return ((h >>> 0) % 10000) / 10000; };
  }

  /* 方塊樹狀圖（squarified）：items 的 v 已經是「面積權重」。回傳 [{item,x,y,w,h}] */
  function squarify(items, x, y, w, h) {
    const out = [];
    const list = items.filter(d => d.v > 0).slice().sort((a, b) => b.v - a.v);
    const total = list.reduce((s, d) => s + d.v, 0);
    if (!list.length || w <= 0 || h <= 0 || total <= 0) return out;
    const scale = (w * h) / total;
    let rest = list.map(d => ({ d, a: d.v * scale }));
    let rx = x, ry = y, rw = w, rh = h;
    const worst = (row, side) => {
      const s = row.reduce((t, r) => t + r.a, 0);
      let mx = 0, mn = Infinity;
      row.forEach(r => { mx = Math.max(mx, r.a); mn = Math.min(mn, r.a); });
      return Math.max((side * side * mx) / (s * s), (s * s) / (side * side * mn));
    };
    while (rest.length) {
      const side = Math.min(rw, rh);
      let row = [rest[0]], i = 1;
      while (i < rest.length && worst(row.concat(rest[i]), side) <= worst(row, side)) { row.push(rest[i]); i++; }
      rest = rest.slice(i);
      const s = row.reduce((t, r) => t + r.a, 0);
      if (rw >= rh) {           // 直的一欄貼左邊
        const cw = rest.length ? s / rh : rw;
        let cy = ry;
        row.forEach((r, k) => { const ch = k === row.length - 1 ? ry + rh - cy : r.a / cw; out.push({ item: r.d, x: rx, y: cy, w: cw, h: ch }); cy += ch; });
        rx += cw; rw -= cw;
      } else {                  // 橫的一列貼上面
        const chh = rest.length ? s / rw : rh;
        let cx = rx;
        row.forEach((r, k) => { const cw2 = k === row.length - 1 ? rx + rw - cx : r.a / chh; out.push({ item: r.d, x: cx, y: ry, w: cw2, h: chh }); cx += cw2; });
        ry += chh; rh -= chh;
      }
    }
    return out;
  }

  /* 海岸線：沿著圓角矩形外擴 base px，再疊兩個正弦波讓它不規則（但永遠在矩形外面，不會蓋到街區）*/
  function coastPath(r, base, amp, seed, R) {
    const rnd = seeded(seed);
    const p1 = rnd() * 6.28, p2 = rnd() * 6.28, k1 = 3 + Math.floor(rnd() * 3), k2 = 7 + Math.floor(rnd() * 4);
    R = Math.min(R, r.w / 2, r.h / 2);
    const segs = [
      { len: r.w - 2 * R, f: (t) => [r.x + R + t * (r.w - 2 * R), r.y, 0, -1] },
      { len: Math.PI * R / 2, f: (t) => { const a = -Math.PI / 2 + t * Math.PI / 2; return [r.x + r.w - R + R * Math.cos(a), r.y + R + R * Math.sin(a), Math.cos(a), Math.sin(a)]; } },
      { len: r.h - 2 * R, f: (t) => [r.x + r.w, r.y + R + t * (r.h - 2 * R), 1, 0] },
      { len: Math.PI * R / 2, f: (t) => { const a = t * Math.PI / 2; return [r.x + r.w - R + R * Math.cos(a), r.y + r.h - R + R * Math.sin(a), Math.cos(a), Math.sin(a)]; } },
      { len: r.w - 2 * R, f: (t) => [r.x + r.w - R - t * (r.w - 2 * R), r.y + r.h, 0, 1] },
      { len: Math.PI * R / 2, f: (t) => { const a = Math.PI / 2 + t * Math.PI / 2; return [r.x + R + R * Math.cos(a), r.y + r.h - R + R * Math.sin(a), Math.cos(a), Math.sin(a)]; } },
      { len: r.h - 2 * R, f: (t) => [r.x, r.y + r.h - R - t * (r.h - 2 * R), -1, 0] },
      { len: Math.PI * R / 2, f: (t) => { const a = Math.PI + t * Math.PI / 2; return [r.x + R + R * Math.cos(a), r.y + R + R * Math.sin(a), Math.cos(a), Math.sin(a)]; } },
    ];
    const per = segs.reduce((s, g) => s + Math.max(0, g.len), 0);
    const n = Math.max(24, Math.round(per / 16));
    const pts = [];
    let acc = 0, si = 0;
    for (let i = 0; i < n; i++) {
      const target = (i / n) * per;
      while (si < segs.length - 1 && acc + Math.max(0, segs[si].len) < target) { acc += Math.max(0, segs[si].len); si++; }
      const g = segs[si], t = g.len > 0 ? (target - acc) / g.len : 0;
      const [px, py, nx, ny] = g.f(clamp(t, 0, 1));
      const u = i / n;
      const off = base + amp * (0.6 * Math.sin(6.283 * k1 * u + p1) + 0.4 * Math.sin(6.283 * k2 * u + p2));
      pts.push([px + nx * off, py + ny * off]);
    }
    // Catmull-Rom → 三次貝茲，封閉
    let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
    for (let i = 0; i < pts.length; i++) {
      const p0 = pts[(i - 1 + pts.length) % pts.length], p1_ = pts[i], p2_ = pts[(i + 1) % pts.length], p3 = pts[(i + 2) % pts.length];
      const c1x = p1_[0] + (p2_[0] - p0[0]) / 6, c1y = p1_[1] + (p2_[1] - p0[1]) / 6;
      const c2x = p2_[0] - (p3[0] - p1_[0]) / 6, c2y = p2_[1] - (p3[1] - p1_[1]) / 6;
      d += `C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2_[0].toFixed(1)},${p2_[1].toFixed(1)}`;
    }
    return d + 'Z';
  }

  /* ---------------------------------------------------------------- 資料 → 模型 */
  const REGION_ROWS = [['semiconductor', 'ai_server', 'electronics'], ['industry', 'infrastructure', 'traditional', 'financial', 'software']];
  const IND_TOP = 11;          // 法定產業別島上最多放幾個產業，其餘併成一塊「其餘 N 個」

  function buildModel(ctx) {
    const im = ctx.im || {}, sc = ctx.sc || null, gt = ctx.gt || [], flow = ctx.flow || null;
    const tierOf = {}, udOf = {};
    (gt || []).forEach(r => { tierOf[r.group_id] = r.tier; udOf[r.group_id] = [r.advancers, r.decliners]; });
    const regions = [];
    const regOf = {};
    (im.chains || []).forEach(c => {
      const gs = (c.groups || []).filter(g => (g.turnover || 0) > 0);
      regions.push({ id: c.id, name: c.name, groups: gs, href: '#industry/' + c.id });
    });
    if ((im.industries || []).length) {
      const all = im.industries.filter(g => (g.turnover || 0) > 0).slice().sort((a, b) => b.turnover - a.turnover);
      const top = all.slice(0, IND_TOP), rest = all.slice(IND_TOP);
      const gs = top.slice();
      if (rest.length) {
        const to = rest.reduce((s, g) => s + (g.turnover || 0), 0);
        gs.push({ id: '_ind_rest', name: `其餘 ${rest.length} 個產業`, chain: 'industry', n: rest.reduce((s, g) => s + (g.n || 0), 0),
          turnover: to, turnover_share: rest.reduce((s, g) => s + (g.turnover_share || 0), 0),
          chg_pct: to > 0 ? rest.reduce((s, g) => s + (g.chg_pct || 0) * (g.turnover || 0), 0) / to : null, _rest: rest.length });
      }
      regions.push({ id: 'industry', name: '法定產業別', groups: gs, href: '#industry/industry', allN: all.length });
    }
    regions.forEach(r => {
      regOf[r.id] = r;
      r.turnover = r.groups.reduce((s, g) => s + (g.turnover || 0), 0);
      r.share = r.groups.reduce((s, g) => s + (g.turnover_share || 0), 0);
      r.chg = r.turnover > 0 ? r.groups.reduce((s, g) => s + (g.chg_pct || 0) * (g.turnover || 0), 0) / r.turnover : null;
      r.up = r.groups.filter(g => (g.chg_pct || 0) > 0).length;
      r.down = r.groups.filter(g => (g.chg_pct || 0) < 0).length;
      r.groups.forEach(g => {
        g._tier = tierOf[g.id] || (r.id === 'industry' ? 'standalone' : 'standalone');
        g._ud = udOf[g.id] || null;
        g._icon = g._rest ? 'box' : groupIcon(g);
        g._region = r.id;
      });
    });
    regions.sort((a, b) => b.turnover - a.turnover);

    /* ---- 道路：只畫資料裡真的有的跨區關係 ---- */
    const gidChain = {}, codeGroups = {}, gname = {};
    regions.forEach(r => r.groups.forEach(g => { gidChain[g.id] = r.id; gname[g.id] = g.name; }));
    (im.chains || []).forEach(c => (c.groups || []).forEach(g => (g.members || []).forEach(m => {
      (codeGroups[m.code] = codeGroups[m.code] || []).push({ gid: g.id, chain: c.id, name: m.name });
    })));
    const roads = {};
    const keyOf = (a, b) => (a < b ? a + '|' + b : b + '|' + a);
    const road = (a, b) => { const k = keyOf(a, b); return roads[k] || (roads[k] = { key: k, a: k.split('|')[0], b: k.split('|')[1], supply: [], shared: [], gids: new Set() }); };
    if (sc && sc.companies && sc.edges) {
      const segChain = {};
      (sc.segments || []).forEach(s => { segChain[s.id] = s.chain; });
      const co = {};
      sc.companies.forEach(c => { co[c.id] = c; });
      const sideOf = (c) => {
        if (!c) return null;
        const code = c.tw_code || null;
        const gs = code && codeGroups[code] ? codeGroups[code] : [];
        if (gs.length) return { chains: [...new Set(gs.map(x => x.chain))], gids: gs.map(x => x.gid), name: c.name };
        const ch = segChain[c.segment];
        return ch ? { chains: [ch], gids: [], name: c.name } : null;
      };
      sc.edges.forEach(e => {
        const A_ = sideOf(co[e.from]), B_ = sideOf(co[e.to]);
        if (!A_ || !B_) return;
        // 一邊同時在兩區（例：鴻海）時，取「跟對面不同的那一區」—— 同區的邊不算道路
        let pair = null;
        for (const ca of A_.chains) { for (const cb of B_.chains) { if (ca !== cb && regOf[ca] && regOf[cb]) { pair = [ca, cb]; break; } } if (pair) break; }
        if (!pair) return;
        const rd = road(pair[0], pair[1]);
        rd.supply.push({ from: A_.name, to: B_.name, item: e.item || '' });
        A_.gids.concat(B_.gids).forEach(g => { if (gidChain[g] === pair[0] || gidChain[g] === pair[1]) rd.gids.add(g); });
      });
    }
    Object.keys(codeGroups).forEach(code => {
      const gs = codeGroups[code];
      const chs = [...new Set(gs.map(x => x.chain))].filter(c => regOf[c]);
      for (let i = 0; i < chs.length; i++) for (let j = i + 1; j < chs.length; j++) {
        const rd = road(chs[i], chs[j]);
        const ga = gs.find(x => x.chain === chs[i]), gb = gs.find(x => x.chain === chs[j]);
        rd.shared.push({ code, name: gs[0].name, ga: gname[ga.gid] || ga.gid, gb: gname[gb.gid] || gb.gid });
        gs.forEach(x => rd.gids.add(x.gid));
      }
    });
    const model = { regions, regOf, roads: Object.values(roads), date: im.date || '', hasFlow: false };
    applyFlow(model, flow);
    return model;
  }
  /* 資金熱度（flow_v3.periods 的 w0＝本週 vs 上週的成交占比差，pp）寫進既有模型 —— 就地改，
     不重建（重建會把畫好的街區座標丟掉，滑過就找不到方塊）。*/
  function applyFlow(model, flow) {
    const flowOf = {};
    if (flow && flow.periods) {
      const p = flow.periods.find(x => x.key === 'w0') || flow.periods[0];
      if (p) (p.groups || []).forEach(g => { flowOf[g.group_id] = g.share_chg; });
    }
    model.hasFlow = Object.keys(flowOf).length > 0;
    model.regions.forEach(r => {
      r.groups.forEach(g => { g._flow = g._rest ? null : (flowOf[g.id] != null ? flowOf[g.id] : null); });
      const fl = r.groups.map(g => g._flow).filter(v => v != null && Number.isFinite(+v));
      r.flow = fl.length ? fl.reduce((s, v) => s + v, 0) : null;
    });
  }

  /* ---------------------------------------------------------------- 版面：區域落點 */
  function blockVal(g, mode, floor) {
    const t = Math.max(0, g.turnover || 0);
    return mode === 'lin' ? Math.max(t, floor) : Math.sqrt(t);
  }
  function layoutRegions(model, W, H, mode) {
    const PAD = 16, G = Math.max(40, Math.round(W * 0.036));      // G＝區域之間的水道（道路從這裡過）
    const total = model.regions.reduce((s, r) => s + r.turnover, 0) || 1;
    const floor = total * 0.0012;
    model.regions.forEach(r => { r.weight = r.groups.reduce((s, g) => s + blockVal(g, mode, floor), 0); r._floor = floor; });
    const rows = REGION_ROWS.map(ids => ids.map(id => model.regOf[id]).filter(Boolean));
    // 不在預設排法裡的新鏈（日後 groups.yaml 新增）一律接在第二列尾巴
    model.regions.forEach(r => { if (!REGION_ROWS.some(ids => ids.indexOf(r.id) >= 0)) rows[1].push(r); });
    const rw = rows.map(rs => rs.reduce((s, r) => s + r.weight, 0));
    const innerH = H - PAD * 2 - G;
    let f1 = rw[0] / ((rw[0] + rw[1]) || 1);
    f1 = clamp(f1, 0.58, 0.7);
    const hs = rows[1].length ? [Math.round(innerH * f1), innerH - Math.round(innerH * f1)] : [innerH, 0];
    let y = PAD;
    rows.forEach((rs, ri) => {
      if (!rs.length) return;
      const avail = W - PAD * 2 - G * (rs.length - 1);
      const minW = Math.min(ri === 0 ? 220 : 150, avail / rs.length);
      // 先依權重分，再把太窄的補到最小寬，多出來的從寬的那幾塊等比扣回來
      let ws = rs.map(r => avail * r.weight / (rw[ri] || 1));
      for (let k = 0; k < 4; k++) {
        const short = ws.reduce((s, w) => s + Math.max(0, minW - w), 0);
        if (short <= 0.5) break;
        const bigSum = ws.reduce((s, w) => s + (w > minW ? w - minW : 0), 0) || 1;
        ws = ws.map(w => (w < minW ? minW : w - (w - minW) * short / bigSum));
      }
      let x = PAD;
      rs.forEach((r, i) => { r.rect = { x, y, w: ws[i], h: hs[ri] }; r.row = ri; r.col = i; x += ws[i] + G; });
      y += hs[ri] + G;
    });
    return { PAD, G };
  }

  /* 區域裡的街區：上游→中游→下游 分欄（有兩種以上 tier 才分），每欄再做方塊樹狀圖 */
  function layoutBlocks(r, mode) {
    const R = r.rect;
    const headH = R.w < 230 ? 46 : 34;
    r.headH = headH;
    const inset = 10;
    const area = { x: R.x + inset, y: R.y + headH + 4, w: R.w - inset * 2, h: R.h - headH - 4 - inset };
    const items = r.groups.map(g => ({ g, v: blockVal(g, mode, r._floor) }));
    const tiers = [...new Set(items.map(d => d.g._tier))].filter(t => t !== 'standalone');
    r.cols = [];
    let parts;
    if (tiers.length >= 2 && r.id !== 'industry') {
      const byT = {};
      items.forEach(d => { const t = d.g._tier === 'standalone' ? 'midstream' : d.g._tier; (byT[t] = byT[t] || []).push(d); });
      const ts = Object.keys(byT).sort((a, b) => TIER_ORD[a] - TIER_ORD[b]);
      const sum = items.reduce((s, d) => s + d.v, 0) || 1;
      const GAP = 8, avail = area.w - GAP * (ts.length - 1);
      let ws = ts.map(t => avail * byT[t].reduce((s, d) => s + d.v, 0) / sum);
      const minW = Math.min(72, avail / ts.length);      // 窄的島（1100 寬的一般電子）三欄放不下 72，就平分
      for (let k = 0; k < 3; k++) {
        const short = ws.reduce((s, w) => s + Math.max(0, minW - w), 0);
        if (short <= 0.5) break;
        const bigSum = ws.reduce((s, w) => s + (w > minW ? w - minW : 0), 0) || 1;
        ws = ws.map(w => (w < minW ? minW : w - (w - minW) * short / bigSum));
      }
      let x = area.x;
      parts = ts.map((t, i) => { const p = { tier: t, x, w: ws[i], items: byT[t] }; x += ws[i] + GAP; return p; });
      r.cols = parts.map(p => ({ tier: p.tier, x: p.x, w: p.w }));
    } else {
      parts = [{ tier: null, x: area.x, w: area.w, items }];
    }
    r.blocks = [];
    parts.forEach(p => {
      squarify(p.items, p.x, area.y, p.w, area.h).forEach(c => {
        const S = 1.5;          // 街道寬 3px ＝ 每塊內縮 1.5
        r.blocks.push({ g: c.item.g, x: c.x + S, y: c.y + S, w: Math.max(0, c.w - 2 * S), h: Math.max(0, c.h - 2 * S) });
      });
    });
    r.area = area;
  }

  /* 兩個區域之間的道路幾何 */
  function roadGeom(ra, rb, G) {
    const A_ = ra.rect, B_ = rb.rect;
    const ovX = [Math.max(A_.x, B_.x), Math.min(A_.x + A_.w, B_.x + B_.w)];
    const ovY = [Math.max(A_.y, B_.y), Math.min(A_.y + A_.h, B_.y + B_.h)];
    const left = A_.x < B_.x ? A_ : B_, right = left === A_ ? B_ : A_;
    if (ra.row === rb.row && Math.abs(ra.col - rb.col) === 1 && ovY[1] - ovY[0] > 40) {
      const y = ovY[0] + (ovY[1] - ovY[0]) * 0.42;
      const x1 = left.x + left.w - 4, x2 = right.x + 4;
      return { d: `M${x1},${y} L${x2},${y}`, mx: (x1 + x2) / 2, my: y };
    }
    if (ra.row !== rb.row && ovX[1] - ovX[0] > 40) {
      const top = A_.y < B_.y ? A_ : B_, bot = top === A_ ? B_ : A_;
      const x = ovX[0] + (ovX[1] - ovX[0]) * 0.5;
      const y1 = top.y + top.h - 4, y2 = bot.y + 4;
      return { d: `M${x},${y1} L${x},${y2}`, mx: x, my: (y1 + y2) / 2 };
    }
    // 同一列但不相鄰（例：半導體 ↔ 一般電子）→ 走兩列之間的水道，繞過中間那一塊
    if (ra.row === rb.row) {
      const yb = A_.y + A_.h;                         // 同列等高
      const yc = yb + G * 0.5;
      const x1 = left.x + left.w * 0.86, x2 = right.x + right.w * 0.14, r_ = Math.min(14, G * 0.4);
      return { d: `M${x1},${yb - 4} L${x1},${yc - r_} Q${x1},${yc} ${x1 + r_},${yc} L${x2 - r_},${yc} Q${x2},${yc} ${x2},${yc - r_} L${x2},${yb - 4}`,
        mx: (x1 + x2) / 2, my: yc };
    }
    // 不同列、沒有重疊 → S 形
    const top = A_.y < B_.y ? A_ : B_, bot = top === A_ ? B_ : A_;
    const x1 = clamp(bot.x + bot.w / 2, top.x + 20, top.x + top.w - 20), y1 = top.y + top.h - 4;
    const x2 = clamp(top.x + top.w / 2, bot.x + 20, bot.x + bot.w - 20), y2 = bot.y + 4;
    const yc = (y1 + y2) / 2;
    return { d: `M${x1},${y1} C${x1},${yc} ${x2},${yc} ${x2},${y2}`, mx: (x1 + x2) / 2, my: yc };
  }

  /* ---------------------------------------------------------------- 畫 */
  const BIN_VAR = ['--hm-n3', '--hm-n2', '--hm-n1', '--hm-0', '--hm-p1', '--hm-p2', '--hm-p3'];
  let cur = null;      // 目前畫面上那一張地圖的狀態（驗收讀它）
  let fitOff = null;   // 目前那張地圖的 Fit.on 訂閱（換頁重畫時先取消上一張的）

  function valOf(g, colorMode) { return colorMode === 'flow' ? g._flow : g.chg_pct; }
  function binOf(v, colorMode) {
    const A = window.App;
    if (A && A.hmBin) return A.hmBin(v, colorMode === 'flow' ? 'flow' : 'chg');
    return -1;
  }
  function fmtVal(v, colorMode) {
    const A = window.App;
    if (v == null || !Number.isFinite(+v)) return '—';
    if (colorMode === 'flow') { const r = Math.round(v * 100) / 100; return (r > 0 ? '+' : '') + r.toFixed(2) + 'pp'; }
    return A ? A.fmt.pct(v, 1) : (v > 0 ? '+' : '') + (+v).toFixed(1) + '%';
  }
  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    if (attrs) for (const k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function iconG(parent, key, x, y, size, cls, sw) {
    const g = el('g', { class: cls, transform: `translate(${x.toFixed(1)},${y.toFixed(1)}) scale(${(size / 24).toFixed(3)})`,
      fill: 'none', stroke: 'currentColor', 'stroke-width': sw || 1.8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, parent);
    g.innerHTML = iconSvg(key);
    return g;
  }

  function draw(svg, model, opt) {
    const W = opt.W, H = opt.H, colorMode = opt.color, sizeMode = opt.size, focus = opt.focus;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('width', W); svg.setAttribute('height', H);
    svg.innerHTML = '';
    const { G } = layoutRegions(model, W, H, sizeMode);
    model.regions.forEach(r => layoutBlocks(r, sizeMode));

    const defs = el('defs', null, svg);
    defs.innerHTML = `<radialGradient id="imSeaG" cx="50%" cy="45%" r="75%"><stop offset="0" style="stop-color:var(--im-sea2)"/><stop offset="1" style="stop-color:var(--im-sea)"/></radialGradient>
      <linearGradient id="imLandG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:color-mix(in srgb,var(--cyan) 12%,var(--im-land2))"/><stop offset="1" style="stop-color:var(--im-land)"/></linearGradient>
      <linearGradient id="imShine" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient>
      <pattern id="imGridP" width="44" height="44" patternUnits="userSpaceOnUse"><path class="im-grid" d="M44 0H0V44"/></pattern>`;
    el('rect', { class: 'im-sea', x: 0, y: 0, width: W, height: H, fill: 'url(#imSeaG)' }, svg);
    el('rect', { x: 0, y: 0, width: W, height: H, fill: 'url(#imGridP)', 'pointer-events': 'none' }, svg);

    // 淺灘線（海岸外一圈虛線）
    const gShoal = el('g', { 'pointer-events': 'none' }, svg);
    model.regions.forEach(r => el('path', { class: 'im-shoal', d: coastPath(r.rect, 15, 3, r.id + 's', 22) }, gShoal));

    // 道路：在島的下面（橋頭鑽進海岸線底下），盾牌數字在最上面另外畫
    const gRoads = el('g', { class: 'im-roads' }, svg);
    const shields = [];
    const roads = model.roads.filter(rd => model.regOf[rd.a] && model.regOf[rd.b] && model.regOf[rd.a].rect && model.regOf[rd.b].rect);
    roads.forEach(rd => {
      const geo = roadGeom(model.regOf[rd.a], model.regOf[rd.b], G);
      const share = !rd.supply.length;
      const n = rd.supply.length || rd.shared.length;
      const w = clamp(5 + Math.log2(n + 1) * 2.2, 6, 15);
      const g = el('g', { class: 'im-rd' + (share ? ' share' : ''), 'data-road': rd.key }, gRoads);
      el('path', { class: 'im-road edge', d: geo.d, 'stroke-width': w + 3 }, g);
      el('path', { class: 'im-road body', d: geo.d, 'stroke-width': w }, g);
      el('path', { class: 'im-road mark', d: geo.d }, g);
      rd._g = g; rd._geo = geo; rd._w = w;
      shields.push(rd);
    });

    // 區域（島）
    const gRegs = el('g', { class: 'im-regs' }, svg);
    model.regions.forEach(r => {
      const g = el('g', { class: 'im-reg', 'data-cid': r.id, style: `--rc:${CHAIN_TINT[r.id] || 'var(--ink-3)'}`, tabindex: 0, role: 'link',
        'aria-label': `${r.name}：成交值 ${fmtYi(r.turnover)}、加權漲跌 ${fmtVal(r.chg, 'chg')}，點一下進入這條產業鏈` }, gRegs);
      r._g = g;
      el('path', { class: 'im-land', d: coastPath(r.rect, 7, 3.2, r.id, 20) }, g);
      // 標題牌：圖示徽章＋名稱＋數字
      const R = r.rect, plate = el('g', { class: 'im-plate' }, g);
      const bx = R.x + 10, by = R.y + 8, bs = 24;
      el('rect', { class: 'im-badge', x: bx, y: by, width: bs, height: bs, rx: 6 }, plate);
      iconG(plate, CHAIN_ICON[r.id] || 'island', bx + 4, by + 4, 16, 'im-bico', 2);
      const nameX = bx + bs + 8;
      const v = colorMode === 'flow' ? r.flow : r.chg;
      const stat = `${fmtVal(v, colorMode)} · ${fmtYi(r.turnover)}`;
      const tierCap = r.cols.length >= 2 ? '上游 → 下游' : '';
      if (r.headH > 40) {       // 窄的島：兩行
        const nm = fitText(r.name, R.x + R.w - 10 - nameX, 14, 700);
        el('text', { class: 'im-rname', x: nameX, y: by + 12, 'dominant-baseline': 'middle' }, plate).textContent = nm;
        const st = el('text', { class: 'im-rstat', x: bx, y: by + bs + 9, 'dominant-baseline': 'middle' }, plate);
        st.innerHTML = `<tspan class="${clsUD(v)}">${esc(fmtVal(v, colorMode))}</tspan><tspan> · ${esc(fmtYi(r.turnover))}</tspan>`;
        if (measure(stat, 12, 400, true) > R.w - 20) st.innerHTML = `<tspan class="${clsUD(v)}">${esc(fmtVal(v, colorMode))}</tspan>`;
      } else {
        const nmW = measure(r.name, 14, 700);
        el('text', { class: 'im-rname', x: nameX, y: by + 12, 'dominant-baseline': 'middle' }, plate).textContent = r.name;
        const sx = nameX + nmW + 10;
        const st = el('text', { class: 'im-rstat', x: sx, y: by + 12, 'dominant-baseline': 'middle' }, plate);
        const extra = `${r.groups.length} 個${r.id === 'industry' ? '產業' : '族群'}`;
        const full = `${stat} · ${extra}`;
        const room = R.x + R.w - 10 - sx - (tierCap ? measure(tierCap, 12) + 14 : 0);
        const txt = measure(full, 12, 400, true) <= room ? full : (measure(stat, 12, 400, true) <= room ? stat : fmtVal(v, colorMode));
        st.innerHTML = `<tspan class="${clsUD(v)}">${esc(fmtVal(v, colorMode))}</tspan>${esc(txt.slice(fmtVal(v, colorMode).length))}`;
        if (tierCap && room > 40) el('text', { class: 'im-tier', x: R.x + R.w - 10, y: by + 12, 'text-anchor': 'end', 'dominant-baseline': 'middle' }, plate).textContent = tierCap;
      }
      // 上中下游之間的分隔「河」
      r.cols.slice(1).forEach(c => el('line', { class: 'im-river', x1: c.x - 4, x2: c.x - 4, y1: r.area.y, y2: r.area.y + r.area.h }, g));
      // 街區
      r.blocks.forEach(b => drawBlock(g, b, r, colorMode, focus));
    });

    // 道路盾牌（數字）畫在最上層，才不會被島蓋掉
    const gSh = el('g', { class: 'im-shields' }, svg);
    shields.forEach(rd => {
      const n = rd.supply.length || rd.shared.length;
      const t = String(n), tw = Math.max(22, measure(t, 12, 700, true) + 12);
      const sg = el('g', { class: 'im-shield', transform: `translate(${(rd._geo.mx - tw / 2).toFixed(1)},${(rd._geo.my - 10).toFixed(1)})` }, gSh);
      el('rect', { width: tw, height: 20, rx: 6 }, sg);
      el('text', { x: tw / 2, y: 10.5, 'text-anchor': 'middle', 'dominant-baseline': 'middle' }, sg).textContent = t;
      // 命中區（透明的粗線＋盾牌本身）放在盾牌層，滑過道路任何一段都有提示
      const hit = el('path', { class: 'hit', d: rd._geo.d }, rd._g);
      hit.dataset.road = rd.key; sg.dataset.road = rd.key; sg.style.cursor = 'help';
      rd._sh = sg;
    });
    return { roads };
  }
  function clsUD(v) { return v > 0 ? 'up' : v < 0 ? 'down' : ''; }
  function fmtYi(v) { const A = window.App; return A ? A.fmt.yi(v) : String(Math.round((v || 0) / 1e8)) + ' 億'; }

  /* 名稱折兩行：第一行塞到滿（盡量斷在空白），第二行放不下就截「…」。回傳 [第一行, 第二行]。*/
  function wrap2(txt, w1, w2, px, wt) {
    txt = String(txt || '');
    let n = 0;
    for (let k = 1; k <= txt.length; k++) { if (measure(txt.slice(0, k), px, wt) <= w1) n = k; else break; }
    if (n < 2) return ['', ''];
    const sp = txt.lastIndexOf(' ', n);
    if (sp >= Math.max(2, n - 4) && sp < n) n = sp;
    const l1 = txt.slice(0, n).trim(), rest = txt.slice(n).trim();
    if (!rest) return [l1, ''];
    const l2 = fitText(rest, w2, px, wt);
    return l2 ? [l1, l2] : [fitText(txt, w1, px, wt), ''];
  }

  function drawBlock(parent, b, r, colorMode, focus) {
    const g0 = b.g;
    if (b.w < 2 || b.h < 2) return;
    const v = valOf(g0, colorMode), bin = binOf(v, colorMode);
    const na = bin < 0;
    const href = g0._rest ? '#industry/industry' : '#industry/group/' + g0.id;
    const g = el('g', { class: 'imb' + (na ? ' na' : '') + (focus != null && focus !== bin ? ' dim' : ''), 'data-gid': g0.id, 'data-bin': bin,
      'data-href': href, tabindex: 0, role: 'link',
      'aria-label': `${g0.name}：${colorMode === 'flow' ? '資金熱度' : '漲跌'} ${fmtVal(v, colorMode)}，成交值 ${fmtYi(g0.turnover)}` }, parent);
    b._g = g;
    el('rect', { class: 'blk', x: b.x.toFixed(1), y: b.y.toFixed(1), width: b.w.toFixed(1), height: b.h.toFixed(1),
      style: `fill:var(${na ? '--hm-na' : BIN_VAR[bin]})` }, g);
    el('rect', { class: 'shine', x: b.x.toFixed(1), y: b.y.toFixed(1), width: b.w.toFixed(1), height: (b.h * 0.6).toFixed(1), rx: 6, fill: 'url(#imShine)' }, g);
    const mn = Math.min(b.w, b.h);
    const P = 6, LH = 16;
    const valTxt = fmtVal(v, colorMode);
    const budget = Math.floor((b.h - P * 2 + 3) / LH);       // 這一塊直的能放幾行字
    b.label = '';
    if (b.w >= 30 && budget >= 1) {
      const px = b.w >= 150 && b.h >= 100 ? 13 : 12;          // 大地標的名字大一號
      const wmOK = mn >= 46;                                   // 夠大 → 右下角一枚淡淡的大圖示（地標）
      const icoW = !wmOK && b.w >= 46 ? 17 : 0;                // 不夠大 → 名稱前面一枚小圖示
      const w1 = b.w - P * 2 - icoW, wAll = b.w - P * 2;
      let lines;
      if (measure(g0.name, px, 600) <= w1) lines = [g0.name];
      else if (budget >= 2) lines = wrap2(g0.name, w1, wAll, px, 600).filter(Boolean);
      else lines = [fitText(g0.name, w1, px, 600)].filter(Boolean);
      if (!lines.length && icoW) lines = [];
      // 名稱一個字都放不下、只剩小圖示時：數字跟圖示同一行（放得下才放），不要多吃一行
      const inlineVal = !lines.length && icoW && measure(valTxt, 12, 400, true) <= w1;
      const showVal = !inlineVal && lines.length > 0 && budget >= lines.length + 1 && measure(valTxt, 12, 400, true) <= wAll;
      let tr = 0;
      if (icoW) iconG(g, g0._icon, b.x + P, b.y + P + (LH - 13) / 2 - 1, 13, 'ic', 2);
      lines.forEach((t, i) => {
        const x = b.x + P + (i === 0 ? icoW : 0);
        const tx = el('text', { class: 'nm', x, y: b.y + P + 7 + i * LH, 'dominant-baseline': 'middle', style: px !== 12 ? `font-size:${px}px` : null }, g);
        tx.textContent = t;
        tr = Math.max(tr, (i === 0 ? icoW : 0) + measure(t, px, 600));
      });
      if (inlineVal) { el('text', { class: 'vl', x: b.x + P + icoW, y: b.y + P + 7, 'dominant-baseline': 'middle' }, g).textContent = valTxt; tr = icoW + measure(valTxt, 12, 400, true); }
      let nl = lines.length || (icoW ? 1 : 0);
      if (showVal) { el('text', { class: 'vl', x: b.x + P, y: b.y + P + 7 + nl * LH, 'dominant-baseline': 'middle' }, g).textContent = valTxt; tr = Math.max(tr, measure(valTxt, 12, 400, true)); nl++; }
      b.label = lines.join('');
      if (wmOK) {
        const textB = P + nl * LH, textR = P + tr;
        let s = clamp(mn * 0.5, 22, 60);
        // 圖示不要壓到字：右邊有空位或下面有空位才放；都不夠就縮小，縮到 20 以下就不放
        if (!(b.w - textR - 6 >= s || b.h - textB - 6 >= s)) s = Math.max(b.w - textR - 6, b.h - textB - 6);
        if (s >= 20) iconG(g, g0._icon, b.x + b.w - s - 5, b.y + b.h - s - 5, s, 'wm', 1.6);
      } else if (!icoW && b.h - (P + nl * LH) >= 22) {
        // 窄而高的方塊（名稱前放不下小圖示）：圖示放到下面的空位
        const s = Math.min(16, b.w - 8);
        if (s >= 12) iconG(g, g0._icon, b.x + (b.w - s) / 2, b.y + b.h - s - 6, s, 'ic', 2);
      }
      if (lines.length || icoW) return;
    }
    // 小方塊：只放圖示（再小就什麼都不放 —— 滑過一樣有提示）
    if (mn >= 15) { const s = Math.min(14, mn - 4); iconG(g, g0._icon, b.x + (b.w - s) / 2, b.y + (b.h - s) / 2, s, 'ic', 2); }
  }
  /* ---------------------------------------------------------------- 提示框 */
  function tipHtml(kind, obj, colorMode) {
    const A = window.App;
    const T = (title, sub, rows, foot) => (A && A.hmTip ? A.hmTip(title, sub, rows, foot) : `<b>${esc(title)}</b>`);
    if (kind === 'block') {
      const g = obj;
      const ud = g._ud ? `${g._ud[0] != null ? g._ud[0] : '—'} 漲 ／ ${g._ud[1] != null ? g._ud[1] : '—'} 跌` : null;
      const rows = [
        { k: '漲跌幅', v: fmtVal(g.chg_pct, 'chg'), c: A ? A.upDown(g.chg_pct) : null, dot: colorMode === 'chg' ? `var(${BIN_VAR[binOf(g.chg_pct, 'chg')] || '--hm-na'})` : null },
        { k: '成交值', v: `${fmtYi(g.turnover)}（${g.turnover_share != null ? (+g.turnover_share).toFixed(2) : '—'}%）` },
      ];
      if (!g._rest && cur && cur.model.hasFlow) rows.push({ k: '資金熱度', v: g._flow != null ? fmtVal(g._flow, 'flow') : '—', c: A && g._flow != null ? A.upDown(g._flow) : null,
        dot: colorMode === 'flow' ? `var(${BIN_VAR[binOf(g._flow, 'flow')] || '--hm-na'})` : null });
      rows.push({ k: g._rest ? '涵蓋' : '成分股', v: g._rest ? `${g._rest} 個產業、${g.n || '—'} 檔` : `${g.n != null ? g.n : '—'} 檔${ud ? '　' + ud : ''}` });
      if (g.valuation && g.valuation.median != null) rows.push({ k: '本益比中位', v: (+g.valuation.median).toFixed(1) });
      const reg = cur && cur.model.regOf[g._region];
      const sub = [reg ? reg.name : '', TIER_NAME[g._tier] || ''].filter(Boolean).join(' · ');
      return T(g.name, sub, rows, g._rest ? '點一下看全部法定產業別' : '點一下看這個族群的個股');
    }
    if (kind === 'region') {
      const r = obj;
      const top = r.groups.filter(g => !g._rest).slice().sort((a, b) => (b.chg_pct || 0) - (a.chg_pct || 0));
      const best = top[0], worst = top[top.length - 1];
      const rows = [
        { k: '加權漲跌', v: fmtVal(r.chg, 'chg'), c: A ? A.upDown(r.chg) : null },
        { k: '成交值', v: `${fmtYi(r.turnover)}（${(+r.share).toFixed(1)}%）` },
        cur && cur.model.hasFlow ? { k: '資金熱度', v: r.flow != null ? fmtVal(r.flow, 'flow') : '—', c: A && r.flow != null ? A.upDown(r.flow) : null } : null,
        { k: r.id === 'industry' ? '產業' : '族群', v: `${r.id === 'industry' ? (r.allN || r.groups.length) : r.groups.length} 個　${r.up} 漲 ／ ${r.down} 跌` },
      ];
      for (let i = rows.length - 1; i >= 0; i--) if (!rows[i]) rows.splice(i, 1);
      if (best) rows.push({ k: '領漲', v: `${best.name} ${fmtVal(best.chg_pct, 'chg')}`, c: A ? A.upDown(best.chg_pct) : null });
      if (worst && worst !== best) rows.push({ k: '最弱', v: `${worst.name} ${fmtVal(worst.chg_pct, 'chg')}`, c: A ? A.upDown(worst.chg_pct) : null });
      return T(r.name, '產業區', rows, '點一下進入這條產業鏈');
    }
    if (kind === 'road') {
      const rd = obj, M = cur.model;
      const nA = M.regOf[rd.a].name, nB = M.regOf[rd.b].name;
      const rows = [];
      if (rd.supply.length) rows.push({ k: '供應關係', v: `${rd.supply.length} 條` });
      if (rd.shared.length) rows.push({ k: '共用成分股', v: `${rd.shared.length} 檔` });
      const cut = (t, n) => (t.length > n ? t.slice(0, n) + '…' : t);
      const items = [...new Set(rd.supply.map(s => cut(String(s.item).split(/[（(]/)[0].trim(), 14)).filter(Boolean))].slice(0, 4);
      const ex = rd.supply.slice(0, 3).map(s => `${esc(s.from)} → ${esc(s.to)}`);
      const sh = rd.shared.slice(0, 3).map(s => `${esc(s.name)}（${esc(s.ga)}／${esc(s.gb)}）`);
      let foot = '';
      if (items.length) foot += `<div>供應品項：${items.map(esc).join('、')}${rd.supply.length > items.length ? ' 等' : ''}</div>`;
      if (ex.length) foot += `<div>例：${ex.join('；')}</div>`;
      if (sh.length) foot += `<div>同時在兩區：${sh.join('、')}</div>`;
      foot += '<div>相關族群已在圖上標亮</div>';
      return T(`${nA} ⇄ ${nB}`, rd.supply.length ? '道路（供應鏈）' : '小路（共用成分股）', rows, foot);
    }
    return '';
  }

  /* ---------------------------------------------------------------- 對外：render */
  function render(host, ctx) {
    injectCss();
    const wrap = host.querySelector('#imMapWrap'), svg = host.querySelector('#imMap'), tip = host.querySelector('#imTip');
    if (!wrap || !svg) return null;
    const model = buildModel(ctx);
    const st = { model, color: ctx.color || 'chg', size: ctx.size || 'sqrt', focus: null, W: 0, H: 0, hover: null, roads: [] };
    cur = st;

    /* 高度：寬 × 0.56（500～760），再壓在「一屏看完」的上限內（DECISIONS #308／#309）——
       整張地圖卡（標題列＋地圖＋圖例列）高度 ≤ 視窗可視高，不必捲動就看得到全部的島與道路。
       Fit.room(svg) ＝ 卡高上限 − 卡裡 svg 以外的東西（標題列、圖例列、內距）；下限 420：
       再矮法定產業別與一般電子那兩塊窄島的街區就只剩色塊沒有字，寧可卡超出一點。
       手機與窄畫面（≤820）本來就沒有地圖，Fit.room 在那裡回 Infinity，不影響。 */
    function measureSize() {
      const W = Math.max(600, Math.round(wrap.clientWidth || 1000));
      let H = clamp(Math.round(W * 0.56), 500, 760);
      if (window.Fit && svg.isConnected) {
        const room = window.Fit.room(svg, { min: 420 });
        if (isFinite(room)) H = Math.min(H, room);
      }
      return { W, H };
    }
    function paint() {
      const { W, H } = measureSize();
      st.W = W; st.H = H;
      const res = draw(svg, model, st);
      st.roads = res.roads;
    }
    paint();

    // ---- 互動 ----
    const findBlock = (gid) => { for (const r of model.regions) for (const b of (r.blocks || [])) if (b.g.id === gid) return b; return null; };
    const showTip = (html, ev) => {
      if (!tip) return;
      tip.innerHTML = html; tip.hidden = false;
      const wr = wrap.getBoundingClientRect();
      let x = ev.clientX - wr.left + 16, y = ev.clientY - wr.top + 16;
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      if (x + tw > wr.width - 6) x = ev.clientX - wr.left - tw - 16;
      if (y + th > wr.height - 6) y = ev.clientY - wr.top - th - 16;
      tip.style.left = Math.max(6, x) + 'px'; tip.style.top = Math.max(6, y) + 'px';
    };
    const hideTip = () => { if (tip) tip.hidden = true; };
    const clearHi = () => {
      svg.querySelectorAll('.im-reg.hov,.im-rd.hov,.imb.hi').forEach(e => e.classList.remove('hov', 'hi'));
      svg.querySelectorAll('.imb.rdim').forEach(e => { e.classList.remove('rdim'); if (!(st.focus != null && +e.dataset.bin !== st.focus)) e.classList.remove('dim'); });
      st.hover = null;
    };
    const onMove = (ev) => {
      const t = ev.target;
      const blk = t.closest && t.closest('.imb');
      const rd = t.closest && (t.closest('[data-road]'));
      const reg = t.closest && t.closest('.im-reg');
      if (blk) {
        const gid = blk.dataset.gid; const b = findBlock(gid);
        if (st.hover !== 'b:' + gid) { clearHi(); st.hover = 'b:' + gid; if (reg) reg.classList.add('hov'); }
        if (b) showTip(tipHtml('block', b.g, st.color), ev);
        return;
      }
      if (rd) {
        const key = rd.dataset.road; const road = st.roads.find(x => x.key === key);
        if (road && st.hover !== 'r:' + key) {
          clearHi(); st.hover = 'r:' + key;
          road._g.classList.add('hov');
          svg.querySelectorAll('.imb').forEach(e => {
            const own = model.regOf[road.a]._g.contains(e) || model.regOf[road.b]._g.contains(e);
            if (road.gids.has(e.dataset.gid)) e.classList.add('hi');
            else if (own) e.classList.add('dim', 'rdim');
          });
        }
        if (road) showTip(tipHtml('road', road, st.color), ev);
        return;
      }
      if (reg) {
        const cid = reg.dataset.cid;
        if (st.hover !== 'g:' + cid) { clearHi(); st.hover = 'g:' + cid; reg.classList.add('hov'); }
        showTip(tipHtml('region', model.regOf[cid], st.color), ev);
        return;
      }
      if (st.hover) clearHi();
      hideTip();
    };
    const go = (h) => { if (h) location.hash = h; };
    const onClick = (ev) => {
      const t = ev.target;
      const blk = t.closest && t.closest('.imb');
      if (blk) { go(blk.dataset.href); return; }
      if (t.closest && t.closest('[data-road]')) return;
      const reg = t.closest && t.closest('.im-reg');
      if (reg) { const r = model.regOf[reg.dataset.cid]; if (r) go(r.href); }
    };
    const onKey = (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      const t = ev.target;
      if (t.classList && t.classList.contains('imb')) { ev.preventDefault(); go(t.dataset.href); }
      else if (t.classList && t.classList.contains('im-reg')) { ev.preventDefault(); const r = model.regOf[t.dataset.cid]; if (r) go(r.href); }
    };
    svg.onmousemove = onMove;
    svg.onmouseleave = () => { clearHi(); hideTip(); };
    svg.onclick = onClick;
    svg.onkeydown = onKey;

    // 寬度變了就重畫（字是真的像素大小，不能用 viewBox 縮放 —— 縮了字就會小於 12px）
    let lastW = st.W, rT = 0;
    if (wrap._imRO) { try { wrap._imRO.disconnect(); } catch (e) { /* 已經沒了 */ } }
    if (window.ResizeObserver) {
      const ro = new ResizeObserver(() => {
        if (!wrap.isConnected) { ro.disconnect(); return; }
        clearTimeout(rT);
        rT = setTimeout(() => { const w = Math.round(wrap.clientWidth); if (w > 0 && Math.abs(w - lastW) > 6) { lastW = w; paint(); } }, 120);
      });
      ro.observe(wrap); wrap._imRO = ro;
    }

    // 視窗「高度」變了（F11、拉矮視窗）寬度沒變，上面的 ResizeObserver 不會醒 → 交給 Fit.on 重算；
    // 卡裡別的東西晚一步長高（圖例列）也會叫醒它。paint 是冪等的：同一個高度再畫一次就收斂。
    // 上一張地圖（換頁回來重畫）的訂閱先取消，不然 Fit 的清單會留著已經離開畫面的舊 svg。
    if (fitOff) { try { fitOff(); } catch (e) { /* 已經取消 */ } fitOff = null; }
    if (window.Fit) {
      const off = window.Fit.on(() => {
        if (!svg.isConnected) { off(); if (fitOff === off) fitOff = null; return; }
        const { H } = measureSize();
        if (Math.abs(H - st.H) > 2) paint();
      }, svg);
      fitOff = off;
    }

    const api = {
      setColor(c) { st.color = c; st.focus = null; paint(); },
      setSize(s) { st.size = s; paint(); },
      setFocus(f) { st.focus = f; paint(); },
      // 資金熱度那份資料（flow_v3，約 1MB）晚到：只更新數字；目前是「資金熱度」顏色才需要重畫
      setFlow(flow, repaint) { ctx.flow = flow; applyFlow(model, flow); if (repaint !== false) paint(); },
      repaint: paint,
    };
    st.api = api;
    return api;
  }

  /* 驗收用：目前地圖的狀態（真人操作驗收量「畫面真的變了」） */
  function state() {
    if (!cur || !cur.model) return null;
    const M = cur.model;
    return {
      color: cur.color, size: cur.size, focus: cur.focus, W: cur.W, H: cur.H,
      regions: M.regions.map(r => ({ id: r.id, name: r.name, n: r.groups.length, rect: r.rect && { x: Math.round(r.rect.x), y: Math.round(r.rect.y), w: Math.round(r.rect.w), h: Math.round(r.rect.h) } })),
      blocks: M.regions.reduce((s, r) => s + (r.blocks || []).length, 0),
      labeled: M.regions.reduce((s, r) => s + (r.blocks || []).filter(b => b.label).length, 0),
      roads: (cur.roads || []).map(rd => ({ key: rd.key, supply: rd.supply.length, shared: rd.shared.length, gids: rd.gids.size })),
    };
  }

  window.IndMap = { render, state, buildModel, iconSvg, GROUP_ICON, CHAIN_ICON };
})();
