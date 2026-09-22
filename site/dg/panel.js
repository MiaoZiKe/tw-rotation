/* 面板疊層 —— docs/diagram_plan.md 的第 7 張（族群 `panel`、electronics 鏈）
   規格書：docs/diagram_specs/panel_stack.md（2026-09-20 由 mechanical-engineer 簽過）

   ================================================================ 這張圖回答什麼
   「一片面板從背光到蓋板疊了哪幾層、每一層在幹嘛」，以及三件最容易被畫錯的事：
     ① 為什麼要**兩片**偏光板（少一片就關不掉）
     ② 顏色是上玻璃的色阻**濾**出來的，不是背光給的；R／G／B **水平並排**不是疊三層
     ③ 換成 OLED 會少掉哪幾層（自發光 → 不需要背光模組，也不需要液晶層）
   最後把「面板產業」族群 9 檔各自放回它站的那一格。

   ================================================================ 為什麼不做真 3D（scene: null）
   規格書〈型式〉已經寫死，這裡照抄理由並複核過：
   這張圖的資訊**全部在剖面的層序裡**。一疊薄膜轉一圈只會看到一塊不透明的平板，
   多轉那一圈不解釋任何一件事（dg3d_standard §「預設 2D／2.5D」的判準）。
   所以走 2.5D 等角，用「階梯式剖切」讓 13 層同時看得見。

   ================================================================ 立體語言（怎麼讀這張等角圖）
   投影沿用 window.DG 的等角工具（x 往右下、y 往左下、z 往上）。
   · **右側那面牆 ＝ 剖面**（x = 每一層自己的右緣）：層序、材質、網點、稜線、
     偏光紋理、液晶短棒、R／G／B 色阻都畫在這裡。右邊的引線就接在這面牆上。
   · **左前方的階梯 ＝ 每一層露出來的一條帶**：往左前方退一階，才看得到下面那一層。
     每一層露出來的那一條帶上畫它的「表面長相」（稜鏡的稜線、TFT 的格柵、色阻的 RGB）。
   · 兩者合起來就是「一疊薄膜」這件事 —— 這是規格書 §4 要求的第一個識別特徵。

   ================================================================ 和規格書不一致的地方（都寫在回報裡）
   規格書是 2026-09-20 寫的，比 MLCC 那張早，有幾條已經被後來的標準蓋掉：
   1. **§0 整節（掛載點）作廢**。當時沒有 slot 機制，所以花了很長一節在討論
      「要新開題材、還是用掉 electronics 鏈唯一的一張圖」。2026-09-21 之後
      `window.DG.register` 支援 `level:'group'`，一條鏈可以掛好幾張族群層級的圖，
      這張直接註冊成 `panel` 族群的圖即可，不需要動任何 YAML。
   2. **§7 的 CW = 1180 → 改成 980 ＋ `native: 980`**（DECISIONS #227）。
      欄寬才是「文字太小」的根因，畫布加寬只會在 1440 螢幕上生出水平捲軸。
   3. **字級下限 12px**（規格書沒訂）：--dg-fs-ttl 16 / hd 13.5 / lbl 12.5 / min 12。
   4. **§6-D1 建議右半掛 `data-seg="adv_pkg"` —— 不能照做。**
      `adv_pkg` 的 chain 是 `semiconductor`（supply_chain.yaml:58），
      掛在 electronics 的頁面上就是 MLCC 踩過的那個坑：
      下方成分股被篩了、上面的環節色標卻沒有一格亮。
      這張圖只用 electronics 鏈上真的有的環節：`panel_mfg`、`display_material`。
      （`ic_design` 也在這條鏈上，但實測掛上去之後驅動 IC 在**預設狀態**就是 opacity 0.3
       —— 因為 panel 族群裡沒有任何一檔驅動 IC 廠。理由與取捨寫在 driver 那一段的註解。）
   5. **§6-D2／D3（`.scode` 晶片、`wireThemeDiagram`）不適用** —— 那是題材圖的機制。
      產業鏈剖析圖的顏色走 `industry.js` 的 `paintDiagram()`（直接 `segColor(data-seg)`），
      所以「同一個 seg 出現在多個零件上」是正常的（MLCC 用了 14 次），不會掉進 PALETTE。
      台股代號一律寫成畫面下方的說明文字，不做可點的晶片 —— 康寧的 ticker 是
      `NYSE:GLW`，做成晶片按下去會導到不存在的路由（這一條規格書 §5-C 是對的，照辦）。
   6. **§5-E 的成分股覆蓋表只列 3 檔**（2409／3481／6116），但 `groups.yaml:495` 的
      `panel` 族群實際有 9 檔，多出來的 6 檔剛好補滿這條鏈的其他格（背光模組、偏光板、
      後段模組、電子紙）。所以覆蓋表擴充到 9 檔，每一檔都寫它**查得到的**業務定位。
   7. 規格書把右半整個給了「面板廠轉先進封裝（FOPLP／GCS）」。那條線證據充分、
      也確實是 2026 年這一格的資金故事，但它是**另一個題材的結構**（先進封裝），
      而 diagram_plan 第 4 張 `ai_adv_packaging` 就是畫那個的。
      在 980 寬的畫布上硬塞會變成兩張圖擠在一起，所以這裡把它收成右下角的**文字結論框**
      （只寫查得到具名揭露的事，不編任何結構），主角留給面板疊層本身。

   ================================================================ 本次補查（WebSearch 摘要層級，點不進原文）
   ⚠ 這個容器的出口代理擋掉 WebFetch，**以下全部只讀到搜尋摘要**，不是原文。
   · 兩片偏光板正交、上玻璃貼彩色濾光片、下玻璃嵌薄膜電晶體、黑矩陣防子像素串光、
     R／G／B 子像素並排 → 維基百科〈薄膜電晶體液晶顯示器〉、
     zhuanlan.zhihu.com/p/1998390244165310113、blog.csdn.net/boybs/article/details/132036707
   · 側光式背光模組的順序（光源／導光板／反射片／下擴散片／稜鏡片 BEF 兩片正交／
     上擴散片／反射式偏光膜）、導光板靠**底面網點**把側面入光轉成面光源
     → 材料世界網 materialsnet.com.tw/DocView.aspx?id=7559 與 id=9840
   · 玻璃本身不發光所以必須加背光模組；OLED 自發光、有機材直接鍍在玻璃上、不需背光源
     → winstar.com.tw/zh-tw/technology/oled/4.html、ledinside.com.tw/knowledge/20121017-23438.html
   · OLED 仍貼**圓偏光片**是為了擋環境光在金屬電極上的反射（線偏光片＋1/4 波片），
     代價是大約一半的出光被擋掉 —— 它是防反射件，不是光閥
     → optics.ansys.com/hc/en-us/articles/5845197523731、SID 2017 P-126
   · 驅動 IC 的接合方式 COG（晶片直接壓在玻璃的 ITO 接點上，用異方性導電膠 ACF）／
     COF（壓在軟性電路板上）→ 頎邦 chipbond.com.tw/zh-tw/product/processing_service/package/cog、
     MoneyDJ〈LCD 驅動 IC 封裝型態〉
   · 6176 瑞儀＝導光板／擴散板／背光模組 → MoneyDJ 公司資料
   · 8215 明基材、4960 誠美材＝偏光板 → 鉅亨網 news.cnyes.com/news/id/4614189
   · 6278 台表科＝TFT-LCD 面板與其他電子產品電路板的表面黏著（SMT）構裝；
     近年往記憶體模組、車用、光通訊分散 → nstock.tw 公司小百科、uc913.com/stock-6278/
   · 8069 元太＝電子紙專業製造商；6143 振曜＝元太電子紙產業聯盟的模組夥伴
     → MoneyDJ 元太公司資料、uanalyze.com.tw/articles/8296719884
   · 友達 × 康寧玻璃核心基板（GCS）、群創既有 LCD 產線轉 FOPLP 與 Chip Last 目標 2027H2
     → 規格書 §6-A5／A7／A8 已列（經濟日報、工商時報、中央社），本輪未重查
   · 台股沒有 TFT 玻璃基板廠（康寧／AGC／NEG 三家外商；台玻 1802 做的是建築玻璃與玻纖）
     → 本 repo pipeline/groups/supply_chain.yaml:135 的 note

   ================================================================ 不准編的東西（規格書 §6-C，逐條照辦）
   · 在手訂單、市占率、營收占比、產能利用率、能見度 —— **一個數字都不進畫面**
     （彩晶的「2027 車載逾三成」、群創的「產能滿載」是最容易溜進來的兩筆）
   · 具名下游客戶 —— 友達董事長自己講「不方便說和誰合作」、彩晶只講「國際品牌客戶」
   · 面積利用率百分比、可放晶片倍數、成本降幅 —— 來源全是自媒體，彼此還互相矛盾
   · 各層的實體厚度 —— 除了規格書 §6-A2 有來源的盒厚與色阻厚度，一律不標數字
   · 共通電極／配向層在哪一片 —— 依顯示模式而異，本輪查不到可引用的定論 → **不畫**
   · 不畫任何真實公司的產品外觀、機殼、logo、料號絲印 */
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { STYLE, labelRow, processBar, P3, px, py, IX, IY, onTop, onYZ } = D;

  /* 這張圖自己的材質色。**不在 JS 裡寫死 #xxxxxx**：全部收成 --dg-pn-* 變數，
     定義在下面這個 <style> 裡，JS 只引用 var(--dg-pn-*)。
     ⚠ 為什麼不寫進 site/index.html 的 :root（那裡才是 --dg-* 的家）：
       這一批有好幾個人同時在畫不同的圖，index.html 一動就會撞在一起（檔頭說明也寫了
       「不要再去動 index.html」）。所以先放在這張圖自己的 scope（.dgpn）裡，
       下一次有人正式整理 index.html 時再搬過去 —— 搬家是同值搬家，外觀零變化。
     剖析圖的容器 --illus 在深色與淺色主題下**都是深底**（index.html:50 的既有決策），
     所以同一組值在兩種主題下都成立，不需要第二套。*/
  const PN_STYLE = `<style>
    /* ★ 關掉發光（Andy 講過三次的「螢光感太重」）。
       實測：這張圖掛在 panel 族群的頁面上，預設狀態就是「族群已選」，
       於是 panel_mfg 與 display_material 的零件全部被加上 .sel ——
       量到 47 個元素同時帶 drop-shadow。那不是精密儀器，那是電競 RGB，
       而且「全部發光」這個狀態不傳達任何資訊（沒有一個是主角）。
       MLCC 用 .dg1 走同一條路（.dg.dg1 裡的 --dg-glow:none），這裡照抄它的判斷。
       關掉之後 hover 與選取仍然看得出來：描邊顏色由混色變成純環節色，
       寬度 0.55 → 2.2（同環節）→ --dg-part-w 3.6（主角）。*/
    .dg.dgpn{--dg-glow:none}
    /* 同環節其餘零件退一階 —— 不退的話「點一層」會變成「25 層一起亮」，
       跟沒點長得一樣（這正是 2026-09-21 晚間替 MLCC 加兩層高亮的理由）。
       .haspart 是 highlightSegments 掛的：沒有人被點著的時候不准壓暗。*/
    .dg.dgpn.haspart [data-seg].sel:not(.sel-part){opacity:var(--dg-sib-o,.4)}
  </style>`;

  /* `.part` 讓這一面吃得到環節色與 hover／選取的描邊。
     ★ stroke-width 寫在屬性上（.55）：`.dg [data-seg] .part` 的 CSS **只設顏色不設寬度**，
     所以基本狀態用我的屬性、hover 與選取用 CSS 的 2.2／3.6 —— 一張 13 層的疊層圖
     若每一面都用 SVG 預設的 1px（再乘上 scale 1.3），整顆會變成一團橘色線框。*/
  const poly = (fill, pts, cls) => `<path class="part${cls ? ' ' + cls : ''}" fill="${fill}" stroke-width=".55" d="M${pts.join('L')}Z"/>`;
  const flat = (fill, pts) => `<path fill="${fill}" d="M${pts.join('L')}Z"/>`;

  function panelStack() {
    // ---------------------------------------------------------------- 模型與畫面
    const L = 172, W = 126;            // 最底下那一層的平面尺寸（模型單位，非實物比例）
    const CX = 455, CY = 250, S = 1.3; // 等角原點與放大倍率（純等比縮放，幾何一行都沒動）
    const ax = (x, y) => (CX + S * px(x, y)).toFixed(1);
    const ay = (x, y, z) => (CY + S * py(x, y, z)).toFixed(1);

    /* ---------------------------------------------------------------- 疊層表
       **順序直接照規格書 §3-A 的 18 行抄**（由下到上，下＝背面、上＝觀看者），
       用一個陣列跑迴圈畫，不手刻每一層 —— 手刻就會刻錯順序，而順序正是 §3-A 的全部。
         t   這一層的厚度（示意，畫面已標明誇大）
         dy  這一層比下一層往左前方退多少（階梯式剖切；退出來的那一條帶就是它的表面）
         xl  這一層在 x 方向的長度（上玻璃比下玻璃短，讓出端子區 —— §3-A 硬規則 5）
       ★ 硬規則 2：TFT 陣列在**下**玻璃、彩色濾光片在**上**玻璃，對調＝錯。
       ★ 硬規則 3：兩片偏光板都在玻璃的**外側**，而且方向正交。
       ★ 硬規則 1：背光在最下面，觀看者在最上面。*/
    const LAY = [
      { id: 'pn_bezel', seg: 'panel_mfg', t: 7, dy: 0, xl: L, mat: 'bezel', nm: '背板／膠框' },
      { id: 'pn_refl', seg: 'panel_mfg', t: 3, dy: 5, xl: L, mat: 'refl', nm: '反射片' },
      { id: 'pn_lgp', seg: 'panel_mfg', t: 16, dy: 5, xl: L, mat: 'lgp', nm: '導光板' },
      { id: 'pn_diff', seg: 'panel_mfg', t: 3, dy: 6, xl: L, mat: 'diff', nm: '下擴散片' },
      { id: 'pn_bef1', seg: 'panel_mfg', t: 3, dy: 6, xl: L, mat: 'bef', nm: '稜鏡片 ①' },
      { id: 'pn_bef2', seg: 'panel_mfg', t: 3, dy: 8, xl: L, mat: 'bef', nm: '稜鏡片 ②（與 ① 正交）' },
      { id: 'pn_pol_lo', seg: 'panel_mfg', t: 5, dy: 8, xl: L, mat: 'pol', nm: '下偏光板' },
      { id: 'pn_glass_lo', seg: 'display_material', t: 14, dy: 8, xl: L, mat: 'glass', nm: 'TFT 陣列玻璃基板（下玻璃）' },
      { id: 'pn_tft', seg: 'panel_mfg', t: 3, dy: 6, xl: L, mat: 'tft', nm: 'TFT 陣列層' },
      { id: 'pn_lc', seg: 'panel_mfg', t: 7, dy: 12, xl: 142, mat: 'lc', nm: '液晶層' },
      { id: 'pn_cf', seg: 'panel_mfg', t: 5, dy: 8, xl: 142, mat: 'cf', nm: '彩色濾光片' },
      { id: 'pn_glass_up', seg: 'display_material', t: 14, dy: 12, xl: 148, mat: 'glass', nm: '彩色濾光片玻璃（上玻璃）' },
      { id: 'pn_pol_up', seg: 'panel_mfg', t: 5, dy: 7, xl: 140, mat: 'pol', nm: '上偏光板' },
    ];
    // 累積量：z0 ＝ 這一層的底面高度、wy ＝ 這一層在 y 方向的長度（階梯退完之後）
    let zc = 0, dyc = 0;
    LAY.forEach((o) => { dyc += o.dy; o.wy = W - dyc; o.z0 = zc; zc += o.t; });
    const ZTOP = zc;                                   // 88：整疊的頂面
    const bandOf = (i) => [i + 1 < LAY.length ? LAY[i + 1].wy : 0, LAY[i].wy];   // 第 i 層露出來的那一條帶

    // ---------------------------------------------------------------- 剖面牆上的紋理（u ＝ y、v ＝ z）
    function wallTex(o, i) {
      const u1 = o.wy, z0 = o.z0, z1 = o.z0 + o.t;
      const a = [];
      if (o.mat === 'lgp') {
        // ★ 導光板的識別特徵：**底面網點**。側面進來的光打在網點上才被打散、從正面出去。
        for (let u = 6; u < u1 - 4; u += 7) a.push(`<circle cx="${u}" cy="${(z0 + 1.6).toFixed(1)}" r="1.5" fill="var(--dg-pn-lgp-d)"/>`);
        // 光從側邊（燈條那一端）進來，沿著導光板往另一端走
        a.push(`<path class="flow slow" d="M${u1 - 8},${z0 + 9} L10,${z0 + 9}" stroke="var(--dg-pn-led)" stroke-width="1.8" fill="none"/>`);
      } else if (o.mat === 'bef') {
        // 稜鏡片的稜線：剖面上就是一排三角齒
        const d = [];
        for (let u = 2; u < u1 - 2; u += 5) d.push(`M${u},${z1} l2.5,-2.4 l2.5,2.4`);
        a.push(`<path d="${d.join(' ')}" stroke="var(--dg-pn-line)" stroke-width=".8" fill="none"/>`);
      } else if (o.mat === 'pol') {
        // 偏光板：剖面上用斜紋表示它只讓某一個方向的光過
        const d = [];
        for (let u = 2; u < u1; u += 5) d.push(`M${u},${z0 + .6} l3.2,${(o.t - 1.2).toFixed(1)}`);
        a.push(`<path d="${d.join(' ')}" stroke="var(--dg-pn-line)" stroke-width=".7" fill="none"/>`);
      } else if (o.mat === 'tft') {
        // TFT 陣列：一排電晶體坐在走線上
        for (let u = 5; u < u1 - 3; u += 11) a.push(`<rect x="${u}" y="${z0 + .4}" width="4.4" height="${(o.t - .8).toFixed(1)}" rx=".6" fill="var(--dg-pn-line2)"/>`);
      } else if (o.mat === 'lc') {
        /* 液晶畫成一排**短棒**（不是圓球、不是水）：左半躺平、右半立起來，
           中間一根光阻間隙物撐住盒厚（§4 的識別特徵）。*/
        for (let u = 4; u < u1 - 3; u += 6) {
          const up = u > u1 * 0.52;
          const cx = u + 1.6, cy = z0 + o.t / 2;
          const r = up ? `M${cx},${(cy - 2.4).toFixed(1)} L${cx},${(cy + 2.4).toFixed(1)}`
            : `M${(cx - 2.4).toFixed(1)},${cy} L${(cx + 2.4).toFixed(1)},${cy}`;
          a.push(`<path d="${r}" stroke="var(--dg-pn-rod)" stroke-width="1.9" stroke-linecap="round" fill="none"/>`);
        }
        a.push(`<rect x="${(u1 * 0.5).toFixed(1)}" y="${z0}" width="2.4" height="${o.t}" fill="var(--dg-pn-refl-d)"/>`);
        a.push(`<rect x="1" y="${z0}" width="4" height="${o.t}" fill="var(--dg-pn-bef-d)"/>`);   // 周邊一圈的封框膠（剖到端點）
      } else if (o.mat === 'cf') {
        /* ★ 硬規則 8：R／G／B 是三個**水平並排**的子像素，不是上下疊三層。
           剖面上看到的就是 R│G│B│R│G│B… 一直重複，中間夾著黑色矩陣。*/
        const col = ['var(--dg-pn-r)', 'var(--dg-pn-g)', 'var(--dg-pn-b)'];
        let k = 0;
        for (let u = 2; u < u1 - 3; u += 6) {
          a.push(`<rect x="${u}" y="${z0 + .5}" width="4.4" height="${(o.t - 1).toFixed(1)}" fill="${col[k % 3]}"/>`);
          a.push(`<rect x="${(u + 4.4).toFixed(1)}" y="${z0}" width="1.6" height="${o.t}" fill="var(--dg-pn-bm)"/>`);
          k++;
        }
      } else if (o.mat === 'glass') {
        a.push(`<path d="M2,${(z1 - 2).toFixed(1)} H${(u1 - 2).toFixed(1)}" stroke="rgba(255,255,255,.22)" stroke-width=".9" fill="none"/>`);
      }
      return a.join('');
    }

    // ---------------------------------------------------------------- 露出來那一條帶上的「表面長相」
    function topTex(o, i) {
      const [yA, yB] = bandOf(i);        // 這一層在 y∈[yA,yB] 這一條帶上是露出來的
      if (yB - yA < 4) return '';
      const x1 = o.xl, a = [];
      const mid = (yA + yB) / 2;
      if (o.mat === 'bef') {
        /* 兩片稜鏡片的稜線**互相正交**：①的稜線沿 x 走、②的沿 y 走。
           畫面上看得出兩組方向不同，才是「兩片正交」而不是「同一片畫兩次」。*/
        const d = [];
        if (i === 4) for (let y = yA + 1.5; y < yB; y += 2.6) d.push(`M2,${y.toFixed(1)} H${x1 - 2}`);
        else for (let x = 3; x < x1 - 2; x += 4) d.push(`M${x},${yA + 1} V${(yB - 1).toFixed(1)}`);
        a.push(`<path d="${d.join(' ')}" stroke="var(--dg-pn-line)" stroke-width=".7" fill="none"/>`);
      } else if (o.mat === 'pol') {
        /* ★ 硬規則 3 的畫面版：兩片偏光板的紋理方向不同（上下正交）。
           下偏光板的紋沿 x、上偏光板的紋沿 y。*/
        const d = [];
        if (i === 6) for (let y = yA + 1.6; y < yB; y += 2.8) d.push(`M2,${y.toFixed(1)} H${x1 - 2}`);
        else for (let x = 3; x < x1 - 2; x += 4.5) d.push(`M${x},${yA + 1} V${(yB - 1).toFixed(1)}`);
        a.push(`<path d="${d.join(' ')}" stroke="var(--dg-pn-line)" stroke-width=".8" fill="none"/>`);
      } else if (o.mat === 'tft') {
        /* ★ §4：橫的閘極線、縱的資料線**正交成格**，每一格角落一顆電晶體。
           畫成平行、或畫成同一層＝錯。*/
        const d = [];
        for (let y = yA + 3; y < yB; y += 4.5) d.push(`M2,${y.toFixed(1)} H${x1 - 2}`);
        a.push(`<path d="${d.join(' ')}" stroke="var(--dg-pn-line)" stroke-width=".7" fill="none"/>`);
        const d2 = [];
        for (let x = 5; x < x1 - 2; x += 7) d2.push(`M${x},${yA + 1} V${(yB - 1).toFixed(1)}`);
        a.push(`<path d="${d2.join(' ')}" stroke="var(--dg-pn-line2)" stroke-width="1" fill="none"/>`);
        for (let x = 5; x < x1 - 4; x += 14) a.push(`<rect x="${x + 1}" y="${(yA + 2).toFixed(1)}" width="2.6" height="2.6" fill="var(--dg-pn-line2)"/>`);
      } else if (o.mat === 'cf') {
        // 從上往下看色阻：一排一排的 R／G／B 方塊，被黑色矩陣框成格柵
        const col = ['var(--dg-pn-r)', 'var(--dg-pn-g)', 'var(--dg-pn-b)'];
        let k = 0;
        for (let x = 3; x < x1 - 4; x += 5) {
          a.push(`<rect x="${x}" y="${(yA + 1.5).toFixed(1)}" width="3.6" height="${(yB - yA - 3).toFixed(1)}" fill="${col[k % 3]}"/>`);
          k++;
        }
      } else if (o.mat === 'lc') {
        const d = [];
        for (let x = 4; x < x1 - 3; x += 7) d.push(`M${x},${(mid - 1.8).toFixed(1)} l3.4,3.6`);
        a.push(`<path d="${d.join(' ')}" stroke="var(--dg-pn-rod)" stroke-width="1.4" stroke-linecap="round" fill="none"/>`);
      } else if (o.mat === 'lgp') {
        const d = [];
        for (let x = 5; x < x1 - 3; x += 6) d.push(`M${x},${(mid - 1).toFixed(1)} h3`);
        a.push(`<path d="${d.join(' ')}" stroke="var(--dg-pn-lgp-d)" stroke-width=".9" fill="none"/>`);
      }
      return a.length ? onTop(o.z0 + o.t, a.join('')) : '';
    }

    // ---------------------------------------------------------------- 一層＝一個可點的零件
    function layer(o, i) {
      const zt = o.z0 + o.t, x1 = o.xl, wy = o.wy;
      const top = `var(--dg-pn-${o.mat})`, side = `var(--dg-pn-${o.mat}-d)`;
      const wall = onYZ(x1, 0)
        + `<rect class="part" x="0" y="${o.z0}" width="${wy}" height="${o.t}" fill="${side}" stroke-width=".55"/>`
        + wallTex(o, i) + `</g>`;
      const face = poly(side, [P3(0, wy, zt), P3(x1, wy, zt), P3(x1, wy, o.z0), P3(0, wy, o.z0)]);
      const face2 = poly(top, [P3(0, 0, zt), P3(x1, 0, zt), P3(x1, wy, zt), P3(0, wy, zt)]);
      return `<g data-seg="${o.seg}" data-part="${o.id}">${wall}${face}${face2}${topTex(o, i)}</g>`;
    }

    // ---------------------------------------------------------------- LED 燈條（★ 在導光板「側邊」，不是正下方）
    const lgp = LAY[2];
    const BY0 = 116, BY1 = 124, BZ0 = lgp.z0 + 2, BZ1 = lgp.z0 + lgp.t - 2;
    const ledBar = `<g data-seg="panel_mfg" data-part="pn_led">
      ${poly('var(--dg-pn-led-d)', [P3(0, BY1, BZ1), P3(L, BY1, BZ1), P3(L, BY1, BZ0), P3(0, BY1, BZ0)])}
      ${poly('var(--dg-pn-led)', [P3(0, BY0, BZ1), P3(L, BY0, BZ1), P3(L, BY1, BZ1), P3(0, BY1, BZ1)])}
      ${poly('var(--dg-pn-led-d)', [P3(L, BY0, BZ1), P3(L, BY1, BZ1), P3(L, BY1, BZ0), P3(L, BY0, BZ0)])}
      <g transform="translate(${px(0, BY1).toFixed(1)},${py(0, BY1, 0).toFixed(1)}) matrix(${IX},${IY},0,-1,0,0)">
        ${(() => { const a = []; for (let u = 8; u < L - 6; u += 16) a.push(`<rect class="pulse" x="${u}" y="${BZ0 + 2}" width="6" height="${(BZ1 - BZ0 - 4).toFixed(1)}" rx="1" fill="#fff" opacity=".8" style="animation-delay:${((u / 16) % 5) * 0.3}s"/>`); return a.join(''); })()}
      </g></g>`;

    // ---------------------------------------------------------------- 端子區：驅動 IC ＋ COF 軟板
    /* ★ §3-A 硬規則 5 的畫面版：下玻璃比上玻璃長，多出來的那一條就是端子區，
       驅動 IC 就貼在那裡（COG：晶片直接壓在玻璃的接點上；COF：壓在軟板上再接過來），
       軟板往背面折。兩片玻璃畫成一樣大＝錯，那樣驅動 IC 無處可接。*/
    const tft = LAY[8], ZL = tft.z0 + tft.t;
    const pads = (() => { const a = []; for (let y = 10; y < 96; y += 6) a.push(`<rect x="149" y="${y}" width="3" height="4" fill="var(--dg-pn-pad)"/>`); return a.join(''); })();
    /* ★ 這一塊刻意掛 `panel_mfg` 而不是 `ic_design`，理由是量出來的：
         這張圖是**族群層級**的圖，頁面預設狀態就是「panel 族群已選」，
         而 `panel` 族群裡一檔驅動 IC 廠都沒有（它們在半導體鏈的「顯示驅動 IC」族群）。
         掛 `ic_design` 的話，實測這一塊與它的說明列**在預設狀態下 opacity 就是 0.3**
         —— 一個永遠灰掉、字也讀不清楚的零件，比沒有更糟。
       掛 `panel_mfg` 也不是敷衍：畫面上這一塊指的是「端子區與貼合」這件事，
       那確實是面板廠模組段的工序（COG 把晶片壓在玻璃的 ITO 接點上、COF 壓在軟板上）。
       **晶片本身是誰做的寫在說明列與左下角的文字裡**，不靠顏色去宣稱。*/
    const driver = `<g data-seg="panel_mfg" data-part="pn_driver">
      ${onTop(ZL, pads)}
      ${poly('var(--dg-pn-ic)', [P3(154, 38, ZL + 4), P3(168, 38, ZL + 4), P3(168, 92, ZL + 4), P3(154, 92, ZL + 4)])}
      ${poly('var(--dg-pn-ic-d)', [P3(154, 92, ZL + 4), P3(168, 92, ZL + 4), P3(168, 92, ZL), P3(154, 92, ZL)])}
      ${poly('var(--dg-pn-ic-d)', [P3(168, 38, ZL + 4), P3(168, 92, ZL + 4), P3(168, 92, ZL), P3(168, 38, ZL)])}
      ${flat('var(--dg-pn-cof)', [P3(168, 44, ZL + .6), P3(190, 44, ZL + .6), P3(190, 86, ZL + .6), P3(168, 86, ZL + .6)])}
      ${flat('var(--dg-pn-cof-d)', [P3(190, 44, ZL + .6), P3(190, 44, 28), P3(190, 86, 28), P3(190, 86, ZL + .6)])}
      ${flat('var(--dg-pn-cof)', [P3(190, 86, ZL + .6), P3(190, 86, 28), P3(196, 86, 28), P3(196, 86, ZL + .6)])}
    </g>`;

    // ---------------------------------------------------------------- 光由下往上穿過整疊（動畫；靜止模式下疊層本身仍看得見）
    const lightUp = onYZ(L, 0)
      + [26, 56, 86].map((u, k) => `<path class="flow ${k === 1 ? '' : 'slow'}" d="M${u},${lgp.z0 + lgp.t} L${u},${ZTOP + 10}" stroke="var(--dg-accent)" stroke-width="1.6" fill="none" opacity=".75"/>`).join('')
      + `</g>`;

    const iso = `<g transform="translate(${CX},${CY}) scale(${S})">`
      + LAY.slice(0, 3).map(layer).join('') + ledBar
      + LAY.slice(3, 9).map((o, k) => layer(o, k + 3)).join('')
      + driver
      + LAY.slice(9).map((o, k) => layer(o, k + 9)).join('')
      + lightUp + `</g>`;

    // ---------------------------------------------------------------- 左欄 ① 兩片偏光板 ＝ 一道光閥
    function valve(ry, on) {
      const rods = [];
      for (let i = 0; i < 5; i++) {
        const cx = 92 + i * 11, cy = ry + 15;
        rods.push(on
          ? `<path d="M${cx - 4},${cy + 4} L${cx + 4},${cy - 4}" stroke="var(--dg-pn-rod)" stroke-width="2.2" stroke-linecap="round" fill="none"/>`
          : `<path d="M${cx - 4},${cy} L${cx + 4},${cy}" stroke="var(--dg-pn-rod)" stroke-width="2.2" stroke-linecap="round" fill="none"/>`);
      }
      const hatch = (x, vert) => {
        const d = [];
        if (vert) for (let k = 0; k < 4; k++) d.push(`M${x + 1.6 + k * 1.8},${ry + 2} v26`);
        else for (let k = 0; k < 7; k++) d.push(`M${x + 1},${ry + 3 + k * 4} h6`);
        return `<path d="${d.join(' ')}" stroke="var(--dg-pn-line)" stroke-width=".9" fill="none"/>`;
      };
      return `<g>
        <rect x="30" y="${ry}" width="20" height="30" rx="3" fill="var(--dg-pn-led)"/>
        <path class="flow fast" d="M52,${ry + 15} H62" stroke="var(--dg-accent)" stroke-width="2" fill="none"/>
        <rect x="64" y="${ry}" width="8" height="30" rx="1.5" fill="var(--dg-pn-pol)"/>${hatch(64, true)}
        <path class="flow fast" d="M74,${ry + 15} H84" stroke="var(--dg-accent)" stroke-width="2" fill="none"/>
        <rect x="86" y="${ry}" width="58" height="30" rx="2" fill="var(--dg-pn-lc)"/>${rods.join('')}
        <path class="flow fast" d="M146,${ry + 15} H156" stroke="${on ? 'var(--dg-accent)' : 'var(--dg-mute)'}" stroke-width="2" fill="none"/>
        <rect x="158" y="${ry}" width="8" height="30" rx="1.5" fill="var(--dg-pn-pol)"/>${hatch(158, false)}
        ${on ? `<path class="flow fast" d="M168,${ry + 15} H186" stroke="var(--dg-accent)" stroke-width="2.4" fill="none"/>`
          : `<path d="M169,${ry + 9} l10,12 M179,${ry + 9} l-10,12" stroke="var(--dg-err)" stroke-width="2" fill="none"/>`}
        <rect x="192" y="${ry + 3}" width="24" height="24" rx="4" fill="${on ? '#f4f7ff' : '#141922'}" stroke="var(--dg-mute)" stroke-width="1"/>
        <text class="lbl" x="224" y="${ry + 20}">${on ? '亮' : '暗'}</text></g>`;
    }

    // ---------------------------------------------------------------- 左欄 ② 顏色是「濾」出來的
    const filt = (() => {
      const col = ['var(--dg-pn-r)', 'var(--dg-pn-g)', 'var(--dg-pn-b)'];
      const nm = ['紅', '綠', '藍'];
      return col.map((c, i) => {
        const y = 318 + i * 17;
        return `<path class="flow slow" d="M34,${y} H84" stroke="#f0f4ff" stroke-width="2" fill="none"/>`
          + `<rect x="86" y="${y - 7}" width="16" height="14" rx="2" fill="${c}"/>`
          + `<rect x="102" y="${y - 7}" width="2.6" height="14" fill="var(--dg-pn-bm)"/>`
          + `<path class="flow slow" d="M106,${y} H150" stroke="${c}" stroke-width="2.4" fill="none"/>`
          + `<text class="sub" x="156" y="${y + 4}">只有${nm[i]}色過得去</text>`;
      }).join('');
    })();

    // ---------------------------------------------------------------- ③ 一個像素放大（R／G／B 並排、不是疊三層）
    const pixels = (() => {
      const col = ['var(--dg-pn-r)', 'var(--dg-pn-g)', 'var(--dg-pn-b)'];
      const SW = 20, SH = 42, BMW = 4, X0 = 36, Y0 = 536;
      const a = [`<rect x="${X0 - BMW}" y="${Y0 - BMW}" width="${3 * (3 * SW + 3 * BMW) + BMW}" height="${2 * (SH + BMW) + BMW}" fill="var(--dg-pn-bm)"/>`];
      for (let r = 0; r < 2; r++) for (let p = 0; p < 3; p++) for (let s = 0; s < 3; s++) {
        const x = X0 + p * (3 * SW + 3 * BMW) + s * (SW + BMW), y = Y0 + r * (SH + BMW);
        a.push(`<rect x="${x}" y="${y}" width="${SW}" height="${SH}" fill="${col[s]}" opacity="${0.55 + 0.15 * ((r + s + p) % 3)}"/>`);
        // 每一個子像素角落一顆薄膜電晶體，接到橫的閘極線與縱的資料線
        a.push(`<rect x="${x + 1.5}" y="${y + SH - 9}" width="7.5" height="7.5" rx="1" fill="var(--dg-pn-ic)"/>`);
      }
      const gx = [], gy = [];
      for (let r = 0; r <= 2; r++) gx.push(`M${X0 - BMW},${Y0 + r * (SH + BMW) - BMW / 2} H${X0 + 3 * (3 * SW + 3 * BMW)}`);
      for (let p = 0; p < 3; p++) for (let s = 0; s < 3; s++) gy.push(`M${X0 + p * (3 * SW + 3 * BMW) + s * (SW + BMW) - BMW / 2},${Y0 - BMW} V${Y0 + 2 * (SH + BMW)}`);
      a.push(`<path d="${gx.join(' ')}" stroke="var(--dg-pn-tft)" stroke-width="2.2" fill="none"/>`);
      a.push(`<path d="${gy.join(' ')}" stroke="var(--dg-pn-cof)" stroke-width="1.6" fill="none"/>`);
      return a.join('');
    })();

    // ---------------------------------------------------------------- ④ 液晶層：兩種排列
    function cell(x0, on) {
      const GT = 560, GB = 604;            // 兩片玻璃之間
      const rods = [];
      for (let i = 0; i < 7; i++) {
        const cx = x0 + 16 + i * 15, cy = (GT + GB) / 2;
        rods.push(on ? `<path d="M${cx},${cy - 12} L${cx},${cy + 12}" stroke="var(--dg-pn-rod)" stroke-width="3" stroke-linecap="round" fill="none"/>`
          : `<path d="M${cx - 11},${cy + 3} L${cx + 11},${cy - 3}" stroke="var(--dg-pn-rod)" stroke-width="3" stroke-linecap="round" fill="none"/>`);
      }
      return `<g>
        <rect x="${x0}" y="${GT - 16}" width="124" height="16" rx="2" fill="var(--dg-pn-glass)"/>
        <rect x="${x0}" y="${GT}" width="124" height="${GB - GT}" fill="var(--dg-pn-lc)"/>
        ${rods.join('')}
        <rect x="${x0 + 58}" y="${GT}" width="6" height="${GB - GT}" fill="var(--dg-pn-refl-d)"/>
        <rect x="${x0}" y="${GT}" width="9" height="${GB - GT}" fill="var(--dg-pn-bef-d)"/>
        <rect x="${x0 + 115}" y="${GT}" width="9" height="${GB - GT}" fill="var(--dg-pn-bef-d)"/>
        <rect x="${x0}" y="${GB}" width="124" height="16" rx="2" fill="var(--dg-pn-glass)"/>
        <path d="M${x0 + 128},${GT} V${GB}" stroke="var(--dg-accent)" stroke-width="1.2" fill="none"/>
        <path d="M${x0 + 125},${GT + 3} l3,-3 l3,3 M${x0 + 125},${GB - 3} l3,3 l3,-3" stroke="var(--dg-accent)" stroke-width="1.2" fill="none"/>
      </g>`;
    }

    // ---------------------------------------------------------------- ⑤ LCD 與 OLED 疊層對照
    function mini(x0, rows, y0) {
      let y = y0;
      return rows.map(([h, c, tag]) => {
        const g = `<rect x="${x0}" y="${y}" width="78" height="${h}" fill="${c}" stroke="var(--dg-pn-line2)" stroke-width=".8"/>`
          + (tag ? `<rect x="${x0 - 3}" y="${y - 2}" width="84" height="${h + 4}" fill="none" stroke="var(--dg-warn)" stroke-width="1.6" stroke-dasharray="4 3"/>` : '');
        y += h;
        return g;
      }).join('');
    }
    const lcdMini = mini(690, [[7, 'var(--dg-pn-pol)'], [13, 'var(--dg-pn-glass)'], [7, 'var(--dg-pn-cf)'],
      [9, 'var(--dg-pn-lc)', 1], [13, 'var(--dg-pn-glass)'], [7, 'var(--dg-pn-pol)'],
      [26, 'var(--dg-pn-lgp)', 1]], 552);
    const oledMini = mini(846, [[7, 'var(--dg-pn-pol)'], [9, 'var(--dg-pn-glass)'],
      [11, 'var(--dg-pn-org)'], [13, 'var(--dg-pn-glass)']], 552);

    return `<svg class="dg dgm dgpn rs" viewBox="0 0 980 1164" width="100%" style="display:block">${STYLE}${PN_STYLE}
      <text class="ttl" x="16" y="26">面板疊層：一片 TFT-LCD 從背光到偏光板，疊了十三層</text>
      <text class="cap" x="16" y="46">中間是等角「階梯式剖切」：右邊那面牆是剖面（層序與材質），左前方每退一階就露出那一層的表面。左欄講原理、右欄逐層說明，下面是放大圖、OLED 對照與製程。</text>

      <!-- ================= 左欄 ① 兩片偏光板 ＝ 一道光閥 ================= -->
      <rect class="frame" x="16" y="70" width="270" height="196" rx="8"/>
      <text class="hd" x="30" y="92">① 兩片偏光板夾著液晶 ＝ 一道光閥</text>
      <text class="lbl" x="30" y="112">液晶把光轉過去</text>
      ${valve(118, true)}
      <text class="lbl" x="30" y="168">液晶不轉</text>
      ${valve(174, false)}
      <text class="sub" x="30" y="222">兩片偏光板的方向「正交」：第一片先把光整</text>
      <text class="sub" x="30" y="240">理成單一方向，液晶轉不轉決定它到不到得</text>
      <text class="sub" x="30" y="258">了第二片。少一片就沒有「擋得掉」這件事。</text>

      <!-- ================= 左欄 ② 顏色是濾出來的 ================= -->
      <rect class="frame" x="16" y="278" width="270" height="146" rx="8"/>
      <text class="hd" x="30" y="300">② 顏色是「濾」出來的，不是背光給的</text>
      ${filt}
      <text class="sub" x="30" y="388">白光上來，上玻璃的色阻讓紅的只過紅、綠</text>
      <text class="sub" x="30" y="406">的只過綠、藍的只過藍；三個子像素各自調</text>
      <text class="sub" x="30" y="424">亮度，混出這一點的顏色。</text>

      <text class="sub" x="16" y="448" style="fill:var(--dg-warn)">★ 兩個常見的畫錯：把背光畫成彩色（顏色不是它給的）、</text>
      <text class="sub" x="16" y="466" style="fill:var(--dg-warn)">　 把 R／G／B 畫成上下疊三層（它們是水平並排的三個子像素）。</text>

      <!-- ================= 中間：等角階梯式剖切 ================= -->
      <text class="cap" x="300" y="80">↑ 觀看者在最上面</text>
      <text class="cap" x="300" y="98">↓ 背光在最下面，光由下往上穿過整疊</text>
      ${iso}

      <!-- ================= 右欄：逐層說明（引線接回剖面牆）=================
           引線一律拉到零件外側的文字框，不壓在零件上；文字不跟著縮放。-->
      ${labelRow('panel_mfg', 688, 122, '上偏光板', '貼在上玻璃外側，方向與下偏光板正交', ax(140, 0), ay(140, 0, 85.5), 268, null, 1)}
      ${labelRow('display_material', 688, 168, '兩片玻璃基板', '★ 台股沒有 TFT 玻璃基板廠，只有外商', ax(148, 0), ay(148, 0, 76), 268, null, 2)}
      ${labelRow('panel_mfg', 688, 214, '上玻璃：彩色濾光片', '黑色矩陣框住並排的 R／G／B 色阻', ax(142, 0), ay(142, 0, 66.5), 268, null, 3)}
      ${labelRow('panel_mfg', 688, 260, '液晶層', '盒厚靠間隙物撐住，周邊一圈封框膠封住', ax(142, 0), ay(142, 0, 60.5), 268, null, 4)}
      ${labelRow('panel_mfg', 688, 306, '下玻璃上的 TFT 陣列', '閘極線與資料線正交成格，一格一顆電晶體', ax(172, 0), ay(172, 0, 55.5), 268, null, 5)}
      ${labelRow('panel_mfg', 688, 352, '下偏光板', '★ 貼在下玻璃外側，不是夾在液晶旁邊', ax(172, 0), ay(172, 0, 37.5), 268, null, 6)}
      ${labelRow('panel_mfg', 688, 398, '背光模組（白光的來源）', '反射片→導光板→擴散片→稜鏡片×2', ax(172, 0), ay(172, 0, 18), 268, null, 7)}
      ${labelRow('panel_mfg', 688, 444, '端子區：驅動 IC ＋ COF 軟板', '晶片由 IC 設計廠做，面板廠負責貼合上去', ax(190, 44), ay(190, 44, 28), 268, null, 8)}

      <!-- ================= 放大區 ③ 一個像素 ================= -->
      <rect class="frame" x="16" y="496" width="296" height="248" rx="8"/>
      <text class="hd" x="30" y="518">③ 放大看：R／G／B 水平並排</text>
      <g data-seg="panel_mfg" data-part="pn_pixel">${pixels}</g>
      <text class="sub" x="30" y="650">每一格是一個子像素，角落那顆是它的電晶體。</text>
      <text class="sub" x="30" y="668">橫的閘極線選一列、縱的資料線送電壓，兩者正交。</text>
      <text class="sub" x="30" y="686">黑色矩陣（黑格柵）把子像素框開，擋住漏光。</text>
      <text class="sub" x="30" y="704" style="fill:var(--dg-warn)">圖上畫 3 個像素 × 2 列，實際一片面板有數百萬個。</text>

      <!-- ================= 放大區 ④ 液晶兩種排列 ================= -->
      <rect class="frame" x="328" y="496" width="324" height="248" rx="8"/>
      <text class="hd" x="342" y="518">④ 液晶層：靠「轉向」控制光</text>
      <text class="lbl" x="342" y="540">不加電（初始排列）</text>
      <text class="lbl" x="494" y="540">加電（分子轉向）</text>
      <g data-seg="panel_mfg" data-part="pn_lcmol">${cell(342, false)}${cell(494, true)}</g>
      <text class="sub" x="342" y="640">短棒＝液晶分子（不是圓球、也不是水）。中間那根</text>
      <text class="sub" x="342" y="658">是光阻間隙物，撐住兩片玻璃之間的盒厚（典型約</text>
      <text class="sub" x="342" y="676">3.7 µm，典型值）；兩端是周邊一圈的封框膠。</text>
      <text class="sub" x="342" y="694" style="fill:var(--dg-warn)">哪一邊是亮、哪一邊是暗，依顯示模式（TN／VA／</text>
      <text class="sub" x="342" y="712" style="fill:var(--dg-warn)">IPS）而定，圖上不指定。</text>

      <!-- ================= 放大區 ⑤ LCD vs OLED ================= -->
      <rect class="frame" x="668" y="496" width="296" height="248" rx="8"/>
      <text class="hd" x="682" y="518">⑤ 換成 OLED 少掉哪幾層</text>
      <g data-seg="panel_mfg" data-part="pn_oled">
        <text class="lbl" x="690" y="540">LCD</text><text class="lbl" x="846" y="540">OLED</text>
        ${lcdMini}${oledMini}
        <path class="flow" d="M776,596 H840" stroke="var(--dg-accent)" stroke-width="2" fill="none"/>
      </g>
      <text class="sub" x="682" y="668" style="fill:var(--dg-warn)">虛線框的兩塊 OLED 沒有：背光模組與液晶層。</text>
      <text class="sub" x="682" y="686">OLED 自發光，顏色由有機材料直接給，所以不需要</text>
      <text class="sub" x="682" y="704">背光，也不需要液晶＋兩片偏光板這道光閥。</text>
      <text class="sub" x="682" y="722">它通常仍貼一片圓偏光片，但那是擋反射用的。</text>

      <!-- ================= 製程 ================= -->
      <text class="cap" x="16" y="790">製造流程（三大段併成五格）　★ 陣列（下玻璃）與彩色濾光片（上玻璃）是兩條各自獨立的線，到「組立」才合在一起</text>
      ${processBar(16, 800, [
        { seg: 'display_material', t: '玻璃基板', s: '上下兩片玻璃（台股沒有廠）' },
        { seg: 'panel_mfg', t: 'Array 陣列', s: '成膜→黃光→蝕刻→剝膜' },
        { seg: 'panel_mfg', t: 'CF 彩色濾光片', s: '黑色矩陣＋R/G/B 色阻' },
        { seg: 'panel_mfg', t: 'Cell 組立', s: '配向、封框、灌液晶、切割' },
        { seg: 'panel_mfg', t: 'Module 模組', s: '貼偏光板、接驅動 IC' }], 180)}

      <!-- ================= 兩個結論框 ================= -->
      <rect class="frame" x="16" y="860" width="470" height="168" rx="8"/>
      <text class="hd" x="30" y="882">「面板產業」族群 9 檔各站在哪一格</text>
      <text class="sub" x="30" y="906">面板廠（TFT-LCD 本體）：2409 友達、3481 群創、6116 彩晶</text>
      <text class="sub" x="30" y="924">背光模組／導光板：6176 瑞儀</text>
      <text class="sub" x="30" y="942">偏光板：8215 明基材、4960 誠美材</text>
      <text class="sub" x="30" y="960">後段模組 SMT：6278 台表科（近年往記憶體模組、車用、光通訊分散）</text>
      <text class="sub" x="30" y="978">電子紙（另一種顯示技術，不是 LCD）：8069 元太、6143 振曜</text>
      <text class="sub" x="30" y="996">驅動 IC 不在這個族群：3034 聯詠等在「顯示驅動 IC」族群（半導體鏈）</text>
      <text class="sub" x="30" y="1014" style="fill:var(--dg-warn)">上游 TFT 玻璃基板台股沒有廠 —— 康寧／AGC／NEG 三家外商</text>

      <rect class="frame" x="502" y="860" width="462" height="168" rx="8"/>
      <text class="hd" x="516" y="882">2026 年這一格在看什麼</text>
      <text class="sub" x="516" y="906">面板報價是循環；一座折舊完的廠 ＋ 一整套在大面積玻璃上做精細</text>
      <text class="sub" x="516" y="924">線路的能力不是 —— 那套能力正被拿去做封裝用的重佈線層（RDL）。</text>
      <text class="sub" x="516" y="942">· 友達與康寧合作玻璃核心基板（GCS），友達出 TGV／RDL 製程，</text>
      <text class="sub" x="516" y="960">　規劃 2026 下半年建置試產線。</text>
      <text class="sub" x="516" y="978">· 群創把既有 LCD 產線轉為扇出型面板級封裝（FOPLP），Chip Last</text>
      <text class="sub" x="516" y="996">　平台目標 2027 下半年量產。</text>
      <text class="sub" x="516" y="1014">· 彩晶留在顯示本業，主攻車載、工控、無人機等利基應用。</text>

      <!-- ================= 示意標示（規格書 §5-D，缺一行就退回）================= -->
      <text class="cap" x="16" y="1050">原創示意圖，非實物比例。疊層厚度為示意：玻璃是零點幾毫米、液晶層只有幾微米，畫面比例已誇大兩個數量級。</text>
      <text class="cap" x="16" y="1068">圖上是「階梯式剖切」—— 每一層往左前方退一階，才看得到下面那一層；實際每一層的面積沒有這樣遞減。背光畫的是側光式（LED 在導光板側邊），直下式不在本圖。</text>
      <text class="cap" x="16" y="1086">共通電極、配向層、平坦化層沒有畫：它們的位置與有無依顯示模式（TN／VA／IPS）而異，本輪查不到可引用的定論 —— 寧可不畫，也不要畫一個看起來很專業的錯結構。</text>
      <text class="cap" x="16" y="1104">零件顏色＝環節色。點零件只會「亮」不會篩成分股（要篩請點下方的環節色標或族群卡片）。這張圖涵蓋兩個環節：面板 TFT-LCD、面板材料 玻璃基板。</text>
      <text class="cap" x="16" y="1122">驅動 IC 的晶片屬半導體鏈的「顯示驅動 IC」族群（3034 聯詠等），圖上只畫它貼在面板端子區的位置。本圖不放任何在手訂單、市占率、營收占比或產能數字。</text>
      <text class="cap" x="16" y="1140">資料來源與信心度見 docs/diagram_specs/panel_stack.md；本輪補查的來源（含每一條的網址）列在 site/dg/panel.js 檔頭。</text>
    </svg>`;
  }

  window.DG.register('panel', {
    level: 'group', chain: 'electronics',
    name: '面板：TFT-LCD 疊層剖析',
    draw: panelStack,
    native: 980,
    /* 不做 3D：這張圖的資訊全部在剖面的層序裡，一疊薄膜轉一圈只會看到一塊不透明的平板，
       多轉的那一圈不解釋任何一件事（規格書〈型式〉已寫死，dg3d_standard 的判準）。*/
    scene: null,
    q: '一片面板從背光到偏光板疊了哪十三層、為什麼非得要兩片偏光板？換成 OLED 會少掉哪幾層，台股的面板廠、背光模組、偏光板各站在哪一格？',
  });
})();
