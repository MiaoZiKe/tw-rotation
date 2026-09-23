/* 被動保護：過流與過壓元件 —— docs/diagram_plan_electronics.md 的 E3
   （族群 `resistor_protect`，electronics 鏈）

   ---- 2026-09-23 v2（Andy：「所有族群 2D 圖呈現風格都需要 Follow AI Server 族群內 2D 圖，
        並且需要適當的調整及填充版面間隔，不許有空白」）----
   原本是 980 寬 ＋ 二十餘行說明畫在 SVG 裡的舊版式；欄寬一窄 12px 的字就被縮成 8px，
   而且五個元件的中文名直接壓在元件方塊上（AI 伺服器那三張早就改掉的畫法）。
   改成跟 `site/dg/server_psu.js`／`liquid_cooling.js`／`switch_wireless.js` 同一套：
     · 畫布 980 → **660**（`native: 660`），svg 根掛 `.rs`；
     · 標題與導言 → `text.ext`（HTML 的 .dghead）；元件名與每一段說明 → `extRow(side)` 外掛卡片，
       畫布上只留**編號圓點**（引線由 externalize 依實際寬度重算）——
       字因此不再壓在零件上，左右兩欄也被卡片填滿、不留空白；
     · 材質走共用的 `D.fx`（`glass` 當元件本體、`beam` 當主線與接地線、`glowDefs`）；
     · 顏色一律 `--dg-*` token（本來就沒有寫死色碼，改完再 grep 一次確認）；
     · **既有互動一個都沒動**：`data-part` 與 `data-seg` 逐字不變（改前改後比對過）。
   ⚠ 舊註解全部保留 —— T1／T2／T3／T6／T10 那幾條紅線還是合約。

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
  if (!D || typeof D.register !== 'function' || !D.fx) return;
  const { extRow, note, fx } = D;

  /* 畫布寬：2026-09-23 從 980 收到 660。說明文字外掛成 HTML 卡片之後，SVG 只剩「畫」的部分。*/
  const CW = 660, SEG = 'passive_comp';

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

  /* ---- 2026-09-23 v2 新增（寫法照 `site/dg/liquid_cooling.js`）----
     card()：說明卡片離開 SVG 變成 HTML（externalize），畫布上只留編號圓點；
     卡片與它指的零件**共用同一個 data-part** —— 點卡片零件亮、點零件卡片亮。*/
  const card = (o) => {
    const s2 = extRow({ seg: o.seg === null ? undefined : (o.seg || SEG), part: o.part, title: o.title, sub: o.sub,
      no: o.no, side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order, warn: o.warn, note: o.note });
    return o.color ? s2.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s2;
  };
  // 中文長句斷行（畫布收窄之後章節裡的長句一個字都不刪，改成自動斷行）
  const wrapCJK = (s2, n) => { const out = []; for (let i = 0; i < s2.length; i += n) out.push(s2.slice(i, i + n)); return out.length ? out : ['']; };
  // 玻璃材質：跟 AI 伺服器那三張同一支 D.fx.glass
  const slab = (x, y, w, h, fill, o) => fx.glass(x, y, w, h,
    { fill, cls: 'part' + ((o && o.cls) ? ' ' + o.cls : ''), rx: (o && o.r) || 2, iso: o && o.iso });
  /* 元件色（卡片色條、編號圓點、引線端點共用）—— 一律 token。
     ⚠ 挑的是「同族但亮一階」的 token：卡片標題印在元件色上要 ≥ 4.5，
       --dg-cp-carbon／--dg-cp-n 這種暗色直接當卡片色會讀不到（liquid_cooling 的銅走過同一條）。*/
  const CC = {
    mov: 'var(--dg-cp-grain)', gdt: 'var(--dg-steel)', ntc: 'var(--dg-cer)',
    pptc: 'var(--dg-cp-poly)', tvs: 'var(--dg-cp-depl)', line: 'var(--dg-accent-2d)',
    gnd: 'var(--dg-steel)', ni: 'var(--dg-ni)', gb: 'var(--dg-cp-gb)', ins: 'var(--dg-resin)',
  };
  // 向右的箭頭（主線）：頂點一定在右邊，所以「箭頭方向」量得出來
  const arrR = (x, y) => PA(`M${f1(x + 7)},${f1(y)} L${f1(x)},${f1(y - 4)} L${f1(x)},${f1(y + 4)} Z`,
    'var(--dg-accent-2d)', 'cparrh');

  /* ================================================================ 區 ① 防護路徑帶
     §3-A／§3-B：由左到右 外部端子 → MOV／GDT（第一道，並聯）→ NTC → PPTC（串聯）
     → TVS／ESD（第二道，並聯，最靠近 IC）→ IC。 */
  /* ⚠ 2026-09-23：座標整組重排到 660 寬。元件名從「寫在方塊上」改成「卡片 ＋ 編號圓點」，
     所以方塊不必再放得下中文字，寬度改由**拓樸**決定（並聯要放得下兩條腿、串聯要放得下主線穿過）。*/
  const LY = 116, GY = 208, LX0 = 64, LX1 = 596;    // 主線 y ／ 接地線 y ／ 主線左右端

  /* 並聯元件：★ 一定有兩條腿 —— 一條接主線、一條接地，主線從它旁邊繼續往右走。 */
  function shunt(id, cx, w, title, fill, inner) {
    const x0 = cx - w / 2, y0 = 146, h = 40;
    // 2026-09-23：本體改用 D.fx.glass（有厚度與邊光），中文名搬到卡片，方塊上不再寫字
    return part(id, slab(x0, y0, w, h, fill, { cls: 'cpbody', r: 4 })
      + (inner || '')
      + LN(`M${cx},${LY} L${cx},${y0}`, 'var(--dg-steel)', 2.2, 'cpleg')
      + LN(`M${cx},${y0 + h} L${cx},${GY}`, 'var(--dg-steel)', 2.2, 'cpleg')
      + C(cx, LY, 3.2, 'var(--dg-accent-2d)', 'cpnode'));
  }

  /* 串聯元件：★ 主線從中間穿過（左進右出），而且**沒有接地腿**。 */
  function series(id, cx, w, title, fill, inner) {
    const x0 = cx - w / 2, y0 = LY - 20, h = 40;
    return part(id, slab(x0, y0, w, h, fill, { cls: 'cpbody', r: 4 })
      + (inner || '')
      + LN(`M${x0},${LY} L${x0 + w},${LY}`, 'var(--dg-accent-2d)', 2.2, 'cpthru'));
  }

  /* 元件位置寫在陣列裡、照順序排 —— T3（MOV 比 TVS 更靠外）因此自動成立。 */
  const PATH = [
    { id: 'cp_mov', kind: 'shunt', cx: 120, w: 76, t: '壓敏電阻 MOV' },
    { id: 'cp_gdt', kind: 'shunt', cx: 214, w: 76, t: '氣體放電管 GDT' },
    { id: 'cp_ntc', kind: 'series', cx: 316, w: 84, t: '熱敏電阻 NTC' },
    { id: 'cp_pptc', kind: 'series', cx: 420, w: 96, t: '自恢復保險絲 PPTC' },
    { id: 'cp_tvs', kind: 'shunt', cx: 520, w: 84, t: 'TVS／ESD 陣列' },
  ];

  function pathBand() {
    const g = [];
    /* 主線：2026-09-23 改用 D.fx.beam（光暈 ＋ 實線 ＋ 流動虛線），跟 AI 伺服器那三張同一套。
       ⚠ 全圖的 feGaussianBlur 元素維持 ≤ 3（DECISIONS #239）：只有主線這一條開 glow。*/
    /* ★ cls:'cpline' 不是裝飾 —— 主線與接地線是這張圖的**拓樸基準**：
       「MOV／GDT／TVS 並聯」與「NTC／PPTC 串聯」這兩條紅線，量的都是
       「元件的腿有沒有碰到主線 / 接地線」，而那要先找得到這兩條線在哪一條 y 上。
       2026-09-23 這兩條線從 LN(...,'cpline'/'cpgnd') 改成 fx.beam() 之後類別被吃掉了，
       結果是**拓樸斷言全部量到 None**（連 .cpgnd 自己那條 stroke-linecap 的樣式也失效）。
       線的畫法可以換，身分不能丟 —— 換算繪圖基元時把 cls 一起帶過去。*/
    g.push(fx.beam(`M${LX0},${LY} L${LX1},${LY}`, { color: 'var(--dg-accent-2d)', w: 2.6, glow: true, flow: true, cls: 'cpline' }));
    g.push(part('cp_line', R(LX0, LY - 3, LX1 - LX0, 6, 'transparent', 'part')));
    g.push(part('cp_gnd', fx.beam(`M${LX0 + 30},${GY} L${LX1 - 40},${GY}`, { color: 'var(--dg-steel)', w: 2.6, glow: false, cls: 'cpgnd' })
      + LN(`M${LX0 + 40},${GY + 6} L${LX0 + 64},${GY + 6}`, 'var(--dg-steel)', 2.2, 'cpgndsym')
      + LN(`M${LX0 + 46},${GY + 11} L${LX0 + 58},${GY + 11}`, 'var(--dg-steel)', 2.2, 'cpgndsym')
      + `<g pointer-events="none">${T(LX0 + 74, GY + 13, '接地：所有並聯元件都掛在同一條上', 'sub')}</g>`));
    // 主線上的方向箭頭：一律向右（外 → 內）
    [92, 170, 262, 370, 470, 566].forEach((x) => { g.push(arrR(x, LY)); });
    // 外部端子（不是任何真實接頭的外觀 —— 只是兩個接點符號）
    g.push(part('cp_term', slab(20, LY - 22, 44, 44, 'var(--dg-mc-case)', { r: 4 })
      + C(38, LY - 9, 4, 'var(--dg-cp-gb)', 'part') + C(38, LY + 9, 4, 'var(--dg-cp-gb)', 'part')
      + LN(`M42,${LY - 9} L64,${LY - 9}`, 'var(--dg-steel)', 1.6)
      + LN(`M42,${LY + 9} L64,${LY + 9}`, 'var(--dg-steel)', 1.6)));
    // 五個元件（名字在卡片上，方塊上不寫字）
    PATH.forEach((p) => {
      g.push(p.kind === 'shunt'
        ? shunt(p.id, p.cx, p.w, p.t, 'var(--dg-mc-case)')
        : series(p.id, p.cx, p.w, p.t, 'var(--dg-mc-case)'));
    });
    // IC（被保護的對象；不是任何真實晶片的外觀）
    g.push(part('cp_ic', slab(596, LY - 24, 48, 48, 'var(--dg-cp-n)', { r: 4 })
      + [0, 1, 2].map((i) => R(590, LY - 14 + i * 13, 6, 4, 'var(--dg-cp-gb)', 'part')).join('')
      + `<g pointer-events="none">${T(620, LY + 4, 'IC', 'lbl', 'middle')}</g>`));
    /* 兩道防護的分界：2026-09-23 畫布收窄之後，分界上的整句話搬到左右兩欄的卡片裡，
       畫布上只留短標（字不准壓到別的字，也不准超出格子）—— 一個字都沒刪，只是換位置。*/
    g.push(LN('M268,70 L268,232', 'var(--dg-frame-s)', 1, null, ' stroke-dasharray="5 5"'));
    g.push(LN('M476,70 L476,232', 'var(--dg-frame-s)', 1, null, ' stroke-dasharray="5 5"'));
    g.push(T(70, 66, '第一道：擋大能量（並聯到地）', 'sub', null, 'fill:var(--dg-accent-2d)'));
    g.push(T(278, 66, '過流那一側：串在線上', 'sub', null, 'fill:var(--dg-accent-2d)'));
    g.push(T(486, 66, '第二道：壓更低（並聯）', 'sub', null, 'fill:var(--dg-accent-2d)'));
    return g.join('');
  }

  /* ================================================================ 區 ② ① PPTC 剖面
     §2-B：鎳電極箔 ×2 夾住高分子基體，裡面是串成鏈的導電碳黑粒子，外面包一層絕緣。
     兩格對照（常溫／跳脫）共用這一支，只換 `polyH` 與 `breaks` 兩個參數 —— T11 自動成立。 */
  /* ⚠ 2026-09-23：40 → 52。畫布收窄之後第 ② 排的高度用不完，高分子層太扁看不出「變厚」。
     跳脫格仍然是 `PP_BASE * 1.4` 真的乘出來的（T11），比例關係一個都沒動。*/
  const PP_BASE = 72;

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
  /* ⚠ 2026-09-23：四格整組重排到 660 寬（分隔線在 178／336／494）。
     每一格的內容一件都沒少，只是寬度從 ~237 收到 ~135、垂直方向放大一點把格子填滿。*/
  function cells() {
    const g = [];
    // ① PPTC
    const p = pptcCell(26, 340, PP_BASE, 0, 140);
    g.push(p.svg);
    g.push(part('cp_pptc', R(20, 334, 152, p.y1 - 328, 'transparent', 'part')));
    // ② NTC：陶瓷本體 ＋ 兩個相對面電極 ＋ 引線 —— 沒有 PN 接面、沒有晶界網（V2）
    g.push(part('cp_ntc', slab(196, 366, 120, 76, 'var(--dg-cer-cut)', { cls: 'cpntcbody', r: 3 })
      + R(196, 354, 120, 12, 'var(--dg-ni)', 'part cpntcel')
      + R(196, 442, 120, 12, 'var(--dg-ni)', 'part cpntcel')
      // 引線兩根：★ 上緣停在 276、下緣停在 400 —— 上面是格子小標（bbox 到 278）、
      //   下面是格子底下的說明（bbox 從 404 起）。字壓在零件上排版體檢抓不到，所以這裡自己算。
      // ⚠ 上緣停在 336（格子小標的 bbox 到 330）、下緣停在 472（底下說明從 482 起）。
      //   字壓在零件上排版體檢抓不到，所以這裡自己算清楚。
      + R(248, 336, 16, 18, 'var(--dg-steel)', 'part')
      + R(248, 454, 16, 18, 'var(--dg-steel)', 'part')));
    // ③ MOV：晶粒 ＋ 晶界 ＋ 電流折線 ＋ 兩個相對面電極
    const mv = movGrains(350, 484, 356, 428);
    g.push(part('cp_movel', R(350, 342, 134, 14, 'var(--dg-ni)', 'part cpmovel')
      + R(350, 428, 134, 14, 'var(--dg-ni)', 'part cpmovel')));
    g.push(mv.svg);
    // ④ TVS：P 區 ／ 空乏區 ／ N 區 ＋ 上下金屬電極
    // ⚠ 上下金屬電極自己一個群組（`cp_tvsel`），不要併進 `cp_tvs` ——
    //   併進去的話 `parts.cp_tvsel` 那張小卡永遠開不起來，
    //   變成「定義在那裡、但點不到」的死條目。
    g.push(part('cp_tvsel', R(508, 338, 130, 12, 'var(--dg-ni)', 'part cptvsel')
      + R(508, 434, 130, 12, 'var(--dg-ni)', 'part cptvsel')));
    g.push(part('cp_pn', R(508, 350, 130, 36, 'var(--dg-cp-p)', 'part cpp')
      + R(508, 386, 130, 10, 'var(--dg-cp-depl)', 'part cpdepl')
      + R(508, 396, 130, 38, 'var(--dg-cp-n)', 'part cpn')));
    return g.join('');
  }

  /* ================================================================ 第 ① 段：PPTC 跳脫前後
     §3-D（T10，紅線）：同一張圖，鏈斷開 ＋ 高分子層**明顯變厚**。
     ★ 1.4 倍是真的乘出來的（`PP_BASE * 1.4`），不是目測；畫面上不寫這個數字
       —— 那是畫圖用的下限，不是事實宣稱（§7-C2）。 */
  /* ⚠ 2026-09-23：章節收到 660 寬。長句一個字都沒刪，改成 `wrapCJK` 自動斷行；
     兩格對照從左右 330 寬改成左右 288 寬（兩格仍然同一個比例尺、同一支函式）。*/
  const FW = 628, LH = 17;
  // 章節裡可點的一列：粗體標題 ＋ 自動斷行的說明
  function txtRow(id, y, title, body, warn) {
    const lines = wrapCJK(body, 44);
    const h = 18 + lines.length * LH;
    const inner = [T(24, y + 13, title, 'lbl', null, warn ? 'fill:var(--dg-warn)' : '')]
      .concat(lines.map((t, i) => T(24, y + 13 + LH * (i + 1), t, 'sub')));
    return { svg: part(id, R(16, y, FW, h, 'transparent', 'part')
      + `<g pointer-events="none">${inner.join('')}</g>`), h: h + 4 };
  }
  // 章節裡不可點的一段文字（自動斷行）
  function txtPara(y, body, warn) {
    const lines = wrapCJK(body, 46);
    return { svg: lines.map((t, i) => T(24, y + 13 + LH * i, t, 'sub', null,
      warn ? 'fill:var(--dg-warn)' : '')).join(''), h: 13 + lines.length * LH };
  }

  function foldTrip(y0) {
    const g = [];
    let y = y0 + 8;
    g.push(T(24, y + 14, 'PPTC 跳脫前後長什麼樣', 'hd'));
    g.push(T(24, y + 31, '兩格同一個比例尺、同一套材質色，只有兩件事不同：', 'sub'));
    g.push(T(24, y + 48, '① 導電碳黑粒子的鏈斷開了　② 高分子層明顯變厚（體積膨脹）。', 'sub'));
    g.push(T(24, y + 65, '只畫「變紅」不畫「變厚＋斷鏈」＝沒有解釋機制。', 'sub'));
    y += 92;
    g.push(T(24, y - 6, '常溫：碳黑連成通路 → 幾乎不擋路', 'sub'));
    g.push(T(348, y - 6, '過流發熱：鏈被拉斷 → 變成高阻', 'sub'));
    const a = pptcCell(24, y, PP_BASE, 0, 288);
    const b = pptcCell(348, y, PP_BASE * 1.4, 1, 288);
    g.push(a.svg, b.svg);
    let yb = Math.max(a.y1, b.y1) + 10;
    [['冷了之後高分子縮回去、鏈重新接上 —— 這就是「自恢復」。本圖不寫膨脹的百分比與正常態電阻值（查不到共通值）。', 0],
      ['★ 台股做 PPTC 的是 6224 聚鼎（PPTC 保護元件）與 6642 富致（PPTC 過電流保護元件）。本圖不區分兩家的技術差異 —— 查不到就不編。', 1],
    ].forEach(([t, w]) => { const r = txtPara(yb, t, w); g.push(r.svg); yb += r.h + 4; });
    return { svg: g.join(''), h: yb - y0 + 10 };
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
    let y = y0 + 8;
    g.push(T(24, y + 14, '這一格的台股站在哪一類（6 家）', 'hd'));
    g.push(T(24, y + 31, '4 家做保護元件、2 家做電阻（那兩家的剖面在別張圖）', 'sub'));
    y += 40;
    WHO.forEach((r, i) => { const b2 = txtRow('cp_who' + i, y, r[0], r[1], i === 3); g.push(b2.svg); y += b2.h; });
    y += 8;
    [['★ 這 6 檔用代號 grep 整份 supply_chain.yaml，一檔都沒有出現；而這張圖掛得上的環節只有「被動元件」一格，它底下的 5 家（國巨、華新科、凱美、禾伸堂、信昌電）沒有一家在這個族群裡 —— 它們做的是 MLCC 與晶片電阻。', 1],
      ['所以這張圖每一個零件的公司清單都刻意留空、改用文字回答 —— 走環節預設會給出錯的答案，不是不完整的答案。', 1],
      ['★ 6224 聚鼎的 CLM 用於 BBU 電池模組與伺服器電源保護（信心 reported）—— 本圖畫的是通用電路，主圖不指定用途，只在這裡列一句。', 0],
    ].forEach(([t, w]) => { const r = txtPara(y, t, w); g.push(r.svg); y += r.h + 4; });
    y += 4;
    const ref = txtRow('cp_res_ref', y, '指路用的一格：晶片電阻不在這張',
      '晶片電阻的三明治（基板／電阻膜／保護層／端電極）與雷射修整溝、電感的磁粉與繞線、石英的密封腔，全部在「被動元件：電感・電阻・石英」那張 —— 本圖一格都不畫。');
    g.push(ref.svg); y += ref.h;
    return { svg: g.join(''), h: y - y0 + 10 };
  }

  /* ================================================================ 版面
     ---- 2026-09-23 v2（Andy：Follow AI 伺服器那三張、版面不許有空白）----
     畫布 660、兩排：
       第 1 排　① 防護路徑帶（外部端子 → MOV／GDT → NTC → PPTC → TVS → IC，箭頭一律向右）
       第 2 排　② 四種元件剖面（PPTC ｜ NTC ｜ MOV ｜ TVS，分隔線在 178／336／494）
     元件名與每一段說明全部外掛成 HTML 卡片（左右兩欄）—— 畫布上只剩編號圓點，
     字因此不再壓在零件上，而兩欄卡片把版面填滿。
     收合時：HTML 標題列 ＋ 兩排圖 ＋ 兩條章節列。
     ⚠ 2026-09-23 **未解**：這行註解原本寫「約 690px（上限 700）」，實測是 **702px** —— 超出自己的規格 2px。
        追出來的機制：收合高度**不是**下面那個 `H` 決定的（`H` 只是 JS 還沒跑之前的靜態 viewBox，
        `diagrams.js` 的 `wireFolds().paint()` 會在執行期把 viewBox 整個重寫掉），
        真正的算式是 `base ＋ 兩條章節列 ＋ PAD(10)`，而 `base = max(第一條章節列的 y − FOLD_H, solidBottom + 8)`。
        這張圖是 `solidBottom + 8` 那一邊贏，`solidBottom` 取的是 **svg 頂層 `<g>` 的 bbox 底**，
        所以單獨把第 2 排外框改矮**沒有用**（同一個群組裡還有別的東西壓到同樣的深度）——
        試過 300 → 296，量出來仍然是 702，已還原。
        ★ 已經確認過的事：**沒有任何東西被截掉**。收合時最深的可見內容在 y=673，viewBox 702，
          而 svg 是自己撐高的（height:auto），物理上不會裁切。也就是說這 2px 純粹是棘輪數字，
          不是畫面上看得到的毛病。
        要收掉它有兩條路，挑一條做：
          (a) 找出那個群組裡真正壓到 582 的元素、把它往上收 4px；
          (b) 把 `_uitest.py` 那條棘輪從 700 放到 704，並在那裡寫明理由
              （這張圖有兩條章節列，框架的固定開銷比別張多一條）。
        這一版兩條都沒做 —— 放寬紅線的棘輪不該由改圖的人順手決定。*/
  function circuitProtection() {
    const S1 = 596;
    const p1 = foldTrip(S1 + 46);
    const S2 = S1 + 46 + p1.h;
    const p2 = foldWho(S2 + 46);
    const H = S2 + 46 + p2.h + 16;
    return `<svg class="dg dgm rs dgcp dg1" viewBox="0 0 ${CW} ${H}" width="100%" style="display:block">${D.STYLE}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（DECISIONS #231）。
           這裡只補 diagrams.js 沒有的幾件：晶界線、接地符號的線帽、碳黑鏈的線帽。
           ★ 晶界是這張圖的識別特徵 —— 它必須是**線**，不是兩塊顏色的交界，
             不然配色把色差壓掉之後就看不見了。顏色一律走 --dg-*。
           2026-09-23 多一組：元件本體改用 D.fx.glass 之後自己有細邊（.fxe），
           共用的 2.2px 描邊再疊上去會變成一團線框（Andy 講過三次的「螢光感太重」），
           所以跟 panel／psu 那幾張一樣把描邊與發光各降一階。*/
        svg.dgcp .cpgrain{stroke:var(--dg-cp-gb);stroke-width:1.1;stroke-linejoin:round}
        svg.dgcp .cpchain{stroke-linecap:round}
        svg.dgcp .cpgnd,svg.dgcp .cpgndsym{stroke-linecap:round}
        svg.dgcp .cppath{stroke-linecap:round}
        svg.dgcp .cpnode{stroke:none}
        svg.dgcp [data-seg] .part{stroke-width:0}
        svg.dgcp [data-seg].sel .part{stroke-width:0;filter:none}
        svg.dgcp [data-seg]:hover .part{stroke-width:1.4;filter:none}
        svg.dgcp [data-seg].sel-part .part{stroke-width:2.4;filter:var(--dg-glow,drop-shadow(0 0 5px var(--cc)))}
        svg.dgcp.haspart [data-seg].sel:not(.sel-part){opacity:.55}
      </style>
      <!-- 標題與導言：v2 搬到 HTML 的 .dghead，SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">被動保護：過流與過壓元件</text>
      <text class="cap ext" x="0" y="0">擋電壓的並聯、擋電流的串聯 —— 位置不一樣，因為工作方式根本不同。上排是一條線從外面走進晶片、中間被幾個零件擋過（由左到右＝由外到內）；下排把四種元件各切開一顆。左右兩欄的卡片逐件說明，點卡片零件會亮、點零件卡片會亮；下面兩段預設收起來，按標題列就打得開。</text>

      <!-- ================= 第 1 排：① 防護路徑帶（這張圖的主角） ================= -->
      ${frame(16, 16, 628, 250)}
      ${T(28, 40, '① 一條線從外面走進晶片，中間被幾個零件擋過', 'hd')}
      ${pathBand()}

      <!-- ================= 第 2 排：② 四種元件剖面（同一個外框尺寸、同一套材質色） ================= -->
      ${frame(16, 282, 628, 300)}
      <path d="M178,292 L178,572" stroke="var(--dg-frame-s)" stroke-width="1" fill="none"/>
      <path d="M336,292 L336,572" stroke="var(--dg-frame-s)" stroke-width="1" fill="none"/>
      <path d="M494,292 L494,572" stroke="var(--dg-frame-s)" stroke-width="1" fill="none"/>
      ${T(26, 312, '① PPTC', 'hd')}${T(26, 330, '自恢復保險絲（串聯）', 'sub')}
      ${T(190, 310, '② NTC', 'hd')}${T(190, 326, '熱敏電阻（串聯）', 'sub')}
      ${T(348, 312, '③ MOV', 'hd')}${T(348, 330, '壓敏電阻（並聯）', 'sub')}
      ${T(506, 312, '④ TVS／ESD', 'hd')}${T(506, 330, '（並聯，最靠近 IC）', 'sub')}
      ${cells()}
      ${T(26, 494, '鎳電極箔 ×2 夾住高分子', 'sub')}
      ${T(26, 511, '基體，外面包一層絕緣；', 'sub')}
      ${T(26, 528, '黑點是導電碳黑。', 'sub')}
      ${T(190, 494, '金屬氧化物燒結的陶瓷本', 'sub')}
      ${T(190, 511, '體＋兩個相對面電極＋兩', 'sub')}
      ${T(190, 528, '根引線。沒有 PN 接面。', 'sub')}
      ${T(348, 494, '一堆大小不一的 ZnO 晶', 'sub')}
      ${T(348, 511, '粒；擋電流的是晶粒之間', 'sub')}
      ${T(348, 528, '的界面（晶界）。', 'sub')}
      ${T(506, 494, '半導體 PN 接面：P 區／', 'sub')}
      ${T(506, 511, '空乏區／N 區＋上下金屬', 'sub')}
      ${T(506, 528, '電極。超過門檻就崩潰。', 'sub')}

      <!-- ================= 說明卡片（HTML）：左欄路徑帶、右欄四種剖面 =================
           每一張卡片的 data-part 都跟畫布上的零件**同一個字串**（改造前後逐字比對過），
           所以既有互動一個都沒掉：點卡片亮零件、點零件亮卡片。-->
      ${card({ side: 'l', no: 1, part: 'cp_term', color: CC.gnd, ax: 42, ay: 96, title: '外部端子（插座／接頭）', sub: '這條線跟外面世界的交界；只畫成兩個接點符號' })}
      ${card({ side: 'l', no: 2, part: 'cp_mov', color: CC.mov, ax: 120, ay: 166, title: '壓敏電阻 MOV —— 第一道，並聯到地', sub: ['★ 兩條腿：一條接主線、一條接地', '平常不導電，電壓一高就把能量導走；它是會消耗的'] })}
      ${card({ side: 'l', no: 3, part: 'cp_gdt', color: CC.gdt, ax: 214, ay: 166, title: '氣體放電管 GDT —— 第一道，並聯到地', sub: '跟 MOV 同屬第一道，靠氣體游離導通（機制完全不同）' })}
      ${card({ side: 'l', no: 4, part: 'cp_ntc', color: CC.ntc, ax: 316, ay: 116, title: '熱敏電阻 NTC —— 串在線上', sub: ['★ 主線從中間穿過，沒有接地腿', '它擋的是開機瞬間的湧浪電流，不是突波電壓'] })}
      ${card({ side: 'l', no: 5, part: 'cp_pptc', color: CC.pptc, ax: 420, ay: 116, title: '自恢復保險絲 PPTC —— 串在線上', sub: '過流發熱 → 變高阻把路切斷；冷了會自己接回來' })}
      ${card({ side: 'l', no: 6, part: 'cp_tvs', color: CC.tvs, ax: 520, ay: 166, title: 'TVS／ESD 陣列 —— 第二道，並聯到地', sub: '★ 擺在最靠近 IC 的地方，把電壓壓得比 MOV 更低' })}
      <!-- ★ 2026-09-23：⑦ 的錨點從 (620,116) 搬到 (592,98)。
           (620,116) 正是 IC 方塊正中央，而方塊中央印的就是「IC」那兩個字 ——
           編號圓點（r=9.5）直接整顆壓在字上，六個寬度 × 兩個主題全部量到 14px 重疊。
           搬到左邊那排接腳上（x 590～596）：指的還是同一個零件，離「IC」字樣橫向讓開 11px。
           通則跟矽晶圓那張同一條：**編號圓點不會跟著畫布縮，所以它不能放在字上。** -->
      ${card({ side: 'l', no: 7, part: 'cp_ic', color: CC.line, ax: 592, ay: 98, title: 'IC（被保護的對象）', sub: '不是任何真實晶片的外觀；整條路徑就是為了它而存在' })}
      ${card({ side: 'r', no: 8, part: 'cp_line', color: CC.line, ax: 176, ay: 116, title: '主線路（訊號／電源線）', sub: '由左到右＝由外到內；箭頭一律向右' })}
      ${card({ side: 'r', no: 9, part: 'cp_gnd', color: CC.gnd, ax: 470, ay: 208, title: '接地線（一條）', sub: '所有並聯元件都掛在同一條上，把導走的能量倒進這裡' })}
      ${card({ side: 'r', no: 10, part: 'cp_ni', color: CC.ni, ax: 96, ay: 352, title: 'PPTC：鎳電極箔 ×2', sub: '上下各一片，把高分子基體夾在中間' })}
      ${card({ side: 'r', no: 11, part: 'cp_poly', color: CC.pptc, ax: 96, ay: 400, title: 'PPTC：高分子基體', sub: '過流發熱就膨脹 —— 跳脫前後的對照見下面第 ① 段' })}
      ${card({ side: 'r', no: 12, part: 'cp_carbon', color: CC.gb, ax: 150, ay: 380, title: 'PPTC：導電碳黑粒子', sub: '常溫連成貫穿上下電極的通路；膨脹時鏈被拉斷' })}
      ${card({ side: 'r', no: 13, part: 'cp_grain', color: CC.mov, ax: 400, ay: 392, title: 'MOV：ZnO 晶粒', sub: '大小不一；畫成一塊均質陶瓷方塊就不是 MOV' })}
      ${card({ side: 'r', no: 14, part: 'cp_gb', color: CC.gb, ax: 440, ay: 392, title: 'MOV：晶界（非線性的來源）', sub: '★ 電流被擋住的地方是晶粒之間的界面，一顆裡面數以百萬計' })}
      ${card({ side: 'r', no: 15, part: 'cp_tvsel', color: CC.ni, ax: 573, ay: 344, title: 'TVS：上下金屬電極', sub: '把 PN 接面夾在中間，兩端接出去' })}
      ${card({ side: 'r', no: 16, part: 'cp_pn', color: CC.tvs, ax: 573, ay: 400, title: 'TVS：PN 接面（P 區／空乏區／N 區）', sub: '★ 空乏區是它的識別特徵；超過門檻就崩潰導通把能量吃掉' })}
      ${note({ side: 'l', warn: true, order: 96, title: '★ 這張圖唯一的一條規矩',
      lines: ['並聯（MOV／GDT／TVS）＝兩條腿：一條接主線、一條接地。',
        '串聯（NTC／PPTC）＝主線從中間穿過、沒有接地腿。',
        '差別畫在**幾何**上，不畫在顏色上 —— 配色把色差壓掉也還是分得出來。'] })}
      ${note({ side: 'l', warn: true, order: 97, title: '★ 誰做的（逐家見下面第 ② 段）',
      lines: ['壓敏電阻與 NTC：2428 興勤（兩類都做，同時指到兩格）。',
        'TVS／ESD：6284 佳邦。PPTC：6224 聚鼎、6642 富致。',
        '★ 晶片電阻與精密電阻（3624 光頡、2478 大毅）在別張圖，本圖一格都不畫。'] })}
      ${note({ side: 'r', order: 98, title: '為什麼零件小卡的公司欄是空的',
      lines: ['本圖的四類元件，目前一家台股都不在供應鏈資料的環節裡。',
        '所以公司一律用文字寫在小卡與第 ② 段，下方的「環節色標」篩不到它們。'] })}
      ${note({ side: 'r', order: 99, title: '這張圖沒有回答的事',
      lines: ['示意圖，非實物比例：晶粒、碳黑顆粒的大小與數量都是示意。',
        '鉗位電壓、通流容量、動作電流、壽命次數、市占率與營收數字一個都不寫。',
        'MOV 每擋一次就退化一點、最後通常以短路收場；TVS 在額定脈衝下漂移很小（信心：中，單一比較型來源）。'] })}

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
    /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。檔頭 §0-A 原本寫「不做真 3D」，
       推翻的不是那個理由本身，是它漏掉的另一半（判準見 DECISIONS #247／#251）：
       原本的理由是「串／並是電路拓樸不是空間形狀」—— 那一句今天仍然成立，
       所以 3D 這一張**不重畫拓樸**（拓樸留在 2D）。漏掉的那一半是：
       這四顆的外觀都只是小方塊，差別全部在**裡面**（晶粒與晶界／高分子與碳黑鏈／
       均質陶瓷／PN 接面與空乏區）—— 四顆並排剖開轉一圈，四種物理一次比得出來。*/
    draw: circuitProtection, native: CW, scene: 'resistor_protect',
    q: '一條線從插座進到晶片，中間被幾個零件擋過？PPTC、NTC、壓敏電阻、TVS 各擋什麼，為什麼不能互換？',
    parts: PARTS,
  });
})();
