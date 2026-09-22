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

  const W = 980;

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

  /* ★★ 提拉箭頭（§3-A C2，紅線）。**只接受往上**：傳進來的 `len` 一律往 -y 走，
     所以這支在物理上畫不出一支朝下的提拉箭頭。畫反是這張圖最容易錯的一條。*/
  function upArrow(x, yBottom, len, col) {
    const yTop = yBottom - Math.abs(len);
    return `<path class="arw" d="M${x},${yBottom} L${x},${yTop + 8}" stroke="${col || 'var(--dg-accent-2d)'}" stroke-width="2.4" fill="none"/>`
      + `<path class="arwh" d="M${x},${yTop} L${x - 5},${yTop + 10} L${x + 5},${yTop + 10}Z" fill="${col || 'var(--dg-accent-2d)'}"/>`;
  }
  // 旋轉箭頭（一段圓弧 ＋ 一個箭頭）。晶碇與坩堝各一個。
  function spinArrow(cx, cy, r, col) {
    return `<path class="spn" d="M${cx - r},${cy} A${r},${r * 0.42} 0 0 0 ${cx + r},${cy}" stroke="${col}" stroke-width="1.8" fill="none"/>`
      + `<path d="M${cx + r},${cy} L${cx + r - 7},${cy - 5} L${cx + r - 2},${cy + 6}Z" fill="${col}"/>`;
  }

  /* ================================================================ 區 A：CZ 長晶爐剖面
     §3-A：熔湯在下、籽晶在上（C1）；提拉箭頭朝上（C2）；
     晶碇有頸縮／肩／等徑段／尾錐（C3）；加熱器環繞坩堝**側面**（C8）。*/
  const FUR = {
    wallL: 66, wallR: 414, wallT: 96, wallB: 446,     // 爐體
    cruL: 152, cruR: 328, cruT: 322, cruB: 424,       // 石英坩堝（U 形）
    meltT: 350, meltB: 414,                            // 熔湯：液面 y=350（CZ 的識別特徵）
    rodX: 240,
  };
  function furnace() {
    const F = FUR, g = [];
    // 爐體：外殼 ＋ 內腔
    g.push(part('sw_chamber', R(F.wallL, F.wallT, F.wallR - F.wallL, F.wallB - F.wallT, 'var(--dg-steel-2)', 'part', 10)
      + R(F.wallL + 10, F.wallT + 10, F.wallR - F.wallL - 20, F.wallB - F.wallT - 20, 'var(--dg-void)', 'part', 6)));
    // 加熱器：**環繞坩堝側面**（不是畫在爐子頂上）
    g.push(part('sw_heater', R(F.cruL - 34, F.cruT - 8, 18, (F.cruB + 8) - (F.cruT - 8), 'var(--dg-hot-2)', 'part', 3)
      + R(F.cruR + 16, F.cruT - 8, 18, (F.cruB + 8) - (F.cruT - 8), 'var(--dg-hot-2)', 'part', 3)));
    // 石墨承座（示意，§7-B3 低信心）：包在石英坩堝外面
    g.push(part('sw_susceptor', PA(`M${F.cruL - 12},${F.cruT - 6} L${F.cruL - 12},${F.cruB - 24} `
      + `Q${F.cruL - 12},${F.cruB + 12} ${(F.cruL + F.cruR) / 2},${F.cruB + 12} `
      + `Q${F.cruR + 12},${F.cruB + 12} ${F.cruR + 12},${F.cruB - 24} L${F.cruR + 12},${F.cruT - 6} `
      + `L${F.cruR},${F.cruT - 6} L${F.cruR},${F.cruB - 24} Q${F.cruR},${F.cruB} ${(F.cruL + F.cruR) / 2},${F.cruB} `
      + `Q${F.cruL},${F.cruB} ${F.cruL},${F.cruB - 24} L${F.cruL},${F.cruT - 6}Z`, 'var(--dg-el)', 'part')));
    // 石英坩堝（U 形，半透明淺色）
    g.push(part('sw_crucible', PA(`M${F.cruL},${F.cruT} L${F.cruL},${F.cruB - 26} `
      + `Q${F.cruL},${F.cruB} ${(F.cruL + F.cruR) / 2},${F.cruB} Q${F.cruR},${F.cruB} ${F.cruR},${F.cruB - 26} `
      + `L${F.cruR},${F.cruT} L${F.cruR - 9},${F.cruT} L${F.cruR - 9},${F.cruB - 28} `
      + `Q${F.cruR - 9},${F.cruB - 9} ${(F.cruL + F.cruR) / 2},${F.cruB - 9} `
      + `Q${F.cruL + 9},${F.cruB - 9} ${F.cruL + 9},${F.cruB - 28} L${F.cruL + 9},${F.cruT}Z`,
      'var(--dg-pn-glass)', 'part')));
    /* ★★ 熔湯（§3-A C7）：**液面畫得出來**就是 CZ 跟 PVT 昇華爐唯一的差別。
       液面那條亮線帶 class="surf"，驗收直接量它在不在、在什麼高度。*/
    g.push(part('sw_melt', PA(`M${F.cruL + 9},${F.meltT} L${F.cruL + 9},${F.meltB - 20} `
      + `Q${F.cruL + 9},${F.meltB} ${(F.cruL + F.cruR) / 2},${F.meltB} `
      + `Q${F.cruR - 9},${F.meltB} ${F.cruR - 9},${F.meltB - 20} L${F.cruR - 9},${F.meltT}Z`, 'var(--dg-hot)', 'part')
      + LN(`M${F.cruL + 9},${F.meltT} L${F.cruR - 9},${F.meltT}`, 'var(--dg-cover)', 2.4, ' class="surf"')));
    // 籽晶桿 ＋ 籽晶（**在最上方**，C1）
    g.push(part('sw_seed', R(F.rodX - 5, 106, 10, 62, 'var(--dg-steel)', 'part rod', 2)
      + R(F.rodX - 9, 168, 18, 14, 'var(--dg-si)', 'part sd', 1)));
    /* 晶碇（C3）：頸縮 → 肩 → 等徑段 → 尾錐。**四段分開畫**，
       驗收才量得出「頸縮比等徑段細」；畫成一根上下等粗的矩形＝C3 不過。*/
    g.push(part('sw_ingot',
      R(F.rodX - 7, 182, 14, 26, 'var(--dg-si)', 'part neck', 1)
      + PA(`M${F.rodX - 7},208 L${F.rodX + 7},208 L${F.rodX + 48},246 L${F.rodX - 48},246Z`, 'var(--dg-si)', 'part shld')
      + R(F.rodX - 48, 246, 96, 74, 'var(--dg-si)', 'part body', 1)
      + PA(`M${F.rodX - 48},320 L${F.rodX + 48},320 L${F.rodX + 16},${FUR.meltT} L${F.rodX - 16},${FUR.meltT}Z`, 'var(--dg-si-2)', 'part tail')));
    /* ★★ 提拉方向：朝上（C2）。
       ⚠ 標註文字**不放在這裡** —— 這一整包幾何在 areaA() 裡會被縮到 66%，
       字跟著縮就破 12px 下限（Andy 2026-09-22 只要求「圖片」縮小，字級是硬的）。
       所以文字畫在 areaA() 的未縮放座標系上，用引線接回來。*/
    g.push(part('sw_pull', upArrow(F.rodX + 74, 214, 92)));
    g.push(part('sw_spin', spinArrow(F.rodX, 196, 26, 'var(--dg-accent-2d)')
      + spinArrow((F.cruL + F.cruR) / 2, F.cruB + 22, 34, 'var(--dg-accent-2d)')));
    /* 動畫只做一件事（§9）：一個小點沿著提拉方向**往上**跑，代表晶碇緩慢長出來。
       **不要讓熔湯翻騰** —— 那會讓人以為這張圖在講流體。
       這是全圖唯一的 `animateMotion`；按「動畫：關」時 `svg.pauseAnimations()` 會把它停住，
       而靜止時提拉箭頭與旋轉箭頭（上面兩個 part）仍然看得見。*/
    g.push(`<circle r="4" fill="var(--dg-accent-2d)" opacity=".9">`
      + `<animateMotion dur="6s" repeatCount="indefinite" path="M${F.rodX + 74},214 L${F.rodX + 74},122"/></circle>`);
    return g.join('');
  }

  /* 爐子縮到 66%（Andy 2026-09-22：「圖片及文字縮小一半…希望能一次看到完整資訊」）。
     **只縮圖形、不縮字**：`SC`／`SDY` 把 furnace() 那包幾何壓進 x 44～273、y 57～289，
     標註文字則畫在未縮放的座標系上（x 288 起），用引線接回縮小後的位置。
     `fpt()` 就是那個換算：螢幕座標 ＝ (SC·x, SC·y + SDY)。*/
  const SC = 0.66, SDY = -6;
  const fpt = (x, y) => [x * SC, y * SC + SDY];
  function fLabel(ty, t, ax, ay) {
    const q = fpt(ax, ay);
    return LN(`M286,${ty - 4} L${(q[0] + 6).toFixed(1)},${q[1].toFixed(1)}`, 'var(--dg-mute)', 1)
      + T(288, ty, t, 'lbl');
  }
  function areaA() {
    return `<g>${frame(16, 52, 446, 240)}
      ${T(32, 74, '一、CZ 提拉法長晶爐（剖面）', 'hd')}
      <g transform="translate(0,${SDY}) scale(${SC})">${furnace()}</g>
      ${fLabel(102, '一邊轉、一邊往上拉', 314, 150)}
      ${fLabel(140, '籽晶（晶格的種子）', 240, 175)}
      ${fLabel(178, '晶碇：頸縮→肩→等徑', 240, 280)}
      ${fLabel(216, '熔湯 —— 看得到液面', 240, 352)}
      ${fLabel(254, '石英坩堝／加熱器', 150, 400)}</g>`;
  }

  /* ================================================================ 區 B：晶碇 → 切片（2.5D 三格）
     §3-A C4 外圓研磨在切片**之前**；C5 notch 是晶碇上的一整條軸向溝；
     C6 切片用的是**一組平行鋼線**（多線鋸），不是圓盤鋸。*/
  const CYL = { x0: 506, x1: 706, h: 56, ry: 26 };
  /* ⚠ class 名稱不可以用 `cap` / `sub` / `hd` / `lbl` / `tag` / `frame` / `num` / `warn`
     —— 那幾個在 `diagrams.js` 的共用 `STYLE` 裡是**文字樣式**，而且都帶 `fill`。
     CSS 的 fill 會蓋掉 SVG 的 `fill` 呈現屬性，所以拿來當零件的 class 會讓那塊零件
     被染成文字色（實測：磊晶那一段掛 `part sub` 就整塊變成 --dg-ink-3 的淺灰藍）。*/
  function cylinder(yTop, fill) {
    const C = CYL, yc = yTop + C.h / 2;
    return R(C.x0, yTop, C.x1 - C.x0, C.h, fill, 'part cylbody')
      + EL(C.x1, yc, 13, C.h / 2, fill, 'part cylend')
      + EL(C.x0, yc, 13, C.h / 2, 'var(--dg-si-2)', 'part cylend2');
  }
  function areaB() {
    const C = CYL;
    const y1 = 128, y2 = 244, y3 = 360;
    // ① 外圓研磨：磨掉的那一層畫成半透明的外殼
    const grind = part('sw_grind',
      `<g opacity=".45">${R(C.x0, y1 - 9, C.x1 - C.x0, C.h + 18, 'var(--dg-mute)', 'part shell')}</g>`
      + cylinder(y1, 'var(--dg-si)'));
    // ② 刻 notch：**一整根從頭到尾的軸向溝**（不是切完之後在每一片上單獨挖）
    const notch = part('sw_notch', cylinder(y2, 'var(--dg-si)')
      + R(C.x0, y2 + 6, C.x1 - C.x0, 10, 'var(--dg-void)', 'part groove')
      + PA(`M${C.x1 + 6},${y2 + 8} L${C.x1 + 13},${y2 + 16} L${C.x1 + 6},${y2 + 16}Z`, 'var(--dg-void)', 'part'));
    // ③ 線鋸切片：一組**平行鋼線**（≥ 8 條；少於 8 條看起來像圓盤鋸的輻條）
    const wires = [];
    for (let i = 0; i < 11; i++) {
      const x = C.x0 + 12 + i * 17;
      wires.push(`<line class="wire" x1="${x}" y1="${y3 - 14}" x2="${x}" y2="${y3 + C.h + 14}" stroke="var(--dg-steel)" stroke-width="1.6"/>`);
    }
    const saw = part('sw_saw', cylinder(y3, 'var(--dg-si)') + wires.join(''));
    const cap = (y, t, s1, s2) => T(C.x1 + 26, y + 16, t, 'lbl') + T(C.x1 + 26, y + 36, s1, 'sub')
      + (s2 ? T(C.x1 + 26, y + 54, s2, 'sub') : '');
    return `<g>${frame(480, 68, 476, 434)}
      ${T(496, 92, '二、晶碇 → 切片（由上到下就是先後順序）', 'hd')}
      ${T(496, 110, '外圓研磨一定在切片之前；notch 刻在晶碇上，不是切完每片挖。', 'sub')}
      ${grind}${cap(y1, '① 外圓研磨', '約 306 mm 拉出，再磨到 300 mm。', '（示意，實際餘量各廠不同）')}
      ${notch}${cap(y2, '② 刻 notch', '沿著整根刻一條溝 —— 切完每一片', '都有同一個方位記號。')}
      ${saw}${cap(y3, '③ 線鋸切片', '一組平行鋼線同時切過去，', '一根晶碇切出上百片。')}</g>`;
  }

  /* ================================================================ 區 C：表面粗糙度階梯
     §3-B S1（紅線）**五段的表面起伏必須一段比一段小，量得出來**。
     所以五段共用 `profile()`，只有 `amp` 不同、而且是從同一個遞減陣列取的。
     S4：加工損傷層只在前三段看得到，蝕刻之後消失。*/
  const STG = [
    { id: 'sw_ascut', t: '① 切片後：鋸痕＋損傷層', u: '這樣的片不能用', amp: 9.0, dmg: true },
    { id: 'sw_edge', t: '② 倒角：只磨邊緣', u: '表面幾乎沒動', amp: 7.2, dmg: true },
    { id: 'sw_lap', t: '③ 研磨：變成小波浪', u: '吃研磨液與磨粒', amp: 4.6, dmg: true },
    { id: 'sw_etch', t: '④ 蝕刻：損傷層被移除', u: '吃蝕刻化學品', amp: 2.2, dmg: false },
    { id: 'sw_polish', t: '⑤ 拋光：鏡面，一條直線', u: '吃研磨液、拋光墊、鑽石碟', amp: 0, dmg: false },
  ];
  const SG = { w: 146, gap: 8, x0: 22, top: 356, bot: 416 };
  /* 同一支函式畫五段的表面，只換 amp。**S1 因此自動成立** —— 手刻五段一定會有一段畫歪。
     amp = 0 就是一條直線（鏡面）。*/
  function profile(x, w, y, amp) {
    if (amp <= 0) return `<path class="prof" d="M${x},${y} L${x + w},${y}" stroke="var(--dg-cover)" stroke-width="2" fill="none"/>`;
    const seg = 14, a = [];
    a.push(`M${x},${y}`);
    for (let i = 0; x + (i + 1) * seg <= x + w; i++) {
      const xx = x + i * seg;
      a.push(`L${(xx + seg / 2).toFixed(1)},${(y - amp).toFixed(1)} L${(xx + seg).toFixed(1)},${y}`);
    }
    return `<path class="prof" d="${a.join(' ')}" stroke="var(--dg-cover)" stroke-width="1.8" fill="none" stroke-linejoin="round"/>`;
  }
  function areaC() {
    const g = STG.map((o, i) => {
      const x = SG.x0 + i * (SG.w + SG.gap);
      const body = R(x, SG.top, SG.w, SG.bot - SG.top, 'var(--dg-si-2)', 'part', 2)
        + (o.dmg ? R(x, SG.top, SG.w, 16, 'var(--dg-organic)', 'part dmg') : '')
        + profile(x, SG.w, SG.top, o.amp)
        // ② 倒角：只改邊緣、不改表面（S5）—— 所以只在兩個角上畫圓角記號
        + (o.id === 'sw_edge'
          ? LN(`M${x + 2},${SG.top + 16} Q${x + 2},${SG.top + 2} ${x + 16},${SG.top + 2}`, 'var(--dg-accent-2d)', 2.2)
          + LN(`M${x + SG.w - 2},${SG.top + 16} Q${x + SG.w - 2},${SG.top + 2} ${x + SG.w - 16},${SG.top + 2}`, 'var(--dg-accent-2d)', 2.2)
          : '');
      return part(o.id, body) + T(x, SG.top - 12, o.t, 'lbl') + T(x, SG.bot + 20, o.u, 'cap');
    }).join('');
    // ⑥ 磊晶（選配的最後一段）：在拋光面上長一層新的矽，**比基板薄很多**、中間有一條清楚的界線
    const ex = SG.x0 + 5 * (SG.w + SG.gap);
    /* 磊晶層 5px、基板 65px ＝ 差一個量級以上（§3-C E1 要求「至少差一個數量級的視覺厚度」）。
       階梯整區從 90px 高壓到 70px，**字一個都沒縮**。*/
    /* 磊晶層 4px、基板 56px ＝ 差一個量級以上（§3-C E1 要求「至少差一個數量級的視覺厚度」）。
       階梯整區從 90px 高壓到 60px，**字一個都沒縮**。*/
    const epi = part('sw_epi',
      R(ex, SG.top + 4, SG.w, (SG.bot - SG.top) - 4, 'var(--dg-si-2)', 'part epibase', 2)
      + R(ex, SG.top, SG.w, 4, 'var(--dg-si)', 'part epi', 1)
      + LN(`M${ex},${SG.top + 4} L${ex + SG.w},${SG.top + 4}`, 'var(--dg-cover)', 1.6));
    return `<g>${frame(16, 300, 940, 152)}
      ${T(32, 322, '三、切完的片不能用 —— 表面一級一級磨到鏡面（粗糙度只會變細，順序不能顛倒）', 'hd')}
      ${g}
      ${epi}${T(ex, SG.top - 12, '⑥ 磊晶（選配）', 'lbl')}
      ${T(ex, SG.bot + 20, '比基板薄得多（長上去的）', 'cap')}</g>`;
  }

  /* ================================================================ 區 D：8 吋 vs 12 吋
     §3-D D1 **兩圓半徑比必須真的是 2:3**（所以直接用 200／300 乘同一個 k）；
     D2 **兩圓上的方格必須一樣大**（所以共用同一個 CELL 常數）；
     D3 兩個圓都要有 notch；D4 兩圓邊緣都要畫殘缺方格。*/
  const K = 0.36, CELL = 13, CGAP = 1.4;
  const CIR = { cx: 150, cy: 900, r8: 200 * K, r12: 300 * K };
  function sizeCompare() {
    const C = CIR, pitch = CELL + CGAP, cells = [];
    const n = Math.ceil((C.r12 * 2) / pitch) + 2;
    const x0 = C.cx - (n * pitch) / 2, y0 = C.cy - (n * pitch) / 2;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const x = x0 + i * pitch, y = y0 + j * pitch;
        const cor = [[x, y], [x + CELL, y], [x, y + CELL], [x + CELL, y + CELL]];
        const d = cor.map((c) => Math.hypot(c[0] - C.cx, c[1] - C.cy));
        const mn = Math.min.apply(null, d), mx = Math.max.apply(null, d);
        if (mn > C.r12) continue;                                   // 整格在大圓外
        let cls = 'c12', fill = 'var(--dg-si)';
        if (mx > C.r12) { cls = 'e12'; fill = 'var(--dg-si-2)'; }   // 大圓邊緣的殘缺方格
        else if (mx <= C.r8) { cls = 'c8'; fill = 'var(--dg-pn-glass)'; }
        else if (mn <= C.r8) { cls = 'e8'; fill = 'var(--dg-si-2)'; }  // 小圓邊緣的殘缺方格
        cells.push(R(x, y, CELL, CELL, fill, cls, 1));
      }
    }
    const notch = (r) => PA(`M${C.cx - 7},${C.cy - r + 0.5} L${C.cx},${C.cy - r + 12} L${C.cx + 7},${C.cy - r + 0.5}Z`, 'var(--dg-bg)', 'notch');
    return `<clipPath id="swBig"><circle cx="${C.cx}" cy="${C.cy}" r="${C.r12}"/></clipPath>`
      + `<circle class="part" cx="${C.cx}" cy="${C.cy}" r="${C.r12}" fill="var(--dg-void)"/>`
      + `<g clip-path="url(#swBig)">${cells.join('')}</g>`
      + `<circle class="ring8" cx="${C.cx}" cy="${C.cy}" r="${C.r8}" fill="none" stroke="var(--dg-accent-2d)" stroke-width="1.6" stroke-dasharray="5 4"/>`
      + notch(C.r12) + notch(C.r8);
  }
  function areaD() {
    const C = CIR;
    return `<g>${frame(16, 766, 452, 314)}
      ${T(32, 790, '四、為什麼晶圓越大越划算', 'hd')}
      ${part('sw_size', sizeCompare())}
      ${LN(`M${C.cx},${C.cy} L${C.cx + C.r8},${C.cy}`, 'var(--dg-accent-2d)', 1.2, ' stroke-dasharray="3 3"')}
      ${LN(`M${C.cx},${C.cy + 6} L${C.cx + C.r12},${C.cy + 6}`, 'var(--dg-cover)', 1.2, ' stroke-dasharray="3 3"')}
      ${T(C.cx + C.r12 + 10, C.cy - 6, '外圈 300 mm（12 吋）', 'sub')}
      ${T(C.cx + C.r12 + 10, C.cy + 14, '內圈 200 mm（8 吋）', 'sub')}
      ${T(C.cx + C.r12 + 10, C.cy + 40, '面積比是算出來的：', 'sub')}
      ${T(C.cx + C.r12 + 10, C.cy + 60, '(300 / 200)² = 2.25 倍', 'lbl')}
      ${T(32, 1030, '方格在兩個圓上一樣大（同一顆晶粒）。暗色的是切不出完整', 'sub')}
      ${T(32, 1048, '晶粒的格子 —— 圓越大，浪費掉的邊緣比例越小。', 'sub')}
      ${T(32, 1066, '格數為示意；本圖不寫任何良率、產能、片數與價格。', 'cap')}</g>`;
  }

  /* ================================================================ 區 E：四句話（說明欄） */
  /* 四句話：每段從兩行副標砍成一行（Andy：「同一件事講三次，留一次」）。
     砍掉的那半句講的東西圖上本來就畫得出來，而且零件小卡裡逐條寫著。*/
  const SAY = [
    ['① 晶圓不是「切出來」的，是「拉出來」的。', '籽晶沾上熔湯，一邊轉一邊往上拉，凝固成一根單晶柱。'],
    ['② 拉出來的柱子比目標大一圈，要先磨小再切。', '約 306 mm 拉出 → 外圓磨到 300 mm → 刻 notch → 多線鋸切片。'],
    ['③ 切完的片不能用，要一級一級磨到鏡面。', '粗糙度一路變細、順序不能顛倒；磊晶一定在拋光之後。'],
    ['④ 12 吋的面積是 8 吋的 2.25 倍，邊緣浪費比例也更小。', '這兩件事加起來，就是「晶圓越大越划算」。'],
  ];
  function areaE() {
    const rows = SAY.map((o, i) => {
      const y = 100 + i * 46;
      return T(486, y, o[0], 'lbl') + T(486, y + 18, o[1], 'sub');
    }).join('');
    return `<g>${frame(470, 52, 486, 240)}
      ${T(486, 74, '二、看完要能自己講出這四句', 'hd')}
      ${rows}</g>`;
  }

  /* ================================================================ 區 F：流程列（七格）＋ 再生晶圓
     §3-E F1 順序寫死；F2 磊晶在最後且標「選配」；
     F3 **再生晶圓是灰色、畫在主線之外**，用一條返回箭頭接回去（它不是新片製程的一段）。
     ⚠ 不能用 `D.processBar()` —— 那支會輸出 data-seg，這張圖依 H4 一個都不能有。*/
  const FLOW = [
    { id: 'sw_poly', t: '① 多晶矽原料', s: ['高純度多晶矽。', '本圖不畫其製法。'] },
    { id: 'sw_cz', t: '② CZ 長晶', s: ['熔湯＋籽晶＋提拉', '→ 單晶晶碇。'] },
    { id: 'sw_grind2', t: '③ 外圓磨', s: ['306 → 300 mm，', '並刻 notch。'] },
    { id: 'sw_saw2', t: '④ 線鋸切片', s: ['多條鋼線同時切。'] },
    { id: 'sw_lap2', t: '⑤ 倒角研磨蝕刻', s: ['去鋸痕、損傷層。'] },
    { id: 'sw_polish2', t: '⑥ 拋光＋清洗', s: ['做到鏡面。'] },
    { id: 'sw_epi2', t: '⑦ 磊晶（選配）', s: ['長一層新的矽。', '不是每片都有。'] },
  ];
  const FB = { x: 16, y: 1128, w: 124, gap: 9, h: 70 };
  function pbar() {
    return FLOW.map((o, i) => {
      const x = FB.x + i * (FB.w + FB.gap);
      const box = part(o.id, R(x, FB.y, FB.w, FB.h, 'var(--dg-step-f)', 'part st', 7)
        + T(x + 10, FB.y + 22, o.t, 'lbl')
        + o.s.map((t, j) => T(x + 10, FB.y + 42 + j * 17, t, 'sub')).join(''));
      const arrow = i < FLOW.length - 1
        ? LN(`M${x + FB.w},${FB.y + FB.h / 2} L${x + FB.w + FB.gap},${FB.y + FB.h / 2}`, 'var(--dg-accent-2d)', 2)
        : '';
      return box + arrow;
    }).join('');
  }
  function areaF() {
    const back = FB.x + 63;          // 第 1 格的中線：返回箭頭指回來的地方
    return `<g>
      ${T(16, 1112, '六、製程流程（七格）—— 順序不准對調：磊晶一定在拋光之後', 'hd')}
      ${pbar()}
      ${part('sw_reclaim', R(660, 1208, 278, 64, 'var(--dg-frame-f)', 'part', 7)
      + T(672, 1230, '（灰）再生晶圓', 'lbl', null, 'fill:var(--dg-mute)')
      + T(672, 1250, '用過的測試片重新磨回可用。', 'sub', null, 'fill:var(--dg-mute)')
      + T(672, 1266, '不是主線的一段。', 'sub', null, 'fill:var(--dg-mute)'))}
      ${LN(`M660,1243 L${back},1243 L${back},${FB.y + FB.h + 6}`, 'var(--dg-mute)', 1.4, ' stroke-dasharray="5 4"')}
      ${PA(`M${back},${FB.y + FB.h} L${back - 5},${FB.y + FB.h + 10} L${back + 5},${FB.y + FB.h + 10}Z`, 'var(--dg-mute)')}
      ${T(back + 12, 1238, '← 另一條路：回收再利用', 'cap', null, 'fill:var(--dg-mute)')}</g>`;
  }

  /* ================================================================ 整張圖 */
  function siliconWafer() {
    /* 版面（Andy 2026-09-22：「圖片及文字縮小一半…希望能一次看到完整資訊」）
       ------------------------------------------------------------------
       主畫面留這張圖的命題：**CZ 提拉爐**（沒有它這張圖跟 SiC 的昇華爐分不出來）
       ＋ **粗糙度階梯**（「一級一級變細」是第三區唯一的命題）＋ 四句話 ＋ 誠實性標示。
       晶碇切片、8 吋 vs 12 吋、流程七格＋台股標示線三塊收進章節列，預設收合、按了打得開。
       收合後高度 ＝ 538 ＋ 三條列 × 46 ＋ 16 ＝ **692px**。

       ★ 為什麼流程七格與台股標示線合成同一段（規格書建議是分開的兩段）：
         台股標示線是**逐格對著流程列的七格**寫的（② CZ 長晶是誰、⑥ 拋光是誰…），
         拆成兩段的話展開其中一段會讀不懂 —— 它們是同一張表的上下兩半。*/
    const S1 = 538, S2 = 1030, S3 = 1402;
    return `<svg class="dg dgm dgsw" viewBox="0 0 ${W} 1896" width="100%" style="display:block">${D.STYLE}
      ${T(16, 24, '矽晶圓：從熔湯到一片鏡面', 'ttl')}
      ${T(16, 42, '一鍋熔湯 → 一根拉出來的單晶柱子 → 一片磨到鏡面的圓片。底下三段預設收起來，按標題列就打得開。', 'cap')}

      ${areaA()}${areaE()}
      ${areaC()}

      ${T(16, 458, '★ 誰做的：長晶到拋光是 6488 環球晶／3532 台勝科／6182 合晶，再生晶圓是 8028 昇陽半導體 —— 逐段名單見第 ④ 段。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 478, '示意圖，非實物比例｜爐體與各層厚度均為誇張放大', 'cap')}
      ${T(16, 494, '本圖講矽晶圓；碳化矽與氮化鎵用的是昇華法（PVT），爐子長得不一樣，見「第三代半導體」那張', 'cap')}
      ${T(16, 510, '本圖止於「一片可以進晶圓廠的晶圓」；之後的製程見「晶圓代工」那張', 'cap')}
      ${T(16, 526, '本圖只講半導體級矽晶圓，不含太陽能矽晶圓；不寫任何良率、市占率、產能、單價與漲價幅度', 'cap')}

      <!-- ================= ② 晶碇 → 切片（預設收合） ================= -->
      ${D.foldBar('sw2', S1, '② 晶碇 → 切片：外圓研磨、刻 notch、多線鋸',
      '由上到下就是先後順序：306→300 mm、一整條軸向溝、一組平行鋼線')}
      <g class="dgbody" data-fold="sw2" data-y0="${S1 + 46}" data-y1="${S1 + 46 + 434}">
        <g transform="translate(-232,${S1 + 46 - 68})">${areaB()}</g>
      </g>

      <!-- ================= ③ 8 吋 vs 12 吋（預設收合） ================= -->
      ${D.foldBar('sw3', S2, '③ 為什麼晶圓越大越划算：8 吋 vs 12 吋',
      '兩圓半徑比 2:3、方格一樣大、邊緣殘缺方格，以及 2.25 倍那條算式')}
      <g class="dgbody" data-fold="sw3" data-y0="${S2 + 46}" data-y1="${S2 + 46 + 314}">
        <g transform="translate(232,${S2 + 46 - 766})">${areaD()}</g>
      </g>

      <!-- ================= ④ 流程七格 ＋ 每一段台股是誰（預設收合） ================= -->
      ${D.foldBar('sw4', S3, '④ 製程流程七格 ＋ 這張圖上每一段台股是誰',
      '多晶矽→長晶→外圓磨→切片→研磨→拋光→磊晶、再生晶圓支線，以及逐段的台股名單')}
      <g class="dgbody" data-fold="sw4" data-y0="${S3 + 46}" data-y1="${S3 + 46 + 432}">
        <g transform="translate(0,${S3 + 46 - 1100})">
          ${areaF()}
          ${frame(16, 1296, 940, 150)}
          ${T(30, 1320, '這張圖上的段，台股是誰（信心：中，來源為媒體與公司網站整理）', 'hd')}
          ${T(30, 1342, '① 多晶矽原料：本圖查不到台股的具名對應 —— 查不到就寫查不到。', 'sub')}
          ${T(30, 1360, '② CZ 長晶／③ 外圓磨＋notch／④ 線鋸切片／⑤ 倒角研磨蝕刻／⑥ 拋光清洗：6488 環球晶、3532 台勝科、6182 合晶。', 'sub')}
          ${T(30, 1378, '　 ③～⑤ 是矽晶圓廠的內部工序，本圖查不到專做這幾道工序的台股獨立廠商。', 'sub')}
          ${T(30, 1396, '⑦ 磊晶（選配）：6488 環球晶（產品含磊晶片）、6182 合晶（產品含磊晶矽晶圓）。', 'sub')}
          ${T(30, 1414, '（灰）再生晶圓：8028 昇陽半導體（以再生晶圓起家）、1560 中砂（再生晶圓是其三大事業之一，掛在「前段製程材料」族群）。', 'sub')}
          ${T(30, 1432, '⑥ 拋光吃的耗材（研磨液、拋光墊、鑽石碟）不是這一格的公司做的 —— 鑽石碟見 1560 中砂。', 'sub')}
          ${T(16, 1466, '★ 5483 中美晶是 6488 環球晶的母公司（2011 年分割出去的子公司，來源：中美晶官網）——', 'sub', null, 'fill:var(--dg-warn)')}
          ${T(16, 1484, '　 兩者是母子不是競爭對手，所以上面刻意不把它跟環球晶並列在同一段；本圖也查不到中美晶目前自有矽晶圓產品線的具名資料。', 'sub', null, 'fill:var(--dg-warn)')}
          ${T(16, 1508, '★ 供應鏈資料的半導體鏈 14 個環節裡沒有一格是矽晶圓，這五檔也一檔都不在裡面 ——', 'sub', null, 'fill:var(--dg-warn)')}
          ${T(16, 1526, '　 所以這張圖一個 data-seg 都沒掛，點零件不會篩成分股。那不是壞掉，是誠實：掛 semi_material 等於宣稱光洋科做矽晶圓。', 'sub', null, 'fill:var(--dg-warn)')}
        </g>
      </g>
    </svg>`;
  }

  window.DG.register('silicon_wafer', {
    level: 'group', chain: 'semiconductor',
    name: '矽晶圓：從熔湯到一片鏡面',
    draw: siliconWafer, native: 980, scene: null,
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
