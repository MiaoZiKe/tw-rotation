/* 多層 PCB 剖面 ＋ 走線 ＋ 銅箔 —— docs/diagram_plan.md 的第 2 張（族群 `pcb_rigid`、ai_server 鏈）

   規格書＝合約：docs/diagram_specs/pcb_stackup.md
     · §0 已經把「要不要 3D」寫死：**不做真 3D**，`scene` 留 null。
       理由是那份規格書逐項對過「轉一圈會不會多理解一件事」—— 疊構、對稱、走線、
       四種孔、銅箔稜面，五項全部是「不會」，其中走線與稜面轉了還更糟。
     · §7-C 列了八條查不到的東西（良率、成本、市佔、線寬、Df 區間、稜面 Rz、
       背鑽殘餘長度、附著力代價），這張圖**一個數字都不編**，只畫相對關係。
     · §7-B 列了四條來源打架的（CCL 成本比重、90° 轉角、Df 門檻、HTE 全稱），
       畫面上分別用「不寫數字」「不寫絕對句」「不做對照表」「只寫中文」處理。

   ---- 立體語言 ----
   2.5D 等角「切近角」cut-away：把 x≥XC 且 y≥YC 那一塊挖掉，露出兩個切面 ——
     y=YC 的 x–z 主切面：**10 層銅的疊構 ＋ 四種孔並排**（這張圖的決定性特徵）
     x=XC 的 y–z 側切面：同一疊構的另一個方向（降權）
   另外兩個面是板子真正的外緣（也看得到層），同樣降權。頂面留著畫走線與防焊開窗 ——
   「走線是平面的、孔是垂直的」這個關係就不用文字解釋了。

   ---- 這張圖上誰做哪一塊（data-seg，三個都在 supply_chain.yaml 的 ai_server 鏈上）----
     ccl_material  銅箔 / 玻纖布 / 樹脂  → 外層那兩張銅箔、銅箔稜面三格、玻纖織紋小圖
     ccl           CCL 銅箔基板          → core（銅－介電－銅）、prepreg（無銅）
     hdi_pcb       高階 PCB（HDI/高層板）→ 內層線路、參考面、四種孔、防焊、表面處理、走線
   ⚠ 右下角的 IC 載板對照格**不掛任何 data-seg**。
     規格書 §7-D1 原本給的理由（「abf_pcb 是 semiconductor 鏈的 seg，掛上去色標不會亮」）
     **是錯的，已經由 CEO 更正**：`site/industry.js` 的 `CHAIN_EXTRA['ai_server']` 本來就把
     `abf_pcb`／`substrate_material`／`ic_design`… 一起拉進 ai_server 的 `chainSegments()`，
     所以色標會亮、篩選也正常。不掛的真正理由是**一張圖一個主體**：
     這張圖的主體是**硬板**（把零件焊上去的那種），ABF 載板是**另一種板子**
     （把晶片黏上去的），在這裡只是一格對照。對照格掛了 seg，
     「點這張圖的任何一處」都可能跳到另一條產品線的公司，把「這張圖在講什麼」稀釋掉。
     載板本身由第 3 張（`docs/diagram_specs/abf_substrate.md`）專門處理。
   ★ 掛 data-seg 的判準是**兩條同時成立**：① 那個環節在 supply_chain.yaml 真的存在
     ② 它在 `chainSegments()` 回傳的清單裡（本籍鏈 ＋ CHAIN_EXTRA）。
     這張圖用的三個都是 ai_server 本籍，兩條都成立。

   ⚠ `site/index.html` 已經把這個檔的 <script> 寫好了，不要再去動 index.html。*/
