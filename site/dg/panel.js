/* 面板疊層 —— docs/diagram_plan.md 的第 7 張（族群 `panel`、electronics 鏈）
   規格書：docs/diagram_specs/panel_stack.md（2026-09-20 由 mechanical-engineer 簽過）

   ================================================================ 這張圖回答什麼
   「一片面板從背光到蓋板疊了哪幾層、每一層在幹嘛」，以及三件最容易被畫錯的事：
     ① 為什麼要**兩片**偏光板（少一片就關不掉）
     ② 顏色是上玻璃的色阻**濾**出來的，不是背光給的；R／G／B **水平並排**不是疊三層
     ③ 換成 OLED 會少掉哪幾層（自發光 → 不需要背光模組，也不需要液晶層）
   最後把「面板產業」族群 9 檔各自放回它站的那一格。

   ---- 2026-09-22 v2（DECISIONS #238／#239／#240 ＋ Andy 的參考圖 docs/diagram_refs/2d_panel_dark_light.webp）----
   ★ 這張是 Andy 親自給參考圖的對象，當全站的示範品。參考圖裡的東西逐項對：
   · **13 層垂直爆炸玻璃層疊**：每一層是 D.fx.glass 畫的帶厚度、圓角、半透明漸層的玻璃板（前面 ＋ 頂面 ＋ 右側面），
     由下往上：背板／膠框 → 反射片 → 導光板（側邊 LED 燈條）→ 下擴散片 → 稜鏡片 ①② → 下偏光板 → 下玻璃（TFT 陣列，
     右端多出端子區貼驅動 IC）→ TFT 陣列 → 液晶層 → 彩色濾光片 → 上玻璃 → 上偏光板。層序直接照規格書 §3-A。
   · **光束穿層**：背光上來的是一道**白光**（顏色不是它給的），穿過彩色濾光片之後才變成 R／G／B 三道 —— 三道共用一個光暈濾鏡
     （D.fx.beams），白光一道（D.fx.beam），柔陰影一組，剛好用完 ≤ 3 個 feGaussianBlur 的預算（#239／#240）。
   · **小元件立體化**：液晶分子＝小橢球（D.fx.molecule，左半躺平、右半立起來）、TFT 陣列＝一格格小磚（閘極線與資料線正交）、
     色阻＝黑色矩陣上一格格 R│G│B 並排的小色塊、背光＝發白光的板 ＋ 側邊 LED、驅動 IC＝端子區上的小晶片 ＋ 往下折的 COF。
   · **左側兩個說明框含小示意**（① 兩片偏光板＝一道光閘、② 顏色是濾出來的）留在 SVG 裡；
     **右側卡片外掛**成 HTML（extRow side:'r'）＋ 細引線 ＋ 編號圓點；背光那兩張卡片走左欄（引線從畫布左緣進來，錨點刻意
     放在說明框②的下緣以下，引線不會壓到說明框）。
   · 畫布 980 → **660**（主角寬），`native: 660`；svg 根掛 `.rs`（閱讀模式字級升一階）。
   · §1 從 471 壓到約 526：只留層疊 ＋ 左側兩個說明框 ＋ 兩行示意標示；放大圖（像素、液晶兩種排列）、OLED 對照 ＋ 製程五格、
     族群九檔 ＋ 2026 結論 ＋ 其餘標示收進三個章節，**一個字沒刪，只改斷行與位置**。收合 ≈ 526 ＋ 8 ＋ 42×3 ＋ 10 ≈ 670。
   · 卡片與畫布上的零件是同一個 data-part：點卡片亮零件、點零件亮卡片；「誰做的」小卡的內容在 register 的 parts。
   · 兩種模式構圖相同、只換材質與光：亮＝米白底＋柔陰影、暗＝深藍底＋發光。顏色全部走 --dg-pn-* 與 --fx-* token，JS 裡沒有色值。

   ================================================================ 為什麼不做真 3D（scene: null）
   規格書〈型式〉已經寫死，這裡照抄理由並複核過：
   這張圖的資訊**全部在剖面的層序裡**。一疊薄膜轉一圈只會看到一塊不透明的平板，
   多轉那一圈不解釋任何一件事（dg3d_standard §「預設 2D／2.5D」的判準）。爆炸拆開來看，13 層同時看得見。

   ================================================================ 和規格書不一致的地方（都寫在回報裡）
   規格書是 2026-09-20 寫的，比 MLCC 那張早，有幾條已經被後來的標準蓋掉：
   1. **§0 整節（掛載點）作廢**。`window.DG.register` 支援 `level:'group'`，直接註冊成 `panel` 族群的圖即可。
   2. **§7 的 CW = 1180 → 改成 660 ＋ `native: 660`**（DECISIONS #227／#239）。
   3. **字級下限 12px**（閱讀模式 `.rs` 13px）。
   4. **§6-D1 建議右半掛 `data-seg="adv_pkg"` —— 不能照做。** `adv_pkg` 的 chain 是 `semiconductor`，
      掛在 electronics 的頁面上就是 MLCC 踩過的那個坑。這張圖只用 electronics 鏈上真的有的環節：`panel_mfg`、`display_material`。
      驅動 IC 那一塊刻意掛 `panel_mfg`：panel 族群裡一檔驅動 IC 廠都沒有，掛 `ic_design` 在預設狀態下就是 opacity 0.3，
      一個永遠灰掉的零件比沒有更糟；晶片本身是誰做的寫在小卡與章節文字裡，不靠顏色宣稱。
   5. **§6-D2／D3（`.scode` 晶片、`wireThemeDiagram`）不適用** —— 台股代號一律寫成文字，不做可點的晶片
      （康寧的 ticker 是 `NYSE:GLW`，做成晶片按下去會導到不存在的路由）。
   6. **§5-E 的成分股覆蓋表只列 3 檔**，但 `groups.yaml` 的 `panel` 族群實際有 9 檔，覆蓋表擴充到 9 檔，每一檔寫它**查得到的**業務定位。
   7. 規格書把右半整個給了「面板廠轉先進封裝（FOPLP／GCS）」。那是另一個題材的結構（先進封裝，diagram_plan 第 4 張），
      這裡收成章節 ④ 的**文字結論框**（只寫查得到具名揭露的事，不編任何結構），主角留給面板疊層本身。

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
  if (!D || typeof D.register !== 'function' || !D.fx) return;
  const { STYLE, extRow, note, processBar, fold, fx } = D;

  /* ================================================================ 版面常數（畫布座標，寬 660；1100 視窗兩欄時畫布欄只有 660，680 會被切掉 20px）
     每一片玻璃板：前面 x ∈ [XL, XL+W]、厚度 t；頂面往右後上擠出 (DX, DY)。層與層之間垂直拉開（爆炸拆解），
     上一片的前面蓋住下一片頂面的一部分 —— 那正是爆炸圖該有的遮擋。上玻璃那一組（1～5）寬 W，
     下玻璃多出一條端子區（W ＋ 40，§3-A 硬規則 5），背板比整疊再寬一圈。*/
  const CW = 660, XL = 246, W = 236, DX = 104, DY = -56;
  const ISO = { dx: DX, dy: DY };
  const tp = (u, v) => `${(u + v * DX).toFixed(1)},${(v * DY).toFixed(1)}`;   // 頂面座標：u 沿板長、v 是深度（0 前緣、1 後緣）
  const S_P = 'panel_mfg', S_G = 'display_material';

  /* 疊層表：**由上往下**列（畫的時候倒過來，由下往上畫）。y ＝ 前面的上緣、t ＝ 厚度、x/w ＝ 這一片的位置與長度。
     ★ 硬規則 1：背光在最下面、觀看者在最上面。★ 硬規則 2：TFT 陣列在**下**玻璃、彩色濾光片在**上**玻璃。
     ★ 硬規則 3：兩片偏光板都在玻璃**外側**，方向正交。★ 硬規則 4：液晶在兩片玻璃**之間**。★ 硬規則 5：下玻璃比上玻璃大。*/
  const L = {
    pol_up: { y: 66, t: 8, x: XL, w: W, fill: 'var(--dg-pn-pol)', part: 'pn_pol_up', seg: S_P },
    glass_up: { y: 102, t: 14, x: XL, w: W, fill: 'var(--dg-pn-glass)', part: 'pn_glass_up', seg: S_G },
    cf: { y: 140, t: 8, x: XL, w: W, fill: 'var(--dg-pn-cf)', part: 'pn_cf', seg: S_P },
    lc: { y: 176, t: 10, x: XL, w: W, fill: 'var(--dg-pn-lc)', part: 'pn_lc', seg: S_P },
    tft: { y: 214, t: 8, x: XL, w: W, fill: 'var(--dg-pn-tft)', part: 'pn_tft', seg: S_P },
    glass_lo: { y: 250, t: 14, x: XL, w: W + 40, fill: 'var(--dg-pn-glass)', part: 'pn_glass_lo', seg: S_G },
    pol_lo: { y: 288, t: 8, x: XL, w: W, fill: 'var(--dg-pn-pol)', part: 'pn_pol_lo', seg: S_P },
    bef2: { y: 318, t: 6, x: XL, w: W, fill: 'var(--dg-pn-bef)', part: 'pn_backlight', seg: S_P },
    bef1: { y: 342, t: 6, x: XL, w: W, fill: 'var(--dg-pn-bef)', part: 'pn_backlight', seg: S_P },
    diff: { y: 366, t: 6, x: XL, w: W, fill: 'var(--dg-pn-diff)', part: 'pn_backlight', seg: S_P },
    lgp: { y: 390, t: 14, x: XL, w: W, fill: 'var(--dg-pn-lgp)', part: 'pn_backlight', seg: S_P },
    refl: { y: 422, t: 6, x: XL, w: W, fill: 'var(--dg-pn-refl)', part: 'pn_backlight', seg: S_P },
    bezel: { y: 446, t: 14, x: XL - 8, w: W + 16, fill: 'var(--dg-pn-bezel)', part: 'pn_backlight', seg: S_P },
  };
  const ORDER = ['bezel', 'refl', 'lgp', 'diff', 'bef1', 'bef2', 'pol_lo', 'glass_lo', 'tft', 'lc', 'cf', 'glass_up', 'pol_up'];   // 畫的順序：由下往上

  /* 卡片的元件色（token，不寫死）。挑的是深底上對編號數字對比 ≥ 4.5 的亮色；--dg-pn-pol 太暗，偏光板用稜鏡片那組亮藍灰。*/
  const COL = { pol: 'var(--dg-pn-bef)', glass: 'var(--dg-pn-glass)', cf: 'var(--dg-pn-g)', lc: 'var(--dg-pn-rod)', tft: 'var(--dg-pn-tft)',
    ic: 'var(--dg-pn-cof)', led: 'var(--dg-pn-led)', bl: 'var(--dg-pn-lgp)' };

  /* ================================================================ 小工具 */
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${x}" y="${y}" width="${w}" height="${h}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  // 頂面上的一塊平行四邊形（u0..u1 × v0..v1）
  const tile = (u0, u1, v0, v1, fill, op, cls) =>
    `<path${cls ? ` class="${cls}"` : ''} d="M${tp(u0, v0)} L${tp(u1, v0)} L${tp(u1, v1)} L${tp(u0, v1)}Z" fill="${fill}"${op != null ? ` opacity="${op}"` : ''}/>`;
  // 頂面上的一組線：沿 u（平行前緣）或沿 v（沿深度方向）
  const linesU = (w, vs, col, sw, u0, u1) => `<path d="${vs.map(v => `M${tp(u0 != null ? u0 : 4, v)} L${tp(u1 != null ? u1 : w - 4, v)}`).join(' ')}" stroke="${col}" stroke-width="${sw}" fill="none"/>`;
  const linesV = (us, col, sw, v0, v1) => `<path d="${us.map(u => `M${tp(u, v0 != null ? v0 : .06)} L${tp(u, v1 != null ? v1 : .94)}`).join(' ')}" stroke="${col}" stroke-width="${sw}" fill="none"/>`;
  const seq = (a, b, step) => { const r = []; for (let x = a; x < b; x += step) r.push(+x.toFixed(2)); return r; };
  const plate = (k, top, cls) => { const o = L[k]; return fx.glass(o.x, o.y, o.w, o.t, { iso: ISO, fill: o.fill, cls: cls || 'part', rx: 3, top }); };
  const plateShadow = (k) => { const o = L[k]; return `<path d="M${o.x + 4},${o.y + o.t + 10} L${o.x + o.w - 2},${o.y + o.t + 10} L${o.x + o.w + DX - 2},${o.y + o.t + 10 + DY} L${o.x + DX + 4},${o.y + o.t + 10 + DY}Z"/>`; };
  // 右側卡片的錨點：板子右側面的中點再往外 14px
  const ancR = (k) => { const o = L[k]; return [o.x + o.w + DX + 14, o.y + DY + o.t / 2 + 2]; };

  /* ================================================================ 每一層頂面上的「表面長相」（規格書 §4 的識別特徵） */
  // 偏光板：一組細紋。★ 硬規則 3 的畫面版：上偏光板的紋沿 u、下偏光板的紋沿 v —— 兩組方向不同才是「正交」。
  const texPolUp = () => linesU(W, seq(.12, .95, .12), 'var(--dg-pn-line)', .8);
  const texPolLo = () => linesV(seq(8, W - 4, 9), 'var(--dg-pn-line)', .8);
  // 稜鏡片 ①② 的稜線互相正交：① 沿 u、② 沿 v。看得出兩組方向不同，才是「兩片正交」不是「同一片畫兩次」。
  const texBef1 = () => linesU(W, seq(.1, .95, .1), 'var(--dg-pn-line)', .7);
  const texBef2 = () => linesV(seq(6, W - 4, 7), 'var(--dg-pn-line)', .7);
  // 擴散片：稀疏的小點（霧面）
  const texDiff = () => { const a = []; for (const v of [.25, .55, .85]) for (let u = 10; u < W - 6; u += 18) a.push(`<circle cx="${(u + v * DX).toFixed(1)}" cy="${(v * DY).toFixed(1)}" r=".9" fill="var(--dg-pn-line)"/>`); return a.join(''); };
  // 反射片：一道斜的高光
  const texRefl = () => linesU(W, [.5], 'var(--dg-sn)', 1.2, 30, W - 30).replace('fill="none"', 'fill="none" opacity=".5"');
  /* 導光板：**側邊 LED 燈條**（★ 硬規則 7：側光式，LED 在導光板側邊，不是正下方）＋ 從側邊進來、沿板面走的光（flow 虛線）。
     底面網點畫在前面（剖面）那一條帶的下緣 —— 見 texLgpFront。*/
  const texLgp = () =>
    `<path class="flow slow" d="M${tp(2, .5)} L${tp(W - 12, .5)}" stroke="var(--dg-pn-led)" stroke-width="1.6" fill="none" opacity=".8"/>`
    + `<path d="M${tp(W - 26, .5)} l-8,-3 M${tp(W - 26, .5)} l-8,3" stroke="var(--dg-pn-led)" stroke-width="1.4" fill="none" opacity=".8"/>`;
  // LED 燈條是獨立的零件（不巢在導光板的群組裡：巢進去的話「點 LED」會被外層的同環節退階規則一起壓暗）。畫在導光板頂面的左緣。
  const ledBar = () => `<g data-seg="${S_P}" data-part="pn_led" transform="translate(${L.lgp.x},${L.lgp.y})">${tile(-16, -2, 0, 1, 'var(--dg-pn-led)', null, 'part')}`
    + [.12, .3, .48, .66, .84].map(v => `<rect class="pulse" x="${(-13 + v * DX).toFixed(1)}" y="${(v * DY - 2).toFixed(1)}" width="8" height="4" rx="1" fill="var(--dg-sn)" opacity=".9" style="animation-delay:${(v * 2).toFixed(1)}s"/>`).join('')
    + `</g>`;
  const texLgpFront = () => { const o = L.lgp, a = []; for (let x = o.x + 8; x < o.x + o.w - 4; x += 8) a.push(`<circle cx="${x}" cy="${(o.y + o.t - 2.4).toFixed(1)}" r="1.4" fill="var(--dg-pn-lgp-d)"/>`); return a.join(''); };
  /* TFT 陣列：★ §4 —— 橫的閘極線（沿 u）、縱的資料線（沿 v）**正交成格**，每一格一塊像素電極（小磚）＋ 角落一顆電晶體。
     畫成平行、或畫成同一層＝錯。*/
  const texTft = () => {
    const us = seq(10, W - 12, 20), vs = [.1, .38, .66];
    const a = [linesU(W, [.08, .36, .64, .92], 'var(--dg-pn-line2)', .8), linesV(seq(8, W - 4, 20), 'var(--dg-pn-line2)', 1)];
    us.forEach(u => vs.forEach(v => { a.push(tile(u + 1, u + 17, v + .03, v + .24, 'var(--dg-pn-glass)', .55)); a.push(tile(u + 1.5, u + 5.5, v + .04, v + .1, 'var(--dg-pn-ic)', .95)); }));
    return a.join('');
  };
  /* 液晶層：★ §4 —— 分子畫成**小橢球**（不是圓球、不是水），左半躺平、右半立起來（加電與不加電兩種排列）。
     中間一根光阻間隙物撐住盒厚；周邊一圈封框膠（頂面外圈）。*/
  const texLc = () => {
    const a = [tile(0, W, 0, 1, 'none').replace('fill="none"', 'fill="none" stroke="var(--dg-pn-bef-d)" stroke-width="3" stroke-opacity=".55"')];
    const vs = [.22, .5, .78];
    for (let u = 16; u < W - 10; u += 22) vs.forEach((v, i) => {
      const up = u > W * .5, cx = u + v * DX + (i % 2) * 5, cy = v * DY - 4;
      a.push(fx.molecule(cx.toFixed(1), cy.toFixed(1), 5.5, 2.4, up ? -68 : -8, 'var(--dg-pn-rod)'));
    });
    a.push(tile(W * .5 - 1.5, W * .5 + 1.5, .08, .92, 'var(--dg-pn-refl-d)', .9));
    return a.join('');
  };
  /* 彩色濾光片：★ 硬規則 8 —— R／G／B 是三個**水平並排**的子像素（沿 u 一直重複 R│G│B），不是上下疊三層；
     黑色矩陣（板子本身的深色）把每一格框起來（硬規則 9）。*/
  const texCf = () => {
    const col = ['var(--dg-pn-r)', 'var(--dg-pn-g)', 'var(--dg-pn-b)'], a = [tile(0, W, 0, 1, 'var(--dg-pn-bm)', .85)];
    let k = 0;
    for (let u = 4; u < W - 8; u += 11) { for (const v of [.08, .38, .68]) a.push(tile(u, u + 8.5, v, v + .24, col[k % 3], .92)); k++; }
    return a.join('');
  };
  // 上玻璃：一道柔的高光；下玻璃：左邊是畫面區的外框，右端是端子區（墊子 ＋ 驅動 IC ＋ 往下折的 COF）
  const texGlassUp = () => linesU(W, [.62], 'var(--dg-sn)', 1.4, 24, W - 40).replace('fill="none"', 'fill="none" opacity=".45"');
  const texGlassLo = () => {
    const a = [tile(4, W - 4, .06, .94, 'none').replace('fill="none"', 'fill="none" stroke="var(--dg-pn-line)" stroke-width=".8" stroke-dasharray="3 3"')];
    for (const v of seq(.1, .95, .12)) a.push(tile(W + 6, W + 14, v, v + .06, 'var(--dg-pn-pad)', .95));
    return a.join('');
  };
  /* 端子區：驅動 IC ＋ COF 軟板（★ §3-A 硬規則 5 的畫面版：下玻璃比上玻璃長，多出來的那一條就是端子區）。
     COG：晶片直接壓在玻璃的接點上；COF：壓在軟板上再接過來，軟板往背面折（右側面上那一段就是折下去的軟板）。*/
  const driver = () => {
    const o = L.glass_lo, u0 = W + 16, u1 = W + 34, v0 = .28, v1 = .72, h = 5;
    const P = (u, v, dz) => `${(u + v * DX).toFixed(1)},${(v * DY - (dz || 0)).toFixed(1)}`;   // 頂面座標再抬高 dz
    const top = `M${P(u0, v0, h)} L${P(u1, v0, h)} L${P(u1, v1, h)} L${P(u0, v1, h)}Z`;
    const front = `M${P(u0, v0, h)} L${P(u1, v0, h)} L${P(u1, v0)} L${P(u0, v0)}Z`;
    const right = `M${P(u1, v0, h)} L${P(u1, v1, h)} L${P(u1, v1)} L${P(u1, v0)}Z`;
    const va = v0 + .08, vb = v1 - .08, dn = o.t + 14;
    return `<g data-seg="${S_P}" data-part="pn_driver" transform="translate(${o.x},${o.y})">
      ${tile(u1, o.w, va, vb, 'var(--dg-pn-cof)', .95)}
      <path d="M${P(o.w, va)} L${P(o.w, vb)} L${P(o.w, vb, -dn)} L${P(o.w, va, -dn)}Z" fill="var(--dg-pn-cof-d)" opacity=".95"/>
      <path d="M${P(o.w, va)} L${P(o.w, vb)}" stroke="var(--dg-sn)" stroke-width=".8" stroke-opacity=".5"/>
      <path d="${front}" fill="var(--dg-pn-ic-d)"/><path d="${right}" fill="var(--dg-pn-ic-d)"/>
      <path class="part" d="${top}" fill="var(--dg-pn-ic)"/>
      <path d="M${P(u0 + 2, v0 + .06, h)} L${P(u1 - 2, v0 + .06, h)}" stroke="var(--dg-sn)" stroke-width=".8" stroke-opacity=".45"/></g>`;
  };

  /* ================================================================ 光束（這張圖的動畫；靜止時光束本身仍看得見）
     ★ 背光上來的是**白光**（顏色不是它給的）—— 一道白光從導光板射到彩色濾光片；穿過色阻之後才變成 R／G／B 三道，
     一路穿過上玻璃與上偏光板到觀看者那一側。三道共用一個光暈濾鏡（fx.beams），白光一道（fx.beam）。*/
  const BX = [95, 125, 155].map(u => XL + u + .5 * DX);                       // 三道光的 x（頂面中線 v=.5）
  const yTop = (k) => L[k].y + .5 * DY;                                       // 某一片頂面中線的 y
  const WHITE = () => `M${BX[1]},${yTop('lgp')} L${BX[1]},${L.cf.y + L.cf.t}`;
  const beams = () => `<g pointer-events="none">
    ${fx.beam(WHITE(), { color: 'var(--dg-pn-refl)', w: 2.4, flow: true, dots: [[BX[1], yTop('lgp')]], dotR: 3.4 })}
    <circle r="3" fill="var(--dg-sn)" opacity=".95"><animateMotion dur="4s" repeatCount="indefinite" path="${WHITE()}"/></circle>
    ${fx.beams([['var(--dg-pn-r)', 0], ['var(--dg-pn-g)', 1], ['var(--dg-pn-b)', 2]].map(([c, i]) =>
    ({ d: `M${BX[i]},${yTop('cf')} L${BX[i]},14`, color: c, w: 2, dots: [[BX[i], 14]] })), { flow: true, dotR: 2.8 })}</g>`;

  /* ================================================================ 左欄 ① 兩片偏光板 ＝ 一道光閥（小示意，留在 SVG 裡） */
  function valve(ry, on) {
    const rods = [];
    for (let i = 0; i < 5; i++) rods.push(fx.molecule(84 + i * 11, ry + 15, 4.6, 2, on ? -45 : 0, 'var(--dg-pn-rod)'));
    const hatch = (x, vert) => {
      const d = [];
      if (vert) for (let k = 0; k < 4; k++) d.push(`M${x + 1.6 + k * 1.8},${ry + 2} v26`);
      else for (let k = 0; k < 7; k++) d.push(`M${x + 1},${ry + 3 + k * 4} h6`);
      return `<path d="${d.join(' ')}" stroke="var(--dg-pn-line)" stroke-width=".9" fill="none"/>`;
    };
    return `<g pointer-events="none">
      ${fx.glass(24, ry, 18, 30, { fill: 'var(--dg-pn-led)', rx: 3 })}
      <path class="flow fast" d="M44,${ry + 15} H54" stroke="var(--dg-accent-2d)" stroke-width="2" fill="none"/>
      ${R(56, ry, 8, 30, 'var(--dg-pn-pol)', '', 1.5)}${hatch(56, true)}
      <path class="flow fast" d="M66,${ry + 15} H76" stroke="var(--dg-accent-2d)" stroke-width="2" fill="none"/>
      ${fx.glass(78, ry, 58, 30, { fill: 'var(--dg-pn-lc)', rx: 2 })}${rods.join('')}
      <path class="flow fast" d="M138,${ry + 15} H148" stroke="${on ? 'var(--dg-accent-2d)' : 'var(--dg-mute)'}" stroke-width="2" fill="none"/>
      ${R(150, ry, 8, 30, 'var(--dg-pn-pol)', '', 1.5)}${hatch(150, false)}
      ${on ? `<path class="flow fast" d="M160,${ry + 15} H178" stroke="var(--dg-accent-2d)" stroke-width="2.4" fill="none"/>`
        : `<path d="M161,${ry + 9} l10,12 M171,${ry + 9} l-10,12" stroke="var(--dg-err)" stroke-width="2" fill="none"/>`}
      ${R(184, ry + 3, 24, 24, on ? 'var(--dg-pn-refl)' : 'var(--dg-pn-ic)', '', 4)}
      <text class="lbl" x="214" y="${ry + 20}">${on ? '亮' : '暗'}</text></g>`;
  }

  /* ================================================================ 左欄 ② 顏色是「濾」出來的（小示意） */
  const filt = (y0) => {
    const col = ['var(--dg-pn-r)', 'var(--dg-pn-g)', 'var(--dg-pn-b)'], nm = ['紅', '綠', '藍'];
    return `<g pointer-events="none">` + col.map((c, i) => {
      const y = y0 + i * 17;
      return `<path class="flow slow" d="M26,${y} H70" stroke="var(--dg-pn-refl-d)" stroke-width="2" fill="none"/>`
        + R(72, y - 7, 16, 14, c, '', 2) + R(88, y - 7, 2.6, 14, 'var(--dg-pn-bm)')
        + `<path class="flow slow" d="M92,${y} H128" stroke="${c}" stroke-width="2.4" fill="none"/>`
        + `<text class="sub" x="134" y="${y + 4}">只有${nm[i]}色過得去</text>`;
    }).join('') + `</g>`;
  };

  /* ================================================================ 章節 ② 一個像素放大（R／G／B 並排、不是疊三層）＋ 液晶兩種排列 */
  const pixels = (X0, Y0) => {
    const col = ['var(--dg-pn-r)', 'var(--dg-pn-g)', 'var(--dg-pn-b)'];
    const SW = 20, SH = 42, BMW = 4;
    const a = [R(X0 - BMW, Y0 - BMW, 3 * (3 * SW + 3 * BMW) + BMW, 2 * (SH + BMW) + BMW, 'var(--dg-pn-bm)')];
    for (let r = 0; r < 2; r++) for (let p = 0; p < 3; p++) for (let s = 0; s < 3; s++) {
      const x = X0 + p * (3 * SW + 3 * BMW) + s * (SW + BMW), y = Y0 + r * (SH + BMW);
      a.push(`<rect x="${x}" y="${y}" width="${SW}" height="${SH}" fill="${col[s]}" opacity="${0.55 + 0.15 * ((r + s + p) % 3)}"/>`);
      a.push(R(x + 1.5, y + SH - 9, 7.5, 7.5, 'var(--dg-pn-ic)', '', 1));   // 每一個子像素角落一顆薄膜電晶體
    }
    const gx = [], gy = [];
    for (let r = 0; r <= 2; r++) gx.push(`M${X0 - BMW},${Y0 + r * (SH + BMW) - BMW / 2} H${X0 + 3 * (3 * SW + 3 * BMW)}`);
    for (let p = 0; p < 3; p++) for (let s = 0; s < 3; s++) gy.push(`M${X0 + p * (3 * SW + 3 * BMW) + s * (SW + BMW) - BMW / 2},${Y0 - BMW} V${Y0 + 2 * (SH + BMW)}`);
    a.push(`<path d="${gx.join(' ')}" stroke="var(--dg-pn-tft)" stroke-width="2.2" fill="none"/>`);
    a.push(`<path d="${gy.join(' ')}" stroke="var(--dg-pn-cof)" stroke-width="1.6" fill="none"/>`);
    return a.join('');
  };
  function cell(x0, GT, on) {
    const GB = GT + 44, rods = [];
    for (let i = 0; i < 7; i++) rods.push(fx.molecule(x0 + 16 + i * 15, (GT + GB) / 2, 11, 3.6, on ? -90 : -12, 'var(--dg-pn-rod)'));
    return `<g>
      ${fx.glass(x0, GT - 16, 124, 16, { fill: 'var(--dg-pn-glass)', rx: 2 })}
      ${R(x0, GT, 124, GB - GT, 'var(--dg-pn-lc)')}${rods.join('')}
      ${R(x0 + 58, GT, 6, GB - GT, 'var(--dg-pn-refl-d)')}
      ${R(x0, GT, 9, GB - GT, 'var(--dg-pn-bef-d)')}${R(x0 + 115, GT, 9, GB - GT, 'var(--dg-pn-bef-d)')}
      ${fx.glass(x0, GB, 124, 16, { fill: 'var(--dg-pn-glass)', rx: 2 })}
      <path d="M${x0 + 128},${GT} V${GB}" stroke="var(--dg-accent-2d)" stroke-width="1.2" fill="none"/>
      <path d="M${x0 + 125},${GT + 3} l3,-3 l3,3 M${x0 + 125},${GB - 3} l3,3 l3,-3" stroke="var(--dg-accent-2d)" stroke-width="1.2" fill="none"/></g>`;
  }
  // 章節 ③ LCD 與 OLED 疊層對照
  function mini(x0, rows, y0) {
    let y = y0;
    return rows.map(([h, c, tag]) => {
      const g = R(x0, y, 78, h, c) + `<rect x="${x0}" y="${y}" width="78" height="${h}" fill="none" stroke="var(--dg-pn-line2)" stroke-width=".8"/>`
        + (tag ? `<rect x="${x0 - 3}" y="${y - 2}" width="84" height="${h + 4}" fill="none" stroke="var(--dg-warn)" stroke-width="1.6" stroke-dasharray="4 3"/>` : '');
      y += h; return g;
    }).join('');
  }

  /* ================================================================ 整張圖 */
  function panelStack() {
    const shadows = fx.shadows(ORDER.map(plateShadow).join(''));
    const tex = { pol_up: texPolUp(), glass_up: texGlassUp(), cf: texCf(), lc: texLc(), tft: texTft(), glass_lo: texGlassLo(), pol_lo: texPolLo(),
      bef2: texBef2(), bef1: texBef1(), diff: texDiff(), lgp: texLgp(), refl: texRefl(), bezel: '' };
    /* 每一層＝一片玻璃板 ＋ 頂面上的表面長相。背光那六片共用一個零件身分 pn_backlight（一個模組），LED 燈條與驅動 IC 各自獨立。*/
    const layers = ORDER.map(k => { const o = L[k];
      return `<g data-seg="${o.seg}" data-part="${o.part}">${plate(k, tex[k])}${k === 'lgp' ? texLgpFront() : ''}${k === 'glass_lo' ? driver() : ''}</g>`
        + (k === 'lgp' ? ledBar() : ''); }).join('');
    const [a1x, a1y] = ancR('pol_up'), [a2x, a2y] = ancR('glass_up'), [a3x, a3y] = ancR('cf'), [a4x, a4y] = ancR('lc'), [a5x, a5y] = ancR('tft'), [a7x, a7y] = ancR('pol_lo');
    const o6 = L.glass_lo, a6x = o6.x + (W + 25) + .5 * DX, a6y = o6.y + .5 * DY - 8;
    const lcdMini = mini(60, [[7, 'var(--dg-pn-pol)'], [13, 'var(--dg-pn-glass)'], [7, 'var(--dg-pn-cf)'], [9, 'var(--dg-pn-lc)', 1], [13, 'var(--dg-pn-glass)'], [7, 'var(--dg-pn-pol)'], [26, 'var(--dg-pn-lgp)', 1]], 866);
    const oledMini = mini(210, [[7, 'var(--dg-pn-pol)'], [9, 'var(--dg-pn-glass)'], [11, 'var(--dg-pn-org)'], [13, 'var(--dg-pn-glass)']], 866);

    return `<svg class="dg dgm rs dgpn" viewBox="0 0 ${CW} 1900" width="100%" style="display:block">${STYLE}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <style>
        /* 描邊與發光各降一階（只作用在這一張圖）。這張圖 13 片玻璃板都有自己的細邊（.fxe），共用的 2.2px 描邊套上去
           整疊會變成一團橘色線框 —— 那正是 Andy 講過三次的「螢光感太重」。
           平時／同環節：不描邊；滑過去 1.4px；你點的那一個 2.4px ＋ 一圈暈開（閱讀模式 --dg-glow:none 就不暈）。*/
        svg.dgpn [data-seg] .part{stroke-width:0}
        svg.dgpn [data-seg].sel .part{stroke-width:0;filter:none}
        svg.dgpn [data-seg]:hover .part{stroke-width:1.4;filter:none}
        svg.dgpn [data-seg].sel-part .part{stroke-width:2.4;filter:var(--dg-glow,drop-shadow(0 0 5px var(--cc)))}
        /* 這張圖掛在 panel 族群的頁面上，預設狀態就是「族群已選」：panel_mfg 的零件全部 .sel、display_material 被壓暗 ——
           被壓暗的正好是兩片玻璃基板，.3 讀不到，放寬到 .55（跟 ABF 同一階）。*/
        svg.dgpn [data-seg].dim{opacity:.55}
        .dgwrap:has(svg.dgpn) .dgc.dim{opacity:.55}
        /* 有人被點著時，同環節其餘零件退一階 —— 不退的話「點一層」會變成「13 層一起亮」，跟沒點長得一樣。*/
        svg.dgpn.haspart [data-seg].sel:not(.sel-part){opacity:.55}
        svg.dgpn .pulse{animation:dgpulse 1.8s ease-in-out infinite}
        @keyframes dgpulse{50%{opacity:.35}}
      </style>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead，SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">面板疊層：一片 TFT-LCD 從背光到偏光板，疊了十三層</text>
      <text class="cap ext" x="0" y="0">中間把十三層一片一片拆開浮著看（由下往上：背光模組 → 下偏光板 → 下玻璃 TFT 陣列 → 液晶 → 彩色濾光片 → 上玻璃 → 上偏光板）。背光上來的是一道白光，穿過上玻璃的色阻之後才變成紅／綠／藍三道（可用「動畫」鈕停）。左邊兩個框講原理，右邊卡片逐層說明；放大圖、OLED 對照、製程與族群九檔收在下面三段。</text>

      <!-- ================= §1 左欄 ① 兩片偏光板 ＝ 一道光閥 ================= -->
      <text class="cap" x="12" y="22">↑ 觀看者在最上面</text>
      <text class="cap" x="12" y="40">↓ 背光在最下面，光由下往上穿過整疊</text>
      <rect class="frame" x="12" y="54" width="224" height="184" rx="8"/>
      <text class="hd" x="24" y="76">① 兩片偏光板夾著液晶</text>
      <text class="hd" x="24" y="94">　＝ 一道光閥</text>
      <text class="lbl" x="24" y="114">液晶把光轉過去</text>
      ${valve(120, true)}
      <text class="lbl" x="24" y="170">液晶不轉</text>
      ${valve(176, false)}
      <text class="sub" x="24" y="226">方向正交；少一片就擋不掉。</text>

      <!-- ================= §1 左欄 ② 顏色是濾出來的 ================= -->
      <rect class="frame" x="12" y="250" width="224" height="164" rx="8"/>
      <text class="hd" x="24" y="272">② 顏色是「濾」出來的</text>
      <text class="hd" x="24" y="290">　不是背光給的</text>
      ${filt(310)}
      <text class="sub" x="24" y="366">白光上來，上玻璃的色阻讓</text>
      <text class="sub" x="24" y="384">紅的只過紅、綠的只過綠、</text>
      <text class="sub" x="24" y="402">藍的只過藍。</text>

      <!-- ================= §1 中間：等角爆炸層疊（由下往上畫；上面的板子蓋住下面板子的頂面）================= -->
      ${shadows}
      ${layers}
      ${beams()}

      <!-- ================= 說明卡片（HTML）：右欄逐層、左欄背光那兩張 ＋ 一張警語 ================= -->
      ${extRow({ side: 'r', no: 1, seg: S_P, part: 'pn_pol_up', color: COL.pol, ax: a1x, ay: a1y, title: '上偏光板', sub: '貼在上玻璃外側，方向與下偏光板正交' })}
      ${extRow({ side: 'r', no: 2, seg: S_G, part: 'pn_glass_up', color: COL.glass, ax: a2x, ay: a2y, title: '兩片玻璃基板', sub: '★ 台股沒有 TFT 玻璃基板廠，只有外商' })}
      ${extRow({ side: 'r', no: 3, seg: S_P, part: 'pn_cf', color: COL.cf, ax: a3x, ay: a3y, title: '上玻璃：彩色濾光片', sub: '黑色矩陣框住並排的 R／G／B 色阻' })}
      ${extRow({ side: 'r', no: 4, seg: S_P, part: 'pn_lc', color: COL.lc, ax: a4x, ay: a4y, title: '液晶層', sub: '分子靠轉向控制光；盒厚靠間隙物撐住' })}
      ${extRow({ side: 'r', no: 5, seg: S_P, part: 'pn_tft', color: COL.tft, ax: a5x, ay: a5y, title: '下玻璃上的 TFT 陣列', sub: '閘極線與資料線正交成格，一格一顆電晶體' })}
      ${extRow({ side: 'r', no: 6, seg: S_P, part: 'pn_driver', color: COL.ic, ax: a6x.toFixed(1), ay: a6y.toFixed(1), title: '端子區：驅動 IC ＋ COF 軟板', sub: '晶片由 IC 設計廠做，面板廠負責貼合' })}
      ${extRow({ side: 'r', no: 7, seg: S_P, part: 'pn_pol_lo', color: COL.pol, ax: a7x, ay: a7y, title: '下偏光板', sub: '★ 貼在下玻璃外側，不是夾在液晶旁邊' })}
      ${extRow({ side: 'l', no: 8, seg: S_P, part: 'pn_led', color: COL.led, ax: 230, ay: 420, title: 'LED 燈條（側光式）', sub: '在導光板側邊，光從側面進、正面出' })}
      ${extRow({ side: 'l', no: 9, seg: S_P, part: 'pn_backlight', color: COL.bl, ax: 230, ay: 462, title: '背光模組（白光的來源）', sub: '反射片→導光板→擴散片→稜鏡片×2；背光是白的' })}
      ${note({ side: 'l', warn: true, title: '★ 兩個常見的畫錯',
    lines: ['把背光畫成彩色 —— 顏色不是它給的，是上玻璃的色阻濾出來的。', '把 R／G／B 畫成上下疊三層 —— 它們是水平並排的三個子像素。',
      '點零件只會「亮」不會篩成分股；上游 TFT 玻璃基板台股沒有廠（康寧／AGC／NEG）。'] })}

      <text class="cap" x="12" y="486">原創示意圖，非實物比例。疊層厚度為示意：玻璃是零點幾毫米、液晶層只有幾微米，</text>
      <text class="cap" x="12" y="504">畫面比例已誇大兩個數量級；層與層之間的空隙是「拆開來看」，實際是貼合在一起的。</text>
      <text class="cap" x="12" y="522">背光畫的是側光式（LED 在導光板側邊），直下式不在本圖。</text>

      <!-- ================= ② 放大：一個像素 ＋ 液晶兩種排列（預設收合；座標由 wireFolds 量）================= -->
      ${fold('pn2', '② 放大看：一個像素 ＋ 液晶兩種排列', '3×2 個像素的 R／G／B 格柵與電晶體；不加電躺平、加電立起來', `
      <rect class="frame" x="12" y="540" width="312" height="252" rx="8"/>
      <text class="hd" x="26" y="562">③ 放大看：R／G／B 水平並排</text>
      <g data-seg="${S_P}" data-part="pn_pixel">${pixels(34, 580)}</g>
      <text class="sub" x="26" y="694">每一格是一個子像素，角落那顆是它的電晶體。</text>
      <text class="sub" x="26" y="712">橫的閘極線選一列、縱的資料線送電壓，兩者正交。</text>
      <text class="sub" x="26" y="730">黑色矩陣（黑格柵）把子像素框開，擋住漏光。</text>
      <text class="sub" x="26" y="748" style="fill:var(--dg-warn)">圖上畫 3 個像素 × 2 列，</text>
      <text class="sub" x="26" y="766" style="fill:var(--dg-warn)">實際一片面板有數百萬個。</text>

      <rect class="frame" x="336" y="540" width="312" height="252" rx="8"/>
      <text class="hd" x="350" y="562">④ 液晶層：靠「轉向」控制光</text>
      <text class="lbl" x="350" y="584">不加電（初始排列）</text>
      <text class="lbl" x="500" y="584">加電（分子轉向）</text>
      <g data-seg="${S_P}" data-part="pn_lcmol">${cell(350, 604, false)}${cell(500, 604, true)}</g>
      <text class="sub" x="358" y="684">橢球＝液晶分子（不是圓球、也不是水）。</text>
      <text class="sub" x="358" y="702">中間那根是光阻間隙物，撐住兩片玻璃之間</text>
      <text class="sub" x="358" y="720">的盒厚（典型約 3.7 µm，典型值）；</text>
      <text class="sub" x="358" y="738">兩端是周邊一圈的封框膠。</text>
      <text class="sub" x="358" y="756" style="fill:var(--dg-warn)">哪一邊是亮、哪一邊是暗，依顯示模式</text>
      <text class="sub" x="358" y="774" style="fill:var(--dg-warn)">（TN／VA／IPS）而定，圖上不指定。</text>`)}

      <!-- ================= ③ OLED 對照 ＋ 製程五格 ================= -->
      ${fold('pn3', '③ 換成 OLED 少掉哪幾層 ＋ 製造流程五格', 'LCD／OLED 疊層對照；玻璃基板→Array→CF→Cell→Module', `
      <rect class="frame" x="12" y="820" width="636" height="196" rx="8"/>
      <text class="hd" x="26" y="842">⑤ 換成 OLED 少掉哪幾層</text>
      <g data-seg="${S_P}" data-part="pn_oled">
        <text class="lbl" x="60" y="860">LCD</text><text class="lbl" x="210" y="860">OLED</text>
        ${lcdMini}${oledMini}
        <path class="flow" d="M146,910 H204" stroke="var(--dg-accent-2d)" stroke-width="2" fill="none"/>
      </g>
      <text class="sub" x="320" y="866" style="fill:var(--dg-warn)">虛線框的兩塊 OLED 沒有：背光模組與液晶層。</text>
      <text class="sub" x="320" y="884">OLED 自發光，顏色由有機材料直接給，所以不需要</text>
      <text class="sub" x="320" y="902">背光，也不需要液晶＋兩片偏光板這道光閥。</text>
      <text class="sub" x="320" y="920">它通常仍貼一片圓偏光片，但那是擋反射用的。</text>
      <text class="cap" x="26" y="962">製造流程（三大段併成五格）　★ 陣列（下玻璃）與彩色濾光片（上玻璃）是兩條各自獨立的線，</text>
      <text class="cap" x="26" y="980">到「組立」才合在一起。玻璃基板那一格台股沒有廠（康寧／AGC／NEG）。</text>
      ${processBar(16, 1030, [
        { seg: S_G, t: '玻璃基板', s: '上下兩片玻璃（台股沒有廠）' },
        { seg: S_P, t: 'Array 陣列', s: '成膜→黃光→蝕刻→剝膜' },
        { seg: S_P, t: 'CF 彩色濾光片', s: '黑色矩陣＋R/G/B 色阻' },
        { seg: S_P, t: 'Cell 組立', s: '配向、封框、灌液晶、切割' },
        { seg: S_P, t: 'Module 模組', s: '貼偏光板、接驅動 IC' }], 200, { cols: 3 })}`)}

      <!-- ================= ④ 族群九檔 ＋ 2026 結論 ＋ 示意標示 ================= -->
      ${fold('pn4', '④ 族群九檔各站哪一格 ＋ 2026 年這一格看什麼', '面板廠／背光／偏光板／SMT／電子紙各一行；GCS 與 FOPLP；示意標示', `
      <rect class="frame" x="12" y="1180" width="636" height="168" rx="8"/>
      <text class="hd" x="26" y="1202">「面板產業」族群 9 檔各站在哪一格</text>
      <text class="sub" x="26" y="1226">面板廠（TFT-LCD 本體）：2409 友達、3481 群創、6116 彩晶</text>
      <text class="sub" x="26" y="1244">背光模組／導光板：6176 瑞儀</text>
      <text class="sub" x="26" y="1262">偏光板：8215 明基材、4960 誠美材</text>
      <text class="sub" x="26" y="1280">後段模組 SMT：6278 台表科（近年往記憶體模組、車用、光通訊分散）</text>
      <text class="sub" x="26" y="1298">電子紙（另一種顯示技術，不是 LCD）：8069 元太、6143 振曜</text>
      <text class="sub" x="26" y="1316">驅動 IC 不在這個族群：3034 聯詠等在「顯示驅動 IC」族群（半導體鏈）</text>
      <text class="sub" x="26" y="1334" style="fill:var(--dg-warn)">上游 TFT 玻璃基板台股沒有廠 —— 康寧／AGC／NEG 三家外商</text>

      <rect class="frame" x="12" y="1364" width="636" height="172" rx="8"/>
      <text class="hd" x="26" y="1386">2026 年這一格在看什麼</text>
      <text class="sub" x="26" y="1410">面板報價是循環；一座折舊完的廠 ＋ 一整套在大面積玻璃上做精細線路的能力</text>
      <text class="sub" x="26" y="1428">不是 —— 那套能力正被拿去做封裝用的重佈線層（RDL）。</text>
      <text class="sub" x="26" y="1446">· 友達與康寧合作玻璃核心基板（GCS），友達出 TGV／RDL 製程，規劃 2026 下半年建置試產線。</text>
      <text class="sub" x="26" y="1464">· 群創把既有 LCD 產線轉為扇出型面板級封裝（FOPLP），Chip Last 平台目標 2027 下半年量產。</text>
      <text class="sub" x="26" y="1482">· 彩晶留在顯示本業，主攻車載、工控、無人機等利基應用。</text>
      <text class="sub" x="26" y="1500">兩條路不互斥，圖上各自站在目前查得到具名揭露的那一格；本圖不放任何在手訂單、</text>
      <text class="sub" x="26" y="1518">市占率、營收占比或產能數字。</text>

      <!-- 示意標示（規格書 §5-D，缺一行就退回） -->
      <text class="cap" x="12" y="1556">共通電極、配向層、平坦化層沒有畫：它們的位置與有無依顯示模式（TN／VA／IPS）而異，</text>
      <text class="cap" x="12" y="1574">本輪查不到可引用的定論 —— 寧可不畫，也不要畫一個看起來很專業的錯結構。</text>
      <text class="cap" x="12" y="1592">標示的盒厚與色阻厚度為典型值，實際依機種而異。圖上每一層的面積沒有這樣遞減，是拆開來看。</text>
      <text class="cap" x="12" y="1610">零件顏色＝環節色。點零件只會「亮」不會篩成分股（要篩請點下方的環節色標或族群卡片）。</text>
      <text class="cap" x="12" y="1628">這張圖涵蓋兩個環節：面板 TFT-LCD、面板材料 玻璃基板。</text>
      <text class="cap" x="12" y="1646">驅動 IC 的晶片屬半導體鏈的「顯示驅動 IC」族群（3034 聯詠等），圖上只畫它貼在面板端子區的位置。</text>
      <!-- ★ 2026-09-26 覆蓋普查：這一行原本伸出畫布 105～127px → 拆兩行 -->
      <text class="cap" x="12" y="1664">資料來源與信心度見 docs/diagram_specs/panel_stack.md；</text>
      <text class="cap" x="12" y="1682">本輪補查的來源（含每一條的網址）列在 site/dg/panel.js 檔頭。</text>`)}
    </svg>`;
  }

  window.DG.register('panel', {
    level: 'group', chain: 'electronics',
    name: '面板：TFT-LCD 疊層剖析',
    draw: panelStack,
    native: CW,
    /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。上面那句「不做 3D」的理由今天仍然成立
       —— 一疊**貼在一起**的薄膜轉一圈確實只看得到一塊不透明的平板。
       它漏掉的那一半是：3D 不必把它們貼在一起。整疊**垂直爆炸**拉開之後，
       「兩片偏光板在兩片玻璃的外側而且透光軸正交」「光是從導光板的側邊進來的」
       這兩件事就從剖面上的兩條線變成一眼看得到的空間關係 —— 那正是這張圖的兩個主問題。
       判準跟 DECISIONS #247 同一條：轉一圈能不能多理解一件事，不是 2D 講不講得完。*/
    scene: 'panel',
    q: '一片面板從背光到偏光板疊了哪十三層、為什麼非得要兩片偏光板？換成 OLED 會少掉哪幾層，台股的面板廠、背光模組、偏光板各站在哪一格？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       v2 之後零件的名字不在 SVG 裡（卡片是 HTML），小卡拿不到 text.lbl，所以每一個零件都要自己給 name。
       `cos` 只放 supply_chain 裡真的有的公司；族群裡有、但供應鏈還沒建成環節的（瑞儀、明基材、誠美材、台表科、元太、振曜）
       寫在 `none` 裡明說「有人做、只是還沒建檔」—— 不編一個對應，也不留白讓人以為沒有人做（R4／R5）。*/
    parts: {
      pn_pol_up: { name: '上偏光板', desc: '貼在上玻璃「外側」的偏光片，偏振方向與下偏光板正交。兩片一夾，液晶轉多少、光就過多少 —— 少一片就沒有「擋得掉」這件事。',
        cos: [], none: '偏光板台股有人做：8215 明基材、4960 誠美材（在「面板產業」族群裡），但供應鏈資料還沒把偏光板建成獨立環節，所以這裡列不出來 —— 不是沒有人做。' },
      pn_pol_lo: { name: '下偏光板', desc: '貼在下玻璃「外側」，不是夾在液晶旁邊。它先把背光整理成單一方向的光，液晶轉不轉才決定光到不到得了上偏光板。',
        cos: [], none: '偏光板台股有人做：8215 明基材、4960 誠美材（在「面板產業」族群裡），但供應鏈資料還沒把偏光板建成獨立環節，所以這裡列不出來 —— 不是沒有人做。' },
      pn_glass_up: { name: '彩色濾光片玻璃基板（上玻璃）', desc: '上面那片玻璃，內側做彩色濾光片。面積比下玻璃小 —— 下玻璃多出來的那一條是端子區。',
        none: '★ 台股沒有 TFT 玻璃基板廠：康寧（Corning，美）、AGC（日）、NEG（日）三家外商供應。台玻 1802 做的是建築玻璃與玻纖，不是 TFT 基板。' },
      pn_glass_lo: { name: 'TFT 陣列玻璃基板（下玻璃）', desc: '下面那片玻璃，內側做 TFT 陣列；比上玻璃大，多出的端子區貼驅動 IC。面板廠在這片玻璃上做大面積精細金屬線路的能力，就是它能轉去做封裝 RDL 的本錢。',
        none: '★ 台股沒有 TFT 玻璃基板廠：康寧（Corning，美）、AGC（日）、NEG（日）三家外商供應。台玻 1802 做的是建築玻璃與玻纖，不是 TFT 基板。' },
      pn_cf: { name: '彩色濾光片（黑色矩陣 ＋ R／G／B 色阻）', desc: '做在上玻璃內側。R／G／B 是三個「水平並排」的子像素（不是上下疊三層），黑色矩陣把每一格框起來、擋住漏光。色阻典型厚度約 1.5–1.6 µm（典型值）。顏色是它濾出來的，不是背光給的。' },
      pn_lc: { name: '液晶層', desc: '夾在兩片玻璃之間，典型盒厚約 3.7 µm（典型值）。分子是短棒狀：不加電躺平、加電立起來，通過的光量就不同 —— 液晶是靠「轉向」控制光。畫面裡的光阻間隙物撐住盒厚，周邊一圈封框膠封住。哪一邊亮哪一邊暗依顯示模式（TN／VA／IPS）而定，圖上不指定。' },
      pn_tft: { name: 'TFT 陣列層', desc: '做在下玻璃內側：橫的閘極線選一列、縱的資料線送電壓，兩者正交成格，每一格角落一顆薄膜電晶體開關那一個子像素的像素電極。這就是面板廠「大面積精細線路」的能力所在。' },
      pn_driver: { name: '端子區：驅動 IC ＋ COF 軟板', desc: '下玻璃外露的端子區貼著驅動 IC：COG 是晶片直接壓在玻璃的 ITO 接點上（用異方性導電膠），COF 是壓在軟性電路板上再接過來，軟板往背面折。兩片玻璃錯開就是為了留這條邊。',
        note: '列出來的三家做的是「貼合」這道工序。晶片本身由「顯示驅動 IC」族群（半導體鏈，3034 聯詠等）供應、封測由頎邦等做 —— 這張圖只畫它貼在端子區的位置，不宣稱晶片是面板廠做的。' },
      pn_led: { name: 'LED 燈條（側光式背光的光源）', desc: '在導光板「側邊」的一排白光 LED：光從側面進導光板、被底面網點打散、從正面出來。直下式（LED 在正下方陣列）不在本圖。背光是白的，顏色不是它給的。',
        cos: [], none: '背光模組台股有人做：6176 瑞儀（導光板／擴散板／背光模組，在「面板產業」族群裡），但供應鏈資料還沒把背光模組建成獨立環節，所以這裡列不出來。LED 晶粒屬 LED 族群，本圖不展開。' },
      pn_backlight: { name: '背光模組（白光的來源）', desc: '一疊薄膜，由下往上：背板／膠框 → 反射片 → 導光板（底面有網點，側邊 LED 入光）→ 下擴散片 → 稜鏡片 ×2（兩片正交）。整疊只做一件事：把側邊進來的光變成均勻的白色面光源。',
        cos: [], none: '背光模組台股有人做：6176 瑞儀（導光板／擴散板／背光模組，在「面板產業」族群裡），但供應鏈資料還沒把背光模組建成獨立環節，所以這裡列不出來 —— 不是沒有人做。' },
      pn_pixel: { name: '放大：一個像素（R／G／B 並排）', desc: '3 個像素 × 2 列的放大：每一格是一個子像素，角落那顆是它的電晶體；橫的閘極線、縱的資料線正交；黑色矩陣把子像素框開。實際一片面板有數百萬個。' },
      pn_lcmol: { name: '液晶兩種排列', desc: '不加電（初始排列）與加電（分子轉向）兩種狀態。橢球＝液晶分子；中間那根是光阻間隙物，兩端是封框膠。哪一邊亮依顯示模式而定，圖上不指定。' },
      pn_oled: { name: 'LCD 與 OLED 疊層對照', desc: 'OLED 自發光，顏色由有機材料直接給，所以不需要背光模組，也不需要液晶＋兩片偏光板這道光閥；通常仍貼一片圓偏光片，但那是擋反射用的。這是對照組，不是 LCD 的一部分。',
        cos: [], none: '台股的 OLED 面板廠這一格供應鏈資料沒有建檔；電子紙（8069 元太、6143 振曜）是另一種顯示技術，也不是 OLED。查不到就寫查不到，不編一個對應。' },
    },
  });
})();
