/* HBM：堆疊起來的記憶體與底下那顆邏輯晶粒 —— docs/diagram_plan_semiconductor.md 的 S3
   （族群 `hbm`、semiconductor 鏈）

   合約＝`docs/diagram_specs/hbm_stack.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的幾件事（四條紅線全部在這裡）：

     · §0-A **不做真 3D**（`scene: null`）。TSV 是「一根貫穿的柱子」，只有剖面看得到；
       透視一進來，第一個被外層晶粒擋掉的就是它。而且 semiconductor 這條鏈**已經有一個
       3D 場景**在畫 CoWoS 封裝，再開一個就多一組 WebGL context 與 rAF 要管。
     · §3-A H1（紅線）**base die（邏輯晶粒）在整疊的最底下**。畫在中間或最上面＝直接退回。
     · §3-A H2（紅線）**TSV 貫穿 base die 與其上每一層 core die**。只畫在最上層、
       只畫在最下層、或只畫在某一層＝退回。實作上 TSV 用**一個 for 迴圈從 base die 底面
       一路畫到最頂那片的底面**，所以「漏掉某一層」在程式層面就不可能發生。
     · §3-C Y2（紅線）**HBM 與 GPU 並排站在中介層上，不是疊在 GPU 上面**。
       疊上去就是完全不同的封裝架構，而且會讓讀者以為 HBM 是 3D 疊在運算晶粒上。
     · §3-D T1（紅線）**2408 南亞科與 6239 力成不可以被畫在「HBM 顆粒」或「堆疊封裝」
       那兩段上**。依據是 repo 內 Andy 校訂過的 `supply_chain.yaml`：南亞科的 note 明寫
       「明確表示看淡 HBM、改押地端 AI 記憶體」；力成的 `tech` 明寫「記憶體封測（非 HBM 本體）」。
     · §0-B 交界：**不畫 CoWoS 的補強環／模封／載板層數**（那是既有的 CoWoS 剖面與先進封裝那張），
       **不畫打線／覆晶／導線架**（那是 S5），**不畫 DRAM 單元結構**（本圖沒有查證），
       **不畫 HBF／NAND 堆疊**（那是另一種東西）。
     · §7-C **一個良率、市占率、產能、單價、成本倍數都不寫**。特別點名：搜尋摘要裡那句
       「台積電做的 base die 成本是 core die 的 3～4 倍」**刻意不寫進畫面**。

   三個實作上的取捨，寫在這裡不要讓下一個人再想一次
   -----------------------------------------------
   1. **層數只有一個常數 `N_CORE`**，畫幾層與旁邊那行「本圖畫 N 層示意」是**同一個來源**。
      一個是畫的、一個是寫死的文字，改層數時兩邊一定會分叉。
   2. **微凸塊與 TSV 共用同一個 x 陣列 `COL`**，所以 H4（上下對齊）不是靠眼睛，是靠結構。
   3. **三種章用「形狀 ＋ 顏色 ＋ 文字」三重編碼**：四個配色下顏色會變、形狀與文字不會。
      ⚠ 規格書 §9 寫的是「紅＝三角、黃＝方、綠＝圓」，這裡把**綠換成青**（`--dg-accent-2d`）：
      台股的慣例是**紅漲綠跌**，在一張講「誰做得到、誰做不到」的圖上放一顆綠圓，
      第一眼會被讀成「跌」。紅（`--dg-err`）與黃（`--dg-warn`）保留 ——
      這兩個 token 在四個配色下都不被覆寫（語意色），正好符合「四個配色下都要分得出來」。

   顏色一律走既有的 `--dg-*`（沒有新增任何 token），JS 裡一個 #xxxxxx 都沒有。
   base die 與 core die 的色差是**這張圖唯一一個顏色本身帶語意**的地方：
   core die 走 `--dg-si`（藍），base die 走 `--dg-organic`（琥珀）——
   兩者色相差得夠遠，四個配色下都分得出來，而且**不是靠 var(--c) 的巧合**。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;

  /* ★ 2026-09-23（Andy：「所有族群 2D 圖呈現風格都需要 Follow AI Server 族群內 2D 圖，
     並且需要適當的調整及填充版面間隔，不許有空白」）
     -------------------------------------------------------------------------
     原本：980 寬的單張 SVG，說明文字、框線、台股標示帶全部畫在 SVG 裡，
           右半邊與框內留了大量空白，字被擠在 446 寬的框裡。
     現在：跟 `site/dg/server_psu.js`／`liquid_cooling.js`／`switch_wireless.js` 同一套
           （DECISIONS #238／#239 的 v2 風格）：
             · svg 根掛 `rs` → `diagrams.js` 的 `externalize()` 把說明卡片搬成 HTML（.dgc），
               排進畫布左右兩欄，欄寬由 index.html 的 .dgv2 容器查詢決定 —— 版面自己填滿，
               不再由這個檔寫死「右邊留 486px」。
             · 畫布收到 **660**（主角寬），`native` 跟著改。
             · 材質走共用介面 `D.fx`（`glowDefs`／`glass`／`beam`／`shadows`）。
             · 章節改用 `D.fold()`（範圍由 getBBox 量），不再手算 data-y0／data-y1。
             · 字級吃 `--dg-fs-min`（12px 基準）、卡片行距 16px —— 由共用 STYLE 給，這裡不寫第二套。
     互動一個都沒少：19 個 `data-part` 一個不改名、`data-seg` 照舊，
     卡片與畫布上的區塊共用同一個 data-part（點卡片亮區塊、點區塊亮卡片）。*/
  const CW = 660;

  /* 這張圖自己的樣式。**全部吃 --dg-* token，一個色碼都沒有。**
     ⚠ 要排在共用 STYLE 之後、特異性也要比它高（多一個 svg 型別選擇器），不然蓋不掉。
     2026-09-23：加這一段是因為 Andy 講過「螢光感太重」—— 這張圖預設就選著 hbm 族群，
     整疊十幾個零件一起 .sel 會同時發光。發光只留給**剛剛點的那一個**（.sel-part）。*/
  const VARS = `<style>
    svg.dg.dghb [data-seg].sel .part{filter:none;stroke-width:1.5}
    svg.dg.dghb [data-seg].sel-part .part{stroke-width:2.6;filter:var(--dg-glow,drop-shadow(0 0 6px var(--cc)))}
    /* 卡片的壓暗跟 SVG 同一階（.55）：預設 hbm 被選著，foundry／adv_pkg 那幾張卡 .3 連字都讀不到 */
    .dgwrap:has(svg.dg.dghb) .dgc.dim{opacity:.55}
  </style>`;

  /* ================================================================ 小工具 */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${+x.toFixed(1)}" y="${+y.toFixed(1)}" width="${+w.toFixed(1)}" height="${+h.toFixed(1)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const PA = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const LN = (d, col, w2, extra) =>
    `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  /* `seg` 可以不傳（GPU 與製程設備那兩件刻意不掛環節，見 §7-D1）。
     ⚠ 不可以傳 undefined 進 data-seg —— 那會變成字串 "undefined"，比沒掛更糟。*/
  const part = (id, inner, seg) => `<g data-part="${id}"${seg ? ` data-seg="${seg}"` : ''}>${inner}</g>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${+x.toFixed(1)}" y="${+y.toFixed(1)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  /* ⚠ class 名稱不可以用 `cap` / `sub` / `hd` / `lbl` / `tag` / `num` / `warn` ——
     那幾個在 `diagrams.js` 的共用 `STYLE` 裡是**文字樣式**而且都帶 `fill`，
     CSS 的 fill 會蓋掉 SVG 的 fill 呈現屬性，零件會被染成文字色。*/

  /* 元件色（卡片 data-dgcolor ＋ 編號圓點 ＋ 引線端點共用），**全部是 index.html 既有的 token**。
     base die 與 core die 的色差是這張圖唯一一個顏色本身帶語意的地方（檔頭最後一段）。*/
  const C = {
    si: 'var(--dg-si)', org: 'var(--dg-organic)', au: 'var(--dg-au)', ni: 'var(--dg-ni)',
    sn: 'var(--dg-sn)', uf: 'var(--dg-uf)', cu: 'var(--dg-cu-lit)', pcb: 'var(--dg-pcb)',
    die: 'var(--dg-die)', mute: 'var(--dg-mute)',
  };
  /* 說明卡片（v2）：卡片離開 SVG 變成 HTML，畫布上只留編號圓點。
     卡片跟它指的零件**共用同一個 data-part**，所以點哪一邊都是同一個身分。*/
  const card = (o) => {
    const s = extRow({ seg: o.seg, part: o.part, title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ================================================================ 區 A：HBM 堆疊剖面（主角）

     §3-A：頂層 core die 上面沒有東西了；中間是重複的 core die；**最底下是 base die**（H1）；
     TSV 一根根貫穿（H2）；每兩層之間一排微凸塊（H3）；TSV 與微凸塊上下對齊（H4）；
     base die 不同色而且比較厚（H5）；core die 至少 4 層（H6）。*/
  const N_CORE = 6;                 // ★ 畫幾層與卡片上那句「本圖畫 N 層示意」同一個來源
  const H_CORE = 20, H_BASE = Math.round(H_CORE * 1.4), H_GAP = 7;
  /* 2026-09-23：畫布從 980 收到 660，整疊跟著從 228 收到 196 寬（x 30～226）；
     右半邊讓給系統剖面，原本那一整排「右側短標籤 ＋ 引線」改成 HTML 卡片。*/
  const SX = 30, SW = 196, TOP = 80;
  const COL = [64, 98, 132, 166, 200];        // ★ TSV 與微凸塊共用這一組 x，H4 因此是結構性的

  function stackGeom() {
    const cores = [], gaps = [];
    let y = TOP;
    for (let i = 0; i < N_CORE; i++) {
      cores.push(y); y += H_CORE;
      gaps.push(y); y += H_GAP;                // 每一層 core die 底下都有一排微凸塊
    }
    const base = y;                            // ★ base die 在整疊最底下
    return { cores: cores, gaps: gaps, base: base, bottom: base + H_BASE };
  }

  function hbmStack() {
    const G = stackGeom(), g = [];
    // 層間填充（NCF／底填，示意）—— §7-B3 低信心，只畫一層半透明、不寫材料名稱
    g.push(part('hb_fill', G.gaps.map((y) =>
      `<g opacity=".4">${R(SX, y, SW, H_GAP, C.uf, 'part')}</g>`).join(''), 'hbm'));
    // core die：每一層同色同厚（H5 的反面保險）。2026-09-23 改走 fx.glass —— 玻璃板材質是 AI 伺服器那三張的基準
    g.push(part('hb_core', G.cores.map((y) =>
      fx.glass(SX, y, SW, H_CORE, { fill: C.si, cls: 'part cdie', rx: 2 })).join(''), 'hbm'));
    // ★ base die：不同色、而且比 core die 厚（H_BASE = H_CORE × 1.4）
    g.push(part('hb_base', fx.glass(SX, G.base, SW, H_BASE, { fill: C.org, cls: 'part bdie', rx: 2, t: 2 }), 'foundry'));
    /* ★★★ TSV（H2，紅線）：**一個迴圈**從 base die 底面一路畫到最頂那片的底面。
       手刻每一層的 TSV 一定會漏掉一層 —— 那就是 H2 不過。*/
    const tsvTop = G.cores[0] + H_CORE, tsvBot = G.bottom;
    g.push(part('hb_tsv', COL.map((x) =>
      `<rect class="part tsv" x="${x - 2.5}" y="${tsvTop}" width="5" height="${tsvBot - tsvTop}" fill="${C.au}"/>`).join(''), 'hbm'));
    // 微凸塊：夾在每兩層之間，x 用同一組 COL（H4 對齊）
    g.push(part('hb_ubump', G.gaps.map((y) => COL.map((x) =>
      R(x - 6, y, 12, H_GAP, C.ni, 'part ub', 2)).join('')).join(''), 'hbm'));
    // base die 底下那一排對外凸塊（接到中介層）
    g.push(part('hb_outbump', COL.map((x) =>
      `<circle class="part ob" cx="${x}" cy="${G.bottom + 7}" r="6" fill="${C.sn}"/>`).join(''), 'hbm'));
    // 頂層那一片：上面沒有東西再疊上去
    g.push(part('hb_top', LN(`M${SX},${TOP - 6} L${SX + SW},${TOP - 6}`, C.mute, 1.2, ' stroke-dasharray="4 4"'), 'hbm'));

    /* 動畫只做一件事（§9）：一個資料點沿著 TSV **由頂層往下跑到 base die**、再橫向跑出去。
       2026-09-23：那條路徑改用共用的 `fx.beam`（glow:false —— 發光預算留給被選到的零件，
       Andy 講過「螢光感太重」），流動虛線與光點照舊，按「動畫：關」時一起停。*/
    const flowD = `M${COL[2]},${tsvTop} V${G.bottom - 12} H${SX + SW + 10}`;
    g.push(fx.beam(flowD, { color: 'var(--dg-accent-2d)', w: 2, glow: false, flow: true }));
    g.push('<circle r="4" fill="var(--dg-accent-2d)" opacity=".92">'
      + `<animateMotion dur="5s" repeatCount="indefinite" path="${flowD}"/></circle>`);
    return g.join('');
  }

  /* ================================================================ 區 C：系統剖面（定位用，刻意畫簡單）
     §3-C Y1 由下到上 載板 → 中介層 → 晶粒；
     Y2（紅線）**HBM 與 GPU 都站在中介層上、左右並排**；
     Y3 俯視小格 GPU 在中間、HBM 在兩側；Y4 中介層裡畫得出細密繞線且連著 GPU 與 HBM；
     Y5 **不准畫補強環、模封、載板的內部層數**（那是別張圖的範圍）。
     2026-09-23：整組從 x 472～956 搬到 x 306～634（畫布收窄），尺寸等比帶過來。*/
  const SYS = { subL: 306, subR: 634, subT: 270, subB: 292, intL: 316, intR: 624, intT: 242, intB: 268, dieT: 182, dieB: 242 };
  const BLK = { h1: 342, h2: 530, bw: 66, gx: 434, gw: 70 };

  function system() {
    const S = SYS, g = [];
    g.push(part('hb_sub', fx.glass(S.subL, S.subT, S.subR - S.subL, S.subB - S.subT, { fill: C.pcb, cls: 'part', rx: 3, t: 2 }), 'adv_pkg'));
    // 中介層：裡面那些細密繞線就是它存在的理由（Y4）——「接住左邊的 HBM 也接住右邊的 HBM」
    const wires = [];
    for (let i = 0; i < 9; i++) {
      const y = S.intT + 5 + i * 2.2;
      wires.push(LN(`M${BLK.h1 + 40},${y} H${BLK.gx + 20}`, C.cu, 1, ' class="route"'));
      wires.push(LN(`M${BLK.gx + BLK.gw - 20},${y} H${BLK.h2 + 26}`, C.cu, 1, ' class="route"'));
    }
    g.push(part('hb_interposer', fx.glass(S.intL, S.intT, S.intR - S.intL, S.intB - S.intT, { fill: 'var(--dg-si-2)', cls: 'part', rx: 2 })
      + wires.join(''), 'adv_pkg'));
    // ★★ HBM 與 GPU **並排**站在中介層上（Y2）：同一個底面 dieB，x 互不重疊
    const hbmBlk = (x) => fx.glass(x, S.dieT, BLK.bw, S.dieB - S.dieT, { fill: C.si, cls: 'part hblk', rx: 2 })
      + [0, 1, 2, 3, 4].map((i) => LN(`M${x + 5},${S.dieT + 7 + i * 9} L${x + BLK.bw - 5},${S.dieT + 7 + i * 9}`, 'var(--dg-void)', 1.2)).join('')
      + R(x, S.dieB - 8, BLK.bw, 8, C.org, 'part hbase', 2);
    g.push(part('hb_hbm_pkg', hbmBlk(BLK.h1) + hbmBlk(BLK.h2), 'hbm'));
    g.push(part('hb_gpu', fx.glass(BLK.gx, S.dieT, BLK.gw, S.dieB - S.dieT, { fill: C.die, cls: 'part gblk', rx: 2 })
      + T(BLK.gx + BLK.gw / 2, S.dieT + 34, 'GPU', 'lbl', 'middle')));
    // 俯視小格（Y3）：GPU 在中間、HBM 在兩側，數量對稱
    const tv = 480;
    g.push(part('hb_topview', R(tv, 40, 136, 110, 'var(--dg-frame-f)', '', 6)
      + R(tv + 54, 58, 28, 74, C.die, 'part tvg', 2)
      + [0, 1].map((i) => R(tv + 12, 60 + i * 36, 26, 30, C.si, 'part tvh', 2)).join('')
      + [0, 1].map((i) => R(tv + 98, 60 + i * 36, 26, 30, C.si, 'part tvh', 2)).join('')
      + T(tv + 68, 166, '俯視：GPU 在中間、HBM 在兩側', 'cap', 'middle')));
    return g.join('');
  }

  /* ================================================================ 區 B：兩種層間接合放大格（章節 ②）
     §3-B B1 微凸塊那格**有一排凸塊**、混合鍵合那格**沒有凸塊**（兩格都畫凸塊＝這一區沒有存在意義）；
     B2 混合鍵合的兩層之間只有一條接合界線；B3 兩格的 die 同色同厚。
     2026-09-23：兩格從「直的上下排」改成「橫的左右並排」，660 寬剛好兩欄，下面不留空白。*/
  const BD = { w: 250, h: 26 };
  function bondPanel(x, y, withBumps) {
    const g = [];
    g.push(fx.glass(x, y, BD.w, BD.h, { fill: C.si, cls: 'part bdie2', rx: 2 }));
    if (withBumps) {
      g.push(`<g opacity=".4">${R(x, y + BD.h, BD.w, 14, C.uf, 'part')}</g>`);
      for (let i = 0; i < 10; i++) g.push(R(x + 14 + i * 24, y + BD.h, 13, 14, C.ni, 'part bump', 2));
      g.push(fx.glass(x, y + BD.h + 14, BD.w, BD.h, { fill: C.si, cls: 'part bdie2', rx: 2 }));
    } else {
      // 混合鍵合：銅對銅直接接合，兩層之間**只有一條界線**，沒有任何凸塊
      g.push(LN(`M${x},${y + BD.h} L${x + BD.w},${y + BD.h}`, 'var(--dg-cu)', 2.6, ' class="bondline"'));
      g.push(fx.glass(x, y + BD.h, BD.w, BD.h, { fill: C.si, cls: 'part bdie2', rx: 2 }));
    }
    return g.join('');
  }
  function areaB() {
    return `<g>
      ${T(16, 376, '兩層之間是怎麼接起來的 —— 差別就是「有沒有那一排凸塊」', 'hd')}
      ${part('hb_ubump_zoom', bondPanel(16, 400, true), 'hbm')}
      ${part('hb_hybrid', bondPanel(392, 400, false), 'hbm')}
      ${T(16, 490, '① 微凸塊（microbump）', 'lbl')}
      ${T(16, 510, '兩層之間有一排凸塊，凸塊周圍填著填充材。', 'sub')}
      ${T(16, 528, '這是目前多數世代的作法。', 'sub')}
      ${T(392, 490, '② 混合鍵合（hybrid bonding）', 'lbl')}
      ${T(392, 510, '沒有凸塊 —— 銅墊直接對銅熔接，只剩', 'sub')}
      ${T(392, 528, '一條接合界線；間距更小、整疊也更薄。', 'sub')}
      ${T(16, 556, '★ 混合鍵合是各家在 HBM4 世代的路線之一，各家做法不同（來源：產業媒體，2026）——', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 574, '　 本圖不列「某家用 A、某家用 B」的對照表。兩格的晶粒刻意同色同厚：只有接法不同。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 596, '本圖不畫 DRAM 單元結構（電容／字元線／位元線）—— 那一件本圖沒有查證。', 'cap')}</g>`;
  }

  /* ================================================================ 區 D：台股標示帶（★ 這張圖最重要的一段，章節 ③）

     §3-D T1（紅線）**南亞科與力成不可以出現在第 ① 段（HBM 顆粒）與第 ③ 段（堆疊封裝）**；
     T2（★★）第 ① 與第 ③ 段必須是紅章，而且**寫出實際上是誰做的**（只寫「台股沒有」＝留白）；
     T3 第 ② 段指名台積電並寫明是 base die／12 奈米／HBM4，**不准寫成「台積電做 HBM」**；
     T4 第 ⑤ 段標黃章（單一來源，信心中低）。

     三種章＝形狀 ＋ 顏色 ＋ 文字（見檔頭第 3 條）：
       none  紅三角 `--dg-err`     台股沒有廠商做
       weak  黃方塊 `--dg-warn`    有，但信心不足
       has   青圓形 `--dg-accent-2d` 台股有（刻意不用綠色：台股紅漲綠跌，綠圓會被讀成「跌」）
     2026-09-23：一列從 924 寬收到 628 寬，「是誰」從同一行挪到第二行（三行制），
     字級與行距一個都沒動（12px／16～18px）。*/
  const BAND = [
    {
      id: 'hb_band1', seg: 'hbm', mark: 'none', t: '① HBM 顆粒（core die）',
      who: '台股沒有廠商做。實際上是 SK hynix（韓）、Micron（美）、Samsung（韓）。',
      s: 'DRAM 晶粒本體。這一層台股是空的 —— 那正是這張圖要講的事，不是漏畫。',
    },
    {
      id: 'hb_band2', seg: 'foundry', mark: 'has', t: '② base die（邏輯晶粒）',
      who: '2330 台積電代工。',
      s: ['SK hynix 的 HBM4 base die 採台積電 12 奈米邏輯製程（來源：產業媒體，2026）。',
        '這是做那顆邏輯晶粒，不是做記憶體顆粒。'],
    },
    {
      id: 'hb_band3', seg: 'hbm', mark: 'none', t: '③ 堆疊與封裝',
      who: '由記憶體原廠自家做，台廠無直接供應商。',
      s: '把顆粒疊起來、接上 TSV。這句話出自供應鏈資料自己的註記。',
    },
    {
      id: 'hb_band4', seg: 'test_interface', mark: 'has', t: '④ 堆疊前的測試',
      who: '6223 旺矽（MEMS 探針卡）。',
      s: '進 CoWoS 之前要先把壞的挑出來，帶動高精度探針卡需求。',
    },
    {
      id: 'hb_band5', seg: '', mark: 'weak', t: '⑤ 製程設備',
      who: '2467 志聖（HBM 製程用烘烤設備）。',
      s: '⚠ 單一來源、投資媒體的概念股整理，信心中低；志聖不在供應鏈資料裡，所以小卡列不出它。',
    },
  ];
  const MARK = {
    none: { c: 'var(--dg-err)', t: '台股沒有' },
    weak: { c: 'var(--dg-warn)', t: '信心不足' },
    has: { c: 'var(--dg-accent-2d)', t: '台股有' },
  };
  function stamp(x, y, kind) {
    const m = MARK[kind];
    if (kind === 'none') return PA(`M${x},${y - 7} L${x + 8},${y + 6} L${x - 8},${y + 6}Z`, m.c, 'mk mk-none');
    if (kind === 'weak') return R(x - 7, y - 6, 14, 13, m.c, 'mk mk-weak', 2);
    return `<circle class="mk mk-has" cx="${x}" cy="${y}" r="7" fill="${m.c}"/>`;
  }
  const BAND_Y = 646, BAND_STEP = 90;   // 一列 82 高（三～四行）＋ 8 的列距
  function areaD() {
    const rows = BAND.map((o, i) => {
      const y = BAND_Y + i * BAND_STEP;
      /* ⚠ 底色那塊**刻意不掛 `part`**：`.dg [data-seg].sel .part` 會替它加一圈發光描邊，
         五條橫帶一起發光就是 Andy 講的「螢光感太重」。*/
      return part(o.id,
        R(16, y, 628, 82, 'var(--dg-step-f)', 'row', 7)
        + stamp(38, y + 22, o.mark)
        + T(52, y + 26, MARK[o.mark].t, 'cap', null, 'fill:' + MARK[o.mark].c)
        + T(120, y + 22, o.t, 'lbl')
        + T(120, y + 42, o.who, 'lbl', null, 'fill:' + MARK[o.mark].c)
        + (Array.isArray(o.s) ? o.s : [o.s]).map((t, j) => T(120, y + 62 + j * 16, t, 'sub')).join(''), o.seg || null);
    }).join('');
    return `<g>${T(16, 630, '台股在這條鏈上到底站在哪裡（★ 這張圖最重要的一段）', 'hd')}${rows}
      <rect class="frame" x="16" y="1122" width="628" height="100" rx="9"/>
      ${T(30, 1146, '同族群的另外兩檔，為什麼不畫在上面任何一段', 'hd')}
      ${T(30, 1168, '2408 南亞科在供應鏈資料裡屬 DRAM／NOR 環節，其註記明寫「明確表示看淡 HBM、改押地端 AI 記憶體」；', 'sub')}
      ${T(30, 1186, '　 它的「UWIO 客製化記憶體堆疊」與 HBM 的關係本圖未查證，所以圖上不把它畫在任何一段。', 'sub')}
      ${T(30, 1204, '6239 力成的 tech 欄明寫「記憶體封測（非 HBM 本體）」，所以第 ③ 段（堆疊與封裝）也不列它。', 'sub')}</g>`;
  }

  /* ================================================================ 整張圖 */
  function hbmStackFig() {
    const G = stackGeom();
    /* 版面（2026-09-23 v2）
       ------------------------------------------------------------------
       §1（永遠看得到的那一段，0～330）＝ 這張圖的兩個命題並排，左右各佔一半、中間不留空白：
         左 x 24～226：堆疊剖面（最底下那顆不是記憶體）
         右 x 300～644：系統剖面（HBM 站在 GPU 旁邊）＋ 右上角的俯視小格
       說明卡片十二張全部外掛成 HTML（`card()` 傳 side），左欄講那一疊、右欄講封裝裡的位置。
       兩種接合方式、台股標示帶收進兩個 `D.fold()` 章節，預設收合、按了打得開。

       ★ 「台股標示帶」是這張圖最重要的一段，收起來會不會把它藏掉？
         不會：**結論留在 .dghead 的說明與那張警語卡片上**（台股沒有 HBM 顆粒廠、
         唯一具名的是 base die 找台積電代工），逐段的章與名單才收進章節。*/
    return `<svg class="dg dgm rs dghb" viewBox="0 0 ${CW} 1260" width="100%" style="display:block">${D.STYLE}${VARS}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">HBM：堆疊起來的記憶體與底下那顆邏輯晶粒</text>
      <text class="cap ext" x="0" y="0">把多顆 DRAM 疊起來、用一根根穿透的孔（TSV）連成一整塊；最底下那顆不是記憶體，是找晶圓代工廠做的邏輯晶粒（base die）。右半邊是它被放進封裝之後的位置 —— HBM 與運算晶粒是左右並排站在中介層上，不是疊在 GPU 上面。★ 誰做的：台股沒有 HBM 顆粒廠（實際上是 SK hynix／Micron／Samsung）；唯一具名的位置是 base die —— SK hynix 的 HBM4 base die 採 2330 台積電 12 奈米邏輯製程（來源：產業媒體，2026）。兩層之間怎麼接、逐段的台股名單收在下面兩段。</text>

      <!-- ================= §1 兩個命題並排（永遠看得到） ================= -->
      ${T(24, 52, '① HBM 那一疊裡面是什麼', 'hd')}
      ${T(306, 52, '② HBM 被放在哪裡', 'hd')}
      ${T(306, 78, '★ HBM 站在 GPU 旁邊，不是', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(306, 96, '　 疊在 GPU 上面。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(306, 116, '由下到上：載板 → 中介層 →', 'sub')}
      ${T(306, 134, '晶粒；中介層裡那些細密繞線', 'sub')}
      ${T(306, 152, '就是它存在的理由。', 'sub')}
      <!-- 柔陰影：整疊與系統剖面各一塊影子，全部包成一個群組（一次 feGaussianBlur） -->
      ${fx.shadows([[SX, TOP, SW, G.bottom - TOP], [SYS.subL, SYS.subT, SYS.subR - SYS.subL, SYS.subB - SYS.subT],
      [SYS.intL, SYS.intT, SYS.intR - SYS.intL, SYS.intB - SYS.intT]]
      .map(([x, y, w, h]) => `<rect x="${x + 3}" y="${y + 6}" width="${w}" height="${h}" rx="4"/>`).join(''))}
      ${hbmStack()}
      ${system()}
      ${T(24, 300, '本圖畫 ' + N_CORE + ' 層 core die 示意（實際依世代而定）；', 'cap')}
      ${T(24, 318, (N_CORE + 1) + ' 層晶粒就有 ' + N_CORE + ' 排微凸塊，且與 TSV 上下對齊。', 'cap')}
      ${T(306, 314, '左右兩塊是 HBM、中間是運算晶粒 —— 三者一起站在中介層上。', 'cap')}

      <!-- ================= 說明卡片（HTML，左欄＝那一疊；右欄＝封裝裡的位置） ================= -->
      ${card({ seg: 'hbm', part: 'hb_core', no: 1, side: 'l', color: C.si, ax: 40, ay: G.cores[2] + 10, title: 'core die（DRAM 晶粒）', sub: ['一層一層疊上去的記憶體晶粒。本圖畫 ' + N_CORE + ' 層示意；實際層數依世代而定。'] })}
      ${card({ seg: 'foundry', part: 'hb_base', no: 2, side: 'l', color: C.org, ax: 40, ay: G.base + H_BASE / 2, title: 'base die（邏輯晶粒，在最底下）', sub: ['★ 最底下這顆不是記憶體，是邏輯晶粒：它負責對外的介面與控制。', '它比較厚、也不同色 —— 因為它掛的是「晶圓代工」環節，是代工廠做的。'] })}
      ${card({ seg: 'hbm', part: 'hb_tsv', no: 3, side: 'l', color: C.au, ax: COL[2], ay: G.cores[3], title: 'TSV 穿矽孔（一根根貫穿每一層）', sub: ['把上面的記憶體跟底下的邏輯晶粒接起來。只有最上面那一層可以不用 —— 但不可以只有最上層有。'] })}
      ${card({ seg: 'hbm', part: 'hb_ubump', no: 4, side: 'l', color: C.ni, ax: COL[1], ay: G.gaps[4] + 3, title: '微凸塊（夾在每兩層之間）', sub: [(N_CORE + 1) + ' 層晶粒就有 ' + N_CORE + ' 排；與 TSV 上下對齊成一條連續的導通柱 —— 對不齊就電氣上接不起來。'] })}
      ${card({ seg: 'hbm', part: 'hb_outbump', no: 5, side: 'l', color: C.sn, ax: COL[3], ay: G.bottom + 7, title: '對外凸塊（base die 底面）', sub: ['整疊 HBM 對外就是從這裡出去，接到中介層。'] })}
      ${card({ seg: 'hbm', part: 'hb_fill', no: 6, side: 'l', color: C.uf, ax: SX + 10, ay: G.gaps[0] + 3, title: '層間填充（示意）', sub: ['填在每兩層之間、微凸塊周圍。⚠ 這一件本圖沒有查證，只畫成一層半透明並標「示意」。'] })}
      ${card({ seg: 'hbm', part: 'hb_top', no: 7, side: 'l', color: C.mute, ax: SX + 10, ay: TOP - 6, title: '頂層 core die 的上表面', sub: ['上面沒有東西再疊上去了。頂層的 TSV 畫或不畫都可以 —— 它沒有東西要往上接。'] })}
      ${card({ seg: 'adv_pkg', part: 'hb_interposer', no: 8, side: 'r', color: C.cu, ax: SYS.intR - 6, ay: (SYS.intT + SYS.intB) / 2, title: '中介層（interposer）', sub: ['極密的金屬繞線 ＋ 垂直連接 ＋ 細間距微凸塊，把每一疊 HBM 接到運算晶粒的記憶體控制器。', '畫成一塊空白的板子就少了它存在的理由。'] })}
      ${card({ seg: 'adv_pkg', part: 'hb_sub', no: 9, side: 'r', color: C.pcb, ax: SYS.subR - 6, ay: (SYS.subT + SYS.subB) / 2, title: '載板（package substrate）', sub: ['整包封裝最底下那一層。本格不畫補強環、模封與載板的內部層數 —— 那是「CoWoS 2.5D 封裝剖面」與「IC 載板」那兩張的範圍。'] })}
      ${card({ seg: 'hbm', part: 'hb_hbm_pkg', no: 10, side: 'r', color: C.si, ax: BLK.h2 + BLK.bw - 6, ay: SYS.dieT + 20, title: 'HBM 堆疊（站在中介層上）', sub: ['★ HBM 是站在 GPU 旁邊，不是疊在 GPU 上面 —— 疊上去是完全不同的封裝架構。'] })}
      ${card({ part: 'hb_gpu', no: 11, side: 'r', color: C.die, ax: BLK.gx + BLK.gw - 6, ay: SYS.dieB - 14, title: '運算晶粒（GPU／ASIC）', sub: ['HBM 站在它旁邊。它本身是 IC 設計與晶圓代工的產物，見「晶圓代工」那張。'] })}
      ${card({ part: 'hb_topview', no: 12, side: 'r', color: C.mute, ax: 610, ay: 95, title: '俯視小格', sub: ['從上往下看：中央是運算晶粒，兩側各一排 HBM，數量對稱 —— 這一格就是把「並排」講死。'] })}
      ${note({ side: 'r', order: 0, warn: true, title: '★ 誰做的（結論）', lines: ['台股沒有 HBM 顆粒廠（實際上是 SK hynix／Micron／Samsung）；唯一具名的位置是 base die —— SK hynix 的 HBM4 base die 採 2330 台積電 12 奈米邏輯製程（來源：產業媒體，2026）。逐段的章與名單見下面第 ③ 段。'] })}
      ${note({ side: 'r', order: 98, title: '示意圖，非實物比例', lines: ['層厚、孔徑與凸塊尺寸均為誇張放大；堆疊層數為示意，實際層數依世代而定。', '本圖講「HBM 那一疊裡面是什麼」；HBM 被放進封裝的完整樣子見「IC 封裝剖析」那張。'] })}
      ${note({ side: 'l', order: 99, title: '為什麼點零件列出來的是外商', lines: ['供應鏈資料的「HBM」環節底下只有外商，所以點零件列出來的是外商，這是刻意的 —— 台股在那一層是空的，而那正是這張圖要講的事。'] })}

      <!-- ================= ② 兩層之間是怎麼接起來的（預設收合） ================= -->
      ${fold('hb2', '② 兩層之間是怎麼接起來的：微凸塊 vs 混合鍵合',
      '差別就是「有沒有那一排凸塊」；混合鍵合是銅對銅直接接，只剩一條界線', areaB())}

      <!-- ================= ③ 台股在這條鏈上到底站在哪裡（預設收合） ================= -->
      ${fold('hb3', '③ 台股在這條鏈上到底站在哪裡',
      '五段各是誰（兩段是紅章），以及南亞科與力成為什麼不畫在上面', areaD())}
    </svg>`;
  }

  window.DG.register('hbm', {
    level: 'group', chain: 'semiconductor',
    name: 'HBM：堆疊起來的記憶體與底下那顆邏輯晶粒',
    draw: hbmStackFig, native: CW, scene: 'hbm',   /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。檔頭 §0 原本寫「不做真 3D」，
                       那個判斷被推翻的理由寫在 site/three3d.js 的 SCENES.hbm 檔頭（一句話：這張圖最重要的那件事本來就是三維的）。2D 的 data-part 與 3D 的 part 是同一組，所以切過去還是選著同一個零件。*/
    q: 'HBM 為什麼要疊？TSV 跟微凸塊各做什麼？最底下那顆為什麼是邏輯晶粒、而且是台積電做的？台股在這條鏈上到底站在哪裡？',
    parts: {
      hb_core: {
        name: 'HBM 記憶體晶粒（core die）',
        desc: '一層一層疊上去的 DRAM 晶粒。本圖畫 6 層示意；實際層數依世代而定 —— 本次查不到可引用的層數說明，所以不寫 8-high／12-high 這種規格。',
        none: '★ 台股沒有廠商做 HBM 顆粒。實際上是 SK hynix（韓）、Micron（美）、Samsung（韓）。⚠ 小卡列出來的是外商，這是刻意的 —— 台股在這一層是空的，而那正是這張圖要講的事。',
      },
      hb_base: {
        name: 'base die（邏輯晶粒）',
        desc: '★ 最底下這顆不是記憶體，是邏輯晶粒（base die／buffer die）。它負責對外的介面與控制，上面的記憶體晶粒都透過 TSV 跟它交換資料與控制訊號。圖上它比 core die 厚、而且不同色。',
        cos: ['2330'],
        note: 'SK hynix 的 HBM4 base die 採台積電 12 奈米邏輯製程（來源：產業媒體，2026）。這是做那顆邏輯晶粒，不是做 HBM 顆粒 —— 不要寫成「台積電做 HBM」。cos 刻意只列 2330，走預設會把聯電與力積電一起列出來，那會變成錯誤宣稱。',
      },
      hb_tsv: {
        name: '穿矽孔（TSV）',
        desc: '一根根垂直貫穿每一層，把上面的記憶體跟底下的邏輯晶粒接起來；TSV 與層間的微凸塊電氣相連（來源：專利摘要）。只有最上面那一層可以不用 —— 但不可以只有最上層有，那把整個結構畫反了。',
        none: '這是記憶體原廠自家的製程，台股無直接供應商。TSV 的直徑、間距與每疊的數量查不到可引用的數字，所以圖上只畫關係、不標數字。',
      },
      hb_ubump: {
        name: '微凸塊（microbump）',
        desc: '夾在每兩層之間。N 層晶粒就有 N−1 排（本圖 7 層、6 排）。它跟 TSV 上下對齊成一條連續的導通柱 —— 對不齊就電氣上接不起來。',
        none: '同上，原廠自家製程，台股無直接供應商。三星在部分世代改用混合鍵合（銅對銅直接接，不用微凸塊）（來源：產業媒體，2026；各家做法不同）。',
      },
      hb_ubump_zoom: {
        name: '放大格 ①：微凸塊接合',
        desc: '兩層晶粒之間有一排凸塊，凸塊周圍填著填充材。跟混合鍵合的差別就是「有沒有那一排凸塊」。',
        none: '原廠自家製程，台股無直接供應商。',
      },
      hb_hybrid: {
        name: '放大格 ②：混合鍵合（hybrid bonding）',
        desc: '兩層之間沒有凸塊 —— 銅墊直接對銅熔接，只剩一條接合界線。間距可以做得更小、整疊也更薄。',
        note: '混合鍵合是各家在 HBM4 世代的路線之一，各家做法不同（來源：產業媒體，2026）。本圖不列「某家用 A、某家用 B」的對照表 —— 沒有一篇把三家的路線並列比較過。',
        none: '原廠自家製程，台股無直接供應商。',
      },
      hb_fill: {
        name: '層間填充（示意）',
        desc: '填在每兩層之間、微凸塊周圍。⚠ 這一件本圖沒有查證，只畫成一層半透明並標「示意」，不寫材料名稱、不寫製程名稱。',
      },
      hb_outbump: { name: '對外凸塊', desc: 'base die 底面的一排凸塊，接到中介層。整疊 HBM 對外就是從這裡出去。' },
      hb_top: { name: '頂層 core die 的上表面', desc: '上面沒有東西再疊上去了。頂層的 TSV 畫或不畫都可以 —— 它沒有東西要往上接。' },
      hb_interposer: {
        name: '中介層（interposer）',
        desc: '提供極密的金屬繞線、垂直連接與細間距微凸塊，把每一疊 HBM 接到運算晶粒的記憶體控制器。畫成一塊空白的板子就少了它存在的理由。',
        cos: ['2330', '3711'],
        note: '「先進封裝 CoWoS/SoIC」這一格在供應鏈資料裡一家公司都沒有（一家公司只能歸一個環節的 schema 限制），所以這裡直接指名 2330 台積電（CoWoS）與 3711 日月光投控（CoWoS 外溢）—— 依據是它們在供應鏈資料裡既有的 tech 欄位。',
      },
      hb_sub: {
        name: '載板（package substrate）',
        desc: '整包封裝最底下那一層。本格刻意畫得簡單：載板的內部層數、補強環與模封是「CoWoS 2.5D 封裝剖面」與「IC 載板」那兩張的範圍。',
        cos: ['2330', '3711'],
      },
      hb_hbm_pkg: {
        name: 'HBM 堆疊（站在中介層上）',
        desc: '★ HBM 是站在 GPU 旁邊，不是疊在 GPU 上面 —— 兩者一起放在中介層上。疊上去是完全不同的封裝架構。',
        none: '★ 堆疊與封裝由記憶體原廠自家做，台廠無直接供應商（這句話出自供應鏈資料自己的註記）。⚠ 6239 力成雖然在這個族群裡，但它的既有資料明寫「記憶體封測（非 HBM 本體）」，所以這個零件不列它。',
      },
      hb_gpu: {
        name: '運算晶粒（GPU／ASIC）',
        desc: 'HBM 是站在它旁邊，不是疊在它上面。它本身是 IC 設計與晶圓代工的產物，見「晶圓代工」那張。',
      },
      hb_topview: {
        name: '俯視小格',
        desc: '從上往下看：中央是運算晶粒，兩側各一排 HBM，數量對稱。這一格就是為了把「並排」這件事講死。',
      },
      hb_band1: {
        name: '① HBM 顆粒：台股沒有廠商做',
        desc: 'DRAM 晶粒本體。實際上是 SK hynix（韓）、Micron（美）、Samsung（韓）。這一段是紅章 —— 全綠就等於把這張圖最有價值的資訊藏起來了。',
        none: '★ 台股沒有 HBM 顆粒廠。實際上是 SK hynix、Micron、Samsung。',
      },
      hb_band2: {
        name: '② base die：台積電代工',
        desc: 'SK hynix 的 HBM4 base die 採台積電 12 奈米邏輯製程（來源：產業媒體，2026）。⚠ 這是做那顆邏輯晶粒，不是做記憶體顆粒。',
        cos: ['2330'],
        note: '下一代 HBM4E 的 logic die 製程各家說法不一（同一家媒體在不同時間點分別報導 3 奈米與交給另一家代工廠），所以畫面上只寫已量產世代的事實。',
      },
      hb_band3: {
        name: '③ 堆疊與封裝：台廠無直接供應商',
        desc: '把顆粒疊起來、接上 TSV，由記憶體原廠自家做。這句話出自供應鏈資料自己的註記。',
        none: '★ 台廠無直接供應商。⚠ 6239 力成的 tech 欄明寫「記憶體封測（非 HBM 本體）」，所以這一段不列它。',
      },
      hb_band4: {
        name: '④ 堆疊前的測試',
        desc: '進 CoWoS 封裝之前必須先把不良品挑出來，帶動高精度探針卡測試需求。',
        cos: ['6223'],
      },
      hb_band5: {
        name: '⑤ 製程設備',
        desc: '2467 志聖（HBM 製程用烘烤設備）。',
        none: '⚠ 單一來源、而且是投資媒體的概念股整理，信心中低；2467 志聖不在供應鏈資料裡，所以小卡列不出它。本圖不寫它供給誰、不寫占比。',
      },
    },
  });
})();
