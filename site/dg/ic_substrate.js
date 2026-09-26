/* IC 載板：ABF 增層剖面 —— docs/diagram_plan.md 的第 3 張（族群 `ic_substrate`、ai_server 鏈）

   合約＝`docs/diagram_specs/abf_substrate.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的四件事：

     · §0-A **不做真 3D**（`scene: null`）。要加 3D 就是改規格書、重新簽，不准實作時順手加。
     · §0-B（一）跟 `pcb_stackup`（PCB 硬板那張）的分工：**PCB 那張的下游是「把零件焊上去」，這張的下游是「把晶片黏上去」。**
       明列五樣這張圖不准畫：銅箔稜面三格、玻纖織紋放大格、四種孔對照、走線頂視小圖、表面處理比較表。這個檔一樣都沒有（M6）。
     · §0-B（二）跟 CoWoS 剖面（`ai_adv_packaging`）的分工：**中介層以上一律只畫灰色剪影、不標細節、不掛 `data-seg`**（M5、D2）。
     · §7-B／§7-C：查不到的東西一個數字都不編。畫面上唯一的百分比是 ABF 膜市占，而且必須連同「來源：今周刊 2026-05」一起寫（N1）。
       載板線寬、CTE 的 ppm、封裝 mm 數、供需缺口、良率與單價差距**全部不進畫面**。

   ---- 2026-09-22 v2（DECISIONS #238／#239 ＋ Andy 晚間的參考圖 docs/diagram_refs/2d_panel_dark_light.webp）----
   · 構圖：**等角爆炸層疊**（層疊類走這一套）。九片薄板（上防焊、U3、U2、U1、core、L1、L2、L3、下防焊）
     一片一片浮著，每一片都是 D.fx.glass 畫的**帶厚度、圓角、半透明漸層的玻璃板**（頂面 ＋ 前面 ＋ 右側面），
     層與層之間留 24px 的呼吸空間。**剖面內容畫在每一片的前面**（那正是原本的正剖面）：織紋、貫孔、細線、錐形微孔、防焊開窗、墊子，
     一條規則都沒有變（core 在正中間、上下各 3 層厚度相等、只有 core 有織紋、微孔朝 core 收窄、貫孔只穿 core）。
     拆開之後多出來的兩件事：微孔畫成**穿過層間空隙的小銅柱**（這一層的孔接到下一層的銅），疊孔靠虛線軸心對齊。
   · 訊號路徑用 D.fx.beam：一條發光光束（一個 feGaussianBlur）＋ 流動虛線 ＋ 端點光點；柔陰影一組（第二個 blur）。
     兩種模式構圖相同、只換材質與光：亮＝米白底＋柔陰影，暗＝深藍底＋發光；全部走 --dg-*／--fx-* token。
   · svg 根掛 `.rs`：閱讀模式字級升一階、說明卡片離開 SVG 變成 HTML（extRow 多傳 side）。畫布 980 → **520**，native 跟著改。
   · §1 從 606 壓到約 504：右欄九列說明全部變成卡片、三格放大與路線圖收進兩個章節（一個字沒刪，只改斷行與位置）。
   · 卡片與畫布上的零件是同一個 data-part：點卡片亮零件、點零件亮卡片。
   · 卡片元件色：core --dg-weave、ABF 膜 --dg-abf、銅件 --dg-cu、灰色剪影 --dg-mute；防焊與主機板不指定（落回環節色）——
     --dg-sr／--dg-pcb 在深底上對編號數字的對比不到 4.5，不拿來當卡片色。

   這個檔不碰 `site/index.html`／`site/three3d.js`。共用工具一律走 `window.DG`。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function' || !D.fx) return;   // diagrams.js 沒載到就安靜退出
  const { STYLE, extRow, note, processBar, fold, fx } = D;

  /* ================================================================ 版面常數（全部是畫布座標，寬 520）
     每一片薄板：前面 x ∈ [XL, XR]、厚度 t；頂面往右後上擠出 (DX, DY)；片與片之間的間距 G（含頂面的 20px，所以空氣是 4px）。*/
  const CW = 520, XL = 24, XR = 452, W = XR - XL, DX = 32, DY = -18, G = 22;
  const ISO = { dx: DX, dy: DY };

  /* 層界（由上往下，用厚度累加出來，所以「上下對稱」是算出來的不是手抄的）。
     **core 44、每一層增層 16 ＝ core 是任一層增層的 2.75 倍厚**（S2）；上下各三層、對應層厚度相同（S3）；
     防焊上下各 7、成對出現（S6）。*/
  const Y = { dieT: 26, dieB: 36, ubT: 36, ubB: 52, itT: 52, itB: 62, c4T: 62, c4B: 80 };
  const ORDER = [['srT', 7], ['u3', 16], ['u2', 16], ['u1', 16], ['core', 44], ['l1', 16], ['l2', 16], ['l3', 16], ['srB', 7]];
  (function stack() {
    let y = Y.c4B + G;
    ORDER.forEach(([k, h]) => { Y[k] = [y, y + h]; y += h + G; });
    Y.ball = Y.srB[1] + 18;                                // 錫球中心（r 12）
    Y.mbT = Y.ball + 16; Y.mbB = Y.mbT + 18;               // 主機板（只畫一小段）
  })();
  /* 每一層增層「自己那一層的銅」在**外側**：上半部在該層上緣、下半部在該層下緣
     —— 因為增層是從 core 往外一層一層長出來的，這也是微孔錐度方向的由來。*/
  const CUH = 6;
  const CU = { u3: Y.u3[0], u2: Y.u2[0], u1: Y.u1[0], coreT: Y.core[0], coreB: Y.core[1] - CUH,
    l1: Y.l1[1] - CUH, l2: Y.l2[1] - CUH, l3: Y.l3[1] - CUH };

  // 三種凸塊的位置（主視圖的節距是示意，真實比例在〔放大格 A〕）
  const PADS = [200, 226, 252, 278, 304, 330, 356, 382];        // bump pad／C4，節距 26
  const BALLS = [48, 113, 178, 243, 308, 373, 438];             // BGA 球墊，節距 65
  const UBUMPS = []; for (let i = 0; i < 16; i++) UBUMPS.push(228 + i * 8.5);   // 微凸塊，節距 8.5

  /* 孔的位置。core 貫孔三個，**只穿 core**（V1）；微孔一層一組，**只穿一層增層**（V2），
     上下兩側都朝 core 收窄（V3）；疊孔固定在 x=380（U1 與 U2 軸心對齊，V4）。*/
  const VIA = {
    core: [78, 250, 432],
    u1: [96, 190, 290], u2: [140, 262, 330], u3: [112, 200, 306, 432],
    l1: [130, 240, 386], l2: [104, 286, 410], l3: [170, 316, 424],
    stack: 380,
  };

  /* 卡片的元件色（token，不寫死）*/
  const COL = { core: 'var(--dg-weave)', abf: 'var(--dg-abf)', cu: 'var(--dg-cu-lit)', off: 'var(--dg-mute)' };   // 銅用亮面：選到的卡片標題在深底上 --dg-cu 只有 4.24:1

  /* ================================================================ 小工具 */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  // 頂面座標：u 沿板長、v 是深度（0 前緣、1 後緣）
  const tp = (u, v) => `${(u + v * DX).toFixed(1)},${(v * DY).toFixed(1)}`;
  // 頂面上的示意銅線（三條，不同深度）：這一層的線路往後延伸
  const topTraces = (n) => [0.3, 0.55, 0.8].slice(0, n).map(v =>
    `<path d="M${tp(8, v)} L${tp(W - 8, v)}" stroke="var(--dg-cu)" stroke-width="1.1" opacity=".38" fill="none"/>`).join('');
  // 頂面上的圓形（貫孔的蓋銅、防焊開窗看到的墊子）
  const topDots = (xs, rxv, fill, op) => xs.map(x =>
    `<ellipse cx="${(x - XL + 0.5 * DX).toFixed(1)}" cy="${(0.5 * DY).toFixed(1)}" rx="${rxv}" ry="${(rxv / 2).toFixed(1)}" fill="${fill}" opacity="${op}"/>`).join('');
  // 一片玻璃板（前面 ＋ 頂面 ＋ 右側面），前面那塊 rect 帶 .part 讓選取描邊有地方掛
  const plate = (r, fill, top) => fx.glass(XL, r[0], W, r[1] - r[0], { iso: ISO, fill, cls: 'part', rx: 4, top });
  // 柔陰影：每一片頂面往下 12px 的影子，全部包成一個群組（一次濾鏡）
  const plateShadow = (r) => `<path d="M${XL + 4},${r[1] + 12} L${XR - 2},${r[1] + 12} L${XR + DX - 2},${r[1] + 12 + DY} L${XL + DX + 4},${r[1] + 12 + DY}Z"/>`;

  /* 玻纖織紋。**整張圖只有 core 那一層可以呼叫它**（S4）——
     ABF 是不含織造玻纖的樹脂膜，那正是它能打出更小的孔、做出更細的線的原因（§7-A1）。*/
  function weave(x0, x1, y0, y1) {
    const h = y1 - y0, w = x1 - x0;
    const n = Math.max(1, Math.floor((h - 4) / 13));
    const gap = h / (n + 1), amp = Math.min(4, gap / 3);
    const seg = Math.min(18, Math.max(8, w / 6));
    const q1 = (seg / 4).toFixed(1), q2 = (seg / 2).toFixed(1), a = amp.toFixed(1);
    const rows = [];
    for (let i = 1; i <= n; i++) {
      const yy = (y0 + gap * i).toFixed(1);
      let d = `M${x0},${yy}`;
      for (let x = x0; x < x1 - seg; x += seg) d += `q${q1},-${a} ${q2},0 q${q1},${a} ${q2},0`;
      rows.push(`<path d="${d}" stroke="var(--dg-weave)" stroke-width="1.1" fill="none" opacity=".62"/>`);
    }
    const warp = [];
    for (let x = x0 + seg / 2; x < x1 - 2; x += seg) warp.push(`M${x.toFixed(1)},${y0 + 2} v${(h - 4).toFixed(1)}`);
    return rows.join('') + `<path d="${warp.join(' ')}" stroke="var(--dg-weave)" stroke-width=".8" fill="none" opacity=".3"/>`;
  }

  /* 一層裡的銅線。載板的線寬 7／節距 16，最底下那一小段主機板的走線寬 34／節距 60 ——
     兩者放在同一張圖上，「**細一個量級**」這句話就不必靠數字（§7-B1：三個來源的載板線寬互相對不起來）。*/
  function traces(y, x0, x1, w, pitch) {
    /* 條數取奇數、置中：整條 path 的外框中心正好落在中間那一條線上。
       真滑鼠（Playwright）點的是外框中心，偶數條的話中心落在兩條線的空隙、打到底下的膜 ——
       「零件誰做的」那一段 2026-09-22 就是這樣點不到細線的。*/
    let n = Math.floor((x1 - w - x0) / pitch) + 1;
    if (n % 2 === 0) { x0 += pitch / 2; n -= 1; }
    const a = [];
    for (let k = 0; k < n; k++) { const x = x0 + k * pitch; a.push(`M${x},${y} h${w} v${CUH} h${-w}Z`); }
    return `<path class="part" d="${a.join(' ')}" fill="var(--dg-cu)"/>`;
  }

  /* 雷射微孔：**上寬下窄的錐形，窄的那一端一律朝向 core**（V2、V3）。
     `yOut`＝外側（離 core 遠，寬）、`yIn`＝內側（靠 core，窄）：
     上半部 yOut < yIn、下半部 yOut > yIn，同一支函式兩邊都對。內部一律畫成**填實**（V4）。*/
  const uvia = (x, yOut, yIn, wOut, wIn) =>
    `M${x - wOut / 2},${yOut} L${x + wOut / 2},${yOut} L${x + wIn / 2},${yIn} L${x - wIn / 2},${yIn}Z`;
  // 穿過層間空隙的小銅柱：這一層的微孔接到下一層的銅（拆開之後才看得到的組裝關係）
  const pillar = (x, y0, y1) => R(x - 2.5, Math.min(y0, y1), 5, Math.abs(y1 - y0), 'var(--dg-cu)', '', 1.5).replace('<rect', '<rect opacity=".55"');

  /* ================================================================ 主視圖的各個零件（玻璃板 ＋ 前面的剖面內容） */

  // ---- 核心層 core：唯一有織紋的一層，也是全圖最厚的一層。頂面畫三個貫孔的蓋銅。
  const gCore = () => `<g data-seg="substrate_material" data-part="abf_core">
    ${plate(Y.core, 'var(--dg-core)', topDots(VIA.core, 10, 'var(--dg-cu)', '.85'))}
    ${weave(XL + 4, XR - 4, Y.core[0] + 2, Y.core[1] - 2)}</g>`;

  /* ---- core 的貫孔（§7-B7 低信心：畫成孔壁銅 ＋ 內部填塞物 ＋ 兩端蓋銅，文字只寫「鍍銅 → 填塞 → 兩端蓋銅」）。
     V1：孔身嚴格落在 core 的兩面之間；蓋銅是「長在 core 表面上的那一片銅」，各往外多 4px，不是孔穿出去。*/
  const gCoreVia = () => `<g data-seg="abf_pcb" data-part="abf_core_via">${VIA.core.map(x => ''
    + R(x - 9, Y.core[0], 18, Y.core[1] - Y.core[0], 'var(--dg-plug)', 'part')
    + R(x - 13, Y.core[0], 4, Y.core[1] - Y.core[0], 'var(--dg-cu)')
    + R(x + 9, Y.core[0], 4, Y.core[1] - Y.core[0], 'var(--dg-cu)')
    + R(x - 17, Y.core[0] - 4, 34, 10, 'var(--dg-cu)', '', 1.5)
    + R(x - 17, Y.core[1] - 6, 34, 10, 'var(--dg-cu)', '', 1.5)).join('')}</g>`;

  /* ---- ABF 增層膜：上下各三層，**層數與厚度都相等**（S3）、**沒有織紋**（S4）。不是 prepreg 膠片（S1）。
     每一片是一塊玻璃板；頂面上畫幾條往後延伸的線路。*/
  const FILMS = () => [Y.u3, Y.u2, Y.u1, Y.l1, Y.l2, Y.l3];
  const gFilm = () => `<g data-seg="substrate_material" data-part="abf_film">
    ${FILMS().map(r => plate(r, 'var(--dg-abf)', topTraces(3))).join('')}</g>`;

  // ---- 半加成細線（SAP／mSAP）＋ core 的兩面線路。U1 的線從 XL+30 起，讓左欄的編號錨點有地方站。
  //      U2 那一條排第一個：它上面沒有墊子、中間那一條線也沒有微孔壓著，真滑鼠點外框中心一定點得到細線本身。
  const gTrace = () => `<g data-seg="abf_pcb" data-part="abf_trace">
    ${traces(CU.u2, XL + 10, XR - 6, 7, 16)}${traces(CU.u3, XL + 6, XR - 6, 7, 16)}${traces(CU.u1, XL + 30, XR - 6, 7, 16)}
    ${traces(CU.coreT, XL + 8, XR - 6, 9, 20)}${traces(CU.coreB, XL + 8, XR - 6, 9, 20)}
    ${traces(CU.l1, XL + 10, XR - 6, 7, 16)}${traces(CU.l2, XL + 6, XR - 6, 7, 16)}${traces(CU.l3, XL + 10, XR - 6, 7, 16)}</g>`;

  // ---- 雷射微孔（錐形、只穿一層、內部填實）＋ 穿過層間空隙的小銅柱
  const gUvia = () => {
    const d = [], pil = [];
    [[VIA.u3, CU.u3 + CUH, Y.u3[1], Y.u2[0]], [VIA.u2, CU.u2 + CUH, Y.u2[1], Y.u1[0]], [VIA.u1, CU.u1 + CUH, Y.u1[1], Y.core[0]],
      [VIA.l1, CU.l1, Y.l1[0], Y.core[1]], [VIA.l2, CU.l2, Y.l2[0], Y.l1[1]], [VIA.l3, CU.l3, Y.l3[0], Y.l2[1]]]
      .forEach(([xs, yOut, yIn, yNext]) => xs.forEach(x => { d.push(uvia(x, yOut, yIn, 16, 8)); pil.push(pillar(x, yIn, yNext)); }));
    return `<g data-seg="abf_pcb" data-part="abf_uvia">${pil.join('')}<path class="part" d="${d.join('')}" fill="var(--dg-cu)"/></g>`;
  };

  /* ---- 疊孔：U1 與 U2 兩個微孔**軸心對齊**，中間那一塊是被電鍍填平的銅（V4）。
     拆開之後兩個孔隔著一層呼吸空間，小銅柱 ＋ 虛線就是那條軸心。*/
  const gStack = () => { const x = VIA.stack; return `<g data-seg="abf_pcb" data-part="abf_stack_via">
    ${pillar(x, Y.u2[1], Y.u1[0])}
    <path class="part" d="${uvia(x, CU.u1 + CUH, Y.u1[1], 16, 8)}${uvia(x, CU.u2 + CUH, Y.u2[1], 16, 8)}" fill="var(--dg-cu)"/>
    ${R(x - 11, CU.u1 - 2, 22, 10, 'var(--dg-cu)', '', 2)}
    <path d="M${x},${CU.u2 + CUH - 2} V${Y.u1[1] + 2}" stroke="var(--dg-sig)" stroke-width=".9" stroke-dasharray="3 3" opacity=".7"/></g>`; };

  /* ---- 防焊層與開窗：**兩個外表面都有**（S6），而且只在墊子處開窗。
     上表面開窗給 bump pad（接晶片）、下表面開窗給球墊（接主機板）—— 兩側不准對調（S5）。
     前面畫開窗的缺口，上防焊的頂面畫「從開窗看到的墊子」。*/
  function srBand(y0, y1, gaps) {
    const segs = []; let cur = XL;
    gaps.forEach(([a, b]) => { if (a > cur) segs.push([cur, a]); cur = b; });
    if (cur < XR) segs.push([cur, XR]);
    return segs.map(([a, b]) => R(a, y0, b - a, y1 - y0, 'var(--dg-sr)', 'part')).join('');
  }
  const gSr = () => `<g data-seg="abf_pcb" data-part="abf_sr">
    ${plate(Y.srT, 'var(--dg-sr)', topDots(PADS, 6, 'var(--dg-cu)', '.9'))}
    ${srBand(Y.srT[0], Y.srT[1], PADS.map(x => [x - 7, x + 7]))}
    ${plate(Y.srB, 'var(--dg-sr)', '')}
    ${srBand(Y.srB[0], Y.srB[1], BALLS.map(x => [x - 13, x + 13]))}</g>`;

  /* ---- 凸塊墊 ＋ 表面處理。上表面 bump pad 寬 16、下表面 BGA 球墊寬 30 ——**兩側墊子大小明顯不同**（S5）。
     表面處理只畫在墊子的銅上（S7）；各家用哪一種表面處理查不到（§7-C），只寫「表面處理」。*/
  const gPad = () => `<g data-seg="abf_pcb" data-part="abf_bump_pad">
    ${PADS.map(x => R(x - 8, CU.u3, 16, CUH, 'var(--dg-cu)', 'part') + R(x - 6, CU.u3 - 4, 12, 4, 'var(--dg-ni)')).join('')}
    ${BALLS.map(x => R(x - 15, CU.l3, 30, CUH, 'var(--dg-cu)', 'part') + R(x - 11, CU.l3 + CUH, 22, 5, 'var(--dg-ni)')).join('')}</g>`;

  /* ---- 三種凸塊（§7-D2：**一律不掛 data-seg**）。凸塊算封裝廠還是載板廠做的依製程分工而異，查不到可引用的分工說法。
     錫球畫成帶高光的小球（玻璃語言）。*/
  const gBumps = () => `<g pointer-events="none">
    ${UBUMPS.map(x => R(x - 1.7, Y.ubT, 3.4, Y.ubB - Y.ubT, 'var(--dg-sn)')).join('')}
    ${PADS.map(x => R(x - 5, Y.c4T, 10, Y.c4B - Y.c4T, 'var(--dg-sn)', '', 4)).join('')}
    ${BALLS.map(x => `<circle cx="${x}" cy="${Y.ball}" r="12" fill="var(--dg-sn)"/><ellipse cx="${x - 3.5}" cy="${Y.ball - 4.5}" rx="4" ry="2.4" fill="var(--dg-pn-refl)" opacity=".85"/>`).join('')}</g>`;

  /* ---- 晶粒與中介層：**灰色剪影，不標任何內部細節**（M5、§0-B 二）。兩片灰玻璃板。
     不掛 data-seg；掛 data-part 只是讓小卡能把讀者導去半導體鏈那張圖。*/
  const gGhost = () => `<g data-part="abf_die_ghost" style="cursor:pointer">
    ${fx.glass(190, Y.itT, 210, Y.itB - Y.itT, { iso: ISO, fill: 'var(--dg-mute)', rx: 3 })}
    ${fx.glass(215, Y.dieT, 151, Y.dieB - Y.dieT, { iso: ISO, fill: 'var(--dg-mute)', rx: 3 })}</g>`;

  /* ---- 主機板（只畫一小段）：綠色玻璃板，比載板寬。走線寬 34／節距 60 ＝「細一個量級」的尺。*/
  const gMb = () => `<g data-seg="hdi_pcb" data-part="abf_motherboard">
    ${fx.glass(8, Y.mbT, 458, Y.mbB - Y.mbT, { iso: ISO, fill: 'var(--dg-pcb)', cls: 'part', rx: 4,
    top: [0.35, 0.7].map(v => `<path d="M${(10 + v * DX).toFixed(1)},${(v * DY).toFixed(1)} L${(446 + v * DX).toFixed(1)},${(v * DY).toFixed(1)}" stroke="var(--dg-cu)" stroke-width="3" opacity=".45" fill="none"/>`).join('') })}
    ${BALLS.map(x => R(x - 15, Y.mbT - 4, 30, CUH, 'var(--dg-cu)')).join('')}
    ${traces(Y.mbT + 6, 18, 446, 34, 60)}</g>`;

  /* ---- 訊號路徑（這張圖唯一的動畫，§9）：從 BGA 錫球進來 → 穿過 core 貫孔 → 沿增層的細線與微孔往上 → 從 bump pad 出去。
     D.fx.beam：一條發光光束（整張圖的第一個 feGaussianBlur）＋ 流動虛線（CSS dgdash）＋ 兩個端點光點；
     再加一顆走 SMIL 的光點 —— industry.js 的 setAnimAll 兩種都會停。*/
  const SIG = `M243,${Y.ball + 6} L243,${CU.l3 + 3} L170,${CU.l3 + 3} L170,${CU.l2 + 3} L286,${CU.l2 + 3} `
    + `L286,${CU.l1 + 3} L240,${CU.l1 + 3} L240,${CU.coreB + 3} L250,${CU.coreB + 3} L250,${CU.coreT + 3} `
    + `L380,${CU.coreT + 3} L380,${CU.u2 + 3} L306,${CU.u2 + 3} L306,${CU.u3 + 3} L304,${CU.u3 + 3} L304,${Y.c4B - 2}`;
  const gSignal = () => `<g pointer-events="none">
    ${fx.beam(SIG, { color: 'var(--dg-sig)', w: 2, flow: true, dots: [[243, Y.ball + 6], [304, Y.c4B - 2]] })}
    <circle r="3.2" fill="var(--dg-sn)" opacity=".95"><animateMotion dur="7s" repeatCount="indefinite" path="${SIG}"/></circle></g>`;

  /* ================================================================ 〔放大格 A〕三種節距
     同一條基線、同一個起點，**線段長度就是節距**。長度比例取 §7-A10 兩個獨立來源區間的中位數（約 45 : 175 : 750），
     所以三根一眼看得出差一個量級（M2）。**尺上不標 µm 數字**，只標小／中／大與來源。*/
  function panelA(x, y, w) {
    const k = 200 / 750, x0 = x + 18;
    const rows = [['微凸塊　晶片 ↔ 中介層（最小）', 45, 3.2],
      ['C4 凸塊　晶片／中介層 ↔ 載板（中）', 175, 6],
      ['BGA 錫球　載板 ↔ 主機板（最大）', 750, 11]];
    return `<g pointer-events="none"><rect class="frame" x="${x}" y="${y}" width="${w}" height="248" rx="8"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">〔A〕三種節距，差一個量級</text>
      ${rows.map(([t, p, r], i) => { const yy = y + 58 + i * 40, len = p * k;
    return `<text class="sub" x="${x0}" y="${yy - 13}">${t}</text>`
      + `<path d="M${x0},${yy + 11} H${x0 + len}" stroke="var(--dg-ink-3)" stroke-width="1" stroke-dasharray="3 3"/>`
      + `<path d="M${x0},${yy + 6} v10 M${x0 + len},${yy + 6} v10" stroke="var(--dg-ink-3)" stroke-width="1"/>`
      + `<circle cx="${x0}" cy="${yy}" r="${r}" fill="var(--dg-sn)"/><circle cx="${x0 + len}" cy="${yy}" r="${r}" fill="var(--dg-sn)"/>`; }).join('')}
      <text class="sub" x="${x0}" y="${y + 176}">同一把尺、同一個起點，</text>
      <text class="sub" x="${x0}" y="${y + 192}">長度＝節距，不標數字。</text>
      <text class="cap" x="${x0}" y="${y + 210}">量級來源：產業技術媒體</text>
      <text class="cap" x="${x0}" y="${y + 226}">與學術論文（2026）。</text></g>`;
  }

  /* ================================================================ 〔放大格 B〕ABF vs BT
     M3：**BT 那格有織紋、ABF 那格沒有**。M4：這兩樣的供應商是外商，畫面上明講。*/
  function panelB(x, y, w) {
    const mini = (mx, my, wv) => { const a = [];
      for (let i = 0; i < 4; i++) { const yy = my + i * 13;
        a.push(R(mx, yy, 118, 11, wv ? 'var(--dg-core)' : 'var(--dg-abf)'));
        if (wv) a.push(weave(mx + 2, mx + 116, yy, yy + 11));
        [6, wv ? 42 : 32, wv ? 78 : 62].forEach(dx => a.push(R(mx + dx, yy - 2, wv ? 18 : 7, 3, 'var(--dg-cu)')));
      }
      return a.join(''); };
    return `<g data-seg="substrate_material" data-part="abf_bt">
      <rect class="frame part" x="${x}" y="${y}" width="${w}" height="214" rx="8"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">〔B〕ABF 與 BT：兩種載板，不是等級高低</text>
      ${mini(x + 16, y + 44, false)}${mini(x + 160, y + 44, true)}
      <text class="lbl" x="${x + 16}" y="${y + 112}">ABF：無織造玻纖</text>
      <text class="lbl" x="${x + 160}" y="${y + 112}">BT：有玻纖補強</text>
      <text class="sub" x="${x + 16}" y="${y + 134}">ABF 走高效能運算與 AI，BT 走記憶體與射頻。</text>
      <text class="sub" x="${x + 16}" y="${y + 152}">景碩同時做兩種 —— 不是等級高低，是不同應用。</text>
      <text class="sub" x="${x + 16}" y="${y + 176}" style="fill:var(--dg-warn)">★ ABF 膜（味之素）、BT 樹脂（三菱瓦斯化學）</text>
      <text class="sub" x="${x + 16}" y="${y + 194}" style="fill:var(--dg-warn)">　 都是外商，台股在這一格是空的。</text></g>`;
  }

  /* ================================================================ 〔放大格 C〕翹曲
     §7-B3：CTE 的 ppm 值三組來源的量測條件全都沒交代，**只寫「樹脂的熱膨脹係數比矽大很多」**。
     §7-B2：封裝尺寸的 mm 數只有 blog 級來源，**只寫定性的「板子越大越翹」**。
     紅色（--dg-err）整張圖只用在這一格翹掉的那一塊，不當裝飾色。*/
  function panelC(x, y, w) {
    const x0 = x + 14;
    return `<g pointer-events="none"><rect class="frame" x="${x}" y="${y}" width="${w}" height="248" rx="8"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">〔C〕板子越大越翹</text>
      <text class="sub" x="${x0}" y="${y + 48}">小板子：迴焊完還是平的</text>
      <path d="M${x0},${y + 70} H${x0 + 150}" stroke="var(--dg-abf)" stroke-width="7" stroke-linecap="round"/>
      ${R(x0 + 50, y + 56, 50, 9, 'var(--dg-mute)')}
      <path d="M${x0},${y + 82} H${x0 + 150}" stroke="var(--dg-ink-3)" stroke-width="1" stroke-dasharray="3 3"/>
      <text class="sub" x="${x0}" y="${y + 110}">大板子：翹成洋芋片，焊不好</text>
      <path d="M${x0},${y + 124} q75,38 150,-6" stroke="var(--dg-err)" stroke-width="7" fill="none" stroke-linecap="round"/>
      ${R(x0 + 50, y + 128, 50, 9, 'var(--dg-mute)')}
      <path d="M${x0},${y + 148} H${x0 + 150}" stroke="var(--dg-ink-3)" stroke-width="1" stroke-dasharray="3 3"/>
      <text class="sub" x="${x0}" y="${y + 174}">樹脂的熱膨脹係數比矽大很多，</text>
      <text class="sub" x="${x0}" y="${y + 190}">迴焊高溫下尺寸越大翹得越兇，</text>
      <text class="sub" x="${x0}" y="${y + 206}">翹了就焊不好。</text>
      <text class="cap" x="${x0}" y="${y + 224}">不寫 ppm 值與封裝 mm 數</text>
      <text class="cap" x="${x0}" y="${y + 240}">（來源對不起來）。</text></g>`;
  }

  /* ================================================================ 路線圖：三條路，差別只在中間那一層
     §7-C：無核心與玻璃核心的**量產時程、台廠在這兩條路上的位置查不到**，只畫結構差異、不寫時程、不寫公司名。*/
  function roadmap(x, y, w) {
    const one = (mx, my, kind) => { const a = [];
      for (let i = 0; i < 3; i++) a.push(R(mx, my + i * 7, 140, 5, 'var(--dg-abf)'));
      const cy = my + 21;
      if (kind === 'core') { a.push(R(mx, cy, 140, 12, 'var(--dg-core)')); a.push(weave(mx + 3, mx + 137, cy, cy + 12)); }
      else if (kind === 'glass') { a.push(R(mx, cy, 140, 12, 'var(--dg-glass)'));
        a.push(`<path d="M${mx + 22},${cy + 11} l10,-10 M${mx + 60},${cy + 11} l10,-10 M${mx + 98},${cy + 11} l10,-10" stroke="var(--dg-ink)" stroke-width="1" opacity=".4" fill="none"/>`); }
      else { a.push(R(mx, cy + 4, 140, 4, 'var(--dg-abf)'));
        a.push(R(mx - 8, cy - 1, 8, 14, 'var(--dg-mute)')); a.push(R(mx + 140, cy - 1, 8, 14, 'var(--dg-mute)')); }
      for (let i = 0; i < 3; i++) a.push(R(mx, cy + 16 + i * 7, 140, 5, 'var(--dg-abf)'));
      return a.join(''); };
    return `<g data-seg="substrate_material" data-part="abf_roadmap">
      <rect class="frame part" x="${x}" y="${y}" width="${w}" height="144" rx="8"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">三條路，差別只在中間那一層（只畫結構差異，不寫時程、不寫公司名）</text>
      ${one(x + 22, y + 38, 'core')}${one(x + 182, y + 38, 'coreless')}${one(x + 342, y + 38, 'glass')}
      <text class="lbl" x="${x + 22}" y="${y + 107}">有核心（現在的主流）</text>
      <text class="lbl" x="${x + 182}" y="${y + 107}">無核心：拿掉 core</text>
      <text class="lbl" x="${x + 342}" y="${y + 107}">玻璃核心</text>
      ${D.para(x + 22, y + 123, 'core 撐住不變形', 150, { lh: 15 }).svg}
      ${D.para(x + 182, y + 123, '路徑短但更會翹，靠補強環', 150, { lh: 15 }).svg}
      ${D.para(x + 342, y + 123, '更硬、熱膨脹更接近矽，更平', w - 342 - 14, { lh: 15 }).svg}</g>`;
    /* ★ 2026-09-26 覆蓋普查：三格底下的說明原本各一行，第三格在 488 寬的框裡伸出框 22px、伸出畫布；
       改成各自照格寬斷兩行（框加高 8，標籤上提 3），下一個框（y 1390）不用動。*/
  }

  /* ================================================================ 整張圖 */
  function abfSubstrate() {
    const steps = [
      { seg: 'substrate_material', t: '① 材料', s: 'core 板材＋ABF 膜' },
      { seg: 'abf_pcb', t: '② core 加工', s: '鑽孔·鍍銅·填塞·線路' },
      { seg: 'abf_pcb', t: '③ 增層循環（上下同時）', s: '貼膜·雷射·除膠渣·電鍍' },
      { seg: 'abf_pcb', t: '④ 防焊與表面', s: '防焊·開窗·表面處理' },
      { seg: 'abf_pcb', t: '⑤ 成品', s: '切割·檢測·出貨封裝廠' },
    ];
    // 柔陰影：每一片板子一個影子，全部包成一個群組（第二個、也是最後一個 feGaussianBlur）
    const shadows = fx.shadows([Y.srT, Y.u3, Y.u2, Y.u1, Y.core, Y.l1, Y.l2, Y.l3, Y.srB].map(plateShadow).join('')
      + `<path d="M12,${Y.mbB + 12} L462,${Y.mbB + 12} L${462 + DX},${Y.mbB + 12 + DY} L${12 + DX},${Y.mbB + 12 + DY}Z"/>`);

    return `<svg class="dg dgm rs dgabf" viewBox="0 0 ${CW} 1870" width="100%" style="display:block">${STYLE}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <style>
        /* ---- 描邊與發光各降一階（只作用在這一張圖）----
           這張圖的零件細碎得多：200 多條 7px 的細線、30 幾個微孔、16 個微凸塊。共用的 2.2px 描邊套在 7px 寬的線上，
           那條線會整條變成實心的環節色塊，整片板子就變成一面發光的格子 —— 那正是「螢光感太重」。
           四個狀態：平時／選到的環節 → 不描邊（玻璃板自己有 .fxe 的細邊）；滑鼠移上去 → 1.4px；
           **你點的那一個** → 2.4px ＋ 一圈 5px 的暈開（閱讀模式 --dg-glow:none 就不暈）。
           多一個 svg 型別選擇器是必要的：特異性才壓得過 diagrams.js 的那一條。*/
        svg.dgabf [data-seg] .part{stroke-width:0}
        svg.dgabf [data-seg].sel .part{stroke-width:0;filter:none}
        svg.dgabf [data-seg]:hover .part{stroke-width:1.4;filter:none}
        svg.dgabf [data-seg].sel-part .part{stroke-width:2.4;filter:var(--dg-glow,drop-shadow(0 0 5px var(--cc)))}
        /* 壓暗那一階從 .3 放寬到 .55：進來的預設狀態是「族群 ic_substrate 被選起來」＝ abf_pcb 亮、
           substrate_material 與 hdi_pcb 被壓暗，而**被壓暗的正好是 core 與 ABF 膜**，也就是這張圖的主角。*/
        svg.dgabf [data-seg].dim{opacity:.55}
        .dgwrap:has(svg.dgabf) .dgc.dim{opacity:.55}
        svg.dgabf g[data-part="abf_die_ghost"].sel-part .fxb{fill-opacity:.9}
      </style>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead，SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">IC 載板：晶片底下那塊板子，跟主機板不是同一種東西</text>
      <text class="cap ext" x="0" y="0">以中間那片 core 為中心、上下對稱長出 ABF 增層；上表面用 bump pad 接晶片，下表面用 BGA 錫球接主機板。這裡把九層一片一片拆開浮著看：剖面畫在每一片的前緣，微孔畫成穿過層間空隙的小銅柱（這一層的孔接到下一層的銅），疊孔靠虛線軸心對齊。藍色光束＝訊號路徑：BGA → core 貫孔 → 微孔 → bump pad（可用「動畫」鈕停）。三格放大、三條路線與製程收在下面兩段。</text>

      <!-- ================= §1 主視圖：等角爆炸層疊 =================
           畫的順序＝由下往上、由後往前（上面的板子會蓋住下面板子的頂面，這是爆炸圖該有的遮擋）：
           陰影 → 主機板 → 下防焊 → L3 → L2 → L1 → core（含貫孔）→ U1 → U2 → U3 → 上防焊 → 墊子 → 剪影 → 凸塊 → 訊號。
           零件群組（data-part）是跨層的（例如所有增層膜是同一個群組），所以這裡先組好每一層要畫的東西，再照層序輸出。-->
      ${shadows}
      ${gMb()}
      ${gSr()}
      ${gFilm()}
      ${gCore()}${gCoreVia()}
      ${gUvia()}${gStack()}${gTrace()}${gPad()}
      ${gGhost()}${gBumps()}${gSignal()}

      <!-- ================= 說明卡片（HTML，左右兩欄）：左欄錨點在剖面左緣、右欄錨點在右半邊 ================= -->
      ${extRow({ side: 'l', no: 1, seg: 'substrate_material', part: 'abf_core', color: COL.core, ax: 34, ay: (Y.core[0] + Y.core[1]) / 2,
    title: '核心層 core：玻纖布補強的樹脂板', sub: '最厚、唯一有織紋的一層' })}
      ${extRow({ side: 'l', no: 3, seg: 'substrate_material', part: 'abf_film', color: COL.abf, ax: 34, ay: Y.u1[0] + 8,
    title: 'ABF 增層膜（味之素增層膜）', sub: '無玻纖樹脂膜，一層一層貼上' })}
      ${extRow({ side: 'l', no: 8, seg: 'abf_pcb', part: 'abf_sr', ax: 34, ay: Y.srT[0] + 3,
    title: '防焊開窗（SR opening）', sub: '蓋住整面，只在墊子處開窗' })}
      ${extRow({ side: 'l', no: 9, seg: 'hdi_pcb', part: 'abf_motherboard', ax: 34, ay: Y.mbT + 9,
    title: '這一條才是「PCB」：主機板', sub: '走線比載板粗一個量級' })}
      ${note({ side: 'l', warn: true, title: '★「載板材料 ABF / BT」這一格台股掛零',
    lines: ['ABF 膜是味之素（市占約 95%，來源：今周刊 2026-05）、BT 樹脂 core 是三菱瓦斯化學 —— 兩家都是外商；點 core／ABF 膜再點色標，成分股會是 0 筆，那不是壞掉。',
      '點零件篩到的是「環節」不是整個族群：「IC 載板」這一格收錄 3037 欣興／8046 南電／3189 景碩。',
      '示意圖，非實物比例；圖上 core ＋ 上下各 3 層，實際為十幾至二十幾層。'] })}
      ${extRow({ side: 'r', no: 2, seg: 'abf_pcb', part: 'abf_core_via', color: COL.cu, ax: 432, ay: (Y.core[0] + Y.core[1]) / 2,
    title: 'core 的貫孔：只穿 core', sub: '鑽穿→鍍銅→填塞→兩端蓋銅' })}
      ${extRow({ side: 'r', no: 4, seg: 'abf_pcb', part: 'abf_trace', color: COL.cu, ax: 429.5, ay: CU.u2 + 3,
    title: '半加成細線（SAP／mSAP）', sub: '比高階 PCB 再細一個量級' })}
      ${extRow({ side: 'r', no: 5, seg: 'abf_pcb', part: 'abf_uvia', color: COL.cu, ax: 432, ay: Y.u3[0] + 11,
    title: '雷射微孔：上寬下窄，窄端朝 core', sub: '一孔只穿一層；先除膠渣' })}
      ${extRow({ side: 'r', no: 6, seg: 'abf_pcb', part: 'abf_stack_via', color: COL.cu, ax: VIA.stack, ay: (Y.u2[1] + Y.u1[0]) / 2,
    title: '疊孔（stacked via）', sub: '填實了才能正上方再疊一個' })}
      ${extRow({ side: 'r', no: 7, seg: 'abf_pcb', part: 'abf_bump_pad', color: COL.cu, ax: 382, ay: CU.u3 - 1,
    title: '凸塊墊 bump pad ＋ 表面處理', sub: '接晶片；墊子比球墊小得多' })}
      ${extRow({ side: 'r', no: 10, part: 'abf_die_ghost', color: COL.off, ax: 360, ay: (Y.dieT + Y.dieB) / 2,
    title: '晶粒／中介層：不是這張圖的主題', sub: '看半導體鏈 CoWoS 那張' })}

      <!-- ================= ② 為什麼載板比主機板貴 ＋ 三格放大（預設收合；座標由 wireFolds 量）================= -->
      ${fold('abf2', '② 為什麼載板比主機板貴 ＋ 三格放大', '四點結論；三種節距差一個量級、ABF 無玻纖 BT 有、板子越大越翹', `
      <rect class="frame" x="16" y="560" width="488" height="176" rx="8"/>
      <text class="hd" x="30" y="584">為什麼載板比主機板貴</text>
      <text class="sub" x="30" y="606">① 線細一個量級：走半加成（SAP／mSAP），一層一層長出來</text>
      <text class="sub" x="30" y="624">② 層數是「循環」出來的：每多一層就多一次貼膜、雷射、除膠渣、</text>
      <text class="sub" x="30" y="642">　 電鍍、蝕刻，而整片的良率是每一層的連乘</text>
      <text class="sub" x="30" y="660">③ 關鍵材料幾乎只有一家（ABF 增層膜），材料漲價直接進成本</text>
      <text class="sub" x="30" y="678">④ 越做越大就越難：尺寸一大，翹曲、平坦度、電鍍均勻度同時變嚴</text>
      <text class="cap" x="30" y="704">一般高階 PCB 的線寬到 50 µm 已算高階，載板要細一個量級</text>
      <text class="cap" x="30" y="722">（50 µm 的來源見規格書 §7-B1，2026 查；載板自己的線寬不寫數字）。</text>
      ${panelA(16, 750, 238)}${panelC(266, 750, 238)}
      ${panelB(16, 1012, 488)}`)}

      <!-- ================= ③ 路線圖 ＋ AI 為什麼推到極限 ＋ 製程五格 ＋ 台股掛零（預設收合）================= -->
      ${fold('abf3', '③ 三條路線圖、AI 為什麼把載板推到極限、製程五格', '有核心／無核心／玻璃核心只差中間一層；五格製程與除膠渣；材料那一格為什麼沒有台股', `
      ${roadmap(16, 1240, 488)}
      <rect class="frame" x="16" y="1390" width="488" height="116" rx="8"/>
      <text class="hd" x="30" y="1414">AI 為什麼把載板推到極限</text>
      <text class="sub" x="30" y="1438">① 晶片變大、要接的線變多 → 載板跟著變大、層數變多</text>
      <text class="sub" x="30" y="1456">② 大板子在迴焊高溫下翹得更兇（樹脂與矽差太多）</text>
      <text class="sub" x="30" y="1474">③ 所以才有人提無核心（路徑短）與玻璃核心（更硬）</text>
      <text class="sub" x="30" y="1492">④ 這兩條路都要換設備、重新認證，不是換個材料就好</text>

      <!-- 製程列（五格）＝ §3-C：P1 增層在防焊之前、P2 第三格裡有除膠渣、P3 材料商與載板廠之間有分界線、P4 第三格標明上下同時 -->
      <text class="cap" x="16" y="1536">製造流程（五格）　★ 增層循環一定在防焊與表面處理之前；</text>
      <text class="cap" x="16" y="1554">雷射開孔之後、鍍銅之前一定有「除膠渣」那一步</text>
      <path d="M170,1560 V1610" stroke="var(--dg-warn)" stroke-dasharray="5 4" fill="none" opacity=".85" style="stroke-width:var(--dg-hair-w,2)"/>
      ${processBar(8, 1564, steps, 156, { cols: 3, wrap: true })}   <!-- ★ 2026-09-26：「③ 增層循環（上下同時）」比格子寬 → 格內斷行，格子等高加高 -->
      <g transform="translate(0,${D.processBarHeight(steps, 156, { cols: 3, wrap: true }) - D.processBarHeight(steps, 156, { cols: 3 })})">
      <text class="sub" x="8" y="1682" style="fill:var(--dg-warn)">← 材料商（外商）</text>
      <text class="sub" x="176" y="1682">載板廠（3037 欣興／8046 南電／3189 景碩）→</text>
      <text class="cap" x="16" y="1706">③ 的完整一圈：貼 ABF 膜 → 雷射開微孔 → 除膠渣（desmear）→ 化學鍍薄銅</text>
      <text class="cap" x="16" y="1724">　 → 圖案電鍍（SAP／mSAP）→ 蝕刻，上下兩面同時做、重複 N 次。</text>

      <!-- 台股掛零那一格：畫面上一定要解釋，不要讓人以為點壞了 -->
      <text class="sub" x="16" y="1752" style="fill:var(--dg-warn)">★「載板材料 ABF / BT」這一格台股掛零：ABF 膜幾乎是單一供應商（味之素）、</text>
      <text class="sub" x="16" y="1770" style="fill:var(--dg-warn)">　 BT 樹脂 core 是三菱瓦斯化學，兩家都是外商。點 core、ABF 膜、〔B〕或路線圖，</text>
      <text class="sub" x="16" y="1788" style="fill:var(--dg-warn)">　 再點下面同色的環節色標，成分股會是 0 筆 —— 那不是壞掉，是這一格真的沒有台股。</text>
      <text class="cap" x="16" y="1814">示意圖，非實物比例｜層數與各層厚度均為示意；載板線寬、CTE、封裝尺寸、供需與價格</text>
      <text class="cap" x="16" y="1832">一律不寫數字（來源對不起來，見規格書 §7-B／§7-C）。圖上畫 core ＋ 上下各 3 層增層，</text>
      <text class="cap" x="16" y="1850">實際為十幾至二十幾層（這句話本身也是示意，不是規格）。</text>
      </g>`)}
    </svg>`;
  }

  window.DG.register('ic_substrate', {
    level: 'group', chain: 'ai_server',
    name: 'IC 載板：ABF 增層剖面',
    draw: abfSubstrate, native: CW, scene: 'ic_substrate',   /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。檔頭 §0 原本寫「不做真 3D」，
        推翻它的是那個理由**漏掉的另一半**（逐張寫在 DECISIONS #250），不是那個理由本身。*/
    q: 'AI 晶片底下那塊板子為什麼比主機板貴？ABF 膜、細線、微孔各卡在哪一關，台股站在哪幾家？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       這張圖是 R4（台股沒有人做的零件要明說）最典型的案例：**核心層與 ABF 膜這兩層台股一家都沒有**，
       而那正是整條鏈的卡點。`cos` 只放代號，「這家在這裡負責什麼」一律讀 supply_chain.json 的 companies[].tech（R3）。
       `items` 只填 supply_chain 的 edges[].item 真的有的字串；沒寫 items 的零件走預設（該環節流進／流出的全部品項）。*/
    parts: {
      /* v2 之後零件的名字不在 SVG 裡（卡片是 HTML），小卡拿不到 text.lbl，所以每一個零件都要自己給 name，
         不然小卡標題會退成環節名「IC 載板（ABF / BT）」（零件誰做的那一段抓到的）。*/
      abf_core: {
        name: '核心層 core（玻纖布補強的樹脂板）',
        desc: '整塊載板最厚、也是唯一看得出玻纖織紋的那一層。它的工作是撐住不變形，上下增層才有東西可以長。',
        items: ['BT 樹脂 core CCL'],
        none: 'core 用的 BT 樹脂銅箔基板由三菱瓦斯化學（MGC，日）供應 —— ★ 這一層的板材台股沒有廠商做。把 core 加工成載板的才是下面那三家台廠。',
      },
      abf_film: {
        name: 'ABF 增層膜（味之素增層膜）',
        desc: '不含織造玻纖的熱固性樹脂膜，一層一層貼上去（不是 prepreg 膠片）。正因為沒有玻纖，才打得出更小的孔、做得出更細的線。',
        items: ['ABF 增層膜'],
        none: '味之素（Ajinomoto，日）一家供應全球，市占約 95%、近乎獨占（來源：今周刊 2026-05）。★ 台股沒有廠商做這一層 —— 這是整條載板鏈最硬的卡點。',
      },
      abf_bt: {
        name: 'ABF 與 BT：兩種載板，不是等級高低',
        desc: 'ABF 與 BT 是兩種不同應用的載板，不是等級高低：ABF 走高效能運算與 AI，BT 走記憶體與射頻。景碩兩種都做。',
        items: ['ABF 增層膜', 'BT 樹脂 core CCL'],
        none: 'ABF 膜（味之素）與 BT 樹脂（三菱瓦斯化學）都是日商。★ 台股在「載板材料」這一格是空的 —— 台廠是買這兩種材料去做載板的人，不是做材料的人。',
      },
      abf_roadmap: {
        name: '三條路：有核心／無核心／玻璃核心',
        desc: '有核心 → 無核心 → 玻璃核心，三條路差別只在中間那一層。規格書 §7-C：量產時程與台廠在這兩條新路上的位置查不到，所以圖上不寫時程、不寫公司名。',
        cos: [],
        none: '無核心與玻璃核心這兩條路「台股是誰在做」目前查不到具名來源 —— 查不到就寫查不到，不編一個對應（R5）。有核心那條路的載板廠見上面各層。',
      },
      abf_core_via: { name: 'core 的貫孔', desc: '鑽穿 core → 鍍銅 → 填塞 → 兩端蓋銅，而且只穿 core。跟主機板那種貫穿整塊板的孔不是同一件事。' },
      abf_trace: { name: '半加成細線（SAP／mSAP）', desc: '半加成法（SAP／mSAP）：先鍍一層很薄的銅，再把線「長」出來，不是把整片銅蝕掉。載板的線寬要比高階 PCB 再細一個量級。' },
      abf_uvia: { name: '雷射微孔', desc: '雷射微孔，上寬下窄、窄的那一端朝向 core，一個孔只穿一層增層。打完一定要先除膠渣（desmear），銅才附得上去。拆開來看，每一層的孔都接到下一層的銅（圖上的小銅柱）。' },
      abf_stack_via: { name: '疊孔（stacked via）', desc: '疊孔：微孔要先用電鍍銅填實，正上方才能再疊一個孔。層數越多、疊得越高，越吃電鍍能力 —— 這是載板廠之間真正拉開差距的地方。' },
      abf_bump_pad: { name: '凸塊墊（bump pad）＋ 表面處理', desc: '晶片的凸塊就焊在這裡。上表面接晶片的墊子，比下表面接主機板的球墊小得多。' },
      abf_sr: { name: '防焊開窗（SR opening）', desc: '防焊蓋住整面，只在要接晶片、要接主機板的墊子上開窗 —— 開窗的位置與大小決定焊得上焊不上。' },
      abf_motherboard: {
        name: '主機板（載板底下那塊板）',
        desc: '載板底下那塊主機板（這張圖只畫一小段）。它的走線寬與節距比載板粗一個量級，兩者擺在同一張圖上就是那把尺。',
      },
      abf_die_ghost: {
        name: '晶粒與中介層（灰色剪影）',
        desc: '晶片這一側不是這張圖的主題：晶粒、微凸塊、中介層的細節在半導體鏈的「先進封裝：CoWoS 剖面」那張圖。這裡只畫剪影，不掛環節。',
        cos: [],
        none: '不掛供應鏈環節：凸塊到底算封裝廠還是載板廠做的依製程分工而異，查不到可引用的分工說法，掛上去等於宣稱一個沒有證據的分工。',
      },
    },
  });
})();
