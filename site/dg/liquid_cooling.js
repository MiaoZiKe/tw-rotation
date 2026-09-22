/* 液冷：冷板 ＋ 均熱板 VC ＋ 熱管 —— docs/diagram_plan.md 的第 5 張
   （族群 `liquid_cooling`、ai_server 鏈）。規格書：docs/diagram_specs/liquid_cooling.md

   ★ 型式：2.5D 等角切開（冷板外形）＋ 2D 剖面（層別、VC／熱管內部、冷板流道）＋ 2D 迴路示意。
     **不做真 3D**（規格書 §0 已寫死，`scene: null`）：冷板流道、毛細層、蒸氣腔
     全部「只存在於剖面」，轉一圈看到的都是一塊實心銅盒 —— 轉不出新資訊。

   ★ 為什麼「層別」用平面剖面、而不是畫在等角切面上（規格書 §9 只是提醒，不是規格）：
     等角切面上，一條等高的層會沿著 x 往右下漂 0.5×長度。冷板長 310、層厚才 8～36，
     漂移量是層厚的好幾倍 —— 五層疊起來會變成五條互相錯開的斜帶，**層序反而讀不出來**。
     第一版就是那樣，實際畫出來看才發現。所以改成：
       · **層序（§6-H1～H3、H6）用平面剖面**表達 —— 它本來就是一維的上下關係；
       · **外形（進出水口在上面、底面是平的、內部有鰭）用等角切開**表達 —— 那才是等角的強項。
     §6 的每一條硬規則（層序、TIM 比相鄰金屬薄、冷板在蓋板之上、鰭 ≥8 條）都還是驗得到。

   ★ 名詞陷阱（規格書 §7-B1，本圖最容易被內行人抓到的錯）：
       **均熱片／蓋板（IHS／lid）＝ 實心銅**，內部沒有腔體；
       **均熱板／均溫板（vapor chamber, VC）＝ 真空腔 ＋ 毛細結構**。
     兩者不是同一個東西。所以：
       1. 畫面上一律**雙標**，沒有任何一處只寫「均熱片」三個字就指向 VC（§6-N6）；
       2. ③ 那一排把「實心 IHS」與「空腔 VC」**並排對照**，那一格就是這條的解藥（§6-P2）。

   ★ 與 `air_cooling.js` 是一對，兩張圖不准互相矛盾：
       · 「液冷帶走多少比例的熱」兩張用**同一個字串常數** `SHARE_LINES`（規格書 §7-B3 ＝ air §7-B2）
       · `heatpipe` / `vc` 兩個 data-part 的字串兩張**刻意相同**（規格書 §7-D2）
       · 冷＝進、暖＝出／排 的顏色語意兩張相同（`--dg-cold` / `--dg-hot`）

   ★ 畫面上不准出現的數字（規格書 §6-N1／N4、§7-B2／B4、§7-C）：
       良率、成本、市占率、VC 相對熱管的性能提升百分比、
       GB200 冷板的流量／功率、液冷滲透率（那一個走 YAML 的 source/confidence）。*/
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || !DG.register) return;
  const { STYLE, labelRow, processBar, P3 } = DG;

  const SEG = 'thermal';        // 散熱（均熱片 / 液冷）—— ai_server 鏈，YAML 裡查證過存在
  const SEG_A = 'assembly';     // 系統組裝 / 機櫃 —— 只有機櫃襯景掛它

  /* ★ 兩張圖共用的那一句（規格書 liquid §7-B3 ＝ air §7-B2）。
     兩個來源一個說「冷板移除 70–80%，其餘由風扇處理」、一個說「液冷約做 80%」，
     而且**分母可能不同**（一個是伺服器、一個是機房）。所以寫區間 ＋ 標明分母不一致，
     **不挑一個當定論**。`air_cooling.js` 裡有一份一字不差的複本 —— 改一邊要改另一邊。
     兩行都掛 `data-share`，`scripts/_uitest.py` 的「批次12-散熱」那一段會把兩張圖
     這幾個元素的文字接起來做**字串比對**，不一致就紅（同一個網站不准自打嘴巴）。*/
  const SHARE_LINES = ['多數熱由冷板帶走（公開資料約在 7～8 成之間，', '各來源分母不同），其餘仍靠氣流'];
  const shareText = (x, y) => SHARE_LINES.map((s, i) =>
    `<text class="sub" data-share="1" x="${x}" y="${y + i * 18}">${s}</text>`).join('');

  /* 這一組色票與 `air_cooling.js` 的完全相同 —— 兩張圖的冷／暖語意必須一致（規格書 §8）。
     ⚠ `--dg-*` 的家本來在 `site/index.html` 的 :root（art-director 擁有），
       但這一批**不准動 index.html**（同時有別人在畫別的圖），所以先定義在圖自己的
       scoped style 裡：**色值只出現在這一個區塊**，底下所有形狀一律 `var(--dg-*)`。
       之後 art-director 要收進 :root，把這一段整塊搬過去即可，形狀一行都不用改。
     ⚠ `--dg-hot` 刻意**不用紅色** —— `--dg-err`（#ff4d6d）已經是「錯誤／裂紋」，
       撞色的話「出水側」會被讀成「這裡壞了」（規格書 §8）。*/
  /* 這張圖的材質色 token 已經在 2026-09-21 深夜收進 `site/index.html` 的 :root（art-director 擁有）。
     收進去的理由：配色切換（html 的 data-dgpal）在 :root 那一層蓋不掉圖自己 scope 裡的變數，
     不收就等於「休閒配色只有一張圖有效」。**是同值搬家，值一個都沒改。**
     這裡只留下這張圖自己的**規則**（class 定義），那些不是 token，不該進 :root。*/
  const VARS = `<style>
    .dgcool .fine{font-size:var(--dg-fs-min,12px);fill:var(--dg-ink-3,#8ea0c4)}
  </style>`;

  // 零件外框：每一個零件都要有 data-part（規格書 §7-D2：沒有身分就「點誰都一樣」）
  const P = (part, inner, seg) => `<g data-seg="${seg || SEG}" data-part="${part}">${inner}</g>`;
  /* 說明列沿用共用的 labelRow（行距／底框已由 art-director 調過，不要自己造第二套），
     只多補一個 data-part —— 讓「說明列」與「它指的那個零件」共用同一個身分：
     點零件時那一列跟著變主角，點那一列時零件也跟著亮。*/
  const row = (part, ...a) => labelRow(...a).replace('<g class="lrow"', `<g class="lrow" data-part="${part}"`);

  /* 流程列補 data-part：規格書 §7-D2 要求每一個 [data-seg] 都要有身分，
     否則 `stampParts` 會自動補「環節 id ＋ 文件順序」，圖上零件一換順序就對不起來。
     共用的 `DG.processBar` 不吃 data-part（它是既有共用函式，這一批不准動 diagrams.js），
     所以在呼叫端把 key 注進去 —— 跟上面 `row()` 同一個做法：
     **沿用共用函式產出的幾何，只多綁一個身分**。*/
  const pbar = (x, y, steps, w) => {
    let i = 0;
    return processBar(x, y, steps, w)
      .replace(/<g data-seg="/g, () => `<g data-part="flow${i++}" data-seg="`);
  };


  function liquidCooling() {
    // ================================================================ ② 冷板外形：2.5D 等角切開
    /* **半切（half cut-away）：把 y > YC 的那一半整個拿掉**，只留一個切面。
       第一版切的是「近角」（x > XC 且 y > YC），但冷板是扁的、切角之後剩下的兩個切面
       各只有四十幾寬，鰭排不下、缺口反而被讀成「這塊零件本來就是 L 形」——
       實際畫出來看才發現。半切只有一個切面、而且它跟冷板一樣長，鰭排得下、形狀也乾淨。
       冷板本來就是扁的，所以這裡的比例接近實物：長 > 寬 >> 高。等角只負責三件事 ——
       進出水口在上面、底面是平的（要貼晶片）、內部不是實心而是密排的鰭。*/
    const L = 124, W = 52, HH = 54;
    const CX = 140, CY = 272;
    const isoFace = (pts, fill, cls) => `<path class="${cls || ''}" fill="${fill}" d="M${pts.join('L')}Z"/>`;
    // 切面（y = W 的 x–z 面，u 就是 x）：底板 → 鰭與冷卻液 → 上蓋
    const isoCut = (() => {
      const a = [];
      for (let i = 0; i < 8; i++) a.push(`<rect x="${7 + i * 15}" y="16" width="6" height="22" fill="var(--dg-cu)"/>`);
      return DG.onXZ(0, W)
        + `<rect x="0" y="0" width="${L}" height="${HH}" fill="var(--dg-void)"/>`
        + `<rect x="0" y="16" width="${L}" height="22" fill="url(#lcFlow)"/>`
        + a.join('')
        + `<rect x="0" y="0" width="${L}" height="16" fill="var(--dg-cu)"/>`
        + `<rect x="0" y="38" width="${L}" height="16" fill="var(--dg-cu)"/></g>`;
    })();
    // 等角圓柱（進出水口）。DG.cyl 的顏色綁環節色，這裡要的是冷／暖語意，所以自己給 fill
    const tube = (x, y, z, r, h, top, side) => {
      const cx = (x - y) * 0.866, cy = (x + y) * 0.5 - (z + h), by = (x + y) * 0.5 - z;
      const rx = r * 1.2247, ry = r * 0.7071;
      return `<path class="part" fill="${side}" d="M${(cx - rx).toFixed(1)},${cy.toFixed(1)} V${by.toFixed(1)} A${rx.toFixed(1)},${ry.toFixed(1)} 0 0 0 ${(cx + rx).toFixed(1)},${by.toFixed(1)} V${cy.toFixed(1)}Z"/>`
        + `<ellipse class="part" fill="${top}" cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" rx="${rx.toFixed(1)}" ry="${ry.toFixed(1)}"/>`;
    };
    const iso = `<g transform="translate(${CX},${CY})">
      ${isoFace([P3(0, 0, HH), P3(L, 0, HH), P3(L, W, HH), P3(0, W, HH)], 'url(#lcLid)', 'part')}
      ${isoFace([P3(L, 0, HH), P3(L, W, HH), P3(L, W, 0), P3(L, 0, 0)], 'var(--dg-cu)', 'part')}
      ${isoCut}
      ${tube(26, 24, HH, 10, 26, 'var(--dg-cold)', 'var(--dg-cold-2)')}
      ${tube(98, 24, HH, 10, 26, 'var(--dg-hot)', 'var(--dg-hot-2)')}
    </g>`;

    // ================================================================ ① 冷板剖面：層別（2D）
    const SX0 = 290, SX1 = 600;                     // 冷板剖面的左右界
    const LYR = [                                   // [y0, y1, x0, x1, 顏色, part]
      [214, 242, SX0, SX1, 'var(--dg-cu)', 'cold_plate'],        // 冷板上蓋
      [312, 340, SX0, SX1, 'var(--dg-cu)', 'cold_plate'],        // 冷板底板（貼晶片那一面是平的）
      [340, 348, 320, 570, 'var(--dg-tim)', 'tim2'],             // TIM2（極薄）
      [348, 384, 330, 560, 'var(--dg-cu)', 'ihs'],               // 均熱片／蓋板（實心銅）
      [384, 392, 360, 530, 'var(--dg-tim)', 'tim1'],             // TIM1（極薄）
      [392, 422, 370, 520, 'var(--dg-die)', 'die'],              // 裸晶 die
    ];
    const slab = ([y0, y1, x0, x1, f]) => `<rect class="part" x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}" rx="2" fill="${f}"/>`;
    /* 流道：一個 for 迴圈排等距薄鰭（§6-H4 要求 ≥8 條，這裡 16 條）。
       鰭與鰭之間是冷卻液 —— 底下先鋪一層「冷→熱」的水平漸層再把銅鰭疊上去，
       所以「進水冷、出水熱」是從**流道本身**讀出來的，不是只靠兩個箭頭。*/
    const fins = [];
    for (let i = 0; i < 16; i++) fins.push(`<rect x="${300 + i * 19}" y="242" width="8" height="70" fill="var(--dg-cu)"/>`);
    const cavity = `<rect x="${SX0}" y="242" width="${SX1 - SX0}" height="70" fill="url(#lcFlow)"/>` + fins.join('');
    // 進出水口（剖面上就是兩根立管；冷色＝進、暖色＝出，§6-H5）
    const port = (x, col, col2) => `<rect class="part" x="${x - 13}" y="180" width="26" height="36" rx="3" fill="${col2}"/>`
      + `<rect x="${x - 9}" y="184" width="18" height="30" rx="2" fill="${col}"/>`;
    const heatUp = [400, 445, 490].map((x, i) =>
      `<path class="flow slow" d="M${x},390V316" stroke="var(--dg-hot)" stroke-width="2.2" fill="none" style="animation-delay:${(i * 0.4).toFixed(1)}s"/>`).join('');

    // ================================================================ ③ 迴路：兩個封閉環
    const CP_X = 150, CP_W = 116, CP_H = 34;
    const CPY = [592, 642, 692, 742];
    const MS_X = 104, MR_X = 300;                   // 供水分歧管／回水分歧管（垂直主幹）
    const CDU = { x: 388, y: 570, w: 244, h: 214 };
    /* 快接頭 QD：對插的兩半、端面是平的（§6-M1）。一定成對出現（一進一出，§6-L2）。*/
    const qd = (x, y, col) =>
      `<rect x="${x - 13}" y="${y - 8}" width="12" height="16" rx="2" fill="var(--dg-steel)"/>`
      + `<rect x="${x + 1}" y="${y - 8}" width="12" height="16" rx="2" fill="var(--dg-steel-2)"/>`
      + `<path d="M${x},${y - 8}V${y + 8}" stroke="var(--dg-void)" stroke-width="1.6"/>`
      + `<path d="M${x - 13},${y}H${x - 20}M${x + 13},${y}H${x + 20}" stroke="${col}" stroke-width="4" stroke-linecap="round"/>`;
    // 並聯支路：每一個冷板各自接到供水與回水分歧管（§6-L3，串聯＝不過）
    const branches = CPY.map((y, i) => {
      const cy = y + CP_H / 2;
      return `<path class="flow" d="M${MS_X},${cy}H${CP_X}" stroke="var(--dg-cold)" stroke-width="3.4" fill="none"/>`
        + `<path class="flow" d="M${CP_X + CP_W},${cy}H${MR_X}" stroke="var(--dg-hot)" stroke-width="3.4" fill="none"/>`
        + `<rect class="part" x="${CP_X}" y="${y}" width="${CP_W}" height="${CP_H}" rx="4" fill="var(--dg-cu)"/>`
        + `<rect x="${CP_X + 6}" y="${y + 6}" width="${CP_W - 12}" height="${CP_H - 12}" rx="2" fill="url(#lcFlow)"/>`
        + [0, 1, 2, 3, 4, 5, 6, 7].map(k => `<rect x="${CP_X + 8 + k * 13}" y="${y + 6}" width="5" height="${CP_H - 12}" fill="var(--dg-cu)"/>`).join('')
        + `<text class="fine" x="${CP_X + CP_W / 2}" y="${cy + 4}" text-anchor="middle" style="fill:var(--dg-ink)">冷板 ${i + 1}</text>`
        + qd(CP_X - 26, cy, 'var(--dg-cold)') + qd(CP_X + CP_W + 26, cy, 'var(--dg-hot)');
    }).join('');
    /* 板式熱交換器（PHE）：一疊交錯薄板，**兩側顏色由 i % 2 決定** —— 這一行就是 §6-L5。
       中間那條隔板是「兩邊的水不相通」在畫面上的樣子（§6-L4，相接＝直接退回）。*/
    const PHE = { x: CDU.x + 128, y: CDU.y + 46, w: 92, h: 104 };
    const phe = (() => {
      const n = 11, t = PHE.h / n, a = [];
      for (let i = 0; i < n; i++) a.push(`<rect x="${PHE.x}" y="${(PHE.y + i * t).toFixed(1)}" width="${PHE.w}" height="${(t - 1.2).toFixed(1)}" fill="${i % 2 ? 'var(--dg-fws)' : 'var(--dg-hot)'}" opacity=".85"/>`);
      return a.join('') + `<rect class="part" x="${PHE.x}" y="${PHE.y}" width="${PHE.w}" height="${PHE.h}" rx="3" fill="none"/>`
        + `<path d="M${PHE.x + PHE.w / 2},${PHE.y}V${PHE.y + PHE.h}" stroke="var(--dg-sn)" stroke-width="2.4"/>`;
    })();
    // 泵：畫在二次側（CDU 內），不是一次側（§6-L6）
    const PUMP = { x: CDU.x + 58, y: CDU.y + 98 };
    /* ⚠ `diagrams.js` 的 `.dg .spin` 已經設了 `transform-box:fill-box; transform-origin:center`，
       所以這裡**不准再寫 `transform-origin: <x>px <y>px`** —— 在 fill-box 座標系裡那個像素值
       是相對於元素自己的邊界框、不是 SVG 使用者座標，寫下去葉輪會飛出畫面。
       改成靠 `center`，再補一個透明同心圓把邊界框撐成正圓，中心才精準落在軸上。*/
    const pump = `<circle class="part" cx="${PUMP.x}" cy="${PUMP.y}" r="24" fill="var(--dg-frame)"/>`
      + `<g class="spin" style="animation-duration:2.4s">`
      + `<circle cx="${PUMP.x}" cy="${PUMP.y}" r="17" fill="none"/>`
      + [0, 1, 2, 3, 4].map(i => `<path d="M${PUMP.x},${PUMP.y} L${(PUMP.x + 17 * Math.cos(i * 1.2566 - 0.5)).toFixed(1)},${(PUMP.y + 17 * Math.sin(i * 1.2566 - 0.5)).toFixed(1)} L${(PUMP.x + 17 * Math.cos(i * 1.2566 + 0.2)).toFixed(1)},${(PUMP.y + 17 * Math.sin(i * 1.2566 + 0.2)).toFixed(1)}Z" fill="var(--dg-cold)"/>`).join('')
      + `</g>`;
    // 二次側封閉環：泵 → 供水分歧管 → 冷板 → 回水分歧管 → PHE → 回到泵（§6-L1）
    const SEC_OUT = `M${CDU.x},${CDU.y + CDU.h - 28}H62V566H${MS_X}V${CPY[0] + CP_H / 2}`;
    const SEC_IN = `M${MR_X},${CPY[3] + CP_H / 2}V${CDU.y + 30}H${CDU.x}`;
    /* 一次側（設施側 FWS）：**比二次側粗**、用第三種顏色，而且**不接到二次側**（§6-L8／L4）。
       它只在板式熱交換器處「靠在一起」—— 畫面上是兩色薄板交錯，中間一條隔板。*/
    const BND = 690;
    const primary = `<path class="flow slow" d="M900,${CDU.y + 62}H${CDU.x + CDU.w}" stroke="var(--dg-fws)" stroke-width="7" fill="none"/>`
      + `<path class="flow slow rev" d="M${CDU.x + CDU.w},${CDU.y + 154}H900" stroke="var(--dg-fws-2)" stroke-width="7" fill="none"/>`;

    // ================================================================ ④ 兩相元件剖面（四格）
    const CELL = [16, 256, 496, 736], CW = 228, CY0 = 908, CH = 206;
    const cellFrame = (i, t) => `<rect class="frame" x="${CELL[i]}" y="${CY0}" width="${CW}" height="${CH}" rx="8"/>`
      + `<text class="hd" x="${CELL[i] + 14}" y="${CY0 + 24}">${t}</text>`;
    const cellText = (i, lines) => lines.map((s, k) =>
      `<text class="fine" x="${CELL[i] + 16}" y="${CY0 + 150 + k * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join('');

    /* 格 ① 均熱片／蓋板（IHS，**實心銅**）—— 斜線填滿代表「裡面是實心的」。
       ★ 這一格與格 ② 並排，就是名詞陷阱唯一的畫面解藥（§6-P2）。*/
    const ihsCell = P('ihs_cmp', cellFrame(0, '① 均熱片／蓋板（IHS，實心銅）')
      + `<rect class="part" x="${CELL[0] + 24}" y="${CY0 + 62}" width="${CW - 48}" height="40" rx="3" fill="url(#lcSolid)"/>`
      + `<rect x="${CELL[0] + 78}" y="${CY0 + 102}" width="72" height="12" rx="2" fill="var(--dg-tim)"/>`
      + `<rect x="${CELL[0] + 88}" y="${CY0 + 114}" width="52" height="18" rx="2" fill="var(--dg-die)"/>`
      + cellText(0, ['內部沒有腔體，熱靠銅的傳導擴散', '★ 這一片才叫「均熱片」', '裸晶 → TIM1 → 實心銅蓋板']));

    /* 格 ② 均熱板 VC（vapor chamber，**真空腔**）：下蓋板 → 毛細層 → 蒸氣腔 → 支撐柱 → 上蓋板。
       硬規則：液體在毛細層、蒸氣在中央空腔、**兩者箭頭反向**（§6-P3）；
       腔體**不准畫滿液體**（§6-P4）；**VC 有支撐柱、熱管沒有**（§6-P5）。*/
    const vcCell = (() => {
      const x = CELL[1] + 18, w = CW - 36, y = CY0 + 56;
      const posts = [];
      for (let i = 0; i < 6; i++) posts.push(`<rect x="${(x + 20 + i * 27).toFixed(1)}" y="${y + 16}" width="6" height="24" rx="1" fill="var(--dg-cu)" opacity=".85"/>`);
      return P('vc', cellFrame(1, '② 均熱板 VC（vapor chamber）')
        + `<rect class="part" x="${x}" y="${y}" width="${w}" height="10" rx="2" fill="var(--dg-cu)"/>`
        + `<rect x="${x}" y="${y + 10}" width="${w}" height="6" fill="url(#lcWick)"/>`
        + `<rect x="${x}" y="${y + 16}" width="${w}" height="24" fill="var(--dg-vap)"/>${posts.join('')}`
        + `<rect x="${x}" y="${y + 40}" width="${w}" height="6" fill="url(#lcWick)"/>`
        + `<rect class="part" x="${x}" y="${y + 46}" width="${w}" height="10" rx="2" fill="var(--dg-cu)"/>`
        + `<path class="flow" d="M${x + 22},${y + 28}H${x + w - 22}" stroke="var(--dg-hot)" stroke-width="2.4" fill="none"/>`
        + `<path d="M${x + w - 28},${y + 24}l8,4l-8,4Z" fill="var(--dg-hot)"/>`
        + `<path class="flow rev" d="M${x + w - 22},${y + 43}H${x + 22}" stroke="var(--dg-cold)" stroke-width="2.4" fill="none"/>`
        + `<path d="M${x + 28},${y + 39}l-8,4l8,4Z" fill="var(--dg-cold)"/>`
        + `<rect x="${x + 72}" y="${y + 56}" width="52" height="14" rx="2" fill="var(--dg-die)"/>`
        + cellText(1, ['真空腔 ＋ 少量工作流體 ＋ 毛細層', '→ 蒸氣往冷端、← 液體在毛細層回流', '★ 有支撐柱撐住真空，不被壓扁']));
    })();

    /* 格 ③ 熱管剖面：管壁 → 毛細層 → 中央蒸氣通道。**沒有支撐柱**（圓管靠管壁自己撐）。*/
    const hpCell = (() => {
      const x = CELL[2] + 18, w = CW - 36, y = CY0 + 62;
      return P('heatpipe', cellFrame(2, '③ 熱管（heat pipe）剖面')
        + `<rect class="part" x="${x}" y="${y}" width="${w}" height="52" rx="26" fill="var(--dg-cu)"/>`
        + `<rect x="${x + 10}" y="${y + 8}" width="${w - 20}" height="36" rx="18" fill="url(#lcWick)"/>`
        + `<rect x="${x + 16}" y="${y + 15}" width="${w - 32}" height="22" rx="11" fill="var(--dg-vap)"/>`
        + `<path class="flow" d="M${x + 30},${y + 26}H${x + w - 36}" stroke="var(--dg-hot)" stroke-width="2.4" fill="none"/>`
        + `<path d="M${x + w - 42},${y + 22}l8,4l-8,4Z" fill="var(--dg-hot)"/>`
        + `<path class="flow rev" d="M${x + w - 30},${y + 41}H${x + 36}" stroke="var(--dg-cold)" stroke-width="2.4" fill="none"/>`
        + `<path d="M${x + 42},${y + 37}l-8,4l8,4Z" fill="var(--dg-cold)"/>`
        + cellText(2, ['管壁 → 毛細層（液體）→ 中央蒸氣通道', '一端蒸發、另一端凝結，液體靠毛細力回流', '★ 圓管不用支撐柱 —— 有柱子就畫錯了']));
    })();

    // 格 ④ 熱擴散維度：一個是線、一個是面（§6-P8）
    const dimCell = (() => {
      const x = CELL[3] + 18, y = CY0 + 56;
      const rings = [0, 1, 2].map(i => `<ellipse cx="${x + 146}" cy="${y + 34}" rx="${16 + i * 15}" ry="${8 + i * 7}" fill="none" stroke="var(--dg-hot)" stroke-width="1.8" opacity="${(0.85 - i * 0.22).toFixed(2)}"/>`).join('');
      return P('dim_cmp', cellFrame(3, '④ 一個是線、一個是面')
        + `<rect x="${x}" y="${y + 26}" width="72" height="16" rx="8" fill="var(--dg-cu)"/>`
        + `<path class="flow" d="M${x + 8},${y + 34}H${x + 64}" stroke="var(--dg-hot)" stroke-width="2.6" fill="none"/>`
        + `<circle cx="${x + 8}" cy="${y + 34}" r="5" fill="var(--dg-hot)"/>`
        + `<text class="fine" x="${x}" y="${y + 62}">熱管：搬到遠處</text>`
        + `<ellipse cx="${x + 146}" cy="${y + 34}" rx="56" ry="28" fill="var(--dg-cu)" opacity=".5"/>${rings}`
        + `<circle cx="${x + 146}" cy="${y + 34}" r="5" fill="var(--dg-hot)"/>`
        + `<text class="fine" x="${x + 104}" y="${y + 62}">VC：就地攤平</text>`
        + cellText(3, ['AI 晶片的熱是「高熱通量的點」，', '所以要先攤平，再交給下一關帶走。', '同樣厚度下 VC 攤平能力較好']));
    })();

    // ================================================================ ⑤ 兩組對照小圖
    const EY = 1136;
    const mini = (x, w, t, a, b, sa, sb, drawA, drawB, part) => P(part,
      `<rect class="frame" x="${x}" y="${EY}" width="${w}" height="152" rx="8"/>`
      + `<text class="hd" x="${x + 14}" y="${EY + 24}">${t}</text>`
      + `<path d="M${x + w / 2},${EY + 34}V${EY + 142}" stroke="rgba(120,150,210,.24)" stroke-width="1" stroke-dasharray="4 4"/>`
      + `<text class="lbl" x="${x + 14}" y="${EY + 52}">${a}</text>`
      + `<text class="lbl" x="${x + w / 2 + 14}" y="${EY + 52}">${b}</text>${drawA}${drawB}`
      + `<text class="fine" x="${x + 14}" y="${EY + 128}">${sa}</text>`
      + `<text class="fine" x="${x + w / 2 + 14}" y="${EY + 128}">${sb}</text>`);
    const phaseA = [0, 1, 2, 3].map(i => `<rect x="${34 + i * 26}" y="${EY + 76}" width="18" height="14" rx="3" fill="var(--dg-cold)"/>`).join('');
    const phaseB = [0, 1, 2, 3].map(i => `<rect x="${182 + i * 26}" y="${EY + 76}" width="18" height="14" rx="3" fill="${i < 2 ? 'var(--dg-cold)' : 'var(--dg-hot)'}" opacity="${i < 2 ? 1 : .6}"/>`).join('')
      + [0, 1, 2].map(i => `<circle class="pulse" cx="${238 + i * 18}" cy="${EY + 66}" r="4" fill="var(--dg-hot)" style="animation-delay:${i * 0.3}s"/>`).join('');
    const dtcA = `<rect x="330" y="${EY + 86}" width="104" height="10" rx="2" fill="var(--dg-pcb)"/>`
      + `<rect x="352" y="${EY + 68}" width="40" height="18" rx="2" fill="var(--dg-cu)"/>`
      + `<rect x="358" y="${EY + 86}" width="28" height="6" fill="var(--dg-die)"/>`
      + [0, 1, 2].map(i => `<path class="flow" d="M${400 + i * 12},${EY + 100}v-10" stroke="var(--dg-cold)" stroke-width="1.6" fill="none"/>`).join('');
    const dtcB = `<rect x="478" y="${EY + 62}" width="108" height="42" rx="4" fill="var(--dg-vap)" opacity=".85"/>`
      + `<rect x="492" y="${EY + 86}" width="80" height="10" rx="2" fill="var(--dg-pcb)"/>`
      + [0, 1, 2, 3].map(i => `<rect x="${498 + i * 19}" y="${EY + 76}" width="12" height="10" rx="1" fill="var(--dg-die)"/>`).join('')
      + [0, 1, 2, 3, 4].map(i => `<circle class="drop ${i % 3 === 1 ? 'd2' : i % 3 === 2 ? 'd3' : ''}" cx="${490 + i * 23}" cy="${EY + 68}" r="3" fill="var(--dg-cold)"/>`).join('');

    // ================================================================ 說明框
    const noteBox = (x, y, w, h, t, lines, part, extra) => P(part,
      `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="8"/>`
      + `<text class="hd" x="${x + 14}" y="${y + 24}">${t}</text>`
      + lines.map((s, i) => `<text class="sub" x="${x + 14}" y="${y + 48 + i * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join('')
      + (extra || ''));

    /* ================================================================ 組裝
       class 多一個 `dg1`：`stampParts` 只在「整張圖只有一個 data-seg」時自動掛它，
       這張圖有兩個（thermal ＋ assembly），所以要**自己掛**。理由是發光量 ——
       `dg1` 的作用就是 `--dg-glow:none`。全圖三十幾個零件裡只有機櫃襯景掛 assembly，
       其餘全是 thermal；不關掉的話，點任何一個零件都會讓三十幾個群組**同時**
       drop-shadow，那正是 Andy 講的「螢光感太重、像電競 RGB」。
       關掉之後層次改由 `.sel-part` 的描邊寬（--dg-part-w 3.6）與
       `--dg-sib-o`（同環節其餘退到 .4）表達，主角／同環節其餘／別的環節三層
       仍然一眼分得開 —— 驗收量的就是這三層的 computed style 真的不同。*/
    return `<svg class="dg dgm dgcool dg1" viewBox="0 0 980 1668" width="100%" style="display:block">${STYLE}${VARS}
      <defs>
        <linearGradient id="lcFlow" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="var(--dg-cold)"/><stop offset="1" stop-color="var(--dg-hot)"/></linearGradient>
        <linearGradient id="lcLid" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="var(--dg-cu-lit)"/><stop offset="1" stop-color="var(--dg-cu-dim)"/></linearGradient>
        <pattern id="lcSolid" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill="var(--dg-cu)"/><path d="M0,0V8" stroke="var(--dg-cu-cut)" stroke-width="2"/></pattern>
        <pattern id="lcWick" width="6" height="6" patternUnits="userSpaceOnUse">
          <rect width="6" height="6" fill="var(--dg-wick)"/>
          <circle cx="1.6" cy="1.6" r="1.1" fill="var(--dg-void)" opacity=".75"/>
          <circle cx="4.6" cy="4.4" r="1.1" fill="var(--dg-void)" opacity=".75"/></pattern>
      </defs>

      <text class="ttl" x="16" y="26">液冷：熱從晶片走到機房外面，中間經過哪幾關</text>
      <text class="cap" x="16" y="46">熱是接力跑的 —— 晶片 → TIM → 蓋板／VC → 冷板 → 快接頭 → 分歧管 → CDU → 設施側。任何一棒掉了，前面做再好都沒用。</text>
      <text class="cap" x="16" y="64">左邊是冷板的外形，中間是它切開之後的層別，右邊逐關說明；再下面是迴路、兩相元件剖面與對照。</text>

      <!-- ========== ①② 主圖 ========== -->
      <text class="hd" x="40" y="130">② 冷板外形（等角切開）</text>
      ${P('cold_plate_iso', iso)}
      <text class="fine" x="40" y="396">進出水口在上面、底面是平的（要貼晶片），</text>
      <text class="fine" x="40" y="414">內部不是實心，是一排密排的細鰭。</text>

      <text class="hd" x="290" y="130">① 切開之後：熱由下往上，一關一關過</text>
      ${P('cp_port', port(330, 'var(--dg-cold)', 'var(--dg-cold-2)') + port(560, 'var(--dg-hot)', 'var(--dg-hot-2)')
      + `<path class="flow fast" d="M330,150V176" stroke="var(--dg-cold)" stroke-width="2.6" fill="none"/><path d="M325,170l5,9l5,-9Z" fill="var(--dg-cold)"/>`
      + `<path class="flow fast rev" d="M560,176V150" stroke="var(--dg-hot)" stroke-width="2.6" fill="none"/><path d="M555,158l5,-9l5,9Z" fill="var(--dg-hot)"/>`
      + `<text class="fine" x="296" y="166" style="fill:var(--dg-cold)">進水（冷）</text>`
      + `<text class="fine" x="576" y="166" style="fill:var(--dg-hot)">出水（熱）</text>`)}
      ${P('cp_fin', cavity + heatUp)}
      ${LYR.map(l => P(l[5], slab(l))).join('')}
      <path d="M${SX0},242H${SX1}" stroke="var(--dg-sn)" stroke-width="1.4" stroke-dasharray="6 5" fill="none" opacity=".7"/>
      <text class="fine" x="290" y="462">TIM 畫得比上下任何金屬層都薄 —— 它實際上也確實最薄，但每一層都非過不可。</text>

      ${row('cp_port', SEG, 648, 150, '進水冷、出水熱', '溫差就是被帶走的熱；溫差要小，流量就得大', 573, 197, 300)}
      ${row('cold_plate', SEG, 648, 204, '冷板（cold plate）', '直接貼在晶片上 —— 所以叫「直接晶片液冷 DTC」', 600, 228, 300)}
      ${row('cp_fin', SEG, 648, 258, '流道：微流道／削切鰭片／柱狀鰭', '鰭越密、接觸面積越大；代價是壓損變大、泵要更用力', 600, 277, 300)}
      ${row('tim2', SEG, 648, 312, '導熱介面材料（TIM1／TIM2）', '兩個固體之間一定有微觀空隙，TIM 把它填掉', 570, 344, 300)}
      ${row('ihs', SEG, 648, 366, '均熱片／蓋板（IHS，實心銅）', '把點熱源先攤開一點，再交給上面那一關', 560, 366, 300)}
      ${row('die', SEG, 648, 420, '裸晶 die（襯景，不是主角）', '熱從這裡出發；上面每一關只是把它往外送一棒', 520, 407, 300)}


      ${DG.fold('lc3', '③ 二次側與一次側：兩個封閉環只交換熱、不交換液體', '機櫃側與機房側的完整迴路、快接頭、分歧管、CDU 與熱交換器各在哪', `
      <!-- ========== ③ 迴路 ========== -->
      <text class="hd" x="16" y="500">③ 迴路：機櫃側（二次側）與機房側（一次側）是兩個封閉環，只交換熱、不交換液體</text>
      <text class="cap" x="16" y="520">冷板是並聯的 —— 串聯的話後面的晶片會吃到前面加熱過的水。每一個可拆的接點都有一對快接頭。</text>
      ${P('rack', `<rect class="part" x="60" y="560" width="288" height="228" rx="10" fill="none" opacity=".55"/>`
      + `<text class="fine" x="200" y="804" style="fill:var(--dg-ink-3)">機櫃／運算托盤（襯景）</text>`, SEG_A)}
      ${P('manifold', `<path class="part flow" d="${SEC_OUT}" stroke="var(--dg-cold)" stroke-width="6" fill="none" stroke-linejoin="round"/>`
      + `<path class="part flow rev" d="${SEC_IN}" stroke="var(--dg-hot)" stroke-width="6" fill="none" stroke-linejoin="round"/>`
      + `<rect class="part" x="${MS_X - 7}" y="${CPY[0] - 18}" width="14" height="${CPY[3] + CP_H + 18 - CPY[0] + 18}" rx="6" fill="var(--dg-cold-2)"/>`
      + `<rect class="part" x="${MR_X - 7}" y="${CPY[0] - 18}" width="14" height="${CPY[3] + CP_H + 18 - CPY[0] + 18}" rx="6" fill="var(--dg-hot-2)"/>`
      + `<text class="fine" x="70" y="552" style="fill:var(--dg-cold)">供水分歧管</text>`
      + `<text class="fine" x="256" y="552" style="fill:var(--dg-hot)">回水分歧管</text>`)}
      ${P('cp_rack', branches)}
      ${P('qd', qd(CP_X - 26, CPY[0] + CP_H / 2, 'var(--dg-cold)'))}
      ${P('cdu', `<rect class="part" x="${CDU.x}" y="${CDU.y}" width="${CDU.w}" height="${CDU.h}" rx="10" fill="var(--dg-frame)"/>`
      + `<text class="lbl" x="${CDU.x + 14}" y="${CDU.y + 24}">CDU 冷卻液分配單元</text>` + pump
      + `<text class="fine" x="${PUMP.x - 26}" y="${PUMP.y + 42}">泵（在二次側）</text>`
      + `<text class="fine" x="${CDU.x + 14}" y="${CDU.y + CDU.h - 14}">泵 ＋ 板式熱交換器 ＋ 過濾 ＋ 控制，四個口</text>`)}
      ${P('phe', phe + `<text class="fine" x="${PHE.x - 4}" y="${PHE.y - 8}">板式熱交換器</text>`
      + `<text class="fine" x="${PHE.x - 4}" y="${PHE.y + PHE.h + 16}" style="fill:var(--dg-sn)">中間這條＝隔板</text>`)}
      ${primary}
      <path d="M${BND},534V790" stroke="var(--dg-mute)" stroke-width="2" stroke-dasharray="7 6" fill="none"/>
      <text class="fine" x="${BND + 10}" y="552" style="fill:var(--dg-mute)">這條線的右邊是機房基礎設施，不在這條</text>
      <text class="fine" x="${BND + 10}" y="570" style="fill:var(--dg-mute)">產業鏈上（所以不掛環節、不列台股）</text>
      <text class="fine" x="${BND + 10}" y="${CDU.y + 56}" style="fill:var(--dg-fws)">一次側（設施水 FWS）進</text>
      <text class="fine" x="${BND + 10}" y="${CDU.y + 148}" style="fill:var(--dg-fws)">一次側出 → 冷卻水塔／冰水主機</text>
      <text class="fine" x="${BND + 10}" y="${CDU.y + 192}">一次側的管比二次側粗、用第三種顏色，</text>
      <text class="fine" x="${BND + 10}" y="${CDU.y + 210}">而且和二次側沒有任何一處相接。</text>
      <!-- 動畫：一顆冷卻液粒子沿著供水主幹跑（零件本身不准跑來跑去） -->
      <circle r="4.5" fill="var(--dg-cold)" opacity=".95">
        <animateMotion dur="4.5s" repeatCount="indefinite" path="M${MS_X},566V${CPY[3] + CP_H / 2}"/></circle>

      ${row('qd', SEG, 16, 826, '快接頭 QD（UQD／盲插 UQDB）', '可帶壓拔插、拔開不滴液 —— 最怕漏水的就是這裡', null, null, 300)}
      ${row('manifold', SEG, 340, 826, '分歧管（manifold）', '一根主幹 ＋ 多個等距分支，是並聯不是串聯', null, null, 300)}
      ${row('phe', SEG, 664, 826, '兩邊的水不相通', '二次側 TCS 與一次側 FWS 只交換熱、不交換液體', null, null, 300)}
      `)}

      ${DG.fold('lc4', '④ 均熱片與均熱板 VC 是兩種東西｜⑤ 三種散熱做法對照', '實心銅蓋與真空腔 VC 的剖面差別、三種做法的對照小圖與結論框', `
      <!-- ========== ④ 兩相元件剖面 ========== -->
      <text class="hd" x="16" y="888">④ 「均熱片」與「均熱板 VC」是兩種東西 —— 一個實心、一個是真空腔</text>
      ${ihsCell}${vcCell}${hpCell}${dimCell}

      <!-- ========== ⑤ 對照小圖 ＋ 結論框 ========== -->
      ${mini(16, 288, '單相 vs 兩相（冷板裡有沒有沸騰）', '單相', '兩相', '全程是液體，靠溫升', '在冷板裡沸騰，靠潛熱', phaseA, phaseB, 'phase_cmp')}
      ${mini(316, 288, 'DTC vs 浸沒式（另一種做法）', 'DTC 冷板', '浸沒式', '冷板貼最熱的那幾顆', '整片板泡進不導電液', dtcA, dtcB, 'dtc_cmp')}
      ${noteBox(616, EY, 348, 152, '為什麼一定要走到液冷', [
        '晶片功耗一路往上，同樣的面積要散掉更多的熱。',
        '空氣的搬熱能力有上限：要多搬就要更大的風量與',
        '風壓，風扇的耗電與噪音等比例上去。',
      ], 'why_liquid', shareText(630, EY + 120))}
      `)}

      ${DG.fold('lc6', '⑥ 結論框｜⑦ 價值鏈流程列', '結論框、流程列（含格 4 與格 5 之間那條分界線），以及資料來源與免責', `
      <!-- ========== ⑥ 說明框 ========== -->
      ${noteBox(16, 1306, 472, 186, '這張圖上誰做哪一塊（寫「主體是」，不是「只做」）', [
        '冷板／分歧管／Sidecar／CDU → 散熱（thermal）環節。',
        '奇鋐 3017、雙鴻 3324 主體是系統層級（水冷板、Sidecar、CDU）；',
        '健策 3653、一詮 2486 主體是封裝層級（均熱片 lid／IHS、補強框）；',
        '高力 8996 是板式熱交換器與 CDM／CDU；富世達 6805 做快接頭 QD。',
        '★ 2026 年這幾家互相跨線，所以寫「主體是」而不是「只做」。',
        '★ 一次側（冷卻水塔、冰水主機）不在這條鏈上，不掛環節、不列台股。',
      ], 'who')}
      ${noteBox(504, 1306, 460, 186, '這張圖沒有回答的事', [
        '各家的市占率：查不到可查證的公開出處，一個百分比都不寫。',
        '良率與成本：查不到可引用的公開數字，不編。',
        'VC 相對熱管的性能提升幅度：兩個來源的比較對象根本不同，',
        '被摘要混在同一段裡，所以只寫定性、不寫百分比。',
        '冷板的流量／功率：來源是經銷商產品頁與部落格，不是原廠規格。',
        '兩相冷板何時放量：來源只說「目前導入少」，沒有可引用的時程。',
      ], 'unknown')}

      <!-- ========== ⑦ 流程列（格 4 與格 5 之間畫分界線） ========== -->
      <text class="cap" x="16" y="1518">熱交給誰、再交給誰（五格）　★ 接點（格 3）一定在 CDU（格 4）之前</text>
      ${pbar(16, 1526, [
      { seg: SEG, t: '晶片端', s: 'die → TIM1 → 蓋板／VC' },
      { seg: SEG, t: '冷板', s: 'TIM2 → 冷板 → 流道' },
      { seg: SEG, t: '接點', s: 'QD → 軟管 → 分歧管' },
      { seg: SEG, t: 'CDU', s: '泵 → 板式熱交換器 → 過濾' },
      { seg: SEG_A, t: '設施端', s: '一次側水 → 屋外散熱' }], 176)}
      <path d="M762,1514V1574" stroke="var(--dg-mute)" stroke-width="2" stroke-dasharray="6 5" fill="none"/>
      <text class="fine" x="586" y="1590" style="fill:var(--dg-mute)">左邊是這條產業鏈上的東西</text>
      <text class="fine" x="768" y="1590" style="fill:var(--dg-mute)">右邊是機房基礎設施</text>

      <text class="cap" x="16" y="1618">示意圖，非實物比例｜流道密度、毛細層厚度與管徑比例均為示意</text>
      <text class="cap" x="16" y="1636">圖上畫 4 個冷板代表一櫃數十個；分歧管分支數為示意。資料來源與信心度見 docs/diagram_specs/liquid_cooling.md</text>
      <text class="cap" x="16" y="1654" style="fill:var(--dg-warn)">點零件篩到的是「供應鏈環節」，不是整個族群；散熱這一格目前收錄六家</text>
      `)}
    </svg>`;
  }

  window.DG.register('liquid_cooling', {
    level: 'group', chain: 'ai_server',
    name: '液冷：冷板、均熱板 VC 與熱管',
    draw: liquidCooling, native: 980, scene: null,
    q: '熱從 GPU 晶片走到機房外面，中間經過哪幾關？冷板、快接頭、分歧管、CDU 各是誰做的？',
  });
})();
