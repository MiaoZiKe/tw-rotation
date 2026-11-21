/* 矽光子／CPO（siph_cpo 鏈）兩張剖析圖 —— 規格書 docs/diagram_specs/siph_cpo.md（必讀，驗收清單 S/L/F/P/T/C/M/Ho/R）
   調查依據：docs/siph_cpo_semi_evidence.md、siph_cpo_optics_evidence.md、siph_cpo_substrate_evidence.md（只放高／中信心的公司）。

   圖 A  `siph_pkg`     CPO 交換器封裝剖析：2D 剖面（由下到上）＋ 俯視 ＋ 3D 爆炸（SCENES.siph_pkg，three3d.js）
   圖 B  `siph_module`  光訊號路徑、三條並行供應鏈道、四種光互連架構對照（純 2D）

   CEO 2026-10-24 拍板（覆蓋規格書 §0-C 的掛載建議）：
     · 不掛 ai_server，掛在新鏈 `siph_cpo`；slot id ＝ 族群 id（`siph_pkg`、`siph_module`），群組出現後自動生效。
     · 規格書主張的「三條並行供應鏈道」照做：雷射晶粒不進 PIC／封裝，與光引擎線在**交換器整機**才相遇（T1，★★★）。
   實作上寫死的幾件事：
     · 光引擎＝同一支 oe() 畫的 PIC（下，外緣伸出）＋ EIC（上，只蓋內側）＋ 混合鍵合（一排短矩形，**不用 circle**）＋ FAU（外緣）。
     · PM 光纖（虛線、暖色，箭頭**指向 PIC**）與資料光纖（實線、主色，TX 出／RX 進反向）是兩種線；雷射端沒有任何箭頭指向 ELSFP。
     · 冷板只壓在 ASIC 上（經 TIM1），光引擎頂面低於 ASIC 頂面，冷板對光引擎與 FAU 讓開。
     · 功耗用區間條（同一把尺），LPO 與 CPO 的 5–10 pJ/bit 畫成重疊；NPO 無獨立數字、不畫數字；底下固定「口徑不同」一行。
     · 不採用：Davisson 102.4T、NVIDIA 四 ASIC×六 OSA×三引擎、NPO／LPO 約 1 pJ/bit（單一來源，規格書 §7-C、§4-D）。
   顏色一律 --dg-*，沒有色碼。 */
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;
  const CW = 660;

  const VARS = `<style>
    svg.dg.dgsp [data-seg].sel .part{filter:none;stroke-width:1.5}
    svg.dg.dgsp [data-seg].sel-part .part{stroke-width:2.6;filter:var(--dg-glow,drop-shadow(0 0 6px var(--cc)))}
    .dgwrap:has(svg.dg.dgsp) .dgc.dim{opacity:.55}
    svg.dg.dgsp .pmf{stroke:var(--dg-sw-fiber);stroke-dasharray:6 4;fill:none;stroke-width:2}
    svg.dg.dgsp .dtf{stroke:var(--dg-accent-2d);fill:none;stroke-width:2}
    svg.dg.dgsp .elc{stroke:var(--dg-sig);fill:none;stroke-width:2}
    svg.dg.dgsp .wg{stroke:var(--dg-accent-2d);fill:none;stroke-width:1.4}
    svg.dg.dgsp .nd{fill:var(--dg-step-f);stroke:var(--dg-line-mix);stroke-width:1}
    svg.dg.dgsp .nd.hl{stroke:var(--dg-accent-2d);stroke-width:1.6}
    svg.dg.dgsp .bar0{fill:var(--dg-step-f);stroke:var(--dg-line-mix)}
    svg.dg.dgsp .rb{fill:var(--dg-accent-2d);fill-opacity:.55;stroke:var(--dg-accent-2d)}
    svg.dg.dgsp .rb.w{fill:var(--dg-sw-fiber);stroke:var(--dg-sw-fiber)}
    svg.dg.dgsp .rb.none{fill:none;stroke-dasharray:4 3}
  </style>`;

  const R = (x, y, w, h, fill, cls, rx) => `<rect${cls ? ` class="${cls}"` : ''} x="${+x.toFixed(1)}" y="${+y.toFixed(1)}" width="${+w.toFixed(1)}" height="${+h.toFixed(1)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const LN = (d, cls, extra) => `<path class="${cls}" d="${d}"${extra || ''}/>`;
  const part = (id, inner, seg, alias) => `<g data-part="${id}"${seg ? ` data-seg="${seg}"` : ''}${alias ? ` data-alias="${alias}"` : ''}>${inner}</g>`;
  const T = (x, y, s, cls, anchor, style) => `<text class="${cls || 'sub'}" x="${+x.toFixed(1)}" y="${+y.toFixed(1)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const ARROW = (x, y, dir) => `<path d="M${x},${y} l${-6 * dir},-4 v8z" fill="currentColor"/>`;
  const C = { si: 'var(--dg-si)', org: 'var(--dg-organic)', au: 'var(--dg-au)', cu: 'var(--dg-cu-lit)', pcb: 'var(--dg-pcb)',
    die: 'var(--dg-die)', mute: 'var(--dg-mute)', sn: 'var(--dg-sn)', glass: 'var(--dg-glass)', met: 'var(--dg-ni)', warm: 'var(--dg-sw-fiber)', acc: 'var(--dg-accent-2d)' };
  const card = (o) => {
    const s = extRow({ seg: o.seg, part: o.part, alias: o.alias, title: o.title, sub: o.sub, no: o.no, side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ================================================================ 圖 A */
  const OY = -118;                       // 整組剖面上移（§1 一眼看完）
  const Y = (v) => v + OY;
  /* 一顆光引擎（左側那顆；mir＝右側鏡像）。x0＝PIC 外緣（FAU 接這裡）。PIC 在下、外緣伸出；EIC 在上、只蓋內側；
     兩層之間是一排銅墊（短矩形，不是圓點）。EIC 頂面（Y 296 之下）低於 ASIC 頂面。 */
  function oe(x0, mir) {
    const s = mir ? -1 : 1, X = (a, w) => (mir ? x0 - a - w : x0 + a);
    const picY = 330, picH = 16, eicH = 14, picW = 88, eicW = 56;
    let g = '';
    g += part('sp_pic', R(X(0, picW), Y(picY), picW, picH, C.si, 'part', 2)
      + [10, 22, 34].map((a) => `<path d="M${X(a, 0)},${Y(picY + 4)} h${s * 22}" stroke="var(--dg-accent-2d)" stroke-width="1.2" fill="none"/>`).join('')
      + R(X(0, 0) + (mir ? -4 : 0), Y(picY + 2), 4, 12, C.glass, '', 0), 'foundry');
    const bx = X(picW - eicW, eicW);
    g += part('sp_hb', Array.from({ length: 9 }, (_, i) => R(bx + 4 + i * 6, Y(picY - 2), 4, 3, 'var(--dg-cu)', 'part', 0)).join(''), 'adv_pkg');
    g += part('sp_eic', R(bx, Y(picY - 2 - eicH), eicW, eicH, C.die, 'part', 2)
      + [0, 1, 2, 3].map((i) => R(bx + 6 + i * 12, Y(picY - eicH), 8, 6, 'var(--dg-void)', '', 1)).join(''), 'ic_design');
    return g;
  }
  function fau(x0, mir) {            // FAU：PIC 外緣的玻璃塊，光纖水平向外
    const w = 30, x = mir ? x0 : x0 - w;
    return part('sp_fau', R(x, Y(326), w, 24, C.glass, 'part', 2) + R(x + (mir ? 4 : w - 16), Y(324), 12, 3, 'var(--dg-void)', '', 1)
      + [332, 338, 344].map((yy) => `<path d="M${mir ? x + 6 : x + 6},${Y(yy)} h${w - 12}" stroke="var(--dg-void)" stroke-width=".8" fill="none"/>`).join(''), 'optical');
  }
  function section() {
    let g = '';
    g += fx.shadows(`<rect x="94" y="${Y(402)}" width="472" height="24" rx="4"/>`);
    g += part('sp_pcb', fx.glass(30, Y(396), 600, 16, { fill: C.pcb, cls: 'part', rx: 3 })
      + Array.from({ length: 19 }, (_, i) => `<circle cx="${112 + i * 24.5}" cy="${Y(384)}" r="6" fill="${C.sn}" class="part"/>`).join(''), 'hdi_pcb', 'sp_bga');
    g += part('sp_sub', fx.glass(90, Y(354), 480, 24, { fill: C.org, cls: 'part', rx: 2 })
      + [358, 364, 370].map((yy) => `<path d="M96,${Y(yy)} H564" stroke="var(--dg-cu)" stroke-width=".8" fill="none" opacity=".6"/>`).join(''), 'abf_pcb');
    g += part('sp_stiff', R(90, Y(336), 14, 18, C.met, 'part', 1) + R(556, Y(336), 14, 18, C.met, 'part', 1)
      + Array.from({ length: 14 }, (_, i) => R(112 + i * 6, Y(346), 4, 8, C.sn, 'part', 0)).join(''), 'adv_pkg', 'sp_c4');
    g += part('sp_asic', fx.glass(250, Y(296), 160, 50, { fill: C.die, cls: 'part', rx: 2 })
      + [0, 1, 2, 3].map((i) => R(262 + i * 36, Y(304), 28, 14, 'var(--dg-void)', '', 1)).join('') + T(330, Y(334), '交換 ASIC', 'lbl', 'middle'), 'ic_design');
    g += part('sp_tim', R(250, Y(290), 160, 6, 'var(--dg-uf)', 'part', 1), 'thermal');
    g += part('sp_lid', fx.glass(238, Y(256), 184, 34, { fill: C.met, cls: 'part', rx: 3 })
      + [0, 1, 2, 3, 4, 5].map((i) => R(252 + i * 28, Y(262), 18, 22, 'var(--dg-void)', '', 2)).join(''), 'thermal', 'sp_tim');
    g += oe(150, false) + fau(150, false) + oe(510, true) + fau(510, true);
    // 光纖與前面板（左）、ELSFP（左上）
    g += part('sp_face', R(18, Y(236), 10, 128, C.met, 'part', 1)
      + [326, 336, 346].map((yy) => R(22, Y(yy - 4), 14, 8, C.au, '', 1)).join('') + T(32, Y(222), '前面板', 'cap'), 'connector');
    g += part('sp_elsfp', R(28, Y(246), 76, 26, C.met, 'part', 3) + R(24, Y(243), 8, 32, C.sn, '', 2) + T(66, Y(263), 'ELSFP', 'lbl', 'middle'), 'optical', 'sp_pm');
    g += part('sp_fiber', LN(`M120,${Y(332)} H36`, 'dtf') + LN(`M120,${Y(338)} H36`, 'dtf') + LN(`M540,${Y(332)} H606`, 'dtf')
      + LN(`M540,${Y(338)} H606`, 'dtf'), 'optical');
    g += part('sp_pm_line', LN(`M104,${Y(259)} H112 V${Y(326)} H120`, 'pmf') + `<path d="M118,${Y(326)} l-6,-4 v8z" fill="var(--dg-sw-fiber)" transform="rotate(0)"/>`, 'optical');
    // 方向箭頭：TX 出、RX 進、CW 光進 PIC（箭頭在 PIC 側）
    g += `<g fill="var(--dg-accent-2d)"><path d="M44,${Y(332)} l8,-4 v8z"/><path d="M110,${Y(338)} l-8,-4 v8z"/></g>`;
    // ASIC ↔ EIC 毫米級短路（藍）
    g += LN(`M252,${Y(350)} H212 V${Y(344)}`, 'elc') + T(214, Y(372), '毫米級短路', 'cap');
    g += T(640, Y(305), '光纖→前面板', 'cap', 'end');
    g += T(126, Y(310), '耦合邊', 'cap');
    return g;
  }
  function topview() {        // Z3：ASIC 居中、OE 環繞（8 顆示意）、FAU 朝外
    const cx = 540, cy = 100, g = [];
    g.push(R(cx - 78, cy - 66, 156, 132, 'var(--dg-frame-f)', '', 6));
    g.push(R(cx - 26, cy - 26, 52, 52, C.die, 'part', 2));
    const sides = [[0, -1], [0, 1], [1, 0], [-1, 0]];
    sides.forEach(([dx, dz]) => [-1, 1].forEach((s) => {
      const tx = -dz, tz = dx, x = cx + dx * 46 + tx * s * 18, y = cy + dz * 40 + tz * s * 18;
      const w = dx ? 14 : 22, h = dx ? 22 : 14;
      g.push(R(x - w / 2, y - h / 2, w, h, C.si, 'part', 1));
      g.push(R(x + dx * (w / 2 + 3) - (dx ? 3 : 7), y + dz * (h / 2 + 3) - (dz ? 3 : 7), dx ? 6 : 14, dz ? 6 : 14, C.glass, '', 1));
    }));
    g.push('');
    return part('sp_top', g.join(''), 'optical');
  }

  /* 章節 ②：PIC 裡面有什麼（Z1）。光的路徑順序：輸入耦合器 → 分光 → 調變器 → 輸出耦合器；RX：耦合器 → 波導 → Ge 光偵測器 */
  function areaPic() {
    const y0 = 440;
    const box = (x, y, w, h, t, t2, on) => R(x, y, w, h, 'var(--dg-step-f)', 'nd' + (on ? ' hl' : ''), 5) + T(x + w / 2, y + 18, t, 'lbl', 'middle') + T(x + w / 2, y + 34, t2, 'sub', 'middle');
    let g = T(16, y0 - 20, '光在 PIC 裡走的順序（示意，真實版圖會把路徑折回同一個邊緣）', 'hd');
    g += R(16, y0 + 54, 628, 50, C.si, 'part', 4) + T(24, y0 + 49, 'PIC（矽，SOI）；調變器電極朝上、接 EIC', 'cap');
    g += part('sp_z_pic',
      R(16, y0 - 6, 628, 128, 'none', '', 6)
      + box(24, y0 + 72, 96, 40, '輸入耦合器', '接 FAU', true)
      + box(132, y0 + 72, 84, 40, '分光器', '一分二')
      + box(228, y0 + 72, 112, 40, '調變器', '並行臂 MZM')
      + box(352, y0 + 72, 112, 40, '輸出耦合器', '接 FAU', true)
      + [[120, 216], [216, 228], [340, 352]].map(([a, b]) => LN(`M${a},${y0 + 92} H${b}`, 'wg')).join('')
      + LN(`M464,${y0 + 92} H520`, 'wg') + T(526, y0 + 96, '→ 資料光（TX）', 'sub')
      + R(268, y0 + 54, 32, 12, C.au, '', 2) + R(300, y0 + 54, 24, 12, C.au, '', 2), 'foundry');
    g += part('sp_z_pd', R(24, y0 + 122, 96, 0, 'none')
      + '', 'foundry');
    g += T(16, y0 + 136, 'RX 接收：邊緣耦合器 → 波導 → 鍺（Ge）光偵測器；光電流往上送進 EIC 的 TIA 放大。', 'sub');
    g += T(16, y0 + 154, '驅動器（Driver）與 TIA 在 EIC；調變器與 Ge 光偵測器在 PIC。波導遠比光纖細，耦合器是錐形放大。', 'sub');
    g += T(16, y0 + 172, '調變器種類擇一示意（台積電／Broadcom 多為 MZM，NVIDIA 為微環 MRM；來源：產業媒體 2025），另一種亦存在。', 'sub', null, 'fill:var(--dg-warn)');
    return `<g>${g}</g>`;
  }
  /* 章節 ③：雷射為什麼放在外面（Z4） */
  function areaLaser() {
    const y0 = 700;
    let g = T(16, y0 - 20, '一個 ELSFP 的光，分供好幾顆光引擎（條數與顆數示意）', 'hd');
    g += part('sp_z_els', R(16, y0, 150, 70, C.met, 'part', 5) + T(91, y0 + 22, 'ELSFP', 'lbl', 'middle')
      + R(36, y0 + 34, 22, 22, C.au, '', 2) + T(70, y0 + 50, '雷射晶粒', 'sub') + T(36, y0 + 90, '前面板可插拔', 'cap'), 'optical');
    [0, 1, 2, 3].forEach((i) => {
      const y = y0 + 6 + i * 20;
      g += LN(`M166,${y + 6} C260,${y + 6} 280,${y0 + 6 + i * 22} 380,${y0 + 6 + i * 22}`, 'pmf');
      g += R(386, y0 + i * 22, 112, 18, C.si, 'part', 3) + T(442, y0 + 13 + i * 22, 'PIC 輸入耦合器', 'sub', 'middle');
      g += `<path d="M384,${y0 + 9 + i * 22} l-8,-4 v8z" fill="var(--dg-sw-fiber)"/>`;
    });
    g += T(508, y0 + 12, '← PM 光纖（虛線）', 'sub') + T(508, y0 + 30, '箭頭指向 PIC', 'sub') + T(508, y0 + 48, '雷射端無箭頭', 'sub');
    g += T(16, y0 + 118, '為什麼放外面：雷射怕熱、壽命隨溫度衰減，不能跟幾百瓦的交換晶片放在同一顆封裝裡；', 'sub');
    g += T(16, y0 + 136, '放在前面板，壞了可以直接換，也比較容易達到眼睛安全等級（IEC 60825-2 Hazard Level 1 為目標）。', 'sub');
    g += T(16, y0 + 154, '（來源：SENKO 摘要 2025／OIF ELSFP 定義之廠商資料；規格原文未讀）', 'cap');
    return `<g>${g}</g>`;
  }
  /* 章節 ④：台股標示帶（只放高／中信心；時程照調查報告原文，不升級成現在式） */
  const BAND = [
    ['sp_band1', 'optical_epi', '① 磊晶／雷射晶粒', '聯亞 3081（磊晶）、全新 2455、光環 3234（後段代工）、華星光 4979（CW 後段）', '聯亞 2026-08 與美系大廠簽 4 年 CW 長約（公司重訊；對象未具名）'],
    ['sp_band2', 'optical', '② 外置雷射模組（ELS／ELSFP）', '眾達-KY 4977（配合 Broadcom）、聯鈞 3450（design-in 階段）、華星光 4979', '眾達：2026–2027 才是第一波大量導入（董座股東會）'],
    ['sp_band3', 'foundry', '③ PIC 製造（晶圓代工）', '台積電 2330（COUPE／SoIC）、聯電 2303（首批 1.6T 矽光子量產晶圓，2026-07）', 'COUPE 2026 量產為目標；EIC 製程節點兩說，圖上不寫死'],
    ['sp_band4', 'ic_design', '④ EIC／ASIC 設計', '聯發科 2454（EIC 自研，CPO 樣品展示 2026-06）；交換 ASIC 設計者為外商（Broadcom、NVIDIA）', '世芯 3661、創意 3443 為 CPO 合作／展示階段，非交換 ASIC 設計者'],
    ['sp_band5', 'optical', '⑤ 光學耦合（FAU／光纖套件）', '上詮 3363、波若威 3163、光聖 6442、大立光 3008（時程兩說）', '放量時程：2026Q3 小量、2027 才放量（照供應鏈資料）；非現在式'],
    ['sp_band6', 'abf_pcb', '⑥ 載板', '欣興 3037、景碩 3189（ABF 載板廠；供貨 CPO 的具名證據查不到）', '景碩 2025-08：CPO 為長期機會、未來一到兩年貢獻有限'],
    ['sp_band7', 'thermal', '⑦ 散熱', '台股無直接對應（CPO 專用冷板／TIM 未查到具名台廠）', '液冷屬 AI 伺服器鏈的液冷環節，這裡不重複'],
    ['sp_band8', 'switch', '⑧ 交換器整機', '智邦 2345（Tomahawk 交換器；CPO 款最快 2026H2）', '「Micas Networks」的 Davisson CPO 是 Micas、不是智邦'],
  ];
  function areaBand() {
    const y0 = 940, st = 70;
    let g = T(16, y0 - 20, '每一段台股做什麼（調查報告 2026-10-24；只放高／中信心）', 'hd');
    BAND.forEach((b, i) => {
      const y = y0 + i * st;
      g += part(b[0], R(16, y, 628, 62, 'var(--dg-step-f)', 'row', 7) + `<circle cx="34" cy="${y + 20}" r="7" fill="var(--dg-accent-2d)"/>`
        + T(50, y + 24, b[2], 'lbl') + T(50, y + 42, b[3], 'sub') + T(50, y + 58, b[4], 'cap'), b[1]);
    });
    return `<g>${g}</g>`;
  }

  function figA() {
    const sec = section();
    return `<svg class="dg dgm rs dgsp" viewBox="0 0 ${CW} 1520" width="100%" style="display:block">${D.STYLE}${VARS}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <text class="ttl ext" x="0" y="0">CPO 交換器封裝：ASIC 與光引擎怎麼共封裝</text>
      <text class="cap ext" x="0" y="0">交換 ASIC 居中、周圍一圈光引擎（PIC 在下、EIC 疊在上），同在一片大載板上；光纖從引擎外緣向外；雷射外置、插在前面板；冷板只壓在 ASIC 上。★ 誰做的見右側卡片與第 ④ 段。細節與示意聲明點「?」。</text>
      ${T(24, 24, '① 剖面：由下到上', 'hd')}
      ${T(470, 24, '② 俯視（8 顆示意）', 'hd')}
      ${sec}${topview()}
      ${T(24, 322, '示意圖，非實物比例｜層厚、凸塊、波導與光纖尺寸均為誇張放大', 'cap')}
      ${T(24, 340, '光引擎顆數、排列與載板／中介層做法依各家方案而異，本圖為概念示意', 'cap')}
      ${T(24, 358, 'PIC 內元件（調變器種類、耦合器形式）擇一示意，另一種亦存在', 'cap')}
      ${T(24, 376, '本圖畫「雷射外置」的 CPO；雷射整合在模組內的是可插拔，見「光訊號路徑與四種光互連架構」', 'cap')}
      ${T(24, 398, '線型：', 'cap')}${LN('M70,394 h26', 'dtf')}${T(100, 398, '資料光纖', 'cap')}${LN('M168,394 h26', 'pmf')}${T(198, 398, 'PM 光纖（CW 光，進 PIC）', 'cap')}${LN('M352,394 h26', 'elc')}${T(382, 398, '電（毫米級）', 'cap')}

      ${card({ seg: 'hdi_pcb', part: 'sp_pcb', alias: 'sp_bga', no: 1, side: 'l', color: C.pcb, ax: 56, ay: Y(402), title: '主板 PCB ＋ BGA 錫球', sub: ['全圖最大的平面；載板底下整片錫球接到它，球比 C4 大一個量級。'] })}
      ${card({ seg: 'abf_pcb', part: 'sp_sub', no: 2, side: 'l', color: C.org, ax: 110, ay: Y(366), title: '封裝載板（ABF 增層基板）', sub: ['平面上最大的封裝件，ASIC 與全部光引擎共用；尺寸比一般 AI 封裝更大（相對大小示意）。'] })}
      ${card({ seg: 'adv_pkg', part: 'sp_c4', alias: 'sp_stiff', no: 3, side: 'l', color: C.met, ax: 97, ay: Y(346), title: 'C4 凸塊／補強環／底填', sub: ['晶粒底下一排鼓形焊錫；補強環圍住載板邊緣、不碰晶粒、不蓋光纖出口。'] })}
      ${card({ seg: 'ic_design', part: 'sp_asic', no: 4, side: 'r', color: C.die, ax: 385, ay: Y(334), title: '交換 ASIC 晶粒', sub: ['居中、全封裝面積最大也最厚；電訊號到光引擎只走毫米級。設計者為外商。'] })}
      ${card({ seg: 'foundry', part: 'sp_pic', no: 5, side: 'l', color: C.si, ax: 205, ay: Y(340), title: 'PIC 光子晶片（下層）', sub: ['把光分路、調變、偵測；外緣伸出 EIC 之外，露出耦合邊給 FAU。'] })}
      ${card({ seg: 'ic_design', part: 'sp_eic', alias: 'sp_hb', no: 6, side: 'r', color: C.die, ax: 485, ay: Y(309), title: 'EIC 電子晶片（上層）＋ 混合鍵合', sub: ['疊在 PIC 上、只蓋內側：驅動器（Driver）與 TIA；兩層之間只有銅墊對銅墊，沒有凸塊。'] })}
      ${card({ seg: 'optical', part: 'sp_fau', alias: 'sp_fiber', no: 7, side: 'l', color: C.glass, ax: 128, ay: Y(329), title: 'FAU ＋ 資料光纖', sub: ['FAU 接在 PIC 外緣（遠離 ASIC 那邊），光纖水平向外，到封裝外才彎向前面板。'] })}
      ${card({ seg: 'optical', part: 'sp_elsfp', alias: 'sp_pm', no: 8, side: 'l', color: C.met, ax: 106, ay: Y(247), title: 'ELSFP 外置雷射 ＋ PM 光纖', sub: ['雷射在前面板，不在載板上；保偏光纖把連續光送進 PIC（箭頭指向 PIC）。'] })}
      ${card({ seg: 'thermal', part: 'sp_lid', alias: 'sp_tim', no: 9, side: 'r', color: C.met, ax: 412, ay: Y(262), title: 'TIM1 ＋ 冷板', sub: ['只壓在 ASIC 上；光引擎與 FAU 邊讓開，頂面比 ASIC 低。'] })}
      ${card({ seg: 'connector', part: 'sp_face', no: 10, side: 'l', color: C.met, ax: 23, ay: Y(290), title: '前面板與光纖連接器', sub: ['光纖終止在連接器（不是可插拔收發模組）；ELSFP 插在同一面板。'] })}
      ${note({ side: 'r', order: 0, warn: true, title: '★ 誰做的（結論）', lines: ['PIC／COUPE：台積電、聯電；FAU／光纖套件：上詮、波若威、光聖；外置雷射：眾達-KY、聯鈞；EIC 設計：聯發科；交換 ASIC 設計者為外商。逐段名單見下面第 ④ 段。'] })}
      ${note({ side: 'r', order: 98, title: '示意圖，非實物比例', lines: ['光引擎 8 顆、排法、層厚與尺寸為概念示意；PIC 內是否有 TSV、載板直接共封或經中介層、冷板讓位形狀依各家方案而異。', '台積電 COUPE：EIC 為 65 奈米級（產業媒體 2024）；Broadcom 51.2T 平台為 8 顆 × 6.4T 光引擎（廠商新聞稿 2024-03）。'] })}

      ${fold('sp2', '② PIC 裡面有什麼', '波導、分光、調變器、耦合器、鍺光偵測器的順序', areaPic())}
      ${fold('sp3', '③ 雷射為什麼放在外面', 'ELSFP 供多顆引擎、PM 光纖進 PIC、熱的理由', areaLaser())}
      ${fold('sp4', '④ 台股各做哪一段', '八段各是誰、時程照調查報告（目標、非現在式）', areaBand())}
    </svg>`;
  }

  /* ================================================================ 圖 B（2026-10-25 重畫：圖像為主、文字為輔）
     Andy 退件：「這篇是發生什麼事情，為何沒圖片 全都文字」。所以：
       B1  光路：真的畫出零件（ELSFP → 保偏光纖 → FAU → PIC 俯視含波導／調變器／耦合器／鍺光偵測器，EIC 疊在 PIC 內側，ASIC 在旁）；
           資料光纖 TX 出、RX 進。零件名全部搬進右／左欄的編號卡片，畫布上只留一個字的標籤。
       B3  四張並排的「交換器機箱側視小圖」：可插拔／LPO／NPO／CPO，光離 ASIC 越來越近；功耗區間條放在每張小圖下面。
       B2  三條並行供應鏈道，每個節點一個小圖示（晶圓、雷射晶粒、模組、堆疊、FAU、探針、機箱、機櫃、雲）。
     大段說明收進「?」（register 的 honest），畫布上不攤文字。結構約束（規格書 §4）不變：雷射不進封裝，在整機才相遇；
     功耗為區間條、LPO 與 CPO 重疊、NPO 不畫數字；所有時程是目標。 */
  const SUB = (x, y, w, h, fill, cls, rx) => R(x, y, w, h, fill, cls, rx);

  /* ---- B1 光路 ---- */
  const KB = 1.4, SB = (x, y) => [+(x * KB).toFixed(1), +(20 + (y - 20) * KB).toFixed(1)];
  function pathFig() {
    const g = [];
    g.push(R(150, 56, 300, 150, 'var(--dg-frame-f)', '', 6));                         // 載板（俯視）
    // 前面板（左）與 ELSFP
    g.push(part('sp_face', R(16, 96, 12, 108, C.met, 'part', 1) + [112, 130, 164, 184].map((y) => R(20, y - 4, 14, 8, C.au, '', 1)).join(''), 'connector'));
    g.push(part('sp_elsfp', fx.glass(40, 40, 82, 30, { fill: C.met, cls: 'part', rx: 3 }) + R(36, 44, 8, 22, C.sn, '', 2)
      + R(106, 48, 12, 6, C.au, '', 1) + T(84, 60, 'ELS', 'lbl', 'middle'), 'optical'));
    // 資料光纖：TX 出（箭頭向左）、RX 進（箭頭向右）
    g.push(part('sp_fiber', LN('M130,126 H34', 'dtf') + LN('M130,152 H34', 'dtf')
      + `<path d="M62,126 l8,-4 v8z M104,152 l-8,-4 v8z" fill="var(--dg-accent-2d)"/>` + T(62, 118, 'TX', 'cap') + T(96, 144, 'RX', 'cap'), 'optical'));
    // FAU
    g.push(part('sp_fau', fx.glass(130, 108, 34, 62, { fill: C.glass, cls: 'part', rx: 2 })
      + [126, 140, 152, 164].map((y) => `<path d="M134,${y} h26" stroke="var(--dg-void)" stroke-width=".8" fill="none"/>`).join(''), 'optical'));
    // PM 光纖：ELSFP 後端 → 繞到 FAU 上緣進 PIC（虛線、暖色，箭頭指向 PIC）
    g.push(part('sp_pm', LN('M122,51 H147 V114 H168', 'pmf') + `<path d="M170,114 l-8,-4 v8z" fill="var(--dg-sw-fiber)"/>`, 'optical'));
    // PIC（俯視）：邊緣耦合器、波導、分光、調變器（兩條並行臂＋電極）、鍺光偵測器
    const wg = (d) => `<path class="wg" d="${d}"/>`;
    g.push(part('sp_pic', R(164, 100, 190, 84, C.si, 'part', 3)
      + [114, 128, 152, 166].map((y) => R(164, y - 3, 10, 6, 'var(--dg-accent-2d)', '', 1)).join('')               // 邊緣耦合器（錐形放大）
      + wg('M174,114 H210') + R(210, 108, 8, 12, C.glass, '', 1)                                                    // 輸入耦合 → 分光
      + wg('M218,111 H262 M218,117 H262') + R(226, 104, 30, 3, C.au, '', 1) + R(226, 121, 30, 3, C.au, '', 1)        // 兩條並行臂＋電極
      + wg('M262,114 H272 V128 H174') + R(266, 108, 8, 12, C.glass, '', 1)                                          // 合光 → 輸出
      + wg('M174,152 H214') + R(214, 147, 12, 10, 'var(--dg-void)', '', 1)                                          // RX：耦合器 → 鍺光偵測器
      + wg('M174,166 H214') + R(214, 161, 12, 10, 'var(--dg-void)', '', 1), 'foundry'));
    // EIC（半透明疊在 PIC 內側）與 ASIC
    g.push(part('sp_eic', `<g opacity=".88">${R(236, 92, 112, 100, C.die, 'part', 3)}</g>`
      + [0, 1, 2, 3, 4].map((i) => R(244 + i * 20, 100, 14, 22, 'var(--dg-void)', '', 1)).join('')
      + [0, 1, 2, 3, 4].map((i) => R(244 + i * 20, 160, 14, 22, 'var(--dg-void)', '', 1)).join(''), 'ic_design'));
    g.push(part('sp_asic', fx.glass(366, 98, 72, 102, { fill: C.die, cls: 'part', rx: 3 })
      + [0, 1, 2].map((r) => [0, 1].map((c) => R(374 + c * 32, 106 + r * 30, 26, 24, 'var(--dg-void)', '', 2)).join('')).join(''), 'ic_design'));
    g.push(LN('M348,142 H366', 'elc'));
    g.push(`<g fill="var(--dg-accent-2d)"><path d="M232,182 l-1,0"/></g>`);
    return `<g transform="translate(0,${20 - 20 * KB}) scale(${KB})">${g.join('')}</g>`;
  }

  /* ---- B3 四張機箱側視小圖 ---- */
  function archFig() {
    const y0 = 318, cw = 150, gap = 8, g = [];
    g.push(T(16, y0 - 12, '② 光離 ASIC 由遠到近：可插拔 → LPO → NPO → CPO（機箱側視）', 'hd'));
    const names = ['可插拔', 'LPO', 'NPO', 'CPO'];
    for (let i = 0; i < 4; i++) {
      const x = 16 + i * (cw + gap), y = y0;
      let c = R(x, y, cw, 128, 'var(--dg-frame-f)', '', 7);
      c += R(x + 4, y + 20, 8, 84, C.met, 'part', 1);                                          // 前面板
      c += R(x + 14, y + 96, cw - 24, 8, C.pcb, 'part', 1);                                    // 主板
      const ax = x + 84, ay = y + 62;                                                           // ASIC（站在主板上）
      if (i === 3) c += R(x + 52, y + 90, 96, 6, C.org, 'part', 1);                            // CPO：同一片載板
      c += R(ax, ay, 40, 34, C.die, 'part', 2) + R(ax + 4, ay + 4, 12, 12, 'var(--dg-void)', '', 1) + R(ax + 22, ay + 4, 12, 12, 'var(--dg-void)', '', 1);
      if (i <= 1) {                                                                            // 可插拔／LPO：模組插在前面板、電走線很長
        c += R(x - 1, y + 56, 46, 26, C.met, 'part', 3) + R(x + 6, y + 62, 14, 14, i === 0 ? C.die : 'none', i === 0 ? '' : 'rb none', 1);
        c += LN(`M${x + 44},${y + 92} H${ax}`, 'elc') + T(x + 62, y + 88, '長', 'cap', 'middle');
        c += LN(`M${x - 1},${y + 69} H${x - 12}`, 'dtf');
      } else {                                                                                  // NPO／CPO：光引擎貼在 ASIC 旁
        const ex = ax - 38;
        if (i === 2) c += R(ex - 4, y + 90, 36, 6, C.org, 'part', 1);                          // NPO：自己的小載板（可拆）
        c += R(ex, y + 80, 28, 10, C.si, 'part', 2) + R(ex + 8, y + 72, 20, 8, C.die, 'part', 1);
        c += LN(`M${ex + 28},${y + 84} H${ax}`, 'elc');
        c += `<path d="M${ex},${y + 82} H${x + 12}" class="dtf" stroke-dasharray="none"/>`;
        c += R(x + 12, y + 70, 8, 22, C.au, '', 1);
      }
      g.push(part('spc_a' + i, c, 'optical'));
      g.push(T(x + cw / 2, y + 144, names[i], 'lbl', 'middle'));
      // 功耗區間條（同一把尺 0–20 pJ/bit）
      const bx = x + 8, sc = (cw - 16) / 20, b = [[15, 20, 'w'], [5, 10, ''], null, [5, 10, '']][i];
      g.push(R(bx, y + 154, cw - 16, 9, 'none', 'bar0', 2));
      g.push(b ? R(bx + b[0] * sc, y + 154, (b[1] - b[0]) * sc, 9, 'none', 'rb ' + b[2], 2) : R(bx + 5 * sc, y + 154, 5 * sc, 9, 'none', 'rb none', 2));
      g.push(T(bx, y + 178, ['15–20 pJ/bit', '5–10 pJ/bit', '介於兩者（不畫數字）', '5–10 pJ/bit'][i], 'sub'));
    }
    g.push(T(16, y0 + 200, '功耗口徑不同：可插拔／LPO 為模組級、CPO 為廠商系統級宣稱；非同基準，僅示意量級', 'cap', null, 'fill:var(--dg-warn)'));
    return g.join('');
  }

  /* ---- B2 三條並行供應鏈道（每個節點一個小圖示） ---- */
  const IC = {
    epi: (x, y) => `<circle cx="${x}" cy="${y}" r="13" fill="${C.si}" class="part"/><path d="M${x - 13},${y} h26 M${x},${y - 13} v26" stroke="var(--dg-void)" stroke-width=".8"/>`,
    laser: (x, y) => R(x - 9, y - 9, 18, 18, C.au, 'part', 2) + `<path d="M${x + 9},${y} h12" stroke="var(--dg-sw-fiber)" stroke-width="2"/>`,
    els: (x, y) => R(x - 22, y - 10, 44, 20, C.met, 'part', 3) + R(x - 26, y - 7, 6, 14, C.sn, '', 1) + R(x + 14, y - 3, 10, 6, C.au, '', 1),
    wafer: (x, y) => `<circle cx="${x}" cy="${y}" r="13" fill="${C.si}" class="part"/>` + [-6, 0, 6].map((d) => `<path d="M${x - 11},${y + d} h22 M${x + d},${y - 11} v22" stroke="var(--dg-void)" stroke-width=".7"/>`).join(''),
    eic: (x, y) => R(x - 12, y - 12, 24, 24, C.die, 'part', 2) + R(x - 7, y - 7, 6, 6, 'var(--dg-void)', '', 1) + R(x + 1, y - 7, 6, 6, 'var(--dg-void)', '', 1) + R(x - 7, y + 1, 14, 6, 'var(--dg-void)', '', 1),
    stack: (x, y) => R(x - 14, y - 12, 28, 8, C.si, 'part', 1) + R(x - 14, y - 1, 28, 2, 'var(--dg-cu)', '', 0) + R(x - 14, y + 3, 28, 9, C.die, 'part', 1),
    fau: (x, y) => R(x - 16, y - 10, 32, 20, C.glass, 'part', 2) + [-5, 0, 5].map((d) => `<path d="M${x - 24},${y + d} h40" stroke="var(--dg-accent-2d)" stroke-width="1.2"/>`).join(''),
    pkg: (x, y) => R(x - 18, y - 12, 36, 24, C.org, 'part', 2) + R(x - 7, y - 7, 14, 14, C.die, 'part', 1) + [-1, 1].map((s) => R(x + s * 12 - 3, y - 3, 6, 6, C.si, '', 1)).join(''),
    probe: (x, y) => R(x - 16, y - 12, 32, 6, C.met, 'part', 1) + [-10, -3, 4, 10].map((d) => `<path d="M${x + d},${y - 6} l${d > 0 ? 2 : -2},12" stroke="var(--dg-sn)" stroke-width="1.2"/>`).join('') + R(x - 12, y + 7, 24, 5, C.si, '', 1),
    sw: (x, y) => R(x - 24, y - 10, 48, 20, C.met, 'part', 2) + [0, 1, 2, 3, 4, 5].map((i) => R(x - 20 + i * 7, y + 2, 5, 5, C.au, '', 0)).join('') + R(x - 6, y - 7, 12, 8, C.die, '', 1),
    rack: (x, y) => R(x - 12, y - 14, 24, 28, C.met, 'part', 2) + [0, 1, 2, 3].map((i) => R(x - 9, y - 11 + i * 6.5, 18, 4, 'var(--dg-void)', '', 1)).join(''),
    cloud: (x, y) => `<path d="M${x - 16},${y + 8} a8,8 0 0 1 2,-15 a10,10 0 0 1 19,-2 a8,8 0 0 1 8,17z" fill="${C.glass}" class="part"/>`,
    asic: (x, y) => R(x - 13, y - 13, 26, 26, C.die, 'part', 2) + [0, 1].map((r) => [0, 1].map((c) => R(x - 9 + c * 10, y - 9 + r * 10, 8, 8, 'var(--dg-void)', '', 1)).join('')).join(''),
  };
  const node = (x, y, w, ic, label, seg, id, on) => part(id, R(x, y, w, 58, 'var(--dg-step-f)', 'nd' + (on ? ' hl' : ''), 6)
    + IC[ic](x + w / 2, y + 22) + T(x + w / 2, y + 51, label, 'lbl', 'middle'), seg);
  function laneFig() {
    const W = 92, G = 12, X = (c) => 16 + c * (W + G), y0 = 572, g = [];
    const arr = (d) => `<path class="wg" d="${d}" marker-end="url(#spm)"/>`;
    g.push(T(16, y0 - 22, '③ 供應鏈：三條並行的道（錢與貨由上游往下游），雷射在「整機」才與光引擎相遇', 'hd'));
    const r1 = y0 + 8, r2 = y0 + 80, r3 = y0 + 250;
    g.push(T(16, r1 - 2, '光源線', 'cap'));
    g.push(node(X(0), r1 + 4, W, 'epi', '① InP 磊晶', 'optical_epi', 'spc_n1'), node(X(1), r1 + 4, W, 'laser', '② 雷射晶粒', 'optical_epi', 'spc_n2'), node(X(2), r1 + 4, W, 'els', '③ ELS 模組', 'optical', 'spc_n3'));
    g.push(arr(`M${X(0) + W},${r1 + 33} H${X(1)}`), arr(`M${X(1) + W},${r1 + 33} H${X(2)}`));
    g.push(arr(`M${X(2) + W},${r1 + 33} H${X(5) + W / 2} V${r2 + 24 + 46}`));
    g.push(T(16, r2 + 6, '光引擎線（主線）', 'cap'));
    g.push(node(X(0), r2 + 10, W, 'wafer', '④ PIC 製造', 'foundry', 'spc_n4'), node(X(0), r2 + 76, W, 'eic', '⑤ EIC 設計', 'ic_design', 'spc_n5'));
    g.push(node(X(1), r2 + 40, W, 'stack', '⑥ SoIC 堆疊', 'adv_pkg', 'spc_n6'), node(X(2), r2 + 40, W, 'fau', '⑦ FAU 耦合', 'optical', 'spc_n7'), node(X(3), r2 + 40, W, 'probe', '⑧ 光引擎測試', 'test_interface', 'spc_n8'), node(X(4), r2 + 40, W, 'pkg', '⑨ 共封裝', 'abf_pcb', 'spc_n9'));
    g.push(arr(`M${X(0) + W},${r2 + 39} L${X(1)},${r2 + 60}`), arr(`M${X(0) + W},${r2 + 105} L${X(1)},${r2 + 84}`));
    [1, 2, 3].forEach((c) => g.push(arr(`M${X(c) + W},${r2 + 69} H${X(c + 1)}`)));
    g.push(node(X(5), r2 + 40, W, 'sw', '⑫ 交換器整機', 'switch', 'spc_n12', true));
    g.push(arr(`M${X(4) + W},${r2 + 69} H${X(5)}`));
    g.push(part('spc_test', R(X(1), r2 + 106, 4 * W + 3 * G, 20, 'var(--dg-step-f)', 'nd', 4) + T(X(1) + 8, r2 + 120, '測試橫帶：晶圓級光電 ▸ 光引擎 ▸ 整機（示意）', 'sub'), 'test_interface'));
    g.push(T(16, r3 - 4, '交換 ASIC 線', 'cap'));
    g.push(node(X(0), r3, W, 'asic', '⑩ ASIC 設計', 'ic_design', 'spc_n10'), node(X(1), r3, W, 'wafer', '⑪ 晶圓製造', 'foundry', 'spc_n11'));
    g.push(arr(`M${X(0) + W},${r3 + 29} H${X(1)}`));
    g.push(arr(`M${X(1) + W},${r3 + 29} H${X(4) + W / 2} V${r2 + 98}`));
    g.push(node(X(5), r2 + 130, W, 'rack', '⑬ 機櫃佈線', 'connector', 'spc_n13'), node(X(5), r3 + 50, W, 'cloud', '雲端業者', 'hyperscaler', 'spc_n14'));
    g.push(arr(`M${X(5) + W / 2},${r2 + 98} V${r2 + 130}`), arr(`M${X(5) + W / 2},${r2 + 188} V${r3 + 50}`));
    return g.join('');
  }
  function srcs() {
    const y0 = 980; const L = ['數字從哪來（來源皆為搜尋摘要，原文未讀）：', '可插拔約 15–20、CPO 約 5–10 pJ/bit：廠商引述', '（NADDOD、SENKO，2025–2026），來源間有出入。', 'LPO 800G 約 4–8 W、DSP 模組 12–16 W：Semtech', '摘要（2025）；CPO 比可插拔低 70% 為 Broadcom 宣稱。', 'NPO：光引擎為板上獨立可拆單元，電氣路徑公分級', '（業界定義摘要，2026）；未取得獨立 pJ/bit。', '不採用：NPO／LPO 約 1 pJ/bit（單一廠商宣稱）；', '102.4T Davisson 與 NVIDIA 引擎配置（單一來源）。'];
    return `<g>${L.map((t, i) => T(16, y0 + i * 20, t, i ? 'sub' : 'hd')).join('')}</g>`;
  }
  const TWB = [['① InP 磊晶、② 雷射晶粒', 'optical_epi', '聯亞 3081、全新 2455；後段代工：光環 3234、華星光 4979'], ['③ ELS／ELSFP 模組', 'optical', '眾達-KY 4977、聯鈞 3450、華星光 4979'],
    ['④ PIC 製造 ⑥ 3D 堆疊', 'foundry', '台積電 2330（COUPE／SoIC）、聯電 2303'], ['⑤ EIC 設計', 'ic_design', '聯發科 2454（交換 ASIC 設計者為外商）'],
    ['⑦ 光學耦合', 'optical', '上詮 3363、波若威 3163、光聖 6442、大立光 3008（兩說）'], ['⑧ 測試（晶圓級／光引擎／整機）', 'test_interface', '致茂 2360、旺矽 6223、穎崴 6515（驗證與接單階段）'],
    ['⑨ 共封裝', 'osat_test', '日月光投控 3711（2027 小量）、力成 6239（2026 年底小量）'], ['⑫ 交換器整機', 'switch', '智邦 2345（CPO 款最快 2026H2）']];
  function twBand() {
    const y0 = 1210;
    let g = T(16, y0 - 20, '每個節點的台股（調查報告 2026-10-24；只放高／中信心，時程為目標）', 'hd');
    TWB.forEach((b, i) => { const y = y0 + i * 52; g += part('spc_tw' + i, R(16, y, 628, 46, 'var(--dg-step-f)', 'row', 7) + T(30, y + 20, b[0], 'lbl') + T(30, y + 38, b[2], 'sub'), b[1]); });
    return `<g>${g}</g>`;
  }
  function figB() {
    return `<svg class="dg dgm rs dgsp" viewBox="0 0 ${CW} 1560" width="100%" style="display:block">${D.STYLE}${VARS}
      <defs><marker id="spm" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L8,4 L0,8z" fill="var(--dg-accent-2d)"/></marker></defs>
      <text class="ttl ext" x="0" y="0">光訊號路徑與四種光互連架構</text>
      <text class="cap ext" x="0" y="0">光從外置雷射出發，經保偏光纖進矽光子晶片，調變後從光纖陣列出去；四種架構差在光離 ASIC 多遠。細節點「?」。</text>
      ${T(16, 20, '① 光怎麼走：雷射 → PIC → 光纖 → 前面板', 'hd')}${pathFig()}${archFig()}${laneFig()}
      ${card({ seg: 'optical', part: 'sp_elsfp', no: 1, side: 'l', color: C.met, ax: SB(84, 32)[0], ay: SB(84, 32)[1], title: 'ELSFP 外置雷射', sub: ['在前面板，不在封裝裡；只有光源輸出。'] })}
      ${card({ seg: 'optical', part: 'sp_pm', no: 2, side: 'l', color: C.warm, ax: SB(147, 80)[0], ay: SB(147, 80)[1], title: '保偏光纖（虛線）', sub: ['連續光進 PIC，箭頭指向 PIC。'] })}
      ${card({ seg: 'optical', part: 'sp_fau', no: 3, side: 'l', color: C.glass, ax: SB(158, 98)[0], ay: SB(158, 98)[1], title: 'FAU 光纖陣列', sub: ['玻璃塊把光纖對準黏在 PIC 外緣。'] })}
      ${card({ seg: 'optical', part: 'sp_fiber', no: 4, side: 'l', color: C.acc, ax: SB(58, 126)[0], ay: SB(58, 126)[1], title: '資料光纖', sub: ['TX 出、RX 進，反向；終止於前面板連接器。'] })}
      ${card({ seg: 'connector', part: 'sp_face', no: 5, side: 'l', color: C.met, ax: SB(22, 86)[0], ay: SB(22, 86)[1], title: '前面板連接器', sub: ['光纖連接器，不是可插拔收發模組。'] })}
      ${card({ seg: 'foundry', part: 'sp_pic', no: 6, side: 'l', color: C.si, ax: SB(190, 92)[0], ay: SB(190, 92)[1], title: 'PIC 光子晶片', sub: ['波導、並行臂調變器、耦合器、鍺光偵測器。'] })}
      ${card({ seg: 'ic_design', part: 'sp_eic', no: 7, side: 'r', color: C.die, ax: SB(292, 80)[0], ay: SB(292, 80)[1], title: 'EIC 電子晶片', sub: ['疊在 PIC 內側：驅動器與 TIA。'] })}
      ${card({ seg: 'ic_design', part: 'sp_asic', no: 8, side: 'r', color: C.die, ax: SB(402, 90)[0], ay: SB(402, 90)[1], title: '交換 ASIC', sub: ['外商設計；與 EIC 只隔毫米。'] })}
      ${note({ side: 'r', order: 90, title: '圖例', lines: ['實線＝資料光纖（TX／RX）；虛線＝保偏光纖（CW 光）；藍線＝電（毫米級）。雷射不進封裝，在整機才與光引擎相遇。'] })}
      ${fold('spc3', '④ 數字從哪來', '來源與口徑、為什麼有些數字不用', srcs())}
      ${fold('spc4', '⑤ 節點的台股', '八段各是誰（高／中信心），時程為目標', twBand())}
    </svg>`;
  }

  /* ================================================================ parts（點零件的小卡） */
  const P = (name, desc, cos, o) => Object.assign({ name, desc, cos }, o || {});
  const NONE = (n, d, why) => ({ name: n, desc: d, cos: [], none: why });   // cos: [] ＝ 明說「這一格台股沒有直接對應」，不退回去列環節名單（否則冷板會列出奇鋐）
  const parts = {
    sp_pcb: NONE('主板 PCB', '全圖最大的平面。', '交換器主板屬 800G→1.6T 通用的高層數板；CPO 專屬的台股證據查不到（調查報告 2026-10-24）。'),
    sp_bga: NONE('BGA 錫球', '載板底下整片錫球，比 C4 大一個量級。', '同上，無 CPO 專屬的台股證據。'),
    sp_sub: P('封裝載板（ABF）', '平面上最大的封裝件，ASIC 與全部光引擎共用（相對大小示意）。', ['3037', '3189'], { note: 'ABF 載板廠；供貨 CPO 封裝的具名證據查不到。景碩 2025-08：CPO 為長期機會，一到兩年內貢獻有限。' }),
    sp_stiff: P('補強環', '圍住載板邊緣防翹曲，不碰晶粒、不蓋光纖出口。', ['3711', '6239'], { note: 'CPO 封裝：日月光（NVIDIA 名單，2027 小量）、力成（2026 年底小量）。' }),
    sp_c4: P('C4 凸塊', '晶粒底下的鼓形焊錫，節距 150–200 µm 級（示意）。', ['3711', '6239']),
    sp_asic: P('交換 ASIC 晶粒', '居中、最大最厚；設計者為外商。', ['2330'], { note: '這一格講「誰代工」，不是「誰設計」。' }),
    sp_pic: P('PIC 光子晶片', '把光分路、調變、偵測；外緣露出給 FAU。', ['2330', '2303'], { note: '台積電 COUPE（2026 量產為目標）；聯電首批 1.6T 矽光子量產晶圓 2026-07。' }),
    sp_hb: P('混合鍵合界面', 'EIC 與 PIC 之間只有銅墊對銅墊，沒有凸塊。', ['2330']),
    sp_eic: P('EIC 電子晶片', '驅動調變器（Driver）、放大光偵測器電流（TIA）。', ['2454', '2330'], { note: '聯發科 2026-06 展示 CPO 樣品（EIC 自家設計）。' }),
    sp_fau: P('FAU 光纖陣列單元', '玻璃 V 槽塊把光纖對準黏在 PIC 外緣；次微米級主動對準。', ['3363', '3163', '6442', '3008'], { note: '放量時程：2026Q3 小量、2027 才放量；大立光時程兩說並列。' }),
    sp_fiber: P('資料光纖', 'TX 出、RX 進，終止在前面板連接器。', ['3163', '3665', '6442']),
    sp_pm: NONE('保偏光纖（PM）', '把外置雷射的連續光送進 PIC，偏振方向維持不變。', 'PM 光纖未查到台廠具名。'),
    sp_elsfp: P('ELSFP 外置雷射模組', '插在前面板、不在封裝裡；只有光源輸出、沒有資料光口。', ['4977', '3450', '4979'], { note: '眾達：2026–2027 才是第一波大量導入；聯鈞為 design-in 階段。' }),
    sp_tim: NONE('TIM1', '只夾在 ASIC 頂面與冷板之間。', 'CPO 專用 TIM 未查到具名台廠。'),
    sp_lid: NONE('冷板／散熱蓋', '只壓在 ASIC 上；光引擎與 FAU 邊讓開。', 'CPO 專用冷板未查到具名台廠；液冷屬 AI 伺服器鏈的液冷環節。'),
    sp_face: P('前面板與光纖連接器', '光纖終止在連接器，不是可插拔收發模組。', ['2345', '3665', '3163']),
    sp_top: P('俯視小圖', 'ASIC 居中、8 顆光引擎環繞、FAU 朝外（示意）。', ['2330']),
    sp_pm_line: NONE('PM 光纖（虛線）', '箭頭指向 PIC。', 'PM 光纖未查到台廠具名。'),
    sp_z_pic: P('PIC 內的光路', '輸入耦合器 → 分光 → 調變器 → 輸出耦合器；RX：耦合器 → 波導 → Ge 光偵測器。', ['2330', '2303']),
    sp_z_els: P('ELSFP 分供多顆引擎', '一個模組的連續光經多條 PM 光纖分供各顆光引擎（條數示意）。', ['4977', '3450', '4979']),
  };
  BAND.forEach((b) => { parts[b[0]] = { name: b[2], desc: b[3] + '。' + b[4] }; });
  const partsB = {
    spc_n1: P('① InP 磊晶', '雷射晶粒的磊晶片。', ['3081', '2455']),
    spc_n2: P('② 雷射晶粒', 'CW 雷射；後段另有代工。', ['3081', '3234', '4979']),
    spc_n3: P('③ ELS／ELSFP 模組', '在整機與光引擎相遇，不進封裝。', ['4977', '3450', '4979']),
    spc_n4: P('④ PIC 製造', '矽光子晶片（SOI）。', ['2330', '2303']),
    spc_n5: P('⑤ EIC 設計', '驅動器與 TIA。', ['2454']),
    spc_n6: P('⑥ SoIC 堆疊', 'EIC 以混合鍵合疊在 PIC 上。', ['2330']),
    spc_n7: P('⑦ FAU 耦合', '主動對準接合。', ['3363', '3163', '6442', '3008'], { note: '2026Q3 小量、2027 才放量；非現在式。' }),
    spc_n8: P('⑧ 光引擎測試', '晶圓級光電、光引擎、整機三個測試點。', ['2360', '6223', '6515']),
    spc_n9: P('⑨ 與 ASIC 共封裝', '載板上共封裝。', ['3711', '6239', '3037', '3189']),
    spc_n10: NONE('⑩ ASIC 設計', '外商設計。', '交換 ASIC 的設計者為外商。'),
    spc_n11: P('⑪ 晶圓製造', '交換 ASIC 的先進製程代工。', ['2330']),
    spc_n12: P('⑫ 交換器整機', '雷射與光引擎在此相遇。', ['2345']),
    spc_n13: P('⑬ 機櫃光纖佈線', '連接器與跳線。', ['3665', '3163']),
    spc_n14: NONE('雲端業者', '終端需求。', '台股無直接對應。'),
    spc_test: P('測試橫帶', '晶圓級光電測試 ▸ 光引擎測試 ▸ 整機測試（示意）。', ['2360', '6223', '6515']),
  };
  ['sp_face', 'sp_elsfp', 'sp_pm', 'sp_fau', 'sp_fiber', 'sp_pic', 'sp_eic'].forEach((k) => { partsB[k] = parts[k]; });
  partsB.sp_asic = NONE('交換 ASIC', '外商設計；與 EIC 只隔毫米。', '交換 ASIC 的設計者為外商（Broadcom、NVIDIA）。');
  TWB.forEach((b, i) => { partsB['spc_tw' + i] = { name: b[0], desc: b[2] }; });
  [0, 1, 2, 3].forEach((i) => { partsB['spc_a' + i] = { name: ['可插拔（DSP）', 'LPO', 'NPO', 'CPO'][i], desc: ['光在前面板，電氣路徑長；現行主流', '同可插拔位置，拿掉 DSP', '光引擎在板上、ASIC 旁，可拆（目標）', '光引擎與 ASIC 同封裝，毫米級（目標）'][i] + '。' }; });

  D.register('siph_pkg', {
    level: 'group', chain: 'siph_cpo', name: 'CPO 交換器封裝：ASIC 與光引擎共封裝',
    draw: figA, native: CW, scene: 'siph_pkg',
    q: '光引擎為什麼要搬到交換晶片旁邊？EIC、PIC、光纖、外置雷射各在哪一層、哪一段是台廠做的？',
    honest: '本圖畫「雷射外置」的 CPO；光引擎顆數（8 顆）、排列、層厚、載板或中介層做法依各家方案而異，為概念示意。PIC 內調變器種類擇一示意（MZM，另有微環 MRM）。台積電 COUPE 的 EIC 為 65 奈米級（產業媒體 2024）；Broadcom 51.2T 平台為 8 顆 × 6.4T 光引擎（廠商新聞稿 2024-03）。時程皆為目標。',
    parts,
  });
  D.register('siph_module', {
    level: 'group', chain: 'siph_cpo', name: '光訊號路徑與四種光互連架構',
    draw: figB, native: CW, scene: 'siph_module',
    honest: '光從外置雷射（ELSFP，插在前面板、不在封裝裡）出發，經保偏光纖進 PIC，調變後由 FAU 光纖出去；RX 反向，末端是 ASIC。供應鏈畫成三條並行的道：雷射不進光引擎封裝，在交換器整機才與光引擎相遇（畫成單線會暗示雷射先進 PIC，結構上是錯的）。四種架構差在光離 ASIC 的距離，功耗口徑不同（模組級 vs 廠商系統級宣稱，非同基準），NPO 沒有獨立數字、不畫；所有時程皆為目標，CPO 預期 2027 前後大量導入。晶粒、波導、光纖尺寸為示意，非實物比例。',
    q: '雷射、矽光子晶片、封裝、測試到機櫃佈線，錢與光各走哪一條？可插拔、LPO、NPO、CPO 差在哪？',
    parts: partsB,
  });
})();
