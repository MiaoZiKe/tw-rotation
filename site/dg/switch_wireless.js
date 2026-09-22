/* 網通：交換器板卡 ＋ 800G 可插拔光模組 ＋ 共同封裝光學（CPO）
   —— docs/diagram_plan.md 的第 8 張（族群 `switch_wireless`、掛在 ai_server 鏈）
   規格書：docs/diagram_specs/switch_board.md

   ================================================================
   ★ 跟 `aiServer()`（site/diagrams.js，AI 伺服器鏈的鏈層級架構圖）的分工
   ================================================================
   `aiServer()` 回答的是「**一座機櫃裡有哪幾層東西**」：機櫃、八個運算托盤、電源櫃、
   液冷 CDU。交換器在那張圖上只是機櫃最上面一條橫條（`data-part="ag_tor"`），
   光模組只是托盤右前方那四個小方塊（`ag_optic`）—— 它不畫、也不該畫板子裡面。
   這一張反過來：**把那一條橫條拆開放大**，只畫板卡本身 ——
   一顆交換器晶片、上千條等長差動對、前面板一整排光模組籠架、後方風扇與電源，
   以及「光引擎到底要插在前面板還是搬進封裝」這個取捨。
   另外跟 `dg/pcb_rigid.js`（多層 PCB 剖面＋走線＋銅箔）也要分工：
   **多層板本身怎麼做**是那一張的題目；這裡只畫「交換器板為什麼非要這麼多層」，
   也就是訊號／地的節律與背鑽，不重畫整套 PCB 製程。

   ---- 2026-09-22 v2（DECISIONS #238／#239／#240，分支 claude/restyle-w2a）----
   · 構圖：板卡＋光模組 → **半層疊**。板子是一片帶厚度的綠色玻璃板（前緣看得到一疊層），
     ASIC 的載板 → 晶片 → 散熱片往上拆開浮著（垂直爆炸，只拆主角），前面板是一片立起來的玻璃板，
     風扇與 PSU 是後方的玻璃方塊。立體語言全部走 D.fx.glass 的斜投影（頂面往右後上擠出），
     所以**前面板在畫面下方、後方在畫面右上**；風扇畫的是朝向機箱內側的進風面。
   · 光路用光束：**光＝ --dg-cool**（光纖進出前面板的籠架）、**電＝ --dg-sig**（籠架 → ASIC → 另一個籠架，雙向）、
     **供電＝ --dg-pwr**（PSU → VRM → ASIC，比訊號線粗）。發光預算：電訊號進來那一條 ＋ 光纖進來那一條 ＋ 一組柔陰影 ＝ 3。
   · svg 根掛 `.rs`：閱讀模式字級升一階、說明卡片離開 SVG 變成 HTML（extRow 多傳 side）。畫布 980 → **600**，native 跟著改。
   · §1 從 502 壓到約 480：右欄八列說明變成卡片（10 張 ＋ 公式卡 ＋ 警語卡），疊構節律、光模組、價值鏈流程列、
     可插拔 vs CPO 收進三個章節（一個字沒刪，只改斷行與位置）。
   · 卡片與畫布上的零件是同一個 data-part：點卡片亮零件、點零件亮卡片。
   · 卡片元件色（token）：光學 --dg-cool、板子 --dg-pcb-3d／層 --dg-cu-lit、散熱 --dg-alu、電源 --dg-pwr、連接 --dg-sig、ASIC --dg-mute。
   · 交換器 ASIC 仍然**不掛任何 data-seg**（規格書 §6-D 紅線）；v2 把「這一級由外商供應、台股沒有直接對應、看半導體鏈」
     寫進零件小卡（parts.sw_asic.none），畫布上的方塊不再帶 data-chain 直接跳走 —— 點區塊要亮它的卡片（跟 ABF 的灰色剪影同一種做法）。

   ================================================================
   ★ 要不要真 3D：**不用**（`scene: null`）。
   ================================================================
   規格書 §0「型式」已經寫死「不用真 3D」。四個答案（平面佈局、側剖面、光模組裡面、電訊號走多遠）
   沒有一個是「要繞到背面才看得到」的，而 3D 在手機上很重（DECISIONS #226 的代價）。

   ================================================================
   ★ 事實來源（2026-09-21 用 WebSearch 查證；只有摘要，沒有人讀過原文，網址留給下一個人）
   ================================================================
   · 51.2T ＝ 64 埠 × 800G、512 條 SerDes 通道 × 100G PAM4（Broadcom Tomahawk 5）；102.4T ＝ 64 埠 × 1.6T（Tomahawk 6）。
     2U／64 × 800G OSFP／前後直通氣流的整機確實存在 → broadcom.com 新聞稿、servethehome.com、fs.com 規格頁（N9600-64OD）
     ※ 算式自洽：64×800G=51.2T、64×1.6T=102.4T、512×100G=51.2T、8×6.4T=51.2T。只用來檢查有沒有畫離譜，不當規格數字標在零件旁邊。
   · CPO：Broadcom 2025-10 出貨 Tomahawk 6 – Davisson，102.4 Tb/s 共同封裝光學，宣稱光互連功耗降低約 70%
     → broadcom.com/company/news/product-releases/63626、storagenewsletter.com 2025-10-10
   · 為什麼要 CPO：224G 世代 PCB 走線損耗守不住。⚠ 兩個來源對 CPO 那一側給的數字不一樣（1～2 dB vs 約 4 dB），
     只有「可插拔約 20 dB 以上」對得起來 → 畫面只寫「可插拔：20 dB 以上／CPO：個位數 dB」
     → blog.apnic.net 2025-05-07、octopart.com「Designing for 224G」、semiengineering.com
   · OSFP vs QSFP-DD800（多個來源一致，信心高）：OSFP 模組本身自帶鰭片散熱片、體積較大；QSFP-DD800 平頂、靠籠架上的散熱片；
     兩者機構不相容。⚠ 功耗數字各家講的不一樣（12W／12–15W／16–18W／15–20W）→ 畫面一個瓦數都不寫
     → juniper.net 800G optics cables guide、fibermall.com、cloudswit.ch、ubytelink.com
   · 交換器板層數：AI 叢集用的 800G／1.6T 交換器板需要 40 層以上（另有 18 層線性直驅設計的反例）
     → 畫面寫「約 40 層以上（依架構而異）」，圖上實際畫 19 條並標「層數為示意」 → fastturnpcbs.com、atlaspcb.com
   · 高速板材與製程：超低損耗 CCL、HVLP 銅箔、背鑽、阻抗控制 → nextpcb.com「224G PCB Design」、hdicircuitboard.com
   ★ 一個都不准編的：市占、良率、單價、價值量、產能、傳輸距離、瓦數、板厚 mm。查不到就只畫相對關係並標「示意」。

   ================================================================
   ★ data-seg：只掛 supply_chain.yaml 裡**真的存在、而且屬於 ai_server 鏈**的環節
   ================================================================
     主板、走線、背鑽                 → hdi_pcb     （金像電、臻鼎-KY、健鼎、華通、精成科、瀚宇博）
     板子前緣的層／疊構裡的芯板 core   → ccl         （台光電、台燿、聯茂、騰輝電子-KY）
     半固化片（玻纖布＋樹脂）          → ccl_material（金居、南亞、建榮、富喬、德宏、榮科）
     籠架＋光模組＋光引擎＋光耦合       → optical     （華星光、波若威、上詮、眾達-KY）
     模組裡的雷射晶粒／光偵測器        → optical_epi （聯亞）
     飛越纜線／金手指等高速連接        → connector   （貿聯-KY）
     PSU、板上 VRM                    → power       （台達電、光寶科）
     散熱片、系統風扇                  → thermal     （奇鋐、雙鴻、一詮、健策、建準、高力）
     管理用處理器所在的整機             → switch      （智邦）
   ★ **交換器 ASIC 不掛任何 data-seg**：`ic_design` 那一格的台股是聯發科／瑞昱／祥碩／聯詠，**沒有一家供應這一級 ASIC**，
     而且它的 chain 是 semiconductor 不是 ai_server —— 掛上去會在畫面上印出四家不相干的公司，那是**資訊錯誤**。速率換算尺同理不掛。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function' || !D.fx) return;
  const { STYLE, extRow, note, processBar, fold, fx } = D;

  const CW = 600;
  /* ================================================================ 板子的斜投影（全部是畫布座標，寬 600）
     板子前緣左端在 (BX, BY)、寬 BW、厚 BT；頂面往右後上擠出 (DX, DY)。
     板上任何一點用 (u, v) 表示：u 沿板寬（0 左 → BW 右）、v 是深度（0 前面板 → 1 後方）。*/
  const BX = 22, BW = 380, BY = 215, BT = 18, DX = 190, DY = -170;
  const ISO = { dx: DX, dy: DY }, ISO2 = { dx: 16, dy: -12 };      // 板子／小零件各一組擠出量（比例相同）
  const P = (u, v) => ({ x: +(BX + u + v * DX).toFixed(1), y: +(BY + v * DY).toFixed(1) });
  const pt = (u, v) => { const q = P(u, v); return `${q.x},${q.y}`; };
  // 前面板：v ≈ 0.06 的一片立起來的板子，16 個籠架（實機 64 個，警語卡標示意）
  const PANEL = { v: 0.06, h: 30 }, PX = P(0, PANEL.v).x, PYB = P(0, PANEL.v).y, PYT = PYB - PANEL.h;
  const NCAGE = 8, CAGE_W = 32, CAGE_P = 45, CAGE_U0 = 12;
  const cageU = (i) => CAGE_U0 + i * CAGE_P + CAGE_W / 2;     // 籠架中心的 u（走線與光束用）
  // ASIC 的位置（板上最大的單一元件；封裝尺寸查不到，比例為示意）＋ 拆開浮著的三層
  const ASIC = { u0: 226, w: 80, v: 0.52 }, AB = P(ASIC.u0, ASIC.v);
  const LAY = { sub: [AB.y - 6, AB.y], die: [AB.y - 6 - 14 - 9, AB.y - 6 - 14], hs: [AB.y - 6 - 14 - 9 - 14 - 4, AB.y - 6 - 14 - 9 - 14] };
  const HS = { x: AB.x - 2, w: ASIC.w + 4, fin: 16 };
  // VRM 緊貼 ASIC 左側（規格書 §3-C：大電流走不遠，所以一定緊鄰）
  const VRM = { u0: 162, v: 0.52, n: 6, pitch: 9 };
  const FANS = [4, 60, 116].map(u => ({ u, v: 0.9, w: 46, h: 38 }));
  const PSUS = [280, 336].map(u => ({ u, v: 0.9, w: 52, h: 30 }));
  const CPU = { u: 8, v: 0.62 };
  // 卡片的元件色（token，不寫死）
  // 管理處理器那張卡預設就是 .sel（族群 switch_wireless → 環節 switch），標題會染成元件色：--dg-mute 在深底卡片上只有 4.38:1，改用 --dg-steel
  const COL = { opt: 'var(--dg-cool)', pcb: 'var(--dg-cu-lit)', therm: 'var(--dg-alu)', pwr: 'var(--dg-pwr)', sig: 'var(--dg-sig)', off: 'var(--dg-mute)', cpu: 'var(--dg-steel)' };

  /* 這張圖自己的樣式。**全部吃 --dg-* token，一個 #xxxxxx 都沒有。** 最後幾條要排在 STYLE 之後、特異性比它高（多一個 svg 型別選擇器）。*/
  const SW_STYLE = `<style>
    .dgsw .thin{stroke:var(--dg-ink-3);fill:none;stroke-width:1}
    .dgsw .air{stroke:var(--dg-mute);fill:none;stroke-dasharray:7 7;opacity:.6;stroke-width:2;animation:dgdash 2.4s linear infinite}
    /* 板子上的差動對：一條**實線**的粗線（兩根導體）＋ 中間一條板色的細縫。
       為什麼不用 .flow：整片板子上十條虛線會變成一堆碎屑，讀起來像雜訊而不是走線；封包的動態交給光束。
       為什麼不真的畫兩條平行線：在斜投影上要逐段算法線，轉角處還會分岔；「粗線＋中縫」讀起來就是「成雙成對的兩根」。*/
    .dgsw .dp{stroke:var(--dg-sig);fill:none;stroke-width:3.2;opacity:.7;stroke-linejoin:round;stroke-linecap:round}
    .dgsw .dpg{stroke:var(--dg-pcb);fill:none;stroke-width:1.1;stroke-linejoin:round;stroke-linecap:round;opacity:.9}
    .dgsw .pw{stroke:var(--dg-pwr);fill:none;stroke-width:4.2;stroke-linecap:round;stroke-linejoin:round;opacity:.85}
    .dgsw .fly{stroke:var(--dg-sig);fill:none;stroke-width:2.2;stroke-linecap:round}
    .dgsw .ly{fill:var(--dg-cu);opacity:.75}
    .dgsw .lyl{stroke:var(--dg-ink-3);stroke-width:1;fill:none;opacity:.5}
    .dgsw .cell{fill:var(--dg-frame-f);stroke:var(--dg-frame-s)}
    .dgsw .fin{fill:var(--dg-alu-2);stroke:var(--dg-alu-3);stroke-width:.6}
    .dgsw .fine{fill:var(--dg-alu)}
    .dgsw .cage{fill:var(--dg-alu-3);stroke:var(--dg-steel-2);stroke-width:.6}
    .dgsw .slot{fill:var(--dg-edge)}
    .dgsw .tab{fill:var(--dg-sw-gold)}
    .dgsw .fxbeam.rev .fxb-flow{animation-direction:reverse}
    /* 描邊與發光各降一階（只作用在這一張圖）：籠架 32×11、電感 8×8，共用的 2.2px 描邊套上去整個變成實心色塊。
       平時／選到的環節 → 不描邊；滑鼠移上去 → 1.4px；你點的那一個 → 2.4px ＋ 一圈暈開（閱讀模式 --dg-glow:none 就不暈）。*/
    svg.dgsw [data-seg] .part{stroke-width:0}
    svg.dgsw [data-seg].sel .part{stroke-width:0;filter:none}
    svg.dgsw [data-seg]:hover .part{stroke-width:1.4;filter:none}
    svg.dgsw [data-seg].sel-part .part{stroke-width:2.4;filter:var(--dg-glow,drop-shadow(0 0 5px var(--cc)))}
    svg.dgsw g[data-part="sw_asic"].sel-part .fxb{fill-opacity:.92}
    /* 壓暗那一階從 .3 放寬到 .55：進來的預設狀態是「族群 switch_wireless 被選起來」＝ switch 亮、其餘八個環節全部被壓暗 —— 那是整張圖。*/
    svg.dgsw [data-seg].dim{opacity:.55}
    .dgwrap:has(svg.dgsw) .dgc.dim{opacity:.55}
  </style>`;

  const R = (x, y, w, h, fill, cls, rx, op) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${(+x).toFixed(1)}" y="${(+y).toFixed(1)}" width="${(+w).toFixed(1)}" height="${(+h).toFixed(1)}"${rx ? ` rx="${rx}"` : ''}${fill ? ` fill="${fill}"` : ''}${op ? ` opacity="${op}"` : ''}/>`;

  /* ================================================================ §1 的零件 */
  // ---- 主板：綠色玻璃板；前緣一條一條銅色細帶＝「這片板子是一疊很多層壓起來的」（那幾條掛 ccl，是另一個零件）
  const gBoard = () => `<g data-seg="hdi_pcb" data-part="sw_pcb">${fx.glass(BX, BY, BW, BT, { iso: ISO, fill: 'var(--dg-pcb)', cls: 'part', rx: 3 })}</g>`;
  const gLayers = () => { const a = [];
    for (let i = 0; i < 8; i++) a.push(R(BX + 2, BY + 2 + i * 2, BW - 4, 0.9, '', 'ly part'));
    return `<g data-seg="ccl" data-part="sw_layers">${a.join('')}</g>`; };
  // ---- 前面板：立起來的玻璃板 ＋ 兩排籠架（拉環、指示燈）—— 一整面同規格的 I/O 全部朝同一個方向，是認出交換器板的第一個特徵
  function gPanel() {
    const cages = [];
    for (let r = 0; r < 2; r++) for (let i = 0; i < NCAGE; i++) {
      const x = PX + CAGE_U0 + i * CAGE_P, y = PYT + (r ? 16.5 : 3.5), h = 11;
      cages.push(R(x, y, CAGE_W, h, '', 'cage part', 1.4) + R(x + 2.2, y + 2.2, 18, h - 4.4, '', 'slot', 1)
        + R(x + 23, y + 3, 4, h - 6, '', 'tab', 1.2)
        + `<circle class="blink b${(i + r) % 3 + 1}" cx="${(x + 2.8).toFixed(1)}" cy="${(y + h - 2.4).toFixed(1)}" r="1.4" fill="var(--dg-cool)"/>`);
    }
    return `<g data-seg="optical" data-part="sw_cage">${fx.glass(PX, PYT, BW, PANEL.h, { iso: { dx: 8, dy: -4.5 }, fill: 'var(--dg-alu)', rx: 2 })}${cages.join('')}</g>`;
  }
  // ---- 風扇（後方、朝機箱內側的進風面）：扇框、扇葉、輪轂 —— AGENTS §11 明列的識別特徵
  function gFans() {
    const out = FANS.map((f, k) => { const b = P(f.u, f.v), x = b.x, y = b.y - f.h, cx = x + f.w / 2, cy = y + f.h / 2 + 1;
      const blades = [0, 1, 2, 3, 4, 5, 6].map(j => `<path class="thin" d="M0,0 L${(13 * Math.cos(j * 0.8976)).toFixed(1)},${(13 * Math.sin(j * 0.8976)).toFixed(1)}"/>`).join('');
      return fx.glass(x, y, f.w, f.h, { fill: 'var(--dg-alu-3)', cls: 'part', rx: 4, t: 3 })
        + `<circle class="thin" cx="${cx}" cy="${cy}" r="15"/>`
        + `<g transform="translate(${cx},${cy})"><g class="spin" style="animation-delay:${(k * 0.4).toFixed(1)}s">${blades}</g></g>`
        + `<circle cx="${cx}" cy="${cy}" r="3.6" fill="var(--dg-ink-3)"/>`; });
    return `<g data-seg="thermal" data-part="sw_fan">${out.join('')}</g>`;
  }
  // ---- PSU（後方、1+1 冗餘、可熱抽換）：金屬盒 ＋ 把手 ＋ 指示燈
  function gPsu() {
    const out = PSUS.map((s, k) => { const b = P(s.u, s.v), x = b.x, y = b.y - s.h;
      return fx.glass(x, y, s.w, s.h, { fill: 'var(--dg-steel)', cls: 'part', rx: 3, t: 3 })
        + R(x + 6, y + 6, 20, 4, 'var(--dg-ink-3)', '', 2) + `<circle class="blink b${k + 1}" cx="${x + s.w - 8}" cy="${y + 9}" r="2.2" fill="var(--dg-pwr)"/>`
        + [0, 1, 2, 3].map(j => `<path class="thin" d="M${x + 6 + j * 8},${y + 16} v8"/>`).join(''); });
    return `<g data-seg="power" data-part="sw_psu">${out.join('')}</g>`;
  }
  // ---- 管理用處理器 ＋ 記憶體（角落一小塊；只管設定與監控，不碰封包轉送）
  function gCpu() { const b = P(CPU.u, CPU.v);
    return `<g data-seg="switch" data-part="sw_cpu">${fx.glass(b.x, b.y - 14, 18, 14, { fill: 'var(--dg-si)', cls: 'part', rx: 2, t: 2 })}
      ${fx.glass(b.x + 22, b.y - 12, 6, 12, { fill: 'var(--dg-el)', cls: 'part', rx: 1, t: 1 })}${fx.glass(b.x + 30, b.y - 12, 6, 12, { fill: 'var(--dg-el)', cls: 'part', rx: 1, t: 1 })}</g>`; }
  // ---- 板上多相供電 VRM：一排 6 個等距電感（多相＝一排並聯，不是一顆），緊貼 ASIC
  function gVrm() { const b = P(VRM.u0, VRM.v), a = [];
    for (let i = 0; i < VRM.n; i++) a.push(fx.glass(b.x + i * VRM.pitch, b.y - 8, 8, 8, { fill: 'var(--dg-el)', cls: 'part', rx: 1.5, t: 2 }));
    return `<g data-seg="power" data-part="sw_vrm">${a.join('')}</g>`; }
  // ---- 交換器 ASIC：有機載板 → 覆晶晶片（往上拆開浮著）。**不掛 data-seg**（規格書 §6-D）
  const gAsic = () => `<g data-part="sw_asic" style="cursor:pointer">
    ${fx.glass(AB.x, LAY.sub[0], ASIC.w, LAY.sub[1] - LAY.sub[0], { iso: ISO2, fill: 'var(--dg-pcb-2)', rx: 2 })}
    ${[0, 1, 2, 3, 4, 5, 6, 7].map(j => R(AB.x + 6 + j * 9.6, LAY.sub[1] - 3, 5, 3, 'var(--dg-sw-gold)')).join('')}
    ${fx.glass(AB.x + 12, LAY.die[0], ASIC.w - 24, LAY.die[1] - LAY.die[0], { iso: ISO2, fill: 'var(--dg-si)', rx: 2 })}
    <path class="thin" d="M${AB.x + 26},${LAY.die[0] - 4} l6,-3 h20" opacity=".5"/></g>`;
  // ---- 晶片散熱片：底板 ＋ 一片片等距的鰭片，鰭片**順著前後氣流**（沿 v 方向拉長）—— 畫成左右向就是擋住風
  function gHs() { const fins = [], y0 = LAY.hs[0], top = y0 - HS.fin;
    for (let i = 0; i < 11; i++) { const x = HS.x + 4 + i * 7.6;
      fins.push(`<path class="fin part" data-fin="1" d="M${x},${y0} L${x},${top} L${x + ISO2.dx},${top + ISO2.dy} L${x + ISO2.dx},${y0 + ISO2.dy}Z"/>` + R(x - 1.2, top, 2.4, HS.fin, '', 'fine')); }
    return `<g data-seg="thermal" data-part="sw_hs">${fx.glass(HS.x, LAY.hs[0], HS.w, LAY.hs[1] - LAY.hs[0], { iso: ISO2, fill: 'var(--dg-alu)', cls: 'part', rx: 1.5 })}${fins.join('')}</g>`; }

  /* ---- 等長蛇行差動對：從 ASIC 的前緣出發，走到前面板每一個籠架的背面。
     ★ 規格書 §3-B 的三條硬規則就在這一段：
       · 每一條的兩端一定是「一個籠架 ↔ 那顆 ASIC」，不准兩個籠架直連
       · **近的埠要繞路、遠的埠直走**（等長）—— folds 就是這一條
       · 方向是**雙向**的（每個埠都同時收與發）—— 光束一條進、一條出
     · 走飛越纜線的那兩個埠（i = 0,1）**板子上就不再畫走線**，不然等於同一個訊號走了兩條路。*/
  const TRACES = (() => {
    const list = [];
    const tg = []; for (let i = 2; i < NCAGE; i++) tg.push(cageU(i));
    // 畫面上的長度（等長是量畫面上那條線，不是 (u,v) 座標）
    const lenOf = (pts) => { let L = 0; for (let k = 1; k < pts.length; k++) { const a = P(pts[k - 1][0], pts[k - 1][1]), b = P(pts[k][0], pts[k][1]); L += Math.hypot(b.x - a.x, b.y - a.y); } return L; };
    const base = tg.map((uT, n) => {
      const uA = ASIC.u0 + 6 + n * (ASIC.w - 12) / (tg.length - 1), vL = 0.40 - n * 0.022;
      return { uT, vL, pts: [[uA, ASIC.v - 0.02], [uA, vL], [uT, vL], [uT, PANEL.v + 0.04]] };
    });
    const target = Math.max.apply(null, base.map(b => lenOf(b.pts)));     // 最遠的埠直走，它的長度就是大家要補到的長度
    base.forEach((b, n) => {
      const STEP = 0.045, AMP = 10, pts = b.pts.slice(0, 3);
      let cur = b.vL, folds = 0;
      // 蛇行：一折一折加，加到跟最遠的那條差不多長為止（近的埠繞路、遠的埠直走）—— 補的長度就在這裡
      while (cur - STEP > PANEL.v + 0.10 && folds < 8) {
        const trial = pts.concat([[b.uT - AMP, cur - STEP / 2], [b.uT + AMP, cur - STEP], [b.uT, cur - STEP - 0.02], [b.uT, PANEL.v + 0.04]]);
        if (lenOf(trial) > target - 6) break;
        pts.push([b.uT - AMP, cur - STEP / 2], [b.uT + AMP, cur - STEP]); cur -= STEP; folds++;
      }
      pts.push([b.uT, cur - 0.02], [b.uT, PANEL.v + 0.04]);
      list.push({ i: n + 2, uT: b.uT, pts, folds, d: 'M' + pts.map(([u, v]) => pt(u, v)).join(' L') });
    });
    return list;
  })();
  const gTraces = () => `<g pointer-events="none">${TRACES.map(t => `<path class="dp" d="${t.d}"/><path class="dpg" d="${t.d}"/>`).join('')}</g>`;
  // ---- 近晶片飛越纜線：從 ASIC 旁的小連接器架空拉到籠架 0、1 的背面（板子走不動的距離，用線來走）
  const FLY = (() => { const c = P(196, 0.44), t0 = P(cageU(0), PANEL.v + 0.04), t1 = P(cageU(1), PANEL.v + 0.04);
    const q0 = [(c.x + t0.x) / 2 - 40, c.y - 66], q1 = [(c.x + t1.x) / 2 - 30, c.y - 58];
    // 纜線的最高點（二次貝茲 t=.5）：卡片的錨點放這裡
    const apex = { x: +(0.25 * (c.x - 2) + 0.5 * q0[0] + 0.25 * t0.x).toFixed(1), y: +(0.25 * (c.y - 6) + 0.5 * q0[1] + 0.25 * t0.y).toFixed(1) };
    return { c, t0, t1, q0, q1, apex }; })();
  function gFly() { const { c, t0, t1, q0, q1 } = FLY;
    return `<g data-seg="connector" data-part="sw_fly">${fx.glass(c.x - 6, c.y - 10, 12, 10, { fill: 'var(--dg-steel)', cls: 'part', rx: 1.5, t: 2 })}
      <path class="fly flow part" d="M${c.x - 2},${c.y - 6} Q${q0[0]},${q0[1]} ${t0.x},${t0.y}"/>
      <path class="fly flow part" d="M${c.x + 1},${c.y - 4} Q${q1[0]},${q1[1]} ${t1.x},${t1.y}"/></g>`; }
  // ---- 氣流：前進後出（規格書 §3-D）。虛線受 #dgAnim 控制。
  const gAir = () => `<g pointer-events="none">${[60, 176, 300].map(u => `<path class="air" d="M${pt(u, 0.13)} L${pt(u, 0.86)}"/>`).join('')}</g>`;
  // ---- 供電：PSU（後方）→ VRM（貼著 ASIC）→ ASIC，由高壓到低壓，而且線比訊號線粗
  const gPower = () => `<g pointer-events="none"><path class="pw flow" d="M${pt(PSUS[0].u + 8, 0.86)} L${pt(PSUS[0].u + 8, 0.66)} L${pt(VRM.u0 + 24, 0.66)} L${pt(VRM.u0 + 24, VRM.v + 0.04)}"/></g>`;
  /* ---- 光束（這張圖的動畫）：光纖進來（--dg-cool，發光）→ 籠架 3 → 電訊號走差動對到 ASIC（--dg-sig，發光）
       → ASIC 決定往哪個埠出去 → 走另一條差動對到籠架 6（--dg-sig，不發光、反向流動）→ 光纖出去（--dg-cool，不發光）。
       雙向：進來的那一條與回去的那一條接的是**不同的埠、同一顆晶片**。SMIL 光點沿電訊號進來那一條跑。*/
  function gBeams() {
    const tin = TRACES.find(t => t.i === 3), tout = TRACES.find(t => t.i === 6);
    const fin = P(cageU(3), PANEL.v), fout = P(cageU(6), PANEL.v);
    const dIn = 'M' + tin.pts.slice().reverse().map(([u, v]) => pt(u, v)).join(' L');
    const FY = PYB + 96;   // 光纖從畫布左下、右下進出（前面板朝向讀者，所以光纖在板子「前面」）
    const fibIn = `M24,${FY} C90,${FY} 168,${PYB + 40} ${fin.x},${PYB + 2}`, fibOut = `M${fout.x},${PYB + 2} C${fout.x + 40},${PYB + 40} 470,${FY} 576,${FY}`;
    return `<g pointer-events="none">
      ${fx.beam(fibIn, { color: 'var(--dg-cool)', w: 2.2, flow: true, dots: [[24, FY]] })}
      ${fx.beam(dIn, { color: 'var(--dg-sig)', w: 2, flow: true, dots: [[fin.x, PYB - 8]] })}
      ${fx.beam(tout.d, { color: 'var(--dg-sig)', w: 2, flow: true, glow: false, cls: 'rev', dots: [[P(tout.uT, PANEL.v + 0.04).x, P(tout.uT, PANEL.v + 0.04).y]] })}
      ${fx.beam(fibOut, { color: 'var(--dg-cool)', w: 2.2, flow: true, glow: false, cls: 'rev', dots: [[576, FY]] })}
      <circle r="3.2" fill="var(--dg-sn)" opacity=".95"><animateMotion dur="6s" repeatCount="indefinite" path="${dIn}"/></circle></g>`;
  }

  /* ================================================================ ② 疊構節律條（純 2D）
     規格書 §3-A 的兩條硬規則：**每一層高速訊號層的正上方與正下方都必須各有一層完整的接地參考層**；**疊構必須上下對稱**。
     下面這張表由上到下讀，而且**完全鏡像對稱**（正中央是電源層）。*/
  const LY = [[5, 'sm'], [5, 'out'], [10, 'pp'], [5, 'gnd'], [9, 'core'], [5, 'sig'], [9, 'core'], [5, 'gnd'],
    [20, 'rep'], [8, 'pwr'], [20, 'rep'],
    [5, 'gnd'], [9, 'core'], [5, 'sig'], [9, 'core'], [5, 'gnd'], [10, 'pp'], [5, 'out'], [5, 'sm']];
  const LY_FILL = { sm: 'var(--dg-sr)', out: 'var(--dg-cu)', pp: 'var(--dg-pp)', core: 'var(--dg-pcb-core)', gnd: 'var(--dg-cu)', sig: 'var(--dg-pcb-core)', pwr: 'var(--dg-cu)', rep: 'var(--dg-pcb-core)' };
  // core＝雙面覆銅的內層芯板（CCL 本身）；pp＝半固化片（玻纖布＋樹脂）；其餘的銅與線路是 PCB 廠做的
  const LY_SEG = { sm: 'hdi_pcb', out: 'hdi_pcb', pp: 'ccl_material', core: 'ccl', gnd: 'hdi_pcb', sig: 'hdi_pcb', pwr: 'hdi_pcb', rep: 'ccl' };
  function stack(x0, y0) {
    const W = 132, byKind = {}, mark = {}; let y = y0;
    LY.forEach((o) => { const h = o[0], k = o[1];
      (byKind[k] = byKind[k] || []).push(R(x0, y, W, h, LY_FILL[k], 'part')
        + (k === 'sig' ? [0, 1, 2, 3, 4, 5].map(j => R(x0 + 5 + j * 21, y + 1, 7, h - 2, 'var(--dg-sig)') + R(x0 + 14 + j * 21, y + 1, 7, h - 2, 'var(--dg-sig)')).join('') : '')
        + (k === 'core' || k === 'pp' ? [0, 1, 2, 3, 4, 5, 6, 7, 8].map(j => `<path class="lyl" d="M${x0 + 8 + j * 14},${y}V${y + h}"/>`).join('') : '')
        + (k === 'rep' ? `<text class="num" x="${x0 + W / 2}" y="${y + 13}" text-anchor="middle" style="fill:var(--dg-ink-3);font-weight:700">⋮ ×N</text>` : ''));
      if (mark[k] == null) mark[k] = +(y + h / 2).toFixed(1);
      y += h; });
    const svg = Object.keys(byKind).map(k => `<g data-seg="${LY_SEG[k]}" data-part="sw_ly_${k}">${byKind[k].join('')}</g>`).join('')
      + [0, 1, 2, 3, 4, 5, 6].map(j => `<circle cx="${x0 + 26 + j * 13}" cy="${y0 + 4}" r="2.6" fill="var(--dg-sw-gold)"/>`).join('');
    return { svg, mark, bot: y };
  }
  // 背鑽孔特寫：上半段有銅、下半段孔徑較大而且**沒有銅**
  function backdrill(x0, y0, h) {
    const w = 150, cut = +(y0 + h * 0.56).toFixed(1);
    return `<g data-seg="hdi_pcb" data-part="sw_backdrill">
      <rect class="part" x="${x0}" y="${y0}" width="${w}" height="${h}" rx="3" fill="var(--dg-pcb-core)"/>
      ${[0, 1, 2, 3, 4, 5, 6, 7].map(j => `<path class="lyl" d="M${x0},${(y0 + 6 + j * (h - 12) / 7).toFixed(1)}H${x0 + w}"/>`).join('')}
      ${R(x0 + 26, y0 + 4, 16, h - 8, 'var(--dg-edge)', '', 2)}${R(x0 + 26, y0 + 4, 4, h - 8, 'var(--dg-cu)')}${R(x0 + 38, y0 + 4, 4, h - 8, 'var(--dg-cu)')}
      <path d="M${x0 + 32},${cut}H${x0 + 58}" stroke="var(--dg-err)" stroke-width="1.8" fill="none"/>
      ${R(x0 + 100, y0 + 4, 16, cut - y0 - 4, 'var(--dg-edge)', '', 2)}${R(x0 + 100, y0 + 4, 4, cut - y0 - 4, 'var(--dg-cu)')}${R(x0 + 112, y0 + 4, 4, cut - y0 - 4, 'var(--dg-cu)')}
      ${R(x0 + 96, cut, 24, y0 + h - cut - 4, 'var(--dg-edge)', '', 2, '.9')}
    </g>`;
  }

  /* ================================================================ ③ 800G 可插拔光模組
     外型對照：OSFP **自帶鰭片**、QSFP-DD800 **平頂**靠籠架散熱（多個來源一致，信心高）。⚠ 功耗瓦數各家講的不一樣，一個瓦數都不寫。*/
  function formFactor(x0, y0, osfp) {
    const w = 118, h = 30;
    const top = osfp
      ? [0, 1, 2, 3, 4, 5, 6, 7].map(j => R(x0 + 16 + j * 10, y0 - 14, 4, 14, 'var(--dg-ni)', '', 1)).join('')
      : R(x0 + 8, y0 - 17, w - 4, 11, 'var(--dg-ni)', '', 2, '.7')
        + [0, 1, 2, 3, 4, 5, 6].map(j => R(x0 + 16 + j * 13, y0 - 27, 4, 11, 'var(--dg-ni)', '', 1, '.7')).join('')
        + `<text class="num" x="${x0}" y="${y0 - 34}" style="fill:var(--dg-ink-3)">散熱片長在籠架上</text>`;
    return `<g data-seg="optical" data-part="sw_ff_${osfp ? 'osfp' : 'qsfpdd'}">
      ${top}
      ${fx.glass(x0, y0, w, h, { fill: 'var(--dg-el)', cls: 'part', rx: 3, t: 2 })}
      ${R(x0 + 4, y0 + 5, 13, h - 10, 'var(--dg-cool)', '', 2, '.85')}
      ${R(x0 + w, y0 + 6, 9, h - 12, 'var(--dg-ni)', 'part', 2)}
      ${[0, 1, 2, 3, 4, 5, 6, 7].map(j => R(x0 + w - 34 + j * 3.8, y0 + h - 5, 2.2, 5, 'var(--dg-sw-gold)')).join('')}
      <text class="lbl" x="${x0}" y="${y0 + h + 20}">${osfp ? 'OSFP：模組自帶鰭片' : 'QSFP-DD800：平頂'}</text>
      <text class="sub" x="${x0}" y="${y0 + h + 38}">${osfp ? '體積較大、散熱裕度較高' : '沿用 QSFP 機構、可向下相容'}</text>
    </g>`;
  }
  function moduleCut(x0, y0) {
    const W = 346, H = 118;
    const blk = (dx, w, y, h, t, fill, seg, id) =>
      `<g data-seg="${seg}" data-part="${id}">${fx.glass(x0 + dx, y, w, h, { fill, cls: 'part', rx: 2.5, t: 2 })}`
      + `<text class="num" x="${x0 + dx + w / 2}" y="${y + h / 2 + 4}" text-anchor="middle" style="fill:var(--dg-ink)">${t}</text></g>`;
    const RY = y0 + 12, TY = y0 + 64;   // 收（上）、發（下）
    const lit = (d, rev) => `<path class="flow${rev ? ' rev' : ''}" d="${d}" stroke="var(--dg-cool)" stroke-width="2.6" fill="none" stroke-linecap="round"/>`;
    const ele = (d, rev) => `<path class="flow${rev ? ' rev' : ''}" d="${d}" stroke="var(--dg-sig)" stroke-width="2.4" fill="none" stroke-linecap="round"/>`;
    return `<g>
      <rect class="frame" x="${x0}" y="${y0}" width="${W}" height="${H}" rx="6"/>
      <g data-seg="optical" data-part="sw_mod_fiber">
        ${lit(`M${x0 - 36},${RY + 21}H${x0 + 12}`)}${lit(`M${x0 - 36},${TY + 21}H${x0 + 12}`, true)}
        ${R(x0 + 8, y0 + 8, 16, H - 16, 'var(--dg-cool)', 'part', 2, '.5')}
      </g>
      ${blk(32, 48, y0 + 8, H - 16, '光耦合', 'var(--dg-glass)', 'optical', 'sw_mod_fau')}
      ${blk(86, 50, RY, 42, 'PD', 'var(--dg-el)', 'optical_epi', 'sw_mod_pd')}
      ${blk(142, 50, RY, 42, 'TIA', 'var(--dg-el)', 'optical', 'sw_mod_tia')}
      ${blk(86, 50, TY, 42, '雷射', 'var(--dg-el)', 'optical_epi', 'sw_mod_ld')}
      ${blk(142, 50, TY, 42, '驅動 IC', 'var(--dg-el)', 'optical', 'sw_mod_drv')}
      ${blk(198, 64, y0 + 18, H - 36, 'DSP', 'var(--dg-si)', 'optical', 'sw_mod_dsp')}
      ${lit(`M${x0 + 80},${RY + 21}H${x0 + 86}`)}${lit(`M${x0 + 86},${TY + 21}H${x0 + 80}`, true)}
      ${ele(`M${x0 + 192},${RY + 21}H${x0 + 198}`)}${ele(`M${x0 + 198},${TY + 21}H${x0 + 192}`, true)}
      <g data-seg="connector" data-part="sw_mod_gold">
        ${ele(`M${x0 + 262},${RY + 21}H${x0 + 280}`)}${ele(`M${x0 + 280},${TY + 21}H${x0 + 262}`, true)}
        ${[0, 1, 2, 3, 4, 5, 6, 7].map(j => R(x0 + 280, y0 + 12 + j * 12, 46, 7, 'var(--dg-sw-gold)', 'part', 1.5)).join('')}
      </g>
    </g>`;
  }

  /* ================================================================ ④ 可插拔 vs CPO
     兩格用**同一組畫法**，只有「那條藍線（電訊號）的長度」不一樣 —— 這張圖最後一個答案就是這一件事。*/
  function compare(x0, y0, w, cpo) {
    const H = 164, by = y0 + 56, bh = 40;
    const asicX = cpo ? x0 + 150 : x0 + 30;
    const panelX = x0 + w - 44;
    const eng = cpo ? [0, 1, 2, 3].map(j => R(asicX - 26, by + 4 + j * 8.5, 20, 6.5, 'var(--dg-cool)', 'part', 1.5, '.85') + R(asicX + 62, by + 4 + j * 8.5, 20, 6.5, 'var(--dg-cool)', 'part', 1.5, '.85')).join('') : '';
    const eX0 = cpo ? asicX - 26 : asicX + 62;
    const eLen = cpo ? 26 : panelX - 36 - (asicX + 62);
    const lit = (d, rev) => `<path class="flow${rev ? ' rev' : ''}" d="${d}" stroke="var(--dg-cool)" stroke-width="3" fill="none" stroke-linecap="round"/>`;
    return `<g>
      <rect class="frame" x="${x0}" y="${y0}" width="${w}" height="${H}" rx="8"/>
      <text class="hd" x="${x0 + 14}" y="${y0 + 22}">${cpo ? 'CPO：光引擎搬到晶片旁邊' : '可插拔光模組（現在的主流）'}</text>
      <text class="sub" x="${x0 + 14}" y="${y0 + 40}">${cpo ? '光引擎與 ASIC 共用同一片基板，光纖直接從基板邊緣拉出去' : '光電轉換全在前面板的模組裡，電訊號要先走過整片板子'}</text>
      ${fx.glass(x0 + 14, by + bh + 6, w - 28, 7, { fill: 'var(--dg-pcb)', rx: 2 })}
      <g data-seg="${cpo ? 'optical' : 'hdi_pcb'}" data-part="sw_cmp_${cpo ? 'cpo' : 'plug'}">
        ${eng}
        ${fx.glass(asicX, by, 62, bh, { fill: 'var(--dg-si)', cls: 'part', rx: 3, t: 2 })}
        <text class="num" x="${asicX + 31}" y="${by + 24}" text-anchor="middle" style="fill:var(--dg-ink)">ASIC</text>
        <path d="M${eX0},${by + bh + 18}h${eLen}" stroke="var(--dg-sig)" stroke-width="5" fill="none" stroke-linecap="round"/>
        ${cpo
        ? lit(`M${asicX + 82},${by + 12}H${panelX + 4}`) + lit(`M${panelX + 4},${by + 30}H${asicX + 82}`, true)
        : fx.glass(panelX - 36, by + 6, 36, bh - 12, { fill: 'var(--dg-el)', cls: 'part', rx: 2, t: 2 })
          + lit(`M${panelX + 26},${by + 12}H${panelX + 4}`) + lit(`M${panelX + 4},${by + 30}H${panelX + 26}`, true)}
        ${R(panelX, by - 2, 8, bh + 4, 'var(--dg-ni)', 'part', 2)}
      </g>
      <text class="num" x="${eX0}" y="${by + bh + 34}" style="fill:var(--dg-sig)">電訊號走${cpo ? '封裝內幾 mm' : '整片板子'}</text>
      <text class="sub" x="${x0 + 14}" y="${y0 + H - 10}"${cpo ? '' : ' style="fill:var(--dg-warn)"'}>${cpo
      ? '取捨：壞一顆光引擎不能像模組那樣抽換，要修就是整台'
      : '取捨：壞了抽換就好，但電通道損耗大、模組本身很耗電'}</text>
    </g>`;
  }

  /* ================================================================ 整張圖 */
  function switchBoard() {
    const Y2 = 320, Y3 = Y2 + 430, Y4 = Y3 + 560;   // 三個章節的自然座標（wireFolds 會重新堆疊）
    const st = stack(30, Y2 + 36);
    const ld = (k, ly) => `<path class="lyl" d="M162,${st.mark[k]}H174V${ly - 4}H186" style="opacity:.75"/>`;
    // 柔陰影：板子、前面板、風扇、PSU、拆開的三層各一個影子，全部包成一個群組（第三個、也是最後一個 feGaussianBlur）
    const shadows = fx.shadows(
      `<path d="M${BX + 4},${BY + BT + 12} L${BX + BW - 2},${BY + BT + 12} L${BX + BW + DX - 2},${BY + BT + 12 + DY} L${BX + DX + 4},${BY + BT + 12 + DY}Z"/>`
      + FANS.map(f => { const b = P(f.u, f.v); return `<rect x="${b.x + 3}" y="${b.y - f.h + 8}" width="${f.w}" height="${f.h}" rx="5"/>`; }).join('')
      + PSUS.map(s => { const b = P(s.u, s.v); return `<rect x="${b.x + 3}" y="${b.y - s.h + 8}" width="${s.w}" height="${s.h}" rx="5"/>`; }).join('')
      + `<rect x="${AB.x + 4}" y="${LAY.sub[1] + 6}" width="${ASIC.w}" height="6" rx="3"/><rect x="${AB.x + 14}" y="${LAY.die[1] + 8}" width="${ASIC.w - 24}" height="7" rx="3"/><rect x="${HS.x + 4}" y="${LAY.hs[1] + 8}" width="${HS.w}" height="5" rx="3"/>`);
    const fanA = P(FANS[0].u, FANS[0].v), psuA = P(PSUS[1].u + PSUS[1].w, PSUS[1].v), cpuA = P(CPU.u, CPU.v), vrmA = P(VRM.u0, VRM.v);

    return `<svg class="dg dgm rs dgsw" viewBox="0 0 ${CW} ${Y4 + 520}" width="100%" style="display:block">${STYLE}${SW_STYLE}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead，SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">交換器板卡：一顆晶片對上所有的埠，逼出 40 層以上的板子</text>
      <text class="cap ext" x="0" y="0">拆掉上蓋、從前上方看進去的 2U 板卡：前面板一整排光模組籠架（下方），一顆交換器晶片坐在正中央、載板／晶片／散熱片往上拆開浮著，上千條等長差動對從它底下扇出到每一個埠（近的埠繞路、遠的直走）；風扇與電源在後方（右上）。青綠光束＝光（光纖進出前面板）、藍色光束＝電（籠架 → 晶片 → 另一個籠架，雙向）、橘線＝供電（PSU → VRM → 晶片）。板子前緣看得到一疊層；為什麼要 40 層、800G 光模組裡有什麼、可插拔 vs CPO 收在下面三段。</text>

      <!-- ================= §1 半層疊的板卡 =================
           畫的順序＝由遠到近、由下往上：陰影 → 板子 → 前緣的層 → 走線 → 供電線 → 氣流 → 風扇／PSU／處理器（後方）→ VRM
           → 飛越纜線 → ASIC 三層（拆開浮著）→ 前面板（最近，永遠最後）→ 光束。-->
      ${shadows}
      ${gBoard()}${gLayers()}
      ${gTraces()}${gPower()}${gAir()}
      ${gFans()}${gPsu()}${gCpu()}${gVrm()}
      ${gFly()}${gAsic()}${gHs()}
      ${gPanel()}
      ${gBeams()}

      <!-- ================= 說明卡片（HTML，左右兩欄）：左欄錨點在畫布左半邊、右欄錨點在右半邊 =================
           卡片只放一句話（標題 ＋ 一行）：三欄模式的卡片欄只有 220px，卡片欄不可以比畫布高；長說明在零件小卡與章節裡 -->
      ${extRow({ side: 'l', no: 1, seg: 'thermal', part: 'sw_fan', color: COL.therm, ax: fanA.x - 7, ay: fanA.y - FANS[0].h / 2,
    title: '系統風扇（後方）', sub: '扇框、扇葉、輪轂；風前進後出' })}
      ${extRow({ side: 'l', no: 3, seg: 'switch', part: 'sw_cpu', color: COL.cpu, ax: cpuA.x - 8, ay: cpuA.y - 7,
    title: '管理用處理器（角落）', sub: '只管設定與監控，不碰封包' })}
      ${extRow({ side: 'l', no: 5, seg: 'connector', part: 'sw_fly', color: COL.sig, ax: FLY.apex.x, ay: FLY.apex.y - 6,
    title: '近晶片飛越纜線 flyover', sub: '訊號改走纜線，繞開 PCB' })}
      ${extRow({ side: 'l', no: 7, seg: 'power', part: 'sw_vrm', color: COL.pwr, ax: vrmA.x - 8, ay: vrmA.y - 4,
    title: '板上多相供電 VRM', sub: '大電流走不遠，所以緊貼晶片' })}
      ${extRow({ side: 'l', no: 9, seg: 'optical', part: 'sw_cage', color: COL.opt, ax: PX + 5, ay: (PYT + PYB) / 2,
    title: '前面板光模組籠架', sub: '一整排同規格；2U 排 64 個' })}
      ${extRow({ side: 'l', no: 11, seg: 'hdi_pcb', part: 'sw_pcb', color: COL.pcb, ax: BX + 8, ay: BY + BT / 2,
    title: '主板：高層數多層板 MLB', sub: '約 40 層以上，依架構而異' })}
      ${extRow({ side: 'r', no: 2, seg: 'power', part: 'sw_psu', color: COL.pwr, ax: psuA.x + 6, ay: psuA.y - PSUS[1].h + 8,
    title: '電源供應器 PSU（後方）', sub: '1+1 冗餘、可熱抽換' })}
      ${extRow({ side: 'r', no: 4, seg: 'thermal', part: 'sw_hs', color: COL.therm, ax: HS.x + HS.w + 6, ay: LAY.hs[0] - 6,
    title: '晶片散熱片', sub: '鰭片順著前後氣流，不擋風' })}
      ${extRow({ side: 'r', no: 6, part: 'sw_asic', color: COL.off, ax: AB.x + ASIC.w + 6, ay: LAY.die[0] + 4,
    title: '交換器晶片 switch ASIC', sub: '外商供應，台股沒有直接對應' })}
      ${extRow({ side: 'r', no: 8, seg: 'ccl', part: 'sw_layers', color: COL.pcb, ax: BX + BW - 8, ay: BY + BT / 2,
    title: '前緣那一疊：core／prepreg', sub: 'CCL 廠交板材，PCB 廠蝕線路' })}
      ${note({ side: 'r', warn: true, title: '★ 族群名單比這張圖寬',
    lines: ['族群含電信與消費性網通；這張只畫資料中心交換器那一段。',
      '示意圖，非實物比例；16 個籠架代表 64 個、19 條疊構代表約 40 層以上。',
      '畫埠側進風機種；市占、良率、單價、瓦數一個都不寫。'] })}

      <!-- ================= ② 板子為什麼要這麼多層（預設收合；座標由 wireFolds 量）================= -->
      ${fold('sw2', '② 層數是被訊號逼出來的：訊號—地—訊號—地', '疊構節律條、背鑽特寫、為什麼是 40 層以上', `
      <text class="hd" x="16" y="${Y2 + 20}">每一層高速訊號的上下都要各有一層完整接地層，而且疊構上下對稱</text>
      ${st.svg}
      ${ld('out', Y2 + 48)}${ld('gnd', Y2 + 92)}${ld('sig', Y2 + 136)}${ld('pwr', Y2 + 180)}
      <text class="lbl" x="190" y="${Y2 + 48}">外層線路 ＋ 防焊</text>
      <text class="sub" x="190" y="${Y2 + 65}">球柵陣列銲墊在這一層</text>
      <text class="lbl" x="190" y="${Y2 + 92}">接地層（完整的一片銅）</text>
      <text class="sub" x="190" y="${Y2 + 109}">訊號層的上下都要各有一層</text>
      <text class="lbl" x="190" y="${Y2 + 136}">高速訊號層（差動對）</text>
      <text class="sub" x="190" y="${Y2 + 153}">成雙成對、兩條線長度要配對</text>
      <text class="lbl" x="190" y="${Y2 + 180}">電源層（厚銅）</text>
      <text class="sub" x="190" y="${Y2 + 197}">疊構上下對稱，不然壓合會翹</text>
      ${backdrill(404, Y2 + 40, 104)}
      <text class="num" x="412" y="${Y2 + 162}" style="fill:var(--dg-err)">沒背鑽</text>
      <text class="num" x="486" y="${Y2 + 162}" style="fill:var(--dg-accent)">背鑽過</text>
      <text class="lbl" x="404" y="${Y2 + 186}">背鑽（back-drill）</text>
      <text class="sub" x="404" y="${Y2 + 203}">通孔用不到的那段銅是天線</text>
      <rect class="frame" x="16" y="${Y2 + 220}" width="544" height="124" rx="8"/>
      <text class="hd" x="30" y="${Y2 + 242}">為什麼是 40 層以上</text>
      <text class="sub" x="30" y="${Y2 + 264}">一顆 51.2T 的晶片有 512 條 SerDes 通道，收發各一組差動對 —— 光是高速 I/O 就上千條，</text>
      <text class="sub" x="30" y="${Y2 + 282}">而且全部要從同一顆球柵陣列底下逃出來。每一層訊號層的上下都要各配一層完整接地層，</text>
      <text class="sub" x="30" y="${Y2 + 300}">阻抗才守得住 → 線塞不下就只能往上疊層。圖上畫 19 條，實機約 40 層以上（依架構而異）。</text>
      <text class="sub" x="30" y="${Y2 + 322}" style="fill:var(--dg-warn)">層數多了還要換超低損耗板材、低粗糙度銅箔，而且是多次壓合 —— 錯一次整片報廢。</text>
      <text class="hd" x="16" y="${Y2 + 370}">速率怎麼換算（只用來檢查有沒有畫離譜，不當規格數字標在零件旁邊）</text>
      <text class="num" x="30" y="${Y2 + 392}">64 埠 × 800G ＝ 51.2T　｜　64 埠 × 1.6T ＝ 102.4T　｜　32 埠 × 800G ＝ 25.6T（1U）</text>
      <text class="num" x="30" y="${Y2 + 410}">512 條 SerDes 通道 × 100G ＝ 51.2T　｜　8 顆 6.4T 光引擎 ＝ 51.2T（CPO）</text>`)}

      <!-- ================= ③ 800G 可插拔光模組 ＋ 價值鏈流程列（預設收合）================= -->
      ${fold('sw3', '③ 800G 可插拔光模組｜價值鏈流程列', '光模組裡有什麼（光在左、電在右）、OSFP 與 QSFP-DD 兩種外型差在哪、五格價值鏈', `
      <text class="hd" x="16" y="${Y3 + 20}">800G 可插拔光模組：裡面有什麼、兩種外型差在哪</text>
      ${formFactor(16, Y3 + 84, true)}
      ${formFactor(16, Y3 + 226, false)}
      <text class="cap" x="16" y="${Y3 + 318}">兩種機構不相容，插不進對方的埠。</text>
      <text class="cap" x="196" y="${Y3 + 44}">光在左、電在右：上排是收（光→電），下排是發（電→光）。</text>
      ${moduleCut(196, Y3 + 52)}
      <text class="cap" x="160" y="${Y3 + 194}">光纖</text>
      <text class="sub" x="196" y="${Y3 + 214}">光耦合（透鏡／光纖陣列 FAU）：矽光子晶片與光纖之間的對準接合</text>
      <text class="sub" x="196" y="${Y3 + 232}">雷射晶粒／光偵測器 PD：發端雷射加調變；收端 PD 把光變回電流</text>
      <text class="sub" x="196" y="${Y3 + 250}">TIA／驅動 IC：收端把微弱電流放大；發端推上調變器</text>
      <text class="sub" x="196" y="${Y3 + 268}">DSP：模組裡最大也最耗電的一顆，做等化與前向錯誤更正</text>
      <text class="sub" x="196" y="${Y3 + 286}">金手指：模組唯一的電接點，插進籠架就接到主板 —— 這就是「可插拔」</text>
      <text class="cap" x="16" y="${Y3 + 346}">從板材到交付雲端：這條鏈上台股站在哪幾格（點一格＝篩那個環節的成分股）</text>
      ${processBar(8, Y3 + 356, [{ seg: 'ccl', t: '銅箔基板 CCL', s: '超低損耗板材' },
    { seg: 'hdi_pcb', t: '高層數多層板', s: '40 層以上・背鑽' },
    { seg: 'optical', t: '光模組／光引擎', s: '800G 可插拔・CPO' },
    { seg: 'connector', t: '高速連接／線材', s: '飛越纜線・籠架' },
    { seg: 'switch', t: '交換器整機', s: '白牌 ODM 組裝' }], 164, { cols: 3 })}`)}

      <!-- ================= ④ 可插拔 vs CPO（預設收合）================= -->
      ${fold('sw4', '④ 可插拔與共同封裝光學（CPO）：差別只有電訊號走多遠', '兩種架構上下並排、電訊號路徑長度對照、插入損耗兩個來源怎麼處理', `
      <text class="hd" x="16" y="${Y4 + 20}">為什麼要把光引擎搬到晶片旁邊：差別只有「電訊號走多遠」</text>
      ${compare(16, Y4 + 32, 544, false)}
      ${compare(16, Y4 + 208, 544, true)}
      <text class="sub" x="16" y="${Y4 + 398}" style="fill:var(--dg-warn)">★ 電通道插入損耗：可插拔整條路徑約 20 dB 以上；搬進封裝之後只剩個位數 dB。</text>
      <text class="sub" x="16" y="${Y4 + 416}" style="fill:var(--dg-warn)">　 速率每升一級，這件事就更嚴重一次。</text>
      <text class="cap" x="16" y="${Y4 + 440}">CPO 那一側兩個來源給的損耗數字不同（1～2 dB 與約 4 dB），所以只寫「個位數」，不挑一個當定論。</text>
      <text class="cap" x="16" y="${Y4 + 458}">示意圖，非實物比例｜層數、走線條數、光模組數量與元件位置均為示意；圖上畫 16 個籠架（實機 64 個）、</text>
      <text class="cap" x="16" y="${Y4 + 476}">19 條疊構（實機約 40 層以上，⋮ ×N，依架構而異）。零件顏色＝環節色，點零件只亮不篩</text>
      <text class="cap" x="16" y="${Y4 + 494}">（點環節色標才會篩）。來源與信心度見 docs/diagram_specs/switch_board.md。</text>`)}
    </svg>`;
  }

  window.DG.register('switch_wireless', {
    level: 'group', chain: 'ai_server',
    name: '網通：交換器板卡 ＋ 800G 光模組 ＋ CPO',
    draw: switchBoard, native: CW, scene: 'switch_wireless',   /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。檔頭 §0 原本寫「不做真 3D」，
        推翻它的是那個理由**漏掉的另一半**（逐張寫在 DECISIONS #250），不是那個理由本身。*/
    q: '一台 800G／1.6T 交換器的板子上到底有什麼？光模組插在前面板跟搬進封裝（CPO）差在哪、台股吃得到哪幾格？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       v2 之後零件的名字不在 SVG 裡（卡片是 HTML），小卡拿不到 text.lbl，所以每一個零件都要自己給 name。
       cos 只放代號（沒寫就走預設：該環節全部台股）；R4：台股沒有人做的零件要明說（ASIC）。*/
    parts: {
      sw_asic: { name: '交換器晶片（switch ASIC）', desc: '板上最大的單一元件：一顆晶片對上所有的埠，上千條差動對從它底下扇出。51.2T＝64 埠 × 800G、102.4T＝64 埠 × 1.6T。', cos: [],
        none: '★ 這一級由外商供應（Broadcom、Marvell 等），台股沒有直接對應 —— 所以不掛任何環節；「IC 設計」那一格的台股沒有一家供應這一級 ASIC。晶片本身的製造與封裝在半導體鏈那幾張圖。' },
      sw_hs: { name: '晶片散熱片（鰭片順著前後氣流）', desc: '這一顆 ASIC 是幾百瓦等級的發熱體。鰭片一片片等距、沿前後方向拉長 —— 畫成左右向就是擋住風。主流仍是氣冷，液冷是新機種。' },
      sw_fan: { name: '系統風扇（後方、可熱抽換）', desc: '前面板全部給光口，所以風扇在後方：冷風從前面板的埠之間吸進來，橫掠光模組與散熱鰭片，由後方風扇抽出。畫的是朝向機箱內側的進風面（扇框、扇葉、輪轂）。' },
      sw_psu: { name: '電源供應器 PSU（後方、1+1 冗餘）', desc: '交流／直流母線進來，往前送到板上的 VRM；兩顆冗餘、可熱抽換。整機功耗數字各家不同，這裡不寫。' },
      sw_vrm: { name: '板上多相供電模組（VRM）', desc: '把 12V／48V 降到次伏特級的核心電壓。電流大、壓降走不遠，所以一定緊貼晶片；一排電感並聯輪流工作（多相）。' },
      sw_cage: { name: '前面板光模組籠架（OSFP／QSFP-DD800）', desc: '一整面同規格的 I/O 全部朝同一個方向：2U 排 64 個 × 800G（圖上畫 16 個，示意）。光模組本身是機箱裡的發熱大戶。' },
      sw_fly: { name: '近晶片飛越纜線（flyover cable）', desc: '高速訊號改走纜線、繞開 PCB：板子走不動的距離，用線來走。畫了它的那兩個埠，板子上就不再畫走線（不然等於同一個訊號走兩條路）。' },
      sw_pcb: { name: '主板：高層數多層板（MLB）', desc: '承載這一切的板子：800G／1.6T 世代約 40 層以上（依架構而異），要超低損耗板材、低粗糙度銅箔、背鑽，而且是多次壓合。' },
      sw_layers: { name: '板子前緣那一疊：core／prepreg 交替', desc: '前緣看得到一條一條的銅 —— 這片板子是很多片雙面覆銅的芯板（CCL）與半固化片交替壓起來的。板材由 CCL 廠交，線路是 PCB 廠蝕的。' },
      sw_cpu: { name: '管理用處理器（跑網路作業系統）', desc: '只管設定與監控，不碰封包轉送，所以很小、在角落；旁邊兩顆是記憶體。掛的是「交換器整機」那一格。' },
      sw_ly_out: { name: '外層線路 ＋ 防焊', desc: '球柵陣列銲墊與元件銲墊在這一層；外層是線路層，不是接地層，防焊在銅之外。' },
      sw_ly_gnd: { name: '接地層（完整的一片銅）', desc: '每一層高速訊號層的正上方與正下方都必須各有一層完整的接地參考層，阻抗才守得住 —— 這就是層數多的全部答案。' },
      sw_ly_sig: { name: '高速訊號層（差動對）', desc: '成雙成對的差動對、兩條線長度要配對；被上下兩層地夾住（帶狀線）。' },
      sw_ly_pwr: { name: '電源層（厚銅）', desc: '走大電流到 VRM 與晶片；畫在中段，確切位置依設計而異（圖上不標層號）。' },
      sw_ly_core: { name: '內層芯板 core（雙面覆銅的 CCL）', desc: '芯板本身就是 CCL 廠交的板材；800G／1.6T 要超低損耗等級。' },
      sw_ly_pp: { name: '半固化片 prepreg（玻纖布＋樹脂）', desc: '把 core 黏起來的膠片，壓合時流動固化；玻纖布與樹脂是再上一層的材料商。' },
      sw_ly_rep: { name: '中段省略（⋮ ×N）', desc: '「訊號 → 地 → 訊號 → 地」重複 N 次；圖上畫 19 條代表約 40 層以上，不假裝畫滿。' },
      sw_ly_sm: { name: '防焊', desc: '最外面的絕緣層，銅之外才是防焊。' },
      sw_backdrill: { name: '背鑽（back-drill）', desc: '通孔用不到的那一段銅柱是天線，會反射訊號，必須鑽掉：上半段有銅、下半段孔徑較大且沒有銅。背鑽一定在電鍍通孔之後。' },
      sw_ff_osfp: { name: 'OSFP：模組自帶鰭片', desc: '體積較大、散熱裕度較高；跟 QSFP-DD800 機構不相容。功耗瓦數各家講的不一樣，不寫。' },
      sw_ff_qsfpdd: { name: 'QSFP-DD800：平頂', desc: '靠籠架上的散熱片導熱；沿用 QSFP 機構、可向下相容。' },
      sw_mod_fiber: { name: '光纖（進出模組）', desc: '光在左、電在右：上排是收（光→電），下排是發（電→光）。' },
      sw_mod_fau: { name: '光學耦合（透鏡／光纖陣列 FAU）', desc: '矽光子晶片與光纖之間的對準接合介面。' },
      sw_mod_pd: { name: '光偵測器（PD）', desc: '收端：把光變回電流。' },
      sw_mod_ld: { name: '雷射晶粒', desc: '發端：雷射加調變，把電變成光。' },
      sw_mod_tia: { name: 'TIA（轉阻放大器）', desc: '收端把微弱電流放大。' },
      sw_mod_drv: { name: '驅動 IC', desc: '發端把訊號推上調變器。' },
      sw_mod_dsp: { name: 'DSP：模組裡最大也最耗電的一顆', desc: '做等化與前向錯誤更正，把訊號整回來。' },
      sw_mod_gold: { name: '金手指：模組唯一的電接點', desc: '插進籠架就接到主板，這就是「可插拔」。' },
      sw_cmp_plug: { name: '可插拔光模組（現在的主流）', desc: '光電轉換全在前面板的模組裡，電訊號要先走過整片板子：整條路徑約 20 dB 以上的插入損耗。壞了抽換就好。' },
      sw_cmp_cpo: { name: '共同封裝光學（CPO）', desc: '光引擎與 ASIC 共用同一片基板，光纖直接從基板邊緣拉出去；電訊號只走封裝內幾 mm（個位數 dB）。壞一顆光引擎不能像模組那樣抽換。' },
    },
  });
})();
