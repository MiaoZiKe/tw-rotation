/* CNC 工具機：一台立式綜合加工機拆開看 —— 族群 `machine_tool`（electronics 鏈）

   ================================================================
   ★ 這個檔為什麼會存在（2026-09-23，Andy 親自抓到的重複）
   ================================================================
   Andy：「我發現工業自動化&CNC 工具機 2D 3D 內容完全相同，幫我先確認內容是屬於哪個族群，
          若兩個指同個項目就合併，不同的話就在找找那個族群的相關資料，並一樣的風格產出 2D 3D 圖」。

   查證結果是**兩個不同的族群共用了同一張圖**，不是同一件事：
     · `factory_automation`（工業自動化，15 檔）＝ 工廠自動化系統整合、設備，
       以及它的**核心傳動元件**（滾珠螺桿、線性滑軌、氣動、減速機、控制器）。
     · `machine_tool`（CNC 工具機，4 檔）＝ **綜合加工機與車床等工具機整機**。
   一個是「會動的軸與它的零件」，一個是「用那些軸組成的整台加工機」——
   所以**不合併**：`site/dg/motion_control.js` 那張留給 `factory_automation`
   （它畫的本來就是單軸模組的縱剖／橫剖／減速機／控制鏈），
   `machine_tool` 改掛這一張**整機**的圖。

   ================================================================
   ★ 這張圖回答的問題（`q`）
   ================================================================
   「一台加工機由哪些部分組成？台廠做得了整機，為什麼關鍵件還是要外購？」
   —— 第二問才是這張圖真正的價值：整機組裝與鑄件是台廠強項，
      但**控制器**幾乎全部外購（日本發那科、德國西門子、海德漢），
      高階主軸也多為進口；反過來**滾珠螺桿與線性滑軌**是台廠自己就很強的一段。
      這是「同一台機器上，台廠站在哪幾格」——
      單純畫一台機器的外觀不會講出這件事。

   ================================================================
   ★ 事實與來源（2026-09-23 用 WebSearch 查證；只有摘要，沒有人讀過原文，網址留給下一個人）
   ================================================================
   A. 出口主力機種：金屬切削工具機出口以**綜合加工機**第一、**車床**第二。
      → 台灣機械工業同業公會（TAMI）逐月「台灣工具機產業現況」新聞稿
        www.tami.org.tw/Statistics-machine_tools.html（2024 與 2025 兩個年度的稿都是同一個順序）
      信心：高（官方公會統計，兩個年度互相對得上）。
      ⚠ 各機種的**占比百分比**只在單一整理裡看到，畫面上只寫「前兩大」，不寫數字。
   B. 綜合加工機的結構：床身（雙柱式框架／鑄件）、立柱、主軸、刀庫與換刀機構、工作台、控制器。
      → 嵩富機械 www.pinnacle-mc.com、BEECNC www.beecnc.com.tw、
        程泰機械 www.goodwaycnc.com、良品工研所 www.ezneering.com（CNC 銑床／車床差異）
      信心：高（多家原廠產品頁一致；這是機構常識，不是誰家的規格）。
      ⚠ 刀庫容量（標配 40 把、可擴充）、主軸轉速與扭矩都是**某一機種的型錄數字**，
        不是通例 → 畫面上一個數字都不寫，刀庫只畫「一圈刀套」並標示「把數依機種而異」。
   C. 控制器：台灣生產的高階工具機**皆搭配進口 CNC 控制器**，
      日本發那科（FANUC）、德國西門子（SIEMENS）、海德漢（HEIDENHAIN）；
      國產的新代（Syntec）、寶元數控（LNC）在**中階與多軸**逐步推廣。
      → PanSci 泛科學 pansci.asia/archives/76879、
        複上精機 forceonecnc.com/zh-TW/blog/control-system/why-taiwan-chooses-fanuc-controllers、
        北美智權報 397 期 naipnews.naipo.com/39385/、工商時報 ctee.com.tw（2023-03「國產五軸控制器 異軍突起」）
      信心：高（四個獨立來源方向一致）。
      ⚠ **「控制器占工具機三到五成成本」這個數字不印在畫面上** ——
        它只在 PanSci 那一篇看到、其餘來源是轉述，屬於單一來源。
        畫面只寫定性的「成本占比最高的單一零組件之一」。數字留在這裡備查。
   D. 關鍵零組件的進口依賴：高階控制器與精密感測器仍須自德、日、美進口；
      但**滾珠螺桿、線性滑軌等傳動元件**台廠全球市占很高。
      → 北美智權報 397 期、工商時報 2022-04「零組件價飆 工具機廠掀漲風」（提到鑄件、控制器、馬達一起漲）
      信心：中高（兩個獨立來源；市占「很高」是定性說法，畫面不寫任何百分比）。
   E. 這一格四檔台股各自做什麼（逐家查，不靠同一篇稿）：
      · 4526 東台精機（1969 成立、2003 上市）：立／臥式加工中心機、立／臥式車床、複合加工、
        搪銑床、金屬積層製造設備、PCB 加工機、雷射加工機。→ www.tongtai.com.tw/tw/introduction.php
      · 1583 程泰機械：**電腦數值控制車床**為主（台灣規模最大的 CNC 車床廠之一）。
        → www.goodwaycnc.com、鉅亨網 cnyes.com/twstock/1583
      · 1528 恩德科技（1972 成立、2000 上市）：金屬與**非金屬**電腦數控加工中心、
        PCB 電子機械、刀具、板材。→ 鉅亨網 cnyes.com/twstock/1528/company/profile、MoneyDJ
      · 6603 富強鑫：**塑膠射出成型機**（50T～4000T、多色與單色），不是切削工具機。
        → 官網 www.fcs.com.tw/company、StockFeel 股感、Fugle 富果（三個獨立來源一致）
      信心：高（每一家都用各自的關鍵字單獨查，沒有共用同一篇稿）。
   ★ 查證過程遇到的坑（寫下來給下一個人）：
     第一次用「東台 4526 程泰 1583 恩德 1528 富強鑫 6603」一次查四家，
     摘要只答得出富強鑫與恩德，另外兩家**整段沒有內容**卻不說「查不到」——
     如果照單全收就會變成「四家裡有兩家沒查證」。拆成兩次逐家查才補齊。
     另外全程**沒有**出現「中文名（英文名）」那種括號對應（那是 2026-09-21 踩過的假對應），
     也沒有母子公司數字被混著回答的狀況（本圖一個財務數字都沒有用）。
   ★ 一個都不准編的：市占率、良率、單價、成本比例、刀庫把數、主軸轉速、精度等級、交期。
     查不到就只畫相對關係並標「示意」。

   ================================================================
   ★ data-seg：一個都不掛（跟 `motion_control.js` 同一個理由）
   ================================================================
   `pipeline/groups/supply_chain.yaml` 的 electronics 鏈只有八個環節
   （終端品牌、消費電子組裝、面板材料、手機光學、機構件、網通設備、面板、被動元件），
   **沒有任何一個跟工具機有關**。硬掛任何一個都會讓「點零件篩公司」篩到不相干的族群 ——
   那不是畫錯，那是**講錯**。所以這張圖走「只有 data-part」那條路：
   高亮與零件小卡照常，公司對應一律寫進 `parts[].none` 的整句話，
   畫面上再放一張永遠看得到的警語卡明講這件事。

   顏色一律 `--dg-*` token，JS 裡一個色碼都沒有（寫完 grep 自檢過）。
   這個檔不碰 `site/app.js`／`site/industry.js`／`site/diagrams.js`／`site/themes3d.js`。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function' || !D.fx) return;   // diagrams.js 沒載到就安靜退出
  const { extRow, note, fx } = D;

  const CW = 660;                                   // 畫布寬＝主角寬（native 跟著改）

  /* ================================================================ 小工具（寫法照 motion_control.js） */
  const f1 = (v) => (+v).toFixed(1);
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const C = (cx, cy, r, fill, cls) =>
    `<circle${cls ? ` class="${cls}"` : ''} cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}" fill="${fill}"/>`;
  const PA = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const LN = (d, col, w, cls, extra) =>
    `<path${cls ? ` class="${cls}"` : ''} d="${d}" stroke="${col}" stroke-width="${w}" fill="none"${extra || ''}/>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${f1(x)}" y="${f1(y)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;
  /* ★ 這張圖一個 data-seg 都不掛（見檔頭），所以 data-part 一律自己寫 ——
     `stampParts()` 只替掛了環節的節點蓋 dgkey。*/
  const part = (id, inner) => `<g data-part="${id}">${inner}</g>`;
  // 玻璃材質：跟 AI 伺服器那幾張同一支 D.fx.glass（機殼、鑄件、工作台這種「大塊面」才用）
  const slab = (x, y, w, h, fill, o) => fx.glass(x, y, w, h,
    { fill, cls: 'part' + ((o && o.cls) ? ' ' + o.cls : ''), rx: (o && o.r) || 2, iso: o && o.iso });

  /* 說明卡片離開 SVG 變成 HTML（externalize），畫布上只留編號圓點。
     卡片與它指的零件共用同一個 data-part：點卡片亮零件、點零件亮卡片。*/
  const card = (o) => {
    const s = extRow({ part: o.part, title: o.title, sub: o.sub, no: o.no, side: o.side,
      ax: o.ax, ay: o.ay, color: o.color, order: o.order, warn: o.warn, note: o.note });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* 元件色（卡片色條、編號圓點、引線端點共用）—— 一律 token、沒有寫死色碼。
     ⚠ 一張圖一個主色：整台機器走「鑄鐵／鋼」的銀灰，靠明暗分件；
        只有三件事被允許跳色 —— 控制與回授（訊號藍）、切削液（冷色）、外購件警示（警示色）。*/
  const COL = {
    iron: 'var(--dg-steel)',        // 鑄件：床身、立柱、鞍座
    steel: 'var(--dg-steel-2)',     // 鋼件：主軸、導螺桿、刀柄
    alu: 'var(--dg-alu)',           // 工作台
    disc: 'var(--dg-mc-disc)',      // 刀庫盤
    case: 'var(--dg-hub-lit)',      // 控制器櫃、馬達殼
    sig: 'var(--dg-accent-2d)',     // 控制訊號與回授
    cool: 'var(--dg-cool)',         // 切削液
    warn: 'var(--dg-warn)',         // 外購件、誠實性標示
    chip: 'var(--dg-oil)',          // 切屑
  };

  /* ================================================================ §1 版面常數（畫布座標，寬 660）
     一台立式綜合加工機的正視半剖，由左到右三帶：
       左帶 x 36–234   刀庫（圓盤）＋ 換刀機械手（雙臂）
       中帶 x 198–544  床身 → 鞍座 → 工作台 → 工件 ／ 立柱上的主軸頭 → 主軸 → 刀柄
       右帶 x 546–642  控制器櫃（虛線框起來的那一格＝外購）
     ⚠ 版面檢查（2026-09-23 第二輪，第一輪實際截圖抓到三處互撞才改成現在這組數字）：
       ① 刀庫馬達不可以頂到第 58 行的副標 → 圓盤中心下移到 y 176，馬達頂端 94。
       ② 換刀機械手是**整支繞中心轉**的，所以它掃出來的是一個圓，
          半徑 ＝ 臂長 36 ＋ 爪 12 ＝ 48。圓心 (186, 268) 到工作台左緣 x 238 還有距離，
          到刀庫外環（圓心 (92,176)、半徑 56）的圓心距 131.5 ＞ 48 ＋ 56 —— 兩個圓不相交。
       ③ 三個軸向箭頭各自放在沒有零件的空檔：X 在工作台左段上方、Z 在主軸頭左側、Y 在床身正面。*/
  const BEDY = 344, BEDH = 44;                      // 床身上緣／高
  const SADY = 322, TBLY = 300;                     // 鞍座上緣／工作台上緣
  const TBX0 = 238, TBW = 196;                      // 工作台左緣／寬
  const COLX = 486, COLY = 76, COLW = 58;           // 立柱
  const HDX = 344, HDY = 156, HDH = 58;             // 主軸頭
  const SPX = 400;                                  // 主軸軸心 x
  const MAGX = 92, MAGY = 176, MAGR = 46;           // 刀庫圓盤
  const ATCX = 186, ATCY = 268, ATCL = 36;          // 換刀機械手軸心與臂長
  const CBX = 552, CBY = 80, CBW = 86;              // 控制器櫃

  /* ---- 刀庫：一圈刀套 ＋ 插在刀套裡的刀柄（錐柄 ＋ 刀刃）。
     ★ 識別特徵：**刀套是繞著一個圓盤排成一圈的**，而且每一個刀套裡是「上粗下尖」的錐柄。
        畫成一排方塊就不是刀庫。把數依機種而異 —— 這裡畫 10 個並在卡片上標「示意」。
     ★ 動畫：**整個圓盤連同刀套一起等速轉**（刀庫轉位就是這樣找刀的）。
        圓形繞自己的中心轉，在正視圖裡本來就是對的 —— 這是這張圖唯一可以直接用 rotate 的幾何。*/
  function magazine() {
    const n = 10, g = [];
    g.push(C(MAGX, MAGY, MAGR + 10, 'var(--dg-frame-f)', 'mtring'));
    const pockets = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const px = Math.cos(a) * MAGR, py = Math.sin(a) * MAGR;
      const rot = (a * 180 / Math.PI + 90).toFixed(1);
      pockets.push(`<g transform="translate(${f1(px)},${f1(py)}) rotate(${rot})">`
        + R(-7, -9, 14, 12, 'var(--dg-mc-case)', null, 2)
        + PA('M-5,3 L5,3 L3,11 L-3,11Z', 'var(--dg-steel-2)')
        + PA('M-3.4,11 L3.4,11 L2.2,17 L-2.2,17Z', 'var(--dg-mute)')
        + '</g>');
    }
    g.push(part('mt_mag', `<g transform="translate(${MAGX},${MAGY})">`
      + `<g class="spin mtslow">`
      + C(0, 0, MAGR, 'var(--dg-mc-disc)', 'part')
      + C(0, 0, MAGR * 0.34, 'var(--dg-frame-f)')
      + pockets.join('')
      + `</g></g>`));
    g.push(part('mt_magmot', R(MAGX - 13, MAGY - MAGR - 36, 26, 24, 'var(--dg-mc-case)', 'part', 3)
      + LN(`M${MAGX},${MAGY - MAGR - 12} V${MAGY - MAGR + 2}`, 'var(--dg-steel-2)', 3)));
    return g.join('');
  }

  /* ---- 換刀機械手（雙臂式 ATC）：一支兩端各有一個爪的臂，繞中心轉。
     ★ 識別特徵：**兩端對稱**（一端抓主軸上的舊刀、另一端抓刀庫裡的新刀），
        轉 180 度就完成交換。單臂畫法沒辦法解釋「一次換兩把」。
     ★ 動畫：整支臂繞中心等速轉 —— 這是它真正在做的動作，不是閃。*/
  function atc() {
    const claw = (s) => `<g transform="translate(${s * ATCL},0)">`
      + PA(`M-8,-6 L8,-6 L8,6 L-8,6Z`, 'var(--dg-steel-2)')
      + PA(`M-8,-6 L-8,6 L-12,3.5 L-12,-3.5Z`, 'var(--dg-mc-case)')
      + PA(`M8,-6 L8,6 L12,3.5 L12,-3.5Z`, 'var(--dg-mc-case)')
      + PA(`M-3.5,6 L3.5,6 L2.3,13 L-2.3,13Z`, 'var(--dg-mute)')
      + '</g>';
    return part('mt_atc', `<g transform="translate(${ATCX},${ATCY})">`
      + `<g class="spin mtmid">`
      + PA(`M${-ATCL - 12},-7 L${ATCL + 12},-7 L${ATCL + 12},7 L${-ATCL - 12},7Z`, 'var(--dg-mc-cam)', 'part')
      + claw(-1) + claw(1)
      + C(0, 0, 10, 'var(--dg-steel)')
      + `</g>`
      + C(0, 0, 4.2, 'var(--dg-mute)')
      + `</g>`);
  }

  /* ---- 主軸頭（Z 軸）＋ 主軸 ＋ 刀柄 ＋ 刀具。
     ★ 識別特徵三件：① 主軸頭是**掛在立柱的線性滑軌上**（上下走）、
        ② 主軸是一根**被前後兩組軸承夾住的軸**（錐孔朝下）、
        ③ 刀柄是**錐形**（靠錐面定位，不是靠螺絲鎖）。
     ⚠ 主軸與刀具**不可以用 rotate 畫轉動**：在正視圖裡它們是長方形，
        繞中心轉出來是「歪掉的一根棒子」，那在物理上是錯的（第一輪就是這樣，截圖立刻看得出來）。
        改成兩個讀得對的做法：
          ① 主軸鼻端畫一個**透視圓環**（橢圓），上面有一顆繞著跑的光點 —— 圓周運動；
          ② 刀刃上的溝是**會往下跑的斜虛線**（.flow）—— 那正是旋轉中的螺旋刃在正視圖裡的樣子。
        馬達裡面那顆風扇是圓的，所以它照舊用 rotate。*/
  function spindle() {
    const g = [];
    g.push(part('mt_head', slab(HDX, HDY, 112, HDH, 'var(--dg-mc-case)', { r: 4 })
      + R(HDX + 10, HDY + 8, 92, 7, 'var(--dg-steel)', null, 2)));
    g.push(part('mt_spmot', R(SPX - 20, HDY - 42, 40, 42, 'var(--dg-mc-case)', 'part', 4)
      + `<g transform="translate(${SPX},${HDY - 21})"><g class="spin mtfast">`
      + [0, 1, 2, 3, 4, 5].map((j) => LN(`M0,0 L${f1(12 * Math.cos(j * 1.047))},${f1(12 * Math.sin(j * 1.047))}`, 'var(--dg-steel-2)', 1.6)).join('')
      + `</g></g>`));
    g.push(part('mt_bear', [0, 1].map((k) => C(SPX, HDY + 16 + k * 24, 14, 'var(--dg-steel)', 'part')
      + C(SPX, HDY + 16 + k * 24, 8, 'var(--dg-frame-f)')
      + [0, 1, 2, 3, 4, 5, 6, 7].map((j) => C(SPX + 11 * Math.cos(j * 0.785), HDY + 16 + k * 24 + 11 * Math.sin(j * 0.785), 2.2, 'var(--dg-mc-ball)')).join('')).join('')));
    // 主軸本體（靜止）＋ 鼻端的透視圓環與繞著跑的光點（＝在轉）
    const ring = `M${SPX - 13},250 a13,4.6 0 1,0 26,0 a13,4.6 0 1,0 -26,0`;
    g.push(part('mt_spindle', R(SPX - 10, 208, 20, 40, 'var(--dg-steel-2)', 'part', 2)
      + LN(`M${SPX - 5},210 V246`, 'var(--dg-mute)', 1)
      + LN(`M${SPX + 5},210 V246`, 'var(--dg-mute)', 1)
      + PA(`M${SPX - 10},248 L${SPX + 10},248 L${SPX + 7},258 L${SPX - 7},258Z`, 'var(--dg-steel)')
      + LN(ring, 'var(--dg-accent-2d)', 1.2, ' opacity=".7"')
      + `<circle r="2.8" fill="var(--dg-flow-dot)"><animateMotion dur="1.1s" repeatCount="indefinite" path="${ring}"/></circle>`));
    // 刀柄（錐形）＋ 刀刃（螺旋刃用會跑的斜虛線表示旋轉）
    g.push(part('mt_tool', R(SPX - 13, 244, 26, 7, 'var(--dg-steel-2)', 'part', 2)
      + PA(`M${SPX - 11},251 L${SPX + 11},251 L${SPX + 7},270 L${SPX - 7},270Z`, 'var(--dg-mute)', 'part')
      + PA(`M${SPX - 5},270 L${SPX + 5},270 L${SPX + 4},290 L${SPX - 4},290Z`, 'var(--dg-mc-cam)')
      + LN(`M${SPX - 4},272 L${SPX + 4},280`, 'var(--dg-steel)', 1.4, ' class="flow fast"')
      + LN(`M${SPX - 4},280 L${SPX + 4},288`, 'var(--dg-steel)', 1.4, ' class="flow fast"')));
    return g.join('');
  }

  /* ---- 切削液噴嘴 ＋ 切屑：加工真的在發生的證據。切屑往兩側飛、切削液往下澆。*/
  function cutting() {
    const jets = [0, 1, 2].map((i) => `<g class="drop${i ? ' d' + (i + 1) : ''}">`
      + C(SPX - 40 + i * 3, 264, 2.6, 'var(--dg-cool)') + '</g>').join('');
    const chips = [-1, 1].map((s) => [0, 1, 2].map((j) =>
      `<g class="drop${j ? ' d' + (j + 1) : ''}">`
      + PA(`M${f1(SPX + s * (10 + j * 8))},${f1(272 - j * 4)} l${s * 6},-5 l1,5Z`, 'var(--dg-oil)') + '</g>').join('')).join('');
    return part('mt_coolant', LN(`M${SPX - 72},236 H${SPX - 44} V252`, 'var(--dg-cool)', 2.4)
      + R(SPX - 49, 252, 10, 8, 'var(--dg-mc-case)', 'part', 2) + jets)
      + part('mt_chip', chips);
  }

  /* ---- 三軸：每一軸都是「伺服馬達 ＋ 滾珠螺桿 ＋ 線性滑軌」。
     ★ 這就是這張圖跟 `factory_automation` 那張的接縫：**那張畫的是這裡的一根軸拆開**。
        這裡只畫得出「三根軸各裝在哪裡、往哪個方向走」，不重畫螺帽剖面。*/
  function axes() {
    const g = [];
    g.push(part('mt_x', R(TBX0 - 6, 326, TBW + 12, 6, 'var(--dg-steel-2)', 'part', 3)
      + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((j) => LN(`M${TBX0 + 4 + j * 18},326 l6,6`, 'var(--dg-mute)', 1.2)).join('')
      + R(TBX0 - 34, 318, 28, 24, 'var(--dg-mc-case)', null, 3)));
    g.push(part('mt_y', LN('M262,356 l40,22', 'var(--dg-steel-2)', 5)
      + R(300, 368, 24, 18, 'var(--dg-mc-case)', null, 3)));
    g.push(part('mt_z', R(COLX - 12, 100, 6, 206, 'var(--dg-steel-2)', 'part', 3)
      + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((j) => LN(`M${COLX - 12},${110 + j * 19} l6,6`, 'var(--dg-mute)', 1.2)).join('')
      + R(COLX - 22, 72, 26, 24, 'var(--dg-mc-case)', null, 3)));
    g.push(part('mt_rail', R(COLX + 2, 100, 7, 236, 'var(--dg-steel)', 'part', 2)
      + R(TBX0 - 6, 336, TBW + 12, 6, 'var(--dg-steel)', 'part', 2)));
    return g.join('');
  }

  /* ---- 控制器櫃：操作面板（畫面 ＋ 手輪）、CNC 控制器、三台伺服驅動器 ＋ 主軸驅動器。
     ★ 這一格是整張圖的重點：**它是外購的**。所以框用警示色的虛線，而不是跟機體同色。*/
  function cabinet() {
    const x = CBX, y = CBY, w = CBW, g = [];
    g.push(`<rect class="mtbuy" x="${x - 6}" y="${y - 8}" width="${w + 12}" height="240" rx="8"/>`);
    g.push(part('mt_panel', slab(x, y, w, 58, 'var(--dg-mc-case)', { r: 4 })
      + R(x + 8, y + 8, w - 16, 28, 'var(--dg-pcb)', null, 2)
      + [0, 1, 2].map((j) => LN(`M${x + 13},${y + 15 + j * 8} H${x + w - 21 - j * 9}`, 'var(--dg-sig)', 1.4, ' class="blink' + (j ? ' b' + (j + 1) : '') + '"')).join('')
      + C(x + w - 18, y + 47, 7, 'var(--dg-steel-2)')
      + [0, 1, 2, 3].map((j) => R(x + 10 + j * 9, y + 43, 6, 6, 'var(--dg-mute)', null, 1)).join('')));
    g.push(part('mt_cnc', slab(x, y + 72, w, 50, 'var(--dg-mc-case)', { r: 4 })
      + R(x + 9, y + 82, w - 18, 20, 'var(--dg-pcb)', null, 2)
      + R(x + 26, y + 86, 24, 12, 'var(--dg-si)', null, 2)
      + [0, 1, 2, 3, 4].map((j) => C(x + 14 + j * 17, y + 112, 2.6, 'var(--dg-sw-gold)')).join('')));
    g.push(part('mt_drive', [0, 1, 2, 3].map((j) =>
      slab(x + 2 + j * 21, y + 136, 18, 84, j === 3 ? 'var(--dg-mc-cam)' : 'var(--dg-mc-case)', { r: 3 })
      + C(x + 11 + j * 21, y + 146, 2.6, 'var(--dg-pwr)', 'blink' + (j % 3 ? ' b' + ((j % 3) + 1) : ''))).join('')));
    return g.join('');
  }

  /* ---- 控制訊號：控制器 → 驅動器 → 三顆馬達（主鏈，往機器方向跑）；
     編碼器 → 控制器（回授，**方向相反**）。兩條平行走在立柱上，一眼看得出是一來一回。*/
  function wires() {
    const main = `M${CBX - 6},238 H504 V70 H${COLX - 22}`;
    const toSp = `M${CBX - 6},252 H466 V${HDY - 26} H${SPX + 20}`;
    const fb = `M${COLX - 9},96 H516 V264 H${CBX - 6}`;
    return part('mt_bus', fx.beam(main, { color: 'var(--dg-sig)', w: 2, flow: true, glow: false })
      + fx.beam(toSp, { color: 'var(--dg-sig)', w: 2, flow: true, glow: false }))
      + part('mt_fb', fx.beam(fb, { color: 'var(--dg-warn)', w: 2, flow: true, glow: false, cls: 'mtrev' }));
  }

  /* ---- 機體（鑄件）：床身 → 鞍座 → 工作台 → 工件；立柱在右。
     ★ 識別特徵：床身與立柱是**一體的鑄件**（所以底部是一個連續的 L 形），
        工作台上面一定有 **T 型槽**（工件靠它鎖上去）。*/
  function body() {
    const g = [];
    /* ★ 床身與立柱分成兩個 data-part（2026-09-23 第二輪）：3D 場景把它們當兩件，
       2D 只有一件的話，點 3D 的立柱在 2D 找不到對應。兩件仍然同色 ——
       它們在實機上通常是**一體的鑄件**，這一點寫在卡片與小卡上。*/
    g.push(part('mt_bed', PA(`M206,${BEDY} H${COLX + COLW} V${BEDY + BEDH} H198Z`, 'var(--dg-steel)', 'part')
      + LN(`M214,${BEDY + 14} H${COLX + 40}`, 'var(--dg-mute)', 1)));
    g.push(part('mt_col', PA(`M${COLX},${COLY} H${COLX + COLW} V${BEDY} H${COLX}Z`, 'var(--dg-steel)', 'part')
      + LN(`M${COLX + 14},${COLY + 16} V${BEDY - 14}`, 'var(--dg-mute)', 1)
      + LN(`M${COLX + 44},${COLY + 16} V${BEDY - 14}`, 'var(--dg-mute)', 1)));
    g.push(part('mt_saddle', slab(TBX0 - 10, SADY, TBW + 20, BEDY - SADY, 'var(--dg-mc-case)', { r: 2 })));
    const slots = [0, 1, 2].map((j) => R(TBX0 + 28 + j * 60, TBLY, 14, 6, 'var(--dg-frame-f)')).join('');
    g.push(part('mt_table', slab(TBX0, TBLY, TBW, SADY - TBLY - 2, 'var(--dg-alu)', { r: 2 }) + slots));
    g.push(part('mt_work', slab(SPX - 37, 274, 74, 26, 'var(--dg-mc-cam)', { r: 2 })
      + LN(`M${SPX - 30},282 H${SPX + 30}`, 'var(--dg-mute)', 1)));
    g.push(part('mt_guard', LN(`M210,104 V${BEDY - 4} M210,104 H${COLX - 4}`, 'var(--dg-frame-s)', 1.4, ' stroke-dasharray="7 5"')));
    g.push(part('mt_conv', PA(`M138,392 L206,356 L206,378 L138,414Z`, 'var(--dg-mc-case)', 'part')
      + [0, 1, 2, 3].map((j) => LN(`M${150 + j * 13},${394 - j * 7} l8,-4`, 'var(--dg-mute)', 1.4)).join('')));
    return g.join('');
  }

  /* 軸向標示：三個雙向箭頭 ＋ 字母，各自放在沒有零件的空檔。
     字是畫在 SVG 裡的（只有三個字母，縮放不影響可讀性），解釋一律在卡片上。*/
  function axisMarks() {
    return `<g class="mtax">`
      + LN(`M${TBX0 + 8},292 H${TBX0 + 96}`, 'var(--dg-accent-2d)', 1.6, ' marker-end="url(#mtAr)" marker-start="url(#mtAr)"')
      + T(TBX0 + 52, 286, 'X', 'lbl', 'middle', 'fill:var(--dg-accent-2d)')
      + LN('M330,148 V236', 'var(--dg-accent-2d)', 1.6, ' marker-end="url(#mtAr)" marker-start="url(#mtAr)"')
      + T(322, 196, 'Z', 'lbl', 'end', 'fill:var(--dg-accent-2d)')
      + LN('M258,352 l40,22', 'var(--dg-accent-2d)', 1.6, ' marker-end="url(#mtAr)" marker-start="url(#mtAr)"')
      /* ★ 2026-09-26 覆蓋普查：原本放在箭頭左上端（250,350），壓在鞍座與滑軌的邊上、又被 2 號編號蓋住 → 移到箭頭右下端、整個字落在床身正面上（1 號編號跟著右移，引線才不會橫劃過這個字）*/
      + T(304, 384, 'Y', 'lbl', null, 'fill:var(--dg-accent-2d)')
      + `</g>`;
  }

  /* ================================================================ ① 自製 vs 外購（預設收合）
     一台機器上，台廠自己做的與非買不可的各是哪幾件。每一列都是「零件｜誰做｜為什麼」。
     ★ 不寫任何百分比與金額（來源不足，見檔頭 §C／§D）。*/
  const BUY = [
    ['控制器（CNC）', 'buy', '幾乎全部外購', '高階機種皆搭配進口控制器（日本發那科、德國西門子、海德漢）。國產的新代、寶元在中階與多軸逐步推廣。它是成本占比最高的單一零組件之一。'],
    ['伺服驅動器與馬達', 'buy', '多隨控制器成套', '驅動器通常跟控制器同一家成套供應，換家等於整套控制架構要重調。'],
    ['高階主軸（含軸承）', 'buy', '高階多為外購', '轉速與剛性決定加工上限；高階品多為日、德、瑞士製，中低階有本土供應。'],
    ['滾珠螺桿・線性滑軌', 'mix', '★ 台廠自己就很強的一段', '這一段反而是台廠的強項（見「工業自動化」那張圖的單軸剖面）。整機廠向本土傳動件廠採購。'],
    ['刀庫與換刀機構', 'mix', '本土與外購都有', '機構件，本土專業廠與整機廠自製都有；把數與型式依機種而異。'],
    ['鑄件（床身、立柱）', 'own', '台廠自製為主', '重、運費高、又要時效 —— 在地供應本來就比較划算，也是中部聚落的底子。'],
    ['整機組裝與精度校正', 'own', '★ 台廠的主場', '組裝、刮花、幾何精度校正與試切 —— 整機廠的價值就在這裡。'],
  ];
  /* ★ 2026-09-26 覆蓋普查：每一列的說明原本一整句寫在一行（最長伸出畫布 234px）→ 照最壞字寬斷行，列高跟著行數長。
     第一行「零件｜外購／自製｜一句話」也拆開：一句話移到第二行開頭，不再跟標籤擠同一行。*/
  function foldBuy(y0) {
    const IN = 604 - 30;
    const P = BUY.map((r) => D.para(0, 0, r[3], IN, { lh: 17 }));
    const rh = P.map((q) => 64 + q.h - 17 + 8);                   // 標題列 ＋ 一句話 ＋ 說明（最少一行）＋ 列距
    const ry = []; let acc = y0 + 40; rh.forEach((hh) => { ry.push(acc); acc += hh; });
    const rowsH = acc - (y0 + 40);
    const h = 40 + rowsH + 64;
    const tag = { buy: '外購', mix: '混合', own: '自製' };
    const col = { buy: 'var(--dg-warn)', mix: 'var(--dg-accent-2d)', own: 'var(--dg-steel-2)' };
    const rows = BUY.map((r, i) => {
      const y = ry[i], hh = rh[i] - 8;
      return `<g data-part="mt_buy${i}">`
        + `<rect class="part frame" x="28" y="${y}" width="604" height="${hh}" rx="6"/>`
        + R(28, y, 5, hh, col[r[1]], null, 2)
        + T(46, y + 20, r[0], 'lbl')
        + R(228, y + 7, 46, 18, 'var(--dg-frame-f)', null, 4)
        + T(251, y + 21, tag[r[1]], 'sub', 'middle', `fill:${col[r[1]]}`)
        + T(46, y + 40, r[2], 'sub', null, `fill:${col[r[1]]}`)
        + D.para(46, y + 58, r[3], IN, { lh: 17 }).svg
        + `</g>`;
    }).join('');
    const tail = D.para(28, y0 + 40 + rowsH + 22, [{ t: '★ 這一段不寫任何成本占比、市占率與金額 —— 公開說法只有單一來源，寫上去就是把線索當成事實。' },
      { t: '★「混合」＝同一件零件在不同機種上，本土與進口都有；不是指同一台機器上兩者並用。' }], 604, { style: 'fill:var(--dg-warn)' });
    const svg = T(28, y0 + 22, '同一台機器上，台廠站在哪幾格', 'hd')
      + rows + tail.svg;
    return { h: 40 + rowsH + 22 + tail.h + 8, svg };
  }

  /* ================================================================ ② 加工中心機 vs 車床 ＋ 這一格四檔（預設收合）
     ★ 兩種機器的分界只有一句話：**誰在轉**。加工中心機是刀轉、工件夾著不動；
        車床是工件轉、刀不轉。畫兩個小圖把這件事講完就夠，不必畫兩台完整的機器。*/
  const CO = [
    ['4526 東台精機', '立／臥式加工中心機、立／臥式車床、複合加工、搪銑床、金屬積層製造設備、PCB 加工機、雷射加工機。機種最廣的一家。'],
    ['1583 程泰機械', '以電腦數值控制**車床**為主，台灣規模最大的 CNC 車床廠之一。'],
    ['1528 恩德科技', '金屬與**非金屬**電腦數控加工中心、PCB 電子機械、刀具與板材。非金屬加工是它跟另外兩家最明顯的差別。'],
    ['6603 富強鑫', '★ 做的是**塑膠射出成型機**（多色與單色），不是切削工具機 —— 它是把塑料射進模具，不切削金屬。族群名叫「CNC 工具機」，但這一檔不在這張圖畫的那種機器裡。'],
  ];
  function foldKinds(y0) {
    const cy = y0 + 116;   // ★ 2026-09-26：原本 96，主軸頂端頂到格標題「…刀在轉」的尾巴 → 兩格的圖一起往下 20
    /* ★ 2026-09-26 覆蓋普查：兩格底下那一句與四檔的說明原本各是一整行（伸出格子 7～313px）→ 照最壞字寬斷行、格高跟著長 */
    const CIN = 296 - 28, RIN = 604 - 30;
    const cmpM = D.para(0, 0, '刀具裝在主軸上旋轉，工作台帶著工件沿 X／Y 走位', CIN, { lh: 17 });
    const cmpL = D.para(0, 0, '工件夾在主軸上旋轉，刀具沿工件的軸向與徑向進給', CIN, { lh: 17 });
    const CH2 = 168 + Math.max(cmpM.h, cmpL.h) - 17;
    const CP = CO.map((r) => D.para(0, 0, r[1].replace(/\*\*/g, ''), RIN, { lh: 17 }));
    const rH = CP.map((q) => 40 + q.h - 17 + 6);
    const rY = []; let acc = y0 + 86 + CH2 + 10; rH.forEach((hh) => { rY.push(acc); acc += hh; });
    const endN = D.para(0, 0, '★ 族群名不等於產品事實：6603 富強鑫在「CNC 工具機」族群裡，做的卻是射出成型機。照抄族群名就會畫錯一整張圖。', 604);
    const h = acc - y0 + 22 + endN.h + 8;
    // 左：加工中心機（刀轉、工件不動）｜右：車床（工件轉、刀不動）
    /* ⚠ 兩格都**不可以用 rotate 把長方形轉起來**（正視圖裡那是歪掉的棒子，不是在轉）：
       銑削那格用「刀刃上會往下跑的斜虛線 ＋ 鼻端的透視圓環」表示刀在轉；
       車床那格用「夾頭是正面的圓、繞中心轉」表示工件在轉 —— 圓轉起來才是對的。*/
    const mring = `M226,${cy - 22} a14,5 0 1,0 28,0 a14,5 0 1,0 -28,0`;
    const mc = `<g data-part="mt_cmp_mill">`
      + `<rect class="part frame" x="28" y="${y0 + 40}" width="296" height="${CH2}" rx="7"/>`
      + T(42, y0 + 62, '綜合加工機（銑削）：刀在轉', 'lbl')
      + R(186, cy + 4, 108, 26, 'var(--dg-mc-cam)', null, 2)
      + T(240, cy + 46, '工件（夾著不動）', 'sub', 'middle')
      + R(228, cy - 46, 24, 8, 'var(--dg-steel-2)', null, 2)
      + PA(`M230,${cy - 38} L250,${cy - 38} L247,${cy - 22} L233,${cy - 22}Z`, 'var(--dg-mute)')
      + PA(`M235,${cy - 22} L245,${cy - 22} L244,${cy + 6} L236,${cy + 6}Z`, 'var(--dg-mc-cam)')
      + LN(`M236,${cy - 18} L244,${cy - 10}`, 'var(--dg-steel)', 1.4, ' class="flow fast"')
      + LN(`M236,${cy - 8} L244,${cy}`, 'var(--dg-steel)', 1.4, ' class="flow fast"')
      + LN(mring, 'var(--dg-accent-2d)', 1.2, ' opacity=".7"')
      + `<circle r="2.8" fill="var(--dg-flow-dot)"><animateMotion dur="1.1s" repeatCount="indefinite" path="${mring}"/></circle>`
      + D.para(42, y0 + 196, '刀具裝在主軸上旋轉，工作台帶著工件沿 X／Y 走位', CIN, { lh: 17 }).svg
      + `</g>`;
    const jaw = [0, 1, 2].map((j) => `<g transform="rotate(${j * 120})">`
      + R(-5, -24, 10, 12, 'var(--dg-steel-2)', null, 2) + '</g>').join('');
    const lt = `<g data-part="mt_cmp_lathe">`
      + `<rect class="part frame" x="336" y="${y0 + 40}" width="296" height="${CH2}" rx="7"/>`
      + T(350, y0 + 62, '車床：工件在轉', 'lbl')
      + R(350, cy - 30, 30, 60, 'var(--dg-mc-case)', null, 3)
      + `<g transform="translate(396,${cy})"><g class="spin mtmid">`
      + C(0, 0, 26, 'var(--dg-mc-disc)') + C(0, 0, 9, 'var(--dg-frame-f)') + jaw
      + `</g></g>`
      + T(350, y0 + 82, '夾頭（正面：在轉）', 'sub')   /* ★ 原本在夾頭正下方置中，左端伸出格子 → 移到夾頭上方、靠左對齊 */
      + R(422, cy - 13, 106, 26, 'var(--dg-mc-cam)', null, 2)
      + [0, 1, 2, 3, 4].map((j) => LN(`M${430 + j * 20},${cy - 13} l10,26`, 'var(--dg-mute)', 1.2, ' class="flow"')).join('')
      + PA(`M478,${cy + 22} L492,${cy + 38} L464,${cy + 38}Z`, 'var(--dg-steel-2)')
      + T(478, cy + 58, '刀（不轉，沿軸走）', 'sub', 'middle')   /* ★ 原本從 x 500 起筆，右端伸出格子 → 移到刀的正下方置中 */
      + D.para(350, y0 + 196, '工件夾在主軸上旋轉，刀具沿工件的軸向與徑向進給', CIN, { lh: 17 }).svg
      + `</g>`;
    const rows = CO.map((r, i) => {
      const y = rY[i], hh = rH[i] - 6;
      return `<g data-part="mt_co${i}">`
        + `<rect class="part frame" x="28" y="${y}" width="604" height="${hh}" rx="6"/>`
        + R(28, y, 5, hh, i === 3 ? 'var(--dg-warn)' : 'var(--dg-steel-2)', null, 2)
        + T(46, y + 17, r[0], 'lbl')
        + D.para(46, y + 34, r[1].replace(/\*\*/g, ''), RIN, { lh: 17 }).svg
        + `</g>`;
    }).join('');
    const svg = T(28, y0 + 22, '兩種機器的分界只有一句話：誰在轉', 'hd')
      + mc + lt
      + T(28, y0 + 64 + CH2, '這一格（CNC 工具機族群）的四檔各自做什麼', 'hd')
      + rows
      + D.para(28, acc + 22, '★ 族群名不等於產品事實：6603 富強鑫在「CNC 工具機」族群裡，做的卻是射出成型機。照抄族群名就會畫錯一整張圖。', 604, { style: 'fill:var(--dg-warn)' }).svg;
    return { h, svg };
  }

  /* ================================================================ 主圖 */
  function machineTool() {
    /* ★ 2026-09-26 覆蓋普查：§1 的標題與誠實性副標各是一整行，在 660 寬裡伸出框 22～43px（閱讀模式更多）。
       兩行各拆成兩行 —— 多出來的 40px 由整台機器（連同錨點）一起往下平移 DY1，機器本身的相對位置一筆都沒動。*/
    const DY1 = 40;
    const S1 = 448 + DY1;
    const w1 = foldBuy(S1 + 46);
    const S2 = S1 + 46 + w1.h;
    const w2 = foldKinds(S2 + 46);
    const H = S2 + 46 + w2.h + 16;
    return `<svg class="dg dgm rs dgmt" viewBox="0 0 ${CW} ${H}" width="100%" style="display:block">${D.STYLE}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}
        <marker id="mtAr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9Z" fill="var(--dg-accent-2d)"/></marker>
      </defs>
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（DECISIONS #231）——
           在 SVG 裡它是被當標記解析的，寫一個像標籤的東西進去會把整張樣式表吃掉。
           這張圖一個環節屬性都沒有，所以 diagrams.js 依環節屬性寫的規則一條都吃不到：
           描邊、游標、被點到的高亮全部要在這裡自己給。顏色一律走 --dg-*，沒有寫死色票。
           發光只給被點的那一個（Andy：要精密儀器不是電競 RGB）。*/
        svg.dgmt [data-part]{cursor:pointer}
        svg.dgmt [data-part] .part{stroke:var(--dg-part-mix);stroke-width:.9;
          transition:stroke .15s,filter .15s}
        svg.dgmt [data-part]:hover .part{stroke:var(--dg-accent-2d);stroke-width:1.6}
        svg.dgmt [data-part].sel-part .part{stroke:var(--dg-accent-2d);stroke-width:2.6;
          filter:var(--dg-glow,drop-shadow(0 0 5px var(--dg-accent-2d)))}
        svg.dgmt .mtring{stroke:var(--dg-frame-s);stroke-width:1.2}
        svg.dgmt .mtbuy{fill:none;stroke:var(--dg-warn);stroke-width:1.4;stroke-dasharray:6 5;opacity:.75}
        /* 轉速分三階：主軸最快、刀庫最慢、換刀臂居中。都是等速旋轉，不是閃爍。*/
        svg.dgmt .spin.mtfast{animation-duration:1.1s}
        svg.dgmt .spin.mtmid{animation-duration:3.4s}
        svg.dgmt .spin.mtslow{animation-duration:9s}
        svg.dgmt .mtrev .fxb-flow{animation-direction:reverse}
      </style>
      <!-- 標題與導言：搬到 HTML 的 .dghead，SVG 裡不畫（字才不會跟著畫布縮小） -->
      <text class="ttl ext" x="0" y="0">CNC 工具機：一台立式綜合加工機拆開看</text>
      <text class="cap ext" x="0" y="0">綜合加工機是台廠金屬切削工具機的出口第一大機種。這張圖把一台立式綜合加工機攤開：左邊是刀庫與換刀機械手，中間是床身 → 鞍座 → 工作台 → 工件，以及從立柱伸出來的主軸頭 → 主軸 → 刀柄，右邊是外購的控制器櫃。三根軸（X 工作台、Y 鞍座、Z 主軸頭）各自是一組伺服馬達加滾珠螺桿加線性滑軌 —— 那一根軸拆開的樣子在「工業自動化」那張圖。虛線框起來的那一格是外購的，點卡片零件會亮、點零件卡片會亮；下面兩段預設收起來，按標題列就打得開。</text>

      <!-- ================= §1 整機（永遠看得到） ================= -->
      ${frame(16, 16, 628, 416 + DY1)}
      ${T(28, 40, '① 一台立式綜合加工機：刀庫 → 換刀機械手 → 主軸 ｜', 'hd')}
      ${T(28, 60, '床身 → 鞍座 → 工作台 ｜ 控制器櫃（外購）', 'hd')}
      ${T(28, 80, '示意圖，非實物比例；刀庫把數、主軸轉速、精度等級一律不標', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(28, 98, '（那些是某一機種的型錄數字，不是通例）', 'sub', null, 'fill:var(--dg-warn)')}
      <g transform="translate(0,${DY1})">
      ${body()}
      ${axes()}
      ${magazine()}
      ${atc()}
      ${spindle()}
      ${cutting()}
      ${cabinet()}
      ${wires()}
      ${axisMarks()}
      ${T(MAGX, 246, '刀庫（圓盤式）', 'sub', 'middle')}
      ${T(128, 352, '換刀機械手（雙臂）', 'sub', 'middle')}   <!-- ★ 原本置中在 150，右端壓到床身斜邊 -->
      ${T(CBX + CBW / 2, 336, '控制器櫃：', 'sub', 'middle', 'fill:var(--dg-warn)')}
      ${T(CBX + CBW / 2, 354, '整櫃外購', 'sub', 'middle', 'fill:var(--dg-warn)')}   <!-- ★ 原本一行，左端壓進立柱、右端伸出畫布 -->
      ${T(104, 386, '排屑機', 'sub', 'middle')}

      <!-- ================= 說明卡片（HTML）：左欄機體與換刀、右欄主軸與控制 ================= -->
      ${card({ side: 'l', no: 1, part: 'mt_bed', color: COL.iron, ax: 332, ay: 366, title: '床身（鑄件）', sub: ['整台機器的地基：所有切削力最後都由它承受', '★ 重、運費高、又要時效 —— 這是台廠自己做的一段'] })}
      ${card({ side: 'l', no: 20, part: 'mt_col', color: COL.iron, ax: 516, ay: 320, title: '立柱（鑄件，與床身一體）', sub: ['主軸頭掛在它正面的兩條滑軌上', '★ 它跟床身通常是一體的鑄件 —— 分成兩塊，剛性就不是一體的了'] })}
      ${card({ side: 'l', no: 2, part: 'mt_saddle', color: COL.case, ax: 250, ay: 332, title: '鞍座（Y 軸滑座）', sub: '夾在床身與工作台之間，帶著工作台往畫面裡外走' })}
      ${card({ side: 'l', no: 3, part: 'mt_table', color: COL.alu, ax: 268, ay: 310, title: '工作台（X 軸）', sub: ['上面那幾道是 T 型槽 —— 工件與虎鉗靠它鎖上去', '沒有 T 型槽的平板不是工作台'] })}
      ${card({ side: 'l', no: 4, part: 'mt_work', color: COL.steel, ax: 400, ay: 294, title: '工件（被加工的那一塊）', sub: '★ 綜合加工機是「刀轉、工件不動」；車床剛好相反（見下面第 ② 段）' })}
      ${card({ side: 'l', no: 5, part: 'mt_mag', color: COL.disc, ax: 92, ay: 176, title: '刀庫（圓盤式）', sub: ['一圈刀套繞著圓盤排列，轉位找到要的那一把', '★ 把數依機種而異，圖上畫 10 個是示意'] })}
      ${card({ side: 'l', no: 6, part: 'mt_atc', color: COL.steel, ax: 186, ay: 268, title: '換刀機械手（雙臂式 ATC）', sub: ['★ 兩端對稱：一端抓主軸上的舊刀、一端抓刀庫的新刀', '轉半圈就同時換完 —— 單臂畫法解釋不了「一次換兩把」'] })}
      ${card({ side: 'l', no: 7, part: 'mt_conv', color: COL.chip, ax: 172, ay: 374, title: '排屑機', sub: '把切屑從加工區運出去。切屑堆在機內會頂到工件、也會把熱悶在裡面' })}
      ${card({ side: 'r', no: 8, part: 'mt_head', color: COL.case, ax: 360, ay: 178, title: '主軸頭（Z 軸）', sub: '掛在立柱的線性滑軌上，沿立柱上下 —— 它是整台機器上最重的一個移動件' })}
      ${card({ side: 'r', no: 9, part: 'mt_spmot', color: COL.case, ax: 400, ay: 135, title: '主軸馬達', sub: '驅動主軸旋轉。高階機種會把馬達直接做進主軸裡（內藏式），圖上畫的是皮帶／直結那一類的外掛式' })}
      ${card({ side: 'r', no: 10, part: 'mt_spindle', color: COL.steel, ax: 400, ay: 228, title: '主軸（錐孔朝下）', sub: ['轉速與剛性決定這台機器的加工上限', '★ 高階主軸多為外購（日、德、瑞士）'] })}
      ${card({ side: 'r', no: 11, part: 'mt_bear', color: COL.steel, ax: 414, ay: 180, title: '主軸軸承（前後兩組）', sub: '夾住主軸的那兩圈滾珠。它決定主軸能轉多快、能吃多大的力' })}
      ${card({ side: 'r', no: 12, part: 'mt_tool', color: COL.steel, ax: 400, ay: 260, title: '刀柄與刀具', sub: ['★ 刀柄是錐形的：靠錐面定位，不是靠螺絲鎖', '換刀機械手抓的就是刀柄中段那一圈溝'] })}
      ${card({ side: 'r', no: 13, part: 'mt_coolant', color: COL.cool, ax: 356, ay: 256, title: '切削液噴嘴', sub: '降溫、潤滑、把切屑沖走。三件事少一件，刀具壽命就掉一截' })}
      ${card({ side: 'r', no: 14, part: 'mt_z', color: COL.steel, ax: 477, ay: 200, title: 'Z 軸：伺服馬達＋滾珠螺桿', sub: ['三根軸的構造完全一樣，只是裝的方向不同', '★ 這一段拆開的樣子在「工業自動化」那張圖'] })}
      ${card({ side: 'r', no: 15, part: 'mt_rail', color: COL.iron, ax: 489, ay: 240, title: '線性滑軌（軌道）', sub: '★ 台廠自己就很強的一段：滾珠螺桿與線性滑軌是本土傳動件廠的主場' })}
      ${card({ side: 'r', no: 16, part: 'mt_cnc', color: COL.warn, ax: 595, ay: 176, title: '★ CNC 控制器（整櫃外購）', sub: ['台灣的高階機種皆搭配進口控制器（日本發那科、德國西門子、海德漢）', '國產的新代、寶元在中階與多軸逐步推廣'] })}
      ${card({ side: 'r', no: 17, part: 'mt_drive', color: COL.warn, ax: 595, ay: 258, title: '伺服驅動器 ×3 ＋ 主軸驅動器', sub: '通常跟控制器同一家成套供應 —— 換一家等於整套控制架構要重調' })}
      ${card({ side: 'r', no: 18, part: 'mt_panel', color: COL.sig, ax: 595, ay: 108, title: '操作面板（人機介面）', sub: '畫面、手輪與按鍵。操作者看到的整台機器都是它的樣子，所以控制器的品牌很難換' })}
      ${card({ side: 'r', no: 19, part: 'mt_fb', color: COL.warn, ax: 516, ay: 180, title: '位置回授（方向相反的那一條）', sub: ['★ 有這條線才叫數值控制：控制器 → 驅動器 → 馬達 → 進給 → 回授 → 控制器', '環不閉的話它只是一台會動的機器'] })}
      ${note({ side: 'l', order: 96, title: '這張圖要講的四件事',
        lines: ['① 一台加工機＝鑄件（床身、立柱）＋ 三根進給軸 ＋ 主軸 ＋ 刀庫與換刀 ＋ 控制器。',
          '② 三根軸的構造一模一樣：伺服馬達 ＋ 滾珠螺桿 ＋ 線性滑軌，只是裝的方向不同。',
          '③ 台廠做得了整機（鑄件、組裝、精度校正），但控制器幾乎全部外購、高階主軸也多為進口。',
          '④ 反過來，滾珠螺桿與線性滑軌是台廠自己就很強的一段 —— 同一台機器上，兩種位置都有。'] })}
      ${note({ side: 'l', warn: true, order: 97, title: '★ 這張圖跟「工業自動化」那張怎麼分',
        lines: ['那張畫的是**一根軸拆開**（螺桿、螺帽、鋼珠、回流通道、滑塊、減速機、控制鏈）。',
          '這張畫的是**用那些軸組成的整台機器**。兩個族群不是同一件事，所以不合併成一張。',
          '要看螺帽裡面的鋼珠怎麼循環，去看「工業自動化」那張的第 ① 區。'] })}
      ${note({ side: 'r', warn: true, order: 98, title: '這張圖沒有回答的事',
        lines: ['示意圖，非實物比例；各零件的相對尺寸為誇張放大。',
          '不寫任何刀庫把數、主軸轉速、精度等級、成本占比、市占率與金額 —— 公開來源不足或只有單一出處。',
          '「CNC 工具機」目前不在供應鏈資料的環節裡，所以下方的「環節色標」篩不到它；公司對應寫在卡片、零件小卡與下面第 ② 段。',
          '★ 6603 富強鑫做的是射出成型機，不是切削工具機 —— 它不在這張圖畫的那種機器裡。'] })}

      </g>
      <!-- ================= ① 自製 vs 外購（預設收合） ================= -->
      ${D.foldBar('mt1', S1, '① 同一台機器上，台廠站在哪幾格',
    '七件零件逐條：哪些非買不可、哪些是台廠的主場、哪些兩者都有')}
      <g class="dgbody" data-fold="mt1" data-y0="${S1 + 46}" data-y1="${S1 + 46 + w1.h}">
        ${w1.svg}
      </g>

      <!-- ================= ② 加工中心機 vs 車床 ＋ 這一格四檔（預設收合） ================= -->
      ${D.foldBar('mt2', S2, '② 加工中心機與車床差在哪 ＋ 這一格四檔各自做什麼',
    '「誰在轉」一句話講完，以及 4526／1583／1528／6603 逐家對應')}
      <g class="dgbody" data-fold="mt2" data-y0="${S2 + 46}" data-y1="${S2 + 46 + w2.h}">
        ${w2.svg}
      </g>
    </svg>`;
  }

  /* `parts` ＝點這個零件時「誰做的」小卡要顯示什麼。
     ★ 這張圖一個環節屬性都沒有，所以 `cos` 一律留空 —— 這四檔一檔都不在
       `supply_chain.yaml` 裡，寫進 `cos` 只會被 filter 靜靜丟掉，
       得到一張「少了人卻沒有任何提示」的卡片。公司一律寫進 `none:` 的整句話。*/
  const PARTS = {
    mt_bed: { name: '床身（鑄件）', desc: '整台機器的地基：主軸切下去的力、工作台移動的慣性，最後都由它承受。★ 床身與立柱通常是一體的鑄件，底部是一個連續的 L 形；本圖分成兩個可點的零件只是為了跟 3D 對得上，兩件同色就是在講「它們是同一塊」。鑄件重、運費高、又要時效，所以在地供應本來就比較划算 —— 這是台中工具機聚落的底子。',
      none: '整機與鑄件在台股：4526 東台精機、1583 程泰機械、1528 恩德科技（三家都是整機廠，鑄件的供應分工查不到具名來源，不編）。★ 這一格不在 supply_chain.yaml 的環節裡，所以「做這個的台股」欄列不出它們 —— 這裡用文字補。' },
    mt_col: { name: '立柱（鑄件，與床身一體）', desc: '站在床身後緣的方柱，正面是兩條線性滑軌的貼合面與一排鎖付孔 —— 主軸頭就掛在那兩條軌道上。★ 它跟床身通常是一體的鑄件：分成兩塊各自站著，剛性就不是一體的了。它的高度與斷面直接決定這台機器能吃多深的刀。' },
    mt_saddle: { name: '鞍座（Y 軸滑座）', desc: '夾在床身與工作台之間的那一層，帶著工作台往畫面的裡外走。三根軸就是這樣疊起來的：床身不動 → 鞍座走 Y → 工作台走 X → 主軸頭走 Z。' },
    mt_table: { name: '工作台（X 軸）', desc: '★ 上面那幾道是 T 型槽：工件、虎鉗與夾治具靠它鎖上去。沒有 T 型槽的平板不是工作台。工作台沿 X 走位，走的距離就是這台機器的 X 行程。' },
    mt_work: { name: '工件（被加工的那一塊）', desc: '★ 綜合加工機是「刀轉、工件夾著不動」。這一點是它跟車床唯一的分界 —— 車床是工件轉、刀不轉（見下面第 ② 段的對照）。' },
    mt_mag: { name: '刀庫（圓盤式）', desc: '一圈刀套繞著圓盤排列，圓盤轉位把要的那一把轉到換刀位置。★ 它的識別特徵是「刀套排成一圈」與「每個刀套裡是上粗下尖的錐柄」—— 畫成一排方塊就不是刀庫。把數依機種而異（有的標配數十把、可擴充到上百把），本圖畫 10 個是示意，不代表任何機種的規格。',
      none: '刀庫與換刀機構的台股供應分工查不到具名來源 —— 查不到就寫查不到，不編一個對應。整機廠自製與向專業機構件廠採購兩種都有。' },
    mt_magmot: { name: '刀庫驅動馬達', desc: '讓刀庫轉位的那一顆。轉位速度直接吃掉換刀時間，所以它不是隨便一顆馬達。' },
    mt_atc: { name: '換刀機械手（雙臂式 ATC）', desc: '★ 兩端對稱是它的識別特徵：一端抓主軸上的舊刀、另一端抓刀庫裡的新刀，轉半圈就同時完成交換。單臂的畫法解釋不了「為什麼一次可以換兩把」，也解釋不了換刀為什麼可以那麼快。爪子抓的是刀柄中段那一圈溝。' },
    mt_head: { name: '主軸頭（Z 軸）', desc: '掛在立柱的線性滑軌上，沿立柱上下。它是整台機器上最重的一個移動件，所以它的重量與剛性同時決定了加工精度與加減速能力。' },
    mt_spmot: { name: '主軸馬達', desc: '驅動主軸旋轉。圖上畫的是外掛式（皮帶或直結）；高階機種會把馬達直接做進主軸裡（內藏式主軸），那種在外觀上看不到這一顆。★ 哪一種機型用哪一種查不到可引用的通例，所以本圖只畫一種並標示「示意」。' },
    mt_spindle: { name: '主軸（錐孔朝下）', desc: '夾著刀柄旋轉的那根空心軸，下端是一個錐孔。★ 它的轉速與剛性決定這台機器的加工上限。高階主軸多為外購（日、德、瑞士），中低階有本土供應 —— 這是「台廠做得了整機、關鍵件還是要買」的第二個例子。',
      none: '主軸這一件，本圖查不到台股的具名對應（高階品多為進口）—— 查不到就寫查不到，不編一個對應。' },
    mt_bear: { name: '主軸軸承（前後兩組）', desc: '夾住主軸的那兩圈滾珠。它決定主軸能轉多快、能吃多大的切削力，也是主軸壽命的瓶頸。圖上剖開看得到內環、外環與夾在中間的一圈滾珠。' },
    mt_tool: { name: '刀柄與刀具', desc: '★ 刀柄是錐形的：靠錐面與主軸錐孔的貼合定位，不是靠螺絲鎖 —— 錐面才有辦法在幾秒內重複裝拆又不失精度。中段那一圈溝是給換刀機械手抓的。刀具本身（銑刀、鑽頭）是消耗品，跟機器是兩個產業。',
      none: '刀具在台股：1528 恩德科技的營業項目含刀具。★ 這一檔不在 supply_chain.yaml 的環節裡，所以這張小卡的「做這個的台股」欄列不出它 —— 這裡用文字補。' },
    mt_coolant: { name: '切削液噴嘴', desc: '降溫、潤滑、把切屑沖走 —— 三件事少一件刀具壽命就掉一截。高階機種會把切削液從主軸中心打出去（中心出水），本圖畫的是外部噴嘴。' },
    mt_chip: { name: '切屑', desc: '切下來的金屬屑。它是「這台機器真的在加工」的證據，也是排屑機存在的理由：切屑堆在機內會頂到工件、也會把熱悶在加工區裡。' },
    mt_conv: { name: '排屑機', desc: '斜著把切屑從加工區運出去、倒進屑車。它不影響精度，但它決定這台機器能不能連續跑而不用有人去清。' },
    mt_guard: { name: '防護鈑金（虛線）', desc: '把加工區圍起來，擋住飛出來的切屑與切削液。畫成虛線是因為這張圖要看得到裡面 —— 實機上它是不透明的鈑金加一片觀察窗。' },
    mt_x: { name: 'X 軸：伺服馬達 ＋ 滾珠螺桿', desc: '工作台左右走的那一根。螺桿上的斜線是螺紋的示意。★ 三根軸的構造完全一樣，只是裝的方向不同 —— 一根軸拆開的樣子（螺帽、鋼珠、回流通道、滑塊）在「工業自動化」那張圖。',
      none: '滾珠螺桿與線性滑軌在台股：2049 上銀、4540 全球傳動、1597 直得；伺服馬達 4576 大銀微系統。★ 這幾檔屬於「工業自動化」族群，不在這一格，也都不在 supply_chain.yaml 的環節裡。' },
    mt_y: { name: 'Y 軸：鞍座的進給', desc: '帶著工作台往畫面的裡外走。圖上畫成一條斜線，因為在正視圖裡它的方向是朝向觀看者的。' },
    mt_z: { name: 'Z 軸：立柱上的進給', desc: '主軸頭上下的那一根。★ 它是三根軸裡唯一要對抗重力的 —— 所以通常還有配重或煞車，停電時主軸頭不會自己掉下來。本圖不畫配重（各家做法不同，查不到通例）。' },
    mt_rail: { name: '線性滑軌（軌道）', desc: '立柱上兩條、床身上兩條。滑軌不出力，只負責「別歪掉」與承重；出力的是旁邊的螺桿。★ 這一段是台廠自己就很強的一段。',
      none: '線性滑軌在台股：2049 上銀、1597 直得。★ 兩檔屬於「工業自動化」族群，不在這一格，也不在 supply_chain.yaml 裡。' },
    mt_cnc: { name: '★ CNC 控制器（整櫃外購）', desc: '這張圖的重點零件：它讀程式、算路徑、把每一軸每一毫秒該走到哪算出來。★ 台灣生產的高階工具機皆搭配進口 CNC 控制器（日本發那科 FANUC、德國西門子 SIEMENS、海德漢 HEIDENHAIN）；國產的新代 Syntec、寶元數控 LNC 在中階與多軸工具機逐步推廣。它是整台機器上成本占比最高的單一零組件之一（公開的占比數字只有單一來源，所以本圖不寫數字）。',
      none: '控制器在台股：7750 新代科技（興櫃／非本族群成分）。★ 這張圖畫的整機廠四檔都不做控制器；控制器這一格不在 supply_chain.yaml 的環節裡，也不在「CNC 工具機」族群裡 —— 這裡用文字補。' },
    mt_drive: { name: '伺服驅動器 ×3 ＋ 主軸驅動器', desc: '控制器算出來的指令由它們變成馬達的電流。★ 通常跟控制器同一家成套供應 —— 這就是為什麼換控制器品牌這麼難：換的不是一個盒子，是整套控制架構與所有調機參數。' },
    mt_panel: { name: '操作面板（人機介面）', desc: '畫面、手輪與按鍵。操作者對「這台機器」的全部印象其實來自它 —— 廠裡的師傅熟的是某一家控制器的操作邏輯，所以整機廠很難換品牌。' },
    mt_bus: { name: '控制匯流排（控制器 → 驅動器 → 馬達）', desc: '指令往外走的那一條。圖上的流動點是往機器方向跑的。' },
    mt_fb: { name: '位置回授（方向相反的那一條）', desc: '★ 有這條線才叫數值控制：控制器 → 驅動器 → 馬達 → 進給機構 → 位置回授 → 控制器，這個環必須是閉的。只畫單向的指令線等於畫成了開迴路，那是普通的自動機器，不是 CNC。' },
    mt_cmp_mill: { name: '綜合加工機（銑削）：刀在轉', desc: '刀具裝在主軸上旋轉，工件夾在工作台上不動，由工作台沿 X／Y 走位、主軸頭沿 Z 進刀。' },
    mt_cmp_lathe: { name: '車床：工件在轉', desc: '工件夾在主軸上旋轉，刀具不轉、沿著工件的軸向與徑向進給。★ 這是兩種機器唯一的分界 —— 誰在轉。',
      none: 'CNC 車床在台股：1583 程泰機械（台灣規模最大的 CNC 車床廠之一）、4526 東台精機（車床也做）。兩檔都不在 supply_chain.yaml 裡。' },
  };
  // ① 自製 vs 外購那七列，每一列各給一張小卡
  BUY.forEach((r, i) => {
    PARTS['mt_buy' + i] = { name: r[0] + '：' + r[2], desc: r[3],
      none: '這一列的公司全部不在 supply_chain.yaml 的環節裡，所以「做這個的台股」欄列不出它們 —— 對應寫在這裡與各零件的小卡。' };
  });
  // ② 四檔逐家
  CO.forEach((r, i) => {
    PARTS['mt_co' + i] = { name: r[0], desc: r[1].replace(/\*\*/g, ''),
      none: '★ 這四檔都不在 supply_chain.yaml 的環節裡（electronics 鏈沒有工具機環節），所以「做這個的台股」欄列不出它們 —— 對應寫在這裡。' };
  });

  window.DG.register('machine_tool', {
    level: 'group', chain: 'electronics',
    name: 'CNC 工具機：一台立式綜合加工機拆開看',
    draw: machineTool, native: CW, scene: 'machine_tool',
    q: '一台加工機由哪些部分組成？台廠做得了整機，為什麼關鍵件還是要外購？',
    parts: PARTS,
  });
})();
