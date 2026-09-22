/* 液冷：冷板 ＋ 均熱板 VC ＋ 熱管 —— docs/diagram_plan.md 的第 5 張
   （族群 `liquid_cooling`、ai_server 鏈）。規格書：docs/diagram_specs/liquid_cooling.md

   ★ 2026-09-22 v2（DECISIONS #238／#239 的最終風格）：
     · 主角改成**垂直爆炸拆解**：冷板連同它底下的晶片一層一層拆開（進出水口 → 上蓋 → 流道 → 底板 →
       TIM2 → 蓋板〔IHS 實心｜VC 真空腔 並排〕→ TIM1 → 裸晶），層與層之間留呼吸空間、
       中軸一條虛線 ＋ 每個間隙一個往上的小熱箭頭，看得出「怎麼疊回去」與「熱往哪走」。
     · 右半邊是**兩個封閉環**：機櫃側（供水分歧管 → 並聯的四個冷板 → 回水分歧管 → CDU 泵）與
       機房側（一次側 FWS），只在板式熱交換器相鄰、絕不相接（§6-L4）。
     · 十一張說明卡片全部外掛成 HTML（`labelRow`／`extRow` 傳 `side`），畫布收到 680 寬；
       其餘（兩相元件剖面、三種做法對照、誰做哪一塊、流程列）收進三段章節（`D.fold()`）。
     · 每張卡片帶 `data-dgcolor`＝那個零件的材質色（銅／TIM／冷側藍／不鏽鋼／液冷青綠／設施灰），
       編號圓點、色條、引線端點一起換色；沒有任何一條發光濾鏡（#239 效能）。

   ★ 型式：2D 剖面爆炸圖 ＋ 2D 迴路示意（**不做真 3D**，規格書 §0 已寫死，`scene: null`）：
     冷板流道、毛細層、蒸氣腔全部「只存在於剖面」，轉一圈看到的都是一塊實心銅盒。

   ★ 名詞陷阱（規格書 §7-B1，本圖最容易被內行人抓到的錯）：
       **均熱片／蓋板（IHS／lid）＝ 實心銅**，內部沒有腔體；
       **均熱板／均溫板（vapor chamber, VC）＝ 真空腔 ＋ 毛細結構**。
     兩者不是同一個東西。所以：
       1. 畫面上一律**雙標**，沒有任何一處只寫「均熱片」三個字就指向 VC（§6-N6）；
       2. 主圖的蓋板那一層就把「實心 IHS」與「空腔 VC」**並排**（§6-P2），章節 ② 再放大對照。

   ★ 與 `air_cooling.js` 是一對，兩張圖不准互相矛盾：
       · 「液冷帶走多少比例的熱」兩張用**同一個字串常數** `SHARE_LINES`（規格書 §7-B3 ＝ air §7-B2）
       · `heatpipe` / `vc` 兩個 data-part 的字串兩張**刻意相同**（規格書 §7-D2）
       · 冷＝進、暖＝出／排 的顏色語意兩張相同（`--dg-cold` / `--dg-hot`）

   ★ 畫面上不准出現的數字（規格書 §6-N1／N4、§7-B2／B4、§7-C）：
       良率、成本、市占率、VC 相對熱管的性能提升百分比、
       GB200 冷板的流量／功率、液冷滲透率（那一個走 YAML 的 source/confidence）。*/
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || !DG.register) return;
  const { STYLE, processBar, extRow, fold, shadow } = DG;

  const SEG = 'thermal';        // 散熱（均熱片 / 液冷）—— ai_server 鏈，YAML 裡查證過存在
  const SEG_A = 'assembly';     // 系統組裝 / 機櫃 —— 只有機櫃襯景與流程列的「設施端」掛它

  /* ★ 兩張圖共用的那一句（規格書 liquid §7-B3 ＝ air §7-B2）。
     兩個來源一個說「冷板移除 70–80%，其餘由風扇處理」、一個說「液冷約做 80%」，
     而且**分母可能不同**（一個是伺服器、一個是機房）。所以寫區間 ＋ 標明分母不一致，
     **不挑一個當定論**。`air_cooling.js` 裡有一份一字不差的複本 —— 改一邊要改另一邊。
     兩行都掛 `data-share`，`scripts/_uitest.py` 的「批次12-散熱」那一段會把兩張圖
     這幾個元素的文字接起來做**字串比對**，不一致就紅（同一個網站不准自打嘴巴）。*/
  const SHARE_LINES = ['多數熱由冷板帶走（公開資料約在 7～8 成之間，', '各來源分母不同），其餘仍靠氣流'];
  const shareText = (x, y) => SHARE_LINES.map((s, i) =>
    `<text class="sub" data-share="1" x="${x}" y="${y + i * 18}">${s}</text>`).join('');

  // 這張圖自己的規則（class），色值一律在 index.html 的 --dg-*（art-director 擁有）
  const VARS = `<style>
    .dgcool .fine{font-size:var(--dg-fs-min,12px);fill:var(--dg-ink-3,#8ea0c4)}
    .dgcool .axis2{stroke:var(--dg-mute);stroke-width:1;stroke-dasharray:3 5;fill:none;opacity:.55}
  </style>`;

  // 零件外框：每一個零件都要有 data-part（規格書 §7-D2：沒有身分就「點誰都一樣」）
  const P = (part, inner, seg) => `<g data-seg="${seg || SEG}" data-part="${part}">${inner}</g>`;
  /* 說明卡片（v2）：卡片離開 SVG 變成 HTML（diagrams.js 的 externalize），畫布上只留編號圓點。
     卡片跟它指的零件**共用同一個 data-part**：點卡片零件亮、點零件卡片亮（同一個身分）。
     `color`＝元件色（data-dgcolor）；地基只把它搬到卡片上，畫布上的錨點吃的是環節色，
     所以這裡順手把同一個值也寫到 .anc 上 —— 圓點、色條、引線端點才會是同一個顏色。*/
  const card = (o) => {
    const s = extRow({ seg: o.seg === null ? undefined : (o.seg || SEG), part: o.part, title: o.title, sub: o.sub,
      no: o.no, side: o.side, ax: o.ax, ay: o.ay, color: o.color, order: o.order, warn: o.warn, note: o.note });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* 流程列補 data-part：規格書 §7-D2 要求每一個 [data-seg] 都要有身分，
     否則 `stampParts` 會自動補「環節 id ＋ 文件順序」，圖上零件一換順序就對不起來。
     共用的 `DG.processBar` 不吃 data-part，所以在呼叫端把 key 注進去。
     （2026-09-22：processBar 卡片化之後開頭變成 `<g class="step lrow" data-seg=`，舊的 regex 對不到，
      main 上這條驗收一直是紅的 —— 這裡改成對新的開頭。）*/
  const pbar = (x, y, steps, w, opts) => {
    let i = 0;
    return processBar(x, y, steps, w, opts)
      .replace(/<g class="step lrow" data-seg="/g, () => `<g class="step lrow" data-part="flow${i++}" data-seg="`);
  };

  // 元件色（卡片、編號圓點、引線端點一起用）—— 全部是 index.html 的 token
  const C = {
    cold: 'var(--dg-cold)', cu: 'var(--dg-cu)', culit: 'var(--dg-cu-lit)', tim: 'var(--dg-tim)',
    steel: 'var(--dg-steel)', cool: 'var(--dg-cool)', fws: 'var(--dg-fws)',
  };

  function liquidCooling() {
    const CW = 680;
    // ================================================================ ① 爆炸拆解：冷板連同晶片一層一層拆開
    /* 2.5D 的斜投影厚度（DX 往右、DY 往上），每一層都是「前面一塊 ＋ 上面一片 ＋ 右邊一片」。
       TIM 的總視覺厚度（6 ＋ 8）仍然比任何金屬層（16 ＋ 8 起跳）薄 —— §6-H2 是用相對厚度驗的。*/
    const DX = 14, DY = 8;
    const slab = (x, y, w, h, front, top, side, cls) =>
      `<path fill="${side}" d="M${x + w},${y}L${x + w + DX},${y - DY}L${x + w + DX},${y + h - DY}L${x + w},${y + h}Z"/>`
      + `<path fill="${top}" d="M${x},${y}L${x + DX},${y - DY}L${x + w + DX},${y - DY}L${x + w},${y}Z"/>`
      + `<rect class="${cls || 'part'}" x="${x}" y="${y}" width="${w}" height="${h}" rx="1.5" fill="${front}"/>`;
    const AX = 170;                                  // 中軸（爆炸拆解的組裝軸）
    const SX = 45, SW = 250;                         // 冷板三層（上蓋／流道／底板）的左緣與寬
    // 每一層的 y（由上往下＝由外到內）。間距不是等距：蓋板那一列上面要放「IHS｜VC 二選一」的標籤
    const Y = { port: 70, lid: 114, fin: 150, base: 210, tim2: 246, cap: 310, tim1: 352, die: 378 };
    const H = { port: 24, lid: 16, fin: 40, base: 16, tim2: 6, cap: 26, tim1: 6, die: 20 };

    // 進出水口：兩根立管（冷色＝進、暖色＝出，§6-H5），箭頭一進一出
    const tube = (cx, col, col2) => `<rect class="part" x="${cx - 12}" y="${Y.port + 4}" width="24" height="${H.port - 4}" rx="2" fill="${col2}"/>`
      + `<ellipse class="part" cx="${cx}" cy="${Y.port + 4}" rx="12" ry="5" fill="${col}"/>`;
    const ports = tube(100, 'var(--dg-cold)', 'var(--dg-cold-2)') + tube(240, 'var(--dg-hot)', 'var(--dg-hot-2)')
      + `<path class="flow fast" d="M100,48V66" stroke="var(--dg-cold)" stroke-width="2.4" fill="none"/><path d="M95,60l5,9l5,-9Z" fill="var(--dg-cold)"/>`
      + `<path class="flow fast" d="M240,66V48" stroke="var(--dg-hot)" stroke-width="2.4" fill="none"/><path d="M235,54l5,-9l5,9Z" fill="var(--dg-hot)"/>`
      + `<text class="fine" x="100" y="42" text-anchor="middle" style="fill:var(--dg-cold)">進水（冷）</text>`
      + `<text class="fine" x="240" y="42" text-anchor="middle" style="fill:var(--dg-hot)">出水（熱）</text>`;
    /* 拆開之後仍然看得出「怎麼接回去」：進水口 → 流道左端、流道右端 → 出水口，兩條虛線畫在上蓋後面
       （進出水口本來就是穿過上蓋的）。流道裡從左到右由冷變熱 —— 「進水冷、出水熱」從流道本身讀出來。*/
    const links = `<path class="flow" d="M100,${Y.port + H.port}V${Y.fin}" stroke="var(--dg-cold)" stroke-width="2" fill="none" opacity=".8"/>`
      + `<path class="flow" d="M240,${Y.fin}V${Y.port + H.port}" stroke="var(--dg-hot)" stroke-width="2" fill="none" opacity=".8"/>`;
    /* 流道：一個 for 迴圈排等距薄鰭（§6-H4 要求 ≥8 條，這裡 12 條）。
       鰭與鰭之間是冷卻液 —— 底下先鋪一層「冷→熱」的水平漸層再把銅鰭疊上去。*/
    const fins = [];
    for (let i = 0; i < 12; i++) fins.push(`<rect x="${SX + 10 + i * 20}" y="${Y.fin}" width="6" height="${H.fin}" fill="var(--dg-cu)"/>`);
    const finLayer = `<path fill="var(--dg-cu-dim)" d="M${SX + SW},${Y.fin}L${SX + SW + DX},${Y.fin - DY}L${SX + SW + DX},${Y.fin + H.fin - DY}L${SX + SW},${Y.fin + H.fin}Z"/>`
      + `<rect class="part" x="${SX}" y="${Y.fin}" width="${SW}" height="${H.fin}" fill="url(#lcFlow)"/>` + fins.join('')
      + `<path class="flow" d="M${SX + 4},${Y.fin + H.fin / 2}H${SX + SW - 4}" stroke="url(#lcFlow)" stroke-width="2" fill="none" opacity=".9"/>`;
    /* 蓋板那一層：左半 ＝ 均熱片／蓋板（IHS，**實心銅**，斜線填滿）、右半 ＝ 均熱板 VC（**真空腔**）。
       ★ 這一列就是名詞陷阱唯一的畫面解藥（§6-P2）：一個實心、一個空的，並排。
       VC 由下到上：下蓋板 → 毛細層 → 蒸氣腔（有支撐柱撐住）→ 毛細層 → 上蓋板（§3-B）。*/
    const IHS = { x: 62, w: 104 }, VC = { x: 174, w: 104 };
    const ihsLayer = slab(IHS.x, Y.cap, IHS.w, H.cap, 'url(#lcSolid)', 'var(--dg-cu-lit)', 'var(--dg-cu-dim)');
    const vcLayer = (() => {
      const x = VC.x, w = VC.w, y = Y.cap;
      const posts = [0, 1, 2, 3, 4].map(i => `<rect x="${x + 14 + i * 20}" y="${y + 8}" width="4" height="10" fill="var(--dg-cu)" opacity=".85"/>`).join('');
      return `<path fill="var(--dg-cu-dim)" d="M${x + w},${y}L${x + w + DX},${y - DY}L${x + w + DX},${y + H.cap - DY}L${x + w},${y + H.cap}Z"/>`
        + `<path fill="var(--dg-cu-lit)" d="M${x},${y}L${x + DX},${y - DY}L${x + w + DX},${y - DY}L${x + w},${y}Z"/>`
        + `<rect class="part" x="${x}" y="${y}" width="${w}" height="${H.cap}" rx="1.5" fill="var(--dg-cu)"/>`
        + `<rect x="${x}" y="${y + 5}" width="${w}" height="3" fill="url(#lcWick)"/>`
        + `<rect x="${x}" y="${y + 8}" width="${w}" height="10" fill="var(--dg-vap)"/>${posts}`
        + `<rect x="${x}" y="${y + 18}" width="${w}" height="3" fill="url(#lcWick)"/>`;
    })();
    // 中軸與每個間隙裡往上走的小熱箭頭（§6-H6：熱全程單向由內往外，沒有往回指的）
    const heatArrows = [Y.die - 8, Y.tim1 - 7, Y.cap - 30, Y.tim2 - 8, Y.base - 8].map((y, i) =>
      `<path class="heat" d="M${AX},${y - 8}l-4.5,8h9Z" fill="var(--dg-hot)" style="animation-delay:${(i * 0.35).toFixed(2)}s"/>`).join('');
    const stack = shadow(`<path class="axis2" d="M${AX},${Y.port - 6}V${Y.die + H.die + 6}"/>${heatArrows}${links}
      ${P('cp_port', ports)}
      ${P('cold_plate', slab(SX, Y.lid, SW, H.lid, 'var(--dg-cu)', 'var(--dg-cu-lit)', 'var(--dg-cu-dim)'))}
      ${P('cp_fin', finLayer)}
      ${P('cold_plate', slab(SX, Y.base, SW, H.base, 'var(--dg-cu)', 'var(--dg-cu-lit)', 'var(--dg-cu-dim)'))}
      ${P('tim2', slab(70, Y.tim2, 200, H.tim2, 'var(--dg-tim)', 'var(--dg-tim)', 'var(--dg-resin)'))}
      <text class="fine" x="${IHS.x + IHS.w / 2}" y="${Y.cap - 12}" text-anchor="middle">IHS（實心）</text>
      <text class="fine" x="${VC.x + VC.w / 2}" y="${Y.cap - 12}" text-anchor="middle">VC（真空腔）</text>
      ${P('ihs', ihsLayer)}${P('vc', vcLayer)}
      ${P('tim1', slab(95, Y.tim1, 150, H.tim1, 'var(--dg-tim)', 'var(--dg-tim)', 'var(--dg-resin)'))}
      ${P('die', slab(110, Y.die, 120, H.die, 'var(--dg-die)', 'var(--dg-si)', 'var(--dg-void)')
      + `<text class="fine" x="${AX}" y="${Y.die + H.die + 20}" text-anchor="middle">裸晶 die（襯景，熱從這裡出發）</text>`)}`);

    // ================================================================ ② 迴路：兩個封閉環，只交換熱、不交換液體
    const RK = { x: 340, y: 84, w: 200, h: 176 };                // 機櫃／托盤（襯景輪廓）
    const MS_X = 368, MR_X = 512, MY0 = 102, MY1 = 240;          // 供水／回水分歧管（垂直主幹）
    const CP = { x: 396, w: 74, h: 20, ys: [112, 146, 180, 214] };
    const CDU = { x: 552, y: 110, w: 118, h: 160 };
    const PHE = { x: 600, y: 138, w: 56, h: 70 };
    const PUMP = { x: 640, y: 242, r: 14 };
    const BND = 676;                                             // 這條線右邊是機房基礎設施（§6-M6）
    /* 快接頭 QD：對插的兩半、端面是平的（§6-M1）。一定成對出現（一進一出，§6-L2）。
       `v` ＝ 畫在垂直管上（兩半上下疊）。*/
    const qd = (x, y, col, v) => v
      ? `<rect x="${x - 6}" y="${y - 7}" width="12" height="6" rx="1.5" fill="var(--dg-steel)"/><rect x="${x - 6}" y="${y + 1}" width="12" height="6" rx="1.5" fill="var(--dg-steel-2)"/>`
        + `<path d="M${x - 6},${y}H${x + 6}" stroke="var(--dg-void)" stroke-width="1.4"/>`
      : `<rect x="${x - 7}" y="${y - 6}" width="6" height="12" rx="1.5" fill="var(--dg-steel)"/><rect x="${x + 1}" y="${y - 6}" width="6" height="12" rx="1.5" fill="var(--dg-steel-2)"/>`
        + `<path d="M${x},${y - 6}V${y + 6}" stroke="var(--dg-void)" stroke-width="1.4"/>`
        + `<path d="M${x - 7},${y}H${x - 11}M${x + 7},${y}H${x + 11}" stroke="${col}" stroke-width="3" stroke-linecap="round"/>`;
    // 並聯支路：每一個冷板各自接到供水與回水分歧管（§6-L3，串聯＝不過）；每個冷板一對 QD
    const branches = CP.ys.map((y) => {
      const cy = y + CP.h / 2;
      return `<path class="flow" d="M${MS_X + 5},${cy}H${CP.x}" stroke="var(--dg-cold)" stroke-width="3" fill="none"/>`
        + `<path class="flow" d="M${CP.x + CP.w},${cy}H${MR_X - 5}" stroke="var(--dg-hot)" stroke-width="3" fill="none"/>`
        + `<rect class="part" x="${CP.x}" y="${y}" width="${CP.w}" height="${CP.h}" rx="3" fill="var(--dg-cu)"/>`
        + `<rect x="${CP.x + 5}" y="${y + 4}" width="${CP.w - 10}" height="${CP.h - 8}" rx="1.5" fill="url(#lcFlow)"/>`
        + [0, 1, 2, 3, 4].map(k => `<rect x="${CP.x + 9 + k * 12}" y="${y + 4}" width="4" height="${CP.h - 8}" fill="var(--dg-cu)"/>`).join('')
        + qd(CP.x - 12, cy, 'var(--dg-cold)') + qd(CP.x + CP.w + 12, cy, 'var(--dg-hot)');
    }).join('');
    /* 板式熱交換器（PHE）：一疊交錯薄板，**兩側顏色由 i % 2 決定** —— 這一行就是 §6-L5。
       中間那條隔板是「兩邊的水不相通」在畫面上的樣子（§6-L4，相接＝直接退回）。*/
    const phe = (() => {
      const n = 7, t = PHE.h / n, a = [];
      for (let i = 0; i < n; i++) a.push(`<rect x="${PHE.x}" y="${(PHE.y + i * t).toFixed(1)}" width="${PHE.w}" height="${(t - 1.2).toFixed(1)}" fill="${i % 2 ? 'var(--dg-fws)' : 'var(--dg-hot)'}" opacity=".85"/>`);
      return a.join('') + `<rect class="part" x="${PHE.x}" y="${PHE.y}" width="${PHE.w}" height="${PHE.h}" rx="3" fill="none"/>`
        + `<path d="M${PHE.x + PHE.w / 2},${PHE.y}V${PHE.y + PHE.h}" stroke="var(--dg-sn)" stroke-width="2.4"/>`;
    })();
    /* 泵：畫在二次側（CDU 內），不是一次側（§6-L6）。
       ⚠ `.dg .spin` 已經是 transform-box:fill-box / origin:center，**不准再寫 transform-origin 像素值**；
         補一個透明同心圓把邊界框撐成正圓，中心才精準落在軸上。*/
    const pump = `<circle class="part" cx="${PUMP.x}" cy="${PUMP.y}" r="${PUMP.r}" fill="var(--dg-frame-f)" stroke="var(--dg-steel-2)"/>`
      + `<g class="spin" style="animation-duration:2.4s"><circle cx="${PUMP.x}" cy="${PUMP.y}" r="10" fill="none"/>`
      + [0, 1, 2, 3, 4].map(i => `<path d="M${PUMP.x},${PUMP.y} L${(PUMP.x + 10 * Math.cos(i * 1.2566 - 0.5)).toFixed(1)},${(PUMP.y + 10 * Math.sin(i * 1.2566 - 0.5)).toFixed(1)} L${(PUMP.x + 10 * Math.cos(i * 1.2566 + 0.2)).toFixed(1)},${(PUMP.y + 10 * Math.sin(i * 1.2566 + 0.2)).toFixed(1)}Z" fill="var(--dg-cold)"/>`).join('')
      + `</g>`;
    /* 二次側封閉環（§6-L1）：泵 → 供水主幹（下面那條）→ 供水分歧管 → 四個冷板（並聯）→ 回水分歧管 →
       回水主幹 → 板式熱交換器 → 回到泵。兩條主幹各有一對 QD（機櫃對 CDU 也是可拆的接點）。
       兩條主幹刻意一條在 y=276、一條在 y=292、垂直段一條 x=596、一條 x=612 —— 互不相交。*/
    const SEC_OUT = `M${PUMP.x - PUMP.r},${PUMP.y}H596V276H${MS_X}V${MY1}`;
    const SEC_IN = `M${MR_X},${MY1}V292H612V${PHE.y + PHE.h}`;
    const PHE2PUMP = `M${PHE.x + PHE.w - 8},${PHE.y + PHE.h}V${PUMP.y - PUMP.r - 10}H${PUMP.x}V${PUMP.y - PUMP.r}`;
    /* 一次側（設施側 FWS）：**比二次側粗**、第三種顏色、只碰到板式熱交換器（§6-L8／L4）。
       它穿過 x=676 那條虛線 —— 虛線右邊就是機房基礎設施，不在這條產業鏈上（§6-M6）。*/
    const primary = `<path class="flow slow" d="M${CW},150H${PHE.x + PHE.w}" stroke="var(--dg-fws)" stroke-width="7" fill="none"/>`
      + `<path d="M${PHE.x + PHE.w + 10},145l-8,5l8,5Z" fill="var(--dg-fws)"/>`
      + `<path class="flow slow" d="M${PHE.x + PHE.w},198H${CW}" stroke="var(--dg-fws-2)" stroke-width="7" fill="none"/>`
      + `<path d="M${CW - 8},193l8,5l-8,5Z" fill="var(--dg-fws-2)"/>`;
    const loop = `<text class="fine" x="${MS_X - 14}" y="80" style="fill:var(--dg-cold)">供水</text>`
      + `<text class="fine" x="${MR_X - 16}" y="80" style="fill:var(--dg-hot)">回水</text>`
      + P('rack', `<rect class="part" x="${RK.x}" y="${RK.y}" width="${RK.w}" height="${RK.h}" rx="8" fill="none" opacity=".55"/>`
        + `<text class="fine" x="${RK.x + 8}" y="${RK.y + RK.h - 4}" style="fill:var(--dg-ink-3)">機櫃／托盤（襯景）</text>`, SEG_A)
      + P('manifold', `<path class="flow" d="${SEC_OUT}" stroke="var(--dg-cold)" stroke-width="5" fill="none" stroke-linejoin="round"/>`
        + `<path class="flow" d="${SEC_IN}" stroke="var(--dg-hot)" stroke-width="5" fill="none" stroke-linejoin="round"/>`
        + `<rect class="part" x="${MS_X - 5}" y="${MY0}" width="10" height="${MY1 - MY0}" rx="5" fill="var(--dg-cold-2)"/>`
        + `<rect class="part" x="${MR_X - 5}" y="${MY0}" width="10" height="${MY1 - MY0}" rx="5" fill="var(--dg-hot-2)"/>`)
      + P('cp_rack', branches)
      + P('qd', qd(596, 262, 'var(--dg-cold)', true) + qd(612, 262, 'var(--dg-hot)', true))
      + P('cdu', `<rect class="part" x="${CDU.x}" y="${CDU.y}" width="${CDU.w}" height="${CDU.h}" rx="8" fill="var(--dg-frame)"/>`
        + `<text class="lbl" x="${CDU.x + 8}" y="${CDU.y + 16}">CDU</text>` + pump
        + `<path class="flow" d="${PHE2PUMP}" stroke="var(--dg-cold)" stroke-width="3" fill="none" stroke-linejoin="round"/>`
        + `<text class="fine" x="${PUMP.x - 34}" y="${PUMP.y + 4}">泵</text>`)
      + P('phe', phe + `<text class="fine" x="${PHE.x - 6}" y="${PHE.y - 6}">板式熱交換器</text>`)
      + primary
      + `<path d="M${BND},${CDU.y + 4}V${CDU.y + CDU.h}" stroke="var(--dg-mute)" stroke-width="1.6" stroke-dasharray="6 5" fill="none"/>`
      + `<text class="fine" x="618" y="288" style="fill:var(--dg-mute)">機房側 →</text>`
      /* 動畫只做一件事（規格書 §9）：一顆冷卻液粒子沿迴路跑 —— 冷的那一顆從泵跑到冷板、
         熱的那一顆從冷板跑回熱交換器；零件本身不准跑來跑去。SMIL 由 industry.js 的 pauseAnimations 管。*/
      + `<circle r="4" fill="var(--dg-cold)" opacity=".95"><animateMotion dur="5s" repeatCount="indefinite" path="M${PUMP.x - PUMP.r},${PUMP.y}H596V276H${MS_X}V156H${CP.x}"/></circle>`
      + `<circle r="4" fill="var(--dg-hot)" opacity=".95"><animateMotion dur="5s" begin="2.5s" repeatCount="indefinite" path="M${CP.x + CP.w},156H${MR_X}V292H612V${PHE.y + PHE.h}"/></circle>`;

    // ================================================================ 章節 ②：兩相元件剖面（四格，2×2）
    const CELL = { w: 324, h: 164, y0: 484 };
    const cx0 = (i) => 16 + (i % 2) * 332, cy0 = (i) => CELL.y0 + Math.floor(i / 2) * 176;
    const cellFrame = (i, t) => `<rect class="frame" x="${cx0(i)}" y="${cy0(i)}" width="${CELL.w}" height="${CELL.h}" rx="8"/>`
      + `<text class="hd" x="${cx0(i) + 14}" y="${cy0(i) + 22}">${t}</text>`;
    const cellText = (i, lines) => lines.map((s, k) =>
      `<text class="fine" x="${cx0(i) + 14}" y="${cy0(i) + 118 + k * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join('');
    /* 格 ① 均熱片／蓋板（IHS，**實心銅**）—— 斜線填滿代表「裡面是實心的」。與格 ② 並排（§6-P2）。*/
    const ihsCell = P('ihs_cmp', cellFrame(0, '① 均熱片／蓋板（IHS，實心銅）')
      + `<rect class="part" x="${cx0(0) + 24}" y="${cy0(0) + 44}" width="${CELL.w - 48}" height="30" rx="3" fill="url(#lcSolid)"/>`
      + `<rect x="${cx0(0) + 126}" y="${cy0(0) + 74}" width="72" height="9" rx="2" fill="var(--dg-tim)"/>`
      + `<rect x="${cx0(0) + 136}" y="${cy0(0) + 83}" width="52" height="14" rx="2" fill="var(--dg-die)"/>`
      + cellText(0, ['內部沒有腔體，熱靠銅的傳導擴散', '★ 這一片才叫「均熱片」', '裸晶 → TIM1 → 實心銅蓋板']));
    /* 格 ② 均熱板 VC（vapor chamber，**真空腔**）：下蓋板 → 毛細層 → 蒸氣腔 → 支撐柱 → 上蓋板。
       液體在毛細層、蒸氣在中央空腔、**兩者箭頭反向**（§6-P3）；腔體不准畫滿液體（§6-P4）；
       **VC 有支撐柱、熱管沒有**（§6-P5）。*/
    const vcCell = (() => {
      const x = cx0(1) + 18, w = CELL.w - 36, y = cy0(1) + 40;
      const posts = [];
      for (let i = 0; i < 7; i++) posts.push(`<rect x="${(x + 24 + i * 38).toFixed(1)}" y="${y + 13}" width="6" height="22" rx="1" fill="var(--dg-cu)" opacity=".85"/>`);
      return P('vc_cmp', cellFrame(1, '② 均熱板 VC（vapor chamber）')
        + `<rect class="part" x="${x}" y="${y}" width="${w}" height="8" rx="2" fill="var(--dg-cu)"/>`
        + `<rect x="${x}" y="${y + 8}" width="${w}" height="5" fill="url(#lcWick)"/>`
        + `<rect x="${x}" y="${y + 13}" width="${w}" height="22" fill="var(--dg-vap)"/>${posts.join('')}`
        + `<rect x="${x}" y="${y + 35}" width="${w}" height="5" fill="url(#lcWick)"/>`
        + `<rect class="part" x="${x}" y="${y + 40}" width="${w}" height="8" rx="2" fill="var(--dg-cu)"/>`
        + `<path class="flow" d="M${x + 40},${y + 20}H${x + w - 40}" stroke="var(--dg-hot)" stroke-width="2.4" fill="none"/>`
        + `<path d="M${x + w - 46},${y + 16}l8,4l-8,4Z" fill="var(--dg-hot)"/>`
        + `<path class="flow rev" d="M${x + w - 40},${y + 31}H${x + 40}" stroke="var(--dg-cold)" stroke-width="2.4" fill="none"/>`
        + `<path d="M${x + 46},${y + 27}l-8,4l8,4Z" fill="var(--dg-cold)"/>`
        + `<rect x="${x + 118}" y="${y + 48}" width="52" height="12" rx="2" fill="var(--dg-die)"/>`
        + cellText(1, ['真空腔 ＋ 少量工作流體 ＋ 毛細層', '→ 蒸氣往冷端、← 液體在毛細層回流', '★ 有支撐柱撐住真空，不被壓扁']));
    })();
    /* 格 ③ 熱管剖面：管壁 → 毛細層 → 中央蒸氣通道。**沒有支撐柱**（圓管靠管壁自己撐）。*/
    const hpCell = (() => {
      const x = cx0(2) + 18, w = CELL.w - 36, y = cy0(2) + 46;
      return P('heatpipe', cellFrame(2, '③ 熱管（heat pipe）剖面')
        + `<rect class="part" x="${x}" y="${y}" width="${w}" height="48" rx="24" fill="var(--dg-cu)"/>`
        + `<rect x="${x + 9}" y="${y + 7}" width="${w - 18}" height="34" rx="17" fill="url(#lcWick)"/>`
        + `<rect x="${x + 15}" y="${y + 14}" width="${w - 30}" height="20" rx="10" fill="var(--dg-vap)"/>`
        + `<path class="flow" d="M${x + 36},${y + 24}H${x + w - 44}" stroke="var(--dg-hot)" stroke-width="2.4" fill="none"/>`
        + `<path d="M${x + w - 50},${y + 20}l8,4l-8,4Z" fill="var(--dg-hot)"/>`
        + `<path class="flow rev" d="M${x + w - 36},${y + 38}H${x + 44}" stroke="var(--dg-cold)" stroke-width="2.4" fill="none"/>`
        + `<path d="M${x + 50},${y + 34}l-8,4l8,4Z" fill="var(--dg-cold)"/>`
        + cellText(2, ['管壁 → 毛細層（液體）→ 中央蒸氣通道', '一端蒸發、另一端凝結，液體靠毛細力回流', '★ 圓管不用支撐柱 —— 有柱子就畫錯了']));
    })();
    // 格 ④ 熱擴散維度：一個是線、一個是面（§6-P8）
    const dimCell = (() => {
      const x = cx0(3) + 18, y = cy0(3) + 40;
      const rings = [0, 1, 2].map(i => `<ellipse cx="${x + 210}" cy="${y + 30}" rx="${16 + i * 15}" ry="${8 + i * 7}" fill="none" stroke="var(--dg-hot)" stroke-width="1.8" opacity="${(0.85 - i * 0.22).toFixed(2)}"/>`).join('');
      return P('dim_cmp', cellFrame(3, '④ 一個是線、一個是面')
        + `<rect x="${x}" y="${y + 22}" width="96" height="16" rx="8" fill="var(--dg-cu)"/>`
        + `<path class="flow" d="M${x + 8},${y + 30}H${x + 88}" stroke="var(--dg-hot)" stroke-width="2.6" fill="none"/>`
        + `<circle cx="${x + 8}" cy="${y + 30}" r="5" fill="var(--dg-hot)"/>`
        + `<text class="fine" x="${x}" y="${y + 60}">熱管：搬到遠處</text>`
        + `<ellipse cx="${x + 210}" cy="${y + 30}" rx="60" ry="28" fill="var(--dg-cu)" opacity=".5"/>${rings}`
        + `<circle cx="${x + 210}" cy="${y + 30}" r="5" fill="var(--dg-hot)"/>`
        + `<text class="fine" x="${x + 160}" y="${y + 60}">VC：就地攤平</text>`
        + cellText(3, ['AI 晶片的熱是「高熱通量的點」，', '所以要先攤平，再交給下一關帶走。', '同樣厚度下 VC 攤平能力較好']));
    })();

    // ================================================================ 章節 ③：兩組對照小圖 ＋ 為什麼一定要走到液冷
    const EY = 860;
    const mini = (x, w, t, a, b, sa, sb, drawA, drawB, part) => P(part,
      `<rect class="frame" x="${x}" y="${EY}" width="${w}" height="150" rx="8"/>`
      + `<text class="hd" x="${x + 14}" y="${EY + 22}">${t}</text>`
      + `<path d="M${x + w / 2},${EY + 32}V${EY + 140}" stroke="var(--dg-frame-s)" stroke-width="1" stroke-dasharray="4 4"/>`
      + `<text class="lbl" x="${x + 14}" y="${EY + 50}">${a}</text>`
      + `<text class="lbl" x="${x + w / 2 + 14}" y="${EY + 50}">${b}</text>${drawA}${drawB}`
      + `<text class="fine" x="${x + 14}" y="${EY + 128}">${sa}</text>`
      + `<text class="fine" x="${x + w / 2 + 14}" y="${EY + 128}">${sb}</text>`);
    const phaseA = [0, 1, 2, 3].map(i => `<rect x="${34 + i * 28}" y="${EY + 76}" width="18" height="14" rx="3" fill="var(--dg-cold)"/>`).join('');
    const phaseB = [0, 1, 2, 3].map(i => `<rect x="${196 + i * 28}" y="${EY + 76}" width="18" height="14" rx="3" fill="${i < 2 ? 'var(--dg-cold)' : 'var(--dg-hot)'}" opacity="${i < 2 ? 1 : .6}"/>`).join('')
      + [0, 1, 2].map(i => `<circle class="pulse" cx="${256 + i * 18}" cy="${EY + 66}" r="4" fill="var(--dg-hot)" style="animation-delay:${i * 0.3}s"/>`).join('');
    const dtcA = `<rect x="358" y="${EY + 86}" width="120" height="10" rx="2" fill="var(--dg-pcb)"/>`
      + `<rect x="384" y="${EY + 68}" width="40" height="18" rx="2" fill="var(--dg-cu)"/>`
      + `<rect x="390" y="${EY + 86}" width="28" height="6" fill="var(--dg-die)"/>`
      + [0, 1, 2].map(i => `<path class="flow" d="M${434 + i * 12},${EY + 100}v-10" stroke="var(--dg-cold)" stroke-width="1.6" fill="none"/>`).join('');
    const dtcB = `<rect x="520" y="${EY + 62}" width="130" height="42" rx="4" fill="var(--dg-vap)" opacity=".85"/>`
      + `<rect x="536" y="${EY + 86}" width="100" height="10" rx="2" fill="var(--dg-pcb)"/>`
      + [0, 1, 2, 3].map(i => `<rect x="${544 + i * 22}" y="${EY + 76}" width="12" height="10" rx="1" fill="var(--dg-die)"/>`).join('')
      + [0, 1, 2, 3, 4].map(i => `<circle class="drop ${i % 3 === 1 ? 'd2' : i % 3 === 2 ? 'd3' : ''}" cx="${532 + i * 26}" cy="${EY + 68}" r="3" fill="var(--dg-cold)"/>`).join('');

    // ================================================================ 說明框（章節 ③④ 共用）
    const noteBox = (x, y, w, h, t, lines, part, extra) => P(part,
      `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="8"/>`
      + `<text class="hd" x="${x + 14}" y="${y + 22}">${t}</text>`
      + lines.map((s, i) => `<text class="sub" x="${x + 14}" y="${y + 46 + i * 18}"${/^★/.test(s) ? ' style="fill:var(--dg-warn)"' : ''}>${s}</text>`).join('')
      + (extra || ''));

    /* ================================================================ 組裝
       `dg1`：`stampParts` 只在「整張圖只有一個 data-seg」時自動掛它，這張有兩個（thermal ＋ assembly），
       所以自己掛 —— 作用是 `--dg-glow:none`（點一個零件不准讓三十幾個群組一起發光，「像電競 RGB」）。
       `rs`：已改造成風格系統（閱讀模式字級升一階、卡片外掛）。
       viewBox 的高度是「全部展開」的靜態版面；收合與章節位置由 wireFolds() 在執行期算。*/
    return `<svg class="dg dgm dgcool dg1 rs" viewBox="0 0 ${CW} 1620" width="100%" style="display:block">${STYLE}${VARS}
      <defs>
        <linearGradient id="lcFlow" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="var(--dg-cold)"/><stop offset="1" stop-color="var(--dg-hot)"/></linearGradient>
        <pattern id="lcSolid" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill="var(--dg-cu)"/><path d="M0,0V8" stroke="var(--dg-cu-cut)" stroke-width="2"/></pattern>
        <pattern id="lcWick" width="6" height="6" patternUnits="userSpaceOnUse">
          <rect width="6" height="6" fill="var(--dg-wick)"/>
          <circle cx="1.6" cy="1.6" r="1.1" fill="var(--dg-void)" opacity=".75"/>
          <circle cx="4.6" cy="4.4" r="1.1" fill="var(--dg-void)" opacity=".75"/></pattern>
      </defs>

      <!-- 標題與說明：v2 搬到 HTML 的 .dghead（跨整個容器寬），SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">液冷：熱從晶片走到機房外面，中間經過哪幾關</text>
      <text class="cap ext" x="0" y="0">熱是接力跑的 —— 晶片 → TIM → 蓋板／VC → 冷板 → 快接頭 → 分歧管 → CDU → 設施側。任何一棒掉了，前面做再好都沒用。</text>
      <text class="cap ext" x="0" y="0">左邊把冷板連同它底下的晶片一層一層拆開（由上往下＝由外到內，熱由下往上走）；右邊是機櫃側與機房側的兩個迴路。兩相元件的剖面、三種做法的對照、誰做哪一塊收在下面三段。</text>
      <text class="cap ext" x="0" y="0">示意圖，非實物比例｜流道密度、毛細層厚度與管徑比例均為示意；圖上畫 4 個冷板代表一櫃數十個，分歧管分支數為示意。</text>

      <!-- ================= §1 主畫面（永遠看得到）：爆炸拆解 ＋ 迴路 ================= -->
      <text class="hd" x="30" y="24">① 拆開看：由外到內，熱由下往上</text>
      <text class="hd" x="${RK.x}" y="24">② 迴路：機櫃側與機房側是兩個封閉環</text>
      ${stack}
      ${loop}

      <!-- 左欄：拆解那一疊（錨點在每一層的左端）；右欄：VC ＋ 迴路（錨點在右端） -->
      ${card({ part: 'cp_port', no: 1, side: 'l', ax: 92, ay: Y.port + 12, color: C.cold, title: '進水冷、出水熱', sub: '溫差就是被帶走的熱；溫差要小，流量就得大' })}
      ${card({ part: 'cold_plate', no: 2, side: 'l', ax: SX + 7, ay: Y.lid + 8, color: C.cu, title: '冷板（cold plate）', sub: '直接貼在晶片上 —— 所以叫「直接晶片液冷 DTC」；底面是平的' })}
      ${card({ part: 'cp_fin', no: 3, side: 'l', ax: SX + 7, ay: Y.fin + 20, color: C.cu, title: '流道：微流道／削切鰭片／柱狀鰭', sub: '鰭越密、接觸面積越大；代價是壓損變大、泵要更用力' })}
      ${card({ part: 'tim2', no: 4, side: 'l', ax: 76, ay: Y.tim2 + 3, color: C.tim, title: '導熱介面材料（TIM1／TIM2）', sub: '兩個固體之間一定有微觀空隙，TIM 把它填掉；很薄，但每一層都要過' })}
      ${card({ part: 'ihs', no: 5, side: 'l', ax: IHS.x + 7, ay: Y.cap + 13, color: C.cu, title: '均熱片／蓋板（IHS，實心銅）', sub: '把點熱源先攤開一點，再交給上面那一關；內部沒有腔體' })}
      ${card({ part: 'vc', no: 6, side: 'r', ax: VC.x + VC.w - 7, ay: Y.cap + 13, color: C.culit, title: '均熱板 VC（vapor chamber）', sub: '跟 IHS 長得像，但裡面是真空腔：靠蒸發—凝結搬熱，不是靠銅傳導' })}
      ${card({ part: 'qd', no: 7, side: 'r', ax: 612, ay: 262, color: C.steel, title: '快接頭 QD（UQD／盲插 UQDB）', sub: '可帶壓拔插、拔開不滴液，一進一出成對出現 —— 最怕漏水的就是這裡' })}
      ${card({ part: 'manifold', no: 8, side: 'r', ax: MS_X, ay: 98, color: C.cold, title: '分歧管（manifold）', sub: '一根主幹 ＋ 多個等距分支，藍＝供水、橘＝回水；是並聯不是串聯' })}
      ${card({ part: 'cdu', no: 9, side: 'r', ax: PUMP.x + PUMP.r, ay: PUMP.y, color: C.cool, title: 'CDU（冷卻液分配單元）', sub: '泵 ＋ 板式熱交換器 ＋ 過濾 ＋ 控制，四個口；泵在機櫃側這一環' })}
      ${card({ part: 'phe', no: 10, side: 'r', ax: PHE.x + PHE.w, ay: PHE.y + PHE.h / 2 + 1, color: C.cool, title: '板式熱交換器：兩邊的水不相通', sub: '機櫃側 TCS 與機房側 FWS 只交換熱、不交換液體 —— 機房的水髒了也流不進 GPU' })}
      ${card({ seg: null, no: 11, side: 'r', ax: BND - 10, ay: 150, color: C.fws, title: '這條線的右邊是機房基礎設施', sub: '一次側（設施水）的管比二次側粗、用第三種顏色，往冷卻水塔／冰水主機去 —— 不在這條產業鏈上，所以不掛環節、不列台股' })}
      ${card({ seg: null, warn: true, note: true, order: 99, side: 'r', title: '點零件篩到的是「供應鏈環節」，不是整個族群', sub: '散熱這一格目前收錄六家；族群「液冷散熱」5 檔裡做快接頭的富世達 6805 不在環節裡，點快接頭列不出它。' })}

      <!-- ================= ② 兩相元件剖面（預設收合；座標由 wireFolds 量） ================= -->
      ${fold('lc2', '② 「均熱片」與「均熱板 VC」是兩種東西 —— 一個實心、一個是真空腔', '實心 IHS、真空腔 VC、熱管三個剖面，以及「線 vs 面」的熱擴散對照', `
        <text class="hd" x="16" y="466">「均熱片」與「均熱板 VC」是兩種東西 —— 一個實心、一個是真空腔；熱管是同一個物理、換成管子</text>
        ${ihsCell}${vcCell}${hpCell}${dimCell}`)}

      <!-- ================= ③ 三種做法對照 ＋ 為什麼一定要走到液冷 ================= -->
      ${fold('lc3', '③ 單相 vs 兩相、DTC vs 浸沒式，以及為什麼一定要走到液冷', '冷板裡有沒有沸騰、整片板泡進液體是另一條路、液冷帶走幾成熱的寫法', `
        ${mini(16, 324, '單相 vs 兩相（冷板裡有沒有沸騰）', '單相', '兩相', '全程是液體，靠溫升', '在冷板裡沸騰，靠潛熱', phaseA, phaseB, 'phase_cmp')}
        ${mini(340, 324, 'DTC vs 浸沒式（另一種做法）', 'DTC 冷板', '浸沒式', '冷板貼最熱的那幾顆', '整片板泡進不導電液', dtcA, dtcB, 'dtc_cmp')}
        ${noteBox(16, EY + 162, 648, 132, '為什麼一定要走到液冷', [
          '晶片功耗一路往上，同樣的面積要散掉更多的熱。',
          '空氣的搬熱能力有上限：要多搬就要更大的風量與風壓，風扇的耗電與噪音等比例上去。',
          '所以最熱的那幾顆（GPU／CPU）先換成冷板直接貼上去，其餘零件仍然靠氣流（詳見「氣冷」那張）。',
        ], 'why_liquid', shareText(30, EY + 162 + 100))}`)}

      <!-- ================= ④ 誰做哪一塊 ＋ 沒有回答的事 ＋ 流程列 ================= -->
      ${fold('lc4', '④ 這張圖上誰做哪一塊、沒有回答的事、五格流程列', '六家各自的主體產品、刻意不寫的數字、晶片端到設施端的五格與那條分界線', `
        ${noteBox(16, 1180, 324, 242, '這張圖上誰做哪一塊（寫「主體是」）', [
          '冷板／分歧管／Sidecar／CDU → 散熱環節。',
          '奇鋐 3017、雙鴻 3324 主體是系統層級',
          '（水冷板、Sidecar、CDU）；',
          '健策 3653、一詮 2486 主體是封裝層級',
          '（均熱片 lid／IHS、補強框）；',
          '高力 8996 是板式熱交換器與 CDM／CDU；',
          '富世達 6805 做快接頭 QD。',
          '★ 2026 年這幾家互相跨線，所以寫「主體是」',
          '　 而不是「只做」。',
          '★ 一次側（冷卻水塔、冰水主機）不在這條鏈上，',
          '　 不掛環節、不列台股。',
        ], 'who')}
        ${noteBox(340, 1180, 324, 242, '這張圖沒有回答的事', [
          '各家的市占率：查不到可查證的公開出處，',
          '一個百分比都不寫。',
          '良率與成本：查不到可引用的公開數字，不編。',
          'VC 相對熱管的性能提升幅度：兩個來源的',
          '比較對象根本不同、被摘要混在同一段裡，',
          '所以只寫定性、不寫百分比。',
          '冷板的流量／功率：來源是經銷商產品頁與',
          '部落格，不是原廠規格，一個數字都不寫。',
          '兩相冷板何時放量：來源只說「目前導入少」，',
          '沒有可引用的時程。',
        ], 'unknown')}
        <text class="cap" x="16" y="1448">熱交給誰、再交給誰（五格）　★ 接點（格 3）一定在 CDU（格 4）之前；格 4 與格 5 之間那條虛線是產業鏈的邊界</text>
        ${pbar(16, 1456, [
          { seg: SEG, t: '晶片端', s: 'die → TIM1 → 蓋板／VC' },
          { seg: SEG, t: '冷板', s: 'TIM2 → 冷板 → 流道' },
          { seg: SEG, t: '接點', s: 'QD → 軟管 → 分歧管' },
          { seg: SEG, t: 'CDU', s: '泵 → 板式熱交換器 → 過濾' },
          { seg: SEG_A, t: '設施端', s: '一次側水 → 屋外散熱' }], 200, { cols: 3 })}
        <path d="M222,1508V1562" stroke="var(--dg-mute)" stroke-width="2" stroke-dasharray="6 5" fill="none"/>
        <text class="fine" x="16" y="1580" style="fill:var(--dg-mute)">左邊是這條產業鏈上的東西</text>
        <text class="fine" x="228" y="1580" style="fill:var(--dg-mute)">右邊是機房基礎設施</text>
        <text class="cap" x="16" y="1606">資料來源與信心度見 docs/diagram_specs/liquid_cooling.md。</text>`)}
    </svg>`;
  }

  window.DG.register('liquid_cooling', {
    level: 'group', chain: 'ai_server',
    name: '液冷：冷板、均熱板 VC 與熱管',
    draw: liquidCooling, native: 680, scene: null,
    q: '熱從 GPU 晶片走到機房外面，中間經過哪幾關？冷板、快接頭、分歧管、CDU 各是誰做的？',
    /* ★ `parts` ＝ 點這個零件時「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       cos 只放代號，而且**只放 supply_chain.yaml 的 companies[].tech 欄自己寫了這個品項的公司**，
       負責什麼一律讀那一欄（R3）。tech 欄沒寫的就不列，改在 note 講清楚為什麼列不出來 ——
       不為了讓卡片好看而湊一個對應（R5）。
       媒體／社群另外提到的（例如報導說雙鴻、奇鋐也做分歧管）寫在 note、標明等級，不進 cos。*/
    parts: {
      cp_port: { name: '進出水口（進水冷、出水熱）', desc: '冷板上面的兩個口，冷卻液從一邊進、帶著熱從另一邊出；進出口的溫差就是被帶走的熱。冷板連同進出口是一件，做冷板的就做它。', cos: ['3017', '3324', '3653'] },
      cold_plate: { name: '冷板（cold plate）', desc: '直接貼在晶片（蓋板）上的液冷主角，銅製、底面平整，這套做法因此叫「直接晶片液冷 DTC」。', cos: ['3017', '3324', '3653'], note: '供應鏈表 tech 欄寫「水冷板」的是奇鋐、雙鴻、健策（健策 2026 起）；建準 2421 也寫了水冷板，但它的主體是風扇，列在氣冷那張。' },
      cp_fin: { name: '冷板內部流道（微流道／削切鰭片／柱狀鰭）', desc: '冷板裡面密排的細鰭，鰭與鰭之間是冷卻液。鰭越密接觸面積越大、帶走的熱越多，代價是壓力損失變大。流道是冷板的一部分，做冷板的就做它。', cos: ['3017', '3324', '3653'] },
      cp_rack: { name: '機櫃裡並聯的冷板', desc: '一櫃裡數十個冷板各自接到供水與回水分歧管（並聯）；圖上畫 4 個是示意。', cos: ['3017', '3324', '3653'] },
      tim1: { name: '導熱介面材料 TIM1（裸晶與蓋板之間）', desc: '兩個固體貼在一起時中間一定有微觀空隙，TIM 把空隙填掉。它很薄，但整條路上每一層都要過。', cos: ['2486'], note: '供應鏈表裡 tech 欄有寫 TIM 的只有一詮（Metal TIM）；其他 TIM 供應商供應鏈表沒有收錄，這裡不補。' },
      tim2: { name: '導熱介面材料 TIM2（蓋板與冷板之間）', desc: '同 TIM1：填掉蓋板與冷板之間的微觀空隙。畫得比上下任何金屬層都薄，它實際上也確實最薄。', cos: ['2486'], note: '供應鏈表裡 tech 欄有寫 TIM 的只有一詮（Metal TIM）；其他 TIM 供應商供應鏈表沒有收錄，這裡不補。' },
      ihs: { name: '均熱片／蓋板（IHS，實心銅）', desc: '蓋在裸晶上的實心銅蓋板，把點熱源先攤開一點再交給上面那一關。內部沒有腔體 —— 這一片才叫「均熱片」，跟均熱板 VC 是兩種東西。', cos: ['3653', '2486', '3324'] },
      ihs_cmp: { name: '均熱片／蓋板（IHS，實心銅）—— 剖面對照', desc: '斜線填滿＝裡面是實心的。熱靠銅的傳導擴散，沒有相變。', cos: ['3653', '2486', '3324'] },
      vc: { name: '均熱板 VC（vapor chamber，真空腔）', desc: '跟 IHS 長得像，但裡面是真空腔＋少量工作流體＋毛細層：靠蒸發—凝結把點熱源攤成一個面，不是靠銅傳導。有支撐柱撐住真空。', cos: ['3017'], note: '供應鏈表 tech 欄寫「3D VC 均熱板」的只有奇鋐；族群「氣冷與核心組件」裡做均溫板的尼得科超眾 6230、泰碩 3338、力致 3483 不在這個環節，點不出來。' },
      vc_cmp: { name: '均熱板 VC（vapor chamber）—— 剖面對照', desc: '下蓋板 → 毛細層（液體回流）→ 蒸氣腔（蒸氣往冷端）→ 支撐柱 → 上蓋板。腔體裡不是滿的液體，是真空＋少量工作流體。', cos: ['3017'], note: '供應鏈表 tech 欄寫「3D VC 均熱板」的只有奇鋐。' },
      heatpipe: { name: '熱管（heat pipe）', desc: '管壁 → 毛細層（液體）→ 中央蒸氣通道。一端吸熱蒸發、另一端放熱凝結，液體靠毛細力爬回來；把熱沿著一條線送走。圓管靠管壁自己撐，沒有支撐柱。', cos: [], none: '散熱環節六家的 tech 欄沒有一家寫熱管。族群「氣冷與核心組件」裡做熱管的尼得科超眾 6230、泰碩 3338、力致 3483 不在這個環節，所以這裡列不出來 —— 這是族群與環節的落差，不是沒人做。' },
      dim_cmp: { name: '熱擴散維度：一個是線、一個是面', desc: '熱管擅長「搬到遠處」（一維），VC 擅長「就地攤平」（二維）。AI 晶片的熱是高熱通量的點，所以要先攤平再帶走。', cos: ['3017'] },
      die: { name: '裸晶 die（襯景）', desc: '熱從這裡出發；上面每一關只是把它往外送一棒。晶片本身不在散熱環節裡，這裡只是襯景。', cos: [], none: '晶片本身不在散熱環節（它是熱的來源），所以這一格不列台股；晶圓代工與封裝在半導體鏈那幾張。' },
      qd: { name: '快接頭 QD（UQD／盲插 UQDB）', desc: '對插的兩半、平面端面，可以帶壓拔插、拔開不滴液，一進一出成對出現。整套系統最怕漏水的就是這裡，OCP 有 UQD／UQDB 兩份通用規格。', cos: [], none: '做水冷快接頭的富世達 6805 在族群「液冷散熱」裡，但不在 supply_chain 的散熱環節裡，所以這一格列不出它 —— 這是族群與環節的落差（規格書 §7-D3 建議交給 Andy 校訂 YAML）。畫面上不寫「通過 UQD 認證」：來源只說它做 QD／UQD，沒有一句話講認證。' },
      manifold: { name: '分歧管（manifold，供水／回水各一根）', desc: '一根主幹 ＋ 多個等距分支，把一路水分給機櫃裡幾十個冷板 —— 是並聯不是串聯，串聯的話後面的晶片會吃到前面加熱過的水。', cos: ['3653'], note: '供應鏈表 tech 欄寫「分歧管」的只有健策（2026-03 起列入系統端名單）。媒體與投資社群另有報導雙鴻、奇鋐也出貨分歧管（WebSearch 摘要等級，未進 YAML），這裡不補進名單。' },
      cdu: { name: 'CDU（冷卻液分配單元）', desc: '泵 ＋ 板式熱交換器 ＋ 過濾 ＋ 控制，四個口（一次側進出、二次側進出）。它是機櫃側與機房側的交界；泵在二次側。', cos: ['3017', '8996'] },
      phe: { name: '板式熱交換器（PHE，CDU 內）', desc: '一疊交錯的波紋薄板，二次側（機櫃側 TCS）與一次側（機房側 FWS）各走一邊，只交換熱、不交換液體 —— 中間那條隔板就是「兩邊的水不相通」。', cos: ['8996'] },
      rack: { name: '機櫃／運算托盤（襯景）', desc: '只畫輪廓，不畫細節；冷板、分歧管、快接頭都裝在它裡面。' },
      phase_cmp: { name: '單相 vs 兩相', desc: '單相：冷卻液全程是液體，靠溫升帶熱。兩相：在冷板裡沸騰，靠汽化潛熱帶熱、晶片表面溫度更平穩，代價是流體管理複雜；來源只說「目前導入少」，沒有可引用的時程。', cos: ['3017', '3324', '3653'] },
      dtc_cmp: { name: 'DTC vs 浸沒式', desc: 'DTC：冷板貼在最熱的那幾顆上，其餘零件仍靠氣流。浸沒式：整片主機板泡進不導電的液體裡。兩者是不同路線，不是同一條路的兩段。', cos: ['3017', '3324', '3653'] },
      why_liquid: { name: '為什麼一定要走到液冷', desc: '晶片功耗一路往上、空氣的搬熱能力有上限，所以最熱的那幾顆先換成冷板。液冷帶走幾成熱：兩個來源的分母不同，畫面只寫區間。', cos: ['3017', '3324', '3653', '8996'] },
      who: { name: '這張圖上誰做哪一塊', desc: '冷板／分歧管／Sidecar／CDU 都在散熱環節；同一格裡系統層級（奇鋐、雙鴻）、封裝層級（健策、一詮）、熱交換器（高力）的主體不同，2026 年互相跨線。' },
      unknown: { name: '這張圖沒有回答的事', desc: '市占率、良率、成本、VC 相對熱管的性能百分比、冷板流量／功率、兩相放量時程 —— 查不到可引用的公開數字，一個都不寫。' },
      flow0: { name: '流程列：晶片端', desc: 'die → TIM1 → 蓋板／VC。封裝層級的均熱片與 VC 在這一格。', cos: ['3653', '2486', '3017'] },
      flow1: { name: '流程列：冷板', desc: 'TIM2 → 冷板 → 流道。', cos: ['3017', '3324', '3653'] },
      flow2: { name: '流程列：接點', desc: 'QD → 軟管 → 分歧管。接點一定在 CDU 之前。', cos: ['3653'], note: '快接頭的富世達 6805 不在散熱環節裡（族群 ≠ 環節）。' },
      flow3: { name: '流程列：CDU', desc: '泵 → 板式熱交換器 → 過濾／控制。', cos: ['3017', '8996'] },
      flow4: { name: '流程列：設施端', desc: '一次側水 → 屋外散熱（冷卻水塔／乾冷器／冰水主機）。這一格右邊是機房基礎設施，不在這條產業鏈上。', cos: [], none: '一次側（冷卻水塔、冰水主機、機房配管）不在這條產業鏈上，圖上只畫到 CDU 為止，所以不列台股。' },
    },
  });
})();
