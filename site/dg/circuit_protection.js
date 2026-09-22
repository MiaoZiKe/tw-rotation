/* 被動保護：過流與過壓元件 —— docs/diagram_plan_electronics.md 的 E3
   （族群 `resistor_protect`，electronics 鏈）

   合約＝`docs/diagram_specs/circuit_protection.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的幾件事：

     · §0-A **不做真 3D**（`scene: null`）。串／並是電路拓樸不是空間形狀；
       晶粒與晶界、碳黑鏈、PN 接面全部是剖面上的圖案。規格書寫死「沒有任何條件
       該回頭加 3D」—— 要加就是改規格書、重新簽。
     · §0-B 這張圖存在的理由：`resistor_protect` 的 6 檔裡有 **4 檔**做的是保護元件，
       而既有的「被動元件：電感・電阻・石英」那張**一格都沒有**。
       所以這張圖**不准畫**晶片電阻的三明治、雷射修整溝、電感的磁粉與繞線、石英的密封腔。
     · §3-A T1／T2（兩條紅線）**擋電壓的並聯、擋電流的串聯**。
       實作上用**兩支不同的繪製函式** `shunt()` 與 `series()`：
       `shunt()` 一定生兩條腿（一條上主線、一條下接地）、`series()` 一定生一條穿過元件的主線
       而且**不生任何接地腿**。不是同一支函式用參數切換 —— 那最容易在複製貼上時把接線畫反。
     · §3-B T3（紅線）**MOV 必須比 TVS 更靠外部端子**。元件位置寫在一個陣列裡、
       照順序 forEach 排 —— 順序改不壞。
     · §3-C T6（紅線）**MOV 必須畫出晶粒與晶界**。非線性完全來自晶界，
       畫成一塊均質陶瓷方塊就不是 MOV。晶粒用抖動格點算出來，不是一顆一顆手畫。
     · §3-D T10（紅線）**跳脫格：鏈斷開 ＋ 高分子層明顯變厚**。
       兩格共用同一支 `pptcCell()`，只換「高分子厚度」與「鏈的斷點數」兩個參數，
       而且 **1.4 倍是真的乘出來的**，不是目測。
     · §7-D2（紅線）**每一個零件的 `cos` 一律寫空陣列** —— `passive_comp` 的預設成員是
       做 MLCC 與晶片電阻的，列出來就是**錯的答案，不是不完整的答案**。
       公司名寫在 `none:` 的整句話裡。

   一個實作上的取捨
   ------------------
   **並聯與串聯不靠顏色區分，靠接線畫法區分。** 休閒配色會把顏色差異壓掉
   （`--dg-glow:none`、色相整體轉暖），所以「並聯有兩條腿接到地、串聯主線從中間穿過」
   這個差異必須在**幾何**上成立，不是在色票上成立。§8 的驗收條件就是這樣寫的。

   顏色一律走既有的 `--dg-*`（新增的七個材質 token 加在 index.html 的 :root，
   而且全部是既有 token 的 color-mix）。JS 裡一個色碼都沒有。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;

  const W = 980, SEG = 'passive_comp';

  /* ================================================================ 小工具 */
  const f1 = (v) => (+v).toFixed(1);
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const C = (cx, cy, r, fill, cls) =>
    `<circle${cls ? ` class="${cls}"` : ''} cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}" fill="${fill}"/>`;
  const PA = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const LN = (d, col, w2, cls, extra) =>
    `<path${cls ? ` class="${cls}"` : ''} d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${f1(x)}" y="${f1(y)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;
  const part = (id, inner) => `<g data-part="${id}" data-seg="${SEG}">${inner}</g>`;
  // 向右的箭頭（主線）：頂點一定在右邊，所以「箭頭方向」量得出來
  const arrR = (x, y) => PA(`M${f1(x + 7)},${f1(y)} L${f1(x)},${f1(y - 4)} L${f1(x)},${f1(y + 4)} Z`,
    'var(--dg-accent-2d)', 'cparrh');

  /* ================================================================ 區 ① 防護路徑帶
     §3-A／§3-B：由左到右 外部端子 → MOV／GDT（第一道，並聯）→ NTC → PPTC（串聯）
     → TVS／ESD（第二道，並聯，最靠近 IC）→ IC。 */
  const LY = 130, GY = 200, LX0 = 84, LX1 = 876;    // 主線 y ／ 接地線 y ／ 主線左右端

  /* 並聯元件：★ 一定有兩條腿 —— 一條接主線、一條接地，主線從它旁邊繼續往右走。 */
  function shunt(id, cx, w, title, fill, inner) {
    const x0 = cx - w / 2, y0 = 148, h = 34;
    return part(id, R(x0, y0, w, h, fill, 'part cpbody', 4)
      + (inner || '')
      + LN(`M${cx},${LY} L${cx},${y0}`, 'var(--dg-steel)', 2.2, 'cpleg')
      + LN(`M${cx},${y0 + h} L${cx},${GY}`, 'var(--dg-steel)', 2.2, 'cpleg')
      + C(cx, LY, 3.2, 'var(--dg-accent-2d)', 'cpnode')
      + `<g pointer-events="none">${T(cx, y0 + 21, title, 'lbl', 'middle')}</g>`);
  }

  /* 串聯元件：★ 主線從中間穿過（左進右出），而且**沒有接地腿**。 */
  function series(id, cx, w, title, fill, inner) {
    const x0 = cx - w / 2, y0 = LY - 17, h = 34;
    return part(id, R(x0, y0, w, h, fill, 'part cpbody', 4)
      + (inner || '')
      + LN(`M${x0},${LY} L${x0 + w},${LY}`, 'var(--dg-accent-2d)', 2.2, 'cpthru')
      + `<g pointer-events="none">${T(cx, y0 - 6, title, 'lbl', 'middle')}</g>`);
  }

  /* 元件位置寫在陣列裡、照順序排 —— T3（MOV 比 TVS 更靠外）因此自動成立。 */
  const PATH = [
    { id: 'cp_mov', kind: 'shunt', cx: 200, w: 84, t: '壓敏電阻 MOV' },
    { id: 'cp_gdt', kind: 'shunt', cx: 306, w: 84, t: '氣體放電管 GDT' },
    { id: 'cp_ntc', kind: 'series', cx: 442, w: 92, t: '熱敏電阻 NTC' },
    { id: 'cp_pptc', kind: 'series', cx: 576, w: 108, t: '自恢復保險絲 PPTC' },
    { id: 'cp_tvs', kind: 'shunt', cx: 736, w: 96, t: 'TVS／ESD 陣列' },
  ];

  function pathBand() {
    const g = [];
    // 主線（一條貫穿全帶，由左到右）＋ 接地線（一條，所有並聯元件都掛在同一條上）
    g.push(LN(`M${LX0},${LY} L${LX1},${LY}`, 'var(--dg-accent-2d)', 2.6, 'cpline'));
    g.push(part('cp_line', R(LX0, LY - 3, LX1 - LX0, 6, 'transparent', 'part')));
    g.push(part('cp_gnd', LN(`M${LX0 + 40},${GY} L${LX1 - 60},${GY}`, 'var(--dg-steel)', 2.6, 'cpgnd')
      + LN(`M${LX0 + 52},${GY + 6} L${LX0 + 76},${GY + 6}`, 'var(--dg-steel)', 2.2, 'cpgndsym')
      + LN(`M${LX0 + 58},${GY + 11} L${LX0 + 70},${GY + 11}`, 'var(--dg-steel)', 2.2, 'cpgndsym')
      + `<g pointer-events="none">${T(LX0 + 84, GY + 12, '接地（所有並聯元件都掛在同一條上）', 'sub')}</g>`));
    // 主線上的方向箭頭：一律向右（外 → 內）
    [140, 372, 512, 664, 820].forEach((x) => { g.push(arrR(x, LY)); });
    // 外部端子（不是任何真實接頭的外觀 —— 只是兩個接點符號）
    g.push(part('cp_term', R(40, LY - 20, 44, 40, 'var(--dg-mc-case)', 'part', 4)
      + C(58, LY - 9, 4, 'var(--dg-cp-gb)', 'part') + C(58, LY + 9, 4, 'var(--dg-cp-gb)', 'part')
      + LN(`M62,${LY - 9} L84,${LY - 9}`, 'var(--dg-steel)', 1.6)
      + LN(`M62,${LY + 9} L84,${LY + 9}`, 'var(--dg-steel)', 1.6)
      + `<g pointer-events="none">${T(40, LY - 28, '外部端子', 'sub')}</g>`));
    // 五個元件
    PATH.forEach((p) => {
      g.push(p.kind === 'shunt'
        ? shunt(p.id, p.cx, p.w, p.t, 'var(--dg-mc-case)')
        : series(p.id, p.cx, p.w, p.t, 'var(--dg-mc-case)'));
    });
    // IC（被保護的對象；不是任何真實晶片的外觀）
    g.push(part('cp_ic', R(876, LY - 22, 64, 44, 'var(--dg-cp-n)', 'part', 4)
      + [0, 1, 2].map((i) => R(870, LY - 12 + i * 12, 6, 4, 'var(--dg-cp-gb)', 'part')).join('')
      + [0, 1, 2].map((i) => R(940, LY - 12 + i * 12, 6, 4, 'var(--dg-cp-gb)', 'part')).join('')
      + `<g pointer-events="none">${T(908, LY + 4, 'IC', 'lbl', 'middle')}</g>`));
    // 兩道防護的分界說明
    g.push(LN('M362,96 L362,214', 'var(--dg-frame-s)', 1, null, ' stroke-dasharray="5 5"'));
    g.push(T(92, 92, '第一道（靠外，擋大能量）：並聯到地', 'sub', null, 'fill:var(--dg-accent-2d)'));
    g.push(T(374, 92, '過流那一側：串在線上', 'sub', null, 'fill:var(--dg-accent-2d)'));
    g.push(LN('M644,96 L644,214', 'var(--dg-frame-s)', 1, null, ' stroke-dasharray="5 5"'));
    g.push(T(656, 92, '第二道（靠近 IC，把電壓壓得更低）：並聯到地', 'sub', null, 'fill:var(--dg-accent-2d)'));
    return g.join('');
  }

  /* ================================================================ 區 ② ① PPTC 剖面
     §2-B：鎳電極箔 ×2 夾住高分子基體，裡面是串成鏈的導電碳黑粒子，外面包一層絕緣。
     兩格對照（常溫／跳脫）共用這一支，只換 `polyH` 與 `breaks` 兩個參數 —— T11 自動成立。 */
  const PP_BASE = 40;

  function pptcCell(x0, yTop, polyH, breaks, wid) {
    const g = [], w = wid || 190, NI = 8, INS = 8;
    const yIns0 = yTop, yNi0 = yTop + INS, yP0 = yNi0 + NI, yP1 = yP0 + polyH;
    const yNi1 = yP1, yIns1 = yNi1 + NI;
    g.push(part('cp_ins', R(x0, yIns0, w, INS, 'var(--dg-resin)', 'part')
      + R(x0, yIns1, w, INS, 'var(--dg-resin)', 'part')));
    g.push(part('cp_ni', R(x0, yNi0, w, NI, 'var(--dg-ni)', 'part cpni')
      + R(x0, yNi1, w, NI, 'var(--dg-ni)', 'part cpni')));
    g.push(part('cp_poly', R(x0, yP0, w, polyH, 'var(--dg-cp-poly)', 'part cppoly')));
    // 導電碳黑：四條鏈。常溫＝連通（一條 path 貫穿上下電極）；跳脫＝同樣的點，鏈被拉斷
    const chains = [];
    for (let k = 0; k < 4; k++) {
      const cx = x0 + w * (k + 0.5) / 4, pts = [];
      const n = 7;
      for (let i = 0; i <= n; i++) {
        pts.push([cx + Math.sin(i * 1.7 + k * 2.1) * (w / 14), yP0 + polyH * i / n]);
      }
      if (!breaks) {
        chains.push(LN('M' + pts.map((p) => `${f1(p[0])},${f1(p[1])}`).join('L'),
          'var(--dg-cp-carbon)', 2, 'cpchain'));
      } else {
        // ★ 斷鏈：同一組點，中間拿掉一段 —— 上下兩截都不再貫穿
        chains.push(LN('M' + pts.slice(0, 3).map((p) => `${f1(p[0])},${f1(p[1])}`).join('L'),
          'var(--dg-cp-carbon)', 2, 'cpchain'));
        chains.push(LN('M' + pts.slice(5).map((p) => `${f1(p[0])},${f1(p[1])}`).join('L'),
          'var(--dg-cp-carbon)', 2, 'cpchain'));
      }
      pts.forEach((p) => { chains.push(C(p[0], p[1], 2.4, 'var(--dg-cp-carbon)', 'part cpdot')); });
    }
    g.push(part('cp_carbon', chains.join('')));
    return { svg: g.join(''), y1: yIns1 + INS };
  }

  /* ================================================================ 區 ② ③ MOV 晶粒剖面
     §3-C（T6，紅線）：一堆大小不一的多邊形晶粒 ＋ 晶粒之間的晶界線。
     晶粒用「抖動格點」算出來（不是一顆一顆手畫），所以數量與大小差異都是真的。 */
  const MV_COLS = 10, MV_ROWS = 4;

  function movGrains(x0, x1, y0, y1) {
    const P = [];
    for (let r = 0; r <= MV_ROWS; r++) {
      const row = [];
      for (let c = 0; c <= MV_COLS; c++) {
        const edge = (r === 0 || r === MV_ROWS || c === 0 || c === MV_COLS);
        const jx = edge ? 0 : Math.sin(r * 7.3 + c * 3.1) * 0.34;
        const jy = (r === 0 || r === MV_ROWS) ? 0 : Math.cos(r * 4.7 + c * 5.9) * 0.34;
        row.push([x0 + (x1 - x0) * ((c + jx) / MV_COLS), y0 + (y1 - y0) * ((r + jy) / MV_ROWS)]);
      }
      P.push(row);
    }
    const cells = [], mid = [];
    for (let r = 0; r < MV_ROWS; r++) {
      for (let c = 0; c < MV_COLS; c++) {
        const q = [P[r][c], P[r][c + 1], P[r + 1][c + 1], P[r + 1][c]];
        cells.push(PA('M' + q.map((p) => `${f1(p[0])},${f1(p[1])}`).join('L') + 'Z',
          'var(--dg-cp-grain)', 'part cpgrain'));
        mid.push([(q[0][0] + q[2][0]) / 2, (q[0][1] + q[2][1]) / 2]);
      }
    }
    // 電流折線：從上電極往下走，**每一步跨進一顆新的晶粒**（跨界次數是真的算出來的）
    const route = [[0, 1], [0, 2], [1, 2], [1, 3], [2, 3], [2, 4], [3, 4], [3, 5]];
    const via = route.map((rc) => mid[rc[0] * MV_COLS + rc[1]]);
    const d = `M${f1(via[0][0])},${f1(y0)} L` + via.map((p) => `${f1(p[0])},${f1(p[1])}`).join('L')
      + ` L${f1(via[via.length - 1][0])},${f1(y1)}`;
    return {
      svg: part('cp_grain', cells.join(''))
        + part('cp_gb', LN(d, 'var(--dg-accent-2d)', 2, 'cppath', ' stroke-dasharray="5 4"')),
      cross: route.length - 1,
    };
  }

  /* ================================================================ 區 ② 四格剖面 */
  function cells() {
    const g = [];
    // ① PPTC
    const p = pptcCell(46, 292, PP_BASE, 0);
    g.push(p.svg);
    g.push(part('cp_pptc', R(40, 286, 202, p.y1 - 280, 'transparent', 'part')));
    // ② NTC：陶瓷本體 ＋ 兩個相對面電極 ＋ 引線 —— 沒有 PN 接面、沒有晶界網（V2）
    g.push(part('cp_ntc', R(300, 300, 130, 56, 'var(--dg-cer-cut)', 'part cpntcbody', 3)
      + R(300, 292, 130, 8, 'var(--dg-ni)', 'part cpntcel')
      + R(300, 356, 130, 8, 'var(--dg-ni)', 'part cpntcel')
      // 引線兩根：★ 上緣停在 284、下緣停在 368 —— 上面是格子標題（bbox 到 277）、
      //   下面是說明文字（bbox 從 370 開始）。字壓在零件上排版體檢抓不到，所以這裡自己算。
      + R(358, 284, 14, 16, 'var(--dg-steel)', 'part')
      + R(358, 356, 14, 12, 'var(--dg-steel)', 'part')));
    // ③ MOV：晶粒 ＋ 晶界 ＋ 電流折線 ＋ 兩個相對面電極
    const mv = movGrains(512, 706, 302, 350);
    g.push(part('cp_movel', R(512, 292, 194, 10, 'var(--dg-ni)', 'part cpmovel')
      + R(512, 350, 194, 10, 'var(--dg-ni)', 'part cpmovel')));
    g.push(mv.svg);
    // ④ TVS：P 區 ／ 空乏區 ／ N 區 ＋ 上下金屬電極
    g.push(part('cp_tvs', R(750, 288, 190, 8, 'var(--dg-ni)', 'part cptvsel')
      + R(750, 354, 190, 8, 'var(--dg-ni)', 'part cptvsel')));
    g.push(part('cp_pn', R(750, 296, 190, 26, 'var(--dg-cp-p)', 'part cpp')
      + R(750, 322, 190, 6, 'var(--dg-cp-depl)', 'part cpdepl')
      + R(750, 328, 190, 26, 'var(--dg-cp-n)', 'part cpn')));
    return g.join('');
  }

  /* ================================================================ 第 ① 段：PPTC 跳脫前後
     §3-D（T10，紅線）：同一張圖，鏈斷開 ＋ 高分子層**明顯變厚**。
     ★ 1.4 倍是真的乘出來的（`PP_BASE * 1.4`），不是目測；畫面上不寫這個數字
       —— 那是畫圖用的下限，不是事實宣稱（§7-C2）。 */
  function foldTrip(y0) {
    const g = [];
    let y = y0 + 22;
    g.push(T(28, y, 'PPTC 跳脫前後長什麼樣：兩格同一個比例尺、同一套材質色，只有兩件事不同', 'hd'));
    y += 20;
    g.push(T(28, y, '① 導電碳黑粒子的鏈斷開了　② 高分子層明顯變厚（體積膨脹）。只畫「變紅」不畫「變厚＋斷鏈」＝沒有解釋機制。', 'sub'));
    const AY = y + 28;                                // ＋28 ＝ 上面那行 sub 的 bbox（15px）留得下
    const a = pptcCell(60, AY, PP_BASE, 0, 330);
    const b = pptcCell(560, AY, PP_BASE * 1.4, 1, 330);
    g.push(a.svg, b.svg);
    g.push(T(60, AY - 4, '常溫：碳黑粒子連成貫穿上下電極的通路 → 幾乎不擋路', 'sub'));
    g.push(T(560, AY - 4, '過流發熱：高分子膨脹，鏈被拉斷 → 變成高阻，把路切斷', 'sub'));
    const yb = Math.max(a.y1, b.y1) + 20;
    g.push(T(28, yb, '冷了之後高分子縮回去、鏈重新接上 —— 這就是「自恢復」。本圖不寫膨脹的百分比與正常態電阻值（查不到共通值）。', 'sub'));
    g.push(T(28, yb + 17, '★ 台股做 PPTC 的是 6224 聚鼎（PPTC 保護元件）與 6642 富致（PPTC 過電流保護元件）。本圖不區分兩家的技術差異 —— 查不到就不編。', 'sub', null, 'fill:var(--dg-warn)'));
    return { svg: g.join(''), h: yb + 17 - y0 + 16 };
  }

  /* 第 ② 段：這一格的台股站在哪一類 */
  const WHO = [
    ['壓敏電阻（MOV）與 NTC 熱敏電阻', '2428 興勤（NTC 熱敏電阻、壓敏電阻與保護元件）—— 兩類都做，所以它同時指到本圖的兩格'],
    ['TVS／ESD 過電壓保護元件', '6284 佳邦（ESD／TVS 等過電壓保護元件）'],
    ['PPTC 自恢復保險絲', '6224 聚鼎（PPTC 保護元件）、6642 富致（PPTC 過電流保護元件）。★ 本圖不區分兩家的技術差異'],
    ['★ 做的是電阻、不是保護元件', '3624 光頡（薄膜與厚膜高精密電阻）、2478 大毅（晶片電阻）—— 它們的剖面在「被動元件：電感・電阻・石英」那張'],
    ['氣體放電管（GDT）', '本圖查不到台股對應 —— 查不到就寫查不到，不編一個對應'],
  ];

  function foldWho(y0) {
    const g = [];
    let y = y0 + 22;
    g.push(T(28, y, '這一格的台股站在哪一類（6 家：4 家做保護元件、2 家做電阻）', 'hd'));
    WHO.forEach((r, i) => {
      y += 20;
      g.push(part('cp_who' + i, R(24, y - 14, 932, 19, 'transparent', 'part')
        + `<g pointer-events="none">${T(30, y, r[0] + '｜' + r[1], 'sub',
          null, i === 3 ? 'fill:var(--dg-warn)' : '')}</g>`));
    });
    y += 26;
    g.push(T(28, y, '★ 這 6 檔用代號 grep 整份 supply_chain.yaml，一檔都沒有出現；而這張圖掛得上的環節只有「被動元件」一格，它底下', 'sub', null, 'fill:var(--dg-warn)'));
    y += 17;
    g.push(T(28, y, '　 的 5 家（國巨、華新科、凱美、禾伸堂、信昌電）沒有一家在這個族群裡 —— 它們做的是 MLCC 與晶片電阻。', 'sub', null, 'fill:var(--dg-warn)'));
    y += 17;
    g.push(T(28, y, '　 所以這張圖每一個零件的公司清單都刻意留空、改用文字回答 —— 走環節預設會給出錯的答案，不是不完整的答案。', 'sub', null, 'fill:var(--dg-warn)'));
    y += 24;
    g.push(part('cp_res_ref', R(24, y - 15, 932, 38, 'transparent', 'part')
      + `<g pointer-events="none">${T(30, y, '指路用的一格：晶片電阻的三明治（基板／電阻膜／保護層／端電極）與雷射修整溝、電感的磁粉與繞線、石英的密封腔，', 'sub')}`
      + `${T(30, y + 17, '　全部在「被動元件：電感・電阻・石英」那張 —— 本圖一格都不畫。', 'sub')}</g>`));
    y += 38;
    g.push(T(28, y, '★ 6224 聚鼎的 CLM 用於 BBU 電池模組與伺服器電源保護（信心 reported）—— 本圖畫的是通用電路，主圖不指定用途，只在這裡列一句。', 'sub'));
    return { svg: g.join(''), h: y - y0 + 16 };
  }

  /* ================================================================ 版面
     收合時：標題 ＋ 兩排圖 ＋ 四行誠實性標示 ＋ 兩條章節列 ＝ **644px**（上限 700）。*/
  function circuitProtection() {
    const S1 = 552;
    const p1 = foldTrip(S1 + 46);
    const S2 = S1 + 46 + p1.h;
    const p2 = foldWho(S2 + 46);
    const H = S2 + 46 + p2.h + 16;
    return `<svg class="dg dgm dgcp dg1" viewBox="0 0 ${W} ${H}" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（DECISIONS #231）。
           這裡只補 diagrams.js 沒有的幾件：晶界線、接地符號的線帽、碳黑鏈的線帽。
           ★ 晶界是這張圖的識別特徵 —— 它必須是**線**，不是兩塊顏色的交界，
             不然休閒配色把色差壓掉之後就看不見了。顏色一律走 --dg-*。*/
        svg.dgcp .cpgrain{stroke:var(--dg-cp-gb);stroke-width:1.1;stroke-linejoin:round}
        svg.dgcp .cpchain{stroke-linecap:round}
        svg.dgcp .cpgnd,svg.dgcp .cpgndsym{stroke-linecap:round}
        svg.dgcp .cppath{stroke-linecap:round}
        svg.dgcp .cpnode{stroke:none}
      </style>
      ${T(16, 22, '被動保護：過流與過壓元件', 'ttl')}
      ${T(16, 40, '擋電壓的並聯、擋電流的串聯 —— 位置不一樣，因為工作方式根本不同。底下兩段預設收起來，按標題列就打得開。', 'cap')}

      <!-- ================= ① 防護路徑帶（這張圖的主角） ================= -->
      ${frame(16, 48, 948, 202)}
      ${T(28, 66, '① 一條線從外面走進晶片，中間被幾個零件擋過（由左到右＝由外到內，箭頭一律向右）', 'hd')}
      ${pathBand()}
      ${T(28, 234, '★ 並聯（MOV／GDT／TVS）＝兩條腿：一條接主線、一條接地。★ 串聯（NTC／PPTC）＝主線從中間穿過、沒有接地腿。', 'sub', null, 'fill:var(--dg-warn)')}

      <!-- ================= ② 四種元件剖面（同一個外框尺寸、同一套材質色） ================= -->
      ${frame(16, 256, 948, 204)}
      <path d="M253,266 L253,452" stroke="var(--dg-frame-s)" stroke-width="1" fill="none"/>
      <path d="M490,266 L490,452" stroke="var(--dg-frame-s)" stroke-width="1" fill="none"/>
      <path d="M727,266 L727,452" stroke="var(--dg-frame-s)" stroke-width="1" fill="none"/>
      ${T(28, 274, '① PPTC 自恢復保險絲（串聯）', 'hd')}
      ${T(265, 274, '② NTC 熱敏電阻（串聯）', 'hd')}
      ${T(502, 274, '③ 壓敏電阻 MOV（並聯）', 'hd')}
      ${T(739, 274, '④ TVS／ESD（並聯）', 'hd')}
      ${cells()}
      ${T(28, 382, '鎳電極箔 ×2 夾住高分子基體，', 'sub')}
      ${T(28, 398, '外面包一層絕緣。裡面的黑點是', 'sub')}
      ${T(28, 414, '導電碳黑，常溫時連成通路。', 'sub')}
      ${T(28, 430, '★ 擋的是過大的電流，冷了會自己', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(28, 446, '　 接回來 —— 跳脫前後見第 ① 段。', 'sub')}
      ${T(265, 382, '金屬氧化物燒結的陶瓷本體 ＋', 'sub')}
      ${T(265, 398, '兩個相對面的電極 ＋ 兩根引線。', 'sub')}
      ${T(265, 414, '沒有 PN 接面，也沒有晶界網 ——', 'sub')}
      ${T(265, 430, '★ 它擋的是開機瞬間的湧浪電流，', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(265, 446, '　 不是突波電壓。那是兩件事。', 'sub')}
      ${T(502, 382, '★ 一堆大小不一的 ZnO 晶粒，', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(502, 398, '　 電流被擋住的地方是晶粒之間的', 'sub')}
      ${T(502, 414, '　 界面（晶界），一顆裡面有數以', 'sub')}
      ${T(502, 430, '　 百萬計個。畫成一塊均質陶瓷就', 'sub')}
      ${T(502, 446, '　 不是 MOV。晶粒大小數量為示意。', 'sub')}
      ${T(739, 382, '半導體 PN 接面：P 區／空乏區／', 'sub')}
      ${T(739, 398, 'N 區 ＋ 上下金屬電極。電壓超過', 'sub')}
      ${T(739, 414, '門檻就崩潰導通，把能量吃掉。', 'sub')}
      ${T(739, 430, '★ 擺在最靠近 IC 的地方，把電壓', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(739, 446, '　 壓得比壓敏電阻更低、漂移更小。', 'sub')}

      ${T(16, 476, '★ 誰做的：壓敏電阻與 NTC 2428 興勤（兩類都做）；TVS／ESD 6284 佳邦；PPTC 6224 聚鼎與 6642 富致 —— 逐家見第 ② 段。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 492, '★ 晶片電阻與精密電阻（3624 光頡、2478 大毅）見「被動元件：電感・電阻・石英」那張；本圖一格都不畫它們的結構。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 508, '本圖的四類元件，目前一家台股都不在供應鏈資料的環節裡，所以公司用文字列在零件小卡與第 ② 段，下方的「環節色標」篩不到它們。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 524, '示意圖，非實物比例。晶粒、碳黑顆粒的大小與數量都是示意；本圖不寫鉗位電壓、通流容量、動作電流、壽命次數、市占率與營收數字。', 'cap')}
      ${T(16, 540, '公司角色取自板塊成分股證據表，信心標示見該表。壓敏電阻每擋一次就退化一點、最後通常以短路收場；TVS 在額定脈衝下漂移很小（信心：中，單一比較型來源）。', 'cap')}

      <!-- ================= ① PPTC 跳脫前後（預設收合） ================= -->
      ${D.foldBar('cp1', S1, '① PPTC 跳脫前後長什麼樣（2 格對照）',
      '同一個比例尺的兩格：導電鏈連通 → 膨脹斷鏈，以及為什麼它會自己恢復')}
      <g class="dgbody" data-fold="cp1" data-y0="${S1 + 46}" data-y1="${S1 + 46 + p1.h}">
        ${p1.svg}
      </g>

      <!-- ================= ② 台股站在哪一類（預設收合） ================= -->
      ${D.foldBar('cp2', S2, '② 這一格的台股站在哪一類（6 家）',
      '4 家做保護元件、2 家做電阻（在別張圖），以及為什麼這張圖的公司清單一律留空')}
      <g class="dgbody" data-fold="cp2" data-y0="${S2 + 46}" data-y1="${S2 + 46 + p2.h}">
        ${p2.svg}
      </g>
    </svg>`;
  }

  /* ================================================================ 零件小卡（§7-E）
     ★ D2（紅線）：**每一個零件的 `cos` 一律是空陣列**。
       `passive_comp` 的預設成員是做 MLCC 與晶片電阻的，列出來就是錯的答案。
       空陣列會讓 `renderPartCard()` 走 `none:` 那一支，把我們寫的整句話印出來。 */
  const N_MOV = '★ 壓敏電阻（MOV）在台股由 2428 興勤（NTC 熱敏電阻、壓敏電阻與保護元件）做。興勤不在 supply_chain.yaml 裡，所以這張小卡的「做這個的台股」欄列不出它 —— 這裡用文字補。信心：reported（產業媒體）。';
  const N_PPTC = '★ PPTC 自恢復保險絲在台股由 6224 聚鼎（PPTC 保護元件）與 6642 富致（PPTC 過電流保護元件）做。兩家都不在 supply_chain.yaml 裡。本圖不區分兩家的技術差異 —— 查不到就不編（R5）。';
  const N_TVS = '★ TVS／ESD 過電壓保護元件在台股由 6284 佳邦（ESD／TVS 等過電壓保護元件）做。佳邦不在 supply_chain.yaml 裡。';

  const PARTS = {
    cp_term: { name: '外部端子（插座／接頭）', desc: '這條線跟外面世界的交界。★ 本圖只畫成兩個接點符號，不畫任何真實接頭的外觀。', cos: [], none: '這一格是介面，不是這個族群做的東西。連接器見 AI 伺服器鏈的「連接器與高速互連」那張。' },
    cp_line: { name: '主線路（訊號／電源線）', desc: '由左到右＝由外到內。箭頭一律向右 —— 方向反過來就把「分層防護」的順序講反了。', cos: [], none: '這是一條線路，不是一個買得到的零件。' },
    cp_gnd: { name: '接地線', desc: '一條，所有並聯元件都掛在同一條上。並聯元件把導走的能量倒進這裡。', cos: [], none: '這是一條線路，不是一個買得到的零件。' },
    cp_mov: {
      name: '壓敏電阻（MOV）—— 並聯到地',
      desc: '★ 兩條腿：一條接主線、一條接地，主線從它旁邊繼續往右走。平常不導電，電壓一高就把能量導走。★ 它是會消耗的：每吸收一次突波內部就退化一點，最後通常以短路收場。寄生電容大，不適合掛在高速資料線上。',
      cos: [], none: N_MOV,
      note: '「每擋一次就退化、最終短路失效」與「寄生電容大」都來自同一篇比較型整理文（單一來源），所以畫面上不寫任何鉗位比、電壓值與 pF 數字。',
    },
    cp_gdt: {
      name: '氣體放電管（GDT）—— 並聯到地',
      desc: '跟壓敏電阻同屬第一道，靠氣體游離導通。★ 它跟 MOV、TVS 的物理機制完全不同：MOV 是陶瓷晶界接面、GDT 是氣體游離電漿、TVS 是半導體累崩。',
      cos: [], none: '★ 氣體放電管（GDT）本圖查不到台股對應 —— 查不到就寫查不到，不編一個對應（R5）。',
    },
    cp_ntc: {
      name: 'NTC 熱敏電阻 —— 串在線上',
      desc: '★ 主線從它中間穿過，而且沒有接地腿。★ 它擋的不是突波電壓，是**開機瞬間的湧浪電流** —— 跟另外三個不是同一件事。剖面是金屬氧化物燒結的陶瓷本體 ＋ 兩個相對面電極，沒有 PN 接面也沒有晶界網。',
      cos: [], none: '★ NTC 熱敏電阻在台股同樣由 2428 興勤 做（NTC 與壓敏電阻兩類都做）。興勤不在 supply_chain.yaml 裡。',
    },
    cp_pptc: {
      name: '自恢復保險絲（PPTC）—— 串在線上',
      desc: '★ 主線從它中間穿過，沒有接地腿。電流一大就發熱膨脹、把導電鏈拉斷；冷了會自己接回來。剖面是「鎳箔／高分子／鎳箔」三層 ＋ 外包絕緣。跳脫前後的對照見第 ① 段。',
      cos: [], none: N_PPTC,
    },
    cp_tvs: {
      name: 'TVS／ESD 陣列 —— 並聯到地，而且最靠近 IC',
      desc: '★ 兩條腿接到地，而且它與 IC 之間不准再插別的元件。把電壓壓得比壓敏電阻更低、漂移更小 —— 這就是「分層」：靠外的第一道擋大能量，靠近 IC 的第二道把電壓壓下來。順序反過來就沒有意義。',
      cos: [], none: N_TVS,
    },
    cp_ic: { name: 'IC（被保護的對象）', desc: '★ 這一格不是這個族群做的東西，它可能是任何一顆 IC。本圖不畫任何真實晶片的外觀。', cos: [], none: '這一格是被保護的對象，不是這個族群做的東西 —— 見半導體那條鏈。' },
    cp_grain: {
      name: 'ZnO 晶粒（MOV 的本體）',
      desc: '氧化鋅晶粒燒結而成（加入少量鉍、鈷、錳等金屬氧化物）。★ 一堆大小不一的多邊形，不是一塊均質陶瓷 —— 畫成均質方塊就不是 MOV。晶粒的實際尺寸與數量查不到，圖上是示意。',
      cos: [], none: N_MOV,
    },
    cp_gb: {
      name: '晶界（電流真正被擋住的地方）',
      desc: '★ MOV 的非線性完全來自晶界：每一對相鄰晶粒之間的界面形成一個微觀位壘，一顆裡面有數以百萬計個，串並聯成一張三維的網。圖上那條折線就是電流穿過好幾道晶界的路徑。',
      cos: [], none: N_MOV,
    },
    cp_movel: { name: 'MOV 的電極 ×2', desc: '在兩個**相對**的面（上下），不是同一面的兩端 —— 電流要垂直穿過整疊晶粒才會撞到那些晶界。', cos: [], none: N_MOV },
    cp_ni: { name: 'PPTC 的鎳電極箔 ×2', desc: '上下各一片，夾住中間的高分子基體。外面還包一層樹脂或塑膠薄膜當絕緣。', cos: [], none: N_PPTC },
    cp_poly: {
      name: 'PPTC 的高分子基體',
      desc: '聚乙烯類的高分子。低溫時結晶之間的導電粒子構成三維網路而導通；電流過大升溫後體積膨脹、聚合物由結晶態轉為非結晶態，導電粒子的連繫網路斷裂而不導通。溫度降低後恢復結晶，又可導通 —— 這就是「自恢復」。',
      cos: [], none: N_PPTC,
    },
    cp_carbon: {
      name: '導電碳黑粒子（串成鏈）',
      desc: '★ 常溫：黑色顆粒連成貫穿上下電極的通路。過流發熱：高分子膨脹，鏈被拉斷。只畫「變紅」不畫「變厚＋斷鏈」就沒有解釋機制。膨脹的實際比例查不到，本圖不寫百分比。',
      cos: [], none: N_PPTC,
    },
    cp_ins: { name: 'PPTC 的外包絕緣層', desc: '最外面那一層樹脂或塑膠薄膜。它不參與導電，只是把裡面包起來。', cos: [], none: N_PPTC },
    cp_pn: {
      name: 'TVS 的 PN 接面（P 區／空乏區／N 區）',
      desc: '★ 兩種不同摻雜的半導體區，中間一條空乏區窄帶 —— 這是 TVS 的識別特徵。畫成陶瓷晶粒就是畫成了 MOV（兩者的物理機制完全不同），畫成三明治薄膜就是畫成了晶片電阻。',
      cos: [], none: N_TVS,
    },
    cp_tvsel: { name: 'TVS 的金屬電極 ×2', desc: '上下各一片，把 PN 接面夾在中間。', cos: [], none: N_TVS },
    cp_res_ref: {
      name: '指路：晶片電阻與精密電阻在另一張圖',
      desc: '3624 光頡（薄膜與厚膜高精密電阻）與 2478 大毅（晶片電阻）做的是電阻，不是保護元件。晶片電阻的三明治、雷射修整溝、電感的磁粉與繞線、石英的密封腔，全部在「被動元件：電感・電阻・石英」那張 —— 本圖一格都不畫。',
      cos: [], none: '★ 這一格是指路用的，不是本圖畫的元件。3624 光頡與 2478 大毅都不在 supply_chain.yaml 裡。',
    },
  };
  WHO.forEach((r, i) => {
    PARTS['cp_who' + i] = {
      name: r[0], desc: r[1], cos: [],
      none: '這一列的公司全部不在 supply_chain.yaml 的環節裡，所以「做這個的台股」欄列不出它們 —— 對應寫在這裡。',
    };
  });

  window.DG.register('resistor_protect', {
    level: 'group', chain: 'electronics',
    name: '被動保護：過流與過壓元件',
    draw: circuitProtection, native: 980, scene: null,
    q: '一條線從插座進到晶片，中間被幾個零件擋過？PPTC、NTC、壓敏電阻、TVS 各擋什麼，為什麼不能互換？',
    parts: PARTS,
  });
})();
