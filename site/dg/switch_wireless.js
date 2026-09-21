/* 網通：交換器板卡 ＋ 800G 可插拔光模組 ＋ 共同封裝光學（CPO）
   —— docs/diagram_plan.md 的第 8 張（族群 `switch_wireless`、掛在 ai_server 鏈）
   規格書：docs/diagram_specs/switch_board.md

   ================================================================
   ★ 跟 `aiServer()`（site/diagrams.js，AI 伺服器鏈的鏈層級架構圖）的分工
   ================================================================
   `aiServer()` 回答的是「**一座機櫃裡有哪幾層東西**」：機櫃、八個運算托盤、電源櫃、
   液冷 CDU。交換器在那張圖上只是機櫃最上面一條 30px 高的橫條（`data-part="ag_tor"`），
   光模組只是托盤右前方那四個小方塊（`ag_optic`）—— 它不畫、也不該畫板子裡面。
   這一張反過來：**把那一條橫條拆開放大**，只畫板卡本身 ——
   一顆交換器晶片、上千條等長差動對、前面板一整排光模組籠架、後方風扇與電源，
   以及「光引擎到底要插在前面板還是搬進封裝」這個取捨。
   兩張共用同一套等角立體語言與 `--dg-*` 色票，但**一個零件都不重複畫**：
   機櫃／托盤／GPU／冷板只在 aiServer()，板體／籠架／DSP／光引擎只在這裡。
   另外跟 `dg/pcb_rigid.js`（多層 PCB 剖面＋走線＋銅箔）也要分工：
   **多層板本身怎麼做**是那一張的題目；這裡只畫「交換器板為什麼非要這麼多層」，
   也就是訊號／地的節律與背鑽，不重畫整套 PCB 製程。

   ================================================================
   ★ 要不要真 3D：**不用**（`scene: null`）。
   ================================================================
   規格書 §0「型式」已經寫死「不用真 3D」，這裡是**複驗**而不是補簽 ——
   它當時的理由只寫了兩個答案（平面佈局、側剖面），而這張圖最後畫了四個，
   所以把四個都對一次，確認結論沒變。
   判準是 AGENTS.md 那一句「轉一圈真的能多理解一件事嗎」：
     ① 板子的**平面佈局**（什麼元件在哪、走線從哪出發到哪去）→ 等角俯視就看完了
     ② 板子的**側剖面**（訊號—地—訊號—地 的節律）→ 那是一張 2D 剖面，轉了反而看不到
     ③ 光模組**裡面**有什麼 → 那是一張拆解剖面，轉一圈只會看到一個金屬盒
     ④ 可插拔 vs CPO 的差別＝**電訊號走多遠** → 那是一段長度的對照，2D 並排最清楚
   四個答案沒有一個是「要繞到背面才看得到」的，而 3D 在手機上很重（DECISIONS #226 的代價）。
   對照：MLCC 那張做了真 3D，理由是「端電極包住五個面、側邊餘白要轉過去才看得到」——
   那個理由在這裡**不成立**。

   ================================================================
   ★ 事實來源（2026-09-21 用 WebSearch 重新查證，不是照抄規格書）
   ================================================================
   ⚠ 證據強度先講清楚：這個容器**只有 WebSearch 能用，WebFetch 一律回 EGRESS_BLOCKED**。
     所以底下每一條的證據都是「**WebSearch 摘要**」，沒有人讀過原文；
     網址留著是給下一個人去讀，不是宣稱我讀過。

   · 51.2T ＝ 64 埠 × 800G、512 條 SerDes 通道 × 100G PAM4（Broadcom Tomahawk 5）；
     102.4T ＝ 64 埠 × 1.6T（Tomahawk 6）。2U／64 × 800G OSFP／**前後直通氣流**的整機
     確實存在 → broadcom.com 新聞稿、servethehome.com、fs.com 規格頁（N9600-64OD）
     ※ 算式自洽：64×800G=51.2T、64×1.6T=102.4T、512×100G=51.2T、8×6.4T=51.2T。
       這些**只用來檢查有沒有畫離譜**，不當成規格數字標在零件旁邊。
   · CPO：Broadcom 2025-10 出貨 Tomahawk 6 – Davisson，102.4 Tb/s 共同封裝光學，
     宣稱**光互連功耗降低約 70%**，光引擎用 TSMC COUPE 平台以基板級多晶片封裝整合
     → broadcom.com/company/news/product-releases/63626、storagenewsletter.com 2025-10-10
   · 為什麼要 CPO：224G 世代 PCB 走線損耗守不住。
     ⚠ **兩個來源對 CPO 那一側給的數字不一樣**：一份說可插拔整條電通道 20 dB 以上、
     CPO 只剩 1～2 dB；另一份引 NVIDIA 硬體文件是封裝級約 4 dB vs 傳統可插拔約 22 dB。
     兩邊只有「可插拔約 20 dB 以上」對得起來，CPO 那一側差一倍以上。
     **所以畫面只寫「可插拔：20 dB 以上／CPO：個位數 dB」，不挑一個當定論**
     （CLAUDE.md：兩個來源打架不准挑順眼的）。
     → blog.apnic.net 2025-05-07 CPO deep dive、octopart.com「Designing for 224G」、
       semiengineering.com「Co-Packaged Optics Reaches Power Efficiency Tipping Point」
   · OSFP vs QSFP-DD800 的**結構差別**（多個來源一致，信心高）：
     OSFP **模組本身自帶鰭片散熱片**、體積較大、散熱裕度較高；
     QSFP-DD800 是**平頂**、靠籠架上的散熱片導熱，沿用 QSFP 機構、可向下相容 QSFP28/56；
     兩者**機構不相容，插不進對方的埠**。
     ⚠ 功耗數字各家講的不一樣（12W／12–15W／16–18W／15–20W 都有）→ **畫面一個瓦數都不寫**。
     → juniper.net 800G optics cables guide、fibermall.com、cloudswit.ch、ubytelink.com
   · 可插拔光模組是機箱裡的發熱大戶：一份 32 埠 800G 機種的資料說光模組約佔整機發熱一半，
     與 Broadcom 講的「可插拔約佔系統功耗 50%」同向 → fibermall.com「OSFP Thermal Management」
   · 交換器板層數：AI 叢集用的 800G／1.6T 交換器板需要 **40 層以上**（背板另有到 32 層的說法）
     → fastturnpcbs.com「800G PCB Design For AI Data Centers」、atlaspcb.com
     ⚠ 信心**中**：來源是 PCB 廠與產業媒體，不是任何一家的公開規格書，而且有反例
       （一份 800G 線性直驅設計的公開資料用的是 18 層）。所以畫面寫
       「**約 40 層以上（依架構而異）**」，**不准寫成「800G 一定是 48 層」**，
       圖上實際畫 19 條並標「層數為示意」。
   · 高速板材與製程：需超低損耗銅箔基板、**低粗糙度（HVLP）銅箔**、**背鑽**去掉通孔多餘的銅柱、
     阻抗控制 → nextpcb.com「224G PCB Design」、hdicircuitboard.com

   ★ 一個都不准編的：市占、良率、單價、價值量、產能、傳輸距離、瓦數、板厚 mm。
     查不到就只畫相對關係並標「示意」。

   ================================================================
   ★ data-seg：只掛 supply_chain.yaml 裡**真的存在、而且屬於 ai_server 鏈**的環節
   ================================================================
   實際查過（`pipeline/groups/supply_chain.yaml`，ai_server 鏈共 12 格）：
     switch / optical / optical_epi / hdi_pcb / ccl / ccl_material /
     connector / power / thermal / assembly / hyperscaler / fpc
   掛法：
     主板、走線、外層與內層銅、背鑽 → hdi_pcb    （金像電、臻鼎-KY、健鼎、華通、精成科、瀚宇博）
     疊構裡的內層芯板（core）      → ccl         （台光電、台燿、聯茂、騰輝電子-KY）
     半固化片（玻纖布＋樹脂）       → ccl_material（金居、南亞、建榮、富喬、德宏、榮科）
     籠架＋光模組＋光引擎＋光耦合   → optical     （華星光、波若威、上詮、眾達-KY）
     模組裡的雷射晶粒／光偵測器     → optical_epi （聯亞）
     飛越纜線／金手指等高速連接     → connector   （貿聯-KY）
     PSU、板上 VRM                → power       （台達電、光寶科）
     散熱片、系統風扇              → thermal     （奇鋐、雙鴻、一詮、健策、建準、高力）
     管理用處理器所在的整機         → switch      （智邦）
   ★ **交換器 ASIC 不掛任何 data-seg**（規格書 §6-D 的紅線）：
     `ic_design` 那一格的台股是聯發科／瑞昱／祥碩／聯詠，**沒有一家供應這一級 ASIC**，
     而且它的 chain 是 semiconductor 不是 ai_server —— 掛上去會在畫面上印出四家
     不相干的公司，那是**資訊錯誤**，比不完整更糟。改成只帶 `data-chain="semiconductor"`
     （點了跳半導體鏈），並在說明文字裡明講「這一級由外商供應，台股沒有直接對應」。
     速率換算尺同理，**不掛**。 */
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || typeof DG.register !== 'function') return;
  const STYLE = DG.STYLE, lrow3 = DG.lrow3, labelRow = DG.labelRow, processBar = DG.processBar;
  const box = DG.box, onTop = DG.onTop, onYZ = DG.onYZ, onXZ = DG.onXZ, p3 = DG.p3;
  const px = DG.px, py = DG.py, wire = DG.wire, chainLink = DG.chainLink;

  /* 這張圖自己的四個色票。
     ⚠ 照 AGENTS §15，`--dg-*` 應該住在 `site/index.html` 的 `:root` 由 art-director 擁有 ——
     但**這一批明確不准動 index.html**（同時有別人在畫別的圖，那個檔一動就撞）。
     所以先定義在這裡、只作用在這張圖（`.dgsw`），命名與寫法照既有那一組的規矩，
     **繪圖的程式碼裡一個 `#xxxxxx` 都不寫**。併版時整組搬進 `:root` 即可，呼叫端一行都不用改。
     深淺主題共用同一組：剖析圖的底 `--illus` 在兩個主題下都是深色（既有決策），
     所以這四個色在兩個主題下的對比是一樣的。 */
  const SW_STYLE = `<style>
    .dgsw{
      --dg-sw-sig:#3ee0ff;     /* 高速電訊號（差動對、SerDes 通道）—— 冷色＝電 */
      --dg-sw-fiber:#f2c14e;   /* 光纖與光訊號 —— 暖黃，一眼跟「電」分得開 */
      --dg-sw-pwr:#ff9d4d;     /* 供電（PSU → VRM → ASIC）—— 橘，而且線一定畫得比訊號粗 */
      --dg-sw-gold:#d9a441;    /* 金手指／電接點 —— 比 --dg-cu 的銅更黃，不會跟銅層混 */
    }
    .dgsw .fib{stroke:var(--dg-sw-fiber);fill:none;stroke-linecap:round}
    .dgsw .sig{stroke:var(--dg-sw-sig);fill:none;stroke-linecap:round}
    .dgsw .air{stroke:var(--dg-mute);fill:none;stroke-dasharray:7 7;opacity:.6;animation:dgdash 2.4s linear infinite}
    /* 板子上的差動對：一條**實線**的粗線（兩根導體）＋ 中間一條板色的細縫。
       為什麼不用 .flow：整片板子上十條虛線會變成一堆碎屑，讀起來像雜訊而不是走線。
       封包的動態另外用 .dpk 一條細亮線跑，虛線只出現在那一條上。
       為什麼不真的畫兩條平行線：在等角平面上要逐段算法線，轉角處還會分岔；
       「粗線＋中縫」讀起來就是「成雙成對的兩根」，而且轉角永遠不會裂開。 */
    .dgsw .dp{stroke:var(--dg-sw-sig);fill:none;stroke-width:3.4;opacity:.75;stroke-linejoin:round;stroke-linecap:round}
    .dgsw .dpg{stroke:var(--dg-pcb);fill:none;stroke-width:1.2;stroke-linejoin:round;stroke-linecap:round}
    .dgsw .dpk{stroke:var(--dg-ink);fill:none;stroke-width:1.6;opacity:.9;stroke-linecap:round}
    .dgsw .ld{stroke:var(--dg-ink-3);fill:none;stroke-width:1;opacity:.75}
    .dgsw .lyl{stroke:var(--dg-ink-3);stroke-width:1;fill:none;opacity:.5}
  </style>`;

  // ================================================================ ① 等角板卡（2.5D）
  /* 模型座標：x＝機箱深度（0＝後方，190＝前面板），y＝機箱寬度（0～300），z＝高度。
     等角投影裡 +x 往畫面右下、+y 往畫面左下，而且只有 +x／+y／+z 三個面看得到 ——
     所以**前面板在畫面右下、後方在左上**。這正是「拆掉上蓋、從前上方看進去」的視角：
       · 前面板的外側面（x=198）看得到 → 光模組籠架一整排看得到
         （一整面同規格的 I/O 全部朝同一個方向，是認出交換器板的第一個特徵）
       · 機箱後方的外側面（x=0）**看不到** —— 這是物理事實，不是漏畫。
         所以風扇畫的是**它朝向機箱內側的進風面**（拆掉上蓋真的會看到扇葉與輪轂），
         PSU 只畫模組本體與把手，它的交流插座在機箱外側、這個視角看不到。 */
  const DEPTH = 190, WID = 300, BZ = 12;      // 板體厚度刻意畫厚一點，邊緣才看得出「一疊很多層」
  const ISO_X = 484, ISO_Y = 128, ISO_S = 1;  // 等角本體在畫面上的原點與等比倍率
  const ax = (x, y) => +(ISO_X + ISO_S * px(x, y)).toFixed(1);
  const ay = (x, y, z) => +(ISO_Y + ISO_S * py(x, y, z)).toFixed(1);
  const AX = 110;                             // ASIC 的前緣（走線從這裡出發）

  // 前面板上 16 個籠架（實機 2U 是 64 個，畫 16 個並在註腳標示意）
  const NCAGE = 8, CU0 = 14, CPITCH = 34.5, CW = 26, CH = 13;
  const cageU = (i) => CU0 + i * CPITCH;
  const cageY = (i) => cageU(i) + CW / 2;     // 籠架對應到板子上的 y 座標（走線用）

  function frontPanel() {
    const vents = [];
    for (let u = 6; u < 296; u += 7) vents.push(`<rect class="f3" x="${u}" y="37" width="3" height="2" rx="1"/>`);
    const cages = [];
    for (let r = 0; r < 2; r++) for (let i = 0; i < NCAGE; i++) {
      const u = cageU(i), v = r ? 21 : 5;
      cages.push(`<rect class="part f1" x="${u}" y="${v}" width="${CW}" height="${CH}" rx="1.6"/>`
        + `<rect class="lit" x="${u + 2.4}" y="${v + 2.4}" width="15" height="${CH - 4.8}" rx="1"/>`
        // 拉環：可插拔光模組最好認的一個特徵（沒有拉環就只是一排色塊）
        + `<rect class="part f1" x="${u + 19.5}" y="${v + 3.4}" width="4.2" height="${CH - 6.8}" rx="1.4"/>`
        + `<circle class="dot blink b${(i + r) % 3 + 1}" cx="${u + 3.4}" cy="${v + CH - 2.2}" r="1.5"/>`);
    }
    return box(DEPTH, 0, 0, 8, WID, 40)
      + onYZ(DEPTH + 8, 0) + `<rect class="part f2" x="0" y="0" width="${WID}" height="40"/>`
      + vents.join('') + cages.join('') + '</g>';
  }

  function fanUnit(fy) {
    const blades = [];
    for (let k = 0; k < 7; k++) {
      const a = k * Math.PI * 2 / 7, a2 = a + 0.58;
      const pt = (r, t) => `${(22 + r * Math.cos(t)).toFixed(1)},${(27 + r * Math.sin(t)).toFixed(1)}`;
      blades.push(`<path class="part f1" d="M${pt(6.5, a)}L${pt(18, a + 0.32)}L${pt(18, a2 + 0.32)}L${pt(6.5, a2)}Z"/>`);
    }
    return box(4, fy, BZ, 20, 44, 38)
      // 朝向機箱內側的進風面：看得到扇框、扇葉與輪轂（AGENTS §11 明列的識別特徵）
      + onYZ(24, fy) + `<rect class="part f2" x="0" y="${BZ}" width="44" height="38" rx="3"/>`
      + `<circle class="f3" cx="22" cy="${BZ + 19}" r="18.5"/>`
      + `<g transform="translate(0,${BZ - 8})"><g class="spin">${blades.join('')}</g>`
      + `<circle class="part f1" cx="22" cy="27" r="6.5"/><circle class="lit" cx="22" cy="27" r="2.8"/></g></g>`;
  }

  function psuUnit(fy) {
    return box(4, fy, BZ, 40, 54, 30)
      // 把手（熱抽換模組的識別特徵），畫在頂面
      + onTop(BZ + 30, `<rect class="part f1" x="30" y="${fy + 18}" width="10" height="18" rx="3"/>`
        + `<rect class="etch" x="10" y="${fy + 8}" width="24" height="38" rx="2"/>`);
  }

  /* 等長蛇行差動對：從 ASIC 的前緣出發，走到前面板每一個籠架的背面。
     ★ 規格書 §3-B 的三條硬規則就在這一段：
       · 每一條的兩端一定是「一個籠架 ↔ 那顆 ASIC」，不准兩個籠架直連
       · **近的埠要繞路、遠的埠直走**（等長）—— folds 就是這一條
       · 方向是**雙向**的（每個埠都同時收與發），所以封包一半正向、一半反向
     · 走飛越纜線的那三個埠（i = 0,1,2）**板子上就不再畫走線**，
       不然等於同一個訊號走了兩條路。 */
  function traces() {
    const out = [], tgt = [];
    for (let i = 3; i < NCAGE; i++) { tgt.push(cageY(i) - 5); tgt.push(cageY(i) + 5); }
    const maxD = Math.max.apply(null, tgt.map(y => Math.abs(y - 150)));
    tgt.forEach((yT, n) => {
      const yA = 128 + n * (44 / (tgt.length - 1));   // ASIC 前緣上的出發點
      const lane = 118 + n * 2.6;                     // 每條各走自己的 x 通道，不會疊成一條粗線
      const s = yT > yA ? 1 : -1, dy = Math.abs(yT - yA);
      const pts = dy < 14
        ? [[AX, yA], [lane + 6, yT]]
        : [[AX, yA], [lane - 6, yA], [lane, yA + s * 6], [lane, yT - s * 6], [lane + 6, yT]];
      let x = lane + 6;
      const room = Math.floor((182 - x) / 16);
      const folds = Math.max(0, Math.min(room, Math.round((maxD - dy) / 33)));
      for (let f = 0; f < folds; f++) {               // 蛇行：上斜 45° → 平 → 下斜 45°，補的長度就在這裡
        pts.push([x + 6, yT - 6], [x + 10, yT - 6], [x + 16, yT]);
        x += 16;
      }
      pts.push([DEPTH - 1, yT]);
      const d = 'M' + pts.map(p => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join('L');
      out.push(`<path class="dp" d="${d}"/><path class="dpg" d="${d}"/>`
        + `<path class="dpk flow${(n % 2) ? ' rev' : ''}${(n % 3 === 0) ? ' slow' : ''}" d="${d}"/>`);
    });
    return out.join('');
  }

  function isoBoard() {
    // 板體側邊的切口：一條一條銅色細帶 ＝「這片板子是一疊很多層壓起來的」
    const edge = [];
    for (let v = 1.4; v < BZ - 1; v += 2.6)
      edge.push(`<rect x="0" y="${v.toFixed(1)}" width="${DEPTH}" height="1.2" fill="var(--dg-cu)" opacity=".6"/>`);
    const board = p3({ id: 'sw_pcb', seg: 'hdi_pcb' },
      box(0, 0, 0, DEPTH, WID, BZ) + onXZ(0, WID) + edge.join('') + '</g>');

    const vrm = [];
    for (let r = 0; r < 2; r++) for (let c = 0; c < 4; c++)
      vrm.push(box(30 + r * 13, 126 + c * 13, BZ, 10, 10, 7));
    // VRM 緊貼 ASIC（規格書 §3-C：大電流走不遠，所以一定緊鄰）
    const vrmG = p3({ id: 'sw_vrm', seg: 'power' }, vrm.join(''));

    const fins = [];
    // 鰭片沿 x（＝前後＝氣流方向）拉長，一片片等距 —— 畫成左右向就是擋住風
    for (let i = 0; i < 11; i++) fins.push(box(54, 120 + i * 5.2, 25, 60, 2.6, 22));
    // 底板壓在晶片蓋上面（z 21 起）—— 低於晶片蓋會穿模，等角圖上會看到晶片從散熱片裡冒出來
    const hs = p3({ id: 'sw_hs', seg: 'thermal' }, box(54, 118, 21, 60, 62, 4) + fins.join(''));

    const asic = p3({ id: 'sw_asic', chain: 'semiconductor' },
      box(58, 124, BZ, 52, 52, 5)                       // 有機基板（底下一整片球柵陣列，見 ② 的頂層）
      + box(66, 132, BZ + 5, 36, 36, 4)                 // 覆晶晶片蓋
      + onTop(BZ + 9, `<rect class="etch" x="70" y="136" width="28" height="28" rx="2"/>`));

    const mgmt = p3({ id: 'sw_cpu', seg: 'switch' },
      box(28, 248, BZ, 20, 20, 5) + box(28, 274, BZ, 8, 16, 4) + box(40, 274, BZ, 8, 16, 4));

    const fly = p3({ id: 'sw_fly', seg: 'connector' },
      box(112, 100, BZ, 12, 22, 7)
      + [0, 1, 2].map(i => wire([[118, 104 + i * 6, BZ + 7], [146, 78 - i * 4, BZ + 28],
        [176, 44 - i * 8, BZ + 24], [188, cageY(i), 26]], 'flow', 'var(--dg-sw-sig)', 2.2)).join(''));

    // 氣流：前進後出（規格書 §3-D）
    const air = [44, 150, 256].map(y =>
      wire([[184, y, 50], [120, y, 48], [30, y, 46]], 'air', 'var(--dg-mute)', 2.4)).join('');
    // 供電：PSU（後方）→ VRM（貼著 ASIC）→ ASIC，由高壓到低壓，而且線比訊號線粗
    const pw = wire([[24, 40, BZ + 6], [34, 118, BZ + 6], [44, 138, BZ + 6]], 'flow', 'var(--dg-sw-pwr)', 4.4)
      + wire([[24, 268, BZ + 6], [36, 196, BZ + 6], [46, 168, BZ + 6]], 'flow', 'var(--dg-sw-pwr)', 4.4);

    /* 繪製順序＝由遠到近（DG.box 沒有深度排序，順序錯了後面的零件會蓋到前面的）。
       等角投影下 x+y 越大越靠近鏡頭；前面板 x 最大，所以永遠畫最後。 */
    return board
      + `<g pointer-events="none">${onTop(BZ, traces())}</g>`
      + p3({ id: 'sw_psu', seg: 'power' }, psuUnit(2) + psuUnit(244))
      + p3({ id: 'sw_fan', seg: 'thermal' }, fanUnit(76) + fanUnit(128) + fanUnit(180))
      + vrmG
      + `<g pointer-events="none">${pw}</g>`
      + asic + hs + mgmt + fly
      + `<g pointer-events="none">${air}</g>`
      + p3({ id: 'sw_cage', seg: 'optical' }, frontPanel());
  }

  // ================================================================ ② 疊構節律條（純 2D）
  /* 規格書 §3-A 的兩條硬規則，缺一整張圖就答不了主標題：
       · **每一層高速訊號層的正上方與正下方，都必須各有一層完整的接地參考層**
       · **疊構必須上下對稱**（不對稱＝壓合後翹曲）
     下面這張表由上到下讀，而且**完全鏡像對稱**（正中央是電源層）。 */
  const LY = [[5, 'sm'], [5, 'out'], [10, 'pp'], [5, 'gnd'], [9, 'core'], [5, 'sig'], [9, 'core'], [5, 'gnd'],
    [20, 'rep'], [8, 'pwr'], [20, 'rep'],
    [5, 'gnd'], [9, 'core'], [5, 'sig'], [9, 'core'], [5, 'gnd'], [10, 'pp'], [5, 'out'], [5, 'sm']];
  const LY_FILL = { sm: 'var(--dg-pcb)', out: 'var(--dg-cu)', pp: 'var(--dg-cer)', core: 'var(--dg-cover)',
    gnd: 'var(--dg-cu)', sig: 'var(--dg-1)', pwr: 'var(--dg-cu)', rep: 'var(--dg-cover)' };
  // core＝雙面覆銅的內層芯板（CCL 本身）；pp＝半固化片（玻纖布＋樹脂）；其餘的銅與線路是 PCB 廠做的
  const LY_SEG = { sm: 'hdi_pcb', out: 'hdi_pcb', pp: 'ccl_material', core: 'ccl', gnd: 'hdi_pcb',
    sig: 'hdi_pcb', pwr: 'hdi_pcb', rep: 'ccl' };

  function stack(x0, y0) {
    const W = 132, out = [], mark = {};
    let y = y0;
    LY.forEach((o, i) => {
      const h = o[0], k = o[1];
      out.push(`<g data-seg="${LY_SEG[k]}" data-part="sw_ly_${k}_${i}">`
        + `<rect class="part" x="${x0}" y="${y}" width="${W}" height="${h}" fill="${LY_FILL[k]}" stroke="none"/>`
        // 高速訊號層：一段一段成雙成對的差動對（跟「一整片銅」的接地層一眼分得開）
        + (k === 'sig' ? [0, 1, 2, 3, 4, 5].map(j => `<rect x="${x0 + 5 + j * 21}" y="${y + 1}" width="7" height="${h - 2}" fill="var(--dg-sw-sig)"/>`
          + `<rect x="${x0 + 14 + j * 21}" y="${y + 1}" width="7" height="${h - 2}" fill="var(--dg-sw-sig)"/>`).join('') : '')
        // 芯板與半固化片：玻纖布的編織紋（銅箔基板的識別特徵）
        + (k === 'core' || k === 'pp' ? [0, 1, 2, 3, 4, 5, 6, 7, 8].map(j => `<path class="lyl" d="M${x0 + 8 + j * 14},${y}V${y + h}"/>`).join('') : '')
        + (k === 'rep' ? `<text class="num" x="${x0 + W / 2}" y="${y + 13}" text-anchor="middle" style="fill:var(--dg-ink-3);font-weight:700">⋮ ×N</text>` : '')
        + `</g>`);
      if (mark[k] == null) mark[k] = +(y + h / 2).toFixed(1);
      y += h;
    });
    // 頂面外層上的球柵陣列銲墊 —— ASIC 就是從這裡把上千條線往下扇出
    out.push([0, 1, 2, 3, 4, 5, 6].map(j => `<circle cx="${x0 + 26 + j * 13}" cy="${y0 + 4}" r="2.6" fill="var(--dg-sw-gold)"/>`).join(''));
    return { svg: out.join(''), mark: mark, bot: y };
  }

  // 背鑽孔特寫：上半段有銅、下半段孔徑較大而且**沒有銅**
  function backdrill(x0, y0, h) {
    const w = 150, cut = +(y0 + h * 0.56).toFixed(1);
    return `<g data-seg="hdi_pcb" data-part="sw_backdrill">
      <rect class="part" x="${x0}" y="${y0}" width="${w}" height="${h}" rx="3" fill="var(--dg-cover)"/>
      ${[0, 1, 2, 3, 4, 5, 6, 7].map(j => `<path class="lyl" d="M${x0},${(y0 + 6 + j * (h - 12) / 7).toFixed(1)}H${x0 + w}"/>`).join('')}
      <rect x="${x0 + 26}" y="${y0 + 4}" width="16" height="${h - 8}" rx="2" fill="var(--dg-1)"/>
      <rect x="${x0 + 26}" y="${y0 + 4}" width="4" height="${h - 8}" fill="var(--dg-cu)"/>
      <rect x="${x0 + 38}" y="${y0 + 4}" width="4" height="${h - 8}" fill="var(--dg-cu)"/>
      <path d="M${x0 + 32},${cut}H${x0 + 58}" stroke="var(--dg-err)" stroke-width="1.8" fill="none"/>
      <rect x="${x0 + 100}" y="${y0 + 4}" width="16" height="${(cut - y0 - 4).toFixed(1)}" rx="2" fill="var(--dg-1)"/>
      <rect x="${x0 + 100}" y="${y0 + 4}" width="4" height="${(cut - y0 - 4).toFixed(1)}" fill="var(--dg-cu)"/>
      <rect x="${x0 + 112}" y="${y0 + 4}" width="4" height="${(cut - y0 - 4).toFixed(1)}" fill="var(--dg-cu)"/>
      <rect x="${x0 + 96}" y="${cut}" width="24" height="${(y0 + h - cut - 4).toFixed(1)}" rx="2" fill="var(--dg-2)" opacity=".9"/>
    </g>`;
  }

  // ================================================================ ③ 800G 可插拔光模組
  /* 外型對照：OSFP **自帶鰭片**、QSFP-DD800 **平頂**靠籠架散熱（多個來源一致，信心高）。
     ⚠ 功耗瓦數各家講的不一樣，所以一個瓦數都不寫（見檔頭）。 */
  function formFactor(x0, y0, osfp) {
    const w = 118, h = 30;
    const top = osfp
      ? [0, 1, 2, 3, 4, 5, 6, 7].map(j => `<rect x="${x0 + 16 + j * 10}" y="${y0 - 14}" width="4" height="14" rx="1" fill="var(--dg-ni)"/>`).join('')
      : `<rect x="${x0 + 8}" y="${y0 - 17}" width="${w - 4}" height="11" rx="2" fill="var(--dg-ni)" opacity=".7"/>`
        + [0, 1, 2, 3, 4, 5, 6].map(j => `<rect x="${x0 + 16 + j * 13}" y="${y0 - 27}" width="4" height="11" rx="1" fill="var(--dg-ni)" opacity=".7"/>`).join('')
        + `<text class="num" x="${x0}" y="${y0 - 34}" style="fill:var(--dg-ink-3)">散熱片長在籠架上</text>`;
    return `<g data-seg="optical" data-part="sw_ff_${osfp ? 'osfp' : 'qsfpdd'}">
      ${top}
      <rect class="part" x="${x0}" y="${y0}" width="${w}" height="${h}" rx="3" fill="var(--dg-el)"/>
      <rect x="${x0 + 4}" y="${y0 + 5}" width="13" height="${h - 10}" rx="2" fill="var(--dg-sw-fiber)" opacity=".85"/>
      <rect class="part" x="${x0 + w}" y="${y0 + 6}" width="9" height="${h - 12}" rx="2" fill="var(--dg-ni)"/>
      ${[0, 1, 2, 3, 4, 5, 6, 7].map(j => `<rect x="${x0 + w - 34 + j * 3.8}" y="${y0 + h - 5}" width="2.2" height="5" fill="var(--dg-sw-gold)"/>`).join('')}
      <text class="lbl" x="${x0}" y="${y0 + h + 20}">${osfp ? 'OSFP：模組自帶鰭片' : 'QSFP-DD800：平頂'}</text>
      <text class="sub" x="${x0}" y="${y0 + h + 38}">${osfp ? '體積較大、散熱裕度較高' : '沿用 QSFP 機構、可向下相容'}</text>
    </g>`;
  }

  function moduleCut(x0, y0) {
    const W = 346, H = 118;
    const blk = (dx, w, y, h, t, fill, seg, id) =>
      `<g data-seg="${seg}" data-part="${id}"><rect class="part" x="${x0 + dx}" y="${y}" width="${w}" height="${h}" rx="2.5" fill="${fill}"/>`
      + `<text class="num" x="${x0 + dx + w / 2}" y="${y + h / 2 + 4}" text-anchor="middle" style="fill:var(--dg-ink)">${t}</text></g>`;
    const RY = y0 + 12, TY = y0 + 64;   // 收（上）、發（下）
    return `<g>
      <rect class="frame" x="${x0}" y="${y0}" width="${W}" height="${H}" rx="6"/>
      <g data-seg="optical" data-part="sw_mod_fiber">
        <path class="fib flow" d="M${x0 - 36},${RY + 21}H${x0 + 12}" stroke-width="3"/>
        <path class="fib flow rev" d="M${x0 - 36},${TY + 21}H${x0 + 12}" stroke-width="3"/>
        <rect class="part" x="${x0 + 8}" y="${y0 + 8}" width="16" height="${H - 16}" rx="2" fill="var(--dg-sw-fiber)" opacity=".5"/>
      </g>
      ${blk(32, 48, y0 + 8, H - 16, '光耦合', 'var(--dg-cer-cut)', 'optical', 'sw_mod_fau')}
      ${blk(86, 50, RY, 42, 'PD', 'var(--dg-el)', 'optical_epi', 'sw_mod_pd')}
      ${blk(142, 50, RY, 42, 'TIA', 'var(--dg-el)', 'optical', 'sw_mod_tia')}
      ${blk(86, 50, TY, 42, '雷射', 'var(--dg-el)', 'optical_epi', 'sw_mod_ld')}
      ${blk(142, 50, TY, 42, '驅動 IC', 'var(--dg-el)', 'optical', 'sw_mod_drv')}
      ${blk(198, 64, y0 + 18, H - 36, 'DSP', 'var(--dg-1)', 'optical', 'sw_mod_dsp')}
      <path class="fib flow" d="M${x0 + 80},${RY + 21}H${x0 + 86}" stroke-width="2.4"/>
      <path class="fib flow rev" d="M${x0 + 86},${TY + 21}H${x0 + 80}" stroke-width="2.4"/>
      <path class="sig flow" d="M${x0 + 192},${RY + 21}H${x0 + 198}" stroke-width="2.4"/>
      <path class="sig flow rev" d="M${x0 + 198},${TY + 21}H${x0 + 192}" stroke-width="2.4"/>
      <g data-seg="connector" data-part="sw_mod_gold">
        <path class="sig flow" d="M${x0 + 262},${RY + 21}H${x0 + 280}" stroke-width="2.4"/>
        <path class="sig flow rev" d="M${x0 + 280},${TY + 21}H${x0 + 262}" stroke-width="2.4"/>
        ${[0, 1, 2, 3, 4, 5, 6, 7].map(j => `<rect class="part" x="${x0 + 280}" y="${y0 + 12 + j * 12}" width="46" height="7" rx="1.5" fill="var(--dg-sw-gold)"/>`).join('')}
      </g>
    </g>`;
  }

  // ================================================================ ④ 可插拔 vs CPO
  /* 兩格用**同一組畫法、同一組引線**，只有「那條藍線（電訊號）的長度」不一樣 ——
     這張圖最後一個答案就是這一件事。 */
  function compare(x0, y0, w, cpo) {
    const H = 160, by = y0 + 56, bh = 40;
    const asicX = cpo ? x0 + 130 : x0 + 30;
    const panelX = x0 + w - 44;
    const eng = cpo ? [0, 1, 2, 3].map(j =>
      `<rect class="part" x="${asicX - 26}" y="${by + 4 + j * 8.5}" width="20" height="6.5" rx="1.5" fill="var(--dg-sw-fiber)" opacity=".85"/>`
      + `<rect class="part" x="${asicX + 62}" y="${by + 4 + j * 8.5}" width="20" height="6.5" rx="1.5" fill="var(--dg-sw-fiber)" opacity=".85"/>`).join('') : '';
    const eX0 = cpo ? asicX - 26 : asicX + 62;
    const eLen = cpo ? 26 : panelX - 36 - (asicX + 62);
    return `<g>
      <rect class="frame" x="${x0}" y="${y0}" width="${w}" height="${H}" rx="8"/>
      <text class="hd" x="${x0 + 14}" y="${y0 + 22}">${cpo ? 'CPO：光引擎搬到晶片旁邊' : '可插拔光模組（現在的主流）'}</text>
      <text class="sub" x="${x0 + 14}" y="${y0 + 40}">${cpo ? '光引擎與 ASIC 共用同一片基板，光纖直接從基板邊緣拉出去' : '光電轉換全在前面板的模組裡，電訊號要先走過整片板子'}</text>
      <rect x="${x0 + 14}" y="${by + bh + 6}" width="${w - 28}" height="7" rx="2" fill="var(--dg-pcb)"/>
      <g data-seg="${cpo ? 'optical' : 'hdi_pcb'}" data-part="sw_cmp_${cpo ? 'cpo' : 'plug'}">
        ${eng}
        <rect class="part" x="${asicX}" y="${by}" width="62" height="${bh}" rx="3" fill="var(--dg-el)"/>
        <text class="num" x="${asicX + 31}" y="${by + 24}" text-anchor="middle" style="fill:var(--dg-ink)">ASIC</text>
        <path class="sig" d="M${eX0},${by + bh + 18}h${eLen}" stroke-width="5"/>
        ${cpo
        ? `<path class="fib flow" d="M${asicX + 82},${by + 12}H${panelX + 4}" stroke-width="3"/>
           <path class="fib flow rev" d="M${panelX + 4},${by + 30}H${asicX + 82}" stroke-width="3"/>`
        : `<rect class="part" x="${panelX - 36}" y="${by + 6}" width="36" height="${bh - 12}" rx="2" fill="var(--dg-el)"/>
           <path class="fib flow" d="M${panelX + 26},${by + 12}H${panelX + 4}" stroke-width="3"/>
           <path class="fib flow rev" d="M${panelX + 4},${by + 30}H${panelX + 26}" stroke-width="3"/>`}
        <rect class="part" x="${panelX}" y="${by - 2}" width="8" height="${bh + 4}" rx="2" fill="var(--dg-ni)"/>
      </g>
      <text class="num" x="${eX0}" y="${by + bh + 34}" style="fill:var(--dg-sw-sig)">電訊號走${cpo ? '封裝內幾 mm' : '整片板子'}</text>
      <text class="sub" x="${x0 + 14}" y="${y0 + H - 10}"${cpo ? '' : ' style="fill:var(--dg-warn)"'}>${cpo
      ? '取捨：壞一顆光引擎不能像模組那樣抽換，要修就是整台'
      : '取捨：壞了抽換就好，但電通道損耗大、模組本身很耗電'}</text>
    </g>`;
  }

  // ================================================================ 整張圖
  function switchBoard() {
    const st = stack(30, 546);
    // 疊構條的四條引線：從那一層的中線繞到右邊說明文字的基線
    const ld = (k, ly) => `<path class="ld" d="M162,${st.mark[k]}H174V${ly - 4}H186"/>`;
    return `<svg class="dg dgm dgsw" viewBox="0 0 980 1482" width="100%" style="display:block">${STYLE}${SW_STYLE}
      <text class="ttl" x="16" y="26">交換器板卡：一顆晶片對上所有的埠，逼出 40 層以上的板子</text>
      <text class="cap" x="16" y="46">上面是拆掉上蓋的 2U 板卡（前面板在右下、風扇與電源在左上）。下面依序回答：板子為什麼要這麼多層、800G 光模組裡面有什麼、光引擎該放前面板還是搬進封裝。</text>

      <!-- ================= ① 等角板卡 ================= -->
      <g transform="translate(${ISO_X},${ISO_Y}) scale(${ISO_S})">${isoBoard()}</g>

      <text class="hd" x="16" y="84">① 板上到底有什麼</text>
      <text class="sub" x="16" y="106">一顆交換器晶片坐在正中</text>
      <text class="sub" x="16" y="124">央，上千條差動對從它底</text>
      <text class="sub" x="16" y="142">下呈放射狀出發，等長走</text>
      <text class="sub" x="16" y="160">到前面板的每一個埠 ——</text>
      <text class="sub" x="16" y="178">這跟伺服器主機板完全不同。</text>

      <rect class="frame" x="16" y="196" width="196" height="96" rx="8"/>
      <text class="hd" x="30" y="218">速率怎麼換算</text>
      <text class="num" x="30" y="240">64 埠 × 800G ＝ 51.2T</text>
      <text class="num" x="30" y="260">64 埠 × 1.6T ＝ 102.4T</text>
      <text class="num" x="30" y="280">32 埠 × 800G ＝ 25.6T</text>

      <text class="hd" x="16" y="322">氣流：前進後出</text>
      <text class="sub" x="16" y="344">冷風從前面板的埠之間吸</text>
      <text class="sub" x="16" y="362">進來，橫掠光模組與散熱</text>
      <text class="sub" x="16" y="380">鰭片，由後方風扇抽出。</text>
      <text class="cap" x="16" y="402">鰭片順著前後氣流，不是橫著</text>
      <text class="cap" x="16" y="420">擋住風。本圖畫埠側進風機種。</text>
      ${chainLink('semiconductor', 16, 438, '← 看半導體鏈')}

      <!-- 右側說明欄（引線接回零件） -->
      ${lrow3({ id: 'sw_cage', seg: 'optical', label: '前面板光模組籠架（一整排同規格）',
    sub: '2U 排 64 個 × 800G；光模組很耗電', ax: ax(198, 150), ay: ay(198, 150, 28) }, 684, 96, 280, 0)}
      ${lrow3({ id: 'sw_hs', seg: 'thermal', label: '晶片散熱片（鰭片順著前後氣流）',
    sub: '一片片等距的薄片；畫成左右向＝擋住風', ax: ax(84, 144), ay: ay(84, 144, 47) }, 684, 150, 280, 1)}
      ${lrow3({ id: 'sw_vrm', seg: 'power', label: '板上多相供電模組（VRM）',
    sub: '把 12V／48V 降到次伏特級，所以緊貼晶片', ax: ax(42, 150), ay: ay(42, 150, 19) }, 684, 204, 280, 2)}
      ${lrow3({ id: 'sw_fan', seg: 'thermal', label: '系統風扇（後方、可熱抽換）',
    sub: '看得到扇框、扇葉與輪轂；前面板全給光口', ax: ax(24, 150), ay: ay(24, 150, 32) }, 684, 258, 280, 3)}
      ${lrow3({ id: 'sw_psu', seg: 'power', label: '電源供應器 PSU（後方、1+1 冗餘）',
    sub: '交流／直流母線進來，往前送到 VRM', ax: ax(24, 270), ay: ay(24, 270, 34) }, 684, 312, 280, 4)}
      ${lrow3({ id: 'sw_fly', seg: 'connector', label: '近晶片飛越纜線（flyover）',
    sub: '高速訊號改走纜線，繞開走不動的那段 PCB', ax: ax(146, 80), ay: ay(146, 80, 40) }, 684, 366, 280, 5)}
      ${lrow3({ id: 'sw_pcb', seg: 'hdi_pcb', label: '主板：高層數多層板（MLB）',
    sub: '板子很厚、一層層壓起來 —— 剖面看 ②', ax: ax(60, 300), ay: ay(60, 300, 4) }, 684, 420, 280, 6)}
      <g data-chain="semiconductor" data-part="sw_asic_row">
        <rect x="676" y="459" width="280" height="40" rx="6" fill="none"/>
        <circle cx="689" cy="472" r="4" fill="var(--dg-ink-3)"/>
        <text class="lbl" x="700" y="476">交換器晶片（switch ASIC）</text>
        <text class="sub" x="700" y="492">這一級由外商供應，台股沒有直接對應</text>
      </g>

      <!-- ================= ② 板子為什麼要這麼多層 ================= -->
      <text class="hd" x="16" y="528">② 層數是被訊號逼出來的：訊號—地—訊號—地</text>
      ${st.svg}
      ${ld('out', 558)}${ld('gnd', 602)}${ld('sig', 646)}${ld('pwr', 690)}
      <text class="lbl" x="190" y="558">外層線路 ＋ 防焊</text>
      <text class="sub" x="190" y="575">球柵陣列銲墊在這一層</text>
      <text class="lbl" x="190" y="602">接地層（完整的一片銅）</text>
      <text class="sub" x="190" y="619">訊號層的上下都要各有一層</text>
      <text class="lbl" x="190" y="646">高速訊號層（差動對）</text>
      <text class="sub" x="190" y="663">成雙成對、兩條線長度要配對</text>
      <text class="lbl" x="190" y="690">電源層（厚銅）</text>
      <text class="sub" x="190" y="707">疊構上下對稱，不然壓合會翹</text>

      ${backdrill(430, 556, 104)}
      <text class="num" x="438" y="678" style="fill:var(--dg-err)">沒背鑽</text>
      <text class="num" x="512" y="678" style="fill:var(--dg-accent)">背鑽過</text>
      <text class="lbl" x="430" y="702">背鑽（back-drill）</text>
      <text class="sub" x="430" y="719">通孔用不到的那一段銅是「天線」，會反射訊號</text>

      <rect class="frame" x="612" y="540" width="354" height="142" rx="8"/>
      <text class="hd" x="626" y="562">為什麼是 40 層以上</text>
      <text class="sub" x="626" y="584">一顆 51.2T 的晶片有 512 條 SerDes 通道，</text>
      <text class="sub" x="626" y="602">收發各一組差動對 —— 光是高速 I/O 就上千條，</text>
      <text class="sub" x="626" y="620">而且全部要從同一顆球柵陣列底下逃出來。</text>
      <text class="sub" x="626" y="638">每一層訊號層的上下都要各配一層完整接地層，</text>
      <text class="sub" x="626" y="656">阻抗才守得住 → 線塞不下就只能往上疊層。</text>
      <text class="sub" x="626" y="674" style="fill:var(--dg-warn)">層數多了還要換超低損耗板材、低粗糙度銅箔。</text>

      <!-- ================= ③ 800G 可插拔光模組 ================= -->
      <text class="hd" x="16" y="760">③ 800G 可插拔光模組：裡面有什麼、兩種外型差在哪</text>
      ${formFactor(16, 826, true)}
      ${formFactor(16, 966, false)}
      <text class="cap" x="16" y="1060">兩種機構不相容，插不進對方的埠。</text>

      <text class="cap" x="300" y="786">光在左、電在右：上排是收（光→電），下排是發（電→光）。</text>
      ${moduleCut(300, 794)}
      <text class="cap" x="262" y="942">光纖</text>

      ${labelRow('optical', 684, 812, '光學耦合（透鏡／光纖陣列 FAU）', '矽光子晶片與光纖之間的對準接合介面', 380, 852, 280)}
      ${labelRow('optical_epi', 684, 866, '雷射晶粒 ／ 光偵測器（PD）', '發：雷射加調變；收：PD 把光變回電流', 436, 900, 280)}
      ${labelRow('optical', 684, 920, 'TIA ／ 驅動 IC', '收端把微弱電流放大；發端推上調變器', 492, 906, 280)}
      ${labelRow('optical', 684, 974, 'DSP：模組裡最大也最耗電的一顆', '做等化與前向錯誤更正，把訊號整回來', 562, 906, 280)}
      ${labelRow('connector', 684, 1028, '金手指：模組唯一的電接點', '插進籠架就接到主板，這就是「可插拔」', 626, 906, 280)}

      <!-- ================= 價值鏈流程列 ================= -->
      <text class="cap" x="16" y="1090">從板材到交付雲端：這條鏈上台股站在哪幾格（點一格＝篩那個環節的成分股）</text>
      ${processBar(16, 1098, [{ seg: 'ccl', t: '銅箔基板 CCL', s: '超低損耗板材' },
    { seg: 'hdi_pcb', t: '高層數多層板', s: '40 層以上・背鑽' },
    { seg: 'optical', t: '光模組／光引擎', s: '800G 可插拔・CPO' },
    { seg: 'connector', t: '高速連接／線材', s: '飛越纜線・籠架' },
    { seg: 'switch', t: '交換器整機', s: '白牌 ODM 組裝' }], 174)}

      <!-- ================= ④ 可插拔 vs CPO ================= -->
      <text class="hd" x="16" y="1178">④ 為什麼要把光引擎搬到晶片旁邊：差別只有「電訊號走多遠」</text>
      ${compare(16, 1190, 470, false)}
      ${compare(496, 1190, 470, true)}

      <text class="sub" x="16" y="1374" style="fill:var(--dg-warn)">★ 電通道插入損耗：可插拔整條路徑約 20 dB 以上；搬進封裝之後只剩個位數 dB。速率每升一級，這件事就更嚴重一次。</text>
      <text class="cap" x="16" y="1394">示意圖，非實物比例｜層數、走線條數、光模組數量與元件位置均為示意。</text>
      <text class="cap" x="16" y="1412">圖上畫 16 個籠架（實機 64 個）、19 條疊構（實機約 40 層以上，⋮ ×N，依架構而異）。</text>
      <text class="cap" x="16" y="1430">CPO 那一側兩個來源給的損耗數字不同（1～2 dB 與約 4 dB），所以只寫「個位數」，不挑一個當定論。</text>
      <text class="cap" x="16" y="1448">零件顏色＝環節色，點零件只亮不篩（點環節色標才會篩）。來源與信心度見 docs/diagram_specs/switch_board.md。</text>
      <!-- 規格書留下來的那條提醒：族群名單比這張圖畫的範圍寬。不點名、不自己改 YAML（AGENTS §5）。 -->
      <text class="cap" x="16" y="1466" style="fill:var(--dg-warn)">★「高速交換器與無線網路」這個族群同時包含電信與消費性網通設備；這張圖畫的只是其中「資料中心交換器」那一段，成分股不等於都做這個。</text>
    </svg>`;
  }

  window.DG.register('switch_wireless', {
    level: 'group', chain: 'ai_server',
    name: '網通：交換器板卡 ＋ 800G 光模組 ＋ CPO',
    draw: switchBoard, native: 980, scene: null,
    q: '一台 800G／1.6T 交換器的板子上到底有什麼？光模組插在前面板跟搬進封裝（CPO）差在哪、台股吃得到哪幾格？',
  });
})();
