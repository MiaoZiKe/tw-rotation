/* 電容器：鋁電解與固態電容剖面 —— docs/diagram_plan_electronics.md 的 E2
   （族群 `capacitor`，electronics 鏈）

   合約＝`docs/diagram_specs/alum_cap.md`。這個檔只實作，不重新決定規格。
   規格書裡已經寫死、這裡照辦的幾件事：

     · §0-A **不做真 3D**（`scene: null`）。四個資訊點全部是剖面關係：
       四層的順序、孔壁上的膜、電解液鑽進孔裡、固態只換中間那一層。
     · §0-B 交界（這份規格書存在的理由）：**不畫陶瓷介電層、不畫鎳內電極、
       不畫端電極三層、不畫導電樹脂軟端子、不畫板彎裂** —— 那些是 MLCC 那張。
       MLCC 是**疊層＋燒結的陶瓷**，這張是**捲繞＋長出來的氧化鋁**，是兩種東西。
     · §3-A P1／§6-K1（紅線）捲芯**四層一個週期**：陽極箔 → 紙 → 陰極箔 → 紙。
       三層捲起來，上一圈的陽極會直接碰到下一圈的陰極 —— 短路。
       實作上靠 `CORE` 這個陣列 ＋ `forEach` 保證，順序改不壞。
     · §3-A P2／§6-K2（紅線）**氧化膜只畫在陽極箔上**。兩面都畫＝畫成了雙極性電容，
       而且把「為什麼有極性」這件事畫掉了。
     · §6-K5（紅線）圖上明寫**「陰極箔不是陰極，真正的陰極是電解液」**。
     · §3-B P5／§6-E1（紅線）**氧化膜貼著孔壁的曲面走、而且等厚**。
       實作上用「同一條孔的 path 畫兩次、內層往內縮一個固定量」——
       外層是膜、內層是電解液，**膜的厚度是兩條 path 的差**，所以天生貼曲面、天生等厚。
       畫成一條平直線就把「表面積被放大」這個命題畫掉了。
     · §6-Y3（紅線）**6175 立敦做的是電容用鋁箔（電蝕箔、化成箔），不是電容成品**。

   兩個實作上的取捨
   ------------------
   1. **每一個零件都寫 `cos`，一個都不准留給預設**（§7-D1，這張圖最大的資料風險）。
      這張圖唯一掛得上的環節是 `passive_comp`（被動元件 MLCC / 電阻），
      而它底下 5 家裡只有 2375 凱美同時在 `capacitor` 族群裡 ——
      不寫 `cos` 的話 `renderPartCard()` 會走 `twOf()`，把做 MLCC 的那幾家
      列成「做這個零件的台股」。**那是錯的答案，不是不完整的答案。**
      `cos` 裡也只准放真的在 `supply_chain.yaml` 裡的代號（查不到的代號會被靜靜丟掉，
      比寫錯更難發現），其餘五檔一律寫進 `none:` 的整句話。
   2. **孔洞與氧化膜是誇張放大的**。真實的孔是 µm 級、箔是 100 µm 級，照比例畫
      氧化膜會薄到消失（800px 下不到 1px）。所以區 ② 單獨放大，並在畫面上標明。
      **但誇張放大不等於可以亂畫比例關係** —— §6-E2 要求氧化膜 ≤ 箔厚的 1/20，
      這個 1/20 是真的算出來的（區 ② 是 3 / 80、區 ① 是 1.4 / 30）。

   顏色一律走既有的 `--dg-*`（新增的七個材質 token 加在 index.html 的 :root，
   而且全部是既有 token 的 color-mix —— 四個配色一換它們自己跟著換）。
   JS 裡一個色碼都沒有。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;

  const W = 980, SEG = 'passive_comp';

  /* ================================================================ 小工具 */
  const f1 = (v) => (+v).toFixed(1);
  const R = (x, y, w, h, fill, cls, rx) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"/>`;
  const PA = (d, fill, cls) => `<path${cls ? ` class="${cls}"` : ''} d="${d}" fill="${fill}"/>`;
  const LN = (d, col, w2, cls, extra) =>
    `<path${cls ? ` class="${cls}"` : ''} d="${d}" stroke="${col}" stroke-width="${w2}" fill="none"${extra || ''}/>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${f1(x)}" y="${f1(y)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const frame = (x, y, w, h) => `<rect class="frame" x="${x}" y="${y}" width="${w}" height="${h}" rx="9"/>`;
  /* 零件外框。這張圖每一個零件都掛 `data-seg="passive_comp"`（§7-D1 第 1 點：
     掛了才點得動、才有小卡、`var(--c)` 才有色），但**每一個都覆寫 `cos`**。*/
  const part = (id, inner) => `<g data-part="${id}" data-seg="${SEG}">${inner}</g>`;

  /* ================================================================ 材質厚度（K6 的量測基準）
     氧化膜 < 電解紙 < 陰極箔 ≤ 陽極箔。這四個數字是唯一的來源，改一個就全圖跟著改。
     ★ 氧化膜 1.7 ／ 陽極箔 36 ＝ 1/21.2，滿足 §6-E2 的「≤ 箔厚的 1/20」。
     ⚠ 不要為了「看得見」把膜畫厚 —— 那就是 E2 不過。要讓它看得見是靠**對比**
       （`--dg-ac-oxide` 跟鋁箔的明度差拉開），不是靠厚度。 */
  const TH_ANODE = 36, TH_PAPER = 12, TH_CATHODE = 20, TH_OXIDE = 1.7;

  /* 一排蝕刻孔（小凹槽）。`down` ＝從上表面往下咬。圓弧底，不是尖角。 */
  function pores(x0, x1, y, depth, w, n, down, cls) {
    const out = [], step = (x1 - x0) / n;
    for (let i = 0; i < n; i++) {
      const cx = x0 + (i + 0.5) * step, k = down ? 1 : -1, r = w / 2;
      const yb = y + k * (depth - r);
      out.push(PA(`M${f1(cx - r)},${f1(y)} L${f1(cx - r)},${f1(yb)} `
        + `A${f1(r)},${f1(r)} 0 0 ${down ? 0 : 1} ${f1(cx + r)},${f1(yb)} L${f1(cx + r)},${f1(y)} Z`,
      'var(--dg-void)', cls));
    }
    return out.join('');
  }

  /* ================================================================ 區 ① 捲芯四層帶
     §3-A（K1，紅線）一個週期由下到上：陽極箔 → 電解紙 → 陰極箔 → 電解紙 → 回到陽極箔。
     ★ 四層寫在同一個陣列、用 forEach 畫 —— K1 因此自動成立，也改不壞。 */
  const BX0 = 32, BX1 = 300, BOFF = 12;          // 帶的左右端；BOFF ＝兩張箔的橫向錯開（K3／P3）
  const CORE = [
    { id: 'ac_paper', th: TH_PAPER, fill: 'var(--dg-ac-paper)', off: 0, nm: '④ 電解紙' },
    { id: 'ac_cathode', th: TH_CATHODE, fill: 'var(--dg-ac-foil)', off: BOFF, nm: '③ 陰極箔' },
    { id: 'ac_paper', th: TH_PAPER, fill: 'var(--dg-ac-paper)', off: 0, nm: '② 電解紙' },
    { id: 'ac_anode', th: TH_ANODE, fill: 'var(--dg-ac-foil)', off: 0, nm: '① 陽極箔' },
  ];

  function coreBand() {
    const g = [];
    let y = 108;                                   // 由上往下堆，陣列的最後一個（陽極箔）落在最下面
    const box = [];
    CORE.forEach((L) => { box.push({ L: L, y0: y, y1: y + L.th }); y += L.th; });
    box.forEach((b) => {
      const L = b.L, x0 = BX0 + L.off, x1 = BX1 + L.off, inner = [];
      inner.push(R(x0, b.y0, x1 - x0, L.th, L.fill, 'part ac' + (L.id === 'ac_anode' ? 'anode' : L.id === 'ac_cathode' ? 'cathode' : 'paper')));
      if (L.id === 'ac_anode' || L.id === 'ac_cathode') {
        // 兩張箔都有蝕刻孔（F1／F2）—— 差別在「有沒有那層膜」，不在有沒有孔
        inner.push(pores(x0 + 8, x1 - 8, b.y0, 6, 5, 14, true, 'acpore'));
        inner.push(pores(x0 + 8, x1 - 8, b.y1, 6, 5, 14, false, 'acpore'));
      } else {
        // 電解紙：畫幾條纖維線 ＋ 含浸的電解液（K4 的一半，另一半在陽極箔的孔裡）
        for (let i = 0; i < 9; i++) {
          inner.push(LN(`M${x0 + 10 + i * 30},${b.y0 + 2} L${x0 + 22 + i * 30},${b.y1 - 2}`,
            'var(--dg-ac-elyte)', 1));
        }
      }
      g.push(part(L.id, inner.join('')));
      if (L.id === 'ac_paper') {
        g.push(part('ac_elyte', R(x0, b.y0, x1 - x0, L.th, 'var(--dg-ac-elyte)', 'part acel',
          0) .replace('/>', ' opacity=".45"/>')));
      }
      if (L.id === 'ac_anode') {
        // ★ K2（紅線）：氧化膜只長在陽極箔上。陰極箔那一層一條都沒有。
        g.push(part('ac_oxide', R(x0, b.y0, x1 - x0, TH_OXIDE, 'var(--dg-ac-oxide)', 'part acoxflat')
          + R(x0, b.y1 - TH_OXIDE, x1 - x0, TH_OXIDE, 'var(--dg-ac-oxide)', 'part acoxflat')));
        // 電解液鑽進陽極箔的孔裡（K4 的另一半 —— 只畫在紙裡＝沒有接觸到介電質，電容不成立）
        g.push(part('ac_elyte', pores(x0 + 8, x1 - 8, b.y0 + TH_OXIDE, 4.5, 3.4, 14, true, 'acel')
          + pores(x0 + 8, x1 - 8, b.y1 - TH_OXIDE, 4.5, 3.4, 14, false, 'acel')));
      }
    });
    // 導針 ×2：一根接陽極箔、一根接陰極箔（K7，連接點看得見）
    const aY = box[3].y0 + TH_ANODE / 2, cY = box[1].y0 + TH_CATHODE / 2;
    g.push(part('ac_lead', R(16, aY - 2, BX0 - 12, 4, 'var(--dg-steel)', 'part aclead')
      + R(16, cY - 2, BX0 + BOFF - 12, 4, 'var(--dg-steel-2)', 'part aclead')));
    // 「捲起來就是一圈一圈」：回到第一層的提示
    g.push(LN(`M${BX1 + 18},${box[0].y0 + 4} L${BX1 + 18},100 L${BX0 + 20},100 L${BX0 + 20},${box[3].y1 - 4}`,
      'var(--dg-accent-2d)', 1.2, null, ' stroke-dasharray="4 4"'));
    g.push(T(BX0 + 30, 98, '④ 之後回到 ① —— 四層是一個週期', 'sub', null, 'fill:var(--dg-accent-2d)'));
    return g.join('');
  }

  /* 捲成渦旋：四條交錯的螺線（每一層一條），θ 至少跑 3 圈（§6-C2）。
     半徑 r = a + P·θ/2π ＋ 這一層的徑向位移 —— 所以四層是交替的，數得出來。 */
  const SP_A = 9, SP_P = 11, SP_TURNS = 3.2, SPX = 372, SPY = 145;

  function spiralRoll() {
    const g = [], N = 220;
    let off = 0;
    CORE.slice().reverse().forEach((L) => {           // 由內到外：陽極箔 → 紙 → 陰極箔 → 紙
      const pts = [];
      for (let i = 0; i <= N; i++) {
        const t = i / N * SP_TURNS * Math.PI * 2;
        const r = SP_A + SP_P * t / (Math.PI * 2) + off + L.th * 0.14;
        pts.push(`${f1(SPX + r * Math.cos(t))},${f1(SPY + r * Math.sin(t))}`);
      }
      g.push(LN('M' + pts.join('L'), L.fill, Math.max(1.6, L.th * 0.28), 'acspiral'));
      off += L.th * 0.28;
    });
    return part('ac_winding', g.join(''));
  }

  /* ================================================================ 區 ② 陽極箔放大
     §3-B（E1，紅線）由外到內：電解液 → 氧化膜（貼孔壁、等厚）→ 鋁基體。
     ★ 同一條孔的 path 畫兩次：外層填氧化膜色、內層往內縮 OX_W 填電解液色。
       膜的厚度就是兩條 path 的差 —— 天生貼曲面、天生等厚，改不壞。 */
  const ZFX0 = 470, ZFX1 = 716, ZFY0 = 120, ZFY1 = 200, ZPD = 30, ZPW = 10, ZPN = 10, OX_W = 3;

  function zoomFoil() {
    const g = [], th = ZFY1 - ZFY0;
    // 鋁基體（整塊），中間留下來的實心芯＝箔厚 − 2×孔深（★ 這個減法是真的算的）
    const coreTh = th - ZPD * 2;
    g.push(part('ac_anode', R(ZFX0, ZFY0, ZFX1 - ZFX0, th, 'var(--dg-ac-foil)', 'part')));
    g.push(part('ac_core', R(ZFX0, ZFY0 + ZPD, ZFX1 - ZFX0, coreTh, 'var(--dg-ac-foil)', 'part accore')));
    // 平的那一段表面上的氧化膜（跟孔壁上的是同一層、同一個厚度）
    g.push(part('ac_oxide', R(ZFX0, ZFY0, ZFX1 - ZFX0, OX_W, 'var(--dg-ac-oxide)', 'part acoxflat')
      + R(ZFX0, ZFY1 - OX_W, ZFX1 - ZFX0, OX_W, 'var(--dg-ac-oxide)', 'part acoxflat')));
    // 一排孔：外層＝氧化膜（貼孔壁）、內層＝電解液（填滿剩下的空間）
    /* ⚠ 上下兩面的孔**各自是一個 path**，不要串成同一條 —— 串起來之後
       `getBBox()` 量到的是「整片箔的高度」，驗收就分不出「膜貼著孔壁往裡面走」
       跟「一條橫躺的平直線」（那正是 §6-E1 這條紅線要擋的事）。*/
    const step = (ZFX1 - ZFX0 - 24) / ZPN, ox = [], el = [];
    for (let i = 0; i < ZPN; i++) {
      const cx = ZFX0 + 12 + (i + 0.5) * step;
      ox.push(porePath(cx, ZFY0, ZPD, ZPW, true));
      ox.push(porePath(cx, ZFY1, ZPD, ZPW, false));
      el.push(porePath(cx, ZFY0 + OX_W, ZPD - OX_W, ZPW - OX_W * 2, true));
      el.push(porePath(cx, ZFY1 - OX_W, ZPD - OX_W, ZPW - OX_W * 2, false));
    }
    g.push(part('ac_pore', ox.map((d) => PA(d, 'var(--dg-ac-oxide)', 'part acox')).join('')));
    g.push(part('ac_elyte', el.map((d) => PA(d, 'var(--dg-ac-elyte)', 'part acel')).join('')));
    // 厚度尺：只標「這是誇張放大的」，不寫任何 µm 數字（§7-C1）
    g.push(LN(`M460,${ZFY0} L460,${ZFY1}`, 'var(--dg-ink-3)', 1)
      + LN(`M456,${ZFY0} L464,${ZFY0}`, 'var(--dg-ink-3)', 1)
      + LN(`M456,${ZFY1} L464,${ZFY1}`, 'var(--dg-ink-3)', 1));
    return g.join('');
  }

  function porePath(cx, y, depth, w, down) {
    const k = down ? 1 : -1, r = w / 2, yb = y + k * (depth - r);
    return `M${f1(cx - r)},${f1(y)} L${f1(cx - r)},${f1(yb)} `
      + `A${f1(r)},${f1(r)} 0 0 ${down ? 0 : 1} ${f1(cx + r)},${f1(yb)} L${f1(cx + r)},${f1(y)} Z`;
  }

  /* ================================================================ 區 ③ 整顆縱剖
     §3-C：鋁殼（最外）→ 捲芯 → 橡膠封口（一端）＋ 兩根導針（同一端）→ 防爆閥（另一端）。
     C1：兩根導針**從同一端出來**（徑向引線型）。一端一根＝那是軸向型。
     C3：防爆閥刻痕在**與封口相反的那一端**，而且旁邊標「示意」（§7-B1 查不到來源）。*/
  /* ⚠ 整顆的下緣（含穿出封口的兩根導針）要停在 248 —— 底下 262／278／294 是三行標註，
     排版體檢只比「字跟字」有沒有重疊，**字壓在零件上它抓不到**，所以這裡自己算清楚。 */
  const CAN_X0 = 790, CAN_X1 = 890, CAN_Y0 = 86, CAN_Y1 = 226, SEAL_Y = 206;

  function wholeCan() {
    const g = [];
    // 外套膠膜（★ 上面一個字、一個色碼、一個廠商標示都不准有 —— C4）
    g.push(part('ac_sleeve', R(CAN_X0 - 4, CAN_Y0 - 4, CAN_X1 - CAN_X0 + 8, CAN_Y1 - CAN_Y0 + 8,
      'var(--dg-ac-sleeve)', 'part acsleeve', 6)));
    // 鋁殼
    g.push(part('ac_can', R(CAN_X0, CAN_Y0, CAN_X1 - CAN_X0, CAN_Y1 - CAN_Y0, 'var(--dg-alu-2)', 'part accan', 4)));
    // 捲芯：縱剖上看到的是一圈一圈交替的同心圓柱 → 一組一組交替的縱帶（四層一個週期）
    const bands = [], bx0 = CAN_X0 + 6, bw = (CAN_X1 - CAN_X0 - 12) / 12;
    for (let i = 0; i < 12; i++) {
      const L = CORE[(3 - (i % 4) + 4) % 4];
      bands.push(R(bx0 + i * bw, CAN_Y0 + 20, bw, SEAL_Y - CAN_Y0 - 24, L.fill, 'part accore2'));
    }
    g.push(part('ac_winding', bands.join('')));
    // 橡膠封口（一端）
    g.push(part('ac_seal', R(CAN_X0 + 2, SEAL_Y, CAN_X1 - CAN_X0 - 4, CAN_Y1 - SEAL_Y - 2,
      'var(--dg-ac-rubber)', 'part acseal', 3)));
    // 導針 ×2：★ 從同一端穿出
    g.push(part('ac_lead', R(CAN_X0 + 22, CAN_Y1 - 2, 5, 24, 'var(--dg-steel)', 'part acpin')
      + R(CAN_X1 - 27, CAN_Y1 - 2, 5, 24, 'var(--dg-steel-2)', 'part acpin')));
    // 防爆閥刻痕（★ 與封口相反的那一端；形狀不寫規格，旁邊標「示意」）
    g.push(part('ac_vent', LN(`M${CAN_X0 + 22},${CAN_Y0 + 10} L${CAN_X1 - 22},${CAN_Y0 + 10}`,
      'var(--dg-void)', 3, 'acvent')
      + LN(`M${(CAN_X0 + CAN_X1) / 2},${CAN_Y0 + 10} L${(CAN_X0 + CAN_X1) / 2 - 14},${CAN_Y0 + 2}`,
        'var(--dg-void)', 3, 'acvent')
      + LN(`M${(CAN_X0 + CAN_X1) / 2},${CAN_Y0 + 10} L${(CAN_X0 + CAN_X1) / 2 - 14},${CAN_Y0 + 18}`,
        'var(--dg-void)', 3, 'acvent')));
    return g.join('');
  }

  /* ================================================================ 區 ④ 液態 vs 固態
     §3-D（D1）：兩格**只有中間那一層不同**，其餘完全一樣。
     ★ 用同一支 `capCell()` 畫兩次、只換一個參數 —— D1／D3 因此自動成立。 */
  /* ⚠ 這一格的層厚**比區 ① 小一號**（陰極 14 ／ 中間 20 ／ 陽極 24 ／ 膜 1.2 ＝ 1/20）。
     理由是版面：區 ④ 只有 146 高，照區 ① 的厚度畫會把底下兩行標註壓到零件上
     （排版體檢只比「字跟字」，字壓在零件上它抓不到，所以這裡自己算）。
     §6-K6 的厚度順序是在區 ① 的四層帶上判定的；這一格判的是 D1／D2／D3。 */
  const CD_CAT = 14, CD_MID = 20, CD_AN = 24, CD_OX = 1.2;

  function capCell(x0, solid) {
    const g = [], w = 440, yC0 = 336, yM0 = yC0 + CD_CAT, yA0 = yM0 + CD_MID;
    // 陰極側（兩格完全一樣）
    g.push(part('ac_cathode', R(x0, yC0, w, CD_CAT, 'var(--dg-ac-foil)', 'part accell_cat')
      + pores(x0 + 10, x0 + w - 10, yC0 + CD_CAT, 4.5, 4.5, 20, false, 'acpore')));
    // 中間那一層：★ 唯一不同的地方
    const mid = solid
      ? part('ac_solid', R(x0, yM0, w, CD_MID, 'var(--dg-ac-poly)', 'part accell_mid acsolid'))
      : part('ac_paper', R(x0, yM0, w, CD_MID, 'var(--dg-ac-paper)', 'part accell_mid')
        + R(x0, yM0, w, CD_MID, 'var(--dg-ac-elyte)', 'part acel').replace('/>', ' opacity=".45"/>'));
    g.push(mid);
    // 陽極箔＋氧化膜＋孔（兩格完全一樣）
    g.push(part('ac_anode', R(x0, yA0, w, CD_AN, 'var(--dg-ac-foil)', 'part accell_an')
      + pores(x0 + 10, x0 + w - 10, yA0, 5.5, 4.5, 20, true, 'acpore')));
    g.push(part('ac_oxide', R(x0, yA0, w, CD_OX, 'var(--dg-ac-oxide)', 'part accell_ox acoxflat')));
    // ★ 中間那一層都要鑽進陽極箔的孔裡（固態也一樣 —— D2）
    g.push(part(solid ? 'ac_solid' : 'ac_elyte',
      pores(x0 + 10, x0 + w - 10, yA0 + CD_OX, 4.2, 3.2, 20, true,
        solid ? 'acsolidfill' : 'acel')
        .split('var(--dg-void)').join(solid ? 'var(--dg-ac-poly)' : 'var(--dg-ac-elyte)')));
    return g.join('');
  }

  /* ================================================================ 第 ① 段：製程 6 站 */
  const PROC = [
    ['① 蝕刻（腐蝕箔）', '把素箔的表面電化學咬成蜂窩狀，有效表面積放大很多倍 —— 這一步就是這個產業的核心製程'],
    ['② 化成', '通電做陽極氧化，在孔壁上長出氧化鋁介電質。★ 膜有多厚由加多少電壓決定，所以耐壓越高、膜越厚、容量越小'],
    ['③ 裁切', '把箔裁成要的寬度，並接上導針'],
    ['④ 捲繞', '陽極箔、紙、陰極箔、紙四層同捲在一個輪上，兩張箔稍微橫向錯開'],
    ['⑤ 含浸', '把電解液吸進紙裡、並鑽進陽極箔的孔中 —— 沒有接觸到氧化膜，電容就不成立'],
    ['⑥ 封口與老化', '裝進鋁殼、橡膠封口，再通電把化成時的缺陷修補回去'],
  ];

  function foldProc(y0) {
    const g = [];
    let y = y0 + 22;
    g.push(T(28, y, '從一片素箔到一顆電容：6 站（順序不准對調 —— 先化成再蝕刻的話，膜會被咬掉）', 'hd'));
    PROC.forEach((r, i) => {
      y += 20;
      g.push(part('ac_proc' + i, R(24, y - 14, 932, 19, 'transparent', 'part')
        + `<g pointer-events="none">${T(30, y, r[0] + '｜' + r[1], 'sub')}</g>`));
    });
    y += 24;
    g.push(T(28, y, '★ 蝕刻（腐蝕箔）與化成（化成箔）這兩道，在台股是 6175 立敦在做的事 —— 它做的是「電容用鋁箔」，不是電容成品。', 'sub', null, 'fill:var(--dg-warn)'));
    y += 17;
    g.push(T(28, y, '　 ③～⑥（裁切、捲繞、含浸、封口老化）是電容廠自己的產線。電解紙與電解液這一段，本圖查不到台股對應，先標為未知。', 'sub'));
    y += 17;
    g.push(T(28, y, '　 本圖不寫任何蝕刻孔徑、孔密度、表面積放大倍數、容值、耐壓、ESR 與壽命小時數 —— 查不到共通值就不寫（R5）。', 'sub'));
    return { svg: g.join(''), h: y - y0 + 16 };
  }

  /* 第 ② 段：這一格的台股站在哪一層 */
  const WHO = [
    ['最上游：電容用鋁箔（電蝕箔、化成箔）', '★ 6175 立敦（電容用鋁箔）—— 它不做電容成品，做的是陽極箔這一層的材料'],
    ['鋁質電解電容（成品）', '2375 凱美（鋁質電解電容，證據表特別註明它不是 MLCC 廠）、2472 立隆電（鋁質電解電容）、4939 亞電（鋁質電解電容）'],
    ['固態電容（導電高分子）', '6449 鈺邦（固態電容）'],
    ['只查到「電容」兩個字的', '5328 華容（電容，信心 estimated）—— 查不到產品細項，所以只列名，不指到主圖任何一層'],
    ['電解紙、電解液、陰極箔', '本圖查不到台股對應 —— 查不到就寫查不到，不編一個對應'],
  ];

  function foldWho(y0) {
    const g = [];
    let y = y0 + 22;
    g.push(T(28, y, '這一格的台股站在哪一層（6 家：1 家在箔、4 家在成品、1 家只查到「電容」兩個字）', 'hd'));
    const ids = ['ac_who0', 'ac_who1', 'ac_who2', 'ac_who3', 'ac_who4'];
    WHO.forEach((r, i) => {
      y += 20;
      g.push(part(ids[i], R(24, y - 14, 932, 19, 'transparent', 'part')
        + `<g pointer-events="none">${T(30, y, r[0] + '｜' + r[1], 'sub',
          null, i === 0 ? 'fill:var(--dg-warn)' : '')}</g>`));
    });
    y += 26;
    g.push(T(28, y, '★ 供應鏈資料的「被動元件」環節底下有 5 家（國巨、華新科、凱美、禾伸堂、信昌電），', 'sub', null, 'fill:var(--dg-warn)'));
    y += 17;
    g.push(T(28, y, '　 但其中只有 2375 凱美同時在「電容器」這個族群裡 —— 其餘 4 家做的是 MLCC 與晶片電阻，跟這張圖畫的東西無關。', 'sub', null, 'fill:var(--dg-warn)'));
    y += 17;
    g.push(T(28, y, '　 所以這張圖的每一個零件都指定了自己的公司清單，沒有一個走環節預設 —— 走預設會給出錯的答案，不是不完整的答案。', 'sub', null, 'fill:var(--dg-warn)'));
    y += 24;
    g.push(part('ac_mlcc_ref', R(24, y - 15, 932, 21, 'transparent', 'part')
      + `<g pointer-events="none">${T(30, y, '指路用的一格：陶瓷電容（MLCC）的疊層與端子結構在另一張圖 —— 做 MLCC 的是 2327 國巨、2492 華新科、3026 禾伸堂、6173 信昌電，跟這一格一家都不重疊。', 'sub')}</g>`));
    return { svg: g.join(''), h: y - y0 + 16 };
  }

  /* ================================================================ 版面
     收合時：標題 ＋ 兩排圖 ＋ 五行誠實性標示 ＋ 兩條章節列 ＝ **652px**（上限 700）。*/
  function alumCap() {
    const S1 = 544;
    const p1 = foldProc(S1 + 46);
    const S2 = S1 + 46 + p1.h;
    const p2 = foldWho(S2 + 46);
    const H = S2 + 46 + p2.h + 16;
    return `<svg class="dg dgm dgac dg1" viewBox="0 0 ${W} ${H}" width="100%" style="display:block">${D.STYLE}
      <style>
        /* ⚠ SVG 裡的 style：連註解都不准出現角括號（DECISIONS #231）。
           這裡只補兩件 diagrams.js 沒有的：孔的描邊，以及渦旋線的線帽。
           顏色一律走 --dg-*，沒有寫死色票。*/
        svg.dgac .acpore{stroke:none}
        svg.dgac .acspiral{stroke-linecap:round}
        svg.dgac .acvent{stroke-linecap:round}
      </style>
      ${T(16, 22, '電容器：鋁電解與固態電容剖面', 'ttl')}
      ${T(16, 40, '容量是「把箔咬出洞」咬出來的，介電質是「通電長出來」的 —— 跟 MLCC 的疊層＋燒結陶瓷完全是兩種東西。底下兩段預設收起來，按標題列就打得開。', 'cap')}

      <!-- ================= ① 捲芯四層帶 ／ ② 陽極箔放大 ／ ③ 整顆縱剖 ================= -->
      ${frame(16, 48, 424, 252)}
      ${T(28, 66, '① 捲芯：四層一個週期（由下到上：陽極箔 → 紙 → 陰極箔 → 紙）', 'hd')}
      ${coreBand()}
      ${spiralRoll()}
      ${T(24, 202, '① 陽極箔（蝕刻成蜂窩狀＋氧化膜）　② 電解紙（含浸電解液）', 'sub')}
      ${T(24, 218, '③ 陰極箔（一樣有孔，但沒有氧化膜）　④ 電解紙 → 回到 ①', 'sub')}
      ${T(24, 234, '★ 四層一個週期；三層捲起來，陽極會碰到陰極 → 短路。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(24, 250, '★ 陰極箔不是陰極 —— 真正的陰極是電解液。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(24, 266, '　 陰極箔只是把電解液的電引出來的集電體。', 'sub')}
      ${T(24, 282, '兩張箔長度方向錯開；右邊的渦旋斷面數得出 3 圈以上。', 'sub')}

      ${frame(448, 48, 280, 252)}
      ${T(460, 66, '② 陽極箔放大：孔是咬出來的，膜是長出來的', 'hd')}
      ${zoomFoil()}
      ${T(460, 218, '★ 氧化膜貼著孔壁的曲面走、而且等厚。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(460, 234, '　 畫成一條平直線，就把「表面積被', 'sub')}
      ${T(460, 250, '　 放大」這個命題畫掉了。', 'sub')}
      ${T(460, 266, '氧化膜是全圖最薄的層（不到箔厚的 1/20）。', 'sub')}
      ${T(460, 282, '★ 電解液鑽進孔裡、貼住氧化膜。', 'sub', null, 'fill:var(--dg-warn)')}

      ${frame(736, 48, 228, 252)}
      ${T(748, 66, '③ 整顆縱剖', 'hd')}
      ${wholeCan()}
      ${T(748, 262, '④ 鋁殼　⑤ 捲芯　⑥ 橡膠封口（一端）', 'sub')}
      ${T(748, 278, '⑦ 導針 ×2（從同一端出來）', 'sub')}
      ${T(748, 294, '⑧ 防爆閥刻痕（另一端，示意）', 'sub')}

      <!-- ================= ④ 液態 vs 固態（同一支函式畫兩次，只換一個參數） ================= -->
      ${frame(16, 306, 948, 146)}
      <path d="M490,316 L490,444" stroke="var(--dg-frame-s)" stroke-width="1" fill="none"/>
      ${T(28, 324, '④ 液態電解電容：中間是電解紙＋電解液', 'hd')}
      ${capCell(30, false)}
      ${T(502, 324, '⑤ 固態電容：只把電解液換成導電高分子，其餘完全一樣', 'hd')}
      ${capCell(504, true)}
      ${T(30, 414, '真正的陰極是電解液（紙只是把它含住、順便隔開兩張箔）', 'sub')}
      ${T(30, 430, '★ 兩格除了中間那一層以外完全一樣 —— 固態只換了一樣東西。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(30, 446, '下面那一層是陽極箔（有孔、有膜），上面那一層是陰極箔（有孔、沒有膜）。', 'sub')}
      ${T(504, 414, '導電高分子是實心的，沒有液體可以汽化 → 不會鼓脹爆漿', 'sub')}
      ${T(504, 430, '等效串聯電阻大幅下降（本圖不寫倍數與數量級）', 'sub')}
      ${T(504, 446, '★ 固態的那一層一樣要鑽進陽極箔的孔裡，才碰得到氧化膜。', 'sub', null, 'fill:var(--dg-warn)')}

      ${T(16, 468, '★ 誰做的：鋁電解 2375 凱美／2472 立隆電／4939 亞電；固態 6449 鈺邦；★ 6175 立敦做的是電容用鋁箔，不是電容成品。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 484, '本圖只有 2375 凱美 在供應鏈資料裡（被動元件環節）；另外五檔不在資料裡，所以寫在零件小卡與第 ② 段。', 'sub', null, 'fill:var(--dg-warn)')}
      ${T(16, 500, '示意圖，非實物比例。孔洞與氧化膜厚度為了看得見而誇張放大；本圖不寫容值、耐壓、ESR、壽命、市占率與營收數字。', 'cap')}
      ${T(16, 516, '陶瓷電容（MLCC）的疊層與端子結構見「被動元件：MLCC 疊層剖析」那張 —— 那是疊層＋燒結陶瓷，跟這張的捲繞完全是兩種東西。', 'cap')}
      ${T(16, 532, '公司角色取自板塊成分股證據表，信心標示見該表；電解紙、電解液與陰極箔是誰做的，本圖查不到台股對應。', 'cap')}

      <!-- ================= ① 製程 6 站（預設收合） ================= -->
      ${D.foldBar('ac1', S1, '① 從一片素箔到一顆電容：製程 6 站',
      '蝕刻 → 化成 → 裁切 → 捲繞 → 含浸 → 封口老化，以及哪兩站是立敦在做的')}
      <g class="dgbody" data-fold="ac1" data-y0="${S1 + 46}" data-y1="${S1 + 46 + p1.h}">
        ${p1.svg}
      </g>

      <!-- ================= ② 台股站在哪一層（預設收合） ================= -->
      ${D.foldBar('ac2', S2, '② 這一格的台股站在哪一層（6 家）',
      '1 家在箔、3 家在鋁電解成品、1 家在固態、1 家只查到「電容」兩個字，以及為什麼不能走環節預設')}
      <g class="dgbody" data-fold="ac2" data-y0="${S2 + 46}" data-y1="${S2 + 46 + p2.h}">
        ${p2.svg}
      </g>
    </svg>`;
  }

  /* ================================================================ 零件小卡（§7-E）
     ★ Y2（紅線）：**每一個零件都寫了 `cos`**，一個都沒有走環節預設。
       `cos` 裡只放真的在 supply_chain.yaml 裡的代號（這張圖只有 2375 一個），
       其餘五檔一律寫進 `none:` 的整句話。 */
  /* ⚠ `renderPartCard()` 只有在「一家台股都列不出來」的時候才印 `none:`。
     所以 `cos` 裡真的有人（2375 凱美）的零件，補充說明一定要寫在 `note:` ——
     寫進 `none:` 的話，**立敦那句話永遠不會出現在畫面上**（§6-Y3 是紅線）。
     `none:` 仍然保留，當作「哪天 2375 從 supply_chain.yaml 消失」的退路。*/
  const NOTE_FOIL = '★ 這一層的上游是 6175 立敦（電容用鋁箔 —— 電蝕箔、化成箔）。立敦不做電容成品，它做的是這一層的材料。立敦不在 supply_chain.yaml 裡，所以上面那一欄列不出它 —— 這裡用文字補。';
  const NOTE_MAKER = '做鋁質電解電容的台股還有 2472 立隆電（鋁質電解電容）與 4939 亞電（鋁質電解電容）。★ 兩家都不在 supply_chain.yaml 裡，所以上面那一欄列不出它們 —— 這裡用文字補。';

  const PARTS = {
    ac_anode: {
      name: '陽極箔（容量就是從這裡來的）',
      desc: '先用電化學蝕刻把表面咬成蜂窩狀，有效表面積放大很多倍 —— 容量就是從這裡來的。再通電做陽極氧化，在孔壁上長出氧化鋁介電質。',
      cos: ['2375'], note: NOTE_FOIL, none: NOTE_FOIL,
    },
    ac_oxide: {
      name: '陽極氧化膜（Al₂O₃，介電質）',
      desc: '★ 介電質不是買來的，是長出來的：鋁箔通電做陽極氧化，表面長出一層氧化鋁。膜有多厚由加多少電壓決定，所以耐壓越高、膜越厚、容量越小。★ 它只長在陽極箔上 —— 陰極箔上沒有這層膜，這就是「為什麼有極性」。',
      cos: ['2375'],
      note: '★ 氧化膜是「化成」這一道製程長出來的，屬於箔的加工、不是電容廠的獨立採購件 —— 做化成箔（電蝕箔）的台股是 6175 立敦（電容用鋁箔），它不做電容成品，也不在 supply_chain.yaml 裡。另外：膜厚與外加電壓成正比是原廠技術文件講的，但每伏特幾埃是 roughly 的說法、不同電解系統也不同，所以畫面上只寫「膜厚由外加電壓決定」，不寫數字。',
      none: '氧化膜是「化成」這一道製程長出來的，屬於箔的加工、不是電容廠的獨立採購件。做化成箔的台股是 6175 立敦（電容用鋁箔），它不在 supply_chain.yaml 裡。',
    },
    ac_pore: {
      name: '蝕刻孔（隧道／海綿狀）',
      desc: '咬出來的孔。孔越多越深，同一片箔的表面積越大。★ 兩面都咬，中間要留一條實心芯 —— 沒有芯的箔會斷。本圖不寫孔徑、孔密度與表面積放大倍數（查不到共通值）。',
      cos: ['2375'], note: NOTE_FOIL, none: NOTE_FOIL,
    },
    ac_core: {
      name: '箔的基體（未蝕刻的芯部）',
      desc: '兩面被咬之後中間留下來的那一條實心鋁。圖上的芯厚是「箔厚 − 2×孔深」真的減出來的，不是目測。',
      cos: ['2375'], note: NOTE_FOIL, none: NOTE_FOIL,
    },
    ac_paper: {
      name: '電解紙（隔離紙）',
      desc: '天然纖維素做的紙，含浸電解液，同時把兩張箔隔開。★ 它本身不是電極，也不是介電質 —— 介電質是陽極箔上那層氧化膜。',
      cos: [],
      none: '★ 電解紙與電解液這一段，本圖查不到台股對應，先標為未知 —— 查不到就寫查不到，不編一個對應（R5）。',
    },
    ac_elyte: {
      name: '電解液（★ 它才是真正的陰極）',
      desc: '★ 這張圖第三句話：陰極箔不是陰極，真正的陰極是含浸在紙裡的電解液。它鑽進陽極箔的孔裡、貼住氧化膜 —— 只畫在紙裡就是沒有接觸到介電質，電容不成立。',
      cos: [],
      none: '★ 電解液的配方與化學品這一段，本圖查不到台股對應，先標為未知（R5）。',
    },
    ac_cathode: {
      name: '陰極箔（不是陰極，是集電體）',
      desc: '★ 一樣有蝕刻孔，但**沒有**那層氧化膜（只有自然氧化層）。它的工作是把電解液的電引出來 —— 兩面都畫氧化膜就變成了雙極性電容，而且把「為什麼有極性」這件事畫掉了。',
      cos: [],
      none: '★ 陰極箔是誰做的，本次查不到。查到的 6175 立敦講的是電蝕箔與化成箔（陽極側），不能直接套到陰極箔上（R5）。',
    },
    ac_lead: {
      name: '導針（引線）×2',
      desc: '一根接陽極箔、一根接陰極箔。★ 整顆的兩根導針從同一端穿出（徑向引線型）—— 一端一根那是軸向型，跟這裡的捲芯畫法對不起來。',
      cos: [], none: '導針這一件，本圖查不到台股的具名對應。',
    },
    ac_winding: {
      name: '捲芯（四層捲成一個圓柱）',
      desc: '四層同時捲在一個大直徑輪上，兩張箔稍微橫向錯開，避免邊緣接觸。★ 右邊的渦旋斷面數得出 3 圈以上、四層交替 —— 三層捲起來，上一圈的陽極會直接碰到下一圈的陰極，短路。',
      cos: ['2375'], note: NOTE_MAKER, none: NOTE_MAKER,
    },
    ac_can: { name: '鋁殼', desc: '捲芯含浸完之後裝進去的薄壁圓筒，再密封。', cos: ['2375'], note: NOTE_MAKER, none: NOTE_MAKER },
    ac_seal: { name: '橡膠封口', desc: '在鋁殼的一端，兩根導針從這裡穿出去。它同時是密封件，也是壓力上來時的洩壓路徑之一。', cos: ['2375'], note: NOTE_MAKER, none: NOTE_MAKER },
    ac_vent: {
      name: '防爆閥（刻痕）',
      desc: '壓力上來時先從這裡裂開，不讓整顆炸掉。★ 本圖把它畫在與封口相反的那一端，但這一點**本次查不到來源**（徑向引線型的防爆結構各家做法不同），所以標為示意，也不寫刻痕形狀的規格。',
      cos: ['2375'], note: NOTE_MAKER, none: NOTE_MAKER,
    },
    ac_sleeve: {
      name: '外套膠膜',
      desc: '包在鋁殼外面的有色薄膜。★ 本圖上面一個字、一個色碼、一個廠商標示都沒有 —— 那些是產品外觀，不是結構。',
      cos: ['2375'], note: NOTE_MAKER, none: NOTE_MAKER,
    },
    ac_solid: {
      name: '導電高分子（固態電容的中間層）',
      desc: '★ 固態電容只換了一樣東西：把電解液換成固態的導電高分子。它一樣要鑽進陽極箔的孔裡。等效串聯電阻大幅下降，而且沒有液體可以汽化，所以不會鼓脹爆漿。',
      cos: [],
      note: '「導電能力高 2～3 個數量級」是單一材料研究網來源，而且那是材料的導電度、不是成品的 ESR 改善倍數 —— 所以畫面上只寫「大幅下降」，不寫倍數。',
      none: '★ 固態（導電高分子）電容的台股是 6449 鈺邦（固態電容）。鈺邦不在 supply_chain.yaml 裡，所以這張小卡列不出它 —— 這裡用文字補。',
    },
    ac_mlcc_ref: {
      name: '指路：陶瓷電容（MLCC）在另一張圖',
      desc: 'MLCC 的介電質是燒結的陶瓷片、靠疊更多層放大容量、電極是印上去的鎳；這張圖的介電質是長出來的氧化鋁、靠把箔咬出更多孔放大容量、鋁箔本身就是電極。兩群台股一家都不重疊。',
      cos: ['2327', '2492', '3026', '6173'],
    },
  };
  PROC.forEach((r, i) => {
    PARTS['ac_proc' + i] = {
      name: r[0], desc: r[1], cos: ['2375'],
      note: '★ 蝕刻與化成這兩站在台股是 6175 立敦（電容用鋁箔）在做 —— 它做的是箔，不是電容成品，而且不在 supply_chain.yaml 裡。其餘四站是電容廠自己的產線。',
      none: '這一站是電容廠自己的產線（蝕刻與化成兩站在台股是 6175 立敦在做，它不在 supply_chain.yaml 裡）。',
    };
  });
  WHO.forEach((r, i) => {
    PARTS['ac_who' + i] = {
      name: r[0], desc: r[1], cos: i === 1 ? ['2375'] : [],
      note: '這一列裡除了 2375 凱美之外的公司全部不在 supply_chain.yaml 的環節裡 —— 對應寫在上面那句話裡。',
      none: '這一列的公司全部不在 supply_chain.yaml 的環節裡，所以「做這個的台股」欄列不出它們 —— 對應寫在這裡。',
    };
  });

  window.DG.register('capacitor', {
    level: 'group', chain: 'electronics',
    name: '電容器：鋁電解與固態電容剖面',
    draw: alumCap, native: 980, scene: null,
    q: '鋁電容的容量是怎麼來的？為什麼要把箔咬出洞？固態電容把什麼換掉了，所以不會爆？',
    parts: PARTS,
  });
})();
