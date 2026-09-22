/* 連接器與高速互連 —— docs/diagram_plan.md 的第 10 張（族群 `ai_interconnect`、ai_server 鏈）

   合約＝`docs/diagram_specs/connector_hsio.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的四件事：

     · §0-A **不做真 3D**（`scene: null`）。接觸物理、遮蔽關係、鍍層順序全部在剖面裡；
       最強的 3D 候選（這四類連接器在機櫃裡的位置）**既有的 `ai_server` 鏈層級 3D 場景
       已經在做**，再做一個就是重複，還多一組 WebGL context 與 rAF 要管。
     · §0-B 佈局：上方一條**編號的訊號路徑帶** ＋ 下方 **2×2 四格**（不是 1×4）。
       980 拆成四欄之後單欄只剩約 245px，剖面加三行標註一定會逼人把字縮到 12px 以下 ——
       這是版面決策，不是美感偏好。路徑帶的編號與格子的編號一致（X2）。
     · §0-C **掛 `ai_interconnect` 不是 `connector_ind`**。`connector_ind` 的 note
       自己寫著「不是資料中心高速料號」，而這張圖從頭到尾講的就是資料中心高速料號。
       掛上去等於宣稱那四家做資料中心互連 —— 跟「金像電被放進 ABF 載板」同一條錯。
     · §0-D 跟 `switch_board`（交換器板卡）的分工：那張畫**一整塊板**、這張畫**一個接點**。
       所以這個檔裡**沒有** CPO、沒有 PCB 疊構剖面、沒有層數、沒有背鑽、
       沒有光模組的內部光學、沒有風扇與晶片散熱片（籠子自己的散熱片除外）。

   誠實性（§6-N）：畫面上**沒有任何市占率、單價、成長率、營收占比**。
   唯一的兩個數字是底部對照條的 22 吋 / 4.5 吋，而且**一定要連同來源與前提一起寫**
   （單一原廠技術頁；IEEE 802.3ck 的損耗上限；特定高階板材）—— 只寫數字不寫前提就是不過。
   CEM 5.0/6.0 的金手指長度、法向力的公克數、NVL72 的銅纜條數，**一個都沒有進畫面**。

   ⚠ §7-D2 是這張圖最嚴重的落差，畫面上那三行不可省略
   ---------------------------------------------------
   `groups.yaml` 的 `ai_interconnect` 有四家（3665／3533／3526／8103），
   但 `supply_chain.yaml` 的 `connector` 環節**只有 3665 貿聯-KY 一家**
   —— 所以點圖上任何一個連接器零件，篩出來的只會有一家。這張圖自己能做的，
   就是把這件事寫在畫面上，不要讓讀者把「列出來的一家」讀成「這一類料號的供應商」。

   這個檔不碰 `site/diagrams.js`／`site/index.html`／`site/three3d.js`。
   共用工具一律走 `window.DG`；色值一律走 `--dg-*`，JS 裡一個 #xxxxxx 都沒有。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;

  /* ================================================================ 版面常數
     四格用同一組常數產生（§9：四格用同一個 cell() 函式，X1 就自動成立）。*/
  const W = 980;
  const CX = [16, 500], CY = [296, 752], CW = 464, CH = 440;
  const ROW0 = 240, ROWP = 52;         // 格內標註列：相對格頂 240 起、間距 52、共 4 列
  const S_CN = 'connector', S_PCB = 'hdi_pcb', S_OPT = 'optical', S_TH = 'thermal';

  /* ================================================================ 小工具 */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const C = (cx, cy, r, fill, cls) =>
    `<circle${cls ? ` class="${cls}"` : ''} cx="${cx}" cy="${cy}" r="${r}" fill="${fill}"/>`;
  const E = (cx, cy, rx, ry, fill, cls) =>
    `<ellipse${cls ? ` class="${cls}"` : ''} cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}"/>`;
  const P = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const line = (d, col, w2, extra) =>
    `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const part = (id, seg, inner) =>
    `<g data-part="${id}"${seg ? ` data-seg="${seg}"` : ''}>${inner}</g>`;
  // 箭頭：頭的方向由 (dx, dy) 決定 —— 法向力與擦拭行程差 90 度，就靠這一支
  function arrow(x, y, dx, dy, col) {
    const L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L;
    const x2 = x + dx, y2 = y + dy;
    const a = 5;
    return line(`M${x},${y} L${x2},${y2}`, col, 2)
      + P(`M${x2},${y2} L${(x2 - ux * 9 - uy * a).toFixed(1)},${(y2 - uy * 9 + ux * a).toFixed(1)}`
        + ` L${(x2 - ux * 9 + uy * a).toFixed(1)},${(y2 - uy * 9 - ux * a).toFixed(1)}Z`, col);
  }

  /* ================================================================ 上方：訊號路徑帶（S1、X2、X3）
     高度 220，整張圖 1392 —— 不到三分之一。ASIC 只是一個標了名字的方塊，沒有內部細節。
     五個編號站點的編號**跟下面四格的標題一致**，沒有編號路徑帶就只是裝飾。*/
  const px2 = (u, v) => 66 + u * 470 + v * 62;
  const py2 = (u, v) => 250 - v * 96;
  // ③ 那條「走內部線纜」的路徑。畫線與跑動的那一顆點共用同一條 d，兩者才不會對不齊。
  const SIG3 = 'M210,176 C260,120 420,104 560,128 L612,150';
  function band() {
    const bd = `M${px2(0, 0)},${py2(0, 0)} L${px2(1, 0)},${py2(1, 0)} L${px2(1, 1)},${py2(1, 1)} L${px2(0, 1)},${py2(0, 1)}Z`;
    const side = `M${px2(0, 0)},${py2(0, 0)} v10 L${px2(1, 0)},${py2(1, 0) + 10} v-10Z`;
    // 前面板（右）：一片直立的鈑金，上面四個光模組籠開口
    const panel = R(628, 120, 26, 140, 'var(--dg-alu-2)', 'part', 2)
      + [0, 1, 2, 3].map(i => R(631, 132 + i * 32, 20, 22, 'var(--dg-frame)')).join('');
    // 機櫃背板線纜匣（更右後方）：直立框體 ＋ 裡面成束的銅纜
    const cart = R(796, 108, 40, 150, 'var(--dg-frame)', 'part', 3)
      + [0, 1, 2, 3, 4, 5].map(i => line(`M802,${120 + i * 22} h28`, 'var(--dg-cu)', 3)).join('');
    return `<g data-part="path_band">
      ${P(side, 'var(--dg-pcb-2)')}${P(bd, 'var(--dg-pcb)', 'part')}
      ${R(150, 176, 84, 34, 'var(--dg-emc)', 'part', 3)}
      ${line('M234,192 L470,192', 'var(--dg-sw-sig)', 2.6)}
      ${R(470, 176, 14, 34, 'var(--dg-sw-gold)', 'part', 1)}
      ${R(486, 172, 16, 42, 'var(--dg-frame)', 'part', 2)}
      ${line(SIG3, 'var(--dg-sw-sig)', 3.2)}
      ${line('M232,186 C330,150 520,158 640,214 L790,196', 'var(--dg-sw-sig)', 2.2)}
      ${panel}${cart}
      <!-- 整張圖唯一的動畫（§9：最多一個，四格本身不要各自動）：
           一顆訊號從 ASIC 出發、沿著 ③ 那條線纜跑到前面板。
           靜止時那條路徑本身仍然看得見（它是一條實線，不是只有動畫時才出現）。-->
      <circle r="3.4" fill="var(--dg-sw-sig)">
        <animateMotion dur="3.6s" repeatCount="indefinite" path="${SIG3}"/></circle>
    </g>`;
  }

  /* ================================================================ 格內的標註列
     走法固定：**從零件水平往左出去 → 垂直落到那一列 → 進入圓點**，
     每一列的垂直段錯開 4px。文字從 x+43 起、垂直段落在 x+10～x+22，引線一次都沒有壓到字。*/
  function crow(ci, j, o) {
    const x = CX[ci % 2], y = CY[ci > 1 ? 1 : 0] + ROW0 + j * ROWP;
    const elbow = x + 10 + j * 4;
    const lead = o.ax != null
      ? `<path class="leader" d="M${o.ax},${o.ay} L${elbow},${o.ay} L${elbow},${y - 2} L${x + 28},${y - 2}"/>` : '';
    return `<g class="lrow" data-part="${o.id}"${o.seg ? ` data-seg="${o.seg}"` : ''}>
      <rect class="bg" x="${x + 24}" y="${y - 15}" width="${CW - 38}" height="48" rx="6"/>
      ${lead}<circle class="dot" cx="${x + 32}" cy="${y - 2}" r="4"/>
      <text class="lbl" x="${x + 43}" y="${y + 2}">${o.t}</text>
      <text class="sub" x="${x + 43}" y="${y + 18}">${o.s1 || ''}</text>
      <text class="sub" x="${x + 43}" y="${y + 34}">${o.s2 || ''}</text></g>`;
  }
  function cell(ci, no, title, draw, one, rows) {
    const x = CX[ci % 2], y = CY[ci > 1 ? 1 : 0];
    return `<g>
      <rect class="frame" x="${x}" y="${y}" width="${CW}" height="${CH}" rx="9"/>
      <text class="hd" x="${x + 14}" y="${y + 22}">${no}　${title}</text>
      ${draw}
      <text class="lbl" x="${x + 42}" y="${y + 216}">${one}</text>
      ${rows.map((r, j) => crow(ci, j, r)).join('')}</g>`;
  }

  /* ================================================================ 格 ②　板邊金手指與插槽（PCIe CEM）
     E1：鍍層由內到外是 **銅 → 鎳 → 硬金**（左端 206/202/200、右端 291/294/298）。
     E2：硬金 2px、鎳 4px —— 硬金**明顯薄於**鎳。
     E3：卡片前端有**倒角**（板邊那條 path 的下兩個角是斜的）。
     E4：母端彈片畫成**被撐開的變形狀態**（貝茲控制點往外推），上下各一列夾住卡片。
     E5：法向力箭頭**垂直於接觸面**（水平），擦拭箭頭**平行於插入方向**（垂直）。*/
  function draw2() {
    /* `dir` ＝往卡片的方向（左牆 +1、右牆 -1）。彈片是**從槽壁長出來、往卡片彎過去**的，
       所以尾端一定落在鍍層那一條線上（左 202／右 298）—— 往外彎就變成「沒有接觸」了。*/
    const beam = (x0, y0, dir) => line(
      `M${x0},${y0} C${x0 + dir * 3},${y0 - 14} ${x0 + dir * 18},${y0 - 20} ${x0 + dir * 14},${y0 - 34}`,
      'var(--dg-cu-lit)', 3.4, ' stroke-linecap="round"');
    const card = 'M206,318 H294 V398 L285,414 H215 L206,398 Z';
    return `<g>
      ${part('slot_housing', S_CN, R(150, 378, 200, 76, 'var(--dg-frame)', 'part', 3)
      + R(188, 378, 124, 62, 'var(--dg-bg)', 'part') + R(240, 422, 20, 18, 'var(--dg-frame)', 'part'))}
      ${part('slot_beam', S_CN, beam(188, 440, 1) + beam(312, 440, -1) + beam(188, 424, 1) + beam(312, 424, -1))}
      ${part('slot_leg', S_CN, [160, 180, 320, 340].map(px => R(px, 454, 7, 18, 'var(--dg-sn)', 'part', 1)).join(''))}
      ${part('card_edge', S_PCB, P(card, 'var(--dg-pcb)', 'part'))}
      ${part('gold_finger', S_PCB,
      R(206, 328, 3, 72, 'var(--dg-cu)', 'part') + R(202, 328, 4, 72, 'var(--dg-ni)', 'part') + R(200, 328, 2, 72, 'var(--dg-au)', 'part')
      + R(291, 328, 3, 72, 'var(--dg-cu)', 'part') + R(294, 328, 4, 72, 'var(--dg-ni)', 'part') + R(298, 328, 2, 72, 'var(--dg-au)', 'part'))}
      ${part('chamfer', S_PCB, P('M206,398 L215,414 H206Z', 'var(--dg-au)', 'part') + P('M294,398 L285,414 H294Z', 'var(--dg-au)', 'part'))}
      ${part('beam_zoom', S_CN,
      R(364, 334, 104, 110, 'var(--dg-frame)', 'part', 8)
      + R(392, 344, 12, 88, 'var(--dg-pcb)', 'part') + R(388, 344, 4, 88, 'var(--dg-au)')
      + line('M420,428 C414,404 400,398 388,392', 'var(--dg-cu-lit)', 3.4, ' stroke-linecap="round"')
      + arrow(370, 392, 14, 0, 'var(--dg-warn)') + arrow(404, 356, 0, 26, 'var(--dg-accent-2d)'))}
      <g pointer-events="none">${R(120, 472, 260, 10, 'var(--dg-pcb)')}
        <text class="sub" x="372" y="${330}">放大：一支彈片</text>
        <text class="sub" x="110" y="340">公端（卡片）</text>
        <text class="sub" x="122" y="492">母端（插槽）壓在主板上</text></g></g>`;
  }

  /* ================================================================ 格 ③　內部線纜（MCIO／SlimSAS ＋ twinax）
     B1／B2：橫剖面是**兩根等徑導體並排、共用同一層接地遮蔽**（遮蔽是一個橢圓，不是兩個圓）。
     B3：由內到外是 導體 → 介電 → 遮蔽 → 外被。
     B4：同一張圖上同時有「走線纜」與「走板子」兩條路，走板子那條標成對照（虛線）。*/
  function draw3() {
    const tw = (cx, cy) => E(cx, cy, 46, 30, 'var(--dg-emc)', 'part')
      + E(cx, cy, 40, 24, 'var(--dg-steel)', 'part')
      + C(cx - 17, cy, 16, 'var(--dg-cover)', 'part') + C(cx + 17, cy, 16, 'var(--dg-cover)', 'part')
      + C(cx - 17, cy, 7, 'var(--dg-cu)', 'part') + C(cx + 17, cy, 7, 'var(--dg-cu)', 'part');
    return `<g>
      ${part('cable_recept', S_CN, R(560, 400, 56, 34, 'var(--dg-frame)', 'part', 2)
      + [0, 1, 2, 3, 4, 5].map(i => R(564 + i * 9, 434, 4, 14, 'var(--dg-sn)', 'part')).join(''))}
      ${part('cable_plug', S_CN, R(612, 392, 46, 42, 'var(--dg-steel-2)', 'part', 2)
      + R(618, 398, 34, 30, 'var(--dg-frame)', 'part', 2))}
      ${part('cable_body', S_CN, line('M656,412 C700,412 704,368 742,360', 'var(--dg-emc)', 16, ' stroke-linecap="round"')
      + line('M656,412 C700,412 704,368 742,360', 'var(--dg-steel)', 8))}
      ${part('twinax', S_CN, tw(830, 378))}
      <g pointer-events="none">${R(540, 446, 340, 14, 'var(--dg-pcb)')}</g>
      ${part('pcb_route', S_PCB, line('M556,453 H866', 'var(--dg-sw-sig)', 2.4, ' stroke-dasharray="6 5"'))}
      <g pointer-events="none">
        <text class="sub" x="540" y="386">母座（板上）＋公端</text>
        <text class="sub" x="790" y="340">雙軸線橫剖面</text>
        <text class="sub" x="540" y="478">虛線＝另一條路：同樣兩點之間繼續走板子</text></g></g>`;
  }

  /* ================================================================ 格 ④　前面板光模組籠（OSFP／QSFP-DD cage）
     G1：籠架是**鈑金盒且有通風孔**（一排小方孔陣列，不用 pattern —— 淺色主題下 pattern 常常整片消失）。
     G2：用**壓接針腳**固定在板上（針腳畫成魚眼形，不是焊接腳）。
     G3：**EMI 指片圍在開口四周、朝向模組**。
     G4：散熱片在**籠架之上**、不在籠架內也不在模組內，而且有**夾持彈簧**。
     G5：光模組**只有外殼與拉環**，沒有任何內部光學。
     G6：背對背示意的上下兩個籠是**鏡像**且共用同一塊板。*/
  function draw4() {
    const vents = [];
    for (let i = 0; i < 9; i++) for (let j = 0; j < 3; j++) vents.push(R(80 + i * 16, 892 + j * 12, 8, 7, 'var(--dg-bg)'));
    const fins = [];
    for (let i = 0; i < 12; i++) fins.push(R(84 + i * 15, 838, 7, 24, 'var(--dg-alu)', 'part'));
    const fingers = [];
    for (let i = 0; i < 7; i++) fingers.push(line(`M232,${886 + i * 8} l12,-4`, 'var(--dg-steel)', 2.2, ' stroke-linecap="round"'));
    /* 下排兩格的座標是照「第一排 ＋ 456」寫的，但剖面區的上緣只有 +30。
       與其把幾十個數字逐一改掉（改一個漏一個就是版面錯位），整組往上平移 44
       —— 標註列的錨點（rows4／rows5 的 ay）也跟著減 44，兩邊是同一個數字。*/
    return `<g transform="translate(0,-44)">
      ${part('cage_body', S_CN, R(72, 876, 172, 62, 'var(--dg-steel-2)', 'part', 2)
      + R(78, 882, 160, 50, 'var(--dg-bg)', 'part') + vents.join(''))}
      ${part('cage_pressfit', S_CN, [86, 116, 146, 176, 206].map(px =>
      R(px, 938, 6, 16, 'var(--dg-sn)', 'part') + E(px + 3, 946, 4, 5, 'var(--dg-bg)')).join(''))}
      ${part('emi_finger', S_CN, fingers.join(''))}
      ${part('cage_hs', S_TH, R(78, 862, 164, 14, 'var(--dg-alu-2)', 'part', 2) + fins.join('')
      + line('M74,868 C64,846 70,832 86,830 M242,868 C252,846 246,832 230,830', 'var(--dg-steel)', 2.4))}
      ${part('optic_module', S_OPT, R(252, 886, 116, 44, 'var(--dg-alu-3)', 'part', 3)
      + R(368, 898, 26, 20, 'var(--dg-mute)', 'part', 3)
      + [0, 1, 2, 3, 4, 5].map(i => R(258 + i * 9, 930, 5, 6, 'var(--dg-au)', 'part')).join(''))}
      <g pointer-events="none">${R(60, 954, 330, 10, 'var(--dg-pcb)')}</g>
      ${part('belly', S_CN, R(410, 866, 56, 22, 'var(--dg-steel-2)', 'part', 2)
      + R(410, 896, 56, 22, 'var(--dg-steel-2)', 'part', 2) + R(408, 888, 60, 8, 'var(--dg-pcb)', 'part'))}
      <g pointer-events="none">
        <text class="sub" x="252" y="880">插進去的光模組（只有外殼與拉環）</text>
        <text class="sub" x="344" y="860">背對背：上下各一個籠</text>
        <text class="sub" x="60" y="980">籠架用壓接針腳固定在板上，不是焊上去的</text></g></g>`;
  }

  /* ================================================================ 格 ⑤　背板與盲插（cable cartridge／blind-mate）
     K1：**導引柱／斜面比訊號接點更靠前**（導引柱頂端 x=700，接點面 x=736）——
        畫成接點先碰到，在工程上就是把接點撞壞。
     K2：浮動連接器**畫得出浮動間隙**（外框與本體之間上下各留一條）。
     K3：線纜匣裡是**成束的纜線**，不是一塊實心板。*/
  function draw5() {
    const cables = [];
    for (let i = 0; i < 9; i++) cables.push(line(`M846,${846 + i * 11} h48`, 'var(--dg-cu)', 4, ' stroke-linecap="round"'));
    // 同 draw4：整組往上平移 44，rows5 的 ay 也是減 44 之後的數字
    return `<g transform="translate(0,-44)">
      ${part('cartridge', S_CN, R(838, 836, 62, 116, 'var(--dg-frame)', 'part', 3) + cables.join(''))}
      ${part('recept_backplane', S_CN, R(806, 866, 32, 56, 'var(--dg-steel-2)', 'part', 2)
      + R(794, 880, 12, 28, 'var(--dg-bg)', 'part'))}
      ${part('float_conn', S_CN, R(718, 856, 74, 76, 'var(--dg-mute)', 'part', 3)
      + R(726, 864, 58, 60, 'var(--dg-steel-2)', 'part', 2)
      + R(784, 880, 10, 26, 'var(--dg-sw-gold)', 'part', 1))}
      ${part('guide_pin', S_CN,
      P('M660,876 H692 L706,882 L692,888 H660Z', 'var(--dg-steel)', 'part')
      + P('M660,900 H692 L706,906 L692,912 H660Z', 'var(--dg-steel)', 'part'))}
      <g pointer-events="none">
        ${R(560, 856, 100, 76, 'var(--dg-emc)', '', 3)}
        ${arrow(516, 894, 38, 0, 'var(--dg-accent-2d)')}
        ${line('M706,830 V952', 'var(--dg-warn)', 1.4, ' stroke-dasharray="4 4"')}
        ${line('M794,830 V952', 'var(--dg-accent-2d)', 1.4, ' stroke-dasharray="4 4"')}
        <text class="sub" x="560" y="850">運算托盤（推進去的方向）</text>
        <text class="sub" x="622" y="968">導引柱先到</text>
        <text class="sub" x="760" y="968">接點後到</text>
        <text class="sub" x="838" y="830">線纜匣</text></g></g>`;
  }

  /* ================================================================ 底部對照條（S2、N2）
     長度比例直接取 22 : 4.5。**兩根旁邊各自標數字，數字旁邊一定帶來源與前提** ——
     只寫數字不寫前提就是不過（N2）。*/
  function reach(x, y) {
    const k = 460 / 22;                       // 22 吋 ＝ 460px，4.5 吋按同一把尺換算
    return `<g data-part="reach_bar">
      <rect class="frame part" x="${x}" y="${y}" width="948" height="130" rx="9"/>
      <text class="hd" x="${x + 14}" y="${y + 24}">同一份損耗預算，能跑多遠 —— 這就是「線纜取代板子」的全部理由</text>
      ${R(x + 190, y + 40, 22 * k, 16, 'var(--dg-sw-gold)', 'part', 3)}
      ${R(x + 190, y + 64, 4.5 * k, 16, 'var(--dg-warn)', 'part', 3)}
      <text class="lbl" x="${x + 14}" y="${y + 53}">低損耗雙軸線纜</text>
      <text class="lbl" x="${x + 14}" y="${y + 77}">走高階板材的走線</text>
      <text class="sub" x="${x + 664}" y="${y + 53}">約 22 吋</text>
      <text class="sub" x="${x + 306}" y="${y + 77}">約 4.5 吋</text>
      <text class="sub" x="${x + 14}" y="${y + 100}">前提：IEEE 802.3ck 的損耗上限 ＋ 特定高階板材。來源＝連接器原廠技術頁，單一來源，依板材、頻率與設計規則而異。</text>
      <text class="sub" x="${x + 14}" y="${y + 118}">省下來的不只是距離：訊號夠強就不必加中繼器（retimer），少一顆就少一份功耗與成本，板子的層數也能往下壓。</text></g>`;
  }

  /* ================================================================ 整張圖 */
  function connectorHsio() {
    const rows2 = [
      { id: 'gold_finger', seg: S_PCB, ax: 200, ay: 344, t: '金手指是「公端」', s1: '銅 → 鎳阻障 → 硬金，由內到外。硬金是為了耐插拔磨損，', s2: '不是為了導電；所以它比底下的鎳層薄得多' },
      { id: 'chamfer', seg: S_PCB, ax: 206, ay: 404, t: '前端倒角', s1: '沒有倒角，插進去會把母端彈片刮壞 —— 倒角是讓彈片', s2: '順著斜面被推開的那一段' },
      { id: 'slot_beam', seg: S_CN, ax: 188, ay: 424, t: '母端彈片被撐開，才有接觸', s1: '撐開產生法向力（垂直於接觸面），插入時接點擦過金手指', s2: '表面把氧化層刮掉。鍍金能用比較小的法向力，鍍錫要大得多' },
      { id: 'beam_zoom', seg: S_CN, ax: 364, ay: 348, t: '放大：法向力與擦拭是兩個方向', s1: '粉紅箭頭＝法向力，垂直於接觸面；青色箭頭＝擦拭行程，', s2: '平行於插入方向。兩支箭頭同方向就是畫錯了' },
    ];
    const rows3 = [
      { id: 'twinax', seg: S_CN, ax: 784, ay: 372, t: '一對雙軸線（twinax）', s1: '兩根等徑導體並排、共用同一層接地遮蔽。遮蔽擋外來干擾，', s2: '也讓這一對的阻抗穩定 —— 畫成單根同軸就變成另一種線了' },
      { id: 'cable_plug', seg: S_CN, ax: 612, ay: 398, t: '內部線纜連接器', s1: '伺服器裡常見兩種：SlimSAS（規格 SFF-8654，常見 4／8 通道）', s2: '與 MCIO（規格 SFF-TA-1016，密度更高、通道組合更多）' },
      { id: 'cable_recept', seg: S_CN, ax: 560, ay: 416, t: '板上的對接母座', s1: 'MCIO 的 38 針對應 4 通道、74 針對應 8 通道；', s2: '針數本身就是「這條線能帶幾條通道」的直接指標' },
      { id: 'pcb_route', seg: S_PCB, ax: 566, ay: 452, t: '另一條路：繼續走板子', s1: '同樣兩點之間，走板子要多花掉一大段損耗預算 ——', s2: '那就是底下那條尺在比的事' },
    ];
    const rows4 = [
      { id: 'cage_body', seg: S_CN, ax: 72, ay: 846, t: '光模組籠（cage）', s1: '鈑金折出來的盒子，盒身要有通風孔 —— 沒有通風孔就不叫籠。', s2: '所有籠都用壓接針腳固定在板上，不是焊上去的' },
      { id: 'emi_finger', seg: S_CN, ax: 232, ay: 856, t: 'EMI 指片', s1: '圍在開口四周的彈性金屬指，把模組與盒子之間的縫隙壓住，', s2: '擋住電磁干擾外洩與埠間串擾' },
      { id: 'cage_hs', seg: S_TH, ax: 78, ay: 822, t: '騎在籠子上的散熱片', s1: '模組的熱經籠架頂面傳到散熱片，所以它在籠架之上、不在裡面。', s2: '現代高速埠幾乎是散熱片、熱介面材料與 EMI 襯墊三件一起上' },
      { id: 'optic_module', seg: S_OPT, ax: 252, ay: 850, t: '插進去的是光模組', s1: '這張圖只畫它的外殼與拉環；內部在光通訊那一條鏈的圖裡。', s2: '另一條路是把光引擎搬到晶片旁邊（CPO），見「交換器板卡」那張' },
    ];
    const rows5 = [
      { id: 'cartridge', seg: S_CN, ax: 838, ay: 802, t: '機櫃背板：線纜匣', s1: '整櫃的互連改用成束的銅纜裝在匣子裡；托盤推進去時自動對接，', s2: '不用一條一條手插。匣裡是纜線，不是一塊實心板' },
      { id: 'guide_pin', seg: S_CN, ax: 660, ay: 838, t: '先對正，再接觸', s1: '導引柱／導引斜面比訊號接點更早接觸，把位置對正；', s2: '畫成接點先碰到，在工程上就是把接點撞壞' },
      { id: 'float_conn', seg: S_CN, ax: 724, ay: 828, t: '浮動連接器（看得出浮動間隙）', s1: '連接器本身可在小範圍內浮動，吸收整櫃累積下來的機構公差；', s2: '這是「整櫃盲插」能成立的另一半條件' },
      { id: 'recept_backplane', seg: S_CN, ax: 794, ay: 848, t: '匣體上的對接母端', s1: '托盤推到底才輪到它。上面兩條虛線就是接觸的先後順序：', s2: '粉紅＝導引柱先到，青色＝接點後到' },
    ];

    return `<svg class="dg dgm dghsio" viewBox="0 0 ${W} 1432" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（DECISIONS #231）。
           描邊與發光降一階，理由同 ic_substrate：這張圖的零件細碎
           （3 層鍍層各只有 2～4px、27 個通風孔、12 片鰭片、9 條銅纜），
           2.2px 的描邊會把它們糊成一片發光的格子 —— 那正是「螢光感太重」。
           平時不描邊 → 滑過去 1.4px → 你點的那一個 2.4px（發光交給 --dg-glow，
           柔和／沉穩／休閒三個配色本來就把它關掉）。
           前面多一個 svg 型別選擇器才壓得過 diagrams.js 的同特異性規則。*/
        svg.dghsio [data-seg] .part{stroke-width:0}
        svg.dghsio [data-seg].sel .part{stroke-width:0;filter:none}
        svg.dghsio [data-seg]:hover .part{stroke-width:1.4;filter:none}
        svg.dghsio [data-seg].sel-part .part{stroke-width:2.4;filter:var(--dg-glow,drop-shadow(0 0 5px var(--c)))}
        /* 路徑帶與對照條刻意不掛 data-seg，所以要自己給描邊與引線的 fill:none
           （diagrams.js 那兩條規則都寫在「.dg [data-seg] …」底下，吃不到）。*/
        svg.dghsio [data-part]:not([data-seg]) .part{stroke:var(--dg-part-mix);stroke-width:.9}
        svg.dghsio .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
      </style>
      <text class="ttl" x="16" y="26">連接器與高速互連：訊號為什麼寧可走線纜，也不走板子</text>
      <text class="cap" x="16" y="46">上面是訊號從 ASIC 出去的四條路（編號跟下面四格一致），下面把每一個接點切開來看。連接器賣的不是一個接頭，是電、機、熱、裝四件事。</text>

      <!-- ================= 上方：訊號路徑帶（高度 220，不到全圖 1392 的三分之一） ================= -->
      <rect class="frame" x="16" y="60" width="948" height="220" rx="9"/>
      ${band()}
      <!-- 標註全部排在板子上方那條空白帶（板子的後緣是 y=154），字一個都不壓在板子或零件上。 -->
      <g pointer-events="none">
        <path class="leader" d="M76,128 L168,176"/>
        <path class="leader" d="M236,128 L300,190"/>
        <path class="leader" d="M400,128 L474,174"/>
        <text class="lbl" x="30" y="92">ASIC／GPU</text>
        <text class="sub" x="30" y="110">只畫方塊，不畫內部</text>
        <text class="lbl" x="192" y="92">① 走板子</text>
        <text class="sub" x="192" y="110">訊號被板材吃掉</text>
        <text class="lbl" x="336" y="92">② 板邊金手指 → 插槽</text>
        <text class="sub" x="336" y="110">③ 走內部線纜，繞過板子（上面那條弧線）</text>
        <text class="lbl" x="640" y="92">④ 前面板光模組籠</text>
        <text class="lbl" x="790" y="92">⑤ 機櫃背板線纜匣</text>
        <text class="sub" x="640" y="272">青線＝高速訊號　金色＝電接點</text>
      </g>


      ${D.fold('hsio2', '② 四格細看：金手指、雙軸線、內部線纜、走板子', '卡緣金手指與母端彈片放大、雙軸線剖面、SlimSAS 與 MCIO 對接、走板子的損耗', `
      <!-- ================= 下方 2×2 四格（同一支 cell() 產生，等高等寬） ================= -->
      ${cell(0, '②', '板邊金手指與插槽（PCIe CEM）', draw2(),
      '它解決「插一張卡上去」：卡片是公端，插槽是母端。', rows2)}
      ${cell(1, '③', '內部線纜（MCIO／SlimSAS ＋ twinax）', draw3(),
      '它解決「繞過板子」：同樣兩點，改走低損耗的線。', rows3)}
      ${cell(2, '④', '前面板光模組籠（OSFP／QSFP-DD）', draw4(),
      '它解決「插光模組，還要散熱、擋電磁干擾」。', rows4)}
      ${cell(3, '⑤', '機櫃背板與盲插（cable cartridge）', draw5(),
      '它解決「整櫃盲插」：推進去就接上，不用手插。', rows5)}
      `)}

      ${D.fold('hsio3', '③ 同一段距離，四條路各花掉多少損耗預算', '四條路徑的損耗對照尺，以及資料來源與免責', `
      <!-- ================= 底部對照條 ＝ ① 的答案 ================= -->
      ${reach(16, 1208)}

      <text class="cap" x="16" y="1360">示意圖，非實物比例｜接點形狀與鍍層厚度均為示意；籠架尺寸、EMI 指片數量、twinax 的線規與阻抗、插拔次數一律不標（查不到可引用的通用值）。</text>
      <text class="cap" x="16" y="1378">距離對照（22 吋 / 4.5 吋）為單一原廠技術頁的數字，依板材、頻率與設計規則而異；本圖不寫任何市占、單價與成長率。</text>
      <text class="cap" x="16" y="1396" style="fill:var(--dg-warn)">★ 點零件篩到的是「環節」不是整個族群：「連接器 / 線材」這一格目前只收錄 3665 貿聯-KY 一家 —— 那不是壞掉。</text>
      <text class="cap" x="16" y="1414" style="fill:var(--dg-warn)">　 族群裡的 3533 嘉澤／3526 凡甲／8103 瀚荃 都還沒進供應鏈資料，所以列出來的一家不等於這四類料號的全部供應商。</text>
      `)}
    </svg>`;
  }

  window.DG.register('ai_interconnect', {
    level: 'group', chain: 'ai_server',
    name: '連接器：高速互連四個站',
    draw: connectorHsio, native: 980, scene: null,
    q: '訊號為什麼寧可用線纜也不走板子？機櫃裡的光模組籠、金手指、內部線纜、背板匣各接在哪一段？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       這張圖四個 seg 全部在 `ai_server` 鏈本籍，所以**每一個零件都點得出小卡**。
       `cos` 只放 supply_chain.json 的 companies[].id；「這家負責什麼」一律讀 companies[].tech（R3）。
       ⚠ `connector` 那一格只有貿聯一家，所以凡是掛 connector 的零件都補一句 `note`
       說清楚「這一格只收錄一家」—— 不寫的話讀者會把貿聯讀成這四類料號的供應商（R5）。 */
    parts: {
      path_band: {
        name: '訊號路徑帶：四條路的索引',
        desc: '訊號從 ASIC 出來之後必然走其中一條路到外界：走板子到板邊插槽、走內部線纜繞過板子、走到前面板的光模組、或走到機櫃背板的線纜匣。上面的編號跟下面四格一一對應。',
        none: '這一條是索引不是零件。板子、晶片、機櫃各有自己的圖。',
      },
      reach_bar: {
        name: '同一份損耗預算，能跑多遠',
        desc: '在 IEEE 802.3ck 允許的損耗上限下，低損耗雙軸線纜可達約 22 吋，而走高階板材的走線約 4.5 吋。這就是「線纜取代板子」的全部理由，也連帶省掉耗電的中繼器（retimer）與 PCB 層數。',
        note: '⚠ 這組數字只有**一個**來源（連接器原廠自己的技術頁），而且前提是特定高階板材與特定損耗上限。它是這張圖的核心論據，但不是通則 —— 依板材、頻率與設計規則而異。',
        none: '這是一把比較用的尺，不是零件。',
      },
      // ---- 格 ②
      card_edge: {
        name: '介面卡的板邊',
        desc: '插進插槽的那一段板子。這張圖只畫板邊那一小段 —— 板子本身的疊構與層數是「PCB 硬板剖面」與「交換器板卡」那兩張的主題。',
        items: ['高階 CCL'],
      },
      gold_finger: {
        name: '金手指（硬金鍍層）',
        desc: '由內到外是銅 → 鎳阻障 → 硬金。硬金是為了耐插拔磨損，不是為了導電，所以它比底下的鎳層薄得多。金手指是公端、插槽是母端，標反了整格就錯了。',
        note: '⚠ 新一代改用 PAM4 調變之後，金手指的長度規格也跟著改。查到的兩組數字沒有對到 PCI-SIG 官方規範原文，所以圖上只寫方向、不寫 mm。',
      },
      chamfer: {
        name: '金手指的倒角',
        desc: '板邊前端的斜切。沒有倒角，插進去會把母端彈片刮壞 —— 倒角是讓彈片順著斜面被推開的那一段。',
      },
      slot_housing: {
        name: '插槽本體（母端絕緣殼）',
        desc: '深色塑膠殼，中間有防呆隔條。卡緣連接器這一類的接點間距是 1.0 mm 等級。',
        note: '⚠「連接器 / 線材」這一格目前只收錄 3665 貿聯-KY 一家；族群裡的 3533 嘉澤（CPU／記憶體插槽）、3526 凡甲、8103 瀚荃 都還沒進供應鏈資料。列出來的一家不等於這一類料號的全部供應商。',
      },
      slot_beam: {
        name: '插槽裡的彈片接點（被撐開）',
        desc: '公端插入時把母端彈片撐開，由此產生法向力；插拔時接點擦過金手指表面把氧化層刮掉。鍍金可以用比較小的法向力，鍍錫會氧化所以要大得多 —— 這就是為什麼高速料號幾乎都鍍金。',
        note: '⚠ 法向力的公克數是原廠的慣用值不是規範值，所以畫面上只寫「比較小／大得多」，不寫數字。',
      },
      slot_leg: {
        name: '彈片的焊腳／壓接腳',
        desc: '把插槽固定並接到主板的那一排。它決定這個連接器是焊上去的還是壓進去的。',
      },
      beam_zoom: {
        name: '放大：法向力與擦拭是兩個方向',
        desc: '法向力垂直於接觸面（所以叫「法向」），擦拭行程平行於插入方向。兩支箭頭畫成同方向就是把接觸物理講錯了 —— 接點是機械問題，不是電氣問題。',
      },
      // ---- 格 ③
      cable_plug: {
        name: '線纜連接器的公端',
        desc: '伺服器裡常見兩種內部線纜介面：SlimSAS（接腳定義在 SFF-8654，常見 4 通道與 8 通道）與 MCIO（定義在 SFF-TA-1016，footprint 更小、支援的通道組合更多）。',
        note: '⚠「連接器 / 線材」這一格目前只收錄一家（見上）。台廠各自做哪一種料號，這次查不到逐家逐料號的可引用揭露，所以圖上不寫任何公司與料號的對應。',
      },
      cable_body: {
        name: '線纜本體（一束 twinax）',
        desc: '一束低損耗雙軸線。用它取代板子上的走線，訊號就不必被板材吃掉 —— 底下那條尺比的就是這件事。',
      },
      twinax: {
        name: '一對雙軸線（twinax）的橫剖面',
        desc: '由內到外是導體 → 介電 → 遮蔽 → 外被。關鍵是**兩根等徑導體並排、共用同一層接地遮蔽**：遮蔽擋外來干擾，也讓這一對的阻抗穩定。畫成單根同軸就變成另一種線了。',
        note: '⚠ twinax 的線規（AWG）、阻抗值、每公尺損耗這次查不到可引用的通用值（查到的是特定料號的規格，不能當通則），所以剖面只畫層次、不標數字。',
      },
      cable_recept: {
        name: '板上的對接母座',
        desc: 'MCIO 的 38 針對應 4 通道、74 針對應 8 通道，124 針的變種對應 x16。針數本身就是「這條線能帶幾條通道」的直接指標。',
      },
      pcb_route: {
        name: '對照：同樣兩點改走板子',
        desc: '同樣兩點之間，走板子要多花掉一大段損耗預算。畫成虛線是因為它在這張圖裡是「另一條路」，不是主角。板子的疊構與層數請看「PCB 硬板剖面」。',
      },
      // ---- 格 ④
      cage_body: {
        name: '光模組籠（cage）本體',
        desc: '鈑金折出來的盒子，盒身要有通風孔 —— 沒有通風孔就不叫籠。所有籠都用壓接（press-fit）方式固定在板上，而且可以背對背（belly-to-belly）雙面安裝。',
        note: '⚠「連接器 / 線材」這一格目前只收錄一家（見上）。籠架的實際尺寸與 EMI 指片數量查不到可引用的數值，所以只畫結構、不標 mm、不數指片。',
      },
      cage_pressfit: {
        name: '籠架的壓接針腳（press-fit）',
        desc: '魚眼形的針腳壓進板上的孔裡，靠過盈量咬住 —— 不是焊上去的。壓接讓籠架可以在不動迴焊爐的情況下裝配與更換。',
      },
      emi_finger: {
        name: 'EMI 指片（彈性金屬指）',
        desc: '圍在開口四周、朝向模組的一圈彈性金屬指。模組插進來時被壓住，把模組與盒子之間的縫隙封起來，擋住電磁干擾外洩與埠間串擾。',
      },
      cage_hs: {
        name: '騎在籠子上的散熱片（riding heat sink）',
        desc: '熱是從模組經籠架頂面傳到散熱片的，所以散熱片在籠架之上、不在籠架裡也不在模組裡，並用夾持彈簧壓住。現代高速埠幾乎是散熱片、熱介面材料與連續彈性體 EMI 襯墊三件一起上。',
      },
      optic_module: {
        name: '插進去的光模組（只有外殼與拉環）',
        desc: '這張圖只畫模組的外殼與拉環；它自己的內部（雷射、透鏡、光纖耦合）在光通訊那一條鏈的圖裡。另一條路是把光引擎搬到晶片旁邊（CPO），那是「交換器板卡」那張的主題。',
      },
      belly: {
        name: '背對背（belly-to-belly）',
        desc: '同一個位置板子上下各一個籠、互為鏡像、共用同一塊板 —— 前面板才塞得下更多埠。',
      },
      // ---- 格 ⑤
      cartridge: {
        name: '機櫃背板：線纜匣（cable cartridge）',
        desc: '整櫃的互連改用成束的銅纜裝在匣子裡，托盤推進去時自動對接，不用一條一條手插。匣子裡是纜線，不是一塊實心背板 —— 那正是「線纜背板」這個名字的由來。',
        note: '⚠ 常被引用的「幾條銅纜、幾英里、幾 TB/s」那組數字，主要出處是社群貼文與轉述文章，官方文件只確認「被動銅纜線匣背板」這個結構。所以這張圖只畫結構，一個數量與頻寬數字都不寫。',
      },
      float_conn: {
        name: '托盤後方的浮動連接器',
        desc: '連接器本身可以在小範圍內浮動（圖上外框與本體之間那條縫就是浮動間隙），吸收整櫃累積下來的機構公差。這是「整櫃盲插」能成立的另一半條件。',
      },
      guide_pin: {
        name: '導引柱／導引斜面',
        desc: '比訊號接點更早接觸，先把位置對正，接點才不會撞壞。圖上兩條虛線就是先後順序：導引柱先到、接點後到。',
        note: '⚠ 低信心：這次**查不到明確的規範條文**，只有「高精度浮動連接器、托盤推進去自動咬合」這類描述。圖上照畫是因為那是盲插能成立的必要條件，但不標任何長度差與公差數字。',
      },
      recept_backplane: {
        name: '匣體上的對接母端',
        desc: '托盤推到底才輪到它接觸。整個盲插的順序是：導引柱對正 → 浮動連接器在間隙內自我修正 → 最後才是訊號接點接觸。',
      },
    },
  });
})();
