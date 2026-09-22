/* 多層 PCB 剖面 ＋ 走線 ＋ 銅箔 —— docs/diagram_plan.md 的第 2 張（族群 `pcb_rigid`、ai_server 鏈）

   規格書＝合約：docs/diagram_specs/pcb_stackup.md
     · §0 已經把「要不要 3D」寫死：**不做真 3D**，`scene` 留 null。
       理由是那份規格書逐項對過「轉一圈會不會多理解一件事」—— 疊構、對稱、走線、
       四種孔、銅箔稜面，五項全部是「不會」，其中走線與稜面轉了還更糟。
     · §7-C 列了八條查不到的東西（良率、成本、市佔、線寬、Df 區間、稜面 Rz、
       背鑽殘餘長度、附著力代價），這張圖**一個數字都不編**，只畫相對關係。
     · §7-B 列了四條來源打架的（CCL 成本比重、90° 轉角、Df 門檻、HTE 全稱），
       畫面上分別用「不寫數字」「不寫絕對句」「不做對照表」「只寫中文」處理。

   ---- 2026-09-22 v2（DECISIONS #238／#239／#240 ＋ Andy 晚間的參考圖 docs/diagram_refs/2d_panel_dark_light.webp）----
   · 構圖：層疊類 → **等角爆炸玻璃層疊**。十三片薄板一片一片浮著（上防焊、L1 銅箔、pp、core×4 與 pp×5 交替、L10 銅箔、下防焊），
     每一片都是 D.fx.glass 畫的**帶厚度、圓角、半透明漸層的玻璃板**（頂面 ＋ 前面 ＋ 右側面），層與層之間留 19px 呼吸空間。
     **剖面內容畫在每一片的前緣**：core 的上下兩條銅、訊號層一段一段的線路、參考面整片銅、prepreg 的紗束、四種孔的孔洞與孔銅。
     規格書 §3-A／§3-B 的硬規則一條都沒動（core 一定是銅－介電－銅、prepreg 一定沒有銅、10 層銅上下對稱、銅遠薄於介電、
     四種孔的跨距各不相同、盲孔上寬下窄只穿一層、埋孔不碰外層、背鑽從背面進而且留殘餘）。
     拆開之後多出來的一件事：**孔畫成穿過層間空隙的小銅柱**（這一層的孔接到下一層的銅）；背鑽掉的那一段空隙裡沒有銅柱。
   · 走線頂視小圖畫在 **L1 銅箔那片的頂面**（差動對成雙、蛇行兩條一起繞、45° 轉角）—— 「走線是平面的、孔是垂直的」不用文字解釋。
   · 訊號路徑用 D.fx.beam：一條發光光束（一個 feGaussianBlur）＋ 流動虛線 ＋ 端點光點；柔陰影一組（第二個 blur）。發光預算 2／3。
   · svg 根掛 `.rs`：閱讀模式字級升一階、說明卡片離開 SVG 變成 HTML（extRow 多傳 side）。畫布 980 → **560**，native 跟著改。
   · §1 從 502 壓到約 445：右欄八列說明全部變成卡片（12 張 ＋ 1 張警語），四種孔的說明格、走線四格、材料三格、
     製程五格與兩塊結論收進三個章節（一個字沒刪，只改斷行與位置）。收合 ≈ 445 ＋ 8 ＋ 42×3 ＋ 10 ＝ 589。
   · 卡片與畫布上的零件是同一個 data-part：點卡片亮零件、點零件亮卡片。
   · 卡片元件色（token，不寫死）：銅件 --dg-cu-lit、金 --dg-au、core --dg-weave、prepreg --dg-yarn；防焊不指定（落回環節色）——
     --dg-sr 在深底上對編號數字的對比不到 4.5，不拿來當卡片色（同 ABF 那張的判斷）。

   ---- 這張圖上誰做哪一塊（data-seg，三個都在 supply_chain.yaml 的 ai_server 鏈上）----
     ccl_material  銅箔 / 玻纖布 / 樹脂  → 外層那兩張銅箔、銅箔稜面三格、玻纖織紋小圖
     ccl           CCL 銅箔基板          → core（銅－介電－銅）、prepreg（無銅）
     hdi_pcb       高階 PCB（HDI/高層板）→ 內層線路、參考面、四種孔、防焊、表面處理、頂層走線
   ⚠ 右下角的 IC 載板對照格**不掛任何 data-seg**：這張圖的主體是**硬板**（把零件焊上去的那種），
     ABF 載板是**另一種板子**（把晶片黏上去的），在這裡只是一格對照 —— 一張圖一個主體。載板由 `ic_substrate` 那張專門處理。
   ★ 掛 data-seg 的判準是**兩條同時成立**：① 那個環節在 supply_chain.yaml 真的存在
     ② 它在 `chainSegments()` 回傳的清單裡（本籍鏈 ＋ CHAIN_EXTRA）。這張圖用的三個都是 ai_server 本籍。

   ⚠ `site/index.html` 已經把這個檔的 <script> 寫好了，不要再去動 index.html。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function' || !D.fx) return;   // diagrams.js 沒載到就安靜退出
  const { STYLE, extRow, note, processBar, fold, fx } = D;

  const M = 'ccl_material', C = 'ccl', P = 'hdi_pcb';

  /* ================================================================ 版面常數（全部是畫布座標，寬 560）
     每一片薄板：前面 x ∈ [XL, XR]、厚度 h；頂面往右後上擠出 (DX, DY)；片與片之間的間距 G（含頂面的 15px，所以空氣是 4px）。*/
  const CW = 560, XL = 24, W = 404, XR = XL + W, DX = 36, DY = -15, G = 19;
  const ISO = { dx: DX, dy: DY };
  const MSK = 6, FOIL = 5, PPH = 11, COREH = 20, CUH = 4;   // 銅 4 ＜ 介電 12（core）／11（prepreg）：S5 是算出來的

  /* 由上往下：防焊 → L1 銅箔 → prepreg → core（L2/L3）→ prepreg → core（L4/L5）→ … → L10 銅箔 → 防焊。
     ★ 這張表就是 S1／S2／S3／S4：core 三件一組、prepreg 沒有銅、10 層銅、鏡像對稱 —— 寫錯整張圖就錯。*/
  const ORDER = [['mskT', MSK], ['l1', FOIL], ['pp1', PPH], ['c1', COREH], ['pp2', PPH], ['c2', COREH], ['pp3', PPH],
    ['c3', COREH], ['pp4', PPH], ['c4', COREH], ['pp5', PPH], ['l10', FOIL], ['mskB', MSK]];
  const Y = {};
  (function stack() { let y = 46; ORDER.forEach(([k, h]) => { Y[k] = [y, y + h]; y += h + G; }); Y.bottom = y - G; })();
  const KEYS = ORDER.map(o => o[0]);
  const CORES = ['c1', 'c2', 'c3', 'c4'], PPS = ['pp1', 'pp2', 'pp3', 'pp4', 'pp5'];
  /* 第 n 層銅的 y 範圍：L1／L10 是整片銅箔；其餘在 core 的上緣（偶數層）或下緣（奇數層）。*/
  const CU = { 1: Y.l1, 10: Y.l10 };
  CORES.forEach((k, i) => { CU[2 * i + 2] = [Y[k][0], Y[k][0] + CUH]; CU[2 * i + 3] = [Y[k][1] - CUH, Y[k][1]]; });
  /* 參考面（整片銅）與訊號層（線路）的分派。三條限制同時成立：
       · T3：每一層訊號的上一層或下一層一定是整片銅
       · S4：上下鏡像（L2↔L9、L3↔L8、L4↔L7、L5↔L6 兩兩同角色）
       · §3-B：背鑽落在 L4、埋孔接 L4↔L7 —— 這兩層必須是**訊號層**才講得通 */
  const PLANE = [2, 5, 6, 9];
  const isPlane = (n) => PLANE.indexOf(n) >= 0;

  // 防焊開窗與焊墊的位置（u 座標）：上面一處、下面一處
  const PAD_T = 372, PAD_B = 150, PADW = 34;

  /* ================================================================ 四種孔（§3-B，跨距全部寫死）
     `hit` ＝真的接到的銅層（其餘層一律留 clearance，不准跟孔銅連在一起，連上去就是短路）。*/
  const VIA = {
    blind: { u: 64, hwT: 7, hwB: 3.5, hit: [1, 2], y0: Y.l1[1], y1: Y.c1[0] + CUH },              // L1 → L2，只穿 pp1
    bur: { u: 140, hw: 4, cw: 2.2, hit: [4, 7], y0: CU[4][0], y1: CU[7][1] },                     // L4 → L7，兩端都在內層
    pth: { u: 296, hw: 5, cw: 2.5, hit: [1, 4], y0: Y.mskT[0], y1: Y.mskB[1], stub: CU[4][1] },  // L1 → L10 貫穿；訊號只到 L4
    bd: { u: 352, hw: 5, cw: 2.5, dhw: 8.5, hit: [1, 4], y0: Y.mskT[0], y1: Y.mskB[1], stub: CU[4][1], stop: CU[4][1] + 7 },  // 背鑽：由 L10 側往上，停在 L4 下方 7px
  };
  const ux = (u) => XL + u;
  const R = (x, y, w, h, fill, cls, rx, op) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${(+x).toFixed(1)}" y="${(+y).toFixed(1)}" width="${(+w).toFixed(1)}" height="${(+h).toFixed(1)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"${op ? ` opacity="${op}"` : ''}/>`;
  const clip = (a0, a1, b0, b1) => { const s = Math.max(a0, b0), e = Math.min(a1, b1); return e > s ? [s, e] : null; };

  /* 卡片的元件色（token，不寫死）。銅用亮面 --dg-cu-lit：選到的卡片標題在深底上 --dg-cu 只有 4.24:1。*/
  const COL = { cu: 'var(--dg-cu-lit)', au: 'var(--dg-au)', core: 'var(--dg-weave)', pp: 'var(--dg-yarn)' };

  /* ================================================================ 小工具 */
  // 頂面座標：u 沿板長、v 是深度（0 前緣、1 後緣）—— 給 plate 的 top 用，原點＝前緣左端
  const tp = (u, v) => `${(u + v * DX).toFixed(1)},${(v * DY).toFixed(1)}`;
  // 一片玻璃板（前面 ＋ 頂面 ＋ 右側面），前面那塊 rect 帶 .part 讓選取描邊有地方掛
  const plate = (k, fill, top) => fx.glass(XL, Y[k][0], W, Y[k][1] - Y[k][0], { iso: ISO, fill, cls: 'part', rx: 3, top });
  // 柔陰影：每一片頂面往下 11px 的影子，全部包成一個群組（一次濾鏡）
  const plateShadow = (k) => `<path d="M${XL + 4},${Y[k][1] + 11} L${XR - 2},${Y[k][1] + 11} L${XR + DX - 2},${Y[k][1] + 11 + DY} L${XL + DX + 4},${Y[k][1] + 11 + DY}Z"/>`;
  // 頂面上的示意銅線（三條，不同深度）：訊號層的線路往後延伸
  const topTraces = () => [0.3, 0.55, 0.8].map(v =>
    `<path d="M${tp(8, v)} L${tp(W - 8, v)}" stroke="var(--dg-cu)" stroke-width="1.1" opacity=".38" fill="none"/>`).join('');
  // 頂面整片銅（參考面）
  const topPlane = () => `<path d="M${tp(2, 0.04)} L${tp(W - 2, 0.04)} L${tp(W - 2, 0.96)} L${tp(2, 0.96)}Z" fill="var(--dg-cu)" opacity=".5"/>`;
  // 頂面上的焊墊（從防焊開窗看到的那一塊，或 L1 上的墊子）
  const topPad = (u, fill, op) => `<path d="M${tp(u, 0.2)} L${tp(u + PADW, 0.2)} L${tp(u + PADW, 0.8)} L${tp(u, 0.8)}Z" fill="${fill}" opacity="${op || '.9'}"/>`;

  /* 玻纖織紋：core 的介電與 prepreg 都是玻纖布補強的樹脂，遠看也認得出來（M1 的放大格在章節 ③）。*/
  function weave(x0, x1, y0, y1, op) {
    const h = y1 - y0, seg = 16, a = Math.min(2.6, h / 4);
    const yy = (y0 + h / 2).toFixed(1); let d = `M${x0},${yy}`;
    for (let x = x0; x < x1 - seg; x += seg) d += `q${(seg / 4).toFixed(1)},-${a.toFixed(1)} ${(seg / 2).toFixed(1)},0 q${(seg / 4).toFixed(1)},${a.toFixed(1)} ${(seg / 2).toFixed(1)},0`;
    const warp = []; for (let x = x0 + seg / 2; x < x1 - 2; x += seg) warp.push(`M${x.toFixed(1)},${(y0 + 1.5).toFixed(1)} v${(h - 3).toFixed(1)}`);
    return `<path d="${d}" stroke="var(--dg-yarn)" stroke-width="1.1" fill="none" opacity="${op || '.55'}"/>`
      + `<path d="${warp.join(' ')}" stroke="var(--dg-yarn)" stroke-width=".8" fill="none" opacity="${(op ? +op * .55 : .3).toFixed(2)}"/>`;
  }

  /* 某一層銅在孔附近要不要讓位（回傳 [u0,u1] 的禁區清單）。不是它接的孔一律留 clearance。*/
  function gapsFor(n) {
    const g = [], mid = (CU[n][0] + CU[n][1]) / 2, V = VIA;
    const add = (u, half) => g.push([u - half, u + half]);
    if (V.pth.hit.indexOf(n) < 0) add(V.pth.u, V.pth.hw + V.pth.cw + 3);
    if (V.bd.hit.indexOf(n) < 0) add(V.bd.u, (mid > V.bd.stop ? V.bd.dhw : V.bd.hw + V.bd.cw) + 3);
    if (V.bur.hit.indexOf(n) < 0 && mid > V.bur.y0 && mid < V.bur.y1) add(V.bur.u, V.bur.hw + V.bur.cw + 3);
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
    const a = []; let u = 6, k = seed;
    while (u < W - 8) { const w = 24 + ((k * 7) % 5) * 8; a.push([u, Math.min(W - 6, u + w)]); u += w + 9; k++; }
    return a;
  }
  /* 第 n 層銅（core 上的那一條）：參考面整片、訊號層一段一段；接到孔的那幾層在孔口留一塊環（ring）。*/
  function band(n) {
    const [y0, y1] = CU[n];
    const segs = cut(isPlane(n) ? [[2, W - 2]] : traceSegs(n), gapsFor(n));
    const rings = [];
    [VIA.pth, VIA.bd, VIA.bur].forEach(v => { if (v.hit.indexOf(n) >= 0) rings.push(R(ux(v.u) - v.hw - v.cw - 4, y0, v.hw * 2 + v.cw * 2 + 8, y1 - y0, 'var(--dg-cu)')); });
    if (VIA.blind.hit.indexOf(n) >= 0 && n === 2) rings.push(R(ux(VIA.blind.u) - VIA.blind.hwB - 4, y0, VIA.blind.hwB * 2 + 8, y1 - y0, 'var(--dg-cu)'));
    return segs.map(([a, b]) => R(ux(a), y0, b - a, y1 - y0, 'var(--dg-cu)', 'part')).join('') + rings.join('');
  }

  /* ================================================================ 四種孔的畫法（每一片各畫自己那一段 ＋ 層間小銅柱）
     hole＝孔洞（--dg-edge）、wall＝孔銅（--dg-cu；殘端 --dg-err、背鑽留下的殘餘 --dg-warn）。*/
  const hole = (u, hw, y0, y1) => R(ux(u) - hw, y0, hw * 2, y1 - y0, 'var(--dg-edge)');
  const wall = (u, hw, cw, y0, y1, fill) => R(ux(u) - hw - cw, y0, cw, y1 - y0, fill) + R(ux(u) + hw, y0, cw, y1 - y0, fill);
  // 穿過層間空隙的小銅柱：這一層的孔接到下一層的銅（拆開之後才看得到的組裝關係）
  const pillar = (u, w, y0, y1, fill) => R(ux(u) - w / 2, y0, w, y1 - y0, fill || 'var(--dg-cu)', '', 1.5, '.55');
  // 這個 y 位置的孔銅是什麼顏色（PTH：L4 以下是殘端；背鑽：L4 下方那一小段是沒鑽乾淨的殘餘）
  const wallFill = (v, y) => (v.stub != null && y >= v.stub) ? (v.stop != null ? 'var(--dg-warn)' : 'var(--dg-err)') : 'var(--dg-cu)';
  const gapsIn = (y0, y1) => { const g = []; for (let i = 0; i < KEYS.length - 1; i++) { const a = Y[KEYS[i]][1], b = Y[KEYS[i + 1]][0]; if (a >= y0 - 0.1 && b <= y1 + 0.1) g.push([a, b]); } return g; };

  // ① 機械通孔 PTH：上下都貫穿、兩端都開口（V1）。訊號只走到 L4，L4 以下那一截孔銅是**殘端**，單獨用 --dg-err 標出來（V2）。
  function gPth() {
    const v = VIA.pth, a = [];
    KEYS.forEach(k => { const c = clip(Y[k][0], Y[k][1], v.y0, v.y1); if (!c) return;
      a.push(hole(v.u, v.hw, c[0], c[1]));
      const s1 = clip(c[0], c[1], v.y0, v.stub), s2 = clip(c[0], c[1], v.stub, v.y1);
      if (s1) a.push(wall(v.u, v.hw, v.cw, s1[0], s1[1], 'var(--dg-cu)'));
      if (s2) a.push(wall(v.u, v.hw, v.cw, s2[0], s2[1], 'var(--dg-err)')); });
    gapsIn(v.y0, v.y1).forEach(([a0, a1]) => a.push(pillar(v.u, v.hw * 2 + v.cw * 2, a0, a1, wallFill(v, a0))));
    // 殘端上那一道往下的箭頭：反射回來的那一段（會閃，動畫關掉就停）
    a.push(`<path class="blink" d="M${ux(v.u) + 15},${v.stub + 6} v34 m-4,-6 l4,6 l4,-6" stroke="var(--dg-err)" stroke-width="2" fill="none"/>`);
    return `<g data-seg="${P}" data-part="pcb_pth">${a.join('')}<rect class="part" x="${ux(v.u) - v.hw - v.cw}" y="${v.y0}" width="${v.hw * 2 + v.cw * 2}" height="${v.y1 - v.y0}" fill="none" pointer-events="all"/></g>`;
  }
  // ② 背鑽：由**背面（L10 側）**進入、鑽頭比原孔大一號、而且**一定留一小段沒鑽乾淨**（V3）。
  function gBackdrill() {
    const v = VIA.bd, a = [];
    KEYS.forEach(k => { const c = clip(Y[k][0], Y[k][1], v.y0, v.y1); if (!c) return;
      const up = clip(c[0], c[1], v.y0, v.stop), dn = clip(c[0], c[1], v.stop, v.y1);
      if (up) { a.push(hole(v.u, v.hw, up[0], up[1]));
        const s1 = clip(up[0], up[1], v.y0, v.stub), s2 = clip(up[0], up[1], v.stub, v.stop);
        if (s1) a.push(wall(v.u, v.hw, v.cw, s1[0], s1[1], 'var(--dg-cu)'));
        if (s2) a.push(wall(v.u, v.hw, v.cw, s2[0], s2[1], 'var(--dg-warn)')); }
      if (dn) a.push(hole(v.u, v.dhw, dn[0], dn[1])); });        // 鑽掉的那一段：孔徑較大、沒有銅
    gapsIn(v.y0, v.y1).forEach(([a0, a1]) => { if (a0 < v.stop) a.push(pillar(v.u, v.hw * 2 + v.cw * 2, a0, a1, wallFill(v, a0))); });
    // 鑽頭走過的軸線（虛線）與鑽頭符號：從最底下往上鑽
    a.push(`<path class="hair" d="M${ux(v.u) - v.dhw},${v.stop} V${v.y1 + 6} M${ux(v.u) + v.dhw},${v.stop} V${v.y1 + 6}" stroke-dasharray="4 3"/>`);
    a.push(`<path d="M${ux(v.u) - 5},${v.y1 + 12} l5,-7 l5,7Z" fill="var(--dg-ink-3)"/>`);
    return `<g data-seg="${P}" data-part="pcb_backdrill">${a.join('')}<rect class="part" x="${ux(v.u) - v.dhw}" y="${v.y0}" width="${v.dhw * 2}" height="${v.y1 - v.y0}" fill="none" pointer-events="all"/></g>`;
  }
  // ③ 雷射盲孔：只碰到一個外層、不貫穿、形狀**上寬下窄**（V4）。直筒或畫穿都是錯的。
  function gBlind() {
    const v = VIA.blind, k = 'pp1';
    const cone = `<path class="part" d="M${ux(v.u) - v.hwT},${Y[k][0]} L${ux(v.u) + v.hwT},${Y[k][0]} L${ux(v.u) + v.hwB},${Y[k][1]} L${ux(v.u) - v.hwB},${Y[k][1]}Z" fill="var(--dg-cu)"/>`;
    return `<g data-seg="${P}" data-part="pcb_blind">${pillar(v.u, v.hwT * 2, Y.l1[1], Y[k][0])}${pillar(v.u, v.hwB * 2, Y[k][1], Y.c1[0])}${cone}</g>`;
  }
  // ④ 埋孔：兩端都不碰任何外層，上下都被介電蓋住（V5）。
  function gBuried() {
    const v = VIA.bur, a = [];
    KEYS.forEach(k => { const c = clip(Y[k][0], Y[k][1], v.y0, v.y1); if (!c) return;
      a.push(hole(v.u, v.hw, c[0], c[1]) + wall(v.u, v.hw, v.cw, c[0], c[1], 'var(--dg-cu)')); });
    gapsIn(v.y0, v.y1).forEach(([a0, a1]) => a.push(pillar(v.u, v.hw * 2 + v.cw * 2, a0, a1)));
    return `<g data-seg="${P}" data-part="pcb_buried">${a.join('')}<rect class="part" x="${ux(v.u) - v.hw - v.cw}" y="${v.y0}" width="${v.hw * 2 + v.cw * 2}" height="${v.y1 - v.y0}" fill="none" pointer-events="all"/></g>`;
  }

  /* ================================================================ 主視圖的各個零件（玻璃板 ＋ 前面的剖面內容） */
  // ---- 防焊（兩面都有，S6）：焊墊處**開窗**，上面一處、下面一處。上防焊的頂面畫「從開窗看到的墊子」。
  const gMask = () => `<g data-seg="${P}" data-part="pcb_mask">
    ${plate('mskT', 'var(--dg-sr)', topPad(PAD_T, 'var(--dg-au)'))}
    ${R(ux(PAD_T) - 2, Y.mskT[0], PADW + 4, MSK, 'var(--dg-bg)')}
    ${plate('mskB', 'var(--dg-sr)', '')}
    ${R(ux(PAD_B) - 2, Y.mskB[0], PADW + 4, MSK, 'var(--dg-bg)')}</g>`;
  /* ---- 外層那兩張銅箔（L1／L10）掛 ccl_material：多層板壓合時，**外層的銅是一張銅箔疊上去的**，
     內層的銅則是隨著 core 的兩面覆銅一起進來的。圖形（線路）都是 PCB 廠蝕刻出來的（頂層走線另一個群組）。*/
  const gFoil = () => {
    const etched = (k) => [40, 96, 176, 230, 312].map(u => R(ux(u), Y[k][0] + 1, 14, FOIL - 2, 'var(--dg-pcb-core)', '', 0, '.7')).join('');
    return `<g data-seg="${M}" data-part="pcb_foil">
    ${plate('l1', 'var(--dg-cu)', `<path d="M${tp(0, 0)} L${tp(W, 0)} L${tp(W, 1)} L${tp(0, 1)}Z" fill="var(--dg-pcb-core)" opacity=".5"/>` + topPad(PAD_T, 'var(--dg-cu-lit)', '.9'))}${etched('l1')}
    ${plate('l10', 'var(--dg-cu)', '')}${etched('l10')}</g>`;
  };
  /* ---- 頂層走線（頂視，畫在 L1 那片的頂面上）：T1 差動對永遠成雙、T2 蛇行兩條一起繞、T4 45° 轉角。
     每一對用同一組 data-pair，驗收數「每一組剛好兩條、形狀相同」。*/
  const gTopTrace = () => {
    const P2 = (pts) => 'M' + pts.map(([u, v]) => tp(u, v)).join(' L');
    const pair = (name, pts, dv) => `<path class="tv part" data-pair="${name}" d="${P2(pts)}"/><path class="tv part" data-pair="${name}" d="${P2(pts.map(([u, v]) => [u, v + dv]))}"/>`;
    const serp = []; let u = 150; serp.push([u, .3]);
    for (let i = 0; i < 4; i++) { serp.push([u + 6, .05], [u + 12, .05], [u + 18, .3]); u += 22; }
    serp.push([u + 8, .3]);
    return `<g data-seg="${P}" data-part="pcb_top_trace" transform="translate(${XL},${Y.l1[0]})">
      ${pair('diff', [[40, .3], [126, .3]], .3)}
      ${pair('serp', serp, .3)}
      ${pair('corner', [[276, .3], [310, .3], [324, .6], [352, .6]], .3)}</g>`;
  };
  // ---- 芯板 core：銅－介電－銅（S1）。介電是玻璃板本身（有織紋）；上下兩條銅在 gTrace／gPlane 裡依層別畫。
  const gCore = () => `<g data-seg="${C}" data-part="pcb_core">${CORES.map((k, i) => plate(k, 'var(--dg-pcb-core)', isPlane(2 * i + 2) ? topPlane() : topTraces())
    + weave(XL + 6, XR - 6, Y[k][0] + CUH + 1, Y[k][1] - CUH - 1)).join('')}</g>`;
  // ---- 半固化片 prepreg：**本身沒有銅**（S2），玻纖布佔比高、比 core 淺；壓合時受熱受壓流動固化，把 core 黏起來。
  const gPp = () => `<g data-seg="${C}" data-part="pcb_pp">${PPS.map(k => plate(k, 'var(--dg-pp)', '') + weave(XL + 6, XR - 6, Y[k][0] + 1, Y[k][1] - 1, '.75')).join('')}</g>`;
  // ---- 內層線路（訊號層，一段一段）與參考面（整片銅）：兩者一眼分得開，而且每一層訊號的上或下一定是整片銅（T3）
  const gTrace = () => `<g data-seg="${P}" data-part="pcb_trace">${[3, 4, 7, 8].map(band).join('')}</g>`;
  const gPlane = () => `<g data-seg="${P}" data-part="pcb_plane">${PLANE.map(band).join('')}</g>`;
  /* ---- 表面處理：**只在開窗露出來的銅上**，順序是銅 → 鎳 → 金（S7／S8）。鎳在內、金在外。*/
  const gEnig = () => `<g data-seg="${P}" data-part="pcb_enig">
    ${R(ux(PAD_T), Y.l1[0] - 2.2, PADW, 2.2, 'var(--dg-ni)', 'part')}${R(ux(PAD_T), Y.l1[0] - 3.8, PADW, 1.6, 'var(--dg-au)')}
    ${R(ux(PAD_B), Y.l10[1], PADW, 2.2, 'var(--dg-ni)', 'part')}${R(ux(PAD_B), Y.l10[1] + 2.2, PADW, 1.6, 'var(--dg-au)')}</g>`;

  /* ---- 訊號跑一次（這張圖唯一的動畫，§9）：從 L1 的焊墊出發 → PTH 下到 L4 → L4 走線 → 埋孔下到 L7 → L7 走線。
     D.fx.beam：一條發光光束（整張圖的第一個 feGaussianBlur）＋ 流動虛線（CSS dgdash）＋ 兩個端點光點；
     再加一顆走 SMIL 的光點 —— industry.js 的 setAnimAll 兩種都會停。經過殘端時那道紅箭頭在閃（表達反射）。*/
  const SIG = `M${ux(PAD_T) + PADW / 2},${Y.l1[0] - 6} L${ux(PAD_T) + PADW / 2},${(Y.l1[0] + Y.l1[1]) / 2} L${ux(VIA.pth.u)},${(Y.l1[0] + Y.l1[1]) / 2} `
    + `L${ux(VIA.pth.u)},${CU[4][0] + 2} L${ux(VIA.bur.u)},${CU[4][0] + 2} L${ux(VIA.bur.u)},${CU[7][1] - 2} L${ux(30)},${CU[7][1] - 2}`;
  const gSignal = () => `<g pointer-events="none">
    ${fx.beam(SIG, { color: 'var(--dg-sig)', w: 2, flow: true, dots: [[ux(PAD_T) + PADW / 2, Y.l1[0] - 6], [ux(30), CU[7][1] - 2]] })}
    <circle r="3.2" fill="var(--dg-sn)" opacity=".95"><animateMotion dur="7s" repeatCount="indefinite" path="${SIG}"/></circle></g>`;

  /* 這一張自己的樣式。**全部吃 --dg-* token，一個 #xxxxxx 都沒有。**
     描邊與發光各降一階（只作用在這一張圖）：疊構裡的銅只有 4px 厚，共用的 2.2px 描邊套上去整條會變成實心的環節色塊，
     整片板子就變成一面發光的格子 —— 那正是「螢光感太重」。四個狀態：平時／選到的環節 → 不描邊（玻璃板自己有 .fxe 的細邊）；
     滑鼠移上去 → 1.4px；**你點的那一個** → 2.4px ＋ 一圈 5px 的暈開（閱讀模式 --dg-glow:none 就不暈）。
     多一個 svg 型別選擇器是必要的：特異性才壓得過 diagrams.js 的那一條。*/
  const CSS = `<style>
    .dgpcb .hair{stroke:var(--dg-ink-3);stroke-width:var(--dg-hair-w,2);fill:none;opacity:.5}
    .dgpcb .mk{font-family:"JetBrains Mono",monospace;font-size:var(--dg-fs-min,12px);font-weight:700;fill:var(--dg-ink)}
    .dgpcb .mkc{fill:var(--dg-edge);stroke:var(--dg-ink-3);stroke-width:1.2}
    .dgpcb .tv{stroke:var(--dg-cu-lit);fill:none;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
    .dgpcb .cell{fill:var(--dg-frame-f);stroke:var(--dg-frame-s)}
    svg.dgpcb [data-seg] .part{stroke-width:0}
    svg.dgpcb [data-seg].sel .part{stroke-width:0;filter:none}
    svg.dgpcb [data-seg]:hover .part{stroke-width:1.4;filter:none}
    svg.dgpcb [data-seg].sel-part .part{stroke-width:2.4;filter:var(--dg-glow,drop-shadow(0 0 5px var(--cc)))}
    svg.dgpcb [data-seg].sel-part .tv,svg.dgpcb [data-seg]:hover .tv{stroke:var(--cc)}
    /* 壓暗那一階從 .3 放寬到 .55：進來的預設狀態是「族群 pcb_rigid 被選起來」＝ hdi_pcb 亮、ccl 與 ccl_material 被壓暗，
       而被壓暗的正好是 core、prepreg 與銅箔 —— 這張圖的主角。*/
    svg.dgpcb [data-seg].dim{opacity:.55}
    .dgwrap:has(svg.dgpcb) .dgc.dim{opacity:.55}
  </style>`;

  /* ================================================================ 章節 ②：四種孔的說明格（2×2）＋ HDI 階數 ＋ 走線四格（2×2） */
  function via4(y) {
    const rows = [
      ['10', '機械通孔 PTH ＋ 殘端', 'L1 → L10（上下都貫穿）', '最便宜，但訊號只走到 L4，', '剩下那截孔銅是沒接東西的天線'],
      ['12', '背鑽（back drill）', '由 L10 側鑽到 L4 下方', '鑽頭比原孔大一號，把殘端鑽掉；', '工程上鑽不到零，一定留一小段'],
      ['07', '雷射盲孔（micro via）', 'L1 → L2（只穿一層介電）', '上寬下窄的碗狀、不貫穿；', '外層才佈得下更密的線'],
      ['11', '埋孔（buried via）', 'L4 → L7（兩端都在內層）', '完全埋在板內，不佔外層面積；', '不會留下需要背鑽的殘端'],
    ];
    return rows.map(([n, t, span, s1, s2], i) => {
      const x = 16 + (i % 2) * 280, yy = y + Math.floor(i / 2) * 92;
      return `<g data-seg="${P}" data-part="via_box_${n}">`
        + `<rect class="part cell" x="${x}" y="${yy}" width="264" height="84" rx="7"/>`
        + `<circle class="mkc" cx="${x + 18}" cy="${yy + 18}" r="9"/><text class="mk" x="${x + 18}" y="${yy + 22.5}" text-anchor="middle">${n}</text>`
        + `<text class="lbl" x="${x + 32}" y="${yy + 22}">${t}</text>`
        + `<text class="tag" x="${x + 12}" y="${yy + 42}">${span}</text>`
        + `<text class="sub" x="${x + 12}" y="${yy + 60}">${s1}</text>`
        + `<text class="sub" x="${x + 12}" y="${yy + 76}">${s2}</text></g>`;
    }).join('');
  }
  function trace4(y) {
    const HGT = 172, cw = 264, bx = (i) => 16 + (i % 2) * 280, by = (i) => y + Math.floor(i / 2) * (HGT + 8);
    const plane = (x, yy, w) => `<rect x="${x}" y="${yy}" width="${w}" height="5" fill="var(--dg-cu)"/>`;
    const die = (x, yy, w, h) => `<rect x="${x}" y="${yy}" width="${w}" height="${h}" fill="var(--dg-pcb-core)"/>`;
    const cell = (i, part, inner, lines) => { const x = bx(i), yy = by(i), DR = yy + 10;
      return `<g data-seg="${P}" data-part="${part}"><rect class="part cell" x="${x}" y="${yy}" width="${cw}" height="${HGT}" rx="7"/>${inner(x, DR)}`
        + lines.map((t, j) => `<text class="${j ? 'sub' : 'lbl'}" x="${x + 12}" y="${yy + 94 + j * 17}">${t}</text>`).join('') + '</g>'; };
    // ① 單端 50 Ω：一條線 ＋ 下一層的整片參考面
    const c1 = cell(0, 'trace_se', (x, DR) => `<rect x="${x + 106}" y="${DR + 8}" width="34" height="6" fill="var(--dg-cu)"/>`
      + die(x + 14, DR + 14, 236, 22) + plane(x + 14, DR + 36, 236) + `<text class="tag" x="${x + 14}" y="${DR + 58}">單端 50 Ω</text>`,
      ['一條線 ＋ 一個參考面', '阻抗是「線對下面那片銅」算出來', '的。50 Ω 不是物理定律，是沿用', '同軸線的慣例 ＋ 製程折衷。']);
    // ② 差動 100 Ω：兩條等寬等距（只畫一條就不是差動對）
    const c2 = cell(1, 'trace_diff', (x, DR) => `<rect x="${x + 94}" y="${DR + 8}" width="24" height="6" fill="var(--dg-cu)"/><rect x="${x + 130}" y="${DR + 8}" width="24" height="6" fill="var(--dg-cu)"/>`
      + `<path class="hair" d="M${x + 118},${DR + 4} H${x + 130}" style="opacity:.9"/>` + die(x + 14, DR + 14, 236, 22) + plane(x + 14, DR + 36, 236)
      + `<text class="tag" x="${x + 14}" y="${DR + 58}">差動 100 Ω</text>`,
      ['永遠成雙，線寬與間距一致', '兩條一組、等大反向，對外干擾互相', '抵消。100 Ω 沿用雙絞線的慣例；', '只畫一條就不是差動對。']);
    // ③ 蛇行等長：兩條**一起**繞（只繞其中一條卻標等長是錯的）
    const c3 = cell(2, 'trace_skew', (x, DR) => { const w1 = `M${x + 16},${DR + 14} h22 v-10 h18 v10 h18 v-10 h18 v10 h18 v-10 h18 v10 h22 v-10 h18 v10 h22`;
      const w2 = `M${x + 16},${DR + 26} h22 v-10 h18 v10 h18 v-10 h18 v10 h18 v-10 h18 v10 h22 v-10 h18 v10 h22`;
      return `<rect x="${x + 12}" y="${DR + 2}" width="240" height="42" rx="3" fill="var(--dg-cu)" opacity=".16"/>`
        + `<path d="${w1}" stroke="var(--dg-cu)" stroke-width="4" fill="none" stroke-linejoin="round"/><path d="${w2}" stroke="var(--dg-cu)" stroke-width="4" fill="none" stroke-linejoin="round"/>`
        + `<text class="tag" x="${x + 14}" y="${DR + 58}">蛇行等長（底色＝下一層的參考面）</text>`; },
      ['兩條一起繞，不是只繞一條', '同一組訊號走不同長度就會先後到達', '（skew）。等長是對「一組」做的，', '只繞一條卻標等長就是錯的。']);
    // ④ 轉角：45° 與 90° 並排對照。★ 規格書 §7-B3：不准寫「90° 一定會反射」這種絕對句
    const c4 = cell(3, 'trace_corner', (x, DR) => `<rect x="${x + 12}" y="${DR + 2}" width="240" height="42" rx="3" fill="var(--dg-cu)" opacity=".16"/>`
      + `<path d="M${x + 22},${DR + 10} h34 v26" stroke="var(--dg-cu)" stroke-width="5" fill="none"/>`
      + `<path d="M${x + 140},${DR + 10} h26 l12,12 v14" stroke="var(--dg-cu)" stroke-width="5" fill="none" stroke-linejoin="round"/>`
      + `<text class="tag" x="${x + 28}" y="${DR + 58}">90°</text><text class="tag" x="${x + 148}" y="${DR + 58}">45°</text>`,
      ['45° 是好習慣，不是鐵律', '① 早年酸性蝕刻液會積在直角裡', '（現在多改鹼性，已大幅緩解）', '② 高速下直角的額外電容造成阻抗', '不連續；低速或邊緣速率慢時很小']);
    return c1 + c2 + c3 + c4;
  }

  /* ================================================================ 章節 ③：銅箔稜面／玻纖織紋／IC 載板對照 */
  function matRow(y) {
    const HGT = 160;
    // ---- 銅箔稜面三格：粗糙度由左到右遞減（M2），電流貼著表面跑
    const cellW = 76;
    const rough = (x0, y0, amp, step) => {
      const p = [`M${x0},${y0}`]; let up = true;
      for (let u = 0; u < cellW - 10; u += step) { p.push(`l${step / 2},${up ? -amp : amp}`); p.push(`l${step / 2},${up ? amp : -amp}`); up = !up; }
      return p.join(' ');
    };
    const cell = (i, amp, step, name) => {
      const x = 28 + i * (cellW + 10), yy = y + 66;
      return `<rect x="${x}" y="${yy - 30}" width="${cellW}" height="30" fill="var(--dg-cu)"/>`
        + `<rect x="${x}" y="${yy}" width="${cellW}" height="22" fill="var(--dg-pcb-core)"/>`
        + `<path d="${rough(x, yy, amp, step)} L${x + cellW},${yy} L${x + cellW},${yy + 22} L${x},${yy + 22} Z" fill="var(--dg-pcb-core)"/>`
        + `<path d="${rough(x, yy - 3, amp, step)}" stroke="var(--dg-accent)" stroke-width="1.6" fill="none" class="pulse"/>`
        + `<text class="tag" x="${x + cellW / 2}" y="${yy + 40}" text-anchor="middle">${name}</text>`;
    };
    const foil = `<g data-seg="${M}" data-part="foil_rough">`
      + `<rect class="part cell" x="16" y="${y}" width="268" height="${HGT}" rx="7"/>`
      + `<text class="lbl" x="28" y="${y + 22}">銅箔為什麼要「低稜面」</text>`
      + cell(0, 4, 10, 'HTE') + cell(1, 2.4, 7, 'RTF') + cell(2, 1.1, 5, 'HVLP')
      + `<text class="sub" x="28" y="${y + 128}">頻率越高，電流越只貼著導體表面跑</text>`
      + `<text class="sub" x="28" y="${y + 144}">（集膚效應）。表面越粗，路越長。</text></g>`;
    // ---- 玻纖織紋：紗束與膠的介電常數不同，差動對兩條壓在不同介質上就有時間差
    const wv = [];
    for (let i = 0; i < 8; i++) wv.push(`<rect x="${306 + i * 30}" y="${y + 34}" width="16" height="60" rx="3" fill="var(--dg-yarn)" opacity=".85"/>`);
    for (let j = 0; j < 4; j++) wv.push(`<rect x="${300}" y="${y + 38 + j * 16}" width="248" height="8" rx="3" fill="var(--dg-yarn)" opacity="${j % 2 ? '.45' : '.62'}"/>`);
    const weaveCell = `<g data-seg="${M}" data-part="fiber_weave">`
      + `<rect class="part cell" x="292" y="${y}" width="268" height="${HGT}" rx="7"/>`
      + `<text class="lbl" x="304" y="${y + 22}">玻纖織效應（fiber weave effect）</text>`
      + `<rect x="300" y="${y + 32}" width="248" height="64" rx="4" fill="var(--dg-resin)"/>`
      + wv.join('')
      + `<path d="M306,${y + 47} H542" stroke="var(--dg-cu)" stroke-width="4.5" fill="none"/>`
      + `<path d="M306,${y + 82} H542" stroke="var(--dg-cu)" stroke-width="4.5" fill="none"/>`
      + `<text class="sub" x="304" y="${y + 114}">一條壓在紗束上、一條壓在膠上 →</text>`
      + `<text class="sub" x="304" y="${y + 130}">等效介電常數不同 → 產生時間差。</text>`
      + `<text class="sub" x="304" y="${y + 146}">對策：攤平玻纖布、低 Dk 玻纖。</text></g>`;
    /* ---- IC 載板對照格：**不掛任何 data-seg**（一張圖一個主體）。載板是另一種板子、另一批公司，在這裡只是一格對照。*/
    const y2 = y + HGT + 12;
    const abf = `<g pointer-events="none">`
      + `<rect class="frame" x="16" y="${y2}" width="544" height="112" rx="7"/>`
      + `<text class="lbl" x="28" y="${y2 + 22}" style="fill:var(--dg-warn)">這不是 PCB，是 IC 載板（對照，不掛環節）</text>`
      + `<rect x="28" y="${y2 + 32}" width="520" height="24" rx="3" fill="var(--dg-resin)"/>`
      + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19].map(i => `<rect x="${36 + i * 26}" y="${y2 + 36}" width="5" height="5" fill="var(--dg-cu)"/>`).join('')
      + `<text class="sub" x="28" y="${y2 + 74}">ABF 積層膜沒有織造玻纖（雷射鑽孔不會打到紗束），線寬比 PCB 細一個量級，</text>`
      + `<text class="sub" x="28" y="${y2 + 90}">做法是半加成（SAP／mSAP）—— 另一段製程、另一批公司。</text>`
      + `<text class="cap" x="28" y="${y2 + 106}">台股在半導體鏈的「IC 載板（ABF / BT）」那一格，不要跟這張圖上的 PCB 廠混在一起。</text></g>`;
    return foil + weaveCell + abf;
  }

  /* ================================================================ 整張圖 */
  function pcbStackup() {
    // 柔陰影：每一片板子一個影子，全部包成一個群組（第二個、也是最後一個 feGaussianBlur）
    const shadows = fx.shadows(KEYS.map(plateShadow).join(''));
    const steps = [
      { seg: C, t: '① 板材', s: '玻纖布＋樹脂＋銅箔壓合' },
      { seg: P, t: '② 內層線路', s: '曝光 → 顯影 → 蝕刻' },
      { seg: P, t: '③ 疊合＋壓合＋鑽孔', s: '機械鑽 ／ 雷射鑽' },
      { seg: P, t: '④ 孔內金屬化＋外層', s: '鍍銅 → 電鍍 → 防焊' },
      { seg: P, t: '⑤ 表面處理＋電測', s: 'ENIG ／ OSP ／ ENEPIG' },
    ];
    const Y2 = 480, Y3 = Y2 + 620, Y4 = Y3 + 330;   // 三個章節的自然座標（wireFolds 會重新堆疊）

    return `<svg class="dg dgm rs dgpcb" viewBox="0 0 ${CW} ${Y4 + 900}" width="100%" style="display:block">${STYLE}${CSS}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <!-- 標題與說明：v2 搬到 HTML 的 .dghead，SVG 裡不畫 -->
      <text class="ttl ext" x="0" y="0">多層 PCB：一塊板子怎麼疊出來，訊號又是怎麼在裡面被磨掉的</text>
      <text class="cap ext" x="0" y="0">把一片 10 層板一片一片拆開浮著看：core（銅－介電－銅）與 prepreg（無銅）交替、上下鏡像對稱，最外面是防焊；剖面畫在每一片的前緣，四種孔畫成穿過層間空隙的小銅柱 —— 貫穿的、鑽掉一截的、只穿一層的、完全埋起來的，跨距各不相同。藍色光束＝訊號路徑：焊墊 → 通孔下到 L4 → 埋孔 → L7（可用「動畫」鈕停）。四種孔與走線、材料、製程與結論收在下面三段。</text>

      <!-- ================= §1 主視圖：等角爆炸層疊 =================
           畫的順序＝由下往上（上面的板子會蓋住下面板子的頂面，這是爆炸圖該有的遮擋）：
           陰影 → 各片玻璃板（含 core 的銅帶）→ 四種孔（孔洞、孔銅、層間小銅柱）→ 焊墊表面處理 → 頂層走線 → 訊號。-->
      ${shadows}
      ${gMask()}${gFoil()}${gPp()}${gCore()}${gPlane()}${gTrace()}
      ${gPth()}${gBackdrill()}${gBlind()}${gBuried()}
      ${gEnig()}${gTopTrace()}${gSignal()}

      <!-- ================= 說明卡片（HTML，左右兩欄）：左欄錨點在板子左緣或左半邊、右欄錨點在右半邊 ================= -->
      <!-- 卡片只放一句話（標題 ＋ 一行）：三欄模式的卡片欄只有 220px，卡片欄不可以比畫布高（一頁看完）；
           長一點的說明在零件小卡（parts.desc）與下面三段章節裡 -->
      ${extRow({ side: 'l', no: 1, seg: P, part: 'pcb_mask', ax: 34, ay: (Y.mskT[0] + Y.mskT[1]) / 2,
    title: '防焊 solder mask', sub: '兩面都有，焊墊處開窗' })}
      ${extRow({ side: 'l', no: 3, seg: P, part: 'pcb_top_trace', color: COL.cu, ax: 70, ay: Y.l1[0] + DY / 2 - 1,
    title: '頂層走線：差動對成雙', sub: '蛇行等長、45° 轉角' })}
      ${extRow({ side: 'l', no: 5, seg: M, part: 'pcb_foil', color: COL.cu, ax: 34, ay: (Y.l1[0] + Y.l1[1]) / 2 + 1,
    title: '銅箔 1 oz ≒ 35 µm', sub: '外層兩張壓合時才疊上' })}
      ${extRow({ side: 'l', no: 7, seg: P, part: 'pcb_blind', color: COL.cu, ax: ux(VIA.blind.u), ay: (Y.pp1[0] + Y.pp1[1]) / 2,
    title: '雷射盲孔 blind via', sub: '只穿一層、上寬下窄' })}
      ${extRow({ side: 'l', no: 9, seg: C, part: 'pcb_pp', color: COL.pp, ax: 34, ay: (Y.pp2[0] + Y.pp2[1]) / 2,
    title: '半固化片 prepreg', sub: '沒有銅；壓合時流動固化' })}
      ${extRow({ side: 'l', no: 11, seg: P, part: 'pcb_buried', color: COL.cu, ax: ux(VIA.bur.u), ay: (Y.pp3[0] + Y.pp3[1]) / 2,
    title: '埋孔 buried via', sub: '兩端都在內層，不碰外層' })}
      ${note({ side: 'l', warn: true, title: '★ 點零件篩到的是「環節」，不是整個族群',
    lines: ['「高階 PCB」這一格收錄六家，跟硬板族群是兩份名單。',
      '示意圖，非實物比例；圖上畫 10 層銅，代表實際 20～50 層以上。',
      '良率、成本、市占、線寬一個數字都不寫。'] })}
      ${extRow({ side: 'r', no: 2, seg: P, part: 'pcb_enig', color: COL.au, ax: ux(PAD_T) + PADW + 6, ay: Y.l1[0] - 8,
    title: '表面處理 ENIG', sub: '只在開窗的銅上：銅→鎳→金' })}
      ${extRow({ side: 'r', no: 4, seg: C, part: 'pcb_core', color: COL.core, ax: XR - 10, ay: (Y.c1[0] + Y.c1[1]) / 2,
    title: '芯板 core：銅－介電－銅', sub: 'CCL 廠賣的就是它' })}
      ${extRow({ side: 'r', no: 6, seg: P, part: 'pcb_trace', color: COL.cu, ax: XR - 10, ay: (CU[4][0] + CU[4][1]) / 2,
    title: '內層線路（一段一段）', sub: '線路是 PCB 廠蝕的' })}
      ${extRow({ side: 'r', no: 8, seg: P, part: 'pcb_plane', color: COL.cu, ax: XR - 10, ay: (CU[6][0] + CU[6][1]) / 2,
    title: '接地／電源平面', sub: '沒有參考面就沒有受控阻抗' })}
      ${extRow({ side: 'r', no: 10, seg: P, part: 'pcb_pth', color: COL.cu, ax: ux(VIA.pth.u), ay: (Y.pp4[0] + Y.pp4[1]) / 2,
    title: '機械通孔 PTH ＋ 殘端', sub: '紅色那截是沒接東西的天線' })}
      ${extRow({ side: 'r', no: 12, seg: P, part: 'pcb_backdrill', color: COL.cu, ax: ux(VIA.bd.u), ay: (Y.pp5[0] + Y.pp5[1]) / 2,
    title: '背鑽 back drill', sub: '從背面鑽掉殘端，留一小段' })}

      <!-- ================= ② 四種孔各解決一件事 ＋ HDI 階數 ＋ 走線四格（預設收合；座標由 wireFolds 量）================= -->
      ${fold('pcb2', '② 四種孔各解決一件事｜走線：差動成雙、蛇行等長、轉角', '通孔／背鑽／盲孔／埋孔四種跨距、HDI 階數怎麼數、單端與差動阻抗、45° 不是鐵律', `
      <text class="hd" x="16" y="${Y2 + 20}">四種孔各解決一件事（編號對應卡片，跨距全部不一樣）</text>
      ${via4(Y2 + 32)}
      <text class="cap" x="16" y="${Y2 + 232}">HDI 階數寫成 i+N+i：1+N+1＝外側各一層微孔（多壓合一次、多雷射鑽一次），</text>
      <text class="cap" x="16" y="${Y2 + 250}">2+N+2＝兩次循序壓合與兩次雷射，3+N+3＝三次；全部層都用微孔互連叫 any-layer。</text>
      <text class="cap" x="16" y="${Y2 + 268}">微孔可以是單孔、錯孔（staggered）、疊孔（stacked）或跳孔（skip）—— 疊孔比錯孔貴。</text>
      <text class="cap" x="16" y="${Y2 + 286}">增層要用更薄的銅箔（1/3 oz 或 1/2 oz）才維持得住微孔的深寬比。</text>
      <text class="hd" x="16" y="${Y2 + 316}">走線：線寬線距、差動成雙、蛇行等長、轉角</text>
      ${trace4(Y2 + 328)}`)}

      <!-- ================= ③ 材料為什麼會變成瓶頸（預設收合）================= -->
      ${fold('pcb3', '③ 材料為什麼變成瓶頸：銅箔稜面、玻纖織紋、IC 載板對照', '稜面 HTE → RTF → HVLP 由粗到細、玻纖織效應與 spread glass、載板為什麼不是 PCB', `
      <text class="hd" x="16" y="${Y3 + 20}">損耗從介電（Df）與導體（銅箔稜面）兩邊一起上來</text>
      ${matRow(Y3 + 32)}`)}

      <!-- ================= ④ 製程五格 ＋ 兩塊結論 ＋ 誰做哪一塊 ＋ 免責（預設收合）================= -->
      ${fold('pcb4', '④ 製程五格｜層數為什麼一直往上加｜誰做哪一塊', '五格流程列（CCL 廠與 PCB 廠的分界線）、兩塊結論、三格誰做哪一塊與示意標示', `
      <text class="cap" x="16" y="${Y4 + 18}">製造流程（併成五格）　★ 壓合一定在鑽孔之前（先鑽好的孔會被流出來的膠填掉）；</text>
      <text class="cap" x="16" y="${Y4 + 36}">防焊一定在表面處理之前（反過來金會鍍到整片銅上）。</text>
      ${processBar(8, Y4 + 46, steps, 164, { cols: 3 })}
      <path class="hair" d="M182,${Y4 + 40} V${Y4 + 94}" stroke="var(--dg-warn)" stroke-dasharray="5 4" style="opacity:.85"/>
      <text class="sub" x="8" y="${Y4 + 180}" style="fill:var(--dg-warn)">← 這條線的左邊是 CCL 廠（交的是「板材」）｜右邊是 PCB 廠（交的是「成品板」）→</text>

      <rect class="frame" x="16" y="${Y4 + 196}" width="544" height="150" rx="8"/>
      <text class="hd" x="30" y="${Y4 + 218}">層數為什麼一直往上加</text>
      <text class="sub" x="30" y="${Y4 + 240}">① 晶片腳位與高速訊號對數變多 → 單層佈不下，只能往上疊。</text>
      <text class="sub" x="30" y="${Y4 + 258}">② 每一組高速訊號都要有緊鄰的參考面 → 一層訊號常常配一層平面，</text>
      <text class="sub" x="30" y="${Y4 + 276}">　 層數是等比例膨脹的，不是線性加一層。</text>
      <text class="sub" x="30" y="${Y4 + 294}">③ 量級：一般伺服器主板 12～14 層 → 16～20 層；AI 伺服器的通用基板</text>
      <text class="sub" x="30" y="${Y4 + 312}">　（UBB）20 層以上；800G 交換器板 20～30 → 36～48 層。</text>
      <text class="cap" x="30" y="${Y4 + 334}">來源：媒體報導，2026（不是公司揭露；口徑各家不同，只當量級看）</text>

      <rect class="frame" x="16" y="${Y4 + 360}" width="544" height="150" rx="8"/>
      <text class="hd" x="30" y="${Y4 + 382}">為什麼瓶頸會落在材料，不在 PCB 廠</text>
      <text class="sub" x="30" y="${Y4 + 404}">速度一提高，損耗同時從介電（Df）與導體（銅箔稜面）這兩邊上來，</text>
      <text class="sub" x="30" y="${Y4 + 422}">兩邊都要換更好的材料才壓得住。所以板材等級一路往上</text>
      <text class="sub" x="30" y="${Y4 + 440}">（M4 → M6 → M7 → M8 → M9，業界沿用的代號，不是標準組織的分級），</text>
      <text class="sub" x="30" y="${Y4 + 458}">而每升一級，底下的銅箔與玻纖布也要跟著升級（低稜面銅箔、低 Dk 玻纖）。</text>
      <text class="sub" x="30" y="${Y4 + 478}" style="fill:var(--dg-warn)">CCL 是 PCB 成本裡最大的一塊單一材料（各來源的百分比差很多、</text>
      <text class="sub" x="30" y="${Y4 + 496}" style="fill:var(--dg-warn)">口徑也不一致，所以這張圖一個百分比都不寫）。</text>

      <!-- 誰做哪一塊（零件顏色＝環節色，點下去就是篩那一格） -->
      <text class="hd" x="16" y="${Y4 + 536}">這張圖上誰做哪一塊</text>
      ${D.labelRow(M, 28, Y4 + 564, '銅箔 / 玻纖布 / 樹脂', 'CCL 的三種原料 —— 稜面與織紋那兩格就是它', null, null, 520)}
      ${D.labelRow(C, 28, Y4 + 612, 'CCL 銅箔基板（core / prepreg）', '把三種原料壓合成板材的那一段', null, null, 520)}
      ${D.labelRow(P, 28, Y4 + 660, '高階 PCB（HDI / 高層板）', '線路、鑽孔、壓合、防焊、表面處理', null, null, 520)}

      <text class="cap" x="16" y="${Y4 + 706}">示意圖，非實物比例｜各層厚度比例為示意：圖上畫 10 層銅（4 片 core ＋ 5 片 prepreg），</text>
      <text class="cap" x="16" y="${Y4 + 724}">代表實際 20～50 層以上。銅遠薄於介電（1 oz 銅 ≒ 35 µm，介電是數十～百餘 µm 等級）；</text>
      <text class="cap" x="16" y="${Y4 + 742}">蝕刻出來的線路剖面實際略呈梯形，這裡畫成矩形是為了可讀性。</text>
      <text class="cap" x="16" y="${Y4 + 760}">點零件篩到的是「供應鏈環節」，不是整個族群 —— 兩份名單由 supply_chain.yaml 維護。</text>
      <text class="cap" x="16" y="${Y4 + 778}">每一條事實的來源與信心度見 docs/diagram_specs/pcb_stackup.md。</text>`)}
    </svg>`;
  }

  window.DG.register('pcb_rigid', {
    level: 'group', chain: 'ai_server',
    name: 'PCB 硬板：多層板剖面與走線',
    draw: pcbStackup, native: CW, scene: 'pcb_rigid',   /* ★ 2026-09-23 Andy：「確保這邊都有 3D 圖」。檔頭 §0 原本寫「不做真 3D」，
        推翻它的是那個理由**漏掉的另一半**（逐張寫在 DECISIONS #250），不是那個理由本身。*/
    q: '一塊 AI 伺服器用的多層板為什麼要疊到幾十層？訊號在裡面被誰磨掉，瓶頸又為什麼卡在板材與銅箔、而不是 PCB 廠？',
    /* ★ `parts` ＝點這個零件時，「誰做的」小卡要顯示什麼（docs/diagram_purpose.md §4）。
       這張圖跨三個環節（銅箔／玻纖布／樹脂 → CCL → 高階 PCB），所以預設那條路
       （data-seg → 該環節全部台股）已經分得開「板材廠」與「PCB 廠」。
       需要精修的是**同一個環節裡面還要再分**的那幾格：
       「銅箔 / 玻纖布 / 樹脂」這一格有 7 家，但做銅箔的跟做玻纖布的不是同一批人 ——
       點「銅箔稜面」卻列出玻纖布廠，等於沒有回答問題。
       cos 只放代號，負責什麼一律讀 supply_chain.json 的 companies[].tech（R3）。
       v2 之後零件的名字不在 SVG 裡（卡片是 HTML），小卡拿不到 text.lbl，所以每一個零件都要自己給 name。*/
    parts: {
      /* 銅箔：金居 8358（HVLP／RTF）、榮科 4989（電解銅箔／RTF／VLP／HVLP）、南亞 1303（銅箔）。
         依據是 companies[].tech 自己寫的項目，不是我挑的。*/
      pcb_foil: {
        name: '銅箔（1 oz ≒ 35 µm）',
        desc: '外層這兩張銅箔是壓合時才疊上去的（1 oz ≒ 35 µm ≒ 1.4 mil）。速度一上來，銅箔背面的稜面就開始吃掉訊號，所以高速板要換低稜面銅箔。',
        cos: ['8358', '4989', '1303'],
        items: ['HVLP 銅箔', '高頻高速反轉銅箔 RTF（2025 初打入 AI 伺服器供應鏈）'],
      },
      pcb_top_trace: {
        name: '頂層走線（頂視）：差動對、蛇行等長、45° 轉角',
        desc: '畫在 L1 那片銅箔的頂面上：差動對永遠成雙、蛇行段兩條一起繞、轉角習慣走 45°。線是 PCB 廠蝕出來的，不是 CCL 廠交的。',
      },
      foil_rough: {
        name: '銅箔稜面（HTE → RTF → HVLP）',
        desc: '銅箔背面的稜面（為了抓住樹脂而刻意做粗）。頻率越高電流越走表面，稜面越粗、導體損耗越大 —— 這就是 RTF／VLP／HVLP 一路往低稜面走的原因。',
        cos: ['8358', '4989', '1303'],
        items: ['HVLP 銅箔', '高頻高速反轉銅箔 RTF（2025 初打入 AI 伺服器供應鏈）'],
      },
      /* 玻纖：建榮 5340、富喬 1815、德宏 5475 做布／紗，南亞 1303 兩樣都做。日東紡是外商。*/
      fiber_weave: {
        name: '玻纖織紋（fiber weave effect）',
        desc: '樹脂裡那層織起來的玻璃纖維布。織紋有紗束也有孔隙，兩者的介電常數不一樣，高速差動對橫過去就會左右不等速（纖維效應）。低 Dk 玻纖布就是在解這件事。',
        cos: ['5340', '1815', '5475', '1303'],
        items: ['高階玻纖布 / T-glass', '第二代低介電玻璃原紗 NER', 'LDK2 低介電玻纖布通過 CSP 認證，指定用於下一代 ASIC 平台'],
      },
      pcb_core: { name: '芯板 core（銅－介電－銅）', desc: '芯板：已固化、兩面覆銅的板材，介電裡看得到玻纖織紋。CCL 廠賣的就是它 —— 交到 PCB 廠手上時線路還沒蝕。' },
      pcb_pp: { name: '半固化片 prepreg（無銅）', desc: '半固化片（prepreg，無銅）。壓合時受熱受壓、流動並固化，把一片片 core 黏起來。疊構一定要上下對稱，不然迴焊高溫下會翹。' },
      pcb_trace: { name: '內層線路', desc: '內層線路，一段一段的。覆銅板由 CCL 廠交，線路是 PCB 廠自己蝕的 —— 這條線就是兩種公司的分界。' },
      pcb_plane: { name: '接地／電源平面（整片銅）', desc: '整片銅的接地／電源平面。沒有緊鄰的參考面就沒有受控阻抗，所以一層訊號常常要配一層平面 —— 層數是等比例膨脹的，不是線性加一層。' },
      pcb_mask: { name: '防焊（solder mask）', desc: '防焊：蓋住不該吃錫的銅，焊墊處開窗，兩面都有。順序上一定在表面處理之前，反過來金會鍍到整片銅上。' },
      pcb_enig: { name: '表面處理（ENIG＝化鎳浸金）', desc: '表面處理（ENIG＝化鎳浸金）：只在防焊開窗露出來的銅上，依序是銅 → 鎳 → 金，鎳負責擋擴散。同一塊板子選 ENIG／OSP／ENEPIG 是成本與保存期的取捨。' },
      pcb_pth: { name: '機械通孔 PTH ＋ 殘端', desc: '機械通孔（PTH）：上下都貫穿，最便宜。但訊號只走到 L4，剩下那一截孔銅（紅色）就是一根沒接東西的天線，會把訊號反射回來。' },
      pcb_backdrill: { name: '背鑽（back drill）', desc: '背鑽：用比原孔大一號的鑽頭，從背面把 PTH 的殘端鑽掉（鑽掉那一段空隙裡沒有銅柱）。工程上鑽不到零，一定會留一小段。' },
      pcb_blind: { name: '雷射盲孔（micro via）', desc: '雷射盲孔（micro via）：上寬下窄的碗狀、只穿一層介電、只接一個外層、不貫穿。外層才佈得下更密的線。' },
      pcb_buried: { name: '埋孔（buried via）', desc: '埋孔：兩端都在內層、完全埋在板內，不佔外層面積，也不會留下需要背鑽的殘端。' },
      via_box_10: { name: '機械通孔 PTH ＋ 殘端（說明格）', desc: 'L1 → L10 上下都貫穿。最便宜，但訊號只走到 L4，剩下那截孔銅是沒接東西的天線。' },
      via_box_12: { name: '背鑽（說明格）', desc: '由 L10 側鑽到 L4 下方，鑽頭比原孔大一號；工程上鑽不到零，一定留一小段。' },
      via_box_07: { name: '雷射盲孔（說明格）', desc: 'L1 → L2 只穿一層介電，上寬下窄、不貫穿。' },
      via_box_11: { name: '埋孔（說明格）', desc: 'L4 → L7 兩端都在內層，完全埋在板內。' },
      trace_se: { name: '單端 50 Ω', desc: '一條線 ＋ 一個參考面。50 Ω 不是物理定律，是沿用同軸線的慣例加上製程折衷。' },
      trace_diff: { name: '差動 100 Ω', desc: '兩條等寬等距、成雙的線；等大反向，對外干擾互相抵消。只畫一條就不是差動對。' },
      trace_skew: { name: '蛇行等長', desc: '同一組訊號走不同長度就會先後到達（skew）。把短的那條繞遠一點，而且兩條一起繞。' },
      trace_corner: { name: '45° 與 90° 轉角', desc: '45° 是好習慣，不是鐵律：早年是酸陷阱（現在多改鹼性蝕刻已緩解）、高速下才有直角的阻抗不連續。' },
    },
  });
})();
