/* IC 封裝剖析 —— docs/diagram_plan.md 的第 4 張（族群 `ai_adv_packaging`、semiconductor 鏈）
   規格書（就是合約）：docs/diagram_specs/ic_package.md

   ---- 這張圖跟既有兩張的分工（規格書 §0，照它做）----
   既有其實是**兩張**，而且它們畫的是**鏈的縱向地圖**：
     · site/diagrams.js 的 semiconductor()  ＝「CoWoS 2.5D 封裝剖面」，畫的是 **CoWoS-S**（矽中介層＋TSV）
     · site/three3d.js 的 SCENES.semiconductor ＝「**CoWoS-L**」，有機 RDL ＋ LSI 矽橋
   一句話分工：
     **既有鏈圖＝「一顆晶片從哪裡來、走到哪裡去」；這張＝「封裝這一格內部，接點怎麼接、
       封裝體怎麼包、為什麼要換成方板」（一格的橫切面，從微米尺度出發）。**
   ⚠ 順便修掉一個既有的矛盾：同一條鏈上 2D 畫 S、3D 畫 L，兩張互相矛盾而沒有任何一張
     解釋它們是同一族的三個變體 —— 本圖第 ③ 區的 S／R／L 並排對照就是為了修這個（規格書 §0-B #3）。

   ---- 要不要 3D：不做（規格書 §1 已經寫死，`scene: null`）----
   六個資訊點有五個是「剖面上的層」，轉一圈不會多理解任何一件事；
   尺度尺（②）一旦進到透視投影，近大遠小就把比較毀掉。
   而且這條鏈**已經有一個 3D 場景**（SCENES.semiconductor），再開第二個只會讓讀者問
   「哪一個才是這顆封裝」。要加 3D＝改規格書、重新簽，不准實作時順手加。

   ---- 事實來源與信心度（全部在規格書 §7，這裡只記「畫面上寫了什麼、憑什麼」）----
   ★ 證據等級：這個容器**只有 WebSearch 能用，WebFetch 一律回 EGRESS_BLOCKED**，
     所以每一條都是「WebSearch 摘要」，沒有人讀過原文。摘要沒明講的數字，畫面上一律不寫。
     · C4 節距 150–200 µm、µbump 30–60 µm（semiengineering「Scaling Bump Pitches」摘要）→ 只寫量級區間
     · 混合鍵合＝**沒有焊料凸塊**、銅對銅，目標 10 µm 以下（semiengineering、tomshardware 摘要）
     · 凸塊內部：焊墊 → UBM（附著／阻障／濕潤）→ 銅柱 → Ni → 焊錫帽；
       銅柱 30–60 µm、Ni 1–5 µm（US20120091576A1、US8492891 摘要）→ 畫面只表達「銅柱最厚、Ni 最薄」
     · CoWoS-S/R/L 的定義（anysilicon、semiwiki、ecrionix 摘要）→ 畫面只寫「換掉了什麼」
     · 熱路徑 晶粒 → TIM1 → 上蓋 → TIM2 → 外部散熱器（indium、US9041192B2 摘要）
     · 面板級：矩形面板邊角浪費少；規格 310×310 起，另有更大規格（acmr、semiengineering 摘要）
   ★ **查不到的一律不畫**（規格書 §7-C）：良率、CoWoS 產能片數、各家營收占比、各層真實厚度比例、
     EMC／底填的台股具名供應商、族群五檔各自對應哪個零件 —— 畫面上一個數字都沒有。
   ★ 來源打架的一條（規格書 §7-B2）：CoPoS 時程有三個互相矛盾的說法（試產差一年、量產差半年到一年），
     所以**畫面只寫方向、不寫年份**。

   ---- 不要出現的東西（規格書 §0-C，畫了就是在重複既有的圖）----
   不畫 IP／EDA、IC 設計、晶圓廠、晶圓切割；不畫主機板、伺服器、機櫃、冷板；
   不重畫整條鏈的製程列；不畫 HBM 堆疊內部與層數；不畫任何廠商 logo／產品外觀。

   ---- 實作邊界 ----
   · `data-part` 一律 `icp_*`，**不准跟既有鏈圖的 `sc_*` 撞名**（撞名會讓高亮跨圖亂跳）。
   · `data-seg` 只掛 supply_chain.yaml 的 semiconductor 鏈上真的存在的環節；
     **模封 EMC 與 TIM2 兩個不掛**（前者沒有對應環節、後者跨到 ai_server 鏈，見規格書 §7-D2／D3）。
   · 色值一律走 `--dg-*`。這張圖需要七個既有 token 沒有的材質色，
     寫法是 `var(--dg-xxx, fallback)` —— 名字照既有命名，fallback 集中在下面那張表，
     art-director 之後把它們收進 index.html 的 :root 就會直接接手（:root 有定義時 fallback 不生效）。*/
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || !DG.register) { console.warn('[ai_adv_packaging] window.DG 還沒就緒，這張圖不註冊'); return; }
  const { STYLE, labelRow, processBar } = DG;

  /* 材質色。★ 一處定義，其餘地方只准引用 C.xxx（AGENTS §15：JS 不准散落 #xxxxxx）。
     七個新 token 都給了 fallback，所以在 index.html 補進 :root 之前畫面就是對的，
     補進去之後 :root 的值會接手 —— 兩種主題共用同一組（剖析圖的底 --illus 深淺主題都是深底）。*/
  const C = {
    si: 'var(--dg-si,#33488a)',            // 矽：晶粒、矽中介層、矽橋
    si2: 'var(--dg-si-2,#1d2b57)',         // 矽的暗階（剖面下緣、HBM 外形）
    org: 'var(--dg-organic,#8a6636)',      // 有機介電：RDL 中介層、ABF 增層膜（琥珀）
    org2: 'var(--dg-organic-2,#6a4c27)',
    emc: 'var(--dg-emc,#2f3039)',          // 模封 EMC（含填料的深色樹脂）
    uf: 'var(--dg-uf,#c08f4e)',            // 底部填充（半透明琥珀）
    met2: 'var(--dg-metal-2,#7d868f)',     // 補強環（比上蓋暗一階的金屬灰）
    sub2: 'var(--dg-sub-2,#10291d)',       // 載板的暗階（核心層）
    // 以下全部是 index.html 已經有的既有 token，直接用
    cu: 'var(--dg-cu)', sn: 'var(--dg-sn)', ni: 'var(--dg-ni)', pcb: 'var(--dg-pcb)',
    mute: 'var(--dg-mute)', warn: 'var(--dg-warn)', ink3: 'var(--dg-ink-3)',
  };

  /* ---------------- 主剖面的幾何（一處定義，右側說明欄的引線錨點也讀它）
     規格書 §4-A 的硬規則全部靠這幾個數字成立，改之前先回去讀：
       R2 大小 BGA > C4 > µbump ｜ R8 寬度 載板 > 中介層 > 晶粒 ｜ R1 C4 在中介層下、µbump 在上 */
  const M = {
    cx: 505,
    subL: 322, subR: 688, subT: 290, subB: 344,      // 載板：366 寬（全圖最寬、最厚）
    intL: 360, intR: 650, intT: 242, intB: 274,      // 中介層：290 寬
    dieL: 449, dieR: 561, dieT: 174, dieB: 232,      // 邏輯晶粒：112 寬
    soicL: 463, soicR: 547, soicT: 142, soicB: 170,  // SoIC 上層晶粒
    hbL1: 372, hbR1: 440, hbL2: 570, hbR2: 638,      // HBM：68 寬、90 高（比晶粒高、比晶粒窄）
    hbT: 142, hbB: 232,
    emcL: 364, emcR: 646, emcT: 142, emcB: 242,      // 模封：只包側面，頂面露出接 TIM1
    lidT: 112, lidB: 134, legT: 134, legB: 208,      // 上蓋與它的腳
    stiffT: 208,                                      // 補強環：從載板頂面長到上蓋的腳
    tim1T: 134, tim1B: 142, tim2T: 104, tim2B: 112,
    c4y: 282, c4r: 4, bgay: 354, bgar: 7, uby: 237, ubr: 2.2,
  };

  // 一排凸塊（BGA／C4）。r 與 step 差一個明顯的倍數，這兩個數字就是 R2 本身
  function balls(y, r, step, x0, x1, fill, part, seg, extra) {
    const a = [];
    for (let x = x0; x <= x1; x += step) a.push(`<ellipse class="part" cx="${x}" cy="${y}" rx="${(r * 1.35).toFixed(1)}" ry="${r}" fill="${fill}"/>`);
    return `<g data-seg="${seg}" data-part="${part}">${a.join('')}${extra || ''}</g>`;
  }
  /* 微凸塊：小一號的**銅柱＋錫帽**（不是一顆球）——「µbump 比 C4 小」是這張圖的核心視覺事實，
     所以這裡的 step 9 / 寬 3.2 跟 C4 的 step 20 / rx 5.4 一定要差一個看得出來的倍數。*/
  function ubumps(y, step, ranges) {
    const a = [];
    ranges.forEach(([x0, x1]) => {
      for (let x = x0; x <= x1; x += step) {
        a.push(`<rect x="${(x - 1.6).toFixed(1)}" y="${y - 2.6}" width="3.2" height="4.2" fill="${C.cu}"/>`
          + `<rect x="${(x - 1.6).toFixed(1)}" y="${y + 1.6}" width="3.2" height="1.8" fill="${C.sn}"/>`);
      }
    });
    return a.join('');
  }

  function icPackage() {
    // ---------------- 主剖面：載板內部（增層 ＋ 核心層 ＋ 雷射盲孔）
    const subCore = `<rect x="${M.subL}" y="310" width="${M.subR - M.subL}" height="16" fill="${C.sub2}"/>`;
    const pth = [];          // 核心層的貫穿孔（鍍通孔）：比盲孔粗、比盲孔長
    for (let x = M.subL + 26; x <= M.subR - 26; x += 52) pth.push(`<rect x="${x - 1.6}" y="310" width="3.2" height="16" fill="${C.cu}"/>`);
    const subTrace = [];     // 載板的銅線：線寬 1.6，**明顯粗於中介層的 RDL（0.7）**（V3）
    [298, 306, 332, 340].forEach((y, i) => {
      for (let x = M.subL + 12; x < M.subR - 40; x += 78) subTrace.push(`<path d="M${x},${y} h${52 - i * 4}" stroke="${C.cu}" stroke-width="1.6" fill="none" opacity=".85"/>`);
    });
    const blind = [];        // 雷射盲孔：上小下大的梯形，只穿一層
    for (let x = M.subL + 38; x <= M.subR - 38; x += 38) {
      blind.push(`<path d="M${x - 2.6},294 L${x + 2.6},294 L${x + 1.4},302 L${x - 1.4},302 Z" fill="${C.cu}" opacity=".9"/>`);
      blind.push(`<path d="M${x - 1.4},334 L${x + 1.4},334 L${x + 2.6},342 L${x - 2.6},342 Z" fill="${C.cu}" opacity=".9"/>`);
    }
    // ABF 增層膜：載板裡的**介電層**（半透明琥珀、沒有玻纖織紋）——它自己是一個零件（載板材料那一格）
    const abfFilm = [292, 300, 328, 336].map(y =>
      `<rect class="part" x="${M.subL + 4}" y="${y}" width="${M.subR - M.subL - 8}" height="6" fill="${C.org}" opacity=".5"/>`).join('');

    // ---------------- 中介層：RDL（細、多層、方向交錯）＋ TSV（細長）
    const rdl = [];
    [246, 250, 254].forEach((y, i) => {
      // 相鄰層的 dash 方向與長度交錯 —— V3 要的是「看得出是多層而且方向不一樣」
      rdl.push(`<path d="M${M.intL + 8},${y} H${M.intR - 8}" stroke="${C.cu}" stroke-width=".7" fill="none"
        stroke-dasharray="${i % 2 ? '16 6' : '5 4'}" opacity=".9"/>`);
    });
    const tsv = [];
    for (let x = M.intL + 14; x <= M.intR - 14; x += 26) tsv.push(`<rect class="part" x="${x - 1.3}" y="258" width="2.6" height="${M.intB - 258}" fill="${C.cu}"/>`);

    // ---------------- 模封裡的填料顆粒（EMC 的識別特徵：含填料的顆粒感）
    const filler = [];
    for (let i = 0; i < 90; i++) {
      const x = M.emcL + 6 + ((i * 97) % (M.emcR - M.emcL - 12));
      const y = M.emcT + 6 + ((i * 53) % (M.emcB - M.emcT - 12));
      filler.push(`<circle cx="${x}" cy="${y}" r="${1 + (i % 3) * 0.5}" fill="${C.mute}" opacity=".22"/>`);
    }

    // ---------------- 底部填充：圓角（fillet）爬上晶粒側壁 —— 少了它就跟「一層膠」沒兩樣（R4）
    const fil = (x, dir) => {
      const d = dir > 0 ? 1 : -1;
      return `<path d="M${x},${M.intT} L${x + d * 15},${M.intT} C${x + d * 7},${M.intT - 4} ${x + d * 2},${M.intT - 8} ${x},${M.dieB - 12} Z" fill="${C.uf}" opacity=".78"/>`;
    };
    const uf = [[M.dieL, M.dieR], [M.hbL1, M.hbR1], [M.hbL2, M.hbR2]].map(([a, b]) =>
      `<rect x="${a}" y="${M.dieB}" width="${b - a}" height="${M.intT - M.dieB}" fill="${C.uf}" opacity=".7"/>`
      + fil(a, -1) + fil(b, 1)).join('');

    // ---------------- HBM：只畫外形（層數與內部一律不畫，那是 hbm 族群自己的圖）
    const hbm = (x0, x1) => {
      const notch = [];
      for (let y = M.hbT + 12; y < M.hbB - 10; y += 14) notch.push(`<path d="M${x0},${y} h6 M${x1 - 6},${y} h6" stroke="${C.si2}" stroke-width="1.2" fill="none" opacity=".8"/>`);
      return `<rect class="part" x="${x0}" y="${M.hbT}" width="${x1 - x0}" height="${M.hbB - M.hbT}" rx="2" fill="url(#igSi)"/>${notch.join('')}`
        + `<text class="num" x="${(x0 + x1) / 2}" y="${M.hbT + 52}" text-anchor="middle" style="fill:${C.mute}">⋮</text>`;
    };

    // ---------------- 邏輯晶粒：接點全在**下表面**（覆晶朝下，S5）；沒有任何打線弧線（S4）
    const diePads = [];
    for (let x = M.dieL + 4; x <= M.dieR - 4; x += 9) diePads.push(`<rect x="${x - 1.8}" y="${M.dieB - 3}" width="3.6" height="3" fill="${C.cu}"/>`);
    const dieBeol = [227, 224, 221].map((y, i) => `<path d="M${M.dieL + 6},${y} H${M.dieR - 6}" stroke="${C.cu}" stroke-width=".6" opacity="${0.75 - i * 0.18}" fill="none"/>`).join('');

    /* ---------------- 混合鍵合界面：**一排銅墊對銅墊，沒有球、沒有柱**（R3、B5）
       規格書 §9 特別交代不要用 <circle> —— 用了就會被讀成凸塊。*/
    const hb = [];
    for (let x = M.soicL + 5; x <= M.soicR - 5; x += 7) hb.push(`<rect x="${x - 2.2}" y="170" width="4.4" height="4" fill="${C.cu}"/>`);
    const hbLine = `<path d="M${M.soicL},172 H${M.soicR}" stroke="${C.mute}" stroke-width=".8" stroke-dasharray="3 3" fill="none"/>`;

    // ---------------- 左欄 ①：凸塊內部特寫（由下到上 焊墊 → UBM 三層 → 銅柱 → Ni → 焊錫帽）
    const BX = 40, BW = 70;
    const ubm = [[283, C.ni, '附著層'], [278, C.met2, '阻障層'], [273, C.cu, '濕潤層']]
      .map(([y, c]) => `<rect x="${BX}" y="${y}" width="${BW}" height="5" fill="${c}"/>`).join('');
    const bumpZoom = `<g data-seg="adv_pkg" data-part="icp_bumpzoom">
      <rect class="part" x="${BX}" y="300" width="${BW}" height="18" fill="url(#igSi)"/>
      <rect x="${BX}" y="288" width="${BW}" height="12" fill="${C.cu}" opacity=".85"/>
      ${ubm}
      <rect class="part" x="${BX}" y="223" width="${BW}" height="50" fill="${C.cu}"/>
      <rect x="${BX}" y="215" width="${BW}" height="8" fill="${C.ni}"/>
      <path d="M${BX},215 h${BW} v-9 a${BW / 2},14 0 0 0 -${BW},0 z" fill="${C.sn}"/>
      <path class="leader" d="M${BX + BW},202 H122 M${BX + BW},219 H122 M${BX + BW},248 H122 M${BX + BW},278 H122 M${BX + BW},294 H122 M${BX + BW},309 H122"/>
      <text class="lbl" x="126" y="206">焊錫帽（最外）</text>
      <text class="lbl" x="126" y="223">Ni 阻障層</text>
      <text class="lbl" x="126" y="252">銅柱（最厚一段）</text>
      <text class="lbl" x="126" y="282">UBM 三層</text>
      <text class="lbl" x="126" y="298">晶粒焊墊</text>
      <text class="lbl" x="126" y="314">晶粒（矽）</text>
    </g>`;

    // ---------------- 左欄 ②：三種接法的尺度尺（同一個比例，由大到小）
    const sc1 = [];   // C4：節距 66px
    for (let x = 30; x <= 240; x += 66) sc1.push(`<ellipse class="part" cx="${x}" cy="410" rx="15" ry="12" fill="${C.sn}"/>`);
    const sc2 = [];   // µbump：節距 17px（同一比例下就是 C4 的約四分之一）
    for (let x = 30; x <= 296; x += 17) sc2.push(`<rect class="part" x="${x - 3}" y="474" width="6" height="8" fill="${C.cu}"/><rect x="${x - 3}" y="482" width="6" height="3" fill="${C.sn}"/>`);
    const sc3 = [];   // 混合鍵合：節距 3.2px，而且**畫的不是柱子**，是兩片平面中間一排銅墊
    for (let x = 30; x <= 296; x += 3.2) sc3.push(`<rect x="${(x - 0.8).toFixed(1)}" y="538" width="1.6" height="6" fill="${C.cu}"/>`);
    const scaleRuler = `<g data-seg="adv_pkg" data-part="icp_scale">
      <rect class="part" x="16" y="388" width="284" height="1.6" fill="${C.mute}" opacity=".5"/>
      ${sc1.join('')}
      <rect class="part" x="16" y="466" width="284" height="1.6" fill="${C.mute}" opacity=".5"/>
      ${sc2.join('')}
      <rect class="part" x="16" y="532" width="284" height="6" fill="url(#igSi)"/>
      ${sc3.join('')}
      <rect x="16" y="544" width="284" height="6" fill="url(#igSi)"/>
      <text class="lbl" x="16" y="440">C4 凸塊　節距 150–200 µm 級</text>
      <text class="sub" x="16" y="458">接「載板 ↔ 中介層」，塌成鼓形的焊錫</text>
      <text class="lbl" x="16" y="504">微凸塊 µbump　30–60 µm 級</text>
      <text class="sub" x="16" y="522">接「中介層 ↔ 晶粒」，銅柱＋錫帽</text>
      <text class="lbl" x="16" y="570">混合鍵合　目標 10 µm 以下</text>
      <text class="sub" x="16" y="588">銅墊直接對銅墊，**沒有**焊料凸塊</text>
    </g>`;

    // ---------------- ③ 三格中介層對照：同一個繪製函式，只換中介層那一層（V4／R16 自動成立）
    function interCell(x, kind) {
      const dieA = [x + 48, x + 138], dieB = [x + 162, x + 252];
      const iL = x + 28, iR = x + 272, mid = x + 150;
      const c4 = [];
      for (let t = iL + 12; t <= iR - 12; t += 22) c4.push(`<ellipse cx="${t}" cy="732" rx="4.6" ry="3.4" fill="${C.sn}"/>`);
      const ub = [];
      [dieA, dieB].forEach(([a, b]) => { for (let t = a + 4; t <= b - 4; t += 9) ub.push(`<rect x="${t - 1.4}" y="694" width="2.8" height="5" fill="${C.cu}"/>`); });
      let band = '', note = '';
      if (kind === 's') {                       // S：整片矽 ＋ TSV 貫穿
        const v = [];
        for (let t = iL + 12; t <= iR - 12; t += 20) v.push(`<rect x="${t - 1.2}" y="708" width="2.4" height="16" fill="${C.cu}"/>`);
        band = `<rect class="part" x="${iL}" y="700" width="${iR - iL}" height="24" fill="url(#igSi)"/>`
          + `<path d="M${iL + 6},704 H${iR - 6}" stroke="${C.cu}" stroke-width=".7" stroke-dasharray="4 3" fill="none"/>` + v.join('');
        note = 'TSV 貫穿整片矽';
      } else if (kind === 'r') {                // R：沒有矽、**沒有 TSV**（R9／R14）
        band = `<rect class="part" x="${iL}" y="700" width="${iR - iL}" height="24" fill="url(#igOrg)"/>`
          + `<path d="M${iL + 6},706 H${iR - 6} M${iL + 6},712 H${iR - 6} M${iL + 6},718 H${iR - 6}"
               stroke="${C.cu}" stroke-width=".8" stroke-dasharray="14 7" fill="none" opacity=".9"/>`;
        note = '整層沒有垂直的孔';
      } else {                                  // L：RDL 為底，**只在兩顆晶粒的交界**鑲一小塊矽橋（R15）
        band = `<rect class="part" x="${iL}" y="700" width="${iR - iL}" height="24" fill="url(#igOrg)"/>`
          + `<path d="M${iL + 6},706 H${iR - 6} M${iL + 6},718 H${iR - 6}" stroke="${C.cu}" stroke-width=".8" stroke-dasharray="14 7" fill="none" opacity=".9"/>`
          + `<rect x="${mid - 24}" y="702" width="48" height="14" rx="2" fill="url(#igSi)" stroke="${C.mute}" stroke-width=".8"/>`
          + `<path d="M${mid - 18},706 H${mid + 18} M${mid - 18},711 H${mid + 18}" stroke="${C.cu}" stroke-width=".6" fill="none"/>`;
        note = '矽橋只在交界正下方';
      }
      return `<g data-seg="adv_pkg" data-part="icp_cowos_${kind}">
        <rect class="part" x="${dieA[0]}" y="664" width="${dieA[1] - dieA[0]}" height="28" rx="2" fill="url(#igSi)"/>
        <rect class="part" x="${dieB[0]}" y="664" width="${dieB[1] - dieB[0]}" height="28" rx="2" fill="url(#igSi)"/>
        ${ub.join('')}${band}${c4.join('')}
        <rect class="part" x="${x + 8}" y="740" width="284" height="22" rx="2" fill="url(#igSub)"/>
        <text class="sub" x="${x + 14}" y="755" style="fill:${C.mute}">封裝載板</text>
        <text class="sub" x="${x}" y="782" style="fill:${C.warn}">${note}</text>
      </g>`;
    }

    // ---------------- ④ 圓晶圓 vs 方板：同一比例、同一種格子（M1／M2）
    function grid(cx, cy, R, sq) {
      const a = [], step = 16, cell = 14;
      for (let gx = -R; gx < R; gx += step) for (let gy = -R; gy < R; gy += step) {
        const x = cx + gx, y = cy + gy;
        if (sq) { a.push(`<rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="1" fill="${C.si}" opacity=".85"/>`); continue; }
        const corners = [[gx, gy], [gx + cell, gy], [gx, gy + cell], [gx + cell, gy + cell]];
        const inAll = corners.every(([a1, b1]) => Math.hypot(a1, b1) <= R);
        const inAny = corners.some(([a1, b1]) => Math.hypot(a1, b1) <= R);
        if (inAll) a.push(`<rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="1" fill="${C.si}" opacity=".85"/>`);
        else if (inAny) a.push(`<rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="1" fill="${C.mute}" opacity=".45" stroke="${C.mute}" stroke-width=".6" stroke-dasharray="2 2" clip-path="url(#igWafer)"/>`);
      }
      return a.join('');
    }
    const panelCmp = `<g data-seg="pkg_equipment" data-part="icp_panel">
      <circle class="part" cx="80" cy="960" r="56" fill="none" stroke="${C.mute}" stroke-width="1.4"/>
      ${grid(80, 960, 56, false)}
      <rect class="part" x="170" y="904" width="112" height="112" rx="3" fill="none" stroke="${C.mute}" stroke-width="1.4"/>
      ${grid(226, 960, 56, true)}
      <text class="sub" x="16" y="1038">圓晶圓：邊角是殘片</text>
      <text class="sub" x="170" y="1038">方板：邊角是滿的</text>
    </g>`;

    /* ---------------- 動畫：只做一件事（規格書 §9）——
       ① 一個訊號從一顆晶粒出發，走 µbump → 中介層的 RDL → 另一顆晶粒；
       ② 另一條走 µbump → TSV → C4 → 載板 → BGA 往下出封裝。
       兩條都用 CSS 的 .flow（`.dgwrap.noanim` 一關就真的停），**靜止時兩條路徑本身仍然看得見**。
       不要讓層跑來跑去 —— 這張圖的層是結構，不是動畫素材。*/
    const sig = `<g pointer-events="none">
      <path class="flow" d="M470,232 V248 H404 V232" stroke="var(--dg-accent)" stroke-width="2" fill="none"/>
      <path class="flow slow rev" d="M540,232 V252 H600 V274 L600,290 H612 V326 H620 V${M.bgay - M.bgar}"
            stroke="var(--dg-accent)" stroke-width="2" fill="none"/>
    </g>`;

    // 右側說明欄的「沒有對應環節」那兩列：不掛 data-seg（點不動、也不會篩出別人的成分股）
    const noteRow = (x, y, t, s) => `<g pointer-events="none">
      <rect x="${x - 8}" y="${y - 15}" width="264" height="40" rx="6" fill="none" stroke="${C.mute}" stroke-width=".8" stroke-dasharray="4 4"/>
      <circle cx="${x + 5}" cy="${y - 2}" r="4" fill="none" stroke="${C.mute}" stroke-width="1.2"/>
      <text class="lbl" x="${x + 16}" y="${y + 2}" style="fill:${C.mute}">${t}</text>
      <text class="sub" x="${x + 16}" y="${y + 18}">${s}</text></g>`;

    return `<svg class="dg dgm" viewBox="0 0 980 1300" width="100%" style="display:block">${STYLE}
      <defs>
        <linearGradient id="igSi" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.si}"/><stop offset="1" stop-color="${C.si2}"/></linearGradient>
        <linearGradient id="igOrg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.org}"/><stop offset="1" stop-color="${C.org2}"/></linearGradient>
        <linearGradient id="igSub" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.pcb}"/><stop offset="1" stop-color="${C.sub2}"/></linearGradient>
        <linearGradient id="igLid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.sn}"/><stop offset=".55" stop-color="${C.ni}"/><stop offset="1" stop-color="${C.met2}"/></linearGradient>
        <clipPath id="igWafer"><circle cx="80" cy="960" r="56"/></clipPath>
      </defs>
      <text class="ttl" x="16" y="26">IC 封裝剖析：晶粒 → 凸塊 → 中介層 → 封裝體</text>
      <text class="cap" x="16" y="46">中間是一顆 2.5D AI 加速器封裝的剖面（由下到上）。左邊把凸塊放大看內部、再用同一個比例比三種接法；右邊逐層說明。</text>
      <text class="cap" x="16" y="64">這張圖只看「封裝這一格的內部」。一顆晶片從哪裡來、走到哪裡去，看半導體鏈那張 CoWoS 剖面。</text>

      <!-- ================= 左欄 ① 凸塊內部 ================= -->
      <text class="hd" x="16" y="100">① 一顆凸塊裡疊了五層</text>
      ${bumpZoom}
      <text class="sub" x="16" y="342" style="fill:${C.warn}">★ Ni 一定夾在銅柱與焊錫之間 ——</text>
      <text class="sub" x="16" y="360" style="fill:${C.warn}">　 畫到焊錫外面是最常見的錯。</text>

      <!-- ================= 左欄 ② 三種接法的尺度尺（這張圖的靈魂） ================= -->
      <text class="hd" x="16" y="382">② 三種接法，同一個比例</text>
      ${scaleRuler}
      <text class="sub" x="16" y="610">三排畫在同一個比例上：接點越小，單位面積能接的線越多，</text>
      <text class="sub" x="16" y="628">但對平整度與潔淨度的要求也越兇。量級為示意，各世代不同。</text>

      <!-- ================= 中欄：主剖面（由下到上） ================= -->
      <text class="hd" x="322" y="88">主剖面：接點由下往上一路變小</text>

      <!-- 上蓋之上的 TIM2：不掛環節（它通往的散熱器屬 AI 伺服器鏈） -->
      <g pointer-events="none">
        <path d="M505,92 v-0 M505,100 l0,-12 m-4,4.5 l4,-4.5 l4,4.5" stroke="${C.mute}" stroke-width="1.4" fill="none"/>
        <rect data-part-note="icp_tim2" x="344" y="${M.tim2T}" width="322" height="8" fill="${C.mute}" opacity=".5"/>
      </g>

      <g data-seg="osat_test" data-part="icp_lid">
        <rect class="part" x="${M.subL}" y="${M.lidT}" width="${M.subR - M.subL}" height="${M.lidB - M.lidT}" rx="3" fill="url(#igLid)"/>
        <rect class="part" x="326" y="${M.legT}" width="28" height="${M.legB - M.legT}" fill="url(#igLid)"/>
        <rect class="part" x="656" y="${M.legT}" width="28" height="${M.legB - M.legT}" fill="url(#igLid)"/>
      </g>
      <g data-seg="osat_test" data-part="icp_tim1">
        ${[[M.hbL1, M.hbR1], [M.soicL, M.soicR], [M.hbL2, M.hbR2]].map(([a, b]) =>
      `<rect class="part" x="${a}" y="${M.tim1T}" width="${b - a}" height="8" fill="${C.mute}" opacity=".62"/>`).join('')}
      </g>
      <g data-seg="adv_pkg" data-part="icp_stiff">
        <rect class="part" x="${M.subL}" y="${M.stiffT}" width="36" height="${M.subT - M.stiffT}" fill="${C.met2}"/>
        <rect class="part" x="652" y="${M.stiffT}" width="36" height="${M.subT - M.stiffT}" fill="${C.met2}"/>
      </g>

      <!-- 模封：包住晶粒側面、頂面露出（本圖畫有上蓋的型式）。沒有對應環節，所以不掛 data-seg -->
      <g data-part-note="icp_emc">
        <rect x="${M.emcL}" y="${M.emcT}" width="${M.emcR - M.emcL}" height="${M.emcB - M.emcT}" fill="${C.emc}"/>
        ${filler.join('')}
      </g>

      <!-- 底填（圓角爬上晶粒側壁）→ 晶粒 → HBM → SoIC，順序就是畫面上的前後關係 -->
      <g data-seg="adv_pkg" data-part="icp_uf">${uf}</g>
      <g data-seg="hbm" data-part="icp_hbm">${hbm(M.hbL1, M.hbR1)}${hbm(M.hbL2, M.hbR2)}</g>
      <g data-seg="foundry" data-part="icp_die">
        <rect class="part" x="${M.dieL}" y="${M.dieT}" width="${M.dieR - M.dieL}" height="${M.dieB - M.dieT}" rx="2" fill="url(#igSi)"/>
        ${dieBeol}${diePads.join('')}
        <text class="num" x="${M.cx}" y="${M.dieT + 32}" text-anchor="middle" style="fill:${C.mute}">GPU / ASIC</text>
      </g>
      <g data-seg="adv_pkg" data-part="icp_soic">
        <rect class="part" x="${M.soicL}" y="${M.soicT}" width="${M.soicR - M.soicL}" height="${M.soicB - M.soicT}" rx="2" fill="url(#igSi)"/>
        ${hb.join('')}${hbLine}
      </g>

      <!-- 微凸塊 → 中介層（RDL ＋ TSV）→ C4 → 載板（ABF 增層膜）→ BGA -->
      <g data-seg="adv_pkg" data-part="icp_ubump">${ubumps(M.uby, 9, [[M.dieL + 4, M.dieR - 4], [M.hbL1 + 4, M.hbR1 - 4], [M.hbL2 + 4, M.hbR2 - 4]])}</g>
      <g data-seg="adv_pkg" data-part="icp_interposer">
        <rect class="part" x="${M.intL}" y="${M.intT}" width="${M.intR - M.intL}" height="${M.intB - M.intT}" rx="2" fill="url(#igSi)"/>
      </g>
      <g data-seg="adv_pkg" data-part="icp_rdl">${rdl.join('')}</g>
      <g data-seg="adv_pkg" data-part="icp_tsv">${tsv.join('')}</g>
      ${balls(M.c4y, M.c4r, 20, M.intL + 10, M.intR - 10, C.sn, 'icp_c4', 'adv_pkg')}
      <g data-seg="abf_pcb" data-part="icp_sub">
        <rect class="part" x="${M.subL}" y="${M.subT}" width="${M.subR - M.subL}" height="${M.subB - M.subT}" rx="3" fill="url(#igSub)"/>
        ${subCore}${pth.join('')}${subTrace.join('')}${blind.join('')}
      </g>
      <g data-seg="substrate_material" data-part="icp_abf">${abfFilm}</g>
      ${balls(M.bgay, M.bgar, 30, 337, 673, C.sn, 'icp_bga', 'abf_pcb')}
      <g pointer-events="none">
        <path d="M322,368 H688" stroke="${C.mute}" stroke-width="1" stroke-dasharray="6 5" fill="none" opacity=".7"/>
        <text class="sub" x="322" y="384" style="fill:${C.ink3}">↓ 往下接主機板（本圖不畫板子，那是 AI 伺服器鏈的事）</text>
      </g>
      ${sig}
      <text class="sub" x="322" y="404">動線：一條走 µbump → 中介層 RDL → 隔壁晶粒；另一條走 TSV → C4 → 載板 → 錫球往下。</text>

      <!-- ================= 右欄：說明（引線接回零件） ================= -->
      ${labelRow('osat_test', 704, 112, '散熱上蓋（lid／IHS）', '封測廠：上蓋、燒機、分選出貨', 688, 123, 264)}
      ${labelRow('osat_test', 704, 158, 'TIM1 導熱介面', '只壓在晶粒頂面，不蓋滿上表面', 638, 138, 264)}
      ${labelRow('adv_pkg', 704, 204, 'SoIC 混合鍵合界面', '銅墊對銅墊，中間沒有任何凸塊', 547, 172, 264)}
      ${labelRow('hbm', 704, 250, 'HBM 堆疊（只畫外形）', '內部與層數不畫；台股無直接對應', 638, 190, 264)}
      ${labelRow('foundry', 704, 296, '邏輯晶粒 GPU／ASIC', '覆晶朝下，接點全在下表面', 561, 206, 264)}
      ${labelRow('adv_pkg', 704, 342, '中介層：TSV ＋ RDL', '比晶粒寬，同時接住晶粒與 HBM', 650, 258, 264)}
      ${labelRow('adv_pkg', 704, 388, 'µbump／C4／底填／補強環', '接點逐級放大；底填有圓角、補強環防翹曲', 644, 282, 264)}
      ${labelRow('abf_pcb', 704, 434, 'ABF 載板 ＋ BGA 錫球', '最厚的一層；錫球是全圖最大的接點', 688, 317, 264)}
      ${labelRow('substrate_material', 704, 480, 'ABF 增層膜（介電層）', '琥珀色、沒有玻纖織紋；台股無對應', 686, 336, 264)}
      ${noteRow(704, 526, '模封 EMC（沒有對應環節）', '日系材料廠為主，查不到具名台股')}
      ${noteRow(704, 572, 'TIM2 → 外部散熱器', '跨到 AI 伺服器鏈，本圖不畫散熱器')}
      <text class="sub" x="696" y="612" style="fill:${C.warn}">★ 掛「先進封裝」那幾個零件點下去是 0 筆，</text>
      <text class="sub" x="696" y="630" style="fill:${C.warn}">　 不是壞掉 —— 原因寫在最下面那一行。</text>

      <!-- ================= ③ 三格中介層對照 ================= -->
      <text class="hd" x="16" y="656">③ CoWoS 有三種：換掉的是「中介層那一層用什麼做」</text>
      ${interCell(16, 's')}${interCell(340, 'r')}${interCell(664, 'l')}
      <text class="hd" x="16" y="810">CoWoS-S：整片矽中介層</text>
      <text class="sub" x="16" y="828">有 TSV 垂直貫穿，線最密。</text>
      <text class="sub" x="16" y="846">受光罩尺寸與成本限制。</text>
      <text class="hd" x="340" y="810">CoWoS-R：有機 RDL 中介層</text>
      <text class="sub" x="340" y="828">沒有矽、沒有 TSV。</text>
      <text class="sub" x="340" y="846">高分子介電當應力緩衝，可做大。</text>
      <text class="hd" x="664" y="810">CoWoS-L：RDL ＋ 局部矽橋</text>
      <text class="sub" x="664" y="828">只在兩顆晶粒交界鑲一小塊矽。</text>
      <text class="sub" x="664" y="846">要高密度的地方才用到矽。</text>
      <text class="sub" x="16" y="872" style="fill:${C.warn}">★ 半導體鏈那張 2D 剖面畫的是 S、3D 場景畫的是 L —— 它們是同一族的三個變體，不是互相矛盾。三格用同一個畫法，只有中介層不同。</text>

      <!-- ================= ④ 圓晶圓 vs 方板 ================= -->
      <text class="hd" x="16" y="896">④ 為什麼要從圓晶圓換成方板</text>
      ${panelCmp}
      <text class="sub" x="330" y="920">同一個比例、同一種格子：一格代表一顆封裝。</text>
      <text class="sub" x="330" y="938">圓的邊角切不出完整的一格（畫成虛線殘片），方的邊角是滿的。</text>
      <text class="sub" x="330" y="956">這就是面板級封裝（FOPLP）被提出來的理由：面積利用率較高、材料效率較好。</text>
      <text class="sub" x="330" y="974">業界在發展的面板規格從 310×310 mm 起，另有更大的規格。</text>
      <text class="sub" x="330" y="992">方向明確：載板越做越大、圓晶圓換成方板。</text>
      <text class="sub" x="330" y="1010" style="fill:${C.warn}">★ 時程不寫：台積電的面板級 CoPoS，三家報導的試產與量產年份互相矛盾，本圖只寫方向。</text>

      <!-- ================= ⑤ 封裝廠內部的五站 ================= -->
      <text class="cap" x="16" y="1054">⑤ 封裝廠內部這五站（★ 晶圓凸塊與 CP 測試都在「接合」之前 —— 反過來就沒有凸塊可以接、也挑不出好晶粒）</text>
      ${processBar(16, 1062, [{ seg: 'pkg_equipment', t: '晶圓凸塊', s: '鍍 UBM → 電鍍銅柱 → 錫帽' },
      { seg: 'test_interface', t: '晶圓測試 CP', s: '探針卡扎下去，先挑出好晶粒' },
      { seg: 'pkg_equipment', t: '接合', s: '熱壓／迴焊／混合鍵合' },
      { seg: 'pkg_equipment', t: '底填與模封', s: '點膠、填充、模封、補強環' },
      { seg: 'osat_test', t: '上蓋與成品測試', s: 'TIM1、上蓋、燒機、分選出貨' }], 178)}
      <path d="M390,1054 V1112" stroke="${C.warn}" stroke-width="1.6" stroke-dasharray="5 4" fill="none"/>
      <text class="sub" x="16" y="1128" style="fill:${C.ink3}">← 這兩站還在整片晶圓上（晶圓廠／凸塊廠）</text>
      <text class="sub" x="396" y="1128" style="fill:${C.ink3}">切開之後一顆一顆組起來（封裝廠／封測廠）→</text>

      <!-- ================= 註腳 ================= -->
      <text class="cap" x="16" y="1160">示意圖，非實物比例｜各層厚度與接點大小都是誇張過的，但「誰比誰大、誰在誰上面」不准倒過來。</text>
      <text class="cap" x="16" y="1178">畫面上沒有任何良率、產能、成本與市占數字 —— 那些查不到可引用的公開來源（見規格書 §7-C）。</text>
      <text class="cap" x="16" y="1196" style="fill:${C.warn}">★ 「先進封裝 CoWoS/SoIC」這一格由晶圓廠自己做，目前沒有台股成分股，所以點中介層、TSV、凸塊、底填這些零件，下面成分股會是 0 筆 —— 那不是壞掉。</text>
      <text class="cap" x="16" y="1214" style="fill:${C.warn}">　 台股在這張圖上的位置是另外三格：封測／測試 7 家、封裝設備／濕製程 4 家、測試介面探針卡 4 家；載板 3 家、晶圓代工 3 家。</text>
      <text class="cap" x="16" y="1232">點零件篩的是「環節」，不是整個族群。AI 先進封裝族群五檔（3711／3374／6271／6451／6789）裡，只有 3711 與 3374 在本圖用到的環節名單上。</text>
      <text class="cap" x="16" y="1250">模封 EMC 與 TIM2 兩個零件沒有掛環節：前者在本站沒有對應的一格、後者通往的散熱器屬 AI 伺服器鏈。</text>
      <text class="cap" x="16" y="1268">本圖畫「有上蓋」的型式，所以模封只包晶粒側面、頂面露出來接 TIM1；無上蓋的型式模封會蓋過晶粒頂面。</text>
      <text class="cap" x="16" y="1286">資料來源、信心度與「查不到的七件事」全部列在 docs/diagram_specs/ic_package.md。</text>
    </svg>`;
  }

  window.DG.register('ai_adv_packaging', {
    level: 'group', chain: 'semiconductor',
    name: '先進封裝：晶粒 → 凸塊 → 中介層 → 封裝體',
    draw: icPackage, native: 980, scene: null,
    q: '一顆 AI 晶片被「包」起來的時候，裡面到底多了哪幾層？為什麼接點越做越小、載板越做越大？',
  });
})();