(function () {
  'use strict';
  const DG = window.DG;
  if (!DG || typeof DG.register !== 'function') return;   // 共用工具還沒載好就不註冊，不要讓整頁掛掉
  const { IX, IY, px, py, onXZ, onYZ, onTop, labelRow, processBar } = DG;

  const M = 'ccl_material', C = 'ccl', P = 'hdi_pcb';

  /* 這一張多出來的五個材質色。
     ⚠ 位置是暫時的：`--dg-*` 由 art-director 擁有、正式的家在 `site/index.html` 的 :root，
       但這一批不准動 index.html（同時有別人在畫別的圖，一動就撞）。
       所以先定義在這張圖自己的 class 上（只影響 .dgpcb），值與理由寫在回報裡，
       art-director 簽過之後整組搬進 :root，這個 <style> 就可以刪掉。
     為什麼需要新的：既有的 --dg-* 是 MLCC 的材質（陶瓷、鎳、錫、導電樹脂），
     沒有「已固化的芯板介電」「半固化片」「玻纖紗束」「金」這四種，
     而 core 與 prepreg 一眼分不分得開**正是這張圖的成敗**（規格書 §4）。*/
  const CSS = `<style>
    .dgpcb .hair{stroke:var(--dg-ink-3);stroke-width:var(--dg-hair-w,2);fill:none;opacity:.5}
    .dgpcb .mk{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-min,12px);font-weight:700;fill:var(--dg-ink)}
    .dgpcb .mkc{fill:var(--dg-edge);stroke:var(--dg-ink-3);stroke-width:1.2}
  </style>`;

  // ================================================================ 疊構表（§3-A，硬規則就在這張表裡）
  const CU = 3.5, DIE = 12, PP = 10, MSK = 6;
  const LAY = [];
  (function build() {
    let z = 0;
    const put = (kind, h, n) => { LAY.push({ kind, z0: z, h, n: n || 0 }); z += h; };
    put('mask', MSK);
    put('cu', CU, 10);                     // L10（外層銅箔）
    put('pp', PP);
    /* ★ 這個迴圈就是 S1／S2：**core 一定是「銅－介電－銅」三件一組、prepreg 一定沒有銅**。
       寫錯這一行，整張圖就只是一疊有顏色的長條。
       由下往上四片 core：L9/L8、L7/L6、L5/L4、L3/L2，中間各夾一片 prepreg。*/
    for (let i = 4; i >= 1; i--) {
      put('cu', CU, 2 * i + 1);            // core 的下銅面
      put('core', DIE);                    // core 的介電（已固化）
      put('cu', CU, 2 * i);                // core 的上銅面
      put('pp', PP);                       // 兩片 core 之間的膠片
    }
    put('cu', CU, 1);                      // L1（外層銅箔）
    put('mask', MSK);
  })();
  const H = LAY[LAY.length - 1].z0 + LAY[LAY.length - 1].h;   // 145
  const cuOf = (n) => LAY.find(l => l.kind === 'cu' && l.n === n);
  const zc = (n) => { const l = cuOf(n); return l.z0 + l.h / 2; };            // 第 n 層銅的中心 z
  /* 參考面（整片銅）與訊號層（線路）的分派。三條限制同時成立：
       · T3：每一層訊號的上一層或下一層一定是整片銅
       · S4：上下鏡像（L1↔L10、L2↔L9、L3↔L8、L4↔L7、L5↔L6 兩兩同角色）
       · §3-B：背鑽落在 L4、埋孔接 L4↔L7 —— 這兩層必須是**訊號層**才講得通 */
  const PLANE = [2, 5, 6, 9];
  const isPlane = (n) => PLANE.indexOf(n) >= 0;

  // ================================================================ 模型與投影
  const L = 330, W = 140, HH = H;          // 板長（x）、板深（y）、板厚（z，已誇張）
  const XC = 58, YC = 76;                  // 切掉的近角
  const UB = L - XC;                       // 主切面沿 x 的長度 272
  const S = 1.25, CX = 233, CY = 251;       // 等比放大與畫面原點（四邊留白都量過）
  const wx = (u) => +(CX + S * (px(XC, YC) + u * IX)).toFixed(1);            // 主切面局部 (u,v) → 畫面
  const wy = (u, v) => +(CY + S * (py(XC, YC, 0) + u * IY - v)).toFixed(1);
  const ex = +(CX + S * px(L, 0)).toFixed(1);                                 // 右前板邊那條垂直稜線
  const ey = (v) => +(CY + S * (py(L, 0, 0) - v)).toFixed(1);
  const tpx = (x, y) => +(CX + S * px(x, y)).toFixed(1);                      // 頂面模型 (x,y) → 畫面
  const tpy = (x, y) => +(CY + S * py(x, y, HH)).toFixed(1);

  // 四個垂直面：主切面不降權，其餘三個壓暗（主角只有一個）
  const FACES = [
    { open: () => onXZ(XC, YC), umax: UB, dim: 0 },        // 主切面（疊構＋四種孔）
    { open: () => onYZ(XC, YC), umax: W - YC, dim: .2 },   // 側切面
    { open: () => onXZ(0, W), umax: XC, dim: .34 },        // 左前板邊
    { open: () => onYZ(L, 0), umax: YC, dim: .16 },        // 右前板邊
  ];
  /* ★ 量出來的事：疊構裡的每一層在畫面上只有 4~5px 高，而 `.dg [data-seg] .part`
     會給它 2.2px（選取時 3.6px）的環節色描邊 —— 描邊比材質本身還厚，
     第一版整張圖因此變成粉紅條紋、core 與 prepreg 完全分不出來。
     所以**疊構的層一律不掛 .part**：選取的回饋改走群組層級（其餘環節 .dim 壓到 .3、
     說明列底色變深），那在薄層上反而讀得出來。.part 只留給下面那幾格夠大的方塊。*/
  const R = (u0, v0, w, h, fill, cls) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${(+u0).toFixed(1)}" y="${(+v0).toFixed(1)}" width="${(+w).toFixed(1)}" height="${(+h).toFixed(1)}" fill="${fill}"/>`;

  // ================================================================ 四種孔（§3-B，跨距全部寫死）
  /* 每一個孔的定義。`hit` ＝真的接到的銅層（其餘層一律留 clearance，不准跟孔銅連在一起，
     連上去就是短路）。`v0/v1` ＝孔銅在 z 上的跨距。*/
  const VIA = {
    pth: { u: 40, hw: 5, cw: 2.5, v0: 0, v1: HH, hit: [1, 4], stub: 93 },       // L1→L10 貫穿；訊號只到 L4
    bd: { u: 96, hw: 5, cw: 2.5, v0: 88, v1: HH, hit: [1, 4], dhw: 8, dv: 88 }, // 背鑽：由 L10 側鑽掉 88 以下
    blind: { u: 150, hwT: 7, hwB: 4, v0: 125.5, v1: 139, hit: [1, 2] },          // L1→L2，只穿一層介電
    bur: { u: 196, hw: 4, cw: 2.2, v0: 48.5, v1: 96.5, hit: [4, 7] },            // L4→L7，兩端都在內層
  };
  // 某一層銅在某個 u 附近要不要讓位（回傳 [u0,u1] 的禁區清單）
  function gapsFor(l) {
    const g = [], mid = l.z0 + l.h / 2;
    const add = (u, half) => g.push([u - half, u + half]);
    const V = VIA;
    if (V.pth.hit.indexOf(l.n) < 0) add(V.pth.u, V.pth.hw + V.pth.cw + 3);
    if (V.bd.hit.indexOf(l.n) < 0) add(V.bd.u, (mid < V.bd.dv ? V.bd.dhw : V.bd.hw + V.bd.cw) + 3);
    if (V.blind.hit.indexOf(l.n) < 0 && mid > V.blind.v0 && mid < V.blind.v1) add(V.blind.u, V.blind.hwT + 2);
    if (V.bur.hit.indexOf(l.n) < 0 && mid > V.bur.v0 && mid < V.bur.v1) add(V.bur.u, V.bur.hw + V.bur.cw + 3);
    return g;
  }
  // 把 [a,b] 扣掉禁區之後剩下的片段
  function cut(segs, gaps) {
    let out = segs;
    gaps.forEach(([g0, g1]) => {
      const n = [];
      out.forEach(([a, b]) => {
        if (g1 <= a || g0 >= b) { n.push([a, b]); return; }
        if (a < g0) n.push([a, g0]);
        if (b > g1) n.push([g1, b]);
      });
      out = n;
    });
    return out.filter(([a, b]) => b - a > 1.2);
  }
  // 訊號層畫成一段一段的線路（不是整片銅）—— 這是「線路 vs 參考面」一眼的差別
  function traceSegs(seed) {
    const a = []; let u = 4, k = seed;
    while (u < UB - 6) { const w = 22 + ((k * 7) % 5) * 8; a.push([u, Math.min(UB - 4, u + w)]); u += w + 9; k++; }
    return a;
  }

  function copperBand(l, umax, main) {
    const segs = main
      ? cut(isPlane(l.n) ? [[2, UB - 2]] : traceSegs(l.n), gapsFor(l))
      : [[1, umax - 1]];
    return segs.map(([a, b]) => R(a, l.z0, b - a, l.h, 'var(--dg-cu)')).join('');
  }

  function pcbStackup() {
    // ---------------- 頂面：防焊、走線、開窗與焊墊（走線是平面上的事，孔是垂直的事）
    const OPEN = [286, 326, 46, YC];      // 防焊開窗（模型 x0,x1,y0,y1），下緣貼著切邊
    const maskPath = `M0,0 H${L} V${YC} H${XC} V${W} H0 Z `
      + `M${OPEN[0]},${OPEN[2]} H${OPEN[1]} V${OPEN[3]} H${OPEN[0]} Z`;
    const topTrace = `<path d="M20,30 H68 L98,60 V${YC}" stroke="var(--dg-cu)" stroke-width="5" fill="none" stroke-linejoin="round" stroke-linecap="round"/>`
      + `<path d="M120,14 H316" stroke="var(--dg-cu)" stroke-width="4" fill="none" stroke-linecap="round"/>`
      + `<path d="M120,26 H316" stroke="var(--dg-cu)" stroke-width="4" fill="none" stroke-linecap="round"/>`;
    /* 防焊是**半透明有色層**，看得出底下的銅（規格書 §2-11）。
       第一版把走線畫在防焊底下、防焊再蓋 .88 的不透明度 —— 量到的結果是走線完全看不見，
       等於畫了一條沒人看得到的線。改成防焊先畫、走線帶 .8 不透明度壓在上面。*/
    const topMask = `<path d="${maskPath}" fill="var(--dg-pcb)" fill-rule="evenodd" fill-opacity=".92"/>`;
    const topPad = R(OPEN[0], OPEN[2], OPEN[1] - OPEN[0], OPEN[3] - OPEN[2], 'var(--dg-au)');

    // ---------------- 主切面上的四種孔
    const hole = (u, hw, v0, v1) => R(u - hw, v0, hw * 2, v1 - v0, 'var(--dg-edge)');
    const barrel = (u, hw, cw, v0, v1, fill) =>
      R(u - hw - cw, v0, cw, v1 - v0, fill) + R(u + hw, v0, cw, v1 - v0, fill);
    const ring = (u, hw, cw, v, h) => R(u - hw - cw - 4, v, hw * 2 + cw * 2 + 8, h, 'var(--dg-cu)');

    const V = VIA;
    /* ① 機械通孔 PTH：上下都貫穿、兩端都開口（V1）。
       訊號只走到 L4，L4 以下那一截孔銅是**殘端**，單獨用 --dg-err 標出來（V2）。*/
    const pth = hole(V.pth.u, V.pth.hw, 0, HH)
      + barrel(V.pth.u, V.pth.hw, V.pth.cw, V.pth.stub, HH, 'var(--dg-cu)')
      + barrel(V.pth.u, V.pth.hw, V.pth.cw, 0, V.pth.stub, 'var(--dg-err)')
      + ring(V.pth.u, V.pth.hw, V.pth.cw, HH - MSK - CU, CU) + ring(V.pth.u, V.pth.hw, V.pth.cw, MSK, CU)
      + `<path class="blink" d="M${V.pth.u + 13},20 v46 m-4,-6 l4,6 l4,-6" stroke="var(--dg-err)" stroke-width="2" fill="none"/>`;
    /* ② 背鑽：由**背面（L10 側）**進入、鑽頭比原孔大一號、而且**一定留一小段沒鑽乾淨**（V3）。
       工程上鑽不到零 —— 畫成「剛好鑽到訊號層、一點都不剩」就是錯的。*/
    const bd = hole(V.bd.u, V.bd.dhw, 0, V.bd.dv)
      + hole(V.bd.u, V.bd.hw, V.bd.dv, HH)
      + barrel(V.bd.u, V.bd.hw, V.bd.cw, V.bd.dv, HH, 'var(--dg-cu)')
      + barrel(V.bd.u, V.bd.hw, V.bd.cw, V.bd.dv, 93, 'var(--dg-warn)')
      + ring(V.bd.u, V.bd.hw, V.bd.cw, HH - MSK - CU, CU)
      + `<path class="hair" d="M${V.bd.u - V.bd.dhw},2 v${V.bd.dv - 4} M${V.bd.u + V.bd.dhw},2 v${V.bd.dv - 4}" stroke-dasharray="4 3"/>`;
    /* ③ 雷射盲孔：只碰到一個外層、不貫穿、形狀**上寬下窄**（V4）。直筒或畫穿都是錯的。*/
    const blind = `<path d="M${V.blind.u - V.blind.hwT},${V.blind.v1} L${V.blind.u + V.blind.hwT},${V.blind.v1} `
      + `L${V.blind.u + V.blind.hwB},${V.blind.v0} L${V.blind.u - V.blind.hwB},${V.blind.v0} Z" fill="var(--dg-cu)"/>`
      + ring(V.blind.u, V.blind.hwT, 0, HH - MSK - CU, CU);
    /* ④ 埋孔：兩端都不碰任何外層，上下都被介電蓋住（V5）。*/
    const bur = hole(V.bur.u, V.bur.hw, V.bur.v0, V.bur.v1)
      + barrel(V.bur.u, V.bur.hw, V.bur.cw, V.bur.v0, V.bur.v1, 'var(--dg-cu)');

    // ---------------- 訊號跑一次：頂層 → PTH 下到 L4 → 內層走線 → 埋孔 → L7
    const dot = `<circle r="3.2" fill="var(--dg-ink)" opacity=".95"><animateMotion dur="6s" repeatCount="indefinite" `
      + `path="M${V.pth.u},${HH} L${V.pth.u},${zc(4)} L${V.bur.u},${zc(4)} L${V.bur.u},${zc(7)} L${UB - 8},${zc(7)}"/></circle>`;

    // ---------------- 四個面上的層（core／prepreg／銅，一層一層鋪）
    const faceBand = (kind) => FACES.map((f, i) => f.open()
      + LAY.filter(l => l.kind === kind).map(l => kind === 'cu'
        ? copperBand(l, f.umax, i === 0)
        : R(0, l.z0, f.umax, l.h, kind === 'core' ? 'var(--dg-pcb-core)' : 'var(--dg-pp)')).join('')
      + (kind === 'pp'
        // prepreg 裡看得出玻纖織紋（§6-M1 在放大格，這裡是遠看也認得出來的那一半）
        ? LAY.filter(l => l.kind === 'pp').map(l => {
          const t = []; for (let u = 6; u < f.umax - 4; u += 13) t.push(`M${u},${l.z0 + 2} v${l.h - 4}`);
          return `<path d="${t.join('')}" stroke="var(--dg-yarn)" stroke-width="1.4" opacity=".5" fill="none"/>`;
        }).join('') : '')
      + '</g>').join('');

    // 只有主切面有孔與開窗；其餘三個面是外緣，乾乾淨淨
    const mainFace = FACES[0].open();
    const groups = ''
      + `<g data-seg="${C}" data-part="pcb_pp">${faceBand('pp')}</g>`
      + `<g data-seg="${C}" data-part="pcb_core">${faceBand('core')}</g>`
      + `<g data-seg="${P}" data-part="pcb_plane">${FACES.map((f, i) => f.open()
        + LAY.filter(l => l.kind === 'cu' && isPlane(l.n)).map(l => copperBand(l, f.umax, i === 0)).join('') + '</g>').join('')}</g>`
      + `<g data-seg="${P}" data-part="pcb_trace">${FACES.map((f, i) => f.open()
        + LAY.filter(l => l.kind === 'cu' && !isPlane(l.n) && l.n !== 1 && l.n !== 10).map(l => copperBand(l, f.umax, i === 0)).join('') + '</g>').join('')}</g>`
      /* 外層那兩張銅箔（L1／L10）掛 ccl_material：多層板壓合時，**外層的銅是一張銅箔疊上去的**，
         內層的銅則是隨著 core 的兩面覆銅一起進來的。圖形（線路）都是 PCB 廠蝕刻出來的，
         這一點寫在右欄那一列的副標裡，不靠讀者自己猜。*/
      + `<g data-seg="${M}" data-part="pcb_foil">${FACES.map((f, i) => f.open()
        + LAY.filter(l => l.kind === 'cu' && (l.n === 1 || l.n === 10)).map(l => copperBand(l, f.umax, i === 0)).join('') + '</g>').join('')}`
      + '</g>'
      + `<g data-seg="${P}" data-part="pcb_mask">${FACES.map((f, i) => f.open()
        + LAY.filter(l => l.kind === 'mask').map(l => {
          if (i !== 0) return R(0, l.z0, f.umax, l.h, 'var(--dg-pcb)');
          // 防焊在焊墊處**開窗**（S6）：上面一處、下面一處，兩個外面都有防焊
          const op = l.z0 > HH / 2 ? [228, 268] : [158, 198];
          return R(0, l.z0, op[0], l.h, 'var(--dg-pcb)') + R(op[1], l.z0, UB - op[1], l.h, 'var(--dg-pcb)');
        }).join('') + '</g>').join('')}`
      + onTop(HH, topMask) + '</g>'
      + `<g data-seg="${M}" data-part="pcb_foil_top">` + onTop(HH, `<g opacity=".82">${topTrace}</g>`) + '</g>'
      /* 表面處理只出現在**開窗露出來的銅**上，而且順序是銅 → 鎳 → 金（S7／S8）。
         鎳在內、金在外；畫反或畫成整片都是錯的。*/
      + `<g data-seg="${P}" data-part="pcb_enig">${mainFace}`
      + R(228, HH - MSK, 40, 2.2, 'var(--dg-ni)') + R(228, HH - MSK + 2.2, 40, 1.6, 'var(--dg-au)')
      + R(158, MSK - 3.8, 40, 2.2, 'var(--dg-ni)') + R(158, MSK - 5.4, 40, 1.6, 'var(--dg-au)')
      + '</g>' + onTop(HH, topPad) + '</g>'
      + `<g data-seg="${P}" data-part="pcb_pth">${mainFace}${pth}</g></g>`
      + `<g data-seg="${P}" data-part="pcb_backdrill">${mainFace}${bd}</g></g>`
      + `<g data-seg="${P}" data-part="pcb_blind">${mainFace}${blind}</g></g>`
      + `<g data-seg="${P}" data-part="pcb_buried">${mainFace}${bur}</g></g>`
      + mainFace + dot + '</g>'
      + FACES.slice(1).map(f => f.open()
        + `<rect x="0" y="0" width="${f.umax}" height="${HH}" fill="var(--dg-edge)" opacity="${f.dim}" pointer-events="none"/></g>`).join('');

    const iso = `<g transform="translate(${CX},${CY}) scale(${S})">${onTop(HH, `<path d="M0,0 H${L} V${YC} H${XC} V${W} H0 Z" fill="var(--dg-edge)"/>`)}${groups}</g>`;

    // 孔的編號記號（畫在等角群組外面 —— 切面的矩陣是鏡射的，文字放進去會左右相反）
    const mark = (n, u, v, dy) => {
      const x = wx(u), y = wy(u, v) + (dy || 0);
      return `<g pointer-events="none"><circle class="mkc" cx="${x}" cy="${y}" r="10"/>`
        + `<text class="mk" x="${x}" y="${y + 4.5}" text-anchor="middle">${n}</text></g>`;
    };
    const marks = mark('1', VIA.pth.u, HH, -16) + mark('2', VIA.bd.u, HH, -16)
      + mark('3', VIA.blind.u, HH, -16) + mark('4', VIA.bur.u, VIA.bur.v1, -12);

    return `<svg class="dg dgm dgpcb" viewBox="0 0 980 1446" width="100%" style="display:block">${DG.STYLE}${CSS}
      <text class="ttl" x="16" y="26">多層 PCB：一塊板子怎麼疊出來，訊號又是怎麼在裡面被磨掉的</text>
      <text class="cap" x="16" y="46">中間是切開近角的 10 層板 —— 切面上 core（銅－介電－銅）與 prepreg（無銅）交替，四種孔的跨距各不相同。右邊逐層說明，下面是走線、銅箔稜面與玻纖織紋。</text>

      ${iso}${marks}

      <!-- 右欄：逐層說明（引線拉到外側文字框，文字不壓在零件上） -->
      ${labelRow(P, 688, 96, '防焊（solder mask）', '蓋住不該吃錫的銅，焊墊處要開窗', ex, ey(HH - MSK / 2), 268)}
      ${labelRow(P, 688, 150, '表面處理（ENIG＝化鎳浸金）', '露出的銅上：銅 → 鎳 → 金，鎳擋擴散', wx(248), wy(248, HH - MSK + 2), 268)}
      ${labelRow(M, 688, 204, '銅箔（1 oz ≒ 35 µm ≒ 1.4 mil）', '外層這兩張是壓合時才疊上去的', ex, ey(zc(1)), 268)}
      ${labelRow(P, 688, 258, '內層線路（一段一段的）', '覆銅板由 CCL 廠交，線路是 PCB 廠蝕的', ex, ey(zc(3)), 268)}
      ${labelRow(P, 688, 312, '接地／電源平面（整片銅）', '沒有參考面就沒有受控阻抗', ex, ey(zc(5)), 268)}
      ${labelRow(C, 688, 366, '芯板 core（銅－介電－銅）', '已固化、兩面覆銅，CCL 廠賣的就是它', ex, ey(116), 268)}
      ${labelRow(C, 688, 420, '半固化片 prepreg（無銅）', '壓合時受熱受壓流動並固化，把 core 黏起來', ex, ey(72.5), 268)}
      ${labelRow(C, 688, 474, '疊構為什麼一定要上下對稱', '不對稱在迴焊高溫下會翹曲，焊點跟著不良', ex, ey(HH / 2), 268)}

      <!-- 四種孔：並排在同一張剖面上，跨距一眼看得出不同 -->
      <text class="hd" x="16" y="524">四種孔各解決一件事（編號對應圖上的 ①②③④，跨距全部不一樣）</text>
      ${via4()}
      <text class="cap" x="16" y="630">HDI 階數寫成 i+N+i：1+N+1＝外側各一層微孔（多壓合一次、多雷射鑽一次），2+N+2＝兩次循序壓合與兩次雷射，3+N+3＝三次；全部層都用微孔互連叫 any-layer。</text>
      <text class="cap" x="16" y="648">微孔可以是單孔、錯孔（staggered）、疊孔（stacked）或跳孔（skip）—— 疊孔比錯孔貴。增層要用更薄的銅箔（1/3 oz 或 1/2 oz）才維持得住微孔的深寬比。</text>

      <!-- 走線：這一段是平面上的事，所以用頂視／剖面小圖畫 -->
      <text class="hd" x="16" y="674">走線：線寬線距、差動成雙、蛇行等長、轉角</text>
      ${trace4()}

      <!-- 材料：銅箔稜面、玻纖織紋、以及「這不是 PCB」的對照 -->
      <text class="hd" x="16" y="878">材料為什麼會變成瓶頸：損耗從介電（Df）與導體（銅箔稜面）兩邊一起上來</text>
      ${matRow()}

      <!-- 製程（十道併成五格；分界線左邊是 CCL 廠、右邊是 PCB 廠） -->
      <text class="cap" x="16" y="1066">製造流程（併成五格）　★ 壓合一定在鑽孔之前（先鑽好的孔會被流出來的膠填掉）；防焊一定在表面處理之前（反過來金會鍍到整片銅上）</text>
      ${processBar(16, 1076, [{ seg: C, t: '板材', s: '玻纖布＋樹脂＋銅箔壓合' },
      { seg: P, t: '內層線路', s: '曝光 → 顯影 → 蝕刻' },
      { seg: P, t: '疊合 ＋ 壓合 ＋ 鑽孔', s: '機械鑽 ／ 雷射鑽' },
      { seg: P, t: '孔內金屬化 ＋ 外層', s: '鍍銅 → 電鍍 → 防焊' },
      { seg: P, t: '表面處理 ＋ 電測', s: 'ENIG ／ OSP ／ ENEPIG' }], 180)}
      <path class="hair" d="M202,1070V1122" stroke-dasharray="5 4" style="opacity:.85"/>
      <text class="cap" x="16" y="1136">← 這條線的左邊是 CCL 廠（交的是「板材」）　｜　右邊是 PCB 廠（交的是「成品板」）→</text>

      <!-- 兩個結論 -->
      <rect class="frame" x="16" y="1150" width="466" height="150" rx="8"/>
      <text class="hd" x="30" y="1172">層數為什麼一直往上加</text>
      <text class="sub" x="30" y="1194">① 晶片腳位與高速訊號對數變多 → 單層佈不下，只能往上疊。</text>
      <text class="sub" x="30" y="1212">② 每一組高速訊號都要有緊鄰的參考面 → 一層訊號常常配一層</text>
      <text class="sub" x="30" y="1230">　 平面，層數是等比例膨脹的，不是線性加一層。</text>
      <text class="sub" x="30" y="1248">③ 量級：一般伺服器主板 12～14 層 → 16～20 層；AI 伺服器的</text>
      <text class="sub" x="30" y="1266">　 通用基板（UBB）20 層以上；800G 交換器板 20～30 → 36～48 層。</text>
      <text class="cap" x="30" y="1286">來源：媒體報導，2026（不是公司揭露；口徑各家不同，只當量級看）</text>
      <rect class="frame" x="498" y="1150" width="466" height="150" rx="8"/>
      <text class="hd" x="512" y="1172">為什麼瓶頸會落在材料，不在 PCB 廠</text>
      <text class="sub" x="512" y="1194">速度一提高，損耗同時從介電（Df）與導體（銅箔稜面）這兩邊</text>
      <text class="sub" x="512" y="1212">上來，兩邊都要換更好的材料才壓得住。</text>
      <text class="sub" x="512" y="1230">所以板材等級一路往上（M4 → M6 → M7 → M8 → M9），而每升一級，</text>
      <text class="sub" x="512" y="1248">底下的銅箔與玻纖布也要跟著升級（低稜面銅箔、低 Dk 玻纖）。</text>
      <text class="sub" x="512" y="1266" style="fill:var(--dg-warn)">CCL 是 PCB 成本裡最大的一塊單一材料（各來源的百分比差很多，</text>
      <text class="sub" x="512" y="1286" style="fill:var(--dg-warn)">口徑也不一致，所以這張圖一個百分比都不寫）。</text>

      <!-- 誰做哪一塊（零件顏色＝環節色，點下去就是篩那一格） -->
      ${labelRow(M, 16, 1330, '銅箔 / 玻纖布 / 樹脂', 'CCL 的三種原料 —— 稜面與織紋那兩格就是它', null, null, 310)}
      ${labelRow(C, 336, 1330, 'CCL 銅箔基板（core / prepreg）', '把三種原料壓合成板材的那一段', null, null, 310)}
      ${labelRow(P, 656, 1330, '高階 PCB（HDI / 高層板）', '線路、鑽孔、壓合、防焊、表面處理', null, null, 310)}

      <text class="cap" x="16" y="1376">示意圖，非實物比例｜各層厚度比例為示意：圖上畫 10 層銅（4 片 core ＋ 5 片 prepreg），代表實際 20～50 層以上。</text>
      <text class="cap" x="16" y="1394">銅遠薄於介電（1 oz 銅 ≒ 35 µm，介電是數十～百餘 µm 等級）；蝕刻出來的線路剖面實際略呈梯形，這裡畫成矩形是為了可讀性。</text>
      <text class="cap" x="16" y="1412">點零件篩到的是「供應鏈環節」，不是整個族群 —— PCB 硬板族群與「高階 PCB」環節是兩份名單，由 supply_chain.yaml 維護。</text>
      <text class="cap" x="16" y="1430">右下角的 IC 載板對照格屬於半導體鏈，所以不掛環節；每一條事實的來源與信心度見 docs/diagram_specs/pcb_stackup.md。</text>
    </svg>`;
  }

  // ================================================================ 四種孔的說明格
  function via4() {
    const rows = [
      ['1', '機械通孔 PTH ＋ 殘端', 'L1 → L10（上下都貫穿）', '最便宜，但訊號只走到 L4，剩下',
        '那一截孔銅就是一根沒接東西的天線'],
      ['2', '背鑽（back drill）', '由 L10 側鑽到 L4 下方', '鑽頭比原孔大一號，把殘端鑽掉；',
        '工程上鑽不到零，一定留一小段'],
      ['3', '雷射盲孔（micro via）', 'L1 → L2（只穿一層介電）', '上寬下窄的碗狀、不貫穿；',
        '外層才佈得下更密的線'],
      ['4', '埋孔（buried via）', 'L4 → L7（兩端都在內層）', '完全埋在板內，不佔外層面積；',
        '不會留下需要背鑽的殘端'],
    ];
    return rows.map(([n, t, span, s1, s2], i) => {
      const x = 16 + i * 238;
      return `<g data-seg="hdi_pcb" data-part="via_box_${n}">`
        + `<rect class="part" x="${x}" y="${534}" width="230" height="84" rx="7" fill="#0f172b" fill-opacity=".55"/>`
        + `<circle class="mkc" cx="${x + 18}" cy="${552}" r="9"/><text class="mk" x="${x + 18}" y="${556.5}" text-anchor="middle">${n}</text>`
        + `<text class="lbl" x="${x + 32}" y="${556}">${t}</text>`
        + `<text class="tag" x="${x + 12}" y="${576}">${span}</text>`
        + `<text class="sub" x="${x + 12}" y="${594}">${s1}</text>`
        + `<text class="sub" x="${x + 12}" y="${610}">${s2}</text></g>`;
    }).join('');
  }

  // ================================================================ 走線四格（頂視／剖面）
  function trace4() {
    const Y = 682, HGT = 170, DR = Y + 10;      // 框的 y、高、繪圖區起點
    const box = (i) => 16 + i * 238;
    const plane = (x, y, w) => `<rect x="${x}" y="${y}" width="${w}" height="5" fill="var(--dg-cu)"/>`;
    const die = (x, y, w, h) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="var(--dg-pcb-core)"/>`;
    const cells = [];

    // ① 單端 50 Ω：一條線 ＋ 下一層的整片參考面
    let x = box(0);
    cells.push(`<g data-seg="hdi_pcb" data-part="trace_se">`
      + `<rect class="part" x="${x}" y="${Y}" width="230" height="${HGT}" rx="7" fill="#0f172b" fill-opacity=".55"/>`
      + `<rect x="${x + 88}" y="${DR + 8}" width="34" height="6" fill="var(--dg-cu)"/>`
      + die(x + 14, DR + 14, 202, 22) + plane(x + 14, DR + 36, 202)
      + `<text class="tag" x="${x + 14}" y="${DR + 58}">單端 50 Ω</text>`
      + `<text class="lbl" x="${x + 12}" y="${Y + 92}">一條線 ＋ 一個參考面</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 110}">阻抗是「線對下面那片銅」算出</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 126}">來的。50 Ω 不是物理定律，是</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 142}">沿用同軸線的慣例＋製程折衷。</text></g>`);

    // ② 差動 100 Ω：兩條等寬等距（只畫一條就不是差動對）
    x = box(1);
    cells.push(`<g data-seg="hdi_pcb" data-part="trace_diff">`
      + `<rect class="part" x="${x}" y="${Y}" width="230" height="${HGT}" rx="7" fill="#0f172b" fill-opacity=".55"/>`
      + `<rect x="${x + 76}" y="${DR + 8}" width="24" height="6" fill="var(--dg-cu)"/>`
      + `<rect x="${x + 112}" y="${DR + 8}" width="24" height="6" fill="var(--dg-cu)"/>`
      + `<path class="hair" d="M${x + 100},${DR + 4} H${x + 112}" style="opacity:.9"/>`
      + die(x + 14, DR + 14, 202, 22) + plane(x + 14, DR + 36, 202)
      + `<text class="tag" x="${x + 14}" y="${DR + 58}">差動 100 Ω</text>`
      + `<text class="lbl" x="${x + 12}" y="${Y + 92}">永遠成雙，線寬與間距一致</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 110}">兩條一組、等大反向，對外干擾</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 126}">互相抵消。100 Ω 沿用雙絞線的</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 142}">慣例；只畫一條就不是差動對。</text></g>`);

    // ③ 蛇行等長：兩條**一起**繞（只繞其中一條卻標等長是錯的）
    x = box(2);
    const w1 = `M${x + 16},${DR + 14} h22 v-10 h18 v10 h18 v-10 h18 v10 h18 v-10 h18 v10 h22`;
    const w2 = `M${x + 16},${DR + 26} h22 v-10 h18 v10 h18 v-10 h18 v10 h18 v-10 h18 v10 h22`;
    cells.push(`<g data-seg="hdi_pcb" data-part="trace_skew">`
      + `<rect class="part" x="${x}" y="${Y}" width="230" height="${HGT}" rx="7" fill="#0f172b" fill-opacity=".55"/>`
      + `<rect x="${x + 12}" y="${DR + 2}" width="206" height="42" rx="3" fill="var(--dg-cu)" opacity=".16"/>`
      + `<path d="${w1}" stroke="var(--dg-cu)" stroke-width="4" fill="none" stroke-linejoin="round"/>`
      + `<path d="${w2}" stroke="var(--dg-cu)" stroke-width="4" fill="none" stroke-linejoin="round"/>`
      + `<text class="tag" x="${x + 14}" y="${DR + 58}">蛇行等長（底色＝下一層的參考面）</text>`
      + `<text class="lbl" x="${x + 12}" y="${Y + 92}">兩條一起繞，不是只繞一條</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 110}">同一組訊號走不同長度就會先後</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 126}">到達（skew）。等長是對「一組」</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 142}">做的，只繞一條標等長就是錯的。</text></g>`);

    // ④ 轉角：45° 與 90° 並排對照。★ 規格書 §7-B3：不准寫「90° 一定會反射」這種絕對句
    x = box(3);
    cells.push(`<g data-seg="hdi_pcb" data-part="trace_corner">`
      + `<rect class="part" x="${x}" y="${Y}" width="230" height="${HGT}" rx="7" fill="#0f172b" fill-opacity=".55"/>`
      + `<rect x="${x + 12}" y="${DR + 2}" width="206" height="42" rx="3" fill="var(--dg-cu)" opacity=".16"/>`
      + `<path d="M${x + 22},${DR + 10} h34 v26" stroke="var(--dg-cu)" stroke-width="5" fill="none"/>`
      + `<path d="M${x + 120},${DR + 10} h26 l12,12 v14" stroke="var(--dg-cu)" stroke-width="5" fill="none" stroke-linejoin="round"/>`
      + `<text class="tag" x="${x + 28}" y="${DR + 58}">90°</text><text class="tag" x="${x + 128}" y="${DR + 58}">45°</text>`
      + `<text class="lbl" x="${x + 12}" y="${Y + 92}">45° 是好習慣，不是鐵律</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 110}">① 早年酸性蝕刻液會積在直角裡</text>
      <text class="sub" x="${x + 12}" y="${Y + 126}">（現在多改鹼性，已大幅緩解）</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 142}">② 高速下直角的額外電容造成阻抗</text>`
      + `<text class="sub" x="${x + 12}" y="${Y + 158}">不連續；低速或邊緣速率慢時很小</text></g>`);
    return cells.join('');
  }

  // ================================================================ 銅箔稜面／玻纖織紋／IC 載板對照
  function matRow() {
    const Y = 886, HGT = 158;
    // ---- 銅箔稜面三格：粗糙度由左到右遞減（M2），電流貼著表面跑
    const cellW = 88;
    const rough = (x0, y0, amp, step) => {
      const p = [`M${x0},${y0}`]; let up = true;
      for (let u = 0; u < cellW - 12; u += step) { p.push(`l${step / 2},${up ? -amp : amp}`); p.push(`l${step / 2},${up ? amp : -amp}`); up = !up; }
      return p.join(' ');
    };
    const cell = (i, amp, step, name) => {
      const x = 28 + i * (cellW + 10), y = Y + 66;
      return `<rect x="${x}" y="${y - 30}" width="${cellW}" height="30" fill="var(--dg-cu)"/>`
        + `<rect x="${x}" y="${y}" width="${cellW}" height="22" fill="var(--dg-pcb-core)"/>`
        + `<path d="${rough(x, y, amp, step)} L${x + cellW},${y} L${x + cellW},${y + 22} L${x},${y + 22} Z" fill="var(--dg-pcb-core)"/>`
        + `<path d="${rough(x, y - 3, amp, step)}" stroke="var(--dg-accent)" stroke-width="1.6" fill="none" class="pulse"/>`
        + `<text class="tag" x="${x + cellW / 2}" y="${y + 40}" text-anchor="middle">${name}</text>`;
    };
    const foil = `<g data-seg="ccl_material" data-part="foil_rough">`
      + `<rect class="part" x="16" y="${Y}" width="300" height="${HGT}" rx="7" fill="#0f172b" fill-opacity=".55"/>`
      + `<text class="lbl" x="28" y="${Y + 22}">銅箔為什麼要「低稜面」</text>`
      + cell(0, 4, 10, 'HTE') + cell(1, 2.4, 7, 'RTF') + cell(2, 1.1, 5, 'HVLP')
      + `<text class="sub" x="28" y="${Y + 128}">頻率越高，電流越只貼著導體表面跑（集膚</text>`
      + `<text class="sub" x="28" y="${Y + 144}">效應）。表面越粗，電流實際走的路越長。</text></g>`;

    // ---- 玻纖織紋：紗束與膠的介電常數不同，差動對兩條壓在不同介質上就有時間差
    const wv = [];
    for (let i = 0; i < 9; i++) wv.push(`<rect x="${346 + i * 30}" y="${Y + 34}" width="16" height="64" rx="3" fill="var(--dg-yarn)" opacity=".85"/>`);
    for (let j = 0; j < 4; j++) wv.push(`<rect x="${340}" y="${Y + 38 + j * 17}" width="268" height="9" rx="3" fill="var(--dg-yarn)" opacity="${j % 2 ? '.45' : '.62'}"/>`);
    const weave = `<g data-seg="ccl_material" data-part="fiber_weave">`
      + `<rect class="part" x="332" y="${Y}" width="300" height="${HGT}" rx="7" fill="#0f172b" fill-opacity=".55"/>`
      + `<text class="lbl" x="344" y="${Y + 22}">玻纖織效應（fiber weave effect）</text>`
      + `<rect x="340" y="${Y + 32}" width="284" height="68" rx="4" fill="var(--dg-resin)"/>`
      + wv.join('')
      + `<path d="M346,${Y + 48} H616" stroke="var(--dg-cu)" stroke-width="4.5" fill="none"/>`
      + `<path d="M346,${Y + 86} H616" stroke="var(--dg-cu)" stroke-width="4.5" fill="none"/>`
      + `<text class="sub" x="344" y="${Y + 118}">一條壓在紗束上、一條壓在膠（樹脂）上 →</text>`
      + `<text class="sub" x="344" y="${Y + 134}">兩條的等效介電常數不同 → 產生時間差。</text>`
      + `<text class="sub" x="344" y="${Y + 150}">對策：攤平的玻纖布（spread glass）與低 Dk 玻纖。</text></g>`;

    /* ---- IC 載板對照格：**不掛任何 data-seg**。
       理由是「一張圖一個主體」，不是「掛了會壞」——
       `abf_pcb` 其實在 ai_server 的環節清單裡（industry.js 的 CHAIN_EXTRA），掛了色標會亮。
       但這張圖講的是**硬板**，載板是另一種板子、另一批公司，在這裡只是一格對照；
       讓對照格可以點，等於讓人從這張圖跳到另一條產品線。載板由第 3 張圖專門處理。*/
    const abf = `<g pointer-events="none">`
      + `<rect class="frame" x="648" y="${Y}" width="316" height="${HGT}" rx="7"/>`
      + `<text class="lbl" x="660" y="${Y + 22}" style="fill:var(--dg-warn)">這不是 PCB，是 IC 載板</text>`
      + `<rect x="660" y="${Y + 34}" width="290" height="30" rx="3" fill="var(--dg-resin)"/>`
      + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(i => `<rect x="${668 + i * 24}" y="${Y + 38}" width="6" height="6" fill="var(--dg-cu)"/>`).join('')
      + `<text class="sub" x="660" y="${Y + 82}">ABF 積層膜沒有織造玻纖（所以雷射鑽孔不會</text>`
      + `<text class="sub" x="660" y="${Y + 98}">打到紗束），線寬比 PCB 細一個量級，做法是半</text>`
      + `<text class="sub" x="660" y="${Y + 114}">加成（SAP／mSAP）—— 是另一段製程、另一批公司。</text>`
      + `<text class="cap" x="660" y="${Y + 136}">台股在半導體鏈的「IC 載板（ABF / BT）」那一格，</text>`
      + `<text class="cap" x="660" y="${Y + 152}">不要跟這張圖上的 PCB 廠混在一起。</text></g>`;
    return foil + weave + abf;
  }

  window.DG.register('pcb_rigid', {
    level: 'group', chain: 'ai_server',
    name: 'PCB 硬板：多層板剖面與走線',
    draw: pcbStackup, native: 980, scene: null,
    q: '一塊 AI 伺服器用的多層板為什麼要疊到幾十層？訊號在裡面被誰磨掉，瓶頸又為什麼卡在板材與銅箔、而不是 PCB 廠？',
  });
})();
