/* 矽晶圓：從熔湯到一片鏡面 —— docs/diagram_plan_semiconductor.md 的 S2
   （族群 `silicon_wafer`、semiconductor 鏈）

   合約＝`docs/diagram_specs/silicon_wafer.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的幾件事：

     · §0-A **不做真 3D**（`scene: null`）。長晶爐是旋轉對稱體，轉一圈看到的每一面都一樣；
       關鍵是「上下關係」與「拉的方向」，那是剖面上的一個箭頭。
       回頭加 3D 的唯一條件是「晶碇在多線鋸裡被鋼線陣列同時切成上百片的空間關係」。
     · §0-B 交界：**不畫電晶體、光罩、曝光、製程迴圈**（那是「晶圓代工」那張），
       **不畫切割打線封裝**（那是 S5），**不畫 PVT 昇華爐**（那是「第三代半導體」那張）。
     · §3-A C2（紅線）**提拉方向箭頭朝上**。畫成往下＝那是在把柱子推進湯裡。
       實作上這一條用一支 `upArrow()` 保證：它只接受「終點 y 小於起點 y」的參數。
     · §3-A C7（紅線）**爐子必須是 CZ 提拉式：看得到熔湯液面、看得到往上拉的柱子**。
       `wide_bandgap.js` 那張的長晶是 PVT 昇華法（固體昇華、沒有液面）——
       兩張圖的流程列第 1 格都叫「長晶」，爐子畫一樣就是在公開網站上把兩種材料的製程講錯。
     · §3-B S1（紅線）**表面粗糙度必須單調變細**。實作上用**同一支 `profile()`**
       畫五段，只換一個 `amp`（起伏振幅）參數，由左到右遞減 —— 手刻五段一定會有一段畫歪。
     · §7-D1（H4）**一個 `data-seg` 都不掛**。`supply_chain.yaml` 的半導體鏈 14 格裡
       **沒有一格是矽晶圓**，兩個看起來像的候選掛上去都會產生錯誤宣稱：
         semi_material → 底下只有 1785 光洋科（靶材、貴金屬回收）＝宣稱「光洋科做矽晶圓」
         foundry       → 底下是 2330／2303／6770       ＝宣稱「台積電自己長晶圓」
       **誠實的代價是：沒有環節色連動、沒有篩選，而且 `renderPartCard()` 在 `if (!seg)`
       就把小卡藏起來 —— 所以「誰做的」全部印在畫面上**（台股標示線 ＋ 說明欄），不是留白。
       下面的 `parts:` 照 `docs/diagram_purpose.md` §4 寫齊，industry.js 一支援就自己亮起來。

   兩個實作上的取捨
   ----------------
   1. **不能用 `D.processBar()`**：那支會輸出 `data-seg="…"`，這張圖依 H4 一個都不能有
      （seg 傳 undefined 會變成字串 "undefined"，那比沒掛更糟）。所以底下自己寫了一支
      `pbar()`，只有 `data-part`。做法與 `wide_bandgap.js` 相同，不是「自己造第二套」。
   2. **8 吋與 12 吋畫成同心圓、共用同一組方格**：兩個圓的半徑直接用 200 與 300 乘同一個 k 算出來
      （§3-D D1 量得出 2:3），方格用同一個 `CELL` 常數（D2 自動成立）。
      手填兩個看起來差不多的數字，就是 D1 唯一會不過的原因。

   顏色一律走既有的 `--dg-*`（沒有新增任何 token），JS 裡一個 #xxxxxx 都沒有。
   熔湯是全圖唯一該有「熱」感的東西，走語意色 `--dg-hot`；其餘一律冷色系。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;

  /* ★ 2026-09-23（Andy：「所有族群 2D 圖呈現風格都需要 Follow AI Server 族群內 2D 圖，
     並且需要適當的調整及填充版面間隔，不許有空白」）
     -------------------------------------------------------------------------
     原本：980 寬。主畫面是「左邊 446 寬的爐子框 ＋ 右邊 486 寬的四句話框 ＋ 底下一條 940 寬的階梯」，
           三塊之間與框內都留了大片空白；標註靠 `fLabel()` 在框裡自己畫一行字。
     現在：跟 `site/dg/server_psu.js`／`liquid_cooling.js`／`switch_wireless.js` 同一套
           （DECISIONS #238／#239 的 v2 風格）：
             · svg 根掛 `rs` → `externalize()` 把說明卡片搬成 HTML（.dgc）排進畫布左右兩欄，
               欄寬由 index.html 的 .dgv2 容器查詢決定。`fLabel()` 整支退場，
               改用共用的 `extRow`（卡片 ＋ 畫布上的編號圓點 ＋ 引線）；
               「四句話」那一框變成三張 note 卡片，一個字都沒刪。
             · 畫布收到 **660**（主角寬），`native` 跟著改。
               §1 只留這張圖的兩個命題：**CZ 提拉爐**（沒有它就跟 SiC 的昇華爐分不出來）
               ＋ **8 吋 vs 12 吋**（面積比是算出來的）。晶碇切片、粗糙度階梯、
               製程七格＋台股名單收進三個 `D.fold()` 章節。
             · 材質走共用介面 `D.fx`（`glowDefs`／`glass`／`shadows`）。
             · 粗糙度階梯從 5＋1 格 ×146 寬改成 ×90 寬，標題拆成兩行短句 ——
               **字級一個都沒縮**（12px 是硬下限），只是斷行變密。
     沒有放寬的事：**一個 `data-seg` 都不掛**（§7-D1／H4 照舊），27 個 `data-part` 一個不改名。*/
  const CW = 660;

  /* ================================================================ 小工具 */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${+x.toFixed(1)}" y="${+y.toFixed(1)}" width="${+w.toFixed(1)}" height="${+h.toFixed(1)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const PA = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const LN = (d, col, w2, extra) =>
    `<path d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const EL = (cx, cy, rx, ry, fill, cls) =>
    `<ellipse${cls ? ` class="${cls}"` : ''} cx="${+cx.toFixed(1)}" cy="${+cy.toFixed(1)}" rx="${+rx.toFixed(1)}" ry="${+ry.toFixed(1)}" fill="${fill}"/>`;
  /* ★ 這張圖**沒有 data-seg**（§7-D1）。`data-part` 一律要自己寫 ——
     沒有 seg 的時候 `stampParts()` 自動補的 key 會退化成「null ＋ 序號」。*/
  const part = (id, inner) => `<g data-part="${id}">${inner}</g>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${+x.toFixed(1)}" y="${+y.toFixed(1)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;

  /* 元件色（卡片 data-dgcolor ＋ 編號圓點 ＋ 引線端點共用），全部是 index.html 既有的 token */
  const C = {
    si: 'var(--dg-si)', si2: 'var(--dg-si-2)', steel: 'var(--dg-steel)', steel2: 'var(--dg-steel-2)',
    hot: 'var(--dg-hot)', hot2: 'var(--dg-hot-2)', glass: 'var(--dg-pn-glass)', el: 'var(--dg-el)',
    org: 'var(--dg-organic)', cyan: 'var(--dg-accent-2d)', mute: 'var(--dg-mute)',
    cover: 'var(--dg-cover)', warn: 'var(--dg-warn)',
  };
  /* 說明卡片（v2）。⚠ 這張圖沒有 data-seg，所以 `extRow` 不傳 seg —— 卡片仍然畫得出來，
     只是跟現況一樣點了不會篩成分股（H4 的既定代價，不是壞掉）。*/
  const card = (o) => {
    const s = extRow({ part: o.part, title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ★★ 提拉箭頭（§3-A C2，紅線）。**只接受往上**：傳進來的 `len` 一律往 -y 走，
     所以這支在物理上畫不出一支朝下的提拉箭頭。畫反是這張圖最容易錯的一條。*/
  function upArrow(x, yBottom, len, col) {
    const yTop = yBottom - Math.abs(len);
    return `<path class="arw" d="M${x},${yBottom} L${x},${yTop + 8}" stroke="${col || C.cyan}" stroke-width="2.4" fill="none"/>`
      + `<path class="arwh" d="M${x},${yTop} L${x - 5},${yTop + 10} L${x + 5},${yTop + 10}Z" fill="${col || C.cyan}"/>`;
  }
  // 旋轉箭頭（一段圓弧 ＋ 一個箭頭）。晶碇與坩堝各一個。
  function spinArrow(cx, cy, r, col) {
    return `<path class="spn" d="M${cx - r},${cy} A${r},${r * 0.42} 0 0 0 ${cx + r},${cy}" stroke="${col}" stroke-width="1.8" fill="none"/>`
      + `<path d="M${cx + r},${cy} L${cx + r - 7},${cy - 5} L${cx + r - 2},${cy + 6}Z" fill="${col}"/>`;
  }

  /* ================================================================ 區 A：CZ 長晶爐剖面（§1 左）
     §3-A：熔湯在下、籽晶在上（C1）；提拉箭頭朝上（C2）；
     晶碇有頸縮／肩／等徑段／尾錐（C3）；加熱器環繞坩堝**側面**（C8）。
     幾何一個數字都沒改，改的只有它被縮放後放在畫布上的哪裡（SC／SDY）。*/
  const FUR = {
    wallL: 66, wallR: 414, wallT: 96, wallB: 446,     // 爐體
    cruL: 152, cruR: 328, cruT: 322, cruB: 424,       // 石英坩堝（U 形）
    meltT: 350, meltB: 414,                            // 熔湯：液面 y=350（CZ 的識別特徵）
    rodX: 240,
  };
  function furnace() {
    const F = FUR, g = [];
    // 爐體：外殼 ＋ 內腔
    g.push(part('sw_chamber', fx.glass(F.wallL, F.wallT, F.wallR - F.wallL, F.wallB - F.wallT, { fill: C.steel2, cls: 'part', rx: 10 })
      + R(F.wallL + 10, F.wallT + 10, F.wallR - F.wallL - 20, F.wallB - F.wallT - 20, 'var(--dg-void)', 'part', 6)));
    // 加熱器：**環繞坩堝側面**（不是畫在爐子頂上）
    g.push(part('sw_heater', R(F.cruL - 34, F.cruT - 8, 18, (F.cruB + 8) - (F.cruT - 8), C.hot2, 'part', 3)
      + R(F.cruR + 16, F.cruT - 8, 18, (F.cruB + 8) - (F.cruT - 8), C.hot2, 'part', 3)));
    // 石墨承座（示意，§7-B3 低信心）：包在石英坩堝外面
    g.push(part('sw_susceptor', PA(`M${F.cruL - 12},${F.cruT - 6} L${F.cruL - 12},${F.cruB - 24} `
      + `Q${F.cruL - 12},${F.cruB + 12} ${(F.cruL + F.cruR) / 2},${F.cruB + 12} `
      + `Q${F.cruR + 12},${F.cruB + 12} ${F.cruR + 12},${F.cruB - 24} L${F.cruR + 12},${F.cruT - 6} `
      + `L${F.cruR},${F.cruT - 6} L${F.cruR},${F.cruB - 24} Q${F.cruR},${F.cruB} ${(F.cruL + F.cruR) / 2},${F.cruB} `
      + `Q${F.cruL},${F.cruB} ${F.cruL},${F.cruB - 24} L${F.cruL},${F.cruT - 6}Z`, C.el, 'part')));
    // 石英坩堝（U 形，半透明淺色）
    g.push(part('sw_crucible', PA(`M${F.cruL},${F.cruT} L${F.cruL},${F.cruB - 26} `
      + `Q${F.cruL},${F.cruB} ${(F.cruL + F.cruR) / 2},${F.cruB} Q${F.cruR},${F.cruB} ${F.cruR},${F.cruB - 26} `
      + `L${F.cruR},${F.cruT} L${F.cruR - 9},${F.cruT} L${F.cruR - 9},${F.cruB - 28} `
      + `Q${F.cruR - 9},${F.cruB - 9} ${(F.cruL + F.cruR) / 2},${F.cruB - 9} `
      + `Q${F.cruL + 9},${F.cruB - 9} ${F.cruL + 9},${F.cruB - 28} L${F.cruL + 9},${F.cruT}Z`,
      C.glass, 'part')));
    /* ★★ 熔湯（§3-A C7）：**液面畫得出來**就是 CZ 跟 PVT 昇華爐唯一的差別。
       液面那條亮線帶 class="surf"，驗收直接量它在不在、在什麼高度。*/
    g.push(part('sw_melt', PA(`M${F.cruL + 9},${F.meltT} L${F.cruL + 9},${F.meltB - 20} `
      + `Q${F.cruL + 9},${F.meltB} ${(F.cruL + F.cruR) / 2},${F.meltB} `
      + `Q${F.cruR - 9},${F.meltB} ${F.cruR - 9},${F.meltB - 20} L${F.cruR - 9},${F.meltT}Z`, C.hot, 'part')
      + LN(`M${F.cruL + 9},${F.meltT} L${F.cruR - 9},${F.meltT}`, C.cover, 2.4, ' class="surf"')));
    // 籽晶桿 ＋ 籽晶（**在最上方**，C1）
    g.push(part('sw_seed', R(F.rodX - 5, 106, 10, 62, C.steel, 'part rod', 2)
      + R(F.rodX - 9, 168, 18, 14, C.si, 'part sd', 1)));
    /* 晶碇（C3）：頸縮 → 肩 → 等徑段 → 尾錐。**四段分開畫**，
       驗收才量得出「頸縮比等徑段細」；畫成一根上下等粗的矩形＝C3 不過。*/
    g.push(part('sw_ingot',
      R(F.rodX - 7, 182, 14, 26, C.si, 'part neck', 1)
      + PA(`M${F.rodX - 7},208 L${F.rodX + 7},208 L${F.rodX + 48},246 L${F.rodX - 48},246Z`, C.si, 'part shld')
      + R(F.rodX - 48, 246, 96, 74, C.si, 'part body', 1)
      + PA(`M${F.rodX - 48},320 L${F.rodX + 48},320 L${F.rodX + 16},${FUR.meltT} L${F.rodX - 16},${FUR.meltT}Z`, C.si2, 'part tail')));
    /* ★★ 提拉方向：朝上（C2）。
       ⚠ 標註文字**不放在這裡** —— 這一整包幾何會被縮到 62%，字跟著縮就破 12px 下限。
       v2 之後那些標註是 HTML 卡片，錨點用 `fpt()` 換算回縮放後的位置。*/
    g.push(part('sw_pull', upArrow(F.rodX + 74, 214, 92)));
    g.push(part('sw_spin', spinArrow(F.rodX, 196, 26, C.cyan)
      + spinArrow((F.cruL + F.cruR) / 2, F.cruB + 22, 34, C.cyan)));
    /* 動畫只做一件事（§9）：一個小點沿著提拉方向**往上**跑，代表晶碇緩慢長出來。
       **不要讓熔湯翻騰** —— 那會讓人以為這張圖在講流體。*/
    g.push(`<circle r="4" fill="${C.cyan}" opacity=".9">`
      + `<animateMotion dur="6s" repeatCount="indefinite" path="M${F.rodX + 74},214 L${F.rodX + 74},122"/></circle>`);
    return g.join('');
  }
  /* 爐子縮到 62%：**只縮圖形、不縮字**。`fpt()` 是換算（螢幕 ＝ SC·x, SC·y ＋ SDY），
     卡片的錨點一律用它算 —— 幾何一改，錨點自己跟著走。*/
  const SC = 0.62, SDY = 20;
  const fpt = (x, y) => [+(x * SC).toFixed(1), +(y * SC + SDY).toFixed(1)];

  /* ================================================================ 區 D：8 吋 vs 12 吋（§1 右）
     §3-D D1 **兩圓半徑比必須真的是 2:3**（所以直接用 200／300 乘同一個 k）；
     D2 **兩圓上的方格必須一樣大**（所以共用同一個 CELL 常數）；
     D3 兩個圓都要有 notch；D4 兩圓邊緣都要畫殘缺方格。
     2026-09-23：從第三個章節搬到 §1 右半邊（原本那裡是「四句話」的文字框，整塊是空白感的來源）。*/
  const K = 0.36, CELL = 13, CGAP = 1.4;
  const CIR = { cx: 476, cy: 196, r8: 200 * K, r12: 300 * K };
  function sizeCompare() {
    const C2 = CIR, pitch = CELL + CGAP, cells = [];
    const n = Math.ceil((C2.r12 * 2) / pitch) + 2;
    const x0 = C2.cx - (n * pitch) / 2, y0 = C2.cy - (n * pitch) / 2;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const x = x0 + i * pitch, y = y0 + j * pitch;
        const cor = [[x, y], [x + CELL, y], [x, y + CELL], [x + CELL, y + CELL]];
        const d = cor.map((c) => Math.hypot(c[0] - C2.cx, c[1] - C2.cy));
        const mn = Math.min.apply(null, d), mx = Math.max.apply(null, d);
        if (mn > C2.r12) continue;                                   // 整格在大圓外
        let cls = 'c12', fill = C.si;
        if (mx > C2.r12) { cls = 'e12'; fill = C.si2; }              // 大圓邊緣的殘缺方格
        else if (mx <= C2.r8) { cls = 'c8'; fill = C.glass; }
        else if (mn <= C2.r8) { cls = 'e8'; fill = C.si2; }          // 小圓邊緣的殘缺方格
        cells.push(R(x, y, CELL, CELL, fill, cls, 1));
      }
    }
    const notch = (r) => PA(`M${C2.cx - 7},${C2.cy - r + 0.5} L${C2.cx},${C2.cy - r + 12} L${C2.cx + 7},${C2.cy - r + 0.5}Z`, 'var(--dg-bg)', 'notch');
    return `<clipPath id="swBig"><circle cx="${C2.cx}" cy="${C2.cy}" r="${C2.r12}"/></clipPath>`
      + `<circle class="part" cx="${C2.cx}" cy="${C2.cy}" r="${C2.r12}" fill="var(--dg-void)"/>`
      + `<g clip-path="url(#swBig)">${cells.join('')}</g>`
      + `<circle class="ring8" cx="${C2.cx}" cy="${C2.cy}" r="${C2.r8}" fill="none" stroke="${C.cyan}" stroke-width="1.6" stroke-dasharray="5 4"/>`
      + notch(C2.r12) + notch(C2.r8);
  }

  /* ================================================================ 區 B：晶碇 → 切片（章節 ①）
     §3-A C4 外圓研磨在切片**之前**；C5 notch 是晶碇上的一整條軸向溝；
     C6 切片用的是**一組平行鋼線**（多線鋸），不是圓盤鋸。*/
  const CYL = { x0: 40, x1: 240, h: 56, ry: 26 };
  /* ⚠ class 名稱不可以用 `cap` / `sub` / `hd` / `lbl` / `tag` / `frame` / `num` / `warn`
     —— 那幾個在 `diagrams.js` 的共用 `STYLE` 裡是**文字樣式**，而且都帶 `fill`，
     拿來當零件的 class 會讓那塊零件被染成文字色。*/
  function cylinder(yTop, fill) {
    const Y = CYL, yc = yTop + Y.h / 2;
    return R(Y.x0, yTop, Y.x1 - Y.x0, Y.h, fill, 'part cylbody')
      + EL(Y.x1, yc, 13, Y.h / 2, fill, 'part cylend')
      + EL(Y.x0, yc, 13, Y.h / 2, C.si2, 'part cylend2');
  }
  function areaB() {
    const Y = CYL;
    const y1 = 430, y2 = 550, y3 = 670;
    // ① 外圓研磨：磨掉的那一層畫成半透明的外殼
    const grind = part('sw_grind',
      `<g opacity=".45">${R(Y.x0, y1 - 9, Y.x1 - Y.x0, Y.h + 18, C.mute, 'part shell')}</g>`
      + cylinder(y1, C.si));
    // ② 刻 notch：**一整根從頭到尾的軸向溝**（不是切完之後在每一片上單獨挖）
    const notch = part('sw_notch', cylinder(y2, C.si)
      + R(Y.x0, y2 + 6, Y.x1 - Y.x0, 10, 'var(--dg-void)', 'part groove')
      + PA(`M${Y.x1 + 6},${y2 + 8} L${Y.x1 + 13},${y2 + 16} L${Y.x1 + 6},${y2 + 16}Z`, 'var(--dg-void)', 'part'));
    // ③ 線鋸切片：一組**平行鋼線**（≥ 8 條；少於 8 條看起來像圓盤鋸的輻條）
    const wires = [];
    for (let i = 0; i < 11; i++) {
      const x = Y.x0 + 12 + i * 17;
      wires.push(`<line class="wire" x1="${x}" y1="${y3 - 14}" x2="${x}" y2="${y3 + Y.h + 14}" stroke="${C.steel}" stroke-width="1.6"/>`);
    }
    const saw = part('sw_saw', cylinder(y3, C.si) + wires.join(''));
    const cap = (y, t, s1, s2) => T(Y.x1 + 40, y + 16, t, 'lbl') + T(Y.x1 + 40, y + 36, s1, 'sub')
      + (s2 ? T(Y.x1 + 40, y + 54, s2, 'sub') : '');
    return `<g>
      ${T(16, 400, '晶碇 → 切片（由上到下就是先後順序）', 'hd')}
      ${T(16, 420, '外圓研磨一定在切片之前；notch 刻在晶碇上，不是切完每片挖。', 'sub')}
      ${grind}${cap(y1, '① 外圓研磨', '約 306 mm 拉出，再磨到 300 mm。', '（示意，實際餘量各廠不同）')}
      ${notch}${cap(y2, '② 刻 notch', '沿著整根刻一條溝 —— 切完每一片都有', '同一個方位記號。')}
      ${saw}${cap(y3, '③ 線鋸切片', '一組平行鋼線同時切過去，', '一根晶碇切出上百片。')}</g>`;
  }

  /* ================================================================ 區 C：表面粗糙度階梯（章節 ②）
     §3-B S1（紅線）**五段的表面起伏必須一段比一段小，量得出來**。
     所以五段共用 `profile()`，只有 `amp` 不同、而且是從同一個遞減陣列取的。
     S4：加工損傷層只在前三段看得到，蝕刻之後消失。
     2026-09-23：一格從 146 收到 90 寬（660 畫布），所以抬頭與腳註都拆成兩行短句 ——
     **字級沒縮**，只是斷行變密。*/
  const STG = [
    { id: 'sw_ascut', t: ['① 切片後', '鋸痕＋損傷層'], u: ['這樣的片', '不能用'], amp: 9.0, dmg: true },
    { id: 'sw_edge', t: ['② 倒角', '只磨邊緣'], u: ['表面幾乎', '沒動'], amp: 7.2, dmg: true },
    { id: 'sw_lap', t: ['③ 研磨', '變成小波浪'], u: ['吃研磨液', '與磨粒'], amp: 4.6, dmg: true },
    { id: 'sw_etch', t: ['④ 蝕刻', '損傷層被移除'], u: ['吃蝕刻', '化學品'], amp: 2.2, dmg: false },
    /* ★ 2026-09-26 覆蓋普查：一格只有 90 寬，「鏡面，一條直線」「吃研磨液、拋光」七個字在閱讀模式伸進隔壁那格
       （跟 ⑥ 的「（選配）」疊 8px）→ 在標點處多斷一行；標題列改成底部對齊，所以多一行是往上長、不會壓到剖面。*/
    { id: 'sw_polish', t: ['⑤ 拋光', '鏡面，', '一條直線'], u: ['吃研磨液、', '拋光墊、', '鑽石碟'], amp: 0, dmg: false },
  ];
  const SG = { w: 90, gap: 8, x0: 16, top: 800, bot: 860 };
  /* 同一支函式畫五段的表面，只換 amp。**S1 因此自動成立** —— 手刻五段一定會有一段畫歪。
     amp = 0 就是一條直線（鏡面）。*/
  function profile(x, w, y, amp) {
    if (amp <= 0) return `<path class="prof" d="M${x},${y} L${x + w},${y}" stroke="${C.cover}" stroke-width="2" fill="none"/>`;
    const seg = 14, a = [];
    a.push(`M${x},${y}`);
    for (let i = 0; x + (i + 1) * seg <= x + w; i++) {
      const xx = x + i * seg;
      a.push(`L${(xx + seg / 2).toFixed(1)},${(y - amp).toFixed(1)} L${(xx + seg).toFixed(1)},${y}`);
    }
    return `<path class="prof" d="${a.join(' ')}" stroke="${C.cover}" stroke-width="1.8" fill="none" stroke-linejoin="round"/>`;
  }
  function areaC() {
    const g = STG.map((o, i) => {
      const x = SG.x0 + i * (SG.w + SG.gap);
      const body = R(x, SG.top, SG.w, SG.bot - SG.top, C.si2, 'part', 2)
        + (o.dmg ? R(x, SG.top, SG.w, 16, C.org, 'part dmg') : '')
        + profile(x, SG.w, SG.top, o.amp)
        // ② 倒角：只改邊緣、不改表面（S5）—— 所以只在兩個角上畫圓角記號
        + (o.id === 'sw_edge'
          ? LN(`M${x + 2},${SG.top + 16} Q${x + 2},${SG.top + 2} ${x + 16},${SG.top + 2}`, C.cyan, 2.2)
          + LN(`M${x + SG.w - 2},${SG.top + 16} Q${x + SG.w - 2},${SG.top + 2} ${x + SG.w - 16},${SG.top + 2}`, C.cyan, 2.2)
          : '');
      return part(o.id, body)
        + o.t.map((s, j) => T(x, SG.top - 14 - (o.t.length - 1 - j) * 16, s, 'lbl')).join('')
        + o.u.map((s, j) => T(x, SG.bot + 20 + j * 16, s, 'cap')).join('');
    }).join('');
    // ⑥ 磊晶（選配的最後一段）：在拋光面上長一層新的矽，**比基板薄很多**、中間有一條清楚的界線
    const ex = SG.x0 + 5 * (SG.w + SG.gap);
    /* 磊晶層 4px、基板 56px ＝ 差一個量級以上（§3-C E1 要求「至少差一個數量級的視覺厚度」）。*/
    const epi = part('sw_epi',
      R(ex, SG.top + 4, SG.w, (SG.bot - SG.top) - 4, C.si2, 'part epibase', 2)
      + R(ex, SG.top, SG.w, 4, C.si, 'part epi', 1)
      + LN(`M${ex},${SG.top + 4} L${ex + SG.w},${SG.top + 4}`, C.cover, 1.6));
    return `<g>
      ${T(16, 712, '切完的片不能用 —— 表面一級一級磨到鏡面', 'hd')}
      ${T(16, 732, '粗糙度只會變細，順序不能顛倒；磊晶一定在拋光之後。', 'sub')}
      ${g}
      ${epi}${T(ex, SG.top - 30, '⑥ 磊晶', 'lbl')}${T(ex, SG.top - 14, '（選配）', 'lbl')}
      ${T(ex, SG.bot + 20, '比基板薄得多', 'cap')}${T(ex, SG.bot + 36, '（長上去的）', 'cap')}</g>`;
  }

  /* ================================================================ 區 F：流程列（七格）＋ 再生晶圓（章節 ③）
     §3-E F1 順序寫死；F2 磊晶在最後且標「選配」；
     F3 **再生晶圓是灰色、畫在主線之外**，用一條返回箭頭接回去（它不是新片製程的一段）。
     ⚠ 不能用 `D.processBar()` —— 那支會輸出 data-seg，這張圖依 H4 一個都不能有。
     2026-09-23：七格從「橫排一列 980 寬」改成 **4 ＋ 3 兩列**（660 畫布），
     列與列之間用一條往下折的線接起來，順序照樣讀得出來。*/
  const FLOW = [
    { id: 'sw_poly', t: '① 多晶矽原料', s: ['高純度多晶矽。', '本圖不畫其製法。'] },
    { id: 'sw_cz', t: '② CZ 長晶', s: ['熔湯＋籽晶＋提拉', '→ 單晶晶碇。'] },
    { id: 'sw_grind2', t: '③ 外圓磨', s: ['306 → 300 mm，', '並刻 notch。'] },
    { id: 'sw_saw2', t: '④ 線鋸切片', s: ['多條鋼線同時切。'] },
    { id: 'sw_lap2', t: '⑤ 倒角研磨蝕刻', s: ['去鋸痕、損傷層。'] },
    { id: 'sw_polish2', t: '⑥ 拋光＋清洗', s: ['做到鏡面。'] },
    { id: 'sw_epi2', t: '⑦ 磊晶（選配）', s: ['長一層新的矽。', '不是每片都有。'] },
  ];
  const FB = { x: 16, y: 1020, w: 145, gap: 16, h: 70, cols: 4, row: 96 };
  function pbar() {
    return FLOW.map((o, i) => {
      const x = FB.x + (i % FB.cols) * (FB.w + FB.gap), y = FB.y + Math.floor(i / FB.cols) * FB.row;
      const box = part(o.id, R(x, y, FB.w, FB.h, 'var(--dg-step-f)', 'part st', 7)
        + T(x + 10, y + 22, o.t, 'lbl')
        + o.s.map((t, j) => T(x + 10, y + 42 + j * 17, t, 'sub')).join(''));
      let arrow = '';
      if (i < FLOW.length - 1) {
        arrow = (i % FB.cols === FB.cols - 1)
          ? LN(`M${x + FB.w},${y + FB.h / 2} h8 V${y + FB.h + 13} H${FB.x - 8} V${y + FB.row + FB.h / 2} h8`, C.cyan, 2)
          : LN(`M${x + FB.w},${y + FB.h / 2} L${x + FB.w + FB.gap},${y + FB.h / 2}`, C.cyan, 2);
      }
      return box + arrow;
    }).join('');
  }
  function areaF() {
    return `<g>
      ${T(16, 1000, '製程流程（七格）—— 順序不准對調：磊晶一定在拋光之後', 'hd')}
      ${pbar()}
      <!-- ★ 2026-09-23：七格改成 4＋3 兩列之後，再生晶圓那一塊不能再放在右上（會壓在第二列上），
           改放在兩列的正下方；返回箭頭沿左緣繞回第 ① 格 —— 它仍然是「主線之外的另一條路」。-->
      ${part('sw_reclaim', R(360, 1212, 284, 70, 'var(--dg-frame-f)', 'part', 7)
      + T(372, 1234, '（灰）再生晶圓', 'lbl', null, `fill:${C.mute}`)
      + T(372, 1254, '用過的測試片重新磨回可用。', 'sub', null, `fill:${C.mute}`)
      + T(372, 1272, '不是主線的一段。', 'sub', null, `fill:${C.mute}`))}
      ${LN(`M360,1247 H8 V${FB.y + 35} H${FB.x - 4}`, C.mute, 1.4, ' stroke-dasharray="5 4"')}
      ${PA(`M${FB.x},${FB.y + 35} L${FB.x - 10},${FB.y + 30} L${FB.x - 10},${FB.y + 40}Z`, C.mute)}
      ${T(30, 1200, '← 另一條路：回收再利用（沿左邊繞回第 ① 格）', 'cap', null, `fill:${C.mute}`)}

      ${frame(16, 1300, 628, 168)}
      ${T(30, 1324, '這張圖上的段，台股是誰（信心：中，來源為媒體與公司網站整理）', 'hd')}
      ${T(30, 1346, '① 多晶矽原料：本圖查不到台股的具名對應 —— 查不到就寫查不到。', 'sub')}
      ${T(30, 1366, '② CZ 長晶／③ 外圓磨＋notch／④ 線鋸切片／⑤ 倒角研磨蝕刻／⑥ 拋光清洗：', 'sub')}
      ${T(30, 1384, '　 6488 環球晶、3532 台勝科、6182 合晶。③～⑤ 是矽晶圓廠的內部工序，', 'sub')}
      ${T(30, 1402, '　 本圖查不到專做這幾道工序的台股獨立廠商。', 'sub')}
      ${T(30, 1422, '⑦ 磊晶（選配）：6488 環球晶（產品含磊晶片）、6182 合晶（產品含磊晶矽晶圓）。', 'sub')}
      ${T(30, 1442, '（灰）再生晶圓：8028 昇陽半導體（以再生晶圓起家）、1560 中砂（再生晶圓是其三大事業', 'sub')}
      ${T(30, 1460, '　 之一，掛在「前段製程材料」族群）。⑥ 拋光吃的耗材不是這一格的公司做的。', 'sub')}</g>`;
  }

  /* ================================================================ 整張圖 */
  function siliconWafer() {
    const f = {
      seed: fpt(FUR.rodX, 175), ingot: fpt(FUR.rodX, 280), melt: fpt(FUR.rodX, 352),
      cru: fpt(FUR.cruL + 4, 386), heat: fpt(FUR.cruL - 25, 370), sus: fpt(FUR.cruL + 2, 428),
      cham: fpt(FUR.wallL + 5, 120), pull: fpt(FUR.rodX + 74, 150),
      /* ★ 2026-09-23：③ 旋轉的錨點從「晶碇上那支旋轉箭頭」(rodX, 196) 換到
         「坩堝底下那支旋轉箭頭」((cruL+cruR)/2, cruB+22) —— 同一個零件 sw_spin 的另一支箭頭，
         語意一樣正確（§「晶碇與坩堝各轉」講的就是這兩支）。
         為什麼要換：爐子縮到 SC=0.62 之後**只縮圖形、不縮字**，
         而編號圓點（r=9.5，直徑 19px）是「字」那一邊 —— 它不跟著縮。
         ① 籽晶在爐內 y=175、③ 旋轉在 y=196，相距 21 個爐內單位，
         換算到畫布只剩 21 × 0.62 ＝ 13px，比編號文字的高度（14px）還小，
         於是「01」與「03」兩顆編號直接相貼（深色 1px、淺色 2px，六個寬度全中）。
         換到坩堝那支之後畫布上相距 168px，離最近的 ⑧ 石墨承座也有 53px。
         ⚠ 這一類「錨點跟著幾何縮、編號不跟著縮」的碰撞，只有逐張打開剖析圖才量得到
            （`_preview.py` 不會逐張打開），所以新增錨點時要自己算一次間距：
            兩個編號錨點的畫布距離至少要 20px，也就是爐內座標至少差 32 個單位。*/
      spin: fpt((FUR.cruL + FUR.cruR) / 2, FUR.cruB + 22),
    };
    return `<svg class="dg dgm rs dgsw2" viewBox="0 0 ${CW} 1500" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（DECISIONS #231）。
           這張圖**一個 data-seg 都沒有**（§7-D1），所以 diagrams.js 那一整組
           「.dg [data-seg] …」的規則一條都吃不到 —— 描邊與高亮要在這裡自己給。
           顏色一律走 --dg-*，JS 與這裡都沒有寫死色票。*/
        svg.dgsw2 [data-part] .part{stroke:var(--dg-part-mix);stroke-width:.9;transition:stroke .15s,filter .15s}
        svg.dgsw2 [data-part]{cursor:default}
        svg.dgsw2 [data-part]:hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgsw2 [data-part].sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.4;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgsw2 .leader{fill:none;stroke:var(--dg-line-mix);stroke-width:1}
        svg.dgsw2 .anc .anchor{fill:var(--dg-card-c,var(--dg-accent-2d))}
      </style>
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">矽晶圓：從熔湯到一片鏡面</text>
      <text class="cap ext" x="0" y="0">一鍋熔湯 → 一根拉出來的單晶柱子 → 一片磨到鏡面的圓片。左邊是 CZ 提拉法長晶爐的剖面：★ 看得到液面，才是 CZ —— 碳化矽與氮化鎵用的是昇華法（PVT），爐子裡沒有液面。右邊是 8 吋與 12 吋的同比例對照：方格一樣大（同一顆晶粒），暗色的是切不出完整晶粒的邊緣格子。★ 誰做的：長晶到拋光是 6488 環球晶／3532 台勝科／6182 合晶，再生晶圓是 8028 昇陽半導體 —— 逐段名單見第 ③ 段。晶碇到切片、粗糙度階梯、製程七格與台股名單收在下面三段。</text>

      <!-- ================= §1 兩個命題並排（永遠看得到） ================= -->
      ${T(16, 52, 'CZ 提拉法長晶爐（剖面）', 'hd')}
      ${T(372, 52, '為什麼晶圓越大越划算', 'hd')}
      ${fx.shadows(`<rect x="44" y="${(FUR.wallT * SC + SDY + 6).toFixed(1)}" width="${((FUR.wallR - FUR.wallL) * SC).toFixed(1)}" height="${((FUR.wallB - FUR.wallT) * SC).toFixed(1)}" rx="8"/>`)}
      <!-- ⚠ 外面一定要再包一層 g：wireFolds() 的 solidBottom 量的是 **svg 直屬子節點**的 getBBox()，
           而 getBBox() **不含元素自己的 transform** —— 縮放群組直接當 svg 的子節點，量到的會是
           縮放前的 460 而不是縮放後的 305，於是第一條章節列被推到下面，中間空出一大塊
           （2026-09-23 實測：收合高度 604px，其中 120px 是這個假的底部撐出來的）。
           多包一層之後量的是「子孫含 transform 的聯集」，數字就對了。-->
      <g><g transform="translate(0,${SDY}) scale(${SC})">${furnace()}</g></g>
      ${part('sw_size', sizeCompare())}
      ${T(16, 322, '一邊轉、一邊往上拉，凝固成一根單晶柱。', 'cap')}
      ${T(16, 340, '★ 看得到液面，才是 CZ 提拉爐。', 'cap', null, `fill:${C.warn}`)}
      ${T(372, 322, '外圈 300 mm（12 吋）、內圈 200 mm（8 吋）：', 'cap')}
      ${T(372, 340, '(300 / 200)² = 2.25 倍，邊緣浪費比例也更小。', 'cap')}

      <!-- ================= 說明卡片（HTML，左欄＝長晶爐；右欄＝尺寸與四句話） ================= -->
      ${card({ part: 'sw_seed', no: 1, side: 'l', color: C.si, ax: f.seed[0], ay: f.seed[1], title: '籽晶（seed）與籽晶桿', sub: ['一顆籽晶沾上熔湯，熔湯就照著它的晶格重新排列 —— 整根柱子因此是一顆單晶，不是一堆晶粒。'] })}
      ${card({ part: 'sw_pull', no: 2, side: 'l', color: C.cyan, ax: f.pull[0], ay: f.pull[1], title: '提拉方向（往上）', sub: ['一邊轉、一邊往上拉 —— 這就是「提拉法（Czochralski，CZ）」。畫成往下就是把柱子推進湯裡，物理上不成立。'] })}
      ${card({ part: 'sw_spin', no: 3, side: 'l', color: C.cyan, ax: f.spin[0], ay: f.spin[1], title: '旋轉（晶碇與坩堝各轉）', sub: ['把熱場與圓柱幾何維持住 —— 不轉就長不出等徑的單晶。'] })}
      ${card({ part: 'sw_ingot', no: 4, side: 'l', color: C.si, ax: f.ingot[0], ay: f.ingot[1], title: '晶碇（ingot／boule）', sub: ['先拉細（頸縮）把差排甩掉，再放大到目標直徑（肩），中間是等徑段，最後收成尾錐。', '畫成一根上下等粗的圓柱就少了 CZ 的識別特徵。'] })}
      ${card({ part: 'sw_melt', no: 5, side: 'l', color: C.hot, ax: f.melt[0], ay: f.melt[1], title: '熔湯（melt）—— ★ 看得到液面', sub: ['多晶矽在石英坩堝裡熔成一鍋湯。看得到液面，才是 CZ 提拉爐；PVT 昇華爐裡沒有液面。'] })}
      ${card({ part: 'sw_crucible', no: 6, side: 'l', color: C.glass, ax: f.cru[0], ay: f.cru[1], title: '石英坩堝', sub: ['裝熔湯的那個碗。它是消耗品 —— 一次長晶就報廢一個。'] })}
      ${card({ part: 'sw_heater', no: 7, side: 'l', color: C.hot2, ax: f.heat[0], ay: f.heat[1], title: '加熱器（環繞坩堝側面）', sub: ['不是裝在爐子頂上。熱場決定長晶速度與缺陷密度。'] })}
      ${card({ part: 'sw_susceptor', no: 8, side: 'l', color: C.el, ax: f.sus[0], ay: f.sus[1], title: '石墨承座（示意）', sub: ['包在石英坩堝外面撐住它。⚠ 這一件本圖沒有查證到可引用的來源，只畫成示意、不寫規格。'] })}
      ${card({ part: 'sw_chamber', no: 9, side: 'l', color: C.steel2, ax: f.cham[0], ay: f.cham[1], title: '爐體（chamber）', sub: ['長晶要在受控氣氛與受控熱場裡進行。爐內氣氛與熱屏配置本圖沒有查證，只畫外殼。'] })}
      ${card({ part: 'sw_size', no: 10, side: 'r', color: C.si, ax: CIR.cx + CIR.r12 - 6, ay: CIR.cy, title: '8 吋 vs 12 吋（同一個比例）', sub: ['兩圓半徑比就是 200:300；方格在兩個圓上一樣大（同一顆晶粒）。', '暗色的是切不出完整晶粒的格子 —— 圓越大，浪費掉的邊緣比例越小。格數為示意。'] })}
      ${note({ side: 'r', order: 0, title: '看完要能自己講出這四句', lines: ['① 晶圓不是「切出來」的，是「拉出來」的：籽晶沾上熔湯，一邊轉一邊往上拉，凝固成一根單晶柱。', '② 拉出來的柱子比目標大一圈，要先磨小再切：約 306 mm 拉出 → 外圓磨到 300 mm → 刻 notch → 多線鋸切片。', '③ 切完的片不能用，要一級一級磨到鏡面：粗糙度一路變細、順序不能顛倒；磊晶一定在拋光之後。', '④ 12 吋的面積是 8 吋的 2.25 倍，邊緣浪費比例也更小 —— 這兩件事加起來就是「晶圓越大越划算」。'] })}
      ${note({ side: 'r', order: 1, warn: true, title: '★ 誰做的（結論）', lines: ['長晶到拋光：6488 環球晶、3532 台勝科、6182 合晶；再生晶圓：8028 昇陽半導體、1560 中砂。', '★ 5483 中美晶是 6488 環球晶的母公司（2011 年分割出去的子公司，來源：中美晶官網）—— 兩者是母子不是競爭對手，所以不把它跟環球晶並列在同一段；本圖也查不到中美晶目前自有矽晶圓產品線的具名資料。'] })}
      ${note({ side: 'l', order: 98, title: '示意圖，非實物比例', lines: ['爐體與各層厚度均為誇張放大。本圖講矽晶圓；碳化矽與氮化鎵用的是昇華法（PVT），爐子長得不一樣，見「第三代半導體」那張。', '本圖止於「一片可以進晶圓廠的晶圓」；之後的製程見「晶圓代工」那張。只講半導體級矽晶圓，不含太陽能矽晶圓；不寫任何良率、市占率、產能、單價與漲價幅度。'] })}
      ${note({ side: 'l', order: 99, warn: true, title: '★ 為什麼點零件不會篩成分股', lines: ['供應鏈資料的半導體鏈 14 個環節裡沒有一格是矽晶圓，這五檔也一檔都不在裡面 —— 所以這張圖一個 data-seg 都沒掛。那不是壞掉，是誠實：掛 semi_material 等於宣稱光洋科做矽晶圓。'] })}

      <!-- ================= ① 晶碇 → 切片（預設收合） ================= -->
      ${fold('sw2', '① 晶碇 → 切片：外圓研磨、刻 notch、多線鋸',
      '由上到下就是先後順序：306→300 mm、一整條軸向溝、一組平行鋼線', areaB())}

      <!-- ================= ② 粗糙度階梯（預設收合） ================= -->
      ${fold('sw3', '② 切完的片不能用：表面一級一級磨到鏡面',
      '五段的起伏一段比一段小、損傷層在蝕刻之後消失、磊晶一定在拋光之後', areaC())}

      <!-- ================= ③ 製程七格 ＋ 每一段台股是誰（預設收合） ================= -->
      ${fold('sw4', '③ 製程流程七格 ＋ 這張圖上每一段台股是誰',
      '多晶矽→長晶→外圓磨→切片→研磨→拋光→磊晶、再生晶圓支線，以及逐段的台股名單', areaF())}
    </svg>`;
  }

  window.DG.register('silicon_wafer', {
    level: 'group', chain: 'semiconductor',
    name: '矽晶圓：從熔湯到一片鏡面',
    draw: siliconWafer, native: CW, scene: 'silicon_wafer',   /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。檔頭 §0 原本寫「不做真 3D」，
                       那個判斷被推翻的理由寫在 site/three3d.js 的 SCENES.silicon_wafer 檔頭（一句話：這張圖最重要的那件事本來就是三維的）。2D 的 data-part 與 3D 的 part 是同一組，所以切過去還是選著同一個零件。*/
    q: '一片 12 吋晶圓是怎麼長出來的？為什麼晶圓越大越划算？台股這五家各自做到哪一段？',
    /* ⚠ 這張圖**沒有 data-seg**，所以 `renderPartCard()` 目前不會顯示小卡（`if (!seg)` 就藏起來）。
       照樣逐件寫齊，理由跟 `wide_bandgap.js` 一樣：① 這是這份對應該住的地方；
       ② industry.js 一支援就自己亮起來；③ 在那之前「誰做的」已經印在畫面上（台股標示線）。
       `cos` 一律留空 —— 這五檔都不在 supply_chain.yaml，寫了也查不到。*/
    parts: {
      sw_melt: {
        name: '熔湯（melt）',
        desc: '多晶矽在石英坩堝裡熔成一鍋湯。★ 看得到液面，才是 CZ 提拉爐 —— 碳化矽與氮化鎵用的是昇華法（PVT），爐子裡沒有液面。',
        none: '熔湯與長晶爐是矽晶圓廠自己的產線，不是外購的零件。★ 供應鏈資料的半導體鏈 14 格裡沒有一格是矽晶圓，所以這張圖不掛環節、點了不會篩。做長晶這一段的台股是 6488 環球晶、3532 台勝科、6182 合晶（信心：中，來源為媒體與公司網站整理）。',
      },
      sw_seed: {
        name: '籽晶（seed）與籽晶桿',
        desc: '一顆籽晶沾上熔湯，熔湯就照著它的晶格重新排列 —— 整根柱子因此是一顆單晶，不是一堆晶粒。',
        none: '籽晶與提拉是 CZ 法的核心動作。同上，這一格在供應鏈資料裡沒有對應環節。',
      },
      sw_pull: {
        name: '提拉方向（往上）',
        desc: '一邊轉、一邊往上拉 —— 這就是「提拉法（Czochralski，CZ）」。畫成往下就是在把柱子推進湯裡，物理上不成立。',
        none: '同上：這一格在供應鏈資料裡沒有對應環節。',
      },
      sw_spin: { name: '旋轉（晶碇與坩堝各轉）', desc: '晶碇與坩堝各自旋轉，是為了把熱場與圓柱幾何維持住 —— 不轉就長不出等徑的單晶。' },
      sw_ingot: {
        name: '晶碇（ingot／boule）',
        desc: '由籽晶往下長成一根圓柱：先拉細（頸縮）把差排甩掉，再放大到目標直徑（肩），中間是等徑段，最後收成尾錐。畫成一根上下等粗的圓柱就少了 CZ 的識別特徵。',
        none: '★ 6488 環球晶是 5483 中美晶 2011 年分割出去的子公司（來源：中美晶官網），兩者是母子不是競爭對手 —— 圖上刻意不把它們並列在同一段。本圖查不到中美晶目前自有矽晶圓產品線的具名資料。',
      },
      sw_chamber: { name: '爐體（chamber）', desc: '長晶要在受控氣氛與受控熱場裡進行。爐內的氣氛與熱屏配置本圖沒有查證，所以只畫外殼，不寫配置。' },
      sw_crucible: { name: '石英坩堝', desc: '裝熔湯的那個碗。它是消耗品 —— 一次長晶就報廢一個。' },
      sw_susceptor: { name: '石墨承座（示意）', desc: '包在石英坩堝外面撐住它。⚠ 這一件本圖沒有查證到可引用的來源，只畫成示意、不寫規格。' },
      sw_heater: { name: '加熱器', desc: '環繞在坩堝的側面（不是裝在爐子頂上）。熱場決定長晶速度與缺陷密度。' },
      sw_grind: {
        name: '① 外圓研磨',
        desc: '先拉到約 306 mm，再把外圓磨到 300 mm。一定在切片之前 —— 切完再一片一片磨外圓，實務上不成立。（只有一個來源，實際餘量各廠不同。）',
        none: '外圓研磨是矽晶圓廠的內部工序，本圖查不到專做這道工序的台股獨立廠商。',
      },
      sw_notch: {
        name: '② 刻 notch',
        desc: '沿著整根晶碇刻一條軸向的溝，切完每一片自然都有同一個方位記號。畫成「切完之後在每一片上單獨挖一個缺口」就是錯的。',
        none: '同上，本圖查不到專做這道工序的台股獨立廠商。',
      },
      sw_saw: {
        name: '③ 線鋸切片',
        desc: '一組平行的鋼線同時切過去（多線鋸），一根晶碇切出上百片。畫成單一圓盤鋸＝畫的是二十年前的做法。切幾片取決於碇長、片厚與鋸縫，本圖不寫確切片數。',
        none: '同上，本圖查不到專做這道工序的台股獨立廠商。',
      },
      sw_ascut: { name: '④ 切片後（as-cut）', desc: '表面是明顯的鋸痕，下面還有一層加工損傷層 —— 這樣的片不能用。' },
      sw_edge: { name: '⑤ 倒角（edge rounding）', desc: '把邊緣的直角磨成圓角，避免崩邊。★ 它只改邊緣、不改表面 —— 把倒角畫成「整片變平滑」是混淆兩件事。' },
      sw_lap: {
        name: '⑥ 研磨（lapping）',
        desc: '上下研磨盤夾著晶片、供應含磨粒的漿料，把鋸齒磨成小很多的波浪，損傷層跟著變薄。',
        none: '研磨用的耗材（研磨液、磨粒）不是這一格的公司做的，見「前段製程材料」那張。',
      },
      sw_etch: { name: '⑦ 蝕刻（etching）', desc: '用化學的方式把殘留的加工損傷層移除。損傷層在這一段之後就不該再畫出來了。' },
      sw_polish: {
        name: '⑧ 拋光（polishing／CMP）',
        desc: '磨到鏡面，表面在剖面上是一條直線。拋光一定是最後一道表面加工 —— 拋完再畫一段研磨就是順序錯了。',
        none: '★ 這一站吃的鑽石碟由 1560 中砂做（信心：中，來源為投顧與產業媒體整理）—— 但 1560 掛在「前段製程材料」族群、不在這一格，而且不在供應鏈資料裡。',
      },
      sw_epi: {
        name: '⑨ 磊晶（epitaxy，選配）',
        desc: '在鏡面上長一層新的矽。它比底下的基板薄得多 —— 因為它是長上去的，不是切出來的；兩者之間有一條清楚的界線。磊晶一定在拋光之後，粗糙面上長不出可用的單晶層。',
        none: '台股做磊晶片的是 6488 環球晶（產品含磊晶片）與 6182 合晶（產品含磊晶矽晶圓）。⚠ 碳化矽／氮化鎵磊晶是另一回事，那是 3016 嘉晶，在「第三代半導體」那張。',
      },
      sw_size: {
        name: '8 吋 vs 12 吋',
        desc: '兩個圓的半徑比就是 200：300，所以面積比是 (300/200)² = 2.25 倍 —— 這是算出來的，不是引用來的。方格在兩個圓上一樣大（代表同一顆晶粒），暗色的那些是切不出完整晶粒的格子：圓越大，浪費掉的邊緣比例越小。',
        none: '尺寸對比不是零件。本圖不寫任何價格、良率、市占率。',
      },
      sw_poly: {
        name: '① 多晶矽原料',
        desc: '長晶的原料。本圖沒有查它的製法（西門子法），也查不到台股的具名對應 —— 查不到就寫查不到。',
        none: '本圖查不到多晶矽原料的台股具名對應。',
      },
      sw_cz: { name: '② CZ 長晶', desc: '熔湯＋籽晶＋旋轉提拉 → 單晶晶碇。台股：6488 環球晶、3532 台勝科、6182 合晶（信心：中）。' },
      sw_grind2: { name: '③ 外圓磨＋刻 notch', desc: '306 → 300 mm，並刻出定位用的缺口。屬矽晶圓廠的內部工序。' },
      sw_saw2: { name: '④ 線鋸切片', desc: '多條鋼線同時切。屬矽晶圓廠的內部工序。' },
      sw_lap2: { name: '⑤ 倒角／研磨／蝕刻', desc: '去鋸痕、去損傷層。屬矽晶圓廠的內部工序。' },
      sw_polish2: { name: '⑥ 拋光＋清洗', desc: '做到鏡面。耗材（研磨液、拋光墊、鑽石碟）不是這一格的公司做的。' },
      sw_epi2: { name: '⑦ 磊晶（選配）', desc: '不是每一片晶圓都有磊晶層，所以標「選配」。台股：6488 環球晶、6182 合晶。' },
      sw_reclaim: {
        name: '再生晶圓（另一條路）',
        desc: '把用過的測試片重新磨回可用。★ 它不是新片製程的一段，所以畫成灰色、放在主線之外，用一條返回箭頭接回去。',
        none: '台股：8028 昇陽半導體（以再生晶圓起家，後擴到晶圓薄化服務）、1560 中砂（再生晶圓是其三大事業之一）。兩家都不在供應鏈資料裡。',
      },
    },
  });
})();
