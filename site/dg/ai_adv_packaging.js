/* IC 封裝剖析 —— docs/diagram_plan.md 的第 4 張（族群 `ai_adv_packaging`、semiconductor 鏈）
   規格書（就是合約）：docs/diagram_specs/ic_package.md

   ---- ★ 2026-09-22 的三件事（DECISIONS #234，位階高於規格書 §0／§1）----
   ① **去重**：`site/diagrams.js` 的鏈層級 `semiconductor()` 退場了。
      Andy：「圖二 圖三 是否重疊題材，是的話幫我刪除一個」——
      兩張畫的都是同一顆 CoWoS 封裝的剖面，分工只存在於設計文件裡、不存在於他的螢幕上。
      那張的兩塊獨門資訊**併進本圖**，一塊都沒有丟：
        · 右側「每一層對應到哪個供應鏈環節」→ 本圖右欄每一列右端的**環節標籤**
        · 「設計 → 晶圓製造 → CoWoS 堆疊 → 上蓋測試 → 上板」→ 本圖 ⑦ 的整鏈流程列
   ② **3D 搬過來**：規格書 §1 原本寫死 `scene: null`，理由是「這條鏈已經有一個 3D 場景」。
      那個前提隨著 ① 消失了 —— 現在 `SCENES.semiconductor` 就是**本圖**的 3D，
      所以 `scene: 'semiconductor'`。Andy 這一輪要的是把 3D 畫得更細緻，不是拿掉。
      （§1 另一半的理由仍然成立：剖面上的層不必轉、尺度尺不能進透視 ——
        所以 3D 畫的是**同一顆封裝的立體版**，2D 的五個分析區塊一個都沒有搬進 3D。）
   ③ **畫得像電路圖**：Andy「不能看起來只有像是一般的方塊，他是電路圖就是要有電路圖的樣貌。
      有 IC 就有 IC 在上面」→ 新增 ⑤ **載板俯視**（走線、焊墊、去耦電容、絲印、
      第 1 腳記號、補強環，以及 IC 本體真的擺在它該在的位置），
      剖面上也補了載板正面與背面的**去耦電容**。
   ④ **動畫拉滿、而且每一條都在講原理**：五條動線（晶粒↔晶粒、對外訊號、供電反向、
      去耦補流、熱往上）各配一句說明，收在剖面下方的動線圖例裡。
      全部走 `.flow`／SMIL，「動畫：關」兩種都真的停得住。

   ⚠ 本圖第 ③ 區的 S／R／L 並排對照仍然留著，而且更重要了：
     2D 畫 S、3D 畫 L，它們是同一族的三個變體，不是互相矛盾（規格書 §0-B #3）。

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
   不畫 HBM 堆疊內部與層數；不畫任何廠商 logo／產品外觀。
   ⚠ 「不重畫整條鏈的製程列」這一條 **2026-09-22 起不成立**（DECISIONS #234）：
     它原本的理由是「鏈層級那張已經有一條了」，那張退場之後這裡就是唯一的一條 ——
     不畫的話那塊資訊會整個消失。所以 ⑦ 就是搬過來的那一條，而且跟 ⑥ 的關係寫在圖上
     （⑥ ＝ ⑦ 第三格「CoWoS 堆疊」拆開來的內部）。

   ---- 實作邊界 ----
   · `data-part` 一律 `icp_*`。★ 2026-09-22 起 **3D 場景的 `part` 也改成同一組 `icp_*`**：
     鏈層級那張退場之後 `sc_*` 沒有第二個主人了，對齊之後「2D 點完切到 3D 還是同一個零件」。
   · `data-seg` 只掛 supply_chain.yaml 裡真的存在的環節；
     **模封 EMC 與 TIM2 兩個不掛**（前者沒有對應環節、後者跨到 ai_server 鏈，見規格書 §7-D2／D3）。
     ⚠ 去耦電容掛的 `passive_comp` **不在半導體鏈的環節名單上**，這是刻意的：
       它是真的被動元件廠在做的東西（國巨、華新科、禾伸堂、信昌電），
       R1 要求每個零件都答得出「誰做的」，掛一個假的半導體環節才是錯的。
       代價：按小卡上的「環節」鈕會答「這個環節的台股不在本鏈成分股裡」並把那幾家列出來
       —— 那是 industry.js 既有的、正確的回答，圖下的註腳也寫了這件事。
   · 色值一律走 `--dg-*`。這張圖需要七個既有 token 沒有的材質色，
     寫法是 `var(--dg-xxx, fallback)` —— 名字照既有命名，fallback 集中在下面那張表，
     art-director 之後把它們收進 index.html 的 :root 就會直接接手（:root 有定義時 fallback 不生效）。*/
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || !DG.register) { console.warn('[ai_adv_packaging] window.DG 還沒就緒，這張圖不註冊'); return; }
  const { STYLE, processBar, extRow, note, fold, fx } = DG;

  /* ★ 2026-09-23（Andy：「所有族群 2D 圖呈現風格都需要 Follow AI Server 族群內 2D 圖，
     並且需要適當的調整及填充版面間隔，不許有空白」）
     -------------------------------------------------------------------------
     原本：980 寬，左欄（x 16–300）是動線圖例、中欄是主剖面、右欄（x 696–960）是九列環節說明，
           三欄之間與右欄下方留著大片空白；四個章節用 `foldBar()` ＋ 手算的 data-y0／y1 ＋ translate。
     現在：跟 `site/dg/server_psu.js`／`liquid_cooling.js`／`switch_wireless.js` 同一套
           （DECISIONS #238／#239 的 v2 風格）：
             · svg 根掛 `rs` → `externalize()` 把說明卡片搬成 HTML（.dgc）排進畫布左右兩欄，
               欄寬由 index.html 的 .dgv2 容器查詢決定 —— 版面自己填滿，這個檔不再寫死三欄。
               左欄的動線圖例 → 五張 note 卡片（畫布上只留會動的樣本線）；
               右欄的九列環節說明 → 九張帶編號的卡片（`segCard`），環節標籤仍然是 `text.tag`。
             · 畫布從 980 收到 **660**（主角寬）：主剖面整組往左平移 175（`translate(-175,0)`），
               幾何一個數字都沒改 —— 所以規格書 §4-A 的 R1／R2／R8 全部照舊成立。
             · 章節改用 `D.fold()`（範圍由 getBBox 量），B1～D4 那一組手算位移整組退場。
             · 材質走共用介面 `D.fx`（`glowDefs`／`shadows`）。
     互動一個都沒少：24 個 `data-part` 一個不改名、`data-seg` 照舊，卡片與畫布共用同一個身分。*/
  /* ★★ 2026-09-23 §C4 根因（Andy：「IC 封裝剖析 這頁似乎沒做好，請確認」）
     ---------------------------------------------------------------------
     **先重現、再量，最後才改。** 量到的事實（Playwright，三個寬度、事件抽屜開與關都量過）：

       A. 原本懷疑的「`translate(-175,0)` 跟 660 畫布對不起來」—— **不成立，翻案**。
          主剖面群組的 `getBBox()` 回局部座標 321→698（`getBBox()` 不含元素自己的 transform），
          套上 DX 之後是 146→523，整張 svg 的 bbox 是 x 8→644，viewBox 0 0 660 573。
          **完整落在畫布裡，一點都沒有溢出。**四條章節列在 y 395／437／479／521，
          在主剖面（最深 387）**下方**，`.fbar` 寬度 628 ＝ 660−32，也沒有擠到右緣。
          1440／1600／1920（抽屜關，三欄）量到的 `.dgcanvas` 都是 660×660（scrollWidth＝clientWidth），
          沒有任何裁切。所以 W5 的位移是對的，不要再去動它。

       B. **真正的缺陷：章節② 的六張卡片被 `externalize()` 搬出章節，永遠掛在右欄。**
          `externalize()` 抓的是 `svg.querySelectorAll('g.lrow.ext')` —— 它**不看**那張卡片
          是不是住在某個 `g.dgbody[data-fold]` 裡。本圖的 16～21 號寫在 `fold('ap2', …)` 的
          內文裡，於是不管② 有沒有展開，那六張都被搬到畫布右欄。
          後果：右欄 16 張、左欄 6 張，右欄比畫布高出 900px ——
          畫布右下角一大塊空白、六張卡片孤零零貼在右緣（它們的錨點還關在收合的章節裡，
          所以連引線都畫不出來）。那就是他截圖上「版面壞掉」的樣子。
          ⚠ **全站 23 張 v2 圖只有本圖這樣寫**（機器掃過：把 `${fold(` 的內文抓出來找
            `segCard(`／`extRow(`／`note(`，只有 `ap2` 命中六次）——
            這就是「為什麼只有這一張壞」。
          修法：`segCard()` 多一個 `side` 參數，16～21 改掛**左欄**。兩欄回到 12／10，
          整頁高度 1560 → 1343，畫布下方那一大塊空白消失。
          **幾何一個數字都沒改、24 個 `data-part` 與 56 個 `data-seg` 一個不差**（改前改後逐一比對過）。

       C. 還沒修、但量到了要記下來的（**框架層，不是這張圖的問題**）：
          `.dgcanvas` 的欄寬只要小於 660，svg 就被切掉右半邊 ——
          `externalize()` 給 svg 寫死 `width/min-width:660px`，`.dgcanvas` 是 `overflow-x:auto`，
          而 `industry.js` 的置中止血只在 `clientWidth < native*0.62`（＝409px）才啟動。
          實測裂縫：容器寬 410～659（視窗 900～1150、事件抽屜開）整段沒有置中、scrollLeft＝0，
          看到的就是「主剖面右半邊不見了」。**23 張 v2 圖全中**，要修得動
          `site/diagrams.js`／`site/industry.js`／`index.html` 的 `.dgv2` 容器查詢，
          而且不能直接把 svg 縮到欄寬（字會跟著縮到 12px 以下，那是紅線）。
          留給框架層那一批處理，本次不碰。*/
  const CW = 660;
  const DX = -175;                 // 主剖面整組往左平移的量（980 → 660 的差）

  /* 說明卡片（v2）：卡片離開 SVG 變成 HTML，畫布上只留編號圓點 ＋ 引線。*/
  const card = (o) => {
    const s2 = extRow({ seg: o.seg, part: o.part, title: o.title, sub: o.sub, no: o.no,
      side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order });
    return o.color ? s2.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s2;
  };

  /* 材質色。★ 一處定義，其餘地方只准引用 C.xxx（AGENTS §15：JS 不准散落 #xxxxxx）。
     七個新 token 都給了 fallback，所以在 index.html 補進 :root 之前畫面就是對的，
     補進去之後 :root 的值會接手 —— 兩種主題共用同一組（剖析圖的底 --illus 深淺主題都是深底）。*/
  const C = {
    /* ★ 2026-09-23：這八個原本寫成 `var(--dg-xxx, #色碼)`（2026-09-22 時 index.html 的 :root
       還沒有它們，fallback 是暫時的接力棒）。八個 token 現在都已經收進 :root 了，
       fallback 變成死碼 —— 而且它是這個檔裡**唯一**的寫死色碼來源，所以一起拿掉。
       盤點依據：grep '--dg-si|--dg-si-2|--dg-organic|--dg-organic-2|--dg-emc|--dg-uf|
       --dg-metal-2|--dg-sub-2' site/index.html，八個全部命中。*/
    si: 'var(--dg-si)',                    // 矽：晶粒、矽中介層、矽橋
    si2: 'var(--dg-si-2)',                 // 矽的暗階（剖面下緣、HBM 外形）
    org: 'var(--dg-organic)',              // 有機介電：RDL 中介層、ABF 增層膜（琥珀）
    org2: 'var(--dg-organic-2)',
    emc: 'var(--dg-emc)',                  // 模封 EMC（含填料的深色樹脂）
    uf: 'var(--dg-uf)',                    // 底部填充（半透明琥珀）
    met2: 'var(--dg-metal-2)',             // 補強環（比上蓋暗一階的金屬灰）
    sub2: 'var(--dg-sub-2)',               // 載板的暗階（核心層）
    // 以下全部是 index.html 已經有的既有 token，直接用
    cu: 'var(--dg-cu)', sn: 'var(--dg-sn)', ni: 'var(--dg-ni)', pcb: 'var(--dg-pcb)',
    mute: 'var(--dg-mute)', warn: 'var(--dg-warn)', ink3: 'var(--dg-ink-3)',
    // ↓ ⑤ 載板俯視用的三個（全部是 :root 既有的 token，不是新開的）
    cer: 'var(--dg-cer)',                  // 去耦電容的陶瓷本體
    au: 'var(--dg-au)',                    // 焊墊（表面處理最外層的金）
    silk: 'var(--dg-cover)',               // 絲印（零件外框與第 1 腳記號的白漆）
    /* 動線的三個顏色刻意用**語意色**（index.html 明寫「配色不准蓋」）：
       電訊號＝冷色、供電＝橘、熱＝暖 —— 四個配色底下這三條線的意思都不會變。*/
    sig: 'var(--dg-sw-sig)', pwr: 'var(--dg-sw-pwr)', hot: 'var(--dg-hot)',
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

    /* ---------------- 動畫（Andy 2026-09-22：「所有動畫都需要再更生動，動畫效果要拉滿，
       讓讀者更明白運作原理」）。★ 關鍵在後半句：**每一條動線都要對應一句「這在講什麼」**，
       所以五條線一條一句，說明收在剖面正下方的「動線圖例」裡（同樣的顏色、同樣的動法）。
       不准為了熱鬧加沒有意義的閃爍 —— 這張圖的層是結構，不是動畫素材，層一格都不會跑。

       五條各自在講的原理：
         ① 晶粒 ↔ HBM：**橫向**走中介層的重佈線就到隔壁，不必繞到載板 —— 這就是 2.5D 的意義
         ② 對外訊號：要離開封裝的才**往下**走 µbump → TSV → C4 → 載板 → BGA
         ③ 供電：方向跟訊號**相反**（從主機板往上灌），所以用 `.rev` ＋ 橘色（--dg-sw-pwr）
         ④ 去耦：晶粒瞬間抽電來不及等主機板，由載板上的電容**就近**補（所以路徑特別短）
         ⑤ 熱：晶粒 → TIM1 → 上蓋 → TIM2 → 往上離開（--dg-hot），用 SMIL 的粒子
       ⚠ 三個顏色都是 index.html 標明「配色不准蓋」的語意色 ——
         四個配色底下「冷色＝電、橘＝供電、暖＝熱」這件事都不會變。
       ⚠ ⑤ 刻意用 SMIL（<animateMotion>）而不是 CSS：`.noanim` 只管得到 CSS 動畫，
         SMIL 要靠 `pauseAnimations()`。兩種都放一點，「動畫：關」才驗得出是不是真的全停。*/
    const heatDot = (x, d) => `<circle r="2.6" fill="${C.hot}" opacity=".9">`
      + `<animateMotion dur="2.4s" begin="${d}s" repeatCount="indefinite" path="M${x},172 V94"/></circle>`;
    const sig = `<g pointer-events="none">
      <path class="flow fast" d="M470,232 V248 H404 V232" stroke="${C.sig}" stroke-width="2" fill="none"/>
      <path class="flow fast rev" d="M540,232 V252 H606 V232" stroke="${C.sig}" stroke-width="2" fill="none"/>
      <path class="flow slow" d="M552,232 V254 H604 V290 H628 V330 H646 V${M.bgay - M.bgar}"
            stroke="${C.sig}" stroke-width="2" fill="none"/>
      <path class="flow slow rev" d="M382,${M.bgay - M.bgar} V326 H404 V290 H426 V256 H452 V232"
            stroke="${C.pwr}" stroke-width="2.2" fill="none"/>
      <path class="flow fast" d="M352,290 V296 H374 V286" stroke="${C.pwr}" stroke-width="1.8" fill="none"/>
      <path class="flow" d="M406,168 V96 M505,168 V96 M604,168 V96" stroke="${C.hot}" stroke-width="1.6" fill="none" opacity=".75"/>
      ${heatDot(406, 0)}${heatDot(505, 0.8)}${heatDot(604, 1.6)}
      <path d="M505,92 l-4,6 M505,92 l4,6" stroke="${C.hot}" stroke-width="1.6" fill="none"/>
    </g>`;

    /* 動線圖例：一條真的在動的樣本 ＋ 它在講什麼。
       樣本跟圖上那條用同一個 class 與同一個顏色，所以「動畫：關」時圖例也會一起停 ——
       讀者看到的兩個東西永遠是同一個狀態。*/
    /* ★ 2026-09-22 第二輪：改排在**左欄**（x 16–300），樣本線與標題同一行、說明另起一行。
       原本橫排在主剖面下面，一列要 38px、五列吃掉 230px 的高度 ——
       Andy 這一輪的問題正是「圖太大、一個畫面看不完」，所以往左欄擠，高度就省下來了。
       ⚠ 說明從 x=16 起、寬度只到 300，最長不准超過 23 個中文字。*/
    /* ★ 2026-09-23：樣本線留在畫布上（它要**真的在動**，「動畫：關」時要跟圖上那條一起停），
       標題與說明搬到左欄的 HTML 卡片（`note()`）。編號把兩邊對起來。*/
    const animRow = (y, cls, col, w, no) => `<g pointer-events="none">
      <path class="flow ${cls}" d="M8,${y} H50" stroke="${col}" stroke-width="${w}" fill="none"/>
      <text class="cap" x="58" y="${y + 4}" style="fill:${col}">${String(no).padStart(2, '0')}</text></g>`;

    /* 「沒有對應環節」的那兩個：★ 2026-09-22 第二輪從兩個框併成一個。
       原本兩框各佔 44px，而且各自的副標（「日系材料廠為主」「跨到 AI 伺服器鏈」）
       在最底下的註腳裡又寫了一次 —— 同一件事講兩遍就是重複，留一次。
       不掛 data-seg（點不動、也不會篩出別人的成分股）。*/
    /* 「沒有對應環節」的那兩個（模封 EMC 與 TIM2）：★ 2026-09-23 從畫布上的虛線框
       改成右欄的一張 note 卡片 —— 它本來就只是一段文字，畫成框只是在佔位置。
       不掛 data-seg（點不動、也不會篩出別人的成分股）。*/
    /* ---------------- 右欄的說明列：**多一個環節標籤**（DECISIONS #234 要併進來的第一塊）
       退場的那張鏈層級剖面，它的獨門價值就是右側那一欄「每一層對應到哪個供應鏈環節」。
       這裡不是照抄一欄文字，而是把它做成**每一列右端的標籤** ——
       這樣「這一層是什麼」與「它屬於哪一格」永遠貼在一起，不用左右對照。
       標籤走 `.tag`（fill 已經是 var(--c)＝環節色），所以它自動跟零件同色。
       ⚠ 標題靠左、標籤靠右，中間一定要留得下 —— 標籤一律寫**短名**（4 個中文字以內）。*/
    /* ★ 2026-09-22 第二輪：底框從 40 收到 36、列距從 44 收到 38。
       **字級一個都沒動**（標題 12.5px、副標 12px、行距仍然 16px）——
       收的是框與框之間的留白，不是字。九列省下 54px。*/
    /* ★ 2026-09-23：`segRow()`（右欄 x=704 的 264 寬說明列）退場，改成 `segCard()` ——
       同樣的「標題 ＋ 環節標籤 ＋ 副標」，但它是 `extRow` 產生的卡片，
       由 `externalize()` 搬到畫布右欄的 HTML 裡，欄寬跟著容器走，不再寫死 264。
       環節標籤照舊放在 `text.tag` 裡（`.tag` 的 fill 本來就是 var(--c)＝環節色），
       而且也併進卡片標題，所以卡片上看得到「這一層屬於哪一格」。*/
    /* ★ 2026-09-23（C4 修版面）：多一個 `side` 參數，預設仍然是右欄。
       為什麼需要它 —— 量到的事實寫在檔頭「§C4 根因」那一段：
       章節② 裡的六張卡片（16～21）**也會被 externalize() 搬出去**，
       所以它們不管②有沒有展開都永遠掛在右欄，右欄因此變成 16 張、左欄只有 6 張。
       把那六張改掛左欄，兩欄就回到 12／10，畫布下方那一大塊空白跟著消失。*/
    const segCard = (seg, tag, no, title, sub, ax, ay, side) => {
      const row = extRow({ seg: seg, title: tag + ' ｜ ' + title, sub: sub, no: no,
        side: side || 'r', ax: ax, ay: ay, order: no });
      // 第一個 </text> 是 .lbl 的結尾 —— 標籤插在它後面，仍然在同一個 g.lrow 裡
      return row.replace('</text>', `</text><text class="tag" x="0" y="0">${tag}</text>`);
    };

    /* ================================================================ 5 載板俯視
       Andy 2026-09-22：「不能看起來只有像是一般的方塊，**他是電路圖就是要有電路圖的樣貌。
       有 IC 就有 IC 在上面**」（DECISIONS #234）。

       剖面看得到「層」，看不到「這塊板子上面有什麼」。所以補一張把封裝翻過來看的俯視：
         · 走線 —— 扇出線，45 度轉角、差動對成雙（板子上的線不會直角轉彎）
         · 焊墊 —— 表面處理的金，每顆被動元件兩端各一塊
         · 被動元件 —— 去耦電容真的畫出兩端端電極（那是 MLCC 的識別特徵）
         · 絲印 —— 零件外框與第 1 腳記號，那是「這塊板子被設計過」的證據
         · 補強環 —— 一圈金屬框，大尺寸封裝防翹曲
         · **IC 真的在上面** —— GPU 晶粒擺中間、HBM 兩側各兩顆，位置跟剖面一致
       每一個特徵各自對到不同的公司（板子＝載板廠、電容＝被動元件廠、晶粒＝晶圓代工、
       堆疊＝先進封裝），這正是 `docs/diagram_purpose.md` R2「拆到對得到公司的粒度」。*/
    const TV = {
      bx: 20, by: 1092, bw: 450, bh: 230,          // 板子外框
      ro: [30, 1102, 430, 210],                    // 補強環外緣 x,y,w,h
      ri: [46, 1118, 398, 178],                    // 補強環內緣（板面可見區）
      px0: 120, py0: 1156, px1: 370, py1: 1258,    // 中介層佔位
      kx: 486, ky: 1102, kw: 168, kh: 200,         // 背面
    };
    // 一顆貼片電容：陶瓷本體 + **兩端的端電極**（少了端電極它就跟電阻、電感長一樣）
    const chipCap = (x, y, w, h) =>
      `<rect x="${(x + w * 0.24).toFixed(1)}" y="${y}" width="${(w * 0.52).toFixed(1)}" height="${h}" fill="${C.cer}"/>`
      + `<rect x="${x}" y="${y}" width="${(w * 0.24).toFixed(1)}" height="${h}" fill="${C.sn}"/>`
      + `<rect x="${(x + w * 0.76).toFixed(1)}" y="${y}" width="${(w * 0.24).toFixed(1)}" height="${h}" fill="${C.sn}"/>`;
    // 焊墊：電容兩端各一塊金（畫在電容底下，所以先畫墊再畫電容）
    const capPads = (x, y, w, h) =>
      `<rect x="${x - 2}" y="${y - 2}" width="${(w * 0.3).toFixed(1)}" height="${h + 4}" rx="1" fill="${C.au}"/>`
      + `<rect x="${(x + w * 0.7 + 2).toFixed(1)}" y="${y - 2}" width="${(w * 0.3).toFixed(1)}" height="${h + 4}" rx="1" fill="${C.au}"/>`;
    // 絲印框：白漆畫的零件外框
    const capSilk = (x, y, w, h) =>
      `<rect x="${x - 4}" y="${y - 4}" width="${w + 8}" height="${h + 8}" fill="none" stroke="${C.silk}" stroke-width=".7" opacity=".5"/>`;

    function boardTop() {
      const CAPW = 18, CAPH = 10;
      const capX = [];
      for (let x = 126; x <= 356; x += 28) capX.push(x);           // 9 顆一排
      const capRow = (y) => capX.map(x => capSilk(x, y, CAPW, CAPH) + capPads(x, y, CAPW, CAPH)
        + chipCap(x, y, CAPW, CAPH)).join('');

      // 扇出走線：差動對成雙、45 度轉角、末端接一塊焊墊。左右兩側各 5 對
      const fan = [];
      for (let i = 0; i < 5; i++) {
        const y = 1170 + i * 17, d = (i % 2 ? 7 : -7);
        [0, 4].forEach((o) => {
          fan.push(`<path d="M${TV.px0},${y + o} H104 L${97},${y + o + d} H56" stroke="${C.cu}" stroke-width="1.3" fill="none" opacity=".9"/>`);
          fan.push(`<path d="M${TV.px1},${y + o} H386 L${393},${y + o + d} H434" stroke="${C.cu}" stroke-width="1.3" fill="none" opacity=".9"/>`);
        });
        fan.push(`<rect x="52" y="${y + d - 1.6}" width="9" height="3.2" rx="1" fill="${C.au}"/>`);
        fan.push(`<rect x="430" y="${y + d - 1.6}" width="9" height="3.2" rx="1" fill="${C.au}"/>`);
      }

      // 中介層上的微凸塊焊墊：晶粒之間露出來的那一圈細格點
      const upads = [];
      for (let x = 196; x <= 292; x += 6) for (let y = 1164; y <= 1250; y += 6) {
        if (x > 210 && x < 280 && y > 1176 && y < 1238) continue;   // 晶粒蓋住的不畫
        upads.push(`<rect x="${x}" y="${y}" width="2.4" height="2.4" fill="${C.cu}" opacity=".75"/>`);
      }

      // HBM：四顆，長邊朝內、側面有層的刻痕（跟剖面那張同一個識別特徵）
      const hbmTop = (x) => {
        const n = [];
        for (let y = 1176; y < 1240; y += 8) n.push(`<path d="M${x},${y} h26" stroke="${C.si2}" stroke-width=".8" opacity=".75"/>`);
        return `<rect class="part" x="${x}" y="1170" width="26" height="76" rx="1.5" fill="url(#igSi)" stroke="${C.mute}" stroke-width=".9"/>${n.join('')}`;
      };
      // 晶粒：切割道（四周一圈空白）＋ 縱橫兩層頂層金屬 —— 這兩件事就是「晶粒」跟「方塊」的差別
      const dieTop = (() => {
        const m = [];
        for (let x = 220; x <= 270; x += 5) m.push(`<path d="M${x},1186 V1228" stroke="${C.cu}" stroke-width=".8" opacity=".92"/>`);
        for (let y = 1190; y <= 1226; y += 6) m.push(`<path d="M220,${y} H270" stroke="${C.cu}" stroke-width=".8" opacity=".6"/>`);
        return `<rect class="part" x="215" y="1182" width="60" height="50" rx="1.5" fill="url(#igSi)" stroke="${C.mute}" stroke-width="1"/>`
          + `<rect x="219" y="1186" width="52" height="42" fill="none" stroke="${C.mute}" stroke-width=".8" opacity=".75"/>${m.join('')}`
          + `<path d="M219,1186 L227,1186 L219,1194 Z" fill="${C.silk}" opacity=".9"/>`;
      })();

      // 背面：BGA 球陣列（中間留一個窗給背面去耦電容 LSC）
      const bb = [];
      for (let i = 0; i < 13; i++) for (let j = 0; j < 15; j++) {
        const x = 498 + i * 12, y = 1114 + j * 12;
        if (x >= 546 && x <= 606 && y >= 1180 && y <= 1226) continue;
        bb.push(`<circle cx="${x}" cy="${y}" r="3.6" fill="${C.sn}"/>`);
      }
      const lsc = [];
      [[548, 1184], [576, 1184], [548, 1206], [576, 1206]].forEach(([x, y]) => {
        lsc.push(capPads(x, y, 22, 9) + chipCap(x, y, 22, 9));
      });

      return `
      <!-- ---- 正面：載板俯視（上蓋與模封已移除） ---- -->
      <g data-seg="abf_pcb" data-part="icp_sub">
        <rect class="part" x="${TV.bx}" y="${TV.by}" width="${TV.bw}" height="${TV.bh}" rx="6" fill="url(#igSub)"/>
      </g>
      <g data-seg="abf_pcb" data-part="icp_fanout">${fan.join('')}
        <path d="M50,1122 L62,1122 L50,1134 Z" fill="${C.silk}" opacity=".85"/>
        <circle cx="436" cy="1128" r="3.4" fill="none" stroke="${C.au}" stroke-width="1.6"/>
        <circle cx="54" cy="1288" r="3.4" fill="none" stroke="${C.au}" stroke-width="1.6"/>
      </g>
      <g data-seg="adv_pkg" data-part="icp_stiff">
        <rect class="part" x="${TV.ro[0]}" y="${TV.ro[1]}" width="${TV.ro[2]}" height="16" fill="${C.met2}"/>
        <rect class="part" x="${TV.ro[0]}" y="${TV.ro[1] + TV.ro[3] - 16}" width="${TV.ro[2]}" height="16" fill="${C.met2}"/>
        <rect class="part" x="${TV.ro[0]}" y="${TV.ri[1]}" width="16" height="${TV.ri[3]}" fill="${C.met2}"/>
        <rect class="part" x="${TV.ro[0] + TV.ro[2] - 16}" y="${TV.ri[1]}" width="16" height="${TV.ri[3]}" fill="${C.met2}"/>
      </g>
      <g data-seg="adv_pkg" data-part="icp_interposer">
        <rect class="part" x="${TV.px0}" y="${TV.py0}" width="${TV.px1 - TV.px0}" height="${TV.py1 - TV.py0}" rx="2" fill="${C.si2}"/>
        ${upads.join('')}
      </g>
      <g data-seg="hbm" data-part="icp_hbm">${hbmTop(136)}${hbmTop(168)}${hbmTop(296)}${hbmTop(328)}</g>
      <g data-seg="foundry" data-part="icp_die">${dieTop}</g>
      <g data-seg="passive_comp" data-part="icp_decap">${capRow(1130)}${capRow(1272)}</g>

      <!-- ---- 背面：BGA 球陣列 + 背面去耦電容（LSC） ---- -->
      <g data-seg="abf_pcb" data-part="icp_bga">
        <rect class="part" x="${TV.kx}" y="${TV.ky}" width="${TV.kw}" height="${TV.kh}" rx="5" fill="url(#igSub)"/>
        ${bb.join('')}
      </g>
      <g data-seg="passive_comp" data-part="icp_lsc">${lsc.join('')}</g>
      <text class="sub" x="20" y="1340">正面：上蓋與模封已移除</text>
      <text class="sub" x="486" y="1340">背面：接主機板的那一面</text>`;
    }

    /* ================================================================ 版面（2026-09-22 第二輪）
       Andy：「幫我將所有 2D 3D 圖的**圖片及文字縮小一半大小**，我發現是**大小問題**
       導致整理版面塞太滿…希望能**一次看到完整資訊**。」

       這張圖第一輪做完是 980×1750 —— 正好撞在他抱怨圖太大的那一刻。壓法照優先順序，
       **一行內容都沒有刪**：
         ① 拿掉重複：標題那三行說明收成兩行；「沒有對應環節」的兩個框併成一個
            （它們的副標在最底下的註腳裡本來就又寫了一次）；右端灰字那兩行警語
            搬進註腳章節（它講的是註腳裡那件事）。
         ② 收納：四塊收進**章節列**（`wireFolds`，MLCC 那張已經在用的同一套機制），
            預設收合，主畫面只留這張圖的命題 —— **主剖面 ＋ 它的逐層環節對應 ＋ 動線圖例**。
            收納 ≠ 刪除：每一條章節列上都寫著裡面有什麼，按一下就打得開。
         ③ 重排：動線圖例從「橫排在主剖面下面」改成「直排在左欄」，省下 230px。
         ④ 縮幾何：說明列的底框 40 → 36、列距 44 → 38。
            **字級一個都沒動**（--dg-fs-* 全部原值，12px 下限是硬的）。

       收合時的高度：base 498 ＋ 四條章節列 × 44 ＋ PAD 16 ＝ **690px**。
       全部展開是 2133px（靜態 SVG 本身就是一份完整、座標正確的全展開版面，
       所以 JS 沒跑到的路徑也不會壞 —— 見 diagrams.js 的 wireFolds 註解）。

       ⚠ 改任何一個 y 之前先回來看這張表：
         always-visible   88–482（右欄最深，482）
         章節列 1  498–542   body1  542–843    ① 接點怎麼接
         章節列 2  843–887   body2  887–1223   ② 載板長什麼樣
         章節列 3 1223–1267  body3 1267–1690   ③ CoWoS 三種 ＋ 圓晶圓換方板
         章節列 4 1690–1734  body4 1734–2117   ④ 誰在做 ＋ 註腳
       ⚠ body 的 y1 要**量過內容真正的下緣**再寫，不要憑印象。
         2026-09-22 第一次寫 body3 的 y1 少算了 ④ 那兩行圖說（y=1038），
         於是 800／390 兩個寬度當場量到「圓晶圓：邊角是殘片」壓在第四條章節列上。*/
    /* ★ 2026-09-23：B1～D4 那一組手算的章節位移整組退場，改用 `D.fold()` ——
       範圍由 `getBBox()` 量，內容放在自己的自然座標就好，不會再有「少算了兩行、
       800／390 當場疊在章節列上」那種錯（上面那段註解記的就是那次）。*/

    /* 這張圖自己的樣式（★ 2026-09-23 新增，理由是 Andy 講過「螢光感太重」）：
       進來的預設狀態就是 adv_pkg 這一格被選著，主剖面上十幾個零件會一起 .sel 發光。
       發光只留給**剛剛點的那一個**（.sel-part）。全部吃 --dg-* token，一個色碼都沒有。
       ⚠ 要排在共用 STYLE 之後、特異性也要比它高（多一個 svg 型別選擇器），不然蓋不掉。*/
    const VARS = `<style>
      svg.dg.icp [data-seg].sel .part{filter:none;stroke-width:1.5}
      svg.dg.icp [data-seg].sel-part .part{stroke-width:2.6;filter:var(--dg-glow,drop-shadow(0 0 6px var(--cc)))}
      .dgwrap:has(svg.dg.icp) .dgc.dim{opacity:.55}
    </style>`;
    return `<svg class="dg dgm rs icp" viewBox="0 0 ${CW} 2133" width="100%" style="display:block">${STYLE}${VARS}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}
        <linearGradient id="igSi" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.si}"/><stop offset="1" stop-color="${C.si2}"/></linearGradient>
        <linearGradient id="igOrg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.org}"/><stop offset="1" stop-color="${C.org2}"/></linearGradient>
        <linearGradient id="igSub" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.pcb}"/><stop offset="1" stop-color="${C.sub2}"/></linearGradient>
        <linearGradient id="igLid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.sn}"/><stop offset=".55" stop-color="${C.ni}"/><stop offset="1" stop-color="${C.met2}"/></linearGradient>
        <clipPath id="igWafer"><circle cx="80" cy="960" r="56"/></clipPath>
      </defs>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">IC 封裝剖析：晶粒 → 凸塊 → 中介層 → 封裝體</text>
      <text class="cap ext" x="0" y="0">畫布上是一顆 2.5D AI 加速器封裝的剖面（由下到上）；右欄的卡片逐層講它屬於哪個供應鏈環節，左欄的五張卡片講圖上五條動線各在說什麼原理（畫布左緣那五條會動的樣本線就是它們，編號對得起來）。另外四塊（接點放大、載板俯視、CoWoS 三種、誰在做）收在下面四條章節列裡，按一下就展開 —— 收起來不是刪掉。</text>

      <!-- ================= 畫布左緣：動線樣本（說明在左欄卡片上） ================= -->
      ${animRow(108, 'fast', C.sig, 2.6, 1)}
      ${animRow(150, 'slow', C.sig, 2.6, 2)}
      ${animRow(192, 'slow rev', C.pwr, 2.8, 3)}
      ${animRow(234, 'fast', C.pwr, 2.2, 4)}
      ${animRow(276, '', C.hot, 2.2, 5)}
      ${note({ side: 'l', no: 1, order: 1, color: C.sig, title: '晶粒 ↔ 隔壁的 HBM', lines: ['橫著走中介層的重佈線就到了，不必繞到載板 —— 這就是 2.5D 的意義。'] })}
      ${note({ side: 'l', no: 2, order: 2, color: C.sig, title: '要離開封裝的訊號', lines: ['µbump → TSV → C4 → 載板 → BGA → 主機板。要離開封裝的才往下走。'] })}
      ${note({ side: 'l', no: 3, order: 3, color: C.pwr, title: '供電：方向跟訊號相反', lines: ['從主機板往上灌 BGA → 載板 → C4 → 晶粒。'] })}
      ${note({ side: 'l', no: 4, order: 4, color: C.pwr, title: '去耦電容補瞬間電流', lines: ['晶粒一瞬間抽電來不及等主機板，就近由電容補 —— 所以這條路徑特別短。'] })}
      ${note({ side: 'l', no: 5, order: 5, color: C.hot, title: '熱往上出去', lines: ['晶粒 → TIM1 → 上蓋 → TIM2 → 外部散熱器。'] })}
      ${note({ side: 'l', order: 6, title: '動線圖例：每一條線都在講一件事', lines: ['冷色＝電訊號、橘＝供電、暖＝熱。按上面的「動畫：關」五條一起停（畫布左緣的樣本線也會一起停）。'] })}

      <!-- ================= 主剖面（由下到上）＝ 這張圖的命題，永遠不收 =================
           ★ 2026-09-23：整組往左平移 175（980 → 660 的畫布差），**內部座標一個都沒改** ——
             規格書 §4-A 的 R1／R2／R8 全部靠那些數字，改它們等於重新簽一次規格。-->
      <g transform="translate(${DX},0)">
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
      <!-- 補強環：2026-09-22 從 36 收窄到 22，讓出載板正面那 16px —— 真實的封裝
           就是在補強環與中介層之間那一圈擺去耦電容，本來畫太寬把它整個蓋掉了 -->
      <g data-seg="adv_pkg" data-part="icp_stiff">
        <rect class="part" x="${M.subL}" y="${M.stiffT}" width="22" height="${M.subT - M.stiffT}" fill="${C.met2}"/>
        <rect class="part" x="666" y="${M.stiffT}" width="22" height="${M.subT - M.stiffT}" fill="${C.met2}"/>
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
      <!-- 載板正面的去耦電容：真的有兩端端電極（那是 MLCC 的識別特徵，畫成一顆方塊就跟電阻分不開）。
           它夾在補強環與中介層之間那一圈 —— 真實封裝就是擺在這裡，因為要離晶粒越近越好。 -->
      <g data-seg="passive_comp" data-part="icp_decap">
        ${[345, 651].map(x => `<rect class="part" x="${x}" y="282" width="14" height="8" fill="${C.cer}"/>`
      + `<rect x="${x}" y="282" width="3.4" height="8" fill="${C.sn}"/>`
      + `<rect x="${x + 10.6}" y="282" width="3.4" height="8" fill="${C.sn}"/>`
      + `<rect x="${x - 1}" y="289" width="5" height="2.6" fill="${C.au}"/>`
      + `<rect x="${x + 10}" y="289" width="5" height="2.6" fill="${C.au}"/>`).join('')}
      </g>
      ${balls(M.bgay, M.bgar, 30, 337, 673, C.sn, 'icp_bga', 'abf_pcb')}
      <g pointer-events="none">
        <path d="M322,368 H688" stroke="${C.mute}" stroke-width="1" stroke-dasharray="6 5" fill="none" opacity=".7"/>
        <text class="sub" x="322" y="384" style="fill:${C.ink3}">↓ 往下接主機板（本圖不畫板子，那是 AI 伺服器鏈的事）</text>
      </g>
      ${sig}
      </g>

      <!-- ================= 右欄卡片：每一層對應到哪個供應鏈環節（從退場的鏈層級剖面併進來的第一塊）
           錨點 ＝ 主剖面上的座標 ＋ DX（整組平移量），所以剖面一搬，引線自己跟著走。-->
      ${segCard('osat_test', '封測', 6, '散熱上蓋 ＋ TIM1', '上蓋、燒機、分選；TIM1 只壓在晶粒頂面', 688 + DX, 123)}
      ${segCard('adv_pkg', '先進封裝', 7, 'SoIC 混合鍵合', '銅墊對銅墊，中間沒有任何凸塊', 547 + DX, 172)}
      ${segCard('hbm', 'HBM', 8, 'HBM 堆疊（只畫外形）', '內部與層數不畫；台股無直接對應', 638 + DX, 190)}
      ${segCard('foundry', '晶圓代工', 9, '邏輯晶粒 GPU／ASIC', '覆晶朝下，接點全在下表面', 561 + DX, 206)}
      ${segCard('adv_pkg', '先進封裝', 10, '中介層 TSV ＋ RDL', '比晶粒寬，同時接住晶粒與 HBM', 650 + DX, 258)}
      ${segCard('adv_pkg', '先進封裝', 11, 'µbump／C4／底填', '接點逐級放大；底填有圓角、補強環防翹曲', 644 + DX, 282)}
      ${segCard('passive_comp', '被動元件', 12, '載板上的去耦電容', '兩端有端電極；擺得離晶粒越近越好', 659 + DX, 286)}
      ${segCard('abf_pcb', 'IC 載板', 13, 'ABF 載板 ＋ BGA', '最厚的一層；錫球是全圖最大的接點', 688 + DX, 317)}
      ${segCard('substrate_material', '載板材料', 14, 'ABF 增層膜', '琥珀色、沒有玻纖織紋；台股無對應', 686 + DX, 336)}
      ${note({ side: 'r', order: 15, title: '模封 EMC 與 TIM2', lines: ['這兩個沒有對應的環節：模封在本站沒有對應的一格（日系材料廠為主，查不到具名台股）、TIM2 通往的散熱器屬 AI 伺服器鏈。'] })}

      <!-- ================= 章節① 接點怎麼接（預設收合） ================= -->
      ${fold('ap1', '① 接點怎麼接：凸塊裡疊了五層',
      '凸塊內部五層的放大剖面，加上 C4／微凸塊／混合鍵合的同比例尺度尺', `
        <text class="hd" x="16" y="100">① 一顆凸塊裡疊了五層</text>
        ${bumpZoom}
        <text class="sub" x="16" y="342" style="fill:${C.warn}">★ Ni 一定夾在銅柱與焊錫之間 ——</text>
        <text class="sub" x="16" y="360" style="fill:${C.warn}">　 畫到焊錫外面是最常見的錯。</text>
        <!-- 尺度尺整塊往右搬到 ① 旁邊（座標一個都沒改，只有 translate）：
             展開之後是橫的兩欄，比原本直的一長條省一半高度。
             ★ 2026-09-23：畫布收到 660，translate 從 330 改成 352（尺度尺自身 16～300 寬）。-->
        <g transform="translate(352,-282)">
          <text class="hd" x="16" y="382">② 三種接法，同一個比例</text>
          ${scaleRuler}
          <text class="sub" x="16" y="610">三排畫在同一個比例上：接點越小，</text>
          <text class="sub" x="16" y="628">單位面積能接的線越多，但對平整度</text>
          <text class="sub" x="16" y="646">與潔淨度的要求也越兇。</text>
          <text class="sub" x="16" y="664">量級為示意，各世代不同。</text>
        </g>`)}

      <!-- ================= 章節② 載板長什麼樣（預設收合） ================= -->
      ${fold('ap2', '② 載板長什麼樣：走線、焊墊、被動元件與 IC',
      '正面俯視（扇出走線、金焊墊、去耦電容、絲印、補強環）與背面 BGA 球陣列', `
        <text class="hd" x="16" y="1060">把封裝翻過來看：載板上有什麼</text>
        <text class="cap" x="16" y="1080">板子不是一塊綠方塊：扇出線 45 度轉角、差動對成雙、每顆電容兩端各一塊金焊墊、</text>
        <text class="cap" x="16" y="1098">外面一圈白漆絲印與第 1 腳記號。</text>
        ${boardTop()}
        ${segCard('abf_pcb', 'IC 載板', 16, '扇出走線與焊墊', '45 度轉角、成對走線、末端接金焊墊', 434, 1187, 'l')}
        ${segCard('passive_comp', '被動元件', 17, '去耦電容（正面兩排）', '兩端端電極；愈靠近晶粒愈有效', 374, 1135, 'l')}
        ${segCard('foundry', '晶圓代工', 18, 'IC 就在板子上面', '中間是 GPU 晶粒，看得到切割道與頂層金屬', 275, 1207, 'l')}
        ${segCard('hbm', 'HBM', 19, 'HBM 四顆貼著晶粒', '長邊朝內，愈短的線愈省電', 354, 1214, 'l')}
        ${segCard('adv_pkg', '先進封裝', 20, '補強環與中介層', '一圈金屬框防翹曲；中介層架在正中央', 444, 1240, 'l')}
        ${segCard('abf_pcb', 'IC 載板', 21, '背面：BGA 球陣列', '中央留一塊窗，擺背面去耦電容 LSC', 648, 1204, 'l')}`)}

      <!-- ================= 章節③ CoWoS 三種 ＋ 圓晶圓換方板（預設收合） =================
           ★ 2026-09-23：三格從「橫排 980 寬」改成**直排三列**（660 畫布），
             每一格仍然是同一支 interCell() 產生的，所以 V4／R16「只有中介層那一層不同」
             照舊是結構性的，不是靠眼睛對。-->
      ${fold('ap3', '③ CoWoS 有三種，換的是中介層那一層',
      'S／R／L 三格同畫法對照，加上圓晶圓與方板的同比例格子', `
        <text class="hd" x="16" y="656">CoWoS 有三種：換掉的是「中介層那一層用什麼做」</text>
        ${interCell(16, 's')}
        <text class="hd" x="330" y="700">CoWoS-S：整片矽中介層</text>
        <text class="sub" x="330" y="720">有 TSV 垂直貫穿，線最密。</text>
        <text class="sub" x="330" y="738">受光罩尺寸與成本限制。</text>
        <g transform="translate(0,152)">${interCell(16, 'r')}</g>
        <text class="hd" x="330" y="852">CoWoS-R：有機 RDL 中介層</text>
        <text class="sub" x="330" y="872">沒有矽、沒有 TSV。</text>
        <text class="sub" x="330" y="890">高分子介電當應力緩衝，可做大。</text>
        <g transform="translate(0,304)">${interCell(16, 'l')}</g>
        <text class="hd" x="330" y="1004">CoWoS-L：RDL ＋ 局部矽橋</text>
        <text class="sub" x="330" y="1024">只在兩顆晶粒交界鑲一小塊矽。</text>
        <text class="sub" x="330" y="1042">要高密度的地方才用到矽。</text>
        <text class="sub" x="16" y="1110" style="fill:${C.warn}">★ 上面那張主剖面畫的是 S、3D 場景畫的是 L —— 它們是同一族的三個變體，不是互相矛盾。</text>
        <text class="sub" x="16" y="1128" style="fill:${C.warn}">　 三格用同一個畫法，只有中介層不同。</text>
        <text class="hd" x="16" y="1162">為什麼要從圓晶圓換成方板</text>
        <g transform="translate(0,222)">${panelCmp}</g>
        <text class="sub" x="330" y="1196">同一個比例、同一種格子：一格代表一顆封裝。</text>
        <text class="sub" x="330" y="1214">圓的邊角切不出完整的一格（畫成虛線殘片），</text>
        <text class="sub" x="330" y="1232">方的邊角是滿的。這就是面板級封裝（FOPLP）</text>
        <text class="sub" x="330" y="1250">被提出來的理由：面積利用率較高、材料效率較好。</text>
        <text class="sub" x="330" y="1268">業界在發展的面板規格從 310×310 mm 起，</text>
        <text class="sub" x="330" y="1286">另有更大的規格。方向明確：載板越做越大、</text>
        <text class="sub" x="330" y="1304">圓晶圓換成方板。</text>
        <text class="sub" x="16" y="1290" style="fill:${C.warn}">★ 時程不寫：台積電的面板級</text>
        <text class="sub" x="16" y="1308" style="fill:${C.warn}">　 CoPoS，三家報導的試產與量產</text>
        <text class="sub" x="16" y="1326" style="fill:${C.warn}">　 年份互相矛盾，本圖只寫方向。</text>`)}

      <!-- ================= 章節④ 誰在做 ＋ 註腳（預設收合） =================
           ★ 2026-09-23：兩排流程列從「五格橫排 178 寬」改成 3＋2 兩列（cols: 3），
             共用 processBar 的折行機制（光點沿著同一條折線跑），字級一個都沒縮。-->
      ${fold('ap4', '④ 誰在做：封裝廠五站 ＋ 整條鏈五站',
      '兩排流程列，加上註腳、資料來源與「查不到的七件事」', `
        <text class="cap" x="16" y="1396">封裝廠內部這五站（★ 晶圓凸塊與 CP 測試都在「接合」之前 ——</text>
        <text class="cap" x="16" y="1414">反過來就沒有凸塊可以接、也挑不出好晶粒）</text>
        ${processBar(16, 1424, [{ seg: 'pkg_equipment', t: '晶圓凸塊', s: '鍍 UBM → 電鍍銅柱 → 錫帽' },
      { seg: 'test_interface', t: '晶圓測試 CP', s: '探針卡扎下去，先挑出好晶粒' },
      { seg: 'pkg_equipment', t: '接合', s: '熱壓／迴焊／混合鍵合' },
      { seg: 'pkg_equipment', t: '底填與模封', s: '點膠、填充、模封、補強環' },
      { seg: 'osat_test', t: '上蓋與成品測試', s: 'TIM1、上蓋、燒機、分選出貨' }], 196, { cols: 3 })}
        <path d="M424,1416 V1474" stroke="${C.warn}" stroke-width="1.6" stroke-dasharray="5 4" fill="none"/>
        <text class="sub" x="16" y="1560" style="fill:${C.ink3}">← 前兩站還在整片晶圓上（晶圓廠／凸塊廠）；切開之後一顆一顆組起來（封裝廠／封測廠）→</text>

        <text class="cap" x="16" y="1596">再往外看一層：整條鏈由左到右的五站（上面那一排就是這裡第三格「CoWoS 堆疊」拆開來的內部）。</text>
        ${processBar(16, 1606, [{ seg: 'ip_eda', t: '設計', s: '矽智財授權、ASIC 設計服務' },
      { seg: 'foundry', t: '晶圓製造', s: '前段製程，切出邏輯晶粒' },
      { seg: 'adv_pkg', t: 'CoWoS 堆疊', s: '中介層 ＋ 晶粒 ＋ HBM' },
      { seg: 'osat_test', t: '上蓋測試', s: '封測廠：上蓋、燒機、分選' },
      { seg: 'abf_pcb', t: '上板', s: '載板 → 主機板' }], 196, { cols: 3 })}
        <path d="M424,1598 V1656" stroke="${C.warn}" stroke-width="1.6" stroke-dasharray="5 4" fill="none"/>
        <text class="sub" x="16" y="1742" style="fill:${C.ink3}">← 前兩站是「晶片從哪裡來」；後三站才是本圖畫的「被包起來、再裝上板」→</text>

        <text class="cap" x="16" y="1778">示意圖，非實物比例｜各層厚度與接點大小都是誇張過的，但「誰比誰大、誰在誰上面」不准倒過來。</text>
        <text class="cap" x="16" y="1796">畫面上沒有任何良率、產能、成本與市占數字 —— 那些查不到可引用的公開來源（見規格書 §7-C）。</text>
        <text class="cap" x="16" y="1814" style="fill:${C.warn}">★ 右欄卡片上的灰字標籤＝這一層屬於哪個環節。「先進封裝 CoWoS/SoIC」這一格在 supply_chain</text>
        <text class="cap" x="16" y="1832" style="fill:${C.warn}">　 裡一家公司都沒有，所以按小卡上的「環節」鈕會篩到 0 筆。</text>
        <text class="cap" x="16" y="1850" style="fill:${C.warn}">　 但點零件本身列得出公司：中介層、TSV、凸塊、SoIC 直接指名台積電 2330 與日月光 3711，</text>
        <text class="cap" x="16" y="1868" style="fill:${C.warn}">　 依據是那一格自己的註記（由台積電自己做、日月光承接外溢）。</text>
        <text class="cap" x="16" y="1890">點零件篩的是「環節」，不是整個族群。AI 先進封裝族群五檔（3711／3374／6271／6451／6789）裡，</text>
        <text class="cap" x="16" y="1908">只有 3711 與 3374 在本圖用到的環節名單上。</text>
        <text class="cap" x="16" y="1926">模封 EMC 與 TIM2 兩個零件沒有掛環節：前者在本站沒有對應的一格（日系材料廠為主，查不到具名台股）、</text>
        <text class="cap" x="16" y="1944">後者通往的散熱器屬 AI 伺服器鏈。</text>
        <text class="cap" x="16" y="1962">去耦電容掛的是「被動元件」，它不在半導體鏈的環節名單上，所以按那顆「環節」鈕會答</text>
        <text class="cap" x="16" y="1980">「這個環節的台股不在本鏈成分股裡」—— 那是正確答案，不是錯誤。</text>
        <text class="cap" x="16" y="1998">本圖畫「有上蓋」的型式，模封只包晶粒側面、頂面露出來接 TIM1。</text>
        <text class="cap" x="16" y="2016">資料來源與信心度全部列在 docs/diagram_specs/ic_package.md。</text>`)}
    </svg>`;
  }

  /* ================================================================ 零件 → 「誰做的」小卡
     `docs/diagram_purpose.md` §4 ＋ R1（每個零件都要答得出「誰做的」）。

     ★ 為什麼這張圖非寫不可（DECISIONS #234 的驗收第 3 條）：
       `adv_pkg`（先進封裝 CoWoS/SoIC）這一格在 `supply_chain.yaml` 裡**一家公司都沒有** ——
       schema 是「一家公司只能歸一個環節」，所以台積電歸在 foundry、日月光歸在 osat_test。
       結果是點中介層、TSV、凸塊、SoIC 這些零件時，小卡列出 **0 家**，
       看起來像壞掉，實際上是資料模型的限制。
     ★ 修法：用 `cos` **直接指名公司 id**，不動 YAML（YAML 的成分由 Andy 校訂，繪圖端不准加公司）。
       依據不是我的判斷，是那一格自己的 note：
         「CoWoS/SoIC 由台積電自己做（見晶圓代工），日月光承接外溢（見封測）」
       兩家的 `tech` 欄位也自己講了：台積電 ['N3/N2 先進製程','CoWoS-L','SoIC']、
       日月光 ['封裝','測試','CoWoS 外溢'] —— 小卡上「這家負責什麼」讀的就是這個欄位（R3）。 */
  const TSMC_ASE = ['tsmc', 'ase'];
  const PARTS = {
    // ---- 先進封裝那一格（原本 0 家的就是這幾個）
    icp_interposer: {
      name: '中介層（CoWoS 的「Wafer」）',
      desc: '架在載板與晶粒之間的那一片。它比晶粒寬，同時接住邏輯晶粒與兩側 HBM；線比載板細一個數量級，所以晶粒之間才接得起那麼多條。CoWoS-S 是整片矽＋TSV、-R 是有機重佈線、-L 是重佈線＋局部矽橋。',
      cos: TSMC_ASE,
      note: '「先進封裝 CoWoS/SoIC」這一格在 supply_chain 裡沒有成分股（一家公司只能歸一個環節），所以按小卡上的「環節」鈕會篩到 0 筆。這兩家是照那一格自己的註記指名的。',
    },
    icp_tsv: {
      name: 'TSV 矽穿孔',
      desc: '垂直貫穿整片矽中介層的銅柱，把上面的晶粒接到下面的 C4。只有 CoWoS-S 有；-R 整層沒有垂直的孔，-L 只有矽橋那一小塊裡面有。',
      cos: TSMC_ASE,
    },
    icp_rdl: {
      name: 'RDL 重佈線層',
      desc: '中介層表面那幾層細線，負責把晶粒的接點「扇出」到中介層的各處。相鄰兩層走向交錯，才不會互相干擾。',
      cos: TSMC_ASE,
    },
    icp_soic: {
      name: 'SoIC 混合鍵合界面',
      desc: '兩片晶粒銅墊直接對銅墊壓在一起，中間**沒有**任何焊料凸塊，所以接點可以做到 10 µm 以下。它跟凸塊是兩種完全不同的接法，不是「更小的凸塊」。',
      cos: TSMC_ASE,
    },
    icp_ubump: {
      name: '微凸塊 µbump',
      desc: '銅柱＋錫帽，接「中介層 ↔ 晶粒」。節距 30–60 µm 級，比下面的 C4 小一個數量級 —— 這張圖左邊那把尺量的就是這件事。',
      cos: TSMC_ASE,
    },
    icp_c4: {
      name: 'C4 凸塊',
      desc: '接「載板 ↔ 中介層」的焊錫球，迴焊之後塌成鼓形。節距 150–200 µm 級，比微凸塊大、比 BGA 小。',
      cos: TSMC_ASE,
    },
    icp_uf: {
      name: '底部填充（underfill）',
      desc: '灌進凸塊之間的膠，撐住凸塊並把熱膨脹造成的應力分散掉。側面一定會爬出一圈圓角（fillet），少了那圈圓角就只是「一層膠」。',
      cos: TSMC_ASE,
      note: '底填膠的**材料**以日商為主，查不到具名的台股供應商，所以這裡列的是做這道製程的人，不是賣膠的人。',
    },
    icp_stiff: {
      name: '補強環（stiffener）',
      desc: '圍在載板邊緣的一圈金屬框。封裝越做越大，加熱冷卻時越容易翹，這圈框就是拿來壓住翹曲的。俯視圖上看得到它是一個完整的「口」字。',
      cos: TSMC_ASE,
    },
    icp_bumpzoom: {
      name: '一顆凸塊的內部（五層）',
      desc: '由下到上是：晶粒焊墊 → UBM 三層（附著／阻障／濕潤）→ 銅柱（最厚一段）→ Ni 阻障 → 焊錫帽。Ni 一定夾在銅柱與焊錫之間，畫到焊錫外面是最常見的錯。',
      cos: TSMC_ASE,
    },
    icp_scale: {
      name: '三種接法的尺度尺',
      desc: '同一個比例上排三種接點：C4（150–200 µm 級）、微凸塊（30–60 µm 級）、混合鍵合（目標 10 µm 以下）。接點越小，單位面積接得起的線越多，但對平整度與潔淨度的要求也越兇。',
      cos: TSMC_ASE,
    },
    // ---- 三格 CoWoS 對照：各自指名同一批人（換掉的是「中介層那一層用什麼做」）
    icp_cowos_s: { name: 'CoWoS-S：整片矽中介層', desc: '有 TSV 垂直貫穿整片矽，線最密；受光罩尺寸與成本限制。', cos: TSMC_ASE },
    icp_cowos_r: { name: 'CoWoS-R：有機 RDL 中介層', desc: '沒有矽、沒有 TSV，用高分子介電當應力緩衝，可以做大。', cos: TSMC_ASE },
    icp_cowos_l: { name: 'CoWoS-L：RDL ＋ 局部矽橋', desc: '以有機重佈線為底，只在兩顆晶粒交界的正下方鑲一小塊矽橋 —— 要高密度的地方才用到矽。', cos: TSMC_ASE },
    // ---- 這幾格在 YAML 裡本來就有公司，走預設就對；只補「這是什麼」與必要的更正
    icp_die: {
      name: '邏輯晶粒（GPU／ASIC）',
      desc: '覆晶（flip-chip）朝下，接點全在下表面，所以圖上看不到任何打線的弧。俯視圖上四周那一圈空白是切割道 —— 鋸片就走在那裡。',
      cos: ['tsmc', 'umc', 'psmc'],
    },
    icp_hbm: {
      name: 'HBM 高頻寬記憶體（只畫外形）',
      desc: '十幾層 DRAM 用 TSV 打通疊起來，貼著邏輯晶粒放 —— 線越短越省電。內部層數本圖不畫，那是 HBM 自己的題目。',
      cos: [],
      none: 'HBM 本體由 SK hynix 與 Micron 自家封裝，台股沒有直接的供應商。台股的位置在更上游（設備、測試介面）與更下游（載板、系統組裝）。',
    },
    icp_sub: {
      name: 'ABF 載板',
      desc: '封裝底下那塊板子：核心層 ＋ 上下增層 ＋ 雷射盲孔電鍍銅，把中介層那幾萬個接點扇出到主機板。它是全圖最厚、最寬的一層。俯視圖上看得到走線、焊墊、絲印與第 1 腳記號。',
    },
    icp_fanout: {
      name: '載板上的扇出走線與焊墊',
      desc: '從中介層底下拉出來的線，45 度轉角、成對走（差動對），末端接一塊表面處理的金焊墊。板子上的線不會直角轉彎 —— 直角會反射訊號。圖上那個三角形是第 1 腳記號，兩個圈是對位用的基準點。',
    },
    icp_abf: {
      name: 'ABF 增層膜（介電層）',
      desc: '載板裡一層一層疊上去的樹脂膜，琥珀色、沒有玻纖織紋 —— 有織紋的是硬板用的 core，兩者是不同的材料、不同的廠。',
    },
    icp_bga: {
      name: 'BGA 錫球',
      desc: '載板背面那一整片球，把封裝接到主機板上。它是全圖最大的接點（節距通常 1 mm 級），跟上面的 C4、微凸塊差了一到兩個數量級。',
    },
    icp_lid: {
      name: '散熱上蓋（lid／IHS）',
      desc: '蓋在晶粒上的金屬蓋，腳踩在載板邊緣。熱從晶粒經 TIM1 進到它，再經 TIM2 出去給外部散熱器。',
    },
    icp_tim1: {
      name: 'TIM1 導熱介面材料',
      desc: '壓在晶粒頂面與上蓋之間的那一層，只蓋在晶粒上、不蓋滿整個上表面。它跟上蓋外面的 TIM2 是兩層不同的東西。',
    },
    // ---- 去耦電容：被動元件那一格（它不在半導體鏈的環節名單上，所以特別要講清楚）
    icp_decap: {
      name: '載板正面的去耦電容',
      desc: '晶粒在一瞬間抽大電流時，等主機板送電來不及，所以在載板上就近擺一排電容先頂著。它畫出來一定要有**兩端的端電極**——沒有端電極，它跟電阻、電感在圖上長得一模一樣。',
      cos: ['yageo', 'walsin_tech', 'holystone', 'chilisin_elec'],
      note: '被動元件不在半導體鏈的環節名單上，所以按上面那顆「環節」鈕會列出「這個環節的台股不在本鏈成分股裡」—— 那是正確的答案。這四家是做 MLCC 的；同一格的 2375 凱美是以晶片電阻進去的，不做 MLCC，所以沒有列。',
    },
    icp_lsc: {
      name: '背面去耦電容（LSC）',
      desc: '裝在載板**背面**、夾在 BGA 球陣列中間的那幾顆。正面擺不下、或需要更靠近某一路電源時就往背面擺，代價是那一塊的錫球要讓位。',
      cos: ['yageo', 'walsin_tech', 'holystone', 'chilisin_elec'],
      note: '同上：被動元件不在半導體鏈的環節名單上，按「環節」鈕會篩到 0 筆。',
    },
    icp_panel: {
      name: '圓晶圓 vs 方板',
      desc: '同一個比例、同一種格子，一格代表一顆封裝：圓的邊角切不出完整的一格（畫成虛線殘片），方的邊角是滿的。這就是面板級封裝（FOPLP）被提出來的理由。',
    },
  };

  window.DG.register('ai_adv_packaging', {
    level: 'group', chain: 'semiconductor',
    name: '先進封裝：晶粒 → 凸塊 → 中介層 → 封裝體',
    draw: icPackage, native: CW,
    /* ★ 2026-09-22（DECISIONS #234）：鏈層級那張 CoWoS 剖面退場，它的 3D 場景搬到這裡。
       規格書 §1 原本寫死 `scene: null`，理由是「這條鏈已經有一個 3D 場景」—— 那個前提沒了。*/
    scene: 'semiconductor',
    /* 這條鏈的**代表圖**：跨鏈面板（E6「ABF 這種跨類別環節要同時出現兩張架構圖」）
       要拿一張圖當半導體鏈的縮圖。鏈層級那張退場之後就是這一張。*/
    rep: true,
    parts: PARTS,
    q: '一顆 AI 晶片被「包」起來的時候，裡面到底多了哪幾層？那塊載板上又有什麼？每一層是誰在做？',
  });
})();
