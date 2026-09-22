/* 被動元件：電感·電阻·石英 —— docs/diagram_plan.md 的第 11 張
   （族群 `power_inductor`、electronics 鏈）

   合約＝`docs/diagram_specs/passive_rlc.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的五件事：

     · §0-A **不做真 3D**（`scene: null`）。三種零件的識別特徵全部在剖面裡，
       轉一圈只會看到三顆不透明的小方塊。要加 3D 就是改規格書、重新簽。
     · §0-B **佈局已經拍板**：上方一條共同舞台（板上情境帶）＋ 下方三欄等高等寬剖面。
       被否決的兩個排法是「三張獨立小圖並排」與「排成一條流程列」——
       後者**會暗示一個不存在的因果順序**（這三種零件之間沒有上下游關係），
       所以這個檔裡**三欄之間一條箭頭、一條流程線都沒有**（X3）。
     · §0-C 跟 MLCC 那張的分工：這張圖**不畫任何電容**、不重畫交錯指狀電極、
       不重畫板彎裂紋、不重新解釋端電極 Cu→Ni→Sn 的原理（只標「三層」並導過去）。
     · §7-D2 **只有電阻欄掛 `data-seg="passive_comp"`**。電感欄與石英欄的成分股
       （3357 臺慶科／3236 千如／6155 鈞寶／3042 晶技／2484 希華／3221 台嘉碩）
       **整份 supply_chain.yaml 一家都沒有**，掛上去等於在公開網站上宣稱
       「國巨那五家做電感」—— 跟「金像電被放進 ABF 載板」同一條錯。
     · §7-B／§7-C：查不到的東西一個數字都不編。畫面上**沒有任何百分比、單價、市占**，
       三種零件的 mm 尺寸一個都不寫（查不到可引用的通用尺寸表）。

   ⚠ 一個已知的限制，寫在這裡不要讓下一個人再查一次
   -------------------------------------------------
   `site/industry.js` 的 `wireDiagram()` 只對 **`[data-seg]`** 綁點擊，
   `renderPartCard()` 也在 `if (!seg)` 就直接把小卡藏起來。
   所以這張圖**只有電阻欄的八個零件點得下去、看得到「誰做的」小卡**；
   電感欄與石英欄按照 §7-D2 不掛 `data-seg`，於是點了沒有反應。
   下面的 `parts:` 仍然把這兩欄逐件寫齊（那是 `docs/diagram_purpose.md` §4 指定的位置），
   等 `industry.js` 支援「有 data-part、沒有 data-seg 也能開小卡」就會自己亮起來。
   在那之前，這兩欄的「誰做的」**改用畫面上的文字回答**（每欄底下兩行 ＋ 右下說明框），
   而不是留白 —— R4 要的是「說出來」，不是「點得到」。

   這個檔不碰 `site/diagrams.js`／`site/index.html`／`site/three3d.js`。
   共用工具一律走 `window.DG`；色值一律走 `--dg-*`，JS 裡一個 #xxxxxx 都沒有。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;   // diagrams.js 沒載到就安靜退出

  /* ================================================================ 版面常數

     三欄用同一組常數產生（§9：手刻三個框是最容易出現不等高的地方）——
     `COLX` 只決定左右，其餘每一個 y 都是「COLY ＋ 固定偏移」，
     所以 X1（三欄等高等寬，誤差 2px 內）在程式上就不可能不成立。*/
  const W = 980;
  const COLX = [16, 338, 660], COLW = 306, COLY = 292, COLH = 656;
  const DRAW_T = COLY + 30;            // 剖面區上緣 322
  const BUS = COLY + 236;              // 引線橫向匯流的第一條線 528（每列再錯開 3.5px）
  const ONE1 = COLY + 262, ONE2 = COLY + 280;      // 「一句話」兩行 554 / 572
  const ROW0 = COLY + 316, ROWP = 50;  // 標註列：608 起、間距 50、共 6 列
  const FOOT1 = COLY + 620, FOOT2 = COLY + 638;    // 每欄底下那兩行（族群說明）948 為欄底
  const SEG_R = 'passive_comp';        // ★ 整張圖唯一的 data-seg，只掛在電阻欄

  /* ================================================================ 小工具 */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const C = (cx, cy, r, fill, cls) =>
    `<circle${cls ? ` class="${cls}"` : ''} cx="${cx}" cy="${cy}" r="${r}" fill="${fill}"/>`;
  const P = (d, fill, cls, extra) =>
    `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"${extra || ''}/>`;
  const line = (d, col, w2, extra) =>
    `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  /* 零件外框。`seg` 有值才掛 data-seg —— 沒有 seg 的群組不會被 wireDiagram 綁點擊，
     那是刻意的（§7-D2），不是漏寫。*/
  const part = (id, seg, inner) =>
    `<g data-part="${id}"${seg ? ` data-seg="${seg}"` : ''}>${inner}</g>`;

  /* 焊點：兩個梯形的焊錫爬坡。三欄都用同一支，「三顆都是表面黏著件」這句話
     才有畫面上的證據（§4-A）。*/
  const solder = (x, y, w2, h) =>
    P(`M${x},${y} L${x + w2},${y} L${x + w2 - 4},${y + h} L${x + 4},${y + h}Z`, 'var(--dg-sn)');

  /* ================================================================ 共同舞台（S1）
     一小塊主板的 2.5D 微斜頂視。`bx`／`by` 把 (u, v) 兩個 0–1 的參數壓成畫面座標：
     u 往右、v 往畫面深處（右上）。零件就是一個頂面平行四邊形 ＋ 一個正面厚度。
     GPU 只准是一個輪廓（X6），所以它用 stroke 不用 fill。*/
  const bx = (u, v) => 70 + u * 672 + v * 76;
  const by = (u, v) => 246 - v * 130;
  function chip(u, v, du, dv, h, top, side) {
    const A = [bx(u, v), by(u, v) - h], B = [bx(u + du, v), by(u + du, v) - h];
    const Cc = [bx(u + du, v + dv), by(u + du, v + dv) - h], Dd = [bx(u, v + dv), by(u, v + dv) - h];
    return P(`M${A} L${B} L${Cc} L${Dd}Z`, top, 'part')
      + P(`M${A} L${B} L${B[0]},${B[1] + h} L${A[0]},${A[1] + h}Z`, side);
  }
  const outline = (u, v, du, dv, h) => {
    const A = [bx(u, v), by(u, v) - h], B = [bx(u + du, v), by(u + du, v) - h];
    const Cc = [bx(u + du, v + dv), by(u + du, v + dv) - h], Dd = [bx(u, v + dv), by(u, v + dv) - h];
    return line(`M${A} L${B} L${Cc} L${Dd}Z`, 'var(--dg-mute)', 1.4)
      + line(`M${A} L${A[0]},${A[1] + h} M${B} L${B[0]},${B[1] + h}`, 'var(--dg-mute)', 1.1);
  };

  function stage() {
    // 板子本體：前緣 (70,246)→(742,246)，後緣往右上推 76／130
    const board = `M${bx(0, 0)},${by(0, 0)} L${bx(1, 0)},${by(1, 0)} L${bx(1, 1)},${by(1, 1)} L${bx(0, 1)},${by(0, 1)}Z`;
    const edge = `M${bx(0, 0)},${by(0, 0)} L${bx(0, 0)},${by(0, 0) + 12} L${bx(1, 0)},${by(1, 0) + 12} L${bx(1, 0)},${by(1, 0)}Z`;
    // 一排電感（六顆）＝ 伺服器供電用的多相供電，一排電感就是那些相位（§7-B8 只保留這句定性說法）
    const inds = [];
    for (let i = 0; i < 6; i++) inds.push(chip(0.615 + i * 0.052, 0.34, 0.040, 0.20, 13, 'var(--dg-el)', 'var(--dg-emc)'));
    // 供電路徑（橘、粗）：左邊進來 → 檢流電阻 → 一排電感 → GPU；時脈（青、細）：晶振 → GPU
    const pwr = line(`M${bx(0.03, 0.16)},${by(0.03, 0.16)} L${bx(0.20, 0.16)},${by(0.20, 0.16)}`
      + ` L${bx(0.30, 0.30)},${by(0.30, 0.30)} L${bx(0.60, 0.42)},${by(0.60, 0.42)}`
      + ` L${bx(0.90, 0.42)},${by(0.90, 0.42)}`, 'var(--dg-sw-pwr)', 3.4);
    const clk = line(`M${bx(0.07, 0.80)},${by(0.07, 0.80)} L${bx(0.28, 0.80)},${by(0.28, 0.80)}`
      + ` L${bx(0.40, 0.66)},${by(0.40, 0.66)}`, 'var(--dg-sw-sig)', 1.6);
    return `<g data-part="stage_board">
      ${P(edge, 'var(--dg-pcb-2)')}${P(board, 'var(--dg-pcb)', 'part')}
      ${pwr}${clk}
      ${outline(0.30, 0.44, 0.22, 0.34, 20)}
      ${inds.join('')}
      ${chip(0.155, 0.10, 0.052, 0.14, 8, 'var(--dg-cer)', 'var(--dg-cer-cut)')}
      ${chip(0.045, 0.72, 0.070, 0.18, 11, 'var(--dg-steel)', 'var(--dg-steel-2)')}
    </g>`;
  }

  /* ================================================================ 引線：零件 → 外側文字框
     走法固定：**從零件水平往左出去 → 垂直落到那一列 → 進入圓點**。
     每一列的垂直段錯開 3.5px，六條線才不會疊成一條粗線。
     文字從 x+41 開始，垂直段落在 x+8 ～ x+25.5，所以**引線一次都沒有壓到字**。*/
  function crow(ci, j, o) {
    const x = COLX[ci], y = ROW0 + j * ROWP;
    const elbow = x + 8 + j * 3.5;
    const lead = o.ax != null
      ? `<path class="leader" d="M${o.ax},${o.ay} L${elbow},${o.ay} L${elbow},${y - 2} L${x + 26},${y - 2}"/>` : '';
    const seg = o.seg ? ` data-seg="${o.seg}"` : '';
    return `<g class="lrow"${o.id ? ` data-part="${o.id}"` : ''}${seg}>
      <rect class="bg" x="${x + 22}" y="${y - 15}" width="${COLW - 34}" height="48" rx="6"/>
      ${lead}<circle class="dot" cx="${x + 30}" cy="${y - 2}" r="4"/>
      <text class="lbl" x="${x + 41}" y="${y + 2}">${o.t}</text>
      <text class="sub" x="${x + 41}" y="${y + 18}">${o.s1 || ''}</text>
      <text class="sub" x="${x + 41}" y="${y + 34}">${o.s2 || ''}</text></g>`;
  }

  /* 一欄。剖面 → 一句話 → 六列標註 → 兩行族群說明，**三欄同一支函式**（X2 自動成立）。*/
  function col(ci, no, title, draw, one, rows, foot) {
    const x = COLX[ci];
    return `<g>
      <rect class="frame" x="${x}" y="${COLY}" width="${COLW}" height="${COLH}" rx="9"/>
      <text class="hd" x="${x + 14}" y="${COLY + 22}">${no}　${title}</text>
      ${draw}
      <text class="lbl" x="${x + 40}" y="${ONE1}">${one[0]}</text>
      <text class="lbl" x="${x + 40}" y="${ONE2}">${one[1]}</text>
      ${rows.map((r, j) => crow(ci, j, r)).join('')}
      <text class="sub" x="${x + 14}" y="${FOOT1}">${foot[0]}</text>
      <text class="sub" x="${x + 14}" y="${FOOT2}">${foot[1]}</text></g>`;
  }

  /* ================================================================ 欄 A：功率電感（一體成型／模壓）

     L1：**先畫本體、再畫繞組** —— 繞組落在本體內縮 30px／14px 的框裡，
     側面與頂面都沒有露出來（剖面切開才看得到裡面的圈數）。
     L3：扁平線的剖面是**橫躺的長方形**；對照件 A6 的圓線剖面是**圓形**。
     L5：磁通迴路完全走在本體之內（漏磁會跟「磁屏蔽」的說法矛盾）。*/
  const FLUX = 'M141,336 C101,336 80,352 80,372 C80,392 101,408 141,408 C181,408 202,392 202,372 C202,352 181,336 141,336Z';
  function drawA() {
    const turns = [];
    for (let i = 0; i < 4; i++) turns.push(R(96, 344 + i * 13, 90, 8, 'var(--dg-cu)', 'part', 1));
    const w6 = [[96, 481], [96, 495], [110, 488], [188, 481], [188, 495], [174, 488]]
      .map(p => C(p[0], p[1], 6.5, 'var(--dg-cu)', 'part')).join('');
    return `<g>
      ${part('ind_body', '', R(66, 330, 150, 84, 'var(--dg-el)', 'part', 3))}
      ${part('ind_wind', '', turns.join(''))}
      ${part('ind_flux', '',
    `<path class="leader flow" d="${FLUX}" stroke="var(--dg-accent-2d)" stroke-width="1.6" fill="none" opacity=".85"/>`
    + `<circle r="3.2" fill="var(--dg-accent-2d)"><animateMotion dur="4.2s" repeatCount="indefinite" path="${FLUX}"/></circle>`)}
      ${part('ind_term', '', R(62, 412, 38, 9, 'var(--dg-sn)', 'part', 1) + R(182, 412, 38, 9, 'var(--dg-sn)', 'part', 1))}
      <g pointer-events="none">${R(52, 421, 180, 9, 'var(--dg-pcb)')}
        ${solder(60, 414, 42, 8)}${solder(180, 414, 42, 8)}</g>
      ${part('ind_wirewound', '',
    R(72, 448, 140, 9, 'var(--dg-steel)', 'part', 1)
    + R(72, 462, 140, 11, 'var(--dg-emc)', 'part', 1)
    + R(122, 473, 40, 30, 'var(--dg-emc)', 'part')
    + R(72, 503, 140, 11, 'var(--dg-emc)', 'part', 1) + w6)}
      <g pointer-events="none">${R(60, 514, 164, 8, 'var(--dg-pcb)')}</g></g>`;
  }

  /* ================================================================ 欄 B：晶片電阻（厚膜）

     R1：電阻膜（326–340）**兩端壓在上面電極（332–342）之上**，不是頭碰頭對接。
     R2：修整溝只切在電阻膜上（326–336），沒有碰到陶瓷基板（342 起）。
     R3：玻璃保護層（314–326）在修整溝的外側，把它蓋起來。
     R4：端電極由內到外是 **Cu → Ni → Sn**（左端 376/370/364、右端 590/604/610）。
     R5：端電極上接上面電極、下接底面電極 —— 那正是「三面包覆」。*/
  function drawB() {
    const term = (cu, ni, sn) => R(cu, 328, 14, 75, 'var(--dg-cu)', 'part')
      + R(ni, 326, 6, 79, 'var(--dg-ni)', 'part') + R(sn, 324, 6, 83, 'var(--dg-sn)', 'part');
    return `<g>
      ${part('res_glass', SEG_R, R(404, 314, 172, 12, 'var(--dg-glass)', 'part', 1))}
      ${part('res_film', SEG_R, R(410, 326, 160, 14, 'var(--dg-resin)', 'part'))}
      ${part('res_trim', SEG_R, R(500, 326, 7, 10, 'var(--dg-bg)', 'part')
    + line('M500,326 v10 h7 v-10', 'var(--dg-warn)', 1.6))}
      ${part('res_inner_term', SEG_R, R(392, 332, 44, 10, 'var(--dg-ni)', 'part') + R(544, 332, 44, 10, 'var(--dg-ni)', 'part'))}
      ${part('res_substrate', SEG_R, R(390, 342, 200, 48, 'var(--dg-cer)', 'part'))}
      ${part('res_bottom', SEG_R, R(394, 390, 44, 9, 'var(--dg-ni)', 'part') + R(542, 390, 44, 9, 'var(--dg-ni)', 'part'))}
      ${part('res_term3', SEG_R, term(376, 370, 364) + term(590, 604, 610))}
      <g pointer-events="none">${R(356, 407, 268, 9, 'var(--dg-pcb)')}
        ${solder(362, 399, 42, 8)}${solder(576, 399, 42, 8)}</g>
      ${part('shunt_alloy', SEG_R,
    R(430, 470, 120, 26, 'var(--dg-steel)', 'part')
    + R(390, 462, 40, 42, 'var(--dg-cu)', 'part', 2) + R(550, 462, 40, 42, 'var(--dg-cu)', 'part', 2)
    + R(396, 450, 12, 12, 'var(--dg-sn)', 'part', 1) + R(572, 450, 12, 12, 'var(--dg-sn)', 'part', 1)
    + R(392, 504, 36, 9, 'var(--dg-sn)', 'part', 1) + R(552, 504, 36, 9, 'var(--dg-sn)', 'part', 1))}
      <g pointer-events="none">${R(376, 513, 228, 8, 'var(--dg-pcb)')}</g></g>`;
  }

  /* ================================================================ 欄 C：石英頻率元件（AT 切 SMD）

     Q1：石英片 736–892／378–385，四周與上下**都沒有碰到**腔壁（720／920）與蓋子（350）與底（414）。
     Q2：固定點**只有兩個，而且都在左端**（727／742）—— 懸臂式。
     Q3：上下激發電極**中央對齊**（兩片都是 784–864，中心 824 ＝ 石英片中心 814±10 內）。
     Q4：腔內填 `--dg-bg`（＝畫布底色），所以在四個配色下都「看得出是空的」。
        §9 特別交代**不要用半透明** —— 半透明在淺色主題下會看不出是空的。
     Q5：縫焊是**一圈連續的線**，不是斷續的點（一支 path、沒有 dasharray）。
     Q6：振盪器那一格的 IC 畫在底座上、石英片下方，**沒有碰到石英片**。*/
  const BASE = 'M700,350 L712,350 L712,372 L720,372 L720,414 L920,414 L920,372 L928,372 L928,350 L940,350 L940,430 L700,430Z';
  const BASE2 = 'M712,472 L726,472 L726,510 L914,510 L914,472 L928,472 L928,522 L712,522Z';
  function drawC() {
    return `<g>
      ${part('xtal_cavity', '', R(720, 350, 200, 64, 'var(--dg-bg)', 'part'))}
      ${part('xtal_base', '', P(BASE, 'var(--dg-cer)', 'part') + R(720, 392, 56, 22, 'var(--dg-cer-cut)', 'part'))}
      ${part('xtal_blank', '', R(736, 378, 156, 9, 'var(--dg-glass)', 'part'))}
      ${part('xtal_elec', '', R(774, 374.5, 80, 3.5, 'var(--dg-au)', 'part') + R(774, 387, 80, 3.5, 'var(--dg-au)', 'part'))}
      ${part('xtal_mount', '', C(740, 389.5, 5, 'var(--dg-resin)', 'part') + C(758, 389.5, 5, 'var(--dg-resin)', 'part'))}
      ${part('xtal_lid', '', R(698, 336, 244, 14, 'var(--dg-steel)', 'part', 1)
    + line('M698,350 L942,350', 'var(--dg-cu-lit)', 3)
    + line('M698,336 L698,350 M942,336 L942,350', 'var(--dg-cu-lit)', 2.4))}
      ${part('xtal_pad', '', [704, 752, 850, 898].map(px => R(px, 430, 38, 9, 'var(--dg-au)', 'part', 1)).join(''))}
      <g pointer-events="none">${R(688, 439, 264, 9, 'var(--dg-pcb)')}</g>
      ${part('xtal_osc', '', R(726, 472, 188, 38, 'var(--dg-bg)', 'part')
    + P(BASE2, 'var(--dg-cer)', 'part')
    + R(710, 462, 220, 10, 'var(--dg-steel)', 'part', 1)
    + line('M710,472 L930,472', 'var(--dg-cu-lit)', 2.4)
    + R(760, 496, 80, 14, 'var(--dg-emc)', 'part', 1)
    + R(750, 480, 120, 5, 'var(--dg-glass)', 'part'))}
      <g pointer-events="none">${R(716, 522, 34, 8, 'var(--dg-au)')}${R(890, 522, 34, 8, 'var(--dg-au)')}
        ${R(700, 530, 244, 8, 'var(--dg-pcb)')}</g></g>`;
  }

  /* ================================================================ 底部共同的尺（S2）
     §7-C：三種零件的**實際外形尺寸（mm）這次查不到可引用的通用尺寸表**，
     所以這把尺只宣稱「同一個比例」，**一個 mm 數字都不寫**。
     MLCC 那張有 EIA／公制雙標的案號表，但那是**電容**的案號，不准套到電感與石英上。*/
  function ruler(x, y) {
    const base = y + 96;
    const box = (bxx, w2, h) => line(`M${bxx},${base} v${-h} h${w2} v${h}`, 'var(--dg-ink-3)', 1.5);
    return `<g data-part="size_ruler">
      <rect class="frame part" x="${x}" y="${y}" width="484" height="130" rx="9"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">底部共同的尺：三顆用同一個比例並排（示意）</text>
      ${line(`M${x + 24},${base} H${x + 300}`, 'var(--dg-ink-3)', 1)}
      ${box(x + 34, 74, 46)}${box(x + 146, 54, 26)}${box(x + 224, 62, 32)}
      <text class="sub" x="${x + 34}" y="${base + 16}">功率電感</text>
      <text class="sub" x="${x + 146}" y="${base + 16}">晶片電阻</text>
      <text class="sub" x="${x + 224}" y="${base + 16}">石英元件</text>
      <text class="sub" x="${x + 320}" y="${y + 48}">三顆都是指甲蓋等級的</text>
      <text class="sub" x="${x + 320}" y="${y + 66}">小零件。實際外形依料</text>
      <text class="sub" x="${x + 320}" y="${y + 84}">號而異，本圖查不到可</text>
      <text class="sub" x="${x + 320}" y="${y + 102}">引用的尺寸表，不標 mm。</text></g>`;
  }

  /* ================================================================ 整張圖 */
  function passiveRLC() {
    const rowsA = [
      { id: 'ind_body', ax: 66, ay: 338, t: '金屬磁粉壓製的本體', s1: '磁芯與外殼是同一塊，繞組直接', s2: '壓在粉裡；比鐵氧體更耐大電流' },
      { id: 'ind_wind', ax: 96, ay: 348, t: '扁平銅線繞組', s1: '扁平線立繞，同樣空間塞進更多', s2: '銅，直流電阻更低（剖面是長方形）' },
      { id: 'ind_flux', ax: 80, ay: 372, t: '磁通路徑（封閉、走在本體裡）', s1: '磁通不跑出本體之外 —— 那就是', s2: '「磁屏蔽」這個說法的意思' },
      { id: 'ind_term', ax: 62, ay: 416, t: '引出端子（只在底面）', s1: '繞組兩端折出來貼在底面，所以', s2: '它是表面黏著件，不是插件' },
      { id: 'ind_wirewound', ax: 72, ay: 468, t: '另一種做法：繞線型＋鐵氧體', s1: '磁芯、圓線、上蓋是分開的件，', s2: '看得到縫隙；鐵氧體比較容易飽和' },
      { id: 'ind_body', t: '規格要看兩個電流，不是一個', s1: '飽和電流 Isat 與溫升電流 Irms，', s2: '小的那一個才是天花板（見右下）' },
    ];
    const rowsB = [
      { id: 'res_substrate', seg: SEG_R, ax: 390, ay: 366, t: '氧化鋁陶瓷基板', s1: '整顆零件的底，也是散熱的路；', s2: '上面的每一層都印在它身上' },
      { id: 'res_film', seg: SEG_R, ax: 410, ay: 333, t: '電阻膜（釕系厚膜）', s1: '網印上去再燒結，兩端壓在電極', s2: '上（是重疊，不是頭碰頭對接）' },
      { id: 'res_trim', seg: SEG_R, ax: 500, ay: 328, t: '雷射修整溝 ← 它的身分證', s1: '印出來的阻值不會剛好，量完用', s2: '雷射切一道溝，把阻值往上修' },
      { id: 'res_glass', seg: SEG_R, ax: 404, ay: 318, t: '玻璃保護層', s1: '修完才蓋上去，所以那道溝在它', s2: '底下 —— 溝露在最外面就是畫錯' },
      { id: 'res_term3', seg: SEG_R, ax: 364, ay: 350, t: '端電極三層（Cu／Ni／Sn）', s1: '由內到外；Ni 擋焊料侵蝕、Sn 幫', s2: '助焊接。原理見 MLCC 那張' },
      { id: 'shunt_alloy', seg: SEG_R, ax: 390, ay: 470, t: '另一種做法：合金檢流電阻', s1: '整片金屬合金當電阻體，沒有陶', s2: '瓷基板；四個接點分開走電流與量壓' },
    ];
    const rowsC = [
      { id: 'xtal_blank', ax: 736, ay: 381, t: '石英晶片（AT 切薄片）', s1: '從人工培養的石英上依特定角度', s2: '切下來；AT 切約 35°15′（US6629342）' },
      { id: 'xtal_elec', ax: 784, ay: 374, t: '激發電極（上下對齊）', s1: '上下兩面各一片，中央對齊；靠它', s2: '把電壓變成機械振動' },
      { id: 'xtal_mount', ax: 727, ay: 392, t: '只靠同一端的兩點架著', s1: '四周都不能碰到東西 —— 碰到就', s2: '振不動。支撐點數量為示意' },
      { id: 'xtal_cavity', ax: 760, ay: 358, t: '密封的空腔（裡面是空的）', s1: '封不住，頻率就跟著環境跑掉；', s2: '這一格填的是畫布底色，不是材料' },
      { id: 'xtal_lid', ax: 698, ay: 343, t: '金屬蓋＋縫焊密封', s1: '用電阻加熱把金屬蓋焊在陶瓷底', s2: '座上，一圈連續的焊縫' },
      { id: 'xtal_osc', ax: 712, ay: 490, t: '同一個封裝多一顆 IC＝振盪器', s1: '只有石英片的叫晶體 XTAL，多一顆', s2: '振盪電路叫 XO，再加溫補叫 TCXO' },
    ];

    return `<svg class="dg dgm dgrlc" viewBox="0 0 ${W} 1300" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ 這一段是 SVG 裡的 style，瀏覽器把它當標記解析 —— 連註解裡都不准出現角括號
           （DECISIONS #231：寫一個像標籤的東西進去，整張樣式表會變成 0 條規則）。

           描邊與發光降一階（只作用在這一張圖）。理由跟 ic_substrate 那張同源：
           這張圖的零件細碎（4 圈繞組、6 顆圓線、3 層端電極、4 個焊墊），
           2.2px 的描邊套在 3.5px 高的電極上，那一層會整條變成實心色塊。
           平時不描邊 → 滑過去 1.4px → 你點的那一個 2.4px ＋ 5px 暈開。
           前面多一個 svg 型別選擇器是必要的：跟 diagrams.js 那條特異性一樣（0,4,0），
           加上型別變成 (0,4,1) 才穩定壓過去，不必去動 diagrams.js。*/
        svg.dgrlc [data-seg] .part{stroke-width:0}
        svg.dgrlc [data-seg].sel .part{stroke-width:0;filter:none}
        svg.dgrlc [data-seg]:hover .part{stroke-width:1.4;filter:none}
        svg.dgrlc [data-seg].sel-part .part{stroke-width:2.4;filter:var(--dg-glow,drop-shadow(0 0 5px var(--c)))}
        /* 沒有掛 data-seg 的欄（電感、石英、共同舞台、共同的尺）給一條固定的細描邊，
           不然它們在深底上會糊成一團。用 --dg-part-mix（配色會換掉它），不是寫死的灰。*/
        svg.dgrlc [data-part]:not([data-seg]) .part{stroke:var(--dg-part-mix);stroke-width:.9}
        /* ★ 引線的 fill 一定要自己關掉。diagrams.js 的 .leader 規則寫在
           「.dg [data-seg] .leader」底下 —— 這張圖有兩欄**刻意不掛 data-seg**（§7-D2），
           那兩欄的引線就吃不到那條規則，會退回預設的黑色實心多邊形（一大塊黑楔子）。
           這一條特異性 (0,2,1) 低於 diagrams.js 那條 (0,3,0)，所以電阻欄的引線
           仍然是環節色，只有沒有 seg 的那兩欄吃這裡的中性色。*/
        svg.dgrlc .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
      </style>
      <text class="ttl" x="16" y="26">電感·電阻·石英：板子上另外三種一塊錢的零件，各自有一個最容易選錯的規格</text>
      <text class="cap" x="16" y="46">上面是它們同時出現的那一小塊主板（供電與時脈區），下面三欄各切開一顆。三者之間沒有上下游關係，所以這張圖刻意不畫任何流程箭頭。</text>

      <!-- ================= 共同舞台：一小塊主板的 2.5D 微斜頂視（高度 216，不到全圖的 1/3） ================= -->
      <rect class="frame" x="16" y="60" width="948" height="216" rx="9"/>
      ${stage()}
      <!-- 標註全部排到板子上方那條空白帶，用引線指下去 —— 字一個都不壓在板子或零件上。
           ⚠ ② 與 ③ 的位置有一次寫反過（② 指到晶振、③ 指到電阻）：
           v 越大＝越往畫面深處＝**越高**，所以 v=0.80 的晶振在上、v=0.16 的電阻在下。 -->
      <g pointer-events="none">
        <path class="leader" d="M106,118 L186,128"/>
        <path class="leader" d="M252,118 L212,210"/>
        <path class="leader" d="M706,118 L648,172"/>
        <text class="lbl" x="24" y="94">③ 一顆晶振</text>
        <text class="sub" x="24" y="112">板子的時間從這裡來</text>
        <text class="lbl" x="216" y="94">② 一顆檢流電阻</text>
        <text class="sub" x="216" y="112">串在供電路徑上</text>
        <text class="lbl" x="430" y="94">GPU／ASIC（只畫輪廓）</text>
        <text class="sub" x="430" y="112">這張圖不畫晶片內部</text>
        <text class="lbl" x="700" y="94">① 一排電感</text>
        <text class="sub" x="700" y="112">多相供電，一相一顆</text>
        <text class="sub" x="660" y="270">橘線＝供電　青線＝時脈　三者之間沒有流程箭頭</text>
      </g>


      ${D.fold('rlc2', '② 三顆零件各自剖開：電感、電阻、石英元件', '三欄等高剖面 —— 金屬磁粉電感、厚膜電阻、石英諧振器各自的內部構造', `
      <!-- ================= 下方三欄（等高等寬，同一支 col() 產生） ================= -->
      ${col(0, '欄 A', '功率電感（一體成型／模壓）', drawA(),
      ['它把脈衝電流變成平順的電流', '選錯會飽和，或是燒燙'], rowsA,
      ['台股在「功率電感」族群：3357 臺慶科／',
        '3236 千如／6155 鈞寶。這一欄不掛環節。'])}
      ${col(1, '欄 B', '晶片電阻（厚膜）', drawB(),
      ['它把電流變成看得懂的電壓', '選錯會不準，或是發燙'], rowsB,
      ['點這一欄的零件會對到「被動元件 MLCC /',
        '電阻」環節（2327 國巨／2492 華新科 等）。'])}
      ${col(2, '欄 C', '石英頻率元件（AT 切 SMD）', drawC(),
      ['它決定整塊板子的時間', '封不住，時間就跟著走鐘'], rowsC,
      ['台股在「石英頻率控制」族群：3042 晶技／',
        '2484 希華／3221 台嘉碩。這一欄不掛環節。'])}
      `)}

      ${D.fold('rlc3', '③ 共同的尺寸尺｜電感要看兩個電流｜這張圖的答案', '三顆零件的實體比例尺、飽和電流與溫升電流的差別、結論框與免責', `
      <!-- ================= 底部：共同的尺 ＋ 電感的兩個電流 ================= -->
      ${ruler(16, 964)}
      <rect class="frame" x="516" y="964" width="448" height="130" rx="9"/>
      <text class="hd" x="530" y="988">電感的規格要看兩個電流，不是一個</text>
      <text class="sub" x="530" y="1010">飽和電流 Isat ＝ 電感值掉到規定幅度（常見 10%／20%／30%）</text>
      <text class="sub" x="530" y="1028">時的電流；溫升電流 Irms ＝ 讓零件溫度升高一個規定值（功率</text>
      <text class="sub" x="530" y="1046">電感常用 40°C，常見值）的直流電流。</text>
      <text class="sub" x="530" y="1066" style="fill:var(--dg-warn)">★ 兩個數字通常不一樣，小的那一個才是天花板。</text>
      <text class="cap" x="530" y="1084">來源：磁性元件原廠應用手冊（門檻與溫升基準各家不同，不寫成標準）</text>

      <!-- ================= 結論框：這張圖的答案 ================= -->
      <rect class="frame" x="16" y="1110" width="948" height="114" rx="9"/>
      <text class="hd" x="30" y="1134">三顆都只值一塊錢，但三顆都會讓整塊板子壞掉</text>
      <text class="sub" x="30" y="1158">① 電感選錯 → 磁芯飽和、電感值急降，或零件過熱 —— 而且 Isat 與 Irms 是兩個不同的天花板</text>
      <text class="sub" x="30" y="1178">② 電阻選錯 → 量到的電流不準，或本身發燙讓阻值漂掉 —— 要量電流就得用合金檢流那一種</text>
      <text class="sub" x="30" y="1198">③ 石英封不住 → 時脈漂掉，整塊板子的時間就錯了 —— 密封腔是這一類零件的生死線</text>
      <text class="sub" x="30" y="1216" style="fill:var(--dg-warn)">★ 這三種零件之間沒有上下游關係，所以這張圖沒有任何流程箭頭；放在一起是因為它們真的在同一塊板子的同一區。</text>

      <text class="cap" x="16" y="1246">示意圖，非實物比例｜各層厚度與繞組圈數均為示意；三種零件的 mm 尺寸、良率、單價、市占一律不寫（查不到可引用的來源）。</text>
      <text class="cap" x="16" y="1264">點零件篩到的是「環節」不是整個族群：這張圖只有「電阻」那一欄對得到供應鏈環節，電感與石英目前在供應鏈圖上還沒有自己的一格。</text>
      <text class="cap" x="16" y="1282">這張圖不畫任何電容（MLCC／鋁質電解／固態／鉭質）—— 那是「被動元件：MLCC 疊層剖析」那一張的主題，端電極的原理也在那張講完了。</text>
      `)}
    </svg>`;
  }

  window.DG.register('power_inductor', {
    level: 'group', chain: 'electronics',
    name: '被動元件：電感·電阻·石英',
    draw: passiveRLC, native: 980, scene: null,
    q: '電感、電阻、石英這三種零件各自長什麼樣？為什麼電感要看兩種電流、電阻要雷射刻一刀、石英要抽真空？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       ⚠ 只有 **seg 為 `passive_comp` 的電阻欄**現在真的點得出小卡（見檔頭那段說明）。
       電感欄與石英欄仍然逐件寫齊：
         ① 那是這份對應該住的地方，不是別處；
         ② `industry.js` 一旦支援「沒有 data-seg 也能開小卡」，這兩欄就自己亮起來；
         ③ 在那之前，這兩欄的答案**已經印在畫面上**（每欄底下兩行 ＋ 結論框），不是留白。
       `cos` 只放 supply_chain.json 的 companies[].id；「這家負責什麼」一律讀 companies[].tech（R3）。
       `items` 只填 edges[].item 真的有的字串 —— `passive_comp` 這一格目前**一條邊都沒有**，
       所以這裡一個 items 都沒寫（編一個出來就是 R5 禁止的事）。*/
    parts: {
      // ---- 共同件
      stage_board: {
        name: '共同舞台：主板的供電與時脈區',
        desc: '這三種零件真的同時出現在同一塊板子的同一個區域 —— 所以把它們放進同一張圖不是版面湊合。GPU 只畫輪廓，晶片內部不是這張圖的主題。',
        none: '這一塊只是舞台、不是零件，沒有對應的公司。板子本身（PCB）與晶片各有自己的圖。',
      },
      size_ruler: {
        name: '共同的尺：三顆並排比大小',
        desc: '用同一個比例把三種零件的外形並排，讓「它們其實差不多大」被看見 —— 這是三合一版面唯一真正的增值。',
        none: '這一塊是比例尺，不是零件。⚠ 三種零件的實際 mm 尺寸這次查不到可引用的通用尺寸表，所以只宣稱同一個比例，不標任何數字（R5：查不到就寫查不到）。',
      },
      // ---- 欄 A　功率電感（★ 這一欄不掛 data-seg，見檔頭）
      ind_body: {
        name: '金屬磁粉壓製的本體（一體成型）',
        desc: '磁芯與外殼是同一塊：金屬磁粉在遠低於鐵氧體燒結的溫度下壓製，可以直接壓在繞組之上而不會熔掉銅線。金屬磁粉的飽和磁通密度比鐵氧體高，同樣體積能扛更大電流，而且是「軟飽和」。',
        none: '★ 這一欄在 supply_chain.yaml 裡沒有自己的環節，所以點下去不會列出公司。台股做功率電感的在 groups.yaml 的「功率電感」族群：3357 臺慶科、3236 千如、6155 鈞寶 —— 但這三家整份 supply_chain.yaml 一家都沒有，所以不能掛在「被動元件 MLCC / 電阻」那一格（掛了等於宣稱國巨那五家做電感）。',
      },
      ind_wind: {
        name: '扁平銅線繞組（立繞）',
        desc: '扁平線立繞，同樣的空間能塞進更多銅，直流電阻更低。剖面是橫躺的長方形 —— 圓形那是繞線型的圓線，兩種做法從剖面就分得開。',
        none: '同上欄：電感這一格在供應鏈資料裡還沒有自己的環節。銅線本身的上游（銅箔／漆包線）也不在這張圖的範圍內。',
      },
      ind_flux: {
        name: '磁通路徑（封閉迴路）',
        desc: '磁通繞著繞組跑一圈，而且完全走在本體之內 —— 那就是「磁屏蔽」的意思。跑出本體之外就是漏磁，會跟磁屏蔽的說法矛盾。',
        none: '這是一條示意的磁力線，不是零件，沒有對應的公司。',
      },
      ind_term: {
        name: '引出端子（只在底面）',
        desc: '繞組兩端折出來貼在底面，所以它是表面黏著件。端子只在底面 —— 畫到頂面或整個側面就是別種零件。',
        none: '同欄 A：電感這一格在供應鏈資料裡還沒有自己的環節。',
      },
      ind_wirewound: {
        name: '對照：繞線型＋鐵氧體磁芯',
        desc: '磁芯、線圈、上蓋是分開的件，所以看得到縫隙與外露的圓線。鐵氧體在電流與溫度升高時比較容易飽和，飽和之後電感值會急降；粉末磁芯的磁通承載力隨溫度幾乎不變。',
        none: '同欄 A：電感這一格在供應鏈資料裡還沒有自己的環節。台股在 groups.yaml 的「功率電感」族群。',
      },
      // ---- 欄 B　晶片電阻（★ 只有這一欄真的點得出小卡）
      res_substrate: {
        name: '氧化鋁陶瓷基板',
        desc: '整顆零件的底，也是散熱的路。上面的電極、電阻膜、保護層全部印在它身上，常見是 96% 氧化鋁。',
      },
      res_inner_term: {
        name: '上面電極（內部端電極）',
        desc: '先印在基板兩端，再讓電阻膜的兩端壓上來 —— 電阻膜與電極是重疊的，不是頭碰頭對接。',
      },
      res_film: {
        name: '電阻膜（釕系厚膜）',
        desc: '網印上去再燒結的釕系厚膜，橫跨兩端電極。阻值就是由它的材料、厚度與形狀決定的。',
      },
      res_trim: {
        name: '雷射修整溝 —— 晶片電阻的身分證',
        desc: '印出來的阻值不會剛好，量完之後用雷射切一道溝，把阻值「往上」修到規格。沒有這道溝，這顆零件的剖面看起來就跟任何一種三明治小方塊沒兩樣。',
      },
      res_glass: {
        name: '玻璃保護層（passivation）',
        desc: '修完才蓋上去，保護電阻膜與那道溝。所以在剖面上，溝一定在保護層底下 —— 溝露在最外面就是把順序畫反了。',
      },
      res_term3: {
        name: '端電極三層（Cu／Ni／Sn）',
        desc: '由內到外是銅、鎳、錫：Ni 擋焊料侵蝕、Sn 幫助焊接，並把上面電極與底面電極連起來（三面包覆）。原理與 MLCC 那張相同，細節見「被動元件：MLCC 疊層剖析」。',
      },
      res_bottom: {
        name: '底面電極',
        desc: '貼在板子上的那一面。它跟上面電極靠端電極連起來，那正是「三面包覆」在剖面上的樣子。',
      },
      shunt_alloy: {
        name: '對照：合金檢流電阻（shunt）',
        desc: '整片金屬合金（錳銅／康銅之類）當電阻體，兩端是明顯更厚的銅端子，沒有陶瓷基板。為了量得準，走電流與量電壓用不同的接點（四端／Kelvin 量測）。專門用在「要知道電流有多大」的地方，不是拿來分壓的。',
        note: '國巨與華新科的 tech 欄有「晶片電阻」，但**這次查不到「哪一家做合金檢流電阻」的具名揭露** —— 所以這裡不挑一家出來講（R5）。',
      },
      // ---- 欄 C　石英頻率元件（★ 這一欄不掛 data-seg，見檔頭）
      xtal_blank: {
        name: '石英晶片（AT 切薄片）',
        desc: '從人工培養的石英晶體上，依特定角度切下來的薄片。常見的 AT 切是把 Y 板轉約 35°15′ 切出來的（來源：AT 切製法專利 US6629342，單一來源）。',
        none: '★ 這一欄在 supply_chain.yaml 裡沒有自己的環節。台股做石英元件的在 groups.yaml 的「石英頻率控制」族群：3042 晶技、2484 希華、3221 台嘉碩 —— 三家整份 supply_chain.yaml 都沒有，所以不掛環節（掛「被動元件」那一格等於宣稱國巨那五家做石英）。',
      },
      xtal_elec: {
        name: '激發電極',
        desc: '上下兩面各一片、中央對齊，靠它把電壓變成機械振動。上下錯開就振不出設計的模態。',
        none: '同欄 C：石英這一格在供應鏈資料裡還沒有自己的環節。',
      },
      xtal_mount: {
        name: '導電膠固定點（同一端兩點）',
        desc: '石英片只靠同一端的兩點導電膠架著，四周與上下都不能碰到東西 —— 碰到就振不動。',
        note: '⚠ 低信心：這次**查不到任何來源明講「只有兩點、位於同一端」**。圖上照這樣畫是因為那是表達「四周懸空」最直觀的方式；支撐點的數量請當成示意，不要當規格。',
        none: '同欄 C：石英這一格在供應鏈資料裡還沒有自己的環節。',
      },
      xtal_cavity: {
        name: '密封的空腔',
        desc: '裡面是空的。封不住，頻率就跟著環境跑掉 —— 氣密是為了讓特性長期維持。這一格在圖上填的是畫布底色，不是某種材料。',
        none: '空腔不是零件。做封裝的是石英元件廠自己（見上一條的族群說明）。',
      },
      xtal_lid: {
        name: '金屬蓋＋縫焊密封（seam seal）',
        desc: '用電阻加熱把金屬蓋焊在陶瓷底座上，形成一圈連續的焊縫。焊縫畫成一段一段的點就不是縫焊了。',
        none: '同欄 C：石英這一格在供應鏈資料裡還沒有自己的環節。',
      },
      xtal_pad: {
        name: '底面焊墊',
        desc: '貼在板子上的那一面，常見四墊（兩個訊號、兩個接地）或兩墊。它跟另外兩顆一樣都是表面黏著件。',
        none: '同欄 C：石英這一格在供應鏈資料裡還沒有自己的環節。',
      },
      xtal_osc: {
        name: '對照：同一封裝多一顆 IC ＝ 振盪器',
        desc: '只有石英片的叫晶體（XTAL）；裡面多一顆振盪電路的叫 XO；再加溫度補償電路的叫 TCXO，用來把溫度造成的頻率漂移補回去（穩定度落在 ppm 等級）。把石英放進恆溫槽的 OCXO 更穩（ppb 等級），但更大更耗電。',
        note: '⚠ 各家給的 TCXO 穩定度數字口徑不一（溫度範圍、含不含老化都沒交代），所以畫面上只寫「ppm 等級」，不寫具體數值。',
        none: '同欄 C：石英這一格在供應鏈資料裡還沒有自己的環節。',
      },
    },
  });
})();
