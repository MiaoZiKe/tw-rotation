/* IC 載板：ABF 增層剖面 —— docs/diagram_plan.md 的第 3 張（族群 `ic_substrate`、ai_server 鏈）

   合約＝`docs/diagram_specs/abf_substrate.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的四件事：

     · §0-A **不做真 3D**（`scene: null`）。要加 3D 就是改規格書、重新簽，
       不准實作時順手加。回頭加 3D 的唯一條件寫在 §0-A，不是「看起來比較立體」。
     · §0-B（一）跟 `pcb_stackup`（PCB 硬板那張）的分工：
       **PCB 那張的下游是「把零件焊上去」，這張的下游是「把晶片黏上去」。**
       明列五樣這張圖不准畫：銅箔稜面三格、玻纖織紋放大格、四種孔對照、
       走線頂視小圖、表面處理比較表。這個檔一樣都沒有（M6）。
     · §0-B（二）跟既有 `semiconductor()`（CoWoS 剖面）的分工：
       **中介層以上一律只畫灰色剪影、不標細節、不掛 `data-seg`**（M5、D2）。
     · §7-B／§7-C：查不到的東西一個數字都不編。畫面上唯一的百分比是 ABF 膜市占，
       而且必須連同「來源：今周刊 2026-05」一起寫（N1）。載板線寬、CTE 的 ppm、
       封裝 mm 數、供需缺口、良率與單價差距**全部不進畫面**。

   為什麼主視圖是「正剖面 ＋ 等角厚度」而不是整塊等角切角
   ------------------------------------------------------
   規格書要的是 2.5D cut-away。這張圖的內容是**九層薄層疊構 ＋ 錐形微孔 ＋
   只穿 core 的貫孔**，全部的資訊都在剖面上（§0-A 自己判 3D 時用的也是這個理由）。
   整塊等角切角（mlccStack 那種）會把剖面壓成 30° 斜面：26px 厚的增層在斜面上
   只剩 13px、錐度看不出來，而且引線要從斜面拉出去一定得橫越主角。
   所以主體畫成**正剖面**，另外把頂面與右側面往右後上擠出去（`TF`／`RF`）當厚度 ——
   立體感與「切開來看」兩件事都成立，錐度與層厚也守得住。
   右側面同時是說明列引線的出口：引線從剖面右緣水平出去就到文字框，不橫越主角。

   這個檔不碰 `site/diagrams.js`／`site/index.html`／`site/three3d.js`
   （同時有九個人在畫別的圖）。共用工具一律走 `window.DG`。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;   // diagrams.js 沒載到就安靜退出

  /* ================================================================ 版面常數（全部是螢幕座標）

     剖面：x ∈ [XL, XR]＝載板的長，y 往下＝往底層。等角厚度往右後上 (DX, DY)。*/
  const XL = 22, XR = 460, DX = 22, DY = -12;

  /* 層界（由上往下）。**core 78px、每一層增層 26px ＝ core 是任一層增層的三倍厚**（S2）；
     上下各三層、對應層厚度相同（S3）；防焊上下各 10px、成對出現（S6）。*/
  const Y = {
    dieT: 78, dieB: 110,          // 晶粒（灰色剪影）
    ubT: 110, ubB: 118,           // 微凸塊（最小的一種）
    itT: 118, itB: 140,           // 中介層（灰色剪影）
    c4T: 140, c4B: 164,           // C4 凸塊（中）
    srT0: 158, srT1: 168,         // 上防焊（接晶片那一面）
    u3: [168, 194], u2: [194, 220], u1: [220, 246],
    core: [246, 324],             // ← 全圖最厚的一層，而且只有這一層有織紋
    l1: [324, 350], l2: [350, 376], l3: [376, 402],
    srB0: 402, srB1: 412,         // 下防焊（接主機板那一面）
    mbT: 442, mbB: 470,           // 主機板（只畫一小段）
  };
  /* 每一層增層「自己那一層的銅」。增層的銅在**外側**：上半部在該層上緣、下半部在該層下緣
     —— 因為增層是從 core 往外一層一層長出來的，這也是微孔錐度方向的由來。*/
  const CU = {
    u3: 168, u2: 194, u1: 220,
    coreT: 246, coreB: 318,              // core 的兩面線路
    l1: 344, l2: 370, l3: 396,
  };
  const CUH = 6;

  // 三種凸塊的位置（主視圖的節距是示意，真實比例在〔放大格 A〕）
  const PADS = [200, 226, 252, 278, 304, 330, 356, 382];        // bump pad／C4，節距 26
  const BALLS = [48, 113, 178, 243, 308, 373, 438];             // BGA 球墊，節距 65
  const UBUMPS = []; for (let i = 0; i < 16; i++) UBUMPS.push(228 + i * 8.5);   // 微凸塊，節距 8.5

  /* 孔的位置。
     · core 貫孔三個，**只穿 core**（V1）
     · 微孔一層一組，**只穿一層增層**（V2），上下兩側都朝 core 收窄（V3）
     · 疊孔固定在 x=380（U1 與 U2 軸心對齊，中間看得到一段填平的銅，V4）*/
  const VIA = {
    core: [78, 250, 432],
    u1: [96, 190, 290], u2: [140, 236, 330], u3: [112, 200, 306, 432],
    l1: [130, 240, 386], l2: [104, 286, 410], l3: [170, 316, 424],
    stack: 380,
  };

  // 說明列（右欄）。引線折點各自錯開，但全部落在 485.5～510 —— 剖面最右到 482，所以不橫越主角
  const LX = 520, LW = 446;
  const elbow = (i) => 510 - i * 3.5;

  /* ================================================================ 小工具
     `TF`／`RF` 就是那個 2.5D：把剖面往右後上擠出去的頂面與右側面。*/
  const TF = (x0, x1, y, fill) =>
    `<path d="M${x0},${y} L${x1},${y} L${x1 + DX},${y + DY} L${x0 + DX},${y + DY}Z" fill="${fill}"/>`;
  const RF = (y0, y1, fill) =>
    `<path d="M${XR},${y0} L${XR + DX},${y0 + DY} L${XR + DX},${y1 + DY} L${XR},${y1}Z" fill="${fill}"/>`;
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;

  /* 玻纖織紋。**整張圖只有 core 那一層可以呼叫它**（S4）——
     ABF 是不含織造玻纖的樹脂膜，那正是它能打出更小的孔、做出更細的線的原因（§7-A1）。
     橫向緯紗走波浪、縱向經紗用短豎線，看得出是「布」而不是純樹脂。
     行數依帶高自動決定，所以同一支函式也能畫〔放大格 B〕與路線圖裡那種很薄的帶。*/
  function weave(x0, x1, y0, y1) {
    const h = y1 - y0, w = x1 - x0;
    const n = Math.max(1, Math.floor((h - 4) / 16));
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
     兩者放在同一張圖上，「**細一個量級**」這句話就不必靠數字
     （§7-B1：三個來源的載板線寬互相對不起來，畫面上一個數字都不寫）。*/
  function traces(y, x0, x1, w, pitch) {
    const a = [];
    for (let x = x0; x <= x1 - w; x += pitch) a.push(`M${x},${y} h${w} v${CUH} h${-w}Z`);
    return `<path class="part" d="${a.join(' ')}" fill="var(--dg-cu)"/>`;
  }

  /* 雷射微孔：**上寬下窄的錐形，窄的那一端一律朝向 core**（V2、V3）。
     `yOut`＝外側（離 core 遠，寬）、`yIn`＝內側（靠 core，窄）：
     上半部 yOut < yIn、下半部 yOut > yIn，同一支函式兩邊都對，
     所以不會出現「下半部的微孔也朝下收窄」那個最常見的錯（4-B 的 V3 那一列）。
     內部一律畫成**填實**，不然疊孔那一格會自相矛盾（V4）。*/
  const uvia = (x, yOut, yIn, wOut, wIn) =>
    `M${x - wOut / 2},${yOut} L${x + wOut / 2},${yOut} L${x + wIn / 2},${yIn} L${x - wIn / 2},${yIn}Z`;

  /* ================================================================ 主視圖的各個零件 */

  // ---- 等角厚度：頂面與右側面（先畫，正剖面壓在上面）
  const gSlab = () => [
    TF(XL, XR, Y.srT0, 'var(--dg-sr-2)'),
    RF(Y.srT0, Y.srT1, 'var(--dg-sr-2)'),
    RF(Y.u3[0], Y.u3[1], 'var(--dg-abf-2)'), RF(Y.u2[0], Y.u2[1], 'var(--dg-abf-2)'), RF(Y.u1[0], Y.u1[1], 'var(--dg-abf-2)'),
    RF(Y.core[0], Y.core[1], 'var(--dg-core-2)'),
    RF(Y.l1[0], Y.l1[1], 'var(--dg-abf-2)'), RF(Y.l2[0], Y.l2[1], 'var(--dg-abf-2)'), RF(Y.l3[0], Y.l3[1], 'var(--dg-abf-2)'),
    RF(Y.srB0, Y.srB1, 'var(--dg-sr-2)'),
  ].join('');

  // ---- 核心層 core：唯一有織紋的一層，也是全圖最厚的一層
  const gCore = () => `<g data-seg="substrate_material" data-part="abf_core">
    ${R(XL, Y.core[0], XR - XL, Y.core[1] - Y.core[0], 'var(--dg-core)', 'part')}
    ${weave(XL + 4, XR - 4, Y.core[0], Y.core[1])}</g>`;

  /* ---- core 的貫孔。
     §7-B7 把它標成**低信心**（查得到「鑽孔＋鍍銅連通上下」，查不到填塞與蓋銅的可引用出處）。
     這次另外查到一條 IEEE 研討會論文摘要，講 HDI／IC 載板 core 貫孔的既有做法是
     「保形鍍銅 → 以環氧或膏填塞 → 平坦化 → 電鍍銅蓋層」，所以畫成
     孔壁銅 ＋ 內部填塞物 ＋ 兩端蓋銅。**畫面上的文字只寫「鍍銅 → 填塞 → 兩端蓋銅」，
     不寫材料名、不寫厚度**，並由「示意圖」那一行涵蓋 —— 照 §7-B7 的處置。
     ⚠ 這仍然是這張圖裡最該被下一位審查者挑戰的零件。
     V1：孔身嚴格落在 core 的 246～324，兩端都停在 core 表面；
     蓋銅是「長在 core 表面上的那一片銅」，所以各往外多 4px，不是孔穿出去。*/
  const gCoreVia = () => `<g data-seg="abf_pcb" data-part="abf_core_via">${VIA.core.map(x => ''
    + R(x - 9, Y.core[0], 18, Y.core[1] - Y.core[0], 'var(--dg-plug)', 'part')
    + R(x - 13, Y.core[0], 4, Y.core[1] - Y.core[0], 'var(--dg-cu)')
    + R(x + 9, Y.core[0], 4, Y.core[1] - Y.core[0], 'var(--dg-cu)')
    + R(x - 17, Y.core[0] - 4, 34, 10, 'var(--dg-cu)', '', 1.5)
    + R(x - 17, Y.core[1] - 6, 34, 10, 'var(--dg-cu)', '', 1.5)).join('')}</g>`;

  /* ---- ABF 增層膜：上下各三層，**層數與厚度都相等**（S3）、**沒有織紋**（S4）。
     不是 prepreg 膠片 —— 載板的增層是一層一層貼上去的膜；
     畫成「core 夾 prepreg」就是把載板畫成 PCB 了（S1）。*/
  const FILMS = () => [Y.u3, Y.u2, Y.u1, Y.l1, Y.l2, Y.l3];
  const gFilm = () => `<g data-seg="substrate_material" data-part="abf_film">
    ${FILMS().map(r => R(XL, r[0], XR - XL, r[1] - r[0], 'var(--dg-abf)', 'part')).join('')}
    ${FILMS().map(r => `<path d="M${XL},${r[0]} H${XR}" stroke="var(--dg-abf-2)" stroke-width="1" opacity=".8"/>`).join('')}</g>`;

  // ---- 半加成細線（SAP／mSAP）＋ core 的兩面線路
  const gTrace = () => `<g data-seg="abf_pcb" data-part="abf_trace">
    ${traces(CU.u3, XL + 6, XR - 6, 7, 16)}${traces(CU.u2, XL + 10, XR - 6, 7, 16)}${traces(CU.u1, XL + 6, XR - 6, 7, 16)}
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
     沒有填平就疊不上去，所以中間那塊銅一定要看得到。*/
  const gStack = () => { const x = VIA.stack; return `<g data-seg="abf_pcb" data-part="abf_stack_via">
    <path class="part" d="${uvia(x, CU.u1 + CUH, Y.u1[1], 16, 8)}${uvia(x, CU.u2 + CUH, Y.u2[1], 16, 8)}" fill="var(--dg-cu)"/>
    ${R(x - 11, CU.u1 - 2, 22, 10, 'var(--dg-cu)', '', 2)}
    <path d="M${x},${Y.u2[1] - 18} v42" stroke="var(--dg-accent)" stroke-width=".9" stroke-dasharray="3 3" opacity=".5"/></g>`; };

  /* ---- 防焊層與開窗：**兩個外表面都有**（S6），而且只在墊子處開窗。
     上表面開窗給 bump pad（接晶片）、下表面開窗給球墊（接主機板）—— 兩側不准對調（S5）。*/
  function srBand(y0, y1, gaps) {
    const segs = []; let cur = XL;
    gaps.forEach(([a, b]) => { if (a > cur) segs.push([cur, a]); cur = b; });
    if (cur < XR) segs.push([cur, XR]);
    return segs.map(([a, b]) => R(a, y0, b - a, y1 - y0, 'var(--dg-sr)', 'part')).join('');
  }
  const gSr = () => `<g data-seg="abf_pcb" data-part="abf_sr">
    ${srBand(Y.srT0, Y.srT1, PADS.map(x => [x - 7, x + 7]))}
    ${srBand(Y.srB0, Y.srB1, BALLS.map(x => [x - 13, x + 13]))}</g>`;

  /* ---- 凸塊墊 ＋ 表面處理。
     上表面 bump pad 寬 16、下表面 BGA 球墊寬 30 ——**兩側墊子大小明顯不同**（S5）。
     表面處理只畫在開窗露出來的銅上，沒有蓋在防焊之上、也沒有畫成整片（S7）。
     §7-C：各家載板廠實際用哪一種表面處理**查不到**，所以只寫「表面處理」，
     種類比較導去「PCB 硬板」那張（§0-B 一：那張已經比過，這張不重畫）。*/
  const gPad = () => `<g data-seg="abf_pcb" data-part="abf_bump_pad">
    ${PADS.map(x => R(x - 8, CU.u3, 16, CUH, 'var(--dg-cu)', 'part') + R(x - 6, Y.srT1 - 4, 12, 4, 'var(--dg-ni)')).join('')}
    ${BALLS.map(x => R(x - 15, CU.l3, 30, CUH, 'var(--dg-cu)', 'part') + R(x - 11, Y.srB0, 22, 5, 'var(--dg-ni)')).join('')}</g>`;

  /* ---- 三種凸塊（§7-D2：**一律不掛 data-seg**）。
     凸塊算封裝廠還是載板廠做的依製程分工而異，這次查不到可引用的分工說法；
     掛上去等於在網站上宣稱一個沒有證據的分工。掛 adv_pkg 又會讓人以為這張圖在講先進封裝。*/
  const gBumps = () => `<g pointer-events="none">
    ${UBUMPS.map(x => R(x - 1.7, Y.ubT, 3.4, Y.ubB - Y.ubT, 'var(--dg-sn)')).join('')}
    ${PADS.map(x => R(x - 5, Y.c4T, 10, Y.c4B - Y.c4T, 'var(--dg-sn)', '', 4)).join('')}
    ${BALLS.map(x => `<ellipse cx="${x}" cy="423" rx="14" ry="16" fill="var(--dg-sn)"/>`).join('')}</g>`;

  /* ---- 晶粒與中介層：**灰色剪影，不標任何內部細節**（M5、§0-B 二）。
     不畫 TSV、不畫微凸塊結構、不畫 RDL／LSI —— 那是半導體鏈「CoWoS 2.5D 封裝剖面」的主題。
     用 --dg-mute 的三階透明度當三個面，跟 mlccStack「附註級圖形給單色」同一套語彙。*/
  function ghost(x0, x1, y0, y1) {
    return `<path d="M${x0},${y0} L${x1},${y0} L${x1 + DX},${y0 + DY} L${x0 + DX},${y0 + DY}Z" fill="var(--dg-mute)" opacity=".5"/>`
      + `<path d="M${x1},${y0} L${x1 + DX},${y0 + DY} L${x1 + DX},${y1 + DY} L${x1},${y1}Z" fill="var(--dg-mute)" opacity=".3"/>`
      + `<path d="M${x0},${y0} L${x1},${y0} L${x1},${y1} L${x0},${y1}Z" fill="var(--dg-mute)" opacity=".42"/>`;
  }
  const gGhost = () => `<g pointer-events="none">${ghost(190, 400, Y.itT, Y.itB)}${ghost(215, 366, Y.dieT, Y.dieB)}</g>`;

  /* ---- 主機板（只畫一小段）。右端畫成鋸齒＝「還有，只是沒畫」。
     走線寬 34／節距 60，跟上面載板的寬 7／節距 16 擺在同一張圖上 —— 那就是「細一個量級」的尺。*/
  const gMb = () => {
    const mx0 = 4, mx1 = 458, zig = [];
    for (let i = 0; i * 7 + Y.mbT < Y.mbB; i++) zig.push(`L${mx1 - (i % 2 ? 7 : 0)},${Y.mbT + (i + 1) * 7}`);
    return `<g data-seg="hdi_pcb" data-part="abf_motherboard">
      ${TF(mx0, mx1, Y.mbT, 'var(--dg-pcb-2)')}
      <path class="part" d="M${mx0},${Y.mbT} L${mx1},${Y.mbT} ${zig.join(' ')} L${mx0},${Y.mbB}Z" fill="var(--dg-pcb)"/>
      ${BALLS.map(x => R(x - 15, Y.mbT - 4, 30, CUH, 'var(--dg-cu)')).join('')}
      ${traces(Y.mbT + 14, mx0 + 10, mx1 - 20, 34, 60)}</g>`;
  };

  /* ---- 訊號路徑（這張圖唯一的動畫，§9）。
     一個訊號從 BGA 錫球進來 → 穿過 core 貫孔 → 沿增層的細線與微孔往上 → 從 bump pad 出去。
     **層與孔一個都不會跑來跑去**；按「動畫：關」之後整條路徑仍然看得見
     （底下那條實線就是靜止時的樣子）。虛線走 CSS 的 dgdash、白點走 SMIL，
     industry.js 的 setAnimAll 兩種都會停 —— 所以不必在這裡自己做開關。*/
  const SIG = `M243,430 L243,${CU.l3 + 3} L170,${CU.l3 + 3} L170,${CU.l2 + 3} L286,${CU.l2 + 3} `
    + `L286,${CU.l1 + 3} L240,${CU.l1 + 3} L240,${CU.coreB + 3} L250,${CU.coreB + 3} L250,${CU.coreT + 3} `
    + `L380,${CU.coreT + 3} L380,${CU.u2 + 3} L306,${CU.u2 + 3} L306,${CU.u3 + 3} L304,${CU.u3 + 3} L304,150`;
  const gSignal = () => `<g pointer-events="none">
    <path d="${SIG}" stroke="var(--dg-accent)" stroke-width="1.5" fill="none" opacity=".32"/>
    <path class="flow slow" d="${SIG}" stroke="var(--dg-accent)" stroke-width="2.2" fill="none" opacity=".9"/>
    <circle r="3.4" fill="var(--dg-accent)" opacity=".95"><animateMotion dur="7s" repeatCount="indefinite" path="${SIG}"/></circle></g>`;

  /* ================================================================ 說明列（右欄）

     為什麼不直接呼叫 `DG.labelRow`：這張圖的每一句話都塞不進一行 12px 的字，
     而且說明列要跟零件共用 `data-part`（D4：點說明列＝點那個零件，兩層高亮才對得起來），
     `labelRow` 兩件事都沒有參數。
     **副標只有一行時，幾何跟 labelRow 完全一樣**（底框 40 高、標題基線 y+2、
     副標基線 y+18、引線折法相同、class 全部沿用 diagrams.js 那一套）——
     這不是第二套樣式，只是多了「副標可以多行」與「帶 data-part」。
     其餘共用工具（STYLE／processBar）照用。*/
  function lrow(o) {
    const subs = o.subs || [];
    const h = 24 + 16 * Math.max(subs.length, 1);
    const eb = elbow(o.i);
    return `<g class="lrow" data-seg="${o.seg}" data-part="${o.part}">
      <rect class="bg" x="${LX - 8}" y="${o.y - 15}" width="${LW}" height="${h}" rx="6"/>
      <path class="leader" d="M${o.ax},${o.ay} L${eb},${o.ay} L${eb},${o.y - 2} L${LX - 2},${o.y - 2}"/>
      <circle class="dot" cx="${LX + 5}" cy="${o.y - 2}" r="4"/>
      <text class="lbl" x="${LX + 16}" y="${o.y + 2}">${o.t}</text>
      ${subs.map((t, k) => `<text class="sub" x="${LX + 16}" y="${o.y + 18 + k * 16}">${t}</text>`).join('')}</g>`;
  }

  const ROWS = [
    { seg: 'substrate_material', part: 'abf_core', y: 100, ax: 471, ay: 279,
      t: '核心層 core（玻纖布補強的樹脂板）',
      subs: ['BT 環氧或玻璃環氧。它的工作是撐住不變形，是全板最厚的一層',
        '★ 整張圖只有這一層看得出織紋；上下增層的層數與厚度必須相等'] },
    { seg: 'abf_pcb', part: 'abf_core_via', y: 166, ax: 446, ay: 285,
      t: 'core 的貫孔',
      subs: ['鑽穿 core → 鍍銅 → 填塞 → 兩端蓋銅，而且只穿 core',
        '跟主機板那種貫穿全板的孔不是同一件事（孔內處理為示意）'] },
    { seg: 'substrate_material', part: 'abf_film', y: 232, ax: 471, ay: 207,
      t: 'ABF 增層膜（味之素增層膜）',
      subs: ['熱固性樹脂膜，不含織造玻纖 —— 這就是它能打出更小的孔、',
        '做出更細的線的原因。是一層一層貼的膜，不是 prepreg 膠片',
        '幾乎是單一供應商（市占約 95%，來源：今周刊 2026-05）'] },
    { seg: 'abf_pcb', part: 'abf_trace', y: 298, ax: 440, ay: 223,
      t: '半加成細線（SAP／mSAP）',
      subs: ['先鍍一層很薄的銅，再把線「長」出來，不是把整片銅蝕掉',
        '一般高階 PCB 的線寬到 50 µm 已算高階，載板要細一個量級',
        '（50 µm 的來源見規格書 §7-B1，2026 查；載板自己的線寬不寫數字）'] },
    { seg: 'abf_pcb', part: 'abf_uvia', y: 380, ax: 441, ay: 183,
      t: '雷射微孔',
      subs: ['上寬下窄，窄的那一端朝向 core；一個孔只穿一層增層',
        '打完一定要先除膠渣（desmear），銅才附得上去'] },
    { seg: 'abf_pcb', part: 'abf_stack_via', y: 446, ax: 392, ay: 210,
      t: '疊孔（stacked via）',
      subs: ['微孔要先用電鍍銅填實，正上方才能再疊一個孔',
        '層數越多、疊得越高，越吃電鍍能力'] },
    { seg: 'abf_pcb', part: 'abf_bump_pad', y: 512, ax: 382, ay: 171,
      t: '凸塊墊（bump pad）＋ 表面處理',
      subs: ['晶片的凸塊就焊在這裡；上表面的墊子比下表面的球墊小得多',
        '表面處理的種類比較見「PCB 硬板：多層板剖面與走線」那張'] },
    { seg: 'abf_pcb', part: 'abf_sr', y: 578, ax: 452, ay: 163,
      t: '防焊開窗（SR opening）',
      subs: ['防焊蓋住整面，只在要接晶片／接主機板的墊子上開窗'] },
  ];

  /* ================================================================ 〔放大格 A〕三種節距
     同一條基線、同一個起點，**線段長度就是節距**。
     長度比例直接取 §7-A10 那兩個獨立來源區間的中位數（約 45 : 175 : 750），
     所以三根一眼看得出差一個量級（M2）。**尺上不標 µm 數字**，只標小／中／大與來源。*/
  function panelA(x, y, w) {
    const k = 200 / 750, x0 = x + 18;
    const rows = [['微凸塊　晶片 ↔ 中介層（最小）', 45, 3.2],
      ['C4 凸塊　晶片／中介層 ↔ 載板（中）', 175, 6],
      ['BGA 錫球　載板 ↔ 主機板（最大）', 750, 11]];
    return `<g pointer-events="none"><rect class="frame" x="${x}" y="${y}" width="${w}" height="214" rx="8"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">〔A〕三種節距，差一個量級</text>
      ${rows.map(([t, p, r], i) => { const yy = y + 62 + i * 44, len = p * k;
    return `<text class="sub" x="${x0}" y="${yy - 13}">${t}</text>`
      + `<path d="M${x0},${yy + 11} H${x0 + len}" stroke="var(--dg-ink-3)" stroke-width="1" stroke-dasharray="3 3"/>`
      + `<path d="M${x0},${yy + 6} v10 M${x0 + len},${yy + 6} v10" stroke="var(--dg-ink-3)" stroke-width="1"/>`
      + `<circle cx="${x0}" cy="${yy}" r="${r}" fill="var(--dg-sn)"/><circle cx="${x0 + len}" cy="${yy}" r="${r}" fill="var(--dg-sn)"/>`; }).join('')}
      <text class="sub" x="${x0}" y="${y + 186}">同一把尺、同一個起點，長度＝節距，不標數字。</text>
      <text class="cap" x="${x0}" y="${y + 204}">量級來源：產業技術媒體與學術論文（2026）。</text></g>`;
  }

  /* ================================================================ 〔放大格 B〕ABF vs BT
     M3：**BT 那格有織紋、ABF 那格沒有**。
     M4：這兩樣的供應商是外商，畫面上明講，不准讓人讀成台廠做的。*/
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
    const x0 = x + 20;
    return `<g pointer-events="none"><rect class="frame" x="${x}" y="${y}" width="${w}" height="214" rx="8"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">〔C〕板子越大越翹</text>
      <text class="sub" x="${x0}" y="${y + 48}">小板子：迴焊完還是平的</text>
      <path d="M${x0},${y + 70} H${x0 + 150}" stroke="var(--dg-abf)" stroke-width="7" stroke-linecap="round"/>
      ${R(x0 + 50, y + 56, 50, 9, 'var(--dg-mute)')}
      <path d="M${x0},${y + 82} H${x0 + 150}" stroke="var(--dg-ink-3)" stroke-width="1" stroke-dasharray="3 3"/>
      <text class="sub" x="${x0}" y="${y + 112}">大板子：翹成洋芋片，焊不好</text>
      <path d="M${x0},${y + 126} q75,38 150,-6" stroke="var(--dg-err)" stroke-width="7" fill="none" stroke-linecap="round"/>
      ${R(x0 + 50, y + 130, 50, 9, 'var(--dg-mute)')}
      <path d="M${x0},${y + 150} H${x0 + 150}" stroke="var(--dg-ink-3)" stroke-width="1" stroke-dasharray="3 3"/>
      <text class="sub" x="${x0}" y="${y + 174}">樹脂的熱膨脹係數比矽大很多，迴焊高溫</text>
      <text class="sub" x="${x0}" y="${y + 190}">下尺寸越大翹得越兇，翹了就焊不好。</text>
      <text class="cap" x="${x0}" y="${y + 206}">圖上不寫 ppm 值與封裝 mm 數（來源對不起來）。</text></g>`;
  }

  /* ================================================================ 路線圖：三條路，差別只在中間那一層
     §7-C：無核心與玻璃核心的**量產時程、台廠在這兩條路上的位置查不到**，
     所以這一格**只畫結構差異、不寫時程、不寫公司名**。
     §7-B4：玻璃核心的楊氏模數與翹曲量只有產業資料庫整理頁與 blog，**一個數字都不寫**。*/
  function roadmap(x, y, w) {
    const one = (mx, my, kind) => { const a = [];
      for (let i = 0; i < 3; i++) a.push(R(mx, my + i * 7, 150, 5, 'var(--dg-abf)'));
      const cy = my + 21;
      if (kind === 'core') { a.push(R(mx, cy, 150, 12, 'var(--dg-core)')); a.push(weave(mx + 3, mx + 147, cy, cy + 12)); }
      else if (kind === 'glass') { a.push(R(mx, cy, 150, 12, 'var(--dg-glass)'));
        a.push(`<path d="M${mx + 24},${cy + 11} l10,-10 M${mx + 64},${cy + 11} l10,-10 M${mx + 104},${cy + 11} l10,-10" stroke="var(--dg-ink)" stroke-width="1" opacity=".4" fill="none"/>`); }
      else { a.push(R(mx, cy + 4, 150, 4, 'var(--dg-abf)'));
        a.push(R(mx - 9, cy - 1, 9, 14, 'var(--dg-mute)')); a.push(R(mx + 150, cy - 1, 9, 14, 'var(--dg-mute)')); }
      for (let i = 0; i < 3; i++) a.push(R(mx, cy + 16 + i * 7, 150, 5, 'var(--dg-abf)'));
      return a.join(''); };
    return `<g data-seg="substrate_material" data-part="abf_roadmap">
      <rect class="frame part" x="${x}" y="${y}" width="${w}" height="136" rx="8"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">三條路，差別只在中間那一層（只畫結構差異，不寫時程、不寫公司名）</text>
      ${one(x + 22, y + 38, 'core')}${one(x + 212, y + 38, 'coreless')}${one(x + 402, y + 38, 'glass')}
      <text class="lbl" x="${x + 22}" y="${y + 110}">有核心（現在的主流）</text>
      <text class="lbl" x="${x + 212}" y="${y + 110}">無核心：拿掉 core</text>
      <text class="lbl" x="${x + 402}" y="${y + 110}">玻璃核心</text>
      <text class="sub" x="${x + 22}" y="${y + 128}">core 撐住不變形</text>
      <text class="sub" x="${x + 212}" y="${y + 128}">路徑短但更會翹，靠補強環</text>
      <text class="sub" x="${x + 402}" y="${y + 128}">更硬、熱膨脹更接近矽，更平</text></g>`;
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

    return `<svg class="dg dgm dgabf" viewBox="0 0 980 1300" width="100%" style="display:block">${D.STYLE}
      <style>
        /* 這張圖用到、但 site/index.html 的 --dg-* 名單裡還沒有的材質色。
           ⚠ 這一批**本來該住在 index.html 的 :root**（AGENTS §15：那一組由 art-director 擁有）。
           放在這裡的唯一理由是：這一輪同時有九個人在畫別的圖，「site/index.html」一動就撞，
           所以先定義在這張圖自己的 scope 上。**JS 裡一個 #xxxxxx 都沒有**，要換色只改這一處。
           下一次 art-director 動 index.html 時，把這七個 token 原樣搬進 :root 的 --dg-* 那一段、
           然後把這一段 style 整個刪掉就好（不是「自動讓位」，是要動手搬）。
           兩個主題共用同一組：.dgwrap 的底色 --illus 在深色與淺色下都是深底（既有決策），
           所以剖析圖的對比在兩個主題下本來就一樣。*/
        .dgabf{
          --dg-core:#3f4a30; --dg-core-2:#2f3824;   /* core：玻纖布補強樹脂（偏暗墨綠） */
          --dg-weave:#7d8c5c;                       /* core 的玻纖織紋（整張圖只有 core 有） */
          --dg-abf:#c3b9a4; --dg-abf-2:#9d947f;     /* ABF 增層膜：均勻、無織紋的樹脂膜 */
          --dg-sr:#2a6e86; --dg-sr-2:#1f5365;       /* 防焊層 */
          --dg-plug:#6b5f49;                        /* core 貫孔內的填塞物 */
          --dg-pcb-2:#12301f;                       /* 主機板的頂面（暗一階） */
          --dg-glass:#8fb6c9;                       /* 玻璃核心（路線圖第三格） */
        }
        /* ---- 描邊與發光各降一階（只作用在這一張圖）----
           全站的值（平時 1、選到 2.2、主角 3.6 ＋ 7px 暈開）是照 MLCC 那種
           「十幾個大零件」調的。這張圖的零件細碎得多：200 多條 7px 的細線、
           30 幾個微孔、16 個微凸塊。2.2px 的描邊套在 7px 寬的線上，那條線會整條變成
           實心的環節色塊，整片板子就變成一面發光的格子 —— 那正是 Andy 講的
           「螢光感太重，要的是精密儀器不是電競 RGB」。
           所以這張圖的四個狀態是：
             平時／選到的環節 → **完全不描邊**（「哪一個環節被選起來」由其餘的壓暗來講）
             滑鼠移上去       → 1.4px（告訴你這塊點得下去）
             **你點的那一個** → 2.4px ＋ 一圈 5px 的暈開（整張圖只有它會發光）
           兩層高亮的差距（0 vs 2.4 ＋ 只有主角發光）其實比全站預設更分得出來。

           ⚠ 前面多一個 svg 型別選擇器是**必要的**，不是手癢。
           「.dgabf [data-seg].sel .part」跟 diagrams.js 的「.dg [data-seg].sel .part」
           特異性一模一樣（都是 0,4,0），量出來 diagrams.js 那一條贏
           —— 實測 stroke-width 是 2.2 而不是 0。加一個型別選擇器變成 (0,4,1) 就穩定壓過去，
           不必去動 diagrams.js（那個檔這一輪有別人在改）。
           量法：點一個零件之後讀 getComputedStyle(rect.part).strokeWidth，
           _uitest.py 的「批次12-ABF載板」那一段就是在驗這個數字。*/
        svg.dgabf [data-seg] .part{stroke-width:0}
        svg.dgabf [data-seg].sel .part{stroke-width:0;filter:none}
        svg.dgabf [data-seg]:hover .part{stroke-width:1.4;filter:none}
        svg.dgabf [data-seg].sel-part .part{stroke-width:2.4;filter:drop-shadow(0 0 5px var(--c))}
        /* 壓暗那一階從 .3 放寬到 .55：這張圖進來的預設狀態是「族群 ic_substrate 被選起來」
           ＝ abf_pcb 亮、substrate_material 與 hdi_pcb 被壓暗，
           而**被壓暗的正好是 core 與 ABF 膜**，也就是這張圖的主角。
           .3 會讓「以 core 為中心、上下對稱長出增層」這句話在預設畫面上看不見。
           .55 仍然明顯比選到的那一組暗（篩選訊號還在），但結構讀得出來。*/
        svg.dgabf [data-seg].dim{opacity:.55}
      </style>
      <text class="ttl" x="16" y="26">IC 載板：晶片底下那塊板子，跟主機板不是同一種東西</text>
      <text class="cap" x="16" y="46">以中間那片 core 為中心、上下對稱長出 ABF 增層。上表面用 bump pad 接晶片，下表面用 BGA 錫球接主機板。右邊逐件說明，下面是三格放大、三條路線與製程。</text>

      <!-- ================= 主視圖：正剖面 ＋ 等角厚度 =================
           畫的順序＝由後往前：厚度面 → 增層 → core → 孔 → 線 → 防焊 → 墊子
           → 主機板 → 灰色剪影 → 凸塊 → 訊號。
           凸塊排在剪影後面，中介層的頂面才不會把微凸塊蓋掉。 -->
      ${gSlab()}
      ${gFilm()}${gCore()}${gCoreVia()}${gUvia()}${gStack()}${gTrace()}${gSr()}${gPad()}
      ${gMb()}${gGhost()}${gBumps()}${gSignal()}

      <!-- 晶片這一側的導引（不掛 data-seg，§0-B 二） -->
      <g pointer-events="none">
        <path d="M170,88 L215,80" stroke="var(--dg-mute)" stroke-width="1" fill="none"/>
        <text class="lbl" x="24" y="84" style="fill:var(--dg-mute)">晶粒／中介層（灰色剪影）</text>
        <text class="sub" x="24" y="102">晶片這一側不是這張圖的主題，</text>
        <text class="sub" x="24" y="120">細節請看半導體鏈的</text>
        <text class="sub" x="24" y="138">「CoWoS 2.5D 封裝剖面」</text>
      </g>

      <text class="sub" x="22" y="492">最底下那一條才是「PCB」（只畫一小段），走線明顯比上面的載板粗。</text>
      <text class="sub" x="22" y="510">三種凸塊由小到大：微凸塊（晶片↔中介層）→ C4（↔載板）→ BGA 錫球（↔主機板）。</text>
      <text class="sub" x="22" y="528">載板的工作就是把最細的那一端轉接到最粗的那一端；真實比例見〔A〕。</text>
      <text class="cap" x="22" y="546">青色虛線＝訊號路徑：BGA → core 貫孔 → 微孔 → bump pad（可用「動畫」鈕停）。</text>

      <!-- ================= 右欄：說明列（引線拉到外側文字框，文字不壓在零件上） ================= -->
      ${ROWS.map((o, i) => lrow({ seg: o.seg, part: o.part, y: o.y, ax: o.ax, ay: o.ay, t: o.t, subs: o.subs, i: i })).join('')}

      <!-- ================= 左下結論 ================= -->
      <rect class="frame" x="16" y="560" width="484" height="136" rx="8"/>
      <text class="hd" x="30" y="584">為什麼載板比主機板貴</text>
      <text class="sub" x="30" y="606">① 線細一個量級：走半加成（SAP／mSAP），一層一層長出來</text>
      <text class="sub" x="30" y="624">② 層數是「循環」出來的：每多一層就多一次貼膜、雷射、除膠渣、</text>
      <text class="sub" x="30" y="642">　 電鍍、蝕刻，而整片的良率是每一層的連乘</text>
      <text class="sub" x="30" y="660">③ 關鍵材料幾乎只有一家（ABF 增層膜），材料漲價直接進成本</text>
      <text class="sub" x="30" y="678">④ 越做越大就越難：尺寸一大，翹曲、平坦度、電鍍均勻度同時變嚴</text>

      <!-- ================= 三格放大 ================= -->
      ${panelA(16, 710, 306)}${panelB(338, 710, 306)}${panelC(660, 710, 306)}

      <!-- ================= 路線圖 ＋ 右下結論 ================= -->
      ${roadmap(16, 938, 584)}
      <rect class="frame" x="616" y="938" width="350" height="136" rx="8"/>
      <text class="hd" x="630" y="962">AI 為什麼把載板推到極限</text>
      <text class="sub" x="630" y="986">① 晶片變大、要接的線變多 → 載板跟著變大、層數變多</text>
      <text class="sub" x="630" y="1004">② 大板子在迴焊高溫下翹得更兇（樹脂與矽差太多）</text>
      <text class="sub" x="630" y="1022">③ 所以才有人提無核心（路徑短）與玻璃核心（更硬）</text>
      <text class="sub" x="630" y="1040">④ 這兩條路都要換設備、重新認證，不是換個材料就好</text>

      <!-- ================= 製程列（五格）＝ §3-C =================
           P1 增層在防焊之前、P2 第三格裡有除膠渣、P3 材料商與載板廠之間有分界線、
           P4 第三格標明上下同時進行。 -->
      <text class="cap" x="16" y="1096">製造流程（五格）　★ 增層循環一定在防焊與表面處理之前；雷射開孔之後、鍍銅之前一定有「除膠渣」那一步</text>
      <path d="M202,1100 V1162" stroke="var(--dg-warn)" stroke-dasharray="5 4" fill="none" opacity=".85" style="stroke-width:var(--dg-hair-w,2)"/>
      ${D.processBar(16, 1104, steps, 180)}
      <text class="sub" x="16" y="1178" style="fill:var(--dg-warn)">← 材料商（外商）</text>
      <text class="sub" x="208" y="1178">載板廠（台股：3037 欣興／8046 南電／3189 景碩）→</text>
      <text class="cap" x="16" y="1198">③ 的完整一圈：貼 ABF 膜 → 雷射開微孔 → 除膠渣（desmear）→ 化學鍍薄銅 → 圖案電鍍（SAP／mSAP）→ 蝕刻，上下兩面同時做、重複 N 次。</text>

      <!-- ================= 台股掛零那一格：畫面上一定要解釋，不要讓人以為點壞了 ================= -->
      <text class="sub" x="16" y="1222" style="fill:var(--dg-warn)">★「載板材料 ABF / BT」這一格台股掛零：ABF 膜是味之素、BT 樹脂 core 是三菱瓦斯化學，兩家都是外商。</text>
      <text class="sub" x="16" y="1240" style="fill:var(--dg-warn)">　 點 core、ABF 膜、〔B〕或路線圖，再點下面同色的環節色標，成分股會是 0 筆 —— 那不是壞掉，是這一格真的沒有台股。</text>

      <text class="cap" x="16" y="1258">示意圖，非實物比例｜層數與各層厚度均為示意；載板線寬、CTE、封裝尺寸、供需與價格一律不寫數字（來源對不起來，見規格書 §7-B／§7-C）。</text>
      <text class="cap" x="16" y="1276">圖上畫 core ＋ 上下各 3 層增層，實際為十幾至二十幾層（這句話本身也是示意，不是規格）。</text>
      <text class="cap" x="16" y="1294">點零件篩到的是「環節」不是整個族群：「IC 載板（ABF / BT）」這一格目前收錄 3037 欣興／8046 南電／3189 景碩三家。</text>
    </svg>`;
  }

  window.DG.register('ic_substrate', {
    level: 'group', chain: 'ai_server',
    name: 'IC 載板：ABF 增層剖面',
    draw: abfSubstrate, native: 980, scene: null,
    q: 'AI 晶片底下那塊板子為什麼比主機板貴？ABF 膜、細線、微孔各卡在哪一關，台股站在哪幾家？',
    /* ★ 2026-09-21：`parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       這張圖是 R4（台股沒有人做的零件要明說）最典型的案例：**核心層與 ABF 膜這兩層台股一家都沒有**，
       而那正是整條鏈的卡點 —— 留白會讓人以為「這裡漏了」或「這裡不重要」，兩個都是錯的判斷。
       `cos` 只放代號，「這家在這裡負責什麼」一律讀 supply_chain.json 的 companies[].tech（R3）。
       `items` 只填 supply_chain 的 edges[].item 真的有的字串，小卡會自己把 confidence 接上去；
       沒寫 items 的零件走預設（該環節流進／流出的全部品項）。*/
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
    },
  });
})();
