/* IC 載板：ABF 增層剖面 —— docs/diagram_plan.md 的第 3 張（族群 `ic_substrate`、ai_server 鏈）

   合約＝`docs/diagram_specs/abf_substrate.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的四件事：

     · §0-A **不做真 3D**（`scene: null`）。要加 3D 就是改規格書、重新簽，不准實作時順手加。
     · §0-B（一）跟 `pcb_stackup`（PCB 硬板那張）的分工：**PCB 那張的下游是「把零件焊上去」，這張的下游是「把晶片黏上去」。**
       明列五樣這張圖不准畫：銅箔稜面三格、玻纖織紋放大格、四種孔對照、走線頂視小圖、表面處理比較表。這個檔一樣都沒有（M6）。
     · §0-B（二）跟 CoWoS 剖面（`ai_adv_packaging`）的分工：**中介層以上一律只畫灰色剪影、不標細節、不掛 `data-seg`**（M5、D2）。
     · §7-B／§7-C：查不到的東西一個數字都不編。畫面上唯一的百分比是 ABF 膜市占，而且必須連同「來源：今周刊 2026-05」一起寫（N1）。
       載板線寬、CTE 的 ppm、封裝 mm 數、供需缺口、良率與單價差距**全部不進畫面**。

   ---- 2026-09-22 v2（DECISIONS #238／#239，分支 claude/restyle-w1b）----
   · svg 根掛 `.rs`：閱讀模式字級升一階、說明卡片離開 SVG 變成 HTML（extRow 多傳 side）。
   · 畫布從 980 收到 **520**（主角寬），`native: 520` 跟著改；欄數由 index.html 的 .dgv2 容器查詢決定。
   · 繪圖本體改成**垂直爆炸拆解**：九層（上防焊、U3、U2、U1、core、L1、L2、L3、下防焊）一層一片薄板，
     層與層之間留 14px 的呼吸空間；每一片都帶自己的頂面與右側面（2.5D 厚度感）。
     疊構關係沒有變：core 在正中間、上下各 3 層厚度相等、只有 core 有織紋、微孔朝 core 收窄、貫孔只穿 core。
     拆開之後多出來的一件事看得更清楚：**微孔是「這一層自己的孔」**（從這一層的銅打到這一層的底面），疊孔靠虛線軸心對齊。
   · §1 從 606 壓到約 480：右欄九列說明全部變成卡片、三格放大與路線圖收進兩個章節（一個字沒刪，只改斷行與位置）。
     收合 ≈ 480 ＋ 8 ＋ 42×2 ＋ 10 ＝ 582。
   · 卡片與畫布上的零件是同一個 data-part：點卡片亮零件、點零件亮卡片（主角是一個 data-part，畫面上兩個節點）。
   · 卡片元件色（data-dgcolor）：core --dg-weave（織紋色，深底上讀得到）、ABF 膜 --dg-abf、銅件 --dg-cu、灰色剪影 --dg-mute；
     防焊與主機板不指定（落回環節色）—— --dg-sr／--dg-pcb 在深底上對編號數字的對比不到 4.5，不拿來當卡片色。
   · 訊號路徑用箭頭 ＋ 虛線（--dg-sig），不加發光濾鏡；發光只給主角（下面 scoped style）。

   為什麼主視圖是「正剖面 ＋ 等角厚度」而不是整塊等角切角
   ------------------------------------------------------
   這張圖的內容是**九層薄層疊構 ＋ 錐形微孔 ＋ 只穿 core 的貫孔**，全部的資訊都在剖面上。
   整塊等角切角會把剖面壓成 30° 斜面：20px 厚的增層在斜面上只剩 10px、錐度看不出來。
   所以主體畫成**正剖面**，另外把每一層的頂面與右側面往右後上擠出去（`TF`／`RF`）當厚度。

   這個檔不碰 `site/index.html`／`site/three3d.js`。共用工具一律走 `window.DG`。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;   // diagrams.js 沒載到就安靜退出
  const { STYLE, extRow, note, processBar, fold } = D;

  /* ================================================================ 版面常數（全部是畫布座標，寬 520）
     剖面：x ∈ [XL, XR]＝載板的長，y 往下＝往底層。等角厚度往右後上 (DX, DY)。*/
  const CW = 520, XL = 24, XR = 452, DX = 16, DY = -7;
  const G = 14;                                            // 層與層之間的呼吸空間（爆炸間距）

  /* 層界（由上往下，用厚度累加出來，所以「上下對稱」是算出來的不是手抄的）。
     **core 56、每一層增層 20 ＝ core 是任一層增層的 2.8 倍厚**（S2）；上下各三層、對應層厚度相同（S3）；
     防焊上下各 8、成對出現（S6）。*/
  const Y = { dieT: 16, dieB: 38, ubT: 38, ubB: 48, itT: 48, itB: 66, c4T: 66, c4B: 86 };
  (function stack() {
    let y = 100;
    [['srT', 8], ['u3', 20], ['u2', 20], ['u1', 20], ['core', 56], ['l1', 20], ['l2', 20], ['l3', 20], ['srB', 8]]
      .forEach(([k, h]) => { Y[k] = [y, y + h]; y += h + G; });
    Y.ball = Y.srB[1] + G + 6;                             // 錫球中心
    Y.mbT = Y.ball + 30; Y.mbB = Y.mbT + 24;               // 主機板（只畫一小段）
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
    u1: [96, 190, 290], u2: [140, 236, 330], u3: [112, 200, 306, 432],
    l1: [130, 240, 386], l2: [104, 286, 410], l3: [170, 316, 424],
    stack: 380,
  };

  /* 卡片的元件色（token，不寫死）*/
  const COL = { core: 'var(--dg-weave)', abf: 'var(--dg-abf)', cu: 'var(--dg-cu)', off: 'var(--dg-mute)' };

  /* ================================================================ 小工具
     `TF`／`RF` 就是那個 2.5D：把每一片薄板往右後上擠出去的頂面與右側面。*/
  const TF = (x0, x1, y, fill) =>
    `<path d="M${x0},${y} L${x1},${y} L${x1 + DX},${y + DY} L${x0 + DX},${y + DY}Z" fill="${fill}"/>`;
  const RF = (y0, y1, fill) =>
    `<path d="M${XR},${y0} L${XR + DX},${y0 + DY} L${XR + DX},${y1 + DY} L${XR},${y1}Z" fill="${fill}"/>`;
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;

  /* 玻纖織紋。**整張圖只有 core 那一層可以呼叫它**（S4）——
     ABF 是不含織造玻纖的樹脂膜，那正是它能打出更小的孔、做出更細的線的原因（§7-A1）。*/
  function weave(x0, x1, y0, y1) {
    const h = y1 - y0, w = x1 - x0;
    const n = Math.max(1, Math.floor((h - 4) / 14));
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
    const a = [];
    for (let x = x0; x <= x1 - w; x += pitch) a.push(`M${x},${y} h${w} v${CUH} h${-w}Z`);
    return `<path class="part" d="${a.join(' ')}" fill="var(--dg-cu)"/>`;
  }

  /* 雷射微孔：**上寬下窄的錐形，窄的那一端一律朝向 core**（V2、V3）。
     `yOut`＝外側（離 core 遠，寬）、`yIn`＝內側（靠 core，窄）：
     上半部 yOut < yIn、下半部 yOut > yIn，同一支函式兩邊都對。內部一律畫成**填實**（V4）。*/
  const uvia = (x, yOut, yIn, wOut, wIn) =>
    `M${x - wOut / 2},${yOut} L${x + wOut / 2},${yOut} L${x + wIn / 2},${yIn} L${x - wIn / 2},${yIn}Z`;

  /* ================================================================ 主視圖的各個零件 */

  // ---- 每一片薄板的等角厚度：頂面與右側面（先畫，正剖面壓在上面）。拆開之後每一層都露出自己的頂面。
  const slab = (r, fill) => TF(XL, XR, r[0], fill) + RF(r[0], r[1], fill);
  const gSlab = () => [
    slab(Y.srT, 'var(--dg-sr-2)'),
    slab(Y.u3, 'var(--dg-abf-2)'), slab(Y.u2, 'var(--dg-abf-2)'), slab(Y.u1, 'var(--dg-abf-2)'),
    slab(Y.core, 'var(--dg-core-2)'),
    slab(Y.l1, 'var(--dg-abf-2)'), slab(Y.l2, 'var(--dg-abf-2)'), slab(Y.l3, 'var(--dg-abf-2)'),
    slab(Y.srB, 'var(--dg-sr-2)'),
  ].join('');

  // ---- 核心層 core：唯一有織紋的一層，也是全圖最厚的一層
  const gCore = () => `<g data-seg="substrate_material" data-part="abf_core">
    ${R(XL, Y.core[0], XR - XL, Y.core[1] - Y.core[0], 'var(--dg-core)', 'part')}
    ${weave(XL + 4, XR - 4, Y.core[0], Y.core[1])}</g>`;

  /* ---- core 的貫孔（§7-B7 低信心：畫成孔壁銅 ＋ 內部填塞物 ＋ 兩端蓋銅，文字只寫「鍍銅 → 填塞 → 兩端蓋銅」）。
     V1：孔身嚴格落在 core 的兩面之間；蓋銅是「長在 core 表面上的那一片銅」，各往外多 4px，不是孔穿出去。*/
  const gCoreVia = () => `<g data-seg="abf_pcb" data-part="abf_core_via">${VIA.core.map(x => ''
    + R(x - 9, Y.core[0], 18, Y.core[1] - Y.core[0], 'var(--dg-plug)', 'part')
    + R(x - 13, Y.core[0], 4, Y.core[1] - Y.core[0], 'var(--dg-cu)')
    + R(x + 9, Y.core[0], 4, Y.core[1] - Y.core[0], 'var(--dg-cu)')
    + R(x - 17, Y.core[0] - 4, 34, 10, 'var(--dg-cu)', '', 1.5)
    + R(x - 17, Y.core[1] - 6, 34, 10, 'var(--dg-cu)', '', 1.5)).join('')}</g>`;

  /* ---- ABF 增層膜：上下各三層，**層數與厚度都相等**（S3）、**沒有織紋**（S4）。不是 prepreg 膠片（S1）。*/
  const FILMS = () => [Y.u3, Y.u2, Y.u1, Y.l1, Y.l2, Y.l3];
  const gFilm = () => `<g data-seg="substrate_material" data-part="abf_film">
    ${FILMS().map(r => R(XL, r[0], XR - XL, r[1] - r[0], 'var(--dg-abf)', 'part')).join('')}</g>`;

  // ---- 半加成細線（SAP／mSAP）＋ core 的兩面線路。U1 與 core 兩面的線從 XL+30 起，讓左欄的編號錨點有地方站。
  const gTrace = () => `<g data-seg="abf_pcb" data-part="abf_trace">
    ${traces(CU.u3, XL + 6, XR - 6, 7, 16)}${traces(CU.u2, XL + 10, XR - 6, 7, 16)}${traces(CU.u1, XL + 30, XR - 6, 7, 16)}
    ${traces(CU.coreT, XL + 8, XR - 6, 9, 20)}${traces(CU.coreB, XL + 8, XR - 6, 9, 20)}
    ${traces(CU.l1, XL + 10, XR - 6, 7, 16)}${traces(CU.l2, XL + 6, XR - 6, 7, 16)}${traces(CU.l3, XL + 10, XR - 6, 7, 16)}</g>`;

  // ---- 雷射微孔（錐形、只穿一層、內部填實）
  const gUvia = () => {
    const d = [];
    [[VIA.u3, CU.u3 + CUH, Y.u3[1]], [VIA.u2, CU.u2 + CUH, Y.u2[1]], [VIA.u1, CU.u1 + CUH, Y.u1[1]],
      [VIA.l1, CU.l1, Y.l1[0]], [VIA.l2, CU.l2, Y.l2[0]], [VIA.l3, CU.l3, Y.l3[0]]]
      .forEach(([xs, yOut, yIn]) => xs.forEach(x => d.push(uvia(x, yOut, yIn, 16, 8))));
    return `<g data-seg="abf_pcb" data-part="abf_uvia"><path class="part" d="${d.join('')}" fill="var(--dg-cu)"/></g>`;
  };

  /* ---- 疊孔：U1 與 U2 兩個微孔**軸心對齊**，中間那一塊是被電鍍填平的銅（V4）。
     拆開之後兩個孔隔著一層呼吸空間，虛線就是那條軸心。*/
  const gStack = () => { const x = VIA.stack; return `<g data-seg="abf_pcb" data-part="abf_stack_via">
    <path class="part" d="${uvia(x, CU.u1 + CUH, Y.u1[1], 16, 8)}${uvia(x, CU.u2 + CUH, Y.u2[1], 16, 8)}" fill="var(--dg-cu)"/>
    ${R(x - 11, CU.u1 - 2, 22, 10, 'var(--dg-cu)', '', 2)}
    <path d="M${x},${CU.u2 + CUH - 4} V${Y.u1[1] + 4}" stroke="var(--dg-sig)" stroke-width=".9" stroke-dasharray="3 3" opacity=".6"/></g>`; };

  /* ---- 防焊層與開窗：**兩個外表面都有**（S6），而且只在墊子處開窗。
     上表面開窗給 bump pad（接晶片）、下表面開窗給球墊（接主機板）—— 兩側不准對調（S5）。*/
  function srBand(y0, y1, gaps) {
    const segs = []; let cur = XL;
    gaps.forEach(([a, b]) => { if (a > cur) segs.push([cur, a]); cur = b; });
    if (cur < XR) segs.push([cur, XR]);
    return segs.map(([a, b]) => R(a, y0, b - a, y1 - y0, 'var(--dg-sr)', 'part')).join('');
  }
  const gSr = () => `<g data-seg="abf_pcb" data-part="abf_sr">
    ${srBand(Y.srT[0], Y.srT[1], PADS.map(x => [x - 7, x + 7]))}
    ${srBand(Y.srB[0], Y.srB[1], BALLS.map(x => [x - 13, x + 13]))}</g>`;

  /* ---- 凸塊墊 ＋ 表面處理。上表面 bump pad 寬 16、下表面 BGA 球墊寬 30 ——**兩側墊子大小明顯不同**（S5）。
     表面處理只畫在墊子的銅上（S7）；各家用哪一種表面處理查不到（§7-C），只寫「表面處理」。*/
  const gPad = () => `<g data-seg="abf_pcb" data-part="abf_bump_pad">
    ${PADS.map(x => R(x - 8, CU.u3, 16, CUH, 'var(--dg-cu)', 'part') + R(x - 6, CU.u3 - 4, 12, 4, 'var(--dg-ni)')).join('')}
    ${BALLS.map(x => R(x - 15, CU.l3, 30, CUH, 'var(--dg-cu)', 'part') + R(x - 11, CU.l3 + CUH, 22, 5, 'var(--dg-ni)')).join('')}</g>`;

  /* ---- 三種凸塊（§7-D2：**一律不掛 data-seg**）。凸塊算封裝廠還是載板廠做的依製程分工而異，查不到可引用的分工說法。*/
  const gBumps = () => `<g pointer-events="none">
    ${UBUMPS.map(x => R(x - 1.7, Y.ubT, 3.4, Y.ubB - Y.ubT, 'var(--dg-sn)')).join('')}
    ${PADS.map(x => R(x - 5, Y.c4T, 10, Y.c4B - Y.c4T, 'var(--dg-sn)', '', 4)).join('')}
    ${BALLS.map(x => `<ellipse cx="${x}" cy="${Y.ball}" rx="14" ry="14" fill="var(--dg-sn)"/>`).join('')}</g>`;

  /* ---- 晶粒與中介層：**灰色剪影，不標任何內部細節**（M5、§0-B 二）。
     不掛 data-seg；掛 data-part 只是讓小卡能把讀者導去半導體鏈那張圖。*/
  function ghost(x0, x1, y0, y1) {
    return `<path d="M${x0},${y0} L${x1},${y0} L${x1 + DX},${y0 + DY} L${x0 + DX},${y0 + DY}Z" fill="var(--dg-mute)" opacity=".5"/>`
      + `<path d="M${x1},${y0} L${x1 + DX},${y0 + DY} L${x1 + DX},${y1 + DY} L${x1},${y1}Z" fill="var(--dg-mute)" opacity=".3"/>`
      + `<path d="M${x0},${y0} L${x1},${y0} L${x1},${y1} L${x0},${y1}Z" fill="var(--dg-mute)" opacity=".42"/>`;
  }
  const gGhost = () => `<g data-part="abf_die_ghost" style="cursor:pointer">${ghost(190, 400, Y.itT, Y.itB)}${ghost(215, 366, Y.dieT, Y.dieB)}</g>`;

  /* ---- 主機板（只畫一小段）。右端畫成鋸齒＝「還有，只是沒畫」。走線寬 34／節距 60 ＝「細一個量級」的尺。*/
  const gMb = () => {
    const mx0 = 8, mx1 = 466, zig = [];
    for (let i = 0; i * 6 + Y.mbT < Y.mbB; i++) zig.push(`L${mx1 - (i % 2 ? 6 : 0)},${Y.mbT + (i + 1) * 6}`);
    return `<g data-seg="hdi_pcb" data-part="abf_motherboard">
      ${TF(mx0, mx1, Y.mbT, 'var(--dg-pcb-2)')}
      <path class="part" d="M${mx0},${Y.mbT} L${mx1},${Y.mbT} ${zig.join(' ')} L${mx0},${Y.mbB}Z" fill="var(--dg-pcb)"/>
      ${BALLS.map(x => R(x - 15, Y.mbT - 4, 30, CUH, 'var(--dg-cu)')).join('')}
      ${traces(Y.mbT + 12, mx0 + 10, mx1 - 20, 34, 60)}</g>`;
  };

  /* ---- 訊號路徑（這張圖唯一的動畫，§9）：從 BGA 錫球進來 → 穿過 core 貫孔 → 沿增層的細線與微孔往上 → 從 bump pad 出去。
     拆開之後路徑會跨過層與層之間的空隙 —— 那正好把「這一層的孔接到下一層的銅」講出來。
     虛線走 CSS 的 dgdash、光點走 SMIL，industry.js 的 setAnimAll 兩種都會停。不加發光濾鏡。*/
  const SIG = `M243,${Y.ball + 8} L243,${CU.l3 + 3} L170,${CU.l3 + 3} L170,${CU.l2 + 3} L286,${CU.l2 + 3} `
    + `L286,${CU.l1 + 3} L240,${CU.l1 + 3} L240,${CU.coreB + 3} L250,${CU.coreB + 3} L250,${CU.coreT + 3} `
    + `L380,${CU.coreT + 3} L380,${CU.u2 + 3} L306,${CU.u2 + 3} L306,${CU.u3 + 3} L304,${CU.u3 + 3} L304,${Y.c4B}`;
  const gSignal = () => `<g pointer-events="none">
    <path d="${SIG}" stroke="var(--dg-sig)" stroke-width="1.4" fill="none" opacity=".32"/>
    <path class="flow slow" d="${SIG}" stroke="var(--dg-sig)" stroke-width="2" fill="none" opacity=".9"/>
    <circle r="3.2" fill="var(--dg-sig)" opacity=".95"><animateMotion dur="7s" repeatCount="indefinite" path="${SIG}"/></circle></g>`;

  /* ================================================================ 〔放大格 A〕三種節距
     同一條基線、同一個起點，**線段長度就是節距**。長度比例取 §7-A10 兩個獨立來源區間的中位數（約 45 : 175 : 750），
     所以三根一眼看得出差一個量級（M2）。**尺上不標 µm 數字**，只標小／中／大與來源。*/
  function panelA(x, y, w) {
    const k = 200 / 750, x0 = x + 18;
    const rows = [['微凸塊　晶片 ↔ 中介層（最小）', 45, 3.2],
      ['C4 凸塊　晶片／中介層 ↔ 載板（中）', 175, 6],
      ['BGA 錫球　載板 ↔ 主機板（最大）', 750, 11]];
    return `<g pointer-events="none"><rect class="frame" x="${x}" y="${y}" width="${w}" height="232" rx="8"/>
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
    return `<g pointer-events="none"><rect class="frame" x="${x}" y="${y}" width="${w}" height="232" rx="8"/>
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
      <text class="cap" x="${x0}" y="${y + 224}">不寫 ppm 值與封裝 mm 數（來源對不起來）。</text></g>`;
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
      <rect class="frame part" x="${x}" y="${y}" width="${w}" height="136" rx="8"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">三條路，差別只在中間那一層（只畫結構差異，不寫時程、不寫公司名）</text>
      ${one(x + 22, y + 38, 'core')}${one(x + 182, y + 38, 'coreless')}${one(x + 342, y + 38, 'glass')}
      <text class="lbl" x="${x + 22}" y="${y + 110}">有核心（現在的主流）</text>
      <text class="lbl" x="${x + 182}" y="${y + 110}">無核心：拿掉 core</text>
      <text class="lbl" x="${x + 342}" y="${y + 110}">玻璃核心</text>
      <text class="sub" x="${x + 22}" y="${y + 128}">core 撐住不變形</text>
      <text class="sub" x="${x + 182}" y="${y + 128}">路徑短但更會翹，靠補強環</text>
      <text class="sub" x="${x + 342}" y="${y + 128}">更硬、熱膨脹更接近矽，更平</text></g>`;
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

    return `<svg class="dg dgm rs dgabf" viewBox="0 0 ${CW} 1800" width="100%" style="display:block">${STYLE}
      <style>
        /* ---- 描邊與發光各降一階（只作用在這一張圖）----
           這張圖的零件細碎得多：200 多條 7px 的細線、30 幾個微孔、16 個微凸塊。共用的 2.2px 描邊套在 7px 寬的線上，
           那條線會整條變成實心的環節色塊，整片板子就變成一面發光的格子 —— 那正是「螢光感太重」。
           四個狀態：平時／選到的環節 → 不描邊；滑鼠移上去 → 1.4px；**你點的那一個** → 2.4px ＋ 一圈 5px 的暈開
           （閱讀模式 --dg-glow:none 就不暈）。多一個 svg 型別選擇器是必要的：特異性才壓得過 diagrams.js 的那一條。*/
        svg.dgabf [data-seg] .part{stroke-width:0}
        svg.dgabf [data-seg].sel .part{stroke-width:0;filter:none}
        svg.dgabf [data-seg]:hover .part{stroke-width:1.4;filter:none}
        svg.dgabf [data-seg].sel-part .part{stroke-width:2.4;filter:var(--dg-glow,drop-shadow(0 0 5px var(--cc)))}
        /* 壓暗那一階從 .3 放寬到 .55：進來的預設狀態是「族群 ic_substrate 被選起來」＝ abf_pcb 亮、
           substrate_material 與 hdi_pcb 被壓暗，而**被壓暗的正好是 core 與 ABF 膜**，也就是這張圖的主角。*/
        svg.dgabf [data-seg].dim{opacity:.55}
        svg.dgabf g[data-part="abf_die_ghost"].sel-part path{opacity:.8}
      </style>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead，SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">IC 載板：晶片底下那塊板子，跟主機板不是同一種東西</text>
      <text class="cap ext" x="0" y="0">以中間那片 core 為中心、上下對稱長出 ABF 增層；上表面用 bump pad 接晶片，下表面用 BGA 錫球接主機板。這裡把九層一片一片拆開來看：每一層的微孔都是「這一層自己的孔」（從這一層的銅打到底面），疊孔靠虛線軸心對齊。藍色虛線＝訊號路徑：BGA → core 貫孔 → 微孔 → bump pad（可用「動畫」鈕停）。三格放大、三條路線與製程收在下面兩段。</text>

      <!-- ================= §1 主視圖：垂直爆炸拆解 =================
           畫的順序＝由後往前：厚度面 → 增層 → core → 孔 → 線 → 防焊 → 墊子 → 主機板 → 灰色剪影 → 凸塊 → 訊號。-->
      ${gSlab()}
      ${gFilm()}${gCore()}${gCoreVia()}${gUvia()}${gStack()}${gTrace()}${gSr()}${gPad()}
      ${gMb()}${gGhost()}${gBumps()}${gSignal()}

      <!-- ================= 說明卡片（HTML，左右兩欄）：左欄錨點在剖面左緣、右欄錨點在右半邊 ================= -->
      ${extRow({ side: 'l', no: 1, seg: 'substrate_material', part: 'abf_core', color: COL.core, ax: 34, ay: (Y.core[0] + Y.core[1]) / 2,
    title: '核心層 core：玻纖布補強的樹脂板', sub: '最厚、唯一有織紋的一層' })}
      ${extRow({ side: 'l', no: 3, seg: 'substrate_material', part: 'abf_film', color: COL.abf, ax: 34, ay: Y.u1[0] + 14,
    title: 'ABF 增層膜（味之素增層膜）', sub: '無玻纖樹脂膜，一層一層貼上' })}
      ${extRow({ side: 'l', no: 8, seg: 'abf_pcb', part: 'abf_sr', ax: 34, ay: Y.srT[0] + 4,
    title: '防焊開窗（SR opening）', sub: '蓋住整面，只在墊子處開窗' })}
      ${extRow({ side: 'l', no: 9, seg: 'hdi_pcb', part: 'abf_motherboard', ax: 34, ay: Y.mbT + 12,
    title: '這一條才是「PCB」：主機板', sub: '走線比載板粗一個量級' })}
      ${note({ side: 'l', warn: true, title: '★「載板材料 ABF / BT」這一格台股掛零',
    lines: ['ABF 膜是味之素（市占約 95%，來源：今周刊 2026-05）、BT 樹脂 core 是三菱瓦斯化學 —— 兩家都是外商；點 core／ABF 膜再點色標，成分股會是 0 筆，那不是壞掉。',
      '點零件篩到的是「環節」不是整個族群：「IC 載板」這一格收錄 3037 欣興／8046 南電／3189 景碩。',
      '示意圖，非實物比例；圖上 core ＋ 上下各 3 層，實際為十幾至二十幾層。'] })}
      ${extRow({ side: 'r', no: 2, seg: 'abf_pcb', part: 'abf_core_via', color: COL.cu, ax: 432, ay: (Y.core[0] + Y.core[1]) / 2,
    title: 'core 的貫孔：只穿 core', sub: '鑽穿→鍍銅→填塞→兩端蓋銅' })}
      ${extRow({ side: 'r', no: 4, seg: 'abf_pcb', part: 'abf_trace', color: COL.cu, ax: 440, ay: CU.u2 + 3,
    title: '半加成細線（SAP／mSAP）', sub: '比高階 PCB 再細一個量級' })}
      ${extRow({ side: 'r', no: 5, seg: 'abf_pcb', part: 'abf_uvia', color: COL.cu, ax: 432, ay: Y.u3[0] + 13,
    title: '雷射微孔：上寬下窄，窄端朝 core', sub: '一孔只穿一層；先除膠渣' })}
      ${extRow({ side: 'r', no: 6, seg: 'abf_pcb', part: 'abf_stack_via', color: COL.cu, ax: VIA.stack, ay: (Y.u2[1] + Y.u1[0]) / 2,
    title: '疊孔（stacked via）', sub: '填實了才能正上方再疊一個' })}
      ${extRow({ side: 'r', no: 7, seg: 'abf_pcb', part: 'abf_bump_pad', color: COL.cu, ax: 382, ay: CU.u3 - 1,
    title: '凸塊墊 bump pad ＋ 表面處理', sub: '接晶片；墊子比球墊小得多' })}
      ${extRow({ side: 'r', no: 10, part: 'abf_die_ghost', color: COL.off, ax: 360, ay: (Y.dieT + Y.dieB) / 2,
    title: '晶粒／中介層：不是這張圖的主題', sub: '看半導體鏈 CoWoS 那張' })}

      <!-- ================= ② 為什麼載板比主機板貴 ＋ 三格放大（預設收合；座標由 wireFolds 量）================= -->
      ${fold('abf2', '② 為什麼載板比主機板貴 ＋ 三格放大', '四點結論；三種節距差一個量級、ABF 無玻纖 BT 有、板子越大越翹', `
      <rect class="frame" x="16" y="500" width="488" height="176" rx="8"/>
      <text class="hd" x="30" y="524">為什麼載板比主機板貴</text>
      <text class="sub" x="30" y="546">① 線細一個量級：走半加成（SAP／mSAP），一層一層長出來</text>
      <text class="sub" x="30" y="564">② 層數是「循環」出來的：每多一層就多一次貼膜、雷射、除膠渣、</text>
      <text class="sub" x="30" y="582">　 電鍍、蝕刻，而整片的良率是每一層的連乘</text>
      <text class="sub" x="30" y="600">③ 關鍵材料幾乎只有一家（ABF 增層膜），材料漲價直接進成本</text>
      <text class="sub" x="30" y="618">④ 越做越大就越難：尺寸一大，翹曲、平坦度、電鍍均勻度同時變嚴</text>
      <text class="cap" x="30" y="644">一般高階 PCB 的線寬到 50 µm 已算高階，載板要細一個量級</text>
      <text class="cap" x="30" y="662">（50 µm 的來源見規格書 §7-B1，2026 查；載板自己的線寬不寫數字）。</text>
      ${panelA(16, 690, 238)}${panelC(266, 690, 238)}
      ${panelB(16, 936, 488)}`)}

      <!-- ================= ③ 路線圖 ＋ AI 為什麼推到極限 ＋ 製程五格 ＋ 台股掛零（預設收合）================= -->
      ${fold('abf3', '③ 三條路線圖、AI 為什麼把載板推到極限、製程五格', '有核心／無核心／玻璃核心只差中間一層；五格製程與除膠渣；材料那一格為什麼沒有台股', `
      ${roadmap(16, 1176, 488)}
      <rect class="frame" x="16" y="1326" width="488" height="116" rx="8"/>
      <text class="hd" x="30" y="1350">AI 為什麼把載板推到極限</text>
      <text class="sub" x="30" y="1374">① 晶片變大、要接的線變多 → 載板跟著變大、層數變多</text>
      <text class="sub" x="30" y="1392">② 大板子在迴焊高溫下翹得更兇（樹脂與矽差太多）</text>
      <text class="sub" x="30" y="1410">③ 所以才有人提無核心（路徑短）與玻璃核心（更硬）</text>
      <text class="sub" x="30" y="1428">④ 這兩條路都要換設備、重新認證，不是換個材料就好</text>

      <!-- 製程列（五格）＝ §3-C：P1 增層在防焊之前、P2 第三格裡有除膠渣、P3 材料商與載板廠之間有分界線、P4 第三格標明上下同時 -->
      <text class="cap" x="16" y="1472">製造流程（五格）　★ 增層循環一定在防焊與表面處理之前；</text>
      <text class="cap" x="16" y="1490">雷射開孔之後、鍍銅之前一定有「除膠渣」那一步</text>
      <path d="M178,1496 V1546" stroke="var(--dg-warn)" stroke-dasharray="5 4" fill="none" opacity=".85" style="stroke-width:var(--dg-hair-w,2)"/>
      ${processBar(16, 1500, steps, 156, { cols: 3 })}
      <text class="sub" x="16" y="1618" style="fill:var(--dg-warn)">← 材料商（外商）</text>
      <text class="sub" x="184" y="1618">載板廠（3037 欣興／8046 南電／3189 景碩）→</text>
      <text class="cap" x="16" y="1642">③ 的完整一圈：貼 ABF 膜 → 雷射開微孔 → 除膠渣（desmear）→ 化學鍍薄銅</text>
      <text class="cap" x="16" y="1660">　 → 圖案電鍍（SAP／mSAP）→ 蝕刻，上下兩面同時做、重複 N 次。</text>

      <!-- 台股掛零那一格：畫面上一定要解釋，不要讓人以為點壞了 -->
      <text class="sub" x="16" y="1688" style="fill:var(--dg-warn)">★「載板材料 ABF / BT」這一格台股掛零：ABF 膜幾乎是單一供應商（味之素）、</text>
      <text class="sub" x="16" y="1706" style="fill:var(--dg-warn)">　 BT 樹脂 core 是三菱瓦斯化學，兩家都是外商。點 core、ABF 膜、〔B〕或路線圖，</text>
      <text class="sub" x="16" y="1724" style="fill:var(--dg-warn)">　 再點下面同色的環節色標，成分股會是 0 筆 —— 那不是壞掉，是這一格真的沒有台股。</text>
      <text class="cap" x="16" y="1750">示意圖，非實物比例｜層數與各層厚度均為示意；載板線寬、CTE、封裝尺寸、供需與價格</text>
      <text class="cap" x="16" y="1768">一律不寫數字（來源對不起來，見規格書 §7-B／§7-C）。圖上畫 core ＋ 上下各 3 層增層，</text>
      <text class="cap" x="16" y="1786">實際為十幾至二十幾層（這句話本身也是示意，不是規格）。</text>`)}
    </svg>`;
  }

  window.DG.register('ic_substrate', {
    level: 'group', chain: 'ai_server',
    name: 'IC 載板：ABF 增層剖面',
    draw: abfSubstrate, native: CW, scene: null,
    q: 'AI 晶片底下那塊板子為什麼比主機板貴？ABF 膜、細線、微孔各卡在哪一關，台股站在哪幾家？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       這張圖是 R4（台股沒有人做的零件要明說）最典型的案例：**核心層與 ABF 膜這兩層台股一家都沒有**，
       而那正是整條鏈的卡點。`cos` 只放代號，「這家在這裡負責什麼」一律讀 supply_chain.json 的 companies[].tech（R3）。
       `items` 只填 supply_chain 的 edges[].item 真的有的字串；沒寫 items 的零件走預設（該環節流進／流出的全部品項）。*/
    parts: {
      abf_core: {
        desc: '整塊載板最厚、也是唯一看得出玻纖織紋的那一層。它的工作是撐住不變形，上下增層才有東西可以長。',
        items: ['BT 樹脂 core CCL'],
        none: 'core 用的 BT 樹脂銅箔基板由三菱瓦斯化學（MGC，日）供應 —— ★ 這一層的板材台股沒有廠商做。把 core 加工成載板的才是下面那三家台廠。',
      },
      abf_film: {
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
      abf_core_via: { desc: '鑽穿 core → 鍍銅 → 填塞 → 兩端蓋銅，而且只穿 core。跟主機板那種貫穿整塊板的孔不是同一件事。' },
      abf_trace: { desc: '半加成法（SAP／mSAP）：先鍍一層很薄的銅，再把線「長」出來，不是把整片銅蝕掉。載板的線寬要比高階 PCB 再細一個量級。' },
      abf_uvia: { desc: '雷射微孔，上寬下窄、窄的那一端朝向 core，一個孔只穿一層增層。打完一定要先除膠渣（desmear），銅才附得上去。' },
      abf_stack_via: { desc: '疊孔：微孔要先用電鍍銅填實，正上方才能再疊一個孔。層數越多、疊得越高，越吃電鍍能力 —— 這是載板廠之間真正拉開差距的地方。' },
      abf_bump_pad: { desc: '晶片的凸塊就焊在這裡。上表面接晶片的墊子，比下表面接主機板的球墊小得多。' },
      abf_sr: { desc: '防焊蓋住整面，只在要接晶片、要接主機板的墊子上開窗 —— 開窗的位置與大小決定焊得上焊不上。' },
      abf_motherboard: {
        name: '主機板（載板底下那塊板）',
        desc: '載板底下那塊主機板（這張圖只畫一小段，右端鋸齒＝還有、只是沒畫）。它的走線寬與節距比載板粗一個量級，兩者擺在同一張圖上就是那把尺。',
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
