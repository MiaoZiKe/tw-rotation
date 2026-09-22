/* 伺服器電源 PSU ＋ BBU 電池備援 —— docs/diagram_plan.md 的第 9 張（族群 `server_psu`、ai_server 鏈）

   規格書＝合約：docs/diagram_specs/server_psu.md。下面只記「為什麼這樣畫」，
   事實與來源一律回去看規格書 §7（每一條都標了信心度與出處）。

   ---- 2026-09-22 v2（DECISIONS #238／#239，分支 claude/restyle-w1b）----
   · svg 根掛 `.rs`：閱讀模式字級升一階、說明卡片離開 SVG 變成 HTML（labelRow／extRow 多傳 side）。
   · 畫布從 980 收到 **640**（主角寬），`native: 640` 跟著改；欄數由 index.html 的 .dgv2 容器查詢決定。
   · 繪圖本體改成**垂直爆炸拆解**：電源架上第 4 顆 PSU 拉出來，往下拆成
       上蓋 → 主板（PFC → LLC 諧振 → 同步整流 → 輸出匯流，四級由上往下）→ 底殼（把手、風扇、後端金手指）。
     拓樸依機種而異，畫的是最常見的「PFC ＋ LLC ＋ 同步整流」組合（示意）：
       - TI 技術文章〈伺服器電源供應設計的五大趨勢〉（https://www.ti.com/lit/pdf/nest036）摘要：
         PFC 從被動式演進到無橋 PFC；隔離式 DC/DC 演進為 LLC 諧振與相移全橋；二次側用同步整流。
       - 專利／應用筆記摘要（NXP AN12617、USPTO 11616446）：伺服器電源含 EMI → PFC → LLC 諧振 → 變壓器 → 整流級；
         PFC 模組＝PFC 電感 ＋ 開關 ＋ 控制 IC；LLC 模組＝兩個電感 ＋ 諧振電容；同步整流＝MOSFET 全橋。
       兩個獨立來源一致 → 中高信心；但「哪一家用哪一種」查不到，所以畫面標「示意」、不寫任何一家的拓樸。
   · §1（永遠看得到的那一段）從 643 壓到約 424：右側說明欄整個變成 HTML 卡片、左邊設施欄縮成一條單線圖，
     機櫃框內只剩「電源架 ＋ 拆開的 PSU ｜ 匯流排 ｜ 托盤 ＋ BBU／超級電容」三欄。
     其餘收進三個章節（② BBU 與 UPS ＋ 四層防線、③ 兩種機櫃配電、④ CRPS ＋ 80 PLUS ＋ 五格流程 ＋ 結論），
     一個字都沒刪，只改斷行與位置。收合 ≈ 424 ＋ 8 ＋ 42×3 ＋ 10 ＝ 568。
   · 卡片與畫布上的區塊是**同一個零件身分**（同一個 data-part）：點卡片亮區塊、點區塊亮卡片。
     所以「主角」是一個 data-part，畫面上會是兩個節點（卡片 ＋ 區塊）同時 .sel-part —— 驗收比的是 data-part 的集合。
   · 卡片的元件色（data-dgcolor）：電力路徑上的零件 --dg-pwr、匯流排與 power whip --dg-cu（銅）、
     不在鏈上的設施側 --dg-mute。電流用箭頭 ＋ 虛線（交流 --dg-sig、直流 --dg-pwr），不加發光濾鏡。
   · 發光只給主角：同環節其餘 .sel 不發光（下面 VARS 那兩條，特異性壓過共用 STYLE）。

   ---- 型式：純 2D，不做真 3D（規格書 §0 已經寫死，scene: null）----
   這張圖本質上是一張**電力系統單線圖**，單線圖的價值就在於把空間拿掉、只留連接關係。
   要加 3D 就是改規格書重新簽，不准實作時順手加。

   ---- 這張圖的紅線（規格書 §6-N，違反任一條就退回）----
   N1 畫面上沒有任何市占率、良率、成本金額（台達電 PSU 市占：兩個來源兩個數字、都沒出處 → 一個都不寫）。
   N2 效率百分比**只出現在效率表裡**，而且附 80 PLUS 的條件（230 V／50% 負載／冗餘與否）。
   N3／N4 帶年份的量級寫成未來式並附來源年份；低信心的不寫成單一數值
      （BBU 撐多久：三個來源三個答案 → 時間軸一個秒數都不出現；800 V 省銅：兩組基準不同 → 只寫定性；
       匯流排電壓：54／50–54／48–54 → 寫「約 50–54 V」並註各家寫法不同；800 VDC 托盤端級數查不到 → 標「級數依設計而異」）。
   N5 畫面上講清楚「點零件篩到的是環節不是族群」而且 **BBU 尚未建檔**（右欄的警語卡，永遠看得到）。

   ---- ★ BBU 的落差（規格書 §7-D4）----
   `groups.yaml` 有獨立的 `bbu` 族群，但 `supply_chain.yaml` 的 ai_server 鏈**沒有任何 BBU 環節**。
   點 BBU 零件會篩到 `power` 那一格的台達電與光寶科 —— YAML 一行都不動，改成在畫面上明講（警語卡 ＋ 零件小卡的 none）。

   ---- data-seg 的掛法（規格書 §7-D，逐一在 YAML 查證過）----
     power      電源架、PSU（含拆開的三層）、板上 DC-DC／VRM、晶片、BBU、超級電容、位置對照、時間軸、效率表、兩欄架構、CRPS
     connector  **匯流排 busbar 與電源線組 power whip**（3665 貿聯-KY 的 tech 就是 Busbar／power whip，不是電源廠做的）
     assembly   機櫃虛線框
     不掛       設施側中壓交流、變壓器、機房 UPS（機房基礎設施，不在這條鏈上）—— 只掛 data-part 讓小卡開得起來 */
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || typeof DG.register !== 'function') return;
  if (!DG.fx) return;
  const { STYLE, extRow, note, processBar, fold, onXZ, onYZ, box, fx } = DG;
  const GL = { steel: 'var(--dg-steel)', alu: 'var(--dg-alu)', pcb: 'var(--dg-pcb)', cu: 'var(--dg-cu)', si: 'var(--dg-si)', off: 'var(--dg-mute)' };   // 玻璃方塊的底色（token）

  const P = 'power', C = 'connector', A = 'assembly';
  const CW = 640;                                           // 畫布寬＝主角寬（native 跟著改）
  const COL = { pwr: 'var(--dg-pwr)', cu: 'var(--dg-cu-lit)', off: 'var(--dg-mute)' };   // 卡片的元件色（token，不寫死；銅用亮面 --dg-cu-lit，選到時的卡片標題在深底上才有 ≥ 4.5）

  /* 這張圖自己的樣式。**全部吃 --dg-* token，一個 #xxxxxx 都沒有。**
     交流側＝--dg-sig（電訊號藍）、直流側＝--dg-pwr（電力橘）：兩種語意色、兩種模式都有對比表（_STYLE.md §1-B）。
     ⚠ 最後三條一定要排在 STYLE 之後、特異性也要比它高（多一個 svg 型別選擇器），不然蓋不掉。*/
  const VARS = `<style>
    .dg.psu .off{stroke:var(--dg-psu-off);fill:none;stroke-width:1.3}
    .dg.psu .offtx{fill:var(--dg-mute)}   /* 設施側的字：實色 mute（科技 5.0:1、閱讀 4.7:1）；52% 透明的 --dg-psu-off 只有 2.2:1，留給線 */
    .dg.psu .acw{stroke:var(--dg-sig);fill:none;stroke-width:2.4;stroke-linecap:round}
    .dg.psu .dcw{stroke:var(--dg-pwr);fill:none;stroke-width:2.4;stroke-linecap:round}
    .dg.psu .thin{stroke:var(--dg-psu-line);fill:none;stroke-width:1}
    .dg.psu .gold{fill:var(--dg-sw-gold)}
    .dg.psu .bd{fill:var(--dg-psu-box)}
    .dg.psu .bd2{fill:var(--dg-psu-box2)}
    .dg.psu .pcbf{fill:var(--dg-pcb)}
    .dg.psu .hair{stroke:var(--dg-psu-line);fill:none;stroke-width:var(--dg-hair-w,2);stroke-dasharray:5 5}
    .dg.psu .pull{stroke:var(--dg-ink-3);fill:none;stroke-width:1.2;stroke-dasharray:3 3}
    /* 發光只給主角（#238「暗色可發光但只給流動線與被選零件」）：同環節其餘 .sel 不發光、描邊細一階 */
    svg.dg.psu [data-seg].sel .part{filter:none;stroke-width:1.6}
    svg.dg.psu [data-seg].sel-part .part{stroke-width:2.6;filter:var(--dg-glow,drop-shadow(0 0 6px var(--cc)))}
    svg.dg.psu g[data-part="psu_ups"].sel-part .off{stroke:var(--dg-ink-2);stroke-width:2}
    svg.dg.psu g[data-part="psu_ups"].sel-part .fxb{fill-opacity:.9}
    /* 卡片的壓暗跟 SVG 同一階（.55）：進來的預設狀態是 power 被選、connector 兩張卡被壓暗，.3 連字都讀不到 */
    .dgwrap:has(svg.dg.psu) .dgc.dim{opacity:.55}
  </style>`;

  /* 兩欄架構對照的匯流排粗細：**兩欄共用這一個常數**（規格書 §6-C3）。
     同樣的功率下電流 ∝ 1 ÷ 電壓，導體截面就跟著走，所以粗細也用 1 ÷ 電壓。
     54 V → 15.0px、800 V → 1.01px。**不寫任何省銅數字**（§7-B4 兩組說法基準不同）。*/
  const BUSK = 810;
  const busH = (v) => +(BUSK / v).toFixed(2);

  /* ================================================================ §1 版面常數（全部是畫布座標，寬 640）
       設施欄（櫃外）x 6–104 ｜ 機櫃框 x 116–634 ｜ 左欄 x 130–312（電源架 ＋ 拆開的 PSU）
       匯流排 x 332–354 ｜ 右欄 x 380–620（托盤、BBU、超級電容）
     引線走法（externalize）：左欄卡片的引線從畫布左緣水平進來，所以左欄零件的錨點 y 要避開設施欄的文字帶
     （交流 24–48、變壓器 60–80、配電 90–136、UPS 288–370）；右欄卡片的引線從右緣進來，錨點 y 要避開托盤裡的字。*/
  const RX = 116, RY = 8, RW = 518, RH = 416;               // 機櫃虛線框 116..634 × 8..424
  const SHX = 130, SHY = 28, SHW = 182, SHH = 82;           // 電源架 130..312 × 28..110
  const BBX = 332, BBY = 26, BBW = 22, BBH = 374;           // 匯流排（厚銅排）332..354 × 26..400
  const TRX = 380, TRW = 240;                               // 托盤 380..620
  const EX0 = 138, EX1 = 304;                               // 拆開的 PSU 三層的左右緣
  const LAY = { cover: [156, 176], board: [190, 332], base: [340, 398] };   // 三層的 y（層與層之間留 14 的呼吸空間）

  function serverPsu() {
    /* PSU 正面（裝在架上的那 4 顆）：把手、風扇、指示燈、底部金手指 —— CRPS 的識別特徵。
       ⚠ `.spin` 的 keyframes 會設 transform，會蓋掉同一個元素上的 translate，
          所以外面一定要再包一層負責定位的 <g>。*/
    const psuUnit = (x, y, i, out) => {
      const w = 34, h = 64;
      const fingers = [0, 1, 2, 3, 4].map(j =>
        `<rect class="gold" x="${x + 6 + j * 4.8}" y="${y + h - 9}" width="2.6" height="7" rx="1"/>`).join('');
      const blades = [0, 1, 2, 3, 4].map(j =>
        `<path class="thin" d="M0,0 L${(8 * Math.cos(j * 1.2566)).toFixed(1)},${(8 * Math.sin(j * 1.2566)).toFixed(1)}"/>`).join('');
      return `<g${out ? ' transform="translate(8,4)"' : ''}>
        ${fx.glass(x, y, w, h, { fill: GL.alu, cls: 'part', rx: 3 })}
        <rect x="${x + 8}" y="${y + 5}" width="18" height="4" rx="2" fill="var(--dg-ink-3)"/>
        <circle class="thin" cx="${x + 17}" cy="${y + 30}" r="10"/>
        <g transform="translate(${x + 17},${y + 30})"><g class="spin" style="animation-delay:${(i * 0.4).toFixed(1)}s">${blades}</g></g>
        <circle class="blink b${(i % 3) + 1}" cx="${x + 28}" cy="${y + 11}" r="2.2" fill="var(--dg-pwr)"/>
        ${fingers}</g>`;
    };

    /* 主板四級（由上往下）：功因校正 → LLC 諧振 → 同步整流 → 輸出匯流。
       每一級一個 34×22 的小圖示 ＋ 中文名 ＋ 代號；級與級之間一個往下的箭頭（電由上往下流）。*/
    const icon = (kind, x, y) => {
      if (kind === 'pfc') return `<path class="thin" d="M${x + 2},${y + 11} q4,-6 8,0 t8,0 t8,0"/><rect class="thin" x="${x + 24}" y="${y + 13}" width="8" height="7"/>`;
      if (kind === 'llc') return `<path class="thin" d="M${x + 3},${y + 8} V${y + 14} M${x + 6},${y + 8} V${y + 14} M${x + 13},${y + 3} q-5,3 0,6 q-5,3 0,6 q-5,3 0,6 M${x + 23},${y + 3} q5,3 0,6 q5,3 0,6 q5,3 0,6 M${x + 17},${y + 3} V${y + 21} M${x + 19},${y + 3} V${y + 21}"/>`;
      if (kind === 'sr') return `<rect class="thin" x="${x + 9}" y="${y + 2}" width="14" height="8"/><rect class="thin" x="${x + 9}" y="${y + 12}" width="14" height="8"/><path class="thin" d="M${x + 3},${y + 11} H${x + 9} M${x + 23},${y + 6} H${x + 30} M${x + 23},${y + 16} H${x + 30}"/>`;
      return `<rect x="${x + 2}" y="${y + 13}" width="28" height="5" fill="var(--dg-psu-cu)"/><rect class="thin" x="${x + 7}" y="${y + 3}" width="6" height="8"/><rect class="thin" x="${x + 18}" y="${y + 3}" width="6" height="8"/>`;
    };
    const STAGES = [['pfc', '功因校正 PFC'], ['llc', '諧振轉換 LLC'], ['sr', '同步整流 SR'], ['out', '輸出匯流排']];
    const boardRows = STAGES.map(([k, t], i) => {
      const y = LAY.board[0] + 8 + i * 34;
      return `${fx.glass(156, y, 34, 22, { fill: GL.alu, rx: 3 })}${icon(k, 156, y)}`
        + `<text class="sub" x="198" y="${y + 15}" style="fill:var(--dg-ink)">${t}</text>`
        + (i < 3 ? `<path class="dcw" d="M173,${y + 23} V${y + 30}" marker-end="url(#psuAr)" stroke-width="1.6"/>` : '');
    }).join('');

    // 板上 DC-DC：一個 for 迴圈畫 6 個等距電感（§6-V4：多相＝一排並聯，不是一顆）
    const phases = [];
    for (let i = 0; i < 6; i++) {
      const x = 399 + i * 20;
      phases.push(fx.glass(x, 136, 14, 22, { fill: GL.alu, cls: 'part', rx: 3 })
        + `<path class="thin" d="M${x + 2},142 H${x + 12} M${x + 2},147 H${x + 12} M${x + 2},152 H${x + 12}"/>`
        + `<rect x="${x + 2}" y="162" width="10" height="8" rx="1.5" fill="var(--dg-el)"/>`);
    }
    // 受電端晶片：die 上的運算格子（會呼吸；動畫關掉就停）
    const dieCells = [];
    for (let r = 0; r < 3; r++) for (let c = 0; c < 4; c++)
      dieCells.push(`<rect class="pulse" x="${556 + c * 13}" y="${136 + r * 13}" width="10" height="10" rx="1.5"
        fill="color-mix(in srgb,var(--dg-pwr) 34%,transparent)" style="animation-delay:${(((r * 4 + c) % 6) * 0.32).toFixed(2)}s"/>`);
    /* BBU：電池芯（帶正負極柱）＋ 管理電路 ＋ 連接器金手指。
       ★ 這個符號跟機房 UPS 那個「交流→直流→交流 ＋ 旁路」的符號完全不同（§6-P4）。*/
    const cells = [];
    for (let r = 0; r < 2; r++) for (let c = 0; c < 3; c++) {
      const x = 522 + c * 32, y = 310 + r * 26;
      cells.push(fx.glass(x, y, 28, 20, { fill: GL.alu, cls: 'part', rx: 2.5 })
        + `<rect x="${x + 4}" y="${y - 3}" width="6" height="4" rx="1" fill="var(--dg-sw-gold)"/>`
        + `<rect x="${x + 18}" y="${y - 3}" width="6" height="4" rx="1" fill="var(--dg-ink-3)"/>`
        + `<path class="thin" d="M${x + 4},${y + 11} h6 M${x + 7},${y + 8} v6 M${x + 18},${y + 11} h6"/>`);
    }
    // 超級電容／LIC：圓柱陣列（側視：柱身 ＋ 頂面橢圓 ＋ 防爆槽），比 BBU 小一號
    const scaps = [];
    for (let i = 0; i < 4; i++) {
      const x = 388 + i * 20;
      scaps.push(fx.glass(x, 316, 16, 34, { fill: GL.alu, cls: 'part', rx: 5 })
        + `<ellipse class="thin" cx="${x + 8}" cy="316" rx="8" ry="3.4" fill="var(--dg-psu-box2)"/>`
        + `<path class="thin" d="M${x + 4},314 H${x + 12} M${x + 8},311 V319"/>`);
    }
    // 其餘運算托盤（同一條路徑，簡化畫）
    const miniTray = (y) => `<g>${fx.glass(TRX, y, TRW, 24, { fill: GL.steel, rx: 4 })}
      ${[0, 1, 2, 3, 4, 5].map(j => `<rect x="${TRX + 8 + j * 9}" y="${y + 7}" width="6" height="10" rx="1.5" fill="var(--dg-psu-off)"/>`).join('')}
      <rect x="${TRX + 70}" y="${y + 6}" width="22" height="12" rx="2" fill="var(--dg-psu-die)"/>
      <text class="sub" x="${TRX + 102}" y="${y + 16}">其餘托盤（同一條路徑）</text></g>`;

    // ---------------------------------------------------------------- ③ 兩欄架構對照（章節裡）
    const AC1 = 16, AC2 = 330, ACW = 294;                    // 左欄（現行）／右欄（800 VDC）
    const slot = (n) => 940 + n * 50;                        // 五個插槽的 y（兩欄對齊，才看得出右欄少一格）
    const archBox = (x, n, t, s, extra) => `<g>${fx.glass(x, slot(n), ACW, 42, { fill: GL.steel, cls: 'part', rx: 6 })}
      <text class="lbl" x="${x + 10}" y="${slot(n) + 17}">${t}</text>
      <text class="sub" x="${x + 10}" y="${slot(n) + 33}">${s}</text>${extra || ''}</g>`;
    const busBar = (x, n, v) => `<rect x="${x + ACW - 92}" y="${(slot(n) + 21 - busH(v) / 2).toFixed(2)}" width="82"
      height="${busH(v)}" rx="${Math.min(2, busH(v) / 2)}" fill="var(--dg-psu-cu)"/>`;

    // ---------------------------------------------------------------- ② 位置對照表 ＋ 四層防線（章節裡）
    const place = [['超級電容／LIC', '直流側', '櫃內', '毫秒等級'],
      ['BBU', '直流側', '櫃內', '比毫秒長，但仍然很短'],
      ['UPS', '交流側', '櫃外（機房）', '撐到發電機起來'],
      ['發電機', '交流側', '廠區', '最長']]
      .map(([a, b, c, d], i) => {
        const y = 554 + i * 26;
        return `<g><rect class="bd" x="22" y="${y - 15}" width="596" height="24" rx="4" opacity="${i % 2 ? '.55' : '0'}"/>
          <text class="lbl" x="30" y="${y}">${a}</text><text class="sub" x="200" y="${y}">${b}</text>
          <text class="sub" x="320" y="${y}">${c}</text><text class="sub" x="450" y="${y}">${d}</text></g>`;
      }).join('');
    /* 四層防線時間軸：**一個秒數都不標、也不按比例**（§6-T2、§7-B3）。
       四條棒子由短到長只表達**排序**，長度不代表任何可引用的數字。*/
    const timeline = [['超級電容／LIC', 60, '毫秒等級：吸收瞬間電流尖峰'],
      ['BBU', 110, '比毫秒長，但仍然很短'],
      ['UPS', 200, '撐到發電機起來'],
      ['發電機', 300, '最長']]
      .map(([n, w, s], i) => {
        const y = 746 + i * 22;
        return `<g><text class="sub" x="28" y="${y + 10}">${n}</text>
          <rect x="150" y="${y}" width="${w}" height="12" rx="6" fill="color-mix(in srgb,var(--dg-pwr) ${34 + i * 14}%,transparent)"/>
          <text class="sub" x="${150 + w + 10}" y="${y + 10}">${s}</text></g>`;
      }).join('');

    // ---------------------------------------------------------------- ④ 效率表（章節裡）
    const effRows = [['Gold', '92%', '92%'], ['Platinum', '94%', '94%'], ['Titanium', '95%', '96%']]
      .map(([a, b, c], i) => {
        const y = 1672 + i * 30;
        return `<g><rect class="bd" x="22" y="${y - 16}" width="596" height="26" rx="4" opacity="${i === 2 ? '1' : (i % 2 ? '.55' : '0')}"/>
          <text class="lbl" x="34" y="${y}">${a}</text><text class="num" x="306" y="${y}">${b}</text>
          <text class="num" x="466" y="${y}">${c}</text></g>`;
      }).join('');

    /* ④ CRPS 型 PSU 的 2.5D 小圖。x=W 面是**前面板**（把手＋風扇孔），y=D 面是**後端卡緣金手指**（§6-S2）。*/
    const IW = 110, ID = 44, IH = 28;
    const isoFront = onYZ(IW, 0)
      + `<rect x="6" y="6" width="32" height="5" rx="2.5" fill="var(--dg-ink-3)"/>`
      + `<circle class="etch" cx="22" cy="18" r="7.5"/><circle class="lit" cx="22" cy="18" r="2.4"/>`
      + `</g>`;
    const isoEdge = onXZ(0, ID)
      + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(j =>
        `<rect class="gold" x="${14 + j * 8.6}" y="7" width="4.8" height="14" rx="1"/>`).join('')
      + `</g>`;

    // ---------------------------------------------------------------- 組起來
    return `<svg class="dg dgm rs psu" viewBox="0 0 ${CW} 2300" width="100%" style="display:block">${STYLE}${VARS}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}
        <linearGradient id="psuCu" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="var(--dg-psu-cu2)"/><stop offset=".45" stop-color="var(--dg-psu-cu)"/><stop offset="1" stop-color="var(--dg-psu-cu2)"/></linearGradient>
        <marker id="psuAr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--dg-pwr)"/></marker>
        <marker id="psuArG" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="var(--dg-ink-3)"/></marker>
      </defs>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">伺服器電源：從牆上的電到晶片核心，中間降壓幾次</text>
      <text class="cap ext" x="0" y="0">這是一張電力單線圖 —— 空間拿掉、只留「誰接在誰後面」。左邊是機房設施（不在這條鏈上）；虛線框內是機櫃：電源架把交流整成直流、厚銅排送到每一片托盤、板上再降到晶片核心電壓，BBU 與超級電容掛在直流側。第 4 顆 PSU 拉出來、由上往下拆成三層。那顆光點每經過一級就小一圈＝電壓一級一級降下來（示意，不是比例）；每一級都有損耗，而且是連乘的。BBU 與 UPS 的分工、兩種機櫃配電、CRPS 與 80 PLUS 收在下面三段。</text>

      <!-- ================= §1 主供電路徑（§3-A：不准跳級、電壓沿路徑單調遞減）================= -->
      <!-- 設施側：只畫單線圖符號、不畫實物，不掛 data-seg（§7-D1、§6-M1）；掛 data-part 讓小卡能講「不在這條鏈上」 -->
      <g data-part="psu_ups" style="cursor:pointer">
        <circle class="off" cx="26" cy="32" r="11"/>
        <path class="off" d="M20,32 q3,-5 6,0 t6,0"/>
        <text class="lbl offtx" x="44" y="30">中壓交流</text>
        <text class="sub offtx" x="44" y="47">例 13.8 kV</text>
        <path class="off" d="M26,43 V60"/>
        <circle class="off" cx="20" cy="70" r="9"/><circle class="off" cx="32" cy="70" r="9"/>
        <text class="sub offtx" x="46" y="74">變壓器</text>
        <path class="off" d="M26,79 V92"/>
        <rect class="off" x="8" y="92" width="96" height="7" rx="2"/>
        <text class="sub offtx" x="8" y="118">機房配電盤</text>
        <text class="sub offtx" x="8" y="134">數百伏特交流</text>
        <!-- 機房 UPS：接在**交流側**、畫在機櫃虛線框**外面**（§6-P2）；符號是雙轉換加旁路（§6-P4） -->
        <path class="off" d="M96,99 V300"/>
        <text class="lbl offtx" x="8" y="292">機房 UPS</text>
        ${fx.glass(8, 300, 96, 46, { fill: GL.off, rx: 5 })}
        <rect class="off" x="14" y="316" width="20" height="16" rx="3"/>
        <path class="off" d="M18,325 q3,-6 6,0 t6,0"/>
        <rect class="off" x="46" y="316" width="20" height="16" rx="3"/>
        <path class="off" d="M50,321 H62 M50,327 H62"/>
        <rect class="off" x="78" y="316" width="20" height="16" rx="3"/>
        <path class="off" d="M82,325 q3,-6 6,0 t6,0"/>
        <path class="off" d="M20,312 q36,-10 72,0"/>
        <text class="sub offtx" x="8" y="364">交流側・櫃外</text>
      </g>
      <!-- 交流進機櫃（跨過那條虛線框）：訊號藍的光束，不發光（發光預算留給直流主路徑） -->
      ${fx.beam(`M104,96 H112 V60 H${SHX}`, { color: 'var(--dg-sig)', w: 2, glow: false, flow: true, dots: [[SHX, 60]], dotR: 2.6 })}

      <!-- 機櫃虛線框（assembly）：沒有這個框，「櫃內／櫃外」就沒有畫面上的依據（§6-P3） -->
      <g data-seg="${A}" data-part="psu_rack">
        <rect class="part" x="${RX}" y="${RY}" width="${RW}" height="${RH}" rx="10" fill="none" stroke-dasharray="9 7"/>
        <text class="sub" x="128" y="414">機櫃（虛線框內＝櫃內；UPS 與設施電都在框外）</text>
      </g>
      <!-- 柔陰影：主要方塊各一個影子，全部包成一個群組（一次 feGaussianBlur；亮色版靠它有「浮起來」的感覺） -->
      ${fx.shadows([[SHX, SHY, SHW, SHH], [EX0, LAY.cover[0], EX1 - EX0, LAY.cover[1] - LAY.cover[0]], [EX0, LAY.board[0], EX1 - EX0, LAY.board[1] - LAY.board[0]],
      [EX0, LAY.base[0], EX1 - EX0, LAY.base[1] - LAY.base[0]], [TRX, 104, TRW, 104], [TRX, 300, 92, 64], [492, 300, 128, 72], [8, 300, 96, 46]]
      .map(([x, y, w, h]) => `<rect x="${x + 3}" y="${y + 7}" width="${w}" height="${h}" rx="6"/>`).join(''))}

      <!-- 電源架 ＋ 4 顆 PSU（power）：3 顆在架上、第 4 顆抽出來一點（熱插拔、N＋1，§6-S1／S3） -->
      <g data-seg="${P}" data-part="psu_shelf">
        ${fx.glass(SHX, SHY, SHW, SHH, { fill: GL.steel, cls: 'part', rx: 6, t: 3 })}
        ${psuUnit(142, 36, 0, false)}${psuUnit(182, 36, 1, false)}${psuUnit(222, 36, 2, false)}
        <rect class="pull" x="262" y="36" width="34" height="64" rx="3"/>
        ${psuUnit(262, 36, 3, true)}
      </g>
      <text class="sub" x="${SHX}" y="124">N＋1：壞一顆不用關機</text>
      <text class="sub" x="${SHX}" y="142">拉出一顆拆開看（示意）</text>
      <path class="pull" d="M287,106 V150" marker-end="url(#psuArG)"/>

      <!-- 拉出來的那一顆：由上往下拆成 上蓋 → 主板 → 底殼（垂直爆炸拆解，層與層之間留呼吸空間） -->
      <g data-seg="${P}" data-part="psu_unit">
        ${fx.glass(EX0, LAY.cover[0], EX1 - EX0, LAY.cover[1] - LAY.cover[0], { fill: GL.steel, cls: 'part', rx: 3, t: 2 })}
        ${[0, 1, 2, 3, 4, 5, 6, 7].map(j => `<path class="thin" d="M${160 + j * 16},${LAY.cover[0] + 5} V${LAY.cover[1] - 5}"/>`).join('')}
        ${fx.glass(EX0, LAY.base[0], EX1 - EX0, LAY.base[1] - LAY.base[0], { fill: GL.steel, cls: 'part', rx: 4, t: 3 })}
        <rect x="146" y="${LAY.base[0] + 10}" width="5" height="38" rx="2" fill="var(--dg-ink-3)"/>
        <circle class="thin" cx="178" cy="${LAY.base[0] + 29}" r="19"/>
        <g transform="translate(178,${LAY.base[0] + 29})"><g class="spin">${[0, 1, 2, 3, 4, 5, 6].map(j =>
          `<path class="thin" d="M0,0 L${(16 * Math.cos(j * 0.8976)).toFixed(1)},${(16 * Math.sin(j * 0.8976)).toFixed(1)}"/>`).join('')}</g></g>
        <circle cx="178" cy="${LAY.base[0] + 29}" r="4" fill="var(--dg-ink-3)"/>
        <circle class="blink b2" cx="206" cy="${LAY.base[0] + 10}" r="2.2" fill="var(--dg-pwr)"/>
        ${[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(j => `<rect class="gold" x="${236 + j * 6.2}" y="${LAY.base[0] + 22}" width="2.8" height="14" rx="1"/>`).join('')}
        <path class="thin" d="M234,${LAY.base[0] + 39} H298"/>
      </g>
      <g data-seg="${P}" data-part="psu_board">
        ${fx.glass(EX0, LAY.board[0], EX1 - EX0, LAY.board[1] - LAY.board[0], { fill: GL.pcb, cls: 'part', rx: 3, t: 2 })}
        <path class="acw" d="M173,${LAY.board[0] - 8} V${LAY.board[0] + 6}" marker-end="url(#psuAr)" stroke-width="1.6"/>
        ${boardRows}
        <path class="dcw" d="M173,${LAY.board[1] - 10} V${LAY.board[1] + 6}" marker-end="url(#psuAr)" stroke-width="1.6"/>
      </g>

      <text class="tag" x="${BBX + BBW + 10}" y="20">約 50–54 V 直流</text>

      <!-- 直流匯流排：厚銅排、實心，不是圓電線（§6-V3）—— 銅色玻璃板，頂面與右側面帶厚度。掛 connector 不是 power（§7-D2） -->
      <g data-seg="${C}" data-part="psu_busbar">
        ${fx.glass(BBX, BBY, BBW, BBH, { fill: GL.cu, cls: 'part', rx: 2, iso: { dx: 8, dy: -8 } })}
      </g>

      <!-- 電源線組 power whip：從匯流排接到托盤（§6-V5），一樣掛 connector -->
      <g data-seg="${C}" data-part="psu_whip">
        ${[42, 78, 128].map(y => `<path class="part" d="M${BBX + BBW},${y} H${TRX}" stroke-width="7" stroke-linecap="round" fill="none"/>`).join('')}
        ${[42, 78].map(y => `<path d="M${BBX + BBW},${y} H${TRX}" stroke="var(--dg-pwr)" stroke-width="1.6" fill="none" opacity=".7"/>`).join('')}
      </g>

      <!-- 其餘托盤（簡化）＋ 主托盤（展開） -->
      ${miniTray(30)}${miniTray(66)}
      ${fx.glass(TRX, 104, TRW, 104, { fill: GL.steel, rx: 6 })}
      <text class="sub" x="${TRX + 8}" y="120">運算托盤（展開）</text>

      <!-- 板上 DC-DC／VRM：一排 6 個等距電感（多相）＋ 開關元件（§6-V4） -->
      <g data-seg="${P}" data-part="psu_vrm">
        ${fx.glass(384, 128, 134, 50, { fill: GL.pcb, cls: 'part', rx: 5 })}
        ${phases.join('')}
      </g>

      <!-- 受電端晶片：矽色玻璃方塊 ＋ 一顆靜態的光暈（第三個、也是最後一個 feGaussianBlur）＝ 供電路徑的終點 -->
      <circle cx="580" cy="153" r="26" fill="var(--dg-pwr)" style="opacity:calc(var(--fx-glow-a) * .35)" filter="url(#fxGlow)" pointer-events="none"/>
      <g data-seg="${P}" data-part="psu_die">
        ${fx.glass(548, 128, 64, 50, { fill: GL.si, cls: 'part', rx: 4, t: 2 })}
        ${dieCells.join('')}
      </g>
      <text class="sub" x="388" y="200">多相：一排電感輪流工作</text>
      <text class="tag" x="548" y="200">約 1 V 以下</text>

      <!-- 直流主路徑（電力橘的發光光束，整張圖唯一發光的線）：電源架 → 匯流排 → 第三條 power whip → VRM → 晶片；
           另一段從匯流排上的直流節點分到超級電容與 BBU（§6-P5：兩者接在同一個節點）。端點光點＝電流到達的地方。-->
      ${fx.beam(`M${SHX + SHW},60 H${BBX + BBW / 2} V128 H384 M518,153 H548 M${BBX + BBW / 2},336 H${TRX} M${BBX + BBW + 8},336 V386 H586 V372`,
      { color: 'var(--dg-pwr)', w: 2.2, flow: true, dots: [[BBX + BBW / 2, 60], [548, 153], [BBX + BBW + 8, 336], [TRX, 336], [586, 372]] })}

      <!-- 超級電容／鋰離子電容（power）：比 BBU 小一號，管最短的那一段 -->
      <g data-seg="${P}" data-part="psu_scap">
        ${fx.glass(TRX, 300, 92, 64, { fill: GL.steel, cls: 'part', rx: 6, t: 2 })}
        ${scaps.join('')}
      </g>
      <!-- BBU（power）：電池芯 ＋ 正負極柱 ＋ 管理電路 ＋ 連接器金手指 -->
      <g data-seg="${P}" data-part="psu_bbu">
        ${fx.glass(492, 300, 128, 72, { fill: GL.steel, cls: 'part', rx: 6, t: 2 })}
        ${fx.glass(500, 308, 14, 46, { fill: GL.pcb, cls: 'part', rx: 3 })}
        ${[0, 1, 2].map(j => `<circle cx="507" cy="${316 + j * 14}" r="2.4" fill="var(--dg-pwr)"/>`).join('')}
        ${cells.join('')}
        ${[0, 1, 2, 3].map(j => `<rect class="gold" x="${560 + j * 8}" y="372" width="5" height="7" rx="1"/>`).join('')}
      </g>

      <!-- 沿路變小的光點：每經過一級就小一圈＝電壓一級一級降下來（示意，不代表任何數字）。走 SMIL，動畫鈕會 pause -->
      <circle r="6" fill="var(--dg-sn)" opacity=".92">
        <animateMotion dur="7s" repeatCount="indefinite" path="M60,96 L112,96 L112,60 L${BBX + BBW / 2},60 L${BBX + BBW / 2},128 L${TRX},128 L388,153 L548,153 L600,153"/>
        <animate attributeName="r" values="6;6;4.4;4.4;2.6;1.4" dur="7s" repeatCount="indefinite"/>
      </circle>

      <!-- ================= 說明卡片（HTML，左右兩欄；引線由 externalize 畫，錨點在畫布上）=================
           左欄錨點 x ≤ 300、右欄錨點 x ≥ 340 —— 引線只從自己那一側進來，不橫越整張圖 -->
      <!-- 卡片只放一句話（標題 ＋ 一行）：卡片欄不可以比畫布高，不然「一頁看完」就破了；
           長一點的說明在零件小卡（parts.desc）與下面三段章節裡 -->
      ${extRow({ side: 'l', no: 1, seg: P, part: 'psu_shelf', color: COL.pwr, ax: 132, ay: 52,
    title: '電源架：多顆 PSU 並排、N＋1', sub: '交流 → 直流約 50–54 V' })}
      ${extRow({ side: 'l', no: 2, seg: P, part: 'psu_unit', color: COL.pwr, ax: 146, ay: 166,
    title: '一顆 PSU 拆開：上蓋／主板／底殼', sub: '後端是卡緣接點，不是電線' })}
      ${extRow({ side: 'l', no: 3, seg: P, part: 'psu_board', color: COL.pwr, ax: 145, ay: 258,
    title: '主板四級：PFC→LLC→同步整流→輸出', sub: '整流→隔離降壓→同步整流' })}
      ${extRow({ side: 'l', no: 10, part: 'psu_ups', color: COL.off, ax: 56, ay: 323,
    title: '機房 UPS 與設施側：不在這條鏈上', sub: '交流側、機櫃外；不列台股' })}
      ${note({ side: 'l', warn: true, title: '★ 點零件篩到的是「環節」，不是整個族群',
    lines: ['BBU 尚未建檔：這條鏈沒有 BBU 環節，點 BBU 篩到的是「電源」那一格（2308 台達電、2301 光寶科），不是做 BBU 的那幾家。',
      '示意圖，非實物比例；時間軸不標秒數：BBU 撐多久的公開說法不一致。'] })}
      ${extRow({ side: 'r', no: 4, seg: C, part: 'psu_busbar', color: COL.cu, ax: BBX + BBW / 2, ay: 230,
    title: '匯流排 busbar：厚銅排不是電線', sub: '電壓越低電流越大，銅越粗' })}
      ${extRow({ side: 'r', no: 5, seg: C, part: 'psu_whip', color: COL.cu, ax: 367, ay: 128,
    title: 'power whip：匯流排接到托盤', sub: '粗線束；連接器廠做的' })}
      ${extRow({ side: 'r', no: 6, seg: P, part: 'psu_vrm', color: COL.pwr, ax: 388, ay: 172,
    title: '板上降壓 VRM：多相', sub: '一排電感並聯輪流工作' })}
      ${extRow({ side: 'r', no: 7, seg: P, part: 'psu_die', color: COL.pwr, ax: 602, ay: 138,
    title: '終點：GPU／ASIC 核心', sub: '約 1 V 以下、電流很大' })}
      ${extRow({ side: 'r', no: 8, seg: P, part: 'psu_bbu', color: COL.pwr, ax: 600, ay: 298,
    title: 'BBU：接在直流側、在機櫃裡', sub: '掉電就頂上；跟 UPS 互補' })}
      ${extRow({ side: 'r', no: 9, seg: P, part: 'psu_scap', color: COL.pwr, ax: 392, ay: 356,
    title: '超級電容／LIC：最短的那一段', sub: '毫秒級尖峰，同直流節點' })}

      <!-- ================= ② BBU 與 UPS 的位置對照 ＋ 四層防線時間軸（預設收合；座標由 wireFolds 量）================= -->
      ${fold('psu2', '② BBU 不是小一號的 UPS：位置對照 ＋ 四層防線', '四者接在哪一側、櫃內外、各管一段時間（不標秒數）', `
      <g data-seg="${P}" data-part="psu_place">
        <rect class="part frame" x="16" y="460" width="608" height="232" rx="8"/>
        <text class="hd" x="28" y="484">BBU 不是小一號的 UPS：接的位置本來就不同</text>
        <text class="sub" x="28" y="504">兩者是互補的兩層，不是替代；也有 UPS ＋ BBU 的混合架構。</text>
        <text class="sub" x="30" y="530" style="fill:var(--dg-ink-3)">名稱</text>
        <text class="sub" x="200" y="530" style="fill:var(--dg-ink-3)">接在哪一側</text>
        <text class="sub" x="320" y="530" style="fill:var(--dg-ink-3)">櫃內還是櫃外</text>
        <text class="sub" x="450" y="530" style="fill:var(--dg-ink-3)">管哪一段時間</text>
        ${place}
        <text class="cap" x="28" y="662">★ UPS 接在交流側、機櫃外；BBU 在直流側、機櫃內。兩者是互補的兩層，不是誰替代誰。</text>
        <text class="cap" x="28" y="680">★ BBU 與超級電容接在同一個直流節點上。</text>
      </g>
      <g data-seg="${P}" data-part="psu_time">
        <rect class="part frame" x="16" y="704" width="608" height="172" rx="8"/>
        <text class="hd" x="28" y="728">四層防線，各自管一段時間（由短到長）</text>
        ${timeline}
        <text class="cap" x="150" y="840">時間越來越長 →</text>
        <path class="thin" d="M150,846 H560" marker-end="url(#psuAr)" stroke="var(--dg-pwr)"/>
        <text class="cap" x="28" y="866" style="fill:var(--dg-warn)">★ 這條軸不標秒數、也不按比例：公開來源說法不一致，講的對象也可能不同。</text>
      </g>`)}

      <!-- ================= ③ 兩欄架構對照（§3-C：不准混成一張；預設收合）================= -->
      ${fold('psu3', '③ 兩種機櫃配電：現行約 50–54 V vs 800 V 高壓直流', '右欄少一級、匯流排同比例尺畫得更細、為什麼要 800 V、2027 才放量', `
      <text class="hd" x="16" y="884">兩種機櫃配電架構並排：右邊那一欄少掉一級</text>
      <text class="sub" x="16" y="904">兩欄的匯流排用同一個比例尺畫（粗細 ∝ 1 ÷ 電壓），只表達關係，不是實際尺寸。</text>
      <path class="hair" d="M322,914 V1196"/>
      <g data-seg="${P}" data-part="psu_arch">
        <text class="lbl" x="${AC1}" y="928">現行：機櫃內約 50–54 V</text>
        <text class="lbl" x="${AC2}" y="928">800 V 高壓直流（HVDC）</text>
        ${archBox(AC1, 0, '機房交流配電', '交流進機櫃')}
        ${archBox(AC1, 1, '機櫃內電源架', '交流 → 直流 約 50–54 V')}
        ${archBox(AC1, 2, '直流匯流排', '約 50–54 V（粗）', busBar(AC1, 2, 54))}
        ${archBox(AC1, 3, '板上 DC-DC／VRM', '降到晶片核心電壓')}
        ${archBox(AC1, 4, 'GPU／ASIC 晶片', '約 1 V 以下')}
        ${archBox(AC2, 0, '周界整流：交流 → 800 V', '在機房周界就整流成直流')}
        ${archBox(AC2, 2, '直流匯流排', '800 V（細）', busBar(AC2, 2, 800))}
        ${archBox(AC2, 3, '板上降壓', '級數依設計而異')}
        ${archBox(AC2, 4, 'GPU／ASIC 晶片', '約 1 V 以下')}
        <text class="sub" x="${AC2 + 10}" y="${slot(1) + 17}" style="fill:var(--dg-warn)">← 少掉這一級</text>
        <text class="sub" x="${AC2 + 10}" y="${slot(1) + 33}" style="fill:var(--dg-warn)">不必在機櫃內再轉一次</text>
      </g>
      <text class="cap" x="16" y="1210">依公開資料，800 V 高壓直流規劃 2027 年起支援百萬瓦級機櫃 ——</text>
      <text class="cap" x="16" y="1228">是未來式，不是現在已經在跑的架構；目前量產機櫃仍以約 50–54 V 為主。</text>
      <text class="sub" x="16" y="1254">為什麼要跳到 800 V：</text>
      <text class="sub" x="16" y="1272">① 機櫃功率一路往上，低電壓送大功率就要用很粗的銅排</text>
      <text class="sub" x="16" y="1290">② 把電壓拉高，同樣的銅可以送更多功率</text>
      <text class="sub" x="16" y="1308">③ 在機房周界就整流成直流，省掉中間幾次轉換、也少掉幾次損耗</text>
      <text class="cap" x="16" y="1332" style="fill:var(--dg-warn)">※ 省銅的量化說法有兩組、基準完全不同，所以這張圖只寫定性、不寫數字。</text>`)}

      <!-- ================= ④ CRPS ＋ 卡緣連接器 ＋ 80 PLUS ＋ 五格流程 ＋ 三塊結論（預設收合）================= -->
      ${fold('psu4', '④ CRPS 型 PSU、80 PLUS 效率表、五格流程與結論', '卡緣連接器放大、效率三列附條件、流程列的分界線、三塊結論框', `
      <text class="hd" x="16" y="1394">CRPS 型 PSU：後端是卡緣連接器，不是一束電線</text>
      <g data-seg="${P}" data-part="psu_crps">
        <g class="p3" transform="translate(90,1448)">${box(0, 0, 0, IW, ID, IH)}${isoFront}${isoEdge}</g>
      </g>
      <text class="sub" x="16" y="1548">CRPS 把 PSU 標準化：尺寸、卡緣連接器</text>
      <text class="sub" x="16" y="1566">與管理介面照同一套規格，所以不同家的</text>
      <text class="sub" x="16" y="1584">可以互換，也才做得到 N＋1 與熱插拔。</text>
      <g data-seg="${P}" data-part="psu_cardedge">
        <text class="lbl" x="270" y="1420">卡緣連接器（card-edge）</text>
        <rect class="part bd2" x="270" y="1430" width="186" height="52" rx="3"/>
        ${[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(j =>
      `<rect class="gold" x="${278 + j * 13}" y="1436" width="7" height="14" rx="1"/>
           <rect class="gold" x="${278 + j * 13}" y="1462" width="7" height="14" rx="1"/>`).join('')}
        <path class="thin" d="M270,1456 H456"/>
      </g>
      <text class="sub" x="270" y="1504">上下兩排鍍金接點（示意，數量非實物）</text>
      <text class="sub" x="270" y="1522">推進去就接上 —— 熱插拔的前提</text>
      <text class="sub" x="270" y="1540">主機也從這裡讀電壓、電流與告警</text>

      <!-- ⚠ 條件那三行**一定要包在同一個群組裡**（§6-N2：效率百分比只准出現在效率表裡） -->
      <g data-seg="${P}" data-part="psu_eff">
        <rect class="part frame" x="16" y="1604" width="608" height="232" rx="8"/>
        <text class="hd" x="28" y="1628">80 PLUS 效率等級：管的是 PSU 那一級</text>
        <text class="sub" x="34" y="1650" style="fill:var(--dg-ink-3)">等級</text>
        <text class="sub" x="300" y="1650" style="fill:var(--dg-ink-3)">非冗餘型</text>
        <text class="sub" x="460" y="1650" style="fill:var(--dg-ink-3)">冗餘型</text>
        ${effRows}
        <text class="cap" x="28" y="1782" style="fill:var(--dg-warn)">★ 條件：230 V 輸入、50% 負載率。同一個等級在不同輸入電壓與負載率下門檻不同。</text>
        <text class="cap" x="28" y="1800">★ Titanium 95% 與 96% 不是打架 —— 是非冗餘型與冗餘型兩套組態，條件一樣。</text>
        <text class="cap" x="28" y="1818">※ 匯流排與板上 DC-DC 各級的通用效率值查不到公開來源，只在 PSU 這一級標效率。</text>
      </g>

      <!-- 流程列（格 1 與格 2 之間那條分界線，§3-D） -->
      <text class="hd" x="16" y="1866">供電路徑五格</text>
      <g><rect class="bd" x="16" y="1878" width="124" height="40" rx="7" stroke="var(--dg-psu-off)"/>
        <text class="lbl offtx" x="26" y="1894">交流進</text>
        <text class="sub offtx" x="26" y="1910">設施配電＋UPS</text></g>
      <path class="hair" d="M148,1870 V1930"/>
      ${processBar(154, 1878, [{ seg: P, t: 'PSU／電源架', s: '交流 → 直流' },
      { seg: C, t: '匯流排', s: '櫃內直流分配（＋BBU）' },
      { seg: P, t: '板上 DC-DC／VRM', s: '降到核心電壓' },
      { seg: P, t: '晶片', s: 'GPU／ASIC' }], 224, { cols: 2 })}
      <text class="sub" x="16" y="2000" style="fill:var(--dg-warn)">↑ 這條線的左邊是機房基礎設施（不在這條產業鏈上），右邊才是這條鏈上的東西。</text>

      <!-- 三塊結論框 -->
      <rect class="frame" x="16" y="2020" width="300" height="154" rx="8"/>
      <text class="hd" x="28" y="2044">為什麼每一級的效率都是錢</text>
      <text class="sub" x="28" y="2066">電從牆上到晶片要經過好幾級，</text>
      <text class="sub" x="28" y="2084">每一級都有損耗，而且是連乘的。</text>
      <text class="sub" x="28" y="2102">損耗變成熱，又要再花錢散掉</text>
      <text class="sub" x="28" y="2120">（回到液冷與氣冷那兩張圖）。</text>
      <text class="sub" x="28" y="2138">所以資料中心願意為更高的效率等級</text>
      <text class="sub" x="28" y="2156">付更多錢，也願意為此改整套架構。</text>

      <rect class="frame" x="324" y="2020" width="300" height="154" rx="8"/>
      <text class="hd" x="336" y="2044">這張圖上誰做哪一塊</text>
      <text class="sub" x="336" y="2066">PSU／電源架／板上 DC-DC／BBU／</text>
      <text class="sub" x="336" y="2084">800 V 電源櫃 →「電源」這一格。</text>
      <text class="sub" x="336" y="2102">匯流排 busbar 與 power whip →</text>
      <text class="sub" x="336" y="2120">「連接器／線材」這一格，</text>
      <text class="sub" x="336" y="2138">不是電源廠做的。機櫃 → 系統組裝。</text>
      <text class="sub" x="336" y="2156">設施側與 UPS 不在這條鏈上。</text>

      <rect class="frame" x="16" y="2188" width="608" height="96" rx="8"/>
      <text class="hd" x="28" y="2212">這張圖沒有回答的事</text>
      <text class="sub" x="28" y="2234">① 各家的 PSU 市占率：兩個來源給兩個數字、都沒有可查證出處，所以一個百分比都不寫。</text>
      <text class="sub" x="28" y="2252">② BBU 到底撐多久：三個來源三個答案、口徑還不一致 → 時間軸不標秒數。</text>
      <text class="sub" x="28" y="2270">③ 良率、單價、成本：查不到，不編。</text>`)}
    </svg>`;
  }

  window.DG.register('server_psu', {
    level: 'group', chain: 'ai_server',
    name: '電源：PSU、匯流排、板上降壓與 BBU',
    draw: serverPsu, native: CW, scene: null,
    q: '牆上的電進來，到 GPU 核心的零點幾伏特，中間降壓幾次、每一級是誰做的？BBU 跟機房 UPS 又差在哪？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       `cos` 只放代號，「這家在這裡負責什麼」一律讀 supply_chain.json 的 companies[].tech（R3）。
       這張圖的重點是 R4：**BBU、超級電容、晶片、設施側都不是「電源」那兩家做的**，
       走預設（data-seg → 該環節的台股）會讓這幾個零件列出台達電與光寶科 —— 那是圖在講 A、小卡答 B。*/
    parts: {
      psu_shelf: { name: '電源架與 PSU（CRPS）', desc: '把機房的交流電整成機櫃內用的直流。多顆 PSU 並排、可熱插拔，N＋1：壞一顆不用關機。', cos: ['2308', '2301'] },
      psu_unit: { name: 'PSU 本體（上蓋／底殼／風扇／卡緣接點）', desc: '拉出來拆開的那一顆：前面板有把手、風扇與指示燈，後端是一排鍍金的卡緣接點。', cos: ['2308', '2301'] },
      psu_board: { name: 'PSU 主板：PFC → LLC → 同步整流 → 輸出', desc: '功因校正把交流整成高壓直流，LLC 諧振透過變壓器隔離降壓，二次側同步整流，最後匯到輸出母線。拓樸依機種而異（示意）。', cos: ['2308', '2301'],
        note: '畫的是常見的 PFC ＋ LLC ＋ 同步整流組合；哪一家用哪一種拓樸查不到公開來源，所以不寫成任何一家的規格。' },
      psu_vrm: { name: '板上降壓 DC-DC／VRM（多相）', desc: '把匯流排的幾十伏特降到晶片核心要的零點幾伏特；一排電感並聯、相位錯開輪流工作。', cos: ['2308', '2301'],
        note: '板上 DC-DC 的實際供應分工查不到具名來源；這裡列的是「電源」這一格的台股，不代表這兩家一定供應這一級。' },
      psu_die: { name: 'GPU／ASIC 核心（受電端）', desc: '供電路徑的終點：電壓很低、電流很大，所以最後一段降壓一定要做在晶片旁邊。', cos: [],
        none: '晶片是受電端，不是電源廠做的 —— 它的設計在 IC 設計、製造在晶圓代工那幾格，這張圖只把它當終點畫。' },
      psu_bbu: { name: 'BBU 電池備援模組', desc: '接在直流側、在機櫃裡。外部電力一有閃失就立刻頂上，讓系統有時間把資料寫回去；跟 UPS 是互補的兩層。', cos: [],
        none: '★ BBU 尚未建檔：供應鏈設定裡 AI 伺服器鏈沒有 BBU 環節，所以這裡列不出做 BBU 的公司（族群「BBU 電池備援」另有 6 檔，但還沒建到環節裡）。點 BBU 篩到的「電源」這一格是 PSU 廠，不是做 BBU 的那幾家。' },
      psu_scap: { name: '超級電容／鋰離子電容（LIC）', desc: '跟 BBU 接在同一個直流節點上，負責毫秒級的瞬間電流尖峰；更長的那一段交給 BBU。', cos: [],
        none: '超級電容／LIC 的台股供應商查不到具名來源 —— 查不到就寫查不到，不編一個對應。' },
      psu_busbar: { name: '直流匯流排 busbar', desc: '沿機櫃背面垂直走的厚銅排，把約 50–54 V 直流送到每一片托盤。電壓越低電流越大、銅排就要越粗。', cos: ['3665'],
        note: '匯流排掛在「連接器／線材」這一格，不是電源廠做的：3665 貿聯-KY 的 tech 就是 Busbar 電源匯流排／power whip。' },
      psu_whip: { name: '電源線組 power whip', desc: '從匯流排分到每一片運算托盤的粗線束。', cos: ['3665'] },
      psu_rack: { name: '機櫃（虛線框）', desc: '虛線框內＝櫃內；UPS 與設施電都在框外。這個框就是「BBU 在櫃內、UPS 在櫃外」的畫面依據。' },
      psu_ups: { name: '機房 UPS 與設施側', desc: '中壓交流 → 變壓器 → 機房配電盤，UPS 接在交流側、在機櫃外面，保護整個機房、撐到發電機起來。', cos: [],
        none: '不在這條產業鏈上：中壓交流、變壓器、配電盤與 UPS 是機房基礎設施，這張圖不掛環節、不列台股。' },
      psu_place: { name: 'BBU 與 UPS 的位置對照', desc: '超級電容與 BBU 在直流側、櫃內；UPS 與發電機在交流側、櫃外。' },
      psu_time: { name: '四層防線時間軸', desc: '超級電容 → BBU → UPS → 發電機，由短到長；不標秒數（公開來源說法不一致）。' },
      psu_arch: { name: '兩種機櫃配電架構', desc: '現行約 50–54 V 與 800 V 高壓直流並排：右欄少掉機櫃內交流轉直流那一級、匯流排更細。' },
      psu_crps: { name: 'CRPS 型 PSU 外觀', desc: '長條盒，前面板把手與風扇孔、後端卡緣連接器；尺寸與介面標準化，所以不同家的可以互換。', cos: ['2308', '2301'] },
      psu_cardedge: { name: '卡緣連接器（card-edge）', desc: '上下兩排鍍金接點，推進去就接上；主機也從這裡讀電壓、電流與告警。', cos: ['2308', '2301'] },
      psu_eff: { name: '80 PLUS 效率等級', desc: '管的是 PSU 那一級：Gold／Platinum／Titanium 三列，條件是 230 V、50% 負載，冗餘與非冗餘兩套。' },
    },
  });
})();
